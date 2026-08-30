from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.experiments.adversarial_evaluation import (
    evaluation_lab_options,
    list_adversarial_evaluation_campaigns,
    load_adversarial_evaluation_campaign,
    run_adversarial_evaluation_campaign,
)


router = APIRouter(prefix="/evaluation-lab", tags=["evaluation-lab"])


class RunEvaluationCampaignRequest(BaseModel):
    source_iteration_id: str
    campaign_id: str | None = Field(default=None, pattern=r"^[a-zA-Z0-9_-]+$")
    buckets: list[str] | None = None
    difficulty_profiles: list[str] | None = None
    seeds: list[int] | None = None
    scenarios_per_card: int = Field(default=1, ge=1, le=10)
    benign_count: int = Field(default=100, ge=20, le=10_000)
    realism_profile: str = Field(default="overlap", pattern="^(baseline|overlap)$")


@router.get("/options")
def options() -> dict[str, Any]:
    return evaluation_lab_options()


@router.post("/campaigns")
def run_campaign(request: RunEvaluationCampaignRequest) -> dict[str, object]:
    try:
        campaign = run_adversarial_evaluation_campaign(
            source_iteration_id=request.source_iteration_id,
            campaign_id=request.campaign_id,
            buckets=request.buckets,
            difficulty_profiles=request.difficulty_profiles,
            seeds=request.seeds,
            scenarios_per_card=request.scenarios_per_card,
            benign_count=request.benign_count,
            realism_profile=request.realism_profile,
        )
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"status": "completed", "campaign": campaign}


@router.get("/campaigns")
def campaigns() -> dict[str, object]:
    return {"campaigns": list_adversarial_evaluation_campaigns()}


@router.get("/campaigns/{campaign_id}")
def campaign_detail(campaign_id: str) -> dict[str, object]:
    try:
        return load_adversarial_evaluation_campaign(campaign_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
