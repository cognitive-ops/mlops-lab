# SGLang Qwen on AKS (GPU)

Terraform config that deploys a self-hosted Qwen LLM on an Azure Kubernetes Service cluster with a GPU node pool, served by [SGLang](https://github.com/sgl-project/sglang) (OpenAI-compatible API). For a local Docker-only version, see [demo/sglang](../../demo/sglang).

## Architecture

- **AKS cluster**: Azure CNI overlay, system-assigned identity
- **System node pool**: small CPU pool for cluster add-ons (`CriticalAddonsOnly`)
- **GPU node pool**: N-series VMs, autoscaled, tainted `sku=gpu:NoSchedule`, optional Spot. AKS Ubuntu images install the NVIDIA driver automatically
- **NVIDIA device plugin** DaemonSet: exposes `nvidia.com/gpu`
- **SGLang Deployment**: 1 pod, `nvidia.com/gpu` request, `/dev/shm` memory volume, startup/readiness/liveness probes on `/health`
- **PVC (managed-csi)**: persistent HuggingFace cache so restarts don't re-download weights
- **Service type LoadBalancer**: public (or internal) Azure LB on port 80, source-IP restricted
- **Log Analytics + Container Insights** (optional)

## Prerequisites

1. Terraform >= 1.5, Azure CLI (`az login`), `kubectl`
2. Azure subscription with **GPU vCPU quota** in the chosen region (e.g. `standardNCADSA100v4Family`). Check: `az vm list-usage -l eastus -o table | grep -i NC`
3. HuggingFace token only if you serve a gated repo (public Qwen repos need none)

## Choosing a GPU

| Model | VRAM need (bf16) | `gpu_vm_size` |
|-------|------------------|---------------|
| Qwen2.5-3B-Instruct | ~7 GB | `Standard_NC4as_T4_v3` (T4 16GB) |
| Qwen2.5-7B-Instruct (default) | ~16 GB + KV cache | `Standard_NC24ads_A100_v4` (A100 80GB) or `Standard_NV36ads_A10_v5` (A10 24GB) |
| Qwen2.5-14B / 32B | 30 / 65 GB | A100 80GB (32B: add `--quantization fp8` or use 2 GPUs: `Standard_NC48ads_A100_v4`, `gpus_per_pod=2`, `sglang_tp_size=2`) |

## Setup

```bash
cd iac/sglang-selfhost
terraform init
```

`terraform.tfvars`:

```hcl
location       = "eastus"
project_name   = "sglang-qwen"
owner          = "your-name"

gpu_vm_size    = "Standard_NC24ads_A100_v4"
gpu_node_count = 1          # autoscaler max
gpu_node_min_count = 1      # 0 = scale to zero when idle

model_name     = "qwen2.5-7b-instruct"     # name clients send
model_repo     = "Qwen/Qwen2.5-7B-Instruct"
sglang_tool_call_parser = "qwen25"

expose_public       = true
allowed_cidr_blocks = ["203.0.113.4/32"]   # your IP! default is 0.0.0.0/0
```

```bash
export TF_VAR_hf_token="hf_xxx"   # optional
terraform plan -out=tfplan
terraform apply tfplan
```

If the first plan fails because the Kubernetes provider can't reach a not-yet-created cluster:

```bash
terraform apply -target=azurerm_kubernetes_cluster_node_pool.gpu
terraform apply
```

First start: node provisioning (~5-10 min) + image pull + model download. Expect 10-20 min until `/health` is green. `apply` does not wait for the rollout.

## Using the API

```bash
az aks get-credentials -g sglang-qwen-rg -n sglang-qwen-aks
terraform output api_endpoint

curl http://<ip>/v1/models
curl http://<ip>/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen2.5-7b-instruct","messages":[{"role":"user","content":"Hello"}],"max_tokens":100}'
```

Without public access: `kubectl -n sglang port-forward svc/sglang 8080:80`.

## Operations

```bash
kubectl -n sglang get pods -w
kubectl -n sglang logs -f deploy/sglang
kubectl describe nodes -l workload=llm-inference | grep -i nvidia.com/gpu
kubectl -n sglang rollout restart deploy/sglang
```

## Cost notes

GPU node is the cost. A100 (NC24ads_A100_v4) is roughly $3.5-4/hr on-demand; T4 ~$0.5/hr. Levers: `gpu_use_spot = true` (evictable), `gpu_node_min_count = 0` (scale to zero; note: with one replica pinned, the autoscaler only removes the node if you scale the deployment to 0 — `kubectl -n sglang scale deploy/sglang --replicas=0`), smaller model/GPU, or `az aks nodepool stop`-style teardown via `terraform destroy`.

## Cleanup

```bash
terraform destroy
```

Deletes cluster, node pools, disks (including the model cache) and the resource group.

## Troubleshooting

- **Pod `Pending`, `0/N nodes ... Insufficient nvidia.com/gpu`**: device plugin not running or GPU node still provisioning. `kubectl -n kube-system get ds nvidia-device-plugin`; check autoscaler events with `kubectl describe pod`.
- **Node pool create fails `QuotaExceeded` / `SkuNotAvailable`**: request GPU quota or change `location` / `gpu_vm_size`.
- **Pod `CrashLoopBackOff` with CUDA OOM**: lower `sglang_context_length` or `sglang_mem_fraction_static`, or use a bigger GPU / `--quantization fp8` via `sglang_extra_args`.
- **T4 errors on bf16/flashinfer**: T4 (Turing) lacks bf16; add `sglang_extra_args = ["--dtype","half","--attention-backend","triton"]`.
- **Tool calls not parsed**: set `sglang_tool_call_parser` to match the model family (`qwen25` for Qwen2.5/Qwen3).
- **Pod evicted/restarting at startup**: startup probe allows ~20 min; raise `failure_threshold` in [k8s.tf](k8s.tf) for slow downloads.
