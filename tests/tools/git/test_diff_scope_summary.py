"""Tests for tools/git/diff_scope_summary.py."""

import importlib
import inspect
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
_GUARD_PATH = REPO_ROOT / "tools" / "wp" / "wp_spec_guard.py"
_guard_spec = importlib.util.spec_from_file_location("wp_spec_guard_parity", _GUARD_PATH)
guard = importlib.util.module_from_spec(_guard_spec)
_guard_spec.loader.exec_module(guard)


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


# ── 13. WP-spec exact-scope mode ────────────────────────────────────────────

def _spec_summary(**overrides):
    base = dict(
        base="origin/main",
        head="HEAD",
        package_class="GOVERNANCE",
        allowed_files=["docs/a.md", "docs/b.md"],
        allowed_prefixes=[],
        forbidden_prefixes=["src/"],
        entries=[
            {"status": "M", "status_detail": "M", "path": "docs/a.md"},
        ],
        diff_stat="1 file changed",
        diff_check_errors=[],
        git_errors=[],
        wp_spec_path="docs/wp_specs/WP159/wp_spec.json",
        wp_spec_schema_version="1.0.0",
        required_changed_files=("docs/a.md",),
        untracked_files=(),
        max_changed_files=2,
        exact_scope_required=True,
        authority={"docs": True, "tests": True, "local_offline_tooling": True},
        git_operations_succeeded=True,
    )
    base.update(overrides)
    return dss.build_summary(**base)


def test_build_summary_signature_locks_keyword_only_extension():
    signature = inspect.signature(dss.build_summary)
    assert list(signature.parameters)[:10] == [
        "base",
        "head",
        "package_class",
        "allowed_files",
        "allowed_prefixes",
        "forbidden_prefixes",
        "entries",
        "diff_stat",
        "diff_check_errors",
        "git_errors",
    ]
    for name in (
        "wp_spec_path",
        "wp_spec_schema_version",
        "required_changed_files",
        "untracked_files",
        "max_changed_files",
        "exact_scope_required",
        "authority",
        "git_operations_succeeded",
    ):
        assert signature.parameters[name].kind is inspect.Parameter.KEYWORD_ONLY


def test_parse_nul_name_status_rename_and_copy():
    raw = (
        "R100\0old/name.md\0new/name.md\0"
        "C075\0source.md\0copy.md\0"
        "D\0deleted.md\0"
    )
    assert dss.parse_name_status(raw) == [
        {
            "status": "R",
            "status_detail": "R100",
            "old_path": "old/name.md",
            "path": "new/name.md",
        },
        {
            "status": "C",
            "status_detail": "C075",
            "old_path": "source.md",
            "path": "copy.md",
        },
        {"status": "D", "status_detail": "D", "path": "deleted.md"},
    ]


def test_spec_summary_adds_schema_two_fields_only_in_spec_mode():
    summary = _spec_summary()
    assert summary["summary_schema_version"] == "2.0"
    assert summary["wp_spec_schema_version"] == "1.0.0"
    assert summary["required_changed_files"] == ["docs/a.md"]
    assert summary["allowed_changed_files"] == ["docs/a.md", "docs/b.md"]
    assert summary["missing_required_files"] == []
    assert summary["untracked_files"] == []
    assert summary["exact_scope_required"] is True
    assert summary["exact_scope_pass"] is True

    legacy = _make_summary()
    assert legacy["summary_schema_version"] == "1.0"
    for field in (
        "wp_spec_path",
        "wp_spec_schema_version",
        "required_changed_files",
        "allowed_changed_files",
        "missing_required_files",
        "untracked_files",
        "exact_scope_required",
        "exact_scope_pass",
    ):
        assert field not in legacy


def test_untracked_files_are_sorted_deduplicated_added_and_present():
    summary = _spec_summary(
        entries=[],
        required_changed_files=("docs/a.md", "docs/b.md"),
        untracked_files=("docs/b.md", "docs/a.md", "docs/b.md"),
    )
    assert summary["untracked_files"] == ["docs/a.md", "docs/b.md"]
    assert summary["changed_files_by_status"]["A"] == ["docs/a.md", "docs/b.md"]
    assert summary["counts"]["added"] == 2
    assert summary["total_changed_files"] == 2
    assert summary["missing_required_files"] == []
    assert sum(summary["counts"].values()) == summary["total_changed_files"]


def test_required_deletion_is_present_and_counts_once():
    summary = _spec_summary(
        entries=[{"status": "D", "status_detail": "D", "path": "docs/a.md"}]
    )
    assert summary["missing_required_files"] == []
    assert summary["counts"]["deleted"] == 1
    assert summary["exact_scope_pass"] is True


def test_rename_source_is_policy_checked_but_not_counted_or_presence():
    summary = _spec_summary(
        allowed_files=["docs/new.md"],
        entries=[
            {
                "status": "R",
                "status_detail": "R100",
                "old_path": "src/old.py",
                "path": "docs/new.md",
            }
        ],
        required_changed_files=("src/old.py",),
    )
    assert summary["total_changed_files"] == 1
    assert "src/old.py" in summary["out_of_scope_files"]
    assert "src/old.py" in summary["protected_path_hits"]
    assert summary["missing_required_files"] == ["src/old.py"]
    assert summary["exact_scope_pass"] is False


@pytest.mark.parametrize(
    "override",
    [
        {"entries": [{"status": "M", "path": "docs/b.md"}]},
        {"required_changed_files": ("docs/missing.md",)},
        {
            "entries": [
                {"status": "M", "path": "docs/a.md"},
                {"status": "M", "path": "docs/b.md"},
            ],
            "untracked_files": ("docs/c.md",),
        },
        {"diff_check_errors": ["docs/a.md:1: trailing whitespace."]},
        {"git_operations_succeeded": False},
    ],
)
def test_every_exact_scope_condition_fails_closed(override):
    summary = _spec_summary(**override)
    assert summary["exact_scope_pass"] is False


def test_unauthorized_tool_and_dependency_paths_fail_exact_scope():
    summary = _spec_summary(
        allowed_files=["tools/x.py", "pyproject.toml"],
        entries=[
            {"status": "M", "path": "tools/x.py"},
            {"status": "M", "path": "pyproject.toml"},
        ],
        required_changed_files=("tools/x.py", "pyproject.toml"),
        authority={"docs": True, "local_offline_tooling": False, "dependencies": False},
    )
    assert summary["exact_scope_pass"] is False
    assert any("authority" in warning for warning in summary["warnings"])


def test_spec_git_command_arrays_are_exact(monkeypatch):
    calls = []

    def fake_run(args, cwd=None):
        calls.append(args)
        if args[0] == "diff" and "--name-status" in args:
            return "M\0docs/a.md\0", "", 0
        return "", "", 0

    monkeypatch.setattr(dss, "_run_git", fake_run)
    entries, error = dss._get_name_status_spec("origin/main", "HEAD")
    untracked, untracked_error = dss._get_untracked_spec()
    dss.get_diff_stat("origin/main", "HEAD")
    dss.get_diff_check("origin/main", "HEAD")
    assert error is None and untracked_error is None
    assert entries[0]["path"] == "docs/a.md"
    assert untracked == []
    assert calls == [
        [
            "diff",
            "--name-status",
            "-z",
            "--find-renames=50%",
            "--find-copies=50%",
            "--find-copies-harder",
            "origin/main...HEAD",
        ],
        ["ls-files", "--others", "--exclude-standard", "-z"],
        ["diff", "--stat", "origin/main...HEAD"],
        ["diff", "--check", "origin/main...HEAD"],
    ]


@pytest.mark.parametrize(
    "args",
    [
        ["--require-exact-scope"],
        ["--wp-spec", "spec.json", "--allowed-file", "docs/a.md"],
        ["--wp-spec", "spec.json", "--allowed-prefix", "docs/"],
        ["--wp-spec", "spec.json", "--forbidden-prefix", "src/"],
        ["--wp-spec", "spec.json", "--package-class", "GOVERNANCE"],
        [
            "--wp-spec",
            "spec.json",
            "--output",
            "local_data/diff_scope_summaries/a.json",
        ],
    ],
)
def test_spec_mode_rejects_ambiguous_manual_flags(args, capsys):
    assert dss.main(args) == 2
    assert "ERROR:" in capsys.readouterr().err


def test_spec_mode_git_failure_is_neutral_exit_two(monkeypatch, capsys):
    scope = {
        "schema_version": "1.0.0",
        "package_class": "GOVERNANCE",
        "required_changed_files": (),
        "allowed_changed_files": (),
        "forbidden_prefixes": (),
        "max_changed_files": 1,
        "exact_scope_required": True,
        "authority": {},
    }
    monkeypatch.setattr(dss, "_read_wp_spec_scope", lambda path: (scope, ()))
    monkeypatch.setattr(
        dss, "_get_name_status_spec", lambda base, head: ([], "sensitive failure")
    )
    monkeypatch.setattr(dss, "get_diff_stat", lambda base, head: ("", None))
    monkeypatch.setattr(dss, "get_diff_check", lambda base, head: ([], None))
    monkeypatch.setattr(dss, "_get_untracked_spec", lambda: ([], None))
    assert dss.main(["--wp-spec", "private-path"]) == 2
    captured = capsys.readouterr()
    assert "sensitive failure" not in captured.out + captured.err
    assert "private-path" not in captured.out + captured.err


def test_spec_mode_exact_failure_exits_one(monkeypatch, capsys):
    scope = {
        "schema_version": "1.0.0",
        "package_class": "GOVERNANCE",
        "required_changed_files": ("docs/a.md",),
        "allowed_changed_files": ("docs/a.md",),
        "forbidden_prefixes": (),
        "max_changed_files": 1,
        "exact_scope_required": True,
        "authority": {"docs": True},
    }
    monkeypatch.setattr(dss, "_read_wp_spec_scope", lambda path: (scope, ()))
    monkeypatch.setattr(dss, "_get_name_status_spec", lambda base, head: ([], None))
    monkeypatch.setattr(dss, "get_diff_stat", lambda base, head: ("", None))
    monkeypatch.setattr(dss, "get_diff_check", lambda base, head: ([], None))
    monkeypatch.setattr(dss, "_get_untracked_spec", lambda: ([], None))
    assert dss.main(["--wp-spec", "spec.json", "--format", "json"]) == 1
    assert json.loads(capsys.readouterr().out)["exact_scope_pass"] is False


@pytest.mark.parametrize(
    "path",
    [
        ".env",
        ".env.production",
        "id_rsa",
        "id_ed25519",
        ".keystore",
        "credentials.json",
        "secret.pem",
        "secret.p12",
        "secret.pfx",
        "tools/hermes/runner.py",
        "agent_runtime/runner.py",
        "agent_memory/state.json",
        "local_data/output.json",
        ".pytest_cache/state",
        ".coverage",
        "scan.sarif",
        "requirements.txt",
        "requirements-dev.txt",
        "pyproject.toml",
        "setup.cfg",
        "setup.py",
        "Pipfile",
        "Pipfile.lock",
        "poetry.lock",
        "uv.lock",
        "package.json",
        "package-lock.json",
        "Cargo.toml",
        "Cargo.lock",
        "custom.lock",
    ],
)
def test_guard_and_diff_helper_classifier_tables_are_identical(path):
    assert guard._is_dependency_or_lock(path) is dss.is_dependency_or_lock(path)
    assert guard._is_generated_artifact(path) is dss.is_generated_artifact(path)
    assert guard._is_protected_builtin(path) is dss.is_protected_builtin(path)


@pytest.mark.parametrize(
    "path",
    [
        ".env",
        ".env.production",
        "id_rsa",
        "id_ed25519",
        ".keystore",
        "credentials.json",
        "secret.pem",
        "secret.p12",
        "secret.pfx",
        "tools/hermes/runner.py",
        "agent_runtime/runner.py",
        "agent_memory/state.json",
        "local_data/output.json",
        ".pytest_cache/state",
        ".coverage",
        "scan.sarif",
    ],
)
def test_exact_spec_guard_rejects_every_helper_protected_or_generated_path(path):
    document = json.loads(
        (REPO_ROOT / "docs/wp_specs/WP159/wp_spec.json").read_text(
            encoding="utf-8"
        )
    )
    document["scope"]["required_changed_files"][0] = path
    document["scope"]["allowed_changed_files"][0] = path
    validated, errors = guard.validate_spec_document(document)
    assert validated is None
    assert any(error["code"] == "SCOPE_POLICY_INVALID" for error in errors)
    assert dss.is_protected_builtin(path) or dss.is_generated_artifact(path)


@pytest.mark.parametrize(
    "path",
    [
        "requirements.txt",
        "requirements-dev.txt",
        "pyproject.toml",
        "setup.cfg",
        "setup.py",
        "Pipfile",
        "Pipfile.lock",
        "poetry.lock",
        "uv.lock",
        "package.json",
        "package-lock.json",
        "Cargo.toml",
        "Cargo.lock",
        "custom.lock",
    ],
)
def test_dependency_classifier_parity_uses_dependency_authority(path):
    document = json.loads(
        (REPO_ROOT / "docs/wp_specs/WP159/wp_spec.json").read_text(
            encoding="utf-8"
        )
    )
    document["scope"]["required_changed_files"][0] = path
    document["scope"]["allowed_changed_files"][0] = path
    document["authority"]["dependencies"] = True
    validated, errors = guard.validate_spec_document(document)
    assert validated is not None
    assert errors == ()
    assert dss.is_dependency_or_lock(path)
    assert not dss.is_protected_builtin(path)
    assert not dss.is_generated_artifact(path)
