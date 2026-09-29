# S10-QUAL-DATA-01 Status

- WP: `S10-QUAL-DATA-01` — Weather Qualification Data Readiness
- Base: `77738717fee422fe83d8bb2b7765c36dfbe6b283` (execution base equals the drafting-time main SHA)
- Predecessor: PR #201 / `S10-NDFD-GRIB-01`, head `cd70800d40f60f4ec20f5b17e107cc56643562a2`,
  MERGED at the base SHA (`isDraft=false`)
- Historical Alpha predecessor: PR #200 / `S10-ALPHA-REAL-01` (RESEARCH_SUPPORTIVE Alpha seed)
- Package class: `WEATHER_QUALIFICATION_DATA_READINESS`; size L
- Governance: RUNTIME, risk 3, capital at risk USD 0; no draftability certificate required
- Exact changed-file scope: 20; dependencies/workflows/qualification contracts unchanged
- Branch: `codex/s10-qual-data-01-weather-readiness`
- Readiness: `IMPLEMENTATION_READY` (governance track RUNTIME, minimum RUNTIME, 20 files,
  34 evidence items, 34 normative rules)
- Authorization: Karl's receipt of the exact package, including the bounded public read-only
  network work (no second go); merge separately gated
- Evidence mode: `PRIVATE_REPO_MANUAL_VERIFIED`
- PR: see GitHub PR metadata and PR body (created Ready for Review, never Draft).
- Current live PR head: see GitHub PR metadata and PR body. This status fragment is stable and
  non-self-referential; it does not encode dynamic PR metadata or the SHA of the commit
  containing itself.
- Merge authorized: NO

Current S10-QUAL-DATA-01 state: QUAL_DATA_READY

## Change

- Offline modules (zero network): `src/data_layer/analytical_research/pendulumflow_v3.py`
  (PendulumFlow v3 manifest/range/coverage/footer/row normalization),
  `src/data_layer/analytical_research/nws_ndfd_history.py` (NDFD PoP12 structural guard,
  deterministic multi-message slicing, header pre-parse, four clocks, station binding, lazy
  exact-version ecCodes decode) and
  `src/data_layer/analytical_research/qualification_data_readiness.py` (checkpoints, rule cohorts,
  labels, evidence selection, execution facts, provenance shards, counts, B0 state, bundle).
- Foreground operator and only network owner: `tools/qualification/run_s10_qual_data_01.py`
  (`prepare`, `probe-sources`, `run-readiness`, `verify-final`).
- Contract `docs/qualification_weather_data_readiness_contract.md`; focused tests for the three
  modules and the operator; contract-doc test; the PR #201 compatibility test now also exercises the
  production adapter under the unchanged strict ndfd-grib jobs.

## Frozen Semantics

- Target dates 2026-08-18..2026-09-26 (40); checkpoint A `MARKET_OBSERVABLE_PLUS_60M_V1`;
  checkpoint B `TARGET_CLIMATE_DAY_START_V1`; market-history lookback 24 h; NDFD lookback 48 h.
- PendulumFlow v3 is `THIRD_PARTY_NATIVE_FRAME_ARCHIVE` / `EXTERNAL_THIRD_PARTY_PIT_RECONSTRUCTION`,
  never canonical PIT; B0 compatibility is
  `EXTERNAL_ONLY_REQUIRES_SEPARATE_COMPATIBILITY_DECISION` unless canonical PIT is independently bound.
- Implementation-time source discovery (before freezing parsers): about 22 anonymous public GETs to
  the allowlisted hosts (two PendulumFlow documentation pages, three manifests, the v3 listing and
  audit pages, Parquet tail/footer/product ranges for 2026-08-19 and 2026-08-20 hours, one Gamma
  market, one NDFD S3 listing, one NWS station). Observed: daily-rain markets for target date D are
  created about 11:09Z on D itself, so checkpoint B (local-standard midnight of D) precedes market
  creation and is expected to yield no eligible rows; v3 resolution for a sample market arrived
  within one minute of the Gamma `closedTime`.

## Real Run

Environment: isolated Docker `python:3.12` (CPython 3.12.14) with the unchanged merged base pins plus
`eccodes==2.48.0` / `eccodeslib==2.48.0.26` (binary wheels; `pip check` clean; ecCodes selfcheck OK). No
repository dependency change.

- Terminal: QUAL_DATA_READY (reason `EVIDENCE_COMPLETE_ROWS_PRESENT`)
- Bundle id: weatherqualbundle:sha256:0d37fcab27fb1e4bf128b60dd491a8c9af08d33b7220d38f521bcd2f33c446a6
- Logical dataset id: weatherqualdataset:sha256:e1863b72800eeecda0f0509f661c50972a00fea915889167488e0088dbda2ab7
- Plan hash: `fbd30b1e3006e111306ad476f5f529b2645dfcfe0dc71068768bf670d70bcf67` (repo code identity = commit `127d66c`)
- B0 contract compatibility: EXTERNAL_ONLY_REQUIRES_SEPARATE_COMPATIBILITY_DECISION
- verify-final: VERIFIED (zero network; 1457 retained artifacts re-hashed; deterministic replay produced
  the byte-identical bundle; 24 ready manifests re-validated)
- Alpha registry: genuine PR #200 registry found under one git worktree root, verified (15 rows, head
  `alpharegistryentry:sha256:4b9a20f7...`, RESEARCH_SUPPORTIVE), copied and re-verified; AF1 receipt
  `af1gate:sha256:281c5e05...` FINALIZED AF1_PASS, ten dimensions PASS.
- Markets: 585 discovered / 119 included / 466 excluded (450 `RULE_SEMANTICS_UNSUPPORTED`,
  15 `TARGET_DATE_OUTSIDE_CORPUS`, 1 `GAMMA_UNAVAILABLE`).
- Checkpoint A (`MARKET_OBSERVABLE_PLUS_60M_V1`) usable rows: 104 over 7 independent target dates
  (2026-08-19, -20, -21, -23, -24, -25, -26); 15 rows of 2026-08-22 excluded
  `MARKET_HISTORY_COVERAGE_INADMISSIBLE`.
- Checkpoint B (`TARGET_CLIMATE_DAY_START_V1`) usable rows: 0 (119 `CHECKPOINT_B_MARKET_NOT_OPEN_60M`:
  markets are created about 11:09Z on the target date, after its local-standard midnight).
- All 104 rows: one rule cohort (`FIRST_PUBLISHED_FINAL`), best_bid_ask coverage FULL; last_trade_price
  observed in the searched hours for 7 rows (97 `NOT_OBSERVED_IN_SEARCHED_HOURS`).
- PendulumFlow hours touched: 117; best_bid_ask coverage over classified hours FULL 92, PARTIAL 16,
  SINGLE-BY-DESIGN 5, SINGLE-BY-DEFECT 2. Discovery-hour failures: 2026-09-09/12 and 2026-09-24/11
  (truncated manifest bodies, see D009). 905 non-target `market_resolved` rows with a 32-byte
  `winning_asset_id` that does not decode canonically were skipped fail-closed; no target market lost its
  label (0 `LABEL_V3_RESOLUTION_MISSING`).
- NDFD vintages selected: 7 (one YDUZ98_KWBN object per row date, public 11:48-11:53Z, before every
  checkpoint); 15 NWS stations.
- Execution facts (per included market): FEES 35 HISTORICALLY_EVIDENCED / 84 CURRENT_ONLY;
  RESOLUTION_RULES 119 CURRENT_ONLY; TICK_SIZE_MIN_ORDER 119 CURRENT_ONLY.

### Network accounting

- Pre-run non-authoritative implementation diagnostics (before the governed operator existed; not
  bound into the bundle and not evidence that any probe/run passed): 24 direct anonymous GETs to the
  allowlisted hosts totalling exactly 4,842,329 response bytes, plus 2 documentation page fetches
  (PendulumFlow `formats/v3`, `audit/v3`) whose byte counts are unavailable.
- Governed operator traffic (only `tools/qualification/run_s10_qual_data_01.py`):
  - failed first probe (commit 2e6b196): 4 attempts / 526,439 bytes, preserved under
    `local_data/s10_qual_data_01/diagnostic-probe-attempt-01/`;
  - fresh probe (commit b9cb207): 14 attempts / 5,330,969 bytes, PROBE_PASS (plan superseded);
  - first run-readiness (commit b9cb207) stopped without any terminal on an unhandled Gamma connection
    reset (`http.client.RemoteDisconnected`); preserved under
    `local_data/s10_qual_data_01/diagnostic-run-attempt-01-transport-interrupted/`;
  - after the same-scope transport fix (commit 127d66c) the plan was re-prepared, the probe re-run
    (15 attempts / 5,330,969 bytes, PROBE_PASS) and run-01 resumed from the 327 hash-verified artifacts
    of the interrupted attempt (failed entries dropped so they received the single retry);
  - run-01 cumulative ledger (including the interrupted attempt and its one unrecorded crashing Gamma
    attempt): 1,472 transport attempts, 483,015,050 bytes, 11 immediate retries, max single response
    11,342,214 bytes; by host: archive.pendulumflow.com 857 / 462,852,459, gamma-api.polymarket.com
    582 / 2,161,628 (canonical JSON bytes), noaa-ndfd-pds 18 / 17,968,809, api.weather.gov 15 / 32,154.
  - Budgets never exhausted.

### Findings for Side14 (recorded, not tuned; run-01 is final)

- Rule-parser coverage defect: all 450 `RULE_SEMANTICS_UNSUPPORTED` markets carry wording of the two
  frozen policies the parser did not match: 420 `LAST_BEFORE_1400_ET` ("as published by 2:00 PM ET on the
  day following ... the last version published before that time governs"), 30 `LATEST_BEFORE_2359_ET`
  ("the most recent CLI report ... the last version published before 11:59 PM ET ... governs"). Correcting
  the parser changes the frozen code digests and would require new network acquisition for those markets,
  i.e. a second corpus run, which this WP does not authorize. The READY result therefore understates the
  available corpus (S10-QUAL-DATA-01-D008).
- Transport: two manifest responses were truncated HTTP 200 bodies accepted without a Content-Length
  check (S10-QUAL-DATA-01-D009).

## Boundaries

- QualificationCandidate created: NO
- Qualification gate run: NO
- WP170/WP172/WP173: NOT STARTED
- Credentials/private APIs/Hermes/scheduler/strategy/paper/execution: 0
- Gate C: NOT AUTHORIZED; live: DISABLED; capital at risk: USD 0; orders: 0
- Merge authorized: NO
