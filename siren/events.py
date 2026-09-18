# -*- coding: utf-8 -*-
"""
Report exceptions to your siren pro workspace, and browse them.

Usage:
    try:
        risky()
    except Exception:
        siren.report()  # uses sys.exc_info()

CLI:
    siren-events list
    siren-events show <id>
"""
from __future__ import print_function

import argparse
import json
import sys
import traceback

from . import account, http_client
from .http_client import URLError
from ._cli import banner
from ._output import safe_print


def report(exc=None, label=None):
    """
    Send an exception to your siren pro workspace. Safe to call even if
    not logged in or offline - prints a local message and returns instead
    of raising, so it never breaks the caller's error handling.
    """
    creds = account.load_credentials()
    if creds is None:
        safe_print(banner("EVENTS", "not logged in - run 'siren-login signup <email>' first"))
        return None

    if exc is None:
        exc_type, exc_value, exc_tb = sys.exc_info()
    else:
        exc_type, exc_value, exc_tb = type(exc), exc, getattr(exc, "__traceback__", None)

    if exc_type is None:
        safe_print(banner("EVENTS", "siren.report() called with no active exception"))
        return None

    formatted_tb = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))

    context_file = None
    context_line = None
    if exc_tb is not None:
        last = exc_tb
        while last.tb_next is not None:
            last = last.tb_next
        context_file = last.tb_frame.f_code.co_filename
        context_line = last.tb_lineno

    payload = {
        "exc_type": exc_type.__name__,
        "message": str(exc_value),
        "traceback": formatted_tb,
        "context_file": context_file,
        "context_line": context_line,
        "label": label,
    }

    try:
        result = http_client.send(
            "POST", creds["api_url"] + "/events",
            headers={"Authorization": "Bearer {}".format(creds["api_key"])},
            json_body=payload,
        )
    except Exception as e:
        safe_print(banner("EVENTS", "could not reach siren-pro: {}".format(e)))
        return None

    if result["status"] != 200:
        safe_print(banner("EVENTS", "report failed ({}): {}".format(result["status"], result["body"])))
        return None

    body = json.loads(result["body"])
    safe_print(banner("EVENTS", "reported {} (id={})".format(exc_type.__name__, body["id"])))
    return body["id"]


def _require_credentials():
    creds = account.load_credentials()
    if creds is None:
        safe_print(banner("EVENTS", "not logged in - run 'siren-login signup <email>' first"))
        sys.exit(1)
    return creds


def _send_or_exit(api_url, *args, **kwargs):
    try:
        return http_client.send(*args, **kwargs)
    except URLError as e:
        safe_print(banner("EVENTS", "Could not reach siren-pro at {} - is it running? ({})".format(api_url, e)))
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(prog="siren-events")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("list")

    show_parser = subparsers.add_parser("show")
    show_parser.add_argument("id", type=int)

    args = parser.parse_args()

    if args.command == "list":
        creds = _require_credentials()
        result = _send_or_exit(
            creds["api_url"], "GET", creds["api_url"] + "/events",
            headers={"Authorization": "Bearer {}".format(creds["api_key"])},
        )
        if result["status"] != 200:
            safe_print(banner("EVENTS", "Error ({}): {}".format(result["status"], result["body"])))
            sys.exit(1)

        events = json.loads(result["body"])
        if not events:
            safe_print(banner("EVENTS", "no events yet"))
        for event in events:
            label = " [{}]".format(event["label"]) if event.get("label") else ""
            safe_print(banner("EVENTS", "#{} {} - {}{} ({})".format(
                event["id"], event["exc_type"], event["message"], label, event["created_at"]
            )))

    elif args.command == "show":
        creds = _require_credentials()
        result = _send_or_exit(
            creds["api_url"], "GET", "{}/events/{}".format(creds["api_url"], args.id),
            headers={"Authorization": "Bearer {}".format(creds["api_key"])},
        )
        if result["status"] != 200:
            safe_print(banner("EVENTS", "Error ({}): {}".format(result["status"], result["body"])))
            sys.exit(1)

        event = json.loads(result["body"])
        safe_print(banner("EVENTS", "#{} {} - {}".format(event["id"], event["exc_type"], event["message"])))
        if event.get("context_file"):
            safe_print(banner("EVENTS", "  at {}:{}".format(event["context_file"], event["context_line"])))
        if event.get("traceback"):
            for line in event["traceback"].rstrip("\n").split("\n"):
                safe_print(banner("EVENTS", "  {}".format(line)))

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
