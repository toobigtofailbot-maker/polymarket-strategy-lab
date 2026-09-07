"""
Focused docs tests for WP73 human review label workflow design.

Verifies:
- docs/human_review_label_workflow_design.md exists and covers required content
- docs/schemas/human_review_label_record_v1.example.json exists with required fields
- Schema example contains safety fields and no forbidden trading/performance fields
- Project status marks WP73 merged and WP74 as current phase
- Repo truth index includes workflow design doc, schema, and WP74 validator
- Deferred items keep fixture loader, report integration, and automation deferred
- Protected boundaries remain unchanged
- No dependency files are modified
"""

import json
import os
import re
import subprocess
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

WORKFLOW_DESIGN_DOC = os.path.join(
    REPO_ROOT, "docs", "human_review_label_workflow_design.md"
)
SCHEMA_EXAMPLE = os.path.join(
    REPO_ROOT, "docs", "schemas", "human_review_label_record_v1.example.json"
)
PROJECT_STATUS_DOC = os.path.join(REPO_ROOT, "docs", "project_status.md")
REPO_TRUTH_INDEX_DOC = os.path.join(REPO_ROOT, "docs", "repo_truth_index.md")
DEFERRED_ITEMS_DOC = os.path.join(REPO_ROOT, "docs", "deferred_items_log.md")


def _read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


# ---------------------------------------------------------------------------
# Test 1: Design doc exists
# ---------------------------------------------------------------------------


def test_human_review_label_workflow_design_doc_exists():
    assert os.path.isfile(WORKFLOW_DESIGN_DOC), (
        f"Expected {WORKFLOW_DESIGN_DOC} to exist"
    )


# ---------------------------------------------------------------------------
# Test 2: Manual research-usefulness purpose
# ---------------------------------------------------------------------------


def test_design_defines_manual_research_usefulness_purpose():
    content = _read(WORKFLOW_DESIGN_DOC)
    assert "manual analyst annotation workflow" in content.lower() or (
        "manual" in content and "research" in content and "usefulness" in content
    ), "Design doc must define manual research-usefulness purpose"
    assert "research calibration" in content.lower() or (
        "research" in content and "calibration" in content
    ), "Design doc must reference research calibration"


# ---------------------------------------------------------------------------
# Test 3: Labels are NOT trade/profitability/buy-sell labels
# ---------------------------------------------------------------------------


def test_design_states_labels_are_not_trade_labels():
    content = _read(WORKFLOW_DESIGN_DOC)
    # Must explicitly state what the labels are not
    assert "trade outcome label" in content.lower() or "not a trade" in content.lower() or (
        "trade" in content and "not" in content
    ), "Design doc must state labels are not trade outcome labels"
    assert "profitability label" in content.lower() or (
        "profitability" in content and "not" in content
    ), "Design doc must state labels are not profitability labels"
    assert "buy/sell label" in content.lower() or (
        "buy" in content and "sell" in content and "not" in content
    ), "Design doc must state labels are not buy/sell labels"


# ---------------------------------------------------------------------------
# Test 4: Label unit and identity fields
# ---------------------------------------------------------------------------


def test_design_defines_label_unit():
    content = _read(WORKFLOW_DESIGN_DOC)
    assert "market_id" in content, "Design doc must reference market_id identity field"
    assert "condition_id" in content, "Design doc must reference condition_id identity field"
    assert "question" in content, "Design doc must reference question identity field"
    assert "snapshot_time_utc" in content, "Design doc must reference snapshot_time_utc"
    assert "review_time_utc" in content, "Design doc must reference review_time_utc"
    assert "reviewer_id_or_alias" in content, "Design doc must reference reviewer_id_or_alias"


# ---------------------------------------------------------------------------
# Test 5: Allowed human review usefulness labels
# ---------------------------------------------------------------------------


def test_design_defines_allowed_usefulness_labels():
    content = _read(WORKFLOW_DESIGN_DOC)
    assert "USEFUL_RESEARCH_TARGET" in content
    assert "PARTIALLY_USEFUL_RESEARCH_TARGET" in content
    assert "NOT_USEFUL_DATA_TOO_WEAK" in content
    assert "NOT_USEFUL_RESOLUTION_TOO_AMBIGUOUS" in content
    assert "NOT_USEFUL_DUPLICATE_OR_OVERLAP" in content
    assert "NOT_REVIEWED" in content


# ---------------------------------------------------------------------------
# Test 6: Workflow states
# ---------------------------------------------------------------------------


def test_design_defines_workflow_states():
    content = _read(WORKFLOW_DESIGN_DOC)
    assert "NOT_REVIEWED" in content
    assert "IN_REVIEW" in content
    assert "LABEL_APPLIED" in content
    assert "NEEDS_SECOND_REVIEW" in content
    assert "EXCLUDED_FROM_CALIBRATION" in content


# ---------------------------------------------------------------------------
# Test 7: Confidence labels
# ---------------------------------------------------------------------------


def test_design_defines_confidence_labels():
    content = _read(WORKFLOW_DESIGN_DOC)
    assert "LOW" in content
    assert "MEDIUM" in content
    assert "HIGH" in content
    assert "NOT_APPLICABLE" in content


# ---------------------------------------------------------------------------
# Test 8: Primary reasons
# ---------------------------------------------------------------------------


def test_design_defines_primary_reasons():
    content = _read(WORKFLOW_DESIGN_DOC)
    assert "SOURCE_CLARITY" in content
    assert "RESOLUTION_RULE_CLARITY" in content
    assert "DATA_COMPLETENESS" in content
    assert "MARKET_OVERLAP_CONTEXT" in content
    assert "QUEUE_BUCKET_RELEVANCE" in content
    assert "AMBIGUITY_TOO_HIGH" in content
    assert "SOURCE_MISSING" in content
    assert "OUTCOME_MAPPING_UNCLEAR" in content
    assert "DUPLICATE_OR_OVERLAP" in content
    assert "NOT_ENOUGH_CONTEXT" in content


# ---------------------------------------------------------------------------
# Test 9: Quality gates
# ---------------------------------------------------------------------------


def test_design_defines_quality_gates():
    content = _read(WORKFLOW_DESIGN_DOC)
    assert "Quality Gate" in content or "quality gate" in content.lower(), (
        "Design doc must define quality gates"
    )
    assert "reviewer" in content.lower(), "Design doc must reference reviewer requirement"
    assert "review_time_utc" in content, "Design doc must include review_time_utc gate"
    assert "market_id" in content, "Design doc must include market_id gate"
    assert (
        "manually applied" in content.lower() or "manual" in content.lower()
    ), "Design doc must state labels remain manually applied"


# ---------------------------------------------------------------------------
# Test 10: Calibration uses and forbidden uses
# ---------------------------------------------------------------------------


def test_design_defines_calibration_uses_and_forbidden_uses():
    content = _read(WORKFLOW_DESIGN_DOC)
    # Allowed calibration uses
    assert "aggregate" in content.lower() or "aggregat" in content.lower()
    assert "data quality" in content.lower() or "data-quality" in content.lower()
    # Forbidden calibration uses
    assert "automatic scoring weight" in content.lower() or (
        "scoring weight" in content.lower() and "forbidden" in content.lower()
    ), "Design doc must state automatic scoring weight changes are forbidden"
    assert "trade signal" in content.lower() or "signals" in content.lower()
    assert (
        "paper" in content.lower() and "trading" in content.lower()
    ), "Design doc must reference paper trading as forbidden"
    assert (
        "live trading" in content.lower() or "live execution" in content.lower()
    ), "Design doc must reference live trading as forbidden"


# ---------------------------------------------------------------------------
# Test 11: Future implementation phases
# ---------------------------------------------------------------------------


def test_design_defines_future_implementation_phases():
    content = _read(WORKFLOW_DESIGN_DOC)
    assert "design" in content.lower() and "only" in content.lower(), (
        "Design doc must state this is design only"
    )
    assert "deferred" in content.lower() or "not started" in content.lower(), (
        "Design doc must indicate implementation is deferred"
    )
    assert (
        "label record validator" in content.lower() or "validator" in content.lower()
    ), "Design doc must reference future label record validator phase"
    assert (
        "fixture loader" in content.lower() or "label fixture" in content.lower()
    ), "Design doc must reference future fixture loader phase"
    assert (
        "report integration" in content.lower() or "label" in content.lower()
    ), "Design doc must reference future report integration phase"
    # Automation/LLM labeling forbidden
    assert (
        "automation" in content.lower() or "automated" in content.lower()
    ), "Design doc must mention automation boundary"
    assert (
        "llm" in content.lower() or "lm" in content.lower()
    ), "Design doc must address LLM labeling"


# ---------------------------------------------------------------------------
# Test 12: Schema/example file exists
# ---------------------------------------------------------------------------


def test_schema_example_file_exists():
    assert os.path.isfile(SCHEMA_EXAMPLE), (
        f"Expected {SCHEMA_EXAMPLE} to exist"
    )


# ---------------------------------------------------------------------------
# Test 13: Schema/example contains required safety fields
# ---------------------------------------------------------------------------


def test_schema_example_contains_required_fields():
    with open(SCHEMA_EXAMPLE, encoding="utf-8") as f:
        data = json.load(f)

    assert "_notice" in data, "Schema example must have _notice field"
    assert "_schema_version" in data, "Schema example must have _schema_version field"
    assert "identity" in data, "Schema example must have identity section"
    assert "review" in data, "Schema example must have review section"
    assert "safety" in data, "Schema example must have safety section"

    # Identity fields
    identity = data["identity"]
    assert "market_id" in identity
    assert "condition_id" in identity
    assert "question" in identity
    assert "snapshot_time_utc" in identity

    # Review fields
    review = data["review"]
    assert "review_time_utc" in review
    assert "reviewer_id_or_alias" in review
    assert "workflow_state" in review
    assert "human_review_usefulness_label" in review
    assert "confidence_level" in review
    assert "primary_reason" in review
    assert "secondary_reasons" in review
    assert "requires_followup_review" in review
    assert "review_notes" in review


# ---------------------------------------------------------------------------
# Test 14: Schema/example safety flags
# ---------------------------------------------------------------------------


def test_schema_example_contains_safety_flags():
    with open(SCHEMA_EXAMPLE, encoding="utf-8") as f:
        data = json.load(f)

    safety = data.get("safety", {})
    assert safety.get("manual_only") is True, "safety.manual_only must be True"
    assert safety.get("not_automated") is True, "safety.not_automated must be True"
    assert safety.get("no_trading_signal") is True, "safety.no_trading_signal must be True"
    assert safety.get("no_score_change") is True, "safety.no_score_change must be True"
    assert safety.get("no_execution") is True, "safety.no_execution must be True"


# ---------------------------------------------------------------------------
# Test 15: Schema/example contains no forbidden trading/performance fields
# ---------------------------------------------------------------------------


FORBIDDEN_SCHEMA_FIELDS = {
    "profit", "pnl", "roi", "expected_return", "win_rate", "sharpe",
    "buy", "sell", "entry", "exit", "position_size", "leverage",
    "trade_signal", "edge", "alpha", "opportunity", "arbitrage",
    "fill_probability", "slippage", "strategy_return", "portfolio_return",
    "execution_confidence", "tradability", "expected_value",
}


def _flatten_keys(obj, prefix=""):
    keys = set()
    if isinstance(obj, dict):
        for k, v in obj.items():
            full_key = f"{prefix}.{k}" if prefix else k
            keys.add(k.lower())
            keys |= _flatten_keys(v, full_key)
    elif isinstance(obj, list):
        for item in obj:
            keys |= _flatten_keys(item, prefix)
    return keys


def test_schema_example_no_forbidden_trading_fields():
    with open(SCHEMA_EXAMPLE, encoding="utf-8") as f:
        data = json.load(f)

    all_keys = _flatten_keys(data)
    found_forbidden = FORBIDDEN_SCHEMA_FIELDS & all_keys
    assert not found_forbidden, (
        f"Schema example contains forbidden trading/performance fields: {found_forbidden}"
    )


# ---------------------------------------------------------------------------
# Test 16: Project status marks WP74 merged and WP75 as current
# ---------------------------------------------------------------------------


def test_project_status_wp72_merged():
    content = _read(PROJECT_STATUS_DOC)
    assert "WP72" in content, "project_status.md must reference WP72"
    assert "WP73" in content, "project_status.md must reference WP73"


def test_project_status_wp73_in_merged_wps():
    content = _read(PROJECT_STATUS_DOC)
    lines = content.splitlines()
    merged_lines = [l for l in lines if "merged wps" in l.lower()]
    assert any("WP73" in l for l in merged_lines), (
        "project_status.md must list WP73 in Merged WPs (WP73 is now merged)"
    )


def test_project_status_wp74_in_merged_wps():
    content = _read(PROJECT_STATUS_DOC)
    lines = content.splitlines()
    merged_lines = [l for l in lines if "merged wps" in l.lower()]
    assert any("WP74" in l for l in merged_lines), (
        "project_status.md must list WP74 in Merged WPs (WP74 is now merged)"
    )


def test_project_status_current_phase_is_wp75():
    content = _read(PROJECT_STATUS_DOC)
    # WP75 must be the current phase after WP74 merge
    lines = content.splitlines()
    phase_lines = [l for l in lines if "current phase" in l.lower()]
    assert any("WP75" in l for l in phase_lines), (
        "project_status.md must set current phase to WP75"
    )


def test_project_status_current_branch_is_wp75():
    content = _read(PROJECT_STATUS_DOC)
    assert "wp75-local-human-review-label-fixture-loader-v1" in content, (
        "project_status.md must set current branch to wp75-local-human-review-label-fixture-loader-v1"
    )


# ---------------------------------------------------------------------------
# Test 17: Repo truth index includes new doc/schema/test
# ---------------------------------------------------------------------------


def test_repo_truth_index_includes_human_review_label_design():
    content = _read(REPO_TRUTH_INDEX_DOC)
    assert "human_review_label_workflow_design" in content, (
        "repo_truth_index.md must reference human_review_label_workflow_design"
    )


def test_repo_truth_index_includes_schema_example():
    content = _read(REPO_TRUTH_INDEX_DOC)
    assert "human_review_label_record_v1" in content, (
        "repo_truth_index.md must reference human_review_label_record_v1 schema example"
    )


def test_repo_truth_index_includes_focused_test():
    content = _read(REPO_TRUTH_INDEX_DOC)
    assert "test_human_review_label_workflow_docs" in content, (
        "repo_truth_index.md must reference test_human_review_label_workflow_docs"
    )


def test_repo_truth_index_includes_validator_module():
    content = _read(REPO_TRUTH_INDEX_DOC)
    assert "human_review_label_validation" in content, (
        "repo_truth_index.md must reference human_review_label_validation (WP74 validator)"
    )


def test_repo_truth_index_includes_validator_test():
    content = _read(REPO_TRUTH_INDEX_DOC)
    assert "test_human_review_label_validation" in content, (
        "repo_truth_index.md must reference test_human_review_label_validation (WP74 tests)"
    )


def test_repo_truth_index_includes_fixture_loader_module():
    content = _read(REPO_TRUTH_INDEX_DOC)
    assert "human_review_label_fixture_loader" in content, (
        "repo_truth_index.md must reference human_review_label_fixture_loader (WP75 loader)"
    )


def test_repo_truth_index_includes_fixture_loader_test():
    content = _read(REPO_TRUTH_INDEX_DOC)
    assert "test_human_review_label_fixture_loader" in content, (
        "repo_truth_index.md must reference test_human_review_label_fixture_loader (WP75 tests)"
    )


# ---------------------------------------------------------------------------
# Test 18: Deferred items keep implementation and automation deferred
# ---------------------------------------------------------------------------


def test_deferred_items_human_review_label_implementation_deferred():
    content = _read(DEFERRED_ITEMS_DOC)
    assert "WP73-D001" in content, "deferred_items_log.md must have WP73-D001"
    assert "WP73-D002" in content, "deferred_items_log.md must have WP73-D002"
    assert "WP73-D003" in content, "deferred_items_log.md must have WP73-D003"
    assert "WP73-D004" in content, "deferred_items_log.md must have WP73-D004"


def test_deferred_items_label_validator_deferred():
    content = _read(DEFERRED_ITEMS_DOC)
    # WP73-D001 covers human review label record validator
    assert "label record validator" in content.lower() or (
        "validator" in content and "WP73-D001" in content
    ), "deferred_items_log.md must keep label validator deferred"


def test_deferred_items_automated_labeling_deferred():
    content = _read(DEFERRED_ITEMS_DOC)
    # WP73-D004 covers automated/LLM labeling
    assert "WP73-D004" in content, "deferred_items_log.md must have WP73-D004"
    assert (
        "automated" in content.lower() or "llm" in content.lower()
    ), "deferred_items_log.md must reference automated/LLM labeling as deferred/forbidden"


# ---------------------------------------------------------------------------
# Test 19: Protected boundaries remain unchanged
# ---------------------------------------------------------------------------


def test_project_status_live_trading_disabled():
    content = _read(PROJECT_STATUS_DOC)
    assert "DISABLED" in content or "live trading" in content.lower(), (
        "project_status.md must keep live trading disabled"
    )
    # Check live trading status line
    lines = content.splitlines()
    live_trading_lines = [l for l in lines if "live trading status" in l.lower()]
    assert any("DISABLED" in l for l in live_trading_lines), (
        "project_status.md must have Live trading status: DISABLED"
    )


def test_project_status_credentials_not_used():
    content = _read(PROJECT_STATUS_DOC)
    lines = content.splitlines()
    cred_lines = [l for l in lines if "credentials status" in l.lower()]
    assert any("NOT_USED" in l for l in cred_lines), (
        "project_status.md must have Credentials status: NOT_USED"
    )


def test_project_status_execution_not_started():
    content = _read(PROJECT_STATUS_DOC)
    lines = content.splitlines()
    exec_lines = [l for l in lines if "execution status" in l.lower()]
    assert any("NOT_STARTED" in l for l in exec_lines), (
        "project_status.md must have Execution status: NOT_STARTED"
    )


def test_project_status_scheduler_not_started():
    content = _read(PROJECT_STATUS_DOC)
    lines = content.splitlines()
    sched_lines = [l for l in lines if "scheduler status" in l.lower()]
    assert any("NOT_STARTED" in l for l in sched_lines), (
        "project_status.md must have Scheduler status: NOT_STARTED"
    )


def test_project_status_bot_loop_not_started():
    content = _read(PROJECT_STATUS_DOC)
    lines = content.splitlines()
    bot_lines = [l for l in lines if "bot loop status" in l.lower()]
    assert any("NOT_STARTED" in l for l in bot_lines), (
        "project_status.md must have Bot loop status: NOT_STARTED"
    )


def test_project_status_hermes_forbidden():
    content = _read(PROJECT_STATUS_DOC)
    lines = content.splitlines()
    hermes_lines = [l for l in lines if "agent execution authority" in l.lower()]
    assert any("FORBIDDEN" in l for l in hermes_lines), (
        "project_status.md must have Agent execution authority: FORBIDDEN"
    )


# ---------------------------------------------------------------------------
# Test 20: WP73 scope verification and WP74 boundary checks
# ---------------------------------------------------------------------------


def test_wp73_design_files_exist():
    """WP73 created these files — verify they are still present after WP74."""
    assert os.path.isfile(WORKFLOW_DESIGN_DOC), (
        "WP73 human_review_label_workflow_design.md must exist"
    )
    assert os.path.isfile(SCHEMA_EXAMPLE), (
        "WP73 human_review_label_record_v1.example.json must exist"
    )
    docs_test = os.path.join(REPO_ROOT, "tests", "test_human_review_label_workflow_docs.py")
    assert os.path.isfile(docs_test), (
        "WP73 test_human_review_label_workflow_docs.py must exist"
    )


def test_wp74_validator_file_exists():
    """WP74 adds the local human review label validator source file."""
    validator = os.path.join(
        REPO_ROOT, "src", "data_layer", "human_review_label_validation.py"
    )
    assert os.path.isfile(validator), (
        "WP74 src/data_layer/human_review_label_validation.py must exist"
    )


def test_wp74_validator_test_file_exists():
    """WP74 adds the focused validator test file."""
    val_test = os.path.join(
        REPO_ROOT, "tests", "test_human_review_label_validation.py"
    )
    assert os.path.isfile(val_test), (
        "WP74 tests/test_human_review_label_validation.py must exist"
    )


def test_wp75_fixture_loader_file_exists():
    """WP75 adds the local human review label fixture loader source file."""
    loader = os.path.join(
        REPO_ROOT, "src", "data_layer", "human_review_label_fixture_loader.py"
    )
    assert os.path.isfile(loader), (
        "WP75 src/data_layer/human_review_label_fixture_loader.py must exist"
    )


def test_wp75_fixture_loader_test_file_exists():
    """WP75 adds the focused fixture loader test file."""
    loader_test = os.path.join(
        REPO_ROOT, "tests", "test_human_review_label_fixture_loader.py"
    )
    assert os.path.isfile(loader_test), (
        "WP75 tests/test_human_review_label_fixture_loader.py must exist"
    )


def test_no_dependency_files_modified():
    """WP75 must not change dependency or lock files."""
    result = subprocess.run(
        ["git", "diff", "--name-only", "origin/main", "HEAD"],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    changed = result.stdout.strip().splitlines()
    dep_changes = [
        f for f in changed
        if f in ("requirements.txt", "pyproject.toml", "package.json", "package-lock.json",
                 "poetry.lock", "Pipfile.lock", "setup.py", "setup.cfg")
    ]
    if "docs/status_entries/WP169.md" in changed:
        # WP169 explicitly authorizes exactly one dependency file, pyproject.toml
        # (the exact websockets==17.1 install-not-vendor pin for the public data plane).
        assert dep_changes == ["pyproject.toml"], dep_changes
        return
    if "docs/status_entries/WP168.md" in changed:
        # WP168 explicitly authorizes exactly one dependency file, pyproject.toml.
        assert dep_changes == ["pyproject.toml"], dep_changes
        return
    if "docs/status_entries/WP167.md" in changed:
        # WP167 explicitly authorizes exactly one dependency file, pyproject.toml.
        assert dep_changes == ["pyproject.toml"], dep_changes
        return
    assert not dep_changes, (
        f"WP75 must not modify dependency files. Found: {dep_changes}"
    )


def _spec_authorized_tool_paths(changed):
    """Governance-tool paths authorized by the current WP machine spec(s).

    Any WP whose status entry is in ``changed`` contributes the ``tools/`` paths declared
    in its machine-spec ``required_changed_files``. Bounded and deterministic; replaces
    the earlier WP159-only tool-scope exception so future governance tooling needs no
    bespoke per-WP allowance.
    """
    authorized = set()
    for path in changed:
        match = re.fullmatch(r"docs/status_entries/(WP[0-9A-Za-z]+)\.md", path)
        if match is None:
            continue
        spec_path = os.path.join(
            REPO_ROOT, "docs", "wp_specs", match.group(1), "wp_spec.json"
        )
        if not os.path.isfile(spec_path):
            continue
        try:
            with open(spec_path, encoding="utf-8") as handle:
                spec = json.load(handle)
        except (OSError, ValueError):
            continue
        for changed_file in spec.get("scope", {}).get("required_changed_files", []):
            if isinstance(changed_file, str) and changed_file.startswith("tools/"):
                authorized.add(changed_file)
    return authorized


def test_historical_tool_scope_guard_uses_current_wp_spec_authority():
    """The tool-scope guard derives authorized governance-tool paths from the active WP
    machine spec rather than a WP159-only exception."""
    authorized = _spec_authorized_tool_paths({"docs/status_entries/WP168G.md"})
    assert "tools/wp/wp_readiness_gate.py" in authorized
    assert "tools/wp/wp_spec_guard.py" in authorized
    # WP159 remains covered through the same spec-derived mechanism, not a hardcode.
    wp159_authorized = _spec_authorized_tool_paths({"docs/status_entries/WP159.md"})
    assert "tools/wp/wp_spec_guard.py" in wp159_authorized
    # No WP status entry changed -> no governance-tool paths are authorized.
    assert _spec_authorized_tool_paths({"docs/project_status.md"}) == set()


def test_no_tools_files_modified():
    """WP75 must not modify tools/ files."""
    result = subprocess.run(
        ["git", "diff", "--name-only", "origin/main", "HEAD"],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    changed = result.stdout.strip().splitlines()
    allowed_tools_changes = {
        "tools/hermes_candidate_review_manual_export_cli.py",
    }
    if (
        "docs/status_entries/WP160.md" in changed
        or "docs/status_entries/WP161.md" in changed
        or "docs/status_entries/WP162.md" in changed
        or "docs/status_entries/WP163.md" in changed
        or "docs/status_entries/WP164.md" in changed
        or "docs/status_entries/WP165.md" in changed
        or "docs/status_entries/WP166.md" in changed
    ):
        # Functional WP160/WP161/WP162/WP163/WP164/WP165/WP166 packages add no
        # tools/ files within their exact authorized scopes.
        assert not [
            f
            for f in changed
            if f.startswith("tools/") and f not in allowed_tools_changes
        ]
        return
    # Authorize governance-tool changes from the current WP machine spec rather than a
    # bespoke WP159-only exception. WP159 (and any later governance WP, including
    # WP168G) is covered because its spec's required_changed_files declare its tools.
    allowed_tools_changes.update(_spec_authorized_tool_paths(changed))
    tools_changes = [
        f for f in changed
        if f.startswith("tools/") and f not in allowed_tools_changes
    ]
    assert not tools_changes, (
        f"WP75 must not modify tools/ files. Found: {tools_changes}"
    )
