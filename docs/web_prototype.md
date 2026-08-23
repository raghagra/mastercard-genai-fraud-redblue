# Web Prototype

This document describes the working UI prototype that will demonstrate the closed-loop system.

The prototype should make the solution understandable in a few minutes.

## Prototype goals

- show the attack catalog,
- let the user generate synthetic fraud,
- show the detector output,
- surface explanations and metrics,
- make the feedback loop visible.

## Suggested views

### 1. Attack catalog view

Purpose:

- browse the 5 fraud buckets and their patterns.

Should show:

- bucket
- subtype
- severity
- realism score
- novelty score

### 2. Scenario generation view

Purpose:

- create synthetic attack runs interactively.

Should show:

- selected attack
- seed
- intensity
- stealth
- number of generated records

### 3. Synthetic data explorer

Purpose:

- inspect generated records.

Should show:

- transaction table
- entity context
- labels
- attack metadata

### 4. Detector results view

Purpose:

- score generated records and show outcomes.

Should show:

- fraud score
- predicted label
- explanation
- threshold status

### 5. Feedback loop view

Purpose:

- demonstrate that misses can drive improvements.

Should show:

- false positives
- false negatives
- suggested attack refinements
- retraining impact

The implemented review cards also expose the benchmark scope, trigger, miss/recall evidence, and representative weak records that caused a human review to be requested. This makes the human governance point explicit: people approve or reject the next attack variant, not every individual transaction.

Mutation-parameter labels include hover definitions so a reviewer can interpret controls such as stealth range, volume range, campaign duration, and noise without leaving the screen. The synthetic-record search applies while the user types, and the iteration browser is paginated with newest runs first.

The closed-loop view includes a native SVG iteration-trends chart for the latest 12 runs. It tracks F1, recall, and false-positive rate together: this keeps the demo focused on the core defence trade-off, rather than presenting F1 without the false-positive context.

### 6. Portfolio onboarding view

Purpose:

- demonstrate local, pseudonymized historical-data onboarding and advisory scoring.

The view loads CSV templates, accepts historical and upcoming transaction files, surfaces local-demo warnings and validation output, scores upcoming records against a selected iteration model, and provides an explicit deletion control. GenAI review is opt-in; remote/cloud routing requires acknowledgement.

## UX principles

- Keep the layout simple and polished.
- Make the flow obvious from left to right or top to bottom.
- Use charts and tables only where they improve clarity.
- Highlight the closed-loop story visually.

## Demo storyline

The ideal demo flow is:

1. Pick an attack family.
2. Generate a synthetic scenario.
3. Inspect the generated data.
4. Run the detector.
5. See the explanation and metric impact.
6. Feed misses back into the generator.

## Why the prototype matters

The prototype is the quickest way to communicate that the project is not just a model, but a system.
