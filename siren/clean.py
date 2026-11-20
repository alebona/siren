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

try:
    text_type = unicode  # Python 2
except NameError:
    text_type = str  # Python 3

TOKEN_NAME = "siren"

IMPORT_RE = re.compile(r"^\s*from\s+siren\s+import\s+siren(?:\s+as\s+\w+)?\s*(?:#.*)?$")

# ANSI para rosa
COLOR = "\033[38;2;255;105;180m"
RESET = "\033[0m"
EMOJI = "🧜‍"

IGNORE_DIRS = {
    "venv",
    ".venv",
    "env",
    "__pycache__",
    "doc",
    "docs",
    ".git",
    ".hg",
    ".svn",
    ".tox",
    ".nox",
    "node_modules",
    "site-packages",
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
    # Compile bytes, not text: Python 2 raises SyntaxError ("encoding
    # declaration in Unicode string") for any decoded source that still has
    # a "# -*- coding: utf-8 -*-" line, which would make every such file
    # look broken.
    if isinstance(source, text_type):
        source = source.encode("utf-8")
    try:
        compile(source, path, "exec")
        return True
    except (SyntaxError, ValueError, TypeError):
        return False


def _code_part(line):
    """The line without its trailing comment or newline (a # inside a string is kept)."""
    quote = None
    i = 0
    while i < len(line):
        ch = line[i]
        if quote:
            if ch == "\\":
                i += 1
            elif ch == quote:
                quote = None
        elif ch in "'\"":
            quote = ch
        elif ch == "#":
            return line[:i].rstrip()
        i += 1
    return line.rstrip()


def _indent(line):
    return len(line) - len(line.lstrip(" \t"))


def _structural_placeholders(lines, marked):
    """
    Where a `pass` is needed, worked out from the code's shape alone: a run of
    removed lines whose block opener (a line ending in ':') has no other
    statement left in its block. Used when the file can't be compiled by the
    interpreter running siren-clean, e.g. Python 2 code checked by Python 3.
    """
    def is_code(lineno):
        text = lines[lineno - 1].strip()
        return bool(text) and not text.startswith("#")

    needed = set()
    openers_done = set()
    for run in _runs(marked):
        prev = run[0] - 1
        while prev >= 1 and (prev in marked or not is_code(prev)):
            prev -= 1
        if prev < 1 or prev in openers_done or not _code_part(lines[prev - 1]).endswith(":"):
            continue
        nxt = run[-1] + 1
        while nxt <= len(lines) and (nxt in marked or not is_code(nxt)):
            nxt += 1
        if nxt > len(lines) or _indent(lines[nxt - 1]) <= _indent(lines[prev - 1]):
            needed.add(run[0])
            openers_done.add(prev)
    return needed


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
    if not _compiles("".join(lines), path):
        # This interpreter can't compile the file even before any change
        # (Python 2 code checked by Python 3, or the reverse), so compiling
        # can't tell a good result from a bad one. Go by the code's shape.
        return _rebuild(lines, marked, _structural_placeholders(lines, marked))

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


_CODING_RE = re.compile(br"^[ \t\f]*#.*?coding[:=][ \t]*([-\w.]+)")


def _read_source(path):
    """
    The file's text and the encoding to write it back with. Legacy projects
    often have Latin-1 files: use the PEP 263 "coding:" line when there is
    one, then UTF-8, then Latin-1 (which decodes any byte, so writing back
    with it reproduces the original bytes exactly).
    """
    with io.open(path, "rb") as f:
        raw = f.read()
    candidates = []
    for line in raw.splitlines()[:2]:
        match = _CODING_RE.match(line)
        if match:
            candidates.append(match.group(1).decode("ascii"))
            break
    candidates += ["utf-8", "latin-1"]
    for encoding in candidates:
        try:
            return raw.decode(encoding), encoding
        except (UnicodeDecodeError, LookupError):
            continue
    return raw.decode("latin-1"), "latin-1"


def clean_file(path, dry_run=False):
    # Bytes are decoded by hand (see _read_source) and the result keeps the
    # file's own line endings (LF or CRLF) instead of rewriting every line in
    # the OS default, which would show the whole file as changed in git.
    source, encoding = _read_source(path)

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

    with io.open(path, "w", encoding=encoding, newline="") as f:
        f.write(new_source)

    return len(marked)


def _is_installed_code(path):
    """A virtualenv (whatever its name) or an installed-packages folder."""
    if os.path.basename(path).lower() == "site-packages":
        return True
    return any(
        os.path.exists(os.path.join(path, marker))
        for marker in ("pyvenv.cfg", os.path.join("bin", "activate"), os.path.join("Scripts", "activate"))
    )


def _clean_one(path, dry_run):
    """clean_file, but a file that can't be processed is reported and skipped
    instead of stopping the whole run."""
    try:
        return clean_file(path, dry_run=dry_run)
    except Exception as e:
        safe_print(u"! {} ({}: {})".format(_text(path), type(e).__name__, _text(str(e)).splitlines()[0]))
        return 0


def _text(value):
    if isinstance(value, text_type):
        return value
    return value.decode("utf-8", "replace")


def clean_directory(root, dry_run=False):
    if os.path.isfile(root):
        return _clean_one(root, dry_run)

    total_removed = 0

    for base, dirs, files in os.walk(root):
        # Don't descend into tooling folders or installed code (virtualenvs of
        # any name), which hold thousands of files and none of ours.
        dirs[:] = [
            d for d in dirs
            if d.lower() not in IGNORE_DIRS and not _is_installed_code(os.path.join(base, d))
        ]

        for name in files:
            if name.endswith(".py"):
                total_removed += _clean_one(os.path.join(base, name), dry_run)

    return total_removed


def main():
    try:
        args = sys.argv[1:]
        dry_run = "--dry-run" in args
        targets = [a for a in args if a != "--dry-run"] or ["."]
        removed = sum(clean_directory(target, dry_run=dry_run) for target in targets)
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
