#!/usr/bin/env bash
# Mirror the vLLM image into this stack's ECR repository.
# Avoids Docker Hub rate limits and keeps node start-up pulls inside AWS.
#
# Usage: scripts/mirror-image.sh [source-image]
#   source-image  default: vllm/vllm-openai:v0.32.0-cu129
# Env: AWS_REGION (default us-east-1)
set -euo pipefail

SRC_IMAGE="${1:-vllm/vllm-openai:v0.32.0-cu129}"
REGION="${AWS_REGION:-us-east-1}"
HERE="$(cd "$(dirname "$0")/.." && pwd)"

REPO_URL="$(terraform -chdir="$HERE" output -raw ecr_repository_url)"
REGISTRY="${REPO_URL%%/*}"
TAG="${SRC_IMAGE##*:}"
DEST="${REPO_URL}:${TAG}"

aws ecr get-login-password --region "$REGION" | docker login --username AWS --password-stdin "$REGISTRY"

docker pull --platform linux/amd64 "$SRC_IMAGE"
docker tag "$SRC_IMAGE" "$DEST"
docker push "$DEST"

DIGEST="$(aws ecr describe-images --region "$REGION" --repository-name "${REPO_URL#*/}" \
  --image-ids imageTag="$TAG" --query 'imageDetails[0].imageDigest' --output text)"

cat <<EOF

Mirrored to: ${DEST}
Pin it by digest in terraform.tfvars, then run terraform apply:

  vllm_image = "${REPO_URL}@${DIGEST}"
EOF
