import requests

from app.llm.base import LLMProvider


class LocalProvider(LLMProvider):
    """
    Local LLM provider using a running llama-server instance.
    """

    def __init__(
        self,
        server_url="http://127.0.0.1:8080",
        model="Qwen2.5-Coder-1.5B",
    ):
        self.server_url = server_url.rstrip("/")
        self.model = model

    def generate(self, prompt: str) -> str:
        url = f"{self.server_url}/completion"

        payload = {
            "prompt": prompt,
            "n_predict": 300,
            "temperature": 0.2,
            "stream": False,
        }

        try:
            response = requests.post(
                url,
                json=payload,
                timeout=180,
            )
        except requests.Timeout:
            raise RuntimeError(
                "Local LLM server timed out after 3 minutes."
            )
        except requests.RequestException as exc:
            raise RuntimeError(
                f"Could not connect to llama-server: {exc}"
            )

        if response.status_code != 200:
            raise RuntimeError(
                f"llama-server returned HTTP {response.status_code}:\n"
                f"{response.text}"
            )

        data = response.json()

        return data.get("content", "").strip()