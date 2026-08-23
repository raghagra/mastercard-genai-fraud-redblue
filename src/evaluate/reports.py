import csv
from pathlib import Path
from typing import Any

from src.common.config import get_project_paths
from src.common.io import read_json, write_json
from src.evaluate.metrics import grouped_metrics, metrics_for_rows


def build_evaluation_report(
    scores_path: str | Path | None = None,
    train_metrics_path: str | Path | None = None,
    output_dir: str | Path | None = None,
) -> dict[str, Any]:
    paths = get_project_paths()
    source_scores = Path(scores_path) if scores_path is not None else paths.outputs_dir / "scores" / "scores.csv"
    source_train_metrics = (
        Path(train_metrics_path)
        if train_metrics_path is not None
        else paths.outputs_dir / "metrics" / "train_metrics.json"
    )
    target_dir = Path(output_dir) if output_dir is not None else paths.outputs_dir / "reports"
    train_metrics = read_json(source_train_metrics)
    threshold = float(train_metrics["threshold"])
    scored_rows = _read_csv(source_scores)

    overall = metrics_for_rows(scored_rows, threshold=threshold)
    ml_only_overall = metrics_for_rows(scored_rows, threshold=threshold, score_key="ml_fraud_score")
    by_bucket = grouped_metrics(scored_rows, "attack_bucket", threshold=threshold)
    by_subtype = grouped_metrics(scored_rows, "attack_subtype", threshold=threshold)
    error_rows = _error_rows(scored_rows)
    holdout = train_metrics.get("holdout", {}) if isinstance(train_metrics, dict) else {}
    heldout_ids = set(holdout.get("transaction_ids", [])) if isinstance(holdout, dict) else set()
    heldout_rows = [row for row in scored_rows if row.get("transaction_id") in heldout_ids]

    report = {
        "threshold": threshold,
        "row_count": len(scored_rows),
        "overall": overall,
        "ml_only_overall": ml_only_overall,
        "heldout_attack_benchmark": {
            "evaluation_strategy": train_metrics.get("evaluation_strategy", "row_stratified_split"),
            "heldout_attack_ids": holdout.get("attack_ids", []),
            "row_count": len(heldout_rows),
            "overall": metrics_for_rows(heldout_rows, threshold=threshold),
            "ml_only_overall": metrics_for_rows(
                heldout_rows, threshold=threshold, score_key="ml_fraud_score"
            ),
        },
        "hybrid_review_summary": {
            "reviewed_row_count": sum(1 for row in scored_rows if str(row.get("llm_reviewed", "0")) == "1"),
            "final_decision_engine": "hybrid_ml_llm",
        },
        "by_bucket": by_bucket,
        "by_subtype": by_subtype,
        "error_count": len(error_rows),
        "false_positive_count": sum(1 for row in error_rows if row["label"] == "0"),
        "false_negative_count": sum(1 for row in error_rows if row["label"] == "1"),
    }

    target_dir.mkdir(parents=True, exist_ok=True)
    write_json(target_dir / "evaluation_report.json", report)
    _write_csv(target_dir / "bucket_performance.csv", by_bucket)
    _write_csv(target_dir / "subtype_performance.csv", by_subtype)
    _write_csv(target_dir / "errors.csv", error_rows)
    return report


def _error_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    return [row for row in rows if str(row["label"]) != str(row["prediction"])]


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return

    fieldnames = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
