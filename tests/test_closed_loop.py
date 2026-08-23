from pathlib import Path

from src.common.io import write_json
from src.loop.compare_iterations import compare_iterations, list_iterations
from src.loop.run_iteration import run_closed_loop_iteration
from src.mutate.apply_mutations import apply_mutations_to_attack_cards
from src.mutate.mutate_attack_card import propose_mutations
from src.mutate.review import accepted_mutations, review_all_mutations


def test_closed_loop_iteration_creates_expected_artifacts(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("src.loop.run_iteration.get_project_paths", lambda: _paths(tmp_path))

    summary = run_closed_loop_iteration(
        iteration_id="iteration_test",
        seed=13,
        benign_count=25,
    )

    root = tmp_path / "outputs" / "iterations" / "iteration_test"
    assert summary["iteration_id"] == "iteration_test"
    assert summary["counts"]["mutation_candidates"] > 0
    assert (root / "generated" / "transactions.csv").exists()
    assert (root / "processed" / "features.csv").exists()
    assert (root / "models" / "baseline_model.pkl").exists()
    assert (root / "reports" / "failure_analysis.json").exists()
    assert (root / "mutation_candidates.json").exists()
    assert (root / "mutation_usage.json").exists()


def test_failure_analysis_and_mutations_use_low_confidence_groups() -> None:
    analysis = {
        "weak_groups": [
            {
                "group_key": "card_not_present",
                "bucket": "credential_based_fraud",
                "subtype": "card_not_present",
                "fraud_count": 1,
                "miss_count": 0,
                "recall": 1.0,
                "avg_fraud_score": 0.61,
                "reason": "lowest_confidence_fraud_group",
            }
        ]
    }

    mutations = propose_mutations(analysis)

    assert mutations
    assert mutations[0]["source_attack_id"] == "cred_cnp_001"
    assert mutations[0]["human_review_required"] is True
    assert mutations[0]["review_evidence"]["selection_reason"] == "lowest_confidence_fraud_group"


def test_local_rule_mutations_are_specific_to_the_attack_family() -> None:
    analysis = {
        "weak_groups": [
            {"subtype": "credential_stuffing", "bucket": "credential_based_fraud"},
            {"subtype": "return_policy_abuse", "bucket": "post_transaction_abuse"},
        ]
    }

    candidates = propose_mutations(analysis, limit=2)

    assert len(candidates) == 2
    assert candidates[0]["rationale"] != candidates[1]["rationale"]
    assert candidates[0]["mutation_strategy"] != candidates[1]["mutation_strategy"]
    assert candidates[0]["parameter_deltas"]
    assert candidates[0]["suggested_generation_strategy"]["volume_range"] != candidates[1]["suggested_generation_strategy"]["volume_range"]


def test_iteration_comparison_reports_metric_deltas(tmp_path: Path) -> None:
    iterations_dir = tmp_path / "iterations"
    first = iterations_dir / "iteration_001"
    second = iterations_dir / "iteration_002"
    first.mkdir(parents=True)
    second.mkdir(parents=True)
    write_json(
        first / "loop_summary.json",
        {
            "seed": 1,
            "counts": {"mutation_candidates": 2},
            "evaluation_overall": {"f1": 0.7, "recall": 0.6, "precision": 0.8},
            "failure_summary": {"false_negatives": 4},
        },
    )
    write_json(
        second / "loop_summary.json",
        {
            "seed": 2,
            "counts": {"mutation_candidates": 3},
            "evaluation_overall": {"f1": 0.9, "recall": 0.75, "precision": 0.92},
            "failure_summary": {"false_negatives": 2},
        },
    )

    listed = list_iterations(iterations_dir)
    comparison = compare_iterations("iteration_001", "iteration_002", iterations_dir)

    assert [item["iteration_id"] for item in listed] == ["iteration_001", "iteration_002"]
    assert comparison["metric_deltas"]["f1"] == 0.2
    assert comparison["metric_deltas"]["recall"] == 0.15


def test_reviewed_mutations_are_consumed_by_next_iteration(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("src.loop.run_iteration.get_project_paths", lambda: _paths(tmp_path))
    monkeypatch.setattr("src.mutate.review.get_project_paths", lambda: _paths(tmp_path))

    run_closed_loop_iteration(
        iteration_id="iteration_source",
        seed=31,
        benign_count=20,
    )
    reviews = review_all_mutations(
        "iteration_source",
        decision="accepted",
        reviewer="pytest",
        notes="accept all for test",
    )
    accepted = accepted_mutations("iteration_source")
    summary = run_closed_loop_iteration(
        iteration_id="iteration_candidate",
        seed=32,
        benign_count=20,
        review_source_iteration_id="iteration_source",
    )

    assert len(reviews) == 5
    assert len(accepted) == 5
    assert summary["counts"]["accepted_mutations_consumed"] == 5
    assert summary["counts"]["mutation_overlays_applied"] == 5


def test_apply_mutations_creates_runtime_attack_card_overlay() -> None:
    cards = [
        {
            "attack_id": "base_001",
            "variant_name": "Base variant",
            "generation_strategy": {
                "mode": "template_plus_sampling",
                "stealth_level_range": [0.3, 0.7],
                "volume_range": [2, 4],
                "noise_level": "medium",
            },
            "evaluation_tags": ["base"],
        }
    ]
    mutations = [
        {
            "mutation_id": "mut_001",
            "source_attack_id": "base_001",
            "proposed_variant_name": "Base variant - stealth hardened",
            "suggested_generation_strategy": {
                "mode": "template_plus_sampling",
                "stealth_level_range": [0.5, 0.9],
                "volume_range": [2, 4],
                "noise_level": "high",
            },
            "review": {"decision": "accepted"},
        }
    ]

    mutated_cards, usage = apply_mutations_to_attack_cards(cards, mutations)

    assert len(mutated_cards) == 2
    assert mutated_cards[1]["attack_id"] == "base_001__mut_001"
    assert mutated_cards[1]["generation_strategy"]["noise_level"] == "high"
    assert usage[0]["status"] == "applied"


def _paths(tmp_path: Path):
    from src.common.config import ProjectPaths, get_project_paths

    real_paths = get_project_paths()
    return ProjectPaths(
        root=real_paths.root,
        schemas_dir=real_paths.schemas_dir,
        attack_cards_dir=real_paths.attack_cards_dir,
        generated_data_dir=tmp_path / "data" / "generated",
        processed_data_dir=tmp_path / "data" / "processed",
        outputs_dir=tmp_path / "outputs",
    )
