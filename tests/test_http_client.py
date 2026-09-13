import json
import shutil
import tempfile
import threading
import unittest
from unittest import mock

try:
    from http.server import BaseHTTPRequestHandler, HTTPServer
except ImportError:  # Python 2
    from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer

from siren import http_client


class _EchoHandler(BaseHTTPRequestHandler):
    def _handle(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode("utf-8") if length else ""
        payload = {
            "method": self.command,
            "path": self.path,
            "headers": dict(self.headers.items()),
            "body": body,
        }
        response = json.dumps(payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(response)

    def do_GET(self):
        self._handle()

    def do_POST(self):
        self._handle()

    def do_PUT(self):
        self._handle()

    def do_PATCH(self):
        self._handle()

    def do_DELETE(self):
        self._handle()

    def log_message(self, format, *args):
        pass


class TestHttpClient(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = HTTPServer(("127.0.0.1", 0), _EchoHandler)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever)
        cls.thread.daemon = True
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.thread.join()

    def _url(self, path="/"):
        return "http://127.0.0.1:{}{}".format(self.port, path)

    def test_get_request(self):
        result = http_client.send("GET", self._url("/items"))
        self.assertEqual(result["status"], 200)
        payload = json.loads(result["body"])
        self.assertEqual(payload["method"], "GET")
        self.assertEqual(payload["path"], "/items")

    def test_post_with_json_body(self):
        result = http_client.send("POST", self._url("/items"), json_body={"name": "x"})
        payload = json.loads(result["body"])
        self.assertEqual(payload["method"], "POST")
        self.assertEqual(json.loads(payload["body"]), {"name": "x"})
        self.assertEqual(payload["headers"]["Content-Type"], "application/json")

    def test_custom_headers_sent(self):
        result = http_client.send("GET", self._url("/"), headers={"X-Test": "abc"})
        payload = json.loads(result["body"])
        self.assertEqual(payload["headers"]["X-Test"], "abc")

    def test_put_and_delete_methods(self):
        for method in ("PUT", "PATCH", "DELETE"):
            result = http_client.send(method, self._url("/"))
            payload = json.loads(result["body"])
            self.assertEqual(payload["method"], method)


class TestHttpCollections(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmpdir, True)
        patcher = mock.patch.object(http_client, "_collections_dir", return_value=self.tmpdir)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_save_and_load_collection(self):
        http_client.save_collection("my-req", "GET", "http://example.com", {"X-A": "1"}, None, None)
        loaded = http_client.load_collection("my-req")
        self.assertEqual(loaded["method"], "GET")
        self.assertEqual(loaded["url"], "http://example.com")
        self.assertEqual(loaded["headers"], {"X-A": "1"})

    def test_load_missing_collection_returns_none(self):
        self.assertIsNone(http_client.load_collection("nope"))

    def test_list_collections(self):
        http_client.save_collection("b", "GET", "http://example.com")
        http_client.save_collection("a", "GET", "http://example.com")
        self.assertEqual(http_client.list_collections(), ["a", "b"])


if __name__ == "__main__":
    unittest.main()
