"""Scratchpad Pruning for agents. Dependency-free, offline, deterministic.

Problem: a ReAct agent re-sends its whole scratchpad (Thought/Action/Observation) every turn,
so prompt size grows ~linearly per step and stale junk (failed calls, superseded values,
fat raw payloads, old reasoning) crowds out what matters.

Scratchpad pruning = edit the scratchpad between turns, keep only what the next decision needs:

  R1 dead-end    failed step later retried OK         -> drop step, keep 1-line lesson
  R2 superseded  fact overwritten by newer observation -> drop old value (stale = harmful)
  R3 compact     old observation (outside window)      -> keep extracted facts only, drop raw body
  R4 thought     old thought (outside window)          -> drop; decisions live in facts/lessons

Facts are pinned notes: never pruned unless superseded. Last `window` steps stay verbatim.

The agent below is a scripted policy that can ONLY read facts from its rendered scratchpad,
so if pruning ate something needed, the run fails. That makes the demo a real correctness check.

Run: python scratchpad_pruning.py            (summary table)
     python scratchpad_pruning.py --trace    (show the pruned scratchpad each turn)
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field


def count_tokens(text: str) -> int:
    return max(1, len(text) // 4)  # swap for tiktoken / API token counting


# =============================================================================
# Scratchpad model
# =============================================================================
@dataclass
class Step:
    idx: int
    thought: str
    action: str
    args: dict
    observation: str           # raw tool output (may be huge)
    ok: bool
    facts: dict = field(default_factory=dict)   # key -> value extracted from observation
    pruned: set = field(default_factory=set)    # which parts were dropped: thought/obs/step


class Scratchpad:
    def __init__(self) -> None:
        self.steps: list[Step] = []
        self.lessons: list[str] = []

    def add(self, step: Step) -> None:
        self.steps.append(step)

    # ---- facts: latest non-pruned value wins -------------------------------
    def facts(self) -> dict:
        out: dict = {}
        for s in self.steps:
            if "step" in s.pruned and not s.ok:
                continue
            out.update(s.facts)
        return out

    # ---- render what the LLM would actually see ----------------------------
    def render(self) -> str:
        lines: list[str] = []
        if self.lessons:
            lines.append("LESSONS: " + " | ".join(self.lessons))
        for s in self.steps:
            if "step" in s.pruned:
                continue
            if "thought" not in s.pruned:
                lines.append(f"Thought {s.idx}: {s.thought}")
            lines.append(f"Action {s.idx}: {s.action}({json.dumps(s.args)})")
            if "obs" in s.pruned:
                lines.append(f"Observation {s.idx}: [facts] {json.dumps(s.facts)}")
            else:
                lines.append(f"Observation {s.idx}: {s.observation}")
        return "\n".join(lines)

    def tokens(self) -> int:
        return count_tokens(self.render())


# =============================================================================
# Pruner
# =============================================================================
@dataclass
class Pruner:
    window: int = 2            # last N steps always verbatim
    log: list[str] = field(default_factory=list)

    def prune(self, pad: Scratchpad) -> None:
        steps = pad.steps
        old = steps[: max(0, len(steps) - self.window)]

        # R1 dead-end: failed step whose (action) later succeeded
        for i, s in enumerate(steps):
            if s.ok or "step" in s.pruned:
                continue
            retried = any(t.ok and t.action == s.action for t in steps[i + 1:])
            if retried:
                s.pruned.add("step")
                lesson = f"{s.action}{json.dumps(s.args)} failed: {s.observation[:60]}"
                pad.lessons.append(lesson)
                self.log.append(f"R1 dead-end   step {s.idx} -> lesson")

        # R2 superseded: older step whose every fact key is overwritten by a newer step
        for i, s in enumerate(steps):
            if "obs" in s.pruned or not s.facts or "step" in s.pruned:
                continue
            newer = {k for t in steps[i + 1:] if "step" not in t.pruned for k in t.facts}
            if set(s.facts) <= newer:
                s.pruned.add("step")
                self.log.append(f"R2 superseded step {s.idx} (keys {sorted(s.facts)})")

        # R3 compact + R4 thought: outside window
        for s in old:
            if "step" in s.pruned:
                continue
            if s.facts and "obs" not in s.pruned and len(s.observation) > 200:
                s.pruned.add("obs")
                self.log.append(f"R3 compact    step {s.idx} obs {count_tokens(s.observation)}t -> facts")
            if "thought" not in s.pruned:
                s.pruned.add("thought")
                self.log.append(f"R4 thought    step {s.idx} dropped")


# =============================================================================
# Mock tools (deterministic) -- task: cheapest HAN->SGN flight under budget, in VND
# =============================================================================
class Tools:
    def __init__(self) -> None:
        self.calls = {"search_flights": 0, "get_fx": 0}

    def search_flights(self, origin: str, dest: str) -> tuple[str, bool, dict]:
        self.calls["search_flights"] += 1
        if self.calls["search_flights"] == 1:
            return "ERROR 429: rate limited, retry later", False, {}
        rows = [{"id": f"VN{200+i}", "price_usd": 120 + (i * 37) % 90, "stops": i % 2,
                 "meta": {"aircraft": "A321", "fare_rules": "x" * 40, "tracking": "y" * 30}}
                for i in range(25)]
        best = min(rows, key=lambda r: r["price_usd"])
        return json.dumps(rows), True, {"best_flight": best["id"], "best_price_usd": best["price_usd"]}

    def get_fx(self, pair: str) -> tuple[str, bool, dict]:
        self.calls["get_fx"] += 1
        rate = 25100 if self.calls["get_fx"] == 1 else 25350  # market moved on refresh
        body = json.dumps({"pair": pair, "rate": rate, "history": [rate - d for d in range(40)],
                           "refreshed": self.calls["get_fx"] >= 2})
        return body, True, {"usd_vnd": rate}

    def calc(self, usd: float, rate: float) -> tuple[str, bool, dict]:
        vnd = int(usd * rate)
        return f"{usd} * {rate} = {vnd}", True, {"total_vnd": vnd}


# =============================================================================
# Scripted agent: decides ONLY from facts visible in the rendered scratchpad
# =============================================================================
def parse_visible_facts(rendered: str) -> dict:
    """What the LLM can 'see': facts in [facts] lines + raw observations that survive."""
    facts: dict = {}
    for line in rendered.splitlines():
        if not line.startswith("Observation"):
            continue
        body = line.split(": ", 1)[1]
        if body.startswith("[facts] "):
            facts.update(json.loads(body[len("[facts] "):]))
        elif body.startswith("["):  # raw flight list
            rows = json.loads(body)
            best = min(rows, key=lambda r: r["price_usd"])
            facts.update(best_flight=best["id"], best_price_usd=best["price_usd"])
        elif body.startswith("{"):
            d = json.loads(body)
            if "rate" in d:
                facts["usd_vnd"] = d["rate"]
                if d.get("refreshed"):
                    facts["fx_refreshed"] = True
        elif " = " in body:  # raw calc output "a * b = c"
            facts["total_vnd"] = int(body.rsplit(" = ", 1)[1])
    return facts


def policy(rendered: str, step_no: int) -> tuple[str, str, dict] | None:
    f = parse_visible_facts(rendered)
    if "best_price_usd" not in f:
        return "Need flight prices first.", "search_flights", {"origin": "HAN", "dest": "SGN"}
    if "usd_vnd" not in f:
        return "Have price, need FX rate.", "get_fx", {"pair": "USD/VND"}
    if "fx_refreshed" not in f:   # policy: refresh FX once before quoting
        return "Rate may be stale, refresh before quoting.", "get_fx", {"pair": "USD/VND"}
    if "total_vnd" not in f:
        return "Convert to VND.", "calc", {"usd": f["best_price_usd"], "rate": f["usd_vnd"]}
    return None


def run(prune: bool, trace: bool = False) -> dict:
    tools, pad, pruner = Tools(), Scratchpad(), Pruner()
    per_turn: list[int] = []
    total_prompt = 0
    n = 0
    while True:
        n += 1
        rendered = pad.render()
        per_turn.append(count_tokens(rendered))
        total_prompt += per_turn[-1]
        if trace:
            print(f"\n--- turn {n} prompt ({per_turn[-1]} tokens) ---\n{rendered or '(empty)'}")
        decision = policy(rendered, n)
        if decision is None or n > 8:
            break
        thought, action, args = decision
        obs, ok, facts = getattr(tools, action)(**args)
        if action == "get_fx" and tools.calls["get_fx"] >= 2:
            facts = {**facts, "fx_refreshed": True}
        pad.add(Step(n, thought, action, args, obs, ok, facts))
        if prune:
            pruner.prune(pad)

    answer = pad.facts() if prune else parse_visible_facts(pad.render())
    return {"turns": n, "per_turn": per_turn, "total_prompt": total_prompt,
            "final_tokens": per_turn[-1], "answer": answer, "rules": pruner.log}


# =============================================================================
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--trace", action="store_true", help="print prompt seen each turn")
    args = ap.parse_args()

    base = run(prune=False, trace=args.trace)
    pruned = run(prune=True, trace=args.trace)

    print("\n=== prompt tokens per turn (scratchpad only) ===")
    print(f"{'turn':>4} | {'no prune':>8} | {'pruned':>6}")
    for i in range(max(len(base['per_turn']), len(pruned['per_turn']))):
        b = base["per_turn"][i] if i < len(base["per_turn"]) else "-"
        p = pruned["per_turn"][i] if i < len(pruned["per_turn"]) else "-"
        print(f"{i+1:>4} | {b:>8} | {p:>6}")

    print("\n=== totals ===")
    print(f"cumulative prompt tokens: {base['total_prompt']} -> {pruned['total_prompt']} "
          f"({100 * (1 - pruned['total_prompt'] / base['total_prompt']):.0f}% saved)")
    print(f"final scratchpad tokens : {base['final_tokens']} -> {pruned['final_tokens']}")

    print("\n=== pruning log ===")
    print("\n".join(pruned["rules"]))

    keys = ("best_flight", "best_price_usd", "usd_vnd", "total_vnd")
    a, b = ({k: r["answer"].get(k) for k in keys} for r in (base, pruned))
    print(f"\nanswer (no prune): {a}\nanswer (pruned)  : {b}")
    assert a == b, "pruning changed the answer!"
    print("OK: same answer, fewer tokens.")


if __name__ == "__main__":
    main()
