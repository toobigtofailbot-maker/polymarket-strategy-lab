"""Tests for PolymarketPublicClient using mocked HTTP."""

from __future__ import annotations

import json
import unittest
from unittest.mock import MagicMock, patch

import pytest

from src.data_layer.polymarket import (
    AdapterResult,
    PolymarketHTTPError,
    PolymarketPublicClient,
    PolymarketReadOnlyError,
    PolymarketResponseError,
)
from src.data_layer.polymarket.public_client import (
    DEFAULT_CLOB_BASE_URL,
    DEFAULT_GAMMA_BASE_URL,
)


FAKE_MARKETS_RESPONSE = [
    {
        "id": "1",
        "conditionId": "0xabc",
        "question": "Will BTC exceed 100k?",
        "active": "true",
        "outcomes": ["Yes", "No"],
        "tokens": [{"token_id": "111"}, {"token_id": "222"}],
    }
]

FAKE_BOOK_RESPONSE = {
    "bids": [{"price": "0.65", "size": "100"}],
    "asks": [{"price": "0.67", "size": "80"}],
}

FAKE_HEALTH_RESPONSE = {"status": "ok"}


def _make_mock_response(body: object, status: int = 200):
    raw = json.dumps(body).encode()
    mock_resp = MagicMock()
    mock_resp.status = status
    mock_resp.read.return_value = raw
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    return mock_resp


class TestPolymarketPublicClientDefaults:
    def test_default_gamma_base_url(self):
        client = PolymarketPublicClient()
        assert client._gamma_base_url == DEFAULT_GAMMA_BASE_URL.rstrip("/")

    def test_default_clob_base_url(self):
        client = PolymarketPublicClient()
        assert client._clob_base_url == DEFAULT_CLOB_BASE_URL.rstrip("/")

    def test_configurable_base_url(self):
        client = PolymarketPublicClient(
            gamma_base_url="http://fake-gamma",
            clob_base_url="http://fake-clob",
        )
        assert client._gamma_base_url == "http://fake-gamma"
        assert client._clob_base_url == "http://fake-clob"

    def test_configurable_timeout(self):
        client = PolymarketPublicClient(timeout_seconds=5.0)
        assert client._timeout == 5.0

    def test_configurable_user_agent(self):
        client = PolymarketPublicClient(user_agent="test-agent/1.0")
        assert client._user_agent == "test-agent/1.0"


class TestGetMarketsMethod:
    @patch("urllib.request.urlopen")
    def test_get_markets_calls_get(self, mock_urlopen):
        mock_urlopen.return_value = _make_mock_response(FAKE_MARKETS_RESPONSE)
        client = PolymarketPublicClient(gamma_base_url="http://fake-gamma")
        result = client.get_markets(limit=1)
        assert isinstance(result, AdapterResult)
        assert result.read_only_provenance == "public-get-only"
        assert result.request_info.method == "GET"

    @patch("urllib.request.urlopen")
    def test_get_markets_includes_limit_in_url(self, mock_urlopen):
        mock_urlopen.return_value = _make_mock_response(FAKE_MARKETS_RESPONSE)
        client = PolymarketPublicClient(gamma_base_url="http://fake-gamma")
        client.get_markets(limit=5)
        call_args = mock_urlopen.call_args
        req = call_args[0][0]
        assert "limit=5" in req.full_url

    @patch("urllib.request.urlopen")
    def test_get_markets_returns_data(self, mock_urlopen):
        mock_urlopen.return_value = _make_mock_response(FAKE_MARKETS_RESPONSE)
        client = PolymarketPublicClient(gamma_base_url="http://fake-gamma")
        result = client.get_markets()
        assert isinstance(result.data, list)
        assert len(result.data) == 1

    @patch("urllib.request.urlopen")
    def test_get_markets_http_error_raises(self, mock_urlopen):
        import urllib.error
        mock_exc = urllib.error.HTTPError(
            "http://fake-gamma/markets", 429, "Too Many Requests", {}, None
        )
        mock_exc.read = lambda: b"rate limited"
        mock_urlopen.side_effect = mock_exc
        client = PolymarketPublicClient(gamma_base_url="http://fake-gamma")
        with pytest.raises(PolymarketHTTPError) as exc_info:
            client.get_markets()
        assert exc_info.value.status == 429

    @patch("urllib.request.urlopen")
    def test_get_markets_bad_json_raises(self, mock_urlopen):
        bad_resp = MagicMock()
        bad_resp.status = 200
        bad_resp.read.return_value = b"not-json{"
        bad_resp.__enter__ = lambda s: s
        bad_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = bad_resp
        client = PolymarketPublicClient(gamma_base_url="http://fake-gamma")
        with pytest.raises(PolymarketResponseError):
            client.get_markets()


class TestGetMarketMethod:
    @patch("urllib.request.urlopen")
    def test_get_market_uses_get(self, mock_urlopen):
        mock_urlopen.return_value = _make_mock_response(FAKE_MARKETS_RESPONSE[0])
        client = PolymarketPublicClient(gamma_base_url="http://fake-gamma")
        result = client.get_market("0xabc")
        assert result.request_info.method == "GET"

    @patch("urllib.request.urlopen")
    def test_get_market_url_contains_identifier(self, mock_urlopen):
        mock_urlopen.return_value = _make_mock_response(FAKE_MARKETS_RESPONSE[0])
        client = PolymarketPublicClient(gamma_base_url="http://fake-gamma")
        client.get_market("0xdeadbeef")
        req = mock_urlopen.call_args[0][0]
        assert "0xdeadbeef" in req.full_url


class TestGetOrderBookSnapshot:
    @patch("urllib.request.urlopen")
    def test_get_order_book_snapshot_uses_get(self, mock_urlopen):
        mock_urlopen.return_value = _make_mock_response(FAKE_BOOK_RESPONSE)
        client = PolymarketPublicClient(clob_base_url="http://fake-clob")
        result = client.get_order_book_snapshot("111")
        assert result.request_info.method == "GET"

    @patch("urllib.request.urlopen")
    def test_get_order_book_snapshot_includes_token_id(self, mock_urlopen):
        mock_urlopen.return_value = _make_mock_response(FAKE_BOOK_RESPONSE)
        client = PolymarketPublicClient(clob_base_url="http://fake-clob")
        client.get_order_book_snapshot("999")
        req = mock_urlopen.call_args[0][0]
        assert "token_id=999" in req.full_url

    @patch("urllib.request.urlopen")
    def test_get_order_book_snapshot_returns_data(self, mock_urlopen):
        mock_urlopen.return_value = _make_mock_response(FAKE_BOOK_RESPONSE)
        client = PolymarketPublicClient(clob_base_url="http://fake-clob")
        result = client.get_order_book_snapshot("111")
        assert "bids" in result.data
        assert "asks" in result.data


class TestGetHealth:
    @patch("urllib.request.urlopen")
    def test_get_health_uses_get(self, mock_urlopen):
        mock_urlopen.return_value = _make_mock_response(FAKE_HEALTH_RESPONSE)
        client = PolymarketPublicClient(clob_base_url="http://fake-clob")
        result = client.get_health()
        assert result.request_info.method == "GET"

    @patch("urllib.request.urlopen")
    def test_get_health_returns_data(self, mock_urlopen):
        mock_urlopen.return_value = _make_mock_response(FAKE_HEALTH_RESPONSE)
        client = PolymarketPublicClient(clob_base_url="http://fake-clob")
        result = client.get_health()
        assert result.data == FAKE_HEALTH_RESPONSE


class TestParseMarketSummary:
    def test_parse_valid_market(self):
        raw = FAKE_MARKETS_RESPONSE[0]
        summary = PolymarketPublicClient.parse_market_summary(raw)
        assert summary.condition_id == "0xabc"
        assert summary.question == "Will BTC exceed 100k?"
        assert "Yes" in summary.outcome_labels
        assert "No" in summary.outcome_labels

    def test_parse_invalid_raises(self):
        with pytest.raises(PolymarketResponseError):
            PolymarketPublicClient.parse_market_summary("not-a-dict")


class TestParseOrderBookSnapshot:
    def test_parse_valid_book(self):
        import datetime
        ts = datetime.datetime.utcnow().isoformat()
        snap = PolymarketPublicClient.parse_order_book_snapshot(
            "111", FAKE_BOOK_RESPONSE, ts, "http://fake-clob/book"
        )
        assert snap.token_id == "111"
        assert len(snap.bids) == 1
        assert snap.bids[0].price == "0.65"
        assert len(snap.asks) == 1
        assert snap.asks[0].price == "0.67"

    def test_parse_invalid_raises(self):
        with pytest.raises(PolymarketResponseError):
            PolymarketPublicClient.parse_order_book_snapshot(
                "x", "not-a-dict", "", ""
            )


class TestRequestInfoGetOnly:
    def test_read_only_request_info_rejects_non_get(self):
        from src.data_layer.polymarket.models import ReadOnlyRequestInfo
        with pytest.raises(ValueError):
            ReadOnlyRequestInfo(method="POST", url="http://x", status_code=200, latency_ms=0)
