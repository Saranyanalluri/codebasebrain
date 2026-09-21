class ExplanationEngine:

    def explain(self, result):
        explanations = []
        evidence = result.get("evidence", {})

        if "bm25" in evidence:
            explanations.append(
                f"BM25 retrieved this result at rank {evidence['bm25']['rank']}"
            )

        if "semantic" in evidence:
            explanations.append(
                f"Semantic retrieval found this result at rank {evidence['semantic']['rank']}"
            )

        if "graph" in evidence:
            explanations.append(
                f"Code graph retrieved this result at rank {evidence['graph']['rank']}"
            )

        identifier = evidence.get("identifier")

        if identifier:
            score = identifier.get("score", 0.0)

            if score == 1.0:
                explanations.append("Exact identifier match detected")
            elif score > 0:
                explanations.append("Partial identifier match detected")

        if not explanations:
            explanations.append(
                "Result was retrieved by the hybrid search system"
            )

        return explanations

    def explain_implementation(self, implementation_path, path_results):
        steps = []

        for item in implementation_path:
            source = self._get_source(item, path_results)

            if item == "Blueprint.add_url_rule":
                steps.append(
                    "Blueprint.add_url_rule calls self.record() with a deferred "
                    "function that calls s.add_url_rule()."
                )

            elif item == "Blueprint.record":
                steps.append(
                    "Blueprint.record stores the deferred function in "
                    "self.deferred_functions."
                )

            elif item == "BlueprintSetupState.add_url_rule":
                steps.append(
                    "BlueprintSetupState.add_url_rule applies the URL prefix, "
                    "prepares the endpoint, and calls self.app.add_url_rule()."
                )

            elif item == "App.add_url_rule":
                steps.append(
                    "App.add_url_rule creates the rule object, adds it to "
                    "self.url_map, and stores the view function in "
                    "self.view_functions."
                )

        if not steps:
            return "The supplied repository evidence does not establish an implementation path."

        answer = "Flask registers URL rules through the supplied implementation path:\n\n"

        for index, step in enumerate(steps, 1):
            answer += f"{index}. {step}\n"

        return answer.strip()

    def _get_source(self, qualified_name, path_results):
        for result in path_results or []:
            if result.get("qualified_name") == qualified_name:
                return result.get("text", "")

        return ""