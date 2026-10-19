# vLLM self-hosted on Amazon EKS

Terraform builds a VPC and an EKS cluster with a tainted GPU node group. Kubernetes manifests then run vLLM (OpenAI-compatible API) behind an NLB.

Default model: `Qwen/Qwen2.5-7B-Instruct` on one `g5.xlarge` (A10G 24 GB).

> This stack is a **single-replica lab deployment**. The production design (about 1M requests/day, hundreds of concurrent agents) is in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Layout

| Path | Purpose |
|------|---------|
| `provider.tf`, `variables.tf`, `outputs.tf` | Terraform config |
| `eks.tf` | VPC, EKS cluster, `system` (CPU) and `gpu` node groups, EBS CSI addon |
| `k8s/` | Namespace, NVIDIA device plugin, gp3 StorageClass + model-cache PVC, vLLM Deployment, NLB Service |

## Deploy

```bash
cd iac/vllm-selfhost
terraform init
terraform apply            # ~15 min

# kubeconfig (also printed as the `configure_kubectl` output)
aws eks update-kubeconfig --region us-east-1 --name vllm-eks-dev

kubectl apply -k k8s/
kubectl -n vllm rollout status deploy/vllm --timeout=30m
kubectl -n vllm logs -f deploy/vllm
```

First start pulls the image (~10 GB) and downloads the weights into the EBS-backed cache; later restarts reuse it.

Optional secrets (create before or after the apply; the pod reads them as optional):

```bash
kubectl -n vllm create secret generic hf-token --from-literal=HF_TOKEN=hf_xxx            # gated models
kubectl -n vllm create secret generic vllm-api-key --from-literal=VLLM_API_KEY=$(openssl rand -hex 24)
kubectl -n vllm rollout restart deploy/vllm
```

## Test

```bash
HOST=$(kubectl -n vllm get svc vllm -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
curl http://$HOST/v1/models
curl http://$HOST/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $VLLM_API_KEY" \
  -d '{"model":"qwen2.5-7b-instruct","messages":[{"role":"user","content":"Hello"}]}'
```

Omit the `Authorization` header if you did not create `vllm-api-key`. The NLB can take a few minutes to become reachable.

## Customize

- **Model / flags**: edit `command` and `args` in `k8s/deployment.yaml`. Match `--tool-call-parser` to the model family. Size the GPU for the weights plus KV cache, and use `--tensor-parallel-size N` with `nvidia.com/gpu: N` on multi-GPU instances.
- **GPU type**: `-var gpu_instance_type=g4dn.xlarge` (T4, no bf16: also uncomment `--dtype half`). Check that the Qwen weights (~15 GB) fit your GPU.
- **Spot**: `-var gpu_use_spot=true`.
- **Image**: pinned to `v0.32.0-cu129`, which needs a recent NVIDIA driver. If the pod fails with CUDA/driver errors, switch to a lower-CUDA tag (e.g. a `cu12x` variant) in `k8s/deployment.yaml`.
- **Lock down access**: set `loadBalancerSourceRanges` in `k8s/service.yaml` and `cluster_endpoint_public_access_cidrs`, or make the NLB internal via the commented annotation.

## Notes

- The EBS volume is zonal, so the vLLM pod stays in the zone where the PVC bound. Keep a GPU node available in that zone.
- The EBS CSI driver gets its permissions from the node role for simplicity. For production, use IRSA or EKS Pod Identity.
- Cost: GPU node, 2 system nodes, NAT gateway, NLB and EBS all bill while the cluster exists.

## Destroy

```bash
kubectl delete -k k8s/        # removes the NLB and EBS volume first
terraform destroy
```
