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
  description = "Max GPU nodes (autoscaler upper bound)"
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
