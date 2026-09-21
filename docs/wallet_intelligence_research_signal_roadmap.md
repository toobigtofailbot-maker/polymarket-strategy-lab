# Wallet Intelligence Research Signal Roadmap

## A. Status

- WP: WP76 (wallet intelligence roadmap lock-in merged); WP77 (wallet intelligence architecture/profile/signal contract merged); WP78 (wallet trade event snapshot schema/local loader/validator merged); WP79 (wallet signal research profiler and advisory research queue annotation merged); WP80 (copyability delay simulator design and wallet intelligence report contract on branch)
- Package class: DOCS_TESTS_ONLY_WALLET_INTELLIGENCE_ROADMAP_LOCKIN_MERGED; DOCS_SCHEMA_TESTS_ONLY_WALLET_INTELLIGENCE_CONTRACT_MERGED; LOCAL_OFFLINE_READ_ONLY_WALLET_TRADE_EVENT_FIXTURE_LOADER_MERGED; LOCAL_OFFLINE_READ_ONLY_WALLET_SIGNAL_RESEARCH_PROFILER_MERGED; DOCS_SCHEMA_TESTS_ONLY_WALLET_COPYABILITY_DELAY_SIMULATOR_DESIGN_ON_BRANCH
- Authority: PLANNING_GUIDANCE_ONLY
- NOT_AUTHORIZATION
- NO_RUNTIME_CHANGE
- DOCS_SCHEMA_TESTS_ONLY_WALLET_COPYABILITY_DELAY_SIMULATOR_DESIGN_ON_BRANCH
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
- WP76 merge commit: 91cd26e4fe16d492fa2f7b319fba176ee60cd9d5
- WP77 merge commit: 24badbfb7a9da06ee4c8ae94795e1f2c862af913
- WP78 merge commit: 7ff117f6caf78eab62e6a116db72b60d76d305f5
- WP79 merge commit: 4266aefa09da9b06a7e2f547aae70149c203da80
- WP80 branch: wp80-copyability-delay-simulator-design-wallet-report-contract

## B. Purpose

Wallet intelligence is a first-class research signal layer.
It is not a blind copy-trading engine.

**Plain analogy:** Top wallets are expert scouts. If a proven scout walks toward
a market, the bot looks there first. The bot does not automatically follow the
scout into a trade.

This document locks the accepted wallet-intelligence roadmap direction into repo
truth after WP75 merge. It does not implement the wallet engine. Future WPs will
implement the wallet registry, profiles, trade event loader, skill profiler,
copyability simulator, and research queue integration in sequence.

**This is planning guidance only.** It does not approve any future wallet API
ingestion, credential usage, automatic copy-trading, live execution, order
placement, paper-trading strategy, scheduler, bot loop, dashboard, or Hermes
runtime. Each future implementation phase requires its own explicitly approved
work package.

## C. Core Locked Decision

Top-wallet activity may materially increase research priority.
Top-wallet activity must not directly trigger live execution.

This policy applies to all future wallet intelligence WPs:
- Wallet signals feed research queues, human review queues, and alerts.
- Wallet signals may eventually feed paper-trading candidate generation after
  delayed-copy evidence and explicit future authorization.
- Wallet signals must never directly place orders, cancel orders, change
  position sizes, change scoring weights, or override risk parameters without
  the full live-trading authorization sequence.

## D. Role In Architecture

Wallet intelligence is one of six major research signal pillars:

1. Resolution-rule intelligence
2. Microstructure/liquidity intelligence
3. Official-source/news intelligence
4. Cross-market relationship intelligence
5. Top-wallet intelligence
6. Calibration/human-review intelligence

Each pillar produces advisory-only research metadata. None of them directly
controls execution. All pillar outputs feed the research queue and human review
queue before any strategic action is proposed.

## E. Wallet Intelligence Jobs

Five jobs define the full wallet intelligence workflow:

1. **Find top wallets.** Identify wallets with strong historical track records
   across realized profit, market count, resolution rate, and niche alignment.

2. **Classify what each wallet is good at.** Build a skill and niche profile:
   which market categories, holding periods, liquidity tiers, and event types
   each wallet trades profitably. Distinguish genuine expertise from lucky outliers.

3. **Detect when those wallets enter markets.** Monitor wallet trade events
   against active markets in the research queue. Flag when a known skilled wallet
   takes a position in a prioritized market.

4. **Test whether their trades are copyable after delay.** Evaluate whether a
   retail trader could have copied the wallet's entry price after a realistic
   delay window while still achieving a profitable outcome after spread, slippage,
   fees, liquidity limits, and size constraints.

5. **Feed wallet signals into the research queue, reports, and paper-trading
   candidate generation.** Raise the research priority of markets where skilled
   wallets are active. Surface wallet intelligence in human review reports and
   eventually in paper-trading candidate generation after evidence and explicit
   authorization.

## F. Required Wallet Metrics

Any future wallet profile or evaluation must include at minimum:

**Activity metrics:**
- number of trades
- number of resolved markets
- average trade size
- median trade size

**Profitability metrics:**
- realized profit
- unrealized profit
- profit by category
- profit by holding period
- profit by market liquidity
- profit before/after major news
- largest win
- largest loss
- max drawdown

**Entry quality metrics:**
- entry price versus later market price
- entry price versus final resolution

**Copyability metrics:**
- copy-after-1s PnL
- copy-after-5s PnL
- copy-after-30s PnL
- copy-after-2m PnL
- copy-after-10m PnL

**The key metric is not "wallet made money."**
**The key metric is: "Could we have made money copying this wallet after
realistic delay, spread, slippage, fees, and size limits?"**

A wallet that makes money but only in a 200ms entry window that a retail trader
cannot access is not a copyable wallet. The evaluation must use delayed-copy
windows that reflect actual latency, market impact, and fee load for a realistic
follower.

## G. Wallet Signal Categories

Every wallet trade event observation must be classified into one of these
signal categories before any research queue update:

- `SPECIALIST_ENTRY` — wallet with a confirmed niche takes a position in its area
- `MULTI_WALLET_CLUSTER` — multiple independent skilled wallets enter the same side
- `EARLY_ENTRY_BEFORE_PRICE_MOVE` — wallet entered before a significant price move
- `LATE_CHASER` — wallet entered after the market had already moved significantly
- `MARKET_MAKER_FLOW` — probable liquidity-provision flow, not directional signal
- `ARBITRAGE_FLOW` — cross-market spread capture behavior, not directional signal
- `SUSPICIOUS_TIMING` — entry timing consistent with pre-news, pre-resolution, or
  possibly privileged information flow; must not be followed
- `LOW_SAMPLE_OUTLIER` — wallet with too few trades to confirm skill; weight low
- `UNCOPYABLE_FAST_FLOW` — wallet entry window too short for realistic delayed copy

## H. Copyability Delay Principle

A wallet is not copyable unless delayed-copy evaluation remains profitable after
realistic spread, slippage, fees, liquidity limits, and size constraints.

Required delay windows for every copyability evaluation:

- 1 second
- 5 seconds
- 30 seconds
- 2 minutes
- 10 minutes

The evaluation must use all five windows and report separate PnL estimates for
each. A wallet that is profitable at 1 second but loses money at 30 seconds is
classified as `UNCOPYABLE_FAST_FLOW` unless explicit evidence shows that 30-second
delay is achievable.

No wallet may be promoted to "copyable" status without evidence across at least
the 5-second and 30-second delay windows that realistic execution is profitable
after fee load.

## I. Research Queue Weighting Policy

This is roadmap direction, not currently implemented behavior.

Wallet intelligence may become a heavy research-priority input after validation:
- Target research-queue influence range: 25% to 35%
- Direct trade-decision influence remains 0% until explicit evidence and
  authorization

This weighting range is a planning target only. Any actual implementation of
research queue weighting for wallet signals requires:
1. A separate implementation WP with explicit scope
2. Evidence from WP79 skill/niche profiler integration
3. Explicit user authorization before implementation

**Optional future path after paper/live proof:**
Wallet signal may become a restricted strategy input only after copyability
evidence, risk review, paper-trading proof, and explicit future WP authorization.

## J. Suspicious-Flow Boundary

Wallets with suspicious pre-news, pre-resolution, or potentially
informed-flow patterns must be classified as `SUSPICIOUS_TIMING` and
flagged as research-watch-only or human-review-required.

The project must not build a strategy whose purpose is to follow suspicious or
privileged-information flow. Copying informed flow is not a legitimate research
strategy for this project.

All `SUSPICIOUS_TIMING` signals must:
- be flagged in the human review queue with `SUSPICIOUS_TIMING` classification
- never be fed into paper-trading candidate generation without explicit human
  review and rejection of the suspicious-flow interpretation
- be noted in the research queue with a human-review-required marker

## K. Updated Near-Term Roadmap

After WP76 wallet intelligence roadmap lock-in, WP77 architecture-contract
merge, and WP78 fixture-loader selection:

- **WP77** - Wallet Intelligence Architecture, Registry, Profile, And Signal Contract
  *Merged: first blueprint for watched-wallet profiles, registry statuses,
  wallet signal contracts, research-priority effects, copyability statuses, and
  forbidden controls.*

- **WP78** - Wallet Trade Event Snapshot Schema, Local Loader, And Validation
  *Current WP: schema and local/offline/read-only fixture loader/validator for
  explicitly provided wallet trade event fixture files.*

- **WP79** - Wallet Skill/Niche Profiler And Research Queue Integration V1
  *Local/offline/read-only niche profiler from validated trade event fixtures;
  first wallet signal integration into research queue (advisory-only).*

- **WP80** - Copyability Delay Simulator Design And Wallet Intelligence Report Contract
  *Current WP: copyability delay simulator design, wallet intelligence report
  contract, static JSON examples, focused tests.*

- **WP81** - Local Copyability Delay Evaluation From Validated Fixtures V1
  *Delayed-copy evaluation from local validated wallet trade event fixtures;
  local/offline/read-only; no live execution.*

- **WP82** - Wallet Intelligence Report Generator V1
  *Local/offline/read-only wallet intelligence report generator satisfying the
  WP80 contract; no live execution.*

- **WP83** - Wallet Signal Paper Strategy Contract
  *Paper-trading candidate generation contract from wallet signals; no live
  execution.*

- **WP84** - Human Review Label And Calibration Record Join Design Or Implementation
  *Join design or implementation between human review labels and calibration records.*

Do not draft WP81 until WP80 is merged and repo truth is re-verified.

## L. Explicit Non-Goals

The following are explicitly not implemented in this WP or any future WP without
separate explicit authorization:

- **no automatic copy-trading** — wallet signals are advisory-only
- **no live execution** — no orders placed for any reason from wallet signals
- **no order placement** — no buy/sell/limit/market orders from wallet signals
- **no cancels** — no order cancellations triggered by wallet signals
- **no position sizing** — wallet signals do not set position sizes
- **no risk override** — wallet signals do not override risk parameters
- **no parameter auto-change** — wallet signals do not change scorer weights,
  thresholds, or bucket boundaries
- **no strategy auto-approval** — wallet signals do not automatically generate
  approved strategies
- **no credentials** — wallet data is local/offline/read-only fixture data only
- **no network ingestion in this WP** — no Polymarket wallet API, no wallet
  data fetch
- **no wallet API client in this WP** — no API client for any wallet data source
- **no dashboard** — no UI, no Streamlit, no Grafana, no visualization layer
- **no scheduler** — no cron, no daemon, no automated trigger
- **no bot loop** — no autonomous polling, no background worker
- **no Hermes/LLM execution authority** — no LLM, no Hermes, no agent runtime
  drives wallet-signal decisions

## M. Future Controlled Live Boundary

Wallet intelligence may later feed:
- research queue (approved from WP79 onward, subject to implementation WP)
- human review queue (approved from WP79 onward, subject to implementation WP)
- alerts (future approved alert WP only)
- paper-trading candidate generation (future, after copyability evidence)
- strategy proposals (future, after paper-trading proof and authorization)
- performance review (future, after performance measurement WP)

Wallet intelligence must not feed live execution until ALL of the following exist:
- validated delayed-copy evidence (from WP81 or successor)
- paper-trading evidence (from WP83 or successor)
- risk-gate approval (from future explicit risk review WP)
- explicit live-trading authorization (from user and documented in repo truth)
- credential boundary (future secret management and key boundary WP)
- execution gateway (future execution gateway implementation WP)
- kill switch (future kill-switch implementation WP)
- monitoring (future observability and alerting WP)
- human approval or restricted-live mode policy (future authorized live policy WP)

Missing any one of the above means wallet signals must not reach live execution.

## N. Deferred Items

The following items are deferred from WP76 to future WPs:

- **WP76-D001**: Wallet intelligence architecture/registry/profile contract
  is resolved only for WP77 docs/schema/tests design scope; implementation
  remains deferred through WP77 items.
- **WP76-D002**: Wallet trade event schema/local loader/validator is resolved
  only for WP78 local/offline/read-only schema, static example, validator, and
  explicit-path fixture loader scope.
- **WP76-D003**: Wallet skill/niche profiler and research queue integration
  are resolved only for WP79 local/offline/read-only advisory wallet signal
  research profile and research queue annotation scope.
- **WP76-D004**: Copyability delay simulator design and wallet intelligence report
  contract are resolved only for WP80 docs/schema/tests-only scope. Copyability
  delay implementation remains deferred to WP81; report generator remains deferred
  to WP82.
- **WP76-D005**: Wallet signal paper strategy contract remains deferred (WP83
  is next candidate).
- **WP76-D006**: Any direct wallet-driven live execution remains forbidden until
  explicit future authorization satisfying all live boundary conditions in
  section M above.
- **WP76-D007**: Automated copy-trading remains forbidden until delayed-copy
  evidence, paper-trading proof, risk review, and live authorization exist.

## S10-WALLET-01 — Public wallet evidence foundation (update)

WP76-WP90 remain bounded local/offline synthetic/fixture prototypes. They are
valuable safety and reference material, but they do not make old profile or
copyability outputs real-data truth.

S10-WALLET-01 is the first real public-evidence foundation. It narrowly
authorizes **bounded, manual, GET-only, PUBLIC, no-auth** Polymarket Data API v2
wallet reads (`/v2/trades`, `/v2/activity`, `/v2/activity/combos`), disabled by
default. It builds the deterministic, replayable, point-in-time-safe wallet
evidence substrate only. It does not decide skill, rank wallets, compute
promotion thresholds, decide copyability, run copy-trading, compute follower
PnL, generate a trade, qualify a strategy, create WP170 experiments, or authorize
Gate C. Every credential, authenticated-account, signing, order, paper, live,
scheduler, and bot-loop prohibition above remains intact. Later S10-WALLET-02/03/04
own real profiling, copyability, and incremental-value studies. See
`docs/wallet_public_evidence_foundation_contract.md`.
