from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.portfolio.service import (
    PortfolioValidationError,
    create_dataset,
    delete_dataset,
    get_dataset,
    list_datasets,
    score_upcoming_transactions,
    template_csv,
)


router = APIRouter(prefix="/portfolio", tags=["portfolio"])


class PortfolioCreateRequest(BaseModel):
    dataset_name: str = Field(default="local_demo", max_length=100)
    historical_csv: str = Field(min_length=1)
    upcoming_csv: str = Field(min_length=1)


class PortfolioScoreRequest(BaseModel):
    model_iteration_id: str | None = None
    enable_genai_review: bool = False
    cloud_data_acknowledged: bool = False


@router.get("/template")
def portfolio_template() -> dict[str, str]:
    return {
        "historical_csv": template_csv(include_label=True),
        "upcoming_csv": template_csv(include_label=False),
        "notice": "Local demo only. Upload pseudonymized data; never include PAN, account numbers, or direct PII.",
    }


@router.post("/datasets")
def create_portfolio_dataset(request: PortfolioCreateRequest) -> dict[str, object]:
    try:
        manifest = create_dataset(request.historical_csv, request.upcoming_csv, request.dataset_name)
    except PortfolioValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"status": "created", "dataset": manifest}


@router.get("/datasets")
def portfolio_datasets() -> dict[str, object]:
    return {"datasets": list_datasets(), "storage_mode": "local_demo_only"}


@router.get("/datasets/{dataset_id}")
def portfolio_dataset(dataset_id: str) -> dict[str, object]:
    try:
        return get_dataset(dataset_id)
    except (FileNotFoundError, PortfolioValidationError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/datasets/{dataset_id}/score")
def score_portfolio_dataset(dataset_id: str, request: PortfolioScoreRequest) -> dict[str, object]:
    try:
        return score_upcoming_transactions(
            dataset_id,
            model_iteration_id=request.model_iteration_id,
            enable_genai_review=request.enable_genai_review,
            cloud_data_acknowledged=request.cloud_data_acknowledged,
        )
    except (FileNotFoundError, PortfolioValidationError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.delete("/datasets/{dataset_id}")
def remove_portfolio_dataset(dataset_id: str) -> dict[str, str]:
    try:
        delete_dataset(dataset_id)
    except (FileNotFoundError, PortfolioValidationError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"status": "deleted", "dataset_id": dataset_id}
