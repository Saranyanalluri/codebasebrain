class LLMAnswerGenerator:

    def __init__(self, provider):
        self.provider = provider

    def generate(self, query, context):
        deterministic = context.get("implementation_explanation")

        if deterministic:
            return deterministic

        prompt = self._build_prompt(query, context)
        print("\n===== LLM PROMPT =====")
        print(prompt)

        return self.provider.generate(prompt)

    def _build_prompt(self, query, context):
        return f"""
You are CodebaseBrain.

Answer using ONLY the supplied repository evidence.

USER QUESTION:
{query}

IMPLEMENTATION PATH:
{context.get("implementation_path", [])}

SOURCE CODE:
{context.get("path_results", [])}

Give a concise factual answer.
Do not speculate.
"""