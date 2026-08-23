import json
from pathlib import Path

from src.genai.base import GenAIRequest
from src.genai.config import load_genai_config
from src.genai.gateway import GenAIGateway
from src.genai.costing import iteration_usage_summary, log_usage_event
from src.mutate.mutate_attack_card import propose_mutations


def test_genai_config_loads_example() -> None:
    config = load_genai_config()

    assert config.default_provider == "local_rules"
    assert "local_rules" in config.providers
    assert "local_lmstudio" in config.providers
    assert "aws_bedrock" in config.providers
    assert "gcp_vertex_ai" in config.providers
    assert "azure_ai_foundry" in config.providers


def test_lmstudio_session_key_overrides_environment(monkeypatch) -> None:
    from src.genai.providers.lmstudio import LMStudioProvider

    monkeypatch.setenv("TEST_LMSTUDIO_KEY", "environment-key")
    provider = LMStudioProvider(
        {
            "type": "openai_compatible",
            "api_key": "session-key",
            "api_key_env": "TEST_LMSTUDIO_KEY",
        }
    )

    assert provider.api_key == "session-key"


def test_iteration_usage_summary(tmp_path: Path) -> None:
    log_usage_event(
        "local_lmstudio",
        "attack_mutation",
        {"attack": "example"},
        {"mutation_id": "mut_001"},
        usage_dir=tmp_path,
        context={"iteration_id": "iteration_009"},
        latency_ms=123.4,
    )

    summary = iteration_usage_summary("iteration_009", usage_dir=tmp_path)
    assert summary["call_count"] == 1
    assert summary["input_tokens_estimated"] > 0
    assert summary["latency_ms_total"] == 123.4
    assert summary["cost_estimates"]


def test_invalid_model_mutation_uses_safe_fallback() -> None:
    class RefusingProvider:
        def complete(self, request):
            from src.genai.base import GenAIResponse
            return GenAIResponse(provider="test_model", task=request.task, content={"raw_content": "refusal"})

    candidates = propose_mutations(
        {"weak_groups": [{"subtype": "card_not_present", "bucket": "credential_based_fraud"}]},
        provider=RefusingProvider(),
        limit=1,
    )

    assert candidates[0]["provider"] == "local_rules"
    assert candidates[0]["mutation_id"]
    assert candidates[0]["gateway_fallback"]["reason"] == "model_output_failed_mutation_contract"


def test_structured_model_mutation_is_normalized_without_losing_provider_provenance() -> None:
    class PartialStructuredProvider:
        provider_name = "local_lmstudio"

        def complete(self, request):
            from src.genai.base import GenAIResponse

            return GenAIResponse(
                provider="local_lmstudio",
                task=request.task,
                content={
                    "proposed_variant_name": "Paced credential attempt variant",
                    "mutation_strategy": ["pace_attempts_across_time", "increase_benign_context_overlap"],
                    "rationale": "Use a slower, more varied synthetic campaign for defensive stress testing.",
                    "suggested_generation_strategy": {
                        "stealth_level_range": [0.6, 0.9],
                        "volume_range": [1, 2],
                        "noise_level": "high",
                        "time_window_multiplier": 2.0,
                    },
                },
            )

    candidates = propose_mutations(
        {"weak_groups": [{"subtype": "card_not_present", "bucket": "credential_based_fraud"}]},
        provider=PartialStructuredProvider(),
        limit=1,
    )

    assert candidates[0]["provider"] == "local_lmstudio"
    assert candidates[0]["source_attack_id"] == "cred_cnp_001"
    assert candidates[0]["parameter_deltas"]
    assert candidates[0]["model_contribution"]["normalized"] is True


def test_compact_model_mutation_intent_is_expanded_to_reviewable_candidate() -> None:
    class IntentProvider:
        provider_name = "local_lmstudio"

        def complete(self, request):
            from src.genai.base import GenAIResponse

            return GenAIResponse(
                provider="local_lmstudio",
                task=request.task,
                content={
                    "variant_name": "Low-and-slow payment pattern",
                    "rationale": "A paced synthetic pattern tests whether behavioral signals remain effective.",
                    "mutation_focus": ["increase_benign_overlap", "pace_attempts", "extend_campaign_window"],
                },
            )

    candidates = propose_mutations(
        {"weak_groups": [{"subtype": "card_not_present", "bucket": "credential_based_fraud"}]},
        provider=IntentProvider(),
        limit=1,
    )

    assert candidates[0]["provider"] == "local_lmstudio"
    assert candidates[0]["model_contribution"]["contract"] == "compact_mutation_intent"
    assert candidates[0]["suggested_generation_strategy"]["time_window_multiplier"] == 2.0


def test_gateway_uses_local_rules_for_attack_mutation() -> None:
    gateway = GenAIGateway()
    response = gateway.complete(
        GenAIRequest(
            task="attack_mutation",
            payload={
                "attack_card": {
                    "attack_id": "attack_001",
                    "bucket": "credential_based_fraud",
                    "subtype": "card_not_present",
                    "variant_name": "Base variant",
                    "generation_strategy": {
                        "mode": "template_plus_sampling",
                        "stealth_level_range": [0.3, 0.7],
                        "volume_range": [2, 4],
                        "noise_level": "medium",
                    },
                },
                "weakness": {
                    "group_key": "card_not_present",
                    "reason": "lowest_confidence_fraud_group",
                },
            },
        )
    )

    assert response.provider == "local_rules"
    assert response.content["source_attack_id"] == "attack_001"
    assert response.content["human_review_required"] is True


def test_gateway_falls_back_when_lmstudio_is_unavailable(tmp_path: Path) -> None:
    config_path = tmp_path / "genai.json"
    config_path.write_text(
        json.dumps(
            {
                "default_provider": "local_lmstudio",
                "fallback_provider": "local_rules",
                "task_routes": {"attack_mutation": "local_lmstudio"},
                "providers": {
                    "local_rules": {"type": "local_rules"},
                    "local_lmstudio": {
                        "type": "openai_compatible",
                        "base_url": "http://127.0.0.1:9/v1",
                        "model": "missing",
                        "timeout_seconds": 1,
                    },
                },
                "budget": {},
            }
        ),
        encoding="utf-8",
    )
    gateway = GenAIGateway(load_genai_config(config_path))
    response = gateway.complete(
        GenAIRequest(
            task="attack_mutation",
            payload={
                "attack_card": {
                    "attack_id": "attack_002",
                    "bucket": "post_transaction_abuse",
                    "subtype": "refund_fraud",
                    "variant_name": "Base variant",
                    "generation_strategy": {
                        "mode": "template_plus_sampling",
                        "stealth_level_range": [0.4, 0.8],
                        "volume_range": [2, 4],
                        "noise_level": "medium",
                    },
                },
                "weakness": {
                    "group_key": "refund_fraud",
                    "reason": "lowest_confidence_fraud_group",
                },
            },
        )
    )

    assert response.provider == "local_rules"
    assert response.content["source_attack_id"] == "attack_002"
    assert response.content["gateway_fallback"]["from_provider"] == "local_lmstudio"
