# Alat Suntingan Wikidata — Pilihan Raya Negeri Sembilan

A Toolforge-hosted Flask app that lets a whitelisted set of Wikimedia editors
log in with OAuth and quickly update election results on Wikidata:

- Per-constituency candidate vote counts (`P1111` qualifier on each `P726` statement)
- A "Rasmi" (official) switch per constituency, which adds `P991` (elected
  candidate, with `P4353` party qualifier) and `P1697` (total valid votes)
- The election-wide statistics on the election item (`P1867` eligible/postal/
  early voters, `P1868` turnout, `P5044` spoilt votes, `P1697` valid votes)
- An admin-only screen to whitelist users and register new elections (so the
  same tool can be reused for future elections)

All edits are made **as the logged-in user**, via their own OAuth token — the
tool itself never edits under its own account.

---

## 0. What you already have

You said you've created a Toolforge account and had a tool approved. That
means you should already have:

- A Wikimedia developer account (Toolforge login)
- A **tool name** (e.g. `pilihanraya-selia`) registered at
  <https://toolsadmin.wikimedia.org/tools/>

Everything below assumes your tool is called `pilihanraya-selia` — replace
that with your actual tool name everywhere.

---

## 1. Register an OAuth 1.0a consumer

This is what lets users "log in with Wikimedia" and lets the tool edit on
their behalf.

1. Go to <https://meta.wikimedia.org/wiki/Special:OAuthConsumerRegistration/propose>
   (log in with your own Wikimedia account first).
2. Fill in the form:
   - **Application name**: something like `Alat Pilihan Raya Negeri Sembilan`
     (must be unique on Meta-Wiki)
   - **Application description**: short description of what it does
   - **OAuth protocol version**: OAuth 1.0a
   - **Callback URL**: `https://pilihanraya-selia.toolforge.org/oauth-callback`
   - Check **"This consumer is for use only by ..."** and enter your own
     username — this skips the manual-approval queue since only you will
     control who uses it (the tool does its own whitelist on top of this).
   - **Applicable project**: `www.wikidata.org` (or "all projects" is fine too)
   - **Grants**: at minimum tick:
     - Basic rights
     - Edit existing pages
     - Create, edit, and move pages
     (Wikibase items are edited through the normal `wbeditentity`-family
     actions, which fall under the normal edit grants — you do not need a
     special Wikidata grant.)
3. Submit. You'll be given a **consumer key** and **consumer secret**.
   Copy both somewhere safe — the secret is shown only once.

(If you ever change the callback URL or tool name, you'll need to edit the
consumer registration too — see "Manage OAuth consumers" on the same wiki.)

---

## 2. Get the code onto Toolforge

On your own computer, unzip the project you were given, then upload it, or
just `scp`/`git` it in. The simplest path if you don't already use git:

```bash
# from your local machine
scp -r pilihanraya-selia login.toolforge.org:
```

(`login.toolforge.org` is the Toolforge SSH bastion; make sure your SSH key
is set up as per <https://wikitech.wikimedia.org/wiki/Help:Toolforge/SSH_Keys>
— you should already have done this when your account was approved.)

Then SSH in and switch to your tool's account:

```bash
ssh login.toolforge.org
become pilihanraya-selia
```

Move the code into your tool's home directory:

```bash
mv ~/pilihanraya-selia ~/www/python/src
cd ~/www/python/src
```

(Toolforge's Python webservice convention expects the code under
`~/www/python/src`. If that directory doesn't exist yet, `mkdir -p ~/www/python`
first, then move the folder in as `src`.)

---

## 3. Create your secrets file

Still as the tool account, inside `~/www/python/src`:

```bash
cat > secrets.json << 'EOF'
{
  "OAUTH_CONSUMER_KEY": "paste-your-consumer-key-here",
  "OAUTH_CONSUMER_SECRET": "paste-your-consumer-secret-here",
  "FLASK_SECRET_KEY": "a-long-random-string-you-make-up",
  "INITIAL_ADMINS": "YourWikimediaUsername"
}
EOF
```

- `FLASK_SECRET_KEY` can be anything long and random — e.g. run
  `python3 -c "import secrets; print(secrets.token_hex(32))"` and paste the
  output.
- `INITIAL_ADMINS` should be your own Wikimedia username (this only matters
  the very first time the tool runs — after that, admin status is managed
  from the tool's own "Urus senarai pengguna dibenarkan" page).

This file is git-ignored and never sent anywhere except read locally by the
app, so it's the simplest way to configure secrets without wrestling with
Kubernetes environment variables.

Also point the tool's data directory outside the code folder, so a future
redeploy never risks wiping your saved elections/whitelist:

```bash
mkdir -p ~/data
export NS_TOOL_DATA_DIR=~/data   # for the seeding step below
```

(You'll also want this exported permanently — easiest is to add
`export NS_TOOL_DATA_DIR=/data/project/pilihanraya-selia/data` — actually
simplest of all: just leave `NS_TOOL_DATA_DIR` unset. The default
`data/` folder next to the code works fine too, since your home directory on
Toolforge is persistent NFS storage; it's only an issue if you later `rm -rf`
and redeploy the whole `src` folder from scratch.)

---

## 4. Set up the Python environment

Toolforge's webservice containers are separate from the bastion, so you build
your virtualenv *inside* a webservice shell:

```bash
webservice --backend=kubernetes python3.11 shell
```

This drops you into a container shell with the right Python version. Inside it:

```bash
cd ~/www/python/src
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

Optionally seed the Negeri Sembilan election + all 36 seats now, instead of
typing them into the web form:

```bash
python3 seed_data.py
```

You should see: `Saved 'Pilihan Raya Negeri Sembilan' (Q139747429) with 36 seats.`

Then exit the shell:

```bash
deactivate
exit
```

---

## 5. Start the webservice

Back on the bastion (still `become`d as your tool):

```bash
webservice --backend=kubernetes python3.11 start
```

Check it came up:

```bash
webservice --backend=kubernetes python3.11 status
```

Your tool should now be reachable at:

```
https://pilihanraya-selia.toolforge.org/
```

If something goes wrong, check the logs:

```bash
webservice --backend=kubernetes python3.11 logs
```

Common gotchas:
- **"application not found"** — make sure `app.py` defines a module-level
  `application` variable (it already does in this codebase).
- **500 error on login** — double check `OAUTH_CONSUMER_KEY`/`SECRET` in
  `secrets.json` and that the callback URL in the OAuth consumer registration
  exactly matches `https://pilihanraya-selia.toolforge.org/oauth-callback`.

To restart after any code change:

```bash
webservice --backend=kubernetes python3.11 restart
```

---

## 6. First login and sanity check

1. Visit `https://pilihanraya-selia.toolforge.org/` and click
   **"Log masuk dengan Wikimedia"**.
2. Approve the OAuth authorization on Meta-Wiki (first time only).
3. You should land back on the main menu, now recognised as an admin (since
   you put your username in `INITIAL_ADMINS`).
4. If you ran `seed_data.py`, the Negeri Sembilan election should already be
   listed — click into it to see the 36-seat grid. Otherwise, use the
   **"Tambah Pilihan Raya Baharu"** form to add it manually.
5. Try editing one constituency's votes and saving *without* ticking
   "Rasmi" first, to make sure edits land correctly on Wikidata (check the
   item's history) before trusting it with the official "Rasmi" toggle.

---

## 7. Whitelisting other editors

As admin, go to **"Urus senarai pengguna dibenarkan"** from the main menu (or
`https://pilihanraya-selia.toolforge.org/admin/whitelist`) and add each
person's exact Wikimedia username. They can then log in with their own
account and will be able to edit, but won't see the admin-only "add election"
/ "whitelist" controls unless you also tick "Jadikan pentadbir" for them.

---

## Notes, caveats and things worth double-checking

- **Party colour / icon**: the seat box colour is read from `P465` (color)
  on the party item referenced by the `P4353` qualifier. If a party item has
  no `P465` statement, that candidate's dot/box falls back to grey — you may
  want to add colours to the relevant party items on Wikidata first.
- **"Rasmi" is one-directional in this version**: once `P991` exists on a
  constituency item, the switch shows as checked and locked (to avoid
  silently re-triggering edits). If you need to *correct* an official result
  after the fact, it's safest to fix the statements directly on Wikidata (or
  ask me to add an "unlock/undo" admin action).
- **No database server needed**: elections and the whitelist are stored as
  small JSON files under `data/` (or wherever `NS_TOOL_DATA_DIR` points). This
  is fine at this scale; if you outgrow it, Toolforge's ToolsDB (MariaDB) is
  the natural next step.
- **Rate limits**: each "save" on a constituency does one API call per
  changed vote count, plus up to two more when marking "Rasmi". For 36 seats
  x ~4 candidates this is well within normal Wikidata API limits.
- **Toolforge documentation moves over time** — if any `webservice` command
  above has changed, check the current instructions at
  <https://wikitech.wikimedia.org/wiki/Help:Toolforge/Web/Python>.
