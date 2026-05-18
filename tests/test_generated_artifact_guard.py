from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CLEANUP_SCRIPT = ROOT / "tools" / "git" / "cleanup_generated_artifacts.py"
GUARD_SCRIPT = ROOT / "tools" / "git" / "preflight_generated_artifact_guard.py"
SETUP_SCRIPT = ROOT / "tools" / "security" / "setup_project_security_tools.py"

GENERATED_PATHS = [
    ".venv-security/",
    "tools/.bin/",
    "tools/security/.cache/",
    "security-scan-output/",
]

FORBIDDEN_CLEANUP_PATTERNS = [
    "git clean -fd",
    "git clean -fdx",
    "git clean -fdX",
    "shutil.rmtree(ROOT)",
    "rm -rf .",
    "del /s",
]

FORBIDDEN_TRADING_OR_SECRET_TERMS = [
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


def test_generated_artifact_files_exist():
    assert CLEANUP_SCRIPT.is_file()
    assert GUARD_SCRIPT.is_file()
    assert (ROOT / "docs" / "local_generated_artifacts.md").is_file()


def test_generated_artifact_paths_are_ignored():
    text = read(ROOT / ".gitignore")
    for path in GENERATED_PATHS:
        assert path in text


def test_cleanup_script_is_allowlist_only_and_avoids_broad_cleanup():
    text = read(CLEANUP_SCRIPT)
    for path in [item.rstrip("/") for item in GENERATED_PATHS]:
        assert f'"{path}"' in text
    lowered = text.lower()
    for pattern in FORBIDDEN_CLEANUP_PATTERNS:
        assert pattern.lower() not in lowered


def test_cleanup_script_checks_tracked_and_staged_files_before_deleting():
    text = read(CLEANUP_SCRIPT)
    assert "ls-files" in text
    assert "diff" in text
    assert "--cached" in text
    assert "shutil.rmtree(path)" in text
    assert "--apply" in text


def test_artifact_guard_checks_ignore_status_and_git_visibility():
    text = read(GUARD_SCRIPT)
    assert "check-ignore" in text
    assert "status" in text
    assert "--short" in text
    assert "ls-files" in text
    assert "diff" in text
    assert "--cached" in text
    assert "cleanup_generated_artifacts.py --apply" in text


def test_security_setup_checks_ignore_protection_before_environment_creation():
    text = read(SETUP_SCRIPT)
    assert "require_security_venv_ignore_protection()" in text
    assert "check-ignore" in text
    assert "ls-files" in text
    assert "diff" in text
    assert "--cached" in text
    assert "venv.EnvBuilder" in text
    assert text.index("require_security_venv_ignore_protection()") < text.index("venv.EnvBuilder")


def test_generated_artifact_scripts_omit_trading_api_order_and_secret_terms():
    text = (read(CLEANUP_SCRIPT) + "\n" + read(GUARD_SCRIPT)).lower()
    for term in FORBIDDEN_TRADING_OR_SECRET_TERMS:
        assert term not in text


def test_repo_truth_mentions_generated_artifact_guard():
    checklist = read(ROOT / "docs" / "review_checklist.md").lower()
    guidelines = read(ROOT / "docs" / "codex_execution_guidelines.md").lower()
    assert "generated artifact guard passed" in checklist
    assert ".venv-security/" in checklist
    assert "tools/.bin/" in checklist
    assert "preflight_generated_artifact_guard.py" in guidelines
