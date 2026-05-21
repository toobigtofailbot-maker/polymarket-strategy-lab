from __future__ import annotations

import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

SCHEMA_DOC = ROOT / "docs" / "agent_context_export_schema.md"
REPO_TRUTH_INDEX = ROOT / "docs" / "repo_truth_index.md"

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

FORBIDDEN_UNAPPROVED_RUNTIME_OR_EXPORTER_PATHS = (
    "src/agents",
    "src/agent_layer",
    "tools/agents",
    "tools/hermes",
    "tools/agent_context_export",
    "tools/agent_context_export.py",
    "agent_reports",
    "schemas/agent_context",
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


def test_required_agent_context_export_schema_doc_exists() -> None:
    assert SCHEMA_DOC.is_file(), f"missing {SCHEMA_DOC.relative_to(ROOT)}"


def test_schema_doc_contains_required_status_phrases() -> None:
    text = _read(SCHEMA_DOC)

    for expected in (
        "POLICY_SCHEMA_DEFINED_EXPORTER_IMPLEMENTED_LOCAL_OFFLINE_READ_ONLY",
        "LOCAL_OFFLINE_READ_ONLY_EXPORTER",
        "NOT_INSTALLED_NOT_RUNTIME_DEPENDENCY",
        "FORBIDDEN",
        "EXCLUDED_FOR_NOW",
    ):
        assert expected in text


def test_schema_doc_contains_required_top_level_fields() -> None:
    text = _read(SCHEMA_DOC)

    for expected in (
        "schema_version",
        "export_created_at_utc",
        "export_mode",
        "producer",
        "source_commit",
        "repo_truth_summary",
        "included_local_artifacts",
        "data_quality_summary",
        "safety_boundaries",
        "deferred_items",
        "allowed_agent_uses",
        "forbidden_agent_uses",
        "redaction_policy",
        "staleness_policy",
        "human_review_requirements",
    ):
        assert expected in text


def test_schema_doc_contains_required_forbidden_use_statements() -> None:
    text = _read(SCHEMA_DOC).lower()

    for expected in (
        "credentials",
        "account connection",
        "private endpoints",
        "order placement",
        "order cancellation",
        "signing",
        "execution",
        "scheduler",
        "bot loop",
        "network scanning",
        "autonomous parameter application",
    ):
        assert expected in text


def test_schema_doc_contains_required_provenance_and_safety_statements() -> None:
    text = _read(SCHEMA_DOC).lower()

    for expected in (
        "local artifacts only",
        "repo-approved local tools only",
        "repo truth overrides exported context",
        "generated artifacts must remain under ignored `local_data/`",
        "no secrets",
        "account data",
        "advisory and untrusted until human review",
    ):
        assert expected in text


def test_no_unapproved_runtime_or_exporter_implementation_paths_are_tracked_or_present() -> None:
    tracked = _git_ls_files()
    for forbidden in FORBIDDEN_UNAPPROVED_RUNTIME_OR_EXPORTER_PATHS:
        assert not any(path == forbidden or path.startswith(f"{forbidden}/") for path in tracked)
        assert not (ROOT / forbidden).exists(), f"unexpected path exists: {forbidden}"


def test_dependency_files_do_not_add_ai_or_agent_runtime_dependencies() -> None:
    dependency_files = [
        ROOT / tracked
        for tracked in _git_ls_files()
        if Path(tracked).name in DEPENDENCY_FILE_NAMES
    ]

    for path in dependency_files:
        text = _read(path).lower()
        for term in FORBIDDEN_AGENT_DEPENDENCY_TERMS:
            assert term not in text, f"{term} found in {path.relative_to(ROOT)}"


def test_repo_truth_index_records_agent_context_export_schema_doc() -> None:
    index = _read(REPO_TRUTH_INDEX)

    assert "docs/agent_context_export_schema.md" in index
