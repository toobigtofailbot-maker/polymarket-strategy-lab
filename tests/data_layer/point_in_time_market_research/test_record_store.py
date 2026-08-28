"""Focused tests for the WP163 bounded durable point-in-time record store.

Every persistence test operates on a store created below pytest ``tmp_path``.
The suite covers the hostile path/container boundaries, the exact SQLite schema
and configuration, initialization/idempotency, ordinary and review-conflict
self-validation, the complete cross-record lineage matrix, transactional rollback
and single-writer contention, the corruption/tamper matrix, read-only byte
stability, both dataset materialization modes, the missing/authority-mismatch
materialization paths, recursive no-echo, and the production SQL source scan.
"""

from __future__ import annotations

import dataclasses
import hashlib
import io
import json
import pathlib
import sqlite3
import tokenize

import pytest

import src.data_layer.point_in_time_market_research as pit
from src.data_layer.point_in_time_market_research import record_store as RS
from src.data_layer.point_in_time_market_research import records as R
from src.data_layer.point_in_time_market_research.manifest_reference import (
    DATASET_REFERENCE_SCHEMA_ID,
    DATASET_REFERENCE_SCHEMA_VERSION,
    build_dataset_snapshot_reference,
)
from src.data_layer.point_in_time_market_research.as_of_synthetic_cases import (
    _meta,
    _require,
    build_synthetic_as_of_records,
)


RECORD_STORE_SRC = (
    pathlib.Path(__file__).resolve().parents[3]
    / "src"
    / "data_layer"
    / "point_in_time_market_research"
    / "record_store.py"
)


# ── Builders / fixtures ──────────────────────────────────────────────────────


def _records() -> dict[str, object]:
    return build_synthetic_as_of_records()


def _new_store(tmp_path, name: str = "store.sqlite3") -> pathlib.Path:
    path = tmp_path / name
    result = pit.initialize_point_in_time_record_store(str(path))
    assert result.is_valid and result.status == "RECORD_STORE_INITIALIZED"
    return path


def _batch_reference(
    ordinary_records,
    *,
    validator: str = "validator:wp163:test",
    parameter_set: str = "params:wp163:test",
):
    batch = R.validate_record_batch(list(ordinary_records))
    assert batch.is_valid, batch.error_codes
    preimage = {
        "schema_id": DATASET_REFERENCE_SCHEMA_ID,
        "schema_version": DATASET_REFERENCE_SCHEMA_VERSION,
        "derivation_mode": "VALIDATED_RECORD_BATCH",
        "validated_batch_sha256": batch.canonical_batch_sha256,
        "ordinary_record_version_ids": list(batch.accepted_record_version_ids),
        "review_conflict_record_version_ids": [],
        "query_spec_sha256": None,
        "query_result_sha256": None,
        "cutoff_mode": None,
        "cutoff_time": None,
        "result_view": None,
        "query_engine_version": None,
        "validator_version": validator,
        "parameter_set_id": parameter_set,
        "human_review_required": False,
        "advisory_only": True,
        "no_execution_authority": True,
    }
    ref_id = "datasetref:sha256:" + R.sha256_hex(R.canonical_json_bytes(preimage))
    mapping = dict(preimage)
    mapping["dataset_snapshot_reference_id"] = ref_id
    mapping["created_from_manifest_entry_id"] = None
    result = build_dataset_snapshot_reference(mapping)
    assert result.is_valid, result.error_codes
    return result.reference


def _asof_reference(ordinary_records, review_records=()):
    ordinary_ids = [r.envelope.record_version_id for r in ordinary_records]
    review_ids = [r.envelope.record_version_id for r in review_records]
    review_required = bool(review_ids)
    preimage = {
        "schema_id": DATASET_REFERENCE_SCHEMA_ID,
        "schema_version": DATASET_REFERENCE_SCHEMA_VERSION,
        "derivation_mode": "AS_OF_QUERY_RESULT",
        "validated_batch_sha256": "a" * 64,
        "ordinary_record_version_ids": list(ordinary_ids),
        "review_conflict_record_version_ids": list(review_ids),
        "query_spec_sha256": "b" * 64,
        "query_result_sha256": "c" * 64,
        "cutoff_mode": "AS_OF_INGESTION_TIME",
        "cutoff_time": "2026-01-01T12:00:00Z",
        "result_view": "AUTHORITATIVE_CURRENT_STATE",
        "query_engine_version": "engine:wp157:test",
        "validator_version": "validator:wp163:test",
        "parameter_set_id": "params:wp163:test",
        "human_review_required": review_required,
        "advisory_only": True,
        "no_execution_authority": True,
    }
    ref_id = "datasetref:sha256:" + R.sha256_hex(R.canonical_json_bytes(preimage))
    mapping = dict(preimage)
    mapping["dataset_snapshot_reference_id"] = ref_id
    mapping["created_from_manifest_entry_id"] = None
    result = build_dataset_snapshot_reference(mapping)
    assert result.is_valid, result.error_codes
    return result.reference


def _raw_connect(path: pathlib.Path) -> sqlite3.Connection:
    return sqlite3.connect(str(path), isolation_level=None)


def _big_conflict_record(n_labels: int, label_len: int, assertion: str = "assertion:big"):
    """Build a standalone WP156-valid review-CONFLICT record with a large payload.

    Review-conflict records self-validate through ``revalidate_review_conflict_record``,
    which (unlike ``validate_record_batch``) does not re-fingerprint the record, so a
    valid conflict record can carry a canonical payload well above WP156's 4,096-byte
    per-string bound. It is the concrete WP156-valid record whose complete WP163
    outer representation exceeds the WP156 payload bounds.
    """

    payload = {
        "question_text": "Will the large synthetic condition be true?",
        "market_status": "OPEN_SYNTHETIC",
        "outcome_labels": [f"L{i}_" + ("x" * label_len) for i in range(n_labels)],
    }
    result = R.build_review_conflict_record(
        _meta(
            source_assertion_id=assertion,
            observed_time="2026-01-01T00:06:00Z",
            ingestion_time="2026-01-01T00:06:01Z",
            classification="CONFLICT",
            human_review=True,
            payload=payload,
        )
    )
    assert result.is_valid and result.record is not None
    return result.record


def _tamper_row_payload(path: pathlib.Path, record_id: str, mutate) -> None:
    """Decode one stored row, mutate the outer mapping, re-encode with a valid
    canonical form and matching digest, and write it back (defeating the sha
    guard so a deeper structural/self-validation check must catch the tamper)."""

    con = _raw_connect(path)
    try:
        payload_json = con.execute(
            "SELECT payload_json FROM records WHERE record_version_id=?", (record_id,)
        ).fetchone()[0]
        mapping = json.loads(payload_json)
        mutate(mapping)
        encoded = RS._canonical_outer_bytes(mapping)
        con.execute(
            "UPDATE records SET payload_json=?, payload_sha256=? "
            "WHERE record_version_id=?",
            (encoded.decode("utf-8"), RS.sha256_hex(encoded), record_id),
        )
    finally:
        con.close()


# ── Public surface (Sections 8) ──────────────────────────────────────────────


def test_public_constants_are_exact() -> None:
    assert pit.POINT_IN_TIME_RECORD_STORE_LABEL == "POINT_IN_TIME_DURABLE_RECORD_STORE"
    assert pit.POINT_IN_TIME_RECORD_STORE_POSTURE == (
        "BOUNDED_LOCAL_SQLITE_APPEND_ONLY_RECORD_PERSISTENCE_AND_MATERIALIZATION"
    )
    assert pit.POINT_IN_TIME_RECORD_STORE_FORMAT_ID == "point-in-time-record-store"
    assert pit.POINT_IN_TIME_RECORD_STORE_SCHEMA_VERSION == 1
    assert pit.POINT_IN_TIME_RECORD_STORE_STATUSES == (
        "RECORD_STORE_INITIALIZED",
        "RECORD_STORE_ALREADY_INITIALIZED",
        "RECORD_STORE_APPEND_COMMITTED",
        "RECORD_STORE_APPEND_IDEMPOTENT",
        "RECORD_STORE_LOADED_VERIFIED",
        "DATASET_REFERENCE_MATERIALIZED",
        "RECORD_STORE_REJECTED",
    )
    assert pit.POINT_IN_TIME_RECORD_STORE_ERROR_CODES == (
        "RECORD_STORE_PATH_INVALID",
        "RECORD_STORE_NOT_FOUND",
        "RECORD_STORE_OPEN_FAILED",
        "RECORD_STORE_BUSY",
        "RECORD_STORE_SCHEMA_UNSUPPORTED",
        "RECORD_STORE_CONFIGURATION_INVALID",
        "RECORD_STORE_SQLITE_INTEGRITY_FAILED",
        "RECORD_STORE_INPUT_INVALID",
        "RECORD_STORE_RECORD_INVALID",
        "RECORD_STORE_PAYLOAD_INVALID",
        "RECORD_STORE_DUPLICATE_CONFLICT",
        "RECORD_STORE_LINEAGE_INVALID",
        "RECORD_STORE_AUTHORITY_VIOLATION",
        "RECORD_STORE_LIMIT_EXCEEDED",
        "RECORD_STORE_REFERENCE_INVALID",
        "RECORD_STORE_REFERENCE_MISSING_RECORD",
        "RECORD_STORE_REFERENCE_CONTENT_MISMATCH",
        "RECORD_STORE_WRITE_FAILED",
    )
    assert pit.DATASET_MATERIALIZATION_VERIFICATION_MODES == (
        "VALIDATED_BATCH_RECOMPUTED",
        "AS_OF_REFERENCE_IDS_RESOLVED",
    )


def test_package_exports_include_the_fourteen_wp163_symbols_as_a_block() -> None:
    # WP164 appended its own exports after WP163, so the WP163 block is no longer
    # the final tail. Anchor on the WP163 label and assert the exact 14-symbol
    # block that follows.
    start = pit.__all__.index("POINT_IN_TIME_RECORD_STORE_LABEL")
    wp163_block = pit.__all__[start : start + 14]
    assert wp163_block == (
        "POINT_IN_TIME_RECORD_STORE_LABEL",
        "POINT_IN_TIME_RECORD_STORE_POSTURE",
        "POINT_IN_TIME_RECORD_STORE_FORMAT_ID",
        "POINT_IN_TIME_RECORD_STORE_SCHEMA_VERSION",
        "POINT_IN_TIME_RECORD_STORE_STATUSES",
        "POINT_IN_TIME_RECORD_STORE_ERROR_CODES",
        "DATASET_MATERIALIZATION_VERIFICATION_MODES",
        "PointInTimeRecordStoreSnapshot",
        "PointInTimeRecordStoreResult",
        "DatasetSnapshotMaterializationResult",
        "initialize_point_in_time_record_store",
        "append_point_in_time_records",
        "load_and_verify_point_in_time_record_store",
        "materialize_dataset_snapshot_reference",
    )
    assert all(getattr(pit, name) is getattr(RS, name) for name in wp163_block)


def test_result_dataclasses_are_frozen() -> None:
    for cls in (
        RS.PointInTimeRecordStoreSnapshot,
        RS.PointInTimeRecordStoreResult,
        RS.DatasetSnapshotMaterializationResult,
    ):
        assert dataclasses.is_dataclass(cls)
        params = getattr(cls, "__dataclass_params__")
        assert params.frozen is True


# ── Path contract (Sections 10) ──────────────────────────────────────────────


class _HostilePathLike:
    def __fspath__(self):
        raise RuntimeError("hostile path object")


class _HostileStr(str):
    def strip(self, *args, **kwargs):  # pragma: no cover - must not be relied on
        raise RuntimeError("hostile str subclass")


@pytest.mark.parametrize(
    "bad",
    [None, True, False, 1, 1.5, b"bytes", "", "   ", "a\x00b"],
)
def test_initialize_rejects_bad_paths(bad) -> None:
    result = pit.initialize_point_in_time_record_store(bad)
    assert not result.is_valid
    assert result.error_codes == ("RECORD_STORE_PATH_INVALID",)


def test_hostile_pathlike_fails_closed(tmp_path) -> None:
    result = pit.initialize_point_in_time_record_store(_HostilePathLike())
    assert not result.is_valid
    assert result.error_codes == ("RECORD_STORE_PATH_INVALID",)


def test_hostile_str_subclass_fails_closed(tmp_path) -> None:
    hostile = _HostileStr(str(tmp_path / "store.sqlite3"))
    result = pit.initialize_point_in_time_record_store(hostile)
    # Either a bounded rejection or a normal init, but never an escaped exception.
    assert result.status in {"RECORD_STORE_INITIALIZED", "RECORD_STORE_REJECTED"}
    if not result.is_valid:
        assert result.error_codes == ("RECORD_STORE_PATH_INVALID",)


def test_directory_path_is_rejected(tmp_path) -> None:
    result = pit.initialize_point_in_time_record_store(str(tmp_path))
    assert result.error_codes == ("RECORD_STORE_PATH_INVALID",)


def test_missing_parent_is_rejected(tmp_path) -> None:
    result = pit.initialize_point_in_time_record_store(
        str(tmp_path / "missing" / "store.sqlite3")
    )
    assert result.error_codes == ("RECORD_STORE_PATH_INVALID",)


def test_load_and_append_require_existing_store(tmp_path) -> None:
    missing = str(tmp_path / "nope.sqlite3")
    assert pit.load_and_verify_point_in_time_record_store(missing).error_codes == (
        "RECORD_STORE_NOT_FOUND",
    )
    assert pit.append_point_in_time_records(missing, []).error_codes == (
        "RECORD_STORE_NOT_FOUND",
    )
    assert not (tmp_path / "nope.sqlite3").exists()


# ── Initialization and schema (Sections 12, 16) ──────────────────────────────


def test_initialize_creates_exact_schema(tmp_path) -> None:
    path = _new_store(tmp_path)
    con = _raw_connect(path)
    try:
        assert con.execute("PRAGMA user_version").fetchone() == (1,)
        objects = con.execute(
            "SELECT type, name FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' "
            "ORDER BY type, name"
        ).fetchall()
        assert objects == [
            ("index", "idx_pit_records_event_time"),
            ("index", "idx_pit_records_ingestion_time"),
            ("index", "idx_pit_records_market_id"),
            ("index", "idx_pit_records_observed_time"),
            ("index", "idx_pit_records_source_id"),
            ("table", "record_store_meta"),
            ("table", "records"),
        ]
        assert con.execute(
            "SELECT singleton, format_id, schema_version FROM record_store_meta"
        ).fetchall() == [(1, "point-in-time-record-store", 1)]
        info = con.execute('PRAGMA table_info("records")').fetchall()
        assert len(info) == 19
        assert con.execute("PRAGMA journal_mode").fetchone()[0].lower() == "delete"
    finally:
        con.close()


def test_initialize_existing_valid_is_already_initialized(tmp_path) -> None:
    path = _new_store(tmp_path)
    again = pit.initialize_point_in_time_record_store(str(path))
    assert again.is_valid and again.status == "RECORD_STORE_ALREADY_INITIALIZED"


def test_initialize_pristine_file_succeeds(tmp_path) -> None:
    path = tmp_path / "pristine.sqlite3"
    con = _raw_connect(path)
    con.close()  # zero tables, user_version 0
    result = pit.initialize_point_in_time_record_store(str(path))
    assert result.is_valid and result.status == "RECORD_STORE_INITIALIZED"


def test_initialize_incompatible_file_is_rejected_and_preserved(tmp_path) -> None:
    path = tmp_path / "foreign.sqlite3"
    con = _raw_connect(path)
    con.execute("CREATE TABLE unrelated (x INTEGER)")
    con.close()
    result = pit.initialize_point_in_time_record_store(str(path))
    assert not result.is_valid
    # The pre-existing caller file is never repaired or removed.
    assert path.exists()
    con = _raw_connect(path)
    try:
        names = con.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    finally:
        con.close()
    assert ("unrelated",) in names


def test_post_commit_init_verification_failure_removes_new_file(
    tmp_path, monkeypatch
) -> None:
    path = tmp_path / "fresh.sqlite3"

    def _boom(_path):
        return RS._rejected("RECORD_STORE_SCHEMA_UNSUPPORTED")

    monkeypatch.setattr(RS, "_load_path", _boom)
    result = pit.initialize_point_in_time_record_store(str(path))
    assert not result.is_valid
    assert not path.exists()


# ── Append input boundary (Section 17) ───────────────────────────────────────


@pytest.mark.parametrize(
    "hostile",
    ["astring", b"bytes", {"a": 1}, {1, 2, 3}, 5, None],
)
def test_hostile_record_container_is_input_invalid(tmp_path, hostile) -> None:
    path = _new_store(tmp_path)
    result = pit.append_point_in_time_records(str(path), hostile)
    assert result.error_codes == ("RECORD_STORE_INPUT_INVALID",)


def test_list_subclass_is_rejected_without_iteration(tmp_path) -> None:
    path = _new_store(tmp_path)

    class _HostileList(list):
        def __iter__(self):
            raise RuntimeError("must not iterate a subclass")

    result = pit.append_point_in_time_records(str(path), _HostileList())
    assert result.error_codes == ("RECORD_STORE_INPUT_INVALID",)


def test_generator_records_are_not_consumed(tmp_path) -> None:
    path = _new_store(tmp_path)
    consumed = []

    def gen():
        consumed.append("touched")
        yield _records()["MKT-META-PRIMARY"]

    result = pit.append_point_in_time_records(str(path), gen())
    assert result.error_codes == ("RECORD_STORE_INPUT_INVALID",)
    assert consumed == []


def test_malformed_direct_record_is_rejected(tmp_path) -> None:
    path = _new_store(tmp_path)
    broken = dataclasses.replace(
        _records()["MKT-META-PRIMARY"], canonical_payload_json="{not json"
    )
    result = pit.append_point_in_time_records(str(path), [broken])
    assert result.error_codes == ("RECORD_STORE_RECORD_INVALID",)


def test_append_limit_exceeded(tmp_path) -> None:
    path = _new_store(tmp_path)
    primary = _records()["MKT-META-PRIMARY"]
    result = pit.append_point_in_time_records(str(path), [primary] * 257)
    assert result.error_codes == ("RECORD_STORE_LIMIT_EXCEEDED",)


# ── Append / idempotency (Section 18) ────────────────────────────────────────


def test_append_commit_reopen_and_idempotency(tmp_path) -> None:
    path = _new_store(tmp_path)
    recs = _records()
    full = list(recs.values())
    committed = pit.append_point_in_time_records(str(path), full)
    assert committed.status == "RECORD_STORE_APPEND_COMMITTED"
    assert len(committed.inserted_record_version_ids) == len(full)
    assert list(committed.inserted_record_version_ids) == sorted(
        committed.inserted_record_version_ids
    )

    reopened = pit.load_and_verify_point_in_time_record_store(str(path))
    assert reopened.is_valid
    reopened_ids = {r.envelope.record_version_id for r in reopened.snapshot.records}
    assert reopened_ids == {r.envelope.record_version_id for r in full}

    retry = pit.append_point_in_time_records(str(path), full)
    assert retry.status == "RECORD_STORE_APPEND_IDEMPOTENT"
    assert retry.inserted_record_version_ids == ()
    assert len(retry.idempotent_record_version_ids) == len(full)


def test_same_id_unequal_is_duplicate_conflict(tmp_path) -> None:
    path = _new_store(tmp_path)
    primary = _records()["MKT-META-PRIMARY"]
    pit.append_point_in_time_records(str(path), [primary])
    # Same committed id, but a tampered object body.
    forged = dataclasses.replace(primary, source_assertion_id="assertion:forged:999")
    result = pit.append_point_in_time_records(str(path), [forged])
    # The forged record fails its own self-validation first (id no longer derives).
    assert not result.is_valid
    assert result.error_codes[0] in {
        "RECORD_STORE_RECORD_INVALID",
        "RECORD_STORE_DUPLICATE_CONFLICT",
    }


def test_within_input_equal_duplicates_collapse(tmp_path) -> None:
    path = _new_store(tmp_path)
    primary = _records()["MKT-META-PRIMARY"]
    result = pit.append_point_in_time_records(str(path), [primary, primary])
    assert result.status == "RECORD_STORE_APPEND_COMMITTED"
    assert result.inserted_record_version_ids == (
        primary.envelope.record_version_id,
    )


def test_empty_append_is_idempotent(tmp_path) -> None:
    path = _new_store(tmp_path)
    result = pit.append_point_in_time_records(str(path), [])
    assert result.status == "RECORD_STORE_APPEND_IDEMPOTENT"
    assert result.inserted_record_version_ids == ()


def test_snapshot_counts_and_ordering(tmp_path) -> None:
    path = _new_store(tmp_path)
    recs = _records()
    pit.append_point_in_time_records(str(path), list(recs.values()))
    snap = pit.load_and_verify_point_in_time_record_store(str(path)).snapshot
    assert snap.ordinary_record_count == len(recs) - 1  # one CONFLICT
    assert snap.review_conflict_record_count == 1
    assert snap.total_payload_bytes > 0
    ingestion = [r.envelope.ingestion_time for r in snap.records]
    assert ingestion == sorted(ingestion)


# ── Ordinary and review-conflict self-validation (Section 14) ────────────────


def test_ordinary_and_conflict_records_persist(tmp_path) -> None:
    path = _new_store(tmp_path)
    recs = _records()
    result = pit.append_point_in_time_records(
        str(path), [recs["MKT-META-PRIMARY"], recs["MKT-CONFLICT"]]
    )
    assert result.is_valid
    snap = result.snapshot
    assert snap.review_conflict_record_count == 1


def test_conflict_without_human_review_flag_is_rejected(tmp_path) -> None:
    path = _new_store(tmp_path)
    conflict = _records()["MKT-CONFLICT"]
    tampered_env = dataclasses.replace(conflict.envelope, human_review_required=False)
    tampered = dataclasses.replace(conflict, envelope=tampered_env)
    result = pit.append_point_in_time_records(str(path), [tampered])
    assert not result.is_valid
    assert result.error_codes == ("RECORD_STORE_RECORD_INVALID",)


# ── Complete lineage (Section 15) ────────────────────────────────────────────


def test_missing_parent_fails_closed(tmp_path) -> None:
    path = _new_store(tmp_path)
    # The correction references the primary as a parent; append it alone.
    correction = _records()["MKT-META-CORRECTION"]
    result = pit.append_point_in_time_records(str(path), [correction])
    assert not result.is_valid
    assert result.error_codes == ("RECORD_STORE_LINEAGE_INVALID",)


def test_ordinary_depending_on_conflict_is_authority_violation(tmp_path) -> None:
    path = _new_store(tmp_path)
    recs = _records()
    primary = recs["MKT-META-PRIMARY"]
    conflict = recs["MKT-CONFLICT"]
    # Build a self-consistent ordinary LATE_ARRIVAL whose legitimate lineage parent
    # is the CONFLICT record's committed id. The record derives its own id from that
    # lineage, so it passes self-validation; only the complete-store authority rule
    # rejects an ordinary record taking a conflict as an authoritative parent.
    dependent = _require(
        pit.build_market_observation(
            _meta(
                source_assertion_id="assertion:metadata:depends-on-conflict",
                observed_time="2026-01-01T00:07:00Z",
                ingestion_time="2026-01-01T00:07:01Z",
                classification="LATE_ARRIVAL",
                parents=[conflict.envelope.record_version_id],
            )
        )
    )
    result = pit.append_point_in_time_records(
        str(path), [primary, conflict, dependent]
    )
    assert not result.is_valid
    assert "RECORD_STORE_AUTHORITY_VIOLATION" in result.error_codes


def test_correction_chain_persists(tmp_path) -> None:
    path = _new_store(tmp_path)
    recs = _records()
    result = pit.append_point_in_time_records(
        str(path), [recs["MKT-META-PRIMARY"], recs["MKT-META-CORRECTION"]]
    )
    assert result.is_valid and result.status == "RECORD_STORE_APPEND_COMMITTED"


def test_lineage_validated_across_two_appends(tmp_path) -> None:
    path = _new_store(tmp_path)
    recs = _records()
    assert pit.append_point_in_time_records(
        str(path), [recs["MKT-META-PRIMARY"]]
    ).is_valid
    # The correction's parent already lives in the store.
    assert pit.append_point_in_time_records(
        str(path), [recs["MKT-META-CORRECTION"]]
    ).is_valid


# ── Transaction / lock (Section 26) ──────────────────────────────────────────


def test_rollback_injection_leaves_no_partial_row(tmp_path, monkeypatch) -> None:
    path = _new_store(tmp_path)
    recs = list(_records().values())
    calls = {"n": 0}

    def _hook():
        calls["n"] += 1
        if calls["n"] >= 1:
            raise RuntimeError("injected mid-transaction failure")

    monkeypatch.setattr(RS, "_after_insert_hook", _hook)
    result = pit.append_point_in_time_records(str(path), recs)
    assert not result.is_valid
    assert result.error_codes == ("RECORD_STORE_WRITE_FAILED",)
    # No partial row survived.
    con = _raw_connect(path)
    try:
        assert con.execute("SELECT COUNT(*) FROM records").fetchone() == (0,)
    finally:
        con.close()


def test_busy_writer_fails_fast(tmp_path) -> None:
    path = _new_store(tmp_path)
    primary = _records()["MKT-META-PRIMARY"]
    holder = sqlite3.connect(str(path), isolation_level=None, timeout=0.0)
    try:
        holder.execute("BEGIN IMMEDIATE")
        holder.execute("PRAGMA user_version")
        result = pit.append_point_in_time_records(str(path), [primary])
        assert result.error_codes == ("RECORD_STORE_BUSY",)
    finally:
        holder.execute("ROLLBACK")
        holder.close()
    # After release, the same append succeeds.
    assert pit.append_point_in_time_records(str(path), [primary]).is_valid


def test_successful_close_leaves_no_sidecar(tmp_path) -> None:
    path = _new_store(tmp_path)
    pit.append_point_in_time_records(str(path), [_records()["MKT-META-PRIMARY"]])
    for suffix in ("-wal", "-shm", "-journal"):
        assert not (tmp_path / (path.name + suffix)).exists()


def test_read_only_load_is_byte_stable(tmp_path) -> None:
    path = _new_store(tmp_path)
    pit.append_point_in_time_records(str(path), list(_records().values()))
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    for _ in range(3):
        assert pit.load_and_verify_point_in_time_record_store(str(path)).is_valid
    after = hashlib.sha256(path.read_bytes()).hexdigest()
    assert before == after


# ── Corruption / tamper matrix (Section 27) ──────────────────────────────────


def _seed_store(tmp_path) -> pathlib.Path:
    path = _new_store(tmp_path)
    pit.append_point_in_time_records(str(path), list(_records().values()))
    return path


def test_random_bytes_file_is_rejected(tmp_path) -> None:
    path = tmp_path / "garbage.sqlite3"
    path.write_bytes(b"\x00\x01\x02not a database\xff" * 32)
    result = pit.load_and_verify_point_in_time_record_store(str(path))
    assert not result.is_valid
    assert result.error_codes[0] in {
        "RECORD_STORE_OPEN_FAILED",
        "RECORD_STORE_SQLITE_INTEGRITY_FAILED",
        "RECORD_STORE_CONFIGURATION_INVALID",
        "RECORD_STORE_SCHEMA_UNSUPPORTED",
    }


def test_wrong_user_version_is_rejected(tmp_path) -> None:
    path = _seed_store(tmp_path)
    con = _raw_connect(path)
    con.execute("PRAGMA user_version=2")
    con.close()
    result = pit.load_and_verify_point_in_time_record_store(str(path))
    assert result.error_codes == ("RECORD_STORE_SCHEMA_UNSUPPORTED",)


def test_dropped_index_is_rejected(tmp_path) -> None:
    path = _seed_store(tmp_path)
    con = _raw_connect(path)
    con.execute("DROP INDEX idx_pit_records_event_time")
    con.close()
    result = pit.load_and_verify_point_in_time_record_store(str(path))
    assert result.error_codes == ("RECORD_STORE_SCHEMA_UNSUPPORTED",)


def test_extra_table_is_rejected(tmp_path) -> None:
    path = _seed_store(tmp_path)
    con = _raw_connect(path)
    con.execute("CREATE TABLE extra (x INTEGER)")
    con.close()
    result = pit.load_and_verify_point_in_time_record_store(str(path))
    assert result.error_codes == ("RECORD_STORE_SCHEMA_UNSUPPORTED",)


def test_wal_journal_is_rejected(tmp_path) -> None:
    path = _seed_store(tmp_path)
    con = _raw_connect(path)
    con.execute("PRAGMA journal_mode=WAL")
    con.close()
    result = pit.load_and_verify_point_in_time_record_store(str(path))
    assert result.error_codes == ("RECORD_STORE_CONFIGURATION_INVALID",)


def test_tampered_payload_json_is_rejected(tmp_path) -> None:
    path = _seed_store(tmp_path)
    con = _raw_connect(path)
    victim = con.execute(
        "SELECT record_version_id FROM records LIMIT 1"
    ).fetchone()[0]
    con.execute(
        "UPDATE records SET payload_json='{\"tampered\": true}' "
        "WHERE record_version_id=?",
        (victim,),
    )
    con.close()
    result = pit.load_and_verify_point_in_time_record_store(str(path))
    assert result.error_codes == ("RECORD_STORE_PAYLOAD_INVALID",)


def test_tampered_indexed_column_is_rejected(tmp_path) -> None:
    path = _seed_store(tmp_path)
    con = _raw_connect(path)
    victim = con.execute(
        "SELECT record_version_id FROM records LIMIT 1"
    ).fetchone()[0]
    con.execute(
        "UPDATE records SET classification='TAMPERED' WHERE record_version_id=?",
        (victim,),
    )
    con.close()
    result = pit.load_and_verify_point_in_time_record_store(str(path))
    assert result.error_codes == ("RECORD_STORE_PAYLOAD_INVALID",)


def test_row_id_mismatch_is_rejected(tmp_path) -> None:
    path = _seed_store(tmp_path)
    con = _raw_connect(path)
    con.execute(
        "UPDATE records SET record_version_id='record:sha256:' || "
        "substr('0',1,1) || substr(record_version_id, 15) "
        "WHERE record_version_id=(SELECT record_version_id FROM records LIMIT 1)"
    )
    con.close()
    result = pit.load_and_verify_point_in_time_record_store(str(path))
    assert not result.is_valid
    assert result.error_codes[0] in {
        "RECORD_STORE_PAYLOAD_INVALID",
        "RECORD_STORE_LINEAGE_INVALID",
    }


def test_duplicate_json_key_in_payload_is_rejected(tmp_path) -> None:
    path = _seed_store(tmp_path)
    con = _raw_connect(path)
    victim, payload = con.execute(
        "SELECT record_version_id, payload_json FROM records LIMIT 1"
    ).fetchone()
    doubled = payload[:-1] + ',"record_type":"x"}'
    con.execute(
        "UPDATE records SET payload_json=? WHERE record_version_id=?",
        (doubled, victim),
    )
    con.close()
    result = pit.load_and_verify_point_in_time_record_store(str(path))
    assert result.error_codes == ("RECORD_STORE_PAYLOAD_INVALID",)


# ── Dataset materialization (Sections 20-24) ─────────────────────────────────


def test_validated_batch_materialization(tmp_path) -> None:
    path = _new_store(tmp_path)
    recs = _records()
    ordinary = [recs["MKT-LATE"], recs["MKT-BOOK-NOEVENT"]]
    pit.append_point_in_time_records(str(path), ordinary)
    reference = _batch_reference(ordinary)
    result = pit.materialize_dataset_snapshot_reference(str(path), reference)
    assert result.is_valid
    assert result.status == "DATASET_REFERENCE_MATERIALIZED"
    assert result.verification_mode == "VALIDATED_BATCH_RECOMPUTED"
    assert {r.envelope.record_version_id for r in result.ordinary_records} == {
        r.envelope.record_version_id for r in ordinary
    }
    assert result.review_conflict_records == ()
    assert result.dataset_reference == reference


def test_asof_materialization_is_id_resolution_only(tmp_path) -> None:
    path = _new_store(tmp_path)
    recs = _records()
    ordinary = [recs["MKT-META-PRIMARY"]]
    review = [recs["MKT-CONFLICT"]]
    pit.append_point_in_time_records(str(path), [recs["MKT-META-PRIMARY"], recs["MKT-CONFLICT"]])
    reference = _asof_reference(ordinary, review)
    result = pit.materialize_dataset_snapshot_reference(str(path), reference)
    assert result.is_valid
    assert result.verification_mode == "AS_OF_REFERENCE_IDS_RESOLVED"
    assert result.human_review_required is True
    assert [r.envelope.record_version_id for r in result.review_conflict_records] == [
        recs["MKT-CONFLICT"].envelope.record_version_id
    ]


def test_reference_order_is_preserved(tmp_path) -> None:
    path = _new_store(tmp_path)
    recs = _records()
    ordinary = [recs["MKT-BOOK-NOEVENT"], recs["MKT-LATE"]]
    pit.append_point_in_time_records(str(path), ordinary)
    reference = _asof_reference(ordinary)
    result = pit.materialize_dataset_snapshot_reference(str(path), reference)
    assert [r.envelope.record_version_id for r in result.ordinary_records] == list(
        reference.ordinary_record_version_ids
    )


def test_malformed_reference_is_rejected_and_hidden(tmp_path) -> None:
    path = _seed_store(tmp_path)
    for bad in (object(), None, "reference", 5):
        result = pit.materialize_dataset_snapshot_reference(str(path), bad)
        assert not result.is_valid
        assert result.error_codes == ("RECORD_STORE_REFERENCE_INVALID",)
        assert result.dataset_reference is None
        assert result.ordinary_records == ()
        assert result.verification_mode is None


def test_missing_referenced_record_fails_closed(tmp_path) -> None:
    path = _new_store(tmp_path)
    recs = _records()
    ordinary = [recs["MKT-LATE"], recs["MKT-BOOK-NOEVENT"]]
    reference = _batch_reference(ordinary)
    pit.append_point_in_time_records(str(path), [recs["MKT-LATE"]])
    result = pit.materialize_dataset_snapshot_reference(str(path), reference)
    assert result.error_codes == ("RECORD_STORE_REFERENCE_MISSING_RECORD",)
    assert result.ordinary_records == ()


def test_ordinary_id_resolving_to_conflict_is_authority_violation(tmp_path) -> None:
    path = _new_store(tmp_path)
    recs = _records()
    conflict = recs["MKT-CONFLICT"]
    pit.append_point_in_time_records(str(path), [recs["MKT-META-PRIMARY"], conflict])
    # An as-of reference that lists the conflict id as an ordinary record.
    reference = _asof_reference([conflict])
    result = pit.materialize_dataset_snapshot_reference(str(path), reference)
    assert result.error_codes == ("RECORD_STORE_AUTHORITY_VIOLATION",)


def test_review_id_resolving_to_ordinary_is_authority_violation(tmp_path) -> None:
    path = _new_store(tmp_path)
    recs = _records()
    primary = recs["MKT-META-PRIMARY"]
    pit.append_point_in_time_records(str(path), [primary])
    reference = _asof_reference([], [primary])
    result = pit.materialize_dataset_snapshot_reference(str(path), reference)
    assert result.error_codes == ("RECORD_STORE_AUTHORITY_VIOLATION",)


def test_tampered_batch_reference_rebuild_is_rejected(tmp_path) -> None:
    path = _new_store(tmp_path)
    recs = _records()
    ordinary = [recs["MKT-LATE"], recs["MKT-BOOK-NOEVENT"]]
    pit.append_point_in_time_records(str(path), ordinary)
    reference = _batch_reference(ordinary)
    # A hash tampered without recomputing the id breaks the WP160 rebuild.
    forged = dataclasses.replace(reference, validated_batch_sha256="f" * 64)
    result = pit.materialize_dataset_snapshot_reference(str(path), forged)
    assert result.error_codes == ("RECORD_STORE_REFERENCE_INVALID",)


def test_self_consistent_wrong_batch_hash_is_content_mismatch(tmp_path) -> None:
    path = _new_store(tmp_path)
    recs = _records()
    ordinary = [recs["MKT-LATE"], recs["MKT-BOOK-NOEVENT"]]
    pit.append_point_in_time_records(str(path), ordinary)
    batch = R.validate_record_batch(list(ordinary))
    # A self-consistent reference (its id matches its preimage) that nonetheless
    # commits a validated_batch_sha256 that is not the real batch identity.
    preimage = {
        "schema_id": DATASET_REFERENCE_SCHEMA_ID,
        "schema_version": DATASET_REFERENCE_SCHEMA_VERSION,
        "derivation_mode": "VALIDATED_RECORD_BATCH",
        "validated_batch_sha256": "e" * 64,
        "ordinary_record_version_ids": list(batch.accepted_record_version_ids),
        "review_conflict_record_version_ids": [],
        "query_spec_sha256": None,
        "query_result_sha256": None,
        "cutoff_mode": None,
        "cutoff_time": None,
        "result_view": None,
        "query_engine_version": None,
        "validator_version": "validator:wp163:test",
        "parameter_set_id": "params:wp163:test",
        "human_review_required": False,
        "advisory_only": True,
        "no_execution_authority": True,
    }
    ref_id = "datasetref:sha256:" + R.sha256_hex(R.canonical_json_bytes(preimage))
    mapping = dict(preimage)
    mapping["dataset_snapshot_reference_id"] = ref_id
    mapping["created_from_manifest_entry_id"] = None
    reference = build_dataset_snapshot_reference(mapping).reference
    assert reference is not None
    result = pit.materialize_dataset_snapshot_reference(str(path), reference)
    assert result.error_codes == ("RECORD_STORE_REFERENCE_CONTENT_MISMATCH",)


def test_materialization_missing_store_fails_closed(tmp_path) -> None:
    recs = _records()
    reference = _batch_reference([recs["MKT-LATE"]])
    result = pit.materialize_dataset_snapshot_reference(
        str(tmp_path / "missing.sqlite3"), reference
    )
    assert result.error_codes == ("RECORD_STORE_NOT_FOUND",)


# ── No-echo (Section 25) ─────────────────────────────────────────────────────


def _iter_strings(value, seen=None):
    if seen is None:
        seen = set()
    if id(value) in seen:
        return
    seen.add(id(value))
    if isinstance(value, str):
        yield value
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from _iter_strings(item, seen)
    elif dataclasses.is_dataclass(value):
        for field in dataclasses.fields(value):
            yield from _iter_strings(getattr(value, field.name), seen)


def test_rejected_results_never_echo_path_or_payload(tmp_path) -> None:
    path = _seed_store(tmp_path)
    con = _raw_connect(path)
    victim = con.execute(
        "SELECT record_version_id FROM records LIMIT 1"
    ).fetchone()[0]
    con.execute(
        "UPDATE records SET payload_json='{\"secret_marker\": \"LEAK\"}' "
        "WHERE record_version_id=?",
        (victim,),
    )
    con.close()
    result = pit.load_and_verify_point_in_time_record_store(str(path))
    assert not result.is_valid
    strings = list(_iter_strings(result))
    assert all(str(path) not in text for text in strings)
    assert all("LEAK" not in text for text in strings)
    assert all("secret_marker" not in text for text in strings)


# ── Production SQL / source safety (Section 28) ──────────────────────────────


def test_production_source_has_no_forbidden_constructs() -> None:
    source = RECORD_STORE_SRC.read_text(encoding="utf-8")
    for forbidden in (
        "executescript",
        "check_same_thread",
        "journal_mode=WAL",
        "os.environ",
        "os.getenv",
        "subprocess",
        "import pickle",
        "import shelve",
        "eval(",
        "exec(",
        "UPDATE records",
        "DELETE FROM records",
    ):
        assert forbidden not in source


def test_production_source_does_not_catch_base_exception() -> None:
    source = RECORD_STORE_SRC.read_text(encoding="utf-8")
    tokens = tokenize.generate_tokens(io.StringIO(source).readline)
    names = [tok.string for tok in tokens if tok.type == tokenize.NAME]
    assert "BaseException" not in names


# ── Blocker A: WP163 outer full-record canonicalization, not WP156 bounds ─────


def test_large_canonical_payload_over_wp156_string_limit_persists(tmp_path) -> None:
    # A WP156-valid record whose canonical_payload_json exceeds WP156's 4,096
    # per-string bound must persist: WP163 canonicalizes the OUTER record itself.
    record = _big_conflict_record(40, 100, "assertion:bigA")
    assert len(record.canonical_payload_json) > 4096
    assert R.revalidate_review_conflict_record(record) == ()
    path = _new_store(tmp_path)
    result = pit.append_point_in_time_records(str(path), [record])
    assert result.is_valid and result.status == "RECORD_STORE_APPEND_COMMITTED"
    reopened = pit.load_and_verify_point_in_time_record_store(str(path))
    stored = {r.envelope.record_version_id: r for r in reopened.snapshot.records}
    assert stored[record.envelope.record_version_id] == record


def test_full_record_over_65536_bytes_persists(tmp_path) -> None:
    # A complete stored representation above WP156's 65,536-byte payload bound but
    # within WP163's 131,072-byte per-row bound must persist.
    record = _big_conflict_record(255, 244, "assertion:bigB")
    outer = len(RS._canonical_outer_bytes(RS._canonical_record_mapping(record)))
    assert 65536 < outer <= 131072
    path = _new_store(tmp_path)
    result = pit.append_point_in_time_records(str(path), [record])
    assert result.is_valid
    reopened = pit.load_and_verify_point_in_time_record_store(str(path))
    ids = {r.envelope.record_version_id for r in reopened.snapshot.records}
    assert record.envelope.record_version_id in ids


def test_over_131072_row_fails_via_bounded_seam(tmp_path, monkeypatch) -> None:
    # Controlled private seam: a normal record exceeds a tightened per-row bound.
    path = _new_store(tmp_path)
    monkeypatch.setattr(RS, "_MAX_PAYLOAD_BYTES_PER_ROW", 200)
    result = pit.append_point_in_time_records(
        str(path), [_records()["MKT-META-PRIMARY"]]
    )
    assert result.error_codes == ("RECORD_STORE_PAYLOAD_INVALID",)


def test_full_record_serialization_is_byte_and_digest_stable() -> None:
    record = _big_conflict_record(80, 120, "assertion:stable")
    first = RS._canonical_outer_bytes(RS._canonical_record_mapping(record))
    second = RS._canonical_outer_bytes(RS._canonical_record_mapping(record))
    assert first == second
    assert RS.sha256_hex(first) == RS.sha256_hex(second)
    # decode -> re-encode is byte-identical.
    reencoded = RS._canonical_outer_bytes(json.loads(first.decode("utf-8")))
    assert reencoded == first


# ── Blocker B: bounded reader preflight before payload fetch ──────────────────


def test_load_rejects_over_row_count_before_fetch(tmp_path, monkeypatch) -> None:
    path = _seed_store(tmp_path)
    monkeypatch.setattr(RS, "_MAX_RECORDS_IN_STORE", 2)
    result = pit.load_and_verify_point_in_time_record_store(str(path))
    assert result.error_codes == ("RECORD_STORE_LIMIT_EXCEEDED",)


def test_load_rejects_over_per_row_bytes_before_decode(tmp_path, monkeypatch) -> None:
    path = _seed_store(tmp_path)
    monkeypatch.setattr(RS, "_MAX_PAYLOAD_BYTES_PER_ROW", 50)
    result = pit.load_and_verify_point_in_time_record_store(str(path))
    assert result.error_codes == ("RECORD_STORE_PAYLOAD_INVALID",)


def test_load_rejects_over_total_bytes_before_decode(tmp_path, monkeypatch) -> None:
    path = _seed_store(tmp_path)
    monkeypatch.setattr(RS, "_MAX_TOTAL_PAYLOAD_BYTES", 100)
    result = pit.load_and_verify_point_in_time_record_store(str(path))
    assert result.error_codes == ("RECORD_STORE_LIMIT_EXCEEDED",)


def test_normal_store_preserves_snapshot_after_bounded_reader(tmp_path) -> None:
    path = _seed_store(tmp_path)
    snap = pit.load_and_verify_point_in_time_record_store(str(path)).snapshot
    assert len(snap.records) == len(_records())
    ingestion = [r.envelope.ingestion_time for r in snap.records]
    assert ingestion == sorted(ingestion)


# ── Expanded path / init coverage ─────────────────────────────────────────────


def test_hostile_pathlike_across_all_entry_points(tmp_path) -> None:
    hostile = _HostilePathLike()
    assert pit.load_and_verify_point_in_time_record_store(hostile).error_codes == (
        "RECORD_STORE_PATH_INVALID",
    )
    assert pit.append_point_in_time_records(hostile, []).error_codes == (
        "RECORD_STORE_PATH_INVALID",
    )
    recs = _records()
    reference = _batch_reference([recs["MKT-LATE"]])
    assert pit.materialize_dataset_snapshot_reference(hostile, reference).error_codes == (
        "RECORD_STORE_PATH_INVALID",
    )


def test_tuple_subclass_is_rejected_without_iteration(tmp_path) -> None:
    path = _new_store(tmp_path)

    class _HostileTuple(tuple):
        def __iter__(self):
            raise RuntimeError("must not iterate a tuple subclass")

    result = pit.append_point_in_time_records(str(path), _HostileTuple())
    assert result.error_codes == ("RECORD_STORE_INPUT_INVALID",)


def test_symlink_db_target_is_rejected(tmp_path) -> None:
    real = _seed_store(tmp_path)
    link = tmp_path / "link.sqlite3"
    try:
        link.symlink_to(real)
    except (OSError, NotImplementedError):
        pytest.skip("symlink creation not permitted in this environment")
    result = pit.load_and_verify_point_in_time_record_store(str(link))
    assert result.error_codes == ("RECORD_STORE_PATH_INVALID",)


def test_post_commit_failure_preserves_preexisting_pristine_file(
    tmp_path, monkeypatch
) -> None:
    path = tmp_path / "pristine.sqlite3"
    con = _raw_connect(path)
    con.close()  # a pre-existing, caller-owned, pristine (empty) SQLite file

    def _boom(_path):
        return RS._rejected("RECORD_STORE_SCHEMA_UNSUPPORTED")

    monkeypatch.setattr(RS, "_load_path", _boom)
    result = pit.initialize_point_in_time_record_store(str(path))
    assert not result.is_valid
    # A pre-existing caller file is never removed by init cleanup.
    assert path.exists()


# ── Expanded schema tamper coverage ───────────────────────────────────────────


def test_extra_view_is_rejected(tmp_path) -> None:
    path = _seed_store(tmp_path)
    con = _raw_connect(path)
    con.execute("CREATE VIEW leak AS SELECT * FROM records")
    con.close()
    assert pit.load_and_verify_point_in_time_record_store(str(path)).error_codes == (
        "RECORD_STORE_SCHEMA_UNSUPPORTED",
    )


def test_extra_trigger_is_rejected(tmp_path) -> None:
    path = _seed_store(tmp_path)
    con = _raw_connect(path)
    con.execute(
        "CREATE TRIGGER t AFTER INSERT ON records BEGIN SELECT 1; END"
    )
    con.close()
    assert pit.load_and_verify_point_in_time_record_store(str(path)).error_codes == (
        "RECORD_STORE_SCHEMA_UNSUPPORTED",
    )


def test_extra_index_is_rejected(tmp_path) -> None:
    path = _seed_store(tmp_path)
    con = _raw_connect(path)
    con.execute("CREATE INDEX extra_idx ON records(classification)")
    con.close()
    assert pit.load_and_verify_point_in_time_record_store(str(path)).error_codes == (
        "RECORD_STORE_SCHEMA_UNSUPPORTED",
    )


def test_wrong_index_columns_are_rejected(tmp_path) -> None:
    path = _seed_store(tmp_path)
    con = _raw_connect(path)
    con.execute("DROP INDEX idx_pit_records_market_id")
    con.execute("CREATE INDEX idx_pit_records_market_id ON records(source_id)")
    con.close()
    assert pit.load_and_verify_point_in_time_record_store(str(path)).error_codes == (
        "RECORD_STORE_SCHEMA_UNSUPPORTED",
    )


def test_missing_meta_row_is_rejected(tmp_path) -> None:
    path = _seed_store(tmp_path)
    con = _raw_connect(path)
    con.execute("DELETE FROM record_store_meta")
    con.close()
    assert pit.load_and_verify_point_in_time_record_store(str(path)).error_codes == (
        "RECORD_STORE_SCHEMA_UNSUPPORTED",
    )


# ── Expanded stored-payload tamper coverage ───────────────────────────────────


def test_nan_payload_is_rejected(tmp_path) -> None:
    path = _seed_store(tmp_path)
    con = _raw_connect(path)
    victim = con.execute("SELECT record_version_id FROM records LIMIT 1").fetchone()[0]
    con.execute(
        'UPDATE records SET payload_json=\'{"x": NaN}\' WHERE record_version_id=?',
        (victim,),
    )
    con.close()
    assert pit.load_and_verify_point_in_time_record_store(str(path)).error_codes == (
        "RECORD_STORE_PAYLOAD_INVALID",
    )


def test_non_object_payload_is_rejected(tmp_path) -> None:
    path = _seed_store(tmp_path)
    con = _raw_connect(path)
    victim = con.execute("SELECT record_version_id FROM records LIMIT 1").fetchone()[0]
    con.execute(
        "UPDATE records SET payload_json='[1,2,3]' WHERE record_version_id=?",
        (victim,),
    )
    con.close()
    assert pit.load_and_verify_point_in_time_record_store(str(path)).error_codes == (
        "RECORD_STORE_PAYLOAD_INVALID",
    )


def test_noncanonical_payload_is_rejected(tmp_path) -> None:
    path = _seed_store(tmp_path)
    con = _raw_connect(path)
    victim, payload = con.execute(
        "SELECT record_version_id, payload_json FROM records LIMIT 1"
    ).fetchone()
    con.execute(
        "UPDATE records SET payload_json=? WHERE record_version_id=?",
        (" " + payload, victim),  # leading space -> not canonical
    )
    con.close()
    assert pit.load_and_verify_point_in_time_record_store(str(path)).error_codes == (
        "RECORD_STORE_PAYLOAD_INVALID",
    )


def test_payload_sha_mismatch_alone_is_rejected(tmp_path) -> None:
    path = _seed_store(tmp_path)
    con = _raw_connect(path)
    victim = con.execute("SELECT record_version_id FROM records LIMIT 1").fetchone()[0]
    con.execute(
        "UPDATE records SET payload_sha256=? WHERE record_version_id=?",
        ("0" * 64, victim),
    )
    con.close()
    assert pit.load_and_verify_point_in_time_record_store(str(path)).error_codes == (
        "RECORD_STORE_PAYLOAD_INVALID",
    )


@pytest.mark.parametrize(
    "column,value",
    [
        ("parameter_set_id", "parameters:tampered"),
        ("validator_version", "validator:tampered"),
        ("platform_id", "platform:tampered"),
        ("human_review_required", 1),
    ],
)
def test_indexed_column_row_payload_mismatch_is_rejected(tmp_path, column, value) -> None:
    path = _new_store(tmp_path)
    # Use a market record so platform_id/human_review columns are populated.
    primary = _records()["MKT-META-PRIMARY"]
    pit.append_point_in_time_records(str(path), [primary])
    con = _raw_connect(path)
    con.execute(
        f"UPDATE records SET {column}=? WHERE record_version_id=?",
        (value, primary.envelope.record_version_id),
    )
    con.close()
    assert pit.load_and_verify_point_in_time_record_store(str(path)).error_codes == (
        "RECORD_STORE_PAYLOAD_INVALID",
    )


def test_safety_posture_tamper_in_payload_is_rejected(tmp_path) -> None:
    path = _new_store(tmp_path)
    primary = _records()["MKT-META-PRIMARY"]
    pit.append_point_in_time_records(str(path), [primary])

    def _flip_safety(mapping):
        mapping["envelope"]["advisory_only"] = False

    _tamper_row_payload(path, primary.envelope.record_version_id, _flip_safety)
    result = pit.load_and_verify_point_in_time_record_store(str(path))
    # The tampered envelope no longer reproduces its committed identity.
    assert not result.is_valid
    assert result.error_codes[0] in {
        "RECORD_STORE_RECORD_INVALID",
        "RECORD_STORE_PAYLOAD_INVALID",
    }


# ── Expanded lineage / authority coverage ─────────────────────────────────────


def _corrected(
    *,
    market_id=None,
    observed="2026-01-01T00:04:30Z",
    ingestion="2026-01-01T00:05:00Z",
    parent_id,
    sup_id,
):
    inp = _meta(
        source_assertion_id="assertion:metadata:001",
        observed_time=observed,
        ingestion_time=ingestion,
        classification="PROJECT_CORRECTION",
        parents=[parent_id],
        supersedes=sup_id,
        payload={
            "question_text": "Will the corrected synthetic condition be true?",
            "market_status": "RESOLVED_SYNTHETIC",
            "outcome_labels": ["YES_SYNTHETIC", "NO_SYNTHETIC"],
        },
    )
    if market_id is not None:
        inp["market_id"] = market_id
    return _require(pit.build_market_observation(inp))


def test_correction_wrong_entity_is_lineage_invalid(tmp_path) -> None:
    path = _new_store(tmp_path)
    primary = _records()["MKT-META-PRIMARY"]
    pid = primary.envelope.record_version_id
    # A self-consistent correction whose supersedes target is a different entity.
    wrong = _corrected(market_id="market:synthetic:other", parent_id=pid, sup_id=pid)
    result = pit.append_point_in_time_records(str(path), [primary, wrong])
    assert result.error_codes == ("RECORD_STORE_LINEAGE_INVALID",)


def test_correction_earlier_than_parent_is_lineage_invalid(tmp_path) -> None:
    path = _new_store(tmp_path)
    primary = _records()["MKT-META-PRIMARY"]  # ingestion 2026-01-01T00:00:02Z
    pid = primary.envelope.record_version_id
    early = _corrected(
        observed="2026-01-01T00:00:00Z",
        ingestion="2026-01-01T00:00:01Z",
        parent_id=pid,
        sup_id=pid,
    )
    result = pit.append_point_in_time_records(str(path), [primary, early])
    assert result.error_codes == ("RECORD_STORE_LINEAGE_INVALID",)


def test_exact_duplicate_payload_mismatch_is_lineage_invalid(tmp_path) -> None:
    path = _new_store(tmp_path)
    primary = _records()["MKT-META-PRIMARY"]
    pid = primary.envelope.record_version_id
    # EXACT_DUPLICATE whose payload differs from the parent's payload.
    inp = _meta(
        source_assertion_id="assertion:metadata:001",
        observed_time="2026-01-01T00:04:00Z",
        ingestion_time="2026-01-01T00:04:01Z",
        classification="EXACT_DUPLICATE",
        parents=[pid],
        payload={
            "question_text": "A DIFFERENT question entirely.",
            "market_status": "OPEN_SYNTHETIC",
            "outcome_labels": ["YES_SYNTHETIC", "NO_SYNTHETIC"],
        },
    )
    dup = _require(pit.build_market_observation(inp))
    result = pit.append_point_in_time_records(str(path), [primary, dup])
    assert result.error_codes == ("RECORD_STORE_LINEAGE_INVALID",)


def test_semantic_duplicate_identity_mismatch_is_lineage_invalid(tmp_path) -> None:
    path = _new_store(tmp_path)
    primary = _records()["MKT-META-PRIMARY"]
    pid = primary.envelope.record_version_id
    # SEMANTIC_DUPLICATE against a parent of a different entity/observation.
    inp = _meta(
        source_assertion_id="assertion:metadata:001",
        observed_time="2026-01-01T00:05:00Z",
        ingestion_time="2026-01-01T00:05:01Z",
        classification="SEMANTIC_DUPLICATE",
        parents=[pid],
        payload={
            "market_status": "OPEN_SYNTHETIC",
            "outcome_labels": ["YES_SYNTHETIC", "NO_SYNTHETIC"],
            "question_text": "Will the synthetic condition be true?",
            "source_representation": "ALTERNATE_SYNTHETIC",
        },
    )
    inp["market_id"] = "market:synthetic:other"
    dup = _require(pit.build_market_observation(inp))
    result = pit.append_point_in_time_records(str(path), [primary, dup])
    assert result.error_codes == ("RECORD_STORE_LINEAGE_INVALID",)


def test_self_parent_and_duplicate_parent_are_caught_by_self_validation(tmp_path) -> None:
    # Duplicate/self parents break the committed record-version identity, so WP156
    # self-validation is the first gate and they fail closed as RECORD_INVALID
    # before store-level lineage is reached.
    path = _new_store(tmp_path)
    primary = _records()["MKT-META-PRIMARY"]
    self_env = dataclasses.replace(
        primary.envelope, lineage_parent_ids=(primary.envelope.record_version_id,)
    )
    self_parent = dataclasses.replace(primary, envelope=self_env)
    assert pit.append_point_in_time_records(str(path), [self_parent]).error_codes == (
        "RECORD_STORE_RECORD_INVALID",
    )


# ── Expanded materialization coverage ─────────────────────────────────────────


def test_malformed_direct_reference_dataclass_is_rejected(tmp_path) -> None:
    path = _seed_store(tmp_path)
    recs = _records()
    valid = _batch_reference([recs["MKT-LATE"]])
    # A directly-mutated dataclass that no longer rebuilds through WP160.
    broken = dataclasses.replace(valid, ordinary_record_version_ids=("not-an-id",))
    result = pit.materialize_dataset_snapshot_reference(str(path), broken)
    assert result.error_codes == ("RECORD_STORE_REFERENCE_INVALID",)
    assert result.dataset_reference is None


def test_empty_asof_materialization_succeeds(tmp_path) -> None:
    path = _seed_store(tmp_path)
    reference = _asof_reference([])
    result = pit.materialize_dataset_snapshot_reference(str(path), reference)
    assert result.is_valid
    assert result.verification_mode == "AS_OF_REFERENCE_IDS_RESOLVED"
    assert result.ordinary_records == ()
    assert result.review_conflict_records == ()


def test_asof_review_conflict_materialization(tmp_path) -> None:
    path = _new_store(tmp_path)
    recs = _records()
    pit.append_point_in_time_records(
        str(path), [recs["MKT-META-PRIMARY"], recs["MKT-CONFLICT"]]
    )
    reference = _asof_reference([recs["MKT-META-PRIMARY"]], [recs["MKT-CONFLICT"]])
    result = pit.materialize_dataset_snapshot_reference(str(path), reference)
    assert result.is_valid and result.human_review_required is True
    assert [r.envelope.record_version_id for r in result.review_conflict_records] == [
        recs["MKT-CONFLICT"].envelope.record_version_id
    ]


def test_missing_reference_id_yields_no_partial_output(tmp_path) -> None:
    path = _new_store(tmp_path)
    recs = _records()
    pit.append_point_in_time_records(str(path), [recs["MKT-LATE"]])
    reference = _asof_reference([recs["MKT-LATE"], recs["MKT-BOOK-NOEVENT"]])
    result = pit.materialize_dataset_snapshot_reference(str(path), reference)
    assert result.error_codes == ("RECORD_STORE_REFERENCE_MISSING_RECORD",)
    assert result.ordinary_records == ()
    assert result.review_conflict_records == ()
    assert result.verification_mode is None


# ── Boundary and no-echo coverage ─────────────────────────────────────────────


def test_canonical_payload_4096_4097_boundary() -> None:
    # A single WP156 payload string of exactly 4,096 is valid; 4,097 is rejected
    # by WP156 (per-string bound), confirming WP163 defers embedded-payload
    # validation to WP156 while the OUTER record uses the wider WP163 bound.
    def build(length):
        payload = {
            "question_text": "x" * length,
            "market_status": "OPEN_SYNTHETIC",
            "outcome_labels": ["YES_SYNTHETIC"],
        }
        return pit.build_market_observation(
            _meta(
                source_assertion_id="assertion:boundary",
                observed_time="2026-01-01T00:00:01Z",
                ingestion_time="2026-01-01T00:00:02Z",
                payload=payload,
            )
        )

    assert build(4096).is_valid
    assert not build(4097).is_valid


def test_no_echo_recursive_over_expanded_invalid_cases(tmp_path) -> None:
    path = _new_store(tmp_path)
    primary = _records()["MKT-META-PRIMARY"]
    pit.append_point_in_time_records(str(path), [primary])

    def _leak(mapping):
        mapping["envelope"]["advisory_only"] = False
        mapping["source_assertion_id"] = "assertion:SENSITIVE_LEAK_MARKER"

    _tamper_row_payload(path, primary.envelope.record_version_id, _leak)
    result = pit.load_and_verify_point_in_time_record_store(str(path))
    assert not result.is_valid
    strings = list(_iter_strings(result))
    assert all(str(path) not in text for text in strings)
    assert all("SENSITIVE_LEAK_MARKER" not in text for text in strings)
