import json
from typing import Any


SYSTEM_PROMPT = (
    "You are a defensive payment-fraud simulation assistant. Analyze only synthetic, "
    "non-production data and provide defensive risk assessment; never provide instructions "
    "to commit or evade fraud. Return only valid JSON. Do not include markdown."
)


def request_body(request_task: str, request_payload: dict[str, Any]) -> str:
    return json.dumps(
        {
            "task": request_task,
            "payload": request_payload,
            "response_contract": response_contract(request_task),
        },
        sort_keys=True,
    )


def response_contract(task: str) -> dict[str, Any]:
    if task == "attack_mutation":
        return {
            "variant_name": "short defensive simulation variant name",
            "rationale": "one sentence explaining the defensive stress-test value",
            "mutation_focus": [
                "increase_benign_overlap|pace_attempts|extend_campaign_window|increase_edge_case_diversity"
            ],
        }
    if task == "defense_review":
        return {
            "semantic_risk_score": "number from 0.0 to 1.0",
            "novelty_score": "number from 0.0 to 1.0",
            "recommendation": "allow|review|step_up_authentication|flag",
            "rationale": "brief defensive explanation based on supplied signals",
            "risk_indicators": ["string"],
        }
    return {"summary": "string"}


def parse_json_content(content: str) -> dict[str, Any]:
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        start = content.find("{")
        end = content.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return {"raw_content": content}
        parsed = json.loads(content[start : end + 1])

    if not isinstance(parsed, dict):
        return {"raw_content": parsed}
    return parsed
