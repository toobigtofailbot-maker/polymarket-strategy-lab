"""Tests for WP29 diff scope summary helper design docs and cross-references."""

import pathlib
import re

REPO_ROOT = pathlib.Path(__file__).parent.parent

DESIGN_DOC = REPO_ROOT / "docs/ai/codex/DIFF_SCOPE_SUMMARY_HELPER_DESIGN.md"
REPO_TRUTH_INDEX = REPO_ROOT / "docs/repo_truth_index.md"
TOKEN_EFFICIENCY_DOC = REPO_ROOT / "docs/ai/codex/TOKEN_EFFICIENCY_OPERATING_MODEL.md"
CODEX_README = REPO_ROOT / "docs/ai/codex/README.md"


# --- 1. Design doc exists ---

def test_design_doc_exists():
    assert DESIGN_DOC.exists(), "DIFF_SCOPE_SUMMARY_HELPER_DESIGN.md must exist"


# --- 2. Design doc contains required status phrases ---

def test_design_doc_status_fields():
    text = DESIGN_DOC.read_text(encoding="utf-8")
    for phrase in [
        "DESIGN_ONLY",
        "NOT_IMPLEMENTED",
        "Claude Code and Codex",
        "NO_RUNTIME_CHANGE",
        "NO_DEPENDENCY_CHANGE",
        "NO_NETWORK",
        "NO_VALIDATION_WEAKENING",
        "NO_PROTECTED_BOUNDARY_CHANGE",
    ]:
        assert phrase in text, f"DIFF_SCOPE_SUMMARY_HELPER_DESIGN.md must contain: {phrase}"


# --- 3. Design doc contains future helper constraints ---

def test_design_doc_future_helper_constraints():
    text = DESIGN_DOC.read_text(encoding="utf-8").lower()
    for phrase in [
        "standard-library only",
        "local",
        "offline",
        "read-only",
        "no dependency",
        "no network calls",
        "no mutation",
        "stdout summary by default",
    ]:
        assert phrase in text, (
            f"DIFF_SCOPE_SUMMARY_HELPER_DESIGN.md must contain future helper constraint: {phrase}"
        )


# --- 4. Design doc contains intended future CLI shape ---

def test_design_doc_cli_shape():
    text = DESIGN_DOC.read_text(encoding="utf-8")
    for phrase in [
        "tools/git/diff_scope_summary.py",
        "--base",
        "--head",
        "--package-class",
        "--allowed-file",
        "--allowed-prefix",
        "--forbidden-prefix",
    ]:
        assert phrase in text, (
            f"DIFF_SCOPE_SUMMARY_HELPER_DESIGN.md must contain CLI shape element: {phrase}"
        )


# --- 5. Design doc contains intended input sources ---

def test_design_doc_input_sources():
    text = DESIGN_DOC.read_text(encoding="utf-8")
    for phrase in [
        "git diff --name-status",
        "git diff --stat",
        "git diff --check",
        "allowed",
        "forbidden",
        "protected-path",
    ]:
        assert phrase in text, (
            f"DIFF_SCOPE_SUMMARY_HELPER_DESIGN.md must reference input source: {phrase}"
        )


# --- 6. Design doc contains required output fields ---

def test_design_doc_output_fields():
    text = DESIGN_DOC.read_text(encoding="utf-8").lower()
    for phrase in [
        "changed file count",
        "files outside",
        "protected-path hits",
        "dependency",
        "lock-file",
        "generated-artifact",
        "local_data",
        "package-class warnings",
        "validation reminder",
    ]:
        assert phrase in text, (
            f"DIFF_SCOPE_SUMMARY_HELPER_DESIGN.md must contain output field: {phrase}"
        )


# --- 7. Design doc contains package-class warnings ---

def test_design_doc_package_class_warnings():
    text = DESIGN_DOC.read_text(encoding="utf-8").lower()
    for phrase in [
        "docs-only",
        "runtime source",
        "design wp",
        "read-only public-data",
        "live-trading",
        "live_trading_authorization",
    ]:
        assert phrase in text, (
            f"DIFF_SCOPE_SUMMARY_HELPER_DESIGN.md must document package-class warning for: {phrase}"
        )


# --- 8. Design doc contains exit status design ---

def test_design_doc_exit_status():
    text = DESIGN_DOC.read_text(encoding="utf-8")
    for phrase in ["0", "1", "2"]:
        assert phrase in text, (
            f"DIFF_SCOPE_SUMMARY_HELPER_DESIGN.md must define exit status: {phrase}"
        )
    assert "bypass" in text.lower() or "must not use" in text.lower(), (
        "DIFF_SCOPE_SUMMARY_HELPER_DESIGN.md must state exit status cannot bypass validation"
    )


# --- 9. Design doc contains future implementation test plan ---

def test_design_doc_future_test_plan():
    text = DESIGN_DOC.read_text(encoding="utf-8").lower()
    for phrase in [
        "fixture-based tests",
        "protected path detection",
        "dependency",
        "lock-file detection",
        "generated artifact detection",
        "windows path handling",
    ]:
        assert phrase in text, (
            f"DIFF_SCOPE_SUMMARY_HELPER_DESIGN.md future test plan must mention: {phrase}"
        )


# --- 10. Design doc contains open design questions and recommended next WP ---

def test_design_doc_open_questions():
    text = DESIGN_DOC.read_text(encoding="utf-8").lower()
    assert "open design question" in text, (
        "DIFF_SCOPE_SUMMARY_HELPER_DESIGN.md must contain open design questions"
    )


def test_design_doc_recommended_next_wp():
    text = DESIGN_DOC.read_text(encoding="utf-8").lower()
    assert "recommended next wp" in text or "next wp" in text, (
        "DIFF_SCOPE_SUMMARY_HELPER_DESIGN.md must contain a recommended next WP"
    )
    assert "wp30" in text, (
        "DIFF_SCOPE_SUMMARY_HELPER_DESIGN.md must mention WP30 as a candidate next WP"
    )


# --- 11. Repo truth index indexes the design doc ---

def test_repo_truth_index_includes_design_doc():
    text = REPO_TRUTH_INDEX.read_text(encoding="utf-8")
    assert "DIFF_SCOPE_SUMMARY_HELPER_DESIGN" in text, (
        "docs/repo_truth_index.md must index DIFF_SCOPE_SUMMARY_HELPER_DESIGN"
    )


def test_repo_truth_index_no_duplicate_numbers():
    text = REPO_TRUTH_INDEX.read_text(encoding="utf-8")
    numbers = re.findall(r"^\s*(\d+)\.", text, re.MULTILINE)
    numbers = [int(n) for n in numbers]
    assert len(numbers) == len(set(numbers)), (
        f"docs/repo_truth_index.md Authority Hierarchy has duplicate numeric prefixes: "
        f"{[n for n in numbers if numbers.count(n) > 1]}"
    )


# --- 12. TOKEN_EFFICIENCY_OPERATING_MODEL.md references the design doc ---

def test_token_efficiency_doc_references_design_doc():
    text = TOKEN_EFFICIENCY_DOC.read_text(encoding="utf-8")
    assert "DIFF_SCOPE_SUMMARY_HELPER_DESIGN" in text, (
        "TOKEN_EFFICIENCY_OPERATING_MODEL.md must reference DIFF_SCOPE_SUMMARY_HELPER_DESIGN"
    )


# --- 13. docs/ai/codex/README.md references the design doc ---

def test_codex_readme_references_design_doc():
    text = CODEX_README.read_text(encoding="utf-8")
    assert "DIFF_SCOPE_SUMMARY_HELPER_DESIGN" in text, (
        "docs/ai/codex/README.md must reference DIFF_SCOPE_SUMMARY_HELPER_DESIGN"
    )


# --- 14. No implementation paths exist ---

def test_no_diff_scope_helper_implementation():
    for pattern in [
        "tools/git/diff_scope_summary.py",
        "tools/diff_scope_summary.py",
        "tools/diff_summary*",
        "tools/scope_summary*",
    ]:
        matches = list(REPO_ROOT.glob(pattern))
        assert not matches, (
            f"No implementation may exist for forbidden path pattern: {pattern}"
        )


def test_no_agent_runtime_dirs():
    for dirname in [
        "src/agents",
        "src/agent_layer",
        "tools/hermes",
        "agent_runtime",
        "agent_memory",
    ]:
        path = REPO_ROOT / dirname
        assert not path.exists(), f"Forbidden directory must not exist: {dirname}"


# --- 15. Dependency files do not add forbidden dependencies ---

def _get_dependency_files():
    files = []
    for name in [
        "requirements.txt",
        "requirements-dev.txt",
        "pyproject.toml",
        "setup.cfg",
        "setup.py",
        "Pipfile",
    ]:
        p = REPO_ROOT / name
        if p.exists():
            files.append(p)
    return files


def test_no_forbidden_dependencies():
    forbidden = [
        "rtk",
        "openai",
        "anthropic",
        "langchain",
        "hermes",
        "token-savior",
        "code-review-graph",
        "tree-sitter",
        "rich",
        "click",
        "typer",
    ]
    for dep_file in _get_dependency_files():
        text = dep_file.read_text(encoding="utf-8").lower()
        for term in forbidden:
            assert term not in text, (
                f"Dependency file {dep_file.name} must not add forbidden dependency: {term}"
            )
