"""
Very small JSON-file backed storage.

This is intentionally simple (no database server needed) since the data
involved (a handful of elections, a whitelist of a few dozen users) is tiny
and changes rarely. If you outgrow this, migrating to Toolforge's ToolsDB
(MariaDB) or an sqlite file is straightforward.
"""
import json
import os
import threading

from config import ELECTIONS_FILE, WHITELIST_FILE, INITIAL_ADMINS

_lock = threading.Lock()


def _load(path, default):
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


# ---------------------------------------------------------------- elections

def get_elections():
    with _lock:
        return _load(ELECTIONS_FILE, {})


def get_election(qid):
    return get_elections().get(qid)


def save_election(qid, name, seats):
    """seats: list of {"kod": ..., "nama": ..., "qid": ...}"""
    with _lock:
        data = _load(ELECTIONS_FILE, {})
        data[qid] = {"name": name, "qid": qid, "seats": seats}
        _save(ELECTIONS_FILE, data)


def delete_election(qid):
    with _lock:
        data = _load(ELECTIONS_FILE, {})
        data.pop(qid, None)
        _save(ELECTIONS_FILE, data)


# ---------------------------------------------------------------- whitelist

def get_whitelist():
    with _lock:
        data = _load(WHITELIST_FILE, None)
        if data is None:
            data = {"users": {u: {"admin": True} for u in INITIAL_ADMINS}}
            _save(WHITELIST_FILE, data)
        return data


def is_user_allowed(username):
    if not username:
        return False
    wl = get_whitelist()
    return username in wl.get("users", {})


def is_user_admin(username):
    if not username:
        return False
    wl = get_whitelist()
    u = wl.get("users", {}).get(username)
    return bool(u and u.get("admin"))


def add_user(username, admin=False):
    username = username.strip()
    with _lock:
        data = _load(WHITELIST_FILE, {"users": {}})
        data.setdefault("users", {})[username] = {"admin": bool(admin)}
        _save(WHITELIST_FILE, data)


def remove_user(username):
    with _lock:
        data = _load(WHITELIST_FILE, {"users": {}})
        data.get("users", {}).pop(username, None)
        _save(WHITELIST_FILE, data)


def list_users():
    return get_whitelist().get("users", {})
