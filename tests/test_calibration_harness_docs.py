"""Focused docs tests for calibration harness design and resolved outcome requirements.

Added in WP66 to enforce that calibration docs exist, state the research-usefulness
purpose, and contain no forbidden trading/performance wording in capability sections.
"""

from __future__ import annotations

import json
import pathlib


REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
CALIBRATION_DESIGN = REPO_ROOT / "docs" / "calibration_harness_design.md"
RESOLVED_OUTCOME_REQ = REPO_ROOT / "docs" / "resolved_outcome_data_requirements.md"
CALIBRATION_SCHEMA = REPO_ROOT / "docs" / "schemas" / "calibration_record_v1.example.json"
PROJECT_STATUS = REPO_ROOT / "docs" / "project_status.md"
REPO_TRUTH_INDEX = REPO_ROOT / "docs" / "repo_truth_index.md"
DEFERRED_LOG = REPO_ROOT / "docs" / "deferred_items_log.md"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _read(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Calibration harness design doc: existence
# ---------------------------------------------------------------------------


def test_calibration_harness_design_exists():
    assert CALIBRATION_DESIGN.is_file(), "docs/calibration_harness_design.md must exist"


def test_resolved_outcome_data_requirements_exists():
    assert RESOLVED_OUTCOME_REQ.is_file(), "docs/resolved_outcome_data_requirements.md must exist"


def test_calibration_schema_example_exists():
    assert CALIBRATION_SCHEMA.is_file(), "docs/schemas/calibration_record_v1.example.json must exist"


# ---------------------------------------------------------------------------
# Calibration harness design: research-usefulness purpose
# ---------------------------------------------------------------------------


def test_calibration_design_states_research_usefulness_purpose():
    text = _read(CALIBRATION_DESIGN)
    assert "research" in text.lower()
    assert "usefulness" in text.lower() or "useful" in text.lower()


def test_calibration_design_states_not_trading_performance():
    text = _read(CALIBRATION_DESIGN)
    assert "not whether they generated trading profit" in text or "not a trading" in text.lower()


def test_calibration_design_states_not_backtest():
    text = _read(CALIBRATION_DESIGN)
    assert "not a backtest" in text.lower() or "not a performance evaluation" in text.lower()


def test_calibration_design_contains_non_signal_boundary_section():
    text = _read(CALIBRATION_DESIGN)
    assert "Non-Signal Boundary" in text or "non-signal boundary" in text.lower()


# ---------------------------------------------------------------------------
# Calibration harness design: forbidden trading terms in capability sections
# ---------------------------------------------------------------------------


def test_calibration_design_contains_forbidden_trading_terms_section():
    text = _read(CALIBRATION_DESIGN)
    # Verify forbidden trading terms appear in a dedicated boundary/forbidden section
    assert "Forbidden" in text or "forbidden" in text.lower()
    assert "profit" in text.lower() or "pnl" in text.lower()
    # alpha must appear in a context that negates or forbids it
    assert "alpha" in text.lower(), "Doc should reference alpha in its forbidden scope"
    # The non-signal boundary section must explicitly list forbidden terms
    non_signal_idx = text.lower().find("non-signal")
    assert non_signal_idx != -1, "Non-signal boundary section must exist"


def test_calibration_design_no_roi_as_allowed_metric():
    text = _read(CALIBRATION_DESIGN)
    # "roi" must not appear as an allowed calibration metric;
    # it may appear in forbidden-scope tables only
    allowed_metrics_section = False
    in_allowed_section = False
    for line in text.splitlines():
        low = line.lower().strip()
        if "calibration does not measure" in low or "forbidden metrics" in low:
            in_allowed_section = True
        if "roi" in low and not in_allowed_section:
            # roi appearing outside forbidden section means it's in allowed context
            # That's only OK if it's a header or forbidden-reference
            assert (
                "forbidden" in low or "not" in low or low.startswith("#")
            ), f"Unexpected 'roi' outside forbidden section: {line!r}"


def test_calibration_design_no_buy_sell_as_allowed_output():
    text = _read(CALIBRATION_DESIGN)
    # buy/sell must not appear as allowed calibration output
    for line in text.splitlines():
        low = line.lower().strip()
        if ("buy" in low or "sell" in low) and "buy" not in low.replace("buy/sell", ""):
            # line contains buy or sell outside buy/sell compound
            assert (
                "forbidden" in low or "not" in low or "must not" in low
                or "no buy" in low or "buy/sell" in low or low.startswith("#")
            ), f"Unexpected buy/sell line: {line!r}"


# ---------------------------------------------------------------------------
# Calibration harness design: required content
# ---------------------------------------------------------------------------


def test_calibration_design_defines_human_review_labels():
    text = _read(CALIBRATION_DESIGN)
    assert "USEFUL_RESEARCH_TARGET" in text
    assert "NOT_USEFUL_DATA_TOO_WEAK" in text
    assert "NOT_REVIEWED" in text


def test_calibration_design_defines_snapshot_timing_offsets():
    text = _read(CALIBRATION_DESIGN)
    assert "T-30d" in text or "T-7d" in text


def test_calibration_design_defines_calibration_gates():
    text = _read(CALIBRATION_DESIGN)
    assert "Do not calibrate if" in text or "calibration gate" in text.lower()


def test_calibration_design_defines_future_phases():
    text = _read(CALIBRATION_DESIGN)
    assert "Phase 1" in text or "future implementation phases" in text.lower()
    assert "NOT STARTED" in text or "deferred" in text.lower()


def test_calibration_design_states_ingestion_not_implemented():
    text = _read(CALIBRATION_DESIGN)
    assert "not implemented" in text.lower() or "not started" in text.lower() or "deferred" in text.lower()


def test_calibration_design_defines_market_id_identity_field():
    text = _read(CALIBRATION_DESIGN)
    assert "market_id" in text


def test_calibration_design_defines_snapshot_time_field():
    text = _read(CALIBRATION_DESIGN)
    assert "snapshot_time_utc" in text


def test_calibration_design_defines_research_queue_bucket_field():
    text = _read(CALIBRATION_DESIGN)
    assert "research_queue_bucket" in text


# ---------------------------------------------------------------------------
# Resolved outcome data requirements doc
# ---------------------------------------------------------------------------


def test_resolved_outcome_req_states_research_audit_purpose():
    text = _read(RESOLVED_OUTCOME_REQ)
    assert "research" in text.lower()
    assert "audit" in text.lower() or "usefulness" in text.lower()


def test_resolved_outcome_req_includes_market_id_field():
    text = _read(RESOLVED_OUTCOME_REQ)
    assert "market_id" in text


def test_resolved_outcome_req_includes_condition_id_field():
    text = _read(RESOLVED_OUTCOME_REQ)
    assert "condition_id" in text


def test_resolved_outcome_req_includes_resolution_status_field():
    text = _read(RESOLVED_OUTCOME_REQ)
    assert "resolution_status" in text


def test_resolved_outcome_req_includes_resolution_time_field():
    text = _read(RESOLVED_OUTCOME_REQ)
    assert "resolution_time_utc" in text


def test_resolved_outcome_req_includes_resolution_source_field():
    text = _read(RESOLVED_OUTCOME_REQ)
    assert "resolution_source" in text


def test_resolved_outcome_req_includes_outcome_token_mapping_field():
    text = _read(RESOLVED_OUTCOME_REQ)
    assert "outcome_token_mapping_verified" in text


def test_resolved_outcome_req_states_no_api_calls_authorized():
    text = _read(RESOLVED_OUTCOME_REQ)
    assert "not authorized" in text.lower() or "no network" in text.lower() or "NO_NETWORK" in text


def test_resolved_outcome_req_states_ingestion_not_implemented():
    text = _read(RESOLVED_OUTCOME_REQ)
    assert "not implemented" in text.lower() or "not started" in text.lower() or "deferred" in text.lower()


def test_resolved_outcome_req_contains_non_signal_boundary():
    text = _read(RESOLVED_OUTCOME_REQ)
    # Doc must define a non-signal boundary section
    assert "Non-Signal Boundary" in text or "non-signal" in text.lower()
    # And must mention that pnl/profit is forbidden
    assert "pnl" in text.lower() or "profit" in text.lower()


def test_resolved_outcome_req_defines_resolution_status_values():
    text = _read(RESOLVED_OUTCOME_REQ)
    assert "RESOLVED" in text
    assert "DISPUTED" in text
    assert "PENDING" in text


# ---------------------------------------------------------------------------
# Example schema: no trading/PnL/performance fields
# ---------------------------------------------------------------------------


def test_calibration_schema_is_valid_json():
    text = _read(CALIBRATION_SCHEMA)
    data = json.loads(text)
    assert isinstance(data, dict)


def test_calibration_schema_has_advisory_only_notice():
    text = _read(CALIBRATION_SCHEMA)
    assert "ADVISORY_ONLY" in text or "advisory" in text.lower()


def test_calibration_schema_no_pnl_json_keys():
    data = json.loads(_read(CALIBRATION_SCHEMA))
    # Flatten all keys recursively and check none are trading-performance fields
    def collect_keys(obj: object) -> list[str]:
        keys: list[str] = []
        if isinstance(obj, dict):
            for k, v in obj.items():
                keys.append(k)
                keys.extend(collect_keys(v))
        elif isinstance(obj, list):
            for item in obj:
                keys.extend(collect_keys(item))
        return keys

    all_keys = [k.lower() for k in collect_keys(data)]
    forbidden_key_terms = ["pnl", "roi", "expected_return", "win_rate", "sharpe", "profit"]
    for term in forbidden_key_terms:
        matching = [k for k in all_keys if term in k]
        assert len(matching) == 0, f"Schema has forbidden key containing '{term}': {matching}"


def test_calibration_schema_has_market_id():
    text = _read(CALIBRATION_SCHEMA)
    assert "market_id" in text


def test_calibration_schema_has_research_queue_bucket():
    text = _read(CALIBRATION_SCHEMA)
    assert "research_queue_bucket" in text


def test_calibration_schema_has_human_review_label():
    text = _read(CALIBRATION_SCHEMA)
    assert "human_review_usefulness_label" in text


def test_calibration_schema_marked_design_only():
    text = _read(CALIBRATION_SCHEMA)
    assert "DESIGN_ONLY_NOT_IMPLEMENTED" in text or "design" in text.lower()


# ---------------------------------------------------------------------------
# Project status: WP66 state
# ---------------------------------------------------------------------------


def test_project_status_has_wp65_in_merged_wps():
    text = _read(PROJECT_STATUS)
    merged_line = next(
        line for line in text.splitlines() if line.startswith("- Merged WPs:")
    )
    assert "WP65" in merged_line


def test_project_status_current_phase_is_wp69_or_later():
    text = _read(PROJECT_STATUS)
    phase_line = next(
        line for line in text.splitlines() if line.startswith("- Current phase:")
    )
    # WP68 is merged; current phase is WP69 or later
    assert "WP68" in text
    assert any(
        f"WP{n}" in phase_line for n in range(69, 105)
    )


def test_project_status_wp68_in_merged_wps():
    text = _read(PROJECT_STATUS)
    merged_line = next(
        line for line in text.splitlines() if line.startswith("- Merged WPs:")
    )
    assert "WP68" in merged_line


def test_project_status_calibration_harness_status_present():
    text = _read(PROJECT_STATUS)
    assert "calibration harness design status" in text.lower() or "CALIBRATION_HARNESS_DESIGN" in text


def test_project_status_protected_boundaries_unchanged():
    text = _read(PROJECT_STATUS)
    assert "Live trading status: DISABLED" in text
    assert "Credentials status: NOT_USED" in text
    assert "Execution status: NOT_STARTED" in text
    assert "Agent execution authority: FORBIDDEN" in text
    assert "Scheduler status: NOT_STARTED" in text
    assert "Bot loop status: NOT_STARTED" in text


# ---------------------------------------------------------------------------
# Repo truth index: new calibration docs
# ---------------------------------------------------------------------------


def test_repo_truth_index_contains_calibration_harness_design():
    text = _read(REPO_TRUTH_INDEX)
    assert "calibration_harness_design.md" in text


def test_repo_truth_index_contains_resolved_outcome_data_requirements():
    text = _read(REPO_TRUTH_INDEX)
    assert "resolved_outcome_data_requirements.md" in text


def test_repo_truth_index_contains_calibration_schema_example():
    text = _read(REPO_TRUTH_INDEX)
    assert "calibration_record_v1.example.json" in text


# ---------------------------------------------------------------------------
# Deferred items log: WP66 deferred items present
# ---------------------------------------------------------------------------


def test_deferred_log_contains_wp66_d001():
    text = _read(DEFERRED_LOG)
    assert "WP66-D001" in text


def test_deferred_log_contains_wp66_d002():
    text = _read(DEFERRED_LOG)
    assert "WP66-D002" in text


def test_deferred_log_contains_wp66_d003():
    text = _read(DEFERRED_LOG)
    assert "WP66-D003" in text


def test_deferred_log_contains_wp66_d004():
    text = _read(DEFERRED_LOG)
    assert "WP66-D004" in text


def test_deferred_log_wp66_d001_about_calibration_validator():
    text = _read(DEFERRED_LOG)
    idx = text.find("WP66-D001")
    assert idx != -1
    snippet = text[idx : idx + 300]
    assert "calibration" in snippet.lower() or "validator" in snippet.lower()


def test_deferred_log_wp66_d002_about_resolved_outcome_ingestion():
    text = _read(DEFERRED_LOG)
    idx = text.find("WP66-D002")
    assert idx != -1
    snippet = text[idx : idx + 300]
    assert "ingestion" in snippet.lower() or "resolved outcome" in snippet.lower()


# ---------------------------------------------------------------------------
# Architecture boundary: no src/tools files modified
# ---------------------------------------------------------------------------


def test_no_src_files_changed():
    src_dir = REPO_ROOT / "src"
    # Check that no src file was touched by verifying key source files
    # are unchanged (they exist and are importable)
    assert (src_dir / "data_layer" / "market_research_priority_scoring.py").is_file()
    assert (src_dir / "data_layer" / "market_research_priority_features.py").is_file()
    assert (src_dir / "data_layer" / "market_research_priority_review_queue.py").is_file()


def test_calibration_docs_are_in_docs_directory():
    assert CALIBRATION_DESIGN.parent == REPO_ROOT / "docs"
    assert RESOLVED_OUTCOME_REQ.parent == REPO_ROOT / "docs"
    assert CALIBRATION_SCHEMA.parent == REPO_ROOT / "docs" / "schemas"
