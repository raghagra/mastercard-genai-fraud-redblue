import json
import os
import urllib.error
import urllib.request
from typing import Any

from src.genai.base import GenAIRequest, GenAIResponse
from src.genai.providers.common import SYSTEM_PROMPT, parse_json_content, request_body


class LMStudioProvider:
    provider_name = "local_lmstudio"

    def __init__(self, config: dict[str, Any], provider_name: str = "local_lmstudio") -> None:
        self.provider_name = provider_name
        self.base_url = str(config.get("base_url", "http://localhost:1234/v1")).rstrip("/")
        self.model = str(config.get("model", "local-model"))
        # A session-configured key is useful for the prototype UI.  A named
        # environment variable remains the preferred production mechanism.
        self.api_key = str(config.get("api_key") or os.getenv(str(config.get("api_key_env", "")), "not-needed"))
        self.timeout_seconds = int(config.get("timeout_seconds", 60))
        self.temperature = float(config.get("temperature", 0.2))
        self.max_tokens = int(config.get("max_tokens", 1200))
        self.json_mode = bool(config.get("json_mode", True))

    def complete(self, request: GenAIRequest) -> GenAIResponse:
        payload = {
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "messages": [
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": request_body(request.task, request.payload),
                },
            ],
        }
        if self.json_mode:
            # LM Studio's OpenAI-compatible server supports JSON-object mode for
            # compatible models. This materially improves structured mutation
            # contracts without tying the gateway to one model family.
            payload["response_format"] = {"type": "json_object"}
        raw = self._post(payload)
        # Some local model/server combinations do not implement response_format.
        # Retry once in prompt-only mode rather than treating that capability gap
        # as an inference failure.
        if raw is None and self.json_mode:
            payload.pop("response_format", None)
            raw = self._post(payload)
        if raw is None:
            raise RuntimeError("LM Studio did not return a usable completion response")
        try:
            parsed = json.loads(raw)
            content = parsed["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"LM Studio response format was invalid: {exc}") from exc
        return GenAIResponse(
            provider=self.provider_name,
            task=request.task,
            content=parse_json_content(content),
        )

    def _post(self, payload: dict[str, Any]) -> str | None:
        data = json.dumps(payload).encode("utf-8")
        http_request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(http_request, timeout=self.timeout_seconds) as response:
                return response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            # A 4xx response can specifically mean JSON mode is unsupported.
            if exc.code in {400, 404, 422}:
                return None
            raise RuntimeError(f"LM Studio request failed: HTTP {exc.code}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"LM Studio request failed: {exc}") from exc
