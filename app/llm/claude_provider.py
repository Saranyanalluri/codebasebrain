import os

from anthropic import Anthropic

from app.llm.base import LLMProvider


class ClaudeProvider(LLMProvider):
    """
    Claude implementation of the CodebaseBrain LLM provider.
    """

    def __init__(self, model="claude-sonnet-5"):
        api_key = os.getenv("ANTHROPIC_API_KEY")

        if not api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY environment variable is not configured."
            )

        self.client = Anthropic(api_key=api_key.strip())
        self.model = model

    def generate(self, prompt: str) -> str:
        response = self.client.messages.create(
            model=self.model,
            max_tokens=2000,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
        )

        return response.content[0].text