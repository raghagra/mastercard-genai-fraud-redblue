import hashlib


def stable_id(prefix: str, *parts: object, length: int = 12) -> str:
    raw = "::".join(str(part) for part in parts)
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:length]
    return f"{prefix}_{digest}"

