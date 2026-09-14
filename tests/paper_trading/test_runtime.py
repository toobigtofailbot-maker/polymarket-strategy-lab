import hashlib
import json
from dataclasses import replace
import sqlite3

import pytest

from src.data_layer.polymarket import market_truth as mt
from src.data_layer.polymarket.market_truth_store import MarketTruthStore
from src.paper_trading import (
    LiveStoreRuntime,
    PaperEngine,
    PaperMarketEvent,
    PaperStore,
    PaperTradingError,
    Wp169ReadOnlyTail,
    build_paper_intent,
    run_replay,
    run_wp172_replay,
)
from tests.data_layer.polymarket.test_market_truth_models_store import _book_raw

from tests.paper_trading.conftest import (
    edge_stack,
    generous_limits,
    make_engine,
    paper_book,
)


def _intent(binding):
    return build_paper_intent(
        binding,
        market_id="market:a",
        asset_id="asset:a",
        side="BUY",
        quantity="2",
        order_style="AGGRESSIVE_TAKER",
        reference_price="0.5",
        decision_time_ns=101,
    )


_RESOLUTION_MARKET = "0x" + "a" * 64
_RESOLUTION_A = "7"
_RESOLUTION_B = "8"


def _market_event(kind, asset, receive, *, size=None):
    if kind == "BOOK":
        return PaperMarketEvent(
            "BOOK",
            _RESOLUTION_MARKET,
            asset,
            receive - 1,
            receive,
            f"resolution-fixture:{asset}:{receive}",
            (("0.49", "20"),),
            (("0.51", "20"),),
        )
    return PaperMarketEvent(
        "TRADE",
        _RESOLUTION_MARKET,
        asset,
        receive - 1,
        receive,
        f"resolution-fixture:{asset}:{receive}",
        side="SELL",
        price="0.49",
        size=size,
    )


def _passive_intent(engine, asset, decision, *, quantity="2"):
    return build_paper_intent(
        engine.state.binding,
        market_id=_RESOLUTION_MARKET,
        asset_id=asset,
        side="BUY",
        quantity=quantity,
        order_style="PASSIVE_MAKER",
        reference_price="0.49",
        decision_time_ns=decision,
    )


def _stored_resolution(tmp_path, name, overrides=None, *, tamper_raw=False):
    message = {
        "event_type": "market_resolved",
        "market": _RESOLUTION_MARKET,
        "condition_id": _RESOLUTION_MARKET,
        "timestamp": "1720000005000",
        "assets_ids": [_RESOLUTION_A, _RESOLUTION_B],
        "winning_asset_id": _RESOLUTION_A,
        "winning_outcome": "Yes",
        "hash": "official-resolution-hash",
    }
    if overrides:
        message.update(overrides)
    if overrides and overrides.get("winning_asset_id") == "__MISSING__":
        message.pop("winning_asset_id")
    frame = [
        {
            "event_type": "tick_size_change",
            "market": _RESOLUTION_MARKET,
            "asset_id": _RESOLUTION_B,
            "timestamp": "1720000004000",
            "old_tick_size": "0.01",
            "new_tick_size": "0.001",
        },
        message,
    ]
    raw = mt.make_raw_envelope(
        "WS",
        "polymarket:market-ws",
        "ws:00000000-0000-4000-8000-000000000000:frame:5",
        "2024-07-03T09:46:45.000000Z",
        json.dumps(frame).encode(),
        occurrence_sequence=5,
    )
    path = tmp_path / name
    with MarketTruthStore(path) as source:
        observations = mt.normalize_websocket_message(raw, book_readiness={})
        assert len(observations) == 2
        assert observations[1].event_kind == "market_resolved"
        assert source.append(raw, observations).status == "OK"
    if tamper_raw:
        connection = sqlite3.connect(path)
        connection.execute(
            "UPDATE raw_occurrences SET raw_bytes=? WHERE occurrence_id=?",
            (b"{}", raw.occurrence_id),
        )
        connection.commit()
        connection.close()
    events = Wp169ReadOnlyTail(path).read_new()
    return next(event for event in events if event.kind == "RESOLUTION")


def test_replay_is_deterministic_and_wp169_tail_is_read_only(tmp_path) -> None:
    model, _exp, _evidence, _trace, _window, assessment, binding = edge_stack()
    final_states = []
    journals = []
    for name in ("one.sqlite3", "two.sqlite3"):
        with PaperStore(tmp_path / name, create=True) as store:
            engine = PaperEngine.create(
                store,
                binding,
                generous_limits(),
                assessment=assessment,
                cost_model=model,
                session_label="same",
                created_time_ns=1,
            )
            run_replay(
                engine,
                market_events=(paper_book(100), paper_book(111)),
                intents=(_intent(binding),),
            )
            final_states.append(engine.state)
            journals.append(tuple((e.event_id, e.event_hash) for e in store.events()))
    assert final_states[0] == final_states[1]
    assert journals[0] == journals[1]

    market = tmp_path / "market.sqlite3"
    with MarketTruthStore(market) as source:
        raw = _book_raw()
        source.append(raw, mt.normalize_websocket_message(raw, book_readiness={}))
    before = hashlib.sha256(market.read_bytes()).hexdigest()
    tail = Wp169ReadOnlyTail(market)
    events = tail.read_new()
    assert len(events) == 1 and events[0].kind == "BOOK"
    assert events[0].bids == (("0.4", "12"),) and events[0].asks == (("0.6", "8"),)
    assert tail.read_new() == ()
    assert before == hashlib.sha256(market.read_bytes()).hexdigest()
    assert "mode=ro" in (
        tmp_path.parents[1] / "nonexistent"
    ).name or "mode=ro" in __import__("inspect").getsource(Wp169ReadOnlyTail)


def test_official_wp169_resolution_settles_positions_and_survives_restart(
    tmp_path,
) -> None:
    model, _exp, _evidence, _trace, _window, assessment, binding = edge_stack(
        "PASSIVE_MAKER"
    )
    paper = tmp_path / "resolution-paper.sqlite3"
    store = PaperStore(paper, create=True)
    engine = PaperEngine.create(
        store,
        binding,
        generous_limits(),
        assessment=assessment,
        cost_model=model,
        session_label="official-resolution",
        created_time_ns=1,
    )
    engine.process_market_event(_market_event("BOOK", _RESOLUTION_A, 100))
    engine.process_market_event(_market_event("BOOK", _RESOLUTION_B, 101))
    engine.submit(_passive_intent(engine, _RESOLUTION_A, 102))
    engine.submit(_passive_intent(engine, _RESOLUTION_B, 103))
    engine.process_market_event(_market_event("BOOK", _RESOLUTION_A, 112))
    engine.process_market_event(_market_event("BOOK", _RESOLUTION_B, 113))
    engine.process_market_event(
        _market_event("TRADE", _RESOLUTION_A, 114, size="22")
    )
    engine.process_market_event(
        _market_event("TRADE", _RESOLUTION_B, 115, size="22")
    )
    open_order = engine.submit(_passive_intent(engine, _RESOLUTION_A, 116))
    assert open_order.status == "OPEN"
    assert {position.asset_id for position in engine.state.account.positions} == {
        _RESOLUTION_A,
        _RESOLUTION_B,
    }

    resolution = _stored_resolution(tmp_path, "official-resolution.sqlite3")
    assert resolution.asset_id is None
    assert resolution.winner_asset_id == _RESOLUTION_A
    engine.process_market_event(resolution)

    settled_order = next(
        order for order in engine.state.orders if order.order_id == open_order.order_id
    )
    assert settled_order.status == "CANCELLED"
    assert engine.state.account.positions == ()
    assert engine.state.account.cash == "100.0204"
    assert engine.state.account.realized_pnl == "0.0204"
    assert engine.state.resolution_pending == ()
    settlements = {
        event.data["asset_id"]: event.data["payoff"]
        for event in store.events()
        if event.event_type == "POSITION_SETTLED"
    }
    assert settlements == {_RESOLUTION_A: "1", _RESOLUTION_B: "0"}
    expected_state = engine.state
    expected_journal = tuple(store.events())
    store.close()

    with PaperStore(paper) as reopened:
        recovered = PaperEngine.open(reopened)
        assert recovered.state == expected_state
        assert tuple(reopened.events()) == expected_journal


@pytest.mark.parametrize(
    ("name", "overrides", "tamper_raw"),
    (
        ("missing", {"winning_asset_id": "__MISSING__"}, False),
        ("malformed", {"winning_asset_id": 7}, False),
        (
            "contradictory",
            {"assets_ids": [_RESOLUTION_B], "winning_asset_id": _RESOLUTION_A},
            False,
        ),
        ("unvalidated-raw", {}, True),
    ),
)
def test_unverifiable_wp169_resolution_remains_pending(
    tmp_path, name, overrides, tamper_raw
) -> None:
    event = _stored_resolution(
        tmp_path,
        f"resolution-{name}.sqlite3",
        overrides,
        tamper_raw=tamper_raw,
    )
    assert event.kind == "RESOLUTION"
    assert event.winner_asset_id is None

    store, engine = make_engine(tmp_path / f"paper-{name}.sqlite3")
    engine.process_market_event(event)
    assert _RESOLUTION_MARKET in engine.state.resolution_pending
    assert engine.state.account.positions == ()
    store.close()


def test_validated_unambiguous_legacy_resolution_remains_supported(tmp_path) -> None:
    event = _stored_resolution(
        tmp_path,
        "resolution-legacy.sqlite3",
        {
            "winning_asset_id": "__MISSING__",
            "asset_id": _RESOLUTION_A,
            "winner": _RESOLUTION_A,
        },
    )
    assert event.asset_id == _RESOLUTION_A
    assert event.winner_asset_id == _RESOLUTION_A


def test_wp169_tail_resumes_without_duplicate_events_after_paper_restart(tmp_path) -> None:
    market = tmp_path / "market.sqlite3"
    with MarketTruthStore(market) as source:
        raw = _book_raw()
        source.append(raw, mt.normalize_websocket_message(raw, book_readiness={}))

    model, _exp, _ev, _trace, _window, assessment, binding = edge_stack()
    paper = tmp_path / "paper.sqlite3"
    with PaperStore(paper, create=True) as store:
        engine = PaperEngine.create(
            store, binding, generous_limits(), assessment=assessment,
            cost_model=model, session_label="restart", created_time_ns=1,
        )
        first = Wp169ReadOnlyTail(market).read_new()
        assert len(first) == 1
        engine.process_market_event(first[0])

    with MarketTruthStore(market) as source:
        update = mt.make_raw_envelope(
            "WS", "polymarket:market-ws",
            "ws:00000000-0000-4000-8000-000000000000:frame:2",
            "2024-07-03T09:46:42.000000Z",
            json.dumps(
                {
                    "event_type": "price_change",
                    "market": "0x" + "a" * 64,
                    "timestamp": "1720000002000",
                    "price_changes": [
                        {"asset_id": "7", "price": "0.5", "size": "1", "side": "BUY"}
                    ],
                }
            ).encode(),
            occurrence_sequence=2,
        )
        source.append(update, mt.normalize_websocket_message(update, book_readiness={"7": True}))

    with PaperStore(paper) as store:
        engine = PaperEngine.open(store)
        processed = tuple(
            event.data["lineage"]
            for event in store.events()
            if event.event_type == "MARKET_EVENT"
        )
        tail = Wp169ReadOnlyTail(market, processed_lineages=processed)
        new_events = tail.read_new()
        assert len(new_events) == 1 and new_events[0].lineage not in processed
        engine.process_market_event(new_events[0])
        assert engine.state.last_market_receive_ns == new_events[0].receive_time_ns
        assert tail.read_new() == ()


def test_live_store_detects_external_paper_head_change_without_market_event(
    tmp_path,
) -> None:
    market = tmp_path / "empty-market.sqlite3"
    with MarketTruthStore(market):
        pass
    model, _exp, _ev, _trace, _window, assessment, binding = edge_stack()
    paper = tmp_path / "concurrent-paper.sqlite3"
    store_a = PaperStore(paper, create=True)
    engine_a = PaperEngine.create(
        store_a,
        binding,
        generous_limits(),
        assessment=assessment,
        cost_model=model,
        session_label="live-concurrency",
        created_time_ns=1,
    )
    runtime = LiveStoreRuntime(engine_a, Wp169ReadOnlyTail(market))
    store_b = PaperStore(paper)
    engine_b = PaperEngine.open(store_b)
    engine_b.pause(101)
    committed = tuple(store_b.events())

    with pytest.raises(PaperTradingError, match="STALE_PAPER_STATE"):
        runtime.poll_once()
    assert engine_a.state.control_state == "RECONCILIATION_BLOCKED"
    assert tuple(store_b.events()) == committed

    store_a.close()
    store_b.close()
    with PaperStore(paper) as reopened:
        recovered = PaperEngine.open(reopened)
        assert recovered.state == engine_b.state
        assert recovered.state.control_state == "PAUSED"


def test_wp169_tail_chunking_preserves_observation_gap_global_order(tmp_path) -> None:
    market = tmp_path / "ordered.sqlite3"
    with MarketTruthStore(market) as source:
        raw = _book_raw()
        source.append(raw, mt.normalize_websocket_message(raw, book_readiness={}))
        source.mark_gap("7", "OPEN", "DISCONNECT", "2024-07-03T09:46:41.000000Z")
    tail = Wp169ReadOnlyTail(market)
    first = tail.read_new(limit=1)
    second = tail.read_new(limit=1)
    assert [first[0].kind, second[0].kind] == ["BOOK", "GAP_OPEN"]
    assert first[0].receive_time_ns <= second[0].receive_time_ns


def test_bound_wp172_window_and_decision_trace_drive_full_paper_engine(tmp_path) -> None:
    model, _exp, _ev, trace, window, assessment, binding = edge_stack()
    with PaperStore(tmp_path / "wp172.sqlite3", create=True) as store:
        engine = PaperEngine.create(
            store,
            binding,
            generous_limits(),
            assessment=assessment,
            cost_model=model,
            session_label="wp172-replay",
            created_time_ns=1,
        )
        run_wp172_replay(
            engine, market_truth=window, decision_trace=trace
        )
        assert engine.state.orders[0].filled_quantity == assessment.filled_quantity
        assert engine.state.orders[0].fee_paid == assessment.fee_cost
        with pytest.raises(PaperTradingError, match="WP172_REPLAY_INVALID"):
            run_wp172_replay(
                engine,
                market_truth=replace(window, lineage_id="markettruthwindow:sha256:" + "0" * 64),
                decision_trace=trace,
            )


def test_live_store_gap_and_invalid_or_unreconstructable_truth_fail_closed(
    tmp_path,
) -> None:
    market = tmp_path / "market.sqlite3"
    with MarketTruthStore(market) as source:
        raw = _book_raw()
        source.append(raw, mt.normalize_websocket_message(raw, book_readiness={}))
        source.mark_gap("7", "OPEN", "DISCONNECT", "2024-07-03T09:46:41.000000Z")
    events = Wp169ReadOnlyTail(market).read_new()
    assert [event.kind for event in events] == ["BOOK", "GAP_OPEN"]

    with MarketTruthStore(market) as source:
        update = mt.make_raw_envelope(
            "WS",
            "polymarket:market-ws",
            "ws:00000000-0000-4000-8000-000000000000:frame:2",
            "2024-07-03T09:46:42.000000Z",
            json.dumps(
                {
                    "event_type": "price_change",
                    "market": "0x" + "a" * 64,
                    "timestamp": "1720000002000",
                    "price_changes": [
                        {"asset_id": "7", "price": "0.5", "size": "1", "side": "BUY"}
                    ],
                }
            ).encode(),
            occurrence_sequence=2,
        )
        observations = mt.normalize_websocket_message(
            update, book_readiness={"7": False}
        )
        source.append(update, observations)
    tail = Wp169ReadOnlyTail(market)
    assert all(
        event.kind != "BOOK" or event.lineage != observations[0].observation_id
        for event in tail.read_new()
    )

    bad = tmp_path / "bad.sqlite3"
    bad.write_bytes(b"not sqlite")
    with pytest.raises(PaperTradingError, match="SOURCE_UNAVAILABLE"):
        Wp169ReadOnlyTail(bad)


def test_stale_gapped_crossed_and_one_sided_market_state_never_fills(tmp_path) -> None:
    model, _exp, _ev, _trace, _window, assessment, binding = edge_stack()
    with PaperStore(tmp_path / "paper.sqlite3", create=True) as store:
        engine = PaperEngine.create(
            store,
            binding,
            generous_limits(max_market_data_age_ns=1),
            assessment=assessment,
            cost_model=model,
            session_label="state",
            created_time_ns=1,
        )
        engine.process_market_event(paper_book(100))
        stale = build_paper_intent(
            binding,
            market_id="market:a",
            asset_id="asset:a",
            side="BUY",
            quantity="1",
            order_style="AGGRESSIVE_TAKER",
            reference_price="0.5",
            decision_time_ns=102,
        )
        assert engine.submit(stale).status == "REJECTED"
        with pytest.raises(PaperTradingError, match="MARKET_EVENT_INVALID"):
            engine.process_market_event(
                PaperMarketEvent(
                    "BOOK",
                    "market:a",
                    "asset:a",
                    102,
                    103,
                    "crossed",
                    (("0.6", "1"),),
                    (("0.5", "1"),),
                )
            )
        with pytest.raises(PaperTradingError, match="MARKET_EVENT_INVALID"):
            engine.process_market_event(
                PaperMarketEvent(
                    "BOOK",
                    "market:a",
                    "asset:a",
                    102,
                    103,
                    "one-sided",
                    (("0.4", "1"),),
                    (),
                )
            )
