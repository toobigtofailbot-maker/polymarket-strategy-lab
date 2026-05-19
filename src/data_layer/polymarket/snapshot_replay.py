"""Offline snapshot replay helpers for WP10 local snapshot records.

Provides deterministic, finite iteration over captured snapshot records
for local research and inspection. Makes no network calls. Does not sleep,
loop forever, schedule polling, or simulate live market data. Carries no
trading, signing, credential, or order authority.

This is offline file replay for inspection only. It is not paper trading,
not simulation, and not execution.

PROHIBITED — this module must never contain:
- Network calls of any kind.
- Order placement, cancellation, signing, or submission logic.
- Credentials, API keys, private keys, wallet keys, or mnemonics.
- Authenticated request logic.
- Scheduled polling, sleep, or bot-loop behavior.
- Imports of PolymarketPublicClient or any network adapter.
"""

from __future__ import annotations

import dataclasses
from collections import defaultdict
from typing import Dict, Generator, List, Optional, Tuple

from .snapshot_models import MarketMetadataSnapshotRecord


@dataclasses.dataclass
class SnapshotTimelineEntry:
    """One entry in the snapshot timeline, sorted by captured_at_utc."""

    snapshot_id: str
    captured_at_utc: str
    market_count: int


def iter_market_records_chronological(
    records: List[MarketMetadataSnapshotRecord],
) -> Generator[MarketMetadataSnapshotRecord, None, None]:
    """Yield market records sorted by captured_at_utc ascending.

    Deterministic for records with equal timestamps (secondary sort by market_id).
    Finite — yields exactly len(records) items.
    """
    for record in sorted(records, key=lambda r: (r.captured_at_utc, r.market_id)):
        yield record


def group_records_by_snapshot_id(
    records: List[MarketMetadataSnapshotRecord],
) -> Dict[str, List[MarketMetadataSnapshotRecord]]:
    """Group records into a dict keyed by snapshot_id.

    Each value is a list of records captured in that snapshot run,
    sorted by market_id for deterministic output.
    """
    groups: Dict[str, List[MarketMetadataSnapshotRecord]] = defaultdict(list)
    for record in records:
        groups[record.snapshot_id].append(record)
    return {
        sid: sorted(recs, key=lambda r: r.market_id)
        for sid, recs in sorted(groups.items())
    }


def get_snapshot_timeline(
    records: List[MarketMetadataSnapshotRecord],
) -> List[SnapshotTimelineEntry]:
    """Return a list of SnapshotTimelineEntry sorted by captured_at_utc ascending.

    One entry per unique snapshot_id. captured_at_utc is the earliest timestamp
    in that snapshot_id group.
    """
    groups = group_records_by_snapshot_id(records)
    entries: List[SnapshotTimelineEntry] = []
    for snapshot_id, recs in groups.items():
        earliest = min(r.captured_at_utc for r in recs)
        entries.append(
            SnapshotTimelineEntry(
                snapshot_id=snapshot_id,
                captured_at_utc=earliest,
                market_count=len(recs),
            )
        )
    entries.sort(key=lambda e: e.captured_at_utc)
    return entries


def replay_snapshots(
    records: List[MarketMetadataSnapshotRecord],
    max_steps: Optional[int] = None,
) -> Generator[Tuple[int, str, List[MarketMetadataSnapshotRecord]], None, None]:
    """Finite iterator over snapshot runs in chronological order.

    Yields (step, snapshot_id, records_in_snapshot) tuples.
    step is 1-indexed.
    Stops after max_steps if provided.

    This is offline file replay for inspection only. It is not paper trading,
    not simulation, and not execution. Does not sleep or loop indefinitely.
    """
    groups = group_records_by_snapshot_id(records)
    timeline = get_snapshot_timeline(records)

    for step, entry in enumerate(timeline, start=1):
        if max_steps is not None and step > max_steps:
            return
        yield step, entry.snapshot_id, groups[entry.snapshot_id]
