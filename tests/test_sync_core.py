"""Testy idempotence sync_core proti lokálnímu mock HTTP serveru (bez přístupu na internet)."""
import hashlib
import http.server
import os
import sys
import tempfile
import threading
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts", "sync"))
import sync_core  # noqa: E402

STATE = {"body": b"verze-1", "etag": '"v1"', "fail": 0, "send_etag": True}


class H(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        if STATE["fail"] > 0:
            STATE["fail"] -= 1
            self.send_response(429 if STATE.get("code") == 429 else 503)
            self.send_header("Retry-After", "0")
            self.end_headers()
            return
        if STATE["send_etag"] and self.headers.get("If-None-Match") == STATE["etag"]:
            self.send_response(304)
            self.end_headers()
            return
        self.send_response(200)
        if STATE["send_etag"]:
            self.send_header("ETag", STATE["etag"])
        self.send_header("Content-Length", str(len(STATE["body"])))
        self.end_headers()
        self.wfile.write(STATE["body"])


class T(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = http.server.HTTPServer(("127.0.0.1", 0), H)
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.url = f"http://127.0.0.1:{cls.srv.server_port}/FINM.zip"

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def setUp(self):
        STATE.update(body=b"verze-1", etag='"v1"', fail=0, send_etag=True, code=503)
        self.tmp = tempfile.mkdtemp()
        self.con = sync_core.open_ledger(os.path.join(self.tmp, "ledger.db"))

    def run_fetch(self):
        return sync_core.fetch(self.con, "test.src", self.url, os.path.join(self.tmp, "raw"),
                               sleep=lambda s: None)

    def test_first_download_then_304(self):
        r1 = self.run_fetch()
        self.assertEqual(r1.status, "downloaded")
        self.assertEqual(r1.sha256, hashlib.sha256(b"verze-1").hexdigest())
        r2 = self.run_fetch()
        self.assertEqual(r2.status, "not_modified")
        self.assertEqual(r2.local_path, r1.local_path)
        self.assertEqual(len(os.listdir(os.path.join(self.tmp, "raw"))), 1)

    def test_new_version_downloaded(self):
        self.run_fetch()
        STATE.update(body=b"verze-2", etag='"v2"')
        r = self.run_fetch()
        self.assertEqual(r.status, "downloaded")
        self.assertEqual(len(os.listdir(os.path.join(self.tmp, "raw"))), 2)

    def test_no_etag_hash_dedup(self):
        STATE["send_etag"] = False
        self.run_fetch()
        r = self.run_fetch()
        self.assertEqual(r.status, "unchanged_hash")
        self.assertEqual(len(os.listdir(os.path.join(self.tmp, "raw"))), 1)

    def test_retry_on_503_and_429(self):
        STATE.update(fail=2, code=503)
        r = self.run_fetch()
        self.assertEqual((r.status, r.attempts), ("downloaded", 3))
        STATE.update(fail=10, code=429, etag='"v9"')
        r = self.run_fetch()
        self.assertEqual((r.status, r.attempts), ("error", 5))
        n = self.con.execute("SELECT COUNT(*) FROM sync_ledger WHERE status='error'").fetchone()[0]
        self.assertEqual(n, 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
