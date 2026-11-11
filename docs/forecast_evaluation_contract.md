# Forecast evaluation contract (S10-R3-FORECAST-01)

Posture: RESEARCH_ONLY, `score_status` always `DIAGNOSTIC_ONLY`. No network, provider, LLM, Hermes, canonical store write, strategy, paper, order, live, credential or capital authority. Not a fair-value, qualification or WP170 run-evidence source.

## Call path

`tools/alpha/run_forecast_evaluation.py`

- `run --grounding-scratch ABS --cases ABS --scratch-dir ABS`
  1. Cold-verifies the caller's S10-R3-SRC-01 scratch with `tools.alpha.run_source_grounding.verify`. Anything other than `VERIFIED` stops with `GROUNDING_VERIFY_FAILED`.
  2. Freezes the inputs into the empty scratch directory, which must be outside the checkout: the SRC-01 tree goes to `inputs/grounding/`, the case bytes to `inputs/cases.json`, an optional WP170 registry to `inputs/wp170.sqlite3`, and the canonical frozen cases to `frozen_cases.json`.
  3. Re-verifies the frozen SRC-01 copy, then calls `forecast_evaluation.build_evaluation_core`.
  4. Writes `receipt.json` once, opened with `xb`.
- `verify --scratch-dir ABS` checks that the frozen cases equal `inputs/cases.json`, re-verifies the SRC-01 copy and recomputes the whole core from frozen bytes. It never writes. It reports failure codes only and never echoes input values.
- Exit codes: `0` means `RUN_COMPLETE` or `VERIFIED`. `1` means `STOPPED` (with a closed `reason_code`) or `TAMPER_DETECTED`. A socket guard fails the run if any socket is used (`NETWORK_ATTEMPT_BLOCKED`).

## Native bindings (read-only)

- **Grounding.** `grounding_receipt_id` must equal the verified SRC-01 receipt id, and `corpus_class` must equal the receipt's class. The native universe is rebuilt with `source_grounding.load_corpus` (which calls `alpha_discovery.build_alpha_universe_snapshot`) over the frozen PIT copy at the receipt `as_of`, and its snapshot id must match the receipt. A target binds only when all of the following hold:
  - its `market_id` is in that universe;
  - `question_sha256` equals SHA-256 of the native `question_text`;
  - the market is binary (exactly two distinct outcome labels) and `yes_label` is one of them;
  - the native category is non-crypto;
  - `rule_content_sha256` equals the SHA-256 of the SRC-01 `BOUND` rule bytes;
  - `decision_time` is at or after the grounding `as_of` and before the native resolution date.

  The event/leakage group is always the native `event_id`. A missing native category is refused (`CATEGORY_MISSING`). Each eligible row records its SRC-01 admitted source reference ids and `source_status` (`SRC01_ADMITTED_SOURCES` or `NO_ADMITTED_SOURCE`); history clocks are caller-asserted (`CALLER_ASSERTED_CLOCKS_NOT_SRC01_GROUNDED`, deferred D004).
- **WP170.** The `wp170` field takes one of two values:
  - `null` gives `DIAGNOSTIC_ONLY_EXPERIMENT_UNBOUND`.
  - `{registry_file, experiment_id}` is checked with `experiment_registry.load_and_verify_experiment_registry` (read-only). The `PreregisteredExperiment`, its `TemporalSplitManifest` and its `ResearchDatasetManifest` (with the embedded `ResearchSample` entries) must exist. Their dataset binding, feature, label, manifest and split identities must agree (`WP170_IDENTITY_MISMATCH` otherwise). Every split sample must be a manifest sample in exactly one role, purge or embargo set (`WP170_SPLIT_INVALID` otherwise). The block records `experiment_os.membership_hash(split, "OUT_OF_SAMPLE")`.

  These checks never create a preregistration or a `RunEvidenceReceipt`, and never append to a registry.

### Per-case WP170 membership (S10-R3-FORECAST-WP170-BIND-01, v2 receipts)

`wp170.membership` is `null` when unbound. Otherwise it binds each eligible target row to at most one embedded `ResearchSample`. The cohort is unchanged and outcomes are never read. Each case is checked in this order:

1. Exactly one sample with the same `market_id` and the same `decision_time`. If there is none, the case is `UNMAPPED` with `SAMPLE_NOT_FOUND` or `DECISION_TIME_MISMATCH`. If there are several, it is `AMBIGUOUS` with `MULTIPLE_SAMPLES_MATCH`.
2. Transitive PIT provenance. The sample must cite the target market's native PIT `metadata_record_version_id` from the verified grounding universe; otherwise the case is `UNMAPPED` with `SOURCE_PROVENANCE_UNPROVEN`. `ResearchSample` carries no rule hash. Rules are checked only through cited native rule record versions, so a cited version whose `rule_content_sha256` differs from the target's bound rule is `RULE_VERSION_CONFLICT`. Citing another grounded market is `CROSS_MARKET_SOURCE`.
3. Clocks. The case is refused as `FEATURE_AFTER_DECISION`, `FEATURE_BEFORE_SOURCE_OBSERVED` (feature availability before the PIT metadata observation), `TARGET_BEFORE_NATIVE_RESOLUTION` or `LABEL_AVAILABLE_AFTER_SCORING_CUTOFF`.
4. Split role. The role comes from the verified split's sample-id sets. A sample in no set is refused as `SAMPLE_OUTSIDE_SPLIT_WINDOW`; a purged or embargoed sample as `SAMPLE_PURGED` or `SAMPLE_EMBARGOED`.
5. Event/leakage grouping. One native event must map to one leakage group, and one leakage group to one event. If not, every involved case is refused as `EVENT_LEAKAGE_GROUP_CONFLICT`.

A case that does not bind is counted and never stops the run. A corrupt registry, split or grounding still stops the whole run. The block records:

- each entry's case id, market, status, reason, sample id and role;
- denominators: offered, not eligible, binding frame, mapped, unmapped, ambiguous, refused, counts by reason, mapped by role, and selected-and-mapped by role;
- the manifest, binding, feature-set, label and split assignment hashes;
- `experiment_os.membership_hash` for all three roles, and the mapped sample-id hash.

`wp170.status` becomes `WP170_REFERENCES_VERIFIED_READ_ONLY_MEMBERSHIP_MAPPED` only when at least one case maps; otherwise it stays `..._MEMBERSHIP_NOT_MAPPED`. The membership block is diagnostic only. It sets `oos_release: NOT_RELEASED`, `run_evidence_receipt: null`, `qualification_claim: false` and `labels_read_for_mapping: false`. Scores stay `DIAGNOSTIC_ONLY`.

## Case file `s10-r3-forecast01-cases-v1`

The input is strict JSON: duplicate keys and NaN/Infinity are rejected, the file must be at most 4 MiB, and secret-shaped values are refused. Keys must match exactly. Keys containing credential- or trade-shaped words (order, side, size, amount, signature, stake, bet, fill, position, plus the SRC-01 secret parts) are refused. `price` is allowed.

- `method`:
  - `prior_alpha`, `prior_beta`: canonical positive decimal strings; the default is `"1"` / `"1"`.
  - `min_training_n`, `wang_min_training_n`, `max_price_age_seconds`: ints; a bool is rejected.
  - `horizon_edges_days`: strictly increasing ints.
  - `price_edges`: strictly increasing canonical probabilities.
- `sampler`: `seed` and `sample_n`.
- `scoring_cutoff`: a UTC timestamp.
- `history[]` and `targets[]`: at most 2000 each. Duplicate `case_id` or `history_id` stops the run.
- Probabilities are strings matching `0|1|0.d{0,11}[1-9]`. Floats, bools, signs, exponents, trailing zeros, more than 12 decimal places, and values below 0 or above 1 are invalid.
- Caller-supplied external probabilities and multi-forecaster aggregation are not implemented; unknown keys are refused. Each lineage has a single producer, and the two exogenous methods share one history lineage (`independent_exogenous_lineages: 1`).

## Methods (parameters frozen before the corpus)

| method_id | lineage | rule |
|---|---|---|
| `independent_stratum_prior_v1` | EXOGENOUS | Beta-smoothed base rate `(k + a) / (n + a + b)` over admitted history in the same category × horizon band. ABSTAIN (`ABSTAIN_NO_TRAINING`, with successes / n / required_n) when n < `min_training_n`. It never falls back to 0.5 or to a price. |
| `train_base_rate_global_v1` | EXOGENOUS | The same formula over all admitted history. This is the train-only base-rate baseline. |
| `market_reference_price_v1` | MARKET_PRICE | Only a price observed at or before the decision and no older than `max_price_age_seconds`. Otherwise `BASELINE_UNAVAILABLE:<PRICE_MISSING, PRICE_CLOCK_MISSING, PRICE_AFTER_DECISION or PRICE_STALE>`. Never backfilled. |
| `wang_probit_distortion_v1` | MARKET_PRICE_DERIVED | Intercept-only `Pr(y=1) = Phi(Phi^-1(p) - lambda)`. lambda is the bounded MLE in [-1, 1], found by a 120-step golden-section search on the convex probit NLL (rounded to 1e-9), with p clipped to 1e-6 and Phi clipped to 1e-12. Training uses only history prices in [0.05, 0.95]. It is applied to the target's contemporaneous price and ABSTAINs when n < `wang_min_training_n`. It is never EXOGENOUS and never substituted for the independent forecast. |

Training is per target. A history row is used only if its resolution, resolution-known and source-observed clocks are all strictly before the target decision. The excluded count is recorded, along with the SHA-256 of the training ids.

History rows are refused (and counted) in these cases:
- BACKFILLED, or invalid fields (bool outcome, bad clock and so on);
- clocks not ordered `decision < resolution <= known`;
- crypto category;
- an `event_group` equal to any eligible target's native event, which would mean train/evaluation leakage.

## Frozen cohort (labels are never read)

1. Eligible targets are reduced to one market per native event. The kept market is the lowest `sha256(seed|case_id)`; the others are counted as `EVENT_GROUP_DUPLICATE`.
2. The strata are `category × horizon band × contemporaneous price band`. A missing or invalid price gets its own `MISSING` band.
3. `sample_n` slots are apportioned across strata by largest remainder (the ForecastBench method). Ties go by remainder, then stratum size, then name, and any shortfall is filled from the largest strata.
4. Within a stratum, cases are drawn in ascending `sha256(seed|case_id)` order.

Every stratum's available / selected count and `inclusion_probability_within_stratum` is recorded (overall inclusion = per-row `event_group_selection` × within-stratum probability), and so are the `offered`, `eligible`, `event_groups`, `event_group_duplicates`, `sampling_frame`, `requested`, `selected` and `not_sampled` counts, the per-reason ineligibility counts, and the membership SHA-256.

## Scoring

- An outcome is scorable only if all of the following hold:
  - it is resolved;
  - its label is in the native labels;
  - its provenance matches the corpus (`SANITIZED_SYNTHETIC_LABEL` or `LOCAL_RESOLUTION_RECORD`);
  - `resolved_time <= known_time`;
  - `resolved_time` is after the decision (`OUTCOME_RESOLVED_BEFORE_DECISION` otherwise), and `known_time` is at or before `scoring_cutoff`.

  Anything else is counted as NOT_SCORABLE, with the reason.
- **Per case:**
  - Brier is `(p - y)^2`, computed in Decimal with no clipping.
  - Log loss is `-ln(q)` with `q` clipped to `[1e-12, 1 - 1e-12]`, computed in Decimal at precision 50. Every clipped case is counted.
  - The Metaculus binary baseline score is `100 * ln(2q) / ln 2`.
  - Means are quantized to 12 decimal places, half-even.
- **Per method:** the receipt reports scores on its own available set and on the primary paired intersection (scorable cases where the independent prior, market and base rate all forecast; Wang is reported on its own `paired_with_wang` subset of that set, so a Wang abstention never removes the primary comparison), plus abstained, unavailable and boundary-0/1 counts (`errors` is always 0: any error is a whole-run `INTERNAL_VALIDATION_FAILED` stop) and the cost (`LOCAL_CPU_ONLY`, 0 calls, `"0"` USD). Lift deltas (independent minus market) are reported only on the paired set. `lift_status` is `SYNTHETIC_CONTRACT_EVIDENCE_NOT_VALUE`, `LOCAL_OBSERVATION_UNREVIEWED_NOT_VALUE` or `NO_PAIRED_CASES`. Latency is the non-identity `total_ms`.

## Receipt

- `receipt_id` is `fcsteval:sha256:` + SHA-256 of the canonical core.
- The core binds the code identity, which is a hash over this module, the CLI and the SRC-01 module and CLI.
- It also binds the SHA-256 of every frozen input file, the cases hash, method parameters, per-target binding rows, the cohort, history accounting, every forecast with its training counts, scoring, source pins, adoption, authority and the mandatory successor `S10-R3-LEARN-01`.
- Cold verify reports the mismatched top-level sections as `OUTPUT_MISMATCH:<key>`, and also `RECEIPT_ID_MISMATCH`, `FROZEN_CASES_MISMATCH` and `NON_IDENTITY_INVALID`.
- **Versions.** New runs write `s10-r3-forecast01-score-receipt-v2`, which adds `wp170.membership`. Historical `s10-r3-forecast01-score-receipt-v1` receipts still cold-verify. `verify` reads the schema the receipt claims and rebuilds a v1 core in the original v1 shape. It binds that core to the pinned original code identity `LEGACY_V1_CODE_IDENTITY` (`code:sha256:1309f030…419ed`), which is the hash of the four identity files at merged main `c249409`. It never stamps the current code digest on a v1 receipt. An unknown or forged schema is rebuilt as v2, so it fails as a mismatch. Altering the scores or the code identity of a v1 receipt, or relabelling it as v2, is `TAMPER_DETECTED`, even when the forger recomputes a self-consistent `receipt_id`.
- **Limit.** v1 receipts written before `43e3d94` (REL-01 changed `run_source_grounding.py`) carry an older code identity. They already failed cold verify on `c249409` and are not covered (deferred D002 of S10-R3-FORECAST-WP170-BIND-01).

## Run refusal precedence (stable codes)

The categories run from `PACKAGE_INVALID`, `SCOPE_VIOLATION`, `FILE_READ_ERROR` (`CASES_UNREADABLE`), `INPUT_INVALID` (`CASES_JSON_INVALID`, `CASES_FIELDS_INVALID`, `METHOD_INVALID`, `SAMPLER_INVALID`, `DUPLICATE_CASE_ID`, `DUPLICATE_HISTORY_ID`, `FORBIDDEN_FIELD`, `SECRET_MATERIAL_REJECTED`) and `SOURCE_INVALID` (`GROUNDING_VERIFY_FAILED`, `GROUNDING_RECEIPT_MISMATCH`, `CORPUS_CLASS_MISMATCH`, `WP170_*`) through `TEMPORAL_INVALID`, `ABSTAIN_NO_TRAINING`, `NOT_SCORABLE`, `BASELINE_UNAVAILABLE` and `VERIFY_REFUSED` (`TAMPER_DETECTED`) to `INTERNAL_VALIDATION_FAILED`.

Temporal, abstention, scoring and baseline outcomes are per-case counts, not whole-run stops. The spec's `failure_precedence` section is the unchanged native WP159 schema precedence.

## Source pins (all ADAPT or READ-ONLY concept, no code copied, no dependency)

| ID | pin | license | use |
|---|---|---|---|
| R3-01 | Metaculus/forecasting-tools@a54dd64 `forecast_bots/forecast_bot.py` | MIT | forecast-or-refuse protocol, producer lineage |
| R3-06 | gnosis/prediction-market-agent-tooling@817117d `benchmark/benchmark.py` | LGPL-3.0 | same-case outcomes, abstention, error and cost accounting |
| R3-10 | YichengYang-Ethan/prediction-market-pricing@04b916c `identification/external_benchmark.py` | MIT | exogenous vs market-derived separation only (no benchmark data) |
| R3-10-WANG | same pin `models/hierarchical_wang_mle.py` | MIT (repository) | intercept probit distortion likelihood, bounds and clips |
| R3-12 / R3-12-SAMPLER | forecastingresearch/forecastbench@e8d3c94 `question_sampling/_sampling.py` | MIT | composite-bin largest-remainder apportionment, seeded draw |
| R3-18 | Metaculus/metac-bot-template@bcbd016 `integrations/main_lightningrod_eval.py` | none declared | protocol concept for independently written tests only |
| R3-20 | Metaculus/metaculus@bfae5fe `scoring/score_math.py` | BSD-2-Clause | binary baseline score formula |
| R3-22 | forecastingresearch/forecastbench-sim@27776fc `packages/fbsim-benchmark/tests/test_contract.py` | GPL-3.0 | adversarial contract-test concepts; tests independently authored |

Gnosis is neither installed nor imported. `src/data_layer/calibration_metric_computation.py` measures coverage quality, not forecast scores, and is not used. `src/live_pilot/calibration.py` is protected and is not read by this code.

## Frozen synthetic corpus

The inline `SANITIZED_SYNTHETIC` corpus is in `tests/tools/alpha/test_forecast_evaluation.py`. Its `CORPUS_SHA256` is `2b8be21612572111e5458a30923fe9a35133d44746a1e9b00e3d8ff8ec161238`.

- **Targets:** 37 markets in 36 native events across 9 categories (1 crypto). 36 are non-crypto, and all are rule hash-bound through SRC-01.
- **History:** 120 resolved prior events (6 categories × 4 horizons) plus 4 explicit refusal rows.

The observed numbers below come from a-priori parameters, with no tuning after observation:
- **Cohort:** offered 37, eligible 36, event groups 35, 1 event duplicate, 1 crypto excluded, sampling frame 35, requested 33, selected 33, not sampled 2.
- **Scoring:** 32 scorable (1 unresolved), paired intersection 29.
- **Paired Brier:**
  - independent prior 0.237860661506
  - global base rate 0.235932591350
  - market 0.133065517241
  - Wang 0.151590323677
- **Paired log loss:**
  - independent 0.668736574038
  - base rate 0.664769554392
  - market 0.428316057643
  - Wang 0.453883214680

The independent prior is worse than the market on this market-aligned synthetic set: NO_LIFT. Synthetic data proves only the contract, never predictive value.

## Adoption truth

- `R3-01`, `R3-06`, `R3-10`, `R3-12` and `R3-12-SAMPLER` are integrated offline and not value-verified.
- `R3-10-WANG` is a market-price-derived comparator and is never independent.
- `R3-18`, `R3-20` and `R3-22` are `PARITY_OPEN_PENDING_KARL_ACCEPTANCE`.
- `value_status` is `NO_REAL_VALUE_VERIFIED`.
- The other 27 of the 36 program IDs, the six provider lanes, Lane B and open PR #268 are unchanged.
- S10-R3-FORECAST-WP170-BIND-01 is a native integration, not an external adoption. It leaves every adoption row unchanged, including the recorded ForecastBench sampler-objective difference (native proportional vs upstream target-weight apportionment).
- `S10-R3-LEARN-01` stays mandatory. It must consume immutable score receipts after resolution and propose only future research priorities, never rewriting a past forecast.
