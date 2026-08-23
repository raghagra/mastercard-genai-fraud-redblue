import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.common.config import get_project_paths
from src.common.io import read_json


GENAI_CONFIG_ENV = "GENAI_CONFIG_PATH"


@dataclass(frozen=True)
class GenAIConfig:
    default_provider: str
    fallback_provider: str
    task_routes: dict[str, str]
    providers: dict[str, dict[str, Any]]
    budget: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "default_provider": self.default_provider,
            "fallback_provider": self.fallback_provider,
            "task_routes": self.task_routes,
            "providers": self.providers,
            "budget": self.budget,
        }


def load_genai_config(path: str | Path | None = None) -> GenAIConfig:
    config_path = _resolve_config_path(path)
    payload = read_json(config_path)
    if not isinstance(payload, dict):
        raise ValueError(f"GenAI config must be a JSON object: {config_path}")

    return GenAIConfig(
        default_provider=str(payload.get("default_provider", "local_rules")),
        fallback_provider=str(payload.get("fallback_provider", "local_rules")),
        task_routes=dict(payload.get("task_routes", {})),
        providers=dict(payload.get("providers", {})),
        budget=dict(payload.get("budget", {})),
    )


def genai_config_from_dict(payload: dict[str, Any]) -> GenAIConfig:
    return GenAIConfig(
        default_provider=str(payload.get("default_provider", "local_rules")),
        fallback_provider=str(payload.get("fallback_provider", "local_rules")),
        task_routes=dict(payload.get("task_routes", {})),
        providers=dict(payload.get("providers", {})),
        budget=dict(payload.get("budget", {})),
    )


def _resolve_config_path(path: str | Path | None) -> Path:
    if path is not None:
        return Path(path)

    env_path = os.getenv(GENAI_CONFIG_ENV)
    if env_path:
        return Path(env_path)

    root = get_project_paths().root
    project_config = root / "configs" / "genai_providers.json"
    if project_config.exists():
        return project_config
    return root / "configs" / "genai_providers.example.json"
