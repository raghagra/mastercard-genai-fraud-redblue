# SentinelLoop — GenAI Payment Fraud Red/Blue Team Lab

SentinelLoop is a local-first, closed-loop prototype for the Mastercard Innovation Challenge. It turns payment-fraud research into a repeatable defensive workflow:

```text
Identify attack patterns → simulate synthetic payment activity → detect and explain risk
        ↑                                                               │
        └──── review detection gaps and approve bounded attack mutations ┘
```

The system is designed for defensive simulation and evaluation. It does **not** process real payment credentials, execute attacks, or connect to payment rails.

## What it demonstrates

- A payment-grounded attack catalog across five practical fraud families.
- Synthetic generation of benign and fraud-labelled transaction, customer, merchant, device, and attack-scenario records.
- A baseline ML detector with feature engineering, scoring, metrics, explanations, and selective GenAI review.
- A human-governed closed loop: failures produce bounded mutation proposals; accepted proposals are consumed by a later run.
- A controlled mutation experiment that scores matched baseline and mutated scenarios with the same frozen detector.
- A local-first GenAI gateway supporting deterministic rules, LM Studio, and cloud-provider configuration surfaces.
- A React web console for running, reviewing, exploring, and presenting the workflow.

## Safety and data boundary

Use only synthetic, anonymized, or explicitly authorized demo data. Never upload or commit PANs, CVVs, account numbers, direct PII, production payment records, API keys, or cloud credentials. The portfolio-onboarding view is local-demo only and includes explicit warnings for cloud GenAI routing.

## Architecture

```text
Attack catalog → Synthetic generator → Feature builder → ML detector → Evaluation
                                                                    │
GenAI gateway ← Human review ← Mutation proposals ← Failure analysis
                                                                    │
                         Next iteration / controlled experiment ───┘
```

Key implementation areas:

| Area | Location |
| --- | --- |
| FastAPI backend | `src/api/` |
| Attack knowledge and schemas | `knowledge/`, `schemas/`, `docs/` |
| Synthetic generator | `src/generate/` |
| Features and detection | `src/features/`, `src/detect/` |
| Evaluation and closed loop | `src/evaluate/`, `src/loop/`, `src/mutate/` |
| GenAI gateway | `src/genai/` |
| React/Vite console | `frontend/` |

## Quick start

### Prerequisites

- Python 3.12+
- Node.js 20+
- Optional: LM Studio with a locally hosted model for GenAI-backed mutation and explanation

### 1. Install backend dependencies

From the repository root:

```bash
python3 -m pip install -r requirements.txt
```

Optional cloud SDKs:

```bash
python3 -m pip install -r requirements-cloud.txt
```

### 2. Validate the attack catalog

```bash
python3 -B -m src.cli.validate_catalog
```

Expected result: `checked=25` and `valid=true`.

### 3. Start the backend

In terminal one:

```bash
python3 -B -m src.cli.run_api --host 127.0.0.1 --port 8000
```

API docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

### 4. Start the frontend

In terminal two:

```bash
cd frontend
npm install
npm run dev
```

Open the local URL printed by Vite, normally [http://127.0.0.1:5173](http://127.0.0.1:5173).

## One-command judge demo

For a reproducible, local-only walkthrough that prepares closed-loop evidence and starts both services:

```bash
python3 scripts/judge_demo.py
```

It uses deterministic local rules by default, so it needs neither cloud credentials nor an LM Studio server. See [Judge demo](JUDGE_DEMO.md) for the walkthrough and options, including using a currently configured local GenAI provider.

## Run the demo

### First iteration

1. Open **Closed loop** in the web console.
2. Set a reproducible seed, benign-record count, scenarios per attack card, and review-candidate limit (1–10).
3. Select **Run iteration** and follow the live pipeline stages.
4. Inspect the generated payment records, hybrid decision evidence, detection metrics, and iteration trends.
5. Review mutation cards and accept or reject the proposed defensive stress-test variants.

### Complete the loop

1. In **Use accepted mutations**, select the source iteration containing accepted proposals.
2. Run a new iteration.
3. Select the new candidate iteration. The console records which approved mutations it consumed.
4. In **Accepted mutation: before vs. after**, select **Run controlled experiment**.
5. The experiment compares matched baseline and mutated synthetic scenarios using the frozen detector from the source iteration.
6. Read the deterministic explanation, then optionally select **Ask LLM** for a short provider-generated interpretation. Only aggregate metrics and declared mutation settings are provided to the LLM.

The broader iteration comparison is an outcome summary only; the controlled experiment is the clearer evidence because it holds the seed, scenario volume, benign volume, and detector fixed.

## Configure local GenAI (LM Studio)

The default `local_rules` provider works without a model server. To use LM Studio:

1. Start its OpenAI-compatible local server, normally `http://127.0.0.1:1234/v1`.
2. Open **GenAI gateway** in the web console.
3. Select **Local LM Studio**, enter the base URL and loaded model identifier, then select **Save & test connection**.
4. Confirm the response provider is `local_lmstudio` before starting a new loop iteration.

Provider configuration is session-only in the prototype. Restarting the backend clears it. See [GenAI Gateway](docs/genai_gateway.md) for provider, security, and cost-estimation details.

## CLI alternative

Run a complete loop without the web console:

```bash
python3 -B -m src.cli.run_loop_iteration --iteration-id iteration_001
python3 -B -m src.cli.list_mutations iteration_001
python3 -B -m src.cli.review_all_mutations iteration_001 --decision accepted
python3 -B -m src.cli.run_loop_iteration \
  --iteration-id iteration_002 \
  --review-source-iteration-id iteration_001
```

Completed artifacts are stored under `outputs/iterations/<iteration_id>/`.

## Verification

```bash
python3 -B -m pytest
cd frontend && npm run build
```

## Documentation

Start with the [documentation index](docs/README.md). Particularly relevant guides:

- [Backend getting started](docs/backend_getting_started.md)
- [Frontend getting started](docs/frontend_getting_started.md)
- [Closed-loop design](docs/closed_loop_design.md)
- [Synthetic data model](docs/synthetic_data_model.md)
- [Detection baseline](docs/detection_baseline.md)
- [Portfolio onboarding](docs/portfolio_onboarding.md)

## Prototype limitations

- Synthetic results are not evidence of real-world fraud performance.
- The baseline detector requires external, portfolio-specific validation before any production use.
- Cloud-provider configuration is intentionally adapter-based; validate credentials, pricing, retention, and governance before deployment.
- Local GenAI explanations are helpful narrative aids, not a replacement for measured evidence or human approval.
