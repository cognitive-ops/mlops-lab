"""
Extractor agent — turns raw text into (subject, relation, object) triples
and writes them into the shared knowledge graph.
"""

from typing import List, Tuple

from langchain_core.messages import AIMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from kg import kg
from state import GraphState


class Triple(BaseModel):
    subject: str
    relation: str
    object: str


class ExtractionResult(BaseModel):
    triples: List[Triple] = Field(description="Entity-relation-entity triples found in the text")


_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
_structured_llm = _llm.with_structured_output(ExtractionResult)

_PROMPT = """Extract factual (subject, relation, object) triples from the text below.
Keep entity names short and canonical (e.g. "OpenAI" not "the company OpenAI").
Keep relations short, lowercase, verb-like (e.g. "founded_by", "works_at", "acquired").

Text:
{text}
"""


def extractor_node(state: GraphState) -> dict:
    text = state["input_text"]
    result: ExtractionResult = _structured_llm.invoke(_PROMPT.format(text=text))

    triples: List[Tuple[str, str, str]] = [(t.subject, t.relation, t.object) for t in result.triples]
    kg.add_triples(triples)

    summary = f"Extracted {len(triples)} triples. KG now has {kg.stats()}."
    return {
        "extracted_triples": triples,
        "mode": "FINISH",
        "messages": [AIMessage(content=summary)],
    }
