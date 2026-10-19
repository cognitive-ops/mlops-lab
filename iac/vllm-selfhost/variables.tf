# ---------------------------------------------------------------------------
# General
# ---------------------------------------------------------------------------
variable "aws_region" {
  description = "AWS region. Must have g6e (L40S) capacity and quota."
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Name prefix for all resources"
  type        = string
  default     = "vllm-eks"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "prod"

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "environment must be dev, staging, or prod."
  }
}

variable "owner" {
  description = "Owner/team responsible for resources"
  type        = string
  default     = "ai-platform"
}

variable "tags" {
  description = "Additional tags to apply to all resources"
  type        = map(string)
  default     = {}
}

variable "deletion_protection" {
  description = "Protect stateful resources (ALB, Aurora, S3 buckets) from accidental deletion. Set false only for throwaway environments."
  type        = bool
  default     = true
}

# ---------------------------------------------------------------------------
# Network
# ---------------------------------------------------------------------------
variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "az_count" {
  description = "Number of availability zones to span"
  type        = number
  default     = 3

  validation {
    condition     = var.az_count >= 2 && var.az_count <= 6
    error_message = "az_count must be between 2 and 6."
  }
}

variable "single_nat_gateway" {
  description = "Use one shared NAT gateway instead of one per AZ. Cheaper, but an AZ-level single point of failure."
  type        = bool
  default     = false
}

variable "enable_ecr_vpc_endpoints" {
  description = "Create ECR interface endpoints so image pulls bypass the NAT gateway (S3 gateway endpoint is always created)"
  type        = bool
  default     = true
}

# ---------------------------------------------------------------------------
# Cluster
# ---------------------------------------------------------------------------
variable "kubernetes_version" {
  description = "EKS Kubernetes version"
  type        = string
  default     = "1.34"
}

variable "cluster_endpoint_public_access" {
  description = "Expose the Kubernetes API publicly (restricted by cluster_endpoint_public_access_cidrs). Set false to require VPN/bastion access."
  type        = bool
  default     = true
}

variable "cluster_endpoint_public_access_cidrs" {
  description = "CIDRs allowed to reach the public Kubernetes API endpoint. Restrict to your operator/CI egress IPs."
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "system_node_instance_types" {
  description = "Instance types for the CPU system node group (Karpenter, gateway, router, monitoring)"
  type        = list(string)
  default     = ["m6i.2xlarge"]
}

variable "system_node_min_size" {
  description = "Minimum system nodes (keep >= az_count for zone spread)"
  type        = number
  default     = 3
}

variable "system_node_max_size" {
  description = "Maximum system nodes"
  type        = number
  default     = 6
}

variable "system_node_desired_size" {
  description = "Initial desired system nodes"
  type        = number
  default     = 3
}

variable "system_node_disk_size_gb" {
  description = "Root volume size of system nodes (also used as scratch space by the model-sync job)"
  type        = number
  default     = 100
}

# ---------------------------------------------------------------------------
# GPU capacity (Karpenter)
# ---------------------------------------------------------------------------
variable "gpu_instance_family" {
  description = "GPU instance family. FP8 requires Ada/Hopper: g6e (L40S) or g6 (L4)."
  type        = string
  default     = "g6e"
}

variable "gpu_instance_sizes" {
  description = "Single-GPU sizes of the family Karpenter may use (more sizes = more Spot pools)"
  type        = list(string)
  default     = ["xlarge", "2xlarge", "4xlarge"]
}

variable "gpu_baseline_count" {
  description = "Always-on GPU replicas on the baseline (on-demand) pool. Size from benchmarks."
  type        = number
  default     = 5
}

variable "gpu_max_count" {
  description = "Hard ceiling on total GPUs (baseline + burst). Must be backed by AWS service quota."
  type        = number
  default     = 16

  validation {
    condition     = var.gpu_max_count >= 1
    error_message = "gpu_max_count must be at least 1."
  }
}

variable "gpu_burst_capacity_types" {
  description = "Capacity types for burst GPUs. Karpenter prefers spot when both are listed and falls back to on-demand."
  type        = list(string)
  default     = ["spot", "on-demand"]
}

variable "gpu_ami_alias" {
  description = "Karpenter AMI alias for GPU nodes. Pin a release (e.g. al2023@v20250901) in production and roll it deliberately."
  type        = string
  default     = "al2023@latest"
}

variable "gpu_node_disk_size_gb" {
  description = "Root volume size of GPU nodes (holds the ~10 GB vLLM image)"
  type        = number
  default     = 200
}

# ---------------------------------------------------------------------------
# Model / vLLM
# ---------------------------------------------------------------------------
variable "model_repo" {
  description = "Hugging Face repo to mirror into S3 and serve"
  type        = string
  default     = "Qwen/Qwen2.5-7B-Instruct"
}

variable "model_revision" {
  description = "Hugging Face revision (commit hash recommended) to mirror. Changing it re-syncs the weights."
  type        = string
  default     = "main"
}

variable "model_served_name" {
  description = "Model name clients send in the `model` field"
  type        = string
  default     = "qwen2.5-7b-instruct"
}

variable "model_source" {
  description = "Where vLLM loads weights from: s3 (streamed from the model bucket) or hf (downloaded from Hugging Face at start)"
  type        = string
  default     = "s3"

  validation {
    condition     = contains(["s3", "hf"], var.model_source)
    error_message = "model_source must be s3 or hf."
  }
}

variable "hf_token" {
  description = "Hugging Face token for the model-sync job (only needed for gated repos)"
  type        = string
  default     = ""
  sensitive   = true
}

variable "vllm_image" {
  description = "vLLM image. Prefer your ECR mirror (see scripts/mirror-image.sh) pinned by digest to avoid Docker Hub rate limits."
  type        = string
  default     = "vllm/vllm-openai:v0.32.0-cu129"
}

variable "vllm_quantization" {
  description = "vLLM --quantization value (fp8 = online FP8 on Ada/Hopper). Empty string disables."
  type        = string
  default     = "fp8"
}

variable "vllm_kv_cache_dtype" {
  description = "vLLM --kv-cache-dtype (fp8 halves KV memory). Validate quality with your evals."
  type        = string
  default     = "fp8"
}

variable "vllm_max_model_len" {
  description = "Maximum context length per request"
  type        = number
  default     = 16384
}

variable "vllm_max_num_seqs" {
  description = "Maximum concurrent sequences per replica"
  type        = number
  default     = 128
}

variable "vllm_gpu_memory_utilization" {
  description = "Fraction of GPU memory vLLM may use"
  type        = number
  default     = 0.9
}

variable "vllm_tool_call_parser" {
  description = "vLLM --tool-call-parser for the model family (hermes for Qwen2.5)"
  type        = string
  default     = "hermes"
}

variable "vllm_extra_args" {
  description = "Additional vLLM CLI arguments"
  type        = list(string)
  default     = []
}

variable "vllm_target_concurrency_per_replica" {
  description = "Autoscaling target: running + waiting requests per replica. Keep well below vllm_max_num_seqs for headroom."
  type        = number
  default     = 64
}

variable "vllm_target_kv_cache_usage" {
  description = "Autoscaling target: average KV-cache usage ratio (0-1)"
  type        = number
  default     = 0.75
}

# ---------------------------------------------------------------------------
# Gateway / router
# ---------------------------------------------------------------------------
variable "litellm_image" {
  description = "LiteLLM proxy image"
  type        = string
  default     = "ghcr.io/berriai/litellm:v1.106.0"
}

variable "litellm_min_replicas" {
  description = "Minimum LiteLLM replicas"
  type        = number
  default     = 3
}

variable "litellm_max_replicas" {
  description = "Maximum LiteLLM replicas"
  type        = number
  default     = 10
}

variable "litellm_max_request_size_mb" {
  description = "Reject request bodies larger than this at the gateway"
  type        = number
  default     = 4
}

variable "router_image" {
  description = "vLLM production-stack router image"
  type        = string
  default     = "lmcache/lmstack-router:v0.1.13"
}

variable "router_replicas" {
  description = "Router replicas"
  type        = number
  default     = 2
}

variable "router_routing_logic" {
  description = "Router policy: prefixaware (cache-aware, no client cooperation), session (needs a session header), or roundrobin"
  type        = string
  default     = "prefixaware"

  validation {
    condition     = contains(["prefixaware", "session", "roundrobin"], var.router_routing_logic)
    error_message = "router_routing_logic must be prefixaware, session, or roundrobin."
  }
}

# ---------------------------------------------------------------------------
# Edge
# ---------------------------------------------------------------------------
variable "domain_name" {
  description = "Public FQDN for the API (e.g. llm.example.com). Empty = HTTP-only ALB on its AWS hostname (testing only, keys travel unencrypted)."
  type        = string
  default     = ""
}

variable "route53_zone_id" {
  description = "Route 53 hosted zone ID that contains domain_name (required when domain_name is set)"
  type        = string
  default     = ""

  validation {
    condition     = var.domain_name == "" || var.route53_zone_id != ""
    error_message = "route53_zone_id is required when domain_name is set."
  }
}

variable "allowed_ingress_cidrs" {
  description = "CIDRs allowed to reach the public ALB. Narrow this to your agents' egress ranges when known."
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "waf_rate_limit_per_5min" {
  description = "Max requests per source IP per 5 minutes before WAF blocks it. Raise if many agents share one NAT egress IP."
  type        = number
  default     = 6000
}

variable "alarm_email" {
  description = "Email subscribed to the alarm SNS topic (must confirm the subscription). Empty = topic only."
  type        = string
  default     = ""
}

# ---------------------------------------------------------------------------
# Data tier
# ---------------------------------------------------------------------------
variable "aurora_engine_version" {
  description = "Aurora PostgreSQL engine version (LiteLLM state: keys, budgets, spend)"
  type        = string
  default     = "16.8"
}

variable "aurora_min_acu" {
  description = "Aurora Serverless v2 minimum capacity (ACU)"
  type        = number
  default     = 0.5
}

variable "aurora_max_acu" {
  description = "Aurora Serverless v2 maximum capacity (ACU)"
  type        = number
  default     = 8
}

variable "redis_node_type" {
  description = "ElastiCache node type for rate-limit counters"
  type        = string
  default     = "cache.t4g.small"
}

variable "log_retention_days" {
  description = "CloudWatch log retention (cluster, WAF)"
  type        = number
  default     = 30
}

variable "monitoring_storage_gb" {
  description = "Prometheus persistent volume size"
  type        = number
  default     = 100
}
