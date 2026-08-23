from typing import Any

from src.detect.metrics import classification_metrics


def metrics_for_rows(
    rows: list[dict[str, str]], threshold: float | None = None, score_key: str = "fraud_score"
) -> dict[str, Any]:
    import numpy as np

    if not rows:
        return {}

    y_true = np.array([_to_int(row["label"]) for row in rows], dtype=int)
    scores = np.array([_to_float(row.get(score_key, row["fraud_score"])) for row in rows], dtype=float)
    selected_threshold = threshold if threshold is not None else 0.5
    return classification_metrics(y_true, scores, selected_threshold)


def grouped_metrics(
    rows: list[dict[str, str]],
    group_key: str,
    threshold: float | None = None,
) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        key = row.get(group_key) or "benign"
        grouped.setdefault(key, []).append(row)

    output: list[dict[str, Any]] = []
    for key, group_rows in sorted(grouped.items()):
        metrics = metrics_for_rows(group_rows, threshold=threshold)
        output.append(
            {
                group_key: key,
                "row_count": len(group_rows),
                "positive_count": sum(1 for row in group_rows if _to_int(row["label"]) == 1),
                "negative_count": sum(1 for row in group_rows if _to_int(row["label"]) == 0),
                **metrics,
            }
        )
    return output


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
