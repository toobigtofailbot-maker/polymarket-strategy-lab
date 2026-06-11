"""Local/offline/read-only Market Research Priority feature extraction foundation.

WP51 first feature-extraction foundation. WP53 provenance/staleness/missing-data
hardening. WP57 resolution ambiguity label feature extraction from validated manual
labels. WP61 microstructure quality metadata from local order-book snapshots.
WP62 cross-market relationship metadata from deterministic local key comparison.
WP63 resolution source hierarchy metadata from deterministic local field presence.
Advisory-only. Not a trading signal. Not expected return. Not investment advice.
Not position sizing. Not an execution instruction. Human review required before
any use.

This module:
- consumes existing local/offline snapshot artifacts and data-layer models only;
- consumes locally stored, manually authored, already schema-validatable resolution
  ambiguity labels using the WP56 validator (read-only, no parser, no inference);
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
import math
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional

from src.data_layer.polymarket.snapshot_models import (
    MarketMetadataSnapshotRecord,
    OrderBookSnapshotRecord,
    SnapshotManifest,
)
from src.data_layer.resolution_ambiguity_labels import (
    ADVISORY_LABEL as _RESOLUTION_ADVISORY_LABEL,
    load_resolution_ambiguity_label_records,
    validate_resolution_ambiguity_label,
)

FEATURE_EXTRACTION_SCOPE = "local/offline/read-only feature extraction foundation"
FEATURE_EXTRACTION_VERSION = "wp63-v1"

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


# ── Resolution ambiguity label helpers ───────────────────────────────────────

_SEVERITY_ORDER = {"NONE": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3, "UNKNOWN": 4}
_CONFIDENCE_ORDER = {"LOW": 0, "MEDIUM": 1, "HIGH": 2}

_DEFAULT_RESOLUTION_AMBIGUITY: dict = {
    "label_available": False,
    "validated_label_count": 0,
    "review_statuses": [],
    "ambiguity_categories": [],
    "highest_ambiguity_severity": "UNKNOWN",
    "lowest_reviewer_confidence": "LOW",
    "manual_review_required": True,
    "advisory_label": _RESOLUTION_ADVISORY_LABEL,
    "source_label_ids": [],
    "source_artifact_refs": [],
    "validation_error_count": 0,
    "validation_warning_count": 0,
}


def build_resolution_ambiguity_label_index(
    labels: Iterable[Mapping[str, Any]],
) -> dict:
    """Validate and index manual resolution ambiguity label records by market_id.

    Read-only. No writes. No parser. No inference from resolution text.
    Invalid labels are excluded; validation issue counts are recorded.

    Returns a dict with:
      "by_market_id": dict[market_id -> list of valid label dicts]
      "invalid_label_count": int
      "total_validation_error_count": int
      "total_validation_warning_count": int
    """
    by_market_id: dict[str, list] = {}
    invalid_label_count = 0
    total_error_count = 0
    total_warning_count = 0

    for label in labels:
        result = validate_resolution_ambiguity_label(label)
        total_error_count += len(result.errors)
        total_warning_count += len(result.warnings)
        if result.is_valid:
            market_id = label.get("market_id", "")
            if market_id:
                by_market_id.setdefault(market_id, []).append(dict(label))
        else:
            invalid_label_count += 1

    return {
        "by_market_id": by_market_id,
        "invalid_label_count": invalid_label_count,
        "total_validation_error_count": total_error_count,
        "total_validation_warning_count": total_warning_count,
    }


def _build_resolution_ambiguity_summary(
    market_id: str,
    label_index: Optional[dict],
) -> dict:
    """Build resolution_ambiguity sub-dict for a single market context.

    Read-only. No parser. No inference. No writes.
    Uses only valid labels from the pre-built label index.
    """
    if label_index is None:
        return dict(_DEFAULT_RESOLUTION_AMBIGUITY)

    valid_labels = label_index.get("by_market_id", {}).get(market_id, [])

    index_error_count = label_index.get("total_validation_error_count", 0)
    index_warning_count = label_index.get("total_validation_warning_count", 0)

    if not valid_labels:
        result = dict(_DEFAULT_RESOLUTION_AMBIGUITY)
        result["validation_error_count"] = index_error_count
        result["validation_warning_count"] = index_warning_count
        return result

    review_statuses: list[str] = []
    all_categories: list[str] = []
    seen_categories: set[str] = set()
    highest_severity = "NONE"
    lowest_confidence = "HIGH"
    any_manual_review_required = False
    source_label_ids: list[str] = []
    source_artifact_refs: list[str] = []
    seen_refs: set[str] = set()

    for lbl in valid_labels:
        rs = lbl.get("review_status", "")
        if rs and rs not in review_statuses:
            review_statuses.append(rs)

        cats = lbl.get("ambiguity_categories") or []
        for cat in cats:
            if cat not in seen_categories:
                all_categories.append(cat)
                seen_categories.add(cat)

        sev = lbl.get("ambiguity_severity", "UNKNOWN")
        if _SEVERITY_ORDER.get(sev, 4) > _SEVERITY_ORDER.get(highest_severity, 0):
            highest_severity = sev

        conf = lbl.get("reviewer_confidence", "LOW")
        if _CONFIDENCE_ORDER.get(conf, 0) < _CONFIDENCE_ORDER.get(lowest_confidence, 2):
            lowest_confidence = conf

        if lbl.get("manual_review_required") is True:
            any_manual_review_required = True

        label_id = lbl.get("label_id", "")
        if label_id and label_id not in source_label_ids:
            source_label_ids.append(label_id)

        for ref in lbl.get("source_artifact_refs") or []:
            if ref not in seen_refs:
                source_artifact_refs.append(ref)
                seen_refs.add(ref)

    return {
        "label_available": True,
        "validated_label_count": len(valid_labels),
        "review_statuses": review_statuses,
        "ambiguity_categories": all_categories,
        "highest_ambiguity_severity": highest_severity,
        "lowest_reviewer_confidence": lowest_confidence,
        "manual_review_required": any_manual_review_required,
        "advisory_label": _RESOLUTION_ADVISORY_LABEL,
        "source_label_ids": source_label_ids,
        "source_artifact_refs": source_artifact_refs,
        "validation_error_count": index_error_count,
        "validation_warning_count": index_warning_count,
    }


# ── Cross-market relationship helpers ────────────────────────────────────────

def _normalize_text(text: Optional[str]) -> str:
    """Deterministic normalization: lowercase, strip, collapse internal whitespace."""
    if not text:
        return ""
    return " ".join(text.lower().strip().split())


def _normalize_outcome_label_set(labels: Optional[list]) -> Optional[frozenset]:
    """Return a frozenset of normalized outcome labels, or None if empty."""
    if not labels:
        return None
    normalized = frozenset(_normalize_text(str(lbl)) for lbl in labels if lbl is not None)
    return normalized if normalized else None


def build_cross_market_relationship_index(
    records: Iterable[MarketMetadataSnapshotRecord],
) -> dict:
    """Build a deterministic in-memory cross-market relationship index.

    Indexes only deterministic, metadata-only keys:
    - normalized question text
    - condition_id (exact, non-empty)
    - token_id (each, non-empty)
    - normalized category + resolution_date
    - normalized outcome-label set

    No semantic matching. No fuzzy matching. No embeddings. No LLM. No external
    libraries. No price comparison. No microstructure comparison.

    Returns a dict with sub-dicts keyed by each relationship type, each mapping
    a key → sorted list of market_ids that share that key.
    """
    by_question: dict[str, list[str]] = {}
    by_condition_id: dict[str, list[str]] = {}
    by_token_id: dict[str, list[str]] = {}
    by_category_resolution: dict[tuple, list[str]] = {}
    by_outcome_label_set: dict[frozenset, list[str]] = {}

    for record in records:
        market_id = record.market_id
        if not market_id:
            continue

        norm_q = _normalize_text(record.question)
        if norm_q:
            by_question.setdefault(norm_q, []).append(market_id)

        cid = record.condition_id
        if cid and str(cid).strip():
            by_condition_id.setdefault(str(cid).strip(), []).append(market_id)

        for tid in (record.token_ids or []):
            if tid and str(tid).strip():
                by_token_id.setdefault(str(tid).strip(), []).append(market_id)

        norm_cat = _normalize_text(record.category)
        res_date = (record.resolution_date or "").strip()
        if norm_cat and res_date:
            key = (norm_cat, res_date)
            by_category_resolution.setdefault(key, []).append(market_id)

        label_set = _normalize_outcome_label_set(record.outcome_labels)
        if label_set is not None:
            by_outcome_label_set.setdefault(label_set, []).append(market_id)

    # Sort all lists for determinism
    for d in (by_question, by_condition_id, by_token_id):
        for k in d:
            d[k] = sorted(set(d[k]))
    for k in by_category_resolution:
        by_category_resolution[k] = sorted(set(by_category_resolution[k]))
    for k in by_outcome_label_set:
        by_outcome_label_set[k] = sorted(set(by_outcome_label_set[k]))

    return {
        "by_question": by_question,
        "by_condition_id": by_condition_id,
        "by_token_id": by_token_id,
        "by_category_resolution": by_category_resolution,
        "by_outcome_label_set": by_outcome_label_set,
    }


def _build_cross_market_relationships(
    record: MarketMetadataSnapshotRecord,
    cross_market_relationship_index: Optional[dict],
) -> dict:
    """Build cross_market_relationships sub-dict for a single market_context.

    Metadata-only. Deterministic. No semantic matching. No price comparison.
    No automated equivalence claim. Advisory-only. Human review required.

    When no index is supplied, returns safe unavailable defaults.
    """
    if cross_market_relationship_index is None:
        return {
            "relationship_metadata_available": False,
            "same_question_market_ids": [],
            "same_condition_id_market_ids": [],
            "shared_token_market_ids": [],
            "same_category_resolution_market_ids": [],
            "same_outcome_label_set_market_ids": [],
            "related_market_candidate_ids": [],
            "relationship_candidate_count": 0,
            "relationship_types_observed": [],
            "metadata_only": True,
            "semantic_matching_performed": False,
            "price_comparison_performed": False,
            "automated_equivalence_claim": False,
            "manual_review_required": True,
            "relationship_warnings": [
                "No local cross-market relationship index supplied; "
                "relationship metadata is unavailable."
            ],
            "advisory_label": _ADVISORY_LABEL,
        }

    market_id = record.market_id
    idx = cross_market_relationship_index
    warnings: list[str] = []

    # same normalized question
    norm_q = _normalize_text(record.question)
    same_question: list[str] = []
    if norm_q:
        same_question = sorted(
            mid for mid in idx.get("by_question", {}).get(norm_q, [])
            if mid != market_id
        )

    # same condition_id
    cid = record.condition_id
    same_condition: list[str] = []
    if cid and str(cid).strip():
        same_condition = sorted(
            mid for mid in idx.get("by_condition_id", {}).get(str(cid).strip(), [])
            if mid != market_id
        )

    # shared token_id
    shared_tokens_set: set[str] = set()
    for tid in (record.token_ids or []):
        if tid and str(tid).strip():
            for mid in idx.get("by_token_id", {}).get(str(tid).strip(), []):
                if mid != market_id:
                    shared_tokens_set.add(mid)
    shared_tokens = sorted(shared_tokens_set)

    # same category + resolution_date
    norm_cat = _normalize_text(record.category)
    res_date = (record.resolution_date or "").strip()
    same_cat_res: list[str] = []
    if norm_cat and res_date:
        key = (norm_cat, res_date)
        same_cat_res = sorted(
            mid for mid in idx.get("by_category_resolution", {}).get(key, [])
            if mid != market_id
        )
        if same_cat_res:
            warnings.append(
                "Same-category-and-resolution-date local relationship metadata candidates "
                "detected; weak candidate relationship only — human review required."
            )

    # same outcome-label set
    label_set = _normalize_outcome_label_set(record.outcome_labels)
    same_outcome_labels: list[str] = []
    if label_set is not None:
        same_outcome_labels = sorted(
            mid for mid in idx.get("by_outcome_label_set", {}).get(label_set, [])
            if mid != market_id
        )

    # union of all relationship lists → related_market_candidate_ids
    all_related: set[str] = set(same_question) | set(same_condition) | set(shared_tokens) | set(same_cat_res) | set(same_outcome_labels)
    related_market_candidate_ids = sorted(all_related)

    # relationship_types_observed
    relationship_types_observed: list[str] = []
    if same_question:
        relationship_types_observed.append("same_normalized_question")
    if same_condition:
        relationship_types_observed.append("same_condition_id")
    if shared_tokens:
        relationship_types_observed.append("shared_token_id")
    if same_cat_res:
        relationship_types_observed.append("same_category_and_resolution_date")
    if same_outcome_labels:
        relationship_types_observed.append("same_outcome_label_set")
    relationship_types_observed = sorted(relationship_types_observed)

    manual_review_required = bool(related_market_candidate_ids)

    return {
        "relationship_metadata_available": True,
        "same_question_market_ids": same_question,
        "same_condition_id_market_ids": same_condition,
        "shared_token_market_ids": shared_tokens,
        "same_category_resolution_market_ids": same_cat_res,
        "same_outcome_label_set_market_ids": same_outcome_labels,
        "related_market_candidate_ids": related_market_candidate_ids,
        "relationship_candidate_count": len(related_market_candidate_ids),
        "relationship_types_observed": relationship_types_observed,
        "metadata_only": True,
        "semantic_matching_performed": False,
        "price_comparison_performed": False,
        "automated_equivalence_claim": False,
        "manual_review_required": manual_review_required,
        "relationship_warnings": warnings,
        "advisory_label": _ADVISORY_LABEL,
    }


# ── Resolution source hierarchy helpers ──────────────────────────────────────

def _build_resolution_source_hierarchy(
    record: MarketMetadataSnapshotRecord,
) -> dict:
    """Build advisory-only local resolution-source hierarchy metadata.

    Deterministic field presence and simple substring checks only.
    No resolution-rule parsing. No source authority judgment.
    No official-source monitoring. No network. No writes.
    Advisory-only. Human review required.

    The current MarketMetadataSnapshotRecord model exposes resolution_date and
    question as the only locally available fields relevant to resolution-source
    metadata. All automated-authority, automated-interpretation, and
    official-source-monitoring flags are always False.
    """
    warnings: list[str] = []

    # Timing fields: resolution_date is the only local timing field in the model
    timing_fields: list[str] = []
    if record.resolution_date and str(record.resolution_date).strip():
        timing_fields.append("resolution_date")
    timing_fields = sorted(timing_fields)
    cutoff_timing_observed = bool(timing_fields)
    resolution_timing_observed = bool(timing_fields)

    question_text = record.question or ""

    # URL detection in question text (simple substring count — no fetch, no validation)
    http_count = question_text.count("http://")
    https_count = question_text.count("https://")
    source_url_count = http_count + https_count
    source_url_observed = source_url_count > 0

    # Source text fields: only when the question contains explicit source evidence (URL).
    # A plain market question (e.g. "Will X happen?") is not resolution-source metadata.
    source_text_fields: list[str] = []
    if source_url_observed:
        source_text_fields.append("question")
    source_text_fields = sorted(source_text_fields)

    # Primary source observed: True only when a URL pattern is found in local text
    primary_source_observed = source_url_observed

    # No dedicated official_source_reference, resolution_rules, or resolution_source
    # fields exist in the current MarketMetadataSnapshotRecord model
    official_source_reference_observed = False
    resolution_rules_text_observed = False

    # Source reference count: dedicated resolution-source reference fields (not timing)
    # No such fields exist in the current model
    source_reference_count = 0

    # source_metadata_available: True only when actual source/reference/URL metadata
    # is locally observed. Timing fields and plain question text alone are not sufficient.
    source_metadata_available = bool(
        source_url_observed
        or official_source_reference_observed
        or resolution_rules_text_observed
    )

    # manual_source_review_required: True when source hierarchy is incomplete
    manual_source_review_required = (
        not source_metadata_available
        or not cutoff_timing_observed
        or not primary_source_observed
        or not official_source_reference_observed
    )

    # Build warnings
    if not source_metadata_available:
        warnings.append(
            "No local resolution-source metadata observed; "
            "manual source review is required."
        )
    else:
        # source_metadata_available is True only when source_url_observed (or future
        # official_source_reference_observed / resolution_rules_text_observed).
        if source_url_observed and not cutoff_timing_observed:
            warnings.append(
                "Source URL pattern observed in local text field without local "
                "cutoff or resolution timing metadata."
            )
        if source_url_observed:
            warnings.append(
                "Source URL pattern observed in local text field; "
                "URL was not fetched, validated, or verified online; "
                "manual source review is required."
            )

    if not warnings:
        warnings.append(
            "No local resolution-source metadata observed; "
            "manual source review is required."
        )

    return {
        "source_metadata_available": source_metadata_available,
        "primary_source_observed": primary_source_observed,
        "official_source_reference_observed": official_source_reference_observed,
        "resolution_rules_text_observed": resolution_rules_text_observed,
        "cutoff_timing_observed": cutoff_timing_observed,
        "resolution_timing_observed": resolution_timing_observed,
        "source_url_observed": source_url_observed,
        "source_text_fields_observed": source_text_fields,
        "timing_fields_observed": timing_fields,
        "source_reference_count": source_reference_count,
        "source_url_count": source_url_count,
        "manual_source_review_required": manual_source_review_required,
        "automated_source_authority_judgment": False,
        "automated_resolution_interpretation": False,
        "official_source_monitoring_performed": False,
        "resolution_source_warnings": warnings,
        "advisory_label": _ADVISORY_LABEL,
    }


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
    """Return age in seconds between ts and reference, or None if ts is unparseable.

    Negative values indicate a future timestamp (clock drift or corrupted capture).
    """
    dt = _parse_utc(ts)
    if dt is None:
        return None
    delta = reference - dt
    return delta.total_seconds()


# ── Microstructure quality helpers ───────────────────────────────────────────

def _parse_level_price(level: Any) -> Optional[float]:
    if not isinstance(level, Mapping):
        return None
    try:
        value = float(level.get("price"))
    except (TypeError, ValueError):
        return None
    return value if math.isfinite(value) else None


def _parse_level_size(level: Any) -> Optional[float]:
    if not isinstance(level, Mapping):
        return None
    try:
        value = float(level.get("size"))
    except (TypeError, ValueError):
        return None
    return value if math.isfinite(value) else None


def _is_non_empty_level(level: Any) -> bool:
    price = _parse_level_price(level)
    size = _parse_level_size(level)
    return price is not None and size is not None and size > 0


def _select_latest_order_book_records(order_book_records: list) -> tuple[list, list]:
    """Select one latest local order-book record per token id.

    Timestamp ties keep the later input record for deterministic fallback behavior.
    Records with no parseable timestamp are used only when no parseable timestamp
    exists for that token id.
    """
    by_token: dict[str, list] = {}
    for position, ob in enumerate(order_book_records):
        by_token.setdefault(ob.token_id, []).append((position, ob))

    selected: list = []
    warnings: list[str] = []
    for token_id in sorted(by_token):
        candidates = by_token[token_id]
        parseable: list = []
        for position, ob in candidates:
            parsed = _parse_utc(ob.captured_at_utc)
            if parsed is not None:
                parseable.append((parsed, position, ob))

        if parseable:
            if len(parseable) < len(candidates):
                warnings.append(
                    f"One or more local order-book snapshot timestamps for token {token_id} "
                    "are unparseable; latest selection used parseable timestamps where available."
                )
            selected.append(max(parseable, key=lambda item: (item[0], item[1]))[2])
        else:
            warnings.append(
                f"Local order-book snapshot timestamps for token {token_id} are missing or "
                "unparseable; latest selection used deterministic input order."
            )
            selected.append(max(candidates, key=lambda item: item[0])[1])

    return selected, warnings


def _build_microstructure_quality(
    order_book_records: list,
    generated_at_utc: datetime,
    orderbook_threshold: int,
) -> dict:
    """Build advisory-only local order-book microstructure quality metadata.

    This summary uses only local OrderBookSnapshotRecord objects already supplied
    to feature extraction. It does not score market quality or interpret data as
    an action signal.
    """
    warnings: list[str] = []

    if not order_book_records:
        return {
            "order_book_available": False,
            "local_order_book_snapshot_count": 0,
            "best_bid_available": False,
            "best_ask_available": False,
            "two_sided_structure_observed": False,
            "one_sided_structure_observed": False,
            "empty_book_observed": True,
            "spread_structure_observed": False,
            "visible_bid_level_count": 0,
            "visible_ask_level_count": 0,
            "visible_total_level_count": 0,
            "non_empty_bid_level_count": 0,
            "non_empty_ask_level_count": 0,
            "latest_order_book_snapshot_id": None,
            "latest_order_book_captured_at_utc": None,
            "order_book_stale": True,
            "order_book_freshness_threshold_seconds": orderbook_threshold,
            "requires_order_book_recapture_before_use": True,
            "microstructure_warnings": [
                "No local order-book snapshot available; research data is incomplete."
            ],
            "advisory_label": _ADVISORY_LABEL,
        }

    latest_records, selection_warnings = _select_latest_order_book_records(order_book_records)
    warnings.extend(selection_warnings)

    latest_overall = None
    latest_parseable = None
    for position, ob in enumerate(order_book_records):
        parsed = _parse_utc(ob.captured_at_utc)
        if parsed is not None:
            if latest_parseable is None or (parsed, position) > latest_parseable[:2]:
                latest_parseable = (parsed, position, ob)

    if latest_parseable is not None:
        latest_overall = latest_parseable[2]
    else:
        latest_overall = order_book_records[-1]

    visible_bid_level_count = 0
    visible_ask_level_count = 0
    non_empty_bid_level_count = 0
    non_empty_ask_level_count = 0
    bid_prices: list[float] = []
    ask_prices: list[float] = []

    for ob in latest_records:
        bids = ob.bids if isinstance(ob.bids, list) else []
        asks = ob.asks if isinstance(ob.asks, list) else []
        visible_bid_level_count += len(bids)
        visible_ask_level_count += len(asks)

        for level in bids:
            if _is_non_empty_level(level):
                non_empty_bid_level_count += 1
                price = _parse_level_price(level)
                if price is not None:
                    bid_prices.append(price)

        for level in asks:
            if _is_non_empty_level(level):
                non_empty_ask_level_count += 1
                price = _parse_level_price(level)
                if price is not None:
                    ask_prices.append(price)

    best_bid_available = bool(bid_prices)
    best_ask_available = bool(ask_prices)
    two_sided_structure_observed = best_bid_available and best_ask_available
    one_sided_structure_observed = (
        (best_bid_available or best_ask_available) and not two_sided_structure_observed
    )
    empty_book_observed = not best_bid_available and not best_ask_available
    spread_structure_observed = False
    if two_sided_structure_observed:
        best_bid = max(bid_prices)
        best_ask = min(ask_prices)
        spread_structure_observed = best_bid <= best_ask
        if not spread_structure_observed:
            warnings.append(
                "Local order-book sides are observable, but best-side prices do not "
                "confirm basic bid/ask structure."
            )
    elif one_sided_structure_observed:
        warnings.append(
            "Only one local order-book side is observable; spread structure is not observable."
        )
    else:
        warnings.append("Local order-book snapshots contain no non-empty bid or ask levels.")

    order_book_stale = False
    for ob in latest_records:
        latest_age = _age_seconds(ob.captured_at_utc, generated_at_utc)
        if latest_age is None:
            order_book_stale = True
            warnings.append(
                f"Latest local order-book timestamp for token {ob.token_id} is missing "
                "or unparseable; recapture is needed before relying on the data for research."
            )
        elif latest_age < 0:
            order_book_stale = True
            warnings.append(
                f"Latest local order-book timestamp for token {ob.token_id} is in the "
                f"future by {abs(latest_age):.0f}s; treating the data as degraded for research."
            )
        elif latest_age > orderbook_threshold:
            order_book_stale = True
            warnings.append(
                f"Latest local order-book snapshot for token {ob.token_id} is {latest_age:.0f}s old "
                f"(threshold {orderbook_threshold}s); recapture is needed before relying "
                "on the data for research."
            )

    return {
        "order_book_available": True,
        "local_order_book_snapshot_count": len(order_book_records),
        "best_bid_available": best_bid_available,
        "best_ask_available": best_ask_available,
        "two_sided_structure_observed": two_sided_structure_observed,
        "one_sided_structure_observed": one_sided_structure_observed,
        "empty_book_observed": empty_book_observed,
        "spread_structure_observed": spread_structure_observed,
        "visible_bid_level_count": visible_bid_level_count,
        "visible_ask_level_count": visible_ask_level_count,
        "visible_total_level_count": visible_bid_level_count + visible_ask_level_count,
        "non_empty_bid_level_count": non_empty_bid_level_count,
        "non_empty_ask_level_count": non_empty_ask_level_count,
        "latest_order_book_snapshot_id": latest_overall.snapshot_id,
        "latest_order_book_captured_at_utc": latest_overall.captured_at_utc,
        "order_book_stale": order_book_stale,
        "order_book_freshness_threshold_seconds": orderbook_threshold,
        "requires_order_book_recapture_before_use": order_book_stale,
        "microstructure_warnings": warnings,
        "advisory_label": _ADVISORY_LABEL,
    }


def _build_staleness(
    record: MarketMetadataSnapshotRecord,
    order_book_records: list,
    generated_at_utc: datetime,
    metadata_threshold: int,
    orderbook_threshold: int,
) -> dict:
    """Build the staleness sub-dict for a market_context.

    WP53 hardening: future timestamps (negative age) are treated as stale, not fresh.
    Missing timestamps are treated as stale. Mixed fresh/stale order books are caught.
    """
    stale_inputs = []
    staleness_warnings = []
    requires_recapture = False
    future_timestamp_detected = False

    meta_age = _age_seconds(record.captured_at_utc, generated_at_utc)
    if meta_age is None:
        stale_inputs.append("metadata_snapshot (unparseable or missing timestamp)")
        staleness_warnings.append(
            "Metadata snapshot timestamp is unparseable or missing; treating as stale."
        )
        requires_recapture = True
        staleness_flag = True
    elif meta_age < 0:
        # Future timestamp: clock drift, corrupted capture, or data error.
        # Do not silently treat as fresh — mark stale and require recapture.
        future_timestamp_detected = True
        stale_inputs.append(
            f"metadata_snapshot (future timestamp, age={meta_age:.0f}s; "
            f"ahead by {abs(meta_age):.0f}s)"
        )
        staleness_warnings.append(
            f"Metadata snapshot timestamp is in the future by {abs(meta_age):.0f}s; "
            "possible clock drift or corrupted capture. Treating as stale; "
            "recapture required."
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
            stale_inputs.append(f"order_book_snapshot (token={ob.token_id}, unparseable timestamp)")
            staleness_warnings.append(
                f"Order book snapshot for token {ob.token_id} has unparseable or missing timestamp."
            )
            requires_recapture = True
            staleness_flag = True
        elif age < 0:
            # Future timestamp on order book — same treatment as metadata future timestamp.
            future_timestamp_detected = True
            stale_inputs.append(
                f"order_book_snapshot (token={ob.token_id}, future timestamp, age={age:.0f}s; "
                f"ahead by {abs(age):.0f}s)"
            )
            staleness_warnings.append(
                f"Order book snapshot for token {ob.token_id} has future timestamp "
                f"by {abs(age):.0f}s; treating as stale."
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
        "future_timestamp_detected": future_timestamp_detected,
    }


# ── Provenance helpers ────────────────────────────────────────────────────────

def _build_provenance(
    record: MarketMetadataSnapshotRecord,
    manifest_index: Optional[dict],
) -> dict:
    """Build the provenance sub-dict for a market_context.

    WP53 hardening: weak provenance is made explicit with provenance_degraded flag,
    provenance_weakness_reasons list, and provenance_warning string.

    Real provenance weaknesses (affect quality status):
      - no manifest index provided
      - snapshot_id not found in manifest index
      - manifest has no output files

    Informational model limitations (always absent in current manifest model;
    recorded but do not set provenance_degraded alone):
      - guard_policy_version absent (not stored in SnapshotManifest model)
      - empty_quality_report_ids (no quality-report workflow implemented yet)

    Missing provenance is never silently treated as valid.
    """
    snapshot_manifest_ids = []
    source_export_paths = []
    capture_session_ids = []
    guard_policy_version = None
    quality_report_ids = []
    input_artifact_types = ["market_metadata_snapshot"]

    # Real weaknesses that degrade quality
    quality_weakness_reasons: list = []
    # Informational model limitations — recorded but not quality-impacting alone
    informational_reasons: list = []

    if manifest_index is None:
        quality_weakness_reasons.append("no_manifest_index_provided")
    else:
        manifest = manifest_index.get(record.snapshot_id)
        if manifest is not None:
            snapshot_manifest_ids.append(manifest.snapshot_id)
            capture_session_ids.append(manifest.snapshot_id)
            output_files = manifest.output_files or []
            source_export_paths.extend(output_files)
            if not output_files:
                quality_weakness_reasons.append("manifest_has_no_output_files")
            # Guard policy not stored in manifest model; omit to avoid inventing values.
        else:
            quality_weakness_reasons.append("snapshot_id_not_found_in_manifest_index")

    # Derive secondary absence reasons only when no manifest was found
    if not snapshot_manifest_ids:
        quality_weakness_reasons.append("empty_snapshot_manifest_ids")
    if not capture_session_ids:
        quality_weakness_reasons.append("empty_capture_session_ids")

    # Source export paths are absent when either no manifest or manifest had no output_files
    if not source_export_paths and not snapshot_manifest_ids:
        quality_weakness_reasons.append("empty_source_export_paths")

    # Informational: these are always absent in the current manifest model
    if guard_policy_version is None:
        informational_reasons.append("guard_policy_version_absent")
    if not quality_report_ids:
        informational_reasons.append("empty_quality_report_ids")

    # provenance_degraded reflects real quality weaknesses only
    provenance_degraded = len(quality_weakness_reasons) > 0
    all_weakness_reasons = quality_weakness_reasons + informational_reasons
    provenance_warning: Optional[str] = (
        "Weak provenance: " + "; ".join(quality_weakness_reasons) + "."
        if quality_weakness_reasons else None
    )

    return {
        "snapshot_manifest_ids": snapshot_manifest_ids,
        "source_export_paths": source_export_paths,
        "capture_session_ids": capture_session_ids,
        "guard_policy_version": guard_policy_version,
        "quality_report_ids": quality_report_ids,
        "input_artifact_types": input_artifact_types,
        "provenance_degraded": provenance_degraded,
        "provenance_weakness_reasons": all_weakness_reasons,
        "provenance_warning": provenance_warning,
    }


# ── Missing-data helpers ──────────────────────────────────────────────────────

def _build_missing_data(
    record: MarketMetadataSnapshotRecord,
    ob_records: list,
    warnings: list,
) -> dict:
    """Build the missing_data sub-dict for a market_context.

    WP53 hardening: adds detection for missing question text and missing
    market_status. Multiple critical missing fields produce explicit non-compensatory
    degradation — good values elsewhere cannot erase critical missing-data warnings.
    """
    missing_fields = []
    has_warning = False

    missing_question = not bool(record.question)
    if missing_question:
        missing_fields.append("question")
        warnings.append("question field is absent")
        has_warning = True

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

    missing_market_status = not bool(record.market_status)
    if missing_market_status:
        missing_fields.append("market_status")
        warnings.append("market_status field is absent")
        has_warning = True

    reason = "; ".join(warnings) if warnings else None

    return {
        "missing_data_warning": has_warning,
        "missing_metadata_fields": missing_fields,
        "missing_order_book": missing_order_book,
        "missing_outcome_tokens": missing_outcome_tokens,
        "missing_category": missing_category,
        "missing_resolution_source": missing_resolution_source,
        "missing_question": missing_question,
        "missing_market_status": missing_market_status,
        "insufficient_coverage_reason": reason,
    }


# ── Quality gates helpers ─────────────────────────────────────────────────────

def _build_quality_gates(
    missing_data: dict,
    staleness: dict,
    manifest_index: Optional[dict],
    record: MarketMetadataSnapshotRecord,
    provenance: Optional[dict] = None,
    resolution_ambiguity: Optional[dict] = None,
) -> dict:
    """Build quality_gates sub-dict from extracted feature state.

    WP53 hardening: provenance_degraded (weak but present manifest) is distinguished
    from absent provenance and produces a weak_provenance warning. FAILING is still
    reserved for stale or absent provenance. Weak-but-present provenance results in
    DEGRADED status.
    """
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
    elif (provenance or {}).get("provenance_degraded"):
        # Manifest present but provenance fields are weak — warn but don't fail
        quality_warnings.append("weak_provenance")

    if not quality_warnings:
        quality_status = "ACCEPTABLE"
    elif staleness["staleness_flag"] or not has_provenance:
        # Stale data or completely absent provenance → FAILING
        quality_status = "FAILING"
    else:
        # Fresh data, provenance present (possibly weak) but with other warnings → DEGRADED
        quality_status = "DEGRADED"

    deferred_caveats = ["rate_limit_policy_unconfirmed_WP8D002"]
    if resolution_ambiguity is not None:
        deferred_caveats.append("resolution_ambiguity_label_review_required")

    return {
        "quality_status": quality_status,
        "quality_warnings": quality_warnings,
        "dedupe_conflict_flag": False,
        "guard_enforced_capture": has_provenance,
        "deferred_item_caveats": deferred_caveats,
    }


# ── Score-component helpers ───────────────────────────────────────────────────

def _build_score_components(
    record: MarketMetadataSnapshotRecord,
    ob_records: list,
    staleness: dict,
    missing_data: dict,
    quality_gates: dict,
    manifest_index: Optional[dict],
    provenance: Optional[dict] = None,
) -> dict:
    """Build score_components dict for WP49 scorer consumption.

    WP53 hardening: guard_provenance_quality is reduced for weak-but-present provenance
    (not just absent provenance). missing_data_penalty is non-zero whenever
    missing_data_warning is True.
    """

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
    if age is not None and age >= 0 and not staleness["staleness_flag"] and threshold > 0:
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

    # guard_provenance_quality: reflects manifest presence and provenance strength.
    # WP53: absent manifest → 0.0; present but weakly provenanced → 0.3; full → 0.8.
    has_provenance = bool(
        manifest_index and manifest_index.get(record.snapshot_id) is not None
    )
    provenance_degraded = (provenance or {}).get("provenance_degraded", False)
    if not has_provenance:
        guard_provenance_quality = 0.0
    elif provenance_degraded:
        guard_provenance_quality = 0.3
    else:
        guard_provenance_quality = 0.8

    # --- Penalty components (all ≤ 0.0) ---

    # duplicate_conflict_penalty: 0.0 (dedup info not available in WP51 basic extraction)
    duplicate_conflict_penalty = 0.0

    # missing_data_penalty: -0.1 per missing critical field, capped at -0.5.
    # Non-zero whenever missing_data_warning is True (non-compensatory).
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
    resolution_ambiguity_label_index: Optional[dict] = None,
    cross_market_relationship_index: Optional[dict] = None,
) -> dict:
    """Extract a market_context dict from a MarketMetadataSnapshotRecord.

    Compatible with build_market_research_priority_output() from WP49.
    Advisory-only. No network. No writes.

    WP53 hardening: provenance_degraded, future_timestamp_detected, missing_question,
    and missing_market_status are now propagated through staleness, provenance, and
    missing_data sub-dicts. Critical missing data cannot be silently erased by good
    values elsewhere.

    WP62: cross_market_relationship_index adds deterministic local relationship
    metadata. When None, relationship_metadata_available is False.

    WP63: resolution_source_hierarchy is always present. Derived from deterministic
    local field presence checks on the supplied record. No parser. No network.

    Args:
        record: market metadata snapshot record to extract from.
        manifests: iterable of SnapshotManifest objects for provenance lookup.
        order_books_by_token_id: dict of token_id → list[OrderBookSnapshotRecord].
        generated_at_utc: reference time for staleness computation. Defaults to now.
        metadata_freshness_threshold_seconds: staleness threshold for metadata.
        orderbook_freshness_threshold_seconds: staleness threshold for order books.
        cross_market_relationship_index: optional pre-built relationship index from
            build_cross_market_relationship_index(). When None, relationship metadata
            is unavailable. Metadata-only — no price, no microstructure comparison.

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
    microstructure_quality = _build_microstructure_quality(
        ob_records, generated_at_utc, ob_threshold
    )
    resolution_ambiguity = _build_resolution_ambiguity_summary(
        record.market_id, resolution_ambiguity_label_index
    )
    cross_market_relationships = _build_cross_market_relationships(
        record, cross_market_relationship_index
    )
    resolution_source_hierarchy = _build_resolution_source_hierarchy(record)
    # Pass resolution_ambiguity to quality_gates only when a label index was explicitly
    # provided; otherwise omit it so the deferred-item caveat is not added superfluously.
    quality_gates = _build_quality_gates(
        missing_data, staleness, manifest_index, record, provenance,
        resolution_ambiguity if resolution_ambiguity_label_index is not None else None,
    )
    score_components = _build_score_components(
        record, ob_records, staleness, missing_data, quality_gates, manifest_index, provenance
    )

    explanation_parts = []
    if staleness["staleness_flag"]:
        explanation_parts.append("stale snapshot")
    if staleness.get("future_timestamp_detected"):
        explanation_parts.append("future timestamp detected")
    if missing_data["missing_question"]:
        explanation_parts.append("missing question")
    if missing_data["missing_category"]:
        explanation_parts.append("missing category")
    if missing_data["missing_market_status"]:
        explanation_parts.append("missing market_status")
    if missing_data["missing_order_book"]:
        explanation_parts.append("no order book")
    if provenance["provenance_degraded"]:
        explanation_parts.append("weak or absent provenance")
    if microstructure_quality["order_book_stale"]:
        explanation_parts.append("order-book recapture needed for research")
    if not explanation_parts:
        explanation_parts.append("basic metadata and provenance present")
    component_explanation = (
        f"WP63 feature extraction (hardened + resolution ambiguity labels + "
        f"microstructure metadata + cross-market relationship metadata + "
        f"resolution source hierarchy metadata). Advisory-only. "
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
        "resolution_ambiguity": resolution_ambiguity,
        "microstructure_quality": microstructure_quality,
        "cross_market_relationships": cross_market_relationships,
        "resolution_source_hierarchy": resolution_source_hierarchy,
    }


def extract_market_research_priority_contexts(
    records: Iterable[MarketMetadataSnapshotRecord],
    manifests: Optional[Iterable[SnapshotManifest]] = None,
    order_books: Optional[Iterable[OrderBookSnapshotRecord]] = None,
    generated_at_utc: Optional[datetime] = None,
    resolution_ambiguity_labels: Optional[Iterable[Mapping[str, Any]]] = None,
) -> list:
    """Extract market_context dicts for all records.

    Returns a list of dicts, each compatible with build_market_research_priority_output().
    Advisory-only. No network. No writes.

    WP62: Builds a deterministic cross-market relationship index over all supplied
    records and attaches relationship metadata to each context. The current market
    is excluded from its own related candidate lists. Metadata-only.

    Args:
        resolution_ambiguity_labels: optional iterable of manually authored local
            label records. Each is validated using the WP56 validator; invalid labels
            are excluded. No parser. No inference from resolution text.
    """
    if generated_at_utc is None:
        generated_at_utc = datetime.now(timezone.utc)

    manifest_index: Optional[dict] = None
    if manifests is not None:
        manifest_index = build_manifest_index(manifests)

    order_books_by_token_id: Optional[dict] = None
    if order_books is not None:
        order_books_by_token_id = index_order_books_by_token_id(order_books)

    label_index: Optional[dict] = None
    if resolution_ambiguity_labels is not None:
        label_index = build_resolution_ambiguity_label_index(resolution_ambiguity_labels)

    # Materialize records once so they can be iterated twice (index + extraction)
    records_list = list(records)
    relationship_index = build_cross_market_relationship_index(records_list)

    return [
        extract_market_research_priority_context(
            record=r,
            manifests=list(manifest_index.values()) if manifest_index else None,
            order_books_by_token_id=order_books_by_token_id,
            generated_at_utc=generated_at_utc,
            resolution_ambiguity_label_index=label_index,
            cross_market_relationship_index=relationship_index,
        )
        for r in records_list
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

    run_id = f"wp63-run-{uuid.uuid4().hex[:12]}"

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
    resolution_ambiguity_label_path: Optional[Path] = None,
) -> tuple:
    """Extract run_context and market_contexts from a local snapshot directory.

    Reads only from existing local snapshot files using snapshot_reader functions.
    No network. No writes. Returns (run_context, list[market_context]).

    Uses only existing snapshot_reader local/offline functions. Does not write
    files, call network, generate reports, or produce CLI output.

    Args:
        resolution_ambiguity_label_path: optional explicit path to a local JSON or
            JSONL file of manually authored resolution ambiguity label records. If
            provided, labels are loaded using the WP56 reader, validated using the
            WP56 validator, and attached to matching market contexts. No directory
            auto-scan. No parser. No inference.
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

    resolution_ambiguity_labels = None
    if resolution_ambiguity_label_path is not None:
        resolution_ambiguity_labels = load_resolution_ambiguity_label_records(
            Path(resolution_ambiguity_label_path)
        )

    market_contexts = extract_market_research_priority_contexts(
        records=records,
        manifests=manifests,
        order_books=order_books,
        generated_at_utc=generated_at_utc,
        resolution_ambiguity_labels=resolution_ambiguity_labels,
    )

    return run_context, market_contexts
