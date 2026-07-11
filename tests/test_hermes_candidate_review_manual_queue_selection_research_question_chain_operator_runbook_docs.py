from pathlib import Path


RUNBOOK = Path("docs/hermes_candidate_review_manual_queue_selection_research_question_chain_operator_runbook.md")


def test_required_headings_and_exact_chain_order() -> None:
    text = RUNBOOK.read_text(encoding="utf-8")
    headings = [
        "Purpose", "Position In The WP126 → WP128 → WP121 Chain", "Operator Preconditions",
        "Assemble And Validate A Candidate Queue", "Perform Explicit Human Selection",
        "Supply Proposed Research-Question Text", "Build The WP128 Handoff",
        "Manually Assemble The WP121 Research-Question Record", "Validate The WP121 Record",
        "Synthetic Smoke Boundary", "Human Review And Non-Authority Boundary",
        "Cleanup And Repo Hygiene", "Forbidden Interpretations", "Future Gates", "Non-Authority Statement",
    ]
    assert all(f"## {heading}" in text for heading in headings)
    assert "exact order is WP126 → WP128 → WP121" in text


def test_manual_caller_supplied_and_non_authority_boundaries() -> None:
    text = RUNBOOK.read_text(encoding="utf-8").lower()
    required = [
        "human operator—not software", "question text is explicit caller input",
        "does not generate, infer, rewrite, complete, or default question text",
        "wp128-to-wp121 transfer is manual", "no automatic adapter", "queue order is not priority",
        "scoring", "ranking", "recommendation", "prioritization", "market discovery",
        "market-data ingestion", "persistence", "export", "cli", "hermes runtime", "provider",
        "model", "prompt execution", "credentials", "private state", "paper/live", "execution",
        "risk", "orders", "synthetic and non-real", "no outputs are written or committed",
        "human review remains mandatory", "separate approved future work package",
    ]
    assert all(phrase in text for phrase in required)
