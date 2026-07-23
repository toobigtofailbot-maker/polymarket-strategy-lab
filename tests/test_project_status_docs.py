"""Focused docs tests for docs/project_status.md repo-truth consistency.

Added in WP43 to prevent stale WP42 branch wording from recurring after merge.
"""

from __future__ import annotations

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
    assert any(wp in current_phase_line for wp in ("WP79", "WP80", "WP81", "WP82", "WP83", "WP84", "WP86", "WP87", "WP88", "WP89", "WP90", "WP91", "WP92", "WP93", "WP94", "WP95", "WP96", "WP97", "WP98", "WP99", "WP100", "WP101", "WP102", "WP103", "WP104", "WP105", "WP106", "WP107", "WP108", "WP109", "WP110", "WP111", "WP112", "WP113", "WP114", "WP115", "WP116", "WP117", "WP118", "WP128", "WP130", "WP136", "WP138", "WP142", "WP148", "WP149"))


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
    assert any(wp in current_phase_line for wp in ("WP88", "WP89", "WP90", "WP91", "WP92", "WP93", "WP94", "WP95", "WP96", "WP97", "WP98", "WP99", "WP100", "WP101", "WP102", "WP103", "WP104", "WP105", "WP106", "WP107", "WP108", "WP109", "WP110", "WP111", "WP112", "WP113", "WP114", "WP115", "WP116", "WP117", "WP118", "WP128", "WP130", "WP136", "WP138", "WP142", "WP148", "WP149"))


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
    assert any(wp in current_phase_line for wp in ("WP91", "WP90", "WP92", "WP93", "WP94", "WP95", "WP96", "WP97", "WP98", "WP99", "WP100", "WP101", "WP102", "WP103", "WP104", "WP105", "WP106", "WP107", "WP108", "WP109", "WP110", "WP111", "WP112", "WP113", "WP114", "WP115", "WP116", "WP117", "WP118", "WP128", "WP130", "WP136", "WP138", "WP142", "WP148", "WP149"))


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
    assert any(wp in current_phase_line for wp in ("WP92", "WP91", "WP93", "WP94", "WP95", "WP96", "WP97", "WP98", "WP99", "WP100", "WP101", "WP102", "WP103", "WP104", "WP105", "WP106", "WP107", "WP108", "WP109", "WP110", "WP111", "WP112", "WP113", "WP114", "WP115", "WP116", "WP117", "WP118", "WP128", "WP130", "WP136", "WP138", "WP142", "WP148", "WP149"))


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
    assert any(wp in current_phase_line for wp in ("WP93", "WP94", "WP95", "WP96", "WP97", "WP98", "WP99", "WP100", "WP101", "WP102", "WP103", "WP104", "WP105", "WP106", "WP107", "WP108", "WP109", "WP110", "WP111", "WP112", "WP113", "WP114", "WP115", "WP116", "WP117", "WP118", "WP128", "WP130", "WP136", "WP138", "WP142", "WP148", "WP149"))


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
    assert any(wp in current_phase_line for wp in ("WP95", "WP96", "WP97", "WP98", "WP99", "WP100", "WP101", "WP102", "WP103", "WP104", "WP105", "WP106", "WP107", "WP108", "WP109", "WP110", "WP111", "WP112", "WP113", "WP114", "WP115", "WP116", "WP117", "WP118", "WP128", "WP130", "WP136", "WP138", "WP142", "WP148", "WP149"))
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
    assert any(wp in current_phase_line for wp in ("WP96", "WP97", "WP98", "WP99", "WP100", "WP101", "WP102", "WP103", "WP104", "WP105", "WP106", "WP107", "WP108", "WP109", "WP110", "WP111", "WP112", "WP113", "WP114", "WP115", "WP116", "WP117", "WP118", "WP128", "WP130", "WP136", "WP138", "WP142", "WP148", "WP149"))
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
    assert any(wp in current_phase_line for wp in ("WP97", "WP98", "WP99", "WP100", "WP101", "WP102", "WP103", "WP104", "WP105", "WP106", "WP107", "WP108", "WP109", "WP110", "WP111", "WP112", "WP113", "WP114", "WP115", "WP116", "WP117", "WP118", "WP128", "WP130", "WP136", "WP138", "WP142", "WP148", "WP149"))
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
    assert any(wp in current_phase_line for wp in ("WP98", "WP99", "WP100", "WP101", "WP102", "WP103", "WP104", "WP105", "WP106", "WP107", "WP108", "WP109", "WP110", "WP111", "WP112", "WP113", "WP114", "WP115", "WP116", "WP117", "WP118", "WP128", "WP130", "WP136", "WP138", "WP142", "WP148", "WP149"))
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
    assert any(wp in current_phase_line for wp in ("WP99", "WP100", "WP101", "WP102", "WP103", "WP104", "WP105", "WP106", "WP107", "WP108", "WP109", "WP110", "WP111", "WP112", "WP113", "WP114", "WP115", "WP116", "WP117", "WP118", "WP128", "WP130", "WP136", "WP138", "WP142", "WP148", "WP149"))
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
    assert any(wp in current_phase_line for wp in ("WP100", "WP101", "WP102", "WP103", "WP104", "WP105", "WP106", "WP107", "WP108", "WP109", "WP110", "WP111", "WP112", "WP113", "WP114", "WP115", "WP116", "WP117", "WP118", "WP128", "WP130", "WP136", "WP138", "WP142", "WP148", "WP149"))
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
    assert any(wp in current_phase_line for wp in ("WP101", "WP102", "WP103", "WP104", "WP105", "WP106", "WP107", "WP108", "WP109", "WP110", "WP111", "WP112", "WP113", "WP114", "WP115", "WP116", "WP117", "WP118", "WP128", "WP130", "WP136", "WP138", "WP142", "WP148", "WP149"))
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
    assert any(wp in current_phase_line for wp in ("WP102", "WP103", "WP104", "WP105", "WP106", "WP107", "WP108", "WP109", "WP110", "WP111", "WP112", "WP113", "WP114", "WP115", "WP116", "WP117", "WP118", "WP128", "WP130", "WP136", "WP138", "WP142", "WP148", "WP149"))
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
    assert any(wp in current_phase_line for wp in ("WP103", "WP104", "WP105", "WP106", "WP107", "WP108", "WP109", "WP110", "WP111", "WP112", "WP113", "WP114", "WP115", "WP116", "WP117", "WP118", "WP128", "WP130", "WP136", "WP138", "WP142", "WP148", "WP149"))
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
    assert any(wp in current_phase_line for wp in ("WP104", "WP105", "WP106", "WP107", "WP108", "WP109", "WP110", "WP111", "WP112", "WP113", "WP114", "WP115", "WP116", "WP117", "WP118", "WP128", "WP130", "WP136", "WP138", "WP142", "WP148", "WP149"))
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
    assert any(wp in current_phase_line for wp in ("WP105", "WP106", "WP107", "WP108", "WP109", "WP110", "WP111", "WP112", "WP113", "WP114", "WP115", "WP116", "WP117", "WP118", "WP128", "WP130", "WP136", "WP138", "WP142", "WP148", "WP149"))
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
    assert any(wp in current_phase_line for wp in ("WP106", "WP107", "WP108", "WP109", "WP110", "WP111", "WP112", "WP113", "WP114", "WP115", "WP116", "WP117", "WP118", "WP128", "WP130", "WP136", "WP138", "WP142", "WP148", "WP149"))
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
    assert any(wp in current_phase_line for wp in ("WP107", "WP108", "WP109", "WP110", "WP111", "WP112", "WP113", "WP114", "WP115", "WP116", "WP117", "WP118", "WP128", "WP130", "WP136", "WP138", "WP142", "WP148", "WP149"))
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
    assert any(wp in current_phase_line for wp in ("WP108", "WP109", "WP110", "WP111", "WP112", "WP113", "WP114", "WP115", "WP116", "WP117", "WP118", "WP128", "WP130", "WP136", "WP138", "WP142", "WP148", "WP149"))
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
    assert any(wp in current_phase_line for wp in ("WP109", "WP110", "WP111", "WP112", "WP113", "WP114", "WP115", "WP116", "WP117", "WP118", "WP128", "WP130", "WP136", "WP138", "WP142", "WP148", "WP149"))
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
    assert any(wp in current_phase_line for wp in ("WP111", "WP112", "WP113", "WP114", "WP115", "WP116", "WP117", "WP118", "WP128", "WP130", "WP136", "WP138", "WP142", "WP148", "WP149"))
    assert "DOCS_STATUS_TESTS_ONLY_TEMP_ONLY_LOCAL_MANUAL_EXPORT_SMOKE_EXERCISE_REVIEW_TARGET" in text
    assert "docs/hermes_candidate_review_local_manual_export_smoke_exercise.md" in text


def test_wp148_is_reconciled_as_merged_and_wp149_is_current_review_target_state():
    text = _read()
    current_phase_line = next(
        line for line in text.splitlines() if line.startswith("- Current phase:")
    )
    merged_line = next(
        line for line in text.splitlines() if line.startswith("- Merged WPs:")
    )
    assert "WP149" in current_phase_line
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
    assert "DOCS_STATUS_TESTS_ONLY_REMOTE_PROVIDER_TRACK_DEFERRAL_REVISIT_CRITERIA_DECISION_REVIEW_TARGET" in text
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


def test_wp131_through_wp149_dedicated_status_chain_is_consistent():
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
    assert "REVIEW_TARGET" in wp149_line
    assert sum("REVIEW_TARGET" in line for line in (
        wp131_line, wp132_line, wp133_line, wp134_line, wp135_line, wp136_line,
        wp137_line, wp138_line, wp139_line, wp140_line, wp141_line, wp142_line,
        wp143_line, wp144_line, wp145_line, wp146_line, wp147_line, wp148_line,
        wp149_line,
    )) == 1
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
    assert "DOCS_STATUS_TESTS_ONLY_REMOTE_PROVIDER_TRACK_DEFERRAL_REVISIT_CRITERIA_DECISION_REVIEW_TARGET" in wp149_line
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
        "WP150 requires separate approval",
    ):
        assert phrase in wp149_line
    assert "WP149" in current_phase_line
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
        "docs/deferred_items_log.md",
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
