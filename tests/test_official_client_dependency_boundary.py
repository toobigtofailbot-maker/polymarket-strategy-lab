from __future__ import annotations

import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

DECISION_DOC = ROOT / "docs" / "official_python_client_dependency_decision.md"
BOUNDARY_DOC = ROOT / "docs" / "polymarket_client_boundary_review.md"

OFFICIAL_CLIENT_TERMS = (
    "py-clob-client",
    "py-clob-client-v2",
    "py_clob_client",
    "py_clob_client_v2",
)

FORBIDDEN_SRC_IMPORTS = (
    "py_clob_client",
    "py_clob_client_v2",
)

FORBIDDEN_SRC_TERMS = (
    "PRIVATE_KEY",
    "CLOB_API_KEY",
    "CLOB_SECRET",
    "CLOB_PASS_PHRASE",
    "mnemonic",
    "create_or_derive_api_key",
    "create_and_post_order",
    "create_and_post_market_order",
    "cancel_order",
    "sign_order",
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
    )
    return [line.strip().replace("\\", "/") for line in result.stdout.splitlines() if line.strip()]


def test_official_client_decision_docs_exist_and_record_required_terms() -> None:
    assert DECISION_DOC.is_file()
    assert BOUNDARY_DOC.is_file()

    combined = f"{_read(DECISION_DOC)}\n{_read(BOUNDARY_DOC)}".lower()

    for expected in (
        "py-clob-client-v2",
        "py-clob-client",
        "archived",
        "avoid",
        "not_installed",
        "not installed",
        "no authenticated client",
        "no private keys",
        "no credentials",
        "no order placement",
        "no signing",
    ):
        assert expected in combined


def test_pyproject_does_not_include_official_client_dependency() -> None:
    pyproject = _read(ROOT / "pyproject.toml")

    for term in OFFICIAL_CLIENT_TERMS:
        assert term not in pyproject


def test_no_requirements_or_lock_file_adds_official_client() -> None:
    dependency_file_names = {
        "requirements.txt",
        "requirements-dev.txt",
        "requirements.lock",
        "poetry.lock",
        "uv.lock",
        "pdm.lock",
        "Pipfile.lock",
        "package-lock.json",
    }
    dependency_files = [
        ROOT / tracked
        for tracked in _git_ls_files()
        if Path(tracked).name in dependency_file_names
    ]

    for path in dependency_files:
        text = _read(path)
        for term in OFFICIAL_CLIENT_TERMS:
            assert term not in text, f"{term} found in {path.relative_to(ROOT)}"


def test_src_does_not_import_official_client() -> None:
    import_pattern = re.compile(
        r"^\s*(?:from|import)\s+(" + "|".join(re.escape(term) for term in FORBIDDEN_SRC_IMPORTS) + r")\b",
        re.MULTILINE,
    )

    for path in (ROOT / "src").rglob("*.py"):
        text = _read(path)
        assert not import_pattern.search(text), f"official client import found in {path.relative_to(ROOT)}"


# Files that use certain forbidden terms defensively (as rejection patterns, not credential use).
# Each entry maps a relative file path to the set of terms it is exempt from.
# Any file listed here must be explicitly reviewed and documented.
FORBIDDEN_TERMS_FILE_EXEMPTIONS: dict[str, set[str]] = {
    # WP56: resolution_ambiguity_labels.py uses "mnemonic" in _FORBIDDEN_REF_SUBSTRINGS
    # to REJECT source artifact refs that contain mnemonic-like strings. This is a
    # defensive rejection pattern, not a credential or key-derivation path.
    "src/data_layer/resolution_ambiguity_labels.py": {"mnemonic"},
}


def test_src_does_not_include_forbidden_official_client_auth_or_order_terms() -> None:
    for path in (ROOT / "src").rglob("*.py"):
        text = _read(path)
        rel = path.relative_to(ROOT).as_posix()
        exempted = FORBIDDEN_TERMS_FILE_EXEMPTIONS.get(rel, set())
        for term in FORBIDDEN_SRC_TERMS:
            if term in exempted:
                continue
            assert not re.search(rf"\b{re.escape(term)}\b", text), (
                f"{term} found in {path.relative_to(ROOT)}"
            )


def test_reuse_docs_mark_old_client_avoid_and_v2_candidate_only() -> None:
    source_registry = _read(ROOT / "docs" / "source_repo_registry.md")
    reuse_matrix = _read(ROOT / "docs" / "repo_reuse_decision_matrix.md")
    reuse_strategy = _read(ROOT / "docs" / "repo_reuse_strategy.md")
    combined = f"{source_registry}\n{reuse_matrix}\n{reuse_strategy}"

    assert "Polymarket/py-clob-client" in combined
    assert "DO_NOT_USE_ARCHIVED" in combined
    assert "AVOID" in combined or "Avoid" in combined
    assert "Polymarket/py-clob-client-v2" in combined
    assert "CANDIDATE_FOR_FUTURE_DEV_ONLY_EVALUATION" in combined
    assert "NOT_APPROVED_IN_WP14" in combined
    assert "FORBIDDEN_UNTIL_EXPLICIT_WP" in combined


def test_project_status_records_candidate_only_not_installed_status() -> None:
    status = _read(ROOT / "docs" / "project_status.md")

    assert "Official Python client status: SANDBOX_CANDIDATE_ONLY_NOT_PROJECT_DEPENDENCY" in status
    assert "OFFICIAL_CLIENT_SANDBOX_DEV_ONLY" in status
    assert "Official client runtime dependency status: NOT_STARTED_FOR_OFFICIAL_CLIENT_RUNTIME" in status
    assert "Authenticated client status: FORBIDDEN_UNTIL_APPROVED_WP" in status


def test_no_generated_artifacts_local_outputs_or_external_source_are_tracked() -> None:
    tracked = _git_ls_files()
    forbidden_prefixes = (
        ".venv-security/",
        "tools/.bin/",
        "tools/security/.cache/",
        "security-scan-output/",
        "local_data/",
    )
    forbidden_names = {
        "requirements.txt",
        "requirements-dev.txt",
        "requirements.lock",
        "poetry.lock",
        "uv.lock",
        "pdm.lock",
        "Pipfile.lock",
        "package-lock.json",
        ".gitmodules",
    }

    assert not any(path.startswith(forbidden_prefixes) for path in tracked)
    assert not any(Path(path).name in forbidden_names for path in tracked if path != "pyproject.toml")
