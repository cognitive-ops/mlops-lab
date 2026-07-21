"""
Jinja prompt demo — shows three template rendering patterns:
  1. System prompt with optional few-shot examples
  2. Per-text user prompt with optional domain context
  3. Batch prompt with a loop over multiple texts

Run:
    python demo.py

No LLM key required — this just prints the rendered prompts.
"""

from prompt_manager import PromptManager

manager = PromptManager()

# ── 1. System prompt (no few-shot) ──────────────────────────────────────────
system_plain = manager.render(
    "sentiment_system.j2",
    language="Vietnamese",
    few_shot_examples=None,
)
print("=== SYSTEM (no few-shot) ===")
print(system_plain)

# ── 2. System prompt WITH few-shot examples ──────────────────────────────────
few_shots = [
    {"text": "Sản phẩm rất tốt, tôi hài lòng!", "label": "POS"},
    {"text": "Giao hàng chậm, chất lượng kém.", "label": "NEG"},
    {"text": "Hàng nhận đúng mô tả.",            "label": "NEU"},
]

system_with_shots = manager.render(
    "sentiment_system.j2",
    language="Vietnamese",
    few_shot_examples=few_shots,
)
print("=== SYSTEM (with few-shot) ===")
print(system_with_shots)

# ── 3. User prompt for a single text ─────────────────────────────────────────
user_prompt = manager.render(
    "sentiment_user.j2",
    language="Vietnamese",
    domain="e-commerce reviews",
    text="Dịch vụ tệ quá, tôi sẽ không quay lại nữa.",
)
print("=== USER PROMPT ===")
print(user_prompt)

# ── 4. Batch prompt ───────────────────────────────────────────────────────────
texts = [
    "Sản phẩm này rất tuyệt vời, tôi rất hài lòng!",
    "Dịch vụ tệ quá, tôi sẽ không quay lại nữa.",
    "Hàng nhận được đúng mô tả, giao hàng bình thường.",
]

batch_prompt = manager.render(
    "batch_analysis.j2",
    language="Vietnamese",
    domain="e-commerce reviews",
    texts=texts,
)
print("=== BATCH PROMPT ===")
print(batch_prompt)
