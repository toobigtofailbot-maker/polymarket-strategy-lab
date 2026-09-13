from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    "AGENTS.md",
    "README.md",
    ".gitignore",
    "pyproject.toml",
    "docs/repo_truth_index.md",
    "docs/project_charter.md",
    "docs/project_status.md",
    "docs/source_repo_registry.md",
    "docs/repo_reuse_strategy.md",
    "docs/architecture_principles.md",
    "docs/strategy_module_registry.md",
    "docs/data_semantics.md",
    "docs/wallet_copy_trading_semantics.md",
    "docs/risk_semantics.md",
    "docs/live_trading_authorization.md",
    "docs/security_and_secrets.md",
    "docs/codex_execution_guidelines.md",
    "docs/work_package_template.md",
    "docs/review_checklist.md",
    "docs/testing_requirements.md",
    ".github/pull_request_template.md",
    "audits/source_repos/README.md",
    "tests/test_repo_truth_docs.py",
    "tests/test_no_live_mode_by_default.py",
    "tests/test_no_secret_placeholders.py",
]


def test_required_repo_truth_files_exist():
    missing = [path for path in REQUIRED_FILES if not (ROOT / path).is_file()]
    assert missing == []


def test_wp171g_repo_truth_transition_is_registered():
    index = (ROOT / "docs" / "repo_truth_index.md").read_text(encoding="utf-8")
    deferred = (ROOT / "docs" / "deferred_items_log.md").read_text(encoding="utf-8")
    assert "WP171 merged: PR #172" in index
    assert "a650c08ab233e47beca7565a5bb8df11a4f41d02" in index
    assert "d6a15e4007fe3ced5a7d059ec3fcdec496d2dc7d" in index
    assert "FAST, RUNTIME, and PROTECTED" in index
    assert "Historical valid certified packages remain accepted" in index
    assert "normative machine-readable authority mirror" in index
    assert "all sixteen authority booleans" in index
    assert "certificate/package guard as not run" in index
    assert "WP172 — Alpha + Executable Edge MVP" in index
    assert "not started by WP171G" in index
    assert "WP171G Lean Agent Execution Governance Deferred Items" in deferred
    assert "parked local WP172 worktree remains separate and" in deferred
    assert "untouched" in deferred
    assert "authority-divergence finding is resolved" in deferred
