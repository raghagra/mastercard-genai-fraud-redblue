"""Deterministic attack-sweep campaigns for defensive evaluation.

An evaluation campaign reuses a frozen detector from a completed loop
iteration and systematically varies attack difficulty across selected payment
fraud families. It is a synthetic, local evaluation tool—not a payment-time
decision service and not evidence of production performance.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from src.common.config import get_project_paths
from src.common.io import read_json, write_json
from src.detect.score import score_feature_rows
from src.detect.train import load_model
from src.evaluate.metrics import metrics_for_rows
from src.features.build_features import build_feature_dataset
from src.generate.pipeline import generate_dataset
from src.knowledge.load_attack_catalog import load_attack_cards


DIFFICULTY_PROFILES: dict[str, dict[str, Any]] = {
    "baseline": {
        "label": "Baseline",
        "description": "Uses the original attack-card generator settings.",
        "stealth_increment": 0.0,
        "volume_multiplier": 1.0,
        "noise_level": None,
        "time_window_multiplier": 1.0,
    },
    "elevated": {
        "label": "Elevated",
        "description": "Moves the campaign closer to benign context while reducing obvious velocity.",
        "stealth_increment": 0.08,
        "volume_multiplier": 0.75,
        "noise_level": "high",
        "time_window_multiplier": 1.4,
    },
    "stealth_stress": {
        "label": "Stealth stress",
        "description": "Applies the strongest bounded overlap, pacing, noise, and campaign-window stress settings.",
        "stealth_increment": 0.15,
        "volume_multiplier": 0.55,
        "noise_level": "high",
        "time_window_multiplier": 2.0,
    },
}


def run_adversarial_evaluation_campaign(
    source_iteration_id: str,
    campaign_id: str | None = None,
    buckets: list[str] | None = None,
    difficulty_profiles: list[str] | None = None,
    seeds: list[int] | None = None,
    scenarios_per_card: int = 1,
    benign_count: int = 100,
    realism_profile: str = "overlap",
) -> dict[str, Any]:
    """Run a reproducible attack-coverage sweep using one frozen detector."""
    if scenarios_per_card < 1:
        raise ValueError("scenarios_per_card must be at least 1")
    if benign_count < 20:
        raise ValueError("benign_count must be at least 20")
    if realism_profile not in {"baseline", "overlap"}:
        raise ValueError("realism_profile must be 'baseline' or 'overlap'")

    selected_profiles = difficulty_profiles or list(DIFFICULTY_PROFILES)
    invalid_profiles = sorted(set(selected_profiles) - set(DIFFICULTY_PROFILES))
    if invalid_profiles:
        raise ValueError(f"Unknown difficulty profile(s): {', '.join(invalid_profiles)}")
    selected_seeds = seeds or [101, 202]
    if not selected_seeds or any(seed < 1 for seed in selected_seeds):
        raise ValueError("seeds must contain positive integers")
    if len(selected_profiles) * len(selected_seeds) > 12:
        raise ValueError("Campaigns may contain at most 12 seed/profile arms.")

    paths = get_project_paths()
    source_root = paths.outputs_dir / "iterations" / source_iteration_id
    model_path = source_root / "models" / "baseline_model.pkl"
    if not model_path.exists():
        raise FileNotFoundError("The selected source iteration does not contain a frozen detector artifact.")
    threshold = float(load_model(model_path)["threshold"])

    all_cards = [deepcopy(card.payload) for card in load_attack_cards()]
    known_buckets = sorted({str(card["bucket"]) for card in all_cards})
    selected_buckets = buckets or known_buckets
    invalid_buckets = sorted(set(selected_buckets) - set(known_buckets))
    if invalid_buckets:
        raise ValueError(f"Unknown attack bucket(s): {', '.join(invalid_buckets)}")
    cards = [card for card in all_cards if card["bucket"] in selected_buckets]
    if not cards:
        raise ValueError("No attack cards match the selected buckets.")

    run_id = campaign_id or _new_campaign_id()
    root = paths.outputs_dir / "evaluation_campaigns" / run_id
    if root.exists():
        raise ValueError(f"Campaign already exists: {run_id}")

    grouped_rows: dict[tuple[str, str], list[dict[str, str]]] = {}
    arms: list[dict[str, Any]] = []
    for profile_name in selected_profiles:
        profile = DIFFICULTY_PROFILES[profile_name]
        profile_cards = [_apply_difficulty(card, profile_name) for card in cards]
        for seed in selected_seeds:
            arm_id = f"{profile_name}_seed_{seed}"
            arm_root = root / "arms" / arm_id
            generated_dir = arm_root / "generated"
            features_path = arm_root / "processed" / "features.csv"
            scores_path = arm_root / "scores" / "scores.csv"
            dataset = generate_dataset(
                seed=seed,
                per_attack_card=scenarios_per_card,
                benign_count=benign_count,
                output_dir=generated_dir,
                attack_cards=profile_cards,
                realism_profile=realism_profile,
            )
            build_feature_dataset(generated_dir=generated_dir, output_path=features_path)
            rows = score_feature_rows(
                features_path=features_path,
                model_path=model_path,
                output_path=scores_path,
                enable_llm_review=False,
            )
            arm_summary = {
                "arm_id": arm_id,
                "difficulty_profile": profile_name,
                "seed": seed,
                "record_count": len(rows),
                "fraud_record_count": sum(1 for row in rows if _as_int(row.get("label")) == 1),
                "metrics": metrics_for_rows(rows, threshold=threshold),
            }
            arms.append(arm_summary)
            write_json(arm_root / "summary.json", arm_summary)

            benign_rows = [row for row in rows if _as_int(row.get("label")) == 0]
            for bucket in selected_buckets:
                fraud_rows = [
                    row for row in rows
                    if _as_int(row.get("label")) == 1 and row.get("attack_bucket") == bucket
                ]
                grouped_rows.setdefault((profile_name, bucket), []).extend([*benign_rows, *fraud_rows])

    cells = [
        _coverage_cell(profile_name, bucket, grouped_rows[(profile_name, bucket)], threshold)
        for profile_name in selected_profiles
        for bucket in selected_buckets
    ]
    weak_cells = [cell for cell in cells if cell["status"] != "strong"]
    campaign = {
        "campaign_id": run_id,
        "created_at": _timestamp(),
        "source_iteration_id": source_iteration_id,
        "detector": {
            "model_path": str(model_path),
            "threshold": threshold,
            "row_level_llm_review": "disabled to isolate frozen-detector coverage",
        },
        "configuration": {
            "buckets": selected_buckets,
            "attack_card_count": len(cards),
            "difficulty_profiles": [
                {"name": name, "label": DIFFICULTY_PROFILES[name]["label"], "description": DIFFICULTY_PROFILES[name]["description"]}
                for name in selected_profiles
            ],
            "seeds": selected_seeds,
            "scenarios_per_card": scenarios_per_card,
            "benign_count_per_arm": benign_count,
            "realism_profile": realism_profile,
            "arm_count": len(arms),
        },
        "arms": arms,
        "coverage_matrix": cells,
        "summary": {
            "cell_count": len(cells),
            "strong_cells": sum(1 for cell in cells if cell["status"] == "strong"),
            "monitor_cells": sum(1 for cell in cells if cell["status"] == "monitor"),
            "weak_cells": sum(1 for cell in cells if cell["status"] == "weak"),
            "lowest_recall_cell": min(cells, key=lambda cell: float(cell["metrics"].get("recall", 0))) if cells else None,
            "follow_up_candidates": weak_cells[:8],
        },
        "disclosure": (
            "Synthetic adversarial evaluation using a frozen detector from the selected source iteration. "
            "LLM row review is disabled for comparability. Results indicate where to inspect or create governed "
            "red-team mutations; they do not establish production fraud-detection performance."
        ),
    }
    write_json(root / "campaign.json", campaign)
    return campaign


def list_adversarial_evaluation_campaigns() -> list[dict[str, Any]]:
    root = get_project_paths().outputs_dir / "evaluation_campaigns"
    if not root.exists():
        return []
    campaigns = []
    for path in root.glob("*/campaign.json"):
        payload = read_json(path)
        if isinstance(payload, dict):
            campaigns.append(
                {
                    "campaign_id": payload.get("campaign_id", path.parent.name),
                    "created_at": payload.get("created_at"),
                    "source_iteration_id": payload.get("source_iteration_id"),
                    "summary": payload.get("summary", {}),
                    "configuration": payload.get("configuration", {}),
                }
            )
    return sorted(campaigns, key=lambda item: str(item.get("created_at", "")), reverse=True)


def load_adversarial_evaluation_campaign(campaign_id: str) -> dict[str, Any]:
    path = get_project_paths().outputs_dir / "evaluation_campaigns" / campaign_id / "campaign.json"
    if not path.exists():
        raise FileNotFoundError(f"Evaluation campaign not found: {campaign_id}")
    payload = read_json(path)
    if not isinstance(payload, dict):
        raise ValueError(f"Evaluation campaign is invalid: {campaign_id}")
    return payload


def evaluation_lab_options() -> dict[str, Any]:
    cards = [card.payload for card in load_attack_cards()]
    buckets: dict[str, int] = {}
    for card in cards:
        bucket = str(card["bucket"])
        buckets[bucket] = buckets.get(bucket, 0) + 1
    return {
        "buckets": [{"name": bucket, "attack_card_count": count} for bucket, count in sorted(buckets.items())],
        "difficulty_profiles": [
            {"name": name, "label": profile["label"], "description": profile["description"]}
            for name, profile in DIFFICULTY_PROFILES.items()
        ],
        "defaults": {"seeds": [101, 202], "scenarios_per_card": 1, "benign_count": 100, "realism_profile": "overlap"},
    }


def _apply_difficulty(card: dict[str, Any], profile_name: str) -> dict[str, Any]:
    profile = DIFFICULTY_PROFILES[profile_name]
    variant = deepcopy(card)
    strategy = dict(variant["generation_strategy"])
    low, high = [float(value) for value in strategy["stealth_level_range"]]
    increase = float(profile["stealth_increment"])
    strategy["stealth_level_range"] = [round(min(0.98, low + increase), 2), round(min(0.99, high + increase), 2)]
    volume_low, volume_high = [int(value) for value in strategy["volume_range"]]
    multiplier = float(profile["volume_multiplier"])
    strategy["volume_range"] = [max(1, round(volume_low * multiplier)), max(1, round(volume_high * multiplier))]
    strategy["time_window_multiplier"] = round(float(strategy.get("time_window_multiplier", 1.0)) * float(profile["time_window_multiplier"]), 2)
    if profile["noise_level"]:
        strategy["noise_level"] = profile["noise_level"]
    variant["generation_strategy"] = strategy
    variant["attack_id"] = f"{card['attack_id']}__evaluation_{profile_name}"
    variant["notes"] = f"Adversarial evaluation profile={profile_name}; source_attack_id={card['attack_id']}"
    variant["evaluation_tags"] = sorted(set(variant.get("evaluation_tags", [])) | {"adversarial_evaluation", profile_name})
    return variant


def _coverage_cell(profile_name: str, bucket: str, rows: list[dict[str, str]], threshold: float) -> dict[str, Any]:
    metrics = metrics_for_rows(rows, threshold=threshold)
    fraud_rows = [row for row in rows if _as_int(row.get("label")) == 1]
    misses = [row for row in fraud_rows if _as_int(row.get("prediction")) != 1]
    subtype_counts: dict[str, int] = {}
    for row in misses:
        subtype = str(row.get("attack_subtype") or "unknown")
        subtype_counts[subtype] = subtype_counts.get(subtype, 0) + 1
    return {
        "difficulty_profile": profile_name,
        "difficulty_label": DIFFICULTY_PROFILES[profile_name]["label"],
        "bucket": bucket,
        "record_count": len(rows),
        "fraud_record_count": len(fraud_rows),
        "miss_count": len(misses),
        "metrics": metrics,
        "status": _cell_status(metrics),
        "missed_subtypes": [
            {"subtype": subtype, "miss_count": count}
            for subtype, count in sorted(subtype_counts.items(), key=lambda item: (-item[1], item[0]))
        ],
        "representative_misses": [
            {
                "transaction_id": row.get("transaction_id"),
                "attack_subtype": row.get("attack_subtype"),
                "fraud_score": _as_float(row.get("fraud_score")),
                "reason_codes": [value for value in str(row.get("reason_codes", "")).split(";") if value],
            }
            for row in misses[:3]
        ],
    }


def _cell_status(metrics: dict[str, Any]) -> str:
    recall = _as_float(metrics.get("recall"))
    f1 = _as_float(metrics.get("f1"))
    fpr = _as_float(metrics.get("false_positive_rate"))
    if recall < 0.85 or f1 < 0.85:
        return "weak"
    if recall < 0.95 or f1 < 0.95 or fpr > 0.10:
        return "monitor"
    return "strong"


def _as_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _as_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _new_campaign_id() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return f"campaign_{stamp}_{uuid4().hex[:6]}"


def _timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
