# mlops-lab

Personal MLOps / AI backend playground. Collection of standalone demos and Terraform IaC for exploring ML pipelines, LLM agents, RAG, context engineering, fine-tuning, vector DBs, model serving, and MLOps infra on AWS/Azure.

Each subfolder is self-contained (own `requirements.txt` / `README.md` where present). This is not a single deployable app.

## Structure

```
demo/                      standalone scripts & prototypes (agents, RAG, training, serving)
iac/                       Terraform stacks for MLOps / LLM-serving infra
claim-intake-options.md    slide-deck draft: three options for agentic claims intake
```

## demo/

### Agents and orchestration

| Folder | What it is |
|---|---|
| `adk` | Google ADK multi-agent example (orchestrator, math/weather/research/writer agents) |
| `agentic-ai` | Basic agentic AI example |
| `ai-agent` | Simple LLM agent example |
| `langgraph` | LangGraph circuit-breaker pattern (CLOSED / OPEN / HALF_OPEN gate with fallback) |
| `multi-agent-langgraph` | Multi-agent system (analyst/coder/researcher) with LangGraph supervisor |
| `state-graph` | LangGraph ReAct agent example |
| `langgraph-sglang-agent` | LangGraph agent backed by a self-hosted SGLang model |
| `graph-engineering` | Multi-agent Graph-RAG: extractor agent builds a knowledge graph (Neo4j), query agent answers via bounded subgraph retrieval |
| `insurance` | Two LangGraph multi-agent pipelines: auto policy application intake, and a cyclic FNOL claims intake with a mandatory human-review gate (SQLite-checkpointed) |
| `uitars-finetune` | GUI agent: LoRA SFT of UI-TARS-7B on screenshot-to-action data (LLaMA-Factory), plus inference and execution loop. See its README and `TECHNICAL_SOLUTION.md` |

### RAG, context and prompt engineering

| Folder | What it is |
|---|---|
| `rag` | RAG demos (LangChain, Haystack, FAISS) |
| `context_engineering` | Semantic and hierarchical chunking, parent-child retrieval, scratchpad pruning, SLM observation-compression middleware (see `README-slm-compressor.md`) |
| `dspy` | DSPy RAG pipelines (simple/optimized/production/with-retriever) |
| `adalflow` | AdalFlow prompt/pipeline optimizer (sentiment example) |
| `autoprompt` | Automatic Prompt Engineer (APE) optimizer |
| `prompt` | Jinja2-based prompt template manager |
| `qdrant` | Qdrant vector DB + RAG agent |
| `pipecone` | Pinecone vector DB demo |
| `vectordb` | Generic vector DB test |

### Models, training and inference

| Folder | What it is |
|---|---|
| `attention` | Self-attention from scratch: Q/K/V (NumPy and PyTorch) and KV cache |
| `inference_engineering` | HF transformers (static batching) vs vLLM (continuous batching, PagedAttention) benchmark. Needs Linux + CUDA; see `WORKFLOW.md` |
| `distillation` | Knowledge distillation: generate data, fine-tune, inference |
| `bert` | PhoBERT sentiment classification |
| `zeroshot-ml` | Zero-shot image/text classification and semantic search |
| `point3d` | Point Transformer for 3D point clouds |
| `nnunet-data-prep` | Dataset prep/validation for nnU-Net |
| `onnx` | ONNX export and inference test |
| `sglang` | SGLang self-hosted inference client |
| `model` | Generic model serving via FastAPI + Docker |
| `pytorch.py`, `colab.ipynb`, `scikit_learn_acceleration_with_gpu.ipynb` | Loose PyTorch / Colab / GPU scikit-learn notebooks |

### MLOps platforms and delivery

| Folder | What it is |
|---|---|
| `az-mlops` | Azure ML pipeline (data prep, train, pipeline) |
| `dvc` | DVC (Data Version Control) demo |
| `wandb` | Weights & Biases logging demos |
| `modal` | Modal.com serverless compute demo |
| `mnist-lambda` | MNIST model trained and deployed to AWS Lambda (SAM/CDK, DVC-tracked) |
| `cicd-dashboard` | Node/TS dashboard collecting AWS CodePipeline status |

`demo/README.md` holds notes from researching different MLOps platforms.

## iac/

Terraform stacks, each deployed independently.

| Folder | Cloud | What it deploys |
|---|---|---|
| `llm-ec2` | AWS | Self-hosted LLM (vLLM) on a GPU EC2 instance behind ALB, with monitoring |
| `vllm-selfhost` | AWS | Production vLLM on EKS: ALB/WAF, LiteLLM gateway, vLLM router, KEDA + Karpenter autoscaling, Aurora and Redis. Design in `docs/ARCHITECTURE.md` |
| `sglang-selfhost` | Azure | Qwen served by SGLang on AKS with a GPU node pool (Terraform for infra, `k8s/` YAML for the workload) |
| `ml-ec2` | AWS | GPU EC2 instance for ML workloads |
| `mlflow-server` | AWS | MLflow tracking server (EC2, RDS, S3, DynamoDB, Route 53, Lambda start/stop control) |
| `sagemaker` | AWS | SageMaker notebook instance plus training job scripts (Dockerfiles, buildspec) |

## Prerequisites

- Python 3.11 (per-demo `requirements.txt`; some demos were run on 3.12)
- Terraform plus AWS CLI (AWS stacks) or Azure CLI (`sglang-selfhost`), configured per stack (`provider.tf` / `.tfvars`)
- Node.js for `demo/cicd-dashboard`
- Linux + NVIDIA GPU (or WSL2/Docker) for vLLM / SGLang / fine-tuning demos
- API keys for LLM providers where a demo needs them. Copy `.env.example` to `.env` (git-ignored)

## Usage

Pick a subfolder and follow its own `README.md`. General pattern for Python demos:

```bash
cd demo/<name>
pip install -r requirements.txt
python <script>.py
```

General pattern for Terraform stacks:

```bash
cd iac/<name>
terraform init
terraform apply
```

## Notes

- `*.tfvars`, `*.tfstate`, `.env`, `*.sqlite`, `.terraform/`, venvs and `__pycache__` are git-ignored. Create your own `terraform.tfvars` (some stacks ship a `terraform.tfvars.example`).
- GPU stacks cost real money. Run `terraform destroy` when done.
