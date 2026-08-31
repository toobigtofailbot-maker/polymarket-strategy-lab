"""Focused tests for the WP162 bounded dataset persistence adapters.

Every persistence test operates on a store created below pytest ``tmp_path``.
The suite re-derives the WP160 reference and manifest-entry identities
independently rather than trusting the adapter helpers, exercises the hostile
input boundary, the provenance rules, the verified-store precondition, the
idempotency / registration-conflict rules, the fail-closed exception boundaries,
and proves the adapter carries no SQL / filesystem / network / clock / execution
authority.
"""

from __future__ import annotations

import ast
import dataclasses
import io
import pathlib
import tokenize

import pytest

import src.data_layer.point_in_time_market_research as pit
from src.data_layer.point_in_time_market_research import dataset_persistence_adapter as A
from src.data_layer.point_in_time_market_research import records as R
from src.data_layer.point_in_time_market_research.as_of_synthetic_cases import (
    build_synthetic_as_of_query_records_for_case as asof_records_for,
    build_synthetic_as_of_records,
)


ADAPTER_SRC = (
    pathlib.Path(__file__).resolve().parents[3]
    / "src"
    / "data_layer"
    / "point_in_time_market_research"
    / "dataset_persistence_adapter.py"
)

BATCH_PARAM = "parameters:wp156:synthetic:v1"
BATCH_VALIDATOR = "validator:wp156:v1"
EFFECTIVE = "2026-01-01T00:00:00Z"
MANIFEST_ID = "manifest:wp162:test"

_BATCH_CASE_BUILDERS = {
    "PIT-C01-VALID-MARKET-METADATA": "build_market_observation",
    "PIT-C03-VALID-PUBLIC-TRADE": "build_market_observation",
    "PIT-C04-VALID-SOURCE-SNAPSHOT": "build_source_snapshot",
    "PIT-C05-VALID-RESOLUTION-RULE-SNAPSHOT": "build_resolution_rule_snapshot",
}


# ── Builders / fixtures ──────────────────────────────────────────────────────


def _batch_record(case_id: str):
    builder = getattr(pit, _BATCH_CASE_BUILDERS[case_id])
    result = builder(pit.load_synthetic_case_input(case_id))
    assert result.is_valid and result.record is not None
    return result.record


def _batch_records() -> list:
    return [
        _batch_record("PIT-C01-VALID-MARKET-METADATA"),
        _batch_record("PIT-C04-VALID-SOURCE-SNAPSHOT"),
        _batch_record("PIT-C05-VALID-RESOLUTION-RULE-SNAPSHOT"),
    ]


def _single_record() -> list:
    return [_batch_record("PIT-C01-VALID-MARKET-METADATA")]


def _store(tmp_path: pathlib.Path, name: str = "store.sqlite") -> pathlib.Path:
    path = tmp_path / name
    result = pit.initialize_manifest_store(path)
    assert result.is_valid, result.error_codes
    return path


def _persist_batch(path, records, **overrides):
    kwargs = dict(
        manifest_id=MANIFEST_ID,
        effective_time=EFFECTIVE,
        parameter_set_id=BATCH_PARAM,
        validator_version=BATCH_VALIDATOR,
    )
    kwargs.update(overrides)
    return pit.persist_validated_record_batch_snapshot(path, records, **kwargs)


def _asof_case(case_id: str):
    return next(
        case
        for case in pit.get_synthetic_as_of_query_cases()
        if case.case_id == case_id
    )


def _persist_asof(path, case_id, **overrides):
    case = _asof_case(case_id)
    records = asof_records_for(case_id)
    kwargs = dict(
        manifest_id=MANIFEST_ID,
        effective_time=EFFECTIVE,
        validator_version="validator:wp157:v1",
    )
    kwargs.update(overrides)
    return pit.persist_as_of_query_snapshot(path, records, case.query_spec, **kwargs), records, case


def _conflict_records() -> list:
    records = build_synthetic_as_of_records()
    conflicts = [
        record
        for record in records.values()
        if record.envelope.classification == "CONFLICT"
    ]
    assert conflicts
    return conflicts


# ── Independent identity re-derivation (mirrors WP158/WP160 preimages) ────────


def _reference_preimage(
    *,
    derivation_mode,
    validated_batch_sha256,
    ordinary_ids,
    review_ids,
    query_spec_sha256=None,
    query_result_sha256=None,
    cutoff_mode=None,
    cutoff_time=None,
    result_view=None,
    query_engine_version=None,
    validator_version,
    parameter_set_id,
):
    return {
        "schema_id": pit.DATASET_REFERENCE_SCHEMA_ID,
        "schema_version": pit.DATASET_REFERENCE_SCHEMA_VERSION,
        "derivation_mode": derivation_mode,
        "validated_batch_sha256": validated_batch_sha256,
        "ordinary_record_version_ids": list(ordinary_ids),
        "review_conflict_record_version_ids": list(review_ids),
        "query_spec_sha256": query_spec_sha256,
        "query_result_sha256": query_result_sha256,
        "cutoff_mode": cutoff_mode,
        "cutoff_time": cutoff_time,
        "result_view": result_view,
        "query_engine_version": query_engine_version,
        "validator_version": validator_version,
        "parameter_set_id": parameter_set_id,
        "human_review_required": bool(review_ids),
        "advisory_only": True,
        "no_execution_authority": True,
    }


def _independent_reference_id(preimage) -> str:
    return "datasetref:sha256:" + pit.sha256_hex(pit.canonical_json_bytes(preimage))


def _independent_entry_id(entry) -> str:
    preimage = {
        "schema_id": pit.MANIFEST_ENTRY_SCHEMA_ID,
        "schema_version": pit.MANIFEST_ENTRY_SCHEMA_VERSION,
        "manifest_id": entry.manifest_id,
        "sequence_number": entry.sequence_number,
        "previous_manifest_entry_id": entry.previous_manifest_entry_id,
        "entry_kind": entry.entry_kind,
        "dataset_snapshot_reference_id": entry.dataset_snapshot_reference_id,
        "supersedes_manifest_entry_id": entry.supersedes_manifest_entry_id,
        "reference_state": entry.reference_state,
        "reason_code": entry.reason_code,
        "effective_time": entry.effective_time,
        "parameter_set_id": entry.parameter_set_id,
        "human_review_required": entry.human_review_required,
        "advisory_only": entry.advisory_only,
        "no_execution_authority": entry.no_execution_authority,
    }
    return "manifestentry:sha256:" + pit.sha256_hex(pit.canonical_json_bytes(preimage))


# ── R001 invalid-result invariant helpers ────────────────────────────────────


def _assert_rejected(result, *codes):
    assert result.is_valid is False
    assert result.status == "ADAPTER_REJECTED"
    assert result.error_codes == tuple(codes)
    assert result.warning_codes == ()
    assert result.dataset_reference is None
    assert result.manifest_entry is None
    assert result.store_status is None
    assert result.human_review_required is False
    assert result.advisory_only is True
    assert result.no_execution_authority is True


def _assert_persisted(result, status):
    assert result.is_valid is True
    assert result.status == status
    assert result.error_codes == ()
    assert result.upstream_error_codes == ()
    assert result.store_error_codes == ()
    assert result.warning_codes == ()
    assert result.dataset_reference is not None
    assert result.manifest_entry is not None
    assert result.advisory_only is True
    assert result.no_execution_authority is True


# ── Public surface ───────────────────────────────────────────────────────────


def test_public_constants_and_vocabularies_are_exact() -> None:
    assert A.DATASET_PERSISTENCE_ADAPTER_LABEL == (
        "POINT_IN_TIME_RESEARCH_DATASET_PERSISTENCE_ADAPTER"
    )
    assert A.DATASET_PERSISTENCE_ADAPTER_POSTURE == (
        "BOUNDED_DETERMINISTIC_WP156_WP157_TO_WP160_WP161_HANDOFF"
    )
    assert A.DATASET_PERSISTENCE_ADAPTER_STATUSES == (
        "ADAPTER_PERSISTED",
        "ADAPTER_ALREADY_PERSISTED",
        "ADAPTER_REJECTED",
    )
    assert A.DATASET_PERSISTENCE_ADAPTER_ERROR_CODES == (
        "ADAPTER_INPUT_INVALID",
        "ADAPTER_BATCH_INVALID",
        "ADAPTER_QUERY_INVALID",
        "ADAPTER_PARAMETER_SET_MISMATCH",
        "ADAPTER_VALIDATOR_VERSION_MISMATCH",
        "ADAPTER_REFERENCE_BUILD_FAILED",
        "ADAPTER_STORE_LOAD_FAILED",
        "ADAPTER_MANIFEST_ID_MISMATCH",
        "ADAPTER_REGISTRATION_CONFLICT",
        "ADAPTER_STORE_STATE_INVALID",
        "ADAPTER_ENTRY_BUILD_FAILED",
        "ADAPTER_STORE_APPEND_FAILED",
        "ADAPTER_PARENT_CONTEXT_INVALID",
        "ADAPTER_PARENT_CONTEXT_UNREGISTERED",
        "ADAPTER_PARENT_CONTEXT_HEAD_CHANGED",
    )


def test_package_exports_contain_the_seven_wp162_symbols_as_a_block() -> None:
    # WP163 appends a further public surface after WP162, so the seven WP162
    # symbols are no longer the package tail. Assert the exact contiguous WP162
    # block located from its label anchor, plus object identity.
    expected = (
        "DATASET_PERSISTENCE_ADAPTER_LABEL",
        "DATASET_PERSISTENCE_ADAPTER_POSTURE",
        "DATASET_PERSISTENCE_ADAPTER_STATUSES",
        "DATASET_PERSISTENCE_ADAPTER_ERROR_CODES",
        "DatasetPersistenceAdapterResult",
        "persist_validated_record_batch_snapshot",
        "persist_as_of_query_snapshot",
    )
    start = pit.__all__.index("DATASET_PERSISTENCE_ADAPTER_LABEL")
    assert pit.__all__[start : start + 7] == expected
    assert all(getattr(pit, name) is getattr(A, name) for name in expected)


def test_result_is_frozen() -> None:
    result = _persist_batch("no-store-needed", None)
    with pytest.raises(dataclasses.FrozenInstanceError):
        result.status = "changed"  # type: ignore[misc]


# ── Batch success ────────────────────────────────────────────────────────────


def test_batch_single_record_genesis_registration(tmp_path) -> None:
    path = _store(tmp_path)
    result = _persist_batch(path, _single_record())
    _assert_persisted(result, "ADAPTER_PERSISTED")
    assert result.store_status == "STORE_APPEND_COMMITTED"
    entry = result.manifest_entry
    assert entry.sequence_number == 0
    assert entry.previous_manifest_entry_id is None
    assert entry.entry_kind == "REGISTER_DATASET_SNAPSHOT_REFERENCE"
    assert entry.manifest_id == MANIFEST_ID
    assert entry.effective_time == EFFECTIVE
    assert result.dataset_reference.derivation_mode == "VALIDATED_RECORD_BATCH"


def test_batch_multi_record_and_ordinary_ids_equal_accepted(tmp_path) -> None:
    path = _store(tmp_path)
    records = _batch_records()
    batch = pit.validate_record_batch(tuple(records))
    result = _persist_batch(path, records)
    _assert_persisted(result, "ADAPTER_PERSISTED")
    assert (
        result.dataset_reference.ordinary_record_version_ids
        == batch.accepted_record_version_ids
    )
    assert result.dataset_reference.review_conflict_record_version_ids == ()


def test_batch_exact_duplicate_committed_once_in_ordinary_ids(tmp_path) -> None:
    path = _store(tmp_path)
    base = _batch_record("PIT-C01-VALID-MARKET-METADATA")
    records = [base, base]
    result = _persist_batch(path, records)
    _assert_persisted(result, "ADAPTER_PERSISTED")
    ordinary = result.dataset_reference.ordinary_record_version_ids
    assert len(ordinary) == len(set(ordinary)) == 1


def test_batch_reference_id_is_deterministic_and_independently_derived(tmp_path) -> None:
    path = _store(tmp_path)
    records = _batch_records()
    batch = pit.validate_record_batch(tuple(records))
    result = _persist_batch(path, records)
    preimage = _reference_preimage(
        derivation_mode="VALIDATED_RECORD_BATCH",
        validated_batch_sha256=batch.canonical_batch_sha256,
        ordinary_ids=batch.accepted_record_version_ids,
        review_ids=(),
        validator_version=BATCH_VALIDATOR,
        parameter_set_id=BATCH_PARAM,
    )
    assert (
        result.dataset_reference.dataset_snapshot_reference_id
        == _independent_reference_id(preimage)
    )


def test_batch_entry_id_is_independently_derived(tmp_path) -> None:
    path = _store(tmp_path)
    result = _persist_batch(path, _batch_records())
    entry = result.manifest_entry
    assert entry.manifest_entry_id == _independent_entry_id(entry)


def test_second_registration_derives_sequence_and_previous_head(tmp_path) -> None:
    path = _store(tmp_path)
    first = _persist_batch(path, _single_record())
    second = _persist_batch(path, _batch_records())
    _assert_persisted(second, "ADAPTER_PERSISTED")
    assert second.manifest_entry.sequence_number == 1
    assert (
        second.manifest_entry.previous_manifest_entry_id
        == first.manifest_entry.manifest_entry_id
    )


def test_persisted_reference_and_entry_survive_reopen(tmp_path) -> None:
    path = _store(tmp_path)
    result = _persist_batch(path, _batch_records())
    reopened = pit.load_and_verify_manifest_store(path)
    assert reopened.is_valid
    assert result.dataset_reference in reopened.snapshot.dataset_references
    assert result.manifest_entry in reopened.snapshot.manifest_entries


def test_exact_retry_is_idempotent(tmp_path) -> None:
    path = _store(tmp_path)
    first = _persist_batch(path, _batch_records())
    retry = _persist_batch(path, _batch_records())
    _assert_persisted(retry, "ADAPTER_ALREADY_PERSISTED")
    assert retry.store_status == "STORE_LOADED_VERIFIED"
    assert retry.dataset_reference == first.dataset_reference
    assert retry.manifest_entry == first.manifest_entry


def test_retry_after_unrelated_later_registration_stays_idempotent(tmp_path) -> None:
    path = _store(tmp_path)
    first = _persist_batch(path, _single_record())
    _persist_batch(path, _batch_records())  # advances the chain
    retry = _persist_batch(path, _single_record())
    _assert_persisted(retry, "ADAPTER_ALREADY_PERSISTED")
    assert retry.manifest_entry == first.manifest_entry
    assert retry.manifest_entry.sequence_number == 0


def test_reference_persisted_but_unregistered_can_be_registered(tmp_path) -> None:
    source_path = _store(tmp_path, "source.sqlite")
    seeded = _persist_batch(source_path, _batch_records())
    reference = seeded.dataset_reference

    target = tmp_path / "target.sqlite"
    assert pit.initialize_manifest_store(target).is_valid
    reference_only = pit.append_manifest_store_batch(
        target, dataset_references=(reference,), manifest_entries=()
    )
    assert reference_only.is_valid
    assert reference_only.snapshot.manifest_entries == ()

    result = _persist_batch(target, _batch_records())
    _assert_persisted(result, "ADAPTER_PERSISTED")
    assert result.dataset_reference == reference
    assert result.manifest_entry.sequence_number == 0


# ── Batch rejection ──────────────────────────────────────────────────────────


def test_empty_batch_is_not_persisted(tmp_path) -> None:
    path = _store(tmp_path)
    _assert_rejected(_persist_batch(path, []), "ADAPTER_BATCH_INVALID")


def test_conflict_batch_is_rejected(tmp_path) -> None:
    path = _store(tmp_path)
    result = _persist_batch(
        path,
        _conflict_records(),
        parameter_set_id="parameters:wp157:synthetic:v1",
        validator_version="validator:wp157:v1",
    )
    _assert_rejected(result, "ADAPTER_BATCH_INVALID")


def test_malformed_direct_record_is_rejected_without_raising(tmp_path) -> None:
    path = _store(tmp_path)
    base = _batch_record("PIT-C01-VALID-MARKET-METADATA")
    tampered = dataclasses.replace(base, market_id="market:synthetic:tampered")
    _assert_rejected(_persist_batch(path, [tampered]), "ADAPTER_BATCH_INVALID")


@pytest.mark.parametrize(
    "hostile",
    [
        None,
        "records",
        b"records",
        {"a": 1},
        {1, 2},
        (x for x in ()),
        iter([]),
    ],
)
def test_hostile_record_container_is_input_invalid(tmp_path, hostile) -> None:
    path = _store(tmp_path)
    _assert_rejected(_persist_batch(path, hostile), "ADAPTER_INPUT_INVALID")


def test_list_subclass_container_is_rejected_and_not_iterated(tmp_path) -> None:
    path = _store(tmp_path)

    class HostileList(list):
        def __iter__(self):  # pragma: no cover - must never be called
            raise AssertionError("subclass iteration must not run")

    hostile = HostileList(_batch_records())
    _assert_rejected(_persist_batch(path, hostile), "ADAPTER_INPUT_INVALID")


def test_generator_records_are_not_consumed(tmp_path) -> None:
    path = _store(tmp_path)
    consumed = []

    def gen():  # pragma: no cover - body must never run
        consumed.append(True)
        yield _batch_record("PIT-C01-VALID-MARKET-METADATA")

    _assert_rejected(_persist_batch(path, gen()), "ADAPTER_INPUT_INVALID")
    assert consumed == []


def test_parameter_set_mismatch(tmp_path) -> None:
    path = _store(tmp_path)
    result = _persist_batch(
        path, _batch_records(), parameter_set_id="parameters:other:v9"
    )
    _assert_rejected(result, "ADAPTER_PARAMETER_SET_MISMATCH")


def test_validator_version_mismatch(tmp_path) -> None:
    path = _store(tmp_path)
    result = _persist_batch(
        path, _batch_records(), validator_version="validator:other:v9"
    )
    _assert_rejected(result, "ADAPTER_VALIDATOR_VERSION_MISMATCH")


@pytest.mark.parametrize(
    "bad",
    [None, "", "   ", " leading", "trailing ", 5, True, b"m", "x" * 257],
)
def test_scalar_boundary_rejects_bad_manifest_id(tmp_path, bad) -> None:
    path = _store(tmp_path)
    _assert_rejected(
        _persist_batch(path, _batch_records(), manifest_id=bad), "ADAPTER_INPUT_INVALID"
    )


def test_missing_store_fails_closed_with_store_codes(tmp_path) -> None:
    missing = tmp_path / "missing.sqlite"
    result = _persist_batch(missing, _batch_records())
    _assert_rejected(result, "ADAPTER_STORE_LOAD_FAILED")
    assert result.store_error_codes == ("STORE_NOT_FOUND",)


def test_malformed_records_beat_missing_store(tmp_path) -> None:
    missing = tmp_path / "missing.sqlite"
    _assert_rejected(_persist_batch(missing, None), "ADAPTER_INPUT_INVALID")


def test_corrupt_store_fails_closed(tmp_path) -> None:
    corrupt = tmp_path / "corrupt.sqlite"
    corrupt.write_bytes(b"this is not a sqlite database" * 8)
    result = _persist_batch(corrupt, _batch_records())
    assert result.error_codes == ("ADAPTER_STORE_LOAD_FAILED",)
    assert result.store_error_codes and all(
        code in pit.MANIFEST_STORE_ERROR_CODES for code in result.store_error_codes
    )


def test_manifest_id_mismatch_against_existing_chain(tmp_path) -> None:
    path = _store(tmp_path)
    _persist_batch(path, _single_record())
    result = _persist_batch(path, _batch_records(), manifest_id="manifest:other:v2")
    _assert_rejected(result, "ADAPTER_MANIFEST_ID_MISMATCH")


def test_registration_effective_time_conflict(tmp_path) -> None:
    path = _store(tmp_path)
    _persist_batch(path, _batch_records())
    result = _persist_batch(
        path, _batch_records(), effective_time="2026-09-09T00:00:00Z"
    )
    _assert_rejected(result, "ADAPTER_REGISTRATION_CONFLICT")


# ── Query success ────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "case_id, view",
    [
        ("ASOF-C01-BEFORE-FIRST-INGESTION", "AUTHORITATIVE_CURRENT_STATE"),
        ("ASOF-C16-VISIBLE-HISTORY", "VISIBLE_HISTORY"),
        ("ASOF-C17-ENTITY-TIMELINE", "ENTITY_TIMELINE"),
    ],
)
def test_query_success_by_view(tmp_path, case_id, view) -> None:
    path = _store(tmp_path)
    result, records, case = _persist_asof(path, case_id)
    _assert_persisted(result, "ADAPTER_PERSISTED")
    reference = result.dataset_reference
    assert reference.derivation_mode == "AS_OF_QUERY_RESULT"
    assert reference.result_view == view
    query_result = pit.query_point_in_time_record_set(records, case.query_spec)
    receipt = query_result.receipt
    if view == "AUTHORITATIVE_CURRENT_STATE":
        assert (
            reference.ordinary_record_version_ids
            == receipt.authoritative_record_version_ids
        )
    else:
        assert (
            reference.ordinary_record_version_ids
            == receipt.history_record_version_ids
        )
    assert (
        reference.review_conflict_record_version_ids
        == receipt.review_conflict_record_version_ids
    )


def test_entity_timeline_ordinary_ids_do_not_duplicate_terminal(tmp_path) -> None:
    path = _store(tmp_path)
    result, records, case = _persist_asof(path, "ASOF-C17-ENTITY-TIMELINE")
    _assert_persisted(result, "ADAPTER_PERSISTED")
    receipt = pit.query_point_in_time_record_set(records, case.query_spec).receipt
    ordinary = result.dataset_reference.ordinary_record_version_ids
    assert ordinary == receipt.history_record_version_ids
    assert len(ordinary) == len(set(ordinary))


def test_query_empty_valid_result_persists(tmp_path) -> None:
    path = _store(tmp_path)
    result, _records, _case = _persist_asof(path, "ASOF-C23-EMPTY-VALID-RECEIPT")
    _assert_persisted(result, "ADAPTER_PERSISTED")
    assert result.dataset_reference.ordinary_record_version_ids == ()
    assert result.dataset_reference.review_conflict_record_version_ids == ()
    assert result.human_review_required is False


def test_query_review_conflict_sets_human_review_required(tmp_path) -> None:
    path = _store(tmp_path)
    result, _records, _case = _persist_asof(path, "ASOF-C19-CONFLICT-REVIEW-ONLY")
    _assert_persisted(result, "ADAPTER_PERSISTED")
    assert result.dataset_reference.review_conflict_record_version_ids
    assert result.dataset_reference.human_review_required is True
    assert result.manifest_entry.human_review_required is True
    assert result.human_review_required is True


def test_query_reference_id_is_independently_derived(tmp_path) -> None:
    path = _store(tmp_path)
    result, records, case = _persist_asof(path, "ASOF-C16-VISIBLE-HISTORY")
    receipt = pit.query_point_in_time_record_set(records, case.query_spec).receipt
    preimage = _reference_preimage(
        derivation_mode="AS_OF_QUERY_RESULT",
        validated_batch_sha256=receipt.validated_batch_sha256,
        ordinary_ids=receipt.history_record_version_ids,
        review_ids=receipt.review_conflict_record_version_ids,
        query_spec_sha256=receipt.query_spec_sha256,
        query_result_sha256=receipt.result_sha256,
        cutoff_mode=receipt.cutoff_mode,
        cutoff_time=receipt.cutoff_time,
        result_view=receipt.result_view,
        query_engine_version=receipt.query_engine_version,
        validator_version="validator:wp157:v1",
        parameter_set_id=receipt.parameter_set_id,
    )
    assert (
        result.dataset_reference.dataset_snapshot_reference_id
        == _independent_reference_id(preimage)
    )


def test_query_exact_retry_is_idempotent(tmp_path) -> None:
    path = _store(tmp_path)
    first, _r, _c = _persist_asof(path, "ASOF-C01-BEFORE-FIRST-INGESTION")
    retry, _r2, _c2 = _persist_asof(path, "ASOF-C01-BEFORE-FIRST-INGESTION")
    _assert_persisted(retry, "ADAPTER_ALREADY_PERSISTED")
    assert retry.dataset_reference == first.dataset_reference
    assert retry.manifest_entry == first.manifest_entry


# ── Query rejection ──────────────────────────────────────────────────────────


def test_wrong_spec_type_is_input_invalid(tmp_path) -> None:
    path = _store(tmp_path)
    records = asof_records_for("ASOF-C01-BEFORE-FIRST-INGESTION")
    result = pit.persist_as_of_query_snapshot(
        path,
        records,
        object(),
        manifest_id=MANIFEST_ID,
        effective_time=EFFECTIVE,
        validator_version="validator:wp157:v1",
    )
    _assert_rejected(result, "ADAPTER_INPUT_INVALID")


def test_invalid_upstream_query_is_query_invalid(tmp_path) -> None:
    path = _store(tmp_path)
    result, _r, _c = _persist_asof(path, "ASOF-C20-INVALID-BATCH-REJECTED")
    _assert_rejected(result, "ADAPTER_QUERY_INVALID")
    assert result.upstream_error_codes


def test_malformed_direct_spec_does_not_raise(tmp_path) -> None:
    path = _store(tmp_path)
    records = asof_records_for("ASOF-C01-BEFORE-FIRST-INGESTION")
    spec = _asof_case("ASOF-C01-BEFORE-FIRST-INGESTION").query_spec
    broken = dataclasses.replace(spec, cutoff_time="not-a-timestamp")
    result = pit.persist_as_of_query_snapshot(
        path,
        records,
        broken,
        manifest_id=MANIFEST_ID,
        effective_time=EFFECTIVE,
        validator_version="validator:wp157:v1",
    )
    _assert_rejected(result, "ADAPTER_QUERY_INVALID")


def test_query_parameter_set_mismatch(tmp_path) -> None:
    path = _store(tmp_path)
    case = _asof_case("ASOF-C01-BEFORE-FIRST-INGESTION")
    records = asof_records_for(case.case_id)
    spec = dataclasses.replace(case.query_spec, parameter_set_id="parameters:other:v9")
    result = pit.persist_as_of_query_snapshot(
        path,
        records,
        spec,
        manifest_id=MANIFEST_ID,
        effective_time=EFFECTIVE,
        validator_version="validator:wp157:v1",
    )
    _assert_rejected(result, "ADAPTER_PARAMETER_SET_MISMATCH")


def test_query_validator_version_mismatch(tmp_path) -> None:
    path = _store(tmp_path)
    result, _r, _c = _persist_asof(
        path, "ASOF-C01-BEFORE-FIRST-INGESTION", validator_version="validator:other:v9"
    )
    _assert_rejected(result, "ADAPTER_VALIDATOR_VERSION_MISMATCH")


def test_query_missing_store_fails_closed(tmp_path) -> None:
    missing = tmp_path / "missing.sqlite"
    result, _r, _c = _persist_asof(missing, "ASOF-C01-BEFORE-FIRST-INGESTION")
    _assert_rejected(result, "ADAPTER_STORE_LOAD_FAILED")
    assert result.store_error_codes == ("STORE_NOT_FOUND",)


def test_query_manifest_id_mismatch(tmp_path) -> None:
    path = _store(tmp_path)
    _persist_batch(path, _batch_records())
    result, _r, _c = _persist_asof(
        path, "ASOF-C01-BEFORE-FIRST-INGESTION", manifest_id="manifest:other:v2"
    )
    _assert_rejected(result, "ADAPTER_MANIFEST_ID_MISMATCH")


# ── Identity sensitivity ─────────────────────────────────────────────────────


def test_one_field_reference_id_sensitivity() -> None:
    base = _reference_preimage(
        derivation_mode="VALIDATED_RECORD_BATCH",
        validated_batch_sha256="a" * 64,
        ordinary_ids=("record:sha256:" + "b" * 64,),
        review_ids=(),
        validator_version=BATCH_VALIDATOR,
        parameter_set_id=BATCH_PARAM,
    )
    other = dict(base)
    other["parameter_set_id"] = BATCH_PARAM + ":changed"
    assert _independent_reference_id(base) != _independent_reference_id(other)


def test_one_field_entry_id_sensitivity(tmp_path) -> None:
    path = _store(tmp_path)
    entry = _persist_batch(path, _batch_records()).manifest_entry
    mutated = dataclasses.replace(entry, effective_time="2027-01-01T00:00:00Z")
    assert _independent_entry_id(entry) != _independent_entry_id(mutated)


# ── Fail-closed exception boundaries (imported names live on the adapter) ─────


def test_batch_validator_exception_is_contained(tmp_path, monkeypatch) -> None:
    path = _store(tmp_path)

    def boom(*args, **kwargs):
        raise RuntimeError("upstream batch secret /etc/passwd")

    monkeypatch.setattr(A, "validate_record_batch", boom)
    result = _persist_batch(path, _batch_records())
    _assert_rejected(result, "ADAPTER_BATCH_INVALID")


def test_query_exception_is_contained(tmp_path, monkeypatch) -> None:
    path = _store(tmp_path)

    def boom(*args, **kwargs):
        raise RuntimeError("upstream query secret")

    monkeypatch.setattr(A, "query_point_in_time_record_set", boom)
    result, _r, _c = _persist_asof(path, "ASOF-C01-BEFORE-FIRST-INGESTION")
    _assert_rejected(result, "ADAPTER_QUERY_INVALID")


def test_reference_builder_exception_is_contained(tmp_path, monkeypatch) -> None:
    path = _store(tmp_path)

    def boom(*args, **kwargs):
        raise RuntimeError("reference secret")

    monkeypatch.setattr(A, "build_dataset_snapshot_reference", boom)
    result = _persist_batch(path, _batch_records())
    _assert_rejected(result, "ADAPTER_REFERENCE_BUILD_FAILED")


def test_entry_builder_exception_is_contained(tmp_path, monkeypatch) -> None:
    path = _store(tmp_path)

    def boom(*args, **kwargs):
        raise RuntimeError("entry secret")

    monkeypatch.setattr(A, "build_manifest_entry", boom)
    result = _persist_batch(path, _batch_records())
    _assert_rejected(result, "ADAPTER_ENTRY_BUILD_FAILED")


def test_store_load_exception_is_contained(tmp_path, monkeypatch) -> None:
    path = _store(tmp_path)

    def boom(*args, **kwargs):
        raise RuntimeError("store load secret")

    monkeypatch.setattr(A, "load_and_verify_manifest_store", boom)
    result = _persist_batch(path, _batch_records())
    _assert_rejected(result, "ADAPTER_STORE_LOAD_FAILED")


def test_store_append_exception_is_contained(tmp_path, monkeypatch) -> None:
    path = _store(tmp_path)

    def boom(*args, **kwargs):
        raise RuntimeError("store append secret")

    monkeypatch.setattr(A, "append_manifest_store_batch", boom)
    result = _persist_batch(path, _batch_records())
    _assert_rejected(result, "ADAPTER_STORE_APPEND_FAILED")


def test_rejected_results_never_echo_secrets(tmp_path, monkeypatch) -> None:
    path = _store(tmp_path)

    def boom(*args, **kwargs):
        raise RuntimeError("SECRET-TOKEN-/etc/passwd")

    monkeypatch.setattr(A, "validate_record_batch", boom)
    result = _persist_batch(path, _batch_records())
    text = repr(dataclasses.astuple(result))
    assert "SECRET-TOKEN" not in text
    assert str(path) not in text
    assert "passwd" not in text


# ── No-mutation / no-retention (R036) ────────────────────────────────────────


def test_original_container_mutation_after_return_does_not_change_result(tmp_path) -> None:
    path = _store(tmp_path)
    records = _batch_records()
    result = _persist_batch(path, records)
    reference_id = result.dataset_reference.dataset_snapshot_reference_id
    entry_id = result.manifest_entry.manifest_entry_id
    records.clear()
    records.append("mutated")
    assert result.dataset_reference.dataset_snapshot_reference_id == reference_id
    assert result.manifest_entry.manifest_entry_id == entry_id


# ── Authority / source-boundary scan ─────────────────────────────────────────


def _adapter_code_names() -> set[str]:
    """Return the set of identifier tokens in adapter code (no strings/comments).

    Only executable code contributes, so the scan cannot be tripped by the
    module docstring or explanatory comments describing forbidden authorities.
    SQL keywords, path literals, and secrets only ever appear inside string
    literals, which are excluded here.
    """

    source = ADAPTER_SRC.read_text(encoding="utf-8")
    names: set[str] = set()
    for token in tokenize.generate_tokens(io.StringIO(source).readline):
        if token.type == tokenize.NAME:
            names.add(token.string)
    return names


def test_adapter_source_has_no_forbidden_authority() -> None:
    names = _adapter_code_names()
    for forbidden in (
        "sqlite3",
        "os",
        "pathlib",
        "open",
        "subprocess",
        "socket",
        "urllib",
        "requests",
        "datetime",
        "time",
        "now",
        "utcnow",
        "environ",
        "getenv",
        "execute",
        "connect",
    ):
        assert forbidden not in names, forbidden
    # No SQL/path/secret literals survive because string literals are excluded;
    # confirm none leaked into an identifier position either.
    assert not any(name.isupper() and " " in name for name in names)


def test_adapter_imports_only_sibling_public_modules() -> None:
    tree = ast.parse(ADAPTER_SRC.read_text(encoding="utf-8"))
    allowed_relative = {
        "as_of_query",
        "manifest_reference",
        "manifest_store",
        "records",
    }
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name in {"dataclasses", "__future__"}, alias.name
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0:
                assert node.module in {"dataclasses", "__future__"}, node.module
            else:
                assert node.level == 1
                assert node.module in allowed_relative, node.module


def test_adapter_does_not_import_sqlite_or_filesystem_modules() -> None:
    for name in ("os", "pathlib", "sqlite3", "socket", "subprocess"):
        assert not hasattr(A, name), name


# ── WP166: lineage-delta (v2) persistence adapter ─────────────────────────────


def _dup_record():
    # PIT-C10 is an EXACT_DUPLICATE whose lineage parent is PIT-C01.
    result = pit.build_market_observation(
        pit.load_synthetic_case_input("PIT-C10-VALID-EXACT-DUPLICATE")
    )
    assert result.is_valid and result.record is not None
    return result.record


def _parent_record():
    return _batch_record("PIT-C01-VALID-MARKET-METADATA")


def _seed_v1_with_parent(tmp_path):
    """Register a v1 batch containing the parent (PIT-C01) and return the path."""

    path = _store(tmp_path)
    seed = _persist_batch(path, [_parent_record()])
    assert seed.is_valid, seed.error_codes
    return path


def _persist_delta(path, current, parents, **overrides):
    kwargs = dict(
        manifest_id=MANIFEST_ID,
        effective_time=EFFECTIVE,
        parameter_set_id=BATCH_PARAM,
        validator_version=BATCH_VALIDATOR,
    )
    kwargs.update(overrides)
    return A.persist_lineage_delta_record_batch_snapshot(
        path, current, parents, **kwargs
    )


def test_lineage_delta_success_registers_v2_reference(tmp_path) -> None:
    path = _seed_v1_with_parent(tmp_path)
    parent = _parent_record()
    dup = _dup_record()
    result = _persist_delta(path, [dup], [parent])
    _assert_persisted(result, "ADAPTER_PERSISTED")
    ref = result.dataset_reference
    assert ref.derivation_mode == "LINEAGE_DELTA_RECORD_BATCH"
    assert ref.ordinary_record_version_ids == (dup.envelope.record_version_id,)
    assert ref.external_parent_record_version_ids == (
        parent.envelope.record_version_id,
    )
    assert ref.created_from_manifest_entry_id is not None
    assert result.manifest_entry.entry_kind == "REGISTER_DATASET_SNAPSHOT_REFERENCE"


def test_lineage_delta_missing_parent_object_rejected(tmp_path) -> None:
    path = _seed_v1_with_parent(tmp_path)
    dup = _dup_record()
    # Required external parent (PIT-C01) not supplied.
    result = _persist_delta(path, [dup], [])
    _assert_rejected(result, "ADAPTER_PARENT_CONTEXT_INVALID")


def test_lineage_delta_extra_unused_parent_object_rejected(tmp_path) -> None:
    path = _seed_v1_with_parent(tmp_path)
    parent = _parent_record()
    dup = _dup_record()
    # An extra parent object that no current record references.
    extra = _batch_record("PIT-C04-VALID-SOURCE-SNAPSHOT")
    result = _persist_delta(path, [dup], [parent, extra])
    _assert_rejected(result, "ADAPTER_PARENT_CONTEXT_INVALID")


def test_lineage_delta_unregistered_parent_rejected(tmp_path) -> None:
    # Seed a v1 baseline that does NOT contain the parent PIT-C01.
    path = _store(tmp_path)
    seed = _persist_batch(path, [_batch_record("PIT-C04-VALID-SOURCE-SNAPSHOT")])
    assert seed.is_valid, seed.error_codes
    parent = _parent_record()
    dup = _dup_record()
    result = _persist_delta(path, [dup], [parent])
    _assert_rejected(result, "ADAPTER_PARENT_CONTEXT_UNREGISTERED")


def test_lineage_delta_parameter_set_mismatch_rejected(tmp_path) -> None:
    path = _seed_v1_with_parent(tmp_path)
    parent = _parent_record()
    dup = _dup_record()
    result = _persist_delta(path, [dup], [parent], parameter_set_id="params:other")
    _assert_rejected(result, "ADAPTER_PARAMETER_SET_MISMATCH")


def test_lineage_delta_validator_version_mismatch_rejected(tmp_path) -> None:
    path = _seed_v1_with_parent(tmp_path)
    parent = _parent_record()
    dup = _dup_record()
    result = _persist_delta(path, [dup], [parent], validator_version="val:other")
    _assert_rejected(result, "ADAPTER_VALIDATOR_VERSION_MISMATCH")


def test_lineage_delta_requires_nonempty_existing_chain(tmp_path) -> None:
    # A freshly-initialized store has no chain; a lineage delta needs a baseline.
    path = _store(tmp_path)
    parent = _parent_record()
    dup = _dup_record()
    result = _persist_delta(path, [dup], [parent])
    _assert_rejected(result, "ADAPTER_STORE_STATE_INVALID")


def test_lineage_delta_input_boundary_rejects_non_records(tmp_path) -> None:
    path = _seed_v1_with_parent(tmp_path)
    result = _persist_delta(path, "not-a-list", [_parent_record()])
    _assert_rejected(result, "ADAPTER_INPUT_INVALID")
    result = _persist_delta(path, [_dup_record()], object())
    _assert_rejected(result, "ADAPTER_INPUT_INVALID")


def test_existing_v1_adapters_unchanged(tmp_path) -> None:
    # The WP156 batch adapter still produces a v1 reference with no external
    # parents and a null backlink.
    path = _store(tmp_path)
    result = _persist_batch(path, _single_record())
    _assert_persisted(result, "ADAPTER_PERSISTED")
    assert result.dataset_reference.derivation_mode == "VALIDATED_RECORD_BATCH"
    assert result.dataset_reference.external_parent_record_version_ids == ()
    assert result.dataset_reference.created_from_manifest_entry_id is None
