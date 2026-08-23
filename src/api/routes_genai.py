from time import perf_counter
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.genai.base import GenAIRequest
from src.genai.costing import estimate_what_if_costs
from src.genai.gateway import GenAIGateway
from src.genai.session_config import SESSION_CONFIG
from src.genai.token_estimator import estimate_tokens_from_payload


router = APIRouter(prefix="/genai", tags=["genai"])


class SessionConfigRequest(BaseModel):
    config: dict[str, Any]


class TestConnectionRequest(BaseModel):
    task: str = "attack_mutation"
    payload: dict[str, Any] | None = None


class CostEstimateRequest(BaseModel):
    input_tokens: int
    output_tokens: int


@router.get("/health")
def genai_health() -> dict[str, object]:
    return {
        "status": "ok",
        "gateway": GenAIGateway().health(),
    }


@router.get("/providers")
def genai_providers() -> dict[str, object]:
    return {
        "providers": {
            "local_rules": {
                "label": "Local deterministic rules",
                "type": "local_rules",
                "fields": [],
                "secret_fields": [],
            },
            "local_lmstudio": {
                "label": "Local LM Studio",
                "type": "openai_compatible",
                "fields": ["base_url", "model", "timeout_seconds", "temperature", "max_tokens"],
                "secret_fields": ["api_key"],
            },
            "aws_bedrock": {
                "label": "AWS Bedrock",
                "type": "aws_bedrock",
                "fields": ["region", "model", "temperature", "max_tokens"],
                "secret_fields": [],
                "credential_note": "Uses boto3 credential resolution: env vars, AWS profile, SSO, role, or instance/task identity.",
            },
            "gcp_vertex_ai": {
                "label": "GCP Vertex AI",
                "type": "gcp_vertex_ai",
                "fields": ["project_id", "location", "model", "temperature", "max_tokens"],
                "secret_fields": [],
                "credential_note": "Uses Google Application Default Credentials.",
            },
            "azure_ai_foundry": {
                "label": "Azure AI Foundry",
                "type": "azure_ai_foundry",
                "fields": ["endpoint", "deployment", "api_version", "temperature", "max_tokens"],
                "secret_fields": ["api_key"],
            },
        },
        "tasks": [
            "attack_mutation",
            "attack_ideation",
            "scenario_narrative",
            "alert_explanation",
            "evaluation_summary",
            "defense_review",
        ],
    }


@router.get("/config/session")
def get_session_config() -> dict[str, object]:
    return {
        "active": SESSION_CONFIG.get_redacted() is not None,
        "config": SESSION_CONFIG.get_redacted(),
    }


@router.post("/config/session")
def set_session_config(request: SessionConfigRequest) -> dict[str, object]:
    config = SESSION_CONFIG.set(request.config)
    return {
        "status": "configured",
        "config": SESSION_CONFIG.get_redacted(),
        "gateway": GenAIGateway(config).health(),
    }


@router.delete("/config/session")
def clear_session_config() -> dict[str, object]:
    SESSION_CONFIG.clear()
    return {
        "status": "cleared",
    }


@router.post("/test-connection")
def test_connection(request: TestConnectionRequest) -> dict[str, object]:
    payload = request.payload or _default_test_payload()
    started_at = perf_counter()
    try:
        response = GenAIGateway().complete(GenAIRequest(task=request.task, payload=payload))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "status": "ok",
        "provider": response.provider,
        "task": response.task,
        "latency_ms": round((perf_counter() - started_at) * 1000, 2),
        "usage_estimate": {
            "input_tokens": estimate_tokens_from_payload({"task": request.task, "payload": payload}),
            "output_tokens": estimate_tokens_from_payload(response.content),
        },
        "fallback": response.content.get("gateway_fallback"),
        "content_keys": sorted(response.content.keys()),
        "content": response.content,
    }


@router.post("/cost/estimate")
def estimate_cost(request: CostEstimateRequest) -> dict[str, object]:
    return estimate_what_if_costs(request.input_tokens, request.output_tokens)


def _default_test_payload() -> dict[str, Any]:
    return {
        "attack_card": {
            "attack_id": "test_attack",
            "bucket": "credential_based_fraud",
            "subtype": "card_not_present",
            "variant_name": "Test variant",
            "generation_strategy": {
                "mode": "template_plus_sampling",
                "stealth_level_range": [0.4, 0.8],
                "volume_range": [2, 5],
                "noise_level": "medium",
            },
        },
        "weakness": {
            "group_key": "card_not_present",
            "reason": "connection_test",
        },
    }
