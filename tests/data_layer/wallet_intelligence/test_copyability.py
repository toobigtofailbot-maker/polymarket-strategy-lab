"""Synthetic evidence tests for the WALLET-03 read-only research contract."""

from __future__ import annotations

import builtins
from copy import deepcopy
from dataclasses import fields, replace
from decimal import localcontext
from hashlib import sha256
import importlib.util
import json
import os
from pathlib import Path
import socket
import sqlite3
import subprocess

import pytest

from src.data_layer.wallet_intelligence import copyability as c
from src.data_layer.point_in_time_market_research.research_provenance import (
    ObservabilityEvidence,
    build_pit_timestamps,
    build_raw_evidence_reference,
    build_research_provenance_manifest,
)

# Reuse the unchanged WALLET-02 synthetic ledger builders, including production
# WALLET-01 persistence validation; no parallel synthetic persistence implementation.
_fixture_spec = importlib.util.spec_from_file_location(
    "wallet02_copyability_fixtures", Path(__file__).with_name("test_profile.py")
)
f = importlib.util.module_from_spec(_fixture_spec)
_fixture_spec.loader.exec_module(f)

COST = c.WalletCopyabilityCostScenario("0.01", "0.02", "0.005", "1")
SEEN = "2026-01-11T00:00:01Z"


def quote(
    *,
    at=SEEN,
    price="0.2",
    depth="10",
    token=f.TOKEN,
    condition=f.CONDITION,
    sign=1,
    observed=True,
    source="POLYMARKET_CLOB",
    manifest_cutoff=None,
    obs_overrides=None,
    raw_document=None,
    flags=("OK",),
):
    content = f.c.wallet_canonical_json_bytes(
        raw_document
        or {
            "market": condition,
            "asset_id": token,
            "asks": [{"price": price, "size": depth or "10"}],
            "bids": [{"price": price, "size": depth or "10"}],
        }
    )
    raw = build_raw_evidence_reference(
        source_system=source,
        endpoint="/book",
        retrieval_method="GET",
        request_parameters={"token_id": token},
        pit=build_pit_timestamps(local_first_seen_time=at, ingestion_time=at),
        content_sha256=sha256(content).hexdigest(),
        byte_length=len(content),
        media_type="application/json",
        dq_flags=("OK",),
        replay_fidelity="EXACT",
        raw_snapshot_ref="synthetic:retained-book",
    )
    manifest = build_research_provenance_manifest(
        repo_code_identity="synthetic-wallet03",
        information_cutoff=manifest_cutoff or at,
        input_evidence_reference_ids=(raw.raw_evidence_reference_id,),
        input_content_hashes=(raw.content_sha256,),
        output_identity="synthetic-book",
        output_hash=raw.content_sha256,
    )
    witness = c.WalletCopyabilityQuoteWitness(
        "DATA_API_RESPONSE_CONDITION_ID",
        condition,
        "CLOB_TOKEN_ID",
        token,
        sign,
        price,
        depth,
        ObservabilityEvidence(local_first_seen_time=at, **(obs_overrides or {})),
        flags,
        "EXACT",
        raw if observed else None,
        manifest if observed else None,
        content if observed else None,
    )
    return witness, (raw, manifest) if observed else ()


def case(
    tmp_path,
    *,
    quotes=None,
    events=None,
    extra_records=(),
    context_overrides=None,
    identity_observability=None,
    observations=None,
):
    if quotes is None:
        witness, records = quote()
        quotes = (witness,)
    else:
        records = tuple(
            item
            for witness in quotes
            for item in (witness.raw_reference, witness.provenance_manifest)
            if item is not None
        )
    original, path, manifest, cohort, context, head = f._profile(
        tmp_path,
        events=events,
        extra_records=(*records, *extra_records),
        context_overrides=context_overrides,
        identity_observability=identity_observability,
        observations=observations,
    )
    return dict(
        profile=original,
        wallet_ledger_path=path,
        expected_ledger_head=head,
        cohort_snapshot=cohort,
        target_wallet=f.WALLET,
        as_of=original.as_of,
        market_contexts=(context,),
        identity_observability=identity_observability,
        quote_witnesses=quotes,
        delay_seconds=("1", "5"),
        cost_scenarios=(COST,),
    )


def build(arguments, **changes):
    return c.build_wallet_copyability_research_assessment(**(arguments | changes))


def mapping(record):
    return c.wallet_copyability_research_assessment_to_mapping(record)


def rehash(data):
    data = deepcopy(data)
    data.pop("wallet_copyability_research_assessment_id", None)
    data["wallet_copyability_research_assessment_id"] = (
        "walletcopyability:sha256:"
        + sha256(f.c.wallet_canonical_json_bytes(data)).hexdigest()
    )
    return data


def test_wallet03_verified_profile_ledger(tmp_path):
    arguments = case(tmp_path)
    before = Path(arguments["wallet_ledger_path"]).read_bytes()
    result = build(arguments)
    assert result.wallet_ledger_head_hash == arguments["expected_ledger_head"]
    assert result.delay_results[0].status == "OBSERVABLE_CONDITIONAL"
    assert result.delay_results[0].best_scenario_price_difference_after_costs == "0.015"
    assert Path(arguments["wallet_ledger_path"]).read_bytes() == before
    original = arguments["profile"]
    fabricated_skill = replace(
        original.directional_skill, mean_signed_entry_residual="0.125"
    )
    fabricated = replace(
        original,
        directional_skill=fabricated_skill,
        scope_cells=tuple(
            replace(
                cell,
                directional_skill=replace(
                    cell.directional_skill, mean_signed_entry_residual="0.125"
                ),
            )
            for cell in original.scope_cells
        ),
        wallet_profile_snapshot_id="",
    )
    fabricated = replace(
        fabricated,
        wallet_profile_snapshot_id="walletprofile:sha256:"
        + sha256(
            f.c.wallet_canonical_json_bytes(fabricated.logical_preimage())
        ).hexdigest(),
    )
    assert (
        f.p.wallet_profile_snapshot_from_mapping(
            f.p.wallet_profile_snapshot_to_mapping(fabricated)
        )
        == fabricated
    )
    with pytest.raises(c.WalletCopyabilityError, match="COPYABILITY_PROFILE_MISMATCH"):
        build(arguments, profile=fabricated)


@pytest.mark.parametrize(
    "change",
    ["missing", "foreign", "head", "cutoff", "context", "cohort", "target", "tamper"],
)
def test_source_binding_negatives(tmp_path, change):
    arguments = case(tmp_path / "original")
    if change == "missing":
        arguments["wallet_ledger_path"] = tmp_path / "absent.sqlite"
    elif change == "foreign":
        arguments["wallet_ledger_path"] = case(
            tmp_path / "foreign", events=[f._event(native="foreign-2")]
        )["wallet_ledger_path"]
    elif change == "head":
        arguments["expected_ledger_head"] = "0" * 64
    elif change == "cutoff":
        arguments["as_of"] = "2026-03-02T00:00:00Z"
    elif change == "context":
        arguments["market_contexts"] = (f._context(f._manifest(), category="changed"),)
    elif change == "cohort":
        arguments["cohort_snapshot"] = f._cohort(
            f._manifest(), cutoff="2026-01-04T00:00:00Z"
        )
    elif change == "target":
        arguments["target_wallet"] = f.CONTROL
    else:
        Path(arguments["wallet_ledger_path"]).write_bytes(b"not a sqlite ledger")
    with pytest.raises(c.WalletCopyabilityError):
        build(arguments)


def test_changed_ledger_and_drift_between_reads(tmp_path, monkeypatch):
    arguments = case(tmp_path)
    loader = c.load_and_verify_wallet_evidence_ledger
    original = loader(arguments["wallet_ledger_path"])
    calls = []

    def drift(path):
        calls.append(path)
        return (
            original
            if len(calls) == 1
            else replace(
                original, snapshot=replace(original.snapshot, head_hash="0" * 64)
            )
        )

    monkeypatch.setattr(c, "load_and_verify_wallet_evidence_ledger", drift)
    with pytest.raises(c.WalletCopyabilityError, match="COPYABILITY_SOURCE_DRIFT"):
        build(arguments)
    monkeypatch.setattr(c, "load_and_verify_wallet_evidence_ledger", loader)
    assert f.ledger.append_wallet_evidence_records(
        arguments["wallet_ledger_path"], [f._event(native="new-2")]
    ).is_valid
    with pytest.raises(c.WalletCopyabilityError, match="COPYABILITY_SOURCE_DRIFT"):
        build(arguments)


def test_wallet03_pit_observability(tmp_path):
    arguments = case(tmp_path)
    result = build(arguments)
    assert result.event_evidence[0].observed_at == "2026-01-11T00:00:00Z"
    assert result.delay_results[0].independently_observable_quote_count == 1
    assert result.delay_results[1].status == "UNOBSERVABLE"
    # An apparent quote at event_time + delay predates wallet-action observation.
    earlier, _ = quote(at="2026-01-10T00:00:01Z")
    early_case = case(tmp_path / "early", quotes=(earlier,))
    assert build(early_case).delay_results[0].status == "UNOBSERVABLE"
    for name, witness in (
        ("late", quote(at="2026-04-01T00:00:00Z")[0]),
        ("future", quote(manifest_cutoff="2026-02-01T00:00:00Z")[0]),
        ("resolved", quote(at="2026-02-02T00:00:00Z")[0]),
        ("foreign_token", quote(token="8")[0]),
        ("foreign_market", quote(condition="0xdef")[0]),
        ("backfilled", quote(obs_overrides={"is_backfilled": True})[0]),
        ("correction", quote(obs_overrides={"is_correction_after_cutoff": True})[0]),
        ("uncertain", quote(obs_overrides={"decisive_clock_uncertain": True})[0]),
    ):
        record = build(case(tmp_path / name, quotes=(witness,)))
        assert record.delay_results[0].independently_observable_quote_count == 0
        assert record.delay_results[0].scenario_differences == ()


def test_source_without_binding_stays_scenario_only(tmp_path):
    witness, _ = quote(observed=False)
    record = build(case(tmp_path / "scenario", quotes=(witness,)))
    assert record.delay_results[0].status == "SCENARIO_ONLY"
    assert record.delay_results[0].independently_observable_quote_count == 0
    assert record.delay_results[0].best_scenario_price_difference_after_costs == "0.015"
    arguments = case(tmp_path / "unbound")
    other, _ = quote(price="0.3")
    assert (
        build(arguments, quote_witnesses=(other,)).delay_results[0].status
        == "SCENARIO_ONLY"
    )
    unknown_time = replace(
        witness, observability=ObservabilityEvidence(event_time=SEEN)
    )
    assert (
        build(arguments, quote_witnesses=(unknown_time,)).delay_results[0].status
        == "UNOBSERVABLE"
    )


@pytest.mark.parametrize(
    "change",
    [
        "content",
        "price",
        "depth",
        "clock",
        "request",
        "market",
        "duplicate",
        "raw_duplicate",
    ],
)
def test_quote_source_binding_rejects_mismatch(tmp_path, change):
    arguments = case(tmp_path)
    witness = arguments["quote_witnesses"][0]
    if change == "content":
        witness = replace(witness, raw_content=b"{}")
    elif change == "price":
        witness = replace(witness, price="0.4")
    elif change == "depth":
        witness = replace(witness, top_level_depth_shares="11")
    elif change == "clock":
        witness = replace(
            witness,
            observability=ObservabilityEvidence(
                local_first_seen_time="2026-01-11T00:00:02Z"
            ),
        )
    elif change == "market":
        witness = replace(witness, condition_value="0xdef")
    elif change == "request":
        witness = replace(witness, token_value="8")
    else:
        second = (
            witness
            if change == "duplicate"
            else replace(witness, price_direction_sign=-1)
        )
        with pytest.raises(c.WalletCopyabilityError):
            build(arguments, quote_witnesses=(witness, second))
        return
    with pytest.raises(c.WalletCopyabilityError):
        build(arguments, quote_witnesses=(witness,))


def test_wallet03_explicit_delayed_costs(tmp_path):
    first, _ = quote()
    later, _ = quote(at="2026-01-11T00:00:05Z", price="0.1")
    arguments = case(tmp_path, quotes=(later, first))
    worst = c.WalletCopyabilityCostScenario("0.1", "0.1", "0.1", "2")
    record = build(arguments, cost_scenarios=(COST, worst))
    assert record.delay_results[0].best_scenario_price_difference_after_costs == "0.015"
    assert (
        record.delay_results[0].worst_scenario_price_difference_after_costs == "-0.25"
    )
    assert record.delay_results[1].best_scenario_price_difference_after_costs == "0.115"
    for field in fields(COST):
        missing = replace(COST, **{field.name: None})
        result = build(arguments, cost_scenarios=(missing,)).delay_results[0]
        assert result.status == "INSUFFICIENT_CONTEXT"
        assert result.best_scenario_price_difference_after_costs is None
    for depth, expected in ((None, "MISSING_DEPTH"), ("0", "INSUFFICIENT_DEPTH")):
        scenario_witness = replace(
            first,
            raw_reference=None,
            provenance_manifest=None,
            raw_content=None,
            top_level_depth_shares=depth,
        )
        result = build(arguments, quote_witnesses=(scenario_witness,)).delay_results[0]
        assert result.outcome_reason_counts == ((expected, 1),)
    negative = replace(first, price_direction_sign=-1)
    sell_case = case(
        tmp_path / "sell", events=[f._event(side="SELL")], quotes=(negative,)
    )
    assert (
        build(sell_case).delay_results[0].best_scenario_price_difference_after_costs
        == "-0.085"
    )


@pytest.mark.parametrize(
    "bad",
    [
        0.1,
        -1,
        "-0.1",
        "NaN",
        "Infinity",
        "1e-3",
        "0.10",
        "-0",
        True,
        "0.1 bps",
        "0.0000000000000000001",
    ],
)
def test_rejects_noncanonical_costs_and_delays(tmp_path, bad):
    arguments = case(tmp_path)
    with pytest.raises(c.WalletCopyabilityError):
        build(arguments, cost_scenarios=(replace(COST, taker_fee_per_share=bad),))
    with pytest.raises(c.WalletCopyabilityError):
        build(arguments, delay_seconds=(bad,))


def test_decimal_clock_direction_and_earliest_conflicts(tmp_path):
    before, _ = quote(at="2026-01-11T00:00:00.000001Z", observed=False)
    after, _ = quote(at="2026-01-11T00:00:01Z", observed=False)
    arguments = case(tmp_path, quotes=(after, before))
    assert (
        build(arguments, delay_seconds=("0.000001",))
        .delay_results[0]
        .selected_quote_ids
    )
    with pytest.raises(c.WalletCopyabilityError):
        build(arguments, delay_seconds=("0.0000001",))
    conflicting, _ = quote(price="0.3", observed=False)
    result = build(arguments, quote_witnesses=(after, conflicting)).delay_results[0]
    assert result.status == "INSUFFICIENT_CONTEXT"
    assert result.outcome_reason_counts == (("CONTRADICTORY_QUOTES", 1),)
    assert result.scenario_differences == ()


def test_wallet03_reconciliation_denominators(tmp_path):
    api = f._event(native="api-1")
    chain = f._event(native="2", strength="CHAIN_NATIVE_STRONG")
    reward = f._event(native="reward-3", event_type="REWARD", price=None, side=None)
    ambiguous = f._event(native="weak-4", strength="WEAK_PARTIAL")
    duplicate = f.c.build_wallet_reconciliation_link(
        reconciliation_state="API_AND_CHAIN_CONFIRMED",
        relation_kind="CHAIN_CONFIRMATION",
        event_ids=(api.wallet_event_id, chain.wallet_event_id),
        finality_state="CONFIRMED",
    )
    result = build(
        case(
            tmp_path, events=[api, chain, reward, ambiguous], extra_records=(duplicate,)
        )
    ).delay_results[0]
    assert result.considered_event_count == 4
    assert result.eligible_event_count == 1
    assert (
        sum(count for _, count in result.excluded_reason_counts)
        + result.eligible_event_count
        == 4
    )
    assert sum(count for _, count in result.outcome_reason_counts) == 1
    for state, relation in (
        ("SOURCE_DISAGREEMENT", "DISAGREEMENT"),
        ("REORGED_OR_REMOVED", "REORG_REMOVAL"),
    ):
        link = f.c.build_wallet_reconciliation_link(
            reconciliation_state=state,
            relation_kind=relation,
            event_ids=(api.wallet_event_id,),
        )
        assert (
            build(case(tmp_path / state, events=[api], extra_records=(link,)))
            .delay_results[0]
            .eligible_event_count
            == 0
        )


def test_supersession_and_related_account_equivalence(tmp_path):
    original, successor = f._event(native="old-1"), f._event(native="new-2")
    link = f.c.build_wallet_reconciliation_link(
        reconciliation_state="SUPERSEDED_BY_STRONGER_EVIDENCE",
        relation_kind="SUPERSESSION",
        event_ids=(original.wallet_event_id, successor.wallet_event_id),
        predecessor_event_id=original.wallet_event_id,
        successor_event_id=successor.wallet_event_id,
    )
    assert (
        build(
            case(
                tmp_path / "superseded",
                events=[original, successor],
                extra_records=(link,),
            )
        )
        .delay_results[0]
        .eligible_event_count
        == 1
    )
    related = f._event(wallet=f.RELATED, native="related-3")
    identity = f.c.build_wallet_account_identity_evidence(
        canonical_wallet=f.WALLET,
        generic_account_role="ACCOUNT_WALLET",
        polymarket_wallet_type="EOA",
        evidence_link_class="ONCHAIN_CONFIRMED",
        related_account=f.RELATED,
        source_reference="chain:synthetic",
        effective_start="2026-01-01T00:00:00Z",
    )
    equivalent = f.c.build_wallet_reconciliation_link(
        reconciliation_state="API_AND_CHAIN_CONFIRMED",
        relation_kind="SAME_EVENT_EQUIVALENCE",
        event_ids=(original.wallet_event_id, related.wallet_event_id),
        finality_state="CONFIRMED",
    )
    arguments = case(
        tmp_path / "related",
        events=[original, related],
        extra_records=(identity, equivalent),
        identity_observability={
            identity.wallet_account_identity_evidence_id: f._obs("2026-01-03T00:00:00Z")
        },
    )
    assert build(arguments).delay_results[0].eligible_event_count == 1


def test_missing_or_future_context_and_unsupported_instrument(tmp_path):
    arguments = case(tmp_path / "missing", events=[f._event(token="8")])
    assert build(arguments).delay_results[0].status == "INSUFFICIENT_CONTEXT"
    late_context = case(
        tmp_path / "late_context",
        context_overrides={"metadata_at": "2026-02-01T00:00:00Z"},
    )
    assert build(late_context).event_evidence[0].reason == "CONTEXT_NOT_PIT"
    after_outcome = case(
        tmp_path / "outcome",
        context_overrides={"resolution_at": "2026-01-10T00:00:00Z"},
    )
    assert build(after_outcome).event_evidence[0].reason == "AFTER_OUTCOME"


def test_wallet03_stable_record_roundtrip(tmp_path):
    first, _ = quote()
    second, _ = quote(at="2026-01-11T00:00:05Z", price="0.3")
    arguments = case(tmp_path, quotes=(first, second))
    original = build(
        arguments,
        delay_seconds=("5", "1"),
        cost_scenarios=(COST, replace(COST, slippage_per_share="0")),
    )
    with localcontext() as precision:
        precision.prec = 5
        reordered = build(
            arguments,
            quote_witnesses=(second, first),
            delay_seconds=("1", "5"),
            cost_scenarios=(replace(COST, slippage_per_share="0"), COST),
        )
    assert original == reordered
    data = mapping(original)
    assert set(data) == {field.name for field in fields(original)}
    assert (
        c.wallet_copyability_research_assessment_from_mapping(
            json.loads(f.c.wallet_canonical_json_bytes(data))
        )
        == original
    )
    for mutation in (
        "extra",
        "identity",
        "count",
        "difference",
        "flag",
        "quote_extra",
        "quote_price",
        "bool_count",
    ):
        changed = deepcopy(data)
        if mutation == "extra":
            changed["untrusted_metadata"] = "SENTINEL_PRIVATE_METADATA"
        elif mutation == "identity":
            changed["wallet_copyability_research_assessment_id"] = (
                "walletcopyability:sha256:" + "0" * 64
            )
        elif mutation == "count":
            changed["delay_results"][0]["eligible_event_count"] += 1
        elif mutation == "difference":
            changed["delay_results"][0][
                "best_scenario_price_difference_after_costs"
            ] = "99"
        elif mutation == "flag":
            changed["advisory_only"] = False
        elif mutation == "quote_extra":
            changed["quote_evidence"][0]["metadata"] = "SENTINEL_PRIVATE_METADATA"
        elif mutation == "quote_price":
            changed["quote_evidence"][0]["price"] = 0.2
        else:
            changed["delay_results"][0]["independently_observable_quote_count"] = True
        if mutation not in {"identity", "quote_price"}:
            changed = rehash(changed)
        with pytest.raises(c.WalletCopyabilityError) as error:
            c.wallet_copyability_research_assessment_from_mapping(changed)
        assert "SENTINEL" not in str(error.value)


def test_wallet03_read_only_no_authority(tmp_path, monkeypatch):
    arguments = case(tmp_path)
    before = Path(arguments["wallet_ledger_path"]).read_bytes()
    originals = deepcopy(arguments)
    real_open, real_connect = builtins.open, sqlite3.connect
    queries = []

    def open_read_only(file, mode="r", *args, **kwargs):
        assert not any(flag in mode for flag in "wax+")
        return real_open(file, mode, *args, **kwargs)

    def connect_read_only(database, *args, **kwargs):
        assert "mode=ro" in database
        connection = real_connect(database, *args, **kwargs)
        connection.set_trace_callback(queries.append)
        return connection

    def forbidden(*_args, **_kwargs):
        raise AssertionError("forbidden side effect")

    monkeypatch.setattr(builtins, "open", open_read_only)
    monkeypatch.setattr(sqlite3, "connect", connect_read_only)
    for target, name in (
        (Path, "write_text"),
        (Path, "write_bytes"),
        (socket, "socket"),
        (socket, "create_connection"),
        (subprocess, "Popen"),
        (os, "getenv"),
    ):
        monkeypatch.setattr(target, name, forbidden)
    monkeypatch.setattr(f.ledger, "initialize_wallet_evidence_ledger", forbidden)
    monkeypatch.setattr(f.ledger, "append_wallet_evidence_records", forbidden)
    result = build(arguments)
    assert Path(arguments["wallet_ledger_path"]).read_bytes() == before
    assert arguments == originals
    assert queries and all(
        not query.lstrip()
        .upper()
        .startswith(("INSERT", "UPDATE", "DELETE", "CREATE", "DROP"))
        for query in queries
    )
    encoded = json.dumps(mapping(result)).lower()
    for token in (
        f.WALLET,
        '"raw_content":',
        "category_label",
        "buy",
        "sell",
        "profit",
        "expected_return",
        "trade_ready",
        "recommendation",
    ):
        assert token.lower() not in encoded
    assert (
        result.advisory_only
        and result.no_execution_authority
        and result.no_strategy_authority
        and result.no_qualification_authority
    )


def test_bounded_inputs_closed_nested_fields_and_no_echo(tmp_path, monkeypatch):
    arguments = case(tmp_path)
    for changes in (
        dict(delay_seconds=()),
        dict(delay_seconds=("1", "1")),
        dict(delay_seconds=("86401",)),
        dict(delay_seconds=tuple(str(i) for i in range(9))),
        dict(cost_scenarios=()),
        dict(cost_scenarios=(COST, COST)),
        dict(cost_scenarios=(replace(COST, required_depth_shares="0"),)),
        dict(quote_witnesses=arguments["quote_witnesses"] * 257),
        dict(profile=replace(arguments["profile"], advisory_only=False)),
    ):
        with pytest.raises(c.WalletCopyabilityError):
            build(arguments, **changes)
    record = build(arguments)
    excluded = case(
        tmp_path / "excluded",
        events=[f._event(event_type="REWARD", side=None, price=None)],
    )
    malformed = mapping(build(excluded))
    malformed["event_evidence"][0]["price_direction_sign"] = "SENTINEL_PRIVATE_METADATA"
    with pytest.raises(c.WalletCopyabilityError) as error:
        c.wallet_copyability_research_assessment_from_mapping(rehash(malformed))
    assert "SENTINEL" not in str(error.value)
    malformed = mapping(record)
    malformed["wallet_profile_snapshot_id"] = "private_identity:sha256:" + "1" * 64
    with pytest.raises(c.WalletCopyabilityError):
        c.wallet_copyability_research_assessment_from_mapping(rehash(malformed))
    monkeypatch.setattr(
        c,
        "load_and_verify_wallet_evidence_ledger",
        lambda _path: replace(
            f.ledger.load_and_verify_wallet_evidence_ledger(
                arguments["wallet_ledger_path"]
            ),
            is_valid=False,
        ),
    )
    with pytest.raises(c.WalletCopyabilityError, match="COPYABILITY_SOURCE_INVALID"):
        build(arguments)


def test_duplicate_json_dq_and_metadata_never_create_observed_evidence(tmp_path):
    witness, _ = quote()
    document = json.loads(witness.raw_content)
    document["untrusted_metadata"] = {"message": "SENTINEL_PRIVATE_METADATA"}
    with_metadata, _ = quote(raw_document=document)
    arguments = case(tmp_path / "metadata", quotes=(with_metadata,))
    assert "SENTINEL" not in json.dumps(mapping(build(arguments)))
    bad_dq = replace(with_metadata, dq_flags=("SOURCE_UNAVAILABLE",))
    assert (
        build(arguments, quote_witnesses=(bad_dq,)).delay_results[0].status
        == "UNOBSERVABLE"
    )
    unretained, _ = quote(source="SYNTHETIC_FIXTURE")
    assert (
        build(case(tmp_path / "fixture", quotes=(unretained,))).delay_results[0].status
        == "SCENARIO_ONLY"
    )
    raw_content = b'{"market":"0xabc","market":"0xabc","asset_id":"7","asks":[{"price":"0.2","size":"10"}]}'
    raw = replace(
        witness.raw_reference,
        content_sha256=sha256(raw_content).hexdigest(),
        byte_length=len(raw_content),
    )
    preimage = raw.logical_preimage()
    preimage.pop("schema_id")
    preimage.pop("schema_version")
    preimage["pit"] = build_pit_timestamps(**preimage["pit"])
    raw = build_raw_evidence_reference(**preimage)
    manifest = build_research_provenance_manifest(
        repo_code_identity="synthetic-wallet03",
        information_cutoff=SEEN,
        input_evidence_reference_ids=(raw.raw_evidence_reference_id,),
        input_content_hashes=(raw.content_sha256,),
        output_identity="synthetic-book",
        output_hash=raw.content_sha256,
    )
    duplicate = replace(
        witness,
        raw_reference=raw,
        provenance_manifest=manifest,
        raw_content=raw_content,
    )
    with pytest.raises(c.WalletCopyabilityError, match="COPYABILITY_BINDING_INVALID"):
        build(case(tmp_path / "duplicate", quotes=(duplicate,)))


def test_one_quote_reused_for_distinct_fills_is_one_observable_witness(tmp_path):
    arguments = case(
        tmp_path, events=[f._event(native="fill-1"), f._event(native="fill-2")]
    )
    result = build(arguments).delay_results[0]
    assert result.eligible_event_count == 2
    assert len(result.selected_quote_ids) == 2
    assert result.independently_observable_quote_count == 1
    assert result.outcome_reason_counts == (("OBSERVED", 2),)


@pytest.mark.parametrize(
    "field,at",
    [
        ("correction_or_revision_time", "2026-01-12T00:00:00Z"),
        ("correction_or_revision_time", "2026-04-01T00:00:00Z"),
        ("resolution_time", "2026-01-10T00:00:00Z"),
        ("resolution_time", "2026-04-01T00:00:00Z"),
    ],
)
def test_raw_provenance_clocks_cannot_be_backdated(tmp_path, field, at):
    witness, _ = quote()
    preimage = witness.raw_reference.logical_preimage()
    preimage.pop("schema_id")
    preimage.pop("schema_version")
    preimage["pit"][field] = at
    preimage["pit"] = build_pit_timestamps(**preimage["pit"])
    raw = build_raw_evidence_reference(**preimage)
    manifest = build_research_provenance_manifest(
        repo_code_identity="synthetic-wallet03",
        information_cutoff=SEEN,
        input_evidence_reference_ids=(raw.raw_evidence_reference_id,),
        input_content_hashes=(raw.content_sha256,),
        output_identity="synthetic-book",
        output_hash=raw.content_sha256,
    )
    witness = replace(witness, raw_reference=raw, provenance_manifest=manifest)
    record = build(case(tmp_path, quotes=(witness,)))
    assert record.quote_evidence[0].source_status == "PIT_NOT_ADMISSIBLE"
    assert record.delay_results[0].status == "UNOBSERVABLE"
    assert record.delay_results[0].scenario_differences == ()
