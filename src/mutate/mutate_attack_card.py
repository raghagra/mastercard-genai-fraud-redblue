from typing import Any

from src.common.ids import stable_id
from src.genai.base import GenAIRequest, GenAIProvider
from src.genai.gateway import GenAIGateway
from src.genai.local_rules import LocalRulesProvider
from src.knowledge.load_attack_catalog import load_attack_cards


def propose_mutations(
    failure_analysis: dict[str, Any],
    provider: GenAIProvider | None = None,
    limit: int = 5,
    iteration_id: str | None = None,
) -> list[dict[str, Any]]:
    selected_provider = provider or GenAIGateway()
    cards_by_subtype = {
        card.payload["subtype"]: card.payload
        for card in load_attack_cards()
    }
    candidates: list[dict[str, Any]] = []

    for weakness in failure_analysis.get("weak_groups", [])[:limit]:
        attack_card = cards_by_subtype.get(weakness["subtype"])
        if not attack_card:
            continue
        request = GenAIRequest(
            task="attack_mutation",
            payload={"attack_card": attack_card, "weakness": weakness},
            context={"iteration_id": iteration_id} if iteration_id else {},
        )
        response = selected_provider.complete(request)
        candidate = _normalize_model_mutation(response.content, attack_card, weakness, response.provider)
        if not _is_reviewable_mutation(candidate):
            # A model may refuse or return malformed/non-JSON text. Do not
            # propagate it into review or training data; use the deterministic
            # defensive fallback and preserve a concise audit signal.
            fallback = LocalRulesProvider().complete(request)
            candidate = {
                "provider": fallback.provider,
                **fallback.content,
                "gateway_fallback": {
                    "from_provider": response.provider,
                    "to_provider": fallback.provider,
                    "reason": "model_output_failed_mutation_contract",
                },
            }
        candidate["review_evidence"] = _review_evidence(failure_analysis, weakness)
        candidates.append(candidate)

    return candidates


def _is_reviewable_mutation(candidate: dict[str, Any]) -> bool:
    required = {
        "mutation_id",
        "source_attack_id",
        "bucket",
        "subtype",
        "proposed_variant_name",
        "mutation_strategy",
        "rationale",
        "parameter_deltas",
        "suggested_generation_strategy",
    }
    return required.issubset(candidate) and isinstance(candidate["mutation_strategy"], list) and isinstance(
        candidate["suggested_generation_strategy"], dict
    ) and isinstance(candidate["parameter_deltas"], list)


def _normalize_model_mutation(
    content: dict[str, Any], attack_card: dict[str, Any], weakness: dict[str, Any], provider: str
) -> dict[str, Any]:
    """Retain useful structured model work while owning immutable safety/lineage fields.

    Small local models often omit IDs or restate card metadata. We repair only
    those mechanical fields and derive a transparent delta list. A response must
    still supply a non-empty rationale, strategy list, variant name, and at least
    one valid generation-strategy change to be accepted as model-generated.
    """
    if not isinstance(content, dict) or "raw_content" in content:
        return {"provider": provider, **content}
    if "mutation_focus" in content:
        return _normalize_mutation_intent(content, attack_card, weakness, provider)
    variant_name = str(content.get("proposed_variant_name", "")).strip()
    rationale = str(content.get("rationale", "")).strip()
    mutation_strategy = content.get("mutation_strategy")
    model_strategy = content.get("suggested_generation_strategy")
    if not variant_name or not rationale or not isinstance(mutation_strategy, list) or not mutation_strategy:
        return {"provider": provider, **content}
    strategy = _merged_generation_strategy(attack_card["generation_strategy"], model_strategy)
    if strategy is None:
        return {"provider": provider, **content}
    deltas = _strategy_deltas(attack_card["generation_strategy"], strategy)
    if not deltas:
        return {"provider": provider, **content}
    return {
        "provider": provider,
        "mutation_id": stable_id("mut", attack_card["attack_id"], weakness.get("group_key", ""), variant_name),
        "source_attack_id": attack_card["attack_id"],
        "bucket": attack_card["bucket"],
        "subtype": attack_card["subtype"],
        "proposed_variant_name": variant_name,
        "mutation_strategy": [str(item) for item in mutation_strategy if str(item).strip()],
        "rationale": rationale,
        "parameter_deltas": deltas,
        "suggested_generation_strategy": strategy,
        "expected_detection_pressure": weakness,
        "human_review_required": True,
        "model_contribution": {
            "normalized": True,
            "model_generated_fields": ["proposed_variant_name", "mutation_strategy", "rationale", "suggested_generation_strategy"],
        },
    }


def _normalize_mutation_intent(
    content: dict[str, Any], attack_card: dict[str, Any], weakness: dict[str, Any], provider: str
) -> dict[str, Any]:
    """Expand a small-model-friendly intent into bounded generator settings.

    The LLM supplies the novel naming, rationale, and chosen defensive focus.
    The backend owns numerical limits and immutable lineage, removing a common
    formatting failure mode without turning the model contribution into a facade.
    """
    variant_name = str(content.get("variant_name", "")).strip()
    rationale = str(content.get("rationale", "")).strip()
    focus = content.get("mutation_focus")
    allowed = {
        "increase_benign_overlap", "pace_attempts", "extend_campaign_window",
        "increase_edge_case_diversity",
    }
    selected = [str(item) for item in focus] if isinstance(focus, list) else []
    selected = [item for item in selected if item in allowed]
    if not variant_name or not rationale or not selected:
        return {"provider": provider, **content}
    strategy = _strategy_from_intent(attack_card["generation_strategy"], selected)
    deltas = _strategy_deltas(attack_card["generation_strategy"], strategy)
    return {
        "provider": provider,
        "mutation_id": stable_id("mut", attack_card["attack_id"], weakness.get("group_key", ""), variant_name),
        "source_attack_id": attack_card["attack_id"],
        "bucket": attack_card["bucket"],
        "subtype": attack_card["subtype"],
        "proposed_variant_name": variant_name,
        "mutation_strategy": selected,
        "rationale": rationale,
        "parameter_deltas": deltas,
        "suggested_generation_strategy": strategy,
        "expected_detection_pressure": weakness,
        "human_review_required": True,
        "model_contribution": {
            "normalized": True,
            "contract": "compact_mutation_intent",
            "model_generated_fields": ["variant_name", "rationale", "mutation_focus"],
        },
    }


def _strategy_from_intent(base: dict[str, Any], focus: list[str]) -> dict[str, Any]:
    strategy = dict(base)
    lower, upper = [float(value) for value in base["stealth_level_range"]]
    volume_low, volume_high = [int(value) for value in base["volume_range"]]
    if "increase_benign_overlap" in focus:
        strategy["stealth_level_range"] = [min(0.98, round(lower + 0.12, 2)), min(0.99, round(upper + 0.12, 2))]
    if "pace_attempts" in focus:
        strategy["volume_range"] = [max(1, round(volume_low * 0.6)), max(1, round(volume_high * 0.6))]
        strategy["volume_range"][1] = max(strategy["volume_range"])
    if "extend_campaign_window" in focus:
        strategy["time_window_multiplier"] = 2.0
    if "increase_edge_case_diversity" in focus:
        strategy["noise_level"] = "high"
    return strategy


def _merged_generation_strategy(base: dict[str, Any], proposed: Any) -> dict[str, Any] | None:
    if not isinstance(proposed, dict):
        return None
    merged = dict(base)
    changed = False
    if _valid_float_range(proposed.get("stealth_level_range"), 0.0, 1.0):
        merged["stealth_level_range"] = [round(float(value), 2) for value in proposed["stealth_level_range"]]
        changed = merged["stealth_level_range"] != base.get("stealth_level_range")
    if _valid_int_range(proposed.get("volume_range"), 1):
        merged["volume_range"] = [int(value) for value in proposed["volume_range"]]
        changed = changed or merged["volume_range"] != base.get("volume_range")
    if proposed.get("noise_level") in {"low", "medium", "high"}:
        merged["noise_level"] = proposed["noise_level"]
        changed = changed or merged["noise_level"] != base.get("noise_level")
    multiplier = proposed.get("time_window_multiplier")
    if isinstance(multiplier, (int, float)) and 0.25 <= float(multiplier) <= 8:
        merged["time_window_multiplier"] = round(float(multiplier), 2)
        changed = changed or merged["time_window_multiplier"] != base.get("time_window_multiplier", 1.0)
    return merged if changed else None


def _valid_float_range(value: Any, lower: float, upper: float) -> bool:
    return isinstance(value, list) and len(value) == 2 and all(isinstance(item, (int, float)) for item in value) and lower <= float(value[0]) <= float(value[1]) <= upper


def _valid_int_range(value: Any, lower: int) -> bool:
    return isinstance(value, list) and len(value) == 2 and all(isinstance(item, int) for item in value) and lower <= value[0] <= value[1]


def _strategy_deltas(base: dict[str, Any], proposed: dict[str, Any]) -> list[dict[str, Any]]:
    purposes = {
        "stealth_level_range": "Change benign-feature overlap in the simulated campaign.",
        "volume_range": "Change campaign volume and velocity pressure.",
        "noise_level": "Change edge-case diversity in generated records.",
        "time_window_multiplier": "Change how activity is distributed across time.",
    }
    return [
        {"field": key, "baseline": base.get(key, 1.0 if key == "time_window_multiplier" else ""), "proposed": value, "purpose": purposes[key]}
        for key, value in proposed.items()
        if key in purposes and value != base.get(key, 1.0 if key == "time_window_multiplier" else "")
    ]


def _review_evidence(failure_analysis: dict[str, Any], weakness: dict[str, Any]) -> dict[str, Any]:
    subtype = str(weakness.get("subtype", ""))
    examples = [
        row for row in failure_analysis.get("false_negatives", [])
        if isinstance(row, dict) and row.get("attack_subtype") == subtype
    ]
    if not examples:
        examples = [
            row for row in failure_analysis.get("low_confidence_fraud", [])
            if isinstance(row, dict) and row.get("attack_subtype") == subtype
        ]
    return {
        "evaluation_scope": failure_analysis.get("evaluation_scope", "all_rows"),
        "selection_reason": weakness.get("reason", "lowest_confidence_fraud_group"),
        "threshold": failure_analysis.get("threshold"),
        "fraud_count": weakness.get("fraud_count", 0),
        "miss_count": weakness.get("miss_count", 0),
        "recall": weakness.get("recall"),
        "average_fraud_score": weakness.get("avg_fraud_score"),
        "representative_records": examples[:3],
    }
