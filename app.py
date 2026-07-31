import mwoauth
from flask import Flask, jsonify, redirect, render_template, request, session, url_for

import auth
import storage
import wikidata_api as wd
from config import OAUTH_MWURI, SECRET_KEY

app = Flask(__name__)
app.config["SECRET_KEY"] = SECRET_KEY

# Wikidata QIDs used for the "postal" / "early voting" qualifier values.
Q_POSTAL_VOTER = "Q15044040"
Q_EARLY_VOTER = "Q708369"

P_CANDIDATE = "P726"
P_VOTES = "P1111"
P_CANDNUM = "P4243"
P_PARTY = "P4353"
P_VOTERS = "P1867"
P_TURNOUT = "P1868"
P_SPOILT = "P5044"
P_VALID = "P1697"
P_ELECTED = "P991"

# Manual colour overrides for specific parties (used in preference to
# whatever P465 says on Wikidata, e.g. while those statements are still
# missing/being added).
PARTY_COLOR_OVERRIDES = {
    "Q140263455": "#ff7800",
    "Q4925703": "#D446B7",
    "Q86890510": "#1759a0",
}

# Used for a seat box when there's no single leading candidate (either no
# votes recorded yet, or a tie for first place).
DEFAULT_SEAT_COLOR = "#4C4C4C"

# Manual colour overrides for parties that don't (yet) have a P465 (colour)
# statement on Wikidata. These take precedence over P465 when present.
PARTY_COLOR_OVERRIDES = {
    "Q140263455": "#ff7800",
    "Q4925703": "#D446B7",
}

# Colour used when there is no single leading candidate (no votes recorded
# yet, or a tie for first place).
NO_LEADER_COLOR = "#4C4C4C"

_party_color_cache = {}


def get_party_color(qid):
    """Look up a party's box colour: manual override first, else P465, cached per-process."""
    if not qid:
        return None
    if qid in PARTY_COLOR_OVERRIDES:
        return PARTY_COLOR_OVERRIDES[qid]
    if qid in _party_color_cache:
        return _party_color_cache[qid]
    entity = wd.get_entity(qid, props="claims")
    color = _party_color(entity)
    _party_color_cache[qid] = color
    return color


def _compute_leading_color(items):
    """
    items: iterable of dicts with 'votes' (int or None) and 'party_color'
    (hex string or None). Returns the leading candidate's party colour, or
    NO_LEADER_COLOR if there's no votes yet or a tie for first place.
    """
    max_votes = None
    leaders = []
    for it in items:
        v = it.get("votes")
        if v is None:
            continue
        if max_votes is None or v > max_votes:
            max_votes = v
            leaders = [it]
        elif v == max_votes:
            leaders.append(it)
    if len(leaders) == 1:
        return leaders[0].get("party_color") or NO_LEADER_COLOR
    return NO_LEADER_COLOR


# --------------------------------------------------------------------- auth

@app.route("/login")
def login():
    redirect_url, request_token = mwoauth.initiate(OAUTH_MWURI, auth.consumer_token)
    session["request_token_key"] = request_token.key
    session["request_token_secret"] = request_token.secret
    return redirect(redirect_url)


@app.route("/oauth-callback")
def oauth_callback():
    request_token = mwoauth.RequestToken(
        session.pop("request_token_key"), session.pop("request_token_secret")
    )
    access_token = mwoauth.complete(
        OAUTH_MWURI, auth.consumer_token, request_token, request.query_string
    )
    identity = mwoauth.identify(OAUTH_MWURI, auth.consumer_token, access_token)
    session["username"] = identity["username"]
    session["access_token_key"] = access_token.key
    session["access_token_secret"] = access_token.secret
    return redirect(url_for("index"))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


# -------------------------------------------------------------------- menu

@app.route("/")
def index():
    elections = storage.get_elections()
    return render_template(
        "index.html",
        elections=elections,
        username=auth.current_user(),
        is_admin=storage.is_user_admin(auth.current_user()),
        is_allowed=storage.is_user_allowed(auth.current_user()),
    )


@app.route("/elections/new", methods=["POST"])
@auth.admin_required
def new_election():
    name = request.form.get("name", "").strip()
    qid = request.form.get("qid", "").strip()
    kods = request.form.getlist("seat_kod")
    namas = request.form.getlist("seat_nama")
    qids = request.form.getlist("seat_qid")
    seats = []
    for k, n, q in zip(kods, namas, qids):
        if k.strip() and q.strip():
            seats.append({"kod": k.strip(), "nama": n.strip(), "qid": q.strip()})
    if name and qid:
        storage.save_election(qid, name, seats)
    return redirect(url_for("index"))


@app.route("/admin/whitelist", methods=["GET", "POST"])
@auth.admin_required
def admin_whitelist():
    if request.method == "POST":
        action = request.form.get("action")
        username = request.form.get("username", "").strip()
        if action == "add" and username:
            storage.add_user(username, admin=bool(request.form.get("admin")))
        elif action == "remove" and username:
            storage.remove_user(username)
        return redirect(url_for("admin_whitelist"))
    return render_template(
        "whitelist.html",
        users=storage.list_users(),
        username=auth.current_user(),
    )


# --------------------------------------------------------------- election page

def _build_seat_view(seat, entity):
    """Turn one constituency's Wikidata entity into template-friendly data."""
    claims = entity.get("claims", {}).get(P_CANDIDATE, [])
    candidates = []
    party_ids = set()
    for c in claims:
        mainsnak = c.get("mainsnak", {})
        dv = mainsnak.get("datavalue", {}).get("value")
        cand_qid = dv.get("id") if isinstance(dv, dict) else None
        party_qid = wd.party_of(c)
        if party_qid:
            party_ids.add(party_qid)
        candidates.append(
            {
                "guid": c["id"],
                "qid": cand_qid,
                "number": wd.candidate_number_of(c),
                "votes": wd.votes_of(c),
                "party_qid": party_qid,
            }
        )

    def sort_key(cnd):
        n = cnd["number"]
        try:
            return (0, int(n))
        except (TypeError, ValueError):
            return (1, str(n))

    candidates.sort(key=sort_key)

    cand_entities = wd.get_entities([c["qid"] for c in candidates if c["qid"]], props="labels")
    party_entities = wd.get_entities(list(party_ids), props="labels|claims")

    for c in candidates:
        c["label"] = wd.label_of(cand_entities.get(c["qid"], {})) if c["qid"] else "?"
        if c["party_qid"]:
            pe = party_entities.get(c["party_qid"], {})
            c["party_label"] = wd.label_of(pe)
            c["party_color"] = PARTY_COLOR_OVERRIDES.get(c["party_qid"]) or _party_color(pe)
        else:
            c["party_label"] = None
            c["party_color"] = None

    leading = None
    tied = False
    for c in candidates:
        if c["votes"] is None:
            continue
        if leading is None or c["votes"] > leading["votes"]:
            leading = c
            tied = False
        elif c["votes"] == leading["votes"]:
            tied = True

    leading_color = leading["party_color"] if (leading and not tied) else None

    rasmi = wd.has_claim(entity, P_ELECTED)

    return {
        "kod": seat["kod"],
        "nama": seat["nama"],
        "qid": seat["qid"],
        "candidates": candidates,
        "leading_color": leading_color or DEFAULT_SEAT_COLOR,
        "rasmi": rasmi,
    }


def _party_color(party_entity):
    claims = party_entity.get("claims", {}).get("P465", [])
    for c in claims:
        dv = c.get("mainsnak", {}).get("datavalue", {}).get("value")
        if dv:
            return "#" + dv
    return None


@app.route("/election/<eqid>")
@auth.login_required
def election_page(eqid):
    election = storage.get_election(eqid)
    if not election:
        return "Pilihan raya tidak dijumpai.", 404

    main_entity = wd.get_entity(eqid)
    main_info = _read_main_info(main_entity)

    seat_qids = [s["qid"] for s in election["seats"]]
    seat_entities = wd.get_entities(seat_qids, props="claims")

    seats_view = [
        _build_seat_view(seat, seat_entities.get(seat["qid"], {}))
        for seat in election["seats"]
    ]

    return render_template(
        "election.html",
        election=election,
        main_info=main_info,
        seats=seats_view,
        username=auth.current_user(),
        is_admin=storage.is_user_admin(auth.current_user()),
    )


def _read_main_info(entity):
    claims = entity.get("claims", {})

    def qty(prop, qualifier_value=None):
        target = wd.find_matching_claim(
            claims.get(prop, []),
            qualifier_prop=("P31" if qualifier_value else None),
            qualifier_value=qualifier_value,
        )
        if not target:
            return None
        dv = target.get("mainsnak", {}).get("datavalue", {}).get("value")
        if dv:
            try:
                return int(float(dv["amount"]))
            except (KeyError, ValueError, TypeError):
                return None
        return None

    return {
        "eligible_voters": qty(P_VOTERS),
        "postal_voters": qty(P_VOTERS, Q_POSTAL_VOTER),
        "early_voters": qty(P_VOTERS, Q_EARLY_VOTER),
        "turnout": qty(P_TURNOUT),
        "spoilt_votes": qty(P_SPOILT),
        "valid_votes": qty(P_VALID),
    }


@app.route("/election/<eqid>/update_main", methods=["POST"])
@auth.login_required
def update_main(eqid):
    election = storage.get_election(eqid)
    if not election:
        return jsonify({"error": "Pilihan raya tidak dijumpai."}), 404

    token = auth.current_access_token()
    entity = wd.get_entity(eqid)

    fields = {
        "eligible_voters": (P_VOTERS, None),
        "postal_voters": (P_VOTERS, Q_POSTAL_VOTER),
        "early_voters": (P_VOTERS, Q_EARLY_VOTER),
        "turnout": (P_TURNOUT, None),
        "spoilt_votes": (P_SPOILT, None),
        "valid_votes": (P_VALID, None),
    }

    try:
        for field, (prop, qualifier_value) in fields.items():
            raw = request.form.get(field, "").strip()
            if raw == "":
                continue
            amount = int(raw)
            wd.upsert_quantity_statement(
                token, eqid, entity, prop, amount,
                qualifier_prop=("P31" if qualifier_value else None),
                qualifier_value=qualifier_value,
            )
    except wd.WikidataApiError as e:
        return jsonify({"error": str(e)}), 400

    return redirect(url_for("election_page", eqid=eqid))


# ----------------------------------------------------------- constituency edit

@app.route("/election/<eqid>/constituency/<cqid>/save", methods=["POST"])
@auth.login_required
def save_constituency(eqid, cqid):
    election = storage.get_election(eqid)
    if not election:
        return jsonify({"error": "Pilihan raya tidak dijumpai."}), 404

    seat = next((s for s in election["seats"] if s["qid"] == cqid), None)
    if not seat:
        return jsonify({"error": "Kawasan tidak dijumpai."}), 404

    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"

    token = auth.current_access_token()
    entity = wd.get_entity(cqid)
    claims = entity.get("claims", {}).get(P_CANDIDATE, [])

    rasmi = request.form.get("rasmi") == "on"

    updated_votes = {}
    try:
        for c in claims:
            guid = c["id"]
            field = f"votes__{guid}"
            raw = request.form.get(field, "").strip()
            current = wd.votes_of(c)
            if raw == "":
                updated_votes[guid] = current
                continue
            amount = int(raw)
            updated_votes[guid] = amount
            existing_hashes = [
                q["hash"] for q in c.get("qualifiers", {}).get(P_VOTES, []) if "hash" in q
            ]
            needs_edit = current != amount or len(existing_hashes) > 1
            if needs_edit:
                wd.upsert_vote_qualifier(token, c, P_VOTES, amount)

        if rasmi and not wd.has_claim(entity, P_ELECTED):
            # Determine the leading candidate using the just-saved vote counts.
            best_guid, best_votes, best_qid, best_party = None, None, None, None
            for c in claims:
                v = updated_votes.get(c["id"])
                if v is not None and (best_votes is None or v > best_votes):
                    best_votes = v
                    best_guid = c["id"]
                    mainsnak = c.get("mainsnak", {})
                    dv = mainsnak.get("datavalue", {}).get("value")
                    best_qid = dv.get("id") if isinstance(dv, dict) else None
                    best_party = wd.party_of(c)

            if best_qid:
                new_claim = wd.create_claim(
                    token, cqid, P_ELECTED, wd.item_value_json(best_qid)
                )
                if best_party:
                    wd.set_qualifier_item(token, new_claim["id"], P_PARTY, best_party)

        if rasmi and not wd.has_claim(entity, P_VALID):
            total = sum(v for v in updated_votes.values() if v is not None)
            wd.create_claim(token, cqid, P_VALID, wd.quantity_value_json(total))

    except wd.WikidataApiError as e:
        return jsonify({"error": str(e)}), 400

    if is_ajax:
        fresh_entity = wd.get_entity(cqid)
        seat_view = _build_seat_view(seat, fresh_entity)
        return jsonify({"seat": seat_view})

    return redirect(url_for("election_page", eqid=eqid))


# Toolforge's Kubernetes-based Python webservice (uwsgi) looks for a module
# level variable called "application" by default.
application = app

if __name__ == "__main__":
    app.run(debug=True)
