import json
from pathlib import Path
from collections import deque


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

        # --------------------------------------------------
        # Build bidirectional adjacency list
        # --------------------------------------------------

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


    # ======================================================
    # Edge weighting
    # ======================================================

    @staticmethod
    def _edge_weight(edge_type):

        """
        Assign different strengths to different
        code relationships.

        INHERITS_METHOD is especially important because
        it connects an API-facing implementation to the
        method where the behavior is defined.
        """

        weights = {

            # Strong relationship:
            # subclass method -> inherited/base method
            "INHERITS_METHOD": 2.0,

            # Direct function/method invocation
            "CALLS": 1.5,

            # Module/class import relationship
            "IMPORTS": 1.0,

            # Defines is deliberately not traversed.
            "DEFINES": 0.0
        }

        return weights.get(
            edge_type,
            1.0
        )


    # ======================================================
    # Graph search
    # ======================================================

    def search(
        self,
        seed_names,
        top_k=5,
        max_depth=2
    ):

        scores = {}

        queue = deque()

        # --------------------------------------------------
        # Track the shortest known distance.
        # --------------------------------------------------

        visited_distance = {}

        # --------------------------------------------------
        # Start from seed symbols
        # --------------------------------------------------

        for seed_name in seed_names:

            if seed_name not in self.node_by_name:
                continue

            queue.append(
                (
                    seed_name,
                    0
                )
            )

            visited_distance[
                seed_name
            ] = 0


        # --------------------------------------------------
        # Breadth-first graph traversal
        # --------------------------------------------------

        while queue:

            current, depth = queue.popleft()

            if depth >= max_depth:
                continue

            for edge in self.neighbors.get(
                current,
                []
            ):

                edge_type = edge["type"]

                # ------------------------------------------
                # DEFINES is not useful for retrieval.
                # ------------------------------------------

                if edge_type == "DEFINES":
                    continue

                # ------------------------------------------
                # Determine neighboring node.
                # ------------------------------------------

                if edge["source"] == current:

                    neighbor = edge["target"]

                else:

                    neighbor = edge["source"]

                if neighbor == current:
                    continue

                # ------------------------------------------
                # Distance
                # ------------------------------------------

                distance = depth + 1

                # ------------------------------------------
                # Edge-specific relationship strength
                # ------------------------------------------

                edge_weight = self._edge_weight(
                    edge_type
                )

                # ------------------------------------------
                # Distance decay
                # ------------------------------------------

                score = (
                    edge_weight
                    / distance
                )

                scores[neighbor] = (
                    scores.get(
                        neighbor,
                        0.0
                    )
                    + score
                )

                # ------------------------------------------
                # Continue traversal only when this node
                # has not already been reached at an
                # equal or shorter distance.
                # ------------------------------------------

                previous_distance = (
                    visited_distance.get(
                        neighbor
                    )
                )

                if (
                    previous_distance is None
                    or distance < previous_distance
                ):

                    visited_distance[
                        neighbor
                    ] = distance

                    queue.append(
                        (
                            neighbor,
                            distance
                        )
                    )


        # --------------------------------------------------
        # Ranking
        # --------------------------------------------------

        ranked = sorted(
            scores.items(),
            key=lambda item: item[1],
            reverse=True
        )


        # --------------------------------------------------
        # Build results
        # --------------------------------------------------

        results = []

        for qualified_name, score in ranked[
            :top_k
        ]:

            node = self.node_by_name.get(
                qualified_name
            )

            if node is None:
                continue

            results.append(
                {
                    "qualified_name":
                        qualified_name,

                    "type":
                        node["type"],

                    "file":
                        node["file"],

                    "line":
                        node["line"],

                    "graph_score":
                        score,
                }
            )

        return results


# ==========================================================
# Test
# ==========================================================

if __name__ == "__main__":

    retriever = GraphRetriever()

    seed_names = [

        "Flask.full_dispatch_request",

        "Flask.dispatch_request",

        "Flask.wsgi_app",

    ]

    results = retriever.search(
        seed_names,
        top_k=10,
        max_depth=2
    )

    print(
        "\nGraph Results:\n"
    )

    for rank, result in enumerate(
        results,
        start=1
    ):

        print(
            f"{rank}. "
            f"{result['qualified_name']} "
            f"| Graph="
            f"{result['graph_score']:.3f} "
            f"| "
            f"{result['file']}:"
            f"{result['line']}"
        )