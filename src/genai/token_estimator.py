import json
from typing import Any


def estimate_tokens_from_text(text: str) -> int:
    if not text:
        return 0
    return max(1, round(len(text) / 4))


def estimate_tokens_from_payload(payload: Any) -> int:
    return estimate_tokens_from_text(json.dumps(payload, sort_keys=True))

