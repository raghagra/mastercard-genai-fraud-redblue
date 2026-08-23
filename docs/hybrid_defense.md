# Hybrid ML + GenAI Defense

The production-shaped defense is deliberately two-stage.

## Stage 1: Primary transaction scorer

The NumPy logistic-regression model scores every synthetic transaction. It is the fast path and remains responsible for high-volume screening, score thresholding, and baseline reason codes.

## Stage 2: Selective GenAI reviewer

The backend selects up to five transactions closest to the ML decision threshold in each loop iteration. This bounded budget makes the LLM a reviewer of ambiguous cases rather than a replacement for the payment-time scorer.

The review request contains:

- transaction reference,
- ML fraud score and threshold,
- ML reason codes,
- selected behavioral feature values.

It intentionally excludes the synthetic label, attack bucket, and attack subtype. The reviewer therefore cannot use generated ground truth to inflate evaluation results.

The response contract contains:

- semantic risk score,
- novelty score,
- recommendation: allow, review, step-up authentication, or flag,
- concise defensive rationale,
- risk indicators.

## Final decision

The hybrid score combines ML and semantic risk with a 70/30 weighting. A `flag` recommendation can also escalate the final decision. Scoring output preserves both ML-only and hybrid values so reports can compare them directly.

## Safety and reliability

Malformed or refusal-shaped model output is not allowed into a decision. The system substitutes a deterministic defensive review and retains fallback metadata in the usage ledger. The row-level ledger can later display the generation provider, ML decision, LLM review, fallback state, and final hybrid decision.

## Row-Level Provenance

The transaction evidence API resolves four distinct provenance layers for the web prototype:

1. **Generation provenance** — benign baseline, base attack card, or accepted runtime mutation; mutated scenarios include the originating mutation provider and fallback marker.
2. **Primary ML decision** — logistic-regression score, prediction, and reason codes.
3. **Selective LLM review** — whether the row was selected, provider, semantic risk, novelty, recommendation, rationale, and fallback state.
4. **Final hybrid decision** — final score, prediction, and decision engine.

This prevents an ambiguous claim such as “the LLM flagged the row.” The UI shows precisely whether the LLM influenced generation, reviewed the detection, both, or neither.
