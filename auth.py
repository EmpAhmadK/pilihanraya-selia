import functools

import mwoauth
from flask import redirect, session, url_for

import storage
from config import OAUTH_CONSUMER_KEY, OAUTH_CONSUMER_SECRET, OAUTH_MWURI

consumer_token = mwoauth.ConsumerToken(OAUTH_CONSUMER_KEY, OAUTH_CONSUMER_SECRET)


def current_user():
    return session.get("username")


def current_access_token():
    """Returns an mwoauth.AccessToken for the logged-in user, or None."""
    key = session.get("access_token_key")
    secret = session.get("access_token_secret")
    if key and secret:
        return mwoauth.AccessToken(key, secret)
    return None


def login_required(view):
    @functools.wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user():
            return redirect(url_for("login"))
        if not storage.is_user_allowed(current_user()):
            return (
                "<div style='font-family:sans-serif;color:#eee;background:#111;"
                "padding:2rem'>Akaun Wikimedia anda (<b>%s</b>) belum "
                "disahkan untuk menggunakan alat ini. Sila hubungi "
                "pentadbir untuk dimasukkan ke dalam senarai putih."
                "</div>" % current_user()
            ), 403
        return view(*args, **kwargs)

    return wrapped


def admin_required(view):
    @functools.wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user():
            return redirect(url_for("login"))
        if not storage.is_user_admin(current_user()):
            return (
                "<div style='font-family:sans-serif;color:#eee;background:#111;"
                "padding:2rem'>Hanya pentadbir boleh mengakses halaman ini."
                "</div>"
            ), 403
        return view(*args, **kwargs)

    return wrapped
