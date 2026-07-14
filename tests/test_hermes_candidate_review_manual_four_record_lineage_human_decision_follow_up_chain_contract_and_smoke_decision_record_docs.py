from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DECISION_RECORD = REPO_ROOT / "docs" / (
    "hermes_candidate_review_manual_four_record_lineage_human_decision_"
    "follow_up_chain_contract_and_smoke_decision_record.md"
)

TITLE = (
    "# Hermes Candidate-Review Manual Four-Record Lineage To Human Decision "
    "And Follow-Up Chain Contract And Smoke Decision Record"
)

HEADINGS = [
    TITLE,
    "## Purpose",
    "## Position After WP137",
    "## Authority And Non-Authority",
    "## Repository Contracts Reviewed",
    "## Compatibility Finding",
    "## Six-Record Future Smoke Decision",
    "## Approved Six-Record Topology",
    "## Direct And Inherited Lineage",
    "## Exact Future Eighteen Linkage Relationships",
    "## Explicit Non-Linkages",
    "## No Field Reinterpretation",
    "## WP123 Compatibility Caveats",
    "## Future WP139 Smoke Requirements",
    "## No Adapter Or Automatic Transfer",
    "## Contract Validity Versus Lineage Consistency",
    "## Source And Citation Non-Verification Boundary",
    "## Output Surface Inventory",
    "## Forbidden Interpretations",
    "## Stop Conditions",
    "## Future Gates",
    "## Decision",
    "## Non-Authority Statement",
]


def _text() -> str:
    return DECISION_RECORD.read_text(encoding="utf-8")


def _section(heading: str) -> str:
    text = _text()
    start = text.index(heading) + len(heading)
    next_positions = [
        text.index(candidate, start)
        for candidate in HEADINGS
        if candidate.startswith("## ") and text.find(candidate, start) >= 0
    ]
    end = min(next_positions, default=len(text))
    return text[start:end]


def test_decision_record_exists_with_exact_title_and_heading_order() -> None:
    assert DECISION_RECORD.is_file()
    text = _text()
    assert text.splitlines()[0] == TITLE
    assert [line for line in text.splitlines() if line.startswith("#")] == HEADINGS


def test_repository_contract_paths_and_wp123_public_surfaces_are_exact() -> None:
    section = _section("## Repository Contracts Reviewed")
    for path in (
        "src/data_layer/hermes_candidate_review_research_question_record.py",
        "src/data_layer/hermes_candidate_review_advisory_output_validation_receipt.py",
        "src/data_layer/hermes_candidate_review_human_decision_follow_up_record.py",
        "src/data_layer/hermes_candidate_review_manual_research_request.py",
        "src/data_layer/hermes_candidate_review_manual_research_response.py",
    ):
        assert f"`{path}`" in section

    for name in (
        "ALLOWED_HUMAN_DECISION_LABELS",
        "REQUIRED_HUMAN_DECISION_RECORD_FIELDS",
        "REQUIRED_CANDIDATE_REVIEW_RECORD_SAFETY_FLAGS",
        "HermesCandidateReviewHumanDecisionRecordResult",
        "validate_candidate_review_human_decision_record",
        "build_candidate_review_human_decision_record",
        "assert_candidate_review_human_decision_record",
        "ALLOWED_FOLLOW_UP_TASK_LABELS",
        "REQUIRED_FOLLOW_UP_RESEARCH_TASK_RECORD_FIELDS",
        "HermesCandidateReviewFollowUpResearchTaskRecordResult",
        "validate_candidate_review_follow_up_research_task_record",
        "build_candidate_review_follow_up_research_task_record",
        "assert_candidate_review_follow_up_research_task_record",
    ):
        assert f"`{name}`" in section


def test_future_six_record_smoke_is_approved_only_for_a_separate_wp() -> None:
    decision = _section("## Six-Record Future Smoke Decision")
    topology = _section("## Approved Six-Record Topology")
    assert "Six-record future smoke: APPROVED FOR A SEPARATE WP" in decision
    assert "separately approved" in decision
    assert (
        "Required future topology: WP121 → WP132 → WP133 → WP122 → "
        "WP123 decision → WP123 follow-up task"
    ) in topology
    assert "WP138 implements no smoke" in _section("## Position After WP137")
    assert "WP139 requires separate approval" in _section("## Future WP139 Smoke Requirements")


def test_direct_and_inherited_lineage_are_distinct() -> None:
    section = _section("## Direct And Inherited Lineage")
    for relationship in (
        "WP121 → WP123 decision",
        "WP122 → WP123 decision",
        "WP123 decision → WP123 follow-up task",
    ):
        assert relationship in section
    assert "WP132 and WP133 lineage is inherited through WP121 and WP122" in section
    assert "WP123 does not directly validate or reference WP132" in section
    assert "WP123 does not directly validate or reference WP133" in section
    for forbidden_claim in (
        "WP123 directly references WP132",
        "WP123 directly references WP133",
        "WP123 directly validates WP132",
        "WP123 directly validates WP133",
    ):
        assert forbidden_claim not in section


def test_all_eighteen_future_linkage_relationships_are_exact() -> None:
    section = _section("## Exact Future Eighteen Linkage Relationships")
    expected = (
        'WP121 `record_id` equals WP122 `source_research_question_record_reference["record_id"]`.',
        "WP121 `selected_candidate_reference` equals WP132 `selected_candidate_reference`.",
        "WP121 `selected_candidate_reference` equals WP133 `selected_candidate_reference`.",
        "WP121 `research_question` equals WP132 `research_question`.",
        "WP121 `research_question` equals WP133 `research_question`.",
        "WP121 `research_question_type` equals WP132 `research_question_type`.",
        "WP121 `research_question_type` equals WP133 `research_question_type`.",
        "WP132 `request_id` equals WP133 `source_request_reference`.",
        "WP132 `source_briefing_packet_reference` equals WP133 `source_briefing_packet_reference`.",
        "WP132 `required_response_sections` equals WP133 `response_sections`.",
        "Every WP133 `cited_source_references` item appears in WP132 `approved_source_references`.",
        'WP133 `response_id` equals WP122 `advisory_output_reference["artifact_id"]`.',
        "WP133 `cited_source_references` equals WP122 `source_references_checked` for the synthetic smoke.",
        'WP121 `record_id` equals WP123 decision `source_research_question_record_reference["record_id"]`.',
        'WP122 `receipt_id` equals WP123 decision `source_advisory_output_validation_receipt_reference["receipt_id"]`.',
        'WP123 decision `decision_id` equals WP123 follow-up task `source_human_decision_reference["decision_id"]`.',
        "Every WP123 decision `evidence_references_relied_on` item appears in WP122 `source_references_checked` for the synthetic smoke.",
        "WP121, WP122, WP132, WP133, WP123 decision, and WP123 follow-up task all require `human_review_required is True`.",
    )
    for number, relationship in enumerate(expected, start=1):
        assert f"{number}. {relationship}" in section
    assert "19." not in section
    assert "future test-only relationships" in section


def test_every_explicit_non_linkage_and_reason_is_present() -> None:
    section = _section("## Explicit Non-Linkages")
    for relationship in (
        "WP133 `evidence_for` and WP123 `accepted_findings`",
        "WP133 `evidence_against` and WP123 `rejected_findings`",
        "WP122 `unsupported_claims` and WP123 `rejected_findings`",
        "WP122 `human_review_notes` and WP123 `decision_basis`",
        "WP133 `uncertainties` and WP123 `unresolved_questions`",
        "WP123 decision `follow_up_research_tasks` and task `task_question`",
        "WP123 decision `follow_up_research_tasks` and task `next_manual_step`",
        "WP123 decision label and WP123 follow-up task label",
        "WP122 receipt label and WP123 decision label",
        "WP132 or WP133 labels and any WP123 label",
    ):
        assert relationship in section
    for reason in (
        "Research content is not human judgment",
        "receipt review evidence is not the human decision",
        "a decision summary is not a task object",
        "labels have different contract semantics",
    ):
        assert reason in section


def test_no_field_reinterpretation_or_automatic_content_transfer() -> None:
    section = _section("## No Field Reinterpretation")
    for statement in (
        "Request ID is not a decision reference",
        "Response ID is not a decision reference",
        "A briefing reference is not a decision reference",
        "Receipt review notes are not decision basis",
        "Response evidence is not accepted findings",
        "A decision task summary is not task question",
        "A receipt label is not a decision label",
        "A decision label is not a task label",
        "No field is renamed, repurposed, inferred, copied automatically",
    ):
        assert statement in section
    automatic = _section("## No Adapter Or Automatic Transfer")
    assert "No decision generator, task generator, adapter, converter, bridge, mapper" in automatic
    assert "No decision or task content is generated or transferred automatically" in automatic


def test_wp123_compatibility_caveats_are_complete() -> None:
    section = _section("## WP123 Compatibility Caveats")
    caveats = (
        "WP123 contains two public record families in one module",
        "WP123 accepts caller-supplied structured mappings for lineage references",
        "WP123 validates required fields but does not create cross-record lineage",
        "WP123 does not verify source/citation truth",
        "WP123 does not create tasks automatically",
        "WP123 does not transform decision summaries into task content",
        "WP138 does not harden WP123",
        "A future source-hardening package requires separate approval",
        "A successful future smoke would prove structural lineage only",
    )
    for caveat in caveats:
        assert caveat in section


def test_future_smoke_requires_independent_fixtures_and_lineage_mismatch_cases() -> None:
    section = _section("## Future WP139 Smoke Requirements")
    for fixture in (
        "_question_record()",
        "_request()",
        "_response()",
        "_receipt()",
        "_decision()",
        "_follow_up_task()",
    ):
        assert f"`{fixture}`" in section
    for requirement in (
        "independently hard-coded",
        "All six validators must run independently",
        "individually valid records can remain lineage-inconsistent",
        "create no chain/session/linkage object",
        "leave `tmp_path` empty",
    ):
        assert requirement in section


def test_validity_lineage_and_meaning_are_not_conflated() -> None:
    section = _section("## Contract Validity Versus Lineage Consistency")
    for concept in (
        "Individual record validity",
        "existing four-record lineage consistency",
        "decision-reference consistency",
        "follow-up-task-reference consistency",
        "six-record lineage consistency",
        "Factual correctness",
        "research completeness",
        "human approval meaning",
        "recommendation/readiness",
    ):
        assert concept in section
    assert "individually valid records can remain lineage-inconsistent" in section


def test_source_and_citation_truth_are_explicitly_not_verified() -> None:
    section = _section("## Source And Citation Non-Verification Boundary")
    for owner in ("WP121 evidence", "WP132 approved", "WP133 cited", "WP122 checked", "WP123 relied-on", "WP123 task"):
        assert f"{owner} references are caller-supplied" in section
    for statement in (
        "Equality and subset checks do not verify sources",
        "Human decision validity does not prove factual correctness",
        "Follow-up-task validity does not prove task necessity",
        "performs no source fetching, source verification, citation verification, browsing, or search",
    ):
        assert statement in section


def test_no_source_smoke_adapter_runtime_or_authority_is_added() -> None:
    position = _section("## Position After WP137")
    authority = _section("## Authority And Non-Authority")
    outputs = _section("## Output Surface Inventory")
    decision = _section("## Decision")
    non_authority = _section("## Non-Authority Statement")
    assert "WP138 changes no source" in position
    assert "WP138 implements no smoke" in position
    assert "No chain validator, session object, adapter, or automatic transfer is authorized" in authority
    for phrase in (
        "source code",
        "a temp smoke",
        "a six-record product test",
        "chain/session/linkage object",
        "adapter",
        "generated decision",
        "generated follow-up task",
    ):
        assert phrase in outputs
    assert "WP139 requires separate approval" in decision
    for boundary in (
        "runtime",
        "model",
        "tool",
        "product-network",
        "storage",
        "trading",
        "paper",
        "live",
        "execution",
        "risk",
        "credential",
        "recommendation",
        "probability",
        "scoring",
        "ranking",
        "priority",
        "PR authority",
    ):
        assert boundary in non_authority


def test_reviewer_trap_permissions_are_rejected_by_normative_sections() -> None:
    text = _text()
    forbidden = _section("## Forbidden Interpretations")
    assert "automatic population" in forbidden
    assert "source fetching or verification" in forbidden
    assert "PR approval/merge authority are forbidden" in forbidden
    for unauthorized_claim in (
        "WP138 implements the smoke",
        "WP138 authorizes source changes",
        "sources and citations are verified",
        "automatic task generation is authorized",
        "recommendation authority is granted",
        "probability authority is granted",
        "execution authority is granted",
        "PR approval authority is granted",
    ):
        assert unauthorized_claim not in text
