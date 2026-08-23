from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from src.common.ids import stable_id
from src.common.random import choose, rng_from_seed
from src.generate.scenario import AttackScenario


CURRENCIES = ["USD", "INR", "EUR", "GBP", "SGD"]
COUNTRIES = ["US", "IN", "GB", "SG", "AE", "DE"]
MERCHANT_CATEGORIES = [
    "digital_goods",
    "travel",
    "retail",
    "marketplace",
    "financial_services",
    "gift_cards",
    "electronics",
]
PAYMENT_METHODS = ["debit_card", "credit_card", "wallet", "bank_account"]
AUTH_RESULTS = ["approved", "declined", "soft_decline"]


@dataclass(frozen=True)
class GeneratedDataset:
    transactions: list[dict[str, Any]]
    customers: list[dict[str, Any]]
    merchants: list[dict[str, Any]]
    devices: list[dict[str, Any]]
    attack_instances: list[dict[str, Any]]


def generate_records_for_scenario(scenario: AttackScenario) -> GeneratedDataset:
    rng = rng_from_seed(scenario.seed)
    base_time = datetime(2026, 8, 17, 9, 0, tzinfo=timezone.utc) + timedelta(
        minutes=scenario.seed % 720
    )

    customer = _customer_profile(scenario, rng)
    merchant = _merchant_profile(scenario, rng)
    device = _device_profile(scenario, rng)
    event_times = _campaign_event_times(scenario, base_time, rng)
    transactions = [
        _transaction_record(scenario, index, event_time, rng)
        for index, event_time in enumerate(event_times)
    ]
    attack_instance = {
        "attack_instance_id": stable_id("atk", scenario.scenario_id),
        "scenario_id": scenario.scenario_id,
        "attack_id": scenario.attack_id,
        "bucket": scenario.bucket,
        "subtype": scenario.subtype,
        "scenario_seed": scenario.seed,
        "attack_intensity": scenario.attack_intensity,
        "stealth_level": scenario.stealth_level,
        "time_window_hours": scenario.time_window_hours,
        "generated_record_ids": ",".join(row["transaction_id"] for row in transactions),
    }

    return GeneratedDataset(
        transactions=transactions,
        customers=[customer],
        merchants=[merchant],
        devices=[device],
        attack_instances=[attack_instance],
    )


def generate_benign_records(seed: int, count: int, realism_profile: str = "overlap") -> GeneratedDataset:
    rng = rng_from_seed(seed)
    base_time = datetime(2026, 8, 17, 0, 0, tzinfo=timezone.utc)
    transactions: list[dict[str, Any]] = []
    customers: dict[str, dict[str, Any]] = {}
    merchants: dict[str, dict[str, Any]] = {}
    devices: dict[str, dict[str, Any]] = {}

    for index in range(count):
        customer_id = stable_id("cust", "benign", seed, index // 4)
        merchant_id = stable_id("merch", "benign", seed, index % 18)
        device_id = stable_id("dev", "benign", seed, index // 5)
        session_id = stable_id("sess", "benign", seed, index)
        country = choose(rng, COUNTRIES)
        channel = choose(rng, ["ecommerce", "mobile_app", "marketplace", "wallet"])
        rail = choose(rng, ["card", "wallet", "p2p"])
        is_edge_case = realism_profile == "overlap" and rng.random() < 0.18
        amount = _benign_amount(rng, is_edge_case)
        event_time = base_time + timedelta(minutes=index * rng.randint(3, 25))
        shipping_country = _benign_shipping_country(country, rng, is_edge_case)
        auth_result = _benign_auth_result(rng, is_edge_case)

        customers.setdefault(customer_id, _benign_customer(customer_id, country, rng))
        merchants.setdefault(merchant_id, _benign_merchant(merchant_id, country, rng))
        devices.setdefault(device_id, _benign_device(device_id, session_id, country, rng))

        transactions.append(
            {
                "transaction_id": stable_id("txn", "benign", seed, index),
                "event_time": event_time.isoformat(),
                "amount": amount,
                "currency": choose(rng, CURRENCIES),
                "channel": channel,
                "rail": rail,
                "transaction_type": "purchase",
                "status": "declined" if auth_result != "approved" else "approved",
                "customer_id": customer_id,
                "merchant_id": merchant_id,
                "device_id": device_id,
                "session_id": session_id,
                "ip_address": f"198.51.100.{rng.randint(1, 254)}",
                "billing_country": country,
                "shipping_country": shipping_country,
                "merchant_category": choose(rng, MERCHANT_CATEGORIES),
                "payment_method_type": choose(rng, PAYMENT_METHODS),
                "auth_result": auth_result,
                "risk_score": _benign_risk_score(rng, is_edge_case),
                "label": 0,
                "attack_id": "",
                "attack_bucket": "",
                "attack_subtype": "",
                "scenario_id": "",
                "simulation_segment": "atypical_benign" if is_edge_case else "routine_benign",
            }
        )

    return GeneratedDataset(
        transactions=transactions,
        customers=list(customers.values()),
        merchants=list(merchants.values()),
        devices=list(devices.values()),
        attack_instances=[],
    )


def merge_datasets(datasets: list[GeneratedDataset]) -> GeneratedDataset:
    merged = GeneratedDataset([], [], [], [], [])
    for dataset in datasets:
        merged.transactions.extend(dataset.transactions)
        merged.customers.extend(dataset.customers)
        merged.merchants.extend(dataset.merchants)
        merged.devices.extend(dataset.devices)
        merged.attack_instances.extend(dataset.attack_instances)
    return merged


def _transaction_record(
    scenario: AttackScenario,
    index: int,
    event_time: datetime,
    rng: Any,
) -> dict[str, Any]:
    billing_country = choose(rng, COUNTRIES)
    shipping_country = _shipping_country(scenario, billing_country, rng)
    status, auth_result = _status_and_auth(scenario, index, rng)

    return {
        "transaction_id": stable_id("txn", scenario.scenario_id, index),
        "event_time": event_time.isoformat(),
        "amount": _amount_for_scenario(scenario, rng),
        "currency": choose(rng, CURRENCIES),
        "channel": scenario.channel,
        "rail": scenario.rail,
        "transaction_type": _transaction_type(scenario),
        "status": status,
        "customer_id": scenario.target_customer_id,
        "merchant_id": scenario.target_merchant_id,
        "device_id": _device_id_for_event(scenario, index),
        "session_id": stable_id("sess", scenario.scenario_id, index // 3),
        "ip_address": f"203.0.113.{1 + (scenario.seed + index) % 254}",
        "billing_country": billing_country,
        "shipping_country": shipping_country,
        "merchant_category": _merchant_category(scenario, rng),
        "payment_method_type": _payment_method(scenario, rng),
        "auth_result": auth_result,
        "risk_score": _fraud_risk_score(scenario, rng),
        "label": 1,
        "attack_id": scenario.attack_id,
        "attack_bucket": scenario.bucket,
        "attack_subtype": scenario.subtype,
        "scenario_id": scenario.scenario_id,
        "simulation_segment": "stealth_fraud" if scenario.stealth_level >= 0.65 else "overt_fraud",
    }


def _customer_profile(scenario: AttackScenario, rng: Any) -> dict[str, Any]:
    stealth_like_benign = _stealth_like_benign(scenario)
    return {
        "customer_id": scenario.target_customer_id,
        "age_band": choose(rng, ["18-25", "26-35", "36-50", "51-65"]),
        "tenure_days": rng.randint(60, 3000) if stealth_like_benign else max(0, round(rng.uniform(1, 1800) * scenario.stealth_level)),
        "account_age_days": rng.randint(60, 3000) if stealth_like_benign else max(0, round(rng.uniform(1, 1500) * scenario.stealth_level)),
        "home_country": choose(rng, COUNTRIES),
        "email_domain": choose(rng, ["gmail.com", "outlook.com", "company.example", "proton.me"]),
        "phone_type": choose(rng, ["mobile", "voip", "landline"]),
        "kyc_level": choose(rng, ["low", "medium", "high"]),
        "historical_spend_mean": round(rng.uniform(25, 280) if stealth_like_benign else rng.uniform(30, 350), 2),
        "historical_spend_std": round(rng.uniform(5, 65) if stealth_like_benign else rng.uniform(8, 90), 2),
        "historical_decline_rate": round(rng.uniform(0.0, 0.08) if stealth_like_benign else rng.uniform(0.01, 0.35), 4),
    }


def _merchant_profile(scenario: AttackScenario, rng: Any) -> dict[str, Any]:
    stealth_like_benign = _stealth_like_benign(scenario)
    merchant_age = rng.randint(120, 5000) if stealth_like_benign else max(1, round(rng.uniform(3, 2000) * scenario.stealth_level))
    return {
        "merchant_id": scenario.target_merchant_id,
        "merchant_category": _merchant_category(scenario, rng),
        "merchant_age_days": merchant_age,
        "country": choose(rng, COUNTRIES),
        "payout_account_age_days": max(1, round(merchant_age * rng.uniform(0.1, 0.9))),
        "refund_rate": round(rng.uniform(0.0, 0.08) if stealth_like_benign else rng.uniform(0.01, 0.25), 4),
        "chargeback_rate": round(rng.uniform(0.0, 0.015) if stealth_like_benign else rng.uniform(0.001, 0.08), 4),
        "average_ticket_size": round(rng.uniform(15, 240) if stealth_like_benign else rng.uniform(20, 600), 2),
        "volume_growth_rate": round(rng.uniform(0.01, 0.35) if stealth_like_benign else rng.uniform(0.05, 2.5) * scenario.attack_intensity, 4),
        "risk_tier": choose(rng, ["low", "medium"] if stealth_like_benign else ["low", "medium", "high"]),
    }


def _device_profile(scenario: AttackScenario, rng: Any) -> dict[str, Any]:
    stealth_like_benign = _stealth_like_benign(scenario)
    return {
        "device_id": scenario.primary_device_id,
        "session_id": stable_id("sess", scenario.scenario_id, 0),
        "browser_family": choose(rng, ["Chrome", "Safari", "Firefox", "Edge"]),
        "os_family": choose(rng, ["iOS", "Android", "Windows", "macOS", "Linux"]),
        "device_type": choose(rng, ["mobile", "desktop", "tablet"]),
        "ip_country": choose(rng, COUNTRIES),
        "ip_reputation_score": round(rng.uniform(0.0, 0.25) if stealth_like_benign else rng.uniform(0.2, 0.95), 4),
        "first_seen_days_ago": rng.randint(30, 1500) if stealth_like_benign else max(0, round(rng.uniform(0, 365) * scenario.stealth_level)),
        "session_duration_seconds": round(rng.uniform(20, 900)),
        "failed_login_count": rng.randint(0, 1) if stealth_like_benign else round(rng.uniform(0, 8) * scenario.attack_intensity),
    }


def _benign_customer(customer_id: str, country: str, rng: Any) -> dict[str, Any]:
    return {
        "customer_id": customer_id,
        "age_band": choose(rng, ["18-25", "26-35", "36-50", "51-65"]),
        "tenure_days": rng.randint(30, 3000),
        "account_age_days": rng.randint(30, 3000),
        "home_country": country,
        "email_domain": choose(rng, ["gmail.com", "outlook.com", "company.example"]),
        "phone_type": "mobile",
        "kyc_level": choose(rng, ["medium", "high"]),
        "historical_spend_mean": round(rng.uniform(25, 280), 2),
        "historical_spend_std": round(rng.uniform(5, 65), 2),
        "historical_decline_rate": round(rng.uniform(0.0, 0.08), 4),
    }


def _benign_merchant(merchant_id: str, country: str, rng: Any) -> dict[str, Any]:
    return {
        "merchant_id": merchant_id,
        "merchant_category": choose(rng, MERCHANT_CATEGORIES),
        "merchant_age_days": rng.randint(120, 5000),
        "country": country,
        "payout_account_age_days": rng.randint(90, 4000),
        "refund_rate": round(rng.uniform(0.0, 0.08), 4),
        "chargeback_rate": round(rng.uniform(0.0, 0.015), 4),
        "average_ticket_size": round(rng.uniform(15, 240), 2),
        "volume_growth_rate": round(rng.uniform(0.01, 0.35), 4),
        "risk_tier": choose(rng, ["low", "medium"]),
    }


def _benign_device(device_id: str, session_id: str, country: str, rng: Any) -> dict[str, Any]:
    return {
        "device_id": device_id,
        "session_id": session_id,
        "browser_family": choose(rng, ["Chrome", "Safari", "Firefox", "Edge"]),
        "os_family": choose(rng, ["iOS", "Android", "Windows", "macOS"]),
        "device_type": choose(rng, ["mobile", "desktop", "tablet"]),
        "ip_country": country,
        "ip_reputation_score": round(rng.uniform(0.0, 0.25), 4),
        "first_seen_days_ago": rng.randint(30, 1500),
        "session_duration_seconds": rng.randint(80, 1800),
        "failed_login_count": rng.randint(0, 1),
    }


def _amount_for_scenario(scenario: AttackScenario, rng: Any) -> float:
    if scenario.subtype in {"card_testing", "credential_stuffing"}:
        return round(rng.uniform(0.5, 8.0), 2)
    if scenario.subtype in {"business_email_compromise", "vendor_rerouting", "executive_impersonation"}:
        return round(rng.uniform(3000, 85000) * scenario.attack_intensity, 2)
    if scenario.bucket == "merchant_ecosystem_abuse":
        return round(rng.uniform(80, 1200) * (0.8 + scenario.attack_intensity), 2)
    if scenario.bucket == "post_transaction_abuse":
        return round(rng.uniform(20, 450), 2)
    return round(max(2.0, rng.lognormvariate(3.7, 0.8)), 2)


def _transaction_type(scenario: AttackScenario) -> str:
    if scenario.bucket == "post_transaction_abuse":
        return "refund"
    if scenario.subtype in {"mule_laundering", "authorized_push_payment_scam"}:
        return "transfer"
    if "merchant" in scenario.subtype and scenario.rail in {"ach", "wire"}:
        return "payout"
    return "purchase"


def _status_and_auth(scenario: AttackScenario, index: int, rng: Any) -> tuple[str, str]:
    if scenario.subtype == "card_testing" and index % 3 != 0:
        return "declined", choose(rng, ["declined", "soft_decline"])
    if rng.random() < 0.08 * (1 - scenario.stealth_level):
        return "declined", "declined"
    return "approved", "approved"


def _shipping_country(scenario: AttackScenario, billing_country: str, rng: Any) -> str:
    mismatch_probability = 0.35 * scenario.attack_intensity * (1 - scenario.stealth_level / 2)
    if scenario.realism_profile == "overlap":
        mismatch_probability *= 0.72
    if rng.random() < mismatch_probability:
        return choose(rng, [country for country in COUNTRIES if country != billing_country])
    return billing_country


def _merchant_category(scenario: AttackScenario, rng: Any) -> str:
    if scenario.subtype == "gift_card_abuse":
        return "gift_cards"
    if scenario.bucket == "merchant_ecosystem_abuse":
        return choose(rng, ["marketplace", "electronics", "digital_goods"])
    if scenario.bucket == "social_engineering_payment_fraud":
        return "financial_services"
    return choose(rng, MERCHANT_CATEGORIES)


def _payment_method(scenario: AttackScenario, rng: Any) -> str:
    if scenario.rail == "card":
        return choose(rng, ["debit_card", "credit_card"])
    if scenario.rail in {"ach", "wire", "instant_transfer", "p2p"}:
        return "bank_account"
    if scenario.rail == "wallet":
        return "wallet"
    return choose(rng, PAYMENT_METHODS)


def _device_id_for_event(scenario: AttackScenario, index: int) -> str:
    if scenario.bucket == "credential_based_fraud" and index % 4 == 0:
        return stable_id("dev", scenario.scenario_id, "rotated", index)
    return scenario.primary_device_id


def _campaign_event_times(
    scenario: AttackScenario, base_time: datetime, rng: Any
) -> list[datetime]:
    """Render ordered but non-uniform campaign timing.

    Uniform spacing makes synthetic campaigns easy to recognize. Sampling ordered
    offsets preserves a scenario's duration while creating natural irregularity.
    """
    if scenario.event_count <= 1:
        return [base_time]
    window_minutes = max(1, scenario.time_window_hours * 60)
    offsets = sorted(rng.uniform(0, window_minutes) for _ in range(scenario.event_count))
    return [base_time + timedelta(minutes=round(offset, 2)) for offset in offsets]


def _benign_amount(rng: Any, is_edge_case: bool) -> float:
    if is_edge_case and rng.random() < 0.45:
        return round(max(5.0, rng.lognormvariate(5.4, 0.85)), 2)
    return round(max(2.0, rng.lognormvariate(3.4, 0.75)), 2)


def _benign_shipping_country(country: str, rng: Any, is_edge_case: bool) -> str:
    if is_edge_case and rng.random() < 0.28:
        return choose(rng, [candidate for candidate in COUNTRIES if candidate != country])
    return country


def _benign_auth_result(rng: Any, is_edge_case: bool) -> str:
    if is_edge_case and rng.random() < 0.22:
        return choose(rng, ["declined", "soft_decline"])
    return "approved"


def _benign_risk_score(rng: Any, is_edge_case: bool) -> float:
    if is_edge_case:
        return round(rng.uniform(0.16, 0.66), 4)
    return round(rng.uniform(0.02, 0.36), 4)


def _fraud_risk_score(scenario: AttackScenario, rng: Any) -> float:
    """Generate an upstream risk signal with intentional benign/fraud overlap.

    It is an input signal, not a label.  High-stealth fraud can therefore look less
    suspicious than atypical legitimate activity.
    """
    if scenario.realism_profile == "baseline":
        return round(rng.uniform(0.52, 0.96) * (1 - scenario.stealth_level * 0.25), 4)
    center = 0.33 + 0.38 * scenario.attack_intensity - 0.26 * scenario.stealth_level
    return round(min(0.92, max(0.08, rng.gauss(center, 0.16))), 4)


def _stealth_like_benign(scenario: AttackScenario) -> bool:
    return scenario.realism_profile == "overlap" and scenario.stealth_level >= 0.65
