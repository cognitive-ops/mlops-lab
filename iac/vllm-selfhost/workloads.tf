locals {
  model_name_part = element(reverse(split("/", var.model_repo)), 0)
  model_s3_prefix = "models/${local.model_name_part}"
  model_s3_uri    = "s3://${aws_s3_bucket.models.id}/${local.model_s3_prefix}"
  api_url         = local.use_tls ? "https://${var.domain_name}" : "http://${aws_lb.api.dns_name}"
}

# --- Karpenter NodePools (baseline on-demand + burst spot) -------------------
resource "helm_release" "karpenter_resources" {
  name      = "karpenter-resources"
  namespace = "kube-system"
  chart     = "${path.module}/charts/karpenter-resources"
  wait      = true
  timeout   = 300

  values = [yamlencode({
    clusterName      = module.eks.cluster_name
    nodeRoleName     = module.karpenter.node_iam_role_name
    amiAlias         = var.gpu_ami_alias
    diskSizeGb       = var.gpu_node_disk_size_gb
    instanceFamily   = var.gpu_instance_family
    instanceSizes    = var.gpu_instance_sizes
    baselineGpuLimit = var.gpu_baseline_count
    burstGpuLimit    = max(var.gpu_max_count - var.gpu_baseline_count, 0)
    burstCapacity    = var.gpu_burst_capacity_types
  })]

  depends_on = [helm_release.karpenter]
}

# --- One-off model mirror: Hugging Face -> S3 (Helm hook job) ---------------
resource "helm_release" "model_sync" {
  count = var.model_source == "s3" ? 1 : 0

  name      = "model-sync"
  namespace = kubernetes_namespace_v1.llm.metadata[0].name
  chart     = "${path.module}/charts/model-sync"
  wait      = true
  timeout   = 3600

  values = [yamlencode({
    region   = var.aws_region
    bucket   = aws_s3_bucket.models.id
    prefix   = local.model_s3_prefix
    hfRepo   = var.model_repo
    revision = var.model_revision
  })]

  set_sensitive {
    name  = "hfToken"
    value = var.hf_token
  }

  depends_on = [module.model_sync_pod_identity, module.eks]
}

# --- Serving stack: vLLM + router + LiteLLM + autoscaling + monitoring -------
resource "helm_release" "llm_serving" {
  name      = "llm-serving"
  namespace = kubernetes_namespace_v1.llm.metadata[0].name
  chart     = "${path.module}/charts/llm-serving"
  wait      = true
  timeout   = 1800

  values = [yamlencode({
    region     = var.aws_region
    vpcCidr    = var.vpc_cidr
    secretName = aws_secretsmanager_secret.gateway.name

    model = {
      servedName           = var.model_served_name
      source               = var.model_source
      path                 = var.model_source == "s3" ? local.model_s3_uri : var.model_repo
      quantization         = var.vllm_quantization
      kvCacheDtype         = var.vllm_kv_cache_dtype
      maxModelLen          = var.vllm_max_model_len
      maxNumSeqs           = var.vllm_max_num_seqs
      gpuMemoryUtilization = var.vllm_gpu_memory_utilization
      toolCallParser       = var.vllm_tool_call_parser
      enforceEager         = var.vllm_enforce_eager
      extraArgs            = var.vllm_extra_args
    }

    vllm = {
      image                = var.vllm_image
      minReplicas          = var.gpu_baseline_count
      maxReplicas          = var.gpu_max_count
      targetConcurrency    = var.vllm_target_concurrency_per_replica
      targetKvCacheUsage   = var.vllm_target_kv_cache_usage
      prometheusServerAddr = "http://kube-prometheus-stack-prometheus.monitoring.svc:9090"
    }

    lmcache = {
      enabled   = var.lmcache_enabled
      image     = var.lmcache_image
      cpuSizeGb = var.lmcache_cpu_size_gb
      podMemory = var.lmcache_pod_memory
    }

    router = {
      image        = var.router_image
      replicas     = var.router_replicas
      routingLogic = var.router_routing_logic
    }

    litellm = {
      image            = var.litellm_image
      minReplicas      = var.litellm_min_replicas
      maxReplicas      = var.litellm_max_replicas
      maxRequestSizeMb = var.litellm_max_request_size_mb
    }

    edge = {
      targetGroupArn = aws_lb_target_group.gateway.arn
    }
  })]

  depends_on = [
    helm_release.karpenter_resources,
    helm_release.keda,
    helm_release.external_secrets,
    helm_release.aws_load_balancer_controller,
    helm_release.kube_prometheus_stack,
    helm_release.nvidia_device_plugin,
    helm_release.model_sync,
    module.vllm_pod_identity,
    aws_secretsmanager_secret_version.gateway,
    aws_vpc_security_group_ingress_rule.nodes_from_alb,
  ]
}
