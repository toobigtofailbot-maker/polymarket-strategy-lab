"""Focused docs tests for WP50 Research Data Foundation Direction Lock-In.

Tests only docs. Does not import source implementation modules.
No feature extraction, CLI/export/report, or scoring implementation is added in WP50.
"""

from __future__ import annotations

import pathlib


REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
DIRECTION_DOC = REPO_ROOT / "docs" / "research_data_foundation_direction.md"
PROJECT_STATUS = REPO_ROOT / "docs" / "project_status.md"
REPO_TRUTH = REPO_ROOT / "docs" / "repo_truth_index.md"
DEFERRED_LOG = REPO_ROOT / "docs" / "deferred_items_log.md"


def _read_direction() -> str:
    return DIRECTION_DOC.read_text(encoding="utf-8")


def _read_status() -> str:
    return PROJECT_STATUS.read_text(encoding="utf-8")


def _read_truth() -> str:
    return REPO_TRUTH.read_text(encoding="utf-8")


def _read_deferred() -> str:
    return DEFERRED_LOG.read_text(encoding="utf-8")


# ── Direction doc existence ───────────────────────────────────────────────────

def test_direction_doc_exists():
    assert DIRECTION_DOC.is_file()


# ── WP50 and docs-only status ─────────────────────────────────────────────────

def test_direction_doc_states_wp50():
    assert "WP50" in _read_direction()


def test_direction_doc_states_docs_only():
    text = _read_direction()
    assert "DOCS_ONLY_DIRECTION_LOCK_ON_BRANCH" in text or "NO_SOURCE_CHANGE" in text


def test_direction_doc_states_no_source_change():
    assert "NO_SOURCE_CHANGE" in _read_direction()


def test_direction_doc_states_no_runtime_change():
    assert "NO_RUNTIME_CHANGE" in _read_direction()


def test_direction_doc_states_no_feature_extraction_in_wp50():
    assert "NO_FEATURE_EXTRACTION_IMPLEMENTATION_IN_WP50" in _read_direction()


# ── WP49 merge commit ─────────────────────────────────────────────────────────

def test_direction_doc_states_wp49_merge_commit():
    assert "3ee02a7c31a1d4f5d599fdb1d5ffa83d6fca1d6d" in _read_direction()


# ── Feature extraction and CLI/export/report not started ──────────────────────

def test_direction_doc_says_feature_extraction_not_started():
    text = _read_direction()
    assert "feature extraction" in text.lower()
    assert "not started" in text.lower()


def test_direction_doc_says_cli_export_report_not_started():
    text = _read_direction()
    assert "CLI/export/report writer is not started" in text or (
        "CLI" in text and "not started" in text.lower()
    )


# ── Local/offline/read-only research-data foundation direction ────────────────

def test_direction_doc_says_local_offline_foundation():
    text = _read_direction()
    assert "local/offline/read-only research-data foundations" in text


def test_direction_doc_says_next_phase_not_strategy():
    text = _read_direction()
    assert "strategy" in text.lower()
    assert "paper trading" in text.lower()
    assert "live trading" in text.lower()
    assert "execution" in text.lower()
    # Must say these are NOT the next phase
    assert "not" in text.lower()


# ── Non-signal semantics ──────────────────────────────────────────────────────

def test_direction_doc_says_market_research_priority_scoring_non_signal():
    text = _read_direction()
    assert "non-signal" in text.lower() or "not a trade signal" in text.lower() or (
        "research triage only" in text.lower() and "non-signal" in text.lower()
    )


def test_direction_doc_says_research_priority_score_triage_only():
    text = _read_direction()
    assert "research_priority_score" in text
    assert "human research triage only" in text


# ── Provenance and staleness ──────────────────────────────────────────────────

def test_direction_doc_says_provenance_staleness_are_data_integrity_gates():
    text = _read_direction()
    assert "Provenance and staleness are data-integrity gates" in text or (
        "provenance" in text.lower() and "staleness" in text.lower()
        and "data-integrity" in text.lower()
    )


# ── Critical missing data must cap or invalidate ─────────────────────────────

def test_direction_doc_says_missing_data_caps_outputs():
    text = _read_direction()
    assert "critical missing data must cap or invalidate" in text.lower() or (
        "cap or invalidate" in text.lower() and "missing" in text.lower()
    )


# ── Resolution-rule ambiguity not proven alpha ────────────────────────────────

def test_direction_doc_says_resolution_rule_ambiguity_not_proven_alpha():
    text = _read_direction()
    assert "resolution-rule ambiguity" in text.lower()
    assert "not proven alpha" in text.lower()


# ── Microstructure quality not tradability ────────────────────────────────────

def test_direction_doc_says_microstructure_quality_not_tradability():
    text = _read_direction()
    assert "microstructure quality" in text.lower()
    assert "not tradability" in text.lower()


# ── Cross-market graphing metadata-only ──────────────────────────────────────

def test_direction_doc_says_cross_market_graphing_metadata_only():
    text = _read_direction()
    assert "metadata-only" in text.lower()
    assert "cross-market" in text.lower() or "cross market" in text.lower()


# ── Calibration waits for resolved-outcome data ───────────────────────────────

def test_direction_doc_says_calibration_waits_for_resolved_outcome_data():
    text = _read_direction()
    assert "calibration" in text.lower()
    assert "resolved-outcome data" in text.lower()


# ── Wallet attention aggregate/anonymized/research-only ──────────────────────

def test_direction_doc_says_wallet_attention_aggregate_research_only():
    text = _read_direction()
    assert "wallet attention" in text.lower()
    # must require public data plan, aggregation/anonymization, copy-trading prevention
    assert "aggregation" in text.lower() or "anonymization" in text.lower()
    assert "copy-trading" in text.lower()


# ── Official-source latency deferred until release timestamp data ─────────────

def test_direction_doc_says_official_source_latency_deferred():
    text = _read_direction()
    assert "official-source latency" in text.lower()
    assert "release timestamp" in text.lower()


# ── Blocked directions ────────────────────────────────────────────────────────

def test_direction_doc_blocks_live_trading():
    assert "live trading" in _read_direction().lower()


def test_direction_doc_blocks_credentials():
    assert "credentials" in _read_direction().lower()


def test_direction_doc_blocks_authenticated_clients():
    text = _read_direction().lower()
    assert "authenticated client" in text


def test_direction_doc_blocks_execution():
    assert "execution gateway" in _read_direction().lower()


def test_direction_doc_blocks_strategy_runtime():
    assert "strategy runtime" in _read_direction().lower()


def test_direction_doc_blocks_paper_trading():
    assert "paper-trading runtime" in _read_direction().lower()


def test_direction_doc_blocks_scheduler_bot_loop():
    text = _read_direction().lower()
    assert "scheduler" in text
    assert "bot loop" in text


def test_direction_doc_blocks_hermes_agent_runtime():
    text = _read_direction().lower()
    assert "hermes" in text
    assert "agent runtime" in text


def test_direction_doc_blocks_autonomous_trading():
    assert "autonomous trading agent" in _read_direction().lower()


def test_direction_doc_blocks_wallet_copy_trading():
    assert "wallet copy-trading" in _read_direction().lower()


def test_direction_doc_blocks_individual_wallet_ranking():
    assert "individual wallet ranking" in _read_direction().lower()


def test_direction_doc_blocks_expected_return_outputs():
    assert "expected-return outputs" in _read_direction().lower()


def test_direction_doc_blocks_position_sizing():
    assert "position sizing" in _read_direction().lower()


def test_direction_doc_blocks_trade_signals():
    text = _read_direction().lower()
    assert "trade signal" in text or "trade-like fields" in text


# ── project_status.md assertions ─────────────────────────────────────────────

def test_project_status_file_exists():
    assert PROJECT_STATUS.is_file()


def test_project_status_wp50_in_merged_wps():
    text = _read_status()
    merged_line = next(
        (l for l in text.splitlines() if l.startswith("- Merged WPs:")),
        None,
    )
    assert merged_line is not None
    assert "WP50" in merged_line


def test_project_status_wp51_current_phase():
    # WP51 merged and is listed in Merged WPs; WP53 is the current phase.
    text = _read_status()
    merged_line = next(
        (l for l in text.splitlines() if l.startswith("- Merged WPs:")),
        None,
    )
    assert merged_line is not None
    assert "WP51" in merged_line


def test_project_status_wp49_in_merged_wps():
    text = _read_status()
    merged_line = next(
        (l for l in text.splitlines() if l.startswith("- Merged WPs:")),
        None,
    )
    assert merged_line is not None
    assert "WP49" in merged_line


def test_project_status_core_scorer_merged():
    text = _read_status()
    assert "CORE_SCORER_MERGED" in text


def test_project_status_research_data_foundation_direction_merged():
    text = _read_status()
    assert "RESEARCH_DATA_FOUNDATION_DIRECTION_MERGED" in text


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


# ── repo_truth_index.md assertions ───────────────────────────────────────────

def test_repo_truth_index_exists():
    assert REPO_TRUTH.is_file()


def test_repo_truth_references_direction_doc():
    assert "docs/research_data_foundation_direction.md" in _read_truth()


def test_repo_truth_direction_doc_describes_final_research_phase_direction():
    text = _read_truth()
    idx = text.find("docs/research_data_foundation_direction.md")
    assert idx != -1
    entry = text[idx:idx + 400]
    assert "direction" in entry.lower()
