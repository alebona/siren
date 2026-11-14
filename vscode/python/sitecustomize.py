# -*- coding: utf-8 -*-
"""
Loaded automatically by Python because the Siren VS Code extension puts this
folder on PYTHONPATH. Importing siren registers `siren` as a builtin, so user
code can call siren(x) without importing anything.

Then chains to any other sitecustomize this one shadows (system Pythons and
some tools ship their own), so adding Siren never disables it.
"""
import os
import sys

try:
    import siren  # noqa: F401
except Exception:
    pass


def _chain():
    here = os.path.dirname(os.path.abspath(__file__))
    others = [p for p in sys.path if os.path.abspath(p or os.curdir) != here]
    try:
        from importlib.machinery import PathFinder
        import importlib.util

        spec = PathFinder.find_spec("sitecustomize", others)
        if spec is None or spec.loader is None:
            return
        module = importlib.util.module_from_spec(spec)
        sys.modules["sitecustomize"] = module
        spec.loader.exec_module(module)
    except ImportError:  # Python 2
        import imp

        try:
            found = imp.find_module("sitecustomize", others)
        except ImportError:
            return
        try:
            sys.modules["sitecustomize"] = imp.load_module("sitecustomize", *found)
        finally:
            if found[0]:
                found[0].close()


try:
    _chain()
except Exception:
    pass
