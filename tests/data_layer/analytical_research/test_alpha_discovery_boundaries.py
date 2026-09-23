from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "src" / "data_layer" / "analytical_research" / "alpha_discovery.py"
REGISTRY = ROOT / "src" / "data_layer" / "analytical_research" / "alpha_discovery_registry.py"


def test_alpha_discovery_source_boundary():
    combined = SOURCE.read_text(encoding="utf-8") + REGISTRY.read_text(encoding="utf-8")
    forbidden_imports = {
        "requests", "httpx", "aiohttp", "urllib", "websocket", "websockets",
        "src.research_runtime", "src.execution_gateway", "src.paper_trading", "src.risk",
    }
    for path in (SOURCE, REGISTRY):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import): imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom): imported.add(node.module or "")
        assert not any(any(name == bad or name.startswith(bad + ".") for bad in forbidden_imports) for name in imported)
    assert "append_alpha_factory_records" not in combined
    for token in ("while True", "time.sleep("):
        assert token not in combined
    assert '"private_key"' in combined  # rejected field name


def test_capture_requests_are_data_only():
    text = SOURCE.read_text(encoding="utf-8")
    assert '"MARKET_METADATA_REFRESH"' in text
    assert '"ORDER_BOOK"' in text
    assert '"RESOLUTION_RULE"' in text
    assert '"SOURCE_SNAPSHOT"' in text
    assert '"FEE_CONFIG"' not in text


def test_preallocation_basis_is_not_a_registry_kind():
    registry = REGISTRY.read_text(encoding="utf-8")
    assert "PreAllocationTriageBasis" not in registry
    assert "TRIAGE_DECISION" in registry and "RESEARCH_QUEUE" in registry
