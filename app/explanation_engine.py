class ExplanationEngine:

    def explain(self, result):
        explanations = []

        evidence = result.get(
            "evidence",
            {}
        )

        if "bm25" in evidence:
            explanations.append(
                f"BM25 retrieved this result at rank "
                f"{evidence['bm25']['rank']}"
            )

        if "semantic" in evidence:
            explanations.append(
                f"Semantic retrieval found this result at rank "
                f"{evidence['semantic']['rank']}"
            )

        if "graph" in evidence:
            explanations.append(
                f"Code graph retrieved this result at rank "
                f"{evidence['graph']['rank']}"
            )

        identifier = evidence.get(
            "identifier"
        )

        if identifier:

            score = identifier.get(
                "score",
                0.0
            )

            if score == 1.0:

                explanations.append(
                    "Exact identifier match detected"
                )

            elif score > 0:

                explanations.append(
                    "Partial identifier match detected"
                )

        if not explanations:

            explanations.append(
                "Result was retrieved by the hybrid search system"
            )

        return explanations

    # ==========================================================
    # Explain implementation path
    # ==========================================================

    def explain_implementation(
        self,
        implementation_path,
        path_results
    ):

        if not implementation_path:

            return (
                "The supplied repository evidence does not "
                "establish an implementation path."
            )

        # ------------------------------------------------------
        # Build lookup
        # ------------------------------------------------------

        result_lookup = {}

        for result in path_results or []:

            qualified_name = result.get(
                "qualified_name"
            )

            if qualified_name:

                result_lookup[
                    qualified_name
                ] = result

        steps = []

        # ------------------------------------------------------
        # Explain each path component using repository evidence
        # ------------------------------------------------------

        for index, qualified_name in enumerate(
            implementation_path
        ):

            result = result_lookup.get(
                qualified_name,
                {}
            )

            code = result.get(
                "code",
                ""
            )

            file_path = result.get(
                "file",
                ""
            )

            line = result.get(
                "line",
                ""
            )

            # --------------------------------------------------
            # Find the next component
            # --------------------------------------------------

            next_name = None

            if index + 1 < len(
                implementation_path
            ):

                next_name = implementation_path[
                    index + 1
                ]

            # --------------------------------------------------
            # Relationship to next component
            # --------------------------------------------------

            relationship = None

            relationships = result.get(
                "graph_relationships",
                []
            )

            for item in relationships:

                if (
                    item.get("direction") == "outgoing"
                    and
                    item.get("target") == next_name
                ):

                    relationship = item.get(
                        "type"
                    )

                    break

            # --------------------------------------------------
            # Deferred blueprint relationship
            # --------------------------------------------------

            if (
                qualified_name
                == "Blueprint.add_url_rule"
                and
                next_name
                == "Blueprint.record"
            ):

                steps.append(
                    "Blueprint.add_url_rule records a "
                    "deferred function through Blueprint.record()."
                )

                continue

            if (
                qualified_name
                == "Blueprint.record"
                and
                next_name
                == "BlueprintSetupState.add_url_rule"
            ):

                steps.append(
                    "Blueprint.record stores the deferred "
                    "function that later invokes "
                    "BlueprintSetupState.add_url_rule()."
                )

                continue

            # --------------------------------------------------
            # Direct CALLS relationship
            # --------------------------------------------------

            if (
                relationship == "CALLS"
                and
                next_name
            ):

                steps.append(
                    f"{qualified_name} directly calls "
                    f"{next_name}."
                )

            # --------------------------------------------------
            # Final path component
            # --------------------------------------------------

            elif next_name is None:

                operation = (
                    self._extract_operation(
                        code
                    )
                )

                if operation:

                    steps.append(
                        f"{qualified_name} {operation}."
                    )

                else:

                    location = ""

                    if file_path:

                        location = (
                            f" in {file_path}"
                        )

                    if line:

                        location += (
                            f" at line {line}"
                        )

                    steps.append(
                        f"{qualified_name} is the final "
                        f"implementation component"
                        f"{location}."
                    )

        if not steps:

            return (
                "The supplied repository evidence does not "
                "establish an implementation path."
            )

        return self._format_answer(
            implementation_path,
            steps
        )

    # ==========================================================
    # Extract concrete operation from source
    # ==========================================================

    def _extract_operation(
        self,
        code
    ):

        if not code:

            return None

        operations = []

        # ------------------------------------------------------
        # Common repository operations
        # ------------------------------------------------------

        operation_patterns = [
            (
                "url_map",
                "updates the application's URL map"
            ),

            (
                "view_functions",
                "stores the associated view function"
            ),

            (
                "dispatch_request",
                "dispatches the request to the matched endpoint"
            ),

            (
                "full_dispatch_request",
                "performs the request dispatch pipeline"
            ),

            (
                "handle_exception",
                "handles an exception"
            ),

            (
                "process_response",
                "processes the response"
            ),

            (
                "send_from_directory",
                "returns a file from the configured directory"
            ),

            (
                "set_cookie",
                "sets the response cookie"
            ),

            (
                "delete_cookie",
                "removes the response cookie"
            ),

            (
                "raise",
                "reraises the exception when no handler is available"
            )
        ]

        for token, description in operation_patterns:

            if token in code:

                operations.append(
                    description
                )

        if not operations:

            return None

        # Remove duplicates while preserving order.
        unique_operations = []

        for operation in operations:

            if operation not in unique_operations:

                unique_operations.append(
                    operation
                )

        return " and ".join(
            unique_operations
        )

    # ==========================================================
    # Format final deterministic explanation
    # ==========================================================

    def _format_answer(
        self,
        implementation_path,
        steps
    ):

        first = implementation_path[0]

        answer = (
            f"The repository evidence shows the implementation "
            f"starting at {first}:\n\n"
        )

        for index, step in enumerate(
            steps,
            start=1
        ):

            answer += (
                f"{index}. {step}\n"
            )

        return answer.strip()