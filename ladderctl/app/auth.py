import hmac
from functools import wraps
from flask import request, Response, current_app


def require_basicauth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        user = current_app.config["LADDERCTL_USERNAME"]
        pw = current_app.config["LADDERCTL_PASSWORD"]
        if not auth or not hmac.compare_digest(auth.username, user) or not hmac.compare_digest(auth.password, pw):
            return Response(
                "Authentication required",
                401,
                {"WWW-Authenticate": 'Basic realm="LadderCtl"'},
            )
        return f(*args, **kwargs)

    return decorated
