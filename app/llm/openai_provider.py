import os

from openai import OpenAI

from app.llm.base import LLMProvider


class OpenAIProvider(LLMProvider):
    """
    OpenAI implementation of the CodebaseBrain LLM provider.
    """

    def __init__(self, model="gpt-5.6"):
        api_key = os.getenv("OPENAI_API_KEY")

        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY environment variable is not configured."
            )

        self.client = OpenAI(api_key=api_key.strip())
        self.model = model

    def generate(self, prompt: str) -> str:
        response = self.client.responses.create(
            model=self.model,
            input=prompt,
        )

        return response.output_text