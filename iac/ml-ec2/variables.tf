variable "aws_region" {
  description = "The AWS region to deploy resources in"
  type        = string
  default     = "us-east-1"  
}

variable "instance_type" {
  description = "The type of EC2 instance to create"
  type        = string
  default     = "p3.2xlarge"
}

variable "ami_id" {
  description = "The AMI ID to use for the EC2 instance"
  type        = string
}

variable "subnet_id" {
  description = "The subnet ID where the EC2 instance will be launched"
  type        = string
}

variable "vpc_id" {
  description = "The VPC ID where the security group will be created"
  type        = string  
}

variable "private_key_path" {
  description = "The local path to the private key file for SSH access"
  type        = string  
  default     = "ssh-keys/ssh-key.pem"
}

variable "project" {
  description = "Project name for tagging resources"
  type        = string
  default     = "scopic-mlops"  
}

variable "owner" {
  description = "Owner name for tagging resources"
  type        = string
  default     = "scopic"
}

