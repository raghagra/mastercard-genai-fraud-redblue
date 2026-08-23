from fastapi.testclient import TestClient
from pathlib import Path

from src.api.main import app


def test_api_health_and_catalog_routes() -> None:
    client = TestClient(app)

    health = client.get("/health")
    catalog = client.get("/attack-catalog")
    validation = client.get("/attack-catalog/validate")
    card = client.get("/attack-catalog/cred_cnp_001")
    genai = client.get("/genai/health")
    providers = client.get("/genai/providers")
    cost = client.post("/genai/cost/estimate", json={"input_tokens": 1000, "output_tokens": 500})

    assert health.status_code == 200
    assert health.json()["status"] == "ok"
    assert catalog.status_code == 200
    assert catalog.json()["summary"]["total_cards"] == 25
    assert validation.status_code == 200
    assert validation.json()["valid"] is True
    assert card.status_code == 200
    assert card.json()["attack_id"] == "cred_cnp_001"
    assert genai.status_code == 200
    assert genai.json()["gateway"]["default_provider"] == "local_rules"
    assert providers.status_code == 200
    assert "aws_bedrock" in providers.json()["providers"]
    assert "gcp_vertex_ai" in providers.json()["providers"]
    assert "azure_ai_foundry" in providers.json()["providers"]
    assert cost.status_code == 200
    assert cost.json()["estimates"]


def test_api_allows_vite_alternate_local_port() -> None:
    client = TestClient(app)
    response = client.options(
        "/genai/providers",
        headers={
            "Origin": "http://127.0.0.1:5174",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:5174"


def test_api_genai_session_config() -> None:
    client = TestClient(app)
    payload = {
        "config": {
            "default_provider": "local_rules",
            "fallback_provider": "local_rules",
            "task_routes": {"attack_mutation": "local_rules"},
            "providers": {
                "local_rules": {"type": "local_rules"},
                "azure_ai_foundry": {
                    "type": "azure_ai_foundry",
                    "endpoint": "https://example.openai.azure.com",
                    "api_key": "secret-value",
                    "deployment": "demo",
                },
            },
            "budget": {"max_calls_per_run": 2},
        }
    }

    set_response = client.post("/genai/config/session", json=payload)
    get_response = client.get("/genai/config/session")
    test_response = client.post("/genai/test-connection", json={"task": "attack_mutation"})
    clear_response = client.delete("/genai/config/session")

    assert set_response.status_code == 200
    assert get_response.status_code == 200
    assert get_response.json()["config"]["providers"]["azure_ai_foundry"]["api_key"] == "***redacted***"
    assert test_response.status_code == 200
    assert test_response.json()["provider"] == "local_rules"
    assert test_response.json()["latency_ms"] >= 0
    assert test_response.json()["usage_estimate"]["input_tokens"] > 0
    assert clear_response.status_code == 200


def test_api_loop_routes(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("src.loop.run_iteration.get_project_paths", lambda: _paths(tmp_path))
    monkeypatch.setattr("src.loop.compare_iterations.get_project_paths", lambda: _paths(tmp_path))
    monkeypatch.setattr("src.mutate.review.get_project_paths", lambda: _paths(tmp_path))
    client = TestClient(app)

    run = client.post(
        "/loop/run",
        json={
            "iteration_id": "iteration_api_test",
            "seed": 21,
            "benign_count": 15,
            "per_attack_card": 1,
        },
    )
    iterations = client.get("/loop/iterations")
    detail = client.get("/loop/iterations/iteration_api_test")
    comparison = client.get(
        "/loop/compare",
        params={
            "baseline": "iteration_api_test",
            "candidate": "iteration_api_test",
        },
    )
    mutations = client.get("/loop/iterations/iteration_api_test/mutations")
    review_all = client.post(
        "/loop/iterations/iteration_api_test/mutations/review-all",
        json={
            "decision": "accepted",
            "reviewer": "pytest",
            "notes": "accept all",
        },
    )

    assert run.status_code == 200
    assert run.json()["status"] == "completed"
    assert iterations.status_code == 200
    assert detail.status_code == 200
    assert detail.json()["iteration_id"] == "iteration_api_test"
    assert comparison.status_code == 200
    assert comparison.json()["metric_deltas"]["f1"] == 0.0
    assert mutations.status_code == 200
    assert len(mutations.json()["candidates"]) == 5
    assert review_all.status_code == 200
    assert review_all.json()["review_count"] == 5

    candidate = client.post(
        "/loop/run",
        json={
            "iteration_id": "iteration_api_candidate",
            "seed": 22,
            "benign_count": 15,
            "per_attack_card": 1,
            "review_source_iteration_id": "iteration_api_test",
        },
    )
    impact = client.get("/loop/iterations/iteration_api_candidate/mutation-impact")

    assert candidate.status_code == 200
    assert impact.status_code == 200
    assert impact.json()["source_iteration_id"] == "iteration_api_test"
    assert impact.json()["outcome"]["mutations_consumed"] == 5


def test_api_starts_async_loop_job(monkeypatch) -> None:
    monkeypatch.setattr(
        "src.api.routes_loop.LOOP_JOBS.start",
        lambda **kwargs: {"job_id": "loop_test", "status": "queued", "stage": "queued", "iteration_id": kwargs["iteration_id"]},
    )
    client = TestClient(app)
    response = client.post(
        "/loop/run",
        json={"async_run": True, "iteration_id": "iteration_async_test", "benign_count": 1},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "started"
    assert response.json()["job"]["status"] in {"queued", "running"}


def test_iteration_transaction_explorer_api() -> None:
    client = TestClient(app)
    response = client.get(
        "/loop/iterations/iteration_003/transactions",
        params={"page": 1, "page_size": 3, "label": 1, "search": "credential", "sort_by": "amount", "sort_direction": "asc"},
    )

    assert response.status_code == 200
    assert response.json()["total"] > 0
    assert len(response.json()["items"]) == 3
    assert response.json()["items"][0]["label"] == 1
    assert "credential" in response.json()["items"][0]["attack_bucket"]
    assert response.json()["items"][0]["amount"] <= response.json()["items"][1]["amount"]

    transaction_id = response.json()["items"][0]["transaction_id"]
    detail = client.get(f"/loop/iterations/iteration_003/transactions/{transaction_id}")
    assert detail.status_code == 200
    assert detail.json()["transaction"]["transaction_id"] == transaction_id
    assert "reason_codes" in detail.json()["detection"]
    assert detail.json()["decision_provenance"]["primary_engine"] == "numpy_logistic_regression"
    assert "generation_type" in detail.json()["generation_provenance"]


def _paths(tmp_path: Path):
    from src.common.config import ProjectPaths, get_project_paths

    real_paths = get_project_paths()
    return ProjectPaths(
        root=real_paths.root,
        schemas_dir=real_paths.schemas_dir,
        attack_cards_dir=real_paths.attack_cards_dir,
        generated_data_dir=tmp_path / "data" / "generated",
        processed_data_dir=tmp_path / "data" / "processed",
        outputs_dir=tmp_path / "outputs",
    )
