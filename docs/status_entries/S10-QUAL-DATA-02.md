# S10-QUAL-DATA-02 Status

- WP: `S10-QUAL-DATA-02` — Weather Qualification Corpus Completion
- Base: `6f67bac990d8ab338f1b87140ae077e9df4172dd` (execution base equals the drafting-time main SHA)
- Predecessor: PR #202 / `S10-QUAL-DATA-01`, head `33c031f41626550294eb6667620b4ce75589d719`, MERGED at the base
  SHA (`isDraft=false`)
- Package class: `WEATHER_QUALIFICATION_CORPUS_COMPLETION`; size L
- Governance: RUNTIME, risk 3, capital at risk USD 0; no draftability certificate required
- Exact changed-file scope: 15; dependencies/workflows/qualification contracts unchanged
- Branch: `codex/s10-qual-data-02-weather-corpus-completion`
- Readiness: `IMPLEMENTATION_READY` (governance track RUNTIME, minimum RUNTIME, 15 files, 35 evidence items,
  29 normative rules)
- Authorization: Karl's authorization of the exact package, including the bounded public read-only network
  work (no second go); merge separately gated
- Evidence mode: `PRIVATE_REPO_MANUAL_VERIFIED`
- PR: see GitHub PR metadata and PR body (created Ready for Review, never Draft).
- Current live PR head: see GitHub PR metadata and PR body. This status fragment is stable and
  non-self-referential; it does not encode dynamic PR metadata or the SHA of the commit containing itself.
- Merge authorized: NO

Current S10-QUAL-DATA-02 state: QUAL_DATA_READY

## Seed (PR #202 run-01)

- Predecessor-code verification (R004), before any analytical-core edit: the S10-QUAL-DATA-01 `verify-final` was
  replayed with the exact predecessor code `33c031f41626550294eb6667620b4ce75589d719` (clean checkout at that head,
  Docker `python:3.12` + `eccodes==2.48.0`) over a read-only mount of `local_data/s10_qual_data_01/run-01/`, with its
  single write intercepted: VERIFIED, zero network, 3600 artifacts re-hashed, 111 ready manifests, bundle
  `weatherqualbundle:sha256:ceca0252b4d41cf9b49591bb3a65ed9e0b79d9321b269ecbab86f5a90ea085e1`, dataset
  `weatherqualdataset:sha256:9058a05354390ca7e61bcb47871f93b925e99571f7cc48f40b057eb0e8454413`; the would-be
  VERIFY_FINAL.json was byte-identical to the stored one (SHA-256 `adc6c299a8eef82ddcc94214a493b3fc66aac2d3e3e5013a187725dda5a76f0f`). DATA-01 evidence was not mutated.
- PR #202 seed verified: YES (one valid copy under the git worktree roots; plan code digests equal the predecessor
  blobs; terminal QUAL_DATA_INSUFFICIENT / FROZEN_BUDGET_EXHAUSTED; exact bundle/dataset ids; VERIFY_FINAL VERIFIED).
- Seed artifact count: 3600 admitted (2,106,893,539 bytes); failed seed entries admitted: 0 (203 HTTP_503
  predecessor entries not admitted and fetched fresh). Seed index SHA-256
  `0a899579ed31f784b18b78990c167f77f5f20e7d5f092e3e90533189cbd4f6ac`.
- Seed reused by the run: 3060 artifacts / 1,728,309,493 bytes (never counted against the caps).
- Failed seed entries admitted: 0

## Real Run (run-01, single completion run)

Environment: Docker `python:3.12` (CPython 3.12.14, Linux) with the unchanged base pins plus `eccodes==2.48.0` /
`eccodeslib==2.48.0.26`; `prepare` on the Windows host (zero network). Plan hash
`3eca002419d0f9ac532e11d9b998c831bcced2c2302798b235e2c8794a9c62d8`; code identity commit `0b308c4`; clean workspace;
`resumed: false`.

- Probe: PROBE_PASS (2 attempts / 15,690 bytes: seed cache hit with zero attempts; live 2026-08-19/12 manifest
  byte-identical to its seed; typed D011 failure `MANIFEST:HTTP_503` -> LABEL_V3_SOURCE_READ_FAILED; live Gamma
  identity equal to the seeded document, rule FIRST_PUBLISHED_FINAL; production NDFD decode PASS).
- Terminal: QUAL_DATA_READY (reason `EVIDENCE_COMPLETE_ROWS_PRESENT`)
- Terminal reason: EVIDENCE_COMPLETE_ROWS_PRESENT
- Bundle id: weatherqualbundle:sha256:a5911ab05cc8c650377447aa46f65f3b2002fc458e3c51a64f8705b1adcc69ae
- Logical dataset id: weatherqualdataset:sha256:a3e98a35ea052e1dfeb5225239a74beaee47d04111ebb34e6d27717490d9ac39
- B0 contract compatibility: EXTERNAL_ONLY_REQUIRES_SEPARATE_COMPATIBILITY_DECISION
- Verify-final: VERIFIED (zero network, Docker --network none; 6970 indexed artifacts and 3600 seed artifacts re-hashed; deterministic replay reproduced the byte-identical bundle, provenance manifests, counts/exclusions, seed usage and network accounting; 114 ready manifests re-validated; failed seed entries admitted 0)
- Markets: 600 discovered / 570 included / 30 excluded (15 `TARGET_DATE_OUTSIDE_CORPUS`, 15
  `LABEL_V3_SOURCE_READ_FAILED`); 0 `BUDGET_EXHAUSTED_BEFORE_EVALUATION`, 0 `LABEL_V3_RESOLUTION_MISSING`,
  0 `RULE_SEMANTICS_UNSUPPORTED`. Included policies: LAST_BEFORE_1400_ET 420, FIRST_PUBLISHED_FINAL 120,
  LATEST_BEFORE_2359_ET 30.
- Evidence-complete rows: 783 over 32 independent target dates.
  - Checkpoint A (`MARKET_OBSERVABLE_PLUS_60M_V1`): 465 rows / 31 dates; exclusions 105
    `MARKET_HISTORY_COVERAGE_INADMISSIBLE`.
  - Checkpoint B (`TARGET_CLIMATE_DAY_START_V1`): 318 rows / 22 dates; exclusions 135
    `CHECKPOINT_B_MARKET_NOT_OPEN_60M`, 110 `MARKET_HISTORY_COVERAGE_INADMISSIBLE`, 7 `MARKET_HISTORY_SOURCE_INVALID`.
  - Rows by policy: LAST_BEFORE_1400_ET 633 (330 A / 303 B), FIRST_PUBLISHED_FINAL 105 (A), LATEST_BEFORE_2359_ET 45
    (30 A / 15 B).
  - last_trade_price: 70 OBSERVED, 713 NOT_OBSERVED_IN_SEARCHED_HOURS, 0 search-incomplete.
- Source-invalid market-history rows: 7 (5 on 2026-08-31, 2 on 2026-09-02).
- LABEL_V3_SOURCE_READ_FAILED: 15 (all 2026-08-29 markets; required label-window hour 2026-08-31/09).
- LABEL_V3_RESOLUTION_MISSING: 0 (the 35 S10-QUAL-DATA-01 cases were 503 read failures; all re-read successfully).
- Failed read counts by source family: best_bid_ask 3 (market_history), market_resolved 1 (labels),
  last_trade_price 0, tick_size_change 0, new_market 0 (discovery); every failure at stage MANIFEST with closed code
  `V3_MANIFEST_INVALID`. The four hours (2026-08-31/07, /08, /09 and 2026-09-02/03) serve manifests whose product byte
  ranges fail validation (`V3_BYTE_RANGE_INVALID`) — a persistent archive source defect, byte-identical to the
  predecessor's retrieval (seeded) — not throttling.
- PendulumFlow hours touched: 392; best_bid_ask coverage FULL 299, PARTIAL 82, SINGLE-BY-DESIGN 5, SINGLE-BY-DEFECT 2.
  Discovery-hour failures: none. NDFD vintages selected: 117; 15 NWS stations; 114 ready manifests.
- Execution facts (per included market): FEES 226 HISTORICALLY_EVIDENCED / 344 CURRENT_ONLY; RESOLUTION_RULES 570
  CURRENT_ONLY; TICK_SIZE_MIN_ORDER 570 CURRENT_ONLY (no tick_size_change read failed).
- Comparison with S10-QUAL-DATA-01 (whole corpus re-derived, not inherited): 197 of its 212 (market, checkpoint)
  rows recur (row ids differ: the LTP failure record is a new field and provenance manifests are re-derived); its
  15 2026-08-29 rows are now `LABEL_V3_SOURCE_READ_FAILED` (DATA-01 read the failed hour as empty and labelled from
  the other window hour).

### Network accounting

- New network attempts: 3,919 (probe 2 + run 3,917); new network bytes: 2,572,004,490 (probe 15,690 + run
  2,571,988,800); caps 12,288 / 6,442,450,944; budget exhausted: NO.
- Run by host: archive.pendulumflow.com 3,912 / 2,559,541,589; noaa-ndfd-pds 5 / 12,447,211; gamma-api 0; api.weather.gov
  0 (all 585 Gamma documents and 15 stations served from the seed). Statuses: 200 x163, 206 x3,748, transport error x6;
  7 immediate transport retries; HTTP 429/503: 0 (throttle retries 0, backoff 0 s); max single response 2,586,708 bytes.
- Total evidence bytes including seed: 4,300,207,206 retained (1,728,309,493 seed-reused + 2,571,897,713 new).

### Findings for Side14 (recorded, not tuned)

- S10-QUAL-DATA-02-D005: the D011 label rule is applied conservatively — any failed required `market_resolved` hour
  excludes the market even when another window hour holds an agreeing resolution (15 markets, 2026-08-29).
- S10-QUAL-DATA-02-D006: four archive hours carry manifests with invalid product byte ranges (persistent source defect).

## Change

- Completion operator and only network owner: `tools/qualification/run_s10_qual_data_02.py` (`prepare`,
  `probe-sources`, `run-completion`, `verify-final`). It imports the S10-QUAL-DATA-01 operator and offline
  modules unchanged and subclasses the store (seed cache, 429/503 backoff), hour access (typed read state and a
  1 GiB in-memory range bound) and pipeline (D011 rules).
- Core: `src/data_layer/analytical_research/qualification_data_readiness.py` gains only the additive
  market-exclusion code `LABEL_V3_SOURCE_READ_FAILED`.
- Contract `docs/qualification_weather_corpus_completion_contract.md`; focused operator tests; the additive
  vocabulary test; contract-doc test; project-status and repo-truth tests.

## Boundaries

- QualificationCandidate created: NO
- Qualification gate run: NO
- WP170/WP172/WP173: NOT STARTED
- Credentials/private APIs/Hermes/scheduler/strategy/paper/execution: 0
- Gate C: NOT AUTHORIZED; live: DISABLED; capital at risk: USD 0; orders: 0
- Merge authorized: NO
