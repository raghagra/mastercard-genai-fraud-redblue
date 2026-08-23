# Local Portfolio Onboarding and Advisory Scoring

This module lets the demo score a small, authorized, pseudonymized transaction portfolio against a detector trained by the closed-loop simulator.

## Scope and disclosure

This is a local demo capability, not a production data platform.

- Do not provide PAN, account numbers, CVV/CVC, names, email addresses, phone numbers, or addresses.
- Use stable pseudonymous values for `customer_id`, `merchant_id`, `device_id`, session, and IP identifiers.
- Each uploaded portfolio is stored only under `outputs/portfolio_datasets/` and can be explicitly deleted.
- Advisory scores are **not calibrated** to the uploaded portfolio until a labeled historical backtest is implemented.

## Input contract

The backend accepts two CSV payloads with the same flat schema:

- historical transactions: prior activity used to create behavioral state;
- upcoming transactions: records to score; labels are ignored even if accidentally provided.

Get empty templates through `GET /portfolio/template`.

Required columns:

```text
transaction_id,event_time,amount,currency,customer_id,merchant_id,
channel,rail,transaction_type,status
```

Useful optional columns:

```text
device_id,session_id,ip_address,billing_country,shipping_country,
merchant_category,payment_method_type,auth_result,risk_score,
customer_account_age_days,customer_historical_decline_rate,
customer_historical_spend_mean,merchant_age_days,merchant_refund_rate,
merchant_chargeback_rate,merchant_volume_growth_rate,
device_ip_reputation_score,device_first_seen_days_ago,device_failed_login_count
```

Historical files may additionally contain `label` (`0` or `1`) for a future backtest workflow. The current advisory scorer does not use it for prediction.

Missing optional values are replaced by an explicit `unknown` or numeric zero and recorded in the dataset’s data-quality report. Required fields are never silently invented.

## API workflow

1. `GET /portfolio/template` — retrieve empty historical and upcoming CSV templates.
2. `POST /portfolio/datasets` — create a local dataset by posting `dataset_name`, `historical_csv`, and `upcoming_csv` as JSON fields.
3. `GET /portfolio/datasets/{dataset_id}` — inspect its manifest and data-quality report.
4. `POST /portfolio/datasets/{dataset_id}/score` — score upcoming records. Supply an optional `model_iteration_id`; otherwise the newest loop model is selected.
5. `DELETE /portfolio/datasets/{dataset_id}` — delete local demo data after the session.

## GenAI data routing

GenAI review is off by default for uploaded records.

- A confirmed local route (`local_rules` or LM Studio at `localhost` / `127.0.0.1`) may be enabled without cloud acknowledgement.
- A remote or cloud route requires `cloud_data_acknowledged: true` on the score request. The response records the selected route and destination type.

This is a demo transparency guard. Production should replace it with DLP classification, provider allowlists, RBAC, consent/purpose controls, encryption, audit logs, and approved governed connectors.

## Future production replacement points

```text
JSON CSV-content API       -> governed lake / event-stream connector
local dataset folder       -> encrypted governed storage + retention policy
batch behavioral rebuild   -> online feature store / stream processor
acknowledgement flag       -> DLP/RBAC/audit policy enforcement
```
