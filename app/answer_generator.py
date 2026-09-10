import ast
import textwrap


class AnswerGenerator:
    """
    Repository-agnostic deterministic answer generator.

    Uses:
    - AST analysis for code behavior
    - retrieval evidence
    - code graph relationships
    - implementation hierarchy

    The generator intentionally produces high-level explanations
    instead of translating every low-level function call into prose.
    """

    # Low-level / language utility calls that should not normally
    # appear in the natural-language explanation.
    IGNORED_CALLS = {
        # Exceptions
        "RuntimeError",
        "ValueError",
        "TypeError",
        "KeyError",
        "AssertionError",
        "Exception",
        "NotImplementedError",

        # Python utilities
        "isinstance",
        "getattr",
        "setattr",
        "hasattr",
        "len",
        "dict",
        "tuple",
        "list",
        "str",
        "int",
        "bool",
        "cast",
        "t.cast",

        # Common collection/string helpers
        "pop",
        "set",
        "get",
        "update",
        "upper",
        "lower",
        "add",
    }

    # ================================================================
    # Main generation
    # ================================================================

    def generate(self, query, context):
        results = context.get("results", [])

        if not results:
            return (
                "I could not find a sufficiently relevant implementation "
                "in the indexed repository."
            )

        primary = self._choose_key_implementation(
            results
        )

        if not primary:
            return (
                "I could not identify a primary implementation "
                "from the retrieved results."
            )

        lines = []

        lines.append(
            f"Based on the retrieved repository code, the relevant "
            f"implementation path for '{query}' is:"
        )

        lines.append("")

        path = self._build_implementation_path(
            results,
            primary,
        )

        if path:
            lines.append(
                "Implementation path:"
            )

            for item in path:
                lines.append(
                    f"- {item}"
                )

            lines.append("")

        primary_name = primary.get(
            "qualified_name",
            "Unknown",
        )

        primary_file = primary.get(
            "file",
            "unknown",
        )

        primary_line = primary.get(
            "line",
            "?",
        )

        lines.append(
            f"The key implementation is `{primary_name}`."
        )

        lines.append(
            f"It is defined in `{primary_file}` "
            f"at line {primary_line}."
        )

        explanation = self._explain_code(
            primary.get(
                "code",
                "",
            )
        )

        if explanation:
            lines.append("")
            lines.append(
                explanation
            )

        structure = self._implementation_structure(
            results,
            primary,
        )

        if structure:
            lines.append("")
            lines.append(
                "Implementation structure:"
            )

            for item in structure:
                lines.append(
                    f"- {item}"
                )

        # ------------------------------------------------------------
        # Graph evidence
        # ------------------------------------------------------------

        relationships = primary.get(
            "graph_relationships",
            [],
        )

        formatted_relationships = []

        for relationship in relationships:
            formatted = self._format_relationship(
                relationship
            )

            if formatted:
                formatted_relationships.append(
                    formatted
                )

        if formatted_relationships:
            lines.append("")
            lines.append(
                "Code graph evidence:"
            )

            for relationship in formatted_relationships[:8]:
                lines.append(
                    f"- {relationship}"
                )

        # ------------------------------------------------------------
        # Retrieval evidence
        # ------------------------------------------------------------

        lines.append("")
        lines.append(
            "Why CodebaseBrain selected this result:"
        )

        evidence = primary.get(
            "evidence",
            {},
        )

        for source in (
            "bm25",
            "semantic",
            "graph",
        ):
            source_evidence = evidence.get(
                source
            )

            if source_evidence:
                rank = source_evidence.get(
                    "rank"
                )

                if rank is not None:
                    lines.append(
                        f"- {source.upper()} retrieved "
                        f"this result at rank {rank}"
                    )

        identifier = evidence.get(
            "identifier"
        )

        if identifier:
            score = identifier.get(
                "score",
                0,
            )

            if score > 0:
                lines.append(
                    f"- Exact identifier evidence "
                    f"(score: {score:.2f})"
                )

        # ------------------------------------------------------------
        # Related implementations
        # ------------------------------------------------------------

        related = self._related_implementations(
            results,
            primary,
        )

        if related:
            lines.append("")
            lines.append(
                "Other relevant implementations:"
            )

            for item in related:
                lines.append(
                    f"- `{item['qualified_name']}` — "
                    f"{item['file']}:{item['line']}"
                )

        # ------------------------------------------------------------
        # Source code
        # ------------------------------------------------------------

        lines.append("")
        lines.append(
            "Primary retrieved code:"
        )

        lines.append(
            "```python"
        )

        lines.append(
            primary.get(
                "code",
                "",
            ).rstrip()
        )

        lines.append(
            "```"
        )

        return "\n".join(
            lines
        )

    # ================================================================
    # Implementation selection
    # ================================================================

    def _choose_key_implementation(
        self,
        results,
    ):
        """
        Select the most useful implementation.

        Concrete implementations are preferred over abstract
        contracts that only raise NotImplementedError.
        """

        if not results:
            return {}

        candidates = []

        for index, result in enumerate(
            results
        ):
            score = float(
                result.get(
                    "final_score",
                    0,
                )
            )

            code = result.get(
                "code",
                "",
            )

            # Strongly penalize abstract implementations.
            if self._is_not_implemented(
                code
            ):
                score -= 10

            # Reward real implementation logic.
            if self._has_ast_node(
                code,
                ast.Assign,
            ):
                score += 0.5

            if self._has_ast_node(
                code,
                ast.If,
            ):
                score += 0.3

            if self._has_ast_node(
                code,
                ast.Return,
            ):
                score += 0.2

            useful_calls = (
                self._count_useful_calls(
                    code
                )
            )

            score += min(
                useful_calls * 0.05,
                0.5,
            )

            candidates.append(
                (
                    score,
                    -index,
                    result,
                )
            )

        candidates.sort(
            key=lambda item: (
                item[0],
                item[1],
            ),
            reverse=True,
        )

        return candidates[0][2]

    # ================================================================
    # Implementation path
    # ================================================================

    def _build_implementation_path(
        self,
        results,
        primary,
    ):
        path = []

        primary_name = primary.get(
            "qualified_name",
            "",
        )

        code = primary.get(
            "code",
            "",
        )

        action = self._infer_primary_action(
            primary_name
        )

        if action:
            path.append(
                f"`{primary_name}` implements "
                f"the `{action}` operation"
            )
        else:
            path.append(
                f"`{primary_name}` contains the "
                f"main implementation logic"
            )

        operations = (
            self._extract_semantic_operations(
                code
            )
        )

        for operation in operations:
            if operation not in path:
                path.append(
                    operation
                )

        return path

    # ================================================================
    # Action inference
    # ================================================================

    def _infer_primary_action(
        self,
        qualified_name,
    ):
        if not qualified_name:
            return ""

        method_name = qualified_name.split(
            "."
        )[-1]

        words = []
        current = ""

        for char in method_name:
            if char == "_":
                if current:
                    words.append(
                        current
                    )

                current = ""

            else:
                current += char

        if current:
            words.append(
                current
            )

        return " ".join(
            words
        )

    # ================================================================
    # Semantic AST analysis
    # ================================================================

    def _extract_semantic_operations(
        self,
        code,
    ):
        """
        Convert AST patterns into high-level semantic operations.

        Instead of saying:

            options.pop()
            item.upper()
            self.url_map.add()
            _endpoint_from_view_func()

        the generator tries to say:

            determines endpoint and methods
            creates and registers the URL rule
            associates the endpoint with the view function
        """

        if not code:
            return []

        try:
            tree = ast.parse(
                textwrap.dedent(code)
            )

        except SyntaxError:
            return []

        operations = []

        source_text = textwrap.dedent(
            code
        )

        # ============================================================
        # REQUEST DISPATCH
        # ============================================================

        if self._contains_call(
            tree,
            {
                "self.ensure_sync",
                "ensure_sync",
            },
        ):
            if (
                "view_functions"
                in source_text
                and "endpoint"
                in source_text
            ):
                operations.append(
                    "It dispatches the request to the "
                    "matched endpoint's view function."
                )

        # ============================================================
        # URL RULE REGISTRATION
        # ============================================================

        has_url_map_add = self._contains_call(
            tree,
            {
                "self.url_map.add",
            },
        )

        has_url_rule_class = self._contains_call(
            tree,
            {
                "self.url_rule_class",
            },
        )

        has_view_function_assignment = (
            self._contains_assignment_containing(
                tree,
                "view_functions",
            )
        )

        has_endpoint_assignment = (
            self._contains_assignment_to(
                tree,
                "endpoint",
            )
        )

        has_methods_assignment = (
            self._contains_assignment_to(
                tree,
                "methods",
            )
        )

        has_endpoint_helper = (
            self._contains_call(
                tree,
                {
                    "_endpoint_from_view_func",
                },
            )
        )

        if (
            has_endpoint_assignment
            or has_endpoint_helper
        ) and has_methods_assignment:

            operations.append(
                "It determines the endpoint and allowed "
                "HTTP methods."
            )

        elif (
            has_endpoint_assignment
            or has_endpoint_helper
        ):

            operations.append(
                "It determines the endpoint used by "
                "the URL rule."
            )

        elif has_methods_assignment:

            operations.append(
                "It determines the allowed HTTP methods."
            )

        if (
            "provide_automatic_options"
            in source_text
            and "required_methods"
            in source_text
            and '"OPTIONS"'
            in source_text
        ):
            operations.append(
                "It enables automatic OPTIONS support "
                "when required."
            )

        if has_url_map_add:

            operations.append(
                "It creates a URL rule and adds it to "
                "the application's URL map."
            )

        elif has_url_rule_class:

            operations.append(
                "It creates a URL rule for the endpoint."
            )

        if has_view_function_assignment:

            operations.append(
                "It associates the endpoint with "
                "the view function."
            )

        # ============================================================
        # SESSION SAVING
        # ============================================================

        has_serializer = self._contains_call(
            tree,
            {
                "self.get_signing_serializer",
            },
        )

        has_set_cookie = self._contains_call(
            tree,
            {
                "response.set_cookie",
            },
        )

        has_delete_cookie = self._contains_call(
            tree,
            {
                "response.delete_cookie",
            },
        )

        if (
            has_serializer
            and has_set_cookie
        ):
            operations.append(
                "It serializes the session data and "
                "stores it in a signed cookie."
            )

        if has_delete_cookie:
            operations.append(
                "It removes the session cookie when "
                "the session is empty and modified."
            )

        # ============================================================
        # EXCEPTION HANDLING
        # ============================================================

        has_error_handler_lookup = (
            self._contains_call(
                tree,
                {
                    "self._find_error_handler",
                },
            )
        )

        has_log_exception = (
            self._contains_call(
                tree,
                {
                    "self.log_exception",
                },
            )
        )

        has_finalize_request = (
            self._contains_call(
                tree,
                {
                    "self.finalize_request",
                },
            )
        )

        has_http_exception_handler = (
            self._contains_call(
                tree,
                {
                    "self.handle_http_exception",
                },
            )
        )

        if has_http_exception_handler:

            operations.append(
                "It delegates HTTP exceptions to the "
                "HTTP exception handler."
            )

        if has_error_handler_lookup:

            operations.append(
                "It looks up a registered error handler."
            )

        if has_log_exception:

            operations.append(
                "It logs the unhandled exception."
            )

        if has_finalize_request:

            operations.append(
                "It finalizes the generated response."
            )

        # ============================================================
        # STATIC FILES
        # ============================================================

        has_send_from_directory = (
            self._contains_call(
                tree,
                {
                    "send_from_directory",
                },
            )
        )

        if has_send_from_directory:

            operations.append(
                "It serves the requested file from "
                "the configured static directory."
            )

        # ============================================================
        # RESPONSE CREATION
        # ============================================================

        has_make_response = (
            self._contains_call(
                tree,
                {
                    "self.make_response",
                },
            )
        )

        if has_make_response:

            operations.append(
                "It converts the result into a response object."
            )

        # ============================================================
        # RETURN BEHAVIOR
        # ============================================================

        for node in ast.walk(
            tree
        ):
            if not isinstance(
                node,
                ast.Return,
            ):
                continue

            description = (
                self._describe_return_expression(
                    node.value
                )
            )

            if description:
                operations.append(
                    f"It returns {description}."
                )

        # ============================================================
        # ABSTRACT CONTRACT
        # ============================================================

        if self._is_not_implemented(
            code
        ):
            operations.append(
                "It defines an abstract contract and "
                "raises `NotImplementedError`."
            )

        # ============================================================
        # BRANCH COUNT
        # ============================================================

        branch_count = sum(
            isinstance(
                node,
                (
                    ast.If,
                    ast.IfExp,
                    ast.Match,
                ),
            )
            for node in ast.walk(
                tree
            )
        )

        if branch_count:
            operations.append(
                f"The implementation evaluates "
                f"{branch_count} conditional branches."
            )

        return self._deduplicate(
            operations
        )

    # ================================================================
    # Code explanation
    # ================================================================

    def _explain_code(
        self,
        code,
    ):
        if not code:
            return ""

        try:
            tree = ast.parse(
                textwrap.dedent(code)
            )

        except SyntaxError:
            return ""

        sections = []

        # ------------------------------------------------------------
        # Documentation
        # ------------------------------------------------------------

        docstring = ast.get_docstring(
            tree,
            clean=True,
        )

        if docstring:
            paragraph = (
                docstring.strip().split(
                    "\n\n",
                    1,
                )[0]
            )

            paragraph = " ".join(
                line.strip()
                for line in paragraph.splitlines()
            )

            # Avoid dumping huge documentation blocks.
            if len(paragraph) > 300:
                paragraph = (
                    paragraph[:297]
                    + "..."
                )

            sections.append(
                f"Documentation: {paragraph}"
            )

        # ------------------------------------------------------------
        # Behavioral explanation
        # ------------------------------------------------------------

        behavior = (
            self._extract_semantic_operations(
                code
            )
        )

        # Don't repeat the branch statement here if it is already
        # present in the semantic operation list.
        behavior = self._deduplicate(
            behavior
        )

        if behavior:

            # Remove the first implementation-path style statement
            # if it isn't useful as behavioral documentation.
            sections.append(
                "Behavior: "
                + " ".join(
                    behavior
                )
            )

        return "\n".join(
            sections
        )

    # ================================================================
    # Return analysis
    # ================================================================

    def _describe_return_expression(
        self,
        value,
    ):
        if value is None:
            return ""

        # Detect:
        #
        # return self.ensure_sync(
        #     self.view_functions[rule.endpoint]
        # )(**view_args)
        #
        if isinstance(
            value,
            ast.Call,
        ):

            inner_func = value.func

            if isinstance(
                inner_func,
                ast.Call,
            ):

                inner_name = (
                    self._get_call_name(
                        inner_func
                    )
                )

                if inner_name in {
                    "self.ensure_sync",
                    "ensure_sync",
                }:
                    return (
                        "the matched endpoint's "
                        "view function's result"
                    )

            call_name = (
                self._get_call_name(
                    value
                )
            )

            if call_name:

                return (
                    f"the result of "
                    f"`{call_name}()`"
                )

            return (
                "the result of a function call"
            )

        if isinstance(
            value,
            ast.Name,
        ):
            return (
                f"`{value.id}`"
            )

        if isinstance(
            value,
            ast.Attribute,
        ):
            return (
                f"`{self._get_attribute_name(value)}`"
            )

        if isinstance(
            value,
            ast.Constant,
        ):
            return repr(
                value.value
            )

        return (
            "the computed result"
        )

    # ================================================================
    # AST pattern helpers
    # ================================================================

    def _contains_call(
        self,
        tree,
        names,
    ):
        for node in ast.walk(
            tree
        ):
            if not isinstance(
                node,
                ast.Call,
            ):
                continue

            call_name = (
                self._get_call_name(
                    node
                )
            )

            if call_name in names:
                return True

        return False

    def _contains_assignment_to(
        self,
        tree,
        name,
    ):
        for node in ast.walk(
            tree
        ):
            if not isinstance(
                node,
                ast.Assign,
            ):
                continue

            for target in node.targets:

                if isinstance(
                    target,
                    ast.Name,
                ) and target.id == name:
                    return True

        return False

    def _contains_assignment_containing(
        self,
        tree,
        text,
    ):
        for node in ast.walk(
            tree
        ):
            if not isinstance(
                node,
                ast.Assign,
            ):
                continue

            for target in node.targets:

                expression = (
                    self._expression_text(
                        target
                    )
                )

                if text in expression:
                    return True

        return False

    def _expression_text(
        self,
        node,
    ):
        if node is None:
            return ""

        try:
            return ast.unparse(
                node
            )

        except Exception:
            return ""

    # ================================================================
    # AST helpers
    # ================================================================

    def _has_ast_node(
        self,
        code,
        node_type,
    ):
        if not code:
            return False

        try:
            tree = ast.parse(
                textwrap.dedent(code)
            )

        except SyntaxError:
            return False

        return any(
            isinstance(
                node,
                node_type,
            )
            for node in ast.walk(
                tree
            )
        )

    def _get_raised_exception_names(
        self,
        code,
    ):
        names = []

        try:
            tree = ast.parse(
                textwrap.dedent(code)
            )

        except SyntaxError:
            return names

        for node in ast.walk(
            tree
        ):
            if not isinstance(
                node,
                ast.Raise,
            ):
                continue

            name = (
                self._get_exception_name(
                    node.exc
                )
            )

            if name:
                names.append(
                    name
                )

        return names

    def _get_exception_name(
        self,
        node,
    ):
        if node is None:
            return ""

        if isinstance(
            node,
            ast.Call,
        ):
            node = node.func

        if isinstance(
            node,
            ast.Name,
        ):
            return node.id

        if isinstance(
            node,
            ast.Attribute,
        ):
            return (
                self._get_attribute_name(
                    node
                )
            )

        return ""

    def _get_call_name(
        self,
        node,
    ):
        if not isinstance(
            node,
            ast.Call,
        ):
            return ""

        return (
            self._get_callable_name(
                node.func
            )
        )

    def _get_callable_name(
        self,
        node,
    ):
        if isinstance(
            node,
            ast.Name,
        ):
            return node.id

        if isinstance(
            node,
            ast.Attribute,
        ):
            return (
                self._get_attribute_name(
                    node
                )
            )

        return ""

    def _get_attribute_name(
        self,
        node,
    ):
        parts = []

        current = node

        while isinstance(
            current,
            ast.Attribute,
        ):
            parts.append(
                current.attr
            )

            current = current.value

        if isinstance(
            current,
            ast.Name,
        ):
            parts.append(
                current.id
            )

        parts.reverse()

        return ".".join(
            parts
        )

    def _current_method_name(
        self,
        code,
    ):
        try:
            tree = ast.parse(
                textwrap.dedent(code)
            )

        except SyntaxError:
            return ""

        for node in ast.walk(
            tree
        ):
            if isinstance(
                node,
                (
                    ast.FunctionDef,
                    ast.AsyncFunctionDef,
                ),
            ):
                return node.name

        return ""

    def _count_useful_calls(
        self,
        code,
    ):
        try:
            tree = ast.parse(
                textwrap.dedent(code)
            )

        except SyntaxError:
            return 0

        current_method = (
            self._current_method_name(
                code
            )
        )

        count = 0

        for node in ast.walk(
            tree
        ):
            if not isinstance(
                node,
                ast.Call,
            ):
                continue

            name = (
                self._get_call_name(
                    node
                )
            )

            if not name:
                continue

            if name in self.IGNORED_CALLS:
                continue

            if (
                name.startswith(
                    "self."
                )
                and name.split(".")[-1]
                == current_method
            ):
                continue

            count += 1

        return count

    # ================================================================
    # Graph relationships
    # ================================================================

    def _normalize_relationship(
        self,
        relationship,
    ):
        if isinstance(
            relationship,
            dict,
        ):
            return (
                relationship.get("type")
                or relationship.get(
                    "relationship"
                )
                or ""
            ).upper()

        if isinstance(
            relationship,
            str,
        ):
            if ":" in relationship:
                return (
                    relationship.split(
                        ":",
                        1,
                    )[0]
                    .strip()
                    .upper()
                )

            return (
                relationship.strip().upper()
            )

        return ""

    def _format_relationship(
        self,
        relationship,
    ):
        if not isinstance(
            relationship,
            dict,
        ):
            return ""

        rel_type = (
            self._normalize_relationship(
                relationship
            )
        )

        source = relationship.get(
            "source",
            "",
        )

        target = relationship.get(
            "target",
            "",
        )

        # Never show malformed relationships.
        if not source or not target:
            return ""

        # DEFINES is usually not useful in the final explanation.
        if rel_type == "DEFINES":
            return ""

        if rel_type == "CALLS":
            return (
                f"`{source}` calls `{target}`"
            )

        if rel_type == "INHERITS":
            return (
                f"`{source}` inherits from "
                f"`{target}`"
            )

        if rel_type == "INHERITS_METHOD":
            return (
                f"`{source}` inherits the method "
                f"`{target}`"
            )

        if rel_type == "IMPORTS":
            return (
                f"`{source}` imports `{target}`"
            )

        return (
            f"`{source}` — "
            f"{rel_type} → `{target}`"
        )

    # ================================================================
    # Implementation hierarchy
    # ================================================================

    def _implementation_structure(
        self,
        results,
        primary,
    ):
        primary_name = primary.get(
            "qualified_name",
            "",
        )

        if not primary_name:
            return []

        method_name = (
            primary_name.split(
                "."
            )[-1]
        )

        related = []

        for result in results:

            name = result.get(
                "qualified_name",
                "",
            )

            if not name:
                continue

            if name == primary_name:
                continue

            if (
                name.split(".")[-1]
                != method_name
            ):
                continue

            related.append(
                result
            )

        if not related:
            return []

        names = [
            primary_name
        ]

        names.extend(
            item["qualified_name"]
            for item in related
        )

        return [
            f"Multiple implementations of "
            f"`{method_name}` were retrieved: "
            f"{', '.join(names)}."
        ]

    # ================================================================
    # Related implementations
    # ================================================================

    def _related_implementations(
        self,
        results,
        primary,
    ):
        primary_name = primary.get(
            "qualified_name",
            "",
        )

        if not primary_name:
            return []

        method_name = (
            primary_name.split(
                "."
            )[-1]
        )

        related = []

        for result in results:

            name = result.get(
                "qualified_name",
                "",
            )

            if not name:
                continue

            if name == primary_name:
                continue

            if (
                name.split(".")[-1]
                != method_name
            ):
                continue

            related.append(
                result
            )

        return related[:5]

    # ================================================================
    # General utilities
    # ================================================================

    def _is_not_implemented(
        self,
        code,
    ):
        return (
            "NotImplementedError"
            in self._get_raised_exception_names(
                code
            )
        )

    def _deduplicate(
        self,
        items,
    ):
        seen = set()
        result = []

        for item in items:

            normalized = item.strip()

            if not normalized:
                continue

            if normalized in seen:
                continue

            seen.add(
                normalized
            )

            result.append(
                normalized
            )

        return result


# ====================================================================
# Standalone test
# ====================================================================

if __name__ == "__main__":

    generator = AnswerGenerator()

    sample_context = {
        "results": [
            {
                "qualified_name":
                    "Example.process",

                "file":
                    "example.py",

                "line":
                    10,

                "code":
                    """
def process(self, value):
    if value is None:
        return None

    result = self.transform(value)
    return result
""",

                "evidence": {
                    "bm25": {
                        "rank": 1
                    },
                    "semantic": {
                        "rank": 2
                    },
                },

                "graph_relationships": [
                    {
                        "source":
                            "Example.process",

                        "target":
                            "Example.transform",

                        "type":
                            "CALLS",
                    }
                ],
            }
        ]
    }

    print(
        generator.generate(
            "How does processing work?",
            sample_context,
        )
    )