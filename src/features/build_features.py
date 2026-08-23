import csv
from collections import defaultdict, deque
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from src.common.config import get_project_paths
from src.features.encoders import bool_as_int, encode_category, fit_category_maps


CATEGORICAL_COLUMNS = [
    "currency",
    "channel",
    "rail",
    "transaction_type",
    "status",
    "billing_country",
    "shipping_country",
    "merchant_category",
    "payment_method_type",
    "auth_result",
]

LABEL_COLUMNS = [
    "label",
    "attack_id",
    "attack_bucket",
    "attack_subtype",
    "scenario_id",
    "attack_id",
]


def build_feature_dataset(
    generated_dir: str | Path | None = None,
    output_path: str | Path | None = None,
) -> list[dict[str, Any]]:
    paths = get_project_paths()
    source_dir = Path(generated_dir) if generated_dir is not None else paths.generated_data_dir
    target_path = Path(output_path) if output_path is not None else paths.processed_data_dir / "features.csv"

    transactions = _read_csv(source_dir / "transactions.csv")
    customers = _index_by(_read_csv(source_dir / "customers.csv"), "customer_id")
    merchants = _index_by(_read_csv(source_dir / "merchants.csv"), "merchant_id")
    devices = _index_by(_read_csv(source_dir / "devices.csv"), "device_id")
    category_maps = fit_category_maps(transactions, CATEGORICAL_COLUMNS)
    behavioral_state = _build_behavioral_state(transactions)

    feature_rows = [
        _feature_row(row, customers, merchants, devices, category_maps, behavioral_state)
        for row in transactions
    ]
    _write_csv(target_path, feature_rows)
    return feature_rows


def _feature_row(
    row: dict[str, str],
    customers: dict[str, dict[str, str]],
    merchants: dict[str, dict[str, str]],
    devices: dict[str, dict[str, str]],
    category_maps: dict[str, dict[str, int]],
    behavioral_state: dict[str, dict[str, float]],
) -> dict[str, Any]:
    customer = customers.get(row["customer_id"], {})
    merchant = merchants.get(row["merchant_id"], {})
    device = devices.get(row["device_id"], {})
    event_hour = _event_hour(row["event_time"])
    behavior = behavioral_state.get(row["transaction_id"], {})

    features: dict[str, Any] = {
        "transaction_id": row["transaction_id"],
        "amount": _to_float(row["amount"]),
        "risk_score": _to_float(row["risk_score"]),
        "event_hour": event_hour,
        "billing_shipping_mismatch": bool_as_int(row["billing_country"] != row["shipping_country"]),
        # All behavioral values are point-in-time: they use events that occurred
        # before this transaction, never the complete batch or future activity.
        "customer_transaction_count": behavior.get("customer_transaction_count_prior", 0.0),
        "merchant_transaction_count": behavior.get("merchant_transaction_count_prior", 0.0),
        "device_transaction_count": behavior.get("device_transaction_count_prior", 0.0),
        "session_transaction_count": behavior.get("session_transaction_count_prior", 0.0),
        "ip_transaction_count": behavior.get("ip_transaction_count_prior", 0.0),
        "customer_txn_count_1h_prior": behavior.get("customer_txn_count_1h_prior", 0.0),
        "device_txn_count_1h_prior": behavior.get("device_txn_count_1h_prior", 0.0),
        "customer_decline_count_24h_prior": behavior.get("customer_decline_count_24h_prior", 0.0),
        "customer_amount_mean_prior": behavior.get("customer_amount_mean_prior", 0.0),
        "customer_amount_deviation_ratio": behavior.get("customer_amount_deviation_ratio", 0.0),
        "minutes_since_customer_event": behavior.get("minutes_since_customer_event", 1440.0),
        "minutes_since_device_event": behavior.get("minutes_since_device_event", 1440.0),
        "customer_account_age_days": _to_float(customer.get("account_age_days", "0")),
        "customer_historical_decline_rate": _to_float(customer.get("historical_decline_rate", "0")),
        "customer_historical_spend_mean": _to_float(customer.get("historical_spend_mean", "0")),
        "merchant_age_days": _to_float(merchant.get("merchant_age_days", "0")),
        "merchant_refund_rate": _to_float(merchant.get("refund_rate", "0")),
        "merchant_chargeback_rate": _to_float(merchant.get("chargeback_rate", "0")),
        "merchant_volume_growth_rate": _to_float(merchant.get("volume_growth_rate", "0")),
        "device_ip_reputation_score": _to_float(device.get("ip_reputation_score", "0")),
        "device_first_seen_days_ago": _to_float(device.get("first_seen_days_ago", "0")),
        "device_failed_login_count": _to_float(device.get("failed_login_count", "0")),
        "label": _to_int(row["label"]),
        "attack_bucket": row.get("attack_bucket", ""),
        "attack_subtype": row.get("attack_subtype", ""),
        "attack_id": row.get("attack_id", ""),
        "scenario_id": row.get("scenario_id", ""),
        "simulation_segment": row.get("simulation_segment", ""),
    }

    for column in CATEGORICAL_COLUMNS:
        features[f"{column}_code"] = encode_category(row.get(column, ""), category_maps[column])

    return features


def feature_columns(rows: list[dict[str, Any]]) -> list[str]:
    if not rows:
        return []
    return [
        column
        for column in rows[0]
        if column not in {
            "transaction_id", "label", "attack_id", "attack_bucket", "attack_subtype",
            "scenario_id", "simulation_segment",
        }
    ]


def _build_behavioral_state(transactions: list[dict[str, str]]) -> dict[str, dict[str, float]]:
    """Build online-style features in event-time order.

    This deliberately replaces full-file counters, which would leak future events
    into a transaction's score. In production the same state belongs in a feature
    store or stream processor; here it is rebuilt deterministically for a batch.
    """
    ordered = sorted(
        enumerate(transactions), key=lambda item: (_parse_time(item[1].get("event_time", "")), item[0])
    )
    total_counts: dict[str, defaultdict[str, int]] = {
        column: defaultdict(int)
        for column in ["customer_id", "merchant_id", "device_id", "session_id", "ip_address"]
    }
    customer_amounts: dict[str, tuple[float, int]] = defaultdict(lambda: (0.0, 0))
    customer_last_seen: dict[str, datetime] = {}
    device_last_seen: dict[str, datetime] = {}
    customer_1h: dict[str, deque[datetime]] = defaultdict(deque)
    device_1h: dict[str, deque[datetime]] = defaultdict(deque)
    customer_declines_24h: dict[str, deque[datetime]] = defaultdict(deque)
    results: dict[str, dict[str, float]] = {}

    for _, row in ordered:
        event_time = _parse_time(row.get("event_time", ""))
        customer_id = row.get("customer_id", "")
        device_id = row.get("device_id", "")
        amount = _to_float(row.get("amount", "0"))
        amount_sum, amount_count = customer_amounts[customer_id]
        prior_mean = amount_sum / amount_count if amount_count else 0.0
        customer_previous = customer_last_seen.get(customer_id)
        device_previous = device_last_seen.get(device_id)
        _expire(customer_1h[customer_id], event_time - timedelta(hours=1))
        _expire(device_1h[device_id], event_time - timedelta(hours=1))
        _expire(customer_declines_24h[customer_id], event_time - timedelta(hours=24))

        results[row["transaction_id"]] = {
            "customer_transaction_count_prior": float(total_counts["customer_id"][customer_id]),
            "merchant_transaction_count_prior": float(total_counts["merchant_id"][row.get("merchant_id", "")]),
            "device_transaction_count_prior": float(total_counts["device_id"][device_id]),
            "session_transaction_count_prior": float(total_counts["session_id"][row.get("session_id", "")]),
            "ip_transaction_count_prior": float(total_counts["ip_address"][row.get("ip_address", "")]),
            "customer_txn_count_1h_prior": float(len(customer_1h[customer_id])),
            "device_txn_count_1h_prior": float(len(device_1h[device_id])),
            "customer_decline_count_24h_prior": float(len(customer_declines_24h[customer_id])),
            "customer_amount_mean_prior": round(prior_mean, 4),
            "customer_amount_deviation_ratio": round(
                abs(amount - prior_mean) / max(1.0, prior_mean), 4
            ) if amount_count else 0.0,
            "minutes_since_customer_event": _minutes_since(customer_previous, event_time),
            "minutes_since_device_event": _minutes_since(device_previous, event_time),
        }
        for column in total_counts:
            total_counts[column][row.get(column, "")] += 1
        customer_amounts[customer_id] = (amount_sum + amount, amount_count + 1)
        customer_last_seen[customer_id] = event_time
        device_last_seen[device_id] = event_time
        customer_1h[customer_id].append(event_time)
        device_1h[device_id].append(event_time)
        if row.get("auth_result") in {"declined", "soft_decline"}:
            customer_declines_24h[customer_id].append(event_time)

    return results


def _expire(values: deque[datetime], cutoff: datetime) -> None:
    while values and values[0] < cutoff:
        values.popleft()


def _minutes_since(previous: datetime | None, current: datetime) -> float:
    if previous is None:
        return 1440.0
    return round(min(43_200.0, max(0.0, (current - previous).total_seconds() / 60)), 4)


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as file:
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


def _index_by(rows: list[dict[str, str]], key: str) -> dict[str, dict[str, str]]:
    return {row[key]: row for row in rows if row.get(key)}


def _to_float(value: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _to_int(value: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _event_hour(value: str) -> int:
    try:
        return datetime.fromisoformat(value).hour
    except ValueError:
        return 0


def _parse_time(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=datetime.now().astimezone().tzinfo)
    except (TypeError, ValueError):
        return datetime.min.replace(tzinfo=datetime.now().astimezone().tzinfo)
