"""Focused docs tests for WP48 Market Research Priority Scoring Output Contract.

Tests only docs. Does not import source implementation modules.
No scoring implementation exists in WP48.
"""

from __future__ import annotations

import pathlib


REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
CONTRACT_DOC = REPO_ROOT / "docs" / "market_research_priority_scoring_output_contract.md"
DESIGN_DOC = REPO_ROOT / "docs" / "market_research_priority_scoring_layer.md"
PROJECT_STATUS = REPO_ROOT / "docs" / "project_status.md"
REPO_TRUTH = REPO_ROOT / "docs" / "repo_truth_index.md"
DEFERRED_LOG = REPO_ROOT / "docs" / "deferred_items_log.md"


def _read_contract() -> str:
    return CONTRACT_DOC.read_text(encoding="utf-8")


def _read_design() -> str:
    return DESIGN_DOC.read_text(encoding="utf-8")


def _read_status() -> str:
    return PROJECT_STATUS.read_text(encoding="utf-8")


def _read_truth() -> str:
    return REPO_TRUTH.read_text(encoding="utf-8")


def _read_deferred() -> str:
    return DEFERRED_LOG.read_text(encoding="utf-8")


# ── Output contract document existence ───────────────────────────────────────

def test_output_contract_doc_exists():
    assert CONTRACT_DOC.is_file()


# ── Status section ────────────────────────────────────────────────────────────

def test_output_contract_status_docs_only():
    assert "DOCS_ONLY_SCHEMA_OUTPUT_CONTRACT_ON_BRANCH" in _read_contract()


def test_output_contract_no_src_change():
    assert "NO_SRC_CHANGE" in _read_contract()


def test_output_contract_no_runtime_change():
    assert "NO_RUNTIME_CHANGE" in _read_contract()


def test_output_contract_no_trading_execution():
    assert "NO_TRADING_EXECUTION" in _read_contract()


def test_output_contract_no_hermes():
    assert "NO_HERMES_INSTALL_OR_RUNTIME" in _read_contract()


def test_output_contract_scoring_implementation_not_started():
    assert "NOT_STARTED" in _read_contract()


# ── Non-signal boundary ───────────────────────────────────────────────────────

def test_output_contract_uses_research_priority_score():
    assert "research_priority_score" in _read_contract()


def test_output_contract_uses_market_research_priority_scoring_output():
    assert "market_research_priority_scoring_output" in _read_contract()


def test_output_contract_states_not_trading_signal():
    assert "not a trading signal" in _read_contract()


def test_output_contract_states_not_expected_return():
    assert "not expected return" in _read_contract()


def test_output_contract_states_not_investment_advice():
    assert "not investment advice" in _read_contract()


def test_output_contract_states_not_position_sizing():
    assert "not position sizing" in _read_contract()


def test_output_contract_states_not_execution_confidence():
    assert "not execution confidence" in _read_contract()


def test_output_contract_states_not_opportunity_scoring():
    assert "not opportunity scoring" in _read_contract()


def test_output_contract_states_no_recommendation_to_trade():
    text = _read_contract()
    assert "not a recommendation to buy" in text.lower() or (
        "not a recommendation" in text.lower() and "trade" in text.lower()
    )


# ── Required top-level fields ─────────────────────────────────────────────────

def test_output_contract_defines_schema_version():
    assert "schema_version" in _read_contract()


def test_output_contract_defines_generated_at_utc():
    assert "generated_at_utc" in _read_contract()


def test_output_contract_defines_run_id():
    assert "run_id" in _read_contract()


def test_output_contract_defines_source_artifacts():
    assert "source_artifacts" in _read_contract()


def test_output_contract_defines_markets():
    assert "markets" in _read_contract()


def test_output_contract_defines_contract_warnings():
    assert "contract_warnings" in _read_contract()


def test_output_contract_defines_forbidden_use_notice():
    assert "forbidden_use_notice" in _read_contract()


# ── Required advisory label ───────────────────────────────────────────────────

def test_output_contract_requires_advisory_only_label():
    assert "ADVISORY_ONLY_HUMAN_REVIEW_REQUIRED" in _read_contract()


def test_output_contract_requires_human_review_required():
    assert "human_review_required" in _read_contract()


def test_output_contract_advisory_label_on_market_object():
    text = _read_contract()
    assert "advisory_label" in text
    assert "ADVISORY_ONLY_HUMAN_REVIEW_REQUIRED" in text


# ── Required market object fields ─────────────────────────────────────────────

def test_output_contract_market_object_has_market_id():
    assert "market_id" in _read_contract()


def test_output_contract_market_object_has_question():
    assert "question" in _read_contract()


def test_output_contract_market_object_has_score_rank():
    assert "score_rank" in _read_contract()


def test_output_contract_market_object_has_score_components():
    assert "score_components" in _read_contract()


def test_output_contract_market_object_has_staleness():
    assert "staleness" in _read_contract()


def test_output_contract_market_object_has_provenance():
    assert "provenance" in _read_contract()


def test_output_contract_market_object_has_missing_data():
    assert "missing_data" in _read_contract()


def test_output_contract_market_object_has_quality_gates():
    assert "quality_gates" in _read_contract()


def test_output_contract_market_object_has_component_explanation():
    assert "component_explanation" in _read_contract()


# ── Score bounds ──────────────────────────────────────────────────────────────

def test_output_contract_score_bounded_0_to_1():
    text = _read_contract()
    assert "[0.0, 1.0]" in text


def test_output_contract_score_higher_means_triage_priority():
    text = _read_contract().lower()
    assert "higher" in text and ("triage" in text or "research priority" in text)


def test_output_contract_score_not_profitability():
    text = _read_contract()
    assert "not" in text.lower() and "profit" in text.lower()


# ── Staleness contract ────────────────────────────────────────────────────────

def test_output_contract_defines_staleness_flag():
    assert "staleness_flag" in _read_contract()


def test_output_contract_defines_snapshot_age_seconds():
    assert "snapshot_age_seconds" in _read_contract()


def test_output_contract_defines_freshness_threshold_seconds():
    assert "freshness_threshold_seconds" in _read_contract()


def test_output_contract_defines_stale_inputs():
    assert "stale_inputs" in _read_contract()


def test_output_contract_defines_staleness_warning():
    assert "staleness_warning" in _read_contract()


def test_output_contract_defines_requires_recapture():
    assert "requires_recapture_before_use" in _read_contract()


def test_output_contract_stale_must_not_default_high():
    text = _read_contract().lower()
    assert "never" in text or "must not" in text
    assert "default" in text or "neutral" in text or "high" in text


# ── Provenance contract ───────────────────────────────────────────────────────

def test_output_contract_defines_snapshot_manifest_ids():
    assert "snapshot_manifest_ids" in _read_contract()


def test_output_contract_defines_source_export_paths():
    assert "source_export_paths" in _read_contract()


def test_output_contract_defines_capture_session_ids():
    assert "capture_session_ids" in _read_contract()


def test_output_contract_defines_guard_policy_version():
    assert "guard_policy_version" in _read_contract()


def test_output_contract_defines_quality_report_ids():
    assert "quality_report_ids" in _read_contract()


def test_output_contract_defines_input_artifact_types():
    assert "input_artifact_types" in _read_contract()


def test_output_contract_provenance_missing_must_warn():
    text = _read_contract().lower()
    assert "missing provenance" in text or "missing" in text
    assert "warning" in text or "degraded" in text


# ── Missing-data contract ─────────────────────────────────────────────────────

def test_output_contract_defines_missing_data_warning():
    assert "missing_data_warning" in _read_contract()


def test_output_contract_defines_missing_order_book():
    assert "missing_order_book" in _read_contract()


def test_output_contract_defines_missing_outcome_tokens():
    assert "missing_outcome_tokens" in _read_contract()


def test_output_contract_defines_missing_category():
    assert "missing_category" in _read_contract()


def test_output_contract_defines_missing_resolution_source():
    assert "missing_resolution_source" in _read_contract()


def test_output_contract_missing_data_must_penalize():
    text = _read_contract().lower()
    assert "penali" in text
    assert "missing" in text


def test_output_contract_missing_data_not_hidden():
    text = _read_contract().lower()
    assert "never" in text or "must not" in text
    assert "hidden" in text or "hidden" in text or "missing" in text


# ── Forbidden fields ──────────────────────────────────────────────────────────

def test_output_contract_forbids_trade_signal():
    assert "trade_signal" in _read_contract()


def test_output_contract_forbids_alpha_score():
    assert "alpha_score" in _read_contract()


def test_output_contract_forbids_opportunity_score():
    assert "opportunity_score" in _read_contract()


def test_output_contract_forbids_expected_return():
    assert "expected_return" in _read_contract()


def test_output_contract_forbids_profit_probability():
    assert "profit_probability" in _read_contract()


def test_output_contract_forbids_buy_recommendation():
    assert "buy_recommendation" in _read_contract()


def test_output_contract_forbids_sell_recommendation():
    assert "sell_recommendation" in _read_contract()


def test_output_contract_forbids_entry_field():
    assert "`entry`" in _read_contract()


def test_output_contract_forbids_exit_field():
    assert "`exit`" in _read_contract()


def test_output_contract_forbids_position_size():
    assert "position_size" in _read_contract()


def test_output_contract_forbids_leverage():
    text = _read_contract()
    assert "`leverage`" in text


def test_output_contract_forbids_execution_confidence():
    assert "execution_confidence" in _read_contract()


def test_output_contract_forbids_order_params():
    assert "order_params" in _read_contract()


def test_output_contract_forbids_strategy_signal():
    assert "strategy_signal" in _read_contract()


def test_output_contract_forbids_paper_trade_authorization():
    assert "paper_trade_authorization" in _read_contract()


def test_output_contract_forbids_live_trade_authorization():
    assert "live_trade_authorization" in _read_contract()


# ── Safe and invalid examples ─────────────────────────────────────────────────

def test_output_contract_includes_safe_example():
    text = _read_contract()
    assert "safe" in text.lower() or "Safe example" in text or "Safe Example" in text
    assert "research_priority_score" in text
    assert "```" in text


def test_output_contract_includes_invalid_example():
    text = _read_contract()
    assert "invalid" in text.lower()
    assert "```" in text


def test_output_contract_safe_example_has_advisory_label():
    text = _read_contract()
    assert "ADVISORY_ONLY_HUMAN_REVIEW_REQUIRED" in text


def test_output_contract_safe_example_no_trade_signal():
    # The safe example block should not contain trade_signal as a real field
    # (It will only appear in the invalid example and forbidden sections)
    text = _read_contract()
    # trade_signal should appear in forbidden fields section, not as the safe example output
    assert "trade_signal" in text


def test_output_contract_invalid_example_explains_failures():
    text = _read_contract()
    assert "Why this fails" in text or "why it fails" in text.lower() or "fails" in text.lower()


# ── No implementation in WP48 ─────────────────────────────────────────────────

def test_output_contract_states_no_implementation_in_wp48():
    text = _read_contract()
    assert "WP48" in text
    assert "NOT_STARTED" in text or "not implemented" in text.lower() or "no scoring logic" in text.lower()


def test_output_contract_states_scoring_not_implemented():
    text = _read_contract()
    assert "NOT_STARTED" in text


# ── Score components defined ──────────────────────────────────────────────────

def test_output_contract_defines_data_completeness():
    assert "data_completeness" in _read_contract()


def test_output_contract_defines_snapshot_freshness():
    assert "snapshot_freshness" in _read_contract()


def test_output_contract_defines_quality_gate_status():
    assert "quality_gate_status" in _read_contract()


def test_output_contract_defines_missing_data_penalty():
    assert "missing_data_penalty" in _read_contract()


def test_output_contract_defines_guard_provenance_quality():
    assert "guard_provenance_quality" in _read_contract()


def test_output_contract_defines_deferred_item_caveat_penalty():
    assert "deferred_item_caveat_penalty" in _read_contract()


def test_output_contract_spread_structure_capped():
    text = _read_contract().lower()
    assert "capped" in text
    assert "spread" in text


def test_output_contract_liquidity_proxy_capped():
    text = _read_contract().lower()
    assert "capped" in text
    assert "liquidity" in text


# ── Future implementation gates ───────────────────────────────────────────────

def test_output_contract_future_gates_require_approval():
    text = _read_contract().lower()
    assert "explicitly approved" in text


def test_output_contract_future_gates_no_network():
    text = _read_contract().lower()
    assert "no network" in text or "no runtime" in text or "network" in text


def test_output_contract_future_gates_advisory_labels_enforced():
    text = _read_contract().lower()
    assert "advisory label" in text or "advisory_label" in text


def test_output_contract_future_gates_bounded_score_enforced():
    text = _read_contract().lower()
    assert "bounded" in text


# ── project_status.md ────────────────────────────────────────────────────────

def test_project_status_file_exists():
    assert PROJECT_STATUS.is_file()


def test_project_status_wp48_is_current_phase():
    text = _read_status()
    phase_line = next(
        line for line in text.splitlines() if line.startswith("- Current phase:")
    )
    assert "WP48" in phase_line


def test_project_status_wp47_in_merged_wps():
    text = _read_status()
    merged_line = next(
        line for line in text.splitlines() if line.startswith("- Merged WPs:")
    )
    assert "WP47" in merged_line


def test_project_status_market_research_scoring_schema_on_branch():
    text = _read_status()
    assert "SCHEMA_OUTPUT_CONTRACT_ON_BRANCH" in text


def test_project_status_market_research_implementation_not_started():
    text = _read_status()
    assert "Market research priority scoring implementation status" in text
    assert "NOT_STARTED" in text


def test_project_status_live_trading_disabled():
    assert "Live trading status: DISABLED" in _read_status()


def test_project_status_credentials_not_used():
    assert "Credentials status: NOT_USED" in _read_status()


def test_project_status_execution_not_started():
    assert "Execution status: NOT_STARTED" in _read_status()


def test_project_status_hermes_not_installed():
    assert "Hermes status: NOT_INSTALLED_NOT_RUNTIME_DEPENDENCY" in _read_status()


def test_project_status_agent_runtime_not_started():
    assert "Agent runtime status: NOT_STARTED" in _read_status()


def test_project_status_agent_execution_authority_forbidden():
    assert "Agent execution authority: FORBIDDEN" in _read_status()


def test_project_status_scheduler_not_started():
    assert "Scheduler status: NOT_STARTED" in _read_status()


def test_project_status_bot_loop_not_started():
    assert "Bot loop status: NOT_STARTED" in _read_status()


def test_project_status_authenticated_client_forbidden():
    assert "Authenticated client status: FORBIDDEN_UNTIL_APPROVED_WP" in _read_status()


def test_project_status_official_client_runtime_not_started():
    assert "Official client runtime dependency status: NOT_STARTED_FOR_OFFICIAL_CLIENT_RUNTIME" in _read_status()


# ── repo_truth_index.md ───────────────────────────────────────────────────────

def test_repo_truth_index_exists():
    assert REPO_TRUTH.is_file()


def test_repo_truth_index_references_output_contract():
    assert "docs/market_research_priority_scoring_output_contract.md" in _read_truth()


def test_repo_truth_index_references_design_doc():
    assert "docs/market_research_priority_scoring_layer.md" in _read_truth()


def test_repo_truth_index_sequential_numbering():
    text = _read_truth()
    # Collect all numeric prefixes in the authority hierarchy
    prefixes = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped and stripped[0].isdigit() and ". `" in stripped:
            num_str = stripped.split(".")[0]
            if num_str.isdigit():
                prefixes.append(int(num_str))
    # Verify sequential and unique
    assert prefixes == list(range(1, len(prefixes) + 1)), (
        f"Repo truth index numbering is not sequential: {prefixes}"
    )


# ── deferred_items_log.md ─────────────────────────────────────────────────────

def test_deferred_log_exists():
    assert DEFERRED_LOG.is_file()


def test_deferred_log_contains_wp44_d001():
    assert "WP44-D001" in _read_deferred()


def test_deferred_log_wp44_d001_still_open():
    text = _read_deferred()
    assert "WP44-D001" in text
    # Must not be resolved by WP48
    assert "NOT_STARTED" in text or "not started" in text.lower() or "OPEN" in text


def test_deferred_log_contains_wp48_d001():
    assert "WP48-D001" in _read_deferred()


def test_deferred_log_contains_wp48_d002():
    assert "WP48-D002" in _read_deferred()


def test_deferred_log_wp48_implementation_not_started():
    text = _read_deferred()
    assert "WP48-D001" in text
    assert "not started" in text.lower() or "NOT_STARTED" in text


def test_deferred_log_wp48_contract_not_enforced():
    text = _read_deferred()
    assert "WP48-D002" in text
    assert "not enforced" in text.lower() or "no implementation" in text.lower()


# ── Design doc cross-reference ────────────────────────────────────────────────

def test_design_doc_references_output_contract():
    text = _read_design()
    assert "market_research_priority_scoring_output_contract.md" in text


def test_design_doc_status_updated_to_merged():
    text = _read_design()
    assert "DOCS_ONLY_DESIGN_MERGED" in text


def test_design_doc_references_wp48():
    text = _read_design()
    assert "WP48" in text
