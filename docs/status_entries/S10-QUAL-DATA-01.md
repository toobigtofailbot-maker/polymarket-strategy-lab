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

Current S10-QUAL-DATA-01 state: QUAL_DATA_INSUFFICIENT

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

## Real Run (authoritative: replacement run-01)

Environment: isolated Docker `python:3.12` (CPython 3.12.14) with the unchanged merged base pins plus
`eccodes==2.48.0` / `eccodeslib==2.48.0.26` (binary wheels; `pip check` clean; ecCodes selfcheck OK). No
repository dependency change. Code identity: commit `a456d2e` (Side14 same-WP correction of D008, D009 and
the checkpoint-B diagnostic). Clean workspace; no manual seeding; the operator reported `resumed: false`
truthfully (the run was not interrupted).

- Terminal: QUAL_DATA_INSUFFICIENT (reason `FROZEN_BUDGET_EXHAUSTED`: the frozen 2 GiB response-byte budget
  was reached; the pre-request check stopped the next request before exceeding it)
- Bundle id: weatherqualbundle:sha256:ceca0252b4d41cf9b49591bb3a65ed9e0b79d9321b269ecbab86f5a90ea085e1
- Logical dataset id: weatherqualdataset:sha256:9058a05354390ca7e61bcb47871f93b925e99571f7cc48f40b057eb0e8454413
- Plan hash: `b51630a7e7e6a29cb1aa8bbdc109cf8d31140821f1880cf5dfe052e8c5ba8202`
- B0 contract compatibility: EXTERNAL_ONLY_REQUIRES_SEPARATE_COMPATIBILITY_DECISION
- verify-final: VERIFIED (zero network; 3600 retained artifacts re-hashed; deterministic replay, including
  the exhaustion point, produced the byte-identical bundle; 111 ready manifests re-validated)
- Alpha registry / AF1: genuine PR #200 registry verified, copied and re-verified (15 rows, head
  `alpharegistryentry:sha256:4b9a20f7...`, RESEARCH_SUPPORTIVE); AF1 receipt `af1gate:sha256:281c5e05...`
  FINALIZED AF1_PASS, ten dimensions PASS.
- Probe: PROBE_PASS (14 attempts / 5,330,969 bytes).
- Markets: 600 discovered / 325 included / 275 excluded (225 `BUDGET_EXHAUSTED_BEFORE_EVALUATION`,
  35 `LABEL_V3_RESOLUTION_MISSING`, 15 `TARGET_DATE_OUTSIDE_CORPUS`); 0 `RULE_SEMANTICS_UNSUPPORTED`.
- Rule policies over the 585 Gamma rule texts: FIRST_PUBLISHED_FINAL 120 (115 included / 5 excluded label
  missing), LAST_BEFORE_1400_ET 435 (195 included / 225 budget-exhausted / 15 label missing),
  LATEST_BEFORE_2359_ET 30 (15 included / 15 label missing).
- Evidence-complete rows: 212 (`market_history_rows_available`), over 12 independent target dates
  (2026-08-19, -20, -21, -23, -24, -25, -26, -28, -29, 2026-09-03, -04, -05).
  - Checkpoint A (`MARKET_OBSERVABLE_PLUS_60M_V1`): 160 rows / 11 dates; exclusions 105
    `MARKET_HISTORY_NOT_OBSERVED_IN_LOOKBACK`, 60 `MARKET_HISTORY_COVERAGE_INADMISSIBLE`.
  - Checkpoint B (`TARGET_CLIMATE_DAY_START_V1`): 52 rows / 4 dates; exclusions 115
    `CHECKPOINT_B_MARKET_NOT_OPEN_60M`, 96 `MARKET_HISTORY_COVERAGE_INADMISSIBLE`, 62
    `MARKET_HISTORY_NOT_OBSERVED_IN_LOOKBACK` (each with its actual closed reason).
  - Rows by policy: FIRST_PUBLISHED_FINAL 100 (A), LAST_BEFORE_1400_ET 82 (45 A / 37 B),
    LATEST_BEFORE_2359_ET 30 (15 A / 15 B).
- PendulumFlow hours touched: 370; best_bid_ask coverage over classified hours FULL 182, PARTIAL 69,
  SINGLE-BY-DESIGN 5, SINGLE-BY-DEFECT 2. Discovery-hour failures: none (the two hours truncated in the
  superseded run, 2026-09-09/12 and 2026-09-24/11, were recovered). 889 non-target `market_resolved` rows
  with a non-canonical 32-byte `winning_asset_id` were skipped fail-closed.
- NDFD vintages selected: 26 (every one public before its checkpoint); 15 NWS stations.
- Execution facts (per included market): FEES 77 HISTORICALLY_EVIDENCED / 248 CURRENT_ONLY;
  RESOLUTION_RULES 325 CURRENT_ONLY; TICK_SIZE_MIN_ORDER 325 CURRENT_ONLY.

### Network accounting

- Pre-run non-authoritative implementation diagnostics (before the governed operator existed; not bound into
  any bundle): 24 direct anonymous GETs totalling exactly 4,842,329 response bytes, plus 2 documentation
  page fetches (PendulumFlow `formats/v3`, `audit/v3`) whose byte counts are unavailable.
- Governed operator traffic (only `tools/qualification/run_s10_qual_data_01.py`):
  - replacement run-01 (authoritative): 4,031 transport attempts, 2,147,013,454 bytes, 228 immediate retries
    (the archive returned 428 HTTP 503 responses), max single response 11,342,214 bytes; by host:
    archive.pendulumflow.com 3,237 / 1,774,287,236; noaa-ndfd-pds 194 / 370,472,141;
    gamma-api.polymarket.com 585 / 2,221,923 (canonical JSON bytes, D007); api.weather.gov 15 / 32,154;
    budget: `BYTE_BUDGET_EXHAUSTED`.
  - replacement probe: 14 attempts / 5,330,969 bytes.
  - historical (superseded / diagnostic, not authoritative for the bundle): failed probe 4 / 526,439;
    superseded probes 14 / 5,330,969 and 15 / 5,330,969; superseded defective run cumulative
    1,472 / 483,015,050 (including its interrupted first attempt).

### Superseded defective run (retained historical evidence)

`local_data/s10_qual_data_01/SUPERSEDED_DEFECTIVE_RUN_D008_D009/` (plan `fbd30b1e...`, code `127d66c`):
QUAL_DATA_READY, bundle `weatherqualbundle:sha256:0d37fcab27fb1e4bf128b60dd491a8c9af08d33b7220d38f521bcd2f33c446a6`, logical dataset `weatherqualdataset:sha256:e1863b72800eeecda0f0509f661c50972a00fea915889167488e0088dbda2ab7`; 585 discovered / 119 included /
466 excluded (450 `RULE_SEMANTICS_UNSUPPORTED` from D008); 104 checkpoint-A rows over 7 dates; checkpoint B
0 rows (all labelled `CHECKPOINT_B_MARKET_NOT_OPEN_60M`); 2 truncated manifests (D009). Superseded by Side14
because D008 and D009 were implementation defects against already-frozen semantics; never relabelled.

### Findings for Side14 (recorded, not tuned)

- The frozen plan cannot finish within the frozen 2 GiB budget once all frozen-policy markets are admitted:
  checkpoint-B history scans and the archive's HTTP 503 throttling (428 responses, 228 retries) consumed the
  budget, leaving 225 LAST_BEFORE_1400_ET markets unevaluated (S10-QUAL-DATA-01-D012).
- Latent operator defect (S10-QUAL-DATA-01-D011): an hour whose targeted best_bid_ask chunk or footer read
  failed is still counted as scanned. Checked against the sealed bundle: 0 of 212 rows have such an hour
  between their selected event and checkpoint (the only failed read inside any row span is a
  `market_resolved` product), so no row is affected; the defect is recorded, not fixed on this run.

## Boundaries

- QualificationCandidate created: NO
- Qualification gate run: NO
- WP170/WP172/WP173: NOT STARTED
- Credentials/private APIs/Hermes/scheduler/strategy/paper/execution: 0
- Gate C: NOT AUTHORIZED; live: DISABLED; capital at risk: USD 0; orders: 0
- Merge authorized: NO
