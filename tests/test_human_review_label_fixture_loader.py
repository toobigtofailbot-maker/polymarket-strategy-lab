"""Focused tests for the WP75 local/offline/read-only human review label fixture loader.

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

from src.data_layer.human_review_label_fixture_loader import (
    HumanReviewLabelFixtureLoadResult,
    LoadedHumanReviewLabelRecord,
    load_human_review_label_fixtures,
)


# ---------------------------------------------------------------------------
# Shared fixture factory
# ---------------------------------------------------------------------------

def _valid_record(**overrides) -> dict:
    """Return a structurally valid human review label record dict."""
    base = {
        "_notice": "ADVISORY_ONLY_MANUAL_RESEARCH_REVIEW_LABEL",
        "_schema_version": "HUMAN_REVIEW_LABEL_RECORD_V1",
        "_status": "TEST",
        "identity": {
            "market_id": "market-abc",
            "condition_id": "cond-def",
            "question": "Will X happen?",
            "snapshot_time_utc": "2026-01-01T00:00:00Z",
        },
        "review": {
            "review_time_utc": "2026-01-02T00:00:00Z",
            "reviewer_id_or_alias": "manual-reviewer",
            "workflow_state": "LABEL_APPLIED",
            "human_review_usefulness_label": "USEFUL_RESEARCH_TARGET",
            "confidence_level": "MEDIUM",
            "primary_reason": "SOURCE_CLARITY",
            "secondary_reasons": [],
            "requires_followup_review": False,
            "review_notes": "Test label record.",
        },
        "safety": {
            "manual_only": True,
            "not_automated": True,
            "no_trading_signal": True,
            "no_score_change": True,
            "no_execution": True,
        },
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# 1. Single valid JSON object loads as one valid record
# ---------------------------------------------------------------------------

def test_single_valid_json_object_loads_as_one_valid_record():
    record = _valid_record()
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "record.json"
        path.write_text(json.dumps(record), encoding="utf-8")
        result = load_human_review_label_fixtures(path)

    assert result.loaded_count == 1
    assert result.valid_count == 1
    assert result.invalid_count == 0
    assert len(result.records) == 1
    assert result.records[0].validation.is_valid
    assert result.records[0].record_index is None
    assert result.errors == ()


# ---------------------------------------------------------------------------
# 2. JSON list of two records loads in list order
# ---------------------------------------------------------------------------

def test_json_list_of_two_records_loads_in_list_order():
    rec1 = _valid_record()
    rec1["identity"]["market_id"] = "market-001"
    rec2 = _valid_record()
    rec2["identity"]["market_id"] = "market-002"
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "list.json"
        path.write_text(json.dumps([rec1, rec2]), encoding="utf-8")
        result = load_human_review_label_fixtures(path)

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
        result = load_human_review_label_fixtures(tmp)

    assert result.loaded_count == 3
    assert result.valid_count == 3
    market_ids = [r.record["identity"]["market_id"] for r in result.records]
    assert market_ids == ["market-aaa", "market-bbb", "market-ccc"]


# ---------------------------------------------------------------------------
# 4. Non-recursive behavior: nested JSON file is not loaded
# ---------------------------------------------------------------------------

def test_directory_does_not_load_nested_subdirectory_json():
    record = _valid_record()
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        (tmp / "top.json").write_text(json.dumps(record), encoding="utf-8")
        subdir = tmp / "subdir"
        subdir.mkdir()
        (subdir / "nested.json").write_text(json.dumps(record), encoding="utf-8")
        result = load_human_review_label_fixtures(tmp)

    assert result.loaded_count == 1, "Only the top-level file should be loaded"
    assert result.records[0].source_path.endswith("top.json")


# ---------------------------------------------------------------------------
# 5. Missing path returns loader-level error
# ---------------------------------------------------------------------------

def test_missing_path_returns_loader_error():
    result = load_human_review_label_fixtures("/nonexistent/path/that/does/not/exist/record.json")
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
        result = load_human_review_label_fixtures(path)

    assert result.loaded_count == 0
    assert len(result.errors) >= 1
    assert any("Invalid JSON" in e for e in result.errors)


# ---------------------------------------------------------------------------
# 7. Unsupported extension is rejected
# ---------------------------------------------------------------------------

def test_unsupported_extension_txt_is_rejected():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "record.txt"
        path.write_text("{}", encoding="utf-8")
        result = load_human_review_label_fixtures(path)

    assert result.loaded_count == 0
    assert len(result.errors) >= 1
    assert any("Unsupported file extension" in e for e in result.errors)


def test_unsupported_extension_jsonl_is_rejected():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "records.jsonl"
        path.write_text("{}\n{}", encoding="utf-8")
        result = load_human_review_label_fixtures(path)

    assert result.loaded_count == 0
    assert any("Unsupported file extension" in e for e in result.errors)


# ---------------------------------------------------------------------------
# 8. URL-like path is rejected
# ---------------------------------------------------------------------------

def test_http_url_path_is_rejected():
    result = load_human_review_label_fixtures("http://example.com/records.json")
    assert result.loaded_count == 0
    assert any("URL-like" in e for e in result.errors)


def test_https_url_path_is_rejected():
    result = load_human_review_label_fixtures("https://api.polymarket.com/records.json")
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
        result = load_human_review_label_fixtures(path)

    assert result.loaded_count == 2, "Valid object entries should still load"
    assert len(result.errors) >= 1
    assert any("not an object" in e or "index 1" in e for e in result.errors)


# ---------------------------------------------------------------------------
# 10. Invalid human review label record loads but counted invalid via WP74 validator
# ---------------------------------------------------------------------------

def test_invalid_human_review_label_record_loads_but_counted_invalid():
    bad_record = {"_notice": "ADVISORY_ONLY_MANUAL_RESEARCH_REVIEW_LABEL"}
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "invalid_record.json"
        path.write_text(json.dumps(bad_record), encoding="utf-8")
        result = load_human_review_label_fixtures(path)

    assert result.loaded_count == 1
    assert result.valid_count == 0
    assert result.invalid_count == 1
    assert not result.records[0].validation.is_valid
    assert len(result.records[0].validation.missing_required_fields) > 0


# ---------------------------------------------------------------------------
# 11. Validator warning counts are included in result
# ---------------------------------------------------------------------------

def test_validator_warning_counts_included_for_cross_field_violation():
    record = _valid_record()
    record["review"]["workflow_state"] = "NOT_REVIEWED"
    record["review"]["human_review_usefulness_label"] = "USEFUL_RESEARCH_TARGET"
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "warn.json"
        path.write_text(json.dumps(record), encoding="utf-8")
        result = load_human_review_label_fixtures(path)

    assert result.warning_count >= 1
    assert len(result.records[0].validation.warnings) >= 1


# ---------------------------------------------------------------------------
# 12. Loader result dataclasses are frozen / deterministic
# ---------------------------------------------------------------------------

def test_load_result_is_frozen():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "r.json"
        path.write_text(json.dumps(_valid_record()), encoding="utf-8")
        result = load_human_review_label_fixtures(path)

    with pytest.raises((AttributeError, TypeError)):
        result.loaded_count = 99  # type: ignore[misc]


def test_loaded_human_review_label_record_is_frozen():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "r.json"
        path.write_text(json.dumps(_valid_record()), encoding="utf-8")
        result = load_human_review_label_fixtures(path)

    rec = result.records[0]
    with pytest.raises((AttributeError, TypeError)):
        rec.source_path = "modified"  # type: ignore[misc]


def test_same_input_produces_same_result():
    record = _valid_record()
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "r.json"
        path.write_text(json.dumps(record), encoding="utf-8")
        r1 = load_human_review_label_fixtures(path)
        r2 = load_human_review_label_fixtures(path)

    assert r1.loaded_count == r2.loaded_count
    assert r1.valid_count == r2.valid_count
    assert r1.invalid_count == r2.invalid_count
    assert r1.warning_count == r2.warning_count


# ---------------------------------------------------------------------------
# 13. Loader does not import network libraries
# ---------------------------------------------------------------------------

def test_loader_module_does_not_import_network_libraries():
    loader_module = importlib.import_module("src.data_layer.human_review_label_fixture_loader")
    source = inspect.getsource(loader_module)
    forbidden_imports = ["urllib", "requests", "httpx", "aiohttp", "socket", "http.client"]
    for lib in forbidden_imports:
        assert lib not in source, f"Loader must not import network library: {lib}"


# ---------------------------------------------------------------------------
# 14. Loader performs no file writes
# ---------------------------------------------------------------------------

def test_loader_source_does_not_call_file_write_methods():
    loader_module = importlib.import_module("src.data_layer.human_review_label_fixture_loader")
    source = inspect.getsource(loader_module)
    write_calls = [".write(", ".write_text(", ".write_bytes(", "open("]
    for call in write_calls:
        assert call not in source, (
            f"Loader must not write files; found forbidden call: '{call}'"
        )


# ---------------------------------------------------------------------------
# 15. Loader references no credentials, .env, wallet, or authenticated client
# ---------------------------------------------------------------------------

def test_loader_does_not_import_credential_or_auth_libraries():
    import pathlib as _pathlib
    mod_name = "src.data_layer.human_review_label_fixture_loader"
    mod = sys.modules.get(mod_name) or importlib.import_module(mod_name)
    source = _pathlib.Path(mod.__file__).read_text(encoding="utf-8")
    forbidden_terms = [
        "import dotenv",
        "import py_clob_client",
        "import clob_client",
        "import keyring",
        "import cryptography",
        "from dotenv",
        "from py_clob_client",
        "os.getenv",
        "os.environ",
        ".env",
        "wallet",
        "private_key",
        "api_key",
    ]
    for term in forbidden_terms:
        assert term not in source, (
            f"Loader must not reference credentials or auth: '{term}'"
        )


# ---------------------------------------------------------------------------
# 16. Loader imports no LLM/agent libraries
# ---------------------------------------------------------------------------

def test_loader_does_not_import_llm_or_agent_libraries():
    loader_module = importlib.import_module("src.data_layer.human_review_label_fixture_loader")
    source = inspect.getsource(loader_module)
    forbidden_imports = [
        "import anthropic",
        "import openai",
        "import langchain",
        "import llama",
        "import hermes",
        "import agent",
        "import transformers",
    ]
    for lib in forbidden_imports:
        assert lib not in source, f"Loader must not import LLM/agent library: {lib}"


# ---------------------------------------------------------------------------
# 17. Loader does not scan directories recursively
# ---------------------------------------------------------------------------

def test_loader_source_does_not_use_rglob_or_walk():
    loader_module = importlib.import_module("src.data_layer.human_review_label_fixture_loader")
    source = inspect.getsource(loader_module)
    recursive_patterns = ["rglob", "os.walk", "glob.glob"]
    for pattern in recursive_patterns:
        assert pattern not in source, (
            f"Loader must not scan recursively; found: '{pattern}'"
        )


# ---------------------------------------------------------------------------
# 18. Loader does not create or edit labels
# ---------------------------------------------------------------------------

def test_loader_source_does_not_create_or_edit_labels():
    loader_module = importlib.import_module("src.data_layer.human_review_label_fixture_loader")
    source = inspect.getsource(loader_module)
    forbidden_patterns = [
        "auto_label",
        "llm_label",
        "automated_label",
        "create_label",
        "edit_label",
        "write_label",
        "apply_label",
    ]
    for pattern in forbidden_patterns:
        assert pattern not in source, (
            f"Loader must not create or edit labels; found: '{pattern}'"
        )


# ---------------------------------------------------------------------------
# 19. Loader does not compute score changes or trading/performance metrics
# ---------------------------------------------------------------------------

def test_loader_result_contains_no_forbidden_metric_fields():
    record = _valid_record()
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "r.json"
        path.write_text(json.dumps(record), encoding="utf-8")
        result = load_human_review_label_fixtures(path)

    result_fields = set(vars(result).keys())
    forbidden_fields = {
        "pnl", "profit", "roi", "expected_return", "win_rate", "sharpe",
        "trade_signal", "position_size", "fill_probability", "slippage",
        "edge", "alpha", "arbitrage", "score_change", "automated_label",
        "llm_label", "buy", "sell",
    }
    overlap = result_fields & forbidden_fields
    assert not overlap, (
        f"Loader result must not contain forbidden trading/performance fields: {overlap}"
    )


def test_loader_source_does_not_compute_trading_metrics():
    loader_module = importlib.import_module("src.data_layer.human_review_label_fixture_loader")
    source = inspect.getsource(loader_module)
    forbidden_patterns = [
        "score_change",
        "trade_signal",
        "win_rate",
        "expected_return",
        "position_size",
    ]
    for pattern in forbidden_patterns:
        assert pattern not in source, (
            f"Loader must not compute trading metrics; found: '{pattern}'"
        )


# ---------------------------------------------------------------------------
# 20. WP74 validator tests still pass (import check)
# ---------------------------------------------------------------------------

def test_wp74_validator_module_importable():
    from src.data_layer.human_review_label_validation import (  # noqa: F401
        validate_human_review_label_record,
        HumanReviewLabelValidationResult,
    )


def test_wp74_validate_human_review_label_record_works_correctly():
    from src.data_layer.human_review_label_validation import validate_human_review_label_record
    record = _valid_record()
    result = validate_human_review_label_record(record)
    assert result.is_valid
    assert result.missing_required_fields == ()
    assert result.invalid_fields == ()


# ---------------------------------------------------------------------------
# 21. WP73 human review label workflow docs tests still pass (import check)
# ---------------------------------------------------------------------------

def test_wp73_human_review_label_workflow_docs_module_importable():
    import tests.test_human_review_label_workflow_docs  # noqa: F401


# ---------------------------------------------------------------------------
# 22. Project status / docs tests pass (import check)
# ---------------------------------------------------------------------------

def test_project_status_docs_module_importable():
    import tests.test_project_status_docs  # noqa: F401


def test_calibration_harness_docs_module_importable():
    import tests.test_calibration_harness_docs  # noqa: F401


# ---------------------------------------------------------------------------
# 23. Full pytest compatibility checks
# ---------------------------------------------------------------------------

def test_loader_result_records_is_tuple():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "r.json"
        path.write_text(json.dumps(_valid_record()), encoding="utf-8")
        result = load_human_review_label_fixtures(path)

    assert isinstance(result.records, tuple)
    assert isinstance(result.errors, tuple)


def test_source_path_matches_input():
    record = _valid_record()
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "record.json"
        path.write_text(json.dumps(record), encoding="utf-8")
        result = load_human_review_label_fixtures(str(path))

    assert result.source_path == str(path)


def test_string_path_and_path_object_produce_same_result():
    record = _valid_record()
    with tempfile.TemporaryDirectory() as tmpdir:
        p = Path(tmpdir) / "r.json"
        p.write_text(json.dumps(record), encoding="utf-8")
        result_str = load_human_review_label_fixtures(str(p))
        result_path = load_human_review_label_fixtures(p)

    assert result_str.loaded_count == result_path.loaded_count
    assert result_str.valid_count == result_path.valid_count


def test_empty_json_object_loads_as_invalid_record():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "empty.json"
        path.write_text("{}", encoding="utf-8")
        result = load_human_review_label_fixtures(path)

    assert result.loaded_count == 1
    assert result.invalid_count == 1
    assert not result.records[0].validation.is_valid


def test_empty_directory_returns_error():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        (tmp / "notes.txt").write_text("not a json file", encoding="utf-8")
        result = load_human_review_label_fixtures(tmp)

    assert result.loaded_count == 0
    assert len(result.errors) >= 1
    assert any("no direct-child" in e.lower() or "*.json" in e for e in result.errors)


def test_non_json_files_in_directory_are_ignored():
    record = _valid_record()
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        (tmp / "record.json").write_text(json.dumps(record), encoding="utf-8")
        (tmp / "readme.txt").write_text("ignore me", encoding="utf-8")
        (tmp / "notes.md").write_text("# notes", encoding="utf-8")
        result = load_human_review_label_fixtures(tmp)

    assert result.loaded_count == 1
    assert result.valid_count == 1


def test_multiple_valid_records_from_directory_have_correct_counts():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        for i in range(3):
            rec = _valid_record()
            rec["identity"]["market_id"] = f"market-{i:03d}"
            (tmp / f"record_{i:03d}.json").write_text(json.dumps(rec), encoding="utf-8")
        result = load_human_review_label_fixtures(tmp)

    assert result.loaded_count == 3
    assert result.valid_count == 3
    assert result.invalid_count == 0
    assert result.errors == ()


def test_mixed_valid_invalid_records_have_correct_counts():
    valid_rec = _valid_record()
    invalid_rec = {"_notice": "ADVISORY_ONLY_MANUAL_RESEARCH_REVIEW_LABEL"}
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "mixed.json"
        path.write_text(json.dumps([valid_rec, invalid_rec]), encoding="utf-8")
        result = load_human_review_label_fixtures(path)

    assert result.loaded_count == 2
    assert result.valid_count == 1
    assert result.invalid_count == 1


def test_list_file_records_preserve_index_order():
    records = [_valid_record() for _ in range(4)]
    for i, r in enumerate(records):
        r["identity"]["market_id"] = f"market-{i}"
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "list.json"
        path.write_text(json.dumps(records), encoding="utf-8")
        result = load_human_review_label_fixtures(path)

    assert result.loaded_count == 4
    for i, rec in enumerate(result.records):
        assert rec.record_index == i
        assert rec.record["identity"]["market_id"] == f"market-{i}"


def test_advisory_label_present_in_result():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "r.json"
        path.write_text(json.dumps(_valid_record()), encoding="utf-8")
        result = load_human_review_label_fixtures(path)

    assert "ADVISORY_ONLY" in result.advisory_label
    assert "trading" in result.advisory_label.lower() or "performance" in result.advisory_label.lower()


def test_forbidden_key_in_record_produces_validator_warning():
    record = _valid_record()
    record["pnl"] = 100.0
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "forbidden.json"
        path.write_text(json.dumps(record), encoding="utf-8")
        result = load_human_review_label_fixtures(path)

    assert result.loaded_count == 1
    assert result.invalid_count == 1
    assert result.warning_count >= 1
    warnings = result.records[0].validation.warnings
    assert any("pnl" in w.lower() for w in warnings)


def test_loader_does_not_import_metric_computation_libraries():
    import pathlib as _pathlib
    mod_name = "src.data_layer.human_review_label_fixture_loader"
    mod = sys.modules.get(mod_name) or importlib.import_module(mod_name)
    source = _pathlib.Path(mod.__file__).read_text(encoding="utf-8")
    forbidden_imports = ["import numpy", "import pandas", "import scipy", "import sklearn"]
    for imp in forbidden_imports:
        assert imp not in source, (
            f"Loader must not import metric computation library: '{imp}'"
        )


def test_ftp_url_path_is_rejected():
    result = load_human_review_label_fixtures("ftp://example.com/records.json")
    assert result.loaded_count == 0
    assert any("URL-like" in e for e in result.errors)


def test_loaded_record_source_path_matches_file():
    record = _valid_record()
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "record.json"
        path.write_text(json.dumps(record), encoding="utf-8")
        result = load_human_review_label_fixtures(path)

    assert result.records[0].source_path == str(path)


def test_loaded_record_from_list_source_path_matches_file():
    records = [_valid_record(), _valid_record()]
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "list.json"
        path.write_text(json.dumps(records), encoding="utf-8")
        result = load_human_review_label_fixtures(path)

    for rec in result.records:
        assert rec.source_path == str(path)


def test_validation_result_is_frozen():
    record = _valid_record()
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "r.json"
        path.write_text(json.dumps(record), encoding="utf-8")
        result = load_human_review_label_fixtures(path)

    validation = result.records[0].validation
    with pytest.raises((AttributeError, TypeError)):
        validation.is_valid = False  # type: ignore[misc]


def test_directory_with_multiple_valid_files_records_sorted():
    names = ["z_record.json", "a_record.json", "m_record.json"]
    expected_ids = []
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        for name in names:
            rec = _valid_record()
            rec["identity"]["market_id"] = name.replace(".json", "")
            (tmp / name).write_text(json.dumps(rec), encoding="utf-8")
        result = load_human_review_label_fixtures(tmp)

    returned_ids = [r.record["identity"]["market_id"] for r in result.records]
    sorted_names = sorted(names)
    expected_ids = [n.replace(".json", "") for n in sorted_names]
    assert returned_ids == expected_ids


def test_empty_list_file_loads_zero_records():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "empty_list.json"
        path.write_text("[]", encoding="utf-8")
        result = load_human_review_label_fixtures(path)

    assert result.loaded_count == 0
    assert result.valid_count == 0
    assert result.invalid_count == 0
    assert result.errors == ()
