from __future__ import annotations

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
        "PR body does not replace",
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
    assert any(wp in branch_line for wp in (
        "workflow/wp86-execution-package-discipline-adoption",
        "wp86",
        "wp87",
        "wp88",
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
