from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "docs" / "source_repo_registry.md"
ALLOWED_DECISIONS = {
    "CORE_DEPENDENCY_CANDIDATE", "FORK_CANDIDATE", "VENDOR_CANDIDATE",
    "CLEAN_ROOM_ADAPTATION", "SEPARATE_SERVICE_CANDIDATE", "STUDY_ONLY",
    "AVOID", "BLOCKED_OR_UNAVAILABLE", "DISCOVERED_NOT_AUDITED",
}
ALLOWED_LIVE_VALUES = {"YES", "NO", "UNCLEAR", "N/A"}
ALLOWED_STATUS = {"AUDITED", "BLOCKED_OR_UNAVAILABLE", "DISCOVERED_NOT_AUDITED"}

def rows():
    assert REGISTRY.is_file()
    for line in REGISTRY.read_text(encoding="utf-8").splitlines():
        if line.startswith("| ") and not line.startswith("|---") and "Repo name" not in line:
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            if len(cells) >= 10:
                yield cells

def test_registry_has_no_unaudited_candidates_after_wp2():
    bad = []
    for cells in rows():
        repo, status, decision, notes = cells[0], cells[5], cells[6], cells[9]
        if status not in ALLOWED_STATUS:
            bad.append(f"{repo}: invalid status {status}")
        if status in {"BLOCKED_OR_UNAVAILABLE", "DISCOVERED_NOT_AUDITED"} and not notes:
            bad.append(f"{repo}: missing reason")
        if status == "UNAUDITED" or decision == "PENDING":
            bad.append(f"{repo}: still pending")
    assert bad == []

def test_reuse_decisions_are_from_approved_enum():
    invalid = [f"{cells[0]}: {cells[6]}" for cells in rows() if cells[6] not in ALLOWED_DECISIONS]
    assert invalid == []

def test_live_trading_logic_values_are_from_approved_enum():
    invalid = [f"{cells[0]}: {cells[8]}" for cells in rows() if cells[8] not in ALLOWED_LIVE_VALUES]
    assert invalid == []
