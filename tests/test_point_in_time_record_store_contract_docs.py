"""Deterministic documentation regression for the WP163 record-store contract.

Proves the canonical contract document
(``docs/point_in_time_record_store_contract.md``) records the locked label and
posture, the exact public API and SQLite schema, the bounds, the canonical
full-record payload rules, the ordinary/review-conflict integrity split, the
complete-lineage failure vocabulary, the append-only/idempotency and
transaction/lock posture, the corruption/no-echo posture, both dataset
materialization modes with the honest as-of limitation, and the successor
boundary. The document is repo truth, not a self-referential PR artifact.
"""

from __future__ import annotations

import pathlib


CONTRACT = (
    pathlib.Path(__file__).resolve().parents[1]
    / "docs"
    / "point_in_time_record_store_contract.md"
)


def _read() -> str:
    return CONTRACT.read_text(encoding="utf-8")


def test_contract_document_exists() -> None:
    assert CONTRACT.is_file()


def test_label_posture_and_format_are_locked() -> None:
    text = _read()
    for phrase in (
        "POINT_IN_TIME_DURABLE_RECORD_STORE",
        "BOUNDED_LOCAL_SQLITE_APPEND_ONLY_RECORD_PERSISTENCE_AND_MATERIALIZATION",
        "point-in-time-record-store",
        "src/data_layer/point_in_time_market_research/record_store.py",
    ):
        assert phrase in text


def test_public_api_is_documented() -> None:
    text = _read()
    for phrase in (
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
    ):
        assert phrase in text


def test_schema_indexes_and_bounds_are_documented() -> None:
    text = _read()
    for phrase in (
        "record_store_meta",
        "records(record_version_id PRIMARY KEY",
        "idx_pit_records_ingestion_time",
        "idx_pit_records_observed_time",
        "idx_pit_records_event_time",
        "idx_pit_records_market_id",
        "idx_pit_records_source_id",
        "256",
        "4096",
        "131072",
        "134217728",
        "user_version",
        "no migration",
    ):
        assert phrase in text


def test_payload_lineage_and_integrity_are_documented() -> None:
    text = _read()
    for phrase in (
        "canonical_json_bytes",
        "sha256_hex",
        "duplicate keys",
        "NaN/Infinity",
        "validate_record_batch",
        "revalidate_review_conflict_record",
        "ordinary authority",
        "RECORD_STORE_LINEAGE_INVALID",
        "RECORD_STORE_AUTHORITY_VIOLATION",
        # The outer full-record encoding is WP163's own canonicalizer, not WP156's
        # bounded helper applied to the whole record.
        "does **not**",
        "allow_nan=False",
        "131,072-byte per-row",
        "semantic authority for the embedded record",
    ):
        assert phrase in text


def test_bounded_reader_preflight_is_documented() -> None:
    text = _read()
    for phrase in (
        "bounded-reader preflight",
        "scalar aggregate",
        "**before** any payload row",
        "independently recomputed",
    ):
        assert phrase in text


def test_transaction_and_no_echo_posture_are_documented() -> None:
    text = _read()
    for phrase in (
        "BEGIN IMMEDIATE",
        "DELETE journal",
        "synchronous",
        "RECORD_STORE_BUSY",
        "WAL",
        "no production UPDATE or DELETE",
        "BaseException",
        "never exposes",
    ):
        assert phrase in text


def test_materialization_modes_and_limits_are_documented() -> None:
    text = _read()
    for phrase in (
        "build_dataset_snapshot_reference",
        "RECORD_STORE_REFERENCE_INVALID",
        "RECORD_STORE_REFERENCE_MISSING_RECORD",
        "RECORD_STORE_REFERENCE_CONTENT_MISMATCH",
        "VALIDATED_BATCH_RECOMPUTED",
        "AS_OF_REFERENCE_IDS_RESOLVED",
        "canonical_batch_sha256",
        "query replay",
        "as-of replay is deferred.",
    ):
        assert phrase in text


def test_boundaries_and_successor_are_documented() -> None:
    text = _read()
    for phrase in (
        "No manifest-store schema change",
        "No Parquet/Arrow/DuckDB/Polars",
        "no real/public data population",
        "WP164",
        "separately gated",
    ):
        assert phrase in text
