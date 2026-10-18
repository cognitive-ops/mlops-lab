# Azure
variable "subscription_id" {
  description = "Azure subscription ID (empty = use az CLI / ARM_SUBSCRIPTION_ID default)"
  type        = string
  default     = ""
}

variable "location" {
  description = "Azure region. Must have GPU VM quota for gpu_vm_size (check: az vm list-usage -l <region>)"
  type        = string
  default     = "eastus"
}

# Project Configuration
variable "project_name" {
  description = "Name prefix for resources"
  type        = string
  default     = "sglang-qwen"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be dev, staging, or prod."
  }
}

variable "owner" {
  description = "Owner/team responsible for resources"
  type        = string
  default     = "ai-team"
}

variable "tags" {
  description = "Additional tags to apply to resources"
  type        = map(string)
  default     = {}
}

# AKS cluster
variable "kubernetes_version" {
  description = "AKS Kubernetes version (null = AKS default)"
  type        = string
  default     = null
}

variable "system_node_vm_size" {
  description = "VM size for the CPU system node pool"
  type        = string
  default     = "Standard_D4s_v5"
}

variable "system_node_count" {
  description = "Node count for the system pool"
  type        = number
  default     = 1
}

# GPU node pool
variable "gpu_vm_size" {
  description = "GPU VM size. Qwen2.5-7B bf16 (~15GB) needs >=24GB VRAM: Standard_NC24ads_A100_v4 (A100 80GB), Standard_NV36ads_A10_v5 (A10 24GB). Standard_NC4as_T4_v3 (T4 16GB) only fits <=3B models or quantized."
  type        = string
  default     = "Standard_NC24ads_A100_v4"

  validation {
    condition     = can(regex("^Standard_N[CDV]", var.gpu_vm_size))
    error_message = "gpu_vm_size must be an Azure N-series GPU VM (NC/ND/NV)."
  }
}

variable "gpu_node_count" {
  description = "Number of GPU nodes (also max when autoscaling)"
  type        = number
  default     = 1
}

variable "gpu_node_min_count" {
  description = "Min GPU nodes. 0 allows scale-to-zero when idle (cold start = node provisioning + model load)."
  type        = number
  default     = 1
}

variable "gpu_use_spot" {
  description = "Use Spot GPU nodes (cheap, can be evicted)"
  type        = bool
  default     = false
}

variable "gpu_os_disk_size_gb" {
  description = "OS disk size for GPU nodes in GB"
  type        = number
  default     = 128
}

# Model Configuration
variable "model_name" {
  description = "Name clients use in the `model` field of API requests (--served-model-name)"
  type        = string
  default     = "qwen2.5-7b-instruct"
}

variable "model_repo" {
  description = "HuggingFace model repository ID"
  type        = string
  default     = "Qwen/Qwen2.5-7B-Instruct"
}

variable "hf_token" {
  description = "HuggingFace token (not needed for public Qwen repos). Prefer TF_VAR_hf_token env var."
  type        = string
  default     = ""
  sensitive   = true
}

variable "model_cache_size_gb" {
  description = "Persistent disk size for the HuggingFace model cache in GB"
  type        = number
  default     = 100
}

# SGLang
variable "sglang_image" {
  description = "SGLang container image (pin a version for reproducibility)"
  type        = string
  default     = "lmsysorg/sglang:latest"
}

variable "sglang_port" {
  description = "Port for SGLang OpenAI-compatible API"
  type        = number
  default     = 30000
}

variable "sglang_context_length" {
  description = "Maximum context length for the model"
  type        = number
  default     = 8192
}

variable "sglang_mem_fraction_static" {
  description = "Fraction of GPU memory reserved for weights + KV cache (0.0 to 1.0)"
  type        = number
  default     = 0.9
}

variable "sglang_tool_call_parser" {
  description = "Tool-call parser matching the model family (qwen25 for Qwen2.5/Qwen3, llama3, mistral, ...). Empty = disabled."
  type        = string
  default     = "qwen25"
}

variable "sglang_tp_size" {
  description = "Tensor parallel size. Must equal GPUs per node used (gpus_per_pod)."
  type        = number
  default     = 1
}

variable "sglang_extra_args" {
  description = "Extra args appended to sglang.launch_server (e.g. [\"--quantization\", \"fp8\"])"
  type        = list(string)
  default     = []
}

variable "gpus_per_pod" {
  description = "nvidia.com/gpu requested by the SGLang pod"
  type        = number
  default     = 1
}

# Exposure
variable "k8s_namespace" {
  description = "Kubernetes namespace for SGLang"
  type        = string
  default     = "sglang"
}

variable "expose_public" {
  description = "Public Azure Load Balancer (true) or internal-only LB in the VNet (false)"
  type        = bool
  default     = true
}

variable "allowed_cidr_blocks" {
  description = "CIDR blocks allowed to reach the API (LoadBalancer source ranges)"
  type        = list(string)
  default     = ["0.0.0.0/0"] # Restrict for production!
}

# Monitoring
variable "enable_monitoring" {
  description = "Enable Log Analytics + Container Insights"
  type        = bool
  default     = true
}

variable "log_retention_days" {
  description = "Log Analytics retention in days"
  type        = number
  default     = 30
}
