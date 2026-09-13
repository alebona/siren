# -*- coding: utf-8 -*-
"""Shared formatting helpers for the siren-* CLI tools."""
from __future__ import print_function

from datetime import datetime

COLOR = "\033[38;2;255;105;180m"
RESET = "\033[0m"
EMOJI = "🧜‍"


def format_timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def banner(tag, message):
    return "{color}[{emoji} SIREN {tag} {ts}]{reset} {color}{message}{reset}".format(
        color=COLOR,
        emoji=EMOJI,
        tag=tag,
        ts=format_timestamp(),
        message=message,
        reset=RESET,
    )
