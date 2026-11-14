# -*- coding: utf-8 -*-
"""
JSON bridge used by the VS Code extension. Reads one request from stdin,
{"op": "<name>", "args": {...}}, and writes one response to stdout:
{"ok": true, "result": ...} or {"ok": false, "error": "..."}.

Each op wraps an existing siren function, so the extension shows the same
results the old command-line tools printed.

    python -m siren._bridge < request.json
"""
from __future__ import print_function

import io
import json
import os
import sys

from . import account, http_client, quality, scaffold, snippets


def _quality_file(path, threshold):
    with io.open(path, "r", encoding="utf-8") as f:
        source = f.read()
    issues = []
    dead = quality.find_dead_code(source, path)
    for name, line in dead["unused_imports"]:
        issues.append({"line": line, "kind": "unused-import", "message": "'{}' is imported but never used".format(name), "name": name})
    for name, line in dead["unused_defs"]:
        issues.append({"line": line, "kind": "unused-def", "message": "'{}' is never used in this file".format(name), "name": name})
    for kind, line, message in quality.find_lint_issues(source, path):
        issues.append({"line": line, "kind": kind, "message": message})
    for name, line, score in quality.find_complexity(source, path):
        if score > threshold:
            issues.append({
                "line": line, "kind": "complexity", "score": score, "name": name,
                "message": "'{}' has cyclomatic complexity {} (threshold {})".format(name, score, threshold),
            })
    return issues


def op_quality(args):
    threshold = int(args.get("threshold", 10))
    files = []
    unparseable = []
    for path in quality._iter_py_files(args["path"]):
        try:
            files.append({"file": os.path.abspath(path), "issues": _quality_file(path, threshold)})
        except (SyntaxError, ValueError, UnicodeDecodeError) as e:
            unparseable.append({"file": os.path.abspath(path), "error": str(e)})
    return {"files": files, "unparseable": unparseable}


def op_scaffold(args):
    return [os.path.abspath(p) for p in scaffold.generate(args["template"], args["name"], args["path"])]


def op_scaffold_templates(args):
    return sorted(scaffold.TEMPLATES)


def op_snippets_list(args):
    result = []
    for name in snippets.list_snippets():
        meta = snippets.metadata(name)
        result.append({
            "name": name,
            "tags": meta.get("tags", []),
            "updated_at": meta.get("updated_at"),
            "content": snippets.show(name) or "",
            "path": snippets._snippet_path(name),
        })
    return result


def op_snippets_save(args):
    snippets.save(args["name"], args.get("content", ""), tags=args.get("tags"), force=args.get("force", False))
    return snippets._snippet_path(args["name"])


def op_snippets_set_tags(args):
    content = snippets.show(args["name"])
    if content is None:
        raise ValueError("Snippet '{}' not found".format(args["name"]))
    snippets.save(args["name"], content, tags=args["tags"], force=True)
    return True


def op_snippets_remove(args):
    return snippets.remove(args["name"])


def op_snippets_rename(args):
    return snippets.rename(args["old"], args["new"], force=args.get("force", False))


def op_snippets_export(args):
    return snippets.export_snippets(args["path"])


def op_snippets_import(args):
    return snippets.import_snippets(args["path"], force=args.get("force", False))


def op_http_send(args):
    return http_client.send(
        args["method"], args["url"],
        headers=args.get("headers"), json_body=args.get("json"), data=args.get("data"),
        timeout=float(args.get("timeout", 30.0)),
    )


def op_http_list(args):
    result = []
    for name in http_client.list_collections():
        entry = http_client.load_collection(name) or {}
        result.append({
            "name": name,
            "method": entry.get("method", "GET"),
            "url": entry.get("url", ""),
            "path": http_client._collection_path(name),
        })
    return result


def op_http_load(args):
    return http_client.load_collection(args["name"])


def op_http_save(args):
    http_client.save_collection(
        args["name"], args["method"], args["url"],
        headers=args.get("headers"), json_body=args.get("json"), data=args.get("data"),
    )
    return http_client._collection_path(args["name"])


def op_http_remove(args):
    path = http_client._collection_path(args["name"])
    if os.path.exists(path):
        os.remove(path)
        return True
    return False


def op_account_status(args):
    creds = account.load_credentials()
    if creds is None:
        return {"logged_in": False}
    status = account.validate() or {}
    return {"logged_in": True, "email": creds.get("email"), "status": status}


def op_account_signup(args):
    return account.signup(args["email"])


def op_account_use_key(args):
    return account.use_key(args["api_key"])


def op_account_logout(args):
    return account.clear_credentials()


def op_account_upgrade(args):
    return account.upgrade(args.get("currency") or None)


def op_account_currency(args):
    return account.detect_currency()


def op_account_invite(args):
    return account.invite(args["email"])


def op_account_webhook(args):
    return account.set_webhook(args.get("url", ""))


def _pro_get(path):
    creds = account.load_credentials()
    if creds is None:
        raise RuntimeError("not logged in")
    result = account._send(
        creds["api_url"], "GET", creds["api_url"] + path,
        headers={"Authorization": "Bearer {}".format(creds["api_key"])},
    )
    if result["status"] != 200:
        raise RuntimeError("{} {}".format(result["status"], result["body"]))
    return json.loads(result["body"])


def op_events_list(args):
    return _pro_get("/events")


def op_events_show(args):
    return _pro_get("/events/{}".format(int(args["id"])))


def op_perf_top(args):
    return _pro_get("/metrics/top?hours={}&limit={}".format(int(args.get("hours", 24)), int(args.get("limit", 20))))


def op_perf_list(args):
    path = "/metrics/list?limit={}".format(int(args.get("limit", 50)))
    if args.get("name"):
        try:
            from urllib.parse import quote
        except ImportError:  # Python 2
            from urllib import quote
        path += "&name={}".format(quote(args["name"]))
    return _pro_get(path)


OPS = dict((name[3:], fn) for name, fn in globals().items() if name.startswith("op_"))


def handle(request):
    op = request.get("op")
    if op not in OPS:
        return {"ok": False, "error": "unknown op: {}".format(op)}
    try:
        return {"ok": True, "result": OPS[op](request.get("args") or {})}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def main():
    raw = sys.stdin.read()
    if not isinstance(raw, type(u"")):
        raw = raw.decode("utf-8")
    response = handle(json.loads(raw))
    # ASCII-only JSON survives any console encoding.
    sys.stdout.write(json.dumps(response, ensure_ascii=True))
    sys.stdout.flush()


if __name__ == "__main__":
    main()
