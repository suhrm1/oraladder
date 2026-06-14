import os
import secrets
import uuid

from flask import Flask

from .routes import bp


def create_app():
    app = Flask(__name__, template_folder="../templates")
    app.secret_key = os.environ.get("SECRET_KEY", uuid.uuid4().hex)
    app.config.from_prefixed_env()

    pw = os.environ.get("LADDERCTL_PASSWORD")
    if not pw:
        pw = secrets.token_urlsafe(24)
        app.logger.warning("LADDERCTL_PASSWORD not set – one-time password generated")
    app.config["LADDERCTL_PASSWORD"] = pw
    app.config["LADDERCTL_USERNAME"] = os.environ.get("LADDERCTL_USERNAME", "admin")

    app.register_blueprint(bp)

    return app
