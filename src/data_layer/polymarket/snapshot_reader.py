"""Offline snapshot reader for WP10 local JSONL snapshot files and manifests.

Reads market metadata snapshots, order-book snapshots, and manifest files
from local_data/polymarket/snapshots/ (git-ignored). Makes no network calls.
Carries no trading, signing, credential, or order authority.

PROHIBITED — this module must never contain:
- Network calls of any kind.
- Order placement, cancellation, signing, or submission logic.
- Credentials, API keys, private keys, wallet keys, or mnemonics.
- Authenticated request logic.
- Scheduled polling or bot-loop behavior.
- Imports of PolymarketPublicClient or any network adapter.
"""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path
from typing import List, Optional

from .snapshot_models import (
    MarketMetadataSnapshotRecord,
    OrderBookSnapshotRecord,
    SnapshotManifest,
)

DEFAULT_INPUT_DIR = Path("local_data") / "polymarket" / "snapshots"

MARKETS_JSONL_NAME = "market_metadata_snapshots.jsonl"
ORDER_BOOKS_JSONL_NAME = "order_book_snapshots.jsonl"
MANIFEST_GLOB = "manifest_*.json"


@dataclasses.dataclass
class SnapshotReadError:
    """Describes a single parse error encountered while reading a snapshot file."""

    file_path: str
    line_number: Optional[int]
    error_message: str


@dataclasses.dataclass
class SnapshotFileSummary:
    """Describes snapshot files found in an input directory."""

    input_dir: str
    markets_file_present: bool
    order_books_file_present: bool
    manifest_files: List[str]
    manifest_count: int


@dataclasses.dataclass
class SnapshotLoadResult:
    """Result of loading a snapshot JSONL or manifest file."""

    records: list
    errors: List[SnapshotReadError]
    lines_read: int
    lines_skipped: int
    source_file: Optional[str]


def list_snapshot_files(input_dir: Path) -> SnapshotFileSummary:
    """Return a summary of snapshot files found in input_dir.

    Does not read file contents. Handles missing directory gracefully.
    """
    input_dir = Path(input_dir)
    markets_present = (input_dir / MARKETS_JSONL_NAME).exists()
    ob_present = (input_dir / ORDER_BOOKS_JSONL_NAME).exists()

    if input_dir.exists():
        manifests = sorted(str(p) for p in input_dir.glob(MANIFEST_GLOB))
    else:
        manifests = []

    return SnapshotFileSummary(
        input_dir=str(input_dir),
        markets_file_present=markets_present,
        order_books_file_present=ob_present,
        manifest_files=manifests,
        manifest_count=len(manifests),
    )


def load_market_snapshot_records(
    input_dir: Path, strict: bool = False
) -> SnapshotLoadResult:
    """Load MarketMetadataSnapshotRecord objects from the JSONL snapshot file.

    In non-strict mode, malformed lines are skipped and collected in errors.
    In strict mode, the first malformed line raises ValueError.
    Returns an empty result if the file is absent.
    """
    input_dir = Path(input_dir)
    source_file = input_dir / MARKETS_JSONL_NAME

    if not source_file.exists():
        return SnapshotLoadResult(
            records=[],
            errors=[],
            lines_read=0,
            lines_skipped=0,
            source_file=str(source_file),
        )

    records: List[MarketMetadataSnapshotRecord] = []
    errors: List[SnapshotReadError] = []
    lines_read = 0
    lines_skipped = 0

    with open(source_file, "r", encoding="utf-8") as fh:
        for line_number, raw_line in enumerate(fh, start=1):
            line = raw_line.strip()
            if not line:
                continue
            lines_read += 1
            try:
                data = json.loads(line)
                record = _dict_to_market_record(data)
                records.append(record)
            except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
                err = SnapshotReadError(
                    file_path=str(source_file),
                    line_number=line_number,
                    error_message=str(exc),
                )
                if strict:
                    raise ValueError(
                        f"Malformed record at {source_file}:{line_number}: {exc}"
                    ) from exc
                errors.append(err)
                lines_skipped += 1

    return SnapshotLoadResult(
        records=records,
        errors=errors,
        lines_read=lines_read,
        lines_skipped=lines_skipped,
        source_file=str(source_file),
    )


def load_order_book_snapshot_records(
    input_dir: Path, strict: bool = False
) -> SnapshotLoadResult:
    """Load OrderBookSnapshotRecord objects from the JSONL snapshot file.

    In non-strict mode, malformed lines are skipped and collected in errors.
    In strict mode, the first malformed line raises ValueError.
    Returns an empty result if the file is absent.
    """
    input_dir = Path(input_dir)
    source_file = input_dir / ORDER_BOOKS_JSONL_NAME

    if not source_file.exists():
        return SnapshotLoadResult(
            records=[],
            errors=[],
            lines_read=0,
            lines_skipped=0,
            source_file=str(source_file),
        )

    records: List[OrderBookSnapshotRecord] = []
    errors: List[SnapshotReadError] = []
    lines_read = 0
    lines_skipped = 0

    with open(source_file, "r", encoding="utf-8") as fh:
        for line_number, raw_line in enumerate(fh, start=1):
            line = raw_line.strip()
            if not line:
                continue
            lines_read += 1
            try:
                data = json.loads(line)
                record = _dict_to_order_book_record(data)
                records.append(record)
            except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
                err = SnapshotReadError(
                    file_path=str(source_file),
                    line_number=line_number,
                    error_message=str(exc),
                )
                if strict:
                    raise ValueError(
                        f"Malformed record at {source_file}:{line_number}: {exc}"
                    ) from exc
                errors.append(err)
                lines_skipped += 1

    return SnapshotLoadResult(
        records=records,
        errors=errors,
        lines_read=lines_read,
        lines_skipped=lines_skipped,
        source_file=str(source_file),
    )


def load_snapshot_manifests(
    input_dir: Path, strict: bool = False
) -> SnapshotLoadResult:
    """Load SnapshotManifest objects from all manifest_*.json files in input_dir.

    In non-strict mode, malformed files are skipped and collected in errors.
    In strict mode, the first malformed file raises ValueError.
    Returns an empty result if no manifest files are found.
    """
    input_dir = Path(input_dir)

    if not input_dir.exists():
        return SnapshotLoadResult(
            records=[],
            errors=[],
            lines_read=0,
            lines_skipped=0,
            source_file=str(input_dir),
        )

    manifest_paths = sorted(input_dir.glob(MANIFEST_GLOB))
    records: List[SnapshotManifest] = []
    errors: List[SnapshotReadError] = []
    files_read = 0
    files_skipped = 0

    for manifest_path in manifest_paths:
        files_read += 1
        try:
            with open(manifest_path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            manifest = _dict_to_manifest(data)
            records.append(manifest)
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            err = SnapshotReadError(
                file_path=str(manifest_path),
                line_number=None,
                error_message=str(exc),
            )
            if strict:
                raise ValueError(
                    f"Malformed manifest {manifest_path}: {exc}"
                ) from exc
            errors.append(err)
            files_skipped += 1

    return SnapshotLoadResult(
        records=records,
        errors=errors,
        lines_read=files_read,
        lines_skipped=files_skipped,
        source_file=str(input_dir),
    )


def _dict_to_market_record(data: dict) -> MarketMetadataSnapshotRecord:
    return MarketMetadataSnapshotRecord(
        snapshot_id=data["snapshot_id"],
        captured_at_utc=data["captured_at_utc"],
        source=data["source"],
        adapter_version=data["adapter_version"],
        market_id=data["market_id"],
        condition_id=data["condition_id"],
        question=data["question"],
        market_status=data["market_status"],
        outcome_labels=data["outcome_labels"],
        token_ids=data["token_ids"],
        resolution_date=data.get("resolution_date"),
        category=data.get("category"),
        raw_field_names=data["raw_field_names"],
        read_only_provenance=data.get("read_only_provenance", ""),
    )


def _dict_to_order_book_record(data: dict) -> OrderBookSnapshotRecord:
    return OrderBookSnapshotRecord(
        snapshot_id=data["snapshot_id"],
        captured_at_utc=data["captured_at_utc"],
        source=data["source"],
        adapter_version=data["adapter_version"],
        token_id=data["token_id"],
        bids=data["bids"],
        asks=data["asks"],
        raw_field_names=data["raw_field_names"],
        read_only_provenance=data.get("read_only_provenance", ""),
    )


def _dict_to_manifest(data: dict) -> SnapshotManifest:
    return SnapshotManifest(
        snapshot_id=data["snapshot_id"],
        created_at_utc=data["created_at_utc"],
        tool_name=data["tool_name"],
        work_package=data["work_package"],
        markets_requested=data["markets_requested"],
        markets_written=data["markets_written"],
        order_books_requested=data["order_books_requested"],
        order_books_written=data["order_books_written"],
        network_used=data["network_used"],
        output_files=data["output_files"],
        notes=data["notes"],
    )
