"""Tests for tools/git/diff_scope_summary.py."""

import importlib
import json
import pathlib
import subprocess
import sys
import types

import pytest

# Import the helper module directly
_HELPER_PATH = (
    pathlib.Path(__file__).parent.parent.parent.parent
    / "tools" / "git" / "diff_scope_summary.py"
)

# Load the module without executing __main__
_spec = importlib.util.spec_from_file_location("diff_scope_summary", _HELPER_PATH)
dss = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(dss)

REPO_ROOT = pathlib.Path(__file__).parent.parent.parent.parent


# ── 1. Parse name-status output ─────────────────────────────────────────────

def test_parse_added():
    raw = "A\tsrc/foo.py\n"
    entries = dss.parse_name_status(raw)
    assert len(entries) == 1
    assert entries[0]["status"] == "A"
    assert entries[0]["path"] == "src/foo.py"


def test_parse_modified():
    raw = "M\tdocs/README.md\n"
    entries = dss.parse_name_status(raw)
    assert entries[0]["status"] == "M"
    assert entries[0]["path"] == "docs/README.md"


def test_parse_deleted():
    raw = "D\told_file.py\n"
    entries = dss.parse_name_status(raw)
    assert entries[0]["status"] == "D"


def test_parse_renamed():
    raw = "R100\told/path.py\tnew/path.py\n"
    entries = dss.parse_name_status(raw)
    assert entries[0]["status"] == "R"
    assert entries[0]["path"] == "new/path.py"
    assert entries[0]["old_path"] == "old/path.py"


def test_parse_multiple_statuses():
    raw = "A\ttools/git/helper.py\nM\tdocs/status.md\nD\told.txt\n"
    entries = dss.parse_name_status(raw)
    statuses = [e["status"] for e in entries]
    assert statuses == ["A", "M", "D"]
    assert entries[0]["path"] == "tools/git/helper.py"


def test_parse_empty():
    assert dss.parse_name_status("") == []


def test_parse_backslash_normalised():
    raw = "M\tdocs\\subdir\\file.md\n"
    entries = dss.parse_name_status(raw)
    assert entries[0]["path"] == "docs/subdir/file.md"


# ── 2. Allowed scope ─────────────────────────────────────────────────────────

def test_in_scope_by_file():
    assert dss.is_in_scope("docs/README.md", allowed_files=["docs/README.md"], allowed_prefixes=[]) is True


def test_in_scope_by_prefix():
    assert dss.is_in_scope("docs/ai/codex/foo.md", allowed_files=[], allowed_prefixes=["docs/"]) is True


def test_out_of_scope():
    assert dss.is_in_scope("src/foo.py", allowed_files=[], allowed_prefixes=["docs/"]) is False


def test_no_scope_declared_returns_none():
    assert dss.is_in_scope("anything.py", allowed_files=[], allowed_prefixes=[]) is None


def test_build_summary_no_scope_no_oos_warning():
    entries = [{"status": "A", "path": "src/foo.py"}]
    summary = dss.build_summary(
        base="main", head="HEAD", package_class="unspecified",
        allowed_files=[], allowed_prefixes=[], forbidden_prefixes=[],
        entries=entries, diff_stat="", diff_check_errors=[], git_errors=[],
    )
    assert summary["out_of_scope_files"] == []
    assert summary["scope_declared"] is False


def test_build_summary_oos_warning_when_scope_declared():
    entries = [
        {"status": "A", "path": "src/foo.py"},
        {"status": "M", "path": "docs/status.md"},
    ]
    summary = dss.build_summary(
        base="main", head="HEAD", package_class="unspecified",
        allowed_files=[], allowed_prefixes=["docs/"], forbidden_prefixes=[],
        entries=entries, diff_stat="", diff_check_errors=[], git_errors=[],
    )
    assert "src/foo.py" in summary["out_of_scope_files"]
    assert "docs/status.md" not in summary["out_of_scope_files"]


# ── 3. Forbidden/protected paths ─────────────────────────────────────────────

def test_explicit_forbidden_prefix():
    assert dss.is_protected_explicit("src/foo.py", ["src/"]) is True
    assert dss.is_protected_explicit("docs/foo.md", ["src/"]) is False


def test_builtin_hermes_protected():
    assert dss.is_protected_builtin("tools/hermes/config.py") is True


def test_builtin_agent_runtime_protected():
    assert dss.is_protected_builtin("agent_runtime/runner.py") is True


def test_builtin_dotenv_protected():
    assert dss.is_protected_builtin(".env") is True


def test_builtin_dotenv_prefix_protected():
    assert dss.is_protected_builtin(".env.production") is True


def test_builtin_private_key_protected():
    assert dss.is_protected_builtin("keys/private_key.pem") is True


def test_builtin_wallet_key_protected():
    assert dss.is_protected_builtin("walletkey.json") is True


def test_builtin_mnemonic_protected():
    assert dss.is_protected_builtin("backup_mnemonic.txt") is True


def test_normal_file_not_protected():
    assert dss.is_protected_builtin("tools/git/diff_scope_summary.py") is False
    assert dss.is_protected_builtin("docs/project_status.md") is False


# ── 4. Dependency/lock detection ─────────────────────────────────────────────

@pytest.mark.parametrize("path", [
    "pyproject.toml",
    "requirements.txt",
    "requirements-dev.txt",
    "uv.lock",
    "package-lock.json",
    "Cargo.lock",
    "poetry.lock",
    "Pipfile.lock",
    "setup.cfg",
    "setup.py",
    "Cargo.toml",
    "package.json",
    "some/path/custom.lock",
])
def test_dependency_lock_detected(path):
    assert dss.is_dependency_or_lock(path) is True


def test_non_dependency_not_flagged():
    assert dss.is_dependency_or_lock("docs/README.md") is False
    assert dss.is_dependency_or_lock("src/foo.py") is False


# ── 5. Generated artifact detection ─────────────────────────────────────────

@pytest.mark.parametrize("path", [
    "local_data/diff_scope_summaries/wp30.json",
    ".venv-security/lib/pkg.py",
    ".venv-official-client/x.py",
    "tools/.bin/gitleaks.exe",
    "tools/security/.cache/report",
    "security-scan-output/results.json",
    "official-client-sandbox-output/sandbox.py",
    ".pytest_cache/v/cache",
    "__pycache__/foo.pyc",
    ".coverage",
    "scan_results.sarif",
])
def test_generated_artifact_detected(path):
    assert dss.is_generated_artifact(path) is True


def test_non_generated_not_flagged():
    assert dss.is_generated_artifact("tools/git/diff_scope_summary.py") is False
    assert dss.is_generated_artifact("docs/project_status.md") is False


# ── 6. Package-class warnings ────────────────────────────────────────────────

def test_docs_only_touching_src_warns():
    warnings = dss.package_class_warnings(
        "docs-only", ["src/foo.py", "docs/README.md"],
        allowed_files=[], allowed_prefixes=[],
    )
    assert any("src/" in w for w in warnings)


def test_design_touching_src_warns():
    warnings = dss.package_class_warnings(
        "design", ["src/bar.py"],
        allowed_files=[], allowed_prefixes=[],
    )
    assert any("src/" in w for w in warnings)


def test_design_touching_tools_warns():
    warnings = dss.package_class_warnings(
        "design", ["tools/git/helper.py"],
        allowed_files=[], allowed_prefixes=[],
    )
    assert any("tools/" in w for w in warnings)


def test_design_tooling_touching_tools_no_warn():
    # package class includes "tooling" → no warning for tools/
    warnings = dss.package_class_warnings(
        "local-tooling", ["tools/git/helper.py"],
        allowed_files=[], allowed_prefixes=["tools/git/"],
    )
    assert not any("tools/" in w for w in warnings)


def test_docs_only_src_explicitly_allowed_no_warn():
    warnings = dss.package_class_warnings(
        "docs-only", ["src/foo.py"],
        allowed_files=[], allowed_prefixes=["src/"],
    )
    assert not any("src/" in w for w in warnings)


def test_live_trading_without_auth_warns():
    warnings = dss.package_class_warnings(
        "live-trading", ["src/foo.py"],
        allowed_files=[], allowed_prefixes=[],
    )
    assert any("live_trading_authorization" in w for w in warnings)


def test_live_trading_with_auth_no_warn_for_auth():
    warnings = dss.package_class_warnings(
        "live-trading",
        ["src/foo.py", "docs/live_trading_authorization.md"],
        allowed_files=[], allowed_prefixes=[],
    )
    # Should not warn about missing auth doc since it's changed
    assert not any("live_trading_authorization" in w for w in warnings)


# ── 7. Text output ───────────────────────────────────────────────────────────

def _make_summary(**overrides):
    base = dict(
        base="main", head="HEAD", package_class="local-tooling",
        allowed_files=["tools/git/diff_scope_summary.py"],
        allowed_prefixes=["docs/", "tests/", "tools/git/"],
        forbidden_prefixes=["src/"],
        entries=[
            {"status": "A", "path": "tools/git/diff_scope_summary.py"},
            {"status": "M", "path": "docs/project_status.md"},
        ],
        diff_stat="2 files changed, 100 insertions(+)",
        diff_check_errors=[],
        git_errors=[],
    )
    base.update(overrides)
    return dss.build_summary(**base)


def test_text_output_includes_changed_file_count():
    summary = _make_summary()
    text = dss.render_text(summary)
    assert "2" in text  # total changed
    assert "Changed files" in text


def test_text_output_includes_validation_reminder():
    summary = _make_summary()
    text = dss.render_text(summary)
    assert "REMINDER" in text
    assert "pytest" in text


def test_text_output_no_raw_diff():
    summary = _make_summary()
    text = dss.render_text(summary)
    # Ensure we don't dump raw git diff hunks
    assert "@@" not in text
    assert "diff --git" not in text


def test_text_output_includes_warnings_section():
    summary = _make_summary(
        entries=[{"status": "A", "path": "pyproject.toml"}],
        allowed_files=[], allowed_prefixes=["docs/"],
    )
    text = dss.render_text(summary)
    assert "WARNING" in text or "warning" in text.lower()


def test_text_output_includes_suggested_attention():
    summary = _make_summary()
    text = dss.render_text(summary)
    assert "review" in text.lower() or "attention" in text.lower()


# ── 8. JSON output ───────────────────────────────────────────────────────────

def test_json_output_parseable():
    summary = _make_summary()
    rendered = dss.render_json(summary)
    parsed = json.loads(rendered)
    assert isinstance(parsed, dict)


def test_json_output_has_schema_version():
    summary = _make_summary()
    parsed = json.loads(dss.render_json(summary))
    assert "summary_schema_version" in parsed
    assert parsed["summary_schema_version"] == dss.SUMMARY_SCHEMA_VERSION


def test_json_output_has_required_fields():
    summary = _make_summary()
    parsed = json.loads(dss.render_json(summary))
    for field in [
        "base", "head", "package_class", "total_changed_files", "counts",
        "changed_files_by_status", "out_of_scope_files", "protected_path_hits",
        "dependency_lock_changes", "generated_artifact_hits", "package_class_warnings",
        "warnings", "warning_count", "validation_reminder", "suggested_review_attention",
    ]:
        assert field in parsed, f"JSON output must contain field: {field}"


def test_json_output_counts_correct():
    summary = _make_summary()
    parsed = json.loads(dss.render_json(summary))
    assert parsed["total_changed_files"] == 2
    assert parsed["counts"]["added"] == 1
    assert parsed["counts"]["modified"] == 1


# ── 9. Output path validation ────────────────────────────────────────────────

def test_valid_output_path_accepted():
    err = dss.validate_output_path("local_data/diff_scope_summaries/wp30.json")
    assert err is None


def test_output_path_outside_allowed_rejected():
    err = dss.validate_output_path("local_data/other_dir/file.json")
    assert err is not None
    assert "local_data/diff_scope_summaries/" in err


def test_output_path_traversal_rejected():
    err = dss.validate_output_path("local_data/diff_scope_summaries/../../etc/passwd")
    assert err is not None
    assert "traversal" in err.lower() or ".." in err


def test_output_path_repo_root_rejected():
    err = dss.validate_output_path("evil_output.json")
    assert err is not None


def test_no_output_path_accepted():
    err = dss.validate_output_path(None)
    assert err is None


def test_empty_output_path_accepted():
    err = dss.validate_output_path("")
    assert err is None


def test_absolute_path_containing_allowed_prefix_rejected():
    # An absolute path that contains the allowed prefix string should still be rejected
    # because it writes outside the repo-local directory.
    err = dss.validate_output_path("/tmp/local_data/diff_scope_summaries/out.json")
    assert err is not None
    assert "absolute" in err.lower() or "repo-relative" in err.lower()


def test_windows_absolute_path_containing_allowed_prefix_rejected():
    # Windows-style absolute path that contains the allowed prefix should be rejected.
    err = dss.validate_output_path(r"C:\some\path\local_data\diff_scope_summaries\out.json")
    assert err is not None
    assert "absolute" in err.lower() or "repo-relative" in err.lower()


def test_absolute_path_at_repo_root_rejected():
    # A plain absolute path (no allowed prefix) must also be rejected.
    err = dss.validate_output_path("/home/user/output.json")
    assert err is not None
    assert "absolute" in err.lower() or "repo-relative" in err.lower()


def test_relative_valid_path_still_accepted():
    # A correct repo-relative path must remain accepted after the fix.
    err = dss.validate_output_path("local_data/diff_scope_summaries/follow_up.json")
    assert err is None


# ── 10. Exit code behaviour ──────────────────────────────────────────────────

def test_exit_0_no_warnings(monkeypatch):
    calls = {}

    def fake_get_name_status(base, head):
        return [{"status": "M", "path": "docs/README.md"}], None

    def fake_get_diff_stat(base, head):
        return "1 file changed", None

    def fake_get_diff_check(base, head):
        return [], None

    monkeypatch.setattr(dss, "get_name_status", fake_get_name_status)
    monkeypatch.setattr(dss, "get_diff_stat", fake_get_diff_stat)
    monkeypatch.setattr(dss, "get_diff_check", fake_get_diff_check)

    rc = dss.main([
        "--base", "main", "--head", "HEAD",
        "--package-class", "docs-only",
        "--allowed-prefix", "docs/",
    ])
    assert rc == 0


def test_exit_0_with_warnings_by_default(monkeypatch):
    def fake_get_name_status(base, head):
        return [{"status": "A", "path": "pyproject.toml"}], None

    def fake_get_diff_stat(base, head):
        return "1 file changed", None

    def fake_get_diff_check(base, head):
        return [], None

    monkeypatch.setattr(dss, "get_name_status", fake_get_name_status)
    monkeypatch.setattr(dss, "get_diff_stat", fake_get_diff_stat)
    monkeypatch.setattr(dss, "get_diff_check", fake_get_diff_check)

    rc = dss.main([
        "--base", "main", "--head", "HEAD",
        "--package-class", "docs-only",
        "--allowed-prefix", "docs/",
    ])
    assert rc == 0


def test_exit_1_with_fail_on_warning_and_warnings(monkeypatch):
    def fake_get_name_status(base, head):
        return [{"status": "A", "path": "pyproject.toml"}], None

    def fake_get_diff_stat(base, head):
        return "1 file changed", None

    def fake_get_diff_check(base, head):
        return [], None

    monkeypatch.setattr(dss, "get_name_status", fake_get_name_status)
    monkeypatch.setattr(dss, "get_diff_stat", fake_get_diff_stat)
    monkeypatch.setattr(dss, "get_diff_check", fake_get_diff_check)

    rc = dss.main([
        "--base", "main", "--head", "HEAD",
        "--package-class", "docs-only",
        "--allowed-prefix", "docs/",
        "--fail-on-warning",
    ])
    assert rc == 1


def test_exit_2_invalid_output_path():
    rc = dss.main([
        "--base", "main", "--head", "HEAD",
        "--package-class", "docs-only",
        "--output", "evil_output.json",
    ])
    assert rc == 2


# ── 11. No-network / no-forbidden imports ────────────────────────────────────

def test_no_forbidden_imports():
    source = _HELPER_PATH.read_text(encoding="utf-8")
    forbidden_imports = [
        "import requests",
        "import httpx",
        "import aiohttp",
        "import websockets",
        "import openai",
        "import anthropic",
        "import langchain",
        "import hermes",
        "import py_clob_client",
        "import socket",
    ]
    for fi in forbidden_imports:
        assert fi not in source, (
            f"tools/git/diff_scope_summary.py must not import: {fi}"
        )


def test_no_forbidden_trading_terms():
    source = _HELPER_PATH.read_text(encoding="utf-8")
    forbidden_terms = [
        "post_order",
        "submit_order",
        "sign_order",
        "execute_trade",
        "create_trade_proposal",
        "generate_signal",
    ]
    for term in forbidden_terms:
        assert term not in source, (
            f"tools/git/diff_scope_summary.py must not contain trading term: {term}"
        )


# ── 12. CLI smoke tests ───────────────────────────────────────────────────────

def test_cli_help_exits_0():
    result = subprocess.run(
        [sys.executable, str(_HELPER_PATH), "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "diff" in result.stdout.lower() or "scope" in result.stdout.lower()


def test_cli_smoke_with_patched_git(monkeypatch, tmp_path, capsys):
    """CLI integration: patch git commands, verify exit 0 and summary output."""

    def fake_get_name_status(base, head):
        return [
            {"status": "A", "path": "tools/git/diff_scope_summary.py"},
            {"status": "M", "path": "docs/project_status.md"},
        ], None

    def fake_get_diff_stat(base, head):
        return "2 files changed, 100 insertions(+)", None

    def fake_get_diff_check(base, head):
        return [], None

    monkeypatch.setattr(dss, "get_name_status", fake_get_name_status)
    monkeypatch.setattr(dss, "get_diff_stat", fake_get_diff_stat)
    monkeypatch.setattr(dss, "get_diff_check", fake_get_diff_check)

    rc = dss.main([
        "--base", "main",
        "--head", "HEAD",
        "--package-class", "local-tooling",
        "--allowed-prefix", "docs/",
        "--allowed-prefix", "tools/git/",
    ])
    assert rc == 0
    captured = capsys.readouterr()
    assert "DIFF SCOPE SUMMARY" in captured.out
    assert "REMINDER" in captured.out


def test_cli_json_smoke_with_patched_git(monkeypatch, capsys):
    def fake_get_name_status(base, head):
        return [{"status": "M", "path": "docs/README.md"}], None

    def fake_get_diff_stat(base, head):
        return "1 file changed", None

    def fake_get_diff_check(base, head):
        return [], None

    monkeypatch.setattr(dss, "get_name_status", fake_get_name_status)
    monkeypatch.setattr(dss, "get_diff_stat", fake_get_diff_stat)
    monkeypatch.setattr(dss, "get_diff_check", fake_get_diff_check)

    rc = dss.main([
        "--base", "main",
        "--head", "HEAD",
        "--package-class", "docs-only",
        "--allowed-prefix", "docs/",
        "--format", "json",
    ])
    assert rc == 0
    captured = capsys.readouterr()
    parsed = json.loads(captured.out)
    assert parsed["summary_schema_version"] == dss.SUMMARY_SCHEMA_VERSION
    assert "validation_reminder" in parsed
