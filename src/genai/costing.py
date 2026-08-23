import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.common.config import get_project_paths
from src.common.io import read_json, write_json
from src.genai.token_estimator import estimate_tokens_from_payload


def estimate_what_if_costs(
    input_tokens: int,
    output_tokens: int,
    pricing_path: str | Path | None = None,
) -> dict[str, Any]:
    pricing = _load_pricing(pricing_path)
    estimates = []
    for model_key, item in pricing.get("models", {}).items():
        input_cost = input_tokens * float(item.get("input_per_1m", 0)) / 1_000_000
        output_cost = output_tokens * float(item.get("output_per_1m", 0)) / 1_000_000
        estimates.append(
            {
                "model_key": model_key,
                "provider": item.get("provider", ""),
                "model": item.get("model", ""),
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "estimated_input_cost": round(input_cost, 8),
                "estimated_output_cost": round(output_cost, 8),
                "estimated_total_cost": round(input_cost + output_cost, 8),
                "currency": pricing.get("currency", "USD"),
            }
        )
    return {
        "basis": pricing.get("basis", "Approximate estimate, not billing-grade."),
        "estimates": estimates,
    }


def log_usage_event(
    provider: str,
    task: str,
    request_payload: dict[str, Any],
    response_content: dict[str, Any],
    usage_dir: str | Path | None = None,
    context: dict[str, Any] | None = None,
    latency_ms: float | None = None,
) -> dict[str, Any]:
    input_tokens = estimate_tokens_from_payload({"task": task, "payload": request_payload})
    output_tokens = estimate_tokens_from_payload(response_content)
    event = {
        "timestamp": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "provider": provider,
        "task": task,
        "input_tokens_estimated": input_tokens,
        "output_tokens_estimated": output_tokens,
        "context": context or {},
        "latency_ms": latency_ms,
        "fallback": response_content.get("gateway_fallback"),
        "what_if_costs": estimate_what_if_costs(input_tokens, output_tokens),
    }
    target_dir = Path(usage_dir) if usage_dir is not None else get_project_paths().outputs_dir / "usage"
    target_dir.mkdir(parents=True, exist_ok=True)
    with (target_dir / "genai_usage.jsonl").open("a", encoding="utf-8") as file:
        file.write(json.dumps(event, sort_keys=True))
        file.write("\n")
    write_json(target_dir / "latest_cost_estimate.json", event)
    return event


def iteration_usage_summary(iteration_id: str, usage_dir: str | Path | None = None) -> dict[str, Any]:
    target_dir = Path(usage_dir) if usage_dir is not None else get_project_paths().outputs_dir / "usage"
    event_path = target_dir / "genai_usage.jsonl"
    events: list[dict[str, Any]] = []
    if event_path.exists():
        with event_path.open(encoding="utf-8") as file:
            for line in file:
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if event.get("context", {}).get("iteration_id") == iteration_id:
                    events.append(event)

    totals: dict[str, dict[str, Any]] = {}
    for event in events:
        for estimate in event.get("what_if_costs", {}).get("estimates", []):
            key = str(estimate.get("model_key", "unknown"))
            total = totals.setdefault(
                key,
                {
                    "model_key": key,
                    "provider": estimate.get("provider", ""),
                    "model": estimate.get("model", ""),
                    "estimated_total_cost": 0.0,
                    "currency": estimate.get("currency", "USD"),
                },
            )
            total["estimated_total_cost"] += float(estimate.get("estimated_total_cost", 0))
    for total in totals.values():
        total["estimated_total_cost"] = round(total["estimated_total_cost"], 8)

    return {
        "iteration_id": iteration_id,
        "call_count": len(events),
        "input_tokens_estimated": sum(int(event.get("input_tokens_estimated", 0)) for event in events),
        "output_tokens_estimated": sum(int(event.get("output_tokens_estimated", 0)) for event in events),
        "latency_ms_total": round(sum(float(event.get("latency_ms") or 0) for event in events), 2),
        "cost_estimates": list(totals.values()),
        "calls": events,
    }


def _load_pricing(path: str | Path | None = None) -> dict[str, Any]:
    root = get_project_paths().root
    pricing_path = Path(path) if path is not None else root / "configs" / "model_pricing.json"
    if not pricing_path.exists():
        pricing_path = root / "configs" / "model_pricing.example.json"
    return read_json(pricing_path)
