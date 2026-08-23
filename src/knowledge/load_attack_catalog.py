from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.common.config import get_project_paths
from src.common.io import list_json_files, read_json


@dataclass(frozen=True)
class AttackCardFile:
    path: Path
    payload: dict[str, Any]


def load_attack_cards(path: str | Path | None = None) -> list[AttackCardFile]:
    cards_dir = Path(path) if path is not None else get_project_paths().attack_cards_dir
    cards: list[AttackCardFile] = []

    for json_path in list_json_files(cards_dir):
        payload = read_json(json_path)
        if not isinstance(payload, dict):
            raise ValueError(f"Attack card must be a JSON object: {json_path}")
        cards.append(AttackCardFile(path=json_path, payload=payload))

    return cards


def summarize_catalog(cards: list[AttackCardFile]) -> dict[str, Any]:
    buckets: dict[str, int] = {}
    subtypes: dict[str, int] = {}
    channels: dict[str, int] = {}
    rails: dict[str, int] = {}

    for card in cards:
        payload = card.payload
        _increment(buckets, payload.get("bucket", "<missing>"))
        _increment(subtypes, payload.get("subtype", "<missing>"))
        _increment(channels, payload.get("channel", "<missing>"))
        _increment(rails, payload.get("rail", "<missing>"))

    return {
        "total_cards": len(cards),
        "buckets": buckets,
        "subtypes": subtypes,
        "channels": channels,
        "rails": rails,
    }


def _increment(counter: dict[str, int], key: object) -> None:
    counter[str(key)] = counter.get(str(key), 0) + 1
