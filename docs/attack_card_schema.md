# Attack Card Schema

An `attack_card` is the core unit of the system. It describes one fraud pattern in a structured way so that:

- the identify module can store and rank attack ideas,
- the generate module can simulate them,
- the defend module can learn from the synthetic outputs,
- the UI can present the attack clearly.

The schema is intentionally designed for defensive simulation and fraud research.

## Top-level structure

```json
{
  "attack_id": "cred_cnp_001",
  "bucket": "credential_based_fraud",
  "subtype": "card_not_present",
  "attack_name": "card_not_present_fraud",
  "variant_name": "stolen_card_checkout_with_velocity",
  "channel": "ecommerce",
  "rail": "card",
  "scope": "single_event",
  "actor_type": "external_fraudster",
  "attacker_goal": "complete unauthorized purchase",
  "genai_role": [
    "phishing_copy_generation",
    "checkout_behavior_mimicry",
    "adaptive_retry_logic"
  ],
  "preconditions": [
    "stolen payment credentials available",
    "checkout flow accepts CNP payments"
  ],
  "attack_sequence": [
    {
      "step": 1,
      "action": "acquire credentials",
      "observable": "credential source unknown"
    }
  ],
  "expected_signals": [
    "high auth velocity",
    "device mismatch",
    "ip churn"
  ],
  "data_fields_affected": [
    "amount",
    "merchant_category",
    "ip_address",
    "device_id"
  ],
  "generation_strategy": {
    "mode": "template_plus_sampling",
    "stealth_level_range": [0.4, 0.8],
    "volume_range": [5, 50],
    "noise_level": "medium"
  },
  "realism_score": 0.82,
  "novelty_score": 0.64,
  "detectability_score": 0.41,
  "impact_score": 0.87,
  "severity": "high",
  "detection_hints": [
    "velocity_features",
    "device_graph_features"
  ],
  "evaluation_tags": [
    "high_value",
    "rapid_sequence",
    "online_payment"
  ],
  "notes": "Synthetic simulation only"
}
```

## Required fields

The minimum viable card should include:

- `attack_id`
- `bucket`
- `subtype`
- `attack_name`
- `variant_name`
- `channel`
- `rail`
- `scope`
- `actor_type`
- `attacker_goal`
- `preconditions`
- `attack_sequence`
- `expected_signals`
- `data_fields_affected`
- `generation_strategy`
- `severity`

## Optional but strongly recommended fields

- `genai_role`
- `realism_score`
- `novelty_score`
- `detectability_score`
- `impact_score`
- `detection_hints`
- `evaluation_tags`
- `notes`

## Design principles

- Keep the card human-readable.
- Keep it machine-parseable.
- Keep generation and detection fields separate.
- Prefer stable enums for bucket, channel, rail, scope, and severity.
- Use arrays for fields that may contain multiple values in real life.

## Suggested enums

```text
bucket:
  credential_based_fraud
  social_engineering_payment_fraud
  identity_onboarding_fraud
  post_transaction_abuse
  merchant_ecosystem_abuse

scope:
  single_event
  multi_step_campaign

severity:
  low
  medium
  high
  critical
```

## Why this schema exists

This schema creates a bridge between research and implementation.

- It gives the identify module a common language for fraud ideas.
- It gives the generator a parameterized input format.
- It gives the detector structured labels and signal hints.
- It gives the prototype a consistent display model.

