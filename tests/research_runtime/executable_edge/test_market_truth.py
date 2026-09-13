from dataclasses import replace

import pytest

from src.research_runtime.executable_edge import (
    ExecutableEdgeError,
    build_market_truth_window,
    validate_market_truth_window,
)
from tests.research_runtime.nautilus_offline.test_conversion import (
    _context,
    _write_files,
    default_rows,
)


def test_wp168_adapter_preserves_lineage_order_book_trade_and_continuity(tmp_path) -> None:
    source = _write_files(tmp_path / "source", [default_rows()])
    window = build_market_truth_window(source, _context())
    assert window.lineage_id.startswith("markettruthwindow:sha256:")
    assert window.source_external_dataset_id == source.descriptor.external_dataset_id
    assert window.continuity_complete is True
    assert tuple(event.kind for event in window.events) == ("BOOK", "TRADE")
    assert window.events[0].asks == (("0.6", "50"),)
    assert window.first_receive_time_ns <= window.last_receive_time_ns
    assert window.advisory_only and window.no_execution_authority
    with pytest.raises(ExecutableEdgeError, match="MARKET_TRUTH_INVALID"):
        validate_market_truth_window(replace(window, continuity_complete=False))
    gapped = replace(source, descriptor=replace(source.descriptor, known_gap_policy="KNOWN_GAPS"))
    assert build_market_truth_window(gapped, _context()).continuity_complete is False


def test_wp172_boundary_and_repo_truth() -> None:
    from pathlib import Path
    source = "\n".join(
        path.read_text(encoding="utf-8").lower()
        for path in Path("src/research_runtime/executable_edge").glob("*.py")
    )
    for forbidden in ("import requests", "import httpx", "import websocket", "api_key", "private_key", "submit_order", "cancel_order"):
        assert forbidden not in source
