"""Focused docs tests for WP45 PR evidence reporting discipline.

Tests verify that all workflow docs require exact PR evidence reporting
as mandated by WP45 - Codex / Claude PR Evidence Reporting Hardening.
"""

from __future__ import annotations

import pathlib

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent

AGENTS_MD = REPO_ROOT / "AGENTS.md"
WP_EXECUTION_REPORT = REPO_ROOT / "docs/ai/codex/WP_EXECUTION_REPORT.md"
PR_REVIEW_CHECKLIST = REPO_ROOT / "docs/ai/codex/PR_REVIEW_CHECKLIST.md"
VALIDATION_MATRIX = REPO_ROOT / "docs/ai/codex/VALIDATION_MATRIX.md"
CONCISE_REPORTING = REPO_ROOT / "docs/ai/codex/CONCISE_REPORTING_RULES.md"
REUSABLE_BLOCKS = REPO_ROOT / "docs/ai/codex/REUSABLE_WP_PROMPT_BLOCKS.md"
PR_EVIDENCE_DISCIPLINE = REPO_ROOT / "docs/ai/codex/PR_EVIDENCE_REPORTING_DISCIPLINE.md"
WORK_PACKAGE_TEMPLATE = REPO_ROOT / "docs/work_package_template.md"
REVIEW_CHECKLIST = REPO_ROOT / "docs/review_checklist.md"
PROJECT_STATUS = REPO_ROOT / "docs/project_status.md"
REPO_TRUTH_INDEX = REPO_ROOT / "docs/repo_truth_index.md"


# ---------------------------------------------------------------------------
# 1. New central doc exists
# ---------------------------------------------------------------------------

def test_pr_evidence_discipline_doc_exists():
    assert PR_EVIDENCE_DISCIPLINE.exists(), (
        "docs/ai/codex/PR_EVIDENCE_REPORTING_DISCIPLINE.md must exist"
    )


# ---------------------------------------------------------------------------
# 2. AGENTS.md — evidence reporting discipline rule
# ---------------------------------------------------------------------------

def test_agents_md_mentions_evidence_reporting():
    text = AGENTS_MD.read_text(encoding="utf-8")
    assert "PR Evidence Reporting Discipline" in text, (
        "AGENTS.md must include a PR Evidence Reporting Discipline section"
    )


def test_agents_md_codex_and_claude_code_coverage():
    text = AGENTS_MD.read_text(encoding="utf-8")
    assert "Codex and Claude Code" in text, (
        "AGENTS.md evidence section must explicitly cover Codex and Claude Code"
    )


def test_agents_md_ready_for_review_gate():
    text = AGENTS_MD.read_text(encoding="utf-8")
    assert "Ready for review" in text and "YES" in text, (
        "AGENTS.md must state Ready for review: YES gate for evidence discipline"
    )


def test_agents_md_network_distinction():
    text = AGENTS_MD.read_text(encoding="utf-8")
    assert "runtime" in text.lower() and "git" in text.lower(), (
        "AGENTS.md must reference network distinction between git/PR and runtime/product"
    )


def test_agents_md_ellipsis_or_abbreviated_commands_forbidden():
    text = AGENTS_MD.read_text(encoding="utf-8")
    assert "ellipses" in text.lower() or "abbreviated" in text.lower(), (
        "AGENTS.md must mention that abbreviated commands or ellipses must be corrected"
    )


def test_agents_md_references_discipline_doc():
    text = AGENTS_MD.read_text(encoding="utf-8")
    assert "PR_EVIDENCE_REPORTING_DISCIPLINE" in text, (
        "AGENTS.md must reference docs/ai/codex/PR_EVIDENCE_REPORTING_DISCIPLINE.md"
    )


# ---------------------------------------------------------------------------
# 3. WP_EXECUTION_REPORT.md — evidence discipline section
# ---------------------------------------------------------------------------

def test_wp_execution_report_has_discipline_section():
    text = WP_EXECUTION_REPORT.read_text(encoding="utf-8")
    assert "PR Body And Final Comment Evidence Discipline" in text, (
        "WP_EXECUTION_REPORT.md must have 'PR Body And Final Comment Evidence Discipline' section"
    )


def test_wp_execution_report_requires_exact_full_commands():
    text = WP_EXECUTION_REPORT.read_text(encoding="utf-8")
    assert "exact full" in text.lower() or "full command" in text.lower(), (
        "WP_EXECUTION_REPORT.md must require exact full validation command invocations"
    )


def test_wp_execution_report_forbids_ellipses():
    text = WP_EXECUTION_REPORT.read_text(encoding="utf-8")
    assert "ellipses" in text.lower() or "ellipsis" in text.lower(), (
        "WP_EXECUTION_REPORT.md must forbid ellipses in validation evidence"
    )


def test_wp_execution_report_requires_network_distinction():
    text = WP_EXECUTION_REPORT.read_text(encoding="utf-8")
    assert "Remote Main Sync Gate" in text and "runtime network" in text.lower(), (
        "WP_EXECUTION_REPORT.md must require network usage distinction wording"
    )


def test_wp_execution_report_requires_body_comment_consistency():
    text = WP_EXECUTION_REPORT.read_text(encoding="utf-8")
    assert "consistent" in text.lower() or "consistency" in text.lower(), (
        "WP_EXECUTION_REPORT.md must require PR body and status fragment consistency (after WP91, final comment is optional)"
    )


def test_wp_execution_report_requires_stale_count_correction():
    text = WP_EXECUTION_REPORT.read_text(encoding="utf-8")
    assert "stale" in text.lower(), (
        "WP_EXECUTION_REPORT.md must require stale count correction before Ready for review"
    )


def test_wp_execution_report_ready_for_review_gate():
    text = WP_EXECUTION_REPORT.read_text(encoding="utf-8")
    assert "Ready for review" in text, (
        "WP_EXECUTION_REPORT.md must state Ready for review gate for evidence discipline"
    )


def test_wp_execution_report_concise_command_rule():
    text = WP_EXECUTION_REPORT.read_text(encoding="utf-8")
    # Concise reporting may compress output but not abbreviate commands
    assert "command" in text.lower() and "output" in text.lower(), (
        "WP_EXECUTION_REPORT.md must address the output-vs-command distinction in concise reporting"
    )


# ---------------------------------------------------------------------------
# 4. PR_REVIEW_CHECKLIST.md — reviewer evidence checks
# ---------------------------------------------------------------------------

def test_pr_review_checklist_has_evidence_discipline_section():
    text = PR_REVIEW_CHECKLIST.read_text(encoding="utf-8")
    assert "PR Evidence Reporting Discipline" in text, (
        "PR_REVIEW_CHECKLIST.md must have a PR Evidence Reporting Discipline section"
    )


def test_pr_review_checklist_requires_exact_commands_in_body():
    text = PR_REVIEW_CHECKLIST.read_text(encoding="utf-8")
    assert "PR body" in text and ("exact" in text.lower() or "full invocation" in text.lower()), (
        "PR_REVIEW_CHECKLIST.md must require reviewers to check exact commands in PR body"
    )


def test_pr_review_checklist_requires_exact_commands_in_final_comment():
    text = PR_REVIEW_CHECKLIST.read_text(encoding="utf-8")
    assert "final" in text.lower() and "comment" in text.lower() and "exact" in text.lower(), (
        "PR_REVIEW_CHECKLIST.md must require reviewers to check exact commands in final comment"
    )


def test_pr_review_checklist_forbids_ellipses():
    text = PR_REVIEW_CHECKLIST.read_text(encoding="utf-8")
    assert "ellipses" in text.lower() or "ellipsis" in text.lower(), (
        "PR_REVIEW_CHECKLIST.md must require reviewers to check for no ellipses"
    )


def test_pr_review_checklist_network_distinction():
    text = PR_REVIEW_CHECKLIST.read_text(encoding="utf-8")
    assert "network" in text.lower() and "runtime" in text.lower(), (
        "PR_REVIEW_CHECKLIST.md must require reviewers to check network usage distinction"
    )


def test_pr_review_checklist_body_comment_consistency():
    text = PR_REVIEW_CHECKLIST.read_text(encoding="utf-8")
    assert "consistent" in text.lower() or "consistency" in text.lower(), (
        "PR_REVIEW_CHECKLIST.md must require reviewers to check PR body / final comment consistency"
    )


def test_pr_review_checklist_follow_up_not_merge():
    text = PR_REVIEW_CHECKLIST.read_text(encoding="utf-8")
    assert "follow-up" in text.lower() or "not merge" in text.lower(), (
        "PR_REVIEW_CHECKLIST.md must state follow-up required (not merge) when evidence is defective"
    )


def test_pr_review_checklist_references_discipline_doc():
    text = PR_REVIEW_CHECKLIST.read_text(encoding="utf-8")
    assert "PR_EVIDENCE_REPORTING_DISCIPLINE" in text, (
        "PR_REVIEW_CHECKLIST.md must reference the central discipline doc"
    )


# ---------------------------------------------------------------------------
# 5. CONCISE_REPORTING_RULES.md — no abbreviation of commands
# ---------------------------------------------------------------------------

def test_concise_reporting_must_not_abbreviate_commands():
    text = CONCISE_REPORTING.read_text(encoding="utf-8")
    assert "abbreviat" in text.lower(), (
        "CONCISE_REPORTING_RULES.md must state concise reporting must not abbreviate command invocations"
    )


def test_concise_reporting_compress_output_not_command():
    text = CONCISE_REPORTING.read_text(encoding="utf-8")
    # The rule: compress output, never the command
    assert "command" in text.lower() and "output" in text.lower(), (
        "CONCISE_REPORTING_RULES.md must distinguish compressing output from abbreviating commands"
    )


def test_concise_reporting_network_wording_rule():
    text = CONCISE_REPORTING.read_text(encoding="utf-8")
    assert "Network Usage Wording" in text or "network usage wording" in text.lower(), (
        "CONCISE_REPORTING_RULES.md must include a Network Usage Wording Rule"
    )


def test_concise_reporting_exact_counts_required():
    text = CONCISE_REPORTING.read_text(encoding="utf-8")
    assert "counts" in text.lower() or "count" in text.lower(), (
        "CONCISE_REPORTING_RULES.md must require exact test counts"
    )


def test_concise_reporting_ellipsis_forbidden():
    text = CONCISE_REPORTING.read_text(encoding="utf-8")
    assert "ellipses" in text.lower() or "ellipsis" in text.lower(), (
        "CONCISE_REPORTING_RULES.md must forbid ellipses in command evidence"
    )


# ---------------------------------------------------------------------------
# 6. REUSABLE_WP_PROMPT_BLOCKS.md — Standard PR Evidence Block
# ---------------------------------------------------------------------------

def test_reusable_blocks_has_evidence_discipline_block():
    text = REUSABLE_BLOCKS.read_text(encoding="utf-8")
    assert "Standard PR Evidence Reporting Discipline Block" in text, (
        "REUSABLE_WP_PROMPT_BLOCKS.md must contain 'Standard PR Evidence Reporting Discipline Block'"
    )


def test_reusable_blocks_evidence_block_requires_exact_commands():
    text = REUSABLE_BLOCKS.read_text(encoding="utf-8")
    assert "exact full" in text.lower() or "full command" in text.lower(), (
        "REUSABLE_WP_PROMPT_BLOCKS.md evidence block must require exact full command invocations"
    )


def test_reusable_blocks_evidence_block_forbids_ellipses():
    text = REUSABLE_BLOCKS.read_text(encoding="utf-8")
    assert "ellipses" in text.lower() or "ellipsis" in text.lower(), (
        "REUSABLE_WP_PROMPT_BLOCKS.md evidence block must forbid ellipses"
    )


def test_reusable_blocks_evidence_block_network_wording():
    text = REUSABLE_BLOCKS.read_text(encoding="utf-8")
    assert "Remote Main Sync Gate" in text and "runtime network" in text.lower(), (
        "REUSABLE_WP_PROMPT_BLOCKS.md evidence block must include network distinction wording"
    )


def test_reusable_blocks_evidence_block_body_comment_consistency():
    text = REUSABLE_BLOCKS.read_text(encoding="utf-8")
    assert "consistent" in text.lower() or "consistency" in text.lower(), (
        "REUSABLE_WP_PROMPT_BLOCKS.md evidence block must require body/comment consistency"
    )


def test_reusable_blocks_evidence_block_stale_counts():
    text = REUSABLE_BLOCKS.read_text(encoding="utf-8")
    assert "stale" in text.lower(), (
        "REUSABLE_WP_PROMPT_BLOCKS.md evidence block must require stale count correction"
    )


def test_reusable_blocks_evidence_block_ready_for_review_gate():
    text = REUSABLE_BLOCKS.read_text(encoding="utf-8")
    assert "Ready for review" in text, (
        "REUSABLE_WP_PROMPT_BLOCKS.md evidence block must include Ready for review gate"
    )


# ---------------------------------------------------------------------------
# 7. docs/work_package_template.md — evidence discipline section
# ---------------------------------------------------------------------------

def test_work_package_template_references_evidence_block():
    text = WORK_PACKAGE_TEMPLATE.read_text(encoding="utf-8")
    assert "Standard PR Evidence Reporting Discipline Block" in text, (
        "docs/work_package_template.md must reference the Standard PR Evidence Reporting Discipline Block"
    )


def test_work_package_template_has_evidence_discipline_section():
    text = WORK_PACKAGE_TEMPLATE.read_text(encoding="utf-8")
    assert "PR Evidence Reporting Discipline" in text, (
        "docs/work_package_template.md must have a PR Evidence Reporting Discipline section"
    )


def test_work_package_template_pr_body_requires_exact_commands():
    text = WORK_PACKAGE_TEMPLATE.read_text(encoding="utf-8")
    assert "exact" in text.lower() and "command" in text.lower(), (
        "docs/work_package_template.md PR body required sections must mention exact commands"
    )


# ---------------------------------------------------------------------------
# 8. docs/review_checklist.md — WP45 reviewer checks
# ---------------------------------------------------------------------------

def test_review_checklist_has_wp45_section():
    text = REVIEW_CHECKLIST.read_text(encoding="utf-8")
    assert "WP45" in text, (
        "docs/review_checklist.md must have a WP45 section"
    )


def test_review_checklist_wp45_checks_body_comment_consistency():
    text = REVIEW_CHECKLIST.read_text(encoding="utf-8")
    assert "consistency" in text.lower() or "consistent" in text.lower(), (
        "docs/review_checklist.md WP45 section must check PR body / final comment consistency"
    )


def test_review_checklist_wp45_checks_evidence_discipline_doc():
    text = REVIEW_CHECKLIST.read_text(encoding="utf-8")
    assert "PR_EVIDENCE_REPORTING_DISCIPLINE" in text, (
        "docs/review_checklist.md WP45 section must reference PR_EVIDENCE_REPORTING_DISCIPLINE.md"
    )


# ---------------------------------------------------------------------------
# 9. PR_EVIDENCE_REPORTING_DISCIPLINE.md — central doc content
# ---------------------------------------------------------------------------

def test_discipline_doc_applies_to_codex_and_claude_code():
    text = PR_EVIDENCE_DISCIPLINE.read_text(encoding="utf-8")
    assert "Codex and Claude Code" in text, (
        "PR_EVIDENCE_REPORTING_DISCIPLINE.md must state it applies to Codex and Claude Code"
    )


def test_discipline_doc_exact_command_requirement():
    text = PR_EVIDENCE_DISCIPLINE.read_text(encoding="utf-8")
    assert "exact full" in text.lower() or "full command" in text.lower() or "exact" in text.lower(), (
        "PR_EVIDENCE_REPORTING_DISCIPLINE.md must define exact validation command requirement"
    )


def test_discipline_doc_no_ellipsis_rule():
    text = PR_EVIDENCE_DISCIPLINE.read_text(encoding="utf-8")
    assert "ellipses" in text.lower() or "ellipsis" in text.lower(), (
        "PR_EVIDENCE_REPORTING_DISCIPLINE.md must state no-ellipsis rule"
    )


def test_discipline_doc_network_wording_rule():
    text = PR_EVIDENCE_DISCIPLINE.read_text(encoding="utf-8")
    assert "Remote Main Sync Gate" in text, (
        "PR_EVIDENCE_REPORTING_DISCIPLINE.md must include network usage wording rule"
    )


def test_discipline_doc_body_comment_consistency():
    text = PR_EVIDENCE_DISCIPLINE.read_text(encoding="utf-8")
    assert "consistent" in text.lower() or "consistency" in text.lower(), (
        "PR_EVIDENCE_REPORTING_DISCIPLINE.md must require PR body and status fragment consistency (after WP91, final comment is optional)"
    )


def test_discipline_doc_ready_for_review_gate():
    text = PR_EVIDENCE_DISCIPLINE.read_text(encoding="utf-8")
    assert "Ready for review" in text, (
        "PR_EVIDENCE_REPORTING_DISCIPLINE.md must define the Ready-for-review gate"
    )


def test_discipline_doc_reviewer_action():
    text = PR_EVIDENCE_DISCIPLINE.read_text(encoding="utf-8")
    assert "follow-up" in text.lower() or "not merge" in text.lower(), (
        "PR_EVIDENCE_REPORTING_DISCIPLINE.md must state reviewer action when evidence is defective"
    )


def test_discipline_doc_has_acceptable_example():
    text = PR_EVIDENCE_DISCIPLINE.read_text(encoding="utf-8")
    assert "Acceptable" in text, (
        "PR_EVIDENCE_REPORTING_DISCIPLINE.md must include examples of acceptable wording"
    )


def test_discipline_doc_has_not_acceptable_example():
    text = PR_EVIDENCE_DISCIPLINE.read_text(encoding="utf-8")
    assert "Not acceptable" in text or "not acceptable" in text.lower(), (
        "PR_EVIDENCE_REPORTING_DISCIPLINE.md must include examples of not acceptable wording"
    )


def test_discipline_doc_standard_network_wording():
    text = PR_EVIDENCE_DISCIPLINE.read_text(encoding="utf-8")
    assert "no runtime network behavior" in text.lower(), (
        "PR_EVIDENCE_REPORTING_DISCIPLINE.md must include standard network distinction wording"
    )


# ---------------------------------------------------------------------------
# 10. VALIDATION_MATRIX.md — all-WP evidence reporting check
# ---------------------------------------------------------------------------

def test_validation_matrix_all_wps_evidence_check():
    text = VALIDATION_MATRIX.read_text(encoding="utf-8")
    assert "PR evidence reporting" in text or "exact PR evidence" in text, (
        "VALIDATION_MATRIX.md All Work Packages section must include PR evidence reporting check"
    )


def test_validation_matrix_workflow_governance_evidence_check():
    text = VALIDATION_MATRIX.read_text(encoding="utf-8")
    lines = text.splitlines()
    wf_line = next(
        (l for l in lines if "workflow/governance" in l.lower()),
        None,
    )
    assert wf_line is not None, (
        "VALIDATION_MATRIX.md must have a workflow/governance WP row"
    )
    assert "evidence" in wf_line.lower() or "PR evidence" in wf_line, (
        "VALIDATION_MATRIX.md workflow/governance WP row must include PR evidence reporting check"
    )


def test_validation_matrix_references_discipline_doc():
    text = VALIDATION_MATRIX.read_text(encoding="utf-8")
    assert "PR_EVIDENCE_REPORTING_DISCIPLINE" in text, (
        "VALIDATION_MATRIX.md must reference docs/ai/codex/PR_EVIDENCE_REPORTING_DISCIPLINE.md"
    )


# ---------------------------------------------------------------------------
# 11. docs/project_status.md — WP46 active, WP44 and WP45 merged
# ---------------------------------------------------------------------------

def test_project_status_wp45_current_phase():
    """WP45 is now merged; the current phase must be a subsequent WP (WP46+)."""
    text = PROJECT_STATUS.read_text(encoding="utf-8")
    phase_line = next(
        (l for l in text.splitlines() if l.startswith("- Current phase:")),
        None,
    )
    assert phase_line is not None, "docs/project_status.md must have a Current phase line"
    # WP45 is merged; current phase is WP46 or later
    assert any(f"WP{n}" in phase_line for n in range(46, 105)), (
        "docs/project_status.md Current phase must show a WP after WP45 merge "
        f"(got: {phase_line!r})"
    )


def test_project_status_wp44_in_merged_wps():
    text = PROJECT_STATUS.read_text(encoding="utf-8")
    merged_line = next(
        (l for l in text.splitlines() if l.startswith("- Merged WPs:")),
        None,
    )
    assert merged_line is not None, "docs/project_status.md must have a Merged WPs line"
    assert "WP44" in merged_line, (
        "docs/project_status.md merged WPs must include WP44"
    )


def test_project_status_wp45_in_merged_wps():
    """WP45 is merged; it must appear in the merged WPs list."""
    text = PROJECT_STATUS.read_text(encoding="utf-8")
    merged_line = next(
        (l for l in text.splitlines() if l.startswith("- Merged WPs:")),
        None,
    )
    assert merged_line is not None, "docs/project_status.md must have a Merged WPs line"
    assert "WP45" in merged_line, (
        "docs/project_status.md merged WPs must include WP45 (now merged)"
    )


def test_project_status_wp45_current_branch():
    """WP45 is merged; the current branch must be a subsequent WP branch."""
    text = PROJECT_STATUS.read_text(encoding="utf-8")
    branch_line = next(
        (l for l in text.splitlines() if l.startswith("- Current branch:")),
        None,
    )
    assert branch_line is not None, "docs/project_status.md must have a Current branch line"
    assert "see GitHub PR metadata and PR body" in branch_line or any(
        f"wp{n}" in branch_line.lower() for n in range(46, 100)
    ), (
        "docs/project_status.md Current branch must reference a branch after WP45 merge "
        f"(got: {branch_line!r})"
    )


def test_project_status_pr_evidence_reporting_status():
    text = PROJECT_STATUS.read_text(encoding="utf-8")
    assert "PR evidence reporting discipline status" in text or "WORKFLOW_GOVERNANCE_ON_BRANCH" in text, (
        "docs/project_status.md must include PR evidence reporting discipline status"
    )


def test_project_status_protected_boundaries_live_trading_disabled():
    text = PROJECT_STATUS.read_text(encoding="utf-8")
    assert "Live trading status: DISABLED" in text, (
        "docs/project_status.md must preserve Live trading status: DISABLED"
    )


def test_project_status_protected_boundaries_credentials_not_used():
    text = PROJECT_STATUS.read_text(encoding="utf-8")
    assert "Credentials status: NOT_USED" in text, (
        "docs/project_status.md must preserve Credentials status: NOT_USED"
    )


def test_project_status_protected_boundaries_execution_not_started():
    text = PROJECT_STATUS.read_text(encoding="utf-8")
    assert "Execution status: NOT_STARTED" in text, (
        "docs/project_status.md must preserve Execution status: NOT_STARTED"
    )


def test_project_status_protected_boundaries_hermes_not_installed():
    text = PROJECT_STATUS.read_text(encoding="utf-8")
    assert "Hermes status: NOT_INSTALLED_NOT_RUNTIME_DEPENDENCY" in text, (
        "docs/project_status.md must preserve Hermes status"
    )


def test_project_status_protected_boundaries_agent_runtime_not_started():
    text = PROJECT_STATUS.read_text(encoding="utf-8")
    assert "Agent runtime status: NOT_STARTED" in text, (
        "docs/project_status.md must preserve Agent runtime status: NOT_STARTED"
    )


def test_project_status_protected_boundaries_agent_execution_forbidden():
    text = PROJECT_STATUS.read_text(encoding="utf-8")
    assert "Agent execution authority: FORBIDDEN" in text, (
        "docs/project_status.md must preserve Agent execution authority: FORBIDDEN"
    )


def test_project_status_wp44_historical_section_not_on_branch():
    text = PROJECT_STATUS.read_text(encoding="utf-8")
    # The historical WP44 section must say "is merged", not "is on branch"
    lines = text.splitlines()
    wp44_section_lines = []
    in_wp44 = False
    for line in lines:
        if line.startswith("## WP44"):
            in_wp44 = True
        elif line.startswith("## WP") and in_wp44:
            break
        if in_wp44:
            wp44_section_lines.append(line)
    wp44_text = "\n".join(wp44_section_lines)
    assert "is on branch" not in wp44_text, (
        "docs/project_status.md WP44 historical section must not say 'is on branch' "
        "(WP44 is merged; use 'is merged' or mark branch name as historical)"
    )


def test_project_status_wp44_historical_section_says_merged():
    text = PROJECT_STATUS.read_text(encoding="utf-8")
    lines = text.splitlines()
    wp44_section_lines = []
    in_wp44 = False
    for line in lines:
        if line.startswith("## WP44"):
            in_wp44 = True
        elif line.startswith("## WP") and in_wp44:
            break
        if in_wp44:
            wp44_section_lines.append(line)
    wp44_text = "\n".join(wp44_section_lines)
    assert "is merged" in wp44_text or "merged" in wp44_text.lower(), (
        "docs/project_status.md WP44 historical section must indicate WP44 is merged"
    )


# ---------------------------------------------------------------------------
# 12. docs/repo_truth_index.md — new central doc indexed
# ---------------------------------------------------------------------------

def test_repo_truth_index_references_discipline_doc():
    text = REPO_TRUTH_INDEX.read_text(encoding="utf-8")
    assert "PR_EVIDENCE_REPORTING_DISCIPLINE" in text, (
        "docs/repo_truth_index.md must index docs/ai/codex/PR_EVIDENCE_REPORTING_DISCIPLINE.md"
    )


def test_repo_truth_index_no_duplicate_numbers():
    text = REPO_TRUTH_INDEX.read_text(encoding="utf-8")
    import re
    numbered = re.findall(r"^(\d+)\.", text, re.MULTILINE)
    seen = set()
    for n in numbered:
        assert n not in seen, (
            f"docs/repo_truth_index.md has duplicate number {n}"
        )
        seen.add(n)
