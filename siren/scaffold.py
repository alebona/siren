# -*- coding: utf-8 -*-
"""
Generate small, opinionated Python file/project skeletons.

Usage:
    siren-scaffold script my_tool
    siren-scaffold package my_package
    siren-scaffold class Widget
    siren-scaffold dataclass Point
    siren-scaffold test Widget
"""
from __future__ import print_function

import argparse
import io
import os
import sys

from ._cli import banner
from ._output import safe_print

try:
    text_type = unicode  # Python 2
except NameError:
    text_type = str  # Python 3

SCRIPT_TEMPLATE = '''# -*- coding: utf-8 -*-
"""{name}"""


def main():
    pass


if __name__ == "__main__":
    main()
'''

PACKAGE_INIT_TEMPLATE = ""

PACKAGE_MODULE_TEMPLATE = '''# -*- coding: utf-8 -*-
"""Core module for {name}."""
'''

PACKAGE_TEST_TEMPLATE = '''# -*- coding: utf-8 -*-
import unittest


class Test{class_name}(unittest.TestCase):
    def test_placeholder(self):
        self.assertTrue(True)


if __name__ == "__main__":
    unittest.main()
'''

CLASS_TEMPLATE = '''# -*- coding: utf-8 -*-


class {class_name}(object):
    def __init__(self):
        pass
'''

DATACLASS_TEMPLATE = '''# -*- coding: utf-8 -*-
"""Plain-Python value object (avoids the dataclasses module, Python 3.7+ only)."""


class {class_name}(object):
    def __init__(self, *args, **kwargs):
        pass

    def __repr__(self):
        return "{class_name}()"

    def __eq__(self, other):
        return isinstance(other, {class_name}) and self.__dict__ == other.__dict__

    def __ne__(self, other):
        return not self.__eq__(other)
'''

TEST_TEMPLATE = '''# -*- coding: utf-8 -*-
import unittest


class Test{class_name}(unittest.TestCase):
    def test_placeholder(self):
        self.assertTrue(True)


if __name__ == "__main__":
    unittest.main()
'''


def _class_name(name):
    parts = name.replace("-", "_").split("_")
    return "".join(part.capitalize() for part in parts if part)


def _write(path, content):
    if os.path.exists(path):
        raise IOError("Refusing to overwrite existing file: {}".format(path))
    if not isinstance(content, text_type):
        content = content.decode("utf-8")
    with io.open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path


def scaffold_script(name, base_path):
    path = os.path.join(base_path, "{}.py".format(name))
    _write(path, SCRIPT_TEMPLATE.format(name=name))
    return [path]


def scaffold_package(name, base_path):
    pkg_dir = os.path.join(base_path, name)
    tests_dir = os.path.join(pkg_dir, "tests")

    if os.path.exists(pkg_dir):
        raise IOError("Refusing to overwrite existing directory: {}".format(pkg_dir))

    os.makedirs(tests_dir)

    created = []
    created.append(_write(os.path.join(pkg_dir, "__init__.py"), PACKAGE_INIT_TEMPLATE))
    created.append(_write(os.path.join(pkg_dir, "core.py"), PACKAGE_MODULE_TEMPLATE.format(name=name)))
    created.append(_write(os.path.join(tests_dir, "__init__.py"), PACKAGE_INIT_TEMPLATE))
    created.append(_write(
        os.path.join(tests_dir, "test_core.py"),
        PACKAGE_TEST_TEMPLATE.format(class_name=_class_name(name)),
    ))
    return created


def scaffold_class(name, base_path):
    class_name = _class_name(name)
    path = os.path.join(base_path, "{}.py".format(name.lower()))
    _write(path, CLASS_TEMPLATE.format(class_name=class_name))
    return [path]


def scaffold_dataclass(name, base_path):
    class_name = _class_name(name)
    path = os.path.join(base_path, "{}.py".format(name.lower()))
    _write(path, DATACLASS_TEMPLATE.format(class_name=class_name))
    return [path]


def scaffold_test(name, base_path):
    class_name = _class_name(name)
    path = os.path.join(base_path, "test_{}.py".format(name.lower()))
    _write(path, TEST_TEMPLATE.format(class_name=class_name))
    return [path]


TEMPLATES = {
    "script": scaffold_script,
    "package": scaffold_package,
    "class": scaffold_class,
    "dataclass": scaffold_dataclass,
    "test": scaffold_test,
}


def generate(template, name, base_path="."):
    if template not in TEMPLATES:
        raise ValueError("Unknown template: {}. Choose from: {}".format(
            template, ", ".join(sorted(TEMPLATES))
        ))
    return TEMPLATES[template](name, base_path)


def main():
    parser = argparse.ArgumentParser(prog="siren-scaffold")
    parser.add_argument("template", choices=sorted(TEMPLATES))
    parser.add_argument("name")
    parser.add_argument("--path", default=".", help="Directory to generate into (default: current directory)")
    args = parser.parse_args()

    try:
        created = generate(args.template, args.name, args.path)
    except (IOError, OSError, ValueError) as e:
        safe_print(banner("SCAFFOLD", "Error: {}".format(e)))
        sys.exit(1)

    safe_print(banner("SCAFFOLD", "created {} file(s):".format(len(created))))
    for path in created:
        safe_print(banner("SCAFFOLD", "  {}".format(path)))


if __name__ == "__main__":
    main()
