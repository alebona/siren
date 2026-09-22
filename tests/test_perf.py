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
    from urllib.parse import urlparse, parse_qs
except ImportError:  # Python 2
    from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
    from urlparse import urlparse, parse_qs

from siren import account, perf

VALID_KEY = "test-key"
_SAMPLES = []


class _FakePerfBackendHandler(BaseHTTPRequestHandler):
    def _send_json(self, status, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body)

    def _authorized(self):
        return self.headers.get("Authorization") == "Bearer {}".format(VALID_KEY)

    def do_POST(self):
        if self.path == "/metrics/batch":
            if not self._authorized():
                self._send_json(401, {"detail": "Invalid API key"})
                return
            length = int(self.headers.get("Content-Length", 0))
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            for sample in payload["samples"]:
                sample["created_at"] = "2026-09-21T00:00:00"
                _SAMPLES.append(sample)
            self._send_json(200, {"count": len(payload["samples"])})
            return
        self._send_json(404, {"detail": "not found"})

    def do_GET(self):
        if not self._authorized():
            self._send_json(401, {"detail": "Invalid API key"})
            return

        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)

        if parsed.path == "/metrics/list":
            name = query.get("name", [None])[0]
            samples = [s for s in reversed(_SAMPLES) if name is None or s["name"] == name]
            self._send_json(200, samples)
            return

        if parsed.path == "/metrics/top":
            by_name = {}
            for s in _SAMPLES:
                row = by_name.setdefault(s["name"], {"name": s["name"], "calls": 0, "total_ms": 0.0, "max_ms": 0.0, "errors": 0})
                row["calls"] += 1
                row["total_ms"] += s["duration_ms"]
                row["max_ms"] = max(row["max_ms"], s["duration_ms"])
                if not s["ok"]:
                    row["errors"] += 1
            rows = []
            for row in by_name.values():
                rows.append({
                    "name": row["name"],
                    "calls": row["calls"],
                    "avg_ms": row["total_ms"] / row["calls"],
                    "p95_ms": row["max_ms"],
                    "total_ms": row["total_ms"],
                    "errors": row["errors"],
                })
            rows.sort(key=lambda r: r["total_ms"], reverse=True)
            self._send_json(200, rows)
            return

        self._send_json(404, {"detail": "not found"})

    def log_message(self, format, *args):
        pass


class TestPerf(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = HTTPServer(("127.0.0.1", 0), _FakePerfBackendHandler)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever)
        cls.thread.daemon = True
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.thread.join()

    def setUp(self):
        del _SAMPLES[:]
        del perf._buffer[:]
        perf._warned_not_logged_in = False
        perf._warned_buffer_full = False

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

    def test_profile_records_and_flushes_on_perf_flush(self):
        self._login()

        @perf.profile(label="checkout")
        def fast():
            return 42

        self.assertEqual(fast(), 42)
        _, output = self._capture_stdout(perf.perf_flush)

        self.assertEqual(len(_SAMPLES), 1)
        self.assertEqual(_SAMPLES[0]["name"], "fast")
        self.assertEqual(_SAMPLES[0]["label"], "checkout")
        self.assertTrue(_SAMPLES[0]["ok"])
        self.assertGreaterEqual(_SAMPLES[0]["duration_ms"], 0)

    def test_min_duration_filters_out_fast_calls(self):
        self._login()

        @perf.profile(min_duration_ms=10000)
        def fast():
            return 1

        fast()
        perf.perf_flush()
        self.assertEqual(len(_SAMPLES), 0)

    def test_sample_rate_zero_records_nothing(self):
        self._login()

        @perf.profile(sample_rate=0.0)
        def fast():
            return 1

        for _ in range(5):
            fast()
        perf.perf_flush()
        self.assertEqual(len(_SAMPLES), 0)

    def test_exception_is_reraised_and_recorded_as_not_ok(self):
        self._login()

        @perf.profile
        def boom():
            raise ValueError("nope")

        with self.assertRaises(ValueError):
            boom()
        perf.perf_flush()

        self.assertEqual(len(_SAMPLES), 1)
        self.assertFalse(_SAMPLES[0]["ok"])

    def test_profile_block_times_a_block_of_code(self):
        self._login()

        with perf.profile_block("db-query", label="orders"):
            pass
        perf.perf_flush()

        self.assertEqual(len(_SAMPLES), 1)
        self.assertEqual(_SAMPLES[0]["name"], "db-query")
        self.assertEqual(_SAMPLES[0]["label"], "orders")
        self.assertTrue(_SAMPLES[0]["ok"])

    def test_not_logged_in_never_raises_and_warns_once(self):
        @perf.profile
        def fast():
            return 1

        fast()
        fast()
        _, output = self._capture_stdout(perf.perf_flush)
        _, output2 = self._capture_stdout(perf.perf_flush)

        self.assertEqual(output.count("not logged in"), 1)
        self.assertEqual(output2.count("not logged in"), 0)
        self.assertEqual(len(_SAMPLES), 0)

    def test_cli_top_lists_ranked_output(self):
        self._login()

        @perf.profile
        def fast():
            return 1

        fast()
        fast()
        perf.perf_flush()

        sys.argv = ["siren-perf", "top"]
        _, output = self._capture_stdout(perf.main)
        self.assertIn("fast", output)
        self.assertIn("2 calls", output)

    def test_cli_list_shows_recent_samples(self):
        self._login()

        @perf.profile(label="checkout")
        def fast():
            return 1

        fast()
        perf.perf_flush()

        sys.argv = ["siren-perf", "list"]
        _, output = self._capture_stdout(perf.main)
        self.assertIn("fast", output)
        self.assertIn("checkout", output)

    def test_cli_list_without_login_exits_nonzero(self):
        sys.argv = ["siren-perf", "list"]
        with self.assertRaises(SystemExit) as ctx:
            self._capture_stdout(perf.main)
        self.assertNotEqual(ctx.exception.code, 0)


if __name__ == "__main__":
    unittest.main()
