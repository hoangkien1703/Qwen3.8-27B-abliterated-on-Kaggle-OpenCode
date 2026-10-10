"""Tests for the password proxy in kaggle/serve_model.py, using a fake model server."""

import http.client
import http.server
import importlib.util
import json
import os
import threading
import time
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location("serve_model", os.path.join(ROOT, "kaggle", "serve_model.py"))
job = importlib.util.module_from_spec(spec)
spec.loader.exec_module(job)


class FakeModel(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    seen_auth = []

    def do_GET(self):
        data = json.dumps({"object": "list", "data": [{"id": "m"}]}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        FakeModel.seen_auth.append(self.headers.get("Authorization"))
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Transfer-Encoding", "chunked")
        self.end_headers()
        for i in range(3):
            event = f"data: {json.dumps({'i': i, 'echo': body['msg']})}\n\n".encode()
            self.wfile.write(b"%x\r\n%s\r\n" % (len(event), event))
            self.wfile.flush()
            time.sleep(0.3)
        self.wfile.write(b"0\r\n\r\n")

    def log_message(self, *args):
        pass


class ProxyTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        job.API_KEY = "secret123"
        job.log = lambda *a: None
        fake = http.server.ThreadingHTTPServer(("127.0.0.1", 0), FakeModel)
        threading.Thread(target=fake.serve_forever, daemon=True).start()
        job.AuthProxy.upstream = ("127.0.0.1", fake.server_address[1])
        cls.proxy = job.start_proxy(0)
        cls.port = cls.proxy.server_address[1]

    def request(self, method, path, key=None, body=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        headers = {"Content-Type": "application/json"}
        if key:
            headers["Authorization"] = f"Bearer {key}"
        conn.request(method, path, body=json.dumps(body) if body is not None else None, headers=headers)
        return conn.getresponse()

    def test_rejects_missing_or_wrong_password(self):
        self.assertEqual(self.request("GET", "/v1/models").status, 401)
        self.assertEqual(self.request("GET", "/v1/models", "wrong").status, 401)

    def test_accepts_password(self):
        r = self.request("GET", "/v1/models", "secret123")
        self.assertEqual(r.status, 200)
        self.assertEqual(json.loads(r.read())["data"][0]["id"], "m")

    def test_streams_incrementally_and_hides_password(self):
        r = self.request("POST", "/v1/chat/completions", "secret123", {"msg": "hi"})
        start, times = time.time(), []
        while True:
            chunk = r.read1(1000)
            if not chunk:
                break
            times.append(time.time() - start)
        self.assertEqual(len(times), 3)
        self.assertGreater(times[-1] - times[0], 0.4)  # chunks arrived as they were produced
        self.assertIsNone(FakeModel.seen_auth[-1])  # password is not forwarded to the model

    def test_stop_endpoint(self):
        r = self.request("POST", "/__stop", "secret123", {})
        self.assertEqual(r.status, 200)
        self.assertTrue(job.state["stop"])
        job.state["stop"] = False


if __name__ == "__main__":
    unittest.main()
