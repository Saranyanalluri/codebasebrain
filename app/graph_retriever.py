import json
from pathlib import Path


GRAPH_PATH = Path(
    "data/indexes/code_graph.json"
)


class GraphRetriever:
    def __init__(self, graph_path=GRAPH_PATH):
        with open(
            graph_path,
            "r",
            encoding="utf-8"
        ) as file:
            graph = json.load(file)

        self.nodes = graph["nodes"]
        self.edges = graph["edges"]

        self.node_by_name = {
            node["qualified_name"]: node
            for node in self.nodes
        }

        self.neighbors = {}

        for edge in self.edges:
            source = edge["source"]
            target = edge["target"]

            self.neighbors.setdefault(
                source,
                []
            ).append(edge)

            self.neighbors.setdefault(
                target,
                []
            ).append(edge)

    def search(
        self,
        seed_names,
        top_k=5
    ):
        scores = {}

        for seed_name in seed_names:

            if seed_name not in self.neighbors:
                continue

            for edge in self.neighbors[seed_name]:

                if edge["type"] == "DEFINES":
                    continue

                if edge["source"] == seed_name:
                    neighbor = edge["target"]
                else:
                    neighbor = edge["source"]

                if neighbor == seed_name:
                    continue

                scores.setdefault(
                    neighbor,
                    0
                )

                scores[neighbor] += 1

        ranked = sorted(
            scores.items(),
            key=lambda item: item[1],
            reverse=True
        )

        results = []

        for qualified_name, score in ranked[:top_k]:

            node = self.node_by_name.get(
                qualified_name
            )

            if node is None:
                continue

            results.append(
                {
                    "qualified_name": qualified_name,
                    "type": node["type"],
                    "file": node["file"],
                    "line": node["line"],
                    "graph_score": score,
                }
            )

        return results


if __name__ == "__main__":

    retriever = GraphRetriever()

    seed_names = [
        "Flask.full_dispatch_request",
        "Flask.dispatch_request",
        "Flask.wsgi_app",
    ]

    results = retriever.search(
        seed_names,
        top_k=10
    )

    print("\nGraph Results:\n")

    for rank, result in enumerate(
        results,
        start=1
    ):
        print(
            f"{rank}. "
            f"{result['qualified_name']} "
            f"| Graph={result['graph_score']} "
            f"| {result['file']}:{result['line']}"
        )