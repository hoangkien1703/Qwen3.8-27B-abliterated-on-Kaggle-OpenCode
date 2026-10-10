# Test results: Kaggle T4 x2 run, 2026-10-10

One run of `kaggle/serve_model.py` on Kaggle's free "GPU T4 x2", used by OpenCode
from a cloud test machine and then from Kien's Windows laptop (OpenCode desktop app).
Times are UTC.

## Setup timeline

| Step | Time | Took |
|---|---|---|
| Job starts (2x Tesla T4, 15 GB each) | 02:37:07 | |
| Ollama installed (v0.40.2) | 02:38:52 | 1m45s |
| Model downloaded (16.8 GB, `huihui_ai/Qwen3.8-abliterated:27b`) | 02:41:43 | 163s |
| Model loaded + first answer | 02:44:21 | 158s |
| Proxy + ngrok tunnel up, `READY` printed | 02:44:24 | |
| Stopped via `POST /__stop` | 03:34:04 | |

**About 7 minutes from push to ready.** Total run 57 minutes, which used 57 minutes of
the 30 h/week GPU quota (T4 x2 is not counted twice).

Memory after load: 10.6 GB on GPU 0 and 11.0 GB on GPU 1 (`ollama ps`: 19 GB, 100% GPU,
context 65536). There is room left, so a bigger context or a slightly bigger quant may fit.

## Speed

| Measure | Value |
|---|---|
| Output (generation) | **7.4 to 8 tokens/s** (`tg = 7.48 t/s` on a 569-token answer) |
| Prompt reading | about 200 tokens/s on long prompts (the 0.8 tok/s in the log is a 1-token warm-up artifact) |
| Largest request seen | 9,388 tokens of context, 569 tokens out, **1m17s** end to end |
| Speculative decoding (MTP draft) | 33% to 77% acceptance, mean accepted length 2.3 to 3.4 |

For comparison, the same model on a single RTX 4090 is expected around 45 to 55 tokens/s,
roughly 6x faster. Kien's verdict after trying it in the OpenCode app: "absurdly slow, but
at least it worked".

## OpenCode task test

Project: [`examples/textstats`](../examples/textstats), a small module with two bugs and
4 failing unit tests.

Prompt given to `opencode run`:

> The tests in test_textstats.py are failing. Fix textstats.py so that all tests pass,
> without changing the tests. Run python3 -m unittest to check your work, and stop when
> all 4 tests pass.

Result: **all 4 tests pass, 1m43s, 6 agent steps** (03:05:47 to 03:07:30), thinking off
(`reasoningEffort: "none"`). The model's fix:

```diff
 def word_count(text):
     """Return the number of words in text."""
-    return len(text.split(" "))
+    return len(text.split())

 def average_word_length(text):
     """Return the average word length, ignoring punctuation."""
     words = text.split()
-    total = sum(len(w) for w in words)
+    if not words:
+        return 0
+    total = 0
+    for w in words:
+        total += sum(1 for c in w if c not in string.punctuation)
     return total / len(words)
```

(plus `import string` at the top). Final message from the model: "All 4 tests pass. Fixed
`word_count` to use `split()` (handles extra spaces/empty strings) and
`average_word_length` to ignore punctuation and return 0 for empty text."

## Things that went wrong and how they were fixed

- **First OpenCode run timed out** at 120 s: OpenCode installs the
  `@ai-sdk/openai-compatible` package on first use. Running again worked.
- **A second test with thinking turned on hung at startup** without sending any request.
  That was OpenCode, not the server. Keep `reasoningEffort: "none"` on this hardware; thinking
  adds hundreds of tokens per step at 8 tokens/s.
- **Two `401`s for `GET /v1 model=...`** in the log: someone opened the printed READY line in a
  browser. The proxy rejects everything without the password except `/health`.
- **Kaggle API `429 Too Many Requests`** (Retry-After 5 s). `kaggle_run.py` retries.
- **Log stream replays from the start on reconnect**, so `kaggle_run.py logs` rewrites the
  file instead of appending.
- **Laptop OpenCode has several MCP servers** (chrome-devtools, windows-mcp, github, rea).
  Their tool descriptions make every prompt much longer, which at ~200 tokens/s prompt speed
  adds real waiting time. Disable unneeded MCP servers when using a slow model.
