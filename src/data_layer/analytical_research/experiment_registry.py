"""Bounded append-only SQLite registry for validated WP170 research records."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import sqlite3
from typing import Mapping

from .experiment_os import (
    EXTERNAL_DATASET_BINDING_SCHEMA_ID,
    EXTERNAL_MEMBER_ID_PREFIX,
    AlphaHypothesis,
    BaselineDefinition,
    DatasetBinding,
    ExperimentControlResult,
    ExperimentFamily,
    ExternalDatasetBinding,
    FamilySummary,
    FeatureDefinition,
    LabelDefinition,
    LifecycleReceipt,
    MetricDefinition,
    PreregisteredExperiment,
    ResearchDatasetManifest,
    RunEvidenceReceipt,
    TemporalSplitManifest,
    _Failure,
    _build_run_evidence_receipt,
    _canonical_bytes,
    _digest,
    _dt,
    _raw_hash,
    _rejected,
    _role_evidence_ready_time,
    _threshold_mapping,
    _valid,
    _validate_evidence_against_experiment,
    _validate_public_record,
    build_temporal_split_manifest,
    membership_hash,
    record_from_mapping,
    record_to_mapping,
)

REGISTRY_FORMAT_ID = "wp170-experiment-registry"
REGISTRY_SCHEMA_VERSION = 1
REGISTRY_APPLICATION_ID = 1464877424
MAX_REGISTRY_RECORDS = 4096
MAX_RECORD_PAYLOAD_BYTES = 262_144
MAX_STORE_PAYLOAD_BYTES = 16_777_216
MAX_APPEND_BATCH = 256

REGISTRY_STATUSES = (
    "REGISTRY_INITIALIZED",
    "REGISTRY_ALREADY_INITIALIZED",
    "REGISTRY_APPEND_COMMITTED",
    "REGISTRY_APPEND_IDEMPOTENT",
    "REGISTRY_LOADED_VERIFIED",
    "REGISTRY_REJECTED",
)

_REGISTRY_ACCOUNTING_KEY = ("REGISTRY_WIDE", "ALL_FAMILIES")


def _family_accounting_key(_family: ExperimentFamily) -> tuple[str, str]:
    """Use one conservative ledger so caller-defined names cannot reset trials."""
    return _REGISTRY_ACCOUNTING_KEY

RECORD_KIND_TYPES = (
    ("DATASET_BINDING", DatasetBinding, "dataset_binding_id"),
    ("FEATURE_DEFINITION", FeatureDefinition, "feature_definition_id"),
    ("LABEL_DEFINITION", LabelDefinition, "label_definition_id"),
    ("RESEARCH_DATASET_MANIFEST", ResearchDatasetManifest, "research_dataset_manifest_id"),
    ("TEMPORAL_SPLIT_MANIFEST", TemporalSplitManifest, "split_assignment_id"),
    ("ALPHA_HYPOTHESIS", AlphaHypothesis, "hypothesis_id"),
    ("METRIC_DEFINITION", MetricDefinition, "metric_definition_id"),
    ("BASELINE_DEFINITION", BaselineDefinition, "baseline_definition_id"),
    ("EXPERIMENT_FAMILY", ExperimentFamily, "experiment_family_id"),
    ("PREREGISTERED_EXPERIMENT", PreregisteredExperiment, "experiment_id"),
    ("LIFECYCLE_RECEIPT", LifecycleReceipt, "lifecycle_receipt_id"),
    ("RUN_EVIDENCE_RECEIPT", RunEvidenceReceipt, "run_evidence_receipt_id"),
)
_TYPE_INFO = {record_type: (kind, id_field) for kind, record_type, id_field in RECORD_KIND_TYPES}
_KIND_INFO = {kind: (record_type, id_field) for kind, record_type, id_field in RECORD_KIND_TYPES}
_KIND_RANK = {kind: index for index, (kind, _type, _field) in enumerate(RECORD_KIND_TYPES)}

# WP175D: the additive ExternalDatasetBinding subtype persists under the EXISTING
# DATASET_BINDING record kind (no new record kind, no schema/version/application-id
# or CHECK-vocabulary change). Serialization maps it to DATASET_BINDING; decoding
# disambiguates the two binding subtypes by exact schema_id only.
_TYPE_INFO[ExternalDatasetBinding] = ("DATASET_BINDING", "dataset_binding_id")
_DATASET_BINDING_SUBTYPES = {
    "polymarket-experiment-dataset-binding": DatasetBinding,
    EXTERNAL_DATASET_BINDING_SCHEMA_ID: ExternalDatasetBinding,
}

_CREATE_META = """CREATE TABLE registry_meta (
    singleton INTEGER PRIMARY KEY NOT NULL CHECK (singleton = 1),
    format_id TEXT NOT NULL CHECK (format_id = 'wp170-experiment-registry'),
    schema_version INTEGER NOT NULL CHECK (schema_version = 1)
)"""
_KIND_CHECK = ", ".join(f"'{kind}'" for kind in _KIND_INFO)
_CREATE_RECORDS = f"""CREATE TABLE experiment_records (
    sequence_number INTEGER PRIMARY KEY NOT NULL CHECK (sequence_number >= 0),
    record_kind TEXT NOT NULL CHECK (record_kind IN ({_KIND_CHECK})),
    record_id TEXT NOT NULL UNIQUE,
    payload_json TEXT NOT NULL,
    payload_sha256 TEXT NOT NULL,
    previous_entry_hash TEXT,
    entry_hash TEXT NOT NULL UNIQUE
)"""
_CREATE_NO_UPDATE = """CREATE TRIGGER experiment_records_no_update
BEFORE UPDATE ON experiment_records
BEGIN
    SELECT RAISE(ABORT, 'append-only');
END"""
_CREATE_NO_DELETE = """CREATE TRIGGER experiment_records_no_delete
BEFORE DELETE ON experiment_records
BEGIN
    SELECT RAISE(ABORT, 'append-only');
END"""


@dataclass(frozen=True)
class ExperimentRegistryEntry:
    sequence_number: int
    record_kind: str
    record_id: str
    payload_sha256: str
    previous_entry_hash: str | None
    entry_hash: str
    record: object


@dataclass(frozen=True)
class ExperimentRegistrySnapshot:
    schema_id: str
    schema_version: str
    entries: tuple[ExperimentRegistryEntry, ...]
    total_rows: int
    total_payload_bytes: int
    head_entry_hash: str | None
    advisory_only: bool
    no_execution_authority: bool


@dataclass(frozen=True)
class ExperimentRegistryResult:
    is_valid: bool
    status: str
    error_codes: tuple[str, ...]
    snapshot: ExperimentRegistrySnapshot | None
    inserted_record_ids: tuple[str, ...]
    idempotent_record_ids: tuple[str, ...]
    advisory_only: bool
    no_execution_authority: bool


class _StoreFailure(Exception):
    def __init__(self, code: str):
        self.code = code


def _reject(code: str) -> ExperimentRegistryResult:
    return ExperimentRegistryResult(False, "REGISTRY_REJECTED", (code,), None, (), (), True, True)


def _success(
    status: str, snapshot: ExperimentRegistrySnapshot,
    inserted: tuple[str, ...] = (), idempotent: tuple[str, ...] = (),
) -> ExperimentRegistryResult:
    return ExperimentRegistryResult(True, status, (), snapshot, inserted, idempotent, True, True)


def _path(path: object, *, must_exist: bool) -> Path:
    try:
        if isinstance(path, (bool, bytes)) or not isinstance(path, (str, os.PathLike)):
            raise _StoreFailure("FIELD_TYPE_INVALID")
        raw = os.fspath(path)
        if not isinstance(raw, str) or not raw.strip() or "\x00" in raw:
            raise _StoreFailure("FIELD_VALUE_INVALID")
        candidate = Path(raw).absolute()
        if candidate.suffix != ".sqlite3" or candidate.parent.is_symlink() or candidate.is_symlink():
            raise _StoreFailure("FIELD_VALUE_INVALID")
        if not candidate.parent.exists() or not candidate.parent.is_dir():
            raise _StoreFailure("FIELD_VALUE_INVALID")
        if candidate.exists():
            stat = candidate.lstat()
            if not candidate.is_file() or stat.st_nlink != 1:
                raise _StoreFailure("FIELD_VALUE_INVALID")
        elif must_exist:
            raise _StoreFailure("REGISTRY_SCHEMA_CONFLICT")
        return candidate
    except _StoreFailure:
        raise
    except Exception:
        raise _StoreFailure("FIELD_VALUE_INVALID") from None


def _uri(path: Path, mode: str) -> str:
    return f"{path.as_uri()}?mode={mode}"


def _connect(path: Path, mode: str) -> sqlite3.Connection:
    try:
        return sqlite3.connect(_uri(path, mode), uri=True, isolation_level=None, timeout=0.0)
    except sqlite3.Error:
        raise _StoreFailure("REGISTRY_SCHEMA_CONFLICT") from None


def _configure(connection: sqlite3.Connection, *, writable: bool) -> None:
    try:
        journal = connection.execute("PRAGMA journal_mode").fetchone()
        if journal != ("delete",):
            raise _StoreFailure("REGISTRY_SCHEMA_CONFLICT")
        if writable:
            connection.execute("PRAGMA synchronous=FULL")
        if connection.execute("PRAGMA synchronous").fetchone() != (2,):
            raise _StoreFailure("REGISTRY_SCHEMA_CONFLICT")
        connection.execute("PRAGMA foreign_keys=ON")
        if connection.execute("PRAGMA foreign_keys").fetchone() != (1,):
            raise _StoreFailure("REGISTRY_SCHEMA_CONFLICT")
    except _StoreFailure:
        raise
    except sqlite3.Error:
        raise _StoreFailure("REGISTRY_SCHEMA_CONFLICT") from None


def _norm_sql(value: str) -> str:
    return " ".join(value.split())


def _verify_schema(connection: sqlite3.Connection) -> None:
    try:
        if connection.execute("PRAGMA application_id").fetchone() != (REGISTRY_APPLICATION_ID,):
            raise _StoreFailure("REGISTRY_SCHEMA_CONFLICT")
        if connection.execute("PRAGMA user_version").fetchone() != (REGISTRY_SCHEMA_VERSION,):
            raise _StoreFailure("REGISTRY_SCHEMA_CONFLICT")
        objects = connection.execute(
            "SELECT type,name,sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' ORDER BY type,name"
        ).fetchall()
        expected = [
            ("table", "experiment_records", _CREATE_RECORDS),
            ("table", "registry_meta", _CREATE_META),
            ("trigger", "experiment_records_no_delete", _CREATE_NO_DELETE),
            ("trigger", "experiment_records_no_update", _CREATE_NO_UPDATE),
        ]
        if [(t, n, _norm_sql(s)) for t, n, s in objects] != [(t, n, _norm_sql(s)) for t, n, s in expected]:
            raise _StoreFailure("REGISTRY_SCHEMA_CONFLICT")
        if connection.execute("SELECT singleton,format_id,schema_version FROM registry_meta").fetchall() != [(1, REGISTRY_FORMAT_ID, REGISTRY_SCHEMA_VERSION)]:
            raise _StoreFailure("REGISTRY_SCHEMA_CONFLICT")
        indexes = connection.execute("PRAGMA index_list(experiment_records)").fetchall()
        signatures = []
        for row in indexes:
            columns = tuple(
                item[2]
                for item in connection.execute(
                    "SELECT * FROM pragma_index_info(?)", (row[1],)
                ).fetchall()
            )
            signatures.append((row[3], columns))
        if sorted(signatures, key=lambda item: item[1]) != sorted([("u", ("record_id",)), ("u", ("entry_hash",))], key=lambda item: item[1]):
            raise _StoreFailure("REGISTRY_SCHEMA_CONFLICT")
        if connection.execute("SELECT name FROM sqlite_master WHERE type='index' AND sql IS NOT NULL").fetchall():
            raise _StoreFailure("REGISTRY_SCHEMA_CONFLICT")
        if connection.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
            raise _StoreFailure("REGISTRY_INTEGRITY_TAMPER")
        if connection.execute("PRAGMA foreign_key_check").fetchall():
            raise _StoreFailure("REGISTRY_INTEGRITY_TAMPER")
    except _StoreFailure:
        raise
    except sqlite3.Error:
        raise _StoreFailure("REGISTRY_SCHEMA_CONFLICT") from None


def _strict_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate")
        result[key] = value
    return result


def _dataset_binding_subtype(value: object) -> type:
    """Exact schema_id subtype dispatch for the DATASET_BINDING record kind.

    No ambiguous subtype inference: any unknown schema_id fails closed as registry
    integrity tamper.
    """
    if not isinstance(value, Mapping):
        raise _StoreFailure("REGISTRY_INTEGRITY_TAMPER")
    subtype = _DATASET_BINDING_SUBTYPES.get(value.get("schema_id"))
    if subtype is None:
        raise _StoreFailure("REGISTRY_INTEGRITY_TAMPER")
    return subtype


def _decode(kind: str, payload: str) -> object:
    try:
        value = json.loads(payload, object_pairs_hook=_strict_pairs, parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
        record_type, _id_field = _KIND_INFO[kind]
        if kind == "DATASET_BINDING":
            record_type = _dataset_binding_subtype(value)
        return record_from_mapping(record_type, value)
    except (KeyError, TypeError, ValueError, UnicodeError, _Failure):
        raise _StoreFailure("REGISTRY_INTEGRITY_TAMPER") from None


def _serialize(record: object) -> tuple[str, str, str, str]:
    try:
        _validate_public_record(record)
        kind, id_field = _TYPE_INFO[type(record)]
        record_id = getattr(record, id_field)
        raw = _canonical_bytes(record_to_mapping(record))
        if len(raw) > MAX_RECORD_PAYLOAD_BYTES:
            raise _StoreFailure("LIMIT_EXCEEDED")
        return kind, record_id, raw.decode("utf-8"), hashlib.sha256(raw).hexdigest()
    except _StoreFailure:
        raise
    except _Failure as failure:
        raise _StoreFailure(failure.code) from None
    except Exception:
        raise _StoreFailure("INTERNAL_VALIDATION_FAILED") from None


def _entry_hash(sequence: int, kind: str, record_id: str, payload_sha: str, previous: str | None) -> str:
    return _digest("registry_entry", "registryentry:sha256:", {
        "sequence_number": sequence, "record_kind": kind, "record_id": record_id,
        "payload_sha256": payload_sha, "previous_entry_hash": previous,
    })


def _load(connection: sqlite3.Connection) -> ExperimentRegistrySnapshot:
    _verify_schema(connection)
    rows = connection.execute(
        "SELECT sequence_number,record_kind,record_id,payload_json,payload_sha256,previous_entry_hash,entry_hash FROM experiment_records ORDER BY sequence_number"
    ).fetchall()
    if len(rows) > MAX_REGISTRY_RECORDS:
        raise _StoreFailure("LIMIT_EXCEEDED")
    entries: list[ExperimentRegistryEntry] = []
    total_bytes = 0
    previous = None
    for expected_sequence, row in enumerate(rows):
        sequence, kind, record_id, payload, payload_sha, prior_hash, entry_hash = row
        if sequence != expected_sequence or kind not in _KIND_INFO or prior_hash != previous:
            raise _StoreFailure("REGISTRY_INTEGRITY_TAMPER")
        if not all(isinstance(value, str) for value in (kind, record_id, payload, payload_sha, entry_hash)):
            raise _StoreFailure("REGISTRY_INTEGRITY_TAMPER")
        raw = payload.encode("utf-8")
        total_bytes += len(raw)
        if len(raw) > MAX_RECORD_PAYLOAD_BYTES or total_bytes > MAX_STORE_PAYLOAD_BYTES:
            raise _StoreFailure("LIMIT_EXCEEDED")
        if hashlib.sha256(raw).hexdigest() != payload_sha or _entry_hash(sequence, kind, record_id, payload_sha, prior_hash) != entry_hash:
            raise _StoreFailure("REGISTRY_INTEGRITY_TAMPER")
        record = _decode(kind, payload)
        if getattr(record, _KIND_INFO[kind][1]) != record_id:
            raise _StoreFailure("REGISTRY_INTEGRITY_TAMPER")
        entries.append(ExperimentRegistryEntry(sequence, kind, record_id, payload_sha, prior_hash, entry_hash, record))
        previous = entry_hash
    snapshot = ExperimentRegistrySnapshot(
        "polymarket-experiment-registry-snapshot", "1.0.0", tuple(entries),
        len(entries), total_bytes, previous, True, True,
    )
    _verify_cross_record_invariants(snapshot)
    return snapshot


def _verify_snapshot_object(snapshot: object) -> ExperimentRegistrySnapshot:
    if not isinstance(snapshot, ExperimentRegistrySnapshot):
        raise _StoreFailure("FIELD_TYPE_INVALID")
    if (
        snapshot.schema_id != "polymarket-experiment-registry-snapshot"
        or snapshot.schema_version != "1.0.0"
        or snapshot.advisory_only is not True
        or snapshot.no_execution_authority is not True
        or not isinstance(snapshot.entries, tuple)
        or snapshot.total_rows != len(snapshot.entries)
        or snapshot.total_rows > MAX_REGISTRY_RECORDS
    ):
        raise _StoreFailure("REGISTRY_INTEGRITY_TAMPER")
    previous = None
    total_bytes = 0
    for sequence, entry in enumerate(snapshot.entries):
        if not isinstance(entry, ExperimentRegistryEntry) or entry.sequence_number != sequence:
            raise _StoreFailure("REGISTRY_INTEGRITY_TAMPER")
        kind, record_id, payload, payload_sha = _serialize(entry.record)
        total_bytes += len(payload.encode("utf-8"))
        if (
            entry.record_kind != kind
            or entry.record_id != record_id
            or entry.payload_sha256 != payload_sha
            or entry.previous_entry_hash != previous
            or entry.entry_hash != _entry_hash(sequence, kind, record_id, payload_sha, previous)
        ):
            raise _StoreFailure("REGISTRY_INTEGRITY_TAMPER")
        previous = entry.entry_hash
    if (
        total_bytes != snapshot.total_payload_bytes
        or total_bytes > MAX_STORE_PAYLOAD_BYTES
        or snapshot.head_entry_hash != previous
    ):
        raise _StoreFailure("REGISTRY_INTEGRITY_TAMPER")
    _verify_cross_record_invariants(snapshot)
    return snapshot


def _role_source_membership(
    manifest: ResearchDatasetManifest,
    split: TemporalSplitManifest,
    role: str,
) -> frozenset[str]:
    """Return feature/split/label-independent source records exposed by a role."""
    role_sample_ids = {
        "FORMATION": split.formation_sample_ids,
        "SELECTION": split.selection_sample_ids,
        "OUT_OF_SAMPLE": split.oos_sample_ids,
    }[role]
    samples_by_id = {sample.sample_id: sample for sample in manifest.samples}
    if any(sample_id not in samples_by_id for sample_id in role_sample_ids):
        raise _StoreFailure("TRIAL_FAMILY_CONFLICT")
    source_ids = frozenset(
        source_id
        for sample_id in role_sample_ids
        for source_id in samples_by_id[sample_id].source_record_version_ids
    )
    if not source_ids:
        raise _StoreFailure("TRIAL_FAMILY_CONFLICT")
    return source_ids


def _verify_cross_record_invariants(snapshot: ExperimentRegistrySnapshot) -> None:
    bindings: dict[str, DatasetBinding] = {}
    external_bindings: dict[str, ExternalDatasetBinding] = {}
    features: dict[str, FeatureDefinition] = {}
    labels: dict[str, LabelDefinition] = {}
    manifests: dict[str, ResearchDatasetManifest] = {}
    splits: dict[str, TemporalSplitManifest] = {}
    hypotheses: dict[str, AlphaHypothesis] = {}
    metrics: dict[str, MetricDefinition] = {}
    baselines: dict[str, BaselineDefinition] = {}
    families: dict[str, ExperimentFamily] = {}
    lineage_families: dict[tuple[str, str], list[str]] = {}
    family_lineage: dict[str, tuple[str, str]] = {}
    experiments: dict[str, PreregisteredExperiment] = {}
    lineage_trials: dict[tuple[str, str], set[int]] = {}
    lifecycle: dict[str, list[LifecycleReceipt]] = {}
    evidence: dict[str, list[RunEvidenceReceipt]] = {}
    oos_releases: list[tuple[str, frozenset[str]]] = []
    controlled_evidence: list[tuple[str, int, frozenset[str]]] = []

    for entry in snapshot.entries:
        record = entry.record
        try:
            _validate_public_record(record)
            if isinstance(record, DatasetBinding):
                bindings[record.dataset_binding_id] = record
            elif isinstance(record, ExternalDatasetBinding):
                external_bindings[record.dataset_binding_id] = record
            elif isinstance(record, FeatureDefinition):
                features[record.feature_definition_id] = record
            elif isinstance(record, LabelDefinition):
                labels[record.label_definition_id] = record
            elif isinstance(record, ResearchDatasetManifest):
                canonical_binding = bindings.get(record.dataset_binding_id)
                external_binding = external_bindings.get(record.dataset_binding_id)
                if (
                    (canonical_binding is None and external_binding is None)
                    or record.label_definition_id not in labels
                    or any(item not in features for item in record.feature_definition_ids)
                ):
                    raise _StoreFailure("TRIAL_FAMILY_CONFLICT")
                if canonical_binding is not None:
                    from .experiment_os import _decode_dataset_reference_json
                    reference = _decode_dataset_reference_json(canonical_binding.dataset_snapshot_reference_json)
                    allowed_sources = set(reference.ordinary_record_version_ids)
                    if any(not set(sample.source_record_version_ids).issubset(allowed_sources) for sample in record.samples):
                        raise _StoreFailure("TRIAL_FAMILY_CONFLICT")
                else:
                    # External binding: the registry does not persist the ephemeral
                    # lineage, so structural provenance is enforced here — every cited
                    # source id must be an external member id (never a canonical
                    # record-version id). Exact membership against the bound lineage is
                    # enforced at bridge-construction time where the lineage exists.
                    if any(
                        not source_id.startswith(EXTERNAL_MEMBER_ID_PREFIX)
                        for sample in record.samples
                        for source_id in sample.source_record_version_ids
                    ):
                        raise _StoreFailure("TRIAL_FAMILY_CONFLICT")
                manifests[record.research_dataset_manifest_id] = record
            elif isinstance(record, TemporalSplitManifest):
                manifest = manifests.get(record.dataset_manifest_id)
                if manifest is None:
                    raise _StoreFailure("TRIAL_FAMILY_CONFLICT")
                rebuilt = build_temporal_split_manifest(manifest, {
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
                })
                if not rebuilt.is_valid or rebuilt.record != record:
                    raise _StoreFailure("TRIAL_FAMILY_CONFLICT")
                splits[record.split_assignment_id] = record
            elif isinstance(record, AlphaHypothesis):
                hypotheses[record.hypothesis_id] = record
            elif isinstance(record, MetricDefinition):
                metrics[record.metric_definition_id] = record
            elif isinstance(record, BaselineDefinition):
                baselines[record.baseline_definition_id] = record
            elif isinstance(record, ExperimentFamily):
                # Every family in this registry shares one conservative accounting lineage.
                # No caller-controlled descriptive field can create a fresh trial ledger.
                lineage_key = _family_accounting_key(record)
                prior_families = lineage_families.setdefault(lineage_key, [])
                if not prior_families:
                    if record.predecessor_family_id is not None:
                        raise _StoreFailure("TRIAL_FAMILY_CONFLICT")
                else:
                    predecessor = families.get(record.predecessor_family_id or "")
                    if (
                        predecessor is None
                        or record.predecessor_family_id != prior_families[-1]
                        or family_lineage[predecessor.experiment_family_id] != lineage_key
                        or predecessor.correction_policy != record.correction_policy
                    ):
                        raise _StoreFailure("TRIAL_FAMILY_CONFLICT")
                families[record.experiment_family_id] = record
                family_lineage[record.experiment_family_id] = lineage_key
                prior_families.append(record.experiment_family_id)
            elif isinstance(record, PreregisteredExperiment):
                family = families.get(record.experiment_family_id)
                hypothesis = hypotheses.get(record.hypothesis_id)
                manifest = manifests.get(record.research_dataset_manifest_id)
                split = splits.get(record.split_assignment_id)
                primary_metric = metrics.get(record.primary_metric_id)
                baseline = baselines.get(record.baseline_id)
                if (
                    family is None or hypothesis is None
                    or (record.dataset_binding_id not in bindings and record.dataset_binding_id not in external_bindings)
                    or manifest is None or split is None or record.label_definition_id not in labels
                    or primary_metric is None or any(item not in metrics for item in record.secondary_metric_ids)
                    or baseline is None or any(item not in features for item in record.feature_definition_ids)
                    or record.correction_policy != family.correction_policy
                    or hypothesis.cohort != family.cohort
                    or hypothesis.target != family.target
                    or manifest.dataset_binding_id != record.dataset_binding_id
                    or manifest.feature_definition_ids != record.feature_definition_ids
                    or manifest.feature_set_id != record.feature_set_id
                    or manifest.label_definition_id != record.label_definition_id
                    or split.dataset_manifest_id != record.research_dataset_manifest_id
                    or split.dataset_binding_id != record.dataset_binding_id
                    or split.feature_definition_ids != record.feature_definition_ids
                    or split.feature_set_id != record.feature_set_id
                    or split.label_definition_id != record.label_definition_id
                    or split.split_plan_id != record.split_plan_id
                    or baseline.acceptance_rule
                    != {
                        "HIGHER_IS_BETTER": "CANDIDATE_GTE_BASELINE",
                        "LOWER_IS_BETTER": "CANDIDATE_LTE_BASELINE",
                    }.get(primary_metric.direction)
                ):
                    raise _StoreFailure("TRIAL_FAMILY_CONFLICT")
                try:
                    _threshold_mapping(
                        json.loads(record.acceptance_thresholds_json),
                        primary_metric.direction,
                    )
                except (_Failure, TypeError, ValueError, UnicodeError):
                    raise _StoreFailure("TRIAL_FAMILY_CONFLICT") from None
                lineage_key = family_lineage[family.experiment_family_id]
                trials = lineage_trials.setdefault(lineage_key, set())
                if record.trial_number in trials:
                    raise _StoreFailure("TRIAL_FAMILY_CONFLICT")
                trials.add(record.trial_number)
                if trials != set(range(1, max(trials) + 1)) or (family.correction_policy == "SINGLETON" and trials != {1}):
                    raise _StoreFailure("TRIAL_FAMILY_CONFLICT")
                experiments[record.experiment_id] = record
            elif isinstance(record, LifecycleReceipt):
                experiment = experiments.get(record.experiment_id)
                if experiment is None:
                    raise _StoreFailure("TRIAL_FAMILY_CONFLICT")
                prior_evidence = evidence.get(record.experiment_id, [])
                if prior_evidence and _dt(record.occurred_at) < max(_dt(item.created_at) for item in prior_evidence):
                    raise _StoreFailure("OOS_SEALED_EXPOSURE_VIOLATION")
                chain = lifecycle.setdefault(record.experiment_id, [])
                chain.append(record)
                from .experiment_os import validate_lifecycle
                if not validate_lifecycle(experiment, tuple(chain)).is_valid:
                    raise _StoreFailure("OOS_SEALED_EXPOSURE_VIOLATION")
                split = splits[experiment.split_assignment_id]
                if record.action == "RELEASE_OOS":
                    manifest = manifests[split.dataset_manifest_id]
                    oos_releases.append((
                        experiment.experiment_id,
                        _role_source_membership(manifest, split, "OUT_OF_SAMPLE"),
                    ))
                if record.action == "CLOSE_EXPERIMENT":
                    oos = [item for item in prior_evidence if item.evaluated_role == "OUT_OF_SAMPLE"]
                    if not oos:
                        raise _StoreFailure("OOS_SEALED_EXPOSURE_VIOLATION")
                    first = oos[0]
                    terminal = "EVIDENCE_INCONCLUSIVE" if first.result_status in {"EVIDENCE_INVALIDATED_AFTER_RUN", "OOS_REUSED_DIAGNOSTIC"} else first.result_status
                    if terminal != record.terminal_result_status:
                        raise _StoreFailure("OOS_SEALED_EXPOSURE_VIOLATION")
            elif isinstance(record, RunEvidenceReceipt):
                experiment = experiments.get(record.experiment_id)
                split = splits.get(record.split_assignment_id)
                if experiment is None or split is None:
                    raise _StoreFailure("TRIAL_FAMILY_CONFLICT")
                baseline = baselines.get(experiment.baseline_id)
                if baseline is None:
                    raise _StoreFailure("TRIAL_FAMILY_CONFLICT")
                _validate_evidence_against_experiment(record, experiment, baseline)
                if record.membership_hash != membership_hash(split, record.evaluated_role):
                    raise _StoreFailure("TRIAL_FAMILY_CONFLICT")
                chain = lifecycle.get(record.experiment_id, [])
                needed = {"FORMATION": "FORMATION_ACTIVE", "SELECTION": "SELECTION_ACTIVE", "OUT_OF_SAMPLE": "OOS_RELEASED"}[record.evaluated_role]
                if not chain or chain[-1].to_state != needed or _dt(record.created_at) < _dt(chain[-1].occurred_at):
                    raise _StoreFailure("OOS_SEALED_EXPOSURE_VIOLATION")
                manifest = manifests.get(experiment.research_dataset_manifest_id)
                if manifest is None:
                    raise _StoreFailure("TRIAL_FAMILY_CONFLICT")
                if _dt(record.created_at) < _role_evidence_ready_time(
                    experiment, manifest, split, record.evaluated_role,
                ):
                    raise _StoreFailure("LABEL_TIMING_INVALID")
                current_evidence = evidence.setdefault(record.experiment_id, [])
                if current_evidence and _dt(record.created_at) < max(_dt(item.created_at) for item in current_evidence):
                    raise _StoreFailure("OOS_SEALED_EXPOSURE_VIOLATION")
                if record.evaluated_role == "OUT_OF_SAMPLE":
                    manifest = manifests[split.dataset_manifest_id]
                    source_membership = _role_source_membership(
                        manifest, split, "OUT_OF_SAMPLE",
                    )
                    prior_release_count = sum(
                        experiment_id != record.experiment_id
                        and bool(source_membership & prior_membership)
                        for experiment_id, prior_membership in oos_releases
                    )
                    prior_evidence_ordinal = max(
                        (
                            ordinal for prior_role, ordinal, prior_membership
                            in controlled_evidence
                            if prior_role == "OUT_OF_SAMPLE"
                            and source_membership & prior_membership
                        ),
                        default=0,
                    )
                    prior_tuning_exposure = int(any(
                        prior_role != "OUT_OF_SAMPLE"
                        and bool(source_membership & prior_membership)
                        for prior_role, _ordinal, prior_membership in controlled_evidence
                    ))
                    expected_ordinal = 1 + max(
                        prior_release_count, prior_evidence_ordinal,
                        prior_tuning_exposure,
                    )
                    if record.oos_exposure_ordinal != expected_ordinal:
                        raise _StoreFailure("OOS_SEALED_EXPOSURE_VIOLATION")
                    controlled_evidence.append(
                        (record.evaluated_role, expected_ordinal, source_membership),
                    )
                elif record.oos_exposure_ordinal != 0:
                    raise _StoreFailure("OOS_SEALED_EXPOSURE_VIOLATION")
                else:
                    manifest = manifests[split.dataset_manifest_id]
                    controlled_evidence.append((
                        record.evaluated_role,
                        0,
                        _role_source_membership(
                            manifest, split, record.evaluated_role,
                        ),
                    ))
                current_evidence.append(record)
        except _StoreFailure:
            raise
        except _Failure as failure:
            raise _StoreFailure(failure.code) from None
        except Exception:
            raise _StoreFailure("REGISTRY_INTEGRITY_TAMPER") from None


def _remove_created(path: Path) -> None:
    try:
        if path.exists() and path.is_file() and not path.is_symlink() and path.lstat().st_nlink == 1:
            path.unlink()
    except OSError:
        pass


def initialize_experiment_registry(path: object) -> ExperimentRegistryResult:
    created = False
    try:
        target = _path(path, must_exist=False)
        existed = target.exists()
        if not existed:
            try:
                descriptor = os.open(target, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            except FileExistsError:
                raise _StoreFailure("REGISTRY_SCHEMA_CONFLICT") from None
            except OSError:
                raise _StoreFailure("REGISTRY_SCHEMA_CONFLICT") from None
            else:
                os.close(descriptor)
                created = True
        connection = _connect(target, "rwc")
        try:
            _configure(connection, writable=True)
            if existed:
                snapshot = _load(connection)
                return _success("REGISTRY_ALREADY_INITIALIZED", snapshot)
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(_CREATE_META)
            # The DDL is built solely from the closed, module-owned RECORD_KIND_TYPES
            # vocabulary; no caller or persisted value is interpolated.
            connection.execute(_CREATE_RECORDS)  # nosemgrep: python.lang.security.audit.formatted-sql-query.formatted-sql-query, python.sqlalchemy.security.sqlalchemy-execute-raw-query.sqlalchemy-execute-raw-query
            connection.execute(_CREATE_NO_UPDATE)
            connection.execute(_CREATE_NO_DELETE)
            connection.execute("INSERT INTO registry_meta VALUES (1,?,?)", (REGISTRY_FORMAT_ID, REGISTRY_SCHEMA_VERSION))
            connection.execute("PRAGMA application_id=1464877424")
            connection.execute("PRAGMA user_version=1")
            connection.execute("COMMIT")
            snapshot = _load(connection)
            return _success("REGISTRY_INITIALIZED", snapshot)
        finally:
            connection.close()
    except _StoreFailure as failure:
        if created:
            _remove_created(target)
        return _reject(failure.code)
    except Exception:
        if created:
            _remove_created(target)
        return _reject("INTERNAL_VALIDATION_FAILED")


def _new_item_sort_key(
    item: tuple[str, str, str, str], all_families: Mapping[str, ExperimentFamily],
    new_family_ids: frozenset[str],
) -> tuple[object, ...]:
    kind, record_id, payload, payload_sha = item
    record = _decode(kind, payload)
    if isinstance(record, ExperimentFamily):
        seen: set[str] = set()
        depth = 0
        predecessor = record.predecessor_family_id
        while predecessor in new_family_ids:
            if predecessor in seen:
                raise _StoreFailure("TRIAL_FAMILY_CONFLICT")
            seen.add(predecessor)
            depth += 1
            predecessor = all_families[predecessor].predecessor_family_id
        return (_KIND_RANK[kind], depth, record_id, payload_sha)
    if isinstance(record, PreregisteredExperiment):
        family = all_families.get(record.experiment_family_id)
        if family is None:
            raise _StoreFailure("TRIAL_FAMILY_CONFLICT")
        return (
            _KIND_RANK[kind], *_family_accounting_key(family), record.trial_number,
            family.experiment_family_id, record_id, payload_sha,
        )
    if isinstance(record, LifecycleReceipt):
        return (_KIND_RANK[kind], record.experiment_id, record.sequence_number, record_id, payload_sha)
    return (_KIND_RANK[kind], record_id, payload_sha)


def _append_experiment_records(
    path: object, records: object, *, allow_evidence: bool,
) -> ExperimentRegistryResult:
    try:
        target = _path(path, must_exist=True)
        if not isinstance(records, (list, tuple)):
            raise _StoreFailure("FIELD_TYPE_INVALID")
        if not records:
            raise _StoreFailure("FIELD_VALUE_INVALID")
        if len(records) > MAX_APPEND_BATCH:
            raise _StoreFailure("LIMIT_EXCEEDED")
        if not allow_evidence and any(isinstance(record, RunEvidenceReceipt) for record in records):
            raise _StoreFailure("OOS_SEALED_EXPOSURE_VIOLATION")
        serialized = [_serialize(record) for record in records]
        by_id: dict[str, tuple[str, str, str, str]] = {}
        duplicate_ids: set[str] = set()
        for item in serialized:
            kind, record_id, payload, payload_sha = item
            prior = by_id.get(record_id)
            if prior is not None and prior != item:
                raise _StoreFailure("TRIAL_FAMILY_CONFLICT")
            if prior == item:
                duplicate_ids.add(record_id)
            by_id[record_id] = item
        connection = _connect(target, "rwc")
        try:
            _configure(connection, writable=True)
            connection.execute("BEGIN IMMEDIATE")
            current = _load(connection)
            existing = {entry.record_id: entry for entry in current.entries}
            new_items = []
            idempotent = set(duplicate_ids)
            for record_id, item in by_id.items():
                kind, _record_id, payload, payload_sha = item
                found = existing.get(record_id)
                if found is not None:
                    if found.record_kind != kind or found.payload_sha256 != payload_sha:
                        raise _StoreFailure("TRIAL_FAMILY_CONFLICT")
                    idempotent.add(record_id)
                else:
                    new_items.append(item)
            all_families = {
                entry.record.experiment_family_id: entry.record
                for entry in current.entries if isinstance(entry.record, ExperimentFamily)
            }
            for kind, _record_id, payload, _payload_sha in new_items:
                if kind == "EXPERIMENT_FAMILY":
                    family_record = _decode(kind, payload)
                    all_families[family_record.experiment_family_id] = family_record
            new_family_ids = frozenset(
                record_id for kind, record_id, _payload, _sha in new_items
                if kind == "EXPERIMENT_FAMILY"
            )
            new_items.sort(key=lambda item: _new_item_sort_key(item, all_families, new_family_ids))
            projected_rows = current.total_rows + len(new_items)
            projected_bytes = current.total_payload_bytes + sum(len(item[2].encode("utf-8")) for item in new_items)
            if projected_rows > MAX_REGISTRY_RECORDS or projected_bytes > MAX_STORE_PAYLOAD_BYTES:
                raise _StoreFailure("LIMIT_EXCEEDED")
            sequence = current.total_rows
            previous = current.head_entry_hash
            inserted = []
            for kind, record_id, payload, payload_sha in new_items:
                entry_hash = _entry_hash(sequence, kind, record_id, payload_sha, previous)
                connection.execute(
                    "INSERT INTO experiment_records(sequence_number,record_kind,record_id,payload_json,payload_sha256,previous_entry_hash,entry_hash) VALUES (?,?,?,?,?,?,?)",
                    (sequence, kind, record_id, payload, payload_sha, previous, entry_hash),
                )
                inserted.append(record_id)
                previous = entry_hash
                sequence += 1
            projected = _load(connection)
            connection.execute("COMMIT")
            status = "REGISTRY_APPEND_COMMITTED" if inserted else "REGISTRY_APPEND_IDEMPOTENT"
            return _success(status, projected, tuple(sorted(inserted)), tuple(sorted(idempotent)))
        except Exception:
            try:
                connection.execute("ROLLBACK")
            except sqlite3.Error:
                pass
            raise
        finally:
            connection.close()
    except _StoreFailure as failure:
        return _reject(failure.code)
    except sqlite3.Error:
        return _reject("REGISTRY_SCHEMA_CONFLICT")
    except Exception:
        return _reject("INTERNAL_VALIDATION_FAILED")


def append_experiment_records(path: object, records: object) -> ExperimentRegistryResult:
    return _append_experiment_records(path, records, allow_evidence=False)


def _evidence_request_key(record: RunEvidenceReceipt) -> dict[str, object]:
    """Canonical caller-controlled evidence content, excluding derived exposure state."""
    value = record_to_mapping(record)
    for field_name in (
        "run_evidence_receipt_id", "result_status", "oos_exposure_ordinal",
    ):
        value.pop(field_name)
    return value


def _find_idempotent_evidence_retry(
    experiment: PreregisteredExperiment,
    manifest: ResearchDatasetManifest,
    split: TemporalSplitManifest,
    baseline: BaselineDefinition,
    chain: tuple[LifecycleReceipt, ...],
    experiment_evidence: tuple[RunEvidenceReceipt, ...],
    input_mapping: object,
) -> RunEvidenceReceipt | None:
    state_lengths = {"FORMATION": 2, "SELECTION": 3, "OUT_OF_SAMPLE": 5}
    prior: list[RunEvidenceReceipt] = []
    for existing in experiment_evidence:
        historical_chain = chain[:state_lengths[existing.evaluated_role]]
        rebuilt = _build_run_evidence_receipt(
            experiment, manifest, split, baseline, historical_chain, tuple(prior),
            input_mapping,
            allow_oos=True, prior_oos_release_count=0,
        )
        if (
            rebuilt.is_valid
            and isinstance(rebuilt.record, RunEvidenceReceipt)
            and _evidence_request_key(rebuilt.record) == _evidence_request_key(existing)
        ):
            return existing
        prior.append(existing)
    return None


def record_experiment_evidence(
    path: object, experiment_id: object, input_mapping: object,
) -> ExperimentRegistryResult:
    """Atomically derive and append evidence from complete authoritative history."""
    try:
        target = _path(path, must_exist=True)
        if not isinstance(experiment_id, str):
            raise _StoreFailure("FIELD_TYPE_INVALID")
        connection = _connect(target, "rwc")
        try:
            _configure(connection, writable=True)
            connection.execute("BEGIN IMMEDIATE")
            current = _load(connection)
            experiment = next(
                (entry.record for entry in current.entries if isinstance(entry.record, PreregisteredExperiment) and entry.record.experiment_id == experiment_id),
                None,
            )
            if experiment is None:
                raise _StoreFailure("TRIAL_FAMILY_CONFLICT")
            split = next(
                (entry.record for entry in current.entries if isinstance(entry.record, TemporalSplitManifest) and entry.record.split_assignment_id == experiment.split_assignment_id),
                None,
            )
            if split is None:
                raise _StoreFailure("TRIAL_FAMILY_CONFLICT")
            manifest = next(
                (
                    entry.record for entry in current.entries
                    if isinstance(entry.record, ResearchDatasetManifest)
                    and entry.record.research_dataset_manifest_id == experiment.research_dataset_manifest_id
                ),
                None,
            )
            baseline = next(
                (
                    entry.record for entry in current.entries
                    if isinstance(entry.record, BaselineDefinition)
                    and entry.record.baseline_definition_id == experiment.baseline_id
                ),
                None,
            )
            if manifest is None or baseline is None:
                raise _StoreFailure("TRIAL_FAMILY_CONFLICT")
            chain = tuple(
                entry.record for entry in current.entries
                if isinstance(entry.record, LifecycleReceipt) and entry.record.experiment_id == experiment_id
            )
            all_evidence = tuple(
                entry.record for entry in current.entries
                if isinstance(entry.record, RunEvidenceReceipt)
            )
            experiment_evidence = tuple(
                receipt for receipt in all_evidence
                if receipt.experiment_id == experiment.experiment_id
            )
            identical_retry = _find_idempotent_evidence_retry(
                experiment, manifest, split, baseline, chain, experiment_evidence,
                input_mapping,
            )
            if identical_retry is not None:
                connection.execute("COMMIT")
                return _success(
                    "REGISTRY_APPEND_IDEMPOTENT", current, (),
                    (identical_retry.run_evidence_receipt_id,),
                )
            current_oos_sources = _role_source_membership(
                manifest, split, "OUT_OF_SAMPLE",
            )
            prior_release_experiments: set[str] = set()
            experiment_by_id = {
                entry.record.experiment_id: entry.record
                for entry in current.entries if isinstance(entry.record, PreregisteredExperiment)
            }
            split_by_id = {
                entry.record.split_assignment_id: entry.record
                for entry in current.entries if isinstance(entry.record, TemporalSplitManifest)
            }
            manifest_by_id = {
                entry.record.research_dataset_manifest_id: entry.record
                for entry in current.entries if isinstance(entry.record, ResearchDatasetManifest)
            }
            for entry in current.entries:
                receipt = entry.record
                if not isinstance(receipt, LifecycleReceipt) or receipt.action != "RELEASE_OOS" or receipt.experiment_id == experiment_id:
                    continue
                prior_experiment = experiment_by_id.get(receipt.experiment_id)
                prior_split = split_by_id.get(prior_experiment.split_assignment_id) if prior_experiment else None
                prior_manifest = manifest_by_id.get(prior_split.dataset_manifest_id) if prior_split else None
                if (
                    prior_split is not None and prior_manifest is not None
                    and current_oos_sources
                    & _role_source_membership(prior_manifest, prior_split, "OUT_OF_SAMPLE")
                ):
                    prior_release_experiments.add(receipt.experiment_id)
            prior_evidence_ordinal = max(
                (
                    receipt.oos_exposure_ordinal
                    for receipt in all_evidence
                    if receipt.evaluated_role == "OUT_OF_SAMPLE"
                    and (prior_experiment := experiment_by_id.get(receipt.experiment_id)) is not None
                    and (prior_split := split_by_id.get(prior_experiment.split_assignment_id)) is not None
                    and (prior_manifest := manifest_by_id.get(prior_split.dataset_manifest_id)) is not None
                    and current_oos_sources
                    & _role_source_membership(prior_manifest, prior_split, "OUT_OF_SAMPLE")
                ),
                default=0,
            )
            prior_tuning_exposure = any(
                receipt.evaluated_role != "OUT_OF_SAMPLE"
                and (prior_experiment := experiment_by_id.get(receipt.experiment_id)) is not None
                and (prior_split := split_by_id.get(prior_experiment.split_assignment_id)) is not None
                and (prior_manifest := manifest_by_id.get(prior_split.dataset_manifest_id)) is not None
                and bool(
                    current_oos_sources
                    & _role_source_membership(
                        prior_manifest, prior_split, receipt.evaluated_role,
                    )
                )
                for receipt in all_evidence
            )
            built = _build_run_evidence_receipt(
                experiment, manifest, split, baseline, chain, all_evidence, input_mapping,
                allow_oos=True,
                prior_oos_release_count=max(
                    len(prior_release_experiments), prior_evidence_ordinal,
                    int(prior_tuning_exposure),
                ),
            )
            if not built.is_valid or not isinstance(built.record, RunEvidenceReceipt):
                raise _StoreFailure(built.error_codes[0] if built.error_codes else "INTERNAL_VALIDATION_FAILED")
            request_key = _evidence_request_key(built.record)
            identical = next(
                (
                    entry for entry in current.entries
                    if isinstance(entry.record, RunEvidenceReceipt)
                    and _evidence_request_key(entry.record) == request_key
                ),
                None,
            )
            if identical is not None:
                connection.execute("COMMIT")
                return _success(
                    "REGISTRY_APPEND_IDEMPOTENT", current, (), (identical.record_id,),
                )
            kind, record_id, payload, payload_sha = _serialize(built.record)
            existing = next((entry for entry in current.entries if entry.record_id == record_id), None)
            if existing is not None:
                if existing.record_kind != kind or existing.payload_sha256 != payload_sha:
                    raise _StoreFailure("TRIAL_FAMILY_CONFLICT")
                connection.execute("COMMIT")
                return _success("REGISTRY_APPEND_IDEMPOTENT", current, (), (record_id,))
            payload_size = len(payload.encode("utf-8"))
            if current.total_rows + 1 > MAX_REGISTRY_RECORDS or current.total_payload_bytes + payload_size > MAX_STORE_PAYLOAD_BYTES:
                raise _StoreFailure("LIMIT_EXCEEDED")
            sequence = current.total_rows
            entry_hash = _entry_hash(sequence, kind, record_id, payload_sha, current.head_entry_hash)
            connection.execute(
                "INSERT INTO experiment_records(sequence_number,record_kind,record_id,payload_json,payload_sha256,previous_entry_hash,entry_hash) VALUES (?,?,?,?,?,?,?)",
                (sequence, kind, record_id, payload, payload_sha, current.head_entry_hash, entry_hash),
            )
            projected = _load(connection)
            connection.execute("COMMIT")
            return _success("REGISTRY_APPEND_COMMITTED", projected, (record_id,), ())
        except Exception:
            try:
                connection.execute("ROLLBACK")
            except sqlite3.Error:
                pass
            raise
        finally:
            connection.close()
    except _StoreFailure as failure:
        return _reject(failure.code)
    except sqlite3.Error:
        return _reject("REGISTRY_SCHEMA_CONFLICT")
    except Exception:
        return _reject("INTERNAL_VALIDATION_FAILED")


def load_and_verify_experiment_registry(path: object) -> ExperimentRegistryResult:
    try:
        target = _path(path, must_exist=True)
        connection = _connect(target, "ro")
        try:
            _configure(connection, writable=False)
            snapshot = _load(connection)
        finally:
            connection.close()
        return _success("REGISTRY_LOADED_VERIFIED", snapshot)
    except _StoreFailure as failure:
        return _reject(failure.code)
    except Exception:
        return _reject("INTERNAL_VALIDATION_FAILED")


def summarize_experiment_family(
    path: object, family_id: object
) -> ExperimentControlResult:
    try:
        family_key = family_id if isinstance(family_id, str) else None
        if family_key is None:
            raise _Failure("FIELD_TYPE_INVALID")
        loaded = load_and_verify_experiment_registry(path)
        if not loaded.is_valid or loaded.snapshot is None:
            raise _Failure(loaded.error_codes[0] if loaded.error_codes else "REGISTRY_INTEGRITY_TAMPER")
        snapshot = _verify_snapshot_object(loaded.snapshot)
        families = [entry.record for entry in snapshot.entries if isinstance(entry.record, ExperimentFamily) and entry.record.experiment_family_id == family_key]
        if len(families) != 1:
            raise _Failure("TRIAL_FAMILY_CONFLICT")
        selected = families[0]
        lineage_ids = {
            entry.record.experiment_family_id
            for entry in snapshot.entries
            if isinstance(entry.record, ExperimentFamily)
            and _family_accounting_key(entry.record)
            == _family_accounting_key(selected)
        }
        experiments = sorted(
            (entry.record for entry in snapshot.entries if isinstance(entry.record, PreregisteredExperiment) and entry.record.experiment_family_id in lineage_ids),
            key=lambda item: item.trial_number,
        )
        evidence = [entry.record for entry in snapshot.entries if isinstance(entry.record, RunEvidenceReceipt) and entry.record.experiment_family_id in lineage_ids]
        lifecycle = [entry.record for entry in snapshot.entries if isinstance(entry.record, LifecycleReceipt)]
        statuses: list[str] = []
        for experiment in experiments:
            experiment_evidence = [item for item in evidence if item.experiment_id == experiment.experiment_id]
            closed = [item for item in lifecycle if item.experiment_id == experiment.experiment_id and item.action == "CLOSE_EXPERIMENT"]
            if closed:
                status = closed[-1].terminal_result_status
            else:
                first_oos = next((item for item in experiment_evidence if item.evaluated_role == "OUT_OF_SAMPLE"), None)
                status = first_oos.result_status if first_oos is not None else experiment_evidence[-1].result_status if experiment_evidence else "REGISTERED_UNEVALUATED"
            statuses.append(status)
        summary = FamilySummary(
            "polymarket-experiment-family-summary", "1.0.0", family_key,
            tuple(item.experiment_id for item in experiments),
            tuple(item.trial_number for item in experiments),
            tuple(item.run_evidence_receipt_id for item in evidence),
            tuple(item.result_status for item in evidence),
            tuple(statuses), len(experiments),
            sum(item != "REGISTERED_UNEVALUATED" for item in statuses),
            len({
                item.experiment_id for item in evidence
                if item.result_status == "EVIDENCE_NEGATIVE"
            }),
            len({
                item.experiment_id for item in evidence
                if item.result_status in {
                    "EVIDENCE_INCONCLUSIVE", "EVIDENCE_INVALIDATED_AFTER_RUN",
                    "OOS_REUSED_DIAGNOSTIC",
                }
            }),
            True, True,
        )
        return _valid(summary)
    except _Failure as failure:
        return _rejected(failure.code)
    except Exception:
        return _rejected("INTERNAL_VALIDATION_FAILED")
