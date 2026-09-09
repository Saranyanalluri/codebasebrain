class AnswerGenerator:
    """
    Generates a deterministic answer from retrieved code context.

    This is intentionally a local/mock answer generator.
    A real LLM can be plugged into the same interface later.
    """

    def generate(self, query, context):
        results = context.get("results", [])

        if not results:
            return (
                "I could not find relevant code in the repository "
                "for this question."
            )

        answer_parts = []

        answer_parts.append(
            f"Based on the retrieved code, the answer to "
            f"'{query}' is:\n"
        )

        # Use the highest-ranked result as the primary explanation.
        primary = results[0]

        symbol = primary.get("qualified_name", "Unknown")
        file = primary.get("file", "Unknown")
        line = primary.get("line", "Unknown")

        answer_parts.append(
            f"The most relevant implementation is `{symbol}`, "
            f"located in `{file}` at line {line}."
        )

        explanation = primary.get("explanation", [])

        if explanation:
            answer_parts.append("\nRetrieval evidence:")

            for reason in explanation:
                answer_parts.append(f"- {reason}")

        code = primary.get("code", "")

        if code:
            answer_parts.append("\nRelevant code:\n")
            answer_parts.append("```python")
            answer_parts.append(code)
            answer_parts.append("```")

        # Mention additional relevant implementations.
        if len(results) > 1:
            answer_parts.append("\nOther relevant implementations:")

            for result in results[1:4]:
                name = result.get("qualified_name", "Unknown")
                result_file = result.get("file", "Unknown")
                result_line = result.get("line", "Unknown")

                answer_parts.append(
                    f"- `{name}` — "
                    f"{result_file}:{result_line}"
                )

        return "\n".join(answer_parts)


if __name__ == "__main__":
    generator = AnswerGenerator()

    test_context = {
        "results": [
            {
                "qualified_name": "App.add_url_rule",
                "file": "sansio\\app.py",
                "line": 605,
                "explanation": [
                    "BM25 retrieved this result at rank 2",
                    "Code graph retrieved this result at rank 5",
                    "Exact identifier match detected",
                ],
                "code": (
                    "def add_url_rule(self, rule, endpoint=None, "
                    "view_func=None, **options):\n"
                    "    self.url_map.add(rule)\n"
                ),
            }
        ]
    }

    answer = generator.generate(
        "How does Flask register URL rules?",
        test_context,
    )

    print("\nGenerated Answer:\n")
    print(answer)