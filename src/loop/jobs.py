"""In-memory local job manager for closed-loop iteration progress."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from threading import Lock
from typing import Any
from uuid import uuid4

from src.loop.run_iteration import run_closed_loop_iteration


class LoopJobStore:
    def __init__(self) -> None:
        self._lock = Lock()
        self._jobs: dict[str, dict[str, Any]] = {}
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="fraud-loop")

    def start(self, **kwargs: Any) -> dict[str, Any]:
        job_id = f"loop_{uuid4().hex[:12]}"
        job = {
            "job_id": job_id,
            "status": "queued",
            "stage": "queued",
            "created_at": _timestamp(),
            "started_at": None,
            "completed_at": None,
            "iteration_id": kwargs.get("iteration_id"),
            "summary": None,
            "error": None,
        }
        with self._lock:
            self._jobs[job_id] = job
        self._executor.submit(self._run, job_id, kwargs)
        return self.get(job_id)

    def get(self, job_id: str) -> dict[str, Any]:
        with self._lock:
            if job_id not in self._jobs:
                raise KeyError(job_id)
            return dict(self._jobs[job_id])

    def _update(self, job_id: str, **updates: Any) -> None:
        with self._lock:
            self._jobs[job_id].update(updates)

    def _run(self, job_id: str, kwargs: dict[str, Any]) -> None:
        self._update(job_id, status="running", stage="preparing", started_at=_timestamp())
        try:
            summary = run_closed_loop_iteration(
                **kwargs,
                progress_callback=lambda stage: self._update(job_id, stage=stage),
            )
            self._update(
                job_id,
                status="completed",
                stage="completed",
                iteration_id=summary["iteration_id"],
                summary=summary,
                completed_at=_timestamp(),
            )
        except Exception as exc:
            self._update(job_id, status="failed", stage="failed", error=str(exc), completed_at=_timestamp())


def _timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


LOOP_JOBS = LoopJobStore()
