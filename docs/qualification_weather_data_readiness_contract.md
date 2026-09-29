# Weather Qualification Data Readiness Contract (S10-QUAL-DATA-01)

Status: governed by `docs/wp_specs/S10-QUAL-DATA-01/` (RUNTIME, risk 3, exact 20-path scope).
Authority: DATA FORMATION / READINESS ONLY. No QualificationCandidate, no qualification-gate run,
no predictive metric, no sample-power threshold, no strategy, paper, execution or live authority.
Gate C: NOT AUTHORIZED. Live: DISABLED. Capital at risk: USD 0. Orders: 0.

## 1. Purpose

Form one bounded, auditable, content-addressed weather qualification-data readiness corpus for the
exact PR #200 NON_WALLET daily-rain Alpha lineage and seal it as a
`WeatherQualificationDataReadinessBundle` whose terminal is exactly `QUAL_DATA_READY` or
`QUAL_DATA_INSUFFICIENT`.

`QUAL_DATA_READY` means only: the frozen corpus run completed truthfully and produced at least one
evidence-complete weather + market-history + rule + outcome row at a predeclared checkpoint, with all
source authority, provenance, exclusions and missing execution facts exposed. It is NOT
SAMPLE_POWER_READINESS (owned by the existing qualification gate), does not mean a future gate will
pass, and does not mean a QualificationCandidate can be built without a separate compatibility
decision.

## 2. Frozen lineage

- Alpha candidate `alphacandidate:sha256:2d1523c8086acf536ad07512e1eaffed9cb9405b65e83c87b89b40ba77ee3add`
- Family `alphafamily:sha256:136000bd56f2fc27cf490cf675ddf2715b0acfc1ee934aa5cdf2579925c208d8`
- Episode `alphaepisode:sha256:2e4c0f484649930ba2677bc360070f0e9ba6ef0e09ecd23b383a32ff3b69000c`
  (`RESEARCH_SUPPORTIVE`)
- Dedicated registry head `alpharegistryentry:sha256:4b9a20f7f0e931dfea7cced80a64d7a4be7ccc58e265dbb9ebde15edb2d79847`
  (15 rows)
- AF1 receipt `af1gate:sha256:281c5e05f5e4f8e30687f232e0289b99b0719c87fab61c8b1d1d417dc0b5cbb2`

`prepare` discovers `local_data/s10_alpha_real_01/attempt-01/alpha_registry.sqlite3` only beneath
`git worktree list --porcelain` roots, verifies the exact semantic snapshot with the merged Alpha
registry API, copies one verified registry into the ignored run workspace and verifies the copy
again. Zero valid snapshots is `ALPHA_LINEAGE_EVIDENCE_MISSING`; two different valid snapshots is
`ALPHA_LINEAGE_CONFLICT`. The registry is never reconstructed from documented ids and the source
absolute path never enters identity, bundle output or PR evidence. The committed AF1 evidence must
validate as FINALIZED `AF1_PASS` with all ten dimensions PASS, else `AF1_EVIDENCE_DRIFT`.

## 3. Frozen corpus, checkpoints and windows

- Target dates: 2026-08-18 through 2026-09-26 inclusive (40 dates). No extension.
- Checkpoint A `MARKET_OBSERVABLE_PLUS_60M_V1`: the later of the v3 `new_market`
  `timestamp_received` and a trustworthy Gamma open time (canonical UTC within 24 hours of the v3
  receive time), plus 60 minutes.
- Checkpoint B `TARGET_CLIMATE_DAY_START_V1`: target-date midnight in the rule-bound station's local
  standard time (explicit standard UTC offset); eligible only if the market was observably open at
  least 60 minutes before it.
- Market-history lookback: exactly 24 hours. NDFD vintage lookback: public availability in
  `[checkpoint - 48 hours, checkpoint]`. No window is widened after seeing missingness.
- This WP chooses no final experiment checkpoint and computes no predictive metric.

## 4. Census, rules and labels

- Discovery: PendulumFlow v3 `new_market` rows in the frozen discovery hours (11:00 and 12:00 UTC
  on each target date), daily-rain family slugs `where-will-it-rain-on-<month>-<day>-<year>-<city>`.
  Witness copies are collapsed by market id (earliest receive). Every discovered candidate gets an
  INCLUDED or closed EXCLUDED disposition.
- Enrichment only through the existing verified `PolymarketPublicClient.get_market(integer_id)`;
  the Gamma condition id, slug and token/outcome pairs must equal the v3 identity, otherwise
  `GAMMA_V3_IDENTITY_MISMATCH`. The unverified keyset endpoint is never used.
- Rule binding: exact rule-text SHA-256, one explicit NWS station (ICAO `K...`), NWS Daily Climate
  Report (CLI) product, `0.01 inches or more`, trace does not qualify, NWS climate day midnight to
  midnight local standard time, and exactly one of `FIRST_PUBLISHED_FINAL`,
  `LATEST_BEFORE_2359_ET`, `LAST_BEFORE_1400_ET`. Any other or ambiguous policy is
  `RULE_SEMANTICS_UNSUPPORTED` and excluded. `rule_cohort_id` (`weatherrulecohort:sha256:`) commits
  the normalized semantics; station and date are per-market bindings.
- Labels: a final Gamma outcome and v3 `market_resolved` rows found in the hours intersecting
  Gamma `closedTime` +/- 30 minutes must agree on winning token and outcome; disagreement or
  absence excludes the sample. Label evidence is post-outcome evidence and never enters checkpoint
  feature evidence. A market resolved at or before its checkpoint is excluded.

## 5. PendulumFlow v3 (external, never canonical PIT)

- Provider `pendulumflow`, dataset `v3`, source class `THIRD_PARTY_NATIVE_FRAME_ARCHIVE`, B0 source
  authority `EXTERNAL_THIRD_PARTY_PIT_RECONSTRUCTION`. Never `SOURCE_KIND_CANONICAL_PIT`, never a
  DatasetSnapshotReference.
- Offline module `src/data_layer/analytical_research/pendulumflow_v3.py`: manifest schema/bounds,
  product byte ranges and row groups, product SHA-256, Parquet tail/footer bounds, targeted column
  chunks, event normalization, `timestamp_received` (capture availability, ordering basis) kept
  distinct from the venue `timestamp`; `sequence` and file order are never arrival order.
- Acquisition: manifest, then Parquet tail/footer, then only the row groups whose `market`
  statistics can hold a target and only the needed column chunks. No whole-hour download. Small
  products (`new_market`, `market_resolved`, `tick_size_change`) are fetched as complete product
  ranges and verified against the manifest SHA-256 (EXACT). Row-group chunks of `best_bid_ask` /
  `last_trade_price` and footers are bound to the declared product range but cannot be digest-verified
  in isolation (FAITHFUL).
- Coverage is product-specific and the most conservative of: the archive audit's named PARTIAL
  hours; audit-pending hours (never assumed complete); manifest witness accounting (>=2 contributing
  machines FULL; one contributor SINGLE-BY-DESIGN when only that machine was set up, else
  SINGLE-BY-DEFECT); a source-declared per-product class. FULL and SINGLE-BY-DESIGN are admissible;
  PARTIAL and SINGLE-BY-DEFECT are diagnostic only (`PARTIALLY_OBSERVED`, fidelity `PARTIAL`).
- Checkpoint market history: the latest `best_bid_ask` of the Yes token received in the 24-hour
  lookback; every hour from that event through the checkpoint must have been scanned and be
  admissible. The latest `last_trade_price` is recorded when observed in the searched hours. No
  future spread/staleness filter is applied (that belongs to S10-QUAL-REAL-01).

## 6. NDFD PoP12 (official)

- Source: NOAA NDFD `noaa-ndfd-pds` WMO objects `wmo/pop12/YYYY/MM/DD/YDUZ98_KWBN_*` (CONUS PoP12),
  source class `OFFICIAL_HISTORICAL_EXPORT`. PoP12 only; QPF is not required.
- Offline module `src/data_layer/analytical_research/nws_ndfd_history.py`. Before ecCodes sees
  any bytes: non-empty, `GRIB` magic, edition 2, section-0 total length equal to the exact slice,
  final `7777`. Multi-message objects are sliced deterministically within bounded WMO framing;
  ambiguous or truncated structure is a closed error. ecCodes is lazy-imported and must be the merged
  S10-NDFD-GRIB-01 version (`eccodes==2.48.0`; `eccodeslib==2.48.0.26` off Windows) under Python 3.12.
- Four clocks stay separate: WMO bulletin time, public availability (S3 `LastModified`, a
  conservative bound), GRIB reference time, forecast valid interval. Reference/valid time never
  substitutes availability. The vintage is the latest object public in the 48-hour window; every
  PoP12 period overlapping the target climate day is kept with its raw value; periods are never
  combined into a probability.
- Station binding: station id from the rule; `api.weather.gov/stations/{id}` supplies coordinate and
  time zone only (reference metadata, not predictive); the standard UTC offset is derived with the
  standard library and must be unambiguous; the grid point comes from ecCodes nearest-grid logic and
  must lie within 10 km.

## 7. Provenance and identity

- Reuses unchanged `ExternalDatasetDescriptor`, `RawEvidenceReference`, `PitTimestamps`,
  `ResearchProvenanceManifest` and the common DQ/replay vocabularies.
- At most three source-family shards per target date (PendulumFlow market history, NOAA NDFD
  weather, Gamma/NWS rule/label metadata), deterministically sub-sharded to <=256 items. Ready-subset
  manifests have `dq_flags == ("OK",)`, replay fidelity EXACT or FAITHFUL and an empty gap summary;
  degraded evidence goes to diagnostic manifests that never enter the ready subset. A row is sealed
  only if all three of its date's shards are ready.
- EXACT requires retained exact bytes of a complete object or a digest-verified range with a
  content-addressed `raw_snapshot_ref`; canonicalized Gamma responses and unverifiable ranges are
  FAITHFUL.
- `weatherqualdataset:sha256:<hex>` commits schema, lineage, corpus, checkpoints, source authority,
  row ids, ready/diagnostic manifest ids, external dataset ids, factual counts, execution-evidence
  summary, B0 state and no-authority flags. `weatherqualbundle:sha256:<hex>` additionally commits the
  rows, exclusions, execution facts, source facts and terminal. Neither contains absolute paths, host
  names, wall-clock execution time, transport latency or retry timing.

## 8. B0 authority boundary

`PIT_MARKET_PROBABILITY_V1` in the qualification contract is unchanged. The bundle reports
`market_history_rows_available` separately and `b0_contract_compatibility =
EXTERNAL_ONLY_REQUIRES_SEPARATE_COMPATIBILITY_DECISION` unless genuine canonical PIT evidence for the
same rows is independently bound; this WP has no route that can verify such a binding, so any claim
is rejected rather than trusted.

## 9. Execution-feasibility facts

Per included market, `FEES`, `RESOLUTION_RULES` and `TICK_SIZE_MIN_ORDER` carry exactly one of
`HISTORICALLY_EVIDENCED`, `CURRENT_ONLY`, `MISSING`, `SOURCE_DISAGREEMENT`. v3 `fee_rate_bps` and
`tick_size_change` observations are historical evidence; current Gamma fee, tick and minimum-order
metadata is current-only and never backdated; the rule text retrieved from Gamma after resolution is
current-only. No state is forced to AVAILABLE and the gate is not run.

## 10. Network, budgets and operator

The only network owner is `tools/qualification/run_s10_qual_data_01.py`: https GET/HEAD/Range only
to `archive.pendulumflow.com`, `noaa-ndfd-pds.s3.amazonaws.com`, `gamma-api.polymarket.com` (via the
existing public client) and `api.weather.gov`; no redirect, credential, arbitrary URL, loop or sleep.
Budgets: <=40 target dates, <=1024 candidates, <=128 stations, <=2000 PendulumFlow hours, <=8192
transport attempts including retries, <=2 GiB total bytes including retries, <=256 MiB per response,
at most one immediate retry for timeout/reset, HTTP 408/429 or 5xx. Budget exhaustion is a valid
`QUAL_DATA_INSUFFICIENT`, never permission to enlarge the budget.

Commands: `prepare` (zero network), `probe-sources` (bounded drift smoke through the production
adapters), `run-readiness` (ONE bounded run; resumable only from hash-verified artifacts after a
transport interruption; refuses a second run once final), `verify-final` (zero network: re-hash
every retained artifact and replay the deterministic derivation; the bundle must be byte-identical).
Artifacts live under ignored `local_data/s10_qual_data_01/run-01/`.

## 11. Successor boundary

This WP authorizes no successor. If `QUAL_DATA_INSUFFICIENT`, Side14 decides whether to close the
weather line or authorize a genuinely new evidence capability (no tuning). If `QUAL_DATA_READY` with
`CANONICAL_PIT_AVAILABLE`, Side14 may draft S10-QUAL-REAL-01. If `QUAL_DATA_READY` with
`EXTERNAL_ONLY_REQUIRES_SEPARATE_COMPATIBILITY_DECISION`, a separately gated minimal B0
provenance/qualification-contract compatibility decision comes first. WP170 stays eligible only after
a future valid QUAL_PASS; WP172, WP173, Gate C and live remain separately gated.
