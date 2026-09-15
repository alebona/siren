import os
import shutil
import tempfile
import unittest

from siren import scaffold


class TestScaffold(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmpdir, True)

    def _compile_all(self, paths):
        for path in paths:
            with open(path, encoding="utf-8") as f:
                compile(f.read(), path, "exec")

    def test_script_template(self):
        created = scaffold.generate("script", "my_tool", self.tmpdir)
        self.assertEqual(len(created), 1)
        self.assertTrue(os.path.exists(os.path.join(self.tmpdir, "my_tool.py")))
        self._compile_all(created)

    def test_package_template(self):
        created = scaffold.generate("package", "my_pkg", self.tmpdir)
        self.assertEqual(len(created), 4)
        self.assertTrue(os.path.exists(os.path.join(self.tmpdir, "my_pkg", "__init__.py")))
        self.assertTrue(os.path.exists(os.path.join(self.tmpdir, "my_pkg", "core.py")))
        self.assertTrue(os.path.exists(os.path.join(self.tmpdir, "my_pkg", "tests", "test_core.py")))
        self._compile_all(created)

    def test_class_template(self):
        created = scaffold.generate("class", "widget", self.tmpdir)
        self._compile_all(created)
        with open(created[0], encoding="utf-8") as f:
            content = f.read()
        self.assertIn("class Widget(object):", content)

    def test_dataclass_template(self):
        created = scaffold.generate("dataclass", "point", self.tmpdir)
        self._compile_all(created)
        with open(created[0], encoding="utf-8") as f:
            content = f.read()
        self.assertIn("class Point(object):", content)
        self.assertIn("__eq__", content)

    def test_test_template(self):
        created = scaffold.generate("test", "widget", self.tmpdir)
        self._compile_all(created)
        with open(created[0], encoding="utf-8") as f:
            content = f.read()
        self.assertIn("class TestWidget(unittest.TestCase):", content)

    def test_class_name_preserves_existing_camel_case(self):
        # Regression: str.capitalize() also lowercases the rest of the
        # string, mangling "IssoEhUmaClasse" into "Issoehumaclasse".
        self.assertEqual(scaffold._class_name("IssoEhUmaClasse"), "IssoEhUmaClasse")

    def test_class_name_capitalizes_snake_and_kebab_case(self):
        self.assertEqual(scaffold._class_name("my_widget"), "MyWidget")
        self.assertEqual(scaffold._class_name("my-widget"), "MyWidget")

    def test_class_template_preserves_camel_case_name(self):
        created = scaffold.generate("class", "IssoEhUmaClasse", self.tmpdir)
        self._compile_all(created)
        with open(created[0], encoding="utf-8") as f:
            content = f.read()
        self.assertIn("class IssoEhUmaClasse(object):", content)

    def test_refuses_to_overwrite_existing_file(self):
        scaffold.generate("script", "dup", self.tmpdir)
        with self.assertRaises(IOError):
            scaffold.generate("script", "dup", self.tmpdir)

    def test_unknown_template_raises(self):
        with self.assertRaises(ValueError):
            scaffold.generate("nope", "x", self.tmpdir)


if __name__ == "__main__":
    unittest.main()
