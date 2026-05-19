"""Offline deduplication helpers for local Polymarket snapshot records.

This module operates only on records already loaded from local snapshot files.
It has no network, credential, scheduler, database, strategy, or execution
authority.
"""

from __future__ import annotations

import dataclasses
import json
from typing import Dict, List


@dataclasses.dataclass(frozen=True)
class DeduplicationDecision:
    """One deterministic keep/drop decision for a local snapshot record."""

    input_index: int
    action: str
    record_type: str
    deduplication_key: tuple
    identity_key: tuple
    reason: str
    duplicate_of_index: int | None = None

    def to_dict(self) -> dict:
        data = dataclasses.asdict(self)
        data["deduplication_key"] = list(self.deduplication_key)
        data["identity_key"] = list(self.identity_key)
        return data


@dataclasses.dataclass(frozen=True)
class DeduplicationConflict:
    """Records that share an identity but have different content."""

    record_type: str
    identity_key: tuple
    input_indexes: List[int]
    fingerprints: List[str]
    reason: str

    def to_dict(self) -> dict:
        data = dataclasses.asdict(self)
        data["identity_key"] = list(self.identity_key)
        return data


@dataclasses.dataclass
class DeduplicationResult:
    """Result of deterministic local snapshot deduplication."""

    record_type: str
    records: list
    decisions: List[DeduplicationDecision]
    conflicts: List[DeduplicationConflict]
    input_count: int
    output_count: int
    exact_duplicate_count: int
    conflict_count: int

    def to_dict(self) -> dict:
        return {
            "record_type": self.record_type,
            "input_count": self.input_count,
            "output_count": self.output_count,
            "exact_duplicate_count": self.exact_duplicate_count,
            "conflict_count": self.conflict_count,
            "decisions": [decision.to_dict() for decision in self.decisions],
            "conflicts": [conflict.to_dict() for conflict in self.conflicts],
        }


def market_record_key(record: object) -> tuple:
    """Return the exact deduplication key for a market snapshot record."""

    return (
        getattr(record, "snapshot_id", None),
        getattr(record, "market_id", None),
        getattr(record, "captured_at_utc", None),
        getattr(record, "condition_id", None),
        tuple(getattr(record, "token_ids", []) or []),
        tuple(getattr(record, "outcome_labels", []) or []),
    )


def order_book_record_key(record: object) -> tuple:
    """Return the exact deduplication key for an order-book snapshot record."""

    return (
        getattr(record, "snapshot_id", None),
        getattr(record, "token_id", None),
        getattr(record, "captured_at_utc", None),
        _normalize_price_levels(getattr(record, "bids", []) or []),
        _normalize_price_levels(getattr(record, "asks", []) or []),
    )


def deduplicate_market_records(records: list) -> DeduplicationResult:
    """Remove exact duplicate market records and report retained conflicts."""

    return _deduplicate_records(
        records=records,
        record_type="market",
        exact_key_func=market_record_key,
        identity_key_func=_market_identity_key,
    )


def deduplicate_order_book_records(records: list) -> DeduplicationResult:
    """Remove exact duplicate order-book records and report retained conflicts."""

    return _deduplicate_records(
        records=records,
        record_type="order_book",
        exact_key_func=order_book_record_key,
        identity_key_func=_order_book_identity_key,
    )


def summarize_deduplication(result: DeduplicationResult) -> dict:
    """Return a sanitized JSON-compatible deduplication summary."""

    return {
        "record_type": result.record_type,
        "input_count": result.input_count,
        "output_count": result.output_count,
        "exact_duplicate_count": result.exact_duplicate_count,
        "conflict_count": result.conflict_count,
        "conflict_identity_keys": [
            list(conflict.identity_key) for conflict in result.conflicts
        ],
        "research_only": True,
        "conflicts_retained": True,
    }


def _deduplicate_records(
    *,
    records: list,
    record_type: str,
    exact_key_func,
    identity_key_func,
) -> DeduplicationResult:
    kept_records = []
    decisions: List[DeduplicationDecision] = []
    conflicts: List[DeduplicationConflict] = []
    first_seen_by_fingerprint: Dict[str, int] = {}
    fingerprints_by_identity: Dict[tuple, Dict[str, List[int]]] = {}
    duplicate_count = 0

    for index, record in enumerate(records):
        exact_key = exact_key_func(record)
        identity_key = identity_key_func(record)
        fingerprint = _record_fingerprint(record)
        identity_fingerprints = fingerprints_by_identity.setdefault(identity_key, {})
        identity_fingerprints.setdefault(fingerprint, []).append(index)

        if fingerprint in first_seen_by_fingerprint:
            duplicate_count += 1
            decisions.append(
                DeduplicationDecision(
                    input_index=index,
                    action="drop_exact_duplicate",
                    record_type=record_type,
                    deduplication_key=exact_key,
                    identity_key=identity_key,
                    reason="Exact duplicate local snapshot record.",
                    duplicate_of_index=first_seen_by_fingerprint[fingerprint],
                )
            )
            continue

        first_seen_by_fingerprint[fingerprint] = index
        kept_records.append(record)
        decisions.append(
            DeduplicationDecision(
                input_index=index,
                action="keep",
                record_type=record_type,
                deduplication_key=exact_key,
                identity_key=identity_key,
                reason="First occurrence of local snapshot record content.",
            )
        )

    for identity_key, by_fingerprint in sorted(
        fingerprints_by_identity.items(), key=lambda item: _stable_key_text(item[0])
    ):
        if len(by_fingerprint) <= 1:
            continue
        indexes = sorted(
            index for grouped_indexes in by_fingerprint.values() for index in grouped_indexes
        )
        conflicts.append(
            DeduplicationConflict(
                record_type=record_type,
                identity_key=identity_key,
                input_indexes=indexes,
                fingerprints=sorted(by_fingerprint.keys()),
                reason=(
                    "Records share the same local snapshot identity but have "
                    "different content; all non-exact records are retained."
                ),
            )
        )

    return DeduplicationResult(
        record_type=record_type,
        records=kept_records,
        decisions=decisions,
        conflicts=conflicts,
        input_count=len(records),
        output_count=len(kept_records),
        exact_duplicate_count=duplicate_count,
        conflict_count=len(conflicts),
    )


def _market_identity_key(record: object) -> tuple:
    return (
        getattr(record, "snapshot_id", None),
        getattr(record, "market_id", None),
        getattr(record, "captured_at_utc", None),
    )


def _order_book_identity_key(record: object) -> tuple:
    return (
        getattr(record, "snapshot_id", None),
        getattr(record, "token_id", None),
        getattr(record, "captured_at_utc", None),
    )


def _normalize_price_levels(levels: list) -> tuple:
    normalized = []
    for level in levels:
        if isinstance(level, dict):
            normalized.append(
                tuple((str(key), str(level[key])) for key in sorted(level.keys()))
            )
        else:
            normalized.append(str(level))
    return tuple(normalized)


def _record_fingerprint(record: object) -> str:
    if dataclasses.is_dataclass(record):
        data = dataclasses.asdict(record)
    elif isinstance(record, dict):
        data = dict(record)
    elif hasattr(record, "to_dict"):
        data = record.to_dict()
    else:
        data = vars(record)
    return json.dumps(data, sort_keys=True, separators=(",", ":"), default=str)


def _stable_key_text(key: tuple) -> str:
    return json.dumps(list(key), sort_keys=True, default=str)
