# SGLang Qwen on AKS (GPU)

Self-hosted Qwen LLM on Azure Kubernetes Service with a GPU node pool, served by [SGLang](https://github.com/sgl-project/sglang) (OpenAI-compatible API).

- **Terraform** ([*.tf](.)) creates infra only: resource group, AKS, CPU system pool, GPU node pool, Log Analytics.
- **Kubernetes YAML** ([k8s/](k8s)) deploys SGLang: namespace, NVIDIA device plugin, PVC, Deployment, Service.

For a local Docker-only version, see [demo/sglang](../../demo/sglang).

## Architecture

- AKS, Azure CNI overlay, system-assigned identity
- System pool (`CriticalAddonsOnly`) for add-ons
- GPU pool: N-series, autoscaled, tainted `sku=gpu:NoSchedule`, label `workload=llm-inference`, optional Spot. AKS Ubuntu images install the NVIDIA driver automatically
- `k8s/`: device plugin DaemonSet, SGLang Deployment (1 GPU, probes on `/health`, `/dev/shm`), `managed-csi` PVC for HF cache, LoadBalancer Service on port 80

## Prerequisites

1. Terraform >= 1.5, Azure CLI (`az login`), `kubectl`
2. **Enabled** Azure subscription with GPU vCPU quota in the region. Check: `az vm list-usage -l eastus -o table | grep -i NC`
3. HuggingFace token only for gated repos (public Qwen repos need none)

## GPU choice

| Model | VRAM (bf16) | `gpu_vm_size` |
|-------|-------------|---------------|
| Qwen2.5-3B-Instruct | ~7 GB | `Standard_NC4as_T4_v3` (T4 16GB) |
| Qwen2.5-7B-Instruct (default) | ~16 GB + KV | `Standard_NC24ads_A100_v4` (A100 80GB) |
| Qwen2.5-32B | ~65 GB | A100 80GB + `--quantization fp8`, or 2 GPUs (`Standard_NC48ads_A100_v4`, `--tp-size 2`, `nvidia.com/gpu: 2`) |

## 1. Infra (Terraform)

Edit [terraform.tfvars](terraform.tfvars), then:

```bash
cd iac/sglang-selfhost
terraform init
terraform plan -out=tfplan
terraform apply tfplan
```

## 2. Deploy SGLang (kubectl)

```bash
az aks get-credentials -g sglang-qwen-rg -n sglang-qwen-aks

# Optional, gated repos only
kubectl create namespace sglang --dry-run=client -o yaml | kubectl apply -f -
kubectl -n sglang create secret generic hf-token --from-literal=HF_TOKEN=hf_xxx

kubectl apply -k k8s/
kubectl -n sglang get pods -w
kubectl -n sglang logs -f deploy/sglang
```

First start: GPU node provisioning (~5-10 min) + image pull + model download, expect 10-20 min until ready.

Change model/flags by editing [k8s/deployment.yaml](k8s/deployment.yaml) (`--model-path`, `--served-model-name`, `--context-length`, `--tool-call-parser`, ...) and re-applying. **Before applying**, restrict `loadBalancerSourceRanges` in [k8s/service.yaml](k8s/service.yaml) (default `0.0.0.0/0`).

### T4 profile

Set `gpu_vm_size = "Standard_NC4as_T4_v3"` in tfvars; in `deployment.yaml` use `Qwen/Qwen2.5-3B-Instruct` and uncomment `--dtype half --attention-backend triton` (T4 has no bf16).

## Using the API

```bash
IP=$(kubectl -n sglang get svc sglang -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
curl http://$IP/v1/models
curl http://$IP/v1/chat/completions -H "Content-Type: application/json" \
  -d '{"model":"qwen2.5-7b-instruct","messages":[{"role":"user","content":"Hello"}],"max_tokens":100}'
```

No public IP: `kubectl -n sglang port-forward svc/sglang 8080:80`.

## Operations

```bash
kubectl describe nodes -l workload=llm-inference | grep -i nvidia.com/gpu
kubectl -n kube-system get ds nvidia-device-plugin
kubectl -n sglang rollout restart deploy/sglang
kubectl -n sglang scale deploy/sglang --replicas=0   # frees GPU; with gpu_node_min_count=0 node scales away
```

## Cost

GPU node is the cost (A100 ~$3.5-4/hr, T4 ~$0.5/hr). Levers: `gpu_use_spot = true`, `gpu_node_min_count = 0` plus scale deployment to 0, smaller model/GPU.

## Cleanup

```bash
kubectl delete -k k8s/
terraform destroy
```

## Troubleshooting

- **Pod `Pending`, `Insufficient nvidia.com/gpu`**: device plugin not running or GPU node still provisioning. `kubectl describe pod`, check autoscaler events.
- **Node pool `QuotaExceeded` / `SkuNotAvailable`**: request GPU quota or change `location` / `gpu_vm_size`.
- **CUDA OOM**: lower `--context-length` / `--mem-fraction-static`, bigger GPU, or `--quantization fp8`.
- **Tool calls not parsed**: match `--tool-call-parser` to model family (`qwen25` for Qwen2.5/Qwen3).
- **Slow download, pod restarts**: raise `startupProbe.failureThreshold` in `deployment.yaml`.
