"""Tests for market_catalog.py (WP11).

All tests are offline. No live network access. Uses synthetic records only.
"""

from __future__ import annotations

import pytest

from src.data_layer.polymarket.market_catalog import (
    CatalogBuildResult,
    CatalogMarket,
    CatalogOutcomeToken,
    MarketCatalog,
)
from src.data_layer.polymarket.snapshot_models import MarketMetadataSnapshotRecord


def _make_record(
    market_id: str = "market-1",
    snapshot_id: str = "snap_001",
    captured_at: str = "2026-01-01T00:00:00+00:00",
    condition_id: str | None = None,
    category: str = "crypto",
    market_status: str = "active",
    token_ids: list | None = None,
    outcome_labels: list | None = None,
) -> MarketMetadataSnapshotRecord:
    return MarketMetadataSnapshotRecord(
        snapshot_id=snapshot_id,
        captured_at_utc=captured_at,
        source="gamma-api/markets",
        adapter_version="wp10",
        market_id=market_id,
        condition_id=condition_id or f"cond-{market_id}",
        question=f"Question for {market_id}?",
        market_status=market_status,
        outcome_labels=outcome_labels or ["Yes", "No"],
        token_ids=token_ids or [f"token-{market_id}-yes", f"token-{market_id}-no"],
        resolution_date="2026-12-31",
        category=category,
        raw_field_names=["id", "question"],
        read_only_provenance="polymarket-strategy-lab/wp10-snapshot-persistence/public-get-only",
    )


class TestMarketCatalogFromRecords:
    def test_empty_records(self):
        result = MarketCatalog.from_market_records([])
        assert isinstance(result, CatalogBuildResult)
        assert result.unique_market_count == 0
        assert result.total_records_processed == 0
        assert result.catalog.count() == 0

    def test_single_record(self):
        records = [_make_record("market-1")]
        result = MarketCatalog.from_market_records(records)
        assert result.unique_market_count == 1
        assert result.total_records_processed == 1
        assert result.catalog.count() == 1

    def test_multiple_unique_markets(self):
        records = [
            _make_record("market-1"),
            _make_record("market-2"),
            _make_record("market-3"),
        ]
        result = MarketCatalog.from_market_records(records)
        assert result.unique_market_count == 3

    def test_latest_record_wins_for_same_market(self):
        old = _make_record("market-1", snapshot_id="snap_001", captured_at="2026-01-01T00:00:00+00:00")
        new = _make_record("market-1", snapshot_id="snap_002", captured_at="2026-06-01T00:00:00+00:00")
        result = MarketCatalog.from_market_records([old, new])
        catalog = result.catalog
        assert result.unique_market_count == 1
        assert result.duplicate_market_count == 1
        market = catalog.get_market("market-1")
        assert market is not None
        assert market.snapshot_id == "snap_002"

    def test_latest_record_wins_regardless_of_input_order(self):
        new = _make_record("market-1", snapshot_id="snap_002", captured_at="2026-06-01T00:00:00+00:00")
        old = _make_record("market-1", snapshot_id="snap_001", captured_at="2026-01-01T00:00:00+00:00")
        catalog = MarketCatalog.from_market_records([new, old]).catalog
        assert catalog.get_market("market-1").snapshot_id == "snap_002"


class TestMarketCatalogLookups:
    def setup_method(self):
        records = [
            _make_record(
                "market-1",
                condition_id="cond-A",
                token_ids=["token-yes-1", "token-no-1"],
                outcome_labels=["Yes", "No"],
                category="crypto",
                market_status="active",
            ),
            _make_record(
                "market-2",
                condition_id="cond-B",
                token_ids=["token-yes-2", "token-no-2"],
                category="politics",
                market_status="closed",
            ),
        ]
        self.catalog = MarketCatalog.from_market_records(records).catalog

    def test_get_market_returns_catalog_market(self):
        market = self.catalog.get_market("market-1")
        assert isinstance(market, CatalogMarket)
        assert market.market_id == "market-1"

    def test_get_market_returns_none_for_unknown(self):
        assert self.catalog.get_market("nonexistent") is None

    def test_list_market_ids_sorted(self):
        ids = self.catalog.list_market_ids()
        assert ids == ["market-1", "market-2"]

    def test_find_by_token_id(self):
        assert self.catalog.find_by_token_id("token-yes-1") == "market-1"
        assert self.catalog.find_by_token_id("token-no-2") == "market-2"
        assert self.catalog.find_by_token_id("token-unknown") is None

    def test_find_by_condition_id(self):
        assert self.catalog.find_by_condition_id("cond-A") == "market-1"
        assert self.catalog.find_by_condition_id("cond-B") == "market-2"
        assert self.catalog.find_by_condition_id("cond-nonexistent") is None

    def test_get_latest_markets_returns_all(self):
        latest = self.catalog.get_latest_markets()
        assert set(latest.keys()) == {"market-1", "market-2"}
        assert isinstance(latest["market-1"], CatalogMarket)

    def test_get_market_history_single_entry(self):
        history = self.catalog.get_market_history("market-1")
        assert len(history) == 1
        assert history[0].market_id == "market-1"

    def test_get_market_history_multiple_snapshots(self):
        records = [
            _make_record("market-1", snapshot_id="snap_001", captured_at="2026-01-01T00:00:00+00:00"),
            _make_record("market-1", snapshot_id="snap_002", captured_at="2026-06-01T00:00:00+00:00"),
        ]
        catalog = MarketCatalog.from_market_records(records).catalog
        history = catalog.get_market_history("market-1")
        assert len(history) == 2
        assert history[0].snapshot_id == "snap_001"
        assert history[1].snapshot_id == "snap_002"

    def test_get_market_history_empty_for_unknown(self):
        assert self.catalog.get_market_history("nonexistent") == []


class TestMarketCatalogSummary:
    def test_summary_keys(self):
        records = [
            _make_record("market-1", category="crypto", market_status="active"),
            _make_record("market-2", category="politics", market_status="active"),
            _make_record("market-3", category="crypto", market_status="closed"),
        ]
        catalog = MarketCatalog.from_market_records(records).catalog
        summary = catalog.summary()

        assert "unique_market_count" in summary
        assert "total_token_count" in summary
        assert "category_distribution" in summary
        assert "status_distribution" in summary
        assert "snapshot_id_count" in summary

    def test_summary_counts(self):
        records = [
            _make_record("market-1", category="crypto", market_status="active"),
            _make_record("market-2", category="crypto", market_status="closed"),
        ]
        catalog = MarketCatalog.from_market_records(records).catalog
        summary = catalog.summary()

        assert summary["unique_market_count"] == 2
        assert summary["total_token_count"] == 4  # 2 tokens per market
        assert summary["category_distribution"]["crypto"] == 2
        assert summary["status_distribution"]["active"] == 1
        assert summary["status_distribution"]["closed"] == 1


class TestCatalogOutcomeTokens:
    def test_outcome_tokens_built_correctly(self):
        record = _make_record(
            "market-1",
            token_ids=["token-yes", "token-no"],
            outcome_labels=["Yes", "No"],
        )
        catalog = MarketCatalog.from_market_records([record]).catalog
        market = catalog.get_market("market-1")
        assert len(market.outcome_tokens) == 2
        tokens = {t.outcome_label: t for t in market.outcome_tokens}
        assert tokens["Yes"].token_id == "token-yes"
        assert tokens["No"].token_id == "token-no"
        assert tokens["Yes"].market_id == "market-1"

    def test_outcome_tokens_with_mismatched_lengths(self):
        record = _make_record(
            "market-1",
            token_ids=["token-a", "token-b", "token-c"],
            outcome_labels=["Label A"],  # fewer labels than tokens
        )
        catalog = MarketCatalog.from_market_records([record]).catalog
        market = catalog.get_market("market-1")
        assert len(market.outcome_tokens) == 3
        assert market.outcome_tokens[0].outcome_label == "Label A"
        assert market.outcome_tokens[1].outcome_label == "outcome_1"


class TestNoNetworkOrTradingImports:
    def _get_function_names(self, source: str) -> set:
        import ast
        tree = ast.parse(source)
        return {
            node.name
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }

    def _get_import_names(self, source: str) -> set:
        import ast
        tree = ast.parse(source)
        names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    names.add(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    names.add(node.module)
                for alias in node.names:
                    names.add(alias.name)
        return names

    def test_market_catalog_has_no_disallowed_function_names(self):
        from pathlib import Path
        source = (
            Path(__file__).resolve().parents[3]
            / "src" / "data_layer" / "polymarket" / "market_catalog.py"
        ).read_text(encoding="utf-8")
        disallowed = {
            "place_order", "create_order", "post_order", "submit_order",
            "cancel_order", "sign_order", "execute_trade",
            "trade", "buy", "sell", "generate_signal", "create_trade_proposal",
        }
        found = self._get_function_names(source) & disallowed
        assert found == set(), f"Disallowed function names found: {found}"

    def test_market_catalog_has_no_http_mutation_literals(self):
        from pathlib import Path
        source = (
            Path(__file__).resolve().parents[3]
            / "src" / "data_layer" / "polymarket" / "market_catalog.py"
        ).read_text(encoding="utf-8")
        for method in ("POST", "PUT", "PATCH", "DELETE"):
            assert f'method="{method}"' not in source
            assert f"method='{method}'" not in source

    def test_market_catalog_does_not_import_public_client(self):
        from pathlib import Path
        source = (
            Path(__file__).resolve().parents[3]
            / "src" / "data_layer" / "polymarket" / "market_catalog.py"
        ).read_text(encoding="utf-8")
        import_names = self._get_import_names(source)
        assert "PolymarketPublicClient" not in import_names
        assert not any("public_client" in n for n in import_names)

    def test_market_catalog_has_no_network_imports(self):
        from pathlib import Path
        source = (
            Path(__file__).resolve().parents[3]
            / "src" / "data_layer" / "polymarket" / "market_catalog.py"
        ).read_text(encoding="utf-8")
        import_names = self._get_import_names(source)
        network_imports = {"urllib", "urllib.request", "http.client", "requests", "aiohttp"}
        found = import_names & network_imports
        assert found == set(), f"Network imports found: {found}"

    def test_market_catalog_has_no_credential_parameters(self):
        from pathlib import Path
        import ast
        source = (
            Path(__file__).resolve().parents[3]
            / "src" / "data_layer" / "polymarket" / "market_catalog.py"
        ).read_text(encoding="utf-8")
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for arg in node.args.args:
                    assert "private_key" not in arg.arg
                    assert "api_key" not in arg.arg
                    assert "wallet_key" not in arg.arg
                    assert "mnemonic" not in arg.arg
