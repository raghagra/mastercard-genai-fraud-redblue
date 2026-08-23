# Repo Structure

This document defines a clean repository layout for the project.

The goal is to separate knowledge, generation, detection, evaluation, and presentation cleanly.

## Recommended top-level structure

```text
mastercardchallenge/
  docs/
  schemas/
  data/
  src/
  app/
  notebooks/
  tests/
  configs/
  outputs/
  README.md
```

## Folder responsibilities

### `docs/`

Human-readable knowledge base.

Contains:

- schema definitions
- data model docs
- generator design
- detection design
- evaluation plan
- attack catalog

### `schemas/`

Machine-readable schema files.

Contains:

- `attack_card.schema.json`
- later, any dataset schema files

### `data/`

Synthetic or example data artifacts.

Suggested subfolders:

- `data/raw/`
- `data/processed/`
- `data/generated/`

### `src/`

Implementation code.

Suggested subfolders:

- `src/generate/`
- `src/detect/`
- `src/evaluate/`
- `src/common/`

### `app/`

Web prototype code.

Suggested subfolders:

- `app/backend/`
- `app/frontend/`

### `notebooks/`

Exploration and experimentation notebooks.

Use sparingly so the core pipeline stays reproducible.

### `tests/`

Automated tests for:

- schema validation
- generation sanity checks
- detection pipeline checks
- evaluation utilities

### `configs/`

Configuration files for:

- attack catalog weights
- generation settings
- model hyperparameters
- evaluation settings

### `outputs/`

Generated artifacts such as:

- charts
- metrics
- example outputs
- prototype screenshots

## Code organization principle

Keep the pipeline layered:

- knowledge in `docs/`
- contracts in `schemas/`
- logic in `src/`
- demo in `app/`
- evidence in `outputs/`

## Why this layout works

- Easy to understand.
- Easy to reproduce.
- Easy to present in a competition setting.
- Easy to expand without becoming messy.

