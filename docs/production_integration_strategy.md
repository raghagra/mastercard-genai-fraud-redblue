# Production Integration Strategy

This document defines how the system should be designed so it can later integrate into a Mastercard-style production environment without depending on a specific cloud provider.

Cloud deployment is a Phase 3 concern. The core architecture should still be production-aware from Phase 1.

## Positioning

The solution should be framed as a fraud simulation and defense accelerator.

Its role is to help payment security teams:

- discover GenAI-enabled fraud patterns,
- simulate realistic synthetic attacks,
- train and stress-test detection models,
- expose risk scores and explanations for operational use.

## Integration principles

### Cloud-neutral by default

The core system should not depend on AWS, Azure, GCP, or any provider-specific service.

Prefer:

- Python modules for core logic,
- REST APIs for serving,
- standard file formats such as JSON, JSONL, CSV, and Parquet,
- environment variables or config files for settings,
- container-ready service boundaries.

### API-first

The web UI should be one client, not the only interface.

Core capabilities should be available through:

- CLI jobs,
- backend APIs,
- batch scripts,
- future event-driven integrations.

### Pluggable adapters

Production environments vary. Keep adapters separate from core logic.

Adapter candidates:

- transaction input adapter,
- feature store adapter,
- model artifact adapter,
- alert/case-management adapter,
- storage adapter,
- audit log adapter.

### Stateless services where possible

The scoring API should avoid storing mutable business state internally.

State should live in:

- durable storage,
- generated output artifacts,
- model artifacts,
- audit logs,
- external case systems.

### Reproducible generation

Every generated scenario should be traceable.

Track:

- attack card ID,
- scenario ID,
- generator version,
- seed,
- timestamp,
- generated record IDs.

This is essential for auditability and model-risk review.

## Production data flow

### Real-time scoring path

```text
Payment event
  -> input adapter
  -> feature builder
  -> detector service
  -> risk score + reason codes
  -> fraud decisioning system
```

### Batch training and stress-testing path

```text
Attack catalog
  -> scenario generator
  -> synthetic datasets
  -> feature builder
  -> model training
  -> evaluation reports
  -> model artifact
```

### Feedback path

```text
Model misses / analyst feedback
  -> error analysis
  -> attack catalog refinement
  -> harder simulations
  -> retraining / re-evaluation
```

## Service boundaries

Recommended future services:

- catalog service,
- generation service,
- detection service,
- evaluation service,
- analyst UI.

For the first implementation, these can live in one repo and one backend process. The module boundaries should still mirror the future services.

## Security and governance

The system should support:

- structured audit logs,
- model version tracking,
- generated-data lineage,
- controlled configuration,
- no secrets hardcoded in code,
- clear separation between synthetic and real data.

## Deployment-neutral artifacts

The system should produce standard artifacts:

- `attack_card` JSON files,
- generated synthetic datasets,
- trained model files,
- metric reports,
- scenario lineage logs,
- API responses.

These artifacts can move across local, containerized, or cloud-hosted environments.

## Phase 3 production roadmap

Phase 3 can add:

- Docker images,
- deployment manifests,
- authentication and authorization,
- observability,
- model registry integration,
- feature store integration,
- event-stream support,
- batch scheduler support,
- cloud-specific templates if required.

## What not to build yet

Do not build cloud-specific deployment in Phase 1 or Phase 2 unless the challenge later requires it.

Avoid early dependencies on:

- provider-specific queues,
- managed feature stores,
- cloud-only secret managers,
- proprietary database services.

## Why this matters

This strategy lets the prototype stay lightweight while proving that it can mature into an enterprise-ready fraud simulation and detection accelerator.

