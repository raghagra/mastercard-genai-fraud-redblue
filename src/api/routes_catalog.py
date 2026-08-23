from fastapi import APIRouter, HTTPException

from src.knowledge.load_attack_catalog import load_attack_cards, summarize_catalog
from src.knowledge.validate_attack_cards import validate_attack_catalog


router = APIRouter(prefix="/attack-catalog", tags=["attack-catalog"])


@router.get("")
def list_attack_catalog() -> dict[str, object]:
    cards = load_attack_cards()
    return {
        "summary": summarize_catalog(cards),
        "cards": [
            {
                "attack_id": card.payload["attack_id"],
                "bucket": card.payload["bucket"],
                "subtype": card.payload["subtype"],
                "attack_name": card.payload["attack_name"],
                "variant_name": card.payload["variant_name"],
                "channel": card.payload["channel"],
                "rail": card.payload["rail"],
                "scope": card.payload["scope"],
                "severity": card.payload["severity"],
            }
            for card in cards
        ],
    }


@router.get("/validate")
def validate_catalog() -> dict[str, object]:
    result = validate_attack_catalog()
    return {
        "valid": result.valid,
        "checked_count": result.checked_count,
        "errors": result.errors,
        "summary": result.summary,
    }


@router.get("/{attack_id}")
def get_attack_card(attack_id: str) -> dict[str, object]:
    for card in load_attack_cards():
        if card.payload["attack_id"] == attack_id:
            return card.payload
    raise HTTPException(status_code=404, detail=f"Attack card not found: {attack_id}")

