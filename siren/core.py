# -*- coding: utf-8 -*-
from __future__ import print_function

import pprint
import inspect
import linecache
import re
import time
import os

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


def _extract_args(source):
    m = re.search(r"siren\s*\((.*)\)", source)
    if not m:
        return []

    inside = m.group(1)

    parts = [p.strip() for p in inside.split(",")]

    return parts


def _prefix(frame, label=None):

    lineno = frame.f_lineno
    filename = frame.f_code.co_filename.split("/")[-1]

    base = "{}[{}SIREN {}:{}]{}".format(
        COLOR,
        EMOJI,
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
    """

    frame = inspect.currentframe().f_back

    label = kwargs.get("label")
    timeit = kwargs.get("timeit", False)

    start = None

    if timeit:
        start = time.time()

    source = _get_call_source(frame)
    args = _extract_args(source)

    prefix = _prefix(frame, label)

    for i, v in enumerate(values):

        name = args[i] if i < len(args) else "?"

        print(prefix, end=" ")

        if _is_simple(v):
            print("{}{} = {}{}".format(COLOR, name, v, RESET))
        else:
            text = pprint.pformat(v)
            print("{}{} = {}{}".format(COLOR, name, text, RESET))

    if timeit:
        elapsed = time.time() - start
        print(
            "{}[{} SIREN TIME]{} {}{:.6f}s{}".format(
                COLOR,
                EMOJI,
                RESET,
                COLOR,
                elapsed,
                RESET,
            )
        )

    if len(values) == 1:
        return values[0]

    return values

def trace(func):
    """
    Decorator para mostrar entrada e saída de funções automaticamente.
    """

    def wrapper(*args, **kwargs):
        siren.info("Calling {}".format(func.__name__))
        result = func(*args, **kwargs)
        siren.info("Returned from {} -> {}".format(func.__name__, result))
        return result

    return wrapper

def info(*args, **kwargs):
    """
    Siren info message
    """
    siren(*args, **kwargs)



siren.trace = trace