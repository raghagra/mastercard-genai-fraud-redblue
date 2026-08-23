from typing import Any
import os

from src.genai.base import GenAIRequest, GenAIResponse
from src.genai.providers.common import SYSTEM_PROMPT, parse_json_content, request_body


class AWSBedrockProvider:
    def __init__(self, config: dict[str, Any], provider_name: str = "aws_bedrock") -> None:
        self.provider_name = provider_name
        self.region = _config_value(config, "region", "region_env")
        self.model = str(config.get("model", ""))
        self.temperature = float(config.get("temperature", 0.2))
        self.max_tokens = int(config.get("max_tokens", 1200))

    def complete(self, request: GenAIRequest) -> GenAIResponse:
        try:
            import boto3
        except ImportError as exc:
            raise RuntimeError("AWS Bedrock provider requires optional dependency 'boto3'.") from exc

        if not self.model:
            raise RuntimeError("AWS Bedrock model ID is required.")

        client_kwargs = {}
        if self.region:
            client_kwargs["region_name"] = self.region
        client = boto3.client("bedrock-runtime", **client_kwargs)
        response = client.converse(
            modelId=self.model,
            system=[{"text": SYSTEM_PROMPT}],
            messages=[
                {
                    "role": "user",
                    "content": [{"text": request_body(request.task, request.payload)}],
                }
            ],
            inferenceConfig={
                "temperature": self.temperature,
                "maxTokens": self.max_tokens,
            },
        )
        content_items = response["output"]["message"]["content"]
        text = "".join(item.get("text", "") for item in content_items)
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
