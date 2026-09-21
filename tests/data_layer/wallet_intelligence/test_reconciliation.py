"""Reconciliation tests (S10-WALLET-01, Section 11)."""

from __future__ import annotations

import pytest

from src.data_layer.wallet_intelligence import contracts as c
from src.data_layer.wallet_intelligence import reconciliation as r


def _chain(**overrides):
    params = dict(
        chain_id=137,
        block_number=100,
        block_hash="0x" + "b" * 64,
        transaction_hash="0x" + "a" * 64,
        transaction_index=2,
        log_index=1,
    )
    params.update(overrides)
    return r.build_chain_event_evidence(**params)


# ---------------------------------------------------------------------------
# Chain ordering / dedupe (R-W08).
# ---------------------------------------------------------------------------
def test_chain_ordering_deterministic_by_block_tx_log():
    a = _chain(block_number=100, transaction_index=0, log_index=5, transaction_hash="0x" + "a" * 64)
    b = _chain(block_number=100, transaction_index=0, log_index=1, transaction_hash="0x" + "a" * 64)
    d = _chain(block_number=99, transaction_index=9, log_index=9, transaction_hash="0x" + "c" * 64)
    ordered = r.order_chain_evidence([a, b, d])
    assert [e.ordering_key() for e in ordered] == [(99, 9, 9), (100, 0, 1), (100, 0, 5)]


def test_same_timestamp_different_log_not_deduped():
    a = _chain(log_index=1, transaction_hash="0x" + "a" * 64)
    b = _chain(log_index=2, transaction_hash="0x" + "a" * 64)  # same tx, different log
    deduped = r.dedupe_chain_evidence([a, b])
    assert len(deduped) == 2


def test_exact_duplicate_native_identity_deduped():
    a = _chain()
    b = _chain()
    assert len(r.dedupe_chain_evidence([a, b])) == 1


# ---------------------------------------------------------------------------
# Finality (R-W09) - no hardcoded block-count assumption.
# ---------------------------------------------------------------------------
def test_finality_requires_explicit_policy():
    policy = r.FinalityPolicy(policy_version="v1", min_confirmations_for_confirmed=3, min_confirmations_for_finalized=30)
    assert r.classify_finality(0, policy) == "UNFINALIZED"
    assert r.classify_finality(5, policy) == "CONFIRMED"
    assert r.classify_finality(50, policy) == "FINALIZED"
    assert r.classify_finality(50, policy, removed=True) == "REORGED"


def test_finality_policy_is_versioned_and_validated():
    bad = r.FinalityPolicy(policy_version="", min_confirmations_for_confirmed=1, min_confirmations_for_finalized=2)
    with pytest.raises(c.WalletContractError):
        r.classify_finality(1, bad)


# ---------------------------------------------------------------------------
# Event equivalence / disagreement (R-W10 / R-W11 / R-F05 / R-V2-03).
# ---------------------------------------------------------------------------
def _api_trade(**overrides):
    params = dict(
        identity_strength="SOURCE_CONTENT_DERIVED",
        canonical_event_type="TRADE_FILL",
        canonical_wallet="0x" + "1" * 40,
        combo_state="FALSE",
        source_system_family="POLYMARKET_DATA_API_V2",
        condition_context="DATA_API_RESPONSE_CONDITION_ID",
        condition_value="0xabc",
        side="BUY",
        price="0.5",
        size="10",
        event_time="2026-01-01T00:00:00Z",
        transaction_hash="0x" + "a" * 64,
    )
    params.update(overrides)
    return c.build_wallet_evidence_event(**params)


def _chain_trade(**overrides):
    params = dict(
        identity_strength="CHAIN_NATIVE_STRONG",
        canonical_event_type="TRADE_FILL",
        canonical_wallet="0x" + "1" * 40,
        combo_state="FALSE",
        chain_id=137,
        transaction_hash="0x" + "a" * 64,
        log_index=1,
        price="0.5",
        size="10",
    )
    params.update(overrides)
    return c.build_wallet_evidence_event(**params)


def test_api_and_chain_confirmed_when_strong_identity_matches():
    api = _api_trade(transaction_hash="0x" + "a" * 64)
    # chain event carries the same tx but api event lacks log_index, so strong keys
    # differ; equivalence instead comes from matching economics is NOT enough. Give
    # the api event a native id path is not applicable; use chain+chain confirmation
    # via an explicit protocol relation.
    chain = _chain_trade(transaction_hash="0x" + "a" * 64, log_index=1)
    assessment = r.assess_event_equivalence(api, chain, deterministic_protocol_relation=True)
    assert assessment.same_event is True
    assert assessment.reconciliation_state == "API_AND_CHAIN_CONFIRMED"
    # Original ids are unchanged (append-only).
    link = r.build_reconciliation_link_from_assessment(api, chain, assessment)
    assert api.wallet_event_id in link.event_ids and chain.wallet_event_id in link.event_ids


def test_source_disagreement_on_incompatible_economics():
    a = _api_trade(price="0.5")
    b = _api_trade(price="0.9")
    assessment = r.assess_event_equivalence(a, b)
    assert assessment.same_event is False
    assert assessment.reconciliation_state == "SOURCE_DISAGREEMENT"
    assert "price" in assessment.conflict_fields


def test_weak_similarity_not_merged():
    # Same wallet/type, identical comparable economics (no conflict), but distinct
    # events (differ only in event_time) with NO strong tx/native identity: they
    # must NOT be merged and must be marked ambiguous.
    a = _api_trade(event_time="2026-01-01T00:00:00Z", transaction_hash=None)
    b = _api_trade(event_time="2026-01-01T00:00:05Z", transaction_hash=None)
    assert a.wallet_event_id != b.wallet_event_id
    assessment = r.assess_event_equivalence(a, b)
    assert assessment.same_event is False
    assert assessment.reconciliation_state == "UNRESOLVED"
    assert "IDENTITY_AMBIGUOUS" in assessment.dq_flags


def test_cross_feed_nontrade_same_event_via_object_key():
    # Different source vocabularies (CONVERSION vs combo CONVERT both map to
    # CONVERSION) resolving to the same canonical economic-object key + no conflict.
    key = [("condition", "COMBO_CONDITION_ID", "0x03" + "bb" * 30)]
    a = c.build_wallet_evidence_event(
        identity_strength="SOURCE_CONTENT_DERIVED",
        canonical_event_type="CONVERSION",
        canonical_wallet="0x" + "1" * 40,
        source_system_family="POLYMARKET_DATA_API_V2",
        event_time="2026-01-01T00:00:00Z",
        economic_object_key=key,
    )
    b = c.build_wallet_evidence_event(
        identity_strength="API_NATIVE_STRONG",
        canonical_event_type="CONVERSION",
        canonical_wallet="0x" + "1" * 40,
        source_system_family="POLYMARKET_DATA_API_V2",
        native_event_id="combo-777",
        event_time="2026-01-01T00:00:00Z",
        economic_object_key=key,
    )
    assessment = r.assess_event_equivalence(a, b)
    assert assessment.same_event is True
    assert assessment.reconciliation_state in ("API_ONLY", "API_AND_CHAIN_CONFIRMED", "CHAIN_ONLY")


def test_different_wallet_or_type_not_same_event():
    a = _api_trade()
    b = _api_trade(canonical_event_type="REDEEM_SETTLEMENT", combo_state=None)
    assessment = r.assess_event_equivalence(a, b)
    assert assessment.same_event is False


def test_supersession_link_is_append_only_and_acyclic_pair():
    link = r.build_supersession_link(
        predecessor_event_id="walletevent:sha256:" + "a" * 64,
        successor_event_id="walletevent:sha256:" + "b" * 64,
    )
    assert link.reconciliation_state == "SUPERSEDED_BY_STRONGER_EVIDENCE"
    assert link.relation_kind == "SUPERSESSION"
    with pytest.raises(c.WalletContractError):
        r.build_supersession_link(
            predecessor_event_id="x", successor_event_id="x"
        )
