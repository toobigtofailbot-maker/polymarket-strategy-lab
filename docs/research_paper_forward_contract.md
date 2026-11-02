# Research-Paper Forward Loop Contract (S10-PAPER-FORWARD-01)

Operator: `tools/alpha/run_paper_forward.py`. Finite, offline, stdlib-only. It turns a frozen research-only plan and an imported, time-ordered candidate file into native WP173 research-paper intents, keeps an append-only hash-chained occurrence ledger, and reconciles the whole funnel with the unchanged native snapshot. It has no execution, live, credential, provider, scheduler or capital authority. Its outputs are simulated research-paper evidence only, never a venue return, edge, qualification or OOS claim.

## Commands

All paths are explicit. The run directory and manager store must be outside the repository (`PATH_INSIDE_REPOSITORY`). A socket guard rejects any network attempt (`NETWORK_ATTEMPTED`).

| Command | Purpose | Writes |
|---|---|---|
| `run --plan P --candidates C --run-dir R --max-decisions N (--replay-events J \| --market-truth-store S.sqlite3) [--max-market-events K] [--finish-time-ns T]` | One finite pass; rerun on the same `R` is the resume path | `R/ledger.jsonl`, `R/paper_store.sqlite3`, `R/report.json` |
| `verify --plan P --run-dir R` | Cold check of chain, plan hash, native snapshot and funnel | nothing |
| `feedback --plan P --run-dir R --feedback-input F --manager-store M [--lifecycle-store L]` | Optional offline PERFORMANCE_UPDATE | only `M` |

Exit codes: 0 means success. 1 is a fail-closed rejection with a stable `reason_code`. 2 is a usage error.

## Input schemas

Prices, sizes, money and fees are decimal strings. JSON floats are rejected, except in the native usage record inside the feedback input.

- **Plan** (`s10-paper-forward-plan-v1`), with keys `frozen_at_ns`, `session_label`, `binding`, `risk_limits`, `rule`, `fee`, `outcome_handling` and `strategy_version_id`:
  - `binding` holds the native `build_research_strategy_binding` arguments. They must use `reserved_evidence_policy` NON_CONFIRMATORY_RESEARCH_PAPER and empty `reserved_evidence_refs`. Cohort = `allowed_market_ids`; the latency, age and fee bps fields are the native binding fields.
  - `risk_limits` holds the native `PaperRiskLimits` fields.
  - `rule` is `{name: FAIR_VALUE_EDGE_V1, min_edge, max_quantity}`.
  - `fee` is either `{basis: CONSERVATIVE_UPPER_BOUND_ESTIMATE, fee_rate, fee_exponent, maker_rebate_bps}` or `{basis: SYNTHETIC_TEST_ONLY}`.
  - `outcome_handling` is `NATIVE_SETTLEMENT_ONLY`.
  - `strategy_version_id` is a string or null.
- **Candidates** (`s10-paper-forward-candidates-v1`) is a list of rows `{occurrence_id, market_id, asset_id, fair_value, source_time_ns, decision_time_ns}`:
  - Rows must be ordered by non-decreasing `decision_time_ns`.
  - `frozen_at_ns` must be earlier than every source time and decision time.
  - Two different occurrences may not share an `(asset_id, decision_time_ns)` pair, because native intent ids are content-derived (`CANDIDATES_OCCURRENCE_COLLISION`).
- **Replay** (`s10-paper-forward-replay-v1`) has `label` set to SYNTHETIC_TEST_ONLY or IMPORTED_UNVERIFIED, and native `PaperMarketEvent` fields with unique lineages and non-decreasing receive time. The alternative source is a WP169 store, read through the native `Wp169ReadOnlyTail` (`mode=ro`) in one bounded read. A read that does not reach the end of the store fails closed with `WP169_READ_INCOMPLETE` before any decision, because otherwise a later decision could use a book that unread earlier events replaced.

Units: prices in USDC per share in [0,1]; quantities in shares; time in ns since the Unix epoch, UTC; `fee_rate_bps` in basis points of fill notional.

## Decision semantics

Each candidate is decided in this order:

1. **Process prior market data.** Process only market events with `receive_time_ns < decision_time_ns`. Events at or after the decision time come later.
2. **Classify the candidate.** The first class that applies wins:
   - `COST_UNKNOWN`: the fee is not a proven bound.
   - `WRONG_SCOPE`: the market is outside the cohort or the decision is outside the binding window.
   - `SOURCE_FUTURE`: `source_time_ns >= decision_time_ns`, or the native market state is already at or after the decision.
   - `SOURCE_GAP`: there is no book, or the book is gapped.
   - `WRONG_SCOPE`: the asset's book belongs to another market.
   - `SOURCE_STALE`: `decision_time_ns - book.receive_time_ns > max_data_age_ns`. This is checked per exact asset, not per feed.
3. **Apply `FAIR_VALUE_EDGE_V1`.** With `fee_bound(p) = p * fee_rate_bps / 1e4`:
   - **No position held:** BUY `max_quantity` if `fair - ask - fee_bound(ask) >= min_edge`.
   - **Position held:** SELL the free held quantity if `bid - fee_bound(bid) - fair >= min_edge`.
   - **Otherwise:** `ABSTAINED_NO_TRADE`.

   The reference price is the touched side for AGGRESSIVE_TAKER. For PASSIVE_MAKER it is the joined own side; the edge is still evaluated against the far side.
4. **Submit.** The intent is submitted through native `PaperEngine.submit`, which applies risk, fills, fees, accounting and settlement unchanged.

**Fee bound:** CONSERVATIVE_UPPER_BOUND_ESTIMATE is accepted only when all of these hold:
- `fee_exponent` is an integer of at least 1;
- `fee_rate` is at least 0;
- both rebates are 0;
- the binding's `fee_rate_bps >= fee_rate * 1e4`.

Then `rate*(p(1-p))^e <= rate*p <= p*bps/1e4` for every p in [0,1]. Anything else gives COST_UNKNOWN for every candidate. Fees are always reported as ESTIMATE, never as exact venue fees.

## Ledger, funnel and restart

`ledger.jsonl` is append-only. Each line is canonical JSON `{seq, prev, kind, body, hash}`, with `hash = sha256(canonical(seq, prev, kind, body))`, and each line is flushed with fsync. The entry kinds are:

| Kind | Content |
|---|---|
| `PLAN_FROZEN` | Always first. Holds the plan byte SHA-256, session id and `plan_evidence_class` LOCAL_RUN_ORDER. This proves local run order only, not preregistration or prospective/OOS status. |
| `RUN_INVOKED` | Candidate byte SHA-256, labelled IMPORTED_UNVERIFIED_SIGNAL; market source |
| `STARTED` | Written before any engine call for one unique occurrence |
| `TERMINAL` | One immutable terminal per started occurrence |
| `DUPLICATE_SUPPRESSED` | A repeated row of a claimed occurrence. It has no STARTED and no submit, and records whether the content matches. |
| `RUN_FINISHED` | Snapshot id and paper head |

The terminal classes are:
- **No-trade classes:** `ABSTAINED_NO_TRADE`, `SOURCE_FUTURE`, `SOURCE_STALE`, `SOURCE_GAP`, `WRONG_SCOPE`, `COST_UNKNOWN`.
- **`ATTEMPTED_INTENT`:** the submission outcome only. It records the native `intent_id` and `order_id`, `risk_permitted`, and `initial_status`. `initial_status` is OPEN or REJECTED, taken from the native risk decision, so it is identical on the fresh and recovery paths. It deliberately does not capture a fill that native `submit` might apply immediately; later fills appear only in the as-of order state.
- **`RECOVERED`:** a committed native intent found after a crash. It is bound once and never resubmitted.
- **`INTERRUPTED_OR_UNKNOWN`:** STARTED with no committed native intent. It is never retried under a new identity.

**Order state as of the snapshot cutoff** is derived at report and verify time from the verified native PaperStore:
- `OPEN` and `PARTIALLY_FILLED` are nonterminal.
- `REJECTED`, `FILLED`, `CANCELLED` and `EXPIRED` are closed.
- `not_filled_count` and `not_filled_quantity` are observations, never terminals.

Past terminals are never rewritten.

**Reconciliation:** every report requires all of the following, otherwise `FUNNEL_RECONCILIATION_BLOCKED`:
- `raw_candidate_rows = unique_occurrences + suppressed_duplicate_rows`;
- `unique_occurrences = count(STARTED) = count(terminals)`;
- ATTEMPTED_INTENT + RECOVERED = native `intent_count`, with the intents equal to the native orders;
- the number of `risk_permitted=false` terminals = native `risk_deny_count`;
- the per-status counts sum to `order_count`, and the closed counts equal native `closed_order_state_counts`.

A row is identified by `(candidates_sha256, row_index)`. Re-reading the same file adds nothing. `RUN_FINISHED` records `input_file_rows` and `input_rows_not_reached`, the rows a `--max-decisions` bound left for a later run. Rows not yet reached are outside the funnel denominator. Market events already applied, identified by their lineage in the native journal, are skipped.

**Resume checks:**
- On resume, the chain and plan hash must match, and the paper session must be the ledger's own.
- After a clean `RUN_FINISHED`, the store head must equal the recorded head (`PAPER_STORE_FOREIGN`).
- After a crash, every native journal event past the last head recorded in the ledger must come from this run: a market event whose lineage is in the current source, or the pending order of an open occurrence. Control changes and manual or kill cancellations count as foreign (`PAPER_STORE_FOREIGN`).
- A writer changing the store during a run trips the native stale-writer guard (`STALE_PAPER_STATE`).
- A torn last ledger line, or a crash between creating the paper store and writing `PLAN_FROZEN`, fails closed (`LEDGER_TAMPERED` or `PAPER_STORE_FOREIGN`). Such a run directory is abandoned, and a new run directory is required.

## Closure, feedback and report

**Closure:** P&L is realized natively by SELL fills and winner-bearing resolutions.
- Winners are labelled WP169_ACCEPTED_OBSERVATION only when they come from the WP169 hash-bound path. Replay winners are IMPORTED_UNVERIFIED_RESOLUTION.
- A null winner stays pending.
- Held positions are listed as UNSETTLED_RESOLUTION_PENDING or UNSETTLED_OPEN.
- Missing marks report unrealized P&L as `UNKNOWN`, never 0.
- `all_positions_closed` is derived from positions, never from `resolution_pending_count`.

**Feedback:** native `run_paper_performance_update` is called only when all of these hold:
- the plan names a `strategy_version_id`;
- a lifecycle store is given;
- that version exists and lists the binding `candidate_id` in `evidence_refs`.

Otherwise the result is `FEEDBACK_PENDING_NO_MATCHING_LIFECYCLE` with zero backend calls. The backend is the existing `_EchoDraftBackend` (a FakeHermesBackend) answering with the operator's fixed offline draft. Any native rejection, such as `BACKEND_NOT_OFFLINE`, `CUTOFF_NOT_ADVANCED` or `BINDING_STRATEGY_MISMATCH`, is returned unchanged. The paper store and lifecycle bytes are not written. Hermes output cannot change the plan, the binding or any privilege.

**Report labels:**
- `signal`: IMPORTED_UNVERIFIED_SIGNAL.
- `market_source`: SYNTHETIC_TEST_ONLY, IMPORTED_UNVERIFIED_MARKET_EVENTS or WP169_ACCEPTED_OBSERVATION.
- `fills`: SIMULATED_PAPER_FILL.
- `fee`: ESTIMATE, SYNTHETIC_TEST_ONLY or COST_UNKNOWN.
- `plan_evidence_class`: LOCAL_RUN_ORDER.
- `resolution`: WP169_ACCEPTED_OBSERVATION or IMPORTED_UNVERIFIED_RESOLUTION.

The report also carries the funnel counts and as-of order counts; the realized, unrealized and pending outcomes; authority flags (research-paper only, zero capital, no live, execution or Hermes authority); and claims flags that are all false.

## Limits

- No real source capture.
- No venue fee-config acquisition. The fee scenario is operator-supplied.
- No authentic settlement witness beyond the WP169 path.
- No recurring operation.
- Market source kind is fixed per run directory.
- One WP169 read per invocation is capped by `--max-market-events`, with a native maximum of 10000.

See `docs/deferred_items_log.md`, section S10-PAPER-FORWARD-01. The successor S10-PAPER-FORWARD-RUN-01 needs separate owner authority.
