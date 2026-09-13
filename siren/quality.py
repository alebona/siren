# -*- coding: utf-8 -*-
"""
Lightweight, local code-quality helpers built on the stdlib `ast` module.
No external dependencies (no pyflakes/radon/etc).

Usage:
    siren-quality deadcode [path]
    siren-quality lint [path]
    siren-quality complexity [path]
"""
from __future__ import print_function

import argparse
import ast
import io
import os
import sys
import tokenize

from ._cli import banner
from ._output import safe_print

IGNORE_DIRS = {
    "venv",
    ".venv",
    "__pycache__",
    "doc",
    "docs",
    ".git",
    "node_modules",
}

_DEF_TYPES = tuple(
    t for t in (
        getattr(ast, "FunctionDef", None),
        getattr(ast, "AsyncFunctionDef", None),
        getattr(ast, "ClassDef", None),
    ) if t is not None
)

_FUNC_TYPES = tuple(
    t for t in (
        getattr(ast, "FunctionDef", None),
        getattr(ast, "AsyncFunctionDef", None),
    ) if t is not None
)


def _iter_py_files(root):
    if os.path.isfile(root):
        if root.endswith(".py"):
            yield root
        return

    for base, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d.lower() not in IGNORE_DIRS]
        for name in files:
            if name.endswith(".py"):
                yield os.path.join(base, name)


def _read(path):
    with io.open(path, "r", encoding="utf-8") as f:
        return f.read()


# ---------------------------------------------------------------------------
# deadcode
# ---------------------------------------------------------------------------

def find_dead_code(source, filename="<string>"):
    """
    Heuristic: unused imports, and module-level functions/classes never
    referenced by name anywhere else in the same file. This can't see
    cross-file usage (e.g. something imported elsewhere from this module),
    so treat module-level "unused defs" as candidates to double-check,
    not certainties.
    """
    tree = ast.parse(source, filename=filename)

    imported = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.asname or alias.name.split(".")[0]
                imported[name] = node.lineno
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.name == "*":
                    continue
                name = alias.asname or alias.name
                imported[name] = node.lineno

    used_names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            used_names.add(node.id)

    unused_imports = sorted(
        ((name, lineno) for name, lineno in imported.items() if name not in used_names),
        key=lambda t: t[1],
    )

    defined = {}
    for node in tree.body:
        if isinstance(node, _DEF_TYPES):
            defined[node.name] = node.lineno

    unused_defs = sorted(
        (
            (name, lineno) for name, lineno in defined.items()
            if name not in used_names and not name.startswith("_")
        ),
        key=lambda t: t[1],
    )

    return {"unused_imports": unused_imports, "unused_defs": unused_defs}


# ---------------------------------------------------------------------------
# lint
# ---------------------------------------------------------------------------

def find_lint_issues(source, filename="<string>"):
    issues = []

    try:
        for tok in tokenize.generate_tokens(io.StringIO(source).readline):
            if tok[0] == tokenize.COMMENT:
                text = tok[1]
                upper = text.upper()
                if "TODO" in upper or "FIXME" in upper:
                    issues.append(("todo", tok[2][0], text.strip()))
    except tokenize.TokenError:
        pass

    tree = ast.parse(source, filename=filename)

    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler) and node.type is None:
            issues.append(("bare-except", node.lineno, "bare 'except:' clause"))
        elif isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Attribute) and func.attr == "set_trace" \
                    and isinstance(func.value, ast.Name) and func.value.id == "pdb":
                issues.append(("debugger", node.lineno, "pdb.set_trace() left in code"))
            elif isinstance(func, ast.Name) and func.id == "breakpoint":
                issues.append(("debugger", node.lineno, "breakpoint() left in code"))

    return sorted(issues, key=lambda t: t[1])


# ---------------------------------------------------------------------------
# complexity
# ---------------------------------------------------------------------------

_DECISION_NODES = tuple(
    t for t in (
        ast.If,
        ast.For,
        getattr(ast, "AsyncFor", None),
        ast.While,
        ast.ExceptHandler,
        ast.Assert,
        getattr(ast, "IfExp", None),
    ) if t is not None
)


def _complexity_of(func_node):
    complexity = 1
    for node in ast.walk(func_node):
        if isinstance(node, _DECISION_NODES):
            complexity += 1
        elif isinstance(node, ast.BoolOp):
            complexity += len(node.values) - 1
        elif isinstance(node, ast.comprehension):
            complexity += 1 + len(node.ifs)
    return complexity


def find_complexity(source, filename="<string>"):
    tree = ast.parse(source, filename=filename)
    results = []
    for node in ast.walk(tree):
        if isinstance(node, _FUNC_TYPES):
            results.append((node.name, node.lineno, _complexity_of(node)))
    return sorted(results, key=lambda t: t[2], reverse=True)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _run_deadcode(path):
    found_anything = False
    for filepath in _iter_py_files(path):
        try:
            result = find_dead_code(_read(filepath), filepath)
        except SyntaxError:
            continue

        for name, lineno in result["unused_imports"]:
            found_anything = True
            safe_print(banner("QUALITY", "{}:{} unused import '{}'".format(filepath, lineno, name)))
        for name, lineno in result["unused_defs"]:
            found_anything = True
            safe_print(banner("QUALITY", "{}:{} '{}' is never referenced in this file (candidate, may be used elsewhere)".format(filepath, lineno, name)))

    if not found_anything:
        safe_print(banner("QUALITY", "no dead code candidates found"))
    return 1 if found_anything else 0


def _run_lint(path):
    found_anything = False
    for filepath in _iter_py_files(path):
        try:
            issues = find_lint_issues(_read(filepath), filepath)
        except SyntaxError:
            continue

        for kind, lineno, message in issues:
            found_anything = True
            safe_print(banner("QUALITY", "{}:{} [{}] {}".format(filepath, lineno, kind, message)))

    if not found_anything:
        safe_print(banner("QUALITY", "no lint issues found"))
    return 1 if found_anything else 0


def _run_complexity(path, threshold=10):
    found_high = False
    for filepath in _iter_py_files(path):
        try:
            results = find_complexity(_read(filepath), filepath)
        except SyntaxError:
            continue

        for name, lineno, complexity in results:
            flag = " [HIGH]" if complexity > threshold else ""
            if complexity > threshold:
                found_high = True
            safe_print(banner("QUALITY", "{}:{} {}() complexity={}{}".format(filepath, lineno, name, complexity, flag)))

    return 1 if found_high else 0


def main():
    parser = argparse.ArgumentParser(prog="siren-quality")
    subparsers = parser.add_subparsers(dest="command")

    deadcode_parser = subparsers.add_parser("deadcode")
    deadcode_parser.add_argument("path", nargs="?", default=".")

    lint_parser = subparsers.add_parser("lint")
    lint_parser.add_argument("path", nargs="?", default=".")

    complexity_parser = subparsers.add_parser("complexity")
    complexity_parser.add_argument("path", nargs="?", default=".")
    complexity_parser.add_argument("--threshold", type=int, default=10)

    args = parser.parse_args()

    if args.command == "deadcode":
        sys.exit(_run_deadcode(args.path))
    elif args.command == "lint":
        sys.exit(_run_lint(args.path))
    elif args.command == "complexity":
        sys.exit(_run_complexity(args.path, args.threshold))
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
