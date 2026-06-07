"""Focused docs tests for docs/project_status.md repo-truth consistency.

Added in WP43 to prevent stale WP42 branch wording from recurring after merge.
"""

from __future__ import annotations

import pathlib


REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
PROJECT_STATUS = REPO_ROOT / "docs" / "project_status.md"


def _read() -> str:
    return PROJECT_STATUS.read_text(encoding="utf-8")


def test_project_status_file_exists():
    assert PROJECT_STATUS.is_file()


def test_wp42_in_merged_wps_list():
    text = _read()
    assert "WP42" in text
    merged_line = next(
        line for line in text.splitlines() if line.startswith("- Merged WPs:")
    )
    assert "WP42" in merged_line


def test_advisory_operator_workflow_status_is_merged():
    text = _read()
    assert "DOCS_ONLY_ADVISORY_OPERATOR_WORKFLOW_MERGED" in text


def test_advisory_operator_workflow_status_not_on_branch():
    text = _read()
    assert "DOCS_ONLY_ADVISORY_OPERATOR_WORKFLOW_ON_BRANCH" not in text


def test_wp42_branch_not_current_branch():
    text = _read()
    branch_line = next(
        line for line in text.splitlines() if line.startswith("- Current branch:")
    )
    assert "wp42-advisory-consumer-operator-workflow-hardening" not in branch_line


def test_live_trading_status_disabled():
    text = _read()
    assert "Live trading status: DISABLED" in text


def test_credentials_status_not_used():
    text = _read()
    assert "Credentials status: NOT_USED" in text


def test_execution_status_not_started():
    text = _read()
    assert "Execution status: NOT_STARTED" in text


def test_hermes_status_not_installed():
    text = _read()
    assert "Hermes status: NOT_INSTALLED_NOT_RUNTIME_DEPENDENCY" in text


def test_agent_runtime_status_not_started():
    text = _read()
    assert "Agent runtime status: NOT_STARTED" in text


def test_agent_execution_authority_forbidden():
    text = _read()
    assert "Agent execution authority: FORBIDDEN" in text


def test_scheduler_status_not_started():
    text = _read()
    assert "Scheduler status: NOT_STARTED" in text


def test_bot_loop_status_not_started():
    text = _read()
    assert "Bot loop status: NOT_STARTED" in text


def test_authenticated_client_status_forbidden():
    text = _read()
    assert "Authenticated client status: FORBIDDEN_UNTIL_APPROVED_WP" in text


def test_official_client_runtime_dependency_status_not_started():
    text = _read()
    assert "Official client runtime dependency status: NOT_STARTED_FOR_OFFICIAL_CLIENT_RUNTIME" in text


def test_wp54_in_merged_wps_list():
    text = _read()
    merged_line = next(
        line for line in text.splitlines() if line.startswith("- Merged WPs:")
    )
    assert "WP54" in merged_line


def test_wp55_in_merged_wps_list():
    text = _read()
    merged_line = next(
        line for line in text.splitlines() if line.startswith("- Merged WPs:")
    )
    assert "WP55" in merged_line


def test_wp56_in_merged_phase_or_later():
    text = _read()
    # WP56 is merged; current phase is WP57 or later
    assert "WP56" in text


def test_wp55_branch_not_current_branch():
    text = _read()
    branch_line = next(
        line for line in text.splitlines() if line.startswith("- Current branch:")
    )
    assert "wp55-resolution-ambiguity-taxonomy-manual-label-workflow" not in branch_line


def test_wp54_bundled_wp_policy_status_is_merged():
    text = _read()
    assert "WORKFLOW_GOVERNANCE_MERGED" in text


def test_wp54_guard_flag_status_is_merged():
    text = _read()
    assert "LOCAL_OFFLINE_STDLIB_GUARD_HARDENING_MERGED" in text


def test_resolution_ambiguity_taxonomy_status_merged():
    text = _read()
    assert "DOCS_SCHEMA_TESTS_ONLY_MERGED" in text


def test_resolution_ambiguity_label_schema_validation_status_merged():
    text = _read()
    assert "LOCAL_OFFLINE_READ_ONLY_LABEL_SCHEMA_VALIDATION_MERGED" in text


def test_resolution_ambiguity_label_feature_extraction_status_merged():
    text = _read()
    assert "LOCAL_OFFLINE_READ_ONLY_LABEL_FEATURE_EXTRACTION_MERGED" in text


def test_wp56_in_merged_wps_list():
    text = _read()
    merged_line = next(
        line for line in text.splitlines() if line.startswith("- Merged WPs:")
    )
    assert "WP56" in merged_line


def test_wp57_in_merged_wps_list():
    text = _read()
    merged_line = next(
        line for line in text.splitlines() if line.startswith("- Merged WPs:")
    )
    assert "WP57" in merged_line


def test_wp61_is_current_phase():
    text = _read()
    current_phase_line = next(
        line for line in text.splitlines() if line.startswith("- Current phase:")
    )
    assert "WP61" in current_phase_line


def test_wp58_in_merged_wps():
    text = _read()
    merged_line = next(
        line for line in text.splitlines() if line.startswith("- Merged WPs:")
    )
    assert "WP58" in merged_line


def test_wp59_in_merged_wps():
    text = _read()
    merged_line = next(
        line for line in text.splitlines() if line.startswith("- Merged WPs:")
    )
    assert "WP59" in merged_line


def test_wp60a_in_merged_wps():
    text = _read()
    merged_line = next(
        line for line in text.splitlines() if line.startswith("- Merged WPs:")
    )
    assert "WP60A" in merged_line


def test_wp61_branch_is_current_branch():
    text = _read()
    branch_line = next(
        line for line in text.splitlines() if line.startswith("- Current branch:")
    )
    assert "wp61-architecture-lockin-and-microstructure-quality-v1" in branch_line


def test_wp59_branch_not_current_branch():
    text = _read()
    branch_line = next(
        line for line in text.splitlines() if line.startswith("- Current branch:")
    )
    assert "wp59-wf-stab-state-machine-private-repo-evidence-mode" not in branch_line


def test_wp58_branch_not_current_branch():
    text = _read()
    branch_line = next(
        line for line in text.splitlines() if line.startswith("- Current branch:")
    )
    assert "wp58-posted-evidence-and-claude-workflow-hardening" not in branch_line


def test_wp57_branch_not_current_branch():
    text = _read()
    branch_line = next(
        line for line in text.splitlines() if line.startswith("- Current branch:")
    )
    assert "wp57-resolution-ambiguity-label-feature-extraction" not in branch_line


def test_wp56_branch_not_current_branch():
    text = _read()
    branch_line = next(
        line for line in text.splitlines() if line.startswith("- Current branch:")
    )
    assert "wp56-resolution-ambiguity-label-schema-validation" not in branch_line


def test_protected_boundaries_unchanged():
    text = _read()
    assert "Live trading status: DISABLED" in text
    assert "Credentials status: NOT_USED" in text
    assert "Execution status: NOT_STARTED" in text
    assert "Hermes status: NOT_INSTALLED_NOT_RUNTIME_DEPENDENCY" in text
    assert "Agent runtime status: NOT_STARTED" in text
    assert "Agent execution authority: FORBIDDEN" in text
    assert "Scheduler status: NOT_STARTED" in text
    assert "Bot loop status: NOT_STARTED" in text
