"""Tests for sanitized local catalog export helpers."""

from __future__ import annotations

import csv
import io

import pytest

from src.data_layer.polymarket.catalog_exports import (
    render_catalog_export_json,
    render_catalog_markets_csv,
    write_local_csv_export,
    write_local_json_export,
)
from src.data_layer.polymarket.market_catalog import MarketCatalog
from tests.data_layer.polymarket.test_snapshot_quality import _market_record


def _catalog():
    records = [
        _market_record("market-b", category="crypto"),
        _market_record("market-a", category="politics"),
    ]
    return MarketCatalog.from_market_records(records).catalog


def test_json_catalog_export_is_sanitized():
    data = render_catalog_export_json(
        _catalog(),
        dedup_summary={"markets": {"exact_duplicate_count": 1}},
    )

    assert data["export_type"] == "polymarket_local_catalog"
    assert data["unique_market_count"] == 2
    assert data["token_count"] == 4
    assert data["deduplication_summary"]["markets"]["exact_duplicate_count"] == 1
    assert data["sanitization"]["raw_source_payloads_included"] is False
    assert data["sanitization"]["credentials_included"] is False
    assert "raw_field_names" not in str(data["market_summaries"])
    assert "raw_payload" not in str(data)
    assert "private_key" not in str(data)


def test_json_catalog_export_contains_mapping_data():
    data = render_catalog_export_json(_catalog())

    assert data["condition_to_market_mappings"] == [
        {"condition_id": "cond-market-a", "market_id": "market-a"},
        {"condition_id": "cond-market-b", "market_id": "market-b"},
    ]
    assert {
        "token_id": "token-market-a-yes",
        "market_id": "market-a",
    } in data["token_to_market_mappings"]


def test_csv_catalog_export_contains_expected_headers_and_rows():
    csv_text = render_catalog_markets_csv(_catalog())
    rows = list(csv.DictReader(io.StringIO(csv_text)))

    assert rows[0]["market_id"] == "market-a"
    assert rows[1]["market_id"] == "market-b"
    assert list(rows[0].keys()) == [
        "market_id",
        "condition_id",
        "question",
        "market_status",
        "category",
        "resolution_date",
        "captured_at_utc",
        "snapshot_id",
        "outcome_labels",
        "token_ids",
    ]


def test_export_writers_accept_local_data_paths(tmp_path):
    json_path = tmp_path / "local_data" / "polymarket" / "exports" / "catalog.local.json"
    csv_path = tmp_path / "local_data" / "polymarket" / "exports" / "catalog.local.csv"

    written_json = write_local_json_export({"ok": True}, json_path)
    written_csv = write_local_csv_export("market_id\nmarket-1\n", csv_path)

    assert written_json == json_path.resolve()
    assert written_csv == csv_path.resolve()
    assert json_path.exists()
    assert csv_path.exists()


def test_export_writer_refuses_paths_outside_local_data(tmp_path):
    with pytest.raises(ValueError):
        write_local_json_export({"ok": True}, tmp_path / "catalog.local.json")
    with pytest.raises(ValueError):
        write_local_csv_export("market_id\n", tmp_path / "catalog.local.csv")


def test_export_writer_refuses_protected_paths_after_local_data(tmp_path):
    with pytest.raises(ValueError):
        write_local_json_export(
            {"ok": True},
            tmp_path / "local_data" / "src" / "catalog.local.json",
        )
