# -*- coding: utf-8 -*-
from __future__ import print_function
import os
import sys
import tokenize

TOKEN_NAME = "siren"


def line_calls_siren(line):
    try:
        tokens = list(tokenize.generate_tokens(lambda L=[line]: L.pop(0)))
    except Exception:
        return False

    for i, tok in enumerate(tokens):
        if tok.type == tokenize.NAME and tok.string == TOKEN_NAME:
            # verificar se próximo token é "("
            if i + 1 < len(tokens):
                next_tok = tokens[i + 1]
                if next_tok.string == "(":
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

    for base, _, files in os.walk(root):
        # ignorar venv automaticamente
        if "venv" in base:
            continue

        for name in files:
            if name.endswith(".py"):
                path = os.path.join(base, name)
                total_removed += clean_file(path)

    return total_removed


def main():
    target = sys.argv[1] if len(sys.argv) > 1 else "."
    removed = clean_directory(target)
    print("SIREN CLEAN: {} linhas removidas".format(removed))


if __name__ == "__main__":
    main()
