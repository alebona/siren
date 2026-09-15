import io
import shutil
import sys
import tempfile
import textwrap
import unittest

from siren import quality


class TestDeadCode(unittest.TestCase):
    def test_finds_unused_import(self):
        source = textwrap.dedent("""
            import os
            import sys

            print(sys.argv)
        """)
        result = quality.find_dead_code(source)
        names = [name for name, _ in result["unused_imports"]]
        self.assertIn("os", names)
        self.assertNotIn("sys", names)

    def test_finds_unused_module_level_function(self):
        source = textwrap.dedent("""
            def used():
                pass

            def unused():
                pass

            used()
        """)
        result = quality.find_dead_code(source)
        names = [name for name, _ in result["unused_defs"]]
        self.assertIn("unused", names)
        self.assertNotIn("used", names)


class TestLint(unittest.TestCase):
    def test_finds_bare_except(self):
        source = textwrap.dedent("""
            try:
                pass
            except:
                pass
        """)
        issues = quality.find_lint_issues(source)
        kinds = [kind for kind, _, _ in issues]
        self.assertIn("bare-except", kinds)

    def test_finds_todo_comment(self):
        source = "# TODO: fix this\nx = 1\n"
        issues = quality.find_lint_issues(source)
        kinds = [kind for kind, _, _ in issues]
        self.assertIn("todo", kinds)

    def test_finds_leftover_debugger_calls(self):
        source = textwrap.dedent("""
            import pdb

            def f():
                pdb.set_trace()
                breakpoint()
        """)
        issues = quality.find_lint_issues(source)
        kinds = [kind for kind, _, _ in issues]
        self.assertEqual(kinds.count("debugger"), 2)


class TestComplexity(unittest.TestCase):
    def test_simple_function_has_complexity_one(self):
        source = textwrap.dedent("""
            def simple():
                return 1
        """)
        results = quality.find_complexity(source)
        self.assertEqual(results[0], ("simple", 2, 1))

    def test_branches_increase_complexity(self):
        source = textwrap.dedent("""
            def branchy(x):
                if x:
                    pass
                elif x == 2:
                    pass
                for i in range(x):
                    if i:
                        pass
                return x
        """)
        results = quality.find_complexity(source)
        name, lineno, complexity = results[0]
        self.assertEqual(name, "branchy")
        self.assertGreater(complexity, 1)


class TestEncodingDeclaration(unittest.TestCase):
    """
    Regression test for a real bug: every file in this project (and most
    real Python 2 codebases) starts with a `# -*- coding: utf-8 -*-` line.
    On Python 2, ast.parse()/compile() rejects an already-decoded unicode
    string that still contains that declaration with
    `SyntaxError: encoding declaration in Unicode string`. quality.py's
    _read() decodes to unicode before parsing, so this hit every single
    file, and find_dead_code/find_lint_issues/find_complexity all raised.
    This can't reproduce the Python-2-only crash on a Python 3 test run,
    but it locks in that source carrying the declaration parses correctly
    through the real code path (_parse's encode-back-to-bytes fix), so a
    regression that mishandles the encode/decode would still be caught.
    """

    SOURCE = textwrap.dedent("""\
        # -*- coding: utf-8 -*-
        import os

        def unused():
            pass
    """)

    def test_dead_code_parses_file_with_coding_declaration(self):
        result = quality.find_dead_code(self.SOURCE)
        names = [name for name, _ in result["unused_imports"]]
        self.assertIn("os", names)

    def test_lint_parses_file_with_coding_declaration(self):
        source = self.SOURCE.replace("def unused():\n    pass", "try:\n    pass\nexcept:\n    pass")
        issues = quality.find_lint_issues(source)
        kinds = [kind for kind, _, _ in issues]
        self.assertIn("bare-except", kinds)

    def test_complexity_parses_file_with_coding_declaration(self):
        results = quality.find_complexity(self.SOURCE)
        names = [name for name, _, _ in results]
        self.assertIn("unused", names)


class TestUnparseableFilesAreReported(unittest.TestCase):
    """
    Regression test: _run_deadcode/_run_lint/_run_complexity used to
    silently `continue` past a SyntaxError, then still print "no issues
    found" - a false-clean report, since the file was never actually
    analyzed. They must now report the failure and return a non-zero
    exit code instead of claiming a clean bill of health.
    """

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmpdir, True)
        with io.open(self.tmpdir + "/broken.py", "w", encoding="utf-8") as f:
            f.write(u"def broken(:\n    pass\n")  # deliberately invalid syntax

    def _capture(self, func, *args):
        captured = io.StringIO()
        original_stdout = sys.stdout
        sys.stdout = captured
        try:
            exit_code = func(*args)
        finally:
            sys.stdout = original_stdout
        return exit_code, captured.getvalue()

    def test_deadcode_reports_unparseable_file_instead_of_claiming_clean(self):
        exit_code, output = self._capture(quality._run_deadcode, self.tmpdir)
        self.assertEqual(exit_code, 1)
        self.assertIn("could not parse", output)
        # The old bug printed this exact unqualified message even when
        # nothing was actually analyzed; it must now be qualified.
        self.assertIn("in the files that could be parsed", output)

    def test_lint_reports_unparseable_file_instead_of_claiming_clean(self):
        exit_code, output = self._capture(quality._run_lint, self.tmpdir)
        self.assertEqual(exit_code, 1)
        self.assertIn("could not parse", output)

    def test_complexity_reports_unparseable_file(self):
        exit_code, output = self._capture(quality._run_complexity, self.tmpdir)
        self.assertEqual(exit_code, 1)
        self.assertIn("could not parse", output)


if __name__ == "__main__":
    unittest.main()
