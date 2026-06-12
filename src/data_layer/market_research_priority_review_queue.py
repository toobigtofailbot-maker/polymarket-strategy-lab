"""Local/offline/read-only Market Research Priority review queue and report objects.

WP64 research queue ranking, local human review report, and research session packet.

This module:
- consumes prepared market_context dicts and/or scored market objects produced
  by the WP49/WP51–WP63 feature extraction and scoring pipeline;
- produces in-memory human research triage objects only;
- performs no network access;
- writes no files;
- adds no CLI;
- adds no export/report writer;
- adds no trading, execution, credentials, wallet, Hermes, LLM, scheduler,
  dashboard, database, polling, or product behavior.

Advisory-only. Not a trading signal. Not expected return. Not investment advice.
Not position sizing. Not an execution instruction. Human review required before
any use.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

_ADVISORY_LABEL = "ADVISORY_ONLY_HUMAN_REVIEW_REQUIRED"
_REPORT_TYPE = "LOCAL_HUMAN_REVIEW_REPORT_V1"
_FORBIDDEN_INTERPRETATION_NOTICE = (
    "This output is not a trading signal, not expected return, not position "
    "sizing, and not an execution instruction. It is for human research triage "
    "only. ADVISORY_ONLY_HUMAN_REVIEW_REQUIRED."
)

# Bucket labels — no trade/signal/opportunity wording allowed.
BUCKET_REVIEW_FIRST = "REVIEW_FIRST"
BUCKET_MANUAL_SOURCE_REVIEW_REQUIRED = "MANUAL_SOURCE_REVIEW_REQUIRED"
BUCKET_REVIEW_LATER = "REVIEW_LATER"
BUCKET_DATA_QUALITY_BLOCKED = "DATA_QUALITY_BLOCKED"
BUCKET_DEPRIORITIZED = "DEPRIORITIZED"

# Bucket sort order: lower index = higher priority in queue.
_BUCKET_ORDER: dict[str, int] = {
    BUCKET_REVIEW_FIRST: 0,
    BUCKET_MANUAL_SOURCE_REVIEW_REQUIRED: 1,
    BUCKET_REVIEW_LATER: 2,
    BUCKET_DATA_QUALITY_BLOCKED: 3,
    BUCKET_DEPRIORITIZED: 4,
}

# Threshold for distinguishing REVIEW_FIRST from REVIEW_LATER when score is available.
_REVIEW_FIRST_SCORE_THRESHOLD = 0.35


def _get_quality_status(ctx: dict) -> str:
    return (ctx.get("quality_gates") or {}).get("quality_status", "UNKNOWN")


def _is_stale(ctx: dict) -> bool:
    return bool((ctx.get("staleness") or {}).get("staleness_flag"))


def _requires_recapture(ctx: dict) -> bool:
    return bool((ctx.get("staleness") or {}).get("requires_recapture_before_use"))


def _has_missing_data_warning(ctx: dict) -> bool:
    return bool((ctx.get("missing_data") or {}).get("missing_data_warning"))


def _has_missing_critical_data(ctx: dict) -> bool:
    md = ctx.get("missing_data") or {}
    return bool(
        md.get("missing_question")
        or md.get("missing_market_status")
        or md.get("missing_order_book")
        or md.get("missing_outcome_tokens")
    )


def _has_absent_provenance(ctx: dict) -> bool:
    prov = ctx.get("provenance") or {}
    manifest_ids = prov.get("snapshot_manifest_ids") or []
    export_paths = prov.get("source_export_paths") or []
    return not manifest_ids and not export_paths


def _is_provenance_degraded(ctx: dict) -> bool:
    return bool((ctx.get("provenance") or {}).get("provenance_degraded"))


def _requires_resolution_manual_review(ctx: dict) -> bool:
    return bool((ctx.get("resolution_ambiguity") or {}).get("manual_review_required"))


def _requires_source_manual_review(ctx: dict) -> bool:
    return bool((ctx.get("resolution_source_hierarchy") or {}).get("manual_source_review_required"))


def _has_source_metadata_available(ctx: dict) -> bool:
    return bool((ctx.get("resolution_source_hierarchy") or {}).get("source_metadata_available"))


def _get_research_priority_score(ctx: dict) -> Optional[float]:
    """Return research_priority_score if present and numeric, else None."""
    val = ctx.get("research_priority_score")
    if val is None:
        return None
    try:
        f = float(val)
    except (TypeError, ValueError):
        return None
    if f != f:  # NaN check
        return None
    return max(0.0, min(1.0, f))


def _determine_bucket(ctx: dict) -> str:
    """Determine the research review queue bucket for a single market context.

    Conservative and explainable. No trade/signal/opportunity wording.
    """
    quality_status = _get_quality_status(ctx)
    stale = _is_stale(ctx)
    requires_recapture = _requires_recapture(ctx)
    has_missing_warning = _has_missing_data_warning(ctx)
    has_missing_critical = _has_missing_critical_data(ctx)
    absent_provenance = _has_absent_provenance(ctx)
    score = _get_research_priority_score(ctx)

    # DATA_QUALITY_BLOCKED: quality FAILING, stale requiring recapture,
    # critical missing data, or completely absent provenance.
    if (
        quality_status == "FAILING"
        or requires_recapture
        or has_missing_critical
        or absent_provenance
    ):
        return BUCKET_DATA_QUALITY_BLOCKED

    # MANUAL_SOURCE_REVIEW_REQUIRED: resolution ambiguity manual review needed,
    # source hierarchy missing, or explicit source manual review flag.
    if _requires_resolution_manual_review(ctx) or _requires_source_manual_review(ctx):
        return BUCKET_MANUAL_SOURCE_REVIEW_REQUIRED

    # DEPRIORITIZED: score unavailable or metadata insufficient.
    if score is None:
        return BUCKET_DEPRIORITIZED

    # REVIEW_FIRST: acceptable/degraded-but-usable data, score present, no blocking gate.
    # Only ACCEPTABLE or DEGRADED quality (not FAILING, handled above).
    if quality_status in ("ACCEPTABLE", "DEGRADED") and not stale:
        if score >= _REVIEW_FIRST_SCORE_THRESHOLD:
            return BUCKET_REVIEW_FIRST
        return BUCKET_REVIEW_LATER

    # REVIEW_LATER: lower score or warnings but not blocking.
    if score > 0.0 or has_missing_warning:
        return BUCKET_REVIEW_LATER

    return BUCKET_DEPRIORITIZED


def _get_review_reasons(ctx: dict) -> list[str]:
    """Return deterministic list of review reasons for a market context.

    No trade-like wording.
    """
    reasons: list[str] = []

    score = _get_research_priority_score(ctx)
    if score is not None:
        reasons.append("research_priority_score_available")

    reso = ctx.get("resolution_ambiguity") or {}
    if reso.get("label_available"):
        reasons.append("resolution_ambiguity_label_present")
    if reso.get("manual_review_required"):
        reasons.append("manual_source_review_required")

    src = ctx.get("resolution_source_hierarchy") or {}
    if src.get("manual_source_review_required"):
        if "manual_source_review_required" not in reasons:
            reasons.append("manual_source_review_required")

    micro = ctx.get("microstructure_quality") or {}
    if micro.get("order_book_available"):
        reasons.append("microstructure_metadata_available")

    cross = ctx.get("cross_market_relationships") or {}
    if cross.get("relationship_metadata_available") and cross.get("relationship_candidate_count", 0) > 0:
        reasons.append("cross_market_candidates_present")

    staleness = ctx.get("staleness") or {}
    if staleness.get("staleness_flag"):
        reasons.append("staleness_warning_present")

    md = ctx.get("missing_data") or {}
    if md.get("missing_data_warning"):
        reasons.append("missing_data_warning_present")

    return sorted(set(reasons))


def _get_caution_flags(ctx: dict) -> list[str]:
    """Return deterministic list of caution flags for a market context.

    No trade-like wording.
    """
    flags: list[str] = []

    staleness = ctx.get("staleness") or {}
    if staleness.get("requires_recapture_before_use"):
        flags.append("stale_input_requires_recapture")

    md = ctx.get("missing_data") or {}
    if md.get("missing_question"):
        flags.append("missing_question")
    if md.get("missing_market_status"):
        flags.append("missing_market_status")
    if md.get("missing_order_book"):
        flags.append("missing_order_book")

    prov = ctx.get("provenance") or {}
    if _has_absent_provenance(ctx):
        flags.append("weak_or_absent_provenance")
    elif prov.get("provenance_degraded"):
        flags.append("weak_or_absent_provenance")

    src = ctx.get("resolution_source_hierarchy") or {}
    if not src.get("source_metadata_available", True):
        flags.append("source_metadata_missing")
    if src.get("manual_source_review_required"):
        flags.append("resolution_ambiguity_manual_review_required")

    micro = ctx.get("microstructure_quality") or {}
    if micro.get("order_book_available"):
        two_sided = micro.get("two_sided_structure_observed")
        if not two_sided:
            flags.append("one_sided_or_empty_order_book")

    cross = ctx.get("cross_market_relationships") or {}
    if cross.get("relationship_metadata_available") and cross.get("relationship_candidate_count", 0) > 0:
        flags.append("cross_market_relationships_require_human_review")

    reso = ctx.get("resolution_ambiguity") or {}
    if reso.get("manual_review_required"):
        if "resolution_ambiguity_manual_review_required" not in flags:
            flags.append("resolution_ambiguity_manual_review_required")

    return sorted(set(flags))


def _build_data_quality_summary(ctx: dict) -> dict:
    staleness = ctx.get("staleness") or {}
    prov = ctx.get("provenance") or {}
    md = ctx.get("missing_data") or {}
    return {
        "quality_status": _get_quality_status(ctx),
        "staleness_flag": bool(staleness.get("staleness_flag")),
        "missing_data_warning": bool(md.get("missing_data_warning")),
        "provenance_degraded": bool(
            _has_absent_provenance(ctx) or prov.get("provenance_degraded")
        ),
    }


def _build_resolution_summary(ctx: dict) -> dict:
    reso = ctx.get("resolution_ambiguity") or {}
    return {
        "resolution_ambiguity_available": bool(reso.get("label_available")),
        "manual_review_required": bool(reso.get("manual_review_required")),
        "highest_ambiguity_severity": reso.get("highest_ambiguity_severity", "UNKNOWN"),
    }


def _build_microstructure_summary(ctx: dict) -> dict:
    micro = ctx.get("microstructure_quality") or {}
    return {
        "order_book_available": bool(micro.get("order_book_available")),
        "two_sided_structure_observed": bool(micro.get("two_sided_structure_observed")),
        "order_book_stale": bool(micro.get("order_book_stale")),
    }


def _build_cross_market_summary(ctx: dict) -> dict:
    cross = ctx.get("cross_market_relationships") or {}
    return {
        "relationship_metadata_available": bool(cross.get("relationship_metadata_available")),
        "relationship_candidate_count": int(cross.get("relationship_candidate_count", 0)),
        "metadata_only": True,
    }


def _build_source_hierarchy_summary(ctx: dict) -> dict:
    src = ctx.get("resolution_source_hierarchy") or {}
    return {
        "source_metadata_available": bool(src.get("source_metadata_available")),
        "manual_source_review_required": bool(src.get("manual_source_review_required")),
        "official_source_monitoring_performed": False,
    }


def _review_priority_label(bucket: str, score: Optional[float]) -> str:
    if bucket == BUCKET_REVIEW_FIRST:
        return "HIGH"
    if bucket == BUCKET_MANUAL_SOURCE_REVIEW_REQUIRED:
        return "HIGH"
    if bucket == BUCKET_REVIEW_LATER:
        return "MEDIUM"
    if bucket == BUCKET_DATA_QUALITY_BLOCKED:
        return "LOW"
    return "LOW"


def build_research_session_packet(
    ctx: dict,
    queue_rank: int,
    bucket: str,
) -> dict:
    """Build a compact research session packet for a single market context.

    Local/offline/read-only. In-memory object only. No network. No file writes.
    No CLI. No strategy. No execution. Advisory-only. Human review required.

    Args:
        ctx: market_context dict from extract_market_research_priority_context()
             or a scored market object from build_market_research_priority_output().
        queue_rank: 1-based rank in the research review queue.
        bucket: queue bucket label from _determine_bucket().

    Returns:
        dict — compact research session packet.
    """
    market_id = ctx.get("market_id", "")
    score = _get_research_priority_score(ctx)
    review_reasons = _get_review_reasons(ctx)
    caution_flags = _get_caution_flags(ctx)

    return {
        "market_id": market_id,
        "question": ctx.get("question", ""),
        "queue_rank": queue_rank,
        "research_queue_bucket": bucket,
        "research_review_priority": _review_priority_label(bucket, score),
        "research_priority_score": score,
        "human_review_required": True,
        "review_reasons": review_reasons,
        "blocking_or_caution_flags": caution_flags,
        "data_quality_summary": _build_data_quality_summary(ctx),
        "resolution_summary": _build_resolution_summary(ctx),
        "microstructure_summary": _build_microstructure_summary(ctx),
        "cross_market_summary": _build_cross_market_summary(ctx),
        "source_hierarchy_summary": _build_source_hierarchy_summary(ctx),
        "forbidden_interpretation_notice": _FORBIDDEN_INTERPRETATION_NOTICE,
        "advisory_label": _ADVISORY_LABEL,
    }


def build_research_review_queue(
    market_contexts: list[dict],
    generated_at_utc: Optional[datetime] = None,
) -> list[dict]:
    """Build a deterministic sorted research review queue from market contexts.

    Local/offline/read-only. In-memory only. No network. No file writes. No CLI.
    No strategy. No execution. Advisory-only. Human review required.

    Sort order:
        1. Bucket priority: REVIEW_FIRST, MANUAL_SOURCE_REVIEW_REQUIRED,
           REVIEW_LATER, DATA_QUALITY_BLOCKED, DEPRIORITIZED
        2. Higher research_priority_score first (None treated as -1.0)
        3. Stable tie-breaker: market_id ascending

    Args:
        market_contexts: list of market_context dicts or scored market objects.
        generated_at_utc: reference time for the queue. Defaults to now (UTC).

    Returns:
        list of research session packet dicts in queue order.
    """
    if generated_at_utc is None:
        generated_at_utc = datetime.now(timezone.utc)

    entries: list[tuple] = []
    for ctx in market_contexts:
        bucket = _determine_bucket(ctx)
        score = _get_research_priority_score(ctx)
        score_sort = score if score is not None else -1.0
        market_id = ctx.get("market_id", "") or ""
        entries.append((bucket, score_sort, market_id, ctx))

    entries.sort(
        key=lambda item: (
            _BUCKET_ORDER.get(item[0], 99),
            -item[1],        # higher score first
            item[2],         # market_id ascending as tie-break
        )
    )

    queue: list[dict] = []
    for rank, (bucket, _score_sort, _market_id, ctx) in enumerate(entries, start=1):
        packet = build_research_session_packet(ctx, queue_rank=rank, bucket=bucket)
        queue.append(packet)

    return queue


def build_local_human_review_report(
    market_contexts: list[dict],
    generated_at_utc: Optional[datetime] = None,
    report_label: str = "HUMAN_RESEARCH_TRIAGE",
) -> dict:
    """Build a local in-memory human review report from market contexts.

    Local/offline/read-only. In-memory object only. No network. No file writes.
    No CLI. No strategy. No execution. Advisory-only. Human review required.

    Args:
        market_contexts: list of market_context dicts or scored market objects.
        generated_at_utc: reference time for the report. Defaults to now (UTC).
        report_label: optional human-readable label for report scope.

    Returns:
        dict — LOCAL_HUMAN_REVIEW_REPORT_V1 shaped in-memory object.
    """
    if generated_at_utc is None:
        generated_at_utc = datetime.now(timezone.utc)

    review_queue = build_research_review_queue(market_contexts, generated_at_utc)

    queued: list[dict] = []
    excluded_or_deprioritized: list[dict] = []

    bucket_counts: dict[str, int] = {
        BUCKET_REVIEW_FIRST: 0,
        BUCKET_MANUAL_SOURCE_REVIEW_REQUIRED: 0,
        BUCKET_REVIEW_LATER: 0,
        BUCKET_DATA_QUALITY_BLOCKED: 0,
        BUCKET_DEPRIORITIZED: 0,
    }

    for packet in review_queue:
        bucket = packet["research_queue_bucket"]
        bucket_counts[bucket] = bucket_counts.get(bucket, 0) + 1
        if bucket in (BUCKET_DATA_QUALITY_BLOCKED, BUCKET_DEPRIORITIZED):
            excluded_or_deprioritized.append(packet)
        else:
            queued.append(packet)

    global_warnings: list[str] = []
    if bucket_counts[BUCKET_DATA_QUALITY_BLOCKED] > 0:
        global_warnings.append(
            f"{bucket_counts[BUCKET_DATA_QUALITY_BLOCKED]} market(s) are "
            "DATA_QUALITY_BLOCKED and require data recapture before human review."
        )
    if bucket_counts[BUCKET_DEPRIORITIZED] > 0:
        global_warnings.append(
            f"{bucket_counts[BUCKET_DEPRIORITIZED]} market(s) are DEPRIORITIZED "
            "due to insufficient metadata for meaningful human review."
        )

    queue_summary: dict = {
        "total_markets": len(market_contexts),
        "review_first_count": bucket_counts[BUCKET_REVIEW_FIRST],
        "review_later_count": bucket_counts[BUCKET_REVIEW_LATER],
        "manual_source_review_required_count": bucket_counts[BUCKET_MANUAL_SOURCE_REVIEW_REQUIRED],
        "data_quality_blocked_count": bucket_counts[BUCKET_DATA_QUALITY_BLOCKED],
        "deprioritized_count": bucket_counts[BUCKET_DEPRIORITIZED],
        "global_advisory_notice": _FORBIDDEN_INTERPRETATION_NOTICE,
    }

    return {
        "report_type": _REPORT_TYPE,
        "generated_at_utc": generated_at_utc.isoformat(),
        "advisory_label": _ADVISORY_LABEL,
        "report_scope": {
            "label": report_label,
            "package": "local/offline/read-only research-output packaging",
            "local_offline_read_only": True,
            "no_network": True,
            "no_file_writes": True,
            "no_cli_export": True,
            "no_strategy": True,
            "no_execution": True,
            "advisory_only": True,
        },
        "queue_summary": queue_summary,
        "review_queue": queued,
        "excluded_or_deprioritized": excluded_or_deprioritized,
        "global_warnings": global_warnings,
    }
