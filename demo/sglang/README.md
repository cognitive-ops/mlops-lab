# SGLang Self-Hosted LLM (local Docker)

Serve an open-source LLM locally via [SGLang](https://github.com/sgl-project/sglang) with an OpenAI-compatible API. For an AWS EC2 deployment of the same server, see [iac/sglang-selfhost](../../iac/sglang-selfhost).

## Prerequisites

- NVIDIA GPU with recent driver + [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html)
- Docker + Docker Compose v2
- 16GB+ VRAM for the default model (Llama-3.1-8B-Instruct, bf16)
- HuggingFace token with access to `meta-llama/Llama-3.1-8B-Instruct` (gated repo)

## Setup

```bash
cp .env.example .env
# edit .env: set HF_TOKEN, optionally swap MODEL_REPO
```

## Run

```bash
make up      # starts SGLang, downloads model on first run (can take several minutes)
make logs    # watch startup / generation logs
make test    # hits /v1/models and /v1/chat/completions
```

## Manual API calls

```bash
curl http://localhost:30000/v1/models

curl -X POST http://localhost:30000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "meta-llama/Llama-3.1-8B-Instruct",
    "messages": [{"role": "user", "content": "What is AI?"}],
    "temperature": 0.7
  }'
```

## Swapping models

Edit `MODEL_REPO` in `.env` to any SGLang-supported HF repo (Llama, Qwen, Mistral, DeepSeek, Gemma, etc.), then `docker compose up -d sglang` to recreate with the new model. Adjust `MAX_MODEL_LEN` to match the model's context window and your VRAM budget.

## Why SGLang over vLLM

Both are OpenAI-API-compatible serving engines. SGLang's RadixAttention gives strong wins on multi-turn / shared-prefix workloads (agents, few-shot, chat with system prompts) via automatic KV-cache reuse across requests. For raw single-turn throughput the two are close; pick based on your workload shape.

## Cleanup

```bash
make down    # stop container
make clean   # also wipe downloaded weights cache
```
