"""Deterministic in-memory Wave 1 research-value measurement harness.

The module has no import-time I/O and no network, credential, provider, model,
Hermes, paper/live, order, scheduler, database, subprocess, environment, or
writer integration. Callers supply an already-loaded fixed corpus mapping.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Any, NamedTuple

METRIC_REGISTRY_VERSION = "local-research-value-metrics-v1.0"
STAGE_MAP_VERSION = "local-research-value-stage-map-v1.0"
CORPUS_ID = "local-research-workflow-value-measurement-v1"
CORPUS_VERSION = "1.0"
CORPUS_POSTURE = "SYNTHETIC_SANITIZED_OFFLINE_FIXED"
CORPUS_CONTENT_SHA256 = "0133b3444aab0a4d045035e292cb46c675de682cee1cc8c5cb4e29fd5dfc3ced"
RUN_CONTRACT_VERSION = "local-research-value-run-v1.0"
EVENT_CONTRACT_VERSION = "local-research-value-event-v1.0"
RECEIPT_CONTRACT_VERSION = "local-research-value-receipt-v1.0"
REQUIRED_REPEATS = 3

NON_AUTHORITY_NOTICE = (
    "Research measurement only; human review is required. This output grants "
    "no strategy, paper or live, order, execution, credential, runtime, "
    "deployment, or approval authority."
)

ALLOWED_EVENT_TYPES = (
    "RUN_STARTED",
    "CASE_STARTED",
    "STAGE_STARTED",
    "STAGE_COMPLETED",
    "VALIDATION_PASSED",
    "VALIDATION_FAILED",
    "OPERATOR_REVIEW_REQUIRED",
    "OPERATOR_ACKNOWLEDGED",
    "CORRECTION_REQUESTED",
    "CASE_COMPLETED",
    "CASE_FAILED",
    "RUN_COMPLETED",
    "RUN_FAILED",
)
ALLOWED_OPERATOR_ACTIONS = (
    "NO_ACTION",
    "ACKNOWLEDGE",
    "REQUEST_CORRECTION",
    "RETRY_CASE",
    "DEFER_CASE",
    "ABORT_RUN",
)
ALLOWED_RUN_STATUSES = (
    "RUN_VALID_MEASUREMENT_COMPLETE",
    "RUN_FAILED_INPUT_CONTRACT",
    "RUN_FAILED_CORPUS_VERSION",
    "RUN_FAILED_METRIC_REGISTRY",
    "RUN_FAILED_STAGE_MAP",
    "RUN_FAILED_EVENT_CONTRACT",
    "RUN_FAILED_VALIDATION",
    "RUN_FAILED_REPEATABILITY",
    "RUN_ABORTED_BY_OPERATOR",
)
ALLOWED_MEASUREMENT_STATUSES = (
    "MEASURED_VALID",
    "NOT_APPLICABLE",
    "FAILED_VALIDATION",
    "INSUFFICIENT_CASE_COVERAGE",
    "BLOCKED_WAVE_2",
)
ALLOWED_OUTPUT_MODES = (
    "IN_MEMORY_ONLY",
    "PYTEST_TMP_PATH_ONLY",
    "IGNORED_LOCAL_TEMP_DIRECTORY",
)
ALLOWED_HUMAN_REVIEW_OUTCOMES = (
    "ACCEPT_MEASUREMENT_RECEIPT_FOR_RESEARCH_MEMORY_ONLY",
    "REJECT_RECEIPT_CONTRACT_FAILURE",
    "REJECT_RECEIPT_COVERAGE_FAILURE",
    "REJECT_RECEIPT_REPEATABILITY_FAILURE",
    "REJECT_RECEIPT_SAFETY_FAILURE",
    "DEFER_RECEIPT_PENDING_CORRECTION",
)
SAFETY_GATES = (
    "NO_NETWORK",
    "NO_CREDENTIAL_ACCESS",
    "NO_PROVIDER_OR_MODEL_CALL",
    "NO_HERMES_RUNTIME",
    "NO_PAPER_OR_LIVE_STATE",
    "NO_ORDER_OR_SIGNAL_CREATION",
    "NO_PROFITABILITY_OR_RECOMMENDATION_OUTPUT",
    "NO_RAW_PRIVATE_OR_SECRET_DATA",
    "NO_UNAPPROVED_PERSISTENCE",
    "NO_SCHEDULER_OR_BACKGROUND_TASK",
    "NO_WAVE_2_FALSE_MEASUREMENT",
    "HUMAN_REVIEW_REQUIRED",
)

REQUIRED_RUN_FIELDS = (
    "run_contract_version",
    "corpus_id",
    "corpus_version",
    "metric_registry_version",
    "stage_map_version",
    "run_id",
    "operator_run_label",
    "case_selection",
    "repeat_index",
    "temporary_output_mode",
    "human_review_required",
    "non_authority_notice",
)
REQUIRED_EVENT_FIELDS = (
    "event_contract_version",
    "run_id",
    "case_id",
    "repeat_index",
    "event_sequence",
    "event_type",
    "stage_id",
    "metric_ids",
    "monotonic_elapsed_ns",
    "validation_state",
    "error_codes",
    "operator_action_type",
    "input_reference",
    "output_reference",
    "non_authority_notice",
)
REQUIRED_ACTION_FIELDS = (
    "action_id",
    "run_id",
    "case_id",
    "stage_id",
    "action_type",
    "reason_code",
    "correction_target",
    "reviewer_acknowledgement",
    "human_review_required",
    "non_authority_notice",
)
REQUIRED_RECEIPT_FIELDS = (
    "receipt_contract_version",
    "receipt_id",
    "run_contract_version",
    "corpus_id",
    "corpus_version",
    "metric_registry_version",
    "stage_map_version",
    "run_id",
    "case_count",
    "repeat_count",
    "event_count",
    "metric_results",
    "hard_failures",
    "repeatability_results",
    "operator_action_counts",
    "run_status",
    "human_review_status",
    "temporary_output_status",
    "non_authority_notice",
    "safety_flags",
)
REQUIRED_METRIC_RESULT_FIELDS = (
    "metric_id",
    "wave",
    "measurement_type",
    "numerator",
    "denominator",
    "count",
    "duration_ns",
    "boolean_result",
    "set_coverage",
    "repeatability_result",
    "rubric_score",
    "applicable_case_count",
    "excluded_case_count",
    "measurement_status",
    "failure_codes",
)
VALIDATION_RESULT_FIELDS = ("is_valid", "run_status", "errors", "normalized")
RUN_RESULT_FIELDS = ("is_valid", "run_status", "errors", "events", "receipt")

ALLOWED_REASON_CODES = frozenset(
    {
        "NO_REASON",
        "REVIEW_COMPLETE",
        "CONTRACT_CORRECTION_REQUIRED",
        "CASE_RETRY_REQUIRED",
        "CASE_DEFERRED",
        "RUN_ABORT_REQUESTED",
    }
)
ALLOWED_CORRECTION_TARGETS = frozenset(
    {"NONE", "CASE_INPUT", "CASE_VALIDATION", "CASE_REVIEW"}
)
_FINAL_REVIEW_ACTIONS = frozenset(
    {"ACKNOWLEDGE", "REQUEST_CORRECTION", "RETRY_CASE", "DEFER_CASE"}
)
_ACTION_RULES = {
    "NO_ACTION": ("NO_REASON", frozenset({"NONE"}), False),
    "ACKNOWLEDGE": ("REVIEW_COMPLETE", frozenset({"NONE"}), True),
    "REQUEST_CORRECTION": (
        "CONTRACT_CORRECTION_REQUIRED",
        frozenset({"CASE_INPUT", "CASE_VALIDATION", "CASE_REVIEW"}),
        False,
    ),
    "RETRY_CASE": (
        "CASE_RETRY_REQUIRED",
        frozenset({"CASE_INPUT", "CASE_VALIDATION"}),
        False,
    ),
    "DEFER_CASE": ("CASE_DEFERRED", frozenset({"NONE", "CASE_REVIEW"}), False),
    "ABORT_RUN": ("RUN_ABORT_REQUESTED", frozenset({"NONE"}), False),
}
ALLOWED_OPERATOR_RUN_LABELS = frozenset(
    {"WP152_SYNTHETIC_VALIDATION", "LOCAL_CONTRACT_TEST"}
)
ALLOWED_CANDIDATE_LABELS = frozenset(
    {
        "CANDIDATE_READY_FOR_MANUAL_RESEARCH_REVIEW",
        "CANDIDATE_REJECTED_FOR_UNSAFE_OR_FORBIDDEN_CONTENT",
        "CANDIDATE_DEFERRED_PENDING_MORE_CONTEXT",
    }
)
ALLOWED_REASON_LABELS = frozenset(
    {
        "EVIDENCE_QUALITY_GAP",
        "SOURCE_CONFLICT",
        "STALE_OR_MISSING_DATA_RISK",
        "FALSIFICATION_CHECK_NEED",
    }
)


class MetricDefinition(NamedTuple):
    metric_id: str
    dimension: str
    metric: str
    wp150_state: str
    wave: str
    measurement_type: str
    exact_input_fields_or_derivation: str
    applicable_stage_ids: str
    corpus_case_ids_or_family: str
    aggregation: str
    fail_closed_condition: str
    receipt_field: str
    human_review: str


class StageDefinition(NamedTuple):
    stage_id: str
    stage_name: str
    applicable_metric_ids: str
    non_applicable_dimensions: str
    required_input_artifact: str
    required_output_artifact: str
    instrumentation_needed: str
    wave: str


_METRIC_ROWS = """
RV-THR-01|Research throughput|markets reviewed|MEASURABLE_NOT_YET_MEASURED|WAVE_1|COUNT|distinct validated `MarketSnapshotRecord.market_id` in selected bounded input|LRW-02; LRW-04; LRW-06; LRW-07|LVM-001; LVM-002; LVM-004|SUM_DISTINCT_PER_CASE_THEN_SUM|missing or invalid market ID, or unselected input counted|metric_results[].count|REQUIRED
RV-THR-02|Research throughput|candidates produced/rejected|MEASURABLE_NOT_YET_MEASURED|WAVE_1|COUNT|count `candidate_items[].candidate_id` by allowed `candidate_label`|LRW-09; LRW-10|LVM-005|SUM_COUNTS_BY_LABEL|missing ID, unknown label, or duplicate candidate counted|metric_results[].count|REQUIRED
RV-THR-03|Research throughput|time per candidate|NOT_CURRENTLY_MEASURABLE|WAVE_2|NOT_IMPLEMENTABLE_YET|missing `candidate_stage_timing` monotonic event references|LRW-09; LRW-10|candidate timing family not implemented|BLOCKED|any status other than BLOCKED_WAVE_2|metric_results[].measurement_status|REQUIRED
RV-THR-04|Research throughput|operator intervention count|NOT_CURRENTLY_MEASURABLE|WAVE_2|NOT_IMPLEMENTABLE_YET|missing typed operator intervention event sequence|LRW-12 through LRW-20|intervention family not implemented|BLOCKED|any status other than BLOCKED_WAVE_2|metric_results[].measurement_status|REQUIRED
RV-THR-05|Research throughput|manual steps|NOT_CURRENTLY_MEASURABLE|WAVE_2|NOT_IMPLEMENTABLE_YET|missing ordered manual-stage completion ledger|LRW-16; LRW-19; LRW-20|manual completion family not implemented|BLOCKED|any status other than BLOCKED_WAVE_2|metric_results[].measurement_status|REQUIRED
RV-THR-06|Research throughput|incomplete records|MEASURABLE_NOT_YET_MEASURED|WAVE_1|COUNT|count validator results where `is_valid` is false and group deterministic `errors`|LRW-09; LRW-10|LVM-005; LVM-014|SUM_COUNTS_BY_ERROR_CODE|invalid record accepted, unknown error, or double count|metric_results[].count|REQUIRED
RV-REJ-01|Candidate rejection quality|reason completeness|MEASURABLE_NOT_YET_MEASURED|WAVE_1|BOOLEAN_COVERAGE|every required `candidate_reason_labels` value is nonempty and allowlisted|LRW-09; LRW-10|LVM-005; LVM-014|ALL_APPLICABLE_CASES_TRUE|missing, empty, duplicate, or unknown reason label|metric_results[].boolean_result|REQUIRED
RV-REJ-02|Candidate rejection quality|evidence coverage|MEASURABLE_NOT_YET_MEASURED|WAVE_1|SET_COVERAGE|observed required fields/labels from `cited_source_references`, `evidence_for`, `evidence_against`, and `completion_labels`|LRW-13; LRW-18|LVM-006; LVM-008; LVM-009|UNION_OBSERVED_OVER_EXPECTED|missing citation/evidence side, unknown label, or zero expected set|metric_results[].set_coverage|REQUIRED
RV-REJ-03|Candidate rejection quality|resolution-rule clarity|NOT_CURRENTLY_MEASURABLE|WAVE_2|NOT_IMPLEMENTABLE_YET|missing versioned resolution-path labels and clarity rubric|LRW-12; LRW-13|resolution clarity family not implemented|BLOCKED|any status other than BLOCKED_WAVE_2|metric_results[].measurement_status|REQUIRED
RV-REJ-04|Candidate rejection quality|data-quality failure detection|MEASURABLE_NOT_YET_MEASURED|WAVE_1|RATE|seeded failures detected by `QualityIssue.code`, severity, and `QualityGateResult.passed` divided by seeded failures|LRW-08|LVM-003; LVM-014|SUM_NUMERATOR_OVER_SUM_DENOMINATOR|zero denominator, unknown issue, or seeded failure missed|metric_results[].numerator; metric_results[].denominator|REQUIRED
RV-REJ-05|Candidate rejection quality|unsupported-claim rejection|MEASURABLE_NOT_YET_MEASURED|WAVE_1|RATE|unsupported cases with required rejection `receipt_label` and `unsupported_claims_identified` divided by unsupported cases|LRW-13|LVM-007; LVM-008; LVM-012|SUM_NUMERATOR_OVER_SUM_DENOMINATOR|zero denominator or unsupported case accepted|metric_results[].numerator; metric_results[].denominator|REQUIRED
RV-REJ-06|Candidate rejection quality|duplicate/contradiction detection|MEASURABLE_NOT_YET_MEASURED|WAVE_1|RATE|seeded duplicate IDs and `source_conflicts` detected divided by seeded duplicates/conflicts|LRW-08; LRW-13|LVM-003; LVM-006|SUM_NUMERATOR_OVER_SUM_DENOMINATOR|zero denominator or seeded duplicate/conflict missed|metric_results[].numerator; metric_results[].denominator|REQUIRED
RV-REJ-07|Candidate rejection quality|deterministic-gate failure rate|MEASURABLE_NOT_YET_MEASURED|WAVE_1|RATE|failed `QualityGateResult.passed` count divided by all applicable quality-gate results|LRW-08|LVM-003; LVM-014|SUM_NUMERATOR_OVER_SUM_DENOMINATOR|zero denominator or pass/fail inconsistent with error counts|metric_results[].numerator; metric_results[].denominator|REQUIRED
RV-HYP-01|Hypothesis quality|falsifiable statement|NOT_CURRENTLY_MEASURABLE|WAVE_2|NOT_IMPLEMENTABLE_YET|missing structured falsifiable statement and refutation condition|LRW-12|hypothesis structure family not implemented|BLOCKED|any status other than BLOCKED_WAVE_2|metric_results[].measurement_status|REQUIRED
RV-HYP-02|Hypothesis quality|supporting and counter-evidence|MEASURABLE_NOT_YET_MEASURED|WAVE_1|BOOLEAN_COVERAGE|nonempty `evidence_for` and `evidence_against` plus both required completion labels|LRW-13; LRW-18|LVM-006; LVM-011|ALL_APPLICABLE_CASES_TRUE|either evidence side or label missing|metric_results[].boolean_result|REQUIRED
RV-HYP-03|Hypothesis quality|invalidation condition|MEASURABLE_NOT_YET_MEASURED|WAVE_1|BOOLEAN_COVERAGE|validated nonempty `what_would_change_the_conclusion` sequence|LRW-13; LRW-18|LVM-010; LVM-011|ALL_APPLICABLE_CASES_TRUE|empty, missing, or invalid sequence|metric_results[].boolean_result|REQUIRED
RV-HYP-04|Hypothesis quality|expected mechanism|NOT_CURRENTLY_MEASURABLE|WAVE_2|NOT_IMPLEMENTABLE_YET|missing structured mechanism inputs, relationship, and consequence|LRW-12|mechanism family not implemented|BLOCKED|any status other than BLOCKED_WAVE_2|metric_results[].measurement_status|REQUIRED
RV-HYP-05|Hypothesis quality|horizon|NOT_CURRENTLY_MEASURABLE|WAVE_2|NOT_IMPLEMENTABLE_YET|missing bounded horizon unit and ordered bounds|LRW-12|horizon family not implemented|BLOCKED|any status other than BLOCKED_WAVE_2|metric_results[].measurement_status|REQUIRED
RV-HYP-06|Hypothesis quality|resolution path|NOT_CURRENTLY_MEASURABLE|WAVE_2|NOT_IMPLEMENTABLE_YET|missing structured source hierarchy, rule, conflict, and fallback|LRW-12; LRW-13|resolution path family not implemented|BLOCKED|any status other than BLOCKED_WAVE_2|metric_results[].measurement_status|REQUIRED
RV-HYP-07|Hypothesis quality|measurable test plan|NOT_CURRENTLY_MEASURABLE|WAVE_2|NOT_IMPLEMENTABLE_YET|missing typed input, outcome, threshold, horizon, and invalidation|LRW-12|test-plan family not implemented|BLOCKED|any status other than BLOCKED_WAVE_2|metric_results[].measurement_status|REQUIRED
RV-REP-01|Reproducibility|exact inputs|MEASURABLE_NOT_YET_MEASURED|WAVE_1|BOOLEAN_COVERAGE|exact required embedded records and strict keys in manual session package|LRW-11; LRW-20|LVM-014|ALL_APPLICABLE_CASES_TRUE|missing, extra, mutated, or unlinked record|metric_results[].boolean_result|REQUIRED
RV-REP-02|Reproducibility|snapshot/fixture identity|MEASURABLE_NOT_YET_MEASURED|WAVE_1|BOOLEAN_COVERAGE|exact corpus ID/version, registry/stage versions, and ordered case IDs|LRW-05; LRW-18; LRW-20|LVM-001; LVM-002; LVM-013; LVM-014|ALL_APPLICABLE_CASES_TRUE|identity/version/order mismatch|metric_results[].boolean_result|REQUIRED
RV-REP-03|Reproducibility|schema/version|NOT_CURRENTLY_MEASURABLE|WAVE_2|NOT_IMPLEMENTABLE_YET|missing workflow-wide record schema version manifest|LRW-01 through LRW-20|schema compatibility family not implemented|BLOCKED|any status other than BLOCKED_WAVE_2|metric_results[].measurement_status|REQUIRED
RV-REP-04|Reproducibility|validation receipt|MEASURABLE_NOT_YET_MEASURED|WAVE_1|BOOLEAN_COVERAGE|valid `receipt_id`, source references, `receipt_label`, review fields, and safety flags|LRW-13; LRW-20|LVM-007; LVM-008; LVM-014|ALL_APPLICABLE_CASES_TRUE|missing/invalid receipt or unsafe flag|metric_results[].boolean_result|REQUIRED
RV-REP-05|Reproducibility|human review|MEASURABLE_NOT_YET_MEASURED|WAVE_1|BOOLEAN_COVERAGE|valid `reviewer_acknowledgement` and true `human_review_required`|LRW-13; LRW-14; LRW-20|LVM-011; LVM-012; LVM-014|ALL_APPLICABLE_CASES_TRUE|acknowledgement absent or review flag false|metric_results[].boolean_result|REQUIRED
RV-REP-06|Reproducibility|rerun consistency|MEASURABLE_NOT_YET_MEASURED|WAVE_1|REPEATABILITY_EQUALITY|normalized deterministic outputs and metric results equal across three repeats|LRW-07; LRW-18; LRW-20|LVM-004; LVM-013|ALL_SELECTED_CASES_PASS|any unexplained normalized mismatch|metric_results[].repeatability_result|REQUIRED
RV-REP-07|Reproducibility|ambiguity record|MEASURABLE_NOT_YET_MEASURED|WAVE_1|BOOLEAN_COVERAGE|required `source_conflicts`, `uncertainties`, `known_missing_data`, and `limitations` present and valid|LRW-13; LRW-20|LVM-006; LVM-009; LVM-010; LVM-014|ALL_APPLICABLE_CASES_TRUE|any required ambiguity field missing|metric_results[].boolean_result|REQUIRED
RV-HOF-01|Strategy-validation handoff quality|research conclusion separated from action|MEASURABLE_NOT_YET_MEASURED|WAVE_1|BOOLEAN_COVERAGE|required non-authority notice, three safety flags true, forbidden scan empty|LRW-14; LRW-16; LRW-17|LVM-011; LVM-012|ALL_APPLICABLE_CASES_TRUE|action language or false/missing authority flag|metric_results[].boolean_result|REQUIRED
RV-HOF-02|Strategy-validation handoff quality|uncertainty represented|MEASURABLE_NOT_YET_MEASURED|WAVE_1|BOOLEAN_COVERAGE|valid `uncertainty_notes`, `limitations`, and `unresolved_questions`|LRW-14; LRW-17|LVM-006; LVM-009|ALL_APPLICABLE_CASES_TRUE|any required uncertainty field missing|metric_results[].boolean_result|REQUIRED
RV-HOF-03|Strategy-validation handoff quality|assumptions explicit|NOT_CURRENTLY_MEASURABLE|WAVE_2|NOT_IMPLEMENTABLE_YET|missing structured neutral assumptions sequence|LRW-14; LRW-17|assumptions family not implemented|BLOCKED|any status other than BLOCKED_WAVE_2|metric_results[].measurement_status|REQUIRED
RV-HOF-04|Strategy-validation handoff quality|data needs explicit|MEASURABLE_NOT_YET_MEASURED|WAVE_1|BOOLEAN_COVERAGE|valid nonempty missing-data, evidence, source-revisit, and uncertainty-reduction fields|LRW-15; LRW-17|LVM-009; LVM-011|ALL_APPLICABLE_CASES_TRUE|any required data-need field missing|metric_results[].boolean_result|REQUIRED
RV-HOF-05|Strategy-validation handoff quality|risk implications explicit|NOT_CURRENTLY_MEASURABLE|WAVE_2|NOT_IMPLEMENTABLE_YET|missing neutral risk-relevance category, uncertainty, and validation consequence|LRW-14; LRW-17|risk-relevance family not implemented|BLOCKED|any status other than BLOCKED_WAVE_2|metric_results[].measurement_status|REQUIRED
RV-HOF-06|Strategy-validation handoff quality|next validation step explicit|MEASURABLE_NOT_YET_MEASURED|WAVE_1|BOOLEAN_COVERAGE|valid `falsification_check_to_perform`, `blocking_reason`, and `next_manual_step`|LRW-15; LRW-17|LVM-010; LVM-011|ALL_APPLICABLE_CASES_TRUE|any required next-step field missing|metric_results[].boolean_result|REQUIRED
RV-HOF-07|Strategy-validation handoff quality|no execution authority leakage|MEASURABLE_NOT_YET_MEASURED|WAVE_1|BOOLEAN_COVERAGE|recursive forbidden scan empty and all three non-authority flags true|LRW-14; LRW-15; LRW-16; LRW-17|LVM-011; LVM-012|ALL_APPLICABLE_CASES_TRUE|any forbidden finding or false/missing flag|metric_results[].boolean_result|REQUIRED
RV-OPB-01|Operator burden|setup/run/review time|NOT_CURRENTLY_MEASURABLE|WAVE_2|NOT_IMPLEMENTABLE_YET|missing operator-phase monotonic event references|LRW-18; LRW-19; LRW-20|operator timing family not implemented|BLOCKED|any status other than BLOCKED_WAVE_2|metric_results[].measurement_status|REQUIRED
RV-OPB-02|Operator burden|correction loops|NOT_CURRENTLY_MEASURABLE|WAVE_2|NOT_IMPLEMENTABLE_YET|missing linked correction-loop sequence|LRW-18; LRW-19; LRW-20|correction loop family not implemented|BLOCKED|any status other than BLOCKED_WAVE_2|metric_results[].measurement_status|REQUIRED
RV-OPB-03|Operator burden|expertise|NOT_CURRENTLY_MEASURABLE|WAVE_2|NOT_IMPLEMENTABLE_YET|missing versioned anonymized expertise category|LRW-19; LRW-20|expertise family not implemented|BLOCKED|any status other than BLOCKED_WAVE_2|metric_results[].measurement_status|REQUIRED
RV-OPB-04|Operator burden|recovery steps|NOT_CURRENTLY_MEASURABLE|WAVE_2|NOT_IMPLEMENTABLE_YET|missing typed recovery trigger/action/result record|LRW-18; LRW-19; LRW-20|recovery family not implemented|BLOCKED|any status other than BLOCKED_WAVE_2|metric_results[].measurement_status|REQUIRED
RV-OPB-05|Operator burden|manual copy/paste burden|NOT_CURRENTLY_MEASURABLE|WAVE_2|NOT_IMPLEMENTABLE_YET|missing typed payload-free transfer count receipt|LRW-16; LRW-19; LRW-20|manual transfer family not implemented|BLOCKED|any status other than BLOCKED_WAVE_2|metric_results[].measurement_status|REQUIRED
""".strip()

METRIC_REGISTRY = tuple(
    MetricDefinition(*row.split("|")) for row in _METRIC_ROWS.splitlines()
)

_STAGE_ROWS = """
LRW-01|market discovery/input|NONE — explicit public-network/manual stage excluded from offline measurement|all dimensions|bounded operator request|finite public result|NONE; stage is not invoked|NONE
LRW-02|public metadata|RV-THR-01|operator burden; hypothesis; handoff|synthetic metadata mapping|normalized market summary|NO|WAVE_1
LRW-03|order-book input|NONE — capture/network operation excluded|all dimensions|synthetic normalized book supplied downstream|no capture output|NONE; stage is not invoked|NONE
LRW-04|parsing and normalization|RV-THR-01|operator burden; hypothesis; handoff|synthetic metadata/book mapping|typed normalized record|NO|WAVE_1
LRW-05|snapshot persistence|RV-REP-02|operator burden; hypothesis; handoff|synthetic identity manifest|in-memory identity result|NO WRITER; identity validation only|WAVE_1
LRW-06|market catalog|RV-THR-01|operator burden; hypothesis; handoff|normalized snapshot set|in-memory catalog view|NO|WAVE_1
LRW-07|chronological replay/inspection|RV-THR-01; RV-REP-06|operator burden; hypothesis; handoff|fixed ordered snapshots|normalized replay order|NO|WAVE_1
LRW-08|data-quality gates|RV-REJ-04; RV-REJ-06; RV-REJ-07|operator burden; hypothesis; handoff|seeded quality cases|issue and gate result|NO|WAVE_1
LRW-09|candidate identification|RV-THR-02; RV-THR-06; RV-REJ-01; RV-THR-03 [BLOCKED]; RV-THR-04 [BLOCKED]|operator burden except blocked declarations|fixed candidate input|validated candidate queue|Wave 1 NO; Wave 2 separate schema|WAVE_1_AND_BLOCKED_WAVE_2
LRW-10|candidate rejection|RV-THR-02; RV-THR-06; RV-REJ-01; RV-THR-03 [BLOCKED]; RV-THR-04 [BLOCKED]|operator burden except blocked declarations|fixed candidate cases|accepted/rejected records|Wave 1 NO; Wave 2 separate schema|WAVE_1_AND_BLOCKED_WAVE_2
LRW-11|context packet|RV-REP-01|operator burden; hypothesis; handoff|validated synthetic summary|sanitized context packet|NO|WAVE_1
LRW-12|research question record|RV-HYP-01; RV-HYP-04; RV-HYP-05; RV-HYP-06; RV-HYP-07; RV-REJ-03; RV-REP-03 [ALL BLOCKED]|Wave 1 metrics|explicit synthetic planning mapping|validated question record|separate Wave 2 schema|BLOCKED_WAVE_2_ONLY
LRW-13|advisory-output validation|RV-REJ-02; RV-REJ-05; RV-HYP-02; RV-HYP-03; RV-REP-04; RV-REP-05; RV-REP-07; RV-REJ-03; RV-HYP-06; RV-REP-03 [LAST THREE BLOCKED]|operator burden; handoff|synthetic response mapping|sanitized validation receipt|Wave 1 NO; Wave 2 separate schema|WAVE_1_AND_BLOCKED_WAVE_2
LRW-14|human decision|RV-REP-05; RV-HOF-01; RV-HOF-02; RV-HOF-07; RV-HOF-03; RV-HOF-05; RV-REP-03 [LAST THREE BLOCKED]|throughput except blocked intervention|reviewed synthetic lineage|validated human decision|Wave 1 NO; Wave 2 separate schema|WAVE_1_AND_BLOCKED_WAVE_2
LRW-15|follow-up research task|RV-HOF-04; RV-HOF-06; RV-HOF-07; RV-REP-03 [BLOCKED]|throughput except blocked intervention|synthetic decision/follow-up fields|validated follow-up task|Wave 1 NO; Wave 2 separate schema|WAVE_1_AND_BLOCKED_WAVE_2
LRW-16|manual export/handoff|RV-HOF-01; RV-HOF-07; RV-THR-05; RV-OPB-05; RV-REP-03 [LAST THREE BLOCKED]|hypothesis; rejection|valid synthetic handoff object|in-memory normalized export shape only|NO WRITER; Wave 2 separate schema|WAVE_1_AND_BLOCKED_WAVE_2
LRW-17|strategy-validation handoff|RV-HOF-01; RV-HOF-02; RV-HOF-04; RV-HOF-06; RV-HOF-07; RV-HOF-03; RV-HOF-05; RV-REP-03 [LAST THREE BLOCKED]|operator burden|advisory research record|contract-validation result|Wave 1 validation only; no strategy implementation|WAVE_1_AND_BLOCKED_WAVE_2
LRW-18|experiment evidence|RV-REJ-02; RV-HYP-02; RV-HYP-03; RV-REP-02; RV-REP-06; RV-THR-04; RV-OPB-01; RV-OPB-02; RV-OPB-04; RV-REP-03 [LAST FIVE BLOCKED]|none beyond declared applicability|fixed case plus precomputed safe output|normalized temporary evidence|Wave 1 future WP152; Wave 2 separate schema|WAVE_1_AND_BLOCKED_WAVE_2
LRW-19|operator runbooks|RV-THR-05; RV-OPB-01; RV-OPB-02; RV-OPB-03; RV-OPB-04; RV-OPB-05; RV-REP-03 [ALL BLOCKED]|all Wave 1 metrics|manual procedure|human procedure only|no automation; separate Wave 2 schema|BLOCKED_WAVE_2_ONLY
LRW-20|audit/reproducibility trail|RV-REP-01; RV-REP-02; RV-REP-04; RV-REP-05; RV-REP-06; RV-REP-07; RV-THR-04; RV-THR-05; RV-REP-03; RV-OPB-01; RV-OPB-02; RV-OPB-03; RV-OPB-04; RV-OPB-05 [LAST EIGHT BLOCKED]|none beyond declared applicability|explicit structured records and events|temporary receipt|Wave 1 future WP152; Wave 2 separate schema|WAVE_1_AND_BLOCKED_WAVE_2
""".strip()

STAGE_MAP = tuple(StageDefinition(*row.split("|")) for row in _STAGE_ROWS.splitlines())

_METRIC_BY_ID = {record.metric_id: record for record in METRIC_REGISTRY}
_STAGE_BY_ID = {record.stage_id: record for record in STAGE_MAP}
_WAVE_1_IDS = tuple(
    record.metric_id for record in METRIC_REGISTRY if record.wave == "WAVE_1"
)
_WAVE_2_IDS = tuple(
    record.metric_id for record in METRIC_REGISTRY if record.wave == "WAVE_2"
)
_CASE_IDS = tuple(f"LVM-{index:03d}" for index in range(1, 15))
_EXPECTED_CASE_MAP = {
    "LVM-001": (("LRW-02", "LRW-04"), ("RV-THR-01", "RV-REP-02")),
    "LVM-002": (("LRW-03", "LRW-04"), ("RV-THR-01", "RV-REP-02")),
    "LVM-003": (("LRW-08",), ("RV-REJ-04", "RV-REJ-06", "RV-REJ-07")),
    "LVM-004": (("LRW-07",), ("RV-THR-01", "RV-REP-06")),
    "LVM-005": (("LRW-09", "LRW-10"), ("RV-THR-02", "RV-THR-06", "RV-REJ-01")),
    "LVM-006": (
        ("LRW-13", "LRW-14"),
        ("RV-REJ-02", "RV-REJ-06", "RV-HYP-02", "RV-REP-07", "RV-HOF-02"),
    ),
    "LVM-007": (("LRW-13",), ("RV-REJ-05", "RV-REP-04")),
    "LVM-008": (("LRW-13",), ("RV-REJ-02", "RV-REJ-05", "RV-REP-04")),
    "LVM-009": (
        ("LRW-13", "LRW-14", "LRW-15"),
        ("RV-REJ-02", "RV-REP-07", "RV-HOF-02", "RV-HOF-04"),
    ),
    "LVM-010": (
        ("LRW-13", "LRW-15"),
        ("RV-HYP-03", "RV-REP-07", "RV-HOF-06"),
    ),
    "LVM-011": (
        ("LRW-14", "LRW-15", "LRW-17"),
        (
            "RV-HYP-02",
            "RV-HYP-03",
            "RV-REP-05",
            "RV-HOF-01",
            "RV-HOF-04",
            "RV-HOF-06",
            "RV-HOF-07",
        ),
    ),
    "LVM-012": (
        ("LRW-13", "LRW-14", "LRW-17"),
        ("RV-REJ-05", "RV-REP-05", "RV-HOF-01", "RV-HOF-07"),
    ),
    "LVM-013": (("LRW-18", "LRW-20"), ("RV-REP-02", "RV-REP-06")),
    "LVM-014": (
        ("LRW-08", "LRW-09", "LRW-10", "LRW-13", "LRW-20"),
        (
            "RV-THR-06",
            "RV-REJ-01",
            "RV-REJ-04",
            "RV-REJ-07",
            "RV-REP-01",
            "RV-REP-02",
            "RV-REP-04",
            "RV-REP-05",
            "RV-REP-07",
        ),
    ),
}
_EXPECTED_CASE_METADATA = {
    "LVM-001": (
        "market metadata parsing",
        "fixed invented metadata mappings with stable IDs",
        "VALID",
        "count and identity coverage",
        "missing/duplicate market ID",
    ),
    "LVM-002": (
        "order-book normalization",
        "fixed invented unordered price/size labels, no venue call",
        "VALID",
        "count and identity coverage",
        "malformed level/order mutation",
    ),
    "LVM-003": (
        "snapshot-quality failures",
        "seeded duplicate, missing, provenance, and gate cases",
        "EXPECTED_FAILURE_DETECTED",
        "issue, duplicate, and gate-rate events",
        "remove/rename seeded failure",
    ),
    "LVM-004": (
        "replay ordering",
        "fixed snapshots with immutable logical sequence",
        "VALID",
        "count and repeatability events",
        "reorder/equal-key mutation",
    ),
    "LVM-005": (
        "candidate production/rejection",
        "fixed candidate items with allowed labels/reasons",
        "VALID_AND_EXPECTED_REJECTIONS",
        "candidate counts, invalid counts, reason coverage",
        "unknown/empty label or duplicate ID",
    ),
    "LVM-006": (
        "source/evidence conflict",
        "invented labeled evidence with explicit conflict",
        "VALID",
        "evidence, conflict, ambiguity, uncertainty events",
        "silently remove conflict/counter-evidence",
    ),
    "LVM-007": (
        "unsupported claims",
        "invented unsupported material and expected rejection receipt",
        "EXPECTED_FAILURE_DETECTED",
        "rejection-rate and receipt events",
        "accept unsupported claim",
    ),
    "LVM-008": (
        "missing citations",
        "invented claim with missing citation disclosure",
        "EXPECTED_FAILURE_DETECTED",
        "coverage, rejection, receipt events",
        "fabricate/add unregistered citation",
    ),
    "LVM-009": (
        "missing data",
        "explicit missing-data labels and follow-up need",
        "VALID",
        "evidence, ambiguity, uncertainty, data-need events",
        "omit missing-data disclosure",
    ),
    "LVM-010": (
        "falsification/invalidation",
        "fixed invalidation condition and next validation step",
        "VALID",
        "invalidation, ambiguity, next-step events",
        "remove invalidation or next step",
    ),
    "LVM-011": (
        "human decisions/follow-ups",
        "explicit acknowledged decision and bounded follow-up",
        "VALID_REVIEW_REQUIRED",
        "review and handoff coverage events",
        "missing acknowledgement/authority flag",
    ),
    "LVM-012": (
        "non-authority leakage",
        "invented prohibited action language for rejection",
        "EXPECTED_FAILURE_DETECTED",
        "rejection, review, separation, leakage events",
        "weaken forbidden phrase or safety flag",
    ),
    "LVM-013": (
        "deterministic rerun equality",
        "fixed case repeated three times with normalized output",
        "VALID",
        "identity and equality events",
        "mutate one normalized repeat",
    ),
    "LVM-014": (
        "malformed/incomplete records",
        "bounded missing/extra/unknown-field mutations",
        "EXPECTED_FAILURE_DETECTED",
        "invalid, quality, identity, receipt, review, ambiguity events",
        "fixture/source/input mutation",
    ),
}
_FIXED_CORPUS_VALIDATION_STATES = tuple(
    dict.fromkeys(metadata[2] for metadata in _EXPECTED_CASE_METADATA.values())
)
_EVENT_REVIEW_STATES = (
    "NOT_APPLICABLE",
    "REVIEW_REQUIRED",
    "REVIEW_COMPLETE",
)
ALLOWED_EVENT_VALIDATION_STATES = tuple(
    dict.fromkeys(
        _FIXED_CORPUS_VALIDATION_STATES
        + _EVENT_REVIEW_STATES
        + ALLOWED_RUN_STATUSES
        + ALLOWED_HUMAN_REVIEW_OUTCOMES
    )
)
ALLOWED_EVENT_ERROR_CODES = (
    "ACTION_DISPOSITION_DEFERRED",
    "BLOCKED_WAVE_2",
    "METRIC_DERIVATION_FAILED",
    "MISSING_REQUIRED_CASE_COVERAGE",
    "RECEIPT_CONTRACT_FAILURE",
    "REPEATABILITY_MISMATCH",
    "SAFETY_GATE_FAILURE",
)
ALLOWED_METRIC_FAILURE_CODES = (
    "BLOCKED_WAVE_2",
    "METRIC_DERIVATION_FAILED",
    "MISSING_REQUIRED_CASE_COVERAGE",
)
ALLOWED_RECEIPT_HARD_FAILURE_CODES = (
    "DEFER_RECEIPT_PENDING_CORRECTION",
    "MISSING_REQUIRED_CASE_COVERAGE",
    "RECEIPT_CONTRACT_FAILURE",
    "REPEATABILITY_MISMATCH",
    "SAFETY_GATE_FAILURE",
)
_ID_PATTERN = re.compile(r"^[A-Z0-9][A-Z0-9._-]{0,79}$")
_CASE_PATTERN = re.compile(r"LVM-\d{3}")
_ABSOLUTE_PATH_PATTERN = re.compile(r"^(?:[A-Za-z]:[\\/]|/[^/])")
_TIMESTAMP_PATTERN = re.compile(r"\b\d{4}-\d{2}-\d{2}T\d{2}:\d{2}")
_UUID_PATTERN = re.compile(
    r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-"
    r"[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}\b"
)
_SECRET_PATTERN = re.compile(
    r"(?i)(api[_ -]?key|private[_ -]?key|mnemonic|passphrase|"
    r"bearer\s+[a-z0-9]|sk-[a-z0-9]{8,}|[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,})"
)
_SAFE_EXACT_TEXT = frozenset(
    {
        NON_AUTHORITY_NOTICE,
        *SAFETY_GATES,
        *ALLOWED_HUMAN_REVIEW_OUTCOMES,
    }
)
_FORBIDDEN_CONTENT_BY_GATE = (
    (
        "SAFETY_GATE_NO_NETWORK",
        (
            "http://",
            "https://",
            "www.",
            "network request",
            "endpoint response",
        ),
    ),
    (
        "SAFETY_GATE_NO_PROVIDER_OR_MODEL_CALL",
        (
            "provider output",
            "provider response",
            "model output",
            "model response",
        ),
    ),
    (
        "SAFETY_GATE_NO_HERMES_RUNTIME",
        (
            "hermes runtime",
            "hermes command",
        ),
    ),
    (
        "SAFETY_GATE_NO_SCHEDULER_OR_BACKGROUND_TASK",
        (
            "background task",
            "background worker",
            "scheduler",
            "scheduled job",
        ),
    ),
    (
        "SAFETY_GATE_NO_UNAPPROVED_PERSISTENCE",
        (
            "database writer",
            "persistent report",
            "persist report",
            "write database",
        ),
    ),
    (
        "SAFETY_GATE_NO_PAPER_OR_LIVE_STATE",
        (
            "account state",
            "account balance",
            "wallet address",
            "wallet balance",
            "paper trading candidate",
            "paper state",
            "live state",
            "paper ready",
            "live ready",
            "paper trade",
            "live trade",
        ),
    ),
    (
        "SAFETY_GATE_NO_ORDER_OR_SIGNAL_CREATION",
        (
            "order payload",
            "order creation",
            "create order",
            "place order",
            "submit order",
            "execute order",
            "strategy signal",
            "trade signal",
            "signal creation",
            "approve strategy",
            "promote strategy",
        ),
    ),
    (
        "SAFETY_GATE_NO_PROFITABILITY_OR_RECOMMENDATION_OUTPUT",
        (
            "buy recommendation",
            "sell recommendation",
            "buy now",
            "sell now",
            "trade ready",
            "position size",
            "position sizing",
            "profit target",
            "expected return",
            "take profit",
            "stop loss",
        ),
    ),
    (
        "SAFETY_GATE_NO_RAW_PRIVATE_OR_SECRET_DATA",
        (
            "username",
            "user profile",
            "user id",
            "user identity",
            "real person",
            "private identity",
        ),
    ),
)


def _validation(
    is_valid: bool,
    run_status: str,
    errors: Sequence[str] = (),
    normalized: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "is_valid": is_valid,
        "run_status": run_status,
        "errors": tuple(errors),
        "normalized": copy.deepcopy(dict(normalized or {})),
    }


def _run_failure(run_status: str, *errors: str) -> dict[str, Any]:
    return {
        "is_valid": False,
        "run_status": run_status,
        "errors": tuple(errors),
        "events": (),
        "receipt": {},
    }


def _safe_identifier(value: object) -> bool:
    return (
        isinstance(value, str)
        and bool(_ID_PATTERN.fullmatch(value))
        and not _UUID_PATTERN.search(value)
        and not _SECRET_PATTERN.search(value)
    )


def _safe_reference(value: object) -> bool:
    return (
        _safe_identifier(value)
        and "/" not in str(value)
        and "\\" not in str(value)
        and ":" not in str(value)
    )


def _recursive_strings(value: object, depth: int = 0) -> tuple[str, ...]:
    if depth > 20:
        return ("UNSUPPORTED_NESTING_DEPTH",)
    if isinstance(value, Mapping):
        found: list[str] = []
        for key, child in value.items():
            found.append(str(key))
            found.extend(_recursive_strings(child, depth + 1))
        return tuple(found)
    if isinstance(value, (list, tuple)):
        found = []
        for child in value:
            found.extend(_recursive_strings(child, depth + 1))
        return tuple(found)
    return (value,) if isinstance(value, str) else ()


def _safety_error(value: object) -> str | None:
    for text in _recursive_strings(value):
        if text in _SAFE_EXACT_TEXT:
            continue
        normalized = " ".join(
            text.lower().replace("_", " ").replace("-", " ").split()
        )
        if (
            _SECRET_PATTERN.search(text)
            or _ABSOLUTE_PATH_PATTERN.search(text)
            or _TIMESTAMP_PATTERN.search(text)
            or _UUID_PATTERN.search(text)
        ):
            return "SAFETY_GATE_NO_RAW_PRIVATE_OR_SECRET_DATA"
        for gate_error, phrases in _FORBIDDEN_CONTENT_BY_GATE:
            if any(phrase in normalized for phrase in phrases):
                return gate_error
    return None


def validate_run_request(request: object) -> dict[str, Any]:
    """Validate the exact run contract and return a neutral no-echo result."""
    if not isinstance(request, Mapping):
        return _validation(False, "RUN_FAILED_INPUT_CONTRACT", ("UNSUPPORTED_INPUT_SHAPE",))
    if tuple(request.keys()) != REQUIRED_RUN_FIELDS:
        return _validation(False, "RUN_FAILED_INPUT_CONTRACT", ("RUN_FIELDS_MISMATCH",))
    if request["run_contract_version"] != RUN_CONTRACT_VERSION:
        return _validation(False, "RUN_FAILED_INPUT_CONTRACT", ("RUN_VERSION_MISMATCH",))
    if request["corpus_id"] != CORPUS_ID:
        return _validation(False, "RUN_FAILED_CORPUS_VERSION", ("CORPUS_ID_MISMATCH",))
    if request["corpus_version"] != CORPUS_VERSION:
        return _validation(False, "RUN_FAILED_CORPUS_VERSION", ("CORPUS_VERSION_MISMATCH",))
    if request["metric_registry_version"] != METRIC_REGISTRY_VERSION:
        return _validation(
            False, "RUN_FAILED_METRIC_REGISTRY", ("METRIC_REGISTRY_VERSION_MISMATCH",)
        )
    if request["stage_map_version"] != STAGE_MAP_VERSION:
        return _validation(False, "RUN_FAILED_STAGE_MAP", ("STAGE_MAP_VERSION_MISMATCH",))
    if not _safe_identifier(request["run_id"]):
        return _validation(False, "RUN_FAILED_INPUT_CONTRACT", ("INVALID_RUN_ID",))
    if request["operator_run_label"] not in ALLOWED_OPERATOR_RUN_LABELS:
        return _validation(False, "RUN_FAILED_INPUT_CONTRACT", ("INVALID_RUN_LABEL",))
    selection = request["case_selection"]
    if (
        not isinstance(selection, (list, tuple))
        or not selection
        or any(case_id not in _CASE_IDS for case_id in selection)
        or len(set(selection)) != len(selection)
        or tuple(selection) != tuple(case_id for case_id in _CASE_IDS if case_id in selection)
    ):
        return _validation(False, "RUN_FAILED_INPUT_CONTRACT", ("INVALID_CASE_SELECTION",))
    if request["repeat_index"] != REQUIRED_REPEATS:
        return _validation(False, "RUN_FAILED_INPUT_CONTRACT", ("REPEAT_COUNT_MUST_EQUAL_THREE",))
    if request["temporary_output_mode"] not in ALLOWED_OUTPUT_MODES:
        return _validation(False, "RUN_FAILED_INPUT_CONTRACT", ("INVALID_OUTPUT_MODE",))
    if request["human_review_required"] is not True:
        return _validation(False, "RUN_FAILED_VALIDATION", ("HUMAN_REVIEW_REQUIRED",))
    if request["non_authority_notice"] != NON_AUTHORITY_NOTICE:
        return _validation(False, "RUN_FAILED_INPUT_CONTRACT", ("NOTICE_MISMATCH",))
    normalized = {field: copy.deepcopy(request[field]) for field in REQUIRED_RUN_FIELDS}
    normalized["case_selection"] = tuple(normalized["case_selection"])
    return _validation(True, "RUN_VALID_MEASUREMENT_COMPLETE", normalized=normalized)


_CORPUS_ROOT_FIELDS = (
    "corpus_id",
    "corpus_version",
    "corpus_posture",
    "metric_registry_version",
    "stage_map_version",
    "cases",
)
_CORPUS_CASE_FIELDS = (
    "case_id",
    "family",
    "stage_ids",
    "metric_ids",
    "input_artifact_shape",
    "expected_validation_state",
    "expected_metric_events",
    "negative_mutation_family",
    "human_review",
    "observations",
)
_OBSERVATION_FIELDS = frozenset(
    {
        "market_ids",
        "candidate_items",
        "invalid_records",
        "cited_source_references",
        "evidence_for",
        "evidence_against",
        "completion_labels",
        "quality_results",
        "unsupported_case",
        "unsupported_claims_identified",
        "receipt_label",
        "seeded_duplicate_or_conflict_count",
        "detected_duplicate_or_conflict_count",
        "what_would_change_the_conclusion",
        "exact_input_contract_validated",
        "identity_validated",
        "validation_receipt_valid",
        "reviewer_acknowledgement",
        "human_review_required",
        "source_conflicts",
        "uncertainties",
        "known_missing_data",
        "limitations",
        "non_authority_notice_valid",
        "no_execution_authority",
        "no_paper_or_live_authority",
        "no_strategy_promotion_authority",
        "forbidden_content_rejected",
        "uncertainty_notes",
        "unresolved_questions",
        "missing_data_to_resolve",
        "evidence_to_check",
        "source_references_to_revisit",
        "uncertainty_to_reduce",
        "falsification_check_to_perform",
        "blocking_reason",
        "next_manual_step",
        "normalized_output_shape",
    }
)


def load_and_validate_corpus(corpus: object) -> dict[str, Any]:
    """Validate and deep-copy the fixed corpus without echoing invalid input."""
    safety_error = _safety_error(corpus)
    if safety_error:
        return _validation(False, "RUN_FAILED_VALIDATION", (safety_error,))
    if not isinstance(corpus, Mapping):
        return _validation(False, "RUN_FAILED_INPUT_CONTRACT", ("UNSUPPORTED_CORPUS_SHAPE",))
    if tuple(corpus.keys()) != _CORPUS_ROOT_FIELDS:
        return _validation(False, "RUN_FAILED_CORPUS_VERSION", ("CORPUS_FIELDS_MISMATCH",))
    expected_root = {
        "corpus_id": CORPUS_ID,
        "corpus_version": CORPUS_VERSION,
        "corpus_posture": CORPUS_POSTURE,
        "metric_registry_version": METRIC_REGISTRY_VERSION,
        "stage_map_version": STAGE_MAP_VERSION,
    }
    for field, expected in expected_root.items():
        if corpus[field] != expected:
            status = (
                "RUN_FAILED_METRIC_REGISTRY"
                if field == "metric_registry_version"
                else "RUN_FAILED_STAGE_MAP"
                if field == "stage_map_version"
                else "RUN_FAILED_CORPUS_VERSION"
            )
            return _validation(False, status, (f"{field.upper()}_MISMATCH",))
    cases = corpus["cases"]
    if not isinstance(cases, list) or len(cases) != 14:
        return _validation(False, "RUN_FAILED_CORPUS_VERSION", ("CORPUS_CASE_COUNT_MISMATCH",))
    seen: list[str] = []
    families: list[str] = []
    normalized_cases: list[dict[str, Any]] = []
    for case in cases:
        if not isinstance(case, Mapping) or tuple(case.keys()) != _CORPUS_CASE_FIELDS:
            return _validation(False, "RUN_FAILED_CORPUS_VERSION", ("CORPUS_CASE_FIELDS_MISMATCH",))
        case_id = case["case_id"]
        if case_id not in _CASE_IDS or case_id in seen:
            return _validation(False, "RUN_FAILED_CORPUS_VERSION", ("INVALID_OR_DUPLICATE_CASE_ID",))
        seen.append(case_id)
        family = case["family"]
        if not isinstance(family, str) or not family or family in families:
            return _validation(False, "RUN_FAILED_CORPUS_VERSION", ("INVALID_OR_DUPLICATE_FAMILY",))
        families.append(family)
        expected_metadata = _EXPECTED_CASE_METADATA[case_id]
        actual_metadata = (
            case["family"],
            case["input_artifact_shape"],
            case["expected_validation_state"],
            case["expected_metric_events"],
            case["negative_mutation_family"],
        )
        if actual_metadata != expected_metadata:
            return _validation(
                False, "RUN_FAILED_CORPUS_VERSION", ("CORPUS_CASE_METADATA_MISMATCH",)
            )
        stage_ids = case["stage_ids"]
        metric_ids = case["metric_ids"]
        if (
            not isinstance(stage_ids, list)
            or not stage_ids
            or len(stage_ids) != len(set(stage_ids))
            or any(stage_id not in _STAGE_BY_ID for stage_id in stage_ids)
        ):
            return _validation(False, "RUN_FAILED_STAGE_MAP", ("INVALID_CASE_STAGE_MAPPING",))
        if (
            not isinstance(metric_ids, list)
            or not metric_ids
            or len(metric_ids) != len(set(metric_ids))
            or any(metric_id not in _WAVE_1_IDS for metric_id in metric_ids)
        ):
            return _validation(False, "RUN_FAILED_METRIC_REGISTRY", ("INVALID_CASE_METRIC_MAPPING",))
        expected_stage_ids, expected_metric_ids = _EXPECTED_CASE_MAP[case_id]
        if tuple(stage_ids) != expected_stage_ids:
            return _validation(False, "RUN_FAILED_STAGE_MAP", ("CASE_STAGE_MAP_MISMATCH",))
        if tuple(metric_ids) != expected_metric_ids:
            return _validation(
                False, "RUN_FAILED_METRIC_REGISTRY", ("CASE_METRIC_COVERAGE_MISMATCH",)
            )
        if case["human_review"] != "REQUIRED":
            return _validation(False, "RUN_FAILED_VALIDATION", ("HUMAN_REVIEW_REQUIRED",))
        observations = case["observations"]
        if not isinstance(observations, Mapping) or not observations:
            return _validation(False, "RUN_FAILED_INPUT_CONTRACT", ("INVALID_OBSERVATIONS",))
        if any(key not in _OBSERVATION_FIELDS for key in observations):
            return _validation(False, "RUN_FAILED_INPUT_CONTRACT", ("UNKNOWN_OBSERVATION_FIELD",))
        normalized_case = copy.deepcopy(dict(case))
        normalized_case["stage_ids"] = tuple(stage_ids)
        normalized_case["metric_ids"] = tuple(metric_ids)
        normalized_case["observations"] = copy.deepcopy(dict(observations))
        normalized_cases.append(normalized_case)
    if tuple(seen) != _CASE_IDS or len(set(families)) != 14:
        return _validation(False, "RUN_FAILED_CORPUS_VERSION", ("CORPUS_IDENTITY_OR_ORDER_MISMATCH",))
    covered = {
        metric_id for case in normalized_cases for metric_id in case["metric_ids"]
    }
    if covered != set(_WAVE_1_IDS):
        return _validation(
            False, "RUN_FAILED_METRIC_REGISTRY", ("WAVE_1_CORPUS_COVERAGE_MISMATCH",)
        )
    try:
        canonical_bytes = json.dumps(
            corpus, sort_keys=True, separators=(",", ":"), ensure_ascii=True
        ).encode("ascii")
    except (TypeError, ValueError):
        return _validation(False, "RUN_FAILED_INPUT_CONTRACT", ("INVALID_CORPUS_VALUE_TYPE",))
    if hashlib.sha256(canonical_bytes).hexdigest() != CORPUS_CONTENT_SHA256:
        return _validation(False, "RUN_FAILED_INPUT_CONTRACT", ("CORPUS_CONTENT_MISMATCH",))
    normalized = copy.deepcopy(dict(corpus))
    normalized["cases"] = tuple(normalized_cases)
    return _validation(True, "RUN_VALID_MEASUREMENT_COMPLETE", normalized=normalized)


def validate_operator_actions(
    actions: object,
    *,
    run_id: str,
    selected_cases: Sequence[str],
    corpus_cases: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Validate bounded actions and reconcile one final disposition per case."""
    safety_error = _safety_error(actions)
    if safety_error:
        return _validation(False, "RUN_FAILED_VALIDATION", (safety_error,))
    if not isinstance(actions, (list, tuple)):
        return _validation(False, "RUN_FAILED_EVENT_CONTRACT", ("INVALID_ACTION_COLLECTION",))
    case_map = {case["case_id"]: case for case in corpus_cases}
    action_ids: set[str] = set()
    retries: Counter[str] = Counter()
    normalized: list[dict[str, Any]] = []
    for action in actions:
        if not isinstance(action, Mapping) or tuple(action.keys()) != REQUIRED_ACTION_FIELDS:
            return _validation(False, "RUN_FAILED_EVENT_CONTRACT", ("ACTION_FIELDS_MISMATCH",))
        if not _safe_identifier(action["action_id"]) or action["action_id"] in action_ids:
            return _validation(False, "RUN_FAILED_EVENT_CONTRACT", ("INVALID_OR_DUPLICATE_ACTION_ID",))
        action_ids.add(action["action_id"])
        if action["run_id"] != run_id:
            return _validation(False, "RUN_FAILED_EVENT_CONTRACT", ("CROSS_RUN_ACTION",))
        case_id = action["case_id"]
        if case_id not in selected_cases or case_id not in case_map:
            return _validation(False, "RUN_FAILED_EVENT_CONTRACT", ("ORPHAN_OR_CROSS_CASE_ACTION",))
        if action["stage_id"] not in case_map[case_id]["stage_ids"]:
            return _validation(False, "RUN_FAILED_EVENT_CONTRACT", ("CROSS_CASE_STAGE_ACTION",))
        action_type = action["action_type"]
        if action_type not in ALLOWED_OPERATOR_ACTIONS:
            return _validation(False, "RUN_FAILED_EVENT_CONTRACT", ("UNKNOWN_OPERATOR_ACTION",))
        if action["reason_code"] not in ALLOWED_REASON_CODES:
            return _validation(False, "RUN_FAILED_EVENT_CONTRACT", ("UNKNOWN_ACTION_REASON",))
        if action["correction_target"] not in ALLOWED_CORRECTION_TARGETS:
            return _validation(False, "RUN_FAILED_EVENT_CONTRACT", ("UNKNOWN_CORRECTION_TARGET",))
        if action["human_review_required"] is not True:
            return _validation(False, "RUN_FAILED_VALIDATION", ("HUMAN_REVIEW_REQUIRED",))
        if action["non_authority_notice"] != NON_AUTHORITY_NOTICE:
            return _validation(False, "RUN_FAILED_INPUT_CONTRACT", ("NOTICE_MISMATCH",))
        expected_reason, allowed_targets, expected_ack = _ACTION_RULES[action_type]
        if (
            action["reason_code"] != expected_reason
            or action["correction_target"] not in allowed_targets
            or action["reviewer_acknowledgement"] is not expected_ack
        ):
            return _validation(False, "RUN_FAILED_VALIDATION", ("INVALID_ACTION_TRANSITION",))
        if action_type == "RETRY_CASE":
            retries[case_id] += 1
            if retries[case_id] > 1:
                return _validation(False, "RUN_FAILED_EVENT_CONTRACT", ("UNBOUNDED_RETRY",))
        normalized.append(copy.deepcopy(dict(action)))
    abort_actions = [
        action for action in normalized if action["action_type"] == "ABORT_RUN"
    ]
    if len(abort_actions) > 1:
        return _validation(
            False,
            "RUN_FAILED_EVENT_CONTRACT",
            ("DUPLICATE_ABORT_ACTION",),
        )
    if abort_actions:
        return _validation(
            True,
            "RUN_ABORTED_BY_OPERATOR",
            normalized={"actions": tuple(normalized)},
        )
    if any(action["action_type"] == "NO_ACTION" for action in normalized):
        return _validation(
            False,
            "RUN_FAILED_VALIDATION",
            ("NONFINAL_ACTION_NOT_ALLOWED",),
        )
    for case_id in selected_cases:
        dispositions = [
            action
            for action in normalized
            if action["case_id"] == case_id
            and action["action_type"] in _FINAL_REVIEW_ACTIONS
        ]
        if not dispositions:
            return _validation(
                False,
                "RUN_FAILED_VALIDATION",
                ("MISSING_FINAL_REVIEW_DISPOSITION",),
            )
        if len(dispositions) > 1:
            error = (
                "DUPLICATE_ACKNOWLEDGEMENT"
                if all(
                    action["action_type"] == "ACKNOWLEDGE"
                    for action in dispositions
                )
                else "CONFLICTING_FINAL_REVIEW_DISPOSITIONS"
            )
            return _validation(False, "RUN_FAILED_VALIDATION", (error,))
    return _validation(
        True,
        "RUN_VALID_MEASUREMENT_COMPLETE",
        normalized={"actions": tuple(normalized)},
    )


def _event(
    *,
    run_id: str,
    case_id: str,
    repeat_index: int,
    sequence: int,
    event_type: str,
    stage_id: str = "",
    metric_ids: Sequence[str] = (),
    validation_state: str = "NOT_APPLICABLE",
    error_codes: Sequence[str] = (),
    operator_action_type: str = "NO_ACTION",
    input_reference: str = "NONE",
    output_reference: str = "NONE",
) -> dict[str, Any]:
    return {
        "event_contract_version": EVENT_CONTRACT_VERSION,
        "run_id": run_id,
        "case_id": case_id,
        "repeat_index": repeat_index,
        "event_sequence": sequence,
        "event_type": event_type,
        "stage_id": stage_id,
        "metric_ids": tuple(metric_ids),
        "monotonic_elapsed_ns": sequence * 10,
        "validation_state": validation_state,
        "error_codes": tuple(error_codes),
        "operator_action_type": operator_action_type,
        "input_reference": input_reference,
        "output_reference": output_reference,
        "non_authority_notice": NON_AUTHORITY_NOTICE,
    }


def validate_event_stream(
    events: object,
    *,
    run_id: str,
    selected_cases: Sequence[str],
    expected_operator_actions: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Validate the complete event surface, lineage, ordering, and dispositions."""
    safety_error = _safety_error(events)
    if safety_error:
        return _validation(False, "RUN_FAILED_VALIDATION", (safety_error,))
    if not isinstance(events, (list, tuple)) or not events:
        return _validation(False, "RUN_FAILED_EVENT_CONTRACT", ("EMPTY_EVENT_STREAM",))
    expected_dispositions = (
        {
            action["case_id"]: action["action_type"]
            for action in expected_operator_actions
            if action["action_type"] in _FINAL_REVIEW_ACTIONS
        }
        if expected_operator_actions is not None
        else None
    )
    normalized: list[dict[str, Any]] = []
    previous_elapsed = -1
    started: set[tuple[str, int, str]] = set()
    completed: set[tuple[str, int, str]] = set()
    event_counts: Counter[tuple[str, int, str]] = Counter()
    review_dispositions: dict[tuple[str, int], str] = {}
    for index, event in enumerate(events, 1):
        if not isinstance(event, Mapping) or tuple(event.keys()) != REQUIRED_EVENT_FIELDS:
            return _validation(False, "RUN_FAILED_EVENT_CONTRACT", ("EVENT_FIELDS_MISMATCH",))
        if event["event_contract_version"] != EVENT_CONTRACT_VERSION:
            return _validation(False, "RUN_FAILED_EVENT_CONTRACT", ("EVENT_VERSION_MISMATCH",))
        if event["run_id"] != run_id:
            return _validation(False, "RUN_FAILED_EVENT_CONTRACT", ("CROSS_RUN_EVENT",))
        if (
            not isinstance(event["event_sequence"], int)
            or isinstance(event["event_sequence"], bool)
            or event["event_sequence"] != index
        ):
            return _validation(False, "RUN_FAILED_EVENT_CONTRACT", ("NONCONTIGUOUS_EVENT_SEQUENCE",))
        if event["event_type"] not in ALLOWED_EVENT_TYPES:
            return _validation(False, "RUN_FAILED_EVENT_CONTRACT", ("UNKNOWN_EVENT_TYPE",))
        if event["validation_state"] not in ALLOWED_EVENT_VALIDATION_STATES:
            return _validation(
                False,
                "RUN_FAILED_EVENT_CONTRACT",
                ("UNKNOWN_EVENT_VALIDATION_STATE",),
            )
        error_codes = event["error_codes"]
        if (
            not isinstance(error_codes, (list, tuple))
            or any(not isinstance(code, str) for code in error_codes)
            or len(error_codes) != len(set(error_codes))
            or any(code not in ALLOWED_EVENT_ERROR_CODES for code in error_codes)
            or tuple(error_codes)
            != tuple(
                sorted(
                    error_codes,
                    key=ALLOWED_EVENT_ERROR_CODES.index,
                )
            )
        ):
            return _validation(
                False,
                "RUN_FAILED_EVENT_CONTRACT",
                ("INVALID_EVENT_ERROR_CODES",),
            )
        if (
            not isinstance(event["monotonic_elapsed_ns"], int)
            or isinstance(event["monotonic_elapsed_ns"], bool)
            or event["monotonic_elapsed_ns"] < 0
        ):
            return _validation(False, "RUN_FAILED_EVENT_CONTRACT", ("NEGATIVE_OR_INVALID_DURATION",))
        if event["monotonic_elapsed_ns"] < previous_elapsed:
            return _validation(False, "RUN_FAILED_EVENT_CONTRACT", ("OUT_OF_ORDER_DURATION",))
        previous_elapsed = event["monotonic_elapsed_ns"]
        case_id = event["case_id"]
        repeat_index = event["repeat_index"]
        if case_id:
            if (
                not isinstance(case_id, str)
                or case_id not in selected_cases
                or not isinstance(repeat_index, int)
                or isinstance(repeat_index, bool)
                or repeat_index not in (1, 2, 3)
            ):
                return _validation(False, "RUN_FAILED_EVENT_CONTRACT", ("ORPHAN_OR_CROSS_CASE_EVENT",))
        elif (
            not isinstance(case_id, str)
            or not isinstance(repeat_index, int)
            or isinstance(repeat_index, bool)
            or repeat_index != 0
        ):
            return _validation(False, "RUN_FAILED_EVENT_CONTRACT", ("INVALID_RUN_LEVEL_EVENT",))
        stage_id = event["stage_id"]
        if not isinstance(stage_id, str) or (
            stage_id and stage_id not in _STAGE_BY_ID
        ):
            return _validation(False, "RUN_FAILED_STAGE_MAP", ("UNKNOWN_STAGE",))
        metric_ids = event["metric_ids"]
        if (
            not isinstance(metric_ids, (list, tuple))
            or any(not isinstance(metric_id, str) for metric_id in metric_ids)
            or len(metric_ids) != len(set(metric_ids))
            or any(metric_id not in _METRIC_BY_ID for metric_id in metric_ids)
        ):
            return _validation(False, "RUN_FAILED_METRIC_REGISTRY", ("INVALID_EVENT_METRIC_IDS",))
        if event["operator_action_type"] not in ALLOWED_OPERATOR_ACTIONS:
            return _validation(False, "RUN_FAILED_EVENT_CONTRACT", ("UNKNOWN_OPERATOR_ACTION",))
        if event["event_type"] == "OPERATOR_ACKNOWLEDGED":
            if (
                event["operator_action_type"] != "ACKNOWLEDGE"
                or event["validation_state"] != "REVIEW_COMPLETE"
                or tuple(error_codes) != ()
            ):
                return _validation(
                    False,
                    "RUN_FAILED_EVENT_CONTRACT",
                    ("EVENT_ACTION_DISPOSITION_MISMATCH",),
                )
            review_dispositions[(case_id, repeat_index)] = "ACKNOWLEDGE"
        elif event["event_type"] == "CORRECTION_REQUESTED":
            if (
                event["operator_action_type"]
                not in {"REQUEST_CORRECTION", "RETRY_CASE", "DEFER_CASE"}
                or event["validation_state"]
                != "DEFER_RECEIPT_PENDING_CORRECTION"
                or tuple(error_codes) != ("ACTION_DISPOSITION_DEFERRED",)
            ):
                return _validation(
                    False,
                    "RUN_FAILED_EVENT_CONTRACT",
                    ("EVENT_ACTION_DISPOSITION_MISMATCH",),
                )
            review_dispositions[(case_id, repeat_index)] = event[
                "operator_action_type"
            ]
        elif event["operator_action_type"] != "NO_ACTION":
            return _validation(
                False,
                "RUN_FAILED_EVENT_CONTRACT",
                ("UNEXPECTED_EVENT_ACTION",),
            )
        if (
            event["event_type"] == "OPERATOR_REVIEW_REQUIRED"
            and event["validation_state"] != "REVIEW_REQUIRED"
        ):
            return _validation(
                False,
                "RUN_FAILED_EVENT_CONTRACT",
                ("EVENT_REVIEW_STATE_MISMATCH",),
            )
        if not _safe_reference(event["input_reference"]) or not _safe_reference(
            event["output_reference"]
        ):
            return _validation(False, "RUN_FAILED_EVENT_CONTRACT", ("UNSAFE_EVENT_REFERENCE",))
        if event["non_authority_notice"] != NON_AUTHORITY_NOTICE:
            return _validation(False, "RUN_FAILED_EVENT_CONTRACT", ("NOTICE_MISMATCH",))
        stage_key = (case_id, repeat_index, stage_id)
        if event["event_type"] == "STAGE_STARTED":
            if not stage_id or stage_key in started:
                return _validation(False, "RUN_FAILED_EVENT_CONTRACT", ("DUPLICATE_STAGE_START",))
            started.add(stage_key)
        if event["event_type"] == "STAGE_COMPLETED":
            if stage_key not in started or stage_key in completed:
                return _validation(False, "RUN_FAILED_EVENT_CONTRACT", ("ORPHAN_STAGE_COMPLETION",))
            completed.add(stage_key)
        event_counts[(case_id, repeat_index, event["event_type"])] += 1
        normalized.append(copy.deepcopy(dict(event)))
    if events[0]["event_type"] != "RUN_STARTED" or events[-1]["event_type"] not in (
        "RUN_COMPLETED",
        "RUN_FAILED",
    ):
        return _validation(False, "RUN_FAILED_EVENT_CONTRACT", ("INVALID_RUN_EVENT_BOUNDARY",))
    if started != completed:
        return _validation(False, "RUN_FAILED_EVENT_CONTRACT", ("INCOMPLETE_STAGE_EVENTS",))
    if event_counts[("", 0, "RUN_STARTED")] != 1 or (
        event_counts[("", 0, "RUN_COMPLETED")]
        + event_counts[("", 0, "RUN_FAILED")]
        != 1
    ):
        return _validation(False, "RUN_FAILED_EVENT_CONTRACT", ("INVALID_RUN_EVENT_COUNT",))
    for case_id in selected_cases:
        expected_stages = set(_EXPECTED_CASE_MAP[case_id][0])
        for repeat_index in range(1, REQUIRED_REPEATS + 1):
            for event_type in (
                "CASE_STARTED",
                "OPERATOR_REVIEW_REQUIRED",
            ):
                if event_counts[(case_id, repeat_index, event_type)] != 1:
                    return _validation(
                        False,
                        "RUN_FAILED_EVENT_CONTRACT",
                        ("MISSING_OR_DUPLICATE_REQUIRED_EVENT",),
                    )
            review_event_count = (
                event_counts[(case_id, repeat_index, "OPERATOR_ACKNOWLEDGED")]
                + event_counts[(case_id, repeat_index, "CORRECTION_REQUESTED")]
            )
            if review_event_count != 1:
                return _validation(
                    False,
                    "RUN_FAILED_EVENT_CONTRACT",
                    ("MISSING_OR_DUPLICATE_REVIEW_DISPOSITION_EVENT",),
                )
            if (
                event_counts[(case_id, repeat_index, "CASE_COMPLETED")]
                + event_counts[(case_id, repeat_index, "CASE_FAILED")]
                != 1
            ) or (
                event_counts[(case_id, repeat_index, "VALIDATION_PASSED")]
                + event_counts[(case_id, repeat_index, "VALIDATION_FAILED")]
                != 1
            ):
                return _validation(
                    False,
                    "RUN_FAILED_EVENT_CONTRACT",
                    ("MISSING_OR_DUPLICATE_REQUIRED_EVENT",),
                )
            disposition = review_dispositions.get((case_id, repeat_index))
            if (
                disposition == "ACKNOWLEDGE"
                and event_counts[(case_id, repeat_index, "CASE_COMPLETED")] != 1
            ) or (
                disposition != "ACKNOWLEDGE"
                and event_counts[(case_id, repeat_index, "CASE_FAILED")] != 1
            ):
                return _validation(
                    False,
                    "RUN_FAILED_EVENT_CONTRACT",
                    ("CASE_DISPOSITION_EVENT_MISMATCH",),
                )
            if (
                expected_dispositions is not None
                and disposition != expected_dispositions.get(case_id)
            ):
                return _validation(
                    False,
                    "RUN_FAILED_EVENT_CONTRACT",
                    ("EVENT_ACTION_RECONCILIATION_FAILED",),
                )
            actual_stages = {
                stage_id
                for event_case_id, event_repeat, stage_id in started
                if event_case_id == case_id and event_repeat == repeat_index
            }
            if actual_stages != expected_stages:
                return _validation(
                    False, "RUN_FAILED_EVENT_CONTRACT", ("CASE_STAGE_EVENT_COVERAGE_MISMATCH",)
                )
        if (
            len(
                {
                    review_dispositions[(case_id, repeat_index)]
                    for repeat_index in range(1, REQUIRED_REPEATS + 1)
                }
            )
            != 1
        ):
            return _validation(
                False,
                "RUN_FAILED_EVENT_CONTRACT",
                ("EVENT_ACTION_RECONCILIATION_FAILED",),
            )
    expected_order: list[tuple[str, int, str, str]] = [
        ("", 0, "RUN_STARTED", "")
    ]
    for case_id in selected_cases:
        for repeat_index in range(1, REQUIRED_REPEATS + 1):
            expected_order.append((case_id, repeat_index, "CASE_STARTED", ""))
            for stage_id in _EXPECTED_CASE_MAP[case_id][0]:
                expected_order.extend(
                    (
                        (case_id, repeat_index, "STAGE_STARTED", stage_id),
                        (case_id, repeat_index, "STAGE_COMPLETED", stage_id),
                    )
                )
            expected_order.extend(
                (
                    (case_id, repeat_index, "VALIDATION_PASSED", ""),
                    (case_id, repeat_index, "OPERATOR_REVIEW_REQUIRED", ""),
                )
            )
            disposition = review_dispositions[(case_id, repeat_index)]
            expected_order.extend(
                (
                    (
                        case_id,
                        repeat_index,
                        (
                            "OPERATOR_ACKNOWLEDGED"
                            if disposition == "ACKNOWLEDGE"
                            else "CORRECTION_REQUESTED"
                        ),
                        "",
                    ),
                    (
                        case_id,
                        repeat_index,
                        (
                            "CASE_COMPLETED"
                            if disposition == "ACKNOWLEDGE"
                            else "CASE_FAILED"
                        ),
                        "",
                    ),
                )
            )
    expected_order.append(("", 0, events[-1]["event_type"], ""))
    actual_order = tuple(
        (
            event["case_id"],
            event["repeat_index"],
            event["event_type"],
            event["stage_id"],
        )
        for event in events
    )
    if actual_order != tuple(expected_order):
        return _validation(
            False,
            "RUN_FAILED_EVENT_CONTRACT",
            ("EVENT_ORDER_MISMATCH",),
        )
    final = events[-1]
    if (
        final["event_type"] == "RUN_COMPLETED"
        and final["validation_state"] != "RUN_VALID_MEASUREMENT_COMPLETE"
    ) or (
        final["event_type"] == "RUN_FAILED"
        and (
            final["validation_state"] not in ALLOWED_RUN_STATUSES
            or final["validation_state"] == "RUN_VALID_MEASUREMENT_COMPLETE"
        )
    ):
        return _validation(False, "RUN_FAILED_EVENT_CONTRACT", ("RUN_TERMINAL_EVENT_MISMATCH",))
    return _validation(
        True,
        "RUN_VALID_MEASUREMENT_COMPLETE",
        normalized={"events": tuple(normalized)},
    )


def _required_case_ids(metric: MetricDefinition) -> tuple[str, ...]:
    return tuple(_CASE_PATTERN.findall(metric.corpus_case_ids_or_family))


def _empty_metric_result(
    metric: MetricDefinition,
    *,
    selected_count: int,
    excluded_count: int,
    status: str,
    failure_codes: Sequence[str] = (),
) -> dict[str, Any]:
    return {
        "metric_id": metric.metric_id,
        "wave": metric.wave,
        "measurement_type": metric.measurement_type,
        "numerator": None,
        "denominator": None,
        "count": None,
        "duration_ns": None,
        "boolean_result": None,
        "set_coverage": None,
        "repeatability_result": None,
        "rubric_score": None,
        "applicable_case_count": selected_count,
        "excluded_case_count": excluded_count,
        "measurement_status": status,
        "failure_codes": tuple(failure_codes),
    }


def _values(cases: Sequence[Mapping[str, Any]], key: str) -> list[Any]:
    return [case["observations"][key] for case in cases if key in case["observations"]]


def _nonempty_sequence(value: object) -> bool:
    return isinstance(value, (list, tuple)) and bool(value) and all(
        isinstance(item, str) and bool(item) for item in value
    )


def _measure_wave_1(
    metric: MetricDefinition,
    cases: Sequence[Mapping[str, Any]],
    repeatability_passed: bool,
) -> dict[str, Any]:
    required = _required_case_ids(metric)
    chosen = tuple(case for case in cases if case["case_id"] in required)
    result = _empty_metric_result(
        metric,
        selected_count=len(chosen),
        excluded_count=len(required) - len(chosen),
        status="MEASURED_VALID",
    )
    if len(chosen) != len(required):
        result["measurement_status"] = "INSUFFICIENT_CASE_COVERAGE"
        result["failure_codes"] = ("MISSING_REQUIRED_CASE_COVERAGE",)
        return result
    observations = [case["observations"] for case in chosen]
    metric_id = metric.metric_id
    valid = True
    if metric_id == "RV-THR-01":
        per_case_counts = [len(set(obs.get("market_ids", ()))) for obs in observations]
        valid = all(
            count > 0
            and count == len(obs.get("market_ids", ()))
            and all(_safe_identifier(item) for item in obs.get("market_ids", ()))
            for count, obs in zip(per_case_counts, observations)
        )
        result["count"] = sum(per_case_counts)
    elif metric_id == "RV-THR-02":
        items = [item for obs in observations for item in obs.get("candidate_items", ())]
        ids = [item.get("candidate_id") for item in items if isinstance(item, Mapping)]
        valid = (
            bool(items)
            and len(ids) == len(items)
            and len(ids) == len(set(ids))
            and all(_safe_identifier(item) for item in ids)
            and all(item.get("candidate_label") in ALLOWED_CANDIDATE_LABELS for item in items)
        )
        result["count"] = len(items)
    elif metric_id == "RV-THR-06":
        invalid = [item for obs in observations for item in obs.get("invalid_records", ())]
        valid = bool(invalid) and all(
            isinstance(item, Mapping)
            and item.get("is_valid") is False
            and _nonempty_sequence(item.get("errors"))
            for item in invalid
        )
        result["count"] = len(invalid)
    elif metric_id == "RV-REJ-01":
        items = [item for obs in observations for item in obs.get("candidate_items", ())]
        valid = bool(items) and all(
            isinstance(item, Mapping)
            and _nonempty_sequence(item.get("candidate_reason_labels"))
            and len(item["candidate_reason_labels"]) == len(set(item["candidate_reason_labels"]))
            and all(label in ALLOWED_REASON_LABELS for label in item["candidate_reason_labels"])
            for item in items
        )
        result["boolean_result"] = valid
    elif metric_id == "RV-REJ-02":
        expected = {"CITATION", "EVIDENCE_FOR", "EVIDENCE_AGAINST", "COMPLETION"}
        observed: set[str] = set()
        for obs in observations:
            if _nonempty_sequence(obs.get("cited_source_references")):
                observed.add("CITATION")
            if _nonempty_sequence(obs.get("evidence_for")):
                observed.add("EVIDENCE_FOR")
            if _nonempty_sequence(obs.get("evidence_against")):
                observed.add("EVIDENCE_AGAINST")
            if _nonempty_sequence(obs.get("completion_labels")):
                observed.add("COMPLETION")
        valid = bool(expected) and observed <= expected and observed == expected
        result["set_coverage"] = f"{len(observed)}/{len(expected)}"
    elif metric_id in {"RV-REJ-04", "RV-REJ-07"}:
        quality = [item for obs in observations for item in obs.get("quality_results", ())]
        valid = bool(quality) and all(
            isinstance(item, Mapping)
            and isinstance(item.get("seeded_failure"), bool)
            and isinstance(item.get("detected"), bool)
            and isinstance(item.get("gate_passed"), bool)
            and (not item["seeded_failure"] or item["detected"])
            and (item["gate_passed"] == (not item["seeded_failure"]))
            for item in quality
        )
        if metric_id == "RV-REJ-04":
            result["numerator"] = sum(
                1 for item in quality if item["seeded_failure"] and item["detected"]
            )
            result["denominator"] = sum(1 for item in quality if item["seeded_failure"])
        else:
            result["numerator"] = sum(1 for item in quality if not item["gate_passed"])
            result["denominator"] = len(quality)
        valid = valid and bool(result["denominator"])
    elif metric_id == "RV-REJ-05":
        denominator = sum(bool(obs.get("unsupported_case")) for obs in observations)
        numerator = sum(
            bool(obs.get("unsupported_case"))
            and bool(obs.get("unsupported_claims_identified"))
            and obs.get("receipt_label") == "REJECTED_UNSUPPORTED_CONTENT"
            for obs in observations
        )
        valid = denominator > 0 and numerator == denominator
        result["numerator"], result["denominator"] = numerator, denominator
    elif metric_id == "RV-REJ-06":
        denominator = sum(
            int(obs.get("seeded_duplicate_or_conflict_count", 0)) for obs in observations
        )
        numerator = sum(
            int(obs.get("detected_duplicate_or_conflict_count", 0)) for obs in observations
        )
        valid = denominator > 0 and numerator == denominator
        result["numerator"], result["denominator"] = numerator, denominator
    elif metric_id == "RV-HYP-02":
        valid = all(
            _nonempty_sequence(obs.get("evidence_for"))
            and _nonempty_sequence(obs.get("evidence_against"))
            and {"EVIDENCE_FOR_RECORDED", "EVIDENCE_AGAINST_RECORDED"}
            <= set(obs.get("completion_labels", ()))
            for obs in observations
        )
        result["boolean_result"] = valid
    elif metric_id == "RV-HYP-03":
        valid = all(
            _nonempty_sequence(obs.get("what_would_change_the_conclusion"))
            for obs in observations
        )
        result["boolean_result"] = valid
    elif metric_id == "RV-REP-01":
        valid = all(obs.get("exact_input_contract_validated") is True for obs in observations)
        result["boolean_result"] = valid
    elif metric_id == "RV-REP-02":
        valid = all(obs.get("identity_validated") is True for obs in observations)
        result["boolean_result"] = valid
    elif metric_id == "RV-REP-04":
        valid = all(obs.get("validation_receipt_valid") is True for obs in observations)
        result["boolean_result"] = valid
    elif metric_id == "RV-REP-05":
        valid = all(
            obs.get("reviewer_acknowledgement") is True
            and obs.get("human_review_required") is True
            for obs in observations
        )
        result["boolean_result"] = valid
    elif metric_id == "RV-REP-06":
        valid = repeatability_passed
        result["repeatability_result"] = "PASS" if valid else "FAIL"
    elif metric_id == "RV-REP-07":
        fields = ("source_conflicts", "uncertainties", "known_missing_data", "limitations")
        valid = all(all(_nonempty_sequence(obs.get(field)) for field in fields) for obs in observations)
        result["boolean_result"] = valid
    elif metric_id in {"RV-HOF-01", "RV-HOF-07"}:
        valid = all(
            obs.get("non_authority_notice_valid") is True
            and obs.get("no_execution_authority") is True
            and obs.get("no_paper_or_live_authority") is True
            and obs.get("no_strategy_promotion_authority") is True
            and obs.get("forbidden_content_rejected") is True
            for obs in observations
        )
        result["boolean_result"] = valid
    elif metric_id == "RV-HOF-02":
        fields = ("uncertainty_notes", "limitations", "unresolved_questions")
        valid = all(all(_nonempty_sequence(obs.get(field)) for field in fields) for obs in observations)
        result["boolean_result"] = valid
    elif metric_id == "RV-HOF-04":
        fields = (
            "missing_data_to_resolve",
            "evidence_to_check",
            "source_references_to_revisit",
            "uncertainty_to_reduce",
        )
        valid = all(all(_nonempty_sequence(obs.get(field)) for field in fields) for obs in observations)
        result["boolean_result"] = valid
    elif metric_id == "RV-HOF-06":
        fields = ("falsification_check_to_perform", "blocking_reason", "next_manual_step")
        valid = all(all(_nonempty_sequence(obs.get(field)) for field in fields) for obs in observations)
        result["boolean_result"] = valid
    else:
        valid = False
    if not valid:
        for field in (
            "numerator",
            "denominator",
            "count",
            "duration_ns",
            "boolean_result",
            "set_coverage",
            "repeatability_result",
            "rubric_score",
        ):
            result[field] = None
        result["measurement_status"] = "FAILED_VALIDATION"
        result["failure_codes"] = ("METRIC_DERIVATION_FAILED",)
    return result


def _execute_case(case: Mapping[str, Any], repeat_index: int) -> dict[str, Any]:
    """Return the deterministic comparison surface for one synthetic case."""
    del repeat_index
    return {
        "case_id": case["case_id"],
        "validation_state": case["expected_validation_state"],
        "error_codes": (),
        "normalized_output_shape": copy.deepcopy(
            case["observations"].get("normalized_output_shape", ())
        ),
        "metric_ids": tuple(case["metric_ids"]),
        "metric_results": copy.deepcopy(case["observations"]),
        "safety_flags": tuple((gate, True) for gate in SAFETY_GATES),
        "run_status": "RUN_VALID_MEASUREMENT_COMPLETE",
    }


def _measure_full_pass(
    cases: Sequence[Mapping[str, Any]],
    repeat_index: int,
) -> dict[str, Any]:
    """Return one complete deterministic case-and-metric comparison surface."""
    case_outputs = tuple(_execute_case(case, repeat_index) for case in cases)
    metric_results = tuple(
        _measure_wave_1(metric, cases, True)
        if metric.wave == "WAVE_1"
        else _empty_metric_result(
            metric,
            selected_count=0,
            excluded_count=0,
            status="BLOCKED_WAVE_2",
            failure_codes=("BLOCKED_WAVE_2",),
        )
        for metric in METRIC_REGISTRY
        if metric.metric_id != "RV-REP-06"
    )
    run_status = (
        "RUN_VALID_MEASUREMENT_COMPLETE"
        if all(
            result["measurement_status"] == "MEASURED_VALID"
            for result in metric_results
            if result["wave"] == "WAVE_1"
        )
        else "RUN_FAILED_VALIDATION"
    )
    return {
        "case_outputs": case_outputs,
        "metric_results": metric_results,
        "safety_flags": tuple((gate, True) for gate in SAFETY_GATES),
        "run_status": run_status,
    }


def _repeat_full_measurement_passes(
    cases: Sequence[Mapping[str, Any]],
) -> tuple[bool, tuple[dict[str, Any], ...]]:
    passes = tuple(
        _measure_full_pass(cases, repeat_index)
        for repeat_index in range(1, REQUIRED_REPEATS + 1)
    )
    return all(item == passes[0] for item in passes[1:]), passes


def _build_events(
    request: Mapping[str, Any],
    cases: Sequence[Mapping[str, Any]],
    actions: Sequence[Mapping[str, Any]],
    run_status: str,
) -> tuple[dict[str, Any], ...]:
    events: list[dict[str, Any]] = []

    def append(**kwargs: Any) -> None:
        events.append(
            _event(
                run_id=request["run_id"],
                sequence=len(events) + 1,
                **kwargs,
            )
        )

    append(case_id="", repeat_index=0, event_type="RUN_STARTED")
    dispositions = {
        action["case_id"]: action
        for action in actions
        if action["action_type"] in _FINAL_REVIEW_ACTIONS
    }
    for case in cases:
        for repeat_index in range(1, REQUIRED_REPEATS + 1):
            append(
                case_id=case["case_id"],
                repeat_index=repeat_index,
                event_type="CASE_STARTED",
                metric_ids=case["metric_ids"],
                input_reference=f"{case['case_id']}_INPUT",
            )
            for stage_id in case["stage_ids"]:
                append(
                    case_id=case["case_id"],
                    repeat_index=repeat_index,
                    event_type="STAGE_STARTED",
                    stage_id=stage_id,
                    metric_ids=case["metric_ids"],
                    input_reference=f"{case['case_id']}_INPUT",
                )
                append(
                    case_id=case["case_id"],
                    repeat_index=repeat_index,
                    event_type="STAGE_COMPLETED",
                    stage_id=stage_id,
                    metric_ids=case["metric_ids"],
                    validation_state=case["expected_validation_state"],
                    output_reference=f"{case['case_id']}_OUTPUT",
                )
            append(
                case_id=case["case_id"],
                repeat_index=repeat_index,
                event_type="VALIDATION_PASSED",
                metric_ids=case["metric_ids"],
                validation_state=case["expected_validation_state"],
                output_reference=f"{case['case_id']}_OUTPUT",
            )
            append(
                case_id=case["case_id"],
                repeat_index=repeat_index,
                event_type="OPERATOR_REVIEW_REQUIRED",
                metric_ids=case["metric_ids"],
                validation_state="REVIEW_REQUIRED",
            )
            disposition = dispositions[case["case_id"]]
            if disposition["action_type"] == "ACKNOWLEDGE":
                append(
                    case_id=case["case_id"],
                    repeat_index=repeat_index,
                    event_type="OPERATOR_ACKNOWLEDGED",
                    metric_ids=case["metric_ids"],
                    validation_state="REVIEW_COMPLETE",
                    operator_action_type="ACKNOWLEDGE",
                )
            else:
                append(
                    case_id=case["case_id"],
                    repeat_index=repeat_index,
                    event_type="CORRECTION_REQUESTED",
                    metric_ids=case["metric_ids"],
                    validation_state="DEFER_RECEIPT_PENDING_CORRECTION",
                    error_codes=("ACTION_DISPOSITION_DEFERRED",),
                    operator_action_type=disposition["action_type"],
                )
            append(
                case_id=case["case_id"],
                repeat_index=repeat_index,
                event_type=(
                    "CASE_COMPLETED"
                    if disposition["action_type"] == "ACKNOWLEDGE"
                    else "CASE_FAILED"
                ),
                metric_ids=case["metric_ids"],
                validation_state=(
                    case["expected_validation_state"]
                    if disposition["action_type"] == "ACKNOWLEDGE"
                    else "DEFER_RECEIPT_PENDING_CORRECTION"
                ),
                error_codes=(
                    ()
                    if disposition["action_type"] == "ACKNOWLEDGE"
                    else ("ACTION_DISPOSITION_DEFERRED",)
                ),
                output_reference=f"{case['case_id']}_OUTPUT",
            )
    append(
        case_id="",
        repeat_index=0,
        event_type=(
            "RUN_COMPLETED"
            if run_status == "RUN_VALID_MEASUREMENT_COMPLETE"
            else "RUN_FAILED"
        ),
        validation_state=run_status,
    )
    return tuple(events)


def _human_review_outcome(
    *,
    safety_failed: bool = False,
    deferred: bool = False,
    repeatability_passed: bool = True,
    coverage_complete: bool = True,
    contract_valid: bool = True,
) -> str:
    """Map bounded receipt state to the exact WP151 human-review outcome."""
    if safety_failed:
        return "REJECT_RECEIPT_SAFETY_FAILURE"
    if deferred:
        return "DEFER_RECEIPT_PENDING_CORRECTION"
    if not repeatability_passed:
        return "REJECT_RECEIPT_REPEATABILITY_FAILURE"
    if not coverage_complete:
        return "REJECT_RECEIPT_COVERAGE_FAILURE"
    if not contract_valid:
        return "REJECT_RECEIPT_CONTRACT_FAILURE"
    return "ACCEPT_MEASUREMENT_RECEIPT_FOR_RESEARCH_MEMORY_ONLY"


def _canonical_metric_results(
    cases: Sequence[Mapping[str, Any]],
    canonical_pass: Mapping[str, Any],
) -> tuple[dict[str, Any], ...]:
    pass_results = iter(canonical_pass["metric_results"])
    return tuple(
        _measure_wave_1(metric, cases, True)
        if metric.metric_id == "RV-REP-06"
        else copy.deepcopy(next(pass_results))
        for metric in METRIC_REGISTRY
    )


def _build_receipt(
    request: Mapping[str, Any],
    cases: Sequence[Mapping[str, Any]],
    events: Sequence[Mapping[str, Any]],
    actions: Sequence[Mapping[str, Any]],
    canonical_metric_results: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    metric_results = tuple(copy.deepcopy(canonical_metric_results))
    complete = all(
        result["measurement_status"] == "MEASURED_VALID"
        for result in metric_results
        if result["wave"] == "WAVE_1"
    )
    coverage_complete = not any(
        result["measurement_status"] == "INSUFFICIENT_CASE_COVERAGE"
        for result in metric_results
        if result["wave"] == "WAVE_1"
    )
    deferred = any(
        action["action_type"] in {"REQUEST_CORRECTION", "RETRY_CASE", "DEFER_CASE"}
        for action in actions
    )
    acknowledgements = {
        action["case_id"]
        for action in actions
        if action["action_type"] == "ACKNOWLEDGE"
    }
    human_review_complete = acknowledgements == {case["case_id"] for case in cases}
    run_status = (
        "RUN_VALID_MEASUREMENT_COMPLETE"
        if complete
        and human_review_complete
        and not deferred
        else "RUN_FAILED_VALIDATION"
    )
    hard_failures = (
        ("DEFER_RECEIPT_PENDING_CORRECTION",)
        if deferred
        else ("MISSING_REQUIRED_CASE_COVERAGE",)
        if not coverage_complete
        else ("RECEIPT_CONTRACT_FAILURE",)
        if not complete or not human_review_complete
        else ()
    )
    human_review_status = _human_review_outcome(
        deferred=deferred,
        repeatability_passed=True,
        coverage_complete=coverage_complete,
        contract_valid=complete and human_review_complete,
    )
    action_counts = Counter(action["action_type"] for action in actions)
    return {
        "receipt_contract_version": RECEIPT_CONTRACT_VERSION,
        "receipt_id": f"{request['run_id']}_RECEIPT",
        "run_contract_version": RUN_CONTRACT_VERSION,
        "corpus_id": CORPUS_ID,
        "corpus_version": CORPUS_VERSION,
        "metric_registry_version": METRIC_REGISTRY_VERSION,
        "stage_map_version": STAGE_MAP_VERSION,
        "run_id": request["run_id"],
        "case_count": len(cases),
        "repeat_count": REQUIRED_REPEATS,
        "event_count": len(events),
        "metric_results": metric_results,
        "hard_failures": hard_failures,
        "repeatability_results": tuple(
            (case["case_id"], "PASS")
            for case in cases
        ),
        "operator_action_counts": tuple(
            (action, action_counts.get(action, 0)) for action in ALLOWED_OPERATOR_ACTIONS
        ),
        "run_status": run_status,
        "human_review_status": human_review_status,
        "temporary_output_status": request["temporary_output_mode"],
        "non_authority_notice": NON_AUTHORITY_NOTICE,
        "safety_flags": tuple((gate, True) for gate in SAFETY_GATES),
    }


def validate_receipt(
    receipt: object,
    *,
    expected_run_id: str,
    expected_case_count: int,
    expected_event_count: int,
    expected_operator_action_count: int,
    expected_metric_results: Sequence[Mapping[str, Any]],
    expected_case_ids: Sequence[str],
    expected_operator_actions: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Validate exact receipt/result fields and Wave 2 blocking."""
    safety_error = _safety_error(receipt)
    if safety_error:
        return _validation(False, "RUN_FAILED_VALIDATION", (safety_error,))
    if not isinstance(receipt, Mapping) or tuple(receipt.keys()) != REQUIRED_RECEIPT_FIELDS:
        return _validation(False, "RUN_FAILED_VALIDATION", ("RECEIPT_FIELDS_MISMATCH",))
    identities = {
        "receipt_contract_version": RECEIPT_CONTRACT_VERSION,
        "receipt_id": f"{expected_run_id}_RECEIPT",
        "run_contract_version": RUN_CONTRACT_VERSION,
        "corpus_id": CORPUS_ID,
        "corpus_version": CORPUS_VERSION,
        "metric_registry_version": METRIC_REGISTRY_VERSION,
        "stage_map_version": STAGE_MAP_VERSION,
        "run_id": expected_run_id,
        "case_count": expected_case_count,
        "repeat_count": REQUIRED_REPEATS,
        "event_count": expected_event_count,
        "non_authority_notice": NON_AUTHORITY_NOTICE,
    }
    if any(receipt[field] != expected for field, expected in identities.items()):
        return _validation(False, "RUN_FAILED_VALIDATION", ("RECEIPT_RECONCILIATION_FAILED",))
    if receipt["run_status"] not in ALLOWED_RUN_STATUSES:
        return _validation(False, "RUN_FAILED_VALIDATION", ("UNKNOWN_RUN_STATUS",))
    if receipt["human_review_status"] not in ALLOWED_HUMAN_REVIEW_OUTCOMES:
        return _validation(
            False,
            "RUN_FAILED_VALIDATION",
            ("UNKNOWN_HUMAN_REVIEW_OUTCOME",),
        )
    metric_results = receipt["metric_results"]
    if not isinstance(metric_results, (list, tuple)) or len(metric_results) != 39:
        return _validation(False, "RUN_FAILED_METRIC_REGISTRY", ("METRIC_RESULT_COUNT_MISMATCH",))
    seen: list[str] = []
    value_fields = (
        "numerator",
        "denominator",
        "count",
        "duration_ns",
        "boolean_result",
        "set_coverage",
        "repeatability_result",
        "rubric_score",
    )
    for expected_metric, result in zip(METRIC_REGISTRY, metric_results):
        if not isinstance(result, Mapping) or tuple(result.keys()) != REQUIRED_METRIC_RESULT_FIELDS:
            return _validation(False, "RUN_FAILED_VALIDATION", ("METRIC_RESULT_FIELDS_MISMATCH",))
        if result["metric_id"] != expected_metric.metric_id or result["metric_id"] in seen:
            return _validation(False, "RUN_FAILED_METRIC_REGISTRY", ("METRIC_RESULT_ORDER_MISMATCH",))
        seen.append(result["metric_id"])
        if (
            result["wave"] != expected_metric.wave
            or result["measurement_type"] != expected_metric.measurement_type
            or result["measurement_status"] not in ALLOWED_MEASUREMENT_STATUSES
        ):
            return _validation(False, "RUN_FAILED_METRIC_REGISTRY", ("METRIC_RESULT_IDENTITY_MISMATCH",))
        if (
            not isinstance(result["applicable_case_count"], int)
            or isinstance(result["applicable_case_count"], bool)
            or not isinstance(result["excluded_case_count"], int)
            or isinstance(result["excluded_case_count"], bool)
            or result["applicable_case_count"] < 0
            or result["excluded_case_count"] < 0
            or (
                expected_metric.wave == "WAVE_1"
                and result["applicable_case_count"] + result["excluded_case_count"]
                != len(_required_case_ids(expected_metric))
            )
        ):
            return _validation(False, "RUN_FAILED_VALIDATION", ("METRIC_CASE_COUNT_MISMATCH",))
        if expected_metric.wave == "WAVE_1" and result["measurement_status"] == "BLOCKED_WAVE_2":
            return _validation(False, "RUN_FAILED_METRIC_REGISTRY", ("WAVE_1_FALSE_BLOCK",))
        if expected_metric.wave == "WAVE_2" and (
            result["measurement_status"] != "BLOCKED_WAVE_2"
            or any(result[field] is not None for field in value_fields)
        ):
            return _validation(
                False,
                "RUN_FAILED_METRIC_REGISTRY",
                (
                    "WAVE_2_FALSE_MEASUREMENT",
                    "SAFETY_GATE_NO_WAVE_2_FALSE_MEASUREMENT",
                ),
            )
        failure_codes = result["failure_codes"]
        expected_failure_codes = {
            "MEASURED_VALID": (),
            "NOT_APPLICABLE": (),
            "FAILED_VALIDATION": ("METRIC_DERIVATION_FAILED",),
            "INSUFFICIENT_CASE_COVERAGE": ("MISSING_REQUIRED_CASE_COVERAGE",),
            "BLOCKED_WAVE_2": ("BLOCKED_WAVE_2",),
        }[result["measurement_status"]]
        if (
            not isinstance(failure_codes, (list, tuple))
            or tuple(failure_codes) != expected_failure_codes
            or any(code not in ALLOWED_METRIC_FAILURE_CODES for code in failure_codes)
        ):
            return _validation(
                False,
                "RUN_FAILED_VALIDATION",
                ("INVALID_METRIC_FAILURE_CODES",),
            )
        populated = [field for field in value_fields if result[field] is not None]
        expected_value_fields = {
            "COUNT": {"count"},
            "RATE": {"numerator", "denominator"},
            "BOOLEAN_COVERAGE": {"boolean_result"},
            "SET_COVERAGE": {"set_coverage"},
            "REPEATABILITY_EQUALITY": {"repeatability_result"},
            "NOT_IMPLEMENTABLE_YET": set(),
        }[expected_metric.measurement_type]
        if result["measurement_status"] == "MEASURED_VALID" and set(populated) != expected_value_fields:
            return _validation(False, "RUN_FAILED_VALIDATION", ("METRIC_VALUE_FIELD_MISMATCH",))
        if result["measurement_status"] != "MEASURED_VALID" and populated:
            return _validation(False, "RUN_FAILED_VALIDATION", ("FAILED_METRIC_VALUE_NOT_EMPTY",))
        if (
            expected_metric.measurement_type == "RATE"
            and result["measurement_status"] == "MEASURED_VALID"
            and (not isinstance(result["denominator"], int) or result["denominator"] <= 0)
        ):
            return _validation(False, "RUN_FAILED_VALIDATION", ("ZERO_DENOMINATOR",))
        if result["measurement_status"] == "MEASURED_VALID":
            if expected_metric.measurement_type == "COUNT" and (
                not isinstance(result["count"], int)
                or isinstance(result["count"], bool)
                or result["count"] < 0
            ):
                return _validation(False, "RUN_FAILED_VALIDATION", ("INVALID_COUNT",))
            if expected_metric.measurement_type == "RATE" and (
                not isinstance(result["numerator"], int)
                or isinstance(result["numerator"], bool)
                or isinstance(result["denominator"], bool)
                or result["numerator"] < 0
                or result["numerator"] > result["denominator"]
            ):
                return _validation(False, "RUN_FAILED_VALIDATION", ("INVALID_RATE",))
            if expected_metric.measurement_type == "BOOLEAN_COVERAGE" and not isinstance(
                result["boolean_result"], bool
            ):
                return _validation(False, "RUN_FAILED_VALIDATION", ("INVALID_BOOLEAN_COVERAGE",))
            if expected_metric.measurement_type == "SET_COVERAGE" and not (
                isinstance(result["set_coverage"], str)
                and re.fullmatch(r"(0|[1-9]\d*)/(0|[1-9]\d*)", result["set_coverage"])
                and int(result["set_coverage"].split("/")[1]) > 0
                and int(result["set_coverage"].split("/")[0])
                <= int(result["set_coverage"].split("/")[1])
            ):
                return _validation(False, "RUN_FAILED_VALIDATION", ("INVALID_SET_COVERAGE",))
            if (
                expected_metric.measurement_type == "REPEATABILITY_EQUALITY"
                and result["repeatability_result"] != "PASS"
            ):
                return _validation(False, "RUN_FAILED_REPEATABILITY", ("REPEATABILITY_MISMATCH",))
    if tuple(metric_results) != tuple(expected_metric_results):
        return _validation(
            False,
            "RUN_FAILED_VALIDATION",
            ("METRIC_RESULT_RECONCILIATION_FAILED",),
        )
    if receipt["temporary_output_status"] not in ALLOWED_OUTPUT_MODES:
        return _validation(False, "RUN_FAILED_VALIDATION", ("INVALID_OUTPUT_MODE",))
    flags = receipt["safety_flags"]
    if tuple(flags) != tuple((gate, True) for gate in SAFETY_GATES):
        return _validation(False, "RUN_FAILED_VALIDATION", ("SAFETY_GATE_FAILURE",))
    repeatability_results = receipt["repeatability_results"]
    if (
        not isinstance(repeatability_results, (list, tuple))
        or len(repeatability_results) != expected_case_count
        or any(
            not isinstance(item, (list, tuple))
            or len(item) != 2
            or item[1] not in {"PASS", "FAIL"}
            for item in repeatability_results
        )
    ):
        return _validation(False, "RUN_FAILED_VALIDATION", ("REPEATABILITY_RECONCILIATION_FAILED",))
    if (
        tuple(item[0] for item in repeatability_results) != tuple(expected_case_ids)
        or len(tuple(expected_case_ids)) != expected_case_count
        or any(
            not _safe_identifier(item[0])
            or item[0] not in _CASE_IDS
            for item in repeatability_results
        )
    ):
        return _validation(False, "RUN_FAILED_VALIDATION", ("REPEATABILITY_RECONCILIATION_FAILED",))
    action_counts = receipt["operator_action_counts"]
    if (
        not isinstance(action_counts, (list, tuple))
        or len(action_counts) != len(ALLOWED_OPERATOR_ACTIONS)
        or any(
            not isinstance(item, (list, tuple))
            or len(item) != 2
            or not isinstance(item[1], int)
            or isinstance(item[1], bool)
            or item[1] < 0
            for item in action_counts
        )
    ):
        return _validation(False, "RUN_FAILED_VALIDATION", ("ACTION_COUNT_RECONCILIATION_FAILED",))
    if (
        tuple(item[0] for item in action_counts) != ALLOWED_OPERATOR_ACTIONS
        or sum(item[1] for item in action_counts) != expected_operator_action_count
    ):
        return _validation(False, "RUN_FAILED_VALIDATION", ("ACTION_COUNT_RECONCILIATION_FAILED",))
    actual_action_counts = Counter(dict(action_counts))
    if expected_operator_actions is not None and actual_action_counts != Counter(
        action["action_type"] for action in expected_operator_actions
    ):
        return _validation(False, "RUN_FAILED_VALIDATION", ("ACTION_COUNT_RECONCILIATION_FAILED",))
    hard_failures = receipt["hard_failures"]
    if (
        not isinstance(hard_failures, (list, tuple))
        or any(not isinstance(code, str) for code in hard_failures)
        or len(hard_failures) != len(set(hard_failures))
        or any(
            code not in ALLOWED_RECEIPT_HARD_FAILURE_CODES
            for code in hard_failures
        )
    ):
        return _validation(False, "RUN_FAILED_VALIDATION", ("INVALID_RECEIPT_FAILURE_CODES",))
    deferred = any(
        actual_action_counts[action] > 0
        for action in ("REQUEST_CORRECTION", "RETRY_CASE", "DEFER_CASE")
    )
    repeatability_passed = all(
        item[1] == "PASS" for item in repeatability_results
    )
    coverage_complete = not any(
        result["measurement_status"] == "INSUFFICIENT_CASE_COVERAGE"
        for result in metric_results
        if result["wave"] == "WAVE_1"
    )
    contract_valid = all(
        result["measurement_status"] == "MEASURED_VALID"
        for result in metric_results
        if result["wave"] == "WAVE_1"
    ) and actual_action_counts["ACKNOWLEDGE"] == expected_case_count
    expected_hard_failures = (
        ("DEFER_RECEIPT_PENDING_CORRECTION",)
        if deferred
        else ("REPEATABILITY_MISMATCH",)
        if not repeatability_passed
        else ("MISSING_REQUIRED_CASE_COVERAGE",)
        if not coverage_complete
        else ("RECEIPT_CONTRACT_FAILURE",)
        if not contract_valid
        else ()
    )
    if tuple(hard_failures) != expected_hard_failures:
        return _validation(False, "RUN_FAILED_VALIDATION", ("RECEIPT_FAILURE_RECONCILIATION_FAILED",))
    expected_human_review_status = _human_review_outcome(
        deferred=deferred,
        repeatability_passed=repeatability_passed,
        coverage_complete=coverage_complete,
        contract_valid=contract_valid,
    )
    if receipt["human_review_status"] != expected_human_review_status:
        return _validation(False, "RUN_FAILED_VALIDATION", ("HUMAN_REVIEW_OUTCOME_MISMATCH",))
    expected_run_status = (
        "RUN_VALID_MEASUREMENT_COMPLETE"
        if expected_human_review_status
        == "ACCEPT_MEASUREMENT_RECEIPT_FOR_RESEARCH_MEMORY_ONLY"
        else "RUN_FAILED_REPEATABILITY"
        if expected_human_review_status
        == "REJECT_RECEIPT_REPEATABILITY_FAILURE"
        else "RUN_FAILED_VALIDATION"
    )
    if receipt["run_status"] != expected_run_status:
        return _validation(False, "RUN_FAILED_VALIDATION", ("RECEIPT_RUN_STATUS_MISMATCH",))
    return _validation(
        True,
        receipt["run_status"],
        normalized={"receipt": copy.deepcopy(dict(receipt))},
    )


def run_measurement(
    request: object,
    corpus: object,
    operator_actions: object,
) -> dict[str, Any]:
    """Run one explicit deterministic in-memory measurement attempt."""
    request_result = validate_run_request(request)
    if not request_result["is_valid"]:
        return _run_failure(request_result["run_status"], *request_result["errors"])
    corpus_result = load_and_validate_corpus(corpus)
    if not corpus_result["is_valid"]:
        return _run_failure(corpus_result["run_status"], *corpus_result["errors"])
    normalized_request = request_result["normalized"]
    all_cases = corpus_result["normalized"]["cases"]
    selected_cases = tuple(
        case for case in all_cases if case["case_id"] in normalized_request["case_selection"]
    )
    actions_result = validate_operator_actions(
        operator_actions,
        run_id=normalized_request["run_id"],
        selected_cases=normalized_request["case_selection"],
        corpus_cases=selected_cases,
    )
    if not actions_result["is_valid"]:
        return _run_failure(actions_result["run_status"], *actions_result["errors"])
    actions = actions_result["normalized"]["actions"]
    if any(action["action_type"] == "ABORT_RUN" for action in actions):
        return _run_failure("RUN_ABORTED_BY_OPERATOR", "ABORTED_BY_OPERATOR")
    repeatability_passed, measurement_passes = _repeat_full_measurement_passes(
        selected_cases
    )
    if not repeatability_passed:
        return _run_failure("RUN_FAILED_REPEATABILITY", "REPEATABILITY_MISMATCH")
    canonical_pass = measurement_passes[0]
    canonical_metric_results = _canonical_metric_results(
        selected_cases,
        canonical_pass,
    )
    deferred = any(
        action["action_type"] in {"REQUEST_CORRECTION", "RETRY_CASE", "DEFER_CASE"}
        for action in actions
    )
    provisional_status = (
        "RUN_VALID_MEASUREMENT_COMPLETE"
        if canonical_pass["run_status"] == "RUN_VALID_MEASUREMENT_COMPLETE"
        and not deferred
        else "RUN_FAILED_VALIDATION"
    )
    events = _build_events(normalized_request, selected_cases, actions, provisional_status)
    receipt = _build_receipt(
        normalized_request,
        selected_cases,
        events,
        actions,
        canonical_metric_results,
    )
    if receipt["run_status"] != provisional_status:
        events = _build_events(
            normalized_request, selected_cases, actions, receipt["run_status"]
        )
        receipt = _build_receipt(
            normalized_request,
            selected_cases,
            events,
            actions,
            canonical_metric_results,
        )
    event_result = validate_event_stream(
        events,
        run_id=normalized_request["run_id"],
        selected_cases=normalized_request["case_selection"],
        expected_operator_actions=actions,
    )
    if not event_result["is_valid"]:
        return _run_failure(event_result["run_status"], *event_result["errors"])
    receipt_result = validate_receipt(
        receipt,
        expected_run_id=normalized_request["run_id"],
        expected_case_count=len(selected_cases),
        expected_event_count=len(events),
        expected_operator_action_count=len(actions),
        expected_metric_results=canonical_metric_results,
        expected_case_ids=normalized_request["case_selection"],
        expected_operator_actions=actions,
    )
    if not receipt_result["is_valid"]:
        return _run_failure(receipt_result["run_status"], *receipt_result["errors"])
    run_status = receipt["run_status"]
    result = {
        "is_valid": run_status == "RUN_VALID_MEASUREMENT_COMPLETE",
        "run_status": run_status,
        "errors": (
            ()
            if run_status == "RUN_VALID_MEASUREMENT_COMPLETE"
            else tuple(receipt["hard_failures"])
        ),
        "events": copy.deepcopy(events),
        "receipt": copy.deepcopy(receipt),
    }
    safety_error = _safety_error(result)
    if safety_error:
        return _run_failure("RUN_FAILED_VALIDATION", safety_error)
    return result
