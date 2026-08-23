from dataclasses import dataclass
from pathlib import Path

from src.common.config import get_project_paths
from src.common.schemas import SchemaValidationError, load_schema, validate_with_jsonschema
from src.knowledge.load_attack_catalog import AttackCardFile, load_attack_cards, summarize_catalog


@dataclass(frozen=True)
class CatalogValidationResult:
    valid: bool
    checked_count: int
    errors: list[str]
    summary: dict[str, object]


def validate_attack_catalog(
    cards_dir: str | Path | None = None,
    schema_path: str | Path | None = None,
) -> CatalogValidationResult:
    paths = get_project_paths()
    schema = load_schema(schema_path or paths.schemas_dir / "attack_card.schema.json")
    cards = load_attack_cards(cards_dir)
    errors = _validate_cards(cards, schema)

    return CatalogValidationResult(
        valid=not errors,
        checked_count=len(cards),
        errors=errors,
        summary=summarize_catalog(cards),
    )


def _validate_cards(cards: list[AttackCardFile], schema: dict[str, object]) -> list[str]:
    errors: list[str] = []
    seen_ids: set[str] = set()

    for card in cards:
        attack_id = str(card.payload.get("attack_id", ""))
        if attack_id in seen_ids:
            errors.append(f"{card.path.name}: duplicate attack_id '{attack_id}'")
        seen_ids.add(attack_id)

        try:
            validate_with_jsonschema(card.payload, schema)
        except SchemaValidationError as exc:
            errors.append(f"{card.path.name}: {exc}")

    return errors
