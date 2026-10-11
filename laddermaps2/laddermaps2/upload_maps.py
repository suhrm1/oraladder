import argparse
import getpass
import json
import os
import re
import sys

import requests

BASE = "https://resource.openra.net"
CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".config", "openra-uploader")
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")


def parse_args(argv=None):
    """Parse and return CLI arguments.

    Accepts an optional argv list (defaults to sys.argv[1:]) for
    testability.  Returns a namespace with fields: files, username,
    parser, info, policy_cc, commercial, adaptations, config,
    no_interactive.
    """
    parser = argparse.ArgumentParser(
        description="Upload .oramap files to resource.openra.net",
    )
    parser.add_argument("files", nargs="*", metavar="FILE", help=".oramap file(s) to upload")
    parser.add_argument("--username", help="OpenRA Resource Center username")
    parser.add_argument("--parser", help="Parser version (e.g. playtest-20260222)")
    parser.add_argument("--info", help="Map description / info text")
    parser.add_argument("--policy-cc", choices=["cc_yes", "cc_no"], help="Creative Commons license")
    parser.add_argument("--commercial", choices=["com_yes", "com_no"], help="Allow commercial use")
    parser.add_argument(
        "--adaptations",
        choices=["adapt_yes", "adapt_no", "adapt_shared"],
        help="Allow adaptations",
    )
    parser.add_argument("--config", help=f"Config file path (default: {CONFIG_PATH})")
    parser.add_argument(
        "--no-interactive",
        action="store_true",
        help="Fail if required params are missing instead of prompting",
    )
    return parser.parse_args(argv)


def load_config(path):
    """Load a JSON config file from *path*.

    Returns a dict (possibly empty).  Missing or malformed files are
    treated as an empty config — never raises.
    """
    try:
        with open(path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_config(path, cfg):
    """Write *cfg* (dict) as JSON to *path*, creating parent dirs."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(cfg, f, indent=2)


def prompt_with_default(label, current_default, is_password=False):
    """Prompt the user for a value with an optional *current_default*.

    If *is_password* is True use getpass and never show a default.
    Returns the entered value, or *current_default* if the user just
    pressed Enter, or None when both are empty.
    """
    if is_password:
        prompt = f"{label}: "
        raw = getpass.getpass(prompt)
        return raw if raw else None
    if current_default:
        prompt = f"{label} [{current_default}]: "
    else:
        prompt = f"{label}: "
    raw = input(prompt).strip()
    return raw if raw else (current_default or None)


def login(session, username, password):
    """Authenticate with resource.openra.net.

    Fetches the login page to obtain a CSRF token, then POSTs the
    credentials.  Returns True on success (HTTP 302 to "/"), False
    otherwise.
    """
    r = session.get(f"{BASE}/login/")
    csrf = _extract_csrf(r.text)
    if not csrf:
        print("ERROR: Could not find CSRF token on login page", file=sys.stderr)
        sys.exit(1)
    r = session.post(
        f"{BASE}/login/",
        data={
            "csrfmiddlewaretoken": csrf,
            "ora_username": username,
            "ora_password": password,
            "ora_remember": "on",
        },
        allow_redirects=False,
    )
    if r.status_code == 302 and "/" in r.headers.get("Location", ""):
        print("Login OK")
        return True
    print(f"Login failed (HTTP {r.status_code})", file=sys.stderr)
    return False


def _extract_csrf(html):
    """Extract the Django CSRF token value from an HTML page.

    Returns the token string or None if not found.
    """
    m = re.search(r"name=['\"]csrfmiddlewaretoken['\"]\s+value=['\"]([^'\"]+)['\"]", html)
    return m.group(1) if m else None


def get_csrf_token(session):
    """Fetch the upload page and return a fresh CSRF token.

    The token is extracted from the page HTML.  Exits on failure since
    no further upload can succeed without it.
    """
    r = session.get(f"{BASE}/upload/map/")
    csrf = _extract_csrf(r.text)
    if not csrf:
        print("ERROR: Could not find CSRF token on upload page", file=sys.stderr)
        sys.exit(1)
    return csrf


def upload_file(session, filepath, parser, info, policy, csrf_token):
    """Upload a single .oramap file.

    Parameters
    ----------
    session : requests.Session
        Authenticated session.
    filepath : str
        Path to the .oramap file.
    parser : str
        OpenRA parser version tag (e.g. "playtest-20260222").
    info : str
        Map description text (may be empty).
    policy : dict
        License policy keys: policy_cc, commercial, adaptations.
    csrf_token : str
        Current CSRF token for the upload endpoint.

    Returns
    -------
    tuple
        ``(True, map_id, csrf_token)`` on success or
        ``(False, None, csrf_token)`` on failure, where *map_id* is
        the numeric resource center ID from the redirect Location.
    """
    fname = os.path.basename(filepath)
    print(f"  Uploading {fname} ...", end=" ", flush=True)
    with open(filepath, "rb") as f:
        r = session.post(
            f"{BASE}/upload/map/",
            files={"file": (fname, f, "application/zip")},
            data={
                "csrfmiddlewaretoken": csrf_token,
                "parser": parser,
                "info": info or "",
                **policy,
            },
            allow_redirects=False,
        )
    if r.status_code == 302:
        loc = r.headers.get("Location", "")
        map_id = loc.strip("/").split("/")[-1]
        print(f"OK ({map_id})")
        return True, map_id, csrf_token
    print(f"FAIL: HTTP {r.status_code}")
    m = re.search(r"error_response['\"]?\s*:\s*['\"]([^'\"]+)", r.text)
    if m:
        print(f"  Error: {m.group(1)}")
    else:
        print(f"  {r.text[:800]}")
    return False, None, csrf_token


def main():
    """Entry point: parse args, (prompt if interactive), log in, upload.

    Exit codes: 0 = all files uploaded, 1 = any failure.
    """
    args = parse_args()

    config_path = args.config or CONFIG_PATH
    cfg = load_config(config_path)

    policy_fields = ["policy_cc", "commercial", "adaptations"]

    if args.no_interactive:
        username = args.username or cfg.get("username")
        parser = args.parser or cfg.get("parser")
        info = args.info or ""
        policy = {k: (getattr(args, k) or cfg.get(k)) for k in policy_fields}
        if not username:
            print("ERROR: --username is required (or set in config)", file=sys.stderr)
            sys.exit(1)
        if not args.files:
            print("ERROR: at least one FILE argument required", file=sys.stderr)
            sys.exit(1)
        password = None
    else:
        print("=== OpenRA Resource Center Upload ===\n")
        username = prompt_with_default("Username", cfg.get("username"))
        password = prompt_with_default("Password", None, is_password=True)
        if password is None:
            password = getpass.getpass("Password: ")
        parser = prompt_with_default("Parser", cfg.get("parser") or "playtest-20260222")
        info = prompt_with_default("Info (description)", cfg.get("info", "")) or ""

        if not args.files:
            raw = input("File(s) to upload (space-separated, or drag-drop): ").strip()
            files = [f.strip().strip("'\"") for f in re.split(r"\s+", raw) if f.strip()]
        else:
            files = args.files

        for k in policy_fields:
            val = getattr(args, k) or cfg.get(k) or "cc_yes"
            setattr(args, k, val)

        policy = {k: getattr(args, k) for k in policy_fields}

        if not username:
            print("ERROR: username is required", file=sys.stderr)
            sys.exit(1)
        if not files:
            print("ERROR: at least one file required", file=sys.stderr)
            sys.exit(1)

        cfg["username"] = username
        cfg["parser"] = parser
        cfg["info"] = info
        for k in policy_fields:
            cfg[k] = getattr(args, k)
        save_config(config_path, cfg)

    s = requests.Session()
    if not login(s, username, password):
        sys.exit(1)

    csrf_token = get_csrf_token(s)

    ok = 0
    fail = 0
    ids = []
    for fp in files:
        fp = os.path.abspath(os.path.expanduser(fp.strip().strip("'\"")))
        if not os.path.isfile(fp):
            print(f"  SKIP: {fp} (not found)")
            fail += 1
            continue
        success, map_id, csrf_token = upload_file(s, fp, parser, info, policy, csrf_token)
        if success:
            ok += 1
            ids.append(map_id)
        else:
            fail += 1
        csrf_token = get_csrf_token(s)

    print(f"\nDone. {ok} uploaded, {fail} failed.")
    sys.exit(1 if fail else 0)
