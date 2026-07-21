"""
AdalFlow: Adaptive Learning for Prompt Optimization
====================================================
AdalFlow takes a PyTorch-inspired approach: wrap every part of your prompt
(instruction text, few-shot demos) in a `Parameter` object that the optimizer
can read and rewrite, just like model weights.

Two optimizers shown here:
  - BootstrapFewShot : selects the best demonstrations from training data
  - TGDOptimizer     : Textual Gradient Descent — an LLM rewrites the instruction
                       based on feedback from failed predictions

Task: Vietnamese e-commerce review → NEG / NEU / POS

Install:
    pip install adalflow openai python-dotenv

Run (dry-run, no API key needed):
    python sentiment_optimizer.py

Run (real optimization):
    OPENAI_API_KEY=sk-... python sentiment_optimizer.py --optimize
"""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass

# ── Guard: give a clear error if adalflow is missing ──────────────────────────
try:
    import adalflow as adal
    from adalflow.components.model_client import OpenAIClient
    from adalflow.optim.few_shot.bootstrap_optimizer import BootstrapFewShot
    from adalflow.optim.text_grad.tgd_optimizer import TGDOptimizer
    from adalflow.optim.parameter import Parameter, ParameterType
    HAS_ADALFLOW = True
except ImportError:
    HAS_ADALFLOW = False


# ── Training data ─────────────────────────────────────────────────────────────
@dataclass
class Example:
    text: str
    label: str   # NEG | NEU | POS


TRAIN = [
    Example("Sản phẩm rất tuyệt vời, tôi rất hài lòng!", "POS"),
    Example("Dịch vụ tệ quá, tôi sẽ không quay lại nữa.", "NEG"),
    Example("Hàng nhận được đúng mô tả, giao hàng bình thường.", "NEU"),
    Example("Chất lượng vượt mong đợi, giao hàng nhanh!", "POS"),
    Example("Sản phẩm bị lỗi, hỗ trợ khách hàng chậm.", "NEG"),
    Example("Hàng ổn, không có gì đặc biệt.", "NEU"),
]

VAL = [
    Example("Tuyệt vời, mình sẽ mua lại!", "POS"),
    Example("Thất vọng, không đúng màu sắc.", "NEG"),
    Example("Bình thường, đúng mô tả.", "NEU"),
]


# ── Jinja2 prompt template ────────────────────────────────────────────────────
# AdalFlow uses {{variable}} Jinja2 syntax.
# The <SYS> block holds the optimizable system instruction.
# {{text}} is the runtime input.
TEMPLATE = """\
<SYS>
{{system_instruction}}
</SYS>

{% if demos %}
Examples:
{% for demo in demos %}
Review : {{demo.text}}
Label  : {{demo.label}}
{% endfor %}
{% endif %}

Review : {{text}}
Label (NEG/NEU/POS):"""


# ── Task component ────────────────────────────────────────────────────────────
def build_task(model_client, model_kwargs: dict) -> "adal.Component":
    """
    Returns an AdalFlow Component whose system_instruction and demos
    are marked as optimizable Parameters.
    """

    class SentimentTask(adal.Component):
        def __init__(self) -> None:
            super().__init__()

            # The instruction is a trainable parameter — TGDOptimizer will rewrite it.
            instruction_param = Parameter(
                data="Classify the Vietnamese e-commerce review as NEG, NEU, or POS.",
                role_desc="Task instruction for sentiment classification",
                requires_opt=True,
                param_type=ParameterType.PROMPT,
            )

            # The demo slots are trainable — BootstrapFewShot will fill them.
            demos_param = Parameter(
                data=[],
                role_desc="Few-shot demonstration examples",
                requires_opt=True,
                param_type=ParameterType.DEMOS,
            )

            self.generator = adal.Generator(
                model_client=model_client,
                model_kwargs=model_kwargs,
                template=TEMPLATE,
                prompt_kwargs={
                    "system_instruction": instruction_param,
                    "demos": demos_param,
                },
            )

        def call(self, text: str) -> str:
            output = self.generator(prompt_kwargs={"text": text})
            # Strip and normalize the label
            raw = output.data.strip().upper()
            for label in ("NEG", "NEU", "POS"):
                if label in raw:
                    return label
            return raw

    return SentimentTask()


# ── Metric ─────────────────────────────────────────────────────────────────────
def metric(example: Example, pred: str) -> bool:
    return pred.strip().upper() == example.label


# ── Dry-run: show rendered template without calling the API ────────────────────
def dry_run() -> None:
    from jinja2 import Environment

    env = Environment(trim_blocks=True, lstrip_blocks=True)
    tpl = env.from_string(TEMPLATE)

    sample = TRAIN[0]
    rendered = tpl.render(
        system_instruction="Classify the Vietnamese e-commerce review as NEG, NEU, or POS.",
        demos=TRAIN[1:3],
        text=sample.text,
    )
    print("=== DRY RUN — rendered prompt (no API call) ===")
    print(rendered)
    print()
    print(f"Expected label: {sample.label}")


# ── Bootstrap few-shot optimization ──────────────────────────────────────────
def run_bootstrap(task: "adal.Component", model_client, model_kwargs: dict) -> None:
    print("\n=== BootstrapFewShot Optimization ===")
    print("Selects the best demonstrations from TRAIN data that maximise")
    print("accuracy on held-out validation examples.")
    print()

    optimizer = BootstrapFewShot(
        task_model_config=model_kwargs,
        teacher_model_config={**model_kwargs, "model": "gpt-4o"},  # stronger teacher
        metric=metric,
        num_demos=3,
        max_steps=len(TRAIN),
    )

    optimized = optimizer.compile(
        task,
        trainset=TRAIN,
        valset=VAL,
    )

    print("Optimized demos selected:")
    for i, demo in enumerate(optimized.generator.prompt_kwargs["demos"].data, 1):
        print(f"  [{i}] {demo.text[:50]}... → {demo.label}")

    print("\nValidation predictions after optimization:")
    for ex in VAL:
        pred = optimized.call(ex.text)
        status = "✓" if metric(ex, pred) else "✗"
        print(f"  {status} pred={pred} | expected={ex.label} | {ex.text[:45]}...")


# ── TGD instruction optimization ──────────────────────────────────────────────
def run_tgd(task: "adal.Component", model_client, model_kwargs: dict) -> None:
    print("\n=== TGDOptimizer (Textual Gradient Descent) ===")
    print("An LLM acts as a 'gradient' function: it reads failed predictions and")
    print("rewrites the instruction to fix them, just like backprop updates weights.")
    print()

    optimizer = TGDOptimizer(
        parameters=list(task.parameters()),
        model_client=model_client,
        model_kwargs={**model_kwargs, "model": "gpt-4o"},
        lr=1.0,
    )

    # Mini training loop: 3 gradient steps over training data
    for step, ex in enumerate(TRAIN[:3], 1):
        pred = task.call(ex.text)
        loss = 0 if metric(ex, pred) else 1
        if loss:
            optimizer.step(
                loss_fn_output=f"Prediction '{pred}' is wrong. Expected '{ex.label}'.",
            )
        print(f"  Step {step}: pred={pred} expected={ex.label} loss={loss}")

    current_instruction = task.generator.prompt_kwargs["system_instruction"].data
    print(f"\nFinal instruction:\n  {current_instruction}")


# ── Entry point ───────────────────────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--optimize", action="store_true",
                        help="Run real optimization (requires OPENAI_API_KEY)")
    parser.add_argument("--mode", choices=["bootstrap", "tgd", "both"],
                        default="bootstrap", help="Which optimizer to run")
    args = parser.parse_args()

    if not args.optimize:
        dry_run()
        print("\nTo run real optimization: OPENAI_API_KEY=sk-... python sentiment_optimizer.py --optimize")
        return

    if not HAS_ADALFLOW:
        print("adalflow not installed. Run: pip install adalflow openai")
        sys.exit(1)

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Set OPENAI_API_KEY before running --optimize")
        sys.exit(1)

    model_client = OpenAIClient()
    model_kwargs = {"model": "gpt-4o-mini", "temperature": 0.0, "max_tokens": 10}
    task = build_task(model_client, model_kwargs)

    if args.mode in ("bootstrap", "both"):
        run_bootstrap(task, model_client, model_kwargs)

    if args.mode in ("tgd", "both"):
        run_tgd(task, model_client, model_kwargs)


if __name__ == "__main__":
    main()
