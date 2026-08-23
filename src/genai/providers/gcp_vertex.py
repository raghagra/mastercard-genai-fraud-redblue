from typing import Any
import os

from src.genai.base import GenAIRequest, GenAIResponse
from src.genai.providers.common import SYSTEM_PROMPT, parse_json_content, request_body


class GCPVertexProvider:
    def __init__(self, config: dict[str, Any], provider_name: str = "gcp_vertex_ai") -> None:
        self.provider_name = provider_name
        self.project_id = _config_value(config, "project_id", "project_id_env")
        self.location = _config_value(config, "location", "location_env") or "us-central1"
        self.model = str(config.get("model", ""))
        self.temperature = float(config.get("temperature", 0.2))
        self.max_tokens = int(config.get("max_tokens", 1200))

    def complete(self, request: GenAIRequest) -> GenAIResponse:
        try:
            from google import genai
            from google.genai import types
        except ImportError as exc:
            raise RuntimeError("GCP Vertex AI provider requires optional dependency 'google-genai'.") from exc

        if not self.project_id:
            raise RuntimeError("GCP project_id is required.")
        if not self.model:
            raise RuntimeError("GCP Vertex AI model ID is required.")

        client = genai.Client(vertexai=True, project=self.project_id, location=self.location)
        response = client.models.generate_content(
            model=self.model,
            contents=request_body(request.task, request.payload),
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                temperature=self.temperature,
                max_output_tokens=self.max_tokens,
            ),
        )
        text = getattr(response, "text", "") or ""
        return GenAIResponse(
            provider=self.provider_name,
            task=request.task,
            content=parse_json_content(text),
        )


def _config_value(config: dict[str, Any], value_key: str, env_key: str) -> str:
    if config.get(value_key):
        return str(config[value_key])
    if config.get(env_key):
        return os.getenv(str(config[env_key]), "")
    return ""
