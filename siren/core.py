# -*- coding: utf-8 -*-
from __future__ import print_function

import pprint
import inspect


def _is_simple(value):
    return isinstance(value, (int, float, str, bool, type(None)))


def siren(*values):
    frame = inspect.currentframe().f_back
    lineno = frame.f_lineno
    filename = frame.f_code.co_filename

    prefix = "[SIREN {}:{}]".format(filename, lineno)

    for v in values:
        print(prefix, end=" ")

        if _is_simple(v):
            print(v)
        else:
            pprint.pprint(v)

    if len(values) == 1:
        return values[0]

    return values