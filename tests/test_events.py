import io
import json
import os
import shutil
import sys
import tempfile
import threading
import unittest
from unittest import mock

try:
    from http.server import BaseHTTPRequestHandler, HTTPServer
except ImportError:  # Python 2
    from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer

from siren import account, events

VALID_KEY = "test-key"
_EVENTS = []


class _FakeEventsBackendHandler(BaseHTTPRequestHandler):
    def _send_json(self, status, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body)

    def _authorized(self):
        return self.headers.get("Authorization") == "Bearer {}".format(VALID_KEY)

    def do_POST(self):
        if self.path == "/events":
            if not self._authorized():
                self._send_json(401, {"detail": "Invalid API key"})
                return
            length = int(self.headers.get("Content-Length", 0))
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            payload["id"] = len(_EVENTS) + 1
            payload["created_at"] = "2026-09-18T00:00:00"
            _EVENTS.append(payload)
            self._send_json(200, {"id": payload["id"]})
            return
        self._send_json(404, {"detail": "not found"})

    def do_GET(self):
        if not self._authorized():
            self._send_json(401, {"detail": "Invalid API key"})
            return

        if self.path == "/events":
            summaries = [
                {
                    "id": e["id"], "exc_type": e["exc_type"], "message": e["message"],
                    "label": e.get("label"), "created_at": e["created_at"],
                }
                for e in _EVENTS
            ]
            self._send_json(200, summaries)
            return

        if self.path.startswith("/events/"):
            event_id = int(self.path.rsplit("/", 1)[-1])
            matches = [e for e in _EVENTS if e["id"] == event_id]
            if not matches:
                self._send_json(404, {"detail": "not found"})
                return
            self._send_json(200, matches[0])
            return

        self._send_json(404, {"detail": "not found"})

    def log_message(self, format, *args):
        pass


class TestEvents(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = HTTPServer(("127.0.0.1", 0), _FakeEventsBackendHandler)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever)
        cls.thread.daemon = True
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.thread.join()

    def setUp(self):
        del _EVENTS[:]

        self.tmpdir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmpdir, True)

        self.api_url = "http://127.0.0.1:{}".format(self.port)
        creds_path = os.path.join(self.tmpdir, "credentials.json")
        patcher = mock.patch.object(account, "_credentials_path", return_value=creds_path)
        patcher.start()
        self.addCleanup(patcher.stop)

    def _login(self):
        with io.open(account._credentials_path(), "w", encoding="utf-8") as f:
            f.write(json.dumps({"api_key": VALID_KEY, "api_url": self.api_url, "email": "me@example.com"}))

    def _capture_stdout(self, func, *args, **kwargs):
        captured = io.StringIO()
        original_stdout = sys.stdout
        sys.stdout = captured
        try:
            result = func(*args, **kwargs)
        finally:
            sys.stdout = original_stdout
        return result, captured.getvalue()

    def test_report_without_login_prints_message_and_returns_none(self):
        try:
            raise ValueError("boom")
        except ValueError:
            result, output = self._capture_stdout(events.report)
        self.assertIsNone(result)
        self.assertIn("not logged in", output)

    def test_report_with_no_active_exception_does_nothing(self):
        self._login()
        result, output = self._capture_stdout(events.report)
        self.assertIsNone(result)
        self.assertIn("no active exception", output)

    def test_report_sends_exception_from_sys_exc_info(self):
        self._login()
        try:
            raise ZeroDivisionError("division by zero")
        except ZeroDivisionError:
            event_id, output = self._capture_stdout(events.report, label="checkout")

        self.assertEqual(event_id, 1)
        self.assertIn("reported ZeroDivisionError", output)
        self.assertEqual(_EVENTS[0]["exc_type"], "ZeroDivisionError")
        self.assertEqual(_EVENTS[0]["message"], "division by zero")
        self.assertEqual(_EVENTS[0]["label"], "checkout")
        self.assertTrue(_EVENTS[0]["context_file"].endswith("test_events.py"))

    def test_report_accepts_explicit_exception_instance(self):
        self._login()
        try:
            raise KeyError("missing")
        except KeyError as e:
            exc = e

        event_id, _ = self._capture_stdout(events.report, exc)
        self.assertEqual(event_id, 1)
        self.assertEqual(_EVENTS[0]["exc_type"], "KeyError")

    def test_cli_list_shows_reported_events(self):
        self._login()
        try:
            raise RuntimeError("oops")
        except RuntimeError:
            events.report()

        sys.argv = ["siren-events", "list"]
        _, output = self._capture_stdout(events.main)
        self.assertIn("RuntimeError", output)
        self.assertIn("oops", output)

    def test_cli_list_without_login_exits_nonzero(self):
        sys.argv = ["siren-events", "list"]
        with self.assertRaises(SystemExit) as ctx:
            self._capture_stdout(events.main)
        self.assertNotEqual(ctx.exception.code, 0)

    def test_cli_show_prints_full_traceback(self):
        self._login()
        try:
            raise ValueError("detailed error")
        except ValueError:
            events.report()

        sys.argv = ["siren-events", "show", "1"]
        _, output = self._capture_stdout(events.main)
        self.assertIn("ValueError", output)
        self.assertIn("detailed error", output)
        self.assertIn("Traceback", output)

    def test_cli_show_missing_event_exits_nonzero(self):
        self._login()
        sys.argv = ["siren-events", "show", "999"]
        with self.assertRaises(SystemExit) as ctx:
            self._capture_stdout(events.main)
        self.assertNotEqual(ctx.exception.code, 0)


if __name__ == "__main__":
    unittest.main()
