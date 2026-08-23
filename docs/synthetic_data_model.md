# Synthetic Data Model

This document defines the record-level data model that the generator will produce and the detector will consume.

The goal is to simulate payment behavior that is:

- realistic enough to resemble live payment systems,
- structured enough to train models,
- flexible enough to represent multiple fraud families.

## Design goals

- Support both benign and fraudulent records.
- Support single-event and multi-step campaign behavior.
- Capture transaction, entity, device, and behavioral context.
- Preserve reproducibility through seeded generation.
- Keep the schema compact enough for a fast prototype, but extensible for later work.

## Core record types

The system should support at least these record types:

- `transaction_record`
- `user_profile_record`
- `merchant_profile_record`
- `device_session_record`
- `attack_instance_record`
- `label_record`

For the first implementation, the most important record is `transaction_record`, with linked metadata from the other record types.

## Primary transaction record schema

The canonical synthetic payment record should look like this:

```json
{
  "transaction_id": "txn_001",
  "event_time": "2026-08-17T10:15:30Z",
  "amount": 124.50,
  "currency": "USD",
  "channel": "ecommerce",
  "rail": "card",
  "transaction_type": "purchase",
  "status": "approved",
  "customer_id": "cust_123",
  "merchant_id": "m_456",
  "device_id": "dev_789",
  "session_id": "sess_001",
  "ip_address": "203.0.113.10",
  "billing_country": "US",
  "shipping_country": "US",
  "merchant_category": "digital_goods",
  "payment_method_type": "debit_card",
  "auth_result": "approved",
  "risk_score": 0.18,
  "simulation_segment": "routine_benign",
  "label": 0,
  "attack_id": null,
  "attack_bucket": null,
  "attack_subtype": null
}
```

## Transaction fields

### Identity and timing

- `transaction_id`: unique identifier for the event.
- `event_time`: timestamp for ordering and sequence analysis.
- `session_id`: session grouping identifier.

These are essential for sequence-based fraud analysis and velocity features.

### Payment context

- `amount`: monetary value of the transaction.
- `currency`: transaction currency.
- `channel`: payment or interaction channel.
- `rail`: payment rail.
- `transaction_type`: purchase, refund, transfer, payout, login, etc.
- `status`: approved, declined, pending, reversed, refunded.
- `auth_result`: low-level authorization result if applicable.
- `payment_method_type`: card type, wallet, bank account, or other instrument class.

These fields define the business action being simulated.

### Entity linkage

- `customer_id`: synthetic customer identity.
- `merchant_id`: synthetic merchant identity.
- `device_id`: synthetic device fingerprint.
- `ip_address`: source network indicator.

These fields let the detector build behavioral and graph-based signals.

### Geography and merchant context

- `billing_country`
- `shipping_country`
- `merchant_category`

These are useful for mismatch detection, anomaly scoring, and merchant profiling.

### Labels and attack metadata

- `label`: `0` for benign, `1` for fraud.
- `attack_id`: linked attack card identifier when fraudulent.
- `attack_bucket`: top-level fraud bucket.
- `attack_subtype`: concrete attack pattern.

These fields connect the synthetic record back to the attack catalog.

### Risk output

- `risk_score`: optional pre-model or heuristic score used during generation or simulation.

This field is useful for stress-testing and for producing separable but realistic examples.

### Simulation provenance

- `simulation_segment`: generator-only provenance describing the behavior regime. Current values are `routine_benign`, `atypical_benign`, `stealth_fraud`, and `overt_fraud`.

This field is deliberately **not** passed to the detector. It supports fidelity analysis: a good defense should not equate an unusual but legitimate purchase with fraud, and should still find stealthy fraud whose ordinary signals overlap with legitimate traffic.

## Realism profiles

`generate_dataset` and the loop accept a `realism_profile`:

- `baseline`: cleaner separation, useful for smoke tests and demonstrations.
- `overlap` (default): introduces controlled overlap between fraud and benign activity. Some legitimate rows have high amounts, cross-border shipping, or declines; high-stealth fraud has less obvious geography, mature-looking entity/device context, and a less extreme upstream risk signal.

The profile is written to `generation_summary.json` and `loop_summary.json`. This is intentional stress testing, not a claim that the synthetic distributions match a particular issuer's production portfolio. Production calibration requires authorized historical reference data and privacy review.

## Supporting linked records

The transaction record should be supported by context tables or companion objects.

### User profile record

Typical fields:

- `customer_id`
- `age_band`
- `tenure_days`
- `account_age_days`
- `home_country`
- `email_domain`
- `phone_type`
- `kyc_level`
- `historical_spend_mean`
- `historical_spend_std`
- `historical_decline_rate`

Why it matters:

- supports identity checks,
- supports behavioral baselines,
- helps model thin-file or synthetic identity patterns.

### Merchant profile record

Typical fields:

- `merchant_id`
- `merchant_category`
- `merchant_age_days`
- `country`
- `payout_account_age_days`
- `refund_rate`
- `chargeback_rate`
- `average_ticket_size`
- `volume_growth_rate`
- `risk_tier`

Why it matters:

- supports merchant abuse simulation,
- supports fraud concentration analysis,
- supports merchant lifecycle anomaly detection.

### Device session record

Typical fields:

- `device_id`
- `session_id`
- `browser_family`
- `os_family`
- `device_type`
- `ip_country`
- `ip_reputation_score`
- `first_seen_days_ago`
- `session_duration_seconds`
- `failed_login_count`

Why it matters:

- supports account takeover and credential-based fraud detection,
- helps with session continuity and device drift features.

### Attack instance record

Typical fields:

- `attack_instance_id`
- `attack_id`
- `bucket`
- `subtype`
- `scenario_seed`
- `attack_intensity`
- `stealth_level`
- `generated_record_ids`

Why it matters:

- links one attack card to one concrete simulation run,
- enables reproducibility and evaluation by scenario.

## Field typing guide

### String fields

Use for:

- identifiers,
- labels,
- categories,
- countries,
- channels,
- rails,
- statuses.

Examples:

- `transaction_id`
- `customer_id`
- `merchant_category`
- `currency`

### Numeric fields

Use for:

- monetary values,
- risk scores,
- rates,
- counts,
- durations.

Examples:

- `amount`
- `risk_score`
- `historical_decline_rate`
- `session_duration_seconds`

### Timestamp fields

Use ISO 8601 timestamps for:

- `event_time`

This makes ordering and time-window feature engineering much easier.

### Boolean / binary labels

Use for:

- `label`

In the first version, `0` should mean benign and `1` should mean fraud.

## Recommended feature families for the defender

The detector will likely need features derived from the raw records.

### Transaction features

- amount deviation
- transaction type frequency
- channel usage
- merchant category risk
- decline-to-approval ratios

### Customer behavior features

- spend velocity
- login or checkout cadence
- account age
- country drift
- repeat beneficiary patterns

### Merchant features

- refund rate
- chargeback rate
- sudden volume increases
- merchant age

### Device and network features

- device reuse
- IP reputation
- IP geography mismatch
- session instability

### Sequence features

- repeated actions in a short window
- event ordering
- time gaps between steps
- transition patterns from login to payment to refund

## Synthetic generation rules

The generator should obey these rules:

- Every fraudulent record must map to a known `attack_card`.
- Every record should have a plausible timestamp.
- Values should remain internally consistent across linked entities.
- Fraudulent data should not look obviously fake.
- Legitimate baseline data should be generated alongside fraud so the detector learns separation.

## Recommended dataset layout

For a first implementation, use a folder or table structure like:

- `transactions`
- `customers`
- `merchants`
- `devices`
- `attack_instances`
- `labels`

This can be implemented as CSVs, JSONL files, or relational tables.

## Why this model matters

This model is the handshake between the generator and the defender.

- The generator needs a target schema to fill.
- The detector needs consistent fields to learn from.
- The feedback loop needs stable identifiers to track failures.

If this schema is unstable, the whole closed-loop system becomes hard to reproduce.
