"""WP161 bounded SQLite manifest-store tests.

All files are created below pytest ``tmp_path``.  The tests exercise the
public fail-closed boundary and use direct stdlib sqlite3 only to construct
independent corruption cases.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError, fields, replace
import hashlib
import inspect
import json
import os
from pathlib import Path
import re
import sqlite3

import pytest

import src.data_layer.point_in_time_market_research as pit
from src.data_layer.point_in_time_market_research import manifest_reference as MR
from src.data_layer.point_in_time_market_research import manifest_store as S


def _hex(seed: str) -> str:
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()


def _record_id(seed: str) -> str:
    return "record:sha256:" + _hex(seed)


def _reference(seed: str = "a", *, review: bool = False) -> MR.DatasetSnapshotReference:
    ordinary = [] if review else [_record_id(seed)]
    conflicts = [_record_id(seed)] if review else []
    data = {
        "schema_id": MR.DATASET_REFERENCE_SCHEMA_ID,
        "schema_version": MR.DATASET_REFERENCE_SCHEMA_VERSION,
        "dataset_snapshot_reference_id": "PENDING",
        "derivation_mode": "VALIDATED_RECORD_BATCH",
        "validated_batch_sha256": _hex("batch-" + seed),
        "ordinary_record_version_ids": ordinary,
        "review_conflict_record_version_ids": conflicts,
        "query_spec_sha256": None,
        "query_result_sha256": None,
        "cutoff_mode": None,
        "cutoff_time": None,
        "result_view": None,
        "query_engine_version": None,
        "validator_version": "validator@wp161-test",
        "parameter_set_id": "paramset:wp161-test",
        "created_from_manifest_entry_id": None,
        "human_review_required": review,
        "advisory_only": True,
        "no_execution_authority": True,
    }
    preimage = dict(data)
    preimage.pop("dataset_snapshot_reference_id")
    preimage.pop("created_from_manifest_entry_id")
    data["dataset_snapshot_reference_id"] = (
        "datasetref:sha256:" + pit.sha256_hex(pit.canonical_json_bytes(preimage))
    )
    result = MR.build_dataset_snapshot_reference(data)
    assert result.is_valid and result.reference is not None
    return result.reference


def _entry(
    reference: MR.DatasetSnapshotReference,
    *,
    sequence: int = 0,
    previous: str | None = None,
    manifest_id: str = "manifest:wp161-test",
) -> MR.ManifestEntry:
    minute, second = divmod(sequence, 60)
    data = {
        "schema_id": MR.MANIFEST_ENTRY_SCHEMA_ID,
        "schema_version": MR.MANIFEST_ENTRY_SCHEMA_VERSION,
        "manifest_entry_id": "PENDING",
        "manifest_id": manifest_id,
        "sequence_number": sequence,
        "previous_manifest_entry_id": previous,
        "entry_kind": "REGISTER_DATASET_SNAPSHOT_REFERENCE",
        "dataset_snapshot_reference_id": reference.dataset_snapshot_reference_id,
        "supersedes_manifest_entry_id": None,
        "reference_state": "ACTIVE_REFERENCE",
        "reason_code": "INITIAL_REGISTRATION",
        "effective_time": f"2026-08-10T00:{minute:02d}:{second:02d}Z",
        "parameter_set_id": "paramset:wp161-test",
        "human_review_required": reference.human_review_required,
        "advisory_only": True,
        "no_execution_authority": True,
    }
    preimage = dict(data)
    preimage.pop("manifest_entry_id")
    data["manifest_entry_id"] = (
        "manifestentry:sha256:" + pit.sha256_hex(pit.canonical_json_bytes(preimage))
    )
    result = MR.build_manifest_entry(data)
    assert result.is_valid and result.entry is not None
    return result.entry


def _valid_store(path: Path, *, entries: int = 1):
    init = S.initialize_manifest_store(path)
    assert init.is_valid
    references = tuple(_reference(str(index)) for index in range(entries))
    manifest_entries = []
    previous = None
    for index, reference in enumerate(references):
        entry = _entry(reference, sequence=index, previous=previous)
        manifest_entries.append(entry)
        previous = entry.manifest_entry_id
    result = S.append_manifest_store_batch(
        path,
        dataset_references=references,
        manifest_entries=tuple(manifest_entries),
    )
    assert result.is_valid
    return references, tuple(manifest_entries), result


def _assert_rejected(result: S.ManifestStoreResult, code: str) -> None:
    assert result == S.ManifestStoreResult(
        is_valid=False,
        status="STORE_REJECTED",
        error_codes=(code,),
        warning_codes=(),
        snapshot=None,
        inserted_dataset_reference_ids=(),
        inserted_manifest_entry_ids=(),
        idempotent_dataset_reference_ids=(),
        idempotent_manifest_entry_ids=(),
        advisory_only=True,
        no_execution_authority=True,
    )


def _result_strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, tuple):
        for item in value:
            yield from _result_strings(item)
    elif hasattr(value, "__dataclass_fields__"):
        for field in fields(value):
            yield from _result_strings(getattr(value, field.name))


def _assert_no_echo(result: S.ManifestStoreResult, *markers: str) -> None:
    rendered = " ".join(_result_strings(result))
    assert all(marker not in rendered for marker in markers)


def _db_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _replace_payload_field(path: Path, table: str, field: str, value: object) -> None:
    with sqlite3.connect(path) as connection:
        payload = json.loads(connection.execute(f"SELECT payload_json FROM {table}").fetchone()[0])
        payload[field] = value
        encoded = pit.canonical_json_bytes(payload).decode("utf-8")
        digest = pit.sha256_hex(encoded)
        connection.execute(
            f"UPDATE {table} SET payload_json=?, payload_sha256=?",
            (encoded, digest),
        )


def test_locked_public_surface_and_frozen_results() -> None:
    assert S.MANIFEST_STORE_LABEL == "POINT_IN_TIME_LOCAL_SQLITE_MANIFEST_STORE"
    assert S.MANIFEST_STORE_POSTURE == (
        "BOUNDED_LOCAL_SQLITE_TRANSACTIONAL_APPEND_AND_VERIFIED_READ"
    )
    assert S.MANIFEST_STORE_FORMAT_ID == "point-in-time-manifest-store"
    assert S.MANIFEST_STORE_SCHEMA_VERSION == 1
    assert S.MANIFEST_STORE_STATUSES == (
        "STORE_INITIALIZED", "STORE_ALREADY_INITIALIZED", "STORE_APPEND_COMMITTED",
        "STORE_APPEND_IDEMPOTENT", "STORE_LOADED_VERIFIED", "STORE_REJECTED",
    )
    assert S.MANIFEST_STORE_ERROR_CODES == (
        "STORE_PATH_INVALID", "STORE_NOT_FOUND", "STORE_OPEN_FAILED", "STORE_BUSY",
        "STORE_SCHEMA_UNSUPPORTED", "STORE_CONFIGURATION_INVALID",
        "STORE_SQLITE_INTEGRITY_FAILED", "STORE_INPUT_INVALID",
        "STORE_REFERENCE_INVALID", "STORE_ENTRY_INVALID", "STORE_PAYLOAD_INVALID",
        "STORE_DUPLICATE_CONFLICT", "STORE_LIMIT_EXCEEDED", "STORE_CHAIN_INVALID",
        "STORE_WRITE_FAILED",
    )
    assert tuple(field.name for field in fields(S.ManifestStoreSnapshot)) == (
        "dataset_references", "manifest_entries", "chain_validation",
        "human_review_required", "advisory_only", "no_execution_authority",
    )
    assert tuple(field.name for field in fields(S.ManifestStoreResult)) == (
        "is_valid", "status", "error_codes", "warning_codes", "snapshot",
        "inserted_dataset_reference_ids", "inserted_manifest_entry_ids",
        "idempotent_dataset_reference_ids", "idempotent_manifest_entry_ids",
        "advisory_only", "no_execution_authority",
    )
    result = S.initialize_manifest_store(None)
    with pytest.raises(FrozenInstanceError):
        result.status = "changed"  # type: ignore[misc]
    snapshot = S.ManifestStoreSnapshot((), (), None, False, True, True)
    with pytest.raises(FrozenInstanceError):
        snapshot.human_review_required = True  # type: ignore[misc]


def test_exact_package_exports_append_wp161_surface() -> None:
    expected = (
        "MANIFEST_STORE_LABEL", "MANIFEST_STORE_POSTURE", "MANIFEST_STORE_FORMAT_ID",
        "MANIFEST_STORE_SCHEMA_VERSION", "MANIFEST_STORE_STATUSES",
        "MANIFEST_STORE_ERROR_CODES", "ManifestStoreSnapshot", "ManifestStoreResult",
        "initialize_manifest_store", "append_manifest_store_batch",
        "load_and_verify_manifest_store",
    )
    # WP161 no longer needs to be the final package tail (a successor WP may
    # append its own surface after it); locate the WP161 block by its label and
    # assert the eleven-symbol run is exact and contiguous, still bound to the
    # manifest_store module objects.
    start = pit.__all__.index("MANIFEST_STORE_LABEL")
    assert pit.__all__[start:start + 11] == expected
    assert all(getattr(pit, name) is getattr(S, name) for name in expected)


@pytest.mark.parametrize("bad", [None, True, 1, 1.0, b"x", "", "   ", "bad\x00path"])
def test_r001_r030_invalid_path_matrix_is_closed(bad) -> None:
    _assert_rejected(S.initialize_manifest_store(bad), "STORE_PATH_INVALID")
    _assert_rejected(S.load_and_verify_manifest_store(bad), "STORE_PATH_INVALID")
    _assert_rejected(S.append_manifest_store_batch(bad), "STORE_PATH_INVALID")


@pytest.mark.parametrize("error_type", [RuntimeError, ValueError])
def test_r001_hostile_pathlike_exceptions_fail_closed_for_all_public_functions(
    error_type,
) -> None:
    marker = f"HOSTILE_PATHLIKE_{error_type.__name__}"

    class ExplodingPathLike(os.PathLike):
        def __fspath__(self):
            raise error_type(marker)

    hostile = ExplodingPathLike()
    results = (
        S.initialize_manifest_store(hostile),
        S.load_and_verify_manifest_store(hostile),
        S.append_manifest_store_batch(hostile),
    )
    for result in results:
        _assert_rejected(result, "STORE_PATH_INVALID")
        _assert_no_echo(result, marker, error_type.__name__)


def test_r001_hostile_str_subclass_strip_exception_fails_closed_for_all_public_functions(
) -> None:
    marker = "HOSTILE_STR_STRIP_RUNTIME_ERROR"

    class ExplodingStr(str):
        def strip(self, *args, **kwargs):
            raise RuntimeError(marker)

    hostile = ExplodingStr("store.sqlite")
    if type(os.fspath(hostile)) is not ExplodingStr:
        pytest.skip("os.fspath does not preserve str subclasses on this runtime")
    results = (
        S.initialize_manifest_store(hostile),
        S.load_and_verify_manifest_store(hostile),
        S.append_manifest_store_batch(hostile),
    )
    for result in results:
        _assert_rejected(result, "STORE_PATH_INVALID")
        _assert_no_echo(result, marker, "RuntimeError")


def test_r001_r030_path_matrix_missing_parent_directory_symlink_and_missing_target(
    tmp_path: Path, monkeypatch
) -> None:
    _assert_rejected(
        S.initialize_manifest_store(tmp_path / "missing" / "store.sqlite"),
        "STORE_PATH_INVALID",
    )
    _assert_rejected(S.initialize_manifest_store(tmp_path), "STORE_PATH_INVALID")
    missing = tmp_path / "missing.sqlite"
    _assert_rejected(S.load_and_verify_manifest_store(missing), "STORE_NOT_FOUND")
    _assert_rejected(S.append_manifest_store_batch(missing), "STORE_NOT_FOUND")
    target = tmp_path / "target.sqlite"
    assert S.initialize_manifest_store(str(target)).is_valid
    link = tmp_path / "link.sqlite"
    try:
        link.symlink_to(target)
    except OSError:
        # Windows may deny symlink creation without Developer Mode. Exercise
        # the identical fail-closed branch deterministically in that environment.
        original = Path.is_symlink
        monkeypatch.setattr(
            Path,
            "is_symlink",
            lambda candidate: candidate == link or original(candidate),
        )
    _assert_rejected(S.load_and_verify_manifest_store(link), "STORE_PATH_INVALID")
    _assert_rejected(S.initialize_manifest_store(link), "STORE_PATH_INVALID")
    _assert_rejected(S.append_manifest_store_batch(link), "STORE_PATH_INVALID")


def test_r002_r013_initialization_schema_reopen_read_only_and_idempotency(tmp_path: Path) -> None:
    path = tmp_path / "store.sqlite"
    first = S.initialize_manifest_store(path)
    assert first.is_valid and first.status == "STORE_INITIALIZED"
    assert first.snapshot == S.ManifestStoreSnapshot((), (), None, False, True, True)
    before = _db_sha(path)
    second = S.initialize_manifest_store(path)
    assert second.is_valid and second.status == "STORE_ALREADY_INITIALIZED"
    loaded = S.load_and_verify_manifest_store(path)
    assert loaded.is_valid and loaded.status == "STORE_LOADED_VERIFIED"
    assert loaded.snapshot == first.snapshot
    assert _db_sha(path) == before
    with sqlite3.connect(path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone() == (1,)
        assert connection.execute("PRAGMA journal_mode").fetchone() == ("delete",)
        objects = connection.execute(
            "SELECT type, name FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' ORDER BY name"
        ).fetchall()
        assert objects == [
            ("table", "dataset_references"),
            ("table", "manifest_entries"),
            ("table", "store_meta"),
        ]
        assert connection.execute("PRAGMA integrity_check").fetchall() == [("ok",)]
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
    assert not path.with_name(path.name + "-wal").exists()
    assert not path.with_name(path.name + "-shm").exists()
    assert not path.with_name(path.name + "-journal").exists()


def test_pristine_zero_table_database_can_be_initialized(tmp_path: Path) -> None:
    path = tmp_path / "pristine.sqlite"
    sqlite3.connect(path).close()
    result = S.initialize_manifest_store(path)
    assert result.is_valid and result.status == "STORE_INITIALIZED"


def test_failed_new_initialization_removes_only_new_file(tmp_path: Path, monkeypatch) -> None:
    path = tmp_path / "failed-new.sqlite"

    def injected_failure(connection) -> None:
        raise RuntimeError("deterministic initialization injection")

    monkeypatch.setattr(S, "_verify_schema", injected_failure)
    _assert_rejected(S.initialize_manifest_store(path), "STORE_WRITE_FAILED")
    assert not path.exists()


def test_post_commit_verification_failure_removes_new_store(
    tmp_path: Path, monkeypatch
) -> None:
    path = tmp_path / "post-commit-failed-new.sqlite"
    calls = 0

    def fail_final_verification(_path: Path) -> S.ManifestStoreResult:
        nonlocal calls
        calls += 1
        return S._rejected("STORE_OPEN_FAILED")

    monkeypatch.setattr(S, "_load_path", fail_final_verification)
    _assert_rejected(S.initialize_manifest_store(path), "STORE_OPEN_FAILED")
    assert calls == 1
    assert not path.exists()


def test_post_commit_verification_failure_preserves_preexisting_pristine_store(
    tmp_path: Path, monkeypatch
) -> None:
    path = tmp_path / "post-commit-failed-pristine.sqlite"
    sqlite3.connect(path).close()
    calls = 0

    def fail_verification(_path: Path) -> S.ManifestStoreResult:
        nonlocal calls
        calls += 1
        return S._rejected("STORE_OPEN_FAILED")

    monkeypatch.setattr(S, "_load_path", fail_verification)
    _assert_rejected(S.initialize_manifest_store(path), "STORE_OPEN_FAILED")
    assert calls == 2
    assert path.is_file()
    with sqlite3.connect(path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone() == (1,)
        assert connection.execute(
            "SELECT COUNT(*) FROM store_meta"
        ).fetchone() == (1,)


def test_schema_with_matching_columns_but_missing_check_is_not_adopted(tmp_path: Path) -> None:
    path = tmp_path / "near-schema.sqlite"
    with sqlite3.connect(path) as connection:
        connection.execute(
            "CREATE TABLE store_meta ("
            "singleton INTEGER PRIMARY KEY NOT NULL, "
            "format_id TEXT NOT NULL, schema_version INTEGER NOT NULL)"
        )
        connection.execute(
            "CREATE TABLE dataset_references ("
            "dataset_snapshot_reference_id TEXT PRIMARY KEY NOT NULL, "
            "payload_json TEXT NOT NULL, payload_sha256 TEXT NOT NULL)"
        )
        connection.execute(
            "CREATE TABLE manifest_entries ("
            "manifest_entry_id TEXT PRIMARY KEY NOT NULL, manifest_id TEXT NOT NULL, "
            "sequence_number INTEGER NOT NULL CHECK (sequence_number >= 0), "
            "dataset_snapshot_reference_id TEXT NOT NULL, payload_json TEXT NOT NULL, "
            "payload_sha256 TEXT NOT NULL, UNIQUE (manifest_id, sequence_number), "
            "FOREIGN KEY (dataset_snapshot_reference_id) REFERENCES dataset_references"
            "(dataset_snapshot_reference_id) ON UPDATE RESTRICT ON DELETE RESTRICT)"
        )
        connection.execute(
            "INSERT INTO store_meta VALUES (1, 'point-in-time-manifest-store', 1)"
        )
        connection.execute("PRAGMA user_version=1")
    _assert_rejected(S.initialize_manifest_store(path), "STORE_SCHEMA_UNSUPPORTED")


def test_r014_r030_batch_boundary_rejects_before_file_access(tmp_path: Path) -> None:
    missing = tmp_path / "missing.sqlite"
    class CustomIterable:
        def __iter__(self):
            return iter(())

    invalid_batches = [
        "x", b"x", {}, set(), (item for item in ()), iter(()), CustomIterable(), None
    ]
    for batch in invalid_batches:
        result = S.append_manifest_store_batch(missing, dataset_references=batch)  # type: ignore[arg-type]
        _assert_rejected(result, "STORE_INPUT_INVALID")
    for wrong in (1, MR.ManifestEntry):
        result = S.append_manifest_store_batch(missing, dataset_references=[wrong])  # type: ignore[list-item]
        _assert_rejected(result, "STORE_REFERENCE_INVALID")
    result = S.append_manifest_store_batch(missing, manifest_entries=[_reference()])  # type: ignore[list-item]
    _assert_rejected(result, "STORE_ENTRY_INVALID")


def test_r014_list_and_tuple_subclasses_reject_without_custom_iteration(
    tmp_path: Path,
) -> None:
    missing = tmp_path / "MISSING_PATH_MUST_NOT_BE_ACCESSED.sqlite"
    marker = "HOSTILE_CONTAINER_ITERATION"
    side_effect = {"called": False}

    class ExplodingList(list):
        def __iter__(self):
            side_effect["called"] = True
            raise RuntimeError(marker)

    class ExplodingTuple(tuple):
        def __iter__(self):
            side_effect["called"] = True
            raise RuntimeError(marker)

    hostile_values = (ExplodingList(), ExplodingTuple())
    for hostile in hostile_values:
        for field_name in ("dataset_references", "manifest_entries"):
            side_effect["called"] = False
            result = S.append_manifest_store_batch(
                missing,
                **{field_name: hostile},
            )
            _assert_rejected(result, "STORE_INPUT_INVALID")
            assert side_effect["called"] is False
            assert not missing.exists()
            _assert_no_echo(result, marker, str(missing))


def test_r014_r030_direct_malformed_dataclasses_reject_before_write(tmp_path: Path) -> None:
    path = tmp_path / "store.sqlite"
    assert S.initialize_manifest_store(path).is_valid
    reference = _reference()
    malformed = replace(reference, advisory_only=False)
    _assert_rejected(
        S.append_manifest_store_batch(path, dataset_references=[malformed]),
        "STORE_REFERENCE_INVALID",
    )
    entry = _entry(reference)
    malformed_entry = replace(entry, no_execution_authority=False)
    _assert_rejected(
        S.append_manifest_store_batch(path, manifest_entries=[malformed_entry]),
        "STORE_ENTRY_INVALID",
    )


def test_r014_r027_append_complete_chain_reopen_and_idempotency(tmp_path: Path) -> None:
    path = tmp_path / "store.sqlite"
    references, entries, committed = _valid_store(path, entries=3)
    assert committed.status == "STORE_APPEND_COMMITTED"
    assert committed.inserted_dataset_reference_ids == tuple(
        sorted(reference.dataset_snapshot_reference_id for reference in references)
    )
    assert committed.inserted_manifest_entry_ids == tuple(
        entry.manifest_entry_id for entry in entries
    )
    reopened = S.load_and_verify_manifest_store(path)
    assert reopened.is_valid and reopened.snapshot == committed.snapshot
    assert reopened.snapshot is not None
    assert reopened.snapshot.chain_validation is not None
    assert reopened.snapshot.chain_validation.status == "CHAIN_VALID"
    before = _db_sha(path)
    retry = S.append_manifest_store_batch(
        path, dataset_references=list(references), manifest_entries=list(entries)
    )
    assert retry.is_valid and retry.status == "STORE_APPEND_IDEMPOTENT"
    assert retry.idempotent_dataset_reference_ids == tuple(
        sorted(reference.dataset_snapshot_reference_id for reference in references)
    )
    assert retry.idempotent_manifest_entry_ids == tuple(
        entry.manifest_entry_id for entry in entries
    )
    assert _db_sha(path) == before


def test_reference_only_empty_batch_and_review_aggregation(tmp_path: Path) -> None:
    path = tmp_path / "store.sqlite"
    assert S.initialize_manifest_store(path).is_valid
    review_reference = _reference("review", review=True)
    appended = S.append_manifest_store_batch(path, dataset_references=[review_reference])
    assert appended.is_valid and appended.snapshot is not None
    assert appended.snapshot.chain_validation is None
    assert appended.snapshot.human_review_required is True
    before = _db_sha(path)
    empty = S.append_manifest_store_batch(path)
    assert empty.is_valid and empty.status == "STORE_APPEND_IDEMPOTENT"
    assert _db_sha(path) == before


def test_r023_r025_duplicate_batch_and_sequence_conflicts_are_atomic(tmp_path: Path) -> None:
    path = tmp_path / "store.sqlite"
    assert S.initialize_manifest_store(path).is_valid
    reference = _reference()
    entry = _entry(reference)
    duplicate = S.append_manifest_store_batch(
        path,
        dataset_references=[reference, reference],
        manifest_entries=[entry, entry],
    )
    assert duplicate.is_valid
    assert duplicate.idempotent_dataset_reference_ids == (
        reference.dataset_snapshot_reference_id,
    )
    assert duplicate.idempotent_manifest_entry_ids == (entry.manifest_entry_id,)
    second_reference = _reference("second")
    collision = _entry(second_reference, sequence=0)
    before = _db_sha(path)
    _assert_rejected(
        S.append_manifest_store_batch(
            path,
            dataset_references=[second_reference],
            manifest_entries=[collision],
        ),
        "STORE_DUPLICATE_CONFLICT",
    )
    assert _db_sha(path) == before


def test_r028_injected_failure_rolls_back_after_first_insert(tmp_path: Path, monkeypatch) -> None:
    path = tmp_path / "store.sqlite"
    assert S.initialize_manifest_store(path).is_valid
    reference = _reference()
    entry = _entry(reference)
    before = path.read_bytes()
    calls = 0

    def fail_after_first_insert() -> None:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("private deterministic injection")

    monkeypatch.setattr(S, "_after_insert_hook", fail_after_first_insert)
    _assert_rejected(
        S.append_manifest_store_batch(
            path, dataset_references=[reference], manifest_entries=[entry]
        ),
        "STORE_WRITE_FAILED",
    )
    assert calls == 1
    assert path.read_bytes() == before
    assert S.load_and_verify_manifest_store(path).snapshot == S.ManifestStoreSnapshot(
        (), (), None, False, True, True
    )


def test_r028_writer_contention_fails_fast_without_partial_write(tmp_path: Path) -> None:
    path = tmp_path / "store.sqlite"
    assert S.initialize_manifest_store(path).is_valid
    reference = _reference()
    entry = _entry(reference)
    before = _db_sha(path)
    holder = sqlite3.connect(path, isolation_level=None, timeout=0.0)
    try:
        holder.execute("BEGIN IMMEDIATE")
        _assert_rejected(
            S.append_manifest_store_batch(
                path, dataset_references=[reference], manifest_entries=[entry]
            ),
            "STORE_BUSY",
        )
    finally:
        holder.execute("ROLLBACK")
        holder.close()
    assert _db_sha(path) == before
    assert S.append_manifest_store_batch(
        path, dataset_references=[reference], manifest_entries=[entry]
    ).is_valid


@pytest.mark.parametrize(
    "tamper,code",
    [
        ("extra_table", "STORE_SCHEMA_UNSUPPORTED"),
        ("extra_view", "STORE_SCHEMA_UNSUPPORTED"),
        ("extra_trigger", "STORE_SCHEMA_UNSUPPORTED"),
        ("extra_index", "STORE_SCHEMA_UNSUPPORTED"),
        ("user_version", "STORE_SCHEMA_UNSUPPORTED"),
        ("meta", "STORE_SCHEMA_UNSUPPORTED"),
        ("reference_json", "STORE_PAYLOAD_INVALID"),
        ("reference_hash", "STORE_PAYLOAD_INVALID"),
        ("reference_pk", "STORE_SQLITE_INTEGRITY_FAILED"),
        ("manifest_json", "STORE_PAYLOAD_INVALID"),
        ("manifest_hash", "STORE_PAYLOAD_INVALID"),
        ("manifest_column", "STORE_PAYLOAD_INVALID"),
    ],
)
def test_r029_schema_and_payload_tamper_matrix(tmp_path: Path, tamper: str, code: str) -> None:
    path = tmp_path / f"{tamper}.sqlite"
    _valid_store(path)
    with sqlite3.connect(path) as connection:
        if tamper == "extra_table":
            connection.execute("CREATE TABLE extra (x INTEGER)")
        elif tamper == "extra_view":
            connection.execute("CREATE VIEW extra_view AS SELECT 1")
        elif tamper == "extra_trigger":
            connection.execute(
                "CREATE TRIGGER extra_trigger AFTER INSERT ON store_meta BEGIN SELECT 1; END"
            )
        elif tamper == "extra_index":
            connection.execute("CREATE INDEX extra_index ON manifest_entries(manifest_id)")
        elif tamper == "user_version":
            connection.execute("PRAGMA user_version=2")
        elif tamper == "meta":
            connection.execute("DELETE FROM store_meta")
        elif tamper == "reference_json":
            connection.execute("UPDATE dataset_references SET payload_json='{' ")
        elif tamper == "reference_hash":
            connection.execute("UPDATE dataset_references SET payload_sha256=?", (_hex("bad"),))
        elif tamper == "reference_pk":
            connection.execute(
                "UPDATE dataset_references SET dataset_snapshot_reference_id=?",
                ("datasetref:sha256:" + _hex("wrong"),),
            )
        elif tamper == "manifest_json":
            connection.execute("UPDATE manifest_entries SET payload_json='[]'")
        elif tamper == "manifest_hash":
            connection.execute("UPDATE manifest_entries SET payload_sha256=?", (_hex("bad"),))
        else:
            connection.execute("UPDATE manifest_entries SET manifest_id='manifest:wrong'")
    _assert_rejected(S.load_and_verify_manifest_store(path), code)


@pytest.mark.parametrize(
    "payload",
    [
        '{"schema_id":"x","schema_id":"y"}',
        '{"value":NaN}',
        ' {"value":1}',
        '"not-an-object"',
        "x" * 65537,
    ],
    ids=("duplicate-key", "nan", "noncanonical", "non-object", "oversized"),
)
def test_r029_strict_json_matrix(tmp_path: Path, payload: str) -> None:
    path = tmp_path / "strict.sqlite"
    _valid_store(path)
    with sqlite3.connect(path) as connection:
        connection.execute(
            "UPDATE dataset_references SET payload_json=?, payload_sha256=?",
            (payload, hashlib.sha256(payload.encode("utf-8")).hexdigest()),
        )
    _assert_rejected(S.load_and_verify_manifest_store(path), "STORE_PAYLOAD_INVALID")


@pytest.mark.parametrize(
    "table,field,value,code",
    [
        ("dataset_references", "validator_version", "", "STORE_REFERENCE_INVALID"),
        ("dataset_references", "advisory_only", False, "STORE_REFERENCE_INVALID"),
        ("manifest_entries", "previous_manifest_entry_id", "manifestentry:sha256:" + "0" * 64, "STORE_ENTRY_INVALID"),
        ("manifest_entries", "reference_state", "INVALIDATED_REFERENCE", "STORE_ENTRY_INVALID"),
        ("manifest_entries", "reason_code", "MANUAL_INVALIDATION", "STORE_ENTRY_INVALID"),
        ("manifest_entries", "no_execution_authority", False, "STORE_ENTRY_INVALID"),
    ],
)
def test_r029_semantic_and_safety_payload_tamper_matrix(
    tmp_path: Path, table: str, field: str, value: object, code: str
) -> None:
    path = tmp_path / f"{table}-{field}.sqlite"
    _valid_store(path)
    _replace_payload_field(path, table, field, value)
    _assert_rejected(S.load_and_verify_manifest_store(path), code)


@pytest.mark.parametrize(
    "column,value,code",
    [
        ("manifest_entry_id", "manifestentry:sha256:" + "1" * 64, "STORE_PAYLOAD_INVALID"),
        ("manifest_id", "manifest:wrong", "STORE_PAYLOAD_INVALID"),
        ("sequence_number", 7, "STORE_PAYLOAD_INVALID"),
    ],
)
def test_r029_manifest_redundant_column_matrix(
    tmp_path: Path, column: str, value: object, code: str
) -> None:
    path = tmp_path / f"column-{column}.sqlite"
    _valid_store(path)
    with sqlite3.connect(path) as connection:
        connection.execute(f"UPDATE manifest_entries SET {column}=?", (value,))
    _assert_rejected(S.load_and_verify_manifest_store(path), code)


def test_r029_manifest_reference_column_mismatch_with_valid_foreign_key(tmp_path: Path) -> None:
    path = tmp_path / "manifest-reference-column.sqlite"
    references, _, _ = _valid_store(path, entries=2)
    with sqlite3.connect(path) as connection:
        connection.execute(
            "UPDATE manifest_entries SET dataset_snapshot_reference_id=? WHERE sequence_number=0",
            (references[1].dataset_snapshot_reference_id,),
        )
    _assert_rejected(S.load_and_verify_manifest_store(path), "STORE_PAYLOAD_INVALID")


def test_r029_truncated_database_fails_closed(tmp_path: Path) -> None:
    path = tmp_path / "truncated.sqlite"
    _valid_store(path)
    content = path.read_bytes()
    path.write_bytes(content[: max(100, len(content) // 3)])
    result = S.load_and_verify_manifest_store(path)
    assert not result.is_valid
    assert result.status == "STORE_REJECTED"
    assert result.error_codes in {
        ("STORE_OPEN_FAILED",),
        ("STORE_SQLITE_INTEGRITY_FAILED",),
        ("STORE_SCHEMA_UNSUPPORTED",),
    }


def test_random_bytes_unrelated_schema_and_foreign_key_corruption_fail_closed(tmp_path: Path) -> None:
    random_path = tmp_path / "random.sqlite"
    random_path.write_bytes(b"not sqlite")
    random_before = random_path.read_bytes()
    result = S.load_and_verify_manifest_store(random_path)
    assert not result.is_valid and result.error_codes in {
        ("STORE_OPEN_FAILED",), ("STORE_SQLITE_INTEGRITY_FAILED",)
    }
    initialized = S.initialize_manifest_store(random_path)
    assert not initialized.is_valid
    assert random_path.read_bytes() == random_before
    unrelated = tmp_path / "unrelated.sqlite"
    with sqlite3.connect(unrelated) as connection:
        connection.execute("CREATE TABLE unrelated (x INTEGER)")
    _assert_rejected(S.initialize_manifest_store(unrelated), "STORE_SCHEMA_UNSUPPORTED")
    path = tmp_path / "fk.sqlite"
    references, entries, _ = _valid_store(path)
    with sqlite3.connect(path) as connection:
        connection.execute("PRAGMA foreign_keys=OFF")
        connection.execute(
            "UPDATE manifest_entries SET dataset_snapshot_reference_id=?",
            ("datasetref:sha256:" + _hex("missing"),),
        )
    _assert_rejected(
        S.load_and_verify_manifest_store(path), "STORE_SQLITE_INTEGRITY_FAILED"
    )


def test_wal_configuration_is_rejected_and_not_repaired(tmp_path: Path) -> None:
    path = tmp_path / "wal.sqlite"
    assert S.initialize_manifest_store(path).is_valid
    with sqlite3.connect(path) as connection:
        assert connection.execute("PRAGMA journal_mode=WAL").fetchone() == ("wal",)
    _assert_rejected(
        S.load_and_verify_manifest_store(path), "STORE_CONFIGURATION_INVALID"
    )


def test_r031_invalid_result_recursive_no_echo_and_field_coverage(tmp_path: Path) -> None:
    marker = "SECRET_PATH_MARKER"
    result = S.load_and_verify_manifest_store(tmp_path / marker)
    _assert_rejected(result, "STORE_NOT_FOUND")

    _assert_no_echo(result, marker, str(tmp_path))
    assert set(result.__dataclass_fields__) == {field.name for field in fields(result)}


def test_r032_source_sql_and_side_effect_safety() -> None:
    source = inspect.getsource(S)
    forbidden = (
        "executescript(", "eval(", "exec(", "pickle", "marshal", "shelve",
        "subprocess", "socket", "requests", "httpx", "aiohttp", "os.environ",
        "getenv(", "check_same_thread", "journal_mode=OFF", "journal_mode=MEMORY",
        "synchronous=OFF", "synchronous=NORMAL",
    )
    assert not [token for token in forbidden if token.lower() in source.lower()]
    assert "BEGIN IMMEDIATE" in source
    assert '_connect(path, "ro")' in source
    assert '_connect(normalized, "rw")' in source
    assert 'else "rwc"' in source
    assert not re.search(
        r"\b(?:UPDATE|DELETE)\s+(?:FROM\s+)?(?:dataset_references|manifest_entries)\b",
        source,
        re.IGNORECASE,
    )
    assert sqlite3.sqlite_version


def test_r030_256_row_bounds(tmp_path: Path) -> None:
    path = tmp_path / "limit.sqlite"
    assert S.initialize_manifest_store(path).is_valid
    references = [_reference(f"limit-{index}") for index in range(256)]
    result = S.append_manifest_store_batch(path, dataset_references=references)
    assert result.is_valid
    before = _db_sha(path)
    _assert_rejected(
        S.append_manifest_store_batch(path, dataset_references=[_reference("257")]),
        "STORE_LIMIT_EXCEEDED",
    )
    assert _db_sha(path) == before


def test_r030_256_entry_chain_is_accepted(tmp_path: Path) -> None:
    path = tmp_path / "entry-limit.sqlite"
    assert S.initialize_manifest_store(path).is_valid
    references = tuple(_reference(f"entry-limit-{index}") for index in range(256))
    entries = []
    previous = None
    for index, reference in enumerate(references):
        entry = _entry(reference, sequence=index, previous=previous)
        entries.append(entry)
        previous = entry.manifest_entry_id
    result = S.append_manifest_store_batch(
        path, dataset_references=references, manifest_entries=entries
    )
    assert result.is_valid and result.snapshot is not None
    assert len(result.snapshot.dataset_references) == 256
    assert len(result.snapshot.manifest_entries) == 256
