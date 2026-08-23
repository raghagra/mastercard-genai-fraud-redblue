#!/usr/bin/env python3
"""Launch a reproducible, judge-friendly SentinelLoop demonstration.

The default run prepares two deterministic local-only iterations, then starts
the FastAPI service and the React console. No model server, cloud credential,
or payment data is required. Stop both services with Ctrl+C.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parents[1]
FRONTEND_DIR = ROOT / "frontend"
REQUIRED_PYTHON_PACKAGES = ("fastapi", "uvicorn", "numpy", "pandas")
LOCAL_RULES_CONFIG: dict[str, Any] = {
    "default_provider": "local_rules",
    "fallback_provider": "local_rules",
    "task_routes": {
        "attack_mutation": "local_rules",
        "attack_ideation": "local_rules",
        "alert_explanation": "local_rules",
        "evaluation_summary": "local_rules",
        "defense_review": "local_rules",
        "experiment_explanation": "local_rules",
    },
    "providers": {"local_rules": {"type": "local_rules"}},
    "budget": {"max_calls_per_run": 500, "max_tokens_per_call": 1200, "dry_run": False},
}

# `python scripts/judge_demo.py` places scripts/ first on sys.path, not the
# repository root. Add the root explicitly so the application package imports
# identically on macOS, Linux, and Windows.
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare and launch the SentinelLoop judge demo.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--prepare-only", action="store_true", help="Prepare the two-iteration fixture, then exit.")
    parser.add_argument("--skip-prepare", action="store_true", help="Start services without creating new demo iterations.")
    parser.add_argument(
        "--provider",
        choices=("local_rules", "current"),
        default="local_rules",
        help="Use deterministic local rules, or the repository's current GenAI provider configuration.",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Host for both local services.")
    parser.add_argument("--api-port", type=int, default=8000, help="FastAPI port.")
    parser.add_argument("--ui-port", type=int, default=5173, help="Vite port.")
    parser.add_argument("--benign-records", type=int, default=150, help="Benign records in each prepared iteration.")
    parser.add_argument("--verify", action="store_true", help="Run backend tests and frontend production build, then exit.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.prepare_only and args.skip_prepare:
        print("--prepare-only and --skip-prepare cannot be used together.", file=sys.stderr)
        return 2
    if args.benign_records < 50:
        print("--benign-records must be at least 50.", file=sys.stderr)
        return 2

    _check_prerequisites()
    if args.verify:
        return _verify_project()

    with tempfile.TemporaryDirectory(prefix="sentinelloop-judge-") as temporary_directory:
        environment = os.environ.copy()
        original_config_path = os.environ.get("GENAI_CONFIG_PATH")
        if args.provider == "local_rules":
            config_path = Path(temporary_directory) / "local_rules.json"
            config_path.write_text(json.dumps(LOCAL_RULES_CONFIG, indent=2), encoding="utf-8")
            environment["GENAI_CONFIG_PATH"] = str(config_path)
            # Fixture preparation happens in this process; the API receives the
            # same setting through its child-process environment below.
            os.environ["GENAI_CONFIG_PATH"] = str(config_path)
            print("GenAI mode: deterministic local rules (no model server or cloud calls).")
        else:
            print("GenAI mode: current repository configuration. Confirm your selected provider is available.")
        try:
            # Fail before generating artifacts when the requested demo cannot
            # start because the user already has either service running.
            if not args.prepare_only:
                _ensure_port_available(args.host, args.api_port, "API")
                _ensure_port_available(args.host, args.ui_port, "frontend")
            if not args.skip_prepare:
                source_id, candidate_id = _prepare_closed_loop_fixture(args.benign_records)
                print(f"Prepared fixture: {source_id} → {candidate_id}")
            if args.prepare_only:
                return 0

            return _launch_services(args, environment)
        finally:
            if args.provider == "local_rules":
                if original_config_path is None:
                    os.environ.pop("GENAI_CONFIG_PATH", None)
                else:
                    os.environ["GENAI_CONFIG_PATH"] = original_config_path


def _check_prerequisites() -> None:
    missing_packages = [package for package in REQUIRED_PYTHON_PACKAGES if importlib.util.find_spec(package) is None]
    if missing_packages:
        joined = ", ".join(missing_packages)
        raise SystemExit(
            f"Missing Python packages: {joined}. Run:\n  {sys.executable} -m pip install -r requirements.txt"
        )
    if shutil.which(_npm_command()) is None:
        raise SystemExit("Node.js/npm was not found. Install Node.js 20+ and retry.")
    if not (FRONTEND_DIR / "node_modules").exists():
        raise SystemExit("Frontend packages are missing. Run:\n  cd frontend && npm install")


def _prepare_closed_loop_fixture(benign_records: int) -> tuple[str, str]:
    """Create evidence for a full loop without requiring a live LLM endpoint."""
    from src.knowledge.validate_attack_cards import validate_attack_catalog
    from src.loop.run_iteration import run_closed_loop_iteration
    from src.mutate.review import review_all_mutations

    validation = validate_attack_catalog()
    if not validation.valid:
        raise SystemExit("Attack catalog validation failed:\n- " + "\n- ".join(validation.errors))
    print(f"Validated {validation.checked_count} attack cards.")

    print("Preparing source iteration: generate → train → detect → analyze gaps …")
    source = run_closed_loop_iteration(
        seed=2026,
        per_attack_card=1,
        benign_count=benign_records,
        mutation_candidate_limit=5,
    )
    source_id = source["iteration_id"]
    review_all_mutations(
        source_id,
        decision="accepted",
        reviewer="judge_demo_fixture",
        notes="Deterministic demo fixture. Review these proposals in the console before operational use.",
    )

    print("Preparing candidate iteration with accepted mutations consumed …")
    candidate = run_closed_loop_iteration(
        seed=2026,
        per_attack_card=1,
        benign_count=benign_records,
        review_source_iteration_id=source_id,
        mutation_candidate_limit=5,
    )
    return source_id, candidate["iteration_id"]


def _verify_project() -> int:
    print("Running backend tests …")
    backend_result = subprocess.run([sys.executable, "-B", "-m", "pytest"], cwd=ROOT, check=False)
    if backend_result.returncode:
        return backend_result.returncode
    print("Building frontend …")
    frontend_result = subprocess.run([_npm_command(), "run", "build"], cwd=FRONTEND_DIR, check=False)
    return frontend_result.returncode


def _ensure_port_available(host: str, port: int, service: str) -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as connection:
        connection.settimeout(0.2)
        if connection.connect_ex((host, port)) == 0:
            raise SystemExit(f"{service} port {port} is already in use on {host}. Stop that service or choose another port.")


def _launch_services(args: argparse.Namespace, environment: dict[str, str]) -> int:
    api_command = [
        sys.executable,
        "-B",
        "-m",
        "src.cli.run_api",
        "--host",
        args.host,
        "--port",
        str(args.api_port),
    ]
    frontend_command = [
        _npm_command(),
        "run",
        "dev",
        "--",
        "--host",
        args.host,
        "--port",
        str(args.ui_port),
    ]
    frontend_environment = dict(environment)
    # Keep the browser client pointed at this launcher's API when custom ports
    # are used, instead of relying on the Vite default of port 8000.
    frontend_environment["VITE_API_URL"] = f"http://{args.host}:{args.api_port}"
    api_process = subprocess.Popen(api_command, cwd=ROOT, env=environment)
    frontend_process: subprocess.Popen[bytes] | None = None
    try:
        _wait_for_api(args.host, args.api_port)
        frontend_process = subprocess.Popen(frontend_command, cwd=FRONTEND_DIR, env=frontend_environment)
        _print_walkthrough(args)
        while True:
            if api_process.poll() is not None:
                return api_process.returncode or 1
            if frontend_process.poll() is not None:
                return frontend_process.returncode or 1
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nStopping SentinelLoop services …")
        return 0
    finally:
        _stop_process(frontend_process)
        _stop_process(api_process)


def _wait_for_api(host: str, port: int, timeout_seconds: int = 30) -> None:
    deadline = time.monotonic() + timeout_seconds
    url = f"http://{host}:{port}/docs"
    while time.monotonic() < deadline:
        try:
            with urlopen(url, timeout=1) as response:
                if 200 <= response.status < 500:
                    return
        except (URLError, TimeoutError):
            time.sleep(0.5)
    raise RuntimeError(f"API did not become available within {timeout_seconds} seconds: {url}")


def _print_walkthrough(args: argparse.Namespace) -> None:
    ui_url = f"http://{args.host}:{args.ui_port}"
    api_url = f"http://{args.host}:{args.api_port}/docs"
    print("\n" + "=" * 72)
    print("SentinelLoop judge demo is ready")
    print(f"Web console: {ui_url}")
    print(f"API docs:    {api_url}")
    print("\nSuggested 3-minute walkthrough:")
    print("  1. Mission control — see the five fraud families and latest defense signal.")
    print("  2. Closed loop — inspect the prepared source/candidate iterations and evidence.")
    print("  3. Human mutation review — see why each gap requires review and its bounded change.")
    print("  4. Synthetic payment explorer — filter decision evidence at transaction level.")
    print("  5. Portfolio onboarding — upload only pseudonymized demo data using the templates.")
    print("\nPress Ctrl+C here to stop both services.")
    print("=" * 72 + "\n")


def _stop_process(process: subprocess.Popen[bytes] | None) -> None:
    if process is None or process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()


def _npm_command() -> str:
    return "npm.cmd" if os.name == "nt" else "npm"


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as error:
        print(f"Judge demo failed: {error}", file=sys.stderr)
        raise SystemExit(1) from error
