# Backend Getting Started

This guide explains how to run the backend for the closed-loop GenAI payment fraud red-team/blue-team system.

## 1. Install Dependencies

From the repo root:

```bash
python3 -m pip install -r requirements.txt
```

Optional cloud provider dependencies:

```bash
python3 -m pip install -r requirements-cloud.txt
```

Install `requirements-cloud.txt` only if you plan to use AWS Bedrock or GCP Vertex AI from this environment.

Azure and LM Studio use HTTP calls from the Python standard library and do not require extra SDK packages.

## 2. Validate The Attack Catalog

```bash
python3 -B -m src.cli.validate_catalog
```

Expected result:

```text
checked=25
valid=true
```

## 3. Run The Linear Backend Pipeline

Generate synthetic records:

```bash
python3 -B -m src.cli.generate_dataset
```

Build model features:

```bash
python3 -B -m src.cli.build_features
```

Train the baseline detector:

```bash
python3 -B -m src.cli.train_detector
```

Score generated records:

```bash
python3 -B -m src.cli.score_detector
```

Evaluate detector results:

```bash
python3 -B -m src.cli.evaluate_detector
```

Main outputs:

```text
data/generated/
data/processed/features.csv
outputs/models/baseline_model.pkl
outputs/metrics/train_metrics.json
outputs/scores/scores.csv
outputs/reports/
```

## 4. Run A Closed-Loop Iteration

Run one full red-team/blue-team loop:

```bash
python3 -B -m src.cli.run_loop_iteration --iteration-id iteration_001
```

This writes:

```text
outputs/iterations/iteration_001/
```

The loop performs:

```text
generate -> features -> train -> score -> evaluate -> failure analysis -> mutation proposals
```

## 5. Review And Consume Mutations

List mutation candidates:

```bash
python3 -B -m src.cli.list_mutations iteration_001
```

Accept all candidates for the next loop run:

```bash
python3 -B -m src.cli.review_all_mutations iteration_001 --decision accepted
```

Run the next iteration using accepted mutations from the previous iteration:

```bash
python3 -B -m src.cli.run_loop_iteration \
  --iteration-id iteration_002 \
  --review-source-iteration-id iteration_001
```

Compare two iterations:

```bash
python3 -B -m src.cli.compare_iterations iteration_001 iteration_002
```

Mutation-review artifacts:

```text
outputs/iterations/iteration_001/mutation_candidates.json
outputs/iterations/iteration_001/mutation_reviews.json
outputs/iterations/iteration_001/accepted_mutations.json
outputs/iterations/iteration_002/mutation_usage.json
```

## 6. Start The API

```bash
python3 -B -m src.cli.run_api --host 127.0.0.1 --port 8000
```

Open:

```text
http://127.0.0.1:8000/docs
```

Useful endpoints:

```text
GET  /health
GET  /attack-catalog
POST /generate
POST /features/build
POST /train
POST /score
GET  /metrics
POST /loop/run
GET  /loop/iterations
GET  /loop/compare
GET  /genai/health
GET  /genai/providers
POST /genai/config/session
POST /genai/test-connection
POST /genai/cost/estimate
```

## 7. GenAI Provider Configuration

Default provider:

```text
local_rules
```

This is deterministic and requires no model server.

Supported provider choices:

```text
local_rules
local_lmstudio
aws_bedrock
gcp_vertex_ai
azure_ai_foundry
```

Example config:

```text
configs/genai_providers.example.json
```

For frontend/API-driven configuration, use:

```text
POST /genai/config/session
```

This stores config in process memory and redacts secrets in responses. It is suitable for the prototype. Production should replace it with encrypted storage plus a secret manager.

## 8. LM Studio

Start LM Studio's local server, usually at:

```text
http://localhost:1234/v1
```

Then configure:

```json
{
  "default_provider": "local_lmstudio",
  "fallback_provider": "local_rules",
  "task_routes": {
    "attack_mutation": "local_lmstudio"
  },
  "providers": {
    "local_rules": {
      "type": "local_rules"
    },
    "local_lmstudio": {
      "type": "openai_compatible",
      "base_url": "http://localhost:1234/v1",
      "model": "your-local-model",
      "timeout_seconds": 60,
      "temperature": 0.2,
      "max_tokens": 1200
    }
  },
  "budget": {
    "max_calls_per_run": 25,
    "max_tokens_per_call": 1200,
    "dry_run": false
  }
}
```

Test the active provider:

```text
POST /genai/test-connection
```

## 9. Cloud Providers

AWS Bedrock:

- install `requirements-cloud.txt`
- configure `region`
- configure `model`
- rely on normal `boto3` credentials

GCP Vertex AI:

- install `requirements-cloud.txt`
- configure `project_id`
- configure `location`
- configure `model`
- rely on Application Default Credentials

Azure AI Foundry:

- configure `endpoint`
- configure `api_key`
- configure `deployment`
- configure `api_version`

For the prototype, secrets can be submitted into the in-memory session config. For production, do not store raw secrets in repo files.

## 10. Cost Estimates

The backend estimates tokens approximately and can produce what-if cloud costs.

Pricing config:

```text
configs/model_pricing.example.json
```

Usage output:

```text
outputs/usage/genai_usage.jsonl
outputs/usage/latest_cost_estimate.json
```

These numbers are not billing-grade. They are for dashboard-level comparison.

## 11. Run Tests

```bash
python3 -B -m pytest
```

Expected result:

```text
16 passed
```

## Troubleshooting

If imports fail, reinstall dependencies:

```bash
python3 -m pip install -r requirements.txt
```

If cloud provider imports fail, install optional dependencies:

```bash
python3 -m pip install -r requirements-cloud.txt
```

If LM Studio fails, check:

- the LM Studio server is running,
- the configured base URL ends in `/v1`,
- the configured model name is available,
- fallback provider is set to `local_rules`.

If API startup fails because port `8000` is busy:

```bash
python3 -B -m src.cli.run_api --host 127.0.0.1 --port 8001
```

