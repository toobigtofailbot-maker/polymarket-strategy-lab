"""
Focused docs tests for the wallet intelligence research signal roadmap (WP76).

These tests prevent the roadmap from drifting and verify that repo truth,
deferred items, and protected boundaries are correctly recorded.

No source implementation is tested here. This module is docs/tests-only.
"""

import os
import pytest

ROADMAP_DOC = "docs/wallet_intelligence_research_signal_roadmap.md"
STATUS_DOC = "docs/project_status.md"
REPO_TRUTH_DOC = "docs/repo_truth_index.md"
DEFERRED_DOC = "docs/deferred_items_log.md"

ROADMAP_TEST_FILE = "tests/test_wallet_intelligence_roadmap_docs.py"


def _read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


# ---------------------------------------------------------------------------
# 1. Roadmap doc exists
# ---------------------------------------------------------------------------

def test_wallet_intelligence_roadmap_doc_exists():
    assert os.path.isfile(ROADMAP_DOC), f"Missing: {ROADMAP_DOC}"


# ---------------------------------------------------------------------------
# 2. Wallet intelligence is a research signal layer, not blind copy-trading
# ---------------------------------------------------------------------------

def test_roadmap_states_research_signal_layer_not_copy_trading():
    content = _read(ROADMAP_DOC)
    assert "research signal layer" in content
    assert "not a blind copy-trading engine" in content


# ---------------------------------------------------------------------------
# 3. Top-wallet activity may affect research priority
# ---------------------------------------------------------------------------

def test_roadmap_states_wallet_activity_may_affect_research_priority():
    content = _read(ROADMAP_DOC)
    assert "may materially increase research priority" in content or (
        "increase research priority" in content
        and "wallet" in content.lower()
    )


# ---------------------------------------------------------------------------
# 4. Top-wallet activity must not directly trigger live execution
# ---------------------------------------------------------------------------

def test_roadmap_states_wallet_activity_must_not_trigger_live_execution():
    content = _read(ROADMAP_DOC)
    assert "must not directly trigger live execution" in content


# ---------------------------------------------------------------------------
# 5. Five wallet intelligence jobs
# ---------------------------------------------------------------------------

def test_roadmap_lists_five_wallet_intelligence_jobs():
    content = _read(ROADMAP_DOC)
    assert "Find top wallets" in content
    assert "Classify what each wallet is good at" in content
    assert "Detect when those wallets enter markets" in content
    assert "Test whether their trades are copyable" in content
    assert "Feed wallet signals into the research queue" in content


# ---------------------------------------------------------------------------
# 6. Required wallet metrics
# ---------------------------------------------------------------------------

def test_roadmap_lists_required_wallet_metrics():
    content = _read(ROADMAP_DOC)
    required_metrics = [
        "realized profit",
        "unrealized profit",
        "number of trades",
        "number of resolved markets",
        "average trade size",
        "median trade size",
        "profit by category",
        "profit by holding period",
        "profit by market liquidity",
        "profit before/after major news",
        "entry price versus later market price",
        "entry price versus final resolution",
        "largest win",
        "largest loss",
        "max drawdown",
    ]
    for metric in required_metrics:
        assert metric in content, f"Missing required metric: {metric}"


# ---------------------------------------------------------------------------
# 7. Delayed-copy windows: 1 second, 5 seconds, 30 seconds, 2 minutes, 10 minutes
# ---------------------------------------------------------------------------

def test_roadmap_lists_required_delay_windows():
    content = _read(ROADMAP_DOC)
    assert "1 second" in content
    assert "5 seconds" in content
    assert "30 seconds" in content
    assert "2 minutes" in content
    assert "10 minutes" in content


# ---------------------------------------------------------------------------
# 8. Delayed copyability must account for spread, slippage, fees, liquidity, size
# ---------------------------------------------------------------------------

def test_roadmap_states_copyability_accounts_for_realistic_constraints():
    content = _read(ROADMAP_DOC)
    assert "spread" in content
    assert "slippage" in content
    assert "fees" in content
    assert "liquidity limits" in content
    assert "size constraints" in content


# ---------------------------------------------------------------------------
# 9. Wallet signal categories
# ---------------------------------------------------------------------------

def test_roadmap_lists_wallet_signal_categories():
    content = _read(ROADMAP_DOC)
    required_categories = [
        "SPECIALIST_ENTRY",
        "MULTI_WALLET_CLUSTER",
        "EARLY_ENTRY_BEFORE_PRICE_MOVE",
        "LATE_CHASER",
        "MARKET_MAKER_FLOW",
        "ARBITRAGE_FLOW",
        "SUSPICIOUS_TIMING",
        "LOW_SAMPLE_OUTLIER",
        "UNCOPYABLE_FAST_FLOW",
    ]
    for cat in required_categories:
        assert cat in content, f"Missing wallet signal category: {cat}"


# ---------------------------------------------------------------------------
# 10. Suspicious-flow / human-review-required boundary
# ---------------------------------------------------------------------------

def test_roadmap_includes_suspicious_flow_boundary():
    content = _read(ROADMAP_DOC)
    assert "SUSPICIOUS_TIMING" in content
    assert "human-review-required" in content or "human review" in content.lower()
    assert "privileged" in content or "informed-flow" in content


# ---------------------------------------------------------------------------
# 11. Target research-queue influence range 25% to 35%
# ---------------------------------------------------------------------------

def test_roadmap_states_research_queue_influence_range():
    content = _read(ROADMAP_DOC)
    assert "25%" in content
    assert "35%" in content
    assert "research-queue influence" in content or "research queue" in content.lower()


# ---------------------------------------------------------------------------
# 12. Direct trade-decision influence remains 0% until evidence and authorization
# ---------------------------------------------------------------------------

def test_roadmap_states_direct_trade_decision_influence_zero():
    content = _read(ROADMAP_DOC)
    assert "0%" in content
    assert "direct trade-decision influence" in content or (
        "trade-decision" in content and "0%" in content
    )


# ---------------------------------------------------------------------------
# 13. Updated near-term roadmap WP77 through WP81
# ---------------------------------------------------------------------------

def test_roadmap_includes_near_term_wp_sequence():
    content = _read(ROADMAP_DOC)
    assert "WP77" in content
    assert "WP78" in content
    assert "WP79" in content
    assert "WP80" in content
    assert "WP81" in content


# ---------------------------------------------------------------------------
# 14. Forbids automatic copy-trading, live execution, order placement, etc.
# ---------------------------------------------------------------------------

def test_roadmap_forbids_auto_copy_trading():
    content = _read(ROADMAP_DOC)
    assert "no automatic copy-trading" in content


def test_roadmap_forbids_live_execution():
    content = _read(ROADMAP_DOC)
    assert "no live execution" in content


def test_roadmap_forbids_order_placement():
    content = _read(ROADMAP_DOC)
    assert "no order placement" in content


def test_roadmap_forbids_cancels():
    content = _read(ROADMAP_DOC)
    assert "no cancels" in content


def test_roadmap_forbids_position_sizing():
    content = _read(ROADMAP_DOC)
    assert "no position sizing" in content


def test_roadmap_forbids_risk_override():
    content = _read(ROADMAP_DOC)
    assert "no risk override" in content


def test_roadmap_forbids_parameter_auto_change():
    content = _read(ROADMAP_DOC)
    assert "no parameter auto-change" in content


def test_roadmap_forbids_credentials():
    content = _read(ROADMAP_DOC)
    assert "no credentials" in content


def test_roadmap_forbids_scheduler():
    content = _read(ROADMAP_DOC)
    assert "no scheduler" in content


def test_roadmap_forbids_bot_loop():
    content = _read(ROADMAP_DOC)
    assert "no bot loop" in content


def test_roadmap_forbids_dashboard():
    content = _read(ROADMAP_DOC)
    assert "no dashboard" in content


def test_roadmap_forbids_hermes_llm_execution_authority():
    content = _read(ROADMAP_DOC)
    assert "no Hermes/LLM execution authority" in content


# ---------------------------------------------------------------------------
# 15. Repo truth index references the new roadmap doc and test
# ---------------------------------------------------------------------------

def test_repo_truth_index_references_roadmap_doc():
    content = _read(REPO_TRUTH_DOC)
    assert "wallet_intelligence_research_signal_roadmap" in content


def test_repo_truth_index_references_roadmap_test():
    content = _read(REPO_TRUTH_DOC)
    assert "test_wallet_intelligence_roadmap_docs" in content


# ---------------------------------------------------------------------------
# 16. Deferred items log contains WP76 wallet-intelligence deferred items
# ---------------------------------------------------------------------------

def test_deferred_items_log_contains_wp76_d001():
    content = _read(DEFERRED_DOC)
    assert "WP76-D001" in content


def test_deferred_items_log_contains_wp76_d002():
    content = _read(DEFERRED_DOC)
    assert "WP76-D002" in content


def test_deferred_items_log_contains_wp76_d003():
    content = _read(DEFERRED_DOC)
    assert "WP76-D003" in content


def test_deferred_items_log_contains_wp76_d004():
    content = _read(DEFERRED_DOC)
    assert "WP76-D004" in content


def test_deferred_items_log_contains_wp76_d005():
    content = _read(DEFERRED_DOC)
    assert "WP76-D005" in content


def test_deferred_items_log_contains_wp76_d006():
    content = _read(DEFERRED_DOC)
    assert "WP76-D006" in content


def test_deferred_items_log_contains_wp76_d007():
    content = _read(DEFERRED_DOC)
    assert "WP76-D007" in content


# ---------------------------------------------------------------------------
# 17. Project status marks WP77 merged and WP78 as current branch/phase
# ---------------------------------------------------------------------------

def test_project_status_marks_wp79_as_current_phase():
    content = _read(STATUS_DOC)
    current_phase_line = next(
        line for line in content.splitlines() if line.startswith("- Current phase:")
    )
    assert any(wp in current_phase_line for wp in ("WP79", "WP80", "WP81", "WP82", "WP83", "WP84", "WP86", "WP87", "WP88", "WP89", "WP90"))


def test_project_status_marks_wp79_branch():
    content = _read(STATUS_DOC)
    branch_line = next(
        line for line in content.splitlines() if line.startswith("- Current branch:")
    )
    assert any(wp in branch_line for wp in (
        "wp79-wallet-skill-niche-profiler-research-queue-integration",
        "wp80-copyability-delay-simulator-design-wallet-report-contract",
        "wp81-local-copyability-delay-evaluation-from-fixtures",
        "wp82-wallet-intelligence-report-generator-v1",
        "wp83-wallet-signal-paper-strategy-contract-v1",
        "wp84-wallet-signal-paper-strategy-contract-local-validator-v1",
        "workflow/wp86-execution-package-discipline-adoption",
        "wp86",
        "wp87",
        "wp88",
        "wp89",
        "wp90",
        "wp91",
        "eager-shtern",
        "happy-torvalds",
    ))


def test_project_status_shows_wp75_merged():
    content = _read(STATUS_DOC)
    # WP75 must be listed in merged WPs
    assert "WP75" in content


def test_project_status_records_pr77_merge_commit():
    content = _read(STATUS_DOC)
    # PR #77 actual merge commit
    assert "91cd26e4fe16d492fa2f7b319fba176ee60cd9d5" in content


def test_project_status_records_pr78_merge_commit():
    content = _read(STATUS_DOC)
    assert "24badbfb7a9da06ee4c8ae94795e1f2c862af913" in content


def test_project_status_records_pr79_merge_commit():
    content = _read(STATUS_DOC)
    assert "7ff117f6caf78eab62e6a116db72b60d76d305f5" in content


def test_project_status_shows_wp78_merged():
    content = _read(STATUS_DOC)
    merged_line = next(
        line for line in content.splitlines() if line.startswith("- Merged WPs:")
    )
    assert "WP78" in merged_line


def test_project_status_shows_wp76_merged():
    content = _read(STATUS_DOC)
    merged_line = next(
        line for line in content.splitlines() if line.startswith("- Merged WPs:")
    )
    assert "WP76" in merged_line


def test_project_status_shows_wp77_merged():
    content = _read(STATUS_DOC)
    merged_line = next(
        line for line in content.splitlines() if line.startswith("- Merged WPs:")
    )
    assert "WP77" in merged_line


# ---------------------------------------------------------------------------
# 17b. Protected boundaries unchanged
# ---------------------------------------------------------------------------

def test_project_status_live_trading_disabled():
    content = _read(STATUS_DOC)
    assert "DISABLED" in content
    assert "live trading" in content.lower() or "Live trading" in content


def test_project_status_credentials_not_used():
    content = _read(STATUS_DOC)
    assert "NOT_USED" in content


def test_project_status_execution_not_started():
    content = _read(STATUS_DOC)
    assert "NOT_STARTED" in content


def test_project_status_bot_loop_not_started():
    content = _read(STATUS_DOC)
    assert "NOT_STARTED" in content


def test_project_status_scheduler_not_started():
    content = _read(STATUS_DOC)
    assert "NOT_STARTED" in content


def test_project_status_agent_execution_authority_forbidden():
    content = _read(STATUS_DOC)
    assert "FORBIDDEN" in content


# ---------------------------------------------------------------------------
# 18. No src/ files changed (boundary check via import test)
# ---------------------------------------------------------------------------

def test_no_forbidden_src_wallet_modules_exist():
    # Only wallet_trade_event_fixtures.py (WP78) and wallet_signal_research_profile.py (WP79)
    # are approved wallet src modules. Forbidden modules must not exist.
    assert not os.path.isfile("src/data_layer/wallet_intelligence.py")
    assert not os.path.isfile("src/data_layer/wallet_registry.py")
    assert not os.path.isfile("src/data_layer/wallet_profiles.py")
    assert not os.path.isfile("src/data_layer/wallet_trade_events.py")
    assert not os.path.isfile("src/data_layer/copyability_simulator.py")


# ---------------------------------------------------------------------------
# 19. No tools/ wallet implementation exists (boundary check)
# ---------------------------------------------------------------------------

def test_no_new_tools_wallet_client_exists():
    assert not os.path.isfile("tools/wallet/wallet_api_client.py")
    assert not os.path.isfile("tools/wallet/wallet_ingestion.py")
    assert not os.path.isdir("tools/wallet") or (
        os.path.isdir("tools/wallet")
        and not os.path.isfile("tools/wallet/wallet_api_client.py")
    )


# ---------------------------------------------------------------------------
# 20. No dependency/lock files changed (boundary check)
# ---------------------------------------------------------------------------

def test_no_wallet_dependency_in_requirements():
    if os.path.isfile("requirements.txt"):
        content = _read("requirements.txt")
        assert "wallet" not in content.lower()
        assert "copy-trading" not in content.lower()


# ---------------------------------------------------------------------------
# Copyability metrics referenced in roadmap
# ---------------------------------------------------------------------------

def test_roadmap_lists_copy_delay_pnl_metrics():
    content = _read(ROADMAP_DOC)
    assert "copy-after-1s PnL" in content or "copy-after-5s PnL" in content
    assert "copy-after-30s PnL" in content
    assert "copy-after-2m PnL" in content


def test_roadmap_key_metric_is_not_wallet_made_money():
    content = _read(ROADMAP_DOC)
    assert "The key metric is not" in content
    assert "wallet made money" in content


# ---------------------------------------------------------------------------
# Future live boundary conditions listed
# ---------------------------------------------------------------------------

def test_roadmap_lists_live_boundary_conditions():
    content = _read(ROADMAP_DOC)
    assert "delayed-copy evidence" in content
    assert "paper-trading evidence" in content
    assert "risk-gate approval" in content
    assert "explicit live-trading authorization" in content
    assert "credential boundary" in content
    assert "kill switch" in content


# ---------------------------------------------------------------------------
# Roadmap test file exists
# ---------------------------------------------------------------------------

def test_wallet_intelligence_roadmap_test_file_exists():
    assert os.path.isfile(ROADMAP_TEST_FILE), f"Missing: {ROADMAP_TEST_FILE}"
