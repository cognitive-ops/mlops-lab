"""
Step 3: Compare fine-tuned small model vs Claude teacher.
Runs local model (free) vs Sonnet (paid) side-by-side.
"""
import time
from pathlib import Path
import anthropic
import torch

ADAPTER_PATH = str(Path(__file__).parent / "output" / "model" / "lora_adapter")
TASK_SYSTEM_PROMPT = """You are a senior software engineer and solutions architect with 15+ years of experience.
Given a software development task or requirement, provide a structured, actionable response covering:
- Analysis of the requirement or problem
- Recommended approach or solution with reasoning
- Key considerations (scalability, security, maintainability)
- Concrete implementation steps or code where relevant
Be precise, technical, and opinionated. Avoid vague advice."""

TEST_QUESTIONS = [
    "Analyze this requirement: 'Users shall be able to upload profile photos up to 5MB in JPEG or PNG format.'",
    "Design the database schema for a task management app with projects, tasks, subtasks, and team members.",
    "Review this code for issues:\ndef login(username, password):\n    user = db.execute(f'SELECT * FROM users WHERE username={username}').first()\n    if user and user.password == password:\n        return True",
]


def load_local_model():
    """Load fine-tuned LoRA model for local inference."""
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    from peft import PeftModel

    base_id = "microsoft/Phi-3.5-mini-instruct"
    tokenizer = AutoTokenizer.from_pretrained(ADAPTER_PATH, trust_remote_code=True)

    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16,
    )
    base = AutoModelForCausalLM.from_pretrained(
        base_id,
        quantization_config=bnb_config,
        device_map="auto",
        trust_remote_code=True,
        attn_implementation="eager",
    )
    model = PeftModel.from_pretrained(base, ADAPTER_PATH)
    model.eval()
    return model, tokenizer, "peft"


def local_inference(model, tokenizer, question: str) -> tuple[str, float]:
    prompt = (
        f"<|system|>\n{TASK_SYSTEM_PROMPT}<|end|>\n"
        f"<|user|>\n{question}<|end|>\n"
        f"<|assistant|>\n"
    )
    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
    t0 = time.time()
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=512,
            temperature=0.7,
            do_sample=True,
            pad_token_id=tokenizer.eos_token_id,
            use_cache=False,
        )
    elapsed = time.time() - t0
    decoded = tokenizer.decode(outputs[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
    return decoded.strip(), elapsed


def claude_inference(question: str) -> tuple[str, float]:
    client = anthropic.Anthropic()
    t0 = time.time()
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        system=TASK_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": question}],
    )
    elapsed = time.time() - t0
    return response.content[0].text, elapsed


def main():
    print("Loading fine-tuned model...")
    model, tokenizer, backend = load_local_model()
    print(f"Model loaded via {backend}\n")

    for i, question in enumerate(TEST_QUESTIONS, 1):
        print(f"{'='*60}")
        print(f"Q{i}: {question}\n")

        local_answer, local_time = local_inference(model, tokenizer, question)
        claude_answer, claude_time = claude_inference(question)

        print(f"[LOCAL MODEL — {local_time:.1f}s, $0.00]")
        print(local_answer)
        print()
        print(f"[CLAUDE SONNET — {claude_time:.1f}s, ~$0.001]")
        print(claude_answer)
        print()


if __name__ == "__main__":
    main()
