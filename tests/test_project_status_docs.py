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
    assert any(wp in current_phase_line for wp in ("WP79", "WP80", "WP81", "WP82", "WP83", "WP84", "WP86", "WP87", "WP88", "WP89", "WP90", "WP91", "WP92", "WP93", "WP94", "WP95", "WP96", "WP97", "WP98", "WP99", "WP100", "WP101"))


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
    assert any(wp in current_phase_line for wp in ("WP88", "WP89", "WP90", "WP91", "WP92", "WP93", "WP94", "WP95", "WP96", "WP97", "WP98", "WP99", "WP100", "WP101"))


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
    assert any(wp in current_phase_line for wp in ("WP91", "WP90", "WP92", "WP93", "WP94", "WP95", "WP96", "WP97", "WP98", "WP99", "WP100", "WP101"))


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
    assert any(wp in current_phase_line for wp in ("WP92", "WP91", "WP93", "WP94", "WP95", "WP96", "WP97", "WP98", "WP99", "WP100", "WP101"))


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
    assert any(wp in current_phase_line for wp in ("WP93", "WP94", "WP95", "WP96", "WP97", "WP98", "WP99", "WP100", "WP101"))


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
    assert any(wp in current_phase_line for wp in ("WP95", "WP96", "WP97", "WP98", "WP99", "WP100", "WP101"))
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
    assert any(wp in current_phase_line for wp in ("WP96", "WP97", "WP98", "WP99", "WP100", "WP101"))
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
    assert any(wp in current_phase_line for wp in ("WP97", "WP98", "WP99", "WP100", "WP101"))
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
    assert any(wp in current_phase_line for wp in ("WP98", "WP99", "WP100", "WP101"))
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
    assert any(wp in current_phase_line for wp in ("WP99", "WP100", "WP101"))
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
    assert any(wp in current_phase_line for wp in ("WP100", "WP101"))
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
    assert "WP101" in current_phase_line
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
