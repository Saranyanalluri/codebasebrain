from app.llm import get_llm_provider


class LLMAnswerGenerator:
    """
    Generates repository-grounded answers using an LLM.

    The LLM is instructed to use only the retrieved repository evidence
    and avoid inventing implementation details.
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
            "STRICT GROUNDING RULES:",
            "1. Answer ONLY from the repository evidence provided below.",
            "2. Do not use outside knowledge about the framework or library.",
            "3. Do not invent functions, variables, attributes, assignments, "
            "or relationships.",
            "4. Every implementation claim must be supported by the supplied "
            "source code or graph relationships.",
            "5. Follow CALLS and INHERITS_METHOD relationships when explaining "
            "the implementation path.",
            "6. Distinguish abstract/interface methods from concrete "
            "implementations.",
            "7. If the evidence does not establish something, do not claim it.",
            "",
            "ANSWER REQUIREMENTS:",
            "- Start with the direct answer.",
            "- Explain the implementation flow in order.",
            "- Use exact function and class names from the evidence.",
            "- Mention relevant file paths.",
            "- Keep the answer concise.",
            "",
            f"USER QUESTION:",
            query,
            "",
            "REPOSITORY EVIDENCE:",
        ]

        results = context.get("results", [])

        # Only send the strongest three retrieved components.
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

            formatted_relationships = []

            for relationship in relationships:
                if isinstance(relationship, dict):
                    relationship_type = relationship.get("type", "")
                    target = relationship.get("target", "")

                    if relationship_type == "DEFINES":
                        continue

                    if relationship_type and target:
                        formatted_relationships.append(
                            f"- {relationship_type}: {target}"
                        )

                elif isinstance(relationship, str):
                    if relationship.startswith("- DEFINES:"):
                        continue

                    formatted_relationships.append(relationship)

            if formatted_relationships:
                sections.append(
                    "Graph relationships:\n"
                    + "\n".join(formatted_relationships)
                )

            code = result.get("code", "")

            if code:
                code_lines = code.splitlines()

                if len(code_lines) > 60:
                    code_lines = code_lines[:60]

                sections.append(
                    "Source code:\n"
                    "```python\n"
                    + "\n".join(code_lines)
                    + "\n```"
                )

        sections.extend(
            [
                "",
                "FINAL ANSWER:",
                "Use only the evidence above.",
                "Do not add information that is not present in the evidence.",
            ]
        )

        return "\n".join(sections)