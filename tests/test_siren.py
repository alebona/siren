import io
import os
import re
import sys
import tempfile
import textwrap
import unittest

from siren import clean, core


class TestSirenCleaner(unittest.TestCase):
    def _write_temp_file(self, content):
        temp_file = tempfile.NamedTemporaryFile("w+", delete=False, encoding="utf-8")
        temp_file.write(textwrap.dedent(content))
        temp_file.flush()
        temp_file.close()
        return temp_file.name

    def test_clean_file_removes_siren_calls_and_imports(self):
        source = """
            from siren import siren
            x = 1
            siren(x)
            print('ok')
            # siren(x) should remain in comments
            text = 'siren(x) inside string'
        """

        path = self._write_temp_file(source)
        removed = clean.clean_file(path)

        with open(path, encoding="utf-8") as f:
            result = f.read()

        os.unlink(path)

        self.assertEqual(removed, 2)
        self.assertIn("x = 1", result)
        self.assertIn("print('ok')", result)
        self.assertIn("# siren(x) should remain in comments", result)
        self.assertIn("text = 'siren(x) inside string'", result)
        self.assertNotIn("siren(x)\n", result)

    def test_clean_file_handles_multiline_siren_call(self):
        source = """
            def foo():
                siren(
                    x,
                    y,
                )
                print('done')
        """

        path = self._write_temp_file(source)
        removed = clean.clean_file(path)

        with open(path, encoding="utf-8") as f:
            result = f.read()

        os.unlink(path)

        self.assertEqual(removed, 4)
        self.assertIn("def foo():", result)
        self.assertIn("print('done')", result)
        self.assertNotIn("siren(", result)


class TestSirenCore(unittest.TestCase):
    def test_trace_decorator_logs_calls(self):
        captured = io.StringIO()
        original_stdout = sys.stdout
        sys.stdout = captured

        try:
            @core.trace
            def add(a, b):
                return a + b

            result = add(2, 3)
        finally:
            sys.stdout = original_stdout

        output = captured.getvalue()

        self.assertEqual(result, 5)
        self.assertIn("Calling add(a=2, b=3)", output)
        self.assertRegex(output, r"Returned from add -> 5.*\(\d+\.\d{6}s\)")

    def test_trace_decorator_with_configuration(self):
        captured = io.StringIO()
        original_stdout = sys.stdout
        sys.stdout = captured

        try:
            @core.trace(timeit=True, show_args=False)
            def multiply(a, b):
                return a * b

            result = multiply(3, 4)
        finally:
            sys.stdout = original_stdout

        output = captured.getvalue()

        self.assertEqual(result, 12)
        self.assertIn("Calling multiply()", output)
        self.assertIn("[int]", output)
        self.assertRegex(output, r"Returned from multiply -> 12.*\(\d+\.\d{6}s\)")

    def test_trace_decorator_with_exception(self):
        captured = io.StringIO()
        original_stdout = sys.stdout
        sys.stdout = captured

        try:
            @core.trace
            def divide(a, b):
                return a / b

            try:
                divide(5, 0)
            except ZeroDivisionError:
                pass
        finally:
            sys.stdout = original_stdout

        output = captured.getvalue()

        self.assertIn("Calling divide(a=5, b=0)", output)
        self.assertIn("Exception in divide", output)
        self.assertIn("ZeroDivisionError", output)

    def test_siren_extracts_multiline_argument_names(self):
        captured = io.StringIO()
        original_stdout = sys.stdout
        sys.stdout = captured

        try:
            x = 1
            y = [2, 3]
            siren(
                x,
                y,
            )
        finally:
            sys.stdout = original_stdout

        output = captured.getvalue()

        self.assertIn("x =", output)
        self.assertIn("y =", output)

    def test_clean_main_prints_timestamp_and_label(self):
        captured = io.StringIO()
        original_stdout = sys.stdout
        original_argv = sys.argv

        temp_file = tempfile.NamedTemporaryFile("w+", delete=False, encoding="utf-8")
        try:
            temp_file.write("siren(x)\n")
            temp_file.flush()
            temp_file.close()
            temp_path = temp_file.name

            sys.stdout = captured
            sys.argv = ["siren-clean", temp_path]

            try:
                clean.main()
            finally:
                sys.stdout = original_stdout
                sys.argv = original_argv

            output = captured.getvalue()

            self.assertIn("SIREN CLEAN", output)
            self.assertIn("linhas removidas", output)
            self.assertRegex(output, r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}")
        finally:
            os.unlink(temp_file.name)

    def test_siren_conditional_if_equals(self):
        captured = io.StringIO()
        original_stdout = sys.stdout
        sys.stdout = captured

        try:
            x = 5
            siren(x, if_equals=5)  # Should print
            output1 = captured.getvalue()
            captured.truncate(0)
            captured.seek(0)

            x = 10
            siren(x, if_equals=5)  # Should NOT print
            output2 = captured.getvalue()
        finally:
            sys.stdout = original_stdout

        self.assertIn("x = 5", output1)
        self.assertEqual(output2, "")

    def test_siren_conditional_if_len_gt(self):
        captured = io.StringIO()
        original_stdout = sys.stdout
        sys.stdout = captured

        try:
            items = [1, 2, 3, 4, 5]
            siren(items, if_len_gt=3)  # Should print (len=5 > 3)
            output = captured.getvalue()
        finally:
            sys.stdout = original_stdout

        self.assertIn("items =", output)

    def test_siren_diff_dicts(self):
        captured = io.StringIO()
        original_stdout = sys.stdout
        sys.stdout = captured

        try:
            before = {"name": "Alice", "age": 30}
            after = {"name": "Alice", "age": 31, "city": "NYC"}
            core.diff(before, after)
            output = captured.getvalue()
        finally:
            sys.stdout = original_stdout

        self.assertIn("[~]", output)  # changed
        self.assertIn("[+]", output)  # added
        self.assertIn("age", output)
        self.assertIn("city", output)

    def test_siren_diff_lists(self):
        captured = io.StringIO()
        original_stdout = sys.stdout
        sys.stdout = captured

        try:
            before = [1, 2, 3]
            after = [1, 2, 3, 4]
            core.diff(before, after)
            output = captured.getvalue()
        finally:
            sys.stdout = original_stdout

        self.assertIn("[+]", output)
        self.assertIn("4", output)


if __name__ == "__main__":
    unittest.main()
