from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT_DIR = ROOT / "audits" / "source_repos"
REQUIRED_HEADINGS = [
    "## Audit Metadata",
    "## License",
    "## Polymarket / Kalshi API Compatibility",
    "## Trading And Execution Behavior",
    "## Security Findings",
    "## Reuse Recommendation",
    "## Final Decision For Registry",
]

def slug(repo_name: str) -> str:
    if repo_name == "Archived old Polymarket V1 clients":
        return "archived_old_polymarket_v1_clients"
    return repo_name.replace("/", "_").lower()

def registry_rows():
    for line in (ROOT / "docs" / "source_repo_registry.md").read_text(encoding="utf-8").splitlines():
        if line.startswith("| ") and not line.startswith("|---") and "Repo name" not in line:
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            if len(cells) >= 10:
                yield cells

def test_required_audit_summary_files_exist():
    assert (ROOT / "docs" / "repo_reuse_decision_matrix.md").is_file()
    assert (AUDIT_DIR / "README.md").is_file()

def test_audit_file_exists_for_each_audited_registry_repo():
    missing = []
    for cells in registry_rows():
        if cells[5] == "AUDITED":
            path = AUDIT_DIR / f"{slug(cells[0])}.md"
            if not path.is_file():
                missing.append(path.relative_to(ROOT).as_posix())
    assert missing == []

def test_audit_files_contain_required_headings():
    audit_files = [p for p in AUDIT_DIR.glob("*.md") if p.name != "README.md"]
    assert audit_files
    findings = []
    for path in audit_files:
        text = path.read_text(encoding="utf-8")
        for heading in REQUIRED_HEADINGS:
            if heading not in text:
                findings.append(f"{path.relative_to(ROOT).as_posix()}: {heading}")
    assert findings == []
