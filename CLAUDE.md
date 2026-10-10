# Notes for continuing this work

Owner: Kien Hoang (GitHub `hoangkien1703`, Kaggle `andrewhoang2030`). Kien likes English
corrections on their messages before the answer.

## Goal

Use an uncensored open-weight model for coding through an agent (OpenCode) that can act on
Kien's Windows laptop. The laptop is too weak for big local models and the budget is small.

## Where things stand (2026-10-10)

- Kaggle T4 x2 run worked end to end: Ollama + password proxy + ngrok + OpenCode. About
  8 tokens/s output, ~200 tokens/s prompt. Kien found it "absurdly slow". Details:
  `docs/test-results.md`.
- Recommended next step: rented RTX 4090 on RunPod Community Cloud ($0.34/h) with
  llama.cpp (`docs/runpod-4090-setup.md`). Kien hasn't decided yet; other options were a
  lighter model on Kaggle, or stopping here.
- Kaggle quota: 30 GPU h/week. 57 min used so far; the API said the next reset is
  2026-10-17. Check with `kaggle_run.py quota`.

## Kien's laptop

- Windows, OpenCode desktop app.
- Global config: `C:\Users\hoang\.config\opencode\opencode.json`. It has MCP servers
  (chrome-devtools, windows-mcp, github, rea) and an `instructions` glob for rules files.
- A `kaggle` provider was added to that file for the test. It points at the Kaggle run's
  ngrok URL, which no longer exists, so that provider is dead until a new run fills in a new
  `baseURL` and `apiKey`. The original file is saved next to it as
  `opencode.json.before-kaggle.backup`.

## Running the Kaggle server

```bash
pip install kagglesdk requests
python kaggle/kaggle_run.py quota
python kaggle/kaggle_run.py push andrewhoang2030 [--model TAG] [--hours 2] [--idle 30]
python kaggle/kaggle_run.py logs andrewhoang2030      # wait for READY (~7 min)
python kaggle/kaggle_run.py info                      # base URL + password
python kaggle/kaggle_run.py stop
python kaggle/kaggle_run.py cleanup
```

Auth:
- In a Claude cloud environment, Kien set network secrets: Bearer token for `*.kaggle.com`
  (Kaggle API token) and for `api.ngrok.com` (ngrok API key). The proxy adds them, so code
  uses `KaggleClient()` with no credentials and plain `requests` for ngrok. Don't try to read
  or extract those secrets.
- Elsewhere, set `KAGGLE_API_TOKEN` and `NGROK_API_KEY` environment variables.
- Never ask Kien to paste a token into chat, and never commit one. `kaggle/state.json` holds
  the run's password and is gitignored.

## How the pieces fit

- `kaggle_run.py push` creates a temporary ngrok authtoken (`POST /credentials`), generates a
  password, replaces the placeholders in `serve_model.py` (`"__API_KEY__"`,
  `"__NGROK_AUTHTOKEN__"`, and the `MODEL`/`MAX_HOURS`/`IDLE_MINUTES` defaults), and saves a
  private Kaggle script kernel `qwen-coder-server` with GPU (`machine_shape="NvidiaTeslaT4"`)
  and internet on. `tests/test_push_placeholders.py` checks those placeholders still match.
- `serve_model.py` serves `/health` without auth, everything else needs
  `Authorization: Bearer <password>`, streams responses chunk by chunk, and `POST /__stop`
  shuts it down. It also stops after `MAX_HOURS` or `IDLE_MINUTES` without requests.
- Logs: `https://api.kaggle.com/v1/kernels/logs/stream/{owner}/qwen-coder-server` (SSE, ends
  with `END_OF_LOG`, replays from the start on reconnect).

## Gotchas

- Kaggle API returns 429 with `Retry-After: 5`; `call()` retries.
- First `opencode run` with a new provider installs `@ai-sdk/openai-compatible` and can take
  over 2 minutes.
- Keep `reasoningEffort: "none"` on slow GPUs. A run with thinking on hung at OpenCode startup.
- Cloudflare quick tunnels don't support SSE; use ngrok.
- Kaggle's acceptable use policy ("server farming", "activity unrelated to ML data science")
  makes this a grey area. Keep runs short and private.

## Tests

`python -m unittest discover -s tests -v` (offline, fake model server).
