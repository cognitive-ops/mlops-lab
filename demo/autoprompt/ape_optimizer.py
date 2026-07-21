"""
AutoPrompt / APE: Gradient-Free Prompt Search via LLM Self-Reflection
======================================================================
The original AutoPrompt (Shin 2020) required gradient access to the model
weights — it only works with open-source models where you control the
forward pass. It cannot be used with API-based LLMs.

The practical 2024 equivalent is APE (Automatic Prompt Engineer, Zhou 2022):

  1. GENERATE  — show the LLM a handful of (input, output) examples and ask it
                 to write N candidate instruction prompts that would produce
                 those outputs.
  2. SCORE     — run each candidate instruction on a validation set and measure
                 accuracy (or any other metric).
  3. SELECT    — return the highest-scoring instruction.

Optional: REFINE — take the best instruction back to the LLM and ask it to
                   improve it ("iterative APE" / gradient-free refinement).

This file implements APE from scratch using the Anthropic Claude API so you
can see exactly what's happening at each step.

Task: Vietnamese e-commerce review → NEG / NEU / POS

Install:
    pip install anthropic python-dotenv

Run (dry-run, prints the APE prompts without API calls):
    python ape_optimizer.py

Run (real search):
    ANTHROPIC_API_KEY=sk-ant-... python ape_optimizer.py --optimize
    ANTHROPIC_API_KEY=sk-ant-... python ape_optimizer.py --optimize --n-candidates 5 --refine
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass

try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False


# ── Data ──────────────────────────────────────────────────────────────────────
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
]

VAL = [
    Example("Tuyệt vời, mình sẽ mua lại!", "POS"),
    Example("Thất vọng, không đúng màu sắc.", "NEG"),
    Example("Bình thường, đúng mô tả.", "NEU"),
    Example("Shop nhiệt tình, hàng đẹp.", "POS"),
    Example("Giao hàng sai địa chỉ, phải chờ thêm 3 ngày.", "NEG"),
]

# Starting instruction (what APE tries to improve on)
SEED_INSTRUCTION = "Classify the sentiment of this Vietnamese text."

MODEL = "claude-haiku-4-5-20251001"  # cheap, fast; swap to sonnet/opus for quality


# ── Step 1: GENERATE candidate instructions ────────────────────────────────────
GENERATE_PROMPT = """\
You are an expert prompt engineer. Your job is to write clear, specific instruction prompts for a sentiment classification task.

Here are some labeled examples of Vietnamese e-commerce reviews:

{examples}

Write {n} distinct instruction prompts (one per line, numbered) that would cause an LLM to correctly classify Vietnamese reviews as NEG (negative), NEU (neutral), or POS (positive).

Rules:
- Each instruction should be a single sentence or two.
- Be specific about the output format (must output exactly one of: NEG, NEU, POS).
- Vary the wording, framing, and emphasis across candidates.
- Output ONLY the numbered list, no other text.
"""


def build_few_shot_block(examples: list[Example]) -> str:
    lines = []
    for ex in examples:
        lines.append(f"  Review : {ex.text}")
        lines.append(f"  Label  : {ex.label}")
        lines.append("")
    return "\n".join(lines)


def generate_candidates(client: "anthropic.Anthropic", n: int) -> list[str]:
    examples_block = build_few_shot_block(TRAIN)
    prompt = GENERATE_PROMPT.format(examples=examples_block, n=n)

    print(f"  Asking {MODEL} to generate {n} candidate instructions...")
    response = client.messages.create(
        model=MODEL,
        max_tokens=600,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = response.content[0].text.strip()

    # Parse numbered list: "1. ...", "2. ..."
    candidates = []
    for line in raw.splitlines():
        line = line.strip()
        if line and line[0].isdigit() and ". " in line:
            candidates.append(line.split(". ", 1)[1].strip())

    # Fallback: include seed instruction so we always have at least one
    if not candidates:
        candidates = [SEED_INSTRUCTION]
    return candidates


# ── Step 2: SCORE each instruction on the validation set ──────────────────────
CLASSIFY_PROMPT = """\
{instruction}

Review: {text}

Respond with exactly one word: NEG, NEU, or POS."""


def classify(client: "anthropic.Anthropic", instruction: str, text: str) -> str:
    prompt = CLASSIFY_PROMPT.format(instruction=instruction, text=text)
    response = client.messages.create(
        model=MODEL,
        max_tokens=5,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = response.content[0].text.strip().upper()
    for label in ("NEG", "NEU", "POS"):
        if label in raw:
            return label
    return raw


def score_instruction(client: "anthropic.Anthropic", instruction: str) -> float:
    correct = 0
    for ex in VAL:
        pred = classify(client, instruction, ex.text)
        if pred == ex.label:
            correct += 1
    return correct / len(VAL)


# ── Step 3 (optional): REFINE the best instruction ────────────────────────────
REFINE_PROMPT = """\
You are an expert prompt engineer. Below is an instruction prompt for a Vietnamese sentiment classification task:

INSTRUCTION:
{instruction}

ACCURACY: {accuracy:.0%} on a 5-example validation set

Some predictions were wrong. Your task is to rewrite the instruction to be more accurate.
The output must still be exactly one of: NEG, NEU, POS.

Respond with ONLY the improved instruction, no other text."""


def refine_instruction(
    client: "anthropic.Anthropic",
    instruction: str,
    accuracy: float,
) -> str:
    prompt = REFINE_PROMPT.format(instruction=instruction, accuracy=accuracy)
    print(f"\n  Refining best instruction (current accuracy: {accuracy:.0%})...")
    response = client.messages.create(
        model=MODEL,
        max_tokens=200,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text.strip()


# ── Dry-run: show the prompts without calling the API ──────────────────────────
def dry_run() -> None:
    print("=== APE Optimizer — Dry Run (no API call) ===\n")

    print("── Step 1: GENERATE candidate instructions ──")
    print("Prompt sent to LLM:")
    print("-" * 60)
    examples_block = build_few_shot_block(TRAIN[:2])
    print(GENERATE_PROMPT.format(examples=examples_block, n=3))
    print("-" * 60)
    print()

    print("── Step 2: SCORE each candidate ──")
    print("For each candidate instruction, run this prompt on every VAL example:")
    print("-" * 60)
    print(CLASSIFY_PROMPT.format(
        instruction="<candidate instruction>",
        text=VAL[0].text,
    ))
    print("-" * 60)
    print()

    print("── Step 3: REFINE (optional) ──")
    print("Feed the best instruction + its accuracy back to the LLM:")
    print("-" * 60)
    print(REFINE_PROMPT.format(
        instruction=SEED_INSTRUCTION,
        accuracy=0.6,
    ))
    print("-" * 60)
    print()
    print("Run with --optimize to see real results.")


# ── Full APE run ───────────────────────────────────────────────────────────────
def run_ape(n_candidates: int, do_refine: bool) -> None:
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    # ── 1. Generate ──────────────────────────────────────────────────────────
    print("\n=== Step 1: Generate candidate instructions ===")
    candidates = generate_candidates(client, n=n_candidates)
    # Always include the seed so we have a baseline
    if SEED_INSTRUCTION not in candidates:
        candidates.insert(0, SEED_INSTRUCTION)

    for i, c in enumerate(candidates, 1):
        print(f"  [{i}] {c}")

    # ── 2. Score ─────────────────────────────────────────────────────────────
    print(f"\n=== Step 2: Score {len(candidates)} candidates on {len(VAL)}-example validation set ===")
    results: list[tuple[float, str]] = []
    for i, instruction in enumerate(candidates, 1):
        print(f"  Scoring [{i}/{len(candidates)}]: {instruction[:60]}...")
        acc = score_instruction(client, instruction)
        results.append((acc, instruction))
        print(f"    → accuracy: {acc:.0%}")

    results.sort(reverse=True)
    best_acc, best_instruction = results[0]

    print(f"\n=== Best instruction (accuracy: {best_acc:.0%}) ===")
    print(f"  {best_instruction}")

    # ── 3. Refine (optional) ──────────────────────────────────────────────────
    if do_refine:
        print("\n=== Step 3: Refine best instruction ===")
        refined = refine_instruction(client, best_instruction, best_acc)
        print(f"  Refined: {refined}")

        print(f"\n  Re-scoring refined instruction...")
        refined_acc = score_instruction(client, refined)
        print(f"  Refined accuracy: {refined_acc:.0%}  (was {best_acc:.0%})")

        if refined_acc > best_acc:
            best_instruction = refined
            best_acc = refined_acc
            print("  Refinement improved accuracy — using refined instruction.")
        else:
            print("  Original instruction retained.")

    print(f"\n=== Final prompt ===")
    print(f"  {best_instruction}")
    print(f"  Accuracy: {best_acc:.0%} on {len(VAL)}-example validation set")

    # Save to a file so you can paste it into production
    out = {"instruction": best_instruction, "accuracy": best_acc}
    with open("best_instruction.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print("\n  Saved to best_instruction.json")


# ── Entry point ────────────────────────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--optimize", action="store_true",
                        help="Run real optimization (requires ANTHROPIC_API_KEY)")
    parser.add_argument("--n-candidates", type=int, default=4,
                        help="Number of candidate instructions to generate (default: 4)")
    parser.add_argument("--refine", action="store_true",
                        help="Refine the best instruction after scoring")
    args = parser.parse_args()

    if not args.optimize:
        dry_run()
        print("\nTo run: ANTHROPIC_API_KEY=sk-ant-... python ape_optimizer.py --optimize")
        return

    if not HAS_ANTHROPIC:
        print("anthropic not installed. Run: pip install anthropic")
        sys.exit(1)

    if not os.getenv("ANTHROPIC_API_KEY"):
        print("Set ANTHROPIC_API_KEY first.")
        sys.exit(1)

    run_ape(n_candidates=args.n_candidates, do_refine=args.refine)


if __name__ == "__main__":
    main()
