# Rent an RTX 4090 on RunPod and connect OpenCode

Prices checked live on 10 October 2026 from RunPod's and Vast.ai's own APIs.

## What it actually costs

**Live prices right now (one GPU, on-demand):**

| Where | GPU | Price per hour | Availability now |
|---|---|---|---|
| RunPod Community Cloud | RTX 4090 24 GB | **$0.34** | Low stock |
| RunPod Community Cloud | RTX 3090 24 GB | $0.22 | Low stock |
| RunPod Secure Cloud | RTX 4090 24 GB | $0.89 | High stock |
| Vast.ai (verified hosts) | RTX 4090 24 GB | $0.40 cheapest, $0.51 typical | 40 offers |

**Everything else on RunPod is close to free for this setup:**

- Container disk (40 GB, holds the model while the pod runs): $0.10 per GB per month, so about half a cent per hour.
- No volume disk, so nothing is billed after you terminate the pod.
- Downloading the model at each start: no transfer fees, and it takes a few minutes of GPU time, about 2 cents.
- Billing is per second.

**So one session costs about $0.35 per hour.** Examples:

| How much you use it | Monthly cost |
|---|---|
| 1 hour a day | about $11 |
| 3 hours a day | about $32 |
| Two 5-hour weekend sessions a week | about $15 |

To start, you add credit first. The minimum is $10, it isn't refundable, and it buys about 28 hours on a Community 4090.

For comparison: at roughly 50 tokens per second, an hour of the 4090 produces about 180,000 tokens, which works out to under $2 per million output tokens, with input tokens free. Featherless charges $12 per million output tokens for the same model on pay-as-you-go. That figure is an estimate, so check your own speed in the logs.

## Setup (about 15 minutes the first time)

### 1. Make an account and add credit

1. Sign up at [runpod.io](https://www.runpod.io).
2. Go to **Billing** and add $10.
3. Make up a long random password for your model server. It stops strangers from using your GPU, because the URL is public. Example: `kien-` followed by 30 random letters and numbers. Below it's called `YOUR_KEY`.

### 2. Start the pod

1. Go to **Pods** and click **Deploy**.
2. Pick **Community Cloud** and the **RTX 4090**. If none are free, the **RTX 3090** ($0.22/h) works with exactly the same settings, just a bit slower.
3. Under the filters, set **CUDA version** to **12.8 or newer**, because the server image needs it.
4. Click **Change Template** or **Edit Template**, and set:
   - **Container Image:** `ghcr.io/ggml-org/llama.cpp:server-cuda`
   - **Container Start Command:**
     ```
     -hf huihui-ai/Huihui-Qwen3.8-27B-abliterated-GGUF:UD-Q4_K_XL -ngl 99 -c 65536 -np 1 --cache-type-k q8_0 --cache-type-v q8_0 --no-mmproj --jinja --host 0.0.0.0 --port 8080
     ```
   - **Container Disk:** `40` GB
   - **Volume Disk:** `0` GB
   - **Expose HTTP Ports:** `8080`
   - **Environment Variables:** add `LLAMA_API_KEY` with the value `YOUR_KEY`
5. Choose **On-Demand** (not Spot, which can be interrupted), then click **Deploy**.

What the settings do: the model file is 17.4 GB. `-c 65536` gives a 64K-token working memory, and the `q8_0` cache settings shrink that memory so everything fits in 24 GB. `--no-mmproj` skips the image-reading add-on to save about 1 GB. `-np 1` gives the whole context to your one agent.

### 3. Wait until it's ready

Open the pod and look at **Logs**. The first start downloads the model, which takes a few minutes. It's ready when you see a line containing `listening on http://0.0.0.0:8080`.

Your endpoint is `https://<POD_ID>-8080.proxy.runpod.net/v1`. The pod ID is shown on the pod card.

Test it from your laptop. On Windows PowerShell, use `curl.exe` instead of `curl`:

```bash
curl https://<POD_ID>-8080.proxy.runpod.net/v1/models -H "Authorization: Bearer YOUR_KEY"
```

If you get a JSON answer that mentions the model, it works. If you get "Invalid API Key", check the `LLAMA_API_KEY` variable.

### 4. Install OpenCode on your laptop

- macOS or Linux: `curl -fsSL https://opencode.ai/install | bash`
- Windows: `npm install -g opencode-ai` (needs Node.js). OpenCode recommends running it inside WSL for the best experience.

### 5. Point OpenCode at your GPU

Create the global config file:

- macOS or Linux: `~/.config/opencode/opencode.json`
- Windows: `C:\Users\<you>\.config\opencode\opencode.json`

```json
{
  "$schema": "https://opencode.ai/config.json",
  "model": "mygpu/qwen3.8-27b-abliterated",
  "small_model": "mygpu/qwen3.8-27b-abliterated",
  "provider": {
    "mygpu": {
      "npm": "@ai-sdk/openai-compatible",
      "name": "My rented 4090",
      "options": {
        "baseURL": "https://<POD_ID>-8080.proxy.runpod.net/v1",
        "apiKey": "YOUR_KEY"
      },
      "models": {
        "qwen3.8-27b-abliterated": {
          "name": "Qwen3.8 27B abliterated",
          "limit": { "context": 65536, "output": 16384 }
        }
      }
    }
  }
}
```

The pod ID changes every time you create a new pod, so update `baseURL` each session.

Then open a terminal in your project folder, run `opencode`, and give it a task. Before your first real task, commit your work in git so you can undo anything it does.

### 6. When you finish: terminate the pod

Go to **Pods**, click the trash icon, and choose **Terminate**. Billing stops right away. Your code is safe, because it lives on your laptop. The pod only held the model, which downloads again next time.

If your balance reaches $0, RunPod stops the pod by itself. Pods without a volume disk are deleted at that point, and nothing on the pod survives.

## If something goes wrong

- **Error 524 in OpenCode:** RunPod's proxy closes any request that sends nothing back for 100 seconds. OpenCode streams answers, so this should be rare. If it happens, lower `-c` to `32768`.
- **Logs show "out of memory":** change `-c 65536` to `-c 32768`.
- **Logs show a CUDA or driver error:** the machine's driver is too old. Terminate the pod and deploy again with the CUDA 12.8+ filter.
- **It's slow to start answering:** Qwen3.8 thinks before it answers by default, which is normal. Output itself should come at roughly 45 to 75 tokens per second, according to community reports for a 4090.

## Check what you actually spent

RunPod's **Billing** page shows spending per pod, per hour. After your first session, compare it with the table at the top.
