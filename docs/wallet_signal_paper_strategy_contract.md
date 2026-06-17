# Wallet Signal Paper Strategy Contract V1

## 1. Status

- WP: WP83 (wallet signal paper strategy contract docs/schema/tests-only)
- Package class: DOCS_SCHEMA_TESTS_ONLY_WALLET_SIGNAL_PAPER_STRATEGY_CONTRACT
- Authority: DESIGN_ONLY
- NOT_AUTHORIZATION
- NO_RUNTIME_CHANGE
- NO_TOOLS_CHANGE
- NO_DEPENDENCY_CHANGE
- NO_NETWORK
- NO_TRADING_EXECUTION
- NO_PAPER_TRADING
- NO_HERMES_RUNTIME
- NO_AGENT_RUNTIME
- NO_CREDENTIALS
- NO_SCHEDULER
- NO_BOT_LOOP
- WP83 merge commit: TO_BE_RECORDED_AFTER_MERGE

## 2. Purpose

This document defines the contract for a wallet-signal paper strategy research
candidate record. A wallet-signal paper strategy contract record is a research
queue advisory record only.

Plain analogy:

```text
WP81 built the local copyability delay evaluator.
WP82 built the local analyst report generator.
WP83 defines the rulebook for when a wallet-signal idea may be considered
for a paper-only research strategy later.

It is like saying:
"This scout report is good enough to discuss in the simulator room."

It does not build the simulator.
It does not create allocation instructions.
It does not set amounts.
It does not connect credentials.
It does not do any account activity.
```

Wallet-signal paper strategy contract records are advisory research queue
records only. They may identify a wallet-signal idea that is eligible for
future paper-only strategy design review. They are not strategy instructions,
not allocation records, not order records, and not authorization of any
implementation.

## 3. Required Contract Sections

A wallet-signal paper strategy contract record must contain all of the following
sections:

### 3.1 contract_identity

```text
contract_id              — a unique contract record identifier
contract_type            — must be WALLET_SIGNAL_PAPER_STRATEGY_CONTRACT_V1
contract_created_at      — timestamp of record creation
wp_version               — the WP under which the record was created
advisory_only_notice     — must be present and non-empty
design_example_only      — true if this is a design example
```

### 3.2 source_report_reference

Local/offline source record IDs only. Must include:

```text
wallet_intelligence_report_id
wallet_signal_profile_ids
copyability_delay_evaluation_ids
research_queue_annotation_ids
human_review_label_ids
local_fixture_set_id
source_reference_advisory
```

No raw external data, no raw API response, no real wallet address required.
Use placeholder IDs only in design examples.

### 3.3 source_signal_context

Advisory research labels derived from WP79/WP81/WP82 records only. May include:

```text
wallet_id_placeholder
market_id_placeholder
condition_id_placeholder
signal_category_label
profitability_advisory_label
specialization_advisory_label
copyability_advisory_label
advisory_only_notice
```

### 3.4 copyability_delay_context

Advisory copyability context from WP81 evaluator records. Must include:

```text
copyability_delay_evaluation_id
delay_window_label
copyability_advisory_status
advisory_only_notice
```

### 3.5 eligibility_review

Eligibility gate result summary. Must include:

```text
eligibility_status
eligibility_gate_results
advisory_only_notice
```

### 3.6 suspicious_flow_review

Suspicious flow gate results. Must include:

```text
suspicious_flow_detected
suspicious_flow_records
advisory_only_notice
```

### 3.7 insufficient_context_review

Insufficient context gate results. Must include:

```text
insufficient_context_warnings
context_completeness_label
advisory_only_notice
```

### 3.8 human_review

Human review gate and label references. Must include:

```text
human_review_required
human_review_label_ids
human_review_advisory_note
advisory_only_notice
```

### 3.9 deferred_items

Explicit list of capabilities that are deferred or forbidden by this contract.
Must include entries for:

```text
paper_strategy_implementation
paper_order_model
paper_portfolio_ledger
paper_fill_model
paper_pnl_computation
network_wallet_ingestion
real_wallet_monitoring
passive_following_scope
live_access_capability
credential_access
scheduler_or_loop
dashboard_capability
```

### 3.10 safety

Safety flags section. All flags must be present and set true.

### 3.11 warnings

Neutral advisory warning strings. Must include:

```text
not_a_strategy_instruction
not_an_allocation_record
not_an_order_record
research_queue_advisory_only
```

### 3.12 advisory_notice

Top-level advisory notice string confirming the record is advisory only.

## 4. Allowed Eligibility Statuses

Only these five statuses are permitted in a wallet-signal paper strategy
contract record:

```text
NOT_ELIGIBLE_INSUFFICIENT_CONTEXT
NOT_ELIGIBLE_SUSPICIOUS_FLOW
NOT_ELIGIBLE_SAFETY_FLAG_FAILURE
HUMAN_REVIEW_REQUIRED
RESEARCH_ONLY_ELIGIBLE_FOR_FUTURE_PAPER_DESIGN
```

No other eligibility status is permitted.

## 5. Required Safety Flags

All of the following safety flags must be present and set to `true`:

```text
manual_research_only = true
not_automated_copy_trading = true
no_live_execution = true
no_order_placement = true
no_position_sizing = true
no_risk_override = true
no_parameter_auto_change = true
no_paper_engine_created = true
no_account_action = true
```

## 6. Blocking Gate Precedence

The following precedence rules govern eligibility status assignment. Gates are
evaluated in order. The first gate that fails sets the status:

```text
1. Missing required source_report_reference
   → NOT_ELIGIBLE_INSUFFICIENT_CONTEXT
   Human review required.

2. Any safety flag false or missing
   → NOT_ELIGIBLE_SAFETY_FLAG_FAILURE
   Human review required. Hard block.

3. Any suspicious_flow_review block present
   → NOT_ELIGIBLE_SUSPICIOUS_FLOW
   Human review required. Must not be converted into any automation.

4. Missing copyability_delay_context
   → NOT_ELIGIBLE_INSUFFICIENT_CONTEXT
   Human review required.

5. Any unresolved insufficient_context_warnings
   → HUMAN_REVIEW_REQUIRED
   Human analyst must inspect before proceeding.

6. Only after all gates pass
   → RESEARCH_ONLY_ELIGIBLE_FOR_FUTURE_PAPER_DESIGN
   Still not implementation authority.
   Human review still required.
```

## 7. Safety Flag Precedence Table

| Condition | Required Status | Human Review | Notes |
|---|---|---|---|
| Missing source report reference | NOT_ELIGIBLE_INSUFFICIENT_CONTEXT | true | Cannot evaluate provenance. |
| Any safety flag false or missing | NOT_ELIGIBLE_SAFETY_FLAG_FAILURE | true | Hard block. |
| Suspicious flow present | NOT_ELIGIBLE_SUSPICIOUS_FLOW | true | Must not become any automation. |
| Copyability context missing | NOT_ELIGIBLE_INSUFFICIENT_CONTEXT | true | Cannot consider future paper design. |
| Insufficient context warning present | HUMAN_REVIEW_REQUIRED | true | Analyst must inspect. |
| All gates pass | RESEARCH_ONLY_ELIGIBLE_FOR_FUTURE_PAPER_DESIGN | true | Still not implementation authority. |

## 8. Source Reference Policy

Contract records may reference only local/offline IDs. Allowed reference fields:

```text
wallet_intelligence_report_id
wallet_signal_profile_ids
copyability_delay_evaluation_ids
research_queue_annotation_ids
human_review_label_ids
local_fixture_set_id
```

No real wallet address is required in design examples. Use placeholders only:

```text
wallet_placeholder_001
market_placeholder_001
condition_placeholder_001
```

## 9. Raw Metadata Policy

No raw caller-provided mapping may be copied into any wallet-signal paper
strategy contract record.

Every metadata-like field must be either:

- absent,
- a fixed allowlisted field,
- a placeholder ID,
- recursively sanitized by a future implementation WP, or
- rejected by a future implementation WP.

No generic `metadata` object may appear in any contract record unless it is
an explicitly allowlisted static object with safe fixed keys.

A future implementation WP must define and enforce the sanitizer. This
contract WP (WP83) is docs/schema/tests-only and adds no sanitizer
implementation. Raw metadata pass-through is explicitly forbidden by this
contract.

## 10. Deferred Items (Kept Deferred)

The following capabilities are explicitly deferred or forbidden. This contract
does not authorize any of them:

- Paper strategy implementation
- Paper order model
- Paper portfolio ledger
- Paper fill model
- Paper PnL computation
- Network or API wallet ingestion
- Real wallet monitoring
- Automatic following behavior
- Live account access
- Credential access
- Scheduler or bot loop
- Dashboard controls

## 11. Advisory Notice

This contract is advisory research-queue guidance only. A wallet-signal paper
strategy contract record does not authorize a human analyst or an automated
system to:

- Implement any paper strategy
- Allocate any funds
- Place any orders
- Follow any wallet
- Change any parameters
- Access any credentials
- Perform any account action

RESEARCH_ONLY_ELIGIBLE_FOR_FUTURE_PAPER_DESIGN means the idea may be queued
for future paper strategy design review by a human analyst in a separate future
approved WP. It does not mean the idea is approved for implementation.

## 12. Normative Forbidden Output Term Ban List

**This section is the only location where forbidden output terms may appear in
this document. They must not appear anywhere else in this document, in any
static JSON example, or in any contract record output.**

### 12.1 Forbidden Eligibility Statuses

The following statuses must never appear in any contract record:

```text
TRADE_READY
COPY_READY
LIVE_READY
ORDER_READY
EXECUTION_READY
BUY_SIGNAL
SELL_SIGNAL
AUTO_APPROVED
```

### 12.2 Forbidden JSON Key and Value Examples

The following JSON examples must NEVER appear in any contract record or static
example outside this ban-list section. They are listed here only to define what
is forbidden:

```json
{"execution_ready": true}
```

```json
{"order_ready": true}
```

```json
{"buy_signal": "YES"}
```

```json
{"sell_signal": "YES"}
```

```json
{"paper_trading_candidate": true}
```

```json
{"strategy_signal": "wallet followed"}
```

```json
{"expected_return": "12%"}
```

```json
{"position_size": "25 USDC"}
```

```json
{"source_metadata": {"expected_return": "buy recommendation"}}
```

```json
{"live_signal": true}
```

```json
{"auto_copy": true}
```

### 12.3 Forbidden Term Variants

The following term variants must not appear as JSON keys or string values
outside this ban-list section:

```text
buy, sell
trade, trading
execute, execution
order_ready, execution_ready
entry, exit
position_size, position sizing, position-size
expected_return, expected return, expected-return
profit_target, profit target
stop_loss, stop loss
take_profit, take profit
live_signal, live signal
auto_copy, auto copy, automatic copy
copy signal, wallet copy instruction
pnl_target, pnl target
paper_trading_candidate, paper trading candidate
strategy_signal, strategy signal
```

Allowed exact safety-flag key exceptions (these exact key names are permitted
in the safety section only):

```text
not_automated_copy_trading
no_live_execution
no_order_placement
no_position_sizing
```
