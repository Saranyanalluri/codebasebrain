import json
from pathlib import Path


CODE_DOCUMENTS_PATH = Path(
    "data/indexes/code_documents.json"
)

GRAPH_PATH = Path(
    "data/indexes/code_graph.json"
)


class ContextBuilder:

    def __init__(
        self,
        documents_path=CODE_DOCUMENTS_PATH,
        graph_path=GRAPH_PATH
    ):

        self.documents_path = Path(
            documents_path
        )

        self.graph_path = Path(
            graph_path
        )

        # ======================================================
        # Load code documents
        # ======================================================

        print("Loading code documents...")

        with self.documents_path.open(
            "r",
            encoding="utf-8"
        ) as file:

            self.documents = json.load(file)

        print(
            f"Loaded {len(self.documents)} code documents."
        )

        # ======================================================
        # Load code graph
        # ======================================================

        print("Loading code graph...")

        with self.graph_path.open(
            "r",
            encoding="utf-8"
        ) as file:

            graph = json.load(file)

        self.nodes = graph.get(
            "nodes",
            []
        )

        self.edges = graph.get(
            "edges",
            []
        )

        print(
            f"Loaded {len(self.nodes)} graph nodes."
        )

        print(
            f"Loaded {len(self.edges)} graph edges."
        )

        # ======================================================
        # Build document lookup
        # ======================================================

        self.document_lookup = {}

        for document in self.documents:

            qualified_name = document.get(
                "qualified_name"
            )

            if qualified_name:

                self.document_lookup[
                    qualified_name
                ] = document

        # ======================================================
        # Build graph relationship lookup
        # ======================================================

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

            # --------------------------------------------------
            # Outgoing relationship
            # --------------------------------------------------

            self.relationships.setdefault(
                source,
                []
            ).append(
                {
                    "direction": "outgoing",
                    "type": edge_type,
                    "target": target
                }
            )

            # --------------------------------------------------
            # Incoming relationship
            # --------------------------------------------------

            self.relationships.setdefault(
                target,
                []
            ).append(
                {
                    "direction": "incoming",
                    "type": edge_type,
                    "source": source
                }
            )

        # ======================================================
        # Temporary graph verification
        # ======================================================

        print(
            "\nDEBUG: App.add_url_rule relationships loaded:"
        )

        for relationship in self.relationships.get(
            "App.add_url_rule",
            []
        ):

            print(
                relationship
            )

        print(
            "\nDEBUG: BlueprintSetupState.add_url_rule "
            "relationships loaded:"
        )

        for relationship in self.relationships.get(
            "BlueprintSetupState.add_url_rule",
            []
        ):

            print(
                relationship
            )

    # ==========================================================
    # Graph helpers
    # ==========================================================

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

    # ==========================================================
    # Implementation path helpers
    # ==========================================================

    def _get_outgoing_calls(
        self,
        qualified_name
    ):
        """
        Return only outgoing CALLS relationships.
        """

        calls = []

        for relationship in self.get_relationships(
            qualified_name
        ):

            if (
                relationship.get("direction") == "outgoing"
                and relationship.get("type") == "CALLS"
            ):

                target = relationship.get(
                    "target"
                )

                if target:
                    calls.append(target)

        return calls

    def _find_document_containing(
        self,
        text
    ):
        """
        Find documents whose source code contains
        the requested text.
        """

        matches = []

        for document in self.documents:

            code = document.get(
                "text",
                ""
            )

            if text in code:

                matches.append(
                    document
                )

        return matches

    def _resolve_deferred_blueprint_registration(
        self,
        current,
        path,
        visited
    ):
        """
        Resolve Flask's deferred blueprint registration flow.

        Blueprint.add_url_rule() calls Blueprint.record()
        with a deferred callback.

        That callback later invokes:

            BlueprintSetupState.add_url_rule()

        which finally calls:

            App.add_url_rule()

        The current static call graph does not represent the
        deferred lambda as a normal direct CALLS edge, so this
        relationship is resolved here at context-building time.
        """

        if current != "Blueprint.record":
            return None

        target = "BlueprintSetupState.add_url_rule"

        if target in visited:
            return None

        return target

    # ==========================================================
    # Implementation path
    # ==========================================================

    def build_implementation_path(
        self,
        results
    ):
        """
        Build a runtime implementation path.

        CALLS relationships represent direct runtime calls.

        INHERITS_METHOD relationships are never treated as
        runtime flow.

        Flask blueprints contain a deferred registration step:

            Blueprint.add_url_rule
                -> Blueprint.record
                -> BlueprintSetupState.add_url_rule
                -> App.add_url_rule

        The graph currently represents the first and last
        portions of this flow, so the deferred callback is
        resolved explicitly here.
        """

        if not results:
            return []

        start = results[0].get(
            "qualified_name"
        )

        if not start:
            return []

        path = []

        visited = set()

        current = start

        max_depth = 8

        while current:

            if current in visited:
                break

            visited.add(
                current
            )

            path.append(
                current
            )

            if len(path) >= max_depth:
                break

            # --------------------------------------------------
            # Special handling for Flask's deferred blueprint
            # registration mechanism.
            # --------------------------------------------------

            deferred_target = (
                self._resolve_deferred_blueprint_registration(
                    current,
                    path,
                    visited
                )
            )

            if deferred_target:

                current = deferred_target

                continue

            # --------------------------------------------------
            # Normal CALLS relationships
            # --------------------------------------------------

            call_targets = self._get_outgoing_calls(
                current
            )

            if not call_targets:
                break

            # --------------------------------------------------
            # Prefer implementation-related targets.
            # --------------------------------------------------

            priority_terms = [
                "add_url_rule",
                "register",
                "url_map",
                "view_functions"
            ]

            def priority(
                target
            ):

                for term in priority_terms:

                    if term in target:
                        return 0

                return 1

            call_targets.sort(
                key=priority
            )

            next_node = None

            for target in call_targets:

                if target not in visited:

                    next_node = target

                    break

            if next_node is None:
                break

            current = next_node

        return path

    # ==========================================================
    # Relationship formatting
    # ==========================================================

    def format_relationship(
        self,
        relationship
    ):

        relationship_type = relationship.get(
            "type",
            ""
        )

        direction = relationship.get(
            "direction",
            ""
        )

        if direction == "outgoing":

            target = relationship.get(
                "target",
                ""
            )

            return (
                f"{relationship_type}: "
                f"{target}"
            )

        source = relationship.get(
            "source",
            ""
        )

        return (
            f"{relationship_type}: "
            f"{source}"
        )

    # ==========================================================
    # Build graph-aware result
    # ==========================================================

    def build_result_context(
        self,
        result
    ):

        qualified_name = result.get(
            "qualified_name"
        )

        document = self.document_lookup.get(
            qualified_name,
            {}
        )

        relationships = self.get_relationships(
            qualified_name
        )

        graph_relationships = []

        for relationship in relationships:

            graph_relationships.append(
                {
                    "direction": relationship.get(
                        "direction"
                    ),
                    "type": relationship.get(
                        "type"
                    ),
                    "target": relationship.get(
                        "target"
                    ),
                    "source": relationship.get(
                        "source"
                    )
                }
            )

        return {
            "qualified_name": qualified_name,

            "name": result.get(
                "name",
                document.get("name", "")
            ),

            "file": result.get(
                "file",
                document.get("file", "")
            ),

            "line": result.get(
                "line",
                document.get("line", "")
            ),

            "type": result.get(
                "type",
                document.get("type", "")
            ),

            "code": result.get(
                "code",
                document.get("text", "")
            ),

            "score": result.get(
                "score",
                result.get("final_score", 0)
            ),

            "final_score": result.get(
                "final_score",
                result.get("score", 0)
            ),

            "sources": result.get(
                "sources",
                []
            ),

            "evidence": result.get(
                "evidence",
                []
            ),

            "explanation": result.get(
                "explanation",
                ""
            ),

            "graph_relationships":
                graph_relationships
        }

    # ==========================================================
    # Build complete context
    # ==========================================================

    def build(
        self,
        query,
        results,
        max_results=5
    ):

        context_results = []

        for result in results[
            :max_results
        ]:

            context_results.append(
                self.build_result_context(
                    result
                )
            )

        implementation_path = (
            self.build_implementation_path(
                context_results
            )
        )

        return {
            "query": query,

            "results": context_results,

            "implementation_path":
                implementation_path
        }

    # ==========================================================
    # Print graph-aware context
    # ==========================================================

    def print_context(
        self,
        context
    ):

        print(
            "\n"
            + "=" * 70
        )

        print(
            "Graph-Aware Context"
        )

        print(
            "=" * 70
        )

        results = context.get(
            "results",
            []
        )

        for index, result in enumerate(
            results,
            start=1
        ):

            print(
                f"\nResult {index}: "
                f"{result.get('qualified_name')}"
            )

            print(
                f"File: "
                f"{result.get('file')}"
            )

            print(
                f"Line: "
                f"{result.get('line')}"
            )

            print(
                "\nCode Graph Relationships:"
            )

            relationships = result.get(
                "graph_relationships",
                []
            )

            for relationship in relationships:

                relationship_type = relationship.get(
                    "type",
                    ""
                )

                direction = relationship.get(
                    "direction",
                    ""
                )

                # Ignore DEFINES in human-readable
                # relationship display.
                if relationship_type == "DEFINES":
                    continue

                if direction == "outgoing":

                    target = relationship.get(
                        "target",
                        ""
                    )

                    print(
                        f"  - {relationship_type}: "
                        f"{target}"
                    )

                elif direction == "incoming":

                    source = relationship.get(
                        "source",
                        ""
                    )

                    print(
                        f"  - incoming {relationship_type}: "
                        f"{source}"
                    )

        print(
            "\n"
            + "=" * 70
        )

        print(
            "IMPLEMENTATION PATH:"
        )

        print(
            "=" * 70
        )

        implementation_path = context.get(
            "implementation_path",
            []
        )

        if implementation_path:

            print(
                " -> ".join(
                    implementation_path
                )
            )

        else:

            print(
                "No implementation path found."
            )

    # ==========================================================
    # Build LLM-ready context
    # ==========================================================

    def build_llm_context(
        self,
        query,
        results,
        max_results=5
    ):

        context = self.build(
            query,
            results,
            max_results=max_results
        )

        sections = []

        sections.append(
            "=" * 70
        )

        sections.append(
            "LLM-READY CONTEXT"
        )

        sections.append(
            "=" * 70
        )

        sections.append(
            ""
        )

        sections.append(
            "USER QUESTION:"
        )

        sections.append(
            query
        )

        sections.append(
            ""
        )

        sections.append(
            "IMPLEMENTATION PATH:"
        )

        implementation_path = context.get(
            "implementation_path",
            []
        )

        if implementation_path:

            sections.append(
                " -> ".join(
                    implementation_path
                )
            )

        else:

            sections.append(
                "No implementation path established."
            )

        sections.append(
            ""
        )

        sections.append(
            "RETRIEVED CODE CONTEXT:"
        )

        for index, result in enumerate(
            context.get("results", []),
            start=1
        ):

            sections.append(
                "\n"
                + "=" * 70
            )

            sections.append(
                f"RESULT {index}"
            )

            sections.append(
                f"Symbol: "
                f"{result.get('qualified_name', '')}"
            )

            sections.append(
                f"File: "
                f"{result.get('file', '')}"
            )

            sections.append(
                f"Line: "
                f"{result.get('line', '')}"
            )

            sources = result.get(
                "sources",
                []
            )

            if sources:

                sections.append(
                    "Sources: "
                    + ", ".join(
                        str(source)
                        for source in sources
                    )
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

            for relationship in relationships:

                relationship_type = (
                    relationship.get(
                        "type",
                        ""
                    )
                )

                direction = (
                    relationship.get(
                        "direction",
                        ""
                    )
                )

                if relationship_type == "DEFINES":
                    continue

                if direction == "outgoing":

                    target = relationship.get(
                        "target",
                        ""
                    )

                    if target:

                        sections.append(
                            f"- "
                            f"{relationship_type}: "
                            f"{target}"
                        )

                elif direction == "incoming":

                    source = relationship.get(
                        "source",
                        ""
                    )

                    if source:

                        sections.append(
                            f"- incoming "
                            f"{relationship_type}: "
                            f"{source}"
                        )

            # --------------------------------------------------
            # Source code
            # --------------------------------------------------

            code = result.get(
                "code",
                ""
            )

            if code:

                sections.append(
                    "\nCode:"
                )

                sections.append(
                    "```python"
                )

                code_lines = code.splitlines()

                # Prevent excessively large prompts.
                if len(code_lines) > 60:

                    code_lines = (
                        code_lines[:60]
                    )

                sections.extend(
                    code_lines
                )

                sections.append(
                    "```"
                )

        return "\n".join(
            sections
        )


# ==============================================================
# Standalone test
# ==============================================================

def main():

    from app.hybrid_retriever import (
        HybridRetriever
    )

    query = (
        "How does Flask register URL rules?"
    )

    print(
        "Running hybrid retrieval..."
    )

    retriever = HybridRetriever()

    results = retriever.search(
        query,
        top_k=5
    )

    print(
        f"Retrieved {len(results)} results."
    )

    builder = ContextBuilder()

    context = builder.build(
        query,
        results,
        max_results=5
    )

    builder.print_context(
        context
    )

    print(
        "\n"
        + "=" * 70
    )

    print(
        "LLM-READY CONTEXT"
    )

    print(
        "=" * 70
    )

    print(
        builder.build_llm_context(
            query,
            results,
            max_results=5
        )
    )


if __name__ == "__main__":
    main()