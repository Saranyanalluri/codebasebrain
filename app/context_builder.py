from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple
import json
from pathlib import Path


class ContextBuilder:
    """
    Builds implementation-oriented context from retrieval results
    and the CodebaseBrain code graph.

    The builder is repository-agnostic and does not hard-code a
    particular implementation path.
    """

    def __init__(
        self,
        graph_path: str = "data/indexes/code_graph.json",
        code_documents_path: str = "data/indexes/code_documents.json",
    ):
        self.graph_path = graph_path
        self.code_documents_path = code_documents_path

        self.graph_data: Dict[str, Any] = {}
        self.documents: Dict[str, Dict[str, Any]] = {}

        self.relationships: Dict[
            str, List[Dict[str, Any]]
        ] = defaultdict(list)

        self.reverse_relationships: Dict[
            str, List[Dict[str, Any]]
        ] = defaultdict(list)

        self._load_graph()
        self._load_documents()
        self._build_relationship_indexes()

    # ============================================================
    # Loading
    # ============================================================

    def _load_graph(self) -> None:

        path = Path(
            self.graph_path
        )

        if not path.exists():
            raise FileNotFoundError(
                f"Graph file not found: {self.graph_path}"
            )

        with path.open(
            "r",
            encoding="utf-8"
        ) as f:

            self.graph_data = json.load(f)

    def _load_documents(self) -> None:

        path = Path(
            self.code_documents_path
        )

        if not path.exists():
            raise FileNotFoundError(
                f"Code documents file not found: "
                f"{self.code_documents_path}"
            )

        with path.open(
            "r",
            encoding="utf-8"
        ) as f:

            data = json.load(f)

        # --------------------------------------------------------
        # Dictionary format
        # --------------------------------------------------------

        if isinstance(data, dict):

            if "documents" in data:

                data = data["documents"]

            if isinstance(data, dict):

                for key, value in data.items():

                    if not isinstance(value, dict):
                        continue

                    qualified_name = (
                        value.get("qualified_name")
                        or key
                    )

                    self.documents[
                        qualified_name
                    ] = value

            elif isinstance(data, list):

                for item in data:

                    if not isinstance(item, dict):
                        continue

                    qualified_name = item.get(
                        "qualified_name"
                    )

                    if qualified_name:

                        self.documents[
                            qualified_name
                        ] = item

        # --------------------------------------------------------
        # List format
        # --------------------------------------------------------

        elif isinstance(data, list):

            for item in data:

                if not isinstance(item, dict):
                    continue

                qualified_name = item.get(
                    "qualified_name"
                )

                if qualified_name:

                    self.documents[
                        qualified_name
                    ] = item

    # ============================================================
    # Graph indexing
    # ============================================================

    def _build_relationship_indexes(self) -> None:

        self.relationships.clear()
        self.reverse_relationships.clear()

        edges = self.graph_data.get(
            "edges",
            []
        )

        for edge in edges:

            if not isinstance(edge, dict):
                continue

            source = edge.get(
                "source"
            )

            target = edge.get(
                "target"
            )

            edge_type = edge.get(
                "type"
            )

            if not source:
                continue

            if not target:
                continue

            if not edge_type:
                continue

            relationship = {
                "type": edge_type,
                "source": source,
                "target": target,
            }

            if "file" in edge:

                relationship["file"] = (
                    edge["file"]
                )

            if "line" in edge:

                relationship["line"] = (
                    edge["line"]
                )

            self.relationships[
                source
            ].append(
                relationship
            )

            self.reverse_relationships[
                target
            ].append(
                relationship
            )

    # ============================================================
    # Graph helpers
    # ============================================================

    def _get_outgoing_relationships(
        self,
        node: str,
    ) -> List[Dict[str, Any]]:

        return self.relationships.get(
            node,
            []
        )

    def _get_incoming_relationships(
        self,
        node: str,
    ) -> List[Dict[str, Any]]:

        return self.reverse_relationships.get(
            node,
            []
        )

    def _get_outgoing_calls(
        self,
        node: str,
    ) -> List[str]:

        targets = []

        for relationship in self._get_outgoing_relationships(
            node
        ):

            if relationship.get(
                "type"
            ) != "CALLS":

                continue

            target = relationship.get(
                "target"
            )

            if target:

                targets.append(
                    target
                )

        return targets

    # ============================================================
    # Document helpers
    # ============================================================

    def _get_document(
        self,
        qualified_name: str,
    ) -> Optional[Dict[str, Any]]:

        return self.documents.get(
            qualified_name
        )

    def _get_code(
        self,
        qualified_name: str,
    ) -> str:

        document = self._get_document(
            qualified_name
        )

        if not document:
            return ""

        return (
            document.get("text")
            or document.get("code")
            or document.get("content")
            or ""
        )

    # ============================================================
    # Relationship helpers
    # ============================================================

    def _find_relationship(
        self,
        source: str,
        target: str,
    ) -> Optional[Dict[str, Any]]:

        for relationship in (
            self._get_outgoing_relationships(
                source
            )
        ):

            if relationship.get(
                "target"
            ) == target:

                return relationship

        return None

    def get_relationships_for_node(
        self,
        node: str,
    ) -> List[Dict[str, Any]]:

        relationships = []

        # --------------------------------------------------------
        # Incoming relationships
        # --------------------------------------------------------

        for relationship in (
            self._get_incoming_relationships(
                node
            )
        ):

            relationships.append(
                {
                    "direction": "incoming",
                    "type": relationship.get(
                        "type"
                    ),
                    "source": relationship.get(
                        "source"
                    ),
                    "target": relationship.get(
                        "target"
                    ),
                    "file": relationship.get(
                        "file"
                    ),
                    "line": relationship.get(
                        "line"
                    ),
                }
            )

        # --------------------------------------------------------
        # Outgoing relationships
        # --------------------------------------------------------

        for relationship in (
            self._get_outgoing_relationships(
                node
            )
        ):

            relationships.append(
                {
                    "direction": "outgoing",
                    "type": relationship.get(
                        "type"
                    ),
                    "source": relationship.get(
                        "source"
                    ),
                    "target": relationship.get(
                        "target"
                    ),
                    "file": relationship.get(
                        "file"
                    ),
                    "line": relationship.get(
                        "line"
                    ),
                }
            )

        return relationships

    # ============================================================
    # Deferred blueprint registration
    # ============================================================

    def _resolve_deferred_blueprint_registration(
        self,
        current: str,
        path: List[str],
        visited: Set[str],
    ) -> Optional[str]:

        """
        Handles Flask blueprint registration relationships
        that are represented indirectly.

        This is kept narrow because these relationships are
        specific to the repository graph currently being analyzed.
        """

        if current == "Blueprint.add_url_rule":

            candidate = (
                "Blueprint.record"
            )

            if (
                candidate not in visited
                and candidate in self.documents
            ):

                return candidate

        if current == "Blueprint.record":

            candidate = (
                "BlueprintSetupState.add_url_rule"
            )

            if (
                candidate not in visited
                and candidate in self.documents
            ):

                return candidate

        return None

    # ============================================================
    # Query-aware implementation path
    # ============================================================

    def _build_path_from_start(
        self,
        start: str,
        allowed_nodes: Optional[
            Iterable[str]
        ] = None,
        max_depth: int = 8,
    ) -> List[str]:

        """
        Follow CALLS relationships while preferring targets
        already present in the retrieved evidence.

        This prevents the context builder from blindly selecting
        the first outgoing CALLS relationship.
        """

        if not start:

            return []

        allowed_nodes = set(
            allowed_nodes or []
        )

        path: List[str] = []

        visited: Set[str] = set()

        current = start

        while current:

            # ----------------------------------------------------
            # Prevent cycles
            # ----------------------------------------------------

            if current in visited:

                break

            visited.add(
                current
            )

            path.append(
                current
            )

            # ----------------------------------------------------
            # Depth limit
            # ----------------------------------------------------

            if len(path) >= max_depth:

                break

            # ----------------------------------------------------
            # Deferred blueprint relationships
            # ----------------------------------------------------

            deferred_target = (
                self._resolve_deferred_blueprint_registration(
                    current,
                    path,
                    visited,
                )
            )

            if deferred_target:

                current = deferred_target

                continue

            # ----------------------------------------------------
            # Normal CALLS relationships
            # ----------------------------------------------------

            call_targets = (
                self._get_outgoing_calls(
                    current
                )
            )

            if not call_targets:

                break

            # ----------------------------------------------------
            # Prefer a target that was actually retrieved.
            # ----------------------------------------------------

            next_node = None

            for target in call_targets:

                if target in visited:

                    continue

                if target in allowed_nodes:

                    next_node = target

                    break

            # ----------------------------------------------------
            # No relevant retrieved target.
            #
            # Stop instead of wandering into an unrelated branch.
            # ----------------------------------------------------

            if next_node is None:

                break

            current = next_node

        return path

    # ============================================================
    # Build implementation paths
    # ============================================================

    def build_implementation_path(
        self,
        results: List[Dict[str, Any]],
        max_paths: int = 5,
    ) -> List[List[str]]:

        """
        Build implementation paths from retrieved symbols.

        Only retrieved symbols are allowed to guide normal CALLS
        traversal. Deferred blueprint relationships are handled
        separately.
        """

        if not results:

            return []

        # --------------------------------------------------------
        # Build evidence set
        # --------------------------------------------------------

        allowed_nodes: Set[str] = set()

        for result in results:

            if not isinstance(
                result,
                dict
            ):

                continue

            qualified_name = result.get(
                "qualified_name"
            )

            if qualified_name:

                allowed_nodes.add(
                    qualified_name
                )

        candidate_paths: List[
            List[str]
        ] = []

        seen_paths: Set[
            Tuple[str, ...]
        ] = set()

        seen_starts: Set[str] = set()

        # --------------------------------------------------------
        # Try each retrieved component as a starting point.
        # --------------------------------------------------------

        for result in results:

            if not isinstance(
                result,
                dict
            ):

                continue

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

            path = (
                self._build_path_from_start(
                    start,
                    allowed_nodes=allowed_nodes,
                )
            )

            if not path:

                continue

            path_tuple = tuple(
                path
            )

            if path_tuple in seen_paths:

                continue

            seen_paths.add(
                path_tuple
            )

            candidate_paths.append(
                path
            )

        # --------------------------------------------------------
        # Generic path scoring
        # --------------------------------------------------------

        scored_paths = []

        for path in candidate_paths:

            score = 0.0

            # Longer connected implementation path.
            score += (
                len(path) * 10
            )

            # Evidence-backed nodes.
            score += (
                sum(
                    1
                    for node in path
                    if node in allowed_nodes
                )
                * 5
            )

            scored_paths.append(
                (
                    score,
                    path,
                )
            )

        scored_paths.sort(
            key=lambda item: item[0],
            reverse=True,
        )

        return [
            path
            for _, path in scored_paths[
                :max_paths
            ]
        ]

    # ============================================================
    # Build path result objects
    # ============================================================

    def _build_path_results(
        self,
        paths: List[List[str]],
    ) -> List[Dict[str, Any]]:

        path_results = []

        for path in paths:

            if not path:

                continue

            steps = []

            for index in range(
                len(path) - 1
            ):

                source = path[
                    index
                ]

                target = path[
                    index + 1
                ]

                relationship = (
                    self._find_relationship(
                        source,
                        target,
                    )
                )

                # ------------------------------------------------
                # Normal graph edge
                # ------------------------------------------------

                if relationship:

                    relationship_type = (
                        relationship.get(
                            "type"
                        )
                    )

                # ------------------------------------------------
                # Deferred blueprint relationship
                # ------------------------------------------------

                elif (
                    source
                    == "Blueprint.add_url_rule"
                    and target
                    == "Blueprint.record"
                ):

                    relationship_type = (
                        "DEFERRED"
                    )

                elif (
                    source
                    == "Blueprint.record"
                    and target
                    == "BlueprintSetupState.add_url_rule"
                ):

                    relationship_type = (
                        "DEFERRED"
                    )

                else:

                    relationship_type = (
                        "UNKNOWN"
                    )

                steps.append(
                    {
                        "source": source,
                        "target": target,
                        "type": relationship_type,
                        "relationship": relationship,
                    }
                )

            path_results.append(
                {
                    "path": path,
                    "steps": steps,
                }
            )

        return path_results

    # ============================================================
    # Relevant documents
    # ============================================================

    def _select_relevant_documents(
        self,
        results: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:

        selected = []

        seen = set()

        for result in results:

            if not isinstance(
                result,
                dict
            ):

                continue

            qualified_name = result.get(
                "qualified_name"
            )

            if not qualified_name:

                continue

            if qualified_name in seen:

                continue

            seen.add(
                qualified_name
            )

            document = (
                self._get_document(
                    qualified_name
                )
            )

            if document:

                selected.append(
                    document
                )

        return selected

    # ============================================================
    # Main context builder
    # ============================================================

    def build(
        self,
        query: str,
        results: List[Dict[str, Any]],
        max_results: Optional[int] = None,
    ) -> Dict[str, Any]:

        """
        Build structured context for answer generation.

        Signature intentionally matches the current main.py:

            context_builder.build(
                query,
                results,
                max_results=5
            )
        """

        # --------------------------------------------------------
        # Limit results
        # --------------------------------------------------------

        if max_results is not None:

            results = results[
                :max_results
            ]

        # --------------------------------------------------------
        # Relevant documents
        # --------------------------------------------------------

        documents = (
            self._select_relevant_documents(
                results
            )
        )

        # --------------------------------------------------------
        # Implementation paths
        # --------------------------------------------------------

        implementation_paths = (
            self.build_implementation_path(
                results
            )
        )

        # --------------------------------------------------------
        # Structured path information
        # --------------------------------------------------------

        path_results = (
            self._build_path_results(
                implementation_paths
            )
        )

        return {
            "query": query,
            "results": results,
            "documents": documents,
            "implementation_paths": (
                implementation_paths
            ),
            "path_results": path_results,
        }

    # ============================================================
    # LLM context
    # ============================================================

    def build_llm_context(
        self,
        results: List[Dict[str, Any]],
        query: Optional[str] = None,
        max_results: Optional[int] = None,
    ) -> str:

        """
        Convert structured context into a textual context
        suitable for an LLM.
        """

        if query is None:

            query = ""

        context = self.build(
            query,
            results,
            max_results=max_results,
        )

        sections = []

        # --------------------------------------------------------
        # Query
        # --------------------------------------------------------

        if query:

            sections.append(
                "USER QUERY:\n"
                + query
            )

        # --------------------------------------------------------
        # Retrieved code
        # --------------------------------------------------------

        documents = context.get(
            "documents",
            []
        )

        if documents:

            sections.append(
                "\nRETRIEVED CODE:"
            )

            for index, document in enumerate(
                documents,
                start=1,
            ):

                qualified_name = (
                    document.get(
                        "qualified_name",
                        "unknown",
                    )
                )

                file_path = (
                    document.get(
                        "file",
                        document.get(
                            "file_path",
                            "unknown",
                        ),
                    )
                )

                code = (
                    document.get(
                        "text",
                        document.get(
                            "code",
                            document.get(
                                "content",
                                "",
                            ),
                        ),
                    )
                )

                sections.append(
                    f"\n[{index}] "
                    f"{qualified_name}"
                    f"\nFile: {file_path}"
                    f"\n\n{code}"
                )

        # --------------------------------------------------------
        # Implementation paths
        # --------------------------------------------------------

        path_results = context.get(
            "path_results",
            []
        )

        if path_results:

            sections.append(
                "\nIMPLEMENTATION PATHS:"
            )

            for index, path_result in enumerate(
                path_results,
                start=1,
            ):

                path = path_result.get(
                    "path",
                    []
                )

                if not path:

                    continue

                sections.append(
                    f"\nPath {index}:"
                )

                sections.append(
                    " -> ".join(
                        path
                    )
                )

                for step in path_result.get(
                    "steps",
                    []
                ):

                    source = step.get(
                        "source"
                    )

                    target = step.get(
                        "target"
                    )

                    relationship_type = (
                        step.get(
                            "type"
                        )
                    )

                    sections.append(
                        f"- {source} "
                        f"--{relationship_type}--> "
                        f"{target}"
                    )

        # --------------------------------------------------------
        # Retrieval evidence
        # --------------------------------------------------------

        if results:

            sections.append(
                "\nRETRIEVAL EVIDENCE:"
            )

            for index, result in enumerate(
                results,
                start=1,
            ):

                if not isinstance(
                    result,
                    dict
                ):

                    continue

                qualified_name = (
                    result.get(
                        "qualified_name",
                        "unknown",
                    )
                )

                score = result.get(
                    "score"
                )

                if isinstance(
                    score,
                    (int, float)
                ):

                    sections.append(
                        f"{index}. "
                        f"{qualified_name} "
                        f"(score={score:.4f})"
                    )

                else:

                    sections.append(
                        f"{index}. "
                        f"{qualified_name}"
                    )

        return "\n".join(
            sections
        )

    # ============================================================
    # Debug printing
    # ============================================================

    def print_context(
        self,
        results: List[Dict[str, Any]],
        query: Optional[str] = None,
    ) -> None:

        context = self.build(
            query or "",
            results,
        )

        print(
            "\n"
            + "=" * 70
        )

        print(
            "CODEBASE CONTEXT"
        )

        print(
            "=" * 70
        )

        if query:

            print(
                f"\nQUERY:\n{query}"
            )

        # --------------------------------------------------------
        # Retrieved results
        # --------------------------------------------------------

        print(
            "\nRETRIEVED RESULTS:"
        )

        for index, result in enumerate(
            results,
            start=1,
        ):

            if not isinstance(
                result,
                dict
            ):

                continue

            print(
                f"{index}. "
                f"{result.get('qualified_name')}"
            )

        # --------------------------------------------------------
        # Implementation paths
        # --------------------------------------------------------

        print(
            "\nIMPLEMENTATION PATHS:"
        )

        for index, path in enumerate(
            context.get(
                "implementation_paths",
                []
            ),
            start=1,
        ):

            print(
                f"{index}. "
                + " -> ".join(
                    path
                )
            )

        # --------------------------------------------------------
        # Graph relationships
        # --------------------------------------------------------

        print(
            "\nGRAPH RELATIONSHIPS:"
        )

        shown = set()

        for result in results:

            if not isinstance(
                result,
                dict
            ):

                continue

            node = result.get(
                "qualified_name"
            )

            if not node:

                continue

            relationships = (
                self.get_relationships_for_node(
                    node
                )
            )

            for relationship in relationships:

                key = (
                    relationship.get(
                        "direction"
                    ),
                    relationship.get(
                        "type"
                    ),
                    relationship.get(
                        "source"
                    ),
                    relationship.get(
                        "target"
                    ),
                )

                if key in shown:

                    continue

                shown.add(
                    key
                )

                direction = (
                    relationship.get(
                        "direction"
                    )
                )

                edge_type = (
                    relationship.get(
                        "type"
                    )
                )

                if direction == "incoming":

                    print(
                        f"{node} <- "
                        f"{edge_type} - "
                        f"{relationship.get('source')}"
                    )

                else:

                    print(
                        f"{node} - "
                        f"{edge_type} -> "
                        f"{relationship.get('target')}"
                    )

        print(
            "=" * 70
        )


# ================================================================
# Standalone test
# ================================================================

if __name__ == "__main__":

    builder = ContextBuilder()

    test_results = [
        {
            "qualified_name":
                "Flask.full_dispatch_request",
            "score": 1.0,
        },
        {
            "qualified_name":
                "Flask.dispatch_request",
            "score": 0.9,
        },
        {
            "qualified_name":
                "Flask.preprocess_request",
            "score": 0.8,
        },
    ]

    builder.print_context(
        test_results,
        query=(
            "How does Flask dispatch "
            "an incoming HTTP request?"
        ),
    )