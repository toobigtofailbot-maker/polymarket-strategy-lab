"""WP169 focused tests: records, identities, store, and PIT promotion."""

from __future__ import annotations

import dataclasses
import json
import pathlib

import pytest

from src.data_layer.polymarket import market_truth as mt
from src.data_layer.polymarket.market_truth_store import MarketTruthStore

CONDITION = "0x" + "a" * 64
RECEIVED = "2024-07-03T09:46:40.000000Z"


def _tmpdb(tmp_path: pathlib.Path, name: str = "wp169.sqlite3") -> pathlib.Path:
    return tmp_path / name


def _book_raw(seq: int = 0, ts: str = "1720000000000") -> mt.RawEnvelope:
    body = json.dumps(
        {
            "event_type": "book",
            "asset_id": "7",
            "market": CONDITION,
            "timestamp": ts,
            "bids": [{"price": "0.40", "size": "12"}],
            "asks": [{"price": "0.60", "size": "8"}],
        }
    ).encode()
    return mt.make_raw_envelope(
        "WS", "polymarket:market-ws", f"ws:00000000-0000-4000-8000-000000000000:frame:{seq}", RECEIVED, body,
        occurrence_sequence=seq,
    )


def test_raw_and_normalized_identity_is_lossless_and_bounded() -> None:
    raw = _book_raw()
    # Content identity is reproducible from the exact bytes and excludes receive time.
    assert raw.raw_id.startswith("markettruth:raw:sha256:")
    assert raw.raw_sha256 == mt.sha256_hex(raw.raw_bytes)
    again = mt.compute_raw_id(
        source_kind="WS", source_id="polymarket:market-ws",
        media_type="application/json", raw_sha256=raw.raw_sha256,
        byte_length=raw.byte_length,
    )
    assert again == raw.raw_id
    # Occurrence identity differs when receive time / sequence differ.
    other = mt.make_raw_envelope(
        "WS", "polymarket:market-ws", "ws:00000000-0000-4000-8000-000000000000:frame:0",
        "2024-07-03T09:46:41.000000Z", raw.raw_bytes, occurrence_sequence=0,
    )
    assert other.raw_id == raw.raw_id  # same content
    assert other.occurrence_id != raw.occurrence_id  # different knowability
    obs = mt.normalize_websocket_message(raw, book_readiness={})
    assert len(obs) == 1 and obs[0].status == "ACCEPTED"
    assert obs[0].event_time == "2024-07-03T09:46:40.000000Z"
    assert obs[0].canonical_payload_sha256 == mt.sha256_hex(
        obs[0].canonical_payload_json.encode("utf-8")
    )
    # canonical_json rejects float / oversize.
    with pytest.raises(mt.MarketTruthError):
        mt.canonical_json_bytes({"x": 1.5})
    with pytest.raises(mt.MarketTruthError):
        mt.canonical_json_bytes({}, max_bytes=0)


def test_normalization_failure_still_archives_exact_raw_bytes(tmp_path) -> None:
    # Non-object JSON frame -> quarantined observation, raw bytes preserved exactly.
    raw = mt.make_raw_envelope(
        "WS", "polymarket:market-ws", "ws:00000000-0000-4000-8000-000000000000:frame:0", RECEIVED, b"[1,2,3]",
        occurrence_sequence=0,
    )
    obs = mt.normalize_websocket_message(raw, book_readiness={})
    assert obs[0].status in ("QUARANTINED", "UNSUPPORTED")
    with MarketTruthStore(_tmpdb(tmp_path)) as store:
        receipt = store.append(raw, obs)
        assert receipt.status == "OK"
        stored = store.iter_normalized()
        assert stored[0].status in ("QUARANTINED", "UNSUPPORTED")
        # raw bytes are retained byte-identically.
        conn = store._require()
        row = conn.execute("SELECT raw_bytes FROM raw_occurrences").fetchone()
        assert bytes(row[0]) == b"[1,2,3]"
    # No invalid-input echo in the receipt surface.
    assert mt.scan_no_echo(
        {"status": receipt.status, "error_codes": list(receipt.error_codes)}
    )


def test_output_database_path_and_existing_schema_fail_closed(tmp_path) -> None:
    # :memory:, wrong suffix, directory, and missing parent all fail closed.
    for bad in (":memory:", str(tmp_path / "x.db"), str(tmp_path)):
        with pytest.raises(mt.MarketTruthError) as excinfo:
            MarketTruthStore(bad)
        assert excinfo.value.code == "STORE_CONFLICT"
    missing_parent = tmp_path / "nope" / "x.sqlite3"
    with pytest.raises(mt.MarketTruthError):
        MarketTruthStore(missing_parent)
    # A corrupt/foreign existing file is never overwritten.
    import sqlite3

    foreign = _tmpdb(tmp_path, "foreign.sqlite3")
    conn = sqlite3.connect(str(foreign))
    conn.execute("CREATE TABLE x(a)")
    conn.commit()
    conn.close()
    store = MarketTruthStore(foreign)
    with pytest.raises(mt.MarketTruthError) as excinfo:
        store.initialize()
    assert excinfo.value.code == "STORE_CONFLICT"
    # Uninitialized store append is STORE_NOT_INITIALIZED.
    fresh = MarketTruthStore(_tmpdb(tmp_path, "fresh.sqlite3"))
    with pytest.raises(mt.MarketTruthError) as excinfo:
        fresh.append(_book_raw())
    assert excinfo.value.code == "STORE_NOT_INITIALIZED"


def test_store_idempotency_multiplicity_and_limits(tmp_path) -> None:
    raw = _book_raw()
    obs = mt.normalize_websocket_message(raw, book_readiness={})
    with MarketTruthStore(_tmpdb(tmp_path)) as store:
        r1 = store.append(raw, obs)
        r2 = store.append(raw, obs)  # idempotent
        assert r1.raw_count == r2.raw_count == 1
        assert r1.normalized_count == r2.normalized_count == 1
        # Byte-identical bytes received later is a distinct occurrence row.
        later = mt.make_raw_envelope(
            "WS", "polymarket:market-ws", "ws:00000000-0000-4000-8000-000000000000:frame:9",
            "2024-07-03T09:47:00.000000Z", raw.raw_bytes, occurrence_sequence=9,
        )
        store.append(later, mt.normalize_websocket_message(later, book_readiness={}))
        assert store.receipt().raw_count == 2
    # Store row limit is terminal and visible.
    limits = mt.AcquisitionLimits(max_store_rows=1)
    with MarketTruthStore(_tmpdb(tmp_path, "bounded.sqlite3"), limits) as store:
        receipt = store.append(raw, obs)
        assert receipt.status == "FAILED" and receipt.error_codes == ("STORE_LIMIT_EXCEEDED",)


def test_provenance_and_checkpoint_hash_chains_are_exact(tmp_path) -> None:
    raw = _book_raw()
    obs = mt.normalize_websocket_message(raw, book_readiness={})[0]
    provenance = json.loads(obs.provenance_json)
    assert set(provenance) == {"normalizer_version", "frame_event_type", "child_index", "event_hash"}
    # Independent observation-id recomputation.
    recomputed = mt.compute_observation_id(
        source_content_id=raw.raw_id, source_kind="WS", event_kind="book",
        event_id=None, market_id=CONDITION, asset_id="7",
        event_time=obs.event_time, canonical_payload_sha256=obs.canonical_payload_sha256,
        status="ACCEPTED", error_codes=(), book_ready=True, provenance_json=obs.provenance_json,
    )
    assert recomputed == obs.observation_id
    with MarketTruthStore(_tmpdb(tmp_path)) as store:
        c1 = store.write_checkpoint("chain:137:order-filled-v2", {"chain_id": 137, "last_verified_block": None, "last_verified_block_hash": None}, "ACTIVE")
        c2 = store.write_checkpoint("chain:137:order-filled-v2", {"chain_id": 137, "last_verified_block": 10, "last_verified_block_hash": "0x" + "a" * 64}, "ACTIVE")
        assert c1.previous_sha256 is None and c2.previous_sha256 == c1.value_sha256
        assert c2.value_sha256 == mt.compute_checkpoint_sha256(
            checkpoint_key="chain:137:order-filled-v2", sequence=2, state="ACTIVE",
            value_json=c2.value_json, previous_sha256=c1.value_sha256,
        )
        loaded = store.load_checkpoint("chain:137:order-filled-v2")
        assert loaded.sequence == 2 and loaded.history_sequence == 2


def _new_market_obs() -> tuple[mt.RawEnvelope, mt.NormalizedObservation]:
    body = json.dumps(
        {
            "event_type": "new_market",
            "condition_id": CONDITION,
            "question": "Will X happen?",
            "outcomes": ["Yes", "No"],
            "event_message": {"id": "12345"},
            "timestamp": "1720000000000",
        }
    ).encode()
    raw = mt.make_raw_envelope(
        "WS", "polymarket:market-ws", "ws:00000000-0000-4000-8000-000000000000:frame:0", RECEIVED, body, occurrence_sequence=0
    )
    return raw, mt.normalize_websocket_message(raw, book_readiness={})[0]


def test_only_accepted_supported_observation_builds_existing_pit_record() -> None:
    raw, obs = _new_market_obs()
    ok = mt.build_point_in_time_observation(
        raw, obs, ingestion_batch_id="batch:wp169:1", snapshot_id="snap:wp169:1"
    )
    assert ok.is_valid and ok.status == "ACCEPTED"
    assert ok.source_snapshot_result is not None and ok.source_snapshot_result.is_valid
    assert ok.observation_result is not None and ok.observation_result.is_valid
    # order_filled is acquisition-only and rejects promotion.
    of_raw = mt.make_raw_envelope(
        "DATA", "polymarket:data-api:activity", "http:activity:offset:0:attempt:0",
        RECEIVED, json.dumps({"type": "SPLIT", "conditionId": CONDITION, "timestamp": 1720000000}).encode(),
        occurrence_sequence=0,
    )
    of_obs = mt.normalize_public_record(of_raw, endpoint="activity", record_index=0)
    rejected = mt.build_point_in_time_observation(
        of_raw, of_obs, ingestion_batch_id="batch:wp169:1", snapshot_id="snap:wp169:1"
    )
    assert not rejected.is_valid and rejected.error_codes == ("PIT_PROMOTION_FORBIDDEN",)


def test_occurrence_id_is_revalidated_and_tamper_fails_closed(tmp_path) -> None:
    """F: the store recomputes occurrence_id from the frozen cursor grammar; tampering
    the occurrence_id, cursor, or receive time fails closed with STORE_CONFLICT."""
    raw = mt.make_raw_envelope(
        "WS", "polymarket:market-ws", "ws:00000000-0000-4000-8000-000000000000:frame:3", RECEIVED,
        json.dumps({"event_type": "book", "asset_id": "7", "market": CONDITION,
                    "timestamp": "1720000000000", "bids": [{"price": "0.4", "size": "12"}],
                    "asks": [{"price": "0.6", "size": "8"}]}).encode(),
        occurrence_sequence=3,
    )
    obs = mt.normalize_websocket_message(raw, book_readiness={})
    with MarketTruthStore(_tmpdb(tmp_path)) as store:
        assert store.append(raw, obs).status == "OK"
        # Tampered occurrence_id.
        bad_occ = dataclasses.replace(raw, occurrence_id="markettruth:occurrence:sha256:" + "0" * 64)
        assert store.append(bad_occ).error_codes == ("STORE_CONFLICT",)
        # Tampered receive time (occurrence recompute mismatch).
        bad_time = dataclasses.replace(raw, received_at="2024-07-03T09:46:41.000000Z")
        assert store.append(bad_time).error_codes == ("STORE_CONFLICT",)
        # Tampered cursor (sequence no longer matches the occurrence_id).
        bad_cursor = dataclasses.replace(raw, source_cursor="ws:00000000-0000-4000-8000-000000000000:frame:9")
        assert store.append(bad_cursor).error_codes == ("STORE_CONFLICT",)


def test_data_api_timestamps_are_seconds_websocket_are_milliseconds() -> None:
    """G: Data API integer timestamps are Unix seconds; WebSocket are milliseconds; both
    resolve to the same UTC instant for the certified regression values."""
    http_raw = mt.make_raw_envelope(
        "DATA", "polymarket:data-api:trades", "http:trades:offset:0:attempt:0", RECEIVED,
        json.dumps({"conditionId": CONDITION, "price": "0.5", "size": "1", "side": "BUY",
                    "transactionHash": "0x" + "c" * 64, "timestamp": 1720000000}).encode(),
        occurrence_sequence=0,
    )
    http_obs = mt.normalize_public_record(http_raw, endpoint="trades", record_index=0)
    assert http_obs.event_time == "2024-07-03T09:46:40.000000Z"
    ws_raw = _book_raw(ts="1720000000000")
    ws_obs = mt.normalize_websocket_message(ws_raw, book_readiness={})[0]
    assert ws_obs.event_time == "2024-07-03T09:46:40.000000Z"


def test_dynamic_config_versions_change_without_historical_rewrite(tmp_path) -> None:
    """I: the full Gamma/CLOB dynamic-config allowlist is normalized with explicit nulls,
    and a changed parameter yields a new observation version without rewriting history."""
    def config_raw(seq: int, tick: str) -> mt.RawEnvelope:
        body = json.dumps({
            "conditionId": CONDITION, "asset": "7", "min_order_size": "5",
            "tick_size": tick, "neg_risk": False, "secondsDelay": 3, "feesEnabled": True,
            "base_fee": "10", "mos": "5", "mts": "0.01",
        }).encode()
        return mt.make_raw_envelope(
            "CLOB", "polymarket:clob:book", f"http:book:offset:0:attempt:{seq}", RECEIVED,
            body, occurrence_sequence=seq,
        )

    first = mt.normalize_public_record(config_raw(0, "0.01"), endpoint="book", record_index=0)
    payload = json.loads(first.canonical_payload_json)
    # Full allowlist present with explicit nulls for absent optionals.
    for key in ("min_order_size", "tick_size", "neg_risk", "base_fee", "mos", "mts",
                "mbf", "tbf", "rfqe", "secondsDelay", "feesEnabled", "clobTokenIds"):
        assert key in payload, key
    assert payload["mbf"] is None  # absent optional preserved as explicit null
    second = mt.normalize_public_record(config_raw(1, "0.02"), endpoint="book", record_index=0)
    # A changed tick_size yields a distinct observation identity (new version).
    assert first.observation_id != second.observation_id
    with MarketTruthStore(_tmpdb(tmp_path)) as store:
        store.append(config_raw(0, "0.01"), (first,))
        store.append(config_raw(1, "0.02"), (second,))
        stored = [o for o in store.iter_normalized(limit=100) if o.event_kind == "dynamic_config"]
        assert len(stored) == 2  # both versions retained, no historical rewrite


def test_pit_source_snapshot_and_context_mappings_are_exact() -> None:
    raw, obs = _new_market_obs()
    result = mt.build_point_in_time_observation(
        raw, obs, ingestion_batch_id="batch:wp169:1", snapshot_id="snap:wp169:1"
    )
    source_record = result.source_snapshot_result.record
    observation_record = result.observation_result.record
    # The adapter binds the built source snapshot id (never fabricates a raw id).
    assert observation_record.envelope.source_snapshot_id == source_record.envelope.source_snapshot_id
    assert source_record.source_type == "POLYMARKET_PUBLIC_API"
    assert source_record.access_classification == "PUBLIC"
    assert source_record.raw_content_sha256 == raw.raw_sha256
    # Namespaced ids and non-namespaced source_assertion_id.
    assert observation_record.platform_id == "platform:polymarket"
    assert observation_record.market_id == "market:polymarket:" + CONDITION
    assert observation_record.event_id == "event:polymarket:12345"
    assert observation_record.source_assertion_id.startswith("sha256:")
    # market_resolved requires exact market context (no self event id).
    resolved_body = json.dumps(
        {"event_type": "market_resolved", "condition_id": CONDITION, "timestamp": "1720000005000"}
    ).encode()
    resolved_raw = mt.make_raw_envelope(
        "WS", "polymarket:market-ws", "ws:00000000-0000-4000-8000-000000000000:frame:5", "2024-07-03T09:46:45.000000Z",
        resolved_body, occurrence_sequence=5,
    )
    resolved_obs = mt.normalize_websocket_message(resolved_raw, book_readiness={})[0]
    without_context = mt.build_point_in_time_observation(
        resolved_raw, resolved_obs, ingestion_batch_id="batch:wp169:1", snapshot_id="snap:wp169:1"
    )
    assert not without_context.is_valid and without_context.error_codes == ("PIT_PROMOTION_FORBIDDEN",)


def test_result_field_coverage_and_no_echo() -> None:
    """Contract: every field of every classified public dataclass is exactly classified
    (adding an unclassified field fails), and diagnostic/invalid results are no-echo clean."""
    for name, classification in mt.FIELD_CLASSIFICATION.items():
        cls = getattr(mt, name)
        fields = {f.name for f in dataclasses.fields(cls)}
        assert set(classification) == fields, name  # exact coverage: none missing, none extra
        assert set(classification.values()) <= {"scalar", "scan", "raw_evidence"}, name
    # A sanitized invalid result carries no forbidden echo content.
    receipt = mt.AcquisitionReceipt("FAILED", ("STORE_CONFLICT",), 0, 0, 0, 0, 0, 0, "NONE")
    assert mt.scan_no_echo(
        {f.name: getattr(receipt, f.name) for f in dataclasses.fields(receipt)}
    )


def test_identical_reappend_succeeds_at_store_row_limit(tmp_path) -> None:
    """SEED09: an exact re-append of an already-committed raw+children adds zero rows and
    must succeed at the store row limit (idempotent), not fail STORE_LIMIT_EXCEEDED."""
    raw = _book_raw()
    obs = mt.normalize_websocket_message(raw, book_readiness={})
    # One append(raw, obs) creates exactly 2 rows (1 raw + 1 normalized).
    with MarketTruthStore(_tmpdb(tmp_path, "limit_idem.sqlite3"), mt.AcquisitionLimits(max_store_rows=2)) as store:
        assert store.append(raw, obs).status == "OK"
        again = store.append(raw, obs)  # identical re-append at the exact limit
        assert again.status == "OK", again
        assert again.raw_count == 1 and again.normalized_count == 1


def test_load_checkpoint_detects_tampered_history_chain(tmp_path) -> None:
    """F10: load_checkpoint verifies the complete value-hash chain; a tampered history row
    fails closed with STORE_CONFLICT."""
    with MarketTruthStore(_tmpdb(tmp_path, "tamper.sqlite3")) as store:
        key = "chain:137:order-filled-v2"
        store.write_checkpoint(key, {"chain_id": 137, "last_verified_block": None, "last_verified_block_hash": None}, "ACTIVE")
        store.write_checkpoint(key, {"chain_id": 137, "last_verified_block": 10, "last_verified_block_hash": "0x" + "a" * 64}, "ACTIVE")
        conn = store._require()
        conn.execute("UPDATE checkpoint_history SET value_json=? WHERE sequence=1", ('{"tampered":true}',))
        with pytest.raises(mt.MarketTruthError) as excinfo:
            store.load_checkpoint(key)
        assert excinfo.value.code == "STORE_CONFLICT"


def test_event_id_rejects_noncanonical_leading_zeros() -> None:
    """ADD03 / Reviewer A#5: a padded event id ('007') is not a positive canonical base-10
    id and must not be accepted; a canonical id is accepted."""
    def new_market(event_id: str, seq: int) -> mt.NormalizedObservation:
        body = json.dumps({
            "event_type": "new_market", "condition_id": CONDITION, "question": "Q",
            "outcomes": ["Yes", "No"], "event_message": {"id": event_id},
            "timestamp": "1720000000000",
        }).encode()
        raw = mt.make_raw_envelope("WS", "polymarket:market-ws", f"ws:00000000-0000-4000-8000-000000000000:frame:{seq}", RECEIVED, body, occurrence_sequence=seq)
        return mt.normalize_websocket_message(raw, book_readiness={})[0]

    assert new_market("007", 0).event_id is None
    assert new_market("12345", 1).event_id == "12345"


def test_pit_context_token_containment_enforced_for_string_clobtokenids() -> None:
    """ADD02 / Reviewer A#3: when a Gamma market context's clobTokenIds is a JSON-array
    STRING (the real upstream form), the token-containment gate is still enforced -- a
    candidate asset absent from the list is rejected, and a present one resolves."""
    context_received = "2024-07-03T09:46:39.000000Z"
    gamma_body = json.dumps({
        "conditionId": CONDITION, "question": "Q", "outcomes": ["Yes", "No"],
        "events": [{"id": "55"}], "clobTokenIds": json.dumps(["7", "11"]),
        "active": True, "acceptingOrders": True,
    }).encode()
    gamma_raw = mt.make_raw_envelope("GAMMA", "polymarket:gamma:markets", "http:markets:offset:0:attempt:0", context_received, gamma_body, occurrence_sequence=0)
    context = mt.normalize_public_record(gamma_raw, endpoint="markets", record_index=0)

    def trade(asset: str, seq: int) -> tuple[mt.RawEnvelope, mt.NormalizedObservation]:
        body = json.dumps({
            "conditionId": CONDITION, "asset": asset, "price": "0.5", "size": "2",
            "side": "BUY", "transactionHash": "0x" + "c" * 64, "timestamp": 1720000000,
        }).encode()
        raw = mt.make_raw_envelope("DATA", "polymarket:data-api:trades", f"http:trades:offset:0:attempt:{seq}", RECEIVED, body, occurrence_sequence=seq)
        return raw, mt.normalize_public_record(raw, endpoint="trades", record_index=0)

    # Candidate asset "99" is NOT in the (string) token list -> containment rejects.
    raw99, obs99 = trade("99", 0)
    rejected = mt.build_point_in_time_observation(
        raw99, obs99, ingestion_batch_id="batch:wp169:1", snapshot_id="snap:wp169:1",
        market_context=context,
    )
    assert not rejected.is_valid and rejected.error_codes == ("PIT_PROMOTION_FORBIDDEN",)

    # Candidate asset "7" IS in the token list -> containment passes and it promotes.
    raw7, obs7 = trade("7", 1)
    accepted = mt.build_point_in_time_observation(
        raw7, obs7, ingestion_batch_id="batch:wp169:1", snapshot_id="snap:wp169:1",
        market_context=context,
    )
    assert accepted.is_valid and accepted.status == "ACCEPTED"


def test_existing_store_reopens_and_wrong_column_schema_fails_closed(tmp_path) -> None:
    """SEED17: a valid store reopens via the exact-DDL verification, but a file with a
    right-NAMED table and WRONG columns fails closed (a name-only check would pass it)."""
    import sqlite3

    p = _tmpdb(tmp_path, "seed17.sqlite3")
    with MarketTruthStore(p):
        pass  # create schema
    with MarketTruthStore(p) as reopened:
        assert reopened.receipt().raw_count == 0  # exact-DDL verification accepts a valid file

    wrong = _tmpdb(tmp_path, "seed17_wrong.sqlite3")
    conn = sqlite3.connect(str(wrong))
    conn.execute("PRAGMA application_id=1347242297")
    conn.execute("PRAGMA user_version=1")
    conn.execute("CREATE TABLE raw_occurrences (wrong INTEGER)")  # right name, wrong columns
    conn.commit()
    conn.close()
    store = MarketTruthStore(wrong)
    with pytest.raises(mt.MarketTruthError) as excinfo:
        store.initialize()
    assert excinfo.value.code == "STORE_CONFLICT"


def test_market_resolved_context_must_be_as_of_and_market_matching() -> None:
    """EV-F1: a market_resolved candidate rejects a context that post-dates it or belongs to
    a different market, and accepts an as-of context for the same market."""
    market_b = "0x" + "b" * 64
    resolved_body = json.dumps(
        {"event_type": "market_resolved", "condition_id": CONDITION, "timestamp": "1720000000000"}
    ).encode()
    resolved_raw = mt.make_raw_envelope(
        "WS", "polymarket:market-ws", "ws:00000000-0000-4000-8000-000000000000:frame:0", "2024-07-03T09:00:00.000000Z",
        resolved_body, occurrence_sequence=0,
    )
    resolved_obs = mt.normalize_websocket_message(resolved_raw, book_readiness={})[0]

    def context(condition: str, received: str, seq: int) -> mt.NormalizedObservation:
        body = json.dumps({
            "event_type": "new_market", "condition_id": condition, "question": "Q",
            "outcomes": ["Yes", "No"], "event_message": {"id": "555"}, "timestamp": "1720000000000",
        }).encode()
        raw = mt.make_raw_envelope("WS", "polymarket:market-ws", f"ws:00000000-0000-4000-8000-000000000000:frame:{seq}", received, body, occurrence_sequence=seq)
        return mt.normalize_websocket_message(raw, book_readiness={})[0]

    # Different market, received AFTER the candidate -> not-as-of AND market mismatch -> reject.
    later_other = context(market_b, "2024-07-03T12:00:00.000000Z", 1)
    rejected = mt.build_point_in_time_observation(
        resolved_raw, resolved_obs, ingestion_batch_id="batch:wp169:1",
        snapshot_id="snap:wp169:1", market_context=later_other,
    )
    assert not rejected.is_valid and rejected.error_codes == ("PIT_PROMOTION_FORBIDDEN",)

    # Same market, received BEFORE the candidate (as-of) -> accepted.
    asof_same = context(CONDITION, "2024-07-03T08:00:00.000000Z", 2)
    accepted = mt.build_point_in_time_observation(
        resolved_raw, resolved_obs, ingestion_batch_id="batch:wp169:1",
        snapshot_id="snap:wp169:1", market_context=asof_same,
    )
    assert accepted.is_valid and accepted.status == "ACCEPTED"


def test_raw_source_domain_forgery_fails_closed(tmp_path) -> None:
    """Item 5: a raw envelope with self-consistent hashes/ids but a forged source domain
    (wrong namespace, endpoint/method mismatch, non-UUID4 session, padded cursor int, wrong
    media type) fails closed with STORE_CONFLICT."""
    good_session = "00000000-0000-4000-8000-000000000000"
    forgeries = [
        ("WS", "polymarket:market-ws", "ws:notauuid:frame:0"),          # session not UUID4
        ("WS", "polymarket:evil", f"ws:{good_session}:frame:0"),        # unknown namespace
        ("WS", "polymarket:market-ws", f"ws:{good_session}:frame:00"),  # padded cursor int
        ("DATA", "polymarket:data-api:trades", "http:activity:offset:0:attempt:0"),  # endpoint mismatch
        ("DATA", "polymarket:data-api:bogus", "http:bogus:offset:0:attempt:0"),      # unknown endpoint
        ("POLYGON", "polygon:137:drpc:eth_getLogs", "rpc:eth_chainId:blocks:1-1:attempt:0"),  # method mismatch
    ]
    with MarketTruthStore(_tmpdb(tmp_path, "srcdom.sqlite3")) as store:
        for kind, source_id, cursor in forgeries:
            raw = mt.make_raw_envelope(kind, source_id, cursor, RECEIVED, b"{}", occurrence_sequence=0)
            receipt = store.append(raw)
            assert receipt.error_codes == ("STORE_CONFLICT",), (kind, source_id, cursor)


def test_raw_wrong_media_type_and_oversize_fail_closed(tmp_path) -> None:
    """Item 5: non-application/json media type and an over-bound byte length fail closed."""
    good = _book_raw()
    with MarketTruthStore(_tmpdb(tmp_path, "media.sqlite3")) as store:
        bad_media = dataclasses.replace(good, media_type="text/plain")
        assert store.append(bad_media).error_codes == ("STORE_CONFLICT",)
    # An envelope whose byte_length exceeds the store's response bound fails closed.
    small = mt.AcquisitionLimits(max_response_bytes=4)
    with MarketTruthStore(_tmpdb(tmp_path, "big.sqlite3"), small) as store:
        assert store.append(good).error_codes == ("STORE_CONFLICT",)


def test_child_trust_boundary_forgeries_fail_closed(tmp_path) -> None:
    """Item 6: forged children fail closed with STORE_CONFLICT while the raw evidence remains
    and no children commit."""
    raw = _book_raw()
    obs = mt.normalize_websocket_message(raw, book_readiness={})[0]
    forgeries = [
        dataclasses.replace(obs, source_kind="DATA"),                       # source-kind mismatch
        dataclasses.replace(obs, status="ACCEPTED", error_codes=("EVENT_INVALID",)),  # ACCEPTED + error
        dataclasses.replace(obs, book_ready=True, status="QUARANTINED"),    # book_ready without ACCEPTED
        dataclasses.replace(obs, provenance_json='{"normalizer_version":"x"}'),  # wrong provenance schema
        dataclasses.replace(obs, canonical_payload_json='{"z": 1}'),        # payload digest/canonical mismatch
    ]
    for index, forged in enumerate(forgeries):
        with MarketTruthStore(_tmpdb(tmp_path, f"child{index}.sqlite3")) as store:
            receipt = store.append(raw, (forged,))
            assert receipt.error_codes == ("STORE_CONFLICT",), index
            assert receipt.raw_count == 1 and receipt.normalized_count == 0  # raw remains, no children


def test_checkpoint_write_load_schema_trust_boundary(tmp_path) -> None:
    """Item 4: write_checkpoint validates the exact frozen value schema (INPUT_INVALID on an
    out-of-schema caller write); a valid checkpoint round-trips through load."""
    http_key = "http:trades:query:sha256:" + "a" * 64
    with MarketTruthStore(_tmpdb(tmp_path, "ckptschema.sqlite3")) as store:
        bad_writes = [
            ("chain:137:order-filled-v2", {"chain_id": 1, "last_verified_block": None, "last_verified_block_hash": None}),
            ("chain:137:order-filled-v2", {"chain_id": 137, "last_verified_block": 5, "last_verified_block_hash": None}),
            (http_key, {"endpoint": "trades", "next_offset": -1, "last_raw_id": None}),
            (http_key, {"endpoint": "bogus", "next_offset": 0, "last_raw_id": None}),
            (http_key, {"endpoint": "trades", "next_offset": 0}),  # missing key
        ]
        for key, value in bad_writes:
            with pytest.raises(mt.MarketTruthError) as excinfo:
                store.write_checkpoint(key, value, "ACTIVE")
            assert excinfo.value.code == "INPUT_INVALID", (key, value)
        # A valid chain checkpoint round-trips.
        written = store.write_checkpoint(
            "chain:137:order-filled-v2",
            {"chain_id": 137, "last_verified_block": 10, "last_verified_block_hash": "0x" + "a" * 64},
            "ACTIVE",
        )
        assert written.sequence == 1
        loaded = store.load_checkpoint("chain:137:order-filled-v2")
        assert json.loads(loaded.value_json)["last_verified_block"] == 10


def test_receipt_rejects_invalid_tokens(tmp_path) -> None:
    """Item 7: MarketTruthStore.receipt rejects status/stop_reason/error tokens outside the
    closed vocabularies."""
    with MarketTruthStore(_tmpdb(tmp_path, "receipttokens.sqlite3")) as store:
        for status, codes, stop in [
            ("BOGUS", (), "NONE"),
            ("OK", ("NOT_A_CODE",), "NONE"),
            ("OK", (), "BOGUS_STOP"),
        ]:
            with pytest.raises(mt.MarketTruthError) as excinfo:
                store.receipt(status, codes, stop)
            assert excinfo.value.code == "INPUT_INVALID", (status, codes, stop)
        assert store.receipt("STOPPED", (), "NETWORK_CALL_LIMIT").status == "STOPPED"


def test_store_limit_receipt_stop_reason_is_store_limit(tmp_path) -> None:
    """Reviewer round-2 #1: a store row/byte bound is FAILED/STORE_LIMIT_EXCEEDED with the
    frozen stop_reason STORE_LIMIT (not NONE), at the store boundary."""
    raw = _book_raw()
    obs = mt.normalize_websocket_message(raw, book_readiness={})
    with MarketTruthStore(_tmpdb(tmp_path, "storelimit.sqlite3"), mt.AcquisitionLimits(max_store_rows=1)) as store:
        receipt = store.append(raw, obs)
        assert receipt.status == "FAILED"
        assert receipt.error_codes == ("STORE_LIMIT_EXCEEDED",)
        assert receipt.stop_reason == "STORE_LIMIT", receipt
