variable "aws_region" {
  description = "AWS region"
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
  default     = "dev"
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

# Networking
variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "az_count" {
  description = "Number of availability zones to span (EKS needs at least 2)"
  type        = number
  default     = 2
}

variable "single_nat_gateway" {
  description = "Use one shared NAT gateway (cheaper) instead of one per AZ"
  type        = bool
  default     = true
}

# Cluster
variable "kubernetes_version" {
  description = "EKS Kubernetes version"
  type        = string
  default     = "1.32"
}

variable "cluster_endpoint_public_access_cidrs" {
  description = "CIDRs allowed to reach the public Kubernetes API endpoint. Restrict to your IP(s)."
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "system_node_instance_types" {
  description = "Instance types for the CPU system node group"
  type        = list(string)
  default     = ["t3.medium"]
}

variable "system_node_count" {
  description = "Desired number of system nodes"
  type        = number
  default     = 2
}

# GPU node group
variable "gpu_instance_type" {
  description = "GPU instance type. g5.xlarge = 1x A10G 24GB (supports bf16). g4dn.xlarge = 1x T4 16GB (no bf16)."
  type        = string
  default     = "g5.xlarge"

  validation {
    condition     = can(regex("^(g4dn|g5|g6|g6e|p3|p4d|p5)\\.", var.gpu_instance_type))
    error_message = "gpu_instance_type must be a GPU instance (g4dn, g5, g6, g6e, p3, p4d, p5 family)."
  }
}

variable "gpu_node_min_count" {
  description = "Minimum GPU nodes"
  type        = number
  default     = 1
}

variable "gpu_node_desired_count" {
  description = "Initial desired GPU nodes (changes after creation are ignored by the module; scale with an autoscaler or the console)"
  type        = number
  default     = 1
}

variable "gpu_node_max_count" {
  description = "Maximum GPU nodes"
  type        = number
  default     = 2
}

variable "gpu_use_spot" {
  description = "Use Spot capacity for GPU nodes (cheaper, can be interrupted)"
  type        = bool
  default     = false
}

variable "gpu_disk_size_gb" {
  description = "Root volume size for GPU nodes (holds the vLLM image, ~10+ GB)"
  type        = number
  default     = 100
}
