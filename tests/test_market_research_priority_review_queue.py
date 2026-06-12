"""Focused tests for WP64 Market Research Priority Review Queue and Report.

Tests src/data_layer/market_research_priority_review_queue.py.
All tests are local/offline/in-memory. No network. No file I/O.
"""

from __future__ import annotations

import importlib
import importlib.util
from datetime import datetime, timezone

import pytest

from src.data_layer.market_research_priority_review_queue import (
    BUCKET_DATA_QUALITY_BLOCKED,
    BUCKET_DEPRIORITIZED,
    BUCKET_MANUAL_SOURCE_REVIEW_REQUIRED,
    BUCKET_REVIEW_FIRST,
    BUCKET_REVIEW_LATER,
    build_local_human_review_report,
    build_research_review_queue,
    build_research_session_packet,
)

_REF_UTC = datetime(2026, 1, 1, 13, 0, 0, tzinfo=timezone.utc)

# ── Minimal market context factories ─────────────────────────────────────────

def _make_acceptable_ctx(
    market_id: str = "mkt-001",
    question: str = "Will X happen?",
    score: float = 0.6,
    staleness_flag: bool = False,
    missing_data_warning: bool = False,
    quality_status: str = "ACCEPTABLE",
    has_resolution_ambiguity: bool = False,
    manual_source_review: bool = False,
    source_metadata_available: bool = True,
    order_book_available: bool = True,
    two_sided: bool = True,
    relationship_candidate_count: int = 0,
    requires_recapture: bool = False,
    missing_question: bool = False,
    missing_market_status: bool = False,
    missing_order_book: bool = False,
    absent_provenance: bool = False,
    provenance_degraded: bool = False,
) -> dict:
    prov: dict = {}
    if absent_provenance:
        prov = {"snapshot_manifest_ids": [], "source_export_paths": [], "provenance_degraded": True}
    elif provenance_degraded:
        prov = {"snapshot_manifest_ids": ["snap-1"], "source_export_paths": [], "provenance_degraded": True}
    else:
        prov = {"snapshot_manifest_ids": ["snap-1"], "source_export_paths": ["out.jsonl"], "provenance_degraded": False}

    return {
        "market_id": market_id,
        "question": question,
        "research_priority_score": score,
        "staleness": {
            "staleness_flag": staleness_flag,
            "requires_recapture_before_use": requires_recapture,
        },
        "missing_data": {
            "missing_data_warning": missing_data_warning,
            "missing_question": missing_question,
            "missing_market_status": missing_market_status,
            "missing_order_book": missing_order_book,
            "missing_outcome_tokens": False,
        },
        "quality_gates": {
            "quality_status": quality_status,
        },
        "provenance": prov,
        "resolution_ambiguity": {
            "label_available": has_resolution_ambiguity,
            "manual_review_required": has_resolution_ambiguity,
            "highest_ambiguity_severity": "LOW" if has_resolution_ambiguity else "NONE",
        },
        "resolution_source_hierarchy": {
            "source_metadata_available": source_metadata_available,
            "manual_source_review_required": manual_source_review,
        },
        "microstructure_quality": {
            "order_book_available": order_book_available,
            "two_sided_structure_observed": two_sided,
            "order_book_stale": staleness_flag,
        },
        "cross_market_relationships": {
            "relationship_metadata_available": True,
            "relationship_candidate_count": relationship_candidate_count,
        },
        "score_components": {},
    }


def _make_blocked_ctx(market_id: str = "mkt-blocked") -> dict:
    return _make_acceptable_ctx(
        market_id=market_id,
        quality_status="FAILING",
        requires_recapture=True,
        missing_order_book=True,
    )


def _make_deprioritized_ctx(market_id: str = "mkt-dep") -> dict:
    ctx = _make_acceptable_ctx(market_id=market_id, score=0.0)
    ctx["research_priority_score"] = None
    return ctx


# ── Module-level safety tests ─────────────────────────────────────────────────

class TestModuleSafety:
    def test_module_imports_no_network_packages(self):
        spec = importlib.util.spec_from_file_location(
            "market_research_priority_review_queue",
            "src/data_layer/market_research_priority_review_queue.py",
        )
        assert spec is not None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        source = open("src/data_layer/market_research_priority_review_queue.py").read()
        for forbidden in ("import requests", "import urllib.request", "import httpx",
                          "import aiohttp", "import socket", "import http.client"):
            assert forbidden not in source, f"Network import found: {forbidden}"

    def test_functions_return_in_memory_objects(self):
        ctx = _make_acceptable_ctx()
        queue = build_research_review_queue([ctx], _REF_UTC)
        assert isinstance(queue, list)
        report = build_local_human_review_report([ctx], _REF_UTC)
        assert isinstance(report, dict)
        packet = build_research_session_packet(ctx, queue_rank=1, bucket=BUCKET_REVIEW_FIRST)
        assert isinstance(packet, dict)

    def test_functions_return_no_file_paths(self):
        ctx = _make_acceptable_ctx()
        report = build_local_human_review_report([ctx], _REF_UTC)
        # report_scope flags must all be True for safety constraints
        scope = report["report_scope"]
        assert scope["no_network"] is True
        assert scope["no_file_writes"] is True
        assert scope["no_cli_export"] is True
        assert scope["no_strategy"] is True
        assert scope["no_execution"] is True
        assert scope["local_offline_read_only"] is True
        assert scope["advisory_only"] is True


# ── Queue bucket tests ────────────────────────────────────────────────────────

class TestQueueBuckets:
    def test_review_first_for_acceptable_high_score(self):
        ctx = _make_acceptable_ctx(score=0.7, quality_status="ACCEPTABLE")
        queue = build_research_review_queue([ctx], _REF_UTC)
        assert queue[0]["research_queue_bucket"] == BUCKET_REVIEW_FIRST

    def test_review_first_for_degraded_high_score(self):
        ctx = _make_acceptable_ctx(score=0.5, quality_status="DEGRADED",
                                   staleness_flag=False, requires_recapture=False,
                                   provenance_degraded=True)
        queue = build_research_review_queue([ctx], _REF_UTC)
        assert queue[0]["research_queue_bucket"] == BUCKET_REVIEW_FIRST

    def test_review_first_only_for_non_blocked_candidates(self):
        good = _make_acceptable_ctx("mkt-good", score=0.7)
        blocked = _make_blocked_ctx("mkt-bad")
        queue = build_research_review_queue([blocked, good], _REF_UTC)
        first_buckets = [q["research_queue_bucket"] for q in queue]
        assert BUCKET_REVIEW_FIRST in first_buckets
        # REVIEW_FIRST must not appear for the blocked market
        good_packet = next(q for q in queue if q["market_id"] == "mkt-good")
        bad_packet = next(q for q in queue if q["market_id"] == "mkt-bad")
        assert good_packet["research_queue_bucket"] == BUCKET_REVIEW_FIRST
        assert bad_packet["research_queue_bucket"] != BUCKET_REVIEW_FIRST

    def test_data_quality_blocked_for_failing_quality(self):
        ctx = _make_acceptable_ctx(quality_status="FAILING")
        queue = build_research_review_queue([ctx], _REF_UTC)
        assert queue[0]["research_queue_bucket"] == BUCKET_DATA_QUALITY_BLOCKED

    def test_data_quality_blocked_for_stale_recapture(self):
        ctx = _make_acceptable_ctx(requires_recapture=True)
        queue = build_research_review_queue([ctx], _REF_UTC)
        assert queue[0]["research_queue_bucket"] == BUCKET_DATA_QUALITY_BLOCKED

    def test_data_quality_blocked_for_missing_critical_data(self):
        ctx = _make_acceptable_ctx(missing_question=True, missing_data_warning=True)
        queue = build_research_review_queue([ctx], _REF_UTC)
        assert queue[0]["research_queue_bucket"] == BUCKET_DATA_QUALITY_BLOCKED

    def test_data_quality_blocked_for_absent_provenance(self):
        ctx = _make_acceptable_ctx(absent_provenance=True)
        queue = build_research_review_queue([ctx], _REF_UTC)
        assert queue[0]["research_queue_bucket"] == BUCKET_DATA_QUALITY_BLOCKED

    def test_manual_source_review_required_bucket_for_resolution_ambiguity(self):
        ctx = _make_acceptable_ctx(has_resolution_ambiguity=True, score=0.5)
        queue = build_research_review_queue([ctx], _REF_UTC)
        assert queue[0]["research_queue_bucket"] == BUCKET_MANUAL_SOURCE_REVIEW_REQUIRED

    def test_manual_source_review_required_bucket_for_source_hierarchy(self):
        ctx = _make_acceptable_ctx(manual_source_review=True, score=0.5)
        queue = build_research_review_queue([ctx], _REF_UTC)
        assert queue[0]["research_queue_bucket"] == BUCKET_MANUAL_SOURCE_REVIEW_REQUIRED

    def test_review_later_for_low_score_non_blocked(self):
        ctx = _make_acceptable_ctx(score=0.2, quality_status="ACCEPTABLE")
        queue = build_research_review_queue([ctx], _REF_UTC)
        assert queue[0]["research_queue_bucket"] == BUCKET_REVIEW_LATER

    def test_deprioritized_for_no_score(self):
        ctx = _make_deprioritized_ctx()
        queue = build_research_review_queue([ctx], _REF_UTC)
        assert queue[0]["research_queue_bucket"] == BUCKET_DEPRIORITIZED


# ── Queue sort order tests ────────────────────────────────────────────────────

class TestQueueSortOrder:
    def test_deterministic_ordering_same_inputs(self):
        ctxs = [
            _make_acceptable_ctx("mkt-a", score=0.7),
            _make_acceptable_ctx("mkt-b", score=0.5),
            _make_blocked_ctx("mkt-c"),
        ]
        q1 = build_research_review_queue(ctxs, _REF_UTC)
        q2 = build_research_review_queue(ctxs, _REF_UTC)
        assert [p["market_id"] for p in q1] == [p["market_id"] for p in q2]

    def test_bucket_priority_respected(self):
        blocked = _make_blocked_ctx("mkt-blocked")
        review_later = _make_acceptable_ctx("mkt-later", score=0.2)
        review_first = _make_acceptable_ctx("mkt-first", score=0.8)
        dep = _make_deprioritized_ctx("mkt-dep")
        manual = _make_acceptable_ctx("mkt-manual", has_resolution_ambiguity=True, score=0.5)

        queue = build_research_review_queue(
            [dep, blocked, review_later, review_first, manual], _REF_UTC
        )
        buckets = [p["research_queue_bucket"] for p in queue]
        # REVIEW_FIRST must come before MANUAL_SOURCE_REVIEW_REQUIRED,
        # MANUAL_SOURCE_REVIEW_REQUIRED before REVIEW_LATER, etc.
        assert buckets[0] == BUCKET_REVIEW_FIRST
        assert BUCKET_MANUAL_SOURCE_REVIEW_REQUIRED in buckets
        assert BUCKET_REVIEW_LATER in buckets
        assert BUCKET_DATA_QUALITY_BLOCKED in buckets
        assert BUCKET_DEPRIORITIZED in buckets
        # Check relative ordering
        idx_first = buckets.index(BUCKET_REVIEW_FIRST)
        idx_manual = buckets.index(BUCKET_MANUAL_SOURCE_REVIEW_REQUIRED)
        idx_later = buckets.index(BUCKET_REVIEW_LATER)
        idx_blocked = buckets.index(BUCKET_DATA_QUALITY_BLOCKED)
        idx_dep = buckets.index(BUCKET_DEPRIORITIZED)
        assert idx_first < idx_manual < idx_later < idx_blocked < idx_dep

    def test_higher_score_first_within_bucket(self):
        high = _make_acceptable_ctx("mkt-high", score=0.9)
        low = _make_acceptable_ctx("mkt-low", score=0.5)
        queue = build_research_review_queue([low, high], _REF_UTC)
        assert queue[0]["market_id"] == "mkt-high"
        assert queue[1]["market_id"] == "mkt-low"

    def test_market_id_tiebreaker(self):
        ctx_a = _make_acceptable_ctx("mkt-alpha", score=0.7)
        ctx_b = _make_acceptable_ctx("mkt-beta", score=0.7)
        ctx_c = _make_acceptable_ctx("mkt-charlie", score=0.7)
        queue = build_research_review_queue([ctx_c, ctx_a, ctx_b], _REF_UTC)
        ids = [p["market_id"] for p in queue]
        assert ids == ["mkt-alpha", "mkt-beta", "mkt-charlie"]

    def test_queue_ranks_are_sequential(self):
        ctxs = [_make_acceptable_ctx(f"mkt-{i}", score=0.5) for i in range(5)]
        queue = build_research_review_queue(ctxs, _REF_UTC)
        for i, packet in enumerate(queue, start=1):
            assert packet["queue_rank"] == i


# ── Review reasons tests ──────────────────────────────────────────────────────

class TestReviewReasons:
    def test_reasons_are_deterministic(self):
        ctx = _make_acceptable_ctx(has_resolution_ambiguity=True, score=0.6)
        p1 = build_research_session_packet(ctx, 1, BUCKET_REVIEW_FIRST)
        p2 = build_research_session_packet(ctx, 1, BUCKET_REVIEW_FIRST)
        assert p1["review_reasons"] == p2["review_reasons"]

    def test_score_available_reason_present(self):
        ctx = _make_acceptable_ctx(score=0.6)
        packet = build_research_session_packet(ctx, 1, BUCKET_REVIEW_FIRST)
        assert "research_priority_score_available" in packet["review_reasons"]

    def test_score_not_available_reason_absent(self):
        ctx = _make_deprioritized_ctx()
        packet = build_research_session_packet(ctx, 1, BUCKET_DEPRIORITIZED)
        assert "research_priority_score_available" not in packet["review_reasons"]

    def test_no_trade_like_wording_in_reasons(self):
        ctx = _make_acceptable_ctx(has_resolution_ambiguity=True, score=0.6,
                                   relationship_candidate_count=2)
        packet = build_research_session_packet(ctx, 1, BUCKET_REVIEW_FIRST)
        forbidden_terms = {"alpha", "edge", "opportunity", "arbitrage",
                           "buy", "sell", "signal", "expected_return",
                           "fill", "slippage", "tradable", "execution"}
        for reason in packet["review_reasons"]:
            for term in forbidden_terms:
                assert term not in reason.lower(), f"Forbidden term '{term}' in reason: {reason}"

    def test_microstructure_reason_present_when_available(self):
        ctx = _make_acceptable_ctx(order_book_available=True, score=0.6)
        packet = build_research_session_packet(ctx, 1, BUCKET_REVIEW_FIRST)
        assert "microstructure_metadata_available" in packet["review_reasons"]

    def test_cross_market_reason_present_when_candidates(self):
        ctx = _make_acceptable_ctx(relationship_candidate_count=3, score=0.6)
        packet = build_research_session_packet(ctx, 1, BUCKET_REVIEW_FIRST)
        assert "cross_market_candidates_present" in packet["review_reasons"]

    def test_staleness_reason_present_when_stale(self):
        ctx = _make_acceptable_ctx(staleness_flag=True, requires_recapture=True)
        queue = build_research_review_queue([ctx], _REF_UTC)
        assert "staleness_warning_present" in queue[0]["review_reasons"]

    def test_missing_data_reason_present_when_warning(self):
        ctx = _make_acceptable_ctx(missing_data_warning=True, missing_market_status=True)
        queue = build_research_review_queue([ctx], _REF_UTC)
        assert "missing_data_warning_present" in queue[0]["review_reasons"]


# ── Caution flags tests ───────────────────────────────────────────────────────

class TestCautionFlags:
    def test_flags_are_deterministic(self):
        ctx = _make_acceptable_ctx(missing_market_status=True)
        p1 = build_research_session_packet(ctx, 1, BUCKET_DATA_QUALITY_BLOCKED)
        p2 = build_research_session_packet(ctx, 1, BUCKET_DATA_QUALITY_BLOCKED)
        assert p1["blocking_or_caution_flags"] == p2["blocking_or_caution_flags"]

    def test_no_trade_like_wording_in_flags(self):
        ctx = _make_blocked_ctx()
        packet = build_research_session_packet(ctx, 1, BUCKET_DATA_QUALITY_BLOCKED)
        forbidden_terms = {"alpha", "edge", "opportunity", "arbitrage",
                           "buy", "sell", "signal", "expected_return",
                           "fill", "slippage", "tradable", "execution"}
        for flag in packet["blocking_or_caution_flags"]:
            for term in forbidden_terms:
                assert term not in flag.lower(), f"Forbidden term '{term}' in flag: {flag}"

    def test_stale_recapture_flag_present(self):
        ctx = _make_acceptable_ctx(requires_recapture=True)
        packet = build_research_session_packet(ctx, 1, BUCKET_DATA_QUALITY_BLOCKED)
        assert "stale_input_requires_recapture" in packet["blocking_or_caution_flags"]

    def test_missing_question_flag_present(self):
        ctx = _make_acceptable_ctx(missing_question=True, missing_data_warning=True)
        packet = build_research_session_packet(ctx, 1, BUCKET_DATA_QUALITY_BLOCKED)
        assert "missing_question" in packet["blocking_or_caution_flags"]

    def test_missing_market_status_flag_present(self):
        ctx = _make_acceptable_ctx(missing_market_status=True, missing_data_warning=True)
        packet = build_research_session_packet(ctx, 1, BUCKET_DATA_QUALITY_BLOCKED)
        assert "missing_market_status" in packet["blocking_or_caution_flags"]

    def test_missing_order_book_flag_present(self):
        ctx = _make_acceptable_ctx(missing_order_book=True, missing_data_warning=True)
        packet = build_research_session_packet(ctx, 1, BUCKET_DATA_QUALITY_BLOCKED)
        assert "missing_order_book" in packet["blocking_or_caution_flags"]

    def test_weak_provenance_flag_for_absent(self):
        ctx = _make_acceptable_ctx(absent_provenance=True)
        packet = build_research_session_packet(ctx, 1, BUCKET_DATA_QUALITY_BLOCKED)
        assert "weak_or_absent_provenance" in packet["blocking_or_caution_flags"]

    def test_source_metadata_missing_flag(self):
        ctx = _make_acceptable_ctx(source_metadata_available=False, manual_source_review=True)
        packet = build_research_session_packet(ctx, 1, BUCKET_MANUAL_SOURCE_REVIEW_REQUIRED)
        assert "source_metadata_missing" in packet["blocking_or_caution_flags"]

    def test_one_sided_flag_for_one_sided_book(self):
        ctx = _make_acceptable_ctx(order_book_available=True, two_sided=False, score=0.4)
        packet = build_research_session_packet(ctx, 1, BUCKET_REVIEW_LATER)
        assert "one_sided_or_empty_order_book" in packet["blocking_or_caution_flags"]

    def test_cross_market_flag_for_candidates(self):
        ctx = _make_acceptable_ctx(relationship_candidate_count=2, score=0.6)
        packet = build_research_session_packet(ctx, 1, BUCKET_REVIEW_FIRST)
        assert "cross_market_relationships_require_human_review" in packet["blocking_or_caution_flags"]


# ── Report summary tests ──────────────────────────────────────────────────────

class TestReportSummary:
    def test_report_queue_summary_counts_correct(self):
        ctxs = [
            _make_acceptable_ctx("mkt-1", score=0.8),
            _make_acceptable_ctx("mkt-2", score=0.6),
            _make_acceptable_ctx("mkt-3", score=0.2),
            _make_acceptable_ctx("mkt-4", has_resolution_ambiguity=True, score=0.5),
            _make_blocked_ctx("mkt-5"),
            _make_deprioritized_ctx("mkt-6"),
        ]
        report = build_local_human_review_report(ctxs, _REF_UTC)
        qs = report["queue_summary"]
        assert qs["total_markets"] == 6
        assert qs["review_first_count"] == 2
        assert qs["review_later_count"] == 1
        assert qs["manual_source_review_required_count"] == 1
        assert qs["data_quality_blocked_count"] == 1
        assert qs["deprioritized_count"] == 1

    def test_report_type_correct(self):
        report = build_local_human_review_report([], _REF_UTC)
        assert report["report_type"] == "LOCAL_HUMAN_REVIEW_REPORT_V1"

    def test_report_advisory_label(self):
        report = build_local_human_review_report([], _REF_UTC)
        assert report["advisory_label"] == "ADVISORY_ONLY_HUMAN_REVIEW_REQUIRED"

    def test_report_empty_input(self):
        report = build_local_human_review_report([], _REF_UTC)
        qs = report["queue_summary"]
        assert qs["total_markets"] == 0
        assert qs["review_first_count"] == 0
        assert report["review_queue"] == []
        assert report["excluded_or_deprioritized"] == []

    def test_blocked_and_deprioritized_in_excluded(self):
        ctxs = [
            _make_acceptable_ctx("mkt-good", score=0.7),
            _make_blocked_ctx("mkt-blocked"),
            _make_deprioritized_ctx("mkt-dep"),
        ]
        report = build_local_human_review_report(ctxs, _REF_UTC)
        excluded_ids = {p["market_id"] for p in report["excluded_or_deprioritized"]}
        assert "mkt-blocked" in excluded_ids
        assert "mkt-dep" in excluded_ids
        queue_ids = {p["market_id"] for p in report["review_queue"]}
        assert "mkt-good" in queue_ids
        assert "mkt-blocked" not in queue_ids
        assert "mkt-dep" not in queue_ids

    def test_global_warnings_for_blocked(self):
        ctxs = [_make_blocked_ctx("mkt-b")]
        report = build_local_human_review_report(ctxs, _REF_UTC)
        assert any("DATA_QUALITY_BLOCKED" in w for w in report["global_warnings"])

    def test_global_warnings_for_deprioritized(self):
        ctxs = [_make_deprioritized_ctx("mkt-d")]
        report = build_local_human_review_report(ctxs, _REF_UTC)
        assert any("DEPRIORITIZED" in w for w in report["global_warnings"])


# ── Session packet structure tests ───────────────────────────────────────────

class TestSessionPacketStructure:
    def test_packet_has_all_required_fields(self):
        ctx = _make_acceptable_ctx()
        packet = build_research_session_packet(ctx, 1, BUCKET_REVIEW_FIRST)
        required = [
            "market_id", "question", "queue_rank", "research_queue_bucket",
            "research_review_priority", "research_priority_score",
            "human_review_required", "review_reasons", "blocking_or_caution_flags",
            "data_quality_summary", "resolution_summary", "microstructure_summary",
            "cross_market_summary", "source_hierarchy_summary",
            "forbidden_interpretation_notice", "advisory_label",
        ]
        for field in required:
            assert field in packet, f"Missing required field: {field}"

    def test_packet_data_quality_summary_structure(self):
        ctx = _make_acceptable_ctx()
        packet = build_research_session_packet(ctx, 1, BUCKET_REVIEW_FIRST)
        dqs = packet["data_quality_summary"]
        assert "quality_status" in dqs
        assert "staleness_flag" in dqs
        assert "missing_data_warning" in dqs
        assert "provenance_degraded" in dqs

    def test_packet_resolution_summary_structure(self):
        ctx = _make_acceptable_ctx()
        packet = build_research_session_packet(ctx, 1, BUCKET_REVIEW_FIRST)
        rs = packet["resolution_summary"]
        assert "resolution_ambiguity_available" in rs
        assert "manual_review_required" in rs
        assert "highest_ambiguity_severity" in rs

    def test_packet_microstructure_summary_structure(self):
        ctx = _make_acceptable_ctx()
        packet = build_research_session_packet(ctx, 1, BUCKET_REVIEW_FIRST)
        ms = packet["microstructure_summary"]
        assert "order_book_available" in ms
        assert "two_sided_structure_observed" in ms
        assert "order_book_stale" in ms

    def test_packet_cross_market_summary_structure(self):
        ctx = _make_acceptable_ctx()
        packet = build_research_session_packet(ctx, 1, BUCKET_REVIEW_FIRST)
        cs = packet["cross_market_summary"]
        assert "relationship_metadata_available" in cs
        assert "relationship_candidate_count" in cs
        assert cs["metadata_only"] is True

    def test_packet_source_hierarchy_summary_structure(self):
        ctx = _make_acceptable_ctx()
        packet = build_research_session_packet(ctx, 1, BUCKET_REVIEW_FIRST)
        sh = packet["source_hierarchy_summary"]
        assert "source_metadata_available" in sh
        assert "manual_source_review_required" in sh
        assert sh["official_source_monitoring_performed"] is False

    def test_packet_human_review_required_true(self):
        ctx = _make_acceptable_ctx()
        packet = build_research_session_packet(ctx, 1, BUCKET_REVIEW_FIRST)
        assert packet["human_review_required"] is True

    def test_packet_advisory_label_correct(self):
        ctx = _make_acceptable_ctx()
        packet = build_research_session_packet(ctx, 1, BUCKET_REVIEW_FIRST)
        assert packet["advisory_label"] == "ADVISORY_ONLY_HUMAN_REVIEW_REQUIRED"

    def test_packet_forbidden_interpretation_notice_present(self):
        ctx = _make_acceptable_ctx()
        packet = build_research_session_packet(ctx, 1, BUCKET_REVIEW_FIRST)
        assert len(packet["forbidden_interpretation_notice"]) > 0
        assert "ADVISORY_ONLY" in packet["forbidden_interpretation_notice"]


# ── Non-signal boundary tests ─────────────────────────────────────────────────

class TestNonSignalBoundary:
    _FORBIDDEN_FIELD_TERMS = {
        "trade_signal", "alpha_score", "opportunity_score", "expected_return",
        "profit_probability", "buy_recommendation", "sell_recommendation",
        "entry", "exit", "position_size", "leverage", "execution_confidence",
        "order_params", "strategy_signal", "paper_trade_authorization",
        "live_trade_authorization",
    }

    _FORBIDDEN_VALUE_TERMS = {
        "alpha", "edge", "opportunity", "arbitrage", "mispricing",
        "tradability", "tradeable", "tradable", "buy", "sell",
        "entry", "exit", "position size", "leverage", "expected return",
        "execution confidence", "fill probability", "slippage", "profitable",
        "signal", "recommendation to trade",
    }

    def _collect_all_field_names(self, obj: object, prefix: str = "") -> list[str]:
        names: list[str] = []
        if isinstance(obj, dict):
            for k, v in obj.items():
                full = f"{prefix}.{k}" if prefix else k
                names.append(full)
                names.extend(self._collect_all_field_names(v, full))
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                names.extend(self._collect_all_field_names(item, f"{prefix}[{i}]"))
        return names

    def _collect_all_string_values(self, obj: object) -> list[str]:
        values: list[str] = []
        if isinstance(obj, dict):
            for v in obj.values():
                values.extend(self._collect_all_string_values(v))
        elif isinstance(obj, list):
            for item in obj:
                values.extend(self._collect_all_string_values(item))
        elif isinstance(obj, str):
            values.append(obj)
        return values

    def _make_full_report(self) -> dict:
        ctxs = [
            _make_acceptable_ctx("mkt-a", score=0.8),
            _make_blocked_ctx("mkt-b"),
            _make_acceptable_ctx("mkt-c", has_resolution_ambiguity=True, score=0.5),
            _make_deprioritized_ctx("mkt-d"),
        ]
        return build_local_human_review_report(ctxs, _REF_UTC)

    def test_no_forbidden_field_names_in_report(self):
        report = self._make_full_report()
        all_fields = self._collect_all_field_names(report)
        for field in all_fields:
            leaf = field.split(".")[-1].lower()
            for term in self._FORBIDDEN_FIELD_TERMS:
                assert term not in leaf, f"Forbidden field term '{term}' in field path: {field}"

    def test_no_forbidden_value_terms_in_non_notice_strings(self):
        report = self._make_full_report()

        def check_object(obj: object, path: str = "") -> None:
            if isinstance(obj, dict):
                for k, v in obj.items():
                    new_path = f"{path}.{k}"
                    if k in ("forbidden_interpretation_notice", "global_advisory_notice"):
                        continue  # explicit forbidden-scope notices are allowed
                    check_object(v, new_path)
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    check_object(item, f"{path}[{i}]")
            elif isinstance(obj, str):
                lower = obj.lower()
                for term in self._FORBIDDEN_VALUE_TERMS:
                    assert term not in lower, (
                        f"Forbidden value term '{term}' found at path {path!r}: {obj!r}"
                    )

        check_object(report)

    def test_no_forbidden_field_names_in_packet(self):
        ctx = _make_acceptable_ctx()
        packet = build_research_session_packet(ctx, 1, BUCKET_REVIEW_FIRST)
        all_fields = self._collect_all_field_names(packet)
        for field in all_fields:
            leaf = field.split(".")[-1].lower()
            for term in self._FORBIDDEN_FIELD_TERMS:
                assert term not in leaf, f"Forbidden field term '{term}' in field path: {field}"


# ── Advisory label tests ──────────────────────────────────────────────────────

class TestAdvisoryLabels:
    def test_report_includes_advisory_label(self):
        report = build_local_human_review_report([], _REF_UTC)
        assert report["advisory_label"] == "ADVISORY_ONLY_HUMAN_REVIEW_REQUIRED"

    def test_packet_includes_advisory_label(self):
        ctx = _make_acceptable_ctx()
        packet = build_research_session_packet(ctx, 1, BUCKET_REVIEW_FIRST)
        assert packet["advisory_label"] == "ADVISORY_ONLY_HUMAN_REVIEW_REQUIRED"

    def test_all_queue_packets_have_advisory_label(self):
        ctxs = [_make_acceptable_ctx(f"mkt-{i}", score=0.5) for i in range(3)]
        queue = build_research_review_queue(ctxs, _REF_UTC)
        for packet in queue:
            assert packet["advisory_label"] == "ADVISORY_ONLY_HUMAN_REVIEW_REQUIRED"


# ── Scorer compatibility tests ────────────────────────────────────────────────

class TestScorerCompatibility:
    """Verify queue functions can consume scored market objects from WP49 scorer."""

    def _make_scored_market_object(
        self,
        market_id: str = "mkt-scored",
        score: float = 0.6,
        quality_status: str = "ACCEPTABLE",
    ) -> dict:
        return {
            "market_id": market_id,
            "question": "Will Y happen?",
            "category": "Politics",
            "active_status": "active",
            "research_priority_score": score,
            "score_rank": None,
            "score_components": {
                "data_completeness": 0.9,
                "snapshot_freshness": 1.0,
                "quality_gate_status": 1.0,
                "market_activity_metadata": 1.0,
                "category_coverage": 1.0,
                "token_outcome_completeness": 1.0,
                "order_book_availability": 1.0,
                "spread_structure_observed": 0.5,
                "visible_local_liquidity_proxy": 0.25,
                "guard_provenance_quality": 0.8,
                "duplicate_conflict_penalty": 0.0,
                "missing_data_penalty": 0.0,
                "deferred_item_caveat_penalty": -0.05,
            },
            "staleness": {"staleness_flag": False, "requires_recapture_before_use": False},
            "provenance": {
                "snapshot_manifest_ids": ["snap-1"],
                "source_export_paths": ["out.jsonl"],
                "provenance_degraded": False,
            },
            "missing_data": {
                "missing_data_warning": False,
                "missing_question": False,
                "missing_market_status": False,
                "missing_order_book": False,
                "missing_outcome_tokens": False,
            },
            "quality_gates": {"quality_status": quality_status},
            "component_explanation": "test",
            "advisory_label": "ADVISORY_ONLY_HUMAN_REVIEW_REQUIRED",
            "human_review_required": True,
            "forbidden_use_notice": "test",
        }

    def test_queue_consumes_scored_market_object(self):
        obj = self._make_scored_market_object(score=0.7)
        queue = build_research_review_queue([obj], _REF_UTC)
        assert len(queue) == 1
        assert queue[0]["research_priority_score"] == pytest.approx(0.7, abs=1e-6)

    def test_queue_handles_mix_of_contexts_and_scored_objects(self):
        raw = _make_acceptable_ctx("mkt-raw", score=0.5)
        scored = self._make_scored_market_object("mkt-scored", score=0.8)
        queue = build_research_review_queue([raw, scored], _REF_UTC)
        assert len(queue) == 2
        ids = [p["market_id"] for p in queue]
        assert "mkt-raw" in ids
        assert "mkt-scored" in ids

    def test_report_accepts_scored_market_objects(self):
        objs = [self._make_scored_market_object(f"mkt-{i}", score=0.5) for i in range(3)]
        report = build_local_human_review_report(objs, _REF_UTC)
        assert report["queue_summary"]["total_markets"] == 3
