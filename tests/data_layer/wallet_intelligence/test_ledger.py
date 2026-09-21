"""Wallet evidence ledger tests (S10-WALLET-01, Section 12)."""

from __future__ import annotations

import itertools
import sqlite3
from dataclasses import replace

import pytest

from src.data_layer.point_in_time_market_research.records import (
    canonical_json_bytes,
    sha256_hex,
)
from src.data_layer.point_in_time_market_research.research_provenance import (
    build_pit_timestamps,
    build_raw_evidence_reference,
)
from src.data_layer.wallet_intelligence import contracts as c
from src.data_layer.wallet_intelligence import ledger as L


def _new_ledger(tmp_path, name="w.sqlite"):
    path = str(tmp_path / name)
    result = L.initialize_wallet_evidence_ledger(path)
    assert result.is_valid and result.status == "LEDGER_INITIALIZED"
    return path


def _pit():
    return build_pit_timestamps(
        local_first_seen_time="2026-01-02T00:00:00Z", ingestion_time="2026-01-02T00:00:01Z"
    )


def _raw():
    return build_raw_evidence_reference(
        source_system="POLYMARKET_DATA_API_V2",
        endpoint="/v2/trades",
        retrieval_method="GET/urllib",
        content_sha256="a" * 64,
        byte_length=10,
        media_type="application/json",
        pit=_pit(),
        dq_flags=["OK"],
        replay_fidelity="FAITHFUL",
        request_parameters={"user": "0x" + "1" * 40},
    )


def _run_key():
    return c.derive_ingest_run_key({"wallet": "0x" + "1" * 40, "feeds": ["TRADES"]})


def _event():
    return c.build_wallet_evidence_event(
        identity_strength="SOURCE_CONTENT_DERIVED",
        canonical_event_type="TRADE_FILL",
        canonical_wallet="0x" + "1" * 40,
        combo_state="UNKNOWN",
        source_system_family="POLYMARKET_DATA_API_V2",
        side="BUY",
        price="0.5",
        size="10",
        event_time="2026-01-01T00:00:00Z",
        transaction_hash="0x" + "a" * 64,
    )


def _page(raw, run_key):
    return c.build_wallet_feed_page_evidence(
        raw_evidence_reference_id=raw.raw_evidence_reference_id,
        ingest_run_key=run_key,
        feed_key="TRADES",
        canonical_request_identity={"user": "0x" + "1" * 40, "taker_only": "false"},
        requested_page_size=100,
        has_more=False,
        local_first_seen_time="2026-01-02T00:00:00Z",
        ingestion_time="2026-01-02T00:00:01Z",
        api_source_parser_version="v/1",
        dq_flags=["OK"],
        replay_fidelity="FAITHFUL",
        source_row_count=1,
        normalized_event_count=1,
        observation_count=1,
    )


def _obs(event, page, raw, run_key):
    return c.build_wallet_event_observation(
        wallet_event_id=event.wallet_event_id,
        wallet_feed_page_evidence_id=page.wallet_feed_page_evidence_id,
        ingest_run_key=run_key,
        source_system="POLYMARKET_DATA_API_V2",
        endpoint="/v2/trades",
        source_activity_type="TRADE",
        pit=_pit(),
        dq_flags=["OK"],
        replay_fidelity="FAITHFUL",
        raw_evidence_reference_id=raw.raw_evidence_reference_id,
    )


def _std_batch(run_key=None):
    run_key = run_key or _run_key()
    raw = _raw()
    event = _event()
    page = _page(raw, run_key)
    obs = _obs(event, page, raw, run_key)
    return [raw, event, page, obs]


# ---------------------------------------------------------------------------
# Application id + schema.
# ---------------------------------------------------------------------------
def test_application_id_is_unique_nonzero():
    assert L.WALLET_EVIDENCE_LEDGER_APPLICATION_ID == 0x57414C31
    # Distinct from the Alpha Factory registry application id (WP175N) and zero.
    assert L.WALLET_EVIDENCE_LEDGER_APPLICATION_ID not in (0, 1464877425)


def test_initialize_sets_application_id(tmp_path):
    path = _new_ledger(tmp_path)
    conn = sqlite3.connect(path)
    try:
        assert conn.execute("PRAGMA application_id").fetchone() == (
            L.WALLET_EVIDENCE_LEDGER_APPLICATION_ID,
        )
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Append + verified load + idempotency.
# ---------------------------------------------------------------------------
def test_append_and_verified_load(tmp_path):
    path = _new_ledger(tmp_path)
    res = L.append_wallet_evidence_records(path, _std_batch())
    assert res.is_valid and res.status == "LEDGER_APPEND_COMMITTED"
    assert len(res.inserted_record_ids) == 4
    loaded = L.load_and_verify_wallet_evidence_ledger(path)
    assert loaded.status == "LEDGER_LOADED_VERIFIED"
    assert len(loaded.snapshot.entries) == 4


def test_exact_duplicate_idempotent(tmp_path):
    path = _new_ledger(tmp_path)
    batch = _std_batch()
    L.append_wallet_evidence_records(path, batch)
    res = L.append_wallet_evidence_records(path, batch)
    assert res.status == "LEDGER_APPEND_IDEMPOTENT"
    assert len(res.idempotent_record_ids) == 4


def test_same_id_different_payload_conflict(tmp_path):
    path = _new_ledger(tmp_path)
    event = _event()
    L.append_wallet_evidence_records(path, [event])
    # cost_basis_state is NOT in the identity preimage, so this variant keeps the
    # same wallet_event_id but a different stored payload -> conflict.
    variant = replace(event, cost_basis_state="UNKNOWN")
    res = L.append_wallet_evidence_records(path, [variant])
    assert not res.is_valid
    assert res.error_codes == ("LEDGER_IDENTITY_CONFLICT",)


# ---------------------------------------------------------------------------
# Caller-order-independent canonical order (R-V2-09).
# ---------------------------------------------------------------------------
def test_permutation_independent_head_and_sequence(tmp_path):
    batch = _std_batch()
    heads = set()
    kind_orders = set()
    for i, perm in enumerate(itertools.permutations(batch)):
        path = _new_ledger(tmp_path, f"perm{i}.sqlite")
        res = L.append_wallet_evidence_records(path, list(perm))
        assert res.is_valid
        heads.add(res.snapshot.head_hash)
        kind_orders.add(tuple(e.record_kind for e in res.snapshot.entries))
    assert len(heads) == 1
    assert len(kind_orders) == 1
    # Canonical dependency order: raw -> event -> page -> observation.
    assert next(iter(kind_orders)) == (
        "RAW_EVIDENCE_REFERENCE",
        "WALLET_EVIDENCE_EVENT",
        "WALLET_FEED_PAGE_EVIDENCE",
        "WALLET_EVENT_OBSERVATION",
    )


# ---------------------------------------------------------------------------
# Reference integrity (R-V2-10).
# ---------------------------------------------------------------------------
def test_missing_reference_rejects(tmp_path):
    path = _new_ledger(tmp_path)
    run_key = _run_key()
    raw = _raw()
    page = _page(raw, run_key)
    event = _event()
    # Observation references an event that is NOT in the batch or ledger.
    obs = _obs(event, page, raw, run_key)
    res = L.append_wallet_evidence_records(path, [raw, page, obs])
    assert not res.is_valid
    assert res.error_codes == ("REFERENCE_INVALID",)


def test_wrong_type_reference_rejects(tmp_path):
    path = _new_ledger(tmp_path)
    run_key = _run_key()
    event = _event()
    # A page whose raw_evidence_reference_id points at an EVENT id (wrong type).
    page = c.build_wallet_feed_page_evidence(
        raw_evidence_reference_id=event.wallet_event_id,
        ingest_run_key=run_key,
        feed_key="TRADES",
        canonical_request_identity={"user": "0x" + "1" * 40},
        requested_page_size=100,
        has_more=False,
        local_first_seen_time="2026-01-02T00:00:00Z",
        ingestion_time="2026-01-02T00:00:01Z",
        api_source_parser_version="v/1",
        dq_flags=["OK"],
        replay_fidelity="FAITHFUL",
        source_row_count=0,
        normalized_event_count=0,
        observation_count=0,
    )
    res = L.append_wallet_evidence_records(path, [event, page])
    assert not res.is_valid
    assert res.error_codes == ("REFERENCE_TYPE_INVALID",)


def test_supersession_cycle_rejects(tmp_path):
    path = _new_ledger(tmp_path)
    e1 = _event()
    e2 = c.build_wallet_evidence_event(
        identity_strength="SOURCE_CONTENT_DERIVED",
        canonical_event_type="TRADE_FILL",
        canonical_wallet="0x" + "1" * 40,
        combo_state="UNKNOWN",
        source_system_family="POLYMARKET_DATA_API_V2",
        side="SELL",
        price="0.4",
        size="5",
        event_time="2026-01-01T00:00:00Z",
        transaction_hash="0x" + "b" * 64,
    )
    link1 = c.build_wallet_reconciliation_link(
        reconciliation_state="SUPERSEDED_BY_STRONGER_EVIDENCE",
        relation_kind="SUPERSESSION",
        event_ids=(e1.wallet_event_id, e2.wallet_event_id),
        predecessor_event_id=e1.wallet_event_id,
        successor_event_id=e2.wallet_event_id,
    )
    link2 = c.build_wallet_reconciliation_link(
        reconciliation_state="SUPERSEDED_BY_STRONGER_EVIDENCE",
        relation_kind="SUPERSESSION",
        event_ids=(e2.wallet_event_id, e1.wallet_event_id),
        predecessor_event_id=e2.wallet_event_id,
        successor_event_id=e1.wallet_event_id,
    )
    res = L.append_wallet_evidence_records(path, [e1, e2, link1, link2])
    assert not res.is_valid
    assert res.error_codes == ("REFERENCE_CYCLE",)


# ---------------------------------------------------------------------------
# Atomicity (R-W18).
# ---------------------------------------------------------------------------
def test_rejected_batch_leaves_ledger_unchanged(tmp_path):
    path = _new_ledger(tmp_path)
    L.append_wallet_evidence_records(path, _std_batch())
    before = L.load_and_verify_wallet_evidence_ledger(path).snapshot
    # A batch with a good new record plus a bad (missing-ref) record.
    run_key = _run_key()
    raw2 = build_raw_evidence_reference(
        source_system="POLYMARKET_DATA_API_V2",
        endpoint="/v2/activity",
        retrieval_method="GET/urllib",
        content_sha256="c" * 64,
        byte_length=5,
        media_type="application/json",
        pit=_pit(),
        dq_flags=["OK"],
        replay_fidelity="FAITHFUL",
    )
    bad_obs = _obs(_event(), _page(raw2, run_key), raw2, run_key)  # page not in batch
    res = L.append_wallet_evidence_records(path, [raw2, bad_obs])
    assert not res.is_valid
    after = L.load_and_verify_wallet_evidence_ledger(path).snapshot
    assert len(after.entries) == len(before.entries)
    assert after.head_hash == before.head_hash


# ---------------------------------------------------------------------------
# Append-only: UPDATE / DELETE forbidden.
# ---------------------------------------------------------------------------
def test_update_and_delete_are_blocked(tmp_path):
    path = _new_ledger(tmp_path)
    L.append_wallet_evidence_records(path, _std_batch())
    conn = sqlite3.connect(path)
    try:
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("UPDATE ledger_entries SET payload_json='x' WHERE sequence_number=0")
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("DELETE FROM ledger_entries WHERE sequence_number=0")
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Self-consistent semantic corruption (R-W17).
# ---------------------------------------------------------------------------
def test_self_consistent_semantic_corruption_fails_verified_load(tmp_path):
    path = _new_ledger(tmp_path)
    event = _event()
    L.append_wallet_evidence_records(path, [event])
    assert L.load_and_verify_wallet_evidence_ledger(path).is_valid

    # Build a semantically INVALID payload (bad cost_basis enum) that keeps the
    # same content-addressed id (cost_basis is not in the identity preimage) and
    # recompute payload sha + entry hash so identity/crypto are self-consistent.
    payload = L._serialize(event, c.RECORD_KIND_WALLET_EVIDENCE_EVENT)
    payload["cost_basis_state"] = "BOGUS_STATE"
    payload_bytes = canonical_json_bytes(payload)
    payload_json = payload_bytes.decode("utf-8")
    payload_sha = sha256_hex(payload_bytes)
    entry_hash = L._entry_hash(
        L._GENESIS_HASH, c.RECORD_KIND_WALLET_EVIDENCE_EVENT, event.wallet_event_id, payload_sha
    )

    # Rebuild the file with the corrupted row inserted before triggers block writes.
    import os

    os.remove(path)
    conn = sqlite3.connect(path)
    try:
        conn.execute("PRAGMA journal_mode=DELETE")
        conn.execute(L._CREATE_META)
        conn.execute(L._CREATE_ENTRIES)
        conn.execute(
            "INSERT INTO ledger_meta (singleton, format_id, schema_version) VALUES (1, ?, ?)",
            (L.WALLET_EVIDENCE_LEDGER_FORMAT_ID, L.WALLET_EVIDENCE_LEDGER_SCHEMA_VERSION),
        )
        conn.execute(
            "INSERT INTO ledger_entries (sequence_number, record_id, record_kind, "
            "payload_json, payload_sha256, prev_hash, entry_hash) VALUES (0, ?, ?, ?, ?, ?, ?)",
            (
                event.wallet_event_id,
                c.RECORD_KIND_WALLET_EVIDENCE_EVENT,
                payload_json,
                payload_sha,
                L._GENESIS_HASH,
                entry_hash,
            ),
        )
        conn.execute(L._CREATE_NO_UPDATE)
        conn.execute(L._CREATE_NO_DELETE)
        conn.execute(f"PRAGMA application_id={L.WALLET_EVIDENCE_LEDGER_APPLICATION_ID}")
        conn.execute(f"PRAGMA user_version={L.WALLET_EVIDENCE_LEDGER_SCHEMA_VERSION}")
        conn.commit()
    finally:
        conn.close()

    result = L.load_and_verify_wallet_evidence_ledger(path)
    assert not result.is_valid
    assert result.error_codes == ("LEDGER_INTEGRITY_TAMPER",)


def test_query_by_ingest_run_key(tmp_path):
    path = _new_ledger(tmp_path)
    run_key = _run_key()
    L.append_wallet_evidence_records(path, _std_batch(run_key))
    snapshot = L.load_and_verify_wallet_evidence_ledger(path).snapshot
    tagged = L.query_records_by_ingest_run_key(snapshot, run_key)
    # page + observation carry the key; raw + event do not.
    kinds = sorted({t.record_kind for t in tagged})
    assert kinds == ["WALLET_EVENT_OBSERVATION", "WALLET_FEED_PAGE_EVIDENCE"]
