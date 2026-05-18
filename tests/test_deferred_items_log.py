from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

REQUIRED_STATUSES = [
    "OPEN",
    "BLOCKED",
    "DEFERRED",
    "READY_FOR_WP",
    "RESOLVED",
    "SUPERSEDED",
]

REQUIRED_INITIAL_ITEMS = [
    "gitleaks",
    "semgrep",
    "npm / npm audit",
    "pip-audit",
    "cargo audit",
]


def test_deferred_items_log_exists():
    assert (ROOT / "docs" / "deferred_items_log.md").is_file()


def test_required_statuses_are_documented():
    text = (ROOT / "docs" / "deferred_items_log.md").read_text(encoding="utf-8")
    for status in REQUIRED_STATUSES:
        assert status in text


def test_initial_deferred_security_and_audit_entries_exist():
    text = (ROOT / "docs" / "deferred_items_log.md").read_text(encoding="utf-8")
    for item in REQUIRED_INITIAL_ITEMS:
        assert item in text


def test_deferred_table_rows_have_required_fields():
    text = (ROOT / "docs" / "deferred_items_log.md").read_text(encoding="utf-8")
    rows = [
        line
        for line in text.splitlines()
        if line.startswith("| WP3-D")
    ]
    assert rows

    for row in rows:
        columns = [column.strip() for column in row.strip().strip("|").split("|")]
        assert len(columns) == 7
        item_id, item, status, priority, reason, required_before, resolution = columns
        assert item_id
        assert item
        assert status
        assert priority
        assert reason
        assert required_before
        assert resolution
