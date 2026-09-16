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
        sections = []

        sections.append(
            "You are CodebaseBrain, an AI assistant that explains software repositories."
        )

        sections.append(
            "Answer the user's question using ONLY the repository context provided below."
        )

        sections.append(
            "Do not invent functions, files, behavior, or relationships that are not "
            "supported by the context."
        )

        sections.append(
            "When useful, mention the relevant file paths, function/class names, "
            "implementation flow, and code relationships."
        )

        sections.append(
            f"\nUSER QUESTION:\n{query}"
        )

        sections.append("\nREPOSITORY CONTEXT:")

        for index, result in enumerate(context.get("results", []), start=1):
            sections.append(
                f"\n--- RESULT {index} ---\n"
                f"Qualified name: {result.get('qualified_name', '')}\n"
                f"Type: {result.get('type', '')}\n"
                f"File: {result.get('file', '')}\n"
                f"Line: {result.get('line', '')}\n"
                f"Final score: {result.get('final_score', '')}\n"
            )

            explanation = result.get("explanation")

            if explanation:
                sections.append(
                    "Retrieval explanation:\n"
                    + "\n".join(f"- {item}" for item in explanation)
                )

            relationships = result.get("graph_relationships", [])

            if relationships:
                sections.append(
                    "Code graph relationships:\n"
                    + "\n".join(f"- {item}" for item in relationships)
                )

            code = result.get("code", "")

            if code:
                sections.append(
                    f"Source code:\n```python\n{code}\n```"
                )

        sections.append(
            "\nProvide a concise but technically useful answer. "
            "Explain the implementation path when multiple related components "
            "are involved."
        )

        return "\n".join(sections)