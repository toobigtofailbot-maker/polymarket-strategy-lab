import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SETUP_SCRIPT = ROOT / "tools" / "security" / "setup_project_security_tools.py"
VERIFY_SCRIPT = ROOT / "tools" / "security" / "verify_project_security_tools.py"

FORBIDDEN_INSTALL_COMMANDS = [
    "winget install",
    "choco install",
    "brew install",
    "apt install",
    "npm install -g",
    "cargo install",
    "pip install --user",
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


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_project_security_tooling_scripts_exist():
    assert SETUP_SCRIPT.is_file()
    assert VERIFY_SCRIPT.is_file()


def test_local_security_tooling_paths_are_ignored():
    text = (ROOT / ".gitignore").read_text(encoding="utf-8")
    for term in [
        ".venv-security/",
        "tools/.bin/",
        "tools/security/.cache/",
        "security-scan-output/",
        "*.sarif",
    ]:
        assert term in text


def test_setup_script_omits_forbidden_global_or_user_install_commands():
    text = read(SETUP_SCRIPT).lower()
    for command in FORBIDDEN_INSTALL_COMMANDS:
        assert command not in text
    assert ".venv-security" in text
    assert "approved_security_tools" in text
    assert '"semgrep"' in text
    assert '"pip-audit"' in text


def test_setup_script_pip_usage_is_project_local():
    text = read(SETUP_SCRIPT)
    assert "venv.EnvBuilder" in text
    assert "SECURITY_VENV" in text
    assert '"-m", "pip", "install"' in text
    assert "venv_python()" in text


def test_security_tooling_completion_scripts_do_not_contain_order_or_secret_terms():
    text = (read(SETUP_SCRIPT) + "\n" + read(VERIFY_SCRIPT)).lower()
    for term in FORBIDDEN_TRADING_TERMS:
        assert term not in text


def test_verify_project_security_tools_exits_zero():
    completed = subprocess.run(
        ["python", str(VERIFY_SCRIPT)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_security_tooling_completion_docs_exist_and_reference_wp5():
    assert (ROOT / "docs" / "security_tooling_completion.md").is_file()
    status = (ROOT / "docs" / "security_tooling_status.md").read_text(encoding="utf-8")
    deferred = (ROOT / "docs" / "deferred_items_log.md").read_text(encoding="utf-8")
    assert "WP5" in status
    assert "WP5 Security Tooling Completion Update" in deferred
    assert "WP3-D001" in deferred
    assert "WP3-D002" in deferred
    assert "WP3-D003" in deferred
    assert "WP3-D004" in deferred
    assert "WP3-D005" in deferred
