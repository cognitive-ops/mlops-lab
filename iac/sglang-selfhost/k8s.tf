locals {
  sglang_labels = {
    app = "sglang"
  }

  sglang_args = concat(
    [
      "python3", "-m", "sglang.launch_server",
      "--model-path", var.model_repo,
      "--served-model-name", var.model_name,
      "--host", "0.0.0.0",
      "--port", tostring(var.sglang_port),
      "--context-length", tostring(var.sglang_context_length),
      "--mem-fraction-static", tostring(var.sglang_mem_fraction_static),
      "--tp-size", tostring(var.sglang_tp_size),
    ],
    var.sglang_tool_call_parser != "" ? ["--tool-call-parser", var.sglang_tool_call_parser] : [],
    var.sglang_extra_args
  )

  gpu_tolerations = concat(
    [{ key = "sku", value = "gpu", effect = "NoSchedule" }],
    var.gpu_use_spot ? [{ key = "kubernetes.azure.com/scalesetpriority", value = "spot", effect = "NoSchedule" }] : []
  )
}

resource "kubernetes_namespace_v1" "sglang" {
  metadata {
    name = var.k8s_namespace
  }

  depends_on = [azurerm_kubernetes_cluster_node_pool.gpu]
}

# NVIDIA device plugin: advertises nvidia.com/gpu on GPU nodes.
resource "kubernetes_daemon_set_v1" "nvidia_device_plugin" {
  metadata {
    name      = "nvidia-device-plugin"
    namespace = "kube-system"
  }

  spec {
    selector {
      match_labels = {
        name = "nvidia-device-plugin"
      }
    }

    strategy {
      type = "RollingUpdate"
    }

    template {
      metadata {
        labels = {
          name = "nvidia-device-plugin"
        }
      }

      spec {
        priority_class_name = "system-node-critical"

        dynamic "toleration" {
          for_each = local.gpu_tolerations
          content {
            key      = toleration.value.key
            operator = "Equal"
            value    = toleration.value.value
            effect   = toleration.value.effect
          }
        }

        toleration {
          key      = "CriticalAddonsOnly"
          operator = "Exists"
        }

        container {
          name  = "nvidia-device-plugin-ctr"
          image = "nvcr.io/nvidia/k8s-device-plugin:v0.17.0"

          env {
            name  = "FAIL_ON_INIT_ERROR"
            value = "false"
          }

          security_context {
            allow_privilege_escalation = false
            capabilities {
              drop = ["ALL"]
            }
          }

          volume_mount {
            name       = "device-plugin"
            mount_path = "/var/lib/kubelet/device-plugins"
          }
        }

        volume {
          name = "device-plugin"
          host_path {
            path = "/var/lib/kubelet/device-plugins"
          }
        }

        # Only run on GPU pool nodes
        node_selector = {
          workload = "llm-inference"
        }
      }
    }
  }

  depends_on = [azurerm_kubernetes_cluster_node_pool.gpu]
}

resource "kubernetes_secret_v1" "hf_token" {
  metadata {
    name      = "hf-token"
    namespace = kubernetes_namespace_v1.sglang.metadata[0].name
  }

  data = {
    HF_TOKEN = var.hf_token
  }
}

# Persistent HF cache so pod restarts don't re-download the model.
resource "kubernetes_persistent_volume_claim_v1" "model_cache" {
  metadata {
    name      = "model-cache"
    namespace = kubernetes_namespace_v1.sglang.metadata[0].name
  }

  spec {
    access_modes       = ["ReadWriteOnce"]
    storage_class_name = "managed-csi"

    resources {
      requests = {
        storage = "${var.model_cache_size_gb}Gi"
      }
    }
  }

  # managed-csi uses WaitForFirstConsumer: PVC binds once the pod schedules.
  wait_until_bound = false
}

resource "kubernetes_deployment_v1" "sglang" {
  metadata {
    name      = "sglang"
    namespace = kubernetes_namespace_v1.sglang.metadata[0].name
    labels    = local.sglang_labels
  }

  spec {
    replicas = 1

    # RWO disk + single GPU: old pod must release both before new starts.
    strategy {
      type = "Recreate"
    }

    selector {
      match_labels = local.sglang_labels
    }

    template {
      metadata {
        labels = local.sglang_labels
      }

      spec {
        node_selector = {
          workload = "llm-inference"
        }

        dynamic "toleration" {
          for_each = local.gpu_tolerations
          content {
            key      = toleration.value.key
            operator = "Equal"
            value    = toleration.value.value
            effect   = toleration.value.effect
          }
        }

        container {
          name              = "sglang"
          image             = var.sglang_image
          image_pull_policy = "IfNotPresent"
          command           = local.sglang_args

          port {
            name           = "http"
            container_port = var.sglang_port
          }

          env {
            name = "HF_TOKEN"
            value_from {
              secret_key_ref {
                name     = kubernetes_secret_v1.hf_token.metadata[0].name
                key      = "HF_TOKEN"
                optional = true
              }
            }
          }

          env {
            name  = "HF_HOME"
            value = "/root/.cache/huggingface"
          }

          resources {
            limits = {
              "nvidia.com/gpu" = tostring(var.gpus_per_pod)
            }
            requests = {
              "nvidia.com/gpu" = tostring(var.gpus_per_pod)
            }
          }

          volume_mount {
            name       = "model-cache"
            mount_path = "/root/.cache/huggingface"
          }

          volume_mount {
            name       = "dshm"
            mount_path = "/dev/shm"
          }

          # Model download + load can take 10+ min on first start.
          startup_probe {
            http_get {
              path = "/health"
              port = var.sglang_port
            }
            period_seconds    = 15
            failure_threshold = 80
            timeout_seconds   = 5
          }

          readiness_probe {
            http_get {
              path = "/health"
              port = var.sglang_port
            }
            period_seconds    = 10
            failure_threshold = 3
            timeout_seconds   = 5
          }

          liveness_probe {
            http_get {
              path = "/health"
              port = var.sglang_port
            }
            period_seconds    = 30
            failure_threshold = 5
            timeout_seconds   = 10
          }
        }

        volume {
          name = "model-cache"
          persistent_volume_claim {
            claim_name = kubernetes_persistent_volume_claim_v1.model_cache.metadata[0].name
          }
        }

        volume {
          name = "dshm"
          empty_dir {
            medium     = "Memory"
            size_limit = "16Gi"
          }
        }
      }
    }
  }

  # PVC uses WaitForFirstConsumer; don't block on rollout so apply can't deadlock
  # while the first model download is running.
  wait_for_rollout = false

  depends_on = [kubernetes_daemon_set_v1.nvidia_device_plugin]
}

resource "kubernetes_service_v1" "sglang" {
  metadata {
    name      = "sglang"
    namespace = kubernetes_namespace_v1.sglang.metadata[0].name
    labels    = local.sglang_labels

    annotations = var.expose_public ? {} : {
      "service.beta.kubernetes.io/azure-load-balancer-internal" = "true"
    }
  }

  spec {
    type                        = "LoadBalancer"
    selector                    = local.sglang_labels
    load_balancer_source_ranges = var.allowed_cidr_blocks

    port {
      name        = "http"
      port        = 80
      target_port = var.sglang_port
    }
  }

  wait_for_load_balancer = true
}
