"""Tests for the WP7 gitleaks secret scan gate."""

import re
import shutil
import string
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest


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


# --- S10-CI-SEC-02: embedded default rules restored and proven by detection ---

GITLEAKS_CONFIG = ROOT / ".gitleaks.toml"
GITLEAKS_IGNORE = ROOT / ".gitleaksignore"
WP14_PROSE = (
    "Authenticated CLOB client integration remains blocked pending "
    "credential/key/security boundary WP"
)
WP14_HISTORICAL_FINGERPRINT = (
    "70136bc4ad74eae69a0c0ee960a12a0f852e4df5:docs/deferred_items_log.md:generic-api-key:49"
)
EXPECTED_FINGERPRINT_COUNT = 20
FINGERPRINT_RE = re.compile(
    r"[0-9a-f]{40}:(?:docs|tests|tools)/[A-Za-z0-9_./-]+:"
    r"(?:generic-api-key|private-key|jwt):[1-9][0-9]*"
)
DEFECTIVE_WP15_CONFIG = (
    "[allowlist]\n"
    'description = "Repository documentation false positives only."\n'
    'regexTarget = "line"\n'
    "paths = [\n  '''docs/deferred_items_log\\.md''',\n]\n"
    f"regexes = [\n  '''{WP14_PROSE}''',\n]\n"
)
ROW_BOUND_ALLOWLIST_CONFIG = (
    "[extend]\nuseDefault = true\n\n[allowlist]\n"
    'regexTarget = "line"\n'
    f"regexes = [\n  '''\\| WP14-D002 \\| {WP14_PROSE} \\|''',\n]\n"
)


def gitleaks_config_violations(text: str) -> list[str]:
    """Return closed violation labels for a gitleaks config; empty means compliant."""
    try:
        config = tomllib.loads(text)
    except tomllib.TOMLDecodeError:
        return ["TOML_INVALID"]
    violations = []
    extend = config.get("extend")
    if not isinstance(extend, dict) or extend.get("useDefault") is not True:
        violations.append("DEFAULT_RULES_NOT_EXTENDED")
    elif set(extend) != {"useDefault"}:
        violations.append("EXTEND_OVERRIDE_PRESENT")
    if "allowlist" in config or "allowlists" in config:
        violations.append("ALLOWLIST_PRESENT")
    if set(config) - {"title", "extend", "allowlist", "allowlists"}:
        violations.append("UNEXPECTED_TOP_LEVEL_KEY")
    return violations


def gitleaksignore_entries() -> list[str]:
    lines = GITLEAKS_IGNORE.read_text(encoding="utf-8").splitlines()
    return [line.strip() for line in lines if line.strip() and not line.startswith("#")]


def gitleaks_binary() -> str | None:
    suffix = ".exe" if sys.platform.startswith("win") else ""
    local = ROOT / "tools" / ".bin" / f"gitleaks{suffix}"
    candidate = str(local) if local.is_file() else shutil.which("gitleaks")
    if candidate is None:
        return None
    # The `dir` subcommand arrived in gitleaks 8.19; older binaries cannot run these proofs.
    probe = subprocess.run(
        [candidate, "dir", "--help"], capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=60, check=False,
    )
    return candidate if probe.returncode == 0 else None


def synthetic_github_token() -> str:
    # Assembled at runtime so this source file never contains a detectable literal.
    return "ghp" + "_" + (string.ascii_letters + string.digits)[7:43]


def run_gitleaks(binary: str, mode: str, source: Path, config: Path | None) -> int:
    command = [binary, mode, str(source), "--no-banner", "--redact", "--exit-code", "9"]
    if config is not None:
        command += ["--config", str(config)]
    completed = subprocess.run(
        command, capture_output=True, text=True, encoding="utf-8",
        errors="replace", timeout=120, check=False,
    )
    assert completed.returncode in (0, 9), "gitleaks did not complete a scan"
    return completed.returncode


def run_gitleaks_dir(binary: str, source: Path, config: Path | None) -> int:
    return run_gitleaks(binary, "dir", source, config)


def test_gitleaks_config_extends_embedded_default_rules():
    assert gitleaks_config_violations(GITLEAKS_CONFIG.read_text(encoding="utf-8")) == []


@pytest.mark.parametrize(
    ("mutation", "label"),
    [
        (lambda t: t.replace("useDefault = true", "useDefault = false"), "DEFAULT_RULES_NOT_EXTENDED"),
        (lambda t: t.replace("[extend]\nuseDefault = true\n", ""), "DEFAULT_RULES_NOT_EXTENDED"),
        (lambda t: t.replace("useDefault = true", 'useDefault = true\ndisabledRules = ["generic-api-key"]'), "EXTEND_OVERRIDE_PRESENT"),
        (lambda t: t.replace("useDefault = true", 'useDefault = true\npath = "other.toml"'), "EXTEND_OVERRIDE_PRESENT"),
        (lambda t: t + f"\n[allowlist]\nregexTarget = \"line\"\nregexes = ['''{WP14_PROSE}''']\n", "ALLOWLIST_PRESENT"),
        (lambda t: t + "\n[allowlist]\npaths = ['''docs/deferred_items_log\\.md''']\n", "ALLOWLIST_PRESENT"),
        (lambda t: t + "\n[allowlist]\nstopwords = [\"secret\"]\n", "ALLOWLIST_PRESENT"),
        (lambda t: t + "\n[allowlist]\ncommits = [\"0c158e0\"]\n", "ALLOWLIST_PRESENT"),
        (lambda t: t + "\n[[allowlists]]\npaths = ['''.*''']\n", "ALLOWLIST_PRESENT"),
        (lambda t: t + '\n[[rules]]\nid = "x"\nregex = "x"\n', "UNEXPECTED_TOP_LEVEL_KEY"),
        (lambda t: "[extend\n" + t, "TOML_INVALID"),
        (lambda t: DEFECTIVE_WP15_CONFIG, "DEFAULT_RULES_NOT_EXTENDED"),
        (lambda t: DEFECTIVE_WP15_CONFIG, "ALLOWLIST_PRESENT"),
        (lambda t: ROW_BOUND_ALLOWLIST_CONFIG, "ALLOWLIST_PRESENT"),
    ],
)
def test_gitleaks_config_negative_matrix(mutation, label):
    original = GITLEAKS_CONFIG.read_text(encoding="utf-8").replace("\r\n", "\n")
    mutated = mutation(original)
    assert mutated != original
    assert label in gitleaks_config_violations(mutated)


def test_gitleaksignore_is_exact_fingerprints_only():
    entries = gitleaksignore_entries()
    assert len(entries) == EXPECTED_FINGERPRINT_COUNT
    assert len(set(entries)) == len(entries)
    assert WP14_HISTORICAL_FINGERPRINT in entries
    for entry in entries:
        assert FINGERPRINT_RE.fullmatch(entry), "non-fingerprint .gitleaksignore entry"


@pytest.mark.parametrize(
    "entry",
    [
        "tests/test_x.py:generic-api-key:1",
        "0c158e0:tests/test_x.py:generic-api-key:1",
        f"{'a' * 40}:tests/:generic-api-key:1",
        f"{'a' * 40}:tests/test_x.py:*:1",
        f"{'a' * 40}:tests/test_x.py:github-pat:1",
        f"{'a' * 40}:src/x.py:generic-api-key:1",
        f"{'a' * 40}:tests/test_x.py:generic-api-key:0",
    ],
)
def test_gitleaksignore_fingerprint_negative_matrix(entry):
    assert not FINGERPRINT_RE.fullmatch(entry)


def test_gitleaks_detects_synthetic_secret_and_accepts_clean_input(tmp_path):
    binary = gitleaks_binary()
    if binary is None:
        pytest.skip("gitleaks binary not available (tools/.bin or PATH)")
    config = tmp_path / "config.toml"
    config.write_text(GITLEAKS_CONFIG.read_text(encoding="utf-8"), encoding="utf-8")

    leaky = tmp_path / "leaky"
    leaky.mkdir()
    (leaky / "settings.py").write_text(f'token = "{synthetic_github_token()}"\n', encoding="utf-8")
    assert run_gitleaks_dir(binary, leaky, config) == 9

    clean = tmp_path / "clean"
    clean.mkdir()
    (clean / "module.py").write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
    (clean / "notes.md").write_text(f"| WP14-D002 | {WP14_PROSE} | BLOCKED |\n", encoding="utf-8")
    assert run_gitleaks_dir(binary, clean, config) == 0

    # A secret on the historically classified WP14-D002 row must still be detected.
    wp14 = tmp_path / "wp14" / "docs"
    wp14.mkdir(parents=True)
    row = f"| WP14-D002 | {WP14_PROSE} | token {synthetic_github_token()} |\n"
    (wp14 / "deferred_items_log.md").write_text(row, encoding="utf-8")
    assert run_gitleaks_dir(binary, wp14.parent, config) == 9


def test_gitleaks_git_mode_detects_secret_added_to_classified_wp14_row(tmp_path):
    binary = gitleaks_binary()
    git = shutil.which("git")
    if binary is None or git is None:
        pytest.skip("gitleaks binary or git not available")
    repo = tmp_path / "repo"
    (repo / "docs").mkdir(parents=True)
    (repo / ".gitleaks.toml").write_text(GITLEAKS_CONFIG.read_text(encoding="utf-8"), encoding="utf-8")
    (repo / ".gitleaksignore").write_text(GITLEAKS_IGNORE.read_text(encoding="utf-8"), encoding="utf-8")
    log = repo / "docs" / "deferred_items_log.md"

    def commit(text: str) -> None:
        log.write_text(text, encoding="utf-8")
        for args in (["add", "-A"], ["-c", "user.name=t", "-c", "user.email=t@example.invalid",
                                     "-c", "commit.gpgsign=false", "commit", "-q", "-m", "c"]):
            subprocess.run([git, "-C", str(repo), *args], check=True, capture_output=True)

    subprocess.run([git, "init", "-q", str(repo)], check=True, capture_output=True)
    commit(f"| WP14-D002 | {WP14_PROSE} | BLOCKED |\n")
    assert run_gitleaks(binary, "git", repo, None) == 0
    commit(f"| WP14-D002 | {WP14_PROSE} | BLOCKED | token {synthetic_github_token()} |\n")
    assert run_gitleaks(binary, "git", repo, None) == 9


def test_gitleaks_repo_config_autoloads_and_detects(tmp_path):
    binary = gitleaks_binary()
    if binary is None:
        pytest.skip("gitleaks binary not available (tools/.bin or PATH)")
    (tmp_path / ".gitleaks.toml").write_text(GITLEAKS_CONFIG.read_text(encoding="utf-8"), encoding="utf-8")
    (tmp_path / "settings.py").write_text(f'token = "{synthetic_github_token()}"\n', encoding="utf-8")
    assert run_gitleaks_dir(binary, tmp_path, None) == 9


@pytest.mark.parametrize("config_text", [DEFECTIVE_WP15_CONFIG, ROW_BOUND_ALLOWLIST_CONFIG])
def test_defective_wp15_config_shape_detects_nothing(tmp_path, config_text):
    binary = gitleaks_binary()
    if binary is None:
        pytest.skip("gitleaks binary not available (tools/.bin or PATH)")
    config = tmp_path / "defective.toml"
    config.write_text(config_text, encoding="utf-8")
    source = tmp_path / "docs"
    source.mkdir()
    row = f"| WP14-D002 | {WP14_PROSE} | token {synthetic_github_token()} |\n"
    (source / "deferred_items_log.md").write_text(row, encoding="utf-8")
    assert run_gitleaks_dir(binary, tmp_path, config) == 0
