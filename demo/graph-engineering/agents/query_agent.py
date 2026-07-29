"""
Query agent — answers questions by retrieving a bounded subgraph around the
entities mentioned in the question, then grounding the LLM's answer in it.

This is "Graph-RAG": retrieval over graph structure instead of vector search,
which makes the reasoning path (which facts led to the answer) inspectable.
"""

from typing import List

from langchain_core.messages import AIMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from kg import kg
from state import GraphState


class EntityMentions(BaseModel):
    entities: List[str] = Field(
        description="Entity names from the knowledge graph mentioned or implied in the question"
    )


_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
_entity_llm = _llm.with_structured_output(EntityMentions)

_ENTITY_PROMPT = """Known entities in the knowledge graph: {entities}

Question: {question}

Which of the known entities above are relevant to answering this question?
"""

_ANSWER_PROMPT = """Answer the question using ONLY the facts below. If the facts
are insufficient, say so explicitly rather than guessing.

Facts (subject, relation, object):
{facts}

Question: {question}
"""


def query_node(state: GraphState) -> dict:
    question = state["question"]

    mention_result = _entity_llm.invoke(
        _ENTITY_PROMPT.format(entities=", ".join(kg.entities()), question=question)
    )
    seed_entities = [e for e in mention_result.entities if e in kg.entities()]

    retrieved = kg.subgraph_for(seed_entities, hops=2) if seed_entities else []
    facts_text = "\n".join(f"- {s} {r} {o}" for s, r, o in retrieved) or "(no relevant facts found)"

    answer = _llm.invoke(_ANSWER_PROMPT.format(facts=facts_text, question=question)).content

    return {
        "retrieved_triples": retrieved,
        "final_answer": answer,
        "mode": "FINISH",
        "messages": [AIMessage(content=answer)],
    }
