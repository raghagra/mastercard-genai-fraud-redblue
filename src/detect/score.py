import csv
from pathlib import Path
from typing import Any

from src.common.config import get_project_paths
from src.detect.explain import explain_row
from src.detect.train import load_model, model_scores
from src.detect.llm_review import hybrid_decision, review_uncertain_rows


def score_feature_rows(
    features_path: str | Path | None = None,
    model_path: str | Path | None = None,
    output_path: str | Path | None = None,
    iteration_id: str | None = None,
    enable_llm_review: bool = True,
    max_llm_reviews: int = 5,
) -> list[dict[str, Any]]:
    paths = get_project_paths()
    source_path = Path(features_path) if features_path is not None else paths.processed_data_dir / "features.csv"
    target_path = Path(output_path) if output_path is not None else paths.outputs_dir / "scores" / "scores.csv"

    rows = _read_csv(source_path)
    model = load_model(model_path)
    scores = model_scores(rows, model)
    threshold = float(model["threshold"])
    reviews = review_uncertain_rows(rows, [float(score) for score in scores], model, iteration_id=iteration_id, max_reviews=max_llm_reviews) if enable_llm_review else {}

    scored_rows: list[dict[str, Any]] = []
    for row, score in zip(rows, scores, strict=True):
        index = len(scored_rows)
        ml_score = round(float(score), 6)
        ml_prediction = int(score >= threshold)
        review = reviews.get(index)
        final_score, prediction, decision_engine = hybrid_decision(float(score), threshold, review)
        scored_rows.append(
            {
                "transaction_id": row["transaction_id"],
                "fraud_score": final_score,
                "prediction": prediction,
                "ml_fraud_score": ml_score,
                "ml_prediction": ml_prediction,
                "decision_engine": decision_engine,
                "llm_reviewed": int(review is not None),
                "llm_provider": review.get("provider", "") if review else "",
                "llm_semantic_risk_score": review.get("semantic_risk_score", "") if review else "",
                "llm_novelty_score": review.get("novelty_score", "") if review else "",
                "llm_recommendation": review.get("recommendation", "") if review else "",
                "llm_rationale": review.get("rationale", "") if review else "",
                "llm_risk_indicators": ";".join(review.get("risk_indicators", [])) if review else "",
                "llm_fallback": review.get("gateway_fallback", "") if review else "",
                "label": row["label"],
                "attack_bucket": row.get("attack_bucket", ""),
                "attack_subtype": row.get("attack_subtype", ""),
                "reason_codes": ";".join(explain_row(row, model, limit=3)),
            }
        )

    _write_csv(target_path, scored_rows)
    return scored_rows


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
