# ---------------------------------------------------------------------------
# EKS Pod Identity roles for platform controllers and workloads
# ---------------------------------------------------------------------------
module "lb_controller_pod_identity" {
  source  = "terraform-aws-modules/eks-pod-identity/aws"
  version = "~> 1.12"

  name = "${local.name}-lb-controller"

  attach_aws_lb_controller_policy = true

  associations = {
    lb_controller = {
      cluster_name    = module.eks.cluster_name
      namespace       = "kube-system"
      service_account = "aws-load-balancer-controller"
    }
  }
}

module "external_secrets_pod_identity" {
  source  = "terraform-aws-modules/eks-pod-identity/aws"
  version = "~> 1.12"

  name = "${local.name}-external-secrets"

  attach_external_secrets_policy        = true
  external_secrets_secrets_manager_arns = [aws_secretsmanager_secret.gateway.arn]
  external_secrets_kms_key_arns         = [aws_kms_key.data.arn]
  external_secrets_create_permission    = false

  associations = {
    external_secrets = {
      cluster_name    = module.eks.cluster_name
      namespace       = "external-secrets"
      service_account = "external-secrets"
    }
  }
}

# vLLM pods stream weights from S3 (read-only).
module "vllm_pod_identity" {
  source  = "terraform-aws-modules/eks-pod-identity/aws"
  version = "~> 1.12"

  name = "${local.name}-vllm"

  attach_custom_policy = true
  policy_statements = [
    {
      sid       = "ReadModels"
      actions   = ["s3:GetObject", "s3:ListBucket", "s3:GetBucketLocation"]
      resources = [aws_s3_bucket.models.arn, "${aws_s3_bucket.models.arn}/*"]
    },
    {
      sid       = "DecryptModels"
      actions   = ["kms:Decrypt"]
      resources = [aws_kms_key.data.arn]
    },
  ]

  associations = {
    vllm = {
      cluster_name    = module.eks.cluster_name
      namespace       = local.llm_ns
      service_account = "vllm"
    }
  }
}

# The model-sync job mirrors Hugging Face weights into S3 (write access).
module "model_sync_pod_identity" {
  source  = "terraform-aws-modules/eks-pod-identity/aws"
  version = "~> 1.12"

  name = "${local.name}-model-sync"

  attach_custom_policy = true
  policy_statements = [
    {
      sid       = "WriteModels"
      actions   = ["s3:GetObject", "s3:PutObject", "s3:ListBucket", "s3:GetBucketLocation", "s3:AbortMultipartUpload"]
      resources = [aws_s3_bucket.models.arn, "${aws_s3_bucket.models.arn}/*"]
    },
    {
      sid       = "UseModelsKey"
      actions   = ["kms:Decrypt", "kms:GenerateDataKey"]
      resources = [aws_kms_key.data.arn]
    },
  ]

  associations = {
    model_sync = {
      cluster_name    = module.eks.cluster_name
      namespace       = local.llm_ns
      service_account = "model-sync"
    }
  }
}

# ---------------------------------------------------------------------------
# Namespaces and storage
# ---------------------------------------------------------------------------
resource "kubernetes_namespace_v1" "llm" {
  metadata {
    name = local.llm_ns

    labels = {
      # Lets the LB controller inject ALB target-health readiness gates so
      # rollouts never drop traffic.
      "elbv2.k8s.aws/pod-readiness-gate-inject" = "enabled"
      "pod-security.kubernetes.io/enforce"      = "baseline"
    }
  }

  depends_on = [module.eks]
}

resource "kubernetes_namespace_v1" "monitoring" {
  metadata {
    name = "monitoring"
  }

  depends_on = [module.eks]
}

resource "kubernetes_storage_class_v1" "gp3" {
  metadata {
    name = "gp3"
  }

  storage_provisioner    = "ebs.csi.aws.com"
  volume_binding_mode    = "WaitForFirstConsumer"
  allow_volume_expansion = true
  reclaim_policy         = "Delete"

  parameters = {
    type      = "gp3"
    encrypted = "true"
  }

  depends_on = [module.eks]
}

resource "random_password" "grafana" {
  length  = 24
  special = false
}

resource "kubernetes_secret_v1" "grafana_admin" {
  metadata {
    name      = "grafana-admin"
    namespace = kubernetes_namespace_v1.monitoring.metadata[0].name
  }

  data = {
    admin-user     = "admin"
    admin-password = random_password.grafana.result
  }
}

# ---------------------------------------------------------------------------
# Platform controllers (Helm)
# ---------------------------------------------------------------------------
resource "helm_release" "karpenter" {
  name       = "karpenter"
  namespace  = "kube-system"
  repository = "oci://public.ecr.aws/karpenter"
  chart      = "karpenter"
  version    = "1.15.0"
  wait       = true
  timeout    = 600

  values = [yamlencode({
    replicas = 2
    settings = {
      clusterName       = module.eks.cluster_name
      interruptionQueue = module.karpenter.queue_name
    }
    serviceAccount = {
      name = module.karpenter.service_account
    }
    controller = {
      resources = {
        requests = { cpu = "1", memory = "1Gi" }
        limits   = { memory = "1Gi" }
      }
    }
  })]

  depends_on = [module.karpenter]
}

resource "helm_release" "aws_load_balancer_controller" {
  name       = "aws-load-balancer-controller"
  namespace  = "kube-system"
  repository = "https://aws.github.io/eks-charts"
  chart      = "aws-load-balancer-controller"
  version    = "3.6.0"
  wait       = true
  timeout    = 600

  values = [yamlencode({
    clusterName  = module.eks.cluster_name
    region       = var.aws_region
    vpcId        = module.vpc.vpc_id
    replicaCount = 2
    serviceAccount = {
      create = true
      name   = "aws-load-balancer-controller"
    }
  })]

  depends_on = [module.lb_controller_pod_identity, module.eks]
}

resource "helm_release" "keda" {
  name             = "keda"
  namespace        = "keda"
  create_namespace = true
  repository       = "https://kedacore.github.io/charts"
  chart            = "keda"
  version          = "2.21.0"
  wait             = true
  timeout          = 600

  depends_on = [module.eks]
}

resource "helm_release" "external_secrets" {
  name             = "external-secrets"
  namespace        = "external-secrets"
  create_namespace = true
  repository       = "https://charts.external-secrets.io"
  chart            = "external-secrets"
  version          = "2.13.0"
  wait             = true
  timeout          = 600

  values = [yamlencode({
    installCRDs = true
    serviceAccount = {
      create = true
      name   = "external-secrets"
    }
  })]

  depends_on = [module.external_secrets_pod_identity, module.eks]
}

resource "helm_release" "kube_prometheus_stack" {
  name       = "kube-prometheus-stack"
  namespace  = kubernetes_namespace_v1.monitoring.metadata[0].name
  repository = "https://prometheus-community.github.io/helm-charts"
  chart      = "kube-prometheus-stack"
  version    = "92.10.1"
  wait       = true
  timeout    = 900

  values = [yamlencode({
    prometheus = {
      prometheusSpec = {
        replicas  = 2
        retention = "15d"
        # Discover ServiceMonitors/PodMonitors/rules from every namespace and chart.
        serviceMonitorSelectorNilUsesHelmValues = false
        podMonitorSelectorNilUsesHelmValues     = false
        ruleSelectorNilUsesHelmValues           = false
        resources = {
          requests = { cpu = "500m", memory = "2Gi" }
          limits   = { memory = "4Gi" }
        }
        storageSpec = {
          volumeClaimTemplate = {
            spec = {
              storageClassName = kubernetes_storage_class_v1.gp3.metadata[0].name
              accessModes      = ["ReadWriteOnce"]
              resources        = { requests = { storage = "${var.monitoring_storage_gb}Gi" } }
            }
          }
        }
      }
    }
    grafana = {
      admin = {
        existingSecret = kubernetes_secret_v1.grafana_admin.metadata[0].name
        userKey        = "admin-user"
        passwordKey    = "admin-password"
      }
      sidecar = {
        dashboards = {
          enabled         = true
          label           = "grafana_dashboard"
          searchNamespace = "ALL"
        }
      }
    }
  })]

  depends_on = [kubernetes_storage_class_v1.gp3, module.eks]
}

# Registers nvidia.com/gpu with the kubelet. The EKS-accelerated AL2023 AMI
# already ships the driver and container runtime.
resource "helm_release" "nvidia_device_plugin" {
  name       = "nvidia-device-plugin"
  namespace  = "kube-system"
  repository = "https://nvidia.github.io/k8s-device-plugin"
  chart      = "nvidia-device-plugin"
  version    = "0.20.1"
  wait       = false

  values = [yamlencode({
    # No NFD/GFD here, so drop the default feature-label affinity and select by pool label.
    affinity     = null
    nodeSelector = { workload = "llm-inference" }
    tolerations = [
      { key = "sku", operator = "Equal", value = "gpu", effect = "NoSchedule" },
    ]
  })]

  depends_on = [module.eks]
}

resource "helm_release" "dcgm_exporter" {
  name       = "dcgm-exporter"
  namespace  = "kube-system"
  repository = "https://nvidia.github.io/dcgm-exporter/helm-charts"
  chart      = "dcgm-exporter"
  version    = "4.8.4"
  wait       = false

  values = [yamlencode({
    nodeSelector = { workload = "llm-inference" }
    tolerations = [
      { key = "sku", operator = "Equal", value = "gpu", effect = "NoSchedule" },
    ]
    serviceMonitor = { enabled = true }
  })]

  depends_on = [helm_release.kube_prometheus_stack]
}
