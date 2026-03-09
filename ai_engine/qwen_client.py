import os
from typing import Any

import requests


class QwenClient:
    def __init__(
        self,
        api_base: str,
        model: str,
        timeout_seconds: int = 90,
        temperature: float = 0.2,
        max_tokens: int = 2048,
    ) -> None:
        self.api_base = api_base.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.api_key = os.getenv("QWEN_API_KEY", "")

    def generate(self, prompt: str) -> str:
        if not self.api_key:
            raise ValueError("QWEN_API_KEY is not set")

        url = f"{self.api_base}/chat/completions"
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You generate production-ready unit tests."},
                {"role": "user", "content": prompt},
            ],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        response = requests.post(url, json=payload, headers=headers, timeout=self.timeout_seconds)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]
