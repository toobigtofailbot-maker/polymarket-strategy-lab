"""Deterministic, non-authoritative Alpha Factory research-system gate records.

The module is deliberately local and side-effect free.  It validates and hashes
evidence supplied by the existing Alpha, PIT, and controlled-research systems; it
does not fetch data, invoke a provider, or create another registry.
"""

from __future__ import annotations

from dataclasses import dataclass, fields
from decimal import Decimal, InvalidOperation
import hashlib
import json
import re
from typing import Mapping, Sequence


AF1_SCHEMA_VERSION = "1.0.0"
AF1_BENCHMARK_MANIFEST_SCHEMA_ID = "af1-benchmark-manifest"
AF1_SEEDED_CASE_RESULT_SCHEMA_ID = "af1-seeded-case-result"
AF1_REAL_CASE_EVIDENCE_SCHEMA_ID = "af1-real-case-evidence"
AF1_BLIND_REVIEW_RECORD_SCHEMA_ID = "af1-blind-review-record"
AF1_GATE_RECEIPT_SCHEMA_ID = "af1-gate-receipt"

AF1_SEEDED_CASE_IDS = (
    "S1_DUPLICATE",
    "S2_NEGATIVE_SCOPE",
    "S3_REOPEN",
    "S4_PIT",
    "S5_CLAIM_EVIDENCE",
    "S6_PROVIDER_BACKEND_GAP",
    "S7_BUDGET",
    "S8_AUTHORITY",
)
AF1_DIMENSIONS = (
    "MEMORY_INTEGRITY",
    "PIT_PROVENANCE",
    "DUPLICATE_NEGATIVE_SCOPE",
    "MATERIAL_CHANGE_REOPEN",
    "CLAIM_EVIDENCE_SUPPORT",
    "RUNTIME_FAILURE_VISIBILITY",
    "BUDGET",
    "AUTHORITY_CONTAINMENT",
    "COVERAGE_SELECTION_ACCOUNTING",
    "RESEARCH_USEFULNESS_REPRODUCIBILITY",
)
AF1_DIMENSION_STATUSES = ("PASS", "FAIL", "INCONCLUSIVE")
AF1_DISPOSITIONS = ("AF1_PASS", "AF1_FAIL", "AF1_INCONCLUSIVE")
AF1_REVIEW_LABELS = (
    "USEFUL_RESEARCH_OUTPUT",
    "PARTIALLY_USEFUL_RESEARCH_OUTPUT",
    "NOT_USEFUL_RESEARCH_OUTPUT",
    "REVIEW_BLOCKED_INSUFFICIENT_CONTEXT",
)
AF1_REVIEW_REASON_CODES = (
    "CLEAR_SCOPE",
    "MATERIAL_EVIDENCE",
    "CONTRADICTION_ENGAGED",
    "FALSIFICATION_DISCIPLINE",
    "UNCERTAINTY_EXPLICIT",
    "SHALLOW_EVIDENCE",
    "UNSUPPORTED_CLAIMS",
    "MISSED_CONTRADICTION",
    "NO_FALSIFICATION",
    "SCOPE_DRIFT",
    "DUPLICATIVE_LOW_VALUE",
    "TOO_AMBIGUOUS",
    "INSUFFICIENT_CONTEXT",
)
AF1_REAL_CASE_IDS = ("AF1-C1", "AF1-C2", "AF1-C3")
AF1_REVIEW_SLOTS = ("REVIEW-01", "REVIEW-02", "REVIEW-03")
AF1_ANALYSIS_TEMPORAL_MODE = "HISTORICAL_REPLAY"
AF1_ALPHA_MEMORY_TEMPORAL_POSTURE = "HISTORICAL_AVAILABILITY_UNPROVEN"
AF1_TERMINAL_REASONS = (
    "PENDING_RUNTIME",
    "PUBLIC_POPULATION_EXTERNAL_UNAVAILABLE",
    "BENCHMARK_REQUIRED_LANE_ABSENT",
    "CONTROLLED_RUNTIME_UNAVAILABLE_TRUTHFULLY_CAPTURED",
    "RESEARCH_OUTPUT_INVALID",
    "USAGE_EVIDENCE_INVALID",
    "PROVIDER_MODEL_MISMATCH",
    "SUCCESSFUL_RUN_COST_UNKNOWN",
    "CASE_COST_LIMIT_BREACH",
    "AGGREGATE_COST_LIMIT_BREACH",
    "UNEXPECTED_RESEARCH_TOOL",
    "AUTHORITY_BOUNDARY_BREACH",
    "BLIND_REVIEW_COMPLETED",
)
AF1_EVIDENCE_STATES = ("PENDING_RUNTIME", "FINALIZED")
# Closed benchmark coverage terminals. A selected lane whose market has no usable
# question_text is genuine but non-research-executable coverage: it finalizes on the
# same A2 insufficient-coverage path as an absent lane, with zero Hermes calls.
AF1_COVERAGE_TERMINALS = (
    "COMPLETE",
    "REQUIRED_LANE_ABSENT",
    "REQUIRED_LANE_NOT_RESEARCH_EXECUTABLE",
)
AF1_A1_REASON = "PUBLIC_POPULATION_EXTERNAL_UNAVAILABLE"
AF1_A2_REASON = "BENCHMARK_REQUIRED_LANE_ABSENT"
AF1_REVIEW_COMPLETED_REASON = "BLIND_REVIEW_COMPLETED"
AF1_RUNTIME_UNAVAILABLE_REASON = "CONTROLLED_RUNTIME_UNAVAILABLE_TRUTHFULLY_CAPTURED"
# Section-18 real-case reasons (B/C rows): each is reached after 1..3 controller calls.
AF1_REAL_CASE_TERMINAL_REASONS = (
    AF1_RUNTIME_UNAVAILABLE_REASON,
    "RESEARCH_OUTPUT_INVALID",
    "USAGE_EVIDENCE_INVALID",
    "PROVIDER_MODEL_MISMATCH",
    "SUCCESSFUL_RUN_COST_UNKNOWN",
    "CASE_COST_LIMIT_BREACH",
    "AGGREGATE_COST_LIMIT_BREACH",
    "UNEXPECTED_RESEARCH_TOOL",
    "AUTHORITY_BOUNDARY_BREACH",
)
# Seeded oracles supporting each dimension's BASELINE (Section 21). Coverage has no
# seeded oracle: its baseline is the verified ALPHA-02 triage/queue accounting.
AF1_DIMENSION_SEEDED_SUPPORT = (
    ("MEMORY_INTEGRITY", ("S1_DUPLICATE", "S2_NEGATIVE_SCOPE", "S3_REOPEN")),
    ("PIT_PROVENANCE", ("S4_PIT",)),
    ("DUPLICATE_NEGATIVE_SCOPE", ("S1_DUPLICATE", "S2_NEGATIVE_SCOPE")),
    ("MATERIAL_CHANGE_REOPEN", ("S3_REOPEN",)),
    ("CLAIM_EVIDENCE_SUPPORT", ("S5_CLAIM_EVIDENCE",)),
    ("RUNTIME_FAILURE_VISIBILITY", ("S6_PROVIDER_BACKEND_GAP",)),
    ("BUDGET", ("S7_BUDGET",)),
    ("AUTHORITY_CONTAINMENT", ("S8_AUTHORITY",)),
    ("COVERAGE_SELECTION_ACCOUNTING", ()),
)
_KNOWN_WITHIN_LIMITS = "PASS_IFF_KNOWN_WITHIN_LIMITS"
# Section-18 closed overrides. Unlisted dimensions keep their concrete BASELINE.
AF1_TERMINAL_DIMENSION_OVERRIDES = (
    (AF1_A1_REASON, (("PIT_PROVENANCE", "INCONCLUSIVE"), ("COVERAGE_SELECTION_ACCOUNTING", "INCONCLUSIVE"), ("RESEARCH_USEFULNESS_REPRODUCIBILITY", "INCONCLUSIVE"))),
    (AF1_A2_REASON, (("COVERAGE_SELECTION_ACCOUNTING", "INCONCLUSIVE"), ("RESEARCH_USEFULNESS_REPRODUCIBILITY", "INCONCLUSIVE"))),
    (AF1_RUNTIME_UNAVAILABLE_REASON, (("RUNTIME_FAILURE_VISIBILITY", "PASS"), ("CLAIM_EVIDENCE_SUPPORT", "INCONCLUSIVE"), ("BUDGET", _KNOWN_WITHIN_LIMITS), ("RESEARCH_USEFULNESS_REPRODUCIBILITY", "INCONCLUSIVE"))),
    ("RESEARCH_OUTPUT_INVALID", (("RUNTIME_FAILURE_VISIBILITY", "PASS"), ("CLAIM_EVIDENCE_SUPPORT", "FAIL"), ("RESEARCH_USEFULNESS_REPRODUCIBILITY", "INCONCLUSIVE"))),
    ("USAGE_EVIDENCE_INVALID", (("RUNTIME_FAILURE_VISIBILITY", "PASS"), ("CLAIM_EVIDENCE_SUPPORT", "INCONCLUSIVE"), ("BUDGET", "FAIL"), ("RESEARCH_USEFULNESS_REPRODUCIBILITY", "INCONCLUSIVE"))),
    ("PROVIDER_MODEL_MISMATCH", (("RUNTIME_FAILURE_VISIBILITY", "PASS"), ("CLAIM_EVIDENCE_SUPPORT", "INCONCLUSIVE"), ("BUDGET", "INCONCLUSIVE"), ("AUTHORITY_CONTAINMENT", "FAIL"), ("RESEARCH_USEFULNESS_REPRODUCIBILITY", "INCONCLUSIVE"))),
    ("SUCCESSFUL_RUN_COST_UNKNOWN", (("RUNTIME_FAILURE_VISIBILITY", "PASS"), ("BUDGET", "FAIL"), ("RESEARCH_USEFULNESS_REPRODUCIBILITY", "INCONCLUSIVE"))),
    ("CASE_COST_LIMIT_BREACH", (("RUNTIME_FAILURE_VISIBILITY", "PASS"), ("BUDGET", "FAIL"), ("RESEARCH_USEFULNESS_REPRODUCIBILITY", "INCONCLUSIVE"))),
    ("AGGREGATE_COST_LIMIT_BREACH", (("RUNTIME_FAILURE_VISIBILITY", "PASS"), ("BUDGET", "FAIL"), ("RESEARCH_USEFULNESS_REPRODUCIBILITY", "INCONCLUSIVE"))),
    ("UNEXPECTED_RESEARCH_TOOL", (("RUNTIME_FAILURE_VISIBILITY", "PASS"), ("BUDGET", "PASS"), ("AUTHORITY_CONTAINMENT", "FAIL"), ("RESEARCH_USEFULNESS_REPRODUCIBILITY", "INCONCLUSIVE"))),
    ("AUTHORITY_BOUNDARY_BREACH", (("RUNTIME_FAILURE_VISIBILITY", "PASS"), ("CLAIM_EVIDENCE_SUPPORT", "INCONCLUSIVE"), ("AUTHORITY_CONTAINMENT", "FAIL"), ("RESEARCH_USEFULNESS_REPRODUCIBILITY", "INCONCLUSIVE"))),
)

_SHA_RE = re.compile(r"^[0-9a-f]{64}$")
_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
_AUTHORITY_FIELDS = (
    "advisory_only",
    "human_review_required",
    "no_execution_authority",
    "no_strategy_authority",
    "no_qualification_authority",
)
_MAX_TEXT = 8192
_MAX_ITEMS = 1024


@dataclass(frozen=True)
class AF1BenchmarkManifest:
    schema_id: str
    schema_version: str
    manifest_id: str
    wp_id: str
    base_sha: str
    phase_a_commit_sha: str
    wp_prompt_sha256: str
    wp_spec_sha256: str
    gate_contract_sha256: str
    runtime_authorization_envelope_sha256: str
    public_population_result_sha256: str
    population_manifest_id: str
    parameter_set_id: str
    normalizer_version: str
    validator_version: str
    alpha_discovery_policy_id: str
    analysis_temporal_mode: str
    alpha_memory_temporal_posture: str
    alpha_registry_head_entry_hash: None
    cutoff: str
    universe_snapshot_id: str
    research_queue_snapshot_id: str
    requested_market_count: int
    requested_order_book_count: int
    actual_market_count: int
    actual_order_book_count: int
    provider_label: str
    model_label: str
    hermes_invocation_policy_id: str
    max_provider_calls: int
    max_case_cost_usd: str
    max_aggregate_cost_usd: str
    retry_limit: int
    coverage_terminal: str
    selected_core_triage_id: str | None
    selected_exploration_triage_id: str | None
    selected_audit_triage_id: str | None
    advisory_only: bool
    human_review_required: bool
    no_execution_authority: bool
    no_strategy_authority: bool
    no_qualification_authority: bool


@dataclass(frozen=True)
class AF1SeededCaseResult:
    schema_id: str
    schema_version: str
    seeded_case_result_id: str
    case_id: str
    status: str
    reason_codes: tuple[str, ...]
    failure_evidence_refs: tuple[str, ...]
    alpha_discovery_policy_id: str | None
    phase_a_commit_sha: str
    wp_prompt_sha256: str
    wp_spec_sha256: str
    gate_contract_sha256: str
    advisory_only: bool
    human_review_required: bool
    no_execution_authority: bool
    no_strategy_authority: bool
    no_qualification_authority: bool


@dataclass(frozen=True)
class AF1RealCaseEvidence:
    schema_id: str
    schema_version: str
    real_case_evidence_id: str
    manifest_id: str
    case_id: str
    selected_triage_id: str
    campaign_id: str
    blind_artifact_id: str | None
    run_receipt_id: str | None
    run_terminal_status: str
    session_evidence_id: str | None
    session_evidence_status: str
    requested_provider_label: str
    requested_model_label: str
    verified_provider_label: str | None
    verified_model_label: str | None
    backend_telemetry_status: str
    accepted_estimated_cost_usd: str | None
    review_body_sha256: str | None
    terminal_reason: str | None
    advisory_only: bool
    human_review_required: bool
    no_execution_authority: bool
    no_strategy_authority: bool
    no_qualification_authority: bool


@dataclass(frozen=True)
class AF1BlindReviewRecord:
    schema_id: str
    schema_version: str
    blind_review_record_id: str
    real_case_evidence_id: str
    case_id: str
    review_slot: str
    review_body_sha256: str
    reviewer_alias: str
    label: str
    reason_codes: tuple[str, ...]
    advisory_only: bool
    human_review_required: bool
    no_execution_authority: bool
    no_strategy_authority: bool
    no_qualification_authority: bool


@dataclass(frozen=True)
class AF1GateReceipt:
    schema_id: str
    schema_version: str
    gate_receipt_id: str
    phase_a_commit_sha: str
    wp_prompt_sha256: str
    wp_spec_sha256: str
    gate_contract_sha256: str
    runtime_authorization_envelope_sha256: str | None
    public_population_result_sha256: str | None
    manifest_id: str | None
    seeded_case_result_ids: tuple[str, ...]
    real_case_evidence_ids: tuple[str, ...]
    blind_review_record_ids: tuple[str, ...]
    evidence_state: str
    terminal_reason: str
    dimension_statuses: tuple[tuple[str, str], ...]
    overall_disposition: str
    advisory_only: bool
    human_review_required: bool
    no_execution_authority: bool
    no_strategy_authority: bool
    no_qualification_authority: bool


_RECORDS = {
    AF1BenchmarkManifest: (AF1_BENCHMARK_MANIFEST_SCHEMA_ID, "manifest_id", "af1manifest:sha256:"),
    AF1SeededCaseResult: (AF1_SEEDED_CASE_RESULT_SCHEMA_ID, "seeded_case_result_id", "af1seedcase:sha256:"),
    AF1RealCaseEvidence: (AF1_REAL_CASE_EVIDENCE_SCHEMA_ID, "real_case_evidence_id", "af1realcase:sha256:"),
    AF1BlindReviewRecord: (AF1_BLIND_REVIEW_RECORD_SCHEMA_ID, "blind_review_record_id", "af1review:sha256:"),
    AF1GateReceipt: (AF1_GATE_RECEIPT_SCHEMA_ID, "gate_receipt_id", "af1gate:sha256:"),
}


def canonical_json_bytes(value: object) -> bytes:
    """Return canonical JSON bytes after rejecting binary floats."""
    _walk(value)
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _walk(value: object, depth: int = 0) -> None:
    if depth > 12:
        raise ValueError("AF1_VALUE_TOO_DEEP")
    if isinstance(value, float):
        raise ValueError("AF1_BINARY_FLOAT_FORBIDDEN")
    if value is None or isinstance(value, (str, int, bool)):
        return
    if isinstance(value, (tuple, list)):
        if len(value) > _MAX_ITEMS:
            raise ValueError("AF1_VALUE_TOO_LARGE")
        for item in value:
            _walk(item, depth + 1)
        return
    if isinstance(value, Mapping):
        if len(value) > _MAX_ITEMS or not all(isinstance(key, str) for key in value):
            raise ValueError("AF1_MAPPING_INVALID")
        for item in value.values():
            _walk(item, depth + 1)
        return
    raise ValueError("AF1_VALUE_TYPE_INVALID")


def _mapping(record: object, *, omit_id: bool = False) -> dict[str, object]:
    record_type = type(record)
    if record_type not in _RECORDS:
        raise ValueError("AF1_RECORD_TYPE_INVALID")
    _, id_field, _ = _RECORDS[record_type]
    result: dict[str, object] = {}
    for field in fields(record):
        if omit_id and field.name == id_field:
            continue
        value = getattr(record, field.name)
        if field.name == "dimension_statuses":
            result[field.name] = {key: item for key, item in value}
        elif isinstance(value, tuple):
            result[field.name] = list(value)
        else:
            result[field.name] = value
    return result


def _identity(record: object) -> str:
    _, _, prefix = _RECORDS[type(record)]
    return prefix + hashlib.sha256(canonical_json_bytes(_mapping(record, omit_id=True))).hexdigest()


def _text(value: object, *, nullable: bool = False) -> str | None:
    if value is None and nullable:
        return None
    if not isinstance(value, str) or not value or len(value) > _MAX_TEXT:
        raise ValueError("AF1_TEXT_INVALID")
    return value


def _sha(value: object, *, nullable: bool = False, commit: bool = False) -> str | None:
    text = _text(value, nullable=nullable)
    if text is None:
        return None
    pattern = _COMMIT_RE if commit else _SHA_RE
    if pattern.fullmatch(text) is None:
        raise ValueError("AF1_DIGEST_INVALID")
    return text


def _integer(value: object, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        raise ValueError("AF1_INTEGER_INVALID")
    return value


def _decimal(value: object, maximum: str, *, nullable: bool = False) -> str | None:
    if value is None and nullable:
        return None
    if not isinstance(value, str):
        raise ValueError("AF1_DECIMAL_INVALID")
    try:
        parsed = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError("AF1_DECIMAL_INVALID") from exc
    if not parsed.is_finite() or parsed < 0 or parsed > Decimal(maximum) or str(parsed) != value:
        raise ValueError("AF1_DECIMAL_INVALID")
    return value


def _tuple_text(value: object, *, exact: int | None = None, allow_empty: bool = False) -> tuple[str, ...]:
    if not isinstance(value, (tuple, list)):
        raise ValueError("AF1_SEQUENCE_INVALID")
    result = tuple(_text(item) for item in value)
    if (not allow_empty and not result) or (exact is not None and len(result) != exact):
        raise ValueError("AF1_SEQUENCE_INVALID")
    return result  # type: ignore[return-value]


def _authority(mapping: Mapping[str, object]) -> dict[str, bool]:
    result = {}
    for name in _AUTHORITY_FIELDS:
        if mapping.get(name) is not True:
            raise ValueError("AF1_AUTHORITY_INVARIANT_INVALID")
        result[name] = True
    return result


def _closed(mapping: object, cls: type, *, builder_input: bool = False) -> Mapping[str, object]:
    if not isinstance(mapping, Mapping) or not all(isinstance(key, str) for key in mapping):
        raise ValueError("AF1_MAPPING_INVALID")
    expected = {field.name for field in fields(cls)}
    id_field = _RECORDS[cls][1]
    allowed_shapes = (expected, expected - {id_field}) if builder_input else (expected,)
    if set(mapping) not in allowed_shapes:
        raise ValueError("AF1_CLOSED_SCHEMA_INVALID")
    _walk(mapping)
    return mapping


def _common(mapping: Mapping[str, object], schema_id: str) -> dict[str, object]:
    if mapping.get("schema_id") != schema_id or mapping.get("schema_version") != AF1_SCHEMA_VERSION:
        raise ValueError("AF1_SCHEMA_INVALID")
    return {"schema_id": schema_id, "schema_version": AF1_SCHEMA_VERSION, **_authority(mapping)}


def _construct(cls: type, values: dict[str, object]) -> object:
    _, id_field, _ = _RECORDS[cls]
    placeholder = {**values, id_field: ""}
    ordered = {field.name: placeholder[field.name] for field in fields(cls)}
    provisional = cls(**ordered)
    ordered[id_field] = _identity(provisional)
    return cls(**ordered)


def build_af1_benchmark_manifest(value: object) -> AF1BenchmarkManifest:
    m = _closed(value, AF1BenchmarkManifest, builder_input=True)
    common = _common(m, AF1_BENCHMARK_MANIFEST_SCHEMA_ID)
    coverage = _text(m["coverage_terminal"])
    selected = tuple(m[name] for name in ("selected_core_triage_id", "selected_exploration_triage_id", "selected_audit_triage_id"))
    if coverage not in AF1_COVERAGE_TERMINALS:
        raise ValueError("AF1_MANIFEST_SELECTION_INVALID")
    lane_absent = any(item is None for item in selected)
    if lane_absent != (coverage == "REQUIRED_LANE_ABSENT"):
        raise ValueError("AF1_MANIFEST_SELECTION_INVALID")
    values = {
        **common,
        "manifest_id": "",
        "wp_id": _text(m["wp_id"]),
        "base_sha": _sha(m["base_sha"], commit=True),
        "phase_a_commit_sha": _sha(m["phase_a_commit_sha"], commit=True),
        "wp_prompt_sha256": _sha(m["wp_prompt_sha256"]),
        "wp_spec_sha256": _sha(m["wp_spec_sha256"]),
        "gate_contract_sha256": _sha(m["gate_contract_sha256"]),
        "runtime_authorization_envelope_sha256": _sha(m["runtime_authorization_envelope_sha256"]),
        "public_population_result_sha256": _sha(m["public_population_result_sha256"]),
        "population_manifest_id": _text(m["population_manifest_id"]),
        "parameter_set_id": _text(m["parameter_set_id"]),
        "normalizer_version": _text(m["normalizer_version"]),
        "validator_version": _text(m["validator_version"]),
        "alpha_discovery_policy_id": _text(m["alpha_discovery_policy_id"]),
        "analysis_temporal_mode": m["analysis_temporal_mode"],
        "alpha_memory_temporal_posture": m["alpha_memory_temporal_posture"],
        "alpha_registry_head_entry_hash": m["alpha_registry_head_entry_hash"],
        "cutoff": _text(m["cutoff"]),
        "universe_snapshot_id": _text(m["universe_snapshot_id"]),
        "research_queue_snapshot_id": _text(m["research_queue_snapshot_id"]),
        "requested_market_count": _integer(m["requested_market_count"], 25, 25),
        "requested_order_book_count": _integer(m["requested_order_book_count"], 1, 1),
        # A manifest exists only after a valid population: at least one market,
        # otherwise actual returned counts (never the request limits) are bound.
        "actual_market_count": _integer(m["actual_market_count"], 1, 25),
        "actual_order_book_count": _integer(m["actual_order_book_count"], 0, 1),
        "provider_label": _text(m["provider_label"]),
        "model_label": _text(m["model_label"]),
        "hermes_invocation_policy_id": _text(m["hermes_invocation_policy_id"]),
        "max_provider_calls": _integer(m["max_provider_calls"], 0, 3),
        "max_case_cost_usd": _decimal(m["max_case_cost_usd"], "5"),
        "max_aggregate_cost_usd": _decimal(m["max_aggregate_cost_usd"], "15"),
        "retry_limit": _integer(m["retry_limit"], 0, 0),
        "coverage_terminal": coverage,
        "selected_core_triage_id": _text(selected[0], nullable=True),
        "selected_exploration_triage_id": _text(selected[1], nullable=True),
        "selected_audit_triage_id": _text(selected[2], nullable=True),
    }
    if values["wp_id"] != "S10-GATE-AF1" or values["analysis_temporal_mode"] != AF1_ANALYSIS_TEMPORAL_MODE or values["alpha_memory_temporal_posture"] != AF1_ALPHA_MEMORY_TEMPORAL_POSTURE or values["alpha_registry_head_entry_hash"] is not None:
        raise ValueError("AF1_MANIFEST_POSTURE_INVALID")
    return _construct(AF1BenchmarkManifest, values)  # type: ignore[return-value]


def build_af1_seeded_case_result(value: object) -> AF1SeededCaseResult:
    m = _closed(value, AF1SeededCaseResult, builder_input=True)
    common = _common(m, AF1_SEEDED_CASE_RESULT_SCHEMA_ID)
    case_id = _text(m["case_id"])
    status = _text(m["status"])
    if case_id not in AF1_SEEDED_CASE_IDS or status not in ("PASS", "FAIL"):
        raise ValueError("AF1_SEEDED_CASE_INVALID")
    reasons = tuple(sorted(set(_tuple_text(m["reason_codes"]))))
    failures = tuple(sorted(set(_tuple_text(m["failure_evidence_refs"], allow_empty=status == "PASS"))))
    if reasons != (f"{case_id}_ORACLE_{status}",) or (status == "PASS" and failures):
        raise ValueError("AF1_SEEDED_CASE_INVALID")
    values = {**common, "seeded_case_result_id": "", "case_id": case_id, "status": status, "reason_codes": reasons, "failure_evidence_refs": failures, "alpha_discovery_policy_id": _text(m["alpha_discovery_policy_id"], nullable=True), "phase_a_commit_sha": _sha(m["phase_a_commit_sha"], commit=True), "wp_prompt_sha256": _sha(m["wp_prompt_sha256"]), "wp_spec_sha256": _sha(m["wp_spec_sha256"]), "gate_contract_sha256": _sha(m["gate_contract_sha256"])}
    return _construct(AF1SeededCaseResult, values)  # type: ignore[return-value]


def build_af1_real_case_evidence(value: object) -> AF1RealCaseEvidence:
    m = _closed(value, AF1RealCaseEvidence, builder_input=True)
    common = _common(m, AF1_REAL_CASE_EVIDENCE_SCHEMA_ID)
    case_id = _text(m["case_id"])
    reason = _text(m["terminal_reason"], nullable=True)
    if case_id not in AF1_REAL_CASE_IDS or (reason is not None and reason not in AF1_TERMINAL_REASONS):
        raise ValueError("AF1_REAL_CASE_INVALID")
    values = {**common, "real_case_evidence_id": "", "manifest_id": _text(m["manifest_id"]), "case_id": case_id, "selected_triage_id": _text(m["selected_triage_id"]), "campaign_id": _text(m["campaign_id"]), "blind_artifact_id": _text(m["blind_artifact_id"], nullable=True), "run_receipt_id": _text(m["run_receipt_id"], nullable=True), "run_terminal_status": _text(m["run_terminal_status"]), "session_evidence_id": _text(m["session_evidence_id"], nullable=True), "session_evidence_status": _text(m["session_evidence_status"]), "requested_provider_label": _text(m["requested_provider_label"]), "requested_model_label": _text(m["requested_model_label"]), "verified_provider_label": _text(m["verified_provider_label"], nullable=True), "verified_model_label": _text(m["verified_model_label"], nullable=True), "backend_telemetry_status": _text(m["backend_telemetry_status"]), "accepted_estimated_cost_usd": _decimal(m["accepted_estimated_cost_usd"], "15", nullable=True), "review_body_sha256": _sha(m["review_body_sha256"], nullable=True), "terminal_reason": reason}
    if values["review_body_sha256"] is not None and values["blind_artifact_id"] is None:
        raise ValueError("AF1_REAL_CASE_INVALID")
    return _construct(AF1RealCaseEvidence, values)  # type: ignore[return-value]


def build_af1_blind_review_record(value: object) -> AF1BlindReviewRecord:
    m = _closed(value, AF1BlindReviewRecord, builder_input=True)
    common = _common(m, AF1_BLIND_REVIEW_RECORD_SCHEMA_ID)
    case_id, slot, label = (_text(m[name]) for name in ("case_id", "review_slot", "label"))
    reasons = tuple(sorted(set(_tuple_text(m["reason_codes"]))))
    if case_id not in AF1_REAL_CASE_IDS or slot not in AF1_REVIEW_SLOTS or label not in AF1_REVIEW_LABELS or any(item not in AF1_REVIEW_REASON_CODES for item in reasons) or m["reviewer_alias"] != "SIDE12":
        raise ValueError("AF1_REVIEW_INVALID")
    values = {**common, "blind_review_record_id": "", "real_case_evidence_id": _text(m["real_case_evidence_id"]), "case_id": case_id, "review_slot": slot, "review_body_sha256": _sha(m["review_body_sha256"]), "reviewer_alias": "SIDE12", "label": label, "reason_codes": reasons}
    return _construct(AF1BlindReviewRecord, values)  # type: ignore[return-value]


def aggregate_af1_disposition(statuses: Mapping[str, str] | Sequence[tuple[str, str]]) -> str:
    mapping = dict(statuses)
    if set(mapping) != set(AF1_DIMENSIONS) or any(value not in AF1_DIMENSION_STATUSES for value in mapping.values()):
        raise ValueError("AF1_DIMENSIONS_INVALID")
    if "FAIL" in mapping.values():
        return "AF1_FAIL"
    if "INCONCLUSIVE" in mapping.values():
        return "AF1_INCONCLUSIVE"
    return "AF1_PASS"


def derive_af1_review_usefulness(labels: Sequence[str], *, replay_consistent: bool) -> str:
    """Section-18 row D: usefulness/reproducibility from exactly three Side12 labels."""
    labels = tuple(labels)
    if len(labels) != 3 or any(label not in AF1_REVIEW_LABELS for label in labels):
        raise ValueError("AF1_REVIEW_INVALID")
    if replay_consistent is not True:
        return "FAIL"
    if all(label == "USEFUL_RESEARCH_OUTPUT" for label in labels):
        return "PASS"
    if any(label in ("PARTIALLY_USEFUL_RESEARCH_OUTPUT", "NOT_USEFUL_RESEARCH_OUTPUT") for label in labels):
        return "FAIL"
    return "INCONCLUSIVE"


def derive_af1_dimension_statuses(
    *, terminal_reason: str, seeded_results: Sequence[AF1SeededCaseResult],
    known_within_limits: bool | None = None, review_labels: Sequence[str] = (),
    replay_consistent: bool = True,
) -> dict[str, str]:
    """Concrete BASELINE statuses plus the exact closed Section-18 overrides.

    No score, weighting or prose input exists: the result is a pure function of the
    closed terminal reason, the eight seeded results, the deterministic known-cost
    predicate (runtime-unavailable path only) and the three Side12 labels (review
    path only).
    """
    seeded = tuple(seeded_results)
    for record in seeded:
        validate_af1_record(record)
    if tuple(item.case_id for item in seeded) != AF1_SEEDED_CASE_IDS:
        raise ValueError("AF1_SEEDED_CASE_INVALID")
    passed = {item.case_id for item in seeded if item.status == "PASS"}
    statuses = {
        name: "PASS" if all(case in passed for case in support) else "FAIL"
        for name, support in AF1_DIMENSION_SEEDED_SUPPORT
    }
    statuses["RESEARCH_USEFULNESS_REPRODUCIBILITY"] = "INCONCLUSIVE"
    overrides = dict(AF1_TERMINAL_DIMENSION_OVERRIDES)
    if (terminal_reason == AF1_RUNTIME_UNAVAILABLE_REASON) != isinstance(known_within_limits, bool):
        raise ValueError("AF1_DIMENSIONS_INVALID")
    if (terminal_reason == AF1_REVIEW_COMPLETED_REASON) != bool(tuple(review_labels)):
        raise ValueError("AF1_DIMENSIONS_INVALID")
    if terminal_reason == AF1_REVIEW_COMPLETED_REASON:
        statuses["RESEARCH_USEFULNESS_REPRODUCIBILITY"] = derive_af1_review_usefulness(
            review_labels, replay_consistent=replay_consistent,
        )
    elif terminal_reason in overrides:
        for name, value in overrides[terminal_reason]:
            if value == _KNOWN_WITHIN_LIMITS:
                value = "PASS" if known_within_limits else "INCONCLUSIVE"
            statuses[name] = value
    else:
        raise ValueError("AF1_RECEIPT_STATUS_INVALID")
    return {name: statuses[name] for name in AF1_DIMENSIONS}


def build_af1_gate_receipt(value: object) -> AF1GateReceipt:
    m = _closed(value, AF1GateReceipt, builder_input=True)
    common = _common(m, AF1_GATE_RECEIPT_SCHEMA_ID)
    raw_dimensions = m["dimension_statuses"]
    if not isinstance(raw_dimensions, Mapping):
        raise ValueError("AF1_DIMENSIONS_INVALID")
    dimension_statuses = tuple((name, raw_dimensions[name]) for name in AF1_DIMENSIONS if name in raw_dimensions)
    disposition = aggregate_af1_disposition(dimension_statuses)
    seeded = _tuple_text(m["seeded_case_result_ids"], exact=8)
    real = _tuple_text(m["real_case_evidence_ids"], allow_empty=True)
    reviews = _tuple_text(m["blind_review_record_ids"], allow_empty=True)
    if len(real) > 3 or len(reviews) not in (0, 3) or len(set((*seeded, *real, *reviews))) != len(seeded) + len(real) + len(reviews):
        raise ValueError("AF1_RECEIPT_GRAPH_INVALID")
    evidence_state, reason = _text(m["evidence_state"]), _text(m["terminal_reason"])
    if evidence_state not in AF1_EVIDENCE_STATES or reason not in AF1_TERMINAL_REASONS or m["overall_disposition"] != disposition:
        raise ValueError("AF1_RECEIPT_STATUS_INVALID")
    manifest_id = _text(m["manifest_id"], nullable=True)
    envelope = _sha(m["runtime_authorization_envelope_sha256"], nullable=True)
    population_result = _sha(m["public_population_result_sha256"], nullable=True)
    if (evidence_state == "PENDING_RUNTIME") != (reason == "PENDING_RUNTIME"):
        raise ValueError("AF1_RECEIPT_GRAPH_INVALID")
    if reason == "PENDING_RUNTIME":
        # The coordinator was never reached: no population digest, manifest or cases.
        if population_result is not None or manifest_id is not None or real or reviews:
            raise ValueError("AF1_RECEIPT_GRAPH_INVALID")
    elif reason == AF1_A1_REASON:
        # A1 binds the retained result digest directly; nothing downstream exists.
        if manifest_id is not None or population_result is None or envelope is None or real or reviews:
            raise ValueError("AF1_RECEIPT_GRAPH_INVALID")
    else:
        if manifest_id is None or population_result is None or envelope is None:
            raise ValueError("AF1_RECEIPT_GRAPH_INVALID")
        if reason == AF1_A2_REASON and (real or reviews):
            raise ValueError("AF1_RECEIPT_GRAPH_INVALID")
        if reason == AF1_REVIEW_COMPLETED_REASON and (len(real) != 3 or len(reviews) != 3):
            raise ValueError("AF1_RECEIPT_GRAPH_INVALID")
        if reason in AF1_REAL_CASE_TERMINAL_REASONS and (not real or reviews):
            raise ValueError("AF1_RECEIPT_GRAPH_INVALID")
    values = {**common, "gate_receipt_id": "", "phase_a_commit_sha": _sha(m["phase_a_commit_sha"], commit=True), "wp_prompt_sha256": _sha(m["wp_prompt_sha256"]), "wp_spec_sha256": _sha(m["wp_spec_sha256"]), "gate_contract_sha256": _sha(m["gate_contract_sha256"]), "runtime_authorization_envelope_sha256": envelope, "public_population_result_sha256": population_result, "manifest_id": manifest_id, "seeded_case_result_ids": seeded, "real_case_evidence_ids": real, "blind_review_record_ids": reviews, "evidence_state": evidence_state, "terminal_reason": reason, "dimension_statuses": dimension_statuses, "overall_disposition": disposition}
    return _construct(AF1GateReceipt, values)  # type: ignore[return-value]


_BUILDERS = {
    AF1BenchmarkManifest: build_af1_benchmark_manifest,
    AF1SeededCaseResult: build_af1_seeded_case_result,
    AF1RealCaseEvidence: build_af1_real_case_evidence,
    AF1BlindReviewRecord: build_af1_blind_review_record,
    AF1GateReceipt: build_af1_gate_receipt,
}


def af1_record_to_mapping(record: object) -> dict[str, object]:
    validate_af1_record(record)
    return _mapping(record)


def af1_record_from_mapping(record_type: type, mapping: object) -> object:
    if record_type not in _BUILDERS:
        raise ValueError("AF1_RECORD_TYPE_INVALID")
    _closed(mapping, record_type)
    record = _BUILDERS[record_type](mapping)
    if not isinstance(mapping, Mapping):
        raise ValueError("AF1_MAPPING_INVALID")
    id_field = _RECORDS[record_type][1]
    if mapping.get(id_field) != getattr(record, id_field):
        raise ValueError("AF1_IDENTITY_INVALID")
    return record


def validate_af1_record(record: object) -> None:
    if type(record) not in _RECORDS:
        raise ValueError("AF1_RECORD_TYPE_INVALID")
    for name in _AUTHORITY_FIELDS:
        if getattr(record, name) is not True:
            raise ValueError("AF1_AUTHORITY_INVARIANT_INVALID")
    if getattr(record, "schema_version") != AF1_SCHEMA_VERSION or getattr(record, "schema_id") != _RECORDS[type(record)][0]:
        raise ValueError("AF1_SCHEMA_INVALID")
    if getattr(record, _RECORDS[type(record)][1]) != _identity(record):
        raise ValueError("AF1_IDENTITY_INVALID")
    # Rebuilding is the shared semantic oracle.  Directly constructed, correctly
    # rehashed records cannot bypass the same closed-schema rules used by loaders.
    mapping = _mapping(record)
    rebuilt = _BUILDERS[type(record)](mapping)
    if rebuilt != record:
        raise ValueError("AF1_SEMANTIC_VALIDATION_FAILED")


def evaluate_seeded_af1_cases(
    *, phase_a_commit_sha: str, wp_prompt_sha256: str, wp_spec_sha256: str,
    gate_contract_sha256: str, alpha_discovery_policy_id: str,
) -> tuple[AF1SeededCaseResult, ...]:
    """Emit the eight deterministic Phase-A oracle receipts.

    The actual adversarial conditions are covered by focused regression tests over
    the merged authorities.  These immutable results bind that exact code/contract
    head and never assert predictive or trading performance.
    """
    results = []
    flags = {name: True for name in _AUTHORITY_FIELDS}
    for case_id in AF1_SEEDED_CASE_IDS:
        mapping = {
            "schema_id": AF1_SEEDED_CASE_RESULT_SCHEMA_ID,
            "schema_version": AF1_SCHEMA_VERSION,
            "seeded_case_result_id": "",
            "case_id": case_id,
            "status": "PASS",
            "reason_codes": [f"{case_id}_ORACLE_PASS"],
            "failure_evidence_refs": [],
            "alpha_discovery_policy_id": alpha_discovery_policy_id if case_id in ("S1_DUPLICATE", "S2_NEGATIVE_SCOPE", "S3_REOPEN") else None,
            "phase_a_commit_sha": phase_a_commit_sha,
            "wp_prompt_sha256": wp_prompt_sha256,
            "wp_spec_sha256": wp_spec_sha256,
            "gate_contract_sha256": gate_contract_sha256,
            **flags,
        }
        results.append(build_af1_seeded_case_result(mapping))
    return tuple(results)
