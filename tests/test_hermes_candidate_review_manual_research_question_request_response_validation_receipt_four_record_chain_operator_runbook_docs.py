from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNBOOK = ROOT / "docs" / "hermes_candidate_review_manual_research_question_request_response_validation_receipt_four_record_chain_operator_runbook.md"

HEADINGS = [
    "# Hermes Candidate-Review Manual Research Question-Request-Response-Validation Receipt Four-Record Chain Operator Runbook",
    "## Purpose", "## Position After WP136", "## Authority And Non-Authority", "## Operator Preconditions",
    "## Existing WP121 Research-Question API", "## Existing WP132 Request API",
    "## Existing WP133 Response API", "## Existing WP122 Validation-Receipt API",
    "## Four-Record Lineage Model", "## No Adapter Or Automatic Transfer",
    "## Step 1 — Construct The WP121 Record Explicitly", "## Step 2 — Validate The WP121 Record",
    "## Step 3 — Construct The WP132 Request Explicitly", "## Step 4 — Validate The WP132 Request",
    "## Step 5 — Perform Research Outside This Package", "## Step 6 — Construct The WP133 Response Explicitly",
    "## Step 7 — Validate The WP133 Response", "## Step 8 — Construct The WP122 Receipt Explicitly",
    "## Step 9 — Validate The WP122 Receipt", "## Step 10 — Perform Four-Record Lineage Review",
    "## Exact Fourteen Linkage Relationships", "## Explicit Non-Linkages",
    "## Contract Validity Versus Lineage Consistency", "## Mismatch Handling",
    "## Source And Citation Non-Verification Boundary", "## WP121 And WP122 Compatibility Caveats",
    "## Temp-Only Synthetic Smoke Boundary", "## Human Review Boundary", "## Failure Handling",
    "## Cleanup And Repo Hygiene", "## Forbidden Interpretations", "## Future Gates",
    "## Non-Authority Statement",
]


def test_exact_title_and_heading_order() -> None:
    text = RUNBOOK.read_text(encoding="utf-8")
    assert [line for line in text.splitlines() if line.startswith("#")] == HEADINGS


def test_four_existing_apis_and_contract_constants_are_documented() -> None:
    text = RUNBOOK.read_text(encoding="utf-8")
    for path in (
        "src/data_layer/hermes_candidate_review_research_question_record.py",
        "src/data_layer/hermes_candidate_review_manual_research_request.py",
        "src/data_layer/hermes_candidate_review_manual_research_response.py",
        "src/data_layer/hermes_candidate_review_advisory_output_validation_receipt.py",
    ):
        assert path in text
    for family in ("research_question_record", "manual_research_request", "manual_research_response", "advisory_output_validation_receipt"):
        for operation in ("validate", "build", "assert"):
            assert f"{operation}_candidate_review_{family}" in text
    for constant in (
        "ALLOWED_RESEARCH_QUESTION_TYPES", "REQUIRED_RESEARCH_QUESTION_RECORD_FIELDS",
        "REQUIRED_RESEARCH_QUESTION_PREFLIGHT_FLAGS", "REQUIRED_RESEARCH_QUESTION_NON_AUTHORITY_FLAGS",
        "REQUIRED_MANUAL_RESEARCH_REQUEST_FIELDS", "REQUIRED_MANUAL_RESEARCH_REQUEST_SAFETY_FLAGS",
        "REQUIRED_MANUAL_RESEARCH_RESPONSE_FIELDS", "REQUIRED_MANUAL_RESEARCH_RESPONSE_SAFETY_FLAGS",
        "ALLOWED_RECEIPT_LABELS", "REQUIRED_ADVISORY_OUTPUT_VALIDATION_RECEIPT_FIELDS",
        "REQUIRED_ADVISORY_OUTPUT_SAFETY_FLAGS", "REQUIRED_ADVISORY_OUTPUT_REVIEW_FLAGS",
    ):
        assert f"`{constant}`" in text


def test_fixture_independence_and_exact_helpers_are_documented() -> None:
    text = RUNBOOK.read_text(encoding="utf-8")
    helpers = (
        "_question_preflight_flags", "_question_safety_flags", "_question_notice", "_question_record",
        "_request_flags", "_request_notice", "_request", "_response_flags", "_response_notice",
        "_response", "_receipt_flags", "_receipt_notice", "_receipt",
    )
    assert all(f"`{helper}`" in text for helper in helpers)
    for phrase in ("zero arguments", "independently hard-coded", "do not call or read another record fixture or result", "do not derive, copy, infer, repair, regenerate"):
        assert phrase in text


def test_all_fourteen_relationships_and_six_non_linkages_are_documented() -> None:
    text = RUNBOOK.read_text(encoding="utf-8")
    section = text[text.index("## Exact Fourteen Linkage Relationships"):text.index("## Explicit Non-Linkages")]
    assert [line.split(". ", 1)[0] for line in section.splitlines() if line[:1].isdigit()] == [str(i) for i in range(1, 15)]
    for phrase in (
        'source_research_question_record_reference["record_id"]', 'advisory_output_reference["artifact_id"]',
        "Every WP133 `cited_source_references` item appears", "all require `human_review_required` exactly `True`",
        "WP133 `uncertainties` and WP122 `uncertainty_review`", "WP133 `limitations` and WP122 `limitations_review`",
        "WP133 `known_missing_data` and WP122 `missing_data_review`",
        "WP133 `falsification_checks_performed` and WP122 `falsification_review`",
        "WP133 response label and WP122 receipt label", "WP132 requirement labels and WP122 review flags",
    ):
        assert phrase in text


def test_matrices_compatibility_and_boundaries_are_complete() -> None:
    text = RUNBOOK.read_text(encoding="utf-8")
    mismatch_cases = (
        "question_record_reference", "question_to_request_candidate", "question_to_response_candidate",
        "question_to_request_text", "question_to_response_text", "question_to_request_type",
        "question_to_response_type", "request_reference", "briefing_reference", "response_sections",
        "cited_reference_outside_request", "response_receipt_artifact", "receipt_checked_sources",
    )
    assert all(f"`{case}`" in text for case in mismatch_cases)
    for phrase in (
        "safe scalar `selected_candidate_reference`", "accepted WP122 structured reference mappings",
        "four invalid cases", "four no-echo cases", "do not fetch sources", "verify provenance",
        "verify citation support", "no file output", "`tmp_path` remains empty", "WP138 is not implemented",
        "no source", "adapter", "runtime", "product network", "storage", "paper", "live", "execution",
        "risk", "credential", "recommendation", "probability", "scoring", "ranking", "priority",
    ):
        assert phrase in text
