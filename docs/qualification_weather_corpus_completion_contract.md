# Weather Qualification Corpus Completion Contract (S10-QUAL-DATA-02)

Package: `docs/wp_specs/S10-QUAL-DATA-02/` (governance track RUNTIME, risk 3, exact 15-path scope).
Predecessor: PR #202 / S10-QUAL-DATA-01, head `33c031f41626550294eb6667620b4ce75589d719`, merged at
`6f67bac990d8ab338f1b87140ae077e9df4172dd`. Frozen predecessor contract:
`docs/qualification_weather_data_readiness_contract.md` (unchanged by this WP).

## Purpose and posture

DATA FORMATION / CORPUS COMPLETION ONLY. S10-QUAL-DATA-01 ended `QUAL_DATA_INSUFFICIENT /
FROZEN_BUDGET_EXHAUSTED` (600 discovered / 325 included / 275 excluded markets; 212 rows over 12 dates;
225 `LAST_BEFORE_1400_ET` markets unevaluated). This WP completes that same frozen corpus in one bounded run.
It changes exactly four things: failed-read accounting (S10-QUAL-DATA-01-D011), throttle handling, seed reuse
and the bounded budget (S10-QUAL-DATA-01-D012). It does not change dates, checkpoints, windows, label window,
finality policies, source classes or the B0 rule, and performs no outcome-informed tuning.

- No QualificationCandidate is created and no qualification gate is run; WP170/WP172/WP173 stay not started.
- No predictive metric, sample-power threshold, Brier/log-loss, feature or model work.
- No dependency, lock or workflow change; no credential, private endpoint, Hermes/provider/model call,
  scheduler or background service.
- Gate C: NOT AUTHORIZED. Live: DISABLED. Capital at risk: USD 0. Orders: 0. Merge: NOT AUTHORIZED.

## Code surface

- `tools/qualification/run_s10_qual_data_02.py` is the only network owner. It imports the S10-QUAL-DATA-01
  operator and offline modules unchanged and subclasses its store, hour access and pipeline.
- `src/data_layer/analytical_research/qualification_data_readiness.py` gains exactly one additive
  market-exclusion code, `LABEL_V3_SOURCE_READ_FAILED`. No other core, gate, WP170, public-client or
  provenance file changes. `run_s10_qual_data_01.py`, `pendulumflow_v3.py` and `nws_ndfd_history.py` are
  byte-unchanged.
- Consequence: the S10-QUAL-DATA-01 plan binds the old `qualification_data_readiness.py` digest, so running
  the DATA-01 `verify-final` from this code reports `CODE_DRIFT`. The PR #202 evidence is therefore verified
  with the exact predecessor code `33c031f41626550294eb6667620b4ce75589d719` (see Seed).

## Seed (PR #202 run-01)

- Discovery: `local_data/s10_qual_data_01/run-01/` beneath `git worktree list --porcelain` roots only.
  Byte-identical valid copies agree; two valid stores that disagree stop `SEED_EVIDENCE_CONFLICT`; no valid
  store stops `SEED_EVIDENCE_MISSING` with no fallback fresh full run.
- Verification: the seed plan hash; the seed plan code digests equal the blobs of the four S10-QUAL-DATA-01
  code files at the exact predecessor head; state FINAL; terminal `QUAL_DATA_INSUFFICIENT`, reason
  `FROZEN_BUDGET_EXHAUSTED`; bundle `weatherqualbundle:sha256:ceca0252b4d41cf9b49591bb3a65ed9e0b79d9321b269ecbab86f5a90ea085e1`;
  dataset `weatherqualdataset:sha256:9058a05354390ca7e61bcb47871f93b925e99571f7cc48f40b057eb0e8454413`;
  RUN_REPORT and VERIFY_FINAL (`VERIFIED`, zero network) bound to both ids and the plan hash; every admitted
  raw artifact re-hashed; admitted count equals the predecessor's re-hashed count; the copied Alpha registry
  re-verified. Before any analytical-core edit the predecessor `verify-final` was also replayed with the
  exact predecessor code over a read-only mount of the seed (status fragment, R004).
- Admission: only successful, hash-valid raw artifacts and their truthful source metadata (`sha256`, `bytes`,
  `media_type`, `last_modified`, `status`) are admitted, copied into `seed_raw/` of the DATA-02 workspace.
  Failed predecessor entries are never admitted (failed entries admitted: 0); their keys are fetched fresh.
  Never seeded: rows, exclusions, bundle, ready manifests, scanned-hour decisions, label classifications or
  execution-evidence decisions. The whole corpus is re-derived.
- Identity: the seed path, user and host never enter any plan, report or bundle identity. The seed is a
  content-addressed cache: a seeded run and a fresh unseeded run over the same sources produce the
  byte-identical bundle.
- Accounting: seed artifacts and bytes are reported separately from new network attempts and bytes; seed hits
  consume no attempt and no byte of the DATA-02 caps.

## D011 failed-read rules

Read state is tracked per `(phase, event_family, hour)` for `best_bid_ask`, `last_trade_price`,
`tick_size_change` and `market_resolved`, with the failing stage (`MANIFEST`, `TAIL`, `FOOTER`, `PRODUCT`,
`CHUNK`, `DECODE`) and closed code. A failed read or decode is never an empty result.

- best_bid_ask: a failed required hour is not scanned. A pair whose walk-back reaches it before finding its
  event (failed hour between the selected event and the checkpoint, or no event with any failed lookback hour)
  is `MARKET_HISTORY_SOURCE_INVALID`, and its deeper walk-back stops.
- last_trade_price: a failed hour is not listed as searched; the row records
  `last_trade_price_failed_hours`, and when no trade is selectable its state is
  `NOT_OBSERVED_SEARCH_INCOMPLETE_SOURCE_READ_FAILED` (never "not observed").
- market_resolved: a failed required read after the allowed retries is `LABEL_V3_SOURCE_READ_FAILED`.
  `LABEL_V3_RESOLUTION_MISSING` is kept only after every relevant-window read succeeded with no qualifying
  resolution.
- tick_size_change: a failed hour stays explicit (`v3_tick_size_change_failed_hours`) and not successfully
  searched; `CURRENT_ONLY` remains only on independent current Gamma metadata.
- The bundle source facts report failed-read counts by phase/family, by family and by stage
  (`pendulumflow_failed_reads`).

## Retry and throttle policy

- HTTP 429/503: initial attempt plus at most 3 retries after the frozen delays 2 s, 8 s, 30 s. An integer
  `Retry-After` in [0, 60] gives `max(frozen delay, Retry-After)`; any other value uses the frozen delay. No
  jitter, randomness or adaptive retry. Gamma through the public client exposes no headers: frozen delays.
- Timeout, reset / `RemoteDisconnected`, range or body truncation and other retryable statuses (408, other
  5xx) keep S10-QUAL-DATA-01's at most one immediate retry.
- An exhausted retry is a closed source failure retained in the index, never source absence; it replays
  identically and is never re-attempted within the run.
- Tests inject a no-sleep seam.

## Network and caps

- Hosts: `archive.pendulumflow.com`, `noaa-ndfd-pds.s3.amazonaws.com`, `gamma-api.polymarket.com` (through
  the existing `PolymarketPublicClient.get_market` only) and `api.weather.gov`; https GET / HEAD / Range GET
  only; no redirect, auth header, arbitrary URL, write method or WebSocket.
- New-network caps (probe traffic counts, seed bytes do not): `MAX_NETWORK_ATTEMPTS=12_288`,
  `MAX_RESPONSE_BYTES=6_442_450_944`, `MAX_SINGLE_RESPONSE=268_435_456`, `MAX_DISTINCT_PENDULUM_HOURS=2_000`;
  S10-QUAL-DATA-01's 40 dates / 1024 candidates / 128 stations bounds are unchanged. Caps are never raised
  during the run; exhaustion is `QUAL_DATA_INSUFFICIENT / FROZEN_BUDGET_EXHAUSTED`.
- Memory: at most 1 GiB of PendulumFlow range bytes is held in memory; an evicted hour is re-read from the
  local content-addressed store, never from the network, and never changes the result.

## Frozen corpus semantics (unchanged)

Target dates 2026-08-18 through 2026-09-26 (40 dates); checkpoints `MARKET_OBSERVABLE_PLUS_60M_V1` and
`TARGET_CLIMATE_DAY_START_V1`; market-history lookback 24 hours; NDFD lookback 48 hours; ±30-minute label
window around the Gamma `closedTime`; whole-object historical NDFD PoP12; PendulumFlow v3 is
`THIRD_PARTY_NATIVE_FRAME_ARCHIVE` / `EXTERNAL_THIRD_PARTY_PIT_RECONSTRUCTION`, never canonical PIT; B0 is
`EXTERNAL_ONLY_REQUIRES_SEPARATE_COMPATIBILITY_DECISION` unless genuine canonical PIT is independently bound;
finality policies exactly `FIRST_PUBLISHED_FINAL`, `LATEST_BEFORE_2359_ET`, `LAST_BEFORE_1400_ET`. The
bundle keeps the S10-QUAL-DATA-01 schema (dataset `wp_id` S10-QUAL-DATA-01); `source_facts.completion`
records S10-QUAL-DATA-02 and the predecessor ids.

## Commands and workspace

Workspace `local_data/s10_qual_data_02/run-01/` (ignored); DATA-01 evidence is never mutated.

- `prepare` — zero network: repo/predecessor gate, seed discovery/verification/admission, `SEED_INDEX.json`,
  `SEED_REPORT.json`, frozen plan with code digests, budgets and retry policy; conflicting workspace refused.
- `probe-sources` — bounded: zero-network seed cache hit; one live unseeded fetch whose bytes must equal the
  seed; typed D011 failure on the real operator path; live Gamma identity equal to the seeded document;
  production NDFD decode. `PROBE_PASS` is required.
- `run-completion` — exactly one real run; seed as cache; missing evidence fetched; the D011 and retry rules
  above. A finalized workspace refuses another run.
- `verify-final` — zero network: re-hash every seed and new artifact, replay the derivation from retained
  artifacts only and reproduce bundle/dataset ids, manifests, ready manifests, counts and exclusions, seed
  usage and network accounting; zero failed seed entries; no look-ahead or authority laundering.

## Outcomes and successor

`QUAL_DATA_READY` returns to Side14; the next candidate is the smallest B0 provenance / qualification-contract
compatibility package, not implemented automatically. `QUAL_DATA_INSUFFICIENT` returns the actual evidence;
no automatic rerun, budget increase, date/window expansion or tuning. This WP authorizes no successor.
