# -*- coding: utf-8 -*-
"""
Save and recall small code/text snippets from the terminal.

Usage:
    echo "some code" | siren-snippet save my-snippet --tag sql
    siren-snippet show my-snippet
    siren-snippet copy my-snippet
    siren-snippet list [--tag sql]
    siren-snippet search some-term
    siren-snippet remove my-snippet
"""
from __future__ import print_function

import argparse
import io
import json
import os
import subprocess
import sys
from datetime import datetime

from ._cli import banner
from ._output import safe_print

try:
    text_type = unicode  # Python 2
except NameError:
    text_type = str  # Python 3

try:
    from shutil import which as _which  # Python 3.3+
except ImportError:
    def _which(cmd):
        for directory in os.environ.get("PATH", "").split(os.pathsep):
            candidate = os.path.join(directory, cmd)
            if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                return candidate
        return None


def _snippets_dir():
    path = os.path.join(os.path.expanduser("~"), ".siren", "snippets")
    if not os.path.isdir(path):
        os.makedirs(path)
    return path


def _snippet_path(name):
    return os.path.join(_snippets_dir(), "{}.txt".format(name))


def _index_path():
    return os.path.join(_snippets_dir(), "_index.json")


def _load_index():
    path = _index_path()
    if not os.path.exists(path):
        return {}
    with io.open(path, "r", encoding="utf-8") as f:
        try:
            return json.loads(f.read())
        except ValueError:
            return {}


def _save_index(index):
    content = json.dumps(index, indent=2, sort_keys=True)
    if not isinstance(content, text_type):
        content = content.decode("utf-8")
    with io.open(_index_path(), "w", encoding="utf-8") as f:
        f.write(content)


def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def save(name, content, tags=None, force=False):
    """
    Save `content` under `name`. Raises IOError if a snippet with that
    name already exists, unless force=True - saving silently over an
    existing snippet without asking is how you lose one by accident.
    """
    path = _snippet_path(name)
    if os.path.exists(path) and not force:
        raise IOError("Snippet '{}' already exists. Use --force to overwrite.".format(name))

    if not isinstance(content, text_type):
        content = content.decode("utf-8")
    with io.open(path, "w", encoding="utf-8") as f:
        f.write(content)

    index = _load_index()
    entry = index.get(name, {})
    now = _now()
    if "created_at" not in entry:
        entry["created_at"] = now
    entry["updated_at"] = now
    if tags is not None:
        entry["tags"] = list(tags)
    else:
        entry.setdefault("tags", [])
    index[name] = entry
    _save_index(index)


def show(name):
    path = _snippet_path(name)
    if not os.path.exists(path):
        return None
    with io.open(path, "r", encoding="utf-8") as f:
        return f.read()


def metadata(name):
    return _load_index().get(name, {"tags": [], "created_at": None, "updated_at": None})


def list_snippets(tag=None):
    directory = _snippets_dir()
    names = [f[:-4] for f in os.listdir(directory) if f.endswith(".txt")]
    if tag is not None:
        index = _load_index()
        names = [n for n in names if tag in index.get(n, {}).get("tags", [])]
    return sorted(names)


def search(term):
    """Match snippets by name, tag, or content (case-insensitive)."""
    term_lower = term.lower()
    index = _load_index()
    matches = []

    for name in list_snippets():
        if term_lower in name.lower():
            matches.append(name)
            continue

        tags = index.get(name, {}).get("tags", [])
        if any(term_lower in tag.lower() for tag in tags):
            matches.append(name)
            continue

        content = show(name) or ""
        if term_lower in content.lower():
            matches.append(name)

    return sorted(matches)


def remove(name):
    path = _snippet_path(name)
    if not os.path.exists(path):
        return False
    os.remove(path)

    index = _load_index()
    if name in index:
        del index[name]
        _save_index(index)

    return True


def copy_to_clipboard(text):
    """Copy `text` to the system clipboard via a platform utility (no external deps)."""
    if not isinstance(text, text_type):
        text = text.decode("utf-8")

    if sys.platform == "darwin":
        cmd = ["pbcopy"]
    elif sys.platform == "win32":
        cmd = ["clip"]
    elif _which("xclip"):
        cmd = ["xclip", "-selection", "clipboard"]
    elif _which("xsel"):
        cmd = ["xsel", "--clipboard", "--input"]
    else:
        raise RuntimeError(
            "No clipboard utility found. Install 'xclip' or 'xsel' to use 'siren-snippet copy'."
        )

    process = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    process.communicate(input=text.encode("utf-8"))
    if process.returncode != 0:
        raise RuntimeError("Clipboard command failed: {}".format(" ".join(cmd)))


def copy(name):
    content = show(name)
    if content is None:
        return False
    copy_to_clipboard(content)
    return True


def _format_preview(content, max_len=60):
    stripped = content.strip()
    if not stripped:
        return ""
    line = stripped.splitlines()[0]
    if len(line) > max_len:
        line = line[:max_len - 3] + "..."
    return line


def main():
    parser = argparse.ArgumentParser(prog="siren-snippet")
    subparsers = parser.add_subparsers(dest="command")

    save_parser = subparsers.add_parser("save", help="Save stdin as a named snippet")
    save_parser.add_argument("name")
    save_parser.add_argument("--tag", action="append", default=[], dest="tags")
    save_parser.add_argument("--force", action="store_true")

    show_parser = subparsers.add_parser("show", help="Print a saved snippet")
    show_parser.add_argument("name")

    copy_parser = subparsers.add_parser("copy", help="Copy a saved snippet to the clipboard")
    copy_parser.add_argument("name")

    list_parser = subparsers.add_parser("list", help="List saved snippets")
    list_parser.add_argument("--tag", default=None)

    search_parser = subparsers.add_parser("search", help="Search snippets by name, tag, or content")
    search_parser.add_argument("term")

    remove_parser = subparsers.add_parser("remove", help="Delete a saved snippet")
    remove_parser.add_argument("name")

    args = parser.parse_args()

    if args.command == "save":
        content = sys.stdin.read()
        try:
            save(args.name, content, tags=args.tags, force=args.force)
        except IOError as e:
            safe_print(banner("SNIPPET", "Error: {}".format(e)))
            sys.exit(1)
        safe_print(banner("SNIPPET", "saved '{}'".format(args.name)))

    elif args.command == "show":
        content = show(args.name)
        if content is None:
            safe_print(banner("SNIPPET", "no snippet named '{}'".format(args.name)))
            sys.exit(1)
        safe_print(content.rstrip("\n"))

    elif args.command == "copy":
        try:
            copied = copy(args.name)
        except Exception as e:
            safe_print(banner("SNIPPET", "Error copying to clipboard: {}".format(e)))
            sys.exit(1)
        if not copied:
            safe_print(banner("SNIPPET", "no snippet named '{}'".format(args.name)))
            sys.exit(1)
        safe_print(banner("SNIPPET", "copied '{}' to clipboard".format(args.name)))

    elif args.command == "list":
        names = list_snippets(tag=args.tag)
        if not names:
            safe_print(banner("SNIPPET", "no snippets saved yet"))
        for name in names:
            entry = metadata(name)
            preview = _format_preview(show(name) or "")
            tags = ",".join(entry.get("tags") or [])
            tag_part = " [{}]".format(tags) if tags else ""
            updated = entry.get("updated_at")
            updated_part = " (updated {})".format(updated) if updated else ""
            preview_part = " - {}".format(preview) if preview else ""
            safe_print(banner("SNIPPET", "{}{}{}{}".format(name, tag_part, updated_part, preview_part)))

    elif args.command == "search":
        names = search(args.term)
        if not names:
            safe_print(banner("SNIPPET", "no snippets match '{}'".format(args.term)))
        for name in names:
            safe_print(banner("SNIPPET", name))

    elif args.command == "remove":
        removed = remove(args.name)
        message = "removed '{}'".format(args.name) if removed else "no snippet named '{}'".format(args.name)
        safe_print(banner("SNIPPET", message))
        if not removed:
            sys.exit(1)

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
