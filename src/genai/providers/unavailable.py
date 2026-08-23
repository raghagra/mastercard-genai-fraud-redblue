from typing import Any

from src.genai.base import GenAIRequest, GenAIResponse


class UnavailableProvider:
    def __init__(self, provider_name: str, config: dict[str, Any]) -> None:
        self.provider_name = provider_name
        self.provider_type = str(config.get("type", "unknown"))
        self.enabled = bool(config.get("enabled", False))

    def complete(self, request: GenAIRequest) -> GenAIResponse:
        raise RuntimeError(
            f"Provider '{self.provider_name}' of type '{self.provider_type}' is configured "
            "but not implemented in this backend phase."
        )

