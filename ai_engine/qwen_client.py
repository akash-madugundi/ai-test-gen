import os
import random
import time
import uuid
from typing import Any, Optional

import requests


class QwenClient:
    def __init__(
        self,
        api_base: str,
        model: str,
        timeout_seconds: int = 300,
        temperature: float = 0.2,
        max_tokens: int = 2048,
        user: Optional[str] = None,
        auth_method: str = "",  # "BEARER", "S2B" (AMTOKEN) or "B2B" (JWT)
    ) -> None:
        self.api_base = api_base.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.temperature = temperature
        self.max_tokens = max_tokens

        self.user = user or os.getenv("AIGW_USER", "")
        self.api_key = os.getenv("QWEN_API_KEY", "").strip()
        self.amtoken = os.getenv("AMTOKEN", "").strip()
        self.jwt = os.getenv("JWT", "").strip()

        env_auth = os.getenv("AUTH_METHOD", "").strip().upper()
        explicit_auth = (auth_method or "").strip().upper()
        self.auth_method = explicit_auth or env_auth

        # Backward-compatible default: if QWEN_API_KEY exists, use Bearer.
        if not self.auth_method:
            self.auth_method = "BEARER" if self.api_key else "S2B"

        if self.auth_method == "BEARER" and not self.api_key:
            raise ValueError("QWEN_API_KEY is not set for BEARER authentication")

        if self.auth_method == "S2B":
            if not self.user:
                raise ValueError("AIGW_USER is not set for S2B authentication")
            if not self.amtoken:
                raise ValueError("AMTOKEN is not set for S2B authentication")

        if self.auth_method == "B2B":
            if not self.user:
                raise ValueError("AIGW_USER is not set for B2B authentication")
            if not self.jwt:
                raise ValueError("JWT is not set for B2B authentication")

    def _build_headers(self) -> dict[str, str]:
        headers: dict[str, str] = {
            "Content-Type": "application/json",
            "x-correlation-id": str(uuid.uuid4()),
            "x-usersession-id": str(uuid.uuid4()),
        }

        if self.auth_method == "BEARER":
            headers["Authorization"] = f"Bearer {self.api_key}"
            return headers

        if self.auth_method == "S2B":
            headers["AMToken"] = self.amtoken
            headers["Token_Type"] = "SESSION_TOKEN"
            return headers

        if self.auth_method == "B2B":
            headers["X-HSBC-E2E-Trust-Token"] = self.jwt
            return headers

        raise ValueError("AUTH_METHOD must be BEARER, S2B, or B2B")

    def generate(self, prompt: str) -> str:
        url = f"{self.api_base}/chat/completions"
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You generate production-ready unit tests."},
                {"role": "user", "content": prompt},
            ],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "user": self.user or None,
        }

        retry_statuses = {429, 502, 503, 504}
        max_attempts = 4
        base_sleep = 2.0
        last_exc: Exception | None = None

        for attempt in range(1, max_attempts + 1):
            try:
                response = requests.post(
                    url,
                    json=payload,
                    headers=self._build_headers(),
                    timeout=self.timeout_seconds,
                )

                if response.status_code in retry_statuses:
                    if attempt == max_attempts:
                        response.raise_for_status()
                    sleep_s = base_sleep * (2 ** (attempt - 1)) + random.uniform(0, 0.5)
                    time.sleep(sleep_s)
                    continue

                response.raise_for_status()
                data = response.json()
                msg = data["choices"][0]["message"]
                return msg.get("content") or msg.get("reasoning_content") or ""

            except (requests.Timeout, requests.ConnectionError) as exc:
                last_exc = exc
                if attempt == max_attempts:
                    raise
                sleep_s = base_sleep * (2 ** (attempt - 1)) + random.uniform(0, 0.5)
                time.sleep(sleep_s)

            except requests.HTTPError as exc:
                last_exc = exc
                status = getattr(exc.response, "status_code", None)
                if status not in retry_statuses:
                    raise
                if attempt == max_attempts:
                    raise
                sleep_s = base_sleep * (2 ** (attempt - 1)) + random.uniform(0, 0.5)
                time.sleep(sleep_s)

        raise last_exc if last_exc else RuntimeError("QwenClient.generate failed unexpectedly")
