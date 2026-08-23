from copy import deepcopy
from pathlib import Path
from typing import Any

from src.common.config import get_project_paths
from src.common.io import read_json, write_json
from src.detect.score import score_feature_rows
from src.detect.train import load_model
from src.evaluate.metrics import metrics_for_rows
from src.features.build_features import build_feature_dataset
from src.generate.pipeline import generate_dataset
from src.knowledge.load_attack_catalog import load_attack_cards


def run_mutation_impact_experiment(
    candidate_iteration_id: str,
    source_iteration_id: str,
    mutation: dict[str, Any],
    seed: int = 314,
    benign_count: int = 200,
    per_attack_card: int = 4,
) -> dict[str, Any]:
    """Score matched baseline and mutated scenarios using one frozen detector.

    Both arms use the same seed, attack family, scenario count and benign volume.
    This is an experiment for defensive evaluation, not a live fraud simulation.
    """
    paths = get_project_paths()
    source_root = paths.outputs_dir / "iterations" / source_iteration_id
    model_path = source_root / "models" / "baseline_model.pkl"
    train_metrics_path = source_root / "metrics" / "train_metrics.json"
    if not model_path.exists() or not train_metrics_path.exists():
        raise FileNotFoundError("The source iteration does not contain a frozen detector artifact.")

    cards = {card.payload["attack_id"]: card.payload for card in load_attack_cards()}
    baseline_card = cards.get(str(mutation.get("source_attack_id", "")))
    if baseline_card is None:
        raise ValueError("The mutation's source attack card is unavailable.")
    mutated_card = deepcopy(baseline_card)
    mutated_card["attack_id"] = f"{baseline_card['attack_id']}__experiment_{mutation['mutation_id']}"
    mutated_card["variant_name"] = mutation.get("proposed_variant_name", baseline_card["variant_name"])
    mutated_card["generation_strategy"] = mutation.get("suggested_generation_strategy", baseline_card["generation_strategy"])
    mutated_card["notes"] = f"Controlled defensive experiment for {mutation['mutation_id']}"

    root = paths.outputs_dir / "experiments" / candidate_iteration_id / str(mutation["mutation_id"])
    threshold = float(load_model(model_path)["threshold"])
    baseline = _run_arm(root / "baseline", baseline_card, model_path, threshold, seed, benign_count, per_attack_card)
    mutated = _run_arm(root / "mutated", mutated_card, model_path, threshold, seed, benign_count, per_attack_card)
    result = {
        "experiment_id": f"{candidate_iteration_id}:{mutation['mutation_id']}",
        "candidate_iteration_id": candidate_iteration_id,
        "source_iteration_id": source_iteration_id,
        "mutation": {
            "mutation_id": mutation["mutation_id"],
            "subtype": mutation.get("subtype", ""),
            "proposed_variant_name": mutation.get("proposed_variant_name", ""),
            "parameter_deltas": mutation.get("parameter_deltas", []),
        },
        "design": {
            "seed": seed,
            "benign_count_per_arm": benign_count,
            "scenarios_per_arm": per_attack_card,
            "detector": f"frozen model from {source_iteration_id}",
            "llm_row_review": "disabled to isolate frozen-model comparison",
        },
        "baseline": baseline,
        "mutated": mutated,
        "metric_deltas": {key: round(mutated["metrics"].get(key, 0) - baseline["metrics"].get(key, 0), 6) for key in ("precision", "recall", "f1", "false_positive_rate")},
        "deterministic_explanation": _explanation(mutation, baseline, mutated),
        "disclosure": "Controlled matched synthetic experiment. Results measure the frozen source detector's performance on this baseline versus mutated scenario; they do not establish production performance.",
    }
    write_json(root / "experiment.json", result)
    return result


def load_mutation_impact_experiment(candidate_iteration_id: str, mutation_id: str) -> dict[str, Any]:
    path = get_project_paths().outputs_dir / "experiments" / candidate_iteration_id / mutation_id / "experiment.json"
    if not path.exists():
        raise FileNotFoundError("Run the controlled experiment before requesting an explanation.")
    return read_json(path)


def _run_arm(root: Path, card: dict[str, Any], model_path: Path, threshold: float, seed: int, benign_count: int, per_attack_card: int) -> dict[str, Any]:
    generated = root / "generated"; processed = root / "processed"; scores = root / "scores" / "scores.csv"
    generate_dataset(seed=seed, per_attack_card=per_attack_card, benign_count=benign_count, output_dir=generated, attack_cards=[card], realism_profile="overlap")
    build_feature_dataset(generated_dir=generated, output_path=processed / "features.csv")
    rows = score_feature_rows(features_path=processed / "features.csv", model_path=model_path, output_path=scores, enable_llm_review=False)
    metrics = metrics_for_rows(rows, threshold=threshold)
    fraud_rows = [row for row in rows if str(row.get("label")) == "1"]
    return {"record_count": len(rows), "fraud_record_count": len(fraud_rows), "metrics": metrics, "miss_count": sum(1 for row in fraud_rows if str(row.get("prediction")) != "1")}


def _explanation(mutation: dict[str, Any], baseline: dict[str, Any], mutated: dict[str, Any]) -> str:
    before, after = baseline["metrics"], mutated["metrics"]
    return (
        f"Using the same frozen detector and matched synthetic conditions, the {mutation.get('subtype', 'selected')} "
        f"variant changed recall from {before.get('recall', 0):.1%} to {after.get('recall', 0):.1%} and F1 from "
        f"{before.get('f1', 0):.1%} to {after.get('f1', 0):.1%}. The mutated arm produced "
        f"{mutated['miss_count']} missed fraud records versus {baseline['miss_count']} in the baseline arm."
    )
