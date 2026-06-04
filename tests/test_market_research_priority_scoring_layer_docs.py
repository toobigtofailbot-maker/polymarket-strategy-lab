"""Focused docs tests for WP44 Market Research Priority Scoring Layer design.

Tests only docs. Does not import source implementation modules.
No scoring implementation exists in WP44.
"""

from __future__ import annotations

import pathlib


REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
DESIGN_DOC = REPO_ROOT / "docs" / "market_research_priority_scoring_layer.md"
PROJECT_STATUS = REPO_ROOT / "docs" / "project_status.md"
REPO_TRUTH = REPO_ROOT / "docs" / "repo_truth_index.md"
DEFERRED_LOG = REPO_ROOT / "docs" / "deferred_items_log.md"


def _read_design() -> str:
    return DESIGN_DOC.read_text(encoding="utf-8")


def _read_status() -> str:
    return PROJECT_STATUS.read_text(encoding="utf-8")


def _read_truth() -> str:
    return REPO_TRUTH.read_text(encoding="utf-8")


def _read_deferred() -> str:
    return DEFERRED_LOG.read_text(encoding="utf-8")


# ── Design document existence ─────────────────────────────────────────────────

def test_design_doc_exists():
    assert DESIGN_DOC.is_file()


# ── Required safety phrases in design doc ─────────────────────────────────────

def test_design_contains_research_priority_score():
    assert "research_priority_score" in _read_design()


def test_design_contains_advisory_only_label():
    text = _read_design()
    assert "ADVISORY_ONLY_HUMAN_REVIEW_REQUIRED" in text


def test_design_states_not_a_trading_signal():
    assert "not a trading signal" in _read_design()


def test_design_states_not_expected_return():
    assert "not expected return" in _read_design()


def test_design_states_not_position_sizing():
    assert "not position sizing" in _read_design()


def test_design_defines_score_laundering():
    assert "score laundering" in _read_design().lower()


def test_design_not_investment_advice():
    text = _read_design()
    assert "not investment advice" in text


# ── Forbidden output terminology ──────────────────────────────────────────────

def test_design_forbids_trade_score_as_output():
    text = _read_design()
    assert "trade_score" in text
    assert "Forbidden" in text or "forbidden" in text


def test_design_forbids_alpha_score_as_output():
    text = _read_design()
    assert "alpha_score" in text
    assert "Forbidden" in text or "forbidden" in text


def test_design_forbids_opportunity_score_as_output():
    text = _read_design()
    assert "opportunity_score" in text
    assert "Forbidden" in text or "forbidden" in text


def test_design_forbids_expected_return_as_output():
    text = _read_design()
    assert "expected_return" in text
    assert "Forbidden" in text or "forbidden" in text


def test_design_forbids_position_sizing_as_output():
    text = _read_design()
    assert "position sizing" in text.lower()
    assert "Forbidden" in text or "forbidden" in text


def test_design_forbids_leverage_as_output():
    text = _read_design()
    assert "leverage" in text.lower()
    assert "Forbidden" in text or "forbidden" in text


def test_design_forbids_entry_exit_as_output():
    text = _read_design()
    assert "entry" in text.lower()
    assert "exit" in text.lower()
    assert "Forbidden" in text or "forbidden" in text


def test_design_forbids_execution_language():
    text = _read_design()
    assert "execution" in text.lower()
    assert "Forbidden" in text or "forbidden" in text


# ── Score laundering mitigations ─────────────────────────────────────────────

def test_design_requires_staleness_flag():
    assert "staleness_flag" in _read_design()


def test_design_requires_provenance_flag():
    assert "provenance" in _read_design().lower()


def test_design_requires_missing_data_penalty():
    assert "missing-data penalt" in _read_design().lower()


def test_design_requires_cap_on_orderbook_features():
    text = _read_design().lower()
    assert "capped" in text or "cap or separate" in text


def test_design_requires_missing_data_warning():
    assert "missing_data_warning" in _read_design()


# ── Status is design-only ─────────────────────────────────────────────────────

def test_design_status_is_docs_only():
    # WP48 updates status from ON_BRANCH to MERGED; SCHEMA_OUTPUT_CONTRACT_ON_BRANCH
    text = _read_design()
    assert "DOCS_ONLY_DESIGN_MERGED" in text or "DOCS_ONLY_DESIGN_ON_BRANCH" in text


def test_design_no_src_change():
    assert "NO_SRC_CHANGE" in _read_design()


def test_design_no_runtime_change():
    assert "NO_RUNTIME_CHANGE" in _read_design()


def test_design_no_trading_execution():
    assert "NO_TRADING_EXECUTION" in _read_design()


def test_design_no_hermes():
    assert "NO_HERMES_INSTALL_OR_RUNTIME" in _read_design()


def test_design_implementation_not_started():
    assert "NOT_STARTED" in _read_design()


# ── project_status.md assertions ──────────────────────────────────────────────

def test_project_status_file_exists():
    assert PROJECT_STATUS.is_file()


def test_project_status_wp44_in_merged_wps():
    # WP44 is merged; verify it appears in merged WPs list
    text = _read_status()
    merged_line = next(
        line for line in text.splitlines() if line.startswith("- Merged WPs:")
    )
    assert "WP44" in merged_line


def test_project_status_wp43_in_merged_wps():
    text = _read_status()
    merged_line = next(
        line for line in text.splitlines() if line.startswith("- Merged WPs:")
    )
    assert "WP43" in merged_line


def test_project_status_wp44_branch_not_current():
    # WP44 branch should no longer be the current branch after merge
    text = _read_status()
    branch_line = next(
        line for line in text.splitlines() if line.startswith("- Current branch:")
    )
    assert "wp44-market-research-priority-scoring-layer-design" not in branch_line


def test_project_status_market_research_priority_scoring_status():
    text = _read_status()
    assert "Market research priority scoring layer status" in text
    assert "DOCS_ONLY_DESIGN_MERGED" in text


# ── Protected boundary preservation in project_status.md ─────────────────────

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


# ── repo_truth_index.md assertions ───────────────────────────────────────────

def test_repo_truth_index_exists():
    assert REPO_TRUTH.is_file()


def test_repo_truth_references_design_doc():
    assert "docs/market_research_priority_scoring_layer.md" in _read_truth()


# ── deferred_items_log.md assertions ─────────────────────────────────────────

def test_deferred_log_exists():
    assert DEFERRED_LOG.is_file()


def test_deferred_log_contains_wp44_d001():
    assert "WP44-D001" in _read_deferred()


def test_deferred_log_wp44_d001_implementation_not_started():
    text = _read_deferred()
    assert "WP44-D001" in text
    assert "not started" in text.lower() or "NOT_STARTED" in text
