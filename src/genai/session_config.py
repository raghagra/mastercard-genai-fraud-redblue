from threading import Lock
from typing import Any

from src.genai.config import GenAIConfig, genai_config_from_dict


SECRET_KEYS = {"api_key", "apiKey", "access_key", "secret_key", "client_secret", "token"}


class GenAISessionConfigStore:
    """Process-local runtime config store for prototype/UI configuration.

    This is intentionally in-memory. In production, the same interface can be
    backed by a database plus a cloud secret manager or enterprise vault.
    """

    def __init__(self) -> None:
        self._lock = Lock()
        self._payload: dict[str, Any] | None = None

    def set(self, payload: dict[str, Any]) -> GenAIConfig:
        config = genai_config_from_dict(payload)
        with self._lock:
            self._payload = config.to_dict()
        return config

    def get(self) -> GenAIConfig | None:
        with self._lock:
            if self._payload is None:
                return None
            return genai_config_from_dict(dict(self._payload))

    def get_redacted(self) -> dict[str, Any] | None:
        with self._lock:
            if self._payload is None:
                return None
            return _redact(self._payload)

    def clear(self) -> None:
        with self._lock:
            self._payload = None


SESSION_CONFIG = GenAISessionConfigStore()


def _redact(value: Any) -> Any:
    if isinstance(value, dict):
        redacted = {}
        for key, item in value.items():
            if key in SECRET_KEYS or any(secret in key.lower() for secret in ["key", "secret", "token"]):
                redacted[key] = "***redacted***" if item else item
            else:
                redacted[key] = _redact(item)
        return redacted
    if isinstance(value, list):
        return [_redact(item) for item in value]
    return value
