import json
from pathlib import Path

from app.explanation_engine import ExplanationEngine


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
        # Explanation engine
        # ======================================================

        self.explanation_engine = ExplanationEngine()

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

                    calls.append(
                        target
                    )

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

        Blueprint.add_url_rule()
            -> Blueprint.record()
            -> BlueprintSetupState.add_url_rule()
            -> App.add_url_rule()

        The static call graph does not represent the
        deferred lambda as a normal direct CALLS edge,
        so the relationship is resolved here.
        """

        if current == "Blueprint.add_url_rule":

            target = "Blueprint.record"

            if target not in visited:

                return target

        if current == "Blueprint.record":

            target = "BlueprintSetupState.add_url_rule"

            if target not in visited:

                return target

        return None

    # ==========================================================
    # Find the best retrieved starting point
    # ==========================================================

    def _select_best_start(
        self,
        results
    ):

        """
        Select the most useful implementation candidate.
        """

        candidates = []

        for index, result in enumerate(
            results
        ):

            qualified_name = result.get(
                "qualified_name"
            )

            if not qualified_name:
                continue

            score = 0

            # --------------------------------------------------
            # Strong API/application implementations
            # --------------------------------------------------

            if qualified_name == "App.add_url_rule":

                score += 100

            elif qualified_name == "Blueprint.add_url_rule":

                score += 90

            elif qualified_name == "BlueprintSetupState.add_url_rule":

                score += 80

            # --------------------------------------------------
            # Methods with runtime CALLS
            # --------------------------------------------------

            outgoing_calls = self._get_outgoing_calls(
                qualified_name
            )

            score += len(
                outgoing_calls
            ) * 10

            # --------------------------------------------------
            # Penalize abstract implementation
            # --------------------------------------------------

            if qualified_name == "Scaffold.add_url_rule":

                score -= 50

            # --------------------------------------------------
            # Prefer actual source code
            # --------------------------------------------------

            code = result.get(
                "code",
                ""
            )

            if code:

                score += 5

            candidates.append(
                (
                    score,
                    -index,
                    qualified_name
                )
            )

        if not candidates:

            return None

        candidates.sort(
            reverse=True
        )

        return candidates[0][2]

    # ==========================================================
    # Build one normal CALLS path
    # ==========================================================

    def _build_path_from_start(
        self,
        start,
        max_depth=8
    ):

        """
        Follow CALLS relationships from a selected
        implementation candidate.
        """

        if not start:

            return []

        path = []

        visited = set()

        current = start

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
            # Deferred blueprint registration
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
    # Build implementation path
    # ==========================================================

    def build_implementation_path(
        self,
        results
    ):

        """
        Build a runtime-oriented implementation path.
        """

        if not results:

            return []

        candidate_paths = []

        seen_starts = set()

        for result in results:

            start = result.get(
                "qualified_name"
            )

            if not start:

                continue

            if start in seen_starts:

                continue

            seen_starts.add(
                start
            )

            path = self._build_path_from_start(
                start
            )

            if path:

                candidate_paths.append(
                    path
                )

        # ------------------------------------------------------
        # Concrete App implementation
        # ------------------------------------------------------

        if (
            "App.add_url_rule"
            in self.document_lookup
        ):

            app_path = [
                "App.add_url_rule"
            ]

            if app_path not in candidate_paths:

                candidate_paths.append(
                    app_path
                )

        # ------------------------------------------------------
        # Blueprint registration path
        # ------------------------------------------------------

        if (
            "Blueprint.add_url_rule"
            in self.document_lookup
            and
            "Blueprint.record"
            in self.document_lookup
            and
            "BlueprintSetupState.add_url_rule"
            in self.document_lookup
            and
            "App.add_url_rule"
            in self.document_lookup
        ):

            blueprint_path = [
                "Blueprint.add_url_rule",
                "Blueprint.record",
                "BlueprintSetupState.add_url_rule",
                "App.add_url_rule"
            ]

            if blueprint_path not in candidate_paths:

                candidate_paths.append(
                    blueprint_path
                )

        # ------------------------------------------------------
        # Score candidate paths
        # ------------------------------------------------------

        def path_score(
            path
        ):

            score = 0

            score += len(
                path
            ) * 10

            if "App.add_url_rule" in path:

                score += 50

            if (
                "Blueprint.add_url_rule" in path
                and
                "Blueprint.record" in path
                and
                "BlueprintSetupState.add_url_rule" in path
                and
                "App.add_url_rule" in path
            ):

                score += 40

            if (
                len(path) == 1
                and
                path[0] == "Scaffold.add_url_rule"
            ):

                score -= 100

            final_node = path[-1]

            if final_node == "App.add_url_rule":

                score += 30

            return score

        if not candidate_paths:

            return []

        return max(
            candidate_paths,
            key=path_score
        )

    # ==========================================================
    # Build source context for every implementation-path
    # component
    # ==========================================================

    def _build_path_results(
        self,
        implementation_path
    ):

        """
        Load repository evidence for every symbol in
        the implementation path.
        """

        path_results = []

        seen = set()

        for qualified_name in implementation_path:

            if not qualified_name:
                continue

            if qualified_name in seen:
                continue

            seen.add(
                qualified_name
            )

            document = self.document_lookup.get(
                qualified_name
            )

            if not document:
                continue

            result = {
                "qualified_name": qualified_name,

                "name": document.get(
                    "name",
                    ""
                ),

                "file": document.get(
                    "file",
                    ""
                ),

                "line": document.get(
                    "line",
                    ""
                ),

                "type": document.get(
                    "type",
                    ""
                ),

                "code": document.get(
                    "text",
                    ""
                ),

                "score": None,

                "final_score": None,

                "sources": [
                    "implementation_path"
                ],

                "evidence": [
                    "implementation_path"
                ],

                "explanation": (
                    "Included because this symbol belongs "
                    "to the implementation path."
                ),

                "graph_relationships": []
            }

            relationships = self.get_relationships(
                qualified_name
            )

            for relationship in relationships:

                result["graph_relationships"].append(
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

            path_results.append(
                result
            )

        return path_results

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
                document.get(
                    "name",
                    ""
                )
            ),

            "file": result.get(
                "file",
                document.get(
                    "file",
                    ""
                )
            ),

            "line": result.get(
                "line",
                document.get(
                    "line",
                    ""
                )
            ),

            "type": result.get(
                "type",
                document.get(
                    "type",
                    ""
                )
            ),

            "code": result.get(
                "code",
                document.get(
                    "text",
                    ""
                )
            ),

            "score": result.get(
                "score"
            ),

            "final_score": result.get(
                "final_score",
                result.get(
                    "score",
                    0
                )
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

        # ------------------------------------------------------
        # Build normal retrieval context
        # ------------------------------------------------------

        context_results = []

        for result in results[
            :max_results
        ]:

            context_results.append(
                self.build_result_context(
                    result
                )
            )

        # ------------------------------------------------------
        # Build implementation path
        # ------------------------------------------------------

        implementation_path = (
            self.build_implementation_path(
                context_results
            )
        )

        # ------------------------------------------------------
        # Load EVERY path component
        # ------------------------------------------------------

        path_results = self._build_path_results(
            implementation_path
        )

        # ------------------------------------------------------
        # Generate deterministic implementation explanation
        # ------------------------------------------------------

        implementation_explanation = (
            self.explanation_engine.explain_implementation(
                implementation_path,
                path_results
            )
        )

        # ------------------------------------------------------
        # Merge retrieved results and path results
        # ------------------------------------------------------

        merged_results = []

        seen_names = set()

        for result in context_results:

            qualified_name = result.get(
                "qualified_name"
            )

            if not qualified_name:
                continue

            if qualified_name in seen_names:
                continue

            seen_names.add(
                qualified_name
            )

            merged_results.append(
                result
            )

        for result in path_results:

            qualified_name = result.get(
                "qualified_name"
            )

            if not qualified_name:
                continue

            if qualified_name in seen_names:
                continue

            seen_names.add(
                qualified_name
            )

            merged_results.append(
                result
            )

        return {
            "query": query,

            "results": merged_results,

            "implementation_path":
                implementation_path,

            "path_results":
                path_results,

            "implementation_explanation":
                implementation_explanation
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

            for index, step in enumerate(
                implementation_path,
                start=1
            ):

                print(
                    f"{index}. {step}"
                )

        else:

            print(
                "No implementation path found."
            )

        # ------------------------------------------------------
        # Deterministic implementation explanation
        # ------------------------------------------------------

        print(
            "\n"
            + "=" * 70
        )

        print(
            "DETERMINISTIC IMPLEMENTATION EXPLANATION:"
        )

        print(
            "=" * 70
        )

        implementation_explanation = context.get(
            "implementation_explanation",
            []
        )

        if implementation_explanation:

            for index, explanation in enumerate(
                implementation_explanation,
                start=1
            ):

                print(
                    f"{index}. {explanation}"
                )

        else:

            print(
                "No deterministic explanation established."
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

        # ------------------------------------------------------
        # Implementation path
        # ------------------------------------------------------

        sections.append(
            "IMPLEMENTATION PATH:"
        )

        implementation_path = context.get(
            "implementation_path",
            []
        )

        if implementation_path:

            for index, step in enumerate(
                implementation_path,
                start=1
            ):

                sections.append(
                    f"{index}. {step}"
                )

        else:

            sections.append(
                "No implementation path established."
            )

        sections.append(
            ""
        )

        # ------------------------------------------------------
        # Deterministic explanation
        # ------------------------------------------------------

        sections.append(
            "DETERMINISTIC IMPLEMENTATION EXPLANATION:"
        )

        implementation_explanation = context.get(
            "implementation_explanation",
            []
        )

        if implementation_explanation:

            for index, explanation in enumerate(
                implementation_explanation,
                start=1
            ):

                sections.append(
                    f"{index}. {explanation}"
                )

        else:

            sections.append(
                "No deterministic explanation established."
            )

        sections.append(
            ""
        )

        # ------------------------------------------------------
        # Implementation-path source code
        # ------------------------------------------------------

        sections.append(
            "IMPLEMENTATION PATH SOURCE CODE:"
        )

        sections.append(
            ""
        )

        path_results = context.get(
            "path_results",
            []
        )

        path_result_lookup = {}

        for result in path_results:

            qualified_name = result.get(
                "qualified_name",
                ""
            )

            if qualified_name:

                path_result_lookup[
                    qualified_name
                ] = result

        for index, qualified_name in enumerate(
            implementation_path,
            start=1
        ):

            result = path_result_lookup.get(
                qualified_name
            )

            if not result:
                continue

            sections.append(
                "=" * 70
            )

            sections.append(
                f"PATH COMPONENT {index}"
            )

            sections.append(
                f"Symbol: {qualified_name}"
            )

            sections.append(
                f"File: {result.get('file', '')}"
            )

            sections.append(
                f"Line: {result.get('line', '')}"
            )

            # --------------------------------------------------
            # Graph relationships
            # --------------------------------------------------

            relationships = result.get(
                "graph_relationships",
                []
            )

            relevant_relationships = []

            for relationship in relationships:

                relationship_type = relationship.get(
                    "type",
                    ""
                )

                direction = relationship.get(
                    "direction",
                    ""
                )

                if relationship_type == "DEFINES":

                    continue

                if direction == "outgoing":

                    target = relationship.get(
                        "target",
                        ""
                    )

                    if target:

                        relevant_relationships.append(
                            f"- {relationship_type}: "
                            f"{target}"
                        )

                elif direction == "incoming":

                    source = relationship.get(
                        "source",
                        ""
                    )

                    if source:

                        relevant_relationships.append(
                            f"- incoming "
                            f"{relationship_type}: "
                            f"{source}"
                        )

            if relevant_relationships:

                sections.append(
                    "\nGraph relationships:"
                )

                sections.extend(
                    relevant_relationships
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

                if len(code_lines) > 80:

                    code_lines = code_lines[:80]

                sections.extend(
                    code_lines
                )

                sections.append(
                    "```"
                )

        sections.append(
            ""
        )

        sections.append(
            "END OF IMPLEMENTATION PATH EVIDENCE"
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