from app.llm.base import LLMProvider
from app.llm.claude_provider import ClaudeProvider
from app.llm.openai_provider import OpenAIProvider
from app.llm.mock_provider import MockProvider


def get_llm_provider(provider: str) -> LLMProvider:
    """
    Return the requested LLM provider.
    """

    provider = provider.lower().strip()

    if provider == "claude":
        return ClaudeProvider()

    if provider == "openai":
        return OpenAIProvider()

    if provider == "mock":
        return MockProvider()

    raise ValueError(
        f"Unsupported LLM provider: {provider}. "
        "Choose 'claude', 'openai', or 'mock'."
    )