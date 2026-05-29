"""
Tests for WP35 - Memory / Status Snapshot Helper Design.

Verifies:
- Design doc exists and contains all required status, authority, mode,
  CLI, input-source, output, sanitization, staleness, lifecycle, relationship,
  test-plan, and open-question sections.
- Repo-truth index and cross-reference docs are updated.
- No implementation paths exist.
- No forbidden dependencies added.
"""

import os
import re
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
DESIGN_DOC = REPO_ROOT / "docs/ai/codex/MEMORY_STATUS_SNAPSHOT_HELPER_DESIGN.md"
REPO_TRUTH_INDEX = REPO_ROOT / "docs/repo_truth_index.md"
TOKEN_EFFICIENCY_DOC = REPO_ROOT / "docs/ai/codex/TOKEN_EFFICIENCY_OPERATING_MODEL.md"
CODEX_README = REPO_ROOT / "docs/ai/codex/README.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class TestDesignDocExists:
    def test_design_doc_exists(self):
        assert DESIGN_DOC.exists(), f"Design doc missing: {DESIGN_DOC}"

    def test_design_doc_not_empty(self):
        content = _read(DESIGN_DOC)
        assert len(content) > 500, "Design doc appears too short to be complete"


class TestDesignDocStatusFields:
    """Section 1: Status fields."""

    def test_design_only(self):
        assert "DESIGN_ONLY" in _read(DESIGN_DOC)

    def test_not_implemented(self):
        assert "NOT_IMPLEMENTED" in _read(DESIGN_DOC)

    def test_applies_to_claude_code_and_codex(self):
        assert "Claude Code and Codex" in _read(DESIGN_DOC)

    def test_no_runtime_change(self):
        assert "NO_RUNTIME_CHANGE" in _read(DESIGN_DOC)

    def test_no_tool_implementation(self):
        assert "NO_TOOL_IMPLEMENTATION" in _read(DESIGN_DOC)

    def test_no_dependency_change(self):
        assert "NO_DEPENDENCY_CHANGE" in _read(DESIGN_DOC)

    def test_no_network(self):
        assert "NO_NETWORK" in _read(DESIGN_DOC)

    def test_no_validation_weakening(self):
        assert "NO_VALIDATION_WEAKENING" in _read(DESIGN_DOC)

    def test_no_protected_boundary_change(self):
        assert "NO_PROTECTED_BOUNDARY_CHANGE" in _read(DESIGN_DOC)

    def test_advisory_only_not_repo_truth(self):
        assert "ADVISORY_ONLY_NOT_REPO_TRUTH" in _read(DESIGN_DOC)


class TestDesignDocAuthorityModel:
    """Section 4: Authority model."""

    def test_repo_truth_always_wins(self):
        assert "Repo truth always wins" in _read(DESIGN_DOC)

    def test_snapshot_is_advisory(self):
        assert "snapshot is advisory" in _read(DESIGN_DOC)

    def test_stale_until_compared_with_main(self):
        assert "stale until" in _read(DESIGN_DOC)

    def test_cannot_override_agents_md(self):
        content = _read(DESIGN_DOC)
        assert "AGENTS.md" in content
        assert "cannot override" in content

    def test_cannot_override_project_status(self):
        assert "docs/project_status.md" in _read(DESIGN_DOC)

    def test_cannot_approve_work(self):
        assert "cannot approve work" in _read(DESIGN_DOC)

    def test_cannot_authorize_merge_ready_status(self):
        assert "cannot authorize merge-ready status" in _read(DESIGN_DOC)


class TestDesignDocIntendedFutureModes:
    """Section 6: Intended future modes."""

    def test_stdout_orientation_mode(self):
        assert "Stdout orientation mode" in _read(DESIGN_DOC)

    def test_snapshot_file_mode(self):
        assert "Snapshot file mode" in _read(DESIGN_DOC)

    def test_compare_staleness_mode(self):
        assert "Compare/staleness mode" in _read(DESIGN_DOC)

    def test_design_only_mode(self):
        assert "Design-only mode" in _read(DESIGN_DOC)

    def test_default_mode_writes_no_file(self):
        content = _read(DESIGN_DOC)
        assert "No file is written" in content or "no file is written" in content.lower()


class TestDesignDocCLIShape:
    """Section 7: Intended future CLI shape."""

    def test_status_snapshot_path(self):
        assert "tools/git/status_snapshot.py" in _read(DESIGN_DOC)

    def test_format_flag(self):
        assert "--format text|json|markdown" in _read(DESIGN_DOC)

    def test_output_flag(self):
        assert "--output" in _read(DESIGN_DOC)

    def test_repo_root_flag(self):
        assert "--repo-root" in _read(DESIGN_DOC)

    def test_include_deferred_flag(self):
        assert "--include-deferred" in _read(DESIGN_DOC)

    def test_include_helper_inventory_flag(self):
        assert "--include-helper-inventory" in _read(DESIGN_DOC)

    def test_include_next_wp_candidates_flag(self):
        assert "--include-next-wp-candidates" in _read(DESIGN_DOC)

    def test_include_protected_boundaries_flag(self):
        assert "--include-protected-boundaries" in _read(DESIGN_DOC)

    def test_max_deferred_items_flag(self):
        assert "--max-deferred-items" in _read(DESIGN_DOC)

    def test_check_stale_flag(self):
        assert "--check-stale" in _read(DESIGN_DOC)

    def test_fail_on_stale_flag(self):
        assert "--fail-on-stale" in _read(DESIGN_DOC)

    def test_fail_on_sensitive_hit_flag(self):
        assert "--fail-on-sensitive-hit" in _read(DESIGN_DOC)


class TestDesignDocSafeInputSources:
    """Section 8: Safe input sources."""

    def test_agents_md(self):
        assert "AGENTS.md" in _read(DESIGN_DOC)

    def test_codex_start_here(self):
        assert "CODEX_START_HERE.md" in _read(DESIGN_DOC)

    def test_docs_project_status(self):
        assert "docs/project_status.md" in _read(DESIGN_DOC)

    def test_docs_repo_truth_index(self):
        assert "docs/repo_truth_index.md" in _read(DESIGN_DOC)

    def test_docs_deferred_items_log(self):
        assert "docs/deferred_items_log.md" in _read(DESIGN_DOC)

    def test_docs_review_checklist(self):
        assert "docs/review_checklist.md" in _read(DESIGN_DOC)

    def test_docs_testing_requirements(self):
        assert "docs/testing_requirements.md" in _read(DESIGN_DOC)

    def test_docs_security_and_secrets(self):
        assert "docs/security_and_secrets.md" in _read(DESIGN_DOC)

    def test_docs_runtime_boundaries(self):
        assert "docs/runtime_boundaries.md" in _read(DESIGN_DOC)

    def test_docs_live_trading_authorization(self):
        assert "docs/live_trading_authorization.md" in _read(DESIGN_DOC)


class TestDesignDocProhibitedInputSources:
    """Section 9: Prohibited input sources."""

    def test_env_files_prohibited(self):
        assert ".env" in _read(DESIGN_DOC)

    def test_credential_files_prohibited(self):
        content = _read(DESIGN_DOC)
        assert "credential" in content.lower() or "Credential" in content

    def test_private_key_prohibited(self):
        assert "private-key" in _read(DESIGN_DOC) or "private key" in _read(DESIGN_DOC).lower()

    def test_wallet_prohibited(self):
        assert "wallet" in _read(DESIGN_DOC)

    def test_mnemonic_prohibited(self):
        assert "mnemonic" in _read(DESIGN_DOC)

    def test_token_prohibited(self):
        assert "token" in _read(DESIGN_DOC).lower()

    def test_local_account_data_prohibited(self):
        assert "local account data" in _read(DESIGN_DOC)

    def test_private_endpoint_responses_prohibited(self):
        assert "Private endpoint responses" in _read(DESIGN_DOC) or \
               "private endpoint responses" in _read(DESIGN_DOC)

    def test_local_data_prohibited_by_default(self):
        assert "local_data/" in _read(DESIGN_DOC)

    def test_generated_reports_prohibited_by_default(self):
        assert "Generated reports" in _read(DESIGN_DOC) or \
               "generated reports" in _read(DESIGN_DOC)

    def test_arbitrary_filesystem_paths_prohibited(self):
        assert "arbitrary filesystem paths" in _read(DESIGN_DOC)

    def test_network_api_prohibited(self):
        assert "network or GitHub API responses" in _read(DESIGN_DOC)

    def test_chat_history_prohibited(self):
        assert "chat history or user memory outside repo truth" in _read(DESIGN_DOC)


class TestDesignDocOutputStructure:
    """Section 10: Intended output structure."""

    def test_summary_schema_version(self):
        assert "summary schema version" in _read(DESIGN_DOC)

    def test_generated_timestamp(self):
        assert "generated timestamp" in _read(DESIGN_DOC) or \
               "Generated timestamp" in _read(DESIGN_DOC)

    def test_repo_commit_sha(self):
        assert "Repo commit SHA" in _read(DESIGN_DOC) or \
               "repo commit SHA" in _read(DESIGN_DOC) or \
               "commit SHA" in _read(DESIGN_DOC)

    def test_branch_field(self):
        assert "Branch if available" in _read(DESIGN_DOC) or \
               "branch" in _read(DESIGN_DOC)

    def test_source_repo_truth_files(self):
        assert "Source repo-truth files used" in _read(DESIGN_DOC) or \
               "source repo-truth files" in _read(DESIGN_DOC).lower()

    def test_current_phase(self):
        assert "Current phase" in _read(DESIGN_DOC) or \
               "current phase" in _read(DESIGN_DOC)

    def test_latest_merged_wp(self):
        assert "Latest merged WP" in _read(DESIGN_DOC) or \
               "latest merged WP" in _read(DESIGN_DOC)

    def test_protected_boundary_status_block(self):
        assert "Protected boundary status block" in _read(DESIGN_DOC) or \
               "protected boundary status block" in _read(DESIGN_DOC)

    def test_helper_inventory(self):
        assert "Helper inventory" in _read(DESIGN_DOC) or \
               "helper inventory" in _read(DESIGN_DOC)

    def test_open_deferred_item_digest(self):
        assert "Open deferred item digest" in _read(DESIGN_DOC) or \
               "open deferred item digest" in _read(DESIGN_DOC)

    def test_next_wp_candidate_digest(self):
        assert "Next WP candidate digest" in _read(DESIGN_DOC) or \
               "next WP candidate digest" in _read(DESIGN_DOC)

    def test_stale_snapshot_warning(self):
        assert "Stale snapshot warning" in _read(DESIGN_DOC) or \
               "stale snapshot warning" in _read(DESIGN_DOC)

    def test_advisory_only_note(self):
        assert "Advisory-only note" in _read(DESIGN_DOC) or \
               "advisory-only note" in _read(DESIGN_DOC)

    def test_repo_truth_verification_reminder(self):
        assert "Repo-truth verification reminder" in _read(DESIGN_DOC) or \
               "repo-truth verification reminder" in _read(DESIGN_DOC)

    def test_validation_human_review_reminder(self):
        assert "Validation" in _read(DESIGN_DOC) and "review reminder" in _read(DESIGN_DOC)


class TestDesignDocSanitizationModel:
    """Section 11: Sanitization and sensitive-output model."""

    def test_api_key(self):
        assert "API_KEY" in _read(DESIGN_DOC)

    def test_private_key_term(self):
        assert "PRIVATE_KEY" in _read(DESIGN_DOC)

    def test_clob_secret(self):
        assert "CLOB_SECRET" in _read(DESIGN_DOC)

    def test_clob_pass_phrase(self):
        assert "CLOB_PASS_PHRASE" in _read(DESIGN_DOC)

    def test_mnemonic_term(self):
        assert "MNEMONIC" in _read(DESIGN_DOC)

    def test_token_term(self):
        assert "TOKEN" in _read(DESIGN_DOC)

    def test_bearer(self):
        assert "Bearer" in _read(DESIGN_DOC)

    def test_private_key_blocks(self):
        assert "private-key blocks" in _read(DESIGN_DOC) or \
               "Private-key blocks" in _read(DESIGN_DOC)

    def test_redaction(self):
        assert "redact" in _read(DESIGN_DOC).lower()

    def test_not_replacement_for_gitleaks_semgrep(self):
        assert "not a replacement for gitleaks" in _read(DESIGN_DOC) or \
               "not a replacement for gitleaks or semgrep" in _read(DESIGN_DOC)


class TestDesignDocStalenessModel:
    """Section 12: Staleness model."""

    def test_commit_sha_staleness(self):
        assert "commit SHA" in _read(DESIGN_DOC)

    def test_branch_staleness(self):
        assert "Branch at generation time" in _read(DESIGN_DOC) or \
               "branch" in _read(DESIGN_DOC)

    def test_generated_timestamp_staleness(self):
        assert "Generated timestamp" in _read(DESIGN_DOC) or \
               "generated timestamp" in _read(DESIGN_DOC)

    def test_helper_version_schema(self):
        assert "helper version" in _read(DESIGN_DOC).lower() or \
               "schema version" in _read(DESIGN_DOC).lower()

    def test_input_file_list(self):
        assert "Input file list" in _read(DESIGN_DOC) or \
               "input file list" in _read(DESIGN_DOC)

    def test_current_head_differs(self):
        assert "current HEAD differs" in _read(DESIGN_DOC) or \
               "Current HEAD differs" in _read(DESIGN_DOC)

    def test_required_repo_truth_files_changed(self):
        assert "required repo-truth files changed" in _read(DESIGN_DOC) or \
               "Required repo-truth files changed" in _read(DESIGN_DOC)

    def test_schema_unsupported(self):
        assert "schema is unsupported" in _read(DESIGN_DOC) or \
               "Schema version is absent or unsupported" in _read(DESIGN_DOC)


class TestDesignDocLifecycleStoragePolicy:
    """Section 13: Snapshot lifecycle and storage policy."""

    def test_default_no_file_generated(self):
        content = _read(DESIGN_DOC)
        assert "Default" in content and "no file" in content.lower()

    def test_local_data_status_snapshots(self):
        assert "local_data/status_snapshots/" in _read(DESIGN_DOC)

    def test_never_staged_or_committed(self):
        assert "never be staged or committed" in _read(DESIGN_DOC) or \
               "never staged or committed" in _read(DESIGN_DOC)

    def test_no_tracked_memory_file(self):
        assert "No tracked memory file" in _read(DESIGN_DOC) or \
               "no tracked memory file" in _read(DESIGN_DOC)

    def test_no_durable_project_memory_outside_repo_truth(self):
        assert "no durable project memory outside repo truth" in _read(DESIGN_DOC) or \
               "No durable project memory outside repo truth" in _read(DESIGN_DOC)


class TestDesignDocRelationshipToExistingHelpers:
    """Section 14: Relationship to existing helpers."""

    def test_diff_scope_helper_mentioned(self):
        assert "Diff/scope helper" in _read(DESIGN_DOC) or \
               "diff_scope_summary" in _read(DESIGN_DOC)

    def test_validation_output_helper_mentioned(self):
        assert "Validation-output helper" in _read(DESIGN_DOC) or \
               "validation_output_summary" in _read(DESIGN_DOC)

    def test_code_blast_radius_helper_mentioned(self):
        assert "Code blast-radius helper" in _read(DESIGN_DOC) or \
               "code_blast_radius" in _read(DESIGN_DOC)

    def test_none_replace_mandatory_validation(self):
        assert "None of these helpers replace mandatory validation" in _read(DESIGN_DOC) or \
               "none replace mandatory validation or review" in _read(DESIGN_DOC).lower() or \
               "do not replace mandatory validation" in _read(DESIGN_DOC)


class TestDesignDocFutureTestPlan:
    """Section 16: Future implementation test plan."""

    def test_safe_input_source_allowlist_tests(self):
        assert "safe input source allowlist tests" in _read(DESIGN_DOC) or \
               "Safe input source allowlist tests" in _read(DESIGN_DOC)

    def test_prohibited_input_source_rejection_tests(self):
        assert "prohibited input source rejection tests" in _read(DESIGN_DOC) or \
               "Prohibited input source rejection tests" in _read(DESIGN_DOC)

    def test_output_path_restriction_tests(self):
        assert "output path restriction tests" in _read(DESIGN_DOC) or \
               "Output path restriction tests" in _read(DESIGN_DOC)

    def test_status_parsing_tests(self):
        assert "status parsing tests" in _read(DESIGN_DOC) or \
               "Status parsing tests" in _read(DESIGN_DOC)

    def test_deferred_item_digest_tests(self):
        assert "deferred item digest tests" in _read(DESIGN_DOC) or \
               "Deferred item digest tests" in _read(DESIGN_DOC)

    def test_helper_inventory_tests(self):
        assert "helper inventory tests" in _read(DESIGN_DOC) or \
               "Helper inventory tests" in _read(DESIGN_DOC)

    def test_next_wp_candidate_extraction_tests(self):
        assert "next WP candidate extraction tests" in _read(DESIGN_DOC) or \
               "Next WP candidate extraction tests" in _read(DESIGN_DOC)

    def test_stale_snapshot_metadata_tests(self):
        assert "stale snapshot metadata tests" in _read(DESIGN_DOC) or \
               "Stale snapshot metadata tests" in _read(DESIGN_DOC)

    def test_sensitive_output_redaction_tests(self):
        assert "sensitive-output redaction tests" in _read(DESIGN_DOC) or \
               "Sensitive-output redaction tests" in _read(DESIGN_DOC)

    def test_no_network_no_command_execution_tests(self):
        assert "no-network" in _read(DESIGN_DOC) or \
               "No-network" in _read(DESIGN_DOC) or \
               "no-command-execution" in _read(DESIGN_DOC)

    def test_windows_path_handling_tests(self):
        assert "Windows path handling tests" in _read(DESIGN_DOC) or \
               "windows path" in _read(DESIGN_DOC).lower()


class TestDesignDocOpenQuestionsAndNextWP:
    """Sections 17-18: Open design questions and recommended next WP."""

    def test_open_design_questions_section_exists(self):
        assert "Open Design Questions" in _read(DESIGN_DOC) or \
               "Open design questions" in _read(DESIGN_DOC)

    def test_recommended_next_wp_section_exists(self):
        assert "Recommended Next WP" in _read(DESIGN_DOC) or \
               "Recommended next WP" in _read(DESIGN_DOC)

    def test_recommended_next_wp_references_wp36(self):
        assert "WP36" in _read(DESIGN_DOC)


class TestRepoTruthIndexUpdated:
    """Repo-truth index must include the new design doc with no gaps or duplicates."""

    def test_design_doc_indexed(self):
        content = _read(REPO_TRUTH_INDEX)
        assert "MEMORY_STATUS_SNAPSHOT_HELPER_DESIGN.md" in content, \
            "Design doc not indexed in docs/repo_truth_index.md"

    def test_no_duplicate_numeric_prefixes(self):
        content = _read(REPO_TRUTH_INDEX)
        numbers = re.findall(r"^(\d+)\.\s+`", content, re.MULTILINE)
        assert len(numbers) == len(set(numbers)), \
            f"Duplicate numeric prefixes in repo_truth_index.md: {numbers}"

    def test_sequential_numeric_prefixes(self):
        content = _read(REPO_TRUTH_INDEX)
        numbers = [int(n) for n in re.findall(r"^(\d+)\.\s+`", content, re.MULTILINE)]
        if numbers:
            assert numbers == list(range(numbers[0], numbers[0] + len(numbers))), \
                f"Non-sequential numeric prefixes: {numbers}"


class TestCrossReferenceDocs:
    """TOKEN_EFFICIENCY_OPERATING_MODEL.md and README.md must reference the design doc."""

    def test_token_efficiency_references_design_doc(self):
        content = _read(TOKEN_EFFICIENCY_DOC)
        assert "MEMORY_STATUS_SNAPSHOT_HELPER_DESIGN.md" in content or \
               "memory/status snapshot" in content.lower(), \
            "TOKEN_EFFICIENCY_OPERATING_MODEL.md does not reference the design doc"

    def test_codex_readme_references_design_doc(self):
        content = _read(CODEX_README)
        assert "MEMORY_STATUS_SNAPSHOT_HELPER_DESIGN.md" in content or \
               "memory" in content.lower() and "snapshot" in content.lower(), \
            "docs/ai/codex/README.md does not reference the design doc"


class TestNoImplementationPaths:
    """WP35 was design-only; WP36 added the implementation.

    The implementation helper (tools/git/status_snapshot.py) and user-facing
    reference (docs/ai/codex/MEMORY_STATUS_SNAPSHOT_HELPER.md) now exist.
    Tests below are updated to reflect the WP36 implementation state while
    preserving all other design-doc integrity checks.
    """

    def test_status_snapshot_py_is_present_in_wp36(self):
        # WP36 implemented tools/git/status_snapshot.py — it must now exist.
        assert (REPO_ROOT / "tools/git/status_snapshot.py").exists(), \
            "tools/git/status_snapshot.py must exist after WP36 implementation"

    def test_no_memory_snapshot_py(self):
        assert not (REPO_ROOT / "tools/git/memory_snapshot.py").exists(), \
            "tools/git/memory_snapshot.py must not exist"

    def test_no_tools_memory_snapshot_glob(self):
        matches = list((REPO_ROOT / "tools").glob("memory_snapshot*")) if \
            (REPO_ROOT / "tools").exists() else []
        assert len(matches) == 0, f"Unexpected memory_snapshot files in tools/: {matches}"

    def test_no_local_data_status_snapshots_tracked(self):
        # local_data/ is git-ignored; snapshots must not be tracked
        # Directory may exist from optional smoke tests but must not be committed
        import subprocess
        result = subprocess.run(
            ["git", "ls-files", "local_data/status_snapshots"],
            capture_output=True, text=True, cwd=str(REPO_ROOT),
        )
        # git ls-files returns empty if the path is untracked (git-ignored)
        assert result.stdout.strip() == "", \
            f"local_data/status_snapshots/ must not contain tracked files: {result.stdout}"

    def test_memory_status_snapshot_helper_md_is_present_in_wp36(self):
        # WP36 added docs/ai/codex/MEMORY_STATUS_SNAPSHOT_HELPER.md
        assert (REPO_ROOT / "docs/ai/codex/MEMORY_STATUS_SNAPSHOT_HELPER.md").exists(), \
            "docs/ai/codex/MEMORY_STATUS_SNAPSHOT_HELPER.md must not exist in WP35"

    def test_no_src_agents(self):
        assert not (REPO_ROOT / "src/agents").exists(), \
            "src/agents/ must not exist"

    def test_no_src_agent_layer(self):
        assert not (REPO_ROOT / "src/agent_layer").exists(), \
            "src/agent_layer/ must not exist"

    def test_no_tools_hermes(self):
        assert not (REPO_ROOT / "tools/hermes").exists(), \
            "tools/hermes/ must not exist"

    def test_no_agent_runtime(self):
        assert not (REPO_ROOT / "agent_runtime").exists(), \
            "agent_runtime/ must not exist"

    def test_no_agent_memory(self):
        assert not (REPO_ROOT / "agent_memory").exists(), \
            "agent_memory/ must not exist"


class TestNoDependencyFilesAddForbiddenPackages:
    """Dependency files must not introduce forbidden packages."""

    FORBIDDEN_PACKAGES = [
        "openai",
        "anthropic",
        "langchain",
        "hermes",
        "token-savior",
        "code-review-graph",
        "tree-sitter",
        "networkx",
        "graphviz",
        "chromadb",
        "llama-index",
        "mem0",
        "rich",
        "click",
        "typer",
    ]

    def _read_dep_files(self):
        dep_files = [
            REPO_ROOT / "requirements.txt",
            REPO_ROOT / "requirements-dev.txt",
            REPO_ROOT / "pyproject.toml",
            REPO_ROOT / "setup.cfg",
            REPO_ROOT / "setup.py",
        ]
        content = ""
        for f in dep_files:
            if f.exists():
                content += f.read_text(encoding="utf-8").lower()
        return content

    def test_no_forbidden_packages_in_dep_files(self):
        content = self._read_dep_files()
        if not content:
            return
        for pkg in self.FORBIDDEN_PACKAGES:
            assert pkg.lower() not in content, \
                f"Forbidden package '{pkg}' found in dependency files"
