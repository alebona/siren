# -*- coding: utf-8 -*-
"""
Toggle automatic injection of `siren` into builtins for every Python
process started from the current environment (venv), by managing a
.pth file in site-packages.

Usage:
    siren-autoload on       # enable
    siren-autoload off      # disable
    siren-autoload status   # check current state
"""
from __future__ import print_function

import os
import sys
import sysconfig

from ._output import safe_print

PTH_FILENAME = "siren-autoload.pth"
PTH_CONTENT = (
    'import sys; exec("try:\\n    import siren\\nexcept Exception:\\n    pass")\n'
)

COLOR = "\033[38;2;255;105;180m"
RESET = "\033[0m"
EMOJI = "🧜‍"


def _pth_path():
    return os.path.join(sysconfig.get_path("purelib"), PTH_FILENAME)


def enable():
    path = _pth_path()
    with open(path, "w", encoding="utf-8") as f:
        f.write(PTH_CONTENT)
    return path


def disable():
    path = _pth_path()
    if os.path.exists(path):
        os.remove(path)
        return True
    return False


def is_enabled():
    return os.path.exists(_pth_path())


def main():
    args = sys.argv[1:]
    command = args[0] if args else "status"

    if command == "on":
        path = enable()
        safe_print("{}[{} SIREN AUTOLOAD]{} enabled -> {}".format(COLOR, EMOJI, RESET, path))
    elif command == "off":
        removed = disable()
        message = "disabled" if removed else "was already disabled"
        safe_print("{}[{} SIREN AUTOLOAD]{} {}".format(COLOR, EMOJI, RESET, message))
    elif command == "status":
        state = "enabled" if is_enabled() else "disabled"
        safe_print("{}[{} SIREN AUTOLOAD]{} {}".format(COLOR, EMOJI, RESET, state))
    else:
        print("Usage: siren-autoload [on|off|status]")
        sys.exit(1)


if __name__ == "__main__":
    main()
