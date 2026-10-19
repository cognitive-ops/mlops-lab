#!/usr/bin/env bash
# One-off: create the S3 bucket (versioned, encrypted, private) used by the
# Terraform S3 backend. Locking uses a lockfile in the same bucket. Idempotent.
#
#   STATE_BUCKET=my-org-vllm-eks-tfstate AWS_REGION=us-east-1 scripts/bootstrap-state.sh
set -euo pipefail

: "${STATE_BUCKET:?set STATE_BUCKET (globally unique)}"
REGION="${AWS_REGION:-us-east-1}"

if aws s3api head-bucket --bucket "$STATE_BUCKET" 2>/dev/null; then
  echo "bucket $STATE_BUCKET exists"
else
  if [ "$REGION" = "us-east-1" ]; then
    aws s3api create-bucket --bucket "$STATE_BUCKET" --region "$REGION"
  else
    aws s3api create-bucket --bucket "$STATE_BUCKET" --region "$REGION" \
      --create-bucket-configuration "LocationConstraint=$REGION"
  fi
fi

aws s3api put-public-access-block --bucket "$STATE_BUCKET" \
  --public-access-block-configuration \
  BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
aws s3api put-bucket-versioning --bucket "$STATE_BUCKET" \
  --versioning-configuration Status=Enabled
aws s3api put-bucket-encryption --bucket "$STATE_BUCKET" \
  --server-side-encryption-configuration \
  '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"aws:kms"},"BucketKeyEnabled":true}]}'

echo "done. cp backend.hcl.example backend.hcl, set bucket, then: terraform init -backend-config=backend.hcl"
