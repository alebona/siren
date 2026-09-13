import os
import shutil
import tempfile
import unittest

from siren import envtool


class TestEnvTool(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmpdir, True)

    def _write(self, name, content):
        path = os.path.join(self.tmpdir, name)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return path

    def test_diff_reports_missing_in_env(self):
        example = self._write(".env.example", "FOO=1\nBAR=2\n")
        env = self._write(".env", "FOO=1\n")

        result = envtool.diff(example, env)

        self.assertEqual(result["missing_in_env"], ["BAR"])
        self.assertEqual(result["missing_in_example"], [])

    def test_diff_reports_missing_in_example(self):
        example = self._write(".env.example", "FOO=1\n")
        env = self._write(".env", "FOO=1\nEXTRA=2\n")

        result = envtool.diff(example, env)

        self.assertEqual(result["missing_in_env"], [])
        self.assertEqual(result["missing_in_example"], ["EXTRA"])

    def test_diff_ignores_comments_and_blank_lines(self):
        example = self._write(".env.example", "# comment\n\nFOO=1\n")
        env = self._write(".env", "FOO=1\n")

        result = envtool.diff(example, env)

        self.assertEqual(result["missing_in_env"], [])
        self.assertEqual(result["missing_in_example"], [])

    def test_diff_returns_none_for_missing_file(self):
        env = self._write(".env", "FOO=1\n")
        result = envtool.diff(os.path.join(self.tmpdir, "nope.example"), env)
        self.assertIsNone(result["example_keys"])


if __name__ == "__main__":
    unittest.main()
