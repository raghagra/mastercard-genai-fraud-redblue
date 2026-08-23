# Implementation Roadmap

This document gives the practical build order for the project.

The goal is to move from documentation to a working system without creating unnecessary rework.

## Phase 1: Contract and knowledge

Complete:

- attack card schema
- attack catalog
- synthetic data model
- generator design
- detection baseline
- evaluation plan
- repo structure
- API design
- web prototype design

## Phase 2: Core code scaffolding

Build:

- directory structure
- config loading
- schema validation utilities
- logging and artifact saving
- shared data models

## Phase 3: Generation engine

Build:

- attack catalog loader
- scenario builder
- record generator
- validation layer
- reproducibility hooks

## Phase 4: Defense baseline

Build:

- feature engineering
- training pipeline
- scoring pipeline
- explanation outputs
- thresholding logic

## Phase 5: Evaluation and iteration

Build:

- metric computation
- per-bucket reporting
- false-positive and false-negative analysis
- closed-loop refinement hooks

## Phase 6: API and prototype

Build:

- backend endpoints
- frontend views
- generation and scoring demo flow
- feedback loop display

## Phase 7: Packaging and submission

Build:

- final README
- run instructions
- walkthrough document or deck
- demo assets

## Recommended implementation order

1. scaffold repo
2. implement schema validation
3. implement attack catalog loading
4. implement synthetic generator
5. implement detector baseline
6. implement evaluation
7. implement API
8. implement prototype
9. finalize documentation

## Why this roadmap matters

It keeps the project from becoming a collection of disconnected parts.

The design docs define the contract first, then the code can follow cleanly.

