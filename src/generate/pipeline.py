from pathlib import Path

from src.common.config import get_project_paths
from src.common.io import write_json
from src.generate.records import (
    GeneratedDataset,
    generate_benign_records,
    generate_records_for_scenario,
    merge_datasets,
)
from src.generate.sampler import build_scenarios
from src.generate.validators import validate_generated_dataset
from src.knowledge.load_attack_catalog import load_attack_cards


def generate_dataset(
    seed: int = 42,
    per_attack_card: int = 1,
    benign_count: int = 500,
    output_dir: str | Path | None = None,
    attack_cards: list[dict[str, object]] | None = None,
    realism_profile: str = "overlap",
) -> GeneratedDataset:
    cards = attack_cards if attack_cards is not None else [card.payload for card in load_attack_cards()]
    if realism_profile not in {"baseline", "overlap"}:
        raise ValueError("realism_profile must be 'baseline' or 'overlap'")
    scenarios = build_scenarios(cards, seed=seed, per_card=per_attack_card, realism_profile=realism_profile)
    fraud_datasets = [generate_records_for_scenario(scenario) for scenario in scenarios]
    benign_dataset = generate_benign_records(
        seed=seed + 100_000, count=benign_count, realism_profile=realism_profile
    )
    dataset = merge_datasets([benign_dataset, *fraud_datasets])
    errors = validate_generated_dataset(dataset)
    if errors:
        raise ValueError(f"Generated dataset failed validation: {errors[0]}")

    target_dir = Path(output_dir) if output_dir is not None else get_project_paths().generated_data_dir
    write_dataset(dataset, target_dir)
    write_json(
        target_dir / "generation_summary.json",
        {
            "seed": seed,
            "per_attack_card": per_attack_card,
            "benign_count": benign_count,
            "realism_profile": realism_profile,
            "attack_card_count": len(cards),
            "transaction_count": len(dataset.transactions),
            "customer_count": len(dataset.customers),
            "merchant_count": len(dataset.merchants),
            "device_count": len(dataset.devices),
            "attack_instance_count": len(dataset.attack_instances),
        },
    )
    return dataset


def write_dataset(dataset: GeneratedDataset, output_dir: str | Path) -> None:
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)
    _write_csv(target / "transactions.csv", dataset.transactions)
    _write_csv(target / "customers.csv", dataset.customers)
    _write_csv(target / "merchants.csv", dataset.merchants)
    _write_csv(target / "devices.csv", dataset.devices)
    _write_csv(target / "attack_instances.csv", dataset.attack_instances)


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    import csv

    if not rows:
        path.write_text("", encoding="utf-8")
        return

    fieldnames = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
