"""
In-memory knowledge graph built with networkx.

Multi-agent nodes read/write through this module-level singleton so the
graph persists across LangGraph invocations within a single process.
"""

from __future__ import annotations

import networkx as nx


class KnowledgeGraph:
    def __init__(self) -> None:
        self.graph = nx.MultiDiGraph()

    def add_triple(self, subject: str, relation: str, obj: str) -> None:
        self.graph.add_node(subject)
        self.graph.add_node(obj)
        self.graph.add_edge(subject, obj, relation=relation)

    def add_triples(self, triples: list[tuple[str, str, str]]) -> None:
        for s, r, o in triples:
            self.add_triple(s, r, o)

    def neighbors(self, entity: str) -> list[tuple[str, str, str]]:
        """Outgoing (entity, relation, target) edges for entity."""
        out = []
        if entity in self.graph:
            for _, target, data in self.graph.out_edges(entity, data=True):
                out.append((entity, data["relation"], target))
        return out

    def subgraph_for(self, entities: list[str], hops: int = 2) -> list[tuple[str, str, str]]:
        """Collect triples within `hops` of any seed entity (undirected BFS)."""
        undirected = self.graph.to_undirected(as_view=True)
        seen_nodes: set[str] = set()
        for entity in entities:
            if entity not in undirected:
                continue
            seen_nodes |= nx.single_source_shortest_path_length(undirected, entity, cutoff=hops).keys()

        triples = []
        for u, v, data in self.graph.edges(data=True):
            if u in seen_nodes and v in seen_nodes:
                triples.append((u, data["relation"], v))
        return triples

    def find_path(self, source: str, target: str) -> list[str] | None:
        try:
            return nx.shortest_path(self.graph.to_undirected(as_view=True), source, target)
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return None

    def stats(self) -> str:
        return f"{self.graph.number_of_nodes()} entities, {self.graph.number_of_edges()} relations"

    def entities(self) -> list[str]:
        return list(self.graph.nodes)

    def draw(self, path: str = "knowledge_graph.png") -> None:
        import matplotlib.pyplot as plt

        pos = nx.spring_layout(self.graph, seed=42)
        plt.figure(figsize=(10, 7))
        nx.draw(self.graph, pos, with_labels=True, node_color="#8ecae6", node_size=1500, font_size=8, arrows=True)
        edge_labels = {(u, v): d["relation"] for u, v, d in self.graph.edges(data=True)}
        nx.draw_networkx_edge_labels(self.graph, pos, edge_labels=edge_labels, font_size=7)
        plt.tight_layout()
        plt.savefig(path, dpi=150)
        plt.close()


# Module-level singleton shared by all agent nodes within a process.
kg = KnowledgeGraph()
