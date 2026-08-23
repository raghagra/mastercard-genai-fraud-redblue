import csv
import json
from pathlib import Path
from time import sleep

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from src.loop.compare_iterations import compare_iterations, get_iteration_summary, list_iterations
from src.loop.jobs import LOOP_JOBS
from src.loop.run_iteration import run_closed_loop_iteration
from src.genai.costing import iteration_usage_summary
from src.common.io import read_json
from src.experiments.mutation_impact import load_mutation_impact_experiment, run_mutation_impact_experiment
from src.genai.base import GenAIRequest
from src.genai.gateway import GenAIGateway
from src.mutate.review import (
    accepted_mutations,
    list_mutation_candidates,
    list_mutation_reviews,
    review_all_mutations,
    review_mutation,
)


router = APIRouter(prefix="/loop", tags=["loop"])


class RunLoopRequest(BaseModel):
    iteration_id: str | None = None
    seed: int = 42
    per_attack_card: int = Field(default=1, ge=1, le=10)
    benign_count: int = Field(default=500, ge=0, le=100_000)
    realism_profile: str = Field(default="overlap", pattern="^(baseline|overlap)$")
    review_source_iteration_id: str | None = None
    mutation_candidate_limit: int = Field(default=5, ge=1, le=10)
    async_run: bool = False


class ReviewMutationRequest(BaseModel):
    decision: str
    reviewer: str = "api"
    notes: str = ""


class RunMutationExperimentRequest(BaseModel):
    mutation_id: str
    seed: int = Field(default=314, ge=1)
    benign_count: int = Field(default=200, ge=20, le=10_000)
    per_attack_card: int = Field(default=4, ge=1, le=30)


@router.post("/run")
def run_loop(request: RunLoopRequest) -> dict[str, object]:
    run_args = {
        "iteration_id": request.iteration_id,
        "seed": request.seed,
        "per_attack_card": request.per_attack_card,
        "benign_count": request.benign_count,
        "realism_profile": request.realism_profile,
        "review_source_iteration_id": request.review_source_iteration_id,
        "mutation_candidate_limit": request.mutation_candidate_limit,
    }
    if request.async_run:
        return {"status": "started", "job": LOOP_JOBS.start(**run_args)}
    summary = run_closed_loop_iteration(
        **run_args,
    )
    return {
        "status": "completed",
        "summary": summary,
    }


@router.get("/iterations/{iteration_id}/transactions/{transaction_id}")
def iteration_transaction_detail(iteration_id: str, transaction_id: str) -> dict[str, object]:
    root = _iteration_path(iteration_id)
    transaction = _find_csv_row(root / "generated" / "transactions.csv", "transaction_id", transaction_id)
    if transaction is None:
        raise HTTPException(status_code=404, detail=f"Transaction not found: {transaction_id}")
    score = _find_csv_row(root / "scores" / "scores.csv", "transaction_id", transaction_id) or {}
    customer = _find_csv_row(root / "generated" / "customers.csv", "customer_id", transaction["customer_id"])
    merchant = _find_csv_row(root / "generated" / "merchants.csv", "merchant_id", transaction["merchant_id"])
    device = _find_csv_row(root / "generated" / "devices.csv", "device_id", transaction["device_id"])
    attack_instance = _find_csv_row(root / "generated" / "attack_instances.csv", "scenario_id", transaction["scenario_id"])
    return {
        "iteration_id": iteration_id,
        "transaction": transaction,
        "detection": {
            **score,
            "reason_codes": [item for item in score.get("reason_codes", "").split(";") if item],
        },
        "entities": {"customer": customer, "merchant": merchant, "device": device},
        "attack_instance": attack_instance,
        "generation_provenance": _generation_provenance(root, transaction),
        "decision_provenance": _decision_provenance(score),
    }


@router.get("/iterations/{iteration_id}/genai-usage")
def iteration_genai_usage(iteration_id: str) -> dict[str, object]:
    return iteration_usage_summary(iteration_id)


@router.get("/iterations/{iteration_id}/mutation-impact")
def iteration_mutation_impact(iteration_id: str) -> dict[str, object]:
    """Relate an iteration to the accepted mutations it explicitly consumed.

    The result intentionally reports an outcome comparison, not causal proof:
    each loop run is a new synthetic sample and may differ for reasons beyond a
    mutation. That distinction is important for a judge-facing demo.
    """
    try:
        candidate = get_iteration_summary(iteration_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    source_iteration_id = candidate.get("review_source_iteration_id")
    if not source_iteration_id:
        return {
            "iteration_id": iteration_id,
            "source_iteration_id": None,
            "accepted_mutations": [],
            "outcome": None,
            "disclosure": "This run did not consume accepted mutations from a prior iteration.",
        }
    try:
        source = get_iteration_summary(str(source_iteration_id))
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Mutation source iteration is unavailable: {exc}") from exc

    source_metrics = source.get("evaluation_overall", {})
    candidate_metrics = candidate.get("evaluation_overall", {})
    metrics = ("precision", "recall", "f1", "false_positive_rate")
    return {
        "iteration_id": iteration_id,
        "source_iteration_id": source_iteration_id,
        "accepted_mutations": [
            {
                "mutation_id": item.get("mutation_id"),
                "subtype": item.get("subtype"),
                "proposed_variant_name": item.get("proposed_variant_name"),
                "provider": item.get("provider"),
            }
            for item in accepted_mutations(str(source_iteration_id))
        ],
        "outcome": {
            "source_metrics": source_metrics,
            "candidate_metrics": candidate_metrics,
            "metric_deltas": {
                metric: round(_as_float(candidate_metrics.get(metric)) - _as_float(source_metrics.get(metric)), 6)
                for metric in metrics
            },
            "mutations_consumed": candidate.get("counts", {}).get("accepted_mutations_consumed", 0),
            "overlays_applied": candidate.get("counts", {}).get("mutation_overlays_applied", 0),
        },
        "disclosure": "Outcome comparison only: a new synthetic sample was generated, so this does not prove that a mutation alone caused the metric change.",
    }


@router.post("/iterations/{iteration_id}/mutation-experiments")
def run_mutation_experiment(iteration_id: str, request: RunMutationExperimentRequest) -> dict[str, object]:
    candidate = get_iteration_summary(iteration_id)
    source_iteration_id = candidate.get("review_source_iteration_id")
    if not source_iteration_id:
        raise HTTPException(status_code=400, detail="This iteration did not consume mutations from a source iteration.")
    mutation = next((item for item in accepted_mutations(str(source_iteration_id)) if item.get("mutation_id") == request.mutation_id), None)
    if mutation is None:
        raise HTTPException(status_code=404, detail="Accepted mutation not found in the source iteration.")
    try:
        return {"experiment": run_mutation_impact_experiment(iteration_id, str(source_iteration_id), mutation, request.seed, request.benign_count, request.per_attack_card)}
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/iterations/{iteration_id}/mutation-experiments/{mutation_id}/explain/stream")
def stream_mutation_explanation(iteration_id: str, mutation_id: str) -> StreamingResponse:
    try:
        experiment = load_mutation_impact_experiment(iteration_id, mutation_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    def events():
        yield _sse("status", {"message": "Preparing aggregate evidence for the configured GenAI provider…"})
        payload = {"experiment": {key: experiment[key] for key in ("mutation", "design", "baseline", "mutated", "metric_deltas", "disclosure")}}
        try:
            response = GenAIGateway().complete(GenAIRequest(task="experiment_explanation", payload=payload, context={"iteration_id": iteration_id}))
            text = str(response.content.get("summary") or response.content.get("raw_content") or "").strip()
            if not text:
                raise ValueError("The provider returned no explanation.")
            yield _sse("meta", {"provider": response.provider, "fallback": response.content.get("gateway_fallback")})
        except Exception as exc:
            text = experiment["deterministic_explanation"]
            yield _sse("meta", {"provider": "deterministic_fallback", "fallback": str(exc)})
        for word in text.split(" "):
            yield _sse("token", {"text": f"{word} "})
            sleep(0.006)
        yield _sse("done", {})

    return StreamingResponse(events(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})


@router.get("/jobs/{job_id}")
def loop_job(job_id: str) -> dict[str, object]:
    try:
        return LOOP_JOBS.get(job_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Loop job not found: {job_id}") from exc


@router.get("/iterations")
def iterations() -> dict[str, object]:
    return {
        "iterations": list_iterations(),
    }


@router.get("/iterations/{iteration_id}")
def iteration_detail(iteration_id: str) -> dict[str, object]:
    try:
        return get_iteration_summary(iteration_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/iterations/{iteration_id}/transactions")
def iteration_transactions(
    iteration_id: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    label: int | None = Query(default=None, ge=0, le=1),
    bucket: str | None = None,
    flagged: int | None = Query(default=None, ge=0, le=1),
    llm_reviewed: int | None = Query(default=None, ge=0, le=1),
    decision_engine: str | None = None,
    search: str | None = None,
    sort_by: str = "event_time",
    sort_direction: str = "desc",
) -> dict[str, object]:
    root = _iteration_path(iteration_id)
    transaction_path = root / "generated" / "transactions.csv"
    score_path = root / "scores" / "scores.csv"
    if not transaction_path.exists() or not score_path.exists():
        raise HTTPException(status_code=404, detail=f"Transaction artifacts not found for {iteration_id}")

    with score_path.open(encoding="utf-8", newline="") as file:
        scores = {row["transaction_id"]: row for row in csv.DictReader(file)}
    with transaction_path.open(encoding="utf-8", newline="") as file:
        records = [_transaction_view(row, scores.get(row["transaction_id"], {})) for row in csv.DictReader(file)]

    filtered = [
        record for record in records
        if (label is None or record["label"] == label)
        and (bucket is None or record["attack_bucket"] == bucket)
        and (flagged is None or record["prediction"] == flagged)
        and (llm_reviewed is None or record["llm_reviewed"] == llm_reviewed)
        and (decision_engine is None or record["decision_engine"] == decision_engine)
        and (search is None or _matches_search(record, search))
    ]
    allowed_sort_fields = {
        "transaction_id", "event_time", "amount", "channel", "rail", "merchant_category", "label",
        "attack_bucket", "fraud_score", "ml_fraud_score", "prediction", "llm_reviewed",
        "llm_semantic_risk_score", "decision_engine",
    }
    if sort_by not in allowed_sort_fields:
        raise HTTPException(status_code=400, detail=f"Unsupported sort field: {sort_by}")
    if sort_direction not in {"asc", "desc"}:
        raise HTTPException(status_code=400, detail="sort_direction must be asc or desc")
    filtered.sort(key=lambda record: _sort_value(record[sort_by]), reverse=sort_direction == "desc")
    start = (page - 1) * page_size
    return {
        "iteration_id": iteration_id,
        "page": page,
        "page_size": page_size,
        "total": len(filtered),
        "items": filtered[start : start + page_size],
        "filters": {
            "buckets": sorted({record["attack_bucket"] for record in records if record["attack_bucket"]}),
            "decision_engines": sorted({record["decision_engine"] for record in records if record["decision_engine"]}),
        },
    }


def _matches_search(record: dict[str, object], search: str) -> bool:
    query = search.strip().lower()
    if not query:
        return True
    searchable = [
        "transaction_id", "channel", "rail", "merchant_category", "currency",
        "attack_bucket", "attack_subtype", "decision_engine", "llm_provider",
    ]
    return any(query in str(record.get(field, "")).lower() for field in searchable)


def _as_float(value: object) -> float:
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0.0


def _sse(event: str, payload: dict[str, object]) -> str:
    return f"event: {event}\ndata: {json.dumps(payload)}\n\n"


def _iteration_path(iteration_id: str) -> Path:
    from src.common.config import get_project_paths

    return get_project_paths().outputs_dir / "iterations" / iteration_id


def _transaction_view(transaction: dict[str, str], score: dict[str, str]) -> dict[str, object]:
    return {
        "transaction_id": transaction["transaction_id"],
        "event_time": transaction["event_time"],
        "amount": float(transaction["amount"]),
        "currency": transaction["currency"],
        "channel": transaction["channel"],
        "rail": transaction["rail"],
        "merchant_category": transaction["merchant_category"],
        "label": int(transaction["label"]),
        "attack_bucket": transaction["attack_bucket"],
        "attack_subtype": transaction["attack_subtype"],
        "fraud_score": float(score.get("fraud_score", 0)),
        "ml_fraud_score": float(score.get("ml_fraud_score", score.get("fraud_score", 0))),
        "prediction": int(score.get("prediction", 0)),
        "llm_reviewed": int(score.get("llm_reviewed", 0)),
        "llm_provider": score.get("llm_provider", ""),
        "llm_semantic_risk_score": _to_optional_float(score.get("llm_semantic_risk_score", "")),
        "decision_engine": score.get("decision_engine", "ml_only"),
        "reason_codes": [item for item in score.get("reason_codes", "").split(";") if item],
    }


def _to_optional_float(value: str) -> float | None:
    try:
        return float(value) if value != "" else None
    except (TypeError, ValueError):
        return None


def _sort_value(value: object) -> tuple[int, object]:
    if value is None or value == "":
        return (1, "")
    return (0, value)


def _find_csv_row(path: Path, key: str, value: str) -> dict[str, str] | None:
    if not path.exists() or not value:
        return None
    with path.open(encoding="utf-8", newline="") as file:
        for row in csv.DictReader(file):
            if row.get(key) == value:
                return row
    return None


def _generation_provenance(root: Path, transaction: dict[str, str]) -> dict[str, object]:
    attack_id = transaction.get("attack_id", "")
    if not attack_id:
        return {"generation_type": "benign_baseline", "source": "deterministic_benign_generator"}
    if "__" not in attack_id:
        return {
            "generation_type": "base_attack_card",
            "source_attack_id": attack_id,
            "source": "deterministic_attack_generator",
        }

    source_attack_id, mutation_id = attack_id.rsplit("__", 1)
    summary_path = root / "loop_summary.json"
    summary = read_json(summary_path) if summary_path.exists() else {}
    review_source = summary.get("review_source_iteration_id") if isinstance(summary, dict) else None
    mutation: dict[str, object] = {}
    if review_source:
        source_path = _iteration_path(str(review_source)) / "mutation_candidates.json"
        if source_path.exists():
            candidates = read_json(source_path)
            if isinstance(candidates, list):
                mutation = next(
                    (item for item in candidates if isinstance(item, dict) and item.get("mutation_id") == mutation_id),
                    {},
                )
    return {
        "generation_type": "accepted_runtime_mutation",
        "source_attack_id": source_attack_id,
        "mutation_id": mutation_id,
        "mutation_provider": mutation.get("provider", "unknown"),
        "mutation_fallback": mutation.get("gateway_fallback"),
        "mutation_variant": mutation.get("proposed_variant_name", ""),
    }


def _decision_provenance(score: dict[str, str]) -> dict[str, object]:
    return {
        "primary_engine": "numpy_logistic_regression",
        "ml_fraud_score": score.get("ml_fraud_score", score.get("fraud_score", "")),
        "ml_prediction": score.get("ml_prediction", score.get("prediction", "")),
        "ml_reason_codes": [item for item in score.get("reason_codes", "").split(";") if item],
        "llm_reviewed": score.get("llm_reviewed", "0") == "1",
        "llm_provider": score.get("llm_provider", ""),
        "llm_semantic_risk_score": score.get("llm_semantic_risk_score", ""),
        "llm_novelty_score": score.get("llm_novelty_score", ""),
        "llm_recommendation": score.get("llm_recommendation", ""),
        "llm_rationale": score.get("llm_rationale", ""),
        "llm_risk_indicators": [item for item in score.get("llm_risk_indicators", "").split(";") if item],
        "llm_fallback": score.get("llm_fallback", ""),
        "final_engine": score.get("decision_engine", "ml_only"),
        "final_fraud_score": score.get("fraud_score", ""),
        "final_prediction": score.get("prediction", ""),
    }


@router.get("/compare")
def compare_loop_iterations(baseline: str, candidate: str) -> dict[str, object]:
    try:
        return compare_iterations(baseline, candidate)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/iterations/{iteration_id}/mutations")
def iteration_mutations(iteration_id: str) -> dict[str, object]:
    return {
        "iteration_id": iteration_id,
        "candidates": list_mutation_candidates(iteration_id),
        "reviews": list_mutation_reviews(iteration_id),
        "accepted": accepted_mutations(iteration_id),
    }


@router.post("/iterations/{iteration_id}/mutations/{mutation_id}/review")
def review_iteration_mutation(
    iteration_id: str,
    mutation_id: str,
    request: ReviewMutationRequest,
) -> dict[str, object]:
    try:
        review = review_mutation(
            iteration_id=iteration_id,
            mutation_id=mutation_id,
            decision=request.decision,
            reviewer=request.reviewer,
            notes=request.notes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "status": "reviewed",
        "review": review,
        "accepted": accepted_mutations(iteration_id),
    }


@router.post("/iterations/{iteration_id}/mutations/review-all")
def review_all_iteration_mutations(
    iteration_id: str,
    request: ReviewMutationRequest,
) -> dict[str, object]:
    try:
        reviews = review_all_mutations(
            iteration_id=iteration_id,
            decision=request.decision,
            reviewer=request.reviewer,
            notes=request.notes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "status": "reviewed",
        "review_count": len(reviews),
        "reviews": reviews,
        "accepted": accepted_mutations(iteration_id),
    }
