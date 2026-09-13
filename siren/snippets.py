# -*- coding: utf-8 -*-
"""
Save and recall small code/text snippets from the terminal.

Usage:
    echo "some code" | siren-snippet save my-snippet
    siren-snippet show my-snippet
    siren-snippet list
    siren-snippet remove my-snippet
"""
from __future__ import print_function

import argparse
import io
import os
import sys

from ._cli import banner
from ._output import safe_print

try:
    text_type = unicode  # Python 2
except NameError:
    text_type = str  # Python 3


def _snippets_dir():
    path = os.path.join(os.path.expanduser("~"), ".siren", "snippets")
    if not os.path.isdir(path):
        os.makedirs(path)
    return path


def _snippet_path(name):
    return os.path.join(_snippets_dir(), "{}.txt".format(name))


def save(name, content):
    if not isinstance(content, text_type):
        content = content.decode("utf-8")
    with io.open(_snippet_path(name), "w", encoding="utf-8") as f:
        f.write(content)


def show(name):
    path = _snippet_path(name)
    if not os.path.exists(path):
        return None
    with io.open(path, "r", encoding="utf-8") as f:
        return f.read()


def list_snippets():
    directory = _snippets_dir()
    names = [f[:-4] for f in os.listdir(directory) if f.endswith(".txt")]
    return sorted(names)


def remove(name):
    path = _snippet_path(name)
    if not os.path.exists(path):
        return False
    os.remove(path)
    return True


def main():
    parser = argparse.ArgumentParser(prog="siren-snippet")
    subparsers = parser.add_subparsers(dest="command")

    save_parser = subparsers.add_parser("save", help="Save stdin as a named snippet")
    save_parser.add_argument("name")

    show_parser = subparsers.add_parser("show", help="Print a saved snippet")
    show_parser.add_argument("name")

    subparsers.add_parser("list", help="List saved snippet names")

    remove_parser = subparsers.add_parser("remove", help="Delete a saved snippet")
    remove_parser.add_argument("name")

    args = parser.parse_args()

    if args.command == "save":
        content = sys.stdin.read()
        save(args.name, content)
        safe_print(banner("SNIPPET", "saved '{}'".format(args.name)))

    elif args.command == "show":
        content = show(args.name)
        if content is None:
            safe_print(banner("SNIPPET", "no snippet named '{}'".format(args.name)))
            sys.exit(1)
        safe_print(content.rstrip("\n"))

    elif args.command == "list":
        names = list_snippets()
        if not names:
            safe_print(banner("SNIPPET", "no snippets saved yet"))
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
