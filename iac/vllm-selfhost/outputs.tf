output "cluster_name" {
  description = "EKS cluster name"
  value       = module.eks.cluster_name
}

output "configure_kubectl" {
  description = "Point kubectl at the cluster"
  value       = "aws eks update-kubeconfig --region ${var.aws_region} --name ${module.eks.cluster_name}"
}

output "api_url" {
  description = "Public base URL of the OpenAI-compatible API (append /v1)"
  value       = local.api_url
}

output "api_base_url" {
  description = "Value for OpenAI SDK base_url"
  value       = "${local.api_url}/v1"
}

output "alb_dns_name" {
  description = "ALB DNS name"
  value       = aws_lb.api.dns_name
}

output "tls_enabled" {
  description = "False means the API is served over plain HTTP (no domain_name set). Do not use for real traffic."
  value       = local.use_tls
}

output "model_bucket" {
  description = "S3 bucket holding model weights"
  value       = aws_s3_bucket.models.id
}

output "model_s3_uri" {
  description = "S3 location vLLM streams the model from"
  value       = local.model_s3_uri
}

output "ecr_repository_url" {
  description = "ECR repository for the mirrored vLLM image (see scripts/mirror-image.sh)"
  value       = aws_ecr_repository.vllm.repository_url
}

output "gateway_secret_name" {
  description = "Secrets Manager secret holding the LiteLLM master key, DB and Redis URLs"
  value       = aws_secretsmanager_secret.gateway.name
}

output "get_master_key" {
  description = "Command that prints the LiteLLM master key (admin only; never hand it to agents)"
  value       = "aws secretsmanager get-secret-value --region ${var.aws_region} --secret-id ${aws_secretsmanager_secret.gateway.name} --query SecretString --output text | jq -r .LITELLM_MASTER_KEY"
}

output "alarm_topic_arn" {
  description = "SNS topic for CloudWatch alarms"
  value       = aws_sns_topic.alarms.arn
}

output "grafana_port_forward" {
  description = "Open Grafana locally (user: admin; password in secret monitoring/grafana-admin)"
  value       = "kubectl -n monitoring port-forward svc/kube-prometheus-stack-grafana 3000:80"
}
