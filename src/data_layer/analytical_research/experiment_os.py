"""WP170 deterministic local/offline experiment-control substrate.

The module records research intent, temporal membership, preregistration, and
evidence.  It is advisory metadata only: no network, strategy, order, paper,
execution, credential, scheduler, or live-trading authority is present.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, fields
from decimal import Decimal, InvalidOperation
from datetime import datetime, timedelta, timezone
import hashlib
import json
import re
from typing import Mapping, Sequence

from ..point_in_time_market_research import (
    DatasetSnapshotReference,
    build_dataset_snapshot_reference,
)
from .research_dataset import (
    ANALYTICAL_DATASET_SCHEMA_ID,
    ANALYTICAL_DATASET_SCHEMA_VERSION,
    ANALYTICAL_LOGICAL_DATASET_ID_PREFIX,
    ANALYTICAL_SCHEMA_VERSION,
    ANALYTICAL_TABLE_ORDER,
    SOURCE_KIND_CANONICAL_PIT,
    AnalyticalDatasetManifest,
    AnalyticalPartitionManifest,
    analytical_canonical_bytes,
)

EXPERIMENT_OS_SCHEMA_VERSION = "1.0.0"
# WP175D external historical research bridge. ExternalDatasetBinding is additive and
# provenance-separated: it never becomes canonical PIT and never fabricates a
# DatasetSnapshotReference or a SOURCE_KIND_CANONICAL_PIT AnalyticalDatasetManifest.
EXTERNAL_DATASET_BINDING_SCHEMA_ID = "polymarket-external-dataset-binding"
EXTERNAL_DATASET_BINDING_SOURCE_KIND = "WP167_EXTERNAL_DATASET_DESCRIPTOR"
EXTERNAL_MEMBER_ID_PREFIX = "externalmember:sha256:"
EXPERIMENT_OS_STATUSES = (
    "EXPERIMENT_RECORD_VALID",
    "EXPERIMENT_LIFECYCLE_VALID",
    "EXPERIMENT_REJECTED",
)
EXPERIMENT_OS_ERROR_CODES = (
    "SCHEMA_UNSUPPORTED",
    "FIELD_MISSING",
    "FIELD_TYPE_INVALID",
    "FIELD_VALUE_INVALID",
    "IDENTITY_DERIVATION_MISMATCH",
    "DATASET_REFERENCE_INVALID",
    "FEATURE_TIMING_LEAKAGE",
    "LABEL_TIMING_INVALID",
    "SPLIT_INVALID",
    "PURGE_EMBARGO_VIOLATION",
    "GROUP_LEAKAGE_VIOLATION",
    "PREREGISTRATION_STATE_INVALID",
    "OOS_SEALED_EXPOSURE_VIOLATION",
    "TRIAL_FAMILY_CONFLICT",
    "REGISTRY_SCHEMA_CONFLICT",
    "REGISTRY_INTEGRITY_TAMPER",
    "LIMIT_EXCEEDED",
    "INTERNAL_VALIDATION_FAILED",
)
_ERROR_ORDER = {code: i for i, code in enumerate(EXPERIMENT_OS_ERROR_CODES)}

RESEARCH_ROLES = ("FORMATION", "SELECTION", "OUT_OF_SAMPLE")
GROUP_POLICIES = ("EXCLUSIVE", "DECLARED_NO_ISOLATION")
CORRECTION_POLICIES = ("SINGLETON", "FAMILY_TRIAL_COUNT")
METRIC_DIRECTIONS = ("HIGHER_IS_BETTER", "LOWER_IS_BETTER")
_BASELINE_ACCEPTANCE_RULES = (
    "CANDIDATE_GTE_BASELINE",
    "CANDIDATE_LTE_BASELINE",
)
UNCERTAINTY_STATES = ("NONE", "INCONCLUSIVE", "INVALIDATED_AFTER_RUN")
EVIDENCE_STATUSES = (
    "EVIDENCE_NEGATIVE",
    "EVIDENCE_INCONCLUSIVE",
    "EVIDENCE_INVALIDATED_AFTER_RUN",
    "FORMATION_CRITERIA_MET",
    "SELECTION_CRITERIA_MET",
    "OOS_CRITERIA_MET_UNCOSTED",
    "OOS_REUSED_DIAGNOSTIC",
)
LIFECYCLE_ACTIONS = (
    "LOCK_PREREGISTRATION",
    "START_FORMATION",
    "START_SELECTION",
    "CLOSE_SELECTION",
    "RELEASE_OOS",
    "CLOSE_EXPERIMENT",
)
LIFECYCLE_STATES = (
    "PREREGISTERED_LOCKED",
    "FORMATION_ACTIVE",
    "SELECTION_ACTIVE",
    "SELECTION_CLOSED",
    "OOS_RELEASED",
    "CLOSED",
)
_TERMINAL_STATUSES = frozenset(
    {"EVIDENCE_NEGATIVE", "EVIDENCE_INCONCLUSIVE", "OOS_CRITERIA_MET_UNCOSTED"}
)

MAX_SAMPLES = 4096
MAX_JSON_BYTES = 262_144
MAX_SEQUENCE_ITEMS = 4096
_MAX_TEXT = 4096
_SHA_RE = re.compile(r"^[0-9a-f]{64}$")
_ID_RE = re.compile(r"^[A-Za-z0-9._:-]{1,512}$")
_UTC_RE = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,6})?Z$"
)
_DECIMAL_RE = re.compile(r"^-?(?:0|[1-9][0-9]*)(?:\.[0-9]*[1-9])?$")


@dataclass(frozen=True)
class DatasetBinding:
    schema_id: str
    schema_version: str
    dataset_binding_id: str
    dataset_snapshot_reference_id: str
    dataset_snapshot_reference_json: str
    dataset_reference_schema_version: str
    analytical_logical_dataset_id: str | None
    analytical_identity_json: str | None
    analytical_schema_version: str | None
    materializer_version: str | None
    source_reference_id: str
    code_version: str
    advisory_only: bool
    no_execution_authority: bool


@dataclass(frozen=True)
class ExternalDatasetBinding:
    """WP175D provenance-separated external-history dataset binding.

    Additive to the canonical :class:`DatasetBinding`. It carries the real source
    availability-time bounds from validated PMXT v2 external history and NEVER
    acquires canonical-PIT authority: ``source_kind`` is the WP167 external
    descriptor kind, no ``DatasetSnapshotReference`` is created, and no local path is
    stored. Persisted under the existing ``DATASET_BINDING`` registry record kind and
    disambiguated from the canonical subtype only by exact ``schema_id``.
    """

    schema_id: str
    schema_version: str
    dataset_binding_id: str
    source_kind: str
    source_external_dataset_id: str
    source_lineage_id: str
    source_membership_digest: str
    source_member_count: int
    instrument_id: str
    conversion_policy_version: str
    first_event_time_ns: int
    last_event_time_ns: int
    first_availability_time_ns: int
    last_availability_time_ns: int
    code_version: str
    advisory_only: bool
    no_execution_authority: bool


@dataclass(frozen=True)
class FeatureDefinition:
    schema_id: str
    schema_version: str
    feature_definition_id: str
    feature_name: str
    feature_version: str
    description: str
    source_dependencies: tuple[str, ...]
    parameters_json: str
    lookback_rule: str
    availability_rule: str
    missing_data_policy: str
    transformation_version: str
    no_future_information_rule: str
    advisory_only: bool
    no_execution_authority: bool


@dataclass(frozen=True)
class LabelDefinition:
    schema_id: str
    schema_version: str
    label_definition_id: str
    label_name: str
    label_version: str
    prediction_target: str
    horizon_rule: str
    target_time_rule: str
    outcome_source_rule: str
    availability_time_rule: str
    censoring_rule: str
    parameters_json: str
    code_version: str
    advisory_only: bool
    no_execution_authority: bool


@dataclass(frozen=True)
class ResearchSample:
    schema_id: str
    schema_version: str
    sample_id: str
    dataset_binding_id: str
    source_record_version_ids: tuple[str, ...]
    source_membership_digest: str
    market_id: str
    related_group_id: str | None
    leakage_group_id: str | None
    decision_time: str
    feature_availability_time: str
    target_time: str
    label_availability_time: str
    feature_set_id: str
    label_definition_id: str
    lineage_digest: str
    advisory_only: bool
    no_execution_authority: bool


@dataclass(frozen=True)
class ResearchDatasetManifest:
    schema_id: str
    schema_version: str
    research_dataset_manifest_id: str
    dataset_binding_id: str
    feature_definition_ids: tuple[str, ...]
    feature_set_id: str
    label_definition_id: str
    group_policy: str
    samples: tuple[ResearchSample, ...]
    total_sample_count: int
    assignment_order: str
    advisory_only: bool
    no_execution_authority: bool


@dataclass(frozen=True)
class TemporalSplitManifest:
    schema_id: str
    schema_version: str
    split_plan_id: str
    split_plan_version: str
    split_assignment_id: str
    dataset_manifest_id: str
    dataset_binding_id: str
    feature_definition_ids: tuple[str, ...]
    feature_set_id: str
    label_definition_id: str
    formation_start: str
    selection_start: str
    oos_start: str
    end_time: str
    purge_rule: str
    embargo_seconds: int
    group_policy: str
    inclusion_policy: str
    min_samples_per_role: int
    formation_sample_ids: tuple[str, ...]
    selection_sample_ids: tuple[str, ...]
    oos_sample_ids: tuple[str, ...]
    purged_sample_ids: tuple[str, ...]
    embargoed_sample_ids: tuple[str, ...]
    assignment_hash: str
    advisory_only: bool
    no_execution_authority: bool


@dataclass(frozen=True)
class AlphaHypothesis:
    schema_id: str
    schema_version: str
    hypothesis_id: str
    hypothesis_name: str
    hypothesis_version: str
    predecessor_candidate_ids: tuple[str, ...]
    falsifiable_claim: str
    proposed_mechanism: str
    cohort: str
    horizon: str
    target: str
    falsification_condition: str
    human_review_state: str
    review_assertion: str
    code_version: str
    creation_provenance: str
    advisory_only: bool
    no_execution_authority: bool


@dataclass(frozen=True)
class MetricDefinition:
    schema_id: str
    schema_version: str
    metric_definition_id: str
    metric_name: str
    metric_version: str
    direction: str
    parameters_json: str
    code_version: str
    advisory_only: bool
    no_execution_authority: bool


@dataclass(frozen=True)
class BaselineDefinition:
    schema_id: str
    schema_version: str
    baseline_definition_id: str
    baseline_name: str
    baseline_version: str
    method_rule: str
    parameters_json: str
    same_partition_required: bool
    acceptance_rule: str
    code_version: str
    advisory_only: bool
    no_execution_authority: bool


@dataclass(frozen=True)
class ExperimentFamily:
    schema_id: str
    schema_version: str
    experiment_family_id: str
    research_program: str
    cohort: str
    target: str
    metric_family: str
    correction_policy: str
    predecessor_family_id: str | None
    advisory_only: bool
    no_execution_authority: bool


@dataclass(frozen=True)
class PreregisteredExperiment:
    schema_id: str
    schema_version: str
    experiment_id: str
    experiment_family_id: str
    trial_number: int
    hypothesis_id: str
    dataset_binding_id: str
    research_dataset_manifest_id: str
    feature_definition_ids: tuple[str, ...]
    feature_set_id: str
    label_definition_id: str
    split_plan_id: str
    split_assignment_id: str
    primary_metric_id: str
    secondary_metric_ids: tuple[str, ...]
    baseline_id: str
    inclusion_exclusion_rules: str
    acceptance_thresholds_json: str
    search_space_json: str
    parameters_json: str
    random_seeds: tuple[int, ...]
    correction_policy: str
    cost_model_reference: str | None
    stop_failure_rules: str
    code_version: str
    creation_provenance: str
    preregistered_at: str
    advisory_only: bool
    no_execution_authority: bool


@dataclass(frozen=True)
class LifecycleReceipt:
    schema_id: str
    schema_version: str
    lifecycle_receipt_id: str
    experiment_id: str
    sequence_number: int
    previous_lifecycle_receipt_id: str | None
    action: str
    from_state: str | None
    to_state: str
    occurred_at: str
    provenance: str
    terminal_result_status: str | None
    advisory_only: bool
    no_execution_authority: bool


@dataclass(frozen=True)
class RunEvidenceReceipt:
    schema_id: str
    schema_version: str
    run_evidence_receipt_id: str
    experiment_id: str
    experiment_family_id: str
    trial_number: int
    dataset_binding_id: str
    research_dataset_manifest_id: str
    split_assignment_id: str
    membership_hash: str
    feature_set_id: str
    label_definition_id: str
    code_version: str
    parameters_json: str
    random_seeds: tuple[int, ...]
    evaluated_role: str
    metric_definition_ids: tuple[str, ...]
    baseline_id: str
    metric_results_json: str
    baseline_results_json: str
    candidate_criterion_met: bool
    baseline_criterion_met: bool
    uncertainty_state: str
    result_status: str
    oos_exposure_ordinal: int
    created_at: str
    creation_provenance: str
    advisory_only: bool
    no_execution_authority: bool


@dataclass(frozen=True)
class FamilySummary:
    schema_id: str
    schema_version: str
    experiment_family_id: str
    registered_experiment_ids: tuple[str, ...]
    trial_numbers: tuple[int, ...]
    evidence_receipt_ids: tuple[str, ...]
    evidence_statuses: tuple[str, ...]
    trial_statuses: tuple[str, ...]
    registered_trial_count: int
    evaluated_trial_count: int
    negative_trial_count: int
    inconclusive_trial_count: int
    advisory_only: bool
    no_execution_authority: bool


@dataclass(frozen=True)
class ExperimentControlResult:
    is_valid: bool
    status: str
    error_codes: tuple[str, ...]
    record: object | None
    advisory_only: bool
    no_execution_authority: bool


class _Failure(Exception):
    def __init__(self, code: str):
        self.code = code


def _ordered(codes: Sequence[str]) -> tuple[str, ...]:
    return tuple(sorted(set(codes), key=lambda code: _ERROR_ORDER.get(code, 999)))


def _rejected(*codes: str) -> ExperimentControlResult:
    return ExperimentControlResult(False, "EXPERIMENT_REJECTED", _ordered(codes), None, True, True)


def _valid(record: object, status: str = "EXPERIMENT_RECORD_VALID") -> ExperimentControlResult:
    return ExperimentControlResult(True, status, (), record, True, True)


def _text(value: object, *, nullable: bool = False) -> str | None:
    if nullable and value is None:
        return None
    if not isinstance(value, str):
        raise _Failure("FIELD_TYPE_INVALID")
    if not value or value != value.strip() or len(value) > _MAX_TEXT or "\x00" in value:
        raise _Failure("FIELD_VALUE_INVALID")
    return value


def _opaque(value: object, *, nullable: bool = False) -> str | None:
    text = _text(value, nullable=nullable)
    if text is not None and _ID_RE.fullmatch(text) is None:
        raise _Failure("FIELD_VALUE_INVALID")
    return text


def _sha(value: object) -> str:
    if not isinstance(value, str):
        raise _Failure("FIELD_TYPE_INVALID")
    if _SHA_RE.fullmatch(value) is None:
        raise _Failure("FIELD_VALUE_INVALID")
    return value


def _utc(value: object) -> str:
    if not isinstance(value, str):
        raise _Failure("FIELD_TYPE_INVALID")
    if _UTC_RE.fullmatch(value) is None:
        raise _Failure("FIELD_VALUE_INVALID")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        raise _Failure("FIELD_VALUE_INVALID") from None
    if parsed.tzinfo != timezone.utc:
        raise _Failure("FIELD_VALUE_INVALID")
    return value


def _dt(value: str) -> datetime:
    return datetime.fromisoformat(value[:-1] + "+00:00")


def _mapping(value: object, keys: frozenset[str]) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise _Failure("FIELD_TYPE_INVALID")
    actual = set(value.keys())
    if any(not isinstance(key, str) for key in actual):
        raise _Failure("FIELD_TYPE_INVALID")
    if keys - actual:
        raise _Failure("FIELD_MISSING")
    if actual - keys:
        raise _Failure("FIELD_VALUE_INVALID")
    return value


def _normalize_json(value: object, depth: int = 0) -> object:
    if depth > 12:
        raise _Failure("LIMIT_EXCEEDED")
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    if isinstance(value, str):
        if len(value) > _MAX_TEXT or "\x00" in value:
            raise _Failure("FIELD_VALUE_INVALID")
        return value
    if isinstance(value, Mapping):
        if len(value) > 256:
            raise _Failure("LIMIT_EXCEEDED")
        normalized: dict[str, object] = {}
        for key in value:
            if not isinstance(key, str) or not key or len(key) > 256:
                raise _Failure("FIELD_TYPE_INVALID" if not isinstance(key, str) else "FIELD_VALUE_INVALID")
            normalized[key] = _normalize_json(value[key], depth + 1)
        return normalized
    if isinstance(value, (list, tuple)):
        if len(value) > 256:
            raise _Failure("LIMIT_EXCEEDED")
        return [_normalize_json(item, depth + 1) for item in value]
    raise _Failure("FIELD_TYPE_INVALID")


def _canonical_bytes(value: object) -> bytes:
    try:
        raw = json.dumps(
            _normalize_json(value), ensure_ascii=False, separators=(",", ":"),
            sort_keys=True, allow_nan=False,
        ).encode("utf-8")
    except _Failure:
        raise
    except (TypeError, ValueError, UnicodeError):
        raise _Failure("FIELD_VALUE_INVALID") from None
    if len(raw) > MAX_JSON_BYTES:
        raise _Failure("LIMIT_EXCEEDED")
    return raw


def _canonical_json(value: object) -> str:
    return _canonical_bytes(value).decode("utf-8")


def _canonical_mapping_json(value: object) -> str:
    if not isinstance(value, Mapping):
        raise _Failure("FIELD_TYPE_INVALID")
    return _canonical_json(value)


def _validate_canonical_mapping_json(value: object) -> str:
    if not isinstance(value, str):
        raise _Failure("FIELD_TYPE_INVALID")
    try:
        decoded = json.loads(
            value,
            parse_constant=lambda _: (_ for _ in ()).throw(ValueError()),
        )
    except (TypeError, ValueError, UnicodeError):
        raise _Failure("FIELD_VALUE_INVALID") from None
    if not isinstance(decoded, Mapping) or _canonical_mapping_json(decoded) != value:
        raise _Failure("FIELD_VALUE_INVALID")
    return value


def _decimal(value: object) -> Decimal:
    if not isinstance(value, str) or not _DECIMAL_RE.fullmatch(value) or value == "-0":
        raise _Failure("FIELD_VALUE_INVALID")
    try:
        parsed = Decimal(value)
    except InvalidOperation:
        raise _Failure("FIELD_VALUE_INVALID") from None
    if not parsed.is_finite():
        raise _Failure("FIELD_VALUE_INVALID")
    return parsed


def _threshold_mapping(value: object, direction: str | None = None) -> dict[str, str]:
    mapping = _mapping(value, frozenset({"primary_metric_operator", "primary_metric_threshold"}))
    operator = _enum(mapping["primary_metric_operator"], ("GTE", "LTE"))
    threshold = _text(mapping["primary_metric_threshold"])
    _decimal(threshold)
    if direction is not None and (
        (direction == "HIGHER_IS_BETTER" and operator != "GTE")
        or (direction == "LOWER_IS_BETTER" and operator != "LTE")
    ):
        raise _Failure("FIELD_VALUE_INVALID")
    return {"primary_metric_operator": operator, "primary_metric_threshold": threshold}


def _digest(kind: str, prefix: str, preimage: Mapping[str, object]) -> str:
    wrapped = {f"{kind}.identity_preimage": preimage}
    return prefix + hashlib.sha256(_canonical_bytes(wrapped)).hexdigest()


def _plain(record: object) -> dict[str, object]:
    return {field.name: getattr(record, field.name) for field in fields(record)}


def _schema(kind: str) -> str:
    return f"polymarket-{kind.replace('_', '-')}"


def _tuple_text(value: object, *, allow_empty: bool = False, sort_values: bool = True) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        raise _Failure("FIELD_TYPE_INVALID")
    if (not allow_empty and not value) or len(value) > MAX_SEQUENCE_ITEMS:
        raise _Failure("FIELD_VALUE_INVALID" if not value else "LIMIT_EXCEEDED")
    out = tuple(_opaque(item) for item in value)
    if len(set(out)) != len(out):
        raise _Failure("FIELD_VALUE_INVALID")
    return tuple(sorted(out)) if sort_values else out


def _tuple_int(value: object) -> tuple[int, ...]:
    if not isinstance(value, (list, tuple)):
        raise _Failure("FIELD_TYPE_INVALID")
    if len(value) > 256:
        raise _Failure("LIMIT_EXCEEDED")
    if any(not isinstance(item, int) or isinstance(item, bool) or item < 0 for item in value):
        raise _Failure("FIELD_TYPE_INVALID")
    out = tuple(value)
    if len(set(out)) != len(out) or out != tuple(sorted(out)):
        raise _Failure("FIELD_VALUE_INVALID")
    return out


def _enum(value: object, allowed: Sequence[str]) -> str:
    if not isinstance(value, str):
        raise _Failure("FIELD_TYPE_INVALID")
    if value not in allowed:
        raise _Failure("FIELD_VALUE_INVALID")
    return value


def _analytical_identity(manifest: AnalyticalDatasetManifest) -> str:
    if (
        manifest.schema_id != ANALYTICAL_DATASET_SCHEMA_ID
        or manifest.schema_version != ANALYTICAL_DATASET_SCHEMA_VERSION
        or manifest.source_kind != SOURCE_KIND_CANONICAL_PIT
        or manifest.analytical_schema_version != ANALYTICAL_SCHEMA_VERSION
        or manifest.advisory_only is not True
        or manifest.no_execution_authority is not True
        or not isinstance(manifest.partition_manifests, tuple)
        or len(manifest.partition_manifests) != len(ANALYTICAL_TABLE_ORDER)
        or not isinstance(manifest.total_row_count, int)
        or isinstance(manifest.total_row_count, bool)
        or manifest.total_row_count < 0
    ):
        raise _Failure("DATASET_REFERENCE_INVALID")
    tables = []
    total_rows = 0
    for expected_name, partition in zip(
        ANALYTICAL_TABLE_ORDER, manifest.partition_manifests, strict=True,
    ):
        if (
            not isinstance(partition, AnalyticalPartitionManifest)
            or partition.table_name != expected_name
            or not isinstance(partition.row_count, int)
            or isinstance(partition.row_count, bool)
            or partition.row_count < 0
        ):
            raise _Failure("DATASET_REFERENCE_INVALID")
        _sha(partition.logical_rows_sha256)
        total_rows += partition.row_count
        tables.append({
            "table_name": partition.table_name,
            "row_count": partition.row_count,
            "logical_rows_sha256": partition.logical_rows_sha256,
        })
    if total_rows != manifest.total_row_count:
        raise _Failure("DATASET_REFERENCE_INVALID")
    _opaque(manifest.source_reference_id)
    _text(manifest.materializer_version)
    preimage = {
        "analytical_schema_id": ANALYTICAL_DATASET_SCHEMA_ID,
        "analytical_schema_version": ANALYTICAL_SCHEMA_VERSION,
        "source_kind": SOURCE_KIND_CANONICAL_PIT,
        "source_reference_id": manifest.source_reference_id,
        "materializer_version": manifest.materializer_version,
        "tables": tables,
    }
    return ANALYTICAL_LOGICAL_DATASET_ID_PREFIX + hashlib.sha256(
        analytical_canonical_bytes(preimage)
    ).hexdigest()


def _analytical_identity_payload(manifest: AnalyticalDatasetManifest) -> dict[str, object]:
    """Return the exact logical-identity preimage, excluding physical/local metadata."""
    _analytical_identity(manifest)
    return {
        "analytical_schema_id": ANALYTICAL_DATASET_SCHEMA_ID,
        "analytical_schema_version": ANALYTICAL_SCHEMA_VERSION,
        "source_kind": SOURCE_KIND_CANONICAL_PIT,
        "source_reference_id": manifest.source_reference_id,
        "materializer_version": manifest.materializer_version,
        "tables": [
            {
                "table_name": partition.table_name,
                "row_count": partition.row_count,
                "logical_rows_sha256": partition.logical_rows_sha256,
            }
            for partition in manifest.partition_manifests
        ],
    }


def _decode_dataset_reference_json(value: object) -> DatasetSnapshotReference:
    canonical = _validate_canonical_mapping_json(value)
    try:
        decoded = json.loads(canonical)
    except (TypeError, ValueError, UnicodeError):
        raise _Failure("DATASET_REFERENCE_INVALID") from None
    if set(decoded) != {field.name for field in fields(DatasetSnapshotReference)}:
        raise _Failure("DATASET_REFERENCE_INVALID")
    rebuilt = build_dataset_snapshot_reference(decoded)
    if not rebuilt.is_valid or rebuilt.reference is None or _canonical_json(_plain(rebuilt.reference)) != canonical:
        raise _Failure("DATASET_REFERENCE_INVALID")
    return rebuilt.reference


def _validate_analytical_identity_json(value: object, logical_id: str) -> str:
    canonical = _validate_canonical_mapping_json(value)
    try:
        decoded = json.loads(canonical)
    except (TypeError, ValueError, UnicodeError):
        raise _Failure("DATASET_REFERENCE_INVALID") from None
    if set(decoded) != {
        "analytical_schema_id", "analytical_schema_version", "source_kind",
        "source_reference_id", "materializer_version", "tables",
    }:
        raise _Failure("DATASET_REFERENCE_INVALID")
    tables = decoded.get("tables")
    if not isinstance(tables, list) or len(tables) != len(ANALYTICAL_TABLE_ORDER):
        raise _Failure("DATASET_REFERENCE_INVALID")
    normalized_tables: list[dict[str, object]] = []
    for expected_name, table in zip(ANALYTICAL_TABLE_ORDER, tables, strict=True):
        if not isinstance(table, Mapping) or set(table) != {"table_name", "row_count", "logical_rows_sha256"}:
            raise _Failure("DATASET_REFERENCE_INVALID")
        if table["table_name"] != expected_name or not isinstance(table["row_count"], int) or isinstance(table["row_count"], bool) or table["row_count"] < 0:
            raise _Failure("DATASET_REFERENCE_INVALID")
        _sha(table["logical_rows_sha256"])
        normalized_tables.append(dict(table))
    if decoded["analytical_schema_id"] != ANALYTICAL_DATASET_SCHEMA_ID or decoded["analytical_schema_version"] != ANALYTICAL_SCHEMA_VERSION or decoded["source_kind"] != SOURCE_KIND_CANONICAL_PIT:
        raise _Failure("DATASET_REFERENCE_INVALID")
    _opaque(decoded["source_reference_id"])
    _text(decoded["materializer_version"])
    recomputed = ANALYTICAL_LOGICAL_DATASET_ID_PREFIX + hashlib.sha256(
        analytical_canonical_bytes(decoded)
    ).hexdigest()
    if recomputed != logical_id:
        raise _Failure("DATASET_REFERENCE_INVALID")
    return canonical


def build_dataset_binding(
    reference: object, analytical_manifest: object, code_version: object
) -> ExperimentControlResult:
    try:
        if not isinstance(reference, DatasetSnapshotReference):
            raise _Failure("DATASET_REFERENCE_INVALID")
        rebuilt = build_dataset_snapshot_reference(_plain(reference))
        if (
            not rebuilt.is_valid or rebuilt.reference != reference
            or reference.human_review_required
            or reference.review_conflict_record_version_ids
            or reference.advisory_only is not True
            or reference.no_execution_authority is not True
        ):
            raise _Failure("DATASET_REFERENCE_INVALID")
        code = _opaque(code_version)
        reference_json = _canonical_json(_plain(reference))
        analytical_id = analytical_version = materializer = analytical_json = None
        source_reference_id = reference.dataset_snapshot_reference_id
        if analytical_manifest is not None:
            if not isinstance(analytical_manifest, AnalyticalDatasetManifest):
                raise _Failure("DATASET_REFERENCE_INVALID")
            recomputed = _analytical_identity(analytical_manifest)
            if (
                recomputed != analytical_manifest.logical_dataset_id
                or analytical_manifest.source_reference_id != reference.dataset_snapshot_reference_id
            ):
                raise _Failure("DATASET_REFERENCE_INVALID")
            analytical_id = recomputed
            analytical_version = analytical_manifest.analytical_schema_version
            materializer = analytical_manifest.materializer_version
            analytical_json = _canonical_json(_analytical_identity_payload(analytical_manifest))
            source_reference_id = analytical_manifest.source_reference_id
        preimage = {
            "schema_id": _schema("experiment-dataset-binding"),
            "schema_version": EXPERIMENT_OS_SCHEMA_VERSION,
            "dataset_snapshot_reference_id": reference.dataset_snapshot_reference_id,
            "dataset_snapshot_reference_json": reference_json,
            "dataset_reference_schema_version": reference.schema_version,
            "analytical_logical_dataset_id": analytical_id,
            "analytical_identity_json": analytical_json,
            "analytical_schema_version": analytical_version,
            "materializer_version": materializer,
            "source_reference_id": source_reference_id,
            "code_version": code,
        }
        record = DatasetBinding(
            preimage["schema_id"], EXPERIMENT_OS_SCHEMA_VERSION,
            _digest("dataset_binding", "datasetbinding:sha256:", preimage),
            reference.dataset_snapshot_reference_id, reference_json, reference.schema_version,
            analytical_id, analytical_json, analytical_version, materializer, source_reference_id,
            code, True, True,
        )
        return _valid(record)
    except _Failure as failure:
        return _rejected(failure.code)
    except Exception:
        return _rejected("INTERNAL_VALIDATION_FAILED")


def _time_ns(value: object) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise _Failure("FIELD_TYPE_INVALID")
    return value


def _member_count(value: object) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1 or value > MAX_SAMPLES:
        raise _Failure("FIELD_TYPE_INVALID" if not isinstance(value, int) or isinstance(value, bool) else "FIELD_VALUE_INVALID")
    return value


def _utc_to_ns(value: str) -> int:
    """Exact integer nanoseconds since epoch for a validated UTC timestamp string.

    Integer/datetime based, never binary float. ``value`` must already have passed
    :func:`_utc`.
    """
    parsed = _dt(value)
    epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
    delta = parsed - epoch
    return (delta.days * 86_400 + delta.seconds) * 1_000_000_000 + delta.microseconds * 1_000


def _external_binding_preimage(
    source_kind: str,
    source_external_dataset_id: str,
    source_lineage_id: str,
    source_membership_digest: str,
    source_member_count: int,
    instrument_id: str,
    conversion_policy_version: str,
    first_event_time_ns: int,
    last_event_time_ns: int,
    first_availability_time_ns: int,
    last_availability_time_ns: int,
    code_version: str,
) -> dict[str, object]:
    """Exact identity preimage: every ExternalDatasetBinding semantic field except
    the id and the two safety booleans."""
    return {
        "schema_id": EXTERNAL_DATASET_BINDING_SCHEMA_ID,
        "schema_version": EXPERIMENT_OS_SCHEMA_VERSION,
        "source_kind": source_kind,
        "source_external_dataset_id": source_external_dataset_id,
        "source_lineage_id": source_lineage_id,
        "source_membership_digest": source_membership_digest,
        "source_member_count": source_member_count,
        "instrument_id": instrument_id,
        "conversion_policy_version": conversion_policy_version,
        "first_event_time_ns": first_event_time_ns,
        "last_event_time_ns": last_event_time_ns,
        "first_availability_time_ns": first_availability_time_ns,
        "last_availability_time_ns": last_availability_time_ns,
        "code_version": code_version,
    }


def _build_external_dataset_binding(
    source_kind: object,
    source_external_dataset_id: object,
    source_lineage_id: object,
    source_membership_digest: object,
    source_member_count: object,
    instrument_id: object,
    conversion_policy_version: object,
    first_event_time_ns: object,
    last_event_time_ns: object,
    first_availability_time_ns: object,
    last_availability_time_ns: object,
    code_version: object,
) -> ExperimentControlResult:
    """Construct/validate a provenance-separated :class:`ExternalDatasetBinding`.

    Private/internal WP170 helper. The ONLY public construction path is the PMXT
    bridge (`build_pmxt_v2_dataset_binding` / `build_pmxt_v2_research_dataset_manifest`
    in ``research_runtime.nautilus_offline.experiment_bridge``), which supplies these
    fields from a validated ``PmxtV2ResearchLineage``. It is intentionally not exported
    from the package root so arbitrary caller-supplied external metadata cannot
    construct an ``ExternalDatasetBinding`` outside the validated bridge. Never creates
    a DatasetSnapshotReference and never claims canonical-PIT authority.
    """
    try:
        kind = _enum(source_kind, (EXTERNAL_DATASET_BINDING_SOURCE_KIND,))
        external_id = _opaque(source_external_dataset_id)
        lineage_id = _opaque(source_lineage_id)
        membership_digest = _sha(source_membership_digest)
        count = _member_count(source_member_count)
        instrument = _opaque(instrument_id)
        # conversion_policy_version contains '/', so it is free text, not an opaque id.
        policy = _text(conversion_policy_version)
        first_event = _time_ns(first_event_time_ns)
        last_event = _time_ns(last_event_time_ns)
        first_availability = _time_ns(first_availability_time_ns)
        last_availability = _time_ns(last_availability_time_ns)
        if first_event > last_event or first_availability > last_availability:
            raise _Failure("FIELD_VALUE_INVALID")
        code = _opaque(code_version)
        preimage = _external_binding_preimage(
            kind, external_id, lineage_id, membership_digest, count, instrument,
            policy, first_event, last_event, first_availability, last_availability, code,
        )
        record = ExternalDatasetBinding(
            EXTERNAL_DATASET_BINDING_SCHEMA_ID, EXPERIMENT_OS_SCHEMA_VERSION,
            _digest("external_dataset_binding", "datasetbinding:sha256:", preimage),
            kind, external_id, lineage_id, membership_digest, count, instrument, policy,
            first_event, last_event, first_availability, last_availability, code,
            True, True,
        )
        return _valid(record)
    except _Failure as failure:
        return _rejected(failure.code)
    except Exception:
        return _rejected("INTERNAL_VALIDATION_FAILED")


_FEATURE_KEYS = frozenset({
    "feature_name", "feature_version", "description", "source_dependencies",
    "parameters", "lookback_rule", "availability_rule", "missing_data_policy",
    "transformation_version", "no_future_information_rule",
})
SAFE_FEATURE_SOURCE_DEPENDENCIES = (
    "market_observation.best_ask",
    "market_observation.best_bid",
    "market_observation.event_time",
    "market_observation.ingestion_time",
    "market_observation.last_trade_price",
    "market_observation.liquidity",
    "market_observation.midpoint",
    "market_observation.observed_time",
    "market_observation.spread",
    "market_observation.volume",
)
_LOOKBACK_RE = re.compile(r"^(?:POINT_IN_TIME|TRAILING_[1-9][0-9]*_(?:SECONDS|MINUTES|HOURS|DAYS))$")
_FUTURE_FRAGMENTS = (
    "after", "closed", "final", "future", "label", "outcome", "payout",
    "resolution", "resolved", "settled", "settlement", "target", "winner",
)


def _validate_feature_information(
    dependencies: tuple[str, ...], lookback_rule: object, availability_rule: object,
    no_future_rule: object, parameters: object,
) -> tuple[str, str, str]:
    if any(item not in SAFE_FEATURE_SOURCE_DEPENDENCIES for item in dependencies):
        raise _Failure("FEATURE_TIMING_LEAKAGE")
    lookback = _text(lookback_rule)
    availability = _text(availability_rule)
    no_future = _text(no_future_rule)
    if (
        not _LOOKBACK_RE.fullmatch(lookback)
        or availability != "SOURCE_AVAILABILITY_TIME"
        or no_future != "FEATURE_AVAILABLE_AT_OR_BEFORE_DECISION_TIME"
    ):
        raise _Failure("FEATURE_TIMING_LEAKAGE")

    def scan(value: object) -> None:
        if isinstance(value, Mapping):
            for key, item in value.items():
                scan(key)
                scan(item)
        elif isinstance(value, (list, tuple)):
            for item in value:
                scan(item)
        elif isinstance(value, str):
            folded = value.casefold()
            if any(fragment in folded for fragment in _FUTURE_FRAGMENTS):
                raise _Failure("FEATURE_TIMING_LEAKAGE")
        elif isinstance(value, int) and not isinstance(value, bool) and value < 0:
            raise _Failure("FEATURE_TIMING_LEAKAGE")

    scan(parameters)
    return lookback, availability, no_future


def build_feature_definition(input_mapping: object) -> ExperimentControlResult:
    try:
        value = _mapping(input_mapping, _FEATURE_KEYS)
        dependencies = _tuple_text(value["source_dependencies"])
        lookback, availability, no_future = _validate_feature_information(
            dependencies, value["lookback_rule"], value["availability_rule"],
            value["no_future_information_rule"], value["parameters"],
        )
        fields_map = {
            "schema_id": _schema("feature-definition"),
            "schema_version": EXPERIMENT_OS_SCHEMA_VERSION,
            "feature_name": _opaque(value["feature_name"]),
            "feature_version": _opaque(value["feature_version"]),
            "description": _text(value["description"]),
            "source_dependencies": list(dependencies),
            "parameters_json": _canonical_mapping_json(value["parameters"]),
            "lookback_rule": lookback,
            "availability_rule": availability,
            "missing_data_policy": _text(value["missing_data_policy"]),
            "transformation_version": _opaque(value["transformation_version"]),
            "no_future_information_rule": no_future,
        }
        record = FeatureDefinition(
            fields_map["schema_id"], EXPERIMENT_OS_SCHEMA_VERSION,
            _digest("feature_definition", "featuredef:sha256:", fields_map),
            fields_map["feature_name"], fields_map["feature_version"], fields_map["description"],
            dependencies, fields_map["parameters_json"], fields_map["lookback_rule"],
            fields_map["availability_rule"], fields_map["missing_data_policy"],
            fields_map["transformation_version"], fields_map["no_future_information_rule"],
            True, True,
        )
        return _valid(record)
    except _Failure as failure:
        return _rejected(failure.code)
    except Exception:
        return _rejected("INTERNAL_VALIDATION_FAILED")


_LABEL_KEYS = frozenset({
    "label_name", "label_version", "prediction_target", "horizon_rule",
    "target_time_rule", "outcome_source_rule", "availability_time_rule",
    "censoring_rule", "parameters", "code_version",
})


def build_label_definition(input_mapping: object) -> ExperimentControlResult:
    try:
        value = _mapping(input_mapping, _LABEL_KEYS)
        preimage = {
            "schema_id": _schema("label-definition"),
            "schema_version": EXPERIMENT_OS_SCHEMA_VERSION,
            "label_name": _opaque(value["label_name"]),
            "label_version": _opaque(value["label_version"]),
            "prediction_target": _text(value["prediction_target"]),
            "horizon_rule": _text(value["horizon_rule"]),
            "target_time_rule": _text(value["target_time_rule"]),
            "outcome_source_rule": _text(value["outcome_source_rule"]),
            "availability_time_rule": _text(value["availability_time_rule"]),
            "censoring_rule": _text(value["censoring_rule"]),
            "parameters_json": _canonical_mapping_json(value["parameters"]),
            "code_version": _opaque(value["code_version"]),
        }
        record = LabelDefinition(
            preimage["schema_id"], EXPERIMENT_OS_SCHEMA_VERSION,
            _digest("label_definition", "labeldef:sha256:", preimage),
            preimage["label_name"], preimage["label_version"], preimage["prediction_target"],
            preimage["horizon_rule"], preimage["target_time_rule"],
            preimage["outcome_source_rule"], preimage["availability_time_rule"],
            preimage["censoring_rule"], preimage["parameters_json"], preimage["code_version"],
            True, True,
        )
        return _valid(record)
    except _Failure as failure:
        return _rejected(failure.code)
    except Exception:
        return _rejected("INTERNAL_VALIDATION_FAILED")


_SAMPLE_KEYS = frozenset({
    "source_record_version_ids", "market_id", "related_group_id", "leakage_group_id",
    "decision_time", "feature_availability_time", "target_time",
    "label_availability_time",
})


def _validate_core_record(record: object, expected_type: type) -> None:
    if not isinstance(record, expected_type):
        raise _Failure("FIELD_TYPE_INVALID")
    if getattr(record, "advisory_only", None) is not True or getattr(record, "no_execution_authority", None) is not True:
        raise _Failure("FIELD_VALUE_INVALID")


def _feature_set_id(features: tuple[FeatureDefinition, ...]) -> tuple[tuple[str, ...], str]:
    ids = tuple(sorted(feature.feature_definition_id for feature in features))
    if not ids or len(set(ids)) != len(ids):
        raise _Failure("FIELD_VALUE_INVALID")
    digest = _digest("feature_set", "featureset:sha256:", {"feature_definition_ids": list(ids)})
    return ids, digest


def _research_dataset_manifest(
    *,
    dataset_binding_id: str,
    validate_source_ids,
    validate_availability,
    feature_definitions: object,
    label_definition: object,
    sample_inputs: object,
    group_policy: object,
) -> ExperimentControlResult:
    """ONE shared ResearchSample/ResearchDatasetManifest construction.

    Both the canonical DatasetBinding path and the WP175D external bridge path use
    this identity/leakage/timing implementation. Binding-subtype-specific membership
    validation is injected via ``validate_source_ids`` (source-id membership, run
    before UTC parsing to preserve the canonical error precedence) and
    ``validate_availability`` (external-only extra source-availability check, a no-op
    for the canonical path).
    """
    try:
        if not isinstance(feature_definitions, (list, tuple)) or not feature_definitions:
            raise _Failure("FIELD_TYPE_INVALID")
        features = tuple(feature_definitions)
        for feature in features:
            _validate_public_record(feature)
            if not isinstance(feature, FeatureDefinition):
                raise _Failure("FIELD_TYPE_INVALID")
        _validate_public_record(label_definition)
        if not isinstance(label_definition, LabelDefinition):
            raise _Failure("FIELD_TYPE_INVALID")
        policy = _enum(group_policy, GROUP_POLICIES)
        if not isinstance(sample_inputs, (list, tuple)):
            raise _Failure("FIELD_TYPE_INVALID")
        if not sample_inputs or len(sample_inputs) > MAX_SAMPLES:
            raise _Failure("FIELD_VALUE_INVALID" if not sample_inputs else "LIMIT_EXCEEDED")
        feature_ids, feature_set_id = _feature_set_id(features)
        samples_by_id: dict[str, ResearchSample] = {}
        membership_seen: dict[str, ResearchSample] = {}
        for raw in sample_inputs:
            value = _mapping(raw, _SAMPLE_KEYS)
            source_ids = _tuple_text(value["source_record_version_ids"])
            # Binding-subtype membership check first (preserves canonical error order).
            validate_source_ids(source_ids)
            source_digest = _raw_hash({"source_record_version_ids": list(source_ids)})
            decision = _utc(value["decision_time"])
            feature_time = _utc(value["feature_availability_time"])
            target = _utc(value["target_time"])
            label_time = _utc(value["label_availability_time"])
            if _dt(feature_time) > _dt(decision):
                raise _Failure("FEATURE_TIMING_LEAKAGE")
            if not (_dt(decision) <= _dt(target) <= _dt(label_time)):
                raise _Failure("LABEL_TIMING_INVALID")
            # External-only: feature availability cannot precede real source availability.
            validate_availability(source_ids, feature_time)
            group = _opaque(value["leakage_group_id"], nullable=True)
            if (policy == "EXCLUSIVE" and group is None) or (
                policy == "DECLARED_NO_ISOLATION" and group is not None
            ):
                raise _Failure("GROUP_LEAKAGE_VIOLATION")
            preimage = {
                "schema_id": _schema("research-sample"),
                "schema_version": EXPERIMENT_OS_SCHEMA_VERSION,
                "dataset_binding_id": dataset_binding_id,
                "source_record_version_ids": list(source_ids),
                "source_membership_digest": source_digest,
                "market_id": _opaque(value["market_id"]),
                "related_group_id": _opaque(value["related_group_id"], nullable=True),
                "leakage_group_id": group,
                "decision_time": decision,
                "feature_availability_time": feature_time,
                "target_time": target,
                "label_availability_time": label_time,
                "feature_set_id": feature_set_id,
                "label_definition_id": label_definition.label_definition_id,
                "lineage_digest": _raw_hash({
                    "dataset_binding_id": dataset_binding_id,
                    "source_record_version_ids": list(source_ids),
                }),
            }
            sample = ResearchSample(
                preimage["schema_id"], EXPERIMENT_OS_SCHEMA_VERSION,
                _digest("sample", "sample:sha256:", preimage),
                dataset_binding_id, source_ids, source_digest, preimage["market_id"],
                preimage["related_group_id"], group, decision, feature_time, target, label_time,
                feature_set_id, label_definition.label_definition_id, preimage["lineage_digest"],
                True, True,
            )
            prior_membership = membership_seen.get(source_digest)
            if prior_membership is not None and prior_membership != sample:
                raise _Failure("DATASET_REFERENCE_INVALID")
            membership_seen[source_digest] = sample
            prior = samples_by_id.get(sample.sample_id)
            if prior is not None and prior != sample:
                raise _Failure("IDENTITY_DERIVATION_MISMATCH")
            samples_by_id[sample.sample_id] = sample
        samples = tuple(samples_by_id[key] for key in sorted(samples_by_id))
        preimage = {
            "schema_id": _schema("research-dataset-manifest"),
            "schema_version": EXPERIMENT_OS_SCHEMA_VERSION,
            "dataset_binding_id": dataset_binding_id,
            "feature_definition_ids": list(feature_ids),
            "feature_set_id": feature_set_id,
            "label_definition_id": label_definition.label_definition_id,
            "group_policy": policy,
            "samples": [_plain(sample) for sample in samples],
            "total_sample_count": len(samples),
            "assignment_order": "SAMPLE_ID_ASC",
        }
        record = ResearchDatasetManifest(
            preimage["schema_id"], EXPERIMENT_OS_SCHEMA_VERSION,
            _digest("research_dataset_manifest", "researchdataset:sha256:", preimage),
            dataset_binding_id, feature_ids, feature_set_id,
            label_definition.label_definition_id, policy, samples, len(samples),
            "SAMPLE_ID_ASC", True, True,
        )
        return _valid(record)
    except _Failure as failure:
        return _rejected(failure.code)
    except Exception:
        return _rejected("INTERNAL_VALIDATION_FAILED")


def build_research_dataset_manifest(
    dataset_binding: object,
    feature_definitions: object,
    label_definition: object,
    sample_inputs: object,
    group_policy: object,
) -> ExperimentControlResult:
    """Canonical DatasetBinding path (unchanged behavior).

    Membership is proven against the exact DatasetSnapshotReference ordinary
    record-version ids, exactly as before.
    """
    try:
        _validate_public_record(dataset_binding)
        if not isinstance(dataset_binding, DatasetBinding):
            raise _Failure("DATASET_REFERENCE_INVALID")
        reference = _decode_dataset_reference_json(dataset_binding.dataset_snapshot_reference_json)
        ordinary_source_ids = frozenset(reference.ordinary_record_version_ids)

        def _canonical_source_ids(source_ids: tuple[str, ...]) -> None:
            if not source_ids or not set(source_ids).issubset(ordinary_source_ids):
                raise _Failure("DATASET_REFERENCE_INVALID")

        def _canonical_availability(source_ids: tuple[str, ...], feature_time: str) -> None:
            return None

        return _research_dataset_manifest(
            dataset_binding_id=dataset_binding.dataset_binding_id,
            validate_source_ids=_canonical_source_ids,
            validate_availability=_canonical_availability,
            feature_definitions=feature_definitions,
            label_definition=label_definition,
            sample_inputs=sample_inputs,
            group_policy=group_policy,
        )
    except _Failure as failure:
        return _rejected(failure.code)
    except Exception:
        return _rejected("INTERNAL_VALIDATION_FAILED")


_SPLIT_KEYS = frozenset({
    "split_plan_version", "formation_start", "selection_start", "oos_start",
    "end_time", "purge_rule", "embargo_seconds", "group_policy",
    "inclusion_policy", "min_samples_per_role",
})


def _raw_hash(value: Mapping[str, object]) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def build_temporal_split_manifest(
    dataset_manifest: object, split_policy: object
) -> ExperimentControlResult:
    try:
        _validate_public_record(dataset_manifest)
        if not isinstance(dataset_manifest, ResearchDatasetManifest):
            raise _Failure("FIELD_TYPE_INVALID")
        value = _mapping(split_policy, _SPLIT_KEYS)
        boundaries = tuple(_utc(value[key]) for key in (
            "formation_start", "selection_start", "oos_start", "end_time"
        ))
        if not all(_dt(boundaries[i]) < _dt(boundaries[i + 1]) for i in range(3)):
            raise _Failure("SPLIT_INVALID")
        purge_rule = _enum(value["purge_rule"], ("PURGE_LABEL_AVAILABILITY_AT_OR_AFTER_NEXT_BOUNDARY",))
        policy = _enum(value["group_policy"], GROUP_POLICIES)
        if policy != dataset_manifest.group_policy:
            raise _Failure("GROUP_LEAKAGE_VIOLATION")
        inclusion = _enum(value["inclusion_policy"], ("DECISION_TIME_HALF_OPEN",))
        embargo = value["embargo_seconds"]
        minimum = value["min_samples_per_role"]
        if not isinstance(embargo, int) or isinstance(embargo, bool) or embargo < 0:
            raise _Failure("FIELD_TYPE_INVALID")
        if not isinstance(minimum, int) or isinstance(minimum, bool) or minimum < 1:
            raise _Failure("FIELD_TYPE_INVALID")
        plan_version = _opaque(value["split_plan_version"])
        plan_preimage = {
            "split_plan_version": plan_version,
            "formation_start": boundaries[0], "selection_start": boundaries[1],
            "oos_start": boundaries[2], "end_time": boundaries[3],
            "purge_rule": purge_rule, "embargo_seconds": embargo,
            "group_policy": policy, "inclusion_policy": inclusion,
            "min_samples_per_role": minimum,
        }
        plan_id = _digest("split_plan", "splitplan:sha256:", plan_preimage)
        roles: dict[str, list[str]] = {role: [] for role in RESEARCH_ROLES}
        purged: list[str] = []
        embargoed: list[str] = []
        sample_by_id = {sample.sample_id: sample for sample in dataset_manifest.samples}
        for sample in dataset_manifest.samples:
            decision = _dt(sample.decision_time)
            role: str | None = None
            if _dt(boundaries[0]) <= decision < _dt(boundaries[1]):
                role = "FORMATION"
            elif _dt(boundaries[1]) <= decision < _dt(boundaries[2]):
                role = "SELECTION"
            elif _dt(boundaries[2]) <= decision < _dt(boundaries[3]):
                role = "OUT_OF_SAMPLE"
            if role is None:
                continue
            next_boundary = boundaries[1] if role == "FORMATION" else boundaries[2] if role == "SELECTION" else None
            if next_boundary is not None and max(_dt(sample.target_time), _dt(sample.label_availability_time)) >= _dt(next_boundary):
                purged.append(sample.sample_id)
                continue
            role_boundary = boundaries[1] if role == "SELECTION" else boundaries[2] if role == "OUT_OF_SAMPLE" else None
            if role_boundary is not None and decision < _dt(role_boundary) + timedelta(seconds=embargo):
                embargoed.append(sample.sample_id)
                continue
            roles[role].append(sample.sample_id)
        for role in RESEARCH_ROLES:
            roles[role].sort()
            if len(roles[role]) < minimum:
                raise _Failure("SPLIT_INVALID")
        source_roles: dict[str, str] = {}
        for role in RESEARCH_ROLES:
            for sample_id in roles[role]:
                for source_id in sample_by_id[sample_id].source_record_version_ids:
                    prior_role = source_roles.setdefault(source_id, role)
                    if prior_role != role:
                        raise _Failure("SPLIT_INVALID")
        if policy == "EXCLUSIVE":
            seen_groups: dict[str, str] = {}
            for role in RESEARCH_ROLES:
                for sample_id in roles[role]:
                    sample = sample_by_id[sample_id]
                    if sample.leakage_group_id is None:
                        raise _Failure("GROUP_LEAKAGE_VIOLATION")
                    isolation_keys = (
                        f"leakage:{sample.leakage_group_id}",
                        f"market:{sample.market_id}",
                        *(() if sample.related_group_id is None else (f"related:{sample.related_group_id}",)),
                    )
                    for isolation_key in isolation_keys:
                        prior_role = seen_groups.setdefault(isolation_key, role)
                        if prior_role != role:
                            raise _Failure("GROUP_LEAKAGE_VIOLATION")
        assignment_preimage = {
            "formation_sample_ids": roles["FORMATION"],
            "selection_sample_ids": roles["SELECTION"],
            "oos_sample_ids": roles["OUT_OF_SAMPLE"],
            "purged_sample_ids": sorted(purged),
            "embargoed_sample_ids": sorted(embargoed),
        }
        assignment_hash = _raw_hash(assignment_preimage)
        split_preimage = {
            "schema_id": _schema("temporal-split-manifest"),
            "schema_version": EXPERIMENT_OS_SCHEMA_VERSION,
            "split_plan_id": plan_id,
            "dataset_manifest_id": dataset_manifest.research_dataset_manifest_id,
            "dataset_binding_id": dataset_manifest.dataset_binding_id,
            "feature_definition_ids": list(dataset_manifest.feature_definition_ids),
            "feature_set_id": dataset_manifest.feature_set_id,
            "label_definition_id": dataset_manifest.label_definition_id,
            **plan_preimage,
            **assignment_preimage,
            "assignment_hash": assignment_hash,
        }
        record = TemporalSplitManifest(
            split_preimage["schema_id"], EXPERIMENT_OS_SCHEMA_VERSION, plan_id,
            plan_version, _digest("temporal_split", "split:sha256:", split_preimage),
            dataset_manifest.research_dataset_manifest_id, dataset_manifest.dataset_binding_id,
            dataset_manifest.feature_definition_ids, dataset_manifest.feature_set_id,
            dataset_manifest.label_definition_id, *boundaries, purge_rule,
            embargo, policy, inclusion, minimum, tuple(roles["FORMATION"]),
            tuple(roles["SELECTION"]), tuple(roles["OUT_OF_SAMPLE"]),
            tuple(sorted(purged)), tuple(sorted(embargoed)), assignment_hash, True, True,
        )
        return _valid(record)
    except _Failure as failure:
        return _rejected(failure.code)
    except Exception:
        return _rejected("INTERNAL_VALIDATION_FAILED")


def _simple_record(
    input_mapping: object,
    keys: frozenset[str],
    kind: str,
    prefix: str,
    record_type: type,
    converters: Mapping[str, object],
) -> ExperimentControlResult:
    try:
        value = _mapping(input_mapping, keys)
        preimage: dict[str, object] = {
            "schema_id": _schema(kind.replace("_", "-")),
            "schema_version": EXPERIMENT_OS_SCHEMA_VERSION,
        }
        for key in keys:
            converter = converters.get(key, _text)
            preimage[key] = converter(value[key])  # type: ignore[operator]
        id_name = fields(record_type)[2].name
        record_values = [preimage[field.name] for field in fields(record_type) if field.name not in {id_name, "advisory_only", "no_execution_authority"}]
        record = record_type(
            *record_values[:2], _digest(kind, prefix, preimage), *record_values[2:], True, True
        )
        return _valid(record)
    except _Failure as failure:
        return _rejected(failure.code)
    except Exception:
        return _rejected("INTERNAL_VALIDATION_FAILED")


_HYPOTHESIS_KEYS = frozenset({
    "hypothesis_name", "hypothesis_version", "predecessor_candidate_ids",
    "falsifiable_claim", "proposed_mechanism", "cohort", "horizon", "target",
    "falsification_condition", "human_review_state", "review_assertion",
    "code_version", "creation_provenance",
})


def build_alpha_hypothesis(input_mapping: object) -> ExperimentControlResult:
    converters = {
        "hypothesis_name": _opaque, "hypothesis_version": _opaque,
        "predecessor_candidate_ids": lambda x: _tuple_text(x, allow_empty=True),
        "human_review_state": lambda x: _enum(x, ("REVIEWED",)),
        "code_version": _opaque,
    }
    return _simple_record(input_mapping, _HYPOTHESIS_KEYS, "hypothesis", "hypothesis:sha256:", AlphaHypothesis, converters)


_METRIC_KEYS = frozenset({"metric_name", "metric_version", "direction", "parameters", "code_version"})


def build_metric_definition(input_mapping: object) -> ExperimentControlResult:
    try:
        value = _mapping(input_mapping, _METRIC_KEYS)
        preimage = {
            "schema_id": _schema("metric-definition"),
            "schema_version": EXPERIMENT_OS_SCHEMA_VERSION,
            "metric_name": _opaque(value["metric_name"]),
            "metric_version": _opaque(value["metric_version"]),
            "direction": _enum(value["direction"], METRIC_DIRECTIONS),
            "parameters_json": _canonical_mapping_json(value["parameters"]),
            "code_version": _opaque(value["code_version"]),
        }
        record = MetricDefinition(
            preimage["schema_id"], EXPERIMENT_OS_SCHEMA_VERSION,
            _digest("metric", "metric:sha256:", preimage), preimage["metric_name"],
            preimage["metric_version"], preimage["direction"],
            preimage["parameters_json"], preimage["code_version"], True, True,
        )
        return _valid(record)
    except _Failure as failure:
        return _rejected(failure.code)
    except Exception:
        return _rejected("INTERNAL_VALIDATION_FAILED")


_BASELINE_KEYS = frozenset({
    "baseline_name", "baseline_version", "method_rule", "parameters",
    "same_partition_required", "acceptance_rule", "code_version",
})


def build_baseline_definition(input_mapping: object) -> ExperimentControlResult:
    try:
        value = _mapping(input_mapping, _BASELINE_KEYS)
        if value["same_partition_required"] is not True:
            raise _Failure("FIELD_VALUE_INVALID")
        preimage = {
            "schema_id": _schema("baseline-definition"), "schema_version": EXPERIMENT_OS_SCHEMA_VERSION,
            "baseline_name": _opaque(value["baseline_name"]), "baseline_version": _opaque(value["baseline_version"]),
            "method_rule": _text(value["method_rule"]), "parameters_json": _canonical_mapping_json(value["parameters"]),
            "same_partition_required": True,
            "acceptance_rule": _enum(value["acceptance_rule"], _BASELINE_ACCEPTANCE_RULES),
            "code_version": _opaque(value["code_version"]),
        }
        record = BaselineDefinition(
            preimage["schema_id"], EXPERIMENT_OS_SCHEMA_VERSION,
            _digest("baseline", "baseline:sha256:", preimage), preimage["baseline_name"],
            preimage["baseline_version"], preimage["method_rule"], preimage["parameters_json"],
            True, preimage["acceptance_rule"], preimage["code_version"], True, True,
        )
        return _valid(record)
    except _Failure as failure:
        return _rejected(failure.code)
    except Exception:
        return _rejected("INTERNAL_VALIDATION_FAILED")


_FAMILY_KEYS = frozenset({
    "research_program", "cohort", "target", "metric_family", "correction_policy",
    "predecessor_family_id",
})


def build_experiment_family(input_mapping: object) -> ExperimentControlResult:
    try:
        value = _mapping(input_mapping, _FAMILY_KEYS)
        preimage = {
            "schema_id": _schema("experiment-family"), "schema_version": EXPERIMENT_OS_SCHEMA_VERSION,
            "research_program": _text(value["research_program"]), "cohort": _text(value["cohort"]),
            "target": _text(value["target"]), "metric_family": _text(value["metric_family"]),
            "correction_policy": _enum(value["correction_policy"], CORRECTION_POLICIES),
            "predecessor_family_id": _opaque(value["predecessor_family_id"], nullable=True),
        }
        record = ExperimentFamily(
            preimage["schema_id"], EXPERIMENT_OS_SCHEMA_VERSION,
            _digest("experiment_family", "experimentfamily:sha256:", preimage),
            preimage["research_program"], preimage["cohort"], preimage["target"],
            preimage["metric_family"], preimage["correction_policy"],
            preimage["predecessor_family_id"], True, True,
        )
        return _valid(record)
    except _Failure as failure:
        return _rejected(failure.code)
    except Exception:
        return _rejected("INTERNAL_VALIDATION_FAILED")


_PLAN_KEYS = frozenset({
    "trial_number", "inclusion_exclusion_rules", "acceptance_thresholds",
    "search_space", "parameters", "random_seeds", "cost_model_reference",
    "stop_failure_rules", "code_version", "creation_provenance", "preregistered_at",
})


def build_preregistered_experiment(
    hypothesis: object, dataset_binding: object, feature_definitions: object,
    label_definition: object, split_manifest: object, primary_metric: object,
    secondary_metrics: object, baseline: object, family: object, plan: object,
) -> ExperimentControlResult:
    try:
        # The dataset binding may be either the canonical DatasetBinding or the
        # additive WP175D ExternalDatasetBinding; the public signature is unchanged
        # and all downstream OOS/lifecycle semantics remain identical.
        _validate_public_record(dataset_binding)
        if not isinstance(dataset_binding, (DatasetBinding, ExternalDatasetBinding)):
            raise _Failure("FIELD_TYPE_INVALID")
        for record, expected in (
            (hypothesis, AlphaHypothesis),
            (label_definition, LabelDefinition), (split_manifest, TemporalSplitManifest),
            (primary_metric, MetricDefinition), (baseline, BaselineDefinition),
            (family, ExperimentFamily),
        ):
            _validate_public_record(record)
            if not isinstance(record, expected):
                raise _Failure("FIELD_TYPE_INVALID")
        if not isinstance(feature_definitions, (list, tuple)) or not feature_definitions:
            raise _Failure("FIELD_TYPE_INVALID")
        features = tuple(feature_definitions)
        for feature in features:
            _validate_public_record(feature)
            if not isinstance(feature, FeatureDefinition):
                raise _Failure("FIELD_TYPE_INVALID")
        if not isinstance(secondary_metrics, (list, tuple)):
            raise _Failure("FIELD_TYPE_INVALID")
        secondaries = tuple(secondary_metrics)
        for metric in secondaries:
            _validate_public_record(metric)
            if not isinstance(metric, MetricDefinition):
                raise _Failure("FIELD_TYPE_INVALID")
        feature_ids, feature_set_id = _feature_set_id(features)
        if (
            split_manifest.dataset_manifest_id == ""
            or hypothesis.cohort != family.cohort
            or hypothesis.target != family.target
            or split_manifest.group_policy not in GROUP_POLICIES
            or split_manifest.dataset_binding_id != dataset_binding.dataset_binding_id
            or split_manifest.feature_definition_ids != feature_ids
            or split_manifest.feature_set_id != feature_set_id
            or split_manifest.label_definition_id != label_definition.label_definition_id
        ):
            raise _Failure("SPLIT_INVALID")
        value = _mapping(plan, _PLAN_KEYS)
        trial = value["trial_number"]
        if not isinstance(trial, int) or isinstance(trial, bool) or trial < 1:
            raise _Failure("FIELD_TYPE_INVALID")
        seeds = _tuple_int(value["random_seeds"])
        secondary_ids = tuple(sorted(metric.metric_definition_id for metric in secondaries))
        if len(set(secondary_ids)) != len(secondary_ids) or primary_metric.metric_definition_id in secondary_ids:
            raise _Failure("FIELD_VALUE_INVALID")
        thresholds = _threshold_mapping(value["acceptance_thresholds"], primary_metric.direction)
        expected_baseline_rule = {
            "HIGHER_IS_BETTER": "CANDIDATE_GTE_BASELINE",
            "LOWER_IS_BETTER": "CANDIDATE_LTE_BASELINE",
        }[primary_metric.direction]
        if baseline.acceptance_rule != expected_baseline_rule:
            raise _Failure("FIELD_VALUE_INVALID")
        preimage = {
            "schema_id": _schema("preregistered-experiment"), "schema_version": EXPERIMENT_OS_SCHEMA_VERSION,
            "experiment_family_id": family.experiment_family_id, "trial_number": trial,
            "hypothesis_id": hypothesis.hypothesis_id, "dataset_binding_id": dataset_binding.dataset_binding_id,
            "research_dataset_manifest_id": split_manifest.dataset_manifest_id,
            "feature_definition_ids": list(feature_ids), "feature_set_id": feature_set_id,
            "label_definition_id": label_definition.label_definition_id,
            "split_plan_id": split_manifest.split_plan_id, "split_assignment_id": split_manifest.split_assignment_id,
            "primary_metric_id": primary_metric.metric_definition_id,
            "secondary_metric_ids": list(secondary_ids), "baseline_id": baseline.baseline_definition_id,
            "inclusion_exclusion_rules": _text(value["inclusion_exclusion_rules"]),
            "acceptance_thresholds_json": _canonical_mapping_json(thresholds),
            "search_space_json": _canonical_mapping_json(value["search_space"]),
            "parameters_json": _canonical_mapping_json(value["parameters"]), "random_seeds": list(seeds),
            "correction_policy": family.correction_policy,
            "cost_model_reference": _opaque(value["cost_model_reference"], nullable=True),
            "stop_failure_rules": _text(value["stop_failure_rules"]),
            "code_version": _opaque(value["code_version"]),
            "creation_provenance": _text(value["creation_provenance"]),
            "preregistered_at": _utc(value["preregistered_at"]),
        }
        record = PreregisteredExperiment(
            preimage["schema_id"], EXPERIMENT_OS_SCHEMA_VERSION,
            _digest("preregistered_experiment", "experiment:sha256:", preimage),
            family.experiment_family_id, trial, hypothesis.hypothesis_id,
            dataset_binding.dataset_binding_id, split_manifest.dataset_manifest_id,
            feature_ids, feature_set_id, label_definition.label_definition_id,
            split_manifest.split_plan_id, split_manifest.split_assignment_id,
            primary_metric.metric_definition_id, secondary_ids, baseline.baseline_definition_id,
            preimage["inclusion_exclusion_rules"], preimage["acceptance_thresholds_json"],
            preimage["search_space_json"], preimage["parameters_json"], seeds,
            family.correction_policy, preimage["cost_model_reference"],
            preimage["stop_failure_rules"], preimage["code_version"],
            preimage["creation_provenance"], preimage["preregistered_at"], True, True,
        )
        return _valid(record)
    except _Failure as failure:
        return _rejected(failure.code)
    except Exception:
        return _rejected("INTERNAL_VALIDATION_FAILED")


def _lifecycle_expected(index: int) -> tuple[str, str | None, str]:
    return LIFECYCLE_ACTIONS[index], None if index == 0 else LIFECYCLE_STATES[index - 1], LIFECYCLE_STATES[index]


def _evidence_matches_experiment(
    evidence: RunEvidenceReceipt, experiment: PreregisteredExperiment
) -> bool:
    return (
        evidence.experiment_id == experiment.experiment_id
        and evidence.experiment_family_id == experiment.experiment_family_id
        and evidence.trial_number == experiment.trial_number
        and evidence.dataset_binding_id == experiment.dataset_binding_id
        and evidence.research_dataset_manifest_id == experiment.research_dataset_manifest_id
        and evidence.split_assignment_id == experiment.split_assignment_id
        and evidence.feature_set_id == experiment.feature_set_id
        and evidence.label_definition_id == experiment.label_definition_id
        and evidence.code_version == experiment.code_version
        and evidence.parameters_json == experiment.parameters_json
        and evidence.random_seeds == experiment.random_seeds
        and evidence.metric_definition_ids
        == (experiment.primary_metric_id,) + experiment.secondary_metric_ids
        and evidence.baseline_id == experiment.baseline_id
    )


def _validate_lifecycle_tuple(experiment: PreregisteredExperiment, receipts: object) -> tuple[LifecycleReceipt, ...]:
    if not isinstance(receipts, (list, tuple)):
        raise _Failure("FIELD_TYPE_INVALID")
    if len(receipts) > len(LIFECYCLE_ACTIONS):
        raise _Failure("PREREGISTRATION_STATE_INVALID")
    prior_id = None
    prior_time: datetime | None = _dt(_utc(experiment.preregistered_at))
    out: list[LifecycleReceipt] = []
    for index, receipt in enumerate(receipts):
        if not isinstance(receipt, LifecycleReceipt):
            raise _Failure("FIELD_TYPE_INVALID")
        _validate_public_record(receipt)
        action, from_state, to_state = _lifecycle_expected(index)
        if (
            receipt.experiment_id != experiment.experiment_id or receipt.sequence_number != index
            or receipt.previous_lifecycle_receipt_id != prior_id or receipt.action != action
            or receipt.from_state != from_state or receipt.to_state != to_state
            or (action != "CLOSE_EXPERIMENT" and receipt.terminal_result_status is not None)
        ):
            raise _Failure("PREREGISTRATION_STATE_INVALID")
        timestamp = _dt(_utc(receipt.occurred_at))
        if prior_time is not None and timestamp < prior_time:
            raise _Failure("PREREGISTRATION_STATE_INVALID")
        prior_time = timestamp
        prior_id = receipt.lifecycle_receipt_id
        out.append(receipt)
    return tuple(out)


def build_lifecycle_receipt(
    experiment: object, prior_receipts: object, action: object,
    occurred_at: object, provenance: object, evidence_receipts: object,
) -> ExperimentControlResult:
    try:
        _validate_public_record(experiment)
        if not isinstance(experiment, PreregisteredExperiment):
            raise _Failure("FIELD_TYPE_INVALID")
        prior = _validate_lifecycle_tuple(experiment, prior_receipts)
        if len(prior) >= len(LIFECYCLE_ACTIONS):
            raise _Failure("PREREGISTRATION_STATE_INVALID")
        expected_action, from_state, to_state = _lifecycle_expected(len(prior))
        if _enum(action, LIFECYCLE_ACTIONS) != expected_action:
            code = "OOS_SEALED_EXPOSURE_VIOLATION" if action == "RELEASE_OOS" else "PREREGISTRATION_STATE_INVALID"
            raise _Failure(code)
        if not isinstance(evidence_receipts, (list, tuple)):
            raise _Failure("FIELD_TYPE_INVALID")
        terminal = None
        if expected_action == "CLOSE_EXPERIMENT":
            oos = [
                item for item in evidence_receipts
                if isinstance(item, RunEvidenceReceipt)
                and _evidence_matches_experiment(item, experiment)
                and item.evaluated_role == "OUT_OF_SAMPLE"
            ]
            if not oos:
                raise _Failure("OOS_SEALED_EXPOSURE_VIOLATION")
            for item in evidence_receipts:
                _validate_public_record(item)
                if not isinstance(item, RunEvidenceReceipt) or not _evidence_matches_experiment(item, experiment):
                    raise _Failure("OOS_SEALED_EXPOSURE_VIOLATION")
            first = min(
                oos,
                key=lambda item: (
                    item.oos_exposure_ordinal,
                    _dt(item.created_at),
                    item.run_evidence_receipt_id,
                ),
            )
            terminal = (
                "EVIDENCE_INCONCLUSIVE"
                if first.result_status in {"EVIDENCE_INVALIDATED_AFTER_RUN", "OOS_REUSED_DIAGNOSTIC"}
                else first.result_status
            )
            if terminal not in _TERMINAL_STATUSES:
                raise _Failure("OOS_SEALED_EXPOSURE_VIOLATION")
        elif evidence_receipts:
            raise _Failure("PREREGISTRATION_STATE_INVALID")
        timestamp = _utc(occurred_at)
        minimum_time = prior[-1].occurred_at if prior else experiment.preregistered_at
        if _dt(timestamp) < _dt(minimum_time):
            raise _Failure("PREREGISTRATION_STATE_INVALID")
        preimage = {
            "schema_id": _schema("lifecycle-receipt"), "schema_version": EXPERIMENT_OS_SCHEMA_VERSION,
            "experiment_id": experiment.experiment_id, "sequence_number": len(prior),
            "previous_lifecycle_receipt_id": prior[-1].lifecycle_receipt_id if prior else None,
            "action": expected_action, "from_state": from_state, "to_state": to_state,
            "occurred_at": timestamp, "provenance": _text(provenance),
            "terminal_result_status": terminal,
        }
        record = LifecycleReceipt(
            preimage["schema_id"], EXPERIMENT_OS_SCHEMA_VERSION,
            _digest("lifecycle_receipt", "lifecyclereceipt:sha256:", preimage),
            experiment.experiment_id, len(prior), preimage["previous_lifecycle_receipt_id"],
            expected_action, from_state, to_state, timestamp, preimage["provenance"],
            terminal, True, True,
        )
        return _valid(record)
    except _Failure as failure:
        return _rejected(failure.code)
    except Exception:
        return _rejected("INTERNAL_VALIDATION_FAILED")


def validate_lifecycle(experiment: object, receipts: object) -> ExperimentControlResult:
    try:
        _validate_public_record(experiment)
        if not isinstance(experiment, PreregisteredExperiment):
            raise _Failure("FIELD_TYPE_INVALID")
        validated = _validate_lifecycle_tuple(experiment, receipts)
        return _valid(validated[-1] if validated else experiment, "EXPERIMENT_LIFECYCLE_VALID")
    except _Failure as failure:
        return _rejected(failure.code)
    except Exception:
        return _rejected("INTERNAL_VALIDATION_FAILED")


_EVIDENCE_KEYS = frozenset({
    "metric_results", "baseline_results", "baseline_membership_hash",
    "candidate_criterion_met", "baseline_criterion_met", "uncertainty_state",
    "created_at", "creation_provenance",
})


def membership_hash(split: TemporalSplitManifest, role: str) -> str:
    _validate_public_record(split)
    if not isinstance(split, TemporalSplitManifest):
        raise _Failure("FIELD_TYPE_INVALID")
    role_value = _enum(role, RESEARCH_ROLES)
    ids = {
        "FORMATION": split.formation_sample_ids,
        "SELECTION": split.selection_sample_ids,
        "OUT_OF_SAMPLE": split.oos_sample_ids,
    }[role_value]
    return _raw_hash({
        "split_assignment_id": split.split_assignment_id,
        "evaluated_role": role_value,
        "sample_ids": list(ids),
    })


def _evidence_payloads(
    experiment: PreregisteredExperiment, baseline_definition: BaselineDefinition,
    value: Mapping[str, object], supplied_membership: str,
) -> tuple[str, str, bool, bool]:
    metrics = _mapping(
        value["metric_results"],
        frozenset({"primary_metric_value", "secondary_metric_values"}),
    )
    primary_value = _text(metrics["primary_metric_value"])
    primary_decimal = _decimal(primary_value)
    secondary = metrics["secondary_metric_values"]
    if not isinstance(secondary, Mapping) or set(secondary) != set(experiment.secondary_metric_ids):
        raise _Failure("FIELD_VALUE_INVALID")
    secondary_values: dict[str, str] = {}
    for metric_id in experiment.secondary_metric_ids:
        metric_value = _text(secondary[metric_id])
        _decimal(metric_value)
        secondary_values[metric_id] = metric_value
    metric_json = _canonical_mapping_json({
        "primary_metric_value": primary_value,
        "secondary_metric_values": secondary_values,
    })

    baseline = _mapping(
        value["baseline_results"],
        frozenset({"baseline_metric_value", "membership_hash"}),
    )
    baseline_value = _text(baseline["baseline_metric_value"])
    baseline_decimal = _decimal(baseline_value)
    if _sha(baseline["membership_hash"]) != supplied_membership:
        raise _Failure("FIELD_VALUE_INVALID")
    baseline_met = (
        primary_decimal >= baseline_decimal
        if baseline_definition.acceptance_rule == "CANDIDATE_GTE_BASELINE"
        else primary_decimal <= baseline_decimal
    )
    baseline_json = _canonical_mapping_json({
        "baseline_metric_value": baseline_value,
        "membership_hash": supplied_membership,
    })

    try:
        threshold_value = json.loads(experiment.acceptance_thresholds_json)
    except (TypeError, ValueError, UnicodeError):
        raise _Failure("FIELD_VALUE_INVALID") from None
    threshold = _threshold_mapping(threshold_value)
    limit = _decimal(threshold["primary_metric_threshold"])
    candidate_met = primary_decimal >= limit if threshold["primary_metric_operator"] == "GTE" else primary_decimal <= limit
    supplied_candidate = value["candidate_criterion_met"]
    supplied_baseline = value["baseline_criterion_met"]
    if not isinstance(supplied_candidate, bool) or not isinstance(supplied_baseline, bool):
        raise _Failure("FIELD_TYPE_INVALID")
    if supplied_candidate is not candidate_met or supplied_baseline is not baseline_met:
        raise _Failure("FIELD_VALUE_INVALID")
    return metric_json, baseline_json, candidate_met, baseline_met


def _validate_evidence_against_experiment(
    evidence: RunEvidenceReceipt, experiment: PreregisteredExperiment,
    baseline_definition: BaselineDefinition,
) -> None:
    if not _evidence_matches_experiment(evidence, experiment):
        raise _Failure("TRIAL_FAMILY_CONFLICT")
    metrics = json.loads(_validate_canonical_mapping_json(evidence.metric_results_json))
    metric_mapping = _mapping(
        metrics, frozenset({"primary_metric_value", "secondary_metric_values"}),
    )
    secondary = metric_mapping["secondary_metric_values"]
    if not isinstance(secondary, Mapping) or set(secondary) != set(experiment.secondary_metric_ids):
        raise _Failure("FIELD_VALUE_INVALID")
    primary_value = _decimal(metric_mapping["primary_metric_value"])
    for value in secondary.values():
        _decimal(value)
    threshold = _threshold_mapping(json.loads(experiment.acceptance_thresholds_json))
    limit = _decimal(threshold["primary_metric_threshold"])
    candidate_met = primary_value >= limit if threshold["primary_metric_operator"] == "GTE" else primary_value <= limit
    baseline = _mapping(
        json.loads(_validate_canonical_mapping_json(evidence.baseline_results_json)),
        frozenset({"baseline_metric_value", "membership_hash"}),
    )
    baseline_value = _decimal(baseline["baseline_metric_value"])
    baseline_met = (
        primary_value >= baseline_value
        if baseline_definition.acceptance_rule == "CANDIDATE_GTE_BASELINE"
        else primary_value <= baseline_value
    )
    if (
        evidence.candidate_criterion_met is not candidate_met
        or evidence.baseline_criterion_met is not baseline_met
        or baseline["membership_hash"] != evidence.membership_hash
        or evidence.baseline_id != baseline_definition.baseline_definition_id
    ):
        raise _Failure("FIELD_VALUE_INVALID")


def _role_evidence_ready_time(
    experiment: PreregisteredExperiment,
    dataset_manifest: ResearchDatasetManifest,
    split_manifest: TemporalSplitManifest,
    role: str,
) -> datetime:
    if (
        experiment.research_dataset_manifest_id
        != dataset_manifest.research_dataset_manifest_id
        or split_manifest.dataset_manifest_id
        != dataset_manifest.research_dataset_manifest_id
        or experiment.split_plan_id != split_manifest.split_plan_id
        or experiment.dataset_binding_id != dataset_manifest.dataset_binding_id
        or experiment.dataset_binding_id != split_manifest.dataset_binding_id
        or experiment.feature_definition_ids != dataset_manifest.feature_definition_ids
        or experiment.feature_definition_ids != split_manifest.feature_definition_ids
        or experiment.feature_set_id != dataset_manifest.feature_set_id
        or experiment.feature_set_id != split_manifest.feature_set_id
        or experiment.label_definition_id != dataset_manifest.label_definition_id
        or experiment.label_definition_id != split_manifest.label_definition_id
    ):
        raise _Failure("SPLIT_INVALID")
    rebuilt = build_temporal_split_manifest(dataset_manifest, {
        "split_plan_version": split_manifest.split_plan_version,
        "formation_start": split_manifest.formation_start,
        "selection_start": split_manifest.selection_start,
        "oos_start": split_manifest.oos_start,
        "end_time": split_manifest.end_time,
        "purge_rule": split_manifest.purge_rule,
        "embargo_seconds": split_manifest.embargo_seconds,
        "group_policy": split_manifest.group_policy,
        "inclusion_policy": split_manifest.inclusion_policy,
        "min_samples_per_role": split_manifest.min_samples_per_role,
    })
    if not rebuilt.is_valid or rebuilt.record != split_manifest:
        raise _Failure("SPLIT_INVALID")
    role_sample_ids = {
        "FORMATION": split_manifest.formation_sample_ids,
        "SELECTION": split_manifest.selection_sample_ids,
        "OUT_OF_SAMPLE": split_manifest.oos_sample_ids,
    }[role]
    samples_by_id = {sample.sample_id: sample for sample in dataset_manifest.samples}
    if not role_sample_ids or any(
        sample_id not in samples_by_id for sample_id in role_sample_ids
    ):
        raise _Failure("SPLIT_INVALID")
    return max(
        _dt(samples_by_id[sample_id].label_availability_time)
        for sample_id in role_sample_ids
    )


def _build_run_evidence_receipt(
    experiment: object, dataset_manifest: object, split_manifest: object,
    baseline_definition: object, lifecycle_receipts: object,
    prior_evidence: object, input_mapping: object, *, allow_oos: bool,
    prior_oos_release_count: int,
) -> ExperimentControlResult:
    try:
        _validate_public_record(experiment)
        _validate_public_record(dataset_manifest)
        _validate_public_record(split_manifest)
        _validate_public_record(baseline_definition)
        if (
            not isinstance(experiment, PreregisteredExperiment)
            or not isinstance(dataset_manifest, ResearchDatasetManifest)
            or not isinstance(split_manifest, TemporalSplitManifest)
            or not isinstance(baseline_definition, BaselineDefinition)
        ):
            raise _Failure("FIELD_TYPE_INVALID")
        if (
            experiment.split_assignment_id != split_manifest.split_assignment_id
            or experiment.baseline_id != baseline_definition.baseline_definition_id
        ):
            raise _Failure("SPLIT_INVALID")
        lifecycle = _validate_lifecycle_tuple(experiment, lifecycle_receipts)
        if not isinstance(prior_evidence, (list, tuple)):
            raise _Failure("FIELD_TYPE_INVALID")
        prior = tuple(prior_evidence)
        seen_evidence_ids: set[str] = set()
        for item in prior:
            _validate_public_record(item)
            if (
                not isinstance(item, RunEvidenceReceipt)
                or item.run_evidence_receipt_id in seen_evidence_ids
            ):
                raise _Failure("PREREGISTRATION_STATE_INVALID")
            seen_evidence_ids.add(item.run_evidence_receipt_id)
        value = _mapping(input_mapping, _EVIDENCE_KEYS)
        # The frozen schema intentionally does not permit an extra key. Derive the role
        # from the caller's baseline_membership_hash by exact unique membership match.
        supplied_membership = _sha(value["baseline_membership_hash"])
        matching_roles = [candidate for candidate in RESEARCH_ROLES if membership_hash(split_manifest, candidate) == supplied_membership]
        if len(matching_roles) != 1:
            raise _Failure("SPLIT_INVALID")
        role = matching_roles[0]
        if role == "OUT_OF_SAMPLE" and not allow_oos:
            raise _Failure("OOS_SEALED_EXPOSURE_VIOLATION")
        required_state = {"FORMATION": "FORMATION_ACTIVE", "SELECTION": "SELECTION_ACTIVE", "OUT_OF_SAMPLE": "OOS_RELEASED"}[role]
        if not lifecycle or lifecycle[-1].to_state != required_state:
            raise _Failure("OOS_SEALED_EXPOSURE_VIOLATION" if role == "OUT_OF_SAMPLE" else "PREREGISTRATION_STATE_INVALID")
        uncertainty = _enum(value["uncertainty_state"], UNCERTAINTY_STATES)
        metrics_json, baseline_json, candidate_met, baseline_met = _evidence_payloads(
            experiment, baseline_definition, value, supplied_membership,
        )
        if not isinstance(prior_oos_release_count, int) or isinstance(prior_oos_release_count, bool) or prior_oos_release_count < 0:
            raise _Failure("FIELD_TYPE_INVALID")
        prior_ordinals = [
            item.oos_exposure_ordinal for item in prior
            if item.evaluated_role == "OUT_OF_SAMPLE" and item.membership_hash == supplied_membership
        ]
        ordinal = 1 + max(prior_oos_release_count, max(prior_ordinals, default=0)) if role == "OUT_OF_SAMPLE" else 0
        if role == "OUT_OF_SAMPLE" and ordinal > 1:
            result_status = "OOS_REUSED_DIAGNOSTIC"
        elif uncertainty == "INVALIDATED_AFTER_RUN":
            result_status = "EVIDENCE_INVALIDATED_AFTER_RUN"
        elif uncertainty == "INCONCLUSIVE":
            result_status = "EVIDENCE_INCONCLUSIVE"
        elif not candidate_met or not baseline_met:
            result_status = "EVIDENCE_NEGATIVE"
        else:
            result_status = {
                "FORMATION": "FORMATION_CRITERIA_MET",
                "SELECTION": "SELECTION_CRITERIA_MET",
                "OUT_OF_SAMPLE": "OOS_CRITERIA_MET_UNCOSTED",
            }[role]
        created_at = _utc(value["created_at"])
        if _dt(created_at) < _dt(lifecycle[-1].occurred_at):
            raise _Failure("OOS_SEALED_EXPOSURE_VIOLATION" if role == "OUT_OF_SAMPLE" else "PREREGISTRATION_STATE_INVALID")
        if _dt(created_at) < _role_evidence_ready_time(
            experiment, dataset_manifest, split_manifest, role,
        ):
            raise _Failure("LABEL_TIMING_INVALID")
        current_prior = [item for item in prior if _evidence_matches_experiment(item, experiment)]
        if current_prior and _dt(created_at) < max(_dt(item.created_at) for item in current_prior):
            raise _Failure("PREREGISTRATION_STATE_INVALID")
        metric_ids = (experiment.primary_metric_id,) + experiment.secondary_metric_ids
        preimage = {
            "schema_id": _schema("run-evidence-receipt"), "schema_version": EXPERIMENT_OS_SCHEMA_VERSION,
            "experiment_id": experiment.experiment_id,
            "experiment_family_id": experiment.experiment_family_id,
            "trial_number": experiment.trial_number, "dataset_binding_id": experiment.dataset_binding_id,
            "research_dataset_manifest_id": experiment.research_dataset_manifest_id,
            "split_assignment_id": split_manifest.split_assignment_id,
            "membership_hash": supplied_membership, "feature_set_id": experiment.feature_set_id,
            "label_definition_id": experiment.label_definition_id, "code_version": experiment.code_version,
            "parameters_json": experiment.parameters_json, "random_seeds": list(experiment.random_seeds),
            "evaluated_role": role, "metric_definition_ids": list(metric_ids),
            "baseline_id": experiment.baseline_id, "metric_results_json": metrics_json,
            "baseline_results_json": baseline_json,
            "candidate_criterion_met": candidate_met,
            "baseline_criterion_met": baseline_met,
            "uncertainty_state": uncertainty,
            "result_status": result_status, "oos_exposure_ordinal": ordinal,
            "created_at": created_at,
            "creation_provenance": _text(value["creation_provenance"]),
        }
        record = RunEvidenceReceipt(
            preimage["schema_id"], EXPERIMENT_OS_SCHEMA_VERSION,
            _digest("run_evidence_receipt", "runevidence:sha256:", preimage),
            experiment.experiment_id, experiment.experiment_family_id, experiment.trial_number,
            experiment.dataset_binding_id, experiment.research_dataset_manifest_id,
            split_manifest.split_assignment_id, supplied_membership, experiment.feature_set_id,
            experiment.label_definition_id, experiment.code_version, experiment.parameters_json,
            experiment.random_seeds, role, metric_ids, experiment.baseline_id, metrics_json,
            baseline_json, candidate_met, baseline_met, uncertainty, result_status, ordinal, preimage["created_at"],
            preimage["creation_provenance"], True, True,
        )
        return _valid(record)
    except _Failure as failure:
        return _rejected(failure.code)
    except Exception:
        return _rejected("INTERNAL_VALIDATION_FAILED")


def build_run_evidence_receipt(
    experiment: object, dataset_manifest: object, split_manifest: object,
    baseline_definition: object, lifecycle_receipts: object,
    prior_evidence: object, input_mapping: object,
) -> ExperimentControlResult:
    """Build formation/selection evidence; OOS requires atomic registry authority."""
    return _build_run_evidence_receipt(
        experiment, dataset_manifest, split_manifest, baseline_definition,
        lifecycle_receipts,
        prior_evidence, input_mapping,
        allow_oos=False, prior_oos_release_count=0,
    )


_RECORD_ID_FIELD = {
    DatasetBinding: ("dataset_binding", "datasetbinding:sha256:", "dataset_binding_id"),
    ExternalDatasetBinding: ("external_dataset_binding", "datasetbinding:sha256:", "dataset_binding_id"),
    FeatureDefinition: ("feature_definition", "featuredef:sha256:", "feature_definition_id"),
    LabelDefinition: ("label_definition", "labeldef:sha256:", "label_definition_id"),
    ResearchSample: ("sample", "sample:sha256:", "sample_id"),
    ResearchDatasetManifest: ("research_dataset_manifest", "researchdataset:sha256:", "research_dataset_manifest_id"),
    TemporalSplitManifest: ("temporal_split", "split:sha256:", "split_assignment_id"),
    AlphaHypothesis: ("hypothesis", "hypothesis:sha256:", "hypothesis_id"),
    MetricDefinition: ("metric", "metric:sha256:", "metric_definition_id"),
    BaselineDefinition: ("baseline", "baseline:sha256:", "baseline_definition_id"),
    ExperimentFamily: ("experiment_family", "experimentfamily:sha256:", "experiment_family_id"),
    PreregisteredExperiment: ("preregistered_experiment", "experiment:sha256:", "experiment_id"),
    LifecycleReceipt: ("lifecycle_receipt", "lifecyclereceipt:sha256:", "lifecycle_receipt_id"),
    RunEvidenceReceipt: ("run_evidence_receipt", "runevidence:sha256:", "run_evidence_receipt_id"),
}


def _identity_preimage(record: object) -> tuple[str, str, str, dict[str, object]]:
    record_type = type(record)
    if record_type not in _RECORD_ID_FIELD:
        raise _Failure("FIELD_TYPE_INVALID")
    kind, prefix, id_field = _RECORD_ID_FIELD[record_type]
    mapping = asdict(record)
    identity = mapping.pop(id_field)
    mapping.pop("advisory_only")
    mapping.pop("no_execution_authority")
    return kind, prefix, identity, mapping


_EXPECTED_RECORD_SCHEMAS = {
    DatasetBinding: "polymarket-experiment-dataset-binding",
    ExternalDatasetBinding: EXTERNAL_DATASET_BINDING_SCHEMA_ID,
    FeatureDefinition: "polymarket-feature-definition",
    LabelDefinition: "polymarket-label-definition",
    ResearchSample: "polymarket-research-sample",
    ResearchDatasetManifest: "polymarket-research-dataset-manifest",
    TemporalSplitManifest: "polymarket-temporal-split-manifest",
    AlphaHypothesis: "polymarket-hypothesis",
    MetricDefinition: "polymarket-metric-definition",
    BaselineDefinition: "polymarket-baseline-definition",
    ExperimentFamily: "polymarket-experiment-family",
    PreregisteredExperiment: "polymarket-preregistered-experiment",
    LifecycleReceipt: "polymarket-lifecycle-receipt",
    RunEvidenceReceipt: "polymarket-run-evidence-receipt",
}


def _validate_public_record_semantics(record: object) -> None:
    if record.schema_id != _EXPECTED_RECORD_SCHEMAS[type(record)]:
        raise _Failure("SCHEMA_UNSUPPORTED")
    if isinstance(record, ExternalDatasetBinding):
        # Provenance-separated external binding: never canonical PIT. The generic
        # datasetbinding:sha256: id derivation is verified by _validate_public_record.
        _enum(record.source_kind, (EXTERNAL_DATASET_BINDING_SOURCE_KIND,))
        _opaque(record.source_external_dataset_id)
        _opaque(record.source_lineage_id)
        _sha(record.source_membership_digest)
        _member_count(record.source_member_count)
        _opaque(record.instrument_id)
        _text(record.conversion_policy_version)
        first_event = _time_ns(record.first_event_time_ns)
        last_event = _time_ns(record.last_event_time_ns)
        first_availability = _time_ns(record.first_availability_time_ns)
        last_availability = _time_ns(record.last_availability_time_ns)
        if first_event > last_event or first_availability > last_availability:
            raise _Failure("FIELD_VALUE_INVALID")
        _opaque(record.code_version)
    elif isinstance(record, DatasetBinding):
        for value in (
            record.dataset_snapshot_reference_id,
            record.dataset_reference_schema_version,
            record.source_reference_id,
            record.code_version,
        ):
            _opaque(value)
        reference = _decode_dataset_reference_json(record.dataset_snapshot_reference_json)
        if (
            reference.dataset_snapshot_reference_id != record.dataset_snapshot_reference_id
            or reference.schema_version != record.dataset_reference_schema_version
            or reference.human_review_required
            or reference.review_conflict_record_version_ids
            or reference.advisory_only is not True
            or reference.no_execution_authority is not True
        ):
            raise _Failure("DATASET_REFERENCE_INVALID")
        analytical = (
            record.analytical_logical_dataset_id,
            record.analytical_identity_json,
            record.analytical_schema_version,
            record.materializer_version,
        )
        if any(value is None for value in analytical) != all(value is None for value in analytical):
            raise _Failure("DATASET_REFERENCE_INVALID")
        for value in (
            record.analytical_logical_dataset_id,
            record.analytical_schema_version,
        ):
            _opaque(value, nullable=True)
        _text(record.materializer_version, nullable=True)
        if record.source_reference_id != record.dataset_snapshot_reference_id:
            raise _Failure("DATASET_REFERENCE_INVALID")
        if record.analytical_logical_dataset_id is not None:
            analytical_json = _validate_analytical_identity_json(
                record.analytical_identity_json, record.analytical_logical_dataset_id,
            )
            decoded = json.loads(analytical_json)
            if (
                decoded["source_reference_id"] != record.dataset_snapshot_reference_id
                or decoded["analytical_schema_version"] != record.analytical_schema_version
                or decoded["materializer_version"] != record.materializer_version
            ):
                raise _Failure("DATASET_REFERENCE_INVALID")
    elif isinstance(record, FeatureDefinition):
        _opaque(record.feature_name)
        _opaque(record.feature_version)
        _text(record.description)
        if not isinstance(record.source_dependencies, tuple) or _tuple_text(record.source_dependencies) != record.source_dependencies:
            raise _Failure("FIELD_VALUE_INVALID")
        parameters_json = _validate_canonical_mapping_json(record.parameters_json)
        parameters = json.loads(parameters_json)
        _validate_feature_information(
            record.source_dependencies, record.lookback_rule, record.availability_rule,
            record.no_future_information_rule, parameters,
        )
        _text(record.missing_data_policy)
        _opaque(record.transformation_version)
    elif isinstance(record, LabelDefinition):
        _opaque(record.label_name)
        _opaque(record.label_version)
        for value in (
            record.prediction_target,
            record.horizon_rule,
            record.target_time_rule,
            record.outcome_source_rule,
            record.availability_time_rule,
            record.censoring_rule,
        ):
            _text(value)
        _validate_canonical_mapping_json(record.parameters_json)
        _opaque(record.code_version)
    elif isinstance(record, ResearchSample):
        _opaque(record.dataset_binding_id)
        if not isinstance(record.source_record_version_ids, tuple) or _tuple_text(record.source_record_version_ids) != record.source_record_version_ids:
            raise _Failure("DATASET_REFERENCE_INVALID")
        expected_membership = _raw_hash({"source_record_version_ids": list(record.source_record_version_ids)})
        expected_lineage = _raw_hash({
            "dataset_binding_id": record.dataset_binding_id,
            "source_record_version_ids": list(record.source_record_version_ids),
        })
        if record.source_membership_digest != expected_membership or record.lineage_digest != expected_lineage:
            raise _Failure("DATASET_REFERENCE_INVALID")
        _opaque(record.market_id)
        _opaque(record.related_group_id, nullable=True)
        _opaque(record.leakage_group_id, nullable=True)
        decision = _dt(_utc(record.decision_time))
        feature = _dt(_utc(record.feature_availability_time))
        target = _dt(_utc(record.target_time))
        label = _dt(_utc(record.label_availability_time))
        if feature > decision:
            raise _Failure("FEATURE_TIMING_LEAKAGE")
        if not decision <= target <= label:
            raise _Failure("LABEL_TIMING_INVALID")
        _opaque(record.feature_set_id)
        _opaque(record.label_definition_id)
        _sha(record.lineage_digest)
    elif isinstance(record, ResearchDatasetManifest):
        _opaque(record.dataset_binding_id)
        if not isinstance(record.feature_definition_ids, tuple) or _tuple_text(record.feature_definition_ids) != record.feature_definition_ids:
            raise _Failure("FIELD_VALUE_INVALID")
        expected_feature_set = _digest(
            "feature_set", "featureset:sha256:",
            {"feature_definition_ids": list(record.feature_definition_ids)},
        )
        if record.feature_set_id != expected_feature_set:
            raise _Failure("IDENTITY_DERIVATION_MISMATCH")
        _opaque(record.label_definition_id)
        policy = _enum(record.group_policy, GROUP_POLICIES)
        if not isinstance(record.samples, tuple) or not record.samples or len(record.samples) > MAX_SAMPLES:
            raise _Failure("FIELD_TYPE_INVALID" if not isinstance(record.samples, tuple) else "FIELD_VALUE_INVALID")
        if record.total_sample_count != len(record.samples) or record.assignment_order != "SAMPLE_ID_ASC":
            raise _Failure("DATASET_REFERENCE_INVALID")
        if tuple(sorted(sample.sample_id for sample in record.samples)) != tuple(sample.sample_id for sample in record.samples):
            raise _Failure("DATASET_REFERENCE_INVALID")
        if len({sample.sample_id for sample in record.samples}) != len(record.samples):
            raise _Failure("DATASET_REFERENCE_INVALID")
        membership: dict[str, ResearchSample] = {}
        for sample in record.samples:
            _validate_public_record(sample)
            if (
                sample.dataset_binding_id != record.dataset_binding_id
                or sample.feature_set_id != record.feature_set_id
                or sample.label_definition_id != record.label_definition_id
                or (policy == "EXCLUSIVE") != (sample.leakage_group_id is not None)
            ):
                raise _Failure("DATASET_REFERENCE_INVALID")
            prior = membership.setdefault(sample.source_membership_digest, sample)
            if prior != sample:
                raise _Failure("DATASET_REFERENCE_INVALID")
    elif isinstance(record, TemporalSplitManifest):
        _opaque(record.split_plan_version)
        _opaque(record.dataset_manifest_id)
        _opaque(record.dataset_binding_id)
        if not isinstance(record.feature_definition_ids, tuple) or _tuple_text(record.feature_definition_ids) != record.feature_definition_ids:
            raise _Failure("FIELD_VALUE_INVALID")
        expected_feature_set = _digest(
            "feature_set", "featureset:sha256:",
            {"feature_definition_ids": list(record.feature_definition_ids)},
        )
        if record.feature_set_id != expected_feature_set:
            raise _Failure("IDENTITY_DERIVATION_MISMATCH")
        _opaque(record.label_definition_id)
        boundaries = tuple(_dt(_utc(value)) for value in (
            record.formation_start, record.selection_start, record.oos_start, record.end_time,
        ))
        if not all(boundaries[index] < boundaries[index + 1] for index in range(3)):
            raise _Failure("SPLIT_INVALID")
        _enum(record.purge_rule, ("PURGE_LABEL_AVAILABILITY_AT_OR_AFTER_NEXT_BOUNDARY",))
        _enum(record.group_policy, GROUP_POLICIES)
        _enum(record.inclusion_policy, ("DECISION_TIME_HALF_OPEN",))
        if not isinstance(record.embargo_seconds, int) or isinstance(record.embargo_seconds, bool) or record.embargo_seconds < 0:
            raise _Failure("FIELD_TYPE_INVALID")
        if not isinstance(record.min_samples_per_role, int) or isinstance(record.min_samples_per_role, bool) or record.min_samples_per_role < 1:
            raise _Failure("FIELD_TYPE_INVALID")
        groups = (
            record.formation_sample_ids, record.selection_sample_ids, record.oos_sample_ids,
            record.purged_sample_ids, record.embargoed_sample_ids,
        )
        for values in groups:
            if not isinstance(values, tuple) or _tuple_text(values, allow_empty=True) != values:
                raise _Failure("FIELD_VALUE_INVALID")
        if any(len(values) < record.min_samples_per_role for values in groups[:3]):
            raise _Failure("SPLIT_INVALID")
        flattened = [item for values in groups for item in values]
        if len(flattened) != len(set(flattened)):
            raise _Failure("SPLIT_INVALID")
        plan_preimage = {
            "split_plan_version": record.split_plan_version,
            "formation_start": record.formation_start,
            "selection_start": record.selection_start,
            "oos_start": record.oos_start,
            "end_time": record.end_time,
            "purge_rule": record.purge_rule,
            "embargo_seconds": record.embargo_seconds,
            "group_policy": record.group_policy,
            "inclusion_policy": record.inclusion_policy,
            "min_samples_per_role": record.min_samples_per_role,
        }
        if record.split_plan_id != _digest("split_plan", "splitplan:sha256:", plan_preimage):
            raise _Failure("IDENTITY_DERIVATION_MISMATCH")
        assignment = {
            "formation_sample_ids": list(record.formation_sample_ids),
            "selection_sample_ids": list(record.selection_sample_ids),
            "oos_sample_ids": list(record.oos_sample_ids),
            "purged_sample_ids": list(record.purged_sample_ids),
            "embargoed_sample_ids": list(record.embargoed_sample_ids),
        }
        if record.assignment_hash != _raw_hash(assignment):
            raise _Failure("IDENTITY_DERIVATION_MISMATCH")
    elif isinstance(record, AlphaHypothesis):
        _opaque(record.hypothesis_name)
        _opaque(record.hypothesis_version)
        if not isinstance(record.predecessor_candidate_ids, tuple) or _tuple_text(record.predecessor_candidate_ids, allow_empty=True) != record.predecessor_candidate_ids:
            raise _Failure("FIELD_VALUE_INVALID")
        for value in (
            record.falsifiable_claim, record.proposed_mechanism, record.cohort,
            record.horizon, record.target, record.falsification_condition,
            record.review_assertion, record.creation_provenance,
        ):
            _text(value)
        _enum(record.human_review_state, ("REVIEWED",))
        _opaque(record.code_version)
    elif isinstance(record, MetricDefinition):
        _opaque(record.metric_name)
        _opaque(record.metric_version)
        _enum(record.direction, METRIC_DIRECTIONS)
        _validate_canonical_mapping_json(record.parameters_json)
        _opaque(record.code_version)
    elif isinstance(record, BaselineDefinition):
        _opaque(record.baseline_name)
        _opaque(record.baseline_version)
        _text(record.method_rule)
        _validate_canonical_mapping_json(record.parameters_json)
        if record.same_partition_required is not True:
            raise _Failure("FIELD_VALUE_INVALID")
        _enum(record.acceptance_rule, _BASELINE_ACCEPTANCE_RULES)
        _opaque(record.code_version)
    elif isinstance(record, ExperimentFamily):
        for value in (record.research_program, record.cohort, record.target, record.metric_family):
            _text(value)
        _enum(record.correction_policy, CORRECTION_POLICIES)
        _opaque(record.predecessor_family_id, nullable=True)
    elif isinstance(record, PreregisteredExperiment):
        for value in (
            record.experiment_family_id, record.hypothesis_id, record.dataset_binding_id,
            record.research_dataset_manifest_id, record.feature_set_id,
            record.label_definition_id, record.split_plan_id, record.split_assignment_id,
            record.primary_metric_id, record.baseline_id,
        ):
            _opaque(value)
        if not isinstance(record.trial_number, int) or isinstance(record.trial_number, bool) or record.trial_number < 1:
            raise _Failure("FIELD_TYPE_INVALID")
        if not isinstance(record.feature_definition_ids, tuple) or _tuple_text(record.feature_definition_ids) != record.feature_definition_ids:
            raise _Failure("FIELD_VALUE_INVALID")
        expected_feature_set = _digest(
            "feature_set", "featureset:sha256:",
            {"feature_definition_ids": list(record.feature_definition_ids)},
        )
        if record.feature_set_id != expected_feature_set:
            raise _Failure("IDENTITY_DERIVATION_MISMATCH")
        if not isinstance(record.secondary_metric_ids, tuple) or _tuple_text(record.secondary_metric_ids, allow_empty=True) != record.secondary_metric_ids or record.primary_metric_id in record.secondary_metric_ids:
            raise _Failure("FIELD_VALUE_INVALID")
        _text(record.inclusion_exclusion_rules)
        threshold_json = _validate_canonical_mapping_json(record.acceptance_thresholds_json)
        _threshold_mapping(json.loads(threshold_json))
        _validate_canonical_mapping_json(record.search_space_json)
        _validate_canonical_mapping_json(record.parameters_json)
        if not isinstance(record.random_seeds, tuple) or _tuple_int(record.random_seeds) != record.random_seeds:
            raise _Failure("FIELD_VALUE_INVALID")
        _enum(record.correction_policy, CORRECTION_POLICIES)
        _opaque(record.cost_model_reference, nullable=True)
        _text(record.stop_failure_rules)
        _opaque(record.code_version)
        _text(record.creation_provenance)
        _utc(record.preregistered_at)
    elif isinstance(record, LifecycleReceipt):
        _opaque(record.experiment_id)
        if not isinstance(record.sequence_number, int) or isinstance(record.sequence_number, bool) or not 0 <= record.sequence_number < len(LIFECYCLE_ACTIONS):
            raise _Failure("PREREGISTRATION_STATE_INVALID")
        expected_action, expected_from, expected_to = _lifecycle_expected(record.sequence_number)
        if (record.action, record.from_state, record.to_state) != (expected_action, expected_from, expected_to):
            raise _Failure("PREREGISTRATION_STATE_INVALID")
        _opaque(record.previous_lifecycle_receipt_id, nullable=True)
        _utc(record.occurred_at)
        _text(record.provenance)
        if record.action == "CLOSE_EXPERIMENT":
            if record.terminal_result_status not in _TERMINAL_STATUSES:
                raise _Failure("OOS_SEALED_EXPOSURE_VIOLATION")
        elif record.terminal_result_status is not None:
            raise _Failure("PREREGISTRATION_STATE_INVALID")
    elif isinstance(record, RunEvidenceReceipt):
        for value in (
            record.experiment_id, record.experiment_family_id, record.dataset_binding_id,
            record.research_dataset_manifest_id, record.split_assignment_id,
            record.feature_set_id, record.label_definition_id, record.code_version,
            record.baseline_id,
        ):
            _opaque(value)
        if not isinstance(record.trial_number, int) or isinstance(record.trial_number, bool) or record.trial_number < 1:
            raise _Failure("FIELD_TYPE_INVALID")
        _sha(record.membership_hash)
        _validate_canonical_mapping_json(record.parameters_json)
        if not isinstance(record.random_seeds, tuple) or _tuple_int(record.random_seeds) != record.random_seeds:
            raise _Failure("FIELD_VALUE_INVALID")
        role = _enum(record.evaluated_role, RESEARCH_ROLES)
        if not isinstance(record.metric_definition_ids, tuple) or _tuple_text(record.metric_definition_ids, sort_values=False) != record.metric_definition_ids:
            raise _Failure("FIELD_VALUE_INVALID")
        metric_json = _validate_canonical_mapping_json(record.metric_results_json)
        metric_results = _mapping(
            json.loads(metric_json),
            frozenset({"primary_metric_value", "secondary_metric_values"}),
        )
        _decimal(metric_results["primary_metric_value"])
        if not isinstance(metric_results["secondary_metric_values"], Mapping):
            raise _Failure("FIELD_TYPE_INVALID")
        for value in metric_results["secondary_metric_values"].values():
            _decimal(value)
        baseline_json = _validate_canonical_mapping_json(record.baseline_results_json)
        baseline_results = _mapping(
            json.loads(baseline_json),
            frozenset({"baseline_metric_value", "membership_hash"}),
        )
        if (
            not isinstance(record.candidate_criterion_met, bool)
            or not isinstance(record.baseline_criterion_met, bool)
            or _sha(baseline_results["membership_hash"]) != record.membership_hash
        ):
            raise _Failure("FIELD_VALUE_INVALID")
        _decimal(baseline_results["baseline_metric_value"])
        uncertainty = _enum(record.uncertainty_state, UNCERTAINTY_STATES)
        _enum(record.result_status, EVIDENCE_STATUSES)
        if role == "OUT_OF_SAMPLE":
            if not isinstance(record.oos_exposure_ordinal, int) or isinstance(record.oos_exposure_ordinal, bool) or record.oos_exposure_ordinal < 1:
                raise _Failure("OOS_SEALED_EXPOSURE_VIOLATION")
        elif record.oos_exposure_ordinal != 0 or record.result_status == "OOS_REUSED_DIAGNOSTIC":
            raise _Failure("OOS_SEALED_EXPOSURE_VIOLATION")
        if role == "OUT_OF_SAMPLE" and record.oos_exposure_ordinal > 1:
            expected_status = "OOS_REUSED_DIAGNOSTIC"
        elif uncertainty == "INVALIDATED_AFTER_RUN":
            expected_status = "EVIDENCE_INVALIDATED_AFTER_RUN"
        elif uncertainty == "INCONCLUSIVE":
            expected_status = "EVIDENCE_INCONCLUSIVE"
        elif not record.candidate_criterion_met or not record.baseline_criterion_met:
            expected_status = "EVIDENCE_NEGATIVE"
        else:
            expected_status = {
                "FORMATION": "FORMATION_CRITERIA_MET",
                "SELECTION": "SELECTION_CRITERIA_MET",
                "OUT_OF_SAMPLE": "OOS_CRITERIA_MET_UNCOSTED",
            }[role]
        if record.result_status != expected_status:
            raise _Failure("FIELD_VALUE_INVALID")
        _utc(record.created_at)
        _text(record.creation_provenance)


def _validate_public_record(record: object) -> None:
    _validate_core_record(record, type(record))
    kind, prefix, identity, preimage = _identity_preimage(record)
    if record.schema_version != EXPERIMENT_OS_SCHEMA_VERSION or record.schema_id != preimage["schema_id"]:
        raise _Failure("SCHEMA_UNSUPPORTED")
    if _digest(kind, prefix, preimage) != identity:
        raise _Failure("IDENTITY_DERIVATION_MISMATCH")
    _validate_public_record_semantics(record)
    if isinstance(record, ResearchDatasetManifest):
        if record.total_sample_count != len(record.samples) or tuple(sorted(s.sample_id for s in record.samples)) != tuple(s.sample_id for s in record.samples):
            raise _Failure("DATASET_REFERENCE_INVALID")
        for sample in record.samples:
            _validate_public_record(sample)
    if isinstance(record, TemporalSplitManifest):
        assignment = {
            "formation_sample_ids": list(record.formation_sample_ids),
            "selection_sample_ids": list(record.selection_sample_ids),
            "oos_sample_ids": list(record.oos_sample_ids),
            "purged_sample_ids": list(record.purged_sample_ids),
            "embargoed_sample_ids": list(record.embargoed_sample_ids),
        }
        if _raw_hash(assignment) != record.assignment_hash:
            raise _Failure("IDENTITY_DERIVATION_MISMATCH")


def record_to_mapping(record: object) -> dict[str, object]:
    _validate_public_record(record)
    return asdict(record)


def record_from_mapping(record_type: type, mapping: object) -> object:
    try:
        if not isinstance(mapping, Mapping) or set(mapping) != {field.name for field in fields(record_type)}:
            raise _Failure("FIELD_VALUE_INVALID")
        converted = dict(mapping)
        tuple_fields = {
            FeatureDefinition: ("source_dependencies",),
            AlphaHypothesis: ("predecessor_candidate_ids",),
            ResearchSample: ("source_record_version_ids",),
            ResearchDatasetManifest: ("feature_definition_ids",),
            TemporalSplitManifest: ("feature_definition_ids", "formation_sample_ids", "selection_sample_ids", "oos_sample_ids", "purged_sample_ids", "embargoed_sample_ids"),
            PreregisteredExperiment: ("feature_definition_ids", "secondary_metric_ids", "random_seeds"),
            RunEvidenceReceipt: ("random_seeds", "metric_definition_ids"),
        }.get(record_type, ())
        if record_type is ResearchDatasetManifest:
            samples = converted.get("samples")
            if not isinstance(samples, list):
                raise _Failure("FIELD_TYPE_INVALID")
            converted["samples"] = tuple(record_from_mapping(ResearchSample, sample) for sample in samples)
        for name in tuple_fields:
            if not isinstance(converted.get(name), list):
                raise _Failure("FIELD_TYPE_INVALID")
            converted[name] = tuple(converted[name])
        record = record_type(**converted)
        _validate_public_record(record)
        return record
    except _Failure:
        raise
    except Exception:
        raise _Failure("REGISTRY_INTEGRITY_TAMPER") from None
