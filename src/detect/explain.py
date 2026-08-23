from typing import Any

import numpy as np


FRIENDLY_REASON_NAMES = {
    "amount": "unusual amount",
    "risk_score": "high generated risk score",
    "billing_shipping_mismatch": "billing and shipping mismatch",
    "customer_transaction_count": "customer velocity",
    "merchant_transaction_count": "merchant velocity",
    "device_transaction_count": "device reuse pattern",
    "session_transaction_count": "session velocity",
    "ip_transaction_count": "IP velocity",
    "customer_txn_count_1h_prior": "customer one-hour velocity",
    "device_txn_count_1h_prior": "device one-hour velocity",
    "customer_decline_count_24h_prior": "recent customer declines",
    "customer_amount_mean_prior": "customer amount baseline",
    "customer_amount_deviation_ratio": "amount deviation from customer history",
    "minutes_since_customer_event": "customer payment cadence",
    "minutes_since_device_event": "device activity cadence",
    "customer_account_age_days": "customer account age",
    "customer_historical_decline_rate": "customer decline history",
    "merchant_age_days": "merchant age",
    "merchant_refund_rate": "merchant refund behavior",
    "merchant_chargeback_rate": "merchant chargeback behavior",
    "merchant_volume_growth_rate": "merchant growth pattern",
    "device_ip_reputation_score": "IP reputation",
    "device_first_seen_days_ago": "device history",
    "device_failed_login_count": "failed login activity",
}


def explain_row(row: dict[str, str], model: dict[str, Any], limit: int = 3) -> list[str]:
    columns = model["feature_columns"]
    mean = np.array(model["mean"], dtype=float)
    std = np.array(model["std"], dtype=float)
    weights = np.array(model["weights"], dtype=float)
    values = np.array([_to_float(row[column]) for column in columns], dtype=float)
    normalized = (values - mean) / std
    contributions = normalized * weights
    ranked = np.argsort(-np.abs(contributions))

    reasons: list[str] = []
    for index in ranked[:limit]:
        column = columns[int(index)]
        direction = "raises risk" if contributions[int(index)] >= 0 else "lowers risk"
        reasons.append(f"{FRIENDLY_REASON_NAMES.get(column, column)} {direction}")
    return reasons


def _to_float(value: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0
