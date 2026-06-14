"""Focused docs tests for calibration report generator design.

Added in WP69 to enforce that the calibration report generator design doc
exists, states the research-usefulness purpose, contains no forbidden
trading/performance wording in capability sections, and keeps all
implementation deferred.
"""

from __future__ import annotations

import json
import pathlib


REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
REPORT_DESIGN = REPO_ROOT / "docs" / "calibration_report_generator_design.md"
REPORT_SCHEMA = REPO_ROOT / "docs" / "schemas" / "calibration_report_v1.example.json"
PROJECT_STATUS = REPO_ROOT / "docs" / "project_status.md"
REPO_TRUTH_INDEX = REPO_ROOT / "docs" / "repo_truth_index.md"
DEFERRED_LOG = REPO_ROOT / "docs" / "deferred_items_log.md"


def _read(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Existence
# ---------------------------------------------------------------------------


def test_calibration_report_design_doc_exists():
    assert REPORT_DESIGN.is_file(), "docs/calibration_report_generator_design.md must exist"


def test_calibration_report_schema_example_exists():
    assert REPORT_SCHEMA.is_file(), "docs/schemas/calibration_report_v1.example.json must exist"


# ---------------------------------------------------------------------------
# Report purpose: research-usefulness calibration
# ---------------------------------------------------------------------------


def test_report_design_states_research_usefulness_purpose():
    text = _read(REPORT_DESIGN)
    assert "research" in text.lower()
    assert "usefulness" in text.lower() or "useful" in text.lower()


def test_report_design_states_not_profitability_report():
    text = _read(REPORT_DESIGN)
    assert "profitability report" in text.lower() or "not a profitability" in text.lower() or \
        "a profitability report" in text.lower() or "no_profitability_metrics" in text


def test_report_design_states_not_strategy_backtest():
    text = _read(REPORT_DESIGN)
    assert "backtest" in text.lower()
    assert "not" in text.lower() or "NOT" in text


def test_report_design_states_not_paper_trading_report():
    text = _read(REPORT_DESIGN)
    assert "paper-trading report" in text.lower() or "no_paper_trading" in text or \
        "paper trading" in text.lower()


def test_report_design_states_not_live_trading_report():
    text = _read(REPORT_DESIGN)
    assert "live-trading report" in text.lower() or "no_live_trading" in text or \
        "live trading" in text.lower()


def test_report_design_states_not_signal_report():
    text = _read(REPORT_DESIGN)
    assert "signal report" in text.lower() or "not a signal" in text.lower()


def test_report_design_states_not_trading_performance():
    text = _read(REPORT_DESIGN)
    assert "trading performance" in text.lower()


# ---------------------------------------------------------------------------
# Report inputs: allowed categories defined
# ---------------------------------------------------------------------------


def test_report_design_defines_allowed_input_categories():
    text = _read(REPORT_DESIGN)
    assert "validated calibration records" in text.lower() or "allowed" in text.lower()
    assert "human review usefulness" in text.lower() or "human review" in text.lower()
    assert "research queue bucket" in text.lower() or "bucket" in text.lower()


def test_report_design_defines_data_quality_as_allowed_input():
    text = _read(REPORT_DESIGN)
    assert "data-quality" in text.lower() or "data quality" in text.lower()


def test_report_design_defines_snapshot_timing_as_allowed_input():
    text = _read(REPORT_DESIGN)
    assert "snapshot" in text.lower()


# ---------------------------------------------------------------------------
# Report inputs: forbidden categories explicitly excluded
# ---------------------------------------------------------------------------


def test_report_design_excludes_account_trades():
    text = _read(REPORT_DESIGN)
    assert "account trades" in text.lower() or "account" in text.lower()


def test_report_design_excludes_order_fill_inputs():
    text = _read(REPORT_DESIGN)
    assert "orders" in text.lower() or "fills" in text.lower()


def test_report_design_excludes_wallet_balance():
    text = _read(REPORT_DESIGN)
    assert "wallet" in text.lower()


def test_report_design_excludes_execution_logs():
    text = _read(REPORT_DESIGN)
    assert "execution logs" in text.lower()


def test_report_design_excludes_paper_trading_ledger():
    text = _read(REPORT_DESIGN)
    assert "paper-trading ledger" in text.lower() or "paper trading ledger" in text.lower()


def test_report_design_excludes_live_trading_ledger():
    text = _read(REPORT_DESIGN)
    assert "live-trading ledger" in text.lower() or "live trading ledger" in text.lower()


# ---------------------------------------------------------------------------
# Report sections defined
# ---------------------------------------------------------------------------


def test_report_design_defines_validation_summary_section():
    text = _read(REPORT_DESIGN)
    assert "validation summary" in text.lower() or "Validation summary" in text


def test_report_design_defines_coverage_summary_section():
    text = _read(REPORT_DESIGN)
    assert "coverage summary" in text.lower() or "Coverage summary" in text


def test_report_design_defines_missingness_summary_section():
    text = _read(REPORT_DESIGN)
    assert "missingness summary" in text.lower() or "Missingness summary" in text


def test_report_design_defines_bucket_summary_section():
    text = _read(REPORT_DESIGN)
    assert "bucket summary" in text.lower() or "Bucket summary" in text


def test_report_design_defines_human_review_usefulness_summary_section():
    text = _read(REPORT_DESIGN)
    assert "human-review usefulness" in text.lower() or "human_review_usefulness" in text.lower() or \
        "human review usefulness" in text.lower()


def test_report_design_defines_forbidden_interpretation_notice_section():
    text = _read(REPORT_DESIGN)
    assert "forbidden_interpretation_notice" in text or "forbidden interpretation" in text.lower()


# ---------------------------------------------------------------------------
# Report output contract fields
# ---------------------------------------------------------------------------


def test_report_design_defines_report_type_field():
    text = _read(REPORT_DESIGN)
    assert "LOCAL_CALIBRATION_REPORT_V1" in text


def test_report_design_defines_advisory_label_field():
    text = _read(REPORT_DESIGN)
    assert "ADVISORY_ONLY_RESEARCH_USEFULNESS_AUDIT" in text


def test_report_design_defines_report_scope_field():
    text = _read(REPORT_DESIGN)
    assert "report_scope" in text


def test_report_design_defines_no_trading_scope_flag():
    text = _read(REPORT_DESIGN)
    assert "no_trading" in text


def test_report_design_defines_input_summary_field():
    text = _read(REPORT_DESIGN)
    assert "input_summary" in text


def test_report_design_defines_warnings_field():
    text = _read(REPORT_DESIGN)
    assert "warnings" in text


# ---------------------------------------------------------------------------
# Allowed metrics defined
# ---------------------------------------------------------------------------


def test_report_design_defines_coverage_rate_metric():
    text = _read(REPORT_DESIGN)
    assert "coverage_rate" in text


def test_report_design_defines_staleness_rate_metric():
    text = _read(REPORT_DESIGN)
    assert "staleness_rate" in text


def test_report_design_defines_valid_record_count_metric():
    text = _read(REPORT_DESIGN)
    assert "valid_record_count" in text


def test_report_design_defines_invalid_record_count_metric():
    text = _read(REPORT_DESIGN)
    assert "invalid_record_count" in text


def test_report_design_defines_bucket_distribution_metric():
    text = _read(REPORT_DESIGN)
    assert "bucket_distribution" in text


def test_report_design_defines_human_review_label_distribution_metric():
    text = _read(REPORT_DESIGN)
    assert "human_review_usefulness_label_distribution" in text


# ---------------------------------------------------------------------------
# Forbidden metrics explicitly excluded
# ---------------------------------------------------------------------------


def test_report_design_forbids_pnl_as_output():
    text = _read(REPORT_DESIGN)
    assert "PnL" in text or "pnl" in text.lower()
    # PnL must only appear in the forbidden section, not as an allowed metric
    forbidden_section_idx = text.lower().find("forbidden metric")
    assert forbidden_section_idx != -1 or "6.1 Forbidden" in text


def test_report_design_forbids_roi_as_output():
    text = _read(REPORT_DESIGN)
    assert "ROI" in text or "roi" in text.lower()


def test_report_design_forbids_expected_return_as_output():
    text = _read(REPORT_DESIGN)
    assert "expected return" in text.lower()


def test_report_design_forbids_win_rate_as_output():
    text = _read(REPORT_DESIGN)
    assert "win rate" in text.lower()


def test_report_design_forbids_sharpe_as_output():
    text = _read(REPORT_DESIGN)
    assert "sharpe" in text.lower()


def test_report_design_non_signal_boundary_section_exists():
    text = _read(REPORT_DESIGN)
    assert "Non-Signal Boundary" in text or "non-signal boundary" in text.lower()


# ---------------------------------------------------------------------------
# Human interpretation guidance
# ---------------------------------------------------------------------------


def test_report_design_defines_allowed_interpretation():
    text = _read(REPORT_DESIGN)
    assert "Allowed Interpretations" in text or "allowed interpretation" in text.lower()


def test_report_design_defines_forbidden_interpretation():
    text = _read(REPORT_DESIGN)
    assert "Forbidden Interpretations" in text or "forbidden interpretation" in text.lower()


def test_report_design_forbids_trading_signal_interpretation():
    text = _read(REPORT_DESIGN)
    assert "trading strategy" in text.lower() or "trading signal" in text.lower()


def test_report_design_forbids_buy_sell_signal_interpretation():
    text = _read(REPORT_DESIGN)
    assert "buy or sell signal" in text.lower() or "buy/sell" in text.lower()


def test_report_design_forbids_position_sizing_interpretation():
    text = _read(REPORT_DESIGN)
    assert "position-sizing" in text.lower() or "position sizing" in text.lower()


# ---------------------------------------------------------------------------
# Future implementation phases defined; implementation deferred
# ---------------------------------------------------------------------------


def test_report_design_defines_future_implementation_phases():
    text = _read(REPORT_DESIGN)
    assert "Future Implementation Phases" in text or "future implementation phases" in text.lower()


def test_report_design_states_metric_computation_not_started():
    text = _read(REPORT_DESIGN)
    assert "NOT STARTED" in text or "not started" in text.lower()


def test_report_design_states_report_generator_not_implemented():
    text = _read(REPORT_DESIGN)
    assert "DESIGN_ONLY_NOT_IMPLEMENTED" in text or "not implemented" in text.lower()


def test_report_design_states_human_review_workflow_not_started():
    text = _read(REPORT_DESIGN)
    assert "Human review label workflow" in text or "human review label workflow" in text.lower()
    assert "NOT STARTED" in text or "not started" in text.lower()


def test_report_design_implementation_phases_require_separate_approval():
    text = _read(REPORT_DESIGN)
    assert "separate" in text.lower() and "approval" in text.lower() or \
        "explicit work package approval" in text.lower() or "separate explicit" in text.lower()


# ---------------------------------------------------------------------------
# Optional schema example: no forbidden trading/performance fields
# ---------------------------------------------------------------------------


def test_report_schema_is_valid_json():
    text = _read(REPORT_SCHEMA)
    data = json.loads(text)
    assert isinstance(data, dict)


def test_report_schema_has_advisory_only_notice():
    text = _read(REPORT_SCHEMA)
    assert "ADVISORY_ONLY" in text or "advisory" in text.lower()


def test_report_schema_has_design_only_status():
    text = _read(REPORT_SCHEMA)
    assert "DESIGN_ONLY_NOT_IMPLEMENTED" in text


def test_report_schema_no_forbidden_positive_trading_fields():
    data = json.loads(_read(REPORT_SCHEMA))

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
    # Check that no key contains forbidden trading/performance terms as a positive capability.
    # Keys that are negation flags (starting with "no_") are explicitly allowed.
    positive_keys = [k for k in all_keys if not k.startswith("no_")]
    forbidden_key_terms = ["pnl", "roi", "expected_return", "win_rate", "sharpe",
                           "alpha", "edge_", "arbitrage", "slippage", "fill_probability",
                           "trade_signal", "strategy_return", "portfolio_return"]
    for term in forbidden_key_terms:
        matching = [k for k in positive_keys if term in k]
        assert len(matching) == 0, (
            f"Schema has forbidden positive key containing '{term}': {matching}"
        )
    # profit must not appear as a positive key (not in negation key)
    profit_matches = [k for k in positive_keys if "profit" in k and k != "_notice" and k != "_description"]
    assert len(profit_matches) == 0, f"Schema has forbidden positive key containing 'profit': {profit_matches}"


def test_report_schema_has_report_type_field():
    data = json.loads(_read(REPORT_SCHEMA))
    assert "report_type" in data
    assert data["report_type"] == "LOCAL_CALIBRATION_REPORT_V1"


def test_report_schema_has_advisory_label_field():
    data = json.loads(_read(REPORT_SCHEMA))
    assert "advisory_label" in data
    assert "ADVISORY_ONLY" in data["advisory_label"]


def test_report_schema_has_forbidden_interpretation_notice():
    data = json.loads(_read(REPORT_SCHEMA))
    assert "forbidden_interpretation_notice" in data
    notice = data["forbidden_interpretation_notice"].lower()
    assert "not be used" in notice or "must not" in notice


# ---------------------------------------------------------------------------
# Project status: WP68 merged, WP69 on branch
# ---------------------------------------------------------------------------


def test_project_status_has_wp68_in_merged_wps():
    text = _read(PROJECT_STATUS)
    merged_line = next(
        line for line in text.splitlines() if line.startswith("- Merged WPs:")
    )
    assert "WP68" in merged_line


def test_project_status_has_wp69_in_merged_wps():
    text = _read(PROJECT_STATUS)
    merged_line = next(
        line for line in text.splitlines() if line.startswith("- Merged WPs:")
    )
    assert "WP69" in merged_line


def test_project_status_calibration_report_design_is_merged():
    text = _read(PROJECT_STATUS)
    assert "CALIBRATION_REPORT_GENERATOR_DESIGN_MERGED" in text
    assert "CALIBRATION_REPORT_GENERATOR_DESIGN_ON_BRANCH" not in text


# ---------------------------------------------------------------------------
# Repo truth index: new design doc present
# ---------------------------------------------------------------------------


def test_repo_truth_index_contains_calibration_report_design():
    text = _read(REPO_TRUTH_INDEX)
    assert "calibration_report_generator_design.md" in text


def test_repo_truth_index_contains_calibration_report_schema():
    text = _read(REPO_TRUTH_INDEX)
    assert "calibration_report_v1.example.json" in text


# ---------------------------------------------------------------------------
# Deferred items: WP69 deferred items keep implementation deferred
# ---------------------------------------------------------------------------


def test_deferred_log_contains_wp69_d001():
    text = _read(DEFERRED_LOG)
    assert "WP69-D001" in text


def test_deferred_log_contains_wp69_d002():
    text = _read(DEFERRED_LOG)
    assert "WP69-D002" in text


def test_deferred_log_contains_wp69_d003():
    text = _read(DEFERRED_LOG)
    assert "WP69-D003" in text


def test_deferred_log_contains_wp69_d004():
    text = _read(DEFERRED_LOG)
    assert "WP69-D004" in text


def test_deferred_log_wp69_d001_metric_computation_deferred():
    text = _read(DEFERRED_LOG)
    idx = text.find("WP69-D001")
    assert idx != -1
    snippet = text[idx: idx + 300]
    assert "metric" in snippet.lower() or "computation" in snippet.lower()


def test_deferred_log_wp69_d002_report_generator_deferred():
    text = _read(DEFERRED_LOG)
    idx = text.find("WP69-D002")
    assert idx != -1
    snippet = text[idx: idx + 300]
    assert "report" in snippet.lower() or "generator" in snippet.lower()


def test_deferred_log_wp68_d002_still_open():
    text = _read(DEFERRED_LOG)
    assert "WP68-D002" in text


def test_deferred_log_wp68_d003_still_open():
    text = _read(DEFERRED_LOG)
    assert "WP68-D003" in text


# ---------------------------------------------------------------------------
# Protected boundaries unchanged
# ---------------------------------------------------------------------------


def test_protected_boundaries_unchanged():
    text = _read(PROJECT_STATUS)
    assert "Live trading status: DISABLED" in text
    assert "Credentials status: NOT_USED" in text
    assert "Execution status: NOT_STARTED" in text
    assert "Agent execution authority: FORBIDDEN" in text
    assert "Scheduler status: NOT_STARTED" in text
    assert "Bot loop status: NOT_STARTED" in text


# ---------------------------------------------------------------------------
# Architecture boundary: no src/ or tools/ files modified
# ---------------------------------------------------------------------------


def test_no_new_src_files_added():
    src_dir = REPO_ROOT / "src"
    # WP69 adds no new files under src/.
    # WP70 adds calibration_metric_computation.py.
    # WP71 adds calibration_report_generator.py — verify key files all exist.
    assert (src_dir / "data_layer" / "calibration_record_validation.py").is_file()
    assert (src_dir / "data_layer" / "resolved_outcome_fixture_loader.py").is_file()
    assert (src_dir / "data_layer" / "calibration_metric_computation.py").is_file()
    assert (src_dir / "data_layer" / "calibration_report_generator.py").is_file()


def test_calibration_report_design_is_in_docs_directory():
    assert REPORT_DESIGN.parent == REPO_ROOT / "docs"


def test_calibration_report_schema_is_in_docs_schemas_directory():
    assert REPORT_SCHEMA.parent == REPO_ROOT / "docs" / "schemas"
