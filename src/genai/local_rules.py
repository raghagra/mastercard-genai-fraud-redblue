from typing import Any

from src.common.ids import stable_id
from src.genai.base import GenAIRequest, GenAIResponse


class LocalRulesProvider:
    """Deterministic stand-in for future LLM providers.

    It lets the loop exercise GenAI-shaped behavior without requiring cloud
    credentials, local model availability, or token spend.
    """

    provider_name = "local_rules"

    def complete(self, request: GenAIRequest) -> GenAIResponse:
        if request.task == "attack_mutation":
            content = _mutate_attack_card(request.payload)
        elif request.task == "defense_review":
            content = _defense_review(request.payload)
        elif request.task == "experiment_explanation":
            experiment = request.payload.get("experiment", {})
            deltas = experiment.get("metric_deltas", {})
            content = {
                "summary": (
                    "The controlled synthetic experiment compares matched baseline and mutated scenarios using the same frozen detector. "
                    f"Recall changed by {float(deltas.get('recall', 0)) * 100:+.2f} percentage points and F1 changed by "
                    f"{float(deltas.get('f1', 0)) * 100:+.2f} percentage points. Treat this as controlled simulation evidence, not a production claim."
                )
            }
        else:
            content = {
                "summary": "No local rule configured for this task.",
                "task": request.task,
            }
        return GenAIResponse(provider=self.provider_name, task=request.task, content=content)


def _mutate_attack_card(payload: dict[str, Any]) -> dict[str, Any]:
    attack_card = payload["attack_card"]
    weakness = payload["weakness"]
    base_strategy = attack_card["generation_strategy"]
    plan = _mutation_plan(attack_card, base_strategy)

    mutation_id = stable_id(
        "mut",
        attack_card["attack_id"],
        weakness.get("group_key", ""),
        weakness.get("reason", ""),
    )

    return {
        "mutation_id": mutation_id,
        "source_attack_id": attack_card["attack_id"],
        "bucket": attack_card["bucket"],
        "subtype": attack_card["subtype"],
        "proposed_variant_name": f"{attack_card['variant_name']} - {plan['suffix']}",
        "mutation_strategy": [*plan["strategies"], "preserve_attack_lineage"],
        "rationale": plan["rationale"],
        "parameter_deltas": plan["parameter_deltas"],
        "suggested_generation_strategy": plan["strategy"],
        "expected_detection_pressure": weakness,
        "human_review_required": True,
    }


def _mutation_plan(attack_card: dict[str, Any], base_strategy: dict[str, Any]) -> dict[str, Any]:
    """Return safe, subtype-specific pressure instead of a generic stealth template."""
    lower, upper = [float(value) for value in base_strategy["stealth_level_range"]]
    volume_low, volume_high = [int(value) for value in base_strategy["volume_range"]]
    bucket = attack_card["bucket"]
    subtype = attack_card["subtype"]

    stealth_lift = 0.10
    volume_multiplier = 0.75
    time_window_multiplier = 1.35
    suffix = "behavioral overlap variant"
    strategies = ["increase_benign_context_overlap"]
    rationale = (
        "Create a bounded defensive stress-test variant that retains the attack's payment "
        "objective while reducing the most obvious synthetic signals."
    )
    if subtype in {"card_testing", "credential_stuffing"}:
        stealth_lift, volume_multiplier, time_window_multiplier = 0.14, 0.40, 2.5
        suffix = "low-and-slow attempt pattern"
        strategies = ["pace_attempts_across_time", "reduce_burst_velocity", "retain_payment_instrument_signal"]
        rationale = (
            "Model a lower-and-slower credential attack: fewer attempts per campaign and "
            "more benign-looking context, while retaining the defensive signature of repeated payment attempts."
        )
    elif bucket == "social_engineering_payment_fraud":
        stealth_lift, volume_multiplier, time_window_multiplier = 0.12, 0.60, 1.8
        suffix = "trusted-context transfer variant"
        strategies = ["increase_trusted_context_overlap", "reduce_single_session_concentration", "retain_transfer_anomaly"]
        rationale = (
            "Stress-test whether the defense can recognize a socially engineered payment when "
            "the transfer is paced and surrounded by otherwise trusted-looking context."
        )
    elif bucket == "identity_onboarding_fraud":
        stealth_lift, volume_multiplier, time_window_multiplier = 0.16, 0.85, 1.5
        suffix = "mature-profile onboarding variant"
        strategies = ["increase_profile_maturity", "increase_benign_context_overlap", "retain_identity_inconsistency"]
        rationale = (
            "Stress-test identity controls with a mature-looking synthetic profile and less obvious "
            "operational noise, while retaining the underlying onboarding inconsistency."
        )
    elif bucket == "post_transaction_abuse":
        stealth_lift, volume_multiplier, time_window_multiplier = 0.11, 0.65, 2.0
        suffix = "plausible post-purchase variant"
        strategies = ["reduce_claim_velocity", "increase_purchase_context_overlap", "retain_post_transaction_signal"]
        rationale = (
            "Stress-test post-transaction controls using fewer, more plausible claims embedded in "
            "ordinary-looking purchase context, without changing the abuse outcome being simulated."
        )
    elif bucket == "merchant_ecosystem_abuse":
        stealth_lift, volume_multiplier, time_window_multiplier = 0.13, 0.55, 2.2
        suffix = "gradual merchant-lifecycle variant"
        strategies = ["reduce_volume_growth_spike", "increase_merchant_maturity", "retain_payout_or_marketplace_signal"]
        rationale = (
            "Stress-test merchant controls with a slower lifecycle and less conspicuous growth, while "
            "retaining the simulated merchant or payout anomaly."
        )

    proposed_stealth = [min(0.98, round(lower + stealth_lift, 2)), min(0.99, round(upper + stealth_lift, 2))]
    proposed_volume = [max(1, round(volume_low * volume_multiplier)), max(1, round(volume_high * volume_multiplier))]
    proposed_volume[1] = max(proposed_volume[0], proposed_volume[1])
    strategy = {
        **base_strategy,
        "stealth_level_range": proposed_stealth,
        "volume_range": proposed_volume,
        "noise_level": "high",
        "time_window_multiplier": time_window_multiplier,
    }
    return {
        "suffix": suffix,
        "strategies": strategies,
        "rationale": rationale,
        "strategy": strategy,
        "parameter_deltas": [
            {
                "field": "stealth_level_range",
                "baseline": [lower, upper],
                "proposed": proposed_stealth,
                "purpose": "Increase benign-feature overlap in the simulated campaign.",
            },
            {
                "field": "volume_range",
                "baseline": [volume_low, volume_high],
                "proposed": proposed_volume,
                "purpose": "Apply the subtype-specific campaign pacing change.",
            },
            {
                "field": "noise_level",
                "baseline": base_strategy.get("noise_level", "medium"),
                "proposed": "high",
                "purpose": "Broaden realistic edge cases without changing the fraud label.",
            },
            {
                "field": "time_window_multiplier",
                "baseline": float(base_strategy.get("time_window_multiplier", 1.0)),
                "proposed": time_window_multiplier,
                "purpose": "Spread events across a longer, more realistic campaign timeline.",
            },
        ],
    }


def _defense_review(payload: dict[str, Any]) -> dict[str, Any]:
    ml_score = float(payload.get("ml_fraud_score", 0.0))
    threshold = float(payload.get("ml_threshold", 0.5))
    indicators = list(payload.get("ml_reason_codes", []))[:3]
    semantic_risk = round(min(1.0, max(0.0, (ml_score * 0.85) + 0.08)), 4)
    novelty = round(min(1.0, 0.35 + abs(ml_score - threshold)), 4)
    if semantic_risk >= 0.75:
        recommendation = "flag"
    elif semantic_risk >= 0.5:
        recommendation = "step_up_authentication"
    elif semantic_risk >= 0.3:
        recommendation = "review"
    else:
        recommendation = "allow"
    return {
        "semantic_risk_score": semantic_risk,
        "novelty_score": novelty,
        "recommendation": recommendation,
        "rationale": "Deterministic defensive review based on the primary model score and supplied behavioral signals.",
        "risk_indicators": indicators,
    }
