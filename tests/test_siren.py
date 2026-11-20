import io
import os
import re
import shutil
import sys
import tempfile
import textwrap
import unittest
from unittest import mock

from siren import autoload, clean, core


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

    def test_clean_file_does_not_strip_siren_function_definition(self):
        source = """
            def siren(*values, **kwargs):
                \"\"\"docstring\"\"\"
                return values

            def info(*args, **kwargs):
                \"\"\"info docstring\"\"\"
                siren(*args, **kwargs)
        """

        path = self._write_temp_file(source)
        removed = clean.clean_file(path)

        with open(path, encoding="utf-8") as f:
            result = f.read()

        os.unlink(path)

        compile(result, path, "exec")
        self.assertEqual(removed, 1)
        self.assertIn("def siren(*values, **kwargs):", result)
        self.assertNotIn("siren(*args, **kwargs)", result)

    def test_clean_file_ignores_import_pattern_inside_string_literal(self):
        source = '''
            source = """
            from siren import siren
            x = 1
            """
            print(source)
        '''

        path = self._write_temp_file(source)
        removed = clean.clean_file(path)

        with open(path, encoding="utf-8") as f:
            result = f.read()

        os.unlink(path)

        self.assertEqual(removed, 0)
        self.assertIn("from siren import siren", result)

    def _clean(self, source):
        path = self._write_temp_file(source)
        removed = clean.clean_file(path)
        result = self._read(path)
        os.unlink(path)
        return removed, result

    def test_clean_file_keeps_pass_when_removal_would_empty_a_block(self):
        removed, result = self._clean("""
            def debug_only():
                siren(x)

            print('after')
        """)

        self.assertEqual(removed, 1)
        self.assertEqual(result, "\ndef debug_only():\n    pass\n\nprint('after')\n")

    def test_clean_file_loop_with_only_a_siren_call(self):
        # The README/guide example: the loop body is only siren(...).
        removed, result = self._clean("""\
            usuario = {"nome": "Ana", "itens": [1, 2, 3]}
            siren(usuario)

            for i in range(3):
                siren(i, label="loop")
        """)

        self.assertEqual(removed, 2)
        self.assertEqual(result, 'usuario = {"nome": "Ana", "itens": [1, 2, 3]}\n\nfor i in range(3):\n    pass\n')

    def test_clean_file_adds_pass_only_where_needed(self):
        removed, result = self._clean("""\
            from siren import siren
            if a:
                siren(a)
            else:
                b = 1
                siren(b)
        """)

        self.assertEqual(removed, 3)
        self.assertEqual(result, "if a:\n    pass\nelse:\n    b = 1\n")

    def test_clean_file_multiline_call_becomes_one_pass(self):
        removed, result = self._clean("""\
            while True:
                siren(
                    x,
                    label="multi",
                )
            print('done')
        """)

        self.assertEqual(removed, 4)
        self.assertEqual(result, "while True:\n    pass\nprint('done')\n")

    def test_clean_file_python2_code_checked_by_python3(self):
        # A Python 2 project (print statement) cleaned with Python 3: the
        # file never compiles here, which used to leave it untouched.
        removed, result = self._clean(u"""\
            # -*- coding: utf-8 -*-
            from siren import siren

            def reajustar(servicos):
                siren("Calculando preços de %d serviços..." % len(servicos))
                print "ok"
                return servicos
        """)

        self.assertEqual(removed, 2)
        self.assertEqual(
            result,
            u'# -*- coding: utf-8 -*-\n\ndef reajustar(servicos):\n    print "ok"\n    return servicos\n',
        )

    def test_clean_file_python2_code_keeps_pass_by_structure(self):
        removed, result = self._clean("""\
            def f(xs):
                for x in xs:
                    siren(x)  # only line in the loop

                    siren(x * 2)
                print "done"
            if True:
                siren(1)
        """)

        self.assertEqual(removed, 3)
        self.assertEqual(
            result,
            'def f(xs):\n    for x in xs:\n        pass\n\n    print "done"\nif True:\n    pass\n',
        )

    def test_clean_file_with_coding_declaration_and_accents(self):
        removed, result = self._clean(u"""\
            # -*- coding: utf-8 -*-
            preço = 10
            siren(preço)
        """)

        self.assertEqual(removed, 1)
        self.assertEqual(result, u"# -*- coding: utf-8 -*-\npreço = 10\n")

    def test_clean_file_latin1_keeps_the_original_bytes(self):
        path = self._write_temp_file("")
        original = u"# -*- coding: latin-1 -*-\npreço = 10\nsiren(preço)\nprint(preço)\n"
        with io.open(path, "wb") as f:
            f.write(original.encode("latin-1"))
        removed = clean.clean_file(path)
        with io.open(path, "rb") as f:
            result = f.read()
        os.unlink(path)

        self.assertEqual(removed, 1)
        self.assertEqual(result, u"# -*- coding: latin-1 -*-\npreço = 10\nprint(preço)\n".encode("latin-1"))

    def test_clean_file_undeclared_latin1_still_cleaned(self):
        # Not valid UTF-8 and no coding line (an old file saved in Latin-1).
        path = self._write_temp_file("")
        with io.open(path, "wb") as f:
            f.write(b"x = 1  # pre\xe7o\nsiren(x)\n")
        removed = clean.clean_file(path)
        with io.open(path, "rb") as f:
            result = f.read()
        os.unlink(path)

        self.assertEqual(removed, 1)
        self.assertEqual(result, b"x = 1  # pre\xe7o\n")

    def test_clean_directory_skips_virtualenvs_of_any_name_and_bad_files(self):
        root = tempfile.mkdtemp()
        try:
            app = os.path.join(root, "app")
            venv = os.path.join(root, "env27")  # a virtualenv, by its pyvenv.cfg
            os.makedirs(app)
            os.makedirs(os.path.join(venv, "lib"))
            with io.open(os.path.join(venv, "pyvenv.cfg"), "w") as f:
                f.write(u"home = /usr/bin\n")
            for path, text in [
                (os.path.join(app, "views.py"), u"x = 1\nsiren(x)\n"),
                (os.path.join(app, "models.py"), u"y = 2\nsiren(y)\n"),
                (os.path.join(venv, "lib", "dep.py"), u"siren(1)\n"),
            ]:
                with io.open(path, "w", encoding="utf-8") as f:
                    f.write(text)
            # A file that fails mid-run must not stop the others.
            original = clean.clean_file

            def flaky(path, dry_run=False):
                if path.endswith("models.py"):
                    raise ValueError("boom")
                return original(path, dry_run=dry_run)

            with mock.patch.object(clean, "clean_file", flaky), \
                    mock.patch("sys.stdout", new_callable=io.StringIO) as out:
                removed = clean.clean_directory(root)

            self.assertEqual(removed, 1)
            self.assertIn("models.py (ValueError: boom)", out.getvalue())
            self.assertEqual(self._read(os.path.join(app, "views.py")), "x = 1\n")
            self.assertEqual(self._read(os.path.join(venv, "lib", "dep.py")), "siren(1)\n")
        finally:
            shutil.rmtree(root, True)

    def test_main_accepts_several_files(self):
        paths = [self._write_temp_file("siren(1)\n") for _ in range(2)]
        try:
            with mock.patch.object(sys, "argv", ["siren-clean"] + paths), \
                    mock.patch("sys.stdout", new_callable=io.StringIO) as out:
                clean.main()
            self.assertIn("2 linhas removidas", out.getvalue())
            self.assertEqual([self._read(p) for p in paths], ["", ""])
        finally:
            for p in paths:
                os.unlink(p)

    def test_clean_file_handles_crlf_line_endings(self):
        path = self._write_temp_file("")
        with io.open(path, "w", encoding="utf-8", newline="") as f:
            f.write(u"for i in x:\r\n    siren(i)\r\n")
        removed = clean.clean_file(path)
        with io.open(path, encoding="utf-8", newline="") as f:
            result = f.read()
        os.unlink(path)

        self.assertEqual(removed, 1)
        self.assertEqual(result, u"for i in x:\r\n    pass\r\n")

    def test_clean_file_keeps_lf_line_endings_on_every_os(self):
        # On Windows the default newline is CRLF; an LF file must stay LF,
        # or git would show every line of the file as changed.
        path = self._write_temp_file("")
        with io.open(path, "w", encoding="utf-8", newline="") as f:
            f.write(u"x = 1\nsiren(x)\nprint(x)\n")
        clean.clean_file(path)
        with io.open(path, encoding="utf-8", newline="") as f:
            result = f.read()
        os.unlink(path)

        self.assertEqual(result, u"x = 1\nprint(x)\n")

    def _read(self, path):
        with open(path, encoding="utf-8") as f:
            return f.read()


class TestSirenAutoload(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        patcher = mock.patch.object(autoload.sysconfig, "get_path", return_value=self.tmpdir)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_enable_writes_pth_file(self):
        self.assertFalse(autoload.is_enabled())

        path = autoload.enable()

        self.assertTrue(os.path.exists(path))
        self.assertTrue(autoload.is_enabled())
        with open(path, encoding="utf-8") as f:
            content = f.read()
        self.assertEqual(content, autoload.PTH_CONTENT)
        # site.py only exec()s .pth lines starting with "import " - must hold.
        self.assertTrue(content.startswith("import "))
        # The line itself must be valid Python (this is what site.py exec()s).
        compile(content, "<pth>", "exec")

    def test_disable_removes_pth_file(self):
        autoload.enable()
        self.assertTrue(autoload.is_enabled())

        removed = autoload.disable()

        self.assertTrue(removed)
        self.assertFalse(autoload.is_enabled())

    def test_disable_when_not_enabled_is_a_noop(self):
        self.assertFalse(autoload.disable())


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

    def test_memory_prints_current_and_peak(self):
        captured = io.StringIO()
        original_stdout = sys.stdout
        sys.stdout = captured

        try:
            core.memory()
            output = captured.getvalue()
        finally:
            sys.stdout = original_stdout

        self.assertIn("current=", output)
        self.assertIn("peak=", output)

    def test_memory_top_allocations(self):
        captured = io.StringIO()
        original_stdout = sys.stdout
        sys.stdout = captured

        try:
            leftover = [str(i) for i in range(1000)]  # noqa: F841
            core.memory(top=3)
            output = captured.getvalue()
        finally:
            sys.stdout = original_stdout

        lines = [line for line in output.splitlines() if "current=" not in line]
        self.assertGreater(len(lines), 0)

    def test_memory_degrades_gracefully_without_tracemalloc(self):
        # tracemalloc doesn't exist on Python 2; core.py sets core.tracemalloc
        # to None in that case instead of failing the whole module import.
        captured = io.StringIO()
        original_stdout = sys.stdout
        sys.stdout = captured

        try:
            with mock.patch.object(core, "tracemalloc", None):
                core.memory()
            output = captured.getvalue()
        finally:
            sys.stdout = original_stdout

        self.assertIn("requires Python 3.4+", output)

    def test_catch_prints_traceback_and_reraises(self):
        captured = io.StringIO()
        original_stdout = sys.stdout
        sys.stdout = captured

        try:
            with self.assertRaises(ValueError):
                with core.catch():
                    raise ValueError("boom")
            output = captured.getvalue()
        finally:
            sys.stdout = original_stdout

        self.assertIn("ValueError", output)
        self.assertIn("boom", output)

    def test_catch_is_silent_when_no_exception(self):
        captured = io.StringIO()
        original_stdout = sys.stdout
        sys.stdout = captured

        try:
            with core.catch():
                pass
            output = captured.getvalue()
        finally:
            sys.stdout = original_stdout

        self.assertEqual(output, "")


if __name__ == "__main__":
    unittest.main()


class TestEditorEvents(unittest.TestCase):
    def setUp(self):
        fd, self.events_path = tempfile.mkstemp(suffix=".jsonl")
        os.close(fd)
        self.env = mock.patch.dict(os.environ, {core.EDITOR_EVENTS_ENV: self.events_path})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        os.remove(self.events_path)

    def _events(self):
        import json
        with io.open(self.events_path, encoding="utf-8") as f:
            return [json.loads(line) for line in f if line.strip()]

    def test_siren_call_writes_event_with_file_line_and_value(self):
        value = {"a": 1}
        with mock.patch("sys.stdout", new_callable=io.StringIO):
            core.siren(value, label="L"); line = sys._getframe().f_lineno
        events = self._events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["file"], os.path.abspath(__file__))
        self.assertEqual(events[0]["line"], line)
        self.assertEqual(events[0]["name"], "value")
        self.assertEqual(events[0]["value"], "{'a': 1}")
        self.assertEqual(events[0]["label"], "L")

    def test_quiet_call_writes_no_event(self):
        core.siren(1, quiet=True)
        self.assertEqual(self._events(), [])

    def test_no_event_without_env_var(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            with mock.patch("sys.stdout", new_callable=io.StringIO):
                core.siren(1)
        self.assertEqual(self._events(), [])


class TestCleanSingleFile(unittest.TestCase):
    def test_clean_directory_accepts_a_file_path(self):
        fd, path = tempfile.mkstemp(suffix=".py")
        with os.fdopen(fd, "w") as f:
            f.write("x = 1\nsiren(x)\n")
        try:
            self.assertEqual(clean.clean_directory(path), 1)
            with io.open(path, encoding="utf-8") as f:
                self.assertEqual(f.read(), "x = 1\n")
        finally:
            os.remove(path)
