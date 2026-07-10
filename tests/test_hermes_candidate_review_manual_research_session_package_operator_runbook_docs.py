from pathlib import Path


RUNBOOK = Path(__file__).resolve().parents[1] / "docs" / "hermes_candidate_review_manual_research_session_package_operator_runbook.md"


def test_wp125_operator_runbook_documents_chain_and_boundaries() -> None:
    assert RUNBOOK.is_file()
    text = RUNBOOK.read_text(encoding="utf-8")
    lower = text.lower()
    assert "wp121 research question record -> wp122 advisory output validation receipt -> wp123 human decision and follow-up research task records -> wp124 manual research session package" in lower
    for phrase in (
        "manual, local, offline, advisory-only", "in-memory only", "not storage",
        "not an export or report artifact", "human review remains required",
        "safe, synthetic, non-real data", "pytest `tmp_path`", "do not commit a generated session package",
        "separate approved wp",
    ):
        assert phrase in lower
    for phrase in (
        "trading", "strategy promotion", "pr approval", "merge readiness", "paper or live readiness",
        "execution", "risk changes", "order placement", "credentials", "account access", "private state",
        "hermes runtime/provider/model/prompt runner", "prompt execution", "scheduler", "dashboard", "bot-loop",
        "daemon", "automation", "parser/loader/writer/storage", "cli", "export/report", "dependencies",
        "workflows", "lock changes", "generated artifacts",
    ):
        assert phrase in lower
