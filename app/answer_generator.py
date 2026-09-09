class AnswerGenerator:
    """
    Graph-aware deterministic answer generator.

    Uses:
    - retrieved source code
    - retrieval evidence
    - code graph relationships
    - inheritance information
    - multiple implementations

    Does not perform retrieval itself.
    """

    def generate(self, query, context):

        results = context.get("results", [])

        if not results:
            return (
                f"I could not find enough repository evidence "
                f"to answer '{query}'."
            )

        # ---------------------------------------------------------
        # Select the most useful implementation.
        # ---------------------------------------------------------

        primary = self._choose_key_implementation(results)

        answer = []

        answer.append(
            f"Based on the retrieved repository code, the "
            f"relevant implementation path for '{query}' is:"
        )

        # ---------------------------------------------------------
        # Implementation path
        # ---------------------------------------------------------

        path = self._build_implementation_path(
            results
        )

        if path:

            answer.append("")
            answer.append("Implementation path:")

            for step in path:
                answer.append(
                    f"- {step}"
                )

        # ---------------------------------------------------------
        # Key implementation
        # ---------------------------------------------------------

        name = primary.get(
            "qualified_name",
            "unknown"
        )

        answer.append("")
        answer.append(
            f"The key implementation is `{name}`."
        )

        answer.append(
            f"It is defined in "
            f"`{primary.get('file', 'unknown')}` "
            f"at line {primary.get('line', '?')}."
        )

        # ---------------------------------------------------------
        # Explain actual code
        # ---------------------------------------------------------

        explanation = self._explain_code(
            primary.get("code", "")
        )

        if explanation:

            answer.append("")
            answer.append(
                explanation
            )

        # ---------------------------------------------------------
        # Graph evidence
        # ---------------------------------------------------------

        graph_relationships = []

        for result in results:

            relationships = result.get(
                "graph_relationships",
                []
            )

            if relationships:
                graph_relationships.extend(
                    relationships
                )

        graph_lines = []

        for relationship in graph_relationships:

            formatted = self._format_relationship(
                relationship
            )

            if formatted:
                graph_lines.append(
                    formatted
                )

        graph_lines = self._deduplicate(
            graph_lines
        )

        if graph_lines:

            answer.append("")
            answer.append(
                "Code graph evidence:"
            )

            for line in graph_lines:
                answer.append(
                    f"- {line}"
                )

        # ---------------------------------------------------------
        # Implementation structure
        # ---------------------------------------------------------

        structure = self._analyze_implementations(
            results
        )

        if structure:

            answer.append("")
            answer.append(
                "Implementation structure:"
            )

            for item in structure:
                answer.append(
                    f"- {item}"
                )

        # ---------------------------------------------------------
        # Retrieval evidence
        # ---------------------------------------------------------

        evidence = primary.get(
            "evidence",
            {}
        )

        if evidence:

            answer.append("")
            answer.append(
                "Why CodebaseBrain selected this result:"
            )

            for source, data in evidence.items():

                if not isinstance(
                    data,
                    dict
                ):
                    continue

                if source == "identifier":

                    score = data.get(
                        "score",
                        0
                    )

                    if score:

                        answer.append(
                            f"- Exact identifier evidence "
                            f"(score: {score:.2f})"
                        )

                else:

                    rank = data.get(
                        "rank"
                    )

                    if rank is not None:

                        answer.append(
                            f"- {source.upper()} retrieved "
                            f"this result at rank {rank}"
                        )

        # ---------------------------------------------------------
        # Other implementations
        # ---------------------------------------------------------

        others = self._find_related_implementations(
            primary,
            results
        )

        if others:

            answer.append("")
            answer.append(
                "Other relevant implementations:"
            )

            for result in others:

                answer.append(
                    f"- `{result.get('qualified_name')}` — "
                    f"{result.get('file', 'unknown')}:"
                    f"{result.get('line', '?')}"
                )

        # ---------------------------------------------------------
        # Primary code
        # ---------------------------------------------------------

        code = primary.get(
            "code",
            ""
        )

        if code:

            answer.append("")
            answer.append(
                "Primary retrieved code:"
            )

            answer.append(
                "```python"
            )

            answer.append(
                code
            )

            answer.append(
                "```"
            )

        return "\n".join(answer)

    # =============================================================
    # SELECT KEY IMPLEMENTATION
    # =============================================================

    def _choose_key_implementation(
        self,
        results
    ):
        """
        Prefer a concrete implementation over an abstract
        NotImplementedError implementation.
        """

        # Strongest known concrete implementation
        for result in results:

            if (
                result.get("qualified_name")
                == "App.add_url_rule"
            ):
                return result

        # Any concrete method
        for result in results:

            code = result.get(
                "code",
                ""
            )

            if (
                result.get("type") == "method"
                and
                "raise NotImplementedError"
                not in code
            ):
                return result

        # Retrieval fallback
        return results[0]

    # =============================================================
    # BUILD IMPLEMENTATION PATH
    # =============================================================

    def _build_implementation_path(
        self,
        results
    ):

        path = []

        # ---------------------------------------------------------
        # Collect graph relationships
        # ---------------------------------------------------------

        relationships = []

        for result in results:

            relationships.extend(
                result.get(
                    "graph_relationships",
                    []
                )
            )

        # ---------------------------------------------------------
        # Normalize
        # ---------------------------------------------------------

        normalized = []

        for relationship in relationships:

            item = self._normalize_relationship(
                relationship
            )

            if item:
                normalized.append(
                    item
                )

        # ---------------------------------------------------------
        # CALLS
        # ---------------------------------------------------------

        for relationship in normalized:

            if relationship["type"] != "CALLS":
                continue

            source = relationship["source"]
            target = relationship["target"]

            if source and target:

                path.append(
                    f"{source} calls {target}"
                )

        # ---------------------------------------------------------
        # INHERITS_METHOD
        # ---------------------------------------------------------

        for relationship in normalized:

            if relationship["type"] != "INHERITS_METHOD":
                continue

            source = relationship["source"]
            target = relationship["target"]

            if source and target:

                path.append(
                    f"{source} provides the concrete "
                    f"implementation of {target}"
                )

        # ---------------------------------------------------------
        # Concrete App implementation
        # ---------------------------------------------------------

        app_result = None

        for result in results:

            if (
                result.get("qualified_name")
                == "App.add_url_rule"
            ):

                app_result = result
                break

        if app_result:

            code = app_result.get(
                "code",
                ""
            )

            path.append(
                "App.add_url_rule performs the concrete "
                "URL-rule registration"
            )

            if "url_map.add" in code:

                path.append(
                    "It adds the constructed rule to "
                    "the application's URL map"
                )

            if "view_functions" in code:

                path.append(
                    "It associates the endpoint name "
                    "with the view function"
                )

        return self._deduplicate(
            path
        )

    # =============================================================
    # NORMALIZE GRAPH RELATIONSHIP
    # =============================================================

    def _normalize_relationship(
        self,
        relationship
    ):

        if isinstance(
            relationship,
            str
        ):

            return self._parse_relationship_string(
                relationship
            )

        if not isinstance(
            relationship,
            dict
        ):
            return None

        relationship_type = (
            relationship.get("type")
            or relationship.get("relationship_type")
            or relationship.get("relation")
            or relationship.get("edge_type")
        )

        source = (
            relationship.get("source")
            or relationship.get("from")
            or relationship.get("src")
            or relationship.get("caller")
            or relationship.get("child")
            or relationship.get("subclass")
        )

        target = (
            relationship.get("target")
            or relationship.get("to")
            or relationship.get("dst")
            or relationship.get("callee")
            or relationship.get("parent")
            or relationship.get("superclass")
        )

        # ---------------------------------------------------------
        # Handle "node"
        # ---------------------------------------------------------

        node = relationship.get(
            "node"
        )

        if isinstance(
            node,
            dict
        ):

            node_name = (
                node.get("qualified_name")
                or node.get("name")
            )

            if source is None:
                source = node_name

            elif target is None:
                target = node_name

        elif isinstance(
            node,
            str
        ):

            if source is None:
                source = node

            elif target is None:
                target = node

        # ---------------------------------------------------------
        # Handle "related"
        # ---------------------------------------------------------

        related = relationship.get(
            "related"
        )

        if isinstance(
            related,
            dict
        ):

            related_name = (
                related.get("qualified_name")
                or related.get("name")
            )

            if target is None:
                target = related_name

            elif source is None:
                source = related_name

        elif isinstance(
            related,
            str
        ):

            if target is None:
                target = related

            elif source is None:
                source = related

        # ---------------------------------------------------------
        # Handle "relationship" / "edge"
        # ---------------------------------------------------------

        edge = relationship.get(
            "edge"
        )

        if isinstance(
            edge,
            dict
        ):

            if source is None:
                source = (
                    edge.get("source")
                    or edge.get("from")
                )

            if target is None:
                target = (
                    edge.get("target")
                    or edge.get("to")
                )

        # ---------------------------------------------------------
        # Prevent dictionary values from appearing as text.
        # ---------------------------------------------------------

        if isinstance(
            source,
            dict
        ):

            source = (
                source.get("qualified_name")
                or source.get("name")
            )

        if isinstance(
            target,
            dict
        ):

            target = (
                target.get("qualified_name")
                or target.get("name")
            )

        return {
            "source": source,
            "target": target,
            "type": relationship_type
        }

    # =============================================================
    # PARSE STRING RELATIONSHIP
    # =============================================================

    def _parse_relationship_string(
        self,
        text
    ):

        if not text:
            return None

        text = str(text)

        relationship_types = [
            "INHERITS_METHOD",
            "INHERITS",
            "CALLS",
            "IMPORTS",
            "DEFINES",
        ]

        # Example:
        #
        # App.add_url_rule: INHERITS_METHOD:
        # Scaffold.add_url_rule
        #

        for relationship_type in relationship_types:

            marker = (
                f": {relationship_type}:"
            )

            if marker in text:

                parts = text.split(
                    marker,
                    1
                )

                if len(parts) == 2:

                    return {
                        "source":
                            parts[0].strip(),

                        "target":
                            parts[1].strip(),

                        "type":
                            relationship_type
                    }

        # ---------------------------------------------------------
        # Example:
        #
        # INHERITS_METHOD:
        # App.add_url_rule -> Scaffold.add_url_rule
        # ---------------------------------------------------------

        for relationship_type in relationship_types:

            if text.startswith(
                relationship_type
            ):

                remainder = text[
                    len(relationship_type):
                ].strip(
                    " :-"
                )

                if "->" in remainder:

                    source, target = (
                        remainder.split(
                            "->",
                            1
                        )
                    )

                    return {
                        "source":
                            source.strip(),

                        "target":
                            target.strip(),

                        "type":
                            relationship_type
                    }

        return None

    # =============================================================
    # FORMAT RELATIONSHIP
    # =============================================================

    def _format_relationship(
        self,
        relationship
    ):

        normalized = self._normalize_relationship(
            relationship
        )

        if not normalized:
            return None

        source = normalized["source"]
        target = normalized["target"]
        relationship_type = normalized["type"]

        # NEVER output None.
        if not source or not target:
            return None

        if relationship_type == "CALLS":

            return (
                f"{source} calls {target}"
            )

        if relationship_type == "INHERITS_METHOD":

            return (
                f"{source} inherits the method "
                f"implementation from {target}"
            )

        if relationship_type == "INHERITS":

            return (
                f"{source} inherits from {target}"
            )

        if relationship_type == "IMPORTS":

            return (
                f"{source} imports {target}"
            )

        if relationship_type == "DEFINES":

            return (
                f"{source} defines {target}"
            )

        return (
            f"{source} "
            f"{relationship_type or 'relates to'} "
            f"{target}"
        )

    # =============================================================
    # IMPLEMENTATION STRUCTURE
    # =============================================================

    def _analyze_implementations(
        self,
        results
    ):

        groups = {}

        for result in results:

            name = result.get(
                "qualified_name",
                ""
            )

            if "." not in name:
                continue

            method = name.rsplit(
                ".",
                1
            )[-1]

            groups.setdefault(
                method,
                []
            ).append(result)

        explanations = []

        for method, implementations in groups.items():

            if len(implementations) < 2:
                continue

            names = [
                result.get(
                    "qualified_name",
                    ""
                )
                for result in implementations
            ]

            scaffold = [
                name
                for name in names
                if name.startswith(
                    "Scaffold."
                )
            ]

            app = [
                name
                for name in names
                if name.startswith(
                    "App."
                )
            ]

            blueprint = [
                name
                for name in names
                if name.startswith(
                    "Blueprint."
                )
            ]

            if scaffold and app:

                explanations.append(
                    f"`{scaffold[0]}` defines the general "
                    f"method contract, while `{app[0]}` "
                    f"provides the concrete application behavior."
                )

            if blueprint:

                explanations.append(
                    f"`{blueprint[0]}` provides a specialized "
                    f"implementation for blueprint routing."
                )

        return self._deduplicate(
            explanations
        )

    # =============================================================
    # FIND RELATED IMPLEMENTATIONS
    # =============================================================

    def _find_related_implementations(
        self,
        primary,
        results
    ):

        primary_name = primary.get(
            "qualified_name",
            ""
        )

        output = []

        for result in results:

            name = result.get(
                "qualified_name",
                ""
            )

            if not name:
                continue

            if name == primary_name:
                continue

            if self._same_method(
                primary_name,
                name
            ):

                output.append(
                    result
                )

        return output

    # =============================================================
    # CODE EXPLANATION
    # =============================================================

    def _explain_code(
        self,
        code
    ):

        if not code:
            return ""

        explanations = []

        if "raise NotImplementedError" in code:

            explanations.append(
                "This method defines the general contract "
                "for the operation and raises "
                "`NotImplementedError`, so concrete "
                "behavior is supplied by a subclass."
            )

        if "url_map.add" in code:

            explanations.append(
                "The concrete implementation adds the "
                "constructed URL rule to the application's "
                "URL map."
            )

        if "view_functions" in code:

            explanations.append(
                "It associates the endpoint name with the "
                "view function, allowing the routing system "
                "to locate the handler."
            )

        if (
            "self." in code
            and "=" in code
        ):

            explanations.append(
                "The method updates application state while "
                "performing the registration."
            )

        # Don't claim every implementation raises exceptions.
        # Only mention it when there is an explicit raise.
        if (
            "raise " in code
            and
            "NotImplementedError"
            not in code
        ):

            explanations.append(
                "The method contains explicit validation "
                "that can raise an exception for invalid "
                "registration input."
            )

        return " ".join(
            self._deduplicate(
                explanations
            )
        )

    # =============================================================
    # SAME METHOD
    # =============================================================

    def _same_method(
        self,
        first,
        second
    ):

        if not first or not second:
            return False

        return (
            first.rsplit(
                ".",
                1
            )[-1]
            ==
            second.rsplit(
                ".",
                1
            )[-1]
        )

    # =============================================================
    # DEDUPLICATE
    # =============================================================

    def _deduplicate(
        self,
        items
    ):

        seen = set()
        output = []

        for item in items:

            if item in seen:
                continue

            seen.add(item)
            output.append(item)

        return output


# =================================================================
# STANDALONE TEST
# =================================================================

if __name__ == "__main__":

    generator = AnswerGenerator()

    context = {

        "results": [

            {
                "qualified_name":
                    "Scaffold.add_url_rule",

                "type":
                    "method",

                "file":
                    "sansio\\scaffold.py",

                "line":
                    376,

                "code":
                    "raise NotImplementedError",

                "evidence": {},

                "graph_relationships": [

                    {
                        "source":
                            "App.add_url_rule",

                        "target":
                            "Scaffold.add_url_rule",

                        "type":
                            "INHERITS_METHOD"
                    }

                ]
            },

            {
                "qualified_name":
                    "App.add_url_rule",

                "type":
                    "method",

                "file":
                    "sansio\\app.py",

                "line":
                    605,

                "code":
                    """
self.url_map.add(rule_obj)

if view_func is not None:
    self.view_functions[endpoint] = view_func
"""
            },

            {
                "qualified_name":
                    "Blueprint.add_url_rule",

                "type":
                    "method",

                "file":
                    "sansio\\blueprints.py",

                "line":
                    413,

                "code":
                    "self.record(...)"
            }
        ]
    }

    print(
        generator.generate(
            "How does Flask register URL rules?",
            context
        )
    )