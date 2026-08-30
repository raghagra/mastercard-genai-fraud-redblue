from pathlib import Path

from src.common.config import ProjectPaths, get_project_paths
from src.experiments.adversarial_evaluation import (
    evaluation_lab_options,
    list_adversarial_evaluation_campaigns,
    load_adversarial_evaluation_campaign,
    run_adversarial_evaluation_campaign,
)
from src.loop.run_iteration import run_closed_loop_iteration


def test_adversarial_evaluation_campaign_runs_and_persists(tmp_path: Path, monkeypatch) -> None:
    paths = _paths(tmp_path)
    monkeypatch.setattr("src.loop.run_iteration.get_project_paths", lambda: paths)
    monkeypatch.setattr("src.experiments.adversarial_evaluation.get_project_paths", lambda: paths)

    source = run_closed_loop_iteration(
        iteration_id="iteration_campaign_source",
        seed=71,
        benign_count=20,
        per_attack_card=1,
    )
    campaign = run_adversarial_evaluation_campaign(
        source_iteration_id=source["iteration_id"],
        campaign_id="campaign_test",
        buckets=["credential_based_fraud", "social_engineering_payment_fraud"],
        difficulty_profiles=["baseline", "stealth_stress"],
        seeds=[101],
        scenarios_per_card=1,
        benign_count=20,
    )

    assert campaign["campaign_id"] == "campaign_test"
    assert campaign["configuration"]["arm_count"] == 2
    assert campaign["detector"]["row_level_llm_review"] == "disabled to isolate frozen-detector coverage"
    assert len(campaign["coverage_matrix"]) == 4
    assert {cell["status"] for cell in campaign["coverage_matrix"]} <= {"strong", "monitor", "weak"}
    assert (paths.outputs_dir / "evaluation_campaigns" / "campaign_test" / "campaign.json").exists()
    assert load_adversarial_evaluation_campaign("campaign_test")["source_iteration_id"] == source["iteration_id"]
    assert list_adversarial_evaluation_campaigns()[0]["campaign_id"] == "campaign_test"


def test_adversarial_evaluation_options_are_catalog_backed() -> None:
    options = evaluation_lab_options()

    assert sum(item["attack_card_count"] for item in options["buckets"]) == 25
    assert {item["name"] for item in options["difficulty_profiles"]} == {"baseline", "elevated", "stealth_stress"}


def _paths(tmp_path: Path) -> ProjectPaths:
    real_paths = get_project_paths()
    return ProjectPaths(
        root=real_paths.root,
        schemas_dir=real_paths.schemas_dir,
        attack_cards_dir=real_paths.attack_cards_dir,
        generated_data_dir=tmp_path / "data" / "generated",
        processed_data_dir=tmp_path / "data" / "processed",
        outputs_dir=tmp_path / "outputs",
    )
