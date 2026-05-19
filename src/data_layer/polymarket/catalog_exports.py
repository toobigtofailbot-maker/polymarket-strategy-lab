"""Sanitized local catalog export helpers for offline Polymarket snapshots."""

from __future__ import annotations

import csv
import io
import json
from datetime import UTC, datetime
from pathlib import Path

from .market_catalog import MarketCatalog


SAFETY_STATEMENT = (
    "Offline local data hygiene/export infrastructure only. It reads local "
    "snapshot and catalog data, does not call Polymarket APIs, does not capture "
    "new data, does not create strategy signals or trade proposals, does not "
    "backtest, does not simulate fills, does not place, cancel, sign, or "
    "simulate orders, does not authenticate, does not read credentials, writes "
    "exports only under ignored local_data/ when explicitly requested, and is "
    "not a database, scheduler, bot loop, or production service."
)

_LOCAL_DATA_PART = "local_data"
_PROTECTED_PARTS = {"src", "docs", "tests", "tools", ".git", "audits"}
_CSV_FIELDS = [
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


def render_catalog_export_json(
    catalog: MarketCatalog,
    dedup_summary: dict | None = None,
) -> dict:
    """Render sanitized JSON-compatible catalog export data."""

    summary = catalog.summary()
    latest_markets = catalog.get_latest_markets()
    markets = [
        _market_to_summary(latest_markets[market_id])
        for market_id in sorted(latest_markets.keys())
    ]
    return {
        "generated_at_utc": _utc_now_iso(),
        "export_type": "polymarket_local_catalog",
        "unique_market_count": summary["unique_market_count"],
        "token_count": summary["total_token_count"],
        "category_distribution": summary["category_distribution"],
        "status_distribution": summary["status_distribution"],
        "market_summaries": markets,
        "token_to_market_mappings": _token_to_market_mappings(markets),
        "condition_to_market_mappings": _condition_to_market_mappings(markets),
        "deduplication_summary": dedup_summary or {},
        "sanitization": {
            "raw_source_payloads_included": False,
            "credentials_included": False,
            "order_book_price_ladders_included": False,
            "local_export_only": True,
        },
        "safety_statement": SAFETY_STATEMENT,
    }


def render_catalog_markets_csv(catalog: MarketCatalog) -> str:
    """Render deterministic sanitized market rows as CSV text."""

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=_CSV_FIELDS, lineterminator="\n")
    writer.writeheader()
    latest_markets = catalog.get_latest_markets()
    for market_id in sorted(latest_markets.keys()):
        row = _market_to_summary(latest_markets[market_id])
        writer.writerow(
            {
                **row,
                "outcome_labels": json.dumps(row["outcome_labels"], sort_keys=True),
                "token_ids": json.dumps(row["token_ids"], sort_keys=True),
            }
        )
    return output.getvalue()


def write_local_json_export(data: dict, output_path: Path) -> Path:
    """Write JSON export data to an approved local_data path."""

    path = _validate_local_export_output_path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def write_local_csv_export(csv_text: str, output_path: Path) -> Path:
    """Write CSV export text to an approved local_data path."""

    path = _validate_local_export_output_path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(csv_text, encoding="utf-8")
    return path


def _validate_local_export_output_path(output_path: Path) -> Path:
    path = Path(output_path)
    resolved = path.resolve()
    parts_lower = [part.lower() for part in resolved.parts]
    if _LOCAL_DATA_PART not in parts_lower:
        raise ValueError(f"Export output path {str(path)!r} is not under local_data/.")
    local_data_index = parts_lower.index(_LOCAL_DATA_PART)
    protected_before_local_data = set(parts_lower[:local_data_index]) & _PROTECTED_PARTS
    protected_after_local_data = set(parts_lower[local_data_index + 1 :]) & {
        ".git",
        "src",
        "docs",
        "tests",
        "tools",
    }
    if protected_before_local_data or protected_after_local_data:
        raise ValueError(
            f"Export output path {str(path)!r} crosses a protected repository path."
        )
    if resolved.name in {"", ".", ".."}:
        raise ValueError("Export output path must be a file path.")
    return resolved


def _market_to_summary(market) -> dict:
    return {
        "market_id": market.market_id,
        "condition_id": market.condition_id,
        "question": market.question,
        "market_status": market.market_status,
        "category": market.category,
        "resolution_date": market.resolution_date,
        "captured_at_utc": market.captured_at_utc,
        "snapshot_id": market.snapshot_id,
        "outcome_labels": list(market.outcome_labels),
        "token_ids": list(market.token_ids),
    }


def _token_to_market_mappings(markets: list) -> list:
    mappings = []
    for market in markets:
        for token_id in market["token_ids"]:
            mappings.append({"token_id": token_id, "market_id": market["market_id"]})
    return sorted(mappings, key=lambda item: (item["token_id"], item["market_id"]))


def _condition_to_market_mappings(markets: list) -> list:
    mappings = [
        {"condition_id": market["condition_id"], "market_id": market["market_id"]}
        for market in markets
    ]
    return sorted(mappings, key=lambda item: (item["condition_id"], item["market_id"]))


def _utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()
