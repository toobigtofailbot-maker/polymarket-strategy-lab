import sqlite3
import json

import pytest

from src.paper_trading import (
    PaperEngine,
    PaperStore,
    PaperTradingError,
    build_paper_intent,
)
from src.paper_trading.models import canonical_json_bytes, content_id

from tests.paper_trading.conftest import make_engine, paper_book


def _intent(engine, *, decision=101, quantity="2"):
    order_style = engine.state.binding.execution_mode
    return build_paper_intent(
        engine.state.binding,
        market_id="market:a",
        asset_id="asset:a",
        side="BUY",
        quantity=quantity,
        order_style=order_style,
        reference_price="0.49" if order_style == "PASSIVE_MAKER" else "0.5",
        decision_time_ns=decision,
    )


def _persistent_snapshot(store):
    checkpoint = store.connection.execute(
        "SELECT last_sequence,last_event_hash,state_json,state_hash "
        "FROM paper_checkpoint WHERE singleton=1"
    ).fetchone()
    journal = store.connection.execute(
        "SELECT sequence,event_id,event_type,event_time_ns,payload_json,"
        "previous_event_hash,event_hash FROM paper_journal ORDER BY sequence"
    ).fetchall()
    return checkpoint, tuple(journal)


@pytest.mark.parametrize(
    ("external_action", "stale_action", "mode"),
    (
        ("submit", "control", "AGGRESSIVE_TAKER"),
        ("pause", "order", "AGGRESSIVE_TAKER"),
        ("cancel", "market", "PASSIVE_MAKER"),
        ("kill", "market", "AGGRESSIVE_TAKER"),
    ),
)
def test_stale_engine_cannot_overwrite_external_committed_state(
    tmp_path, external_action, stale_action, mode
) -> None:
    path = tmp_path / f"stale-{external_action}.sqlite3"
    store_a, engine_a = make_engine(path, mode=mode)
    engine_a.process_market_event(paper_book(100))
    if external_action == "cancel":
        existing = engine_a.submit(_intent(engine_a))
        assert existing.status == "OPEN"

    store_b = PaperStore(path)
    engine_b = PaperEngine.open(store_b)
    assert engine_a.expected_head == engine_b.expected_head

    if external_action == "submit":
        engine_b.submit(_intent(engine_b))
    elif external_action == "pause":
        engine_b.pause(101)
    elif external_action == "cancel":
        engine_b.cancel(engine_b.state.orders[0].order_id, 102)
    else:
        engine_b.kill(101)

    committed = _persistent_snapshot(store_b)
    with pytest.raises(PaperTradingError, match="STALE_PAPER_STATE"):
        if stale_action == "control":
            engine_a.pause(102)
        elif stale_action == "order":
            engine_a.submit(_intent(engine_a, decision=102))
        else:
            engine_a.process_market_event(paper_book(110))

    assert engine_a.state.control_state == "RECONCILIATION_BLOCKED"
    assert _persistent_snapshot(store_b) == committed
    expected_state = engine_b.state
    store_a.close()
    store_b.close()
    with PaperStore(path) as reopened:
        recovered = PaperEngine.open(reopened)
        assert recovered.state == expected_state
        assert recovered.state.control_state != "RECONCILIATION_BLOCKED"


def test_stale_writer_detection_is_symmetric(tmp_path) -> None:
    path = tmp_path / "stale-symmetric.sqlite3"
    store_a, engine_a = make_engine(path)
    store_b = PaperStore(path)
    engine_b = PaperEngine.open(store_b)

    engine_a.pause(101)
    committed = _persistent_snapshot(store_a)
    with pytest.raises(PaperTradingError, match="STALE_PAPER_STATE"):
        engine_b.kill(102)
    assert _persistent_snapshot(store_a) == committed

    expected_state = engine_a.state
    store_a.close()
    store_b.close()
    with PaperStore(path) as reopened:
        recovered = PaperEngine.open(reopened)
        assert recovered.state == expected_state
        assert recovered.state.control_state == "PAUSED"


def _rewrite_valid_chain(path, mutate) -> None:
    connection = sqlite3.connect(path)
    rows = connection.execute(
        "SELECT sequence,event_type,event_time_ns,payload_json "
        "FROM paper_journal ORDER BY sequence"
    ).fetchall()
    previous = None
    final_state_json = None
    for sequence, event_type, event_time_ns, payload_json in rows:
        payload = json.loads(payload_json)
        mutate(sequence, event_type, payload)
        payload_json = canonical_json_bytes(payload).decode("utf-8")
        event_id = content_id(
            "paperevent:sha256:",
            {"event_type": event_type, "event_time_ns": event_time_ns, "data": payload["data"]},
        )
        digest = PaperStore._event_hash(
            sequence, event_id, event_type, event_time_ns, payload_json, previous
        )
        connection.execute(
            "UPDATE paper_journal SET event_id=?,payload_json=?,previous_event_hash=?,"
            "event_hash=? WHERE sequence=?",
            (event_id, payload_json, previous, digest, sequence),
        )
        previous = digest
        final_state_json = canonical_json_bytes(payload["state_after"]).decode("utf-8")
    connection.execute(
        "UPDATE paper_checkpoint SET state_json=?,state_hash=?,last_event_hash=? "
        "WHERE singleton=1",
        (
            final_state_json,
            __import__("hashlib").sha256(final_state_json.encode("utf-8")).hexdigest(),
            previous,
        ),
    )
    connection.commit()
    connection.close()


def test_restart_replays_exact_state_and_corruption_blocks_reconciliation(
    tmp_path,
) -> None:
    path = tmp_path / "paper.sqlite3"
    store, engine = make_engine(path)
    engine.process_market_event(paper_book(100))
    engine.submit(_intent(engine, quantity="4"))
    engine.process_market_event(paper_book(111, ask_size="2"))
    assert engine.state.orders[0].filled_quantity == "2"
    assert engine.state.orders[0].status == "CANCELLED"
    expected = engine.summary()
    expected_state = engine.state
    store.close()

    with PaperStore(path) as reopened:
        recovered = PaperEngine.open(reopened)
        assert recovered.state == expected_state
        assert recovered.summary() == expected

    connection = sqlite3.connect(path)
    connection.execute(
        "UPDATE paper_journal SET event_hash=? WHERE sequence=1", ("0" * 64,)
    )
    connection.commit()
    connection.close()
    with PaperStore(path) as corrupted:
        assert corrupted.reconciliation_blocked
        blocked = PaperEngine.open(corrupted)
        assert blocked.state.control_state == "RECONCILIATION_BLOCKED"
        with pytest.raises(PaperTradingError, match="RECONCILIATION_BLOCKED"):
            blocked.submit(_intent(blocked, decision=200))


def test_rehashed_logical_state_divergence_still_blocks_reconciliation(tmp_path) -> None:
    path = tmp_path / "logical-divergence.sqlite3"
    store, engine = make_engine(path)
    engine.process_market_event(paper_book(100))
    engine.submit(_intent(engine))
    store.close()

    connection = sqlite3.connect(path)
    rows = connection.execute(
        "SELECT sequence,event_id,event_type,event_time_ns,payload_json "
        "FROM paper_journal ORDER BY sequence"
    ).fetchall()
    payload = json.loads(rows[1][4])
    payload["state_after"]["marks"] = [["asset:a", "0.6"]]
    rows[1] = (*rows[1][:4], canonical_json_bytes(payload).decode("utf-8"))
    previous = None
    for sequence, event_id, event_type, event_time_ns, payload_json in rows:
        digest = PaperStore._event_hash(
            sequence,
            event_id,
            event_type,
            event_time_ns,
            payload_json,
            previous,
        )
        connection.execute(
            "UPDATE paper_journal SET payload_json=?,previous_event_hash=?,event_hash=? "
            "WHERE sequence=?",
            (payload_json, previous, digest, sequence),
        )
        previous = digest
    connection.execute(
        "UPDATE paper_checkpoint SET last_event_hash=? WHERE singleton=1", (previous,)
    )
    connection.commit()
    connection.close()

    with PaperStore(path) as rehashed:
        assert not rehashed.reconciliation_blocked
        blocked = PaperEngine.open(rehashed)
        assert blocked.state.control_state == "RECONCILIATION_BLOCKED"
        assert rehashed.reconciliation_blocked


def test_rehashed_intent_tamper_blocks_authoritative_recovery(tmp_path) -> None:
    path = tmp_path / "intent-tamper.sqlite3"
    store, engine = make_engine(path)
    engine.process_market_event(paper_book(100))
    engine.submit(_intent(engine))
    store.close()

    def mutate(_sequence, event_type, payload):
        if event_type == "ORDER_PENDING_RISK":
            intent = payload["data"]["intent"]
            intent["reference_price"] = "0.4"
            preimage = dict(intent)
            preimage.pop("intent_id")
            preimage.pop("simulated_paper_only")
            intent["intent_id"] = content_id("paperintent:sha256:", preimage)

    _rewrite_valid_chain(path, mutate)
    with PaperStore(path) as rehashed:
        assert not rehashed.reconciliation_blocked
        blocked = PaperEngine.open(rehashed)
        assert blocked.state.control_state == "RECONCILIATION_BLOCKED"
        assert rehashed.reconciliation_blocked


def test_rehashed_risk_decision_bypass_blocks_authoritative_recovery(tmp_path) -> None:
    path = tmp_path / "risk-bypass.sqlite3"
    store, engine = make_engine(path)
    engine.process_market_event(paper_book(100))
    engine.submit(_intent(engine))
    store.close()
    replacement_id = None

    def mutate(_sequence, event_type, payload):
        nonlocal replacement_id
        if event_type == "RISK_DECIDED":
            decision = payload["data"]
            decision["decided_time_ns"] = 102
            replacement_id = content_id(
                "paperrisk:sha256:",
                {
                    "intent_id": decision["intent_id"],
                    "result": decision["result"],
                    "reason_codes": decision["reason_codes"],
                    "decided_time_ns": decision["decided_time_ns"],
                    "limits_hash": decision["limits_hash"],
                },
            )
            decision["decision_id"] = replacement_id
            payload["state_after"]["risk_decisions"][-1] = dict(decision)
        elif event_type == "ORDER_OPENED":
            payload["data"]["risk_decision_id"] = replacement_id
            payload["state_after"]["risk_decisions"][-1]["decision_id"] = replacement_id
            payload["state_after"]["risk_decisions"][-1]["decided_time_ns"] = 102
            payload["state_after"]["orders"][0]["risk_decision_id"] = replacement_id

    _rewrite_valid_chain(path, mutate)
    with PaperStore(path) as rehashed:
        assert not rehashed.reconciliation_blocked
        blocked = PaperEngine.open(rehashed)
        assert blocked.state.control_state == "RECONCILIATION_BLOCKED"
        assert rehashed.reconciliation_blocked


@pytest.mark.parametrize("mutation", ["initial_cash", "limits_hash"])
def test_rehashed_cross_record_divergence_blocks_reconciliation(
    tmp_path, mutation
) -> None:
    path = tmp_path / f"cross-record-{mutation}.sqlite3"
    store, engine = make_engine(path)
    engine.process_market_event(paper_book(100))
    engine.submit(_intent(engine))
    store.close()

    connection = sqlite3.connect(path)
    rows = connection.execute(
        "SELECT sequence,event_id,event_type,event_time_ns,payload_json "
        "FROM paper_journal ORDER BY sequence"
    ).fetchall()
    payload = json.loads(rows[-1][4])
    if mutation == "initial_cash":
        payload["state_after"]["account"]["initial_cash"] = "101"
    else:
        payload["state_after"]["risk_decisions"][-1]["limits_hash"] = "0" * 64
    rows[-1] = (*rows[-1][:4], canonical_json_bytes(payload).decode("utf-8"))
    previous = None
    for sequence, event_id, event_type, event_time_ns, payload_json in rows:
        digest = PaperStore._event_hash(
            sequence, event_id, event_type, event_time_ns, payload_json, previous
        )
        connection.execute(
            "UPDATE paper_journal SET payload_json=?,previous_event_hash=?,event_hash=? "
            "WHERE sequence=?",
            (payload_json, previous, digest, sequence),
        )
        previous = digest
    connection.execute(
        "UPDATE paper_checkpoint SET state_json=?,last_event_hash=? WHERE singleton=1",
        (canonical_json_bytes(payload["state_after"]).decode("utf-8"), previous),
    )
    connection.commit()
    connection.close()

    with PaperStore(path) as rehashed:
        with pytest.raises(PaperTradingError, match="RECONCILIATION_BLOCKED"):
            PaperEngine.open(rehashed)
        assert rehashed.reconciliation_blocked


def test_transaction_failure_cannot_leave_fill_without_journal_or_accounting(
    tmp_path, monkeypatch
) -> None:
    path = tmp_path / "paper.sqlite3"
    store, engine = make_engine(path)
    engine.process_market_event(paper_book(100))
    engine.submit(_intent(engine))
    before_events = store.events()
    before_state = engine.state

    def fail_checkpoint(*_args):
        raise RuntimeError("synthetic transaction fault")

    monkeypatch.setattr(store, "_write_checkpoint", fail_checkpoint)
    with pytest.raises(PaperTradingError, match="TRANSACTION_FAILED"):
        engine.process_market_event(paper_book(111))
    assert store.events() == before_events
    assert engine.state == before_state
    assert not any(event.event_type == "PAPER_FILL" for event in store.events())
    store.close()


def test_duplicate_retry_is_idempotent_and_conflicting_identity_rejects(
    tmp_path,
) -> None:
    store, engine = make_engine(tmp_path / "paper.sqlite3")
    engine.process_market_event(paper_book(100))
    intent = _intent(engine)
    first = engine.submit(intent)
    count = len(store.events())
    assert engine.submit(intent) == first and len(store.events()) == count
    from dataclasses import replace

    with pytest.raises(PaperTradingError, match="INTENT_INVALID"):
        engine.submit(replace(intent, quantity="3"))
    store.close()


def test_wrong_schema_and_symlink_or_hardlink_paths_fail_closed(tmp_path) -> None:
    foreign = tmp_path / "foreign.sqlite3"
    sqlite3.connect(foreign).close()
    with pytest.raises(PaperTradingError, match="SOURCE_UNAVAILABLE"):
        PaperStore(foreign)
    path = tmp_path / "paper.sqlite3"
    store, _engine = make_engine(path)
    store.close()
    alias = tmp_path / "alias.sqlite3"
    try:
        alias.hardlink_to(path)
    except OSError:
        pytest.skip("hard links unavailable")
    with pytest.raises(PaperTradingError, match="SOURCE_UNAVAILABLE"):
        PaperStore(alias)
