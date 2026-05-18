import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHECK_SCRIPT = ROOT / "tools" / "security" / "check_security_tools.py"
RUN_SCRIPT = ROOT / "tools" / "security" / "run_available_security_checks.py"

FORBIDDEN_INSTALL_COMMANDS = [
    "pip install",
    "npm install",
    "winget install",
    "choco install",
    "brew install",
    "apt install",
    "cargo install",
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


def test_security_tooling_scripts_exist():
    assert CHECK_SCRIPT.is_file()
    assert RUN_SCRIPT.is_file()


def test_security_tooling_scripts_do_not_install_packages():
    text = CHECK_SCRIPT.read_text(encoding="utf-8") + "\n" + RUN_SCRIPT.read_text(encoding="utf-8")
    lowered = text.lower()
    for command in FORBIDDEN_INSTALL_COMMANDS:
        assert command not in lowered


def test_security_tooling_scripts_do_not_contain_trading_or_secret_terms():
    text = CHECK_SCRIPT.read_text(encoding="utf-8") + "\n" + RUN_SCRIPT.read_text(encoding="utf-8")
    lowered = text.lower()
    for term in FORBIDDEN_TRADING_TERMS:
        assert term not in lowered


def test_check_security_tools_exits_zero():
    completed = subprocess.run(
        ["python", str(CHECK_SCRIPT)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_security_readme_documents_no_installation_and_no_trading_authority():
    text = (ROOT / "tools" / "security" / "README.md").read_text(encoding="utf-8").lower()
    assert "do not install packages" in text
    assert "do not authorize live trading" in text
