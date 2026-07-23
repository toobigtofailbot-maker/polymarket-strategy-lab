import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DOC = REPO_ROOT / (
    "docs/local_research_workflow_value_validation_and_"
    "paper_trading_readiness_decision.md"
)
STATUS = REPO_ROOT / "docs/status_entries/WP150.md"
PROJECT_STATUS = REPO_ROOT / "docs/project_status.md"
REPO_TRUTH = REPO_ROOT / "docs/repo_truth_index.md"

TITLE = "# Local Research Workflow Value Validation And Paper-Trading Readiness Decision"
HEADINGS = [
    TITLE,
    "## Purpose",
    "## Position After WP149",
    "## Authority And Non-Authority",
    "## Repository Inputs Reviewed",
    "## Discovery Method",
    "## Capability-State Definitions",
    "## Local Research Workflow Inventory",
    "## Implemented Versus Contract-Only Capabilities",
    "## Research-Value Framework",
    "## Metric-To-Evidence Grounding Matrix",
    "## Research Throughput",
    "## Candidate Rejection Quality",
    "## Hypothesis Quality",
    "## Reproducibility",
    "## Strategy-Validation Handoff Quality",
    "## Operator Burden",
    "## Value-Measurement Readiness",
    "## Paper-Trading Readiness Method",
    "## Market-Data Readiness",
    "## Replay And Fill-Model Readiness",
    "## Strategy-Input Readiness",
    "## Paper Order-Lifecycle Readiness",
    "## Portfolio And Accounting Readiness",
    "## Risk And Safety Readiness",
    "## Observability Readiness",
    "## Reconciliation Readiness",
    "## Operational Readiness",
    "## Mandatory Readiness Matrix",
    "## Blocker Register",
    "## Paper-Trading Implementation Readiness",
    "## Productive Next Phase",
    "## Promotion Gates",
    "## Explicit Deferred Capabilities",
    "## Output Surface Inventory",
    "## Forbidden Interpretations",
    "## Future WP151 Boundary",
    "## Decision",
    "## Non-Authority Statement",
]
CAPABILITY_STATES = {
    "IMPLEMENTED_AND_TESTED",
    "IMPLEMENTED_LIMITED_OR_MANUAL",
    "CONTRACT_OR_RUNBOOK_ONLY",
    "SYNTHETIC_TEST_ONLY",
    "ABSENT",
    "EVIDENCE_INSUFFICIENT",
}
MEASUREMENT_STATES = {
    "MEASURED",
    "MEASURABLE_NOT_YET_MEASURED",
    "NOT_CURRENTLY_MEASURABLE",
}
READINESS_STATES = {
    "READY",
    "PARTIALLY_READY",
    "NOT_READY",
    "ABSENT",
    "EVIDENCE_INSUFFICIENT",
}
DECISION_TOKENS = (
    "Remote provider track status:\nDEFERRED_PENDING_MATERIAL_NEW_EVIDENCE",
    "Automatic periodic provider re-research:\nFORBIDDEN",
    "Deferral review cadence:\nEVENT_DRIVEN_ONLY",
    "Remote configurations eligible:\n0",
    "Remote configurations shortlisted:\n0",
    "Provider/model selection:\nNOT MADE",
    "Remote controlled experiment readiness:\nNOT_READY",
    "Local research workflow value-validation status:\n"
    "PARTIALLY_READY_BLOCKERS_IDENTIFIED",
    "Research-value metric records:\n39",
    "Research-value metrics measured:\n0",
    "Research-value metrics measurable but not yet measured:\n22",
    "Research-value metrics not currently measurable:\n17",
    "Research-value blockers:\n7",
    "Paper-trading implementation readiness:\nNOT_READY_FOUNDATIONAL_GAPS",
    "Paper-trading execution:\nNOT AUTHORIZED",
    "Live-trading execution:\nFORBIDDEN",
    "Capital at risk:\nUSD 0",
    "Orders submitted:\n0",
    "Credentials created/used:\n0",
    "External model calls:\n0",
    "Next phase:\nLOCAL_RESEARCH_WORKFLOW_VALUE_MEASUREMENT_HARNESS_CONTRACT",
    "WP151 requires separate approval",
)
STAGE_FIELDS = (
    "stage_id",
    "stage_name",
    "current_state",
    "canonical_artifact",
    "input",
    "output",
    "deterministic_validation",
    "human_review",
    "persistence",
    "network",
    "known_limitations",
    "paper_trading_relevance",
)
BLOCKER_FIELDS = (
    "blocker_id",
    "domain",
    "classification",
    "priority",
    "current_state",
    "required_state",
    "why_blocking",
    "prerequisite",
    "suggested_future_wp",
    "authority_required",
)
METRIC_GROUNDING_FIELDS = (
    "metric_id",
    "dimension",
    "metric",
    "measurement_state",
    "current_artifact",
    "exact_current_field_or_derivation",
    "current_corpus_or_rubric_coverage",
    "blocker",
)


def _read(path: Path = DOC) -> str:
    return path.read_text(encoding="utf-8")


def _normalized(text: str) -> str:
    return " ".join(text.split())


def _section(text: str, heading: str, next_heading: str) -> str:
    return text.split(heading, 1)[1].split(next_heading, 1)[0]


def _table(section: str) -> tuple[list[str], list[list[str]]]:
    table_lines = [line for line in section.splitlines() if line.startswith("|")]
    assert len(table_lines) >= 2
    header = [cell.strip() for cell in table_lines[0].strip("|").split("|")]
    rows = []
    for line in table_lines[2:]:
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if cells and set("".join(cells)) <= {"-", ":"}:
            continue
        rows.append(cells)
    return header, rows


def test_exact_title_heading_order_and_decision_tokens():
    text = _read()
    headings = [
        line
        for line in text.splitlines()
        if line.startswith("# ") or line.startswith("## ")
    ]
    assert headings == HEADINGS
    assert text.startswith(TITLE + "\n")
    normalized = _normalized(text)
    for token in DECISION_TOKENS:
        assert _normalized(token) in normalized


def test_wp149_remote_deferral_is_preserved_without_research_or_activation():
    text = _read()
    prior = _section(text, "## Position After WP149", "## Authority And Non-Authority")
    for phrase in (
        "DEFERRED_PENDING_MATERIAL_NEW_EVIDENCE",
        "Automatic periodic provider re-research:\nFORBIDDEN",
        "Deferral review cadence:\nEVENT_DRIVEN_ONLY",
        "Remote configurations eligible:\n0",
        "Remote configurations shortlisted:\n0",
        "Provider/model selection:\nNOT MADE",
        "Remote controlled experiment readiness:\nNOT_READY",
        "provider-independent",
        "no external research",
        "No external model call",
    ):
        assert phrase in prior


def test_twenty_stage_inventory_has_complete_fields_and_allowed_states():
    text = _read()
    inventory = _section(
        text,
        "## Local Research Workflow Inventory",
        "## Implemented Versus Contract-Only Capabilities",
    )
    header, rows = _table(inventory)
    assert tuple(header) == STAGE_FIELDS
    assert len(rows) == 20
    assert [row[0] for row in rows] == [f"LRW-{number:02d}" for number in range(1, 21)]
    assert all(len(row) == len(STAGE_FIELDS) for row in rows)
    assert all(all(cell for cell in row) for row in rows)
    assert {row[2] for row in rows} <= CAPABILITY_STATES
    assert {row[2] for row in rows} == {
        "IMPLEMENTED_AND_TESTED",
        "IMPLEMENTED_LIMITED_OR_MANUAL",
        "CONTRACT_OR_RUNBOOK_ONLY",
        "SYNTHETIC_TEST_ONLY",
    }
    assert sum(row[2] == "IMPLEMENTED_AND_TESTED" for row in rows) == 13
    assert sum(row[2] == "IMPLEMENTED_LIMITED_OR_MANUAL" for row in rows) == 4
    assert sum(row[2] == "CONTRACT_OR_RUNBOOK_ONLY" for row in rows) == 2
    assert sum(row[2] == "SYNTHETIC_TEST_ONLY" for row in rows) == 1


def test_capability_matrix_uses_only_allowed_states_and_separates_nonimplementation():
    text = _read()
    section = _section(
        text,
        "## Implemented Versus Contract-Only Capabilities",
        "## Research-Value Framework",
    )
    header, rows = _table(section)
    assert header == [
        "Capability",
        "Canonical artifact",
        "Tests",
        "Data dependency",
        "Authority",
        "State",
        "Limitations",
    ]
    assert len(rows) >= 19
    assert all(len(row) == 7 for row in rows)
    assert {row[5] for row in rows} <= CAPABILITY_STATES
    by_capability = {row[0]: row for row in rows}
    assert by_capability["research workflow runbooks"][5] == "CONTRACT_OR_RUNBOOK_ONLY"
    assert by_capability["assisted-research dry-run harness"][5] == "SYNTHETIC_TEST_ONLY"
    assert by_capability["paper order lifecycle"][5] == "ABSENT"
    assert by_capability["paper fill model"][5] == "ABSENT"
    assert by_capability["paper portfolio/accounting"][5] == "ABSENT"
    assert by_capability["deterministic paper risk"][5] == "ABSENT"
    assert "does not convert" in section
    assert "Scaffold boundary tests prove absence" in section


def test_every_research_value_metric_is_grounded_and_state_totals_are_derived():
    text = _read()
    section = _section(
        text,
        "## Metric-To-Evidence Grounding Matrix",
        "## Research Throughput",
    )
    header, rows = _table(section)
    assert tuple(header) == METRIC_GROUNDING_FIELDS
    assert len(rows) == 39
    assert len({row[0] for row in rows}) == 39
    assert all(len(row) == len(METRIC_GROUNDING_FIELDS) for row in rows)
    assert all(all(cell for cell in row) for row in rows)
    assert {row[3] for row in rows} <= MEASUREMENT_STATES

    state_counts = {
        state: sum(row[3] == state for row in rows)
        for state in MEASUREMENT_STATES
    }
    assert state_counts == {
        "MEASURED": 0,
        "MEASURABLE_NOT_YET_MEASURED": 22,
        "NOT_CURRENTLY_MEASURABLE": 17,
    }

    for row in rows:
        artifact_paths = re.findall(r"`([^`]+)`", row[4])
        assert artifact_paths, row[0]
        for raw_path in artifact_paths:
            path = raw_path.split("::", 1)[0]
            assert (REPO_ROOT / path).exists(), (row[0], path)

    measurable_rows = [
        row for row in rows if row[3] == "MEASURABLE_NOT_YET_MEASURED"
    ]
    for row in measurable_rows:
        assert "NONE" not in row[4]
        assert "NONE" not in row[5]
        assert "NONE" not in row[6]
        coverage_paths = re.findall(r"`([^`]+)`", row[6])
        assert coverage_paths, row[0]
        for raw_path in coverage_paths:
            path = raw_path.split("::", 1)[0]
            if path.startswith(("src/", "tests/", "docs/")):
                assert (REPO_ROOT / path).exists(), (row[0], path)
        assert "`" in row[5] or "deterministic derivation:" in row[5]
        assert "future" not in (row[4] + row[5] + row[6]).lower()

    unsupported_rows = [
        row for row in rows if row[3] == "NOT_CURRENTLY_MEASURABLE"
    ]
    assert all("NONE" in row[5] for row in unsupported_rows)
    assert all("NONE" in row[6] for row in unsupported_rows)

    totals = _normalized(section)
    for token in (
        "Metric records: 39",
        "MEASURED: 0",
        "MEASURABLE_NOT_YET_MEASURED: 22",
        "NOT_CURRENTLY_MEASURABLE: 17",
        "Measurable metrics without exact current field/derivation: 0",
        "Measurable metrics without bounded corpus/rubric coverage: 0",
        "Future-only fields used as current evidence: 0",
    ):
        assert token in totals

    framework = _section(
        text, "## Research-Value Framework", "## Metric-To-Evidence Grounding Matrix"
    )
    normalized_framework = _normalized(framework)
    assert "Research value means" in normalized_framework
    assert "It is not profitability" in normalized_framework
    assert "`MEASURED` requires an actual measurement receipt." in normalized_framework
    assert (
        "WP150 records no `MEASURED` result and no measurement receipt."
        in normalized_framework
    )
    assert "future field" in normalized_framework
    assert "free-form concept" in normalized_framework


def test_future_runbook_free_form_wp142_and_wp151_evidence_fail_closed():
    text = _read()
    matrix = _section(
        text,
        "## Metric-To-Evidence Grounding Matrix",
        "## Research Throughput",
    )
    _, rows = _table(matrix)
    by_metric = {row[2]: row for row in rows}

    horizon = by_metric["horizon"]
    assert horizon[3] == "NOT_CURRENTLY_MEASURABLE"
    assert "future horizon field" in horizon[6]

    manual_steps = by_metric["manual steps"]
    expertise = by_metric["expertise"]
    assert manual_steps[3] == "NOT_CURRENTLY_MEASURABLE"
    assert expertise[3] == "NOT_CURRENTLY_MEASURABLE"
    assert "runbook mention is not structured completion evidence" in manual_steps[6]
    assert "runbook instruction is not an operator study" in expertise[6]

    mechanism = by_metric["expected mechanism"]
    assert mechanism[3] == "NOT_CURRENTLY_MEASURABLE"
    assert "free-form `research_question` does not prove mechanism" in mechanism[6]

    schema_version = by_metric["schema/version"]
    assert schema_version[3] == "NOT_CURRENTLY_MEASURABLE"
    assert "not all 20 workflow stages" in schema_version[6]

    readiness = _section(
        text,
        "## Value-Measurement Readiness",
        "## Paper-Trading Readiness Method",
    )
    normalized_readiness = _normalized(readiness)
    assert "Future WP151 field/schema requirements cannot retroactively" in normalized_readiness
    assert "WP142 covers a synthetic assisted-research experiment surface" in normalized_readiness


def test_overall_value_readiness_is_derived_from_grounded_metric_states():
    text = _read()
    matrix = _section(
        text,
        "## Metric-To-Evidence Grounding Matrix",
        "## Research Throughput",
    )
    _, rows = _table(matrix)
    measured = sum(row[3] == "MEASURED" for row in rows)
    measurable = sum(row[3] == "MEASURABLE_NOT_YET_MEASURED" for row in rows)
    unsupported = sum(row[3] == "NOT_CURRENTLY_MEASURABLE" for row in rows)
    if measurable and not unsupported:
        derived = "READY_FOR_BOUNDED_VALUE_MEASUREMENT_IMPLEMENTATION"
    elif measurable and unsupported:
        derived = "PARTIALLY_READY_BLOCKERS_IDENTIFIED"
    else:
        derived = "NOT_READY_FOUNDATIONAL_GAPS"
    assert measured == 0
    assert derived == "PARTIALLY_READY_BLOCKERS_IDENTIFIED"
    assert (
        f"Local research workflow value-validation status:\n{derived}"
        in text
    )
    assert (
        "READY_FOR_BOUNDED_VALUE_MEASUREMENT_IMPLEMENTATION"
        not in _section(
            text,
            "## Value-Measurement Readiness",
            "## Paper-Trading Readiness Method",
        )
    )


def test_value_measurement_readiness_is_bounded_local_and_not_implemented():
    text = _read()
    section = _section(
        text,
        "## Value-Measurement Readiness",
        "## Paper-Trading Readiness Method",
    )
    for phrase in (
        "22 currently measurable but unmeasured metrics",
        "17 metrics that fail closed as not currently measurable",
        "structured hypothesis mechanism/horizon/test-plan fields",
        "metric-to-stage mapping",
        "operator-burden instrumentation",
        "cannot automatically cover all 20 local workflow stages",
        "cannot retroactively make a WP150 metric measurable",
        "WP150 implements none of them",
        "PARTIALLY_READY_BLOCKERS_IDENTIFIED",
    ):
        assert phrase in _normalized(section)


def test_all_readiness_domains_use_allowed_states_and_fail_closed():
    text = _read()
    expected = {
        "Market data": "PARTIALLY_READY",
        "Replay/fill": "ABSENT",
        "Strategy input": "NOT_READY",
        "Order lifecycle": "ABSENT",
        "Accounting": "ABSENT",
        "Risk": "ABSENT",
        "Observability": "ABSENT",
        "Reconciliation": "ABSENT",
        "Operations": "ABSENT",
    }
    for domain, state in expected.items():
        assert state in READINESS_STATES
        assert f"{domain}:\n{state}" in text
    matrix = _section(
        text, "## Mandatory Readiness Matrix", "## Blocker Register"
    )
    header, rows = _table(matrix)
    assert header == [
        "Domain",
        "State",
        "Critical",
        "Deterministic contract identified",
        "Implementation present",
        "Blocking conclusion",
    ]
    assert len(rows) == 9
    assert {row[1] for row in rows} <= READINESS_STATES
    assert "Critical gaps cannot be averaged away." in matrix
    assert "six critical domains" in matrix


def test_replay_public_adapter_candidate_advisory_and_readiness_negative_matrix():
    text = _read()
    forbidden = _section(
        text, "## Forbidden Interpretations", "## Future WP151 Boundary"
    )
    required_negative_assertions = (
        "Contract-only is not implemented",
        "Synthetic-only is not operational",
        "Replay inspection is not fill simulation",
        "A public adapter is not a paper engine",
        "A candidate is not a signal",
        "A signal is not an order",
        "Advisory output cannot become an order directly",
        "Readiness analysis is not execution approval",
        "A missing critical domain cannot be averaged into readiness",
        "Paper readiness is not paper authority",
        "Paper authority is not live authority",
        "WP150 does not implement WP151",
    )
    for phrase in required_negative_assertions:
        assert phrase in forbidden
    replay = _section(
        text,
        "## Replay And Fill-Model Readiness",
        "## Strategy-Input Readiness",
    )
    assert "Inspection replay is not fill simulation." in replay


def test_blocker_records_are_complete_and_use_allowed_classification_priority():
    text = _read()
    section = _section(
        text, "## Blocker Register", "## Paper-Trading Implementation Readiness"
    )
    header, rows = _table(section)
    assert tuple(header) == BLOCKER_FIELDS
    assert len(rows) == 17
    assert all(len(row) == len(BLOCKER_FIELDS) for row in rows)
    assert all(all(cell for cell in row) for row in rows)
    assert {row[2] for row in rows} <= {
        "FOUNDATIONAL",
        "CONTRACT_MISSING",
        "IMPLEMENTATION_MISSING",
        "EVIDENCE_MISSING",
        "EXTERNAL_DEPENDENCY",
        "OPERATOR_DECISION",
    }
    assert {row[3] for row in rows} <= {
        "P0_SAFETY",
        "P1_INTEGRITY",
        "P2_READINESS",
        "P3_OPTIMIZATION",
    }
    assert {row[0] for row in rows} == {
        "PT-001",
        "PT-002",
        "PT-003",
        "PT-004",
        "PT-005",
        "PT-006",
        "PT-007",
        "PT-008",
        "PT-009",
        "PT-010",
        "RV-001",
        "RV-002",
        "RV-003",
        "RV-004",
        "RV-005",
        "RV-006",
        "RV-007",
    }
    assert sum(row[3] == "P0_SAFETY" for row in rows) == 4
    assert sum(row[3] == "P1_INTEGRITY" for row in rows) == 8
    assert sum(row[3] == "P2_READINESS" for row in rows) == 5
    assert sum(row[2] == "FOUNDATIONAL" for row in rows) == 5
    assert sum(row[2] == "CONTRACT_MISSING" for row in rows) == 7
    assert sum(row[2] == "IMPLEMENTATION_MISSING" for row in rows) == 1
    assert sum(row[2] == "EVIDENCE_MISSING" for row in rows) == 3
    assert sum(row[2] == "OPERATOR_DECISION" for row in rows) == 1
    research_rows = [row for row in rows if row[0].startswith("RV-")]
    assert len(research_rows) == 7
    joined = _normalized(" ".join(" ".join(row) for row in research_rows))
    for required_gap in (
        "structured hypothesis",
        "deterministic derivation",
        "corpus/rubric coverage",
        "metric-to-stage mapping",
        "handoff fields",
        "operator burden",
    ):
        assert required_gap in joined


def test_paper_readiness_is_foundationally_blocked_and_grants_no_authority():
    text = _read()
    section = _section(
        text,
        "## Paper-Trading Implementation Readiness",
        "## Productive Next Phase",
    )
    for phrase in (
        "Paper-trading implementation readiness:\nNOT_READY_FOUNDATIONAL_GAPS",
        "replay/fill, order lifecycle, portfolio/accounting, risk, reconciliation, and operations",
        "critical and `ABSENT`",
        "Paper-trading execution:\nNOT AUTHORIZED",
        "Live-trading execution:\nFORBIDDEN",
        "Capital at risk:\nUSD 0",
        "Orders submitted:\n0",
        "Credentials created/used:\n0",
        "External model calls:\n0",
        "WP151 requires separate approval",
    ):
        assert _normalized(phrase) in _normalized(section)
    assert "READY_FOR_SEPARATE_BOUNDED_IMPLEMENTATION_WP" not in section


def test_next_phase_and_wp151_boundary_match_value_measurement_decision():
    text = _read()
    next_phase = _section(text, "## Productive Next Phase", "## Promotion Gates")
    future = _section(text, "## Future WP151 Boundary", "## Decision")
    assert (
        "Next phase:\nLOCAL_RESEARCH_WORKFLOW_VALUE_MEASUREMENT_HARNESS_CONTRACT"
        in next_phase
    )
    assert (
        "WP151 — Local Research Workflow Value Measurement Harness Contract V1"
        in future
    )
    assert "docs/status/tests-only contract" in _normalized(future)
    for phrase in (
        "missing structured fields",
        "metric-to-stage applicability",
        "metric grounding",
        "deterministic scoring",
        "per-metric coverage",
        "measurement receipts",
    ):
        assert phrase in future
    assert "must not implement instrumentation" in future
    assert "build a paper engine" in future
    assert "WP151 requires separate approval" in future
    for forbidden_next_phase in (
        "BOUNDED_PAPER_TRADING_ARCHITECTURE_AND_SAFETY_CONTRACT",
        "LOCAL_RESEARCH_AND_MARKET_DATA_FOUNDATION_GAP_RESOLUTION_DECISION",
    ):
        assert forbidden_next_phase not in next_phase


def test_output_inventory_is_exact_and_no_forbidden_surface_is_changed():
    text = _read()
    inventory = _section(
        text, "## Output Surface Inventory", "## Forbidden Interpretations"
    )
    expected_paths = (
        "docs/local_research_workflow_value_validation_and_paper_trading_readiness_decision.md",
        "tests/test_local_research_workflow_value_validation_and_paper_trading_readiness_decision_docs.py",
        "docs/status_entries/WP150.md",
        "docs/project_status.md",
        "docs/repo_truth_index.md",
        "tests/test_project_status_docs.py",
    )
    assert len(re.findall(r"(?m)^\d+\. ", inventory)) == 6
    for path in expected_paths:
        assert path in inventory
    for statement in (
        "Source changes: 0",
        "Tool changes: 0",
        "Fixture changes: 0",
        "Workflow changes: 0",
        "Dependency/lock changes: 0",
        "Configuration/runtime changes: 0",
        "`docs/deferred_items_log.md` changes: 0",
    ):
        assert statement in inventory


def test_document_status_project_and_repo_truth_surfaces_agree():
    surfaces = {
        "document": _read(),
        "status": _read(STATUS),
        "project": _read(PROJECT_STATUS),
        "repo_truth": _read(REPO_TRUTH),
    }
    normalized = {name: _normalized(value) for name, value in surfaces.items()}
    for token in DECISION_TOKENS:
        normalized_token = _normalized(token)
        for name in ("document", "status", "project"):
            assert normalized_token in normalized[name], (name, normalized_token)
    for path in (
        "docs/local_research_workflow_value_validation_and_paper_trading_readiness_decision.md",
        "tests/test_local_research_workflow_value_validation_and_paper_trading_readiness_decision_docs.py",
        "docs/status_entries/WP150.md",
    ):
        assert path in surfaces["repo_truth"]
    assert "WP149" in surfaces["project"] and "MERGED" in surfaces["project"]
    assert "WP150" in surfaces["project"] and "REVIEW_TARGET" in surfaces["project"]


def test_status_fragment_is_stable_model_d_and_has_no_dynamic_placeholders():
    status = _read(STATUS)
    for forbidden in (
        "TBD",
        "LOCAL_DRAFT_VERIFIED",
        "Head commit:",
        "future mergeability",
    ):
        assert forbidden not in status
    assert re.search(
        r"Current live PR head:\s*`?[0-9a-f]{40}`?", status, re.IGNORECASE
    ) is None
    assert "PR: see GitHub PR metadata and PR body." in status
    assert "Evidence mode: PRIVATE_REPO_MANUAL_VERIFIED" in status
    assert "Evidence architecture: Model D" in status
    assert "Ready for review: YES only after final validation" in status
