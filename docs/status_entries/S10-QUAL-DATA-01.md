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

Current S10-QUAL-DATA-01 state: PHASE_A_IMPLEMENTED_REAL_RUN_PENDING

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

- Phase A candidate validated locally; the single real run (`prepare`, `probe-sources`,
  `run-readiness`, `verify-final`) follows under Python 3.12 with the merged optional `ndfd-grib`
  extra in an isolated environment. Actual terminal, counts, ids and network totals are recorded
  here only after the run.

## Boundaries

- QualificationCandidate created: NO
- Qualification gate run: NO
- WP170/WP172/WP173: NOT STARTED
- Credentials/private APIs/Hermes/scheduler/strategy/paper/execution: 0
- Gate C: NOT AUTHORIZED; live: DISABLED; capital at risk: USD 0; orders: 0
- Merge authorized: NO
