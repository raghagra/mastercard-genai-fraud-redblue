from pathlib import Path
from typing import Any

from src.common.config import get_project_paths
from src.common.io import read_json, write_json


COMPARABLE_METRICS = [
    "precision",
    "recall",
    "f1",
    "accuracy",
    "false_positive_rate",
    "roc_auc",
    "pr_auc",
]


def list_iterations(iterations_dir: str | Path | None = None) -> list[dict[str, Any]]:
    root = Path(iterations_dir) if iterations_dir is not None else get_project_paths().outputs_dir / "iterations"
    if not root.exists():
        return []

    iterations: list[dict[str, Any]] = []
    for path in sorted(root.glob("iteration_*")):
        summary_path = path / "loop_summary.json"
        if summary_path.exists():
            summary = read_json(summary_path)
            iterations.append(
                {
                    "iteration_id": path.name,
                    "path": str(path),
                    "seed": summary.get("seed"),
                    "counts": summary.get("counts", {}),
                    "evaluation_overall": summary.get("evaluation_overall", {}),
                    "failure_summary": summary.get("failure_summary", {}),
                }
            )
    return iterations


def get_iteration_summary(iteration_id: str, iterations_dir: str | Path | None = None) -> dict[str, Any]:
    root = Path(iterations_dir) if iterations_dir is not None else get_project_paths().outputs_dir / "iterations"
    summary_path = root / iteration_id / "loop_summary.json"
    if not summary_path.exists():
        raise FileNotFoundError(f"Iteration summary not found: {summary_path}")
    return read_json(summary_path)


def compare_iterations(
    baseline_iteration_id: str,
    candidate_iteration_id: str,
    iterations_dir: str | Path | None = None,
    output_path: str | Path | None = None,
) -> dict[str, Any]:
    baseline = get_iteration_summary(baseline_iteration_id, iterations_dir)
    candidate = get_iteration_summary(candidate_iteration_id, iterations_dir)
    baseline_metrics = baseline.get("evaluation_overall", {})
    candidate_metrics = candidate.get("evaluation_overall", {})

    metric_deltas = {
        metric: round(
            _to_float(candidate_metrics.get(metric)) - _to_float(baseline_metrics.get(metric)),
            6,
        )
        for metric in COMPARABLE_METRICS
    }
    comparison = {
        "baseline_iteration_id": baseline_iteration_id,
        "candidate_iteration_id": candidate_iteration_id,
        "metric_deltas": metric_deltas,
        "baseline": {
            "counts": baseline.get("counts", {}),
            "evaluation_overall": baseline_metrics,
            "failure_summary": baseline.get("failure_summary", {}),
        },
        "candidate": {
            "counts": candidate.get("counts", {}),
            "evaluation_overall": candidate_metrics,
            "failure_summary": candidate.get("failure_summary", {}),
        },
    }

    if output_path is not None:
        write_json(output_path, comparison)
    return comparison


def _to_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0

