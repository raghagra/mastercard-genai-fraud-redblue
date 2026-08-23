from pathlib import Path

from src.generate.pipeline import generate_dataset
from src.generate.sampler import build_scenarios
from src.generate.validators import validate_generated_dataset
from src.knowledge.load_attack_catalog import load_attack_cards


def test_scenario_generation_is_reproducible() -> None:
    card = load_attack_cards()[0].payload

    first = build_scenarios([card], seed=123, per_card=1)[0]
    second = build_scenarios([card], seed=123, per_card=1)[0]

    assert first.scenario_id == second.scenario_id
    assert first.event_count == second.event_count
    assert first.target_customer_id == second.target_customer_id


def test_generate_dataset_writes_expected_files(tmp_path: Path) -> None:
    dataset = generate_dataset(seed=7, benign_count=20, output_dir=tmp_path)

    assert len(dataset.attack_instances) == 25
    assert len(dataset.transactions) > 20
    assert validate_generated_dataset(dataset) == []
    assert (tmp_path / "transactions.csv").exists()
    assert (tmp_path / "customers.csv").exists()
    assert (tmp_path / "merchants.csv").exists()
    assert (tmp_path / "devices.csv").exists()
    assert (tmp_path / "attack_instances.csv").exists()
    assert (tmp_path / "generation_summary.json").exists()


def test_campaign_events_have_non_uniform_ordered_timing(tmp_path: Path) -> None:
    card = load_attack_cards()[0].payload
    scenario = build_scenarios([card], seed=9, per_card=1)[0]
    dataset = generate_dataset(
        seed=9, per_attack_card=1, benign_count=0, attack_cards=[card], output_dir=tmp_path
    )
    events = sorted(
        (row["event_time"] for row in dataset.transactions if row["scenario_id"] == scenario.scenario_id)
    )

    assert events == [row["event_time"] for row in dataset.transactions if row["scenario_id"] == scenario.scenario_id]
    assert len(events) == scenario.event_count
