# Wallet Copyability Delay Simulator Design

## 1. Status

- WP: WP80 (copyability delay simulator design docs/schema/tests-only)
- Package class: DOCS_SCHEMA_TESTS_ONLY_WALLET_COPYABILITY_REPORT_CONTRACT
- Authority: DESIGN_ONLY
- NOT_IMPLEMENTATION
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
- WP80 merge commit: ee3d10296dce5504164b7e747b286e8fe5a09991

## 1b. WP81 Implementation Status

- WP: WP81 (local/offline/read-only copyability delay evaluation implementation — first evaluator)
- Package class: LOCAL_OFFLINE_READ_ONLY_WALLET_COPYABILITY_DELAY_EVALUATION
- Scope: `src/data_layer/wallet_copyability_delay_evaluation.py` — first local/offline evaluator implementation

WP81 evaluates local fixture records only. It does not prove a wallet is copyable.
It does not estimate expected return. It does not create trade recommendations.
It does not place or simulate live orders.

Specifically, WP81:
- Consumes only in-memory/local `DelayWindowObservation` fixture records and
  already-validated WP78 `LoadedWalletTradeEventRecord` objects.
- Evaluates all five required delay windows (1_second, 5_seconds, 30_seconds,
  2_minutes, 10_minutes) for each (wallet, market, condition) group.
- Produces only advisory `WalletCopyabilityDelayEvaluation` records.
- Emits only the eight allowed advisory statuses from the WP80 design contract.
- Never computes dollar PnL, expected return, position size, or live signal.
- Is stdlib-only. No network. No credentials. No file writes.

## 2. Purpose

This document defines the design contract for a future local/offline copyability
delay evaluation component. It does not implement that component.

Plain analogy:

```text
WP78 built the safe local file reader for wallet observation sheets.
WP79 sorted those local observations into advisory wallet-scout classifications.
WP80 designs the test track for asking:
"Would following this wallet late still have worked?"
```

The question "would it have worked after delay?" is the core research question
this simulator design answers in principle. The simulator itself is deferred to
WP81.

## 3. Core Copyability Delay Principle

A wallet is not copyable unless delayed-copy evaluation remains favorable after
realistic delay, spread, slippage, fees, liquidity limits, and size constraints.

This principle governs all future evaluation:

- Delay is unavoidable for any follower of a watched wallet.
- Spread, slippage, fees, liquidity limits, and size constraints are real costs
  that erode or eliminate apparent copyability.
- An evaluation that ignores any of these factors is incomplete and may
  overestimate copyability.

Favorable evaluation means the simulated delayed-copy entry could have achieved
a better outcome than the simulated alternative (e.g., not entering). Favorable
does not mean "guaranteed profit." No evaluation output is a trading signal or
trade recommendation.

## 4. Required Delay Windows

Any future evaluation must assess copyability across all of the following delay
windows:

```text
1 second
5 seconds
30 seconds
2 minutes
10 minutes
```

These windows represent realistic latency ranges for a retail-speed follower
observing a wallet event and attempting to enter the same market.

The evaluation must not treat any single delay window as definitively
"copyable" or "uncopyable." All five windows must be assessed and reported
separately. Human review is required to interpret the window-level results.

## 5. Allowed Evaluation Inputs

Future implementations must derive all evaluation inputs from local/offline
validated fixtures. No live API feed, authenticated account data, or real-time
execution feed is allowed as an evaluation input.

Allowed future inputs:

```text
validated local wallet trade event fixtures      (from WP78 loader/validator)
local market and orderbook snapshots             (from future approved WPs)
local fee/tick/min-size metadata                 (from future approved WPs)
local resolved-outcome fixtures                  (from WP68 loader)
local research queue context                     (from future approved WPs)
```

Forbidden inputs (at any time):

```text
live API wallet feed
authenticated account data
real-time order placement
private keys
execution feed
scheduler loop
credentials
```

Any future WP that proposes adding a live input must go through a separate
explicit scope approval.

## 6. Constraint Factors Required In Evaluation

Any future evaluation must account for all of the following constraint factors.
Omitting any factor makes the evaluation incomplete and must be reflected in
the evaluation status as INSUFFICIENT_CONTEXT.

Required constraint factors:

- **Spread context**: the bid-ask spread observable after the delay window
- **Slippage context**: the expected price impact of a follower-sized entry
- **Fee context**: maker/taker fee costs for the follower entry
- **Liquidity limit context**: available liquidity at or near the observable price
- **Size constraint context**: minimum and maximum entry size constraints

An evaluation may still reach INSUFFICIENT_CONTEXT if any of these contexts
is unavailable from local fixtures at evaluation time.

## 7. Evaluation Output Contract

All evaluation outputs are advisory research metadata. They are never trade
instructions.

Allowed advisory output fields:

```text
wallet_id_or_address          — placeholder or hashed wallet reference only
market_id                     — market under evaluation
condition_id                  — condition under evaluation
market_category               — market category classification
signal_category               — wallet signal category from research profile
delay_window                  — which delay window this evaluation covers
entry_price_at_wallet_event   — historical price at time of wallet event
observable_price_after_delay  — historical price observable after delay window
spread_context_available      — whether spread data is present for this window
liquidity_context_available   — whether liquidity data is present
fee_context_available         — whether fee data is present
size_limit_context_available  — whether size limit data is present
resolved_outcome_available    — whether the market resolved and outcome is known
evaluation_status             — one of the allowed advisory statuses below
research_interpretation       — free-text advisory research summary
human_review_required         — boolean; true if any P0 condition is met
warnings                      — list of advisory warning strings
advisory_only_notice          — must be present and non-empty in all outputs
```

Allowed advisory evaluation statuses:

```text
NOT_EVALUATED                  — evaluation not yet attempted
INSUFFICIENT_CONTEXT           — one or more required context fields are absent
RESEARCH_PROMISING             — delayed-copy context appears favorable (advisory only)
RESEARCH_WEAK                  — delayed-copy context appears unfavorable (advisory only)
UNCOPYABLE_FAST_FLOW           — wallet entered too fast for any realistic follower delay
UNCOPYABLE_TOO_ILLIQUID        — insufficient liquidity at any realistic follower size
SUSPICIOUS_FLOW_DO_NOT_COPY    — suspicious-flow flag is active; human review required
HUMAN_REVIEW_REQUIRED          — evaluation is indeterminate; requires human judgment
```

RESEARCH_PROMISING and RESEARCH_WEAK are advisory research labels only. They
are not buy or sell signals. They do not imply any trade should be made.

Forbidden output fields and values (must never appear in any output):

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

## 8. Suspicious-Flow Boundary

Suspicious-flow observations must not become a strategy to follow privileged
or suspicious information.

When a wallet event carries suspicious_flow_status = SUSPICIOUS_TIMING or
equivalent, the evaluation must:

- set evaluation_status = SUSPICIOUS_FLOW_DO_NOT_COPY
- set human_review_required = true
- include a warning that suspicious-flow events are blocked from further use

Suspicious-flow observations may trigger human review or block automation. They
must not become a rationale for entering a market faster or at a larger size.

## 9. Forbidden Implementation Scope

This design does not authorize and WP80 must not implement:

```text
live copyability simulator
PnL computation for following wallets
expected-return calculation
position sizing from wallet signals
wallet API or network ingestion
authenticated account access
paper-trading strategy contract
live-trading signal output
scheduler or bot loop
credentials
Hermes/LLM execution authority
order placement or cancellation
```

## 10. Future Implementation Sequence

```text
WP81 — Local Copyability Delay Evaluation From Validated Fixtures V1
WP82 — Wallet Intelligence Report Generator V1
WP83 — Wallet Signal Paper Strategy Contract
WP84 — Human Review Label And Calibration Record Join Design Or Implementation
```

WP81 must remain local/offline/read-only. It must not create live copy-trading,
buy/sell outputs, credentials, or execution.

## 11. Safety

This design document is planning guidance only. It is not authorization for any
implementation, network access, live execution, credentials, order placement,
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
