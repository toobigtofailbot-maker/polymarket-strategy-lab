"""Focused tests for the WP167 external-history provenance descriptor.

Local, offline, deterministic, in-memory. Descriptor identity is recomputed
independently of the module under test to prove the canonical preimage, and the
negative matrix covers ordering, byte mutation, path exclusion, source class,
timestamp, and vocabulary faults with closed, non-echoing error codes.
"""

from __future__ import annotations

import dataclasses

from src.data_layer.point_in_time_market_research import (
    canonical_json_bytes,
    sha256_hex,
)
import src.data_layer.analytical_research as ar
from src.data_layer.analytical_research.external_dataset import (
    EXTERNAL_DATASET_ID_PREFIX,
    EXTERNAL_DATASET_SCHEMA_ID,
    EXTERNAL_DATASET_SCHEMA_VERSION,
    ExternalSourceObject,
    build_external_dataset_descriptor,
)


def _obj(name, sha_digit="1", byte_length=10, partition="p"):
    return ExternalSourceObject(
        object_name=name,
        source_sha256=sha_digit * 64,
        byte_length=byte_length,
        partition_identity=partition,
    )


def _base(**overrides):
    fields = dict(
        provider_id="pmxt",
        dataset_name="pmxt_polymarket_orderbook_archive",
        dataset_version="v2",
        source_class="THIRD_PARTY_NATIVE_FRAME_ARCHIVE",
        coverage_start="2026-04-13T19:00:00Z",
        coverage_end="2026-04-13T20:00:00Z",
        source_objects=[_obj("a.parquet", "1"), _obj("b.parquet", "2", 20, "p2")],
        source_schema_fingerprint_sha256="f" * 64,
        source_timestamp_semantics="SOURCE_EVENT_TIME_UTC",
        receive_timestamp_semantics="EXPORTER_RECEIVE_TIME_UTC",
        event_types=["book", "price_change"],
        known_gap_policy="AS_CAPTURED",
        quality_tier="RAW_NATIVE",
        importer_id="wp167-pmxt-v2-adapter",
        importer_version="1.0.0",
        license_id="pmxt-archive-terms",
        attribution="pmxt Polymarket Orderbook Archive",
    )
    fields.update(overrides)
    return fields


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


def test_valid_descriptor_is_built():
    result = build_external_dataset_descriptor(**_base())
    assert result.is_valid and result.status == "EXTERNAL_DESCRIPTOR_BUILT"
    descriptor = result.descriptor
    assert descriptor is not None
    assert descriptor.external_dataset_id.startswith(EXTERNAL_DATASET_ID_PREFIX)
    assert descriptor.source_class == "THIRD_PARTY_NATIVE_FRAME_ARCHIVE"
    assert descriptor.advisory_only is True
    assert descriptor.no_execution_authority is True


def test_descriptor_id_matches_independent_recomputation():
    result = build_external_dataset_descriptor(**_base())
    descriptor = result.descriptor
    preimage = {
        "schema_id": EXTERNAL_DATASET_SCHEMA_ID,
        "schema_version": EXTERNAL_DATASET_SCHEMA_VERSION,
        "provider_id": "pmxt",
        "dataset_name": "pmxt_polymarket_orderbook_archive",
        "dataset_version": "v2",
        "source_class": "THIRD_PARTY_NATIVE_FRAME_ARCHIVE",
        "coverage_start": "2026-04-13T19:00:00Z",
        "coverage_end": "2026-04-13T20:00:00Z",
        "source_objects": [
            {"object_name": "a.parquet", "source_sha256": "1" * 64, "byte_length": 10, "partition_identity": "p"},
            {"object_name": "b.parquet", "source_sha256": "2" * 64, "byte_length": 20, "partition_identity": "p2"},
        ],
        "source_schema_fingerprint_sha256": "f" * 64,
        "source_timestamp_semantics": "SOURCE_EVENT_TIME_UTC",
        "receive_timestamp_semantics": "EXPORTER_RECEIVE_TIME_UTC",
        "event_types": ["book", "price_change"],
        "known_gap_policy": "AS_CAPTURED",
        "quality_tier": "RAW_NATIVE",
        "importer_id": "wp167-pmxt-v2-adapter",
        "importer_version": "1.0.0",
        "license_id": "pmxt-archive-terms",
        "attribution": "pmxt Polymarket Orderbook Archive",
        "advisory_only": True,
        "no_execution_authority": True,
    }
    expected = EXTERNAL_DATASET_ID_PREFIX + sha256_hex(canonical_json_bytes(preimage))
    assert descriptor.external_dataset_id == expected


def test_source_object_order_does_not_change_identity():
    forward = build_external_dataset_descriptor(**_base())
    reordered = build_external_dataset_descriptor(
        **_base(source_objects=[_obj("b.parquet", "2", 20, "p2"), _obj("a.parquet", "1")])
    )
    assert (
        forward.descriptor.external_dataset_id
        == reordered.descriptor.external_dataset_id
    )


def test_event_type_order_does_not_change_identity():
    forward = build_external_dataset_descriptor(**_base(event_types=["book", "price_change"]))
    reordered = build_external_dataset_descriptor(**_base(event_types=["price_change", "book"]))
    assert (
        forward.descriptor.external_dataset_id
        == reordered.descriptor.external_dataset_id
    )


def test_source_byte_mutation_changes_identity():
    baseline = build_external_dataset_descriptor(**_base())
    mutated = build_external_dataset_descriptor(
        **_base(source_objects=[_obj("a.parquet", "9"), _obj("b.parquet", "2", 20, "p2")])
    )
    assert (
        baseline.descriptor.external_dataset_id
        != mutated.descriptor.external_dataset_id
    )


def test_absolute_path_object_name_is_rejected():
    result = build_external_dataset_descriptor(
        **_base(source_objects=[_obj("/etc/passwd", "1")])
    )
    assert result.error_codes == ("EXTERNAL_SOURCE_FILE_INVALID",)


def test_backslash_object_name_is_rejected():
    result = build_external_dataset_descriptor(
        **_base(source_objects=[_obj("C:\\\\x.parquet", "1")])
    )
    assert result.error_codes == ("EXTERNAL_SOURCE_FILE_INVALID",)


def test_duplicate_object_name_is_rejected():
    result = build_external_dataset_descriptor(
        **_base(source_objects=[_obj("a.parquet", "1"), _obj("a.parquet", "2")])
    )
    assert result.error_codes == ("EXTERNAL_SOURCE_FILE_INVALID",)


def test_empty_source_objects_is_rejected():
    result = build_external_dataset_descriptor(**_base(source_objects=[]))
    assert result.error_codes == ("EXTERNAL_SOURCE_FILE_INVALID",)


def test_invalid_source_class_is_rejected():
    result = build_external_dataset_descriptor(**_base(source_class="MADE_UP_CLASS"))
    assert result.error_codes == ("EXTERNAL_DESCRIPTOR_INVALID",)


def test_non_utc_coverage_is_rejected():
    result = build_external_dataset_descriptor(
        **_base(coverage_start="2026-04-13T19:00:00-05:00")
    )
    assert result.error_codes == ("EXTERNAL_SOURCE_TIMESTAMP_INVALID",)


def test_reversed_coverage_window_is_rejected():
    result = build_external_dataset_descriptor(
        **_base(coverage_start="2026-04-13T21:00:00Z", coverage_end="2026-04-13T20:00:00Z")
    )
    assert result.error_codes == ("EXTERNAL_SOURCE_TIMESTAMP_INVALID",)


def test_empty_event_types_is_rejected():
    result = build_external_dataset_descriptor(**_base(event_types=[]))
    assert result.error_codes == ("EXTERNAL_SOURCE_EVENT_INVALID",)


def test_bad_schema_fingerprint_is_rejected():
    result = build_external_dataset_descriptor(
        **_base(source_schema_fingerprint_sha256="not-a-sha")
    )
    assert result.error_codes == ("EXTERNAL_DESCRIPTOR_INVALID",)


def test_rejected_result_carries_only_closed_codes():
    result = build_external_dataset_descriptor(**_base(source_class="/secret/path"))
    assert not result.is_valid and result.descriptor is None
    for text in _all_strings(result):
        assert "/secret/path" not in text
        assert text in ar.EXTERNAL_DATASET_ERROR_CODES or text in ("EXTERNAL_REJECTED",)


def test_reordered_inputs_produce_equal_complete_descriptors():
    forward = build_external_dataset_descriptor(
        **_base(
            source_objects=[_obj("a.parquet", "1"), _obj("b.parquet", "2", 20, "p2")],
            event_types=["book", "price_change"],
        )
    ).descriptor
    reordered = build_external_dataset_descriptor(
        **_base(
            source_objects=[_obj("b.parquet", "2", 20, "p2"), _obj("a.parquet", "1")],
            event_types=["price_change", "book"],
        )
    ).descriptor
    # Not merely equal ids: the full frozen descriptors are structurally equal.
    assert forward == reordered
    assert forward.source_objects == reordered.source_objects
    assert forward.event_types == reordered.event_types
    assert list(forward.source_objects) == sorted(forward.source_objects, key=lambda e: e.object_name)
    assert list(forward.event_types) == sorted(forward.event_types)
