# Qwen3.8-27B abliterated on Kaggle + OpenCode

Run an uncensored open-weight coding model on a free or cheap remote GPU, and use it from
[OpenCode](https://opencode.ai) on a laptop that is too weak to run it locally.

```
OpenCode (laptop)  --HTTPS + password-->  ngrok tunnel  -->  password proxy :8000  -->  Ollama :11434
                                                             (Kaggle "GPU T4 x2" job, kaggle/serve_model.py)
```

**Status (2026-10-10):** works end to end, but on Kaggle's T4s it is slow: about
**8 tokens/s** output. OpenCode fixed a small buggy project in 1m43s. A rented RTX 4090
(about $0.34/hour) should be roughly 6x faster and is the recommended next step.
Full numbers in [docs/test-results.md](docs/test-results.md).

## What's here

| Path | What it is |
|---|---|
| [`kaggle/serve_model.py`](kaggle/serve_model.py) | The Kaggle job. Installs Ollama, downloads the model, measures speed, starts a password proxy and an ngrok tunnel, prints `READY base_url=...`, stops on a time limit, on idle, or on request. |
| [`kaggle/kaggle_run.py`](kaggle/kaggle_run.py) | Runs on your machine. Pushes the job to Kaggle with a fresh password and a temporary ngrok token, follows logs, prints the URL and password for OpenCode, stops the server, cleans up. |
| [`opencode/`](opencode) | Example OpenCode configs for the Kaggle server and for a RunPod 4090 (placeholders, no keys). |
| [`docs/research.md`](docs/research.md) | Research: which uncensored model, where to run it (Kaggle, Colab, rented GPUs, APIs), which agent, safety. |
| [`docs/runpod-4090-setup.md`](docs/runpod-4090-setup.md) | Click-by-click guide for renting an RTX 4090 on RunPod, with costs. |
| [`docs/test-results.md`](docs/test-results.md) | Measurements and the OpenCode test from the Kaggle run. |
| [`examples/textstats/`](examples/textstats) | Small buggy project with failing tests, used to test the agent. |
| [`tests/`](tests) | Offline tests for the proxy and the push script (no GPU needed). |
| [`CLAUDE.md`](CLAUDE.md) | Notes for picking the work up later (with Claude or by hand). |

## The model

[`huihui_ai/Qwen3.8-abliterated:27b`](https://ollama.com/huihui_ai/Qwen3.8-abliterated)
(Ollama, 16.8 GB, Q4). GGUF for llama.cpp:
`huihui-ai/Huihui-Qwen3.8-27B-abliterated-GGUF:UD-Q4_K_XL` (17.4 GB).
"Abliterated" means the refusal behaviour was removed from the weights; it is otherwise
the normal Qwen3.8-27B, whose base model scores 61.7 on SWE-bench Pro and 73.0 on
Terminal-Bench 2.1. See [docs/research.md](docs/research.md) for other options.

## Quick start: Kaggle (free, slow)

You need a Kaggle account with phone verification (for GPU and internet), and a free
ngrok account.

1. **Install the Python packages** on the machine you run the launcher from:
   ```bash
   pip install kagglesdk requests
   ```
2. **Give it your keys** as environment variables (never put them in files in this repo):
   - `KAGGLE_API_TOKEN`: Kaggle > Settings > API > Generate New Token.
   - `NGROK_API_KEY`: dashboard.ngrok.com > API Keys > New API Key. This is the *API key*,
     not the agent authtoken. Each run creates its own temporary authtoken from it and
     deletes it at the end.

   In a Claude cloud environment, these are instead set as network secrets
   (Bearer for `*.kaggle.com` and for `api.ngrok.com`), so no variables are needed.
3. **Start the server**:
   ```bash
   python kaggle/kaggle_run.py quota                       # GPU hours left this week
   python kaggle/kaggle_run.py push YOUR_KAGGLE_USERNAME   # --hours 2 --idle 30 by default
   python kaggle/kaggle_run.py logs YOUR_KAGGLE_USERNAME   # wait for "READY base_url=..." (about 7 min)
   ```
4. **Get the URL and password** (in another terminal while `logs` runs):
   ```bash
   python kaggle/kaggle_run.py info
   ```
5. **Point OpenCode at it.** Copy the `kaggle` provider from
   [`opencode/opencode.kaggle.example.json`](opencode/opencode.kaggle.example.json) into your
   global config (`~/.config/opencode/opencode.json`, on Windows
   `C:\Users\<you>\.config\opencode\opencode.json`), fill in `baseURL` and `apiKey`, then pick
   "Qwen3.8 27B abliterated" in OpenCode's model list. The URL changes on every run.
6. **Stop it when you're done** (it also stops by itself after `--hours`, or after `--idle`
   minutes without requests):
   ```bash
   python kaggle/kaggle_run.py stop
   python kaggle/kaggle_run.py cleanup    # deletes the temporary ngrok token if a run crashed
   ```

## Quick start: RunPod RTX 4090 (about $0.35/hour, recommended)

Follow [docs/runpod-4090-setup.md](docs/runpod-4090-setup.md). In short: Community Cloud
RTX 4090, image `ghcr.io/ggml-org/llama.cpp:server-cuda`, start command

```
-hf huihui-ai/Huihui-Qwen3.8-27B-abliterated-GGUF:UD-Q4_K_XL -ngl 99 -c 65536 -np 1 --cache-type-k q8_0 --cache-type-v q8_0 --no-mmproj --jinja --host 0.0.0.0 --port 8080
```

with `LLAMA_API_KEY` set to a password you choose, 40 GB container disk, port 8080 exposed.
Then use [`opencode/opencode.runpod.example.json`](opencode/opencode.runpod.example.json).
Terminate the pod when you finish so billing stops.

## Costs

| Option | Cost | Speed (this model) |
|---|---|---|
| Kaggle T4 x2 | Free, 30 GPU hours/week | ~8 tokens/s |
| RunPod Community RTX 4090 | $0.34/h ($10 minimum top-up) | ~50 tokens/s expected |
| RunPod Community RTX 3090 | $0.22/h | somewhat slower than a 4090 |
| RunPod Secure RTX 4090 | $0.89/h | same as Community |

Prices checked on 2026-10-10.

## Security

- The server is on the public internet. Every request except `/health` needs the password
  (`Authorization: Bearer ...`), which `kaggle_run.py` generates fresh for each run and keeps
  in `kaggle/state.json` (gitignored, mode 600).
- `kaggle_run.py` puts the password and a temporary ngrok token into the job source before
  uploading it. The Kaggle notebook is private, but anyone with access to your Kaggle account
  can read them. Both stop working when the run ends (the ngrok token is deleted).
- Never commit `kaggle/state.json`, `kaggle/run.log`, or a filled-in OpenCode config.
- An uncensored model in an agent that can run commands will do what it is told, including
  harmful things it misunderstood. Commit your work before each task, keep OpenCode's
  permission prompts on for commands, and don't give it access to folders it doesn't need.
  More in [docs/research.md](docs/research.md#4-keep-it-from-hurting-your-computer).

## Things learned

- **Kaggle's rules are a grey area for this.** The acceptable use policy bans "server
  farming" and activity unrelated to machine learning. Using it briefly for testing is low
  risk, but it is not a good permanent setup. Google Colab's FAQ explicitly bans remote
  control and serving a web UI from free runtimes, so it was not tried.
- **Cloudflare quick tunnels don't stream (no SSE)**, which breaks OpenCode's streaming
  replies, so ngrok is used. ngrok's free plan has 1 GB/month and 20k requests, and API
  clients don't see the browser warning page (the `ngrok-skip-browser-warning` header is
  set anyway).
- **Long prompts are the real cost on slow GPUs.** OpenCode sends its system prompt, tool
  descriptions and file contents on every step. MCP servers add more. At ~200 tokens/s prompt
  reading, a 9k-token step takes over a minute before any output.
- **Turn thinking off** (`"reasoningEffort": "none"`) on slow hardware.
- **Kaggle API** returns 429 sometimes (retry after ~5 s). The log stream endpoint replays
  from the start each time you reconnect.
- **T4 x2 is not double-counted** against the 30 h/week quota: 57 minutes used 57 minutes.

## Next steps

- Try the same setup on a RunPod Community RTX 4090 and compare speed and cost.
- If staying on Kaggle: try a smaller model (for example a 14B coder) for speed, and remove
  MCP servers from the OpenCode config to shorten prompts.
- Optional: a one-command RunPod launcher like `kaggle_run.py`, using the RunPod API.

## Running the tests

```bash
python -m unittest discover -s tests -v
```

The tests start the proxy against a fake model server; no GPU, Kaggle or ngrok needed.
