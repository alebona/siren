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


if __name__ == "__main__":
    unittest.main()
