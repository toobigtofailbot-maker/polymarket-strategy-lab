import dataclasses
from dataclasses import replace
import hashlib
import inspect
import json

import pytest

from src.data_layer.polymarket import market_truth as mt
from src.data_layer.polymarket.market_truth_store import MarketTruthStore
from src.research_runtime.nautilus_offline import convert_pmxt_v2_events
from src.research_runtime.executable_edge import (
    ExecutableEdgeError,
    NativeContinuityAttestation,
    NativeMarketTruthContext,
    build_market_truth_window,
    build_native_market_truth_window,
    identify_market_truth_window,
    validate_native_continuity_attestation,
    validate_native_market_truth_window,
    validate_market_truth_window,
)
from src.research_runtime.executable_edge.models import canonical_bytes
from tests.research_runtime.nautilus_offline.test_conversion import (
    _context,
    _write_files,
    book,
    default_rows,
    price_change,
)


_SESSION = "00000000-0000-4000-8000-000000000001"
_ASSET = "7"
_CONDITION = "0x" + "a" * 64
_STREAMING_AT = "2024-07-03T09:59:59.000000Z"
_BOOK_AT = "2024-07-03T10:00:00.000000Z"
_DELTA_AT = "2024-07-03T10:00:01.000000Z"
_END_AT = "2024-07-03T10:00:02.000000Z"


def _ws_raw(sequence, received_at, body, *, session_id=_SESSION):
    return mt.make_raw_envelope(
        "WS",
        "polymarket:market-ws",
        f"ws:{session_id}:frame:{sequence}",
        received_at,
        json.dumps(body, separators=(",", ":")).encode(),
        occurrence_sequence=sequence,
    )


def _append_book(store, *, sequence=0, received_at=_BOOK_AT, bid="0.4", session_id=_SESSION):
    raw = _ws_raw(
        sequence,
        received_at,
        {
            "event_type": "book",
            "asset_id": _ASSET,
            "market": _CONDITION,
            "timestamp": "1720000000000",
            "bids": [{"price": bid, "size": "12"}],
            "asks": [{"price": "0.6", "size": "8"}],
        },
        session_id=session_id,
    )
    observations = mt.normalize_websocket_message(raw, book_readiness={})
    assert store.append(raw, observations).status == "OK"
    return observations[0]


def _append_delta(store, *, sequence=1, received_at=_DELTA_AT, session_id=_SESSION):
    raw = _ws_raw(
        sequence,
        received_at,
        {
            "event_type": "price_change",
            "market": _CONDITION,
            "timestamp": "1720000001000",
            "price_changes": [
                {"asset_id": _ASSET, "price": "0.41", "size": "5", "side": "BUY"}
            ],
        },
        session_id=session_id,
    )
    observations = mt.normalize_websocket_message(raw, book_readiness={_ASSET: True})
    assert store.append(raw, observations).status == "OK"
    return observations[0]


def _context_native(instrument_id="asset:7.POLYMARKET"):
    return NativeMarketTruthContext(instrument_id)


def _build_native(path, *, setup=None, bid="0.4", instrument_id="asset:7.POLYMARKET"):
    with MarketTruthStore(path) as store:
        store.mark_session(_SESSION, "STREAMING", _STREAMING_AT)
        first = _append_book(store, bid=bid)
        second = _append_delta(store)
        if setup is not None:
            setup(store)
        window = build_native_market_truth_window(
            store,
            asset_id=_ASSET,
            start_received_at=_BOOK_AT,
            end_received_at=_END_AT,
            context=_context_native(instrument_id),
        )
    return window, first, second


def test_wp168_adapter_preserves_lineage_order_book_trade_and_continuity(tmp_path) -> None:
    source = _write_files(tmp_path / "source", [default_rows()])
    window = build_market_truth_window(source, _context())
    assert window.lineage_id.startswith("markettruthwindow:sha256:")
    assert window.source_external_dataset_id == source.descriptor.external_dataset_id
    assert window.continuity_complete is True
    assert tuple(event.kind for event in window.events) == ("BOOK", "BOOK", "TRADE", "BOOK")
    assert window.events[0].asks == (("0.6", "50"),)
    assert window.events[1].bids == (("0.41", "10"), ("0.4", "50"))
    assert window.events[3].asks == (("0.585", "7"), ("0.6", "50"))
    assert window.first_receive_time_ns <= window.last_receive_time_ns
    assert window.advisory_only and window.no_execution_authority
    with pytest.raises(ExecutableEdgeError, match="MARKET_TRUTH_INVALID"):
        validate_market_truth_window(replace(window, continuity_complete=False))
    gapped = replace(source, descriptor=replace(source.descriptor, known_gap_policy="KNOWN_GAPS"))
    assert build_market_truth_window(gapped, _context()).continuity_complete is False
    as_captured = replace(source, descriptor=replace(source.descriptor, known_gap_policy="AS_CAPTURED"))
    assert build_market_truth_window(as_captured, _context()).continuity_complete is False


def test_wp168_adapter_replays_incremental_update_and_delete(tmp_path) -> None:
    rows = [
        book(
            1000,
            1005,
            [["0.4000", "10.000000"], ["0.3900", "5.000000"]],
            [["0.6000", "20.000000"]],
        ),
        price_change(1001, 1006, "0.4000", "7.000000", "BUY"),
        price_change(1002, 1007, "0.3900", "0.000000", "BUY"),
    ]
    source = _write_files(tmp_path / "incremental", [rows])
    window = build_market_truth_window(source, _context())

    assert tuple(event.kind for event in window.events) == ("BOOK", "BOOK", "BOOK")
    assert window.events[0].bids == (("0.4", "10"), ("0.39", "5"))
    assert window.events[1].bids == (("0.4", "7"), ("0.39", "5"))
    assert window.events[2].bids == (("0.4", "7"),)
    assert window.ordered_event_digests == convert_pmxt_v2_events(
        source, _context()
    ).ordered_event_digests


def test_wp172_boundary_and_repo_truth() -> None:
    from pathlib import Path
    source = "\n".join(
        path.read_text(encoding="utf-8").lower()
        for path in Path("src/research_runtime/executable_edge").glob("*.py")
    )
    for forbidden in ("import requests", "import httpx", "import websocket", "api_key", "private_key", "submit_order", "cancel_order"):
        assert forbidden not in source


def test_native_complete_window_is_store_derived_path_free_and_float_free(tmp_path) -> None:
    window, first, second = _build_native(tmp_path / "native.sqlite3")
    assert window.continuity_complete is True
    assert window.ordered_observation_ids == (first.observation_id, second.observation_id)
    assert window.events[0].bids == (("0.4", "12"),)
    assert window.events[1].bids == (("0.41", "5"), ("0.4", "12"))
    assert window.source_capture_id.startswith("nativecapture:sha256:")
    assert str(tmp_path) not in repr(window)
    assert window.continuity_attestation_id == window.continuity_attestation.attestation_id
    validate_native_continuity_attestation(window.continuity_attestation)
    validate_native_market_truth_window(window)
    expected_ns = 1_720_000_000_000_000_000
    assert window.events[0].event_time_ns == expected_ns


def test_native_caller_cannot_supply_capture_or_continuity_authority(tmp_path) -> None:
    context_parameters = inspect.signature(NativeMarketTruthContext).parameters
    builder_parameters = inspect.signature(build_native_market_truth_window).parameters
    attestation_parameters = inspect.signature(NativeContinuityAttestation).parameters
    assert "source_capture_id" not in context_parameters
    assert "continuity_complete" not in builder_parameters
    assert "continuity_complete" not in attestation_parameters
    window, _, _ = _build_native(tmp_path / "authority.sqlite3")
    tampered = replace(window.continuity_attestation, gap_open_count=1)
    with pytest.raises(ExecutableEdgeError, match="NATIVE_MARKET_TRUTH_INVALID"):
        validate_native_continuity_attestation(tampered)
    malformed = replace(window.continuity_attestation, session_id=object())
    with pytest.raises(ExecutableEdgeError) as failure:
        validate_native_continuity_attestation(malformed)
    assert str(failure.value) == "NATIVE_MARKET_TRUTH_INVALID"
    with pytest.raises(ExecutableEdgeError, match="NATIVE_MARKET_TRUTH_INVALID"):
        validate_native_market_truth_window(replace(window, continuity_complete=False))
    with pytest.raises(ExecutableEdgeError) as window_failure:
        validate_native_market_truth_window(replace(window, events=(object(),)))
    assert str(window_failure.value) == "NATIVE_MARKET_TRUTH_INVALID"


def test_native_requires_initial_full_ready_snapshot(tmp_path) -> None:
    with MarketTruthStore(tmp_path / "no-snapshot.sqlite3") as store:
        store.mark_session(_SESSION, "STREAMING", _STREAMING_AT)
        _append_delta(store, sequence=0, received_at=_BOOK_AT)
        with pytest.raises(ExecutableEdgeError, match="NATIVE_MARKET_TRUTH_INVALID"):
            build_native_market_truth_window(
                store,
                asset_id=_ASSET,
                start_received_at=_BOOK_AT,
                end_received_at=_END_AT,
                context=_context_native(),
            )


@pytest.mark.parametrize(
    "reason",
    (
        "DISCONNECT",
        "TIMESTAMP_REGRESSION",
        "HASH_CONFLICT",
        "PARSE_FAULT",
        "QUEUE_OVERFLOW",
        "STORAGE_FAILURE",
        "REORG",
    ),
)
def test_native_open_or_interval_gap_is_never_complete(tmp_path, reason) -> None:
    def gap(store):
        store.mark_gap(_ASSET, "OPEN", reason, _DELTA_AT)

    window, _, _ = _build_native(tmp_path / f"gap-{reason}.sqlite3", setup=gap)
    assert window.continuity_complete is False


def test_native_reconnect_and_session_boundary_are_never_complete(tmp_path) -> None:
    for state in ("RECONNECT_WAIT", "CONNECTING", "FAILED", "STREAMING"):
        def transition(store, state=state):
            store.mark_session(_SESSION, state, _DELTA_AT)

        window, _, _ = _build_native(tmp_path / f"session-{state}.sqlite3", setup=transition)
        assert window.continuity_complete is False


def test_native_healed_gap_allows_only_a_fresh_later_epoch(tmp_path) -> None:
    path = tmp_path / "healed.sqlite3"
    with MarketTruthStore(path) as store:
        store.mark_session(_SESSION, "STREAMING", "2024-07-03T09:59:00.000000Z")
        store.mark_gap(_ASSET, "OPEN", "DISCONNECT", "2024-07-03T09:59:30.000000Z")
        store.mark_gap(_ASSET, "HEALED", "DISCONNECT", "2024-07-03T09:59:40.000000Z")
        _append_book(store)
        _append_delta(store)
        later = build_native_market_truth_window(
            store,
            asset_id=_ASSET,
            start_received_at=_BOOK_AT,
            end_received_at=_END_AT,
            context=_context_native(),
        )
        assert later.continuity_complete is True
        assert later.continuity_attestation.gap_open_count == 1
        assert later.continuity_attestation.gap_healed_count == 1

        overlapping = build_native_market_truth_window(
            store,
            asset_id=_ASSET,
            start_received_at="2024-07-03T09:59:35.000000Z",
            end_received_at=_END_AT,
            context=_context_native(),
        )
        assert overlapping.continuity_complete is False


def test_native_excludes_quarantined_unsupported_and_non_ws_records(tmp_path) -> None:
    path = tmp_path / "excluded.sqlite3"
    with MarketTruthStore(path) as store:
        store.mark_session(_SESSION, "STREAMING", _STREAMING_AT)
        book_observation = _append_book(store)

        unsupported_raw = _ws_raw(
            1,
            _DELTA_AT,
            {"event_type": "future_unknown", "asset_id": _ASSET},
        )
        unsupported = mt.normalize_websocket_message(unsupported_raw, book_readiness={})
        assert unsupported[0].status == "UNSUPPORTED"
        assert store.append(unsupported_raw, unsupported).status == "OK"

        api_raw = mt.make_raw_envelope(
            "DATA",
            "polymarket:data-api:trades",
            "http:trades:offset:0:attempt:0",
            _DELTA_AT,
            json.dumps(
                {
                    "conditionId": _CONDITION,
                    "asset": _ASSET,
                    "price": "0.5",
                    "size": "1",
                    "side": "BUY",
                    "transactionHash": "0x" + "b" * 64,
                    "timestamp": 1720000001,
                }
            ).encode(),
            occurrence_sequence=0,
        )
        api_observation = mt.normalize_public_record(api_raw, endpoint="trades", record_index=0)
        assert store.append(api_raw, (api_observation,)).status == "OK"
        window = build_native_market_truth_window(
            store,
            asset_id=_ASSET,
            start_received_at=_BOOK_AT,
            end_received_at=_END_AT,
            context=_context_native(),
        )
    assert window.ordered_observation_ids == (book_observation.observation_id,)
    assert tuple(event.kind for event in window.events) == ("BOOK",)


def test_native_identity_binds_observations_and_continuity_evidence(tmp_path) -> None:
    first, _, _ = _build_native(tmp_path / "first.sqlite3", bid="0.4")
    changed_observation, _, _ = _build_native(tmp_path / "changed.sqlite3", bid="0.39")
    assert first.lineage_id != changed_observation.lineage_id
    assert first.ordered_observation_ids != changed_observation.ordered_observation_ids

    def historical_gap(store):
        store.mark_gap(_ASSET, "OPEN", "DISCONNECT", "2024-07-03T09:59:10.000000Z")
        store.mark_gap(_ASSET, "HEALED", "DISCONNECT", "2024-07-03T09:59:20.000000Z")

    changed_evidence, _, _ = _build_native(
        tmp_path / "changed-evidence.sqlite3", setup=historical_gap
    )
    assert changed_evidence.continuity_complete is True
    assert (
        first.continuity_attestation_id
        != changed_evidence.continuity_attestation_id
    )
    assert first.lineage_id != changed_evidence.lineage_id


def test_existing_pmxt_field_set_and_identity_preimage_remain_exact(tmp_path) -> None:
    source = _write_files(tmp_path / "pmxt-exact", [default_rows()])
    window = build_market_truth_window(source, _context())
    assert tuple(field.name for field in dataclasses.fields(type(window))) == (
        "lineage_id",
        "source_external_dataset_id",
        "instrument_id",
        "conversion_policy_version",
        "ordered_event_digests",
        "known_gap_policy",
        "continuity_complete",
        "first_receive_time_ns",
        "last_receive_time_ns",
        "events",
        "advisory_only",
        "no_execution_authority",
    )
    preimage = {
        "source_external_dataset_id": window.source_external_dataset_id,
        "conversion_policy_version": window.conversion_policy_version,
        "instrument_id": window.instrument_id,
        "ordered_event_digests": list(window.ordered_event_digests),
        "known_gap_policy": window.known_gap_policy,
        "events": [dataclasses.asdict(event) for event in window.events],
    }
    expected = "markettruthwindow:sha256:" + hashlib.sha256(canonical_bytes(preimage)).hexdigest()
    assert window.lineage_id == expected == identify_market_truth_window(window)
