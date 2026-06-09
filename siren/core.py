# -*- coding: utf-8 -*-
from __future__ import print_function

import io
import io
import pprint
import inspect
import linecache
import re
import time
import os
import tokenize
from datetime import datetime
import tokenize

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
COLOR = "\033[38;2;255;105;180m"
RESET = "\033[0m"
EMOJI = '🧜‍' #"🔱"

PROJECT_MARKERS = [
    ".git",
    "pyproject.toml",
    "setup.py",
    "requirements.txt",
    "manage.py",
]

# Global configuration
_SIREN_CONFIG = {
    "quiet": False,
    "logfile": None,
    "enabled": True,
}

def find_project_root(start_path):
    path = os.path.abspath(start_path)

    while True:
        for marker in PROJECT_MARKERS:
            if os.path.exists(os.path.join(path, marker)):
                return path

        parent = os.path.dirname(path)

        if parent == path:
            return None

        path = parent


def _is_simple(value):
    return isinstance(value, (int, float, str, bool, type(None)))


def _format_timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _print_output(text):
    """Handle output according to configuration (stdout or logfile)."""
    if _SIREN_CONFIG["quiet"]:
        return

    print(text)

    if _SIREN_CONFIG["logfile"]:
        try:
            with open(_SIREN_CONFIG["logfile"], "a", encoding="utf-8") as f:
                f.write(text + "\n")
        except Exception:
            pass  # Silently fail on log write errors


def _get_call_source(frame):
    filename = frame.f_code.co_filename
    lineno = frame.f_lineno

    line = linecache.getline(filename, lineno).strip()

    return line


def get_rel_path(frame):
    caminho = frame.f_code.co_filename

    root = find_project_root(caminho)

    if root:
        return os.path.relpath(caminho, root)

    return caminho


def _extract_args(frame):
    filename = frame.f_code.co_filename
    lineno = frame.f_lineno

    try:
        lines = linecache.getlines(filename)
    except Exception:
        return []

    if not lines or lineno > len(lines):
        return []

    start = lineno - 1
    while start >= 0 and "siren" not in lines[start]:
        start -= 1

    if start < 0:
        return []

    source_lines = []
    paren_depth = 0
    saw_call = False

    for line in lines[start:]:
        source_lines.append(line)

        for char in line:
            if char == "(":
                paren_depth += 1
                saw_call = saw_call or "siren" in line
            elif char == ")":
                paren_depth -= 1

        if saw_call and paren_depth <= 0:
            break

    source = "".join(source_lines)

    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(source).readline))
    except tokenize.TokenError:
        return []

    for index, token in enumerate(tokens):
        toknum, tokval, _, _, _ = token
        if toknum == tokenize.NAME and tokval == "siren":
            j = index + 1
            while j < len(tokens) and tokens[j][0] in (
                tokenize.NL,
                tokenize.NEWLINE,
                tokenize.INDENT,
                tokenize.DEDENT,
            ):
                j += 1

            if j >= len(tokens) or tokens[j][0] != tokenize.OP or tokens[j][1] != "(":
                continue

            depth = 0
            current = []
            parts = []
            k = j + 1

            while k < len(tokens):
                tn, tv, _, _, _ = tokens[k]

                if tn == tokenize.OP and tv == "(":
                    depth += 1
                    current.append(tv)
                elif tn == tokenize.OP and tv == ")":
                    if depth == 0:
                        break
                    depth -= 1
                    current.append(tv)
                elif tn == tokenize.OP and tv == "," and depth == 0:
                    parts.append("".join(current).strip())
                    current = []
                else:
                    if tn in (tokenize.NEWLINE, tokenize.NL):
                        current.append(" ")
                    elif tn in (tokenize.INDENT, tokenize.DEDENT):
                        pass
                    elif tn == tokenize.COMMENT:
                        pass
                    else:
                        current.append(tv)
                k += 1

            if current:
                parts.append("".join(current).strip())

            return [p for p in parts if p]

    return []


def _prefix(frame, label=None):

    lineno = frame.f_lineno

    base = "{}[{} SIREN {} {}:{}]{}".format(
        COLOR,
        EMOJI,
        _format_timestamp(),
        get_rel_path(frame),
        lineno,
        RESET,
    )

    if label:
        base += " {}{}{}".format(COLOR, label, RESET)

    return base


def siren(*values, **kwargs):
    """
    siren(x)
    siren(x, y)
    siren(x, label="BEFORE LOOP")
    siren(x, timeit=True)
    siren(x, quiet=True)
    siren(x, if_equals=5)
    siren(x, if_len_gt=100)
    """

    if not _SIREN_CONFIG["enabled"]:
        if len(values) == 1:
            return values[0]
        return values

    # Check conditional filters
    if_equals = kwargs.get("if_equals")
    if_len_gt = kwargs.get("if_len_gt")
    if_len_lt = kwargs.get("if_len_lt")
    if_true = kwargs.get("if_true")
    if_false = kwargs.get("if_false")

    # Evaluate conditions
    if if_equals is not None:
        if len(values) != 1 or values[0] != if_equals:
            if len(values) == 1:
                return values[0]
            return values

    if if_len_gt is not None:
        if len(values) != 1 or not hasattr(values[0], "__len__") or len(values[0]) <= if_len_gt:
            if len(values) == 1:
                return values[0]
            return values

    if if_len_lt is not None:
        if len(values) != 1 or not hasattr(values[0], "__len__") or len(values[0]) >= if_len_lt:
            if len(values) == 1:
                return values[0]
            return values

    if if_true is not None:
        if not values[0]:
            if len(values) == 1:
                return values[0]
            return values

    if if_false is not None:
        if values[0]:
            if len(values) == 1:
                return values[0]
            return values

    frame = inspect.currentframe().f_back

    label = kwargs.get("label")
    timeit = kwargs.get("timeit", False)
    quiet = kwargs.get("quiet", False)

    start = None

    if timeit:
        start = time.time()

    args = _extract_args(frame)

    prefix = _prefix(frame, label)

    # Temporarily override quiet setting if specified
    original_quiet = _SIREN_CONFIG["quiet"]
    if quiet:
        _SIREN_CONFIG["quiet"] = True

    try:
        for i, v in enumerate(values):

            name = args[i] if i < len(args) else "?"

            if _is_simple(v):
                output = "{} {}{} = {}{}".format(prefix, COLOR, name, v, RESET)
            else:
                text = pprint.pformat(v)
                output = "{} {}{} = {}{}".format(prefix, COLOR, name, text, RESET)

            _print_output(output)

        if timeit:
            elapsed = time.time() - start
            timer_output = "{}[{} SIREN TIME {}] {}{:.6f}s{}".format(
                COLOR,
                EMOJI,
                _format_timestamp(),
                COLOR,
                elapsed,
                RESET,
            )
            _print_output(timer_output)

        if len(values) == 1:
            return values[0]

        return values
    finally:
        _SIREN_CONFIG["quiet"] = original_quiet

def _truncate_str(text, max_len=80):
    """Truncate long strings for readable trace output."""
    if len(text) <= max_len:
        return text
    return text[:max_len-3] + "..."


def _format_value_for_trace(value, max_len=80):
    """Format a value for trace output with truncation."""
    if _is_simple(value):
        return str(value)
    text = pprint.pformat(value)
    return _truncate_str(text, max_len)


def _format_trace_args(func, args, kwargs):
    try:
        signature = inspect.signature(func)
        bound = signature.bind_partial(*args, **kwargs)
        bound.apply_defaults()
        parts = []

        for name, value in bound.arguments.items():
            formatted = _format_value_for_trace(value, max_len=60)
            parts.append(f"{name}={formatted}")

        return ", ".join(parts)
    except (TypeError, ValueError):
        parts = [repr(value) for value in args]
        parts += [f"{name}={repr(value)}" for name, value in kwargs.items()]
        return ", ".join(parts)


def trace(func=None, *, timeit=True, show_args=True, show_return=True, show_type=True):
    """
    Decorator to display function entry and exit automatically.

    Usage:
        @siren.trace
        def foo(...):
            ...

    Optional configuration:
        @siren.trace(timeit=True, show_args=False, show_type=True)
    """

    def decorator(target):
        def wrapper(*args, **kwargs):
            arg_text = _format_trace_args(target, args, kwargs) if show_args else ""
            call_label = "Calling {}".format(target.__name__)
            if arg_text:
                call_label += "({})".format(arg_text)
            else:
                call_label += "()"

            start = time.perf_counter() if timeit else None
            siren.info(call_label)

            result = None
            exception_occurred = False
            try:
                result = target(*args, **kwargs)
            except Exception as e:
                exception_occurred = True
                exc_type = type(e).__name__
                exc_msg = str(e)
                siren.info(f"Exception in {target.__name__} -> {exc_type}: {exc_msg}")
                raise
            finally:
                if not exception_occurred:
                    elapsed_text = ""
                    if timeit:
                        elapsed = time.perf_counter() - start
                        elapsed_text = " ({:.6f}s)".format(elapsed)

                    if show_return and result is not None:
                        result_text = _format_value_for_trace(result, max_len=100)
                        type_text = f" [{type(result).__name__}]" if show_type else ""
                        siren.info(
                            "Returned from {} -> {}{}{}".format(
                                target.__name__, result_text, type_text, elapsed_text
                            )
                        )
                    elif show_return and result is None and timeit:
                        siren.info(
                            "Completed {} (None){}".format(
                                target.__name__, elapsed_text
                            )
                        )

            return result

        return wrapper

    if func is None:
        return decorator

    return decorator(func)


def info(*args, **kwargs):
    """
    Siren info message
    """
    siren(*args, **kwargs)


def set_quiet(enabled=True):
    """Enable or disable output (quiet mode)."""
    _SIREN_CONFIG["quiet"] = enabled


def set_logfile(filepath):
    """Set a file to log all siren output to."""
    _SIREN_CONFIG["logfile"] = filepath


def set_enabled(enabled=True):
    """Enable or disable siren completely."""
    _SIREN_CONFIG["enabled"] = enabled


def get_config():
    """Get current siren configuration."""
    return _SIREN_CONFIG.copy()


def diff(obj1, obj2, label="DIFF"):
    """
    Compare two objects and display differences.
    
    Usage:
        before = {"name": "Alice", "age": 30}
        after = {"name": "Alice", "age": 31, "city": "NYC"}
        siren.diff(before, after)
    """
    frame = inspect.currentframe().f_back
    prefix = _prefix(frame, label)

    if type(obj1) != type(obj2):
        _print_output(f"{prefix} {COLOR}Type mismatch: {type(obj1).__name__} vs {type(obj2).__name__}{RESET}")
        return

    if isinstance(obj1, dict) and isinstance(obj2, dict):
        all_keys = set(obj1.keys()) | set(obj2.keys())

        for key in sorted(all_keys):
            if key not in obj1:
                _print_output(f"{prefix} {COLOR}[+] {key}: {pprint.pformat(obj2[key])} (new){RESET}")
            elif key not in obj2:
                _print_output(f"{prefix} {COLOR}[-] {key}: {pprint.pformat(obj1[key])} (removed){RESET}")
            elif obj1[key] != obj2[key]:
                _print_output(
                    f"{prefix} {COLOR}[~] {key}: {pprint.pformat(obj1[key])} → {pprint.pformat(obj2[key])} (changed){RESET}"
                )

    elif isinstance(obj1, (list, tuple)) and isinstance(obj2, (list, tuple)):
        max_len = max(len(obj1), len(obj2))

        for i in range(max_len):
            if i >= len(obj1):
                _print_output(f"{prefix} {COLOR}[+] [{i}]: {pprint.pformat(obj2[i])} (new){RESET}")
            elif i >= len(obj2):
                _print_output(f"{prefix} {COLOR}[-] [{i}]: {pprint.pformat(obj1[i])} (removed){RESET}")
            elif obj1[i] != obj2[i]:
                _print_output(
                    f"{prefix} {COLOR}[~] [{i}]: {pprint.pformat(obj1[i])} → {pprint.pformat(obj2[i])} (changed){RESET}"
                )

    else:
        if obj1 == obj2:
            _print_output(f"{prefix} {COLOR}No differences{RESET}")
        else:
            _print_output(f"{prefix} {COLOR}Before: {pprint.pformat(obj1)}{RESET}")
            _print_output(f"{prefix} {COLOR}After: {pprint.pformat(obj2)}{RESET}")


def breakpoint_debug():
    """
    Interactive debugger with siren context.
    Pauses execution and allows inspection.
    
    Usage:
        x = 42
        siren.breakpoint()  # Pauses here
    """
    frame = inspect.currentframe().f_back
    prefix = _prefix(frame, "BREAKPOINT")

    local_vars = frame.f_locals
    _print_output(f"{prefix} {COLOR}=== BREAKPOINT ==={RESET}")
    _print_output(f"{prefix} {COLOR}Locals:{RESET}")

    for name, value in sorted(local_vars.items()):
        if not name.startswith("_"):
            formatted = _format_value_for_trace(value, max_len=80)
            _print_output(f"{prefix} {COLOR}  {name} = {formatted}{RESET}")

    _print_output(f"{prefix} {COLOR}Press Ctrl+C to continue or 'd' for debugger...{RESET}")

    try:
        import sys
        if sys.stdin.isatty():
            response = input(">>> ").strip()
            if response.lower() == "d":
                import pdb
                pdb.set_trace()
    except (EOFError, KeyboardInterrupt):
        pass

    _print_output(f"{prefix} {COLOR}Continuing execution...{RESET}")


siren.trace = trace
siren.set_quiet = set_quiet
siren.set_logfile = set_logfile
siren.set_enabled = set_enabled
siren.get_config = get_config
siren.diff = diff
siren.breakpoint = breakpoint_debug
siren.info = info