"""
Knowledge graph backed by Neo4j.

Multi-agent nodes read/write through this module-level singleton. Connection
config comes from env vars:

    NEO4J_URI       default: bolt://localhost:7687
    NEO4J_USER      default: neo4j
    NEO4J_PASSWORD  default: password

Run `docker-compose up -d` in this folder to start a local Neo4j instance.
"""

from __future__ import annotations

import os
import re

from neo4j import GraphDatabase


def _sanitize_relation(relation: str) -> str:
    """Cypher relationship types can't be parameterized, so validate/normalize
    before interpolating into a query string (prevents Cypher injection)."""
    sanitized = re.sub(r"[^A-Za-z0-9_]", "_", relation).upper().strip("_") or "RELATED_TO"
    if not sanitized[0].isalpha():
        sanitized = f"REL_{sanitized}"
    return sanitized


class KnowledgeGraph:
    def __init__(self) -> None:
        uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
        user = os.environ.get("NEO4J_USER", "neo4j")
        password = os.environ.get("NEO4J_PASSWORD", "password")
        self._driver = GraphDatabase.driver(uri, auth=(user, password))
        self._ensure_constraints()

    def close(self) -> None:
        self._driver.close()

    def _ensure_constraints(self) -> None:
        with self._driver.session() as session:
            session.run(
                "CREATE CONSTRAINT entity_name IF NOT EXISTS "
                "FOR (e:Entity) REQUIRE e.name IS UNIQUE"
            )

    def add_triple(self, subject: str, relation: str, obj: str) -> None:
        rel_type = _sanitize_relation(relation)
        query = (
            "MERGE (s:Entity {name: $subject}) "
            "MERGE (o:Entity {name: $object}) "
            f"MERGE (s)-[r:{rel_type}]->(o) "
            "SET r.label = $relation"
        )
        with self._driver.session() as session:
            session.run(query, subject=subject, object=obj, relation=relation)

    def add_triples(self, triples: list[tuple[str, str, str]]) -> None:
        for s, r, o in triples:
            self.add_triple(s, r, o)

    def neighbors(self, entity: str) -> list[tuple[str, str, str]]:
        """Outgoing (entity, relation, target) edges for entity."""
        query = (
            "MATCH (e:Entity {name: $entity})-[r]->(t:Entity) "
            "RETURN e.name AS s, coalesce(r.label, type(r)) AS r, t.name AS o"
        )
        with self._driver.session() as session:
            return [(rec["s"], rec["r"], rec["o"]) for rec in session.run(query, entity=entity)]

    def subgraph_for(self, entities: list[str], hops: int = 2) -> list[tuple[str, str, str]]:
        """Collect triples within `hops` of any seed entity."""
        if not entities:
            return []
        query = (
            "MATCH (seed:Entity) WHERE seed.name IN $entities "
            f"MATCH (seed)-[*0..{hops}]-(other:Entity) "
            "WITH collect(DISTINCT other) AS nodes "
            "UNWIND nodes AS n1 "
            "MATCH (n1)-[r]->(n2) WHERE n2 IN nodes "
            "RETURN DISTINCT n1.name AS s, coalesce(r.label, type(r)) AS r, n2.name AS o"
        )
        with self._driver.session() as session:
            return [(rec["s"], rec["r"], rec["o"]) for rec in session.run(query, entities=entities)]

    def find_path(self, source: str, target: str) -> list[str] | None:
        query = (
            "MATCH p = shortestPath((a:Entity {name: $source})-[*]-(b:Entity {name: $target})) "
            "RETURN [n IN nodes(p) | n.name] AS path"
        )
        with self._driver.session() as session:
            rec = session.run(query, source=source, target=target).single()
            return rec["path"] if rec else None

    def stats(self) -> str:
        query = "MATCH (n:Entity) OPTIONAL MATCH ()-[r]->() RETURN count(DISTINCT n) AS nodes, count(r) AS edges"
        with self._driver.session() as session:
            rec = session.run(query).single()
            return f"{rec['nodes']} entities, {rec['edges']} relations"

    def entities(self) -> list[str]:
        query = "MATCH (n:Entity) RETURN n.name AS name"
        with self._driver.session() as session:
            return [rec["name"] for rec in session.run(query)]


# Module-level singleton shared by all agent nodes within a process.
kg = KnowledgeGraph()
