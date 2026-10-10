# Kaggle job: serve an uncensored coding model on Kaggle's free "GPU T4 x2"
# and expose it as a password-protected OpenAI-compatible API through ngrok.
#
# Normally pushed by kaggle_run.py, which fills in API_KEY (a fresh random
# password) and NGROK_AUTHTOKEN (a temporary ngrok authtoken) before upload.
# To run it by hand in a Kaggle notebook instead, paste both values below and
# turn on Settings > Accelerator "GPU T4 x2" and Settings > Internet.
#
# Steps: install Ollama -> pull MODEL -> measure speed -> start a password proxy
# on :8000 in front of Ollama -> open an ngrok tunnel -> print
# "READY base_url=..." -> serve until MAX_HOURS, IDLE_MINUTES without
# requests, or POST /__stop with the password.

import hmac
import http.client
import http.server
import json
import os
import shutil
import subprocess
import sys
import threading
import time
import urllib.request

API_KEY = "__API_KEY__"
NGROK_AUTHTOKEN = "__NGROK_AUTHTOKEN__"
MODEL = os.environ.get("MODEL", "huihui_ai/Qwen3.8-abliterated:27b")
CONTEXT = int(os.environ.get("CONTEXT", "65536"))
MAX_HOURS = float(os.environ.get("MAX_HOURS", "2"))
IDLE_MINUTES = float(os.environ.get("IDLE_MINUTES", "30"))

OLLAMA = ("127.0.0.1", 11434)
PROXY_PORT = 8000
MODELS_DIR = "/tmp/ollama-models"

state = {"last_request": time.time(), "requests": 0, "stop": False}


def log(*args):
    print(time.strftime("%H:%M:%S"), *args, flush=True)


def sh(cmd):
    log("$", cmd)
    subprocess.run(cmd, shell=True, check=True)


def wait_http(url, seconds):
    deadline = time.time() + seconds
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=5) as r:
                return r.read()
        except Exception:
            time.sleep(2)
    raise RuntimeError(f"timed out waiting for {url}")


def ollama_json(path, payload, timeout=600):
    conn = http.client.HTTPConnection(*OLLAMA, timeout=timeout)
    conn.request("POST", path, body=json.dumps(payload), headers={"Content-Type": "application/json"})
    return conn.getresponse()


# ---------------------------------------------------------------- auth proxy

HOP_HEADERS = {
    "connection", "keep-alive", "proxy-authenticate", "proxy-authorization", "te",
    "trailers", "transfer-encoding", "upgrade", "host", "content-length", "authorization",
}


class AuthProxy(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    upstream = OLLAMA

    def _reply(self, status, body):
        data = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _read_body(self):
        if "chunked" in self.headers.get("Transfer-Encoding", "").lower():
            parts = []
            while True:
                size = int(self.rfile.readline().split(b";")[0].strip() or b"0", 16)
                if size == 0:
                    self.rfile.readline()
                    break
                parts.append(self.rfile.read(size))
                self.rfile.readline()
            return b"".join(parts)
        length = int(self.headers.get("Content-Length") or 0)
        return self.rfile.read(length) if length else None

    def _handle(self):
        body = self._read_body()
        if self.path == "/health":
            return self._reply(200, {"ok": True})
        expected = f"Bearer {API_KEY}".encode()
        if not hmac.compare_digest(self.headers.get("Authorization", "").encode(), expected):
            return self._reply(401, {"error": {"message": "Invalid API key", "type": "authentication_error"}})
        state["last_request"] = time.time()
        state["requests"] += 1
        if self.path == "/__stop":
            state["stop"] = True
            return self._reply(200, {"stopping": True})

        headers = {k: v for k, v in self.headers.items() if k.lower() not in HOP_HEADERS}
        upstream = http.client.HTTPConnection(*self.upstream, timeout=3600)
        try:
            upstream.request(self.command, self.path, body=body, headers=headers)
            resp = upstream.getresponse()
            self.send_response(resp.status)
            for k, v in resp.getheaders():
                if k.lower() not in HOP_HEADERS:
                    self.send_header(k, v)
            self.send_header("Transfer-Encoding", "chunked")
            self.end_headers()
            while True:
                chunk = resp.read1(65536)
                if not chunk:
                    break
                self.wfile.write(b"%x\r\n%s\r\n" % (len(chunk), chunk))
                self.wfile.flush()
                state["last_request"] = time.time()
            self.wfile.write(b"0\r\n\r\n")
            self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass  # client went away; closing upstream cancels generation
        finally:
            upstream.close()

    do_GET = do_POST = do_PUT = do_DELETE = _handle

    def log_message(self, fmt, *args):
        log("proxy:", self.command, self.path.split("?")[0], args[1] if len(args) > 1 else "")


def start_proxy(port=PROXY_PORT):
    server = http.server.ThreadingHTTPServer(("127.0.0.1", port), AuthProxy)
    server.daemon_threads = True
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


# ---------------------------------------------------------------- main steps

def main():
    if API_KEY.startswith("__") or NGROK_AUTHTOKEN.startswith("__"):
        sys.exit("Set API_KEY and NGROK_AUTHTOKEN at the top of this file first.")
    started = time.time()

    log("== GPUs and disk")
    sh("nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv")
    sh("df -h / /tmp /kaggle/working 2>/dev/null || true")

    log("== Installing Ollama")
    if not shutil.which("zstd"):
        sh("apt-get -qq update >/dev/null && apt-get -qq install -y zstd >/dev/null")
    sh("curl -fsSL https://ollama.com/install.sh | sh 2>&1 | tail -n 5")

    log("== Starting Ollama")
    os.makedirs(MODELS_DIR, exist_ok=True)
    env = dict(
        os.environ,
        OLLAMA_HOST=f"{OLLAMA[0]}:{OLLAMA[1]}",
        OLLAMA_MODELS=MODELS_DIR,
        OLLAMA_CONTEXT_LENGTH=str(CONTEXT),
        OLLAMA_FLASH_ATTENTION="1",
        OLLAMA_KV_CACHE_TYPE="q8_0",
        OLLAMA_KEEP_ALIVE="-1",
    )
    ollama_log = open("/tmp/ollama.log", "w")
    ollama = subprocess.Popen(["ollama", "serve"], env=env, stdout=ollama_log, stderr=subprocess.STDOUT)
    log("Ollama version:", wait_http(f"http://{OLLAMA[0]}:{OLLAMA[1]}/api/version", 120).decode())

    log(f"== Downloading {MODEL}")
    t0 = time.time()
    resp = ollama_json("/api/pull", {"model": MODEL, "stream": True}, timeout=3600)
    last_pct = -10
    for line in resp:
        msg = json.loads(line)
        if "error" in msg:
            raise RuntimeError(msg["error"])
        total, done = msg.get("total"), msg.get("completed")
        if total and done:
            pct = int(done * 100 / total)
            if pct >= last_pct + 10:
                last_pct = pct
                log(f"  {msg.get('status', '')[:30]} {pct}% of {total / 1e9:.1f} GB")
        elif msg.get("status") and not total:
            log(" ", msg["status"])
    log(f"Download finished in {time.time() - t0:.0f}s")

    log("== Loading the model and measuring speed")
    t0 = time.time()
    resp = ollama_json("/api/generate", {
        "model": MODEL,
        "prompt": "Write a Python function that returns the n-th Fibonacci number, with a docstring.",
        "think": False,
        "stream": False,
        "options": {"num_predict": 256},
    }, timeout=1800)
    result = json.loads(resp.read())
    if "error" in result:
        raise RuntimeError(result["error"])
    log(f"Load + first answer took {time.time() - t0:.0f}s")
    log(f"Prompt speed: {result['prompt_eval_count'] / (result['prompt_eval_duration'] / 1e9):.1f} tokens/s")
    log(f"Output speed: {result['eval_count'] / (result['eval_duration'] / 1e9):.1f} tokens/s")
    sh("ollama ps")
    sh("nvidia-smi --query-gpu=index,memory.used,memory.total --format=csv")

    log("== Starting password proxy and ngrok tunnel")
    start_proxy()
    if not shutil.which("ngrok"):
        sh("curl -fsSL https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-amd64.tgz | tar -xz -C /usr/local/bin")
    log("$ ngrok config add-authtoken ***")
    subprocess.run(["ngrok", "config", "add-authtoken", NGROK_AUTHTOKEN], check=True, stdout=subprocess.DEVNULL)
    ngrok_log = open("/tmp/ngrok.log", "w")
    ngrok = subprocess.Popen(
        ["ngrok", "http", str(PROXY_PORT), "--log", "stdout", "--log-format", "json"],
        stdout=ngrok_log, stderr=subprocess.STDOUT,
    )
    tunnels = json.loads(wait_http("http://127.0.0.1:4040/api/tunnels", 60))
    for _ in range(30):
        if tunnels.get("tunnels"):
            break
        time.sleep(1)
        tunnels = json.loads(wait_http("http://127.0.0.1:4040/api/tunnels", 10))
    url = tunnels["tunnels"][0]["public_url"]
    log(f"READY base_url={url}/v1 model={MODEL} context={CONTEXT}")

    state["last_request"] = time.time()
    next_beat = time.time()
    while True:
        now = time.time()
        if state["stop"]:
            log("Stop requested through the API.")
            break
        if now - started > MAX_HOURS * 3600:
            log(f"Reached the {MAX_HOURS}-hour limit.")
            break
        if now - state["last_request"] > IDLE_MINUTES * 60:
            log(f"No requests for {IDLE_MINUTES:.0f} minutes.")
            break
        if ollama.poll() is not None or ngrok.poll() is not None:
            log("Ollama or ngrok exited unexpectedly; see logs below.")
            break
        if now >= next_beat:
            log(f"alive: {state['requests']} requests so far, {(now - started) / 60:.0f} min since start")
            next_beat = now + 300
        time.sleep(5)

    log("== Shutting down")
    for p in (ngrok, ollama):
        p.terminate()
    os.system("tail -n 20 /tmp/ollama.log")
    log(f"Total run time {(time.time() - started) / 60:.0f} min")


if __name__ == "__main__":
    main()
