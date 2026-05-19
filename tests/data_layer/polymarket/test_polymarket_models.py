"""Tests for Polymarket read-only data models."""

from __future__ import annotations

import pytest

from src.data_layer.polymarket.models import (
    AdapterResult,
    MarketSummary,
    OrderBookLevel,
    OrderBookSnapshot,
    ReadOnlyRequestInfo,
)


class TestOrderBookLevel:
    def test_create(self):
        level = OrderBookLevel(price="0.65", size="100")
        assert level.price == "0.65"
        assert level.size == "100"

    def test_frozen(self):
        level = OrderBookLevel(price="0.65", size="100")
        with pytest.raises((AttributeError, TypeError)):
            level.price = "0.99"


class TestOrderBookSnapshot:
    def test_create(self):
        bids = [OrderBookLevel("0.60", "50"), OrderBookLevel("0.59", "30")]
        asks = [OrderBookLevel("0.62", "40")]
        snap = OrderBookSnapshot(
            token_id="111",
            bids=bids,
            asks=asks,
            snapshot_timestamp="2026-01-01T00:00:00Z",
            source_url="http://fake-clob/book",
        )
        assert snap.token_id == "111"
        assert len(snap.bids) == 2
        assert len(snap.asks) == 1

    def test_bids_asks_are_tuples(self):
        snap = OrderBookSnapshot(
            token_id="1",
            bids=[OrderBookLevel("0.5", "10")],
            asks=[],
            snapshot_timestamp="",
            source_url="",
        )
        assert isinstance(snap.bids, tuple)
        assert isinstance(snap.asks, tuple)

    def test_frozen(self):
        snap = OrderBookSnapshot(
            token_id="1", bids=[], asks=[], snapshot_timestamp="", source_url=""
        )
        with pytest.raises((AttributeError, TypeError)):
            snap.token_id = "2"


class TestMarketSummary:
    def test_create(self):
        m = MarketSummary(
            market_id="1",
            condition_id="0xabc",
            question="Will X happen?",
            market_status="active",
            outcome_labels=["Yes", "No"],
            token_ids=["111", "222"],
        )
        assert m.condition_id == "0xabc"
        assert "Yes" in m.outcome_labels
        assert isinstance(m.outcome_labels, tuple)
        assert isinstance(m.token_ids, tuple)

    def test_frozen(self):
        m = MarketSummary(
            market_id="1",
            condition_id="0x",
            question="Q",
            market_status="active",
            outcome_labels=[],
            token_ids=[],
        )
        with pytest.raises((AttributeError, TypeError)):
            m.market_id = "2"

    def test_optional_fields_default_none(self):
        m = MarketSummary(
            market_id="1",
            condition_id="0x",
            question="Q",
            market_status="active",
            outcome_labels=[],
            token_ids=[],
        )
        assert m.resolution_date is None
        assert m.category is None


class TestReadOnlyRequestInfo:
    def test_create_valid(self):
        info = ReadOnlyRequestInfo(
            method="GET", url="http://x/markets", status_code=200, latency_ms=50.0
        )
        assert info.method == "GET"
        assert info.status_code == 200

    def test_rejects_post(self):
        with pytest.raises(ValueError, match="GET"):
            ReadOnlyRequestInfo(
                method="POST", url="http://x", status_code=200, latency_ms=0
            )

    def test_rejects_put(self):
        with pytest.raises(ValueError):
            ReadOnlyRequestInfo(method="PUT", url="http://x", status_code=200, latency_ms=0)

    def test_rejects_patch(self):
        with pytest.raises(ValueError):
            ReadOnlyRequestInfo(method="PATCH", url="http://x", status_code=200, latency_ms=0)

    def test_rejects_delete(self):
        with pytest.raises(ValueError):
            ReadOnlyRequestInfo(method="DELETE", url="http://x", status_code=200, latency_ms=0)

    def test_frozen(self):
        info = ReadOnlyRequestInfo(method="GET", url="http://x", status_code=200, latency_ms=1)
        with pytest.raises((AttributeError, TypeError)):
            info.status_code = 500


class TestAdapterResult:
    def test_create(self):
        info = ReadOnlyRequestInfo(method="GET", url="http://x", status_code=200, latency_ms=1)
        result = AdapterResult(data={"key": "val"}, request_info=info)
        assert result.data == {"key": "val"}
        assert result.read_only_provenance == "public-get-only"

    def test_frozen(self):
        info = ReadOnlyRequestInfo(method="GET", url="http://x", status_code=200, latency_ms=1)
        result = AdapterResult(data={}, request_info=info)
        with pytest.raises((AttributeError, TypeError)):
            result.data = "changed"
