# API Usage Guide

Complete reference for using your self-hosted LLM API.

## Quick Start

```bash
# Set your endpoint
ENDPOINT="http://your-load-balancer-dns"

# List available models
curl $ENDPOINT/v1/models

# Generate text
curl -X POST $ENDPOINT/v1/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "mistral-7b",
    "prompt": "The fastest programming language is",
    "max_tokens": 50
  }'

# Chat interface
curl -X POST $ENDPOINT/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "mistral-7b",
    "messages": [
      {"role": "system", "content": "You are a helpful assistant."},
      {"role": "user", "content": "What is machine learning?"}
    ],
    "temperature": 0.7
  }'
```

## API Endpoints

### 1. List Models

**Request**:
```bash
GET /v1/models
```

**Response**:
```json
{
  "object": "list",
  "data": [
    {
      "id": "mistral-7b",
      "object": "model",
      "created": 1702123456,
      "owned_by": "mistralai"
    }
  ]
}
```

---

### 2. Text Completion

**Request**:
```bash
POST /v1/completions
Content-Type: application/json

{
  "model": "mistral-7b",
  "prompt": "Write a haiku about",
  "max_tokens": 100,
  "temperature": 0.7,
  "top_p": 0.9,
  "top_k": 40,
  "frequency_penalty": 0.0,
  "presence_penalty": 0.0,
  "stop": ["\n"],
  "stream": false
}
```

**Parameters**:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `model` | string | required | Model name (e.g., "mistral-7b") |
| `prompt` | string | required | Input text |
| `max_tokens` | integer | 16 | Max output tokens (1-4096) |
| `temperature` | float | 1.0 | Randomness (0.0-2.0), lower=deterministic |
| `top_p` | float | 1.0 | Nucleus sampling (0.0-1.0) |
| `top_k` | integer | -1 | Top-k sampling (-1=disabled) |
| `frequency_penalty` | float | 0.0 | Penalize repeated tokens |
| `presence_penalty` | float | 0.0 | Penalize new tokens |
| `stop` | string[] | null | Stop generation at these strings |
| `stream` | boolean | false | Stream response tokens |

**Response**:
```json
{
  "id": "cmpl-123",
  "object": "text_completion",
  "created": 1702123456,
  "model": "mistral-7b",
  "choices": [
    {
      "text": " artificial intelligence is the simulation",
      "index": 0,
      "logprobs": null,
      "finish_reason": "length"
    }
  ],
  "usage": {
    "prompt_tokens": 10,
    "completion_tokens": 5,
    "total_tokens": 15
  }
}
```

---

### 3. Chat Completion (OpenAI Compatible)

**Request**:
```bash
POST /v1/chat/completions
Content-Type: application/json

{
  "model": "mistral-7b",
  "messages": [
    {"role": "system", "content": "You are a Python expert."},
    {"role": "user", "content": "How do I read a CSV file?"},
    {"role": "assistant", "content": "You can use pandas..."},
    {"role": "user", "content": "Can you show me an example?"}
  ],
  "temperature": 0.7,
  "max_tokens": 200,
  "top_p": 0.9,
  "stream": false
}
```

**Parameters**:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `model` | string | required | Model name |
| `messages` | object[] | required | Chat messages |
| `temperature` | float | 1.0 | Randomness |
| `max_tokens` | integer | null | Max output length |
| `top_p` | float | 1.0 | Nucleus sampling |
| `stream` | boolean | false | Stream tokens |

**Message Object**:
```json
{
  "role": "user|assistant|system",
  "content": "Message text"
}
```

**Response**:
```json
{
  "id": "chatcmpl-123",
  "object": "chat.completion",
  "created": 1702123456,
  "model": "mistral-7b",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "To read a CSV file in pandas:\n\n```python\nimport pandas as pd\ndf = pd.read_csv('file.csv')\n```"
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 45,
    "completion_tokens": 30,
    "total_tokens": 75
  }
}
```

---

## Streaming Responses

For real-time token generation, use streaming:

```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "mistral-7b",
    "messages": [{"role": "user", "content": "Count to 5"}],
    "stream": true
  }' | jq -Rs 'split("\n") | .[]'
```

**Streaming Response** (newline-delimited JSON):
```
data: {"choices":[{"delta":{"content":"One"},"finish_reason":null}]}
data: {"choices":[{"delta":{"content":" "},"finish_reason":null}]}
data: {"choices":[{"delta":{"content":"two"},"finish_reason":null}]}
...
data: [DONE]
```

---

## Client Libraries

### Python with OpenAI SDK

```python
from openai import OpenAI

client = OpenAI(
    api_key="not needed",
    base_url="http://your-endpoint"
)

# Chat completion
response = client.chat.completions.create(
    model="mistral-7b",
    messages=[
        {"role": "user", "content": "What is AI?"}
    ],
    max_tokens=100,
    temperature=0.7
)

print(response.choices[0].message.content)

# Streaming
stream = client.chat.completions.create(
    model="mistral-7b",
    messages=[{"role": "user", "content": "Tell a joke"}],
    stream=True
)

for chunk in stream:
    if chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="", flush=True)
```

### Node.js

```javascript
import OpenAI from "openai";

const openai = new OpenAI({
  apiKey: "not-needed",
  baseURL: "http://your-endpoint",
});

async function chat() {
  const response = await openai.chat.completions.create({
    model: "mistral-7b",
    messages: [{ role: "user", content: "Hello!" }],
    max_tokens: 100,
  });

  console.log(response.choices[0].message.content);
}

chat();
```

### JavaScript/Fetch

```javascript
const endpoint = "http://your-endpoint";

async function generateText(prompt) {
  const response = await fetch(`${endpoint}/v1/completions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      model: "mistral-7b",
      prompt: prompt,
      max_tokens: 100,
    }),
  });

  const data = await response.json();
  return data.choices[0].text;
}

generateText("What is web development?").then(console.log);
```

### cURL Examples

**Simple completion**:
```bash
curl -s -X POST http://localhost:8000/v1/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "mistral-7b",
    "prompt": "The meaning of life is",
    "max_tokens": 50
  }' | jq '.choices[0].text'
```

**Chat with system prompt**:
```bash
curl -s -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "mistral-7b",
    "messages": [
      {"role": "system", "content": "You are a mathematics expert."},
      {"role": "user", "content": "What is 2+2?"}
    ]
  }' | jq '.choices[0].message.content'
```

**Using environment variable for endpoint**:
```bash
export LLM_ENDPOINT="http://your-load-balancer-dns"

curl -s -X POST $LLM_ENDPOINT/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "mistral-7b",
    "messages": [{"role": "user", "content": "Hi"}]
  }' | jq
```

---

## Use Case Examples

### 1. Code Generation

```python
from openai import OpenAI

client = OpenAI(base_url="http://your-endpoint")

code_prompt = """
Write a Python function that:
1. Takes a list of numbers
2. Returns the sum of squares
3. Handles empty lists
"""

response = client.chat.completions.create(
    model="mistral-7b",
    messages=[{"role": "user", "content": code_prompt}],
    max_tokens=200,
    temperature=0.7
)

print(response.choices[0].message.content)
```

### 2. Summarization

```python
long_text = "..."  # Your text to summarize

response = client.chat.completions.create(
    model="mistral-7b",
    messages=[{
        "role": "user",
        "content": f"Summarize in 3 sentences:\n\n{long_text}"
    }],
    max_tokens=100,
    temperature=0.3  # Low temperature for consistency
)

print(response.choices[0].message.content)
```

### 3. Question Answering

```python
context = "Paris is the capital of France..."

response = client.chat.completions.create(
    model="mistral-7b",
    messages=[
        {"role": "system", "content": f"Context: {context}"},
        {"role": "user", "content": "What is the capital of France?"}
    ],
    max_tokens=50
)
```

### 4. Batch Processing

```python
questions = [
    "What is Python?",
    "What is JavaScript?",
    "What is Go?"
]

for question in questions:
    response = client.chat.completions.create(
        model="mistral-7b",
        messages=[{"role": "user", "content": question}],
        max_tokens=100
    )
    print(f"Q: {question}")
    print(f"A: {response.choices[0].message.content}\n")
```

---

## Performance Tips

### 1. Batch Requests
```bash
# Don't spam individual requests, batch where possible
# Instead of 10 sequential requests, combine into fewer requests
```

### 2. Optimize Temperature
```python
# For creativity: temperature = 0.8-1.0
# For consistency: temperature = 0.3-0.5
# For logic: temperature = 0.1-0.3
```

### 3. Tune Max Tokens
```python
# Only request what you need
# max_tokens=50 for summaries
# max_tokens=200 for code
# max_tokens=500 for essays
```

### 4. Use Streaming for UX
```python
# For user-facing: enable streaming for better responsiveness
# For processing: disable streaming to get full response at once
```

### 5. Connection Pooling
```python
# Reuse client connection
client = OpenAI(base_url="http://your-endpoint")
# Reuse this client for multiple requests
```

---

## Error Handling

```python
from openai import OpenAI, APIError, APIConnectionError

client = OpenAI(base_url="http://your-endpoint")

try:
    response = client.chat.completions.create(
        model="mistral-7b",
        messages=[{"role": "user", "content": "Hello"}],
        max_tokens=100
    )
except APIConnectionError:
    print("Failed to connect to LLM endpoint")
except APIError as e:
    print(f"API error: {e}")
else:
    print(response.choices[0].message.content)
```

---

## Monitoring & Debugging

### Check API Health
```bash
# Endpoint responsiveness
curl -v http://your-endpoint/v1/models

# Response time
time curl http://your-endpoint/v1/models

# Load balancer status
aws elb describe-instance-health --load-balancer-name llm-server-alb
```

### Monitor Instance
```bash
# SSH into instance and monitor
watch -n 1 'nvidia-smi | grep " 0 "'
watch -n 1 'curl -s http://localhost:8000/v1/models | jq'
```

### Check Metrics
```bash
# View CloudWatch metrics
aws cloudwatch get-metric-statistics \
  --metric-name CPUUtilization \
  --namespace AWS/EC2 \
  --start-time 2024-01-01T00:00:00Z \
  --end-time 2024-01-01T01:00:00Z \
  --period 300 \
  --statistics Average
```

---

## Rate Limiting & Quotas

Currently no built-in rate limiting. To add:

1. **Use API Gateway**: Add throttling at AWS API Gateway layer
2. **Use Nginx**: Reverse proxy with rate limiting
3. **Add authentication**: Use JWT tokens + rate limit per user

See [ADVANCED.md](ADVANCED.md) for implementation details.

---

## Costs to Consider

Request costs depend on:
- **Model size**: Larger models = higher compute = slower responses
- **Request frequency**: More requests = more GPU utilization = more cost
- **Batch size**: Processing multiple requests together = better efficiency
- **Instance uptime**: Running 24/7 ≠ running on-demand

Monitor with:
```bash
aws ce get-cost-and-usage \
  --time-period Start=2024-01-01,End=2024-01-31 \
  --granularity MONTHLY \
  --metrics "UnblendedCost"
```

---

## Getting Help

- **API Issues**: Check [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- **vLLM Docs**: https://docs.vllm.ai/
- **OpenAI API Docs**: https://platform.openai.com/docs/api-reference
- **Instance Issues**: Check CloudWatch logs: `aws logs tail /aws/ec2/llm-server/vllm --follow`
