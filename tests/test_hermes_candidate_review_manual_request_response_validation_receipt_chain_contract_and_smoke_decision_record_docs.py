import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "hermes_candidate_review_manual_request_response_validation_receipt_chain_contract_and_smoke_decision_record.md"

HEADINGS = [
    "# Hermes Candidate-Review Manual Request-Response-Validation Receipt Chain Contract And Smoke Decision Record",
    "## Purpose", "## Position After WP135", "## Authority And Non-Authority",
    "## Repository Contracts Reviewed", "## Compatibility Finding",
    "## Direct Three-Record Smoke Decision", "## Approved Four-Record Topology",
    "## Why WP121 Is Required", "## Exact Future Linkage Contract",
    "## Explicit Non-Linkages", "## No Field Reinterpretation",
    "## WP122 Compatibility Caveats", "## Future WP137 Smoke Requirements",
    "## No Adapter Or Automatic Transfer", "## Contract Validity Versus Lineage Consistency",
    "## Source And Citation Non-Verification Boundary", "## Output Surface Inventory",
    "## Forbidden Interpretations", "## Stop Conditions", "## Future Gates",
    "## Decision", "## Non-Authority Statement",
]


def _read() -> str:
    return DOC.read_text(encoding="utf-8")


def _section(text: str, heading: str) -> str:
    start = text.index(heading) + len(heading)
    following = [text.find("\n## ", start), text.find("\n# ", start)]
    ends = [value for value in following if value >= 0]
    return text[start:min(ends) if ends else len(text)]


def test_exact_title_and_heading_order() -> None:
    text = _read()
    assert [line for line in text.splitlines() if line.startswith("#")] == HEADINGS


def test_reviewed_paths_and_controlling_fields_are_exact() -> None:
    text = _section(_read(), "## Repository Contracts Reviewed")
    for path in (
        "src/data_layer/hermes_candidate_review_research_question_record.py",
        "src/data_layer/hermes_candidate_review_advisory_output_validation_receipt.py",
        "src/data_layer/hermes_candidate_review_manual_research_request.py",
        "src/data_layer/hermes_candidate_review_manual_research_response.py",
        "docs/hermes_candidate_review_manual_research_request_response_session_chain_operator_runbook.md",
    ):
        assert path in text
    for field in (
        "record_id", "source_research_question_record_reference", "advisory_output_reference",
        "source_references_checked", "receipt_label", "request_id",
        "source_briefing_packet_reference", "selected_candidate_reference", "research_question",
        "research_question_type", "approved_source_references", "required_response_sections",
        "response_id", "source_request_reference", "cited_source_references",
        "response_sections", "human_review_required",
    ):
        assert f"`{field}`" in text


def test_all_fourteen_future_linkages_are_present() -> None:
    text = _section(_read(), "## Exact Future Linkage Contract")
    assert [line.split(". ", 1)[0] for line in text.splitlines() if line[:1].isdigit()] == [str(i) for i in range(1, 15)]
    for phrase in (
        'WP121 `record_id` equals WP122 `source_research_question_record_reference["record_id"]`',
        'WP121 `selected_candidate_reference` equals WP132 `selected_candidate_reference`',
        'WP121 `selected_candidate_reference` equals WP133 `selected_candidate_reference`',
        'WP121 `research_question` equals WP132 `research_question`',
        'WP121 `research_question` equals WP133 `research_question`',
        'WP121 `research_question_type` equals WP132 `research_question_type`',
        'WP121 `research_question_type` equals WP133 `research_question_type`',
        'WP132 `request_id` equals WP133 `source_request_reference`',
        'WP132 `source_briefing_packet_reference` equals WP133 `source_briefing_packet_reference`',
        'WP132 `required_response_sections` equals WP133 `response_sections`',
        'Every WP133 `cited_source_references` item appears in WP132 `approved_source_references`',
        'WP133 `response_id` equals WP122 `advisory_output_reference["artifact_id"]`',
        'WP133 `cited_source_references` equals WP122 `source_references_checked`',
        'WP121, WP122, WP132, and WP133 all require `human_review_required` exactly `True`',
    ):
        assert phrase in text


def test_locked_decision_rejects_three_record_and_requires_wp121() -> None:
    text = _read()
    assert "`Direct three-record smoke: NOT APPROVED`" in text
    assert "`Required future topology: WP121 → WP132 → WP133 → WP122`" in text
    assert "This is the only approved future topology" in text
    assert "`WP121 research-question lineage is mandatory`" in text
    direct = _section(text, "## Direct Three-Record Smoke Decision")
    assert "NOT APPROVED" in direct and "cannot provide WP122's explicit WP121" in direct
    assert "WP132 request → WP133 response → WP122 validation receipt" in direct


def test_explicit_non_linkages_prevent_semantic_laundering() -> None:
    text = _section(_read(), "## Explicit Non-Linkages")
    for pair in (
        "WP133 `uncertainties` and WP122 `uncertainty_review`",
        "WP133 `limitations` and WP122 `limitations_review`",
        "WP133 `known_missing_data` and WP122 `missing_data_review`",
        "WP133 `falsification_checks_performed` and WP122 `falsification_review`",
        "WP133 response label and WP122 `receipt_label`",
        "WP132 requirement labels and WP122 review flags",
    ):
        assert pair in text
    assert "research content" in text and "review evidence" in text
    assert "semantic laundering" in text and "automatic transformation is forbidden" in text


def test_no_field_reinterpretation_or_automation() -> None:
    text = _section(_read(), "## No Field Reinterpretation")
    for field in (
        "request_id", "source_request_reference", "source_briefing_packet_reference",
        "selected_candidate_reference", "response_id", "advisory_output_reference",
    ):
        assert f"`{field}`" in text
    assert "research-question-record reference" in text
    assert "renamed, repurposed, or treated as “equivalent enough.”" in text
    automation = _section(_read(), "## No Adapter Or Automatic Transfer")
    for phrase in (
        "adapter", "converter", "bridge", "mapper", "transfer helper", "chain builder",
        "session builder", "automatic population", "inferred lineage", "auto-repair",
        "generated default", "No automatic transfer",
    ):
        assert phrase in automation


def test_wp122_caveats_and_wp137_requirements_are_complete() -> None:
    caveats = _section(_read(), "## WP122 Compatibility Caveats")
    for phrase in (
        "WP122 predates WP132 and WP133", "structured mappings", "schema discipline differs",
        "does not harden WP122", "does not add unknown-field rejection",
        "does not change result or assertion behavior", "existing accepted WP122 fixture shape",
        "source hardening requires a separate WP",
    ):
        assert phrase in caveats
    future = _section(_read(), "## Future WP137 Smoke Requirements")
    for phrase in (
        "`WP137 requires separate approval`", "`_question_record()`", "`_request()`",
        "`_response()`", "`_receipt()`", "independent zero-argument fixtures",
        "independently hard-coded", "validators must run separately",
        "linkage assertions only after validation", "valid-but-inconsistent",
        "no repair, inference, transfer, or regeneration", "no chain/session/linkage object",
        "no file output", "`tmp_path` remains empty", "WP136 creates none",
    ):
        assert phrase in future


def test_wp136_has_no_source_smoke_or_product_authority() -> None:
    decision = _section(_read(), "## Decision")
    for phrase in (
        "`WP136 implements no smoke`", "`WP136 changes no source`",
        "`WP137 requires separate approval`",
    ):
        assert phrase in decision
    authority = _section(_read(), "## Authority And Non-Authority")
    for phrase in (
        "no source", "smoke", "prompt", "model", "Hermes", "tool", "product network",
        "storage", "runtime", "recommendation", "probability", "scoring", "ranking",
        "priority", "trading", "credential", "paper", "live", "execution", "risk",
    ):
        assert phrase.lower() in authority.lower()


def test_source_and_citation_boundary_denies_verification_and_claims() -> None:
    text = _section(_read(), "## Source And Citation Non-Verification Boundary")
    for phrase in (
        "do not fetch", "browse", "search", "verify", "validate sources or citations",
        "do not establish factual correctness", "findings", "conclusions", "recommendations",
        "probabilities", "readiness",
    ):
        assert phrase in text


def test_reviewer_traps_remain_explicitly_forbidden() -> None:
    text = _read()
    assert "Briefing reference → question-record reference" in text
    assert "Request ID → question-record reference" in text
    assert "response_id`, and `advisory_output_reference` must never be treated" in text
    assert "WP136 changes no source" in text
    assert "WP136 implements no smoke" in text
    assert "No adapter" in text
    assert "No automatic transfer" in text
    assert "do not establish factual correctness" in text


def test_docs_test_reads_markdown_only_and_does_not_import_product_modules() -> None:
    source = Path(__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported_modules = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    } | {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    assert imported_modules == {"ast", "pathlib"}
    assert DOC.suffix == ".md"
