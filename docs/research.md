# Uncensored coding agent: which model, where to run it, how to connect it

Researched 10 October 2026. Prices and model rankings change monthly, so re-check the linked pages before paying for anything. Benchmark numbers below are the model makers' own (vendor-reported), not independent tests.

## Short answer

- **Kaggle works, but it is a poor daily setup.** Its free GPUs (two T4s) can hold a good uncensored model, but sessions end after 12 hours or 20 idle minutes, you get roughly 30 GPU hours a week, the T4s are slow, and Kaggle's Acceptable Use Policy lists "server farming" and "activity unrelated to ML data science" as resource abuse. Using a notebook as a private API server for your coding agent is close to that line, so your account is at risk.
- **Strongest uncensored model you can realistically use:** **Qwen3.8-27B abliterated** (by huihui-ai, or the "heretic" version). It is a 27B model, about 17 GB at 4-bit, fits on one 24 GB GPU, and its base model scores 61.7 on SWE-bench Pro and 73.0 on Terminal-Bench 2.1.
- **Recommended setup:** run **OpenCode** on your laptop (the agent that reads, edits and runs things on your computer), pointed at that model on a **rented RTX 4090 or 3090** (about $0.13–0.35 per hour, only while you use it). If you don't want to manage a server, use **Featherless** for a flat **$25 a month** instead, with a 32K context limit.

## 1. Which uncensored model

"Abliterated" or "heretic" models are normal open models with the refusal behaviour removed by editing the weights. They keep almost all of the original skill, so the best uncensored coder is simply an abliterated copy of the best open coder that fits your hardware.

| Model (uncensored build) | Type | Download size (4-bit) | GPU memory needed | Notes |
|---|---|---|---|---|
| **Qwen3.8-27B abliterated** ([huihui-ai](https://huggingface.co/huihui-ai/Huihui-Qwen3.8-27B-abliterated-GGUF)) or [heretic-org/Qwen3.8-27B-heretic-ara](https://huggingface.co/heretic-org/Qwen3.8-27B-heretic-ara) | Dense 27B, Apache-2.0, released Aug 2026, 262K context, can see images | Q4_K_M 16.6 GB, UD-Q4_K_XL 17.4 GB | 24 GB (RTX 3090/4090) | **Best pick.** Base model: SWE-bench Pro 61.7, Terminal-Bench 2.1 73.0, LiveCodeBench v6 90.3 |
| Qwen3.6-35B-A3B abliterated ([huihui-ai](https://huggingface.co/huihui-ai/Huihui-Qwen3.6-35B-A3B-abliterated)) | Mixture-of-experts, 3B active | about 20 GB (estimate) | 24 GB, or two 16 GB GPUs | Much faster than the 27B but weaker. Best fit for Kaggle's slow T4s |
| Qwen3.8-Flash-Next abliterated ([huihui-ai](https://huggingface.co/huihui-ai/Huihui-Qwen3.8-Flash-Next-abliterated-GGUF)) | Mixture-of-experts, 177B total, community licence | UD-IQ4_XS 93.7 GB | 96 GB (RTX PRO 6000) | Bigger budget option. Base model: SWE-bench Pro 62.5, DeepSWE 58.7 (vs 42.2 for the 27B) |
| GLM-5.3-Flash abliterated ([huihui-ai](https://huggingface.co/huihui-ai/Huihui-GLM-5.3-Flash-abliterated-GGUF)) | Mixture-of-experts, about 321B, MIT | UD-IQ4_XS 157 GB | 2+ large GPUs | Too expensive to run for a modest budget |
| Qwen3.5-9B abliterated ([huihui-ai](https://huggingface.co/huihui-ai/Huihui-Qwen3.5-9B-abliterated)) | Dense 9B | about 6 GB | 8 GB, or a laptop with 16 GB RAM | Only if you want something on the laptop itself; much weaker |

Things worth knowing:

- **Stick to plain abliterated or heretic builds of the official model** (huihui-ai, heretic-org). Hugging Face is full of merges with names like "Cold-Fusion", "Claude distill" or "ULTRA" that have huge download counts but no independent testing; avoid them for real coding work.
- **Abliteration has a small quality cost** that huihui-ai does not measure. Their card for the 27B says only layers 18–51 were edited to keep more of the original performance.
- **"Uncensored" does not mean "smarter".** For ordinary coding, the strongest open models through a normal API, such as DeepSeek V4.1 Flash (about $0.30/$1.20 per million tokens on OpenRouter) or GLM-5.3-Flash (about $0.15/$0.50), are stronger than any 27B model and rarely refuse normal programming tasks. Refusals mostly show up around security tools, scraping and similar grey areas. A good habit is to use a mainstream model for most work and switch to the uncensored one when it refuses.

## 2. Where to run it

| Option | Cost | Good | Bad | Verdict |
|---|---|---|---|---|
| **Kaggle** (free) | Free | Two T4 GPUs (16 GB each) and 29 GB RAM can hold Qwen3.8-27B at 4-bit split across both, or Qwen3.6-35B-A3B | 12-hour session limit and a 20-minute idle timeout; weekly GPU quota around 30 hours (Kaggle doesn't publish it; check your account settings); T4s are 2018 hardware, so long agent prompts are slow; re-download about 17 GB each session; new tunnel URL each time; AUP risk (below) | Fine for one experiment, not for daily use |
| **Google Colab free** | Free | | Colab's FAQ bans on free runtimes "remote control such as SSH shells" and "bypassing the notebook UI to interact primarily via a web UI", and on all runtimes "web service offerings not related to interactive compute". Serving an API to your agent breaks these rules | Skip |
| **Rented GPU** (RunPod, Vast.ai) | RunPod RTX 4090 24 GB about $0.34/h, RTX 5090 32 GB about $0.69/h; Vast.ai RTX 3090 about $0.13/h, RTX 5090 median about $0.53/h | Any model, long context (64K–128K+), fast (community reports about 47–75 tokens/s for the 27B on a 4090), allowed by the provider, private to you | You start and stop it yourself; a few dollars a month for storage if you keep the disk | **Best value and the main recommendation** |
| **Featherless** (hosted API) | $25/month flat ("Featherless Chat" plan) | No setup; hosts both Qwen3.8-27B abliterated and the heretic build; its catalogue marks tool calling as supported | That model is capped at **32K context**, which runs out on larger projects; per-token pricing for it is $1.60 in / $12 out per million tokens, which is expensive for agents | **Best no-setup option** |
| **OpenRouter uncensored models** | Dolphin Mistral 24B Venice Edition $0.20/$0.90; Hermes 4 405B $1/$3 per million tokens | Cheap and easy | Old models, weak at coding, and OpenRouter doesn't list tool calling for them, which coding agents need | Not for agent coding |
| **Your laptop** | Free | Fully private | Only small models (about 9B) unless you have a strong GPU or a Mac with 32 GB+ memory | Backup only |

Example monthly cost for the rented-GPU route: 3 hours a day for 30 days is about 90 hours, so about $12 on a Vast.ai RTX 3090 or about $31 on a RunPod RTX 4090, plus a little storage.

### About Kaggle's rules

Kaggle's [Acceptable Use Policy](https://www.kaggle.com/aup) (version of 22 June 2025) says you may not "abuse resources offered as part of the Services", listing among other things "server farming" and "activity unrelated to ML data science". Plenty of public notebooks do expose a model through ngrok, and Kaggle doesn't name tunnels specifically, but running a notebook as a backend for your personal coding agent fits those two phrases uncomfortably well. If you try it anyway: use the "GPU T4 x2" accelerator, run llama.cpp's `llama-server` with an `--api-key`, and keep it short. Without a key, anyone who finds the tunnel URL can use your GPU.

## 3. Connecting the model to an agent that works on your computer

All of these tools run on your laptop and talk to any OpenAI-compatible endpoint (a URL ending in `/v1` plus an API key). The model runs in the cloud; the agent reads your files and runs commands locally.

| Tool | What it is | Why you might pick it |
|---|---|---|
| **[OpenCode](https://opencode.ai/docs/providers/)** | Terminal coding agent, MIT, the most widely used open one | **Recommended.** Reads and edits your project, runs commands, works with any OpenAI-compatible provider through a small JSON file |
| **Cline** | VS Code extension, plus a CLI | Pick it if you prefer working inside VS Code |
| **Aider** | Terminal, git-based editing | Uses very little context, so it suits Featherless's 32K limit. One tracker reports no commits since May 2026 |
| **OpenHands** | Autonomous agent that works in a Docker sandbox | Safer for long unattended jobs; heavier to set up |
| **Open Interpreter** | Runs code on your machine; "OS mode" can take screenshots and use mouse and keyboard | Only if you want it to control apps, not just code. Qwen3.8-27B can read images, but treat this as experimental |

### Example: rented GPU plus OpenCode

On the rented machine (a RunPod or Vast.ai template with CUDA and llama.cpp), start the server. `--jinja` turns on the chat template that tool calling needs:

```bash
llama-server -hf huihui-ai/Huihui-Qwen3.8-27B-abliterated-GGUF:UD-Q4_K_XL \
  -ngl 99 -c 65536 --jinja \
  --host 0.0.0.0 --port 8080 --api-key CHANGE_ME_TO_A_LONG_SECRET
```

On RunPod, expose HTTP port 8080 and your endpoint becomes `https://<POD_ID>-8080.proxy.runpod.net/v1`.

On your laptop, put this in `opencode.json` in your project (or `~/.config/opencode/opencode.json`):

```json
{
  "$schema": "https://opencode.ai/config.json",
  "provider": {
    "mygpu": {
      "npm": "@ai-sdk/openai-compatible",
      "name": "My rented GPU",
      "options": {
        "baseURL": "https://<POD_ID>-8080.proxy.runpod.net/v1",
        "apiKey": "{env:MYGPU_KEY}"
      },
      "models": {
        "qwen3.8-27b-abliterated": { "name": "Qwen3.8 27B abliterated" }
      }
    },
    "featherless": {
      "npm": "@ai-sdk/openai-compatible",
      "name": "Featherless",
      "options": {
        "baseURL": "https://api.featherless.ai/v1",
        "apiKey": "{env:FEATHERLESS_API_KEY}"
      },
      "models": {
        "huihui-ai/Huihui-Qwen3.8-27B-abliterated": { "name": "Qwen3.8 27B abliterated (Featherless)" }
      }
    }
  }
}
```

Then set `MYGPU_KEY` (or `FEATHERLESS_API_KEY`) in your shell, run `opencode` in your project folder, and pick the model with `/models`. **Stop the pod when you finish**, or it keeps billing.

## 4. Keep it from hurting your computer

An uncensored model will not hesitate before a destructive command, and the agent can run commands on your machine. Before you let it act:

- Keep the agent's "ask before running commands" approval on, at least until you trust the setup.
- Work in a project folder, a git repo you commit often, or better a VM, WSL or Docker container.
- Don't let it see passwords, SSH keys, browser profiles or crypto wallets.
- Always put an API key on your server. A public endpoint with no key is a free GPU for strangers.

## 5. Recommended setup

1. **Agent:** install OpenCode on your laptop.
2. **Model:** Qwen3.8-27B abliterated (huihui-ai GGUF, UD-Q4_K_XL).
3. **Where:** a rented RTX 3090 on Vast.ai (about $0.13/h) or RTX 4090 on RunPod (about $0.34/h), with `llama-server` as above, started when you code and stopped after.
4. **Everyday work:** add a cheap mainstream model (for example DeepSeek V4.1 Flash on OpenRouter) as a second provider in OpenCode, and switch to the uncensored one when it refuses.

What changes with a different situation:

- **You don't want to manage servers:** Featherless at $25/month, same model, 32K context. Pair it with Aider or keep OpenCode sessions small.
- **Bigger budget:** rent a 96 GB RTX PRO 6000 (about $1.69–2.09/h on RunPod, from about $0.80/h on Vast.ai) and run Qwen3.8-Flash-Next abliterated. It is noticeably better on long multi-step tasks (DeepSWE 58.7 vs 42.2) but barely better on SWE-bench Pro (62.5 vs 61.7).
- **Zero budget:** try Kaggle with Qwen3.6-35B-A3B abliterated for a few sessions, accepting the rules risk and the slowness, or run Qwen3.5-9B abliterated on your laptop.
- **Your laptop has an NVIDIA GPU with 24 GB, or a Mac with 32 GB+ memory:** you can run Qwen3.8-27B at 4-bit locally with Ollama (`ollama run huihui_ai/Qwen3.8-abliterated`) and skip the cloud entirely.

## Sources

- Kaggle notebook limits (12-hour sessions, 20-minute idle timeout, T4 x2 and P100 specs): [kaggle.com/docs/notebooks](https://www.kaggle.com/docs/notebooks)
- Kaggle Acceptable Use Policy: [kaggle.com/aup](https://www.kaggle.com/aup)
- Kaggle weekly quota of about 30 hours (not published by Kaggle): [gpuperhour.com](https://gpuperhour.com/blog/free-cloud-gpus-and-credits), [aicreditmart.com](https://aicreditmart.com/ai-credits-providers/kaggle-free-gpu-tpu-30-hours-week-access-guide-2026/)
- Colab disallowed activities: [Colab FAQ](https://research.google.com/colaboratory/faq.html)
- Qwen3.8-27B benchmarks and specs: [Qwen/Qwen3.8-27B model card](https://huggingface.co/Qwen/Qwen3.8-27B)
- Qwen3.8-Flash-Next and 27B coverage: [llm-stats.com](https://llm-stats.com/blog/research/qwen3.8-flash-next-launch), [acecloud.ai](https://acecloud.ai/blog/qwen3-8-27b-vs-flash-next/)
- Abliterated model cards: [Huihui-Qwen3.8-27B-abliterated](https://huggingface.co/huihui-ai/Huihui-Qwen3.8-27B-abliterated), [its GGUF files](https://huggingface.co/huihui-ai/Huihui-Qwen3.8-27B-abliterated-GGUF), [Flash-Next GGUF](https://huggingface.co/huihui-ai/Huihui-Qwen3.8-Flash-Next-abliterated-GGUF), [GLM-5.3-Flash GGUF](https://huggingface.co/huihui-ai/Huihui-GLM-5.3-Flash-abliterated-GGUF)
- Speed and memory reports for Qwen3.8-27B: [computingforgeeks.com](https://computingforgeeks.com/?p=171993), [zimaspace.com](https://shop.zimaspace.com/blogs/tech-ai-hub/run-qwen3-8-27b-locally-ram-vram-ollama)
- Open model landscape: [thundercompute.com](https://www.thundercompute.com/blog/best-open-source-llms), [llm-stats SWE-bench Verified](https://llm-stats.com/benchmarks/swe-bench-verified)
- Featherless plans and catalogue: [featherless.ai/docs/plans](https://featherless.ai/docs/plans), [api.featherless.ai/v1/models](https://api.featherless.ai/v1/models), [tool calling](https://featherless.ai/docs/tool-calling)
- OpenRouter model list and prices: [openrouter.ai/api/v1/models](https://openrouter.ai/api/v1/models)
- GPU rental prices: [RunPod pricing](https://www.runpod.io/gpu-cloud/pricing), [computeprices.com RunPod 4090](https://computeprices.com/providers/runpod/gpus/rtx4090), [Vast.ai RTX 5090](https://vast.ai/pricing/gpu/RTX-5090), [computeprices.com Vast 3090](https://computeprices.com/providers/vast/gpus/rtx3090), [RTX PRO 6000 prices](https://northflank.com/blog/how-much-does-an-nvidia-rtx-pro-6000-gpu-cost)
- Coding agents: [OpenCode providers docs](https://opencode.ai/docs/providers/), [morphllm.com comparison](https://www.morphllm.com/ai-coding-assistant-open-source), [pinggy.io CLI agents](https://pinggy.io/blog/best_open_source_cli_coding_agents/), [Open Interpreter on Real Python](https://realpython.com/ref/ai-coding-tools/open-interpreter)
