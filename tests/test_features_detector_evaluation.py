import csv
from pathlib import Path

from src.detect.score import score_feature_rows
from src.detect.train import train_baseline_detector
from src.evaluate.reports import build_evaluation_report
from src.features.build_features import build_feature_dataset, feature_columns
from src.generate.pipeline import generate_dataset


def test_features_detector_and_evaluation_pipeline(tmp_path: Path) -> None:
    generated_dir = tmp_path / "generated"
    processed_dir = tmp_path / "processed"
    outputs_dir = tmp_path / "outputs"

    generate_dataset(seed=11, benign_count=40, output_dir=generated_dir)
    feature_rows = build_feature_dataset(
        generated_dir=generated_dir,
        output_path=processed_dir / "features.csv",
    )

    assert feature_rows
    assert "label" not in feature_columns(feature_rows)
    assert "attack_bucket" not in feature_columns(feature_rows)
    assert "customer_txn_count_1h_prior" in feature_columns(feature_rows)
    assert "customer_amount_deviation_ratio" in feature_columns(feature_rows)
    assert any(float(row["customer_transaction_count"]) == 0 for row in feature_rows)
    assert any(float(row["customer_transaction_count"]) > 0 for row in feature_rows)

    metrics = train_baseline_detector(
        features_path=processed_dir / "features.csv",
        model_path=outputs_dir / "models" / "baseline_model.pkl",
        metrics_path=outputs_dir / "metrics" / "train_metrics.json",
        seed=11,
    )
    assert metrics["row_count"] == len(feature_rows)
    assert metrics["feature_count"] == len(feature_columns(feature_rows))
    assert metrics["evaluation_strategy"] == "attack_card_holdout"
    assert metrics["holdout"]["attack_ids"]

    heldout_ids = set(metrics["holdout"]["attack_ids"])
    heldout_transactions = set(metrics["holdout"]["transaction_ids"])
    training_attack_ids = {
        row["attack_id"]
        for row in feature_rows
        if row["label"] == 1 and row["transaction_id"] not in heldout_transactions
    }
    assert not heldout_ids & training_attack_ids

    scored_rows = score_feature_rows(
        features_path=processed_dir / "features.csv",
        model_path=outputs_dir / "models" / "baseline_model.pkl",
        output_path=outputs_dir / "scores" / "scores.csv",
    )
    assert len(scored_rows) == len(feature_rows)
    assert {"transaction_id", "fraud_score", "prediction", "reason_codes", "ml_fraud_score", "llm_reviewed"} <= set(scored_rows[0])
    assert sum(int(row["llm_reviewed"]) for row in scored_rows) == 5

    report = build_evaluation_report(
        scores_path=outputs_dir / "scores" / "scores.csv",
        train_metrics_path=outputs_dir / "metrics" / "train_metrics.json",
        output_dir=outputs_dir / "reports",
    )
    assert report["row_count"] == len(feature_rows)
    assert "ml_only_overall" in report
    assert report["heldout_attack_benchmark"]["evaluation_strategy"] == "attack_card_holdout"
    assert report["heldout_attack_benchmark"]["row_count"] == len(metrics["holdout"]["transaction_ids"])
    assert report["hybrid_review_summary"]["reviewed_row_count"] == 5
    assert (outputs_dir / "reports" / "bucket_performance.csv").exists()

    with (outputs_dir / "reports" / "bucket_performance.csv").open(encoding="utf-8") as file:
        bucket_rows = list(csv.DictReader(file))
    assert bucket_rows
