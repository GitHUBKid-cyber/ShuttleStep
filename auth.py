"""Sign in with Google.

Sign-in turns on when a file called client_secret.json (downloaded from Google Cloud) sits next to app.py.
Without it, everyone uses ShuttleStep as a guest and their videos are remembered in their browser.
"""

import json
import os
import uuid

from authlib.integrations.flask_client import OAuth
from flask import Blueprint, redirect, render_template, request, session, url_for

import storage

CLIENT_SECRET_PATH = os.path.join(os.path.dirname(__file__), "client_secret.json")

bp = Blueprint("auth", __name__)
oauth = OAuth()


def init_app(app):
    oauth.init_app(app)
    if os.path.exists(CLIENT_SECRET_PATH):
        with open(CLIENT_SECRET_PATH) as f:
            secret = json.load(f)
        # Google's download wraps the keys in "web"; accept a plain file too.
        secret = secret.get("web", secret)
        oauth.register(
            name="google",
            client_id=secret["client_id"],
            client_secret=secret["client_secret"],
            server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
            client_kwargs={"scope": "openid email profile"},
        )
    app.register_blueprint(bp)
    app.context_processor(lambda: {"user": session.get("user"), "google_enabled": google_enabled()})


def google_enabled():
    return "google" in oauth._clients


def current_owner():
    """Who new videos belong to: the signed-in Google account, or this browser's guest id."""
    if "user" in session:
        return session["user"]["id"]
    if "guest_id" not in session:
        session["guest_id"] = "guest:" + uuid.uuid4().hex
        session.permanent = True
    return session["guest_id"]


@bp.route("/login")
def login():
    if not google_enabled():
        return render_template("message.html", title="Google sign-in isn't set up",
                               text="Add a client_secret.json file from Google Cloud to turn on sign-in. You can keep using ShuttleStep as a guest.")
    host = request.host.split(":")[0]
    # A public Tailscale Funnel link (https://<name>.ts.net) reaches the laptop as plain http, so ask Google to come back over https.
    if host.endswith(".ts.net"):
        redirect_uri = url_for("auth.callback", _external=True, _scheme="https")
    # Google only allows sign-in back to "localhost" for sites running on a laptop, not to a Wi-Fi address like 192.168.x.x.
    elif host in ("localhost", "127.0.0.1"):
        redirect_uri = url_for("auth.callback", _external=True).replace("127.0.0.1", "localhost")
    else:
        return render_template("message.html", title="Sign in on your laptop",
                               text="Google sign-in only works on the laptop running ShuttleStep (at localhost:8000). On your phone you can keep using ShuttleStep as a guest.")
    return oauth.google.authorize_redirect(redirect_uri)


@bp.route("/auth/callback")
def callback():
    token = oauth.google.authorize_access_token()
    info = token["userinfo"]
    user_id = "google:" + info["sub"]
    if "guest_id" in session:
        storage.move_analyses(session.pop("guest_id"), user_id)
    session["user"] = {"id": user_id, "name": info.get("given_name") or info.get("name") or info["email"],
                       "email": info["email"], "picture": info.get("picture")}
    session.permanent = True
    return redirect(url_for("videos"))


@bp.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("index"))
