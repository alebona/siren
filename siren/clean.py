# -*- coding: utf-8 -*-
from __future__ import print_function

import os
import sys
import re

TOKEN_NAME = "siren"

CALL_RE = re.compile(r"\bsiren\s*\(")

# detecta import de siren
IMPORT_RE = re.compile(r"^\s*from\s+siren\s+import\s+siren")

# ANSI para rosa
PINK = "\033[95m"
RESET = "\033[0m"
EMOJI = "🧜‍♀️"


def line_calls_siren(line):
    stripped = line.strip()

    # ignorar outros imports
    if stripped.startswith("import "):
        # mas remove import específico
        if IMPORT_RE.match(stripped):
            return True
        return False

    if CALL_RE.search(line):
        return True

    return False


def clean_file(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except TypeError:
        with open(path, "r") as f:
            lines = f.readlines()

    new_lines = []
    removed = 0

    for line in lines:
        if line_calls_siren(line):
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
    print("[{emoji}{pink}SIREN CLEAN]:{reset} {removed} linhas removidas".format(
        emoji=EMOJI,
        pink=PINK,
        reset=RESET,
        removed=removed
    ))


if __name__ == "__main__":
    main()