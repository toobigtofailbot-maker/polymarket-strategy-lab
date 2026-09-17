"""WP170 identity, immutable definition, and predecessor-binding proofs."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
import hashlib
import json

import pytest

import src.data_layer.analytical_research as ar
from src.data_layer.analytical_research import research_dataset as rd
from src.data_layer.point_in_time_market_research import (
    DATASET_REFERENCE_SCHEMA_ID,
    DATASET_REFERENCE_SCHEMA_VERSION,
    build_dataset_snapshot_reference,
    canonical_json_bytes,
    sha256_hex,
)


def source_record_id(value: str) -> str:
    return "record:sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def reference(*, review_conflicts=()):
    all_ids = sorted(source_record_id(value) for value in ("a1", "b2", "c3", "d4", "e5", "f6"))
    review_ids = sorted(review_conflicts)
    preimage = {
        "schema_id": DATASET_REFERENCE_SCHEMA_ID,
        "schema_version": DATASET_REFERENCE_SCHEMA_VERSION,
        "derivation_mode": "VALIDATED_RECORD_BATCH",
        "validated_batch_sha256": "a" * 64,
        "ordinary_record_version_ids": [item for item in all_ids if item not in review_ids],
        "review_conflict_record_version_ids": review_ids,
        "query_spec_sha256": None,
        "query_result_sha256": None,
        "cutoff_mode": None,
        "cutoff_time": None,
        "result_view": None,
        "query_engine_version": None,
        "validator_version": "wp170-test",
        "parameter_set_id": "wp170-test",
        "human_review_required": bool(review_ids),
        "advisory_only": True,
        "no_execution_authority": True,
    }
    mapping = dict(preimage)
    mapping["dataset_snapshot_reference_id"] = "datasetref:sha256:" + sha256_hex(canonical_json_bytes(preimage))
    mapping["created_from_manifest_entry_id"] = None
    result = build_dataset_snapshot_reference(mapping)
    assert result.is_valid
    return result.reference


def feature(**overrides):
    value = {
        "feature_name": "midpoint_change",
        "feature_version": "1.0.0",
        "description": "Past-only midpoint change.",
        "source_dependencies": ["market_observation.best_bid", "market_observation.best_ask"],
        "parameters": {"window_seconds": 60},
        "lookback_rule": "TRAILING_60_SECONDS",
        "availability_rule": "SOURCE_AVAILABILITY_TIME",
        "missing_data_policy": "REJECT_SAMPLE",
        "transformation_version": "wp170-test:1",
        "no_future_information_rule": "FEATURE_AVAILABLE_AT_OR_BEFORE_DECISION_TIME",
    }
    value.update(overrides)
    result = ar.build_feature_definition(value)
    assert result.is_valid, result.error_codes
    return result.record


def label(**overrides):
    value = {
        "label_name": "resolved_binary_outcome",
        "label_version": "1.0.0",
        "prediction_target": "binary resolution",
        "horizon_rule": "MARKET_RESOLUTION_TIME",
        "target_time_rule": "TARGET_EVENT_TIME",
        "outcome_source_rule": "CANONICAL_RESOLUTION_SNAPSHOT",
        "availability_time_rule": "FIRST_CANONICAL_RESOLUTION_OBSERVED_TIME",
        "censoring_rule": "AMBIGUOUS_IS_MISSING",
        "parameters": {"positive": "YES"},
        "code_version": "wp170-test:1",
    }
    value.update(overrides)
    result = ar.build_label_definition(value)
    assert result.is_valid, result.error_codes
    return result.record


def binding():
    result = ar.build_dataset_binding(reference(), None, "commit:test")
    assert result.is_valid, result.error_codes
    return result.record


def _analytical_manifest(ref, physical_hash: str):
    partitions = tuple(
        ar.AnalyticalPartitionManifest(name, f"{name}.parquet", 0, "b" * 64, physical_hash, 1, "c" * 64)
        for name in ar.ANALYTICAL_TABLE_ORDER
    )
    logical_preimage = {
        "analytical_schema_id": ar.ANALYTICAL_DATASET_SCHEMA_ID,
        "analytical_schema_version": ar.ANALYTICAL_SCHEMA_VERSION,
        "source_kind": ar.SOURCE_KIND_CANONICAL_PIT,
        "source_reference_id": ref.dataset_snapshot_reference_id,
        "materializer_version": ar.ANALYTICAL_MATERIALIZER_VERSION,
        "tables": [{"table_name": p.table_name, "row_count": 0, "logical_rows_sha256": "b" * 64} for p in partitions],
    }
    logical_id = ar.ANALYTICAL_LOGICAL_DATASET_ID_PREFIX + hashlib.sha256(rd.analytical_canonical_bytes(logical_preimage)).hexdigest()
    return ar.AnalyticalDatasetManifest(
        ar.ANALYTICAL_DATASET_SCHEMA_ID, ar.ANALYTICAL_DATASET_SCHEMA_VERSION,
        logical_id, ar.SOURCE_KIND_CANONICAL_PIT, ref.dataset_snapshot_reference_id,
        ar.ANALYTICAL_SCHEMA_VERSION, ar.ANALYTICAL_MATERIALIZER_VERSION, partitions, 0,
        ar.EXPECTED_PYARROW_VERSION, ar.EXPECTED_DUCKDB_VERSION,
        ar.EXPECTED_POLARS_VERSION, "3.14.0", True, True,
    )


def test_dataset_binding_revalidates_existing_identities_and_rejects_tamper(tmp_path) -> None:
    ref = reference()
    first = ar.build_dataset_binding(ref, _analytical_manifest(ref, "d" * 64), "commit:test")
    physical_only = ar.build_dataset_binding(ref, _analytical_manifest(ref, "e" * 64), "commit:test")
    assert first.is_valid and physical_only.is_valid
    assert first.record.dataset_binding_id == physical_only.record.dataset_binding_id
    assert first.record.analytical_logical_dataset_id == physical_only.record.analytical_logical_dataset_id
    assert json.loads(first.record.dataset_snapshot_reference_json)[
        "dataset_snapshot_reference_id"
    ] == ref.dataset_snapshot_reference_id
    assert json.loads(first.record.analytical_identity_json)[
        "source_reference_id"
    ] == ref.dataset_snapshot_reference_id
    path = tmp_path / "analytical_binding.sqlite3"
    assert ar.initialize_experiment_registry(path).is_valid
    assert ar.append_experiment_records(path, (first.record,)).is_valid
    tampered = replace(ref, validated_batch_sha256="f" * 64)
    rejected = ar.build_dataset_binding(tampered, None, "commit:test")
    assert rejected.error_codes == ("DATASET_REFERENCE_INVALID",)
    assert rejected.record is None
    analytical_tamper = replace(
        _analytical_manifest(ref, "d" * 64), logical_dataset_id="analytical:sha256:" + "f" * 64,
    )
    assert ar.build_dataset_binding(
        ref, analytical_tamper, "commit:test"
    ).error_codes == ("DATASET_REFERENCE_INVALID",)
    quarantined = reference(review_conflicts=(source_record_id("f6"),))
    assert ar.build_dataset_binding(
        quarantined, None, "commit:test"
    ).error_codes == ("DATASET_REFERENCE_INVALID",)


def test_feature_definition_identity_and_no_future_contract() -> None:
    original = feature()
    reordered = feature(parameters={"window_seconds": 60})
    changed = feature(parameters={"window_seconds": 120})
    assert original.feature_definition_id == reordered.feature_definition_id
    assert original.feature_definition_id != changed.feature_definition_id
    hostile = ar.build_feature_definition({
        "feature_name": "bad", "feature_version": "1", "description": "bad",
        "source_dependencies": ["future.resolved_outcome"], "parameters": {},
        "lookback_rule": "NONE", "availability_rule": "FUTURE",
        "missing_data_policy": "REJECT", "transformation_version": "v",
        "no_future_information_rule": "NONE",
    })
    assert hostile.error_codes == ("FEATURE_TIMING_LEAKAGE",)
    for dependency in ("market.winner", "market.oracleAnswer", "market.settledPayout", "market.marketClosed"):
        blocked = ar.build_feature_definition({
            "feature_name": "bad", "feature_version": "1", "description": "bad",
            "source_dependencies": [dependency], "parameters": {},
            "lookback_rule": "POINT_IN_TIME", "availability_rule": "SOURCE_AVAILABILITY_TIME",
            "missing_data_policy": "REJECT", "transformation_version": "v",
            "no_future_information_rule": "FEATURE_AVAILABLE_AT_OR_BEFORE_DECISION_TIME",
        })
        assert blocked.error_codes == ("FEATURE_TIMING_LEAKAGE",)
    for parameters in (
        {"settlementValue": 1},
        {"nested": ["resolvedOutcome"]},
        {"window_seconds": -1},
    ):
        blocked = ar.build_feature_definition({
            "feature_name": "bad", "feature_version": "1", "description": "bad",
            "source_dependencies": ["market_observation.best_bid"],
            "parameters": parameters, "lookback_rule": "POINT_IN_TIME",
            "availability_rule": "SOURCE_AVAILABILITY_TIME",
            "missing_data_policy": "REJECT", "transformation_version": "v",
            "no_future_information_rule": "FEATURE_AVAILABLE_AT_OR_BEFORE_DECISION_TIME",
        })
        assert blocked.error_codes == ("FEATURE_TIMING_LEAKAGE",)
    with pytest.raises(FrozenInstanceError):
        original.feature_name = "changed"  # type: ignore[misc]
    assert isinstance(original.source_dependencies, tuple)


def test_label_definition_separates_target_and_availability() -> None:
    original = label()
    target_changed = label(target_time_rule="TARGET_PLUS_ONE_DAY")
    availability_changed = label(availability_time_rule="FINAL_RESOLUTION_TIME")
    assert len({original.label_definition_id, target_changed.label_definition_id, availability_changed.label_definition_id}) == 3
    assert original.target_time_rule != original.availability_time_rule
    assert original.parameters_json == '{"positive":"YES"}'


# =============================================================================
# WP175D — ExternalDatasetBinding identity (R009) and canonical binding (R010)
# =============================================================================

from src.data_layer.analytical_research import experiment_os as _os_contract  # noqa: E402


def _external_binding_record(**overrides):
    value = {
        "source_kind": ar.EXTERNAL_DATASET_BINDING_SOURCE_KIND,
        "source_external_dataset_id": "ext:pmxt:test0001",
        "source_lineage_id": "pmxtresearchlineage:sha256:" + "a" * 64,
        "source_membership_digest": "b" * 64,
        "source_member_count": 3,
        "instrument_id": "0x" + "c" * 64 + "-123.POLYMARKET",
        "conversion_policy_version": "wp168-nautilus-pmxt-v2-conversion/1.0.0",
        "first_event_time_ns": 1_000_000_000,
        "last_event_time_ns": 2_000_000_000,
        "first_availability_time_ns": 1_005_000_000,
        "last_availability_time_ns": 2_005_000_000,
        "code_version": "commit:test",
    }
    value.update(overrides)
    result = ar.build_external_dataset_binding(
        value["source_kind"], value["source_external_dataset_id"], value["source_lineage_id"],
        value["source_membership_digest"], value["source_member_count"], value["instrument_id"],
        value["conversion_policy_version"], value["first_event_time_ns"], value["last_event_time_ns"],
        value["first_availability_time_ns"], value["last_availability_time_ns"], value["code_version"],
    )
    return result


def _validate_record(record):
    try:
        _os_contract._validate_public_record(record)
        return None
    except _os_contract._Failure as failure:
        return failure.code


def test_external_binding_identity_one_field_tamper() -> None:
    """R009: identity binds every semantic field; one-field tamper fails closed."""
    result = _external_binding_record()
    assert result.is_valid, result.error_codes
    binding = result.record
    assert isinstance(binding, ar.ExternalDatasetBinding)
    assert binding.dataset_binding_id.startswith("datasetbinding:sha256:")
    assert binding.schema_id == ar.EXTERNAL_DATASET_BINDING_SCHEMA_ID
    assert binding.advisory_only is True and binding.no_execution_authority is True
    # It is not a canonical DatasetBinding and carries no snapshot reference.
    assert not isinstance(binding, ar.DatasetBinding)
    assert _validate_record(binding) is None

    # Every semantic field participates in the content-addressed id: tampering any
    # one (without recomputing the id) fails the closed identity recomputation.
    tampers = {
        "source_external_dataset_id": "ext:pmxt:OTHER",
        "source_lineage_id": "pmxtresearchlineage:sha256:" + "9" * 64,
        "source_membership_digest": "0" * 64,
        "source_member_count": 4,
        "instrument_id": "0x" + "d" * 64 + "-999.POLYMARKET",
        "conversion_policy_version": "wp168-nautilus-pmxt-v2-conversion/9.9.9",
        "first_event_time_ns": 999,
        "last_event_time_ns": 3_000_000_000,
        "first_availability_time_ns": 1,
        "last_availability_time_ns": 3_000_000_000,
        "code_version": "commit:other",
    }
    for field_name, new_value in tampers.items():
        tampered = replace(binding, **{field_name: new_value})
        assert _validate_record(tampered) == "IDENTITY_DERIVATION_MISMATCH", field_name

    # A distinct lineage yields a distinct binding id (identity is closed).
    other = _external_binding_record(source_lineage_id="pmxtresearchlineage:sha256:" + "e" * 64)
    assert other.record.dataset_binding_id != binding.dataset_binding_id
    # Wrong source_kind (canonical-PIT masquerade) is rejected at construction.
    assert ar.build_external_dataset_binding(
        ar.SOURCE_KIND_CANONICAL_PIT, "ext:pmxt:test0001",
        "pmxtresearchlineage:sha256:" + "a" * 64, "b" * 64, 3,
        "0x" + "c" * 64 + "-123.POLYMARKET", "wp168-x/1.0.0",
        1, 2, 1, 2, "commit:test",
    ).error_codes == ("FIELD_VALUE_INVALID",)


def test_canonical_dataset_binding_unchanged() -> None:
    """R010: canonical DatasetBinding fields, signature, and identity are unchanged."""
    import inspect

    assert [f.name for f in __import__("dataclasses").fields(ar.DatasetBinding)] == [
        "schema_id", "schema_version", "dataset_binding_id", "dataset_snapshot_reference_id",
        "dataset_snapshot_reference_json", "dataset_reference_schema_version",
        "analytical_logical_dataset_id", "analytical_identity_json", "analytical_schema_version",
        "materializer_version", "source_reference_id", "code_version", "advisory_only",
        "no_execution_authority",
    ]
    signature = inspect.signature(ar.build_dataset_binding)
    assert list(signature.parameters) == ["reference", "analytical_manifest", "code_version"]
    first = binding()
    second = binding()
    assert first == second  # deterministic identity
    assert first.schema_id == "polymarket-experiment-dataset-binding"
    assert first.dataset_binding_id.startswith("datasetbinding:sha256:")
    # The external binding subtype never collides with the canonical schema id.
    assert first.schema_id != ar.EXTERNAL_DATASET_BINDING_SCHEMA_ID
