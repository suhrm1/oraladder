import os
from functools import wraps
from uuid import uuid4

import hashlib

from flask import request, abort, Flask, Response, current_app, session

# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------


def create_app():
    """Build and configure the Flask application instance.

    Reads configuration from ``LADDER_*`` environment variables
    (via ``from_prefixed_env``).  Falls back to auto-generated values for
    ``SECRET_KEY``, ``LADDER_API_KEY``, and ``LADDER_ADMIN_PASSWORD`` when
    the corresponding env vars are not set.
    """
    app = Flask(__name__)
    app.config.from_prefixed_env()

    if "LADDER_API_KEY" not in app.config.keys():
        _api_key = uuid4().hex
        app.config["LADDER_API_KEY"] = _api_key
        print(f"Ladder admin API key generated:\n\n{_api_key}\n\n")
        del _api_key

    if "LADDER_ADMIN_USERNAME" not in app.config:
        app.config["LADDER_ADMIN_USERNAME"] = "admin"

    if "LADDER_ADMIN_PASSWORD" not in app.config:
        app.config["LADDER_ADMIN_PASSWORD"] = uuid4().hex[:16]
        print(
            f"Admin UI password generated:\n\n"
            f"  username: {app.config['LADDER_ADMIN_USERNAME']}\n"
            f"  password: {app.config['LADDER_ADMIN_PASSWORD']}\n\n"
        )

    if not app.config.get("SECRET_KEY"):
        app.config["SECRET_KEY"] = uuid4().hex

    app.secret_key = app.config["SECRET_KEY"]
    app.logger.setLevel(str(os.environ.get("LOG_LEVEL", "INFO")).upper())
    return app


# ---------------------------------------------------------------------------
# Authentication: API key (REST endpoints)
# ---------------------------------------------------------------------------


def api_key_authn(keys: [str]):
    """Decorator that requires a valid API key for the wrapped view.

    The caller supplies the key via one of three locations (checked in
    order):

    * ``request.json["api_key"]`` – when the body is JSON
    * ``request.args["api_key"]`` – query string
    * ``request.form["api_key"]`` – form-encoded POST body
    """

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            invalid_msg = "Invalid API key provided"
            missing_msg = "Invalid API key provided"
            if request.is_json:
                if "api_key" not in request.get_json().keys():
                    abort(401, missing_msg)
                if request.get_json()["api_key"] not in keys:
                    abort(401, invalid_msg)
            elif "api_key" in request.args:
                if request.args["api_key"] not in keys:
                    abort(401, invalid_msg)
            else:
                if "api_key" not in request.form.keys():
                    abort(401, missing_msg)
                if request.form.get("api_key") not in keys:
                    abort(401, invalid_msg)
            return f(*args, **kwargs)

        return decorated_function

    return decorator


# ---------------------------------------------------------------------------
# Authentication: HTTP BasicAuth (admin UI)
# ---------------------------------------------------------------------------


def require_basicauth(f):
    """Decorator that enforces HTTP Basic Authentication on admin views.

    Credentials are matched against the ``LADDER_ADMIN_USERNAME`` and
    ``LADDER_ADMIN_PASSWORD`` config values.
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth = request.authorization
        expected_user = current_app.config.get("LADDER_ADMIN_USERNAME", "admin")
        expected_pass = current_app.config.get("LADDER_ADMIN_PASSWORD", "")
        if not auth or auth.username != expected_user or auth.password != expected_pass:
            return Response(
                "Authentication required",
                401,
                {"WWW-Authenticate": 'Basic realm="Admin UI"'},
            )
        return f(*args, **kwargs)

    return decorated_function


# ---------------------------------------------------------------------------
# CSRF token helpers (admin UI)
# ---------------------------------------------------------------------------


def _csrf_token_key():
    """Return the session key used to store the current CSRF token."""
    return hashlib.sha256(f"_csrf_token_{current_app.secret_key}".encode()).hexdigest()


def generate_csrf_token():
    """Return a CSRF token, creating one if it does not yet exist."""
    if _csrf_token_key() not in session:
        session[_csrf_token_key()] = uuid4().hex
    return session[_csrf_token_key()]


def validate_csrf(f):
    """Decorator that validates the ``_csrf_token`` form field against the
    token stored in the session.  Must be applied **after**
    ``@require_basicauth`` so authentication is checked first.
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.form.get("_csrf_token", "")
        expected = session.get(_csrf_token_key())
        if not expected or token != expected:
            abort(403, "CSRF token validation failed")
        return f(*args, **kwargs)

    return decorated_function
