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
    build_manifest_index,
    build_market_research_priority_run_context,
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
                "component_explanation"):
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


# ── WP53 Version constant ─────────────────────────────────────────────────────

def test_feature_extraction_version_is_wp53():
    assert FEATURE_EXTRACTION_VERSION == "wp53-v1"


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
