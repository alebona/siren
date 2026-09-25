# -*- coding: utf-8 -*-
from __future__ import print_function

import io
import os
import re
import sys
import tokenize
import traceback
from datetime import datetime

from ._output import safe_print

TOKEN_NAME = "siren"

IMPORT_RE = re.compile(r"^\s*from\s+siren\s+import\s+siren(?:\s+as\s+\w+)?\s*(?:#.*)?$")

# ANSI para rosa
COLOR = "\033[38;2;255;105;180m"
RESET = "\033[0m"
EMOJI = "🧜‍"

IGNORE_DIRS = {
    "venv",
    ".venv",
    "__pycache__",
    "doc",
    "docs",
    ".git",
    "node_modules",
}


def _format_timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _multiline_string_lines(tokens):
    """Line numbers that fall entirely inside a multi-line string literal."""
    lines = set()

    for token in tokens:
        if token[0] == tokenize.STRING:
            start_row, end_row = token[2][0], token[3][0]
            if end_row > start_row:
                lines.update(range(start_row + 1, end_row + 1))

    return lines


def _collect_siren_lines(source):
    # Python 2's splitlines() only accepts keepends positionally, not as a
    # keyword - splitlines(keepends=True) raises TypeError there.
    lines = source.splitlines(True)
    marked = set()

    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(source).readline))
    except tokenize.TokenError:
        return marked

    string_lines = _multiline_string_lines(tokens)

    for index, token in enumerate(tokens):
        toknum, tokval, start, _, _ = token

        if toknum == tokenize.NAME and tokval == TOKEN_NAME:
            # Skip definitions like `def siren(...)` / `def siren.trace(...)` -
            # only actual calls should be stripped, not the definition itself.
            prev = index - 1
            while prev >= 0 and tokens[prev][0] in (
                tokenize.NL,
                tokenize.INDENT,
                tokenize.DEDENT,
                tokenize.COMMENT,
            ):
                prev -= 1

            if prev >= 0 and tokens[prev][0] == tokenize.NAME and tokens[prev][1] == "def":
                continue

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
        if lineno in string_lines:
            continue
        if IMPORT_RE.match(line):
            marked.add(lineno)

    return marked


def clean_file(path, dry_run=False):
    # io.open decodes/encodes explicitly on both Python 2 and 3, unlike the
    # builtin open() which doesn't accept encoding= on Python 2.
    with io.open(path, "r", encoding="utf-8") as f:
        source = f.read()

    # Python 2's splitlines() only accepts keepends positionally, not as a
    # keyword - splitlines(keepends=True) raises TypeError there.
    lines = source.splitlines(True)

    try:
        marked = _collect_siren_lines(source)
    except Exception as e:
        raise type(e)("{}\nArquivo: {}".format(e, path))

    if not marked:
        return 0

    if dry_run:
        safe_print("✓ {} ({} linhas)".format(path, len(marked)))
        return len(marked)

    new_lines = [line for lineno, line in enumerate(lines, start=1) if lineno not in marked]
    new_source = "".join(new_lines)

    try:
        compile(new_source, path, "exec")
    except SyntaxError:
        # Removing these lines would leave invalid Python (e.g. an emptied
        # block). Leave the file untouched rather than corrupting it.
        return 0

    with io.open(path, "w", encoding="utf-8") as f:
        f.write(new_source)

    return len(marked)


def clean_directory(root):
    total_removed = 0

    for base, dirs, files in os.walk(root):
        # Impede o os.walk de entrar nesses diretórios
        dirs[:] = [d for d in dirs if d.lower() not in IGNORE_DIRS]

        for name in files:
            if name.endswith(".py"):
                path = os.path.join(base, name)
                total_removed += clean_file(path)

    return total_removed


def main():
    try:
        target = sys.argv[1] if len(sys.argv) > 1 else "."
        removed = clean_directory(target)
        safe_print(
            "{}[{} SIREN CLEAN {}] {}{} linhas removidas{}".format(
                COLOR,
                EMOJI,
                _format_timestamp(),
                COLOR,
                removed,
                RESET,
            )
        )
    except Exception:
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
