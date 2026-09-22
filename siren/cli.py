# -*- coding: utf-8 -*-
"""
siren - overview of every siren-* command: what it does and which area it
belongs to. Run any individual command with --help for its full usage
(e.g. `siren-scaffold --help`); this one just points you to the right tool.

Usage:
    siren
    siren --help
    siren debug          # filter to one category
    siren snippet         # or filter by a (partial) command name
"""
from __future__ import print_function

import sys

from ._cli import COLOR, RESET
from ._output import safe_print

# (name, category, description)
COMMANDS = [
    ("siren()", "debug", "print/pprint a value with file and line context"),
    ("siren.trace", "debug", "decorator that logs a function's calls, args, return value, and exceptions"),
    ("siren.diff", "debug", "compare two objects (dict/list/object) and show what changed"),
    ("siren.breakpoint", "debug", "pause execution and print local variables"),
    ("siren.memory", "debug", "print current/peak traced memory usage"),
    ("siren.catch", "debug", "context manager: print a formatted traceback, then re-raise"),
    ("siren-clean", "debug", "remove siren(...) debug calls from a project automatically"),
    ("siren-autoload", "debug", "use siren anywhere without importing it (on/off/status)"),
    ("siren-scaffold", "productivity", "generate a file/project skeleton (script, package, class, dataclass, test)"),
    ("siren-env", "productivity", "compare .env against .env.example, report missing/extra keys"),
    ("siren-snippet", "productivity", "save, tag, search, and recall code snippets from the terminal"),
    ("siren-http", "http", "httpie-like HTTP client with saved, replayable request collections"),
    ("siren.patch_requests", "http", "log every call made through the requests library"),
    ("siren.patch_httpx", "http", "log every call made through the httpx library"),
    ("siren-quality", "quality", "local checks: dead code, lint issues, cyclomatic complexity"),
    ("siren-login", "pro", "pro account: signup, upgrade, team invites, webhook notifications"),
    ("siren-events", "pro", "browse exceptions captured via siren.report() (pro tier)"),
]

CATEGORY_ORDER = ["debug", "productivity", "http", "quality", "pro"]
CATEGORY_LABELS = {
    "debug": "Debug & profiling",
    "productivity": "CLI productivity",
    "http": "API / HTTP",
    "quality": "Code quality",
    "pro": "Pro tier",
}


def _matches(entry, query):
    name, category, description = entry
    query = query.lower()
    return query == category.lower() or query in name.lower()


def main():
    query = None
    for arg in sys.argv[1:]:
        if arg in ("-h", "--help"):
            continue
        query = arg
        break

    entries = COMMANDS
    if query:
        entries = [e for e in COMMANDS if _matches(e, query)]
        if not entries:
            valid = ", ".join(CATEGORY_ORDER)
            safe_print("no command or category matches '{}' (categories: {})".format(query, valid))
            sys.exit(1)

    by_category = {}
    for name, category, description in entries:
        by_category.setdefault(category, []).append((name, description))

    width = max(len(name) for name, _category, _description in entries)

    safe_print("{}siren-debug{} - a Python dev toolbelt\n".format(COLOR, RESET))
    for category in CATEGORY_ORDER:
        if category not in by_category:
            continue
        safe_print("{}{}{}".format(COLOR, CATEGORY_LABELS[category], RESET))
        for name, description in by_category[category]:
            safe_print("  {:<{width}}  {}".format(name, description, width=width))
        safe_print("")

    safe_print("Run any command with --help for its full usage (e.g. siren-scaffold --help).")
    safe_print("Filter this list: siren <category|command> (e.g. siren pro, siren snippet).")


if __name__ == "__main__":
    main()
