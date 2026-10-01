# Weather Qualification Prospective OOS Accrual Contract (S10-QUAL-DATA-03)

Status: governed by `docs/wp_specs/S10-QUAL-DATA-03/` (RUNTIME, risk 3, exact 15-path scope).
Authority: PROSPECTIVE EVIDENCE ACCRUAL ONLY. This contract implements the DATA-03 seal frozen by
S10-QUAL-PLAN-01 without any analytic change. It computes no B1/B2 forecast, fits no model, exposes no label or
outcome, computes no Brier/log-loss/comparison statistic, constructs no QualificationCandidate, runs no
qualification gate and builds no WP170 object. No scheduler, cron, delayed trigger, watcher or background task:
every network action is a manual foreground command. Gate C: NOT AUTHORIZED. Live: DISABLED. Capital at risk:
USD 0. Orders: 0. Merge: NOT AUTHORIZED by this WP.

Code-merge state: `DATA03_IMPLEMENTED_NOT_STARTED`. `ACCRUAL_INCOMPLETE` is claimed only after a real post-start
accrual run has committed a provisional state.

## 1. Immutable plan binding

`prepare` verifies, with zero network: the PLAN-01 plan bytes in the working tree and in merge commit
`75e17927155dc7ffb5aebfba2f1d97ddd5c2f8b9` hash to `3b2a99abea8bbd18794c8117d6c1ab696ac817217cd5713367b2ee9a76aa9463`;
the power document's LF-normalized SHA-256 is `f20f24a26444c93389b10a34ed1a88530aca0f64bc7efb694dccce826c6ee884`;
the merge commit is the GitHub server merge (committer `GitHub`, parents `e2edb21e...` and `11244eed...`) at
`2026-10-01T02:39:26Z`, at or before the freeze deadline `2026-10-14T00:00:00Z`; and every plan literal DATA-03
depends on (oos_start `2026-10-15T00:00:00Z`, effective embargo lower bound `2026-10-17T00:00:00Z`, cap
`2027-02-12T00:00:00Z`, embargo 172800 s, 50 target dates, 100 rows per role, the B0 parameters, the closed
exclusion vocabularies, the membership preimage keys, the DATA-02 bundle
`weatherqualbundle:sha256:a5911ab05cc8c650377447aa46f65f3b2002fc458e3c51a64f8705b1adcc69ae` and dataset
`weatherqualdataset:sha256:a3e98a35ea052e1dfeb5225239a74beaee47d04111ebb34e6d27717490d9ac39`, which stay permanently
`HISTORICAL_NON_OOS`). Any mismatch is `STOP PLAN_FREEZE_INVALID`. PLAN-01 files are never edited.

## 2. Architecture

- Pure module `src/data_layer/analytical_research/qualification_oos_accrual.py`: pending/terminal types, row
  identity, stable prefix, B0 / q / L materialization, feature-column and label-store identities, the membership
  preimage/id, MR12 execution evidence, the ledger chain and the closed visible-report schema. No network, no files.
- Operator `tools/qualification/run_s10_qual_data_03.py`, the only network owner. It composes the unchanged
  DATA-01/02 operators (the DATA-02 bounded transport and 429/503 policy, typed per-hour PendulumFlow reads and the
  Gamma-by-id path through `PolymarketPublicClient.get_market`; the DATA-01 NDFD object access and provenance
  descriptors) and never subclasses the DATA-02 completion pipeline. Reused transports keep their frozen user agents.
- Byte-unchanged: `qualification_data_readiness.py`, the DATA-01/02 operators, `pendulumflow_v3.py`,
  `nws_ndfd_history.py`, `qualification.py`, `qualification_gate.py`, `experiment_os.py`, WP170/172/173 and every
  PLAN-01 file. No dependency, lock or workflow change.

## 3. Frozen prospective census

Scan days 2026-10-15 through 2027-02-11 inclusive (the 120-date window); discovery hours 11:00 and 12:00 UTC of
PendulumFlow v3 `new_market` only. Family admission is the frozen slug or question regex; the target date comes from
the slug; witness copies collapse by Gamma market id with the earliest receive; enrichment uses only
`get_market(id)` with mandatory v3/Gamma identity equality. No Gamma list/keyset discovery and no outcome-dependent
discovery. A market first appearing outside the 11/12 UTC census is outside this plan's population (a recorded
limitation, never backfilled).

A target date's market set is drawn from the census hours of scan days up to and including that date; copies in
later hours never move a market's earliest receive. **A required discovery hour that fails after the frozen retries
does not close the census**: the date stays `STRUCTURAL_CLASSIFICATION_PENDING` and the hour is retried on a later
manual run. An hour not yet ended or not yet published in the archive audit is not read. An empty or complete census
is never minted from a failed read.

## 4. Rows, checkpoints and identity

Checkpoints and windows are those of PLAN-01 / DATA-01: market-history lookback 24 h, NDFD lookback 48 h, label
window ±30 min around Gamma `closedTime`, checkpoint A `MARKET_OBSERVABLE_PLUS_60M_V1`, checkpoint B
`TARGET_CLIMATE_DAY_START_V1`. All cities and both checkpoints of a target date share one leakage role.

Row id `weatherqualoosrow:sha256:<64hex>` over exactly `{target_date, market_id, condition_id, checkpoint_id,
decision_time, yes_token_id}`; no label, B0, q/L value or outcome enters it. Exclusion subjects: MARKET = Gamma
market id, ROW = `<gamma_market_id>:<checkpoint_id>`, DATE = ISO target date; one closed reason per subject.

## 5. B0 and features (sealed values only)

B0 `EXTERNAL_PIT_MARKET_PROBABILITY_V1` (`max_midpoint_spread = 0.1`, `max_last_trade_age_seconds = 86400`): the
spread is recomputed from bid/ask; a valid two-sided Yes book (`0 < bid <= ask < 1`) with spread `<= 0.1` yields the
midpoint; otherwise the latest successfully searched Yes-token trade aged `<= 86400` s by `timestamp_received`; an
incomplete required trade search after a source-read failure is `MARKET_HISTORY_SOURCE_INVALID` (not
`B0_UNAVAILABLE`); a complete search without an eligible book or trade is `B0_UNAVAILABLE`. Every missing-data
decision precedes label access; no canonical PIT relabeling.

`q = clip(max overlapping PoP12_percent / 100, 0.01, 0.99)` and `L = (climate_day_start -
vintage_public_available_time) / 24 h` (exact signed seconds stored; the quotient rounded half-even to 1e-12 days)
are canonical decimal strings materialized only inside the sealed store. B1/B2 forecasts are forbidden.

## 6. Workspace and multi-run state

Workspace `local_data/s10_qual_data_03/accrual-01/` (ignored, never committed): `PLAN.json`, `PLAN.sha256`, `raw/`,
`INDEX.jsonl`, `runs/run-NNN/`, `CLASSIFICATION_LEDGER.jsonl`, `STATE.json`, `sealed/`.

- Raw blobs are content-addressed and immutable; `INDEX.jsonl` is append-only. The view of run `k` holds every
  successful entry of earlier runs (successful immutable bytes are reused, never redownloaded) and every entry of
  run `k`; failures of earlier runs are retried. Mutable sources (archive audit page, NDFD day listings, Gamma
  documents, the fee page) are versioned per run (`capture=run-NNN`) and never overwritten or backdated.
- Runs are sequential. A crashed run resumes with the same run number and `as_of`; its uncommitted ledger state is
  discarded. Only a completed run commits terminal entries; committed entries are hash-chained and immutable. Before
  any network acquisition each run verifies both chains and re-hashes every raw blob referenced by terminal entries.
- State: `DATA03_IMPLEMENTED_NOT_STARTED` -> `ACCRUAL_INCOMPLETE` -> `OOS_MEMBERSHIP_SEALED` or
  `QUAL_OOS_ROWS_INSUFFICIENT` or `QUAL_OOS_INSUFFICIENT_AT_CAP`. Final states are one-way: no post-seal `accrue`, no
  second `seal`.

## 7. Pending and terminal classification

`PENDING_LABEL_FINALITY` is a prospective market state, never an exclusion, never in the terminal ledger, never
counted toward D1..D50, with no elapsed-time timeout. Terminal label classifications: final Gamma + agreeing v3
resolution (internally label-known); disagreement `LABEL_SOURCE_DISAGREEMENT`; final Gamma + successful complete
label-window reads without a resolution `LABEL_V3_RESOLUTION_MISSING`; a published label-window read failing after
the frozen retries `LABEL_V3_SOURCE_READ_FAILED`. A Gamma finality re-poll failure stays pending (absence is never
minted). Initial Gamma enrichment failure keeps `GAMMA_UNAVAILABLE`. `LABEL_GAMMA_NOT_FINAL` is never emitted
prospectively.

`STRUCTURAL_CLASSIFICATION_PENDING` covers: a required discovery hour not yet successfully read; a required archive
hour not yet published/audit-measured; a checkpoint not yet reached; an NDFD listing captured before
`min(day end, checkpoint)` (not final for selection). A market whose rows are all excluded by pre-label reasons cannot
affect its date and is terminal without label evidence.

## 8. Stable chronological prefix

Considered dates are walked ascending: PENDING stops the walk (`ACCRUAL_INCOMPLETE`), EXCLUDED is skipped,
ELIGIBLE counts. A later date never leapfrogs an earlier pending date; dates after D50 never affect the prefix; a
formerly pending date that becomes excluded before the seal shifts the prefix mechanically. A date is classified
only when every market and row of it is terminal; its included rows decide `OOS_DATE_DECISION_BEFORE_START`,
`OOS_DATE_DECISION_IN_WP170_EMBARGO`, `OOS_DATE_DECISION_AT_OR_AFTER_CAP` or `OOS_DATE_NO_ELIGIBLE_ROW` (in that
precedence). Fewer than 50 eligible dates once the whole in-window population is terminal is
`QUAL_OOS_INSUFFICIENT_AT_CAP` (never while an earlier in-window date is pending); a stable 50-date prefix with fewer
than 100 rows is `QUAL_OOS_ROWS_INSUFFICIENT`. No extension.

## 9. OOS membership seal

`seal` (zero network, one-way) builds `oosmembership:sha256:<64hex>` over the canonical JSON (UTF-8, sorted keys,
compact separators, no floats/NaN/Infinity) of exactly `cap`, `data03_bundle_id`, `end_time` (MR09),
`oos_exclusions`, `oos_row_ids`, `oos_start`, `oos_target_dates`, `plan_01_plan_sha256`; dates ascending, row ids
ascending, exclusions ascending by `(target_date, subject_kind, subject_id)` covering every considered-date
exclusion through D50. The `weatherqualoosbundle:sha256:` bundle is structural: it binds the ledger head, the raw
index digest, D1..D50, rows, exclusions, ready manifests and MR12 states; sealed feature-column
(`weatherqualoosfeaturecolumn:sha256:`) and label-store (`weatherqualooslabelstore:sha256:`) ids stay inside the
sealed store. The seal is derived twice and must reproduce; a second seal or any later rewrite is refused.

## 10. Pre-release exposure firewall

Visible files and stdout carry only the allowlisted schemas: counts by closed reason, eligible row/date counts per
checkpoint, B0 availability and midpoint-vs-trade basis counts, coverage classes, network/reuse accounting,
aggregate ids/hashes, execution-evidence states, prefix length, total pending market/date counts and the earliest
pending date. Every string must match a closed shape; an extra key is a hard `VISIBLE_SCHEMA_VIOLATION`. Never
visible: label values, prevalence, per-market outcomes, Gamma outcome prices, B0/q/L values, per-row evidence hashes,
per-market pending flags, feature distributions, forecasts, coefficients, Brier/log-loss or comparison statistics.
`main()` prints only a validated report, `STOP <CODE>` or `STOP INTERNAL_ERROR:<ExceptionClass>`. Reviewers do not
inspect real `raw/`, `sealed/` or ledger contents to summarize results.

## 11. Execution-terms capture

Frozen fee source: `https://help.polymarket.com/en/articles/13364478-trading-fees` (host `help.polymarket.com`),
captured each run and versioned. MR12 per class over the D1..D50 markets: FEES (official fee page + every market's
Gamma fee fields + every rule cohort represented by a pre-close Gamma capture); RESOLUTION_RULES (every cohort
represented by captured open rule evidence); TICK_SIZE_MIN_ORDER (`orderPriceMinTickSize`, `orderMinSize` and a
complete v3 `tick_size_change` history; official tick-change semantics `NOT_CAPTURED_NO_AUTHORIZED_EXACT_SOURCE`);
SPREAD_DEPTH may remain PARTIAL (no depth capture); LATENCY and PARTIAL_FILL may remain MISSING. Captures after the
candidate evidence cutoff never count: current evidence is never backdated. A probe fee-page contract failure is
`STOP EXECUTION_TERMS_SOURCE_UNAVAILABLE`.

## 12. Network and budgets

Only HTTPS GET / Range GET to `archive.pendulumflow.com`, `noaa-ndfd-pds.s3.amazonaws.com`,
`gamma-api.polymarket.com`, `api.weather.gov` and the exact fee URL on `help.polymarket.com`. No redirect,
authentication, credential, WebSocket, POST/mutation, CLOB/order endpoint or browser automation. Retry: 429/503 at
most 3 retries after 2 s, 8 s, 30 s (an integer Retry-After in [0, 60] only lengthens); timeout/reset/truncation/408/
other 5xx one immediate retry; an exhausted read is typed failure or pending, never false absence.

- Per manual `accrue` run: `RUN_MAX_ATTEMPTS=12_288`, `RUN_MAX_BYTES=6_442_450_944`,
  `MAX_SINGLE_RESPONSE=268_435_456`, `RUN_MAX_PENDULUM_HOURS=2_000`. Exhaustion ends the run truthfully as
  `ACCRUAL_INCOMPLETE` and mints no exclusion; the next manual run continues.
- Cumulative: `CUM_MAX_ATTEMPTS=65_536`, `CUM_MAX_BYTES=34_359_738_368`, `CUM_MAX_PENDULUM_HOURS=6_000`,
  `MAX_ACCRUE_RUNS=64`, 120 considered dates, `MAX_CANDIDATES=4_096`, `MAX_STATIONS=128`. Exhaustion is
  `STOP ACCRUAL_BUDGET_EXHAUSTED` (never auto-raised).
- One implementation-time `probe-sources` before OOS start: `PROBE_MAX_ATTEMPTS=32`, `PROBE_MAX_BYTES=16_777_216`,
  `PROBE_MAX_SINGLE_RESPONSE=8_388_608`, `PROBE_MAX_PENDULUM_HOURS=4`; pre-OOS hours only; no OOS member, label,
  score or prospective dataset; `PROBE_PASS` required; a second probe is refused.

## 13. Provenance ceiling

`MAX_QUALIFICATION_PROVENANCE_MANIFESTS = 256`; existing <=256-item ready-subset sharding per date and source family
(PendulumFlow market history, NDFD weather, Gamma/NWS rule/label metadata); a date's rows need ready shards in all
three families. `prepare` computes exact N2 (DATA-02 ready manifests of the MR14 FORMATION/SELECTION dates) and, before
any prospective acquisition, `N2 + 150 > 256` is `STOP PROVENANCE_CEILING_UNREACHABLE`. Each run reports the
projected final count `N2 + actual prefix manifests + 3 x remaining dates`; above 256 it is
`STOP QUAL_PROVENANCE_LIMIT_EXCEEDED_UNAVOIDABLE`. No aggregation, substitution or omission.

## 14. Commands

`prepare` (zero network), `probe-sources` (one bounded pre-OOS probe), `accrue` (manual, refused before
`2026-10-15T00:00:00Z`, repeatable within cumulative caps until a final state), `seal` (zero network, one-way),
`verify-final` (zero network, sockets forbidden; replays every committed run, re-hashes raw evidence and reproduces
the ledger, sealed store, manifests, membership, reports and network accounting; may run repeatedly).

## 15. Hard stops

`PLAN_FREEZE_INVALID`, `STATE_DRIFT`, `SOURCE_CONTRACT_DRIFT`, `EXECUTION_TERMS_SOURCE_UNAVAILABLE`,
`PROVENANCE_CEILING_UNREACHABLE`, `QUAL_PROVENANCE_LIMIT_EXCEEDED_UNAVOIDABLE`, `MEMBERSHIP_REPRODUCTION_FAILED`,
`DEPENDENCY_EXPANSION_REQUIRED`, `WORKFLOW_EXPANSION_REQUIRED`, `SCOPE_EXPANSION_REQUIRED`,
`AUTHORITY_EXPANSION_REQUIRED`, `ACCRUAL_BUDGET_EXHAUSTED`, `CODE_DRIFT_AFTER_PROSPECTIVE_ACCRUAL`. After prospective
accrual begins, any code change that could affect evidence, classification or sealing is
`STOP CODE_DRIFT_AFTER_PROSPECTIVE_ACCRUAL` (plan code digests are bound at `prepare`); return to Side14.

## 16. Successor

After merge: `prepare` on the merged code; no `accrue` before `2026-10-15T00:00:00Z`; then manual bounded `accrue`
runs; on a hard stop return to Side14; after a final membership seal return to Side14 for the minimal evidence/status
closure before S10-QUAL-REAL-01. This WP authorizes no successor: not REAL-01, WP170, Gate C, paper or live.
