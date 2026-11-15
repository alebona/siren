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


def _compiles(source, path):
    try:
        compile(source, path, "exec")
        return True
    except SyntaxError:
        return False


def _runs(marked):
    """Group line numbers into runs of consecutive lines (one multi-line call = one run)."""
    runs = []
    for lineno in sorted(marked):
        if runs and lineno == runs[-1][-1] + 1:
            runs[-1].append(lineno)
        else:
            runs.append([lineno])
    return runs


def _rebuild(lines, marked, placeholders):
    """Source without the marked lines; a run starting at a line in
    `placeholders` is replaced by `pass` at that line's indentation."""
    out = []
    for lineno, line in enumerate(lines, 1):
        if lineno not in marked:
            out.append(line)
        elif lineno in placeholders:
            body = line.rstrip("\r\n")
            ending = line[len(body):]
            indent = body[:len(body) - len(body.lstrip())]
            out.append(indent + "pass" + ending)
    return "".join(out)


def _remove_lines(lines, marked, path):
    """
    Remove the marked lines. When that would leave a block empty (a loop or
    if whose only line was siren(...)), keep a `pass` where the call was -
    only where one is needed. Returns None if no version compiles.
    """
    source = _rebuild(lines, marked, set())
    if _compiles(source, path):
        return source

    placeholders = set(run[0] for run in _runs(marked))
    if not _compiles(_rebuild(lines, marked, placeholders), path):
        return None

    for start in sorted(placeholders):
        trial = placeholders - set([start])
        if _compiles(_rebuild(lines, marked, trial), path):
            placeholders = trial

    return _rebuild(lines, marked, placeholders)


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

    new_source = _remove_lines(lines, marked, path)
    if new_source is None:
        # Not even placeholders give valid Python. Leave the file untouched
        # rather than corrupting it.
        return 0

    with io.open(path, "w", encoding="utf-8") as f:
        f.write(new_source)

    return len(marked)


def clean_directory(root, dry_run=False):
    if os.path.isfile(root):
        return clean_file(root, dry_run=dry_run)

    total_removed = 0

    for base, dirs, files in os.walk(root):
        # Impede o os.walk de entrar nesses diretórios
        dirs[:] = [d for d in dirs if d.lower() not in IGNORE_DIRS]

        for name in files:
            if name.endswith(".py"):
                path = os.path.join(base, name)
                total_removed += clean_file(path, dry_run=dry_run)

    return total_removed


def main():
    try:
        args = sys.argv[1:]
        dry_run = "--dry-run" in args
        positional = [a for a in args if a != "--dry-run"]
        target = positional[0] if positional else "."
        removed = clean_directory(target, dry_run=dry_run)
        safe_print(
            "{}[{} SIREN CLEAN {}] {}{} linhas {}{}".format(
                COLOR,
                EMOJI,
                _format_timestamp(),
                COLOR,
                removed,
                "encontradas" if dry_run else "removidas",
                RESET,
            )
        )
    except Exception:
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
