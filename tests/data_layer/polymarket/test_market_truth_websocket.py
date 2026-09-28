"""WP169 focused tests: book reconstruction, gaps, plan/commit, and the WS runner."""

from __future__ import annotations

import asyncio
import json
import pathlib

import pytest

from src.data_layer.polymarket import market_truth as mt
from src.data_layer.polymarket.market_truth_store import MarketTruthStore
from src.data_layer.polymarket.market_truth_websocket import (
    MarketBookState,
    SubscriptionController,
    run_market_websocket,
    _run_market_websocket,
)

CONDITION = "0x" + "a" * 64


def _ws(seq: int, body: dict, ts: str | None = None) -> mt.RawEnvelope:
    ts = ts or f"2024-07-03T09:46:{seq % 60:02d}.000000Z"
    return mt.make_raw_envelope(
        "WS", "polymarket:market-ws", f"ws:00000000-0000-4000-8000-000000000000:frame:{seq}", ts,
        json.dumps(body).encode(), occurrence_sequence=seq,
    )


def _book(seq, bids, asks, ts_ms="1720000000000"):
    return _ws(seq, {"event_type": "book", "asset_id": "7", "market": CONDITION,
                     "timestamp": ts_ms, "bids": bids, "asks": asks})


def _apply(book: MarketBookState, raw: mt.RawEnvelope):
    obs = mt.normalize_websocket_message(raw, book_readiness=book._readiness())
    return book.commit(book.plan(obs)), obs


def test_disconnect_gap_requires_fresh_book_snapshot() -> None:
    book = MarketBookState(["7"])
    res, _ = _apply(book, _book(0, [{"price": "0.40", "size": "12"}], [{"price": "0.60", "size": "8"}]))
    assert res[0].status == "APPLIED" and book.is_ready("7")
    # Disconnect marks the ready asset gapped.
    book.mark_disconnect("2024-07-03T09:47:00.000000Z")
    assert not book.is_ready("7")
    # A delta while gapped is quarantined BOOK_GAP_ACTIVE and does not apply.
    delta = _ws(1, {"event_type": "price_change", "market": CONDITION, "timestamp": "1720000001000",
                    "price_changes": [{"asset_id": "7", "price": "0.41", "size": "5", "side": "BUY"}]})
    obs = mt.normalize_websocket_message(delta, book_readiness=book._readiness())
    assert obs[0].status == "QUARANTINED" and obs[0].error_codes == ("BOOK_GAP_ACTIVE",)
    res2 = book.commit(book.plan(obs))
    assert res2[0].applied is False and not book.is_ready("7")
    # Only a fresh full snapshot heals the gap.
    res3, _ = _apply(book, _book(2, [{"price": "0.40", "size": "12"}], [{"price": "0.60", "size": "8"}], "1720000002000"))
    assert res3[0].status == "APPLIED" and book.is_ready("7")


def test_multi_asset_frame_plan_commit_discard_and_ordering(tmp_path) -> None:
    book = MarketBookState(["7", "11"])
    # Establish both books.
    for asset in ("7", "11"):
        raw = _ws(0, {"event_type": "book", "asset_id": asset, "market": CONDITION,
                      "timestamp": "1720000000000", "bids": [{"price": "0.40", "size": "12"}],
                      "asks": [{"price": "0.60", "size": "8"}]})
        book.commit(book.plan(mt.normalize_websocket_message(raw, book_readiness=book._readiness())))
    assert book.is_ready("7") and book.is_ready("11")
    # A price_change frame touching both assets yields one transition per distinct asset in order.
    frame = _ws(1, {"event_type": "price_change", "market": CONDITION, "timestamp": "1720000001000",
                    "price_changes": [
                        {"asset_id": "11", "price": "0.42", "size": "3", "side": "BUY"},
                        {"asset_id": "7", "price": "0.41", "size": "5", "side": "BUY"},
                    ]})
    obs = mt.normalize_websocket_message(frame, book_readiness=book._readiness())
    plan = book.plan(obs)
    assert [t.asset_id for t in plan.transitions] == ["11", "7"]  # first-observation order
    results = book.commit(plan)
    assert {r.asset_id for r in results} == {"7", "11"}
    # discard gaps every affected asset (storage-failure path), no READY advanced.
    frame2 = _ws(2, {"event_type": "price_change", "market": CONDITION, "timestamp": "1720000002000",
                     "price_changes": [{"asset_id": "7", "price": "0.43", "size": "1", "side": "BUY"}]})
    plan2 = book.plan(mt.normalize_websocket_message(frame2, book_readiness=book._readiness()))
    discarded = book.discard(plan2, "STORAGE_FAILURE")
    assert discarded[0].status == "GAPPED" and discarded[0].applied is False
    assert not book.is_ready("7")
    # Unknown / duplicate assets reject INPUT_INVALID at construction.
    with pytest.raises(mt.MarketTruthError):
        MarketBookState(["7", "7"])


def test_snapshot_delta_reconstruction_checkpoint_and_restart_equivalence(tmp_path) -> None:
    book = MarketBookState(["7"])
    _apply(book, _book(0, [{"price": "0.40", "size": "12"}], [{"price": "0.60", "size": "8"}]))
    # Upsert + delete deltas.
    _apply(book, _ws(1, {"event_type": "price_change", "market": CONDITION, "timestamp": "1720000001000",
                         "price_changes": [{"asset_id": "7", "price": "0.41", "size": "5", "side": "BUY"}]}))
    _apply(book, _ws(2, {"event_type": "price_change", "market": CONDITION, "timestamp": "1720000002000",
                         "price_changes": [{"asset_id": "7", "price": "0.40", "size": "0", "side": "BUY"}]}))
    # Equivalent full snapshot must reconstruct the same levels.
    equivalent = MarketBookState(["7"])
    _apply(equivalent, _book(3, [{"price": "0.41", "size": "5"}], [{"price": "0.60", "size": "8"}], "1720000003000"))
    a = json.loads(book.snapshot_json())["assets"]["7"]
    b = json.loads(equivalent.snapshot_json())["assets"]["7"]
    assert a["bids"] == b["bids"] == [["0.41", "5"]]
    assert a["asks"] == b["asks"] == [["0.6", "8"]]  # 0.60 canonicalizes to 0.6
    # Invalid delta (delete of an absent level) gaps the asset.
    res, _ = _apply(book, _ws(4, {"event_type": "price_change", "market": CONDITION, "timestamp": "1720000004000",
                                  "price_changes": [{"asset_id": "7", "price": "0.99", "size": "0", "side": "BUY"}]}))
    assert res[0].status == "GAPPED" and res[0].error_codes == ("CONTINUITY_GAP",)
    # Checkpoint / restart round-trip via from_checkpoint.
    equivalent2 = MarketBookState(["7"])
    _apply(equivalent2, _book(5, [{"price": "0.41", "size": "5"}], [{"price": "0.60", "size": "8"}], "1720000005000"))
    with MarketTruthStore(tmp_path / "wp169_ws.sqlite3") as store:
        key = "ws:market:assets:sha256:" + mt.sha256_hex(mt.canonical_json_bytes(["7"]))
        checkpoint = store.write_checkpoint(
            key, {"asset_ids": ["7"], "last_occurrence_id": None,
                  "book_states": json.loads(equivalent2.snapshot_json())}, "ACTIVE"
        )
        restored = MarketBookState.from_checkpoint(checkpoint)
        # Restored levels equal the pre-checkpoint snapshot; the next connection re-gaps.
        assert json.loads(restored.snapshot_json())["assets"]["7"]["bids"] == [["0.41", "5"]]
        restored.mark_disconnect("2024-07-03T09:48:00.000000Z")
        assert not restored.is_ready("7")


def test_subscription_controller_owns_bounded_queue() -> None:
    async def scenario() -> None:
        controller = SubscriptionController(mt.AcquisitionLimits(max_queue_items=1))
        ok = controller.submit(mt.SubscriptionUpdate("subscribe", ("7",)))
        assert ok.status == "QUEUED" and ok.accepted
        overflow = controller.submit(mt.SubscriptionUpdate("subscribe", ("11",)))
        assert overflow.status == "REJECTED" and overflow.error_codes == ("QUEUE_LIMIT_EXCEEDED",)
        assert controller.overflowed() is True
        bad = controller.submit(mt.SubscriptionUpdate("bogus", ("7",)))
        assert bad.status == "REJECTED" and bad.error_codes == ("INPUT_INVALID",)

    asyncio.run(scenario())


class _FakeSocket:
    def __init__(self, messages):
        self._messages = list(messages)
        self.sent = []

    async def send(self, data):
        self.sent.append(data)

    async def recv(self):
        if not self._messages:
            raise StopAsyncIteration()
        return self._messages.pop(0)

    async def close(self):
        pass


class _FakeConn:
    def __init__(self, messages):
        self._socket = _FakeSocket(messages)

    async def __aenter__(self):
        return self._socket

    async def __aexit__(self, *exc):
        return False


def test_ws_runner_manual_start_archives_and_checkpoints(tmp_path) -> None:
    async def scenario() -> mt.AcquisitionReceipt:
        stop = asyncio.Event()
        message = json.dumps({"event_type": "book", "asset_id": "7", "market": CONDITION,
                              "timestamp": "1720000000000", "bids": [{"price": "0.4", "size": "12"}],
                              "asks": [{"price": "0.6", "size": "8"}]})
        calls = {"n": 0}

        def factory(url, max_size):
            calls["n"] += 1
            if calls["n"] >= 2:
                stop.set()
            return _FakeConn([message] if calls["n"] == 1 else [])

        counter = {"i": 0}

        def clock():
            counter["i"] += 1
            return f"2024-07-03T10:{(counter['i'] // 60) % 60:02d}:{counter['i'] % 60:02d}.000000Z"

        with MarketTruthStore(tmp_path / "wp169_wsrun.sqlite3") as store:
            return await _run_market_websocket(["7"], store, stop, connection_factory=factory, now=clock)

    receipt = asyncio.run(scenario())
    assert receipt.status == "STOPPED" and receipt.stop_reason == "CALLER_STOP"
    assert receipt.raw_count >= 1 and receipt.checkpoint_sequence >= 1
    # A non-fixed websocket_url is INPUT_INVALID before any connection factory runs.
    with pytest.raises(mt.MarketTruthError):
        asyncio.run(run_market_websocket(["7"], None, asyncio.Event(), websocket_url="wss://evil"))


class _FeedSocket:
    def __init__(self):
        self.q: asyncio.Queue = asyncio.Queue()
        self.sent: list[str] = []

    async def send(self, data):
        self.sent.append(data)

    async def recv(self):
        item = await self.q.get()
        if item is None:
            raise StopAsyncIteration()
        return item

    async def close(self):
        pass


def _feed_conn(sock: _FeedSocket):
    class _Conn:
        async def __aenter__(self):
            return sock

        async def __aexit__(self, *exc):
            return False

    return lambda url, max_size: _Conn()


# Reconnect tests keep the REAL product backoff (_BACKOFF_SCHEDULE[0] == 1s) but never infer
# its completion from wall-clock sleeps: they await the observable condition itself, bounded
# by a generous finite timeout that stops the runner and fails clearly instead of hanging.
_SYNC_TIMEOUT_SECONDS = 30.0
_POLL_SECONDS = 0.005


async def _wait_for_condition(condition, stop: asyncio.Event, task, what: str) -> None:
    """Await `condition()` (a coroutine function) or stop the runner and fail on timeout."""
    try:
        await asyncio.wait_for(condition(), timeout=_SYNC_TIMEOUT_SECONDS)
    except asyncio.TimeoutError:
        stop.set()
        await asyncio.wait_for(task, timeout=_SYNC_TIMEOUT_SECONDS)
        pytest.fail(f"timed out after {_SYNC_TIMEOUT_SECONDS}s waiting for {what}")


def _polling(predicate):
    """Coroutine function that yields to the loop until `predicate()` is true."""
    async def _poll() -> None:
        while not predicate():
            await asyncio.sleep(_POLL_SECONDS)
    return _poll


def test_runner_emits_periodic_heartbeat_ping_and_stops(tmp_path) -> None:
    """B: the runner emits an outgoing text PING at the heartbeat seam and shuts down
    on the stop event; incoming PING is answered with PONG."""
    async def scenario() -> _FeedSocket:
        sock = _FeedSocket()
        stop = asyncio.Event()
        fired = {"n": 0}

        async def heartbeat():
            fired["n"] += 1
            if fired["n"] == 1:
                return  # one deterministic heartbeat tick
            await asyncio.Event().wait()

        with MarketTruthStore(tmp_path / "wp169_hb.sqlite3") as store:
            task = asyncio.ensure_future(
                _run_market_websocket(
                    ["7"], store, stop, connection_factory=_feed_conn(sock),
                    heartbeat_waiter=heartbeat, now=lambda: "2024-07-03T10:00:00.000000Z",
                )
            )
            await asyncio.sleep(0.05)
            await sock.q.put("PING")  # server PING -> client PONG
            await asyncio.sleep(0.05)
            stop.set()
            await task
        return sock

    sock = asyncio.run(scenario())
    assert "PING" in sock.sent  # outgoing heartbeat
    assert "PONG" in sock.sent  # answered the server PING


def test_runner_consumes_dynamic_subscription_updates(tmp_path) -> None:
    """A: the streaming runner consumes the controller queue, sends the exact wire
    message, and only then adds the new asset as NOT_READY; no-ops send nothing."""
    async def scenario():
        sock = _FeedSocket()
        stop = asyncio.Event()
        controller = SubscriptionController(mt.AcquisitionLimits())

        async def heartbeat():
            await asyncio.Event().wait()

        with MarketTruthStore(tmp_path / "wp169_sub.sqlite3") as store:
            task = asyncio.ensure_future(
                _run_market_websocket(
                    ["7"], store, stop, connection_factory=_feed_conn(sock),
                    subscription_controller=controller, heartbeat_waiter=heartbeat,
                    now=lambda: "2024-07-03T10:00:00.000000Z",
                )
            )
            await asyncio.sleep(0.05)
            controller.submit(mt.SubscriptionUpdate("subscribe", ("11",)))
            await asyncio.sleep(0.05)
            controller.submit(mt.SubscriptionUpdate("subscribe", ("11",)))  # no-op now
            await asyncio.sleep(0.05)
            controller.submit(mt.SubscriptionUpdate("unsubscribe", ("11",)))
            await asyncio.sleep(0.05)
            stop.set()
            await task
        return sock

    sock = asyncio.run(scenario())
    subs = [m for m in sock.sent if '"operation":"subscribe"' in m and "11" in m]
    unsubs = [m for m in sock.sent if '"operation":"unsubscribe"' in m and "11" in m]
    # Exactly one subscribe wire message (the duplicate is a no-op) and one unsubscribe.
    assert len(subs) == 1, sock.sent
    assert len(unsubs) == 1, sock.sent


def test_runner_gaps_oversize_frame_without_storing_unbounded_bytes(tmp_path) -> None:
    """J: an oversize frame is a visible continuity fault -- books are gapped, a gap
    event is recorded, and the unbounded bytes are never stored."""
    async def scenario():
        sock = _FeedSocket()
        stop = asyncio.Event()

        async def heartbeat():
            await asyncio.Event().wait()

        cond = "0x" + "a" * 64
        book_msg = json.dumps({
            "event_type": "book", "asset_id": "7", "market": cond,
            "timestamp": "1720000000000", "bids": [{"price": "0.4", "size": "12"}],
            "asks": [{"price": "0.6", "size": "8"}],
        })
        limits = mt.AcquisitionLimits(max_frame_bytes=max(300, len(book_msg) + 10))
        oversize = "y" * (limits.max_frame_bytes + 200)
        with MarketTruthStore(tmp_path / "wp169_over.sqlite3", limits) as store:
            task = asyncio.ensure_future(
                _run_market_websocket(
                    ["7"], store, stop, limits=limits, connection_factory=_feed_conn(sock),
                    heartbeat_waiter=heartbeat, now=lambda: "2024-07-03T10:00:00.000000Z",
                )
            )
            await sock.q.put(book_msg)
            await asyncio.sleep(0.05)
            await sock.q.put(oversize)
            await asyncio.sleep(0.05)
            stop.set()
            await task
            conn = store._require()
            gaps = conn.execute(
                "SELECT COUNT(*) FROM gap_events WHERE reason='PARSE_FAULT'"
            ).fetchone()[0]
            raw = conn.execute("SELECT COUNT(*) FROM raw_occurrences").fetchone()[0]
        return gaps, raw

    gaps, raw = asyncio.run(scenario())
    assert gaps >= 1  # oversize frame recorded a visible gap
    assert raw == 1  # only the valid book stored; oversize bytes not persisted


def test_reconnect_uses_current_subscription_set_not_original(tmp_path) -> None:
    """#5: dynamic subscribe/unsubscribe survive a reconnect -- the reconnect payload and
    checkpoint use the current authoritative asset set, not the original one."""
    async def scenario():
        sockets: list[_FeedSocket] = []
        stop = asyncio.Event()
        controller = SubscriptionController(mt.AcquisitionLimits())

        def factory(url, max_size):
            sock = _FeedSocket()
            sockets.append(sock)

            class _Conn:
                async def __aenter__(self):
                    return sock

                async def __aexit__(self, *exc):
                    return False

            return _Conn()

        async def heartbeat():
            await asyncio.Event().wait()

        with MarketTruthStore(tmp_path / "wp169_recon.sqlite3") as store:
            task = asyncio.ensure_future(
                _run_market_websocket(
                    ["7"], store, stop, limits=mt.AcquisitionLimits(max_reconnect_attempts=5),
                    connection_factory=factory, subscription_controller=controller,
                    heartbeat_waiter=heartbeat, now=lambda: "2024-07-03T10:00:00.000000Z",
                )
            )
            # First connection has sent its initial subscription payload.
            await _wait_for_condition(
                _polling(lambda: len(sockets) >= 1 and len(sockets[0].sent) >= 1),
                stop, task, "the first connection's initial subscription payload",
            )
            controller.submit(mt.SubscriptionUpdate("subscribe", ("11",)))
            controller.submit(mt.SubscriptionUpdate("subscribe", ("99",)))
            controller.submit(mt.SubscriptionUpdate("unsubscribe", ("7",)))
            # All three dynamic updates were sent on the wire (membership mutates only after
            # a successful send), so the authoritative set is {11, 99} before the disconnect.
            await _wait_for_condition(
                _polling(lambda: len(sockets[0].sent) >= 4),
                stop, task, "the three dynamic subscription updates to be sent",
            )
            # Force a disconnect: the first socket closes -> reconnect on a fresh socket.
            await sockets[0].q.put(None)
            # The reconnect (after the real 1s backoff) actually emitted its subscription
            # payload on the second connection; socket creation alone is insufficient.
            await _wait_for_condition(
                _polling(lambda: len(sockets) >= 2 and len(sockets[1].sent) >= 1),
                stop, task, "the second connection's reconnect subscription payload",
            )
            stop.set()
            await task
            key_ids = None
            for ck in [store.load_checkpoint("ws:market:assets:sha256:" + mt.sha256_hex(mt.canonical_json_bytes(list(a))))
                       for a in (["11", "99"],)]:
                if ck is not None:
                    key_ids = json.loads(ck.value_json)["asset_ids"]
            return sockets, key_ids

    sockets, key_ids = asyncio.run(scenario())
    assert len(sockets) >= 2  # at least one reconnect happened
    # The reconnect (second connection) initial payload uses the CURRENT set {11,99}.
    reconnect_initial = sockets[1].sent[0]
    assert "11" in reconnect_initial and "99" in reconnect_initial
    assert '"assets_ids":["11","99"]' in reconnect_initial or '"assets_ids": ["11", "99"]' in reconnect_initial
    # 7 was unsubscribed and must not reappear on reconnect.
    assert '"7"' not in reconnect_initial.split('"type"')[0]
    # Checkpoint asset_ids match the current membership.
    assert key_ids == ["11", "99"]


def test_normal_book_gaps_are_persisted_and_healed(tmp_path) -> None:
    """#6 + item 9: a READY->GAPPED continuity fault persists an OPEN gap with the exact
    reason AND leaves STREAMING via the reconnect path; after reconnect a fresh full snapshot
    persists a HEALED event."""
    async def scenario():
        sock = _FeedSocket()
        stop = asyncio.Event()

        async def heartbeat():
            await asyncio.Event().wait()

        cond = "0x" + "a" * 64

        def book_msg(ts_ms: str, bid_size: str = "12") -> str:
            return json.dumps({
                "event_type": "book", "asset_id": "7", "market": cond,
                "timestamp": ts_ms, "bids": [{"price": "0.4", "size": bid_size}],
                "asks": [{"price": "0.6", "size": "8"}],
            })

        # A price_change with an OLDER timestamp than the book -> TIMESTAMP_REGRESSION gap.
        regress = json.dumps({
            "event_type": "price_change", "market": cond, "timestamp": "1719999999000",
            "price_changes": [{"asset_id": "7", "price": "0.41", "size": "5", "side": "BUY"}],
        })
        with MarketTruthStore(tmp_path / "wp169_gap.sqlite3") as store:
            task = asyncio.ensure_future(
                _run_market_websocket(
                    ["7"], store, stop, connection_factory=_feed_conn(sock),
                    heartbeat_waiter=heartbeat, now=lambda: "2024-07-03T10:00:00.000000Z",
                )
            )
            conn = store._require()

            def gap_count(state: str, reason: str | None = None) -> int:
                sql = "SELECT COUNT(*) FROM gap_events WHERE state=?"
                args: tuple[str, ...] = (state,)
                if reason is not None:
                    sql += " AND reason=?"
                    args += (reason,)
                return conn.execute(sql, args).fetchone()[0]

            await sock.q.put(book_msg("1720000000000"))
            await sock.q.put(regress)  # READY -> GAPPED (timestamp regression) -> reconnect
            # The durable OPEN gap is written synchronously on the continuity fault, just
            # before the runner leaves STREAMING for RECONNECT_WAIT (real 1s backoff).
            await _wait_for_condition(
                _polling(lambda: gap_count("OPEN", "TIMESTAMP_REGRESSION") >= 1),
                stop, task, "the OPEN TIMESTAMP_REGRESSION gap evidence",
            )
            # Queue the fresh full book so the reconnected session consumes it and heals the gap.
            await sock.q.put(book_msg("1720000005000"))
            await _wait_for_condition(
                _polling(lambda: gap_count("HEALED") >= 1),
                stop, task, "the HEALED gap evidence after reconnect",
            )
            stop.set()
            await task
            open_reasons = [r[0] for r in conn.execute(
                "SELECT reason FROM gap_events WHERE state='OPEN'"
            ).fetchall()]
            healed = conn.execute("SELECT COUNT(*) FROM gap_events WHERE state='HEALED'").fetchone()[0]
        return open_reasons, healed

    open_reasons, healed = asyncio.run(scenario())
    assert "TIMESTAMP_REGRESSION" in open_reasons  # exact reason persisted
    assert healed >= 1  # fresh snapshot healed the gap


import dataclasses as _dataclasses


def test_invalid_delta_does_not_partially_mutate_book() -> None:
    """SEED13: a rejected delta (crossed book) gaps the asset WITHOUT committing the
    rejected level; the last valid level set is preserved until a full snapshot heals."""
    book = MarketBookState(["7"])
    _apply(book, _book(0, [{"price": "0.40", "size": "12"}], [{"price": "0.60", "size": "8"}]))
    before = json.loads(book.snapshot_json())["assets"]["7"]
    crossed = _ws(1, {"event_type": "price_change", "market": CONDITION, "timestamp": "1720000001000",
                      "price_changes": [{"asset_id": "7", "price": "0.65", "size": "5", "side": "BUY"}]})
    res, _ = _apply(book, crossed)
    assert res[0].status == "GAPPED" and res[0].applied is False
    after = json.loads(book.snapshot_json())["assets"]["7"]
    assert after["bids"] == before["bids"] == [["0.4", "12"]]
    assert all(level[0] != "0.65" for level in after["bids"])


def test_from_checkpoint_recomputes_hash_and_validates_invariants(tmp_path) -> None:
    """SEED08: from_checkpoint recomputes the value hash and validates every book-state
    invariant before restore; a tampered value or a crossed book fails closed."""
    equivalent = MarketBookState(["7"])
    _apply(equivalent, _book(0, [{"price": "0.41", "size": "5"}], [{"price": "0.60", "size": "8"}]))
    with MarketTruthStore(tmp_path / "wp169_ckpt.sqlite3") as store:
        key = "ws:market:assets:sha256:" + mt.sha256_hex(mt.canonical_json_bytes(["7"]))
        ck = store.write_checkpoint(
            key, {"asset_ids": ["7"], "last_occurrence_id": None,
                  "book_states": json.loads(equivalent.snapshot_json())}, "ACTIVE"
        )
        restored = MarketBookState.from_checkpoint(ck)
        assert json.loads(restored.snapshot_json())["assets"]["7"]["bids"] == [["0.41", "5"]]
        # Tampered value_json (hash no longer matches) fails closed.
        tampered = _dataclasses.replace(ck, value_json=ck.value_json.replace('"0.41"', '"0.42"'))
        with pytest.raises(mt.MarketTruthError):
            MarketBookState.from_checkpoint(tampered)
        # A crossed-book invariant violation also fails closed (even with a valid hash).
        crossed_states = {"assets": {"7": {"state": "READY", "market_id": CONDITION,
                          "last_timestamp_ms": 1, "last_hash": None, "last_observation_id": None,
                          "bids": [["0.7", "5"]], "asks": [["0.6", "8"]]}}}
        ck2 = store.write_checkpoint(
            key, {"asset_ids": ["7"], "last_occurrence_id": None, "book_states": crossed_states}, "ACTIVE"
        )
        with pytest.raises(mt.MarketTruthError):
            MarketBookState.from_checkpoint(ck2)


def test_market_book_state_500_asset_boundary() -> None:
    """F9: the reusable WebSocket/book-state API caps membership at 500 at construction AND
    cumulatively across dynamic subscribe."""
    ok = MarketBookState([str(i) for i in range(500)])
    assert len(ok._subscribed_assets()) == 500
    with pytest.raises(mt.MarketTruthError):
        MarketBookState([str(i) for i in range(501)])
    book = MarketBookState([str(i) for i in range(499)])
    book.subscribe(["100000"])  # -> exactly 500
    with pytest.raises(mt.MarketTruthError):
        book.subscribe(["100001"])  # -> 501, cumulative cap exceeded


def test_public_wrapper_rejects_non_fixed_url() -> None:
    """SEED07: the exact frozen public run_market_websocket validates the WS URL before any
    connection factory runs."""
    with pytest.raises(mt.MarketTruthError):
        asyncio.run(run_market_websocket(["7"], None, asyncio.Event(), websocket_url="wss://evil"))


class _BoomSocket:
    def __init__(self):
        self.sent: list[str] = []

    async def send(self, data):
        self.sent.append(data)

    async def recv(self):
        raise RuntimeError("unexpected /secret/path with Traceback text")

    async def close(self):
        pass


def test_recv_arbitrary_exception_is_terminal_internal_closed_failure(tmp_path) -> None:
    """SEED11: an unexpected (non connection-closed) recv exception is a terminal
    FAILED/INTERNAL_CLOSED_FAILURE, never masked as an ordinary reconnect, and no raw
    exception text is echoed."""
    def factory(url, max_size):
        sock = _BoomSocket()

        class _Conn:
            async def __aenter__(self):
                return sock

            async def __aexit__(self, *exc):
                return False

        return _Conn()

    async def scenario():
        stop = asyncio.Event()

        async def heartbeat():
            await asyncio.Event().wait()

        with MarketTruthStore(tmp_path / "wp169_boom.sqlite3") as store:
            return await _run_market_websocket(
                ["7"], store, stop, connection_factory=factory,
                heartbeat_waiter=heartbeat, now=lambda: "2024-07-03T10:00:00.000000Z",
            )

    receipt = asyncio.run(scenario())
    assert receipt.status == "FAILED" and receipt.error_codes == ("INTERNAL_CLOSED_FAILURE",)
    assert mt.scan_no_echo({"status": receipt.status, "error_codes": list(receipt.error_codes)})


def test_runner_terminates_on_queue_overflow_no_false_ready(tmp_path) -> None:
    """F7 / SEED12: queue overflow terminates FAILED/QUEUE_LIMIT_EXCEEDED/QUEUE_LIMIT; a
    previously-READY asset is gapped with QUEUE_OVERFLOW and no asset remains READY."""
    async def scenario():
        sock = _FeedSocket()
        stop = asyncio.Event()
        controller = SubscriptionController(mt.AcquisitionLimits(max_queue_items=1))

        async def heartbeat():
            await asyncio.Event().wait()

        book_msg = json.dumps({
            "event_type": "book", "asset_id": "7", "market": CONDITION,
            "timestamp": "1720000000000", "bids": [{"price": "0.4", "size": "12"}],
            "asks": [{"price": "0.6", "size": "8"}],
        })
        with MarketTruthStore(tmp_path / "wp169_qover.sqlite3") as store:
            task = asyncio.ensure_future(
                _run_market_websocket(
                    ["7", "11"], store, stop, connection_factory=_feed_conn(sock),
                    subscription_controller=controller, heartbeat_waiter=heartbeat,
                    now=lambda: "2024-07-03T10:00:00.000000Z",
                )
            )
            await sock.q.put(book_msg)  # asset 7 -> READY; 11 stays NOT_READY
            await asyncio.sleep(0.05)
            controller.submit(mt.SubscriptionUpdate("subscribe", ("13",)))  # fills queue (size 1)
            controller.submit(mt.SubscriptionUpdate("subscribe", ("17",)))  # sticky overflow
            receipt = await asyncio.wait_for(task, timeout=3)
            conn = store._require()
            reasons = [r[0] for r in conn.execute(
                "SELECT reason FROM gap_events WHERE state='OPEN'"
            ).fetchall()]
            states = set()
            for row in conn.execute("SELECT value_json FROM checkpoint_current").fetchall():
                assets = json.loads(row[0]).get("book_states", {}).get("assets", {})
                states |= {a["state"] for a in assets.values()}
        return receipt, reasons, states

    receipt, reasons, states = asyncio.run(scenario())
    assert receipt.status == "FAILED"
    assert receipt.error_codes == ("QUEUE_LIMIT_EXCEEDED",) and receipt.stop_reason == "QUEUE_LIMIT"
    # Item 2: queue overflow gaps EVERY subscribed asset (READY and NOT_READY) with durable
    # OPEN QUEUE_OVERFLOW evidence -- no asset may remain READY or NOT_READY.
    assert states == {"GAPPED"}, states
    assert reasons.count("QUEUE_OVERFLOW") >= 2, reasons  # both original subscribed assets gapped


def test_subscription_controller_projected_membership_rejects_noops() -> None:
    """Item 1: duplicate subscribe, absent unsubscribe, and a projected total over 500 are
    REJECTED/INPUT_INVALID (state-relative no-ops) without a wire send; a genuinely new
    update is QUEUED."""
    controller = SubscriptionController(mt.AcquisitionLimits())
    controller._bind(["7"])
    assert controller.submit(mt.SubscriptionUpdate("subscribe", ("7",))).error_codes == ("INPUT_INVALID",)
    assert controller.submit(mt.SubscriptionUpdate("unsubscribe", ("99",))).error_codes == ("INPUT_INVALID",)
    ok = controller.submit(mt.SubscriptionUpdate("subscribe", ("11",)))
    assert ok.status == "QUEUED" and ok.accepted
    assert controller.submit(mt.SubscriptionUpdate("subscribe", ("11",))).error_codes == ("INPUT_INVALID",)
    big = SubscriptionController(mt.AcquisitionLimits())
    big._bind([str(i) for i in range(500)])
    assert big.submit(mt.SubscriptionUpdate("subscribe", ("100000",))).error_codes == ("INPUT_INVALID",)


def test_subscription_controller_queuefull_does_not_mutate_projection() -> None:
    """Item 1: a QueueFull rejection must not mutate the projected membership."""
    async def scenario():
        controller = SubscriptionController(mt.AcquisitionLimits(max_queue_items=1))
        controller._bind([])
        assert controller.submit(mt.SubscriptionUpdate("subscribe", ("7",))).status == "QUEUED"
        overflow = controller.submit(mt.SubscriptionUpdate("subscribe", ("11",)))
        assert overflow.status == "REJECTED" and overflow.error_codes == ("QUEUE_LIMIT_EXCEEDED",)
        await controller.get()
        assert controller.submit(mt.SubscriptionUpdate("subscribe", ("11",))).status == "QUEUED"

    asyncio.run(scenario())


def test_discard_rejects_invalid_reason() -> None:
    """Item 7: MarketBookState.discard validates the closed gap-reason vocabulary."""
    book = MarketBookState(["7"])
    plan = book.plan(())
    with pytest.raises(mt.MarketTruthError):
        book.discard(plan, "BOGUS")
    assert book.discard(plan, "STORAGE_FAILURE") == ()


def test_effective_book_level_cap_honors_stricter_limit() -> None:
    """Item 14: a stricter privately-bound per-side cap gaps an over-cap snapshot while the
    default (5000) still accepts it."""
    snapshot = _ws(0, {
        "event_type": "book", "asset_id": "7", "market": CONDITION, "timestamp": "1720000000000",
        "bids": [{"price": "0.40", "size": "1"}, {"price": "0.41", "size": "1"}, {"price": "0.42", "size": "1"}],
        "asks": [{"price": "0.60", "size": "8"}],
    })
    strict = MarketBookState(["7"])
    strict._max_levels = 2
    res = strict.commit(strict.plan(mt.normalize_websocket_message(snapshot, book_readiness=strict._readiness())))
    assert res[0].status == "GAPPED" and res[0].error_codes == ("QUEUE_LIMIT_EXCEEDED",)
    default = MarketBookState(["7"])
    res2 = default.commit(default.plan(mt.normalize_websocket_message(snapshot, book_readiness=default._readiness())))
    assert res2[0].status == "APPLIED"


def test_from_checkpoint_rejects_each_invalid_field() -> None:
    """Item 3: from_checkpoint validates every ws-checkpoint invariant; each field violation
    fails closed with STORE_CONFLICT (no partial restore)."""
    key = "ws:market:assets:sha256:" + mt.sha256_hex(mt.canonical_json_bytes(["7"]))

    def ckpt(value: dict) -> mt.Checkpoint:
        vj = mt.canonical_json_bytes(value).decode("utf-8")
        sha = mt.compute_checkpoint_sha256(
            checkpoint_key=key, sequence=1, state="ACTIVE", value_json=vj, previous_sha256=None
        )
        return mt.Checkpoint(1, 1, key, vj, sha, None, "ACTIVE")

    def asset(**over):
        base = {"state": "READY", "market_id": None, "last_timestamp_ms": 1, "last_hash": None,
                "last_observation_id": None, "bids": [["0.4", "12"]], "asks": [["0.6", "8"]]}
        base.update(over)
        return base

    valid = {"asset_ids": ["7"], "last_occurrence_id": None, "book_states": {"assets": {"7": asset()}}}
    restored = MarketBookState.from_checkpoint(ckpt(valid))
    assert json.loads(restored.snapshot_json())["assets"]["7"]["bids"] == [["0.4", "12"]]

    invalids = [
        {**valid, "extra": 1},
        {"asset_ids": ["07"], "last_occurrence_id": None, "book_states": {"assets": {"07": asset()}}},
        {"asset_ids": ["11"], "last_occurrence_id": None, "book_states": {"assets": {"11": asset()}}},
        {"asset_ids": ["7"], "last_occurrence_id": "bad", "book_states": {"assets": {"7": asset()}}},
        {"asset_ids": ["7"], "last_occurrence_id": None, "book_states": {"assets": {"8": asset()}}},
        {"asset_ids": ["7"], "last_occurrence_id": None, "book_states": {"assets": {"7": asset(state="FOO")}}},
        {"asset_ids": ["7"], "last_occurrence_id": None, "book_states": {"assets": {"7": asset(market_id="notcondition")}}},
        {"asset_ids": ["7"], "last_occurrence_id": None, "book_states": {"assets": {"7": asset(last_timestamp_ms=-1)}}},
        {"asset_ids": ["7"], "last_occurrence_id": None, "book_states": {"assets": {"7": asset(last_observation_id="bad")}}},
        {"asset_ids": ["7"], "last_occurrence_id": None, "book_states": {"assets": {"7": asset(bids=[["0.7", "5"]])}}},
    ]
    for bad in invalids:
        with pytest.raises(mt.MarketTruthError):
            MarketBookState.from_checkpoint(ckpt(bad))


def test_continuity_fault_triggers_reconnect_wait(tmp_path) -> None:
    """Item 9: a READY->GAPPED continuity fault leaves STREAMING via the reconnect path (a
    fresh connection is opened) rather than continuing the same connection."""
    async def scenario():
        sockets: list[_FeedSocket] = []
        stop = asyncio.Event()
        socket_opened = {1: asyncio.Event(), 2: asyncio.Event()}

        def factory(url, max_size):
            sock = _FeedSocket()
            sockets.append(sock)
            if len(sockets) in socket_opened:
                socket_opened[len(sockets)].set()

            class _Conn:
                async def __aenter__(self):
                    return sock

                async def __aexit__(self, *exc):
                    return False

            return _Conn()

        async def heartbeat():
            await asyncio.Event().wait()

        book_msg = json.dumps({"event_type": "book", "asset_id": "7", "market": CONDITION,
                               "timestamp": "1720000000000", "bids": [{"price": "0.4", "size": "12"}],
                               "asks": [{"price": "0.6", "size": "8"}]})
        regress = json.dumps({"event_type": "price_change", "market": CONDITION, "timestamp": "1719999999000",
                              "price_changes": [{"asset_id": "7", "price": "0.41", "size": "5", "side": "BUY"}]})
        with MarketTruthStore(tmp_path / "wp169_contreconnect.sqlite3") as store:
            task = asyncio.ensure_future(
                _run_market_websocket(
                    ["7"], store, stop, limits=mt.AcquisitionLimits(max_reconnect_attempts=5),
                    connection_factory=factory, heartbeat_waiter=heartbeat,
                    now=lambda: "2024-07-03T10:00:00.000000Z",
                )
            )
            await _wait_for_condition(socket_opened[1].wait, stop, task, "socket #1 to open")
            await sockets[0].q.put(book_msg)
            await sockets[0].q.put(regress)
            # Socket #2 opens only via the reconnect path, after the real 1s backoff.
            await _wait_for_condition(socket_opened[2].wait, stop, task, "reconnect socket #2 to open")
            stop.set()
            await task
        return sockets

    sockets = asyncio.run(scenario())
    assert len(sockets) >= 2


def test_non_store_limit_failed_append_reconnects_not_silently_continues(tmp_path) -> None:
    """Reviewer round-4 F1 / item-9 F2: a FAILED store.append that is NOT
    STORE_LIMIT_EXCEEDED (e.g. STORE_CONFLICT) must leave STREAMING via the reconnect path
    -- a fresh socket is opened and the affected asset carries an OPEN STORAGE_FAILURE gap --
    rather than silently continuing to read frames on the same (now inconsistent) socket.
    This would fail if the branch regressed to `continue` past the failure."""
    async def scenario():
        sockets: list[_FeedSocket] = []
        stop = asyncio.Event()
        socket_opened = {2: asyncio.Event()}

        def book_msg(ts_ms: str) -> str:
            return json.dumps({"event_type": "book", "asset_id": "7", "market": CONDITION,
                               "timestamp": ts_ms, "bids": [{"price": "0.4", "size": "12"}],
                               "asks": [{"price": "0.6", "size": "8"}]})

        def factory(url, max_size):
            sock = _FeedSocket()
            sockets.append(sock)
            if len(sockets) in socket_opened:
                socket_opened[len(sockets)].set()
            if len(sockets) == 1:
                # Good frame (asset 7 -> READY), then the frame whose store.append FAILS.
                sock.q.put_nowait(book_msg("1720000000000"))
                sock.q.put_nowait(book_msg("1720000001000"))

            class _Conn:
                async def __aenter__(self):
                    return sock

                async def __aexit__(self, *exc):
                    return False

            return _Conn()

        async def heartbeat():
            await asyncio.Event().wait()

        with MarketTruthStore(tmp_path / "wp169_nonstorelimit_fail.sqlite3") as store:
            real_append = store.append
            calls = {"n": 0}

            def failing_append(raw, observations):
                calls["n"] += 1
                if calls["n"] == 2:  # the second book frame's store fails NON-fatally
                    return store.receipt("FAILED", ("STORE_CONFLICT",), "NONE")
                return real_append(raw, observations)

            store.append = failing_append  # type: ignore[assignment]
            task = asyncio.ensure_future(
                _run_market_websocket(
                    ["7"], store, stop, limits=mt.AcquisitionLimits(max_reconnect_attempts=5),
                    connection_factory=factory, heartbeat_waiter=heartbeat,
                    now=lambda: "2024-07-03T10:00:00.000000Z",
                )
            )
            # Socket #2 opens only via the reconnect path, after the real 1s backoff.
            await _wait_for_condition(socket_opened[2].wait, stop, task, "reconnect socket #2 to open")
            stop.set()
            await task
            conn = store._require()
            open_reasons = [r[0] for r in conn.execute(
                "SELECT reason FROM gap_events WHERE state='OPEN'"
            ).fetchall()]
        return sockets, open_reasons

    sockets, open_reasons = asyncio.run(scenario())
    # A non-store-limit FAILED append is NOT swallowed: a fresh socket is opened (reconnect).
    assert len(sockets) >= 2, "non-store-limit FAILED append must reconnect on a fresh socket"
    # The affected asset is gapped with the exact STORAGE_FAILURE reason.
    assert "STORAGE_FAILURE" in open_reasons


def test_reconnect_exhaustion_terminal_from_real_runner(tmp_path) -> None:
    """wp_prompt.txt line 506: 'reconnect attempts exhausted -> FAILED, RETRY_EXHAUSTED,
    RECONNECT_LIMIT', driven by the REAL _run_market_websocket runner (not a runtime stub).
    With max_reconnect_attempts=1 a factory that always disconnects exhausts after one retry.
    Red-sensitive to a wrong error code, an off-by-one on the '>' bound, or stop_reason!=RECONNECT_LIMIT."""
    async def scenario():
        stop = asyncio.Event()
        sockets: list[_FeedSocket] = []

        def factory(url, max_size):
            sock = _FeedSocket()
            sock.q.put_nowait(None)  # immediate connection-closed -> disconnect -> reconnect
            sockets.append(sock)

            class _Conn:
                async def __aenter__(self):
                    return sock

                async def __aexit__(self, *exc):
                    return False

            return _Conn()

        async def heartbeat():
            await asyncio.Event().wait()

        with MarketTruthStore(tmp_path / "wp169_reconn_exhaust.sqlite3") as store:
            receipt = await _run_market_websocket(
                ["7"], store, stop, limits=mt.AcquisitionLimits(max_reconnect_attempts=1),
                connection_factory=factory, heartbeat_waiter=heartbeat,
                now=lambda: "2024-07-03T10:00:00.000000Z",
            )
        return receipt, sockets

    receipt, sockets = asyncio.run(scenario())
    assert receipt.status == "FAILED"
    assert receipt.error_codes == ("RETRY_EXHAUSTED",)
    assert receipt.stop_reason == "RECONNECT_LIMIT", receipt
    # attempt 1 + exactly one reconnect before exhaustion (max_reconnect_attempts=1).
    assert len(sockets) == 2, sockets
