# backend-mlops

Personal MLOps / AI backend playground. Collection of standalone demos and Terraform IaC for exploring ML pipelines, LLM agents, RAG, vector DBs, model serving, and MLOps infra on AWS/Azure.

Each subfolder is self-contained (own `requirements.txt` / `README.md`) — not a single deployable app.

## Structure

```
demo/    standalone scripts & prototypes (agents, RAG, training, serving)
iac/     Terraform stacks for MLOps infra
```

### demo/

| Folder | What it is |
|---|---|
| `adalflow` | AdalFlow prompt/pipeline optimizer (sentiment example) |
| `adk` | Google ADK multi-agent example (orchestrator, math/weather/research/writer agents) |
| `agentic-ai` | Basic agentic AI example |
| `ai-agent` | Simple LLM agent example |
| `autoprompt` | Automatic Prompt Engineer (APE) optimizer |
| `az-mlops` | Azure ML pipeline (data prep, train, pipeline) |
| `bert` | PhoBERT sentiment classification |
| `cicd-dashboard` | Node/TS dashboard collecting AWS CodePipeline status |
| `distillation` | Knowledge distillation: generate data → finetune → inference |
| `dspy` | DSPy RAG pipelines (simple/optimized/production/with-retriever) |
| `dvc` | DVC (Data Version Control) demo |
| `graph-engineering` | Multi-agent Graph-RAG: extractor agent builds a knowledge graph (networkx), query agent answers via bounded subgraph retrieval |
| `langgraph-sglang-agent` | LangGraph agent backed by a self-hosted SGLang model |
| `mnist-lambda` | MNIST model trained + deployed to AWS Lambda (SAM/CDK, DVC-tracked) |
| `modal` | Modal.com serverless compute demo |
| `model` | Generic model serving via FastAPI + Docker |
| `multi-agent-langgraph` | Multi-agent system (analyst/coder/researcher) with LangGraph supervisor |
| `nnunet-data-prep` | Dataset prep/validation for nnU-Net |
| `onnx` | ONNX export & inference test |
| `pipecone` | Pinecone vector DB demo |
| `point3d` | Point Transformer for 3D point clouds |
| `prompt` | Jinja2-based prompt template manager |
| `qdrant` | Qdrant vector DB + RAG agent |
| `rag` | RAG demos (LangChain, Haystack, FAISS) |
| `sglang` | SGLang self-hosted inference client |
| `state-graph` | LangGraph ReAct agent example |
| `vectordb` | Generic vector DB test |
| `wandb` | Weights & Biases logging demos |
| `zeroshot-ml` | Zero-shot image/text classification & semantic search |

### iac/

Terraform stacks, each deployed independently.

| Folder | What it deploys |
|---|---|
| `llm-selfhost` | Self-hosted LLM on EC2 behind ALB (+ monitoring) |
| `ml-ec2` | EC2 instance for ML workloads |
| `mlflow-server` | MLflow tracking server (EC2, RDS, S3, DynamoDB, Lambda start/stop control) |
| `sagemaker` | SageMaker notebook instance + training job scripts |
| `sglang-selfhost` | Self-hosted SGLang inference server on EC2 behind ALB |

## Prerequisites

- Python 3.11 (per-demo `requirements.txt`)
- Terraform, AWS CLI configured (per-stack `provider.tf` / `.tfvars`) for `iac/`
- Node.js for `demo/cicd-dashboard`

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
