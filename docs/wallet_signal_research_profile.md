# Wallet Signal Research Profile

## 1. Purpose

A wallet signal research profile is a deterministic advisory classification
derived from local validated WP78 wallet trade event fixture records.

It is advisory research metadata only.

It is **not**:
- a wallet ranking for trading;
- a copy-trading instruction;
- a buy/sell signal;
- an expected-return estimate;
- a position sizing input;
- a live-trading permission;
- a proof of wallet skill;
- a proof of copyability.

## 2. Source

Profiles are derived only from local validated WP78 `LoadedWalletTradeEventRecord`
objects. These records are local JSON fixture files explicitly loaded from disk
using `load_wallet_trade_event_fixtures`.

This module does not fetch wallet data from any network source or API. It does
not monitor real wallets. It does not scan wallet leaderboards. It does not
ingest any live or authenticated market data.

## 3. Classification Boundaries

### Sample-size status

| Value | Meaning |
|---|---|
| `SINGLE_EVENT_LOW_SAMPLE` | Only one event in the fixture group. Low sample — advisory context only. |
| `SMALL_SAMPLE_REVIEW_ONLY` | 2–4 events. Review-only context. |
| `SUFFICIENT_FOR_RESEARCH_CONTEXT` | 5+ events. Sufficient for research context only. |
| `NOT_EVALUATED` | No events found. |

None of these statuses imply wallet skill, copyability, or trading authorization.

### Signal category

Allowed signal categories (all are advisory observations, not instructions):

- `SPECIALIST_ENTRY`
- `MULTI_WALLET_CLUSTER`
- `EARLY_ENTRY_BEFORE_PRICE_MOVE`
- `LATE_CHASER`
- `MARKET_MAKER_FLOW`
- `ARBITRAGE_FLOW`
- `SUSPICIOUS_TIMING`
- `LOW_SAMPLE_OUTLIER`
- `UNCOPYABLE_FAST_FLOW`
- `UNKNOWN_WALLET_SIGNAL`

Forbidden values (never emitted by this module):
`BUY`, `SELL`, `TRADE`, `EXECUTE`, `OPEN_POSITION`, `CLOSE_POSITION`,
`POSITION_SIZE`, `EXPECTED_RETURN`, `PROFIT_TARGET`, `STOP_LOSS`,
`LIVE_SIGNAL`, `AUTO_COPY`, `TRADE_READY`, `COPY_READY`, `LIVE_READY`,
`BUY_SIGNAL`, `SELL_SIGNAL`.

### Specialization match

- `MATCHED_CATEGORY_CONTEXT`: fixture has a known market category.
- `UNMATCHED_CATEGORY_CONTEXT`: category present but not recognized.
- `UNKNOWN_CATEGORY_CONTEXT`: category field missing or empty.

### Suspicious-flow status

- `NO_SUSPICIOUS_FLOW_FLAG`: no suspicious flow flag in the fixture review section.
- `SUSPICIOUS_FLOW_RESEARCH_WATCH_ONLY`: suspicious flow flag present, research watch only.
- `SUSPICIOUS_FLOW_HUMAN_REVIEW_REQUIRED`: suspicious flow flag and human review required flag present.

Suspicious flow is **research-watch-only** or **human-review-required**. It is
never a strategy input, copy-trading trigger, automation input, or paper/live
trading signal. The project must not build a strategy whose purpose is to follow
suspicious or privileged-information flow.

### Copyability status

- `NOT_EVALUATED`: not enough information to evaluate.
- `COPYABILITY_UNPROVEN`: copyability context available but not yet evaluated.
- `UNCOPYABLE_FAST_FLOW`: copyability context unavailable; flow may be too fast.
- `SUSPICIOUS_FLOW_DO_NOT_COPY`: suspicious flow; do not use for copy-trading evaluation.

### Research priority effect

Allowed effects:

- `NO_CHANGE`
- `LOW_RESEARCH_BOOST`
- `MEDIUM_RESEARCH_BOOST`
- `HIGH_RESEARCH_BOOST`
- `CAP_RESEARCH_PRIORITY`
- `REQUIRE_HUMAN_REVIEW`
- `BLOCK_FROM_AUTOMATION`

These effects are **advisory metadata only**. They may influence human research
queue ordering only as metadata. They do not modify scoring weights. They do
not create trade signals. They do not create position sizing outputs. They do
not authorize live or paper execution.

## 4. Research Queue Annotations

The `build_wallet_research_queue_annotations` function takes a list of
`WalletSignalResearchProfile` objects and returns advisory
`WalletResearchQueueAnnotation` objects.

Each annotation includes:
- `wallet_id_or_address`
- `market_id`
- `condition_id`
- `research_priority_effect`
- `human_review_required`
- `suspicious_flow_status`
- `sample_size_status`
- `signal_category`
- `advisory_label`
- `advisory_notice`

Annotations do **not** include: `buy`, `sell`, `entry`, `exit`, `position_size`,
`expected_return`, `profit_target`, `stop_loss`, `live_signal`, `execute`,
`auto_copy`, or any trade-like field.

## 5. Human Review Requirement

Profiles and annotations **require human review** before any use.

Suspicious-flow profiles require human review and are blocked from automation.
Single-event / small-sample profiles are low-confidence advisory context only.
Specialization match requires human validation of category relevance.

## 6. What This Module Does Not Do

- Does not fetch network or API data.
- Does not monitor real wallets.
- Does not compute copyability PnL or expected return.
- Does not produce buy/sell/trade/execute/position-sizing instructions.
- Does not modify scoring weights.
- Does not place orders, cancel orders, size positions, or override risk.
- Does not write files.
- Does not access credentials or authentication clients.
- Does not invoke LLM, Hermes, scheduler, dashboard, or bot loop.
- Does not run paper or live trading.
- Does not prove wallet skill.
- Does not prove copyability.
- Does not create trade recommendations.

Direct live execution remains forbidden until the full live boundary conditions
described in `docs/wallet_intelligence_research_signal_roadmap.md` are satisfied.

## 7. Module Location

`src/data_layer/wallet_signal_research_profile.py`

## 8. Safety Label

All profiles carry `advisory_label = "ADVISORY_ONLY_WALLET_SIGNAL_RESEARCH_PROFILE"`.
All annotations carry `advisory_label = "ADVISORY_ONLY_WALLET_RESEARCH_QUEUE_ANNOTATION"`.

## 9. Relationship to Other WPs

- WP78 (`wallet_trade_event_fixtures.py`) provides the validated input records.
- WP79 (this module) consumes WP78 records and produces advisory profiles and annotations.
- WP80 (future) will design copyability delay simulation and wallet intelligence
  report generation (local/offline/read-only only).
- WP81 (future) will design a wallet signal paper strategy contract after
  copyability evidence.

No WP from WP79 onward may add network ingestion, live execution, or automatic
copy-trading until all live boundary conditions are satisfied.
