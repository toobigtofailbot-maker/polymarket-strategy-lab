from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

ARCHITECTURE_DOCS = [
    "docs/architecture_skeleton.md",
    "docs/runtime_boundaries.md",
    "docs/interface_contracts.md",
    "docs/mode_separation.md",
    "docs/security_tooling_requirements.md",
]

SRC_READMES = [
    "src/README.md",
    "src/execution_gateway/README.md",
    "src/risk_engine/README.md",
    "src/strategy_modules/README.md",
    "src/data_layer/README.md",
    "src/paper_trading/README.md",
    "src/monitoring/README.md",
    "src/shared/README.md",
]


def test_architecture_docs_exist():
    missing = [path for path in ARCHITECTURE_DOCS if not (ROOT / path).is_file()]
    assert missing == []


def test_required_src_readmes_exist():
    missing = [path for path in SRC_READMES if not (ROOT / path).is_file()]
    assert missing == []



# WP8 approves executable source files under src/data_layer/polymarket/ only.
# All other src/ directories must remain README-only.
WP8_APPROVED_SRC_SCOPE = "src/data_layer/polymarket"


def test_no_executable_files_exist_under_src_except_approved_scope():
    """Executable files under src/ are forbidden except in WP8-approved scope.

    WP8 explicitly permits .py files under src/data_layer/polymarket/ for the
    read-only public data adapter. All other src/ subdirectories must remain
    README-only. This test enforces that boundary without weakening trading safety.
    """
    src = ROOT / "src"
    executable_suffixes = {".py", ".ts", ".tsx", ".js", ".jsx", ".rs", ".sh", ".ps1"}
    findings = []
    for path in src.rglob("*"):
        if not path.is_file():
            continue
        if path.name == "README.md":
            continue
        # Allow approved WP8 read-only data-layer scope.
        rel = path.relative_to(ROOT).as_posix()
        if rel.startswith(WP8_APPROVED_SRC_SCOPE + "/") or rel == WP8_APPROVED_SRC_SCOPE:
            continue
        if path.suffix.lower() in executable_suffixes:
            findings.append(rel)
    assert findings == [], (
        f"Unexpected executable files outside approved scope ({WP8_APPROVED_SRC_SCOPE}): {findings}"
    )


def test_architecture_docs_forbid_direct_strategy_order_placement():
    combined = "\n".join(
        (ROOT / path).read_text(encoding="utf-8")
        for path in ["docs/architecture_skeleton.md", "docs/runtime_boundaries.md"]
    )
    assert "Strategies produce proposals only." in combined
    assert "Strategies cannot place orders directly." in combined


def test_live_trading_remains_disabled():
    text = (ROOT / "docs" / "live_trading_authorization.md").read_text(encoding="utf-8")
    assert "LIVE TRADING STATUS: DISABLED" in text
    assert "LIVE TRADING STATUS: ENABLED" not in text


def test_security_tools_are_mandatory_before_runtime_dependency_integration():
    text = (ROOT / "docs" / "security_tooling_requirements.md").read_text(encoding="utf-8")
    assert "mandatory before runtime dependency integration" in text
    assert "vendoring" in text
    assert "live/API execution" in text
