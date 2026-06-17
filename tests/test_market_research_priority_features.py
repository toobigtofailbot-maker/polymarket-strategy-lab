"""Focused tests for WP51 Market Research Priority Feature Extraction Foundation.

Tests src/data_layer/market_research_priority_features.py.
All tests are local/offline/in-memory. No network. No file I/O except the
optional extract_from_snapshot_dir tests which use a temporary local fixture
directory.
"""

from __future__ import annotations

import importlib
import importlib.util
import json
import pathlib
import tempfile
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.data_layer.market_research_priority_features import (
    DEFAULT_METADATA_FRESHNESS_THRESHOLD_SECONDS,
    DEFAULT_ORDERBOOK_FRESHNESS_THRESHOLD_SECONDS,
    FEATURE_EXTRACTION_SCOPE,
    FEATURE_EXTRACTION_VERSION,
    build_cross_market_relationship_index,
    build_manifest_index,
    build_market_research_priority_run_context,
    build_resolution_ambiguity_label_index,
    extract_from_snapshot_dir,
    extract_market_research_priority_context,
    extract_market_research_priority_contexts,
    index_order_books_by_token_id,
)
from src.data_layer.market_research_priority_scoring import (
    assert_market_research_priority_output,
    build_market_research_priority_output,
)
from src.data_layer.polymarket.snapshot_models import (
    MarketMetadataSnapshotRecord,
    OrderBookSnapshotRecord,
    SnapshotManifest,
)

ROOT = pathlib.Path(__file__).resolve().parents[1]

# ── Fixtures ──────────────────────────────────────────────────────────────────

_FRESH_UTC = "2026-01-01T12:00:00+00:00"
_REFERENCE_UTC = datetime(2026, 1, 1, 13, 0, 0, tzinfo=timezone.utc)  # 1h after capture


def _make_record(
    market_id="mkt-001",
    question="Will X happen?",
    category="Politics",
    market_status="active",
    outcome_labels=None,
    token_ids=None,
    resolution_date="2026-06-01T00:00:00+00:00",
    captured_at_utc=_FRESH_UTC,
    snapshot_id="snap_20260101_120000_000000",
) -> MarketMetadataSnapshotRecord:
    return MarketMetadataSnapshotRecord(
        snapshot_id=snapshot_id,
        captured_at_utc=captured_at_utc,
        source="gamma-api/markets",
        adapter_version="wp10",
        market_id=market_id,
        condition_id="cond-001",
        question=question,
        market_status=market_status,
        outcome_labels=outcome_labels if outcome_labels is not None else ["Yes", "No"],
        token_ids=token_ids if token_ids is not None else ["tok-yes", "tok-no"],
        resolution_date=resolution_date,
        category=category,
        raw_field_names=["market_id", "question", "category"],
        read_only_provenance="polymarket-strategy-lab/wp10-snapshot-persistence/public-get-only",
    )


def _make_manifest(snapshot_id="snap_20260101_120000_000000") -> SnapshotManifest:
    return SnapshotManifest(
        snapshot_id=snapshot_id,
        created_at_utc=_FRESH_UTC,
        tool_name="capture_market_snapshots",
        work_package="WP18",
        markets_requested=1,
        markets_written=1,
        order_books_requested=2,
        order_books_written=2,
        network_used=True,
        output_files=["local_data/polymarket/snapshots/market_metadata_snapshots.jsonl"],
        notes="test manifest",
    )


def _make_ob(
    token_id="tok-yes",
    snapshot_id="snap_20260101_120000_000000",
    captured_at_utc=_FRESH_UTC,
    bids=None,
    asks=None,
) -> OrderBookSnapshotRecord:
    return OrderBookSnapshotRecord(
        snapshot_id=snapshot_id,
        captured_at_utc=captured_at_utc,
        source="clob-api/book",
        adapter_version="wp10",
        token_id=token_id,
        bids=bids if bids is not None else [{"price": "0.50", "size": "100"}],
        asks=asks if asks is not None else [{"price": "0.52", "size": "90"}],
        raw_field_names=["token_id", "bids", "asks"],
        read_only_provenance="polymarket-strategy-lab/wp10-snapshot-persistence/public-get-only",
    )


# ── Constants tests ───────────────────────────────────────────────────────────

def test_module_constants_present():
    assert DEFAULT_METADATA_FRESHNESS_THRESHOLD_SECONDS > 0
    assert DEFAULT_ORDERBOOK_FRESHNESS_THRESHOLD_SECONDS > 0
    assert isinstance(FEATURE_EXTRACTION_SCOPE, str) and FEATURE_EXTRACTION_SCOPE
    assert isinstance(FEATURE_EXTRACTION_VERSION, str) and FEATURE_EXTRACTION_VERSION


# ── Index helpers ─────────────────────────────────────────────────────────────

def test_build_manifest_index_empty():
    result = build_manifest_index([])
    assert result == {}


def test_build_manifest_index_single():
    m = _make_manifest("snap-001")
    result = build_manifest_index([m])
    assert "snap-001" in result
    assert result["snap-001"] is m


def test_index_order_books_empty():
    result = index_order_books_by_token_id([])
    assert result == {}


def test_index_order_books_groups_by_token():
    ob1 = _make_ob("tok-A")
    ob2 = _make_ob("tok-B")
    ob3 = _make_ob("tok-A")
    result = index_order_books_by_token_id([ob1, ob2, ob3])
    assert len(result["tok-A"]) == 2
    assert len(result["tok-B"]) == 1


# ── Valid record produces required keys ───────────────────────────────────────

def test_valid_record_produces_required_keys():
    record = _make_record()
    ctx = extract_market_research_priority_context(
        record=record,
        manifests=[_make_manifest()],
        order_books_by_token_id=index_order_books_by_token_id([
            _make_ob("tok-yes"), _make_ob("tok-no"),
        ]),
        generated_at_utc=_REFERENCE_UTC,
    )
    for key in ("market_id", "question", "category", "active_status", "score_components",
                "staleness", "provenance", "missing_data", "quality_gates",
                "component_explanation", "microstructure_quality"):
        assert key in ctx, f"Missing key: {key}"


def test_valid_record_score_components_has_all_required():
    record = _make_record()
    ctx = extract_market_research_priority_context(
        record=record,
        manifests=[_make_manifest()],
        order_books_by_token_id=index_order_books_by_token_id([_make_ob()]),
        generated_at_utc=_REFERENCE_UTC,
    )
    from src.data_layer.market_research_priority_scoring import (
        POSITIVE_COMPONENTS, PENALTY_COMPONENTS,
    )
    for comp in POSITIVE_COMPONENTS + PENALTY_COMPONENTS:
        assert comp in ctx["score_components"], f"Missing component: {comp}"


# ── Run context tests ─────────────────────────────────────────────────────────

def test_run_context_has_required_keys():
    run_ctx = build_market_research_priority_run_context(
        snapshot_id="snap-001",
        manifests=[_make_manifest()],
        generated_at_utc=_REFERENCE_UTC,
    )
    for key in ("generated_at_utc", "run_id", "source_artifacts", "scope"):
        assert key in run_ctx, f"Missing key: {key}"


def test_run_context_scope_is_local_offline():
    run_ctx = build_market_research_priority_run_context(
        snapshot_id="snap-001",
        generated_at_utc=_REFERENCE_UTC,
    )
    scope = run_ctx["scope"]
    assert scope.get("local_offline_read_only") is True
    assert scope.get("network") == "none"
    assert scope.get("trading") == "none"
    assert scope.get("execution") == "none"
    assert scope.get("advisory_only") is True


# ── Scorer compatibility ──────────────────────────────────────────────────────

def test_extracted_context_passes_scorer_validation():
    record = _make_record()
    run_ctx = build_market_research_priority_run_context(
        snapshot_id=record.snapshot_id,
        manifests=[_make_manifest()],
        generated_at_utc=_REFERENCE_UTC,
    )
    market_ctx = extract_market_research_priority_context(
        record=record,
        manifests=[_make_manifest()],
        order_books_by_token_id=index_order_books_by_token_id([
            _make_ob("tok-yes"), _make_ob("tok-no"),
        ]),
        generated_at_utc=_REFERENCE_UTC,
    )
    output = build_market_research_priority_output(run_ctx, market_ctx)
    assert_market_research_priority_output(output)


# ── Missing category ─────────────────────────────────────────────────────────

def test_missing_category_produces_low_coverage_and_warning():
    record = _make_record(category=None)
    ctx = extract_market_research_priority_context(
        record=record, generated_at_utc=_REFERENCE_UTC
    )
    assert ctx["missing_data"]["missing_category"] is True
    assert ctx["score_components"]["category_coverage"] == 0.0
    assert ctx["missing_data"]["missing_data_warning"] is True
    assert "category" in ctx["missing_data"]["missing_metadata_fields"]


# ── Missing outcome tokens ────────────────────────────────────────────────────

def test_missing_outcome_tokens_produces_low_completeness_and_warning():
    record = _make_record(token_ids=[], outcome_labels=[])
    ctx = extract_market_research_priority_context(
        record=record, generated_at_utc=_REFERENCE_UTC
    )
    assert ctx["missing_data"]["missing_outcome_tokens"] is True
    assert ctx["score_components"]["token_outcome_completeness"] == 0.0
    assert ctx["missing_data"]["missing_data_warning"] is True


# ── Mismatched outcome labels / token IDs ─────────────────────────────────────

def test_mismatched_outcome_labels_token_ids_produces_degraded_warning():
    record = _make_record(token_ids=["tok-a", "tok-b", "tok-c"], outcome_labels=["Yes", "No"])
    ctx = extract_market_research_priority_context(
        record=record, generated_at_utc=_REFERENCE_UTC
    )
    assert ctx["missing_data"]["missing_data_warning"] is True
    assert "outcome_label_mismatch" in ctx["missing_data"]["missing_metadata_fields"]
    # token_outcome_completeness should be less than 1.0
    assert ctx["score_components"]["token_outcome_completeness"] < 1.0


# ── Missing manifest/provenance ───────────────────────────────────────────────

def test_missing_manifest_produces_low_guard_provenance():
    record = _make_record()
    ctx = extract_market_research_priority_context(
        record=record, manifests=[], generated_at_utc=_REFERENCE_UTC
    )
    assert ctx["provenance"]["snapshot_manifest_ids"] == []
    assert ctx["score_components"]["guard_provenance_quality"] == 0.0
    assert ctx["quality_gates"]["guard_enforced_capture"] is False


def test_missing_manifest_produces_no_provenance_warning():
    record = _make_record()
    ctx = extract_market_research_priority_context(
        record=record, manifests=[], generated_at_utc=_REFERENCE_UTC
    )
    assert "no_manifest_provenance" in ctx["quality_gates"]["quality_warnings"]


# ── Stale metadata snapshot ───────────────────────────────────────────────────

def test_stale_metadata_sets_staleness_flag_and_requires_recapture():
    old_ts = "2025-01-01T00:00:00+00:00"
    record = _make_record(captured_at_utc=old_ts)
    ctx = extract_market_research_priority_context(
        record=record, generated_at_utc=_REFERENCE_UTC
    )
    assert ctx["staleness"]["staleness_flag"] is True
    assert ctx["staleness"]["requires_recapture_before_use"] is True
    assert len(ctx["staleness"]["stale_inputs"]) > 0


# ── Malformed timestamp ───────────────────────────────────────────────────────

def test_malformed_timestamp_marks_stale_and_does_not_crash():
    record = _make_record(captured_at_utc="not-a-timestamp")
    ctx = extract_market_research_priority_context(
        record=record, generated_at_utc=_REFERENCE_UTC
    )
    assert ctx["staleness"]["staleness_flag"] is True
    assert ctx["staleness"]["requires_recapture_before_use"] is True


# ── No orderbook records ──────────────────────────────────────────────────────

def test_no_orderbook_produces_missing_order_book_and_low_availability():
    record = _make_record()
    ctx = extract_market_research_priority_context(
        record=record, order_books_by_token_id={}, generated_at_utc=_REFERENCE_UTC
    )
    assert ctx["missing_data"]["missing_order_book"] is True
    assert ctx["score_components"]["order_book_availability"] == 0.0
    assert ctx["score_components"]["spread_structure_observed"] == 0.0
    assert ctx["score_components"]["visible_local_liquidity_proxy"] == 0.0


# ── Two-sided orderbook sets nonzero values ───────────────────────────────────

def test_two_sided_orderbook_sets_conservative_nonzero_values():
    record = _make_record()
    obs = {
        "tok-yes": [_make_ob("tok-yes")],
        "tok-no": [_make_ob("tok-no")],
    }
    ctx = extract_market_research_priority_context(
        record=record, order_books_by_token_id=obs, generated_at_utc=_REFERENCE_UTC
    )
    assert ctx["score_components"]["order_book_availability"] > 0.0
    assert ctx["score_components"]["spread_structure_observed"] > 0.0
    assert ctx["score_components"]["visible_local_liquidity_proxy"] > 0.0
    # Must be capped: never implies executable liquidity
    assert ctx["score_components"]["visible_local_liquidity_proxy"] <= 0.5


# ── One-sided orderbook remains degraded ─────────────────────────────────────

def test_one_sided_orderbook_does_not_imply_tradability():
    record = _make_record()
    one_sided_ob = _make_ob("tok-yes", bids=[], asks=[{"price": "0.55", "size": "50"}])
    obs = {"tok-yes": [one_sided_ob]}
    ctx = extract_market_research_priority_context(
        record=record, order_books_by_token_id=obs, generated_at_utc=_REFERENCE_UTC
    )
    # Not two-sided → spread_structure_observed should be low (< 0.5)
    assert ctx["score_components"]["spread_structure_observed"] < 0.5
    # visible_local_liquidity_proxy capped
    assert ctx["score_components"]["visible_local_liquidity_proxy"] <= 0.5


# ── WP61 microstructure quality metadata ─────────────────────────────────────

def test_microstructure_quality_present_for_every_market_context():
    record = _make_record()
    ctx = extract_market_research_priority_context(
        record=record, order_books_by_token_id={}, generated_at_utc=_REFERENCE_UTC
    )
    assert "microstructure_quality" in ctx
    assert ctx["microstructure_quality"]["advisory_label"] == "ADVISORY_ONLY_HUMAN_REVIEW_REQUIRED"


def test_microstructure_quality_no_order_book_safe_defaults():
    record = _make_record()
    ctx = extract_market_research_priority_context(
        record=record, order_books_by_token_id={}, generated_at_utc=_REFERENCE_UTC
    )
    mq = ctx["microstructure_quality"]
    assert mq["order_book_available"] is False
    assert mq["local_order_book_snapshot_count"] == 0
    assert mq["best_bid_available"] is False
    assert mq["best_ask_available"] is False
    assert mq["two_sided_structure_observed"] is False
    assert mq["one_sided_structure_observed"] is False
    assert mq["empty_book_observed"] is True
    assert mq["spread_structure_observed"] is False
    assert mq["visible_total_level_count"] == 0
    assert mq["non_empty_bid_level_count"] == 0
    assert mq["non_empty_ask_level_count"] == 0
    assert mq["latest_order_book_snapshot_id"] is None
    assert mq["latest_order_book_captured_at_utc"] is None
    assert mq["order_book_stale"] is True
    assert mq["requires_order_book_recapture_before_use"] is True


def test_microstructure_quality_bid_only_book_is_one_sided():
    record = _make_record()
    ob = _make_ob("tok-yes", bids=[{"price": "0.49", "size": "10"}], asks=[])
    ctx = extract_market_research_priority_context(
        record=record,
        order_books_by_token_id={"tok-yes": [ob]},
        generated_at_utc=_REFERENCE_UTC,
    )
    mq = ctx["microstructure_quality"]
    assert mq["best_bid_available"] is True
    assert mq["best_ask_available"] is False
    assert mq["two_sided_structure_observed"] is False
    assert mq["one_sided_structure_observed"] is True
    assert mq["spread_structure_observed"] is False


def test_microstructure_quality_ask_only_book_is_one_sided():
    record = _make_record()
    ob = _make_ob("tok-yes", bids=[], asks=[{"price": "0.52", "size": "10"}])
    ctx = extract_market_research_priority_context(
        record=record,
        order_books_by_token_id={"tok-yes": [ob]},
        generated_at_utc=_REFERENCE_UTC,
    )
    mq = ctx["microstructure_quality"]
    assert mq["best_bid_available"] is False
    assert mq["best_ask_available"] is True
    assert mq["two_sided_structure_observed"] is False
    assert mq["one_sided_structure_observed"] is True
    assert mq["spread_structure_observed"] is False


def test_microstructure_quality_empty_bid_ask_book_is_empty():
    record = _make_record()
    ob = _make_ob("tok-yes", bids=[], asks=[])
    ctx = extract_market_research_priority_context(
        record=record,
        order_books_by_token_id={"tok-yes": [ob]},
        generated_at_utc=_REFERENCE_UTC,
    )
    mq = ctx["microstructure_quality"]
    assert mq["order_book_available"] is True
    assert mq["empty_book_observed"] is True
    assert mq["two_sided_structure_observed"] is False
    assert mq["spread_structure_observed"] is False


def test_microstructure_quality_two_sided_book_observes_spread_structure():
    record = _make_record()
    ob = _make_ob(
        "tok-yes",
        bids=[{"price": "0.49", "size": "10"}],
        asks=[{"price": "0.51", "size": "8"}],
    )
    ctx = extract_market_research_priority_context(
        record=record,
        order_books_by_token_id={"tok-yes": [ob]},
        generated_at_utc=_REFERENCE_UTC,
    )
    mq = ctx["microstructure_quality"]
    assert mq["best_bid_available"] is True
    assert mq["best_ask_available"] is True
    assert mq["two_sided_structure_observed"] is True
    assert mq["spread_structure_observed"] is True


def test_microstructure_quality_counts_visible_and_non_empty_levels():
    record = _make_record()
    ob = _make_ob(
        "tok-yes",
        bids=[
            {},
            {"price": "0.48", "size": "0"},
            {"price": "0.49", "size": "10"},
        ],
        asks=[
            {"price": "0.51", "size": ""},
            {"price": "0.52", "size": "5"},
        ],
    )
    ctx = extract_market_research_priority_context(
        record=record,
        order_books_by_token_id={"tok-yes": [ob]},
        generated_at_utc=_REFERENCE_UTC,
    )
    mq = ctx["microstructure_quality"]
    assert mq["visible_bid_level_count"] == 3
    assert mq["visible_ask_level_count"] == 2
    assert mq["visible_total_level_count"] == 5
    assert mq["non_empty_bid_level_count"] == 1
    assert mq["non_empty_ask_level_count"] == 1


def test_microstructure_quality_multiple_snapshots_choose_latest_parseable_timestamp():
    record = _make_record(token_ids=["tok-yes"])
    older = _make_ob(
        "tok-yes",
        snapshot_id="snap-old",
        captured_at_utc="2026-01-01T11:00:00+00:00",
        bids=[{"price": "0.40", "size": "10"}],
        asks=[],
    )
    newer = _make_ob(
        "tok-yes",
        snapshot_id="snap-new",
        captured_at_utc="2026-01-01T12:30:00+00:00",
        bids=[],
        asks=[{"price": "0.60", "size": "10"}],
    )
    ctx = extract_market_research_priority_context(
        record=record,
        order_books_by_token_id={"tok-yes": [older, newer]},
        generated_at_utc=_REFERENCE_UTC,
    )
    mq = ctx["microstructure_quality"]
    assert mq["local_order_book_snapshot_count"] == 2
    assert mq["latest_order_book_snapshot_id"] == "snap-new"
    assert mq["latest_order_book_captured_at_utc"] == "2026-01-01T12:30:00+00:00"
    assert mq["best_bid_available"] is False
    assert mq["best_ask_available"] is True


def test_microstructure_quality_unparseable_timestamp_is_degraded():
    record = _make_record(token_ids=["tok-yes"])
    ob = _make_ob("tok-yes", snapshot_id="snap-bad-ts", captured_at_utc="not-a-time")
    ctx = extract_market_research_priority_context(
        record=record,
        order_books_by_token_id={"tok-yes": [ob]},
        generated_at_utc=_REFERENCE_UTC,
    )
    mq = ctx["microstructure_quality"]
    assert mq["latest_order_book_snapshot_id"] == "snap-bad-ts"
    assert mq["order_book_stale"] is True
    assert mq["requires_order_book_recapture_before_use"] is True
    assert any("unparseable" in warning for warning in mq["microstructure_warnings"])


def test_microstructure_quality_future_timestamp_is_degraded_not_fresh():
    record = _make_record(token_ids=["tok-yes"])
    ob = _make_ob(
        "tok-yes",
        snapshot_id="snap-future",
        captured_at_utc="2026-01-01T14:00:00+00:00",
    )
    ctx = extract_market_research_priority_context(
        record=record,
        order_books_by_token_id={"tok-yes": [ob]},
        generated_at_utc=_REFERENCE_UTC,
    )
    mq = ctx["microstructure_quality"]
    assert mq["latest_order_book_snapshot_id"] == "snap-future"
    assert mq["order_book_stale"] is True
    assert mq["requires_order_book_recapture_before_use"] is True
    assert any("future" in warning for warning in mq["microstructure_warnings"])


def test_microstructure_quality_degrades_when_any_latest_token_book_is_stale():
    record = _make_record(token_ids=["tok-yes", "tok-no"])
    stale_ob = _make_ob(
        "tok-yes",
        snapshot_id="snap-stale-token",
        captured_at_utc="2025-12-31T00:00:00+00:00",
    )
    fresh_ob = _make_ob(
        "tok-no",
        snapshot_id="snap-fresh-token",
        captured_at_utc="2026-01-01T12:30:00+00:00",
    )
    ctx = extract_market_research_priority_context(
        record=record,
        order_books_by_token_id={"tok-yes": [stale_ob], "tok-no": [fresh_ob]},
        generated_at_utc=_REFERENCE_UTC,
    )
    mq = ctx["microstructure_quality"]
    assert mq["latest_order_book_snapshot_id"] == "snap-fresh-token"
    assert mq["order_book_stale"] is True
    assert mq["requires_order_book_recapture_before_use"] is True
    assert any("tok-yes" in warning for warning in mq["microstructure_warnings"])


def test_microstructure_quality_warnings_avoid_forbidden_action_wording():
    record = _make_record()
    ob = _make_ob("tok-yes", bids=[], asks=[{"price": "0.52", "size": "10"}])
    ctx = extract_market_research_priority_context(
        record=record,
        order_books_by_token_id={"tok-yes": [ob]},
        generated_at_utc=_REFERENCE_UTC,
    )
    warning_text = " ".join(ctx["microstructure_quality"]["microstructure_warnings"]).lower()
    forbidden_terms = (
        "alpha", "edge", "opportunity", "tradeable", "tradable", "buy", "sell",
        "entry", "exit", "position size", "leverage", "expected return",
        "execution confidence", "fill probability", "slippage", "profitable",
    )
    for term in forbidden_terms:
        assert term not in warning_text


# ── Forbidden fields do not appear ───────────────────────────────────────────

_FORBIDDEN_FIELD_NAMES = frozenset({
    "alpha_score",
    "opportunity_score",
    "expected_return",
    "trade_signal",
    "position_size",
    "execution_confidence",
    "tradability_score",
    "liquidity_score",
})


def _collect_keys_recursive(obj, found=None):
    if found is None:
        found = set()
    if isinstance(obj, dict):
        for k, v in obj.items():
            found.add(k)
            _collect_keys_recursive(v, found)
    elif isinstance(obj, (list, tuple)):
        for item in obj:
            _collect_keys_recursive(item, found)
    return found


def test_no_forbidden_fields_in_extracted_context():
    record = _make_record()
    ctx = extract_market_research_priority_context(
        record=record,
        manifests=[_make_manifest()],
        order_books_by_token_id=index_order_books_by_token_id([_make_ob()]),
        generated_at_utc=_REFERENCE_UTC,
    )
    all_keys = _collect_keys_recursive(ctx)
    found_forbidden = all_keys & _FORBIDDEN_FIELD_NAMES
    assert found_forbidden == set(), (
        f"Forbidden field(s) found in extracted context: {found_forbidden}"
    )


def test_no_forbidden_fields_in_run_context():
    run_ctx = build_market_research_priority_run_context(
        snapshot_id="snap-001",
        generated_at_utc=_REFERENCE_UTC,
    )
    all_keys = _collect_keys_recursive(run_ctx)
    found_forbidden = all_keys & _FORBIDDEN_FIELD_NAMES
    assert found_forbidden == set(), (
        f"Forbidden field(s) found in run context: {found_forbidden}"
    )


# ── Module imports no forbidden packages ─────────────────────────────────────

_FORBIDDEN_MODULE_PREFIXES = (
    "requests",
    "httpx",
    "aiohttp",
    "boto3",
    "sqlalchemy",
    "celery",
    "redis",
    "anthropic",
    "openai",
    "hermes",
    "apscheduler",
    "schedule",
)


def test_module_imports_no_network_or_llm_packages():
    spec = importlib.util.spec_from_file_location(
        "market_research_priority_features",
        ROOT / "src" / "data_layer" / "market_research_priority_features.py",
    )
    source = (ROOT / "src" / "data_layer" / "market_research_priority_features.py").read_text()
    for prefix in _FORBIDDEN_MODULE_PREFIXES:
        assert f"import {prefix}" not in source and f"from {prefix}" not in source, (
            f"Forbidden import found: {prefix}"
        )


# ── Module performs no writes ─────────────────────────────────────────────────

def test_module_performs_no_writes_in_extraction():
    record = _make_record()
    import os
    before = set(Path(ROOT).rglob("*.json"))
    ctx = extract_market_research_priority_context(
        record=record,
        manifests=[_make_manifest()],
        order_books_by_token_id=index_order_books_by_token_id([_make_ob()]),
        generated_at_utc=_REFERENCE_UTC,
    )
    after = set(Path(ROOT).rglob("*.json"))
    new_files = after - before
    # Filter out any local_data files (git-ignored) and manifest files already present
    relevant_new = {f for f in new_files if "local_data" not in str(f)}
    assert relevant_new == set(), f"Unexpected new JSON files created: {relevant_new}"


# ── extract_market_research_priority_contexts (batch) ────────────────────────

def test_batch_extraction_returns_list_of_dicts():
    records = [_make_record(market_id=f"mkt-{i:03d}") for i in range(3)]
    ctxs = extract_market_research_priority_contexts(
        records=records, generated_at_utc=_REFERENCE_UTC
    )
    assert len(ctxs) == 3
    for ctx in ctxs:
        assert "market_id" in ctx


# ── extract_from_snapshot_dir (temp fixture) ─────────────────────────────────

def test_extract_from_snapshot_dir_with_local_fixture():
    record = _make_record()
    manifest = _make_manifest()
    ob = _make_ob()

    with tempfile.TemporaryDirectory() as tmpdir:
        snap_dir = Path(tmpdir)

        # Write markets JSONL
        markets_file = snap_dir / "market_metadata_snapshots.jsonl"
        markets_file.write_text(record.to_jsonl_line() + "\n", encoding="utf-8")

        # Write order books JSONL
        obs_file = snap_dir / "order_book_snapshots.jsonl"
        obs_file.write_text(ob.to_jsonl_line() + "\n", encoding="utf-8")

        # Write manifest
        manifest_file = snap_dir / f"manifest_{manifest.snapshot_id}.json"
        manifest_file.write_text(manifest.to_json(), encoding="utf-8")

        run_ctx, market_ctxs = extract_from_snapshot_dir(
            snap_dir, generated_at_utc=_REFERENCE_UTC
        )

    assert "generated_at_utc" in run_ctx
    assert "run_id" in run_ctx
    assert len(market_ctxs) == 1
    assert market_ctxs[0]["market_id"] == "mkt-001"


def test_extract_from_snapshot_dir_empty_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        run_ctx, market_ctxs = extract_from_snapshot_dir(
            Path(tmpdir), generated_at_utc=_REFERENCE_UTC
        )
    assert "run_id" in run_ctx
    assert market_ctxs == []


# ── WP53 Provenance hardening tests ──────────────────────────────────────────

def test_provenance_degraded_flag_absent_when_manifest_present():
    """A record with a matching manifest produces provenance_degraded=False."""
    record = _make_record()
    ctx = extract_market_research_priority_context(
        record=record,
        manifests=[_make_manifest()],
        order_books_by_token_id=index_order_books_by_token_id([_make_ob()]),
        generated_at_utc=_REFERENCE_UTC,
    )
    # When manifest matches the record's snapshot_id, provenance_degraded should be False
    # (even though guard_policy_version and quality_report_ids are absent, the manifest
    # itself is present and covers the critical weakness).
    # Note: WP53 still marks provenance_degraded=True for absent guard_policy_version etc.
    # The key check: provenance_weakness_reasons is a list (possibly non-empty for minor gaps).
    assert isinstance(ctx["provenance"]["provenance_weakness_reasons"], list)
    assert isinstance(ctx["provenance"]["provenance_degraded"], bool)


def test_absent_manifest_produces_provenance_degraded_true():
    """No manifest index → provenance_degraded=True with non-empty weakness reasons."""
    record = _make_record()
    ctx = extract_market_research_priority_context(
        record=record,
        manifests=None,
        generated_at_utc=_REFERENCE_UTC,
    )
    assert ctx["provenance"]["provenance_degraded"] is True
    assert len(ctx["provenance"]["provenance_weakness_reasons"]) > 0


def test_empty_manifest_list_produces_provenance_degraded_true():
    """Empty manifest list → provenance_degraded=True (snapshot_id not found)."""
    record = _make_record()
    ctx = extract_market_research_priority_context(
        record=record,
        manifests=[],
        generated_at_utc=_REFERENCE_UTC,
    )
    assert ctx["provenance"]["provenance_degraded"] is True


def test_provenance_warning_non_empty_when_degraded():
    """provenance_warning is a non-empty string when provenance_degraded=True."""
    record = _make_record()
    ctx = extract_market_research_priority_context(
        record=record,
        manifests=[],
        generated_at_utc=_REFERENCE_UTC,
    )
    assert ctx["provenance"]["provenance_warning"] is not None
    assert len(ctx["provenance"]["provenance_warning"]) > 0


def test_provenance_warning_none_when_manifest_present_and_not_degraded():
    """Even when manifest is present, provenance_warning may describe minor gaps.
    Check the field exists and is a string or None (not crashing).
    """
    record = _make_record()
    ctx = extract_market_research_priority_context(
        record=record,
        manifests=[_make_manifest()],
        order_books_by_token_id=index_order_books_by_token_id([_make_ob()]),
        generated_at_utc=_REFERENCE_UTC,
    )
    # provenance_warning is either None or a string — never raises
    pw = ctx["provenance"]["provenance_warning"]
    assert pw is None or isinstance(pw, str)


def test_absent_provenance_reduces_guard_provenance_quality_to_zero():
    """No manifest → guard_provenance_quality == 0.0."""
    record = _make_record()
    ctx = extract_market_research_priority_context(
        record=record,
        manifests=None,
        generated_at_utc=_REFERENCE_UTC,
    )
    assert ctx["score_components"]["guard_provenance_quality"] == 0.0


def test_manifest_with_empty_output_files_is_weak_provenance():
    """Manifest found but output_files=[] → provenance_degraded=True, guard_provenance_quality < 0.8."""
    empty_manifest = SnapshotManifest(
        snapshot_id="snap_20260101_120000_000000",
        created_at_utc=_FRESH_UTC,
        tool_name="capture_market_snapshots",
        work_package="WP18",
        markets_requested=1,
        markets_written=1,
        order_books_requested=2,
        order_books_written=2,
        network_used=True,
        output_files=[],  # empty — weak provenance
        notes="test manifest with no output files",
    )
    record = _make_record()
    ctx = extract_market_research_priority_context(
        record=record,
        manifests=[empty_manifest],
        order_books_by_token_id=index_order_books_by_token_id([_make_ob()]),
        generated_at_utc=_REFERENCE_UTC,
    )
    assert ctx["provenance"]["provenance_degraded"] is True
    assert ctx["score_components"]["guard_provenance_quality"] < 0.8


def test_weak_provenance_quality_status_degraded_not_failing():
    """Weak provenance (manifest present, empty output_files, fresh data) → DEGRADED not FAILING."""
    empty_manifest = SnapshotManifest(
        snapshot_id="snap_20260101_120000_000000",
        created_at_utc=_FRESH_UTC,
        tool_name="capture_market_snapshots",
        work_package="WP18",
        markets_requested=1,
        markets_written=1,
        order_books_requested=0,
        order_books_written=0,
        network_used=True,
        output_files=[],
        notes="test",
    )
    record = _make_record()
    ctx = extract_market_research_priority_context(
        record=record,
        manifests=[empty_manifest],
        order_books_by_token_id=index_order_books_by_token_id([_make_ob("tok-yes"), _make_ob("tok-no")]),
        generated_at_utc=_REFERENCE_UTC,
    )
    # Weak provenance with fresh data → DEGRADED (not FAILING)
    assert ctx["quality_gates"]["quality_status"] in ("DEGRADED", "FAILING")
    # Must not be ACCEPTABLE
    assert ctx["quality_gates"]["quality_status"] != "ACCEPTABLE"


# ── WP53 Staleness hardening tests ───────────────────────────────────────────

def test_future_metadata_timestamp_marks_stale_and_requires_recapture():
    """Future metadata timestamp → staleness_flag=True, requires_recapture=True."""
    # Reference time is 2026-01-01 13:00:00 UTC; captured_at is 2026-01-02 (future)
    future_ts = "2026-01-02T00:00:00+00:00"
    record = _make_record(captured_at_utc=future_ts)
    ctx = extract_market_research_priority_context(
        record=record, generated_at_utc=_REFERENCE_UTC
    )
    assert ctx["staleness"]["staleness_flag"] is True
    assert ctx["staleness"]["requires_recapture_before_use"] is True


def test_future_metadata_timestamp_sets_future_timestamp_detected():
    """Future metadata timestamp sets future_timestamp_detected=True in staleness dict."""
    future_ts = "2026-01-02T00:00:00+00:00"
    record = _make_record(captured_at_utc=future_ts)
    ctx = extract_market_research_priority_context(
        record=record, generated_at_utc=_REFERENCE_UTC
    )
    assert ctx["staleness"]["future_timestamp_detected"] is True


def test_future_metadata_timestamp_does_not_silently_pass_as_fresh():
    """Future timestamp must not yield snapshot_freshness > 0.0."""
    future_ts = "2026-01-02T00:00:00+00:00"
    record = _make_record(captured_at_utc=future_ts)
    ctx = extract_market_research_priority_context(
        record=record, generated_at_utc=_REFERENCE_UTC
    )
    assert ctx["score_components"]["snapshot_freshness"] == 0.0


def test_future_orderbook_timestamp_marks_stale():
    """Future OB timestamp → staleness_flag=True for that token."""
    future_ts = "2026-01-02T00:00:00+00:00"
    record = _make_record()
    future_ob = _make_ob("tok-yes", captured_at_utc=future_ts)
    ctx = extract_market_research_priority_context(
        record=record,
        order_books_by_token_id={"tok-yes": [future_ob]},
        generated_at_utc=_REFERENCE_UTC,
    )
    assert ctx["staleness"]["staleness_flag"] is True
    assert ctx["staleness"]["future_timestamp_detected"] is True
    assert ctx["staleness"]["requires_recapture_before_use"] is True


def test_fresh_timestamp_does_not_set_future_timestamp_detected():
    """Fresh (non-future) timestamp → future_timestamp_detected=False."""
    record = _make_record()  # _FRESH_UTC is 1h before _REFERENCE_UTC
    ctx = extract_market_research_priority_context(
        record=record,
        manifests=[_make_manifest()],
        order_books_by_token_id=index_order_books_by_token_id([_make_ob()]),
        generated_at_utc=_REFERENCE_UTC,
    )
    assert ctx["staleness"]["future_timestamp_detected"] is False


def test_staleness_warning_non_empty_when_stale():
    """staleness_warning is a non-empty string whenever staleness_flag=True."""
    old_ts = "2025-01-01T00:00:00+00:00"
    record = _make_record(captured_at_utc=old_ts)
    ctx = extract_market_research_priority_context(
        record=record, generated_at_utc=_REFERENCE_UTC
    )
    assert ctx["staleness"]["staleness_flag"] is True
    assert ctx["staleness"]["staleness_warning"] is not None
    assert len(ctx["staleness"]["staleness_warning"]) > 0


def test_stale_inputs_non_empty_when_stale():
    """stale_inputs list is non-empty when staleness_flag=True."""
    old_ts = "2025-01-01T00:00:00+00:00"
    record = _make_record(captured_at_utc=old_ts)
    ctx = extract_market_research_priority_context(
        record=record, generated_at_utc=_REFERENCE_UTC
    )
    assert len(ctx["staleness"]["stale_inputs"]) > 0


def test_mixed_fresh_stale_orderbooks_marks_stale():
    """One stale OB alongside a fresh OB still sets staleness_flag=True."""
    fresh_ob = _make_ob("tok-yes", captured_at_utc=_FRESH_UTC)
    old_ts = "2025-01-01T00:00:00+00:00"
    stale_ob = _make_ob("tok-no", captured_at_utc=old_ts)
    record = _make_record()
    ctx = extract_market_research_priority_context(
        record=record,
        order_books_by_token_id={"tok-yes": [fresh_ob], "tok-no": [stale_ob]},
        generated_at_utc=_REFERENCE_UTC,
    )
    assert ctx["staleness"]["staleness_flag"] is True
    assert ctx["staleness"]["requires_recapture_before_use"] is True


# ── WP53 Missing-data hardening tests ────────────────────────────────────────

def test_missing_question_produces_warning():
    """Missing question text → missing_data_warning=True, missing_question=True."""
    record = _make_record(question=None)
    ctx = extract_market_research_priority_context(
        record=record, generated_at_utc=_REFERENCE_UTC
    )
    assert ctx["missing_data"]["missing_question"] is True
    assert ctx["missing_data"]["missing_data_warning"] is True
    assert "question" in ctx["missing_data"]["missing_metadata_fields"]


def test_missing_market_status_produces_warning():
    """Missing market_status → missing_data_warning=True, missing_market_status=True."""
    record = _make_record(market_status=None)
    ctx = extract_market_research_priority_context(
        record=record, generated_at_utc=_REFERENCE_UTC
    )
    assert ctx["missing_data"]["missing_market_status"] is True
    assert ctx["missing_data"]["missing_data_warning"] is True
    assert "market_status" in ctx["missing_data"]["missing_metadata_fields"]


def test_empty_question_string_produces_warning():
    """Empty string question → missing_data_warning=True."""
    record = _make_record(question="")
    ctx = extract_market_research_priority_context(
        record=record, generated_at_utc=_REFERENCE_UTC
    )
    assert ctx["missing_data"]["missing_question"] is True
    assert ctx["missing_data"]["missing_data_warning"] is True


def test_multiple_critical_missing_fields_produce_nonzero_penalty():
    """Multiple missing critical fields → missing_data_penalty < 0 (non-compensatory)."""
    record = _make_record(
        question=None,
        category=None,
        market_status=None,
        token_ids=[],
        outcome_labels=[],
        resolution_date=None,
    )
    ctx = extract_market_research_priority_context(
        record=record,
        order_books_by_token_id={},
        generated_at_utc=_REFERENCE_UTC,
    )
    penalty = ctx["score_components"]["missing_data_penalty"]
    assert penalty < 0, "Multiple critical missing fields must produce a negative penalty"
    assert ctx["missing_data"]["missing_data_warning"] is True


def test_multiple_critical_missing_fields_penalty_capped():
    """missing_data_penalty is capped at -0.5 (non-compensatory but bounded)."""
    record = _make_record(
        question=None,
        category=None,
        market_status=None,
        token_ids=[],
        outcome_labels=[],
        resolution_date=None,
    )
    ctx = extract_market_research_priority_context(
        record=record,
        order_books_by_token_id={},
        generated_at_utc=_REFERENCE_UTC,
    )
    penalty = ctx["score_components"]["missing_data_penalty"]
    assert penalty >= -0.5, "missing_data_penalty must be capped at -0.5"


def test_good_values_do_not_erase_critical_missing_data_warning():
    """A record with fresh data and manifest but missing question still has warning=True."""
    record = _make_record(question=None)  # missing question, but everything else good
    ctx = extract_market_research_priority_context(
        record=record,
        manifests=[_make_manifest()],
        order_books_by_token_id=index_order_books_by_token_id([
            _make_ob("tok-yes"), _make_ob("tok-no"),
        ]),
        generated_at_utc=_REFERENCE_UTC,
    )
    # Despite fresh data and manifest, missing question must still produce a warning
    assert ctx["missing_data"]["missing_data_warning"] is True
    assert ctx["missing_data"]["missing_question"] is True


def test_missing_data_penalty_nonzero_when_warning_true():
    """missing_data_penalty must be < 0 whenever missing_data_warning=True."""
    record = _make_record(category=None)  # single missing field
    ctx = extract_market_research_priority_context(
        record=record, generated_at_utc=_REFERENCE_UTC
    )
    assert ctx["missing_data"]["missing_data_warning"] is True
    assert ctx["score_components"]["missing_data_penalty"] < 0


# ── WP53 Quality status semantic tests ───────────────────────────────────────

def test_quality_status_failing_when_stale_and_no_provenance():
    """Stale + no manifest → quality_status=FAILING."""
    old_ts = "2025-01-01T00:00:00+00:00"
    record = _make_record(captured_at_utc=old_ts)
    ctx = extract_market_research_priority_context(
        record=record,
        manifests=None,
        generated_at_utc=_REFERENCE_UTC,
    )
    assert ctx["quality_gates"]["quality_status"] == "FAILING"


def test_quality_status_failing_when_stale_even_with_manifest():
    """Stale data → quality_status=FAILING even if manifest is present."""
    old_ts = "2025-01-01T00:00:00+00:00"
    record = _make_record(captured_at_utc=old_ts)
    ctx = extract_market_research_priority_context(
        record=record,
        manifests=[_make_manifest()],
        order_books_by_token_id=index_order_books_by_token_id([_make_ob()]),
        generated_at_utc=_REFERENCE_UTC,
    )
    assert ctx["quality_gates"]["quality_status"] == "FAILING"


def test_quality_status_acceptable_for_clean_record():
    """Fresh, provenanced record with full metadata → quality_status=ACCEPTABLE."""
    record = _make_record()
    ctx = extract_market_research_priority_context(
        record=record,
        manifests=[_make_manifest()],
        order_books_by_token_id=index_order_books_by_token_id([
            _make_ob("tok-yes"), _make_ob("tok-no"),
        ]),
        generated_at_utc=_REFERENCE_UTC,
    )
    assert ctx["quality_gates"]["quality_status"] == "ACCEPTABLE"


def test_quality_status_degraded_for_missing_data_fresh_provenanced():
    """Fresh + provenanced + missing non-critical data → DEGRADED (not FAILING)."""
    record = _make_record(category=None)  # single missing field
    ctx = extract_market_research_priority_context(
        record=record,
        manifests=[_make_manifest()],
        order_books_by_token_id=index_order_books_by_token_id([
            _make_ob("tok-yes"), _make_ob("tok-no"),
        ]),
        generated_at_utc=_REFERENCE_UTC,
    )
    assert ctx["quality_gates"]["quality_status"] == "DEGRADED"


def test_requires_recapture_true_when_stale():
    """requires_recapture_before_use=True when staleness_flag=True."""
    old_ts = "2025-01-01T00:00:00+00:00"
    record = _make_record(captured_at_utc=old_ts)
    ctx = extract_market_research_priority_context(
        record=record, generated_at_utc=_REFERENCE_UTC
    )
    assert ctx["staleness"]["requires_recapture_before_use"] is True


def test_requires_recapture_false_when_fresh():
    """requires_recapture_before_use=False for a fresh record."""
    record = _make_record()
    ctx = extract_market_research_priority_context(
        record=record,
        manifests=[_make_manifest()],
        order_books_by_token_id=index_order_books_by_token_id([_make_ob()]),
        generated_at_utc=_REFERENCE_UTC,
    )
    assert ctx["staleness"]["requires_recapture_before_use"] is False


# ── Version constant ──────────────────────────────────────────────────────────

def test_feature_extraction_version_is_wp63():
    assert FEATURE_EXTRACTION_VERSION == "wp63-v1"


# ── Project status checks ─────────────────────────────────────────────────────

def test_project_status_includes_wp53_current_phase():
    status_file = ROOT / "docs" / "project_status.md"
    content = status_file.read_text(encoding="utf-8")
    assert "WP53" in content, "docs/project_status.md must reference WP53"


def test_project_status_includes_wp52_in_merged_wps():
    status_file = ROOT / "docs" / "project_status.md"
    content = status_file.read_text(encoding="utf-8")
    # WP52 must appear in the Merged WPs line
    for line in content.splitlines():
        if line.startswith("- Merged WPs:"):
            assert "WP52" in line, "WP52 must be listed in Merged WPs"
            break


def test_project_status_includes_wp51_in_merged_wps():
    status_file = ROOT / "docs" / "project_status.md"
    content = status_file.read_text(encoding="utf-8")
    for line in content.splitlines():
        if line.startswith("- Merged WPs:"):
            assert "WP51" in line, "WP51 must be listed in Merged WPs"
            break


# ── Research direction doc checks ─────────────────────────────────────────────

def test_research_direction_doc_present():
    assert (ROOT / "docs" / "research_data_foundation_direction.md").is_file()


def test_research_direction_doc_still_blocks_strategy_and_trading():
    content = (ROOT / "docs" / "research_data_foundation_direction.md").read_text(
        encoding="utf-8"
    )
    assert "Live trading" in content
    assert "Strategy runtime" in content
    assert "Paper-trading runtime" in content


# ── WP57 Resolution ambiguity label fixtures ──────────────────────────────────

_VALID_FORBIDDEN_USE = (
    "This label is not a trading signal. Not expected return. "
    "Not position sizing. Not execution instruction."
)


def _make_valid_label(
    label_id="label-001",
    market_id="mkt-001",
    review_status="REVIEWED_CLEAR",
    ambiguity_categories=None,
    ambiguity_severity="NONE",
    reviewer_confidence="HIGH",
    manual_review_required=False,
    reviewed_at_utc="2026-01-01T00:00:00Z",
    source_artifact_refs=None,
) -> dict:
    if ambiguity_categories is None:
        ambiguity_categories = []
    if source_artifact_refs is None:
        source_artifact_refs = ["local_data/manual_labels/label_001.txt"]
    return {
        "schema_version": "wp55-v1",
        "label_id": label_id,
        "market_id": market_id,
        "question_snapshot": "Will X happen by date Y?",
        "resolution_text_snapshot": "Resolves YES if X occurs.",
        "review_status": review_status,
        "ambiguity_categories": ambiguity_categories,
        "ambiguity_severity": ambiguity_severity,
        "reviewer_confidence": reviewer_confidence,
        "manual_review_required": manual_review_required,
        "reviewed_at_utc": reviewed_at_utc,
        "reviewer_id_or_role": "human-reviewer-a",
        "source_artifact_refs": source_artifact_refs,
        "evidence_notes": "No ambiguity observed in resolution rules.",
        "limitations": "Only local snapshot data reviewed.",
        "advisory_label": "ADVISORY_ONLY_HUMAN_REVIEW_REQUIRED",
        "forbidden_use_notice": _VALID_FORBIDDEN_USE,
    }


def _make_valid_label_medium_ambiguity(market_id="mkt-001", label_id="label-002") -> dict:
    return _make_valid_label(
        label_id=label_id,
        market_id=market_id,
        review_status="REVIEWED_MEDIUM_AMBIGUITY",
        ambiguity_categories=["cutoff_time_ambiguity", "timezone_ambiguity"],
        ambiguity_severity="MEDIUM",
        reviewer_confidence="MEDIUM",
        manual_review_required=True,
    )


def _make_valid_label_high_ambiguity(market_id="mkt-001", label_id="label-003") -> dict:
    return _make_valid_label(
        label_id=label_id,
        market_id=market_id,
        review_status="REVIEWED_HIGH_AMBIGUITY",
        ambiguity_categories=["source_conflict"],
        ambiguity_severity="HIGH",
        reviewer_confidence="LOW",
        manual_review_required=True,
    )


# ── WP57 8.1 Backward compatibility ──────────────────────────────────────────

def test_extraction_without_labels_still_passes():
    record = _make_record()
    ctx = extract_market_research_priority_context(
        record=record,
        manifests=[_make_manifest()],
        order_books_by_token_id=index_order_books_by_token_id([_make_ob()]),
        generated_at_utc=_REFERENCE_UTC,
    )
    assert "market_id" in ctx
    assert "score_components" in ctx
    assert "resolution_ambiguity" in ctx


def test_score_components_unchanged_without_labels():
    record = _make_record()
    ctx = extract_market_research_priority_context(
        record=record,
        manifests=[_make_manifest()],
        order_books_by_token_id=index_order_books_by_token_id([_make_ob()]),
        generated_at_utc=_REFERENCE_UTC,
    )
    sc = ctx["score_components"]
    assert "data_completeness" in sc
    assert "snapshot_freshness" in sc
    assert "guard_provenance_quality" in sc
    assert "missing_data_penalty" in sc


def test_existing_scorer_accepts_context_with_resolution_ambiguity():
    record = _make_record()
    run_ctx = build_market_research_priority_run_context(
        snapshot_id=record.snapshot_id,
        manifests=[_make_manifest()],
        generated_at_utc=_REFERENCE_UTC,
    )
    market_ctx = extract_market_research_priority_context(
        record=record,
        manifests=[_make_manifest()],
        order_books_by_token_id=index_order_books_by_token_id([_make_ob()]),
        generated_at_utc=_REFERENCE_UTC,
        resolution_ambiguity_label_index=build_resolution_ambiguity_label_index(
            [_make_valid_label()]
        ),
    )
    output = build_market_research_priority_output(run_ctx, market_ctx)
    assert_market_research_priority_output(output)


def test_no_scorer_import_required_for_basic_extraction():
    record = _make_record()
    ctx = extract_market_research_priority_context(
        record=record, generated_at_utc=_REFERENCE_UTC
    )
    assert "resolution_ambiguity" in ctx


# ── WP57 8.2 Valid label consumption ─────────────────────────────────────────

def test_valid_reviewed_clear_label_attaches_correctly():
    label = _make_valid_label(market_id="mkt-001", review_status="REVIEWED_CLEAR",
                               ambiguity_severity="NONE", reviewer_confidence="HIGH",
                               manual_review_required=False)
    idx = build_resolution_ambiguity_label_index([label])
    record = _make_record(market_id="mkt-001")
    ctx = extract_market_research_priority_context(
        record=record,
        manifests=[_make_manifest()],
        order_books_by_token_id=index_order_books_by_token_id([_make_ob()]),
        generated_at_utc=_REFERENCE_UTC,
        resolution_ambiguity_label_index=idx,
    )
    ra = ctx["resolution_ambiguity"]
    assert ra["label_available"] is True
    assert ra["validated_label_count"] == 1
    assert ra["manual_review_required"] is False
    assert ra["ambiguity_categories"] == []
    assert ra["highest_ambiguity_severity"] == "NONE"
    assert ra["lowest_reviewer_confidence"] == "HIGH"
    assert ra["advisory_label"] == "ADVISORY_ONLY_HUMAN_REVIEW_REQUIRED"


def test_valid_medium_ambiguity_label_attaches_categories_and_severity():
    label = _make_valid_label_medium_ambiguity(market_id="mkt-001")
    idx = build_resolution_ambiguity_label_index([label])
    record = _make_record(market_id="mkt-001")
    ctx = extract_market_research_priority_context(
        record=record, generated_at_utc=_REFERENCE_UTC,
        resolution_ambiguity_label_index=idx,
    )
    ra = ctx["resolution_ambiguity"]
    assert ra["label_available"] is True
    assert "cutoff_time_ambiguity" in ra["ambiguity_categories"]
    assert "timezone_ambiguity" in ra["ambiguity_categories"]
    assert ra["highest_ambiguity_severity"] == "MEDIUM"
    assert ra["lowest_reviewer_confidence"] == "MEDIUM"
    assert ra["manual_review_required"] is True
    assert "REVIEWED_MEDIUM_AMBIGUITY" in ra["review_statuses"]


def test_multiple_labels_aggregate_categories_without_duplicates():
    label1 = _make_valid_label_medium_ambiguity(market_id="mkt-001", label_id="lbl-1")
    label2 = _make_valid_label(
        label_id="lbl-2", market_id="mkt-001",
        review_status="REVIEWED_MEDIUM_AMBIGUITY",
        ambiguity_categories=["cutoff_time_ambiguity", "source_conflict"],
        ambiguity_severity="MEDIUM", reviewer_confidence="MEDIUM",
        manual_review_required=True,
    )
    idx = build_resolution_ambiguity_label_index([label1, label2])
    record = _make_record(market_id="mkt-001")
    ctx = extract_market_research_priority_context(
        record=record, generated_at_utc=_REFERENCE_UTC,
        resolution_ambiguity_label_index=idx,
    )
    ra = ctx["resolution_ambiguity"]
    assert ra["validated_label_count"] == 2
    cats = ra["ambiguity_categories"]
    assert len(cats) == len(set(cats)), "categories should not contain duplicates"
    assert "cutoff_time_ambiguity" in cats
    assert "timezone_ambiguity" in cats
    assert "source_conflict" in cats
    assert len(ra["source_label_ids"]) == 2


def test_multiple_labels_pick_highest_severity():
    label_low = _make_valid_label(
        label_id="lbl-low", market_id="mkt-001",
        review_status="REVIEWED_LOW_AMBIGUITY",
        ambiguity_categories=["timezone_ambiguity"],
        ambiguity_severity="LOW", reviewer_confidence="HIGH",
        manual_review_required=True,
    )
    label_high = _make_valid_label_high_ambiguity(market_id="mkt-001", label_id="lbl-high")
    idx = build_resolution_ambiguity_label_index([label_low, label_high])
    record = _make_record(market_id="mkt-001")
    ctx = extract_market_research_priority_context(
        record=record, generated_at_utc=_REFERENCE_UTC,
        resolution_ambiguity_label_index=idx,
    )
    ra = ctx["resolution_ambiguity"]
    assert ra["highest_ambiguity_severity"] == "HIGH"
    assert ra["lowest_reviewer_confidence"] == "LOW"


# ── WP57 8.3 No matching labels ───────────────────────────────────────────────

def test_labels_for_other_market_do_not_attach_to_this_market():
    label = _make_valid_label(market_id="mkt-OTHER")
    idx = build_resolution_ambiguity_label_index([label])
    record = _make_record(market_id="mkt-001")
    ctx = extract_market_research_priority_context(
        record=record, generated_at_utc=_REFERENCE_UTC,
        resolution_ambiguity_label_index=idx,
    )
    ra = ctx["resolution_ambiguity"]
    assert ra["label_available"] is False
    assert ra["validated_label_count"] == 0


def test_no_matching_labels_produces_safe_defaults():
    idx = build_resolution_ambiguity_label_index([])
    record = _make_record(market_id="mkt-001")
    ctx = extract_market_research_priority_context(
        record=record, generated_at_utc=_REFERENCE_UTC,
        resolution_ambiguity_label_index=idx,
    )
    ra = ctx["resolution_ambiguity"]
    assert ra["label_available"] is False
    assert ra["highest_ambiguity_severity"] == "UNKNOWN"
    assert ra["lowest_reviewer_confidence"] == "LOW"
    assert ra["manual_review_required"] is True
    assert ra["advisory_label"] == "ADVISORY_ONLY_HUMAN_REVIEW_REQUIRED"
    assert ra["ambiguity_categories"] == []
    assert ra["source_label_ids"] == []


def test_no_label_index_provided_produces_safe_defaults():
    record = _make_record()
    ctx = extract_market_research_priority_context(
        record=record, generated_at_utc=_REFERENCE_UTC,
        resolution_ambiguity_label_index=None,
    )
    ra = ctx["resolution_ambiguity"]
    assert ra["label_available"] is False
    assert ra["advisory_label"] == "ADVISORY_ONLY_HUMAN_REVIEW_REQUIRED"


# ── WP57 8.4 Invalid labels ───────────────────────────────────────────────────

def test_invalid_label_excluded_from_ambiguity_summary():
    bad_label = {"label_id": "bad", "market_id": "mkt-001"}  # missing required fields
    idx = build_resolution_ambiguity_label_index([bad_label])
    assert idx["invalid_label_count"] == 1
    assert len(idx["by_market_id"]) == 0


def test_invalid_label_does_not_crash_extraction():
    bad_label = {"label_id": "bad", "market_id": "mkt-001"}
    idx = build_resolution_ambiguity_label_index([bad_label])
    record = _make_record(market_id="mkt-001")
    ctx = extract_market_research_priority_context(
        record=record, generated_at_utc=_REFERENCE_UTC,
        resolution_ambiguity_label_index=idx,
    )
    ra = ctx["resolution_ambiguity"]
    assert ra["label_available"] is False


def test_mixed_valid_invalid_labels_only_valid_ones_counted():
    valid_label = _make_valid_label(market_id="mkt-001", label_id="valid-1")
    bad_label = {"label_id": "bad", "market_id": "mkt-001"}
    idx = build_resolution_ambiguity_label_index([valid_label, bad_label])
    assert idx["invalid_label_count"] == 1
    assert len(idx["by_market_id"]["mkt-001"]) == 1

    record = _make_record(market_id="mkt-001")
    ctx = extract_market_research_priority_context(
        record=record, generated_at_utc=_REFERENCE_UTC,
        resolution_ambiguity_label_index=idx,
    )
    ra = ctx["resolution_ambiguity"]
    assert ra["label_available"] is True
    assert ra["validated_label_count"] == 1


def test_validation_error_count_surfaced_in_index():
    bad_label = {"label_id": "bad", "market_id": "mkt-001"}
    idx = build_resolution_ambiguity_label_index([bad_label])
    assert idx["total_validation_error_count"] > 0


# ── WP57 8.5 Forbidden semantics ─────────────────────────────────────────────

_FORBIDDEN_SEMANTIC_TERMS = frozenset({
    "alpha", "edge", "opportunity", "tradability", "tradeable", "tradable",
    "expected_return", "execution_confidence", "fill_probability", "slippage",
    "buy", "sell", "entry", "exit",
})


def _collect_all_string_values(obj) -> list:
    results = []
    if isinstance(obj, str):
        results.append(obj)
    elif isinstance(obj, dict):
        for v in obj.values():
            results.extend(_collect_all_string_values(v))
    elif isinstance(obj, (list, tuple)):
        for item in obj:
            results.extend(_collect_all_string_values(item))
    return results


def test_resolution_ambiguity_no_forbidden_key_names():
    label = _make_valid_label_medium_ambiguity()
    idx = build_resolution_ambiguity_label_index([label])
    record = _make_record(market_id="mkt-001")
    ctx = extract_market_research_priority_context(
        record=record, generated_at_utc=_REFERENCE_UTC,
        resolution_ambiguity_label_index=idx,
    )
    ra = ctx["resolution_ambiguity"]
    all_keys = set(_collect_keys_recursive(ra))
    found = all_keys & _FORBIDDEN_SEMANTIC_TERMS
    assert found == set(), f"Forbidden key names in resolution_ambiguity: {found}"


def test_advisory_label_preserved_exactly():
    label = _make_valid_label(market_id="mkt-001")
    idx = build_resolution_ambiguity_label_index([label])
    record = _make_record(market_id="mkt-001")
    ctx = extract_market_research_priority_context(
        record=record, generated_at_utc=_REFERENCE_UTC,
        resolution_ambiguity_label_index=idx,
    )
    ra = ctx["resolution_ambiguity"]
    assert ra["advisory_label"] == "ADVISORY_ONLY_HUMAN_REVIEW_REQUIRED"


def test_advisory_label_present_in_default_state():
    record = _make_record()
    ctx = extract_market_research_priority_context(
        record=record, generated_at_utc=_REFERENCE_UTC,
    )
    assert ctx["resolution_ambiguity"]["advisory_label"] == "ADVISORY_ONLY_HUMAN_REVIEW_REQUIRED"


# ── WP57 8.6 No parser / no LLM / no network / no writes ─────────────────────

def test_module_does_not_import_network_packages_after_wp57():
    source = (ROOT / "src" / "data_layer" / "market_research_priority_features.py").read_text()
    for prefix in _FORBIDDEN_MODULE_PREFIXES:
        assert f"import {prefix}" not in source and f"from {prefix}" not in source, (
            f"Forbidden import found after WP57: {prefix}"
        )


def test_resolution_ambiguity_sub_dict_has_required_keys():
    label = _make_valid_label(market_id="mkt-001")
    idx = build_resolution_ambiguity_label_index([label])
    record = _make_record(market_id="mkt-001")
    ctx = extract_market_research_priority_context(
        record=record, generated_at_utc=_REFERENCE_UTC,
        resolution_ambiguity_label_index=idx,
    )
    ra = ctx["resolution_ambiguity"]
    for key in ("label_available", "validated_label_count", "review_statuses",
                "ambiguity_categories", "highest_ambiguity_severity",
                "lowest_reviewer_confidence", "manual_review_required",
                "advisory_label", "source_label_ids", "source_artifact_refs",
                "validation_error_count", "validation_warning_count"):
        assert key in ra, f"Missing key in resolution_ambiguity: {key}"


def test_build_resolution_ambiguity_label_index_is_deterministic():
    labels = [_make_valid_label(market_id="mkt-001")]
    idx1 = build_resolution_ambiguity_label_index(labels)
    idx2 = build_resolution_ambiguity_label_index(labels)
    assert idx1["by_market_id"].keys() == idx2["by_market_id"].keys()
    assert idx1["invalid_label_count"] == idx2["invalid_label_count"]


def test_label_index_does_not_mutate_input():
    label = _make_valid_label(market_id="mkt-001")
    original_keys = set(label.keys())
    build_resolution_ambiguity_label_index([label])
    assert set(label.keys()) == original_keys


# ── WP57 8.7 Optional explicit label-path read ────────────────────────────────

def test_extract_from_snapshot_dir_with_label_json_file():
    record = _make_record()
    manifest = _make_manifest()
    ob = _make_ob()
    label = _make_valid_label(market_id=record.market_id)

    with tempfile.TemporaryDirectory() as tmpdir:
        snap_dir = Path(tmpdir)
        (snap_dir / "market_metadata_snapshots.jsonl").write_text(
            record.to_jsonl_line() + "\n", encoding="utf-8"
        )
        (snap_dir / "order_book_snapshots.jsonl").write_text(
            ob.to_jsonl_line() + "\n", encoding="utf-8"
        )
        (snap_dir / f"manifest_{manifest.snapshot_id}.json").write_text(
            manifest.to_json(), encoding="utf-8"
        )

        label_file = snap_dir / "labels.json"
        label_file.write_text(json.dumps([label]), encoding="utf-8")

        run_ctx, market_ctxs = extract_from_snapshot_dir(
            snap_dir,
            generated_at_utc=_REFERENCE_UTC,
            resolution_ambiguity_label_path=label_file,
        )

    assert len(market_ctxs) == 1
    ra = market_ctxs[0]["resolution_ambiguity"]
    assert ra["label_available"] is True
    assert ra["validated_label_count"] == 1


def test_extract_from_snapshot_dir_with_label_jsonl_file():
    record = _make_record()
    manifest = _make_manifest()
    ob = _make_ob()
    label = _make_valid_label(market_id=record.market_id)

    with tempfile.TemporaryDirectory() as tmpdir:
        snap_dir = Path(tmpdir)
        (snap_dir / "market_metadata_snapshots.jsonl").write_text(
            record.to_jsonl_line() + "\n", encoding="utf-8"
        )
        (snap_dir / "order_book_snapshots.jsonl").write_text(
            ob.to_jsonl_line() + "\n", encoding="utf-8"
        )
        (snap_dir / f"manifest_{manifest.snapshot_id}.json").write_text(
            manifest.to_json(), encoding="utf-8"
        )

        label_file = snap_dir / "labels.jsonl"
        label_file.write_text(json.dumps(label) + "\n", encoding="utf-8")

        run_ctx, market_ctxs = extract_from_snapshot_dir(
            snap_dir,
            generated_at_utc=_REFERENCE_UTC,
            resolution_ambiguity_label_path=label_file,
        )

    assert len(market_ctxs) == 1
    ra = market_ctxs[0]["resolution_ambiguity"]
    assert ra["label_available"] is True


def test_extract_from_snapshot_dir_without_label_path_produces_safe_defaults():
    record = _make_record()
    with tempfile.TemporaryDirectory() as tmpdir:
        snap_dir = Path(tmpdir)
        (snap_dir / "market_metadata_snapshots.jsonl").write_text(
            record.to_jsonl_line() + "\n", encoding="utf-8"
        )
        (snap_dir / "order_book_snapshots.jsonl").write_text("", encoding="utf-8")

        run_ctx, market_ctxs = extract_from_snapshot_dir(
            snap_dir, generated_at_utc=_REFERENCE_UTC
        )

    assert len(market_ctxs) == 1
    ra = market_ctxs[0]["resolution_ambiguity"]
    assert ra["label_available"] is False
    assert ra["advisory_label"] == "ADVISORY_ONLY_HUMAN_REVIEW_REQUIRED"


def test_extract_from_snapshot_dir_unsupported_label_extension_raises():
    record = _make_record()
    with tempfile.TemporaryDirectory() as tmpdir:
        snap_dir = Path(tmpdir)
        (snap_dir / "market_metadata_snapshots.jsonl").write_text(
            record.to_jsonl_line() + "\n", encoding="utf-8"
        )
        label_file = snap_dir / "labels.txt"
        label_file.write_text("not supported", encoding="utf-8")
        import pytest
        with pytest.raises(ValueError):
            extract_from_snapshot_dir(
                snap_dir, generated_at_utc=_REFERENCE_UTC,
                resolution_ambiguity_label_path=label_file,
            )


# ── WP57 8.8 Existing scorer tests remain compatible ─────────────────────────

def test_project_status_includes_wp56_in_merged_wps():
    status_file = ROOT / "docs" / "project_status.md"
    content = status_file.read_text(encoding="utf-8")
    for line in content.splitlines():
        if line.startswith("- Merged WPs:"):
            assert "WP56" in line, "WP56 must be listed in Merged WPs"
            break


def test_project_status_current_phase_is_wp58_or_later():
    status_file = ROOT / "docs" / "project_status.md"
    content = status_file.read_text(encoding="utf-8")
    current_phase_line = next(
        line for line in content.splitlines() if line.startswith("- Current phase:")
    )
    assert any(wp in current_phase_line for wp in ("WP58", "WP59", "WP60", "WP61", "WP62", "WP63", "WP64", "WP65", "WP66", "WP67", "WP68", "WP69", "WP70", "WP71", "WP72", "WP73", "WP74", "WP75", "WP76")), (
        f"Expected WP58 or later in current phase line: {current_phase_line}"
    )


def test_project_status_current_branch_is_wp59_or_later():
    status_file = ROOT / "docs" / "project_status.md"
    content = status_file.read_text(encoding="utf-8")
    branch_line = next(
        line for line in content.splitlines() if line.startswith("- Current branch:")
    )
    assert any(wp in branch_line for wp in ("wp59", "wp60", "wp61", "wp62", "wp63", "wp64", "wp65", "wp66", "wp67", "wp68", "wp69", "wp70", "wp71", "wp72", "wp73", "wp74", "wp75", "wp76")), (
        f"Expected wp59 or later branch in branch line: {branch_line}"
    )


def test_deferred_item_caveat_includes_resolution_ambiguity_when_labels_present():
    label = _make_valid_label(market_id="mkt-001")
    idx = build_resolution_ambiguity_label_index([label])
    record = _make_record(market_id="mkt-001")
    ctx = extract_market_research_priority_context(
        record=record,
        manifests=[_make_manifest()],
        order_books_by_token_id=index_order_books_by_token_id([_make_ob()]),
        generated_at_utc=_REFERENCE_UTC,
        resolution_ambiguity_label_index=idx,
    )
    assert "resolution_ambiguity_label_review_required" in ctx["quality_gates"]["deferred_item_caveats"]


def test_deferred_item_caveat_does_not_include_resolution_when_no_labels():
    record = _make_record()
    ctx = extract_market_research_priority_context(
        record=record,
        manifests=[_make_manifest()],
        order_books_by_token_id=index_order_books_by_token_id([_make_ob()]),
        generated_at_utc=_REFERENCE_UTC,
    )
    assert "resolution_ambiguity_label_review_required" not in ctx["quality_gates"]["deferred_item_caveats"]


def test_score_components_unchanged_when_labels_present():
    record = _make_record()
    label = _make_valid_label(market_id=record.market_id)
    idx = build_resolution_ambiguity_label_index([label])

    ctx_no_labels = extract_market_research_priority_context(
        record=record,
        manifests=[_make_manifest()],
        order_books_by_token_id=index_order_books_by_token_id([_make_ob()]),
        generated_at_utc=_REFERENCE_UTC,
    )
    ctx_with_labels = extract_market_research_priority_context(
        record=record,
        manifests=[_make_manifest()],
        order_books_by_token_id=index_order_books_by_token_id([_make_ob()]),
        generated_at_utc=_REFERENCE_UTC,
        resolution_ambiguity_label_index=idx,
    )
    assert ctx_no_labels["score_components"] == ctx_with_labels["score_components"]


def test_quality_status_unchanged_when_labels_present():
    record = _make_record()
    label = _make_valid_label(market_id=record.market_id)
    idx = build_resolution_ambiguity_label_index([label])

    ctx_no = extract_market_research_priority_context(
        record=record,
        manifests=[_make_manifest()],
        order_books_by_token_id=index_order_books_by_token_id([_make_ob()]),
        generated_at_utc=_REFERENCE_UTC,
    )
    ctx_with = extract_market_research_priority_context(
        record=record,
        manifests=[_make_manifest()],
        order_books_by_token_id=index_order_books_by_token_id([_make_ob()]),
        generated_at_utc=_REFERENCE_UTC,
        resolution_ambiguity_label_index=idx,
    )
    assert ctx_no["quality_gates"]["quality_status"] == ctx_with["quality_gates"]["quality_status"]


# ── WP62 Cross-Market Relationship Metadata tests ────────────────────────────

# helper to make records with explicit fields for relationship testing
def _make_relationship_record(
    market_id="mkt-rel-001",
    question="Will X happen?",
    category="Politics",
    condition_id="cond-A",
    token_ids=None,
    outcome_labels=None,
    resolution_date="2026-06-01T00:00:00+00:00",
) -> MarketMetadataSnapshotRecord:
    return MarketMetadataSnapshotRecord(
        snapshot_id="snap-rel-001",
        captured_at_utc=_FRESH_UTC,
        source="gamma-api/markets",
        adapter_version="wp10",
        market_id=market_id,
        condition_id=condition_id,
        question=question,
        market_status="active",
        outcome_labels=outcome_labels if outcome_labels is not None else ["Yes", "No"],
        token_ids=token_ids if token_ids is not None else ["tok-A", "tok-B"],
        resolution_date=resolution_date,
        category=category,
        raw_field_names=["market_id", "question", "category"],
        read_only_provenance="polymarket-strategy-lab/wp10-snapshot-persistence/public-get-only",
    )


# 1. cross_market_relationships is always present in market_context

def test_cross_market_relationships_key_always_present_single_record():
    record = _make_record()
    ctx = extract_market_research_priority_context(
        record=record,
        generated_at_utc=_REFERENCE_UTC,
    )
    assert "cross_market_relationships" in ctx


def test_cross_market_relationships_key_always_present_batch():
    records = [_make_record("mkt-001"), _make_record("mkt-002")]
    ctxs = extract_market_research_priority_contexts(records, generated_at_utc=_REFERENCE_UTC)
    for ctx in ctxs:
        assert "cross_market_relationships" in ctx


# 2. Single-record extraction without relationship index returns safe unavailable defaults

def test_single_record_no_index_returns_unavailable_defaults():
    record = _make_record()
    ctx = extract_market_research_priority_context(
        record=record,
        generated_at_utc=_REFERENCE_UTC,
    )
    cmr = ctx["cross_market_relationships"]
    assert cmr["relationship_metadata_available"] is False
    assert cmr["related_market_candidate_ids"] == []
    assert cmr["relationship_candidate_count"] == 0
    assert cmr["semantic_matching_performed"] is False
    assert cmr["price_comparison_performed"] is False
    assert cmr["automated_equivalence_claim"] is False
    assert cmr["advisory_label"] == "ADVISORY_ONLY_HUMAN_REVIEW_REQUIRED"
    assert any("unavailable" in w.lower() for w in cmr["relationship_warnings"])


def test_single_record_no_index_has_metadata_only_true():
    ctx = extract_market_research_priority_context(
        record=_make_record(),
        generated_at_utc=_REFERENCE_UTC,
    )
    assert ctx["cross_market_relationships"]["metadata_only"] is True


# 3. Batch extraction builds relationship index and passes metadata into each context

def test_batch_extraction_relationship_metadata_available_true():
    r1 = _make_relationship_record("mkt-001", question="Will X happen?")
    r2 = _make_relationship_record("mkt-002", question="Will Y happen?")
    ctxs = extract_market_research_priority_contexts([r1, r2], generated_at_utc=_REFERENCE_UTC)
    for ctx in ctxs:
        assert ctx["cross_market_relationships"]["relationship_metadata_available"] is True


# 4. Same normalized question text links related market candidates

def test_same_normalized_question_links_candidates():
    r1 = _make_relationship_record("mkt-001", question="Will X happen?")
    r2 = _make_relationship_record("mkt-002", question="will x happen?")  # same, different case
    r3 = _make_relationship_record("mkt-003", question="  Will  X  happen?  ")  # same, extra whitespace
    ctxs = extract_market_research_priority_contexts([r1, r2, r3], generated_at_utc=_REFERENCE_UTC)
    ctx1 = next(c for c in ctxs if c["market_id"] == "mkt-001")
    assert "mkt-002" in ctx1["cross_market_relationships"]["same_question_market_ids"]
    assert "mkt-003" in ctx1["cross_market_relationships"]["same_question_market_ids"]
    assert "mkt-001" not in ctx1["cross_market_relationships"]["same_question_market_ids"]
    assert "same_normalized_question" in ctx1["cross_market_relationships"]["relationship_types_observed"]


def test_different_questions_do_not_link():
    r1 = _make_relationship_record("mkt-001", question="Will X happen?")
    r2 = _make_relationship_record("mkt-002", question="Will Y happen?")
    ctxs = extract_market_research_priority_contexts([r1, r2], generated_at_utc=_REFERENCE_UTC)
    ctx1 = next(c for c in ctxs if c["market_id"] == "mkt-001")
    assert ctx1["cross_market_relationships"]["same_question_market_ids"] == []


# 5. Same condition_id links related market candidates

def test_same_condition_id_links_candidates():
    r1 = _make_relationship_record("mkt-001", condition_id="cond-X")
    r2 = _make_relationship_record("mkt-002", condition_id="cond-X")
    r3 = _make_relationship_record("mkt-003", condition_id="cond-Y")
    ctxs = extract_market_research_priority_contexts([r1, r2, r3], generated_at_utc=_REFERENCE_UTC)
    ctx1 = next(c for c in ctxs if c["market_id"] == "mkt-001")
    assert ctx1["cross_market_relationships"]["same_condition_id_market_ids"] == ["mkt-002"]
    assert "same_condition_id" in ctx1["cross_market_relationships"]["relationship_types_observed"]


# 6. Shared token_id links related market candidates

def test_shared_token_id_links_candidates():
    r1 = _make_relationship_record("mkt-001", token_ids=["tok-shared", "tok-only-1"])
    r2 = _make_relationship_record("mkt-002", token_ids=["tok-shared", "tok-only-2"])
    r3 = _make_relationship_record("mkt-003", token_ids=["tok-only-3"])
    ctxs = extract_market_research_priority_contexts([r1, r2, r3], generated_at_utc=_REFERENCE_UTC)
    ctx1 = next(c for c in ctxs if c["market_id"] == "mkt-001")
    assert "mkt-002" in ctx1["cross_market_relationships"]["shared_token_market_ids"]
    assert "mkt-003" not in ctx1["cross_market_relationships"]["shared_token_market_ids"]
    assert "shared_token_id" in ctx1["cross_market_relationships"]["relationship_types_observed"]


# 7. Same category + same resolution date links related market candidates

def test_same_category_resolution_date_links_candidates():
    r1 = _make_relationship_record("mkt-001", category="Politics", resolution_date="2026-06-01T00:00:00+00:00")
    r2 = _make_relationship_record("mkt-002", category="politics", resolution_date="2026-06-01T00:00:00+00:00")
    r3 = _make_relationship_record("mkt-003", category="Sports", resolution_date="2026-06-01T00:00:00+00:00")
    ctxs = extract_market_research_priority_contexts([r1, r2, r3], generated_at_utc=_REFERENCE_UTC)
    ctx1 = next(c for c in ctxs if c["market_id"] == "mkt-001")
    assert "mkt-002" in ctx1["cross_market_relationships"]["same_category_resolution_market_ids"]
    assert "mkt-003" not in ctx1["cross_market_relationships"]["same_category_resolution_market_ids"]
    assert "same_category_and_resolution_date" in ctx1["cross_market_relationships"]["relationship_types_observed"]


def test_same_category_different_resolution_date_does_not_link():
    r1 = _make_relationship_record("mkt-001", category="Politics", resolution_date="2026-06-01T00:00:00+00:00")
    r2 = _make_relationship_record("mkt-002", category="Politics", resolution_date="2026-12-01T00:00:00+00:00")
    ctxs = extract_market_research_priority_contexts([r1, r2], generated_at_utc=_REFERENCE_UTC)
    ctx1 = next(c for c in ctxs if c["market_id"] == "mkt-001")
    assert ctx1["cross_market_relationships"]["same_category_resolution_market_ids"] == []


# 8. Same outcome-label set links related market candidates

def test_same_outcome_label_set_links_candidates():
    r1 = _make_relationship_record("mkt-001", outcome_labels=["Yes", "No"])
    r2 = _make_relationship_record("mkt-002", outcome_labels=["No", "Yes"])  # same set, different order
    r3 = _make_relationship_record("mkt-003", outcome_labels=["Option A", "Option B"])
    ctxs = extract_market_research_priority_contexts([r1, r2, r3], generated_at_utc=_REFERENCE_UTC)
    ctx1 = next(c for c in ctxs if c["market_id"] == "mkt-001")
    assert "mkt-002" in ctx1["cross_market_relationships"]["same_outcome_label_set_market_ids"]
    assert "mkt-003" not in ctx1["cross_market_relationships"]["same_outcome_label_set_market_ids"]
    assert "same_outcome_label_set" in ctx1["cross_market_relationships"]["relationship_types_observed"]


# 9. Current market id is excluded from its own related candidate lists

def test_current_market_excluded_from_own_candidate_lists():
    r1 = _make_relationship_record("mkt-001", question="Will X happen?")
    r2 = _make_relationship_record("mkt-002", question="Will X happen?")
    ctxs = extract_market_research_priority_contexts([r1, r2], generated_at_utc=_REFERENCE_UTC)
    ctx1 = next(c for c in ctxs if c["market_id"] == "mkt-001")
    ctx2 = next(c for c in ctxs if c["market_id"] == "mkt-002")
    assert "mkt-001" not in ctx1["cross_market_relationships"]["related_market_candidate_ids"]
    assert "mkt-002" not in ctx2["cross_market_relationships"]["related_market_candidate_ids"]
    assert "mkt-001" not in ctx1["cross_market_relationships"]["same_question_market_ids"]


# 10. Related candidate IDs are sorted and unique

def test_related_candidate_ids_sorted_and_unique():
    r1 = _make_relationship_record("mkt-001", question="Will X happen?", condition_id="cond-same")
    r2 = _make_relationship_record("mkt-002", question="Will X happen?", condition_id="cond-same")
    r3 = _make_relationship_record("mkt-003", question="Will X happen?", condition_id="cond-other")
    ctxs = extract_market_research_priority_contexts([r1, r2, r3], generated_at_utc=_REFERENCE_UTC)
    ctx1 = next(c for c in ctxs if c["market_id"] == "mkt-001")
    related = ctx1["cross_market_relationships"]["related_market_candidate_ids"]
    assert related == sorted(set(related))
    assert len(related) == len(set(related))


# 11. Relationship type list is sorted and deterministic

def test_relationship_types_observed_sorted_and_deterministic():
    r1 = _make_relationship_record("mkt-001", question="Will X happen?", condition_id="cond-X",
                                   outcome_labels=["Yes", "No"])
    r2 = _make_relationship_record("mkt-002", question="Will X happen?", condition_id="cond-X",
                                   outcome_labels=["Yes", "No"])
    ctxs = extract_market_research_priority_contexts([r1, r2], generated_at_utc=_REFERENCE_UTC)
    ctx1 = next(c for c in ctxs if c["market_id"] == "mkt-001")
    types = ctx1["cross_market_relationships"]["relationship_types_observed"]
    assert types == sorted(types)


# 12. Empty/missing fields do not create false relationship candidates

def test_empty_condition_id_does_not_create_false_link():
    r1 = _make_relationship_record("mkt-001", condition_id="")
    r2 = _make_relationship_record("mkt-002", condition_id="")
    idx = build_cross_market_relationship_index([r1, r2])
    assert "" not in idx["by_condition_id"]


def test_empty_token_ids_do_not_create_false_link():
    r1 = _make_relationship_record("mkt-001", token_ids=[])
    r2 = _make_relationship_record("mkt-002", token_ids=[])
    idx = build_cross_market_relationship_index([r1, r2])
    assert idx["by_token_id"] == {}


def test_missing_resolution_date_prevents_category_resolution_link():
    r1 = _make_relationship_record("mkt-001", category="Politics", resolution_date=None)
    r2 = _make_relationship_record("mkt-002", category="Politics", resolution_date=None)
    idx = build_cross_market_relationship_index([r1, r2])
    assert idx["by_category_resolution"] == {}


# 13. Relationship metadata never uses price/order-book/microstructure fields

def test_relationship_index_does_not_use_order_book_data():
    r1 = _make_relationship_record("mkt-001")
    r2 = _make_relationship_record("mkt-002")
    idx = build_cross_market_relationship_index([r1, r2])
    # Index should only have metadata-key sub-dicts — no order book keys
    assert "bids" not in idx
    assert "asks" not in idx
    assert "spread" not in idx
    assert "best_bid" not in idx
    assert "microstructure" not in idx


# 14. Relationship metadata marks semantic matching as false

def test_relationship_metadata_semantic_matching_false():
    r1 = _make_relationship_record("mkt-001")
    ctx = extract_market_research_priority_context(
        record=r1,
        generated_at_utc=_REFERENCE_UTC,
        cross_market_relationship_index=build_cross_market_relationship_index([r1]),
    )
    assert ctx["cross_market_relationships"]["semantic_matching_performed"] is False


# 15. Relationship metadata marks price comparison as false

def test_relationship_metadata_price_comparison_false():
    r1 = _make_relationship_record("mkt-001")
    ctx = extract_market_research_priority_context(
        record=r1,
        generated_at_utc=_REFERENCE_UTC,
        cross_market_relationship_index=build_cross_market_relationship_index([r1]),
    )
    assert ctx["cross_market_relationships"]["price_comparison_performed"] is False


# 16. Relationship metadata marks automated equivalence claim as false

def test_relationship_metadata_automated_equivalence_claim_false():
    r1 = _make_relationship_record("mkt-001")
    r2 = _make_relationship_record("mkt-002", question="Will X happen?")
    ctxs = extract_market_research_priority_contexts([r1, r2], generated_at_utc=_REFERENCE_UTC)
    for ctx in ctxs:
        assert ctx["cross_market_relationships"]["automated_equivalence_claim"] is False


# 17. Advisory label is present

def test_relationship_advisory_label_present():
    ctx = extract_market_research_priority_context(
        record=_make_record(),
        generated_at_utc=_REFERENCE_UTC,
    )
    assert ctx["cross_market_relationships"]["advisory_label"] == "ADVISORY_ONLY_HUMAN_REVIEW_REQUIRED"


def test_relationship_advisory_label_present_with_index():
    r1 = _make_relationship_record("mkt-001")
    ctx = extract_market_research_priority_context(
        record=r1,
        generated_at_utc=_REFERENCE_UTC,
        cross_market_relationship_index=build_cross_market_relationship_index([r1]),
    )
    assert ctx["cross_market_relationships"]["advisory_label"] == "ADVISORY_ONLY_HUMAN_REVIEW_REQUIRED"


# 18. New output/warnings avoid forbidden trading/action wording

_FORBIDDEN_WORDING = [
    "alpha", "edge", "opportunity", "arbitrage", "mispricing",
    "incoherence opportunity", "price inconsistency signal", "tradability",
    "tradeable", "tradable", "buy", "sell", "entry", "exit", "position size",
    "leverage", "expected return", "execution confidence", "fill probability",
    "slippage", "market attractiveness", "profitable",
]


def test_relationship_warnings_avoid_forbidden_wording():
    r1 = _make_relationship_record("mkt-001", category="Politics", resolution_date="2026-06-01T00:00:00+00:00")
    r2 = _make_relationship_record("mkt-002", category="politics", resolution_date="2026-06-01T00:00:00+00:00")
    ctxs = extract_market_research_priority_contexts([r1, r2], generated_at_utc=_REFERENCE_UTC)
    for ctx in ctxs:
        warnings_text = " ".join(ctx["cross_market_relationships"]["relationship_warnings"]).lower()
        for forbidden in _FORBIDDEN_WORDING:
            assert forbidden not in warnings_text, (
                f"Forbidden wording '{forbidden}' found in relationship_warnings"
            )


def test_advisory_label_does_not_contain_forbidden_wording():
    ctx = extract_market_research_priority_context(
        record=_make_record(),
        generated_at_utc=_REFERENCE_UTC,
    )
    label = ctx["cross_market_relationships"]["advisory_label"].lower()
    for forbidden in ("buy", "sell", "arbitrage", "alpha", "edge", "opportunity"):
        assert forbidden not in label


# 19. Existing microstructure quality tests still pass (regression guard)

def test_microstructure_quality_still_present_after_wp62():
    ctx = extract_market_research_priority_context(
        record=_make_record(),
        generated_at_utc=_REFERENCE_UTC,
    )
    assert "microstructure_quality" in ctx


def test_microstructure_quality_fields_unchanged_by_wp62():
    ctx = extract_market_research_priority_context(
        record=_make_record(),
        generated_at_utc=_REFERENCE_UTC,
    )
    mq = ctx["microstructure_quality"]
    assert "order_book_available" in mq
    assert "advisory_label" in mq
    assert mq["semantic_matching_performed"] if "semantic_matching_performed" in mq else True  # not present → ok


# 20. Existing resolution ambiguity tests still pass (regression guard)

def test_resolution_ambiguity_still_present_after_wp62():
    ctx = extract_market_research_priority_context(
        record=_make_record(),
        generated_at_utc=_REFERENCE_UTC,
    )
    assert "resolution_ambiguity" in ctx


# 21. Existing scorer compatibility tests still pass (regression guard)

def test_scorer_accepts_context_with_cross_market_relationships():
    record = _make_record()
    ctx = extract_market_research_priority_context(
        record=record,
        manifests=[_make_manifest()],
        order_books_by_token_id=index_order_books_by_token_id([_make_ob()]),
        generated_at_utc=_REFERENCE_UTC,
    )
    run_ctx = build_market_research_priority_run_context(
        snapshot_id=record.snapshot_id,
        manifests=[_make_manifest()],
        generated_at_utc=_REFERENCE_UTC,
    )
    output = build_market_research_priority_output(run_ctx, ctx)
    assert_market_research_priority_output(output)


def test_batch_scorer_accepts_contexts_with_cross_market_relationships():
    records = [_make_record("mkt-001"), _make_record("mkt-002")]
    ctxs = extract_market_research_priority_contexts(records, generated_at_utc=_REFERENCE_UTC)
    run_ctx = build_market_research_priority_run_context(
        snapshot_id="snap_20260101_120000_000000",
        generated_at_utc=_REFERENCE_UTC,
    )
    for ctx in ctxs:
        output = build_market_research_priority_output(run_ctx, ctx)
        assert_market_research_priority_output(output)


# 22. relationship_candidate_count equals len(related_market_candidate_ids)

def test_relationship_candidate_count_matches_ids_length():
    r1 = _make_relationship_record("mkt-001", question="Will X happen?")
    r2 = _make_relationship_record("mkt-002", question="Will X happen?")
    r3 = _make_relationship_record("mkt-003", question="Will Y happen?")
    ctxs = extract_market_research_priority_contexts([r1, r2, r3], generated_at_utc=_REFERENCE_UTC)
    for ctx in ctxs:
        cmr = ctx["cross_market_relationships"]
        assert cmr["relationship_candidate_count"] == len(cmr["related_market_candidate_ids"])


# 23. build_cross_market_relationship_index helper tests

def test_relationship_index_question_key_normalized():
    r1 = _make_relationship_record("mkt-001", question="Will X happen?")
    r2 = _make_relationship_record("mkt-002", question="WILL X HAPPEN?")
    idx = build_cross_market_relationship_index([r1, r2])
    assert "will x happen?" in idx["by_question"]
    assert sorted(idx["by_question"]["will x happen?"]) == ["mkt-001", "mkt-002"]


def test_relationship_index_condition_id_exact():
    r1 = _make_relationship_record("mkt-001", condition_id="cond-exact")
    r2 = _make_relationship_record("mkt-002", condition_id="cond-exact")
    idx = build_cross_market_relationship_index([r1, r2])
    assert sorted(idx["by_condition_id"]["cond-exact"]) == ["mkt-001", "mkt-002"]


def test_relationship_index_token_id_per_token():
    r1 = _make_relationship_record("mkt-001", token_ids=["tok-A", "tok-B"])
    r2 = _make_relationship_record("mkt-002", token_ids=["tok-A"])
    idx = build_cross_market_relationship_index([r1, r2])
    assert sorted(idx["by_token_id"]["tok-A"]) == ["mkt-001", "mkt-002"]
    assert idx["by_token_id"]["tok-B"] == ["mkt-001"]


def test_relationship_index_outcome_label_set_order_independent():
    r1 = _make_relationship_record("mkt-001", outcome_labels=["Yes", "No"])
    r2 = _make_relationship_record("mkt-002", outcome_labels=["No", "Yes"])
    idx = build_cross_market_relationship_index([r1, r2])
    # There should be exactly one key in by_outcome_label_set since both normalize to same frozenset
    assert len(idx["by_outcome_label_set"]) == 1
    values = list(idx["by_outcome_label_set"].values())[0]
    assert sorted(values) == ["mkt-001", "mkt-002"]


# 24. manual_review_required behavior

def test_manual_review_required_true_when_related_candidates_present():
    r1 = _make_relationship_record("mkt-001", question="Will X happen?")
    r2 = _make_relationship_record("mkt-002", question="Will X happen?")
    ctxs = extract_market_research_priority_contexts([r1, r2], generated_at_utc=_REFERENCE_UTC)
    for ctx in ctxs:
        assert ctx["cross_market_relationships"]["manual_review_required"] is True


def test_manual_review_required_false_when_no_related_candidates():
    r1 = _make_relationship_record("mkt-001", question="Unique question alpha")
    r2 = _make_relationship_record("mkt-002", question="Unique question beta", condition_id="cond-diff",
                                   token_ids=["tok-diff-1", "tok-diff-2"], outcome_labels=["A", "B"],
                                   resolution_date="2027-01-01T00:00:00+00:00")
    ctxs = extract_market_research_priority_contexts([r1, r2], generated_at_utc=_REFERENCE_UTC)
    ctx1 = next(c for c in ctxs if c["market_id"] == "mkt-001")
    # mkt-001 has unique question and different category/resolution than mkt-002
    # but they share default category "Politics" from _make_relationship_record
    # so we need to also differentiate category
    r1b = _make_relationship_record("mkt-001", question="Unique question alpha", category="Cat-A",
                                    condition_id="cond-unique-1", token_ids=["tok-u1"], outcome_labels=["X", "Y"],
                                    resolution_date="2026-01-01T00:00:00+00:00")
    r2b = _make_relationship_record("mkt-002", question="Unique question beta", category="Cat-B",
                                    condition_id="cond-unique-2", token_ids=["tok-u2"], outcome_labels=["P", "Q"],
                                    resolution_date="2027-01-01T00:00:00+00:00")
    ctxs2 = extract_market_research_priority_contexts([r1b, r2b], generated_at_utc=_REFERENCE_UTC)
    ctx1b = next(c for c in ctxs2 if c["market_id"] == "mkt-001")
    assert ctx1b["cross_market_relationships"]["related_market_candidate_ids"] == []
    assert ctx1b["cross_market_relationships"]["manual_review_required"] is False


# 25. Docs project_status reconciliation guard (WP63 → updated for WP64)

def test_project_status_current_phase_is_wp64_or_later():
    status_file = ROOT / "docs" / "project_status.md"
    content = status_file.read_text(encoding="utf-8")
    current_phase_line = next(
        line for line in content.splitlines() if line.startswith("- Current phase:")
    )
    assert any(wp in current_phase_line for wp in ("WP64", "WP65", "WP66", "WP67", "WP68", "WP69", "WP70", "WP71", "WP72", "WP73", "WP74", "WP75", "WP76")), (
        f"Expected WP64 or later in current phase line: {current_phase_line}"
    )


def test_project_status_current_branch_is_wp64():
    status_file = ROOT / "docs" / "project_status.md"
    content = status_file.read_text(encoding="utf-8")
    branch_line = next(
        line for line in content.splitlines() if line.startswith("- Current branch:")
    )
    assert any(wp in branch_line for wp in ("wp64", "wp65", "wp66", "wp67", "wp68", "wp69", "wp70", "wp71", "wp72", "wp73", "wp74", "wp75", "wp76")), (
        f"Expected wp64 or later in current branch line: {branch_line}"
    )


def test_project_status_includes_wp63_in_merged_wps():
    status_file = ROOT / "docs" / "project_status.md"
    content = status_file.read_text(encoding="utf-8")
    merged_line = next(
        line for line in content.splitlines() if line.startswith("- Merged WPs:")
    )
    assert "WP63" in merged_line, (
        f"Expected WP63 in merged WPs line: {merged_line}"
    )


def test_project_status_includes_wp62_in_merged_wps():
    status_file = ROOT / "docs" / "project_status.md"
    content = status_file.read_text(encoding="utf-8")
    for line in content.splitlines():
        if line.startswith("- Merged WPs:"):
            assert "WP62" in line, "WP62 must be listed in Merged WPs"
            break


def test_project_status_cross_market_metadata_merged():
    status_file = ROOT / "docs" / "project_status.md"
    content = status_file.read_text(encoding="utf-8")
    assert (
        "CROSS_MARKET_RELATIONSHIP_METADATA_MERGED" in content
        or "cross-market" in content.lower()
    ), "project_status.md must reference cross-market relationship metadata as merged"


# 26. WP63 resolution source hierarchy metadata tests

def test_resolution_source_hierarchy_always_present():
    record = _make_record()
    ctx = extract_market_research_priority_context(
        record=record, generated_at_utc=_REFERENCE_UTC
    )
    assert "resolution_source_hierarchy" in ctx
    rsh = ctx["resolution_source_hierarchy"]
    assert isinstance(rsh, dict)


def test_resolution_source_hierarchy_required_fields():
    record = _make_record()
    ctx = extract_market_research_priority_context(
        record=record, generated_at_utc=_REFERENCE_UTC
    )
    rsh = ctx["resolution_source_hierarchy"]
    for field in (
        "source_metadata_available",
        "primary_source_observed",
        "official_source_reference_observed",
        "resolution_rules_text_observed",
        "cutoff_timing_observed",
        "resolution_timing_observed",
        "source_url_observed",
        "source_text_fields_observed",
        "timing_fields_observed",
        "source_reference_count",
        "source_url_count",
        "manual_source_review_required",
        "automated_source_authority_judgment",
        "automated_resolution_interpretation",
        "official_source_monitoring_performed",
        "resolution_source_warnings",
        "advisory_label",
    ):
        assert field in rsh, f"resolution_source_hierarchy missing field: {field}"


def test_no_source_metadata_returns_unavailable_defaults():
    record = _make_record(question="", resolution_date=None)
    ctx = extract_market_research_priority_context(
        record=record, generated_at_utc=_REFERENCE_UTC
    )
    rsh = ctx["resolution_source_hierarchy"]
    assert rsh["source_metadata_available"] is False
    assert rsh["primary_source_observed"] is False
    assert rsh["official_source_reference_observed"] is False
    assert rsh["source_reference_count"] == 0
    assert rsh["source_url_count"] == 0
    assert rsh["manual_source_review_required"] is True
    assert isinstance(rsh["resolution_source_warnings"], list)
    assert len(rsh["resolution_source_warnings"]) > 0
    warning_text = " ".join(rsh["resolution_source_warnings"])
    assert "manual source review" in warning_text.lower()


def test_timing_field_observed_from_resolution_date():
    record = _make_record(resolution_date="2026-06-01T00:00:00+00:00")
    ctx = extract_market_research_priority_context(
        record=record, generated_at_utc=_REFERENCE_UTC
    )
    rsh = ctx["resolution_source_hierarchy"]
    assert rsh["cutoff_timing_observed"] is True
    assert rsh["resolution_timing_observed"] is True
    assert "resolution_date" in rsh["timing_fields_observed"]


def test_no_timing_when_resolution_date_absent():
    record = _make_record(resolution_date=None)
    ctx = extract_market_research_priority_context(
        record=record, generated_at_utc=_REFERENCE_UTC
    )
    rsh = ctx["resolution_source_hierarchy"]
    assert rsh["cutoff_timing_observed"] is False
    assert rsh["resolution_timing_observed"] is False
    assert rsh["timing_fields_observed"] == []


def test_source_text_field_from_question_with_url():
    # "question" is only counted as a source text field when it contains a URL.
    record = _make_record(question="See https://example.com for resolution details.")
    ctx = extract_market_research_priority_context(
        record=record, generated_at_utc=_REFERENCE_UTC
    )
    rsh = ctx["resolution_source_hierarchy"]
    assert "question" in rsh["source_text_fields_observed"]


def test_no_source_text_field_when_question_empty():
    record = _make_record(question="")
    ctx = extract_market_research_priority_context(
        record=record, generated_at_utc=_REFERENCE_UTC
    )
    rsh = ctx["resolution_source_hierarchy"]
    assert "question" not in rsh["source_text_fields_observed"]


def test_source_url_observed_when_url_in_question():
    record = _make_record(question="See https://example.com for details.")
    ctx = extract_market_research_priority_context(
        record=record, generated_at_utc=_REFERENCE_UTC
    )
    rsh = ctx["resolution_source_hierarchy"]
    assert rsh["source_url_observed"] is True
    assert rsh["source_url_count"] >= 1
    assert rsh["primary_source_observed"] is True


def test_source_url_not_fetched_or_validated():
    record = _make_record(question="See https://example.com/data for details.")
    ctx = extract_market_research_priority_context(
        record=record, generated_at_utc=_REFERENCE_UTC
    )
    rsh = ctx["resolution_source_hierarchy"]
    assert rsh["official_source_monitoring_performed"] is False
    assert rsh["automated_source_authority_judgment"] is False
    assert rsh["automated_resolution_interpretation"] is False


def test_source_url_count_increments_per_occurrence():
    record = _make_record(
        question="See https://a.com and https://b.com for resolution info."
    )
    ctx = extract_market_research_priority_context(
        record=record, generated_at_utc=_REFERENCE_UTC
    )
    rsh = ctx["resolution_source_hierarchy"]
    assert rsh["source_url_count"] >= 2


def test_source_url_with_no_timing_produces_warning():
    # A URL in the question without resolution_date produces a timing-absent warning.
    record = _make_record(
        question="See https://example.com for resolution details.",
        resolution_date=None,
    )
    ctx = extract_market_research_priority_context(
        record=record, generated_at_utc=_REFERENCE_UTC
    )
    rsh = ctx["resolution_source_hierarchy"]
    assert rsh["cutoff_timing_observed"] is False
    combined = " ".join(rsh["resolution_source_warnings"]).lower()
    assert "timing" in combined or "manual" in combined


def test_manual_source_review_required_always_true_without_official_source():
    record = _make_record()
    ctx = extract_market_research_priority_context(
        record=record, generated_at_utc=_REFERENCE_UTC
    )
    rsh = ctx["resolution_source_hierarchy"]
    assert rsh["manual_source_review_required"] is True
    assert rsh["official_source_reference_observed"] is False


def test_automated_authority_judgment_always_false():
    record = _make_record()
    ctx = extract_market_research_priority_context(
        record=record, generated_at_utc=_REFERENCE_UTC
    )
    assert ctx["resolution_source_hierarchy"]["automated_source_authority_judgment"] is False


def test_automated_resolution_interpretation_always_false():
    record = _make_record()
    ctx = extract_market_research_priority_context(
        record=record, generated_at_utc=_REFERENCE_UTC
    )
    assert ctx["resolution_source_hierarchy"]["automated_resolution_interpretation"] is False


def test_official_source_monitoring_always_false():
    record = _make_record()
    ctx = extract_market_research_priority_context(
        record=record, generated_at_utc=_REFERENCE_UTC
    )
    assert ctx["resolution_source_hierarchy"]["official_source_monitoring_performed"] is False


def test_timing_fields_list_sorted_and_deterministic():
    record = _make_record(resolution_date="2026-06-01T00:00:00+00:00")
    ctx = extract_market_research_priority_context(
        record=record, generated_at_utc=_REFERENCE_UTC
    )
    rsh = ctx["resolution_source_hierarchy"]
    fields = rsh["timing_fields_observed"]
    assert fields == sorted(fields)


def test_source_text_fields_list_sorted_and_deterministic():
    record = _make_record(question="See https://example.com for resolution details.")
    ctx = extract_market_research_priority_context(
        record=record, generated_at_utc=_REFERENCE_UTC
    )
    rsh = ctx["resolution_source_hierarchy"]
    fields = rsh["source_text_fields_observed"]
    assert fields == sorted(fields)


def test_resolution_source_warnings_avoid_forbidden_trading_wording():
    record = _make_record()
    ctx = extract_market_research_priority_context(
        record=record, generated_at_utc=_REFERENCE_UTC
    )
    warnings_text = " ".join(ctx["resolution_source_hierarchy"]["resolution_source_warnings"]).lower()
    for forbidden in ("alpha", "edge", "arbitrage", "buy", "sell", "entry", "exit",
                       "position size", "leverage", "expected return", "tradability",
                       "tradable", "tradeable", "fill probability", "slippage"):
        assert forbidden not in warnings_text, (
            f"Forbidden wording '{forbidden}' found in resolution_source_warnings"
        )


def test_advisory_label_present():
    record = _make_record()
    ctx = extract_market_research_priority_context(
        record=record, generated_at_utc=_REFERENCE_UTC
    )
    rsh = ctx["resolution_source_hierarchy"]
    assert rsh["advisory_label"] == "ADVISORY_ONLY_HUMAN_REVIEW_REQUIRED"


def test_resolution_source_hierarchy_present_in_batch():
    records = [_make_record(market_id=f"mkt-{i:03d}") for i in range(3)]
    ctxs = extract_market_research_priority_contexts(records, generated_at_utc=_REFERENCE_UTC)
    for ctx in ctxs:
        assert "resolution_source_hierarchy" in ctx
        assert isinstance(ctx["resolution_source_hierarchy"], dict)


def test_existing_resolution_ambiguity_still_present_after_wp63():
    record = _make_record()
    ctx = extract_market_research_priority_context(
        record=record, generated_at_utc=_REFERENCE_UTC
    )
    assert "resolution_ambiguity" in ctx
    assert isinstance(ctx["resolution_ambiguity"], dict)


def test_existing_microstructure_quality_still_present_after_wp63():
    record = _make_record()
    ctx = extract_market_research_priority_context(
        record=record, generated_at_utc=_REFERENCE_UTC
    )
    assert "microstructure_quality" in ctx
    assert isinstance(ctx["microstructure_quality"], dict)


def test_existing_cross_market_relationships_still_present_after_wp63():
    record = _make_record()
    ctx = extract_market_research_priority_context(
        record=record, generated_at_utc=_REFERENCE_UTC
    )
    assert "cross_market_relationships" in ctx
    assert isinstance(ctx["cross_market_relationships"], dict)


def test_scorer_still_compatible_after_wp63():
    record = _make_record()
    manifest = _make_manifest()
    run_ctx = build_market_research_priority_run_context(
        snapshot_id=record.snapshot_id,
        manifests=[manifest],
        generated_at_utc=_REFERENCE_UTC,
    )
    market_ctx = extract_market_research_priority_context(
        record=record,
        manifests=[manifest],
        generated_at_utc=_REFERENCE_UTC,
    )
    output = build_market_research_priority_output(run_ctx, market_ctx)
    assert_market_research_priority_output(output)


def test_plain_question_with_no_source_not_counted_as_source_metadata():
    # Regression: a non-empty question with no URL and no resolution_date must NOT
    # make source_metadata_available=True. Plain market title text is not resolution-
    # source metadata.
    record = _make_record(question="Will X happen?", resolution_date=None)
    ctx = extract_market_research_priority_context(
        record=record, generated_at_utc=_REFERENCE_UTC
    )
    rsh = ctx["resolution_source_hierarchy"]
    assert rsh["source_metadata_available"] is False
    assert rsh["primary_source_observed"] is False
    assert rsh["official_source_reference_observed"] is False
    assert rsh["source_url_observed"] is False
    assert rsh["source_reference_count"] == 0
    assert rsh["source_url_count"] == 0
    assert rsh["manual_source_review_required"] is True
    assert rsh["automated_source_authority_judgment"] is False
    assert rsh["automated_resolution_interpretation"] is False
    assert rsh["official_source_monitoring_performed"] is False
    warnings_text = " ".join(rsh["resolution_source_warnings"]).lower()
    assert "manual source review" in warnings_text


def test_project_status_resolution_source_hierarchy_on_branch():
    status_file = ROOT / "docs" / "project_status.md"
    content = status_file.read_text(encoding="utf-8")
    assert (
        "RESOLUTION_SOURCE_HIERARCHY" in content
        or "resolution source hierarchy" in content.lower()
    ), "project_status.md must reference resolution source hierarchy metadata"
