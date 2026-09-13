import io
import sys
import threading
import unittest

try:
    from http.server import BaseHTTPRequestHandler, HTTPServer
except ImportError:  # Python 2
    from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer

from siren import http_patch

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False


class _OkHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(204)
        self.end_headers()

    def log_message(self, format, *args):
        pass


class _LocalServerMixin(object):
    @classmethod
    def setUpClass(cls):
        cls.server = HTTPServer(("127.0.0.1", 0), _OkHandler)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever)
        cls.thread.daemon = True
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.thread.join()

    def _url(self):
        return "http://127.0.0.1:{}/ping".format(self.port)

    def _capture_stdout(self, func):
        captured = io.StringIO()
        original_stdout = sys.stdout
        sys.stdout = captured
        try:
            func()
        finally:
            sys.stdout = original_stdout
        return captured.getvalue()


@unittest.skipUnless(HAS_REQUESTS, "requests is not installed")
class TestPatchRequests(_LocalServerMixin, unittest.TestCase):
    def tearDown(self):
        http_patch.unpatch_requests()

    def test_logs_method_url_and_status(self):
        http_patch.patch_requests()
        output = self._capture_stdout(lambda: requests.get(self._url()))
        self.assertIn("get", output.lower())
        self.assertIn(self._url(), output)
        self.assertIn("204", output)

    def test_unpatch_restores_original_method(self):
        original = requests.Session.request
        http_patch.patch_requests()
        self.assertIsNot(requests.Session.request, original)
        http_patch.unpatch_requests()
        self.assertIs(requests.Session.request, original)

    def test_patch_is_idempotent(self):
        http_patch.patch_requests()
        patched_once = requests.Session.request
        http_patch.patch_requests()
        self.assertIs(requests.Session.request, patched_once)


@unittest.skipUnless(HAS_HTTPX, "httpx is not installed")
class TestPatchHttpx(_LocalServerMixin, unittest.TestCase):
    def tearDown(self):
        http_patch.unpatch_httpx()

    def test_logs_method_url_and_status(self):
        http_patch.patch_httpx()
        output = self._capture_stdout(lambda: httpx.Client().get(self._url()))
        self.assertIn("GET", output)
        self.assertIn(self._url(), output)
        self.assertIn("204", output)

    def test_unpatch_restores_original_method(self):
        original = httpx.Client.request
        http_patch.patch_httpx()
        self.assertIsNot(httpx.Client.request, original)
        http_patch.unpatch_httpx()
        self.assertIs(httpx.Client.request, original)


if __name__ == "__main__":
    unittest.main()
