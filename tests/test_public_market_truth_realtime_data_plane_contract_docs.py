"""WP169 contract / status / roadmap / dependency posture documentation guard."""

from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "docs" / "public_market_truth_realtime_data_plane_contract.md"
PROJECT_STATUS = ROOT / "docs" / "project_status.md"
ROADMAP = ROOT / "docs" / "long_term_bot_completion_roadmap.md"
STATUS_ENTRY = ROOT / "docs" / "status_entries" / "WP169.md"


def _read(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8")


def test_contract_document_exists_and_declares_capability_and_authority() -> None:
    text = _read(CONTRACT)
    for token in (
        "PUBLIC_MARKET_TRUTH_REALTIME_DATA_PLANE",
        "Market WebSocket",
        "wss://ws-subscriptions-clob.polymarket.com/ws/market",
        "eth_chainId",
        "eth_getLogs",
        "eth_getBlockByNumber",
        "Canonical PIT authority unchanged: YES",
        "Direct Nautilus ingestion claimed: NO",
        "Paper-trading execution: NOT AUTHORIZED",
        "Live-trading execution: FORBIDDEN",
        "Merge authorized: NO",
    ):
        assert token in text, token


def test_wp169_contract_status_roadmap_and_dependency_posture() -> None:
    """R011: contract, current status, roadmap, and dependency posture are consistent."""
    contract = _read(CONTRACT)
    status = _read(PROJECT_STATUS)
    roadmap = _read(ROADMAP)
    entry = _read(STATUS_ENTRY)

    # Exact dependency posture: websockets 17.1 BSD-3-Clause install-not-vendor.
    assert "websockets==17.1" in contract
    assert "BSD-3-Clause" in contract
    assert "install-not-vendor" in contract
    assert "New direct runtime dependency: `websockets==17.1`" in entry

    # The existing exact pins remain preserved and unchanged.
    for pin in ("pyarrow==25.0.1", "duckdb==1.5.5", "polars==1.44.1", "nautilus_trader==1.231.0"):
        assert pin in contract, pin

    # Current status reconciles WP169 as merged and WP170 as the review target.
    current_phase = next(
        line for line in status.splitlines() if line.startswith("- Current phase:")
    )
    assert "WP170" in current_phase
    assert "WP169 merged: YES" in current_phase
    assert "WP169 PR: 170" in current_phase
    assert "WP169 final head: c4a09aeb33e4c271feb709622660e5e58a00b642" in current_phase
    assert "WP169 merge commit: 17df81001171988e9ca49f92dc8fd170ecaa7103" in current_phase

    # Roadmap and status entry agree on the WP169 -> WP170 sequence.
    assert "WP169" in roadmap and "WP170" in roadmap
    assert "WP169" in entry


def test_wp170_is_current_and_trading_successors_remain_separately_gated() -> None:
    """R014: WP169's contract remains historical while WP170 is current."""
    contract = _read(CONTRACT)
    roadmap = _read(ROADMAP)
    assert "WP170" in contract
    assert "separately gated" in contract
    # No successor capability is implemented in WP169.
    for forbidden in (
        "Experiment Registry",
        "Operator Cockpit",
        "Alpha Factory",
        "Execution Gateway",
        "Live",
    ):
        assert forbidden in contract, forbidden
    for successor in ("WP170", "WP171", "WP172", "WP176", "WP177", "WP178"):
        assert successor in roadmap, successor
