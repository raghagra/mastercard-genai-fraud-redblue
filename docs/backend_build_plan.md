# Backend Build Plan

This document defines the first backend implementation sequence.

The backend should start as a local, reproducible Python system and later expose the same logic through an API.

## Backend objective

Build the smallest useful backend that can:

- load and validate attack cards,
- generate synthetic transactions,
- train a baseline fraud detector,
- score records,
- report metrics.

## First milestone

The first backend milestone should be:

```text
attack cards -> schema validation -> synthetic transactions -> baseline model -> metrics report
```

This creates an end-to-end engine before the UI is built.

## Initial modules

### `src/common`

Shared utilities.

Needed files:

- `config.py`
- `io.py`
- `ids.py`
- `random.py`
- `schemas.py`

### `src/knowledge`

Attack catalog loading and validation.

Needed files:

- `load_attack_catalog.py`
- `validate_attack_cards.py`

### `src/generate`

Synthetic scenario and record generation.

Needed files:

- `scenario.py`
- `sampler.py`
- `records.py`
- `validators.py`
- `pipeline.py`

### `src/features`

Model-ready feature creation.

Needed files:

- `build_features.py`
- `encoders.py`

### `src/detect`

Baseline detector.

Needed files:

- `train.py`
- `score.py`
- `explain.py`
- `thresholds.py`

### `src/evaluate`

Metrics and reporting.

Needed files:

- `metrics.py`
- `reports.py`
- `feedback.py`

### `src/cli`

Runnable commands.

Needed files:

- `validate_catalog.py`
- `generate_dataset.py`
- `train_detector.py`
- `evaluate_detector.py`

## First commands to support

```bash
python -m src.cli.validate_catalog
python -m src.cli.generate_dataset
python -m src.cli.train_detector
python -m src.cli.evaluate_detector
```

## Backend-first success criteria

The first backend phase is successful when:

- attack cards validate,
- synthetic data is generated reproducibly,
- a detector trains successfully,
- metrics are written to outputs,
- the flow can be run from CLI.

## API phase

After the backend engine works, wrap it with FastAPI.

Initial endpoints:

- `GET /health`
- `GET /attack-catalog`
- `POST /generate`
- `POST /score`
- `GET /metrics`

## Why this build order matters

The engine needs to work before the UI can tell a convincing story.

Once the backend is stable, the UI can become a clean operational console rather than a thin demo shell.

