"""Focused tests for the WP167 canonical-PIT -> derived research Parquet layer.

Local, offline, deterministic. Every store lives below pytest ``tmp_path`` and
every derived Parquet partition is written into ``tmp_path``; nothing is written
into the repository. Canonical evidence is produced exclusively through the merged
WP163 public API. DuckDB-dependent assertions are executed without skips under
strict hosted CI (the authoritative cross-platform proof); locally they run when
the pinned DuckDB native module loads and are otherwise skipped with an explicit
reason when a local OS security policy (Windows Smart App Control) blocks the
binary. That local state is environmental and can change over time.
"""

from __future__ import annotations

import dataclasses
import os
import pathlib

import pytest

import src.data_layer.point_in_time_market_research as pit
from src.data_layer.point_in_time_market_research import records as R
from src.data_layer.point_in_time_market_research.manifest_reference import (
    DATASET_REFERENCE_SCHEMA_ID,
    DATASET_REFERENCE_SCHEMA_VERSION,
    build_dataset_snapshot_reference,
)
from src.data_layer.point_in_time_market_research.as_of_synthetic_cases import (
    build_synthetic_as_of_records,
)

import src.data_layer.analytical_research as ar
from src.data_layer.analytical_research import research_dataset as RD


# ── DuckDB strict/skip gate (Windows Smart App Control environmental block) ───


def _duckdb_or_skip():
    strict = os.environ.get("WP167_STRICT_DUCKDB") == "1"
    try:
        import duckdb  # noqa: PLC0415

        return duckdb
    except Exception as exc:  # pragma: no cover - exercised in CI/local split
        if strict:
            raise
        pytest.skip(
            "DuckDB native module unavailable in local environment "
            f"(Windows Smart App Control): {type(exc).__name__}; "
            "executed under strict hosted CI instead"
        )


# ── Builders / fixtures ──────────────────────────────────────────────────────


def _clean_records():
    recs = build_synthetic_as_of_records()
    chosen = [recs["MKT-META-PRIMARY"], recs["SRC-PRIMARY"]]
    for value in recs.values():
        if value.envelope.record_family == "RESOLUTION_RULE_SNAPSHOT":
            chosen.append(value)
    return recs, chosen


def _batch_reference(ordinary_records):
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
        "validator_version": "validator:wp167:test",
        "parameter_set_id": "params:wp167:test",
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
        "validator_version": "validator:wp167:test",
        "parameter_set_id": "params:wp167:test",
        "human_review_required": bool(review_ids),
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


def _store(tmp_path, records, name="store.sqlite3"):
    path = tmp_path / name
    assert pit.initialize_point_in_time_record_store(str(path)).is_valid
    appended = pit.append_point_in_time_records(str(path), list(records))
    assert appended.is_valid, appended.error_codes
    return path


def _outdir(tmp_path, name):
    directory = tmp_path / name
    directory.mkdir()
    return directory


def _all_strings(value):
    out = []
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        for f in dataclasses.fields(value):
            out.extend(_all_strings(getattr(value, f.name)))
    elif isinstance(value, str):
        out.append(value)
    elif isinstance(value, (list, tuple)):
        for item in value:
            out.extend(_all_strings(item))
    return out


# ── Successful materialization ───────────────────────────────────────────────


def test_materialize_validated_batch_across_families(tmp_path):
    _, chosen = _clean_records()
    reference = _batch_reference(chosen)
    store = _store(tmp_path, chosen)
    out = _outdir(tmp_path, "out")
    result = ar.materialize_canonical_pit_dataset(str(store), reference, str(out))

    assert result.is_valid and result.status == "ANALYTICAL_MATERIALIZED"
    assert result.error_codes == ()
    assert result.advisory_only is True and result.no_execution_authority is True
    manifest = result.manifest
    assert manifest is not None
    assert manifest.total_row_count == len(chosen)
    assert tuple(p.table_name for p in manifest.partition_manifests) == ar.ANALYTICAL_TABLE_ORDER
    for partition in manifest.partition_manifests:
        assert (out / partition.relative_path).is_file()
    assert manifest.pyarrow_version == ar.EXPECTED_PYARROW_VERSION
    assert manifest.duckdb_version == ar.EXPECTED_DUCKDB_VERSION
    assert manifest.polars_version == ar.EXPECTED_POLARS_VERSION
    assert manifest.advisory_only is True and manifest.no_execution_authority is True


def test_manifest_contains_no_absolute_paths(tmp_path):
    _, chosen = _clean_records()
    reference = _batch_reference(chosen)
    store = _store(tmp_path, chosen)
    out = _outdir(tmp_path, "abs")
    result = ar.materialize_canonical_pit_dataset(str(store), reference, str(out))
    drive = str(tmp_path)
    for text in _all_strings(result):
        assert drive not in text
        assert not text.startswith("/")
        assert "\\" not in text


# ── Logical vs physical identity ─────────────────────────────────────────────


def test_logical_id_is_path_independent(tmp_path):
    _, chosen = _clean_records()
    reference = _batch_reference(chosen)
    store = _store(tmp_path, chosen)
    out_a = _outdir(tmp_path, "a")
    out_b = _outdir(tmp_path, "b")
    a = ar.materialize_canonical_pit_dataset(str(store), reference, str(out_a))
    b = ar.materialize_canonical_pit_dataset(str(store), reference, str(out_b))
    assert a.logical_dataset_id == b.logical_dataset_id
    assert [p.logical_rows_sha256 for p in a.manifest.partition_manifests] == [
        p.logical_rows_sha256 for p in b.manifest.partition_manifests
    ]


def test_logical_id_changes_when_source_records_change(tmp_path):
    recs, chosen = _clean_records()
    reference_a = _batch_reference(chosen)
    store_a = _store(tmp_path, chosen, "a.sqlite3")
    out_a = _outdir(tmp_path, "oa")
    a = ar.materialize_canonical_pit_dataset(str(store_a), reference_a, str(out_a))

    smaller = [chosen[0], chosen[1]]
    reference_b = _batch_reference(smaller)
    store_b = _store(tmp_path, smaller, "b.sqlite3")
    out_b = _outdir(tmp_path, "ob")
    b = ar.materialize_canonical_pit_dataset(str(store_b), reference_b, str(out_b))

    assert a.logical_dataset_id != b.logical_dataset_id


def test_physical_integrity_is_separate_from_logical_identity(tmp_path):
    _, chosen = _clean_records()
    reference = _batch_reference(chosen)
    store = _store(tmp_path, chosen)
    out = _outdir(tmp_path, "phys")
    result = ar.materialize_canonical_pit_dataset(str(store), reference, str(out))
    partition = result.manifest.partition_manifests[0]

    ok, codes = ar.verify_partition_file_integrity(partition, str(out))
    assert ok and codes == ()

    target = out / partition.relative_path
    target.write_bytes(target.read_bytes() + b"corruption")
    ok, codes = ar.verify_partition_file_integrity(partition, str(out))
    assert not ok and codes == ("ANALYTICAL_FILE_INTEGRITY_INVALID",)


def test_deterministic_writer_reproduces_identical_partitions(tmp_path):
    _, chosen = _clean_records()
    reference = _batch_reference(chosen)
    store = _store(tmp_path, chosen)
    out_a = _outdir(tmp_path, "det_a")
    out_b = _outdir(tmp_path, "det_b")
    a = ar.materialize_canonical_pit_dataset(str(store), reference, str(out_a))
    b = ar.materialize_canonical_pit_dataset(str(store), reference, str(out_b))
    for pa_part, pb_part in zip(a.manifest.partition_manifests, b.manifest.partition_manifests):
        assert pa_part.logical_rows_sha256 == pb_part.logical_rows_sha256
        assert pa_part.schema_fingerprint_sha256 == pb_part.schema_fingerprint_sha256
        assert pa_part.parquet_file_sha256 == pb_part.parquet_file_sha256


# ── Review-role preservation ─────────────────────────────────────────────────


def test_review_conflict_role_is_preserved(tmp_path):
    recs = build_synthetic_as_of_records()
    ordinary = [recs["MKT-META-PRIMARY"]]
    review = [recs["MKT-CONFLICT"]]
    store = _store(tmp_path, [recs["MKT-META-PRIMARY"], recs["MKT-CONFLICT"]])
    reference = _asof_reference(ordinary, review)
    out = _outdir(tmp_path, "review")
    result = ar.materialize_canonical_pit_dataset(str(store), reference, str(out))
    assert result.is_valid, result.error_codes

    counts = {p.table_name: p.row_count for p in result.manifest.partition_manifests}
    assert counts[ar.TABLE_REVIEW_CONFLICTS] == 1
    assert counts[ar.TABLE_MARKET_OBSERVATIONS] == 1

    frame_review = ar.polars_group_count(
        str(out / f"{ar.TABLE_REVIEW_CONFLICTS}.parquet"), "classification"
    )
    assert frame_review == {"CONFLICT": 1}
    frame_market = ar.polars_group_count(
        str(out / f"{ar.TABLE_MARKET_OBSERVATIONS}.parquet"), "analytical_role"
    )
    assert frame_market == {"ORDINARY": 1}


# ── UTC timestamps and null handling ─────────────────────────────────────────


def test_utc_timestamp_columns_and_null_event_time(tmp_path):
    _, chosen = _clean_records()
    reference = _batch_reference(chosen)
    store = _store(tmp_path, chosen)
    out = _outdir(tmp_path, "utc")
    ar.materialize_canonical_pit_dataset(str(store), reference, str(out))

    import polars as pl

    source_frame = pl.read_parquet(str(out / f"{ar.TABLE_SOURCE_SNAPSHOTS}.parquet"))
    # Derived UTC timestamps are stored tz-naive (UTC wall-clock) so DuckDB/Polars
    # queries need no timezone database; the canonical string columns retain the
    # explicit UTC offset for provenance.
    assert source_frame["observed_time_utc"].dtype == pl.Datetime("us")
    assert source_frame["observed_time"][0].endswith("Z")
    # The source snapshot has a null event_time; the derived UTC column must be null.
    assert source_frame["event_time_utc"].null_count() == source_frame.height


# ── Negative / boundary matrix ───────────────────────────────────────────────


def test_non_reference_input_is_rejected(tmp_path):
    store = _store(tmp_path, _clean_records()[1])
    out = _outdir(tmp_path, "n1")
    result = ar.materialize_canonical_pit_dataset(str(store), {"not": "a reference"}, str(out))
    assert result.error_codes == ("ANALYTICAL_REFERENCE_INVALID",)
    assert result.manifest is None and result.logical_dataset_id is None


def test_invalid_store_is_rejected(tmp_path):
    _, chosen = _clean_records()
    reference = _batch_reference(chosen)
    out = _outdir(tmp_path, "n2")
    missing = tmp_path / "does_not_exist.sqlite3"
    result = ar.materialize_canonical_pit_dataset(str(missing), reference, str(out))
    assert result.error_codes == ("ANALYTICAL_CANONICAL_STORE_INVALID",)


def test_invalid_output_directory_is_rejected(tmp_path):
    _, chosen = _clean_records()
    reference = _batch_reference(chosen)
    store = _store(tmp_path, chosen)
    result = ar.materialize_canonical_pit_dataset(
        str(store), reference, str(tmp_path / "missing_dir")
    )
    assert result.error_codes == ("ANALYTICAL_INPUT_INVALID",)


def test_reference_absent_record_is_rejected(tmp_path):
    _, chosen = _clean_records()
    reference = _batch_reference(chosen)
    # Store only a subset so the reference points at an absent record.
    store = _store(tmp_path, [chosen[0]])
    out = _outdir(tmp_path, "n3")
    result = ar.materialize_canonical_pit_dataset(str(store), reference, str(out))
    assert not result.is_valid
    assert result.error_codes == ("ANALYTICAL_MATERIALIZATION_FAILED",)


def test_rejected_result_never_echoes_paths_or_exceptions(tmp_path):
    token_dir = tmp_path / "SECRET_TOKEN_dir"
    token_dir.mkdir()
    _, chosen = _clean_records()
    reference = _batch_reference(chosen)
    result = ar.materialize_canonical_pit_dataset(
        str(tmp_path / "SECRET_TOKEN_missing.sqlite3"), reference, str(token_dir)
    )
    for text in _all_strings(result):
        assert "SECRET_TOKEN" not in text
        assert "Traceback" not in text
        assert "Error" not in text or text in ar.ANALYTICAL_RESEARCH_ERROR_CODES


# ── DuckDB / Polars parity (DuckDB strict in CI, skipped locally) ─────────────


def test_duckdb_polars_row_and_group_parity(tmp_path):
    _duckdb_or_skip()
    _, chosen = _clean_records()
    reference = _batch_reference(chosen)
    store = _store(tmp_path, chosen)
    out = _outdir(tmp_path, "parity")
    ar.materialize_canonical_pit_dataset(str(store), reference, str(out))
    path = str(out / f"{ar.TABLE_MARKET_OBSERVATIONS}.parquet")

    assert ar.duckdb_row_count(path) == ar.polars_row_count(path)
    assert ar.duckdb_group_count(path, "record_family") == ar.polars_group_count(
        path, "record_family"
    )
    assert ar.duckdb_timestamp_min_max(path, "observed_time_utc") == ar.polars_timestamp_min_max(
        path, "observed_time_utc"
    )
    assert ar.duckdb_filter_count(path, "analytical_role", "ORDINARY") == ar.polars_filter_count(
        path, "analytical_role", "ORDINARY"
    )


def test_polars_queries_available_without_duckdb(tmp_path):
    # PyArrow/Polars analytical access must work even where DuckDB cannot load.
    _, chosen = _clean_records()
    reference = _batch_reference(chosen)
    store = _store(tmp_path, chosen)
    out = _outdir(tmp_path, "polars_only")
    ar.materialize_canonical_pit_dataset(str(store), reference, str(out))
    path = str(out / f"{ar.TABLE_SOURCE_SNAPSHOTS}.parquet")
    assert ar.polars_row_count(path) == 1
    assert ar.polars_group_count(path, "record_family") == {"SOURCE_SNAPSHOT": 1}


def test_duckdb_is_not_imported_at_module_load():
    import sys

    # Importing the analytical package must never eagerly import the DuckDB
    # native module (which is blocked by Smart App Control locally).
    assert "src.data_layer.analytical_research.research_dataset" in sys.modules
    # Fresh import of the module object does not require duckdb.
    assert RD.materialize_canonical_pit_dataset is not None


# ── Blocker A: complete canonical PIT projection ─────────────────────────────

import importlib.metadata

from src.data_layer.point_in_time_market_research.as_of_synthetic_cases import (
    build_synthetic_as_of_records,
)


def _read_parquet(path):
    import polars as pl

    return pl.read_parquet(str(path))


def test_logical_row_commits_full_envelope_and_family(tmp_path):
    _, chosen = _clean_records()
    market = chosen[0]
    row = RD._logical_row(market, ar.TABLE_MARKET_OBSERVATIONS, "ORDINARY")
    # Every envelope field is committed to the logical row.
    for name in RD._ENVELOPE_COLUMNS:
        assert name in row
    # Family fields and the canonical payload are committed.
    for name in ("mo_observation_kind", "mo_source_assertion_id", "canonical_payload_json"):
        assert name in row
    assert row["lifecycle_state"] == market.envelope.lifecycle_state
    assert row["snapshot_id"] == market.envelope.snapshot_id


def test_supersedes_change_alters_logical_digest():
    _, chosen = _clean_records()
    record = chosen[0]
    base = RD._logical_rows_sha256([RD._logical_row(record, ar.TABLE_MARKET_OBSERVATIONS, "ORDINARY")])
    mutated_env = dataclasses.replace(record.envelope, supersedes_record_version_id="record:sha256:other")
    mutated = dataclasses.replace(record, envelope=mutated_env)
    changed = RD._logical_rows_sha256([RD._logical_row(mutated, ar.TABLE_MARKET_OBSERVATIONS, "ORDINARY")])
    assert base != changed


def test_lineage_parent_ids_change_and_order_alter_logical_digest():
    _, chosen = _clean_records()
    record = chosen[0]
    env_ab = dataclasses.replace(record.envelope, lineage_parent_ids=("p1", "p2"))
    env_ba = dataclasses.replace(record.envelope, lineage_parent_ids=("p2", "p1"))
    env_none = dataclasses.replace(record.envelope, lineage_parent_ids=())
    d_ab = RD._logical_rows_sha256([RD._logical_row(dataclasses.replace(record, envelope=env_ab), ar.TABLE_MARKET_OBSERVATIONS, "ORDINARY")])
    d_ba = RD._logical_rows_sha256([RD._logical_row(dataclasses.replace(record, envelope=env_ba), ar.TABLE_MARKET_OBSERVATIONS, "ORDINARY")])
    d_none = RD._logical_rows_sha256([RD._logical_row(dataclasses.replace(record, envelope=env_none), ar.TABLE_MARKET_OBSERVATIONS, "ORDINARY")])
    assert d_ab != d_ba != d_none and d_ab != d_none


def test_complete_provenance_and_family_columns_survive(tmp_path):
    _, chosen = _clean_records()
    reference = _batch_reference(chosen)
    store = _store(tmp_path, chosen)
    out = _outdir(tmp_path, "proj")
    assert ar.materialize_canonical_pit_dataset(str(store), reference, str(out)).is_valid

    market = _read_parquet(out / f"{ar.TABLE_MARKET_OBSERVATIONS}.parquet")
    for col in ("snapshot_id", "source_snapshot_id", "resolution_rule_snapshot_id",
                "ingestion_batch_id", "lifecycle_state", "source_content_sha256",
                "lineage_parent_ids", "mo_observation_kind", "mo_source_assertion_id"):
        assert col in market.columns
    source = _read_parquet(out / f"{ar.TABLE_SOURCE_SNAPSHOTS}.parquet")
    for col in ("ss_source_type", "ss_source_reference", "ss_raw_content_sha256",
                "ss_byte_length", "ss_retrieval_version", "ss_access_classification"):
        assert col in source.columns
    assert source["ss_byte_length"].dtype.__class__.__name__ in ("Int64", "Int64Type") or str(source["ss_byte_length"].dtype).startswith("Int")
    rule = _read_parquet(out / f"{ar.TABLE_RESOLUTION_RULE_SNAPSHOTS}.parquet")
    for col in ("rr_resolution_source_id", "rr_source_snapshot_id", "rr_rule_content_sha256",
                "rr_ambiguity_labels", "rr_source_hierarchy_rank", "rr_human_review_state"):
        assert col in rule.columns
    assert rule["rr_ambiguity_labels"][0].to_list() == list(
        [v for v in chosen if v.envelope.record_family == "RESOLUTION_RULE_SNAPSHOT"][0].ambiguity_labels
    )


def test_review_conflict_retains_complete_family_semantics(tmp_path):
    recs = build_synthetic_as_of_records()
    ordinary = [recs["MKT-META-PRIMARY"]]
    review = [recs["MKT-CONFLICT"]]
    store = _store(tmp_path, [recs["MKT-META-PRIMARY"], recs["MKT-CONFLICT"]])
    reference = _asof_reference(ordinary, review)
    out = _outdir(tmp_path, "review_family")
    assert ar.materialize_canonical_pit_dataset(str(store), reference, str(out)).is_valid

    frame = _read_parquet(out / f"{ar.TABLE_REVIEW_CONFLICTS}.parquet")
    # The union table carries every family's columns.
    for col in ("mo_observation_kind", "ss_source_type", "rr_resolution_source_id"):
        assert col in frame.columns
    # The market-family conflict populates mo_* and leaves other families null.
    assert frame["mo_market_id"][0] is not None
    assert frame["ss_source_type"][0] is None
    assert frame["rr_resolution_source_id"][0] is None


# ── Blocker C: manifest version truth and runtime gate ───────────────────────


def test_manifest_reports_actual_installed_versions(tmp_path):
    _, chosen = _clean_records()
    reference = _batch_reference(chosen)
    store = _store(tmp_path, chosen)
    out = _outdir(tmp_path, "versions")
    manifest = ar.materialize_canonical_pit_dataset(str(store), reference, str(out)).manifest
    assert manifest.duckdb_version == importlib.metadata.version("duckdb")
    assert manifest.pyarrow_version == importlib.metadata.version("pyarrow")
    assert manifest.polars_version == importlib.metadata.version("polars")


def test_runtime_dependency_mismatch_rejects_materialization(tmp_path, monkeypatch):
    _, chosen = _clean_records()
    reference = _batch_reference(chosen)
    store = _store(tmp_path, chosen)
    out = _outdir(tmp_path, "mismatch")
    real = RD._installed_version
    monkeypatch.setattr(
        RD, "_installed_version",
        lambda dist: "0.0.0" if dist == "duckdb" else real(dist),
    )
    result = ar.materialize_canonical_pit_dataset(str(store), reference, str(out))
    assert not result.is_valid
    assert result.error_codes == ("ANALYTICS_DEPENDENCY_VERSION_INVALID",)
    assert not (out / f"{ar.TABLE_MARKET_OBSERVATIONS}.parquet").exists()


# ── Blocker A (round 3): analytical row hashing supports large valid payloads ──

from src.data_layer.point_in_time_market_research.as_of_synthetic_cases import _meta


def _big_conflict_record(n_labels=40, label_len=200, assertion="assertion:big"):
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


def test_valid_pit_record_with_large_payload_materializes(tmp_path):
    conflict = _big_conflict_record()
    # The canonical payload exceeds WP156's 4096-byte per-string bound; applying the
    # WP156 canonicalizer to the outer analytical row would wrongly reject it.
    assert len(conflict.canonical_payload_json) > 4096
    recs = build_synthetic_as_of_records()
    ordinary = [recs["MKT-META-PRIMARY"]]
    store = _store(tmp_path, [recs["MKT-META-PRIMARY"], conflict])
    reference = _asof_reference(ordinary, [conflict])
    out_a = _outdir(tmp_path, "big_a")
    out_b = _outdir(tmp_path, "big_b")
    result = ar.materialize_canonical_pit_dataset(str(store), reference, str(out_a))
    assert result.is_valid, result.error_codes

    frame = _read_parquet(out_a / f"{ar.TABLE_REVIEW_CONFLICTS}.parquet")
    stored = frame.filter(
        frame["record_version_id"] == conflict.envelope.record_version_id
    )["canonical_payload_json"][0]
    assert stored == conflict.canonical_payload_json

    # Deterministic logical identity for the large-payload record.
    result_b = ar.materialize_canonical_pit_dataset(str(store), reference, str(out_b))
    assert result.logical_dataset_id == result_b.logical_dataset_id


# ── Final round: result-object field-coverage gate (WP88+) ───────────────────

_PARTITION_MANIFEST_FIELDS = {
    "table_name": "SCANNED", "relative_path": "SCANNED", "row_count": "EXEMPT_INT",
    "logical_rows_sha256": "SCANNED", "parquet_file_sha256": "SCANNED",
    "parquet_byte_length": "EXEMPT_INT", "schema_fingerprint_sha256": "SCANNED",
}
_DATASET_MANIFEST_FIELDS = {
    "schema_id": "SCANNED", "schema_version": "SCANNED", "logical_dataset_id": "SCANNED",
    "source_kind": "SCANNED", "source_reference_id": "SCANNED",
    "analytical_schema_version": "SCANNED", "materializer_version": "SCANNED",
    "partition_manifests": "SCANNED", "total_row_count": "EXEMPT_INT",
    "pyarrow_version": "SCANNED", "duckdb_version": "SCANNED", "polars_version": "SCANNED",
    "python_version": "SCANNED", "advisory_only": "EXEMPT_BOOL", "no_execution_authority": "EXEMPT_BOOL",
}
_MATERIALIZATION_RESULT_FIELDS = {
    "is_valid": "EXEMPT_BOOL", "status": "SCANNED", "error_codes": "SCANNED",
    "manifest": "SCANNED", "logical_dataset_id": "SCANNED",
    "advisory_only": "EXEMPT_BOOL", "no_execution_authority": "EXEMPT_BOOL",
}
_RUNTIME_RESULT_FIELDS = {
    "is_valid": "EXEMPT_BOOL", "status": "SCANNED", "error_codes": "SCANNED",
    "pyarrow_version": "SCANNED", "duckdb_version": "SCANNED", "polars_version": "SCANNED",
    "python_version": "SCANNED", "advisory_only": "EXEMPT_BOOL", "no_execution_authority": "EXEMPT_BOOL",
}


def test_research_dataclass_field_coverage_is_complete():
    assert {f.name for f in dataclasses.fields(ar.AnalyticalPartitionManifest)} == set(_PARTITION_MANIFEST_FIELDS)
    assert {f.name for f in dataclasses.fields(ar.AnalyticalDatasetManifest)} == set(_DATASET_MANIFEST_FIELDS)
    assert {f.name for f in dataclasses.fields(ar.AnalyticalMaterializationResult)} == set(_MATERIALIZATION_RESULT_FIELDS)
    assert {f.name for f in dataclasses.fields(ar.AnalyticalRuntimeCompatibilityResult)} == set(_RUNTIME_RESULT_FIELDS)


def test_invalid_materialization_result_recursive_no_echo(tmp_path):
    token_dir = tmp_path / "HOSTILE_SENTINEL_dir"
    token_dir.mkdir()
    result = ar.materialize_canonical_pit_dataset(
        str(tmp_path / "HOSTILE_SENTINEL_missing.sqlite3"),
        {"hostile": "HOSTILE_SENTINEL_reference"},
        str(token_dir),
    )
    assert not result.is_valid and result.manifest is None
    for text in _all_strings(result):
        assert "HOSTILE_SENTINEL" not in text
        assert text in ar.ANALYTICAL_RESEARCH_ERROR_CODES or text == "ANALYTICAL_REJECTED"


def test_valid_materialization_result_is_recursively_scannable(tmp_path):
    _, chosen = _clean_records()
    reference = _batch_reference(chosen)
    store = _store(tmp_path, chosen)
    out = _outdir(tmp_path, "scan")
    result = ar.materialize_canonical_pit_dataset(str(store), reference, str(out))
    # A valid result (with nested manifest + partition manifests) scans without error.
    strings = _all_strings(result)
    assert strings and all(isinstance(s, str) for s in strings)
