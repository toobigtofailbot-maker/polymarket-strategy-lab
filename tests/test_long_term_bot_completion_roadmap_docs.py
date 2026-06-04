"""
Focused docs test for docs/long_term_bot_completion_roadmap.md and related
repo-truth updates in WP52.
"""
import os
import pathlib

REPO_ROOT = pathlib.Path(__file__).parent.parent
ROADMAP_DOC = REPO_ROOT / "docs" / "long_term_bot_completion_roadmap.md"
PROJECT_STATUS = REPO_ROOT / "docs" / "project_status.md"
REPO_TRUTH_INDEX = REPO_ROOT / "docs" / "repo_truth_index.md"
RESEARCH_DIRECTION = REPO_ROOT / "docs" / "research_data_foundation_direction.md"


def _read(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Roadmap doc existence
# ---------------------------------------------------------------------------

def test_roadmap_doc_exists():
    assert ROADMAP_DOC.exists(), f"Missing: {ROADMAP_DOC}"


# ---------------------------------------------------------------------------
# WP52 identity
# ---------------------------------------------------------------------------

def test_roadmap_doc_states_wp52():
    content = _read(ROADMAP_DOC)
    assert "WP52" in content


def test_roadmap_doc_states_docs_only():
    content = _read(ROADMAP_DOC)
    assert "DOCS_ONLY_ROADMAP_ON_BRANCH" in content or "docs/tests-only" in content or "PLANNING_GUIDANCE_ONLY" in content


def test_roadmap_doc_states_planning_guidance_only():
    content = _read(ROADMAP_DOC)
    assert "PLANNING_GUIDANCE_ONLY" in content
    assert "planning guidance only" in content.lower()


def test_roadmap_doc_states_not_authorization():
    content = _read(ROADMAP_DOC)
    assert "NOT_AUTHORIZATION" in content
    assert "not approve" in content.lower() or "does not approve" in content.lower()


# ---------------------------------------------------------------------------
# WP51 merge commit reference
# ---------------------------------------------------------------------------

def test_roadmap_doc_states_wp51_merge_commit():
    content = _read(ROADMAP_DOC)
    assert "c57b9c0adcc044f8bd9ed01a6368f2fafdbe222f" in content, (
        "Roadmap doc must reference WP51 merge commit c57b9c0adcc044f8bd9ed01a6368f2fafdbe222f"
    )


# ---------------------------------------------------------------------------
# Side 4.0 onboarding summary
# ---------------------------------------------------------------------------

def test_roadmap_doc_includes_side40_onboarding_summary():
    content = _read(ROADMAP_DOC)
    assert "Side 4.0" in content
    assert "onboarding" in content.lower()


def test_roadmap_doc_side40_references_project_status():
    content = _read(ROADMAP_DOC)
    assert "docs/project_status.md" in content


def test_roadmap_doc_side40_references_repo_truth_index():
    content = _read(ROADMAP_DOC)
    assert "docs/repo_truth_index.md" in content


def test_roadmap_doc_side40_read_repo_truth_first():
    content = _read(ROADMAP_DOC)
    assert "repo truth" in content.lower()


# ---------------------------------------------------------------------------
# Milestone labels and exact estimate ranges
# ---------------------------------------------------------------------------

def test_roadmap_doc_milestone_research_intelligence_bot():
    content = _read(ROADMAP_DOC)
    assert "Research Intelligence Bot" in content
    assert "15-25 WPs" in content


def test_roadmap_doc_milestone_paper_trading_bot():
    content = _read(ROADMAP_DOC)
    assert "Paper Trading Bot" in content
    assert "45-75 WPs" in content


def test_roadmap_doc_milestone_controlled_live_bot():
    content = _read(ROADMAP_DOC)
    assert "Controlled Live Bot" in content
    assert "75-110 WPs" in content


def test_roadmap_doc_milestone_robust_autonomous_bot():
    content = _read(ROADMAP_DOC)
    assert "Robust Autonomous-ish Bot" in content
    assert "100-160 WPs" in content


def test_roadmap_doc_full_serious_completion_range():
    content = _read(ROADMAP_DOC)
    assert "93-160 WPs" in content


# ---------------------------------------------------------------------------
# All ten phase names and WP ranges
# ---------------------------------------------------------------------------

def test_roadmap_doc_phase1_data_foundation():
    content = _read(ROADMAP_DOC)
    assert "Data Foundation" in content or "Data foundation" in content or "data foundation" in content.lower()
    assert "6-10 WPs" in content


def test_roadmap_doc_phase2_market_understanding():
    content = _read(ROADMAP_DOC)
    assert "Market Understanding" in content or "Market understanding" in content
    assert "10-16 WPs" in content


def test_roadmap_doc_phase3_microstructure_liquidity():
    content = _read(ROADMAP_DOC)
    assert "Microstructure" in content
    assert "8-14 WPs" in content


def test_roadmap_doc_phase4_scoring_output_reporting():
    content = _read(ROADMAP_DOC)
    assert "Scoring Output" in content or "Scoring output" in content or "scoring output" in content.lower()
    assert "7-12 WPs" in content


def test_roadmap_doc_phase5_calibration_validation():
    content = _read(ROADMAP_DOC)
    assert "Calibration" in content
    assert "8-15 WPs" in content


def test_roadmap_doc_phase6_research_strategy_layer():
    content = _read(ROADMAP_DOC)
    assert "Research Strategy Layer" in content or "Research strategy layer" in content or "strategy layer" in content.lower()
    assert "8-14 WPs" in content


def test_roadmap_doc_phase7_paper_trading():
    content = _read(ROADMAP_DOC)
    assert "Paper Trading" in content or "Paper trading" in content
    assert "12-20 WPs" in content


def test_roadmap_doc_phase8_risk_engine():
    content = _read(ROADMAP_DOC)
    assert "Risk Engine" in content or "Risk engine" in content
    assert "10-16 WPs" in content


def test_roadmap_doc_phase9_live_execution():
    content = _read(ROADMAP_DOC)
    assert "Live Execution" in content or "Live execution" in content
    assert "14-25 WPs" in content


def test_roadmap_doc_phase10_scheduler_bot_loop():
    content = _read(ROADMAP_DOC)
    assert "Scheduler" in content or "scheduler" in content.lower()
    assert "Bot Loop" in content or "bot loop" in content.lower() or "Bot loop" in content
    assert "10-18 WPs" in content


# ---------------------------------------------------------------------------
# Analogies
# ---------------------------------------------------------------------------

def test_roadmap_doc_analogy_give_the_bot_eyes():
    content = _read(ROADMAP_DOC)
    assert "give the bot eyes" in content.lower() or "Give the bot eyes" in content


def test_roadmap_doc_analogy_rules_of_the_game():
    content = _read(ROADMAP_DOC)
    assert "rules of the game" in content.lower()


def test_roadmap_doc_analogy_road_is_drivable():
    content = _read(ROADMAP_DOC)
    assert "road is drivable" in content.lower()


def test_roadmap_doc_analogy_dashboard_before_autopilot():
    content = _read(ROADMAP_DOC)
    assert "dashboard before autopilot" in content.lower() or "dashboard before" in content.lower()


def test_roadmap_doc_analogy_compass_points_north():
    content = _read(ROADMAP_DOC)
    assert "compass points north" in content.lower()


def test_roadmap_doc_analogy_think_but_not_act():
    content = _read(ROADMAP_DOC)
    assert "think, but not act" in content.lower() or "think but not act" in content.lower()


def test_roadmap_doc_analogy_flight_simulator():
    content = _read(ROADMAP_DOC)
    assert "flight simulator before flying" in content.lower() or "flight simulator" in content.lower()


def test_roadmap_doc_analogy_build_the_brakes():
    content = _read(ROADMAP_DOC)
    assert "build the brakes" in content.lower()


def test_roadmap_doc_analogy_steering_wheel():
    content = _read(ROADMAP_DOC)
    assert "steering wheel" in content.lower()


def test_roadmap_doc_analogy_run_without_falling_asleep():
    content = _read(ROADMAP_DOC)
    assert "run without falling asleep" in content.lower() or "falling asleep" in content.lower()


# ---------------------------------------------------------------------------
# What the roadmap does not approve
# ---------------------------------------------------------------------------

def test_roadmap_doc_does_not_approve_strategy():
    content = _read(ROADMAP_DOC)
    assert "strategy" in content.lower()
    assert "does not approve" in content.lower() or "not approved" in content.lower() or "NOT_AUTHORIZATION" in content


def test_roadmap_doc_does_not_approve_paper_trading():
    content = _read(ROADMAP_DOC)
    lower = content.lower()
    assert "paper trading" in lower
    assert "does not approve" in lower or "NOT_AUTHORIZATION" in content


def test_roadmap_doc_does_not_approve_live_trading():
    content = _read(ROADMAP_DOC)
    lower = content.lower()
    assert "live trading" in lower
    assert "does not approve" in lower or "NOT_AUTHORIZATION" in content


def test_roadmap_doc_does_not_approve_execution():
    content = _read(ROADMAP_DOC)
    assert "Execution" in content or "execution" in content.lower()
    assert "does not approve" in content.lower() or "NOT_AUTHORIZATION" in content


def test_roadmap_doc_does_not_approve_credentials():
    content = _read(ROADMAP_DOC)
    assert "credentials" in content.lower() or "Credentials" in content


def test_roadmap_doc_does_not_approve_authenticated_client():
    content = _read(ROADMAP_DOC)
    assert "authenticated client" in content.lower() or "Authenticated client" in content


def test_roadmap_doc_does_not_approve_scheduler():
    content = _read(ROADMAP_DOC)
    assert "scheduler" in content.lower() or "Scheduler" in content


def test_roadmap_doc_does_not_approve_bot_loop():
    content = _read(ROADMAP_DOC)
    assert "bot loop" in content.lower() or "Bot loop" in content


def test_roadmap_doc_does_not_approve_hermes_runtime():
    content = _read(ROADMAP_DOC)
    assert "Hermes" in content or "hermes" in content.lower()
    assert "NO_HERMES_RUNTIME" in content


def test_roadmap_doc_does_not_approve_wallet_copying():
    content = _read(ROADMAP_DOC)
    assert "wallet-copying" in content.lower() or "wallet copying" in content.lower()


def test_roadmap_doc_does_not_approve_autonomous_agent():
    content = _read(ROADMAP_DOC)
    assert "autonomous agent" in content.lower() or "Autonomous agent" in content


# ---------------------------------------------------------------------------
# project_status.md checks
# ---------------------------------------------------------------------------

def test_project_status_includes_wp52_current_phase():
    content = _read(PROJECT_STATUS)
    assert "WP52" in content
    assert "Long-Term Bot Roadmap" in content or "Long-term Bot Roadmap" in content or "long-term bot roadmap" in content.lower()


def test_project_status_includes_wp51_in_merged_wps():
    content = _read(PROJECT_STATUS)
    merged_line = [line for line in content.splitlines() if "Merged WPs:" in line]
    assert merged_line, "No 'Merged WPs:' line found in project_status.md"
    assert "WP51" in merged_line[0], f"WP51 not in merged WPs line: {merged_line[0]}"


def test_project_status_marks_feature_extraction_foundation_merged():
    content = _read(PROJECT_STATUS)
    assert "FEATURE_EXTRACTION_FOUNDATION_MERGED" in content


# ---------------------------------------------------------------------------
# repo_truth_index.md checks
# ---------------------------------------------------------------------------

def test_repo_truth_index_references_roadmap_doc():
    content = _read(REPO_TRUTH_INDEX)
    assert "long_term_bot_completion_roadmap.md" in content


def test_repo_truth_index_roadmap_entry_states_planning_guidance():
    content = _read(REPO_TRUTH_INDEX)
    assert "planning guidance" in content.lower() or "planning level" in content.lower()


def test_repo_truth_index_roadmap_entry_states_not_authorization():
    content = _read(REPO_TRUTH_INDEX)
    assert "not authorization" in content.lower() or "NOT_AUTHORIZATION" in content or "not authorize" in content.lower()


# ---------------------------------------------------------------------------
# research_data_foundation_direction.md checks
# ---------------------------------------------------------------------------

def test_research_direction_references_roadmap_doc():
    content = _read(RESEARCH_DIRECTION)
    assert "long_term_bot_completion_roadmap.md" in content


def test_research_direction_roadmap_does_not_approve_beyond_current_direction():
    content = _read(RESEARCH_DIRECTION)
    assert "does not approve implementation beyond" in content.lower() or (
        "does not approve" in content.lower() and "implementation" in content.lower()
    )


# ---------------------------------------------------------------------------
# Protected boundaries unchanged
# ---------------------------------------------------------------------------

def test_project_status_live_trading_disabled():
    content = _read(PROJECT_STATUS)
    assert "Live trading status: DISABLED" in content or "DISABLED" in content


def test_project_status_credentials_not_used():
    content = _read(PROJECT_STATUS)
    assert "Credentials status: NOT_USED" in content or "NOT_USED" in content


def test_project_status_execution_not_started():
    content = _read(PROJECT_STATUS)
    assert "Execution status: NOT_STARTED" in content or (
        "Execution" in content and "NOT_STARTED" in content
    )


def test_project_status_authenticated_client_forbidden():
    content = _read(PROJECT_STATUS)
    assert "FORBIDDEN_UNTIL_APPROVED_WP" in content


def test_project_status_hermes_not_installed():
    content = _read(PROJECT_STATUS)
    assert "NOT_INSTALLED_NOT_RUNTIME_DEPENDENCY" in content


def test_project_status_agent_runtime_not_started():
    content = _read(PROJECT_STATUS)
    assert "Agent runtime status: NOT_STARTED" in content or (
        "agent runtime" in content.lower() and "NOT_STARTED" in content
    )


def test_project_status_agent_execution_authority_forbidden():
    content = _read(PROJECT_STATUS)
    assert "Agent execution authority: FORBIDDEN" in content or (
        "execution authority" in content.lower() and "FORBIDDEN" in content
    )


def test_project_status_autonomous_trading_excluded():
    content = _read(PROJECT_STATUS)
    assert "EXCLUDED_FOR_NOW" in content


def test_project_status_scheduler_not_started():
    content = _read(PROJECT_STATUS)
    assert "Scheduler status: NOT_STARTED" in content or (
        "Scheduler" in content and "NOT_STARTED" in content
    )


def test_project_status_bot_loop_not_started():
    content = _read(PROJECT_STATUS)
    assert "Bot loop status: NOT_STARTED" in content or (
        "bot loop" in content.lower() and "NOT_STARTED" in content
    )
