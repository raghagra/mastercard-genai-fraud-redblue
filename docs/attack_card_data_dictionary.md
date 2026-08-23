# Attack Card Data Dictionary

This document defines every field in the `attack_card` schema, including:

- what it means,
- how it behaves in real payment/fraud systems,
- what type it should hold,
- why it matters for the solution.

## Field reference

### `attack_id`

- Type: `string`
- Meaning: Unique stable identifier for the attack card.
- Real-life shape: Short code or slug, often with a prefix and numeric suffix.
- Why it matters: Used for versioning, traceability, and linking generated instances back to the source attack card.

### `bucket`

- Type: `string`
- Meaning: Top-level fraud family.
- Real-life shape: One of the five project buckets.
- Why it matters: Organizes the taxonomy and helps evaluation across broad fraud classes.

### `subtype`

- Type: `string`
- Meaning: Concrete subfamily inside a bucket.
- Real-life shape: Examples include `card_not_present`, `business_email_compromise`, or `synthetic_identity`.
- Why it matters: Lets the system differentiate similar attacks and generate more varied scenarios.

### `attack_name`

- Type: `string`
- Meaning: Human-readable canonical name for the attack family.
- Real-life shape: Descriptive label used in reports and UI.
- Why it matters: Useful for documentation and presentation.

### `variant_name`

- Type: `string`
- Meaning: Specific scenario variant.
- Real-life shape: Fine-grained version of the attack with a particular twist or context.
- Why it matters: Prevents the generator from producing only one template per family.

### `channel`

- Type: `string`
- Meaning: The payment or interaction channel affected by the attack.
- Real-life shape: Examples include `ecommerce`, `mobile_app`, `email`, `bank_transfer`, `marketplace`, `call_center`.
- Why it matters: Channel drives features, behavior, and detection logic.

### `rail`

- Type: `string`
- Meaning: The payment rail or settlement path.
- Real-life shape: Examples include `card`, `ach`, `wire`, `upi`, `wallet`, `p2p`.
- Why it matters: Different rails have different fraud patterns and operational controls.

### `scope`

- Type: `string`
- Meaning: Whether the attack is a single event or a longer campaign.
- Real-life shape: A one-off transaction versus a multi-step sequence over time.
- Why it matters: Determines whether the detector should operate on transaction features or sequence features.

### `actor_type`

- Type: `string`
- Meaning: Who is carrying out the attack.
- Real-life shape: External fraudster, insider, mule, compromised merchant, or synthetic identity holder.
- Why it matters: Helps define behavior, access level, and likely signals.

### `attacker_goal`

- Type: `string`
- Meaning: The objective of the attack.
- Real-life shape: Unauthorized purchase, payment diversion, refund extraction, account takeover, laundering, or merchant cash-out.
- Why it matters: Useful for generation realism and for grouping attacks by intent.

### `genai_role`

- Type: `array[string]`
- Meaning: The ways GenAI assists the attack.
- Real-life shape: Message generation, impersonation, adaptive retries, fake document drafting, conversation steering.
- Why it matters: Makes the challenge explicitly about GenAI-enabled fraud rather than generic fraud.

### `preconditions`

- Type: `array[string]`
- Meaning: Conditions that must be true before the attack can happen.
- Real-life shape: Stolen credentials, weak onboarding controls, payment method availability, vulnerable refund process.
- Why it matters: Supports realistic scenario generation and helps the model distinguish feasible from infeasible attacks.

### `attack_sequence`

- Type: `array[object]`
- Meaning: Ordered steps of the attack.
- Real-life shape: Multi-step workflow such as lure, access, payment initiation, laundering, or refund abuse.
- Why it matters: This is the main structure for campaign simulation.

Each step object should contain:

- `step`: `integer`
- `action`: `string`
- `observable`: `string`

### `expected_signals`

- Type: `array[string]`
- Meaning: Behavioral or transactional signals the attack may leave behind.
- Real-life shape: Velocity spikes, device churn, beneficiary changes, risk-score jumps, payout anomalies.
- Why it matters: These signals become candidate features for the defense model.

### `data_fields_affected`

- Type: `array[string]`
- Meaning: Columns or entities likely impacted by the attack.
- Real-life shape: `amount`, `device_id`, `ip_address`, `billing_country`, `merchant_id`, `beneficiary_account`.
- Why it matters: Helps the generator know which fields to modify and helps the detector know where to look.

### `generation_strategy`

- Type: `object`
- Meaning: How synthetic examples should be created from the card.
- Real-life shape: Template-driven, stochastic, agent-based, or hybrid generation.
- Why it matters: Connects the attack definition to the simulator implementation.

Recommended fields inside `generation_strategy`:

- `mode`: `string`
- `stealth_level_range`: `array[number]`
- `volume_range`: `array[number]`
- `noise_level`: `string`

### `realism_score`

- Type: `number`
- Meaning: How plausible the attack is in real payment systems.
- Real-life shape: Usually between `0` and `1`.
- Why it matters: Helps prioritize the most credible attacks for simulation.

### `novelty_score`

- Type: `number`
- Meaning: How much GenAI changes or amplifies the attack.
- Real-life shape: Usually between `0` and `1`.
- Why it matters: Helps distinguish ordinary fraud from GenAI-enabled fraud.

### `detectability_score`

- Type: `number`
- Meaning: Estimated ease of detecting the attack.
- Real-life shape: Usually between `0` and `1`, where higher can mean easier detection.
- Why it matters: Useful for choosing hard-versus-easy scenarios and benchmarking detector strength.

### `impact_score`

- Type: `number`
- Meaning: Estimated damage if the attack succeeds.
- Real-life shape: Usually between `0` and `1`.
- Why it matters: Helps rank attacks by business risk.

### `severity`

- Type: `string`
- Meaning: Qualitative severity label.
- Real-life shape: `low`, `medium`, `high`, or `critical`.
- Why it matters: Makes the system easy to explain to non-technical stakeholders.

### `detection_hints`

- Type: `array[string]`
- Meaning: Suggested feature families or signals for the detector.
- Real-life shape: Velocity, graph, device, sequence, text, or anomaly features.
- Why it matters: Guides feature engineering and model experimentation.

### `evaluation_tags`

- Type: `array[string]`
- Meaning: Labels used to group attacks during analysis.
- Real-life shape: `high_value`, `rapid_sequence`, `first_party`, `online_payment`.
- Why it matters: Helps slice evaluation results and compare model behavior across segments.

### `notes`

- Type: `string`
- Meaning: Free-form human notes.
- Real-life shape: Short clarifications, assumptions, or implementation reminders.
- Why it matters: Keeps context attached to the card without changing the schema.

## Practical typing guidance

- Use `string` for identifiers, labels, and descriptive text.
- Use `array[string]` for lists of signals, steps, or conditions.
- Use `number` for normalized scores.
- Use `object` for grouped configuration or sequence steps.
- Use `integer` for step indices and counters.

## Suggested real-life normalization

For this solution, scores should usually be normalized to `0..1` so they can be compared and plotted easily.

## Why the data dictionary matters

The generator and detector will both depend on these definitions.

- If a field is poorly defined, synthetic data will drift.
- If a field is too vague, the detector will learn weak patterns.
- If the data types are stable, the whole system stays reproducible.

