from app.llm.factory import get_llm_provider


class LLMAnswerGenerator:

    def __init__(self, provider="local"):

        # If an actual provider object is supplied,
        # use it directly.
        if hasattr(provider, "generate"):
            self.provider = provider

        # Otherwise resolve the provider name through
        # the existing provider factory.
        else:
            self.provider = get_llm_provider(
                provider
            )

    def generate(self, query, context):

        # --------------------------------------------------
        # Use deterministic explanation if available
        # --------------------------------------------------

        deterministic = context.get(
            "implementation_explanation"
        )

        if deterministic:
            return deterministic

        # --------------------------------------------------
        # Build prompt
        # --------------------------------------------------

        prompt = self._build_prompt(
            query,
            context
        )

        print(
            "\n===== LLM PROMPT ====="
        )

        print(prompt)

        # --------------------------------------------------
        # Generate answer
        # --------------------------------------------------

        return self.provider.generate(
            prompt
        )

    def _build_prompt(
        self,
        query,
        context
    ):

        implementation_path = context.get(
            "implementation_path",
            context.get(
                "implementation_paths",
                []
            )
        )

        path_results = context.get(
            "path_results",
            []
        )

        return f"""
You are CodebaseBrain.

Answer using ONLY the supplied repository evidence.

USER QUESTION:
{query}

IMPLEMENTATION PATH:
{implementation_path}

SOURCE CODE:
{path_results}

Give a concise factual answer.
Do not speculate.
"""