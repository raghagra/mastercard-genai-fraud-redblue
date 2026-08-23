from pathlib import Path

from fastapi import APIRouter
from pydantic import BaseModel, Field

from src.common.config import get_project_paths
from src.common.io import read_json
from src.generate.pipeline import generate_dataset


router = APIRouter(prefix="/generate", tags=["generate"])


class GenerateRequest(BaseModel):
    seed: int = 42
    per_attack_card: int = Field(default=1, ge=1, le=10)
    benign_count: int = Field(default=500, ge=0, le=100_000)


@router.post("")
def generate(request: GenerateRequest) -> dict[str, object]:
    dataset = generate_dataset(
        seed=request.seed,
        per_attack_card=request.per_attack_card,
        benign_count=request.benign_count,
    )
    summary_path = get_project_paths().generated_data_dir / "generation_summary.json"
    summary = read_json(summary_path) if Path(summary_path).exists() else {}
    return {
        "status": "generated",
        "summary": summary,
        "counts": {
            "transactions": len(dataset.transactions),
            "customers": len(dataset.customers),
            "merchants": len(dataset.merchants),
            "devices": len(dataset.devices),
            "attack_instances": len(dataset.attack_instances),
        },
    }

