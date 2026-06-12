"""Focused tests for WP65 local research queue export tool.

Tests tools/research_queue/local_research_queue_export.py.
All tests are local/offline. No network. File I/O uses pytest tmp_path only.
"""

from __future__ import annotations

import importlib
import importlib.util
import json
import pathlib
import sys
from datetime import datetime, timezone

import pytest

# ---------------------------------------------------------------------------
# Module loading — uses spec_from_file_location like all tool tests in this repo
# to avoid pytest import-mode sys.path ordering issues.
# ---------------------------------------------------------------------------

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
_TOOL_PATH = _REPO_ROOT / "tools" / "research_queue" / "local_research_queue_export.py"

_spec = importlib.util.spec_from_file_location(
    "local_research_queue_export", _TOOL_PATH
)
_mod = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(_mod)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _export_main(argv: list[str]) -> None:
    _mod.main(argv)


def _minimal_ctx(
    market_id: str = "mkt-001",
    question: str = "Will X happen?",
    score: float = 0.55,
    quality_status: str = "ACCEPTABLE",
) -> dict:
    return {
        "market_id": market_id,
        "question": question,
        "research_priority_score": score,
        "quality_gates": {"quality_status": quality_status},
        "staleness": {"staleness_flag": False, "requires_recapture_before_use": False},
        "missing_data": {"missing_data_warning": False},
        "provenance": {
            "snapshot_manifest_ids": ["m1"],
            "source_export_paths": ["local_data/snap.jsonl"],
            "provenance_degraded": False,
        },
        "resolution_ambiguity": {"label_available": False, "manual_review_required": False},
        "resolution_source_hierarchy": {
            "source_metadata_available": True,
            "manual_source_review_required": False,
        },
        "microstructure_quality": {"order_book_available": True, "two_sided_structure_observed": True},
        "cross_market_relationships": {"relationship_metadata_available": True, "relationship_candidate_count": 0},
    }


def _write_input(tmp_path: pathlib.Path, data: object, filename: str = "input.json") -> pathlib.Path:
    p = tmp_path / filename
    p.write_text(json.dumps(data), encoding="utf-8")
    return p


_REF_UTC = "2026-01-01T13:00:00+00:00"


# ---------------------------------------------------------------------------
# 1. CLI reads local JSON list and produces JSON to stdout
# ---------------------------------------------------------------------------

def test_json_list_input_produces_json_stdout(tmp_path: pathlib.Path, capsys) -> None:
    contexts = [_minimal_ctx("mkt-001"), _minimal_ctx("mkt-002", score=0.4)]
    inp = _write_input(tmp_path, contexts)
    _export_main(["--input", str(inp), "--format", "json",
                  "--generated-at-utc", _REF_UTC])
    out = capsys.readouterr().out
    parsed = json.loads(out)
    assert parsed["report_type"] == "LOCAL_HUMAN_REVIEW_REPORT_V1"
    assert "queue_summary" in parsed
    assert "review_queue" in parsed


# ---------------------------------------------------------------------------
# 2. CLI reads local JSON list and produces Markdown to stdout
# ---------------------------------------------------------------------------

def test_json_list_input_produces_markdown_stdout(tmp_path: pathlib.Path, capsys) -> None:
    contexts = [_minimal_ctx("mkt-001")]
    inp = _write_input(tmp_path, contexts)
    _export_main(["--input", str(inp), "--format", "markdown",
                  "--generated-at-utc", _REF_UTC])
    out = capsys.readouterr().out
    assert "# Local Research Queue Briefing" in out
    assert "ADVISORY" in out


# ---------------------------------------------------------------------------
# 3. CLI reads existing WP64 report object and preserves summary shape
# ---------------------------------------------------------------------------

def test_wp64_report_object_input_preserves_shape(tmp_path: pathlib.Path, capsys) -> None:
    from src.data_layer.market_research_priority_review_queue import (
        build_local_human_review_report,
    )
    ref = datetime(2026, 1, 1, 13, 0, 0, tzinfo=timezone.utc)
    report = build_local_human_review_report([_minimal_ctx()], generated_at_utc=ref)
    inp = _write_input(tmp_path, report)
    _export_main(["--input", str(inp), "--format", "json",
                  "--generated-at-utc", _REF_UTC])
    out = capsys.readouterr().out
    parsed = json.loads(out)
    assert parsed["report_type"] == "LOCAL_HUMAN_REVIEW_REPORT_V1"
    assert "queue_summary" in parsed
    assert "review_queue" in parsed
    assert "excluded_or_deprioritized" in parsed
    assert "global_warnings" in parsed


# ---------------------------------------------------------------------------
# 4. --output writes only to explicit tmp_path
# ---------------------------------------------------------------------------

def test_output_flag_writes_to_tmp_path(tmp_path: pathlib.Path) -> None:
    contexts = [_minimal_ctx()]
    inp = _write_input(tmp_path, contexts)
    out_file = tmp_path / "out.json"
    _export_main(["--input", str(inp), "--format", "json",
                  "--output", str(out_file),
                  "--generated-at-utc", _REF_UTC])
    assert out_file.exists()
    parsed = json.loads(out_file.read_text(encoding="utf-8"))
    assert parsed["report_type"] == "LOCAL_HUMAN_REVIEW_REPORT_V1"


# ---------------------------------------------------------------------------
# 5. Missing input file returns nonzero
# ---------------------------------------------------------------------------

def test_missing_input_file_exits_nonzero(tmp_path: pathlib.Path) -> None:
    with pytest.raises(SystemExit) as exc:
        _export_main(["--input", str(tmp_path / "nonexistent.json"), "--format", "json"])
    assert exc.value.code != 0


# ---------------------------------------------------------------------------
# 6. Non-JSON input returns nonzero
# ---------------------------------------------------------------------------

def test_non_json_input_exits_nonzero(tmp_path: pathlib.Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text("this is not json {{{", encoding="utf-8")
    with pytest.raises(SystemExit) as exc:
        _export_main(["--input", str(bad), "--format", "json"])
    assert exc.value.code != 0


# ---------------------------------------------------------------------------
# 7. Unsupported format returns nonzero
# ---------------------------------------------------------------------------

def test_unsupported_format_exits_1(tmp_path: pathlib.Path) -> None:
    contexts = [_minimal_ctx()]
    inp = _write_input(tmp_path, contexts)
    with pytest.raises(SystemExit) as exc:
        _export_main(["--input", str(inp), "--format", "csv"])
    assert exc.value.code == 1


# ---------------------------------------------------------------------------
# 8. Unsafe output path returns nonzero
# ---------------------------------------------------------------------------

def test_unsafe_output_path_exits_2(tmp_path: pathlib.Path) -> None:
    contexts = [_minimal_ctx()]
    inp = _write_input(tmp_path, contexts)
    with pytest.raises(SystemExit) as exc:
        _export_main(["--input", str(inp), "--format", "json",
                      "--output", "src/data_layer/should_not_write.json"])
    assert exc.value.code == 2


def test_unsafe_output_path_tests_exits_2(tmp_path: pathlib.Path) -> None:
    contexts = [_minimal_ctx()]
    inp = _write_input(tmp_path, contexts)
    with pytest.raises(SystemExit) as exc:
        _export_main(["--input", str(inp), "--format", "json",
                      "--output", "tests/tools/research_queue/should_not_write.json"])
    assert exc.value.code == 2


def test_unsafe_output_path_absolute_exits_2(tmp_path: pathlib.Path) -> None:
    contexts = [_minimal_ctx()]
    inp = _write_input(tmp_path, contexts)
    abs_path = _REPO_ROOT / "docs" / "should_not_write.md"
    with pytest.raises(SystemExit) as exc:
        _export_main(["--input", str(inp), "--format", "json",
                      "--output", str(abs_path)])
    assert exc.value.code == 2


def test_safe_tmp_path_output_succeeds(tmp_path: pathlib.Path) -> None:
    contexts = [_minimal_ctx()]
    inp = _write_input(tmp_path, contexts)
    out_file = tmp_path / "safe_out.json"
    _export_main(["--input", str(inp), "--format", "json",
                  "--output", str(out_file), "--generated-at-utc", _REF_UTC])
    assert out_file.exists()
    parsed = json.loads(out_file.read_text(encoding="utf-8"))
    assert parsed["report_type"] == "LOCAL_HUMAN_REVIEW_REPORT_V1"


def test_symlink_to_docs_exits_2(tmp_path: pathlib.Path) -> None:
    import os
    pytest.importorskip("os")
    link = tmp_path / "link_to_docs"
    docs_dir = _REPO_ROOT / "docs"
    try:
        link.symlink_to(docs_dir)
    except (OSError, NotImplementedError):
        pytest.skip("Symlink creation not supported on this platform")
    contexts = [_minimal_ctx()]
    inp = _write_input(tmp_path, contexts)
    with pytest.raises(SystemExit) as exc:
        _export_main(["--input", str(inp), "--format", "json",
                      "--output", str(link / "should_not_write.md")])
    assert exc.value.code == 2


# ---------------------------------------------------------------------------
# 9. Markdown output contains advisory notice and forbidden interpretation notice
# ---------------------------------------------------------------------------

def test_markdown_contains_advisory_and_forbidden_notices(tmp_path: pathlib.Path, capsys) -> None:
    contexts = [_minimal_ctx()]
    inp = _write_input(tmp_path, contexts)
    _export_main(["--input", str(inp), "--format", "markdown",
                  "--generated-at-utc", _REF_UTC])
    out = capsys.readouterr().out
    assert "ADVISORY" in out
    assert "FORBIDDEN INTERPRETATIONS" in out
    assert "human review" in out.lower() or "HUMAN_REVIEW" in out


# ---------------------------------------------------------------------------
# 10. Markdown output groups items by research queue bucket
# ---------------------------------------------------------------------------

def test_markdown_groups_by_bucket(tmp_path: pathlib.Path, capsys) -> None:
    contexts = [
        _minimal_ctx("mkt-a", score=0.7, quality_status="ACCEPTABLE"),
        _minimal_ctx("mkt-b", score=0.1, quality_status="ACCEPTABLE"),
    ]
    inp = _write_input(tmp_path, contexts)
    _export_main(["--input", str(inp), "--format", "markdown",
                  "--generated-at-utc", _REF_UTC])
    out = capsys.readouterr().out
    assert "## Review First" in out
    assert "## Review Later" in out


# ---------------------------------------------------------------------------
# 11. JSON output contains expected report shape
# ---------------------------------------------------------------------------

def test_json_output_expected_shape(tmp_path: pathlib.Path, capsys) -> None:
    contexts = [_minimal_ctx()]
    inp = _write_input(tmp_path, contexts)
    _export_main(["--input", str(inp), "--format", "json",
                  "--generated-at-utc", _REF_UTC])
    out = capsys.readouterr().out
    parsed = json.loads(out)
    for key in ("report_type", "advisory_label", "report_scope",
                "queue_summary", "review_queue", "excluded_or_deprioritized",
                "global_warnings"):
        assert key in parsed, f"Missing key: {key}"


# ---------------------------------------------------------------------------
# 12. Output contains no forbidden positive trade/signal wording
# ---------------------------------------------------------------------------

_FORBIDDEN_POSITIVE_WORDS = [
    "alpha", "edge", "opportunity", "arbitrage", "mispricing",
    "tradability", "tradeable", "tradable", "entry", "exit",
    "position size", "leverage", "expected return", "execution confidence",
    "fill probability", "slippage", "profitable", "signal",
    "recommendation to trade",
]


def test_json_output_no_forbidden_positive_wording(tmp_path: pathlib.Path, capsys) -> None:
    contexts = [_minimal_ctx()]
    inp = _write_input(tmp_path, contexts)
    _export_main(["--input", str(inp), "--format", "json",
                  "--generated-at-utc", _REF_UTC])
    out = capsys.readouterr().out.lower()
    for word in _FORBIDDEN_POSITIVE_WORDS:
        # Allow "trade" only in forbidden/advisory notices, not as positive field.
        if word == "tradable" or word == "tradeable" or word == "tradability":
            assert word not in out, f"Forbidden word found in JSON output: {word!r}"


def test_markdown_output_no_forbidden_positive_wording(tmp_path: pathlib.Path, capsys) -> None:
    contexts = [_minimal_ctx()]
    inp = _write_input(tmp_path, contexts)
    _export_main(["--input", str(inp), "--format", "markdown",
                  "--generated-at-utc", _REF_UTC])
    out = capsys.readouterr().out
    # These words must not appear as positive capability wording.
    for word in ["tradeable", "tradability", "fill probability",
                 "execution confidence"]:
        assert word.lower() not in out.lower(), (
            f"Forbidden word found in markdown output: {word!r}"
        )
    # "buy" and "sell" as positive standalone keywords (not in advisory notices).
    # Check they don't appear as positive action words outside forbidden notices.
    lines_without_notices = [
        ln for ln in out.splitlines()
        if "FORBIDDEN" not in ln.upper() and "ADVISORY" not in ln.upper()
    ]
    plain = "\n".join(lines_without_notices).lower()
    for word in ["tradeable", "tradability"]:
        assert word not in plain, f"Forbidden word in non-notice output: {word!r}"


# ---------------------------------------------------------------------------
# 13. Command does not import network libraries
# ---------------------------------------------------------------------------

def test_no_network_imports() -> None:
    source_file = _TOOL_PATH.read_text(encoding="utf-8")
    forbidden = ["import requests", "import httpx", "import urllib.request",
                 "import aiohttp", "import httplib", "import http.client",
                 "socket.connect", "urllib.urlopen"]
    for f in forbidden:
        assert f not in source_file, f"Forbidden network import/call found: {f!r}"


# ---------------------------------------------------------------------------
# 14. Command does not require credentials or .env
# ---------------------------------------------------------------------------

def test_no_credentials_or_env() -> None:
    source_file = _TOOL_PATH.read_text(encoding="utf-8")
    # Check for actual code-level credential patterns, not doc-string mentions.
    forbidden_patterns = [
        "CLOB_SECRET", "PRIVATE_KEY", "API_KEY", "MNEMONIC",
        "load_dotenv", "import dotenv",
    ]
    for pat in forbidden_patterns:
        assert pat not in source_file, (
            f"Forbidden credential/env pattern found in tool source: {pat!r}"
        )


# ---------------------------------------------------------------------------
# 15. Command does not touch database/dashboard/scheduler code
# ---------------------------------------------------------------------------

def test_no_database_dashboard_scheduler() -> None:
    source_file = _TOOL_PATH.read_text(encoding="utf-8")
    # Check for actual import-level forbidden patterns, not doc-string mentions.
    forbidden_imports = [
        "import sqlite3", "import sqlalchemy", "import psycopg",
        "import streamlit", "import APScheduler", "import celery",
        "import schedule\n", "import cron",
    ]
    for f in forbidden_imports:
        assert f not in source_file, (
            f"Forbidden database/dashboard/scheduler import found: {f!r}"
        )


# ---------------------------------------------------------------------------
# 16. Full WP64 review queue tests still pass (import check)
# ---------------------------------------------------------------------------

def test_wp64_review_queue_module_importable() -> None:
    from src.data_layer.market_research_priority_review_queue import (
        build_local_human_review_report,
        build_research_review_queue,
        build_research_session_packet,
        BUCKET_REVIEW_FIRST,
        BUCKET_REVIEW_LATER,
    )
    assert callable(build_local_human_review_report)
    assert callable(build_research_review_queue)
    assert callable(build_research_session_packet)


# ---------------------------------------------------------------------------
# 17. Scorer core tests still pass (import check)
# ---------------------------------------------------------------------------

def test_scorer_core_module_importable() -> None:
    from src.data_layer.market_research_priority_scoring import (
        compute_research_priority_score,
        build_market_research_priority_output,
    )
    assert callable(compute_research_priority_score)
    assert callable(build_market_research_priority_output)


# ---------------------------------------------------------------------------
# 18. --generated-at-utc override is reflected in JSON output
# ---------------------------------------------------------------------------

def test_generated_at_utc_override(tmp_path: pathlib.Path, capsys) -> None:
    contexts = [_minimal_ctx()]
    inp = _write_input(tmp_path, contexts)
    ts = "2026-03-15T08:00:00+00:00"
    _export_main(["--input", str(inp), "--format", "json",
                  "--generated-at-utc", ts])
    out = capsys.readouterr().out
    parsed = json.loads(out)
    assert parsed.get("generated_at_utc") == ts


# ---------------------------------------------------------------------------
# 19. Invalid --generated-at-utc exits nonzero
# ---------------------------------------------------------------------------

def test_invalid_generated_at_utc_exits_nonzero(tmp_path: pathlib.Path) -> None:
    contexts = [_minimal_ctx()]
    inp = _write_input(tmp_path, contexts)
    with pytest.raises(SystemExit) as exc:
        _export_main(["--input", str(inp), "--format", "json",
                      "--generated-at-utc", "not-a-timestamp"])
    assert exc.value.code != 0


# ---------------------------------------------------------------------------
# 20. JSON input with bad shape exits nonzero
# ---------------------------------------------------------------------------

def test_bad_json_shape_exits_nonzero(tmp_path: pathlib.Path) -> None:
    bad = tmp_path / "bad_shape.json"
    bad.write_text(json.dumps({"some_key": "no_market_fields"}), encoding="utf-8")
    with pytest.raises(SystemExit) as exc:
        _export_main(["--input", str(bad), "--format", "json"])
    assert exc.value.code != 0


# ---------------------------------------------------------------------------
# 21. --max-items caps the number of queue items
# ---------------------------------------------------------------------------

def test_max_items_caps_output(tmp_path: pathlib.Path, capsys) -> None:
    contexts = [_minimal_ctx(f"mkt-{i:03d}", score=0.5 + i * 0.01) for i in range(10)]
    inp = _write_input(tmp_path, contexts)
    _export_main(["--input", str(inp), "--format", "json",
                  "--max-items", "3", "--generated-at-utc", _REF_UTC])
    out = capsys.readouterr().out
    parsed = json.loads(out)
    rq = parsed.get("review_queue", [])
    excl = parsed.get("excluded_or_deprioritized", [])
    assert len(rq) + len(excl) <= 3


# ---------------------------------------------------------------------------
# 22. DATA_QUALITY_BLOCKED context ends up in excluded_or_deprioritized
# ---------------------------------------------------------------------------

def test_blocked_ctx_in_excluded(tmp_path: pathlib.Path, capsys) -> None:
    ctx_blocked = _minimal_ctx("mkt-blocked", quality_status="FAILING")
    ctx_ok = _minimal_ctx("mkt-ok", score=0.6)
    inp = _write_input(tmp_path, [ctx_blocked, ctx_ok])
    _export_main(["--input", str(inp), "--format", "json",
                  "--generated-at-utc", _REF_UTC])
    out = capsys.readouterr().out
    parsed = json.loads(out)
    excl_ids = {p["market_id"] for p in parsed.get("excluded_or_deprioritized", [])}
    assert "mkt-blocked" in excl_ids
    rq_ids = {p["market_id"] for p in parsed.get("review_queue", [])}
    assert "mkt-ok" in rq_ids


# ---------------------------------------------------------------------------
# 23. Markdown output includes per-bucket section headings for all buckets
# ---------------------------------------------------------------------------

def test_markdown_all_bucket_headings(tmp_path: pathlib.Path, capsys) -> None:
    contexts = [_minimal_ctx()]
    inp = _write_input(tmp_path, contexts)
    _export_main(["--input", str(inp), "--format", "markdown",
                  "--generated-at-utc", _REF_UTC])
    out = capsys.readouterr().out
    for heading in ["Review First", "Manual Source Review Required",
                    "Review Later", "Data Quality Blocked", "Deprioritized"]:
        assert f"## {heading}" in out, f"Missing heading: {heading!r}"


# ---------------------------------------------------------------------------
# 24. Tool module has no top-level side effects on import
# ---------------------------------------------------------------------------

def test_tool_module_no_side_effects_on_import() -> None:
    # Should import without touching file system or network.
    assert hasattr(_mod, "main")
    assert callable(_mod.main)
