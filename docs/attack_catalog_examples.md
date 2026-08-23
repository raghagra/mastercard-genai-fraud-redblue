# Attack Catalog Examples

These are starter examples for the five bucket structure. They are intentionally written as defensive simulation cards, not operational attack instructions.

## 1. Credential-based fraud

### Card-not-present fraud

- Bucket: `credential_based_fraud`
- Subtype: `card_not_present`
- Channel: `ecommerce`
- Rail: `card`
- Scope: `single_event`
- Signals: high auth velocity, device churn, billing/shipping mismatch

### Account takeover

- Bucket: `credential_based_fraud`
- Subtype: `account_takeover`
- Channel: `mobile_app`
- Rail: `wallet`
- Scope: `multi_step_campaign`
- Signals: device change, login anomaly, payment method edits

## 2. Social-engineering payment fraud

### Business email compromise

- Bucket: `social_engineering_payment_fraud`
- Subtype: `business_email_compromise`
- Channel: `email`
- Rail: `wire`
- Scope: `multi_step_campaign`
- Signals: new payee, invoice mismatch, urgency language, beneficiary change

### Authorized push payment scam

- Bucket: `social_engineering_payment_fraud`
- Subtype: `authorized_push_payment_scam`
- Channel: `bank_transfer`
- Rail: `instant_transfer`
- Scope: `multi_step_campaign`
- Signals: recipient novelty, emotional pressure, unusual transfer cadence

## 3. Identity / onboarding fraud

### Synthetic identity

- Bucket: `identity_onboarding_fraud`
- Subtype: `synthetic_identity`
- Channel: `onboarding`
- Rail: `card` or `wallet`
- Scope: `multi_step_campaign`
- Signals: weak lineage, inconsistent profile, thin-file behavior

### Fraudulent merchant onboarding

- Bucket: `identity_onboarding_fraud`
- Subtype: `fraudulent_merchant_onboarding`
- Channel: `merchant_portal`
- Rail: `card`
- Scope: `multi_step_campaign`
- Signals: entity mismatch, short merchant age, suspicious activity ramp

## 4. Post-transaction abuse

### Refund fraud

- Bucket: `post_transaction_abuse`
- Subtype: `refund_fraud`
- Channel: `customer_support`
- Rail: `card`
- Scope: `multi_step_campaign`
- Signals: repeated refund claims, destination changes, dispute clustering

### Chargeback fraud

- Bucket: `post_transaction_abuse`
- Subtype: `chargeback_fraud`
- Channel: `ecommerce`
- Rail: `card`
- Scope: `multi_step_campaign`
- Signals: customer history mismatch, excessive dispute frequency

## 5. Merchant / ecosystem abuse

### Triangulation fraud

- Bucket: `merchant_ecosystem_abuse`
- Subtype: `triangulation_fraud`
- Channel: `marketplace`
- Rail: `card`
- Scope: `multi_step_campaign`
- Signals: fulfillment mismatch, buyer/seller network inconsistency

### Mule laundering

- Bucket: `merchant_ecosystem_abuse`
- Subtype: `mule_laundering`
- Channel: `bank_transfer`
- Rail: `p2p`
- Scope: `multi_step_campaign`
- Signals: many inbound sources, rapid outflow, circular transfer flow

