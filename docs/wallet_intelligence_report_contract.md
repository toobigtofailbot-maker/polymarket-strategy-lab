# Wallet Intelligence Report Contract

## 1. Status

- WP: WP80 (wallet intelligence report contract docs/schema/tests-only); WP82 (local/offline/read-only report generator implementation)
- Package class: DOCS_SCHEMA_TESTS_ONLY_WALLET_COPYABILITY_REPORT_CONTRACT (WP80); LOCAL_OFFLINE_READ_ONLY_WALLET_INTELLIGENCE_REPORT_GENERATOR (WP82)
- Authority: DESIGN_ONLY (WP80); LOCAL_OFFLINE_READ_ONLY_IMPLEMENTATION (WP82)
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
- WP80 merge commit: TO_BE_RECORDED_AFTER_MERGE
- WP82 implementation: `src/data_layer/wallet_intelligence_report_generator.py`

## 2. Purpose

This document defines the contract for a future local/offline wallet intelligence
report. A wallet intelligence report is a human review report. It is not a trade recommendation, not a buy/sell signal, not a position sizing output, and not a copy-trading instruction.

Plain analogy:

```text
A wallet intelligence report is a briefing document for a human analyst.
It summarizes what the bot observed about wallet activity and what research
questions remain open.
It does not tell the analyst what to buy, sell, or size.
```

The report generator itself is deferred to WP82. This document defines what
the report may and must not contain.

## 3. Report Identity

A wallet intelligence report must carry a report identity section that includes:

```text
report_id              — a unique report identifier
report_type            — must be WALLET_INTELLIGENCE_ADVISORY_REPORT_V1
report_generated_at    — timestamp of report generation
wp_version             — the WP under which the report was generated
advisory_only_notice   — must be present and non-empty
design_example_only    — true if this is a design example, false otherwise
```

## 4. Required Report Sections

A wallet intelligence report must contain all of the following sections:

### 4.1 report_identity

Identity fields as defined in Section 3.

### 4.2 input_summary

Summary of inputs used to generate the report:

```text
wallet_fixture_source       — source path or identifier for wallet fixtures
event_count                 — count of wallet trade events included
market_count                — count of distinct markets covered
condition_count             — count of distinct conditions covered
fixture_validation_status   — VALID, PARTIAL, INVALID, or NOT_VALIDATED
research_queue_context      — whether research queue context was present
```

### 4.3 wallet_signal_summary

Summary of wallet signal research profiles derived from input:

```text
profile_count                 — count of wallet signal research profiles
signal_category_distribution  — distribution of signal categories
suspicious_flow_count         — count of profiles with suspicious flow flag
human_review_required_count   — count of profiles requiring human review
advisory_only_notice          — must be present
```

### 4.4 copyability_delay_design_summary

Summary of copyability delay evaluation design or results (if evaluation was
performed):

```text
delay_windows_assessed          — list of delay windows covered
evaluation_status_distribution  — distribution of evaluation statuses
uncopyable_fast_flow_count      — count of events classified uncopyable fast flow
uncopyable_illiquid_count       — count of events classified uncopyable illiquid
suspicious_flow_blocked_count   — count of events blocked by suspicious-flow rule
advisory_only_notice            — must be present
```

### 4.5 research_queue_implications

Advisory research-queue implications (not instructions):

```text
markets_flagged_for_research      — count of markets with wallet-influenced priority
research_priority_effect_summary  — distribution of advisory priority effect labels
human_review_queue_additions      — count of items added to human review queue
advisory_only_notice              — must be present
```

### 4.6 suspicious_flow_review

Summary of suspicious-flow observations:

```text
suspicious_flow_events     — list of event references with suspicious-flow flag
required_action            — must be HUMAN_REVIEW_REQUIRED for all entries
blocked_from_automation    — must be true for all entries
advisory_only_notice       — must be present
```

### 4.7 limitations

Explicit statement of report limitations:

```text
data_source_limitations    — description of local/offline data-source constraints
evaluation_limitations     — which constraint factors are absent or incomplete
no_live_data_notice        — explicit statement that no live data was used
no_trading_signal_notice   — explicit statement that report contains no signals
advisory_only_notice       — must be present
```

### 4.8 deferred_items

Items explicitly deferred from this report, using safe advisory capability names
(not forbidden trade-like field names — see Section 5 for the normative ban list):

```text
copyability_evaluation_implementation   — deferred to WP81
wallet_report_generator_implementation  — deferred to WP82
future_simulation_contract              — deferred to WP83
live_execution_forbidden                — forbidden
wallet_api_ingestion_forbidden          — forbidden
```

### 4.9 safety

Safety flags. All must be present and set to true:

```text
manual_research_only        = true
not_automated_copy_trading  = true
no_live_execution           = true
no_order_placement          = true
no_position_sizing          = true
no_risk_override            = true
no_parameter_auto_change    = true
```

## 5. Forbidden Report Content

The following must never appear in any wallet intelligence report, in any
section, field name, or field value:

```text
BUY
SELL
TRADE
EXECUTE
OPEN_POSITION
CLOSE_POSITION
POSITION_SIZE
EXPECTED_RETURN
PROFIT_TARGET
STOP_LOSS
TAKE_PROFIT
LIVE_SIGNAL
AUTO_COPY
PNL_TARGET
```

These are forbidden regardless of context. A field named "expected_return"
is forbidden even if its value is null or zero.

## 6. Suspicious-Flow Boundary In Reports

Suspicious-flow observations may trigger human review or block automation.
They must not become a strategy to follow privileged or suspicious information.

Any suspicious-flow event in a report must:

- appear only in the suspicious_flow_review section
- carry required_action = HUMAN_REVIEW_REQUIRED
- carry blocked_from_automation = true
- not contribute to any research priority recommendation

A report must not use suspicious-flow observations as positive evidence that
a market is worth entering or that a wallet's activity should be emulated.

## 7. Human Review Report Requirement

A wallet intelligence report is a human review report. It exists to help a
human analyst understand what the bot observed. It is not designed to be
consumed by an automated trading system.

All interpretive sections (wallet_signal_summary, copyability_delay_design_summary,
research_queue_implications) must carry advisory_only_notice fields.

The report must not contain a section called "recommendations," "signals,"
"trades," "positions," or any equivalent.

## 8. Future WP Sequence

```text
WP81 — Local Copyability Delay Evaluation From Validated Fixtures V1
WP82 — Wallet Intelligence Report Generator V1
WP83 — Wallet Signal Paper Strategy Contract
WP84 — Human Review Label And Calibration Record Join Design Or Implementation
```

WP82 implements the local/offline/read-only wallet intelligence report generator at
`src/data_layer/wallet_intelligence_report_generator.py`. The generator:

```text
WP82 generates advisory local reports only.
It does not prove a wallet is copyable.
It does not estimate expected return.
It does not create trade recommendations.
It does not place or simulate live orders.
```

WP82 consumes only:
- WalletSignalResearchProfile records (WP79) in-memory
- WalletResearchQueueAnnotation records (WP79) in-memory
- WalletCopyabilityDelayEvaluation records (WP81) in-memory
- Optional explicit local metadata supplied by callers

WP82 does not add live execution, network ingestion, credentials,
paper-trading strategy, or buy/sell signal output.

The following deferred items remain open:

```text
wallet_signal_paper_strategy_contract   — DEFERRED_TO_WP83
real_wallet_api_ingestion               — FORBIDDEN_UNTIL_APPROVED_WP
automated_copy_trading                  — FORBIDDEN
live_execution                          — FORBIDDEN
```

## 9. Safety

This contract document is planning guidance only. It is not authorization for
any implementation, network access, live execution, credentials, order placement,
position sizing, risk override, parameter auto-change, scheduler loop, bot loop,
dashboard, paper-trading strategy, or Hermes/LLM execution authority.

```text
manual_research_only        = true
not_automated_copy_trading  = true
no_live_execution           = true
no_order_placement          = true
no_position_sizing          = true
no_risk_override            = true
no_parameter_auto_change    = true
```
