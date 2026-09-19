from app.llm import get_llm_provider


class LLMAnswerGenerator:
    """
    Generates repository-grounded answers using a configurable LLM.
    """

    def __init__(self, provider="mock"):
        self.provider = get_llm_provider(provider)

    def generate(self, query, context):
        prompt = self._build_prompt(query, context)

        return self.provider.generate(prompt)

    def _build_prompt(self, query, context):
        sections = [
            "You are CodebaseBrain, an AI assistant for understanding "
            "software repositories.",
            "",
            "Answer the user's question using ONLY the repository evidence.",
            "Do not invent code, functions, files, or relationships.",
            "Give a concise technical answer.",
            "Explain the implementation path when multiple functions are involved.",
            "Use actual function names and file paths.",
            "",
            f"USER QUESTION:",
            query,
            "",
            "REPOSITORY EVIDENCE:",
        ]

        results = context.get("results", [])

        # Only send the most relevant 3 results to the local model.
        for index, result in enumerate(results[:3], start=1):

            sections.append(
                f"""
--- RESULT {index} ---

Qualified name: {result.get("qualified_name", "")}
File: {result.get("file", "")}
Line: {result.get("line", "")}
"""
            )

            relationships = result.get("graph_relationships", [])

            if relationships:
                sections.append(
                    "Relationships:\n"
                    + "\n".join(
                        f"- {item}"
                        for item in relationships
                    )
                )

            code = result.get("code", "")

            if code:
                # Limit each code component sent to the local model.
                code_lines = code.splitlines()

                if len(code_lines) > 60:
                    code_lines = code_lines[:60]

                sections.append(
                    "Source code:\n```python\n"
                    + "\n".join(code_lines)
                    + "\n```"
                )

        sections.extend(
            [
                "",
                "ANSWER:",
                "Start with the direct answer.",
                "Then explain the implementation flow.",
                "Mention important classes, functions, and files.",
                "Keep the answer concise.",
            ]
        )

        return "\n".join(sections)