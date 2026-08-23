from pathlib import Path
from time import perf_counter
from typing import Any

from src.genai.costing import log_usage_event
from src.genai.base import GenAIProvider, GenAIRequest, GenAIResponse
from src.genai.config import GenAIConfig, load_genai_config
from src.genai.local_rules import LocalRulesProvider
from src.genai.providers.aws_bedrock import AWSBedrockProvider
from src.genai.providers.azure_ai import AzureAIFoundryProvider
from src.genai.providers.gcp_vertex import GCPVertexProvider
from src.genai.providers.lmstudio import LMStudioProvider
from src.genai.session_config import SESSION_CONFIG


class GenAIGateway:
    def __init__(self, config: GenAIConfig | None = None) -> None:
        self.config = config or SESSION_CONFIG.get() or load_genai_config()
        self.providers = self._build_providers(self.config.providers)
        if "local_rules" not in self.providers:
            self.providers["local_rules"] = LocalRulesProvider()

    def complete(self, request: GenAIRequest) -> GenAIResponse:
        provider_name = self.config.task_routes.get(request.task, self.config.default_provider)
        started_at = perf_counter()
        try:
            provider = self._provider(provider_name)
            response = provider.complete(request)
        except Exception as exc:
            fallback_name = self.config.fallback_provider
            if fallback_name == provider_name:
                raise
            fallback = self._provider(fallback_name)
            response = fallback.complete(request)
            response = GenAIResponse(
                provider=response.provider,
                task=response.task,
                content={
                    **response.content,
                    "gateway_fallback": {
                        "from_provider": provider_name,
                        "to_provider": fallback_name,
                        "reason": str(exc),
                    },
                },
            )
        log_usage_event(
            response.provider,
            request.task,
            request.payload,
            response.content,
            context=request.context,
            latency_ms=round((perf_counter() - started_at) * 1000, 2),
        )
        return response

    def health(self) -> dict[str, Any]:
        return {
            "default_provider": self.config.default_provider,
            "fallback_provider": self.config.fallback_provider,
            "task_routes": self.config.task_routes,
            "providers": {
                name: {
                    "available": name in self.providers,
                    "type": config.get("type", "unknown"),
                    "enabled": config.get("enabled", True),
                }
                for name, config in self.config.providers.items()
            },
            "budget": self.config.budget,
        }

    def _provider(self, provider_name: str) -> GenAIProvider:
        provider = self.providers.get(provider_name)
        if provider is None:
            raise RuntimeError(f"GenAI provider not configured: {provider_name}")
        return provider

    def _build_providers(self, configs: dict[str, dict[str, Any]]) -> dict[str, GenAIProvider]:
        providers: dict[str, GenAIProvider] = {}
        for name, provider_config in configs.items():
            provider_type = provider_config.get("type")
            if provider_type == "local_rules":
                providers[name] = LocalRulesProvider()
            elif provider_type == "openai_compatible":
                providers[name] = LMStudioProvider(provider_config, provider_name=name)
            elif provider_type == "aws_bedrock":
                providers[name] = AWSBedrockProvider(provider_config, provider_name=name)
            elif provider_type == "gcp_vertex_ai":
                providers[name] = GCPVertexProvider(provider_config, provider_name=name)
            elif provider_type == "azure_ai_foundry":
                providers[name] = AzureAIFoundryProvider(provider_config, provider_name=name)
        return providers


def gateway_from_config_path(path: str | Path | None = None) -> GenAIGateway:
    return GenAIGateway(load_genai_config(path))
