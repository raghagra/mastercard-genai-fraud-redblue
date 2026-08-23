"""Selective LLM review for uncertain fraud decisions.

The primary classifier scores every record. This module samples a small set of
rows nearest to the decision threshold for a slower, structured second opinion.
It never sends synthetic labels or attack taxonomy to the LLM.
"""

from typing import Any

from src.detect.explain import explain_row
from src.genai.base import GenAIRequest, GenAIProvider
from src.genai.gateway import GenAIGateway
from src.genai.local_rules import LocalRulesProvider


def review_uncertain_rows(
    rows: list[dict[str, str]],
    scores: list[float],
    model: dict[str, Any],
    iteration_id: str | None = None,
    provider: GenAIProvider | None = None,
    max_reviews: int = 5,
    uncertainty_band: float = 0.15,
) -> dict[int, dict[str, Any]]:
    if max_reviews <= 0:
        return {}
    gateway = provider or GenAIGateway()
    threshold = float(model["threshold"])
    ordered = sorted(range(len(rows)), key=lambda index: abs(float(scores[index]) - threshold))
    selected = [index for index in ordered if abs(float(scores[index]) - threshold) <= uncertainty_band][:max_reviews]
    if len(selected) < max_reviews:
        selected.extend(index for index in ordered if index not in selected[:max_reviews])
    selected = selected[:max_reviews]

    reviews: dict[int, dict[str, Any]] = {}
    for index in selected:
        row = rows[index]
        request = GenAIRequest(
            task="defense_review",
            payload=_review_payload(row, float(scores[index]), threshold, model),
            context={"iteration_id": iteration_id, "transaction_id": row["transaction_id"]} if iteration_id else {"transaction_id": row["transaction_id"]},
        )
        response = gateway.complete(request)
        review = {"provider": response.provider, **response.content}
        if not _valid_review(review):
            fallback = LocalRulesProvider().complete(request)
            review = {
                "provider": fallback.provider,
                **fallback.content,
                "gateway_fallback": {
                    "from_provider": response.provider,
                    "to_provider": fallback.provider,
                    "reason": "model_output_failed_defense_review_contract",
                },
            }
        reviews[index] = review
    return reviews


def hybrid_decision(ml_score: float, threshold: float, review: dict[str, Any] | None) -> tuple[float, int, str]:
    if review is None:
        return ml_score, int(ml_score >= threshold), "ml_only"
    semantic_score = float(review["semantic_risk_score"])
    recommendation = str(review["recommendation"])
    final_score = round((0.7 * ml_score) + (0.3 * semantic_score), 6)
    final_prediction = int(final_score >= threshold or recommendation == "flag")
    return final_score, final_prediction, "hybrid_ml_llm"


def _review_payload(row: dict[str, str], ml_score: float, threshold: float, model: dict[str, Any]) -> dict[str, Any]:
    behavioral_keys = [
        "amount", "risk_score", "billing_shipping_mismatch", "customer_transaction_count",
        "merchant_transaction_count", "device_transaction_count", "session_transaction_count",
        "ip_transaction_count", "customer_account_age_days", "merchant_age_days",
        "device_ip_reputation_score", "device_failed_login_count",
    ]
    return {
        "transaction_reference": row["transaction_id"],
        "ml_fraud_score": round(ml_score, 6),
        "ml_threshold": threshold,
        "ml_reason_codes": explain_row(row, model, limit=3),
        "behavioral_signals": {key: row.get(key, "") for key in behavioral_keys if key in row},
    }


def _valid_review(review: dict[str, Any]) -> bool:
    if not {"semantic_risk_score", "novelty_score", "recommendation", "rationale", "risk_indicators"}.issubset(review):
        return False
    try:
        return 0 <= float(review["semantic_risk_score"]) <= 1 and 0 <= float(review["novelty_score"]) <= 1 and str(review["recommendation"]) in {"allow", "review", "step_up_authentication", "flag"}
    except (TypeError, ValueError):
        return False
