import json
import os
import shutil
import tempfile
import threading
import unittest
from unittest import mock

try:
    from http.server import BaseHTTPRequestHandler, HTTPServer
except ImportError:  # Python 2
    from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer

from siren import account

# email -> api_key, api_key -> {"plan", "active", "workspace_id"}
_USERS = {}
_KEYS = {}


class _FakeBackendHandler(BaseHTTPRequestHandler):
    def _send_json(self, status, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body)

    def _auth_key(self):
        header = self.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            return None
        return header[len("Bearer "):]

    def do_POST(self):
        if self.path == "/auth/signup":
            length = int(self.headers.get("Content-Length", 0))
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            email = payload["email"]

            if email in _USERS:
                self._send_json(409, {"detail": "Email already has an account."})
                return

            api_key = "key-{}".format(len(_KEYS) + 1)
            workspace_id = len(_KEYS) + 1
            _USERS[email] = api_key
            _KEYS[api_key] = {"plan": "trial", "active": True, "workspace_id": workspace_id}
            self._send_json(200, {"api_key": api_key, "workspace_id": workspace_id})
            return

        self._send_json(404, {"detail": "not found"})

    def do_GET(self):
        if self.path == "/licenses/validate":
            api_key = self._auth_key()
            if api_key not in _KEYS:
                self._send_json(401, {"detail": "Invalid API key"})
                return
            self._send_json(200, _KEYS[api_key])
            return

        self._send_json(404, {"detail": "not found"})

    def log_message(self, format, *args):
        pass


class TestAccount(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = HTTPServer(("127.0.0.1", 0), _FakeBackendHandler)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever)
        cls.thread.daemon = True
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.thread.join()

    def setUp(self):
        _USERS.clear()
        _KEYS.clear()

        self.tmpdir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmpdir, True)

        creds_path = os.path.join(self.tmpdir, "credentials.json")
        patcher1 = mock.patch.object(account, "_credentials_path", return_value=creds_path)
        patcher1.start()
        self.addCleanup(patcher1.stop)

        api_url = "http://127.0.0.1:{}".format(self.port)
        patcher2 = mock.patch.object(account, "_api_url", return_value=api_url)
        patcher2.start()
        self.addCleanup(patcher2.stop)

    def test_signup_saves_credentials(self):
        body = account.signup("me@example.com")
        self.assertIn("api_key", body)

        creds = account.load_credentials()
        self.assertEqual(creds["api_key"], body["api_key"])
        self.assertEqual(creds["email"], "me@example.com")

    def test_signup_twice_raises(self):
        account.signup("dup@example.com")
        with self.assertRaises(RuntimeError):
            account.signup("dup@example.com")

    def test_use_key_saves_valid_key(self):
        body = account.signup("me@example.com")
        account.clear_credentials()

        status = account.use_key(body["api_key"])
        self.assertTrue(status["active"])
        creds = account.load_credentials()
        self.assertEqual(creds["api_key"], body["api_key"])

    def test_use_key_rejects_invalid_key(self):
        with self.assertRaises(RuntimeError):
            account.use_key("not-a-real-key")
        self.assertIsNone(account.load_credentials())

    def test_validate_returns_none_when_not_logged_in(self):
        self.assertIsNone(account.validate())

    def test_validate_returns_status_when_logged_in(self):
        account.signup("me@example.com")
        status = account.validate()
        self.assertEqual(status["plan"], "trial")
        self.assertTrue(status["active"])

    def test_clear_credentials(self):
        account.signup("me@example.com")
        self.assertTrue(account.clear_credentials())
        self.assertIsNone(account.load_credentials())

    def test_clear_credentials_when_not_logged_in_returns_false(self):
        self.assertFalse(account.clear_credentials())


if __name__ == "__main__":
    unittest.main()
