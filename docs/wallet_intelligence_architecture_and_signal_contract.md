# Wallet Intelligence Architecture And Signal Contract

## 1. Purpose

Wallet intelligence is an advisory research-signal architecture.
It identifies wallets worth studying, classifies wallet behavior, and defines
how wallet signals may influence research priority.
It does not authorize automatic copy-trading, order placement, live execution,
or risk overrides.

Plain analogy:

```text
WP76 pinned the plan to the wall.
WP77 draws the blueprint for the wallet-scout system.
The blueprint says what information a scout card must contain and what the scout is never allowed to control.
```

WP77 is merged as docs/schema/tests-only. It created a design contract for later
local/offline wallet intelligence work. WP78 adds only the local/offline
wallet trade event fixture schema, validator, and explicit-path loader. Neither
WP77 nor WP78 fetches network data, monitors wallets, ranks real wallets,
copies wallets, paper trades, or live trades.

## 2. Architecture Position

Wallet intelligence is an advisory layer between:

- WP78 local/offline wallet event fixtures
- research queue and human review queue
- future paper-trading candidate generation, only after separate approval

Wallet intelligence must not connect directly to:

- credentials
- authenticated account endpoints
- order placement
- order cancellation
- position sizing
- risk override
- live execution
- scheduler
- bot loop
- Hermes/LLM execution authority

Any future implementation must remain local/offline/read-only until a later
approved work package explicitly changes that boundary.

## 3. Wallet Registry Concept

A future wallet registry is a list of watched wallet profiles. The registry
classifies wallets for research review; it does not follow them blindly.

Required registry-level concepts:

- `wallet_id_or_address`
- `alias_or_label`
- `source_of_inclusion`
- `sample_size_status`
- `specialization_status`
- `copyability_status`
- `suspicious_flow_status`
- `review_status`
- `last_reviewed_at_utc`
- `advisory_only_notice`

Allowed future registry statuses:

- `ACTIVE_RESEARCH_WATCH`
- `WATCH_ONLY_LOW_SAMPLE`
- `WATCH_ONLY_UNCOPYABLE`
- `WATCH_ONLY_SUSPICIOUS_FLOW`
- `DEPRECATED_DO_NOT_USE`

Forbidden registry statuses:

- `AUTO_COPY`
- `LIVE_TRADE`
- `EXECUTE`
- `POSITION_SIZE_FROM_WALLET`
- `RISK_OVERRIDE_FROM_WALLET`

## 4. Wallet Profile Contract

A future watched wallet profile must be grouped into these sections:

- `identity`: placeholder-safe wallet identifier, label, inclusion source,
  and provenance for why the wallet is watched.
- `sample_size`: trade count, market count, resolved-market count, and whether
  evidence is sufficient for research use.
- `profitability`: realized and unrealized historical performance observations
  by category, holding period, liquidity tier, and timing context.
- `specialization`: market categories, event types, holding periods, and
  liquidity contexts where the wallet appears more or less consistent.
- `entry_quality`: historical observation of the wallet's timing versus later
  market price and final resolution, without creating any instruction.
- `copyability`: evidence about realistic delayed copyability after spread,
  slippage, fees, liquidity limits, size constraints, and delay windows.
- `risk`: drawdown, largest win/loss, concentration, timing concerns, and
  suspicious-flow flags.
- `signal_policy`: advisory-only limits for how the wallet may influence
  research priority.
- `review`: human-review state, reviewer notes, and review timestamps.
- `safety`: mandatory safety flags proving the profile has no execution,
  order, sizing, risk, or parameter authority.

Raw PnL is not enough to classify a wallet as useful. A wallet must have
sufficient sample size, category consistency, copyability evidence, and
non-suspicious timing before it can materially influence research priority.

## 5. Wallet Signal Contract

A wallet signal is a single advisory observation about wallet behavior in
relation to one market context. It is a research observation, not an
instruction.

Required signal fields:

- `signal_id`
- `wallet_id_or_address`
- `market_id`
- `condition_id`
- `observed_at_utc`
- `signal_category`
- `market_category`
- `wallet_specialization_match`
- `direction_observed`
- `entry_price_observed`
- `size_observed`
- `liquidity_context_available`
- `copyability_context_available`
- `suspicious_flow_flag`
- `human_review_required`
- `research_priority_effect`
- `advisory_only_notice`

`direction_observed` may record what happened historically and must not be interpreted as a buy/sell instruction.

## 6. Allowed Signal Categories

Allowed wallet signal categories:

- `SPECIALIST_ENTRY`
- `MULTI_WALLET_CLUSTER`
- `EARLY_ENTRY_BEFORE_PRICE_MOVE`
- `LATE_CHASER`
- `MARKET_MAKER_FLOW`
- `ARBITRAGE_FLOW`
- `SUSPICIOUS_TIMING`
- `LOW_SAMPLE_OUTLIER`
- `UNCOPYABLE_FAST_FLOW`

## 7. Research Priority Effect Contract

Wallet signals may affect research priority only as advisory-only values.

Allowed research-priority effect values:

- `NO_CHANGE`
- `LOW_RESEARCH_BOOST`
- `MEDIUM_RESEARCH_BOOST`
- `HIGH_RESEARCH_BOOST`
- `CAP_RESEARCH_PRIORITY`
- `REQUIRE_HUMAN_REVIEW`
- `BLOCK_FROM_AUTOMATION`

Forbidden research-priority effect values:

- `BUY`
- `SELL`
- `TRADE`
- `EXECUTE`
- `OPEN_POSITION`
- `CLOSE_POSITION`
- `POSITION_SIZE`
- `EXPECTED_RETURN`
- `PROFIT_TARGET`
- `STOP_LOSS`
- `LIVE_SIGNAL`
- `AUTO_COPY`

## 8. Copyability Status Contract

Allowed copyability statuses:

- `NOT_EVALUATED`
- `COPYABILITY_UNPROVEN`
- `COPYABILITY_RESEARCH_PROMISING`
- `COPYABILITY_PAPER_ELIGIBLE`
- `UNCOPYABLE_FAST_FLOW`
- `UNCOPYABLE_TOO_ILLIQUID`
- `UNCOPYABLE_TOO_LATE`
- `SUSPICIOUS_FLOW_DO_NOT_COPY`

No status may imply current live permission.

## 9. Suspicious-Flow Boundary

Wallets or signals with suspicious timing must be research-watch-only or
human-review-required.
The project must not build a strategy whose purpose is to follow suspicious or
privileged-information flow.

Suspicious-flow observations may be studied as research risk and data-quality
context. They must not become a strategy, paper-trading trigger, live signal,
copy-trading instruction, or automation input.

## 10. Safety Flags

Every static profile and signal schema must include safety fields equivalent to:

```text
manual_research_only = true
not_automated_copy_trading = true
no_live_execution = true
no_order_placement = true
no_position_sizing = true
no_risk_override = true
no_parameter_auto_change = true
```

These flags must remain true in static examples. A later implementation may
add stricter flags, but may not remove these boundaries.

## 11. Future WP Sequence

Updated sequence:

- WP78 - Wallet Trade Event Snapshot Schema, Local Loader, And Validation (on branch)
- WP79 - Wallet Skill/Niche Profiler And Research Queue Integration V1
- WP80 - Copyability Delay Simulator Design And Wallet Intelligence Report Generator
- WP81 - Wallet Signal Paper Strategy Contract
- WP82 - Human Review Label And Calibration Record Join Design Or Implementation

WP78 is merged (PR #79 merge commit `7ff117f6caf78eab62e6a116db72b60d76d305f5`).
WP79 is on branch: local/offline/read-only wallet signal research profiler and
advisory research queue annotation. Do not draft WP80 until WP79 is merged and
repo truth is re-verified.

## 12. Non-Goals

WP77 explicitly did not add, WP78 still did not add, and WP79 adds only local
advisory profiling and annotation (no network/API ingestion, no copyability PnL,
no buy/sell signals, no scoring weight changes):

- no wallet API client
- no network ingestion
- no real wallet monitoring
- no copyability delay simulator
- no wallet intelligence report generator
- no automatic copy-trading
- no live execution
- no order placement
- no cancels
- no position sizing
- no risk override
- no parameter auto-change
- no strategy auto-approval
- no credentials
- no scheduler
- no bot loop
- no dashboard
- no Hermes/LLM execution authority

WP79 adds:

- local/offline/read-only wallet signal research profile builder
- local/offline/read-only wallet research queue annotation builder
- advisory-only frozen dataclasses (no trade-like fields)
- docs and focused tests
