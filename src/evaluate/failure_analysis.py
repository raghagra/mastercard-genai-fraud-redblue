import csv
from collections import defaultdict
from pathlib import Path
from typing import Any

from src.common.config import get_project_paths
from src.common.io import read_json, write_json


def analyze_detector_failures(
    scores_path: str | Path | None = None,
    train_metrics_path: str | Path | None = None,
    output_path: str | Path | None = None,
    transaction_ids: set[str] | None = None,
) -> dict[str, Any]:
    paths = get_project_paths()
    source_scores = Path(scores_path) if scores_path is not None else paths.outputs_dir / "scores" / "scores.csv"
    source_metrics = (
        Path(train_metrics_path)
        if train_metrics_path is not None
        else paths.outputs_dir / "metrics" / "train_metrics.json"
    )
    target_path = (
        Path(output_path)
        if output_path is not None
        else paths.outputs_dir / "reports" / "failure_analysis.json"
    )
    rows = _read_csv(source_scores)
    if transaction_ids is not None:
        rows = [row for row in rows if row.get("transaction_id") in transaction_ids]
    metrics = read_json(source_metrics)
    threshold = float(metrics["threshold"])

    analysis = {
        "threshold": threshold,
        "row_count": len(rows),
        "evaluation_scope": "heldout_attack_benchmark" if transaction_ids is not None else "all_rows",
        "false_positives": _filter(rows, label="0", prediction="1"),
        "false_negatives": _filter(rows, label="1", prediction="0"),
        "low_confidence_fraud": _low_confidence_fraud(rows, threshold),
        "high_risk_benign": _high_risk_benign(rows, threshold),
        "weak_groups": _weak_groups(rows, threshold),
    }
    write_json(target_path, analysis)
    return analysis


def _weak_groups(rows: list[dict[str, str]], threshold: float) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        if row.get("label") == "1":
            grouped[(row.get("attack_bucket", ""), row.get("attack_subtype", ""))].append(row)

    weak: list[dict[str, Any]] = []
    for (bucket, subtype), group_rows in grouped.items():
        scores = [_to_float(row["fraud_score"]) for row in group_rows]
        misses = [row for row in group_rows if row.get("prediction") == "0"]
        avg_score = sum(scores) / len(scores)
        weak.append(
            {
                "group_key": subtype,
                "bucket": bucket,
                "subtype": subtype,
                "fraud_count": len(group_rows),
                "miss_count": len(misses),
                "recall": round(1 - len(misses) / len(group_rows), 6),
                "avg_fraud_score": round(avg_score, 6),
                "reason": "false_negative" if misses else "lowest_confidence_fraud_group",
            }
        )

    return sorted(weak, key=lambda item: (item["recall"], item["avg_fraud_score"]))[:8]


def _low_confidence_fraud(rows: list[dict[str, str]], threshold: float) -> list[dict[str, Any]]:
    fraud_rows = [row for row in rows if row.get("label") == "1"]
    ranked = sorted(fraud_rows, key=lambda row: _to_float(row["fraud_score"]))
    return [_compact_row(row, threshold) for row in ranked[:10]]


def _high_risk_benign(rows: list[dict[str, str]], threshold: float) -> list[dict[str, Any]]:
    benign_rows = [row for row in rows if row.get("label") == "0"]
    ranked = sorted(benign_rows, key=lambda row: _to_float(row["fraud_score"]), reverse=True)
    return [_compact_row(row, threshold) for row in ranked[:10]]


def _filter(rows: list[dict[str, str]], label: str, prediction: str) -> list[dict[str, Any]]:
    return [
        _compact_row(row, threshold=None)
        for row in rows
        if row.get("label") == label and row.get("prediction") == prediction
    ]


def _compact_row(row: dict[str, str], threshold: float | None) -> dict[str, Any]:
    score = _to_float(row.get("fraud_score", "0"))
    compact = {
        "transaction_id": row.get("transaction_id", ""),
        "fraud_score": score,
        "prediction": _to_int(row.get("prediction", "0")),
        "label": _to_int(row.get("label", "0")),
        "attack_bucket": row.get("attack_bucket", ""),
        "attack_subtype": row.get("attack_subtype", ""),
        "reason_codes": row.get("reason_codes", ""),
    }
    if threshold is not None:
        compact["margin_to_threshold"] = round(score - threshold, 6)
    return compact


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def _to_float(value: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _to_int(value: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0
