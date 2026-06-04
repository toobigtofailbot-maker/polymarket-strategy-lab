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


# ── Project status checks ─────────────────────────────────────────────────────

def test_project_status_includes_wp51_current_phase():
    status_file = ROOT / "docs" / "project_status.md"
    content = status_file.read_text(encoding="utf-8")
    assert "WP51" in content, "docs/project_status.md must reference WP51"


def test_project_status_includes_wp50_in_merged_wps():
    status_file = ROOT / "docs" / "project_status.md"
    content = status_file.read_text(encoding="utf-8")
    assert "WP50" in content
    # WP50 must appear in the Merged WPs line
    for line in content.splitlines():
        if line.startswith("- Merged WPs:"):
            assert "WP50" in line, "WP50 must be listed in Merged WPs"
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
