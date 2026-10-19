#!/usr/bin/env bash
# Issue a LiteLLM virtual API key for an agent or team.
# The admin API is not exposed through the public ALB, so this uses a temporary
# kubectl port-forward and the master key from AWS Secrets Manager.
#
# Usage: scripts/create-key.sh <alias> [rpm] [tpm] [max_budget_usd] [budget_duration]
#   e.g. scripts/create-key.sh support-agents 600 400000 500 30d
# Env: AWS_REGION (default us-east-1)
set -euo pipefail

ALIAS="${1:?usage: create-key.sh <alias> [rpm] [tpm] [max_budget_usd] [budget_duration]}"
RPM="${2:-300}"
TPM="${3:-200000}"
BUDGET="${4:-100}"
DURATION="${5:-30d}"
REGION="${AWS_REGION:-us-east-1}"
HERE="$(cd "$(dirname "$0")/.." && pwd)"

SECRET_NAME="$(terraform -chdir="$HERE" output -raw gateway_secret_name)"
MASTER_KEY="$(aws secretsmanager get-secret-value --region "$REGION" --secret-id "$SECRET_NAME" \
  --query SecretString --output text | python3 -c 'import json,sys; print(json.load(sys.stdin)["LITELLM_MASTER_KEY"])')"

kubectl -n llm port-forward svc/litellm 14000:4000 >/dev/null 2>&1 &
PF_PID=$!
trap 'kill $PF_PID 2>/dev/null || true' EXIT
for _ in $(seq 1 20); do
  curl -fs http://127.0.0.1:14000/health/liveliness >/dev/null 2>&1 && break
  sleep 1
done

curl -fsS http://127.0.0.1:14000/key/generate \
  -H "Authorization: Bearer ${MASTER_KEY}" \
  -H "Content-Type: application/json" \
  -d "{\"key_alias\":\"${ALIAS}\",\"rpm_limit\":${RPM},\"tpm_limit\":${TPM},\"max_budget\":${BUDGET},\"budget_duration\":\"${DURATION}\"}"
echo
