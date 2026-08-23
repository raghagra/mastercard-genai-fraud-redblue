from collections.abc import Iterable
from typing import Any

from src.common.ids import stable_id
from src.common.random import choose, rng_from_seed, sample_range
from src.generate.scenario import AttackScenario, utc_now_iso


DEFAULT_CHANNELS_BY_BUCKET = {
    "credential_based_fraud": ["ecommerce", "mobile_app", "api"],
    "social_engineering_payment_fraud": ["email", "bank_transfer", "call_center"],
    "identity_onboarding_fraud": ["onboarding", "merchant_portal"],
    "post_transaction_abuse": ["customer_support", "ecommerce"],
    "merchant_ecosystem_abuse": ["marketplace", "merchant_portal", "bank_transfer"],
}


def build_scenario(
    attack_card: dict[str, Any],
    seed: int,
    scenario_index: int = 0,
    stealth_level: float | None = None,
    attack_intensity: float | None = None,
    realism_profile: str = "overlap",
) -> AttackScenario:
    rng = rng_from_seed(seed)
    generation_strategy = attack_card["generation_strategy"]

    sampled_stealth = (
        stealth_level
        if stealth_level is not None
        else sample_range(rng, generation_strategy["stealth_level_range"])
    )
    sampled_intensity = attack_intensity if attack_intensity is not None else rng.uniform(0.35, 0.9)
    event_count = _sample_event_count(
        generation_strategy["volume_range"],
        sampled_intensity,
        attack_card["scope"],
    )

    attack_id = attack_card["attack_id"]
    scenario_id = stable_id("scn", attack_id, seed, scenario_index)
    customer_id = stable_id("cust", scenario_id, "customer")
    merchant_id = stable_id("merch", scenario_id, "merchant")
    device_id = stable_id("dev", scenario_id, "device")

    return AttackScenario(
        scenario_id=scenario_id,
        attack_id=attack_id,
        bucket=attack_card["bucket"],
        subtype=attack_card["subtype"],
        channel=_resolve_channel(attack_card, rng),
        rail=attack_card["rail"],
        scope=attack_card["scope"],
        seed=seed,
        stealth_level=round(float(sampled_stealth), 4),
        attack_intensity=round(float(sampled_intensity), 4),
        event_count=event_count,
        time_window_hours=_time_window_hours(
            attack_card["scope"],
            event_count,
            sampled_stealth,
            float(generation_strategy.get("time_window_multiplier", 1.0)),
        ),
        target_customer_id=customer_id,
        target_merchant_id=merchant_id,
        primary_device_id=device_id,
        generated_at=utc_now_iso(),
        realism_profile=realism_profile,
    )


def build_scenarios(
    attack_cards: Iterable[dict[str, Any]],
    seed: int,
    per_card: int = 1,
    realism_profile: str = "overlap",
) -> list[AttackScenario]:
    scenarios: list[AttackScenario] = []
    scenario_index = 0

    for card in attack_cards:
        for _ in range(per_card):
            scenarios.append(
                build_scenario(
                    card,
                    seed=seed + scenario_index,
                    scenario_index=scenario_index,
                    realism_profile=realism_profile,
                )
            )
            scenario_index += 1

    return scenarios


def _sample_event_count(volume_range: list[int], intensity: float, scope: str) -> int:
    low, high = volume_range
    scaled = low + (high - low) * intensity
    event_count = max(1, round(scaled))
    if scope == "multi_step_campaign":
        return max(2, event_count)
    return event_count


def _time_window_hours(
    scope: str, event_count: int, stealth_level: float, multiplier: float = 1.0
) -> int:
    if scope == "single_event":
        base_hours = 1 + event_count * stealth_level / 12
    else:
        base_hours = 2 + event_count * (0.5 + stealth_level)
    return max(1, round(base_hours * max(0.25, multiplier)))


def _resolve_channel(attack_card: dict[str, Any], rng: Any) -> str:
    channel = attack_card["channel"]
    if isinstance(channel, str):
        return channel

    bucket = attack_card["bucket"]
    return choose(rng, DEFAULT_CHANNELS_BY_BUCKET.get(bucket, ["ecommerce"]))
