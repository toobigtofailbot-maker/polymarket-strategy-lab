import re
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DOC = REPO_ROOT / "docs/local_research_workflow_value_measurement_harness_contract.md"
WP150_DOC = REPO_ROOT / (
    "docs/local_research_workflow_value_validation_and_"
    "paper_trading_readiness_decision.md"
)
STATUS = REPO_ROOT / "docs/status_entries/WP151.md"
PROJECT_STATUS = REPO_ROOT / "docs/project_status.md"
REPO_TRUTH = REPO_ROOT / "docs/repo_truth_index.md"

TITLE = "# Local Research Workflow Value Measurement Harness Contract"
HEADINGS = [
    TITLE,
    "## Purpose",
    "## Position After WP150",
    "## Authority And Non-Authority",
    "## Repository Inputs Reviewed",
    "## Contract Architecture",
    "## Measurement Waves",
    "## Canonical Metric Registry",
    "## Metric-To-Stage Applicability Map",
    "## Corpus Contract",
    "## Run Contract",
    "## Event Contract",
    "## Operator Action Contract",
    "## Measurement Receipt Contract",
    "## Deterministic Scoring And Aggregation",
    "## Repeatability Contract",
    "## Run Status Contract",
    "## Temporary Output Contract",
    "## Human Review Contract",
    "## Safety And Non-Authority Gates",
    "## Negative And Mutation Matrix",
    "## Blocker Resolution Map",
    "## Implementation Readiness Decision",
    "## Promotion Gates",
    "## Explicit Deferred Capabilities",
    "## Output Surface Inventory",
    "## Forbidden Interpretations",
    "## Future WP152 Boundary",
    "## Decision",
    "## Non-Authority Statement",
]
METRIC_FIELDS = (
    "metric_id",
    "dimension",
    "metric",
    "wp150_state",
    "wave",
    "measurement_type",
    "exact_input_fields_or_derivation",
    "applicable_stage_ids",
    "corpus_case_ids_or_family",
    "aggregation",
    "fail_closed_condition",
    "receipt_field",
    "human_review",
)
STAGE_FIELDS = (
    "stage_id",
    "stage_name",
    "applicable_metric_ids",
    "non_applicable_dimensions",
    "required_input_artifact",
    "required_output_artifact",
    "instrumentation_needed",
    "wave",
)
CORPUS_FIELDS = (
    "case_id",
    "family",
    "stage_ids",
    "metric_ids",
    "input_artifact_shape",
    "expected_validation_state",
    "expected_metric_events",
    "negative_mutation_family",
    "human_review",
)
WAVE2_FIELDS = (
    "metric_id",
    "missing_field_or_derivation",
    "missing_corpus_or_rubric_coverage",
    "required_future_schema",
    "required_validation",
    "required_negative_tests",
    "separate_schema_enablement_wp",
)
ALLOWED_MEASUREMENT_TYPES = {
    "COUNT",
    "RATE",
    "BOOLEAN_COVERAGE",
    "SET_COVERAGE",
    "DURATION",
    "REPEATABILITY_EQUALITY",
    "RUBRIC_SCORE",
    "NOT_IMPLEMENTABLE_YET",
}
EXPECTED_EVENT_TYPES = {
    "RUN_STARTED",
    "CASE_STARTED",
    "STAGE_STARTED",
    "STAGE_COMPLETED",
    "VALIDATION_PASSED",
    "VALIDATION_FAILED",
    "OPERATOR_REVIEW_REQUIRED",
    "OPERATOR_ACKNOWLEDGED",
    "CORRECTION_REQUESTED",
    "CASE_COMPLETED",
    "CASE_FAILED",
    "RUN_COMPLETED",
    "RUN_FAILED",
}
EXPECTED_RUN_STATUSES = {
    "RUN_VALID_MEASUREMENT_COMPLETE",
    "RUN_FAILED_INPUT_CONTRACT",
    "RUN_FAILED_CORPUS_VERSION",
    "RUN_FAILED_METRIC_REGISTRY",
    "RUN_FAILED_STAGE_MAP",
    "RUN_FAILED_EVENT_CONTRACT",
    "RUN_FAILED_VALIDATION",
    "RUN_FAILED_REPEATABILITY",
    "RUN_ABORTED_BY_OPERATOR",
}
EXPECTED_SAFETY_GATES = {
    "NO_NETWORK",
    "NO_CREDENTIAL_ACCESS",
    "NO_PROVIDER_OR_MODEL_CALL",
    "NO_HERMES_RUNTIME",
    "NO_PAPER_OR_LIVE_STATE",
    "NO_ORDER_OR_SIGNAL_CREATION",
    "NO_PROFITABILITY_OR_RECOMMENDATION_OUTPUT",
    "NO_RAW_PRIVATE_OR_SECRET_DATA",
    "NO_UNAPPROVED_PERSISTENCE",
    "NO_SCHEDULER_OR_BACKGROUND_TASK",
    "NO_WAVE_2_FALSE_MEASUREMENT",
    "HUMAN_REVIEW_REQUIRED",
}


def _read(path: Path = DOC) -> str:
    return path.read_text(encoding="utf-8")


def _section(text: str, heading: str, next_heading: str) -> str:
    return text.split(heading, 1)[1].split(next_heading, 1)[0]


def _table(section: str) -> tuple[list[str], list[list[str]]]:
    lines = [line for line in section.splitlines() if line.startswith("|")]
    assert len(lines) >= 2
    header = [cell.strip() for cell in lines[0].strip("|").split("|")]
    rows = [
        [cell.strip() for cell in line.strip("|").split("|")]
        for line in lines[2:]
    ]
    return header, rows


def _code_tokens(section: str) -> set[str]:
    return {
        line.strip()
        for line in section.splitlines()
        if line.strip() and re.fullmatch(r"[A-Z][A-Z0-9_]+", line.strip())
    }


def _metric_rows(text: str) -> list[list[str]]:
    section = _section(
        text, "## Canonical Metric Registry", "## Metric-To-Stage Applicability Map"
    )
    header, rows = _table(section)
    assert tuple(header) == METRIC_FIELDS
    return rows


def _wp150_metric_rows() -> list[list[str]]:
    text = _read(WP150_DOC)
    section = _section(
        text, "## Metric-To-Evidence Grounding Matrix", "## Research Throughput"
    )
    _, rows = _table(section)
    return rows


def test_exact_title_headings_and_locked_decision_tokens():
    text = _read()
    headings = [
        line
        for line in text.splitlines()
        if line.startswith("# ") or line.startswith("## ")
    ]
    assert headings == HEADINGS
    assert text.startswith(TITLE + "\n")
    for token in (
        "LOCAL_DETERMINISTIC_OPERATOR_INITIATED_TEMPORARY_HARNESS",
        "OFFLINE_LOCAL_NO_PROVIDER_NO_MARKET_NETWORK",
        "RESEARCH_MEASUREMENT_ONLY_NO_STRATEGY_NO_PAPER_NO_LIVE",
        "IN_MEMORY_OR_PYTEST_TEMPORARY_ONLY",
        "EXPLICIT_SINGLE_RUN_NO_SCHEDULER",
        "GROUNDED_22_METRICS_ONLY",
        "CONTRACT_DEFINED_IMPLEMENTATION_DEFERRED",
        "COMPLETE_READY_FOR_BOUNDED_IMPLEMENTATION_WP",
        "BOUNDED_LOCAL_RESEARCH_VALUE_MEASUREMENT_HARNESS_IMPLEMENTATION",
    ):
        assert token in text


def test_registry_exactly_matches_wp150_identity_state_and_22_17_split():
    rows = _metric_rows(_read())
    prior = _wp150_metric_rows()
    assert len(rows) == len(prior) == 39
    assert len({row[0] for row in rows}) == 39
    assert all(len(row) == len(METRIC_FIELDS) for row in rows)
    assert all(all(cell for cell in row) for row in rows)
    assert [(row[0], row[1], row[2], row[3]) for row in rows] == [
        (row[0], row[1], row[2], row[3]) for row in prior
    ]
    assert sum(row[4] == "WAVE_1" for row in rows) == 22
    assert sum(row[4] == "WAVE_2" for row in rows) == 17
    assert sum(row[3] == "MEASURABLE_NOT_YET_MEASURED" for row in rows) == 22
    assert sum(row[3] == "NOT_CURRENTLY_MEASURABLE" for row in rows) == 17


def test_wave1_types_are_concrete_and_wave2_is_not_implementable_yet():
    rows = _metric_rows(_read())
    assert {row[5] for row in rows} <= ALLOWED_MEASUREMENT_TYPES
    wave1 = [row for row in rows if row[4] == "WAVE_1"]
    wave2 = [row for row in rows if row[4] == "WAVE_2"]
    assert all(row[5] != "NOT_IMPLEMENTABLE_YET" for row in wave1)
    assert all(row[5] == "NOT_IMPLEMENTABLE_YET" for row in wave2)
    assert all(row[10] and row[11] and row[12] == "REQUIRED" for row in rows)
    assert all("BLOCKED_WAVE_2" in row[10] for row in wave2)


def test_wave2_requirements_cover_exactly_the_17_blocked_metrics():
    text = _read()
    section = _section(text, "## Measurement Waves", "## Canonical Metric Registry")
    header, rows = _table(section)
    assert tuple(header) == WAVE2_FIELDS
    assert len(rows) == 17
    assert all(len(row) == len(WAVE2_FIELDS) and all(row) for row in rows)
    blocked = {row[0] for row in _metric_rows(text) if row[4] == "WAVE_2"}
    assert {row[0] for row in rows} == blocked
    assert all(row[6] == "YES" for row in rows)
    assert "separately approved Wave 2 schema-enablement package" in section
    assert "not an architecture question" in section


def test_stage_map_has_exactly_20_stages_and_covers_every_wave1_metric():
    text = _read()
    section = _section(
        text, "## Metric-To-Stage Applicability Map", "## Corpus Contract"
    )
    header, rows = _table(section)
    assert tuple(header) == STAGE_FIELDS
    assert len(rows) == 20
    assert [row[0] for row in rows] == [f"LRW-{i:02d}" for i in range(1, 21)]
    assert all(len(row) == len(STAGE_FIELDS) and all(row) for row in rows)
    mapped = set(re.findall(r"RV-[A-Z]+-\d{2}", " ".join(row[2] for row in rows)))
    wave1 = {row[0] for row in _metric_rows(text) if row[4] == "WAVE_1"}
    assert wave1 <= mapped
    assert "Manual/export/runbook stages remain manual" in section
    assert "No paper stage is added" in section


def test_corpus_has_14_fixed_families_and_explicit_wave1_coverage():
    text = _read()
    section = _section(text, "## Corpus Contract", "## Run Contract")
    header, rows = _table(section)
    assert tuple(header) == CORPUS_FIELDS
    assert len(rows) == 14
    assert [row[0] for row in rows] == [f"LVM-{i:03d}" for i in range(1, 15)]
    assert len({row[1] for row in rows}) == 14
    assert all(len(row) == len(CORPUS_FIELDS) and all(row) for row in rows)
    covered = set(re.findall(r"RV-[A-Z]+-\d{2}", " ".join(row[3] for row in rows)))
    wave1 = {row[0] for row in _metric_rows(text) if row[4] == "WAVE_1"}
    assert wave1 <= covered
    for token in (
        "local-research-workflow-value-measurement-v1",
        "Corpus version:\n1.0",
        "SYNTHETIC_SANITIZED_OFFLINE_FIXED",
        "Corpus case count:\n14",
        "Corpus family count:\n14",
        "WP151 creates no fixture",
    ):
        assert token in section


def test_run_event_action_and_receipt_schemas_are_complete():
    text = _read()
    run = _section(text, "## Run Contract", "## Event Contract")
    for field in (
        "run_contract_version",
        "corpus_id",
        "corpus_version",
        "metric_registry_version",
        "stage_map_version",
        "run_id",
        "operator_run_label",
        "case_selection",
        "repeat_index",
        "temporary_output_mode",
        "human_review_required",
        "non_authority_notice",
    ):
        assert f"| {field} |" in run

    event = _section(text, "## Event Contract", "## Operator Action Contract")
    assert EXPECTED_EVENT_TYPES == _code_tokens(event)
    for field in (
        "event_contract_version",
        "run_id",
        "case_id",
        "repeat_index",
        "event_sequence",
        "event_type",
        "stage_id",
        "metric_ids",
        "monotonic_elapsed_ns",
        "validation_state",
        "error_codes",
        "operator_action_type",
        "input_reference",
        "output_reference",
        "non_authority_notice",
    ):
        assert field in event

    action = _section(
        text, "## Operator Action Contract", "## Measurement Receipt Contract"
    )
    assert {
        "NO_ACTION",
        "ACKNOWLEDGE",
        "REQUEST_CORRECTION",
        "RETRY_CASE",
        "DEFER_CASE",
        "ABORT_RUN",
    } <= _code_tokens(action)
    for field in (
        "action_id",
        "run_id",
        "case_id",
        "stage_id",
        "action_type",
        "reason_code",
        "correction_target",
        "reviewer_acknowledgement",
        "human_review_required",
        "non_authority_notice",
    ):
        assert field in action

    receipt = _section(
        text,
        "## Measurement Receipt Contract",
        "## Deterministic Scoring And Aggregation",
    )
    for field in (
        "receipt_contract_version",
        "receipt_id",
        "run_contract_version",
        "corpus_id",
        "corpus_version",
        "metric_registry_version",
        "stage_map_version",
        "run_id",
        "case_count",
        "repeat_count",
        "event_count",
        "metric_results",
        "hard_failures",
        "repeatability_results",
        "operator_action_counts",
        "run_status",
        "human_review_status",
        "temporary_output_status",
        "non_authority_notice",
        "safety_flags",
        "numerator",
        "denominator",
        "duration_ns",
        "set_coverage",
        "measurement_status",
        "failure_codes",
    ):
        assert field in receipt
    for status in (
        "MEASURED_VALID",
        "NOT_APPLICABLE",
        "FAILED_VALIDATION",
        "INSUFFICIENT_CASE_COVERAGE",
        "BLOCKED_WAVE_2",
    ):
        assert status in receipt


def test_exact_formulas_repeatability_statuses_and_output_modes():
    text = _read()
    scoring = _section(
        text,
        "## Deterministic Scoring And Aggregation",
        "## Repeatability Contract",
    )
    for formula in (
        "count = number of qualifying deterministic events or records",
        "rate = numerator / denominator",
        "true only when every required field/flag is present and valid",
        "coverage = observed required labels / expected required labels",
        "duration_ns = stage_completed.monotonic_elapsed_ns - stage_started.monotonic_elapsed_ns",
        "PASS only when normalized deterministic outputs and metric results are equal across required repeats",
    ):
        assert formula in scoring

    repeat = _section(
        text, "## Repeatability Contract", "## Run Status Contract"
    )
    assert "Required repeats per selected case:\n3" in repeat
    for phrase in (
        "run ID",
        "receipt ID",
        "monotonic duration",
        "acknowledgement ID",
        "validation state",
        "error codes",
        "normalized output shape",
        "safety flags",
        "run status",
    ):
        assert phrase in repeat

    statuses = _section(
        text, "## Run Status Contract", "## Temporary Output Contract"
    )
    assert EXPECTED_RUN_STATUSES == _code_tokens(statuses)
    output = _section(
        text, "## Temporary Output Contract", "## Human Review Contract"
    )
    assert {
        "IN_MEMORY_ONLY",
        "PYTEST_TMP_PATH_ONLY",
        "IGNORED_LOCAL_TEMP_DIRECTORY",
    } == _code_tokens(output)
    assert "authorizes no writer and no output path" in output


def test_human_review_safety_and_mutation_matrix_are_complete():
    text = _read()
    review = _section(
        text, "## Human Review Contract", "## Safety And Non-Authority Gates"
    )
    for outcome in (
        "ACCEPT_MEASUREMENT_RECEIPT_FOR_RESEARCH_MEMORY_ONLY",
        "REJECT_RECEIPT_CONTRACT_FAILURE",
        "REJECT_RECEIPT_COVERAGE_FAILURE",
        "REJECT_RECEIPT_REPEATABILITY_FAILURE",
        "REJECT_RECEIPT_SAFETY_FAILURE",
        "DEFER_RECEIPT_PENDING_CORRECTION",
    ):
        assert outcome in review

    safety = _section(
        text, "## Safety And Non-Authority Gates", "## Negative And Mutation Matrix"
    )
    assert EXPECTED_SAFETY_GATES == _code_tokens(safety)
    assert "One failed gate fails the run" in safety

    mutations = _section(
        text, "## Negative And Mutation Matrix", "## Blocker Resolution Map"
    )
    header, rows = _table(mutations)
    assert header == ["mutation_id", "mutation", "required_failure"]
    assert len(rows) == 21
    joined = " ".join(" ".join(row) for row in rows).lower()
    for phrase in (
        "renamed metric",
        "wave 2 metric marked measured",
        "unknown stage",
        "duplicate case id",
        "out-of-order event",
        "negative duration",
        "zero denominator",
        "unknown operator action",
        "free-form note",
        "wall-clock",
        "network attempt",
        "credential access",
        "provider/model output",
        "recommendation",
        "persistent output",
        "repeatability mismatch",
        "missing human review",
        "extra or missing receipt field",
        "input mutation",
    ):
        assert phrase in joined


def test_all_seven_wp150_blockers_are_contract_resolved_not_implemented():
    text = _read()
    section = _section(
        text, "## Blocker Resolution Map", "## Implementation Readiness Decision"
    )
    header, rows = _table(section)
    assert header == [
        "blocker_id",
        "WP150 blocker",
        "WP151 contract resolution",
        "implementation still required",
        "target_wp",
    ]
    assert [row[0] for row in rows] == [f"RV-{i:03d}" for i in range(1, 8)]
    assert all(row[3] == "YES" for row in rows)
    assert "All seven blockers are contract-resolved" in section
    assert "No separate schema decision remains open" in section


def test_readiness_is_derived_and_wp152_is_wave1_only():
    text = _read()
    readiness = _section(
        text, "## Implementation Readiness Decision", "## Promotion Gates"
    )
    rows = _metric_rows(text)
    stage_rows = _table(
        _section(text, "## Metric-To-Stage Applicability Map", "## Corpus Contract")
    )[1]
    corpus_rows = _table(_section(text, "## Corpus Contract", "## Run Contract"))[1]
    assert len(rows) == 39
    assert sum(row[4] == "WAVE_1" for row in rows) == 22
    assert sum(row[4] == "WAVE_2" for row in rows) == 17
    assert len(stage_rows) == 20
    assert len(corpus_rows) == 14
    assert "COMPLETE_READY_FOR_BOUNDED_IMPLEMENTATION_WP" in readiness
    boundary = _section(text, "## Future WP152 Boundary", "## Decision")
    for phrase in (
        "WP152 — Bounded Local Research Workflow Value Measurement Harness Implementation V1",
        "22 Wave 1 metrics",
        "All 17 Wave 2 metrics remain blocked",
        "must not implement WP153",
        "must not implement",
    ):
        assert phrase in boundary


def test_preserved_wp150_truth_and_non_authority_are_explicit():
    text = _read()
    for token in (
        "DEFERRED_PENDING_MATERIAL_NEW_EVIDENCE",
        "PARTIALLY_READY_BLOCKERS_IDENTIFIED",
        "Research-value metric records:\n39",
        "Research-value metrics measured:\n0",
        "Research-value metrics measurable but not yet measured:\n22",
        "Research-value metrics not currently measurable:\n17",
        "Research-value blockers:\n7",
        "NOT_READY_FOUNDATIONAL_GAPS",
        "Paper-trading execution:\nNOT AUTHORIZED",
        "Live-trading execution:\nFORBIDDEN",
        "Capital at risk:\nUSD 0",
        "Orders submitted:\n0",
        "Credentials created/used:\n0",
        "External model calls:\n0",
        "Measurement harness implementation:\nNOT AUTHORIZED",
        "Measurement run:\nNOT AUTHORIZED",
        "Persistent measurement output:\nNOT AUTHORIZED",
        "WP152 requires separate approval",
    ):
        assert token in text


def test_forbidden_interpretations_are_complete():
    section = _section(
        _read(), "## Forbidden Interpretations", "## Future WP152 Boundary"
    )
    for phrase in (
        "Contract is not implementation",
        "Measurable is not measured",
        "Wave 1 excludes Wave 2",
        "Future schema is not current field",
        "Corpus coverage is not real-world validity",
        "Deterministic validation is not factual truth",
        "Research value is not profitability",
        "Research output is not a signal or order",
        "Temporary output is not persistent evidence",
        "Human review is not trading approval",
        "Readiness is not authority",
        "WP151 does not implement WP152",
        "No paper/live/execution authority changes",
    ):
        assert phrase in section


def test_status_project_and_index_agree_on_contract_decision():
    text = _read()
    status = _read(STATUS)
    project = _read(PROJECT_STATUS)
    index = _read(REPO_TRUTH)
    for token in (
        "COMPLETE_READY_FOR_BOUNDED_IMPLEMENTATION_WP",
        "GROUNDED_22_METRICS_ONLY",
        "CONTRACT_DEFINED_IMPLEMENTATION_DEFERRED",
        "BOUNDED_LOCAL_RESEARCH_VALUE_MEASUREMENT_HARNESS_IMPLEMENTATION",
        "Research-value metric records:\n39",
        "Research-value metrics measurable but not yet measured:\n22",
        "Research-value metrics not currently measurable:\n17",
        "WP152 requires separate approval",
    ):
        assert token in text
        assert " ".join(token.split()) in " ".join(status.split())
        assert " ".join(token.split()) in " ".join(project.split())
    assert DOC.name in index
    assert Path(__file__).name in index
    assert STATUS.name in index


def test_exact_six_file_scope_and_no_implementation_or_deferred_log_change():
    result = subprocess.run(
        ["git", "diff", "--name-only", "origin/main"],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    untracked_result = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard"],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    changed = {
        line
        for line in (result.stdout + untracked_result.stdout).splitlines()
        if line
    }
    assert changed == {
        "docs/local_research_workflow_value_measurement_harness_contract.md",
        "docs/project_status.md",
        "docs/repo_truth_index.md",
        "docs/status_entries/WP151.md",
        "tests/test_local_research_workflow_value_measurement_harness_contract_docs.py",
        "tests/test_project_status_docs.py",
    }
    assert not any(
        path.startswith(
            (
                "src/",
                "tools/",
                "tests/fixtures/",
                ".github/workflows/",
                "config/",
            )
        )
        for path in changed
    )
    assert not changed & {
        "requirements.txt",
        "pyproject.toml",
        "package.json",
        "docs/deferred_items_log.md",
    }


def test_status_fragment_is_stable_model_d_and_has_required_headings():
    status = _read(STATUS)
    headings = [
        line
        for line in status.splitlines()
        if line.startswith("# ") or line.startswith("## ")
    ]
    assert headings == [
        "# WP151 — Local Research Workflow Value Measurement Harness Contract V1",
        "## Package Identity",
        "## Authorization Basis",
        "## Authority / Non-Authority",
        "## Merge Gate",
        "## Repository Inputs Reviewed",
        "## Repository Discovery",
        "## Contract Architecture",
        "## Measurement Waves",
        "## Metric Registry",
        "## Stage Map",
        "## Corpus Contract",
        "## Run Contract",
        "## Event Contract",
        "## Operator Action Contract",
        "## Receipt Contract",
        "## Scoring",
        "## Repeatability",
        "## Temporary Output",
        "## Human Review",
        "## Safety Gates",
        "## Mutation Matrix",
        "## Blocker Resolution",
        "## Contract Readiness",
        "## Next Phase",
        "## Promotion Gates",
        "## Deferred Capabilities",
        "## Changed Files",
        "## Requirement-To-Evidence",
        "## Validation",
        "## Model D Evidence",
        "## Stable Metadata",
        "## Follow-Up Classification",
        "## Ready For Review",
    ]
    assert "PR: see GitHub PR metadata and PR body." in status
    assert (
        "Current live PR head: see GitHub PR metadata and PR body."
        in status
    )
    assert re.search(r"\b[0-9a-f]{40}\b", status, re.IGNORECASE) is None
    assert "TBD" not in status
    assert "future mergeability" not in status.lower()
