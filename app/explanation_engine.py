class ExplanationEngine:

    def explain(self, result):
        """
        Convert retrieval evidence into a
        human-readable explanation.
        """

        explanations = []

        evidence = result.get(
            "evidence",
            {}
        )

        # ----------------------------------------------
        # BM25 evidence
        # ----------------------------------------------

        if "bm25" in evidence:

            rank = evidence["bm25"]["rank"]

            explanations.append(
                f"BM25 retrieved this result at rank {rank}"
            )

        # ----------------------------------------------
        # Semantic evidence
        # ----------------------------------------------

        if "semantic" in evidence:

            rank = evidence["semantic"]["rank"]

            explanations.append(
                f"Semantic retrieval found this result at rank {rank}"
            )

        # ----------------------------------------------
        # Graph evidence
        # ----------------------------------------------

        if "graph" in evidence:

            rank = evidence["graph"]["rank"]

            explanations.append(
                f"Code graph retrieved this result at rank {rank}"
            )

        # ----------------------------------------------
        # Identifier evidence
        # ----------------------------------------------

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

        # ----------------------------------------------
        # No evidence fallback
        # ----------------------------------------------

        if not explanations:

            explanations.append(
                "Result was retrieved by the hybrid search system"
            )

        return explanations
if __name__ == "__main__":

    engine = ExplanationEngine()

    test_result = {
        "qualified_name": "App.add_url_rule",

        "evidence": {
            "bm25": {
                "rank": 2
            },

            "graph": {
                "rank": 6
            },

            "identifier": {
                "score": 1.0
            }
        }
    }

    explanations = engine.explain(
        test_result
    )

    print("\nExplanation:\n")

    for explanation in explanations:

        print(
            f"✓ {explanation}"
        )