# Current Public Execution Feasibility Contract (S10-EXEC-FEAS-01)

## 1. Purpose

Answer one narrow question: can this exact proposed execution intent be mechanically supported
by currently observable public Polymarket venue state, and which execution frictions or unknowns
are visible? The answer is a current-public mechanics assessment only. It does not decide
strategy merit, Hermes preference, profitability, formal WP172 executable edge, account balance or
allowance, portfolio risk, Gate C, signing or submission.

Governing invariant: execution feasibility says whether the current public venue mechanics
support an exact intent. It does not say whether the strategy is good, whether the account is
allowed to act, or whether the system may trade.

## 2. Architecture position

Known-candidate path: S10-STRAT-LIFE-01 (MERGED) -> S10-HERMES-STRAT-01 (MERGED) ->
S10-EXEC-FEAS-01 (this package) -> S10-GATE-C-EXPLORE-01 (NOT AUTHORIZED / NOT STARTED) ->
S10-DEPLOY-EXEC-01 -> S10-LIVE-ORCH-01. ALPHA-03, DATA-03, S10-CC-FOUND-01 and S10-DEPLOY-01 host
activation are parallel and unchanged; ALPHA-03 is not a prerequisite.

Three execution concepts stay distinct: qualification evidence availability (metadata only,
unchanged); this current public execution feasibility; and WP172 formal executable edge (the
durable preregistered/OOS evidence lane, unchanged).

Source: `src/execution_feasibility/` — `models.py` (canonical helpers, records, vocabularies,
StrategyVersion binding), `public_market.py` (bounded GET-only acquisition and normalization),
`evaluator.py` (pure evaluation), `__init__.py` (small public API).

## 3. Current public source contracts (frozen 2026-10-03)

- Gamma `GET https://gamma-api.polymarket.com/markets/<GAMMA_MARKET_ID>`: identity (`id`,
  `conditionId`, `clobTokenIds` as a JSON-encoded string or list), state (`active`, `closed`,
  `acceptingOrders`, `enableOrderBook`, `restricted`, `negRisk`) and trading configuration
  (`orderPriceMinTickSize`, `orderMinSize` = minimum USDC notional per order, `feesEnabled`,
  `feeSchedule.{rate, exponent, takerOnly, rebateRate}`, `secondsDelay`).
- CLOB `GET https://clob.polymarket.com/book?token_id=<TOKEN_ID>`: `market`, `asset_id`,
  `timestamp` (epoch ms), `hash`, `bids`, `asks`, `min_order_size`, `tick_size`, `neg_risk`,
  `last_trade_price` (nullable). The wire presents bids ascending and asks descending; the package
  never trusts wire order and normalizes bids descending and asks ascending (best first).

Identity must match exactly (Gamma id/condition, token membership, CLOB market/asset) or the
source is INVALID with `SOURCE_IDENTITY_MISMATCH`. Book levels require 0 < price < 1, size > 0,
unique prices per side, at most 5,000 levels per side, and no crossed book (best bid < best ask);
an empty side is a valid state. Transport/HTTP failure -> source UNAVAILABLE; body, shape, schema,
size or identity violation -> INVALID. Unavailable or invalid facts stay null; nothing is invented.

## 4. Intent contract

`ExecutionIntent` (`polymarket-execution-intent` 1.0.0, id prefix `executionintent:sha256:`)
binds one exact `StrategyVersion` (revalidated by the STRAT-LIFE canonical round trip, never
mutated, never written) and `execution_rule_sha256 = "executionrule:sha256:" +
sha256(canonical_json({"execution_rule": spec["execution_rule"]}))`, always derived, never
caller-supplied. Venue ids: Gamma id 1..32 ASCII digits; condition id `0x` + 64 lowercase hex;
token id 1..100 ASCII digits. Closed vocabularies: side BUY/SELL; AGGRESSIVE_TAKER with FOK/FAK
(post_only false, no expiration); PASSIVE_MAKER with GTC/GTD (post_only true; GTC no expiration;
GTD expiration Unix seconds >= floor(information_cutoff_ns / 1e9) + 180). The venue applies a
one-minute security threshold, so a GTD order's effective lifetime ends about one minute before
its stated expiration; this package does not simulate a running order. requested_shares > 0;
0 < price_limit < 1 (BUY maximum, SELL minimum); 0 < max_public_data_age_ns <= 60 s. Numbers are
canonical decimal strings only; floats, NaN and non-canonical text reject.

## 5. Venue snapshot contract

`PublicExecutionVenueSnapshot` (`polymarket-public-execution-venue-snapshot` 1.0.0, prefix
`executionsnapshot:sha256:`) records ids, explicit acquisition start/completion nanoseconds,
per-source state (AVAILABLE / UNAVAILABLE / INVALID) and raw-body SHA-256, the normalized Gamma and
CLOB facts, normalized levels and closed source diagnostics. Book timestamps are normalized from
milliseconds to nanoseconds. Given identical read results and clocks, construction is
deterministic; repeated real acquisitions need not share an id because acquisition time is
evidence.

## 6. Evaluator and status semantics

`assess_execution_feasibility(intent, snapshot, evaluated_at_ns)` is pure; `evaluated_at_ns` must
be >= the snapshot completion time. Nine dimensions are always populated with PASS / LIMITED /
FAIL / UNKNOWN / NOT_APPLICABLE: market (active, not closed, accepting orders, order book enabled;
`restricted` is recorded only), identity (both sources available, negRisk agreement), freshness
(book timestamp not in the future and age <= max_public_data_age_ns; HTTP duration is never used),
tick (Gamma and CLOB tick must both exist and agree; exact Decimal `price_limit % tick == 0`),
minimum order (two independent hard dimensions, both required to exist: Gamma `orderMinSize` is a
minimum USDC notional compared with intent notional = requested_shares x price_limit
(`MINIMUM_ORDER_NOTIONAL_NOT_MET`), and CLOB `min_order_size` is a minimum share count compared
with requested_shares (`MINIMUM_ORDER_SHARES_NOT_MET`); the two values are never required to be
equal, a missing source is UNKNOWN, any failed inequality is FAIL with its exact diagnostic and
both passing is PASS — corrected by S10-LIVE-ORCH-01, which removed the frozen-base
`gamma_min != book_min` source-conflict branch that conflated notional with shares;
`MIN_ORDER_SOURCE_CONFLICT` stays in the closed vocabulary but is no longer emitted), book, fill,
fee and delay. Book-derived dimensions are
UNKNOWN unless the book is available and fresh.

Aggressive takers sweep visible opposing levels within the price bound (BUY asks ascending with
price <= limit; SELL bids descending with price >= limit). FOK needs a full visible fill; FAK with
zero fill is NOT_FEASIBLE and a partial fill is LIMITED. Metrics: visible_fill_shares, fill_ratio,
weighted_execution_price, slippage versus best ask/bid, visible_depth_capacity_shares (total
opposing depth) and price_bound_capacity_shares (depth within the limit) — market depth only,
never account capacity. Division-derived values are quantized to 18 decimal places in the
conservative direction (fill_ratio down; BUY VWAP up; SELL VWAP down); every other value is exact.
Passive makers are post-only: a BUY at or above the best ask, or a SELL at or below the best bid,
would cross and is NOT_FEASIBLE; an empty opposite side can rest. FEASIBLE for a passive order
means mechanically compatible with resting now, not that it will fill.

Positive Gamma `secondsDelay` makes an aggressive intent LIMITED (`MARKETABLE_ORDER_DELAY`); missing
delay is UNKNOWN for aggressive intents; delay is NOT_APPLICABLE for post-only passive intents.
Top-level precedence: any FAIL -> NOT_FEASIBLE; else any UNKNOWN -> INCONCLUSIVE; else any V1
limitation (FAK_PARTIAL_VISIBLE_FILL, MARKETABLE_ORDER_DELAY) -> LIMITED; else FEASIBLE. A missing
fact never overrides a known hard failure and absence of evidence never becomes PASS. Diagnostics
use one closed vocabulary, deduplicated in frozen precedence order; no raw upstream text appears.

## 7. Fee handling

Fee exactness is EXACT_ZERO_NO_FEES (fees disabled), EXACT_ZERO_MAKER (fees enabled, takerOnly
true, passive maker), CONSERVATIVE_5DP_UPPER_BOUND (aggressive taker with a complete supported
schedule) or UNKNOWN. Taker fees are computed per fill level and summed exactly:
`shares x rate x (price x (1 - price)) ** exponent`, integer exponent 0..8 only — never from the
VWAP alone. The venue rounds fee amounts to five decimals without a frozen rounding mode here, so
the package reports the exact theoretical value plus a five-decimal ceiling upper bound and never
claims the server-rounded fee. A missing, malformed, unsupported or non-taker-only enabled
schedule is UNKNOWN (INCONCLUSIVE for the affected style). For an aggressive taker the fee
dimension is PASS only when a fee was actually calculated: if the book is unavailable, invalid
or stale there is no usable fill path, so the fee dimension and exactness are UNKNOWN with null
amounts (no fee is invented from the limit, best price or notional). A usable book with zero
visible fill deterministically records a zero executed fee. The rebate rate is informational;
`expected_maker_rebate_usd` is always null.

## 8. Unknowns and non-claims

Every assessment carries `client_latency_state = UNKNOWN` (null value), `adverse_selection_state
= UNKNOWN` (null cost) and, for passive makers, `passive_fill_state = UNKNOWN` (null probability);
aggressive intents record NOT_APPLICABLE passive fill. These visible limitations are never zero and
do not by themselves change the status. The assessment invariants `public_mechanics_only`,
`no_profitability_claim`, `no_account_capacity_claim`, `no_gate_c_authority`,
`no_order_authority`, `no_execution_authority` and `no_live_authority` are always true. No expected
value, edge, PnL, alpha, Sharpe or ROI is computed.

## 9. Network and authority boundaries

One explicit foreground acquisition performs at most two HTTPS GETs to exactly
`gamma-api.polymarket.com` and `clob.polymarket.com` on the default port: no redirects (rejected),
no retries, no backoff, no cookies, no authorization or credential headers, no proxy discovery,
5 s timeout, body caps 1,048,576 (Gamma) and 4,194,304 (CLOB) bytes read as cap + 1 with
Content-Length pre-rejection. The low-level transport itself fails closed before any request unless the URL is exactly
`https://gamma-api.polymarket.com/markets/<1..32 digits>` (no query or fragment) or
`https://clob.polymarket.com/book?token_id=<1..100 digits>` (exactly that single parameter, no
fragment), with optional explicit port 443 and no userinfo; any other path, query or fragment is
NETWORK_HOST_FORBIDDEN. No other endpoint (orders, auth, balances, allowances, positions,
private trades, open orders, wallet, geoblock, RPC, WebSocket, Data API) is used. Importing the
package performs no network, file write, database open, thread, process, sleep or environment
read. There is no persistence. Records are bounded: 262,144 canonical bytes, depth 12, 20,000
nodes, 64 diagnostics; a book too large for that record is an INVALID source.

## 10. Relationship to WP172

WP172 remains the formal durable executable-edge evidence lane. This package does not import,
rename, reuse or weaken `EXECUTABLE_EDGE_PASS`, its queue model or its ordering assumptions, and no
EXEC-FEAS status is equivalent to a WP172 PASS.

## 11. Relationship to future exploratory Gate C

A merge establishes only CURRENT_PUBLIC_EXECUTION_FEASIBILITY_CORE_MERGED and makes
S10-GATE-C-EXPLORE-01 separately draftable; it does not start it. A future exploratory Gate-C
permit is expected to bind an `execution_feasibility_assessment_id` plus freshness together with
policy, strategy, Hermes decision, allocation, market/order scope, expiry, runtime identity and
account/access/reconciliation state. None of that is implemented here.

## 12. Test and evidence posture

All capability tests live in `tests/execution_feasibility/test_execution_feasibility.py` and use a
deterministic fake transport and explicit clocks; no real network is used and real external calls
during implementation/CI are 0. Merge evidence is deterministic; a live public probe is not a CI
success criterion. Each record round-trips through the exact closed loader and rejects tampered
ids, wrong prefixes, dropped fields and modified identity fields.
