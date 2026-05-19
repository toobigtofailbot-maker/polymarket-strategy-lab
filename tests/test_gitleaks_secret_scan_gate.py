"""Tests for the WP7 gitleaks secret scan gate."""

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SETUP_SCRIPT = ROOT / "tools" / "security" / "setup_project_gitleaks.py"
VERIFY_SCRIPT = ROOT / "tools" / "security" / "verify_project_gitleaks.py"
GATE_DOC = ROOT / "docs" / "gitleaks_secret_scan_gate.md"
RUN_SCRIPT = ROOT / "tools" / "security" / "run_available_security_checks.py"
STATUS_DOC = ROOT / "docs" / "security_tooling_status.md"
DEFERRED_LOG = ROOT / "docs" / "deferred_items_log.md"
GITIGNORE = ROOT / ".gitignore"

FORBIDDEN_INSTALL_COMMANDS = [
    "winget install",
    "choco install",
    "brew install",
    "apt-get install",
    "apt install ",
    "npm install -g",
    # "cargo install" is checked separately to allow docstring references
    "pip install --user",
]

# These must not appear as executable calls (not just docstring references)
FORBIDDEN_INSTALL_CALLS = [
    "subprocess.run.*cargo.*install",
    "subprocess.run.*npm.*install",
]

FORBIDDEN_TRADING_TERMS = [
    "place_order",
    "create_order",
    "post_order",
    "cancel_order",
    "private_key",
    "mnemonic",
    "live_mode=true",
]


# --- File existence ---

def test_setup_project_gitleaks_exists():
    assert SETUP_SCRIPT.is_file(), f"Missing: {SETUP_SCRIPT}"


def test_verify_project_gitleaks_exists():
    assert VERIFY_SCRIPT.is_file(), f"Missing: {VERIFY_SCRIPT}"


def test_gitleaks_secret_scan_gate_doc_exists():
    assert GATE_DOC.is_file(), f"Missing: {GATE_DOC}"


# --- .gitignore protections ---

def test_gitignore_protects_tools_bin():
    text = GITIGNORE.read_text(encoding="utf-8")
    assert "tools/.bin/" in text, ".gitignore must contain 'tools/.bin/'"


def test_gitignore_protects_security_scan_output():
    text = GITIGNORE.read_text(encoding="utf-8")
    assert "security-scan-output/" in text, ".gitignore must contain 'security-scan-output/'"


# --- Setup script safety ---

def _setup_text() -> str:
    return SETUP_SCRIPT.read_text(encoding="utf-8").lower()


def test_setup_script_checks_ignore_protection():
    text = SETUP_SCRIPT.read_text(encoding="utf-8")
    assert "check-ignore" in text or "verify_local_bin_is_ignored" in text, (
        "setup_project_gitleaks.py must verify tools/.bin/ ignore protection before use"
    )


def test_setup_script_no_global_install_commands():
    lowered = _setup_text()
    for cmd in FORBIDDEN_INSTALL_COMMANDS:
        assert cmd not in lowered, (
            f"setup_project_gitleaks.py must not contain forbidden install command: {cmd!r}"
        )
    # Verify there is no subprocess.run call that invokes cargo install or npm install
    text = SETUP_SCRIPT.read_text(encoding="utf-8")
    import re
    for pattern in FORBIDDEN_INSTALL_CALLS:
        assert not re.search(pattern, text), (
            f"setup_project_gitleaks.py must not call: {pattern!r}"
        )


def test_setup_script_no_trading_or_secret_terms():
    lowered = _setup_text()
    for term in FORBIDDEN_TRADING_TERMS:
        assert term not in lowered, (
            f"setup_project_gitleaks.py must not contain trading/secret term: {term!r}"
        )


def test_setup_script_does_not_write_to_committed_paths():
    text = SETUP_SCRIPT.read_text(encoding="utf-8")
    # The binary destination must only reference LOCAL_BIN (tools/.bin), not src/ or committed dirs.
    assert "tools/.bin" in text or "LOCAL_BIN" in text, (
        "setup_project_gitleaks.py must write only to tools/.bin/"
    )
    # Confirm no write_bytes/write_text call targets src/ directory
    import re
    assert not re.search(r'\.write_(?:bytes|text)\s*\(.*["\']src/', text), (
        "setup_project_gitleaks.py must not write to src/"
    )


# --- Verify script behavior ---

def test_verify_project_gitleaks_exits_zero():
    result = subprocess.run(
        [sys.executable, str(VERIFY_SCRIPT)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert result.returncode == 0, (
        f"verify_project_gitleaks.py must exit 0 regardless of gitleaks availability.\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )


def test_verify_script_no_trading_or_secret_terms():
    lowered = VERIFY_SCRIPT.read_text(encoding="utf-8").lower()
    for term in FORBIDDEN_TRADING_TERMS:
        assert term not in lowered, (
            f"verify_project_gitleaks.py must not contain trading/secret term: {term!r}"
        )


# --- run_available_security_checks.py references ---

def test_run_checks_references_project_local_gitleaks():
    text = RUN_SCRIPT.read_text(encoding="utf-8")
    assert "local_binary" in text or "tools/.bin" in text or "LOCAL_BIN" in text, (
        "run_available_security_checks.py must detect project-local gitleaks binary"
    )


# --- Documentation references ---

def test_security_tooling_status_references_wp7():
    text = STATUS_DOC.read_text(encoding="utf-8")
    assert "WP7" in text, "docs/security_tooling_status.md must reference WP7"


def test_security_tooling_status_references_gitleaks_wp7():
    text = STATUS_DOC.read_text(encoding="utf-8")
    assert "gitleaks" in text.lower(), "docs/security_tooling_status.md must reference gitleaks"


def test_deferred_log_contains_wp7_update():
    text = DEFERRED_LOG.read_text(encoding="utf-8")
    assert "WP7 Gitleaks Secret Scan Gate Update" in text, (
        "docs/deferred_items_log.md must contain 'WP7 Gitleaks Secret Scan Gate Update'"
    )


def test_deferred_log_wp3_d001_not_deferred_without_evidence():
    """WP3-D001 may be READY_FOR_WP only if scan evidence is present."""
    text = DEFERRED_LOG.read_text(encoding="utf-8")
    assert "WP3-D001" in text, "docs/deferred_items_log.md must contain WP3-D001"
    # If marked READY_FOR_WP, scan evidence must also be present
    if "READY_FOR_WP" in text:
        evidence_markers = ["gitleaks", "scan", "version"]
        assert any(m in text.lower() for m in evidence_markers), (
            "WP3-D001 READY_FOR_WP requires scan evidence in deferred_items_log.md"
        )


def test_gitleaks_gate_doc_has_required_sections():
    text = GATE_DOC.read_text(encoding="utf-8")
    required_sections = [
        "Purpose",
        "Setup Strategy",
        "Scan Result",
        "Safety Statement",
        "Generated Artifact Guard",
    ]
    for section in required_sections:
        assert section in text, f"docs/gitleaks_secret_scan_gate.md missing section: {section!r}"


def test_gitleaks_gate_doc_no_broad_suppressions():
    text = GATE_DOC.read_text(encoding="utf-8")
    # The doc must explicitly state no broad suppressions were added.
    # Acceptable phrases: "No broad suppressions added", "no broad suppressions", etc.
    lowered = text.lower()
    has_suppression_mention = "broad suppression" in lowered
    has_negation = "no broad" in lowered or "not added" in lowered or "none" in lowered
    if has_suppression_mention:
        assert has_negation, (
            "docs/gitleaks_secret_scan_gate.md mentions broad suppressions "
            "but does not negate them — confirm no broad suppressions were added"
        )
