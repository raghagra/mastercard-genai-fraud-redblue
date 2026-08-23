# Attack Catalog

This catalog expands the five core fraud buckets into concrete simulation-ready variants.

Each entry is written at a defensive level:

- enough detail to generate realistic examples,
- enough signal context to support detection,
- not enough operational detail to help misuse.

## 1. Credential-based fraud

### 1.1 Card-not-present fraud

- Bucket: `credential_based_fraud`
- Subtype: `card_not_present`
- Channel: `ecommerce`, `mobile_app`
- Rail: `card`
- Scope: `single_event`
- GenAI role: adaptive message generation, phishing copy variation, checkout mimicry
- Common signals:
  - bursty authorization attempts
  - device churn
  - IP reputation shifts
  - billing and shipping mismatch
  - unusual checkout timing

### 1.2 Card testing and enumeration

- Bucket: `credential_based_fraud`
- Subtype: `card_testing`
- Channel: `ecommerce`, `api`
- Rail: `card`
- Scope: `single_event`
- GenAI role: adaptive retry logic, template variation, automated response handling
- Common signals:
  - many low-value authorization attempts
  - repeated declines
  - same source infrastructure across many cards
  - short-lived sessions

### 1.3 Consumer account takeover

- Bucket: `credential_based_fraud`
- Subtype: `consumer_account_takeover`
- Channel: `mobile_app`, `wallet`, `ecommerce`
- Rail: `card`, `wallet`
- Scope: `multi_step_campaign`
- GenAI role: phishing copy generation, impersonation, support-chat scripting
- Common signals:
  - login location change
  - device swap
  - password reset followed by payment action
  - new beneficiary or card edits

### 1.4 Merchant or admin account takeover

- Bucket: `credential_based_fraud`
- Subtype: `merchant_admin_takeover`
- Channel: `merchant_portal`, `api`
- Rail: `card`, `ach`, `wire`
- Scope: `multi_step_campaign`
- GenAI role: internal impersonation, support-response drafting, social engineering
- Common signals:
  - privileged login anomalies
  - payout changes
  - bank account edits
  - sudden policy or refund setting changes

### 1.5 Credential stuffing on payment-linked accounts

- Bucket: `credential_based_fraud`
- Subtype: `credential_stuffing`
- Channel: `ecommerce`, `mobile_app`, `wallet`
- Rail: `card`, `wallet`
- Scope: `single_event`
- GenAI role: retry orchestration, adaptive pacing, message diversification
- Common signals:
  - high login failure ratio
  - repeated credential reuse
  - distributed IP patterns
  - automation-like request timing

## 2. Social-engineering payment fraud

### 2.1 Business email compromise

- Bucket: `social_engineering_payment_fraud`
- Subtype: `business_email_compromise`
- Channel: `email`
- Rail: `wire`, `ach`
- Scope: `multi_step_campaign`
- GenAI role: email drafting, tone imitation, invoice rewriting
- Common signals:
  - new or changed beneficiary
  - domain impersonation
  - urgency language
  - invoice metadata mismatch

### 2.2 Fake invoice or vendor rerouting

- Bucket: `social_engineering_payment_fraud`
- Subtype: `vendor_rerouting`
- Channel: `email`, `api`
- Rail: `wire`, `ach`
- Scope: `multi_step_campaign`
- GenAI role: invoice generation, vendor-role impersonation, reply-chain continuation
- Common signals:
  - changed bank details
  - altered invoice formatting
  - vendor-contact mismatch
  - unusual payment destination

### 2.3 Executive impersonation

- Bucket: `social_engineering_payment_fraud`
- Subtype: `executive_impersonation`
- Channel: `email`, `call_center`, `chat`
- Rail: `wire`, `ach`
- Scope: `multi_step_campaign`
- GenAI role: high-fidelity messaging, voice-like text, urgency scripting
- Common signals:
  - unusual request timing
  - bypass of normal approval chain
  - off-channel urgency
  - repeated escalation pressure

### 2.4 Authorized push payment scam

- Bucket: `social_engineering_payment_fraud`
- Subtype: `authorized_push_payment_scam`
- Channel: `bank_transfer`, `mobile_app`
- Rail: `instant_transfer`, `p2p`
- Scope: `multi_step_campaign`
- GenAI role: conversational manipulation, trust-building messages, objection handling
- Common signals:
  - recipient novelty
  - emotional pressure
  - rapid transfer initiation after contact
  - repeated transfers to related accounts

### 2.5 AI voice or chat impersonation

- Bucket: `social_engineering_payment_fraud`
- Subtype: `ai_impersonation`
- Channel: `call_center`, `chat`, `email`
- Rail: `wire`, `ach`, `card`
- Scope: `multi_step_campaign`
- GenAI role: conversational mimicry, scripted escalation, contextual reply generation
- Common signals:
  - identity switching across channels
  - unusual request wording
  - atypical support interaction paths
  - payment request after trust establishment

## 3. Identity / onboarding fraud

### 3.1 Synthetic identity

- Bucket: `identity_onboarding_fraud`
- Subtype: `synthetic_identity`
- Channel: `onboarding`
- Rail: `card`, `wallet`
- Scope: `multi_step_campaign`
- GenAI role: profile generation, identity narrative creation, document drafting
- Common signals:
  - weak identity lineage
  - inconsistent personal attributes
  - thin-file behavior
  - repeated contact or address reuse

### 3.2 Synthetic business or shell company

- Bucket: `identity_onboarding_fraud`
- Subtype: `synthetic_business`
- Channel: `merchant_portal`, `onboarding`
- Rail: `card`, `ach`, `wire`
- Scope: `multi_step_campaign`
- GenAI role: business-description generation, website copy, registration text drafting
- Common signals:
  - short business age
  - reused contact information
  - inconsistent business profile fields
  - rapid activity ramp after approval

### 3.3 Mule account creation

- Bucket: `identity_onboarding_fraud`
- Subtype: `mule_account_creation`
- Channel: `onboarding`, `mobile_app`
- Rail: `p2p`, `wallet`, `card`
- Scope: `multi_step_campaign`
- GenAI role: recruitment messaging, onboarding scripting, support conversation drafting
- Common signals:
  - clustered signups
  - similar device or IP lineage
  - rapid fund movement after activation
  - repeated beneficiary churn

### 3.4 Fraudulent merchant onboarding

- Bucket: `identity_onboarding_fraud`
- Subtype: `fraudulent_merchant_onboarding`
- Channel: `merchant_portal`
- Rail: `card`, `ach`
- Scope: `multi_step_campaign`
- GenAI role: website copy, business story generation, form-filling assistance
- Common signals:
  - mismatch between claimed business and observed activity
  - suspicious descriptor data
  - unusually fast activation to volume growth
  - inconsistent contact and payout details

### 3.5 Stolen identity sign-up fraud

- Bucket: `identity_onboarding_fraud`
- Subtype: `stolen_identity_signup`
- Channel: `onboarding`
- Rail: `card`, `wallet`
- Scope: `multi_step_campaign`
- GenAI role: profile blending, application completion, interaction scripting
- Common signals:
  - cross-field inconsistency
  - identity reuse across accounts
  - document or address mismatch
  - unusual onboarding completion path

## 4. Post-transaction abuse

### 4.1 Chargeback fraud

- Bucket: `post_transaction_abuse`
- Subtype: `chargeback_fraud`
- Channel: `ecommerce`
- Rail: `card`
- Scope: `multi_step_campaign`
- GenAI role: dispute narrative generation, claim refinement, evidence framing
- Common signals:
  - dispute frequency
  - buyer-history mismatch
  - pattern of claims after delivery
  - high refund-to-purchase ratio

### 4.2 Non-delivery claim abuse

- Bucket: `post_transaction_abuse`
- Subtype: `non_delivery_claim`
- Channel: `customer_support`, `ecommerce`
- Rail: `card`, `wallet`
- Scope: `multi_step_campaign`
- GenAI role: complaint drafting, escalation scripting, support chat imitation
- Common signals:
  - claims after delivery confirmation
  - repeated missing-item stories
  - policy-edge behavior
  - support-channel escalation

### 4.3 Refund fraud

- Bucket: `post_transaction_abuse`
- Subtype: `refund_fraud`
- Channel: `customer_support`
- Rail: `card`, `wallet`
- Scope: `multi_step_campaign`
- GenAI role: refund request drafting, policy language mimicry
- Common signals:
  - repeated refund claims
  - refund destination shifts
  - abnormal refund timing
  - inconsistent return reasons

### 4.4 Alternative refund abuse

- Bucket: `post_transaction_abuse`
- Subtype: `alternative_refund_abuse`
- Channel: `customer_support`
- Rail: `card`, `wallet`, `bank_transfer`
- Scope: `multi_step_campaign`
- GenAI role: conversation steering, explanation generation, method-switch requests
- Common signals:
  - request to change refund destination
  - account mismatch
  - sudden policy exceptions
  - unusual customer-service pathing

### 4.5 Return policy abuse

- Bucket: `post_transaction_abuse`
- Subtype: `return_policy_abuse`
- Channel: `ecommerce`, `marketplace`
- Rail: `card`
- Scope: `multi_step_campaign`
- GenAI role: return-story generation, persuasion copy, escalation scripts
- Common signals:
  - repeat returns
  - item-condition mismatch
  - policy boundary exploitation
  - returns clustered by account or household

## 5. Merchant / ecosystem abuse

### 5.1 Triangulation fraud

- Bucket: `merchant_ecosystem_abuse`
- Subtype: `triangulation_fraud`
- Channel: `marketplace`, `ecommerce`
- Rail: `card`
- Scope: `multi_step_campaign`
- GenAI role: storefront text generation, customer messaging, fulfillment concealment
- Common signals:
  - seller-buyer-fulfillment mismatch
  - inconsistent shipping origin
  - unusual order routing
  - complaints after delivery

### 5.2 Bust-out or flash merchant fraud

- Bucket: `merchant_ecosystem_abuse`
- Subtype: `bust_out_merchant`
- Channel: `merchant_portal`
- Rail: `card`, `ach`, `wire`
- Scope: `multi_step_campaign`
- GenAI role: merchant branding, website content, staged communication
- Common signals:
  - rapid merchant growth
  - short account age
  - cash-out behavior
  - sudden descriptor or payout anomalies

### 5.3 Marketplace seller fraud

- Bucket: `merchant_ecosystem_abuse`
- Subtype: `marketplace_seller_fraud`
- Channel: `marketplace`
- Rail: `card`
- Scope: `multi_step_campaign`
- GenAI role: listing generation, review manipulation, customer chat scripting
- Common signals:
  - fake review patterns
  - high dispute clusters
  - delivery inconsistency
  - seller reputation drift

### 5.4 Gift card abuse

- Bucket: `merchant_ecosystem_abuse`
- Subtype: `gift_card_abuse`
- Channel: `retail`, `digital`
- Rail: `card`, `wallet`
- Scope: `multi_step_campaign`
- GenAI role: support impersonation, account recovery scripting, social engineering
- Common signals:
  - activation/drain bursts
  - abnormal redemption timing
  - repeated account recovery requests
  - channel-switch behavior

### 5.5 Mule laundering

- Bucket: `merchant_ecosystem_abuse`
- Subtype: `mule_laundering`
- Channel: `bank_transfer`, `p2p`
- Rail: `p2p`, `instant_transfer`, `ach`
- Scope: `multi_step_campaign`
- GenAI role: coordination messaging, recruitment copy, transaction narrative generation
- Common signals:
  - many inbound sources
  - rapid outflow
  - circular flows
  - account network clustering

## How to use this catalog

- Use it as the source for `attack_card` records.
- Use each entry as a template seed for scenario generation.
- Use `expected_signals` and `common_signals` as feature hints for the defense model.
- Use the bucket and subtype hierarchy to analyze coverage and diversity.

## Suggested coverage target

To start, aim for:

- 5 buckets
- 5 attack patterns per bucket
- 2 to 4 variants per pattern

That gives you enough breadth for a strong synthetic benchmark without making the system too large to manage.

