# Evaluation Plan

This document defines how the closed-loop system should be measured.

The evaluation needs to show that the solution is not just creative, but useful.

## Evaluation pillars

The solution should be evaluated across four pillars:

1. Attack diversity
2. Simulation fidelity
3. Detection efficacy
4. Real-world feasibility

## 1. Attack diversity

Measure how broad the attack catalog is.

Useful metrics:

- number of buckets covered
- number of attack patterns covered
- number of variants per pattern
- channel coverage
- rail coverage

Expected output:

- a catalog summary table
- a coverage heatmap or matrix

## 2. Simulation fidelity

Measure how realistic the generated attacks look.

Useful metrics:

- distribution similarity versus benign reference data
- constraint violation rate
- scenario plausibility score
- human review score
- per-bucket realism score

Examples of fidelity checks:

- amounts fall in plausible ranges
- timestamps and sequences make sense
- entity relationships remain consistent
- fraud behavior matches the target pattern

## 3. Detection efficacy

Measure how well the defense model catches the synthetic fraud.

Required metrics:

- precision
- recall
- F1
- ROC-AUC
- PR-AUC
- false positive rate

Recommended breakdowns:

- by bucket
- by subtype
- by attack intensity
- by stealth level

## 4. Real-world feasibility

Measure whether the solution could plausibly be used in live payments.

Useful checks:

- inference latency
- feature availability in real time
- explanation quality
- retraining practicality
- support for new attack variants

## Experimental design

Recommended evaluation setup:

- train on a subset of attack patterns
- test on held-out variants
- compare benign versus fraudulent records
- compare weak and strong attacks
- measure robustness under different stealth levels

### Implemented leakage-resistant benchmark

The repository now implements the recommended attack-pattern holdout. It deterministically withholds complete attack cards (`attack_id`), rather than random individual events, and reserves a benign sample for false-positive measurement. This prevents records from the same synthetic campaign being used both to train and evaluate the detector.

Report these separately in the walkthrough:

- `heldout_attack_benchmark`: primary metric for transfer to unknown attack cards;
- `overall`: all generated rows, useful for operational observability but not a novelty/generalization assertion;
- `ml_only_overall` versus hybrid scores: the marginal value and cost of selective GenAI review.

The default `overlap` realism profile should be used for judged metrics. Also report the profile and seed so results remain reproducible.

## Closed-loop evaluation

The system should support iterative improvement.

Iteration loop:

1. Generate attacks.
2. Train detector.
3. Measure misses and false alarms.
4. Update attack generation.
5. Retrain the detector.
6. Compare metrics across iterations.

## Reporting format

The write-up should include:

- summary tables
- metric plots
- confusion matrix or equivalent breakdown
- per-bucket performance analysis
- examples of true positives, false positives, and false negatives

## Why this evaluation plan matters

It shows the system is:

- broad enough to be interesting,
- realistic enough to be useful,
- accurate enough to matter,
- and structured enough to improve over time.
