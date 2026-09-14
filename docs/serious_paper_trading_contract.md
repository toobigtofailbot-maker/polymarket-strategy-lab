# Serious Paper Trading System Contract

## Status and authority

WP173 owns deterministic simulated-paper session, intent, order, fill,
accounting, risk, journal, recovery, foreground runtime, and read-only cockpit
projection evidence. Its governance track is RUNTIME and its authority is
`SIMULATED_PAPER_ONLY`.

The centralized boundary groups in
`docs/ai/codex/PROTECTED_PATHS.md` remain controlling. WP173 does not authorize
credentials, authentication, wallets, signing, private account data, venue
orders, real execution, live trading, Hermes/model authority, an OS scheduler,
a daemon, a service, or a new external product-network client. It does not
write WP169, WP170, or WP172 evidence. WP174 Auth / Signing / Execution Gateway
is separately gated.

## Eligibility and immutable records

A `PaperStrategyBinding` is valid only when both the complete WP172
`ExecutableEdgeAssessment` and its exact `ExecutionCostModel` validate, the
assessment is `EXECUTABLE_EDGE_PASS`, `wp173_evaluation_eligible` is true, the
cost-model IDs match, and the fee regime is known. The binding retains the
assessment, decision-trace, market-lineage, experiment, first-look, and cost-model
identities and freezes execution mode, fees/rebate, latency, passive TTL, queue
multiplier, markout horizon, and maximum data age. It cannot broaden WP172.

`PaperIntent` is content-addressed and binds one market/asset, BUY or SELL,
positive Decimal-string quantity, reference price, decision receive time, and
the binding's exact `AGGRESSIVE_TAKER` or `PASSIVE_MAKER` mode. Passive TTL
comes only from the binding. It has no account, credential, or venue-order
field, and submission always creates and persists a risk decision before an
order may become OPEN.

Order states are closed: `PENDING_RISK`, `REJECTED`, `OPEN`,
`PARTIALLY_FILLED`, `FILLED`, `CANCELLED`, and `EXPIRED`. Terminal orders never
reopen. Identical intent retries return the existing order; identity collisions
with different content fail closed. Fills are explicitly
`SIMULATED_PAPER_FILL`, use a per-order monotonic sequence, retain WP169/WP172
market-truth lineage, and never claim a venue order or trade ID.

## Risk and accounting

Every session freezes initial cash, single-order, per-market, total-gross,
open-order, session-drawdown, UTC-day-loss, minimum-free-cash, market-age, and
optional position-quantity limits. Risk decisions are canonical ALLOW/DENY
records with a fixed reason-code order. No caller, strategy, cockpit, AI, or
Hermes path can override a decision or mutate limits.

Gross-exposure admission counts current marked positions until fills change
them, remaining open BUY exposure, and candidate BUY exposure. A SELL that
passes the owned free-position check is reduce-only: it reserves quantity but
does not add new gross exposure. An unfilled SELL is never subtracted from held
gross and therefore cannot manufacture capacity for another BUY.

The spot-token ledger uses `Decimal` only. BUY reserves quantity at the maximum
unit payoff plus the frozen taker fee, and can never make free cash negative.
SELL reserves owned quantity and cannot borrow or short. Partial fills reduce
reservations proportionally; cancel, expiry, kill, and resolution release them.
Buy fees enter weighted-average cost basis. Reductions recognize net proceeds
less removed weighted basis. Session and UTC-day realized PnL are retained;
unrealized PnL and equity use only a current, non-gapped, non-crossed, two-sided
mid and are unavailable when the required mark is unavailable or stale.

Unambiguous resolution cancels open orders and settles each held outcome at
one for the winner and zero otherwise. Missing or ambiguous mapping records
`RESOLUTION_PENDING`, freezes new orders for that market, and never guesses.

## Fill equivalence

Aggressive orders arrive at decision receive time plus frozen latency, select
the latest valid book known by receive time at arrival, sweep visible opposing
depth, and preserve partial fills. Spread, depth slippage, latency, and fees use
the same formulas as WP172. Insufficient depth is never fabricated.

Passive orders initialize queue ahead as visible same-price size times the
frozen multiplier. A touch or book update alone cannot fill. Only eligible
opposite-aggressor trade flow after arrival consumes queue, and only excess
flow fills at the frozen limit before TTL. Fee/rebate treatment is identical
to WP172. Per-order arrival and horizon references yield the same adverse
selection markout, or an explicit `MARKET_DATA_UNAVAILABLE` result.

The `run_wp172_replay` adapter validates the exact decision trace and market
window identities frozen in the binding before constructing intents/events.
The generic replay boundary accepts only validated immutable paper events and
intents, orders equal-time market truth before decisions, and produces
deterministic journal/state identities.

## Persistence and reconciliation

The caller selects a dedicated lowercase `.sqlite3` paper store. Paths, parents,
schema application ID, user version, exact table definitions, integrity, and
single-link/no-symlink rules are checked. Each logical mutation is one SQLite
transaction.

The append-only journal is authoritative. Each row commits its monotonic
sequence, stable event ID/type/time, canonical payload, previous-event hash,
event hash, and canonical state after the transition. Startup verifies the
complete chain, canonical payloads, checkpoint hash, every replayed state and
its order/fill/risk/account relationships, then compares the replayed terminal
state with the materialized checkpoint. Mismatch or corruption is
`RECONCILIATION_BLOCKED`; no new order can open. A transaction failure rolls
back journal and checkpoint together, so no fill exists without its order,
accounting state, and audit evidence.

Each engine retains the exact checkpoint head used for reconstruction. Every
mutation compares that expected head with the persistent head inside the same
`BEGIN IMMEDIATE` transaction that would append the mutation. A mismatch rolls
back and fails closed as `STALE_PAPER_STATE`; the stale engine enters local
`RECONCILIATION_BLOCKED` and cannot overwrite the newer journal/checkpoint.
Successful commits advance the engine's expected head. Operationally, one
long-lived engine is the active writer: an external CLI writer is allowed, but
causes the long-lived engine to fail closed on its next poll and requires a
clean operator restart.

## Runtime and controls

`REPLAY` is finite and deterministic. `LIVE_STORE` opens one caller-selected
WP169 store with SQLite URI `mode=ro`, validates its application/schema
identity, and tails only accepted canonical observations and explicit gap
events in receive-time order. The bounded foreground poll loop creates no
external client and installs no scheduler or background service. Every poll
checks the paper-store head before reading WP169, including polls with no new
market event, so an external paper mutation cannot be clobbered.

For accepted WP169 `market_resolved` observations, the adapter retrieves the
exact linked raw WebSocket occurrence, revalidates its raw/occurrence hashes,
source domain, normalized identity, timestamp, provenance, and child index,
then accepts the current official `winning_asset_id` only when it is a valid
token and belongs to `assets_ids` when that array is present. Missing,
malformed, contradictory, or unverifiable raw resolution evidence emits an
ambiguous resolution and remains `RESOLUTION_PENDING`; outcome labels and
array positions never imply a winner.

Control states are `RUNNING`, `PAUSED`, `KILLED`, and
`RECONCILIATION_BLOCKED`. PAUSED denies new orders. Resume is valid only from
PAUSED. KILLED cancels remaining simulated orders, is terminal, and cannot be
resumed. Reconciliation blockage has no manual override.

The CLI exposes explicit-path `init`, `run`, `submit-intent`, `cancel`, `pause`,
`resume`, `kill`, and `status` operations over bounded validated JSON. It does
not load code dynamically, execute shell input, accept secrets, select a live
mode, or create a product-network client.

## Cockpit projection

The existing loopback FastAPI/React cockpit may receive an optional paper-store
path. Six GET-only routes project summary, orders, fills, positions, risk, and
audit. List routes retain the existing default/minimum/maximum limit rules.
The backend opens the paper database read-only, verifies its chain/checkpoint,
and returns sanitized values without paths or raw payloads. The frontend adds
one compact Paper Operations view. Neither surface can submit/cancel orders,
change controls or limits, write evidence, or start execution.

Paper results are forward-simulation evidence, not proof of future profitability
and never rewrite WP170/WP172 research evidence. Negative results and rejected
orders remain in the journal.
