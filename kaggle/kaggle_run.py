"""Start, watch and stop the Kaggle model server job (kaggle/serve_model.py).

Auth:
  * Kaggle: set KAGGLE_API_TOKEN (Kaggle > Settings > API > Generate New Token),
    or run where a network proxy adds the token for *.kaggle.com (Claude cloud
    environment "network secret").
  * ngrok: set NGROK_API_KEY (dashboard.ngrok.com > API Keys), or let a proxy
    add it for api.ngrok.com. This is the API key, not the agent authtoken:
    each run creates its own temporary authtoken and deletes it afterwards.

Usage:
  python kaggle/kaggle_run.py quota
  python kaggle/kaggle_run.py push OWNER [--model TAG] [--hours 2] [--idle 30]
  python kaggle/kaggle_run.py status OWNER
  python kaggle/kaggle_run.py logs OWNER [--out run.log]     # follows until the job ends
  python kaggle/kaggle_run.py info                            # base URL + password for OpenCode
  python kaggle/kaggle_run.py stop                            # ask the server to shut down
  python kaggle/kaggle_run.py cleanup                         # delete the temporary ngrok authtoken
"""

import argparse
import json
import os
import re
import secrets
import sys
import time

import requests
from kagglesdk import KaggleClient
from kagglesdk.kernels.types.kernels_api_service import (
    ApiGetAcceleratorQuotaStatisticsRequest,
    ApiGetKernelSessionStatusRequest,
    ApiSaveKernelRequest,
)

HERE = os.path.dirname(os.path.abspath(__file__))
JOB_FILE = os.path.join(HERE, "serve_model.py")
STATE = os.path.join(HERE, "state.json")  # holds the run's password; gitignored
DEFAULT_LOG = os.path.join(HERE, "run.log")
SLUG = "qwen-coder-server"
NGROK_API = "https://api.ngrok.com"


def ngrok_headers():
    headers = {"Ngrok-Version": "2", "Content-Type": "application/json"}
    if os.environ.get("NGROK_API_KEY"):
        headers["Authorization"] = f"Bearer {os.environ['NGROK_API_KEY']}"
    return headers


def call(fn, req, tries=8):
    """Call a Kaggle API method, waiting out 429 rate limits (Retry-After is ~5s)."""
    for attempt in range(tries):
        with KaggleClient(verbose=False) as k:
            try:
                return fn(k)(req)
            except requests.HTTPError as e:
                if e.response is None or e.response.status_code != 429 or attempt == tries - 1:
                    raise
                time.sleep(int(e.response.headers.get("Retry-After", "5")) + attempt * 2)


def load_state():
    try:
        with open(STATE) as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def save_state(state):
    with open(STATE, "w") as f:
        json.dump(state, f, indent=2)
    os.chmod(STATE, 0o600)


def quota(_args):
    r = call(lambda k: k.kernels.kernels_api_client.get_accelerator_quota_statistics,
             ApiGetAcceleratorQuotaStatisticsRequest())
    gpu = r.gpu_quota
    print(f"GPU used {gpu.time_used} of {gpu.total_time_allowed}; resets {r.quota_refresh_time}")


def ngrok_create():
    r = requests.post(f"{NGROK_API}/credentials", headers=ngrok_headers(),
                      json={"description": f"kaggle {SLUG} (temporary)"}, timeout=30)
    r.raise_for_status()
    cred = r.json()
    return cred["id"], cred["token"]


def ngrok_delete(cred_id):
    r = requests.delete(f"{NGROK_API}/credentials/{cred_id}", headers=ngrok_headers(), timeout=30)
    print("ngrok temporary authtoken deleted" if r.status_code in (204, 404) else f"ngrok delete: HTTP {r.status_code}")


def push(args):
    state = load_state()
    if state.get("ngrok_cred_id"):
        ngrok_delete(state["ngrok_cred_id"])
    cred_id, ngrok_token = ngrok_create()
    api_key = "sk-" + secrets.token_urlsafe(24)

    source = open(JOB_FILE).read()
    replacements = {
        '"__API_KEY__"': json.dumps(api_key),
        '"__NGROK_AUTHTOKEN__"': json.dumps(ngrok_token),
        'os.environ.get("MODEL", "huihui_ai/Qwen3.8-abliterated:27b")': json.dumps(args.model),
        'float(os.environ.get("MAX_HOURS", "2"))': repr(float(args.hours)),
        'float(os.environ.get("IDLE_MINUTES", "30"))': repr(float(args.idle)),
    }
    for old, new in replacements.items():
        assert old in source, f"placeholder not found in serve_model.py: {old}"
        source = source.replace(old, new)

    req = ApiSaveKernelRequest()
    req.slug = f"{args.owner}/{SLUG}"
    req.new_title = SLUG
    req.text = source
    req.language = "python"
    req.kernel_type = "script"
    req.is_private = True
    req.enable_gpu = True
    req.enable_tpu = False
    req.enable_internet = True
    req.dataset_data_sources = []
    req.competition_data_sources = []
    req.kernel_data_sources = []
    req.model_data_sources = []
    req.category_ids = []
    req.session_timeout_seconds = int(args.hours * 3600) + 900
    req.machine_shape = "NvidiaTeslaT4"  # Kaggle's "GPU T4 x2"
    resp = call(lambda k: k.kernels.kernels_api_client.save_kernel, req)
    if resp.error:
        ngrok_delete(cred_id)
        sys.exit(f"push failed: {resp.error}")
    save_state({"owner": args.owner, "api_key": api_key, "ngrok_cred_id": cred_id,
                "model": args.model, "url": resp.url, "version": resp.version_number})
    print(f"pushed version {resp.version_number}: {resp.url}")
    print("Now run: kaggle_run.py logs", args.owner)


def kernel_status(owner):
    req = ApiGetKernelSessionStatusRequest()
    req.user_name = owner
    req.kernel_slug = SLUG
    r = call(lambda k: k.kernels.kernels_api_client.get_kernel_session_status, req)
    return str(r.status), r.failure_message or ""


def status(args):
    print(*kernel_status(args.owner))


def stream_logs_once(owner, outfile):
    """Write the whole log so far to outfile (the stream replays from the start)."""
    url = f"https://api.kaggle.com/v1/kernels/logs/stream/{owner}/{SLUG}"
    with requests.get(url, stream=True, headers={"Accept": "text/event-stream, */*"}, timeout=(30, 900)) as r:
        r.raise_for_status()
        sse = (r.headers.get("Content-Type") or "").lower().startswith("text/event-stream")
        with open(outfile, "w") as out:
            for line in r.iter_lines(decode_unicode=True):
                if sse:
                    if not line or not line.startswith("data:"):
                        continue
                    payload = line[5:].strip()
                    if payload == "END_OF_LOG":
                        return True
                    try:
                        payload = json.loads(payload).get("data", payload)
                    except json.JSONDecodeError:
                        pass
                    text = str(payload)
                    out.write(text if text.endswith("\n") else text + "\n")
                else:
                    out.write(line + "\n")
                out.flush()
    return not sse


def logs(args):
    print(f"Writing live logs to {args.out} (Ctrl+C to stop watching; the job keeps running)")
    while True:
        try:
            if stream_logs_once(args.owner, args.out):
                break
        except (requests.RequestException, ConnectionError) as e:
            print("log stream dropped, reconnecting:", type(e).__name__)
        state, _ = kernel_status(args.owner)
        if "RUNNING" not in state and "QUEUED" not in state:
            stream_logs_once(args.owner, args.out)
            break
        time.sleep(5)
    print("Job finished:", *kernel_status(args.owner))


def find_base_url(logfile):
    try:
        text = open(logfile).read()
    except FileNotFoundError:
        return None
    found = re.findall(r"READY base_url=(\S+)", text)
    return found[-1] if found else None


def info(args):
    state = load_state()
    base_url = find_base_url(args.log)
    print("Base URL :", base_url or f"(not ready yet; run `logs` and wait for READY in {args.log})")
    print("Password :", state.get("api_key", "(no run pushed yet)"))
    print("Model    :", state.get("model", "huihui_ai/Qwen3.8-abliterated:27b"))


def stop(args):
    state = load_state()
    base_url = find_base_url(args.log)
    if not base_url or not state.get("api_key"):
        sys.exit("No running server found (need READY line in the log and a pushed run).")
    root = base_url[: -len("/v1")] if base_url.endswith("/v1") else base_url
    r = requests.post(f"{root}/__stop", headers={"Authorization": f"Bearer {state['api_key']}"}, json={}, timeout=30)
    print("stop:", r.status_code, r.text)


def cleanup(_args):
    state = load_state()
    if state.get("ngrok_cred_id"):
        ngrok_delete(state.pop("ngrok_cred_id"))
        save_state(state)
    else:
        print("nothing to clean up")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("quota").set_defaults(fn=quota)
    sp = sub.add_parser("push")
    sp.add_argument("owner", help="your Kaggle username")
    sp.add_argument("--model", default="huihui_ai/Qwen3.8-abliterated:27b", help="Ollama model tag")
    sp.add_argument("--hours", type=float, default=2, help="hard time limit for the server")
    sp.add_argument("--idle", type=float, default=30, help="stop after this many minutes without requests")
    sp.set_defaults(fn=push)
    sp = sub.add_parser("status")
    sp.add_argument("owner")
    sp.set_defaults(fn=status)
    sp = sub.add_parser("logs")
    sp.add_argument("owner")
    sp.add_argument("--out", default=DEFAULT_LOG)
    sp.set_defaults(fn=logs)
    for name, fn in (("info", info), ("stop", stop)):
        sp = sub.add_parser(name)
        sp.add_argument("--log", default=DEFAULT_LOG)
        sp.set_defaults(fn=fn)
    sub.add_parser("cleanup").set_defaults(fn=cleanup)
    args = p.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
