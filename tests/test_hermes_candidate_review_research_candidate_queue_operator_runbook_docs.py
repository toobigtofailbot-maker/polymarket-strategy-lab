from pathlib import Path


RUNBOOK = Path(__file__).resolve().parents[1] / "docs" / "hermes_candidate_review_research_candidate_queue_operator_runbook.md"


def test_wp127_operator_runbook_documents_queue_use_and_boundaries() -> None:
    assert RUNBOOK.is_file()
    text = RUNBOOK.read_text(encoding="utf-8").lower()
    for heading in (
        "purpose", "position after wp126", "operator preconditions", "safe manual candidate item assembly",
        "safe manual queue package assembly", "synthetic smoke fixture boundary", "human review boundary",
        "cleanup / repo hygiene", "forbidden interpretations", "future gates", "non-authority statement",
    ):
        assert f"## {heading}" in text
    for phrase in (
        "manual, local, offline, and advisory-only", "explicit in-memory mappings only",
        "synthetic, non-real fixture data only", "generated outputs must not be committed",
        "human review remains required", "deterministic queue contract accepted the supplied mapping",
        "does not rank opportunities", "identify edges", "authorize research priority", "approve trading",
        "separate approved work package",
    ):
        assert phrase in text
    for phrase in (
        "file output", "storage", "export", "report", "cli", "automation", "prompt execution",
        "runtime", "credentials", "account access", "paper/live", "execution", "risk", "orders",
        "market discovery", "market data ingestion", "scoring", "ranking",
    ):
        assert phrase in text
