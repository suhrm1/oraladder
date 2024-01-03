from functools import wraps
from uuid import uuid4

from flask import request, abort, Flask, g


def create_app():
    app = Flask(__name__)
    app.config.from_prefixed_env()
    if "LADDER_API_KEY" not in app.config.keys():
        _api_key = uuid4().hex
        app.config["LADDER_API_KEY"] = _api_key
        print(f"Ladder admin API key generated:\n\n{_api_key}\n\n")
        del _api_key
    return app


def api_key_authn(keys: [str]):
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
