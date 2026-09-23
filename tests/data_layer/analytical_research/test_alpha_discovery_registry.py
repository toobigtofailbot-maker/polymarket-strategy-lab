from __future__ import annotations

from dataclasses import replace
import sqlite3

import pytest

from src.data_layer.analytical_research import alpha_discovery as AD
from src.data_layer.analytical_research import alpha_discovery_registry as DR


def _policy():
    result = AD.build_alpha_discovery_policy({
        "schema_version":"1.0.0", "policy_version":"test", "eligible_market_statuses":["open"],
        "metadata_freshness_seconds":60, "order_book_freshness_seconds":60,
        "resolution_rule_freshness_seconds":60, "soft_last_trade_price_abs_delta":"0.1",
        "soft_mid_price_abs_delta":"0.1", "soft_spread_abs_delta":"0.1",
        "soft_top_depth_relative_delta":"0.1", "queue_capacity":2, "exploration_slots":1,
        "audit_slots":1, "max_per_category":1, "audit_seed":"seed",
        "research_archetype_taxonomy_version":"v1", "advisory_only":True,
        "no_execution_authority":True, "no_strategy_authority":True,
        "no_qualification_authority":True,
    })
    assert result.is_valid
    return result.record


def _universe(policy):
    pre = dict(schema_version="1.0.0", policy_id=policy.alpha_discovery_policy_id,
        as_of="2026-01-01T00:00:00Z", cutoff_mode="AS_OF_INGESTION_TIME",
        query_engine_version="point-in-time-as-of-query@1.0.0", query_parameter_set_id=AD.ALPHA_DISCOVERY_PARAMETER_SET_ID,
        coverage_scope="BOUNDED_OBSERVED_UNIVERSE", external_universe_completeness="UNPROVEN", markets=(),
        advisory_only=True, no_execution_authority=True, no_strategy_authority=True, no_qualification_authority=True)
    return AD.AlphaUniverseSnapshot(**pre, alpha_universe_snapshot_id=AD._id("alphauniverse:sha256:", pre))


def test_discovery_registry_append_only_hash_chain_and_refs(tmp_path):
    path = (tmp_path / "discovery.sqlite3").resolve()
    initialized = DR.initialize_alpha_discovery_registry(path)
    assert initialized.is_valid and initialized.status == "REGISTRY_INITIALIZED"
    policy = _policy(); universe = _universe(policy)
    appended = DR.append_alpha_discovery_records(path, [universe, policy])
    assert appended.is_valid and appended.inserted_record_ids == tuple(sorted((policy.alpha_discovery_policy_id, universe.alpha_universe_snapshot_id)))
    assert [e.record_kind for e in appended.snapshot.entries] == ["DISCOVERY_POLICY", "UNIVERSE_SNAPSHOT"]
    assert appended.snapshot.head_entry_hash
    again = DR.append_alpha_discovery_records(path, [policy, universe])
    assert again.is_valid and again.status == "REGISTRY_APPEND_IDEMPOTENT"
    before = path.read_bytes(); loaded = DR.load_and_verify_alpha_discovery_registry(path)
    assert loaded.is_valid and path.read_bytes() == before
    con = sqlite3.connect(path)
    try:
        for sql in ("UPDATE discovery_registry_records SET record_kind=record_kind", "DELETE FROM discovery_registry_records"):
            try:
                con.execute(sql); con.commit(); assert False, "mutation unexpectedly succeeded"
            except sqlite3.DatabaseError:
                con.rollback()
    finally:
        con.close()


def test_discovery_registry_invalid_batch_rolls_back(tmp_path):
    path = (tmp_path / "discovery.sqlite3").resolve(); assert DR.initialize_alpha_discovery_registry(path).is_valid
    policy = _policy(); universe = _universe(policy)
    result = DR.append_alpha_discovery_records(path, [universe])
    assert not result.is_valid and result.error_codes == ("REFERENCE_INVALID",)
    loaded = DR.load_and_verify_alpha_discovery_registry(path)
    assert loaded.is_valid and loaded.snapshot.total_rows == 0
    assert DR.append_alpha_discovery_records(path, [policy, object()]).error_codes == ("FIELD_TYPE_INVALID",)
    assert DR.load_and_verify_alpha_discovery_registry(path).snapshot.total_rows == 0


def test_semantic_validation_is_symmetric_across_mapping_append_and_load(tmp_path):
    path = (tmp_path / "semantic.sqlite3").resolve()
    assert DR.initialize_alpha_discovery_registry(path).is_valid
    policy = _policy()
    token = "token:polymarket:symmetry"
    market = AD.ObservedMarketState(
        "market:polymarket:symmetry", "event:polymarket:symmetry", "open", "condition:symmetry",
        (token,), ("No", "Yes"), "2026-12-01T00:00:00Z", "test", "Question",
        "record:sha256:" + "1" * 64, "2026-01-01T00:00:00Z", "FRESH",
        "2" * 64, "3" * 64, "4" * 64, (),
        (AD.OrderBookState(token, "record:sha256:" + "5" * 64, "2026-01-01T00:00:00Z",
            "FRESH", "0.01", "1", "0.5", "0.45", "0.55", "0.5", "0.1", "2", "ORDER_BOOK_VALID"),), (),
    )
    pre = dict(schema_version="1.0.0", policy_id=policy.alpha_discovery_policy_id,
        as_of="2026-01-01T00:00:30Z", cutoff_mode="AS_OF_INGESTION_TIME",
        query_engine_version="point-in-time-as-of-query@1.0.0",
        query_parameter_set_id=AD.ALPHA_DISCOVERY_PARAMETER_SET_ID,
        coverage_scope="BOUNDED_OBSERVED_UNIVERSE", external_universe_completeness="UNPROVEN",
        markets=(market,), advisory_only=True, no_execution_authority=True,
        no_strategy_authority=True, no_qualification_authority=True)
    universe = AD.AlphaUniverseSnapshot(**pre, alpha_universe_snapshot_id=AD._id("alphauniverse:sha256:", pre))
    bases = AD.build_pre_allocation_triage_bases(universe, policy,
        analysis_temporal_mode="HISTORICAL_REPLAY",
        alpha_memory_temporal_posture="HISTORICAL_AVAILABILITY_UNPROVEN").records
    finalized = AD.allocate_and_finalize_research_queue(universe, policy, bases)
    assert finalized.is_valid
    valid_decision = finalized.records[0]
    invalid = replace(valid_decision, historical_replay_valid_for_alpha_memory=True)
    invalid_preimage = AD._without_id(invalid, "market_triage_decision_id")
    invalid = replace(invalid, market_triage_decision_id=AD._id("alphatriage:sha256:", invalid_preimage))
    invalid_mapping = AD._canonical(invalid)
    with pytest.raises(ValueError, match="TEMPORAL_POSTURE_INVALID"):
        AD.alpha_discovery_record_to_mapping(invalid)
    with pytest.raises(ValueError, match="TEMPORAL_POSTURE_INVALID"):
        AD.alpha_discovery_record_from_mapping(AD.MarketTriageDecision, invalid_mapping)
    assert DR.append_alpha_discovery_records(path, [invalid]).error_codes == ("FIELD_VALUE_INVALID",)

    valid_records = [policy, universe, *finalized.records]
    for record in valid_records:
        mapping = AD.alpha_discovery_record_to_mapping(record)
        assert AD.alpha_discovery_record_from_mapping(type(record), mapping) == record
    appended = DR.append_alpha_discovery_records(path, valid_records)
    assert appended.is_valid, appended.error_codes
    loaded = DR.load_and_verify_alpha_discovery_registry(path)
    assert loaded.is_valid and tuple(entry.record for entry in loaded.snapshot.entries)


def test_registry_rejects_memory_relative_symlink_and_foreign_schema(tmp_path):
    assert DR.initialize_alpha_discovery_registry(":memory:").error_codes == ("PATH_INVALID",)
    assert DR.initialize_alpha_discovery_registry("relative.sqlite3").error_codes == ("PATH_INVALID",)
    foreign = (tmp_path / "foreign.sqlite3").resolve()
    sqlite3.connect(foreign).close()
    assert DR.initialize_alpha_discovery_registry(foreign).error_codes == ("REGISTRY_SCHEMA_CONFLICT",)
