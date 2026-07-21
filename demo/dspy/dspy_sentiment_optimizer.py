"""
DSPy: Systematic Prompt Programming with Automatic Optimization
================================================================
DSPy treats your prompt as a *program*, not a string.
You define:
  - Signature  : typed input/output spec (like a function signature)
  - Module     : the program (ChainOfThought, Predict, ReAct, etc.)
  - Metric     : a Python function that scores predictions
  - Optimizer  : compiles the program by searching for the best
                 instructions + few-shot examples

Two optimizers shown:
  BootstrapFewShot — randomly samples demonstrations, keeps those that
                     pass the metric. Cheap and effective.
  MIPROv2          — Bayesian search over (instruction, demos) pairs.
                     More powerful, uses more LLM calls.

Task: Vietnamese e-commerce review → NEG / NEU / POS

Install:
    pip install dspy-ai openai python-dotenv

Run (dry-run, no API key needed):
    python dspy_sentiment_optimizer.py

Run (real optimization):
    OPENAI_API_KEY=sk-... python dspy_sentiment_optimizer.py --optimize
    OPENAI_API_KEY=sk-... python dspy_sentiment_optimizer.py --optimize --optimizer mipro
"""

from __future__ import annotations

import argparse
import os
import sys

# ── Guard ─────────────────────────────────────────────────────────────────────
try:
    import dspy
    from dspy.teleprompt import BootstrapFewShot, MIPROv2
    HAS_DSPY = True
except ImportError:
    HAS_DSPY = False


# ── Training / validation data ────────────────────────────────────────────────
RAW_TRAIN = [
    ("Sản phẩm rất tuyệt vời, tôi rất hài lòng!", "POS"),
    ("Dịch vụ tệ quá, tôi sẽ không quay lại nữa.", "NEG"),
    ("Hàng nhận được đúng mô tả, giao hàng bình thường.", "NEU"),
    ("Chất lượng vượt mong đợi, giao hàng nhanh!", "POS"),
    ("Sản phẩm bị lỗi, hỗ trợ khách hàng chậm.", "NEG"),
    ("Hàng ổn, không có gì đặc biệt.", "NEU"),
    ("Mua lần đầu rất hài lòng, sẽ ủng hộ tiếp.", "POS"),
    ("Giao hàng sai địa chỉ, phải chờ thêm 3 ngày.", "NEG"),
]

RAW_VAL = [
    ("Tuyệt vời, mình sẽ mua lại!", "POS"),
    ("Thất vọng, không đúng màu sắc.", "NEG"),
    ("Bình thường, đúng mô tả.", "NEU"),
    ("Shop nhiệt tình, hàng đẹp.", "POS"),
]


# ── DSPy Signature ─────────────────────────────────────────────────────────────
# A Signature is an input/output contract. The docstring becomes the task
# instruction that BootstrapFewShot / MIPROv2 will optimise.
class SentimentSignature(dspy.Signature if HAS_DSPY else object):
    """Classify a Vietnamese e-commerce review as NEG (negative), NEU (neutral), or POS (positive)."""

    text: str = dspy.InputField(desc="Vietnamese review text") if HAS_DSPY else None
    label: str = dspy.OutputField(desc="exactly one of: NEG, NEU, POS") if HAS_DSPY else None


# ── DSPy Module ───────────────────────────────────────────────────────────────
# ChainOfThought makes the LLM produce a reasoning trace before the final label.
# Swap with dspy.Predict(SentimentSignature) for a direct prediction.
class SentimentClassifier(dspy.Module if HAS_DSPY else object):
    def __init__(self) -> None:
        super().__init__()
        self.classify = dspy.ChainOfThought(SentimentSignature)

    def forward(self, text: str):
        return self.classify(text=text)


# ── Metric ─────────────────────────────────────────────────────────────────────
def exact_match(example, pred, trace=None) -> bool:
    """Return True if predicted label exactly matches ground truth."""
    return example.label.strip().upper() == pred.label.strip().upper()


# ── Evaluation helper ──────────────────────────────────────────────────────────
def evaluate(program, valset) -> float:
    correct = 0
    for ex in valset:
        try:
            pred = program(text=ex.text)
            if exact_match(ex, pred):
                correct += 1
        except Exception as e:
            print(f"    [error] {e}")
    acc = correct / len(valset)
    print(f"  Accuracy: {correct}/{len(valset)} = {acc:.0%}")
    return acc


# ── Dry-run ────────────────────────────────────────────────────────────────────
def dry_run() -> None:
    print("=== DSPy — Dry Run (no API call) ===\n")

    print("1. Signature (input/output contract):")
    print("   text  → [InputField]  Vietnamese review")
    print("   label → [OutputField] NEG | NEU | POS")
    print()

    print("2. Module: SentimentClassifier(ChainOfThought)")
    print("   ChainOfThought adds a 'reasoning' field before the label output,")
    print("   which helps the LLM think step-by-step before committing.")
    print()

    print("3. Training set examples:")
    for text, label in RAW_TRAIN[:3]:
        print(f"   [{label}] {text}")
    print()

    print("4. BootstrapFewShot will:")
    print("   a) Run the un-compiled program on each training example")
    print("   b) Keep examples where metric(example, pred) == True")
    print("   c) Attach those as few-shot demos to the compiled program")
    print()

    print("5. MIPROv2 will additionally:")
    print("   a) Generate many candidate instructions (via LLM)")
    print("   b) Try (instruction, demos) combinations on a mini validation set")
    print("   c) Use Bayesian optimization to converge on the best combination")
    print()
    print("Run with --optimize to see real results.")


# ── Bootstrap few-shot ─────────────────────────────────────────────────────────
def run_bootstrap(trainset, valset) -> None:
    print("\n=== BootstrapFewShot Optimization ===")
    print("Compiling program by finding which training examples best serve as demos...\n")

    program = SentimentClassifier()

    # Baseline (before optimization)
    print("Baseline (zero-shot, no demos):")
    evaluate(program, valset)

    optimizer = BootstrapFewShot(
        metric=exact_match,
        max_bootstrapped_demos=4,   # include up to 4 demos in the prompt
        max_labeled_demos=4,        # additionally allow labeled demos from trainset
        max_rounds=1,               # number of bootstrap rounds
    )

    compiled = optimizer.compile(
        SentimentClassifier(),      # fresh instance
        trainset=trainset,
    )

    print("\nAfter BootstrapFewShot compilation:")
    evaluate(compiled, valset)

    # Inspect what demos were selected
    for name, predictor in compiled.named_predictors():
        demos = getattr(predictor, "demos", [])
        if demos:
            print(f"\n  Demos selected for '{name}':")
            for d in demos:
                print(f"    [{d.label}] {d.text[:55]}...")

    return compiled


# ── MIPROv2 ───────────────────────────────────────────────────────────────────
def run_mipro(trainset, valset) -> None:
    print("\n=== MIPROv2 Optimization ===")
    print("Jointly optimises the instruction text AND few-shot demos via Bayesian search.\n")

    # auto="light"  →  fast, fewer trials (~10 LLM calls for instruction generation)
    # auto="medium" →  balanced (~25 calls)
    # auto="heavy"  →  thorough (~50 calls)
    optimizer = MIPROv2(
        metric=exact_match,
        auto="light",
        num_threads=4,
    )

    compiled = optimizer.compile(
        SentimentClassifier(),
        trainset=trainset,
        valset=valset,
        requires_permission_to_run=False,
    )

    print("After MIPROv2 compilation:")
    evaluate(compiled, valset)

    # Print the optimized instruction DSPy found
    for name, predictor in compiled.named_predictors():
        if hasattr(predictor, "extended_signature"):
            sig = predictor.extended_signature
            print(f"\n  Optimized instruction for '{name}':\n    {sig.instructions}")

    return compiled


# ── Entry point ────────────────────────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--optimize", action="store_true",
                        help="Run real optimization (requires OPENAI_API_KEY)")
    parser.add_argument("--optimizer", choices=["bootstrap", "mipro", "both"],
                        default="bootstrap")
    args = parser.parse_args()

    if not args.optimize:
        dry_run()
        print("\nTo run: OPENAI_API_KEY=sk-... python dspy_sentiment_optimizer.py --optimize")
        return

    if not HAS_DSPY:
        print("dspy-ai not installed. Run: pip install dspy-ai openai")
        sys.exit(1)

    if not os.getenv("OPENAI_API_KEY"):
        print("Set OPENAI_API_KEY first.")
        sys.exit(1)

    # Configure LM — DSPy supports any litellm-compatible model string
    # Claude alternative: dspy.LM("anthropic/claude-haiku-4-5-20251001")
    dspy.configure(lm=dspy.LM("openai/gpt-4o-mini", max_tokens=50))

    trainset = [dspy.Example(text=t, label=l).with_inputs("text") for t, l in RAW_TRAIN]
    valset   = [dspy.Example(text=t, label=l).with_inputs("text") for t, l in RAW_VAL]

    if args.optimizer in ("bootstrap", "both"):
        run_bootstrap(trainset, valset)

    if args.optimizer in ("mipro", "both"):
        run_mipro(trainset, valset)


if __name__ == "__main__":
    main()
