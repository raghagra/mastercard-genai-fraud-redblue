import csv
import pickle
from pathlib import Path
from typing import Any

import numpy as np

from src.common.config import get_project_paths
from src.common.io import write_json
from src.detect.metrics import classification_metrics
from src.detect.thresholds import select_threshold
from src.features.build_features import feature_columns


def train_baseline_detector(
    features_path: str | Path | None = None,
    model_path: str | Path | None = None,
    metrics_path: str | Path | None = None,
    seed: int = 42,
) -> dict[str, Any]:
    paths = get_project_paths()
    source_path = Path(features_path) if features_path is not None else paths.processed_data_dir / "features.csv"
    target_model_path = Path(model_path) if model_path is not None else paths.outputs_dir / "models" / "baseline_model.pkl"
    target_metrics_path = (
        Path(metrics_path) if metrics_path is not None else paths.outputs_dir / "metrics" / "train_metrics.json"
    )

    rows = _read_csv(source_path)
    if not rows:
        raise ValueError(f"No feature rows found: {source_path}")

    columns = feature_columns(rows)
    x = np.array([[_to_float(row[column]) for column in columns] for row in rows], dtype=float)
    y = np.array([_to_int(row["label"]) for row in rows], dtype=int)
    train_idx, test_idx, holdout_attack_ids = _attack_holdout_split(rows, y, seed=seed)

    x_train_raw = x[train_idx]
    x_test_raw = x[test_idx]
    y_train = y[train_idx]
    y_test = y[test_idx]
    mean = x_train_raw.mean(axis=0)
    std = x_train_raw.std(axis=0)
    std[std == 0] = 1.0
    x_train = (x_train_raw - mean) / std
    x_test = (x_test_raw - mean) / std

    weights, bias = _fit_logistic_regression(x_train, y_train, seed=seed)
    train_scores = _predict_scores(x_train, weights, bias)
    test_scores = _predict_scores(x_test, weights, bias)
    threshold = select_threshold(y_train, train_scores)

    model = {
        "model_type": "numpy_logistic_regression",
        "feature_columns": columns,
        "mean": mean.tolist(),
        "std": std.tolist(),
        "weights": weights.tolist(),
        "bias": float(bias),
        "threshold": threshold,
        "seed": seed,
        "evaluation_strategy": "attack_card_holdout",
        "holdout_transaction_ids": [rows[int(index)]["transaction_id"] for index in test_idx],
    }
    _write_pickle(target_model_path, model)

    metrics = {
        "model_type": model["model_type"],
        "feature_count": len(columns),
        "row_count": len(rows),
        "train_count": int(len(train_idx)),
        "test_count": int(len(test_idx)),
        "positive_count": int(y.sum()),
        "threshold": threshold,
        "evaluation_strategy": "attack_card_holdout",
        "holdout": {
            "attack_ids": holdout_attack_ids,
            "attack_card_count": len(holdout_attack_ids),
            "transaction_ids": [rows[int(index)]["transaction_id"] for index in test_idx],
            "positive_count": int(y_test.sum()),
            "benign_count": int((y_test == 0).sum()),
        },
        "train": classification_metrics(y_train, train_scores, threshold),
        "test": classification_metrics(y_test, test_scores, threshold),
        "heldout_attack_test": classification_metrics(y_test, test_scores, threshold),
    }
    write_json(target_metrics_path, metrics)
    return metrics


def load_model(path: str | Path | None = None) -> dict[str, Any]:
    model_path = Path(path) if path is not None else get_project_paths().outputs_dir / "models" / "baseline_model.pkl"
    with model_path.open("rb") as file:
        return pickle.load(file)


def model_scores(rows: list[dict[str, str]], model: dict[str, Any]) -> np.ndarray:
    columns = model["feature_columns"]
    x = np.array([[_to_float(row[column]) for column in columns] for row in rows], dtype=float)
    mean = np.array(model["mean"], dtype=float)
    std = np.array(model["std"], dtype=float)
    weights = np.array(model["weights"], dtype=float)
    bias = float(model["bias"])
    return _predict_scores((x - mean) / std, weights, bias)


def _fit_logistic_regression(
    x: np.ndarray,
    y: np.ndarray,
    seed: int,
    learning_rate: float = 0.01,
    epochs: int = 2500,
    l2: float = 0.001,
) -> tuple[np.ndarray, float]:
    rng = np.random.default_rng(seed)
    weights = rng.normal(0, 0.01, size=x.shape[1])
    bias = 0.0
    positive_weight = len(y) / max(1, 2 * int(y.sum()))
    negative_weight = len(y) / max(1, 2 * int((y == 0).sum()))

    for _ in range(epochs):
        with np.errstate(over="ignore", divide="ignore", invalid="ignore"):
            logits = x @ weights + bias
        logits = np.nan_to_num(logits, nan=0.0, posinf=500.0, neginf=-500.0)
        predictions = _sigmoid(logits)
        sample_weights = np.where(y == 1, positive_weight, negative_weight)
        error = (predictions - y) * sample_weights
        with np.errstate(over="ignore", divide="ignore", invalid="ignore"):
            grad_w = (x.T @ error) / len(y) + l2 * weights
        grad_w = np.nan_to_num(grad_w, nan=0.0, posinf=10.0, neginf=-10.0)
        grad_b = float(error.mean())
        grad_norm = float(np.linalg.norm(grad_w))
        if grad_norm > 10:
            grad_w = grad_w * (10 / grad_norm)
        weights -= learning_rate * grad_w
        bias -= learning_rate * grad_b
        weights = np.clip(weights, -25, 25)
        bias = float(np.clip(bias, -25, 25))

    return weights, bias


def _predict_scores(x: np.ndarray, weights: np.ndarray, bias: float) -> np.ndarray:
    with np.errstate(over="ignore", divide="ignore", invalid="ignore"):
        logits = x @ weights + bias
    logits = np.nan_to_num(logits, nan=0.0, posinf=500.0, neginf=-500.0)
    return _sigmoid(logits)


def _sigmoid(values: np.ndarray) -> np.ndarray:
    clipped = np.clip(values, -500, 500)
    return 1 / (1 + np.exp(-clipped))


def _stratified_split(y: np.ndarray, seed: int, test_fraction: float = 0.25) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    train_parts = []
    test_parts = []

    for label in [0, 1]:
        indices = np.where(y == label)[0]
        rng.shuffle(indices)
        test_size = max(1, int(round(len(indices) * test_fraction)))
        test_parts.append(indices[:test_size])
        train_parts.append(indices[test_size:])

    train_idx = np.concatenate(train_parts)
    test_idx = np.concatenate(test_parts)
    rng.shuffle(train_idx)
    rng.shuffle(test_idx)
    return train_idx, test_idx


def _attack_holdout_split(
    rows: list[dict[str, str]],
    y: np.ndarray,
    seed: int,
    test_fraction: float = 0.25,
) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """Keep complete fraud attack cards out of training.

    A row-level split can put near-duplicate events from one campaign in both
    partitions.  This split measures transfer to entirely unseen attack cards,
    with an independently sampled benign holdout for false-positive measurement.
    """
    attack_ids = sorted({row.get("attack_id", "") for row, label in zip(rows, y) if label == 1 and row.get("attack_id")})
    if len(attack_ids) < 2:
        train_idx, test_idx = _stratified_split(y, seed=seed, test_fraction=test_fraction)
        return train_idx, test_idx, []

    rng = np.random.default_rng(seed)
    shuffled_attack_ids = np.array(attack_ids, dtype=object)
    rng.shuffle(shuffled_attack_ids)
    holdout_count = max(1, int(round(len(shuffled_attack_ids) * test_fraction)))
    held_out = {str(item) for item in shuffled_attack_ids[:holdout_count]}

    benign_indices = np.where(y == 0)[0]
    rng.shuffle(benign_indices)
    benign_test_size = min(
        max(1, int(round(len(benign_indices) * test_fraction))),
        max(0, len(benign_indices) - 1),
    )
    benign_test = set(int(index) for index in benign_indices[:benign_test_size])

    test_indices: list[int] = []
    train_indices: list[int] = []
    for index, row in enumerate(rows):
        is_heldout_fraud = y[index] == 1 and row.get("attack_id", "") in held_out
        if is_heldout_fraud or index in benign_test:
            test_indices.append(index)
        else:
            train_indices.append(index)

    return np.array(train_indices, dtype=int), np.array(test_indices, dtype=int), sorted(held_out)


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def _write_pickle(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as file:
        pickle.dump(payload, file)


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
