from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class AttackScenario:
    scenario_id: str
    attack_id: str
    bucket: str
    subtype: str
    channel: str
    rail: str
    scope: str
    seed: int
    stealth_level: float
    attack_intensity: float
    event_count: int
    time_window_hours: int
    target_customer_id: str
    target_merchant_id: str
    primary_device_id: str
    generated_at: str
    realism_profile: str = "overlap"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
