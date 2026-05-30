import pathlib
import re


REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent


def read(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def test_closeout_doc_exists():
    assert (REPO_ROOT / "docs/ai/codex/TOKEN_EFFICIENCY_SEQUENCE_CLOSEOUT.md").exists()


def test_closeout_status_phrases_present():
    text = read("docs/ai/codex/TOKEN_EFFICIENCY_SEQUENCE_CLOSEOUT.md")
    for phrase in [
        "DOCS_ONLY_CLOSEOUT",
        "Codex and Claude Code",
        "NO_RUNTIME_CHANGE",
        "NO_NEW_TOOLING",
        "NO_DEPENDENCY_CHANGE",
        "NO_NETWORK",
        "NO_VALIDATION_WEAKENING",
        "NO_PROTECTED_BOUNDARY_CHANGE",
    ]:
        assert phrase in text


def test_closeout_sequence_references_wp28_through_wp36():
    text = read("docs/ai/codex/TOKEN_EFFICIENCY_SEQUENCE_CLOSEOUT.md")
    for wp in range(28, 37):
        assert f"WP{wp}" in text


def test_closeout_helper_inventory_paths_present():
    text = read("docs/ai/codex/TOKEN_EFFICIENCY_SEQUENCE_CLOSEOUT.md")
    for path in [
        "tools/git/diff_scope_summary.py",
        "tools/validation/validation_output_summary.py",
        "tools/git/code_blast_radius.py",
        "tools/git/status_snapshot.py",
        "docs/ai/codex/DIFF_SCOPE_SUMMARY_HELPER.md",
        "docs/ai/codex/VALIDATION_OUTPUT_SUMMARY_HELPER.md",
        "docs/ai/codex/CODE_INDEX_BLAST_RADIUS_HELPER.md",
        "docs/ai/codex/MEMORY_STATUS_SNAPSHOT_HELPER.md",
    ]:
        assert path in text


def test_closeout_future_helper_usage_order_present():
    text = read("docs/ai/codex/TOKEN_EFFICIENCY_SEQUENCE_CLOSEOUT.md")
    for phrase in [
        "WP drafting",
        "PR review",
        "status snapshot",
        "diff/scope helper",
        "code blast-radius",
        "validation-output helper",
    ]:
        assert phrase in text


def test_closeout_advisory_only_limits_present():
    text = read("docs/ai/codex/TOKEN_EFFICIENCY_SEQUENCE_CLOSEOUT.md")
    for phrase in [
        "Helpers are advisory only",
        "do not replace repo truth",
        "do not replace tests",
        "do not replace security checks",
        "do not replace direct file inspection",
        "do not authorize merge-ready status",
        "do not authorize protected work",
    ]:
        assert phrase in text


def test_closeout_deferred_helper_items_present():
    text = read("docs/ai/codex/TOKEN_EFFICIENCY_SEQUENCE_CLOSEOUT.md")
    for phrase in [
        "WP30-D001",
        "WP32-D001",
        "WP34-D001",
        "WP36-D001",
        "WP36-D002",
        "broader command-output compression",
        "runner mode",
        "persistent code-index snapshot/index",
        "Markdown snapshot output",
        "input file hashes",
    ]:
        assert phrase in text


def test_closeout_protected_boundary_reaffirmations_present():
    text = read("docs/ai/codex/TOKEN_EFFICIENCY_SEQUENCE_CLOSEOUT.md")
    for phrase in [
        "Hermes not installed",
        "Agent runtime not started",
        "Agent execution authority forbidden",
        "Fully autonomous trading agent excluded",
        "Live trading disabled",
        "Credentials not used",
        "Scheduler not started",
        "Bot loop not started",
        "Authenticated client forbidden",
        "Official client remains not a runtime dependency",
    ]:
        assert phrase in text


def test_closeout_resumption_gate_present():
    text = read("docs/ai/codex/TOKEN_EFFICIENCY_SEQUENCE_CLOSEOUT.md")
    for phrase in [
        "WP37 does not resume advisory-agent/Hermes/product plan",
        "next WP must be selected explicitly",
        "WP38 - Local Advisory Handoff Package",
        "WP38 - Token Efficiency Closeout Follow-Up",
        "do not jump to database/dashboard/strategy/paper trading/live trading/wallet/scheduler/Hermes install/agent runtime",
    ]:
        assert phrase in text


def test_repo_truth_index_indexes_closeout_doc_and_numbering_is_sequential():
    text = read("docs/repo_truth_index.md")
    assert "docs/ai/codex/TOKEN_EFFICIENCY_SEQUENCE_CLOSEOUT.md" in text
    numbers = []
    in_hierarchy = False
    for line in text.splitlines():
        if line.strip() == "## Authority Hierarchy":
            in_hierarchy = True
            continue
        if in_hierarchy and line.startswith("Codex workflow docs"):
            break
        match = re.match(r"^(\d+)\. `", line)
        if match:
            numbers.append(int(match.group(1)))
    assert numbers == list(range(1, len(numbers) + 1))


def test_operating_model_and_readme_reference_closeout_doc():
    for path in [
        "docs/ai/codex/TOKEN_EFFICIENCY_OPERATING_MODEL.md",
        "docs/ai/codex/README.md",
    ]:
        assert "docs/ai/codex/TOKEN_EFFICIENCY_SEQUENCE_CLOSEOUT.md" in read(path)


def test_project_status_references_wp37_and_next_gate():
    text = read("docs/project_status.md")
    for phrase in [
        "WP37 - Token Efficiency Sequence Closeout / Repo Truth Consolidation",
        "WP36",
        "WP38 - Local Advisory Handoff Package",
        "WP38 - Token Efficiency Closeout Follow-Up",
    ]:
        assert phrase in text


def test_no_new_forbidden_implementation_paths_exist():
    forbidden_paths = [
        "tools/git/token_efficiency_closeout.py",
        "src/agents",
        "src/agent_layer",
        "tools/hermes",
        "agent_runtime",
        "agent_memory",
        "local_data/token_efficiency",
    ]
    for path in forbidden_paths:
        assert not (REPO_ROOT / path).exists()
    assert not list((REPO_ROOT / "tools").glob("token_efficiency*"))


def test_dependency_files_do_not_add_forbidden_dependencies():
    dependency_files = [
        "pyproject.toml",
        "requirements.txt",
        "requirements-dev.txt",
        "package.json",
        "package-lock.json",
        "Cargo.toml",
        "Cargo.lock",
    ]
    forbidden = [
        "openai",
        "anthropic",
        "langchain",
        "hermes",
        "token-savior",
        "code-review-graph",
        "tree-sitter",
        "networkx",
        "graphviz",
        "chromadb",
        "llama-index",
        "mem0",
        "rich",
        "click",
        "typer",
    ]
    for file_name in dependency_files:
        path = REPO_ROOT / file_name
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8").lower()
        for package in forbidden:
            assert package not in text, f"{package} present in {file_name}"
