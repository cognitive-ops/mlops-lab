"""Context engineering sample: assemble a prompt under a token budget.

Techniques shown:
  1. Prioritized sections (system > task > retrieved docs > memory > history)
  2. Token budgeting with per-section caps
  3. Retrieval ranking + dedup
  4. History compression (keep recent turns verbatim, summarize older ones)
  5. Structured (XML-tagged) layout for the model
"""
from __future__ import annotations

from dataclasses import dataclass, field


def count_tokens(text: str) -> int:
    """Rough estimate (~4 chars/token). Swap for tiktoken / API token counting."""
    return max(1, len(text) // 4)


def truncate_to_tokens(text: str, max_tokens: int) -> str:
    max_chars = max_tokens * 4
    return text if len(text) <= max_chars else text[: max_chars - 3] + "..."


@dataclass
class Doc:
    id: str
    text: str
    score: float  # retrieval relevance


@dataclass
class Turn:
    role: str  # "user" | "assistant"
    content: str


@dataclass
class ContextBuilder:
    max_tokens: int = 2000
    reserve_for_output: int = 500
    keep_recent_turns: int = 4
    caps: dict = field(default_factory=lambda: {
        "docs": 0.45,     # share of remaining budget
        "history": 0.30,
        "memory": 0.10,
    })

    # ---- section builders -------------------------------------------------
    def _select_docs(self, docs: list[Doc], budget: int) -> str:
        seen, picked, used = set(), [], 0
        for d in sorted(docs, key=lambda d: d.score, reverse=True):
            key = d.text.strip().lower()
            if key in seen:  # dedup
                continue
            cost = count_tokens(d.text)
            if used + cost > budget:
                continue  # skip what doesn't fit, try smaller ones
            seen.add(key)
            picked.append(f'<doc id="{d.id}" score="{d.score:.2f}">{d.text}</doc>')
            used += cost
        return "\n".join(picked)

    def _compress_history(self, turns: list[Turn], budget: int) -> str:
        recent = turns[-self.keep_recent_turns:]
        older = turns[: -self.keep_recent_turns]
        parts = []
        if older:
            # Placeholder summary. In production: call a cheap LLM to summarize.
            gist = "; ".join(f"{t.role}: {t.content[:60]}" for t in older)
            parts.append(f"<summary>{gist}</summary>")
        parts += [f"<turn role=\"{t.role}\">{t.content}</turn>" for t in recent]
        return truncate_to_tokens("\n".join(parts), budget)

    # ---- main -------------------------------------------------------------
    def build(
        self,
        system: str,
        task: str,
        docs: list[Doc],
        history: list[Turn],
        memory: list[str],
    ) -> str:
        # Fixed, non-negotiable sections first
        fixed = count_tokens(system) + count_tokens(task)
        remaining = self.max_tokens - self.reserve_for_output - fixed
        if remaining <= 0:
            raise ValueError("System + task exceed budget")

        docs_txt = self._select_docs(docs, int(remaining * self.caps["docs"]))
        hist_txt = self._compress_history(history, int(remaining * self.caps["history"]))
        mem_txt = truncate_to_tokens("\n".join(f"- {m}" for m in memory),
                                     int(remaining * self.caps["memory"]))

        # Layout: stable prefix first (cache-friendly), volatile content last,
        # task at the end (models weight the end of the prompt heavily).
        return "\n\n".join([
            f"<system>\n{system}\n</system>",
            f"<memory>\n{mem_txt}\n</memory>",
            f"<documents>\n{docs_txt}\n</documents>",
            f"<history>\n{hist_txt}\n</history>",
            f"<task>\n{task}\n</task>",
        ])


# ---- demo -----------------------------------------------------------------
if __name__ == "__main__":
    builder = ContextBuilder(max_tokens=1200, reserve_for_output=300)

    docs = [
        Doc("kb-1", "Claims over $10k need senior adjuster approval.", 0.92),
        Doc("kb-2", "Claims over $10k need senior adjuster approval.", 0.90),  # dup
        Doc("kb-3", "Auto FNOL must include police report number.", 0.75),
        Doc("kb-4", "Office hours are 9-5." * 20, 0.20),  # low value, bulky
    ]
    history = [Turn("user" if i % 2 == 0 else "assistant", f"message {i} " * 5)
               for i in range(10)]
    memory = ["User is a claims triage agent", "Prefers concise answers"]

    prompt = builder.build(
        system="You are a claims assistant. Answer only from <documents>.",
        task="Does a $15k auto claim need extra approval?",
        docs=docs,
        history=history,
        memory=memory,
    )
    print(prompt)
    print(f"\n~{count_tokens(prompt)} tokens (budget {builder.max_tokens})")

    # Send to Claude (needs `pip install anthropic` + ANTHROPIC_API_KEY):
    # import anthropic
    # client = anthropic.Anthropic()
    # resp = client.messages.create(
    #     model="claude-sonnet-5-5",
    #     max_tokens=builder.reserve_for_output,
    #     messages=[{"role": "user", "content": prompt}],
    # )
    # print(resp.content[0].text)
