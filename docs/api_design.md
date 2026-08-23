# API Design

This document defines the backend interface between the generator, detector, and prototype UI.

The API should be small, predictable, and easy to demo.

## Core API responsibilities

- expose attack catalog metadata,
- generate synthetic scenarios,
- return generated synthetic records,
- score records with the detector,
- return explanations and metrics.

## Recommended endpoints

### `GET /health`

Purpose:

- basic service check

Returns:

- service status
- version

### `GET /attack-catalog`

Purpose:

- list available attack cards

Returns:

- catalog summary
- filtering metadata

### `GET /attack-catalog/{attack_id}`

Purpose:

- fetch one detailed attack card

Returns:

- the full attack card
- derived metadata

### `POST /generate`

Purpose:

- create synthetic scenarios and records

Inputs:

- selected attack IDs
- generation count
- stealth level
- intensity
- seed

Returns:

- generated scenario metadata
- synthetic records
- validation results

### `POST /score`

Purpose:

- run the defense model on generated or uploaded records

Inputs:

- transaction records or file reference

Returns:

- fraud scores
- labels
- explanations

### `GET /metrics`

Purpose:

- expose evaluation summaries

Returns:

- precision
- recall
- F1
- AUC
- false positive rate

### `POST /feedback`

Purpose:

- capture detector misses and user feedback

Returns:

- updated attack priorities
- suggested generator changes

### Closed-loop job endpoints

`POST /loop/run` starts the full pipeline. Set `async_run: true` for the UI workflow; it returns an in-memory job immediately rather than holding the HTTP request open.

Poll `GET /loop/jobs/{job_id}` for the current status and stage. Completed jobs contain the iteration summary. Existing endpoints provide durable iteration evidence and human review:

- `GET /loop/iterations`
- `GET /loop/iterations/{iteration_id}`
- `GET /loop/iterations/{iteration_id}/mutations`
- `POST /loop/iterations/{iteration_id}/mutations/{mutation_id}/review`
- `GET /loop/compare?baseline=<id>&candidate=<id>`
- `GET /loop/iterations/{iteration_id}/transactions?page=1&page_size=25&label=1&bucket=<bucket>&flagged=1`

The transaction endpoint joins generated transaction records with detector scores and returns a paginated, browser-safe view. It is intended for the prototype explorer; production should apply authorization and row-level data controls before exposing transaction data.

It also accepts `llm_reviewed`, `decision_engine`, `sort_by`, and `sort_direction`. Sorting occurs before pagination and supports transaction, context, ML score, LLM review, final score, and decision fields.

`GET /loop/iterations/{iteration_id}/transactions/{transaction_id}` returns the complete synthetic transaction plus its detector output and linked synthetic customer, merchant, device, and attack-scenario records. It powers the transaction evidence panel.

`GET /loop/iterations/{iteration_id}/genai-usage` returns iteration-attributed gateway calls, estimated token totals, latency totals, fallback metadata, and aggregated what-if cost estimates. It is an observability estimate, not a billing record.

### Local portfolio onboarding endpoints

The local demo onboarding API accepts CSV **content** as JSON fields. This keeps the backend dependency-free until the upload UI is added; the future browser flow can read a selected local file and submit its content unchanged.

- `GET /portfolio/template`
- `POST /portfolio/datasets`
- `GET /portfolio/datasets`
- `GET /portfolio/datasets/{dataset_id}`
- `POST /portfolio/datasets/{dataset_id}/score`
- `DELETE /portfolio/datasets/{dataset_id}`

`POST /portfolio/datasets/{dataset_id}/score` defaults to ML-only advisory scoring. GenAI review is opt-in. Local LM Studio routes are permitted; remote/cloud routes require an explicit `cloud_data_acknowledged` request flag and the response exposes the selected data route. See [Local Portfolio Onboarding](./portfolio_onboarding.md) for the canonical CSV contract and safety boundary.

## API design principles

- Use JSON as the default payload format.
- Keep requests idempotent where possible.
- Include seeds for reproducibility.
- Return structured errors.
- Keep responses stable enough for a demo UI.

## Example request shape

```json
{
  "attack_id": "cred_cnp_001",
  "count": 25,
  "stealth_level": 0.7,
  "intensity": 0.6,
  "seed": 42
}
```

## Example response shape

```json
{
  "scenario_id": "scn_001",
  "generated_count": 25,
  "fraud_count": 8,
  "validation_passed": true
}
```

## Why the API matters

The API is the glue that lets the prototype show the closed loop in action.

- The UI should not need to know model internals.
- The generator and detector should remain independently testable.
- The API should make the system feel real and interactive.
