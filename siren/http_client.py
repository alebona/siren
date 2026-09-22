# -*- coding: utf-8 -*-
"""
A tiny httpie-like HTTP client with local, replayable collections.
Built on urllib only (no requests/httpx dependency).

Usage:
    siren-http GET https://api.example.com/items
    siren-http POST https://api.example.com/items --json '{"name": "x"}'
    siren-http GET https://api.example.com/items --save my-request
    siren-http replay my-request
    siren-http list
"""
from __future__ import print_function

import argparse
import io
import json
import os
import sys

try:
    from urllib.request import Request, urlopen
    from urllib.error import HTTPError, URLError
except ImportError:  # Python 2
    from urllib2 import Request, urlopen, HTTPError, URLError

from ._cli import banner
from ._output import safe_print

# Some Python installs (notably Python 2.7 and old python.org builds on
# macOS) don't have their SSL module wired up to the system's trusted root
# certificates, so any HTTPS request fails with CERTIFICATE_VERIFY_FAILED
# even though the server's certificate is perfectly valid. certifi is a
# real dependency (see pyproject.toml) specifically so this always works,
# regardless of the platform's own certificate setup - relying on it
# happening to already be installed wasn't reliable enough for a paid
# feature. The try/except is just defensive (e.g. running from a source
# checkout before `pip install` has pulled it in).
try:
    import ssl
    import certifi
    _SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    _SSL_CONTEXT = None

try:
    text_type = unicode  # Python 2
except NameError:
    text_type = str  # Python 3

METHODS = ("GET", "POST", "PUT", "PATCH", "DELETE")


class _MethodRequest(Request):
    def __init__(self, url, data=None, headers=None, method=None):
        Request.__init__(self, url, data=data, headers=headers or {})
        self._method = method

    def get_method(self):
        if self._method:
            return self._method
        return Request.get_method(self)


def send(method, url, headers=None, json_body=None, data=None, timeout=10.0):
    """
    Perform an HTTP request and return {"status", "reason", "headers", "body"}.
    """
    headers = dict(headers or {})
    body_bytes = None

    if json_body is not None:
        body_bytes = json.dumps(json_body).encode("utf-8")
        headers.setdefault("Content-Type", "application/json")
    elif data is not None:
        body_bytes = data if isinstance(data, bytes) else data.encode("utf-8")

    request = _MethodRequest(url, data=body_bytes, headers=headers, method=method)

    try:
        response = urlopen(request, timeout=timeout, context=_SSL_CONTEXT)
        try:
            status = response.getcode()
            reason = getattr(response, "reason", "")
            resp_headers = list(response.info().items())
            raw_body = response.read()
        finally:
            response.close()
    except HTTPError as e:
        try:
            status = e.code
            reason = getattr(e, "reason", "")
            resp_headers = list(e.headers.items()) if e.headers else []
            raw_body = e.read()
        finally:
            e.close()

    try:
        body_text = raw_body.decode("utf-8")
    except UnicodeDecodeError:
        body_text = raw_body.decode("utf-8", errors="replace")

    return {"status": status, "reason": reason, "headers": resp_headers, "body": body_text}


def _format_body(body_text):
    try:
        parsed = json.loads(body_text)
    except ValueError:
        return body_text
    return json.dumps(parsed, indent=2, ensure_ascii=False)


def _collections_dir():
    path = os.path.join(os.path.expanduser("~"), ".siren", "http_collections")
    if not os.path.isdir(path):
        os.makedirs(path)
    return path


def _collection_path(name):
    return os.path.join(_collections_dir(), "{}.json".format(name))


def save_collection(name, method, url, headers=None, json_body=None, data=None):
    payload = {
        "method": method,
        "url": url,
        "headers": headers or {},
        "json": json_body,
        "data": data,
    }
    content = json.dumps(payload, indent=2)
    if not isinstance(content, text_type):
        content = content.decode("utf-8")
    with io.open(_collection_path(name), "w", encoding="utf-8") as f:
        f.write(content)


def load_collection(name):
    path = _collection_path(name)
    if not os.path.exists(path):
        return None
    with io.open(path, "r", encoding="utf-8") as f:
        return json.loads(f.read())


def list_collections():
    directory = _collections_dir()
    names = [f[:-5] for f in os.listdir(directory) if f.endswith(".json")]
    return sorted(names)


def _parse_header(raw):
    if ":" not in raw:
        raise ValueError("Header must be in 'Key: Value' format, got: {}".format(raw))
    key, value = raw.split(":", 1)
    return key.strip(), value.strip()


def _print_response(result):
    safe_print(banner("HTTP", "{} {}".format(result["status"], result["reason"]).strip()))
    for key, value in result["headers"]:
        safe_print(banner("HTTP", "  {}: {}".format(key, value)))
    safe_print(banner("HTTP", "body:"))
    for line in _format_body(result["body"]).split("\n"):
        safe_print(banner("HTTP", "  {}".format(line)))


def main():
    parser = argparse.ArgumentParser(prog="siren-http")
    subparsers = parser.add_subparsers(dest="command")

    for method in METHODS:
        p = subparsers.add_parser(method)
        p.add_argument("url")
        p.add_argument("-H", "--header", action="append", default=[], dest="headers")
        body_group = p.add_mutually_exclusive_group()
        body_group.add_argument("--json")
        body_group.add_argument("--data")
        p.add_argument("--timeout", type=float, default=10.0)
        p.add_argument("--save")

    replay_parser = subparsers.add_parser("replay")
    replay_parser.add_argument("name")

    subparsers.add_parser("list")

    args = parser.parse_args()

    if args.command in METHODS:
        try:
            headers = dict(_parse_header(h) for h in args.headers)
        except ValueError as e:
            safe_print(banner("HTTP", "Error: {}".format(e)))
            sys.exit(1)

        json_body = json.loads(args.json) if args.json else None

        if args.save:
            save_collection(args.save, args.command, args.url, headers, json_body, args.data)
            safe_print(banner("HTTP", "saved as '{}'".format(args.save)))

        try:
            result = send(args.command, args.url, headers, json_body, args.data, args.timeout)
        except URLError as e:
            safe_print(banner("HTTP", "Error: {}".format(e)))
            sys.exit(1)

        _print_response(result)

    elif args.command == "replay":
        collection = load_collection(args.name)
        if collection is None:
            safe_print(banner("HTTP", "no saved request named '{}'".format(args.name)))
            sys.exit(1)

        try:
            result = send(
                collection["method"], collection["url"], collection["headers"],
                collection["json"], collection["data"],
            )
        except URLError as e:
            safe_print(banner("HTTP", "Error: {}".format(e)))
            sys.exit(1)

        _print_response(result)

    elif args.command == "list":
        names = list_collections()
        if not names:
            safe_print(banner("HTTP", "no saved requests yet"))
        for name in names:
            safe_print(banner("HTTP", name))

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
