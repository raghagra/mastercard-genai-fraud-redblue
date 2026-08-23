from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True)
class GenAIRequest:
    task: str
    payload: dict[str, Any]
    context: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class GenAIResponse:
    provider: str
    task: str
    content: dict[str, Any]


class GenAIProvider(Protocol):
    provider_name: str

    def complete(self, request: GenAIRequest) -> GenAIResponse:
        """Return a structured response for a GenAI-style task."""
