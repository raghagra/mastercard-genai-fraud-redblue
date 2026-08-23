# Closed-Loop Design

This document describes the red-team/blue-team feedback loop added after the backend MVP.

The goal is to move beyond a linear pipeline and toward a system that uses its own simulated attacks as training and stress-testing material for a stronger defense.

## Current loop

The current loop can run in two modes.

Baseline loop:

```text
generate -> features -> train -> score -> evaluate -> analyze failures -> propose mutations
```

Reviewed mutation loop:

```text
mutation candidates -> human review -> accepted mutations -> runtime overlays -> next generation run
```

## Why this matters

The problem statement asks for a closed-loop AI system. That means the detector should not be treated as the final step.

Instead:

- generated attacks train and stress-test the detector,
- detector weaknesses are analyzed,
- weak areas feed back into new attack variants,
- later iterations should compare whether the defense improved.

## Realism and unseen-attack feedback

Each iteration now defaults to the `overlap` realism profile, which produces stealth fraud and atypical legitimate activity with intentionally overlapping signals. Training holds out complete attack cards and writes a `heldout_attack_benchmark` alongside all-row metrics. The loop should use misses from this held-out benchmark—not only its in-sample failures—to prioritize the next red-team mutations. This makes “unseen attack” performance part of the feedback signal.

## Lightweight GenAI interface

The code now includes a GenAI-shaped abstraction:

- `src/genai/base.py`
- `src/genai/local_rules.py`

`local_rules` is a deterministic stand-in for a future LLM provider. It lets the backend exercise the same interface we will later use for LM Studio, AWS, GCP, or Azure without needing credentials or token spend.

## Failure analysis

Failure analysis reads detector scores and identifies:

- false positives,
- false negatives,
- low-confidence fraud groups,
- high-risk benign records,
- weak attack subtypes.

If there are no false negatives yet, the loop still produces useful pressure points by selecting the lowest-confidence fraud groups.

## Mutation candidates

Mutation candidates are structured suggestions for harder red-team variants.

Each candidate includes:

- source attack ID,
- bucket and subtype,
- proposed variant name,
- mutation strategy,
- suggested generation strategy,
- rationale,
- human review flag.

### Attack-aware proposal content

Every proposal includes `parameter_deltas`: an explicit before-and-after view of the generation strategy and the defensive purpose of each change. The deterministic fallback is no longer one generic stealth template. It uses family-specific pressure plans, for example:

- credential attacks: low-and-slow campaign pacing and reduced burst volume;
- social-engineering payments: trusted-context overlap and reduced single-session concentration;
- identity onboarding: mature-looking profiles with retained inconsistency signals;
- post-transaction abuse: plausible purchase context with reduced claim velocity;
- merchant abuse: gradual merchant lifecycle and lower volume-growth spikes.

The UI renders these as `baseline → proposed` values. Human acceptance remains mandatory before a variant can enter a future run.

Mutation candidates are not automatically inserted into the permanent catalog.

Instead, they pass through a review workflow:

```text
mutation_candidates.json
  -> mutation_reviews.json
  -> accepted_mutations.json
  -> mutation_usage.json in the next iteration
```

This design keeps the future UI clean: candidate review can be represented as accept/reject buttons, while the backend already owns the review state and accepted mutation consumption.

## Iteration outputs

Each loop run writes to:

```text
outputs/iterations/iteration_001/
  generated/
  processed/
  models/
  metrics/
  scores/
  reports/
  loop_summary.json
  mutation_candidates.json
  mutation_reviews.json
  accepted_mutations.json
  mutation_usage.json
```

## Mutation review commands

List candidates and decisions:

```bash
python3 -B -m src.cli.list_mutations iteration_001
```

Accept one mutation:

```bash
python3 -B -m src.cli.review_mutation iteration_001 mut_abc123 --decision accepted
```

Accept all candidates:

```bash
python3 -B -m src.cli.review_all_mutations iteration_001 --decision accepted
```

Run a later iteration using reviewed mutations from a previous iteration:

```bash
python3 -B -m src.cli.run_loop_iteration \
  --iteration-id iteration_002 \
  --review-source-iteration-id iteration_001
```

## API support

The same workflow is exposed through the API:

```text
GET  /loop/iterations/{iteration_id}/mutations
POST /loop/iterations/{iteration_id}/mutations/{mutation_id}/review
POST /loop/iterations/{iteration_id}/mutations/review-all
GET  /loop/iterations/{iteration_id}/mutation-impact
POST /loop/run
```

`POST /loop/run` accepts `review_source_iteration_id`, allowing a UI to start a new loop run from previously accepted mutations.
It also accepts `mutation_candidate_limit` (1–10; default 5), so a demo operator can widen the human-review queue without changing code.

The mutation-impact endpoint provides a judge-friendly before/after view: it lists the accepted variants that were consumed and compares the source and candidate iteration's F1, recall, precision, and false-positive rate. It is deliberately labelled as an outcome comparison, not causal proof, because each iteration creates a new synthetic sample.

## Controlled mutation experiment and LLM explanation

For a stronger comparison, the web prototype can run a controlled experiment for an accepted mutation. It creates matched baseline and mutated synthetic scenarios with the same seed, benign volume, and number of scenarios, then scores each with the frozen detector from the source iteration. Per-row LLM review is disabled for this experiment so its aggregate comparison isolates the frozen detector.

The resulting deterministic explanation is always shown first. **Ask LLM** then streams a short interpretation generated from aggregate metrics and the mutation's declared parameter deltas only; raw transaction records are not included. The UI labels this as an interpretation and retains the deterministic result if the provider fails.

## Important limitation

The current mutation provider is deterministic. It creates useful closed-loop behavior, but it is still a local stand-in for a real LLM-powered mutation engine.
