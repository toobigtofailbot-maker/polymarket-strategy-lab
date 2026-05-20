from __future__ import annotations

import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

AI_POLICY_DOC = ROOT / "docs" / "ai_agent_integration_policy.md"
HERMES_BOUNDARY_DOC = ROOT / "docs" / "hermes_readonly_boundary.md"
AGENT_REGISTRY_DOC = ROOT / "docs" / "agent_model_registry.md"
AGENTS_DOC = ROOT / "AGENTS.md"

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

FORBIDDEN_RUNTIME_PATHS = (
    "src/agents",
    "src/agent_layer",
    "tools/agents",
    "tools/hermes",
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


def test_required_ai_agent_boundary_docs_exist() -> None:
    for path in (AI_POLICY_DOC, HERMES_BOUNDARY_DOC, AGENT_REGISTRY_DOC):
        assert path.is_file(), f"missing {path.relative_to(ROOT)}"


def test_policy_docs_contain_required_status_phrases() -> None:
    combined = f"{_read(AI_POLICY_DOC)}\n{_read(HERMES_BOUNDARY_DOC)}\n{_read(AGENT_REGISTRY_DOC)}"

    for expected in (
        "POLICY_ONLY_NOT_IMPLEMENTED",
        "NOT_INSTALLED_NOT_RUNTIME_DEPENDENCY",
        "FORBIDDEN",
        "EXCLUDED_FOR_NOW",
    ):
        assert expected in combined


def test_policy_docs_document_allowed_advisory_capabilities() -> None:
    combined = f"{_read(AI_POLICY_DOC)}\n{_read(AGENT_REGISTRY_DOC)}".lower()

    for expected in (
        "read-only analysis",
        "performance review",
        "market research",
        "strategy suggestion",
        "codex / wp support",
    ):
        assert expected in combined


def test_policy_docs_document_forbidden_agent_capabilities() -> None:
    combined = f"{_read(AI_POLICY_DOC)}\n{_read(HERMES_BOUNDARY_DOC)}".lower()

    for expected in (
        "autonomous order placement",
        "autonomous order cancellation",
        "autonomous parameter application",
        "agent-controlled credentials",
        "agent-controlled execution",
        "scheduler or bot loop",
    ):
        assert expected in combined


def test_dependency_files_do_not_add_ai_agent_runtime_dependencies() -> None:
    dependency_files = [
        ROOT / tracked
        for tracked in _git_ls_files()
        if Path(tracked).name in DEPENDENCY_FILE_NAMES
    ]

    for path in dependency_files:
        text = _read(path).lower()
        for term in FORBIDDEN_AGENT_DEPENDENCY_TERMS:
            assert term not in text, f"{term} found in {path.relative_to(ROOT)}"


def test_no_runtime_agent_implementation_paths_are_tracked_or_present() -> None:
    tracked = _git_ls_files()
    for forbidden in FORBIDDEN_RUNTIME_PATHS:
        assert not any(path == forbidden or path.startswith(f"{forbidden}/") for path in tracked)
        assert not (ROOT / forbidden).exists(), f"unexpected runtime path exists: {forbidden}"


def test_accepted_agent_suggestions_require_human_repo_truth_wp_flow() -> None:
    combined = f"{_read(AGENTS_DOC)}\n{_read(AI_POLICY_DOC)}\n{_read(AGENT_REGISTRY_DOC)}".lower()

    for expected in (
        "human review",
        "approved config changes",
        "normal codex work package",
        "repo-truth workflow",
    ):
        assert expected in combined


def test_repo_truth_index_records_ai_agent_boundary_docs() -> None:
    index = _read(ROOT / "docs" / "repo_truth_index.md")

    for expected in (
        "docs/ai_agent_integration_policy.md",
        "docs/hermes_readonly_boundary.md",
        "docs/agent_model_registry.md",
    ):
        assert expected in index

