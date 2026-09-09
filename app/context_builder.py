import json
from pathlib import Path


DOCUMENTS_PATH = Path(
    "data/indexes/code_documents.json"
)

GRAPH_PATH = Path(
    "data/indexes/code_graph.json"
)


class ContextBuilder:
    """
    Builds structured, graph-aware context from
    retrieval results.
    """

    def __init__(
        self,
        documents_path=DOCUMENTS_PATH,
        graph_path=GRAPH_PATH
    ):

        self.documents_path = Path(
            documents_path
        )

        self.graph_path = Path(
            graph_path
        )

        # --------------------------------------------------
        # Load code documents
        # --------------------------------------------------

        with open(
            self.documents_path,
            "r",
            encoding="utf-8"
        ) as file:

            self.documents = json.load(file)

        self.documents_by_id = {
            document["id"]: document
            for document in self.documents
        }

        # --------------------------------------------------
        # Load code graph
        # --------------------------------------------------

        with open(
            self.graph_path,
            "r",
            encoding="utf-8"
        ) as file:

            self.graph = json.load(file)

        self.nodes = self.graph.get(
            "nodes",
            []
        )

        self.edges = self.graph.get(
            "edges",
            []
        )

        # --------------------------------------------------
        # Build relationship lookup
        # --------------------------------------------------

        self.relationships = {}

        for edge in self.edges:

            source = edge.get(
                "source"
            )

            target = edge.get(
                "target"
            )

            edge_type = edge.get(
                "type"
            )

            if not source or not target:
                continue

            # Outgoing relationship
            self.relationships.setdefault(
                source,
                []
            ).append({
                "direction": "outgoing",
                "type": edge_type,
                "target": target
            })

            # Incoming relationship
            self.relationships.setdefault(
                target,
                []
            ).append({
                "direction": "incoming",
                "type": edge_type,
                "source": source
            })

    # ======================================================
    # Graph helpers
    # ======================================================

    def get_relationships(
        self,
        qualified_name
    ):
        """
        Return graph relationships connected
        to a symbol.
        """

        return self.relationships.get(
            qualified_name,
            []
        )

    def _format_relationship(
        self,
        relationship
    ):

        direction = relationship.get(
            "direction"
        )

        edge_type = relationship.get(
            "type"
        )

        if direction == "outgoing":

            target = relationship.get(
                "target"
            )

            return (
                f"{edge_type}: "
                f"{target}"
            )

        source = relationship.get(
            "source"
        )

        return (
            f"{edge_type}: "
            f"{source}"
        )

    # ======================================================
    # Build structured context
    # ======================================================

    def build(
        self,
        query,
        results,
        max_results=5
    ):

        context_results = []

        for result in results[:max_results]:

            document_id = result.get(
                "document_id"
            )

            document = self.documents_by_id.get(
                document_id
            )

            if document is None:
                continue

            qualified_name = result.get(
                "qualified_name"
            )

            graph_relationships = (
                self.get_relationships(
                    qualified_name
                )
            )

            context_results.append({

                "qualified_name":
                    qualified_name,

                "file":
                    result.get(
                        "file"
                    ),

                "line":
                    result.get(
                        "line"
                    ),

                "code":
                    document.get(
                        "text",
                        ""
                    ),

                "sources":
                    result.get(
                        "sources",
                        []
                    ),

                "evidence":
                    result.get(
                        "evidence",
                        {}
                    ),

                "explanation":
                    result.get(
                        "explanation",
                        []
                    ),

                "final_score":
                    result.get(
                        "final_score"
                    ),

                "graph_relationships":
                    graph_relationships
            })

        return {
            "query": query,
            "results": context_results
        }

    # ======================================================
    # Format context for LLM
    # ======================================================

    def format_for_llm(
        self,
        context
    ):

        sections = []

        sections.append(
            f"User Question:\n"
            f"{context['query']}"
        )

        sections.append(
            "\nRetrieved Code Context:"
        )

        for index, result in enumerate(
            context["results"],
            start=1
        ):

            sections.append(
                "\n"
                + "=" * 70
            )

            sections.append(
                f"Result {index}"
            )

            sections.append(
                f"Symbol: "
                f"{result['qualified_name']}"
            )

            sections.append(
                f"File: "
                f"{result['file']}"
            )

            sections.append(
                f"Line: "
                f"{result['line']}"
            )

            sections.append(
                f"Sources: "
                f"{', '.join(result['sources'])}"
            )

            # --------------------------------------------------
            # Graph relationships
            # --------------------------------------------------

            sections.append(
                "\nCode Graph Relationships:"
            )

            relationships = result.get(
                "graph_relationships",
                []
            )

            if relationships:

                for relationship in relationships:

                    sections.append(
                        "- "
                        + self._format_relationship(
                            relationship
                        )
                    )

            else:

                sections.append(
                    "- No graph relationships found"
                )

            # --------------------------------------------------
            # Code
            # --------------------------------------------------

            sections.append(
                "\nCode:"
            )

            sections.append(
                result["code"]
            )

            # --------------------------------------------------
            # Retrieval explanation
            # --------------------------------------------------

            sections.append(
                "\nWhy this result was retrieved:"
            )

            for explanation in (
                result["explanation"]
            ):

                sections.append(
                    f"- {explanation}"
                )

        return "\n".join(
            sections
        )


# ==========================================================
# Standalone test
# ==========================================================

if __name__ == "__main__":

    from app.hybrid_retriever import (
        HybridRetriever
    )

    query = (
        "How does Flask register URL rules?"
    )

    print(
        "\nRunning hybrid retrieval..."
    )

    retriever = HybridRetriever()

    results = retriever.search(
        query,
        top_k=5
    )

    print(
        f"Retrieved {len(results)} results."
    )

    # ------------------------------------------------------
    # Build context
    # ------------------------------------------------------

    builder = ContextBuilder()

    context = builder.build(
        query,
        results
    )

    # ------------------------------------------------------
    # Display graph-aware context
    # ------------------------------------------------------

    print(
        "\n\nGraph-Aware Context\n"
    )

    for index, result in enumerate(
        context["results"],
        start=1
    ):

        print(
            "=" * 70
        )

        print(
            f"Result {index}: "
            f"{result['qualified_name']}"
        )

        print(
            f"File: {result['file']}"
        )

        print(
            f"Line: {result['line']}"
        )

        print(
            "\nCode Graph Relationships:"
        )

        relationships = result.get(
            "graph_relationships",
            []
        )

        if relationships:

            for relationship in relationships:

                print(
                    "  - "
                    + builder._format_relationship(
                        relationship
                    )
                )

        else:

            print(
                "  - No graph relationships found"
            )

    # ------------------------------------------------------
    # LLM-ready context
    # ------------------------------------------------------

    print(
        "\n\nLLM-Ready Context\n"
    )

    formatted_context = (
        builder.format_for_llm(
            context
        )
    )

    print(
        formatted_context
    )