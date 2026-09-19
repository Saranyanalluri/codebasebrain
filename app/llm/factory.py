from app.llm.base import LLMProvider
from app.llm.claude_provider import ClaudeProvider
from app.llm.openai_provider import OpenAIProvider
from app.llm.mock_provider import MockProvider
from app.llm.local_provider import LocalProvider


def get_llm_provider(provider: str) -> LLMProvider:
    provider = provider.lower().strip()

    if provider == "claude":
        return ClaudeProvider()

    if provider == "openai":
        return OpenAIProvider()

    if provider == "mock":
        return MockProvider()

    if provider == "local":
        return LocalProvider()

    raise ValueError(
        f"Unsupported LLM provider: {provider}. "
        "Choose 'claude', 'openai', 'local', or 'mock'."
    )