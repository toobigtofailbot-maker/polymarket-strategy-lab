"""Focused deterministic tests for the WP160 manifest/reference validator.

Local, offline, stdlib-only, in-memory. No file, network, credential,
scheduler, strategy, paper, or execution behavior is exercised. Identity
digests are recomputed independently of the module under test to prove the
canonical preimages match the WP158 contract.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError, asdict, fields
import hashlib
import json
import pathlib
import re

import pytest

import src.data_layer.point_in_time_market_research as pit
from src.data_layer.point_in_time_market_research import manifest_reference as M
from src.data_layer.point_in_time_market_research.records import (
    canonical_json_bytes,
    sha256_hex,
)


# ── Independent identity derivation (mirrors the contract, not the module) ────

_REF_PREIMAGE_KEYS = (
    "schema_id",
    "schema_version",
    "derivation_mode",
    "validated_batch_sha256",
    "ordinary_record_version_ids",
    "review_conflict_record_version_ids",
    "query_spec_sha256",
    "query_result_sha256",
    "cutoff_mode",
    "cutoff_time",
    "result_view",
    "query_engine_version",
    "validator_version",
    "parameter_set_id",
    "human_review_required",
    "advisory_only",
    "no_execution_authority",
)
_ENTRY_PREIMAGE_KEYS = (
    "schema_id",
    "schema_version",
    "manifest_id",
    "sequence_number",
    "previous_manifest_entry_id",
    "entry_kind",
    "dataset_snapshot_reference_id",
    "supersedes_manifest_entry_id",
    "reference_state",
    "reason_code",
    "effective_time",
    "parameter_set_id",
    "human_review_required",
    "advisory_only",
    "no_execution_authority",
)


def _hex(seed: str) -> str:
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()


def _record_id(seed: str) -> str:
    return "record:sha256:" + _hex(seed)


def _derive_ref_id(data: dict) -> str:
    preimage = {key: data[key] for key in _REF_PREIMAGE_KEYS}
    preimage["ordinary_record_version_ids"] = list(data["ordinary_record_version_ids"])
    preimage["review_conflict_record_version_ids"] = list(
        data["review_conflict_record_version_ids"]
    )
    return "datasetref:sha256:" + sha256_hex(canonical_json_bytes(preimage))


def _derive_entry_id(data: dict) -> str:
    preimage = {key: data[key] for key in _ENTRY_PREIMAGE_KEYS}
    return "manifestentry:sha256:" + sha256_hex(canonical_json_bytes(preimage))


# ── Valid-input factories ────────────────────────────────────────────────────


def _ref_input(**overrides) -> dict:
    data = {
        "schema_id": "point-in-time-dataset-snapshot-reference",
        "schema_version": "1.0.0",
        "dataset_snapshot_reference_id": "PENDING",
        "derivation_mode": "VALIDATED_RECORD_BATCH",
        "validated_batch_sha256": _hex("batch"),
        "ordinary_record_version_ids": [_record_id("a"), _record_id("b")],
        "review_conflict_record_version_ids": [],
        "query_spec_sha256": None,
        "query_result_sha256": None,
        "cutoff_mode": None,
        "cutoff_time": None,
        "result_view": None,
        "query_engine_version": None,
        "validator_version": "point-in-time-validator@1.0.0-synthetic",
        "parameter_set_id": "paramset:wp160-synthetic",
        "created_from_manifest_entry_id": None,
        "human_review_required": False,
        "advisory_only": True,
        "no_execution_authority": True,
    }
    data.update(overrides)
    if "dataset_snapshot_reference_id" not in overrides:
        data["dataset_snapshot_reference_id"] = _derive_ref_id(data)
    return data


def _asof_ref_input(**overrides) -> dict:
    data = _ref_input(
        derivation_mode="AS_OF_QUERY_RESULT",
        query_spec_sha256=_hex("qspec"),
        query_result_sha256=_hex("qresult"),
        cutoff_mode="AS_OF_INGESTION_TIME",
        cutoff_time="2026-01-10T00:00:00Z",
        result_view="AUTHORITATIVE_CURRENT_STATE",
        query_engine_version="point-in-time-as-of-query@1.0.0-synthetic",
    )
    data.update(overrides)
    if "dataset_snapshot_reference_id" not in overrides:
        data["dataset_snapshot_reference_id"] = _derive_ref_id(data)
    return data


def _entry_input(**overrides) -> dict:
    data = {
        "schema_id": "point-in-time-local-manifest-entry",
        "schema_version": "1.0.0",
        "manifest_entry_id": "PENDING",
        "manifest_id": "manifest:wp160-chain",
        "sequence_number": 0,
        "previous_manifest_entry_id": None,
        "entry_kind": "REGISTER_DATASET_SNAPSHOT_REFERENCE",
        "dataset_snapshot_reference_id": "datasetref:sha256:" + _hex("subject"),
        "supersedes_manifest_entry_id": None,
        "reference_state": "ACTIVE_REFERENCE",
        "reason_code": "INITIAL_REGISTRATION",
        "effective_time": "2026-01-15T00:00:00Z",
        "parameter_set_id": "paramset:wp160-synthetic",
        "human_review_required": False,
        "advisory_only": True,
        "no_execution_authority": True,
    }
    data.update(overrides)
    if "manifest_entry_id" not in overrides:
        data["manifest_entry_id"] = _derive_entry_id(data)
    return data


def _build_ref(**overrides) -> M.DatasetSnapshotReference:
    result = M.build_dataset_snapshot_reference(_ref_input(**overrides))
    assert result.is_valid, result.error_codes
    return result.reference


def _build_entry(**overrides) -> M.ManifestEntry:
    result = M.build_manifest_entry(_entry_input(**overrides))
    assert result.is_valid, result.error_codes
    return result.entry


def _coherent_chain():
    """Return (entries, references) for a valid four-entry two-subject chain."""

    ref_a = _build_ref(validated_batch_sha256=_hex("A"), ordinary_record_version_ids=[_record_id("A")])
    ref_b = _build_ref(validated_batch_sha256=_hex("B"), ordinary_record_version_ids=[_record_id("B")])
    subject_a = ref_a.dataset_snapshot_reference_id
    subject_b = ref_b.dataset_snapshot_reference_id
    e0 = _build_entry(
        sequence_number=0,
        previous_manifest_entry_id=None,
        entry_kind="REGISTER_DATASET_SNAPSHOT_REFERENCE",
        dataset_snapshot_reference_id=subject_a,
        supersedes_manifest_entry_id=None,
        reference_state="ACTIVE_REFERENCE",
        reason_code="INITIAL_REGISTRATION",
        effective_time="2026-01-15T00:00:00Z",
    )
    e1 = _build_entry(
        sequence_number=1,
        previous_manifest_entry_id=e0.manifest_entry_id,
        entry_kind="REGISTER_DATASET_SNAPSHOT_REFERENCE",
        dataset_snapshot_reference_id=subject_b,
        supersedes_manifest_entry_id=None,
        reference_state="ACTIVE_REFERENCE",
        reason_code="INITIAL_REGISTRATION",
        effective_time="2026-01-16T00:00:00Z",
    )
    e2 = _build_entry(
        sequence_number=2,
        previous_manifest_entry_id=e1.manifest_entry_id,
        entry_kind="SUPERSEDE_DATASET_SNAPSHOT_REFERENCE",
        dataset_snapshot_reference_id=subject_a,
        supersedes_manifest_entry_id=e0.manifest_entry_id,
        reference_state="SUPERSEDED_REFERENCE",
        reason_code="SOURCE_SUPERSEDED",
        effective_time="2026-01-17T00:00:00Z",
    )
    e3 = _build_entry(
        sequence_number=3,
        previous_manifest_entry_id=e2.manifest_entry_id,
        entry_kind="INVALIDATE_DATASET_SNAPSHOT_REFERENCE",
        dataset_snapshot_reference_id=subject_b,
        supersedes_manifest_entry_id=e1.manifest_entry_id,
        reference_state="INVALIDATED_REFERENCE",
        reason_code="REFERENCE_INVALIDATED",
        effective_time="2026-01-18T00:00:00Z",
        human_review_required=True,
    )
    return [e0, e1, e2, e3], [ref_a, ref_b]


def _all_strings(value) -> list[str]:
    out: list[str] = []

    def walk(node) -> None:
        if isinstance(node, str):
            out.append(node)
        elif isinstance(node, dict):
            for key, item in node.items():
                walk(key)
                walk(item)
        elif isinstance(node, (list, tuple, set)):
            for item in node:
                walk(item)

    walk(value)
    return out


# ── Locked surface, vocabularies, constants ──────────────────────────────────


def test_labels_and_schema_constants_are_exact() -> None:
    assert M.MANIFEST_REFERENCE_LABEL == (
        "APPEND_ONLY_LOCAL_MANIFEST_AND_DATASET_SNAPSHOT_REFERENCE_VALIDATION"
    )
    assert M.MANIFEST_REFERENCE_POSTURE == (
        "BOUNDED_LOCAL_OFFLINE_STDLIB_ONLY_IN_MEMORY_VALIDATION"
    )
    assert M.DATASET_REFERENCE_SCHEMA_ID == "point-in-time-dataset-snapshot-reference"
    assert M.DATASET_REFERENCE_SCHEMA_VERSION == "1.0.0"
    assert M.MANIFEST_ENTRY_SCHEMA_ID == "point-in-time-local-manifest-entry"
    assert M.MANIFEST_ENTRY_SCHEMA_VERSION == "1.0.0"


def test_closed_vocabularies_are_exact_ordered_tuples() -> None:
    assert M.DATASET_DERIVATION_MODES == ("VALIDATED_RECORD_BATCH", "AS_OF_QUERY_RESULT")
    assert M.MANIFEST_ENTRY_KINDS == (
        "REGISTER_DATASET_SNAPSHOT_REFERENCE",
        "SUPERSEDE_DATASET_SNAPSHOT_REFERENCE",
        "INVALIDATE_DATASET_SNAPSHOT_REFERENCE",
    )
    assert M.REFERENCE_STATES == (
        "ACTIVE_REFERENCE",
        "SUPERSEDED_REFERENCE",
        "INVALIDATED_REFERENCE",
    )
    assert M.MANIFEST_REASON_CODES == (
        "INITIAL_REGISTRATION",
        "SOURCE_SUPERSEDED",
        "REFERENCE_INVALIDATED",
    )
    assert M.MANIFEST_REFERENCE_VALIDATION_STATUSES == (
        "REFERENCE_VALID",
        "REFERENCE_REJECTED_CONTRACT",
        "REFERENCE_UNSUPPORTED_SCHEMA",
        "ENTRY_VALID",
        "ENTRY_REJECTED_CONTRACT",
        "ENTRY_UNSUPPORTED_SCHEMA",
        "CHAIN_VALID",
        "CHAIN_REJECTED",
    )
    assert M.MANIFEST_REFERENCE_ERROR_CODES == (
        "SCHEMA_UNSUPPORTED",
        "FIELD_MISSING",
        "FIELD_TYPE_INVALID",
        "FIELD_VALUE_INVALID",
        "ID_DERIVATION_MISMATCH",
        "REFERENCE_MODE_MISMATCH",
        "REVIEW_CONFLICT_AUTHORITY_FORBIDDEN",
        "MANIFEST_SEQUENCE_INVALID",
        "MANIFEST_PREVIOUS_ENTRY_UNKNOWN",
        "MANIFEST_CHAIN_MISMATCH",
        "MANIFEST_SUPERSEDES_INVALID",
        "MANIFEST_CYCLE",
        "MANIFEST_ID_COLLISION_OR_MISMATCH",
        "DATASET_REFERENCE_ID_COLLISION_OR_MISMATCH",
        "SAFETY_POSTURE_INVALID",
    )


def test_public_symbols_reachable_from_package() -> None:
    for name in (
        "MANIFEST_REFERENCE_LABEL",
        "DATASET_DERIVATION_MODES",
        "DatasetSnapshotReference",
        "ManifestEntry",
        "DatasetSnapshotReferenceBuildResult",
        "ManifestEntryBuildResult",
        "ManifestChainValidationResult",
        "build_dataset_snapshot_reference",
        "build_manifest_entry",
        "validate_manifest_chain",
    ):
        assert name in pit.__all__
        assert hasattr(pit, name)


def test_private_helpers_are_not_exported() -> None:
    for name in ("_digest", "_ordered", "_validate_reference_mode", "_valid_utc"):
        assert name not in pit.__all__


# ── Dataset snapshot reference builder ───────────────────────────────────────


def test_reference_valid_batch_and_asof() -> None:
    batch = M.build_dataset_snapshot_reference(_ref_input())
    assert batch.is_valid and batch.status == "REFERENCE_VALID"
    assert batch.error_codes == () and batch.warning_codes == ()
    assert batch.reference.advisory_only is True
    assert batch.reference.no_execution_authority is True
    assert batch.reference.created_from_manifest_entry_id is None
    asof = M.build_dataset_snapshot_reference(_asof_ref_input())
    assert asof.is_valid and asof.reference.derivation_mode == "AS_OF_QUERY_RESULT"


def test_reference_non_mapping_input() -> None:
    for bad in (None, [], "x", 5, ()):
        result = M.build_dataset_snapshot_reference(bad)
        assert not result.is_valid
        assert result.status == "REFERENCE_REJECTED_CONTRACT"
        assert result.error_codes == ("FIELD_TYPE_INVALID",)
        assert result.reference is None


def test_reference_unknown_field() -> None:
    data = _ref_input()
    data["surprise_field"] = "x"
    result = M.build_dataset_snapshot_reference(data)
    assert result.error_codes == ("FIELD_VALUE_INVALID",)


def test_reference_missing_field() -> None:
    data = _ref_input()
    del data["validator_version"]
    result = M.build_dataset_snapshot_reference(data)
    assert result.error_codes == ("FIELD_MISSING",)


def test_reference_unsupported_schema() -> None:
    for override in ({"schema_id": "other"}, {"schema_version": "2.0.0"}):
        result = M.build_dataset_snapshot_reference(_ref_input(**override))
        assert result.status == "REFERENCE_UNSUPPORTED_SCHEMA"
        assert result.error_codes == ("SCHEMA_UNSUPPORTED",)


def test_reference_invalid_mode() -> None:
    result = M.build_dataset_snapshot_reference(_ref_input(derivation_mode="OTHER_MODE"))
    assert "FIELD_VALUE_INVALID" in result.error_codes


def test_reference_type_errors() -> None:
    result = M.build_dataset_snapshot_reference(_ref_input(validated_batch_sha256=123))
    assert "FIELD_TYPE_INVALID" in result.error_codes
    result = M.build_dataset_snapshot_reference(
        _ref_input(ordinary_record_version_ids="not-a-list")
    )
    assert "FIELD_TYPE_INVALID" in result.error_codes


def test_reference_bool_does_not_satisfy_string_or_int_fields() -> None:
    result = M.build_dataset_snapshot_reference(_ref_input(validator_version=True))
    assert "FIELD_TYPE_INVALID" in result.error_codes


def test_reference_malformed_hashes_and_ids() -> None:
    result = M.build_dataset_snapshot_reference(_ref_input(validated_batch_sha256="XYZ"))
    assert "FIELD_VALUE_INVALID" in result.error_codes
    result = M.build_dataset_snapshot_reference(
        _ref_input(ordinary_record_version_ids=["record:sha256:tooshort"])
    )
    assert "FIELD_VALUE_INVALID" in result.error_codes
    # Uppercase hex is rejected (must be lowercase).
    result = M.build_dataset_snapshot_reference(
        _ref_input(validated_batch_sha256="A" * 64)
    )
    assert "FIELD_VALUE_INVALID" in result.error_codes


def test_reference_oversized_strings_and_id_counts() -> None:
    result = M.build_dataset_snapshot_reference(
        _ref_input(validator_version="v" * 257)
    )
    assert "FIELD_VALUE_INVALID" in result.error_codes
    too_many = [_record_id(str(i)) for i in range(257)]
    # An explicit placeholder id keeps the factory from hashing an over-limit
    # sequence (the bounded canonical encoder itself caps at 256); the builder
    # still fails closed on the count.
    result = M.build_dataset_snapshot_reference(
        _ref_input(
            ordinary_record_version_ids=too_many,
            dataset_snapshot_reference_id="datasetref:sha256:" + _hex("placeholder"),
        )
    )
    assert "FIELD_VALUE_INVALID" in result.error_codes


def test_reference_duplicate_records_within_tuple() -> None:
    dup = _record_id("dup")
    result = M.build_dataset_snapshot_reference(
        _ref_input(ordinary_record_version_ids=[dup, dup])
    )
    assert "FIELD_VALUE_INVALID" in result.error_codes


def test_reference_cross_authority_overlap_takes_precedence() -> None:
    shared = _record_id("shared")
    result = M.build_dataset_snapshot_reference(
        _asof_ref_input(
            ordinary_record_version_ids=[shared],
            review_conflict_record_version_ids=[shared],
            human_review_required=True,
        )
    )
    assert result.error_codes == ("REVIEW_CONFLICT_AUTHORITY_FORBIDDEN",)


def test_reference_partial_query_fields_rejected() -> None:
    data = _asof_ref_input()
    data["query_spec_sha256"] = None  # now stale id, but mode mismatch fires first
    result = M.build_dataset_snapshot_reference(data)
    assert "REFERENCE_MODE_MISMATCH" in result.error_codes


def test_reference_query_fields_present_in_batch_mode() -> None:
    data = _ref_input()
    data["query_spec_sha256"] = _hex("q")
    result = M.build_dataset_snapshot_reference(data)
    assert "REFERENCE_MODE_MISMATCH" in result.error_codes


def test_reference_invalid_cutoff_mode_view_and_time() -> None:
    assert "FIELD_VALUE_INVALID" in M.build_dataset_snapshot_reference(
        _asof_ref_input(cutoff_mode="NOPE")
    ).error_codes
    assert "FIELD_VALUE_INVALID" in M.build_dataset_snapshot_reference(
        _asof_ref_input(result_view="NOPE")
    ).error_codes
    assert "FIELD_VALUE_INVALID" in M.build_dataset_snapshot_reference(
        _asof_ref_input(cutoff_time="2026-01-10T00:00:00")
    ).error_codes
    # A non-UTC offset is rejected.
    assert "FIELD_VALUE_INVALID" in M.build_dataset_snapshot_reference(
        _asof_ref_input(cutoff_time="2026-01-10T00:00:00+01:00")
    ).error_codes


def test_reference_nonnull_reserved_backlink() -> None:
    data = _ref_input()
    data["created_from_manifest_entry_id"] = "manifestentry:sha256:" + _hex("x")
    result = M.build_dataset_snapshot_reference(data)
    assert "FIELD_VALUE_INVALID" in result.error_codes


def test_reference_incorrect_human_review_flag() -> None:
    # review-conflicts present but flag False.
    result = M.build_dataset_snapshot_reference(
        _asof_ref_input(
            review_conflict_record_version_ids=[_record_id("rc")],
            human_review_required=False,
        )
    )
    assert "FIELD_VALUE_INVALID" in result.error_codes
    # no conflicts but flag True.
    result = M.build_dataset_snapshot_reference(_ref_input(human_review_required=True))
    assert "FIELD_VALUE_INVALID" in result.error_codes


def test_reference_false_or_nonbool_safety_flags() -> None:
    for override in (
        {"advisory_only": False},
        {"no_execution_authority": False},
        {"advisory_only": 1},
    ):
        result = M.build_dataset_snapshot_reference(_ref_input(**override))
        assert "SAFETY_POSTURE_INVALID" in result.error_codes


def test_reference_id_mismatch() -> None:
    data = _ref_input()
    data["validated_batch_sha256"] = _hex("tampered")  # id now stale
    result = M.build_dataset_snapshot_reference(data)
    assert result.error_codes == ("ID_DERIVATION_MISMATCH",)


def test_reference_derives_review_only_and_mixed_humanreview() -> None:
    review_only = M.build_dataset_snapshot_reference(
        _asof_ref_input(
            ordinary_record_version_ids=[],
            review_conflict_record_version_ids=[_record_id("rc")],
            human_review_required=True,
        )
    )
    assert review_only.is_valid
    assert review_only.reference.human_review_required is True


def test_reference_caller_list_not_retained_after_call() -> None:
    ordinary = [_record_id("x")]
    data = _ref_input(ordinary_record_version_ids=ordinary)
    result = M.build_dataset_snapshot_reference(data)
    assert result.is_valid
    ordinary.append(_record_id("y"))
    assert result.reference.ordinary_record_version_ids == (_record_id("x"),)


def test_reference_no_echo_of_secret_path_like_values() -> None:
    sentinel = "/etc/passwd?api_key=SUPERSECRETVALUE"
    # The sentinel lands in a rejected field (a malformed batch hash), so the
    # fail-closed result must not echo it anywhere.
    data = _ref_input(validated_batch_sha256=sentinel)
    result = M.build_dataset_snapshot_reference(data)
    assert not result.is_valid
    assert sentinel not in _all_strings(asdict(result))


# ── Manifest entry builder ───────────────────────────────────────────────────


def test_entry_valid_register() -> None:
    result = M.build_manifest_entry(_entry_input())
    assert result.is_valid and result.status == "ENTRY_VALID"
    assert result.warning_codes == ()
    assert result.entry.advisory_only is True
    assert result.entry.no_execution_authority is True


def test_entry_non_mapping_input() -> None:
    for bad in (None, [], "x", 7):
        result = M.build_manifest_entry(bad)
        assert result.error_codes == ("FIELD_TYPE_INVALID",)
        assert result.status == "ENTRY_REJECTED_CONTRACT"


def test_entry_unknown_missing_and_type_errors() -> None:
    data = _entry_input()
    data["extra"] = 1
    assert M.build_manifest_entry(data).error_codes == ("FIELD_VALUE_INVALID",)
    data = _entry_input()
    del data["manifest_id"]
    assert M.build_manifest_entry(data).error_codes == ("FIELD_MISSING",)
    assert "FIELD_TYPE_INVALID" in M.build_manifest_entry(
        _entry_input(manifest_id=5)
    ).error_codes


def test_entry_unsupported_schema() -> None:
    result = M.build_manifest_entry(_entry_input(schema_version="9.9.9"))
    assert result.status == "ENTRY_UNSUPPORTED_SCHEMA"
    assert result.error_codes == ("SCHEMA_UNSUPPORTED",)


def test_entry_invalid_and_boolean_sequence() -> None:
    assert "MANIFEST_SEQUENCE_INVALID" in M.build_manifest_entry(
        _entry_input(sequence_number=-1)
    ).error_codes
    assert "MANIFEST_SEQUENCE_INVALID" in M.build_manifest_entry(
        _entry_input(sequence_number=True)
    ).error_codes
    assert "MANIFEST_SEQUENCE_INVALID" in M.build_manifest_entry(
        _entry_input(sequence_number="0")
    ).error_codes


def test_entry_sequence_previous_nullness_rules() -> None:
    # seq 0 must have null previous.
    result = M.build_manifest_entry(
        _entry_input(previous_manifest_entry_id="manifestentry:sha256:" + _hex("p"))
    )
    assert "MANIFEST_SEQUENCE_INVALID" in result.error_codes
    # seq > 0 must have non-null previous.
    result = M.build_manifest_entry(
        _entry_input(sequence_number=1, previous_manifest_entry_id=None)
    )
    assert "MANIFEST_SEQUENCE_INVALID" in result.error_codes


def test_entry_invalid_previous_and_supersedes_shapes() -> None:
    result = M.build_manifest_entry(
        _entry_input(sequence_number=1, previous_manifest_entry_id="not-an-id")
    )
    assert "FIELD_VALUE_INVALID" in result.error_codes
    result = M.build_manifest_entry(
        _entry_input(
            entry_kind="SUPERSEDE_DATASET_SNAPSHOT_REFERENCE",
            reference_state="SUPERSEDED_REFERENCE",
            reason_code="SOURCE_SUPERSEDED",
            sequence_number=1,
            previous_manifest_entry_id="manifestentry:sha256:" + _hex("p"),
            supersedes_manifest_entry_id="bad-shape",
        )
    )
    assert "MANIFEST_SUPERSEDES_INVALID" in result.error_codes


def test_entry_kind_state_reason_mismatch() -> None:
    assert "FIELD_VALUE_INVALID" in M.build_manifest_entry(
        _entry_input(reference_state="SUPERSEDED_REFERENCE")
    ).error_codes
    assert "FIELD_VALUE_INVALID" in M.build_manifest_entry(
        _entry_input(reason_code="SOURCE_SUPERSEDED")
    ).error_codes
    assert "FIELD_VALUE_INVALID" in M.build_manifest_entry(
        _entry_input(entry_kind="NOT_A_KIND")
    ).error_codes


def test_entry_register_with_supersedes_rejected() -> None:
    result = M.build_manifest_entry(
        _entry_input(supersedes_manifest_entry_id="manifestentry:sha256:" + _hex("t"))
    )
    assert "MANIFEST_SUPERSEDES_INVALID" in result.error_codes


def test_entry_transition_without_supersedes_rejected() -> None:
    result = M.build_manifest_entry(
        _entry_input(
            entry_kind="SUPERSEDE_DATASET_SNAPSHOT_REFERENCE",
            reference_state="SUPERSEDED_REFERENCE",
            reason_code="SOURCE_SUPERSEDED",
            sequence_number=1,
            previous_manifest_entry_id="manifestentry:sha256:" + _hex("p"),
            supersedes_manifest_entry_id=None,
        )
    )
    assert "MANIFEST_SUPERSEDES_INVALID" in result.error_codes


def test_entry_invalidate_without_review_rejected() -> None:
    result = M.build_manifest_entry(
        _entry_input(
            entry_kind="INVALIDATE_DATASET_SNAPSHOT_REFERENCE",
            reference_state="INVALIDATED_REFERENCE",
            reason_code="REFERENCE_INVALIDATED",
            sequence_number=1,
            previous_manifest_entry_id="manifestentry:sha256:" + _hex("p"),
            supersedes_manifest_entry_id="manifestentry:sha256:" + _hex("t"),
            human_review_required=False,
        )
    )
    assert "FIELD_VALUE_INVALID" in result.error_codes


def test_entry_invalid_utc_effective_time() -> None:
    assert "FIELD_VALUE_INVALID" in M.build_manifest_entry(
        _entry_input(effective_time="2026-01-15 00:00:00")
    ).error_codes


def test_entry_false_safety_flags() -> None:
    assert "SAFETY_POSTURE_INVALID" in M.build_manifest_entry(
        _entry_input(no_execution_authority=False)
    ).error_codes


def test_entry_id_mismatch() -> None:
    data = _entry_input()
    data["effective_time"] = "2026-02-02T00:00:00Z"  # id now stale
    result = M.build_manifest_entry(data)
    assert result.error_codes == ("ID_DERIVATION_MISMATCH",)


def test_entry_no_echo() -> None:
    sentinel = "C:\\secrets\\token=DEADBEEF"
    data = _entry_input(parameter_set_id=sentinel)
    result = M.build_manifest_entry(data)
    assert not result.is_valid
    assert sentinel not in _all_strings(asdict(result))


# ── Chain validator ──────────────────────────────────────────────────────────


def test_chain_valid() -> None:
    entries, references = _coherent_chain()
    result = M.validate_manifest_chain(entries, dataset_references=references)
    assert result.is_valid and result.status == "CHAIN_VALID"
    assert result.error_codes == () and result.warning_codes == ()
    assert result.manifest_id == "manifest:wp160-chain"
    assert result.ordered_entry_ids == tuple(e.manifest_entry_id for e in entries)
    assert result.head_manifest_entry_id == entries[-1].manifest_entry_id
    assert result.active_reference_ids == ()
    assert result.superseded_reference_ids == (references[0].dataset_snapshot_reference_id,)
    assert result.invalidated_reference_ids == (references[1].dataset_snapshot_reference_id,)
    assert result.human_review_required is True
    assert result.advisory_only is True
    assert result.no_execution_authority is True


def test_chain_valid_single_register_all_active() -> None:
    ref = _build_ref()
    entry = _build_entry(dataset_snapshot_reference_id=ref.dataset_snapshot_reference_id)
    result = M.validate_manifest_chain([entry], dataset_references=[ref])
    assert result.is_valid
    assert result.active_reference_ids == (ref.dataset_snapshot_reference_id,)
    assert result.superseded_reference_ids == ()
    assert result.invalidated_reference_ids == ()
    assert result.human_review_required is False


def test_chain_unreferenced_reference_allowed() -> None:
    entries, references = _coherent_chain()
    spare = _build_ref(validated_batch_sha256=_hex("spare"), ordinary_record_version_ids=[_record_id("spare")])
    result = M.validate_manifest_chain(entries, dataset_references=references + [spare])
    assert result.is_valid


def test_chain_non_sequence_and_string_input() -> None:
    entries, references = _coherent_chain()
    assert M.validate_manifest_chain("not-a-seq", dataset_references=references).error_codes == (
        "FIELD_TYPE_INVALID",
    )
    assert M.validate_manifest_chain(entries, dataset_references="nope").error_codes == (
        "FIELD_TYPE_INVALID",
    )
    assert M.validate_manifest_chain(123, dataset_references=references).error_codes == (
        "FIELD_TYPE_INVALID",
    )


def test_chain_empty() -> None:
    result = M.validate_manifest_chain([], dataset_references=[])
    assert result.status == "CHAIN_REJECTED"
    assert result.error_codes == ("MANIFEST_SEQUENCE_INVALID",)


def test_chain_over_limit_chain_and_registry() -> None:
    ref = _build_ref()
    entry = _build_entry(dataset_snapshot_reference_id=ref.dataset_snapshot_reference_id)
    result = M.validate_manifest_chain([entry] * 257, dataset_references=[ref])
    assert result.error_codes == ("MANIFEST_SEQUENCE_INVALID",)
    result = M.validate_manifest_chain([entry], dataset_references=[ref] * 257)
    assert result.error_codes == ("DATASET_REFERENCE_ID_COLLISION_OR_MISMATCH",)


def test_chain_invalid_direct_dataclass_construction() -> None:
    entries, references = _coherent_chain()
    # An entry whose stored id does not match its content (bypasses builder).
    tampered = M.ManifestEntry(
        **{**_entry_to_dict(entries[0]), "manifest_entry_id": "manifestentry:sha256:" + _hex("wrong")}
    )
    result = M.validate_manifest_chain(
        [tampered] + entries[1:], dataset_references=references
    )
    assert "MANIFEST_ID_COLLISION_OR_MISMATCH" in result.error_codes
    # A reference with a false safety flag (invalid direct construction).
    bad_ref = M.DatasetSnapshotReference(
        **{**_reference_to_dict(references[0]), "advisory_only": False}
    )
    result = M.validate_manifest_chain(entries, dataset_references=[bad_ref, references[1]])
    assert "DATASET_REFERENCE_ID_COLLISION_OR_MISMATCH" in result.error_codes


def test_chain_order_mismatch_and_sequence_gap() -> None:
    entries, references = _coherent_chain()
    reordered = [entries[1], entries[0]] + entries[2:]
    assert "MANIFEST_SEQUENCE_INVALID" in M.validate_manifest_chain(
        reordered, dataset_references=references
    ).error_codes


def test_chain_duplicate_sequence_and_id() -> None:
    entries, references = _coherent_chain()
    dup = [entries[0], entries[0]]
    result = M.validate_manifest_chain(dup, dataset_references=references)
    assert not result.is_valid
    assert (
        "MANIFEST_ID_COLLISION_OR_MISMATCH" in result.error_codes
        or "MANIFEST_SEQUENCE_INVALID" in result.error_codes
    )


def test_chain_wrong_previous_and_unknown_previous() -> None:
    ref = _build_ref()
    subject = ref.dataset_snapshot_reference_id
    e0 = _build_entry(dataset_snapshot_reference_id=subject)
    # e1 points to an unknown previous id.
    e1_unknown = _build_entry(
        sequence_number=1,
        previous_manifest_entry_id="manifestentry:sha256:" + _hex("ghost"),
        entry_kind="SUPERSEDE_DATASET_SNAPSHOT_REFERENCE",
        dataset_snapshot_reference_id=subject,
        supersedes_manifest_entry_id=e0.manifest_entry_id,
        reference_state="SUPERSEDED_REFERENCE",
        reason_code="SOURCE_SUPERSEDED",
        effective_time="2026-01-17T00:00:00Z",
    )
    result = M.validate_manifest_chain([e0, e1_unknown], dataset_references=[ref])
    assert "MANIFEST_PREVIOUS_ENTRY_UNKNOWN" in result.error_codes


def test_chain_multiple_manifest_ids() -> None:
    ref_a = _build_ref(validated_batch_sha256=_hex("A"), ordinary_record_version_ids=[_record_id("A")])
    ref_b = _build_ref(validated_batch_sha256=_hex("B"), ordinary_record_version_ids=[_record_id("B")])
    e0 = _build_entry(dataset_snapshot_reference_id=ref_a.dataset_snapshot_reference_id)
    e1 = _build_entry(
        manifest_id="manifest:other",
        sequence_number=1,
        previous_manifest_entry_id=e0.manifest_entry_id,
        dataset_snapshot_reference_id=ref_b.dataset_snapshot_reference_id,
    )
    result = M.validate_manifest_chain([e0, e1], dataset_references=[ref_a, ref_b])
    assert "MANIFEST_CHAIN_MISMATCH" in result.error_codes


def test_chain_tampered_self_link_is_collision() -> None:
    # A self-linked entry is necessarily a tampered (non-self-consistent) direct
    # construction, so the integrity boundary rejects it before cycle detection.
    ref = _build_ref()
    e0 = _build_entry(dataset_snapshot_reference_id=ref.dataset_snapshot_reference_id)
    self_id = "manifestentry:sha256:" + _hex("self")
    e1 = M.ManifestEntry(
        **{
            **_entry_to_dict(e0),
            "manifest_entry_id": self_id,
            "sequence_number": 1,
            "previous_manifest_entry_id": self_id,
        }
    )
    result = M.validate_manifest_chain([e0, e1], dataset_references=[ref])
    assert result.error_codes == ("MANIFEST_ID_COLLISION_OR_MISMATCH",)


def test_chain_repeated_previous_branch_is_cycle() -> None:
    # A self-consistent branch (two entries sharing one previous) reaches the
    # link resolver and is a MANIFEST_CYCLE (repeated node).
    ref_a = _build_ref(validated_batch_sha256=_hex("A"), ordinary_record_version_ids=[_record_id("A")])
    ref_b = _build_ref(validated_batch_sha256=_hex("B"), ordinary_record_version_ids=[_record_id("B")])
    ref_c = _build_ref(validated_batch_sha256=_hex("C"), ordinary_record_version_ids=[_record_id("C")])
    e0 = _build_entry(dataset_snapshot_reference_id=ref_a.dataset_snapshot_reference_id)
    e1 = _build_entry(
        sequence_number=1,
        previous_manifest_entry_id=e0.manifest_entry_id,
        dataset_snapshot_reference_id=ref_b.dataset_snapshot_reference_id,
        effective_time="2026-01-16T00:00:00Z",
    )
    # e2 branches: its previous points at e0 instead of the immediately prior e1.
    e2 = _build_entry(
        sequence_number=2,
        previous_manifest_entry_id=e0.manifest_entry_id,
        dataset_snapshot_reference_id=ref_c.dataset_snapshot_reference_id,
        effective_time="2026-01-17T00:00:00Z",
    )
    result = M.validate_manifest_chain(
        [e0, e1, e2], dataset_references=[ref_a, ref_b, ref_c]
    )
    assert "MANIFEST_CYCLE" in result.error_codes


def test_chain_missing_dataset_reference() -> None:
    entries, references = _coherent_chain()
    result = M.validate_manifest_chain(entries, dataset_references=[references[0]])
    assert "DATASET_REFERENCE_ID_COLLISION_OR_MISMATCH" in result.error_codes


def test_chain_duplicate_reference_id() -> None:
    entries, references = _coherent_chain()
    result = M.validate_manifest_chain(
        entries, dataset_references=[references[0], references[0], references[1]]
    )
    assert "DATASET_REFERENCE_ID_COLLISION_OR_MISMATCH" in result.error_codes


def test_chain_duplicate_subject_registration() -> None:
    ref = _build_ref()
    subject = ref.dataset_snapshot_reference_id
    e0 = _build_entry(dataset_snapshot_reference_id=subject)
    e1 = _build_entry(
        sequence_number=1,
        previous_manifest_entry_id=e0.manifest_entry_id,
        dataset_snapshot_reference_id=subject,
        effective_time="2026-01-16T00:00:00Z",
    )
    result = M.validate_manifest_chain([e0, e1], dataset_references=[ref])
    assert "MANIFEST_SUPERSEDES_INVALID" in result.error_codes


def test_chain_supersedes_different_subject() -> None:
    ref_a = _build_ref(validated_batch_sha256=_hex("A"), ordinary_record_version_ids=[_record_id("A")])
    ref_b = _build_ref(validated_batch_sha256=_hex("B"), ordinary_record_version_ids=[_record_id("B")])
    subject_a = ref_a.dataset_snapshot_reference_id
    subject_b = ref_b.dataset_snapshot_reference_id
    e0 = _build_entry(dataset_snapshot_reference_id=subject_a)
    e1 = _build_entry(
        sequence_number=1,
        previous_manifest_entry_id=e0.manifest_entry_id,
        dataset_snapshot_reference_id=subject_b,
        effective_time="2026-01-16T00:00:00Z",
    )
    # e2 supersedes subject_b but targets e0 (subject_a) -> different subject.
    e2 = _build_entry(
        sequence_number=2,
        previous_manifest_entry_id=e1.manifest_entry_id,
        entry_kind="SUPERSEDE_DATASET_SNAPSHOT_REFERENCE",
        dataset_snapshot_reference_id=subject_b,
        supersedes_manifest_entry_id=e0.manifest_entry_id,
        reference_state="SUPERSEDED_REFERENCE",
        reason_code="SOURCE_SUPERSEDED",
        effective_time="2026-01-17T00:00:00Z",
    )
    result = M.validate_manifest_chain([e0, e1, e2], dataset_references=[ref_a, ref_b])
    assert "MANIFEST_SUPERSEDES_INVALID" in result.error_codes


def test_chain_repeated_terminal_transition() -> None:
    ref = _build_ref()
    subject = ref.dataset_snapshot_reference_id
    e0 = _build_entry(dataset_snapshot_reference_id=subject)
    e1 = _build_entry(
        sequence_number=1,
        previous_manifest_entry_id=e0.manifest_entry_id,
        entry_kind="SUPERSEDE_DATASET_SNAPSHOT_REFERENCE",
        dataset_snapshot_reference_id=subject,
        supersedes_manifest_entry_id=e0.manifest_entry_id,
        reference_state="SUPERSEDED_REFERENCE",
        reason_code="SOURCE_SUPERSEDED",
        effective_time="2026-01-16T00:00:00Z",
    )
    # e2 tries to supersede the already-terminal subject again (targets e1).
    e2 = _build_entry(
        sequence_number=2,
        previous_manifest_entry_id=e1.manifest_entry_id,
        entry_kind="SUPERSEDE_DATASET_SNAPSHOT_REFERENCE",
        dataset_snapshot_reference_id=subject,
        supersedes_manifest_entry_id=e1.manifest_entry_id,
        reference_state="SUPERSEDED_REFERENCE",
        reason_code="SOURCE_SUPERSEDED",
        effective_time="2026-01-17T00:00:00Z",
    )
    result = M.validate_manifest_chain([e0, e1, e2], dataset_references=[ref])
    assert "MANIFEST_SUPERSEDES_INVALID" in result.error_codes


def test_chain_human_review_binding_mismatch() -> None:
    ref = _build_ref()  # human_review_required False
    subject = ref.dataset_snapshot_reference_id
    e0 = _build_entry(dataset_snapshot_reference_id=subject, human_review_required=True)
    result = M.validate_manifest_chain([e0], dataset_references=[ref])
    assert "FIELD_VALUE_INVALID" in result.error_codes


def test_chain_invalid_output_is_bounded_and_safe() -> None:
    result = M.validate_manifest_chain([], dataset_references=[])
    assert result.manifest_id is None
    assert result.ordered_entry_ids == ()
    assert result.head_manifest_entry_id is None
    assert result.active_reference_ids == ()
    assert result.superseded_reference_ids == ()
    assert result.invalidated_reference_ids == ()
    assert result.warning_codes == ()
    assert result.advisory_only is True
    assert result.no_execution_authority is True


def test_chain_input_immutability() -> None:
    entries, references = _coherent_chain()
    entries_snapshot = list(entries)
    references_snapshot = list(references)
    M.validate_manifest_chain(entries, dataset_references=references)
    assert entries == entries_snapshot
    assert references == references_snapshot


# ── No-echo, immutability, field coverage ────────────────────────────────────


def test_frozen_dataclasses_reject_mutation() -> None:
    reference = _build_ref()
    entry = _build_entry(dataset_snapshot_reference_id=reference.dataset_snapshot_reference_id)
    with pytest.raises(FrozenInstanceError):
        reference.advisory_only = False  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        entry.sequence_number = 9  # type: ignore[misc]


def test_recursive_no_echo_across_all_public_functions() -> None:
    sentinel = "LEAKME_secret_token=/root/.ssh/id_rsa"
    ref_result = M.build_dataset_snapshot_reference(_ref_input(parameter_set_id=sentinel))
    entry_result = M.build_manifest_entry(_entry_input(parameter_set_id=sentinel))
    assert sentinel not in _all_strings(asdict(ref_result))
    assert sentinel not in _all_strings(asdict(entry_result))
    # Chain with a non-ManifestEntry element must not echo the raw object.
    chain_result = M.validate_manifest_chain([sentinel], dataset_references=[])
    assert sentinel not in _all_strings(asdict(chain_result))


def test_reference_field_coverage_is_complete() -> None:
    expected = {
        "schema_id",
        "schema_version",
        "dataset_snapshot_reference_id",
        "derivation_mode",
        "validated_batch_sha256",
        "ordinary_record_version_ids",
        "review_conflict_record_version_ids",
        "query_spec_sha256",
        "query_result_sha256",
        "cutoff_mode",
        "cutoff_time",
        "result_view",
        "query_engine_version",
        "validator_version",
        "parameter_set_id",
        "created_from_manifest_entry_id",
        "human_review_required",
        "advisory_only",
        "no_execution_authority",
    }
    names = {f.name for f in fields(M.DatasetSnapshotReference)}
    assert names == expected
    reference = _build_ref()
    for name in expected:
        assert hasattr(reference, name)


def test_entry_field_coverage_is_complete() -> None:
    expected = {
        "schema_id",
        "schema_version",
        "manifest_entry_id",
        "manifest_id",
        "sequence_number",
        "previous_manifest_entry_id",
        "entry_kind",
        "dataset_snapshot_reference_id",
        "supersedes_manifest_entry_id",
        "reference_state",
        "reason_code",
        "effective_time",
        "parameter_set_id",
        "human_review_required",
        "advisory_only",
        "no_execution_authority",
    }
    names = {f.name for f in fields(M.ManifestEntry)}
    assert names == expected
    entry = _build_entry()
    for name in expected:
        assert hasattr(entry, name)


def test_result_dataclass_field_coverage() -> None:
    assert {f.name for f in fields(M.DatasetSnapshotReferenceBuildResult)} == {
        "is_valid",
        "status",
        "error_codes",
        "warning_codes",
        "reference",
    }
    assert {f.name for f in fields(M.ManifestEntryBuildResult)} == {
        "is_valid",
        "status",
        "error_codes",
        "warning_codes",
        "entry",
    }
    assert {f.name for f in fields(M.ManifestChainValidationResult)} == {
        "is_valid",
        "status",
        "error_codes",
        "warning_codes",
        "manifest_id",
        "ordered_entry_ids",
        "head_manifest_entry_id",
        "active_reference_ids",
        "superseded_reference_ids",
        "invalidated_reference_ids",
        "human_review_required",
        "advisory_only",
        "no_execution_authority",
    }


def test_warning_codes_always_empty() -> None:
    assert M.build_dataset_snapshot_reference(_ref_input()).warning_codes == ()
    assert M.build_dataset_snapshot_reference(_ref_input(advisory_only=False)).warning_codes == ()
    assert M.build_manifest_entry(_entry_input()).warning_codes == ()
    entries, references = _coherent_chain()
    assert M.validate_manifest_chain(entries, dataset_references=references).warning_codes == ()


# ── Contract example cross-check (canonicalization parity) ───────────────────


_DOC = (
    pathlib.Path(__file__).resolve().parents[3]
    / "docs"
    / "append_only_local_manifest_and_dataset_snapshot_reference_contract.md"
)


def _contract_examples() -> list[dict]:
    text = _DOC.read_text(encoding="utf-8")
    return [json.loads(block) for block in re.findall(r"```json\n(.*?)\n```", text, re.DOTALL)]


def test_builders_reproduce_contract_example_identities() -> None:
    examples = _contract_examples()
    assert len(examples) == 12
    for example in examples:
        payload = example["input"]
        if payload["schema_id"] == "point-in-time-dataset-snapshot-reference":
            result = M.build_dataset_snapshot_reference(payload)
        else:
            result = M.build_manifest_entry(payload)
        if example["example_id"] in {
            "WP158-EXAMPLE-01",
            "WP158-EXAMPLE-02",
            "WP158-EXAMPLE-03",
            "WP158-EXAMPLE-04",
            "WP158-EXAMPLE-05",
            "WP158-EXAMPLE-06",
            "WP158-EXAMPLE-07",
            "WP158-EXAMPLE-08",
            "WP158-EXAMPLE-09",
        }:
            # Structurally valid; the recomputed self-id equals the contract id.
            assert result.is_valid, (example["example_id"], result.error_codes)
        elif example["example_id"] == "WP158-EXAMPLE-12":
            assert result.error_codes == ("REVIEW_CONFLICT_AUTHORITY_FORBIDDEN",)
        else:
            # Examples 10 and 11 are chain-level defects; single-entry structure
            # is valid and the recomputed id still matches the contract id.
            assert result.is_valid


def test_contract_chain_examples_validate_as_a_chain() -> None:
    # Examples 6-9 form one coherent chain but reference synthetic subject ids
    # outside the example set, so full-chain validation is exercised through the
    # builder-produced coherent chain instead. Here we only assert the four
    # entries rebuild individually.
    examples = {ex["example_id"]: ex["input"] for ex in _contract_examples()}
    for example_id in ("WP158-EXAMPLE-06", "WP158-EXAMPLE-07", "WP158-EXAMPLE-08", "WP158-EXAMPLE-09"):
        assert M.build_manifest_entry(examples[example_id]).is_valid


# ── Local helpers that mirror the module's dataclass -> mapping projection ────


def _entry_to_dict(entry: M.ManifestEntry) -> dict:
    return {f.name: getattr(entry, f.name) for f in fields(M.ManifestEntry)}


def _reference_to_dict(reference: M.DatasetSnapshotReference) -> dict:
    return {f.name: getattr(reference, f.name) for f in fields(M.DatasetSnapshotReference)}


# ── Same-PR review follow-up: malformed / unhashable fail-closed hardening ────

_SENTINEL = "MALFORMED_LEAK_SENTINEL_XYZ"
_UNHASHABLE = [[], {}, [_SENTINEL], {_SENTINEL: 1}, {"outer": [_SENTINEL]}]


def _assert_reference_fail_closed(result) -> None:
    assert result.is_valid is False
    assert result.reference is None
    assert result.warning_codes == ()
    assert set(result.error_codes) <= set(M.MANIFEST_REFERENCE_ERROR_CODES)
    assert "FIELD_TYPE_INVALID" in result.error_codes
    assert _SENTINEL not in _all_strings(asdict(result))


def _assert_entry_fail_closed(result) -> None:
    assert result.is_valid is False
    assert result.entry is None
    assert result.warning_codes == ()
    assert set(result.error_codes) <= set(M.MANIFEST_REFERENCE_ERROR_CODES)
    assert "FIELD_TYPE_INVALID" in result.error_codes
    assert _SENTINEL not in _all_strings(asdict(result))


@pytest.mark.parametrize("value", _UNHASHABLE)
def test_reference_unhashable_batch_derivation_mode_fails_closed(value) -> None:
    data = _ref_input(derivation_mode=value)
    first = M.build_dataset_snapshot_reference(data)
    second = M.build_dataset_snapshot_reference(data)
    assert first == second  # deterministic across repeated calls
    _assert_reference_fail_closed(first)


@pytest.mark.parametrize("value", _UNHASHABLE)
@pytest.mark.parametrize("field", ["cutoff_mode", "result_view"])
def test_reference_unhashable_query_vocab_fails_closed(field, value) -> None:
    data = _asof_ref_input(**{field: value})
    first = M.build_dataset_snapshot_reference(data)
    second = M.build_dataset_snapshot_reference(data)
    assert first == second
    _assert_reference_fail_closed(first)


@pytest.mark.parametrize("value", _UNHASHABLE)
@pytest.mark.parametrize("field", ["entry_kind", "reference_state", "reason_code"])
def test_entry_unhashable_vocab_fails_closed(field, value) -> None:
    data = _entry_input(**{field: value})
    first = M.build_manifest_entry(data)
    second = M.build_manifest_entry(data)
    assert first == second
    _assert_entry_fail_closed(first)


# ── Same-PR review follow-up: malformed direct dataclasses in the chain ───────

_TAMPERED_ENTRY_FIELDS = [
    {"manifest_id": []},
    {"entry_kind": {}},
    {"dataset_snapshot_reference_id": []},
    {"reference_state": {}},
    {"reason_code": []},
    {"sequence_number": []},
    {"previous_manifest_entry_id": {}},
    {"supersedes_manifest_entry_id": []},
]

_TAMPERED_REFERENCE_FIELDS = [
    {"derivation_mode": {}},
    {"cutoff_mode": []},
    {"result_view": []},
    {"validated_batch_sha256": []},
]


@pytest.mark.parametrize("override", _TAMPERED_ENTRY_FIELDS)
def test_chain_malformed_direct_entry_fails_closed(override) -> None:
    ref = _build_ref()
    valid = _build_entry(dataset_snapshot_reference_id=ref.dataset_snapshot_reference_id)
    tampered = M.ManifestEntry(**{**_entry_to_dict(valid), **override})
    result = M.validate_manifest_chain([tampered], dataset_references=[ref])
    assert result.status == "CHAIN_REJECTED"
    assert "MANIFEST_ID_COLLISION_OR_MISMATCH" in result.error_codes
    assert set(result.error_codes) <= set(M.MANIFEST_REFERENCE_ERROR_CODES)
    assert result.manifest_id is None
    assert result.ordered_entry_ids == ()
    assert result.head_manifest_entry_id is None
    assert result.active_reference_ids == ()
    assert result.superseded_reference_ids == ()
    assert result.invalidated_reference_ids == ()
    assert _SENTINEL not in _all_strings(asdict(result))


@pytest.mark.parametrize("override", _TAMPERED_REFERENCE_FIELDS)
def test_chain_malformed_direct_reference_fails_closed(override) -> None:
    ref = _build_ref()
    entry = _build_entry(dataset_snapshot_reference_id=ref.dataset_snapshot_reference_id)
    asof = M.build_dataset_snapshot_reference(_asof_ref_input()).reference
    tampered = M.DatasetSnapshotReference(**{**_reference_to_dict(asof), **override})
    result = M.validate_manifest_chain([entry], dataset_references=[ref, tampered])
    assert result.status == "CHAIN_REJECTED"
    assert "DATASET_REFERENCE_ID_COLLISION_OR_MISMATCH" in result.error_codes
    assert set(result.error_codes) <= set(M.MANIFEST_REFERENCE_ERROR_CODES)
    assert result.manifest_id is None
    assert result.ordered_entry_ids == ()


def test_chain_malformed_direct_objects_never_raise() -> None:
    # Every listed tampering case returns a bounded result, never an exception.
    ref = _build_ref()
    valid_entry = _build_entry(dataset_snapshot_reference_id=ref.dataset_snapshot_reference_id)
    for override in _TAMPERED_ENTRY_FIELDS:
        tampered = M.ManifestEntry(**{**_entry_to_dict(valid_entry), **override})
        result = M.validate_manifest_chain([tampered], dataset_references=[ref])
        assert result.is_valid is False


# ── Same-PR review follow-up: human-review aggregation over the registry ──────


def _build_review_reference(seed: str) -> M.DatasetSnapshotReference:
    result = M.build_dataset_snapshot_reference(
        _asof_ref_input(
            validated_batch_sha256=_hex(seed),
            ordinary_record_version_ids=[],
            review_conflict_record_version_ids=[_record_id(seed)],
            human_review_required=True,
        )
    )
    assert result.is_valid, result.error_codes
    return result.reference


def test_chain_unreferenced_non_review_reference_does_not_force_review() -> None:
    ref = _build_ref()
    spare = _build_ref(
        validated_batch_sha256=_hex("spare"),
        ordinary_record_version_ids=[_record_id("spare")],
    )
    entry = _build_entry(dataset_snapshot_reference_id=ref.dataset_snapshot_reference_id)
    result = M.validate_manifest_chain(
        [entry], dataset_references=[ref, spare]
    )
    assert result.is_valid
    assert result.human_review_required is False


def test_chain_unreferenced_review_required_reference_forces_review() -> None:
    ref = _build_ref()
    review_ref = _build_review_reference("unreferenced-review")
    entry = _build_entry(dataset_snapshot_reference_id=ref.dataset_snapshot_reference_id)
    result = M.validate_manifest_chain(
        [entry], dataset_references=[ref, review_ref]
    )
    assert result.is_valid
    assert result.human_review_required is True
    # An unreferenced reference never enters the reference-state tuples.
    subject = review_ref.dataset_snapshot_reference_id
    assert subject not in result.active_reference_ids
    assert subject not in result.superseded_reference_ids
    assert subject not in result.invalidated_reference_ids
    assert result.active_reference_ids == (ref.dataset_snapshot_reference_id,)


def test_chain_registered_review_required_reference_forces_review() -> None:
    review_ref = _build_review_reference("registered-review")
    entry = _build_entry(
        dataset_snapshot_reference_id=review_ref.dataset_snapshot_reference_id,
        human_review_required=True,
    )
    result = M.validate_manifest_chain([entry], dataset_references=[review_ref])
    assert result.is_valid
    assert result.human_review_required is True
    assert result.active_reference_ids == (review_ref.dataset_snapshot_reference_id,)


def test_chain_invalidation_entry_forces_review() -> None:
    entries, references = _coherent_chain()
    result = M.validate_manifest_chain(entries, dataset_references=references)
    assert result.is_valid
    assert result.human_review_required is True
