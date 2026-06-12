"""Focused tests for the WP67 calibration record schema validator.

Tests cover: valid example schema, missing required fields, invalid enum values,
forbidden trading/performance keys, type checks, determinism/immutability,
and module safety constraints (no network imports, no file writes, no
local_data/.env reads).
"""

from __future__ import annotations

import copy
import importlib
import json
import pathlib
import sys
import types

import pytest

from src.data_layer.calibration_record_validation import (
    ALLOWED_HUMAN_REVIEW_USEFULNESS_LABELS,
    ALLOWED_RESEARCH_QUEUE_BUCKETS,
    ALLOWED_RESOLUTION_SOURCE_TYPES,
    ALLOWED_RESOLUTION_STATUSES,
    ALLOWED_SNAPSHOT_OFFSETS,
    FORBIDDEN_KEY_NAMES,
    CalibrationRecordValidationResult,
    validate_calibration_record,
)

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
EXAMPLE_SCHEMA = REPO_ROOT / "docs" / "schemas" / "calibration_record_v1.example.json"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _load_example() -> dict:
    return json.loads(EXAMPLE_SCHEMA.read_text(encoding="utf-8"))


def _valid_record() -> dict:
    """Return a deep copy of the valid example record."""
    return _load_example()


def _drop(record: dict, *dotted_keys: str) -> dict:
    """Remove dotted keys like 'identity.market_id' from a deep copy."""
    r = copy.deepcopy(record)
    for dotted in dotted_keys:
        parts = dotted.split(".", 1)
        if len(parts) == 1:
            r.pop(parts[0], None)
        else:
            sub = r.get(parts[0])
            if isinstance(sub, dict):
                sub.pop(parts[1], None)
    return r


def _set(record: dict, dotted_key: str, value: object) -> dict:
    """Set a dotted key like 'identity.market_id' in a deep copy."""
    r = copy.deepcopy(record)
    parts = dotted_key.split(".", 1)
    if len(parts) == 1:
        r[parts[0]] = value
    else:
        if parts[0] not in r or not isinstance(r[parts[0]], dict):
            r[parts[0]] = {}
        r[parts[0]][parts[1]] = value
    return r


# ---------------------------------------------------------------------------
# Test 1: Valid example schema passes
# ---------------------------------------------------------------------------


def test_valid_example_schema_passes():
    record = _valid_record()
    result = validate_calibration_record(record)
    assert result.is_valid, (
        f"Expected valid example to pass. "
        f"missing={result.missing_required_fields}, invalid={result.invalid_fields}"
    )
    assert result.missing_required_fields == ()
    assert result.invalid_fields == ()


# ---------------------------------------------------------------------------
# Test 2: Missing top-level section fails
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "section",
    [
        "_notice",
        "_schema_version",
        "_status",
        "identity",
        "snapshot_metadata",
        "research_queue_state",
        "resolved_outcome",
        "human_review",
        "calibration_validity",
    ],
)
def test_missing_top_level_section_fails(section: str):
    record = _drop(_valid_record(), section)
    result = validate_calibration_record(record)
    assert not result.is_valid
    assert section in result.missing_required_fields


# ---------------------------------------------------------------------------
# Test 3: Missing identity.market_id fails
# ---------------------------------------------------------------------------


def test_missing_identity_market_id_fails():
    record = _drop(_valid_record(), "identity.market_id")
    result = validate_calibration_record(record)
    assert not result.is_valid
    assert "identity.market_id" in result.missing_required_fields


# ---------------------------------------------------------------------------
# Test 4: Missing identity.condition_id fails
# ---------------------------------------------------------------------------


def test_missing_identity_condition_id_fails():
    record = _drop(_valid_record(), "identity.condition_id")
    result = validate_calibration_record(record)
    assert not result.is_valid
    assert "identity.condition_id" in result.missing_required_fields


# ---------------------------------------------------------------------------
# Test 5: Missing snapshot_time_utc fails
# ---------------------------------------------------------------------------


def test_missing_snapshot_time_utc_fails():
    record = _drop(_valid_record(), "snapshot_metadata.snapshot_time_utc")
    result = validate_calibration_record(record)
    assert not result.is_valid
    assert "snapshot_metadata.snapshot_time_utc" in result.missing_required_fields


# ---------------------------------------------------------------------------
# Test 6: Invalid snapshot offset fails
# ---------------------------------------------------------------------------


def test_invalid_snapshot_offset_fails():
    record = _set(_valid_record(), "snapshot_metadata.snapshot_offset_from_resolution", "T-999d")
    result = validate_calibration_record(record)
    assert not result.is_valid
    assert "snapshot_metadata.snapshot_offset_from_resolution" in result.invalid_fields


@pytest.mark.parametrize("offset", sorted(ALLOWED_SNAPSHOT_OFFSETS))
def test_all_valid_snapshot_offsets_pass(offset: str):
    record = _set(_valid_record(), "snapshot_metadata.snapshot_offset_from_resolution", offset)
    result = validate_calibration_record(record)
    assert result.is_valid, f"Offset {offset!r} should be valid"


# ---------------------------------------------------------------------------
# Test 7: Invalid research queue bucket fails
# ---------------------------------------------------------------------------


def test_invalid_research_queue_bucket_fails():
    record = _set(_valid_record(), "research_queue_state.research_queue_bucket", "UNKNOWN_BUCKET")
    result = validate_calibration_record(record)
    assert not result.is_valid
    assert "research_queue_state.research_queue_bucket" in result.invalid_fields


@pytest.mark.parametrize("bucket", sorted(ALLOWED_RESEARCH_QUEUE_BUCKETS))
def test_all_valid_buckets_pass(bucket: str):
    record = _set(_valid_record(), "research_queue_state.research_queue_bucket", bucket)
    result = validate_calibration_record(record)
    assert result.is_valid, f"Bucket {bucket!r} should be valid"


# ---------------------------------------------------------------------------
# Test 8: Missing research_priority_score fails unless excluded
# ---------------------------------------------------------------------------


def test_missing_research_priority_score_fails_when_not_excluded():
    record = _drop(_valid_record(), "research_queue_state.research_priority_score")
    result = validate_calibration_record(record)
    assert not result.is_valid
    assert "research_queue_state.research_priority_score" in result.missing_required_fields


def test_none_research_priority_score_fails_when_not_excluded():
    record = _set(_valid_record(), "research_queue_state.research_priority_score", None)
    result = validate_calibration_record(record)
    assert not result.is_valid
    assert "research_queue_state.research_priority_score" in result.invalid_fields


def test_none_research_priority_score_allowed_when_excluded():
    record = _set(_valid_record(), "research_queue_state.research_priority_score", None)
    record = _set(record, "calibration_validity.excluded_from_calibration", True)
    result = validate_calibration_record(record)
    # None score allowed when excluded; other fields still validated
    assert "research_queue_state.research_priority_score" not in result.invalid_fields


# ---------------------------------------------------------------------------
# Test 9: research_priority_score outside [0, 1] fails
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("bad_score", [-0.1, 1.1, 2.0, -1])
def test_research_priority_score_out_of_range_fails(bad_score: object):
    record = _set(_valid_record(), "research_queue_state.research_priority_score", bad_score)
    result = validate_calibration_record(record)
    assert not result.is_valid
    assert "research_queue_state.research_priority_score" in result.invalid_fields


@pytest.mark.parametrize("good_score", [0.0, 0.5, 1.0, 0, 1])
def test_research_priority_score_in_range_passes(good_score: object):
    record = _set(_valid_record(), "research_queue_state.research_priority_score", good_score)
    result = validate_calibration_record(record)
    assert result.is_valid, f"Score {good_score!r} should be valid"


# ---------------------------------------------------------------------------
# Test 10: Invalid resolution_status fails
# ---------------------------------------------------------------------------


def test_invalid_resolution_status_fails():
    record = _set(_valid_record(), "resolved_outcome.resolution_status", "INVALID_STATUS")
    result = validate_calibration_record(record)
    assert not result.is_valid
    assert "resolved_outcome.resolution_status" in result.invalid_fields


@pytest.mark.parametrize("status", sorted(ALLOWED_RESOLUTION_STATUSES))
def test_all_valid_resolution_statuses_pass(status: str):
    record = _set(_valid_record(), "resolved_outcome.resolution_status", status)
    result = validate_calibration_record(record)
    assert result.is_valid, f"Resolution status {status!r} should be valid"


# ---------------------------------------------------------------------------
# Test 11: Invalid resolution_source_type fails
# ---------------------------------------------------------------------------


def test_invalid_resolution_source_type_fails():
    record = _set(_valid_record(), "resolved_outcome.resolution_source_type", "BLOG_POST")
    result = validate_calibration_record(record)
    assert not result.is_valid
    assert "resolved_outcome.resolution_source_type" in result.invalid_fields


@pytest.mark.parametrize("src_type", sorted(ALLOWED_RESOLUTION_SOURCE_TYPES))
def test_all_valid_resolution_source_types_pass(src_type: str):
    record = _set(_valid_record(), "resolved_outcome.resolution_source_type", src_type)
    result = validate_calibration_record(record)
    assert result.is_valid, f"Resolution source type {src_type!r} should be valid"


# ---------------------------------------------------------------------------
# Test 12: Missing outcome_token_mapping_verified fails
# ---------------------------------------------------------------------------


def test_missing_outcome_token_mapping_verified_fails():
    record = _drop(_valid_record(), "resolved_outcome.outcome_token_mapping_verified")
    result = validate_calibration_record(record)
    assert not result.is_valid
    assert "resolved_outcome.outcome_token_mapping_verified" in result.missing_required_fields


# ---------------------------------------------------------------------------
# Test 13: outcome_token_mapping_verified=False produces warning
# ---------------------------------------------------------------------------


def test_outcome_token_mapping_verified_false_produces_warning():
    record = _set(_valid_record(), "resolved_outcome.outcome_token_mapping_verified", False)
    result = validate_calibration_record(record)
    # False is not an invalid value (bool); it produces a warning
    assert "resolved_outcome.outcome_token_mapping_verified" not in result.invalid_fields
    assert any("outcome_token_mapping_verified" in w for w in result.warnings)


def test_outcome_token_mapping_verified_non_bool_fails():
    record = _set(_valid_record(), "resolved_outcome.outcome_token_mapping_verified", "yes")
    result = validate_calibration_record(record)
    assert not result.is_valid
    assert "resolved_outcome.outcome_token_mapping_verified" in result.invalid_fields


# ---------------------------------------------------------------------------
# Test 14: Invalid human_review_usefulness_label fails
# ---------------------------------------------------------------------------


def test_invalid_human_review_usefulness_label_fails():
    record = _set(
        _valid_record(), "human_review.human_review_usefulness_label", "INVALID_LABEL"
    )
    result = validate_calibration_record(record)
    assert not result.is_valid
    assert "human_review.human_review_usefulness_label" in result.invalid_fields


@pytest.mark.parametrize("label", sorted(ALLOWED_HUMAN_REVIEW_USEFULNESS_LABELS))
def test_all_valid_human_review_labels_pass(label: str):
    record = _set(_valid_record(), "human_review.human_review_usefulness_label", label)
    result = validate_calibration_record(record)
    assert result.is_valid, f"Label {label!r} should be valid"


# ---------------------------------------------------------------------------
# Test 15: Forbidden key pnl is flagged
# ---------------------------------------------------------------------------


def test_forbidden_key_pnl_at_top_level_flagged():
    record = _valid_record()
    record["pnl"] = 0.0
    result = validate_calibration_record(record)
    assert not result.is_valid
    assert any("pnl" in f for f in result.invalid_fields)


# ---------------------------------------------------------------------------
# Test 16: Forbidden key expected_return is flagged
# ---------------------------------------------------------------------------


def test_forbidden_key_expected_return_at_top_level_flagged():
    record = _valid_record()
    record["expected_return"] = 0.05
    result = validate_calibration_record(record)
    assert not result.is_valid
    assert any("expected_return" in f for f in result.invalid_fields)


# ---------------------------------------------------------------------------
# Test 17: Forbidden key nested inside any section is flagged
# ---------------------------------------------------------------------------


def test_forbidden_key_nested_inside_section_flagged():
    record = _valid_record()
    record["identity"]["pnl"] = 99.9
    result = validate_calibration_record(record)
    assert not result.is_valid
    assert any("pnl" in f for f in result.invalid_fields)


def test_forbidden_key_deeply_nested_flagged():
    record = _valid_record()
    record["research_queue_state"]["expected_return"] = 0.1
    result = validate_calibration_record(record)
    assert not result.is_valid
    assert any("expected_return" in f for f in result.invalid_fields)


@pytest.mark.parametrize(
    "key",
    ["profit", "roi", "win_rate", "sharpe", "trade_signal", "buy", "sell",
     "position_size", "entry", "exit", "fill_probability", "slippage",
     "edge", "alpha", "opportunity", "arbitrage"],
)
def test_all_forbidden_keys_flagged(key: str):
    record = _valid_record()
    record[key] = "forbidden"
    result = validate_calibration_record(record)
    assert not result.is_valid
    assert any(key in f for f in result.invalid_fields)


# ---------------------------------------------------------------------------
# Test 18: Result object is deterministic and frozen
# ---------------------------------------------------------------------------


def test_result_is_frozen():
    record = _valid_record()
    result = validate_calibration_record(record)
    with pytest.raises((AttributeError, TypeError)):
        result.is_valid = False  # type: ignore[misc]


def test_result_is_deterministic():
    record = _valid_record()
    r1 = validate_calibration_record(record)
    r2 = validate_calibration_record(record)
    assert r1 == r2


def test_result_tuple_fields_are_tuples():
    record = _valid_record()
    result = validate_calibration_record(record)
    assert isinstance(result.missing_required_fields, tuple)
    assert isinstance(result.invalid_fields, tuple)
    assert isinstance(result.warnings, tuple)


def test_advisory_label_is_string():
    record = _valid_record()
    result = validate_calibration_record(record)
    assert isinstance(result.advisory_label, str)
    assert len(result.advisory_label) > 0


def test_advisory_label_contains_research_usefulness():
    record = _valid_record()
    result = validate_calibration_record(record)
    assert "research" in result.advisory_label.lower()
    assert "trading" not in result.advisory_label.lower() or "not" in result.advisory_label.lower()


# ---------------------------------------------------------------------------
# Test 19: Validator does not import network libraries
# ---------------------------------------------------------------------------


def test_validator_does_not_import_network_libraries():
    mod_name = "src.data_layer.calibration_record_validation"
    mod = sys.modules.get(mod_name)
    if mod is None:
        mod = importlib.import_module(mod_name)
    forbidden_network_modules = {
        "urllib.request", "urllib3", "requests", "httpx", "aiohttp",
        "socket", "http.client", "http", "ssl",
    }
    # Check the module's own imports by inspecting sys.modules keys that were
    # imported as a result of loading the module. We check module __dict__ only.
    module_source = pathlib.Path(mod.__file__).read_text(encoding="utf-8")
    for net_mod in forbidden_network_modules:
        assert f"import {net_mod}" not in module_source, (
            f"Validator must not import network library: {net_mod}"
        )


# ---------------------------------------------------------------------------
# Test 20: Validator performs no file writes
# ---------------------------------------------------------------------------


def test_validator_performs_no_file_writes():
    module_source = pathlib.Path(
        sys.modules["src.data_layer.calibration_record_validation"].__file__
    ).read_text(encoding="utf-8")
    for write_call in ("open(", ".write(", "pathlib.Path", "json.dump(", "os.makedirs"):
        # Allow pathlib in type hints but not in runtime logic (conservative check)
        if write_call == "pathlib.Path":
            continue  # pathlib.Path is not imported in the module
        assert write_call not in module_source, (
            f"Validator must not contain file-write call: {write_call!r}"
        )


def test_validator_module_has_no_pathlib_import():
    module_source = pathlib.Path(
        sys.modules["src.data_layer.calibration_record_validation"].__file__
    ).read_text(encoding="utf-8")
    assert "import pathlib" not in module_source
    assert "from pathlib" not in module_source


# ---------------------------------------------------------------------------
# Test 21: Validator does not read local_data or .env
# ---------------------------------------------------------------------------


def test_validator_does_not_reference_local_data():
    module_source = pathlib.Path(
        sys.modules["src.data_layer.calibration_record_validation"].__file__
    ).read_text(encoding="utf-8")
    assert "local_data" not in module_source


def test_validator_does_not_reference_dotenv():
    module_source = pathlib.Path(
        sys.modules["src.data_layer.calibration_record_validation"].__file__
    ).read_text(encoding="utf-8")
    assert ".env" not in module_source
    assert "dotenv" not in module_source


# ---------------------------------------------------------------------------
# Additional edge cases
# ---------------------------------------------------------------------------


def test_empty_record_fails_all_required_sections():
    result = validate_calibration_record({})
    assert not result.is_valid
    for section in (
        "_notice", "_schema_version", "_status", "identity",
        "snapshot_metadata", "research_queue_state", "resolved_outcome",
        "human_review", "calibration_validity",
    ):
        assert section in result.missing_required_fields


def test_non_string_market_id_fails():
    record = _set(_valid_record(), "identity.market_id", 12345)
    result = validate_calibration_record(record)
    assert not result.is_valid
    assert "identity.market_id" in result.invalid_fields


def test_empty_string_question_fails():
    record = _set(_valid_record(), "identity.question", "")
    result = validate_calibration_record(record)
    assert not result.is_valid
    assert "identity.question" in result.invalid_fields


def test_non_bool_source_metadata_available_fails():
    record = _set(_valid_record(), "research_queue_state.source_metadata_available", "yes")
    result = validate_calibration_record(record)
    assert not result.is_valid
    assert "research_queue_state.source_metadata_available" in result.invalid_fields


def test_negative_cross_market_candidate_count_fails():
    record = _set(_valid_record(), "research_queue_state.cross_market_candidate_count", -1)
    result = validate_calibration_record(record)
    assert not result.is_valid
    assert "research_queue_state.cross_market_candidate_count" in result.invalid_fields


def test_zero_cross_market_candidate_count_is_valid():
    record = _set(_valid_record(), "research_queue_state.cross_market_candidate_count", 0)
    result = validate_calibration_record(record)
    assert result.is_valid


def test_timestamp_without_z_suffix_fails():
    record = _set(_valid_record(), "snapshot_metadata.snapshot_time_utc", "2025-12-01T12:00:00")
    result = validate_calibration_record(record)
    assert not result.is_valid
    assert "snapshot_metadata.snapshot_time_utc" in result.invalid_fields


def test_timestamp_with_z_suffix_passes():
    record = _set(_valid_record(), "snapshot_metadata.snapshot_time_utc", "2025-12-01T12:00:00Z")
    result = validate_calibration_record(record)
    assert result.is_valid


def test_calibration_validity_missing_required_fields_not_list_fails():
    record = _set(_valid_record(), "calibration_validity.missing_required_fields", "none")
    result = validate_calibration_record(record)
    assert not result.is_valid
    assert "calibration_validity.missing_required_fields" in result.invalid_fields


def test_record_with_missing_human_review_label_field_fails():
    record = _drop(_valid_record(), "human_review.human_review_usefulness_label")
    result = validate_calibration_record(record)
    assert not result.is_valid
    assert "human_review.human_review_usefulness_label" in result.missing_required_fields


def test_forbidden_keys_set_is_not_empty():
    assert len(FORBIDDEN_KEY_NAMES) > 0


def test_result_is_valid_field_matches_empty_missing_and_invalid():
    record = _valid_record()
    result = validate_calibration_record(record)
    if result.missing_required_fields or result.invalid_fields:
        assert not result.is_valid
    else:
        assert result.is_valid


def test_missing_calibration_validity_section_fails():
    record = _drop(_valid_record(), "calibration_validity")
    result = validate_calibration_record(record)
    assert not result.is_valid
    assert "calibration_validity" in result.missing_required_fields


def test_missing_resolved_outcome_resolution_status_fails():
    record = _drop(_valid_record(), "resolved_outcome.resolution_status")
    result = validate_calibration_record(record)
    assert not result.is_valid
    assert "resolved_outcome.resolution_status" in result.missing_required_fields
