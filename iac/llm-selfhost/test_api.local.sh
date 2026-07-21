#!/bin/bash
# Quick smoke test for the local docker-compose vLLM deployment.
set -euo pipefail

if [ -f .env ]; then
  # shellcheck disable=SC1091
  source .env
fi

PORT=${VLLM_PORT:-8000}
MODEL=${MODEL_NAME:-qwen2.5-7b-instruct}
HOST=${1:-"http://localhost:$PORT"}

echo "Testing vLLM API at: $HOST"
echo
echo "=== Available Models ==="
curl -s "$HOST/v1/models" | jq '.'
echo
echo "=== Test Completion Request ==="
curl -s -X POST "$HOST/v1/completions" \
  -H "Content-Type: application/json" \
  -d "{\"model\": \"$MODEL\", \"prompt\": \"What is artificial intelligence?\", \"max_tokens\": 100, \"temperature\": 0.7, \"top_p\": 0.9}" | jq '.'
