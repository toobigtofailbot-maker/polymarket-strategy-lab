import sqlite3
import json

import pytest

from src.paper_trading import (
    PaperEngine,
    PaperStore,
    PaperTradingError,
    build_paper_intent,
)
from src.paper_trading.models import canonical_json_bytes

from conftest import make_engine, paper_book


def _intent(engine, *, decision=101, quantity="2"):
    return build_paper_intent(
        engine.state.binding,
        market_id="market:a",
        asset_id="asset:a",
        side="BUY",
        quantity=quantity,
        order_style="AGGRESSIVE_TAKER",
        reference_price="0.5",
        decision_time_ns=decision,
    )


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
