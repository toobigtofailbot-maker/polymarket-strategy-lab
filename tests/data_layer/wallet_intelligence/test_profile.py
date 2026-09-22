"""S10-WALLET-02 deterministic PIT wallet profile contract tests."""

from __future__ import annotations

from dataclasses import fields

import pytest

from src.data_layer.point_in_time_market_research.research_provenance import (
    ObservabilityEvidence,
    build_pit_timestamps,
    build_raw_evidence_reference,
    build_research_provenance_manifest,
)
from src.data_layer.wallet_intelligence import contracts as c
from src.data_layer.wallet_intelligence import ledger as ledger
from src.data_layer.wallet_intelligence import profile as p


WALLET = "0x" + "1" * 40
RELATED = "0x" + "2" * 40
CONTROL = "0x" + "3" * 40
CONDITION = "0xabc"
TOKEN = "7"


def _obs(at: str, *, event_time: str | None = None, uncertain: bool = False) -> ObservabilityEvidence:
    return ObservabilityEvidence(
        local_first_seen_time=at,
        event_time=event_time,
        decisive_clock_uncertain=uncertain,
    )


def _manifest(*, cutoff: str = "2026-01-04T00:00:00Z"):
    return build_research_provenance_manifest(
        repo_code_identity="test-head",
        information_cutoff=cutoff,
        output_identity="wallet-profile-test",
        output_hash="9" * 64,
    )


def _cohort(manifest, *, members=None, cutoff="2026-01-05T00:00:00Z"):
    members = members or (
        p.WalletDiscoveryCohortMember(
            canonical_wallet=WALLET,
            cohort_role="CANDIDATE",
            discovery_reason="verified-public-cohort",
            discovery_evidence_reference_ids=("evidence:cohort",),
            discovery_provenance_manifest_ids=(manifest.research_provenance_manifest_id,),
            discovery_observability=_obs("2026-01-04T00:00:00Z"),
        ),
    )
    return p.build_wallet_discovery_cohort_snapshot(
        discovery_cutoff=cutoff,
        evaluation_start="2026-01-05T00:00:00Z",
        evaluation_end="2026-04-01T00:00:00Z",
        discovery_method="CALLER_SUPPLIED_PIT_SET",
        selection_policy_id="test-selection",
        selection_policy_version="1",
        members=members,
        provenance_manifests=(manifest,),
    )


def _context(
    manifest,
    *,
    group="group-1",
    metadata_at="2026-01-03T00:00:00Z",
    resolution_at="2026-02-01T00:00:00Z",
    resolved="1",
    category="politics",
):
    return p.build_wallet_profile_market_context(
        condition_context="DATA_API_RESPONSE_CONDITION_ID",
        condition_value=CONDITION,
        token_context="CLOB_TOKEN_ID",
        token_value=TOKEN,
        instrument_class="STANDARD_BINARY_OUTCOME",
        category_label=category,
        mechanism_label="binary",
        horizon_label="monthly",
        independence_group_id=group,
        metadata_observability=_obs(metadata_at),
        metadata_dq_flags=("OK",),
        metadata_replay_fidelity="FAITHFUL",
        resolved_token_value=resolved,
        resolution_observability=_obs(resolution_at),
        resolution_dq_flags=("OK",),
        resolution_replay_fidelity="FAITHFUL",
        research_provenance_manifest_ids=(manifest.research_provenance_manifest_id,),
    )


def _raw(run_key, *, seen="2026-01-11T00:00:00Z", suffix="a"):
    pit = build_pit_timestamps(local_first_seen_time=seen, ingestion_time=seen)
    return build_raw_evidence_reference(
        source_system="POLYMARKET_DATA_API_V2",
        endpoint="/v2/trades",
        retrieval_method="GET/fixture",
        content_sha256=suffix * 64,
        byte_length=10,
        media_type="application/json",
        pit=pit,
        dq_flags=("OK",),
        replay_fidelity="FAITHFUL",
        request_parameters={"user": WALLET, "run": run_key[-8:]},
    )


def _page(raw, run_key, *, seen="2026-01-11T00:00:00Z"):
    return c.build_wallet_feed_page_evidence(
        raw_evidence_reference_id=raw.raw_evidence_reference_id,
        ingest_run_key=run_key,
        feed_key="TRADES",
        canonical_request_identity={"user": WALLET},
        requested_page_size=100,
        has_more=False,
        local_first_seen_time=seen,
        ingestion_time=seen,
        api_source_parser_version="test/1",
        dq_flags=("OK",),
        replay_fidelity="FAITHFUL",
        source_row_count=10,
        normalized_event_count=10,
        observation_count=10,
    )


def _event(
    *,
    wallet=WALLET,
    event_time="2026-01-10T00:00:00Z",
    price="0.25",
    side="BUY",
    event_type="TRADE_FILL",
    native="event-1",
    strength="API_NATIVE_STRONG",
    condition=CONDITION,
    token=TOKEN,
    notional="10",
):
    kwargs = dict(
        identity_strength=strength,
        canonical_event_type=event_type,
        canonical_wallet=wallet,
        source_system_family="POLYMARKET_DATA_API_V2",
        side=side,
        price=price,
        notional=notional,
        event_time=event_time,
        condition_context="DATA_API_RESPONSE_CONDITION_ID",
        condition_value=condition,
        token_context="CLOB_TOKEN_ID",
        token_value=token,
    )
    if event_type == "TRADE_FILL":
        kwargs["combo_state"] = "FALSE"
    if strength == "API_NATIVE_STRONG":
        kwargs["native_event_id"] = native
    elif strength == "CHAIN_NATIVE_STRONG":
        kwargs.update(chain_id=137, transaction_hash="0x" + native[-1] * 64, log_index=int(native[-1]))
    return c.build_wallet_evidence_event(**kwargs)


def _event_observation(event, page, raw, run_key, *, seen="2026-01-11T00:00:00Z", dq=("OK",), fidelity="FAITHFUL"):
    return c.build_wallet_event_observation(
        wallet_event_id=event.wallet_event_id,
        wallet_feed_page_evidence_id=page.wallet_feed_page_evidence_id,
        ingest_run_key=run_key,
        source_system="POLYMARKET_DATA_API_V2",
        endpoint="/v2/trades",
        source_activity_type="TRADE",
        pit=build_pit_timestamps(event_time=event.event_time, local_first_seen_time=seen, ingestion_time=seen),
        dq_flags=dq,
        replay_fidelity=fidelity,
        raw_evidence_reference_id=raw.raw_evidence_reference_id,
    )


def _ledger_case(tmp_path, events, *, observations=None, extra_records=()):
    tmp_path.mkdir(parents=True, exist_ok=True)
    path = str(tmp_path / "wallet.sqlite")
    assert ledger.initialize_wallet_evidence_ledger(path).is_valid
    manifest = _manifest()
    run_key = c.derive_ingest_run_key({"wallet": WALLET, "case": "profile"})
    raw = _raw(run_key)
    page = _page(raw, run_key)
    if observations is None:
        observations = [_event_observation(event, page, raw, run_key) for event in events]
    batch = [manifest, raw, page, *events, *observations, *extra_records]
    result = ledger.append_wallet_evidence_records(path, batch)
    assert result.is_valid, result.error_codes
    return path, manifest, result.snapshot.head_hash


def _profile(tmp_path, *, events=None, context_overrides=None, observations=None, extra_records=(), identity_observability=None, contexts=None):
    events = events or [_event()]
    path, manifest, head = _ledger_case(tmp_path, events, observations=observations, extra_records=extra_records)
    cohort = _cohort(manifest)
    context = _context(manifest, **(context_overrides or {}))
    result = p.build_wallet_profile_snapshot(
        wallet_ledger_path=path,
        cohort_snapshot=cohort,
        target_wallet=WALLET,
        as_of="2026-03-01T00:00:00Z",
        market_contexts=contexts or (context,),
        identity_observability=identity_observability or {},
    )
    return result, path, manifest, cohort, context, head


def test_market_context_identity_pit_and_roundtrip():
    manifest = _manifest()
    context = _context(manifest)
    mapping = p.wallet_profile_market_context_to_mapping(context)
    assert set(mapping) == set(p.WalletProfileMarketContext.__dataclass_fields__)
    assert p.wallet_profile_market_context_to_mapping(p.wallet_profile_market_context_from_mapping(mapping)) == mapping
    changed = _context(manifest, category="sports")
    assert changed.wallet_profile_market_context_id != context.wallet_profile_market_context_id
    tampered = dict(mapping)
    tampered["category_label"] = "sports"
    with pytest.raises(p.WalletProfileError, match="PROFILE_IDENTITY_MISMATCH"):
        p.wallet_profile_market_context_from_mapping(tampered)
    future = _context(manifest, metadata_at="2026-04-01T00:00:00Z")
    assert future.metadata_observability != context.metadata_observability


def test_cohort_rejects_post_cutoff_discovery_and_retains_members():
    manifest = _manifest()
    late = p.WalletDiscoveryCohortMember(
        WALLET, "CANDIDATE", "late", ("e",), (manifest.research_provenance_manifest_id,),
        _obs("2026-02-01T00:00:00Z", event_time="2025-01-01T00:00:00Z"),
    )
    with pytest.raises(p.WalletProfileError, match="PROFILE_PIT_NOT_ADMISSIBLE"):
        _cohort(manifest, members=(late,))
    inactive = p.WalletDiscoveryCohortMember(
        RELATED, "CANDIDATE", "inactive-retained", ("e2",), (manifest.research_provenance_manifest_id,), _obs("2026-01-04T00:00:00Z")
    )
    cohort = _cohort(manifest, members=(_cohort(manifest).members[0], inactive))
    assert tuple(item.canonical_wallet for item in cohort.members) == (WALLET, RELATED)
    mapping = p.wallet_discovery_cohort_to_mapping(cohort)
    assert set(mapping) == set(p.WalletDiscoveryCohortSnapshot.__dataclass_fields__)
    assert p.wallet_discovery_cohort_to_mapping(p.wallet_discovery_cohort_from_mapping(mapping, provenance_manifests=(manifest,))) == mapping


def test_event_time_never_substitutes_for_observability(tmp_path):
    event = _event(event_time="2026-01-10T00:00:00Z")
    path = str(tmp_path / "late.sqlite")
    assert ledger.initialize_wallet_evidence_ledger(path).is_valid
    manifest = _manifest()
    run_key = c.derive_ingest_run_key({"wallet": WALLET, "case": "late"})
    raw = _raw(run_key, seen="2026-04-01T00:00:00Z")
    page = _page(raw, run_key, seen="2026-04-01T00:00:00Z")
    observation = _event_observation(event, page, raw, run_key, seen="2026-04-01T00:00:00Z")
    assert ledger.append_wallet_evidence_records(path, [manifest, raw, page, event, observation]).is_valid
    result = p.build_wallet_profile_snapshot(wallet_ledger_path=path, cohort_snapshot=_cohort(manifest), target_wallet=WALLET, as_of="2026-03-01T00:00:00Z", market_contexts=(_context(manifest),))
    assert result.sample_strength.admissible_trade_event_count == 0
    assert result.directional_skill.status == "INSUFFICIENT_DIRECTIONAL_EVIDENCE"


def test_reconciliation_and_repeated_trades_collapse_before_independent_sample(tmp_path):
    api = _event(native="event-1", event_time="2026-01-10T00:00:00Z")
    chain = _event(native="2", strength="CHAIN_NATIVE_STRONG", event_time="2026-01-10T00:00:00Z")
    repeat = _event(native="event-3", event_time="2026-01-12T00:00:00Z", price="0.30")
    disputed = _event(native="event-4", event_time="2026-01-13T00:00:00Z", price="0.35")
    link = c.build_wallet_reconciliation_link(
        reconciliation_state="API_AND_CHAIN_CONFIRMED", relation_kind="CHAIN_CONFIRMATION",
        event_ids=(api.wallet_event_id, chain.wallet_event_id), finality_state="CONFIRMED",
    )
    disagreement = c.build_wallet_reconciliation_link(
        reconciliation_state="SOURCE_DISAGREEMENT", relation_kind="DISAGREEMENT",
        event_ids=(disputed.wallet_event_id,),
    )
    result, *_ = _profile(tmp_path, events=[api, chain, repeat, disputed], extra_records=(link, disagreement))
    assert result.sample_strength.raw_trade_event_count == 4
    assert result.sample_strength.eligible_directional_episode_count == 2
    assert result.sample_strength.independent_event_group_count == 1
    assert result.sample_strength.effective_sample_size_groups == 1
    decisions = {item.wallet_event_id: item.reason_code for item in result.evidence_decisions}
    assert decisions[disputed.wallet_event_id] == "SOURCE_DISAGREEMENT"

    predecessor = _event(native="event-5", event_time="2026-01-15T00:00:00Z", price="0.9")
    successor = _event(native="event-6", event_time="2026-01-16T00:00:00Z", price="0.2")
    supersession = c.build_wallet_reconciliation_link(
        reconciliation_state="SUPERSEDED_BY_STRONGER_EVIDENCE", relation_kind="SUPERSESSION",
        event_ids=(predecessor.wallet_event_id, successor.wallet_event_id),
        predecessor_event_id=predecessor.wallet_event_id, successor_event_id=successor.wallet_event_id,
    )
    second, *_ = _profile(tmp_path / "supersession", events=[predecessor, successor], extra_records=(supersession,))
    assert successor.wallet_event_id in second.included_wallet_event_ids
    assert predecessor.wallet_event_id not in second.included_wallet_event_ids
    removal = c.build_wallet_reconciliation_link(
        reconciliation_state="REORGED_OR_REMOVED", relation_kind="REORG_REMOVAL",
        event_ids=(successor.wallet_event_id,), finality_state="REORGED",
    )
    third, *_ = _profile(
        tmp_path / "reorg", events=[predecessor, successor],
        extra_records=(supersession, removal),
    )
    assert predecessor.wallet_event_id in third.included_wallet_event_ids
    assert successor.wallet_event_id not in third.included_wallet_event_ids


def test_tiny_sample_uses_exact_jeffreys_shrinkage_without_promotion(tmp_path):
    result, *_ = _profile(tmp_path)
    assert result.directional_skill.status == "ESTIMATED_UNCALIBRATED"
    assert result.directional_skill.jeffreys_alpha == "1.5"
    assert result.directional_skill.jeffreys_beta == "0.5"
    assert result.directional_skill.jeffreys_posterior_mean == "0.75"
    assert result.directional_skill.jeffreys_posterior_variance == "0.0625"
    assert result.sample_strength.effective_sample_size_groups == 1


def test_raw_pnl_size_rank_and_rebates_never_drive_directional_skill(tmp_path):
    reward = _event(event_type="REWARD", side=None, price=None, native="event-9", notional="999999")
    result, *_ = _profile(tmp_path, events=[reward])
    assert result.directional_skill.status == "INSUFFICIENT_DIRECTIONAL_EVIDENCE"
    assert result.directional_skill.jeffreys_posterior_mean is None
    assert result.archetype.resolved_archetype == "INCENTIVE_REBATE"


def test_specialization_is_descriptive_and_one_group_never_claims_specialist(tmp_path):
    result, *_ = _profile(tmp_path)
    category = result.specialization.dimensions[0]
    assert category.status == "DESCRIPTIVE_UNCALIBRATED"
    assert category.group_shares == (("politics", "1"),)
    assert category.dominant_label == "politics"
    assert "specialist" not in {field.name.lower() for field in fields(p.SpecializationDimensionEvidence)}


def test_archetype_requires_direct_event_evidence_and_trade_fill_alone_is_not_enough(tmp_path):
    sell = _event(side="SELL", native="event-4")
    maker = _event(event_type="MAKER_REBATE", side=None, price=None, native="event-5")
    result, *_ = _profile(tmp_path, events=[sell, maker])
    assert result.archetype.classified_event_counts == (("MARKET_MAKING", 1),)
    assert result.archetype.unclassified_event_count == 1
    assert result.archetype.resolved_archetype == "MARKET_MAKING"


def test_related_address_strength_and_discovery_cutoff_control_aggregation(tmp_path):
    strong = c.build_wallet_account_identity_evidence(
        canonical_wallet=WALLET, generic_account_role="ACCOUNT_WALLET", polymarket_wallet_type="EOA",
        evidence_link_class="ONCHAIN_CONFIRMED", related_account=RELATED, source_reference="chain:1",
        effective_start="2026-01-01T00:00:00Z",
    )
    weak = c.build_wallet_account_identity_evidence(
        canonical_wallet=WALLET, generic_account_role="ACCOUNT_WALLET", polymarket_wallet_type="EOA",
        evidence_link_class="STATISTICAL_SIMILARITY", related_account=CONTROL, source_reference="stats:1",
    )
    observations = {strong.wallet_account_identity_evidence_id: _obs("2026-01-04T00:00:00Z"), weak.wallet_account_identity_evidence_id: _obs("2026-01-04T00:00:00Z")}
    result, path, manifest, _, context, _ = _profile(tmp_path, extra_records=(strong, weak), identity_observability=observations)
    assert result.subject_wallets == (WALLET, RELATED)
    by_id = {item.wallet_account_identity_evidence_id: item for item in result.related_address_evidence}
    assert by_id[strong.wallet_account_identity_evidence_id].aggregation_safe
    assert not by_id[weak.wallet_account_identity_evidence_id].aggregation_safe
    late_result, *_ = _profile(
        tmp_path / "late",
        extra_records=(strong,),
        identity_observability={strong.wallet_account_identity_evidence_id: _obs("2026-01-06T00:00:00Z")},
    )
    assert late_result.subject_wallets == (WALLET,)
    assert not late_result.related_address_evidence[0].aggregation_safe
    conflicting = _cohort(manifest, members=(
        _cohort(manifest).members[0],
        p.WalletDiscoveryCohortMember(
            RELATED, "CONTROL", "control", ("control:evidence",),
            (manifest.research_provenance_manifest_id,), _obs("2026-01-04T00:00:00Z"),
        ),
    ))
    with pytest.raises(p.WalletProfileError, match="PROFILE_COHORT_ROLE_CONFLICT"):
        p.build_wallet_profile_snapshot(
            wallet_ledger_path=path, cohort_snapshot=conflicting, target_wallet=WALLET,
            as_of="2026-03-01T00:00:00Z", market_contexts=(context,),
            identity_observability=observations,
        )


def test_current_market_metadata_and_late_resolution_cannot_leak_backward(tmp_path):
    future_context = None
    events = [_event()]
    path, manifest, _ = _ledger_case(tmp_path, events)
    future_context = _context(manifest, metadata_at="2026-04-01T00:00:00Z")
    result = p.build_wallet_profile_snapshot(wallet_ledger_path=path, cohort_snapshot=_cohort(manifest), target_wallet=WALLET, as_of="2026-03-01T00:00:00Z", market_contexts=(future_context,))
    assert result.directional_skill.status == "INSUFFICIENT_DIRECTIONAL_EVIDENCE"
    late_resolution = _context(manifest, resolution_at="2026-04-01T00:00:00Z")
    result2 = p.build_wallet_profile_snapshot(wallet_ledger_path=path, cohort_snapshot=_cohort(manifest), target_wallet=WALLET, as_of="2026-03-01T00:00:00Z", market_contexts=(late_resolution,))
    assert result2.directional_skill.status == "INSUFFICIENT_DIRECTIONAL_EVIDENCE"


def test_bad_dq_or_replay_fidelity_cannot_increase_sample_strength(tmp_path):
    event = _event()
    path = str(tmp_path / "bad.sqlite")
    assert ledger.initialize_wallet_evidence_ledger(path).is_valid
    manifest = _manifest()
    run_key = c.derive_ingest_run_key({"wallet": WALLET, "case": "bad"})
    raw = _raw(run_key)
    page = _page(raw, run_key)
    observation = _event_observation(event, page, raw, run_key, dq=("PARTIALLY_OBSERVED",), fidelity="PARTIAL")
    assert ledger.append_wallet_evidence_records(path, [manifest, raw, page, event, observation]).is_valid
    result = p.build_wallet_profile_snapshot(wallet_ledger_path=path, cohort_snapshot=_cohort(manifest), target_wallet=WALLET, as_of="2026-03-01T00:00:00Z", market_contexts=(_context(manifest),))
    assert result.sample_strength.admissible_trade_event_count == 0
    assert result.evidence_decisions[0].reason_code == "DQ_NOT_OK"
    partial_path = str(tmp_path / "partial.sqlite")
    assert ledger.initialize_wallet_evidence_ledger(partial_path).is_valid
    partial_observation = _event_observation(event, page, raw, run_key, fidelity="PARTIAL")
    assert ledger.append_wallet_evidence_records(partial_path, [manifest, raw, page, event, partial_observation]).is_valid
    partial = p.build_wallet_profile_snapshot(
        wallet_ledger_path=partial_path, cohort_snapshot=_cohort(manifest), target_wallet=WALLET,
        as_of="2026-03-01T00:00:00Z", market_contexts=(_context(manifest),),
    )
    assert partial.sample_strength.admissible_trade_event_count == 0
    assert partial.evidence_decisions[0].reason_code == "REPLAY_NOT_ELIGIBLE"


def test_profile_identity_binds_every_material_input_and_is_caller_order_invariant(tmp_path):
    result, path, manifest, cohort, context, head = _profile(tmp_path)
    same = p.build_wallet_profile_snapshot(wallet_ledger_path=path, cohort_snapshot=cohort, target_wallet=WALLET.upper().replace("0X", "0x"), as_of="2026-03-01T00:00:00Z", market_contexts=(context,))
    assert same.wallet_profile_snapshot_id == result.wallet_profile_snapshot_id
    changed = p.build_wallet_profile_snapshot(wallet_ledger_path=path, cohort_snapshot=cohort, target_wallet=WALLET, as_of="2026-03-02T00:00:00Z", market_contexts=(context,))
    assert changed.wallet_profile_snapshot_id != result.wallet_profile_snapshot_id
    assert result.wallet_ledger_head_hash == head
    assert p.wallet_profile_snapshot_from_mapping(p.wallet_profile_snapshot_to_mapping(result)) == result


def test_profile_schema_has_no_copyability_qualification_or_trading_authority():
    public_fields = set(p.WalletProfileSnapshot.__dataclass_fields__)
    forbidden = {"lead_time", "copy_latency", "copyability_score", "follower_pnl", "expected_return", "position_size", "paper_eligibility", "live_readiness", "insider_probability", "beneficial_owner"}
    assert public_fields.isdisjoint(forbidden)
    assert p.WalletProfileSnapshot.__dataclass_fields__["advisory_only"]
    assert not any(name.startswith("build_") and "score" in name for name in p.__dict__)


def test_profile_roundtrip_revalidates_and_rejects_tampering_or_unknown_fields(tmp_path):
    result, *_ = _profile(tmp_path)
    mapping = p.wallet_profile_snapshot_to_mapping(result)
    assert set(mapping) == set(p.WalletProfileSnapshot.__dataclass_fields__)
    assert p.wallet_profile_snapshot_to_mapping(p.wallet_profile_snapshot_from_mapping(mapping)) == mapping
    tampered = dict(mapping)
    tampered["as_of"] = "2026-03-02T00:00:00Z"
    with pytest.raises(p.WalletProfileError, match="PROFILE_IDENTITY_MISMATCH"):
        p.wallet_profile_snapshot_from_mapping(tampered)
    unknown = dict(mapping, unexpected="x")
    with pytest.raises(p.WalletProfileError, match="PROFILE_UNKNOWN_FIELD"):
        p.wallet_profile_snapshot_from_mapping(unknown)
    floaty = dict(mapping)
    floaty["sample_strength"] = dict(mapping["sample_strength"], max_group_episode_share=0.5)
    with pytest.raises(p.WalletProfileError, match="PROFILE_FIELD_TYPE_INVALID"):
        p.wallet_profile_snapshot_from_mapping(floaty)
    missing = dict(mapping)
    missing.pop("as_of")
    with pytest.raises(p.WalletProfileError, match="PROFILE_FIELD_VALUE_INVALID"):
        p.wallet_profile_snapshot_from_mapping(missing)
    null_required = dict(mapping, profile_policy_version=None)
    with pytest.raises(p.WalletProfileError):
        p.wallet_profile_snapshot_from_mapping(null_required)
    wrong_type = dict(mapping, subject_wallets={"wallet": WALLET})
    with pytest.raises(p.WalletProfileError, match="PROFILE_FIELD_TYPE_INVALID"):
        p.wallet_profile_snapshot_from_mapping(wrong_type)
    empty_required = dict(mapping, profile_policy_version="")
    with pytest.raises(p.WalletProfileError, match="PROFILE_FIELD_VALUE_INVALID"):
        p.wallet_profile_snapshot_from_mapping(empty_required)
    with pytest.raises(p.WalletProfileError, match="PROFILE_FIELD_TYPE_INVALID"):
        p.wallet_profile_snapshot_from_mapping(None)


def test_missing_independence_grouping_returns_unknown_not_raw_trade_count(tmp_path):
    result, *_ = _profile(tmp_path, context_overrides={"group": None})
    assert result.sample_strength.raw_trade_event_count == 1
    assert result.sample_strength.independent_event_group_count is None
    assert result.sample_strength.effective_sample_size_groups is None
    assert result.sample_strength.status == "UNKNOWN_INDEPENDENCE"
    assert result.directional_skill.status == "UNKNOWN_INDEPENDENCE"
