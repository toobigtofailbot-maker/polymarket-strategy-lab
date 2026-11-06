# Outcome Learning Feedback Contract (S10-R3-LEARN-01)

Status: RESEARCH_ONLY / DIAGNOSTIC_ONLY / NO_CANONICAL_WRITE. Local, offline, stdlib only.

This contract defines the mandatory R3 learning loop. A frozen, verified S10-R3-FORECAST-01 receipt is joined with later outcome records. The original probabilities are scored unchanged. The run then produces descriptive diagnostics and advisory future-research proposals.

The loop proves mechanism and accounting only. It never proves predictive value, OOS lift, qualification, settlement origin or an execution edge.

## 1. Callers

- Module: `src/data_layer/analytical_research/learning_feedback.py`
- Operator: `tools/alpha/run_learning_feedback.py`

```
run    --forecast-scratch ABS --outcomes ABS --scratch-dir ABS [--alpha-registry ABS]
verify --scratch-dir ABS
```

The call path is `run -> run_forecast_evaluation.verify (caller scratch) -> freeze -> run_forecast_evaluation.verify (frozen copy) -> learning_feedback.build_learning_core -> forecast_evaluation.score_one`.

`run` executes one finite foreground pass, with no scheduler and no background work. `verify` repeats the whole recomputation from the frozen copies and never writes.

## 2. Compatibility table (merged FORECAST-01, read-only)

| Item | Actual merged shape used | Use here |
|---|---|---|
| Forecast receipt | `{core, receipt_id: "fcsteval:sha256:…", non_identity}` | `receipt_id` bound as `upstream.forecast_receipt_id` |
| `core.cohort` | `selected_case_ids` (sorted), `membership_sha256` | one-to-one with `core.targets[status=SELECTED]` and `core.forecasts` keys, else `FORECAST_COHORT_INCONSISTENT` |
| `core.targets` | per row `case_id, market_id, event_group, category, horizon_band, yes_label, outcome_labels, decision_time, rule_content_sha256` | join identity and decision clock for each outcome |
| `core.forecasts` | `{case_id: {methods: {m: {status, p_yes, lineage}}}}` | only `status == FORECAST` p_yes is scored, verbatim |
| `core.scoring` | original FORECAST-01 scores | hashed as `original_scoring_snapshot_sha256`; never amended |
| `core.inputs.scoring_cutoff` | original cutoff | recorded as `original_scoring_cutoff`; a separate `learning_cutoff` governs this run |
| `frozen_cases.json` targets `.outcome` | may hold retrospective labels | used **only** as a prior-label consistency check, never to regenerate p |
| `run_forecast_evaluation.verify(dir)` | returns `{status: VERIFIED…}` or raises its own stop | any non-VERIFIED result or stop becomes `FORECAST_VERIFY_FAILED` |
| `forecast_evaluation.score_one(p: Decimal, y: int)` | Brier, log loss with ε=1e-12, Metaculus baseline, clipped flag | the only scorer; aggregated by `forecast_evaluation._aggregate` |
| Alpha registry | `alpha_factory_registry.load_and_verify_alpha_factory_registry` (opened read-only, mode `ro`) | optional advisory candidate and episode linking via `subject_refs` |
| WP170 | the forecast receipt's `wp170` block | inherited unchanged; this WP never reads or writes a WP170 registry |

There is no impossibility. No old module, receipt or registry needed modification.

**Local hash vs settlement origin.** The run checks that the frozen outcome packet bytes match their recorded SHA-256. That is local integrity only. It never authenticates where a settlement came from: `settlement_origin_verified` is always `false`.

## 3. Outcome packet `s10-r3-learn01-outcomes-v1`

The packet is strict UTF-8 JSON, at most 4 MiB. Duplicate keys, NaN and Infinity are rejected. Packet keys are exactly:

- `schema_id`
- `packet_label`
- `forecast_receipt_id` (must equal the verified forecast receipt id)
- `learning_cutoff` (canonical UTC)
- `records` (1 to 4000 items)

Every record has exactly these keys: `case_id, market_id, event_group, yes_label, rule_content_sha256, outcome_label, resolved_time, known_time, local_first_seen_time (nullable), source_content_sha256 (nullable), evidence_class`.

**Evidence class.**

| Forecast `corpus_class` | Only admissible record `evidence_class` | Provenance label |
|---|---|---|
| `SANITIZED_SYNTHETIC` | `SANITIZED_SYNTHETIC` | `SYNTHETIC_LABEL_NOT_SETTLEMENT` |
| `LOCAL_REAL_PIT` | `CALLER_IMPORTED_UNVERIFIED` | `CALLER_IMPORTED_ORIGIN_UNAUTHENTICATED` |

**Record refusal precedence.** The first failing check wins:

1. `RECORD_FIELDS_INVALID`
2. `FOREIGN_CASE`
3. `EVIDENCE_CLASS_MISMATCH`
4. `SOURCE_CLAIM_UNVALIDATED`: any non-null `source_content_sha256`. No source bytes are admitted by this WP, so a claimed hash cannot be validated (D002).
5. `MARKET_MISMATCH`
6. `EVENT_GROUP_MISMATCH`
7. `RULE_MISMATCH`
8. `YES_LABEL_MISMATCH`
9. `OUTCOME_LABEL_UNKNOWN`
10. `CLOCK_INCONSISTENT`: `known < resolved`, or `local_first_seen < known`
11. `RESOLVED_BEFORE_DECISION`: `resolved <= decision`, which also excludes `known <= decision`
12. `PRIOR_OUTCOME_CONFLICT`: a within-cutoff record whose label or `resolved_time` differs from a label already frozen in the forecast inputs

**Clocks.** The availability clock is `local_first_seen_time` when present, otherwise the caller-asserted `known_time`. This is recorded as `clock_basis`. A record is in time only when its availability clock is at or before `learning_cutoff`.

**Per-case state.** Each selected case is in exactly one state. Precedence:

1. `DISPUTED` (`PRIOR_OUTCOME_CONFLICT`)
2. `EXCLUDED` (first refusal reason of an attributable record)
3. `MISSING_OUTCOME` (no record)
4. `LATE_AFTER_CUTOFF` (only post-cutoff records)
5. `DISPUTED` (`DUPLICATE_OUTCOME` or `CONFLICTING_OUTCOME`: more than one in-time record)
6. `SCORABLE` (exactly one in-time record)

**Corrections.** A post-cutoff record for a scorable case goes only into `corrections`, as `CORRECTION_AFTER_CUTOFF_SAME_LABEL` or `CORRECTION_AFTER_CUTOFF_LABEL_CHANGED`, with `conflicts_prior`. It never rewrites the scored label.

**Unattributable rows.** A record with an unusable `case_id` is counted in `records_refused_by_reason` and leaves the case `MISSING_OUTCOME` unless another record attributes to it.

## 4. Whole-run refusal priority

Whole-run refusals emit `STOPPED` with one code and write no receipt. In order:

1. Path and scratch: `SCRATCH_INSIDE_REPOSITORY`, `SCRATCH_NOT_EMPTY`, `FORECAST_SCRATCH_INVALID`.
2. `FORECAST_VERIFY_FAILED`.
3. `OUTCOMES_UNREADABLE`: relative path, symlink, more than one hard link, inside the repo or scratch, empty, or larger than 4 MiB.
4. `SECRET_MATERIAL_REJECTED`.
5. `OUTCOMES_JSON_INVALID`.
6. `FORBIDDEN_FIELD`: the native FORECAST-01 secret and trade key scan.
7. Packet checks: `OUTCOMES_FIELDS_INVALID`, `OUTCOMES_SCHEMA_INVALID`, `PACKET_LABEL_INVALID`, `FOREIGN_FORECAST_RECEIPT`, `LEARNING_CUTOFF_INVALID`, `OUTCOME_RECORDS_INVALID`.
8. Registry: `ALPHA_REGISTRY_UNUSABLE`, `STORE_SIDECAR_PRESENT`.
9. Freeze and receipt: `INPUT_CHANGED_DURING_FREEZE`, `FORECAST_CODE_IDENTITY_MISMATCH`, `FORECAST_COHORT_INCONSISTENT`, `ALPHA_REGISTRY_INVALID`, `NETWORK_ATTEMPT_BLOCKED`, `WRITE_ONCE_CONFLICT`, `INTERNAL_VALIDATION_FAILED`.

Output never echoes paths, exception text or input values.

This product refusal priority sits under the fixed native WP159 failure-precedence categories in the WP spec.

## 5. Scoring

Each frozen method is scored on the scorable cases where its original status is `FORECAST`. The methods are:

- `independent_stratum_prior_v1`
- `train_base_rate_global_v1`
- `market_reference_price_v1`
- `wang_probit_distortion_v1`, always `MARKET_PRICE_DERIVED`

Its original string `p_yes` goes to `Decimal` and then to `score_one`. Abstentions are never interpolated.

**Per-method denominators.** `offered, eligible, missing_outcome, disputed, late, excluded, abstained, unavailable, scored`. Two identities always hold:

- `offered = eligible + missing + disputed + late + excluded`
- `eligible = scored + abstained + unavailable`

**Paired sets.**

- The primary paired set is the exact scorable cases where all three primary methods forecast.
- Wang uses its own subset of that set.
- Both id lists are SHA-256 bound.

**Event groups.** `scorable_event_groups` and `event_groups_disjoint` show that markets of one event never inflate independent counts.

**Deltas.** Deltas are the independent method minus market and minus base rate, for Brier and log loss; lower is better. `lift_status` is always `DIAGNOSTIC_ONLY_NOT_OOS_LIFT_NOT_VALUE`, or `NO_PAIRED_CASES`.

## 6. Diagnostics `learn01-diagnostics-v1`

All diagnostics are descriptive and post hoc: `DESCRIPTIVE_POSTHOC_DIAGNOSTIC_NOT_OOS_NOT_QUALIFICATION_NOT_EDGE`.

**Calibration.** Predeclared edges 0.0, 0.1, …, 1.0 per method on its paired set. Each bin carries `n`, mean p_yes and observed yes rate. A bin is `INSUFFICIENT_SAMPLE` when `n < 5`.

**By category and by horizon band.** Each group reports:

- `selected`, and a count for each state
- `independent_not_forecast` and `paired`
- `evidence_coverage` as a ratio
- the independent mean p, observed rate and absolute calibration gap
- independent-minus-market Brier mean and standard error with `significance_claim: false`
- `identity_refusals`
- `sample_status`: `INSUFFICIENT_SAMPLE` when `paired < 5`

`outcome_vintage` equals `learning_cutoff`.

## 7. Future research proposals (advisory)

There is one proposal per category group. Reasons come from the closed ordered set `RESOLUTION_EVIDENCE_MISSING, SOURCE_RULE_REVIEW, FORECAST_ABSTENTION, INSUFFICIENT_SAMPLE, CALIBRATION_DRIFT_REVIEW, BASELINE_UNDERPERFORMING_REVIEW, NO_PRIORITY_CHANGE`:

| Reason | When it is set |
|---|---|
| `RESOLUTION_EVIDENCE_MISSING` | any missing, late, excluded or disputed case |
| `SOURCE_RULE_REVIEW` | any identity refusal or dispute |
| `FORECAST_ABSTENTION` | the independent method did not forecast a scorable case |
| `INSUFFICIENT_SAMPLE` | `paired < 5` |
| `CALIBRATION_DRIFT_REVIEW` | `gap > 0.15`, only when the sample is sufficient |
| `BASELINE_UNDERPERFORMING_REVIEW` | mean independent-minus-market Brier `> 0`, only when the sample is sufficient |
| `NO_PRIORITY_CHANGE` | nothing else applies |

Each proposal binds:

- the source forecast receipt id
- the cohort membership digest
- the group case-id digest
- an outcome-evidence digest over the group's record SHA-256s
- an `alpha_link`

The `alpha_link` is `ALPHA_LINKED_READ_ONLY`, with the candidate ids whose `subject_refs` hit the group's markets and those candidates' research-episode ids. Without a join it is `ALPHA_LINK_UNVERIFIED` with empty lists; no id is ever invented.

**Identity.** `proposal_id = "learnprop:sha256:" + sha256(canonical(body))`, where `body` excludes `proposal_id` and `priority_rank`, so there is no self-hash cycle.

**Order.** Proposals are ordered by (first reason rank, group value). `priority_rank` is assigned afterwards.

A proposal is not a canonical Alpha queue item, ResearchEpisode, WP170 evidence, requalification or scheduled action. A later, separately authorized decision may adopt it.

## 8. Receipt and cold verify

The run copies the forecast scratch (no symlinks or hard links, bounded size), the packet bytes and the optional registry into `scratch/inputs/`. It writes `receipt.json` once (`xb`) as:

```
{core, receipt_id: "learnfb:sha256:" + sha256(canonical(core))}
```

The core binds:

- the code identity: the module and operator bytes plus the FORECAST-01 code identity
- every input file's SHA-256
- the packet SHA-256
- the upstream identities
- the outcome ledger and states
- scores and diagnostics
- proposals
- authority and adoption

`verify` re-runs the native forecast verifier on the frozen copy, recomputes the core and compares it. Any edit to an input byte, id, time, lineage, score or proposal order gives `TAMPER_DETECTED` or a closed stop.

Zero network is enforced by the shared SRC-01 socket guard around run and verify.

## 9. Adoption truth

- The learning loop is `FUNCTIONAL_LOOP_INTEGRATED_OFFLINE_NOT_VALUE_VERIFIED`.
- All 36 tracked capability ids are unchanged (`capability_status_changes: 0`).
- The six provider lanes stay `UNCHANGED_SIX_OWNER_GATED`: `R3-EXT-PMXT-01, R3-EXT-SYNPATH-01, R3-EXT-LSE-01, R3-EXT-REACH-01, R3-EXT-KAIROS-01, R3-EXT-BECKER-01`.
- R3-10-WANG stays `MARKET_PRICE_DERIVED_NEVER_INDEPENDENT`.
- Value status is `NO_REAL_VALUE_VERIFIED`.
- R3-02 value-unverified and the 12 parity candidates remain as previously adjudicated.
