locals {
  common_tags = merge({
    Project     = var.project_name
    Environment = var.environment
    Owner       = var.owner
    ManagedBy   = "Terraform"
  }, var.tags)
}

resource "azurerm_resource_group" "main" {
  name     = "${var.project_name}-rg"
  location = var.location
  tags     = local.common_tags
}

resource "azurerm_kubernetes_cluster" "main" {
  name                = "${var.project_name}-aks"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  dns_prefix          = var.project_name
  kubernetes_version  = var.kubernetes_version
  tags                = local.common_tags

  # CPU pool for system pods only; GPU pool is separate and tainted.
  default_node_pool {
    name                         = "system"
    vm_size                      = var.system_node_vm_size
    node_count                   = var.system_node_count
    only_critical_addons_enabled = true
    os_disk_size_gb              = 64
  }

  identity {
    type = "SystemAssigned"
  }

  network_profile {
    network_plugin      = "azure"
    network_plugin_mode = "overlay"
    load_balancer_sku   = "standard"
  }

  dynamic "oms_agent" {
    for_each = var.enable_monitoring ? [1] : []
    content {
      log_analytics_workspace_id = azurerm_log_analytics_workspace.main[0].id
    }
  }
}

# GPU node pool. AKS Ubuntu images install the NVIDIA driver and container
# runtime on N-series VMs automatically; the device plugin DaemonSet (k8s.tf)
# exposes nvidia.com/gpu to the scheduler.
resource "azurerm_kubernetes_cluster_node_pool" "gpu" {
  name                  = "gpu"
  kubernetes_cluster_id = azurerm_kubernetes_cluster.main.id
  vm_size               = var.gpu_vm_size
  os_disk_size_gb       = var.gpu_os_disk_size_gb
  os_type               = "Linux"
  mode                  = "User"
  tags                  = local.common_tags

  auto_scaling_enabled = true
  min_count            = var.gpu_node_min_count
  max_count            = var.gpu_node_count

  priority        = var.gpu_use_spot ? "Spot" : "Regular"
  eviction_policy = var.gpu_use_spot ? "Delete" : null
  spot_max_price  = var.gpu_use_spot ? -1 : null

  node_labels = {
    workload = "llm-inference"
  }

  # Keep non-GPU pods off expensive nodes
  node_taints = concat(
    ["sku=gpu:NoSchedule"],
    var.gpu_use_spot ? ["kubernetes.azure.com/scalesetpriority=spot:NoSchedule"] : []
  )

  lifecycle {
    ignore_changes = [node_count]
  }
}
