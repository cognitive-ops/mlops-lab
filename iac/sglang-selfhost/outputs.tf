output "resource_group_name" {
  description = "Resource group containing the AKS cluster"
  value       = azurerm_resource_group.main.name
}

output "aks_cluster_name" {
  description = "AKS cluster name"
  value       = azurerm_kubernetes_cluster.main.name
}

output "get_credentials_command" {
  description = "Command to configure kubectl"
  value       = "az aks get-credentials -g ${azurerm_resource_group.main.name} -n ${azurerm_kubernetes_cluster.main.name}"
}

output "gpu_vm_size" {
  description = "GPU VM size in use"
  value       = var.gpu_vm_size
}

output "load_balancer_ip" {
  description = "IP of the SGLang LoadBalancer service (public or internal per expose_public)"
  value       = try(kubernetes_service_v1.sglang.status[0].load_balancer[0].ingress[0].ip, null)
}

output "api_endpoint" {
  description = "SGLang OpenAI-compatible API base URL"
  value       = try("http://${kubernetes_service_v1.sglang.status[0].load_balancer[0].ingress[0].ip}/v1", null)
}

output "model_name" {
  description = "Model name to use in API requests"
  value       = var.model_name
}

output "model_repo" {
  description = "HuggingFace model repository"
  value       = var.model_repo
}

output "quick_start_guide" {
  description = "Quick start guide"
  value       = <<-EOT

    1. Configure kubectl:
       az aks get-credentials -g ${azurerm_resource_group.main.name} -n ${azurerm_kubernetes_cluster.main.name}

    2. Watch pod (first start downloads model, 10-20 min):
       kubectl -n ${var.k8s_namespace} get pods -w
       kubectl -n ${var.k8s_namespace} logs -f deploy/sglang

    3. Verify GPU is visible:
       kubectl describe nodes -l workload=llm-inference | grep -i nvidia.com/gpu

    4. Test API:
       curl http://<load_balancer_ip>/v1/models
       curl http://<load_balancer_ip>/v1/chat/completions \
         -H "Content-Type: application/json" \
         -d '{"model": "${var.model_name}", "messages": [{"role": "user", "content": "Hello!"}], "max_tokens": 100}'

    No public IP / internal LB? Port-forward:
       kubectl -n ${var.k8s_namespace} port-forward svc/sglang 8080:80
  EOT
}
