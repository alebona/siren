# -*- coding: utf-8 -*-
"""
Account management for siren pro features: signup, key management, status.

Usage:
    siren-login signup <email>
    siren-login use-key <api_key>
    siren-login status
    siren-login logout
"""
from __future__ import print_function

import argparse
import io
import json
import os
import sys

from . import http_client
from .http_client import URLError
from ._cli import banner
from ._output import safe_print

try:
    text_type = unicode  # Python 2
except NameError:
    text_type = str  # Python 3

DEFAULT_API_URL = "https://siren-pro.onrender.com"


def _credentials_path():
    directory = os.path.join(os.path.expanduser("~"), ".siren")
    if not os.path.isdir(directory):
        os.makedirs(directory)
    return os.path.join(directory, "credentials.json")


def _api_url():
    return os.environ.get("SIREN_API_URL", DEFAULT_API_URL)


def load_credentials():
    path = _credentials_path()
    if not os.path.exists(path):
        return None
    with io.open(path, "r", encoding="utf-8") as f:
        return json.loads(f.read())


def save_credentials(api_key, email=None):
    payload = {"api_key": api_key, "api_url": _api_url(), "email": email}
    content = json.dumps(payload, indent=2)
    if not isinstance(content, text_type):
        content = content.decode("utf-8")
    with io.open(_credentials_path(), "w", encoding="utf-8") as f:
        f.write(content)
    return payload


def clear_credentials():
    path = _credentials_path()
    if not os.path.exists(path):
        return False
    os.remove(path)
    return True


def _send(api_url, *args, **kwargs):
    # Render's free tier sleeps after inactivity and can take 30-60s to
    # wake on the first request - the default 10s timeout in http_client
    # would misreport that as "unreachable" instead of "just slow".
    kwargs.setdefault("timeout", 60.0)
    try:
        return http_client.send(*args, **kwargs)
    except URLError as e:
        raise RuntimeError("Could not reach siren-pro at {} - is it running? ({})".format(api_url, e))


def signup(email):
    api_url = _api_url()
    result = _send(api_url, "POST", api_url + "/auth/signup", json_body={"email": email})
    if result["status"] != 200:
        raise RuntimeError("Signup failed ({}): {}".format(result["status"], result["body"]))
    body = json.loads(result["body"])
    save_credentials(body["api_key"], email=email)
    return body


def use_key(api_key):
    api_url = _api_url()
    result = _send(
        api_url, "GET", api_url + "/licenses/validate",
        headers={"Authorization": "Bearer {}".format(api_key)},
    )
    if result["status"] != 200:
        raise RuntimeError("Invalid API key ({}): {}".format(result["status"], result["body"]))
    save_credentials(api_key)
    return json.loads(result["body"])


def validate():
    """Check the stored credentials against the backend. None if not logged in."""
    creds = load_credentials()
    if creds is None:
        return None
    try:
        result = _send(
            creds["api_url"], "GET", creds["api_url"] + "/licenses/validate",
            headers={"Authorization": "Bearer {}".format(creds["api_key"])},
        )
    except RuntimeError as e:
        return {"active": False, "error": str(e)}
    if result["status"] != 200:
        return {"active": False, "error": "{} {}".format(result["status"], result["body"])}
    return json.loads(result["body"])


def main():
    parser = argparse.ArgumentParser(prog="siren-login")
    subparsers = parser.add_subparsers(dest="command")

    signup_parser = subparsers.add_parser("signup")
    signup_parser.add_argument("email")

    use_key_parser = subparsers.add_parser("use-key")
    use_key_parser.add_argument("api_key")

    subparsers.add_parser("status")
    subparsers.add_parser("logout")

    args = parser.parse_args()

    if args.command == "signup":
        try:
            body = signup(args.email)
        except Exception as e:
            safe_print(banner("LOGIN", "Error: {}".format(e)))
            sys.exit(1)
        safe_print(banner("LOGIN", "signed up as {} (workspace {})".format(args.email, body["workspace_id"])))

    elif args.command == "use-key":
        try:
            status = use_key(args.api_key)
        except Exception as e:
            safe_print(banner("LOGIN", "Error: {}".format(e)))
            sys.exit(1)
        safe_print(banner("LOGIN", "key saved, plan={} active={}".format(status["plan"], status["active"])))

    elif args.command == "status":
        creds = load_credentials()
        if creds is None:
            safe_print(banner("LOGIN", "not logged in"))
            sys.exit(1)

        status = validate()
        if status is None or status.get("error"):
            error = status.get("error") if status else "no response"
            safe_print(banner("LOGIN", "logged in as {} but validation failed: {}".format(
                creds.get("email") or "(unknown)", error
            )))
            sys.exit(1)

        safe_print(banner("LOGIN", "{} plan={} active={}".format(
            creds.get("email") or "(unknown)", status["plan"], status["active"]
        )))

    elif args.command == "logout":
        removed = clear_credentials()
        safe_print(banner("LOGIN", "logged out" if removed else "was not logged in"))

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
