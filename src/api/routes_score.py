from fastapi import APIRouter

from src.detect.score import score_feature_rows
from src.detect.train import train_baseline_detector
from src.evaluate.reports import build_evaluation_report
from src.features.build_features import build_feature_dataset, feature_columns


router = APIRouter(tags=["detect"])


@router.post("/features/build")
def build_features() -> dict[str, object]:
    rows = build_feature_dataset()
    return {
        "status": "features_built",
        "rows": len(rows),
        "feature_columns": len(feature_columns(rows)),
    }


@router.post("/train")
def train_detector(seed: int = 42) -> dict[str, object]:
    metrics = train_baseline_detector(seed=seed)
    return {
        "status": "trained",
        "metrics": metrics,
    }


@router.post("/score")
def score_detector() -> dict[str, object]:
    rows = score_feature_rows()
    flagged = sum(1 for row in rows if int(row["prediction"]) == 1)
    return {
        "status": "scored",
        "rows": len(rows),
        "flagged": flagged,
        "llm_reviewed": sum(1 for row in rows if int(row.get("llm_reviewed", 0)) == 1),
        "sample": rows[:5],
    }


@router.get("/metrics")
def metrics() -> dict[str, object]:
    report = build_evaluation_report()
    return {
        "status": "evaluated",
        "report": report,
    }
