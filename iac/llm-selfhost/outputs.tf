# EC2 Instance ID
output "instance_id" {
  description = "EC2 instance ID"
  value       = aws_instance.llm.id
}

# EC2 Instance Private IP
output "instance_private_ip" {
  description = "EC2 instance private IP address"
  value       = aws_instance.llm.private_ip
}

# Elastic IP
output "instance_public_ip" {
  description = "Elastic IP address of the instance"
  value       = aws_eip.llm.public_ip
}

# SSH Connection Instructions
output "ssh_command" {
  description = "Command to SSH into the instance"
  value       = "ssh -i ~/.ssh/${aws_key_pair.main.key_name}.pem ubuntu@${aws_eip.llm.public_ip}"
}

# SSH Key Location
output "ssh_key_path" {
  description = "Path to the SSH private key"
  value       = local_file.private_key.filename
}

# Load Balancer DNS
output "load_balancer_dns" {
  description = "DNS name of the load balancer"
  value       = var.enable_alb ? aws_lb.main[0].dns_name : null
}

# Load Balancer URL
output "api_endpoint" {
  description = "vLLM API endpoint URL"
  value       = var.enable_alb ? "http://${aws_lb.main[0].dns_name}" : "http://${aws_eip.llm.public_ip}:${var.vllm_port}"
}

# S3 Bucket Name
output "s3_bucket_name" {
  description = "S3 bucket for model artifacts and logs"
  value       = var.enable_s3_bucket ? aws_s3_bucket.artifacts[0].id : null
}

# VPC ID
output "vpc_id" {
  description = "VPC ID"
  value       = aws_vpc.main.id
}

# Subnet ID
output "subnet_id" {
  description = "Public subnet ID"
  value       = aws_subnet.public.id
}

# CloudWatch Log Group
output "log_group_name" {
  description = "CloudWatch log group for vLLM"
  value       = var.enable_cloudwatch_monitoring ? aws_cloudwatch_log_group.vllm[0].name : null
}

# Model Storage Volume
output "model_volume_id" {
  description = "EBS volume ID for model storage"
  value       = aws_ebs_volume.model_storage.id
}

# Security Group IDs
output "instance_security_group_id" {
  description = "Security group ID for EC2 instance"
  value       = aws_security_group.llm_instance.id
}

output "alb_security_group_id" {
  description = "Security group ID for load balancer"
  value       = aws_security_group.alb.id
}

# Instance Type Used
output "instance_type" {
  description = "EC2 instance type"
  value       = aws_instance.llm.instance_type
}

# Model Information
output "model_name" {
  description = "Model name being served"
  value       = var.model_name
}

output "model_repo" {
  description = "HuggingFace model repository"
  value       = var.model_repo
}

# Quick Access Information
output "quick_start_guide" {
  description = "Quick start guide"
  value       = <<-EOT
    
    1. SSH into the instance:
       ${var.enable_alb ? "ssh -i ~/.ssh/${aws_key_pair.main.key_name}.pem ubuntu@${aws_eip.llm.public_ip}" : ""}

    2. Check vLLM status:
       sudo systemctl status vllm
       
    3. View logs:
       sudo journalctl -u vllm -f

    4. Test the API:
       curl http://${var.enable_alb ? aws_lb.main[0].dns_name : aws_eip.llm.public_ip}${var.enable_alb ? "" : ":${var.vllm_port}"}/v1/models

    5. Make a completion request:
       curl -X POST http://${var.enable_alb ? aws_lb.main[0].dns_name : aws_eip.llm.public_ip}${var.enable_alb ? "" : ":${var.vllm_port}"}/v1/completions \
         -H "Content-Type: application/json" \
         -d '{"model": "${var.model_name}", "prompt": "Hello, world!", "max_tokens": 100}'

    Model Storage: /mnt/models
    S3 Bucket: ${var.enable_s3_bucket ? aws_s3_bucket.artifacts[0].id : "Not created"}
  EOT
}
