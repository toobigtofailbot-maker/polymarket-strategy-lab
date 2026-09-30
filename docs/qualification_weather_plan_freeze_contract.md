# Weather Qualification Prospective Plan Freeze Contract (S10-QUAL-PLAN-01)

Status: governed by `docs/wp_specs/S10-QUAL-PLAN-01/` (FAST, risk 2, exact 13-path scope, docs/tests only).
Authority: ANALYTIC COMMITMENT ONLY. This contract and its plan create no `PreregisteredExperiment`, no
lifecycle/OOS-release record, no real `QualificationCandidate`, no qualification-gate receipt, no DATA-03 data, no
model fit, no score and no network call. **WP170 remains the sole preregistration/OOS authority.**
Gate C: NOT AUTHORIZED. Live: DISABLED. Capital at risk: USD 0. Orders: 0.

## 1. Frozen artifact and identity

- Plan: `docs/qualification_plans/S10-QUAL-PLAN-01/weather_plan_v1.json`.
- Canonical bytes: UTF-8, object keys sorted, compact separators `(",", ":")`, no binary floats / NaN /
  Infinity, ASCII-only content, no trailing newline. Every non-integer number is a canonical decimal string.
- Authoritative plan hash: `sha256(exact file bytes)` =
  `1124ecfb528e5055e4193a885e89a5d9bde74df501b48a0ca4ebded8df89c46e`. The hash is never inside its own preimage.
- Power analysis: `docs/qualification_plans/S10-QUAL-PLAN-01/power_analysis_v1.md`, bound into the plan by the
  SHA-256 of its LF-normalized UTF-8 bytes (`f20f24a26444c93389b10a34ed1a88530aca0f64bc7efb694dccce826c6ee884`), so
  a Windows CRLF checkout cannot change the binding.
- Top-level keys: `schema_id`, `schema_version`, `wp_id`, `plan_version`, `authority` and the 13 closed sections
  `lineage`, `hypothesis_plan`, `feature_plan`, `label_plan`, `dataset_split_plan`, `sample_power_plan`,
  `test_family_plan`, `forecast_evaluation_plan`, `execution_feasibility_plan`, `forecast_model_spec`,
  `prospective_data_seal`, `wp170_handoff`, `mechanical_resolution_rules`. Every keyset is closed and pinned by
  `tests/data_layer/analytical_research/test_qualification_weather_plan_freeze.py`.
- Any analytic change requires a new plan file, a new family/trial and a new freeze; this file is never edited
  in place after merge.

## 2. Freeze event and prospective boundary

- Frozen OOS start: `2026-10-15T00:00:00Z`. 120-day eligibility cap: `2027-02-12T00:00:00Z`.
- Freeze-validity rule: the PLAN-01 GitHub merge time MUST be `<= 2026-10-14T00:00:00Z`. The authoritative
  freeze time is the GitHub server PR merge timestamp on `main` plus the merge commit SHA; committer/author
  timestamps are not authority. A later merge is `STOP OOS_START_FREEZE_WINDOW_MISSED`; `oos_start` is never moved
  inside the same WP after prospective exposure risk begins (return to Side14 for a later literal).
- All S10-QUAL-DATA-02 dates (2026-08-18..2026-09-26) are permanently `HISTORICAL_NON_OOS`: FORMATION,
  SELECTION and derivation/eligibility checks only.

## 3. Lineage and hypothesis

Bound exactly: alpha candidate
`alphacandidate:sha256:2d1523c8086acf536ad07512e1eaffed9cb9405b65e83c87b89b40ba77ee3add`, family
`alphafamily:sha256:136000bd56f2fc27cf490cf675ddf2715b0acfc1ee934aa5cdf2579925c208d8`, episode
`alphaepisode:sha256:2e4c0f484649930ba2677bc360070f0e9ba6ef0e09ecd23b383a32ff3b69000c` (`RESEARCH_SUPPORTIVE`),
registry head `alpharegistryentry:sha256:4b9a20f7f0e931dfea7cced80a64d7a4be7ccc58e265dbb9ebde15edb2d79847`, AF1
receipt `af1gate:sha256:281c5e05f5e4f8e30687f232e0289b99b0719c87fab61c8b1d1d417dc0b5cbb2`. The S10-ALPHA-REAL-01
research question and Alpha-family falsifiable theme are preserved verbatim as provenance context; the Alpha
registry is not mutated.

Hypothesis `nws-public-weather-incrementality` / `v1` (cohort `polymarket-nws-daily-rain-v1`, horizon
`checkpoint-to-final-market-resolution`, target `binary-rain-ge-0.01in-nws-cli`, `REVIEWED`, code version
`s10-qual-plan-01-weather-plan-v1`): B1 must beat B0, B2 must beat B0 and B2 must add incremental information over
B1 in out-of-sample Brier loss on genuinely prospective dates. Not supported if the absolute Brier criterion or any
fixed-sequence comparison fails, or the OOS evidence is invalid/inconclusive.

## 4. B0, features and label

- B0 `EXTERNAL_PIT_MARKET_PROBABILITY_V1`, `max_midpoint_spread = "0.1"`, `max_last_trade_age_seconds = 86400`:
  the spread `ask - bid` is recomputed; the midpoint only for a valid two-sided Yes-token book with spread
  `<= 0.1`; otherwise the latest observed trade with age `<= 86400` s by capture `timestamp_received`; otherwise
  `B0_UNAVAILABLE`. A B0-missing row leaves B0, B1 and B2 alike before label access; no imputation, no canonical PIT
  relabeling; B0 itself is scored unclipped.
- B1: `wx.ndfd_pop12_max_climate_day_v1` (`PUBLIC_NON_MARKET`,
  `q = clip(max overlapping PoP12_percent / 100, 0.01, 0.99)`) and `time.ndfd_lead_hours_v1` (`TIME_ONLY`,
  `L = (climate_day_start - vintage_public_available_time) / 24h`). B2 adds exactly `mkt.ext_b0_probability_v1`
  (`MARKET_EXTERNAL_RECONSTRUCTION`, model input `m = clip(B0, 0.001, 0.999)`); B2 is exact `B1 ∪ added`.
- Label `label.polymarket_nws_cli_rain_yes_v1`: Yes iff rule-bound NWS CLI precipitation `>= 0.01` inch; trace does
  not count; DATA-02 rule-bound local-standard-time climate day; final Gamma outcome and v3 `market_resolved` must
  agree under the existing finality policy; DATA-02/03 source-read exclusions remain exclusions; no label value
  enters B0 or any feature.

## 5. Forecast model (frozen before OOS)

`p1 = sigmoid(β0 + β1*logit(q) + β2*L)` and `p2 = sigmoid(γ0 + γ1*logit(q) + γ2*L + γ3*logit(m))`: binary
logistic regression, intercept, no interactions, no feature dropping, no alternate model, Firth/Jeffreys-prior bias
reduction (Bernoulli log-likelihood plus `0.5*log(det(I(β)))`, no tunable penalty), unweighted FORMATION rows only.
Solver: Firth-modified Newton-Raphson / Fisher scoring, full step, all-zero initialization, converged when
`max(abs(delta_coefficient)) < 1e-10` (plan decimal `"0.0000000001"`), at most 100 iterations; a non-finite
coefficient, a singular information matrix or no convergence by iteration 100 is `FIT_FAILED` with no fallback,
restart, model substitution or alternate feature set. Any later implementation/library is admissible only with
deterministic parity tests against these semantics. SELECTION is diagnostics only (calibration intercept/slope,
Brier, 10-bin reliability) and causes no refit, recalibration, feature/model choice or threshold change; any
analytic change after SELECTION invalidates the plan. Post-hoc calibration NONE; hyperparameter search NONE; search
space `{}`; randomness NONE.

## 6. Splits, floors and power

- `group_policy = EXCLUSIVE`, `event_grouping_rule = LEAKAGE_MARKET_RELATED_EXCLUSIVE`,
  `leakage_group_id = related_group_id = target_date`; all checkpoints/cities of one date share one role. Embargo
  `172800` s; purge `PURGE_LABEL_AVAILABILITY_AT_OR_AFTER_NEXT_BOUNDARY`; inclusion `DECISION_TIME_HALF_OPEN`;
  `min_samples_per_role = 100`.
- Historical allocation (MR14): FORMATION precedes SELECTION; SELECTION = the last 7 eligible historical dates with
  `>= 5` effective SELECTION dates after purge/embargo; FORMATION `>= 385` structurally eligible rows and `>= 20`
  effective dates (Riley criterion iii; EPV10 not used). Allocation never depends on outcomes/performance.
  Shortfalls are `QUAL_FORMATION_INSUFFICIENT` (fewer than 385 structurally eligible rows or 20 effective dates) / `QUAL_SELECTION_INSUFFICIENT`
  (fewer than 5 effective dates or 100 rows); `ROLE_BOUNDARY_CROSSING_EXCLUDED` is the closed historical exclusion code.
- Prospective OOS: statistical unit `target_date`; per-date loss = mean row-level Brier differential; target 50
  effective dates from power `0.8`, one-sided alpha `0.025`, `dz = 0.5`, `rho1 = 0.25`, VIF `1.5`
  (derivation and sensitivity in the power-analysis doc; development sufficiency is kept separate from OOS power).

## 7. Test family

Primary `BRIER_SCORE`; secondary diagnostic `LOG_LOSS` (computed on probabilities clipped to [0.001, 0.999] for B0,
B1 and B2 alike, diagnostic only; B0 stays unclipped for the Brier primary, the absolute criterion and every
confirmatory comparison); absolute criterion B2 `LTE 0.25`; calibration diagnostic =
10 equal-width reliability bins with Murphy decomposition. Fixed sequence (one-sided, FWER 0.025): 1. B2 vs B0,
2. B2 vs B1, 3. B1 vs B0; a later comparison is confirmatory only if every preceding one rejects.
`correction_policy = FAMILY_TRIAL_COUNT`, `family_size = 3`. Frozen statistic: Diebold-Mariano on `d_1..d_50` with a
Newey-West Bartlett lag-1 long-run variance `V = gamma_0 + gamma_1`; reject iff `V > 0` and
`DM <= -t_{0.975, 49}`. No predictive score is computed by this WP.

## 8. Prospective DATA-03 seal

- DATA-03 may store content-addressed raw bytes, decode labels internally only for closed eligibility and
  source-agreement checks, materialize feature values only inside the sealed store and materialize the sealed B0
  basis/value.
- Before WP170 OOS release DATA-03 must not expose label values, prevalence, per-market outcomes, feature
  distributions, B1/B2 forecasts, Brier/log-loss, model coefficients, comparison statistics or any result-dependent
  summary. Visible: counts by closed reason, eligible row/date counts per checkpoint, B0 availability and
  midpoint-vs-trade basis counts, coverage classes, network/seed accounting, ids/hashes and execution-terms states.
- Eligibility (MR13): a date is considered only when every included row decision time is `< 2027-02-12T00:00:00Z`;
  it is OOS-eligible only when it has an eligible row and every included row decision time is
  `>= 2026-10-15T00:00:00Z` and also `>= 2026-10-17T00:00:00Z` (see section 11). Eligibility depends only on source,
  data-quality, feature, B0 and label-source-agreement availability, never on an outcome value or performance.
  `D1..D50` are the chronologically first 50 eligible dates; a pending date is never skipped and an entered date is
  never replaced.
- Seal: `oosmembership:sha256:<64hex>` over the canonical JSON of exactly `plan_01_plan_sha256`, `oos_start`, `cap`,
  `end_time` (MR09), `oos_target_dates`, `oos_row_ids`, `oos_exclusions` (with closed reason codes) and
  `data03_bundle_id`. Future REAL-01 and WP170 split assignment must reproduce it exactly.
- Before the cap with fewer than 50 dates: `ACCRUAL_INCOMPLETE` (structural counts only). Fewer than 50 at the cap:
  `QUAL_OOS_INSUFFICIENT_AT_CAP`: no extension, no REAL-01, no score; a new attempt needs a new plan/family/trial and
  a later prospective boundary. A sealed 50-date membership with fewer than 100 OOS rows is
  `QUAL_OOS_ROWS_INSUFFICIENT` (WP170 would reject the split; no REAL-01, no score).

## 9. Execution-evidence meaning

Critical classes may be `AVAILABLE` only when official/current evidence is captured with an honest
availability/capture timestamp at or before the candidate cutoff, provenance-bound, sufficient for the
candidate-specific experiment and not represented as historical. DATA-02 `CURRENT_ONLY` facts stay `CURRENT_ONLY`.
DATA-03 must capture at minimum the current open daily-rain Gamma market documents, official fee documentation,
current resolution-rule text/cohort semantics, current `orderPriceMinTickSize` and `orderMinSize`, and official
tick-change semantics when published. Meanings: `FEES` current forward fee regime; `RESOLUTION_RULES` current
station/CLI/threshold/climate-day/finality semantics; `TICK_SIZE_MIN_ORDER` current tick/min-order constraints plus
available tick-change history; `SPREAD_DEPTH` may remain PARTIAL; `LATENCY` and `PARTIAL_FILL` may remain MISSING.
State derivation is mechanical (MR12). Current evidence is never backdated.

## 10. WP170 handoff

`preregistered_at` is the actual build time of the future `PreregisteredExperiment` and never the PLAN-01 freeze
time. `creation_provenance` must bind the PLAN-01 plan SHA-256, the PLAN-01 merge commit SHA, the DATA-03
`oosmembership` id, the REAL-01 `QUAL_PASS` receipt id and a statement that the experiment inputs equal the frozen
plan. `search_space_json = {}`; `parameters_json` holds only frozen model constants (never fitted coefficients);
`random_seeds = []` (the current WP170 validator admits the empty tuple; `[0]` is not used); split `oos_start`
equals the PLAN-01 literal. The current WP170 cannot encode the NDFD B1 feature dependencies: that later feature
bridge is eligible only after a real `QUAL_PASS` and blocks neither PLAN-01 nor prospective accrual. WP170 is
unchanged by this WP. The WP170 `ResearchDatasetManifest` samples are exactly the surviving MR14 FORMATION/SELECTION
rows plus the sealed `oos_row_ids` (MR15): no excluded-date row, no row of a date after D50 and no row before
`oos_start` ever enters the WP170 split, so WP170's decision-time role assignment reproduces the membership exactly.

## 11. Mechanical resolution (no operator discretion)

Every data-dependent candidate field is a closed rule `MR01`..`MR15` in `mechanical_resolution_rules`, never an
editable placeholder: information cutoff (MR01), provenance manifests (MR02), creation provenance (MR03), feature
and label evidence refs (MR04/MR05), external dataset refs (MR06), formation/selection starts (MR07/MR08), end time
(MR09), OOS row/date counts (MR10/MR11), execution states (MR12), OOS membership (MR13) and historical allocation
(MR14) and the WP170 sample set (MR15). An unresolvable rule is `PLAN_MECHANICAL_RESOLUTION_FAILED`. The static decisions resolve with synthetic
values into plan bodies accepted unchanged by the existing `build_qualification_candidate` (tested with the
synthetic S10-QUAL-01 Alpha fixture only; no real candidate).

Four closed rules follow mechanically from the existing validators rather than from any new analytic choice:

- WP170 embargoes every OOS row with `decision_time < oos_start + 172800` s, so a date with an included row before
  `2026-10-17T00:00:00Z` is excluded (`OOS_DATE_DECISION_IN_WP170_EMBARGO`) to keep the membership exactly
  reproducible by WP170.
- A FORMATION-date row at or after `selection_start` is excluded (`ROLE_BOUNDARY_CROSSING_EXCLUDED`) so no target
  date straddles two roles under the exclusive leakage grouping.
- A market without an agreeing final label 604800 s after its climate day ends is excluded
  (`LABEL_GAMMA_NOT_FINAL`) so every considered date's eligibility becomes decidable.
- More than 256 provenance manifests is `QUAL_PROVENANCE_LIMIT_EXCEEDED` (the existing
  `MAX_QUALIFICATION_PROVENANCE_MANIFESTS`); there is no aggregation, substitution or omission.

## 12. Successor

If PLAN-01 merges before the freeze deadline, return to Side14. Next expected package: S10-QUAL-DATA-03 —
Prospective Weather Qualification OOS Accrual + Execution-Terms Capture (separately gated; preserves the sealed
plan without analytic changes). Only after 50 effective prospective dates and a valid final membership seal may
S10-QUAL-REAL-01 build the one real candidate and run the qualification gate; only a real `QUAL_PASS` makes the
WP170 feature bridge / candidate-specific experiment eligible to be drafted. WP170/WP172/WP173 remain not started.
