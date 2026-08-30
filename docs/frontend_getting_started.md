# Frontend Getting Started

The web prototype is a React and Vite application in `frontend/`. It is the operational console for the existing FastAPI backend; it does not contain fraud-model logic or provider credentials.

## Prerequisites

- Python dependencies installed according to [Backend Getting Started](./backend_getting_started.md)
- Node.js 20 or later

## 1. Start the Backend

From the repository root, start the API in one terminal:

```bash
python3 -B -m src.cli.run_api --host 127.0.0.1 --port 8000
```

The API is available at `http://127.0.0.1:8000`, including interactive API documentation at `http://127.0.0.1:8000/docs`.

## 2. Install and Run the Frontend

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open `http://127.0.0.1:5173`.

The default frontend API target is `http://127.0.0.1:8000`. To point it at another backend, create `frontend/.env.local`:

```text
VITE_API_URL=https://your-api.example.com
```

## 3. What the Prototype Demonstrates

- **Mission control:** attack coverage, the closed-loop story, and current model signal.
- **Attack catalog:** browse all mapped attack vectors by fraud family.
- **Closed loop:** run an iteration with live stage status, inspect generated-record and detection metrics, review mutation candidates, and compare the latest two iterations.
- **Evaluation Lab:** sweep a frozen detector over selected fraud families, difficulty profiles, and reproducible seeds; inspect the coverage matrix and the evidence behind monitor/weak cells.
- **GenAI gateway:** choose local rules, LM Studio, AWS Bedrock, GCP Vertex AI, or Azure AI Foundry and submit a session-only configuration.
- **Portfolio onboarding:** load canonical CSV templates, validate authorized pseudonymized demo records, score upcoming transactions, and delete local demo data after use.

For the prototype, gateway configuration is deliberately stored only in backend memory. API keys are sent to the backend to make a request but are redacted from configuration responses. Refreshing or restarting the backend clears the session. Production storage should use the secret-management design in [GenAI Gateway](./genai_gateway.md).

## Closed-Loop UI Workflow

1. Open **Closed loop** and select **Run iteration**.
2. Follow the live stages: generation, feature construction, training, scoring, evaluation, failure analysis, and mutation proposal.
3. Select the completed iteration to inspect counts, F1, threshold, the lowest-confidence fraud groups, and the generated/scored synthetic payment records.
4. Review each proposed mutation as **Accept** or **Reject**.
5. Run a subsequent iteration using accepted mutations, then select **Compare latest** to view the metric deltas.

The local prototype keeps run status in backend memory. Restarting the API clears an in-progress job, but completed iteration artifacts remain under `outputs/iterations/`.

The run launcher supports a reproducible seed, benign-record count, simulated scenarios per attack card, and an optional prior iteration whose accepted mutations should be consumed. The transaction explorer supports filtering by label, attack family, and detector outcome. Select a transaction row to open the complete synthetic record, detector reason codes, and linked customer, merchant, device, and attack-scenario context.

The explorer is an analyst workbench: use **Columns** to show or hide analysis fields, click a column title to sort the complete filtered dataset, and filter by LLM-review status or decision engine in addition to fraud label, attack family, and final outcome.

In **GenAI gateway**, use **Save & test connection** after selecting LM Studio. The result must show `local_lmstudio` as the responding provider for the Mac-hosted model to be confirmed. If the result shows `local_rules` with fallback metadata, inspect the endpoint, model identifier, and LM Studio server state before running a GenAI-backed loop.

In **Portfolio onboarding**, run a recent closed-loop iteration before advisory scoring, then select that iteration as the detector model. The page is intentionally local-demo only; never upload direct PII or payment-instrument data. See [Local Portfolio Onboarding](./portfolio_onboarding.md) for the CSV contract.

In **Evaluation Lab**, first select a completed iteration that contains a frozen detector. The normal initial sweep is all five fraud families, three bounded difficulty profiles, and two deterministic seeds. A campaign evaluates its cells with row-level LLM review disabled, preserving comparable frozen-detector evidence. Select an amber `monitor` or red `weak` cell to inspect missed subtypes and representative misses, then use **Open closed loop** only to begin a human-governed follow-up—not to automatically modify the generator.

## 4. Verify a Production Build

```bash
cd frontend
npm run build
```

The static production bundle is written to `frontend/dist/`. A deployment environment can serve this bundle from any CDN or web server and configure `VITE_API_URL` at build time.

## Local Development Notes

The FastAPI application permits `localhost` and `127.0.0.1` development origins on any local port, including Vite's fallback port when `5173` is busy. Add your deployed UI origin to the backend CORS allow-list before a separate production deployment.
