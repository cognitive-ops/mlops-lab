output "cluster_name" {
  description = "EKS cluster name"
  value       = module.eks.cluster_name
}

output "cluster_endpoint" {
  description = "EKS API server endpoint"
  value       = module.eks.cluster_endpoint
}

output "vpc_id" {
  description = "VPC ID"
  value       = module.vpc.vpc_id
}

output "configure_kubectl" {
  description = "Command to point kubectl at the cluster"
  value       = "aws eks update-kubeconfig --region ${var.aws_region} --name ${module.eks.cluster_name}"
}

output "deploy_vllm" {
  description = "Command to deploy vLLM"
  value       = "kubectl apply -k k8s/"
}

output "get_endpoint" {
  description = "Command to read the load balancer hostname once deployed"
  value       = "kubectl -n vllm get svc vllm -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'"
}
