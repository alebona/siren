import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest
from unittest import mock

from siren import _bridge, account, http_client, snippets

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestBridgeProtocol(unittest.TestCase):
    def test_unknown_op(self):
        self.assertEqual(_bridge.handle({"op": "nope"}), {"ok": False, "error": "unknown op: nope"})

    def test_errors_are_returned_not_raised(self):
        response = _bridge.handle({"op": "scaffold", "args": {"template": "bogus", "name": "x", "path": "."}})
        self.assertFalse(response["ok"])
        self.assertIn("Unknown template", response["error"])

    def test_stdin_stdout_round_trip(self):
        out = subprocess.check_output(
            [sys.executable, "-m", "siren._bridge"],
            input=json.dumps({"op": "scaffold_templates"}).encode("utf-8"),
            cwd=ROOT,
        )
        self.assertEqual(
            json.loads(out.decode("ascii")),
            {"ok": True, "result": ["class", "dataclass", "package", "script", "test"]},
        )


class TestBridgeQuality(unittest.TestCase):
    def test_reports_issues_with_lines_and_kinds(self):
        tmpdir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmpdir, True)
        path = os.path.join(tmpdir, "mod.py")
        with io.open(path, "w", encoding="utf-8") as f:
            f.write(textwrap.dedent(u"""\
                import os
                def helper():
                    try:
                        pass
                    except:
                        pass  # TODO fix
            """))
        with io.open(os.path.join(tmpdir, "broken.py"), "w", encoding="utf-8") as f:
            f.write(u"def (:\n")

        result = _bridge.op_quality({"path": tmpdir, "threshold": 10})

        self.assertEqual(len(result["files"]), 1)
        kinds = sorted((i["kind"], i["line"]) for i in result["files"][0]["issues"])
        self.assertEqual(kinds, [("bare-except", 5), ("todo", 6), ("unused-def", 2), ("unused-import", 1)])
        self.assertEqual([os.path.basename(u["file"]) for u in result["unparseable"]], ["broken.py"])

    def test_complexity_above_threshold_only(self):
        tmpdir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmpdir, True)
        path = os.path.join(tmpdir, "c.py")
        with io.open(path, "w", encoding="utf-8") as f:
            f.write(u"def _f(a):\n    if a:\n        return 1\n    if not a:\n        return 2\n")
        issues = _bridge.op_quality({"path": path, "threshold": 2})["files"][0]["issues"]
        self.assertEqual([(i["kind"], i["score"]) for i in issues], [("complexity", 3)])
        issues = _bridge.op_quality({"path": path, "threshold": 3})["files"][0]["issues"]
        self.assertEqual(issues, [])


class TestBridgeSnippets(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmpdir, True)
        patcher = mock.patch.object(snippets, "_snippets_dir", return_value=self.tmpdir)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_save_list_tag_rename_remove(self):
        _bridge.op_snippets_save({"name": "q", "content": "SELECT 1", "tags": ["sql"]})
        listed = _bridge.op_snippets_list({})
        self.assertEqual([(s["name"], s["tags"], s["content"]) for s in listed], [("q", ["sql"], "SELECT 1")])

        _bridge.op_snippets_set_tags({"name": "q", "tags": ["sql", "db"]})
        self.assertEqual(_bridge.op_snippets_list({})[0]["tags"], ["sql", "db"])

        _bridge.op_snippets_rename({"old": "q", "new": "query"})
        self.assertEqual([s["name"] for s in _bridge.op_snippets_list({})], ["query"])

        self.assertTrue(_bridge.op_snippets_remove({"name": "query"}))
        self.assertEqual(_bridge.op_snippets_list({}), [])


class TestBridgeHttp(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmpdir, True)
        patcher = mock.patch.object(http_client, "_collections_dir", return_value=self.tmpdir)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_save_list_load_remove(self):
        _bridge.op_http_save({"name": "items", "method": "POST", "url": "https://x.io/items", "json": {"a": 1}})
        listed = _bridge.op_http_list({})
        self.assertEqual([(r["name"], r["method"], r["url"]) for r in listed], [("items", "POST", "https://x.io/items")])
        self.assertEqual(_bridge.op_http_load({"name": "items"})["json"], {"a": 1})
        self.assertTrue(_bridge.op_http_remove({"name": "items"}))
        self.assertEqual(_bridge.op_http_list({}), [])


class TestBridgeAccount(unittest.TestCase):
    def test_status_when_logged_out(self):
        with mock.patch.object(account, "load_credentials", return_value=None):
            self.assertEqual(_bridge.op_account_status({}), {"logged_in": False})

    def test_pro_get_requires_login(self):
        with mock.patch.object(account, "load_credentials", return_value=None):
            response = _bridge.handle({"op": "events_list"})
        self.assertEqual(response, {"ok": False, "error": "not logged in"})

    def test_perf_list_quotes_name(self):
        creds = {"api_url": "https://api", "api_key": "k"}
        with mock.patch.object(account, "load_credentials", return_value=creds), \
                mock.patch.object(account, "_send", return_value={"status": 200, "body": "[]"}) as send:
            _bridge.op_perf_list({"name": "a b&c", "limit": 5})
        self.assertEqual(send.call_args[0][2], "https://api/metrics/list?limit=5&name=a%20b%26c")
