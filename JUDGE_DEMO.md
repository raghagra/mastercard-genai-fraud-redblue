# Judge demo

SentinelLoop includes a one-command, local-first demonstration launcher. It is designed to let a judge explore the working product without manually starting services or configuring a GenAI account.

## Run it

From the repository root, after the normal Python and frontend dependency installation:

```bash
python3 scripts/judge_demo.py
```

The launcher:

1. checks the required Python and Node dependencies;
2. validates the attack catalogue;
3. creates a deterministic two-iteration fixture: a source run, then a candidate run that consumes its accepted bounded mutations;
4. starts the FastAPI API at `http://127.0.0.1:8000`;
5. starts the React console at `http://127.0.0.1:5173`; and
6. prints a short walkthrough in the terminal.

Press `Ctrl+C` in that terminal to stop both local services.

The default uses the deterministic `local_rules` provider. It makes no cloud calls, does not require LM Studio, and does not use payment credentials or real payment records.

## Useful options

```bash
# Create the reproducible fixture only; do not start the services.
python3 scripts/judge_demo.py --prepare-only

# Start the services without creating additional iterations.
python3 scripts/judge_demo.py --skip-prepare

# Use the current repository GenAI configuration, such as a running local LM Studio server.
python3 scripts/judge_demo.py --provider current

# Run the backend tests and production frontend build.
python3 scripts/judge_demo.py --verify
```

If ports `8000` or `5173` are already in use, stop the existing service or supply `--api-port` and `--ui-port` values.

## What to demonstrate

1. **Mission control:** the five research-backed fraud families and latest detection signal.
2. **Closed loop:** generated attacks, measured detection outcomes, failure analysis, human-reviewed mutation proposals, and a later run that consumes accepted proposals.
3. **Transaction evidence:** filter the synthetic-payment table by model review, decision engine, or outcome.
4. **Human governance:** show the evidence and bounded deltas that require approval before a mutation affects the next run.
5. **Portfolio onboarding:** show the sample CSV contract and the explicit synthetic/pseudonymized-data boundary.

The prepared acceptance records are explicitly labelled `judge_demo_fixture`. They exist solely to make the whole feedback loop visible immediately; in a real evaluation, a reviewer accepts or rejects each candidate through the console.
