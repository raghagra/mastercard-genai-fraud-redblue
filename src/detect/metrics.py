from typing import Any

import numpy as np


def classification_metrics(y_true: np.ndarray, scores: np.ndarray, threshold: float) -> dict[str, Any]:
    predictions = (scores >= threshold).astype(int)
    true_positive = int(((predictions == 1) & (y_true == 1)).sum())
    true_negative = int(((predictions == 0) & (y_true == 0)).sum())
    false_positive = int(((predictions == 1) & (y_true == 0)).sum())
    false_negative = int(((predictions == 0) & (y_true == 1)).sum())

    precision = _safe_div(true_positive, true_positive + false_positive)
    recall = _safe_div(true_positive, true_positive + false_negative)
    f1 = _safe_div(2 * precision * recall, precision + recall)

    return {
        "threshold": threshold,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "accuracy": _safe_div(true_positive + true_negative, len(y_true)),
        "false_positive_rate": _safe_div(false_positive, false_positive + true_negative),
        "true_positive": true_positive,
        "true_negative": true_negative,
        "false_positive": false_positive,
        "false_negative": false_negative,
        "roc_auc": roc_auc(y_true, scores),
        "pr_auc": pr_auc(y_true, scores),
    }


def roc_auc(y_true: np.ndarray, scores: np.ndarray) -> float:
    positives = scores[y_true == 1]
    negatives = scores[y_true == 0]
    if len(positives) == 0 or len(negatives) == 0:
        return 0.0

    wins = 0.0
    for positive_score in positives:
        wins += float((positive_score > negatives).sum())
        wins += 0.5 * float((positive_score == negatives).sum())
    return round(wins / (len(positives) * len(negatives)), 6)


def pr_auc(y_true: np.ndarray, scores: np.ndarray) -> float:
    order = np.argsort(-scores)
    sorted_true = y_true[order]
    positives = int((y_true == 1).sum())
    if positives == 0:
        return 0.0

    true_positive = 0
    false_positive = 0
    points: list[tuple[float, float]] = [(0.0, 1.0)]

    for label in sorted_true:
        if label == 1:
            true_positive += 1
        else:
            false_positive += 1
        recall = true_positive / positives
        precision = true_positive / (true_positive + false_positive)
        points.append((recall, precision))

    area = 0.0
    for index in range(1, len(points)):
        recall_delta = points[index][0] - points[index - 1][0]
        area += recall_delta * points[index][1]
    return round(area, 6)


def _safe_div(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return 0.0
    return round(numerator / denominator, 6)

