# GenAI Gateway

This document describes the provider-agnostic GenAI gateway.

The gateway lets the closed-loop backend use GenAI-shaped tasks without binding the system to one model provider.

## Current status

Implemented:

- deterministic `local_rules` provider,
- config-driven gateway,
- task-based provider routing,
- fallback provider support,
- LM Studio / OpenAI-compatible chat completions adapter,
- AWS Bedrock adapter,
- GCP Vertex AI adapter,
- Azure AI Foundry adapter,
- in-memory session config for frontend-driven provider setup,
- approximate token and what-if cost estimation.

Not yet implemented:

- production secret persistence,
- billing-grade cost accounting,
- provider-specific streaming.

## Default behavior

The default provider is `local_rules`.

This keeps local runs cheap, deterministic, and reliable.

## Config file

The example config lives at:

```text
configs/genai_providers.example.json
```

By default, the backend uses:

```text
configs/genai_providers.json
```

if it exists. Otherwise, it falls back to the example config.

You can also set:

```bash
export GENAI_CONFIG_PATH=/path/to/genai_providers.json
```

## Frontend-driven session config

For the prototype, the frontend should configure providers through the backend API.

The backend stores this config in process memory:

```text
POST   /genai/config/session
GET    /genai/config/session
DELETE /genai/config/session
```

This is deliberate. It avoids writing cloud secrets into repo files while keeping the UI workflow realistic.

Production can replace the in-memory store with:

- encrypted database config for non-secret fields,
- AWS Secrets Manager, Azure Key Vault, GCP Secret Manager, HashiCorp Vault, or internal Mastercard secret storage for secrets,
- per-user or per-workspace provider profiles.

## Provider selection API

The UI can discover provider forms from:

```text
GET /genai/providers
```

Supported provider choices:

- `local_rules`
- `local_lmstudio`
- `aws_bedrock`
- `gcp_vertex_ai`
- `azure_ai_foundry`

The gateway is task-routed, so a UI can set:

```json
{
  "default_provider": "local_lmstudio",
  "fallback_provider": "local_rules",
  "task_routes": {
    "attack_mutation": "aws_bedrock"
  }
}
```

## Cloud adapters

### AWS Bedrock

Provider type:

```text
aws_bedrock
```

Expected fields:

- `region`
- `model`
- `temperature`
- `max_tokens`

Credentials use standard `boto3` resolution, such as environment variables, AWS profile, SSO, workload identity, or role-based credentials.

Optional dependency:

```bash
python3 -m pip install -r requirements-cloud.txt
```

### GCP Vertex AI

Provider type:

```text
gcp_vertex_ai
```

Expected fields:

- `project_id`
- `location`
- `model`
- `temperature`
- `max_tokens`

Credentials use Google Application Default Credentials.

Optional dependency:

```bash
python3 -m pip install -r requirements-cloud.txt
```

### Azure AI Foundry

Provider type:

```text
azure_ai_foundry
```

Expected fields:

- `endpoint`
- `api_key`
- `deployment`
- `api_version`
- `temperature`
- `max_tokens`

The adapter calls the Azure OpenAI-compatible chat completions deployment path.

## LM Studio

LM Studio can be used through its OpenAI-compatible local server.

Expected default endpoint:

```text
http://localhost:1234/v1
```

Example route:

```json
{
  "default_provider": "local_lmstudio",
  "fallback_provider": "local_rules",
  "task_routes": {
    "attack_mutation": "local_lmstudio"
  }
}
```

If LM Studio is not running or the request fails, the gateway falls back to `local_rules` when configured that way.

### Mac-only recommended setup

For the first working setup, host one primary model in LM Studio on the same Mac as the backend. A 14B Q4 model is the recommended primary model for attack ideation and mutation generation on a 24 GB Apple Silicon Mac.

1. Load the model in LM Studio.
2. In LM Studio's Developer tab, start the local server.
3. Start the FastAPI backend and frontend.
4. In the frontend, open **GenAI gateway**, select **Local LM Studio**, and enter:

```text
Base URL:       http://127.0.0.1:1234/v1
Model:          the model identifier shown by LM Studio
Timeout seconds: 120
Temperature:    0.7
Max tokens:     1200
```

5. Save the session configuration, then use `POST /genai/test-connection` or the API documentation to verify it.

If LM Studio authentication is enabled, enter its API token in the UI's API key field. It stays in backend process memory and is redacted in all configuration responses. Leave it empty when the LM Studio server is using its default unauthenticated local-only setting.

## Supported tasks

Current task:

- `attack_mutation`

For this task, the provider must return a structured, reviewable candidate. In addition to lineage, rationale, and a suggested generation strategy, the response contract requires `parameter_deltas`: the baseline value, proposed value, and defensive simulation purpose for each changed parameter. Invalid or incomplete model responses safely fall back to the attack-aware `local_rules` provider.

Future tasks:

- `attack_ideation`
- `scenario_narrative`
- `alert_explanation`
- `evaluation_summary`

## Health check

CLI:

```bash
python3 -B -m src.cli.genai_health
```

API:

```text
GET /genai/health
```

Test the active provider:

```text
POST /genai/test-connection
```

The web prototype's **Save & test connection** action first saves the selected provider into the in-memory session, then sends a defensive `attack_mutation` test request. It displays the provider that actually answered, end-to-end latency, estimated input/output tokens, and any fallback metadata. This is the quickest way to verify that LM Studio—not `local_rules`—is participating in the loop.

## Cost estimation

The gateway estimates input/output tokens with a simple character-based heuristic and writes usage events to:

```text
outputs/usage/genai_usage.jsonl
outputs/usage/latest_cost_estimate.json
```

The pricing table lives at:

```text
configs/model_pricing.example.json
```

This is approximate and not billing-grade. It is meant for a dashboard that answers:

```text
If this local run had used AWS/GCP/Azure, roughly what might it have cost?
```

The estimate endpoint is:

```text
POST /genai/cost/estimate
```

After a successful connection test, the web prototype submits that request's estimated token volumes to this endpoint and renders the configured what-if cost comparisons.

## Iteration-Level Usage Attribution

Every gateway call created while a closed-loop iteration proposes mutations now carries the iteration ID as internal request context. The usage ledger records:

- iteration ID and task,
- responding provider and fallback metadata,
- end-to-end gateway latency,
- estimated input and output tokens,
- per-call what-if cost estimates.

The frontend reads `GET /loop/iterations/{iteration_id}/genai-usage` to show aggregate token/latency totals, equivalent provider costs, and a call-by-call ledger. Iterations created before this feature will have no attributed calls; run a new iteration to populate the dashboard.

## Mutation Output Contract And Fallback

Local models can refuse a prompt or return incomplete/non-JSON output. A mutation is reviewable only when it contains the required mutation ID, source attack lineage, subtype, rationale, strategy, and generation strategy fields. Invalid model output is retained in the provider usage ledger but is not allowed into review or synthetic training data. The system substitutes a deterministic `local_rules` mutation with an explicit `gateway_fallback` audit marker, so the closed loop continues safely.

### Structured local-model reliability

The LM Studio adapter requests OpenAI-compatible JSON-object mode when the server/model supports it. If that capability is unavailable, it retries once using the prompt-only JSON contract. The current mutation request uses a compact small-model-friendly intent contract: the model supplies a variant name, rationale, and selected defensive focuses; the backend converts those focuses into bounded generator settings, immutable lineage, and reviewable parameter deltas. This lets a 14B local model contribute genuine ideation without being asked to reproduce mechanical IDs or a large nested schema.

Responses that are refusal-shaped, non-JSON, vague, or propose no valid generation-strategy change are still rejected and safely replaced by `local_rules`. The review card identifies the responding provider and any fallback, so a demo never misrepresents deterministic output as an LLM contribution.

## Design principle

The backend should call the gateway by task, not by provider.

That means closed-loop modules ask for:

```text
attack_mutation
```

and the gateway decides whether that runs on local rules, LM Studio, or a future cloud provider.
