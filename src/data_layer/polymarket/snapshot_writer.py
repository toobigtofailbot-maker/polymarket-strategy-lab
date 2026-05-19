"""Read-only snapshot writer for local Polymarket market data persistence.

Writes normalized JSONL records and JSON manifests to ignored local output
directories. Validates output path against approved roots. Performs no
network calls. Returns SnapshotWriteResult.

Write strategy: append JSONL for market and order-book records (supports
incremental runs); overwrite JSON for manifests (one per run by snapshot_id).

PROHIBITED — this module must never contain:
- Network calls of any kind.
- Order placement, cancellation, signing, or submission logic.
- Credentials, API keys, private keys, wallet keys, or mnemonics.
- Authenticated request logic.
- Scheduled polling or bot-loop behavior.
- Writes to source directories, docs, tests, audits, or the repo root.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path
from typing import List, Optional

from .snapshot_models import (
    MarketMetadataSnapshotRecord,
    OrderBookSnapshotRecord,
    SnapshotManifest,
    SnapshotWriteResult,
)

DEFAULT_OUTPUT_DIR = Path("local_data") / "polymarket" / "snapshots"

_APPROVED_SUBDIR = "local_data"
_FORBIDDEN_DIRS = frozenset({"src", "tests", "docs", "audits", ".git", "tools"})

MARKETS_JSONL_NAME = "market_metadata_snapshots.jsonl"
ORDER_BOOKS_JSONL_NAME = "order_book_snapshots.jsonl"


def _validate_output_path(path: Path) -> None:
    """Raise ValueError if path is not under an approved local_data/ root.

    Guards against accidental writes to source, test, doc, or repo-root dirs.
    """
    resolved = path.resolve()
    parts_lower = [p.lower() for p in resolved.parts]

    if _APPROVED_SUBDIR not in parts_lower:
        raise ValueError(
            f"Output path {str(path)!r} is not under an approved 'local_data/' directory. "
            "Snapshot files must be written to local_data/. "
            "Pass _allow_any_output_dir=True only in tests using tmp_path."
        )

    for forbidden in _FORBIDDEN_DIRS:
        if forbidden in parts_lower:
            raise ValueError(
                f"Output path {str(path)!r} contains forbidden directory {forbidden!r}. "
                "Snapshot writes must stay under local_data/."
            )


class SnapshotWriter:
    """Writes normalized snapshot records to local ignored output directories.

    Path validation is enforced by default. Use _allow_any_output_dir=True
    only in tests with pytest tmp_path.

    Append strategy for JSONL files supports incremental snapshot runs.
    """

    def __init__(
        self,
        output_dir: Optional[Path] = None,
        _allow_any_output_dir: bool = False,
    ) -> None:
        self._output_dir = Path(output_dir) if output_dir is not None else DEFAULT_OUTPUT_DIR
        if not _allow_any_output_dir:
            _validate_output_path(self._output_dir)

    def _ensure_dir(self) -> None:
        self._output_dir.mkdir(parents=True, exist_ok=True)

    def write_market_snapshots(
        self, records: List[MarketMetadataSnapshotRecord]
    ) -> Path:
        """Append market metadata records to JSONL file. Returns the output path."""
        self._ensure_dir()
        out_file = self._output_dir / MARKETS_JSONL_NAME
        with open(out_file, "a", encoding="utf-8") as fh:
            for record in records:
                fh.write(record.to_jsonl_line() + "\n")
        return out_file

    def write_order_book_snapshots(
        self, records: List[OrderBookSnapshotRecord]
    ) -> Path:
        """Append order-book records to JSONL file. Returns the output path."""
        self._ensure_dir()
        out_file = self._output_dir / ORDER_BOOKS_JSONL_NAME
        with open(out_file, "a", encoding="utf-8") as fh:
            for record in records:
                fh.write(record.to_jsonl_line() + "\n")
        return out_file

    def write_manifest(self, manifest: SnapshotManifest) -> Path:
        """Write run manifest as JSON. Overwrites if same snapshot_id exists."""
        self._ensure_dir()
        safe_id = manifest.snapshot_id.replace("/", "_").replace("\\", "_")
        out_file = self._output_dir / f"manifest_{safe_id}.json"
        with open(out_file, "w", encoding="utf-8") as fh:
            fh.write(manifest.to_json())
        return out_file

    def write_all(
        self,
        market_records: List[MarketMetadataSnapshotRecord],
        order_book_records: List[OrderBookSnapshotRecord],
        manifest: SnapshotManifest,
    ) -> SnapshotWriteResult:
        """Write all records and manifest. Returns SnapshotWriteResult.

        Writes market JSONL and order-book JSONL only when records are present.
        Always writes manifest.

        The manifest written to disk has output_files populated with the paths
        of all files produced during this call. The caller-provided manifest
        is not mutated; a rebuilt copy is written instead.
        """
        try:
            markets_file: Optional[str] = None
            ob_file: Optional[str] = None

            if market_records:
                markets_file = str(self.write_market_snapshots(market_records))
            if order_book_records:
                ob_file = str(self.write_order_book_snapshots(order_book_records))

            # Compute manifest path (same logic as write_manifest) so it can be
            # included in output_files before the manifest is written.
            self._ensure_dir()
            safe_id = manifest.snapshot_id.replace("/", "_").replace("\\", "_")
            manifest_path = str(self._output_dir / f"manifest_{safe_id}.json")

            # Rebuild manifest with populated output_files. Does not mutate
            # the caller-provided manifest object.
            output_files = [f for f in [markets_file, ob_file, manifest_path] if f is not None]
            updated_manifest = dataclasses.replace(manifest, output_files=output_files)
            manifest_file = str(self.write_manifest(updated_manifest))

            return SnapshotWriteResult(
                output_dir=str(self._output_dir),
                markets_file=markets_file,
                order_books_file=ob_file,
                manifest_file=manifest_file,
                markets_written=len(market_records),
                order_books_written=len(order_book_records),
                success=True,
            )
        except Exception as exc:
            return SnapshotWriteResult(
                output_dir=str(self._output_dir),
                markets_file=None,
                order_books_file=None,
                manifest_file=None,
                markets_written=0,
                order_books_written=0,
                success=False,
                error=str(exc),
            )
