from typing import Any


REQUIRED_TRANSACTION_FIELDS = {
    "transaction_id",
    "event_time",
    "amount",
    "currency",
    "channel",
    "rail",
    "transaction_type",
    "status",
    "customer_id",
    "merchant_id",
    "device_id",
    "session_id",
    "ip_address",
    "billing_country",
    "shipping_country",
    "merchant_category",
    "payment_method_type",
    "auth_result",
    "risk_score",
    "label",
    "attack_id",
    "attack_bucket",
    "attack_subtype",
    "scenario_id",
}


def validate_generated_dataset(dataset: Any) -> list[str]:
    errors: list[str] = []
    transaction_ids: set[str] = set()
    customer_ids = {row["customer_id"] for row in dataset.customers}
    merchant_ids = {row["merchant_id"] for row in dataset.merchants}

    for index, row in enumerate(dataset.transactions):
        missing = REQUIRED_TRANSACTION_FIELDS - set(row)
        if missing:
            errors.append(f"transactions[{index}]: missing {sorted(missing)[0]}")

        transaction_id = row.get("transaction_id")
        if transaction_id in transaction_ids:
            errors.append(f"transactions[{index}]: duplicate transaction_id {transaction_id}")
        transaction_ids.add(transaction_id)

        if row.get("amount", 0) <= 0:
            errors.append(f"transactions[{index}]: amount must be positive")
        if not 0 <= row.get("risk_score", -1) <= 1:
            errors.append(f"transactions[{index}]: risk_score must be between 0 and 1")
        if row.get("label") not in {0, 1}:
            errors.append(f"transactions[{index}]: label must be 0 or 1")
        if row.get("customer_id") not in customer_ids:
            errors.append(f"transactions[{index}]: unknown customer_id")
        if row.get("merchant_id") not in merchant_ids:
            errors.append(f"transactions[{index}]: unknown merchant_id")
        if row.get("label") == 1 and not row.get("attack_id"):
            errors.append(f"transactions[{index}]: fraud rows require attack_id")

    return errors

