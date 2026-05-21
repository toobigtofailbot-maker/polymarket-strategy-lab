"""Tests for WP28 token-efficiency operating model docs and cross-references."""

import pathlib

REPO_ROOT = pathlib.Path(__file__).parent.parent

TOKEN_EFFICIENCY_DOC = REPO_ROOT / "docs/ai/codex/TOKEN_EFFICIENCY_OPERATING_MODEL.md"
CONCISE_REPORTING_DOC = REPO_ROOT / "docs/ai/codex/CONCISE_REPORTING_RULES.md"
REUSABLE_BLOCKS_DOC = REPO_ROOT / "docs/ai/codex/REUSABLE_WP_PROMPT_BLOCKS.md"
AGENTS_MD = REPO_ROOT / "AGENTS.md"
CODEX_START_HERE = REPO_ROOT / "CODEX_START_HERE.md"
CODEX_README = REPO_ROOT / "docs/ai/codex/README.md"
CODEX_EXEC_GUIDELINES = REPO_ROOT / "docs/codex_execution_guidelines.md"
WORK_PACKAGE_TEMPLATE = REPO_ROOT / "docs/work_package_template.md"
PR_TEMPLATE = REPO_ROOT / ".github/pull_request_template.md"
REPO_TRUTH_INDEX = REPO_ROOT / "docs/repo_truth_index.md"


# --- 1. New docs exist ---

def test_token_efficiency_doc_exists():
    assert TOKEN_EFFICIENCY_DOC.exists(), "TOKEN_EFFICIENCY_OPERATING_MODEL.md must exist"


def test_concise_reporting_doc_exists():
    assert CONCISE_REPORTING_DOC.exists(), "CONCISE_REPORTING_RULES.md must exist"


def test_reusable_blocks_doc_exists():
    assert REUSABLE_BLOCKS_DOC.exists(), "REUSABLE_WP_PROMPT_BLOCKS.md must exist"


# --- 2. Token-efficiency doc content ---

def test_token_efficiency_doc_status_fields():
    text = TOKEN_EFFICIENCY_DOC.read_text(encoding="utf-8")
    for phrase in [
        "ACTIVE_REPO_TRUTH_GUIDANCE",
        "Codex and Claude Code",
        "NO_VALIDATION_WEAKENING",
        "NO_RUNTIME_CHANGE",
        "NO_DEPENDENCY_CHANGE",
        "NO_PROTECTED_BOUNDARY_CHANGE",
    ]:
        assert phrase in text, f"TOKEN_EFFICIENCY_OPERATING_MODEL.md must contain: {phrase}"


def test_token_efficiency_doc_sections():
    text = TOKEN_EFFICIENCY_DOC.read_text(encoding="utf-8")
    for phrase in [
        "context hygiene",
        "validation-output summarization",
        "reusable prompt blocks",
        "future helper-tool design gates",
    ]:
        assert phrase.lower() in text.lower(), (
            f"TOKEN_EFFICIENCY_OPERATING_MODEL.md must contain section/content: {phrase}"
        )


# --- 3. Concise-reporting doc content ---

def test_concise_reporting_doc_mandatory_final_comment():
    text = CONCISE_REPORTING_DOC.read_text(encoding="utf-8").lower()
    assert "final pr comment" in text and "mandatory" in text, (
        "CONCISE_REPORTING_RULES.md must state that the final PR comment remains mandatory"
    )


def test_concise_reporting_doc_pr_body_not_replacement():
    text = CONCISE_REPORTING_DOC.read_text(encoding="utf-8")
    assert "PR body does not replace" in text, (
        "CONCISE_REPORTING_RULES.md must state that the PR body does not replace the final report"
    )


def test_concise_reporting_doc_required_sections():
    text = CONCISE_REPORTING_DOC.read_text(encoding="utf-8")
    for phrase in [
        "Validation summary",
        "Boundary check",
        "Deferred items",
        "Ready for review: YES/NO",
    ]:
        assert phrase in text, f"CONCISE_REPORTING_RULES.md must contain: {phrase}"


def test_concise_reporting_doc_unavailable_tools():
    text = CONCISE_REPORTING_DOC.read_text(encoding="utf-8")
    assert "unavailable" in text.lower(), (
        "CONCISE_REPORTING_RULES.md must address unavailable security tools"
    )
    assert "passed" in text.lower(), (
        "CONCISE_REPORTING_RULES.md must prohibit reporting unavailable tools as passed"
    )


# --- 4. Reusable prompt-blocks doc content ---

def test_reusable_blocks_standard_blocks():
    text = REUSABLE_BLOCKS_DOC.read_text(encoding="utf-8")
    for block in [
        "Standard Preflight Block",
        "Standard Security Check Block",
        "Standard Validation Block",
        "Standard Final Report Block",
        "Standard Safety Boundary Block",
        "Standard Generated Artifact Block",
        "Standard Stop/Escalation Block",
    ]:
        assert block in text, f"REUSABLE_WP_PROMPT_BLOCKS.md must define: {block}"


def test_reusable_blocks_required_per_wp_fields():
    text = REUSABLE_BLOCKS_DOC.read_text(encoding="utf-8")
    for phrase in [
        "previous merge commit",
        "forbidden scope",
        "acceptance",
        "failure criteria",
    ]:
        assert phrase.lower() in text.lower(), (
            f"REUSABLE_WP_PROMPT_BLOCKS.md must list required per-WP field: {phrase}"
        )


# --- 5. Existing workflow docs reference new docs ---

def test_agents_md_references_token_efficiency():
    text = AGENTS_MD.read_text(encoding="utf-8")
    assert "TOKEN_EFFICIENCY_OPERATING_MODEL" in text, (
        "AGENTS.md must reference TOKEN_EFFICIENCY_OPERATING_MODEL"
    )


def test_codex_start_here_references_token_efficiency():
    text = CODEX_START_HERE.read_text(encoding="utf-8")
    assert "TOKEN_EFFICIENCY_OPERATING_MODEL" in text, (
        "CODEX_START_HERE.md must reference TOKEN_EFFICIENCY_OPERATING_MODEL"
    )


def test_codex_readme_references_new_docs():
    text = CODEX_README.read_text(encoding="utf-8")
    for doc in [
        "TOKEN_EFFICIENCY_OPERATING_MODEL",
        "CONCISE_REPORTING_RULES",
        "REUSABLE_WP_PROMPT_BLOCKS",
    ]:
        assert doc in text, f"docs/ai/codex/README.md must reference: {doc}"


def test_codex_exec_guidelines_references_token_efficiency():
    text = CODEX_EXEC_GUIDELINES.read_text(encoding="utf-8")
    assert "TOKEN_EFFICIENCY_OPERATING_MODEL" in text, (
        "docs/codex_execution_guidelines.md must reference TOKEN_EFFICIENCY_OPERATING_MODEL"
    )


def test_work_package_template_references_reusable_blocks():
    text = WORK_PACKAGE_TEMPLATE.read_text(encoding="utf-8")
    assert "REUSABLE_WP_PROMPT_BLOCKS" in text, (
        "docs/work_package_template.md must reference REUSABLE_WP_PROMPT_BLOCKS"
    )


# --- 6. PR template retains existing checks and adds concise-reporting checks ---

def test_pr_template_existing_checks_preserved():
    text = PR_TEMPLATE.read_text(encoding="utf-8")
    for phrase in [
        "Full WP final report posted as PR comment",
        "PR body is not the only final report",
        "Full pytest passed after final commit",
        "Generated Artifact Guard passed after final commit",
        "Ready for review: YES/NO stated",
    ]:
        assert phrase in text, f".github/pull_request_template.md must retain: {phrase}"


def test_pr_template_concise_reporting_checks():
    text = PR_TEMPLATE.read_text(encoding="utf-8")
    for phrase in [
        "Validation summary includes exact commands and result counts",
        "UNAVAILABLE/SKIPPED",
        "CONCISE_REPORTING_RULES",
    ]:
        assert phrase in text, f".github/pull_request_template.md must contain: {phrase}"


# --- 7. Repo-truth index includes all new docs ---

def test_repo_truth_index_includes_new_docs():
    text = REPO_TRUTH_INDEX.read_text(encoding="utf-8")
    for doc in [
        "TOKEN_EFFICIENCY_OPERATING_MODEL",
        "CONCISE_REPORTING_RULES",
        "REUSABLE_WP_PROMPT_BLOCKS",
    ]:
        assert doc in text, f"docs/repo_truth_index.md must index: {doc}"


# --- 7b. Repo-truth index Authority Hierarchy has no duplicate numeric prefixes ---

def test_repo_truth_index_no_duplicate_numbers():
    import re
    text = REPO_TRUTH_INDEX.read_text(encoding="utf-8")
    # Extract all lines that start a numbered list entry (e.g. "26. `...`")
    numbers = re.findall(r"^\s*(\d+)\.", text, re.MULTILINE)
    numbers = [int(n) for n in numbers]
    assert len(numbers) == len(set(numbers)), (
        f"docs/repo_truth_index.md Authority Hierarchy has duplicate numeric prefixes: "
        f"{[n for n in numbers if numbers.count(n) > 1]}"
    )


# --- 8. No runtime/helper implementation paths added ---

def test_no_token_tools_added():
    for pattern in ["tools/token", "tools/diff_summary", "tools/code_index"]:
        matches = list(REPO_ROOT.glob(pattern + "*"))
        assert not matches, f"Forbidden implementation path must not exist: {pattern}*"


def test_no_agent_runtime_dirs():
    for dirname in ["src/agents", "src/agent_layer", "tools/hermes", "agent_runtime", "agent_memory"]:
        path = REPO_ROOT / dirname
        assert not path.exists(), f"Forbidden directory must not exist: {dirname}"


# --- 9. Dependency files do not add forbidden dependencies ---

def _get_dependency_files():
    files = []
    for name in ["requirements.txt", "requirements-dev.txt", "pyproject.toml", "setup.cfg", "setup.py", "Pipfile"]:
        p = REPO_ROOT / name
        if p.exists():
            files.append(p)
    return files


def test_no_forbidden_dependencies():
    forbidden = ["rtk", "openai", "anthropic", "langchain", "hermes", "token-savior", "code-review-graph"]
    for dep_file in _get_dependency_files():
        text = dep_file.read_text(encoding="utf-8").lower()
        for term in forbidden:
            assert term not in text, (
                f"Dependency file {dep_file.name} must not add forbidden dependency: {term}"
            )
