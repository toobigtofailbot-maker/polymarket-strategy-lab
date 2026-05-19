"""Tests for snapshot_replay.py (WP11).

All tests are offline. No live network access. Replay is finite and does not sleep.
"""

from __future__ import annotations

import time

import pytest

from src.data_layer.polymarket.snapshot_models import MarketMetadataSnapshotRecord
from src.data_layer.polymarket.snapshot_replay import (
    SnapshotTimelineEntry,
    get_snapshot_timeline,
    group_records_by_snapshot_id,
    iter_market_records_chronological,
    replay_snapshots,
)


def _make_record(
    market_id: str,
    snapshot_id: str = "snap_001",
    captured_at: str = "2026-01-01T00:00:00+00:00",
) -> MarketMetadataSnapshotRecord:
    return MarketMetadataSnapshotRecord(
        snapshot_id=snapshot_id,
        captured_at_utc=captured_at,
        source="gamma-api/markets",
        adapter_version="wp10",
        market_id=market_id,
        condition_id=f"cond-{market_id}",
        question=f"Q {market_id}?",
        market_status="active",
        outcome_labels=["Yes", "No"],
        token_ids=[f"tok-{market_id}-yes", f"tok-{market_id}-no"],
        resolution_date=None,
        category="test",
        raw_field_names=["id"],
        read_only_provenance="polymarket-strategy-lab/wp10-snapshot-persistence/public-get-only",
    )


class TestIterMarketRecordsChronological:
    def test_empty_input(self):
        result = list(iter_market_records_chronological([]))
        assert result == []

    def test_single_record(self):
        rec = _make_record("market-1")
        result = list(iter_market_records_chronological([rec]))
        assert len(result) == 1
        assert result[0].market_id == "market-1"

    def test_sorted_by_captured_at_utc(self):
        r1 = _make_record("market-1", captured_at="2026-06-01T00:00:00+00:00")
        r2 = _make_record("market-2", captured_at="2026-01-01T00:00:00+00:00")
        r3 = _make_record("market-3", captured_at="2026-03-01T00:00:00+00:00")

        result = list(iter_market_records_chronological([r1, r2, r3]))
        assert [r.market_id for r in result] == ["market-2", "market-3", "market-1"]

    def test_stable_secondary_sort_by_market_id(self):
        r1 = _make_record("market-b", captured_at="2026-01-01T00:00:00+00:00")
        r2 = _make_record("market-a", captured_at="2026-01-01T00:00:00+00:00")

        result = list(iter_market_records_chronological([r1, r2]))
        assert [r.market_id for r in result] == ["market-a", "market-b"]

    def test_is_generator(self):
        import types
        result = iter_market_records_chronological([])
        assert isinstance(result, types.GeneratorType)

    def test_is_finite_and_does_not_sleep(self):
        records = [_make_record(f"market-{i}") for i in range(10)]
        start = time.monotonic()
        list(iter_market_records_chronological(records))
        elapsed = time.monotonic() - start
        assert elapsed < 1.0, "iter_market_records_chronological took too long (sleeping?)"


class TestGroupRecordsBySnapshotId:
    def test_empty_input(self):
        result = group_records_by_snapshot_id([])
        assert result == {}

    def test_groups_correctly(self):
        r1 = _make_record("market-1", snapshot_id="snap_001")
        r2 = _make_record("market-2", snapshot_id="snap_002")
        r3 = _make_record("market-3", snapshot_id="snap_001")

        result = group_records_by_snapshot_id([r1, r2, r3])
        assert set(result.keys()) == {"snap_001", "snap_002"}
        assert len(result["snap_001"]) == 2
        assert len(result["snap_002"]) == 1

    def test_within_group_sorted_by_market_id(self):
        r1 = _make_record("market-b", snapshot_id="snap_001")
        r2 = _make_record("market-a", snapshot_id="snap_001")

        result = group_records_by_snapshot_id([r1, r2])
        ids = [r.market_id for r in result["snap_001"]]
        assert ids == ["market-a", "market-b"]

    def test_deterministic_across_calls(self):
        records = [
            _make_record("market-c", snapshot_id="snap_001"),
            _make_record("market-a", snapshot_id="snap_002"),
            _make_record("market-b", snapshot_id="snap_001"),
        ]
        r1 = group_records_by_snapshot_id(records)
        r2 = group_records_by_snapshot_id(records)
        assert [r.market_id for r in r1["snap_001"]] == [r.market_id for r in r2["snap_001"]]


class TestGetSnapshotTimeline:
    def test_empty_input(self):
        result = get_snapshot_timeline([])
        assert result == []

    def test_single_snapshot(self):
        records = [
            _make_record("market-1", snapshot_id="snap_001", captured_at="2026-01-01T00:00:00+00:00"),
            _make_record("market-2", snapshot_id="snap_001", captured_at="2026-01-01T00:00:00+00:00"),
        ]
        result = get_snapshot_timeline(records)
        assert len(result) == 1
        assert isinstance(result[0], SnapshotTimelineEntry)
        assert result[0].snapshot_id == "snap_001"
        assert result[0].market_count == 2

    def test_sorted_by_captured_at_utc(self):
        records = [
            _make_record("market-1", snapshot_id="snap_002", captured_at="2026-06-01T00:00:00+00:00"),
            _make_record("market-2", snapshot_id="snap_001", captured_at="2026-01-01T00:00:00+00:00"),
        ]
        result = get_snapshot_timeline(records)
        assert result[0].snapshot_id == "snap_001"
        assert result[1].snapshot_id == "snap_002"

    def test_earliest_timestamp_used_per_snapshot(self):
        records = [
            _make_record("market-1", snapshot_id="snap_001", captured_at="2026-01-01T06:00:00+00:00"),
            _make_record("market-2", snapshot_id="snap_001", captured_at="2026-01-01T00:00:00+00:00"),
        ]
        result = get_snapshot_timeline(records)
        assert result[0].captured_at_utc == "2026-01-01T00:00:00+00:00"


class TestReplaySnapshots:
    def test_empty_input(self):
        result = list(replay_snapshots([]))
        assert result == []

    def test_yields_tuples(self):
        records = [_make_record("market-1", snapshot_id="snap_001")]
        result = list(replay_snapshots(records))
        assert len(result) == 1
        step, snap_id, recs = result[0]
        assert step == 1
        assert snap_id == "snap_001"
        assert len(recs) == 1

    def test_step_is_1_indexed(self):
        r1 = _make_record("market-1", snapshot_id="snap_001", captured_at="2026-01-01T00:00:00+00:00")
        r2 = _make_record("market-2", snapshot_id="snap_002", captured_at="2026-06-01T00:00:00+00:00")
        result = list(replay_snapshots([r1, r2]))
        steps = [t[0] for t in result]
        assert steps == [1, 2]

    def test_chronological_order(self):
        r1 = _make_record("market-1", snapshot_id="snap_002", captured_at="2026-06-01T00:00:00+00:00")
        r2 = _make_record("market-2", snapshot_id="snap_001", captured_at="2026-01-01T00:00:00+00:00")
        result = list(replay_snapshots([r1, r2]))
        snap_ids = [t[1] for t in result]
        assert snap_ids == ["snap_001", "snap_002"]

    def test_max_steps_limits_output(self):
        records = [
            _make_record("market-1", snapshot_id="snap_001", captured_at="2026-01-01T00:00:00+00:00"),
            _make_record("market-2", snapshot_id="snap_002", captured_at="2026-02-01T00:00:00+00:00"),
            _make_record("market-3", snapshot_id="snap_003", captured_at="2026-03-01T00:00:00+00:00"),
        ]
        result = list(replay_snapshots(records, max_steps=2))
        assert len(result) == 2

    def test_max_steps_none_yields_all(self):
        records = [
            _make_record("market-1", snapshot_id="snap_001", captured_at="2026-01-01T00:00:00+00:00"),
            _make_record("market-2", snapshot_id="snap_002", captured_at="2026-02-01T00:00:00+00:00"),
        ]
        result = list(replay_snapshots(records, max_steps=None))
        assert len(result) == 2

    def test_is_finite_and_does_not_sleep(self):
        records = [
            _make_record(f"market-{i}", snapshot_id=f"snap_{i:03d}",
                         captured_at=f"2026-0{i%9+1}-01T00:00:00+00:00")
            for i in range(5)
        ]
        start = time.monotonic()
        list(replay_snapshots(records))
        elapsed = time.monotonic() - start
        assert elapsed < 1.0, "replay_snapshots took too long (sleeping?)"

    def test_is_generator(self):
        import types
        result = replay_snapshots([])
        assert isinstance(result, types.GeneratorType)


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

    def test_snapshot_replay_has_no_disallowed_function_names(self):
        from pathlib import Path
        source = (
            Path(__file__).resolve().parents[3]
            / "src" / "data_layer" / "polymarket" / "snapshot_replay.py"
        ).read_text(encoding="utf-8")
        disallowed = {
            "place_order", "create_order", "post_order", "submit_order",
            "cancel_order", "sign_order", "execute_trade",
            "trade", "buy", "sell", "generate_signal", "create_trade_proposal",
        }
        found = self._get_function_names(source) & disallowed
        assert found == set(), f"Disallowed function names found: {found}"

    def test_snapshot_replay_has_no_http_mutation_literals(self):
        from pathlib import Path
        source = (
            Path(__file__).resolve().parents[3]
            / "src" / "data_layer" / "polymarket" / "snapshot_replay.py"
        ).read_text(encoding="utf-8")
        for method in ("POST", "PUT", "PATCH", "DELETE"):
            assert f'method="{method}"' not in source
            assert f"method='{method}'" not in source

    def test_snapshot_replay_has_no_sleep(self):
        from pathlib import Path
        source = (
            Path(__file__).resolve().parents[3]
            / "src" / "data_layer" / "polymarket" / "snapshot_replay.py"
        ).read_text(encoding="utf-8")
        assert "time.sleep" not in source
        assert "asyncio.sleep" not in source

    def test_snapshot_replay_does_not_import_public_client(self):
        from pathlib import Path
        source = (
            Path(__file__).resolve().parents[3]
            / "src" / "data_layer" / "polymarket" / "snapshot_replay.py"
        ).read_text(encoding="utf-8")
        import_names = self._get_import_names(source)
        assert "PolymarketPublicClient" not in import_names
        assert not any("public_client" in n for n in import_names)

    def test_snapshot_replay_has_no_network_imports(self):
        from pathlib import Path
        source = (
            Path(__file__).resolve().parents[3]
            / "src" / "data_layer" / "polymarket" / "snapshot_replay.py"
        ).read_text(encoding="utf-8")
        import_names = self._get_import_names(source)
        network_imports = {"urllib", "urllib.request", "http.client", "requests", "aiohttp"}
        found = import_names & network_imports
        assert found == set(), f"Network imports found: {found}"
