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

output "next_steps" {
  description = "Deploy SGLang with the manifests in ./k8s"
  value       = <<-EOT

    1. az aks get-credentials -g ${azurerm_resource_group.main.name} -n ${azurerm_kubernetes_cluster.main.name}
    2. kubectl apply -k k8s/
    3. kubectl -n sglang get pods -w
  EOT
}
