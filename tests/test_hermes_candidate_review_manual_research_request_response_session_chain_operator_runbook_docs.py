from pathlib import Path

from src.data_layer.hermes_candidate_review_manual_research_request import (
    REQUIRED_MANUAL_RESEARCH_REQUEST_FIELDS,
)
from src.data_layer.hermes_candidate_review_manual_research_response import (
    REQUIRED_MANUAL_RESEARCH_RESPONSE_FIELDS,
)


RUNBOOK = Path(
    "docs/hermes_candidate_review_manual_research_request_response_session_chain_operator_runbook.md"
)


def test_runbook_exact_title_and_heading_order() -> None:
    text = RUNBOOK.read_text(encoding="utf-8")
    assert text.startswith(
        "# Hermes Candidate-Review Manual Research Request-To-Response Session Chain Operator Runbook\n"
    )
    headings = [
        "Purpose", "Position After WP134", "Authority And Non-Authority",
        "Operator Preconditions", "Existing WP132 Request API", "Existing WP133 Response API",
        "Chain Model", "No Adapter Or Automatic Transfer",
        "Step 1 — Construct The Request Explicitly", "Step 2 — Validate The Request",
        "Step 3 — Perform Research Outside This Package",
        "Step 4 — Construct The Response Explicitly", "Step 5 — Validate The Response",
        "Step 6 — Perform Manual Linkage Review", "Exact Linkage Fields",
        "Contract Validity Versus Chain Consistency", "Mismatch Handling",
        "Source And Citation Non-Verification Boundary", "Sequence Ordering Is Not Ranking",
        "Temp-Only Synthetic Smoke Boundary", "No Generated Research Output",
        "Human Review Boundary", "Failure Handling", "Cleanup And Repo Hygiene",
        "Forbidden Interpretations", "Future Gates", "Non-Authority Statement",
    ]
    positions = [text.index(f"## {heading}") for heading in headings]
    assert positions == sorted(positions)


def test_runbook_locks_both_exact_public_contracts() -> None:
    text = RUNBOOK.read_text(encoding="utf-8")
    required = (
        "src/data_layer/hermes_candidate_review_manual_research_request.py",
        "src/data_layer/hermes_candidate_review_manual_research_response.py",
        "validate_candidate_review_manual_research_request",
        "build_candidate_review_manual_research_request",
        "assert_candidate_review_manual_research_request",
        "validate_candidate_review_manual_research_response",
        "build_candidate_review_manual_research_response",
        "assert_candidate_review_manual_research_response",
        "INVALID_MANUAL_RESEARCH_REQUEST", "INVALID_MANUAL_RESEARCH_RESPONSE",
        "REQUIRED_MANUAL_RESEARCH_REQUEST_FIELDS",
        "REQUIRED_MANUAL_RESEARCH_REQUEST_SAFETY_FLAGS",
        "REQUIRED_MANUAL_RESEARCH_RESPONSE_FIELDS",
        "REQUIRED_MANUAL_RESEARCH_RESPONSE_SAFETY_FLAGS",
    )
    for token in required:
        assert token in text
    for field in REQUIRED_MANUAL_RESEARCH_REQUEST_FIELDS:
        assert f"`{field}`" in text
    for field in REQUIRED_MANUAL_RESEARCH_RESPONSE_FIELDS:
        assert f"`{field}`" in text
    assert "29 fields" in text
    assert "30 fields" in text


def test_runbook_locks_eight_manual_linkage_relationships() -> None:
    text = RUNBOOK.read_text(encoding="utf-8")
    relationships = (
        ("`request_id`", "`source_request_reference`", "exact equality"),
        ("`source_briefing_packet_reference`", "`source_briefing_packet_reference`", "exact equality"),
        ("`selected_candidate_reference`", "`selected_candidate_reference`", "exact equality"),
        ("`research_question`", "`research_question`", "exact equality"),
        ("`research_question_type`", "`research_question_type`", "exact equality"),
        ("`required_response_sections`", "`response_sections`", "exact sequence equality"),
        ("`approved_source_references`", "`cited_source_references`", "every cited reference"),
        ("`human_review_required`", "`human_review_required`", "both exactly `True`"),
    )
    table = text[text.index("## Exact Linkage Fields"):text.index(
        "## Contract Validity Versus Chain Consistency"
    )]
    for request_field, response_field, relationship in relationships:
        assert request_field in table
        assert response_field in table
        assert relationship in table


def test_runbook_preserves_manual_non_authority_boundaries() -> None:
    text = RUNBOOK.read_text(encoding="utf-8").lower()
    required = (
        "remain independent validators", "no chain validator", "no chain/session record",
        "no field is copied automatically", "explicit caller content",
        "contract validity does not establish chain consistency",
        "chain consistency does not establish factual correctness",
        "no response is generated", "no source or citation is verified",
        "tmp_path", "remains empty", "no file", "no network", "no storage",
        "paper", "live", "execution", "risk", "credential", "human review",
        "separate approved wp",
    )
    for phrase in required:
        assert phrase in text
