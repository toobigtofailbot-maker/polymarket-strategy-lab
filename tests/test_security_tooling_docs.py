from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ALLOWED_AVAILABILITY_VALUES = {
    "AVAILABLE",
    "NOT_AVAILABLE",
    "NOT_APPLICABLE",
    "NOT_RUN",
    "ERROR",
}
TOOLS = ["gitleaks", "semgrep", "npm audit", "pip-audit", "cargo audit"]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_security_tooling_status_exists():
    assert (ROOT / "docs" / "security_tooling_status.md").is_file()


def test_security_tooling_installation_exists():
    assert (ROOT / "docs" / "security_tooling_installation.md").is_file()


def test_security_tooling_requirements_mentions_all_tools():
    text = read("docs/security_tooling_requirements.md")
    for tool in TOOLS:
        assert tool in text


def test_deferred_items_log_contains_security_tool_items():
    text = read("docs/deferred_items_log.md")
    for item_id in ["WP3-D001", "WP3-D002", "WP3-D003", "WP3-D004", "WP3-D005"]:
        assert item_id in text


def test_security_tooling_status_uses_allowed_availability_values():
    text = read("docs/security_tooling_status.md")
    rows = [line for line in text.splitlines() if line.startswith("| ") and "WP3-D00" in line]
    assert rows
    for row in rows:
        columns = [column.strip() for column in row.strip().strip("|").split("|")]
        assert len(columns) == 8
        assert columns[1] in ALLOWED_AVAILABILITY_VALUES


def test_security_tooling_status_does_not_falsely_claim_all_tools_resolved():
    text = read("docs/security_tooling_status.md")
    resolved_count = text.count("RESOLVED")
    evidence_markers = ["version", "PASS", "AVAILABLE"]
    if resolved_count:
        assert all(marker in text for marker in evidence_markers)
    assert "WP3-D001" in text
    assert "WP3-D003" in text
    assert "WP3-D005" in text
    assert "remain `DEFERRED`" in text
    assert "READY_FOR_WP" in text
