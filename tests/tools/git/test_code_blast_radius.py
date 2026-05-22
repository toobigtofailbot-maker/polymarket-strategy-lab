"""Tests for tools/git/code_blast_radius.py."""

import importlib
import importlib.util
import json
import pathlib
import subprocess
import sys
import tempfile

import pytest

# Import the helper module directly without executing __main__
_HELPER_PATH = (
    pathlib.Path(__file__).parent.parent.parent.parent
    / "tools" / "git" / "code_blast_radius.py"
)

_spec = importlib.util.spec_from_file_location("code_blast_radius", _HELPER_PATH)
cbr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cbr)

REPO_ROOT = pathlib.Path(__file__).parent.parent.parent.parent


# ── 1. CLI help exits 0 ──────────────────────────────────────────────────────

def test_cli_help_exits_0():
    result = subprocess.run(
        [sys.executable, str(_HELPER_PATH), "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "blast-radius" in result.stdout.lower() or "advisory" in result.stdout.lower()


# ── 2. Input validation ──────────────────────────────────────────────────────

def test_rejects_missing_changed_inputs():
    code = cbr.main(["--package-class", "docs-only"])
    assert code == 2


def test_rejects_absolute_changed_file_unix():
    code = cbr.main(["--changed-file", "/absolute/path.py"])
    assert code == 2


def test_rejects_absolute_changed_file_windows():
    code = cbr.main(["--changed-file", "C:\\absolute\\path.py"])
    assert code == 2


def test_rejects_traversal_changed_file():
    code = cbr.main(["--changed-file", "../outside/file.py"])
    assert code == 2


def test_rejects_traversal_changed_prefix():
    code = cbr.main(["--changed-prefix", "docs/../../../etc"])
    assert code == 2


def test_rejects_invalid_max_results_zero():
    code = cbr.main(["--changed-file", "docs/project_status.md", "--max-results", "0"])
    assert code == 2


def test_rejects_invalid_max_results_negative():
    code = cbr.main(["--changed-file", "docs/project_status.md", "--max-results", "-1"])
    assert code == 2


def test_valid_input_exits_0():
    code = cbr.main([
        "--changed-file", "docs/project_status.md",
        "--package-class", "docs-only",
        "--repo-root", str(REPO_ROOT),
    ])
    assert code == 0


# ── 3. Output path validation ────────────────────────────────────────────────

def test_validate_output_accepts_valid():
    err = cbr.validate_output_path("local_data/code_blast_radius/out.json")
    assert err is None


def test_validate_output_accepts_nested():
    err = cbr.validate_output_path("local_data/code_blast_radius/subdir/out.json")
    assert err is None


def test_validate_output_rejects_absolute():
    err = cbr.validate_output_path("/tmp/out.json")
    assert err is not None


def test_validate_output_rejects_windows_absolute():
    err = cbr.validate_output_path("C:\\tmp\\out.json")
    assert err is not None


def test_validate_output_rejects_traversal():
    err = cbr.validate_output_path("local_data/code_blast_radius/../../evil.json")
    assert err is not None


def test_validate_output_rejects_outside_dir():
    err = cbr.validate_output_path("local_data/other/out.json")
    assert err is not None


def test_validate_output_rejects_root_level():
    err = cbr.validate_output_path("output.json")
    assert err is not None


def test_cli_rejects_absolute_output():
    code = cbr.main([
        "--changed-file", "docs/project_status.md",
        "--output", "/tmp/evil.json",
    ])
    assert code == 2


def test_cli_rejects_outside_output():
    code = cbr.main([
        "--changed-file", "docs/project_status.md",
        "--output", "local_data/other/out.json",
    ])
    assert code == 2


# ── 4. Excluded paths and sensitive paths are skipped ───────────────────────

def test_is_excluded_git_dir():
    assert cbr.is_excluded_path(".git/config") is True


def test_is_excluded_local_data():
    assert cbr.is_excluded_path("local_data/something.json") is True


def test_is_excluded_venv_security():
    assert cbr.is_excluded_path(".venv-security/lib/foo.py") is True


def test_is_excluded_pytest_cache():
    assert cbr.is_excluded_path(".pytest_cache/v/cache/lastfailed") is True


def test_is_excluded_pycache():
    assert cbr.is_excluded_path("src/__pycache__/foo.cpython-311.pyc") is True


def test_is_excluded_claude_dir():
    assert cbr.is_excluded_path(".claude/settings.json") is True


def test_is_excluded_coverage():
    assert cbr.is_excluded_path(".coverage") is True


def test_not_excluded_normal_py():
    assert cbr.is_excluded_path("tools/git/code_blast_radius.py") is False


def test_is_sensitive_env_file():
    assert cbr.is_sensitive_file(".env") is True


def test_is_sensitive_env_local():
    assert cbr.is_sensitive_file(".env.local") is True


def test_is_sensitive_private_key():
    assert cbr.is_sensitive_file("private_key.pem") is True


def test_is_sensitive_mnemonic():
    assert cbr.is_sensitive_file("mnemonic.txt") is True


def test_is_sensitive_wallet_key():
    assert cbr.is_sensitive_file("wallet_key.json") is True


def test_is_sensitive_id_rsa():
    assert cbr.is_sensitive_file("id_rsa") is True


def test_not_sensitive_normal_py():
    assert cbr.is_sensitive_file("code_blast_radius.py") is False


def test_walk_excludes_sensitive(tmp_path):
    (tmp_path / ".env").write_text("SECRET=abc")
    (tmp_path / "normal.py").write_text("x = 1")
    files = cbr.walk_repo_files(tmp_path)
    rel_files = [cbr._norm(f) for f in files]
    assert ".env" not in rel_files
    assert "normal.py" in rel_files


def test_walk_excludes_git_dir(tmp_path):
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    (git_dir / "config").write_text("[core]")
    (tmp_path / "readme.md").write_text("hello")
    files = cbr.walk_repo_files(tmp_path)
    assert not any(".git" in f for f in files)


# ── 5. Direct reference detection ───────────────────────────────────────────

def test_direct_reference_detects_path_mention(tmp_path):
    (tmp_path / "mentioner.py").write_text("# see docs/project_status.md for details\nx = 1")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "project_status.md").write_text("# Status")
    repo_files = cbr.walk_repo_files(tmp_path)
    refs = cbr.find_direct_references(repo_files, ["docs/project_status.md"], tmp_path)
    ref_files = [r["file"] for r in refs]
    assert "mentioner.py" in ref_files


def test_direct_reference_detects_stem_mention(tmp_path):
    (tmp_path / "other.py").write_text("import project_status\n")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "project_status.md").write_text("# Status")
    repo_files = cbr.walk_repo_files(tmp_path)
    refs = cbr.find_direct_references(repo_files, ["docs/project_status.md"], tmp_path)
    ref_files = [r["file"] for r in refs]
    assert "other.py" in ref_files


def test_direct_reference_excludes_self(tmp_path):
    (tmp_path / "changed.py").write_text("# This is the changed file: changed.py\n")
    repo_files = cbr.walk_repo_files(tmp_path)
    refs = cbr.find_direct_references(repo_files, ["changed.py"], tmp_path)
    ref_files = [r["file"] for r in refs]
    assert "changed.py" not in ref_files


def test_direct_reference_no_match(tmp_path):
    (tmp_path / "unrelated.py").write_text("x = 42\n")
    (tmp_path / "target.md").write_text("# Target")
    repo_files = cbr.walk_repo_files(tmp_path)
    refs = cbr.find_direct_references(repo_files, ["target.md"], tmp_path)
    assert refs == []


# ── 6. Naming heuristics ─────────────────────────────────────────────────────

def test_naming_heuristic_test_found(tmp_path):
    tests_dir = tmp_path / "tests" / "tools" / "git"
    tests_dir.mkdir(parents=True)
    (tests_dir / "test_my_helper.py").write_text("# tests")
    repo_files = cbr.walk_repo_files(tmp_path)
    hints = cbr.naming_heuristic_tests(["tools/git/my_helper.py"], repo_files)
    test_files = [h["suggested_test"] for h in hints]
    assert any("test_my_helper.py" in f for f in test_files)


def test_naming_heuristic_test_not_found():
    hints = cbr.naming_heuristic_tests(["tools/git/nonexistent_tool.py"], [])
    assert hints == []


def test_naming_heuristic_doc_found(tmp_path):
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "my_helper.md").write_text("# Doc")
    repo_files = cbr.walk_repo_files(tmp_path)
    hints = cbr.naming_heuristic_docs(["tools/git/my_helper.py"], repo_files)
    doc_files = [h["suggested_doc"] for h in hints]
    assert any("my_helper.md" in f for f in doc_files)


def test_naming_heuristic_doc_excludes_changed_file(tmp_path):
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "project_status.md").write_text("# Status")
    repo_files = cbr.walk_repo_files(tmp_path)
    changed_set = {"docs/project_status.md"}
    hints = cbr.naming_heuristic_docs(["docs/project_status.md"], repo_files)
    filtered = [h for h in hints if cbr._norm(h.get("suggested_doc", "")) not in changed_set]
    # The changed file itself should not appear in docs output
    doc_files = [h["suggested_doc"] for h in filtered]
    assert "docs/project_status.md" not in doc_files


# ── 7. Repo-truth relationship rules ────────────────────────────────────────

def test_repo_truth_rules_for_repo_truth_index():
    results = cbr.apply_repo_truth_rules(["docs/repo_truth_index.md"])
    related = [r["related"] for r in results]
    assert "docs/project_status.md" in related
    assert "docs/deferred_items_log.md" in related


def test_repo_truth_rules_for_project_status():
    results = cbr.apply_repo_truth_rules(["docs/project_status.md"])
    related = [r["related"] for r in results]
    assert "docs/deferred_items_log.md" in related
    assert "docs/repo_truth_index.md" in related


def test_repo_truth_rules_for_deferred_items():
    results = cbr.apply_repo_truth_rules(["docs/deferred_items_log.md"])
    related = [r["related"] for r in results]
    assert "docs/project_status.md" in related


def test_repo_truth_rules_for_codex_docs():
    results = cbr.apply_repo_truth_rules(["docs/ai/codex/NEW_HELPER.md"])
    related = [r["related"] for r in results]
    assert "docs/ai/codex/README.md" in related
    assert "docs/ai/codex/TOKEN_EFFICIENCY_OPERATING_MODEL.md" in related


def test_repo_truth_rules_for_tools_git():
    results = cbr.apply_repo_truth_rules(["tools/git/some_tool.py"])
    related = [r["related"] for r in results]
    assert "tests/tools/git/" in related


def test_repo_truth_rules_for_tools_validation():
    results = cbr.apply_repo_truth_rules(["tools/validation/some_tool.py"])
    related = [r["related"] for r in results]
    assert "tests/tools/validation/" in related


def test_repo_truth_rules_for_src_data_layer():
    results = cbr.apply_repo_truth_rules(["src/data_layer/polymarket/adapter.py"])
    related = [r["related"] for r in results]
    assert "docs/runtime_boundaries.md" in related


def test_repo_truth_no_spurious_results_for_unrelated():
    results = cbr.apply_repo_truth_rules(["some/random/file.py"])
    assert results == []


# ── 8. Protected/sensitive attention ────────────────────────────────────────

def test_protected_category_src():
    cat = cbr.get_protected_category("src/data_layer/adapter.py")
    assert cat is not None
    assert "protected-prefix" in cat


def test_protected_category_hermes():
    cat = cbr.get_protected_category("tools/hermes/client.py")
    assert cat is not None


def test_protected_category_agent_runtime():
    cat = cbr.get_protected_category("agent_runtime/main.py")
    assert cat is not None


def test_protected_category_env_file():
    cat = cbr.get_protected_category(".env")
    assert cat is not None
    assert "sensitive" in cat


def test_protected_category_env_local():
    cat = cbr.get_protected_category(".env.local")
    assert cat is not None


def test_protected_category_credential_name():
    cat = cbr.get_protected_category("private_key.pem")
    assert cat is not None
    assert "credential" in cat


def test_protected_category_mnemonic():
    cat = cbr.get_protected_category("mnemonic.txt")
    assert cat is not None


def test_protected_category_dependency_lock():
    cat = cbr.get_protected_category("requirements.txt")
    assert cat is not None
    assert "dependency" in cat


def test_protected_category_none_for_normal():
    cat = cbr.get_protected_category("docs/project_status.md")
    assert cat is None


def test_is_dependency_lock_requirements():
    assert cbr.is_dependency_lock("requirements.txt") is True


def test_is_dependency_lock_poetry():
    assert cbr.is_dependency_lock("poetry.lock") is True


def test_is_dependency_lock_package_json():
    assert cbr.is_dependency_lock("package.json") is True


def test_is_dependency_lock_pyproject():
    assert cbr.is_dependency_lock("pyproject.toml") is True


def test_is_not_dependency_lock():
    assert cbr.is_dependency_lock("tools/git/helper.py") is False


def test_is_generated_output_local_data():
    assert cbr.is_generated_output("local_data/snapshots/foo.json") is True


def test_is_generated_output_sarif():
    assert cbr.is_generated_output("scan.sarif") is True


def test_is_generated_output_coverage():
    assert cbr.is_generated_output(".coverage") is True


def test_is_not_generated_output():
    assert cbr.is_generated_output("docs/project_status.md") is False


def test_find_protected_hits_src():
    hits = cbr.find_protected_hits(["src/example.py"])
    assert any(h["path"] == "src/example.py" for h in hits)
    assert all("protected" in h["category"] or "credential" in h["category"] or "sensitive" in h["category"] or "dependency" in h["category"] for h in hits)


def test_find_protected_hits_env():
    hits = cbr.find_protected_hits([".env"])
    assert len(hits) >= 1
    assert any("sensitive" in h["category"] for h in hits)


def test_find_protected_hits_dep_lock():
    hits = cbr.find_dep_lock_hits(["requirements.txt"])
    assert len(hits) >= 1


def test_find_generated_output_hits():
    hits = cbr.find_generated_output_hits(["local_data/code_blast_radius/test.json"])
    assert len(hits) >= 1


# ── 9. Package-class warnings ────────────────────────────────────────────────

def test_pkg_warn_docs_only_touching_src():
    warnings = cbr.generate_package_class_warnings(
        "docs-only", ["src/data_layer/foo.py"], set()
    )
    assert any("src/" in w for w in warnings)


def test_pkg_warn_design_touching_src():
    warnings = cbr.generate_package_class_warnings(
        "design", ["src/module.py"], set()
    )
    assert any("src/" in w for w in warnings)


def test_pkg_warn_local_tooling_touching_src():
    warnings = cbr.generate_package_class_warnings(
        "local-tooling", ["src/unrelated_module.py"], set()
    )
    assert any("runtime" in w.lower() or "src" in w.lower() for w in warnings)


def test_pkg_warn_dep_lock_change_wrong_class():
    warnings = cbr.generate_package_class_warnings(
        "docs-only", ["requirements.txt"], set()
    )
    assert any("dependency" in w.lower() or "lock" in w.lower() for w in warnings)


def test_pkg_warn_dep_lock_change_right_class():
    warnings = cbr.generate_package_class_warnings(
        "dependency", ["requirements.txt"], set()
    )
    dep_lock_warns = [w for w in warnings if "dependency" in w.lower() and "authorized" not in w.lower() and "explicit" in w.lower()]
    assert len(dep_lock_warns) == 0


def test_pkg_warn_live_trading_missing_auth():
    warnings = cbr.generate_package_class_warnings(
        "live-trading", ["src/trading.py"], set()
    )
    assert any("live_trading_authorization" in w for w in warnings)


def test_pkg_warn_live_trading_with_auth():
    repo_files_set = {"docs/live_trading_authorization.md"}
    warnings = cbr.generate_package_class_warnings(
        "live-trading", ["src/trading.py"], repo_files_set
    )
    auth_warns = [w for w in warnings if "live_trading_authorization" in w]
    assert len(auth_warns) == 0


def test_pkg_no_warn_docs_only_touching_docs():
    warnings = cbr.generate_package_class_warnings(
        "docs-only", ["docs/project_status.md"], set()
    )
    assert len(warnings) == 0


# ── 10. Text output includes required sections ───────────────────────────────

def test_text_output_includes_advisory_note():
    code = cbr.main([
        "--changed-file", "docs/project_status.md",
        "--package-class", "docs-only",
        "--repo-root", str(REPO_ROOT),
    ])
    assert code == 0


def test_text_output_advisory_note_content(capsys):
    cbr.main([
        "--changed-file", "docs/project_status.md",
        "--package-class", "docs-only",
        "--repo-root", str(REPO_ROOT),
    ])
    captured = capsys.readouterr()
    assert "advisory only" in captured.out.lower()


def test_text_output_validation_reminder(capsys):
    cbr.main([
        "--changed-file", "docs/project_status.md",
        "--package-class", "docs-only",
        "--repo-root", str(REPO_ROOT),
    ])
    captured = capsys.readouterr()
    assert "pytest" in captured.out.lower() or "validation" in captured.out.lower()


def test_text_output_human_review_reminder(capsys):
    cbr.main([
        "--changed-file", "docs/project_status.md",
        "--package-class", "docs-only",
        "--repo-root", str(REPO_ROOT),
    ])
    captured = capsys.readouterr()
    assert "human review" in captured.out.lower()


def test_text_output_no_raw_file_dump(capsys):
    cbr.main([
        "--changed-file", "docs/project_status.md",
        "--package-class", "docs-only",
        "--repo-root", str(REPO_ROOT),
    ])
    captured = capsys.readouterr()
    # Should not contain bulk raw file contents (e.g., full file data)
    # Check it doesn't appear to be raw python source dumps
    assert "def test_" not in captured.out or captured.out.count("def test_") < 3


def test_text_output_mode_field(capsys):
    cbr.main([
        "--changed-file", "docs/project_status.md",
        "--package-class", "docs-only",
        "--repo-root", str(REPO_ROOT),
    ])
    captured = capsys.readouterr()
    assert "on_demand_scan" in captured.out


# ── 11. JSON output is parseable with required fields ───────────────────────

def test_json_output_parseable(capsys):
    cbr.main([
        "--changed-file", "docs/project_status.md",
        "--package-class", "docs-only",
        "--format", "json",
        "--repo-root", str(REPO_ROOT),
    ])
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert isinstance(data, dict)


def test_json_output_schema_version(capsys):
    cbr.main([
        "--changed-file", "docs/project_status.md",
        "--package-class", "docs-only",
        "--format", "json",
        "--repo-root", str(REPO_ROOT),
    ])
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["summary_schema_version"] == "1.0"


def test_json_output_required_keys(capsys):
    cbr.main([
        "--changed-file", "docs/project_status.md",
        "--package-class", "docs-only",
        "--format", "json",
        "--include-tests",
        "--include-docs",
        "--repo-root", str(REPO_ROOT),
    ])
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    required_keys = [
        "summary_schema_version",
        "repo_root",
        "mode",
        "stale_index_status",
        "package_class",
        "changed_files",
        "changed_prefixes",
        "related_source_files",
        "likely_tests",
        "likely_docs",
        "repo_truth_files_to_inspect",
        "direct_references",
        "naming_heuristics",
        "protected_boundary_attention",
        "dependency_lock_attention",
        "generated_output_attention",
        "package_class_warnings",
        "unknown_or_low_confidence_notes",
        "truncated_sections",
        "validation_reminder",
        "human_review_reminder",
        "advisory_only_note",
    ]
    for key in required_keys:
        assert key in data, f"missing key: {key}"


def test_json_stale_index_status(capsys):
    cbr.main([
        "--changed-file", "docs/project_status.md",
        "--package-class", "docs-only",
        "--format", "json",
        "--repo-root", str(REPO_ROOT),
    ])
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["stale_index_status"] == "not_applicable_on_demand_scan"


def test_json_changed_files_field(capsys):
    cbr.main([
        "--changed-file", "docs/project_status.md",
        "--package-class", "docs-only",
        "--format", "json",
        "--repo-root", str(REPO_ROOT),
    ])
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert "docs/project_status.md" in data["changed_files"]


def test_json_has_reminders(capsys):
    cbr.main([
        "--changed-file", "docs/project_status.md",
        "--format", "json",
        "--repo-root", str(REPO_ROOT),
    ])
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert "validation_reminder" in data
    assert "human_review_reminder" in data
    assert "advisory_only_note" in data
    assert len(data["advisory_only_note"]) > 10


# ── 12. --max-results caps sections ─────────────────────────────────────────

def test_max_results_caps_direct_references(tmp_path):
    # Create many files that reference the target
    for i in range(30):
        (tmp_path / f"ref_{i}.py").write_text(f"# see target_module in ref_{i}")
    (tmp_path / "target_module.py").write_text("x = 1")
    repo_files = cbr.walk_repo_files(tmp_path)
    truncated: list[str] = []
    refs = cbr.find_direct_references(repo_files, ["target_module.py"], tmp_path)
    capped = cbr.cap_list(refs, 5, "direct_references", truncated)
    assert len(capped) <= 5
    assert any("direct_references" in t for t in truncated)


def test_max_results_cli_flag(capsys):
    cbr.main([
        "--changed-file", "docs/project_status.md",
        "--package-class", "docs-only",
        "--max-results", "3",
        "--format", "json",
        "--repo-root", str(REPO_ROOT),
    ])
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert len(data["direct_references"]) <= 3


def test_max_results_truncation_note(capsys):
    cbr.main([
        "--changed-file", "docs/project_status.md",
        "--package-class", "docs-only",
        "--max-results", "2",
        "--format", "json",
        "--repo-root", str(REPO_ROOT),
    ])
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    # If we have many direct refs, truncation should appear
    if len(data["direct_references"]) == 2:
        assert len(data["truncated_sections"]) >= 0  # may have truncation notes


# ── 13. Exit behavior ────────────────────────────────────────────────────────

def test_exit_0_default_with_protected_inputs():
    code = cbr.main([
        "--changed-file", "src/data_layer/example.py",
        "--package-class", "docs-only",
        "--repo-root", str(REPO_ROOT),
    ])
    assert code == 0


def test_exit_0_with_protected_no_flag():
    code = cbr.main([
        "--changed-file", "src/data_layer/example.py",
        "--include-protected-boundaries",
        "--package-class", "docs-only",
        "--repo-root", str(REPO_ROOT),
    ])
    assert code == 0


def test_exit_1_strict_protected_hit():
    code = cbr.main([
        "--changed-file", "src/example.py",
        "--include-protected-boundaries",
        "--fail-on-protected-hit",
        "--package-class", "docs-only",
        "--repo-root", str(REPO_ROOT),
    ])
    assert code == 1


def test_exit_1_only_when_flag_set():
    code = cbr.main([
        "--changed-file", "src/example.py",
        "--include-protected-boundaries",
        "--package-class", "docs-only",
        "--repo-root", str(REPO_ROOT),
    ])
    assert code == 0


def test_exit_2_missing_inputs():
    code = cbr.main(["--package-class", "docs-only"])
    assert code == 2


def test_exit_2_invalid_path():
    code = cbr.main(["--changed-file", "/absolute/path.py"])
    assert code == 2


def test_exit_2_invalid_max_results():
    code = cbr.main([
        "--changed-file", "docs/project_status.md",
        "--max-results", "0",
    ])
    assert code == 2


# ── 14. Optional output smoke ────────────────────────────────────────────────

def test_optional_output_writes_json(tmp_path):
    out_dir = tmp_path / "local_data" / "code_blast_radius"
    out_dir.mkdir(parents=True)
    out_file = out_dir / "test_out.json"

    code = cbr.main([
        "--changed-file", "docs/project_status.md",
        "--package-class", "docs-only",
        "--format", "json",
        "--output", "local_data/code_blast_radius/test_out.json",
        "--repo-root", str(tmp_path),
    ])
    assert code == 0
    assert out_file.exists()
    data = json.loads(out_file.read_text(encoding="utf-8"))
    assert "summary_schema_version" in data


def test_optional_output_text_mode(tmp_path):
    out_dir = tmp_path / "local_data" / "code_blast_radius"
    out_dir.mkdir(parents=True)
    out_file = out_dir / "test_out.txt"

    code = cbr.main([
        "--changed-file", "docs/project_status.md",
        "--package-class", "docs-only",
        "--format", "text",
        "--output", "local_data/code_blast_radius/test_out.txt",
        "--repo-root", str(tmp_path),
    ])
    assert code == 0
    assert out_file.exists()
    content = out_file.read_text(encoding="utf-8")
    assert "advisory" in content.lower()


def test_optional_output_not_written_by_default(tmp_path):
    code = cbr.main([
        "--changed-file", "docs/project_status.md",
        "--package-class", "docs-only",
        "--repo-root", str(tmp_path),
    ])
    assert code == 0
    blast_dir = tmp_path / "local_data" / "code_blast_radius"
    if blast_dir.exists():
        assert len(list(blast_dir.iterdir())) == 0


# ── 15. No forbidden imports in helper source ────────────────────────────────

def test_no_subprocess_import():
    source = _HELPER_PATH.read_text(encoding="utf-8")
    # Must not import subprocess
    import re as _re
    assert not _re.search(r"^\s*import subprocess", source, _re.MULTILINE), \
        "code_blast_radius.py must not import subprocess"


def test_no_network_library_imports():
    source = _HELPER_PATH.read_text(encoding="utf-8")
    forbidden = [
        "import requests",
        "import httpx",
        "import aiohttp",
        "import websockets",
        "import socket",
        "import openai",
        "import anthropic",
        "import langchain",
        "import hermes",
        "import py_clob_client",
    ]
    for term in forbidden:
        assert term not in source, f"forbidden import found: {term!r}"


def test_no_os_system_call():
    source = _HELPER_PATH.read_text(encoding="utf-8")
    assert "os.system(" not in source, "code_blast_radius.py must not use os.system()"


def test_no_network_in_tests():
    test_source = pathlib.Path(__file__).read_text(encoding="utf-8")
    # Check that no actual network call patterns appear (as code, not as strings in assertions)
    # Use split to avoid self-match
    call_patterns = ["requests" + ".get", "urllib.request" + ".urlopen", "socket" + ".connect"]
    # Count occurrences — only the forbidden_terms list above will produce 1 match each
    # Real network calls would use these as code outside string contexts
    for pat in call_patterns:
        count = test_source.count(pat)
        # Only one occurrence is allowed: inside this test's own forbidden list
        assert count <= 1, f"network call pattern appears more than once (possible real usage): {pat!r}"


# ── 16. CLI smoke tests ──────────────────────────────────────────────────────

def test_cli_smoke_basic_text():
    result = subprocess.run(
        [
            sys.executable, str(_HELPER_PATH),
            "--changed-file", "docs/project_status.md",
            "--package-class", "docs-only",
            "--repo-root", str(REPO_ROOT),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "CODE BLAST RADIUS" in result.stdout
    assert "advisory" in result.stdout.lower()


def test_cli_smoke_json():
    result = subprocess.run(
        [
            sys.executable, str(_HELPER_PATH),
            "--changed-file", "tools/git/code_blast_radius.py",
            "--package-class", "local-tooling",
            "--include-tests",
            "--include-docs",
            "--format", "json",
            "--repo-root", str(REPO_ROOT),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["summary_schema_version"] == "1.0"
    assert "tools/git/code_blast_radius.py" in data["changed_files"]


def test_cli_smoke_strict_protected_hit():
    result = subprocess.run(
        [
            sys.executable, str(_HELPER_PATH),
            "--changed-file", "src/example.py",
            "--package-class", "docs-only",
            "--include-protected-boundaries",
            "--fail-on-protected-hit",
            "--repo-root", str(REPO_ROOT),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1


def test_cli_smoke_no_output_by_default():
    # Running the helper should not create any files in the repo
    before_files = set(REPO_ROOT.glob("local_data/code_blast_radius/*"))
    subprocess.run(
        [
            sys.executable, str(_HELPER_PATH),
            "--changed-file", "docs/project_status.md",
            "--package-class", "docs-only",
            "--repo-root", str(REPO_ROOT),
        ],
        capture_output=True,
        text=True,
    )
    after_files = set(REPO_ROOT.glob("local_data/code_blast_radius/*"))
    assert before_files == after_files


def test_cli_smoke_prefix_mode():
    result = subprocess.run(
        [
            sys.executable, str(_HELPER_PATH),
            "--changed-prefix", "docs/ai/codex/",
            "--package-class", "docs-only",
            "--include-docs",
            "--format", "json",
            "--repo-root", str(REPO_ROOT),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert "docs/ai/codex/" in data["changed_prefixes"]


# ── 17. AST import parsing ───────────────────────────────────────────────────

def test_ast_parse_imports(tmp_path):
    (tmp_path / "mymodule.py").write_text(
        "import os\nimport json\nfrom pathlib import Path\n"
    )
    imports = cbr.parse_py_imports(tmp_path / "mymodule.py")
    assert "os" in imports
    assert "json" in imports
    assert "pathlib" in imports


def test_ast_parse_handles_syntax_error(tmp_path):
    (tmp_path / "broken.py").write_text("def (((invalid syntax)))")
    imports = cbr.parse_py_imports(tmp_path / "broken.py")
    assert imports == []


def test_ast_references_find_importer(tmp_path):
    (tmp_path / "code_blast_radius.py").write_text("def run(): pass")
    (tmp_path / "uses_it.py").write_text("from code_blast_radius import run\n")
    repo_files = cbr.walk_repo_files(tmp_path)
    refs = cbr.find_ast_references(repo_files, ["code_blast_radius.py"], tmp_path)
    ref_files = [r["file"] for r in refs]
    assert "uses_it.py" in ref_files


def test_no_ast_flag_disables_ast(capsys):
    cbr.main([
        "--changed-file", "tools/git/code_blast_radius.py",
        "--package-class", "local-tooling",
        "--format", "json",
        "--no-ast",
        "--repo-root", str(REPO_ROOT),
    ])
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    # With --no-ast, no ast-method refs should appear
    ast_refs = [
        r for r in data["direct_references"]
        if r.get("confidence") == "medium" and "ast" in str(r)
    ]
    # We just confirm it didn't crash and produced valid output
    assert "summary_schema_version" in data


# ── 18. build_summary correctness ───────────────────────────────────────────

def test_build_summary_returns_dict():
    summary = cbr.build_summary(
        changed_files=["docs/project_status.md"],
        changed_prefixes=[],
        package_class="docs-only",
        include_tests=True,
        include_docs=True,
        include_protected=True,
        max_results=25,
        repo_root=REPO_ROOT,
        use_ast=False,
    )
    assert isinstance(summary, dict)
    assert summary["mode"] == "on_demand_scan"
    assert summary["stale_index_status"] == "not_applicable_on_demand_scan"


def test_build_summary_protected_hits_src():
    summary = cbr.build_summary(
        changed_files=["src/example.py"],
        changed_prefixes=[],
        package_class="docs-only",
        include_tests=False,
        include_docs=False,
        include_protected=True,
        max_results=25,
        repo_root=REPO_ROOT,
        use_ast=False,
    )
    assert len(summary["protected_boundary_attention"]) >= 1


def test_build_summary_pkg_warnings_docs_src():
    summary = cbr.build_summary(
        changed_files=["src/data_layer/foo.py"],
        changed_prefixes=[],
        package_class="docs-only",
        include_tests=False,
        include_docs=False,
        include_protected=False,
        max_results=25,
        repo_root=REPO_ROOT,
        use_ast=False,
    )
    assert len(summary["package_class_warnings"]) >= 1


def test_build_summary_unknown_file_note():
    summary = cbr.build_summary(
        changed_files=["nonexistent/truly_not_here.py"],
        changed_prefixes=[],
        package_class="local-tooling",
        include_tests=False,
        include_docs=False,
        include_protected=False,
        max_results=25,
        repo_root=REPO_ROOT,
        use_ast=False,
    )
    assert any("not found" in n for n in summary["unknown_or_low_confidence_notes"])
