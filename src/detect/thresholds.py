import numpy as np

from src.detect.metrics import classification_metrics


def select_threshold(y_true: np.ndarray, scores: np.ndarray) -> float:
    candidates = np.linspace(0.05, 0.95, 91)
    best_threshold = 0.5
    best_f1 = -1.0

    for threshold in candidates:
        metrics = classification_metrics(y_true, scores, float(threshold))
        if metrics["f1"] > best_f1:
            best_f1 = metrics["f1"]
            best_threshold = float(threshold)

    return round(best_threshold, 4)

