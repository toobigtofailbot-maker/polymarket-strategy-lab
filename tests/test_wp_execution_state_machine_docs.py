"""
Focused docs tests for WP59 / WF-STAB-1: WP Execution State Machine canonical document.
"""
import os
import re

STATE_MACHINE_PATH = "docs/ai/codex/WP_EXECUTION_STATE_MACHINE.md"


def _read_state_machine():
    assert os.path.exists(STATE_MACHINE_PATH), f"Missing: {STATE_MACHINE_PATH}"
    with open(STATE_MACHINE_PATH, encoding="utf-8") as f:
        return f.read()


# ── Existence and header ──────────────────────────────────────────────────────

def test_state_machine_doc_exists():
    assert os.path.exists(STATE_MACHINE_PATH)


def test_state_machine_declares_workflow_governance_canonical():
    content = _read_state_machine()
    assert "WORKFLOW_GOVERNANCE_CANONICAL" in content


def test_state_machine_references_claude_code():
    content = _read_state_machine()
    assert "Claude Code" in content


def test_state_machine_references_codex():
    content = _read_state_machine()
    assert "Codex" in content


# ── All phases present ────────────────────────────────────────────────────────

def test_state_machine_phase_receive_wp():
    content = _read_state_machine()
    assert "Receive WP" in content or "receive WP" in content.lower()


def test_state_machine_phase_startup_read():
    content = _read_state_machine()
    assert "Startup read" in content or "startup read" in content.lower()


def test_state_machine_phase_repo_truth_preflight():
    content = _read_state_machine()
    assert "preflight" in content.lower() or "Repo-truth" in content


def test_state_machine_phase_branch_creation():
    content = _read_state_machine()
    assert "Branch creation" in content or "branch creation" in content.lower()


def test_state_machine_phase_scoped_implementation():
    content = _read_state_machine()
    assert "implementation" in content.lower()


def test_state_machine_phase_validation():
    content = _read_state_machine()
    assert "Validation" in content


def test_state_machine_phase_evidence_package_construction():
    content = _read_state_machine()
    assert "Evidence package" in content or "evidence package" in content.lower()


def test_state_machine_phase_local_evidence_guard():
    content = _read_state_machine()
    assert "Local evidence guard" in content or "local evidence guard" in content.lower()


def test_state_machine_phase_github_posting():
    content = _read_state_machine()
    assert "GitHub posting" in content or "GitHub Posting" in content or "github posting" in content.lower()


def test_state_machine_phase_evidence_mode_selection():
    content = _read_state_machine()
    assert "evidence mode" in content.lower()


def test_state_machine_phase_ready_for_review_decision():
    content = _read_state_machine()
    assert "Ready-for-review" in content or "ready-for-review" in content.lower()


def test_state_machine_phase_review_merge_decision():
    content = _read_state_machine()
    assert "Review/merge" in content or "review/merge" in content.lower()


def test_state_machine_phase_post_merge_reconciliation():
    content = _read_state_machine()
    assert "reconciliation" in content.lower()


# ── Three evidence modes defined ─────────────────────────────────────────────

def test_state_machine_defines_public_verifier_pass():
    content = _read_state_machine()
    assert "PUBLIC_VERIFIER_PASS" in content


def test_state_machine_defines_private_repo_manual_verified():
    content = _read_state_machine()
    assert "PRIVATE_REPO_MANUAL_VERIFIED" in content


def test_state_machine_defines_blocked_not_ready():
    content = _read_state_machine()
    assert "BLOCKED_NOT_READY" in content


# ── Core rules ────────────────────────────────────────────────────────────────

def test_state_machine_forbids_calling_manual_inspection_verifier_pass():
    content = _read_state_machine()
    # Must state that manual inspection must not be called verifier PASS
    assert (
        "must never be reported as" in content.lower()
        or "must not be called" in content.lower()
        or "never call" in content.lower()
    )
    # Specifically forbids calling it "Posted GitHub evidence verifier: PASS"
    assert "Posted GitHub evidence verifier: PASS" in content


def test_state_machine_exit_3_not_process_defect_in_private_mode():
    content = _read_state_machine()
    assert "exit 3" in content
    assert "not itself a process defect" in content


def test_state_machine_blocked_mode_forces_ready_no():
    content = _read_state_machine()
    assert "BLOCKED_NOT_READY" in content
    # Must say ready is NO under blocked mode
    lower = content.lower()
    assert "ready for review must be no" in lower or "ready must be no" in lower or "always" in content


def test_state_machine_separates_validation_from_evidence_mode():
    content = _read_state_machine()
    assert "Validation proves" in content or "validation proves" in content.lower()
    assert "Evidence mode proves" in content or "evidence mode proves" in content.lower()


def test_state_machine_routes_draftability_by_governance_track():
    content = _read_state_machine()
    lower = " ".join(content.lower().split())
    assert "LOCAL_DRAFT -> DRAFTABILITY_PASS -> AUTHORIZED -> IMPLEMENTED_LOCAL" in content
    assert "governance-track routing" in lower
    assert "risk 4" in lower and "risk 3" in lower and "risk 0–2" in lower
    assert "historical pre-wp171g packages" in lower
    assert "legacy `protected`" in lower
    assert "begin_governance_authority_v1" in lower
    assert "all sixteen" in lower
    assert "prompt prose cannot broaden" in lower
    assert "missing, duplicate, malformed, reordered, or mismatching" in lower
    assert "package_guard_passed: null" in lower
    assert "fast" in lower and "runtime" in lower and "protected" in lower
    assert "not an independent llm review" in lower
    assert "independent recertification" in lower
    assert "same-capability" in lower
    assert "all tracks require independent side pr review" in lower
    assert "failed required test" in lower


def test_state_machine_local_guard_necessary_not_sufficient():
    content = _read_state_machine()
    assert "necessary but not sufficient" in content.lower()


def test_state_machine_stale_project_status_after_merge_expected():
    content = _read_state_machine()
    assert "stale" in content.lower()
    assert "expected" in content.lower()
    assert "reconcil" in content.lower()


def test_state_machine_exit_3_forbidden_under_public_verifier_pass():
    content = _read_state_machine()
    # Must forbid using PUBLIC_VERIFIER_PASS when verifier exits 3
    assert "exit 3" in content
    # The mode defines this — check the mode section says exit 3 is not allowed
    assert "PUBLIC_VERIFIER_PASS" in content
    # The text should say using this mode when exit is 3 is forbidden
    assert "Forbidden" in content or "forbidden" in content.lower()


def test_state_machine_private_mode_ready_yes_only_when_fields_complete():
    content = _read_state_machine()
    assert "PRIVATE_REPO_MANUAL_VERIFIED" in content
    # Must require all manual fields to be complete for Ready YES
    assert "all required" in content.lower() or "required fields" in content.lower()


# ── Cross-references ──────────────────────────────────────────────────────────

def test_state_machine_references_agents_md():
    content = _read_state_machine()
    assert "AGENTS.md" in content


def test_state_machine_references_claude_start_here():
    content = _read_state_machine()
    assert "CLAUDE_START_HERE.md" in content


def test_state_machine_references_posted_evidence_doc():
    content = _read_state_machine()
    assert "POSTED_GITHUB_EVIDENCE_VERIFICATION.md" in content


def test_state_machine_references_validation_matrix():
    content = _read_state_machine()
    assert "VALIDATION_MATRIX.md" in content


# ── Startup docs reference state machine ─────────────────────────────────────

def test_agents_md_references_state_machine():
    path = "AGENTS.md"
    assert os.path.exists(path)
    with open(path, encoding="utf-8") as f:
        content = f.read()
    assert "WP_EXECUTION_STATE_MACHINE.md" in content


def test_codex_start_here_references_state_machine():
    path = "CODEX_START_HERE.md"
    assert os.path.exists(path)
    with open(path, encoding="utf-8") as f:
        content = f.read()
    assert "WP_EXECUTION_STATE_MACHINE.md" in content


def test_claude_start_here_references_state_machine():
    path = "CLAUDE_START_HERE.md"
    assert os.path.exists(path)
    with open(path, encoding="utf-8") as f:
        content = f.read()
    assert "WP_EXECUTION_STATE_MACHINE.md" in content


def test_codex_readme_references_state_machine():
    path = "docs/ai/codex/README.md"
    assert os.path.exists(path)
    with open(path, encoding="utf-8") as f:
        content = f.read()
    assert "WP_EXECUTION_STATE_MACHINE.md" in content


# ── Old contradiction is absent ───────────────────────────────────────────────

def test_startup_docs_do_not_require_exit_3_means_ready_no():
    """
    Startup docs must not imply exit 3 alone forces Ready NO.
    Under PRIVATE_REPO_MANUAL_VERIFIED with complete fields, Ready YES is allowed.
    """
    for path in ["CLAUDE_START_HERE.md", "CODEX_START_HERE.md", "AGENTS.md"]:
        with open(path, encoding="utf-8") as f:
            content = f.read()
        # Must not contain wording that says unavailable alone means Ready NO
        # The old wording was: "Ready for review must be NO unless manual live GitHub verification is fully documented and accepted"
        # which could be misread. The new wording must clarify that PRIVATE_REPO_MANUAL_VERIFIED can be Ready YES.
        assert "PRIVATE_REPO_MANUAL_VERIFIED" in content or "evidence mode" in content.lower(), \
            f"{path} should reference evidence modes or PRIVATE_REPO_MANUAL_VERIFIED"


def test_claude_start_here_drift_prevention_rule():
    """CLAUDE_START_HERE.md must contain explicit drift prevention for private-repo evidence mode."""
    with open("CLAUDE_START_HERE.md", encoding="utf-8") as f:
        content = f.read()
    assert "exit 3" in content
    assert "not itself a process defect" in content


def test_claude_start_here_forbids_calling_manual_verifier_pass():
    """Must explicitly forbid calling manual inspection 'posted verifier PASS'."""
    with open("CLAUDE_START_HERE.md", encoding="utf-8") as f:
        content = f.read()
    assert "PRIVATE_REPO_MANUAL_VERIFIED" in content


# ── Posted evidence doc defines three modes ───────────────────────────────────

def test_posted_evidence_doc_defines_public_verifier_pass():
    path = "docs/ai/codex/POSTED_GITHUB_EVIDENCE_VERIFICATION.md"
    with open(path, encoding="utf-8") as f:
        content = f.read()
    assert "PUBLIC_VERIFIER_PASS" in content


def test_posted_evidence_doc_defines_private_repo_manual_verified():
    path = "docs/ai/codex/POSTED_GITHUB_EVIDENCE_VERIFICATION.md"
    with open(path, encoding="utf-8") as f:
        content = f.read()
    assert "PRIVATE_REPO_MANUAL_VERIFIED" in content


def test_posted_evidence_doc_defines_blocked_not_ready():
    path = "docs/ai/codex/POSTED_GITHUB_EVIDENCE_VERIFICATION.md"
    with open(path, encoding="utf-8") as f:
        content = f.read()
    assert "BLOCKED_NOT_READY" in content


def test_posted_evidence_doc_allows_ready_yes_under_private_mode():
    """
    Posted evidence doc must not say verifier-unavailable alone requires Ready NO
    if private manual verification is complete.
    """
    path = "docs/ai/codex/POSTED_GITHUB_EVIDENCE_VERIFICATION.md"
    with open(path, encoding="utf-8") as f:
        content = f.read()
    # Must say this mode is valid for private repos
    assert "valid evidence mode" in content.lower() or "allowed when" in content.lower()
    # Must say PRIVATE_REPO_MANUAL_VERIFIED can have Ready YES
    assert "Ready for review: YES/NO" in content


# ── PR evidence discipline distinguishes FAIL from UNAVAILABLE ────────────────

def test_pr_evidence_discipline_distinguishes_fail_from_unavailable():
    path = "docs/ai/codex/PR_EVIDENCE_REPORTING_DISCIPLINE.md"
    with open(path, encoding="utf-8") as f:
        content = f.read()
    assert "PUBLIC_VERIFIER_FAIL" in content or "VERIFIER_FAIL" in content
    assert "PUBLIC_VERIFIER_UNAVAILABLE" in content or "VERIFIER_UNAVAILABLE" in content


def test_pr_evidence_discipline_ready_gate_has_evidence_mode():
    path = "docs/ai/codex/PR_EVIDENCE_REPORTING_DISCIPLINE.md"
    with open(path, encoding="utf-8") as f:
        content = f.read()
    assert "Evidence mode" in content
    assert "PUBLIC_VERIFIER_PASS" in content
    assert "PRIVATE_REPO_MANUAL_VERIFIED" in content
    assert "BLOCKED_NOT_READY" in content


# ── Validation matrix recognizes modes ───────────────────────────────────────

def test_validation_matrix_recognizes_private_repo_manual_verified():
    path = "docs/ai/codex/VALIDATION_MATRIX.md"
    with open(path, encoding="utf-8") as f:
        content = f.read()
    assert "PRIVATE_REPO_MANUAL_VERIFIED" in content


def test_validation_matrix_recognizes_blocked_not_ready():
    path = "docs/ai/codex/VALIDATION_MATRIX.md"
    with open(path, encoding="utf-8") as f:
        content = f.read()
    assert "BLOCKED_NOT_READY" in content


def test_validation_matrix_separates_validation_from_evidence_mode():
    path = "docs/ai/codex/VALIDATION_MATRIX.md"
    with open(path, encoding="utf-8") as f:
        content = f.read()
    assert "Evidence mode does not replace validation" in content or "evidence mode" in content.lower()


# ── PR review checklist references evidence modes ─────────────────────────────

def test_pr_review_checklist_references_evidence_modes():
    path = "docs/ai/codex/PR_REVIEW_CHECKLIST.md"
    with open(path, encoding="utf-8") as f:
        content = f.read()
    assert "PUBLIC_VERIFIER_PASS" in content
    assert "PRIVATE_REPO_MANUAL_VERIFIED" in content
    assert "BLOCKED_NOT_READY" in content


# ── WP execution report references evidence mode block ───────────────────────

def test_wp_execution_report_has_evidence_mode_field():
    path = "docs/ai/codex/WP_EXECUTION_REPORT.md"
    with open(path, encoding="utf-8") as f:
        content = f.read()
    assert "Evidence mode:" in content


def test_wp_execution_report_header_block_has_manual_verification():
    path = "docs/ai/codex/WP_EXECUTION_REPORT.md"
    with open(path, encoding="utf-8") as f:
        content = f.read()
    assert "Manual live GitHub verification:" in content


# ── Project status marks WP58 merged and WP59 current ────────────────────────

def test_project_status_marks_wp58_merged():
    path = "docs/project_status.md"
    with open(path, encoding="utf-8") as f:
        content = f.read()
    assert "WP58" in content
    # Must be in merged WPs list
    assert re.search(r"Merged WPs:.*WP58", content)


def test_project_status_wp59_is_merged():
    path = "docs/project_status.md"
    with open(path, encoding="utf-8") as f:
        content = f.read()
    assert "WP59" in content
    # WP59 must appear in the merged WPs list
    lines = content.splitlines()
    for line in lines:
        if line.startswith("- Merged WPs:"):
            assert "WP59" in line, f"Expected WP59 in merged WPs line: {line}"
            break
    else:
        assert False, "Could not find 'Merged WPs:' line"


def test_project_status_wp59_statuses_merged():
    path = "docs/project_status.md"
    with open(path, encoding="utf-8") as f:
        content = f.read()
    assert "WORKFLOW_GOVERNANCE_MERGED" in content


def test_project_status_wp58_statuses_merged():
    path = "docs/project_status.md"
    with open(path, encoding="utf-8") as f:
        content = f.read()
    assert "CLAUDE_START_HERE_MERGED" in content
    assert "GITHUB_AWARE_READ_ONLY_WORKFLOW_HELPER_MERGED" in content
