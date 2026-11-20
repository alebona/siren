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


_SKIP = (tokenize.NL, tokenize.COMMENT, tokenize.INDENT, tokenize.DEDENT)


class _Plan(object):
    """What to change in a file to take siren out of it."""

    def __init__(self):
        self.remove = set()  # whole lines to drop (1-based)
        self.cuts = []       # (row, start_col, end_col): text to delete inside a line
        self.dedents = []    # (first_row, last_row, columns): blocks to shift left
        self.kept = []       # rows with a siren use this can't take out safely
        self.string_lines = set()  # rows inside a multi-line string (left as they are)

    def changes(self):
        return len(self.remove) + len(set(row for row, _, _ in self.cuts))


def _matching_paren(tokens, open_index):
    depth = 0
    for k in range(open_index, len(tokens)):
        if tokens[k][0] == tokenize.OP:
            if tokens[k][1] in "([{":
                depth += 1
            elif tokens[k][1] in ")]}":
                depth -= 1
                if depth == 0:
                    return k
    return None


def _significant(tokens, index, step):
    k = index + step
    while 0 <= k < len(tokens) and tokens[k][0] in _SKIP:
        k += step
    return k if 0 <= k < len(tokens) else None


def _single_argument(tokens, open_index, close_index):
    """True when the call's positional arguments are exactly one (keywords
    like label= are fine): siren(x, label="a") returns x."""
    depth = 0
    positional = 0
    starts_arg = True
    for k in range(open_index + 1, close_index):
        kind, value = tokens[k][0], tokens[k][1]
        if kind in _SKIP:
            continue
        if kind == tokenize.OP and value in "([{":
            depth += 1
        elif kind == tokenize.OP and value in ")]}":
            depth -= 1
        if depth == 0 and kind == tokenize.OP and value == ",":
            starts_arg = True
            continue
        if starts_arg and depth == 0:
            starts_arg = False
            nxt = _significant(tokens, k, 1)
            is_keyword = kind == tokenize.NAME and nxt is not None and tokens[nxt][1] == "="
            if value in ("*", "**"):
                return False
            if not is_keyword:
                positional += 1
    return positional == 1


def _plan(source):
    """
    Find every use of siren in `source` and decide how to take it out:

    - a statement (siren(x), siren.diff(a, b), siren.set_quiet(True)): drop it
    - a decorator (@siren.trace, @siren.profile(...)): drop it
    - inside an expression (total = siren(compute())): keep the argument,
      `total = compute()`, since that's what siren returned
    - `with siren.catch():`: drop the header and shift its block left
    - `from siren import siren`: drop it
    """
    plan = _Plan()
    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(source).readline))
    except (tokenize.TokenError, IndentationError, SyntaxError):
        tokens = []
    lines = source.splitlines(True)
    string_lines = _multiline_string_lines(tokens)
    plan.string_lines = string_lines

    for index, token in enumerate(tokens):
        if token[0] != tokenize.NAME or token[1] != TOKEN_NAME:
            continue
        prev = _significant(tokens, index, -1)
        prev_value = tokens[prev][1] if prev is not None else None
        prev_kind = tokens[prev][0] if prev is not None else None
        # def siren(...), obj.siren(...), import siren: not ours to remove.
        if prev_value in ("def", "class", ".", "import", "as", "from"):
            continue

        # Walk siren.attr.attr
        end = index
        nxt = _significant(tokens, end, 1)
        while nxt is not None and tokens[nxt][1] == "." and tokens[nxt + 1][0] == tokenize.NAME:
            end = nxt + 1
            nxt = _significant(tokens, end, 1)
        has_call = nxt is not None and tokens[nxt][0] == tokenize.OP and tokens[nxt][1] == "("
        close = _matching_paren(tokens, nxt) if has_call else None
        last = close if close is not None else end
        first_row = token[2][0]
        last_row = tokens[last][3][0]

        statement_start = prev is None or prev_kind in (tokenize.NEWLINE, tokenize.ENDMARKER) or prev_value == ";"
        after = _significant(tokens, last, 1)
        statement_end = after is None or tokens[after][0] in (tokenize.NEWLINE, tokenize.ENDMARKER) or tokens[after][1] == ";"

        if prev_value == "@":
            # Decorator: from the @ line through its arguments, if any.
            plan.remove.update(range(tokens[prev][2][0], last_row + 1))
        elif statement_start and statement_end:
            plan.remove.update(range(first_row, last_row + 1))
        elif prev_value == "with" and has_call and close is not None and statement_end is False \
                and tokens[after][1] == ":":
            _plan_with(tokens, prev, after, lines, plan)
        elif has_call and close is not None and end == index and _single_argument(tokens, nxt, close) \
                and tokens[index][2][0] == tokens[nxt][2][0]:
            _plan_unwrap(tokens, index, nxt, close, plan)
        else:
            plan.kept.append(first_row)

    for lineno, line in enumerate(lines, 1):
        if lineno not in string_lines and IMPORT_RE.match(line):
            plan.remove.add(lineno)
    return plan


_LOOSE_KEYWORDS = ("and", "or", "not", "is", "in", "if", "else", "lambda", "for", "await", "yield")


def _is_simple(tokens, first, last):
    """No operator at the top level (a name, a call, an attribute, a literal),
    so the argument can lose its parentheses without changing what it means."""
    depth = 0
    for k in range(first, last + 1):
        kind, value = tokens[k][0], tokens[k][1]
        if kind in _SKIP:
            continue
        if kind == tokenize.OP and value in "([{":
            depth += 1
        elif kind == tokenize.OP and value in ")]}":
            depth -= 1
        elif depth == 0:
            if kind == tokenize.OP and value != ".":
                return False
            if kind == tokenize.NAME and value in _LOOSE_KEYWORDS:
                return False
    return True


def _plan_unwrap(tokens, index, open_index, close_index, plan):
    """
    siren(...) inside an expression returns its single positional argument,
    so keep that: `total = siren(compute(), label="x")` -> `total = compute()`.
    A compound argument keeps its parentheses: `siren(a + b).real` ->
    `(a + b).real`.
    """
    comma = _top_level_comma(tokens, open_index, close_index)
    arg_last = _significant(tokens, comma if comma is not None else close_index, -1)
    simple = _is_simple(tokens, open_index + 1, arg_last)
    row, col = tokens[index][2]
    head = (row, col, tokens[open_index][3][1] if simple else tokens[open_index][2][1])  # "siren(" or "siren"
    tail_from = tokens[arg_last][3]
    tail_to = tokens[close_index][3] if simple else tokens[close_index][2]  # through ")" or up to it
    if tail_from[0] == tail_to[0]:
        tail = (tail_from[0], tail_from[1], tail_to[1]) if tail_to[1] > tail_from[1] else None
    elif comma is None and simple:
        tail = (tokens[close_index][2][0], tokens[close_index][2][1], tokens[close_index][3][1])  # just ")"
    elif comma is None:
        tail = None
    else:
        plan.kept.append(row)  # keyword arguments spread over several lines
        return
    plan.cuts.append(head)
    if tail:
        plan.cuts.append(tail)


def _top_level_comma(tokens, open_index, close_index):
    depth = 0
    for k in range(open_index + 1, close_index):
        kind, value = tokens[k][0], tokens[k][1]
        if kind == tokenize.OP and value in "([{":
            depth += 1
        elif kind == tokenize.OP and value in ")]}":
            depth -= 1
        elif depth == 0 and kind == tokenize.OP and value == ",":
            return k
    return None


def _plan_with(tokens, with_index, colon_index, lines, plan):
    """`with siren.catch():` -> drop the header and shift its block left."""
    header_row = tokens[with_index][2][0]
    header = lines[header_row - 1]
    header_indent = len(header) - len(header.lstrip(" \t"))
    after_colon = _significant(tokens, colon_index, 1)
    if after_colon is None or tokens[after_colon][0] != tokenize.NEWLINE:
        plan.kept.append(header_row)  # `with siren.catch(): x()` on one line
        return
    first = header_row + 1
    while first <= len(lines) and not lines[first - 1].strip():
        first += 1
    if first > len(lines):
        plan.kept.append(header_row)
        return
    body_indent = len(lines[first - 1]) - len(lines[first - 1].lstrip(" \t"))
    last = first
    for row in range(first, len(lines) + 1):
        text = lines[row - 1]
        if text.strip() and len(text) - len(text.lstrip(" \t")) < body_indent:
            break
        if text.strip():
            last = row
    plan.remove.add(header_row)
    plan.dedents.append((first, last, body_indent - header_indent))


def _collect_siren_lines(source):
    """Lines that removing siren changes (kept for the dry run's count)."""
    plan = _plan(source)
    return plan.remove | set(row for row, _, _ in plan.cuts)


def _apply_cuts_and_dedents(lines, plan, string_lines):
    lines = list(lines)
    by_row = {}
    for row, start, end in plan.cuts:
        by_row.setdefault(row, []).append((start, end))
    for row, spans in by_row.items():
        text = lines[row - 1]
        for start, end in sorted(spans, reverse=True):
            text = text[:start] + text[end:]
        lines[row - 1] = text
    for first, last, columns in plan.dedents:
        for row in range(first, last + 1):
            text = lines[row - 1]
            if row in string_lines or not text.strip():
                continue
            lead = len(text) - len(text.lstrip(" \t"))
            lines[row - 1] = text[min(columns, lead):]
    return lines


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


def _remove_lines(lines, marked, path, original=None):
    """
    Remove the marked lines. When that would leave a block empty (a loop or
    if whose only line was siren(...)), keep a `pass` where the call was -
    only where one is needed. Returns None if no version compiles.
    """
    if not _compiles(original if original is not None else "".join(lines), path):
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

    plan = _plan(source)
    for row in plan.kept:
        safe_print(u"! {}:{} (kept: this siren use can't be removed safely; remove it by hand)".format(_text(path), row))
    count = plan.changes()
    if not count:
        return 0

    if dry_run:
        safe_print("✓ {} ({} linhas)".format(path, count))
        return count

    edited = _apply_cuts_and_dedents(lines, plan, plan.string_lines)
    new_source = _remove_lines(edited, plan.remove, path, original="".join(lines))
    if new_source is None:
        # Not even placeholders give valid Python. Leave the file untouched
        # rather than corrupting it.
        return 0

    with io.open(path, "w", encoding=encoding, newline="") as f:
        f.write(new_source)

    return count


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
