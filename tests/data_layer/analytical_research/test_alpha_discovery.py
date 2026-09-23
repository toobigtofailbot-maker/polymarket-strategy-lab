from __future__ import annotations

from dataclasses import replace
from copy import deepcopy
import hashlib
import random
from types import SimpleNamespace

import pytest

from src.data_layer.analytical_research import alpha_discovery as AD
from src.data_layer.analytical_research import alpha_factory as AF
from src.data_layer.analytical_research import alpha_factory_registry as AFR
import src.data_layer.point_in_time_market_research as PIT
from src.data_layer.point_in_time_market_research import records as PITR
from tests.data_layer.analytical_research.test_alpha_factory_records import (
    candidate_input, episode_input, family_input, source_input,
)


def _policy(**overrides):
    value = {
        "schema_version": "1.0.0", "policy_version": "fixture/1",
        "eligible_market_statuses": ["open"], "metadata_freshness_seconds": 60,
        "order_book_freshness_seconds": 30, "resolution_rule_freshness_seconds": 120,
        "soft_last_trade_price_abs_delta": "0.1", "soft_mid_price_abs_delta": "0.1",
        "soft_spread_abs_delta": "0.05", "soft_top_depth_relative_delta": "0.25",
        "queue_capacity": 4, "exploration_slots": 1, "audit_slots": 1,
        "max_per_category": 2, "audit_seed": "fixture-seed",
        "research_archetype_taxonomy_version": "alpha-archetypes/1",
        "advisory_only": True, "no_execution_authority": True,
        "no_strategy_authority": True, "no_qualification_authority": True,
    }
    value.update(overrides)
    result = AD.build_alpha_discovery_policy(value)
    assert result.is_valid, result.error_codes
    return result.record


def _book(token, *, last="0.5", midpoint="0.5", spread="0.1", depth="10", tick="0.01", minimum="1", freshness="FRESH"):
    return AD.OrderBookState(token, f"record:sha256:{hashlib.sha256(token.encode()).hexdigest()}", "2026-01-01T00:00:00Z", freshness,
        tick, minimum, last, "0.45", "0.55", midpoint, spread, depth, "ORDER_BOOK_VALID")


def _market(name: str, *, category="cat", status="open", gaps=(), book=None, question="Q", condition="c"):
    token = f"token:polymarket:{name}"
    return AD.ObservedMarketState(
        f"market:polymarket:{name}", f"event:polymarket:{name}", status, condition, (token,), ("No", "Yes"),
        "2026-12-01T00:00:00Z", category, question,
        f"record:sha256:{hashlib.sha256(name.encode()).hexdigest()}",
        "2026-01-01T00:00:00Z", "FRESH", "a" * 64, "b" * 64, "c" * 64, (),
        (book or _book(token),), tuple(gaps),
    )


def _universe(policy, markets, *, as_of="2026-01-01T00:00:30Z"):
    pre = dict(schema_version="1.0.0", policy_id=policy.alpha_discovery_policy_id, as_of=as_of,
        cutoff_mode="AS_OF_INGESTION_TIME", query_engine_version="point-in-time-as-of-query@1.0.0",
        query_parameter_set_id=AD.ALPHA_DISCOVERY_PARAMETER_SET_ID, coverage_scope="BOUNDED_OBSERVED_UNIVERSE",
        external_universe_completeness="UNPROVEN", markets=tuple(sorted(markets, key=lambda x:x.market_id)),
        advisory_only=True, no_execution_authority=True, no_strategy_authority=True, no_qualification_authority=True)
    return AD.AlphaUniverseSnapshot(**pre, alpha_universe_snapshot_id=AD._id("alphauniverse:sha256:", pre))


def _change(policy, prior, current, market, *, hard=("MARKET_STATUS_CHANGED",), soft=()):
    pre = dict(schema_version="1.0.0", policy_id=policy.alpha_discovery_policy_id,
        prior_universe_id=prior.alpha_universe_snapshot_id, current_universe_id=current.alpha_universe_snapshot_id,
        market_id=market.market_id, hard_change_classes=hard, soft_change_classes=soft,
        review_only_change_classes=(), affected_token_ids=(), affected_resolution_source_ids=(),
        before_record_version_ids=(market.metadata_record_version_id,), after_record_version_ids=(market.metadata_record_version_id,),
        comparison_diagnostics=(), advisory_only=True, no_execution_authority=True,
        no_strategy_authority=True, no_qualification_authority=True)
    return AD.MaterialChangeEvent(**pre, material_change_event_id=AD._id("alphachange:sha256:", pre))


def _pit_built(case_id, **overrides):
    value = deepcopy(PIT.load_synthetic_case_input(case_id))
    value.update(overrides)
    builders = {
        "MARKET_OBSERVATION": PIT.build_market_observation,
        "SOURCE_SNAPSHOT": PIT.build_source_snapshot,
        "RESOLUTION_RULE_SNAPSHOT": PIT.build_resolution_rule_snapshot,
    }
    result = builders[value["record_family"]](value)
    assert result.is_valid, result.error_codes
    return result.record, value


def _canonical_pit_records(*, post_cutoff=False, conflict_kind=None):
    source, source_input = _pit_built("PIT-C04-VALID-SOURCE-SNAPSHOT",
        source_id="source:polymarket:rules", observed_time="2026-01-01T00:00:01Z",
        ingestion_time="2026-01-01T00:00:02Z")
    meta_payload = {"market_status":"open", "outcome_labels":["No", "Yes"],
        "question_text":"Authoritative question",
        "token_ids":["token:polymarket:no", "token:polymarket:yes"],
        "condition_id":"condition:one", "category":"test", "resolution_date":"2026-12-01T00:00:00Z"}
    meta, meta_input = _pit_built("PIT-C01-VALID-MARKET-METADATA",
        platform_id="platform:polymarket", event_id="event:polymarket:one",
        market_id="market:polymarket:one", source_id="source:polymarket:gamma-markets",
        source_assertion_id="assertion:alpha02:metadata", canonical_payload=meta_payload)
    book_payload = {"bids":[{"price":"0.45","size":"10"}],
        "asks":[{"price":"0.55","size":"12"}], "tick_size":"0.01",
        "minimum_order_size":"1", "last_trade_price":"0.5"}
    book, book_input = _pit_built("PIT-C02-VALID-ORDER-BOOK-MISSING-EVENT-TIME",
        platform_id="platform:polymarket", event_id="event:polymarket:one",
        market_id="market:polymarket:one", token_id="token:polymarket:yes",
        source_id="source:polymarket:clob-book", source_assertion_id="assertion:alpha02:book",
        canonical_payload=book_payload)
    other_book, _ = _pit_built("PIT-C02-VALID-ORDER-BOOK-MISSING-EVENT-TIME",
        platform_id="platform:polymarket", event_id="event:polymarket:one",
        market_id="market:polymarket:one", token_id="token:polymarket:no",
        source_id="source:polymarket:clob-book", source_assertion_id="assertion:alpha02:book:no",
        canonical_payload=book_payload)
    rule, rule_input = _pit_built("PIT-C05-VALID-RESOLUTION-RULE-SNAPSHOT",
        platform_id="platform:polymarket", event_id="event:polymarket:one",
        market_id="market:polymarket:one", resolution_source_id="resolution-source:polymarket:primary",
        source_snapshot_id=source.envelope.source_snapshot_id)
    records = [meta, book, other_book, rule, source]
    inputs = {"metadata":meta_input, "book":book_input, "rule":rule_input, "source":source_input}
    if conflict_kind:
        conflict_input = deepcopy(inputs[conflict_kind])
        conflict_input.update(classification="CONFLICT", human_review_required=True,
            ingestion_time="2026-01-01T00:00:20Z", lineage_parent_ids=[])
        if conflict_kind == "metadata":
            conflict_input["source_assertion_id"] = "assertion:alpha02:metadata:conflict"
            conflict_input["canonical_payload"] = {**meta_payload, "market_status":"conflict-only-value"}
        elif conflict_kind == "book":
            conflict_input["source_assertion_id"] = "assertion:alpha02:book:conflict"
            conflict_input["canonical_payload"] = {**book_payload, "tick_size":"0.02"}
        elif conflict_kind == "rule":
            conflict_input["ambiguity_labels"] = ["CONFLICTING_SOURCE_TEXT"]
            conflict_input["rule_content_sha256"] = "9" * 64
        result = PITR.build_review_conflict_record(conflict_input)
        assert result.is_valid, result.error_codes
        records.append(result.record)
    if post_cutoff:
        late_payload = {**meta_payload, "question_text":"Unrelated future market"}
        late, _ = _pit_built("PIT-C01-VALID-MARKET-METADATA",
            platform_id="platform:polymarket", event_id="event:polymarket:future",
            market_id="market:polymarket:future", source_id="source:polymarket:gamma-markets",
            source_assertion_id="assertion:alpha02:future", observed_time="2026-01-01T00:01:00Z",
            ingestion_time="2026-01-01T00:01:01Z", canonical_payload=late_payload)
        records.append(late)
    return records


def _pit_store(tmp_path, records, name="pit.sqlite3"):
    path = (tmp_path / name).resolve()
    assert PIT.initialize_point_in_time_record_store(path).is_valid
    appended = PIT.append_point_in_time_records(path, records)
    assert appended.is_valid, appended.error_codes
    return path


def _alpha_registry(tmp_path, market_states, name="alpha.sqlite3"):
    path = (tmp_path / name).resolve()
    assert AFR.initialize_alpha_factory_registry(path).is_valid
    source_result = AF.build_research_source_reference(source_input())
    assert source_result.is_valid
    source = source_result.record
    records = [source]
    for market_name, state in market_states:
        candidate_result = AF.build_opportunity_candidate(candidate_input(
            title=f"Candidate {market_name}", scope_key=f"scope-{market_name}",
            subject_refs=[f"market:polymarket:{market_name}"],
            novelty_dimensions={"subject_keys":[market_name], "scope_key":f"scope-{market_name}",
                "mechanism_key":f"mechanism-{market_name}"}))
        family_result = AF.build_hypothesis_family(family_input(
            family_name=f"Family {market_name}", mechanism_key=f"mechanism-{market_name}",
            mechanism_dimensions={"driver":market_name}))
        assert candidate_result.is_valid and family_result.is_valid
        candidate, family = candidate_result.record, family_result.record
        records.extend((candidate, family))
        if state is not None:
            episode_result = AF.build_research_episode(episode_input(
                candidate_id=candidate.candidate_id, hypothesis_family_id=family.hypothesis_family_id,
                source_reference_ids=[source.source_reference_id], result_state=state,
                exact_scope={"market":market_name}, evidence_for=["evidence"], evidence_against=[],
                known_missing_data=[], what_would_change_the_conclusion=["new evidence"],
                material_change_basis=["market changed"], deterministic_evidence_refs=[f"ref-{market_name}"]))
            assert episode_result.is_valid, episode_result.error_codes
            records.append(episode_result.record)
    appended = AFR.append_alpha_factory_records(path, records)
    assert appended.is_valid, appended.error_codes
    return path


def test_identity_roundtrip_and_authority_boundaries():
    policy = _policy()
    mapping = AD.alpha_discovery_record_to_mapping(policy)
    assert AD.alpha_discovery_record_from_mapping(AD.AlphaDiscoveryPolicy, mapping) == policy
    changed = dict(mapping); changed["queue_capacity"] = 99
    with pytest.raises(ValueError, match="IDENTITY_DERIVATION_MISMATCH"):
        AD.alpha_discovery_record_from_mapping(AD.AlphaDiscoveryPolicy, changed)
    base = {k:v for k,v in mapping.items() if k != "alpha_discovery_policy_id"}
    base["execution_instruction"] = "undeclared authority-like field"
    assert AD.build_alpha_discovery_policy(base).error_codes == ("FORBIDDEN_FIELD",)
    base.pop("execution_instruction"); base["soft_spread_abs_delta"] = 0.1
    assert AD.build_alpha_discovery_policy(base).error_codes == ("FIELD_TYPE_INVALID",)


def test_visibility_and_freshness_clocks_are_distinct():
    assert AD.freshness_state("2026-01-01T00:00:00Z", "2026-01-01T00:01:00Z", 60) == "FRESH"
    assert AD.freshness_state("2026-01-01T00:00:00Z", "2026-01-01T00:01:01Z", 60) == "STALE"
    assert AD.freshness_state("2026-01-01T00:02:00Z", "2026-01-01T00:01:00Z", 60) == "INVALID_CLOCK"


def test_typed_subject_namespace_matching_never_cross_matches():
    market = _market("same")
    assert AD.canonical_market_subject_refs(market) == (
        "event:polymarket:same", "market:polymarket:same", "token:polymarket:same")
    refs = set(AD.canonical_market_subject_refs(market))
    assert "token:polymarket:same" in refs
    assert "token_id:token:polymarket:same" not in refs
    assert "same" not in refs


def test_alpha_memory_temporal_posture_blocks_historical_lookahead(tmp_path):
    policy = _policy(); universe = _universe(policy, [_market("a")])
    result = AD.build_pre_allocation_triage_bases(universe, policy,
        analysis_temporal_mode="HISTORICAL_REPLAY",
        alpha_memory_temporal_posture="HISTORICAL_AVAILABILITY_UNPROVEN")
    basis = result.records[0]
    assert basis.priority_class == "MARKET_EVIDENCE_ONLY"
    assert basis.alpha_registry_head_entry_hash is None and not basis.matched_candidate_ids
    assert set(dict(basis.coverage).values()) == {"UNKNOWN"}
    rejected = AD.build_pre_allocation_triage_bases(universe, policy,
        analysis_temporal_mode="HISTORICAL_REPLAY",
        alpha_memory_temporal_posture="CURRENT_REGISTRY_BUILD_TIME_ONLY",
        alpha_registry_path=tmp_path / "today.sqlite3")
    assert rejected.error_codes == ("TEMPORAL_POSTURE_INVALID",)


@pytest.mark.parametrize("row, market_name, expected", [
    ("T1", "t1", ("INELIGIBLE", "INELIGIBLE", "NO_REOPEN", "INELIGIBLE", "MARKET_STATUS_INELIGIBLE", (), (False,False,False))),
    ("T2", "t2", ("DEFERRED", "DEFER_CAPTURE_REFRESH", "REOPEN_UNAVAILABLE_DATA", "DEFERRED", "METADATA_CONFLICT", ("MARKET_METADATA_REFRESH",), (False,False,False))),
    ("T3", "t3", ("DEFERRED", "DEFER_CAPTURE_REFRESH", "REOPEN_UNAVAILABLE_DATA", "DEFERRED", "METADATA_STALE", ("MARKET_METADATA_REFRESH",), (False,False,False))),
    ("T4", "t4", ("ELIGIBLE", "MARKET_EVIDENCE_ONLY", "REOPEN_UNAVAILABLE_HISTORICAL_ALPHA_MEMORY", "READY", "ALPHA_MEMORY_HISTORICAL_UNPROVEN", (), (True,True,True))),
    ("T5", "t5", ("ELIGIBLE", "NEW_RESEARCH", "NO_REOPEN", "READY", "ALPHA_NO_CANONICAL_MATCH", (), (True,True,True))),
    ("T6", "t6", ("ELIGIBLE", "MATERIAL_REOPEN", "REOPEN_ELIGIBLE", "READY", "MATERIAL_CHANGE_REOPEN_ELIGIBLE", (), (True,True,True))),
    ("T7", "t7", ("ELIGIBLE", "EXISTING_RESEARCH_FOLLOWUP", "NO_AUTOMATIC_REOPEN", "READY", "MATERIAL_CHANGE_EXISTING_RESEARCH", (), (True,True,True))),
    ("T8", "t8", ("ELIGIBLE", "EXISTING_RESEARCH_FOLLOWUP", "NO_REOPEN", "READY", "EXISTING_RESEARCH_FOLLOWUP", (), (True,True,True))),
    ("T9", "t9", ("ELIGIBLE", "EXISTING_OTHER", "NO_REOPEN", "READY", "EXISTING_RESEARCH_NO_CURRENT_TRIGGER", (), (True,True,True))),
])
def test_closed_triage_decision_table(tmp_path, row, market_name, expected):
    policy = _policy()
    market = _market(market_name)
    if row == "T1": market = replace(market, market_status="closed")
    if row == "T2": market = replace(market, data_gap_codes=("METADATA_CONFLICT",))
    if row == "T3": market = replace(market, metadata_freshness="STALE")
    universe = _universe(policy, [market])
    kwargs = {}
    if row == "T4":
        mode, posture = "HISTORICAL_REPLAY", "HISTORICAL_AVAILABILITY_UNPROVEN"
    else:
        mode, posture = "CURRENT_BUILD_ANALYSIS", "CURRENT_REGISTRY_BUILD_TIME_ONLY"
        kwargs["alpha_registry_path"] = _alpha_registry(tmp_path,
            [("t6", "WATCH_FOR_CHANGE"), ("t7", "RESEARCH_SUPPORTIVE"),
             ("t8", "RESEARCH_SUPPORTIVE"), ("t9", "WATCH_FOR_CHANGE")], f"{row}.sqlite3")
    if row in {"T6", "T7"}:
        prior = _universe(policy, [market], as_of="2026-01-01T00:00:00Z")
        kwargs["prior"] = prior
        kwargs["material_changes"] = (_change(policy, prior, universe, market),)
    result = AD.build_pre_allocation_triage_bases(universe, policy,
        analysis_temporal_mode=mode, alpha_memory_temporal_posture=posture, **kwargs)
    assert result.is_valid, result.error_codes
    basis = result.records[0]
    eligibility, priority, reopen, readiness, reason, requests, flags = expected
    assert (basis.eligibility, basis.priority_class, basis.reopen_disposition, basis.readiness) == (eligibility, priority, reopen, readiness)
    assert reason in basis.reason_codes
    assert tuple(sorted(x.request_type for x in basis.capture_requests)) == requests
    assert (basis.core_eligible, basis.exploration_eligible, basis.audit_eligible) == flags


def test_capture_gap_overlay_matrix():
    policy = _policy()
    gaps = ("OPTIONAL_METADATA_MISSING", "ORDER_BOOK_MISSING", "RULE_EVIDENCE_MISSING", "SOURCE_EVIDENCE_MISSING")
    market = _market("gaps", gaps=gaps)
    basis = AD.build_pre_allocation_triage_bases(_universe(policy,[market]), policy,
        analysis_temporal_mode="HISTORICAL_REPLAY",
        alpha_memory_temporal_posture="HISTORICAL_AVAILABILITY_UNPROVEN").records[0]
    assert basis.readiness == "READY_WITH_CAPTURE_GAPS"
    assert {x.request_type for x in basis.capture_requests} == {
        "MARKET_METADATA_REFRESH", "ORDER_BOOK", "RESOLUTION_RULE", "SOURCE_SNAPSHOT"}


def test_reopen_is_grouped_by_exact_candidate_and_family(tmp_path):
    policy = _policy()
    market = _market("multi")
    current = _universe(policy, [market])
    prior = _universe(policy, [market], as_of="2026-01-01T00:00:00Z")
    path = (tmp_path / "multi.sqlite3").resolve()
    assert AFR.initialize_alpha_factory_registry(path).is_valid
    source_result = AF.build_research_source_reference(source_input())
    assert source_result.is_valid
    source = source_result.record
    records = [source]
    for suffix, state in (("a", "WATCH_FOR_CHANGE"), ("b", None)):
        candidate_result = AF.build_opportunity_candidate(candidate_input(
            title=f"Candidate multi {suffix}", scope_key=f"scope-multi-{suffix}",
            subject_refs=[market.market_id],
            novelty_dimensions={"subject_keys":[f"multi-{suffix}"], "scope_key":f"scope-multi-{suffix}",
                "mechanism_key":f"mechanism-multi-{suffix}"}))
        family_result = AF.build_hypothesis_family(family_input(
            family_name=f"Family multi {suffix}", mechanism_key=f"mechanism-multi-{suffix}",
            mechanism_dimensions={"driver":f"multi-{suffix}"}))
        assert candidate_result.is_valid and family_result.is_valid
        candidate, family = candidate_result.record, family_result.record
        records.extend((candidate, family))
        if state is not None:
            episode_result = AF.build_research_episode(episode_input(
                candidate_id=candidate.candidate_id, hypothesis_family_id=family.hypothesis_family_id,
                source_reference_ids=[source.source_reference_id], result_state=state,
                exact_scope={"market":"multi-a"}, evidence_for=["evidence"], evidence_against=[],
                known_missing_data=[], what_would_change_the_conclusion=["new evidence"],
                material_change_basis=["market changed"], deterministic_evidence_refs=["ref-multi-a"]))
            assert episode_result.is_valid, episode_result.error_codes
            records.append(episode_result.record)
    appended = AFR.append_alpha_factory_records(path, records)
    assert appended.is_valid, appended.error_codes
    result = AD.build_pre_allocation_triage_bases(current, policy,
        analysis_temporal_mode="CURRENT_BUILD_ANALYSIS",
        alpha_memory_temporal_posture="CURRENT_REGISTRY_BUILD_TIME_ONLY",
        alpha_registry_path=path, prior=prior,
        material_changes=(_change(policy, prior, current, market),))
    assert result.is_valid, result.error_codes
    basis = result.records[0]
    assert len(basis.matched_candidate_ids) == 2
    assert basis.reopen_disposition == "REOPEN_REVIEW_REQUIRED"
    assert basis.priority_class == "EXISTING_RESEARCH_FOLLOWUP"
    assert "MATERIAL_CHANGE_REOPEN_ELIGIBLE" not in basis.reason_codes


def test_capture_requests_are_data_only():
    policy = _policy(); universe = _universe(policy, [_market("gap", gaps=("ORDER_BOOK_MISSING",))])
    basis = AD.build_pre_allocation_triage_bases(
        universe, policy, analysis_temporal_mode="HISTORICAL_REPLAY",
        alpha_memory_temporal_posture="HISTORICAL_AVAILABILITY_UNPROVEN",
    ).records[0]
    assert basis.capture_requests and {r.request_type for r in basis.capture_requests} == {"ORDER_BOOK"}
    request = basis.capture_requests[0]
    assert request.universe_id == universe.alpha_universe_snapshot_id
    assert request.policy_id == policy.alpha_discovery_policy_id
    assert not hasattr(request, "market_triage_decision_id")
    assert not hasattr(request, "alpha_research_queue_snapshot_id")
    assert not hasattr(request, "selected_lane")


def test_material_change_field_source_and_formula_table():
    policy = _policy()
    token = "token:polymarket:a"
    rule = AD.ResolutionRuleState("resolution-source:one", "1"*64, "record:sha256:"+"2"*64,
        "2026-01-01T00:00:00Z", "FRESH", "srcsnap:sha256:"+"3"*64,
        "record:sha256:"+"4"*64, "2026-01-01T00:00:00Z", "FRESH", "5"*64)
    before = replace(_market("a", question="Q1", book=_book(token, depth="10")), rules=(rule,))

    hard_cases = {
        "MARKET_STATUS_CHANGED": replace(before, market_status="paused"),
        "CONDITION_ID_CHANGED": replace(before, condition_id="condition:changed"),
        "TOKEN_SET_CHANGED": replace(before, token_ids=(token, "token:polymarket:b"),
            books=(before.books[0], _book("token:polymarket:b"))),
        "OUTCOME_SET_CHANGED": replace(before, outcome_labels=("Maybe", "No", "Yes")),
        "RESOLUTION_RULE_CHANGED": replace(before, rules=(replace(rule, rule_content_sha256="6"*64),)),
        "RESOLUTION_SOURCE_CHANGED": replace(before, rules=(replace(rule, resolution_source_id="resolution-source:two"),)),
        "TICK_SIZE_CHANGED": replace(before, books=(replace(before.books[0], tick_size="0.02"),)),
        "MIN_ORDER_SIZE_CHANGED": replace(before, books=(replace(before.books[0], minimum_order_size="2"),)),
    }
    for expected, after in hard_cases.items():
        result = AD.compare_alpha_universes(_universe(policy,[before]),
            _universe(policy,[after],as_of="2026-01-01T00:02:00Z"), policy)
        assert result.is_valid and expected in result.records[0].hard_change_classes

    soft_cases = {
        "LAST_TRADE_PRICE_MOVED": replace(before.books[0], last_trade_price="0.6"),
        "MID_PRICE_MOVED": replace(before.books[0], midpoint="0.6"),
        "SPREAD_CHANGED": replace(before.books[0], spread="0.15"),
        "TOP_DEPTH_CHANGED": replace(before.books[0], top_depth="20"),
    }
    for expected, book in soft_cases.items():
        result = AD.compare_alpha_universes(_universe(policy,[before]),
            _universe(policy,[replace(before, books=(book,))],as_of="2026-01-01T00:02:00Z"), policy)
        assert result.is_valid and expected in result.records[0].soft_change_classes

    review = replace(before, question_text="Q2", category="new")
    result = AD.compare_alpha_universes(_universe(policy,[before]),
        _universe(policy,[review],as_of="2026-01-01T00:02:00Z"), policy)
    assert result.records[0].review_only_change_classes == AD.REVIEW_CHANGE_CLASSES

    zero = replace(before, books=(replace(before.books[0], top_depth="0"),))
    zero_again = replace(zero, metadata_record_version_id="record:sha256:"+"f"*64)
    assert AD.compare_alpha_universes(_universe(policy,[zero]),
        _universe(policy,[zero_again],as_of="2026-01-01T00:02:00Z"), policy).records == ()
    missing_side = replace(before, books=(replace(before.books[0], midpoint=None),))
    missing = AD.compare_alpha_universes(_universe(policy,[before]),
        _universe(policy,[missing_side],as_of="2026-01-01T00:02:00Z"), policy).records[0]
    assert missing.comparison_diagnostics == ("DATA_MISSING",) and "MID_PRICE_MOVED" not in missing.soft_change_classes

    removed = AD.compare_alpha_universes(_universe(policy,[before]),
        _universe(policy,[replace(before, rules=())],as_of="2026-01-01T00:02:00Z"), policy).records[0]
    assert removed.hard_change_classes == ("RESOLUTION_SOURCE_CHANGED",)
    shared = AD.compare_alpha_universes(_universe(policy,[before]),
        _universe(policy,[hard_cases["RESOLUTION_RULE_CHANGED"]],as_of="2026-01-01T00:02:00Z"), policy).records[0]
    assert "RESOLUTION_RULE_CHANGED" in shared.hard_change_classes and "RESOLUTION_SOURCE_CHANGED" not in shared.hard_change_classes


def test_priority_vector_exact_order_and_direction():
    policy = _policy(); universe = _universe(policy, [_market(x) for x in "abcdefghij"])
    bases = list(AD.build_pre_allocation_triage_bases(universe, policy,
        analysis_temporal_mode="HISTORICAL_REPLAY", alpha_memory_temporal_posture="HISTORICAL_AVAILABILITY_UNPROVEN").records)
    pairs = [
        (replace(bases[0], priority_class="MATERIAL_REOPEN"), replace(bases[1], priority_class="NEW_RESEARCH")),
        (replace(bases[2], priority_class="NEW_RESEARCH", hard_material_change_count=2), replace(bases[3], priority_class="NEW_RESEARCH", hard_material_change_count=1)),
        (replace(bases[4], priority_class="NEW_RESEARCH", soft_material_change_count=2), replace(bases[5], priority_class="NEW_RESEARCH", soft_material_change_count=1)),
        (replace(bases[6], priority_class="NEW_RESEARCH", readiness="READY"), replace(bases[7], priority_class="NEW_RESEARCH", readiness="READY_WITH_CAPTURE_GAPS")),
        (replace(bases[8], priority_class="NEW_RESEARCH"), replace(bases[9], priority_class="NEW_RESEARCH")),
    ]
    for better, worse in pairs:
        assert better.priority_vector < worse.priority_vector
    modified = [item for pair in pairs for item in pair]
    expected = [b.market_id for b in sorted(modified, key=lambda b:b.priority_vector)]
    random.Random(41).shuffle(modified)
    assert [b.market_id for b in sorted(modified, key=lambda b:b.priority_vector)] == expected


def test_two_phase_allocation_materialization_is_order_invariant():
    policy = _policy(); universe = _universe(policy, [_market(x, category="same" if x != "d" else "other") for x in "abcd"])
    bases = list(AD.build_pre_allocation_triage_bases(universe, policy,
        analysis_temporal_mode="HISTORICAL_REPLAY", alpha_memory_temporal_posture="HISTORICAL_AVAILABILITY_UNPROVEN").records)
    first = AD.allocate_and_finalize_research_queue(universe, policy, bases); assert first.is_valid
    random.Random(7).shuffle(bases)
    second = AD.allocate_and_finalize_research_queue(universe, policy, bases); assert second.is_valid
    assert AD.alpha_discovery_record_to_mapping(first.record) == AD.alpha_discovery_record_to_mapping(second.record)
    decisions = first.records[:-1]
    assert {d.market_id for d in decisions} == {m.market_id for m in universe.markets}
    assert len({d.market_triage_decision_id for d in decisions}) == len(decisions)
    assert sum(d.selected_lane is not None for d in decisions) <= policy.queue_capacity


def test_newly_and_no_longer_observed_local_semantics():
    policy = _policy(); prior = _universe(policy, [_market("old")], as_of="2026-01-01T00:00:00Z")
    current = _universe(policy, [_market("new")], as_of="2026-01-02T00:00:00Z")
    bases = AD.build_pre_allocation_triage_bases(current, policy, analysis_temporal_mode="HISTORICAL_REPLAY",
        alpha_memory_temporal_posture="HISTORICAL_AVAILABILITY_UNPROVEN", prior=prior).records
    assert bases[0].newly_observed_locally and bases[0].comparison_prior_universe_id == prior.alpha_universe_snapshot_id
    final = AD.allocate_and_finalize_research_queue(current, policy, bases, prior=prior)
    assert final.record.prior_only_market_ids == ("market:polymarket:old",)
    no_prior = AD.build_pre_allocation_triage_bases(current, policy, analysis_temporal_mode="HISTORICAL_REPLAY",
        alpha_memory_temporal_posture="HISTORICAL_AVAILABILITY_UNPROVEN").records[0]
    assert not no_prior.newly_observed_locally and no_prior.comparison_prior_universe_id is None


def test_observed_universe_never_overclaims_external_completeness():
    policy = _policy(); universe = _universe(policy, [_market("a")])
    assert universe.coverage_scope == "BOUNDED_OBSERVED_UNIVERSE"
    assert universe.external_universe_completeness == "UNPROVEN"


def test_post_cutoff_store_growth_preserves_t0_semantic_universe_identity(tmp_path):
    policy = _policy(metadata_freshness_seconds=120, order_book_freshness_seconds=120,
        resolution_rule_freshness_seconds=120)
    records = _canonical_pit_records()
    path = _pit_store(tmp_path, records)
    before = AD.build_alpha_universe_snapshot(path, policy, "2026-01-01T00:00:30Z")
    assert before.is_valid, before.error_codes
    late = _canonical_pit_records(post_cutoff=True)[-1]
    assert PIT.append_point_in_time_records(path, [late]).is_valid
    after = AD.build_alpha_universe_snapshot(path, policy, "2026-01-01T00:00:30Z")
    assert after.is_valid, after.error_codes
    assert AD.alpha_discovery_record_to_mapping(before.record) == AD.alpha_discovery_record_to_mapping(after.record)
    assert before.record.alpha_universe_snapshot_id == after.record.alpha_universe_snapshot_id


@pytest.mark.parametrize("conflict_kind, expected_gap", [
    ("metadata", "METADATA_CONFLICT"), ("book", "ORDER_BOOK_CONFLICT"),
    ("rule", "RULE_EVIDENCE_CONFLICT"), ("source", "SOURCE_EVIDENCE_CONFLICT"),
])
def test_shared_pit_review_conflicts_overlay_exact_scope_without_replacing_authority(tmp_path, conflict_kind, expected_gap):
    policy = _policy(metadata_freshness_seconds=120, order_book_freshness_seconds=120,
        resolution_rule_freshness_seconds=120)
    path = _pit_store(tmp_path, _canonical_pit_records(conflict_kind=conflict_kind), f"{conflict_kind}.sqlite3")
    result = AD.build_alpha_universe_snapshot(path, policy, "2026-01-01T00:00:30Z")
    assert result.is_valid, result.error_codes
    market = result.record.markets[0]
    books = {book.token_id: book for book in market.books}
    assert expected_gap in market.data_gap_codes
    assert market.market_status == "open" and market.question_text == "Authoritative question"
    assert books["token:polymarket:yes"].tick_size == "0.01"
    assert books["token:polymarket:no"].state == "ORDER_BOOK_VALID"
    assert market.rules[0].rule_content_sha256 == "2" * 64
    if conflict_kind == "book":
        assert books["token:polymarket:yes"].state == "ORDER_BOOK_CONFLICT"


def test_conflict_only_metadata_does_not_admit_market(tmp_path):
    records = _canonical_pit_records(conflict_kind="metadata")
    conflict = records.pop()
    records = [record for record in records if not (
        isinstance(record, PIT.MarketObservationRecord) and record.observation_kind == "MARKET_METADATA")]
    records.append(conflict)
    path = _pit_store(tmp_path, records, "conflict-only.sqlite3")
    result = AD.build_alpha_universe_snapshot(path, _policy(), "2026-01-01T00:00:30Z")
    assert result.is_valid, result.error_codes
    assert result.record.markets == ()


def test_alpha_lane_to_coverage_mapping_is_closed():
    episode = SimpleNamespace(
        evidence_lanes=("RESOLUTION_RULES", "CROSS_MARKET", "FUNDAMENTAL", "HISTORICAL_REPEATABILITY", "MICROSTRUCTURE", "WEATHER"),
        producer_type="HERMES_CONTROLLED_RESEARCH",
    )
    coverage = dict(AD._coverage([episode], False))
    assert coverage["resolution_contract"] == "SUPPORTED"
    assert coverage["settlement_capital_lock"] == "PARTIAL"
    assert coverage["cross_market_logic"] == "SUPPORTED"
    assert coverage["combinatorial_portfolio"] == "PARTIAL"
    assert coverage["fundamental_public_info"] == "SUPPORTED"
    assert coverage["calibration_probability"] == "PARTIAL"
    assert coverage["microstructure"] == "SUPPORTED" and coverage["maker_liquidity"] == "PARTIAL"
    assert coverage["domain_specific"] == "SUPPORTED" and coverage["semantic_model_assisted"] == "SUPPORTED"
    for unmapped in ("wallet_public_flow", "latency_information_arrival", "behavioral_structural", "data_publication_latency"):
        assert coverage[unmapped] == "UNKNOWN"
    assert set(dict(AD._coverage([episode], True)).values()) == {"UNKNOWN"}


def test_skip_accounting_exploration_caps_and_audit_replay():
    policy = _policy(queue_capacity=5, exploration_slots=2, audit_slots=2, max_per_category=1)
    universe = _universe(policy, [_market(x, category="same") for x in "abc"])
    bases = AD.build_pre_allocation_triage_bases(universe, policy, analysis_temporal_mode="HISTORICAL_REPLAY",
        alpha_memory_temporal_posture="HISTORICAL_AVAILABILITY_UNPROVEN").records
    one = AD.allocate_and_finalize_research_queue(universe, policy, bases); two = AD.allocate_and_finalize_research_queue(universe, policy, tuple(reversed(bases)))
    assert one.record.alpha_research_queue_snapshot_id == two.record.alpha_research_queue_snapshot_id
    assert one.record.unused_exploration_slots > 0
    assert "EXPLORATION_POOL_EXHAUSTED" in one.record.unused_capacity_reason_codes
    assert one.record.core_triage_ids and len(one.record.core_triage_ids) == 1
