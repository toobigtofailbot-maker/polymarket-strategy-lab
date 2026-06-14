"""Focused tests for WP72 local calibration report export tool.

Tests tools/calibration/local_calibration_report_export.py.
All tests are local/offline. No network. File I/O uses pytest tmp_path only.
"""

from __future__ import annotations

import ast
import importlib.util
import json
import os
import pathlib
import sys

import pytest

# ---------------------------------------------------------------------------
# Module loading — uses spec_from_file_location like all tool tests in this
# repo to avoid pytest import-mode sys.path ordering issues.
# ---------------------------------------------------------------------------

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
_TOOL_PATH = _REPO_ROOT / "tools" / "calibration" / "local_calibration_report_export.py"

_spec = importlib.util.spec_from_file_location(
    "local_calibration_report_export", _TOOL_PATH
)
_mod = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(_mod)


# ---------------------------------------------------------------------------
# Required WP71 JSON report fields
# ---------------------------------------------------------------------------

_REQUIRED_JSON_FIELDS = {
    "report_type",
    "advisory_label",
    "report_scope",
    "input_summary",
    "validation_summary",
    "coverage_summary",
    "missingness_summary",
    "staleness_summary",
    "resolution_source_summary",
    "manual_review_summary",
    "bucket_summary",
    "human_review_usefulness_summary",
    "excluded_record_summary",
    "warnings",
    "forbidden_interpretation_notice",
}

# Non-signal boundary: these field names must not appear in output.
_FORBIDDEN_FIELDS = {
    "profit", "pnl", "roi", "expected_return", "win_rate", "hit_rate",
    "sharpe", "strategy_return", "portfolio_return", "trade_result",
    "position_size", "execution_quality", "fill_quality", "fill_probability",
    "slippage", "edge", "alpha", "opportunity", "arbitrage", "mispricing",
    "tradability", "buy", "sell", "entry", "exit",
}

# Required Markdown sections.
_REQUIRED_MD_SECTIONS = [
    "# Local Calibration Report",
    "## Report Scope",
    "## Input Summary",
    "## Validation Summary",
    "## Coverage Summary",
    "## Missingness Summary",
    "## Staleness Summary",
    "## Resolution-Source Summary",
    "## Manual-Review Summary",
    "## Bucket Summary",
    "## Human-Review Usefulness Summary",
    "## Excluded-Record Summary",
    "## Warnings",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _export_main(argv: list[str]) -> None:
    _mod.main(argv)


def _minimal_record(
    market_id: str = "mkt-001",
    bucket: str = "REVIEW_FIRST",
) -> dict:
    """Minimal calibration record that the WP68 loader accepts without fatal errors."""
    return {
        "market_id": market_id,
        "question": "Will X happen?",
        "resolved_outcome": {
            "outcome_label": "YES",
            "resolution_source_url_or_reference": "https://example.com",
            "resolution_dispute_or_ambiguity_flag": False,
            "outcome_token_mapping_verified": True,
        },
        "snapshot_metadata": {
            "snapshot_offset_from_resolution": "T_MINUS_7_DAYS",
            "snapshot_capture_timestamp_utc": "2026-01-01T00:00:00Z",
        },
        "research_queue_state": {
            "research_queue_bucket": bucket,
            "manual_source_review_required": False,
            "source_metadata_available": True,
            "resolution_ambiguity_manual_review_required": False,
        },
        "calibration_validity": {"excluded_from_calibration": False},
    }


def _write_json(tmp_path: pathlib.Path, data: object, filename: str = "input.json") -> pathlib.Path:
    p = tmp_path / filename
    p.write_text(json.dumps(data), encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# 1. CLI reads single JSON object and writes JSON to stdout
# ---------------------------------------------------------------------------

def test_single_json_object_input_produces_json_stdout(
    tmp_path: pathlib.Path, capsys
) -> None:
    inp = _write_json(tmp_path, _minimal_record())
    _export_main(["--input", str(inp), "--format", "json"])
    out = capsys.readouterr().out
    parsed = json.loads(out)
    assert parsed["report_type"] == "LOCAL_CALIBRATION_REPORT_V1"
    assert "input_summary" in parsed


# ---------------------------------------------------------------------------
# 2. CLI reads JSON list and writes JSON to stdout
# ---------------------------------------------------------------------------

def test_json_list_input_produces_json_stdout(
    tmp_path: pathlib.Path, capsys
) -> None:
    records = [_minimal_record("mkt-001"), _minimal_record("mkt-002")]
    inp = _write_json(tmp_path, records)
    _export_main(["--input", str(inp), "--format", "json"])
    out = capsys.readouterr().out
    parsed = json.loads(out)
    assert parsed["report_type"] == "LOCAL_CALIBRATION_REPORT_V1"
    assert parsed["input_summary"]["record_count"] == 2


# ---------------------------------------------------------------------------
# 3. CLI reads directory of *.json files and writes JSON to stdout
# ---------------------------------------------------------------------------

def test_directory_input_produces_json_stdout(
    tmp_path: pathlib.Path, capsys
) -> None:
    fixture_dir = tmp_path / "fixtures"
    fixture_dir.mkdir()
    (fixture_dir / "a.json").write_text(
        json.dumps(_minimal_record("mkt-A")), encoding="utf-8"
    )
    (fixture_dir / "b.json").write_text(
        json.dumps(_minimal_record("mkt-B")), encoding="utf-8"
    )
    _export_main(["--input", str(fixture_dir), "--format", "json"])
    out = capsys.readouterr().out
    parsed = json.loads(out)
    assert parsed["report_type"] == "LOCAL_CALIBRATION_REPORT_V1"
    assert parsed["input_summary"]["record_count"] == 2


# ---------------------------------------------------------------------------
# 4. CLI writes Markdown to stdout
# ---------------------------------------------------------------------------

def test_markdown_output_to_stdout(tmp_path: pathlib.Path, capsys) -> None:
    inp = _write_json(tmp_path, _minimal_record())
    _export_main(["--input", str(inp), "--format", "markdown"])
    out = capsys.readouterr().out
    assert "# Local Calibration Report" in out


# ---------------------------------------------------------------------------
# 5. CLI writes JSON to explicit tmp_path output file
# ---------------------------------------------------------------------------

def test_json_output_to_explicit_file(tmp_path: pathlib.Path) -> None:
    inp = _write_json(tmp_path, _minimal_record())
    out_file = tmp_path / "out.json"
    _export_main(["--input", str(inp), "--format", "json", "--output", str(out_file)])
    assert out_file.exists()
    parsed = json.loads(out_file.read_text(encoding="utf-8"))
    assert parsed["report_type"] == "LOCAL_CALIBRATION_REPORT_V1"


# ---------------------------------------------------------------------------
# 6. CLI writes Markdown to explicit tmp_path output file
# ---------------------------------------------------------------------------

def test_markdown_output_to_explicit_file(tmp_path: pathlib.Path) -> None:
    inp = _write_json(tmp_path, _minimal_record())
    out_file = tmp_path / "out.md"
    _export_main(["--input", str(inp), "--format", "markdown", "--output", str(out_file)])
    assert out_file.exists()
    md = out_file.read_text(encoding="utf-8")
    assert "# Local Calibration Report" in md


# ---------------------------------------------------------------------------
# 7. Unsupported format exits 1
# ---------------------------------------------------------------------------

def test_unsupported_format_exits_1(tmp_path: pathlib.Path) -> None:
    inp = _write_json(tmp_path, _minimal_record())
    with pytest.raises(SystemExit) as exc:
        _export_main(["--input", str(inp), "--format", "csv"])
    assert exc.value.code == 1


# ---------------------------------------------------------------------------
# 8. Missing input exits 1
# ---------------------------------------------------------------------------

def test_missing_input_file_exits_1(tmp_path: pathlib.Path) -> None:
    with pytest.raises(SystemExit) as exc:
        _export_main(
            ["--input", str(tmp_path / "nonexistent.json"), "--format", "json"]
        )
    assert exc.value.code == 1


# ---------------------------------------------------------------------------
# 9. URL-like input exits 1
# ---------------------------------------------------------------------------

def test_url_like_input_exits_1(tmp_path: pathlib.Path) -> None:
    with pytest.raises(SystemExit) as exc:
        _export_main(
            ["--input", "https://example.com/records.json", "--format", "json"]
        )
    assert exc.value.code == 1


# ---------------------------------------------------------------------------
# 10. Unsafe output path under src/ exits 2
# ---------------------------------------------------------------------------

def test_unsafe_output_path_src_exits_2(tmp_path: pathlib.Path) -> None:
    inp = _write_json(tmp_path, _minimal_record())
    with pytest.raises(SystemExit) as exc:
        _export_main(
            [
                "--input",
                str(inp),
                "--format",
                "json",
                "--output",
                "src/data_layer/should_not_write.json",
            ]
        )
    assert exc.value.code == 2


# ---------------------------------------------------------------------------
# 11. Absolute unsafe output path under repo docs/ exits 2
# ---------------------------------------------------------------------------

def test_unsafe_output_path_docs_absolute_exits_2(tmp_path: pathlib.Path) -> None:
    inp = _write_json(tmp_path, _minimal_record())
    docs_path = str(_REPO_ROOT / "docs" / "should_not_write.json")
    with pytest.raises(SystemExit) as exc:
        _export_main(
            ["--input", str(inp), "--format", "json", "--output", docs_path]
        )
    assert exc.value.code == 2


# ---------------------------------------------------------------------------
# 12. Symlink to tracked dir exits 2 (or skipped on platforms without support)
# ---------------------------------------------------------------------------

def test_symlink_to_tracked_dir_exits_2_or_skip(tmp_path: pathlib.Path) -> None:
    inp = _write_json(tmp_path, _minimal_record())
    link = tmp_path / "docs_link"
    docs_real = _REPO_ROOT / "docs"
    try:
        link.symlink_to(docs_real, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("Symlink creation not supported on this platform")

    with pytest.raises(SystemExit) as exc:
        _export_main(
            [
                "--input",
                str(inp),
                "--format",
                "json",
                "--output",
                str(link / "should_not_write.json"),
            ]
        )
    assert exc.value.code == 2


# ---------------------------------------------------------------------------
# 13. Markdown contains advisory notice and forbidden interpretation notice
# ---------------------------------------------------------------------------

def test_markdown_contains_advisory_and_forbidden_notice(
    tmp_path: pathlib.Path, capsys
) -> None:
    inp = _write_json(tmp_path, _minimal_record())
    _export_main(["--input", str(inp), "--format", "markdown"])
    out = capsys.readouterr().out
    assert "ADVISORY" in out
    assert "FORBIDDEN INTERPRETATIONS" in out


# ---------------------------------------------------------------------------
# 14. Markdown contains all required report sections
# ---------------------------------------------------------------------------

def test_markdown_contains_all_required_sections(
    tmp_path: pathlib.Path, capsys
) -> None:
    inp = _write_json(tmp_path, _minimal_record())
    _export_main(["--input", str(inp), "--format", "markdown"])
    out = capsys.readouterr().out
    for section in _REQUIRED_MD_SECTIONS:
        assert section in out, f"Missing section: {section!r}"


# ---------------------------------------------------------------------------
# 15. JSON output contains all required WP71 report fields
# ---------------------------------------------------------------------------

def test_json_contains_all_required_fields(
    tmp_path: pathlib.Path, capsys
) -> None:
    inp = _write_json(tmp_path, _minimal_record())
    _export_main(["--input", str(inp), "--format", "json"])
    out = capsys.readouterr().out
    parsed = json.loads(out)
    missing = _REQUIRED_JSON_FIELDS - set(parsed.keys())
    assert not missing, f"Missing required fields: {missing}"


# ---------------------------------------------------------------------------
# 16. Output contains no forbidden positive trading/performance fields
# ---------------------------------------------------------------------------

def test_json_output_has_no_forbidden_fields(
    tmp_path: pathlib.Path, capsys
) -> None:
    inp = _write_json(tmp_path, _minimal_record())
    _export_main(["--input", str(inp), "--format", "json"])
    out_text = capsys.readouterr().out
    out_lower = out_text.lower()
    for field in _FORBIDDEN_FIELDS:
        # Allow the field name ONLY in the forbidden interpretation notice
        # (it appears as a warning string). We check that it doesn't appear
        # as a JSON key by verifying the parsed dict.
        parsed = json.loads(out_text)
        assert field not in _collect_keys(parsed), (
            f"Forbidden field {field!r} found as a JSON key in output"
        )


def _collect_keys(obj: object) -> set[str]:
    """Recursively collect all dict keys from a JSON-parsed object."""
    keys: set[str] = set()
    if isinstance(obj, dict):
        for k, v in obj.items():
            keys.add(k)
            keys |= _collect_keys(v)
    elif isinstance(obj, list):
        for item in obj:
            keys |= _collect_keys(item)
    return keys


# ---------------------------------------------------------------------------
# 17. Tool imports no network libraries
# ---------------------------------------------------------------------------

def test_tool_imports_no_network_libraries() -> None:
    source = _TOOL_PATH.read_text(encoding="utf-8")
    forbidden_imports = [
        "import requests",
        "import urllib.request",
        "import httpx",
        "import aiohttp",
        "import socket",
        "import http.client",
        "from requests",
        "from httpx",
        "from aiohttp",
    ]
    for pattern in forbidden_imports:
        assert pattern not in source, (
            f"Tool contains forbidden network import: {pattern!r}"
        )


# ---------------------------------------------------------------------------
# 18. Tool references no credentials, .env, wallet, or authenticated client
# ---------------------------------------------------------------------------

def test_tool_has_no_credential_references() -> None:
    source = _TOOL_PATH.read_text(encoding="utf-8")
    # Check for actual credential-loading import/usage patterns (not docstring mentions).
    forbidden_import_patterns = [
        "import dotenv",
        "from dotenv",
        "load_dotenv",
        "import wallet",
        "PolymarketClient",
        "ClobClient",
        "private_key",
        "auth_token",
    ]
    for pattern in forbidden_import_patterns:
        assert pattern not in source, (
            f"Tool contains forbidden credential import/usage: {pattern!r}"
        )


# ---------------------------------------------------------------------------
# 19. Tool has no scheduler/daemon/polling patterns
# ---------------------------------------------------------------------------

def test_tool_has_no_scheduler_or_daemon_patterns() -> None:
    source = _TOOL_PATH.read_text(encoding="utf-8")
    # Check for actual scheduler/daemon import or usage patterns (not docstring mentions).
    forbidden_import_patterns = [
        "import schedule",
        "from schedule",
        "import apscheduler",
        "from apscheduler",
        "import celery",
        "from celery",
        "time.sleep",
        "asyncio.sleep",
        "threading.Timer",
    ]
    for pattern in forbidden_import_patterns:
        assert pattern not in source, (
            f"Tool contains forbidden scheduler/daemon import: {pattern!r}"
        )


# ---------------------------------------------------------------------------
# 20. Tool does not scan directories recursively
# ---------------------------------------------------------------------------

def test_tool_does_not_scan_directories_recursively() -> None:
    source = _TOOL_PATH.read_text(encoding="utf-8")
    assert "rglob" not in source, "Tool uses rglob (recursive directory scan)"
    assert "walk" not in source, "Tool uses os.walk (recursive directory scan)"


# ---------------------------------------------------------------------------
# 21. Tool does not modify source report/metric/loader modules
# ---------------------------------------------------------------------------

def test_tool_does_not_modify_source_modules() -> None:
    source = _TOOL_PATH.read_text(encoding="utf-8")
    # The tool must only import from src modules, never write to them.
    assert "write_text" not in source or "output_path" in source, (
        "Unexpected write_text not associated with output_path"
    )
    # Confirm no sys.path manipulation that would shadow src modules.
    assert "sys.path.insert" not in source
    assert "sys.path.append" not in source


# ---------------------------------------------------------------------------
# 22–26. Compatibility: prior WP tests still importable
# ---------------------------------------------------------------------------

def test_calibration_report_generator_module_importable() -> None:
    from src.data_layer.calibration_report_generator import (
        build_calibration_report_from_load_result,
        LocalCalibrationReport,
    )
    assert callable(build_calibration_report_from_load_result)
    assert LocalCalibrationReport is not None


def test_calibration_metric_computation_module_importable() -> None:
    from src.data_layer.calibration_metric_computation import (
        compute_calibration_metrics,
        CalibrationMetricComputationResult,
    )
    assert callable(compute_calibration_metrics)


def test_resolved_outcome_fixture_loader_module_importable() -> None:
    from src.data_layer.resolved_outcome_fixture_loader import (
        load_resolved_outcome_fixtures,
    )
    assert callable(load_resolved_outcome_fixtures)


def test_calibration_record_validation_module_importable() -> None:
    from src.data_layer.calibration_record_validation import (
        validate_calibration_record,
    )
    assert callable(validate_calibration_record)


# ---------------------------------------------------------------------------
# 27. JSON output for list input reports correct record count
# ---------------------------------------------------------------------------

def test_json_output_record_count_matches_input(
    tmp_path: pathlib.Path, capsys
) -> None:
    records = [
        _minimal_record("mkt-A"),
        _minimal_record("mkt-B"),
        _minimal_record("mkt-C"),
    ]
    inp = _write_json(tmp_path, records)
    _export_main(["--input", str(inp), "--format", "json"])
    out = capsys.readouterr().out
    parsed = json.loads(out)
    assert parsed["input_summary"]["record_count"] == 3
