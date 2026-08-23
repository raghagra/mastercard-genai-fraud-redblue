from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.common.config import get_project_paths
from src.common.io import read_json, write_json


VALID_DECISIONS = {"accepted", "rejected", "needs_changes"}


def list_mutation_candidates(iteration_id: str, iterations_dir: str | Path | None = None) -> list[dict[str, Any]]:
    path = _iteration_root(iteration_id, iterations_dir) / "mutation_candidates.json"
    if not path.exists():
        return []
    candidates = read_json(path)
    if not isinstance(candidates, list):
        raise ValueError(f"Mutation candidates must be a list: {path}")
    # Historic runs may contain malformed raw model output. It is retained in
    # the JSON artifact for auditability but excluded from review workflows.
    return [candidate for candidate in candidates if isinstance(candidate, dict) and candidate.get("mutation_id")]


def list_mutation_reviews(iteration_id: str, iterations_dir: str | Path | None = None) -> list[dict[str, Any]]:
    path = _iteration_root(iteration_id, iterations_dir) / "mutation_reviews.json"
    if not path.exists():
        return []
    reviews = read_json(path)
    if not isinstance(reviews, list):
        raise ValueError(f"Mutation reviews must be a list: {path}")
    return reviews


def review_mutation(
    iteration_id: str,
    mutation_id: str,
    decision: str,
    reviewer: str = "cli",
    notes: str = "",
    iterations_dir: str | Path | None = None,
) -> dict[str, Any]:
    if decision not in VALID_DECISIONS:
        raise ValueError(f"decision must be one of: {', '.join(sorted(VALID_DECISIONS))}")

    candidates = list_mutation_candidates(iteration_id, iterations_dir)
    if mutation_id not in {candidate["mutation_id"] for candidate in candidates}:
        raise ValueError(f"Mutation candidate not found: {mutation_id}")

    review = {
        "mutation_id": mutation_id,
        "decision": decision,
        "reviewer": reviewer,
        "notes": notes,
        "reviewed_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }
    reviews = [
        existing
        for existing in list_mutation_reviews(iteration_id, iterations_dir)
        if existing.get("mutation_id") != mutation_id
    ]
    reviews.append(review)
    root = _iteration_root(iteration_id, iterations_dir)
    write_json(root / "mutation_reviews.json", reviews)
    write_json(root / "accepted_mutations.json", accepted_mutations(iteration_id, iterations_dir))
    return review


def review_all_mutations(
    iteration_id: str,
    decision: str,
    reviewer: str = "cli",
    notes: str = "",
    iterations_dir: str | Path | None = None,
) -> list[dict[str, Any]]:
    reviews = []
    for candidate in list_mutation_candidates(iteration_id, iterations_dir):
        reviews.append(
            review_mutation(
                iteration_id=iteration_id,
                mutation_id=candidate["mutation_id"],
                decision=decision,
                reviewer=reviewer,
                notes=notes,
                iterations_dir=iterations_dir,
            )
        )
    return reviews


def accepted_mutations(iteration_id: str, iterations_dir: str | Path | None = None) -> list[dict[str, Any]]:
    candidates = {candidate["mutation_id"]: candidate for candidate in list_mutation_candidates(iteration_id, iterations_dir)}
    accepted = []
    for review in list_mutation_reviews(iteration_id, iterations_dir):
        if review.get("decision") != "accepted":
            continue
        candidate = candidates.get(review.get("mutation_id"))
        if candidate:
            accepted.append(
                {
                    **candidate,
                    "review": review,
                }
            )
    return accepted


def _iteration_root(iteration_id: str, iterations_dir: str | Path | None = None) -> Path:
    root = Path(iterations_dir) if iterations_dir is not None else get_project_paths().outputs_dir / "iterations"
    return root / iteration_id
