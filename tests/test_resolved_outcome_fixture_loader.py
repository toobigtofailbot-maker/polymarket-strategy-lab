"""Focused tests for the WP68 local/offline/read-only resolved outcome fixture loader.

Tests cover: single file, list file, directory loading, determinism, safety checks,
validator integration, non-recursive behavior, and forbidden scope boundaries.
"""

from __future__ import annotations

import importlib
import inspect
import json
import sys
import tempfile
from pathlib import Path

import pytest

from src.data_layer.resolved_outcome_fixture_loader import (
    LoadedCalibrationRecord,
    ResolvedOutcomeFixtureLoadResult,
    load_resolved_outcome_fixtures,
)


# ---------------------------------------------------------------------------
# Shared fixture factory
# ---------------------------------------------------------------------------

def _valid_record(**overrides) -> dict:
    """Return a structurally valid calibration record dict."""
    base = {
        "_notice": "ADVISORY_ONLY",
        "_schema_version": "calibration_record_v1",
        "_status": "TEST",
        "identity": {
            "market_id": "market-abc",
            "condition_id": "cond-def",
            "question": "Will X happen?",
            "category": "Politics",
        },
        "snapshot_metadata": {
            "snapshot_time_utc": "2025-12-01T12:00:00Z",
            "local_capture_time_utc": "2025-12-01T12:05:00Z",
            "snapshot_offset_from_resolution": "T-30d",
        },
        "research_queue_state": {
            "research_queue_bucket": "REVIEW_FIRST",
            "research_review_priority": 1,
            "research_priority_score": 0.75,
            "quality_status": "ACCEPTABLE",
            "source_metadata_available": True,
            "manual_source_review_required": False,
            "resolution_ambiguity_manual_review_required": False,
            "microstructure_quality_summary": "LOCAL_DATA_AVAILABLE",
            "cross_market_candidate_count": 0,
        },
        "resolved_outcome": {
            "resolved_outcome": "YES",
            "resolution_status": "RESOLVED",
            "resolution_time_utc": "2026-01-02T00:00:00Z",
            "resolution_source_url_or_reference": "https://example.invalid/source",
            "resolution_source_type": "NEWS_ARTICLE",
            "resolution_rule_text_snapshot_available": True,
            "resolution_dispute_or_ambiguity_flag": False,
            "final_market_status": "RESOLVED",
            "outcome_token_mapping_verified": True,
        },
        "human_review": {
            "human_review_usefulness_label": "USEFUL_RESEARCH_TARGET",
        },
        "calibration_validity": {
            "record_complete": True,
            "missing_required_fields": [],
            "excluded_from_calibration": False,
            "exclusion_reason": None,
        },
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# 1. Single valid JSON object file
# ---------------------------------------------------------------------------

def test_single_valid_json_object_loads_as_one_valid_record():
    record = _valid_record()
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "record.json"
        path.write_text(json.dumps(record), encoding="utf-8")
        result = load_resolved_outcome_fixtures(path)

    assert result.loaded_count == 1
    assert result.valid_count == 1
    assert result.invalid_count == 0
    assert len(result.records) == 1
    assert result.records[0].validation.is_valid
    assert result.records[0].record_index is None
    assert result.errors == ()


# ---------------------------------------------------------------------------
# 2. JSON list file loads in list order
# ---------------------------------------------------------------------------

def test_json_list_of_two_records_loads_in_list_order():
    rec1 = _valid_record()
    rec1["identity"]["market_id"] = "market-001"
    rec2 = _valid_record()
    rec2["identity"]["market_id"] = "market-002"
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "list.json"
        path.write_text(json.dumps([rec1, rec2]), encoding="utf-8")
        result = load_resolved_outcome_fixtures(path)

    assert result.loaded_count == 2
    assert result.valid_count == 2
    assert result.records[0].record_index == 0
    assert result.records[1].record_index == 1
    assert result.records[0].record["identity"]["market_id"] == "market-001"
    assert result.records[1].record["identity"]["market_id"] == "market-002"


# ---------------------------------------------------------------------------
# 3. Directory loads direct *.json children sorted by filename
# ---------------------------------------------------------------------------

def test_directory_loads_direct_json_children_sorted_by_filename():
    rec_a = _valid_record()
    rec_a["identity"]["market_id"] = "market-aaa"
    rec_b = _valid_record()
    rec_b["identity"]["market_id"] = "market-bbb"
    rec_c = _valid_record()
    rec_c["identity"]["market_id"] = "market-ccc"
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        (tmp / "c_record.json").write_text(json.dumps(rec_c), encoding="utf-8")
        (tmp / "a_record.json").write_text(json.dumps(rec_a), encoding="utf-8")
        (tmp / "b_record.json").write_text(json.dumps(rec_b), encoding="utf-8")
        result = load_resolved_outcome_fixtures(tmp)

    assert result.loaded_count == 3
    assert result.valid_count == 3
    market_ids = [r.record["identity"]["market_id"] for r in result.records]
    assert market_ids == ["market-aaa", "market-bbb", "market-ccc"]


# ---------------------------------------------------------------------------
# 4. Non-recursive: nested JSON file is not loaded
# ---------------------------------------------------------------------------

def test_directory_does_not_load_nested_subdirectory_json():
    record = _valid_record()
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        (tmp / "top.json").write_text(json.dumps(record), encoding="utf-8")
        subdir = tmp / "subdir"
        subdir.mkdir()
        (subdir / "nested.json").write_text(json.dumps(record), encoding="utf-8")
        result = load_resolved_outcome_fixtures(tmp)

    assert result.loaded_count == 1, "Only the top-level file should be loaded"
    assert result.records[0].source_path.endswith("top.json")


# ---------------------------------------------------------------------------
# 5. Missing path returns loader-level error
# ---------------------------------------------------------------------------

def test_missing_path_returns_loader_error():
    result = load_resolved_outcome_fixtures("/nonexistent/path/that/does/not/exist/record.json")
    assert result.loaded_count == 0
    assert result.valid_count == 0
    assert len(result.errors) >= 1
    assert any("does not exist" in e for e in result.errors)


# ---------------------------------------------------------------------------
# 6. Invalid JSON returns loader-level error
# ---------------------------------------------------------------------------

def test_invalid_json_returns_loader_error():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "bad.json"
        path.write_text("{ this is not valid json }", encoding="utf-8")
        result = load_resolved_outcome_fixtures(path)

    assert result.loaded_count == 0
    assert len(result.errors) >= 1
    assert any("Invalid JSON" in e for e in result.errors)


# ---------------------------------------------------------------------------
# 7. Unsupported extension is rejected
# ---------------------------------------------------------------------------

def test_unsupported_extension_is_rejected():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "record.txt"
        path.write_text("{}", encoding="utf-8")
        result = load_resolved_outcome_fixtures(path)

    assert result.loaded_count == 0
    assert len(result.errors) >= 1
    assert any("Unsupported file extension" in e for e in result.errors)


def test_jsonl_extension_is_rejected():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "records.jsonl"
        path.write_text("{}\n{}", encoding="utf-8")
        result = load_resolved_outcome_fixtures(path)

    assert result.loaded_count == 0
    assert any("Unsupported file extension" in e for e in result.errors)


# ---------------------------------------------------------------------------
# 8. URL-like path is rejected
# ---------------------------------------------------------------------------

def test_http_url_path_is_rejected():
    result = load_resolved_outcome_fixtures("http://example.com/records.json")
    assert result.loaded_count == 0
    assert any("URL-like" in e for e in result.errors)


def test_https_url_path_is_rejected():
    result = load_resolved_outcome_fixtures("https://api.polymarket.com/records.json")
    assert result.loaded_count == 0
    assert any("URL-like" in e for e in result.errors)


# ---------------------------------------------------------------------------
# 9. JSON list containing non-object entry is reported at loader level
# ---------------------------------------------------------------------------

def test_json_list_non_object_entry_is_reported_as_error():
    record = _valid_record()
    mixed_list = [record, "not-an-object", record]
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "mixed.json"
        path.write_text(json.dumps(mixed_list), encoding="utf-8")
        result = load_resolved_outcome_fixtures(path)

    assert result.loaded_count == 2, "Valid object entries should still load"
    assert len(result.errors) >= 1
    assert any("not an object" in e or "index 1" in e for e in result.errors)


# ---------------------------------------------------------------------------
# 10. Invalid calibration record loads but counted as invalid via WP67 validator
# ---------------------------------------------------------------------------

def test_invalid_calibration_record_loads_but_counted_invalid():
    bad_record = {"_notice": "some notice"}  # missing almost all required fields
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "invalid_record.json"
        path.write_text(json.dumps(bad_record), encoding="utf-8")
        result = load_resolved_outcome_fixtures(path)

    assert result.loaded_count == 1
    assert result.valid_count == 0
    assert result.invalid_count == 1
    assert not result.records[0].validation.is_valid
    assert len(result.records[0].validation.missing_required_fields) > 0


# ---------------------------------------------------------------------------
# 11. Validator warning counts are included in result
# ---------------------------------------------------------------------------

def test_validator_warning_counts_included():
    record = _valid_record()
    record["resolved_outcome"]["outcome_token_mapping_verified"] = False
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "warn.json"
        path.write_text(json.dumps(record), encoding="utf-8")
        result = load_resolved_outcome_fixtures(path)

    assert result.warning_count >= 1
    assert len(result.records[0].validation.warnings) >= 1


# ---------------------------------------------------------------------------
# 12. Loader result dataclasses are frozen / deterministic
# ---------------------------------------------------------------------------

def test_load_result_is_frozen():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "r.json"
        path.write_text(json.dumps(_valid_record()), encoding="utf-8")
        result = load_resolved_outcome_fixtures(path)

    with pytest.raises((AttributeError, TypeError)):
        result.loaded_count = 99  # type: ignore[misc]


def test_loaded_calibration_record_is_frozen():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "r.json"
        path.write_text(json.dumps(_valid_record()), encoding="utf-8")
        result = load_resolved_outcome_fixtures(path)

    rec = result.records[0]
    with pytest.raises((AttributeError, TypeError)):
        rec.source_path = "modified"  # type: ignore[misc]


def test_same_input_produces_same_result():
    record = _valid_record()
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "r.json"
        path.write_text(json.dumps(record), encoding="utf-8")
        r1 = load_resolved_outcome_fixtures(path)
        r2 = load_resolved_outcome_fixtures(path)

    assert r1.loaded_count == r2.loaded_count
    assert r1.valid_count == r2.valid_count
    assert r1.invalid_count == r2.invalid_count
    assert r1.warning_count == r2.warning_count


# ---------------------------------------------------------------------------
# 13. Loader does not import network libraries
# ---------------------------------------------------------------------------

def test_loader_module_does_not_import_network_libraries():
    loader_module = importlib.import_module("src.data_layer.resolved_outcome_fixture_loader")
    source = inspect.getsource(loader_module)
    forbidden_imports = ["urllib", "requests", "httpx", "aiohttp", "socket", "http.client"]
    for lib in forbidden_imports:
        assert lib not in source, f"Loader must not import network library: {lib}"


# ---------------------------------------------------------------------------
# 14. Loader does not import credential/auth libraries or authenticated clients
# ---------------------------------------------------------------------------

def test_loader_does_not_import_credential_or_auth_libraries():
    import pathlib as _pathlib
    import sys as _sys
    mod_name = "src.data_layer.resolved_outcome_fixture_loader"
    mod = _sys.modules.get(mod_name) or importlib.import_module(mod_name)
    source = _pathlib.Path(mod.__file__).read_text(encoding="utf-8")
    forbidden_imports = [
        "import dotenv",
        "import py_clob_client",
        "import clob_client",
        "import keyring",
        "import cryptography",
        "from dotenv",
        "from py_clob_client",
        "os.getenv",
        "os.environ",
    ]
    for term in forbidden_imports:
        assert term not in source, (
            f"Loader must not import credential/auth library or read env vars: '{term}'"
        )


# ---------------------------------------------------------------------------
# 15. Loader performs no file writes
# ---------------------------------------------------------------------------

def test_loader_source_does_not_call_file_write_methods():
    loader_module = importlib.import_module("src.data_layer.resolved_outcome_fixture_loader")
    source = inspect.getsource(loader_module)
    write_calls = [".write(", ".write_text(", ".write_bytes(", "open("]
    for call in write_calls:
        assert call not in source, (
            f"Loader must not write files; found forbidden call: '{call}'"
        )


# ---------------------------------------------------------------------------
# 16. Loader does not scan directories recursively
# ---------------------------------------------------------------------------

def test_loader_source_does_not_use_rglob_or_walk():
    loader_module = importlib.import_module("src.data_layer.resolved_outcome_fixture_loader")
    source = inspect.getsource(loader_module)
    recursive_patterns = ["rglob", "os.walk", "glob.glob"]
    for pattern in recursive_patterns:
        assert pattern not in source, (
            f"Loader must not scan recursively; found: '{pattern}'"
        )


# ---------------------------------------------------------------------------
# 17. Loader result contains no forbidden trading/performance metric fields
# ---------------------------------------------------------------------------

def test_loader_result_contains_no_forbidden_metric_fields():
    record = _valid_record()
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "r.json"
        path.write_text(json.dumps(record), encoding="utf-8")
        result = load_resolved_outcome_fixtures(path)

    result_fields = set(vars(result).keys())
    forbidden_fields = {
        "pnl", "profit", "roi", "expected_return", "win_rate", "sharpe",
        "trade_signal", "position_size", "fill_probability", "slippage",
        "edge", "alpha", "arbitrage",
    }
    overlap = result_fields & forbidden_fields
    assert not overlap, (
        f"Loader result must not contain forbidden trading/performance fields: {overlap}"
    )


def test_loader_does_not_import_metric_computation_libraries():
    import pathlib as _pathlib
    import sys as _sys
    mod_name = "src.data_layer.resolved_outcome_fixture_loader"
    mod = _sys.modules.get(mod_name) or importlib.import_module(mod_name)
    source = _pathlib.Path(mod.__file__).read_text(encoding="utf-8")
    forbidden_imports = ["import numpy", "import pandas", "import scipy", "import sklearn"]
    for imp in forbidden_imports:
        assert imp not in source, (
            f"Loader must not import metric computation library: '{imp}'"
        )


# ---------------------------------------------------------------------------
# 18. Full WP67 validator tests still pass (import check)
# ---------------------------------------------------------------------------

def test_wp67_validator_module_importable():
    from src.data_layer.calibration_record_validation import (  # noqa: F401
        validate_calibration_record,
        CalibrationRecordValidationResult,
    )


def test_wp67_validate_calibration_record_works_correctly():
    from src.data_layer.calibration_record_validation import validate_calibration_record
    record = _valid_record()
    result = validate_calibration_record(record)
    assert result.is_valid
    assert result.missing_required_fields == ()
    assert result.invalid_fields == ()


# ---------------------------------------------------------------------------
# 19. Source path in result matches input path
# ---------------------------------------------------------------------------

def test_source_path_matches_input():
    record = _valid_record()
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "record.json"
        path.write_text(json.dumps(record), encoding="utf-8")
        result = load_resolved_outcome_fixtures(str(path))

    assert result.source_path == str(path)


# ---------------------------------------------------------------------------
# 20. Directory with no json files returns empty result with error
# ---------------------------------------------------------------------------

def test_empty_directory_returns_error():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        (tmp / "notes.txt").write_text("not a json file", encoding="utf-8")
        result = load_resolved_outcome_fixtures(tmp)

    assert result.loaded_count == 0
    assert len(result.errors) >= 1
    assert any("no direct-child" in e.lower() or "*.json" in e for e in result.errors)


# ---------------------------------------------------------------------------
# 21. Multiple valid records loaded from directory have correct counts
# ---------------------------------------------------------------------------

def test_multiple_valid_records_from_directory_have_correct_counts():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        for i in range(3):
            rec = _valid_record()
            rec["identity"]["market_id"] = f"market-{i:03d}"
            (tmp / f"record_{i:03d}.json").write_text(json.dumps(rec), encoding="utf-8")
        result = load_resolved_outcome_fixtures(tmp)

    assert result.loaded_count == 3
    assert result.valid_count == 3
    assert result.invalid_count == 0
    assert result.errors == ()


# ---------------------------------------------------------------------------
# 22. Mixed valid/invalid records have correct counts
# ---------------------------------------------------------------------------

def test_mixed_valid_invalid_records_have_correct_counts():
    valid_rec = _valid_record()
    invalid_rec = {"_notice": "missing everything"}
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "mixed.json"
        path.write_text(json.dumps([valid_rec, invalid_rec]), encoding="utf-8")
        result = load_resolved_outcome_fixtures(path)

    assert result.loaded_count == 2
    assert result.valid_count == 1
    assert result.invalid_count == 1


# ---------------------------------------------------------------------------
# 23. Advisory label is present in result
# ---------------------------------------------------------------------------

def test_advisory_label_present_in_result():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "r.json"
        path.write_text(json.dumps(_valid_record()), encoding="utf-8")
        result = load_resolved_outcome_fixtures(path)

    assert "ADVISORY_ONLY" in result.advisory_label
    assert "trading" in result.advisory_label.lower() or "performance" in result.advisory_label.lower()


# ---------------------------------------------------------------------------
# 24. Non-json files in directory are silently ignored (not counted as errors)
# ---------------------------------------------------------------------------

def test_non_json_files_in_directory_are_ignored():
    record = _valid_record()
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        (tmp / "record.json").write_text(json.dumps(record), encoding="utf-8")
        (tmp / "readme.txt").write_text("ignore me", encoding="utf-8")
        (tmp / "notes.md").write_text("# notes", encoding="utf-8")
        result = load_resolved_outcome_fixtures(tmp)

    assert result.loaded_count == 1, "Only the .json file should be loaded"
    assert result.valid_count == 1


# ---------------------------------------------------------------------------
# 25. Records tuple preserves file order within a single list file
# ---------------------------------------------------------------------------

def test_list_file_records_preserve_index_order():
    records = [_valid_record() for _ in range(4)]
    for i, r in enumerate(records):
        r["identity"]["market_id"] = f"market-{i}"
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "list.json"
        path.write_text(json.dumps(records), encoding="utf-8")
        result = load_resolved_outcome_fixtures(path)

    assert result.loaded_count == 4
    for i, rec in enumerate(result.records):
        assert rec.record_index == i
        assert rec.record["identity"]["market_id"] == f"market-{i}"


# ---------------------------------------------------------------------------
# 26. Loader result records field is a tuple (immutable sequence)
# ---------------------------------------------------------------------------

def test_loader_result_records_is_tuple():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "r.json"
        path.write_text(json.dumps(_valid_record()), encoding="utf-8")
        result = load_resolved_outcome_fixtures(path)

    assert isinstance(result.records, tuple)
    assert isinstance(result.errors, tuple)


# ---------------------------------------------------------------------------
# 27. Path given as string is accepted equivalently to Path object
# ---------------------------------------------------------------------------

def test_string_path_and_path_object_produce_same_result():
    record = _valid_record()
    with tempfile.TemporaryDirectory() as tmpdir:
        p = Path(tmpdir) / "r.json"
        p.write_text(json.dumps(record), encoding="utf-8")
        result_str = load_resolved_outcome_fixtures(str(p))
        result_path = load_resolved_outcome_fixtures(p)

    assert result_str.loaded_count == result_path.loaded_count
    assert result_str.valid_count == result_path.valid_count


# ---------------------------------------------------------------------------
# 28. Empty JSON object ({}) loads as one invalid record (missing all sections)
# ---------------------------------------------------------------------------

def test_empty_json_object_loads_as_invalid_record():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "empty.json"
        path.write_text("{}", encoding="utf-8")
        result = load_resolved_outcome_fixtures(path)

    assert result.loaded_count == 1
    assert result.invalid_count == 1
    assert not result.records[0].validation.is_valid


# ---------------------------------------------------------------------------
# 29. Forbidden key in record produces validator warning via WP67
# ---------------------------------------------------------------------------

def test_forbidden_key_in_record_produces_validator_warning():
    record = _valid_record()
    record["pnl"] = 100.0
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "forbidden.json"
        path.write_text(json.dumps(record), encoding="utf-8")
        result = load_resolved_outcome_fixtures(path)

    assert result.loaded_count == 1
    assert result.invalid_count == 1
    assert result.warning_count >= 1
    warnings = result.records[0].validation.warnings
    assert any("pnl" in w.lower() for w in warnings)


# ---------------------------------------------------------------------------
# 30. Project status / docs test compatibility (import check)
# ---------------------------------------------------------------------------

def test_project_status_docs_module_importable():
    import tests.test_project_status_docs  # noqa: F401


def test_calibration_harness_docs_module_importable():
    import tests.test_calibration_harness_docs  # noqa: F401
