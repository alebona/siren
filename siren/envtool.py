# -*- coding: utf-8 -*-
"""
Compare a .env file against its .env.example, catching drift.

Usage:
    siren-env diff
    siren-env diff --example .env.sample --env .env.local
"""
from __future__ import print_function

import argparse
import io
import sys

from ._cli import banner
from ._output import safe_print


def _parse_env_file(path):
    keys = set()
    try:
        with io.open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key = line.split("=", 1)[0].strip()
                if key:
                    keys.add(key)
    except (IOError, OSError):
        return None
    return keys


def diff(example_path, env_path):
    """
    Compare the keys of two env files.

    Returns a dict: {"missing_in_env": [...], "missing_in_example": [...]}
    or None for a file if it couldn't be read.
    """
    example_keys = _parse_env_file(example_path)
    env_keys = _parse_env_file(env_path)

    return {
        "example_keys": example_keys,
        "env_keys": env_keys,
        "missing_in_env": sorted(example_keys - env_keys) if example_keys is not None and env_keys is not None else [],
        "missing_in_example": sorted(env_keys - example_keys) if example_keys is not None and env_keys is not None else [],
    }


def main():
    parser = argparse.ArgumentParser(prog="siren-env")
    subparsers = parser.add_subparsers(dest="command")

    diff_parser = subparsers.add_parser("diff", help="Compare .env against .env.example")
    diff_parser.add_argument("--example", default=".env.example")
    diff_parser.add_argument("--env", default=".env")

    args = parser.parse_args()

    if args.command != "diff":
        parser.print_help()
        sys.exit(1)

    result = diff(args.example, args.env)

    if result["example_keys"] is None:
        safe_print(banner("ENV", "Error: could not read {}".format(args.example)))
        sys.exit(1)
    if result["env_keys"] is None:
        safe_print(banner("ENV", "Error: could not read {}".format(args.env)))
        sys.exit(1)

    if not result["missing_in_env"] and not result["missing_in_example"]:
        safe_print(banner("ENV", "{} and {} are in sync".format(args.example, args.env)))
        sys.exit(0)

    for key in result["missing_in_env"]:
        safe_print(banner("ENV", "[-] {} is in {} but missing from {}".format(key, args.example, args.env)))
    for key in result["missing_in_example"]:
        safe_print(banner("ENV", "[+] {} is in {} but missing from {}".format(key, args.env, args.example)))

    sys.exit(1)


if __name__ == "__main__":
    main()
