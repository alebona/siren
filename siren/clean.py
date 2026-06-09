# -*- coding: utf-8 -*-
from __future__ import print_function

import io
import os
import re
import sys
import tokenize
from datetime import datetime

TOKEN_NAME = "siren"

IMPORT_RE = re.compile(r"^\s*from\s+siren\s+import\s+siren(?:\s+as\s+\w+)?\s*(?:#.*)?$")

# ANSI para rosa
COLOR = "\033[38;2;255;105;180m"
RESET = "\033[0m"
EMOJI = "🧜‍"


def _format_timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _collect_siren_lines(source):
    lines = source.splitlines(keepends=True)
    marked = set()

    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(source).readline))
    except tokenize.TokenError:
        return marked

    for index, token in enumerate(tokens):
        toknum, tokval, start, _, _ = token

        if toknum == tokenize.NAME and tokval == TOKEN_NAME:
            j = index + 1
            while j < len(tokens) and tokens[j][0] in (
                tokenize.NL,
                tokenize.NEWLINE,
                tokenize.INDENT,
                tokenize.DEDENT,
                tokenize.ENDMARKER,
            ):
                j += 1

            if j < len(tokens) and tokens[j][0] == tokenize.OP and tokens[j][1] == "(":
                depth = 0
                k = j

                while k < len(tokens):
                    toknum2, tokval2, start2, _, _ = tokens[k]
                    marked.add(start2[0])

                    if toknum2 == tokenize.OP:
                        if tokval2 == "(":
                            depth += 1
                        elif tokval2 == ")":
                            depth -= 1
                            if depth == 0:
                                break

                    k += 1

    for lineno, line in enumerate(lines, 1):
        if IMPORT_RE.match(line):
            marked.add(lineno)

    return marked


def clean_file(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            source = f.read()
    except TypeError:
        with open(path, "r") as f:
            source = f.read()

    lines = source.splitlines(keepends=True)
    marked = _collect_siren_lines(source)
    removed = 0

    new_lines = []
    for lineno, line in enumerate(lines, start=1):
        if lineno in marked:
            removed += 1
            continue

        new_lines.append(line)

    if removed:
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.writelines(new_lines)
        except TypeError:
            with open(path, "w") as f:
                f.writelines(new_lines)

    return removed


def clean_directory(root):
    total_removed = 0

    for base, dirs, files in os.walk(root):

        # ignorar venv automaticamente
        if "venv" in base.lower():
            continue

        if "__pycache__" in base:
            continue

        for name in files:
            if name.endswith(".py"):
                path = os.path.join(base, name)
                total_removed += clean_file(path)

    return total_removed


def main():
    target = sys.argv[1] if len(sys.argv) > 1 else "."
    removed = clean_directory(target)
    print(
        "{}[{} SIREN CLEAN {}] {}{} linhas removidas{}".format(
            COLOR,
            EMOJI,
            _format_timestamp(),
            COLOR,
            removed,
            RESET,
        )
    )


if __name__ == "__main__":
    main()