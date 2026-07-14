from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNBOOK = ROOT / "docs" / (
    "hermes_candidate_review_manual_six_record_research_lineage_human_decision_"
    "follow_up_task_operator_runbook.md"
)

HEADINGS = [
    "# Hermes Candidate-Review Manual Six-Record Research Lineage, Human Decision, And Follow-Up Task Operator Runbook",
    "## Purpose", "## Position After WP138", "## Authority And Non-Authority",
    "## Operator Preconditions", "## Existing WP121 Research-Question API",
    "## Existing WP132 Request API", "## Existing WP133 Response API",
    "## Existing WP122 Validation-Receipt API", "## Existing WP123 Human-Decision API",
    "## Existing WP123 Follow-Up-Task API", "## Six-Record Manual Lineage Model",
    "## No Adapter, Decision Generator, Or Task Generator",
    "## Step 1 — Construct The WP121 Record Explicitly", "## Step 2 — Validate The WP121 Record",
    "## Step 3 — Construct The WP132 Request Explicitly", "## Step 4 — Validate The WP132 Request",
    "## Step 5 — Perform Research Outside This Package", "## Step 6 — Construct The WP133 Response Explicitly",
    "## Step 7 — Validate The WP133 Response", "## Step 8 — Construct The WP122 Receipt Explicitly",
    "## Step 9 — Validate The WP122 Receipt", "## Step 10 — Perform Human Review Outside This Package",
    "## Step 11 — Construct The WP123 Human Decision Explicitly",
    "## Step 12 — Validate The WP123 Human Decision",
    "## Step 13 — Construct The WP123 Follow-Up Task Explicitly",
    "## Step 14 — Validate The WP123 Follow-Up Task",
    "## Step 15 — Perform Six-Record Lineage Review", "## Exact Eighteen Linkage Relationships",
    "## Existing Six Non-Linkages", "## Additional Ten Non-Linkages",
    "## Contract Validity Versus Lineage Consistency", "## Seventeen Valid-But-Inconsistent Cases",
    "## Mismatch Handling", "## Human Review Boundary", "## Unsafe No-Echo Boundary",
    "## Source And Citation Non-Verification Boundary", "## WP123 Compatibility Caveats",
    "## Temp-Only Synthetic Smoke Boundary", "## Cleanup And Repo Hygiene",
    "## Forbidden Interpretations", "## Future Gates", "## Non-Authority Statement",
]


def test_exact_title_and_heading_order() -> None:
    text = RUNBOOK.read_text(encoding="utf-8")
    assert text.splitlines()[0] == HEADINGS[0]
    assert [line for line in text.splitlines() if line.startswith("#")] == HEADINGS


def test_all_five_modules_and_six_api_families_are_documented() -> None:
    text = RUNBOOK.read_text(encoding="utf-8")
    for path in (
        "src/data_layer/hermes_candidate_review_research_question_record.py",
        "src/data_layer/hermes_candidate_review_manual_research_request.py",
        "src/data_layer/hermes_candidate_review_manual_research_response.py",
        "src/data_layer/hermes_candidate_review_advisory_output_validation_receipt.py",
        "src/data_layer/hermes_candidate_review_human_decision_follow_up_record.py",
    ):
        assert f"`{path}`" in text
    for family in (
        "research_question_record", "manual_research_request", "manual_research_response",
        "advisory_output_validation_receipt", "human_decision_record",
        "follow_up_research_task_record",
    ):
        for operation in ("validate", "build", "assert"):
            assert f"`{operation}_candidate_review_{family}`" in text


def test_exact_seventeen_helpers_and_six_fixture_independence_are_documented() -> None:
    text = RUNBOOK.read_text(encoding="utf-8")
    helpers = (
        "_question_preflight_flags", "_question_safety_flags", "_question_notice",
        "_question_record", "_request_flags", "_request_notice", "_request",
        "_response_flags", "_response_notice", "_response", "_receipt_flags",
        "_receipt_notice", "_receipt", "_wp123_flags", "_wp123_notice", "_decision",
        "_follow_up_task",
    )
    assert all(f"`{helper}`" in text for helper in helpers)
    for phrase in (
        "independently hard-coded zero-argument functions",
        "never call or read another record fixture",
        "never consume another result",
        "No validation or build result becomes another fixture input",
        "All six validators and all six builders run independently",
    ):
        assert phrase in text


def test_eighteen_relationships_and_sixteen_non_linkages_are_exact() -> None:
    text = RUNBOOK.read_text(encoding="utf-8")
    linkage = text[text.index("## Exact Eighteen Linkage Relationships"):text.index("## Existing Six Non-Linkages")]
    existing = text[text.index("## Existing Six Non-Linkages"):text.index("## Additional Ten Non-Linkages")]
    additional = text[text.index("## Additional Ten Non-Linkages"):text.index("## Contract Validity Versus Lineage Consistency")]
    assert [line.split(". ", 1)[0] for line in linkage.splitlines() if line[:1].isdigit()] == [str(i) for i in range(1, 19)]
    assert [line.split(". ", 1)[0] for line in existing.splitlines() if line[:1].isdigit()] == [str(i) for i in range(1, 7)]
    assert [line.split(". ", 1)[0] for line in additional.splitlines() if line[:1].isdigit()] == [str(i) for i in range(7, 17)]
    for phrase in (
        "WP121 record ID equals WP123 decision nested question-record ID",
        "WP122 receipt ID equals WP123 decision nested receipt ID",
        "WP123 decision ID equals WP123 task nested decision ID",
        "Every WP123 decision relied-on evidence reference appears",
        "All six normalized records require `human_review_required is True`",
        "Research content, review evidence, human judgment, and task content remain distinct",
    ):
        assert phrase in text


def test_all_seventeen_mismatches_and_required_co_adjustments_are_documented() -> None:
    text = RUNBOOK.read_text(encoding="utf-8")
    cases = (
        "question_receipt_record_reference", "question_to_request_candidate",
        "question_to_response_candidate", "question_to_request_text", "question_to_response_text",
        "question_to_request_type", "question_to_response_type", "request_response_reference",
        "briefing_reference", "response_sections", "cited_reference_outside_request",
        "response_receipt_artifact", "receipt_checked_sources", "question_decision_record_reference",
        "receipt_decision_reference", "decision_task_reference", "decision_evidence_outside_receipt",
    )
    assert all(f"`{case}`" in text for case in cases)
    for phrase in (
        "co-adjusts response citations, receipt checked references, and decision relied-on evidence",
        "co-adjusts receipt checked references and decision relied-on evidence",
        "changes only decision relied-on evidence",
        "exactly one of the seventeen non-human-review lineage relationships is false",
    ):
        assert phrase in text


def test_failure_matrices_and_no_echo_are_documented() -> None:
    text = RUNBOOK.read_text(encoding="utf-8")
    human = text[text.index("## Human Review Boundary"):text.index("## Unsafe No-Echo Boundary")]
    unsafe = text[text.index("## Unsafe No-Echo Boundary"):text.index("## Source And Citation Non-Verification Boundary")]
    for name in ("question", "request", "response", "receipt", "decision", "follow-up task"):
        assert name in human
    assert "set only `human_review_required` to `False`" in human
    assert "normalized record or receipt exactly `{}`" in human
    assert "No peer fixture is generated" in human
    assert "six unsafe cases" in unsafe
    assert "absent from every public result field and `repr(result)`" in unsafe
    assert "assertion exception does not echo it" in unsafe
    assert "`tmp_path` remains empty" in human and "`tmp_path` remains empty" in unsafe


def test_non_verification_wp123_caveats_and_boundaries_are_complete() -> None:
    text = RUNBOOK.read_text(encoding="utf-8")
    for phrase in (
        "WP132 and WP133 decision lineage is inherited through WP121 and WP122",
        "explicitly authored after external human review",
        "follow-up task is explicitly authored and is not generated from the decision",
        "do not fetch sources", "verify provenance", "verify citation support",
        "validates required fields rather than cross-record truth",
        "neither verifies sources/citations nor generates decisions or tasks",
        "no file is written anywhere", "WP140 is not implemented here",
        "no repair, inference, transfer, adapter, decision/task generation",
        "chain/session/linkage product object", "product network", "storage", "paper",
        "live", "execution", "risk", "credential", "recommendation", "probability",
        "scoring", "ranking", "priority",
    ):
        assert phrase in text


def test_docs_test_is_markdown_only() -> None:
    source = Path(__file__).read_text(encoding="utf-8")
    assert all(
        not line.startswith(("from " + "src.", "import " + "src."))
        for line in source.splitlines()
    )
