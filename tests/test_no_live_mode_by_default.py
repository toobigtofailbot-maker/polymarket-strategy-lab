from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

SOURCE_DIRS = ["src", "app", "apps", "services", "packages"]
CONFIG_SUFFIXES = {".env", ".json", ".toml", ".yaml", ".yml", ".ini", ".cfg"}
LIVE_ORDER_PATTERNS = [
    "place_order",
    "create_order",
    "submit_order",
    "send_order",
    "cancel_order",
    "live_mode = true",
    "live_mode=true",
    "LIVE_MODE=true",
    "trading_enabled = true",
    "trading_enabled=true",
]
LIVE_ENABLED_CONFIG_PATTERNS = [
    "live_mode = true",
    "live_mode=true",
    "LIVE_MODE=true",
    "trading_enabled = true",
    "trading_enabled=true",
    "LIVE_TRADING_ENABLED=true",
]

# WP174B: src/execution_gateway/gate_b.py is the explicitly authorized Gate-B
# real cancellation boundary. It uses the literal cancel_order/cancel_orders
# methods of the official client for exposure-reducing cancellation (never
# obfuscated or dynamically constructed). Every real economic create/post stays
# Gate-C locked (GATE_C_REQUIRED), and the global prohibition on live order
# placement/enable in every other source file is preserved.
LIVE_ORDER_PATTERN_FILE_EXEMPTIONS: dict[str, set[str]] = {
    "src/execution_gateway/gate_b.py": {"cancel_order"},
}


def test_live_trading_authorization_is_disabled():
    auth_doc = ROOT / "docs" / "live_trading_authorization.md"
    assert auth_doc.is_file()
    text = auth_doc.read_text(encoding="utf-8")
    assert "LIVE TRADING STATUS: DISABLED" in text
    assert "LIVE TRADING STATUS: ENABLED" not in text


def test_no_obvious_live_order_placement_code_exists():
    findings = []
    for directory in SOURCE_DIRS:
        source_root = ROOT / directory
        if not source_root.exists():
            continue
        for path in source_root.rglob("*"):
            if path.is_file() and path.suffix.lower() in {".py", ".ts", ".tsx", ".js", ".jsx", ".json", ".toml", ".yaml", ".yml"}:
                text = path.read_text(encoding="utf-8", errors="ignore")
                rel = path.relative_to(ROOT).as_posix()
                exempted = LIVE_ORDER_PATTERN_FILE_EXEMPTIONS.get(rel, set())
                for pattern in LIVE_ORDER_PATTERNS:
                    if pattern in exempted:
                        continue
                    if pattern in text:
                        findings.append(f"{rel}: {pattern}")
    assert findings == []


def test_no_live_enabled_config_exists():
    findings = []
    for path in ROOT.rglob("*"):
        if ".git" in path.parts or path.is_dir():
            continue
        if path.suffix.lower() not in CONFIG_SUFFIXES and not path.name.startswith(".env"):
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in LIVE_ENABLED_CONFIG_PATTERNS:
            if pattern in text:
                findings.append(f"{path.relative_to(ROOT)}: {pattern}")
    assert findings == []
