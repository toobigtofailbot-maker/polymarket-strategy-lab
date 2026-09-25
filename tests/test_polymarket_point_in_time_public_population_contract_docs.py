"""Focused docs tests for the WP164 public-population canonical contract."""

from __future__ import annotations

import pathlib
import re


REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
CONTRACT = REPO_ROOT / "docs" / "polymarket_point_in_time_public_population_contract.md"
MODULE = (
    REPO_ROOT
    / "src"
    / "data_layer"
    / "point_in_time_market_research"
    / "polymarket_public_population.py"
)


def _contract() -> str:
    return CONTRACT.read_text(encoding="utf-8")


def _flat(text: str) -> str:
    return re.sub(r"\s+", " ", text)


def test_contract_document_exists():
    assert CONTRACT.is_file()


def test_label_and_posture_are_exact():
    text = _contract()
    assert "POLYMARKET_REAL_PUBLIC_INITIAL_POINT_IN_TIME_POPULATION" in text
    assert "EXPLICIT_NETWORK_GET_ONLY_BOUNDED_INITIAL_SEED_NO_TRADING_AUTHORITY" in text
    assert (
        "src/data_layer/point_in_time_market_research/polymarket_public_population.py"
        in text
    )


def test_endpoint_basis_and_get_only_boundary_are_documented():
    text = _flat(_contract())
    assert "https://gamma-api.polymarket.com" in text
    assert "https://clob.polymarket.com" in text
    assert "GET /markets" in text
    assert "GET /book" in text
    assert "no-authentication" in text
    assert "get_markets" in text and "get_order_book_snapshot" in text
    assert "POST /books" in text  # documented as out of scope


def test_local_guard_remains_runtime_authority():
    text = _flat(_contract())
    assert "default_polling_policy()" in text
    assert "RateLimitGuard" in text
    assert "sole runtime request authority" in text
    assert "never fabricates elapsed guard time" in text
    assert "native monotonic clock" in text
    assert "only an upper bound" in text
    assert "network_used` is truthful" in text


def test_initial_seed_and_empty_store_requirement_documented():
    text = _flat(_contract())
    assert "INITIAL SEED only" in text
    assert "record store to be empty" in text
    assert "POPULATION_RECORD_STORE_NOT_EMPTY" in text
    assert "PRIMARY_ASSERTION" in text
    assert "NORMALIZED_ACCEPTED" in text


def test_public_api_symbols_are_documented():
    text = _contract()
    for symbol in (
        "POLYMARKET_PUBLIC_POPULATION_LABEL",
        "POLYMARKET_PUBLIC_POPULATION_POSTURE",
        "POLYMARKET_PUBLIC_POPULATION_STATUSES",
        "POLYMARKET_PUBLIC_POPULATION_ERROR_CODES",
        "PolymarketPublicPopulationConfig",
        "PolymarketPublicPopulationResult",
        "populate_initial_polymarket_public_data",
        "recover_initial_polymarket_public_registration",
    ):
        assert symbol in text


def test_records_first_then_registration_ordering_documented():
    text = _flat(_contract())
    assert "records first, reference second" in text
    assert "append_point_in_time_records" in text
    assert "persist_validated_record_batch_snapshot" in text
    assert "POPULATION_RECORDS_PERSISTED_REGISTRATION_FAILED" in text
    assert "EVERY registration failure mode" in text
    assert "raised registration exception is contained" in text
    assert "raw adapter object is never dereferenced" in text
    assert "DATASET_PERSISTENCE_ADAPTER_ERROR_CODES" in text
    assert "no arbitrary string, URL, or payload ever crosses the boundary" in text


def test_recovery_reproves_wp164_construction_documented():
    text = _flat(_contract())
    assert "re-proves the WP164 construction invariants" in text
    assert "a book-only store is rejected" in text
    assert "canonical payload key sets" in text
    assert "re-derived from the stored snapshot and payload" in text
    assert "recomputed from the unique" in text
    assert "owned by exactly one Gamma market" in text


def test_deterministic_identity_and_order_documented():
    text = _flat(_contract())
    assert "snapshot:sha256:" in text
    assert "ingest:sha256:" in text
    assert "response order never controls dataset identity" in text
    assert "No random UUID" in text


def test_no_jsonl_no_raw_response_no_scheduler_documented():
    text = _flat(_contract())
    assert "does not write WP10 JSONL snapshots" in text
    assert "never stores raw" in text
    assert "no scheduler" in text.lower()
    assert "never catches" in text and "BaseException" in text


def test_recovery_semantics_documented():
    text = _flat(_contract())
    assert (
        "recover_initial_polymarket_public_registration` performs zero network" in text
    )
    assert "never writes records" in text
    assert "1..45 total records" in text


def test_successor_boundary_and_no_wp163_amendment():
    text = _flat(_contract())
    assert "WP164-D001" in text
    assert "WP164-D007" in text
    assert "does not amend the WP163 record-store contract" in text


def test_module_matches_documented_public_symbols():
    module_text = MODULE.read_text(encoding="utf-8")
    for symbol in (
        "POLYMARKET_PUBLIC_POPULATION_LABEL",
        "populate_initial_polymarket_public_data",
        "recover_initial_polymarket_public_registration",
    ):
        assert symbol in module_text


def test_wp164a_additive_diagnostics_and_stage_counts_are_documented():
    text = _flat(_contract())
    for field in (
        "batch_is_valid",
        "batch_status",
        "batch_error_codes",
        "batch_warning_codes",
        "batch_accepted_record_version_ids",
        "batch_exact_duplicate_record_version_ids",
        "batch_quarantined_record_version_ids",
        "canonical_batch_sha256",
    ):
        assert field in text
    assert "complete typed `PointInTimeBatchValidationResult`" in text
    assert "successful Gamma list response" in text
    assert "before book normalization" in text
    assert "immediately after its builder returns" in text
    assert "only after the append commits" in text
    for field in (
        "build_failure_observation_kind",
        "build_status",
        "build_error_codes",
        "build_warning_codes",
        "build_quarantine_id",
        "build_input_fingerprint_sha256",
    ):
        assert field in text
    assert "completed invalid `PointInTimeBuildResult`" in text
    assert "already-derived `snapshot_id`" in text
    assert "PAYLOAD_SEQUENCE_LIMIT_EXCEEDED" in text
    assert "does not weaken `canonical_json_bytes`" in text


def test_wp164a_population_local_lifecycle_mapping_is_closed():
    text = _flat(_contract())
    assert "`closed is True`" in text and "exactly `closed`" in text
    assert "`active is True`" in text and "`closed is False`" in text
    assert "exactly `open`" in text
    assert "POPULATION_RESPONSE_INVALID" in text
    assert "There is no fallback" in text
    assert "`PolymarketPublicClient`" in text
    assert "downstream Alpha eligible statuses remain unchanged" in text


def test_wp164a_frozen_smoke_operator_contract_is_exact():
    text = _flat(_contract())
    assert "tools/polymarket/run_wp164a_public_smoke.py" in text
    assert "I_AUTHORIZE_EXACT_WP164A_PUBLIC_SMOKE_ATTEMPT_03" in text
    assert "/attempt-03" in text
    assert "Attempt-01 and Attempt-02 are permanently consumed" in text
    assert "128-bid/128-ask" in text
    assert "wp164a-public-smoke-authorization-envelope/1.0.0" in text
    assert "exactly 28 keys" in text
    for label in (
        "manifest:wp164a:public-smoke:1.0.0",
        "params:wp164a:public-smoke:1.0.0",
        "normalizer:wp164a:public-smoke:1.0.0",
        "validator:wp164a:public-smoke:1.0.0",
    ):
        assert label in text
    for artifact in (
        "WP164A_PUBLIC_SMOKE_INVOCATION.json",
        "WP164A_PUBLIC_SMOKE_RESULT.json",
        "point_in_time_records.sqlite3",
        "point_in_time_manifest.sqlite3",
    ):
        assert artifact in text
    for terminal in (
        "WP164A_PUBLIC_SMOKE_STATE_DRIFT",
        "WP164A_PUBLIC_SMOKE_LOCAL_EVIDENCE_DEFECT",
        "WP164A_PUBLIC_SMOKE_COMPLETE_SUCCESS",
        "WP164A_PUBLIC_SMOKE_BUILD_FAILED",
        "WP164A_PUBLIC_SMOKE_BATCH_INVALID",
        "WP164A_PUBLIC_SMOKE_EXTERNAL_FETCH_OR_RESPONSE_INVALID",
    ):
        assert terminal in text
