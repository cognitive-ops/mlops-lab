#!/usr/bin/env bash
# End-to-end smoke test against the public endpoint.
#
# Usage: LLM_API_KEY=sk-... scripts/smoke-test.sh [base_url]
#   base_url default: `terraform output api_url`
set -euo pipefail

HERE="$(cd "$(dirname "$0")/.." && pwd)"
BASE="${1:-$(terraform -chdir="$HERE" output -raw api_url)}"
KEY="${LLM_API_KEY:?set LLM_API_KEY to a virtual key from scripts/create-key.sh}"
MODEL="${LLM_MODEL:-qwen2.5-7b-instruct}"

pass() { echo "PASS  $*"; }
fail() { echo "FAIL  $*"; exit 1; }

code() { curl -s -o /dev/null -w '%{http_code}' "$@"; }

[ "$(code "$BASE/v1/models")" = "401" ] && pass "unauthenticated /v1/models rejected" || fail "unauthenticated request was not rejected"
[ "$(code "$BASE/key/generate" -X POST)" = "404" ] && pass "admin path /key/generate not exposed" || fail "admin path reachable from the internet"
[ "$(code "$BASE/ui")" = "404" ] && pass "admin UI not exposed" || fail "admin UI reachable from the internet"
[ "$(code "$BASE/v1/models" -H "Authorization: Bearer $KEY")" = "200" ] && pass "authenticated /v1/models" || fail "/v1/models with key"

curl -fsS "$BASE/v1/chat/completions" \
  -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" \
  -d "{\"model\":\"$MODEL\",\"messages\":[{\"role\":\"user\",\"content\":\"Reply with the single word: ok\"}],\"max_tokens\":8}" \
  | python3 -c 'import json,sys; r=json.load(sys.stdin); print("PASS  chat completion ->", repr(r["choices"][0]["message"]["content"]))'

echo "--- streaming"
curl -fsSN "$BASE/v1/chat/completions" \
  -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" \
  -d "{\"model\":\"$MODEL\",\"stream\":true,\"messages\":[{\"role\":\"user\",\"content\":\"Count to 5\"}],\"max_tokens\":32}" \
  | head -n 5
echo
pass "streaming responded"
