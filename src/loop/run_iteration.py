from pathlib import Path
from typing import Any, Callable

from src.common.config import get_project_paths
from src.common.io import write_json
from src.detect.score import score_feature_rows
from src.detect.train import train_baseline_detector
from src.evaluate.failure_analysis import analyze_detector_failures
from src.evaluate.reports import build_evaluation_report
from src.features.build_features import build_feature_dataset, feature_columns
from src.generate.pipeline import generate_dataset
from src.knowledge.load_attack_catalog import load_attack_cards
from src.mutate.apply_mutations import apply_mutations_to_attack_cards
from src.mutate.mutate_attack_card import propose_mutations
from src.mutate.review import accepted_mutations


def run_closed_loop_iteration(
    iteration_id: str | None = None,
    seed: int = 42,
    per_attack_card: int = 1,
    benign_count: int = 500,
    realism_profile: str = "overlap",
    review_source_iteration_id: str | None = None,
    mutation_candidate_limit: int = 5,
    progress_callback: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    def progress(stage: str) -> None:
        if progress_callback is not None:
            progress_callback(stage)

    progress("preparing")
    iteration_root = _iteration_root(iteration_id)
    generated_dir = iteration_root / "generated"
    processed_dir = iteration_root / "processed"
    models_dir = iteration_root / "models"
    metrics_dir = iteration_root / "metrics"
    scores_dir = iteration_root / "scores"
    reports_dir = iteration_root / "reports"
    cards = [card.payload for card in load_attack_cards()]
    mutation_usage: list[dict[str, Any]] = []
    accepted = []
    if review_source_iteration_id:
        accepted = accepted_mutations(review_source_iteration_id)
        cards, mutation_usage = apply_mutations_to_attack_cards(cards, accepted)
    write_json(iteration_root / "mutation_usage.json", mutation_usage)

    progress("generating")
    dataset = generate_dataset(
        seed=seed,
        per_attack_card=per_attack_card,
        benign_count=benign_count,
        realism_profile=realism_profile,
        output_dir=generated_dir,
        attack_cards=cards,
    )
    progress("building_features")
    feature_rows = build_feature_dataset(
        generated_dir=generated_dir,
        output_path=processed_dir / "features.csv",
    )
    progress("training")
    train_metrics = train_baseline_detector(
        features_path=processed_dir / "features.csv",
        model_path=models_dir / "baseline_model.pkl",
        metrics_path=metrics_dir / "train_metrics.json",
        seed=seed,
    )
    progress("scoring")
    scored_rows = score_feature_rows(
        features_path=processed_dir / "features.csv",
        model_path=models_dir / "baseline_model.pkl",
        output_path=scores_dir / "scores.csv",
        iteration_id=iteration_root.name,
    )
    progress("evaluating")
    evaluation_report = build_evaluation_report(
        scores_path=scores_dir / "scores.csv",
        train_metrics_path=metrics_dir / "train_metrics.json",
        output_dir=reports_dir,
    )
    progress("analyzing_failures")
    failure_analysis = analyze_detector_failures(
        scores_path=scores_dir / "scores.csv",
        train_metrics_path=metrics_dir / "train_metrics.json",
        output_path=reports_dir / "failure_analysis.json",
        transaction_ids=set(train_metrics.get("holdout", {}).get("transaction_ids", [])),
    )
    progress("proposing_mutations")
    mutation_candidates = propose_mutations(failure_analysis, iteration_id=iteration_root.name, limit=mutation_candidate_limit)
    write_json(iteration_root / "mutation_candidates.json", mutation_candidates)

    summary = {
        "iteration_id": iteration_root.name,
        "seed": seed,
        "per_attack_card": per_attack_card,
        "benign_count": benign_count,
        "realism_profile": realism_profile,
        "review_source_iteration_id": review_source_iteration_id,
        "mutation_candidate_limit": mutation_candidate_limit,
        "paths": {
            "root": str(iteration_root),
            "generated": str(generated_dir),
            "processed": str(processed_dir),
            "models": str(models_dir),
            "metrics": str(metrics_dir),
            "scores": str(scores_dir),
            "reports": str(reports_dir),
        },
        "counts": {
            "transactions": len(dataset.transactions),
            "features": len(feature_rows),
            "feature_columns": len(feature_columns(feature_rows)),
            "scored_rows": len(scored_rows),
            "mutation_candidates": len(mutation_candidates),
            "accepted_mutations_consumed": len(accepted),
            "mutation_overlays_applied": sum(1 for item in mutation_usage if item["status"] == "applied"),
        },
        "train_metrics": train_metrics,
        "evaluation_overall": evaluation_report["overall"],
        "heldout_attack_benchmark": evaluation_report["heldout_attack_benchmark"],
        "failure_summary": {
            "false_positives": len(failure_analysis["false_positives"]),
            "false_negatives": len(failure_analysis["false_negatives"]),
            "weak_groups": failure_analysis["weak_groups"],
        },
    }
    write_json(iteration_root / "loop_summary.json", summary)
    progress("completed")
    return summary


def _iteration_root(iteration_id: str | None) -> Path:
    root = get_project_paths().outputs_dir / "iterations"
    root.mkdir(parents=True, exist_ok=True)
    name = iteration_id or _next_iteration_id(root)
    return root / name


def _next_iteration_id(root: Path) -> str:
    existing = sorted(path.name for path in root.glob("iteration_*") if path.is_dir())
    if not existing:
        return "iteration_001"
    last = existing[-1].split("_")[-1]
    try:
        next_number = int(last) + 1
    except ValueError:
        next_number = len(existing) + 1
    return f"iteration_{next_number:03d}"
