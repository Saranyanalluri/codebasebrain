from app.llm.base import LLMProvider


class MockProvider(LLMProvider):
    """
    Free local provider used to test the LLM pipeline
    without calling an external API.
    """

    def generate(self, prompt: str) -> str:
        return (
            "This is a test response from CodebaseBrain's mock LLM. "
            "The RAG pipeline successfully produced context for the LLM."
        )