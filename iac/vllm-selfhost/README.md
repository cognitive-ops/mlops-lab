# vLLM on Amazon EKS (production)

Self-hosted, OpenAI-compatible LLM serving for ~1M requests/day and hundreds of concurrent agents.
Design rationale, sizing, and decisions: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

```
Agents -> Route 53 -> ALB (TLS, WAF) -> LiteLLM (keys, limits) -> vLLM router (prefix-aware) -> vLLM pods (g6e / L40S)
                                                                                                   ^ KEDA scales on queue depth
                                                                                                   ^ Karpenter provisions GPU nodes
Model weights: S3 -> Run:ai streamer      State: Aurora (keys/spend), Redis (rate limits)
```

Model: `Qwen/Qwen2.5-7B-Instruct`, FP8 weights and KV cache, on single-GPU `g6e` instances (FP8 needs Ada/Hopper; the A10G in `g5` does not support it).

## Layout

| Path | What it builds |
|---|---|
| `network.tf` | 3-AZ VPC, NAT per AZ, S3 and ECR VPC endpoints |
| `eks.tf` | EKS (Pod Identity, network policies, EBS CSI), system node group, Karpenter IAM and SQS |
| `data.tf` | KMS key, S3 model bucket, ECR repo, Aurora Serverless v2, ElastiCache Redis, Secrets Manager |
| `edge.tf` | ACM, Route 53, public ALB, WAF, access logs, CloudWatch alarms and SNS |
| `platform.tf` | Pod Identity roles, Karpenter, LB controller, KEDA, External Secrets, Prometheus/Grafana, NVIDIA device plugin, DCGM |
| `workloads.tf` | Installs the three charts below |
| `charts/karpenter-resources` | GPU `EC2NodeClass` and `NodePool`s: `gpu-baseline` (on-demand) and `gpu-burst` (Spot with on-demand fallback) |
| `charts/model-sync` | Hook job that mirrors Hugging Face weights into S3 |
| `charts/llm-serving` | vLLM, router, LiteLLM, KEDA `ScaledObject`, NetworkPolicies, ServiceMonitors, alerts, Grafana dashboard |
| `scripts/` | `mirror-image.sh`, `create-key.sh`, `smoke-test.sh` |

## Prerequisites

- Terraform >= 1.5, `aws` CLI (Terraform uses it for the EKS token), `kubectl`, `helm`, `docker` (image mirroring), `jq`.
- AWS credentials with admin-level rights for the first apply.
- **GPU quota** in the target region: Running On-Demand *G and VT* instances and All *G and VT* Spot Instance Requests. Request vCPUs for the maximum fleet (`g6e.xlarge` = 4 vCPUs, so 16 GPUs = 64+). Approval can take days. Without it, pods stay `Pending`.
- For TLS: a Route 53 hosted zone for your domain.

## Deploy

```bash
cd iac/vllm-selfhost
cp terraform.tfvars.example terraform.tfvars   # edit: domain, CIDRs, capacity

# 1. Create the registry first and mirror the vLLM image (avoids Docker Hub rate limits)
terraform init
terraform apply -target=aws_ecr_repository.vllm
bash scripts/mirror-image.sh                    # prints the vllm_image value to put in terraform.tfvars

# 2. Everything else (~25-40 min; includes the model download and first GPU node)
terraform apply
$(terraform output -raw configure_kubectl)
kubectl -n llm get pods
```

`terraform apply` blocks until the model is mirrored into S3 (hook job) and the vLLM, router, and LiteLLM deployments are ready. If it times out on GPU capacity, see Troubleshooting, then re-run `terraform apply`.

Without `domain_name`, the ALB serves plain HTTP on its AWS hostname (`tls_enabled = false`). Use that for a first test only.

## Issue keys and test

```bash
bash scripts/create-key.sh support-agents 600 400000 500 30d    # alias, rpm, tpm, budget USD, period
export LLM_API_KEY=sk-...                                        # the key returned above
bash scripts/smoke-test.sh
```

Agents use any OpenAI-compatible client:

```python
from openai import OpenAI
client = OpenAI(base_url="https://llm.example.com/v1", api_key=LLM_API_KEY)
client.chat.completions.create(model="qwen2.5-7b-instruct", messages=[{"role": "user", "content": "Hello"}])
```

Give each agent or team its own key. Never hand out the master key (`terraform output get_master_key`).
Only `/v1/*` is routed from the internet; the LiteLLM admin API and UI are reachable only via `kubectl port-forward`.

## Operations

| Task | How |
|---|---|
| Watch capacity | Grafana: `kubectl -n monitoring port-forward svc/kube-prometheus-stack-grafana 3000:80` (user `admin`, password in secret `monitoring/grafana-admin`), dashboard **vLLM Serving** |
| Scaling state | `kubectl -n llm get scaledobject,hpa,pods -o wide` and `kubectl get nodeclaims,nodepools` |
| Change baseline/max GPUs | Edit `gpu_baseline_count` / `gpu_max_count` and `terraform apply`. Check the quota first |
| Change model | Edit `model_repo`, `model_revision`, `model_served_name` (and `vllm_tool_call_parser` if the family changes), then `terraform apply`. Roll out via a canary first |
| Upgrade vLLM | Mirror the new image, change `vllm_image`, apply. Rollout surges one pod at a time and never drops capacity |
| Upgrade GPU AMI | Pin `gpu_ami_alias` to a tested release, apply. Nodes do not expire on their own, so replace them deliberately (cordon, drain, delete) |
| Rotate gateway secrets | Update the Secrets Manager secret, then `kubectl -n llm rollout restart deploy/litellm`. Do **not** rotate `LITELLM_SALT_KEY` |
| Alerts | CloudWatch alarms go to the SNS topic (`alarm_email`). Prometheus alerts are defined in the chart; add Alertmanager receivers to page on them |

## Troubleshooting

- **vLLM pods `Pending`**: `kubectl get nodeclaims`; `kubectl describe nodeclaim <name>`. Usual causes: GPU vCPU quota, no `g6e` capacity in the AZ (add sizes in `gpu_instance_sizes`), or `gpu_max_count` reached.
- **Pod starts but crashes loading weights**: `kubectl -n llm logs deploy/vllm`. Check the S3 path (`terraform output model_s3_uri`), the Pod Identity association for SA `llm/vllm`, and that the Run:ai streamer is in your image. As a fallback set `model_source = "hf"` to download from Hugging Face.
- **CUDA / driver errors**: the `cu129` image needs a recent NVIDIA driver; use a lower-CUDA tag or a newer GPU AMI.
- **Router shows no backends**: `kubectl -n llm logs deploy/vllm-router`; the pod needs label `app=vllm` and a passing `/health`.
- **429 from the gateway**: per-key rpm/tpm/budget limit; adjust the key. **403 from the ALB**: WAF rate limit (`waf_rate_limit_per_5min`) or `allowed_ingress_cidrs`.
- **Prometheus metrics missing for KEDA**: check `kubectl -n llm get servicemonitor` and that the query in `charts/llm-serving/templates/keda.yaml` returns data in Prometheus.

## Destroy

```bash
terraform destroy
```

`deletion_protection = true` (default) protects the ALB, Aurora, and S3 buckets. Set it to `false` and apply before destroying a throwaway environment.

## Known limitations (see ARCHITECTURE.md, section 14)

Workloads are installed by Terraform-driven Helm rather than GitOps, NetworkPolicies cover ingress only, and DR is out of scope. Throughput and fleet-size figures are planning assumptions until you run the Phase 0 benchmark.
