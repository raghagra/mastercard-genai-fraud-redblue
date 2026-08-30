# Adversarial Evaluation Lab

The Adversarial Evaluation Lab is a deterministic, backend-first stress-test capability for SentinelLoop. It evaluates a **frozen detector from a completed loop iteration** across selected payment-fraud families, bounded attack-difficulty profiles, and reproducible seeds.

It is synthetic evaluation evidence. It is not a payment-time decisioning service and does not establish production fraud-detection performance.

## Why it exists

A normal closed-loop iteration shows one generated sample and its outcomes. The Evaluation Lab answers a broader question:

> Across the known payment-fraud surface, where does the frozen defence remain strong and where should the red team create the next governed stress test?

The resulting coverage matrix is designed for a future UI heatmap: rows are attack families, columns are difficulty profiles, and each cell contains precision, recall, F1, false-positive rate, misses, representative misses, and an action status.

## Evaluation design

1. Choose a completed source iteration with a frozen detector artifact.
2. Select attack buckets, difficulty profiles, deterministic seeds, scenarios per attack card, and benign-volume setting.
3. For every profile/seed arm, generate the selected attack cards with the same frozen detector.
4. Disable row-level LLM review for every arm, isolating detector coverage from provider availability, latency, and variable LLM output.
5. Aggregate metrics per `(difficulty profile, attack bucket)` cell.
6. Mark each cell:
   - `strong`: recall and F1 are at least 95%, with false-positive rate at most 10%;
   - `monitor`: below the strong threshold but above weak thresholds; or
   - `weak`: recall or F1 below 85%.

The thresholds are demo defaults, not production policy values. A portfolio-specific deployment must calibrate them using authorized data and business loss/review capacity.

## Difficulty profiles

| Profile | Controlled generator changes | Purpose |
| --- | --- | --- |
| `baseline` | Original attack-card strategy | Establish reference coverage. |
| `elevated` | +0.08 stealth, 0.75x volume, high noise, 1.4x time window | Reduce obvious velocity and increase benign overlap. |
| `stealth_stress` | +0.15 stealth, 0.55x volume, high noise, 2.0x time window | Apply the strongest bounded overlap and pacing stress test. |

Every profile only changes simulation controls. It never executes an attack, contacts a payment rail, or creates real credentials.

## API

### Discover valid options

```text
GET /evaluation-lab/options
```

### Run a campaign

```text
POST /evaluation-lab/campaigns
```

Example request:

```json
{
  "source_iteration_id": "iteration_027",
  "buckets": ["credential_based_fraud", "social_engineering_payment_fraud"],
  "difficulty_profiles": ["baseline", "elevated", "stealth_stress"],
  "seeds": [101, 202],
  "scenarios_per_card": 1,
  "benign_count": 100,
  "realism_profile": "overlap"
}
```

The result is written to:

```text
outputs/evaluation_campaigns/<campaign_id>/campaign.json
outputs/evaluation_campaigns/<campaign_id>/arms/<profile>_seed_<seed>/
```

### Retrieve evidence

```text
GET /evaluation-lab/campaigns
GET /evaluation-lab/campaigns/{campaign_id}
```

## Campaign evidence and lineage

Each saved campaign records the source iteration and frozen detector threshold; selected attack buckets and card count; exact profile definitions; seeds and sample settings; per-arm metrics; coverage cells with missed subtypes and representative misses; and a disclosure describing the synthetic, frozen-detector, no-LLM-review design.

A `monitor` or `weak` cell is a signal for human investigation. It can later become the starting point for a bounded red-team mutation proposal, rather than automatically changing generator behaviour.
