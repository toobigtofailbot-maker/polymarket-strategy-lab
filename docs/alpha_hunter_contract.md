# Multi-Category Alpha Hunter Contract (S10-HERMES-ALPHA-HUNTER-01)

Status: governed by `docs/wp_specs/S10-HERMES-ALPHA-HUNTER-01/` (RUNTIME, risk 3, exact seven-path
scope; amendments A1-A3 independently reviewed). Operator: `tools/alpha/run_alpha_hunter.py`.
Authority: PUBLIC RESEARCH ONLY. No StrategyVersion, lifecycle record, ExecutionIntent, Gate C
permit, order, wallet/account read, credential read, deployment or capital. Live trading stays
DISABLED (`docs/live_trading_authorization.md`).

## 1. Commands

    run    --scratch-dir ABS --alpha-registry ABS --categories nba,rain
           [--research-budget ABS_JSON --hermes-executable ABS --hermes-home ABS]
    verify --scratch-dir ABS

Paths must be absolute and outside the checkout. The Alpha registry must already exist (the
operator never initializes it). The three Hermes flags are all-or-nothing. `run` is one finite
STARTED-first operation under the kernel lock with at most 64 public GETs and 180 s of
acquisition. `verify` re-derives every completed manifest from stored bytes with zero network and
zero Hermes dispatch, and fails on any changed input byte.

## 2. Categories and independent sources

| Category | Market family | Independent source | Method |
|---|---|---|---|
| `SPORTS_NBA_MONEYLINE` | merged shadow discovery URL, exact `rule()` template | ESPN Matchup Predictor | `espn-nba-pregame-v1` (unchanged; 0.5 cancellation hull) |
| `WEATHER_US_DAILY_RAIN` | `where-will-it-rain-on-<month>-<d>-<yyyy>` for the two dates after the operation's UTC anchor date; merged `parse_rain_slug`/`parse_rule`, `LAST_BEFORE_1400_ET`, trace is No, CLI `issuedby` = station without `K` | `api.weather.gov` station -> points (4 dp, trailing zeros stripped) -> gridpoint `probabilityOfPrecipitation` | `nws-gridpoint-pop-climate-day-v1` |

Rain bounds over the LST climate-day window: lower = max PoP of intervals fully inside the window
(0 if none); upper = min(1, sum p_i x ceil(overlap hours)); point = 1 - prod(1 - p_i x h_i/d_i),
clamped. Labels: `BOUNDS_OVER_POP_INTERVALS`, `RUN_LENGTH_VALUE_ASSUMED_INTERVAL_POP`,
`INTERVAL_INDEPENDENCE_AND_UNIFORM_WITHIN_INTERVAL`, `GRID_CELL_EQUALS_STATION`,
`CLI_PUBLICATION_DEADLINE_UNMODELLED`, `SUB_THRESHOLD_INTERVAL_SUMS_UNMODELLED`, calibration
`UNPROVEN`. A gridpoint older than 6 h at the source cutoff is `SOURCE_STALE`. Crypto is excluded.

Protocol V2 (A3): a market is V2 iff its `positionIds` equal its `clobTokenIds` as a set, or its
market or event slug starts with `polyv2-`. On 2026-10-27 all 55 open NBA CTF markets carried
`positionIds` distinct from `clobTokenIds`, so presence alone is not a V2 marker. A V2 market with
null `positionIds` and no `polyv2-` slug would only be caught by the identity checks (accepted risk).

## 3. Venue economics and small-order indication

Single best-ask level, taker only, fixed research quantity 10 shares (numeric parity with the
shadow operator; parity is numeric only - the action rule intentionally differs). Minimum order
follows repo truth (`evaluator._minimum_order`): CLOB `min_order_size` is shares and Gamma
`orderMinSize` is USD notional; the official order docs describe size in shares and that dispute
is recorded in the deferred log, not reinterpreted. Book age = evaluation time - book timestamp
<= 30 s. Fee = native `_taker_fee` with the Gamma rate and exponent, rounded up to 0.00001; when the
Gamma rate differs from the documented category taker rate (fees page read 2026-10-27: Sports
0.05, Weather 0.05) the row carries `fee_rate_source_disagreement` and the conservative margin uses
the larger fee (same Gamma exponent). Disagreement is only set when fees are enabled.

`estimated_after_cost_margin = q*p - notional - fee - 0.005*q`; conservative/optimistic margins use
the payout bounds. `fill_probability` is null (`UNMEASURED`); `restricted` is recorded as
`restriction_observed`.

Small-order fit (research only, `HYPOTHETICAL_RESEARCH_ONLY_FULL_FILL_ASSUMED_FILL_PROBABILITY_UNKNOWN`):
largest 0.01-share q_s <= min(best-ask size, floor(5.00/ask)) whose cost with the cap fee is
<= USD 5.00; sub-reasons in order DEPTH_BELOW_FLOOR (none, or cost < 2.00), GAMMA_MIN_NOTIONAL_NOT_MET_WITHIN_CAP,
CLOB_MIN_SHARES_NOT_MET_WITHIN_CAP, MARGIN_NONPOSITIVE. **Expected consequence:** with a USD 5 Gamma
minimum, any positive cap fee makes a <= USD 5 fee-inclusive order impossible, and with fees
disabled only an exact USD 5.00 notional on the 0.01 grid fits, so the selected set is almost
always empty. This is reported, never worked around; it is a WP2 policy input.

## 4. Classes, reasons, funnel, ranking

Classes are exactly `RESEARCH_CANDIDATE` and `NO_TRADE`, fixed through the margin stage.
`SMALL_ORDER_UNFIT`, `HERMES_CONTRARY_EVIDENCE` and `CAPACITY_NOT_SELECTED` are non-selection reasons
on research candidates only. Every row carries one closed reason (first failing stage); reused
native codes map by the fixed table in prompt 6.5, anything inside `rule()` is `RULE_UNSUPPORTED`,
and `UNMAPPED_NATIVE_CODE` is fatal only for codes outside the listed functions. Funnel drops:
observed->eligible (PROTOCOL, RULE, ACQUISITION_CAPACITY), eligible->source_supported (IDENTITY,
DUPLICATE, SOURCE_UNAVAILABLE, LOOKAHEAD, SOURCE_STALE, EVENT_OR_CLIMATE_DAY_STARTED),
source_supported->probability_assessed (COVERAGE, PROBABILITY_INVALID, INDEPENDENCE,
MARKET_UNAVAILABLE - this last bucket includes markets whose probability was computed but whose
venue state was unavailable). Token stages: assessed (2 x assessed markets) >= venue_feasible >=
positive margin >= small_order_fit >= not_contested >= selected (top 10). Rank: research tier, then
margin/notional desc, conservative margin desc, category, market, token. Non-finite input is fatal.
The alpha-discovery queue is recorded, never gating.

## 5. Hermes research stage

No budget file -> zero dispatch, `run_mode=PUBLIC_SCREENER_NO_HERMES`: an honest screener, not
proof of Hermes inference. With a budget (ceilings: 3 runs/invocation, USD 0.50/run, 20 runs and
USD 5 per rolling 7 days; `ledger_scratch_dir` must equal `--scratch-dir`, so the ledger is scoped
to that directory) the operator researches RESEARCH_CANDIDATE tokens in provisional rank order
(small-order fit is not required, so budget can be spent on tokens that can never be selected; a
tier change on such a token still counts toward the milestone). Each dispatch goes through the
merged controller (`context_mode=False`, zero automatic retries) wrapped in ALPHA-REAL-01
`CaptureBackend`; its exclusive sentinel `hermes-<NN>.sentinel.json` carries `reserved_usd` and is
counted even after a crash. Lists come only from `revalidate_full_draft`. Origin uses `isinstance`
on the wrapped backend: `FakeHermesBackend` -> `OFFLINE_FIXTURE_MODEL_ORIGIN_UNVERIFIED`;
`ExternalHermesCliBackend` with verified provider/model -> `REAL_PROVIDER_REPORTED`
(provider-reported, not attested). Only a valid, revalidated, source-backed, token-bound
REAL_PROVIDER_REPORTED finding whose `end_utc` lies between operation start and influence
evaluation changes the research tier (contrary evidence -> contested, never selected; non-empty
`evidence_for` without contrary -> corroborated). Hermes never changes probability, bounds,
margins, small-order fields or class. Sources are mapped with this WP's provenance prefix (not the
ALPHA-REAL-01 `map_sources` prefix). Milestone `SATISFIED_REAL_PROVIDER_INFLUENCE` only when a
REAL_PROVIDER_REPORTED finding changed a tier; otherwise `UNSATISFIED_REAL_INFERENCE_NOT_DEMONSTRATED`.

## 6. Alpha lineage

Per eligible market: one OpportunityCandidate whose inputs are a pure function of (category,
method, market, condition, rule hash) - reruns are idempotent; one HypothesisFamily per method; one
DETERMINISTIC_ANALYSIS episode per run chained to the current leaf, referencing the manifest row
digest. No economic field names enter Alpha records.

## 7. Transport note

The shadow `bounded_body` probes the raw socket; on this Windows host api.weather.gov and small
CLOB responses expose none (WinError 10038) and the failed probe empties the body. The hunter
therefore uses one byte-capped read bounded by the 20 s socket timeout (deferred-log row records the
shadow observation; the shadow operator is unchanged).
