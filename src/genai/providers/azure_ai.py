import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from src.genai.base import GenAIRequest, GenAIResponse
from src.genai.providers.common import SYSTEM_PROMPT, parse_json_content, request_body


class AzureAIFoundryProvider:
    def __init__(self, config: dict[str, Any], provider_name: str = "azure_ai_foundry") -> None:
        self.provider_name = provider_name
        self.endpoint = _config_value(config, "endpoint", "endpoint_env").rstrip("/")
        self.api_key = _config_value(config, "api_key", "api_key_env")
        self.deployment = str(config.get("deployment", config.get("model", "")))
        self.api_version = str(config.get("api_version", "2024-10-21"))
        self.timeout_seconds = int(config.get("timeout_seconds", 60))
        self.temperature = float(config.get("temperature", 0.2))
        self.max_tokens = int(config.get("max_tokens", 1200))

    def complete(self, request: GenAIRequest) -> GenAIResponse:
        if not self.endpoint:
            raise RuntimeError("Azure AI endpoint is required.")
        if not self.api_key:
            raise RuntimeError("Azure AI API key is required.")
        if not self.deployment:
            raise RuntimeError("Azure AI deployment/model is required.")

        url = (
            f"{self.endpoint}/openai/deployments/{urllib.parse.quote(self.deployment)}"
            f"/chat/completions?api-version={urllib.parse.quote(self.api_version)}"
        )
        payload = {
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": request_body(request.task, request.payload)},
            ],
        }
        http_request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "api-key": self.api_key,
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(http_request, timeout=self.timeout_seconds) as response:
                raw = response.read().decode("utf-8")
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Azure AI request failed: {exc}") from exc

        parsed = json.loads(raw)
        content = parsed["choices"][0]["message"]["content"]
        return GenAIResponse(
            provider=self.provider_name,
            task=request.task,
            content=parse_json_content(content),
        )


def _config_value(config: dict[str, Any], value_key: str, env_key: str) -> str:
    if config.get(value_key):
        return str(config[value_key])
    if config.get(env_key):
        return os.getenv(str(config[env_key]), "")
    return ""
