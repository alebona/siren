# -*- coding: utf-8 -*-
"""
Save and recall small code/text snippets from the terminal.

Usage:
    echo "some code" | siren-snippet save my-snippet --tag sql
    siren-snippet save my-snippet --file query.sql
    siren-snippet show my-snippet
    siren-snippet copy my-snippet
    siren-snippet edit my-snippet
    siren-snippet rename my-snippet renamed
    siren-snippet list [--tag sql]
    siren-snippet tags
    siren-snippet search some-term
    siren-snippet remove my-snippet
    siren-snippet export backup.json
    siren-snippet import backup.json
"""
from __future__ import print_function

import argparse
import io
import json
import os
import shlex
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


def _write_text_file(path, content):
    if not isinstance(content, text_type):
        content = content.decode("utf-8")
    with io.open(path, "w", encoding="utf-8") as f:
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

    _write_text_file(path, content)

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


def render(content, variables=None):
    """Replace {{key}} placeholders with values from `variables`."""
    if not variables:
        return content
    for key, value in variables.items():
        content = content.replace("{{" + key + "}}", value)
    return content


def metadata(name):
    return _load_index().get(name, {"tags": [], "created_at": None, "updated_at": None})


def list_snippets(tag=None):
    directory = _snippets_dir()
    names = [f[:-4] for f in os.listdir(directory) if f.endswith(".txt")]
    if tag is not None:
        index = _load_index()
        names = [n for n in names if tag in index.get(n, {}).get("tags", [])]
    return sorted(names)


def all_tags():
    """Every tag currently in use, with how many snippets carry it."""
    index = _load_index()
    counts = {}
    for name in list_snippets():
        for tag in index.get(name, {}).get("tags", []):
            counts[tag] = counts.get(tag, 0) + 1
    return sorted(counts.items())


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


def rename(old_name, new_name, force=False):
    old_path = _snippet_path(old_name)
    if not os.path.exists(old_path):
        return False

    new_path = _snippet_path(new_name)
    if os.path.exists(new_path) and not force:
        raise IOError("Snippet '{}' already exists. Use --force to overwrite.".format(new_name))

    os.rename(old_path, new_path)

    index = _load_index()
    entry = index.pop(old_name, {"tags": [], "created_at": _now()})
    entry["updated_at"] = _now()
    index[new_name] = entry
    _save_index(index)
    return True


def edit(name):
    """Open a snippet in $EDITOR (or $VISUAL) for in-place editing."""
    path = _snippet_path(name)
    if not os.path.exists(path):
        return False

    editor = os.environ.get("EDITOR") or os.environ.get("VISUAL")
    if not editor:
        raise RuntimeError("No editor configured. Set the EDITOR (or VISUAL) environment variable.")

    subprocess.call(shlex.split(editor) + [path])

    index = _load_index()
    entry = index.get(name, {})
    entry.setdefault("tags", [])
    entry.setdefault("created_at", _now())
    entry["updated_at"] = _now()
    index[name] = entry
    _save_index(index)
    return True


def export_snippets(path):
    """Write every snippet (content + metadata) to a single JSON file."""
    index = _load_index()
    data = {}
    for name in list_snippets():
        entry = dict(index.get(name, {"tags": [], "created_at": None, "updated_at": None}))
        entry["content"] = show(name)
        data[name] = entry

    _write_text_file(path, json.dumps(data, indent=2, sort_keys=True))
    return len(data)


def import_snippets(path, force=False):
    """
    Load snippets from a file written by export_snippets(). Existing
    snippets are skipped unless force=True. Returns {"imported": n, "skipped": [names]}.
    """
    with io.open(path, "r", encoding="utf-8") as f:
        data = json.loads(f.read())

    index = _load_index()
    imported = 0
    skipped = []

    for name, entry in data.items():
        if os.path.exists(_snippet_path(name)) and not force:
            skipped.append(name)
            continue

        _write_text_file(_snippet_path(name), entry.get("content", ""))
        index[name] = {
            "tags": entry.get("tags", []),
            "created_at": entry.get("created_at"),
            "updated_at": entry.get("updated_at"),
        }
        imported += 1

    _save_index(index)
    return {"imported": imported, "skipped": sorted(skipped)}


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


def copy(name, variables=None):
    content = show(name)
    if content is None:
        return False
    copy_to_clipboard(render(content, variables))
    return True


def _format_preview(content, max_len=60):
    stripped = content.strip()
    if not stripped:
        return ""
    line = stripped.splitlines()[0]
    if len(line) > max_len:
        line = line[:max_len - 3] + "..."
    return line


def _parse_var(raw):
    if "=" not in raw:
        raise ValueError("--var must be in 'key=value' format, got: {}".format(raw))
    key, value = raw.split("=", 1)
    return key, value


def main():
    parser = argparse.ArgumentParser(prog="siren-snippet")
    subparsers = parser.add_subparsers(dest="command")

    save_parser = subparsers.add_parser("save", help="Save stdin (or --file) as a named snippet")
    save_parser.add_argument("name", nargs="?")
    save_parser.add_argument("--file", help="Read content from this file instead of stdin")
    save_parser.add_argument("--tag", action="append", default=[], dest="tags")
    save_parser.add_argument("--force", action="store_true")

    show_parser = subparsers.add_parser("show", help="Print a saved snippet")
    show_parser.add_argument("name")
    show_parser.add_argument("--var", action="append", default=[], dest="variables")

    copy_parser = subparsers.add_parser("copy", help="Copy a saved snippet to the clipboard")
    copy_parser.add_argument("name")
    copy_parser.add_argument("--var", action="append", default=[], dest="variables")

    edit_parser = subparsers.add_parser("edit", help="Edit a saved snippet in $EDITOR")
    edit_parser.add_argument("name")

    rename_parser = subparsers.add_parser("rename", help="Rename a saved snippet")
    rename_parser.add_argument("old_name")
    rename_parser.add_argument("new_name")
    rename_parser.add_argument("--force", action="store_true")

    list_parser = subparsers.add_parser("list", help="List saved snippets")
    list_parser.add_argument("--tag", default=None)

    subparsers.add_parser("tags", help="List every tag currently in use")

    search_parser = subparsers.add_parser("search", help="Search snippets by name, tag, or content")
    search_parser.add_argument("term")

    remove_parser = subparsers.add_parser("remove", help="Delete a saved snippet")
    remove_parser.add_argument("name")

    export_parser = subparsers.add_parser("export", help="Write all snippets to a JSON backup file")
    export_parser.add_argument("path")

    import_parser = subparsers.add_parser("import", help="Load snippets from a JSON backup file")
    import_parser.add_argument("path")
    import_parser.add_argument("--force", action="store_true")

    args = parser.parse_args()

    if args.command == "save":
        if args.file:
            with io.open(args.file, "r", encoding="utf-8") as f:
                content = f.read()
            name = args.name or os.path.splitext(os.path.basename(args.file))[0]
        else:
            content = sys.stdin.read()
            name = args.name

        if not name:
            parser.error("a snippet name is required (or pass --file to default to the filename)")

        try:
            save(name, content, tags=args.tags, force=args.force)
        except IOError as e:
            safe_print(banner("SNIPPET", "Error: {}".format(e)))
            sys.exit(1)
        safe_print(banner("SNIPPET", "saved '{}'".format(name)))

    elif args.command == "show":
        content = show(args.name)
        if content is None:
            safe_print(banner("SNIPPET", "no snippet named '{}'".format(args.name)))
            sys.exit(1)
        try:
            variables = dict(_parse_var(v) for v in args.variables)
        except ValueError as e:
            safe_print(banner("SNIPPET", "Error: {}".format(e)))
            sys.exit(1)
        safe_print(render(content, variables).rstrip("\n"))

    elif args.command == "copy":
        try:
            variables = dict(_parse_var(v) for v in args.variables)
        except ValueError as e:
            safe_print(banner("SNIPPET", "Error: {}".format(e)))
            sys.exit(1)
        try:
            copied = copy(args.name, variables)
        except Exception as e:
            safe_print(banner("SNIPPET", "Error copying to clipboard: {}".format(e)))
            sys.exit(1)
        if not copied:
            safe_print(banner("SNIPPET", "no snippet named '{}'".format(args.name)))
            sys.exit(1)
        safe_print(banner("SNIPPET", "copied '{}' to clipboard".format(args.name)))

    elif args.command == "edit":
        try:
            edited = edit(args.name)
        except RuntimeError as e:
            safe_print(banner("SNIPPET", "Error: {}".format(e)))
            sys.exit(1)
        if not edited:
            safe_print(banner("SNIPPET", "no snippet named '{}'".format(args.name)))
            sys.exit(1)
        safe_print(banner("SNIPPET", "edited '{}'".format(args.name)))

    elif args.command == "rename":
        try:
            renamed = rename(args.old_name, args.new_name, force=args.force)
        except IOError as e:
            safe_print(banner("SNIPPET", "Error: {}".format(e)))
            sys.exit(1)
        if not renamed:
            safe_print(banner("SNIPPET", "no snippet named '{}'".format(args.old_name)))
            sys.exit(1)
        safe_print(banner("SNIPPET", "renamed '{}' -> '{}'".format(args.old_name, args.new_name)))

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

    elif args.command == "tags":
        tags = all_tags()
        if not tags:
            safe_print(banner("SNIPPET", "no tags in use yet"))
        for tag, count in tags:
            safe_print(banner("SNIPPET", "{} ({})".format(tag, count)))

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

    elif args.command == "export":
        count = export_snippets(args.path)
        safe_print(banner("SNIPPET", "exported {} snippet(s) to {}".format(count, args.path)))

    elif args.command == "import":
        result = import_snippets(args.path, force=args.force)
        safe_print(banner("SNIPPET", "imported {} snippet(s)".format(result["imported"])))
        if result["skipped"]:
            safe_print(banner("SNIPPET", "skipped (already exist, use --force): {}".format(", ".join(result["skipped"]))))

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
