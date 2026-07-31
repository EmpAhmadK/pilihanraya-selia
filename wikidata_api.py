"""
Thin wrapper around the Wikidata action API.

Read calls are made anonymously (no auth needed for public data).
Write calls are signed with the logged-in user's OAuth 1.0a token, so every
edit is attributed to that person's own Wikidata account - this tool never
edits under its own identity.
"""
import json

import requests
from requests_oauthlib import OAuth1

from config import (
    OAUTH_CONSUMER_KEY,
    OAUTH_CONSUMER_SECRET,
    USER_AGENT,
    WIKIDATA_API_URL,
)

_session = requests.Session()
_session.headers.update({"User-Agent": USER_AGENT})


class WikidataApiError(Exception):
    pass


def _oauth1(access_token):
    return OAuth1(
        client_key=OAUTH_CONSUMER_KEY,
        client_secret=OAUTH_CONSUMER_SECRET,
        resource_owner_key=access_token.key,
        resource_owner_secret=access_token.secret,
        signature_method="HMAC-SHA1",
    )


# ------------------------------------------------------------------- reads

def get_entities(ids, props="claims|labels"):
    """Fetch one or many entities. ids: str or list[str]. Returns dict qid->entity."""
    if isinstance(ids, str):
        ids = [ids]
    ids = [i for i in ids if i]
    if not ids:
        return {}
    entities = {}
    # API allows up to 50 ids per request
    for i in range(0, len(ids), 50):
        chunk = ids[i : i + 50]
        r = _session.get(
            WIKIDATA_API_URL,
            params={
                "action": "wbgetentities",
                "ids": "|".join(chunk),
                "props": props,
                "languages": "ms|en",
                "format": "json",
            },
            timeout=30,
        )
        r.raise_for_status()
        data = r.json()
        entities.update(data.get("entities", {}))
    return entities


def get_entity(qid, props="claims|labels"):
    return get_entities([qid], props=props).get(qid, {})


def label_of(entity, lang_pref=("ms", "en")):
    labels = entity.get("labels", {}) if entity else {}
    for lang in lang_pref:
        if lang in labels:
            return labels[lang]["value"]
    if labels:
        return next(iter(labels.values()))["value"]
    return entity.get("id", "?") if entity else "?"


# ------------------------------------------------------------------ writes

def get_csrf_token(access_token):
    r = _session.get(
        WIKIDATA_API_URL,
        params={"action": "query", "meta": "tokens", "type": "csrf", "format": "json"},
        auth=_oauth1(access_token),
        timeout=30,
    )
    r.raise_for_status()
    data = r.json()
    return data["query"]["tokens"]["csrftoken"]


def _post(access_token, params):
    token = get_csrf_token(access_token)
    params = dict(params)
    params["token"] = token
    params["format"] = "json"
    r = _session.post(
        WIKIDATA_API_URL,
        data=params,
        auth=_oauth1(access_token),
        timeout=30,
    )
    r.raise_for_status()
    data = r.json()
    if "error" in data:
        raise WikidataApiError(data["error"].get("info", str(data["error"])))
    return data


# --------------------------------------------------------------- value helpers

def quantity_value_json(amount):
    amount = int(round(amount))
    sign = "+" if amount >= 0 else ""
    return json.dumps({"amount": f"{sign}{amount}", "unit": "1"})


def item_value_json(qid):
    return json.dumps({"entity-type": "item", "numeric-id": int(qid[1:]), "id": qid})


# ------------------------------------------------------------------ actions

def set_qualifier_quantity(access_token, statement_guid, prop, amount, snakhash=None):
    params = {
        "action": "wbsetqualifier",
        "claim": statement_guid,
        "property": prop,
        "snaktype": "value",
        "value": quantity_value_json(amount),
    }
    if snakhash:
        params["snakhash"] = snakhash
    return _post(access_token, params)


def set_qualifier_item(access_token, statement_guid, prop, qid):
    return _post(
        access_token,
        {
            "action": "wbsetqualifier",
            "claim": statement_guid,
            "property": prop,
            "snaktype": "value",
            "value": item_value_json(qid),
        },
    )


def edit_claim_value(access_token, statement_guid, value_json):
    """Set the mainsnak value of an existing statement, given its GUID."""
    return _post(
        access_token,
        {
            "action": "wbsetclaimvalue",
            "claim": statement_guid,
            "snaktype": "value",
            "value": value_json,
        },
    )


def create_claim(access_token, entity_id, prop, value_json, snak_type="value"):
    """Create a new top-level statement. Returns the new claim dict."""
    data = _post(
        access_token,
        {
            "action": "wbcreateclaim",
            "entity": entity_id,
            "property": prop,
            "snaktype": snak_type,
            "value": value_json,
        },
    )
    return data["claim"]


def remove_qualifiers(access_token, statement_guid, prop, snakhashes):
    if not snakhashes:
        return None
    return _post(
        access_token,
        {
            "action": "wbremovequalifiers",
            "claim": statement_guid,
            "property": prop,
            "snakhash": "|".join(snakhashes),
        },
    )


def upsert_vote_qualifier(access_token, claim, prop, amount):
    """
    Edit the P1111 (or similar) qualifier on `claim` in place rather than
    adding a new one. If the qualifier already has more than one value
    (a data-quality issue), keep/update only the first and remove the rest.
    """
    guid = claim["id"]
    existing = claim.get("qualifiers", {}).get(prop, [])
    hashes = [q["hash"] for q in existing if "hash" in q]
    primary_hash = hashes[0] if hashes else None
    set_qualifier_quantity(access_token, guid, prop, amount, snakhash=primary_hash)
    if len(hashes) > 1:
        remove_qualifiers(access_token, guid, prop, hashes[1:])



def remove_claims(access_token, guids):
    if not guids:
        return None
    return _post(access_token, {"action": "wbremoveclaims", "claim": "|".join(guids)})


# ---------------------------------------------------------- higher-level helpers

def find_matching_claim(claims, qualifier_prop=None, qualifier_value=None):
    """
    Find a statement among `claims` (a list, i.e. entity["claims"].get(prop, [])).
    If qualifier_prop is None: match the statement that has NO P31 qualifier at all
    (used to distinguish the "plain" P1867 value from postal/early-voting ones).
    Otherwise: match the statement whose qualifier_prop qualifier equals qualifier_value (a QID).
    """
    for c in claims:
        quals = c.get("qualifiers", {})
        if qualifier_prop is None:
            if "P31" not in quals:
                return c
        else:
            for q in quals.get(qualifier_prop, []):
                dv = q.get("datavalue", {}).get("value", {})
                if isinstance(dv, dict) and dv.get("id") == qualifier_value:
                    return c
    return None


def upsert_quantity_statement(
    access_token, entity_id, entity, prop, amount, qualifier_prop=None, qualifier_value=None
):
    """Create or update a quantity-valued statement, optionally distinguished by a P31 qualifier."""
    claims = entity.get("claims", {}).get(prop, [])
    target = find_matching_claim(claims, qualifier_prop, qualifier_value)
    value_json = quantity_value_json(amount)
    if target:
        edit_claim_value(access_token, target["id"], value_json)
        return target["id"]
    else:
        new_claim = create_claim(access_token, entity_id, prop, value_json)
        if qualifier_prop and qualifier_value:
            set_qualifier_item(access_token, new_claim["id"], qualifier_prop, qualifier_value)
        return new_claim["id"]


def has_claim(entity, prop):
    return bool(entity.get("claims", {}).get(prop))


def candidate_number_of(claim):
    quals = claim.get("qualifiers", {})
    for q in quals.get("P4243", []):
        dv = q.get("datavalue", {}).get("value")
        if dv is not None:
            return dv
    return None


def votes_of(claim):
    quals = claim.get("qualifiers", {})
    for q in quals.get("P1111", []):
        dv = q.get("datavalue", {}).get("value")
        if dv:
            try:
                return int(dv["amount"])
            except (KeyError, ValueError, TypeError):
                return None
    return None


def party_of(claim):
    quals = claim.get("qualifiers", {})
    for q in quals.get("P4353", []):
        dv = q.get("datavalue", {}).get("value")
        if dv:
            return dv.get("id")
    return None
