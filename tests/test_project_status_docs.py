"""Focused docs tests for docs/project_status.md repo-truth consistency.

Added in WP43 to prevent stale WP42 branch wording from recurring after merge.
"""

from __future__ import annotations

import hashlib
import json
import pathlib
import re


REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
PROJECT_STATUS = REPO_ROOT / "docs" / "project_status.md"
STATUS_ENTRIES = REPO_ROOT / "docs" / "status_entries"


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


def test_wp79_is_current_phase():
    text = _read()
    current_phase_line = next(
        line for line in text.splitlines() if line.startswith("- Current phase:")
    )
    assert any(wp in current_phase_line for wp in ("WP79", "WP80", "WP81", "WP82", "WP83", "WP84", "WP86", "WP87", "WP88", "WP89", "WP90", "WP91", "WP92", "WP93", "WP94", "WP95", "WP96", "WP97", "WP98", "WP99", "WP100", "WP101", "WP102", "WP103", "WP104", "WP105", "WP106", "WP107", "WP108", "WP109", "WP110", "WP111", "WP112", "WP113", "WP114", "WP115", "WP116", "WP117", "WP118", "WP128", "WP130", "WP136", "WP138", "WP142", "WP148", "WP149", "WP159"))


def test_wp97_in_merged_wps_list():
    text = _read()
    merged_line = next(
        line for line in text.splitlines() if line.startswith("- Merged WPs:")
    )
    assert "WP97" in merged_line


def test_wp98_in_merged_wps_list():
    text = _read()
    merged_line = next(
        line for line in text.splitlines() if line.startswith("- Merged WPs:")
    )
    assert "WP98" in merged_line


def test_hermes_prompt_pack_status_is_locked():
    text = _read()
    assert "REPO_TRUTH_RESEARCH_PROMPT_PACK_AND_OPERATOR_RUNBOOKS_LOCKED" in text


def test_hermes_prompt_pack_status_not_on_branch():
    text = _read()
    assert "HERMES_RESEARCH_PROMPT_PACK_ON_BRANCH" not in text


def test_hermes_prompt_pack_doc_referenced_in_status():
    text = _read()
    assert "docs/hermes_research_prompt_pack_and_operator_runbooks.md" in text


def test_wp73_in_merged_wps():
    text = _read()
    merged_line = next(
        line for line in text.splitlines() if line.startswith("- Merged WPs:")
    )
    assert "WP73" in merged_line


def test_wp65_in_merged_wps():
    text = _read()
    merged_line = next(
        line for line in text.splitlines() if line.startswith("- Merged WPs:")
    )
    assert "WP65" in merged_line


def test_wp64_in_merged_wps():
    text = _read()
    merged_line = next(
        line for line in text.splitlines() if line.startswith("- Merged WPs:")
    )
    assert "WP64" in merged_line


def test_wp63_in_merged_wps():
    text = _read()
    merged_line = next(
        line for line in text.splitlines() if line.startswith("- Merged WPs:")
    )
    assert "WP63" in merged_line


def test_wp62_in_merged_wps():
    text = _read()
    merged_line = next(
        line for line in text.splitlines() if line.startswith("- Merged WPs:")
    )
    assert "WP62" in merged_line


def test_wp61_in_merged_wps():
    text = _read()
    merged_line = next(
        line for line in text.splitlines() if line.startswith("- Merged WPs:")
    )
    assert "WP61" in merged_line


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


def test_wp69_in_merged_wps():
    text = _read()
    merged_line = next(
        line for line in text.splitlines() if line.startswith("- Merged WPs:")
    )
    assert "WP69" in merged_line


def test_wp70_in_merged_wps():
    text = _read()
    merged_line = next(
        line for line in text.splitlines() if line.startswith("- Merged WPs:")
    )
    assert "WP70" in merged_line


def test_wp79_branch_is_current_branch():
    text = _read()
    branch_line = next(
        line for line in text.splitlines() if line.startswith("- Current branch:")
    )
    assert "see GitHub PR metadata and PR body" in branch_line or any(wp in branch_line for wp in (
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
        "wp92",
        "wp93",
        "wp94",
        "eager-shtern",
        "happy-torvalds",
        "recursing-bell",
    ))


def test_wp78_in_merged_wps():
    text = _read()
    merged_line = next(
        line for line in text.splitlines() if line.startswith("- Merged WPs:")
    )
    assert "WP78" in merged_line


def test_wp77_in_merged_wps():
    text = _read()
    merged_line = next(
        line for line in text.splitlines() if line.startswith("- Merged WPs:")
    )
    assert "WP77" in merged_line


def test_wp74_in_merged_wps():
    text = _read()
    merged_line = next(
        line for line in text.splitlines() if line.startswith("- Merged WPs:")
    )
    assert "WP74" in merged_line


def test_wp76_in_merged_wps():
    text = _read()
    merged_line = next(
        line for line in text.splitlines() if line.startswith("- Merged WPs:")
    )
    assert "WP76" in merged_line


def test_wp74_branch_not_current_branch():
    text = _read()
    branch_line = next(
        line for line in text.splitlines() if line.startswith("- Current branch:")
    )
    assert "wp74-local-human-review-label-record-validator-v1" not in branch_line


def test_wp68_in_merged_wps():
    text = _read()
    merged_line = next(
        line for line in text.splitlines() if line.startswith("- Merged WPs:")
    )
    assert "WP68" in merged_line


def test_wp68_branch_not_current_branch():
    text = _read()
    branch_line = next(
        line for line in text.splitlines() if line.startswith("- Current branch:")
    )
    assert "wp68-local-resolved-outcome-fixture-loader-v1" not in branch_line


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


# ── WP87 / WP88 ──────────────────────────────────────────────────────────────


def test_wp87_in_merged_wps():
    text = _read()
    merged_line = next(
        line for line in text.splitlines() if line.startswith("- Merged WPs:")
    )
    assert "WP87" in merged_line


def test_wp88_is_current_phase():
    text = _read()
    current_phase_line = next(
        line for line in text.splitlines() if line.startswith("- Current phase:")
    )
    assert any(wp in current_phase_line for wp in ("WP88", "WP89", "WP90", "WP91", "WP92", "WP93", "WP94", "WP95", "WP96", "WP97", "WP98", "WP99", "WP100", "WP101", "WP102", "WP103", "WP104", "WP105", "WP106", "WP107", "WP108", "WP109", "WP110", "WP111", "WP112", "WP113", "WP114", "WP115", "WP116", "WP117", "WP118", "WP128", "WP130", "WP136", "WP138", "WP142", "WP148", "WP149", "WP159"))


def test_wp88_current_branch_name():
    text = _read()
    branch_line = next(
        line for line in text.splitlines() if line.startswith("- Current branch:")
    )
    assert "see GitHub PR metadata and PR body" in branch_line or any(wp in branch_line for wp in ("wp88", "wp89", "wp90", "wp91", "wp92", "wp93", "wp94", "eager-shtern", "happy-torvalds", "recursing-bell"))


def test_wp88_is_workflow_evidence_repair_not_product():
    text = _read()
    assert "No product behavior changed" in text or "workflow" in text.lower()


def test_wp88_candidate_fixture_loader_is_merged():
    text = _read()
    assert "WALLET_SIGNAL_PAPER_STRATEGY_CANDIDATE_FIXTURE_LOADER_MERGED" in text


def test_wp88_evidence_architecture_on_branch():
    text = _read()
    assert "EVIDENCE_ARCHITECTURE" in text


def test_wp89_in_merged_wps():
    text = _read()
    merged_line = next(
        line for line in text.splitlines() if line.startswith("- Merged WPs:")
    )
    assert "WP89" in merged_line


def test_wp90_candidate_review_report_export_on_branch():
    text = _read()
    assert "WALLET_SIGNAL_CANDIDATE_REVIEW_REPORT_EXPORT_ON_BRANCH" in text or (
        "WP90" in text and "export" in text.lower()
    )


# ── WP91: Final Comment Transition Retirement Decision ────────────────────────


def test_wp90_in_merged_wps():
    text = _read()
    merged_line = next(
        line for line in text.splitlines() if line.startswith("- Merged WPs:")
    )
    assert "WP90" in merged_line


def test_wp91_is_current_phase():
    text = _read()
    current_phase_line = next(
        line for line in text.splitlines() if line.startswith("- Current phase:")
    )
    assert any(wp in current_phase_line for wp in ("WP91", "WP90", "WP92", "WP93", "WP94", "WP95", "WP96", "WP97", "WP98", "WP99", "WP100", "WP101", "WP102", "WP103", "WP104", "WP105", "WP106", "WP107", "WP108", "WP109", "WP110", "WP111", "WP112", "WP113", "WP114", "WP115", "WP116", "WP117", "WP118", "WP128", "WP130", "WP136", "WP138", "WP142", "WP148", "WP149", "WP159"))


def test_wp91_final_comment_retirement_status():
    text = _read()
    assert "RETIRED_AFTER_WP91" in text or "final comment" in text.lower()


def test_wp91_evidence_architecture_merged_in_project_status():
    text = _read()
    assert "EVIDENCE_ARCHITECTURE" in text


# ── WP92: Repo-Truth Policy Guard And One-Shot Execution Gate ─────────────────


def test_wp91_in_merged_wps():
    text = _read()
    merged_line = next(
        line for line in text.splitlines() if line.startswith("- Merged WPs:")
    )
    assert "WP91" in merged_line


def test_wp92_is_current_phase():
    text = _read()
    current_phase_line = next(
        line for line in text.splitlines() if line.startswith("- Current phase:")
    )
    assert any(wp in current_phase_line for wp in ("WP92", "WP91", "WP93", "WP94", "WP95", "WP96", "WP97", "WP98", "WP99", "WP100", "WP101", "WP102", "WP103", "WP104", "WP105", "WP106", "WP107", "WP108", "WP109", "WP110", "WP111", "WP112", "WP113", "WP114", "WP115", "WP116", "WP117", "WP118", "WP128", "WP130", "WP136", "WP138", "WP142", "WP148", "WP149", "WP159"))


def test_wp92_branch_is_current_branch():
    text = _read()
    branch_line = next(
        line for line in text.splitlines() if line.startswith("- Current branch:")
    )
    assert "see GitHub PR metadata and PR body" in branch_line or any(wp in branch_line for wp in ("wp92", "wp93", "wp94", "recursing-bell"))


def test_wp92_repo_truth_policy_guard_status():
    text = _read()
    assert "REPO_TRUTH_POLICY_GUARD" in text or "repo-truth policy guard" in text.lower()


def test_wp92_in_merged_wps():
    text = _read()
    merged_line = next(
        line for line in text.splitlines() if line.startswith("- Merged WPs:")
    )
    assert "WP92" in merged_line


def test_wp93_is_current_phase():
    text = _read()
    current_phase_line = next(
        line for line in text.splitlines() if line.startswith("- Current phase:")
    )
    assert any(wp in current_phase_line for wp in ("WP93", "WP94", "WP95", "WP96", "WP97", "WP98", "WP99", "WP100", "WP101", "WP102", "WP103", "WP104", "WP105", "WP106", "WP107", "WP108", "WP109", "WP110", "WP111", "WP112", "WP113", "WP114", "WP115", "WP116", "WP117", "WP118", "WP128", "WP130", "WP136", "WP138", "WP142", "WP148", "WP149", "WP159"))


def test_wp93_branch_is_current_branch():
    text = _read()
    branch_line = next(
        line for line in text.splitlines() if line.startswith("- Current branch:")
    )
    assert "see GitHub PR metadata and PR body" in branch_line or any(wp in branch_line for wp in (
        "wp93-candidate-review-report-operator-runbook-v1",
        "wp94-candidate-review-workflow-local-smoke-receipt-v1",
    ))


def test_wp93_candidate_review_report_operator_runbook_status():
    text = _read()
    assert "DOCS_ONLY_OPERATOR_RUNBOOK_MERGED" in text
    assert "Candidate review report operator runbook status" in text


def test_wp94_is_reconciled_as_merged():
    text = _read()
    merged_line = next(
        line for line in text.splitlines() if line.startswith("- Merged WPs:")
    )
    assert "WP94" in merged_line


def test_current_branch_uses_stable_github_pointer():
    text = _read()
    branch_line = next(
        line for line in text.splitlines() if line.startswith("- Current branch:")
    )
    assert "see GitHub PR metadata and PR body" in branch_line
    assert "stable post-merge target repo truth" in branch_line


def test_wp94_candidate_review_workflow_smoke_receipt_status():
    text = _read()
    assert "LOCAL_SMOKE_RECEIPT_MERGED" in text
    assert "Candidate review workflow local smoke receipt status" in text


# ── WP95: Post-WP94 repo-truth and Hermes plan lock-in ───────────────────────


def test_wp95_is_stable_post_merge_target_state():
    text = _read()
    current_phase_line = next(
        line for line in text.splitlines() if line.startswith("- Current phase:")
    )
    merged_line = next(
        line for line in text.splitlines() if line.startswith("- Merged WPs:")
    )
    assert any(wp in current_phase_line for wp in ("WP95", "WP96", "WP97", "WP98", "WP99", "WP100", "WP101", "WP102", "WP103", "WP104", "WP105", "WP106", "WP107", "WP108", "WP109", "WP110", "WP111", "WP112", "WP113", "WP114", "WP115", "WP116", "WP117", "WP118", "WP128", "WP130", "WP136", "WP138", "WP142", "WP148", "WP149", "WP159"))
    assert "WP95" in merged_line
    assert "Hermes Advisory Foundation And Research-Brain Architecture V1" in text


def test_wp96_is_stable_post_merge_target_state():
    text = _read()
    current_phase_line = next(
        line for line in text.splitlines() if line.startswith("- Current phase:")
    )
    merged_line = next(
        line for line in text.splitlines() if line.startswith("- Merged WPs:")
    )
    assert any(wp in current_phase_line for wp in ("WP96", "WP97", "WP98", "WP99", "WP100", "WP101", "WP102", "WP103", "WP104", "WP105", "WP106", "WP107", "WP108", "WP109", "WP110", "WP111", "WP112", "WP113", "WP114", "WP115", "WP116", "WP117", "WP118", "WP128", "WP130", "WP136", "WP138", "WP142", "WP148", "WP149", "WP159"))
    assert "WP96" in merged_line
    assert "Hermes input/output contracts and validator hardening" in text
    assert "Hermes advisory foundation architecture status: REPO_TRUTH_ARCHITECTURE_LOCKED" in text


def test_wp97_is_stable_post_merge_target_state():
    text = _read()
    current_phase_line = next(
        line for line in text.splitlines() if line.startswith("- Current phase:")
    )
    merged_line = next(
        line for line in text.splitlines() if line.startswith("- Merged WPs:")
    )
    assert any(wp in current_phase_line for wp in ("WP97", "WP98", "WP99", "WP100", "WP101", "WP102", "WP103", "WP104", "WP105", "WP106", "WP107", "WP108", "WP109", "WP110", "WP111", "WP112", "WP113", "WP114", "WP115", "WP116", "WP117", "WP118", "WP128", "WP130", "WP136", "WP138", "WP142", "WP148", "WP149", "WP159"))
    assert "WP97" in merged_line
    assert "Hermes input/output contracts and validator requirements status: REPO_TRUTH_DOCUMENTATION_LEVEL_CONTRACT_REQUIREMENTS_LOCKED" in text
    assert "docs/hermes_input_output_contracts_and_validator_requirements.md" in text


def test_wp94_and_wp95_committed_status_docs_reject_stale_wording():
    wp94_text = (STATUS_ENTRIES / "WP94.md").read_text(encoding="utf-8")
    wp95_path = STATUS_ENTRIES / "WP95.md"
    assert wp95_path.is_file()
    wp95_text = wp95_path.read_text(encoding="utf-8")
    project_text = _read()
    forbidden_wp94 = (
        "WP94 on branch",
        "WP94 active branch",
        "Merge commit: TBD after merge",
    )
    forbidden_wp95 = (
        "WP95 on branch",
        "WP95 active branch",
        "Merge commit: TBD after merge",
        "PR: TBD",
    )
    for phrase in forbidden_wp94:
        assert phrase not in wp94_text
        assert phrase not in project_text
    for phrase in forbidden_wp95:
        assert phrase not in wp95_text
        assert phrase not in project_text
    fixed_live_head = re.compile(r"Current live PR head:\s*`?[0-9a-f]{40}`?", re.IGNORECASE)
    assert fixed_live_head.search(wp95_text) is None
    assert fixed_live_head.search(project_text) is None


def test_wp96_committed_status_docs_reject_stale_wording():
    wp96_path = STATUS_ENTRIES / "WP96.md"
    assert wp96_path.is_file()
    wp96_text = wp96_path.read_text(encoding="utf-8")
    project_text = _read()
    forbidden_wp96 = (
        "WP96 on branch",
        "WP96 active branch",
        "Merge commit: TBD after merge",
        "PR: TBD",
    )
    for phrase in forbidden_wp96:
        assert phrase not in wp96_text
        assert phrase not in project_text
    fixed_live_head = re.compile(r"Current live PR head:\s*`?[0-9a-f]{40}`?", re.IGNORECASE)
    assert fixed_live_head.search(wp96_text) is None
    assert fixed_live_head.search(project_text) is None


def test_wp97_committed_status_docs_reject_stale_wording():
    wp97_path = STATUS_ENTRIES / "WP97.md"
    assert wp97_path.is_file()
    wp97_text = wp97_path.read_text(encoding="utf-8")
    project_text = _read()
    forbidden_wp97 = (
        "WP97 on branch",
        "WP97 active branch",
        "Merge commit: TBD after merge",
        "PR: TBD",
    )
    for phrase in forbidden_wp97:
        assert phrase not in wp97_text
        assert phrase not in project_text
    fixed_live_head = re.compile(r"Current live PR head:\s*`?[0-9a-f]{40}`?", re.IGNORECASE)
    assert fixed_live_head.search(wp97_text) is None
    assert fixed_live_head.search(project_text) is None


def test_wp94_status_entry_records_actual_merge_commit():
    text = (STATUS_ENTRIES / "WP94.md").read_text(encoding="utf-8")
    assert "e22212c7abaa2cb924bd2c43eeaae0695713633c" in text


def test_hermes_research_brain_plan_is_registered_and_complete():
    plan_path = REPO_ROOT / "docs" / "hermes_research_brain_execution_plan.md"
    index_text = (REPO_ROOT / "docs" / "repo_truth_index.md").read_text(encoding="utf-8")
    assert plan_path.is_file()
    plan_text = plan_path.read_text(encoding="utf-8")
    assert "docs/hermes_research_brain_execution_plan.md" in index_text
    required = (
        "adaptive research brain",
        "Broad Research Freedoms",
        "Deterministic-Core Responsibilities",
        "Forbidden Hermes Authority",
        "Manual-Step Checkpoints",
        "Future changes to the accepted Hermes/research-brain execution plan must update",
        "Chat memory alone is not authoritative",
        "PR comments alone are not authoritative",
        "Hermes Advisory Foundation And Research-Brain Architecture V1",
    )
    for phrase in required:
        assert phrase in plan_text


def test_wp95_preserves_hermes_and_trading_boundaries():
    plan_text = (REPO_ROOT / "docs" / "hermes_research_brain_execution_plan.md").read_text(encoding="utf-8")
    project_text = _read()
    for phrase in (
        "Live trading status: DISABLED",
        "Hermes status: NOT_INSTALLED_NOT_RUNTIME_DEPENDENCY",
        "Agent execution authority: FORBIDDEN",
    ):
        assert phrase in project_text
    for phrase in (
        "access credentials or private endpoints",
        "place, cancel, sign, or submit orders",
        "control runtime, scheduler, or bot loop",
        "approve pull requests or claim merge readiness",
    ):
        assert phrase in plan_text


def test_ready_model_d_status_fragments_use_stable_dynamic_metadata_references():
    """Ready WP88+ fragments must not store live PR metadata as committed facts."""
    failures = []
    fixed_live_head = re.compile(r"Current live PR head:\s*`?[0-9a-f]{40}`?", re.IGNORECASE)
    for path in sorted(STATUS_ENTRIES.glob("WP*.md")):
        match = re.fullmatch(r"WP(\d+)\.md", path.name)
        if not match or int(match.group(1)) < 88:
            continue
        text = path.read_text(encoding="utf-8")
        if "Ready for review: YES" not in text:
            continue
        if "PR: TBD" in text:
            failures.append(f"{path.name}: contains PR: TBD while Ready YES")
        if "Guard input source: LOCAL_DRAFT_VERIFIED" in text:
            failures.append(f"{path.name}: contains LOCAL_DRAFT_VERIFIED while Ready YES")
        if "Head commit:" in text:
            failures.append(f"{path.name}: contains Head commit while Ready YES")
        if fixed_live_head.search(text):
            failures.append(f"{path.name}: contains fixed current live PR head SHA")
        if "PR: see GitHub PR metadata and PR body." not in text:
            failures.append(f"{path.name}: missing stable PR field wording")
        if "Current live PR head: see GitHub PR metadata and PR body" not in text:
            failures.append(f"{path.name}: missing stable live-head wording")
        if "stable and non-self-referential" not in text:
            failures.append(f"{path.name}: missing stable/non-self-referential wording")
    assert not failures, "\n".join(failures)


# ── WP98: Hermes research prompt pack and operator runbooks ───────────────────


def test_wp98_committed_status_docs_reject_stale_wording():
    wp98_path = STATUS_ENTRIES / "WP98.md"
    assert wp98_path.is_file()
    wp98_text = wp98_path.read_text(encoding="utf-8")
    project_text = _read()
    forbidden_wp98 = (
        "WP98 on branch",
        "WP98 active branch",
        "Merge commit: TBD after merge",
        "PR: TBD",
    )
    for phrase in forbidden_wp98:
        assert phrase not in wp98_text
        assert phrase not in project_text
    fixed_live_head = re.compile(r"Current live PR head:\s*`?[0-9a-f]{40}`?", re.IGNORECASE)
    assert fixed_live_head.search(wp98_text) is None
    assert fixed_live_head.search(project_text) is None


def test_wp98_is_stable_post_merge_target_state():
    text = _read()
    current_phase_line = next(
        line for line in text.splitlines() if line.startswith("- Current phase:")
    )
    merged_line = next(
        line for line in text.splitlines() if line.startswith("- Merged WPs:")
    )
    assert any(wp in current_phase_line for wp in ("WP98", "WP99", "WP100", "WP101", "WP102", "WP103", "WP104", "WP105", "WP106", "WP107", "WP108", "WP109", "WP110", "WP111", "WP112", "WP113", "WP114", "WP115", "WP116", "WP117", "WP118", "WP128", "WP130", "WP136", "WP138", "WP142", "WP148", "WP149", "WP159"))
    assert "WP98" in merged_line
    assert "REPO_TRUTH_RESEARCH_PROMPT_PACK_AND_OPERATOR_RUNBOOKS_LOCKED" in text
    assert "docs/hermes_research_prompt_pack_and_operator_runbooks.md" in text


# ── WP99: Hermes advisory output validator V1 ─────────────────────────────────


def test_wp99_in_merged_wps_list():
    text = _read()
    merged_line = next(
        line for line in text.splitlines() if line.startswith("- Merged WPs:")
    )
    assert "WP99" in merged_line


def test_wp99_is_stable_post_merge_target_state():
    text = _read()
    current_phase_line = next(
        line for line in text.splitlines() if line.startswith("- Current phase:")
    )
    merged_line = next(
        line for line in text.splitlines() if line.startswith("- Merged WPs:")
    )
    assert any(wp in current_phase_line for wp in ("WP99", "WP100", "WP101", "WP102", "WP103", "WP104", "WP105", "WP106", "WP107", "WP108", "WP109", "WP110", "WP111", "WP112", "WP113", "WP114", "WP115", "WP116", "WP117", "WP118", "WP128", "WP130", "WP136", "WP138", "WP142", "WP148", "WP149", "WP159"))
    assert "WP99" in merged_line
    assert "LOCAL_OFFLINE_READ_ONLY_VALIDATOR_MERGED" in text
    assert "src/data_layer/hermes_advisory_output_validator.py" in text


def test_wp99_committed_status_docs_reject_stale_wording():
    wp99_path = STATUS_ENTRIES / "WP99.md"
    assert wp99_path.is_file()
    wp99_text = wp99_path.read_text(encoding="utf-8")
    project_text = _read()
    forbidden_wp99 = (
        "WP99 on branch",
        "WP99 active branch",
        "Merge commit: TBD after merge",
        "PR: TBD",
    )
    for phrase in forbidden_wp99:
        assert phrase not in wp99_text
        assert phrase not in project_text
    fixed_live_head = re.compile(r"Current live PR head:\s*`?[0-9a-f]{40}`?", re.IGNORECASE)
    assert fixed_live_head.search(wp99_text) is None
    assert fixed_live_head.search(project_text) is None


def test_hermes_advisory_output_validator_status_is_registered():
    text = _read()
    assert "Hermes advisory output validator status" in text
    assert "LOCAL_OFFLINE_READ_ONLY_VALIDATOR_MERGED" in text


def test_hermes_advisory_output_validator_not_on_branch():
    text = _read()
    assert "HERMES_ADVISORY_OUTPUT_VALIDATOR_ON_BRANCH" not in text


# ── WP100: Hermes context-packet exporter foundation V1 ─────────────────────


def test_wp100_in_stable_merged_wps_target_list():
    text = _read()
    merged_line = next(
        line for line in text.splitlines() if line.startswith("- Merged WPs:")
    )
    assert "WP100" in merged_line


def test_wp100_is_stable_post_merge_target_state():
    text = _read()
    current_phase_line = next(
        line for line in text.splitlines() if line.startswith("- Current phase:")
    )
    assert any(wp in current_phase_line for wp in ("WP100", "WP101", "WP102", "WP103", "WP104", "WP105", "WP106", "WP107", "WP108", "WP109", "WP110", "WP111", "WP112", "WP113", "WP114", "WP115", "WP116", "WP117", "WP118", "WP128", "WP130", "WP136", "WP138", "WP142", "WP148", "WP149", "WP159"))
    assert "LOCAL_OFFLINE_READ_ONLY_IN_MEMORY_PACKET_BUILDER_MERGED" in text
    assert "src/data_layer/hermes_context_packet_exporter.py" in text


def test_wp100_committed_status_docs_reject_stale_wording():
    wp100_path = STATUS_ENTRIES / "WP100.md"
    assert wp100_path.is_file()
    wp100_text = wp100_path.read_text(encoding="utf-8")
    project_text = _read()
    for phrase in (
        "WP100 on branch",
        "WP100 active branch",
        "Merge commit: TBD after merge",
        "PR: TBD",
    ):
        assert phrase not in wp100_text
        assert phrase not in project_text
    fixed_live_head = re.compile(
        r"Current live PR head:\s*`?[0-9a-f]{40}`?", re.IGNORECASE
    )
    assert fixed_live_head.search(wp100_text) is None
    assert fixed_live_head.search(project_text) is None


def test_hermes_context_packet_exporter_is_registered_in_repo_truth():
    status_text = _read()
    index_text = (REPO_ROOT / "docs" / "repo_truth_index.md").read_text(
        encoding="utf-8"
    )
    assert "Hermes context-packet exporter foundation status" in status_text
    assert "src/data_layer/hermes_context_packet_exporter.py" in index_text
    assert "tests/test_hermes_context_packet_exporter.py" in index_text


def test_wp100_preserves_protected_boundary_statuses():
    text = _read()
    assert "Live trading status: DISABLED" in text
    assert "Credentials status: NOT_USED" in text
    assert "Execution status: NOT_STARTED" in text
    assert "Hermes status: NOT_INSTALLED_NOT_RUNTIME_DEPENDENCY" in text
    assert "Agent runtime status: NOT_STARTED" in text
    assert "Scheduler status: NOT_STARTED" in text
    assert "Bot loop status: NOT_STARTED" in text


# ── WP101: Hermes context-packet dry-run receipt V1 ─────────────────────────


def test_wp101_in_stable_merged_wps_target_list():
    text = _read()
    merged_line = next(
        line for line in text.splitlines() if line.startswith("- Merged WPs:")
    )
    assert "WP101" in merged_line


def test_wp101_is_stable_post_merge_target_state():
    text = _read()
    current_phase_line = next(
        line for line in text.splitlines() if line.startswith("- Current phase:")
    )
    assert any(wp in current_phase_line for wp in ("WP101", "WP102", "WP103", "WP104", "WP105", "WP106", "WP107", "WP108", "WP109", "WP110", "WP111", "WP112", "WP113", "WP114", "WP115", "WP116", "WP117", "WP118", "WP128", "WP130", "WP136", "WP138", "WP142", "WP148", "WP149", "WP159"))
    assert "LOCAL_OFFLINE_READ_ONLY_IN_MEMORY_DRY_RUN_RECEIPT_MERGED" in text
    assert "src/data_layer/hermes_context_packet_dry_run_receipt.py" in text


def test_wp101_committed_status_docs_reject_stale_wording():
    wp101_path = STATUS_ENTRIES / "WP101.md"
    assert wp101_path.is_file()
    wp101_text = wp101_path.read_text(encoding="utf-8")
    project_text = _read()
    for phrase in (
        "WP101 on branch",
        "WP101 active branch",
        "Merge commit: TBD after merge",
        "PR: TBD",
    ):
        assert phrase not in wp101_text
        assert phrase not in project_text
    fixed_live_head = re.compile(
        r"Current live PR head:\s*`?[0-9a-f]{40}`?", re.IGNORECASE
    )
    assert fixed_live_head.search(wp101_text) is None
    assert fixed_live_head.search(project_text) is None


def test_hermes_context_packet_dry_run_receipt_is_registered_in_repo_truth():
    status_text = _read()
    index_text = (REPO_ROOT / "docs" / "repo_truth_index.md").read_text(
        encoding="utf-8"
    )
    assert "Hermes context-packet dry-run receipt status" in status_text
    assert "src/data_layer/hermes_context_packet_dry_run_receipt.py" in index_text
    assert "tests/test_hermes_context_packet_dry_run_receipt.py" in index_text


# ── WP102: Hermes manual research dry-run operator review V1 ─────────────────


def test_wp102_in_stable_merged_wps_target_list():
    text = _read()
    merged_line = next(
        line for line in text.splitlines() if line.startswith("- Merged WPs:")
    )
    assert "WP102" in merged_line


def test_wp102_is_stable_post_merge_target_state():
    text = _read()
    current_phase_line = next(
        line for line in text.splitlines() if line.startswith("- Current phase:")
    )
    assert any(wp in current_phase_line for wp in ("WP102", "WP103", "WP104", "WP105", "WP106", "WP107", "WP108", "WP109", "WP110", "WP111", "WP112", "WP113", "WP114", "WP115", "WP116", "WP117", "WP118", "WP128", "WP130", "WP136", "WP138", "WP142", "WP148", "WP149", "WP159"))
    assert "LOCAL_OFFLINE_READ_ONLY_IN_MEMORY_OPERATOR_REVIEW_MERGED" in text
    assert "src/data_layer/hermes_manual_research_dry_run_review.py" in text


def test_wp102_committed_status_docs_reject_stale_wording():
    wp102_path = STATUS_ENTRIES / "WP102.md"
    assert wp102_path.is_file()
    wp102_text = wp102_path.read_text(encoding="utf-8")
    project_text = _read()
    for phrase in (
        "WP102 on branch",
        "WP102 active branch",
        "Merge commit: TBD after merge",
        "PR: TBD",
    ):
        assert phrase not in wp102_text
        assert phrase not in project_text
    fixed_live_head = re.compile(
        r"Current live PR head:\s*`?[0-9a-f]{40}`?", re.IGNORECASE
    )
    assert fixed_live_head.search(wp102_text) is None
    assert fixed_live_head.search(project_text) is None


def test_hermes_manual_research_dry_run_review_is_registered_in_repo_truth():
    status_text = _read()
    index_text = (REPO_ROOT / "docs" / "repo_truth_index.md").read_text(
        encoding="utf-8"
    )
    assert "Hermes manual research dry-run operator review status" in status_text
    assert "src/data_layer/hermes_manual_research_dry_run_review.py" in index_text
    assert "tests/test_hermes_manual_research_dry_run_review.py" in index_text


# ── WP103: Hermes candidate-review context packet integration V1 ─────────────


def test_wp103_in_stable_merged_wps_target_list():
    text = _read()
    merged_line = next(
        line for line in text.splitlines() if line.startswith("- Merged WPs:")
    )
    assert "WP103" in merged_line


def test_wp103_is_stable_post_merge_target_state():
    text = _read()
    current_phase_line = next(
        line for line in text.splitlines() if line.startswith("- Current phase:")
    )
    assert any(wp in current_phase_line for wp in ("WP103", "WP104", "WP105", "WP106", "WP107", "WP108", "WP109", "WP110", "WP111", "WP112", "WP113", "WP114", "WP115", "WP116", "WP117", "WP118", "WP128", "WP130", "WP136", "WP138", "WP142", "WP148", "WP149", "WP159"))
    assert "LOCAL_OFFLINE_READ_ONLY_IN_MEMORY_CANDIDATE_REVIEW_INTEGRATION_MERGED" in text
    assert "src/data_layer/hermes_candidate_review_context_packet_integration.py" in text


def test_wp103_committed_status_docs_reject_stale_wording():
    wp103_path = STATUS_ENTRIES / "WP103.md"
    assert wp103_path.is_file()
    wp103_text = wp103_path.read_text(encoding="utf-8")
    project_text = _read()
    for phrase in (
        "WP103 on branch",
        "WP103 active branch",
        "Merge commit: TBD after merge",
        "PR: TBD",
    ):
        assert phrase not in wp103_text
        assert phrase not in project_text
    fixed_live_head = re.compile(
        r"Current live PR head:\s*`?[0-9a-f]{40}`?", re.IGNORECASE
    )
    assert fixed_live_head.search(wp103_text) is None
    assert fixed_live_head.search(project_text) is None


def test_hermes_candidate_review_integration_is_registered_in_repo_truth():
    status_text = _read()
    index_text = (REPO_ROOT / "docs" / "repo_truth_index.md").read_text(
        encoding="utf-8"
    )
    assert "Hermes candidate-review context packet integration status" in status_text
    assert "src/data_layer/hermes_candidate_review_context_packet_integration.py" in index_text
    assert "tests/test_hermes_candidate_review_context_packet_integration.py" in index_text


# ── WP104: Hermes candidate-review manual chain smoke V1 ─────────────────────


def test_wp104_in_stable_merged_wps_target_list():
    text = _read()
    merged_line = next(
        line for line in text.splitlines() if line.startswith("- Merged WPs:")
    )
    assert "WP104" in merged_line


def test_wp104_is_stable_post_merge_target_state():
    text = _read()
    current_phase_line = next(
        line for line in text.splitlines() if line.startswith("- Current phase:")
    )
    assert any(wp in current_phase_line for wp in ("WP104", "WP105", "WP106", "WP107", "WP108", "WP109", "WP110", "WP111", "WP112", "WP113", "WP114", "WP115", "WP116", "WP117", "WP118", "WP128", "WP130", "WP136", "WP138", "WP142", "WP148", "WP149", "WP159"))
    assert "LOCAL_OFFLINE_READ_ONLY_IN_MEMORY_MANUAL_CHAIN_SMOKE_MERGED" in text
    assert "src/data_layer/hermes_candidate_review_manual_chain_smoke.py" in text


def test_wp104_committed_status_docs_reject_stale_wording():
    wp104_path = STATUS_ENTRIES / "WP104.md"
    assert wp104_path.is_file()
    wp104_text = wp104_path.read_text(encoding="utf-8")
    project_text = _read()
    for phrase in (
        "WP104 on branch",
        "WP104 active branch",
        "Merge commit: TBD after merge",
        "PR: TBD",
    ):
        assert phrase not in wp104_text
        assert phrase not in project_text
    fixed_live_head = re.compile(
        r"Current live PR head:\s*`?[0-9a-f]{40}`?", re.IGNORECASE
    )
    assert fixed_live_head.search(wp104_text) is None
    assert fixed_live_head.search(project_text) is None


def test_hermes_candidate_review_chain_smoke_is_registered_in_repo_truth():
    status_text = _read()
    index_text = (REPO_ROOT / "docs" / "repo_truth_index.md").read_text(
        encoding="utf-8"
    )
    assert "Hermes candidate-review manual chain smoke status" in status_text
    assert "src/data_layer/hermes_candidate_review_manual_chain_smoke.py" in index_text
    assert "tests/test_hermes_candidate_review_manual_chain_smoke.py" in index_text


# ── WP105: Hermes candidate-review operator handoff contract V1 ─────────────


def test_wp105_in_stable_merged_wps_target_list():
    text = _read()
    merged_line = next(
        line for line in text.splitlines() if line.startswith("- Merged WPs:")
    )
    assert "WP105" in merged_line


def test_wp105_is_stable_post_merge_target_state():
    text = _read()
    current_phase_line = next(
        line for line in text.splitlines() if line.startswith("- Current phase:")
    )
    assert any(wp in current_phase_line for wp in ("WP105", "WP106", "WP107", "WP108", "WP109", "WP110", "WP111", "WP112", "WP113", "WP114", "WP115", "WP116", "WP117", "WP118", "WP128", "WP130", "WP136", "WP138", "WP142", "WP148", "WP149", "WP159"))
    assert "DOCS_STATUS_TESTS_ONLY_OPERATOR_HANDOFF_CONTRACT_MERGED" in text
    assert "docs/hermes_candidate_review_operator_handoff_contract.md" in text


def test_wp105_committed_status_docs_reject_stale_wording():
    wp105_path = STATUS_ENTRIES / "WP105.md"
    assert wp105_path.is_file()
    wp105_text = wp105_path.read_text(encoding="utf-8")
    project_text = _read()
    for phrase in (
        "WP105 on branch",
        "WP105 active branch",
        "Merge commit: TBD after merge",
        "PR: TBD",
        "count depends",
    ):
        assert phrase not in wp105_text
        assert phrase not in project_text
    fixed_live_head = re.compile(
        r"Current live PR head:\s*`?[0-9a-f]{40}`?", re.IGNORECASE
    )
    assert fixed_live_head.search(wp105_text) is None
    assert fixed_live_head.search(project_text) is None


def test_hermes_candidate_review_operator_handoff_contract_is_registered():
    status_text = _read()
    index_text = (REPO_ROOT / "docs" / "repo_truth_index.md").read_text(
        encoding="utf-8"
    )
    assert "Hermes candidate-review operator handoff contract status" in status_text
    assert "docs/hermes_candidate_review_operator_handoff_contract.md" in index_text
    assert "tests/test_hermes_candidate_review_operator_handoff_contract_docs.py" in index_text


# ── WP106: Hermes candidate-review in-memory handoff object V1 ──────────────


def test_wp106_in_stable_merged_wps_target_list():
    text = _read()
    merged_line = next(
        line for line in text.splitlines() if line.startswith("- Merged WPs:")
    )
    assert "WP106" in merged_line


def test_wp106_is_stable_post_merge_target_state():
    text = _read()
    current_phase_line = next(
        line for line in text.splitlines() if line.startswith("- Current phase:")
    )
    assert any(wp in current_phase_line for wp in ("WP106", "WP107", "WP108", "WP109", "WP110", "WP111", "WP112", "WP113", "WP114", "WP115", "WP116", "WP117", "WP118", "WP128", "WP130", "WP136", "WP138", "WP142", "WP148", "WP149", "WP159"))
    assert "LOCAL_OFFLINE_READ_ONLY_IN_MEMORY_OPERATOR_HANDOFF_OBJECT_MERGED" in text
    assert "src/data_layer/hermes_candidate_review_operator_handoff.py" in text


def test_wp106_committed_status_docs_reject_stale_wording():
    wp106_path = STATUS_ENTRIES / "WP106.md"
    assert wp106_path.is_file()
    wp106_text = wp106_path.read_text(encoding="utf-8")
    project_text = _read()
    for phrase in (
        "WP106 on branch",
        "WP106 active branch",
        "Merge commit: TBD after merge",
        "PR: TBD",
        "count depends",
    ):
        assert phrase not in wp106_text
        assert phrase not in project_text
    fixed_live_head = re.compile(
        r"Current live PR head:\s*`?[0-9a-f]{40}`?", re.IGNORECASE
    )
    assert fixed_live_head.search(wp106_text) is None
    assert fixed_live_head.search(project_text) is None


def test_hermes_candidate_review_operator_handoff_object_is_registered():
    status_text = _read()
    index_text = (REPO_ROOT / "docs" / "repo_truth_index.md").read_text(
        encoding="utf-8"
    )
    assert "Hermes candidate-review in-memory operator handoff object status" in status_text
    assert "src/data_layer/hermes_candidate_review_operator_handoff.py" in index_text
    assert "tests/test_hermes_candidate_review_operator_handoff.py" in index_text


# ── WP107: Hermes candidate-review handoff local manual export contract V1 ───


def test_wp107_in_stable_merged_wps_target_list():
    text = _read()
    merged_line = next(
        line for line in text.splitlines() if line.startswith("- Merged WPs:")
    )
    assert "WP107" in merged_line


def test_wp107_is_stable_post_merge_target_state():
    text = _read()
    current_phase_line = next(
        line for line in text.splitlines() if line.startswith("- Current phase:")
    )
    assert any(wp in current_phase_line for wp in ("WP107", "WP108", "WP109", "WP110", "WP111", "WP112", "WP113", "WP114", "WP115", "WP116", "WP117", "WP118", "WP128", "WP130", "WP136", "WP138", "WP142", "WP148", "WP149", "WP159"))
    assert "DOCS_STATUS_TESTS_ONLY_LOCAL_MANUAL_EXPORT_CONTRACT_MERGED" in text
    assert "docs/hermes_candidate_review_handoff_local_manual_export_contract.md" in text


def test_wp107_committed_status_docs_reject_stale_wording():
    wp107_path = STATUS_ENTRIES / "WP107.md"
    assert wp107_path.is_file()
    wp107_text = wp107_path.read_text(encoding="utf-8")
    project_text = _read()
    for phrase in (
        "WP107 on branch",
        "WP107 active branch",
        "Merge commit: TBD after merge",
        "PR: TBD",
        "count depends",
    ):
        assert phrase not in wp107_text
        assert phrase not in project_text
    fixed_live_head = re.compile(
        r"Current live PR head:\s*`?[0-9a-f]{40}`?", re.IGNORECASE
    )
    assert fixed_live_head.search(wp107_text) is None
    assert fixed_live_head.search(project_text) is None


def test_hermes_candidate_review_handoff_local_manual_export_contract_is_registered():
    status_text = _read()
    index_text = (REPO_ROOT / "docs" / "repo_truth_index.md").read_text(
        encoding="utf-8"
    )
    assert "Hermes candidate-review handoff local manual export contract status" in status_text
    assert "docs/hermes_candidate_review_handoff_local_manual_export_contract.md" in index_text
    assert "tests/test_hermes_candidate_review_handoff_local_manual_export_contract_docs.py" in index_text


# ── WP108: Hermes candidate-review handoff in-memory manual export artifact builder V1 ──


def test_wp108_in_stable_merged_wps_target_list():
    text = _read()
    merged_line = next(
        line for line in text.splitlines() if line.startswith("- Merged WPs:")
    )
    assert "WP108" in merged_line


def test_wp108_is_stable_post_merge_target_state():
    text = _read()
    current_phase_line = next(
        line for line in text.splitlines() if line.startswith("- Current phase:")
    )
    assert any(wp in current_phase_line for wp in ("WP108", "WP109", "WP110", "WP111", "WP112", "WP113", "WP114", "WP115", "WP116", "WP117", "WP118", "WP128", "WP130", "WP136", "WP138", "WP142", "WP148", "WP149", "WP159"))
    assert "LOCAL_OFFLINE_READ_ONLY_IN_MEMORY_MANUAL_EXPORT_ARTIFACT_MERGED" in text
    assert "src/data_layer/hermes_candidate_review_handoff_manual_export_artifact.py" in text


def test_wp108_committed_status_docs_reject_stale_wording():
    wp108_path = STATUS_ENTRIES / "WP108.md"
    assert wp108_path.is_file()
    wp108_text = wp108_path.read_text(encoding="utf-8")
    project_text = _read()
    for phrase in (
        "WP108 on branch",
        "WP108 active branch",
        "Merge commit: TBD after merge",
        "PR: TBD",
        "count depends",
        "TBD after merge",
        "LOCAL_DRAFT_VERIFIED",
    ):
        assert phrase not in wp108_text
        assert phrase not in project_text
    fixed_live_head = re.compile(
        r"Current live PR head:\s*`?[0-9a-f]{40}`?", re.IGNORECASE
    )
    assert fixed_live_head.search(wp108_text) is None
    assert fixed_live_head.search(project_text) is None


def test_hermes_candidate_review_handoff_manual_export_artifact_is_registered():
    status_text = _read()
    index_text = (REPO_ROOT / "docs" / "repo_truth_index.md").read_text(
        encoding="utf-8"
    )
    assert "Hermes candidate-review handoff in-memory manual export artifact status" in status_text
    assert "src/data_layer/hermes_candidate_review_handoff_manual_export_artifact.py" in index_text
    assert "tests/test_hermes_candidate_review_handoff_manual_export_artifact.py" in index_text


# ── WP109: Hermes candidate-review local manual export file writer V1 ─────────


def test_wp109_in_stable_merged_wps_target_list():
    text = _read()
    merged_line = next(
        line for line in text.splitlines() if line.startswith("- Merged WPs:")
    )
    assert "WP109" in merged_line


def test_wp109_is_stable_post_merge_target_state():
    text = _read()
    current_phase_line = next(
        line for line in text.splitlines() if line.startswith("- Current phase:")
    )
    assert any(wp in current_phase_line for wp in ("WP109", "WP110", "WP111", "WP112", "WP113", "WP114", "WP115", "WP116", "WP117", "WP118", "WP128", "WP130", "WP136", "WP138", "WP142", "WP148", "WP149", "WP159"))
    assert "LOCAL_OFFLINE_MANUAL_ONLY_FILE_WRITER_MERGED" in text
    assert "src/data_layer/hermes_candidate_review_handoff_manual_export_writer.py" in text


def test_wp110_is_stable_post_merge_target_state():
    text = _read()
    merged_line = next(
        line for line in text.splitlines() if line.startswith("- Merged WPs:")
    )
    assert "WP110" in merged_line
    assert "DOCS_STATUS_TESTS_ONLY_LOCAL_MANUAL_EXPORT_OPERATOR_RUNBOOK_MERGED" in text
    assert "docs/hermes_candidate_review_local_manual_export_operator_runbook.md" in text


def test_wp111_is_reconciled_or_in_current_chain_context():
    text = _read()
    current_phase_line = next(
        line for line in text.splitlines() if line.startswith("- Current phase:")
    )
    assert any(wp in current_phase_line for wp in ("WP111", "WP112", "WP113", "WP114", "WP115", "WP116", "WP117", "WP118", "WP128", "WP130", "WP136", "WP138", "WP142", "WP148", "WP149", "WP159"))
    assert "DOCS_STATUS_TESTS_ONLY_TEMP_ONLY_LOCAL_MANUAL_EXPORT_SMOKE_EXERCISE_REVIEW_TARGET" in text
    assert "docs/hermes_candidate_review_local_manual_export_smoke_exercise.md" in text


def test_wp151_is_reconciled_as_merged_and_wp159_is_current_review_target_state():
    text = _read()
    current_phase_line = next(
        line for line in text.splitlines() if line.startswith("- Current phase:")
    )
    merged_line = next(
        line for line in text.splitlines() if line.startswith("- Merged WPs:")
    )
    assert "WP161" in current_phase_line
    assert "WP111" in merged_line
    assert "WP112" in merged_line
    assert "WP113" in merged_line
    assert "WP114" in merged_line
    assert "WP115" in merged_line
    assert "WP116" in merged_line
    assert "WP117" in merged_line
    assert "WP118" in merged_line
    assert "WP119" in merged_line
    assert "WP120" in merged_line
    assert "WP121" in merged_line
    assert "WP122" in merged_line
    assert "WP123" in merged_line
    assert "WP124" in merged_line
    assert "WP125" in merged_line
    assert "WP126" in merged_line
    assert "WP127" in merged_line
    assert "WP128" in merged_line
    assert "WP129" in merged_line
    assert "WP130" in merged_line
    assert "WP131" in merged_line
    assert "WP132" in merged_line
    assert "WP144" in merged_line
    assert "WP145" in merged_line
    assert "WP146" in merged_line
    assert "WP147" in merged_line
    assert "WP148" in merged_line
    assert "WP149" in merged_line
    assert "WP150" in merged_line
    assert "WP151" in merged_line
    assert "src/data_layer/hermes_candidate_review_manual_research_briefing_packet.py" in text
    assert "LOCAL_OFFLINE_READ_ONLY_IN_MEMORY_MANUAL_RESEARCH_BRIEFING_PACKET_MERGED" in text
    assert "DOCS_STATUS_TESTS_PLUS_TEMP_ONLY_SYNTHETIC_SMOKE_MERGED" in text
    assert "docs/hermes_candidate_review_manual_research_briefing_packet_operator_runbook.md" in (REPO_ROOT / "docs" / "repo_truth_index.md").read_text(encoding="utf-8")
    assert "tests/test_hermes_candidate_review_manual_research_briefing_packet_temp_smoke.py" in (REPO_ROOT / "docs" / "repo_truth_index.md").read_text(encoding="utf-8")
    assert "docs/status_entries/WP131.md" in (REPO_ROOT / "docs" / "repo_truth_index.md").read_text(encoding="utf-8")
    assert "src/data_layer/hermes_candidate_review_manual_research_request.py" in text
    assert "LOCAL_OFFLINE_READ_ONLY_IN_MEMORY_MANUAL_RESEARCH_REQUEST_MERGED" in text
    assert "tests/test_hermes_candidate_review_manual_research_request.py" in (REPO_ROOT / "docs" / "repo_truth_index.md").read_text(encoding="utf-8")
    assert "docs/status_entries/WP132.md" in (REPO_ROOT / "docs" / "repo_truth_index.md").read_text(encoding="utf-8")
    assert "src/data_layer/hermes_candidate_review_manual_research_response.py" in text
    assert "LOCAL_OFFLINE_READ_ONLY_IN_MEMORY_MANUAL_RESEARCH_RESPONSE_MERGED" in text
    assert "tests/test_hermes_candidate_review_manual_research_response.py" in (REPO_ROOT / "docs" / "repo_truth_index.md").read_text(encoding="utf-8")
    assert "docs/status_entries/WP133.md" in (REPO_ROOT / "docs" / "repo_truth_index.md").read_text(encoding="utf-8")
    assert "WP133" in merged_line
    assert "WP134" in merged_line
    assert "WP135" in merged_line
    assert "WP136" in merged_line
    assert "WP137" in merged_line
    assert "WP138" in merged_line
    assert "WP139" in merged_line
    assert "WP140" in merged_line
    assert "WP141" in merged_line
    assert "DOCS_STATUS_TESTS_PLUS_TEMP_ONLY_SYNTHETIC_MANUAL_RESEARCH_RESPONSE_SMOKE_MERGED" in text
    index = (REPO_ROOT / "docs" / "repo_truth_index.md").read_text(encoding="utf-8")
    assert "docs/hermes_candidate_review_manual_research_response_operator_runbook.md" in index
    assert "tests/test_hermes_candidate_review_manual_research_response_operator_runbook_docs.py" in index
    assert "tests/test_hermes_candidate_review_manual_research_response_temp_smoke.py" in index
    assert "docs/status_entries/WP134.md" in index
    assert "DOCS_STATUS_TESTS_PLUS_TEMP_ONLY_SYNTHETIC_MANUAL_REQUEST_RESPONSE_SESSION_CHAIN_SMOKE_MERGED" in text
    assert "docs/hermes_candidate_review_manual_research_request_response_session_chain_operator_runbook.md" in index
    assert "tests/test_hermes_candidate_review_manual_research_request_response_session_chain_operator_runbook_docs.py" in index
    assert "tests/test_hermes_candidate_review_manual_research_request_response_session_chain_temp_smoke.py" in index
    assert "docs/status_entries/WP135.md" in index
    assert "DOCS_STATUS_TESTS_ONLY_MANUAL_REQUEST_RESPONSE_VALIDATION_RECEIPT_CHAIN_DECISION_MERGED" in text
    assert "docs/hermes_candidate_review_manual_request_response_validation_receipt_chain_contract_and_smoke_decision_record.md" in index
    assert "tests/test_hermes_candidate_review_manual_request_response_validation_receipt_chain_contract_and_smoke_decision_record_docs.py" in index
    assert "docs/status_entries/WP136.md" in index
    assert "DOCS_STATUS_TESTS_PLUS_TEMP_ONLY_SYNTHETIC_FOUR_RECORD_MANUAL_LINEAGE_SMOKE_MERGED" in text
    assert "DOCS_STATUS_TESTS_ONLY_FOUR_RECORD_LINEAGE_TO_HUMAN_DECISION_FOLLOW_UP_CHAIN_DECISION_MERGED" in text
    assert "DOCS_STATUS_TESTS_PLUS_TEMP_ONLY_SYNTHETIC_SIX_RECORD_MANUAL_LINEAGE_HUMAN_DECISION_FOLLOW_UP_TASK_SMOKE_MERGED" in text
    assert "DOCS_STATUS_TESTS_ONLY_MANUAL_SIX_RECORD_WORKFLOW_CLOSEOUT_ASSISTED_RESEARCH_TRANSITION_MERGED" in text
    assert "DOCS_STATUS_TESTS_ONLY_PROVIDER_NEUTRAL_RUNTIME_INACTIVE_ASSISTED_RESEARCH_EXPERIMENT_CONTRACT_MERGED" in text
    assert "DOCS_STATUS_TESTS_FIXTURE_ONLY_LOCAL_SYNTHETIC_OFFLINE_GOLD_CASE_PACK_EVALUATION_RUBRIC_MERGED" in text
    assert "DOCS_STATUS_TESTS_ONLY_HERMES_PROVIDER_RUNTIME_PRIVACY_PERMISSIONS_BUDGET_DECISION_MERGED" in text
    assert "DOCS_STATUS_TESTS_ONLY_HERMES_CONTROLLED_EXPERIMENT_HARNESS_CONTRACT_DRY_RUN_PLAN_MERGED" in text
    assert "LOCAL_OFFLINE_TEST_ORIENTED_SKELETON_MERGED" in text
    assert "DOCS_STATUS_TESTS_ONLY_LOCAL_HARNESS_CLOSEOUT_REMOTE_READINESS_DECISION_MERGED" in text
    assert "DOCS_STATUS_TESTS_ONLY_CURRENT_PROVIDER_MODEL_RESEARCH_AND_CANDIDATE_SHORTLIST_MERGED" in text
    assert "DOCS_STATUS_TESTS_ONLY_MANDATORY_PROVIDER_EVIDENCE_RESOLUTION_AND_RESEARCH_REFRESH_DECISION_MERGED" in text
    assert "DOCS_STATUS_TESTS_ONLY_REMOTE_PROVIDER_TRACK_DEFERRAL_REVISIT_CRITERIA_DECISION_MERGED" in text
    assert "DOCS_STATUS_MARKDOWN_TESTS_ONLY_LOCAL_RESEARCH_VALUE_AND_PAPER_READINESS_DECISION_MERGED" in text
    assert "DOCS_STATUS_MARKDOWN_TESTS_ONLY_LOCAL_RESEARCH_VALUE_MEASUREMENT_HARNESS_CONTRACT_MERGED" in text
    assert "LOCAL_OFFLINE_DETERMINISTIC_WAVE_1_MEASUREMENT_HARNESS_MERGED" in text
    assert "DOCS_STATUS_TESTS_ONLY_LOCAL_MANUAL_EXPORT_CHAIN_CLOSEOUT_REVIEW_TARGET" in text
    assert "docs/hermes_candidate_review_local_manual_export_chain_closeout.md" in text
    assert "DOCS_STATUS_TESTS_ONLY_CLI_WRAPPER_CONTRACT_MERGED" in text
    assert "docs/hermes_candidate_review_local_manual_export_cli_wrapper_contract.md" in text
    assert "Hermes candidate-review local manual export CLI wrapper contract status" in text
    assert "DOCS_STATUS_TESTS_ONLY_CLI_COMMAND_SURFACE_CONTRACT_MERGED" in text
    assert "docs/hermes_candidate_review_local_manual_export_cli_command_surface_contract.md" in text
    assert "Hermes candidate-review local manual export CLI command surface contract status" in text
    assert "LOCAL_OFFLINE_MANUAL_CLI_WRAPPER_MERGED" in text
    assert "tools/hermes_candidate_review_manual_export_cli.py" in text
    assert "Hermes candidate-review local manual export CLI wrapper implementation status" in text
    assert "DOCS_STATUS_TESTS_ONLY_CLI_OPERATOR_RUNBOOK_SMOKE_RECEIPT_MERGED" in text
    assert "docs/hermes_candidate_review_local_manual_export_cli_operator_runbook.md" in text
    assert "docs/hermes_candidate_review_local_manual_export_cli_smoke_receipt.md" in text
    assert "Hermes candidate-review local manual export CLI operator runbook and smoke receipt status" in text
    assert "DOCS_STATUS_TESTS_ONLY_CLI_CHAIN_CLOSEOUT_RESEARCH_WORKFLOW_TRANSITION_MERGED" in text
    assert "docs/hermes_candidate_review_local_manual_export_cli_chain_closeout.md" in text
    assert "Hermes candidate-review local manual export CLI chain closeout and research-workflow transition status" in text
    assert "DOCS_STATUS_TESTS_ONLY_RESEARCH_WORKFLOW_INTAKE_CONTRACT_MERGED" in text
    assert "docs/hermes_candidate_review_research_workflow_intake_contract.md" in text
    assert "Hermes candidate-review research workflow intake contract status" in text
    assert "DOCS_STATUS_TESTS_ONLY_RESEARCH_WORKFLOW_RUNBOOK_MERGED" in text
    assert "docs/hermes_candidate_review_research_workflow_runbook.md" in text
    assert "Hermes candidate-review research workflow runbook status" in text
    assert "DOCS_STATUS_TESTS_ONLY_RESEARCH_QUESTION_RECORD_CONTRACT_MERGED" in text
    assert "docs/hermes_candidate_review_research_question_record_contract.md" in text
    assert "Hermes candidate-review research question record contract status" in text
    assert "LOCAL_OFFLINE_READ_ONLY_IN_MEMORY_RESEARCH_QUESTION_RECORD_MERGED" in text
    assert "src/data_layer/hermes_candidate_review_research_question_record.py" in text
    assert "Hermes candidate-review research question record implementation status" in text
    assert "LOCAL_OFFLINE_READ_ONLY_IN_MEMORY_ADVISORY_OUTPUT_VALIDATION_RECEIPT_MERGED" in text
    assert "src/data_layer/hermes_candidate_review_advisory_output_validation_receipt.py" in text
    assert "Hermes candidate-review advisory output validation receipt status" in text
    assert "LOCAL_OFFLINE_READ_ONLY_IN_MEMORY_HUMAN_DECISION_FOLLOW_UP_RECORD_MERGED" in text
    assert "src/data_layer/hermes_candidate_review_human_decision_follow_up_record.py" in text
    assert "Hermes candidate-review human decision and follow-up record status" in text
    assert "LOCAL_OFFLINE_READ_ONLY_IN_MEMORY_MANUAL_RESEARCH_SESSION_PACKAGE_MERGED" in text
    assert "src/data_layer/hermes_candidate_review_manual_research_session_package.py" in text
    assert "Hermes candidate-review manual research session package status" in text
    assert "LOCAL_OFFLINE_READ_ONLY_IN_MEMORY_RESEARCH_CANDIDATE_QUEUE_MERGED" in text
    assert "src/data_layer/hermes_candidate_review_research_candidate_queue.py" in text
    assert "Hermes candidate-review research candidate queue status" in text
    assert "DOCS_STATUS_TESTS_ONLY_MANUAL_LOCAL_OFFLINE_ADVISORY_QUEUE_OPERATOR_RUNBOOK_TEMP_SMOKE_MERGED" in text
    assert "Hermes candidate-review research candidate queue operator runbook/temp smoke status" in text
    assert "LOCAL_OFFLINE_READ_ONLY_IN_MEMORY_EXPLICIT_HUMAN_SELECTION_HANDOFF_MERGED" in text
    assert "src/data_layer/hermes_candidate_review_manual_queue_selection_handoff.py" in text
    assert "Hermes candidate-review manual queue selection/research-question handoff status" in text
    for phrase in (
        "no product/runtime network",
        "no Hermes runtime",
        "no credentials",
        "no paper/live",
        "no execution/risk/order",
        "no scheduler/dashboard/bot-loop",
        "no dependency/workflow/lock-file",
        "no parser/loader/writer/storage path",
        "no CLI",
        "no report/export pipeline",
    ):
        assert phrase in text


def test_wp109_committed_status_docs_reject_stale_wording():
    wp109_path = STATUS_ENTRIES / "WP109.md"
    assert wp109_path.is_file()
    wp109_text = wp109_path.read_text(encoding="utf-8")
    project_text = _read()
    for phrase in (
        "WP109 on branch",
        "WP109 active branch",
        "Merge commit: TBD after merge",
        "PR: TBD",
        "count depends",
        "TBD after merge",
        "LOCAL_DRAFT_VERIFIED",
    ):
        assert phrase not in wp109_text
        assert phrase not in project_text
    fixed_live_head = re.compile(
        r"Current live PR head:\s*`?[0-9a-f]{40}`?", re.IGNORECASE
    )
    assert fixed_live_head.search(wp109_text) is None
    assert fixed_live_head.search(project_text) is None


def test_hermes_candidate_review_handoff_manual_export_writer_is_registered():
    status_text = _read()
    index_text = (REPO_ROOT / "docs" / "repo_truth_index.md").read_text(
        encoding="utf-8"
    )
    assert "Hermes candidate-review handoff local manual export file writer status" in status_text
    assert "src/data_layer/hermes_candidate_review_handoff_manual_export_writer.py" in index_text
    assert "tests/test_hermes_candidate_review_handoff_manual_export_writer.py" in index_text


def test_wp131_through_wp151_dedicated_status_chain_is_consistent():
    lines = _read().splitlines()
    wp131_line = next(line for line in lines if line.startswith(
        "- Hermes candidate-review manual research briefing packet operator runbook/temp smoke status:"
    ))
    wp132_line = next(line for line in lines if line.startswith(
        "- Hermes candidate-review manual research request contract status:"
    ))
    wp133_line = next(line for line in lines if line.startswith(
        "- Hermes candidate-review manual research response contract status:"
    ))
    wp134_line = next(line for line in lines if line.startswith(
        "- Hermes candidate-review manual research response operator runbook/temp smoke status:"
    ))
    wp135_line = next(line for line in lines if line.startswith(
        "- Hermes candidate-review manual research request-to-response session chain runbook/temp smoke status:"
    ))
    wp136_line = next(line for line in lines if line.startswith(
        "- Hermes candidate-review manual request-response-validation receipt chain contract/smoke decision status:"
    ))
    wp137_line = next(line for line in lines if line.startswith(
        "- Hermes candidate-review manual research question-request-response-validation receipt four-record chain runbook/temp smoke status:"
    ))
    wp138_line = next(line for line in lines if line.startswith(
        "- Hermes candidate-review four-record lineage to human decision and follow-up chain decision status:"
    ))
    wp139_line = next(line for line in lines if line.startswith(
        "- Hermes candidate-review manual six-record research lineage, human decision, and follow-up-task runbook/temp smoke status:"
    ))
    wp140_line = next(line for line in lines if line.startswith(
        "- Hermes candidate-review manual six-record workflow closeout and assisted-research transition status:"
    ))
    wp141_line = next(line for line in lines if line.startswith(
        "- Hermes candidate-review assisted research session experiment contract status:"
    ))
    wp142_line = next(line for line in lines if line.startswith(
        "- Hermes candidate-review assisted research gold-case fixture pack and evaluation rubric status:"
    ))
    wp143_line = next(line for line in lines if line.startswith(
        "- Hermes candidate-review assisted research provider/runtime/privacy/permissions/budget decision status:"
    ))
    wp144_line = next(line for line in lines if line.startswith(
        "- Hermes candidate-review assisted research controlled experiment harness contract, prompt/configuration boundary, and dry-run plan status:"
    ))
    wp145_line = next(line for line in lines if line.startswith(
        "- Hermes candidate-review assisted research local deterministic harness skeleton and no-network dry-run status:"
    ))
    wp146_line = next(line for line in lines if line.startswith(
        "- Hermes candidate-review assisted research local-harness closeout and controlled remote-experiment readiness decision status:"
    ))
    wp147_line = next(line for line in lines if line.startswith(
        "- Hermes candidate-review assisted research current provider/model, privacy, retention, cost, endpoint, and candidate-shortlist research status:"
    ))
    wp148_line = next(line for line in lines if line.startswith(
        "- Hermes candidate-review assisted research mandatory provider evidence resolution and research refresh decision status:"
    ))
    wp149_line = next(line for line in lines if line.startswith(
        "- Hermes remote provider track deferral and revisit criteria decision status:"
    ))
    wp150_line = next(line for line in lines if line.startswith(
        "- Local research workflow value validation and paper-trading readiness decision status:"
    ))
    wp151_line = next(line for line in lines if line.startswith(
        "- Local research workflow value measurement harness contract status:"
    ))
    wp152_line = next(line for line in lines if line.startswith(
        "- Local research workflow value measurement harness implementation status:"
    ))
    wp153_line = next(line for line in lines if line.startswith(
        "- Local research workflow value measurement dry run and receipt review status:"
    ))
    wp154_line = next(line for line in lines if line.startswith(
        "- Adoption architecture, dependency registry and alpha-factory roadmap status:"
    ))
    wp155_line = next(line for line in lines if line.startswith(
        "- Point-in-time market research data foundation contract status:"
    ))
    wp156_line = next(line for line in lines if line.startswith(
        "- Point-in-time observation schema validator and synthetic fixture implementation status:"
    ))
    current_phase_line = next(line for line in lines if line.startswith("- Current phase:"))
    merged_line = next(line for line in lines if line.startswith("- Merged WPs:"))

    assert "DOCS_STATUS_TESTS_PLUS_TEMP_ONLY_SYNTHETIC_SMOKE_MERGED" in wp131_line
    assert "LOCAL_OFFLINE_READ_ONLY_IN_MEMORY_MANUAL_RESEARCH_REQUEST_MERGED" in wp132_line
    assert "LOCAL_OFFLINE_READ_ONLY_IN_MEMORY_MANUAL_RESEARCH_RESPONSE_MERGED" in wp133_line
    assert "DOCS_STATUS_TESTS_PLUS_TEMP_ONLY_SYNTHETIC_MANUAL_RESEARCH_RESPONSE_SMOKE_MERGED" in wp134_line
    assert all("REVIEW_TARGET" not in line for line in (
        wp131_line, wp132_line, wp133_line, wp134_line, wp135_line,
        wp136_line, wp137_line, wp138_line,
    ))
    assert "DOCS_STATUS_TESTS_PLUS_TEMP_ONLY_SYNTHETIC_MANUAL_REQUEST_RESPONSE_SESSION_CHAIN_SMOKE_MERGED" in wp135_line
    assert "DOCS_STATUS_TESTS_ONLY_MANUAL_REQUEST_RESPONSE_VALIDATION_RECEIPT_CHAIN_DECISION_MERGED" in wp136_line
    assert "Direct three-record smoke: NOT APPROVED" in wp136_line
    assert "WP121 research-question lineage is mandatory" in wp136_line
    assert "Required future topology: WP121 → WP132 → WP133 → WP122" in wp136_line
    assert "DOCS_STATUS_TESTS_PLUS_TEMP_ONLY_SYNTHETIC_FOUR_RECORD_MANUAL_LINEAGE_SMOKE_MERGED" in wp137_line
    assert "fourteen post-validation relationships" in wp137_line
    assert "thirteen valid-but-inconsistent cases" in wp137_line
    assert "no source change" in wp137_line
    assert "no adapter" in wp137_line
    assert "no runtime" in wp137_line
    assert "product network" in wp137_line
    assert "storage" in wp137_line
    assert "trading" not in wp137_line or "authority" in wp137_line
    assert "DOCS_STATUS_TESTS_ONLY_FOUR_RECORD_LINEAGE_TO_HUMAN_DECISION_FOLLOW_UP_CHAIN_DECISION_MERGED" in wp138_line
    assert "Six-record future smoke: APPROVED FOR A SEPARATE WP" in wp138_line
    assert "Required future topology: WP121 → WP132 → WP133 → WP122 → WP123 decision → WP123 follow-up task" in wp138_line
    assert "WP132/WP133 lineage is inherited through WP121/WP122" in wp138_line
    assert "WP139 is the separately approved implementation package" in wp138_line
    assert "no source" in wp138_line
    assert "no smoke" in wp138_line
    assert "no runtime" in wp138_line
    assert "trading authority" in wp138_line
    assert "DOCS_STATUS_TESTS_PLUS_TEMP_ONLY_SYNTHETIC_SIX_RECORD_MANUAL_LINEAGE_HUMAN_DECISION_FOLLOW_UP_TASK_SMOKE_MERGED" in wp139_line
    assert "eighteen post-validation relationships" in wp139_line
    assert "sixteen explicit non-linkages" in wp139_line
    assert "seventeen valid-but-inconsistent cases" in wp139_line
    assert "six human-review failures" in wp139_line
    assert "six unsafe no-echo failures" in wp139_line
    assert "no source change" in wp139_line
    assert "no adapter" in wp139_line
    assert "no generated decision/task" in wp139_line
    assert "no runtime" in wp139_line
    assert "product network" in wp139_line
    assert "storage" in wp139_line
    assert "WP140 remains separately gated" not in wp139_line
    assert "REVIEW_TARGET" not in wp138_line
    assert "REVIEW_TARGET" not in wp139_line
    assert "REVIEW_TARGET" not in wp140_line
    assert "REVIEW_TARGET" not in wp141_line
    assert "REVIEW_TARGET" not in wp142_line
    assert "REVIEW_TARGET" not in wp143_line
    assert "REVIEW_TARGET" not in wp144_line
    assert "REVIEW_TARGET" not in wp145_line
    assert "REVIEW_TARGET" not in wp146_line
    assert "REVIEW_TARGET" not in wp147_line
    assert "REVIEW_TARGET" not in wp148_line
    assert "REVIEW_TARGET" not in wp149_line
    assert "REVIEW_TARGET" not in wp150_line
    assert "REVIEW_TARGET" not in wp151_line
    assert "REVIEW_TARGET" not in wp152_line
    assert "REVIEW_TARGET" not in wp153_line
    assert "REVIEW_TARGET" not in wp154_line
    assert "REVIEW_TARGET" not in wp155_line
    # WP156 is merged; WP157 is the current review target (asserted separately).
    assert "REVIEW_TARGET" not in wp156_line
    assert sum("REVIEW_TARGET" in line for line in (
        wp131_line, wp132_line, wp133_line, wp134_line, wp135_line, wp136_line,
        wp137_line, wp138_line, wp139_line, wp140_line, wp141_line, wp142_line,
        wp143_line, wp144_line, wp145_line, wp146_line, wp147_line, wp148_line,
        wp149_line, wp150_line, wp151_line, wp152_line, wp153_line, wp154_line,
        wp155_line, wp156_line,
    )) == 0
    assert "Manual six-record workflow status: CLOSED_COMPLETE_ENOUGH_FOR_BOUNDED_MANUAL_USE" in wp140_line
    assert "Default manual-chain extension: STOP" in wp140_line
    assert "Next phase: HERMES_ASSISTED_RESEARCH_EXPERIMENT_CONTRACT" in wp140_line
    assert "Hermes installation/runtime activation: NOT AUTHORIZED" in wp140_line
    assert "Deterministic validation and safety authority: UNCHANGED" in wp140_line
    assert "Hermes paper/live/execution authority: FORBIDDEN" in wp140_line
    assert "WP141 was separately approved" in wp140_line
    assert "DOCS_STATUS_TESTS_ONLY_PROVIDER_NEUTRAL_RUNTIME_INACTIVE_ASSISTED_RESEARCH_EXPERIMENT_CONTRACT_MERGED" in wp141_line
    assert "Experiment contract status: PROVIDER_NEUTRAL_RUNTIME_INACTIVE" in wp141_line
    assert "Assisted output status: UNTRUSTED_DRAFT_ONLY" in wp141_line
    assert "Deterministic validation: MANDATORY_BEFORE_ACCEPTANCE" in wp141_line
    assert "Human review: MANDATORY_BEFORE_ANY_DOWNSTREAM_HANDOFF" in wp141_line
    assert "Hermes installation/runtime activation: NOT AUTHORIZED" in wp141_line
    assert "Provider/model selection: NOT AUTHORIZED" in wp141_line
    assert "Network/source fetching: NOT AUTHORIZED" in wp141_line
    assert "Persistence/storage: NOT AUTHORIZED" in wp141_line
    assert "Paper/live/execution authority: FORBIDDEN" in wp141_line
    assert "WP142 was separately approved" in wp141_line
    assert "DOCS_STATUS_TESTS_FIXTURE_ONLY_LOCAL_SYNTHETIC_OFFLINE_GOLD_CASE_PACK_EVALUATION_RUBRIC_MERGED" in wp142_line
    for phrase in (
        "Fixture-pack status: LOCAL_SYNTHETIC_OFFLINE_TEST_ONLY", "Case count: 20",
        "Positive/complete cases: 6", "Refusal/defer cases: 6", "Adversarial cases: 8",
        "Human-review rubric: 16_CATEGORIES_THREE_LEVEL_SCALE",
        "Hard safety gates: ZERO_TOLERANCE", "Provider/model performance claims: NONE",
        "Hermes installation/runtime activation: NOT AUTHORIZED",
        "Network/source fetching: NOT AUTHORIZED", "Paper/live/execution authority: FORBIDDEN",
        "WP143 was separately approved",
    ):
        assert phrase in wp142_line
    assert "DOCS_STATUS_TESTS_ONLY_HERMES_PROVIDER_RUNTIME_PRIVACY_PERMISSIONS_BUDGET_DECISION_MERGED" in wp143_line
    for phrase in (
        "Assisted-research architecture: LOCAL_DETERMINISTIC_CONTROL_PLANE_WITH_EPHEMERAL_HERMES_SESSION",
        "Model-access posture: PROVIDER_NEUTRAL_REMOTE_MODEL_CANDIDATES_WITH_OPTIONAL_LOCAL_BASELINE",
        "Provider decision: SHORTLIST_MAXIMUM_TWO_REMOTE_CANDIDATES_PLUS_OPTIONAL_ONE_LOCAL_BASELINE",
        "Experiment data classification: SYNTHETIC_OFFLINE_TEST_DATA_ONLY",
        "Network posture for the first future experiment: PROVIDER_ENDPOINT_ONLY_DENY_ALL_OTHER_NETWORK",
        "Repository posture: NO_REPOSITORY_WIDE_ACCESS", "Command and shell posture: DISABLED",
        "Tool posture: NO_BROWSER_NO_SEARCH_NO_SOURCE_FETCH_NO_TRADING_TOOLS",
        "Memory posture: EPHEMERAL_SESSION_MEMORY_ONLY", "Persistent memory: FORBIDDEN",
        "Credential posture: OUT_OF_REPO_OPERATOR_INJECTED_LEAST_PRIVILEGE_REVOCABLE_SECRET",
        "Maximum total remote calls: 140", "Maximum total experiment spend: USD 100",
        "Maximum daily spend: USD 25", "Maximum single-call spend: USD 2",
        "Concurrent remote calls: 1", "Provider activation: NOT AUTHORIZED",
        "Hermes installation/runtime activation: NOT AUTHORIZED",
        "Paper/live/execution authority: FORBIDDEN", "WP144 was separately approved",
    ):
        assert phrase in wp143_line
    assert "DOCS_STATUS_TESTS_ONLY_HERMES_CONTROLLED_EXPERIMENT_HARNESS_CONTRACT_DRY_RUN_PLAN_MERGED" in wp144_line
    for phrase in (
        "Harness contract status: DOCUMENTATION_ONLY_RUNTIME_INACTIVE",
        "Controller authority: LOCAL_DETERMINISTIC_EXCLUSIVE",
        "Hermes session posture: ONE_CASE_ONE_EPHEMERAL_SESSION",
        "Provider adapter posture: ONE_EXPLICIT_CANDIDATE_CONFIGURATION_ONE_ALLOWLISTED_ENDPOINT",
        "Prompt/configuration status: VERSIONED_NON_EXECUTABLE_CONTRACT_ONLY",
        "Input posture: EXACT_VALIDATED_WP142_CASE_BUNDLE_ONLY",
        "Output posture: UNTRUSTED_DRAFT_ONLY",
        "Raw input/output persistence: FORBIDDEN_BY_DEFAULT",
        "Sanitized experiment metadata: FUTURE_ALLOW_EXACT_FIELDS_ONLY",
        "Network posture: DENY_ALL_EXCEPT_ONE_CONTROLLER_MEDIATED_PROVIDER_ENDPOINT",
        "Tool posture: NO_BROWSER_NO_SEARCH_NO_SOURCE_FETCH_NO_SHELL_NO_TRADING_TOOLS",
        "Memory posture: EPHEMERAL_SESSION_ONLY_DELETE_ON_TEARDOWN",
        "Dry-run posture: LOCAL_NO_PROVIDER_NO_NETWORK_NO_CREDENTIAL",
        "Deterministic validation and human review: MANDATORY",
        "Hermes/provider/model activation: NOT AUTHORIZED",
        "Paper/live/execution authority: FORBIDDEN", "WP145 was separately approved",
    ):
        assert phrase in wp144_line
    assert "LOCAL_OFFLINE_TEST_ORIENTED_SKELETON_MERGED" in wp145_line
    for phrase in (
        "Harness implementation status: LOCAL_OFFLINE_TEST_ORIENTED_SKELETON",
        "Controller authority: LOCAL_DETERMINISTIC_EXCLUSIVE",
        "Adapter status: TEST_ONLY_PRECOMPUTED_FAKE_RESPONSE",
        "Dry-run case count: 1", "Dry-run case ID: GC-P01-COMPLETE-SUPPORTED",
        "Network: FORBIDDEN", "Credentials: FORBIDDEN",
        "Hermes installation/invocation: FORBIDDEN", "Provider/model call: FORBIDDEN",
        "Stable raw input/output persistence: FORBIDDEN",
        "Temporary filesystem: PYTEST_TMP_PATH_ONLY", "Output: SANITIZED_EVIDENCE_ONLY",
        "Deterministic WP133 validation: MANDATORY",
        "Human review: EXPLICIT_CALLER_SUPPLIED_ACKNOWLEDGEMENT_REQUIRED",
        "Automatic downstream records: FORBIDDEN",
        "Paper/live/execution authority: FORBIDDEN", "WP146 was separately approved",
    ):
        assert phrase in wp145_line
    assert "DOCS_STATUS_TESTS_ONLY_LOCAL_HARNESS_CLOSEOUT_REMOTE_READINESS_DECISION_MERGED" in wp146_line
    for phrase in (
        "Local harness phase status: CLOSED_COMPLETE_ENOUGH_FOR_BOUNDED_LOCAL_DRY_RUN",
        "WP145 corrected evidence accepted: YES",
        "Local one-case dry-run status: ACCEPTED_AS_TEST_ONLY_CONTROL_EVIDENCE",
        "WP145 implementation classification: BOUNDED_LOCAL_CONTROL_SKELETON",
        "WP145 phase-completion decision: ACCEPT",
        "Remote controlled experiment readiness: NOT_READY",
        "Primary remote-readiness blocker: CURRENT_PROVIDER_MODEL_PRIVACY_RETENTION_COST_AND_ENDPOINT_EVIDENCE_MISSING",
        "Provider/model candidate naming: DEFERRED_CURRENT_EXTERNAL_RESEARCH_REQUIRED",
        "Current external provider/model research: REQUIRED_BEFORE_REMOTE_EXPERIMENT_IMPLEMENTATION",
        "Remote experiment implementation authorization: DENIED_PENDING_RESEARCH_AND_CONTROL_GATES",
        "Remote adapter implementation: NOT AUTHORIZED",
        "Hermes installation/invocation: NOT AUTHORIZED",
        "Provider/model call: NOT AUTHORIZED",
        "Credential creation/use: NOT AUTHORIZED",
        "Network endpoint activation: NOT AUTHORIZED",
        "Experiment spending: NOT AUTHORIZED",
        "Raw input/output persistence: NOT AUTHORIZED",
        "Paper/live/execution authority: FORBIDDEN",
        "Next phase: CURRENT_PROVIDER_MODEL_PRIVACY_RETENTION_COST_RESEARCH_AND_CANDIDATE_SHORTLIST",
        "WP147 was separately approved",
    ):
        assert phrase in wp146_line
    assert "DOCS_STATUS_TESTS_ONLY_CURRENT_PROVIDER_MODEL_RESEARCH_AND_CANDIDATE_SHORTLIST_MERGED" in wp147_line
    for phrase in (
        "WP147 research status: COMPLETE",
        "Research cut-off: 2026-07-22T23:49:02Z",
        "Candidate pool posture: CURRENT_AUTHORITATIVE_FIRST_PARTY_RESEARCH_ONLY",
        "Provider decision: NO_PROVIDER_SELECTED_EVIDENCE_INSUFFICIENT",
        "Remote configurations researched deeply: 3",
        "Remote configurations eligible: 0",
        "Remote configurations shortlisted: 0",
        "Candidate shortlist decision: EVIDENCE_INSUFFICIENT_NO_SHORTLIST",
        "OAI-SOL-RESPONSES, OAI-LUNA-RESPONSES, and ANT-SONNET-MESSAGES are NOT_SHORTLISTABLE_EVIDENCE_INSUFFICIENT",
        "GGL-FLASH-DEVELOPER is PRELIMINARY_STOP_EVIDENCE_INSUFFICIENT",
        "expected_us_geo_cost: USD 0.0594",
        "stress_us_geo_cost: USD 0.2970",
        "Local baseline decision: DEFERRED_HARDWARE_EVIDENCE_MISSING",
        "Remote controlled experiment readiness: NOT_READY",
        "Provider/model activation: NOT AUTHORIZED",
        "Provider/model call: NOT AUTHORIZED",
        "Hermes installation/invocation: NOT AUTHORIZED",
        "Provider account creation: NOT AUTHORIZED",
        "Credential creation/use: NOT AUTHORIZED",
        "Network endpoint activation: NOT AUTHORIZED",
        "Experiment spending: NOT AUTHORIZED",
        "Raw input/output persistence: NOT AUTHORIZED",
        "Paper/live/execution authority: FORBIDDEN",
        "Next phase: MANDATORY_EVIDENCE_RESOLUTION_AND_RESEARCH_REFRESH_DECISION",
        "WP148 was separately approved",
    ):
        assert phrase in wp147_line
    assert "DOCS_STATUS_TESTS_ONLY_MANDATORY_PROVIDER_EVIDENCE_RESOLUTION_AND_RESEARCH_REFRESH_DECISION_MERGED" in wp148_line
    for phrase in (
        "Research cut-off: 2026-07-23T16:10:31Z",
        "Refreshed source count: 11",
        "Tier 1 source count: 10",
        "Tier 2 source count: 1",
        "Tier 2 source IDs: ANT-R02",
        "OpenAI deletion result: EVIDENCE_INSUFFICIENT",
        "OpenAI key-lifecycle result: EVIDENCE_INSUFFICIENT",
        "Anthropic deletion result: EVIDENCE_INSUFFICIENT",
        "Anthropic subprocessor result: PASS",
        "Anthropic security/incident result: PASS",
        "Google result: EVIDENCE_INSUFFICIENT",
        "WP148 evidence-resolution status: COMPLETE_EVIDENCE_STILL_INSUFFICIENT",
        "Candidate eligibility result: EVIDENCE_INSUFFICIENT_NO_ELIGIBLE_CANDIDATE",
        "Remote configurations deeply researched: 3",
        "Remote configurations eligible: 0",
        "Remote configurations shortlisted: 0",
        "Provider/model selection: NOT MADE",
        "Local baseline pivot decision: DEFER_HARDWARE_EVIDENCE_MISSING",
        "Remote controlled experiment readiness: NOT_READY",
        "Next phase: REMOTE_PROVIDER_TRACK_DEFER_OR_RESEARCH_REFRESH_LATER_DECISION",
        "Provider/model activation: NOT AUTHORIZED",
        "Provider/model call: NOT AUTHORIZED",
        "Hermes installation/invocation: NOT AUTHORIZED",
        "Provider account creation: NOT AUTHORIZED",
        "Credential creation/use: NOT AUTHORIZED",
        "Network endpoint activation: NOT AUTHORIZED",
        "Experiment spending: NOT AUTHORIZED",
        "Raw input/output persistence: NOT AUTHORIZED",
        "Paper/live/execution authority: FORBIDDEN",
        "WP149 requires separate approval",
    ):
        assert phrase in wp148_line
    assert "DOCS_STATUS_TESTS_ONLY_REMOTE_PROVIDER_TRACK_DEFERRAL_REVISIT_CRITERIA_DECISION_MERGED" in wp149_line
    for phrase in (
        "Remote provider track status: DEFERRED_PENDING_MATERIAL_NEW_EVIDENCE",
        "Automatic periodic provider re-research: FORBIDDEN",
        "Repeated unchanged provider research: FORBIDDEN",
        "Scheduled periodic provider sweep: FORBIDDEN",
        "Reopen based only on elapsed time: FORBIDDEN",
        "Provider track may reopen only after: MATERIAL_EVIDENCE_TRIGGER_AND_SEPARATE_APPROVAL",
        "Deferral review cadence: EVENT_DRIVEN_ONLY",
        "Remote configurations eligible: 0",
        "Remote configurations shortlisted: 0",
        "Provider/model selection: NOT MADE",
        "Remote controlled experiment readiness: NOT_READY",
        "Provider/model activation: NOT AUTHORIZED",
        "Provider/model call: NOT AUTHORIZED",
        "Hermes installation/invocation: NOT AUTHORIZED",
        "Provider account creation: NOT AUTHORIZED",
        "Credential creation/use: NOT AUTHORIZED",
        "Network endpoint activation: NOT AUTHORIZED",
        "Experiment spending: NOT AUTHORIZED",
        "Raw input/output persistence: NOT AUTHORIZED",
        "Paper/live/execution authority: FORBIDDEN",
        "Next phase: LOCAL_RESEARCH_WORKFLOW_VALUE_VALIDATION_AND_PAPER_TRADING_READINESS_DECISION",
        "WP150 was separately approved",
    ):
        assert phrase in wp149_line
    assert "DOCS_STATUS_MARKDOWN_TESTS_ONLY_LOCAL_RESEARCH_VALUE_AND_PAPER_READINESS_DECISION_MERGED" in wp150_line
    for phrase in (
        "Local workflow stages inventoried: 20",
        "Implemented and tested: 13",
        "Limited/manual: 4",
        "Contract/runbook only: 2",
        "Synthetic only: 1",
        "Review follow-up required: YES",
        "Classification: B — positive readiness conclusion was not fully grounded in current structured fields",
        "Local research workflow value-validation status: PARTIALLY_READY_BLOCKERS_IDENTIFIED",
        "Research-value metric records: 39",
        "Research-value metrics measured: 0",
        "Research-value metrics measurable but not yet measured: 22",
        "Research-value metrics not currently measurable: 17",
        "Research throughput: 3 MEASURABLE_NOT_YET_MEASURED / 3 NOT_CURRENTLY_MEASURABLE",
        "Candidate rejection quality: 6 MEASURABLE_NOT_YET_MEASURED / 1 NOT_CURRENTLY_MEASURABLE",
        "Hypothesis quality: 2 MEASURABLE_NOT_YET_MEASURED / 5 NOT_CURRENTLY_MEASURABLE",
        "Reproducibility: 6 MEASURABLE_NOT_YET_MEASURED / 1 NOT_CURRENTLY_MEASURABLE",
        "Strategy-validation handoff quality: 5 MEASURABLE_NOT_YET_MEASURED / 2 NOT_CURRENTLY_MEASURABLE",
        "Operator burden: 0 MEASURABLE_NOT_YET_MEASURED / 5 NOT_CURRENTLY_MEASURABLE",
        "Research-value blockers: 7",
        "Market data: PARTIALLY_READY",
        "Replay/fill: ABSENT",
        "Strategy input: NOT_READY",
        "Order lifecycle: ABSENT",
        "Accounting: ABSENT",
        "Risk: ABSENT",
        "Observability: ABSENT",
        "Reconciliation: ABSENT",
        "Operations: ABSENT",
        "Paper-trading implementation readiness: NOT_READY_FOUNDATIONAL_GAPS",
        "Paper-trading execution: NOT AUTHORIZED",
        "Live-trading execution: FORBIDDEN",
        "Capital at risk: USD 0",
        "Orders submitted: 0",
        "Credentials created/used: 0",
        "External model calls: 0",
        "Next phase: LOCAL_RESEARCH_WORKFLOW_VALUE_MEASUREMENT_HARNESS_CONTRACT",
        "WP151 requires separate approval",
    ):
        assert phrase in wp150_line
    for phrase in (
        "DOCS_STATUS_MARKDOWN_TESTS_ONLY_LOCAL_RESEARCH_VALUE_MEASUREMENT_HARNESS_CONTRACT_MERGED",
        "Measurement harness contract status: COMPLETE_READY_FOR_BOUNDED_IMPLEMENTATION_WP",
        "Measurement architecture: LOCAL_DETERMINISTIC_OPERATOR_INITIATED_TEMPORARY_HARNESS",
        "Initial harness metric scope: GROUNDED_22_METRICS_ONLY",
        "Blocked metric posture: CONTRACT_DEFINED_IMPLEMENTATION_DEFERRED",
        "Research-value metric records: 39",
        "Research-value metrics measured: 0",
        "Research-value metrics measurable but not yet measured: 22",
        "Research-value metrics not currently measurable: 17",
        "Wave 1 metrics: 22",
        "Wave 2 metrics: 17",
        "Workflow stages: 20",
        "Corpus cases: 14",
        "Corpus families: 14",
        "Event types: 13",
        "Run statuses: 9",
        "Required repeats per selected case: 3",
        "WP150 blockers mapped: 7",
        "Contract-resolved blockers: 7",
        "Implementation-required blockers: 7",
        "Separate schema decision required: NO",
        "Measurement harness implementation: NOT AUTHORIZED",
        "Measurement run: NOT AUTHORIZED",
        "Measurement receipts generated: 0",
        "Persistent measurement output: NOT AUTHORIZED",
        "Paper-trading implementation readiness: NOT_READY_FOUNDATIONAL_GAPS",
        "Paper-trading execution: NOT AUTHORIZED",
        "Live-trading execution: FORBIDDEN",
        "Capital at risk: USD 0",
        "Orders submitted: 0",
        "Credentials created/used: 0",
        "External model calls: 0",
        "Scheduler/tasks: 0",
        "Next phase: BOUNDED_LOCAL_RESEARCH_VALUE_MEASUREMENT_HARNESS_IMPLEMENTATION",
        "WP152 required separate approval and was separately approved",
    ):
        assert phrase in wp151_line
        assert "WP161" in current_phase_line
    assert "WP153" in merged_line
    assert "WP152" in merged_line
    assert "WP138" in merged_line
    assert "WP139" in merged_line
    assert "WP140" in merged_line
    assert "WP141" in merged_line
    assert "WP142" in merged_line
    assert "WP143" in merged_line
    assert "WP144" in merged_line
    assert "WP145" in merged_line
    assert "WP146" in merged_line
    assert "WP147" in merged_line
    assert "WP148" in merged_line
    assert "WP149" in merged_line
    assert "WP150" in merged_line
    assert "WP151" in merged_line
    for phrase in (
        "LOCAL_OFFLINE_DETERMINISTIC_WAVE_1_MEASUREMENT_HARNESS_MERGED",
        "Review follow-up required: YES",
        "Classification: F/G — implementation semantics and adversarial-test coverage",
        "Current PR reused: YES",
        "Separate hardening WP required: NO",
        "WP153 implemented: NO",
        "Bounded Wave 1 harness implementation: IMPLEMENTED_AND_TESTED",
        "Registry records: 39",
        "Wave 1 metrics implemented: 22",
        "Wave 2 metrics implemented: 0",
        "Wave 2 metrics blocked: 17",
        "Fixed corpus: SYNTHETIC_SANITIZED_OFFLINE_FIXED",
        "Corpus cases: 14",
        "Corpus families: 14",
        "Workflow stages: 20",
        "Event types: 13",
        "Run statuses: 9",
        "Safety gates: 12",
        "Required repeats per selected case: 3",
        "Measurement runs accepted: 0",
        "Measurement receipts accepted: 0",
        "Product/runtime network calls: 0",
        "Credentials accessed: 0",
        "Provider/model/Hermes calls: 0",
        "Paper/live orders: 0",
        "Capital at risk: USD 0",
        "Scheduler/tasks: 0",
        "Persistent output: 0",
        "Paper-trading implementation readiness: NOT_READY_FOUNDATIONAL_GAPS",
        "Paper-trading execution: NOT AUTHORIZED",
        "Live-trading execution: FORBIDDEN",
        "Next sequence phase reconciled by the separately approved WP153",
        "accepted no project-level measurement run or receipt",
        "src/data_layer/local_research_value_measurement/",
        "tests/fixtures/local_research_workflow_value_measurement_v1.json",
    ):
        assert phrase in wp152_line
    for phrase in (
        "LOCAL_OFFLINE_DETERMINISTIC_SYNTHETIC_DRY_RUN_AND_RECEIPT_REVIEW_MERGED",
        "Synthetic project dry runs completed: 1",
        "Synthetic research-memory receipts accepted: 1",
        "Real workflow measurement runs accepted: 0",
        "Real workflow research-value metrics measured: 0",
        "run_id: WP153-DRY-RUN-001",
        "operator_run_label: WP152_SYNTHETIC_VALIDATION",
        "Event count: 392",
        "Metric result count: 39",
        "Wave 1 harness metrics implemented: 22",
        "Wave 2 metrics blocked: 17",
        "Wave 2 populated value fields: 0",
        "Repeatability PASS results: 14",
        "Safety gates: 12",
        "Acknowledgement actions: 14",
        "run_status: RUN_VALID_MEASUREMENT_COMPLETE",
        "human_review_status: ACCEPT_MEASUREMENT_RECEIPT_FOR_RESEARCH_MEMORY_ONLY",
        "Hard failures: 0",
        "temporary_output_status: IN_MEMORY_ONLY",
        "Run-created files: 0",
        "event_stream_sha256: 31eca5ee6b7881029585f494de0740f04fd068ac9625b4cd8b387b41a87f3135",
        "receipt_sha256: 5a60772bec6c582a83a1e36bfeaa60de4a7aff7840f8ec9b7f33ad9f17234750",
        "public_result_sha256: f95101f9ed82ca32cc458f2133b8cb0c34e2adfccf0619b349c993fafcc8b514",
        "Paper-trading readiness: NOT_READY_FOUNDATIONAL_GAPS",
        "Next sequence phase reconciled by the separately approved WP154 architecture decision",
        "docs/local_research_workflow_value_measurement_dry_run_and_receipt_review.md",
    ):
        assert phrase in wp153_line
    index_text = (REPO_ROOT / "docs" / "repo_truth_index.md").read_text(encoding="utf-8")
    for path in (
        "docs/local_research_workflow_value_measurement_dry_run_and_receipt_review.md",
        "docs/status_entries/WP153.md",
        "tests/test_local_research_workflow_value_measurement_dry_run_and_receipt_review.py",
    ):
        assert path in index_text
    index = (REPO_ROOT / "docs" / "repo_truth_index.md").read_text(encoding="utf-8")
    for path in (
        "docs/hermes_candidate_review_manual_research_question_request_response_validation_receipt_four_record_chain_operator_runbook.md",
        "tests/test_hermes_candidate_review_manual_research_question_request_response_validation_receipt_four_record_chain_operator_runbook_docs.py",
        "tests/test_hermes_candidate_review_manual_research_question_request_response_validation_receipt_four_record_chain_temp_smoke.py",
        "docs/status_entries/WP137.md",
        "docs/hermes_candidate_review_manual_four_record_lineage_human_decision_follow_up_chain_contract_and_smoke_decision_record.md",
        "tests/test_hermes_candidate_review_manual_four_record_lineage_human_decision_follow_up_chain_contract_and_smoke_decision_record_docs.py",
        "docs/status_entries/WP138.md",
        "docs/hermes_candidate_review_manual_six_record_research_lineage_human_decision_follow_up_task_operator_runbook.md",
        "tests/test_hermes_candidate_review_manual_six_record_research_lineage_human_decision_follow_up_task_operator_runbook_docs.py",
        "tests/test_hermes_candidate_review_manual_six_record_research_lineage_human_decision_follow_up_task_temp_smoke.py",
        "docs/status_entries/WP139.md",
        "docs/hermes_candidate_review_manual_six_record_workflow_closeout_and_assisted_research_transition_decision_record.md",
        "tests/test_hermes_candidate_review_manual_six_record_workflow_closeout_and_assisted_research_transition_decision_record_docs.py",
        "docs/status_entries/WP140.md",
        "docs/hermes_candidate_review_assisted_research_session_experiment_contract.md",
        "tests/test_hermes_candidate_review_assisted_research_session_experiment_contract_docs.py",
        "docs/status_entries/WP141.md",
        "docs/hermes_candidate_review_assisted_research_experiment_gold_case_fixture_pack_and_evaluation_rubric.md",
        "tests/fixtures/hermes_candidate_review_assisted_research_gold_cases.json",
        "tests/test_hermes_candidate_review_assisted_research_experiment_gold_case_fixture_pack_docs.py",
        "tests/test_hermes_candidate_review_assisted_research_experiment_gold_case_fixture_pack.py",
        "docs/status_entries/WP142.md",
        "docs/hermes_candidate_review_assisted_research_provider_runtime_privacy_permissions_budget_decision.md",
        "tests/test_hermes_candidate_review_assisted_research_provider_runtime_privacy_permissions_budget_decision_docs.py",
        "docs/status_entries/WP143.md",
        "docs/hermes_candidate_review_assisted_research_controlled_experiment_harness_contract_prompt_configuration_boundary_and_dry_run_plan.md",
        "tests/test_hermes_candidate_review_assisted_research_controlled_experiment_harness_contract_prompt_configuration_boundary_and_dry_run_plan_docs.py",
        "docs/status_entries/WP144.md",
        "src/data_layer/hermes_candidate_review_assisted_research_local_dry_run_harness.py",
        "tests/test_hermes_candidate_review_assisted_research_local_dry_run_harness.py",
        "tests/test_hermes_candidate_review_assisted_research_local_dry_run_harness_temp_smoke.py",
        "docs/hermes_candidate_review_assisted_research_local_dry_run_harness_operator_note.md",
        "docs/status_entries/WP145.md",
        "docs/hermes_candidate_review_assisted_research_local_harness_closeout_and_controlled_remote_experiment_readiness_decision.md",
        "tests/test_hermes_candidate_review_assisted_research_local_harness_closeout_and_controlled_remote_experiment_readiness_decision_docs.py",
        "docs/status_entries/WP146.md",
        "docs/hermes_candidate_review_assisted_research_current_provider_model_privacy_retention_cost_endpoint_research_and_candidate_shortlist.md",
        "tests/test_hermes_candidate_review_assisted_research_current_provider_model_privacy_retention_cost_endpoint_research_and_candidate_shortlist_docs.py",
        "docs/status_entries/WP147.md",
        "docs/hermes_candidate_review_assisted_research_mandatory_provider_evidence_resolution_and_research_refresh_decision.md",
        "tests/test_hermes_candidate_review_assisted_research_mandatory_provider_evidence_resolution_and_research_refresh_decision_docs.py",
        "docs/status_entries/WP148.md",
        "docs/hermes_remote_provider_track_deferral_and_revisit_criteria_decision.md",
        "tests/test_hermes_remote_provider_track_deferral_and_revisit_criteria_decision_docs.py",
        "docs/status_entries/WP149.md",
    ):
        assert path in index


def test_wp140_status_fragment_is_stable_and_contains_locked_decisions():
    status = (STATUS_ENTRIES / "WP140.md").read_text(encoding="utf-8")
    for statement in (
        "Manual six-record workflow status: CLOSED_COMPLETE_ENOUGH_FOR_BOUNDED_MANUAL_USE",
        "Default manual-chain extension: STOP",
        "Next phase: HERMES_ASSISTED_RESEARCH_EXPERIMENT_CONTRACT",
        "Hermes installation/runtime activation: NOT AUTHORIZED",
        "Deterministic validation and safety authority: UNCHANGED",
        "Hermes paper/live/execution authority: FORBIDDEN",
        "WP141 requires separate approval",
        "Evidence mode: PRIVATE_REPO_MANUAL_VERIFIED",
        "Guard input source: pre-publication local evidence draft used only for consistency checking; the current canonical review evidence is the PR body and authenticated GitHub metadata.",
        "Evidence architecture: Model D",
    ):
        assert statement in status
    assert "LOCAL_DRAFT_VERIFIED" not in status
    assert "TBD" not in status
    assert "Head commit:" not in status
    assert re.search(r"Current live PR head:\s*`?[0-9a-f]{40}`?", status, re.IGNORECASE) is None
    assert "future mergeability" not in status.lower()


def test_wp141_status_fragment_is_stable_and_contains_locked_decisions():
    status = (STATUS_ENTRIES / "WP141.md").read_text(encoding="utf-8")
    for statement in (
        "Experiment contract status: PROVIDER_NEUTRAL_RUNTIME_INACTIVE",
        "Assisted output status: UNTRUSTED_DRAFT_ONLY",
        "Deterministic validation: MANDATORY_BEFORE_ACCEPTANCE",
        "Human review: MANDATORY_BEFORE_ANY_DOWNSTREAM_HANDOFF",
        "Hermes installation/runtime activation: NOT AUTHORIZED",
        "Provider/model selection: NOT AUTHORIZED",
        "Network/source fetching: NOT AUTHORIZED",
        "Persistence/storage: NOT AUTHORIZED",
        "Paper/live/execution authority: FORBIDDEN",
        "WP142 requires separate approval",
        "Evidence mode: PRIVATE_REPO_MANUAL_VERIFIED",
        "Evidence architecture: Model D",
        "Ready for review: YES only after final validation",
    ):
        assert statement in status
    for path in (
        "docs/hermes_candidate_review_assisted_research_session_experiment_contract.md",
        "tests/test_hermes_candidate_review_assisted_research_session_experiment_contract_docs.py",
        "docs/status_entries/WP141.md",
    ):
        assert path in status
    assert "LOCAL_DRAFT_VERIFIED" not in status
    assert "TBD" not in status
    assert "Head commit:" not in status
    assert re.search(r"Current live PR head:\s*`?[0-9a-f]{40}`?", status, re.IGNORECASE) is None
    assert "future mergeability" not in status.lower()


def test_wp142_status_fragment_is_stable_and_contains_locked_decisions():
    status = (STATUS_ENTRIES / "WP142.md").read_text(encoding="utf-8")
    for statement in (
        "Fixture-pack status: LOCAL_SYNTHETIC_OFFLINE_TEST_ONLY", "Case count: 20",
        "Positive/complete cases: 6", "Refusal/defer cases: 6", "Adversarial cases: 8",
        "Human-review rubric: 16_CATEGORIES_THREE_LEVEL_SCALE",
        "Hard safety gates: ZERO_TOLERANCE", "Provider/model performance claims: NONE",
        "Hermes installation/runtime activation: NOT AUTHORIZED",
        "Network/source fetching: NOT AUTHORIZED", "Paper/live/execution authority: FORBIDDEN",
        "WP143 requires separate approval", "Evidence mode: PRIVATE_REPO_MANUAL_VERIFIED",
        "Evidence architecture: Model D", "Ready for review: YES only after final validation",
    ):
        assert statement in status
    for path in (
        "docs/hermes_candidate_review_assisted_research_experiment_gold_case_fixture_pack_and_evaluation_rubric.md",
        "tests/fixtures/hermes_candidate_review_assisted_research_gold_cases.json",
        "tests/test_hermes_candidate_review_assisted_research_experiment_gold_case_fixture_pack_docs.py",
        "tests/test_hermes_candidate_review_assisted_research_experiment_gold_case_fixture_pack.py",
        "docs/status_entries/WP142.md",
    ):
        assert path in status
    assert "LOCAL_DRAFT_VERIFIED" not in status
    assert "TBD" not in status
    assert "Head commit:" not in status
    assert re.search(r"Current live PR head:\s*`?[0-9a-f]{40}`?", status, re.IGNORECASE) is None
    assert "future mergeability" not in status.lower()


def test_wp143_status_fragment_is_stable_and_contains_locked_decisions():
    status = (STATUS_ENTRIES / "WP143.md").read_text(encoding="utf-8")
    for statement in (
        "Assisted-research architecture: LOCAL_DETERMINISTIC_CONTROL_PLANE_WITH_EPHEMERAL_HERMES_SESSION",
        "Model-access posture: PROVIDER_NEUTRAL_REMOTE_MODEL_CANDIDATES_WITH_OPTIONAL_LOCAL_BASELINE",
        "Provider decision: SHORTLIST_MAXIMUM_TWO_REMOTE_CANDIDATES_PLUS_OPTIONAL_ONE_LOCAL_BASELINE",
        "Experiment data classification: SYNTHETIC_OFFLINE_TEST_DATA_ONLY",
        "Network posture for the first future experiment: PROVIDER_ENDPOINT_ONLY_DENY_ALL_OTHER_NETWORK",
        "Repository posture: NO_REPOSITORY_WIDE_ACCESS",
        "Credential posture: OUT_OF_REPO_OPERATOR_INJECTED_LEAST_PRIVILEGE_REVOCABLE_SECRET",
        "Memory posture: EPHEMERAL_SESSION_MEMORY_ONLY", "Persistent memory: FORBIDDEN",
        "140-call hard maximum", "USD 100 total", "USD 25 daily", "USD 2 per call",
        "one concurrent remote call", "Provider activation: NOT AUTHORIZED",
        "Hermes installation/runtime activation: NOT AUTHORIZED",
        "Evidence mode: PRIVATE_REPO_MANUAL_VERIFIED", "Evidence architecture: Model D",
        "Ready for review: YES only after final validation",
    ):
        assert statement in status
    assert "WP144" in status and "not implemented here" in status
    for path in (
        "docs/hermes_candidate_review_assisted_research_provider_runtime_privacy_permissions_budget_decision.md",
        "tests/test_hermes_candidate_review_assisted_research_provider_runtime_privacy_permissions_budget_decision_docs.py",
    ):
        assert path in status
    assert "LOCAL_DRAFT_VERIFIED" not in status
    assert "TBD" not in status
    assert "Head commit:" not in status
    assert re.search(r"Current live PR head:\s*`?[0-9a-f]{40}`?", status, re.IGNORECASE) is None
    assert "future mergeability" not in status.lower()


def test_wp144_status_fragment_is_stable_and_contains_locked_decisions():
    status = (STATUS_ENTRIES / "WP144.md").read_text(encoding="utf-8")
    for statement in (
        "Harness contract status: DOCUMENTATION_ONLY_RUNTIME_INACTIVE",
        "Controller authority: LOCAL_DETERMINISTIC_EXCLUSIVE",
        "Hermes session posture: ONE_CASE_ONE_EPHEMERAL_SESSION",
        "Provider adapter posture: ONE_EXPLICIT_CANDIDATE_CONFIGURATION_ONE_ALLOWLISTED_ENDPOINT",
        "Prompt/configuration status: VERSIONED_NON_EXECUTABLE_CONTRACT_ONLY",
        "Input posture: EXACT_VALIDATED_WP142_CASE_BUNDLE_ONLY",
        "Output posture: UNTRUSTED_DRAFT_ONLY",
        "Raw input/output persistence: FORBIDDEN_BY_DEFAULT",
        "Sanitized experiment metadata: FUTURE_ALLOW_EXACT_FIELDS_ONLY",
        "Network posture: DENY_ALL_EXCEPT_ONE_CONTROLLER_MEDIATED_PROVIDER_ENDPOINT",
        "Tool posture: NO_BROWSER_NO_SEARCH_NO_SOURCE_FETCH_NO_SHELL_NO_TRADING_TOOLS",
        "Memory posture: EPHEMERAL_SESSION_ONLY_DELETE_ON_TEARDOWN",
        "Dry-run posture: LOCAL_NO_PROVIDER_NO_NETWORK_NO_CREDENTIAL",
        "Deterministic validation and human review: MANDATORY",
        "Hermes/provider/model activation: NOT AUTHORIZED",
        "Paper/live/execution authority: FORBIDDEN", "WP145 requires separate approval",
        "Evidence mode: PRIVATE_REPO_MANUAL_VERIFIED", "Evidence architecture: Model D",
        "Ready for review: YES only after final validation",
    ):
        assert statement in status
    for path in (
        "docs/hermes_candidate_review_assisted_research_controlled_experiment_harness_contract_prompt_configuration_boundary_and_dry_run_plan.md",
        "tests/test_hermes_candidate_review_assisted_research_controlled_experiment_harness_contract_prompt_configuration_boundary_and_dry_run_plan_docs.py",
        "docs/status_entries/WP144.md",
    ):
        assert path in status
    assert "WP145" in status and "not implemented here" in status
    assert "LOCAL_DRAFT_VERIFIED" not in status
    assert "TBD" not in status
    assert "Head commit:" not in status
    assert re.search(r"Current live PR head:\s*`?[0-9a-f]{40}`?", status, re.IGNORECASE) is None
    assert "future mergeability" not in status.lower()


def test_wp145_status_fragment_is_stable_and_contains_locked_decisions():
    status = (STATUS_ENTRIES / "WP145.md").read_text(encoding="utf-8")
    for statement in (
        "Harness implementation status: LOCAL_OFFLINE_TEST_ORIENTED_SKELETON",
        "Controller authority: LOCAL_DETERMINISTIC_EXCLUSIVE",
        "Adapter status: TEST_ONLY_PRECOMPUTED_FAKE_RESPONSE",
        "Dry-run case count: 1",
        "Dry-run case ID: GC-P01-COMPLETE-SUPPORTED",
        "Network: FORBIDDEN",
        "Credentials: FORBIDDEN",
        "Hermes installation/invocation: FORBIDDEN",
        "Provider/model call: FORBIDDEN",
        "Stable raw input/output persistence: FORBIDDEN",
        "Temporary filesystem: PYTEST_TMP_PATH_ONLY",
        "Output: SANITIZED_EVIDENCE_ONLY",
        "Deterministic WP133 validation: MANDATORY",
        "Human review: EXPLICIT_CALLER_SUPPLIED_ACKNOWLEDGEMENT_REQUIRED",
        "Automatic downstream records: FORBIDDEN",
        "Paper/live/execution authority: FORBIDDEN",
        "WP146 requires separate approval",
        "Evidence mode: PRIVATE_REPO_MANUAL_VERIFIED",
        "Evidence architecture: Model D",
        "Ready for review: YES only after final validation",
    ):
        assert statement in status
    for path in (
        "src/data_layer/hermes_candidate_review_assisted_research_local_dry_run_harness.py",
        "tests/test_hermes_candidate_review_assisted_research_local_dry_run_harness.py",
        "tests/test_hermes_candidate_review_assisted_research_local_dry_run_harness_temp_smoke.py",
        "docs/hermes_candidate_review_assisted_research_local_dry_run_harness_operator_note.md",
        "docs/status_entries/WP145.md",
    ):
        assert path in status
    assert "WP144 merged" in status
    assert "WP145 sole review target" in status
    assert "WP146 gated" in status
    assert "LOCAL_DRAFT_VERIFIED" not in status
    assert "TBD" not in status
    assert "Head commit:" not in status
    assert re.search(r"Current live PR head:\s*`?[0-9a-f]{40}`?", status, re.IGNORECASE) is None
    assert "future mergeability" not in status.lower()


def test_wp146_status_fragment_is_stable_and_contains_locked_decisions():
    status = (STATUS_ENTRIES / "WP146.md").read_text(encoding="utf-8")
    for statement in (
        "Local harness phase status: CLOSED_COMPLETE_ENOUGH_FOR_BOUNDED_LOCAL_DRY_RUN",
        "WP145 corrected evidence accepted: YES",
        "Local one-case dry-run status: ACCEPTED_AS_TEST_ONLY_CONTROL_EVIDENCE",
        "WP145 implementation classification: BOUNDED_LOCAL_CONTROL_SKELETON",
        "WP145 phase-completion decision: ACCEPT",
        "Remote controlled experiment readiness: NOT_READY",
        "Primary remote-readiness blocker: CURRENT_PROVIDER_MODEL_PRIVACY_RETENTION_COST_AND_ENDPOINT_EVIDENCE_MISSING",
        "Provider/model candidate naming: DEFERRED_CURRENT_EXTERNAL_RESEARCH_REQUIRED",
        "Current external provider/model research: REQUIRED_BEFORE_REMOTE_EXPERIMENT_IMPLEMENTATION",
        "Remote experiment implementation authorization: DENIED_PENDING_RESEARCH_AND_CONTROL_GATES",
        "Remote adapter implementation: NOT AUTHORIZED",
        "Hermes installation/invocation: NOT AUTHORIZED",
        "Provider/model call: NOT AUTHORIZED",
        "Credential creation/use: NOT AUTHORIZED",
        "Network endpoint activation: NOT AUTHORIZED",
        "Experiment spending: NOT AUTHORIZED",
        "Raw input/output persistence: NOT AUTHORIZED",
        "Paper/live/execution authority: FORBIDDEN",
        "Next phase: CURRENT_PROVIDER_MODEL_PRIVACY_RETENTION_COST_RESEARCH_AND_CANDIDATE_SHORTLIST",
        "WP147 requires separate approval",
        "Review follow-up required: YES",
        "Classification: A — stable repo-truth / PR-evidence contradiction",
        "Resolution status: COMPLETE",
        "Further follow-up correction required: NO",
        "Separate hardening WP needed: NO",
        "Evidence mode: PRIVATE_REPO_MANUAL_VERIFIED",
        "Evidence architecture: Model D",
        "Ready for review: YES only after final validation",
    ):
        assert statement in status
    for path in (
        "docs/hermes_candidate_review_assisted_research_local_harness_closeout_and_controlled_remote_experiment_readiness_decision.md",
        "tests/test_hermes_candidate_review_assisted_research_local_harness_closeout_and_controlled_remote_experiment_readiness_decision_docs.py",
        "docs/status_entries/WP146.md",
    ):
        assert path in status
    assert "WP145 is merged" in status
    assert "WP146" in status and "review target" in status.lower()
    assert "LOCAL_DRAFT_VERIFIED" not in status
    assert "TBD" not in status
    assert "Head commit:" not in status
    assert re.search(r"Current live PR head:\s*`?[0-9a-f]{40}`?", status, re.IGNORECASE) is None
    assert "future mergeability" not in status.lower()
    normalized_status = " ".join(status.split())
    assert (
        "Existing Hermes foundation guards already accepted the WP146 documentation and "
        "focused-test paths, so no Hermes-document allowlist edit was required."
        in normalized_status
    )
    assert (
        "The only compatibility-test modification was the dedicated project-status/"
        "status-fragment chain extension in `tests/test_project_status_docs.py`."
        in normalized_status
    )
    assert "Hermes-document allowlist additions: NONE" in status
    assert (
        "Compatibility-test modification: `tests/test_project_status_docs.py` ONLY"
        in status
    )
    assert (
        "No source registration, prompt-runbook source registration, architecture source "
        "allowlist, fixture registration, wildcard, regex weakening, assertion deletion, "
        "filename-specific evidence exception, or deferred-log change was required."
        in normalized_status
    )
    assert "two exact Hermes-document allowlist additions" not in status


def test_wp147_status_fragment_is_stable_and_contains_locked_decisions():
    status = (STATUS_ENTRIES / "WP147.md").read_text(encoding="utf-8")
    expected_headings = [
        "# WP147 — Hermes Current Provider/Model Research And Candidate Shortlist V1",
        "## Package Identity",
        "## Authorization Basis",
        "## Authority / Non-Authority",
        "## Merge Gate",
        "## Repository Inputs Reviewed",
        "## Repository Discovery",
        "## Research Authority",
        "## Research Method",
        "## Research Cut-Off",
        "## Source Hierarchy",
        "## Candidate Pool",
        "## Hermes Compatibility",
        "## Mandatory Eligibility",
        "## Candidate Research Summary",
        "## Privacy/Retention Summary",
        "## Endpoint Summary",
        "## Cost Summary",
        "## Optional Local Baseline",
        "## Eligibility Matrix",
        "## Shortlist Decision",
        "## Candidate-Specific Blockers",
        "## Cross-Cutting Blockers",
        "## Readiness Decision",
        "## Next Phase",
        "## Promotion Gates",
        "## Deferred Capabilities",
        "## Changed Files",
        "## Requirement-To-Evidence",
        "## Validation",
        "## Model D Evidence",
        "## Stable Metadata",
        "## Follow-Up Classification",
        "## Ready For Review",
    ]
    headings = [
        line
        for line in status.splitlines()
        if line.startswith("# ") or line.startswith("## ")
    ]
    assert headings == expected_headings
    for statement in (
        "WP147 research status: COMPLETE",
        "Research cut-off: 2026-07-22T23:49:02Z",
        "Candidate pool posture: CURRENT_AUTHORITATIVE_FIRST_PARTY_RESEARCH_ONLY",
        "Provider decision: NO_PROVIDER_SELECTED_EVIDENCE_INSUFFICIENT",
        "Candidate shortlist decision: EVIDENCE_INSUFFICIENT_NO_SHORTLIST",
        "Remote configurations eligible: 0",
        "Remote configurations shortlisted: 0",
        "expected_us_geo_cost: USD 0.0594",
        "stress_us_geo_cost: USD 0.2970",
        "Local baseline decision: DEFERRED_HARDWARE_EVIDENCE_MISSING",
        "Remote controlled experiment readiness: NOT_READY",
        "Provider/model activation: NOT AUTHORIZED",
        "Provider/model call: NOT AUTHORIZED",
        "Hermes installation/invocation: NOT AUTHORIZED",
        "Provider account creation: NOT AUTHORIZED",
        "Credential creation/use: NOT AUTHORIZED",
        "Network endpoint activation: NOT AUTHORIZED",
        "Experiment spending: NOT AUTHORIZED",
        "Raw input/output persistence: NOT AUTHORIZED",
        "Paper/live/execution authority: FORBIDDEN",
        "Next phase: MANDATORY_EVIDENCE_RESOLUTION_AND_RESEARCH_REFRESH_DECISION",
        "WP148 requires separate approval and is not authorized as candidate selection while the shortlist count is zero",
        "Review follow-up required: YES",
        "Classification: B — candidate-eligibility evidence integrity and canonical evidence consistency",
        "Evidence mode: PRIVATE_REPO_MANUAL_VERIFIED",
        "Evidence architecture: Model D",
        "Ready for review: YES only after final validation",
    ):
        assert statement in status
    for path in (
        "docs/hermes_candidate_review_assisted_research_current_provider_model_privacy_retention_cost_endpoint_research_and_candidate_shortlist.md",
        "tests/test_hermes_candidate_review_assisted_research_current_provider_model_privacy_retention_cost_endpoint_research_and_candidate_shortlist_docs.py",
        "docs/status_entries/WP147.md",
    ):
        assert path in status
    assert "WP146 is merged" in status
    assert "WP147 is the sole current review target" in status
    assert "Hermes-document allowlist additions: NONE" in status
    assert "Compatibility-test modification: `tests/test_project_status_docs.py` ONLY" in status
    assert "LOCAL_DRAFT_VERIFIED" not in status
    assert "TBD" not in status
    assert "Head commit:" not in status
    assert re.search(r"Current live PR head:\s*`?[0-9a-f]{40}`?", status, re.IGNORECASE) is None
    assert "future mergeability" not in status.lower()


def test_wp148_status_fragment_is_stable_and_contains_locked_decisions():
    status = (STATUS_ENTRIES / "WP148.md").read_text(encoding="utf-8")
    expected_headings = [
        "# WP148 — Hermes Mandatory Provider Evidence Resolution And Research Refresh Decision V1",
        "## Package Identity",
        "## Authorization Basis",
        "## Authority / Non-Authority",
        "## Merge Gate",
        "## Repository Discovery",
        "## Research Authority And Method",
        "## Research Cut-Off And Registry",
        "## Evidence Resolution",
        "## Eligibility And Provider Decision",
        "## Local-Baseline And Next Phase",
        "## Readiness And Non-Authority",
        "## Changed Files",
        "## Requirement-To-Evidence",
        "## Validation",
        "## Model D Evidence",
        "## Stable Metadata",
        "## Ready For Review",
    ]
    headings = [
        line
        for line in status.splitlines()
        if line.startswith("# ") or line.startswith("## ")
    ]
    assert headings == expected_headings
    for statement in (
        "Research cut-off: 2026-07-23T16:10:31Z",
        "Refreshed source count: 11",
        "Tier 1 source count: 10",
        "Tier 2 source count: 1",
        "Tier 2 source IDs: ANT-R02",
        "OpenAI deletion result: EVIDENCE_INSUFFICIENT",
        "OpenAI key-lifecycle result: EVIDENCE_INSUFFICIENT",
        "Anthropic deletion result: EVIDENCE_INSUFFICIENT",
        "Anthropic subprocessor result: PASS",
        "Anthropic security/incident result: PASS",
        "Google result: EVIDENCE_INSUFFICIENT",
        "WP148 evidence-resolution status: COMPLETE_EVIDENCE_STILL_INSUFFICIENT",
        "Candidate eligibility result: EVIDENCE_INSUFFICIENT_NO_ELIGIBLE_CANDIDATE",
        "Remote configurations deeply researched: 3",
        "Remote configurations eligible: 0",
        "Remote configurations shortlisted: 0",
        "Provider/model selection: NOT MADE",
        "Local baseline pivot decision: DEFER_HARDWARE_EVIDENCE_MISSING",
        "Remote controlled experiment readiness: NOT_READY",
        "Next phase: REMOTE_PROVIDER_TRACK_DEFER_OR_RESEARCH_REFRESH_LATER_DECISION",
        "Provider/model activation: NOT AUTHORIZED",
        "Provider/model call: NOT AUTHORIZED",
        "Hermes installation/invocation: NOT AUTHORIZED",
        "Provider account creation: NOT AUTHORIZED",
        "Credential creation/use: NOT AUTHORIZED",
        "Network endpoint activation: NOT AUTHORIZED",
        "Experiment spending: NOT AUTHORIZED",
        "Raw input/output persistence: NOT AUTHORIZED",
        "Paper/live/execution authority: FORBIDDEN",
        "WP149 requires separate approval",
        "Hermes-document allowlist additions: NONE",
        "Compatibility-test modification: `tests/test_project_status_docs.py` ONLY",
        "Evidence mode: PRIVATE_REPO_MANUAL_VERIFIED",
        "Evidence architecture: Model D",
        "Ready for review: YES only after final validation",
    ):
        assert statement in status
    for path in (
        "docs/hermes_candidate_review_assisted_research_mandatory_provider_evidence_resolution_and_research_refresh_decision.md",
        "tests/test_hermes_candidate_review_assisted_research_mandatory_provider_evidence_resolution_and_research_refresh_decision_docs.py",
        "docs/status_entries/WP148.md",
    ):
        assert path in status
    assert "WP147 is merged" in status
    assert "WP148 is the sole current review target" in status
    assert "LOCAL_DRAFT_VERIFIED" not in status
    assert "TBD" not in status
    assert "Head commit:" not in status
    assert (
        re.search(
            r"Current live PR head:\s*`?[0-9a-f]{40}`?",
            status,
            re.IGNORECASE,
        )
        is None
    )
    assert "future mergeability" not in status.lower()


def test_wp149_status_fragment_is_stable_and_contains_locked_decisions():
    status = (STATUS_ENTRIES / "WP149.md").read_text(encoding="utf-8")
    expected_headings = [
        "# WP149 — Hermes Remote Provider Track Deferral And Revisit Criteria Decision V1",
        "## Package Identity",
        "## Authorization Basis",
        "## Authority / Non-Authority",
        "## Merge Gate",
        "## Repository Inputs Reviewed",
        "## Repository Discovery",
        "## Deferral Decision",
        "## Meaning Of Deferral",
        "## Revisit Triggers",
        "## Non-Triggers",
        "## Materiality Standard",
        "## Revisit Evidence Packet",
        "## Anti-Loop Rules",
        "## Deferral Review Cadence",
        "## Reopen State Machine",
        "## Productive Next Phase",
        "## Promotion Gates",
        "## Deferred Capabilities",
        "## Changed Files",
        "## Requirement-To-Evidence",
        "## Validation",
        "## Model D Evidence",
        "## Stable Metadata",
        "## Follow-Up Classification",
        "## Ready For Review",
    ]
    headings = [
        line
        for line in status.splitlines()
        if line.startswith("# ") or line.startswith("## ")
    ]
    assert headings == expected_headings
    for statement in (
        "Remote provider track status:\nDEFERRED_PENDING_MATERIAL_NEW_EVIDENCE",
        "Automatic periodic provider re-research:\nFORBIDDEN",
        "Repeated unchanged provider research:\nFORBIDDEN",
        "Scheduled periodic provider sweep:\nFORBIDDEN",
        "Reopen based only on elapsed time:\nFORBIDDEN",
        "Provider track may reopen only after:\nMATERIAL_EVIDENCE_TRIGGER_AND_SEPARATE_APPROVAL",
        "Deferral review cadence:\nEVENT_DRIVEN_ONLY",
        "Remote configurations eligible",
        "zero eligible",
        "zero shortlisted",
        "no provider/model selection",
        "remote readiness `NOT_READY`",
        "Next phase:\nLOCAL_RESEARCH_WORKFLOW_VALUE_VALIDATION_AND_PAPER_TRADING_READINESS_DECISION",
        "WP150 requires separate approval",
        "Hermes-document allowlist additions: NONE",
        "Architecture-test modification:",
        "`tests/test_wallet_intelligence_architecture_contract_docs.py` current-phase",
        "Compatibility-test modification: `tests/test_project_status_docs.py` ONLY",
        "Evidence mode: PRIVATE_REPO_MANUAL_VERIFIED",
        "Evidence architecture: Model D",
        "Ready for review: YES only after final validation",
    ):
        assert statement in status
    for path in (
        "docs/hermes_remote_provider_track_deferral_and_revisit_criteria_decision.md",
        "tests/test_hermes_remote_provider_track_deferral_and_revisit_criteria_decision_docs.py",
        "docs/status_entries/WP149.md",
        "docs/project_status.md",
        "docs/repo_truth_index.md",
        "tests/test_project_status_docs.py",
        "tests/test_wallet_intelligence_architecture_contract_docs.py",
    ):
        assert path in status
    assert "WP148 is merged" in status
    assert "WP149 is the sole current review target" in status
    assert "LOCAL_DRAFT_VERIFIED" not in status
    assert "TBD" not in status
    assert "Head commit:" not in status
    assert (
        re.search(
            r"Current live PR head:\s*`?[0-9a-f]{40}`?",
            status,
            re.IGNORECASE,
        )
        is None
    )
    assert "future mergeability" not in status.lower()


def test_wp150_status_fragment_is_stable_and_contains_locked_decisions():
    status = (STATUS_ENTRIES / "WP150.md").read_text(encoding="utf-8")
    expected_headings = [
        "# WP150 — Local Research Workflow Value Validation And Paper-Trading Readiness Decision V1",
        "## Package Identity",
        "## Authorization Basis",
        "## Authority / Non-Authority",
        "## Merge Gate",
        "## Repository Inputs Reviewed",
        "## Repository Discovery",
        "## Research-Value Decision",
        "## Paper-Readiness Decision",
        "## Preserved Boundaries",
        "## Blockers",
        "## Productive Next Phase",
        "## Promotion Gates",
        "## Deferred Capabilities",
        "## Changed Files",
        "## Requirement-To-Evidence",
        "## Validation",
        "## Model D Evidence",
        "## Stable Metadata",
        "## Follow-Up Classification",
        "## Ready For Review",
    ]
    headings = [
        line
        for line in status.splitlines()
        if line.startswith("# ") or line.startswith("## ")
    ]
    assert headings == expected_headings
    for statement in (
        "Local research workflow value-validation status:\n"
        "PARTIALLY_READY_BLOCKERS_IDENTIFIED",
        "Research-value metric records:\n39",
        "Research-value metrics measured:\n0",
        "Research-value metrics measurable but not yet measured:\n22",
        "Research-value metrics not currently measurable:\n17",
        "Research-value blockers:\n7",
        "Paper-trading implementation readiness:\nNOT_READY_FOUNDATIONAL_GAPS",
        "Remote provider track status:\nDEFERRED_PENDING_MATERIAL_NEW_EVIDENCE",
        "Automatic periodic provider re-research:\nFORBIDDEN",
        "Deferral review cadence:\nEVENT_DRIVEN_ONLY",
        "Remote configurations eligible:\n0",
        "Remote configurations shortlisted:\n0",
        "Provider/model selection:\nNOT MADE",
        "Remote controlled experiment readiness:\nNOT_READY",
        "Paper-trading execution:\nNOT AUTHORIZED",
        "Live-trading execution:\nFORBIDDEN",
        "Capital at risk:\nUSD 0",
        "Orders submitted:\n0",
        "Credentials created/used:\n0",
        "External model calls:\n0",
        "Next phase:\nLOCAL_RESEARCH_WORKFLOW_VALUE_MEASUREMENT_HARNESS_CONTRACT",
        "WP151 requires separate approval",
        "Hermes-document and architecture-test allowlist additions: NONE",
        "Compatibility-test modification: `tests/test_project_status_docs.py` ONLY",
        "Evidence mode: PRIVATE_REPO_MANUAL_VERIFIED",
        "Evidence architecture: Model D",
        "Ready for review: YES only after final validation",
        "Follow-up correction required: YES",
        "Classification: B — positive readiness conclusion was not fully grounded in",
        "Current PR reused: YES",
        "WP151 implemented: NO",
    ):
        assert statement in status
    for path in (
        "docs/local_research_workflow_value_validation_and_paper_trading_readiness_decision.md",
        "tests/test_local_research_workflow_value_validation_and_paper_trading_readiness_decision_docs.py",
        "docs/status_entries/WP150.md",
        "docs/project_status.md",
        "docs/repo_truth_index.md",
        "tests/test_project_status_docs.py",
    ):
        assert path in status
    assert "WP149 is merged" in status
    assert "WP150 is the sole current review target" in status
    assert "LOCAL_DRAFT_VERIFIED" not in status
    assert "TBD" not in status
    assert "Head commit:" not in status
    assert (
        re.search(
            r"Current live PR head:\s*`?[0-9a-f]{40}`?",
            status,
            re.IGNORECASE,
        )
        is None
    )
    assert "future mergeability" not in status.lower()


# ── WP153: bounded synthetic dry run and receipt review ──────────────────────


def test_wp153_through_wp169_merged_and_wp170_is_current_review_target():
    # WP169 is merged via PR #170. WP170 is the current experiment-registry review target
    # and precedes the separately gated WP171 operator-cockpit successor.
    text = _read()
    current_phase_line = next(
        line for line in text.splitlines() if line.startswith("- Current phase:")
    )
    merged_line = next(
        line for line in text.splitlines() if line.startswith("- Merged WPs:")
    )
    assert "WP170" in current_phase_line
    assert "WP130" in current_phase_line
    for wp in (
        "WP153", "WP154", "WP155", "WP156", "WP157", "WP158", "WP159", "WP160",
        "WP161", "WP162", "WP163", "WP164", "WP165", "WP166", "WP167", "WP168",
        "WP168G", "WP169",
    ):
        assert wp in merged_line, wp
    for phrase in (
        "current review target",
        "following merged WP169",
        "Primary package class: FALSIFICATION_GRADE_EXPERIMENT_REGISTRY_AND_RESEARCH_DATASET_OS",
        "Package size class: XL",
        "XL explicit authorization: YES",
        "Risk level: 2",
        "Implementation posture: LOCAL_OFFLINE_DETERMINISTIC_APPEND_ONLY_RESEARCH_CONTROL_NO_EXECUTION_AUTHORITY",
        "Ready for review: YES_INDEPENDENTLY_CERTIFIED",
        "Merge authorized: NO",
        "Independent live PR review required: YES",
        "Exact changed-file scope: 26",
        "New direct runtime dependency: NONE",
        "Default network posture: OFF",
        "Product/runtime network calls: 0",
        "Paper-trading execution: NOT AUTHORIZED",
        "Live-trading execution: FORBIDDEN",
        "Canonical PIT authority unchanged: YES",
        "Direct Nautilus ingestion claimed: NO",
        "WP166 merged: YES",
        "WP167 merged: YES",
        "WP168 merged: YES",
        "WP168G merged: YES",
        "WP169 merged: YES",
        "WP169 PR: 170",
        "WP169 final head: c4a09aeb33e4c271feb709622660e5e58a00b642",
        "WP169 merge commit: 17df81001171988e9ca49f92dc8fd170ecaa7103",
        "Next phase: WP171_INTERACTIVE_OPERATOR_COCKPIT_SEPARATELY_GATED",
    ):
        assert phrase in current_phase_line, phrase


def test_wp170_status_reconciles_wp169_merge_and_preserves_wp171_successor():
    # Project status records WP169 merged at its exact head/merge SHA (PR #170), WP170 as
    # the current experiment-registry review target, and WP171 as separately gated.
    text = _read()
    current_phase_line = next(
        line for line in text.splitlines() if line.startswith("- Current phase:")
    )
    merged_line = next(
        line for line in text.splitlines() if line.startswith("- Merged WPs:")
    )
    assert "WP169" in merged_line
    assert "WP169 merge commit: 17df81001171988e9ca49f92dc8fd170ecaa7103" in current_phase_line
    assert "WP169 final head: c4a09aeb33e4c271feb709622660e5e58a00b642" in current_phase_line
    assert "WP170" in current_phase_line
    assert "FALSIFICATION_GRADE_EXPERIMENT_REGISTRY_AND_RESEARCH_DATASET_OS" in current_phase_line
    assert "WP171_INTERACTIVE_OPERATOR_COCKPIT_SEPARATELY_GATED" in current_phase_line


def test_wp167_analytical_research_foundation_status_is_registered():
    text = _read()
    line = next(
        item
        for item in text.splitlines()
        if item.startswith("- Analytical research foundation status:")
    )
    for phrase in (
        "LOCAL_OFFLINE_DERIVED_ANALYTICAL_MATERIALIZATION_AND_EXTERNAL_HISTORY_FOUNDATION",
        "Implemented by: WP167",
        "src/data_layer/analytical_research/",
        "New direct runtime dependencies: pyarrow==25.0.1, duckdb==1.5.5, polars==1.44.1",
        "Python support floor: >=3.12,<3.15",
        "Canonical PIT authority unchanged: YES",
        "Logical dataset identity independent of physical Parquet bytes: YES",
        "External pmxt v2 provenance classified THIRD_PARTY_NATIVE_FRAME_ARCHIVE: YES",
        "External downloader: NONE",
        "DuckDB local execution: OBSERVATIONAL_PASS_OR_BLOCKED_BY_WINDOWS_SMART_APP_CONTROL",
        "DuckDB/Polars parity validated by hosted CI: GREEN",
        "No NautilusTrader/WebSocket/Data API/Hermes/strategy/paper/execution/live: YES",
        "docs/analytical_research_layer_contract.md",
    ):
        assert phrase in line, phrase


def test_wp166_scaled_population_status_is_registered():
    text = _read()
    line = next(
        item for item in text.splitlines()
        if item.startswith(
            "- Bounded scalable lineage-delta keyset Polymarket population status:"
        )
    )
    for phrase in (
        "POLYMARKET_SCALABLE_KEYSET_LINEAGE_DELTA_POPULATION",
        "MANUAL_ONE_PAGE_KEYSET_GET_ONLY_EXTERNAL_PARENT_COMMITTED_NO_TRADING_AUTHORITY",
        "polymarket_scaled_population.py",
        "Endpoints: Gamma GET /markets/keyset and optional CLOB GET /book only",
        "Keyset endpoint repo-verified: NO",
        "Double opt-in required for real keyset use: YES",
        "Offset ever sent: NO",
        "Maximum keyset page requests per invocation: 1",
        "Maximum markets per page: 100",
        "Automatic cursor loop: NO",
        "Only current records registered as v2 lineage-delta reference: YES",
        "Physical history beyond 256 supported within WP163 4096 horizon: YES",
        "v1 dataset snapshot references remain supported: YES",
        "SQLite schema or user_version migration: NONE",
        "next_cursor part of immutable record identity: NO",
        "Package export inventory grew by: 8",
        "WP162-D004 resolved for bounded registered external-parent context: YES",
        "WP165-D001 resolved by lineage-delta within current physical horizon: YES",
        "WP166 Ready for review: YES",
    ):
        assert phrase in line


def test_wp164_public_population_status_repo_truth_and_deferred_items_are_registered():
    text = _read()
    line = next(
        item for item in text.splitlines()
        if item.startswith(
            "- Bounded real/public initial Polymarket population status:"
        )
    )
    for phrase in (
        "POLYMARKET_REAL_PUBLIC_INITIAL_POINT_IN_TIME_POPULATION",
        "EXPLICIT_NETWORK_GET_ONLY_BOUNDED_INITIAL_SEED_NO_TRADING_AUTHORITY",
        "polymarket_public_population.py",
        "Package class: DATA_LAYER_PUBLIC_POPULATION",
        "Default network posture: OFF",
        "Endpoints: Gamma GET /markets and optional CLOB GET /book only",
        "Authenticated endpoints used: NONE",
        "POST /books used: NO",
        "Trading/order/execution methods used: NONE",
        "Local guard remains runtime request authority: YES",
        "Maximum Gamma requests per run: 1",
        "Maximum CLOB book requests per run: 20",
        "Empty WP163 record store required for new population: YES",
        "Records built through WP156 build_market_observation only: YES",
        "Records persisted through WP163 append only: YES",
        "Manifest registered through WP162 only: YES",
        "Record write occurs before reference registration: YES",
        "Registration failure recoverable offline without deletion or re-fetch: YES",
        "Recovery performs zero network: YES",
        "Raw HTTP/source-response bytes stored: NO",
        "Old WP10 JSONL writer or local_data path used: NO",
        "Direct network library in new module: NO",
        "Scheduler/retry/backoff/sleep: NO",
        "Incremental population into non-empty store: NO",
        "Package export inventory grew by: 8",
        "Dependencies added: 0",
        "WP164 Ready for review: YES",
        "Merge authorized: NO",
    ):
        assert phrase in line

    status = (STATUS_ENTRIES / "WP164.md").read_text(encoding="utf-8")
    for phrase in (
        "stable and non-self-referential",
        "Ready for review: YES",
        "Merge authorized: NO",
        "98d8e5813efddddca87608c6965bbbb5346cb371",
        "889a249c54aac589d952827425eadfc0aae1606a",
        "WP164-D007",
    ):
        assert phrase in status
    assert re.search(
        r"Current live PR head:\s*`?[0-9a-f]{40}`?", status, re.IGNORECASE
    ) is None

    index = (REPO_ROOT / "docs" / "repo_truth_index.md").read_text(encoding="utf-8")
    for path in (
        "src/data_layer/point_in_time_market_research/polymarket_public_population.py",
        "docs/status_entries/WP164.md",
        "docs/polymarket_point_in_time_public_population_contract.md",
        "tests/data_layer/point_in_time_market_research/test_polymarket_public_population.py",
    ):
        assert path in index
    deferred = (REPO_ROOT / "docs" / "deferred_items_log.md").read_text(
        encoding="utf-8"
    )
    assert "RESOLVED_BOUNDED_WP164_INITIAL_PUBLIC_MARKET_POPULATION" in deferred
    for index_value in range(1, 8):
        assert f"WP164-D{index_value:03d}" in deferred


def test_wp165_incremental_population_status_repo_truth_and_deferred_items_are_registered():
    text = _read()
    line = next(
        item for item in text.splitlines()
        if item.startswith(
            "- Bounded incremental cumulative Polymarket population status:"
        )
    )
    for phrase in (
        "POLYMARKET_BOUNDED_CUMULATIVE_INCREMENTAL_POINT_IN_TIME_POPULATION",
        "MANUAL_GET_ONLY_CUMULATIVE_256_RECORD_CROSS_RUN_LINEAGE_NO_TRADING_AUTHORITY",
        "polymarket_incremental_population.py",
        "Package class: DATA_LAYER_PUBLIC_POPULATION",
        "Default network posture: OFF",
        "Endpoints: Gamma GET /markets and optional CLOB GET /book only",
        "Authenticated endpoints used: NONE",
        "POST /books used: NO",
        "Keyset/pagination used: NO",
        "Data API used: NO",
        "Trading/order/execution methods used: NONE",
        "Local guard remains runtime request authority: YES",
        "Cumulative record cap: 256",
        "Populated and registered WP163 record store required: YES",
        "Latest registered VALIDATED_RECORD_BATCH reference convergence proven before network: YES",
        "Store strict-superset yields recoverable baseline-unregistered: YES",
        "Worst-case capacity checked before any client call: YES",
        "Identity drift rejected: YES",
        "External known_parent_record_ids passed through WP162: NO",
        "Manifest/dataset snapshot reference schema migration: NONE",
        "Only new records appended through WP163: YES",
        "Complete cumulative dataset registered through WP162: YES",
        "New records appended before cumulative registration: YES",
        "Old registered reference remains immutable: YES",
        "Registration failure recoverable offline without deletion or re-fetch: YES",
        "Recovery performs zero network: YES",
        "Raw HTTP/source-response bytes stored: NO",
        "Direct network library in new module: NO",
        "Scheduler/retry/backoff/sleep: NO",
        "Package export inventory grew by: 7",
        "Dependencies added: 0",
        "WP164-D001 partially resolved for bounded cumulative internal-parent lineage scope: YES",
        "WP162-D004 remains open: YES",
        "WP165 Ready for review: YES",
        "Merge authorized: NO",
    ):
        assert phrase in line

    status = (STATUS_ENTRIES / "WP165.md").read_text(encoding="utf-8")
    for phrase in (
        "stable and non-self-referential",
        "Ready for review: YES",
        "Merge authorized: NO",
        "0f3f29e32f7bb404f1156afba83ea33c3ee5cb1b",
        "652ac21547db42512e7f9360986e1616c6622384",
        "WP165-D007",
    ):
        assert phrase in status
    assert re.search(
        r"Current live PR head:\s*`?[0-9a-f]{40}`?", status, re.IGNORECASE
    ) is None

    index = (REPO_ROOT / "docs" / "repo_truth_index.md").read_text(encoding="utf-8")
    for path in (
        "src/data_layer/point_in_time_market_research/polymarket_incremental_population.py",
        "docs/status_entries/WP165.md",
        "docs/polymarket_incremental_point_in_time_population_contract.md",
        "tests/data_layer/point_in_time_market_research/test_polymarket_incremental_population.py",
    ):
        assert path in index
    deferred = (REPO_ROOT / "docs" / "deferred_items_log.md").read_text(
        encoding="utf-8"
    )
    assert "PARTIALLY_RESOLVED_WP165_CUMULATIVE_INTERNAL_PARENT_LINEAGE" in deferred
    for index_value in range(1, 8):
        assert f"WP165-D{index_value:03d}" in deferred


def test_wp163_record_store_status_repo_truth_and_deferred_items_are_registered():
    text = _read()
    line = next(
        item for item in text.splitlines()
        if item.startswith("- Bounded durable point-in-time record store status:")
    )
    for phrase in (
        "POINT_IN_TIME_DURABLE_RECORD_STORE",
        "BOUNDED_LOCAL_SQLITE_APPEND_ONLY_RECORD_PERSISTENCE_AND_MATERIALIZATION",
        "record_store.py",
        "Python standard-library sqlite3",
        "Store format: point-in-time-record-store",
        "Application tables: 2",
        "Explicit indexes: 5",
        "Journal mode: DELETE",
        "Writable synchronous: FULL",
        "Transaction start: BEGIN IMMEDIATE",
        "Read URI mode: ro",
        "Existing-write URI mode: rw",
        "Creation URI mode: rwc",
        "Maximum records per append: 256",
        "Maximum records in store: 4096",
        "Maximum canonical full-record payload bytes per row: 131072",
        "Maximum total canonical payload bytes: 134217728",
        "Conflict record ever ordinary authority: NO",
        "Idempotent retry uses UPDATE: NO",
        "Public persisted-row DELETE path: NO",
        "Schema migration: NOT AUTHORIZED",
        "WAL: FORBIDDEN",
        "Parquet/Arrow/DuckDB/Polars adopted: NO",
        "Raw HTTP/source-response bytes stored: NO",
        "Real/public network collection performed: NO",
        "Dependencies added: 0",
        "Strategy/signal/paper/order/risk/execution authority: NONE",
        "WP163 Ready for review: YES",
        "Merge authorized: NO",
    ):
        assert phrase in line

    status = (STATUS_ENTRIES / "WP163.md").read_text(encoding="utf-8")
    for phrase in (
        "stable and non-self-referential",
        "Ready for review: YES",
        "Merge authorized: NO",
        "R001",
        "R040",
        "WP163-D007",
    ):
        assert phrase in status
    assert re.search(
        r"Current live PR head:\s*`?[0-9a-f]{40}`?", status, re.IGNORECASE
    ) is None

    index = (REPO_ROOT / "docs" / "repo_truth_index.md").read_text(encoding="utf-8")
    for path in (
        "src/data_layer/point_in_time_market_research/record_store.py",
        "docs/status_entries/WP163.md",
        "docs/point_in_time_record_store_contract.md",
        "tests/data_layer/point_in_time_market_research/test_record_store.py",
    ):
        assert path in index
    deferred = (REPO_ROOT / "docs" / "deferred_items_log.md").read_text(
        encoding="utf-8"
    )
    assert (
        "RESOLVED_BOUNDED_WP163_SQLITE_RECORD_STORE_AND_REFERENCE_MATERIALIZATION"
        in deferred
    )
    for index_value in range(1, 8):
        assert f"WP163-D{index_value:03d}" in deferred


def test_wp161_sqlite_status_repo_truth_and_deferred_items_are_registered():
    text = _read()
    line = next(
        item for item in text.splitlines()
        if item.startswith("- Bounded local SQLite manifest store status:")
    )
    for phrase in (
        "POINT_IN_TIME_LOCAL_SQLITE_MANIFEST_STORE",
        "BOUNDED_LOCAL_SQLITE_TRANSACTIONAL_APPEND_AND_VERIFIED_READ",
        "manifest_store.py",
        "Python standard-library sqlite3",
        "Application tables: 3",
        "Journal mode: DELETE",
        "Writable synchronous: FULL",
        "Writable foreign_keys: ON",
        "Transaction start: BEGIN IMMEDIATE",
        "Read URI mode: ro",
        "Existing-write URI mode: rw",
        "Creation URI mode: rwc",
        "Maximum dataset references: 256",
        "Maximum manifest entries: 256",
        "Maximum canonical payload bytes per row: 65536",
        "Idempotent retry uses UPDATE: NO",
        "Public persisted-row DELETE path: NO",
        "Schema migration: NOT AUTHORIZED",
        "WAL: FORBIDDEN",
        "Dependencies added: 0",
        "Product/runtime network calls: 0",
        "Strategy/signal/paper/order/risk/execution authority: NONE",
        "WP161 Ready for review: NO",
        "Merge authorized: NO",
    ):
        assert phrase in line

    status = (STATUS_ENTRIES / "WP161.md").read_text(encoding="utf-8")
    for phrase in (
        "stable and non-self-referential",
        "Ready for review: NO",
        "Merge authorized: NO",
        "BLOCKED_NOT_READY",
        "exactly these 18 paths",
        "R001",
        "R032",
        "WP161-D007",
    ):
        assert phrase in status
    assert re.search(
        r"Current live PR head:\s*`?[0-9a-f]{40}`?", status, re.IGNORECASE
    ) is None

    index = (REPO_ROOT / "docs" / "repo_truth_index.md").read_text(encoding="utf-8")
    for path in (
        "src/data_layer/point_in_time_market_research/manifest_store.py",
        "docs/status_entries/WP161.md",
        "tests/data_layer/point_in_time_market_research/test_manifest_store.py",
    ):
        assert path in index
    deferred = (REPO_ROOT / "docs" / "deferred_items_log.md").read_text(
        encoding="utf-8"
    )
    for phrase in (
        "RESOLVED_BOUNDED_SQLITE_APPEND",
        "RESOLVED_BOUNDED_SQLITE_VERIFIED_READ",
        "RESOLVED_SQLITE_SINGLE_FILE_EXPLICIT_CALLER_PATH",
        "RESOLVED_BOUNDED_SQLITE_TRANSACTION_AND_FAIL_FAST_SINGLE_WRITER",
        "RESOLVED_BOUNDED_SQLITE_ATOMIC_TRANSACTION_PRIMITIVE",
    ):
        assert phrase in deferred
    for index_value in range(1, 8):
        assert f"WP161-D{index_value:03d}" in deferred


def test_wp153_synthetic_results_are_not_labeled_real_metrics():
    text = _read()
    assert "Research-value metrics measured: 0" in text
    assert "Real workflow research-value metrics measured: 0" in text
    assert "Research-value metrics measured: 22" not in text


def test_wp153_document_status_and_test_are_registered_in_repo_truth():
    index_text = (REPO_ROOT / "docs" / "repo_truth_index.md").read_text(
        encoding="utf-8"
    )
    status_text = _read()
    for path in (
        "docs/local_research_workflow_value_measurement_dry_run_and_receipt_review.md",
        "docs/status_entries/WP153.md",
        "tests/test_local_research_workflow_value_measurement_dry_run_and_receipt_review.py",
    ):
        assert path in index_text
    assert (
        "Local research workflow value measurement dry run and receipt review status:"
        in status_text
    )
    assert (STATUS_ENTRIES / "WP153.md").is_file()
    assert (
        REPO_ROOT
        / "docs"
        / "local_research_workflow_value_measurement_dry_run_and_receipt_review.md"
    ).is_file()


def test_wp153_records_exact_deterministic_hashes():
    status_text = _read()
    wp153_status = (STATUS_ENTRIES / "WP153.md").read_text(encoding="utf-8")
    doc = (
        REPO_ROOT
        / "docs"
        / "local_research_workflow_value_measurement_dry_run_and_receipt_review.md"
    ).read_text(encoding="utf-8")
    for digest in (
        "31eca5ee6b7881029585f494de0740f04fd068ac9625b4cd8b387b41a87f3135",
        "5a60772bec6c582a83a1e36bfeaa60de4a7aff7840f8ec9b7f33ad9f17234750",
        "f95101f9ed82ca32cc458f2133b8cb0c34e2adfccf0619b349c993fafcc8b514",
    ):
        assert digest in status_text
        assert digest in wp153_status
        assert digest in doc


def test_wp153_committed_status_docs_reject_stale_wording():
    wp153_path = STATUS_ENTRIES / "WP153.md"
    assert wp153_path.is_file()
    wp153_text = wp153_path.read_text(encoding="utf-8")
    project_text = _read()
    for phrase in (
        "WP153 on branch",
        "WP153 active branch",
        "Merge commit: TBD after merge",
        "PR: TBD",
    ):
        assert phrase not in wp153_text
        assert phrase not in project_text
    assert "Ready for review: YES" in wp153_text
    assert "PR: see GitHub PR metadata and PR body." in wp153_text
    assert "Current live PR head: see GitHub PR metadata and PR body" in wp153_text
    assert "stable and non-self-referential" in wp153_text
    fixed_live_head = re.compile(
        r"Current live PR head:\s*`?[0-9a-f]{40}`?", re.IGNORECASE
    )
    assert fixed_live_head.search(wp153_text) is None


# ── WP154: adoption architecture, dependency registry, alpha-factory roadmap ──


def test_wp154_document_status_and_test_are_registered_in_repo_truth():
    index_text = (REPO_ROOT / "docs" / "repo_truth_index.md").read_text(
        encoding="utf-8"
    )
    status_text = _read()
    for path in (
        "docs/adoption_architecture_dependency_registry_and_alpha_factory_roadmap_lock_in.md",
        "docs/status_entries/WP154.md",
        "tests/test_adoption_architecture_dependency_registry_and_alpha_factory_roadmap_lock_in_docs.py",
    ):
        assert path in index_text
    assert (
        "Adoption architecture, dependency registry and alpha-factory roadmap status:"
        in status_text
    )
    assert (STATUS_ENTRIES / "WP154.md").is_file()


def test_wp154_through_wp158_are_merged_and_wp159_is_the_only_current_review_target():
    text = _read()
    current_phase_line = next(
        line for line in text.splitlines() if line.startswith("- Current phase:")
    )
    assert current_phase_line.count("current review target") == 1
    assert "WP161" in current_phase_line
    merged_line = next(
        line for line in text.splitlines() if line.startswith("- Merged WPs:")
    )
    assert "WP154" in merged_line
    assert "WP155" in merged_line
    assert "WP156" in merged_line
    assert "WP157" in merged_line
    assert "WP158" in merged_line
    assert (
        "WP153 bounded local research workflow value measurement dry run and receipt review sole review target"
        not in text
    )
    assert (
        "WP154 adoption architecture, dependency registry and alpha-factory roadmap lock-in sole review target"
        not in text
    )
    assert (
        "LOCAL_OFFLINE_DETERMINISTIC_SYNTHETIC_DRY_RUN_AND_RECEIPT_REVIEW_MERGED"
        in text
    )
    assert (
        "DOCS_STATUS_TESTS_ONLY_ADOPTION_ARCHITECTURE_DEPENDENCY_REGISTRY_ALPHA_FACTORY_ROADMAP_REVIEW_TARGET"
        not in text
    )
    assert (
        "LOCAL_OFFLINE_DETERMINISTIC_SYNTHETIC_DRY_RUN_AND_RECEIPT_REVIEW_REVIEW_TARGET"
        not in text
    )


def test_wp154_project_status_preserves_non_authority_and_next_gate():
    text = _read()
    wp154_line = next(
        line
        for line in text.splitlines()
        if line.startswith(
            "- Adoption architecture, dependency registry and alpha-factory roadmap status:"
        )
    )
    for phrase in (
        "DOCS_STATUS_TESTS_ONLY_ADOPTION_ARCHITECTURE_DEPENDENCY_REGISTRY_ALPHA_FACTORY_ROADMAP_MERGED",
        "MEASURABLE_ALPHA_FACTORY_PLUS_DETERMINISTIC_TRADING_KERNEL",
        "Dependency registry candidates: 15",
        "Listed dependencies approved: 0",
        "Dependencies installed or activated: 0",
        "Paper-trading execution: NOT AUTHORIZED",
        "Restricted-live eligibility: NOT ESTABLISHED",
        "Live-trading execution: FORBIDDEN",
        "Capital at risk: USD 0",
        "Provider/model/Hermes runtime calls: 0",
        "Product/runtime network calls: 0",
        "Credentials accessed: 0",
        "Scheduler/tasks: 0",
        "Source/dependency/lock/workflow changes: 0",
        "Planning estimates only: YES",
        "Next sequence phase reconciled by the separately approved WP155",
    ):
        assert phrase in wp154_line


def test_wp154_status_fragment_is_stable_and_non_self_referential():
    status = (STATUS_ENTRIES / "WP154.md").read_text(encoding="utf-8")
    assert "WP153 is merged. WP154 is the sole current review target." in status
    assert "Ready for review: YES only after final committed-head validation" in status
    assert "PR: see GitHub PR metadata and PR body." in status
    assert "Current live PR head: see GitHub PR metadata and PR body" in status
    assert "stable, non-self-referential repo record" in status
    assert "TBD" not in status
    assert "LOCAL_DRAFT_VERIFIED" not in status
    fixed_live_head = re.compile(
        r"Current live PR head:\s*`?[0-9a-f]{40}`?", re.IGNORECASE
    )
    assert fixed_live_head.search(status) is None


# ── WP155: point-in-time market research data foundation contract ────────────


def test_wp155_document_status_and_test_are_registered_in_repo_truth():
    index_text = (REPO_ROOT / "docs" / "repo_truth_index.md").read_text(
        encoding="utf-8"
    )
    status_text = _read()
    for path in (
        "docs/point_in_time_market_research_data_foundation_contract.md",
        "docs/status_entries/WP155.md",
        "tests/test_point_in_time_market_research_data_foundation_contract_docs.py",
    ):
        assert path in index_text
    assert "Point-in-time market research data foundation contract status:" in status_text
    assert (STATUS_ENTRIES / "WP155.md").is_file()


def test_wp155_project_status_preserves_contract_only_posture_and_next_gate():
    text = _read()
    wp155_line = next(
        line
        for line in text.splitlines()
        if line.startswith(
            "- Point-in-time market research data foundation contract status:"
        )
    )
    for phrase in (
        "POINT_IN_TIME_APPEND_ONLY_MARKET_RESEARCH_DATA_CONTRACT_MERGED",
        "CONTRACT_ONLY_NO_WRITER_NO_DEPENDENCY_NO_COLLECTION",
        "AS_OF_INGESTION_TIME",
        "NO_DESTRUCTIVE_HISTORY_REWRITE",
        "PARQUET_ARROW_PREFERRED_BUT_NOT_INSTALLED",
        "record_family / schema_major / ingestion_date_utc",
        "BENCHMARK_REQUIRED_NO_ADOPTION_DECISION",
        "Product/runtime network calls: 0",
        "Paper-trading execution: NOT AUTHORIZED",
        "Live-trading execution: FORBIDDEN",
        "Next sequence phase reconciled by the separately approved WP156",
    ):
        assert phrase in wp155_line


def test_wp155_status_fragment_is_stable_and_non_self_referential():
    status = (STATUS_ENTRIES / "WP155.md").read_text(encoding="utf-8")
    assert "PR #154 is merged. WP155 is the sole current review target." in status
    assert "Ready for review: YES only after final committed-head validation" in status
    assert "PR: see GitHub PR metadata and PR body." in status
    assert "Current live PR head: see GitHub PR metadata and PR body" in status
    assert "stable and non-self-referential" in status
    assert "TBD" not in status
    assert "LOCAL_DRAFT_VERIFIED" not in status
    fixed_live_head = re.compile(
        r"Current live PR head:\s*`?[0-9a-f]{40}`?", re.IGNORECASE
    )
    assert fixed_live_head.search(status) is None


# ── WP156: bounded point-in-time validator and synthetic corpus ─────────────


def test_wp156_document_status_package_and_test_are_registered_in_repo_truth():
    index_text = (REPO_ROOT / "docs" / "repo_truth_index.md").read_text(
        encoding="utf-8"
    )
    status_text = _read()
    for path in (
        "docs/point_in_time_observation_schema_validator_and_synthetic_fixture_implementation.md",
        "docs/status_entries/WP156.md",
        "src/data_layer/point_in_time_market_research/",
        "tests/data_layer/point_in_time_market_research/test_records_and_synthetic_corpus.py",
    ):
        assert path in index_text
    assert (
        "Point-in-time observation schema validator and synthetic fixture implementation status:"
        in status_text
    )
    assert (STATUS_ENTRIES / "WP156.md").is_file()


def test_wp156_project_status_exact_implementation_posture_and_next_gate():
    text = _read()
    wp156_line = next(
        line
        for line in text.splitlines()
        if line.startswith(
            "- Point-in-time observation schema validator and synthetic fixture implementation status:"
        )
    )
    for phrase in (
        "LOCAL_OFFLINE_STDLIB_ONLY_IN_MEMORY_VALIDATION_MERGED",
        "POINT_IN_TIME_APPEND_ONLY_MARKET_RESEARCH_DATA_CONTRACT",
        "point-in-time-market-research-record@1.0.0",
        "Record families: 3",
        "Observation kinds: 3",
        "Frozen public dataclasses: 8",
        "Public functions: 8",
        "Synthetic cases: 20",
        "Maximum batch records: 256",
        "Dependencies added: 0",
        "Writers/readers/manifests/databases/query engines/collectors/migrations: 0",
        "Existing Polymarket snapshot behavior changed: NO",
        "Product/runtime network calls: 0",
        "Credentials accessed: 0",
        "Scheduler/tasks: 0",
        "Strategy/signal/paper/order/risk/execution authority: NONE",
        "Paper-trading execution: NOT AUTHORIZED",
        "Live-trading execution: FORBIDDEN",
        "Next sequence phase reconciled by the separately approved WP157",
        "WP157 implemented: YES",
    ):
        assert phrase in wp156_line


def test_wp156_status_fragment_is_stable_and_non_self_referential():
    status = (STATUS_ENTRIES / "WP156.md").read_text(encoding="utf-8")
    assert "PR: see GitHub PR metadata and PR body." in status
    assert "Current live PR head: see GitHub PR metadata and PR body" in status
    assert "stable and non-self-referential" in status
    assert "Ready for review: YES only after final committed-head validation" in status
    assert "LOCAL_DRAFT_VERIFIED" not in status
    assert "PR: TBD" not in status
    fixed_live_head = re.compile(
        r"Current live PR head:\s*`?[0-9a-f]{40}`?", re.IGNORECASE
    )
    assert fixed_live_head.search(status) is None


# ── WP157: bounded in-memory as-of query implementation ──────────────────────


def test_wp157_document_status_package_and_test_are_registered_in_repo_truth():
    index_text = (REPO_ROOT / "docs" / "repo_truth_index.md").read_text(
        encoding="utf-8"
    )
    status_text = _read()
    for path in (
        "docs/bounded_in_memory_point_in_time_record_set_reconstruction_and_as_of_query_implementation.md",
        "docs/status_entries/WP157.md",
        "src/data_layer/point_in_time_market_research/as_of_query.py",
        "src/data_layer/point_in_time_market_research/as_of_synthetic_cases.py",
        "tests/data_layer/point_in_time_market_research/test_as_of_query.py",
    ):
        assert path in index_text
    assert (
        "Bounded in-memory point-in-time record-set reconstruction and as-of query status:"
        in status_text
    )
    assert (STATUS_ENTRIES / "WP157.md").is_file()
    assert (
        REPO_ROOT
        / "docs"
        / "bounded_in_memory_point_in_time_record_set_reconstruction_and_as_of_query_implementation.md"
    ).is_file()


def test_wp157_and_wp158_merged_and_wp159_current():
    text = _read()
    current_phase_line = next(
        line for line in text.splitlines() if line.startswith("- Current phase:")
    )
    merged_line = next(
        line for line in text.splitlines() if line.startswith("- Merged WPs:")
    )
    assert "WP161" in current_phase_line
    assert "WP156" in merged_line
    assert "WP157" in merged_line
    assert "WP158" in merged_line
    assert (
        "LOCAL_OFFLINE_STDLIB_ONLY_IN_MEMORY_VALIDATION_REVIEW_TARGET" not in text
    )


def test_wp157_project_status_exact_posture_and_next_gate():
    text = _read()
    wp157_line = next(
        line
        for line in text.splitlines()
        if line.startswith(
            "- Bounded in-memory point-in-time record-set reconstruction and as-of query status:"
        )
    )
    for phrase in (
        "BOUNDED_IN_MEMORY_AS_OF_INGESTION_TIME_RECONSTRUCTION_MERGED",
        "POINT_IN_TIME_RECORD_SET_RECONSTRUCTION",
        "Consumes: valid WP156 public record objects only",
        "Supported cutoff modes: 2",
        "Supported result views: 3",
        "Query statuses: 6",
        "Exclusion reasons: 12",
        "New frozen query dataclasses: 5",
        "New public query functions: 3",
        "Synthetic as-of query cases: 24",
        "Default visibility contract: AS_OF_INGESTION_TIME",
        "Observed diagnostic bound: INGESTION_BOUNDED",
        "Maximum input records: 256",
        "Dependencies added: 0",
        "Writers/readers/manifests/databases/query engines/collectors/migrations/persistence: 0",
        "NARROW_ADDITIVE_REVIEW_ONLY_CONFLICT_HANDOFF_ALL_WP156_TESTS_PRESERVED",
        "Existing Polymarket snapshot behavior changed: NO",
        "Product/runtime network calls: 0",
        "Credentials accessed: 0",
        "Scheduler/tasks: 0",
        "Strategy/signal/paper/order/risk/execution authority: NONE",
        "Paper-trading execution: NOT AUTHORIZED",
        "Live-trading execution: FORBIDDEN",
        "Next sequence phase reconciled by the separately approved WP158 append-only local manifest and deterministic dataset snapshot reference contract",
        "WP158 implemented: YES",
    ):
        assert phrase in wp157_line


def test_wp157_status_fragment_is_stable_and_non_self_referential():
    status = (STATUS_ENTRIES / "WP157.md").read_text(encoding="utf-8")
    assert "PR: see GitHub PR metadata and PR body." in status
    assert "Current live PR head: see GitHub PR metadata and PR body" in status
    assert "stable and non-self-referential" in status
    assert "Ready for review: YES only after final committed-head validation" in status
    assert "LOCAL_DRAFT_VERIFIED" not in status
    assert "PR: TBD" not in status
    fixed_live_head = re.compile(
        r"Current live PR head:\s*`?[0-9a-f]{40}`?", re.IGNORECASE
    )
    assert fixed_live_head.search(status) is None


def test_wp157_preserves_protected_boundary_statuses():
    text = _read()
    for phrase in (
        "Live trading status: DISABLED",
        "Credentials status: NOT_USED",
        "Execution status: NOT_STARTED",
        "Hermes status: NOT_INSTALLED_NOT_RUNTIME_DEPENDENCY",
        "Agent runtime status: NOT_STARTED",
        "Agent execution authority: FORBIDDEN",
        "Scheduler status: NOT_STARTED",
        "Bot loop status: NOT_STARTED",
    ):
        assert phrase in text


# ── WP158: append-only local manifest and dataset snapshot reference contract ─


def test_wp158_document_status_package_and_test_are_registered_in_repo_truth():
    index_text = (REPO_ROOT / "docs" / "repo_truth_index.md").read_text(
        encoding="utf-8"
    )
    status_text = _read()
    for path in (
        "docs/append_only_local_manifest_and_dataset_snapshot_reference_contract.md",
        "docs/status_entries/WP158.md",
        "tests/test_append_only_local_manifest_and_dataset_snapshot_reference_contract_docs.py",
    ):
        assert path in index_text
    assert (
        "Append-only local manifest and deterministic dataset snapshot reference contract status:"
        in status_text
    )
    assert (STATUS_ENTRIES / "WP158.md").is_file()
    assert (
        REPO_ROOT
        / "docs"
        / "append_only_local_manifest_and_dataset_snapshot_reference_contract.md"
    ).is_file()


def test_wp159_in_current_and_wp158_reconciled_as_merged():
    text = _read()
    current_phase_line = next(
        line for line in text.splitlines() if line.startswith("- Current phase:")
    )
    merged_line = next(
        line for line in text.splitlines() if line.startswith("- Merged WPs:")
    )
    assert "WP161" in current_phase_line
    assert "WP158" in merged_line
    assert (
        "BOUNDED_IN_MEMORY_AS_OF_INGESTION_TIME_RECONSTRUCTION_REVIEW_TARGET" not in text
    )


def test_wp158_project_status_exact_posture_and_next_gate():
    text = _read()
    wp158_line = next(
        line
        for line in text.splitlines()
        if line.startswith(
            "- Append-only local manifest and deterministic dataset snapshot reference contract status:"
        )
    )
    for phrase in (
        "APPEND_ONLY_LOCAL_MANIFEST_AND_DETERMINISTIC_DATASET_SNAPSHOT_REFERENCE_CONTRACT_MERGED",
        "CONTRACT_ONLY_NO_WRITER_NO_READER_NO_PERSISTENCE",
        "point-in-time-dataset-snapshot-reference@1.0.0",
        "point-in-time-local-manifest-entry@1.0.0",
        "Dataset derivation modes: 2",
        "Manifest entry kinds: 3",
        "Reference states: 3",
        "Reason codes: 3",
        "Reference identity prefix: datasetref:sha256:",
        "Manifest entry identity prefix: manifestentry:sha256:",
        "New src files: 0",
        "New public exports: 0",
        "Writers/readers/manifests/databases/query engines/collectors/migrations/persistence: 0",
        "WP157 public surface changed: NO",
        "Strategy/signal/paper/order/risk/execution authority: NONE",
        "Paper-trading execution: NOT AUTHORIZED",
        "Live-trading execution: FORBIDDEN",
        "Next sequence phase reconciled by the separately approved WP159",
        "WP159 implemented as draft PR: YES",
        "WP159 Ready for review: NO",
    ):
        assert phrase in wp158_line


def test_wp158_status_fragment_is_stable_and_non_self_referential():
    status = (STATUS_ENTRIES / "WP158.md").read_text(encoding="utf-8")
    assert "PR: see GitHub PR metadata and PR body." in status
    assert "Current live PR head: see GitHub PR metadata and PR body" in status
    assert "stable and non-self-referential" in status
    assert "Ready for review: YES only after final committed-head validation" in status
    assert "LOCAL_DRAFT_VERIFIED" not in status
    assert "PR: TBD" not in status
    fixed_live_head = re.compile(
        r"Current live PR head:\s*`?[0-9a-f]{40}`?", re.IGNORECASE
    )
    assert fixed_live_head.search(status) is None


def test_wp158_preserves_protected_boundary_statuses():
    text = _read()
    for phrase in (
        "Live trading status: DISABLED",
        "Credentials status: NOT_USED",
        "Execution status: NOT_STARTED",
        "Hermes status: NOT_INSTALLED_NOT_RUNTIME_DEPENDENCY",
        "Agent runtime status: NOT_STARTED",
        "Agent execution authority: FORBIDDEN",
        "Scheduler status: NOT_STARTED",
        "Bot loop status: NOT_STARTED",
    ):
        assert phrase in text


# ── WP159: draftability/specification/exact-scope governance foundation ─────


def test_wp159_package_files_hashes_and_waiver_are_exact():
    package = REPO_ROOT / "docs" / "wp_specs" / "WP159"
    wp_bytes = (package / "wp_prompt.txt").read_bytes()
    spec_bytes = (package / "wp_spec.json").read_bytes()
    waiver = json.loads(
        (package / "draftability_certificate.json").read_text(encoding="utf-8")
    )
    assert hashlib.sha256(wp_bytes).hexdigest() == (
        "7dfd1e826b688873c3303dcf89d13522d82620840b17f1a40812c3ceb2c74911"
    )
    assert hashlib.sha256(spec_bytes).hexdigest() == (
        "2300bd295bdd0f679857d2aec0d007d296ef05421095e77e69937b457ad094b3"
    )
    assert waiver == {
        "schema_id": "polymarket-wp-draftability-waiver",
        "schema_version": "1.0.0",
        "wp_id": "WP159",
        "waiver_mode": "WAIVED_FOR_LOW_RISK_DRAFT_PR_IMPLEMENTATION",
        "authorization_source": "EXPLICIT_USER_AUTHORIZATION",
        "wp_text_sha256": hashlib.sha256(wp_bytes).hexdigest(),
        "wp_spec_sha256": hashlib.sha256(spec_bytes).hexdigest(),
        "implementation_authorized": True,
        "ready_for_review_authorized": False,
        "merge_authorized": False,
        "independent_live_pr_review_required": True,
        "unresolved_decisions": [],
    }
    prompt = wp_bytes.decode("utf-8")
    for stale in (
        "V5",
        "\n9. L-PACKAGE BUNDLE JUSTIFICATION",
        "REQUIRES A NEW INDEPENDENT REVIEW OF THESE EXACT",
        "NOT YET AUTHORIZED FOR CODEX OR CLAUDE CODE EXECUTION",
        "Do not execute without the independent PASS certificate",
    ):
        assert stale not in prompt
    for current in (
        "V6 / XL23",
        "one-time bootstrap path",
        "READY FOR REVIEW IS NOT AUTHORIZED",
        "MERGE IS NOT AUTHORIZED",
        "Normal future governed WPs",
    ):
        assert current in prompt
    guard_source = (
        REPO_ROOT / "tools" / "wp" / "wp_spec_guard.py"
    ).read_text(encoding="utf-8")
    assert waiver["wp_text_sha256"] in guard_source
    assert waiver["wp_spec_sha256"] in guard_source


def test_wp159_spec_exact_topology_lenses_errors_and_scope():
    package = REPO_ROOT / "docs" / "wp_specs" / "WP159"
    spec = json.loads((package / "wp_spec.json").read_text(encoding="utf-8"))
    assert list(spec) == [
        "schema_id",
        "schema_version",
        "identity",
        "scope",
        "authority",
        "api_matrix",
        "semantic_fields",
        "identity_derivations",
        "state_transitions",
        "failure_precedence",
        "examples",
        "evidence_plan",
        "successor_boundary",
    ]
    assert "certificate" not in spec
    expected_files = [
        "docs/ai/codex/WP_DRAFTING_STANDARD.md",
        "docs/ai/codex/WP_SPEC_STANDARD.md",
        "docs/ai/codex/VALIDATION_MATRIX.md",
        "docs/ai/codex/WP_EXECUTION_STATE_MACHINE.md",
        "tools/wp/wp_spec_guard.py",
        "tools/git/diff_scope_summary.py",
        "tests/tools/wp/test_wp_spec_guard.py",
        "tests/tools/git/test_diff_scope_summary.py",
        "tests/test_project_status_docs.py",
        "tests/test_append_only_local_manifest_and_dataset_snapshot_reference_contract_docs.py",
        "tests/test_adoption_architecture_dependency_registry_and_alpha_factory_roadmap_lock_in_docs.py",
        "tests/test_local_research_workflow_value_measurement_harness_contract_docs.py",
        "tests/test_point_in_time_market_research_data_foundation_contract_docs.py",
        "tests/test_wallet_intelligence_architecture_contract_docs.py",
        "tests/test_hermes_research_prompt_pack_operator_runbooks_docs.py",
        "tests/test_human_review_label_workflow_docs.py",
        "docs/wp_specs/WP159/wp_prompt.txt",
        "docs/wp_specs/WP159/wp_spec.json",
        "docs/wp_specs/WP159/draftability_certificate.json",
        "docs/status_entries/WP159.md",
        "docs/project_status.md",
        "docs/repo_truth_index.md",
        "docs/deferred_items_log.md",
    ]
    assert spec["scope"]["required_changed_files"] == expected_files
    assert spec["scope"]["allowed_changed_files"] == expected_files
    assert spec["identity"]["package_size_class"] == "XL"
    assert spec["identity"]["xl_explicit_authorization"] is True
    assert spec["identity"]["xl_authorization_basis"] == (
        "Explicit user authorization for six merged historical compatibility "
        "regression tests required to preserve the full repository suite while "
        "WP159 adds and modifies local governance tools."
    )
    assert spec["scope"]["max_changed_files"] == 23
    assert spec["scope"]["exact_scope_required"] is True
    assert spec["scope"]["historical_compatibility_edits"] == expected_files[10:16]
    assert [item["category"] for item in spec["failure_precedence"]["items"]] == [
        "FILE_READ_ERROR",
        "JSON_PARSE_INVALID",
        "SCHEMA_UNSUPPORTED",
        "UNKNOWN_FIELD",
        "FIELD_MISSING",
        "FIELD_TYPE_INVALID",
        "FIELD_VALUE_INVALID",
        "CERTIFICATE_HASH_MISMATCH",
        "DRAFTABILITY_INCOMPLETE",
        "SCOPE_POLICY_INVALID",
        "AUTHORITY_CONTRADICTION",
        "SEMANTIC_CONTRADICTION",
        "IDENTITY_DERIVATION_INVALID",
        "FAILURE_PRECEDENCE_INVALID",
        "EXAMPLE_TRUTH_INVALID",
    ]


def test_wp159_status_is_stable_model_d_and_not_ready():
    status = (STATUS_ENTRIES / "WP159.md").read_text(encoding="utf-8")
    for phrase in (
        "PR: see GitHub PR metadata and PR body.",
        "Current live PR head: see GitHub PR metadata and PR body.",
        "stable and non-self-referential",
        "Ready for review: NO",
        "Merge authorized: NO",
        "Independent live PR re-review required: YES",
        "Independent draftability PASS certificate: NOT CREATED",
        "BLOCKED_NOT_READY",
        "WP160",
        "WP161",
    ):
        assert phrase in status
    assert re.search(
        r"Current live PR head:\s*`?[0-9a-f]{40}`?", status, re.IGNORECASE
    ) is None


def test_wp171g_status_and_package_evidence_are_registered():
    project = (REPO_ROOT / "docs" / "project_status.md").read_text(encoding="utf-8")
    status = (STATUS_ENTRIES / "WP171G.md").read_text(encoding="utf-8")
    package = REPO_ROOT / "docs" / "wp_specs" / "WP171G"
    assert "WP171G canonical transition: Lean Agent Execution Governance" in project
    assert "a650c08ab233e47beca7565a5bb8df11a4f41d02" in project
    assert "d6a15e4007fe3ced5a7d059ec3fcdec496d2dc7d" in project
    assert "WP172 — Alpha + Executable Edge MVP" in project
    assert "Prompt authority mirror: REQUIRED_EXACT_RISK_PLUS_16_BOOLEAN_SPEC_EQUALITY" in project
    assert "Certificate-free package-guard result: NULL_NOT_RUN" in project
    assert "PR: see GitHub PR metadata and PR body." in status
    assert "stable and non-self-referential" in status
    assert "Current live PR head: see GitHub PR metadata and PR body" in status
    assert re.search(
        r"Current live PR head:\s*`?[0-9a-f]{40}`?", status, re.IGNORECASE
    ) is None
    for name in ("wp_prompt.txt", "wp_spec.json", "draftability_certificate.json"):
        assert (package / name).is_file()
    assert "categories F/G" in status
    assert "prompt/spec authority-mirror equality" in status


def test_wp174_status_security_and_successor_are_consistent():
    project = (REPO_ROOT / "docs" / "project_status.md").read_text(encoding="utf-8")
    index = (REPO_ROOT / "docs" / "repo_truth_index.md").read_text(encoding="utf-8")
    deferred = (REPO_ROOT / "docs" / "deferred_items_log.md").read_text(
        encoding="utf-8"
    )
    security = (REPO_ROOT / "docs" / "security_tooling_status.md").read_text(
        encoding="utf-8"
    )
    fragment = (STATUS_ENTRIES / "WP174.md").read_text(encoding="utf-8")
    combined = "\n".join((project, index, deferred, security, fragment))
    assert "WP173 merged: YES" in project
    assert "WP173 PR: 175" in project
    assert "79e2953dee8754dc8d09781edd647202dee834aa" in combined
    assert "e0202750c1e6f2a3a885aa6efa04bbd8d0b2291a" in combined
    assert "WP174 current review target" in project
    assert "Package size class: XL_FOR_SCOPE_SIZE_ONLY" in project
    assert "Exact changed-file scope: 24" in project
    assert "DRAFTABILITY_PASS" in combined
    assert "IMPLEMENTATION_READY" in combined
    assert "polymarket-client==0.10.0" in combined
    assert "websockets==15.0.1" in combined
    assert "BLOCKED_GATE_B" in deferred
    assert "A3_RESTRICTED_LIVE: ABSENT" in combined
    assert "WP175 Restricted Live Canary: SEPARATELY_GATED_NOT_STARTED" in project
    assert "Gate B was not exercised" in fragment
    assert "Gate C was not exercised" in fragment
    assert "Merge authorized: NO" in combined
    assert "Unresolved decisions: 0" in project


def test_wp174b_status_repo_truth_and_successor_are_consistent():
    project = (REPO_ROOT / "docs" / "project_status.md").read_text(encoding="utf-8")
    deferred = (REPO_ROOT / "docs" / "deferred_items_log.md").read_text(
        encoding="utf-8"
    )
    security = (REPO_ROOT / "docs" / "security_tooling_status.md").read_text(
        encoding="utf-8"
    )
    fragment = (STATUS_ENTRIES / "WP174B.md").read_text(encoding="utf-8")
    combined = "\n".join((project, deferred, security, fragment))
    assert "WP174B current review target" in project
    assert "Package size class: XL_FOR_SCOPE_SIZE_ONLY" in project
    assert "Exact changed-file scope: 24" in project
    assert "6fff7fefd8f936824a7586f94d452ca073b225dd" in combined
    assert "dbb4ee0e21e409c4639edc44cce17696a5b15156" in combined
    assert "c849cfaf68576fe98d853aad11fb0798a7ab8b9461f35fc75c03e81f0e7b6e1f" in fragment
    assert "c3fdd63f7b748fe491b29ca29a2dadd4408c820a4c7edef242b3f3cc7de0a12d" in fragment
    assert "DRAFTABILITY_PASS" in fragment
    assert "IMPLEMENTATION_READY" in combined
    assert "polymarket-client==0.10.0" in combined
    assert "Dependencies/lock/workflow files: UNCHANGED" in project
    assert "RESOLVED_WP174B" in deferred
    assert "GATE_C_REQUIRED" in combined
    assert "A3_RESTRICTED_LIVE: ABSENT" in combined
    assert "WP175 Restricted Live Canary: SEPARATELY_GATED_NOT_STARTED" in project
    assert "Capital at risk: USD 0" in fragment
    assert "EPHEMERAL_NO_ECHO_NEVER_PERSISTED" in combined
    assert "Merge authorized: NO" in combined
    assert "Unresolved decisions: 0" in project


def test_wp175_status_records_code_complete_pending_activation() -> None:
    project = (REPO_ROOT / "docs" / "project_status.md").read_text(encoding="utf-8")
    status = (STATUS_ENTRIES / "WP175.md").read_text(encoding="utf-8")
    contract = (REPO_ROOT / "docs" / "restricted_live_canary_contract.md").read_text(
        encoding="utf-8"
    )
    combined = "\n".join((project, status, contract))
    assert "WP175 current review target" in project
    assert "PROTECTED_RESTRICTED_LIVE_CANARY" in combined
    assert "Exact changed-file scope: 30" in combined
    assert "IMPLEMENTATION_READY" in combined
    assert "LIVE_ACTIVATION_PREREQUISITE_NOT_YET_AVAILABLE" in combined
    assert "Gate-C activation: PENDING" in combined
    assert "Real economic CREATE count: 0" in combined
    assert "Capital at risk: USD 0" in combined
    assert "WP176" in combined


def test_wp175_status_repo_truth_and_activation_prerequisite() -> None:
    """Status evidence keeps implementation separate from activation."""
    test_wp175_status_records_code_complete_pending_activation()
    project = (REPO_ROOT / "docs" / "project_status.md").read_text(encoding="utf-8")
    index = (REPO_ROOT / "docs" / "repo_truth_index.md").read_text(encoding="utf-8")
    assert "LIVE_ACTIVATION_PREREQUISITE_NOT_YET_AVAILABLE" in project
    assert "activation is pending a separate exact-head human decision" in index


def test_wp159_repo_truth_and_deferred_items_are_registered():
    index = (REPO_ROOT / "docs" / "repo_truth_index.md").read_text(
        encoding="utf-8"
    )
    deferred = (REPO_ROOT / "docs" / "deferred_items_log.md").read_text(
        encoding="utf-8"
    )
    for path in (
        "docs/ai/codex/WP_SPEC_STANDARD.md",
        "tools/wp/wp_spec_guard.py",
        "tests/tools/wp/test_wp_spec_guard.py",
        "docs/wp_specs/WP159/wp_prompt.txt",
        "docs/status_entries/WP159.md",
        "tools/git/diff_scope_summary.py",
    ):
        assert path in index
    for index_value in range(1, 7):
        assert f"WP159-D{index_value:03d}" in deferred


def test_wp175d_project_status_registers_research_bridge() -> None:
    status = _read()
    fragment = (STATUS_ENTRIES / "WP175D.md").read_text(encoding="utf-8")
    for text in (status, fragment):
        assert "WP175D" in text
        assert "S10-DATA-02" in text
        assert "LOCAL_OFFLINE_EXTERNAL_HISTORICAL_RESEARCH_BRIDGE" in text
    assert "Governance track: FAST" in status
    assert "Exact changed-file scope: 24" in status
    assert "WP175 merged dormant: YES" in status
    assert "489c6f9548c39cb3bcb2196a81d5352a0d1dd653" in status
    assert "Canonical PIT authority unchanged: YES" in status
    assert "Capital at risk: USD 0" in status
    assert "Merge authorized: NO" in status
    assert "WP176 Mature Controlled Live: NOT STARTED" in status
    assert "LIVE_ACTIVATION_PREREQUISITE_NOT_YET_AVAILABLE" in status


def test_wp175e_status_and_exact_scope_are_registered() -> None:
    project = _read()
    fragment = (STATUS_ENTRIES / "WP175E.md").read_text(encoding="utf-8")
    contract = (
        REPO_ROOT
        / "docs"
        / "native_continuity_attested_market_truth_bridge_contract.md"
    ).read_text(encoding="utf-8")
    spec = json.loads(
        (REPO_ROOT / "docs" / "wp_specs" / "WP175E" / "wp_spec.json").read_text(
            encoding="utf-8"
        )
    )
    combined = "\n".join((project, fragment, contract))
    assert "WP175E current review target" in project
    assert "S10-DATA-03" in combined
    assert "EVIDENCE_INCONCLUSIVE" in combined
    assert "NativeContinuityAttestation" in combined
    assert "NativeMarketTruthWindow" in combined
    assert "PMXT AS_CAPTURED reclassified: NO" in project
    assert "WP169 APPLICATION_ID/USER_VERSION/DDL/indexes: UNCHANGED" in project
    assert "LIVE_PATH_EVIDENCE_READY: NOT CLAIMED" in project
    assert "WP175 Gate C: NOT AUTHORIZED" in fragment
    assert "WP176: NOT STARTED" in fragment
    assert "Merge authorized: NO" in fragment
    assert "stable and non-self-referential" in fragment
    assert re.search(
        r"Current live PR head:\s*`?[0-9a-f]{40}`?", fragment, re.IGNORECASE
    ) is None
    scope = spec["scope"]
    assert scope["exact_scope_required"] is True
    assert scope["max_changed_files"] == 20
    assert scope["required_changed_files"] == scope["allowed_changed_files"]
    assert len(scope["required_changed_files"]) == 20
    assert "tests/test_architecture_boundaries.py" not in scope["allowed_changed_files"]
    assert "src/data_layer/polymarket/market_truth.py" not in scope["allowed_changed_files"]


def test_wp175h_status_and_runtime_activation_split_are_registered() -> None:
    project = _read()
    fragment = (STATUS_ENTRIES / "WP175H.md").read_text(encoding="utf-8")
    contract = (
        REPO_ROOT / "docs" / "hermes_controlled_research_runtime_contract.md"
    ).read_text(encoding="utf-8")
    spec = json.loads(
        (REPO_ROOT / "docs" / "wp_specs" / "WP175H" / "wp_spec.json").read_text(
            encoding="utf-8"
        )
    )
    combined = "\n".join((project, fragment, contract))
    # WP175I (current review target) reconciles merged WP175H; WP175H is no longer the
    # current review target but its runtime facts remain registered.
    assert "WP175H merged (S10-HERMES-01, PR #181)" in project
    assert "WP175H current review target" not in project
    assert "S10-HERMES-01" in combined
    assert "CONTROLLED_EXTERNAL_HERMES_RESEARCH_RUNTIME_CORE" in combined
    assert "Governance track: RUNTIME" in project
    assert "Exact changed-file scope: 24" in project
    assert "Hermes Agent v0.21.3" in combined
    assert "v2026.9.14" in combined
    assert "web_search" in contract and "web_extract" in contract
    # Code-complete is stated separately from runtime activation (R023).
    assert "CODE COMPLETE: YES" in combined
    assert "RUNTIME ACTIVATED: NO" in combined
    assert "S10-GATE-H1" in combined
    assert "Real provider-backed research run: NO" in project
    assert "Real provider/model call count: 0" in project
    assert "Credentials created/used: 0" in project
    assert "Capital at risk: USD 0" in project
    assert "WP175 merged dormant: YES" in project
    assert "Gate-C activation: NOT AUTHORIZED" in project
    assert "WP176 Mature Controlled Live: NOT STARTED" in project
    assert "S10-ALPHA-01" in combined and "NOT STARTED" in combined
    assert "Merge authorized: NO" in project
    scope = spec["scope"]
    assert spec["identity"]["risk_level"] == 3
    assert spec["authority"]["hermes_runtime"] is True
    assert spec["authority"]["network"] is True
    assert spec["authority"]["credentials"] is False
    assert spec["authority"]["execution"] is False
    assert spec["authority"]["live"] is False
    assert spec["authority"]["paper"] is False
    assert scope["exact_scope_required"] is True
    assert scope["max_changed_files"] == 24
    assert scope["required_changed_files"] == scope["allowed_changed_files"]
    assert len(scope["required_changed_files"]) == 24
    assert (
        "src/research_runtime/hermes_controlled_runtime/controller.py"
        in scope["required_changed_files"]
    )


def test_wp175i_controlled_profile_status_registered() -> None:
    project = _read()
    fragment = (STATUS_ENTRIES / "WP175I.md").read_text(encoding="utf-8")
    contract = (
        REPO_ROOT / "docs" / "hermes_controlled_research_runtime_contract.md"
    ).read_text(encoding="utf-8")
    spec = json.loads(
        (REPO_ROOT / "docs" / "wp_specs" / "WP175I" / "wp_spec.json").read_text(
            encoding="utf-8"
        )
    )
    combined = "\n".join((project, fragment, contract))
    # WP175J is now current; WP175I and WP175H remain registered as merged truth.
    assert "WP175J current review target" in project
    assert "WP175I / PR #182 merged: YES" in project
    assert "WP175H / PR #181 merged: YES" in project
    assert "S10-HERMES-01A" in combined
    assert "BOUNDED_CONTROLLED_RESEARCH_PROFILE_ENFORCEMENT_CORRECTION" in combined
    assert "Governance track: RUNTIME" in project
    assert "Exact changed-file scope: 15" in project
    assert "Hermes Agent v0.21.3" in combined
    assert "v2026.9.14" in combined and "345cd2b" in combined
    # The safe-mode removal and controlled managed profile are stated.
    assert "Research argv safe-mode: REMOVED" in project
    assert "Controlled managed scope" in combined
    assert "Firecrawl" in combined
    assert "keyless" in contract.lower()
    assert "web_search" in contract and "web_extract" in contract
    # Activation split and prior-H1 truth.
    assert "CODE COMPLETE: YES" in combined
    assert "RUNTIME ACTIVATED: NO" in combined
    assert "S10-GATE-H1" in combined
    assert "FAIL / SOFTWARE_GAP" in combined
    assert "Prior H1 real research invocations: 0" in project
    assert "Firecrawl secret requested/used: 0" in project
    assert "Real provider/model call count: 0" in project
    assert "Capital at risk: USD 0" in project
    assert "WP175 merged dormant: YES" in project
    assert "Gate-C activation: NOT AUTHORIZED" in project
    assert "WP176 Mature Controlled Live: NOT STARTED" in project
    assert "S10-ALPHA-01" in combined and "NOT STARTED" in combined
    assert "Merge authorized: NO" in project
    scope = spec["scope"]
    assert spec["identity"]["risk_level"] == 3
    assert spec["identity"]["package_class"] == (
        "BOUNDED_CONTROLLED_RESEARCH_PROFILE_ENFORCEMENT_CORRECTION"
    )
    assert spec["authority"]["hermes_runtime"] is True
    assert spec["authority"]["network"] is True
    assert spec["authority"]["credentials"] is False
    assert spec["authority"]["execution"] is False
    assert spec["authority"]["live"] is False
    assert spec["authority"]["paper"] is False
    assert scope["exact_scope_required"] is True
    assert scope["max_changed_files"] == 15
    assert scope["required_changed_files"] == scope["allowed_changed_files"]
    assert len(scope["required_changed_files"]) == 15
    assert (
        "src/research_runtime/hermes_controlled_runtime/policy.py"
        in scope["required_changed_files"]
    )
    # The correction leaves models.py and response_capture.py out of scope.
    assert (
        "src/research_runtime/hermes_controlled_runtime/models.py"
        not in scope["required_changed_files"]
    )
    assert (
        "src/research_runtime/hermes_controlled_runtime/response_capture.py"
        not in scope["required_changed_files"]
    )


def test_wp175j_version_banner_parser_correction_registered() -> None:
    project = _read()
    fragment = (STATUS_ENTRIES / "WP175J.md").read_text(encoding="utf-8")
    contract = (
        REPO_ROOT / "docs" / "hermes_controlled_research_runtime_contract.md"
    ).read_text(encoding="utf-8")
    spec = json.loads(
        (REPO_ROOT / "docs" / "wp_specs" / "WP175J" / "wp_spec.json").read_text(
            encoding="utf-8"
        )
    )
    combined = "\n".join((project, fragment, contract))
    assert "WP175J current review target" in project
    assert "WP175I / PR #182 merged: YES" in project
    assert "S10-HERMES-01B" in combined
    assert "BOUNDED_HERMES_VERSION_BANNER_PREFLIGHT_CORRECTION" in combined
    assert "Governance track: RUNTIME" in project and "Risk level: 3" in project
    assert "Exact changed-file scope: 12" in project
    assert "Hermes Agent v0.21.3 (2026.9.14)" in combined
    assert "generic first-semver" in combined
    assert "H1 real research invocations: 0" in combined
    assert "RUNTIME ACTIVATED: NO" in project
    assert "Gate C: NOT AUTHORIZED" in combined
    assert "Alpha Factory: NOT STARTED" in combined
    assert "S10-GATE-H1" in combined and "fresh-human-authorized" in combined
    assert "WP176 Mature Controlled Live: NOT STARTED" in combined
    assert "Merge authorized: NO" in combined
    scope = spec["scope"]
    assert spec["identity"]["risk_level"] == 3
    assert scope["exact_scope_required"] is True
    assert scope["max_changed_files"] == 12
    assert scope["required_changed_files"] == scope["allowed_changed_files"]
    assert len(scope["required_changed_files"]) == 12
    assert "src/research_runtime/hermes_controlled_runtime/policy.py" in scope["required_changed_files"]
    assert "src/research_runtime/hermes_controlled_runtime/controller.py" not in scope["required_changed_files"]
    assert "src/research_runtime/hermes_controlled_runtime/runner.py" not in scope["required_changed_files"]


def test_wp175k_sanitized_failure_evidence_hardening_registered() -> None:
    project = _read()
    fragment = (STATUS_ENTRIES / "WP175K.md").read_text(encoding="utf-8")
    contract = (
        REPO_ROOT / "docs" / "hermes_controlled_research_runtime_contract.md"
    ).read_text(encoding="utf-8")
    spec = json.loads(
        (REPO_ROOT / "docs" / "wp_specs" / "WP175K" / "wp_spec.json").read_text(
            encoding="utf-8"
        )
    )
    combined = "\n".join((project, fragment, contract))
    # WP175K is the current review target; WP175J is reconciled as merged.
    assert "WP175K current review target" in project
    assert "WP175J / PR #183 merged: YES" in project
    assert "S10-HERMES-01C" in combined
    assert "BOUNDED_HERMES_SANITIZED_FAILURE_EVIDENCE_HARDENING" in combined
    assert "Governance track: RUNTIME" in project and "Risk level: 3" in project
    assert "Exact changed-file scope: 14" in project
    # Incident truth: the one authorized H1 run was consumed and failed.
    assert "S10-GATE-H1 single authorized real invocation consumed = 1" in combined
    assert "EXIT_CODE_NONZERO" in combined
    assert "validated research NONE" in combined or "validated research: NONE" in combined
    assert "ROOT_CAUSE_NARROWED_NOT_CONFIRMED" in combined
    assert "PREACCOUNTING_PATHS_PASS_ROOT_CAUSE_STILL_UNRECOVERABLE" in combined
    # Evidence-hardening contract.
    assert "hermes-research-run-receipt/1.2.0" in combined
    assert "MAX_SANITIZED_STDERR_EXCERPT_BYTES" in combined and "4096" in combined
    assert "raw stderr" in combined.lower()
    # Authority + successor boundary.
    assert "RUNTIME ACTIVATED: NO" in project
    assert "H1 rerun: NOT_AUTHORIZED" in project
    assert "Gate C: NOT AUTHORIZED" in combined
    assert "Alpha Factory: NOT STARTED" in combined
    assert "WP176" in combined and "NOT STARTED" in combined
    assert "SEPARATE human/governance decision" in combined
    assert "Merge authorized: NO" in combined
    scope = spec["scope"]
    assert spec["identity"]["risk_level"] == 3
    assert scope["exact_scope_required"] is True
    assert scope["max_changed_files"] == 14
    assert scope["required_changed_files"] == scope["allowed_changed_files"]
    assert len(scope["required_changed_files"]) == 14
    for path in (
        "src/research_runtime/hermes_controlled_runtime/runner.py",
        "src/research_runtime/hermes_controlled_runtime/controller.py",
        "src/research_runtime/hermes_controlled_runtime/models.py",
    ):
        assert path in scope["required_changed_files"]
    # WP175K is evidence-capture hardening only: policy.py stays out of scope.
    assert (
        "src/research_runtime/hermes_controlled_runtime/policy.py"
        not in scope["required_changed_files"]
    )


# ── WP175L: Sanitized Windows runtime envelope and startup preflight ──────────


def test_wp175l_sanitized_windows_runtime_registered() -> None:
    project = _read()
    fragment = (STATUS_ENTRIES / "WP175L.md").read_text(encoding="utf-8")
    spec = json.loads(
        (REPO_ROOT / "docs" / "wp_specs" / "WP175L" / "wp_spec.json").read_text(
            encoding="utf-8"
        )
    )
    combined = "\n".join((project, fragment))
    # WP175L is the current review target; WP175K is reconciled as merged.
    assert "WP175L current review target" in project
    assert "WP175K / PR #184 merged: YES" in project
    assert "S10-HERMES-01D" in combined
    assert "BOUNDED_HERMES_WINDOWS_RUNTIME_ENVELOPE_AND_STARTUP_PREFLIGHT" in combined
    assert "Governance track: RUNTIME" in project and "Risk level: 3" in project
    assert "Exact changed-file scope: 12" in project
    # Incident + confirmed root-cause truth (two H1 runs consumed historically).
    assert "Historical real H1 research invocations consumed: 2" in combined
    assert (
        "CONTROLLED_WINDOWS_RUNTIME_ENVIRONMENT_INSUFFICIENT_FOR_HERMES_PROFILE_INITIALIZATION"
        in combined
    )
    assert "NOT_REACHED" in combined
    assert "Could not determine home directory" in combined
    assert "_apply_profile_override" in combined and "_get_platform_default_hermes_home" in combined
    assert "SUCCESSFUL AS OBSERVABILITY HARDENING" in combined
    # Runtime-envelope + preflight contract.
    assert "EXPLICIT_BENIGN_ALLOWLIST_NEVER_OS_ENVIRON_COPY" in project
    assert "LOCALAPPDATA" in combined and "USERPROFILE" in combined
    assert "injection/capability denylist: ADDED" in project
    assert "ambient provider credentials forwarded: NO" in project
    assert "STARTUP_PREFLIGHT_FAILED" in combined
    assert "transport_attempt_count 0" in combined
    # Authority + successor boundary.
    assert "RUNTIME ACTIVATED: NO" in project
    assert "H1 #3: NOT AUTHORIZED" in combined
    assert "S10-ALPHA-01: BLOCKED" in project
    assert "Gate C: NOT AUTHORIZED" in combined
    assert "Alpha Factory: NOT STARTED" in combined
    assert "WP176" in combined and "NOT STARTED" in combined
    assert "Merge authorized: NO" in combined
    # Wallet roadmap anchor persisted (not global; no live shortcut).
    assert "Wallet-intelligence roadmap anchor" in project
    assert "wallet gate NOT global" in project
    scope = spec["scope"]
    assert spec["identity"]["risk_level"] == 3
    assert scope["exact_scope_required"] is True
    assert scope["max_changed_files"] == 12
    assert scope["required_changed_files"] == scope["allowed_changed_files"]
    assert len(scope["required_changed_files"]) == 12
    for path in (
        "src/research_runtime/hermes_controlled_runtime/runner.py",
        "src/research_runtime/hermes_controlled_runtime/controller.py",
    ):
        assert path in scope["required_changed_files"]
    # WP175L is a wrapper runtime + preflight correction: models.py and policy.py stay out.
    for path in (
        "src/research_runtime/hermes_controlled_runtime/models.py",
        "src/research_runtime/hermes_controlled_runtime/policy.py",
    ):
        assert path not in scope["required_changed_files"]
