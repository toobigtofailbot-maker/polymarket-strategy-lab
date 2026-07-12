from pathlib import Path


RUNBOOK = Path("docs/hermes_candidate_review_manual_research_briefing_packet_operator_runbook.md")


def _text() -> str:
    return RUNBOOK.read_text(encoding="utf-8")


def test_exact_headings_and_wp130_position() -> None:
    text = _text()
    headings = (
        "# Hermes Candidate-Review Manual Research Briefing Packet Operator Runbook",
        "## Purpose", "## Position After WP130", "## Operator Preconditions",
        "## Exact Manual Input Schema", "## Step 1 — Prepare Synthetic Briefing Content",
        "## Step 2 — Build The Safety Flags", "## Step 3 — Build The Non-Authority Notice",
        "## Step 4 — Validate And Build The Packet", "## Step 5 — Inspect The Sanitized Result",
        "## Failure Handling", "## Temp-Only Smoke Boundary", "## No Generated Research Output",
        "## Human Review Boundary", "## Cleanup And Repo Hygiene", "## Forbidden Interpretations",
        "## Future Gates", "## Non-Authority Statement",
    )
    for heading in headings:
        assert heading in text
    assert "src/data_layer/hermes_candidate_review_manual_research_briefing_packet.py" in text
    assert "operator constructs the mapping manually" in text
    assert "No WP121→WP130, WP128→WP130, or WP129→WP130 adapter exists" in text
    assert "no reusable conversion helper exists" in text
    assert "no automatic population or generated default exists" in text


def test_exact_schema_and_shape_rejections_are_documented() -> None:
    text = _text()
    scalar_fields = (
        "briefing_id", "source_wp_context", "source_research_question_record_reference",
        "selected_candidate_reference", "research_question", "research_question_type",
        "resolution_rule_context", "evidence_gap_summary", "uncertainty_summary",
        "known_missing_data", "limitations", "operator_research_instructions",
        "operator_next_manual_step", "created_by_operator_note", "non_authority_notice",
    )
    sequence_fields = (
        "source_references_to_inspect", "falsification_checks_to_perform",
        "required_response_sections",
    )
    for field in scalar_fields + sequence_fields:
        assert f"`{field}`" in text
    assert "Each must be a non-empty `str`" in text
    assert "mappings, lists, tuples, numbers, booleans, bytes, blank strings, and nested response objects are rejected" in text
    assert "non-empty `list[str]` or `tuple[str, ...]`" in text
    assert "Empty sequences, scalar strings, nested containers, mappings, numbers, booleans, bytes" in text
    assert "Sequence order is preserved only as operator-supplied order" in text
    assert "not rank, score, recommendation, priority, or importance" in text


def test_all_critical_non_authority_boundaries_are_explicit() -> None:
    text = _text()
    required = (
        "labels only", "generate no response", "constitute no prompt", "authorize no prompt execution",
        "makes no model, provider, or Hermes call", "discovery/ingestion", "scoring/ranking/priority/recommendation",
        "parser/loader/writer/storage/database", "CLI/export/report", "credentials/private state",
        "paper/live/execution/risk/order", "synthetic fixtures", "`tmp_path` remains empty",
        "Human review is mandatory", "Contract-valid does not mean factually correct",
        "requires a separate approved work package", "grants no source, research-generation, runtime",
    )
    for phrase in required:
        assert phrase in text
    assert "No file, prompt, response, model output, export, report, or committed artifact is produced" in text
    assert "no prompt generation or execution" in text
    assert "no automatic selection" in text
