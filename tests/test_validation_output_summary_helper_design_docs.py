"""
WP31: Tests enforcing the validation output summary helper design document and cross-references.
"""

import pathlib
import re

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
DESIGN_DOC = REPO_ROOT / "docs/ai/codex/VALIDATION_OUTPUT_SUMMARY_HELPER_DESIGN.md"
REPO_TRUTH_INDEX = REPO_ROOT / "docs/repo_truth_index.md"
TOKEN_EFFICIENCY_DOC = REPO_ROOT / "docs/ai/codex/TOKEN_EFFICIENCY_OPERATING_MODEL.md"
CONCISE_REPORTING_DOC = REPO_ROOT / "docs/ai/codex/CONCISE_REPORTING_RULES.md"
VALIDATION_MATRIX_DOC = REPO_ROOT / "docs/ai/codex/VALIDATION_MATRIX.md"
README_DOC = REPO_ROOT / "docs/ai/codex/README.md"
PYPROJECT = REPO_ROOT / "pyproject.toml"


def _read(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# 1. Design doc exists
# ---------------------------------------------------------------------------

def test_design_doc_exists():
    assert DESIGN_DOC.exists(), f"Missing: {DESIGN_DOC}"


# ---------------------------------------------------------------------------
# 2. Design doc status phrases
# ---------------------------------------------------------------------------

def test_design_doc_status_design_only():
    assert "DESIGN_ONLY" in _read(DESIGN_DOC)


def test_design_doc_status_not_implemented():
    assert "NOT_IMPLEMENTED" in _read(DESIGN_DOC)


def test_design_doc_applies_to_claude_code_and_codex():
    assert "Claude Code and Codex" in _read(DESIGN_DOC)


def test_design_doc_no_runtime_change():
    assert "NO_RUNTIME_CHANGE" in _read(DESIGN_DOC)


def test_design_doc_no_tool_implementation():
    assert "NO_TOOL_IMPLEMENTATION" in _read(DESIGN_DOC)


def test_design_doc_no_dependency_change():
    assert "NO_DEPENDENCY_CHANGE" in _read(DESIGN_DOC)


def test_design_doc_no_network():
    assert "NO_NETWORK" in _read(DESIGN_DOC)


def test_design_doc_no_validation_weakening():
    assert "NO_VALIDATION_WEAKENING" in _read(DESIGN_DOC)


def test_design_doc_no_protected_boundary_change():
    assert "NO_PROTECTED_BOUNDARY_CHANGE" in _read(DESIGN_DOC)


# ---------------------------------------------------------------------------
# 3. Intended future modes
# ---------------------------------------------------------------------------

def test_design_doc_parser_mode():
    assert "Parser mode" in _read(DESIGN_DOC)


def test_design_doc_metadata_mode():
    assert "Metadata mode" in _read(DESIGN_DOC)


def test_design_doc_future_runner_mode():
    assert "Future runner mode" in _read(DESIGN_DOC)


def test_design_doc_prefers_parser_metadata_mode():
    content = _read(DESIGN_DOC)
    assert "first implementation should prefer parser/metadata mode" in content


# ---------------------------------------------------------------------------
# 4. Intended future CLI shape
# ---------------------------------------------------------------------------

def test_design_doc_cli_path():
    assert "tools/validation/validation_output_summary.py" in _read(DESIGN_DOC)


def test_design_doc_flag_command():
    assert "`--command`" in _read(DESIGN_DOC)


def test_design_doc_flag_exit_code():
    assert "`--exit-code`" in _read(DESIGN_DOC)


def test_design_doc_flag_check_type():
    assert "`--check-type`" in _read(DESIGN_DOC)


def test_design_doc_flag_stdout_file():
    assert "`--stdout-file`" in _read(DESIGN_DOC)


def test_design_doc_flag_stderr_file():
    assert "`--stderr-file`" in _read(DESIGN_DOC)


def test_design_doc_flag_from_stdin():
    assert "`--from-stdin`" in _read(DESIGN_DOC)


def test_design_doc_flag_format():
    assert "`--format text|json`" in _read(DESIGN_DOC)


def test_design_doc_flag_max_failure_lines():
    assert "`--max-failure-lines`" in _read(DESIGN_DOC)


def test_design_doc_flag_tool_availability():
    assert "`--tool-availability`" in _read(DESIGN_DOC)


def test_design_doc_flag_output():
    assert "`--output`" in _read(DESIGN_DOC)


def test_design_doc_flag_fail_on_missing_required_evidence():
    assert "`--fail-on-missing-required-evidence`" in _read(DESIGN_DOC)


# ---------------------------------------------------------------------------
# 5. Intended input sources
# ---------------------------------------------------------------------------

def test_design_doc_input_explicit_command_string():
    assert "explicit command string" in _read(DESIGN_DOC)


def test_design_doc_input_exit_code():
    assert "exit code" in _read(DESIGN_DOC).lower()


def test_design_doc_input_stdout_stderr():
    assert "stdout/stderr snippets or files" in _read(DESIGN_DOC)


def test_design_doc_input_pytest_result_lines():
    assert "pytest result lines" in _read(DESIGN_DOC)


def test_design_doc_input_artifact_guard():
    assert "Generated artifact guard output" in _read(DESIGN_DOC)


def test_design_doc_input_sync_gate():
    assert "Remote Main Sync Gate output" in _read(DESIGN_DOC)


def test_design_doc_input_security_tool_availability():
    assert "security tool availability output" in _read(DESIGN_DOC)


def test_design_doc_input_diff_scope_helper():
    assert "diff/scope helper output" in _read(DESIGN_DOC)


# ---------------------------------------------------------------------------
# 6. Intended output fields
# ---------------------------------------------------------------------------

def test_design_doc_output_field_command():
    assert "**command**" in _read(DESIGN_DOC)


def test_design_doc_output_field_check_type():
    assert "**check type**" in _read(DESIGN_DOC)


def test_design_doc_output_field_exit_code():
    assert "**exit code**" in _read(DESIGN_DOC)


def test_design_doc_output_field_status():
    assert "**status**" in _read(DESIGN_DOC)


def test_design_doc_output_field_pass_count():
    assert "**pass count**" in _read(DESIGN_DOC)


def test_design_doc_output_field_warning_count():
    assert "**warning count**" in _read(DESIGN_DOC)


def test_design_doc_output_field_unavailable_tools_list():
    assert "**unavailable tools list**" in _read(DESIGN_DOC)


def test_design_doc_output_field_generated_output_paths():
    assert "**generated output paths**" in _read(DESIGN_DOC)


def test_design_doc_output_field_failure_snippet():
    assert "**failure snippet**" in _read(DESIGN_DOC)


def test_design_doc_output_field_truncation_indicator():
    assert "**truncation indicator**" in _read(DESIGN_DOC)


def test_design_doc_output_field_validation_reminder():
    assert "**validation reminder**" in _read(DESIGN_DOC)


def test_design_doc_output_field_raw_log_retention_note():
    assert "**raw log retention note**" in _read(DESIGN_DOC)


# ---------------------------------------------------------------------------
# 7. Status classification rules
# ---------------------------------------------------------------------------

def test_design_doc_status_pass():
    assert "**PASS**" in _read(DESIGN_DOC)


def test_design_doc_status_fail():
    assert "**FAIL**" in _read(DESIGN_DOC)


def test_design_doc_status_skipped():
    assert "**SKIPPED**" in _read(DESIGN_DOC)


def test_design_doc_status_unavailable():
    assert "**UNAVAILABLE**" in _read(DESIGN_DOC)


def test_design_doc_status_partial():
    assert "**PARTIAL**" in _read(DESIGN_DOC)


def test_design_doc_status_error():
    assert "**ERROR**" in _read(DESIGN_DOC)


def test_design_doc_unavailable_tools_not_pass():
    content = _read(DESIGN_DOC)
    assert "unavailable" in content.lower() and "must not be summarized as" in content.lower()


def test_design_doc_missing_result_not_pass():
    content = _read(DESIGN_DOC)
    assert "missing command result" in content.lower() and "must not be summarized as" in content.lower()


# ---------------------------------------------------------------------------
# 8. Validation preservation rules
# ---------------------------------------------------------------------------

def test_design_doc_preserves_focused_tests():
    assert "focused tests" in _read(DESIGN_DOC)


def test_design_doc_preserves_full_pytest():
    assert "full pytest" in _read(DESIGN_DOC)


def test_design_doc_preserves_artifact_guard():
    assert "generated artifact guard" in _read(DESIGN_DOC).lower()


def test_design_doc_preserves_remote_main_sync_gate():
    assert "Remote Main Sync Gate" in _read(DESIGN_DOC)


def test_design_doc_preserves_security_checks():
    assert "security checks" in _read(DESIGN_DOC)


def test_design_doc_preserves_git_diff_check():
    assert "git diff --check" in _read(DESIGN_DOC)


def test_design_doc_preserves_human_review():
    assert "human review" in _read(DESIGN_DOC)


def test_design_doc_preserves_final_pr_comment():
    assert "final PR comment" in _read(DESIGN_DOC)


def test_design_doc_cannot_authorize_merge_ready():
    content = _read(DESIGN_DOC)
    assert "helper cannot authorize merge-ready status by itself" in content


# ---------------------------------------------------------------------------
# 9. Future implementation test plan
# ---------------------------------------------------------------------------

def test_design_doc_test_plan_pytest_parser():
    assert "pytest pass/fail/warning parser tests" in _read(DESIGN_DOC)


def test_design_doc_test_plan_artifact_guard_parser():
    assert "generated artifact guard parser tests" in _read(DESIGN_DOC)


def test_design_doc_test_plan_sync_gate_parser():
    assert "Remote Main Sync Gate parser tests" in _read(DESIGN_DOC)


def test_design_doc_test_plan_security_tool_states():
    assert "security tool unavailable/skipped/passed/failed tests" in _read(DESIGN_DOC)


def test_design_doc_test_plan_status_classification():
    assert "status classification tests" in _read(DESIGN_DOC)


def test_design_doc_test_plan_truncation():
    assert "failure-snippet truncation tests" in _read(DESIGN_DOC)


def test_design_doc_test_plan_secret_handling():
    assert "secret-like output handling tests" in _read(DESIGN_DOC)


def test_design_doc_test_plan_json_text_output():
    assert "JSON/text output tests" in _read(DESIGN_DOC)


def test_design_doc_test_plan_output_path_restriction():
    assert "output path restriction tests" in _read(DESIGN_DOC)


def test_design_doc_test_plan_windows_paths():
    assert "Windows path handling tests" in _read(DESIGN_DOC)


# ---------------------------------------------------------------------------
# 10. Open design questions and recommended next WP
# ---------------------------------------------------------------------------

def test_design_doc_has_open_design_questions():
    content = _read(DESIGN_DOC)
    assert "Open Design Questions" in content or "open design questions" in content.lower()


def test_design_doc_has_recommended_next_wp():
    content = _read(DESIGN_DOC)
    assert "Recommended Next WP" in content or "recommended next WP" in content.lower()


def test_design_doc_next_wp_references_wp32():
    assert "WP32" in _read(DESIGN_DOC)


# ---------------------------------------------------------------------------
# 11. Repo truth index
# ---------------------------------------------------------------------------

def test_repo_truth_index_contains_design_doc():
    content = _read(REPO_TRUTH_INDEX)
    assert "VALIDATION_OUTPUT_SUMMARY_HELPER_DESIGN.md" in content


def test_repo_truth_index_no_duplicate_numeric_prefixes():
    content = _read(REPO_TRUTH_INDEX)
    numbers = re.findall(r"^(\d+)\. ", content, re.MULTILINE)
    assert len(numbers) == len(set(numbers)), (
        f"Duplicate numeric prefixes found: {[n for n in numbers if numbers.count(n) > 1]}"
    )


# ---------------------------------------------------------------------------
# 12-15. Cross-reference checks in existing docs
# ---------------------------------------------------------------------------

def test_token_efficiency_doc_references_design_doc():
    content = _read(TOKEN_EFFICIENCY_DOC)
    assert "VALIDATION_OUTPUT_SUMMARY_HELPER_DESIGN.md" in content


def test_concise_reporting_doc_references_design_doc():
    content = _read(CONCISE_REPORTING_DOC)
    assert "VALIDATION_OUTPUT_SUMMARY_HELPER_DESIGN.md" in content


def test_validation_matrix_doc_references_design_doc():
    content = _read(VALIDATION_MATRIX_DOC)
    assert "VALIDATION_OUTPUT_SUMMARY_HELPER_DESIGN.md" in content


def test_readme_doc_references_design_doc():
    content = _read(README_DOC)
    assert "VALIDATION_OUTPUT_SUMMARY_HELPER_DESIGN.md" in content


# ---------------------------------------------------------------------------
# 16. No implementation paths exist
# ---------------------------------------------------------------------------

def test_no_validation_output_summary_implementation():
    impl = REPO_ROOT / "tools/validation/validation_output_summary.py"
    assert not impl.exists(), f"Forbidden implementation file exists: {impl}"


def test_no_validation_output_summary_at_tools_root():
    impl = REPO_ROOT / "tools/validation_output_summary.py"
    assert not impl.exists(), f"Forbidden implementation file exists: {impl}"


def test_no_validation_summary_glob():
    matches = list((REPO_ROOT / "tools").glob("validation_summary*"))
    assert not matches, f"Forbidden validation_summary* files found: {matches}"


def test_no_command_output_glob():
    matches = list((REPO_ROOT / "tools").glob("command_output*"))
    assert not matches, f"Forbidden command_output* files found: {matches}"


def test_no_output_compression_glob():
    matches = list((REPO_ROOT / "tools").glob("output_compression*"))
    assert not matches, f"Forbidden output_compression* files found: {matches}"


def test_no_src_agents():
    assert not (REPO_ROOT / "src/agents").exists()


def test_no_src_agent_layer():
    assert not (REPO_ROOT / "src/agent_layer").exists()


def test_no_tools_hermes():
    assert not (REPO_ROOT / "tools/hermes").exists()


def test_no_agent_runtime():
    assert not (REPO_ROOT / "agent_runtime").exists()


def test_no_agent_memory():
    assert not (REPO_ROOT / "agent_memory").exists()


# ---------------------------------------------------------------------------
# 17. Dependency files do not add forbidden dependencies
# ---------------------------------------------------------------------------

_FORBIDDEN_DEPS = [
    "RTK",
    "openai",
    "anthropic",
    "langchain",
    "hermes",
    "token-savior",
    "code-review-graph",
    "tree-sitter",
    '"rich"',
    '"click"',
    '"typer"',
]


def test_pyproject_no_forbidden_dependencies():
    if not PYPROJECT.exists():
        return
    content = _read(PYPROJECT).lower()
    for dep in _FORBIDDEN_DEPS:
        assert dep.lower() not in content, (
            f"Forbidden dependency '{dep}' found in pyproject.toml"
        )
