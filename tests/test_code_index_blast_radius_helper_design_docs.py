"""
WP33: Tests enforcing the code index / blast-radius helper design document and
repo-truth cross-references.
"""

import pathlib
import re

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
DESIGN_DOC = REPO_ROOT / "docs/ai/codex/CODE_INDEX_BLAST_RADIUS_HELPER_DESIGN.md"
REPO_TRUTH_INDEX = REPO_ROOT / "docs/repo_truth_index.md"


def _read(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8")


def test_required_design_doc_exists():
    assert DESIGN_DOC.exists(), f"Missing: {DESIGN_DOC}"


def test_required_status_phrases_exist():
    content = _read(DESIGN_DOC)
    for phrase in [
        "DESIGN_ONLY",
        "NOT_IMPLEMENTED",
        "Claude Code and Codex",
        "NO_RUNTIME_CHANGE",
        "NO_TOOL_IMPLEMENTATION",
        "NO_DEPENDENCY_CHANGE",
        "NO_NETWORK",
        "NO_VALIDATION_WEAKENING",
        "NO_PROTECTED_BOUNDARY_CHANGE",
    ]:
        assert phrase in content


def test_intended_future_modes_exist():
    content = _read(DESIGN_DOC)
    for phrase in [
        "On-demand scan mode",
        "Snapshot/index file mode",
        "Query mode",
        "Design-only mode",
        "first implementation should prefer on-demand scan",
    ]:
        assert phrase in content


def test_intended_cli_shape_exists():
    content = _read(DESIGN_DOC)
    for phrase in [
        "tools/git/code_blast_radius.py",
        "--changed-file",
        "--changed-prefix",
        "--package-class",
        "--include-tests",
        "--include-docs",
        "--include-protected-boundaries",
        "--format text|json",
        "--output",
        "--max-results",
        "--fail-on-protected-hit",
        "--repo-root",
    ]:
        assert phrase in content


def test_relationship_model_exists():
    content = _read(DESIGN_DOC)
    for phrase in [
        "Direct references",
        "Naming heuristics",
        "Repo-truth relationships",
        "Protected/sensitive relationships",
        "confidence high/medium/low",
    ]:
        assert phrase in content


def test_package_class_awareness_warnings_exist():
    content = _read(DESIGN_DOC)
    assert "Package-Class Awareness" in content
    assert "package-class warnings" in content


def test_stale_index_model_exists():
    content = _read(DESIGN_DOC)
    assert "Stale-Index Model" in content
    assert "Source commit SHA differs from current `HEAD`" in content


def test_excluded_paths_and_sensitive_content_model_exists():
    content = _read(DESIGN_DOC)
    assert "Excluded Paths and Sensitive-Content Model" in content
    assert "`.env` values" in content
    assert "private keys" in content


def test_validation_preservation_rules_exist():
    content = _read(DESIGN_DOC)
    assert "Validation-Preservation Rules" in content
    assert "Full pytest" in content
    assert "Remote Main Sync Gate" in content
    assert "The helper cannot authorize merge-ready status by itself" in content


def test_future_implementation_test_plan_exists():
    content = _read(DESIGN_DOC)
    assert "Future Implementation Test Plan" in content
    assert "No network calls or external service calls" in content
    assert "No dependency additions" in content


def test_open_design_questions_and_recommended_next_wp_exist():
    content = _read(DESIGN_DOC)
    assert "Open Design Questions" in content
    assert "Recommended Next WP" in content
    assert "WP34" in content


def test_repo_truth_index_contains_design_doc():
    content = _read(REPO_TRUTH_INDEX)
    assert "CODE_INDEX_BLAST_RADIUS_HELPER_DESIGN.md" in content


def test_repo_truth_index_numeric_prefixes_unique_and_sequential():
    content = _read(REPO_TRUTH_INDEX)
    numbers = [int(n) for n in re.findall(r"^(\d+)\. ", content, re.MULTILINE)]
    assert len(numbers) == len(set(numbers)), f"Duplicate numeric prefixes: {numbers}"
    assert numbers == list(range(1, len(numbers) + 1)), (
        f"Authority Hierarchy numbering is not sequential. Got: {numbers}"
    )


def test_no_code_index_or_blast_radius_implementation_paths_exist():
    forbidden_paths = [
        REPO_ROOT / "tools/git/code_blast_radius.py",
        REPO_ROOT / "tools/git/code_index.py",
    ]
    for path in forbidden_paths:
        assert not path.exists(), f"Forbidden implementation path exists: {path}"

    forbidden_globs = [
        REPO_ROOT / "tools/code_index*",
        REPO_ROOT / "tools/blast_radius*",
    ]
    for pattern in forbidden_globs:
        matches = list(pattern.parent.glob(pattern.name))
        assert not matches, f"Forbidden implementation paths found: {matches}"


def test_no_tracked_local_data_code_index_path_exists():
    tracked = REPO_ROOT / "local_data/code_index"
    assert not tracked.exists(), f"Forbidden tracked/generated path exists: {tracked}"


def test_dependency_files_do_not_add_forbidden_indexing_packages():
    dependency_files = [
        REPO_ROOT / "pyproject.toml",
        *REPO_ROOT.glob("requirements*.txt"),
    ]
    forbidden = [
        "rtk",
        "openai",
        "anthropic",
        "langchain",
        "hermes",
        "token-savior",
        "code-review-graph",
        "tree-sitter",
    ]
    for path in dependency_files:
        if not path.exists():
            continue
        content = _read(path).lower()
        for package in forbidden:
            assert package not in content, f"Forbidden dependency {package!r} in {path}"
