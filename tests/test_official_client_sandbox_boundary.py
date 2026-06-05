from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SANDBOX = ROOT / "tools" / "polymarket" / "official_client_sandbox"
AUDIT_DOC = ROOT / "docs" / "official_client_readonly_sandbox_audit.md"
README = SANDBOX / "README.md"
SETUP = SANDBOX / "setup_sandbox.py"
VERIFY = SANDBOX / "verify_sandbox.py"
INSPECT = SANDBOX / "inspect_package.py"
PROBE = SANDBOX / "readonly_public_probe.py"
GITIGNORE = ROOT / ".gitignore"

OFFICIAL_CLIENT_TERMS = (
    "py-clob-client",
    "py-clob-client-v2",
    "py_clob_client",
    "py_clob_client_v2",
)

DEPENDENCY_FILE_NAMES = {
    "requirements.txt",
    "requirements-dev.txt",
    "requirements.lock",
    "poetry.lock",
    "uv.lock",
    "pdm.lock",
    "Pipfile.lock",
    "package-lock.json",
}

FORBIDDEN_SRC_IMPORTS = ("py_clob_client", "py_clob_client_v2")
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

FORBIDDEN_GLOBAL_INSTALL_TEXT = (
    "winget install",
    "choco install",
    "brew install",
    "apt install",
    "apt-get install",
    "npm install -g",
    "cargo install",
    "pip install --user",
    "global pip install",
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


def test_sandbox_required_files_exist() -> None:
    for path in (AUDIT_DOC, README, SETUP, VERIFY, INSPECT, PROBE):
        assert path.is_file(), f"Missing official-client sandbox file: {path.relative_to(ROOT)}"


def test_gitignore_protects_sandbox_artifacts() -> None:
    text = _read(GITIGNORE)
    for expected in (
        ".venv-official-client/",
        "official-client-sandbox-output/",
        "local_data/polymarket/official_client_sandbox/",
    ):
        assert expected in text


def test_pyproject_does_not_include_official_client_dependency() -> None:
    pyproject = _read(ROOT / "pyproject.toml")
    for term in OFFICIAL_CLIENT_TERMS:
        assert term not in pyproject


def test_no_tracked_dependency_or_lock_file_adds_official_client_terms() -> None:
    dependency_files = [
        ROOT / tracked
        for tracked in _git_ls_files()
        if Path(tracked).name in DEPENDENCY_FILE_NAMES
    ]
    for path in dependency_files:
        text = _read(path)
        for term in OFFICIAL_CLIENT_TERMS:
            assert term not in text, f"{term} found in {path.relative_to(ROOT)}"


def test_no_src_official_client_imports() -> None:
    pattern = re.compile(
        r"^\s*(?:from|import)\s+(" + "|".join(re.escape(term) for term in FORBIDDEN_SRC_IMPORTS) + r")\b",
        re.MULTILINE,
    )
    for path in (ROOT / "src").rglob("*.py"):
        text = _read(path)
        assert not pattern.search(text), f"official client import found in {path.relative_to(ROOT)}"


# Files that use certain forbidden terms defensively (as rejection patterns, not credential use).
# Each entry maps a relative file path to the set of terms it is exempt from.
# Any file listed here must be explicitly reviewed and documented.
FORBIDDEN_TERMS_FILE_EXEMPTIONS: dict[str, set[str]] = {
    # WP56: resolution_ambiguity_labels.py uses "mnemonic" in _FORBIDDEN_REF_SUBSTRINGS
    # to REJECT source artifact refs that contain mnemonic-like strings. This is a
    # defensive rejection pattern, not a credential or key-derivation path.
    "src/data_layer/resolution_ambiguity_labels.py": {"mnemonic"},
}


def test_no_src_forbidden_auth_or_order_terms() -> None:
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


def test_setup_script_verifies_ignore_protection_before_sandbox_use() -> None:
    text = _read(SETUP)
    assert "require_ignored" in text
    assert ".venv-official-client" not in text or "VENV_DIR" in text
    assert "OUTPUT_DIR" in text
    assert "LOCAL_OUTPUT_DIR" in text


def test_setup_script_does_not_contain_global_or_system_install_commands() -> None:
    lowered = _read(SETUP).lower()
    for forbidden in FORBIDDEN_GLOBAL_INSTALL_TEXT:
        assert forbidden not in lowered, f"setup script contains forbidden install text: {forbidden}"


def test_verify_script_exits_zero_when_package_unavailable() -> None:
    result = subprocess.run(
        [sys.executable, str(VERIFY)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "no installation" in result.stdout.lower()


def test_readonly_probe_requires_allow_network_and_default_is_safe() -> None:
    text = _read(PROBE)
    assert "--allow-network" in text
    assert "if not args.allow_network" in text

    result = subprocess.run(
        [sys.executable, str(PROBE)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "no network call" in result.stdout.lower()
    assert "package import" in result.stdout.lower()


def test_readonly_probe_contains_no_credential_loading_or_authenticated_setup() -> None:
    lowered = _read(PROBE).lower()
    for forbidden in (
        "dotenv",
        "load_dotenv",
        "os.environ",
        "private_key",
        "clob_api_key",
        "clob_secret",
        "clob_pass_phrase",
        "create_or_derive_api_key",
        "api_creds",
    ):
        assert forbidden not in lowered, f"readonly probe contains forbidden credential/auth text: {forbidden}"


def test_docs_state_no_runtime_integration_or_live_trading() -> None:
    combined = f"{_read(AUDIT_DOC)}\n{_read(README)}".lower()
    for expected in (
        "does not authorize runtime use",
        "does not import official client packages under `src/`",
        "existing stdlib public adapter remains the active runtime path",
        "live-trading",
        "no authenticated client",
        "no credentials",
        "no signing",
        "no order placement",
        "no order cancellation",
    ):
        assert expected in combined


def test_official_client_import_strings_only_in_allowed_paths() -> None:
    allowed_prefixes = (
        "docs/",
        "tests/",
        "tools/polymarket/official_client_sandbox/",
    )
    offenders: list[str] = []
    for tracked in _git_ls_files():
        path = ROOT / tracked
        if not path.is_file():
            continue
        text = _read(path)
        if any(term in text for term in ("py_clob_client", "py_clob_client_v2")):
            normalized = tracked.replace("\\", "/")
            if not normalized.startswith(allowed_prefixes):
                offenders.append(normalized)
    assert not offenders
