from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

WORKFLOW_DOCS = (
    ROOT / "CODEX_START_HERE.md",
    ROOT / "docs" / "ai" / "codex" / "README.md",
    ROOT / "docs" / "ai" / "codex" / "WP_EXECUTION_REPORT.md",
    ROOT / "docs" / "ai" / "codex" / "VALIDATION_MATRIX.md",
    ROOT / "docs" / "ai" / "codex" / "PR_REVIEW_CHECKLIST.md",
    ROOT / "docs" / "ai" / "codex" / "PROJECT_STATUS_UPDATE_RULES.md",
    ROOT / "docs" / "ai" / "codex" / "PROTECTED_PATHS.md",
)

DEPENDENCY_FILE_NAMES = {
    "pyproject.toml",
    "requirements.txt",
    "requirements-dev.txt",
    "requirements.lock",
    "poetry.lock",
    "uv.lock",
    "pdm.lock",
    "Pipfile.lock",
    "package.json",
    "package-lock.json",
}

FORBIDDEN_AGENT_DEPENDENCY_TERMS = (
    "hermes",
    "openai",
    "anthropic",
    "langchain",
    "llama-index",
    "crewai",
    "autogen",
)

FORBIDDEN_IMPLEMENTATION_PATHS = (
    "src/agents",
    "src/agent_layer",
    "tools/agents",
    "tools/hermes",
    "tools/agent_context_export",
    "tools/agent_context_export.py",
    "agent_reports",
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _git_ls_files() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        timeout=60,
    )
    return [line.strip().replace("\\", "/") for line in result.stdout.splitlines() if line.strip()]


def test_required_workflow_docs_exist() -> None:
    for path in WORKFLOW_DOCS:
        assert path.is_file(), f"missing {path.relative_to(ROOT)}"


def test_codex_start_here_contains_required_startup_and_stop_language() -> None:
    text = _read(ROOT / "CODEX_START_HERE.md")
    lower = text.lower()

    for expected in (
        "AGENTS.md",
        "docs/project_status.md",
        "docs/repo_truth_index.md",
        "docs/deferred_items_log.md",
        "docs/ai/codex/README.md",
    ):
        assert expected in text

    assert "stop and report" in lower


def test_wp_execution_report_contains_required_final_report_sections() -> None:
    text = _read(ROOT / "docs" / "ai" / "codex" / "WP_EXECUTION_REPORT.md")

    for expected in (
        "full final report",
        "Branch / base",
        "Repo-truth discovery",
        "Delivered changes",
        "Validation results",
        "Validation gates",
        "Forbidden-scope check",
        "Generated-artifact check",
        "Ready for review",
    ):
        assert expected in text
    # "PR body does not replace" was the pre-WP91 mandatory wording — now retired
    assert "PR body does not replace" not in text


def test_validation_matrix_contains_required_package_classes() -> None:
    text = _read(ROOT / "docs" / "ai" / "codex" / "VALIDATION_MATRIX.md").lower()

    for expected in (
        "docs-only policy",
        "schema-only",
        "workflow/governance",
        "local report/export",
        "read-only public-data",
        "official-client sandbox",
        "security/tooling",
        "runtime dependency",
        "future live-trading",
    ):
        assert expected in text


def test_pr_review_checklist_contains_recurring_missing_checks() -> None:
    text = _read(ROOT / "docs" / "ai" / "codex" / "PR_REVIEW_CHECKLIST.md")

    for expected in (
        "final report PR comment",
        "`docs/project_status.md` security wording uses the current WP number",
        "Tests were rerun after the final commit",
        "Generated-artifact guard was rerun after the final commit",
        "dependency or lock files",
        "Deferred items",
    ):
        assert expected in text


def test_project_status_rules_prevent_stale_security_wording() -> None:
    text = _read(ROOT / "docs" / "ai" / "codex" / "PROJECT_STATUS_UPDATE_RULES.md")

    for expected in (
        "current WP",
        "unavailable or skipped, not passed",
        "branch-state phrasing",
        "Merged WPs list must include only already merged WPs",
        "conservative and conditional",
    ):
        assert expected in text


def test_protected_paths_doc_contains_required_boundaries() -> None:
    text = _read(ROOT / "docs" / "ai" / "codex" / "PROTECTED_PATHS.md").lower()

    for expected in (
        "live trading",
        "credentials",
        "authenticated clients",
        "order, execution, signing",
        "scheduler, daemon",
        "bot loop",
        "database, dashboard, deployment",
        "runtime dependencies",
        "generated artifacts",
    ):
        assert expected in text


def test_pr_template_contains_mandatory_workflow_checkboxes() -> None:
    text = _read(ROOT / ".github" / "pull_request_template.md")

    for expected in (
        "Full WP final report posted as PR comment",
        "PR body is not the only final report",
        "Remote Main Sync Gate",
        "Generated Artifact Guard passed after final commit",
        "Full pytest passed after final commit",
        "`docs/project_status.md` security wording updated to current WP",
        "Unavailable semgrep/pip-audit or other tools not called passed",
        "Ready for review",
    ):
        assert expected in text


def test_work_package_template_contains_required_codex_ready_fields() -> None:
    text = _read(ROOT / "docs" / "work_package_template.md")

    for expected in (
        "Package Identity",
        "Package Class",
        "Authorization Basis",
        "Current Expected Repo Truth",
        "Required Discovery Before Editing",
        "Exact Changed-File Set",
        "Stop/Report Triggers",
        "Final PR Comment",
        "Ready for review",
    ):
        assert expected in text


def test_repo_truth_index_records_new_codex_workflow_docs() -> None:
    text = _read(ROOT / "docs" / "repo_truth_index.md")

    for path in (
        "CODEX_START_HERE.md",
        "docs/ai/codex/README.md",
        "docs/ai/codex/WP_EXECUTION_REPORT.md",
        "docs/ai/codex/VALIDATION_MATRIX.md",
        "docs/ai/codex/PR_REVIEW_CHECKLIST.md",
        "docs/ai/codex/PROJECT_STATUS_UPDATE_RULES.md",
        "docs/ai/codex/PROTECTED_PATHS.md",
    ):
        assert path in text


def test_no_runtime_exporter_or_report_paths_are_added() -> None:
    tracked = _git_ls_files()
    for forbidden in FORBIDDEN_IMPLEMENTATION_PATHS:
        assert not any(path == forbidden or path.startswith(f"{forbidden}/") for path in tracked)
        assert not (ROOT / forbidden).exists(), f"unexpected path exists: {forbidden}"


def test_wp_bundling_policy_exists() -> None:
    path = ROOT / "docs" / "ai" / "codex" / "WP_BUNDLING_POLICY.md"
    assert path.is_file(), "docs/ai/codex/WP_BUNDLING_POLICY.md must exist"


def test_wp_bundling_policy_contains_package_size_classes() -> None:
    text = _read(ROOT / "docs" / "ai" / "codex" / "WP_BUNDLING_POLICY.md")
    for expected in ("S", "M", "L", "XL"):
        assert f"| {expected} |" in text or f"Class | Description" in text
    assert "S" in text
    assert "M" in text
    assert "L" in text
    assert "XL" in text


def test_wp_bundling_policy_contains_risk_class_bundling_principle() -> None:
    text = _read(ROOT / "docs" / "ai" / "codex" / "WP_BUNDLING_POLICY.md").lower()
    for expected in (
        "risk-class bundling principle",
        "same safety class",
        "mode boundaries",
        "paper trading",
        "credentials",
        "execution",
        "hermes runtime",
        "live trading",
    ):
        assert expected in text, f"WP_BUNDLING_POLICY.md missing: {expected!r}"


def test_wp_bundling_policy_contains_allowed_and_forbidden_bundles() -> None:
    text = _read(ROOT / "docs" / "ai" / "codex" / "WP_BUNDLING_POLICY.md").lower()
    assert "allowed bundle" in text
    assert "forbidden bundle" in text


def test_wp_bundling_policy_contains_follow_up_classification() -> None:
    text = _read(ROOT / "docs" / "ai" / "codex" / "WP_BUNDLING_POLICY.md")
    for expected in (
        "Follow-up correction required",
        "Classification",
        "Systemic assessment",
        "Separate hardening WP needed",
    ):
        assert expected in text, f"WP_BUNDLING_POLICY.md missing: {expected!r}"


def test_wp_bundling_policy_contains_posted_evidence_self_check() -> None:
    text = _read(ROOT / "docs" / "ai" / "codex" / "WP_BUNDLING_POLICY.md").lower()
    assert "posted evidence self-check" in text
    assert "guard input source" in text


def test_wp_bundling_policy_indexed_in_repo_truth() -> None:
    text = _read(ROOT / "docs" / "repo_truth_index.md")
    assert "WP_BUNDLING_POLICY.md" in text


def test_work_package_template_contains_package_size_class() -> None:
    text = _read(ROOT / "docs" / "work_package_template.md")
    assert "Package Size Class" in text


def test_work_package_template_contains_risk_class_bundle_justification() -> None:
    text = _read(ROOT / "docs" / "work_package_template.md")
    assert "Risk-Class Bundle Justification" in text


def test_work_package_template_contains_follow_up_classification() -> None:
    text = _read(ROOT / "docs" / "work_package_template.md")
    assert "Follow-up process-defect classification" in text or "Follow-Up Process-Defect Classification" in text


def test_work_package_template_contains_posted_evidence_self_check() -> None:
    text = _read(ROOT / "docs" / "work_package_template.md")
    assert "Posted Evidence Self-Check" in text


def test_pr_review_checklist_contains_follow_up_classification_check() -> None:
    text = _read(ROOT / "docs" / "ai" / "codex" / "PR_REVIEW_CHECKLIST.md")
    assert "follow-up classification" in text.lower()


def test_pr_review_checklist_contains_bundle_risk_check() -> None:
    text = _read(ROOT / "docs" / "ai" / "codex" / "PR_REVIEW_CHECKLIST.md")
    assert "bundle" in text.lower()
    assert "risk class" in text.lower() or "bundle is within one risk class" in text.lower()


def test_pr_review_checklist_contains_current_final_evidence_check() -> None:
    text = _read(ROOT / "docs" / "ai" / "codex" / "PR_REVIEW_CHECKLIST.md")
    assert "current final evidence" in text.lower() or "CURRENT FINAL WP EVIDENCE" in text


def test_pr_review_checklist_contains_guard_input_source_check() -> None:
    text = _read(ROOT / "docs" / "ai" / "codex" / "PR_REVIEW_CHECKLIST.md")
    assert "Guard input source" in text


def test_pr_template_contains_follow_up_classification_check() -> None:
    text = _read(ROOT / ".github" / "pull_request_template.md")
    assert "follow-up" in text.lower() or "Follow-up" in text


def test_pr_template_contains_bundle_risk_check() -> None:
    text = _read(ROOT / ".github" / "pull_request_template.md")
    assert "bundle" in text.lower()


def test_pr_template_contains_guard_input_source_check() -> None:
    text = _read(ROOT / ".github" / "pull_request_template.md")
    assert "Guard input source" in text


def test_pr_template_contains_package_size_class_check() -> None:
    text = _read(ROOT / ".github" / "pull_request_template.md")
    assert "Package size class" in text or "package size class" in text.lower()


def test_project_status_reflects_wp53_merged() -> None:
    text = _read(ROOT / "docs" / "project_status.md")
    merged_line = next(
        line for line in text.splitlines() if line.startswith("- Merged WPs:")
    )
    assert "WP53" in merged_line


def test_project_status_reflects_wp68_merged() -> None:
    text = _read(ROOT / "docs" / "project_status.md")
    merged_line = next(
        line for line in text.splitlines() if line.startswith("- Merged WPs:")
    )
    assert "WP68" in merged_line


def test_project_status_reflects_wp63_merged() -> None:
    text = _read(ROOT / "docs" / "project_status.md")
    merged_line = next(
        line for line in text.splitlines() if line.startswith("- Merged WPs:")
    )
    assert "WP63" in merged_line


def test_project_status_reflects_wp62_merged() -> None:
    text = _read(ROOT / "docs" / "project_status.md")
    merged_line = next(
        line for line in text.splitlines() if line.startswith("- Merged WPs:")
    )
    assert "WP62" in merged_line


def test_project_status_reflects_wp61_merged() -> None:
    text = _read(ROOT / "docs" / "project_status.md")
    merged_line = next(
        line for line in text.splitlines() if line.startswith("- Merged WPs:")
    )
    assert "WP61" in merged_line


def test_project_status_reflects_wp58_merged() -> None:
    text = _read(ROOT / "docs" / "project_status.md")
    merged_line = next(
        line for line in text.splitlines() if line.startswith("- Merged WPs:")
    )
    assert "WP58" in merged_line


def test_project_status_reflects_wp59_merged() -> None:
    text = _read(ROOT / "docs" / "project_status.md")
    merged_line = next(
        line for line in text.splitlines() if line.startswith("- Merged WPs:")
    )
    assert "WP59" in merged_line


def test_project_status_reflects_wp69_merged() -> None:
    text = _read(ROOT / "docs" / "project_status.md")
    merged_line = next(
        line for line in text.splitlines() if line.startswith("- Merged WPs:")
    )
    assert "WP69" in merged_line


def test_project_status_reflects_wp79_branch() -> None:
    text = _read(ROOT / "docs" / "project_status.md")
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


def test_project_status_reflects_wp64_merged() -> None:
    text = _read(ROOT / "docs" / "project_status.md")
    merged_line = next(
        line for line in text.splitlines() if line.startswith("- Merged WPs:")
    )
    assert "WP64" in merged_line


def test_project_status_reflects_wp60a_merged() -> None:
    text = _read(ROOT / "docs" / "project_status.md")
    merged_line = next(
        line for line in text.splitlines() if line.startswith("- Merged WPs:")
    )
    assert "WP60A" in merged_line


def test_project_status_reflects_wp56_merged() -> None:
    text = _read(ROOT / "docs" / "project_status.md")
    merged_line = next(
        line for line in text.splitlines() if line.startswith("- Merged WPs:")
    )
    assert "WP56" in merged_line


def test_project_status_reflects_wp55_merged() -> None:
    text = _read(ROOT / "docs" / "project_status.md")
    merged_line = next(
        line for line in text.splitlines() if line.startswith("- Merged WPs:")
    )
    assert "WP55" in merged_line


def test_resolution_ambiguity_label_schema_validator_indexed() -> None:
    text = _read(ROOT / "docs" / "repo_truth_index.md")
    assert "resolution_ambiguity_labels.py" in text


def test_resolution_ambiguity_label_schema_validator_file_exists() -> None:
    path = ROOT / "src" / "data_layer" / "resolution_ambiguity_labels.py"
    assert path.is_file(), "src/data_layer/resolution_ambiguity_labels.py must exist"


def test_wp54_in_merged_wps_in_codex_workflow_check() -> None:
    text = _read(ROOT / "docs" / "project_status.md")
    merged_line = next(
        line for line in text.splitlines() if line.startswith("- Merged WPs:")
    )
    assert "WP54" in merged_line


def test_project_status_data_integrity_hardening_merged_not_on_branch() -> None:
    text = _read(ROOT / "docs" / "project_status.md")
    assert "DATA_INTEGRITY_HARDENING_MERGED" in text
    assert "DATA_INTEGRITY_HARDENING_ON_BRANCH" not in text


def test_no_live_trading_in_bundling_policy_or_codex_docs() -> None:
    for path in (
        ROOT / "docs" / "ai" / "codex" / "WP_BUNDLING_POLICY.md",
        ROOT / "docs" / "work_package_template.md",
    ):
        text = _read(path).lower()
        forbidden_phrases = (
            "place_order",
            "sign_order",
            "execute_trade",
            "submit_order",
            "autonomous trading agent is active",
            "live trading enabled",
            "credentials_in_use",
        )
        for phrase in forbidden_phrases:
            assert phrase not in text, f"{path.name} must not contain: {phrase!r}"


def test_dependency_files_do_not_add_agent_runtime_dependencies() -> None:
    dependency_files = [
        ROOT / tracked
        for tracked in _git_ls_files()
        if Path(tracked).name in DEPENDENCY_FILE_NAMES
    ]

    for path in dependency_files:
        text = _read(path).lower()
        for term in FORBIDDEN_AGENT_DEPENDENCY_TERMS:
            assert term not in text, f"{term} found in {path.relative_to(ROOT)}"


# ── WP58: Posted evidence verifier and new governance docs ───────────────────


def test_claude_start_here_exists() -> None:
    assert (ROOT / "CLAUDE_START_HERE.md").is_file()


def test_posted_github_evidence_verification_doc_exists() -> None:
    assert (ROOT / "docs" / "ai" / "codex" / "POSTED_GITHUB_EVIDENCE_VERIFICATION.md").is_file()


def test_negative_test_matrix_policy_doc_exists() -> None:
    assert (ROOT / "docs" / "ai" / "codex" / "NEGATIVE_TEST_MATRIX_POLICY.md").is_file()


def test_posted_pr_evidence_verifier_exists() -> None:
    assert (ROOT / "tools" / "git" / "posted_pr_evidence_verifier.py").is_file()


def test_pr_template_contains_posted_evidence_section() -> None:
    path = ROOT / ".github" / "pull_request_template.md"
    content = _read(path)
    assert "posted" in content.lower() or "POSTED" in content


def test_validation_matrix_includes_github_aware_class() -> None:
    path = ROOT / "docs" / "ai" / "codex" / "VALIDATION_MATRIX.md"
    content = _read(path)
    assert (
        "github-aware" in content.lower()
        or "github_aware" in content.lower()
        or "posted" in content.lower()
    )


def test_pr_review_checklist_includes_current_final_verification() -> None:
    path = ROOT / "docs" / "ai" / "codex" / "PR_REVIEW_CHECKLIST.md"
    content = _read(path)
    assert "current-final" in content.lower() or "CURRENT FINAL" in content


def test_wp_execution_report_includes_posted_evidence_section() -> None:
    path = ROOT / "docs" / "ai" / "codex" / "WP_EXECUTION_REPORT.md"
    content = _read(path)
    assert (
        "Posted GitHub" in content
        or "posted github" in content.lower()
        or "posted pr evidence" in content.lower()
    )


# ── WP60A: Agent-neutral startup layer ───────────────────────────────────────


def test_ai_coding_agent_start_here_exists() -> None:
    assert (ROOT / "AI_CODING_AGENT_START_HERE.md").is_file()


def test_agents_md_title_no_longer_codex_rulebook() -> None:
    text = _read(ROOT / "AGENTS.md")
    assert "# Codex Rulebook" not in text


def test_codex_start_here_references_shared_startup() -> None:
    text = _read(ROOT / "CODEX_START_HERE.md")
    assert "AI_CODING_AGENT_START_HERE.md" in text


def test_claude_start_here_references_shared_startup() -> None:
    text = _read(ROOT / "CLAUDE_START_HERE.md")
    assert "AI_CODING_AGENT_START_HERE.md" in text


def test_pr_template_contains_ai_coding_agent_section() -> None:
    text = _read(ROOT / ".github" / "pull_request_template.md")
    assert "AI coding agent" in text


def test_work_package_template_contains_execution_agent_field() -> None:
    text = _read(ROOT / "docs" / "work_package_template.md")
    assert "Execution agent" in text


def test_repo_truth_index_contains_ai_coding_agent_start_here() -> None:
    text = _read(ROOT / "docs" / "repo_truth_index.md")
    assert "AI_CODING_AGENT_START_HERE.md" in text


def test_project_status_includes_agent_neutral_start_layer_status() -> None:
    text = _read(ROOT / "docs" / "project_status.md")
    assert "AGENT_NEUTRAL_START_LAYER_MERGED" in text


# ── WP86: Execution Package Discipline Adoption ──────────────────────────────


def test_wp_drafting_standard_exists() -> None:
    assert (ROOT / "docs" / "ai" / "codex" / "WP_DRAFTING_STANDARD.md").is_file()


def test_status_entries_readme_exists() -> None:
    assert (ROOT / "docs" / "status_entries" / "README.md").is_file()


def test_work_package_template_contains_authority_posture() -> None:
    text = _read(ROOT / "docs" / "work_package_template.md")
    assert "Authority / Non-Authority Posture" in text


def test_work_package_template_contains_hard_merge_gate() -> None:
    text = _read(ROOT / "docs" / "work_package_template.md")
    assert "Hard Merge Gate" in text


def test_work_package_template_contains_context_budget() -> None:
    text = _read(ROOT / "docs" / "work_package_template.md")
    assert "Context Budget" in text


def test_work_package_template_contains_compatibility_check() -> None:
    text = _read(ROOT / "docs" / "work_package_template.md")
    assert "Compatibility / Impossibility Check" in text


def test_work_package_template_contains_concrete_stop_conditions() -> None:
    text = _read(ROOT / "docs" / "work_package_template.md")
    assert "Concrete Stop Conditions" in text


def test_work_package_template_contains_requirement_traceability() -> None:
    text = _read(ROOT / "docs" / "work_package_template.md")
    assert "Requirement-to-Evidence Traceability" in text


def test_work_package_template_contains_status_fragment() -> None:
    text = _read(ROOT / "docs" / "work_package_template.md")
    assert "Status Fragment" in text or "status_entries" in text


def test_wp_execution_report_requires_status_fragment() -> None:
    text = _read(ROOT / "docs" / "ai" / "codex" / "WP_EXECUTION_REPORT.md")
    assert "status" in text.lower() and ("fragment" in text.lower() or "status_entries" in text.lower() or "committed" in text.lower())


def test_pr_review_checklist_requires_self_diagnosis() -> None:
    text = _read(ROOT / "docs" / "ai" / "codex" / "PR_REVIEW_CHECKLIST.md").lower()
    assert "root cause" in text
    assert "preventable" in text


def test_pr_review_checklist_requires_status_fragment_check() -> None:
    text = _read(ROOT / "docs" / "ai" / "codex" / "PR_REVIEW_CHECKLIST.md").lower()
    assert "status fragment" in text or "status_entries" in text


def test_pr_review_checklist_requires_traceability_check() -> None:
    text = _read(ROOT / "docs" / "ai" / "codex" / "PR_REVIEW_CHECKLIST.md").lower()
    assert "traceability" in text


def test_pr_review_checklist_requires_compatibility_check() -> None:
    text = _read(ROOT / "docs" / "ai" / "codex" / "PR_REVIEW_CHECKLIST.md").lower()
    assert "compatibility" in text or "impossibility" in text


def test_validation_matrix_includes_risk_levels() -> None:
    text = _read(ROOT / "docs" / "ai" / "codex" / "VALIDATION_MATRIX.md").lower()
    assert "risk level" in text or "risk class" in text or "package class" in text


def test_validation_matrix_includes_validator_class() -> None:
    text = _read(ROOT / "docs" / "ai" / "codex" / "VALIDATION_MATRIX.md").lower()
    assert "validator" in text


def test_validation_matrix_includes_report_class() -> None:
    text = _read(ROOT / "docs" / "ai" / "codex" / "VALIDATION_MATRIX.md").lower()
    assert "report" in text


def test_validation_matrix_includes_status_fragment_requirement() -> None:
    text = _read(ROOT / "docs" / "ai" / "codex" / "VALIDATION_MATRIX.md").lower()
    assert "status fragment" in text or "status_entries" in text or "committed evidence" in text


def test_codex_readme_states_docs_apply_to_claude_and_codex() -> None:
    text = _read(ROOT / "docs" / "ai" / "codex" / "README.md").lower()
    assert "claude code" in text
    assert "codex" in text
    assert ("shared" in text or "both" in text or "applies to" in text)


def test_codex_readme_clarifies_prompt_wrappers_non_canonical() -> None:
    text = _read(ROOT / "docs" / "ai" / "codex" / "README.md").lower()
    assert "non-canonical" in text or "not canonical" in text or "prompt wrapper" in text


def test_codex_execution_guidelines_contains_worktree_first() -> None:
    text = _read(ROOT / "docs" / "codex_execution_guidelines.md").lower()
    assert "worktree" in text


def test_status_entries_readme_defines_evidence_distinction() -> None:
    text = _read(ROOT / "docs" / "status_entries" / "README.md")
    assert "LOCAL_DRAFT_VERIFIED" in text
    assert "POSTED_GITHUB_API_VERIFIED" in text
    assert "MANUAL_UI_VERIFIED" in text


def test_status_entries_readme_states_local_drafts_do_not_count() -> None:
    text = _read(ROOT / "docs" / "status_entries" / "README.md").lower()
    assert "local draft" in text
    assert "posted" in text


def test_evidence_doc_requires_github_refetch() -> None:
    text = _read(ROOT / "docs" / "ai" / "codex" / "PR_EVIDENCE_REPORTING_DISCIPLINE.md").lower()
    assert "re-fetch" in text or "refetch" in text or "re-fetching" in text or "posted github" in text


def test_evidence_doc_states_local_drafts_do_not_count() -> None:
    text = _read(ROOT / "docs" / "ai" / "codex" / "PR_EVIDENCE_REPORTING_DISCIPLINE.md")
    assert "LOCAL_DRAFT_VERIFIED" in text


def test_pr_template_contains_status_fragment_section() -> None:
    text = _read(ROOT / ".github" / "pull_request_template.md").lower()
    assert "status fragment" in text or "status_entries" in text


def test_pr_template_contains_traceability_section() -> None:
    text = _read(ROOT / ".github" / "pull_request_template.md").lower()
    assert "traceability" in text


def test_pr_template_contains_compatibility_section() -> None:
    text = _read(ROOT / ".github" / "pull_request_template.md").lower()
    assert "compatibility" in text or "impossibility" in text


def test_protected_paths_centralizes_boundary_groups() -> None:
    text = _read(ROOT / "docs" / "ai" / "codex" / "PROTECTED_PATHS.md").lower()
    assert "boundary group" in text or "centralized boundary" in text or "centralize" in text


# ── WP88: Evidence Architecture And Result-Object Invariant Repair ────────────


def test_evidence_architecture_doc_exists() -> None:
    assert (ROOT / "docs" / "ai" / "codex" / "EVIDENCE_ARCHITECTURE.md").is_file()


def test_result_output_invariant_standard_doc_exists() -> None:
    assert (ROOT / "docs" / "ai" / "codex" / "RESULT_OUTPUT_INVARIANT_STANDARD.md").is_file()


def test_followup_prompt_standard_doc_exists() -> None:
    assert (ROOT / "docs" / "ai" / "codex" / "FOLLOWUP_PROMPT_STANDARD.md").is_file()


def test_evidence_architecture_defines_pr_body_as_current_review_surface() -> None:
    text = _read(ROOT / "docs" / "ai" / "codex" / "EVIDENCE_ARCHITECTURE.md").lower()
    assert "pr body" in text
    assert "current review" in text


def test_evidence_architecture_defines_status_fragment_as_stable() -> None:
    text = _read(ROOT / "docs" / "ai" / "codex" / "EVIDENCE_ARCHITECTURE.md").lower()
    assert "stable" in text
    assert "non-self-referential" in text or "non self-referential" in text or "non-self referential" in text


def test_evidence_architecture_forbids_current_live_head_in_status_fragment() -> None:
    text = _read(ROOT / "docs" / "ai" / "codex" / "EVIDENCE_ARCHITECTURE.md").lower()
    assert "current live" in text
    assert "fixed sha" in text or "fixed sha" in text.replace("_", " ")


def test_evidence_architecture_defines_final_comment_as_transition_only() -> None:
    text = _read(ROOT / "docs" / "ai" / "codex" / "EVIDENCE_ARCHITECTURE.md").lower()
    assert "transition" in text
    assert "final" in text


def test_evidence_architecture_contains_contradiction_matrix() -> None:
    text = _read(ROOT / "docs" / "ai" / "codex" / "EVIDENCE_ARCHITECTURE.md").lower()
    assert "contradiction" in text or "invalid combination" in text or "invalid state" in text


def test_evidence_architecture_blocks_not_verified_plus_ready_yes() -> None:
    text = _read(ROOT / "docs" / "ai" / "codex" / "EVIDENCE_ARCHITECTURE.md")
    assert "NOT_VERIFIED" in text
    assert "Ready for review: YES" in text or "ready for review" in text.lower()
    assert "Block merge" in text or "block merge" in text.lower()


def test_result_output_invariant_standard_requires_field_inventory() -> None:
    text = _read(ROOT / "docs" / "ai" / "codex" / "RESULT_OUTPUT_INVARIANT_STANDARD.md").lower()
    assert "public field" in text or "field" in text
    assert "enumerate" in text or "inventory" in text or "all public" in text


def test_result_output_invariant_standard_requires_serializer_losslessness() -> None:
    text = _read(ROOT / "docs" / "ai" / "codex" / "RESULT_OUTPUT_INVARIANT_STANDARD.md").lower()
    assert "lossless" in text or "manual serializer" in text


def test_result_output_invariant_standard_requires_invalid_output_full_scan() -> None:
    text = _read(ROOT / "docs" / "ai" / "codex" / "RESULT_OUTPUT_INVARIANT_STANDARD.md").lower()
    assert "invalid" in text
    assert "full" in text or "recursive" in text or "entire" in text
    assert "scan" in text or "check" in text


def test_followup_prompt_standard_requires_root_cause_classification() -> None:
    text = _read(ROOT / "docs" / "ai" / "codex" / "FOLLOWUP_PROMPT_STANDARD.md").lower()
    assert "root cause" in text
    assert "classif" in text


def test_status_entries_readme_requires_non_self_referential_wording() -> None:
    text = _read(ROOT / "docs" / "status_entries" / "README.md").lower()
    assert "non-self-referential" in text or "non self referential" in text or "non-self referential" in text


def test_status_entries_readme_forbids_head_commit_for_in_review_head() -> None:
    text = _read(ROOT / "docs" / "status_entries" / "README.md")
    assert "Validated implementation commit" in text or "validated implementation commit" in text.lower()
    assert "Head commit" not in text or "must not" in text.lower() or "forbidden" in text.lower()


def test_pr_review_checklist_blocks_not_verified_plus_ready_yes() -> None:
    text = _read(ROOT / "docs" / "ai" / "codex" / "PR_REVIEW_CHECKLIST.md")
    assert "NOT_VERIFIED" in text
    assert "Ready for review: YES" in text or "ready for review" in text.lower()


def test_pr_review_checklist_blocks_status_fragment_with_live_head_sha() -> None:
    text = _read(ROOT / "docs" / "ai" / "codex" / "PR_REVIEW_CHECKLIST.md").lower()
    assert "status fragment" in text
    assert "current live" in text or "live pr head" in text or "fixed sha" in text


def test_pr_review_checklist_requires_result_object_field_coverage() -> None:
    text = _read(ROOT / "docs" / "ai" / "codex" / "PR_REVIEW_CHECKLIST.md").lower()
    assert "field" in text
    assert "coverage" in text or "public field" in text


def test_validation_matrix_references_field_coverage_gate() -> None:
    text = _read(ROOT / "docs" / "ai" / "codex" / "VALIDATION_MATRIX.md").lower()
    assert "field" in text and "coverage" in text


def test_validation_matrix_references_evidence_architecture_model_d() -> None:
    text = _read(ROOT / "docs" / "ai" / "codex" / "VALIDATION_MATRIX.md").lower()
    assert "model d" in text or "evidence architecture" in text


def test_work_package_template_references_evidence_architecture() -> None:
    text = _read(ROOT / "docs" / "work_package_template.md").lower()
    assert "evidence architecture" in text or "model d" in text


def test_work_package_template_references_result_output_invariant_standard() -> None:
    text = _read(ROOT / "docs" / "work_package_template.md").lower()
    assert "result" in text and ("invariant" in text or "field-coverage" in text or "field coverage" in text)


def test_pr_template_contains_evidence_architecture_section() -> None:
    text = _read(ROOT / ".github" / "pull_request_template.md").lower()
    assert "evidence architecture" in text or "model d" in text


def test_codex_readme_references_evidence_architecture() -> None:
    text = _read(ROOT / "docs" / "ai" / "codex" / "README.md").lower()
    assert "evidence architecture" in text or "model d" in text


def test_codex_readme_references_result_output_invariant_standard() -> None:
    text = _read(ROOT / "docs" / "ai" / "codex" / "README.md").lower()
    assert "result" in text and "invariant" in text


def test_codex_readme_references_followup_prompt_standard() -> None:
    text = _read(ROOT / "docs" / "ai" / "codex" / "README.md").lower()
    assert "follow" in text and "root cause" in text


def test_protected_paths_includes_paper_engine_group() -> None:
    text = _read(ROOT / "docs" / "ai" / "codex" / "PROTECTED_PATHS.md").lower()
    assert "paper engine" in text


def test_protected_paths_includes_scheduler_group() -> None:
    text = _read(ROOT / "docs" / "ai" / "codex" / "PROTECTED_PATHS.md").lower()
    assert "scheduler" in text


def test_project_status_reflects_wp84_merged() -> None:
    text = _read(ROOT / "docs" / "project_status.md")
    merged_line = next(
        line for line in text.splitlines() if line.startswith("- Merged WPs:")
    )
    assert "WP84" in merged_line


def test_project_status_reflects_wp86_branch() -> None:
    text = _read(ROOT / "docs" / "project_status.md")
    branch_line = next(
        line for line in text.splitlines() if line.startswith("- Current branch:")
    )
    assert "see GitHub PR metadata and PR body" in branch_line or any(wp in branch_line for wp in (
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


def test_repo_truth_index_references_wp_drafting_standard() -> None:
    text = _read(ROOT / "docs" / "repo_truth_index.md")
    assert "WP_DRAFTING_STANDARD.md" in text


def test_repo_truth_index_references_status_entries_readme() -> None:
    text = _read(ROOT / "docs" / "repo_truth_index.md")
    assert "status_entries" in text or "status entries" in text.lower()


def test_wp_drafting_standard_contains_authority_posture() -> None:
    text = _read(ROOT / "docs" / "ai" / "codex" / "WP_DRAFTING_STANDARD.md")
    assert "Authority / Non-Authority Posture" in text


def test_wp_drafting_standard_contains_hard_merge_gate() -> None:
    text = _read(ROOT / "docs" / "ai" / "codex" / "WP_DRAFTING_STANDARD.md")
    assert "Hard Merge Gate" in text


def test_wp_drafting_standard_contains_context_budget() -> None:
    text = _read(ROOT / "docs" / "ai" / "codex" / "WP_DRAFTING_STANDARD.md")
    assert "Context Budget" in text


def test_wp_drafting_standard_contains_compatibility_check() -> None:
    text = _read(ROOT / "docs" / "ai" / "codex" / "WP_DRAFTING_STANDARD.md")
    assert "Compatibility / Impossibility Check" in text


def test_wp_drafting_standard_contains_stop_conditions() -> None:
    text = _read(ROOT / "docs" / "ai" / "codex" / "WP_DRAFTING_STANDARD.md")
    assert "Concrete Stop Conditions" in text


def test_wp_drafting_standard_contains_traceability() -> None:
    text = _read(ROOT / "docs" / "ai" / "codex" / "WP_DRAFTING_STANDARD.md")
    assert "Requirement-to-Evidence Traceability" in text


def test_wp_drafting_standard_contains_worktree_first() -> None:
    text = _read(ROOT / "docs" / "ai" / "codex" / "WP_DRAFTING_STANDARD.md").lower()
    assert "worktree" in text


def test_wp_drafting_standard_contains_evidence_model() -> None:
    text = _read(ROOT / "docs" / "ai" / "codex" / "WP_DRAFTING_STANDARD.md")
    assert "LOCAL_DRAFT_VERIFIED" in text
    assert "POSTED_GITHUB_API_VERIFIED" in text


def test_wp_drafting_standard_contains_prompt_wrappers_non_canonical() -> None:
    text = _read(ROOT / "docs" / "ai" / "codex" / "WP_DRAFTING_STANDARD.md").lower()
    assert "non-canonical" in text or "not canonical" in text or "prompt wrapper" in text


# ── WP91: Final Comment Transition Retirement Decision ────────────────────────


def test_final_comment_policy_doc_exists() -> None:
    assert (ROOT / "docs" / "ai" / "codex" / "FINAL_COMMENT_POLICY.md").is_file()


def test_final_comment_policy_states_final_comments_optional() -> None:
    text = _read(ROOT / "docs" / "ai" / "codex" / "FINAL_COMMENT_POLICY.md").lower()
    assert "optional" in text
    assert "wp91" in text
    assert "non-canonical" in text or "not canonical" in text


def test_final_comment_policy_defines_correct_evidence_mode() -> None:
    text = _read(ROOT / "docs" / "ai" / "codex" / "FINAL_COMMENT_POLICY.md")
    assert "PR_BODY_CURRENT_REVIEW_SURFACE" in text
    assert "STABLE_NON_SELF_REFERENTIAL" in text
    assert "OPTIONAL_REVIEW_CLARIFICATION" in text


def test_evidence_architecture_final_comment_optional_after_wp91() -> None:
    text = _read(ROOT / "docs" / "ai" / "codex" / "EVIDENCE_ARCHITECTURE.md").lower()
    assert "optional" in text
    assert "wp91" in text


def test_evidence_architecture_defines_optional_final_comment_as_non_canonical() -> None:
    text = _read(ROOT / "docs" / "ai" / "codex" / "EVIDENCE_ARCHITECTURE.md").lower()
    assert "non-canonical" in text or "not required for merge" in text or "optional reviewer clarification" in text


def test_pr_evidence_reporting_discipline_final_comment_optional_after_wp91() -> None:
    text = _read(ROOT / "docs" / "ai" / "codex" / "PR_EVIDENCE_REPORTING_DISCIPLINE.md").lower()
    assert "optional" in text
    assert "wp91" in text


def test_pr_review_checklist_final_comment_not_required_after_wp91() -> None:
    text = _read(ROOT / "docs" / "ai" / "codex" / "PR_REVIEW_CHECKLIST.md").lower()
    assert "optional" in text or "wp91" in text
    assert "not a merge blocker" in text or "not required for merge" in text or "absence" in text


def test_status_entries_readme_transition_ended_after_wp91() -> None:
    text = _read(ROOT / "docs" / "status_entries" / "README.md").lower()
    assert "wp91" in text


def test_status_entries_readme_final_comment_optional() -> None:
    text = _read(ROOT / "docs" / "status_entries" / "README.md").lower()
    assert "optional" in text


def test_pr_template_final_comment_optional_note() -> None:
    text = _read(ROOT / ".github" / "pull_request_template.md").lower()
    assert "optional" in text
    assert "wp91" in text


def test_validation_matrix_final_comment_optional_after_wp91() -> None:
    text = _read(ROOT / "docs" / "ai" / "codex" / "VALIDATION_MATRIX.md").lower()
    assert "optional" in text or "wp91" in text


def test_deferred_item_wp90_d002_resolved() -> None:
    text = _read(ROOT / "docs" / "deferred_items_log.md")
    assert "WP90-D002" in text
    lines = [line for line in text.splitlines() if "WP90-D002" in line]
    assert any("RESOLVED" in line for line in lines), "WP90-D002 must be RESOLVED"


def test_deferred_item_wp88_defer_002_resolved() -> None:
    text = _read(ROOT / "docs" / "deferred_items_log.md")
    assert "WP88-DEFER-002" in text
    lines = [line for line in text.splitlines() if "WP88-DEFER-002" in line]
    assert any("RESOLVED" in line for line in lines), "WP88-DEFER-002 must be RESOLVED"


def test_project_status_final_comment_transition_retired() -> None:
    text = _read(ROOT / "docs" / "project_status.md")
    assert "RETIRED_AFTER_WP91" in text or "final comment" in text.lower()


def test_repo_truth_index_references_final_comment_policy() -> None:
    text = _read(ROOT / "docs" / "repo_truth_index.md")
    assert "FINAL_COMMENT_POLICY.md" in text


def test_project_status_reflects_wp90_merged() -> None:
    text = _read(ROOT / "docs" / "project_status.md")
    merged_line = next(
        line for line in text.splitlines() if line.startswith("- Merged WPs:")
    )
    assert "WP90" in merged_line


def test_guard_doc_states_final_comment_not_required_after_wp91() -> None:
    text = _read(ROOT / "docs" / "ai" / "codex" / "PR_EVIDENCE_CONSISTENCY_GUARD.md")
    assert "not required after WP91" in text or "optional after WP91" in text


def test_guard_doc_states_absence_not_a_merge_blocker_after_wp91() -> None:
    text = _read(ROOT / "docs" / "ai" / "codex" / "PR_EVIDENCE_CONSISTENCY_GUARD.md")
    assert "not a merge blocker after WP91" in text or "Absence of a final comment is not" in text


def test_guard_doc_optional_final_comment_is_non_canonical() -> None:
    text = _read(ROOT / "docs" / "ai" / "codex" / "PR_EVIDENCE_CONSISTENCY_GUARD.md")
    assert "non-canonical" in text


def test_guard_doc_require_current_final_marker_is_historical() -> None:
    text = _read(ROOT / "docs" / "ai" / "codex" / "PR_EVIDENCE_CONSISTENCY_GUARD.md")
    assert "WP86" in text or "historical" in text.lower()


def test_posted_evidence_verification_doc_final_comment_not_required_after_wp91() -> None:
    text = _read(ROOT / "docs" / "ai" / "codex" / "POSTED_GITHUB_EVIDENCE_VERIFICATION.md")
    assert "mandatory final GitHub evidence comments are retired" in text or "not required after WP91" in text


def test_posted_evidence_verification_doc_absence_not_a_merge_blocker() -> None:
    text = _read(ROOT / "docs" / "ai" / "codex" / "POSTED_GITHUB_EVIDENCE_VERIFICATION.md")
    assert "not a merge blocker after WP91" in text


def test_posted_evidence_verification_doc_historical_sections_labeled() -> None:
    text = _read(ROOT / "docs" / "ai" / "codex" / "POSTED_GITHUB_EVIDENCE_VERIFICATION.md")
    assert "Historical WP58/WP86" in text or "Not Active After WP91" in text


def test_guard_doc_posted_verifier_cross_reference_aligned_with_wp91() -> None:
    text = _read(ROOT / "docs" / "ai" / "codex" / "PR_EVIDENCE_CONSISTENCY_GUARD.md")
    assert "not a required final-comment merge gate" in text


def test_pr_template_no_active_current_final_marker_requirement() -> None:
    text = _read(ROOT / ".github" / "pull_request_template.md")
    assert "Current-final evidence comment identified by marker" not in text


def test_pr_template_no_active_latest_comment_url_requirement() -> None:
    text = _read(ROOT / ".github" / "pull_request_template.md")
    assert "Latest current-final comment URL" not in text


def test_wp_template_final_comment_optional_non_canonical_after_wp91() -> None:
    text = _read(ROOT / "docs" / "work_package_template.md")
    assert "optional and non-canonical" in text and "WP91" in text


def test_wp_template_absence_not_a_merge_blocker_after_wp91() -> None:
    text = _read(ROOT / "docs" / "work_package_template.md")
    assert "not a merge blocker after WP91" in text


def test_wp_template_posted_evidence_sections_labeled_historical() -> None:
    text = _read(ROOT / "docs" / "work_package_template.md")
    assert "Not Active After WP91" in text


def test_wp_template_evidence_architecture_no_transition_only_pointer() -> None:
    text = _read(ROOT / "docs" / "work_package_template.md")
    assert "Final comment is transition-only pointer" not in text


def test_wp_template_final_comment_optional_non_canonical_field() -> None:
    text = _read(ROOT / "docs" / "work_package_template.md")
    assert "optional/non-canonical after WP91" in text


def test_pr_evidence_discipline_purpose_absence_not_a_merge_blocker_after_wp91() -> None:
    text = _read(ROOT / "docs" / "ai" / "codex" / "PR_EVIDENCE_REPORTING_DISCIPLINE.md")
    assert "not a merge blocker after WP91" in text


def test_pr_evidence_discipline_pr_body_is_required_surface() -> None:
    text = _read(ROOT / "docs" / "ai" / "codex" / "PR_EVIDENCE_REPORTING_DISCIPLINE.md")
    assert "PR body is the required surface" in text


def test_pr_evidence_discipline_missing_final_comment_not_active_blocker() -> None:
    text = _read(ROOT / "docs" / "ai" / "codex" / "PR_EVIDENCE_REPORTING_DISCIPLINE.md")
    assert "after WP91, absence is not a merge blocker" in text


def test_pr_evidence_discipline_latest_comment_url_not_required_after_wp91() -> None:
    text = _read(ROOT / "docs" / "ai" / "codex" / "PR_EVIDENCE_REPORTING_DISCIPLINE.md")
    assert "Latest current-final comment URL" in text
    assert "not required after WP91" in text


def test_pr_evidence_discipline_status_fragment_consistent_with_pr_body() -> None:
    text = _read(ROOT / "docs" / "ai" / "codex" / "PR_EVIDENCE_REPORTING_DISCIPLINE.md")
    assert "consistent with the PR body on all key fields" in text


# ── WP91 follow-up 5: Top-level rulebook and execution-report alignment ────────


def test_agents_md_final_comment_optional_non_canonical_after_wp91() -> None:
    text = _read(ROOT / "AGENTS.md")
    assert "optional and non-canonical" in text
    assert "WP91" in text


def test_agents_md_no_active_mandatory_final_comment_requirement() -> None:
    text = _read(ROOT / "AGENTS.md")
    assert "full final report PR comment is mandatory" not in text
    assert "PR body does not replace this final report comment" not in text


def test_agents_md_pr_body_and_status_fragment_evidence_discipline() -> None:
    text = _read(ROOT / "AGENTS.md")
    assert "PR body and stable status-fragment evidence discipline" in text


def test_wp_execution_report_final_comment_optional_after_wp91() -> None:
    text = _read(ROOT / "docs" / "ai" / "codex" / "WP_EXECUTION_REPORT.md")
    assert "optional and non-canonical" in text
    assert "WP91" in text


def test_wp_execution_report_no_active_mandatory_final_comment() -> None:
    text = _read(ROOT / "docs" / "ai" / "codex" / "WP_EXECUTION_REPORT.md")
    assert "PR body alone is not sufficient" not in text
    assert "Codex must post a full final report as a top-level PR comment" not in text


def test_wp_execution_report_current_final_marker_not_active_requirement() -> None:
    text = _read(ROOT / "docs" / "ai" / "codex" / "WP_EXECUTION_REPORT.md")
    assert "Historical WP86" in text or "not active after WP91" in text.lower()


def test_wp_execution_report_missing_final_comment_not_active_blocker() -> None:
    text = _read(ROOT / "docs" / "ai" / "codex" / "WP_EXECUTION_REPORT.md")
    assert "WP86–WP90 only; absence is not a merge blocker after WP91" in text


def test_wp_execution_report_latest_comment_url_not_required_after_wp91() -> None:
    text = _read(ROOT / "docs" / "ai" / "codex" / "WP_EXECUTION_REPORT.md")
    assert "Verified latest current-final comment URL" in text
    assert "not required after WP91" in text


# ── WP91 follow-up 6: Repo-wide sweep — all active old-policy hits resolved ───


def test_concise_reporting_rules_mandatory_header_retired() -> None:
    text = _read(ROOT / "docs" / "ai" / "codex" / "CONCISE_REPORTING_RULES.md")
    assert "## Mandatory Final PR Comment" not in text


def test_concise_reporting_rules_final_comment_optional_after_wp91() -> None:
    text = _read(ROOT / "docs" / "ai" / "codex" / "CONCISE_REPORTING_RULES.md")
    assert "optional" in text.lower()
    assert "WP91" in text


def test_concise_reporting_rules_pr_body_not_replacement_retired() -> None:
    text = _read(ROOT / "docs" / "ai" / "codex" / "CONCISE_REPORTING_RULES.md")
    assert "The PR body does not replace this final report comment" not in text


def test_posted_pr_evidence_review_hardening_wp91_note() -> None:
    text = _read(ROOT / "docs" / "ai" / "codex" / "POSTED_PR_EVIDENCE_REVIEW_HARDENING.md")
    assert "WP91" in text
    assert "optional" in text.lower()


def test_posted_pr_evidence_review_hardening_workflows_labeled_historical() -> None:
    text = _read(ROOT / "docs" / "ai" / "codex" / "POSTED_PR_EVIDENCE_REVIEW_HARDENING.md")
    assert "Historical WP47" in text


def test_wp_execution_state_machine_phase6_final_comment_optional() -> None:
    text = _read(ROOT / "docs" / "ai" / "codex" / "WP_EXECUTION_STATE_MACHINE.md")
    assert "optional after WP91" in text


def test_wp_execution_state_machine_phase8_final_comment_not_required() -> None:
    text = _read(ROOT / "docs" / "ai" / "codex" / "WP_EXECUTION_STATE_MACHINE.md")
    assert "not required after WP91" in text


def test_pr_review_checklist_wp47_checks_labeled_post_wp91() -> None:
    text = _read(ROOT / "docs" / "ai" / "codex" / "PR_REVIEW_CHECKLIST.md")
    assert "After WP91" in text or "after WP91" in text


def test_pr_review_checklist_status_fragment_not_final_comment_consistency() -> None:
    text = _read(ROOT / "docs" / "ai" / "codex" / "PR_REVIEW_CHECKLIST.md")
    assert "Status fragment validation summary is consistent with the PR body" in text


def test_wp_bundling_policy_posted_evidence_rule_wp91() -> None:
    text = _read(ROOT / "docs" / "ai" / "codex" / "WP_BUNDLING_POLICY.md")
    assert "WP91" in text or "optional after WP91" in text


def test_validation_matrix_guard_example_no_final_comment_required() -> None:
    text = _read(ROOT / "docs" / "ai" / "codex" / "VALIDATION_MATRIX.md")
    assert "optional" in text.lower() or "WP91" in text


def test_token_efficiency_operating_model_final_comment_optional() -> None:
    text = _read(ROOT / "docs" / "ai" / "codex" / "TOKEN_EFFICIENCY_OPERATING_MODEL.md")
    assert "optional" in text.lower() and "WP91" in text


def test_token_efficiency_operating_model_no_mandatory_final_comment() -> None:
    text = _read(ROOT / "docs" / "ai" / "codex" / "TOKEN_EFFICIENCY_OPERATING_MODEL.md")
    assert "skipping any required preflight, validation, security check, final PR comment" not in text


def test_token_efficiency_sequence_closeout_final_comment_optional() -> None:
    text = _read(ROOT / "docs" / "ai" / "codex" / "TOKEN_EFFICIENCY_SEQUENCE_CLOSEOUT.md")
    assert "optional" in text.lower() and "WP91" in text


def test_diff_scope_summary_helper_no_mandatory_final_comment() -> None:
    text = _read(ROOT / "docs" / "ai" / "codex" / "DIFF_SCOPE_SUMMARY_HELPER.md")
    assert "mandatory final PR comment" not in text


def test_diff_scope_summary_helper_design_no_mandatory_final_comment() -> None:
    text = _read(ROOT / "docs" / "ai" / "codex" / "DIFF_SCOPE_SUMMARY_HELPER_DESIGN.md")
    assert "mandatory final PR comment" not in text


def test_validation_output_summary_helper_design_final_comment_optional() -> None:
    text = _read(ROOT / "docs" / "ai" / "codex" / "VALIDATION_OUTPUT_SUMMARY_HELPER_DESIGN.md")
    assert "optional after WP91" in text or "WP91" in text


def test_validation_output_summary_helper_design_no_mandatory_final_comment() -> None:
    text = _read(ROOT / "docs" / "ai" / "codex" / "VALIDATION_OUTPUT_SUMMARY_HELPER_DESIGN.md")
    assert "mandatory final PR comment" not in text or "Historical" in text


def test_code_index_blast_radius_helper_design_no_mandatory_final_comment() -> None:
    text = _read(ROOT / "docs" / "ai" / "codex" / "CODE_INDEX_BLAST_RADIUS_HELPER_DESIGN.md")
    assert "The mandatory final PR comment." not in text


def test_claude_start_here_final_comment_optional_after_wp91() -> None:
    text = _read(ROOT / "CLAUDE_START_HERE.md")
    assert "optional" in text.lower() or "WP91" in text


def test_wp_execution_report_guard_not_both_surfaces() -> None:
    text = _read(ROOT / "docs" / "ai" / "codex" / "WP_EXECUTION_REPORT.md")
    assert "in both the PR body and final comment" not in text


# ── WP92: Repo-Truth Policy Guard And One-Shot Execution Gate ─────────────────

OLD_POLICY_PHRASES = (
    "CURRENT FINAL WP EVIDENCE",
    "--final-comment",
    "require-current-final-marker",
    "final comment required",
    "final evidence comment required",
    "current final evidence comment required",
    "Ready only after final evidence",
    "Ready for review only after final evidence",
    "mark Ready for review only after final evidence passes",
    "final comment will be posted after merge",
    "PR body and final comment drafts",
    "latest final comment must exist",
    "final comment starts with CURRENT FINAL WP EVIDENCE",
    "final evidence comment is mandatory",
)

ALLOWED_CLASSIFIERS = (
    "historical wp",
    "wp86-wp90 only",
    "wp86–wp90 only",
    "after wp91",
    "not required",
    "optional",
    "omit",
    "if no final comment",
    "if skipping",
    "historical_wp86_wp90_only",
    "rewritten_to_post_wp91_policy",
    "removed",
    "optional_non_canonical_comment",
    "not posted",
    "not mandatory",
    "is not required",
    "non-canonical",
    "not a merge blocker",
)


def _phrase_hit_is_classified(lines: list, hit_lineno: int) -> bool:
    """Return True if phrase hit at hit_lineno is in a historical/optional context.

    Checks three scopes: ±5-line local context, nearest section header (## heading
    above the hit), and the document-level preamble (first 25 lines).
    """
    context_start = max(0, hit_lineno - 5)
    context_end = min(len(lines), hit_lineno + 6)
    local_context = "\n".join(lines[context_start:context_end]).lower()

    section_header = ""
    for i in range(hit_lineno - 1, -1, -1):
        if lines[i].startswith("#"):
            section_header = lines[i].lower()
            break

    doc_preamble = "\n".join(lines[:25]).lower()

    return any(
        m in local_context or m in section_header or m in doc_preamble
        for m in ALLOWED_CLASSIFIERS
    )


ACTIVE_CANONICAL_POLICY_DOCS = (
    # Core codex docs (original WP92 set)
    ROOT / "docs" / "ai" / "codex" / "EVIDENCE_ARCHITECTURE.md",
    ROOT / "docs" / "ai" / "codex" / "PR_EVIDENCE_REPORTING_DISCIPLINE.md",
    ROOT / "docs" / "ai" / "codex" / "PR_EVIDENCE_CONSISTENCY_GUARD.md",
    ROOT / "docs" / "ai" / "codex" / "PR_REVIEW_CHECKLIST.md",
    ROOT / "docs" / "ai" / "codex" / "VALIDATION_MATRIX.md",
    ROOT / "docs" / "ai" / "codex" / "WP_DRAFTING_STANDARD.md",
    ROOT / "docs" / "ai" / "codex" / "FOLLOWUP_PROMPT_STANDARD.md",
    ROOT / "docs" / "ai" / "codex" / "RESULT_OUTPUT_INVARIANT_STANDARD.md",
    ROOT / "docs" / "work_package_template.md",
    ROOT / "docs" / "status_entries" / "README.md",
    ROOT / ".github" / "pull_request_template.md",
    # Top-level agent startup/rulebook docs (added WP92 follow-up)
    ROOT / "AGENTS.md",
    ROOT / "CLAUDE_START_HERE.md",
    ROOT / "CODEX_START_HERE.md",
    ROOT / "AI_CODING_AGENT_START_HERE.md",
    # Execution and evidence helper/design docs (added WP92 follow-up)
    ROOT / "docs" / "ai" / "codex" / "WP_EXECUTION_REPORT.md",
    ROOT / "docs" / "ai" / "codex" / "CONCISE_REPORTING_RULES.md",
    ROOT / "docs" / "ai" / "codex" / "POSTED_PR_EVIDENCE_REVIEW_HARDENING.md",
    ROOT / "docs" / "ai" / "codex" / "WP_EXECUTION_STATE_MACHINE.md",
    ROOT / "docs" / "ai" / "codex" / "WP_BUNDLING_POLICY.md",
    ROOT / "docs" / "ai" / "codex" / "TOKEN_EFFICIENCY_OPERATING_MODEL.md",
    ROOT / "docs" / "ai" / "codex" / "TOKEN_EFFICIENCY_SEQUENCE_CLOSEOUT.md",
    ROOT / "docs" / "ai" / "codex" / "DIFF_SCOPE_SUMMARY_HELPER.md",
    ROOT / "docs" / "ai" / "codex" / "DIFF_SCOPE_SUMMARY_HELPER_DESIGN.md",
    ROOT / "docs" / "ai" / "codex" / "VALIDATION_OUTPUT_SUMMARY_HELPER_DESIGN.md",
    ROOT / "docs" / "ai" / "codex" / "CODE_INDEX_BLAST_RADIUS_HELPER_DESIGN.md",
)


def test_repo_truth_policy_guard_doc_exists() -> None:
    assert (ROOT / "docs" / "ai" / "codex" / "REPO_TRUTH_POLICY_GUARD.md").is_file()


def test_repo_truth_policy_guard_defines_canonical_policy_doc_set() -> None:
    text = _read(ROOT / "docs" / "ai" / "codex" / "REPO_TRUTH_POLICY_GUARD.md")
    # Original core codex docs
    assert "EVIDENCE_ARCHITECTURE.md" in text
    assert "PR_EVIDENCE_REPORTING_DISCIPLINE.md" in text
    assert "PR_REVIEW_CHECKLIST.md" in text
    assert "work_package_template.md" in text
    assert "status_entries/README.md" in text
    assert "pull_request_template.md" in text
    # Top-level agent startup/rulebook docs (WP92 follow-up expansion)
    assert "AGENTS.md" in text
    assert "CLAUDE_START_HERE.md" in text
    assert "CODEX_START_HERE.md" in text
    assert "AI_CODING_AGENT_START_HERE.md" in text
    # Execution and evidence helper docs (WP92 follow-up expansion)
    assert "WP_EXECUTION_REPORT.md" in text
    assert "POSTED_PR_EVIDENCE_REVIEW_HARDENING.md" in text
    assert "WP_EXECUTION_STATE_MACHINE.md" in text
    assert "WP_BUNDLING_POLICY.md" in text


def test_repo_truth_policy_guard_defines_old_policy_phrase_sweep() -> None:
    text = _read(ROOT / "docs" / "ai" / "codex" / "REPO_TRUTH_POLICY_GUARD.md")
    assert "CURRENT FINAL WP EVIDENCE" in text
    assert "--final-comment" in text
    assert "require-current-final-marker" in text
    assert "final evidence comment is mandatory" in text


def test_repo_truth_policy_guard_defines_phrase_hit_classifications() -> None:
    text = _read(ROOT / "docs" / "ai" / "codex" / "REPO_TRUTH_POLICY_GUARD.md")
    assert "ACTIVE_POST_WP91_POLICY" in text
    assert "HISTORICAL_WP86_WP90_ONLY" in text
    assert "REMOVED" in text
    assert "REWRITTEN_TO_POST_WP91_POLICY" in text
    assert "OPTIONAL_NON_CANONICAL_COMMENT" in text


def test_repo_truth_policy_guard_defines_product_wp_gate() -> None:
    text = _read(ROOT / "docs" / "ai" / "codex" / "REPO_TRUTH_POLICY_GUARD.md").lower()
    assert "product wp" in text or "product work package" in text
    assert "repo-truth phrase sweep" in text


def test_repo_truth_policy_guard_defines_policy_wp_gate() -> None:
    text = _read(ROOT / "docs" / "ai" / "codex" / "REPO_TRUTH_POLICY_GUARD.md").lower()
    assert "policy wp" in text or "policy work package" in text
    assert "canonical-doc set" in text or "canonical doc set" in text


def test_active_policy_docs_do_not_contain_mandatory_final_comment_phrase() -> None:
    forbidden = "final evidence comment is mandatory"
    for path in ACTIVE_CANONICAL_POLICY_DOCS:
        if path.is_file():
            text = _read(path).lower()
            assert forbidden not in text, (
                f"{path.name} contains forbidden phrase: {forbidden!r}"
            )


def test_active_policy_docs_full_phrase_sweep() -> None:
    """All 14 old-policy phrases must be absent or classified in every active canonical policy doc.

    A phrase hit is allowed only when a classification label appears in one of three context
    scopes: ±5 local lines, nearest ## section header above the hit, or document preamble
    (first 25 lines). Unclassified hits in active instruction context fail.
    """
    failures = []
    for path in ACTIVE_CANONICAL_POLICY_DOCS:
        if not path.is_file():
            continue
        lines = path.read_text(encoding="utf-8").splitlines()
        for phrase in OLD_POLICY_PHRASES:
            for i, line in enumerate(lines):
                if phrase.lower() in line.lower():
                    if not _phrase_hit_is_classified(lines, i):
                        failures.append(
                            f"{path.name}:L{i + 1} — unclassified hit for {phrase!r}: "
                            f"{line.strip()[:80]}"
                        )
    assert not failures, (
        "Unclassified old-policy phrase hits in active canonical policy docs "
        "(must add HISTORICAL_WP86_WP90_ONLY / REWRITTEN / OPTIONAL_NON_CANONICAL_COMMENT "
        "classifier in nearby context):\n" + "\n".join(failures)
    )


def test_active_canonical_policy_docs_all_exist() -> None:
    """Every path in ACTIVE_CANONICAL_POLICY_DOCS must exist on disk."""
    missing = [str(p) for p in ACTIVE_CANONICAL_POLICY_DOCS if not p.is_file()]
    assert not missing, f"Active canonical policy docs missing from repo: {missing}"


def test_pr_template_contains_one_shot_readiness_gate() -> None:
    text = _read(ROOT / ".github" / "pull_request_template.md")
    assert "One-Shot Readiness Gate" in text


def test_wp_template_contains_one_shot_readiness_gate() -> None:
    text = _read(ROOT / "docs" / "work_package_template.md")
    assert "One-Shot Readiness Gate" in text


def test_pr_review_checklist_requires_repo_truth_phrase_sweep() -> None:
    text = _read(ROOT / "docs" / "ai" / "codex" / "PR_REVIEW_CHECKLIST.md").lower()
    assert "phrase sweep" in text or "repo-truth phrase sweep" in text


def test_validation_matrix_references_repo_truth_phrase_sweep() -> None:
    text = _read(ROOT / "docs" / "ai" / "codex" / "VALIDATION_MATRIX.md").lower()
    assert "phrase sweep" in text or "repo-truth phrase sweep" in text


def test_status_entries_readme_forbids_pending_guard_with_ready_yes() -> None:
    text = _read(ROOT / "docs" / "status_entries" / "README.md")
    assert "NOT_VERIFIED" in text
    lower = text.lower()
    assert "ready for review" in lower or "ready for review: yes" in lower
    assert "block merge" in lower or "invalid" in lower


def test_status_entries_readme_defines_stable_only_pr_identity_policy() -> None:
    text = _read(ROOT / "docs" / "status_entries" / "README.md")
    assert "Status fragments are stable committed repo records" in text
    assert "PR: see GitHub PR metadata and PR body." in text
    assert "PR: TBD" in text
    assert "LOCAL_DRAFT_VERIFIED" in text
    assert "Current live PR head: <40-character SHA>" in text
    assert "dynamic PR metadata" in text


def test_templates_reference_stable_status_fragment_pr_field() -> None:
    pr_template = _read(ROOT / ".github" / "pull_request_template.md")
    wp_template = _read(ROOT / "docs" / "work_package_template.md")
    assert "not \"PR: TBD\" with Ready YES" in pr_template
    assert "PR: see GitHub PR metadata and PR body." in wp_template
    assert "no `PR: TBD` with Ready YES" in wp_template


def test_repo_truth_index_references_repo_truth_policy_guard() -> None:
    text = _read(ROOT / "docs" / "repo_truth_index.md")
    assert "REPO_TRUTH_POLICY_GUARD.md" in text


def test_project_status_reflects_wp91_merged() -> None:
    text = _read(ROOT / "docs" / "project_status.md")
    merged_line = next(
        line for line in text.splitlines() if line.startswith("- Merged WPs:")
    )
    assert "WP91" in merged_line


def test_project_status_reflects_wp92_branch() -> None:
    text = _read(ROOT / "docs" / "project_status.md")
    branch_line = next(
        line for line in text.splitlines() if line.startswith("- Current branch:")
    )
    assert "see GitHub PR metadata and PR body" in branch_line or any(
        wp in branch_line for wp in ("wp92", "wp93", "wp94", "recursing-bell")
    )


def test_repo_truth_index_references_wp93_runbook() -> None:
    text = _read(ROOT / "docs" / "repo_truth_index.md")
    assert "candidate_review_report_operator_runbook.md" in text
    assert "docs/status_entries/WP93.md" in text


def test_repo_truth_index_references_wp94_smoke_receipt() -> None:
    text = _read(ROOT / "docs" / "repo_truth_index.md")
    assert "candidate_review_workflow_local_smoke_receipt.md" in text
    assert "docs/status_entries/WP94.md" in text


# ── WP168G: pre-implementation readiness gate and PR-body-canonical policy ────


def test_wp_execution_state_machine_requires_readiness_gate_without_new_authority_state() -> None:
    text = _read(ROOT / "docs" / "ai" / "codex" / "WP_EXECUTION_STATE_MACHINE.md")
    # Canonical authorization chain is preserved exactly (no new authority state).
    assert "LOCAL_DRAFT -> DRAFTABILITY_PASS -> AUTHORIZED -> IMPLEMENTED_LOCAL" in text
    lower = text.lower()
    assert "wp_readiness_gate" in lower
    assert "readiness is not authorization" in lower
    assert "non-authority" in lower
    # WP168G bootstrap is explicitly documented.
    assert "wp168g bootstrap" in lower
    # Later applicable WPs require readiness before the human AUTHORIZED transition.
    assert "before the user grants `authorized`" in lower or "before the human `authorized`" in lower


def test_pr_template_makes_final_comment_optional_after_wp91() -> None:
    text = _read(ROOT / ".github" / "pull_request_template.md")
    lower = text.lower()
    assert "wp91" in lower
    assert "optional" in lower
    assert "canonical current-review evidence surface" in lower
    assert "non-canonical" in lower


def test_validation_matrix_requires_wp_readiness_gate_for_implementation_packages() -> None:
    text = _read(ROOT / "docs" / "ai" / "codex" / "VALIDATION_MATRIX.md")
    lower = text.lower()
    assert "wp_readiness_gate" in lower
    assert "implementation_ready" in lower
    assert "not authorization" in lower
    assert "before" in lower and "authorized" in lower


def test_validation_matrix_requires_full_changed_set_guard_discovery_before_scope_freeze() -> None:
    text = _read(ROOT / "docs" / "ai" / "codex" / "VALIDATION_MATRIX.md")
    # Normalize whitespace so line wrapping in the doc does not break phrase matching.
    lower = " ".join(text.lower().split())
    # Bounded pre-freeze discovery of complete-changed-set guards is required...
    assert "complete changed-file set" in lower
    assert "before scope freeze" in lower
    assert "governed scope contains every required compatibility edit" in lower
    # ...but the claim is bounded and does not overclaim proof of all future dependencies.
    assert "does not claim to mathematically prove every possible future test dependency" in lower
    assert "full repository suite at the exact final head remains the backstop" in lower


# ── WP171G: lean FAST / RUNTIME / PROTECTED governance ───────────────────────


def test_wp171g_governance_docs_define_tracks_and_validation() -> None:
    paths = [
        ROOT / "docs" / "ai" / "codex" / "WP_DRAFTING_STANDARD.md",
        ROOT / "docs" / "ai" / "codex" / "WP_EXECUTION_STATE_MACHINE.md",
        ROOT / "docs" / "ai" / "codex" / "WP_SPEC_STANDARD.md",
        ROOT / "docs" / "ai" / "codex" / "VALIDATION_MATRIX.md",
        ROOT / "docs" / "ai" / "codex" / "TOKEN_EFFICIENCY_OPERATING_MODEL.md",
        ROOT / "docs" / "ai" / "codex" / "REUSABLE_WP_PROMPT_BLOCKS.md",
    ]
    combined = "\n".join(_read(path) for path in paths)
    lower = combined.lower()
    for track in ("FAST", "RUNTIME", "PROTECTED"):
        assert track in combined
    assert "Governance track expected" in combined
    assert "BEGIN_GOVERNANCE_AUTHORITY_V1" in combined
    assert "END_GOVERNANCE_AUTHORITY_V1" in combined
    normalized = " ".join(lower.split())
    assert "normative machine-readable authority declaration" in normalized
    assert "prose cannot broaden" in lower or "prose may not broaden" in lower
    for field in (
        "risk_level", "workflow_governance", "local_offline_tooling",
        "canonical_evidence_policy", "docs", "tests", "source_runtime",
        "workflow_files", "dependencies", "network", "credentials",
        "scheduler", "hermes_runtime", "strategy", "paper", "execution", "live",
    ):
        assert field in combined
    assert "package_guard_passed: null" in combined
    assert "risk 4" in lower
    assert "credential" in lower and "execution" in lower and "live" in lower
    assert "risk 3" in lower
    assert "network" in lower and "scheduler" in lower and "paper" in lower
    assert "no independent pre-implementation" in lower
    assert "historical valid certified" in lower
    assert "same-capability" in lower and "deterministic" in lower
    assert "one authoritative" in lower and "stable candidate" in lower
    assert "side pr review" in lower
    assert "failed required" in lower or "failed-check" in lower
    assert "contract compilation" in lower
    assert "smoke-test" in lower
    assert "3–6 kb" in lower and "5–10 kb" in lower



# --- S10-CI-OPT-01 local-first CI cost optimization (text-based, no YAML dependency) ---

CI_WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"
CI_TOP_LEVEL_JOBS = (
    "classify",
    "compatibility",
    "dependency-audit",
    "ndfd-grib-compat",
    "ndfd-grib-dependency-audit",
    "cockpit-frontend",
    "ci-final-gate",
)
CI_DRAFT_CONDITION = "if: github.event.pull_request.draft == false"
CI_EVENT_TYPES_LINE = "    types: [opened, synchronize, reopened, ready_for_review]\n"
CI_OS_MATRIX = "os: [ubuntu-24.04, windows-2022]"


CI_JOB_CONDITIONS = {job: CI_DRAFT_CONDITION for job in CI_TOP_LEVEL_JOBS}
CI_JOB_CONDITIONS.update({
    "ci-final-gate": "if: always() && github.event.pull_request.draft == false",
    **{job: CI_DRAFT_CONDITION + " && needs.classify.outputs." + flag + " == 'true'"
       for job, flag in (("dependency-audit", "run_dependency_audit"),
                         ("ndfd-grib-compat", "run_ndfd"),
                         ("ndfd-grib-dependency-audit", "run_ndfd"),
                         ("cockpit-frontend", "run_frontend"))},
})


def _ci_trigger_block(text: str) -> str:
    lines = text.splitlines()
    start = lines.index("on:")
    block = []
    for line in lines[start + 1:]:
        if line and not line.startswith((" ", "#")):
            break
        block.append(line)
    return "\n".join(block)


def _ci_jobs(text: str) -> dict[str, str]:
    lines = text.splitlines()
    start = lines.index("jobs:")
    jobs: dict[str, list[str]] = {}
    current: str | None = None
    for line in lines[start + 1:]:
        match = re.match(r"^  ([A-Za-z0-9_-]+):\s*$", line)
        if match:
            current = match.group(1)
            jobs[current] = []
        elif line and not line.startswith((" ", "#")):
            break
        elif current is not None:
            jobs[current].append(line)
    return {name: "\n".join(body) for name, body in jobs.items()}


def _ci_policy_violations(text: str) -> list[str]:
    violations: list[str] = []
    trigger = _ci_trigger_block(text)
    if re.search(r"(?m)^\s*push\s*:", trigger):
        violations.append("T01 push trigger present")
    types_match = re.search(r"(?m)^\s*types:\s*\[([^\]]*)\]", trigger)
    types = {item.strip() for item in types_match.group(1).split(",")} if types_match else set()
    required_types = {"opened", "synchronize", "reopened", "ready_for_review"}
    if not re.search(r"(?m)^  pull_request:\s*$", trigger) or not required_types <= types:
        violations.append("T02 pull_request event types incomplete")
    if "pull_request_target" in text:
        violations.append("T11 pull_request_target present")
    if re.search(r"(?m)^\s*(paths|paths-ignore|branches|branches-ignore)\s*:", trigger):
        violations.append("T12 trigger filter present")
    if not re.search(
        r"(?m)^concurrency:\n  group: ci-pr-\$\{\{ github\.event\.pull_request\.number \}\}\n"
        r"  cancel-in-progress: true$",
        text,
    ):
        violations.append("T04 same-PR concurrency missing")
    jobs = _ci_jobs(text)
    for job in CI_TOP_LEVEL_JOBS:
        if job not in jobs:
            violations.append(f"T05 job missing: {job}")
        elif f"    {CI_JOB_CONDITIONS[job]}" not in jobs[job].splitlines():
            violations.append(f"T03 draft suppression missing: {job}")
    for job, body in jobs.items():
        if job not in CI_TOP_LEVEL_JOBS:
            violations.append(f"T05 unexpected job: {job}")
        job_conditions = [line for line in body.splitlines() if line.startswith("    if:")]
        if job_conditions and job_conditions != [f"    {CI_JOB_CONDITIONS.get(job)}"]:
            violations.append(f"T03 non-equivalent job condition: {job}")
    compat = jobs.get("compatibility", "")
    if text.count('for o in ["ubuntu-24.04", "windows-2022"] for p in ["3.12", "3.14"]') != 2:
        violations.append("T06 compatibility OS matrix changed")
    if 'include: ${{ fromJSON(needs.classify.outputs.matrix).include }}' not in compat:
        violations.append("T07 compatibility Python matrix changed")
    if CI_OS_MATRIX not in jobs.get("ndfd-grib-compat", ""):
        violations.append("T08 NDFD OS matrix changed")
    if not re.search(r"(?m)^      - name: Full test suite\n        if: matrix.smoke == false\n        run: python -m pytest -q$", compat):
        violations.append("T09 full-suite step missing")
    if 'WP167_STRICT_DUCKDB: "1"' not in text or "Focused WP167 tests (DuckDB strict, no skips permitted)" not in compat:
        violations.append("T10 strict DuckDB missing")
    for audit_job in ("dependency-audit", "ndfd-grib-dependency-audit"):
        if "run: python -m pip_audit" not in jobs.get(audit_job, ""):
            violations.append(f"audit step missing: {audit_job}")
    frontend = jobs.get("cockpit-frontend", "")
    for step in ("npm ci", "npm run typecheck", "npm run build", "npm audit --audit-level=high",
                 'node-version: "24.18.0"'):
        if step not in frontend:
            violations.append(f"cockpit-frontend step missing: {step}")
    if 'NDFD_GRIB_STRICT: "1"' not in jobs.get("ndfd-grib-compat", ""):
        violations.append("NDFD strict missing")
    return violations


def test_ci_workflow_final_head_trigger_policy() -> None:
    """R001 / T01-T04, T11: final-head pull_request events, draft suppression, same-PR concurrency."""
    text = _read(CI_WORKFLOW)
    violations = _ci_policy_violations(text)
    assert not violations, violations
    trigger = _ci_trigger_block(text)
    assert "push:" not in trigger and "main" not in trigger
    assert CI_EVENT_TYPES_LINE.strip() in trigger
    assert "pull_request_target" not in text
    jobs = _ci_jobs(text)
    for job in CI_TOP_LEVEL_JOBS:
        assert [line.strip() for line in jobs[job].splitlines() if line.startswith("    if:")] == [CI_JOB_CONDITIONS[job]], job
    assert "permissions:\n  contents: read\n" in text
    assert "secrets." not in text


def test_ci_workflow_preserves_full_final_matrix() -> None:
    """R002 / T05-T12: the five jobs and nine expanded hosted jobs keep their coverage."""
    text = _read(CI_WORKFLOW)
    jobs = _ci_jobs(text)
    assert tuple(jobs) == CI_TOP_LEVEL_JOBS
    # Default-off bootstrap has four explicit compat legs plus two NDFD legs,
    # two audits and frontend; classify/final gate are separate control jobs.
    assert text.count('for o in ["ubuntu-24.04", "windows-2022"] for p in ["3.12", "3.14"]') == 2
    assert "include: ${{ fromJSON(needs.classify.outputs.matrix).include }}" in jobs["compatibility"]
    assert CI_OS_MATRIX in jobs["ndfd-grib-compat"]
    assert 4 + 2 + 2 + 1 == 9
    for focused in ("Focused WP168", "Focused WP167", "Focused WP169", "Focused WP170", "Focused WP171",
                    "Generated artifact guard", "pip check",
                    "tests/data_layer/analytical_research/test_dependency_runtime_compatibility.py"):
        assert focused in jobs["compatibility"], focused
    assert "Focused NDFD GRIB dependency tests (strict, no skips permitted)" in jobs["ndfd-grib-compat"]
    assert not _ci_policy_violations(text)


def test_ci_policy_negative_matrix() -> None:
    """N01-N07: mutated workflow text is rejected by the focused governance checker."""
    text = _read(CI_WORKFLOW)
    assert not _ci_policy_violations(text)
    last_os = text.rindex(CI_OS_MATRIX)
    mutations = {
        # N01 / N02: draft suppression removed from a job or replaced by a non-equivalent condition.
        "draft condition removed": text.replace(f"    {CI_DRAFT_CONDITION}\n", "", 1),
        "non-equivalent condition": text.replace(CI_DRAFT_CONDITION, "if: always()", 1),
        # N02 / N03: ready_for_review or synchronize dropped from the event types.
        "ready_for_review dropped": text.replace(CI_EVENT_TYPES_LINE, "    types: [opened, synchronize, reopened]\n"),
        "synchronize dropped": text.replace(CI_EVENT_TYPES_LINE, "    types: [opened, reopened, ready_for_review]\n"),
        # N04: push-to-main reintroduced; pull_request_target or no concurrency cancellation.
        "push to main": text.replace(CI_EVENT_TYPES_LINE, CI_EVENT_TYPES_LINE + "  push:\n    branches:\n      - main\n"),
        "pull_request_target": text.replace("  pull_request:\n", "  pull_request_target:\n", 1),
        "concurrency not cancelling": text.replace("  cancel-in-progress: true\n", "  cancel-in-progress: false\n"),
        # N05: a current job deleted or renamed.
        "job renamed": text.replace("\n  dependency-audit:\n", "\n  dep-audit:\n"),
        "job deleted": text[: text.index("\n  cockpit-frontend:\n") + 1],
        # N06: OS / Python / suite / strict / audit coverage dropped.
        "compat windows dropped": text.replace('for o in ["ubuntu-24.04", "windows-2022"]', 'for o in ["ubuntu-24.04"]', 1),
        "compat ubuntu dropped": text.replace('for o in ["ubuntu-24.04", "windows-2022"]', 'for o in ["windows-2022"]', 1),
        "ndfd windows dropped": text[:last_os] + "os: [ubuntu-24.04]" + text[last_os + len(CI_OS_MATRIX):],
        "py3.14 dropped": text.replace('for p in ["3.12", "3.14"]', 'for p in ["3.12"]'),
        "py3.12 dropped": text.replace('for p in ["3.12", "3.14"]', 'for p in ["3.14"]'),
        "full suite removed": text.replace("      - name: Full test suite\n        if: matrix.smoke == false\n        run: python -m pytest -q\n", ""),
        "strict duckdb removed": text.replace('WP167_STRICT_DUCKDB: "1"', 'WP167_STRICT_DUCKDB: "0"'),
        # S10-CI-SEC-01: the audit step now carries the exact selective CVE-2026-104851 exception.
        "audit removed": text.replace(
            "run: python -m pip_audit --ignore-vuln CVE-2026-104851\n", "run: echo skipped\n", 1),
        "frontend audit removed": text.replace("npm audit --audit-level=high", "true"),
        # N07: path or branch filters that could skip parts of the final matrix.
        "paths filter": text.replace(CI_EVENT_TYPES_LINE, CI_EVENT_TYPES_LINE + "    paths:\n      - 'src/**'\n"),
        "paths-ignore filter": text.replace(CI_EVENT_TYPES_LINE, CI_EVENT_TYPES_LINE + "    paths-ignore:\n      - 'docs/**'\n"),
        "branches filter": text.replace(CI_EVENT_TYPES_LINE, CI_EVENT_TYPES_LINE + "    branches:\n      - main\n"),
    }
    for name, mutated in mutations.items():
        assert mutated != text, name
        assert _ci_policy_violations(mutated), name


def test_ci_governance_docs_require_local_first_final_hosted_once() -> None:
    """R003 / T13-T14, N08-N10: canonical guidance is local-first with one final exact-head hosted run."""
    matrix = " ".join(_read(ROOT / "docs" / "ai" / "codex" / "VALIDATION_MATRIX.md").split())
    for phrase in (
        "## Local-First Validation And Final Hosted CI (S10-CI-OPT-01)",
        "Hosted GitHub Actions CI is final exact-head verification, not the iterative development test loop.",
        "Do not use hosted CI as the iterative test loop.",
        "one authoritative local broad/full suite",
        "Create or update one DRAFT PR and keep it draft while source is changing.",
        "mark it Ready for review once; that transition launches the one required exact-head hosted plan.",
        "Convert back to draft before iterative repairs where practical",
        "Rerun only the affected cancelled or failed-to-start job where GitHub supports it; "
        "do not rerun already-green jobs.",
        "A cancellation before runner/test execution is infrastructure evidence, not a code PASS or FAIL.",
        "fresh exact-head hosted CI is then mandatory",
        "A hosted PASS on an older head never justifies Ready for review: YES for a changed head.",
        "Tier 3 retains every legacy leg",
    ):
        assert phrase in matrix, phrase
    drafting = " ".join(_read(ROOT / "docs" / "ai" / "codex" / "WP_DRAFTING_STANDARD.md").split())
    for phrase in (
        "### Hosted CI planning (S10-CI-OPT-01)",
        "Every future WP must plan hosted CI as final exact-head verification, not iterative testing.",
        "the PR kept DRAFT while source is changing",
        "one required hosted plan on that exact non-draft head",
        "must not plan hosted CI as its development test loop",
        "any source change after a hosted PASS requires fresh exact-head hosted CI",
        "rerun affected-job-only where supported",
    ):
        assert phrase in drafting, phrase
    for doc in (matrix.lower(), drafting.lower()):
        assert "hosted-only iterative" not in doc
        assert "may use equivalent exact-head hosted ci;" not in doc


def test_ci_optimization_status_and_repo_truth_are_recorded() -> None:
    """R004 / T15: status and repo truth register S10-CI-OPT-01; S10-LIVE-CANARY-01 stays separately gated."""
    status_lines = _read(ROOT / "docs" / "project_status.md").splitlines()
    record = next(line for line in status_lines if line.startswith(
        "# S10-CI-OPT-01 workflow-governance review target: Local-First CI Cost Optimization"))
    for text in (
        "Governance track: FAST", "Risk level: 2", "Exact changed-file scope: 9",
        "Frozen base: 7dc323df2aa5820621cc2e6cf89a1d91827ed122", "PR #219 merged: YES",
        "PR #219 head: 30a5d70aaf385450cd8a9644773e6ecd25a10b9a",
        "first real canary: S10-LIVE-CANARY-01, separately gated live successor (NOT AUTHORIZED)",
        "live: DISABLED", "S10-CI-OPT-01 capital/orders: USD 0 / 0", "Merge authorized: NO",
    ):
        assert text in record, text
    for claim in ("S10-LIVE-CANARY-01: AUTHORIZED", "live: ENABLED", "Merge authorized: YES"):
        assert claim not in record, claim
    index = _read(ROOT / "docs" / "repo_truth_index.md")
    assert "## S10-CI-OPT-01 Local-First CI Cost Optimization (workflow-governance review target)" in index
    section = " ".join(index.split("## S10-CI-OPT-01 ", 1)[1].split("\n## ", 1)[0].split())
    assert "S10-LIVE-CANARY-01 remains the separately gated live successor (NOT AUTHORIZED)" in section
    fragment = _read(ROOT / "docs" / "status_entries" / "S10-CI-OPT-01.md")
    for text in ("Merge authorized: NO", "Exact implementation scope: 9 paths", "Governance track: FAST",
                 "PR and current live head: see GitHub metadata and the PR body",
                 "Next: S10-LIVE-CANARY-01 First Restricted Live Canary Activation, separately gated"):
        assert text in fragment, text
    package = ROOT / "docs" / "wp_specs" / "S10-CI-OPT-01"
    spec = json.loads(_read(package / "wp_spec.json"))
    assert spec["identity"]["required_predecessor"] == {
        "pr_number": 219,
        "head_sha": "30a5d70aaf385450cd8a9644773e6ecd25a10b9a",
        "merge_sha": "7dc323df2aa5820621cc2e6cf89a1d91827ed122",
    }
    assert spec["successor_boundary"]["next_wp"] == "S10-LIVE-CANARY-01"
    assert spec["successor_boundary"]["separately_gated"] is True
    assert len(spec["scope"]["allowed_changed_files"]) == spec["scope"]["max_changed_files"] == 9
    for key in ("source_runtime", "dependencies", "network", "credentials", "execution", "live"):
        assert spec["authority"][key] is False, key
    assert hashlib.sha256((package / "wp_spec.json").read_bytes()).hexdigest() == (
        "bef6863aa291a85538b2d094f879adcfc856cfe847b5813ad3f4a35ed6774090")
    assert hashlib.sha256((package / "wp_prompt.txt").read_bytes()).hexdigest() == (
        "ebd6ab082e3f191cb7ad3226a43e3a8b13cd56532c45eda4824baee2ec0ac4f7")


# ---------------------------------------------------------------------------
# S10-CI-SEC-01 Dependency-Security CI Closure
# ---------------------------------------------------------------------------

CI_SEC_01_EXCEPTION = "run: python -m pip_audit --ignore-vuln CVE-2026-104851"
CI_SEC_01_AUDIT_JOBS = ("dependency-audit", "ndfd-grib-dependency-audit")
CI_SEC_01_FRONTEND = ROOT / "src" / "operator_cockpit_frontend"


def _ci_sec_01_violations(text: str) -> list[str]:
    violations: list[str] = []
    jobs = _ci_jobs(text)
    ignored = re.findall(r"--ignore-vuln[ =](\S+)", text)
    if ignored != ["CVE-2026-104851", "CVE-2026-104851"]:
        violations.append(f"ignored ids not exactly two CVE-2026-104851: {ignored}")
    if text.count(CI_SEC_01_EXCEPTION) != 2:
        violations.append("exact exception command count != 2")
    for job in CI_SEC_01_AUDIT_JOBS:
        body = jobs.get(job, "")
        audit_runs = [line.strip() for line in body.splitlines() if "pip_audit" in line and "run:" in line]
        if audit_runs != [CI_SEC_01_EXCEPTION]:
            violations.append(f"audit step not exact: {job}")
        if "run: python -m pip check" not in body:
            violations.append(f"pip check missing: {job}")
        for mask in ("|| true", "continue-on-error", "--no-deps", "fsspec=="):
            if mask in body:
                violations.append(f"masking or forced install in {job}: {mask}")
    for job, body in jobs.items():
        if job not in CI_SEC_01_AUDIT_JOBS and "--ignore-vuln" in body:
            violations.append(f"exception outside the Python audit jobs: {job}")
    if "continue-on-error" in text:
        violations.append("continue-on-error present")
    return violations


def test_ci_sec_01_python_audit_exception_is_exact() -> None:
    """R003: both Python audit jobs run exactly one selective ignore for CVE-2026-104851."""
    text = _read(CI_WORKFLOW)
    jobs = _ci_jobs(text)
    for job in CI_SEC_01_AUDIT_JOBS:
        assert job in jobs, job
        assert f"        {CI_SEC_01_EXCEPTION}" in jobs[job].splitlines(), job
    assert text.count(CI_SEC_01_EXCEPTION) == 2
    assert re.findall(r"--ignore-vuln[ =](\S+)", text) == ["CVE-2026-104851", "CVE-2026-104851"]
    assert not _ci_sec_01_violations(text), _ci_sec_01_violations(text)
    assert not _ci_policy_violations(text)


def test_ci_sec_01_audit_exception_negative_matrix() -> None:
    """R004 / N01-N06: widened, masked, spread or removed exceptions are rejected."""
    text = _read(CI_WORKFLOW)
    assert not _ci_sec_01_violations(text)
    exception_line = f"        {CI_SEC_01_EXCEPTION}\n"
    mutations = {
        "N01 exception dropped from one job": text.replace(
            exception_line, "        run: python -m pip_audit\n", 1),
        "N02 second ignored id": text.replace(
            exception_line, exception_line.rstrip("\n") + " --ignore-vuln GHSA-0000-0000-0000\n", 1),
        "N02 different ignored id": text.replace("CVE-2026-104851\n", "CVE-2026-999999\n", 1),
        "N03 exception spread to compat": text.replace(
            "        run: python -m pytest -q\n",
            "        run: python -m pytest -q\n      - name: extra\n        run: python -m pip_audit --ignore-vuln CVE-2026-104851\n", 1),
        "N04 or-true masking": text.replace(exception_line, exception_line.rstrip("\n") + " || true\n", 1),
        "N04 continue-on-error": text.replace(
            exception_line, exception_line + "        continue-on-error: true\n", 1),
        "N05 audit step removed": text.replace(exception_line, "        run: echo skipped\n", 1),
        "N06 pip check removed": text.replace("        run: python -m pip check\n", "        run: echo skipped\n", 2),
        "forced fsspec install": text.replace(
            "pytest>=8.0\" pip-audit\n", "pytest>=8.0\" pip-audit fsspec==2026.6.0 --no-deps\n", 1),
    }
    for name, mutated in mutations.items():
        assert mutated != text, name
        assert _ci_sec_01_violations(mutated), name


def test_ci_sec_01_no_python_pin_or_fsspec_change() -> None:
    """R005: the stable Nautilus pin stays and no direct fsspec pin or forced install exists."""
    pyproject = _read(ROOT / "pyproject.toml")
    assert '"nautilus_trader==1.231.0"' in pyproject
    assert "fsspec" not in pyproject.lower()
    workflow = _read(CI_WORKFLOW)
    assert 'WP168_DEP: "nautilus_trader==1.231.0"' in workflow
    assert "fsspec==" not in workflow and "--no-deps" not in workflow
    jobs = _ci_jobs(workflow)
    for job in CI_SEC_01_AUDIT_JOBS:
        assert "      - name: pip check\n        run: python -m pip check" in jobs[job], job


def test_ci_sec_01_frontend_lock_patches_source_map_js_only() -> None:
    """R002 / N08-N09: the lock resolves source-map-js 1.2.2 transitively; package.json is untouched."""
    lock = json.loads(_read(CI_SEC_01_FRONTEND / "package-lock.json"))
    node = lock["packages"]["node_modules/source-map-js"]
    assert node["version"] == "1.2.2"
    assert node["resolved"] == "https://registry.npmjs.org/source-map-js/-/source-map-js-1.2.2.tgz"
    assert node["integrity"] == (
        "sha512-KGj/8Y43x35aZVDtt+J4mK1hoLGHULMYfSkODJNQjNDC3oW1PqPoxMwo0pLUsWM/UEGzON/NxeHywEfNXNP3Vw==")
    assert node["dev"] is True
    assert lock["packages"]["node_modules/postcss"]["dependencies"]["source-map-js"] == "^1.2.2"
    package = json.loads(_read(CI_SEC_01_FRONTEND / "package.json"))
    for section in ("dependencies", "devDependencies", "optionalDependencies", "overrides"):
        assert "source-map-js" not in package.get(section, {}), section
    for name in ("", *lock["packages"]):
        assert "source-map-js" not in lock["packages"].get(name, {}).get("devDependencies", {}), name


def test_ci_sec_01_status_and_repo_truth_record_removal_trigger() -> None:
    """R006 / N10: status, project status and repo truth record the exception reason and removal trigger."""
    fragment = " ".join(_read(ROOT / "docs" / "status_entries" / "S10-CI-SEC-01.md").split())
    for phrase in (
        "Governance track: FAST", "Merge authorized: NO", "PR and current live head: see GitHub metadata and the PR body",
        "`CVE-2026-104851` is ignored only because the repository's current stable production pin "
        "`nautilus_trader==1.231.0` resolves `fsspec==2026.2.0`.",
        "A Nautilus prerelease alone is not a removal path for production.",
        "source-map-js` 1.2.1, GHSA-68fv-2mgg-jv7q",
        "PR #221: untouched",
    ):
        assert phrase in fragment, phrase
    status_lines = _read(ROOT / "docs" / "project_status.md").splitlines()
    record = next(line for line in status_lines if line.startswith(
        "# S10-CI-SEC-01 current bounded security closure (open branch"))
    for text in (
        "Governance track: FAST", "Risk level: 2", "Exact changed-file scope: 8",
        "Frozen base: f9a0bae6a69d008862e6466f1fe532bc9416de5d", "python -m pip_audit --ignore-vuln CVE-2026-104851",
        "exception removal trigger:", "PR #221 / S10-LIVE-CANARY-UA-01: separately paused pending this closure",
        "live: DISABLED", "S10-CI-SEC-01 capital/orders: USD 0 / 0", "Merge authorized: NO",
    ):
        assert text in record, text
    for claim in ("merged: YES at", "live: ENABLED", "Merge authorized: YES"):
        assert claim not in record.split("Immediate predecessor")[0], claim
    index = _read(ROOT / "docs" / "repo_truth_index.md")
    heading = "## S10-CI-SEC-01 Dependency-Security CI Closure (current bounded security closure, open branch)"
    assert index.count(heading) == 1
    section = " ".join(index.split(heading, 1)[1].split("\n## ", 1)[0].split())
    for phrase in (
        "Removal trigger:", "a Nautilus prerelease alone is not a removal path",
        "exactly `dependency-audit` and `ndfd-grib-dependency-audit` run `python -m pip_audit --ignore-vuln CVE-2026-104851`",
        "Successor: PR #221 / S10-LIVE-CANARY-UA-01",
    ):
        assert phrase in section, phrase
    spec = json.loads(_read(ROOT / "docs" / "wp_specs" / "S10-CI-SEC-01" / "wp_spec.json"))
    assert spec["scope"]["required_changed_files"] == spec["scope"]["allowed_changed_files"]
    assert len(spec["scope"]["allowed_changed_files"]) == spec["scope"]["max_changed_files"] == 8
    src_paths = [p for p in spec["scope"]["allowed_changed_files"] if p.startswith("src/")]
    assert src_paths == ["src/operator_cockpit_frontend/package-lock.json"]
    for key in ("network", "credentials", "scheduler", "hermes_runtime", "strategy", "paper", "execution", "live"):
        assert spec["authority"][key] is False, key


def test_ci_opt_02_workflow_policy_and_bootstrap() -> None:
    text = _read(CI_WORKFLOW)
    assert not _ci_policy_violations(text)
    jobs = _ci_jobs(text)
    assert set(jobs) == set(CI_TOP_LEVEL_JOBS)
    assert 'git show "$BASE_SHA:tools/ci/risk_tier.py"' in jobs["classify"]
    assert 'python "$RUNNER_TEMP/base_risk_tier.py"' in jobs["classify"]
    assert "python tools/ci/risk_tier.py" not in text
    assert "CI_RISK_ROUTING_ENABLED" in text
    assert "always()" in jobs["ci-final-gate"]
    assert "all(needs[j][\"result\"] == \"success\" for j in jobs)" in jobs["ci-final-gate"]
    assert "matrix.smoke == true" in jobs["compatibility"]
    assert "tests/tools/wp tests/tools/git" in jobs["compatibility"]
    for key in ("run_dependency_audit", "run_ndfd", "run_frontend"):
        assert key in jobs["classify"] and key in jobs["ci-final-gate"]
    spec_path = ROOT / "docs/wp_specs/S10-CI-OPT-02/wp_spec.json"
    spec = json.loads(_read(spec_path))
    assert spec["scope"]["required_changed_files"] == spec["scope"]["allowed_changed_files"]
    assert len(spec["scope"]["required_changed_files"]) == 13
    assert hashlib.sha256(spec_path.read_bytes()).hexdigest() == "6842c4673c3c47a7d6618210f2ab42cc9340e4b9aad9c8b3e1d98ad7ec824367"
    assert hashlib.sha256((spec_path.parent / "wp_prompt.txt").read_bytes()).hexdigest() == "1263a6471d5ab1e8c16366452a925dfd5d479c7e87f699e56dda9a955dce5f69"


# --- S10-CI-SEC-04: mandatory hosted gitleaks enforcement inside ci-final-gate ---

CI_SEC_04_FINAL_STEP = "      - name: Verify exact plan and required job results"
CI_SEC_04_STEPS = (
    "      - name: Verify exact PR head and full history for the secret scan",
    "      - name: Install pinned gitleaks 8.27.2 (strict SHA-256 verification)",
    "      - name: Gitleaks full-history scan (redacted, fail-closed)",
    "      - name: Binary-backed gitleaks detection tests (5 required, 0 skipped)",
)
CI_SEC_04_ARCHIVE_SHA256 = "141c3b2dede46d8b3a53b47116da756bd223decc0374797559a6b50ecba5590c"
CI_SEC_04_CHECKSUMS_SHA256 = "37c3277907a277499370e980d13d8497215d49c69809668dc8841dbabd574dc0"
CI_SEC_04_DETECTION_NODES = (
    "test_gitleaks_detects_synthetic_secret_and_accepts_clean_input",
    "test_gitleaks_git_mode_detects_secret_added_to_classified_wp14_row",
    "test_gitleaks_repo_config_autoloads_and_detects",
    "test_defective_wp15_config_shape_detects_nothing",
)
CI_SEC_04_JUNIT_CHECKS = ('tests="5"', 'skipped="0"', 'failures="0"', 'errors="0"')


def _ci_sec_04_gate_steps(gate: str) -> dict[str, str]:
    """Split the ci-final-gate body into its named steps (text between step headers)."""
    lines = gate.splitlines()
    starts = [i for i, line in enumerate(lines) if line.startswith("      - ")]
    steps: dict[str, str] = {}
    for index, start in enumerate(starts):
        end = starts[index + 1] if index + 1 < len(starts) else len(lines)
        steps[lines[start]] = "\n".join(lines[start:end])
    return steps


def _ci_sec_04_violations(text: str) -> list[str]:
    gate = _ci_jobs(text).get("ci-final-gate", "")
    violations: list[str] = []
    steps = _ci_sec_04_gate_steps(gate)
    headers = list(steps)
    for header in CI_SEC_04_STEPS:
        if header not in steps:
            violations.append(f"G01 gate step missing: {header.strip()}")
    if not headers or headers[-1] != CI_SEC_04_FINAL_STEP:
        violations.append("G02 final verification is not the last step")
    elif all(h in headers for h in CI_SEC_04_STEPS):
        positions = [headers.index(h) for h in CI_SEC_04_STEPS]
        if positions != sorted(positions) or positions[-1] >= headers.index(CI_SEC_04_FINAL_STEP):
            violations.append("G02 gate steps not ordered before the final verification")
    new_steps = "\n".join(steps.get(h, "") for h in CI_SEC_04_STEPS)
    for masked in ("continue-on-error", "|| true", "\n        if:", "latest",
                   "setup_project_gitleaks", "sudo", "/usr/local/bin"):
        if masked in new_steps:
            violations.append(f"G03 masking or unsafe acquisition: {masked.strip()}")
    if re.search(r"\|\s*(sh|bash)\b", new_steps):
        violations.append("G03 masking or unsafe acquisition: pipe to shell")
    head = steps.get(CI_SEC_04_STEPS[0], "")
    for needle in ('test "$(git rev-parse HEAD)" = "$HEAD_SHA"',
                   'test "$(git rev-parse --is-shallow-repository)" = "false"',
                   'git merge-base --is-ancestor "$BASE_SHA" "$HEAD_SHA"'):
        if needle not in head:
            violations.append(f"G04 exact-head/full-history check missing: {needle}")
    if "fetch-depth: 0" not in gate or "persist-credentials: false" not in gate:
        violations.append("G04 full-history checkout changed")
    install = steps.get(CI_SEC_04_STEPS[1], "")
    if 'GITLEAKS_VERSION: "8.27.2"' not in install or "GITLEAKS_ARCHIVE: gitleaks_8.27.2_linux_x64.tar.gz" not in install:
        violations.append("G05 pinned version or asset changed")
    archive_pin = re.search(r"GITLEAKS_ARCHIVE_SHA256: ([0-9a-f]{64})\n", install)
    manifest_pin = re.search(r"GITLEAKS_CHECKSUMS_SHA256: ([0-9a-f]{64})\n", install)
    if not archive_pin or archive_pin.group(1) != CI_SEC_04_ARCHIVE_SHA256:
        violations.append("G06 archive SHA-256 pin missing or changed")
    if not manifest_pin or manifest_pin.group(1) != CI_SEC_04_CHECKSUMS_SHA256:
        violations.append("G06 manifest SHA-256 pin missing or changed")
    archive_check = '"$GITLEAKS_ARCHIVE_SHA256  $dl/$GITLEAKS_ARCHIVE" | sha256sum --check --strict -'
    manifest_check = '"$GITLEAKS_CHECKSUMS_SHA256  $dl/checksums.txt" | sha256sum --check --strict -'
    extract = 'tar -xzf "$dl/$GITLEAKS_ARCHIVE" -C "$bin" gitleaks'
    if archive_check not in install or extract not in install or install.index(archive_check) > install.index(extract):
        violations.append("G07 archive not verified before extraction")
    if manifest_check not in install:
        violations.append("G07 checksum manifest not verified")
    if "grep -c '[^[:space:]]')\" -eq 1" not in install or 'test "$manifest_sha" = "$GITLEAKS_ARCHIVE_SHA256"' not in install:
        violations.append("G08 single manifest entry match missing")
    for needle in ("set -euo pipefail", "curl -fsSL --proto '=https' --tlsv1.2",
                   'test "$("$bin/gitleaks" version)" = "$GITLEAKS_VERSION"', 'echo "$bin" >> "$GITHUB_PATH"',
                   'bin="$RUNNER_TEMP/gitleaks-bin"'):
        if needle not in install:
            violations.append(f"G09 install requirement missing: {needle}")
    scan = steps.get(CI_SEC_04_STEPS[2], "")
    if 'gitleaks git --redact --no-banner --exit-code 1 --log-opts="--all" .' not in scan:
        violations.append("G10 redacted full-history git scan missing")
    if "gitleaks dir" in gate:
        violations.append("G10 working-tree dir scan substitute")
    if "test -f .gitleaks.toml" not in scan or "test -f .gitleaksignore" not in scan:
        violations.append("G10 committed scanner configuration not required")
    detect = steps.get(CI_SEC_04_STEPS[3], "")
    for node in CI_SEC_04_DETECTION_NODES:
        if f"tests/test_gitleaks_secret_scan_gate.py::{node}" not in detect:
            violations.append(f"G11 detection case not selected: {node}")
    for check in CI_SEC_04_JUNIT_CHECKS:
        if f"grep -Eq '<testsuite [^>]*{check}' \"$report\"" not in detect:
            violations.append(f"G12 junit requirement missing: {check}")
    return violations


def test_ci_sec_04_gitleaks_gate_acquisition_is_pinned_and_strict() -> None:
    """R002: pinned 8.27.2 linux x64 asset, both SHA-256 pins, single manifest entry, verify before extract."""
    text = _read(CI_WORKFLOW)
    assert _ci_sec_04_violations(text) == []
    install = _ci_sec_04_gate_steps(_ci_jobs(text)["ci-final-gate"])[CI_SEC_04_STEPS[1]]
    assert install.index("sha256sum --check --strict") < install.index("tar -xzf")
    assert "$RUNNER_TEMP" in install and "GITHUB_PATH" in install


def test_ci_sec_04_gitleaks_gate_scans_full_history() -> None:
    """R003: exact PR head, non-shallow history, redacted git scan with the committed configuration."""
    text = _read(CI_WORKFLOW)
    steps = _ci_sec_04_gate_steps(_ci_jobs(text)["ci-final-gate"])
    assert 'gitleaks git --redact --no-banner --exit-code 1 --log-opts="--all" .' in steps[CI_SEC_04_STEPS[2]]
    assert 'test "$(git rev-parse HEAD)" = "$HEAD_SHA"' in steps[CI_SEC_04_STEPS[0]]
    assert "${{ github.event.pull_request.head.sha }}" in steps[CI_SEC_04_STEPS[0]]


def test_ci_sec_04_gitleaks_gate_requires_five_unskipped_cases() -> None:
    """R004: the four binary-backed functions (five cases) run and the JUnit report must be 5/0/0/0."""
    text = _read(CI_WORKFLOW)
    detect = _ci_sec_04_gate_steps(_ci_jobs(text)["ci-final-gate"])[CI_SEC_04_STEPS[3]]
    assert all(f"::{node}" in detect for node in CI_SEC_04_DETECTION_NODES)
    assert all(check in detect for check in CI_SEC_04_JUNIT_CHECKS)
    gate_tests = _read(ROOT / "tests" / "test_gitleaks_secret_scan_gate.py")
    for node in CI_SEC_04_DETECTION_NODES:
        assert f"def {node}(" in gate_tests, node
    assert '@pytest.mark.parametrize("config_text", [DEFECTIVE_WP15_CONFIG, ROW_BOUND_ALLOWLIST_CONFIG])' in gate_tests


def test_ci_sec_04_gitleaks_gate_negative_matrix() -> None:
    """R005 / N01-N12: weakening, masking, reordering or skipping the gate is rejected."""
    text = _read(CI_WORKFLOW)
    assert _ci_sec_04_violations(text) == [] and not _ci_policy_violations(text)
    gate_start = text.index("  ci-final-gate:")
    install_header = CI_SEC_04_STEPS[1] + "\n"
    scan_block = text[text.index(CI_SEC_04_STEPS[2]):text.index(CI_SEC_04_STEPS[3])]
    archive_check = 'echo "$GITLEAKS_ARCHIVE_SHA256  $dl/$GITLEAKS_ARCHIVE" | sha256sum --check --strict -\n'
    mutations = {
        "N01 install step removed": text.replace(text[text.index(install_header):text.index(CI_SEC_04_STEPS[2])], ""),
        "N02 archive check removed": text.replace("          " + archive_check, ""),
        "N02 archive check after extraction": text.replace("          " + archive_check, "").replace(
            "          test -x \"$bin/gitleaks\"\n", "          " + archive_check + "          test -x \"$bin/gitleaks\"\n"),
        "N03 archive pin missing": text.replace(CI_SEC_04_ARCHIVE_SHA256, "not-a-sha256"),
        "N03 manifest pin short": text.replace(CI_SEC_04_CHECKSUMS_SHA256, CI_SEC_04_CHECKSUMS_SHA256[:40]),
        "N04 wrong version": text.replace('GITLEAKS_VERSION: "8.27.2"', 'GITLEAKS_VERSION: "8.18.0"'),
        "N04 wrong asset": text.replace("GITLEAKS_ARCHIVE: gitleaks_8.27.2_linux_x64.tar.gz", "GITLEAKS_ARCHIVE: gitleaks_8.27.2_darwin_x64.tar.gz"),
        "N05 single-entry check removed": text.replace("grep -c '[^[:space:]]')\" -eq 1", "grep -c '[^[:space:]]')\" -ge 1"),
        "N06 dir replaces git": text.replace('gitleaks git --redact --no-banner', 'gitleaks dir --redact --no-banner'),
        "N07 redact dropped": text.replace("gitleaks git --redact --no-banner", "gitleaks git --no-banner"),
        "N08 detection case dropped": text.replace(
            '            "tests/test_gitleaks_secret_scan_gate.py::test_gitleaks_repo_config_autoloads_and_detects" \\\n', ""),
        "N09 zero-skip check removed": text.replace("          grep -Eq '<testsuite [^>]*skipped=\"0\"' \"$report\"\n", ""),
        "N10 masked scan": text.replace('--log-opts="--all" .\n', '--log-opts="--all" . || true\n'),
        "N10 continue-on-error": text.replace(install_header, install_header + "        continue-on-error: true\n"),
        "N10 step condition": text.replace(install_header, install_header + "        if: always()\n"),
        "N11 scanner after final pass": text.replace(scan_block, "") + scan_block,
        "N12 exact-head check removed": text.replace('          test "$(git rev-parse HEAD)" = "$HEAD_SHA"\n', ""),
        "N12 shallow checkout": text[:gate_start] + text[gate_start:].replace("fetch-depth: 0", "fetch-depth: 1", 1),
        "N12 latest version": text.replace("releases/download/v${GITLEAKS_VERSION}", "releases/latest/download"),
    }
    for label, mutated in mutations.items():
        assert mutated != text, label
        assert _ci_sec_04_violations(mutated), label


def test_ci_sec_04_deferred_status_and_doc_record_hosted_enforcement() -> None:
    """D001 moves to implemented-on-branch only; the gate doc and status entry record limits truthfully."""
    deferred = _read(ROOT / "docs" / "deferred_items_log.md")
    row = next(line for line in deferred.splitlines() if line.startswith("| S10-CI-SEC-02-D001 |"))
    assert "IMPLEMENTED_ON_BRANCH_PENDING_HOSTED_VALIDATION_AND_MERGE" in row and "S10-CI-SEC-04" in row
    for other in ("S10-CI-SEC-02-D002", "S10-CI-SEC-02-D003", "S10-CI-SEC-02-D004"):
        assert any(line.startswith(f"| {other} |") for line in deferred.splitlines()), other
    doc = _read(ROOT / "docs" / "gitleaks_secret_scan_gate.md")
    assert "S10-CI-SEC-04" in doc and CI_SEC_04_ARCHIVE_SHA256 in doc and "ci-final-gate" in doc
    status = _read(ROOT / "docs" / "status_entries" / "S10-CI-SEC-04.md")
    assert "Merge authorized: NO" in status and "live values in the PR body" in status
