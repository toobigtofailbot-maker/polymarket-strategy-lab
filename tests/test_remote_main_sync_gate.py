from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "git" / "preflight_sync_main.py"


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_remote_main_sync_gate_script_exists():
    assert SCRIPT.is_file()


def test_remote_main_sync_gate_contains_required_git_logic():
    text = SCRIPT.read_text(encoding="utf-8")
    required_terms = [
        '"fetch", "origin", "--prune"',
        '"switch", "main"',
        '"pull", "--ff-only", "origin", "main"',
        '"status", "--short"',
        '"rev-parse", "HEAD"',
        '"rev-parse", "origin/main"',
        "required_commit",
        "required_file",
        "cat-file",
        "rev-list",
    ]
    for term in required_terms:
        assert term in text


def test_remote_main_sync_gate_omits_forbidden_operations_and_sensitive_terms():
    text = SCRIPT.read_text(encoding="utf-8").lower()
    forbidden_terms = [
        "git checkout -b",
        "git switch -c",
        "git merge",
        "git commit",
        "git push",
        "place_order",
        "create_order",
        "post_order",
        "cancel_order",
        "private_key",
        "mnemonic",
    ]
    for term in forbidden_terms:
        assert term not in text


def test_repo_truth_requires_remote_main_sync_gate_before_wp_branch_creation():
    agents = read("AGENTS.md").lower()
    guidelines = read("docs/codex_execution_guidelines.md").lower()
    assert "remote main sync gate" in agents
    assert "before any wp branch is created" in agents
    assert "origin/main" in agents
    assert "git fetch origin --prune" in guidelines
    assert "git pull --ff-only origin main" in guidelines
    assert "head` equals `origin/main" in guidelines


def test_wp_template_and_review_checklist_include_base_verification():
    template = read("docs/work_package_template.md").lower()
    checklist = read("docs/review_checklist.md").lower()
    for term in [
        "base branch:",
        "local main commit:",
        "origin/main commit:",
        "local main equals origin/main:",
        "required previous wp commit present:",
        "required previous wp files present:",
        "remote main sync gate result:",
    ]:
        assert term in template
    for term in [
        "remote main sync gate passed",
        "local `main` equals `origin/main`",
        "previous wp merge commit/files verified",
        "no stacked wp branch",
        "no manual local merge",
    ]:
        assert term in checklist


def test_docs_prohibit_stacked_wps_and_manual_prior_wp_merges():
    combined = "\n".join(
        [
            read("AGENTS.md"),
            read("docs/codex_execution_guidelines.md"),
            read("tools/git/README.md"),
        ]
    ).lower()
    assert "do not stack" in combined
    assert "do not manually merge prior wp branches locally" in combined
    assert "stale local `main`" in combined or "stale local main" in combined
