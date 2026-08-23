"""Canonical flat transaction contract for demo portfolio onboarding."""

REQUIRED_COLUMNS = {
    "transaction_id",
    "event_time",
    "amount",
    "currency",
    "customer_id",
    "merchant_id",
    "channel",
    "rail",
    "transaction_type",
    "status",
}

OPTIONAL_COLUMNS = {
    "device_id", "session_id", "ip_address", "billing_country", "shipping_country",
    "merchant_category", "payment_method_type", "auth_result", "risk_score", "label",
    "customer_account_age_days", "customer_historical_decline_rate", "customer_historical_spend_mean",
    "merchant_age_days", "merchant_refund_rate", "merchant_chargeback_rate",
    "merchant_volume_growth_rate", "device_ip_reputation_score", "device_first_seen_days_ago",
    "device_failed_login_count",
}

CANONICAL_COLUMNS = sorted(REQUIRED_COLUMNS | OPTIONAL_COLUMNS)

# The demo contract deliberately rejects direct-PII/payment-instrument columns.
PROHIBITED_COLUMNS = {
    "pan", "card_number", "card_pan", "cvv", "cvc", "account_number", "iban",
    "email", "phone", "full_name", "first_name", "last_name", "address",
}

DEFAULTS = {
    "device_id": "unknown_device",
    "session_id": "unknown_session",
    "ip_address": "unknown_ip",
    "billing_country": "ZZ",
    "shipping_country": "ZZ",
    "merchant_category": "unknown",
    "payment_method_type": "unknown",
    "auth_result": "unknown",
    "risk_score": "0",
    "customer_account_age_days": "0",
    "customer_historical_decline_rate": "0",
    "customer_historical_spend_mean": "0",
    "merchant_age_days": "0",
    "merchant_refund_rate": "0",
    "merchant_chargeback_rate": "0",
    "merchant_volume_growth_rate": "0",
    "device_ip_reputation_score": "0",
    "device_first_seen_days_ago": "0",
    "device_failed_login_count": "0",
}
