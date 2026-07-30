import json
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# --------------------------------------------------------------------------
# Optional local secrets file. This is the easiest way to configure the tool
# on Toolforge without having to fight with environment variables: create a
# file called secrets.json (NOT committed to git - it's in .gitignore)
# next to this config.py, shaped like:
#
# {
#   "OAUTH_CONSUMER_KEY": "....",
#   "OAUTH_CONSUMER_SECRET": "....",
#   "FLASK_SECRET_KEY": "any-long-random-string",
#   "INITIAL_ADMINS": "YourWikimediaUsername"
# }
#
# Values here are only used as a fallback if the corresponding environment
# variable isn't set, so real env vars (if you do set them) always win.
_SECRETS_FILE = os.path.join(BASE_DIR, "secrets.json")
_secrets = {}
if os.path.exists(_SECRETS_FILE):
    with open(_SECRETS_FILE, "r", encoding="utf-8") as _f:
        _secrets = json.load(_f)


def _get(name, default=""):
    return os.environ.get(name, _secrets.get(name, default))

# On Toolforge you should point this at a persistent, non-web-readable
# location, e.g. os.path.expanduser("~/data"). Kept local by default so the
# tool also works out of the box for local testing.
DATA_DIR = os.environ.get("NS_TOOL_DATA_DIR", os.path.join(BASE_DIR, "data"))
os.makedirs(DATA_DIR, exist_ok=True)

ELECTIONS_FILE = os.path.join(DATA_DIR, "elections.json")
WHITELIST_FILE = os.path.join(DATA_DIR, "whitelist.json")

# Register a consumer at:
# https://meta.wikimedia.org/wiki/Special:OAuthConsumerRegistration/propose
# "This consumer is for use only by <yourtoolname>" is fine, grants needed:
#   - Basic rights
#   - High-volume (bot) editing  [optional, but recommended]
#   - Edit existing pages
#   - Create, edit, and move pages  (Wikidata items count as pages)
# Callback URL: https://<tool-name>.toolforge.org/oauth-callback
OAUTH_CONSUMER_KEY = _get("OAUTH_CONSUMER_KEY", "")
OAUTH_CONSUMER_SECRET = _get("OAUTH_CONSUMER_SECRET", "")

# mwoauth needs an index.php URL on the wiki that issues the OAuth tokens.
# Wikidata OAuth is centralised via Meta-Wiki.
OAUTH_MWURI = "https://meta.wikimedia.org/w/index.php"

WIKIDATA_API_URL = "https://www.wikidata.org/w/api.php"
WIKIDATA_ENTITY_DATA_URL = "https://www.wikidata.org/wiki/Special:EntityData"

# Flask session signing key. MUST be overridden via environment variable in
# production (put it in a file only you can read and export it before
# starting the webservice, see README.md).
SECRET_KEY = _get("FLASK_SECRET_KEY", "please-change-this-secret-key")

# Bootstrap administrator(s). Only used the very first time the tool runs
# (i.e. before data/whitelist.json exists). Put your own Wikidata/Wikimedia
# username(s) here before first deployment.
INITIAL_ADMINS = [u.strip() for u in _get("INITIAL_ADMINS", "").split(",") if u.strip()]

USER_AGENT = "NSElectionTool/1.0 (Toolforge; https://toolforge.org)"
