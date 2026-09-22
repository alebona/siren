import sys
import unittest

try:
    from io import StringIO
except ImportError:  # Python 2
    from StringIO import StringIO

from unittest import mock

from siren import cli


class TestCli(unittest.TestCase):
    def _run(self, argv):
        out = StringIO()
        with mock.patch.object(sys, "argv", ["siren"] + argv), \
                mock.patch("sys.stdout", out):
            try:
                cli.main()
            except SystemExit as e:
                return out.getvalue(), e.code
        return out.getvalue(), None

    def test_no_args_lists_every_command(self):
        output, code = self._run([])
        self.assertIsNone(code)
        for name, _category, _description in cli.COMMANDS:
            self.assertIn(name, output)

    def test_help_flag_behaves_like_no_args(self):
        output, code = self._run(["--help"])
        self.assertIsNone(code)
        self.assertIn("siren-scaffold", output)
        self.assertIn("siren-login", output)

    def test_filter_by_category(self):
        output, code = self._run(["pro"])
        self.assertIsNone(code)
        self.assertIn("siren-login", output)
        self.assertIn("siren-events", output)
        self.assertNotIn("CLI productivity", output)

    def test_category_filter_does_not_match_productivity_substring(self):
        output, code = self._run(["pro"])
        self.assertNotIn("CLI productivity", output)

    def test_filter_by_command_name(self):
        output, code = self._run(["snippet"])
        self.assertIsNone(code)
        self.assertIn("siren-snippet", output)
        self.assertNotIn("siren-env", output)

    def test_filter_with_no_match_exits_nonzero(self):
        output, code = self._run(["not-a-real-thing"])
        self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()
