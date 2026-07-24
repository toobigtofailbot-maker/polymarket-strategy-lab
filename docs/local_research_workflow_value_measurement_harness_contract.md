# Local Research Workflow Value Measurement Harness Contract

## Purpose

This document defines the complete deterministic contract for a future bounded
local research-workflow value-measurement harness. It defines identity,
applicability, corpus coverage, events, operator actions, receipts, scoring,
repeatability, temporary output, human review, safety gates, and the exact
implementation boundary. It does not implement a harness, fixture, writer,
instrumentation, schema change, or measurement run.

## Position After WP150

Merged WP150 is controlling truth:

```text
Remote provider track status:
DEFERRED_PENDING_MATERIAL_NEW_EVIDENCE
Local research workflow value-validation status:
PARTIALLY_READY_BLOCKERS_IDENTIFIED
Research-value metric records:
39
Research-value metrics measured:
0
Research-value metrics measurable but not yet measured:
22
Research-value metrics not currently measurable:
17
Research-value blockers:
7
Paper-trading implementation readiness:
NOT_READY_FOUNDATIONAL_GAPS
Paper-trading execution:
NOT AUTHORIZED
Live-trading execution:
FORBIDDEN
Capital at risk:
USD 0
Orders submitted:
0
Credentials created/used:
0
External model calls:
0
```

WP151 preserves those facts. Contracting future support does not make a metric
measured or currently measurable.

## Authority And Non-Authority

WP151 is authorized to define documentation, stable status, and Markdown-only
regression contracts. It has canonical authority only for the future
measurement-harness contract and the separately gated implementation boundary.

It crosses none of the `credentials/secrets`, `authenticated clients`,
`wallet/account behavior`, `order placement/cancel`, `execution gateway`,
`paper engine`, `scheduler/bot loop`, `runtime/daemon`,
`dashboard/deployment`, `dependency/lock changes`, `external code copying`, or
`generated artifacts` boundary groups in the Centralized Boundary Group
Reference in `docs/ai/codex/PROTECTED_PATHS.md`.

```text
Measurement harness implementation:
NOT AUTHORIZED
Measurement run:
NOT AUTHORIZED
Persistent measurement output:
NOT AUTHORIZED
Paper/live/execution authority:
FORBIDDEN
WP152 requires separate approval
```

## Repository Inputs Reviewed

The mandatory startup and workflow-governance layer; merged WP149 and WP150
decision, tests, status, and PR evidence; the complete WP150 39-row grounding
matrix and all cited current artifacts; the WP150 20-stage inventory; WP142
gold-case fixture/rubric and tests; WP145 local dry-run harness, tests, operator
note, and status; project status, repo-truth index, deferred-items log; and
strategy, paper, live, credentials, runtime, risk, execution, reconciliation,
monitoring, and scheduling boundaries were reviewed. No external research was
performed.

Repository discovery confirmed exactly 39 metrics, the corrected 22/17 split,
seven research-value blockers, 20 stages, zero value-measurement receipts, and
zero implementation of this harness.

## Contract Architecture

```text
Measurement architecture:
LOCAL_DETERMINISTIC_OPERATOR_INITIATED_TEMPORARY_HARNESS
Execution posture:
OFFLINE_LOCAL_NO_PROVIDER_NO_MARKET_NETWORK
Authority posture:
RESEARCH_MEASUREMENT_ONLY_NO_STRATEGY_NO_PAPER_NO_LIVE
Output posture:
IN_MEMORY_OR_PYTEST_TEMPORARY_ONLY
Orchestration posture:
EXPLICIT_SINGLE_RUN_NO_SCHEDULER
```

The future harness is deterministic, operator initiated, offline,
credential-free, provider-free, model-free, Hermes-runtime-free,
strategy-free, paper-free, live-free, scheduler-free, and fail closed.

Compatibility and impossibility check:

| Required behavior | Controlling mechanism | Allowed in WP151 | Compatible | Action |
|---|---|---|---|---|
| Preserve 39/22/17 truth | merged WP150 grounding matrix | YES | YES | copy identities and states exactly |
| Define complete Wave 1 contract | current structured fields plus fixed future corpus contract | YES | YES | define only; implement in WP152 |
| Enable Wave 2 schemas | missing current fields and coverage | NO | YES | define exact future requirement; separate enablement WP |
| Run measurements | future harness and fixture | NO | NO | explicitly forbid |
| Persist receipts | writer or durable store | NO | NO | temporary/in-memory only |
| Cross paper/live boundaries | protected subsystems | NO | NO | preserve forbidden authority |

## Measurement Waves

```text
Initial harness metric scope:
GROUNDED_22_METRICS_ONLY
Blocked metric posture:
CONTRACT_DEFINED_IMPLEMENTATION_DEFERRED
Wave 1 metric count:
22
Wave 1 status:
CONTRACTED_FOR_FUTURE_BOUNDED_IMPLEMENTATION
Wave 2 metric count:
17
Wave 2 status:
BLOCKED_PENDING_SCHEMA_DERIVATION_OR_COVERAGE_IMPLEMENTATION
```

Wave 1 contains only WP150 `MEASURABLE_NOT_YET_MEASURED` metrics. Wave 2
contains only WP150 `NOT_CURRENTLY_MEASURABLE` metrics. No Wave 2 row may
produce a measured value in WP152.

Wave 2 enablement requirements:

| metric_id | missing_field_or_derivation | missing_corpus_or_rubric_coverage | required_future_schema | required_validation | required_negative_tests | separate_schema_enablement_wp |
|---|---|---|---|---|---|---|
| RV-THR-03 | candidate-stage monotonic duration | timed candidate cases | `candidate_stage_timing` with start/end event references | nonnegative ordered duration and case binding | missing, duplicate, negative, cross-case timing | YES |
| RV-THR-04 | intervention event count | intervention/no-intervention cases | typed `operator_intervention_events` | allowed action, stage, case, and reason | unknown, duplicate, identity-bearing intervention | YES |
| RV-THR-05 | completed manual-stage ledger | completed/skipped manual cases | ordered `manual_stage_completion` records | known stage and explicit completion state | prose-only, unknown, duplicate, reordered step | YES |
| RV-REJ-03 | deterministic resolution-clarity score | clear, ambiguous, and incomplete resolution cases | versioned resolution-path labels and rubric | fixed applicability and category scale | free-form inference, missing source class, unknown label | YES |
| RV-HYP-01 | structured falsifiable statement | positive and non-falsifiable hypotheses | `falsifiable_statement` plus observable refutation condition | nonempty structured fields and rubric applicability | question text substituted for structured field | YES |
| RV-HYP-04 | structured expected mechanism | mechanism-present/absent cases | `expected_mechanism` with inputs, relationship, and observable consequence | exact keys and bounded labels | free-form mechanism, unknown relationship | YES |
| RV-HYP-05 | structured horizon | bounded/unknown horizon cases | `horizon` with unit, lower, upper, and uncertainty state | unit and ordered bound validation | wall-clock now, negative or inverted horizon | YES |
| RV-HYP-06 | structured resolution path | source hierarchy and ambiguity cases | `resolution_path` with source class, rule, conflict state, and fallback | deterministic hierarchy and conflict validation | silent conflict resolution, missing rule | YES |
| RV-HYP-07 | measurable test plan | complete/incomplete plan cases | `test_plan` with input, outcome, threshold, horizon, and invalidation | exact keys, typed threshold, linked hypothesis | prose-only plan, missing threshold or horizon | YES |
| RV-REP-03 | workflow-wide schema/version identity | version mismatch across all applicable stages | explicit record schema versions plus version manifest | exact 20-stage compatibility matrix | missing, unknown, mixed, or renamed version | YES |
| RV-HOF-03 | structured assumptions | present/missing/contradictory assumptions cases | neutral `assumptions` sequence with evidence state | bounded values and no action language | free-form substitution, recommendation leakage | YES |
| RV-HOF-05 | neutral research risk relevance | present/missing risk-relevance cases | `risk_relevance` with category, uncertainty, and validation consequence only | non-authoritative labels and forbidden-content scan | size/order/position implication, unknown category | YES |
| RV-OPB-01 | setup/run/review durations | complete operator timing cases | typed operator-phase monotonic event references | ordered nonnegative durations | wall-clock, missing phase, negative duration | YES |
| RV-OPB-02 | correction-loop receipt | zero/one/multiple correction cases | linked correction request and acknowledgement records | contiguous loop sequence and bounded retry count | orphan, duplicate, unbounded loop | YES |
| RV-OPB-03 | expertise rubric | bounded anonymized expertise cases | versioned non-identity expertise category | fixed scale and human review | username, employer, free-form biography | YES |
| RV-OPB-04 | recovery-event record | recoverable and aborted cases | typed recovery action, trigger, result, and stage | allowed recovery transitions | scheduler/retry loop, unknown action | YES |
| RV-OPB-05 | manual-transfer receipt | zero and bounded transfer cases | typed transfer action count without payload | nonnegative count and known stage | raw clipboard data, private text, identity | YES |

All 17 rows require a separately approved Wave 2 schema-enablement package.
That is an implementation decision already made, not an architecture question
deferred to WP152.

## Canonical Metric Registry

Registry version: `local-research-value-metrics-v1.0`.

| metric_id | dimension | metric | wp150_state | wave | measurement_type | exact_input_fields_or_derivation | applicable_stage_ids | corpus_case_ids_or_family | aggregation | fail_closed_condition | receipt_field | human_review |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| RV-THR-01 | Research throughput | markets reviewed | MEASURABLE_NOT_YET_MEASURED | WAVE_1 | COUNT | distinct validated `MarketSnapshotRecord.market_id` in selected bounded input | LRW-02; LRW-04; LRW-06; LRW-07 | LVM-001; LVM-002; LVM-004 | SUM_DISTINCT_PER_CASE_THEN_SUM | missing or invalid market ID, or unselected input counted | metric_results[].count | REQUIRED |
| RV-THR-02 | Research throughput | candidates produced/rejected | MEASURABLE_NOT_YET_MEASURED | WAVE_1 | COUNT | count `candidate_items[].candidate_id` by allowed `candidate_label` | LRW-09; LRW-10 | LVM-005 | SUM_COUNTS_BY_LABEL | missing ID, unknown label, or duplicate candidate counted | metric_results[].count | REQUIRED |
| RV-THR-03 | Research throughput | time per candidate | NOT_CURRENTLY_MEASURABLE | WAVE_2 | NOT_IMPLEMENTABLE_YET | missing `candidate_stage_timing` monotonic event references | LRW-09; LRW-10 | candidate timing family not implemented | BLOCKED | any status other than BLOCKED_WAVE_2 | metric_results[].measurement_status | REQUIRED |
| RV-THR-04 | Research throughput | operator intervention count | NOT_CURRENTLY_MEASURABLE | WAVE_2 | NOT_IMPLEMENTABLE_YET | missing typed operator intervention event sequence | LRW-12 through LRW-20 | intervention family not implemented | BLOCKED | any status other than BLOCKED_WAVE_2 | metric_results[].measurement_status | REQUIRED |
| RV-THR-05 | Research throughput | manual steps | NOT_CURRENTLY_MEASURABLE | WAVE_2 | NOT_IMPLEMENTABLE_YET | missing ordered manual-stage completion ledger | LRW-16; LRW-19; LRW-20 | manual completion family not implemented | BLOCKED | any status other than BLOCKED_WAVE_2 | metric_results[].measurement_status | REQUIRED |
| RV-THR-06 | Research throughput | incomplete records | MEASURABLE_NOT_YET_MEASURED | WAVE_1 | COUNT | count validator results where `is_valid` is false and group deterministic `errors` | LRW-09; LRW-10 | LVM-005; LVM-014 | SUM_COUNTS_BY_ERROR_CODE | invalid record accepted, unknown error, or double count | metric_results[].count | REQUIRED |
| RV-REJ-01 | Candidate rejection quality | reason completeness | MEASURABLE_NOT_YET_MEASURED | WAVE_1 | BOOLEAN_COVERAGE | every required `candidate_reason_labels` value is nonempty and allowlisted | LRW-09; LRW-10 | LVM-005; LVM-014 | ALL_APPLICABLE_CASES_TRUE | missing, empty, duplicate, or unknown reason label | metric_results[].boolean_result | REQUIRED |
| RV-REJ-02 | Candidate rejection quality | evidence coverage | MEASURABLE_NOT_YET_MEASURED | WAVE_1 | SET_COVERAGE | observed required fields/labels from `cited_source_references`, `evidence_for`, `evidence_against`, and `completion_labels` | LRW-13; LRW-18 | LVM-006; LVM-008; LVM-009 | UNION_OBSERVED_OVER_EXPECTED | missing citation/evidence side, unknown label, or zero expected set | metric_results[].set_coverage | REQUIRED |
| RV-REJ-03 | Candidate rejection quality | resolution-rule clarity | NOT_CURRENTLY_MEASURABLE | WAVE_2 | NOT_IMPLEMENTABLE_YET | missing versioned resolution-path labels and clarity rubric | LRW-12; LRW-13 | resolution clarity family not implemented | BLOCKED | any status other than BLOCKED_WAVE_2 | metric_results[].measurement_status | REQUIRED |
| RV-REJ-04 | Candidate rejection quality | data-quality failure detection | MEASURABLE_NOT_YET_MEASURED | WAVE_1 | RATE | seeded failures detected by `QualityIssue.code`, severity, and `QualityGateResult.passed` divided by seeded failures | LRW-08 | LVM-003; LVM-014 | SUM_NUMERATOR_OVER_SUM_DENOMINATOR | zero denominator, unknown issue, or seeded failure missed | metric_results[].numerator; metric_results[].denominator | REQUIRED |
| RV-REJ-05 | Candidate rejection quality | unsupported-claim rejection | MEASURABLE_NOT_YET_MEASURED | WAVE_1 | RATE | unsupported cases with required rejection `receipt_label` and `unsupported_claims_identified` divided by unsupported cases | LRW-13 | LVM-007; LVM-008; LVM-012 | SUM_NUMERATOR_OVER_SUM_DENOMINATOR | zero denominator or unsupported case accepted | metric_results[].numerator; metric_results[].denominator | REQUIRED |
| RV-REJ-06 | Candidate rejection quality | duplicate/contradiction detection | MEASURABLE_NOT_YET_MEASURED | WAVE_1 | RATE | seeded duplicate IDs and `source_conflicts` detected divided by seeded duplicates/conflicts | LRW-08; LRW-13 | LVM-003; LVM-006 | SUM_NUMERATOR_OVER_SUM_DENOMINATOR | zero denominator or seeded duplicate/conflict missed | metric_results[].numerator; metric_results[].denominator | REQUIRED |
| RV-REJ-07 | Candidate rejection quality | deterministic-gate failure rate | MEASURABLE_NOT_YET_MEASURED | WAVE_1 | RATE | failed `QualityGateResult.passed` count divided by all applicable quality-gate results | LRW-08 | LVM-003; LVM-014 | SUM_NUMERATOR_OVER_SUM_DENOMINATOR | zero denominator or pass/fail inconsistent with error counts | metric_results[].numerator; metric_results[].denominator | REQUIRED |
| RV-HYP-01 | Hypothesis quality | falsifiable statement | NOT_CURRENTLY_MEASURABLE | WAVE_2 | NOT_IMPLEMENTABLE_YET | missing structured falsifiable statement and refutation condition | LRW-12 | hypothesis structure family not implemented | BLOCKED | any status other than BLOCKED_WAVE_2 | metric_results[].measurement_status | REQUIRED |
| RV-HYP-02 | Hypothesis quality | supporting and counter-evidence | MEASURABLE_NOT_YET_MEASURED | WAVE_1 | BOOLEAN_COVERAGE | nonempty `evidence_for` and `evidence_against` plus both required completion labels | LRW-13; LRW-18 | LVM-006; LVM-011 | ALL_APPLICABLE_CASES_TRUE | either evidence side or label missing | metric_results[].boolean_result | REQUIRED |
| RV-HYP-03 | Hypothesis quality | invalidation condition | MEASURABLE_NOT_YET_MEASURED | WAVE_1 | BOOLEAN_COVERAGE | validated nonempty `what_would_change_the_conclusion` sequence | LRW-13; LRW-18 | LVM-010; LVM-011 | ALL_APPLICABLE_CASES_TRUE | empty, missing, or invalid sequence | metric_results[].boolean_result | REQUIRED |
| RV-HYP-04 | Hypothesis quality | expected mechanism | NOT_CURRENTLY_MEASURABLE | WAVE_2 | NOT_IMPLEMENTABLE_YET | missing structured mechanism inputs, relationship, and consequence | LRW-12 | mechanism family not implemented | BLOCKED | any status other than BLOCKED_WAVE_2 | metric_results[].measurement_status | REQUIRED |
| RV-HYP-05 | Hypothesis quality | horizon | NOT_CURRENTLY_MEASURABLE | WAVE_2 | NOT_IMPLEMENTABLE_YET | missing bounded horizon unit and ordered bounds | LRW-12 | horizon family not implemented | BLOCKED | any status other than BLOCKED_WAVE_2 | metric_results[].measurement_status | REQUIRED |
| RV-HYP-06 | Hypothesis quality | resolution path | NOT_CURRENTLY_MEASURABLE | WAVE_2 | NOT_IMPLEMENTABLE_YET | missing structured source hierarchy, rule, conflict, and fallback | LRW-12; LRW-13 | resolution path family not implemented | BLOCKED | any status other than BLOCKED_WAVE_2 | metric_results[].measurement_status | REQUIRED |
| RV-HYP-07 | Hypothesis quality | measurable test plan | NOT_CURRENTLY_MEASURABLE | WAVE_2 | NOT_IMPLEMENTABLE_YET | missing typed input, outcome, threshold, horizon, and invalidation | LRW-12 | test-plan family not implemented | BLOCKED | any status other than BLOCKED_WAVE_2 | metric_results[].measurement_status | REQUIRED |
| RV-REP-01 | Reproducibility | exact inputs | MEASURABLE_NOT_YET_MEASURED | WAVE_1 | BOOLEAN_COVERAGE | exact required embedded records and strict keys in manual session package | LRW-11; LRW-20 | LVM-014 | ALL_APPLICABLE_CASES_TRUE | missing, extra, mutated, or unlinked record | metric_results[].boolean_result | REQUIRED |
| RV-REP-02 | Reproducibility | snapshot/fixture identity | MEASURABLE_NOT_YET_MEASURED | WAVE_1 | BOOLEAN_COVERAGE | exact corpus ID/version, registry/stage versions, and ordered case IDs | LRW-05; LRW-18; LRW-20 | LVM-001; LVM-002; LVM-013; LVM-014 | ALL_APPLICABLE_CASES_TRUE | identity/version/order mismatch | metric_results[].boolean_result | REQUIRED |
| RV-REP-03 | Reproducibility | schema/version | NOT_CURRENTLY_MEASURABLE | WAVE_2 | NOT_IMPLEMENTABLE_YET | missing workflow-wide record schema version manifest | LRW-01 through LRW-20 | schema compatibility family not implemented | BLOCKED | any status other than BLOCKED_WAVE_2 | metric_results[].measurement_status | REQUIRED |
| RV-REP-04 | Reproducibility | validation receipt | MEASURABLE_NOT_YET_MEASURED | WAVE_1 | BOOLEAN_COVERAGE | valid `receipt_id`, source references, `receipt_label`, review fields, and safety flags | LRW-13; LRW-20 | LVM-007; LVM-008; LVM-014 | ALL_APPLICABLE_CASES_TRUE | missing/invalid receipt or unsafe flag | metric_results[].boolean_result | REQUIRED |
| RV-REP-05 | Reproducibility | human review | MEASURABLE_NOT_YET_MEASURED | WAVE_1 | BOOLEAN_COVERAGE | valid `reviewer_acknowledgement` and true `human_review_required` | LRW-13; LRW-14; LRW-20 | LVM-011; LVM-012; LVM-014 | ALL_APPLICABLE_CASES_TRUE | acknowledgement absent or review flag false | metric_results[].boolean_result | REQUIRED |
| RV-REP-06 | Reproducibility | rerun consistency | MEASURABLE_NOT_YET_MEASURED | WAVE_1 | REPEATABILITY_EQUALITY | normalized deterministic outputs and metric results equal across three repeats | LRW-07; LRW-18; LRW-20 | LVM-004; LVM-013 | ALL_SELECTED_CASES_PASS | any unexplained normalized mismatch | metric_results[].repeatability_result | REQUIRED |
| RV-REP-07 | Reproducibility | ambiguity record | MEASURABLE_NOT_YET_MEASURED | WAVE_1 | BOOLEAN_COVERAGE | required `source_conflicts`, `uncertainties`, `known_missing_data`, and `limitations` present and valid | LRW-13; LRW-20 | LVM-006; LVM-009; LVM-010; LVM-014 | ALL_APPLICABLE_CASES_TRUE | any required ambiguity field missing | metric_results[].boolean_result | REQUIRED |
| RV-HOF-01 | Strategy-validation handoff quality | research conclusion separated from action | MEASURABLE_NOT_YET_MEASURED | WAVE_1 | BOOLEAN_COVERAGE | required non-authority notice, three safety flags true, forbidden scan empty | LRW-14; LRW-16; LRW-17 | LVM-011; LVM-012 | ALL_APPLICABLE_CASES_TRUE | action language or false/missing authority flag | metric_results[].boolean_result | REQUIRED |
| RV-HOF-02 | Strategy-validation handoff quality | uncertainty represented | MEASURABLE_NOT_YET_MEASURED | WAVE_1 | BOOLEAN_COVERAGE | valid `uncertainty_notes`, `limitations`, and `unresolved_questions` | LRW-14; LRW-17 | LVM-006; LVM-009 | ALL_APPLICABLE_CASES_TRUE | any required uncertainty field missing | metric_results[].boolean_result | REQUIRED |
| RV-HOF-03 | Strategy-validation handoff quality | assumptions explicit | NOT_CURRENTLY_MEASURABLE | WAVE_2 | NOT_IMPLEMENTABLE_YET | missing structured neutral assumptions sequence | LRW-14; LRW-17 | assumptions family not implemented | BLOCKED | any status other than BLOCKED_WAVE_2 | metric_results[].measurement_status | REQUIRED |
| RV-HOF-04 | Strategy-validation handoff quality | data needs explicit | MEASURABLE_NOT_YET_MEASURED | WAVE_1 | BOOLEAN_COVERAGE | valid nonempty missing-data, evidence, source-revisit, and uncertainty-reduction fields | LRW-15; LRW-17 | LVM-009; LVM-011 | ALL_APPLICABLE_CASES_TRUE | any required data-need field missing | metric_results[].boolean_result | REQUIRED |
| RV-HOF-05 | Strategy-validation handoff quality | risk implications explicit | NOT_CURRENTLY_MEASURABLE | WAVE_2 | NOT_IMPLEMENTABLE_YET | missing neutral risk-relevance category, uncertainty, and validation consequence | LRW-14; LRW-17 | risk-relevance family not implemented | BLOCKED | any status other than BLOCKED_WAVE_2 | metric_results[].measurement_status | REQUIRED |
| RV-HOF-06 | Strategy-validation handoff quality | next validation step explicit | MEASURABLE_NOT_YET_MEASURED | WAVE_1 | BOOLEAN_COVERAGE | valid `falsification_check_to_perform`, `blocking_reason`, and `next_manual_step` | LRW-15; LRW-17 | LVM-010; LVM-011 | ALL_APPLICABLE_CASES_TRUE | any required next-step field missing | metric_results[].boolean_result | REQUIRED |
| RV-HOF-07 | Strategy-validation handoff quality | no execution authority leakage | MEASURABLE_NOT_YET_MEASURED | WAVE_1 | BOOLEAN_COVERAGE | recursive forbidden scan empty and all three non-authority flags true | LRW-14; LRW-15; LRW-16; LRW-17 | LVM-011; LVM-012 | ALL_APPLICABLE_CASES_TRUE | any forbidden finding or false/missing flag | metric_results[].boolean_result | REQUIRED |
| RV-OPB-01 | Operator burden | setup/run/review time | NOT_CURRENTLY_MEASURABLE | WAVE_2 | NOT_IMPLEMENTABLE_YET | missing operator-phase monotonic event references | LRW-18; LRW-19; LRW-20 | operator timing family not implemented | BLOCKED | any status other than BLOCKED_WAVE_2 | metric_results[].measurement_status | REQUIRED |
| RV-OPB-02 | Operator burden | correction loops | NOT_CURRENTLY_MEASURABLE | WAVE_2 | NOT_IMPLEMENTABLE_YET | missing linked correction-loop sequence | LRW-18; LRW-19; LRW-20 | correction loop family not implemented | BLOCKED | any status other than BLOCKED_WAVE_2 | metric_results[].measurement_status | REQUIRED |
| RV-OPB-03 | Operator burden | expertise | NOT_CURRENTLY_MEASURABLE | WAVE_2 | NOT_IMPLEMENTABLE_YET | missing versioned anonymized expertise category | LRW-19; LRW-20 | expertise family not implemented | BLOCKED | any status other than BLOCKED_WAVE_2 | metric_results[].measurement_status | REQUIRED |
| RV-OPB-04 | Operator burden | recovery steps | NOT_CURRENTLY_MEASURABLE | WAVE_2 | NOT_IMPLEMENTABLE_YET | missing typed recovery trigger/action/result record | LRW-18; LRW-19; LRW-20 | recovery family not implemented | BLOCKED | any status other than BLOCKED_WAVE_2 | metric_results[].measurement_status | REQUIRED |
| RV-OPB-05 | Operator burden | manual copy/paste burden | NOT_CURRENTLY_MEASURABLE | WAVE_2 | NOT_IMPLEMENTABLE_YET | missing typed payload-free transfer count receipt | LRW-16; LRW-19; LRW-20 | manual transfer family not implemented | BLOCKED | any status other than BLOCKED_WAVE_2 | metric_results[].measurement_status | REQUIRED |

No metric may be added, removed, renamed, or aliased. Profitability, alpha,
return, recommendation, ranking, probability, fair value, signal, size, and
order metrics are outside the registry.

## Metric-To-Stage Applicability Map

Stage-map version: `local-research-value-stage-map-v1.0`. Wave 2 identifiers in
this table are applicability declarations only and remain blocked.

| stage_id | stage_name | applicable_metric_ids | non_applicable_dimensions | required_input_artifact | required_output_artifact | instrumentation_needed | wave |
|---|---|---|---|---|---|---|---|
| LRW-01 | market discovery/input | NONE — explicit public-network/manual stage excluded from offline measurement | all dimensions | bounded operator request | finite public result | NONE; stage is not invoked | NONE |
| LRW-02 | public metadata | RV-THR-01 | operator burden; hypothesis; handoff | synthetic metadata mapping | normalized market summary | NO | WAVE_1 |
| LRW-03 | order-book input | NONE — capture/network operation excluded | all dimensions | synthetic normalized book supplied downstream | no capture output | NONE; stage is not invoked | NONE |
| LRW-04 | parsing and normalization | RV-THR-01 | operator burden; hypothesis; handoff | synthetic metadata/book mapping | typed normalized record | NO | WAVE_1 |
| LRW-05 | snapshot persistence | RV-REP-02 | operator burden; hypothesis; handoff | synthetic identity manifest | in-memory identity result | NO WRITER; identity validation only | WAVE_1 |
| LRW-06 | market catalog | RV-THR-01 | operator burden; hypothesis; handoff | normalized snapshot set | in-memory catalog view | NO | WAVE_1 |
| LRW-07 | chronological replay/inspection | RV-THR-01; RV-REP-06 | operator burden; hypothesis; handoff | fixed ordered snapshots | normalized replay order | NO | WAVE_1 |
| LRW-08 | data-quality gates | RV-REJ-04; RV-REJ-06; RV-REJ-07 | operator burden; hypothesis; handoff | seeded quality cases | issue and gate result | NO | WAVE_1 |
| LRW-09 | candidate identification | RV-THR-02; RV-THR-06; RV-REJ-01; RV-THR-03 [BLOCKED]; RV-THR-04 [BLOCKED] | operator burden except blocked declarations | fixed candidate input | validated candidate queue | Wave 1 NO; Wave 2 separate schema | WAVE_1_AND_BLOCKED_WAVE_2 |
| LRW-10 | candidate rejection | RV-THR-02; RV-THR-06; RV-REJ-01; RV-THR-03 [BLOCKED]; RV-THR-04 [BLOCKED] | operator burden except blocked declarations | fixed candidate cases | accepted/rejected records | Wave 1 NO; Wave 2 separate schema | WAVE_1_AND_BLOCKED_WAVE_2 |
| LRW-11 | context packet | RV-REP-01 | operator burden; hypothesis; handoff | validated synthetic summary | sanitized context packet | NO | WAVE_1 |
| LRW-12 | research question record | RV-HYP-01; RV-HYP-04; RV-HYP-05; RV-HYP-06; RV-HYP-07; RV-REJ-03; RV-REP-03 [ALL BLOCKED] | Wave 1 metrics | explicit synthetic planning mapping | validated question record | separate Wave 2 schema | BLOCKED_WAVE_2_ONLY |
| LRW-13 | advisory-output validation | RV-REJ-02; RV-REJ-05; RV-HYP-02; RV-HYP-03; RV-REP-04; RV-REP-05; RV-REP-07; RV-REJ-03; RV-HYP-06; RV-REP-03 [LAST THREE BLOCKED] | operator burden; handoff | synthetic response mapping | sanitized validation receipt | Wave 1 NO; Wave 2 separate schema | WAVE_1_AND_BLOCKED_WAVE_2 |
| LRW-14 | human decision | RV-REP-05; RV-HOF-01; RV-HOF-02; RV-HOF-07; RV-HOF-03; RV-HOF-05; RV-REP-03 [LAST THREE BLOCKED] | throughput except blocked intervention | reviewed synthetic lineage | validated human decision | Wave 1 NO; Wave 2 separate schema | WAVE_1_AND_BLOCKED_WAVE_2 |
| LRW-15 | follow-up research task | RV-HOF-04; RV-HOF-06; RV-HOF-07; RV-REP-03 [BLOCKED] | throughput except blocked intervention | synthetic decision/follow-up fields | validated follow-up task | Wave 1 NO; Wave 2 separate schema | WAVE_1_AND_BLOCKED_WAVE_2 |
| LRW-16 | manual export/handoff | RV-HOF-01; RV-HOF-07; RV-THR-05; RV-OPB-05; RV-REP-03 [LAST THREE BLOCKED] | hypothesis; rejection | valid synthetic handoff object | in-memory normalized export shape only | NO WRITER; Wave 2 separate schema | WAVE_1_AND_BLOCKED_WAVE_2 |
| LRW-17 | strategy-validation handoff | RV-HOF-01; RV-HOF-02; RV-HOF-04; RV-HOF-06; RV-HOF-07; RV-HOF-03; RV-HOF-05; RV-REP-03 [LAST THREE BLOCKED] | operator burden | advisory research record | contract-validation result | Wave 1 validation only; no strategy implementation | WAVE_1_AND_BLOCKED_WAVE_2 |
| LRW-18 | experiment evidence | RV-REJ-02; RV-HYP-02; RV-HYP-03; RV-REP-02; RV-REP-06; RV-THR-04; RV-OPB-01; RV-OPB-02; RV-OPB-04; RV-REP-03 [LAST FIVE BLOCKED] | none beyond declared applicability | fixed case plus precomputed safe output | normalized temporary evidence | Wave 1 future WP152; Wave 2 separate schema | WAVE_1_AND_BLOCKED_WAVE_2 |
| LRW-19 | operator runbooks | RV-THR-05; RV-OPB-01; RV-OPB-02; RV-OPB-03; RV-OPB-04; RV-OPB-05; RV-REP-03 [ALL BLOCKED] | all Wave 1 metrics | manual procedure | human procedure only | no automation; separate Wave 2 schema | BLOCKED_WAVE_2_ONLY |
| LRW-20 | audit/reproducibility trail | RV-REP-01; RV-REP-02; RV-REP-04; RV-REP-05; RV-REP-06; RV-REP-07; RV-THR-04; RV-THR-05; RV-REP-03; RV-OPB-01; RV-OPB-02; RV-OPB-03; RV-OPB-04; RV-OPB-05 [LAST EIGHT BLOCKED] | none beyond declared applicability | explicit structured records and events | temporary receipt | Wave 1 future WP152; Wave 2 separate schema | WAVE_1_AND_BLOCKED_WAVE_2 |

Manual/export/runbook stages remain manual. No paper stage is added.

## Corpus Contract

```text
Corpus ID:
local-research-workflow-value-measurement-v1
Corpus version:
1.0
Corpus posture:
SYNTHETIC_SANITIZED_OFFLINE_FIXED
Corpus case count:
14
Corpus family count:
14
```

| case_id | family | stage_ids | metric_ids | input_artifact_shape | expected_validation_state | expected_metric_events | negative_mutation_family | human_review |
|---|---|---|---|---|---|---|---|---|
| LVM-001 | market metadata parsing | LRW-02; LRW-04 | RV-THR-01; RV-REP-02 | fixed invented metadata mappings with stable IDs | VALID | count and identity coverage | missing/duplicate market ID | REQUIRED |
| LVM-002 | order-book normalization | LRW-03; LRW-04 | RV-THR-01; RV-REP-02 | fixed invented unordered price/size labels, no venue call | VALID | count and identity coverage | malformed level/order mutation | REQUIRED |
| LVM-003 | snapshot-quality failures | LRW-08 | RV-REJ-04; RV-REJ-06; RV-REJ-07 | seeded duplicate, missing, provenance, and gate cases | EXPECTED_FAILURE_DETECTED | issue, duplicate, and gate-rate events | remove/rename seeded failure | REQUIRED |
| LVM-004 | replay ordering | LRW-07 | RV-THR-01; RV-REP-06 | fixed snapshots with immutable logical sequence | VALID | count and repeatability events | reorder/equal-key mutation | REQUIRED |
| LVM-005 | candidate production/rejection | LRW-09; LRW-10 | RV-THR-02; RV-THR-06; RV-REJ-01 | fixed candidate items with allowed labels/reasons | VALID_AND_EXPECTED_REJECTIONS | candidate counts, invalid counts, reason coverage | unknown/empty label or duplicate ID | REQUIRED |
| LVM-006 | source/evidence conflict | LRW-13; LRW-14 | RV-REJ-02; RV-REJ-06; RV-HYP-02; RV-REP-07; RV-HOF-02 | invented labeled evidence with explicit conflict | VALID | evidence, conflict, ambiguity, uncertainty events | silently remove conflict/counter-evidence | REQUIRED |
| LVM-007 | unsupported claims | LRW-13 | RV-REJ-05; RV-REP-04 | invented unsupported material and expected rejection receipt | EXPECTED_FAILURE_DETECTED | rejection-rate and receipt events | accept unsupported claim | REQUIRED |
| LVM-008 | missing citations | LRW-13 | RV-REJ-02; RV-REJ-05; RV-REP-04 | invented claim with missing citation disclosure | EXPECTED_FAILURE_DETECTED | coverage, rejection, receipt events | fabricate/add unregistered citation | REQUIRED |
| LVM-009 | missing data | LRW-13; LRW-14; LRW-15 | RV-REJ-02; RV-REP-07; RV-HOF-02; RV-HOF-04 | explicit missing-data labels and follow-up need | VALID | evidence, ambiguity, uncertainty, data-need events | omit missing-data disclosure | REQUIRED |
| LVM-010 | falsification/invalidation | LRW-13; LRW-15 | RV-HYP-03; RV-REP-07; RV-HOF-06 | fixed invalidation condition and next validation step | VALID | invalidation, ambiguity, next-step events | remove invalidation or next step | REQUIRED |
| LVM-011 | human decisions/follow-ups | LRW-14; LRW-15; LRW-17 | RV-HYP-02; RV-HYP-03; RV-REP-05; RV-HOF-01; RV-HOF-04; RV-HOF-06; RV-HOF-07 | explicit acknowledged decision and bounded follow-up | VALID_REVIEW_REQUIRED | review and handoff coverage events | missing acknowledgement/authority flag | REQUIRED |
| LVM-012 | non-authority leakage | LRW-13; LRW-14; LRW-17 | RV-REJ-05; RV-REP-05; RV-HOF-01; RV-HOF-07 | invented prohibited action language for rejection | EXPECTED_FAILURE_DETECTED | rejection, review, separation, leakage events | weaken forbidden phrase or safety flag | REQUIRED |
| LVM-013 | deterministic rerun equality | LRW-18; LRW-20 | RV-REP-02; RV-REP-06 | fixed case repeated three times with normalized output | VALID | identity and equality events | mutate one normalized repeat | REQUIRED |
| LVM-014 | malformed/incomplete records | LRW-08; LRW-09; LRW-10; LRW-13; LRW-20 | RV-THR-06; RV-REJ-01; RV-REJ-04; RV-REJ-07; RV-REP-01; RV-REP-02; RV-REP-04; RV-REP-05; RV-REP-07 | bounded missing/extra/unknown-field mutations | EXPECTED_FAILURE_DETECTED | invalid, quality, identity, receipt, review, ambiguity events | fixture/source/input mutation | REQUIRED |

Every Wave 1 metric has explicit case coverage. IDs and ordering are immutable
within version 1.0. The corpus contains no real people, wallets, accounts,
orders, markets, URLs, credentials, secrets, provider/model output, trading
recommendations, absolute paths, current timestamps, or random timestamps.
WP151 creates no fixture.

## Run Contract

Run-contract version: `local-research-value-run-v1.0`.

| field | rule |
|---|---|
| run_contract_version | exact supported version |
| corpus_id | exact fixed corpus identity |
| corpus_version | exact `1.0` |
| metric_registry_version | exact registry version |
| stage_map_version | exact stage-map version |
| run_id | caller-supplied safe identifier or deterministic derivation from versions, selection, and repeat count |
| operator_run_label | bounded allowlisted label, no identity or free text |
| case_selection | explicit ordered subset of known case IDs |
| repeat_index | integer `1..3` for each selected case |
| temporary_output_mode | one allowed temporary mode |
| human_review_required | literal true |
| non_authority_notice | exact contract notice |

Invocation is explicit and single-run. Ordering is fixed; dynamic discovery is
forbidden. Version or case mismatch fails closed. No network, secrets,
provider, model, Hermes runtime, scheduler, strategy, paper, or live behavior
is allowed.

## Event Contract

Event-contract version: `local-research-value-event-v1.0`.

Allowed event types, in the only event vocabulary:

```text
RUN_STARTED
CASE_STARTED
STAGE_STARTED
STAGE_COMPLETED
VALIDATION_PASSED
VALIDATION_FAILED
OPERATOR_REVIEW_REQUIRED
OPERATOR_ACKNOWLEDGED
CORRECTION_REQUESTED
CASE_COMPLETED
CASE_FAILED
RUN_COMPLETED
RUN_FAILED
```

Required fields:

```text
event_contract_version
run_id
case_id
repeat_index
event_sequence
event_type
stage_id
metric_ids
monotonic_elapsed_ns
validation_state
error_codes
operator_action_type
input_reference
output_reference
non_authority_notice
```

`event_sequence` starts at one and is contiguous. Duration uses only monotonic
elapsed nanoseconds; no wall clock is read. References are safe logical IDs,
not paths or raw content. No username or machine ID is recorded. Invalid,
missing, duplicate, or out-of-order events fail the run. Events remain in
memory or an approved temporary mode.

## Operator Action Contract

Allowed actions:

```text
NO_ACTION
ACKNOWLEDGE
REQUEST_CORRECTION
RETRY_CASE
DEFER_CASE
ABORT_RUN
```

Required fields:

```text
action_id
run_id
case_id
stage_id
action_type
reason_code
correction_target
reviewer_acknowledgement
human_review_required
non_authority_notice
```

Reason codes and correction targets are allowlisted. Unrestricted free-form
notes and personal identity are forbidden. An action cannot approve trading,
strategy, deployment, credentials, paper/live operation, or PR merge.

## Measurement Receipt Contract

Receipt-contract version: `local-research-value-receipt-v1.0`.

Required receipt fields:

```text
receipt_contract_version
receipt_id
run_contract_version
corpus_id
corpus_version
metric_registry_version
stage_map_version
run_id
case_count
repeat_count
event_count
metric_results
hard_failures
repeatability_results
operator_action_counts
run_status
human_review_status
temporary_output_status
non_authority_notice
safety_flags
```

Each metric result has exactly:

```text
metric_id
wave
measurement_type
numerator
denominator
count
duration_ns
boolean_result
set_coverage
repeatability_result
rubric_score
applicable_case_count
excluded_case_count
measurement_status
failure_codes
```

Allowed measurement statuses:

```text
MEASURED_VALID
NOT_APPLICABLE
FAILED_VALIDATION
INSUFFICIENT_CASE_COVERAGE
BLOCKED_WAVE_2
```

All 17 Wave 2 rows must be `BLOCKED_WAVE_2` with no value field populated.
Receipts contain no profitability, expected return, recommendation, ranking,
probability, fair value, size, order, strategy promotion, model output, raw
source text, credentials, or private state.

## Deterministic Scoring And Aggregation

Count:

```text
count = number of qualifying deterministic events or records
```

Rate:

```text
rate = numerator / denominator
```

Numerators and denominators sum across applicable cases before division. A zero
denominator fails unless the registry marks the metric `NOT_APPLICABLE`.

Boolean coverage:

```text
true only when every required field/flag is present and valid
```

Set coverage:

```text
coverage = observed required labels / expected required labels
```

Set aggregation uses the union of observed labels over the fixed expected set.
A missing or empty expected set fails.

Duration:

```text
duration_ns = stage_completed.monotonic_elapsed_ns - stage_started.monotonic_elapsed_ns
```

Missing, negative, duplicated, cross-case, or out-of-order events fail.

Repeatability:

```text
PASS only when normalized deterministic outputs and metric results are equal across required repeats
```

Rubric score is allowed only with fixed versioned categories, scale,
applicability, and human review. Model judgment is never deterministic.
No Wave 1 registry row depends on model judgment.

## Repeatability Contract

```text
Required repeats per selected case:
3
```

Equality excludes run ID, receipt ID, monotonic duration, and acknowledgement ID.
Equality includes validation state, error codes, normalized output shape,
metric applicability/results, safety flags, and run status. Normalization may
sort only fields explicitly declared unordered by the schema; it may not drop,
rewrite, or infer content. Any unexplained mismatch fails the metric and run.

## Run Status Contract

```text
RUN_VALID_MEASUREMENT_COMPLETE
RUN_FAILED_INPUT_CONTRACT
RUN_FAILED_CORPUS_VERSION
RUN_FAILED_METRIC_REGISTRY
RUN_FAILED_STAGE_MAP
RUN_FAILED_EVENT_CONTRACT
RUN_FAILED_VALIDATION
RUN_FAILED_REPEATABILITY
RUN_ABORTED_BY_OPERATOR
```

A valid run requires complete selected-case execution, complete Wave 1 corpus
coverage across the run, a complete receipt, zero safety failures, complete
human review, no Wave 2 metric marked measured, and no unapproved persistence.

## Temporary Output Contract

Allowed modes:

```text
IN_MEMORY_ONLY
PYTEST_TMP_PATH_ONLY
IGNORED_LOCAL_TEMP_DIRECTORY
```

Tracked output, database/cloud/provider storage, telemetry, analytics,
permanent local reports, background upload, and user-profile output are
forbidden. Temporary cleanup is mandatory before acceptance. WP151 authorizes no writer and no output path.

## Human Review Contract

Review confirms corpus, registry, and stage-map identity; Wave separation;
safety state; failed/excluded cases; repeatability; operator actions; absence
of unsupported measured claims; absence of profitability/trading
interpretation; and temporary cleanup.

Allowed outcomes:

```text
ACCEPT_MEASUREMENT_RECEIPT_FOR_RESEARCH_MEMORY_ONLY
REJECT_RECEIPT_CONTRACT_FAILURE
REJECT_RECEIPT_COVERAGE_FAILURE
REJECT_RECEIPT_REPEATABILITY_FAILURE
REJECT_RECEIPT_SAFETY_FAILURE
DEFER_RECEIPT_PENDING_CORRECTION
```

Human review cannot approve strategy, paper/live trading, deployment,
credentials, execution, or merge.

## Safety And Non-Authority Gates

Every gate is mandatory and zero tolerance:

```text
NO_NETWORK
NO_CREDENTIAL_ACCESS
NO_PROVIDER_OR_MODEL_CALL
NO_HERMES_RUNTIME
NO_PAPER_OR_LIVE_STATE
NO_ORDER_OR_SIGNAL_CREATION
NO_PROFITABILITY_OR_RECOMMENDATION_OUTPUT
NO_RAW_PRIVATE_OR_SECRET_DATA
NO_UNAPPROVED_PERSISTENCE
NO_SCHEDULER_OR_BACKGROUND_TASK
NO_WAVE_2_FALSE_MEASUREMENT
HUMAN_REVIEW_REQUIRED
```

One failed gate fails the run.

## Negative And Mutation Matrix

| mutation_id | mutation | required_failure |
|---|---|---|
| NM-01 | missing, unknown, or renamed metric | RUN_FAILED_METRIC_REGISTRY |
| NM-02 | Wave 2 metric marked measured | RUN_FAILED_METRIC_REGISTRY plus safety failure |
| NM-03 | metric lacks stage map or corpus coverage | INSUFFICIENT_CASE_COVERAGE |
| NM-04 | unknown stage | RUN_FAILED_STAGE_MAP |
| NM-05 | duplicate case ID | RUN_FAILED_CORPUS_VERSION |
| NM-06 | wrong corpus, registry, or stage-map version | corresponding version/status failure |
| NM-07 | missing, duplicate, or out-of-order event | RUN_FAILED_EVENT_CONTRACT |
| NM-08 | negative duration | RUN_FAILED_EVENT_CONTRACT |
| NM-09 | zero denominator | FAILED_VALIDATION unless explicitly not applicable |
| NM-10 | unknown operator action | RUN_FAILED_EVENT_CONTRACT |
| NM-11 | unrestricted free-form note | RUN_FAILED_INPUT_CONTRACT |
| NM-12 | random or wall-clock dependence | RUN_FAILED_REPEATABILITY |
| NM-13 | network attempt | safety failure and RUN_FAILED_VALIDATION |
| NM-14 | credential access attempt | safety failure and RUN_FAILED_VALIDATION |
| NM-15 | provider/model output | safety failure and RUN_FAILED_VALIDATION |
| NM-16 | recommendation, signal, order, or paper/live field | safety failure and RUN_FAILED_VALIDATION |
| NM-17 | persistent output | safety failure and RUN_FAILED_VALIDATION |
| NM-18 | repeatability mismatch | RUN_FAILED_REPEATABILITY |
| NM-19 | missing human review | RUN_FAILED_VALIDATION |
| NM-20 | extra or missing receipt field | RUN_FAILED_VALIDATION |
| NM-21 | fixture, source, or input mutation | RUN_FAILED_INPUT_CONTRACT |

All mutations remain in memory or approved temporary paths.

## Blocker Resolution Map

| blocker_id | WP150 blocker | WP151 contract resolution | implementation still required | target_wp |
|---|---|---|---|---|
| RV-001 | measurement receipts | exact run/event/action/receipt identities, fields, statuses, and failures | YES | WP152 for Wave 1 |
| RV-002 | structured hypothesis | exact Wave 2 hypothesis fields and validation/negative tests defined | YES | separate future Wave 2 schema-enablement WP |
| RV-003 | deterministic derivation | every Wave 1 derivation and every Wave 2 missing derivation defined | YES | WP152 for Wave 1; separate Wave 2 schema-enablement WP |
| RV-004 | corpus/rubric coverage | fixed 14-case/14-family v1.0 contract maps every Wave 1 metric | YES | WP152 for Wave 1 fixture; separate Wave 2 coverage WP |
| RV-005 | metric-to-stage mapping | exact 20-row applicability map and blocked declarations defined | YES | WP152 consumes Wave 1 map |
| RV-006 | handoff fields | exact neutral assumptions and risk-relevance future schemas defined | YES | separate future Wave 2 schema-enablement WP |
| RV-007 | operator burden | exact timing, intervention, correction, expertise, recovery, and transfer schemas defined | YES | separate future Wave 2 schema-enablement WP |

Contract resolution is not implementation resolution. All seven blockers are contract-resolved;
all seven still require implementation work in their stated
targets. No separate schema decision remains open, although separate schema
implementation remains required.

## Implementation Readiness Decision

The registry has exactly 39 metrics and the unchanged 22/17 split; the stage
map has exactly 20 stages; every Wave 1 metric has explicit corpus coverage;
all schemas, formulas, repeatability, temporary-output, safety, human-review,
mutation, and blocker rules are complete; and WP152 has no architecture
decision left to invent.

```text
Measurement harness contract status:
COMPLETE_READY_FOR_BOUNDED_IMPLEMENTATION_WP
Initial harness metric scope:
GROUNDED_22_METRICS_ONLY
Blocked metric posture:
CONTRACT_DEFINED_IMPLEMENTATION_DEFERRED
Next phase:
BOUNDED_LOCAL_RESEARCH_VALUE_MEASUREMENT_HARNESS_IMPLEMENTATION
```

## Promotion Gates

WP152 requires separate approval, clean remote-main preflight, exact use of
the v1.0 registry/map/corpus contract, Wave 1-only implementation, temporary
output, full negative tests, complete validation, Model D evidence, and human
review. Any Wave 2 schema enablement requires a separate approved work package.
Paper, live, execution, credentials, provider/model, runtime, and scheduler
promotion remain separately forbidden.

## Explicit Deferred Capabilities

Deferred: every Wave 2 schema and corpus implementation; real fixtures beyond
the fixed synthetic contract; instrumentation; measurement execution; durable
receipts; telemetry; orchestration; scheduler; provider/model/Hermes runtime;
strategy, paper, live, execution, order, accounting, risk, reconciliation, and
deployment behavior.

## Output Surface Inventory

WP151 adds only this canonical Markdown contract, its Markdown-only focused
regression, and its stable status fragment. It updates project status,
repo-truth index, and project-status regression. It adds no source, tool,
fixture, workflow, dependency, lock, configuration, runtime, credential,
provider/model/Hermes, paper/risk/execution, scheduler, or generated-output
surface. `docs/deferred_items_log.md` is unchanged.

## Forbidden Interpretations

- Contract is not implementation.
- Measurable is not measured.
- Wave 1 excludes Wave 2.
- Future schema is not current field.
- Corpus coverage is not real-world validity.
- Deterministic validation is not factual truth.
- Research value is not profitability.
- Research output is not a signal or order.
- Temporary output is not persistent evidence.
- Human review is not trading approval.
- Readiness is not authority.
- WP151 does not implement WP152.
- No paper/live/execution authority changes.

## Future WP152 Boundary

```text
WP152 — Bounded Local Research Workflow Value Measurement Harness Implementation V1
```

WP152 may add the fixed 14-case synthetic fixture, implement a local
deterministic Wave 1 harness, event/receipt validators, exact formulas,
temporary-only execution, and focused mutation tests. It must measure only the
22 Wave 1 metrics and must use no network, credentials, provider/model, Hermes
runtime, strategy, paper, live, scheduler, or permanent output. All 17 Wave 2 metrics remain blocked
unless separately authorized. WP152 must not implement WP153 or any Wave 2 schema.

## Decision

```text
Measurement harness contract status:
COMPLETE_READY_FOR_BOUNDED_IMPLEMENTATION_WP
Measurement harness implementation:
NOT AUTHORIZED
Measurement run:
NOT AUTHORIZED
Persistent measurement output:
NOT AUTHORIZED
Paper/live/execution authority:
FORBIDDEN
WP152 requires separate approval
```

## Non-Authority Statement

WP151 is a deterministic research-measurement contract only. It creates no
fixture, harness, measurement, receipt, writer, provider call, credential
access, Hermes run, scheduler, strategy signal, paper order, live order,
execution path, capital risk, or trading authority.
