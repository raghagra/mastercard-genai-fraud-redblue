from pathlib import Path

from fastapi.testclient import TestClient

from src.api.main import app
from src.common.config import ProjectPaths, get_project_paths
from src.detect.train import train_baseline_detector
from src.features.build_features import build_feature_dataset
from src.generate.pipeline import generate_dataset
from src.portfolio.service import create_dataset, score_upcoming_transactions, template_csv


def test_portfolio_template_create_and_delete(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("src.portfolio.service.get_project_paths", lambda: _paths(tmp_path))
    client = TestClient(app)
    template = client.get("/portfolio/template")
    assert template.status_code == 200
    assert "transaction_id" in template.json()["historical_csv"]

    response = client.post(
        "/portfolio/datasets",
        json={
            "dataset_name": "Judge demo",
            "historical_csv": _csv([_row("hist_001", "2026-08-17T09:00:00+00:00")], include_label=True),
            "upcoming_csv": _csv([_row("next_001", "2026-08-17T10:00:00+00:00")]),
        },
    )
    assert response.status_code == 200
    dataset_id = response.json()["dataset"]["dataset_id"]
    assert response.json()["dataset"]["row_counts"] == {"historical": 1, "upcoming": 1}
    assert client.get(f"/portfolio/datasets/{dataset_id}").status_code == 200
    assert client.delete(f"/portfolio/datasets/{dataset_id}").status_code == 200


def test_portfolio_scores_upcoming_rows_with_selected_iteration_model(tmp_path: Path, monkeypatch) -> None:
    paths = _paths(tmp_path)
    monkeypatch.setattr("src.portfolio.service.get_project_paths", lambda: paths)
    generated = tmp_path / "synthetic" / "generated"
    features = tmp_path / "synthetic" / "features.csv"
    model = paths.outputs_dir / "iterations" / "iteration_model" / "models" / "baseline_model.pkl"
    metrics = paths.outputs_dir / "iterations" / "iteration_model" / "metrics" / "train_metrics.json"
    generate_dataset(seed=17, benign_count=40, output_dir=generated)
    build_feature_dataset(generated_dir=generated, output_path=features)
    train_baseline_detector(features_path=features, model_path=model, metrics_path=metrics, seed=17)

    manifest = create_dataset(
        _csv([_row("hist_001", "2026-08-17T09:00:00+00:00")], include_label=True),
        _csv([_row("next_001", "2026-08-17T10:00:00+00:00")]),
    )
    result = score_upcoming_transactions(manifest["dataset_id"], model_iteration_id="iteration_model")

    assert result["mode"] == "live_advisory_scoring"
    assert result["upcoming_count"] == 1
    assert result["results"][0]["transaction_id"] == "next_001"


def test_portfolio_rejects_direct_pii_columns(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("src.portfolio.service.get_project_paths", lambda: _paths(tmp_path))
    invalid = template_csv().replace("transaction_id", "transaction_id,card_number", 1) + "bad\n"
    try:
        create_dataset(invalid, _csv([_row("next_001", "2026-08-17T10:00:00+00:00")]))
    except ValueError as exc:
        assert "prohibited" in str(exc)
    else:
        raise AssertionError("Expected direct PII validation failure")


def _csv(rows: list[dict[str, str]], include_label: bool = False) -> str:
    import csv
    import io

    columns = template_csv(include_label=include_label).splitlines()[0].split(",")
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=columns, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


def _row(transaction_id: str, event_time: str) -> dict[str, str]:
    return {
        "transaction_id": transaction_id, "event_time": event_time, "amount": "120.50", "currency": "USD",
        "customer_id": "cust_demo", "merchant_id": "merch_demo", "channel": "ecommerce", "rail": "card",
        "transaction_type": "purchase", "status": "approved", "device_id": "dev_demo", "session_id": "sess_demo",
        "ip_address": "pseudonymous_ip_1", "billing_country": "US", "shipping_country": "US",
        "merchant_category": "retail", "payment_method_type": "credit_card", "auth_result": "approved",
        "risk_score": "0.1", "label": "0",
    }


def _paths(tmp_path: Path) -> ProjectPaths:
    real_paths = get_project_paths()
    return ProjectPaths(
        root=real_paths.root, schemas_dir=real_paths.schemas_dir, attack_cards_dir=real_paths.attack_cards_dir,
        generated_data_dir=tmp_path / "data" / "generated", processed_data_dir=tmp_path / "data" / "processed",
        outputs_dir=tmp_path / "outputs",
    )
