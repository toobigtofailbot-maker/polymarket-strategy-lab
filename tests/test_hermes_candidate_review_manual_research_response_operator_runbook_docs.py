from pathlib import Path


RUNBOOK = Path("docs/hermes_candidate_review_manual_research_response_operator_runbook.md")


def test_runbook_exact_structure_and_contract() -> None:
    text = RUNBOOK.read_text(encoding="utf-8")
    assert text.startswith("# Hermes Candidate-Review Manual Research Response Operator Runbook\n")
    headings = [
        "Purpose", "Position After WP133", "Authority And Non-Authority", "Operator Preconditions",
        "Exact WP133 Public API", "Exact Manual Input Schema", "Exact Scalar Fields",
        "Exact Sequence Fields", "Exact Labels", "Exact Safety Flags",
        "Step 1 — Prepare Synthetic Response Content", "Step 2 — Select Structural Labels",
        "Step 3 — Build The Safety Flags", "Step 4 — Build The Non-Authority Notice",
        "Step 5 — Validate Or Build The Response", "Step 6 — Inspect The Sanitized Result",
        "Step 7 — Use The Assert Helper Only For Neutral Failure", "Failure Handling",
        "Source And Citation Non-Verification Boundary", "Sequence Ordering Is Not Ranking",
        "Temp-Only Synthetic Smoke Boundary", "No Adapter Or Automatic Field Transfer",
        "No Generated Research Output", "Human Review Boundary", "Cleanup And Repo Hygiene",
        "Forbidden Interpretations", "Future Gates", "Non-Authority Statement",
    ]
    positions = [text.index(f"## {heading}") for heading in headings]
    assert positions == sorted(positions)
    required = (
        "src/data_layer/hermes_candidate_review_manual_research_response.py",
        "ALLOWED_MANUAL_RESEARCH_RESPONSE_LABELS", "ALLOWED_RESEARCH_RESPONSE_SECTION_LABELS",
        "ALLOWED_RESEARCH_SOURCE_ASSESSMENT_LABELS", "ALLOWED_RESEARCH_COMPLETION_LABELS",
        "REQUIRED_MANUAL_RESEARCH_RESPONSE_FIELDS", "REQUIRED_MANUAL_RESEARCH_RESPONSE_SAFETY_FLAGS",
        "HermesCandidateReviewManualResearchResponseResult",
        "validate_candidate_review_manual_research_response", "build_candidate_review_manual_research_response",
        "assert_candidate_review_manual_research_response", "INVALID_MANUAL_RESEARCH_RESPONSE",
        "non-empty `str`", "non-empty `list[str]` or `tuple[str, ...]`", "exactly `True`",
        "WP132→WP133", "WP130→WP133", "tmp_path", "remains empty",
        "Contract-valid does not mean research-valid", "separate approved WP",
    )
    for token in required:
        assert token in text


def test_runbook_lists_exact_schema_and_non_authority_boundaries() -> None:
    text = RUNBOOK.read_text(encoding="utf-8")
    fields = (
        "response_id", "source_wp_context", "source_request_reference", "source_briefing_packet_reference",
        "selected_candidate_reference", "response_label", "research_question", "research_question_type",
        "question_restatement", "source_summary", "resolution_rule_analysis", "evidence_for",
        "evidence_against", "source_conflicts", "uncertainties", "known_missing_data",
        "falsification_checks_performed", "limitations", "what_would_change_the_conclusion",
        "operator_review_notes", "cited_source_references", "source_assessment_labels", "completion_labels",
        "response_sections", "operator_next_manual_step", "reviewer_acknowledgement",
        "human_review_required", "created_by_operator_note", "non_authority_notice", "safety_flags",
    )
    for field in fields:
        assert f"`{field}`" in text
    for boundary in ("no source or citation is verified", "no network", "no file output", "no product", "Human review"):
        assert boundary.lower() in text.lower()
