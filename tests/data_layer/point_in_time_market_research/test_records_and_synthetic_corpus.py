"""Focused WP156 record, lineage, safety, and synthetic-corpus regression."""

from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, asdict, fields, is_dataclass, replace
from decimal import Decimal
import hashlib
import json
import math
from pathlib import Path

import pytest

import src.data_layer.point_in_time_market_research as pit
from src.data_layer.point_in_time_market_research import records as record_module


ROOT = Path(__file__).resolve().parents[3]
SOURCE_DIR = ROOT / "src" / "data_layer" / "point_in_time_market_research"

CASE_IDS = (
    "PIT-C01-VALID-MARKET-METADATA",
    "PIT-C02-VALID-ORDER-BOOK-MISSING-EVENT-TIME",
    "PIT-C03-VALID-PUBLIC-TRADE",
    "PIT-C04-VALID-SOURCE-SNAPSHOT",
    "PIT-C05-VALID-RESOLUTION-RULE-SNAPSHOT",
    "PIT-C06-VALID-LATE-ARRIVAL",
    "PIT-C07-VALID-SOURCE-REVISION",
    "PIT-C08-VALID-PROJECT-CORRECTION",
    "PIT-C09-VALID-SOURCE-RETRACTION",
    "PIT-C10-VALID-EXACT-DUPLICATE",
    "PIT-C11-VALID-SEMANTIC-DUPLICATE",
    "PIT-C12-CONFLICT-REQUIRES-REVIEW",
    "PIT-C13-INVALID-NAIVE-TIME",
    "PIT-C14-INVALID-INGESTION-BEFORE-OBSERVED",
    "PIT-C15-INVALID-SCHEMA-MAJOR",
    "PIT-C16-INVALID-UNKNOWN-FIELD",
    "PIT-C17-INVALID-NESTED-SECRET-KEY",
    "PIT-C18-INVALID-FLOAT-PAYLOAD",
    "PIT-C19-INVALID-LINEAGE-CYCLE",
    "PIT-C20-INVALID-CORRECTION-BACKDATE",
)


def _builder(case_id: str):
    case = next(case for case in pit.get_synthetic_point_in_time_cases() if case.case_id == case_id)
    if case.case_family == "MARKET_OBSERVATION":
        return pit.build_market_observation
    if case.case_family == "SOURCE_SNAPSHOT":
        return pit.build_source_snapshot
    if case.case_family == "RESOLUTION_RULE_SNAPSHOT":
        return pit.build_resolution_rule_snapshot
    raise ValueError("BATCH_CASE_HAS_NO_DIRECT_BUILDER")


def _build(case_id: str) -> pit.PointInTimeBuildResult:
    return _builder(case_id)(pit.load_synthetic_case_input(case_id))


def _record(case_id: str):
    result = _build(case_id)
    assert result.is_valid and result.record is not None
    return result.record


def _recursive_text(value: object) -> str:
    if is_dataclass(value) and not isinstance(value, type):
        return _recursive_text(asdict(value))
    if isinstance(value, dict):
        return " ".join(
            f"{_recursive_text(key)} {_recursive_text(nested)}"
            for key, nested in value.items()
        )
    if isinstance(value, (list, tuple, set, frozenset)):
        return " ".join(_recursive_text(item) for item in value)
    return value if isinstance(value, str) else repr(value)


def _assert_batch_rejects_record(
    record: object, *expected_codes: str
) -> pit.PointInTimeBatchValidationResult:
    result = pit.validate_record_batch([record])
    assert result.is_valid is False
    for code in expected_codes:
        assert code in result.error_codes
    record_id = record.envelope.record_version_id
    assert record_id not in result.accepted_record_version_ids
    assert record_id in result.quarantined_record_version_ids
    return result


def _independent_record_version_id(record: object) -> str:
    envelope = record.envelope
    if isinstance(record, pit.MarketObservationRecord):
        metadata = {
            "observation_kind": record.observation_kind,
            "platform_id": record.platform_id,
            "event_id": record.event_id,
            "market_id": record.market_id,
            "token_id": record.token_id,
            "source_id": record.source_id,
            "source_assertion_id": record.source_assertion_id,
        }
    elif isinstance(record, pit.SourceSnapshotRecord):
        metadata = {
            "source_id": record.source_id,
            "source_type": record.source_type,
            "source_reference": record.source_reference,
            "media_type": record.media_type,
            "raw_content_sha256": record.raw_content_sha256,
            "byte_length": record.byte_length,
            "retrieval_method": record.retrieval_method,
            "retrieval_version": record.retrieval_version,
            "upstream_revision": record.upstream_revision,
            "prior_source_snapshot_id": record.prior_source_snapshot_id,
            "access_classification": record.access_classification,
        }
    else:
        metadata = {
            "platform_id": record.platform_id,
            "event_id": record.event_id,
            "market_id": record.market_id,
            "resolution_source_id": record.resolution_source_id,
            "source_snapshot_id": record.source_snapshot_id,
            "rule_content_sha256": record.rule_content_sha256,
            "source_declared_effective_time": record.source_declared_effective_time,
            "ambiguity_labels": record.ambiguity_labels,
            "source_hierarchy_rank": record.source_hierarchy_rank,
            "human_review_state": record.human_review_state,
        }

    def digest(value: object) -> str:
        encoded = json.dumps(
            value,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    preimage = {
        "schema_id": pit.SUPPORTED_SCHEMA_ID,
        "schema_version": pit.SUPPORTED_SCHEMA_VERSION,
        "record_family": envelope.record_family,
        "record_specific_metadata_sha256": digest(metadata),
        "canonical_payload_sha256": envelope.canonical_payload_sha256,
        "observation_id": envelope.observation_id,
        "snapshot_id": envelope.snapshot_id,
        "source_snapshot_id": envelope.source_snapshot_id,
        "resolution_rule_snapshot_id": envelope.resolution_rule_snapshot_id,
        "ingestion_batch_id": envelope.ingestion_batch_id,
        "observed_time": envelope.observed_time,
        "ingestion_time": envelope.ingestion_time,
        "event_time": envelope.event_time,
        "lineage_parent_ids": envelope.lineage_parent_ids,
        "supersedes_record_version_id": envelope.supersedes_record_version_id,
        "lifecycle_state": envelope.lifecycle_state,
        "classification": envelope.classification,
        "normalizer_version": envelope.normalizer_version,
        "validator_version": envelope.validator_version,
        "parameter_set_id": envelope.parameter_set_id,
        "source_content_sha256": envelope.source_content_sha256,
        "human_review_required": envelope.human_review_required,
        "advisory_only": envelope.advisory_only,
        "no_execution_authority": envelope.no_execution_authority,
    }
    return "record:sha256:" + digest(preimage)


def test_public_package_exports_exact_supported_surface() -> None:
    # The WP156 validation surface is preserved verbatim; the WP157 bounded
    # as-of query surface is appended by the separately approved successor WP.
    assert pit.__all__ == (
        "FOUNDATION_LABEL",
        "IMPLEMENTATION_POSTURE",
        "SUPPORTED_SCHEMA_ID",
        "SUPPORTED_SCHEMA_VERSION",
        "SUPPORTED_RECORD_FAMILIES",
        "SUPPORTED_OBSERVATION_KINDS",
        "LIFECYCLE_STATES",
        "RECORD_CLASSIFICATIONS",
        "VALIDATION_STATUSES",
        "PointInTimeEnvelope",
        "MarketObservationRecord",
        "SourceSnapshotRecord",
        "ResolutionRuleSnapshotRecord",
        "QuarantineDescriptor",
        "PointInTimeBuildResult",
        "PointInTimeBatchValidationResult",
        "SyntheticPointInTimeCase",
        "canonical_json_bytes",
        "sha256_hex",
        "build_market_observation",
        "build_source_snapshot",
        "build_resolution_rule_snapshot",
        "validate_record_batch",
        "get_synthetic_point_in_time_cases",
        "load_synthetic_case_input",
        "AS_OF_QUERY_LABEL",
        "AS_OF_QUERY_POSTURE",
        "SUPPORTED_CUTOFF_MODES",
        "SUPPORTED_RESULT_VIEWS",
        "QUERY_STATUSES",
        "EXCLUSION_REASONS",
        "EventTimeWindow",
        "PointInTimeQuerySpec",
        "PointInTimeQueryReceipt",
        "PointInTimeRecordSetResult",
        "SyntheticAsOfQueryCase",
        "query_point_in_time_record_set",
        "get_synthetic_as_of_query_cases",
        "load_synthetic_as_of_query_case",
        # WP160 bounded in-memory manifest chain and dataset snapshot reference
        # validation surface (appended by the separately approved successor WP).
        "MANIFEST_REFERENCE_LABEL",
        "MANIFEST_REFERENCE_POSTURE",
        "DATASET_REFERENCE_SCHEMA_ID",
        "DATASET_REFERENCE_SCHEMA_VERSION",
        "MANIFEST_ENTRY_SCHEMA_ID",
        "MANIFEST_ENTRY_SCHEMA_VERSION",
        "DATASET_DERIVATION_MODES",
        "MANIFEST_ENTRY_KINDS",
        "REFERENCE_STATES",
        "MANIFEST_REASON_CODES",
        "MANIFEST_REFERENCE_VALIDATION_STATUSES",
        "MANIFEST_REFERENCE_ERROR_CODES",
        "DatasetSnapshotReference",
        "ManifestEntry",
        "DatasetSnapshotReferenceBuildResult",
        "ManifestEntryBuildResult",
        "ManifestChainValidationResult",
        "build_dataset_snapshot_reference",
        "build_manifest_entry",
        "validate_manifest_chain",
        # WP161 bounded local SQLite transactional manifest store.
        "MANIFEST_STORE_LABEL",
        "MANIFEST_STORE_POSTURE",
        "MANIFEST_STORE_FORMAT_ID",
        "MANIFEST_STORE_SCHEMA_VERSION",
        "MANIFEST_STORE_STATUSES",
        "MANIFEST_STORE_ERROR_CODES",
        "ManifestStoreSnapshot",
        "ManifestStoreResult",
        "initialize_manifest_store",
        "append_manifest_store_batch",
        "load_and_verify_manifest_store",
        # WP162 bounded deterministic WP156/WP157 -> WP160 -> WP161 dataset
        # persistence and registration adapters.
        "DATASET_PERSISTENCE_ADAPTER_LABEL",
        "DATASET_PERSISTENCE_ADAPTER_POSTURE",
        "DATASET_PERSISTENCE_ADAPTER_STATUSES",
        "DATASET_PERSISTENCE_ADAPTER_ERROR_CODES",
        "DatasetPersistenceAdapterResult",
        "persist_validated_record_batch_snapshot",
        "persist_as_of_query_snapshot",
        # WP163 bounded durable local SQLite point-in-time record store and
        # dataset snapshot materialization (appended by the separately approved
        # successor WP).
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


def test_locked_constants_and_vocabularies_are_exact_tuples() -> None:
    assert pit.FOUNDATION_LABEL == "POINT_IN_TIME_APPEND_ONLY_MARKET_RESEARCH_DATA_CONTRACT"
    assert pit.IMPLEMENTATION_POSTURE == "LOCAL_OFFLINE_STDLIB_ONLY_IN_MEMORY_VALIDATION"
    assert pit.SUPPORTED_SCHEMA_ID == "point-in-time-market-research-record"
    assert pit.SUPPORTED_SCHEMA_VERSION == "1.0.0"
    assert pit.SUPPORTED_RECORD_FAMILIES == (
        "MARKET_OBSERVATION",
        "SOURCE_SNAPSHOT",
        "RESOLUTION_RULE_SNAPSHOT",
    )
    assert pit.SUPPORTED_OBSERVATION_KINDS == (
        "MARKET_METADATA",
        "ORDER_BOOK",
        "PUBLIC_TRADE",
    )
    assert pit.LIFECYCLE_STATES == (
        "RAW_CAPTURED",
        "NORMALIZED_ACCEPTED",
        "QUARANTINED",
        "SUPERSEDED",
        "RETRACTED_BY_SOURCE",
        "INVALIDATED_BY_CONTRACT",
    )
    assert len(pit.RECORD_CLASSIFICATIONS) == 8
    assert len(pit.VALIDATION_STATUSES) == 6


@pytest.mark.parametrize(
    "public_type",
    (
        pit.PointInTimeEnvelope,
        pit.MarketObservationRecord,
        pit.SourceSnapshotRecord,
        pit.ResolutionRuleSnapshotRecord,
        pit.QuarantineDescriptor,
        pit.PointInTimeBuildResult,
        pit.PointInTimeBatchValidationResult,
        pit.SyntheticPointInTimeCase,
    ),
)
def test_public_dataclasses_are_frozen(public_type: type[object]) -> None:
    assert public_type.__dataclass_params__.frozen is True


def test_frozen_record_rejects_mutation() -> None:
    record = _record("PIT-C01-VALID-MARKET-METADATA")
    with pytest.raises(FrozenInstanceError):
        record.market_id = "market:synthetic:changed"


def test_result_object_field_coverage_and_invalid_full_surface_scan() -> None:
    expected = {
        pit.PointInTimeBuildResult: {
            "is_valid",
            "status",
            "error_codes",
            "warning_codes",
            "record",
            "quarantine",
        },
        pit.PointInTimeBatchValidationResult: {
            "is_valid",
            "status",
            "error_codes",
            "warning_codes",
            "accepted_record_version_ids",
            "exact_duplicate_record_version_ids",
            "quarantined_record_version_ids",
            "canonical_batch_sha256",
        },
        pit.QuarantineDescriptor: {
            "quarantine_id",
            "schema_id",
            "schema_version",
            "record_family",
            "source_id",
            "observed_time",
            "ingestion_time",
            "input_fingerprint_sha256",
            "failure_codes",
            "warning_codes",
            "operator_review_required",
            "safe_diagnostics_only",
        },
    }
    for public_type, names in expected.items():
        assert {field.name for field in fields(public_type)} == names
    invalid = _build("PIT-C17-INVALID-NESTED-SECRET-KEY")
    full_text = _recursive_text(invalid)
    assert "NEUTRAL_REDACTED_SYNTHETIC" not in full_text
    assert "api_key" not in full_text
    assert invalid.record is None


@pytest.mark.parametrize(
    ("field_name", "marker"),
    (
        ("schema_id", "QUARANTINE_MARKER_SCHEMA"),
        ("schema_version", "QUARANTINE_MARKER_VERSION"),
        ("record_family", "QUARANTINE_MARKER_FAMILY"),
        ("source_id", "source:synthetic:QUARANTINE_MARKER_SOURCE"),
        ("observed_time", "QUARANTINE_MARKER_OBSERVED"),
        ("ingestion_time", "QUARANTINE_MARKER_INGESTION"),
    ),
)
def test_quarantine_nominal_safe_field_value_channels_never_echo(
    field_name: str, marker: str
) -> None:
    candidate = pit.load_synthetic_case_input(CASE_IDS[0])
    candidate[field_name] = marker
    candidate["canonical_payload"]["nested"] = {
        "api_" + "key": "QUARANTINE_TRIGGER_VALUE"
    }
    first = pit.build_market_observation(candidate)
    second = pit.build_market_observation(candidate)
    assert first == second
    assert first.is_valid is False
    assert first.record is None
    assert first.quarantine is not None
    assert first.quarantine == second.quarantine
    assert (
        first.quarantine.schema_id,
        first.quarantine.schema_version,
        first.quarantine.record_family,
        first.quarantine.source_id,
        first.quarantine.observed_time,
        first.quarantine.ingestion_time,
    ) == (None, None, None, None, None, None)
    full_output = asdict(first)
    full_text = _recursive_text(full_output)
    assert marker not in full_text
    assert "api_" + "key" not in full_text
    assert "QUARANTINE_TRIGGER_VALUE" not in full_text
    assert "Traceback" not in full_text
    assert "C:\\" not in full_text
    assert candidate != full_output


@pytest.mark.parametrize(
    ("field_name", "malformed"),
    (
        ("schema_id", {"not": "a string"}),
        ("schema_version", ["not", "a", "string"]),
        ("record_family", 7),
        ("source_id", {"not": "an id"}),
        ("observed_time", ["not", "a", "timestamp"]),
        ("ingestion_time", {"not": "a timestamp"}),
    ),
)
def test_quarantine_malformed_nominal_safe_fields_are_none_and_bounded(
    field_name: str, malformed: object
) -> None:
    candidate = pit.load_synthetic_case_input(CASE_IDS[0])
    candidate[field_name] = malformed
    result = pit.build_market_observation(candidate)
    assert result.is_valid is False
    assert result.record is None
    assert result.quarantine is not None
    assert all(
        getattr(result.quarantine, name) is None
        for name in (
            "schema_id",
            "schema_version",
            "record_family",
            "source_id",
            "observed_time",
            "ingestion_time",
        )
    )
    assert len(result.quarantine.input_fingerprint_sha256) == 64
    assert result.quarantine.quarantine_id.startswith("quarantine:sha256:")


@pytest.mark.parametrize(
    "placement",
    ("top_level", "nested_mapping", "nested_list_mapping"),
)
def test_quarantine_unsafe_key_placements_never_echo_complete_output(
    placement: str,
) -> None:
    unsafe_key = "api_" + "key"
    marker = "QUARANTINE_UNSAFE_PLACEMENT_MARKER"
    candidate = pit.load_synthetic_case_input(CASE_IDS[0])
    if placement == "top_level":
        candidate[unsafe_key] = marker
    elif placement == "nested_mapping":
        candidate["canonical_payload"]["nested"] = {unsafe_key: marker}
    else:
        candidate["canonical_payload"]["nested"] = [{"items": [{unsafe_key: marker}]}]
    result = pit.build_market_observation(candidate)
    output = _recursive_text(asdict(result))
    assert result.is_valid is False
    assert result.record is None
    assert unsafe_key not in output
    assert marker not in output
    assert "Traceback" not in output
    assert "C:\\" not in output


def test_quarantine_hashes_are_fixed_independent_constants() -> None:
    candidate = pit.load_synthetic_case_input(CASE_IDS[0])
    candidate["schema_id"] = "QUARANTINE_MARKER_SCHEMA"
    result = pit.build_market_observation(candidate)
    assert result.quarantine is not None
    assert result.quarantine.input_fingerprint_sha256 == (
        "664e9cb88e55aa2245bef8e62755af979d7a3bb1ea4c2f97302846ffd29e547b"
    )
    assert result.quarantine.quarantine_id == (
        "quarantine:sha256:18a43e7bec2600c27d3f5e1fd19a3af6de1918682acba4710c47956067eab5f4"
    )


def test_quarantine_structural_fingerprint_ignores_arbitrary_string_values() -> None:
    first = pit.load_synthetic_case_input(CASE_IDS[0])
    second = pit.load_synthetic_case_input(CASE_IDS[0])
    first["source_id"] = "source:synthetic:QUARANTINE_MARKER_ONE"
    second["source_id"] = "source:synthetic:QUARANTINE_MARKER_TWO"
    first["observed_time"] = "QUARANTINE_TIME_MARKER_ONE"
    second["observed_time"] = "QUARANTINE_TIME_MARKER_TWO"
    first_result = pit.build_market_observation(first)
    second_result = pit.build_market_observation(second)
    assert first_result.quarantine is not None
    assert second_result.quarantine is not None
    assert (
        first_result.quarantine.input_fingerprint_sha256
        == second_result.quarantine.input_fingerprint_sha256
    )


def test_successful_record_retains_no_mutable_caller_references() -> None:
    caller = pit.load_synthetic_case_input("PIT-C02-VALID-ORDER-BOOK-MISSING-EVENT-TIME")
    payload = caller["canonical_payload"]
    result = pit.build_market_observation(caller)
    assert result.is_valid and isinstance(result.record, pit.MarketObservationRecord)
    payload["bids"][0]["price"] = "9.99"
    caller["lineage_parent_ids"].append("record:synthetic:mutated")
    assert '"price":"0.45"' in result.record.canonical_payload_json
    assert result.record.envelope.lineage_parent_ids == ()


def test_canonical_json_exact_bytes_key_order_unicode_and_null() -> None:
    value = {"z": None, "é": ["λ", True, 7], "a": {"b": "x"}}
    assert pit.canonical_json_bytes(value) == (
        '{"a":{"b":"x"},"z":null,"é":["λ",true,7]}'.encode("utf-8")
    )
    assert pit.canonical_json_bytes({"b": 2, "a": 1}) == b'{"a":1,"b":2}'
    assert pit.canonical_json_bytes(("x", "y")) == b'["x","y"]'


@pytest.mark.parametrize("value", (0.0, 0.5, math.nan, math.inf, -math.inf))
def test_canonical_json_rejects_all_floats(value: float) -> None:
    with pytest.raises(ValueError, match="^PAYLOAD_FLOAT_FORBIDDEN$"):
        pit.canonical_json_bytes({"value": value})


@pytest.mark.parametrize(
    ("value", "code"),
    (
        ({1: "x"}, "PAYLOAD_TYPE_UNSUPPORTED"),
        ({"x": b"bytes"}, "PAYLOAD_TYPE_UNSUPPORTED"),
        ({"x": bytearray(b"x")}, "PAYLOAD_TYPE_UNSUPPORTED"),
        ({"x": {"set"}}, "PAYLOAD_TYPE_UNSUPPORTED"),
        ({"x": Decimal("1.0")}, "PAYLOAD_TYPE_UNSUPPORTED"),
        ({"x": object()}, "PAYLOAD_TYPE_UNSUPPORTED"),
        ({"x": "a" * 4097}, "PAYLOAD_STRING_LIMIT_EXCEEDED"),
        ({"x": list(range(257))}, "PAYLOAD_SEQUENCE_LIMIT_EXCEEDED"),
        ({str(index): index for index in range(129)}, "PAYLOAD_KEY_LIMIT_EXCEEDED"),
    ),
)
def test_canonical_json_rejects_unsupported_and_bounded_inputs(
    value: object, code: str
) -> None:
    with pytest.raises(ValueError, match=f"^{code}$"):
        pit.canonical_json_bytes(value)


def test_canonical_json_depth_node_and_byte_bounds() -> None:
    deep: object = "leaf"
    for _ in range(9):
        deep = {"nested": deep}
    with pytest.raises(ValueError, match="^PAYLOAD_DEPTH_EXCEEDED$"):
        pit.canonical_json_bytes(deep)
    nodes = {
        f"k{outer}": {f"n{inner}": inner for inner in range(128)}
        for outer in range(9)
    }
    with pytest.raises(ValueError, match="^PAYLOAD_NODE_LIMIT_EXCEEDED$"):
        pit.canonical_json_bytes(nodes)
    with pytest.raises(ValueError, match="^PAYLOAD_SIZE_EXCEEDED$"):
        pit.canonical_json_bytes({"x": "é" * 4096, "items": ["é" * 4096] * 8})


def test_sha256_fixed_outputs_and_canonical_fixture_hashes() -> None:
    assert pit.sha256_hex(b"") == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    assert pit.sha256_hex("abc") == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    assert pit.sha256_hex(pit.canonical_json_bytes({"b": 2, "a": 1})) == (
        "43258cff783fe7036d8a43033f830adfc60ec037382473548ac742b888292777"
    )


@pytest.mark.parametrize("case_id", CASE_IDS[:12])
def test_first_twelve_corpus_cases_match_committed_expectations(case_id: str) -> None:
    case = next(case for case in pit.get_synthetic_point_in_time_cases() if case.case_id == case_id)
    result = _build(case_id)
    assert result.is_valid == case.expected_valid
    assert result.status == case.expected_status
    assert result.error_codes == case.expected_error_codes
    assert result.warning_codes == case.expected_warning_codes
    if result.record is not None:
        assert result.record.envelope.record_version_id == case.expected_record_version_id
        assert result.record.envelope.record_family == case.expected_record_family


def test_fixed_synthetic_record_ids_are_exact() -> None:
    expected = {
        "PIT-C01-VALID-MARKET-METADATA": "record:sha256:4f4b89654077ff2e6e24cec53c3e976172abb9a71ef4ec08e4e459cb29d97e72",
        "PIT-C02-VALID-ORDER-BOOK-MISSING-EVENT-TIME": "record:sha256:ff5df4b4293175aeebf40e41f0141f73d52fed69e3702ef63debe257859adbf3",
        "PIT-C03-VALID-PUBLIC-TRADE": "record:sha256:a837dd270e7d89a5c17dfeabdd2075484876a2effd312f62e394465d1717f048",
        "PIT-C04-VALID-SOURCE-SNAPSHOT": "record:sha256:bfac30b3ff4838a1e33fb65de44425726d4571cbf4a8359b86a3285940424447",
        "PIT-C05-VALID-RESOLUTION-RULE-SNAPSHOT": "record:sha256:8f69de0782a7dda84ed58cf78a970cc47964219eef9818a1384dd8ee5feb224c",
        "PIT-C06-VALID-LATE-ARRIVAL": "record:sha256:1a9443d9b25f74afd0a4f92f8889006254c0ef7851ed18e6c96be3d28986dae9",
        "PIT-C07-VALID-SOURCE-REVISION": "record:sha256:2e749ad9202902af554c9b3ca113f1ac6e827400285a59d09d8b8340e10ff97e",
        "PIT-C08-VALID-PROJECT-CORRECTION": "record:sha256:c8c22907a21709407a66bb92b7282018a2a5ccfa19cb14ce873120785a0e9c67",
        "PIT-C09-VALID-SOURCE-RETRACTION": "record:sha256:20b3c7025525a20feb649ffc235558ba4e22a842c066ba417441ca50bd60261e",
        "PIT-C10-VALID-EXACT-DUPLICATE": "record:sha256:f6ab5a5465ebe2357c14e5f4b3da14e20a32ef26ab74bf1676ff1c7ed5f75180",
        "PIT-C11-VALID-SEMANTIC-DUPLICATE": "record:sha256:d5756fd61545b7fba3ce41c4ae4ab5181bb533c0282dfc8afb4bc6cba866456a",
    }
    cases = {case.case_id: case for case in pit.get_synthetic_point_in_time_cases()}
    assert {case_id: cases[case_id].expected_record_version_id for case_id in expected} == expected
    for case_id, expected_id in expected.items():
        assert _independent_record_version_id(_record(case_id)) == expected_id


def test_all_twenty_expected_outcomes_are_committed_exact_constants() -> None:
    expected = {
        CASE_IDS[0]: (True, "VALID", (), ()),
        CASE_IDS[1]: (True, "VALID_WITH_WARNINGS", (), ("EVENT_TIME_MISSING_ALLOWED",)),
        CASE_IDS[2]: (True, "VALID", (), ()),
        CASE_IDS[3]: (True, "VALID_WITH_WARNINGS", (), ("EVENT_TIME_MISSING_ALLOWED",)),
        CASE_IDS[4]: (True, "VALID_WITH_WARNINGS", (), ("EVENT_TIME_MISSING_ALLOWED",)),
        CASE_IDS[5]: (True, "VALID_WITH_WARNINGS", (), ("LATE_ARRIVAL_DECLARED",)),
        CASE_IDS[6]: (
            True,
            "VALID_WITH_WARNINGS",
            (),
            ("EVENT_TIME_MISSING_ALLOWED", "SOURCE_REVISION_DECLARED"),
        ),
        CASE_IDS[7]: (True, "VALID_WITH_WARNINGS", (), ("PROJECT_CORRECTION_DECLARED",)),
        CASE_IDS[8]: (
            True,
            "VALID_WITH_WARNINGS",
            (),
            ("EVENT_TIME_MISSING_ALLOWED", "SOURCE_RETRACTION_DECLARED"),
        ),
        CASE_IDS[9]: (True, "VALID", (), ()),
        CASE_IDS[10]: (True, "VALID_WITH_WARNINGS", (), ("SEMANTIC_DUPLICATE_DECLARED",)),
        CASE_IDS[11]: (
            False,
            "CONFLICT_REQUIRES_REVIEW",
            ("CONFLICT_REQUIRES_HUMAN_REVIEW",),
            ("CONFLICT_DECLARED",),
        ),
        CASE_IDS[12]: (False, "REJECTED_CONTRACT", ("TIMESTAMP_FORMAT_INVALID",), ()),
        CASE_IDS[13]: (False, "REJECTED_CONTRACT", ("INGESTION_BEFORE_OBSERVED",), ()),
        CASE_IDS[14]: (False, "UNSUPPORTED_SCHEMA", ("SCHEMA_VERSION_UNSUPPORTED",), ()),
        CASE_IDS[15]: (False, "REJECTED_CONTRACT", ("UNKNOWN_FIELD",), ()),
        CASE_IDS[16]: (False, "QUARANTINED", ("SECRET_LIKE_KEY_REJECTED",), ()),
        CASE_IDS[17]: (False, "QUARANTINED", ("PAYLOAD_FLOAT_FORBIDDEN",), ()),
        CASE_IDS[18]: (False, "REJECTED_CONTRACT", ("LINEAGE_CYCLE",), ()),
        CASE_IDS[19]: (
            False,
            "REJECTED_CONTRACT",
            ("CORRECTION_VISIBILITY_VIOLATION",),
            ("PROJECT_CORRECTION_DECLARED",),
        ),
    }
    actual = {
        case.case_id: (
            case.expected_valid,
            case.expected_status,
            case.expected_error_codes,
            case.expected_warning_codes,
        )
        for case in pit.get_synthetic_point_in_time_cases()
    }
    assert actual == expected


@pytest.mark.parametrize("case_id", CASE_IDS[12:18])
def test_invalid_direct_corpus_cases_fail_closed(case_id: str) -> None:
    case = next(case for case in pit.get_synthetic_point_in_time_cases() if case.case_id == case_id)
    result = _build(case_id)
    assert result.is_valid is False
    assert result.record is None
    assert result.status == case.expected_status
    assert result.error_codes == case.expected_error_codes
    assert result.quarantine is not None
    assert result.quarantine.operator_review_required is True
    assert result.quarantine.safe_diagnostics_only is True


def test_exact_twenty_case_order_and_sanitized_content() -> None:
    cases = pit.get_synthetic_point_in_time_cases()
    assert tuple(case.case_id for case in cases) == CASE_IDS
    assert len(cases) == 20
    combined = "\n".join(case.input_json for case in cases)
    assert "example.invalid" in combined
    for forbidden in (
        "polymarket.com",
        "0x",
        "profit target",
        "trade_signal",
        "paper_order",
        "place_order",
        "private_key",
        "C:\\",
    ):
        assert forbidden not in combined
    assert all(case.safety_notice == "SANITIZED_SYNTHETIC_ONLY_NO_EXECUTION_AUTHORITY_NO_REAL_MARKET_DATA" for case in cases)


def test_load_synthetic_case_input_returns_fresh_mutable_mapping() -> None:
    first = pit.load_synthetic_case_input(CASE_IDS[0])
    second = pit.load_synthetic_case_input(CASE_IDS[0])
    first["canonical_payload"]["question_text"] = "mutated"
    assert second["canonical_payload"]["question_text"] != "mutated"
    assert pit.load_synthetic_case_input(CASE_IDS[0]) == second
    with pytest.raises(KeyError, match="SYNTHETIC_CASE_NOT_FOUND"):
        pit.load_synthetic_case_input("PIT-C99-MISSING")


def test_time_normalization_precision_and_event_warning() -> None:
    trade_input = pit.load_synthetic_case_input("PIT-C03-VALID-PUBLIC-TRADE")
    result = pit.build_market_observation(trade_input)
    assert result.is_valid and result.record is not None
    assert result.record.envelope.ingestion_time == "2026-01-01T00:00:08.123Z"
    assert result.record.envelope.event_time == "2026-01-01T00:00:06.123Z"
    trade_input["event_time"] = "2026-01-01T00:00:09.123Z"
    warned = pit.build_market_observation(trade_input)
    assert warned.is_valid
    assert warned.warning_codes == ("EVENT_TIME_AFTER_INGESTION",)


@pytest.mark.parametrize(
    ("timestamp", "expected"),
    (
        ("2026-01-01T00:00:00", "TIMESTAMP_FORMAT_INVALID"),
        ("2026-01-01T00:00:00+01:00", "TIMESTAMP_NOT_UTC"),
        ("2026-01-01T00:00:00.1234567Z", "TIMESTAMP_PRECISION_UNSUPPORTED"),
        ("2026-01-01", "TIMESTAMP_FORMAT_INVALID"),
        ("2026-01-01T00:00:60Z", "TIMESTAMP_FORMAT_INVALID"),
        (" 2026-01-01T00:00:00Z", "TIMESTAMP_FORMAT_INVALID"),
    ),
)
def test_timestamp_negative_matrix(timestamp: str, expected: str) -> None:
    candidate = pit.load_synthetic_case_input(CASE_IDS[0])
    candidate["observed_time"] = timestamp
    result = pit.build_market_observation(candidate)
    assert expected in result.error_codes


def test_public_trade_requires_event_time() -> None:
    candidate = pit.load_synthetic_case_input("PIT-C03-VALID-PUBLIC-TRADE")
    candidate["event_time"] = None
    result = pit.build_market_observation(candidate)
    assert result.is_valid is False
    assert "EVENT_TIME_REQUIRED" in result.error_codes


@pytest.mark.parametrize(
    "mutation",
    (
        lambda value: value.pop("market_id"),
        lambda value: value.__setitem__("market_id", 7),
        lambda value: value.__setitem__("record_family", "UNKNOWN"),
        lambda value: value.__setitem__("observation_kind", "UNKNOWN"),
        lambda value: value.__setitem__("platform_id", "not-namespaced"),
        lambda value: value.__setitem__("market_id", "market/path"),
        lambda value: value.__setitem__("record_version_id", "record:sha256:" + "0" * 64),
    ),
)
def test_field_schema_identity_and_derived_id_negative_matrix(mutation) -> None:
    candidate = pit.load_synthetic_case_input(CASE_IDS[0])
    mutation(candidate)
    result = pit.build_market_observation(candidate)
    assert result.is_valid is False
    assert result.record is None
    assert result.error_codes


@pytest.mark.parametrize("unsafe_key", tuple(record_module._SECRET_KEYS))
def test_secret_key_matrix_rejected_without_echo(unsafe_key: str) -> None:
    candidate = pit.load_synthetic_case_input(CASE_IDS[0])
    candidate["canonical_payload"]["nested"] = [{unsafe_key: "DO_NOT_ECHO_VALUE"}]
    result = pit.build_market_observation(candidate)
    assert result.error_codes == ("SECRET_LIKE_KEY_REJECTED",)
    full_text = _recursive_text(result)
    assert unsafe_key not in full_text
    assert "DO_NOT_ECHO_VALUE" not in full_text


@pytest.mark.parametrize("unsafe_key", tuple(record_module._AUTHORITY_KEYS))
def test_authority_key_matrix_rejected_without_echo(unsafe_key: str) -> None:
    candidate = pit.load_synthetic_case_input(CASE_IDS[0])
    candidate["canonical_payload"]["nested"] = {"items": [{unsafe_key: "DO_NOT_ECHO"}]}
    result = pit.build_market_observation(candidate)
    assert result.error_codes == ("AUTHORITY_LIKE_KEY_REJECTED",)
    assert unsafe_key not in _recursive_text(result)
    assert "DO_NOT_ECHO" not in _recursive_text(result)


@pytest.mark.parametrize("bad_decimal", (0.5, "-1", ".5", "01", "1.", "NaN", "Infinity", "1e-2"))
def test_order_book_decimal_string_matrix(bad_decimal: object) -> None:
    candidate = pit.load_synthetic_case_input("PIT-C02-VALID-ORDER-BOOK-MISSING-EVENT-TIME")
    candidate["canonical_payload"]["bids"][0]["price"] = bad_decimal
    result = pit.build_market_observation(candidate)
    assert result.is_valid is False
    assert "DECIMAL_STRING_INVALID" in result.error_codes


def test_source_snapshot_rejects_raw_content_private_access_and_invalid_sha() -> None:
    source = pit.load_synthetic_case_input("PIT-C04-VALID-SOURCE-SNAPSHOT")
    source["raw_body"] = "unsafe"
    assert pit.build_source_snapshot(source).error_codes == ("UNKNOWN_FIELD",)
    source = pit.load_synthetic_case_input("PIT-C04-VALID-SOURCE-SNAPSHOT")
    source["access_classification"] = "PRIVATE"
    assert pit.build_source_snapshot(source).error_codes == ("ACCESS_CLASSIFICATION_FORBIDDEN",)
    source = pit.load_synthetic_case_input("PIT-C04-VALID-SOURCE-SNAPSHOT")
    source["raw_content_sha256"] = "ABC"
    assert pit.build_source_snapshot(source).error_codes == ("SHA256_FORMAT_INVALID",)
    source = pit.load_synthetic_case_input("PIT-C04-VALID-SOURCE-SNAPSHOT")
    source["byte_length"] = True
    assert pit.build_source_snapshot(source).error_codes == ("FIELD_TYPE_INVALID",)


def test_resolution_rule_ambiguity_rank_review_and_conflict_matrix() -> None:
    rule = pit.load_synthetic_case_input("PIT-C05-VALID-RESOLUTION-RULE-SNAPSHOT")
    rule["ambiguity_labels"] = ["UNKNOWN"]
    assert pit.build_resolution_rule_snapshot(rule).error_codes == ("AMBIGUITY_LABEL_UNSUPPORTED",)
    rule = pit.load_synthetic_case_input("PIT-C05-VALID-RESOLUTION-RULE-SNAPSHOT")
    rule["source_hierarchy_rank"] = "UNKNOWN"
    assert pit.build_resolution_rule_snapshot(rule).error_codes == ("SOURCE_HIERARCHY_RANK_UNSUPPORTED",)
    rule = pit.load_synthetic_case_input("PIT-C05-VALID-RESOLUTION-RULE-SNAPSHOT")
    rule["human_review_state"] = "UNKNOWN"
    assert pit.build_resolution_rule_snapshot(rule).error_codes == ("HUMAN_REVIEW_STATE_UNSUPPORTED",)
    rule = pit.load_synthetic_case_input("PIT-C05-VALID-RESOLUTION-RULE-SNAPSHOT")
    rule["ambiguity_labels"] = ["CONFLICTING_SOURCE_TEXT"]
    result = pit.build_resolution_rule_snapshot(rule)
    assert result.is_valid is False
    assert "CONFLICT_REQUIRES_HUMAN_REVIEW" in result.error_codes


def test_lineage_builder_negative_matrix() -> None:
    base = _record(CASE_IDS[0])
    candidate = pit.load_synthetic_case_input("PIT-C08-VALID-PROJECT-CORRECTION")
    candidate["lineage_parent_ids"] = [base.envelope.record_version_id] * 2
    result = pit.build_market_observation(candidate)
    assert "LINEAGE_PARENT_DUPLICATE" in result.error_codes
    candidate = pit.load_synthetic_case_input("PIT-C08-VALID-PROJECT-CORRECTION")
    candidate["supersedes_record_version_id"] = None
    result = pit.build_market_observation(candidate)
    assert "SUPERSEDES_REQUIRED" in result.error_codes
    candidate = pit.load_synthetic_case_input("PIT-C08-VALID-PROJECT-CORRECTION")
    candidate["lineage_parent_ids"] = []
    result = pit.build_market_observation(candidate)
    assert "SUPERSEDES_NOT_IN_LINEAGE" in result.error_codes


def test_batch_revision_correction_retraction_duplicate_and_semantic_chains() -> None:
    records = [
        _record("PIT-C01-VALID-MARKET-METADATA"),
        _record("PIT-C04-VALID-SOURCE-SNAPSHOT"),
        _record("PIT-C07-VALID-SOURCE-REVISION"),
        _record("PIT-C08-VALID-PROJECT-CORRECTION"),
        _record("PIT-C09-VALID-SOURCE-RETRACTION"),
        _record("PIT-C10-VALID-EXACT-DUPLICATE"),
        _record("PIT-C11-VALID-SEMANTIC-DUPLICATE"),
    ]
    result = pit.validate_record_batch(records)
    assert result.is_valid is True
    assert result.error_codes == ()
    assert len(result.accepted_record_version_ids) == 7
    assert result.canonical_batch_sha256 == pit.validate_record_batch(records).canonical_batch_sha256


def test_batch_identical_object_acknowledged_once() -> None:
    record = _record(CASE_IDS[0])
    result = pit.validate_record_batch([record, record])
    assert result.is_valid
    assert result.accepted_record_version_ids == (record.envelope.record_version_id,)
    assert result.exact_duplicate_record_version_ids == (record.envelope.record_version_id,)


def test_batch_unknown_parent_cycle_hash_and_limit_negative_matrix() -> None:
    base_a = _record(CASE_IDS[0])
    base_b = _record("PIT-C03-VALID-PUBLIC-TRADE")
    unknown_envelope = replace(
        base_a.envelope, lineage_parent_ids=("record:synthetic:unknown",)
    )
    unknown = replace(base_a, envelope=unknown_envelope)
    assert "LINEAGE_PARENT_UNKNOWN" in pit.validate_record_batch([unknown]).error_codes

    envelope_a = replace(
        base_a.envelope,
        record_version_id="record:synthetic:cycle:a",
        lineage_parent_ids=("record:synthetic:cycle:b",),
    )
    envelope_b = replace(
        base_b.envelope,
        record_version_id="record:synthetic:cycle:b",
        lineage_parent_ids=("record:synthetic:cycle:a",),
    )
    cycle = pit.validate_record_batch(
        [replace(base_a, envelope=envelope_a), replace(base_b, envelope=envelope_b)]
    )
    assert "LINEAGE_CYCLE" in cycle.error_codes
    assert "RECORD_VERSION_HASH_COLLISION_OR_MISMATCH" in cycle.error_codes

    too_many = pit.validate_record_batch([base_a] * 257)
    assert "RECORD_BATCH_LIMIT_EXCEEDED" in too_many.error_codes


def test_invalid_record_id_marker_is_not_returned_in_batch_output() -> None:
    original = _record(CASE_IDS[0])
    marker = "record:synthetic:BATCH_OUTPUT_MARKER"
    tampered = replace(
        original,
        envelope=replace(original.envelope, record_version_id=marker),
    )
    result = pit.validate_record_batch([tampered])
    assert result.is_valid is False
    assert result.accepted_record_version_ids == ()
    assert result.quarantined_record_version_ids == ()
    assert marker not in _recursive_text(asdict(result))


def test_batch_backdated_and_identity_changing_correction_rejected() -> None:
    parent = _record(CASE_IDS[0])
    wrapper = pit.load_synthetic_case_input("PIT-C20-INVALID-CORRECTION-BACKDATE")
    correction_result = pit.build_market_observation(wrapper["correction_input"])
    assert correction_result.is_valid and correction_result.record is not None
    batch = pit.validate_record_batch([parent, correction_result.record])
    assert batch.error_codes == ("CORRECTION_VISIBILITY_VIOLATION",)

    correction = _record("PIT-C08-VALID-PROJECT-CORRECTION")
    changed = replace(correction, market_id="market:synthetic:changed")
    batch = pit.validate_record_batch([parent, changed])
    assert "ID_DERIVATION_MISMATCH" in batch.error_codes
    assert "RECORD_VERSION_HASH_COLLISION_OR_MISMATCH" in batch.error_codes
    assert changed.envelope.record_version_id not in batch.accepted_record_version_ids


def test_exact_and_semantic_duplicate_mismatch_rejected() -> None:
    parent = _record(CASE_IDS[0])
    exact = _record("PIT-C10-VALID-EXACT-DUPLICATE")
    wrong_exact = replace(exact, canonical_payload_json='{"different":"content"}')
    result = pit.validate_record_batch([parent, wrong_exact])
    assert "RECORD_VERSION_HASH_COLLISION_OR_MISMATCH" in result.error_codes
    collision = pit.validate_record_batch([exact, wrong_exact])
    assert "RECORD_VERSION_HASH_COLLISION_OR_MISMATCH" in collision.error_codes

    semantic = _record("PIT-C11-VALID-SEMANTIC-DUPLICATE")
    wrong_semantic = replace(semantic, market_id="market:synthetic:other")
    result = pit.validate_record_batch([parent, wrong_semantic])
    assert "ID_DERIVATION_MISMATCH" in result.error_codes
    assert "RECORD_VERSION_HASH_COLLISION_OR_MISMATCH" in result.error_codes


@pytest.mark.parametrize(
    ("mutation", "expected_code"),
    (
        (
            lambda record: replace(record, source_id="source:synthetic:changed"),
            "ID_DERIVATION_MISMATCH",
        ),
        (lambda record: replace(record, source_type="UNSUPPORTED"), "SOURCE_TYPE_UNSUPPORTED"),
        (
            lambda record: replace(record, access_classification="PRIVATE"),
            "ACCESS_CLASSIFICATION_FORBIDDEN",
        ),
        (
            lambda record: replace(
                record, source_reference="https://example.invalid/wp156/source-v2"
            ),
            "ID_DERIVATION_MISMATCH",
        ),
        (
            lambda record: replace(record, source_reference="/synthetic/path"),
            "FIELD_TYPE_INVALID",
        ),
        (
            lambda record: replace(record, media_type="application/synthetic+json"),
            "ID_DERIVATION_MISMATCH",
        ),
        (
            lambda record: replace(record, raw_content_sha256="9" * 64),
            "ID_DERIVATION_MISMATCH",
        ),
        (
            lambda record: replace(record, byte_length=129),
            "ID_DERIVATION_MISMATCH",
        ),
        (
            lambda record: replace(record, byte_length=True),
            "FIELD_TYPE_INVALID",
        ),
        (
            lambda record: replace(record, retrieval_method="SYNTHETIC_IN_MEMORY_V2"),
            "ID_DERIVATION_MISMATCH",
        ),
        (
            lambda record: replace(record, retrieval_version="retrieval:wp156:v2"),
            "ID_DERIVATION_MISMATCH",
        ),
        (
            lambda record: replace(record, upstream_revision="revision:synthetic:2"),
            "ID_DERIVATION_MISMATCH",
        ),
        (
            lambda record: replace(
                record, prior_source_snapshot_id="srcsnap:synthetic:prior"
            ),
            "ID_DERIVATION_MISMATCH",
        ),
        (
            lambda record: replace(
                record,
                envelope=replace(
                    record.envelope,
                    ingestion_batch_id="batch:synthetic:wp156:v2",
                ),
            ),
            "ID_DERIVATION_MISMATCH",
        ),
        (
            lambda record: replace(
                record,
                canonical_payload_json=(
                    '{"content_class":"SANITIZED_SYNTHETIC",'
                    '"source_notice":"Changed synthetic notice."}'
                ),
            ),
            "ID_DERIVATION_MISMATCH",
        ),
    ),
)
def test_source_snapshot_replace_tamper_matrix_fails_closed(
    mutation, expected_code: str
) -> None:
    original = _record(CASE_IDS[3])
    tampered = mutation(original)
    _assert_batch_rejects_record(
        tampered, expected_code, "RECORD_VERSION_HASH_COLLISION_OR_MISMATCH"
    )
    assert pit.validate_record_batch([original]).is_valid is True


@pytest.mark.parametrize(
    ("mutation", "expected_code"),
    (
        (
            lambda record: replace(record, platform_id="platform:synthetic:v2"),
            "ID_DERIVATION_MISMATCH",
        ),
        (
            lambda record: replace(record, event_id="event:synthetic:changed"),
            "ID_DERIVATION_MISMATCH",
        ),
        (
            lambda record: replace(record, market_id="market:synthetic:changed"),
            "ID_DERIVATION_MISMATCH",
        ),
        (
            lambda record: replace(
                record,
                resolution_source_id="resolution-source:synthetic:secondary",
            ),
            "ID_DERIVATION_MISMATCH",
        ),
        (
            lambda record: replace(
                record, source_snapshot_id="srcsnap:synthetic:changed"
            ),
            "ID_DERIVATION_MISMATCH",
        ),
        (
            lambda record: replace(record, rule_content_sha256="9" * 64),
            "ID_DERIVATION_MISMATCH",
        ),
        (
            lambda record: replace(
                record, source_declared_effective_time="2026-01-01T00:00:02Z"
            ),
            "ID_DERIVATION_MISMATCH",
        ),
        (
            lambda record: replace(record, ambiguity_labels=("SOURCE_AMBIGUOUS",)),
            "CONFLICT_REQUIRES_HUMAN_REVIEW",
        ),
        (
            lambda record: replace(
                record, source_hierarchy_rank="SECONDARY_OFFICIAL_SOURCE"
            ),
            "ID_DERIVATION_MISMATCH",
        ),
        (
            lambda record: replace(
                record, human_review_state="REVIEWED_ACKNOWLEDGED"
            ),
            "ID_DERIVATION_MISMATCH",
        ),
        (
            lambda record: replace(
                record, ambiguity_labels=("CONFLICTING_SOURCE_TEXT",)
            ),
            "CONFLICT_REQUIRES_HUMAN_REVIEW",
        ),
        (
            lambda record: replace(
                record,
                ambiguity_labels=("CONFLICTING_SOURCE_TEXT",),
                envelope=replace(record.envelope, classification="CONFLICT"),
            ),
            "CONFLICT_REQUIRES_HUMAN_REVIEW",
        ),
        (
            lambda record: replace(
                record,
                envelope=replace(
                    record.envelope,
                    ingestion_batch_id="batch:synthetic:wp156:v2",
                ),
            ),
            "ID_DERIVATION_MISMATCH",
        ),
        (
            lambda record: replace(
                record,
                canonical_payload_json=(
                    '{"normalized_rule_summary":"Changed synthetic rule.",'
                    '"sanitized":true}'
                ),
            ),
            "ID_DERIVATION_MISMATCH",
        ),
    ),
)
def test_resolution_rule_replace_tamper_matrix_fails_closed(
    mutation, expected_code: str
) -> None:
    original = _record(CASE_IDS[4])
    tampered = mutation(original)
    _assert_batch_rejects_record(
        tampered, expected_code, "RECORD_VERSION_HASH_COLLISION_OR_MISMATCH"
    )
    assert pit.validate_record_batch([original]).is_valid is True


@pytest.mark.parametrize(
    "mutation",
    (
        lambda record: replace(record, observation_kind="MARKET_METADATA"),
        lambda record: replace(record, platform_id="platform:synthetic:changed"),
        lambda record: replace(record, event_id="event:synthetic:changed"),
        lambda record: replace(
            record, source_assertion_id="assertion:book:changed"
        ),
        lambda record: replace(record, market_id="market:synthetic:changed"),
        lambda record: replace(record, token_id="token:synthetic:no"),
        lambda record: replace(record, source_id="source:synthetic:changed"),
        lambda record: replace(
            record,
            envelope=replace(
                record.envelope, ingestion_batch_id="batch:synthetic:wp156:v2"
            ),
        ),
        lambda record: replace(
            record,
            envelope=replace(record.envelope, human_review_required=True),
        ),
        lambda record: replace(
            record,
            envelope=replace(record.envelope, advisory_only=False),
        ),
        lambda record: replace(
            record,
            envelope=replace(record.envelope, no_execution_authority=False),
        ),
        lambda record: replace(
            record,
            canonical_payload_json=(
                '{"asks":[],"bids":[],"minimum_order_size":"1","tick_size":"0.02"}'
            ),
        ),
        lambda record: replace(
            record,
            envelope=replace(
                record.envelope, canonical_payload_sha256="0" * 64
            ),
        ),
    ),
)
def test_market_and_envelope_replace_tamper_matrix_fails_closed(mutation) -> None:
    original = _record(CASE_IDS[1])
    tampered = mutation(original)
    _assert_batch_rejects_record(
        tampered, "RECORD_VERSION_HASH_COLLISION_OR_MISMATCH"
    )
    assert pit.validate_record_batch([original]).is_valid is True


@pytest.mark.parametrize(
    "mutation",
    (
        lambda envelope: replace(
            envelope, record_version_id="record:sha256:" + "0" * 64
        ),
        lambda envelope: replace(envelope, schema_id="unsupported-schema"),
        lambda envelope: replace(envelope, schema_version="9.9.9"),
        lambda envelope: replace(envelope, record_family="SOURCE_SNAPSHOT"),
        lambda envelope: replace(
            envelope, observation_id="obs:sha256:" + "0" * 64
        ),
        lambda envelope: replace(envelope, snapshot_id="snapshot:synthetic:changed"),
        lambda envelope: replace(
            envelope, source_snapshot_id="srcsnap:synthetic:changed"
        ),
        lambda envelope: replace(
            envelope, resolution_rule_snapshot_id="rulesnap:synthetic:changed"
        ),
        lambda envelope: replace(
            envelope, ingestion_batch_id="batch:synthetic:changed"
        ),
        lambda envelope: replace(envelope, event_time="2026-01-01T00:00:04Z"),
        lambda envelope: replace(envelope, observed_time="2026-01-01T00:00:04Z"),
        lambda envelope: replace(envelope, ingestion_time="2026-01-01T00:00:07Z"),
        lambda envelope: replace(envelope, lifecycle_state="SUPERSEDED"),
        lambda envelope: replace(envelope, classification="LATE_ARRIVAL"),
        lambda envelope: replace(
            envelope,
            supersedes_record_version_id="record:sha256:" + "1" * 64,
        ),
        lambda envelope: replace(
            envelope, lineage_parent_ids=("record:sha256:" + "1" * 64,)
        ),
        lambda envelope: replace(envelope, canonical_payload_sha256="0" * 64),
        lambda envelope: replace(envelope, source_content_sha256="1" * 64),
        lambda envelope: replace(
            envelope, normalizer_version="normalizer:wp156:v2"
        ),
        lambda envelope: replace(envelope, validator_version="validator:wp156:v2"),
        lambda envelope: replace(
            envelope, parameter_set_id="parameters:wp156:synthetic:v2"
        ),
        lambda envelope: replace(envelope, human_review_required=True),
        lambda envelope: replace(envelope, advisory_only=False),
        lambda envelope: replace(envelope, no_execution_authority=False),
    ),
)
def test_every_envelope_integrity_field_tamper_fails_closed(mutation) -> None:
    original = _record(CASE_IDS[1])
    tampered = replace(original, envelope=mutation(original.envelope))
    _assert_batch_rejects_record(
        tampered, "RECORD_VERSION_HASH_COLLISION_OR_MISMATCH"
    )


@pytest.mark.parametrize(
    ("case_id", "mutation"),
    (
        (
            CASE_IDS[0],
            lambda record: replace(
                record, source_assertion_id="assertion:metadata:changed"
            ),
        ),
        (
            CASE_IDS[3],
            lambda record: replace(
                record,
                source_reference="https://example.invalid/wp156/source-changed",
            ),
        ),
        (
            CASE_IDS[4],
            lambda record: replace(
                record, source_hierarchy_rank="SECONDARY_OFFICIAL_SOURCE"
            ),
        ),
    ),
)
def test_same_id_different_content_single_and_paired_records_fail_closed(
    case_id: str, mutation
) -> None:
    original = _record(case_id)
    tampered = mutation(original)
    assert tampered.envelope.record_version_id == original.envelope.record_version_id
    single = _assert_batch_rejects_record(
        tampered, "RECORD_VERSION_HASH_COLLISION_OR_MISMATCH"
    )
    assert single.accepted_record_version_ids == ()
    paired = pit.validate_record_batch([original, tampered])
    assert paired.is_valid is False
    assert "RECORD_VERSION_HASH_COLLISION_OR_MISMATCH" in paired.error_codes
    assert original.envelope.record_version_id not in paired.accepted_record_version_ids
    assert original.envelope.record_version_id in paired.quarantined_record_version_ids


@pytest.mark.parametrize(
    ("case_id", "field_name", "new_value", "builder"),
    (
        (
            CASE_IDS[0],
            "source_assertion_id",
            "assertion:metadata:changed",
            pit.build_market_observation,
        ),
        (
            CASE_IDS[3],
            "source_reference",
            "https://example.invalid/wp156/source-changed",
            pit.build_source_snapshot,
        ),
        (
            CASE_IDS[4],
            "source_hierarchy_rank",
            "SECONDARY_OFFICIAL_SOURCE",
            pit.build_resolution_rule_snapshot,
        ),
    ),
)
def test_valid_metadata_mutation_changes_record_version_id(
    case_id: str, field_name: str, new_value: object, builder
) -> None:
    original = _record(case_id)
    candidate = pit.load_synthetic_case_input(case_id)
    candidate[field_name] = new_value
    changed = builder(candidate)
    assert changed.is_valid is True
    assert changed.record is not None
    assert changed.record.envelope.record_version_id != original.envelope.record_version_id


def test_fixed_valid_and_tampered_batch_hashes_are_exact() -> None:
    valid_records = [
        _record(CASE_IDS[0]),
        _record(CASE_IDS[3]),
        _record(CASE_IDS[4]),
    ]
    valid = pit.validate_record_batch(valid_records)
    tampered_source = replace(
        valid_records[1],
        access_classification="PRIVATE",
    )
    tampered = pit.validate_record_batch([tampered_source])
    assert valid.canonical_batch_sha256 == (
        "82e37102a881cb4a3d60f8cd44f9a5a0abeeb68ae46e02d2a06dbaced0428375"
    )
    assert tampered.canonical_batch_sha256 == (
        "02bf55747a37a0136f2e0f1c857efedb5e4629c779be79fb47c231427aa533d5"
    )


def test_identical_second_execution_is_byte_and_hash_equal_and_inputs_unchanged() -> None:
    caller = pit.load_synthetic_case_input(CASE_IDS[0])
    before = pit.canonical_json_bytes(caller)
    first = pit.build_market_observation(caller)
    second = pit.build_market_observation(caller)
    assert first == second
    assert first.record == second.record
    assert pit.canonical_json_bytes(caller) == before


def test_no_files_created_and_no_side_effect_calls(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)

    def forbidden(*args, **kwargs):
        raise AssertionError("SIDE_EFFECT_CALL_FORBIDDEN")

    monkeypatch.setattr("builtins.open", forbidden)
    result = pit.build_market_observation(
        pit.load_synthetic_case_input(CASE_IDS[0])
    )
    assert result.is_valid
    assert list(tmp_path.iterdir()) == []


def test_source_ast_has_no_forbidden_imports_or_calls() -> None:
    forbidden_import_roots = {
        "os",
        "pathlib",
        "socket",
        "subprocess",
        "requests",
        "urllib",
        "http",
        "random",
        "uuid",
        "time",
        "pydantic",
        "pyarrow",
        "parquet",
        "duckdb",
        "polars",
    }
    forbidden_calls = {
        "open",
        "eval",
        "exec",
        "compile",
        "datetime.now",
        "datetime.utcnow",
        "time.time",
        "os.getenv",
        "os.environ",
    }
    for path in sorted(SOURCE_DIR.glob("*.py")):
        # WP161's manifest store and WP163's durable record store both realize an
        # exact explicit-path SQLite boundary requiring only these two stdlib path
        # modules; every earlier source module retains the original
        # side-effect-free import prohibition.
        wp161_path_imports = (
            {"os", "pathlib"}
            if path.name in ("manifest_store.py", "record_store.py")
            else set()
        )
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                assert not {
                    alias.name.split(".")[0] for alias in node.names
                } & (forbidden_import_roots - wp161_path_imports)
            if isinstance(node, ast.ImportFrom) and node.module:
                assert node.module.split(".")[0] not in (
                    forbidden_import_roots - wp161_path_imports
                )
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    call_name = node.func.id
                elif isinstance(node.func, ast.Attribute) and isinstance(
                    node.func.value, ast.Name
                ):
                    call_name = f"{node.func.value.id}.{node.func.attr}"
                else:
                    call_name = ""
                assert call_name not in forbidden_calls


def test_no_writer_reader_collector_query_or_migration_public_behavior() -> None:
    # WP157 introduces the only authorized public surface whose names contain
    # "query"/"as_of": a bounded in-memory reconstruction with no writer,
    # reader, collector, poller, persistence, scheduler, or execution behavior.
    authorized_query_surface = {
        "AS_OF_QUERY_LABEL",
        "AS_OF_QUERY_POSTURE",
        "SUPPORTED_CUTOFF_MODES",
        "SUPPORTED_RESULT_VIEWS",
        "QUERY_STATUSES",
        "EXCLUSION_REASONS",
        "EventTimeWindow",
        "PointInTimeQuerySpec",
        "PointInTimeQueryReceipt",
        "PointInTimeRecordSetResult",
        "SyntheticAsOfQueryCase",
        "query_point_in_time_record_set",
        "get_synthetic_as_of_query_cases",
        "load_synthetic_as_of_query_case",
    }
    exported = set(pit.__all__)
    # WP161/WP162 introduce the only authorized persistence-adjacent public
    # surface: the bounded local SQLite manifest store and the deterministic
    # WP156/WP157 -> WP160 -> WP161 dataset persistence/registration adapters.
    # These append no writer, reader, collector, poller, scheduler, or execution
    # behavior to the WP156 records layer itself.
    authorized_persistence_surface = {
        "MANIFEST_STORE_LABEL",
        "MANIFEST_STORE_POSTURE",
        "MANIFEST_STORE_FORMAT_ID",
        "MANIFEST_STORE_SCHEMA_VERSION",
        "MANIFEST_STORE_STATUSES",
        "MANIFEST_STORE_ERROR_CODES",
        "ManifestStoreSnapshot",
        "ManifestStoreResult",
        "initialize_manifest_store",
        "append_manifest_store_batch",
        "load_and_verify_manifest_store",
        "DATASET_PERSISTENCE_ADAPTER_LABEL",
        "DATASET_PERSISTENCE_ADAPTER_POSTURE",
        "DATASET_PERSISTENCE_ADAPTER_STATUSES",
        "DATASET_PERSISTENCE_ADAPTER_ERROR_CODES",
        "DatasetPersistenceAdapterResult",
        "persist_validated_record_batch_snapshot",
        "persist_as_of_query_snapshot",
    }
    persistence_fragments = (
        "write",
        "read",
        "collect",
        "poll",
        "migrate",
        "persist",
        "schedule",
        "execute",
    )
    assert not any(
        fragment in name.lower()
        for name in exported - authorized_persistence_surface
        for fragment in persistence_fragments
    )
    query_named = {
        name
        for name in exported - authorized_persistence_surface
        if "query" in name.lower() or "as_of" in name.lower()
    }
    assert query_named
    assert query_named <= authorized_query_surface


def test_legacy_polymarket_snapshot_modules_are_unchanged_by_wp156_diff() -> None:
    import subprocess

    diff = subprocess.run(
        ["git", "diff", "--name-only", "origin/main"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    ).stdout.splitlines()
    assert not any(
        path.replace("\\", "/").startswith("src/data_layer/polymarket/")
        for path in diff
    )


def test_canonical_docs_status_deferred_and_repo_truth_are_exactly_registered() -> None:
    canonical = (
        ROOT
        / "docs"
        / "point_in_time_observation_schema_validator_and_synthetic_fixture_implementation.md"
    ).read_text(encoding="utf-8")
    status = (ROOT / "docs" / "status_entries" / "WP156.md").read_text(
        encoding="utf-8"
    )
    deferred = (ROOT / "docs" / "deferred_items_log.md").read_text(
        encoding="utf-8"
    )
    index = (ROOT / "docs" / "repo_truth_index.md").read_text(encoding="utf-8")
    for token in (
        "LOCAL_OFFLINE_STDLIB_ONLY_IN_MEMORY_VALIDATION",
        "WP157 requires separate approval",
        "WP157 requires separate approval and is not implemented",
        "Product/runtime network",
        "exactly 16 files",
        "record_specific_metadata_sha256",
        "All six optional caller-derived public fields",
        "Follow-up required: YES",
        "Preventable: YES",
        "Defect categories: F",
    ):
        assert token in f"{canonical}\n{status}"
    for item_id in ("WP155-D001", "WP155-D002", "WP155-D003"):
        assert item_id in deferred
    for item_id in (f"WP156-D{index:03d}" for index in range(1, 11)):
        assert item_id in deferred
    for path in (
        "docs/point_in_time_observation_schema_validator_and_synthetic_fixture_implementation.md",
        "docs/status_entries/WP156.md",
        "src/data_layer/point_in_time_market_research/",
        "tests/data_layer/point_in_time_market_research/test_records_and_synthetic_corpus.py",
    ):
        assert path in index


def test_exact_seventeen_file_wp157_scope() -> None:
    # WP156 is merged; WP157 is the current review target. The prior WP156
    # branch-scope guard failed on merged main (empty diff against origin/main),
    # which is the clean-main proof that successor maintenance is required.
    import subprocess

    merged = subprocess.run(
        ["git", "cat-file", "-e", "origin/main:docs/status_entries/WP157.md"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if merged.returncode == 0:
        # Once WP157 is present on origin/main, successor WPs own their own
        # exact-scope guards; the WP157 branch-scope assertion no longer applies
        # to an empty or successor diff.
        return

    changed = subprocess.run(
        ["git", "diff", "--name-only", "origin/main"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    ).stdout.splitlines()
    untracked = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    ).stdout.splitlines()
    actual = {path.replace("\\", "/") for path in changed + untracked if path}
    assert actual == {
        "docs/bounded_in_memory_point_in_time_record_set_reconstruction_and_as_of_query_implementation.md",
        "docs/deferred_items_log.md",
        "docs/project_status.md",
        "docs/repo_truth_index.md",
        "docs/status_entries/WP157.md",
        "src/data_layer/point_in_time_market_research/__init__.py",
        "src/data_layer/point_in_time_market_research/as_of_query.py",
        "src/data_layer/point_in_time_market_research/as_of_synthetic_cases.py",
        "src/data_layer/point_in_time_market_research/records.py",
        "tests/data_layer/point_in_time_market_research/test_as_of_query.py",
        "tests/data_layer/point_in_time_market_research/test_records_and_synthetic_corpus.py",
        "tests/test_adoption_architecture_dependency_registry_and_alpha_factory_roadmap_lock_in_docs.py",
        "tests/test_hermes_research_prompt_pack_operator_runbooks_docs.py",
        "tests/test_local_research_workflow_value_measurement_harness_contract_docs.py",
        "tests/test_point_in_time_market_research_data_foundation_contract_docs.py",
        "tests/test_project_status_docs.py",
        "tests/test_wallet_intelligence_architecture_contract_docs.py",
    }
