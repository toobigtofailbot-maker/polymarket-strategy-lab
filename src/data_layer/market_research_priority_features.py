"""Local/offline/read-only Market Research Priority feature extraction foundation.

WP51 first feature-extraction foundation. Advisory-only. Not a trading signal.
Not expected return. Not investment advice. Not position sizing. Not an execution
instruction. Human review required before any use.

This module:
- consumes existing local/offline snapshot artifacts and data-layer models only;
- produces prepared run_context and market_context dicts for the WP49 core scorer;
- performs no network access;
- writes no files;
- adds no CLI;
- adds no export/report writer;
- adds no trading, execution, credentials, wallet, Hermes, LLM, scheduler,
  dashboard, database, or polling behavior.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional

from src.data_layer.polymarket.snapshot_models import (
    MarketMetadataSnapshotRecord,
    OrderBookSnapshotRecord,
    SnapshotManifest,
)

FEATURE_EXTRACTION_SCOPE = "local/offline/read-only feature extraction foundation"
FEATURE_EXTRACTION_VERSION = "wp51-v1"

DEFAULT_METADATA_FRESHNESS_THRESHOLD_SECONDS: int = 86400   # 24 hours
DEFAULT_ORDERBOOK_FRESHNESS_THRESHOLD_SECONDS: int = 3600   # 1 hour

_ADVISORY_LABEL = "ADVISORY_ONLY_HUMAN_REVIEW_REQUIRED"
_MAX_LIQUIDITY_PROXY = 0.5  # cap — never implies executable liquidity


# ── Index helpers ─────────────────────────────────────────────────────────────

def build_manifest_index(
    manifests: Iterable[SnapshotManifest],
) -> dict:
    """Return a dict of snapshot_id → SnapshotManifest for fast provenance lookup."""
    return {m.snapshot_id: m for m in manifests}


def index_order_books_by_token_id(
    order_books: Iterable[OrderBookSnapshotRecord],
) -> dict:
    """Return a dict of token_id → list[OrderBookSnapshotRecord] for all supplied records."""
    index: dict = {}
    for ob in order_books:
        index.setdefault(ob.token_id, []).append(ob)
    return index


# ── Staleness helpers ─────────────────────────────────────────────────────────

def _parse_utc(ts: Optional[str]) -> Optional[datetime]:
    """Parse an ISO 8601 UTC string. Returns None on failure."""
    if not ts:
        return None
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, AttributeError):
        return None


def _age_seconds(ts: Optional[str], reference: datetime) -> Optional[float]:
    """Return age in seconds between ts and reference, or None if ts is unparseable."""
    dt = _parse_utc(ts)
    if dt is None:
        return None
    delta = reference - dt
    return delta.total_seconds()


def _build_staleness(
    record: MarketMetadataSnapshotRecord,
    order_book_records: list,
    generated_at_utc: datetime,
    metadata_threshold: int,
    orderbook_threshold: int,
) -> dict:
    """Build the staleness sub-dict for a market_context."""
    stale_inputs = []
    staleness_warnings = []
    requires_recapture = False

    meta_age = _age_seconds(record.captured_at_utc, generated_at_utc)
    if meta_age is None:
        stale_inputs.append("metadata_snapshot (unparseable timestamp)")
        staleness_warnings.append(
            "Metadata snapshot timestamp is unparseable; treating as stale."
        )
        requires_recapture = True
        staleness_flag = True
    elif meta_age > metadata_threshold:
        stale_inputs.append(f"metadata_snapshot (age={meta_age:.0f}s > {metadata_threshold}s)")
        staleness_warnings.append(
            f"Metadata snapshot is {meta_age:.0f}s old (threshold {metadata_threshold}s); "
            "recapture required before use."
        )
        requires_recapture = True
        staleness_flag = True
    else:
        staleness_flag = False

    # Order book staleness: check all supplied records
    ob_ages = []
    for ob in order_book_records:
        age = _age_seconds(ob.captured_at_utc, generated_at_utc)
        if age is None:
            stale_inputs.append(f"order_book_snapshot (token={ob.token_id}, unparseable)")
            staleness_warnings.append(
                f"Order book snapshot for token {ob.token_id} has unparseable timestamp."
            )
            requires_recapture = True
            staleness_flag = True
        else:
            ob_ages.append(age)
            if age > orderbook_threshold:
                stale_inputs.append(
                    f"order_book_snapshot (token={ob.token_id}, age={age:.0f}s > {orderbook_threshold}s)"
                )
                staleness_warnings.append(
                    f"Order book snapshot for token {ob.token_id} is {age:.0f}s old "
                    f"(threshold {orderbook_threshold}s)."
                )
                requires_recapture = True
                staleness_flag = True

    # Representative snapshot age for display
    snapshot_age = meta_age if meta_age is not None else None

    return {
        "staleness_flag": staleness_flag,
        "snapshot_age_seconds": snapshot_age,
        "freshness_threshold_seconds": metadata_threshold,
        "stale_inputs": stale_inputs,
        "staleness_warning": "; ".join(staleness_warnings) if staleness_warnings else None,
        "requires_recapture_before_use": requires_recapture,
    }


# ── Provenance helpers ────────────────────────────────────────────────────────

def _build_provenance(
    record: MarketMetadataSnapshotRecord,
    manifest_index: Optional[dict],
) -> dict:
    """Build the provenance sub-dict for a market_context."""
    snapshot_manifest_ids = []
    source_export_paths = []
    capture_session_ids = []
    guard_policy_version = None
    quality_report_ids = []
    input_artifact_types = ["market_metadata_snapshot"]

    if manifest_index:
        manifest = manifest_index.get(record.snapshot_id)
        if manifest is not None:
            snapshot_manifest_ids.append(manifest.snapshot_id)
            capture_session_ids.append(manifest.snapshot_id)
            source_export_paths.extend(manifest.output_files or [])
            # Guard policy not stored in manifest; omit to avoid inventing values
        # No else: absent manifest → empty lists (do not invent IDs)

    return {
        "snapshot_manifest_ids": snapshot_manifest_ids,
        "source_export_paths": source_export_paths,
        "capture_session_ids": capture_session_ids,
        "guard_policy_version": guard_policy_version,
        "quality_report_ids": quality_report_ids,
        "input_artifact_types": input_artifact_types,
    }


# ── Missing-data helpers ──────────────────────────────────────────────────────

def _build_missing_data(
    record: MarketMetadataSnapshotRecord,
    ob_records: list,
    warnings: list,
) -> dict:
    missing_fields = []
    has_warning = False

    missing_category = not bool(record.category)
    if missing_category:
        missing_fields.append("category")
        warnings.append("category field is absent")
        has_warning = True

    token_ids = record.token_ids or []
    outcome_labels = record.outcome_labels or []
    missing_outcome_tokens = (len(token_ids) == 0)
    if missing_outcome_tokens:
        missing_fields.append("token_ids")
        warnings.append("no token_ids found in record")
        has_warning = True

    # Token/label mismatch
    labels_mismatch = len(token_ids) > 0 and len(outcome_labels) != len(token_ids)
    if labels_mismatch:
        missing_fields.append("outcome_label_mismatch")
        warnings.append(
            f"outcome_labels count ({len(outcome_labels)}) != "
            f"token_ids count ({len(token_ids)})"
        )
        has_warning = True

    missing_order_book = len(ob_records) == 0
    if missing_order_book:
        missing_fields.append("order_book_snapshots")
        warnings.append("no order book records supplied for this market")
        has_warning = True

    missing_resolution_source = not bool(record.resolution_date)
    if missing_resolution_source:
        missing_fields.append("resolution_date")
        warnings.append("resolution_date is absent")
        has_warning = True

    reason = "; ".join(warnings) if warnings else None

    return {
        "missing_data_warning": has_warning,
        "missing_metadata_fields": missing_fields,
        "missing_order_book": missing_order_book,
        "missing_outcome_tokens": missing_outcome_tokens,
        "missing_category": missing_category,
        "missing_resolution_source": missing_resolution_source,
        "insufficient_coverage_reason": reason,
    }


# ── Quality gates helpers ─────────────────────────────────────────────────────

def _build_quality_gates(
    missing_data: dict,
    staleness: dict,
    manifest_index: Optional[dict],
    record: MarketMetadataSnapshotRecord,
) -> dict:
    """Build quality_gates sub-dict from extracted feature state."""
    quality_warnings = []

    if staleness["staleness_flag"]:
        quality_warnings.append("stale_snapshot")
    if missing_data["missing_data_warning"]:
        quality_warnings.append("missing_data")
    has_provenance = bool(
        manifest_index and manifest_index.get(record.snapshot_id) is not None
    )
    if not has_provenance:
        quality_warnings.append("no_manifest_provenance")

    if quality_warnings and (
        staleness["staleness_flag"] or not has_provenance
    ):
        quality_status = "FAILING"
    elif quality_warnings:
        quality_status = "DEGRADED"
    else:
        quality_status = "ACCEPTABLE"

    return {
        "quality_status": quality_status,
        "quality_warnings": quality_warnings,
        "dedupe_conflict_flag": False,
        "guard_enforced_capture": has_provenance,
        "deferred_item_caveats": ["rate_limit_policy_unconfirmed_WP8D002"],
    }


# ── Score-component helpers ───────────────────────────────────────────────────

def _build_score_components(
    record: MarketMetadataSnapshotRecord,
    ob_records: list,
    staleness: dict,
    missing_data: dict,
    quality_gates: dict,
    manifest_index: Optional[dict],
) -> dict:
    """Build score_components dict for WP49 scorer consumption."""

    # --- Positive components ---

    # data_completeness: fraction of key metadata fields present
    key_fields = ["market_id", "question", "category", "outcome_labels", "token_ids",
                  "resolution_date", "market_status"]
    present = sum(
        1 for f in key_fields
        if getattr(record, f, None) not in (None, "", [], {})
    )
    data_completeness = present / len(key_fields)

    # snapshot_freshness: inverse of staleness
    snapshot_freshness = 0.0 if staleness["staleness_flag"] else 1.0
    age = staleness.get("snapshot_age_seconds")
    threshold = staleness.get("freshness_threshold_seconds") or DEFAULT_METADATA_FRESHNESS_THRESHOLD_SECONDS
    if age is not None and not staleness["staleness_flag"] and threshold > 0:
        # Smooth decay: 1.0 at age=0, ~0 at threshold
        snapshot_freshness = max(0.0, 1.0 - (age / threshold))

    # quality_gate_status
    qs = quality_gates.get("quality_status", "UNKNOWN")
    qg_map = {"ACCEPTABLE": 1.0, "DEGRADED": 0.5, "FAILING": 0.1, "UNKNOWN": 0.0}
    quality_gate_status = qg_map.get(qs, 0.0)

    # market_activity_metadata: active=1.0, closed=0.5, unknown=0.0
    status = (record.market_status or "").lower()
    if status in ("active", "open"):
        market_activity_metadata = 1.0
    elif status in ("closed", "resolved", "finalized"):
        market_activity_metadata = 0.5
    else:
        market_activity_metadata = 0.0

    # category_coverage: 1.0 if category present and non-empty, 0.0 otherwise
    category_coverage = 0.0 if missing_data["missing_category"] else 1.0

    # token_outcome_completeness: based on token_ids and outcome_labels
    token_ids = record.token_ids or []
    outcome_labels = record.outcome_labels or []
    if len(token_ids) == 0:
        token_outcome_completeness = 0.0
    elif len(token_ids) != len(outcome_labels):
        # Mismatch — partially complete
        if len(outcome_labels) > 0:
            token_outcome_completeness = min(len(outcome_labels), len(token_ids)) / max(len(outcome_labels), len(token_ids)) * 0.5
        else:
            token_outcome_completeness = 0.1
    else:
        token_outcome_completeness = min(1.0, len(token_ids) / 2.0)

    # order_book_availability: 0 if no ob records, scale with count
    if len(ob_records) == 0:
        order_book_availability = 0.0
    else:
        order_book_availability = min(1.0, len(ob_records) / max(len(token_ids), 1))

    # spread_structure_observed: basic two-sided check
    has_two_sided = False
    for ob in ob_records:
        has_bids = bool(ob.bids)
        has_asks = bool(ob.asks)
        if has_bids and has_asks:
            has_two_sided = True
            break
    if len(ob_records) == 0:
        spread_structure_observed = 0.0
    elif has_two_sided:
        spread_structure_observed = 0.5  # conservative — not spread bps
    else:
        spread_structure_observed = 0.1  # one-sided only

    # visible_local_liquidity_proxy: capped at _MAX_LIQUIDITY_PROXY, conservative
    # Only counts non-empty sides; does not compute depth, bps, slippage, or fill probability
    if len(ob_records) == 0:
        visible_local_liquidity_proxy = 0.0
    else:
        total_sides = sum(
            (1 if ob.bids else 0) + (1 if ob.asks else 0)
            for ob in ob_records
        )
        # 2 sides per record = fully two-sided; normalize conservatively
        max_expected_sides = len(ob_records) * 2
        raw_proxy = total_sides / max_expected_sides if max_expected_sides > 0 else 0.0
        visible_local_liquidity_proxy = min(_MAX_LIQUIDITY_PROXY, raw_proxy * _MAX_LIQUIDITY_PROXY)

    # guard_provenance_quality: high if manifest present; 0 otherwise
    has_provenance = bool(
        manifest_index and manifest_index.get(record.snapshot_id) is not None
    )
    guard_provenance_quality = 0.8 if has_provenance else 0.0

    # --- Penalty components (all ≤ 0.0) ---

    # duplicate_conflict_penalty: 0.0 (dedup info not available in WP51 basic extraction)
    duplicate_conflict_penalty = 0.0

    # missing_data_penalty: -0.1 per missing critical field, capped at -0.5
    n_missing = len(missing_data.get("missing_metadata_fields") or [])
    missing_data_penalty = max(-0.5, -0.1 * n_missing)

    # deferred_item_caveat_penalty: small advisory penalty for known open deferred items
    deferred_item_caveat_penalty = -0.05

    return {
        "data_completeness": data_completeness,
        "snapshot_freshness": snapshot_freshness,
        "quality_gate_status": quality_gate_status,
        "market_activity_metadata": market_activity_metadata,
        "category_coverage": category_coverage,
        "token_outcome_completeness": token_outcome_completeness,
        "order_book_availability": order_book_availability,
        "spread_structure_observed": spread_structure_observed,
        "visible_local_liquidity_proxy": visible_local_liquidity_proxy,
        "guard_provenance_quality": guard_provenance_quality,
        "duplicate_conflict_penalty": duplicate_conflict_penalty,
        "missing_data_penalty": missing_data_penalty,
        "deferred_item_caveat_penalty": deferred_item_caveat_penalty,
    }


# ── Main extraction function ──────────────────────────────────────────────────

def extract_market_research_priority_context(
    record: MarketMetadataSnapshotRecord,
    manifests: Optional[Iterable[SnapshotManifest]] = None,
    order_books_by_token_id: Optional[dict] = None,
    generated_at_utc: Optional[datetime] = None,
    metadata_freshness_threshold_seconds: Optional[int] = None,
    orderbook_freshness_threshold_seconds: Optional[int] = None,
) -> dict:
    """Extract a market_context dict from a MarketMetadataSnapshotRecord.

    Compatible with build_market_research_priority_output() from WP49.
    Advisory-only. No network. No writes.

    Args:
        record: market metadata snapshot record to extract from.
        manifests: iterable of SnapshotManifest objects for provenance lookup.
        order_books_by_token_id: dict of token_id → list[OrderBookSnapshotRecord].
        generated_at_utc: reference time for staleness computation. Defaults to now.
        metadata_freshness_threshold_seconds: staleness threshold for metadata.
        orderbook_freshness_threshold_seconds: staleness threshold for order books.

    Returns:
        dict compatible with build_market_research_priority_output().
    """
    if generated_at_utc is None:
        generated_at_utc = datetime.now(timezone.utc)

    meta_threshold = (
        metadata_freshness_threshold_seconds
        if metadata_freshness_threshold_seconds is not None
        else DEFAULT_METADATA_FRESHNESS_THRESHOLD_SECONDS
    )
    ob_threshold = (
        orderbook_freshness_threshold_seconds
        if orderbook_freshness_threshold_seconds is not None
        else DEFAULT_ORDERBOOK_FRESHNESS_THRESHOLD_SECONDS
    )

    manifest_index: Optional[dict] = None
    if manifests is not None:
        manifest_index = build_manifest_index(manifests)

    # Collect order book records for this market's tokens
    token_ids = record.token_ids or []
    ob_records: list = []
    if order_books_by_token_id:
        for tid in token_ids:
            ob_records.extend(order_books_by_token_id.get(tid, []))

    staleness = _build_staleness(
        record, ob_records, generated_at_utc, meta_threshold, ob_threshold
    )
    provenance = _build_provenance(record, manifest_index)
    missing_data_warnings: list = []
    missing_data = _build_missing_data(record, ob_records, missing_data_warnings)
    quality_gates = _build_quality_gates(missing_data, staleness, manifest_index, record)
    score_components = _build_score_components(
        record, ob_records, staleness, missing_data, quality_gates, manifest_index
    )

    explanation_parts = []
    if staleness["staleness_flag"]:
        explanation_parts.append("stale snapshot")
    if missing_data["missing_category"]:
        explanation_parts.append("missing category")
    if missing_data["missing_order_book"]:
        explanation_parts.append("no order book")
    if not provenance["snapshot_manifest_ids"]:
        explanation_parts.append("no manifest provenance")
    if not explanation_parts:
        explanation_parts.append("basic metadata and provenance present")
    component_explanation = (
        f"WP51 feature extraction foundation. Advisory-only. "
        f"Notes: {'; '.join(explanation_parts)}."
    )

    return {
        "market_id": record.market_id,
        "question": record.question,
        "category": record.category,
        "active_status": record.market_status,
        "score_components": score_components,
        "staleness": staleness,
        "provenance": provenance,
        "missing_data": missing_data,
        "quality_gates": quality_gates,
        "component_explanation": component_explanation,
    }


def extract_market_research_priority_contexts(
    records: Iterable[MarketMetadataSnapshotRecord],
    manifests: Optional[Iterable[SnapshotManifest]] = None,
    order_books: Optional[Iterable[OrderBookSnapshotRecord]] = None,
    generated_at_utc: Optional[datetime] = None,
) -> list:
    """Extract market_context dicts for all records.

    Returns a list of dicts, each compatible with build_market_research_priority_output().
    Advisory-only. No network. No writes.
    """
    if generated_at_utc is None:
        generated_at_utc = datetime.now(timezone.utc)

    manifest_index: Optional[dict] = None
    if manifests is not None:
        manifest_index = build_manifest_index(manifests)

    order_books_by_token_id: Optional[dict] = None
    if order_books is not None:
        order_books_by_token_id = index_order_books_by_token_id(order_books)

    return [
        extract_market_research_priority_context(
            record=r,
            manifests=list(manifest_index.values()) if manifest_index else None,
            order_books_by_token_id=order_books_by_token_id,
            generated_at_utc=generated_at_utc,
        )
        for r in records
    ]


# ── Run context ───────────────────────────────────────────────────────────────

def build_market_research_priority_run_context(
    snapshot_id: str,
    manifests: Optional[Iterable[SnapshotManifest]] = None,
    source_artifacts: Optional[dict] = None,
    generated_at_utc: Optional[datetime] = None,
) -> dict:
    """Build a run_context dict for use with build_market_research_priority_output().

    Advisory-only. No network. No writes.
    """
    if generated_at_utc is None:
        generated_at_utc = datetime.now(timezone.utc)

    manifest_ids = []
    if manifests is not None:
        manifest_index = build_manifest_index(manifests)
        manifest_ids = list(manifest_index.keys())

    artifacts = source_artifacts or {}
    if snapshot_id and snapshot_id not in artifacts:
        artifacts = dict(artifacts)
        artifacts["snapshot_id"] = snapshot_id

    run_id = f"wp51-run-{uuid.uuid4().hex[:12]}"

    return {
        "generated_at_utc": generated_at_utc.isoformat(),
        "run_id": run_id,
        "source_artifacts": artifacts,
        "scope": {
            "package": FEATURE_EXTRACTION_SCOPE,
            "version": FEATURE_EXTRACTION_VERSION,
            "advisory_only": True,
            "network": "none",
            "trading": "none",
            "execution": "none",
            "local_offline_read_only": True,
            "manifest_ids": manifest_ids,
            "advisory_label": _ADVISORY_LABEL,
        },
    }


# ── Optional snapshot-dir extraction ─────────────────────────────────────────

def extract_from_snapshot_dir(
    input_dir: Path,
    generated_at_utc: Optional[datetime] = None,
) -> tuple:
    """Extract run_context and market_contexts from a local snapshot directory.

    Reads only from existing local snapshot files using snapshot_reader functions.
    No network. No writes. Returns (run_context, list[market_context]).

    Uses only existing snapshot_reader local/offline functions. Does not write
    files, call network, generate reports, or produce CLI output.
    """
    from src.data_layer.polymarket.snapshot_reader import (
        load_market_snapshot_records,
        load_order_book_snapshot_records,
        load_snapshot_manifests,
    )

    if generated_at_utc is None:
        generated_at_utc = datetime.now(timezone.utc)

    input_dir = Path(input_dir)

    manifests_result = load_snapshot_manifests(input_dir)
    manifests = list(manifests_result.records)

    markets_result = load_market_snapshot_records(input_dir)
    records = list(markets_result.records)

    obs_result = load_order_book_snapshot_records(input_dir)
    order_books = list(obs_result.records)

    # Use the first snapshot_id found, or a placeholder
    snap_id = records[0].snapshot_id if records else "unknown"

    run_context = build_market_research_priority_run_context(
        snapshot_id=snap_id,
        manifests=manifests,
        generated_at_utc=generated_at_utc,
    )

    market_contexts = extract_market_research_priority_contexts(
        records=records,
        manifests=manifests,
        order_books=order_books,
        generated_at_utc=generated_at_utc,
    )

    return run_context, market_contexts
