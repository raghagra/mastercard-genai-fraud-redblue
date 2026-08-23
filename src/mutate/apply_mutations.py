from copy import deepcopy
from typing import Any


def apply_mutations_to_attack_cards(
    attack_cards: list[dict[str, Any]],
    accepted_mutations: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    cards_by_id = {card["attack_id"]: card for card in attack_cards}
    mutated_cards = [deepcopy(card) for card in attack_cards]
    usage: list[dict[str, Any]] = []

    for mutation in accepted_mutations:
        source_attack_id = mutation.get("source_attack_id")
        source = cards_by_id.get(source_attack_id)
        if not source:
            usage.append(
                {
                    "mutation_id": mutation.get("mutation_id"),
                    "source_attack_id": source_attack_id,
                    "status": "skipped",
                    "reason": "source_attack_card_not_found",
                }
            )
            continue

        generated_card = deepcopy(source)
        generated_card["attack_id"] = f"{source_attack_id}__{mutation['mutation_id']}"
        generated_card["variant_name"] = mutation.get("proposed_variant_name", source["variant_name"])
        generated_card["generation_strategy"] = mutation.get(
            "suggested_generation_strategy",
            source["generation_strategy"],
        )
        generated_card["notes"] = (
            f"Runtime mutation generated from {source_attack_id}; "
            f"mutation_id={mutation['mutation_id']}"
        )
        generated_card["evaluation_tags"] = sorted(
            set(generated_card.get("evaluation_tags", [])) | {"runtime_mutation", "closed_loop"}
        )

        mutated_cards.append(generated_card)
        usage.append(
            {
                "mutation_id": mutation["mutation_id"],
                "source_attack_id": source_attack_id,
                "generated_attack_id": generated_card["attack_id"],
                "status": "applied",
                "review": mutation.get("review", {}),
            }
        )

    return mutated_cards, usage

