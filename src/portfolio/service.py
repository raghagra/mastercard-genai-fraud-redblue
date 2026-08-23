import csv
import io
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from uuid import uuid4

from src.common.config import get_project_paths
from src.common.io import read_json, write_json
from src.detect.score import score_feature_rows
from src.features.build_features import build_feature_dataset
from src.genai.gateway import GenAIGateway
from src.portfolio.contract import CANONICAL_COLUMNS, DEFAULTS, PROHIBITED_COLUMNS, REQUIRED_COLUMNS


class PortfolioValidationError(ValueError):
    pass


def template_csv(include_label: bool = False) -> str:
    columns = [column for column in CANONICAL_COLUMNS if include_label or column != "label"]
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=columns)
    writer.writeheader()
    return output.getvalue()


def create_dataset(historical_csv: str, upcoming_csv: str, dataset_name: str = "local_demo") -> dict[str, Any]:
    historical_rows, historical_quality = _parse_and_normalize(historical_csv, "historical", labels_allowed=True)
    upcoming_rows, upcoming_quality = _parse_and_normalize(upcoming_csv, "upcoming", labels_allowed=False)
    duplicate_ids = {row["transaction_id"] for row in historical_rows} & {
        row["transaction_id"] for row in upcoming_rows
    }
    if duplicate_ids:
        raise PortfolioValidationError("transaction_id values must be unique across historical and upcoming files")

    dataset_id = f"portfolio_{uuid4().hex[:12]}"
    root = _dataset_root(dataset_id)
    raw_dir = root / "raw"
    generated_dir = root / "generated"
    raw_dir.mkdir(parents=True, exist_ok=False)
    _write_csv(raw_dir / "historical_transactions.csv", historical_rows)
    _write_csv(raw_dir / "upcoming_transactions.csv", upcoming_rows)
    _write_normalized_dataset(generated_dir, [*historical_rows, *upcoming_rows])
    manifest = {
        "dataset_id": dataset_id,
        "dataset_name": _safe_name(dataset_name),
        "storage_mode": "local_demo_only",
        "genai_data_policy": {
            "default": "no_uploaded_rows_sent_to_genai",
            "cloud_requires_explicit_acknowledgement": True,
        },
        "created_at": datetime.now().astimezone().replace(microsecond=0).isoformat(),
        "row_counts": {"historical": len(historical_rows), "upcoming": len(upcoming_rows)},
        "data_quality": {"historical": historical_quality, "upcoming": upcoming_quality},
        "warnings": [
            "Local demo storage only. Delete this dataset after the demonstration.",
            "Do not upload PAN, account numbers, direct PII, or production data without authorization.",
            "Upcoming transaction labels are intentionally ignored during advisory scoring.",
        ],
    }
    write_json(root / "manifest.json", manifest)
    return manifest


def list_datasets() -> list[dict[str, Any]]:
    base = _datasets_root()
    if not base.exists():
        return []
    manifests = []
    for path in sorted(base.glob("portfolio_*/manifest.json"), reverse=True):
        manifests.append(read_json(path))
    return manifests


def get_dataset(dataset_id: str) -> dict[str, Any]:
    path = _dataset_root(_validate_dataset_id(dataset_id)) / "manifest.json"
    if not path.exists():
        raise FileNotFoundError(f"Portfolio dataset not found: {dataset_id}")
    return read_json(path)


def score_upcoming_transactions(
    dataset_id: str,
    model_iteration_id: str | None = None,
    enable_genai_review: bool = False,
    cloud_data_acknowledged: bool = False,
) -> dict[str, Any]:
    """Build point-in-time features over history + upcoming rows and score only upcoming rows."""
    manifest = get_dataset(dataset_id)
    review_route = _review_route()
    if enable_genai_review and review_route["is_cloud"] and not cloud_data_acknowledged:
        raise PortfolioValidationError(
            "The active GenAI reviewer is cloud-hosted. Explicit data-routing acknowledgement is required."
        )
    root = _dataset_root(dataset_id)
    generated_dir = root / "generated"
    processed_dir = root / "processed"
    scores_dir = root / "scores"
    feature_path = processed_dir / "features.csv"
    rows = build_feature_dataset(generated_dir=generated_dir, output_path=feature_path)
    model_path, model_source = _resolve_model(model_iteration_id)
    scored = score_feature_rows(
        features_path=feature_path,
        model_path=model_path,
        output_path=scores_dir / "all_scores.csv",
        iteration_id=f"portfolio:{dataset_id}",
        enable_llm_review=enable_genai_review,
    )
    upcoming_ids = {row["transaction_id"] for row in _read_csv(root / "raw" / "upcoming_transactions.csv")}
    upcoming_scores = [row for row in scored if row["transaction_id"] in upcoming_ids]
    _write_csv(scores_dir / "upcoming_scores.csv", upcoming_scores)
    result = {
        "dataset_id": dataset_id,
        "mode": "live_advisory_scoring",
        "model_source": model_source,
        "genai_review_enabled": enable_genai_review,
        "genai_data_route": review_route if enable_genai_review else {"enabled": False},
        "upcoming_count": len(upcoming_scores),
        "flagged_count": sum(1 for row in upcoming_scores if int(row["prediction"]) == 1),
        "results": upcoming_scores,
        "disclosure": (
            "Scores are advisory and uncalibrated for this portfolio unless a labeled historical "
            "backtest and threshold calibration have been completed."
        ),
    }
    write_json(scores_dir / "advisory_summary.json", result)
    return result


def delete_dataset(dataset_id: str) -> None:
    root = _dataset_root(_validate_dataset_id(dataset_id))
    if not root.exists():
        raise FileNotFoundError(f"Portfolio dataset not found: {dataset_id}")
    shutil.rmtree(root)


def _parse_and_normalize(content: str, partition: str, labels_allowed: bool) -> tuple[list[dict[str, str]], dict[str, Any]]:
    if not content.strip():
        raise PortfolioValidationError(f"{partition} CSV is empty")
    reader = csv.DictReader(io.StringIO(content))
    headers = {header.strip() for header in (reader.fieldnames or []) if header}
    prohibited = sorted(headers & PROHIBITED_COLUMNS)
    if prohibited:
        raise PortfolioValidationError(f"{partition} CSV contains prohibited direct-PII fields: {', '.join(prohibited)}")
    missing = sorted(REQUIRED_COLUMNS - headers)
    if missing:
        raise PortfolioValidationError(f"{partition} CSV missing required columns: {', '.join(missing)}")

    rows: list[dict[str, str]] = []
    seen_ids: set[str] = set()
    missing_optional: dict[str, int] = {column: 0 for column in CANONICAL_COLUMNS if column not in REQUIRED_COLUMNS}
    for line_number, raw in enumerate(reader, start=2):
        row = {key.strip(): (value or "").strip() for key, value in raw.items() if key}
        transaction_id = row.get("transaction_id", "")
        if not transaction_id or transaction_id in seen_ids:
            raise PortfolioValidationError(f"{partition} CSV line {line_number}: transaction_id is missing or duplicated")
        seen_ids.add(transaction_id)
        _validate_row(row, partition, line_number)
        normalized = {column: row.get(column, "") for column in CANONICAL_COLUMNS}
        for column, default in DEFAULTS.items():
            if not normalized[column]:
                normalized[column] = default
                missing_optional[column] += 1
        normalized["label"] = row.get("label", "") if labels_allowed else ""
        normalized["source_partition"] = partition
        rows.append(normalized)
    if not rows:
        raise PortfolioValidationError(f"{partition} CSV has no data rows")
    return rows, {
        "row_count": len(rows),
        "missing_optional_values": {key: value for key, value in missing_optional.items() if value},
        "unrecognized_columns_ignored": sorted(headers - set(CANONICAL_COLUMNS)),
    }


def _validate_row(row: dict[str, str], partition: str, line_number: int) -> None:
    try:
        if float(row["amount"]) <= 0:
            raise ValueError
    except (TypeError, ValueError):
        raise PortfolioValidationError(f"{partition} CSV line {line_number}: amount must be a positive number") from None
    try:
        datetime.fromisoformat(row["event_time"])
    except ValueError:
        raise PortfolioValidationError(f"{partition} CSV line {line_number}: event_time must be ISO 8601") from None


def _write_normalized_dataset(target: Path, rows: list[dict[str, str]]) -> None:
    transactions = []
    customers: dict[str, dict[str, str]] = {}
    merchants: dict[str, dict[str, str]] = {}
    devices: dict[str, dict[str, str]] = {}
    for row in rows:
        transactions.append({
            key: row[key] for key in [
                "transaction_id", "event_time", "amount", "currency", "channel", "rail", "transaction_type",
                "status", "customer_id", "merchant_id", "device_id", "session_id", "ip_address", "billing_country",
                "shipping_country", "merchant_category", "payment_method_type", "auth_result", "risk_score", "label",
            ]
        } | {"attack_id": "", "attack_bucket": "", "attack_subtype": "", "scenario_id": "", "simulation_segment": "external_portfolio"})
        customers.setdefault(row["customer_id"], {
            "customer_id": row["customer_id"], "account_age_days": row["customer_account_age_days"],
            "historical_decline_rate": row["customer_historical_decline_rate"],
            "historical_spend_mean": row["customer_historical_spend_mean"],
        })
        merchants.setdefault(row["merchant_id"], {
            "merchant_id": row["merchant_id"], "merchant_age_days": row["merchant_age_days"],
            "refund_rate": row["merchant_refund_rate"], "chargeback_rate": row["merchant_chargeback_rate"],
            "volume_growth_rate": row["merchant_volume_growth_rate"],
        })
        devices.setdefault(row["device_id"], {
            "device_id": row["device_id"], "ip_reputation_score": row["device_ip_reputation_score"],
            "first_seen_days_ago": row["device_first_seen_days_ago"], "failed_login_count": row["device_failed_login_count"],
        })
    target.mkdir(parents=True, exist_ok=True)
    _write_csv(target / "transactions.csv", transactions)
    _write_csv(target / "customers.csv", list(customers.values()))
    _write_csv(target / "merchants.csv", list(merchants.values()))
    _write_csv(target / "devices.csv", list(devices.values()))
    _write_csv(target / "attack_instances.csv", [])


def _resolve_model(iteration_id: str | None) -> tuple[Path, str]:
    paths = get_project_paths()
    if iteration_id:
        candidate = paths.outputs_dir / "iterations" / iteration_id / "models" / "baseline_model.pkl"
        if not candidate.exists():
            raise PortfolioValidationError(f"Model iteration not found: {iteration_id}")
        return candidate, f"iteration:{iteration_id}"
    candidates = sorted(paths.outputs_dir.glob("iterations/*/models/baseline_model.pkl"))
    if candidates:
        return candidates[-1], f"iteration:{candidates[-1].parents[1].name}"
    fallback = paths.outputs_dir / "models" / "baseline_model.pkl"
    if fallback.exists():
        return fallback, "default_baseline"
    raise PortfolioValidationError("No trained detector model found. Run a closed-loop iteration first.")


def _review_route() -> dict[str, Any]:
    gateway = GenAIGateway()
    provider_name = gateway.config.task_routes.get("defense_review", gateway.config.default_provider)
    provider_config = gateway.config.providers.get(provider_name, {})
    provider_type = str(provider_config.get("type", "local_rules"))
    base_url = str(provider_config.get("base_url", ""))
    host = urlparse(base_url).hostname if base_url else None
    is_local = provider_type == "local_rules" or (
        provider_type == "openai_compatible" and host in {"localhost", "127.0.0.1", "::1"}
    )
    return {
        "enabled": True,
        "provider": provider_name,
        "provider_type": provider_type,
        "destination": "local_machine" if is_local else "cloud_or_remote_endpoint",
        "is_cloud": not is_local,
        "cloud_acknowledgement_required": not is_local,
    }


def _datasets_root() -> Path:
    return get_project_paths().outputs_dir / "portfolio_datasets"


def _dataset_root(dataset_id: str) -> Path:
    return _datasets_root() / dataset_id


def _validate_dataset_id(dataset_id: str) -> str:
    if not re.fullmatch(r"portfolio_[a-f0-9]{12}", dataset_id):
        raise PortfolioValidationError("Invalid portfolio dataset identifier")
    return dataset_id


def _safe_name(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9 _.-]", "_", name.strip())[:100] or "local_demo"


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
