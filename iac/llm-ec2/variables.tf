# AWS Region
variable "aws_region" {
  description = "AWS region for resource deployment"
  type        = string
  default     = "us-east-1"
}

# Project Configuration
variable "project_name" {
  description = "Name of the project"
  type        = string
  default     = "llm-server"
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

# Networking
variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "subnet_cidr" {
  description = "CIDR block for public subnet"
  type        = string
  default     = "10.0.1.0/24"
}

variable "enabled_nat_gateway" {
  description = "Enable NAT Gateway for private subnets"
  type        = bool
  default     = false
}

# EC2 Instance Configuration
variable "instance_type" {
  description = "EC2 instance type (GPU instances recommended: g4dn.xlarge, g4dn.2xlarge, p3.2xlarge)"
  type        = string
  default     = "g4dn.xlarge" # 1x NVIDIA T4 GPU
  
  validation {
    condition     = can(regex("^(g4dn|p3|p4d|g5)\\.", var.instance_type))
    error_message = "Instance type must be a GPU instance (g4dn, p3, p4d, g5 family)."
  }
}

variable "ami_id" {
  description = "AMI ID for Ubuntu 22.04 LTS (update per region). Use Ubuntu for NVIDIA driver support."
  type        = string
  default     = "" # User must provide their regional AMI
}

variable "root_volume_size" {
  description = "Root volume size in GB"
  type        = number
  default     = 100
}

variable "model_volume_size" {
  description = "Additional EBS volume size for model storage in GB"
  type        = number
  default     = 200
}

# Model Configuration
variable "model_name" {
  description = "Name of the model to self-host (e.g., mistral-7b, llama2-7b)"
  type        = string
  default     = "mistral-7b"
}

variable "model_repo" {
  description = "HuggingFace model repository ID"
  type        = string
  default     = "mistralai/Mistral-7B-v0.1"
}

variable "model_size_gb" {
  description = "Approximate model size in GB"
  type        = number
  default     = 14
}

# API Configuration
variable "vllm_port" {
  description = "Port for vLLM API"
  type        = number
  default     = 8000
}

variable "vllm_max_model_len" {
  description = "Maximum sequence length for the model"
  type        = number
  default     = 4096
}

variable "vllm_gpu_memory_utilization" {
  description = "GPU memory utilization (0.0 to 1.0)"
  type        = number
  default     = 0.9
}

variable "vllm_version" {
  description = "vLLM version to pin in the venv. Empty string installs the latest release."
  type        = string
  default     = ""
}

variable "nvidia_driver_version" {
  description = "NVIDIA driver branch to install (e.g. \"550\"). Empty string lets ubuntu-drivers pick the recommended driver."
  type        = string
  default     = ""
}

variable "hf_token" {
  description = "Hugging Face access token, required for gated model repos (e.g. Meta Llama). Leave empty for ungated models."
  type        = string
  default     = ""
  sensitive   = true
}

# Load Balancer Configuration
variable "enable_alb" {
  description = "Enable Application Load Balancer"
  type        = bool
  default     = true
}

variable "health_check_path" {
  description = "Health check endpoint path"
  type        = string
  default     = "/v1/models"
}

variable "health_check_interval" {
  description = "Health check interval in seconds"
  type        = number
  default     = 30
}

variable "health_check_timeout" {
  description = "Health check timeout in seconds"
  type        = number
  default     = 5
}

# Security Configuration
variable "allow_public_access" {
  description = "Allow public access to the API"
  type        = bool
  default     = true
}

variable "allowed_cidr_blocks" {
  description = "CIDR blocks allowed to access the API"
  type        = list(string)
  default     = ["0.0.0.0/0"] # Change for production!
}

variable "allowed_ssh_cidr_blocks" {
  description = "CIDR blocks allowed for SSH access"
  type        = list(string)
  default     = ["0.0.0.0/0"] # Change for production!
}

# S3 Configuration
variable "enable_s3_bucket" {
  description = "Create S3 bucket for model artifacts and logs"
  type        = bool
  default     = true
}

variable "s3_bucket_name" {
  description = "S3 bucket name (must be globally unique)"
  type        = string
  default     = ""
}

variable "enable_s3_versioning" {
  description = "Enable versioning for S3 bucket"
  type        = bool
  default     = true
}

variable "enable_s3_encryption" {
  description = "Enable encryption for S3 bucket"
  type        = bool
  default     = true
}

# Monitoring Configuration
variable "enable_cloudwatch_monitoring" {
  description = "Enable CloudWatch monitoring and logging"
  type        = bool
  default     = true
}

variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 7
}

# Tagging
variable "tags" {
  description = "Additional tags to apply to resources"
  type        = map(string)
  default     = {}
}
