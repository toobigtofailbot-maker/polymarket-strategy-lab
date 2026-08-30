"""Focused docs tests for the WP165 incremental-population canonical contract."""

from __future__ import annotations

import pathlib
import re


REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
CONTRACT = (
    REPO_ROOT / "docs" / "polymarket_incremental_point_in_time_population_contract.md"
)
MODULE = (
    REPO_ROOT
    / "src"
    / "data_layer"
    / "point_in_time_market_research"
    / "polymarket_incremental_population.py"
)


def _contract() -> str:
    return CONTRACT.read_text(encoding="utf-8")


def _flat(text: str) -> str:
    return re.sub(r"\s+", " ", text)


def test_contract_document_exists():
    assert CONTRACT.is_file()


def test_label_and_posture_are_exact():
    text = _contract()
    assert "POLYMARKET_BOUNDED_CUMULATIVE_INCREMENTAL_POINT_IN_TIME_POPULATION" in text
    assert (
        "MANUAL_GET_ONLY_CUMULATIVE_256_RECORD_CROSS_RUN_LINEAGE_NO_TRADING_AUTHORITY"
        in text
    )
    assert (
        "src/data_layer/point_in_time_market_research/polymarket_incremental_population.py"
        in text
    )


def test_cumulative_technique_and_wp162_d004_open_documented():
    text = _flat(_contract())
    assert "WP162-D004 remains OPEN" in text
    assert "MUST NOT silently pass uncommitted external `known_parent_record_ids`" in text
    assert "cumulative validated batch" in text
    assert "bounded to 256 records" in text
    assert "WP165-D001" in text


def test_baseline_convergence_proof_documented():
    text = _flat(_contract())
    assert "highest `sequence_number` entry" in text
    assert "VALIDATED_RECORD_BATCH" in text
    assert "set(reference.ordinary_record_version_ids) == set(store record ids)" in text
    assert "validated_batch_sha256" in text
    assert "VALIDATED_BATCH_RECOMPUTED" in text
    assert "INCREMENTAL_BASELINE_UNREGISTERED" in text
    assert "recovery_required=True" in text


def test_manifest_id_binding_documented():
    text = _flat(_contract())
    assert "binds the chain's `manifest_id` to `config.manifest_id` BEFORE any network" in text
    assert "closed pre-network `INCREMENTAL_PROVENANCE_MISMATCH`" in text


def test_strict_superset_recoverability_documented():
    text = _flat(_contract())
    assert "recovery_required` is `True` ONLY when the extra suffix is provably" in text
    assert "two distinct orphan batches is blocked with `recovery_required=False`" in text


def test_parsed_time_chronology_documented():
    text = _flat(_contract())
    assert "true chronology, never by lexical string order" in text
    assert "12:00:00.500000Z" in text


def test_registration_success_is_proven_documented():
    text = _flat(_contract())
    assert "A typed adapter success is never trusted on its type alone" in text
    assert "independent WP161 reload shows the exact reference and entry durably persisted" in text
    assert "never actually wrote the registration is treated as a registration failure" in text


def test_recovery_config_bounded_shape_documented():
    text = _flat(_contract())
    assert "at least one and at most `bounded_markets` Gamma records" in text
    assert "zero CLOB records when `bounded_books == 0`" in text
    assert "reproduces the exact deterministic `_select_tokens` selection" in text
    assert "each parented to its same-run Gamma owner" in text


def test_public_api_symbols_are_documented():
    text = _contract()
    for symbol in (
        "POLYMARKET_INCREMENTAL_POPULATION_LABEL",
        "POLYMARKET_INCREMENTAL_POPULATION_POSTURE",
        "POLYMARKET_INCREMENTAL_POPULATION_STATUSES",
        "POLYMARKET_INCREMENTAL_POPULATION_ERROR_CODES",
        "PolymarketIncrementalPopulationResult",
        "capture_incremental_polymarket_public_data",
        "recover_incremental_polymarket_public_registration",
    ):
        assert symbol in text
    text_flat = _flat(_contract())
    assert "reuses the exact WP164 `PolymarketPublicPopulationConfig`" in text_flat
    assert "grew by exactly 7" in text_flat


def test_lineage_classifications_documented():
    text = _flat(_contract())
    assert "PRIMARY_ASSERTION" in text
    assert "EXACT_DUPLICATE" in text
    assert "SOURCE_REVISION" in text
    assert "latest prior record for the same WP156 entity" in text
    assert "chosen by ingestion time, then observed time, then `record_version_id`" in text
    assert "three classification counts sum to `new_record_count`" in text
    assert "never writes `SEMANTIC_DUPLICATE`" in text


def test_identity_drift_documented():
    text = _flat(_contract())
    assert "INCREMENTAL_IDENTITY_DRIFT" in text
    assert "never silently forks identity" in text
    assert "same raw token was previously associated with a different `market_id`" in text


def test_deterministic_run_identity_documented():
    text = _flat(_contract())
    assert "does NOT reuse the WP164 `_run_identities`" in text
    assert "snapshot:sha256:" in text
    assert "ingest:sha256:" in text
    assert "response order never controls dataset identity" in text
    assert "No random UUID" in text


def test_append_new_register_cumulative_ordering_documented():
    text = _flat(_contract())
    assert "ONLY the new records are appended" in text
    assert "append_point_in_time_records" in text
    assert "COMPLETE cumulative dataset is then registered" in text
    assert "persist_validated_record_batch_snapshot" in text
    assert "new records first, cumulative reference second" in text
    assert "prior reference remains immutable" in text
    assert "no `known_parent_record_ids`" in text.replace("NO ", "no ")


def test_registration_failure_and_recovery_documented():
    text = _flat(_contract())
    assert "INCREMENTAL_RECORDS_PERSISTED_REGISTRATION_FAILED" in text
    assert "EVERY registration failure mode" in text
    assert "raised registration exception is contained" in text
    assert "raw adapter object is never dereferenced" in text
    assert "DATASET_PERSISTENCE_ADAPTER_ERROR_CODES" in text
    assert (
        "recover_incremental_polymarket_public_registration` performs zero network"
        in text
    )
    assert "1..45 orphan records" in text
    assert "reconstructed from only the registered prior state" in text
    assert "object-for-object" in text
    assert "INCREMENTAL_RECOVERY_INVALID" in text


def test_no_keyset_scheduler_auth_trading_documented():
    text = _flat(_contract())
    assert "never stores raw" in text
    assert "no keyset/pagination" in text.lower() or "adds no keyset/pagination" in text
    assert "no Data API" in text
    assert "no scheduler" in text.lower()
    assert "never catches `BaseException`" in text
    assert "no order/trading/execution authority" in text


def test_import_allowlist_and_successor_boundary_documented():
    text = _flat(_contract())
    assert "imports ONLY the allowlisted sibling-private WP164 helpers" in text
    assert "_run_network_population" in text
    assert "WP165-D007" in text
    assert "intended scope of WP166" in text
    assert "does not amend the WP164 initial-seed contract" in text


def test_module_matches_documented_public_symbols():
    module_text = MODULE.read_text(encoding="utf-8")
    for symbol in (
        "POLYMARKET_INCREMENTAL_POPULATION_LABEL",
        "capture_incremental_polymarket_public_data",
        "recover_incremental_polymarket_public_registration",
    ):
        assert symbol in module_text
