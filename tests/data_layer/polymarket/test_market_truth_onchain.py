"""WP169 focused tests: Polygon V2 OrderFilled decoding, confirmation, and reorg."""

from __future__ import annotations

import json

import pytest

from src.data_layer.polymarket import market_truth as mt
from src.data_layer.polymarket import market_truth_onchain as oc
from src.data_layer.polymarket.market_truth_store import MarketTruthStore

RECEIVED = "2024-07-03T10:00:00.000000Z"


def _word_int(value: int) -> str:
    return format(value, "064x")


def _word_addr(addr: str) -> str:
    return "0" * 24 + addr[2:]


def _log(address=oc.CTF_EXCHANGE_V2, topic=oc.ORDER_FILLED_V2_TOPIC, block="0x64", bhash="0x" + "a" * 64):
    maker = "0x" + "1" * 40
    taker = "0x" + "2" * 40
    builder = "0x" + "3" * 40
    data = "0x" + _word_int(0) + _word_int(999) + _word_int(100) + _word_int(50) + _word_int(1) + _word_addr(builder) + ("ab" * 32)
    return {
        "address": address,
        "topics": [topic, "0x" + "f" * 64, "0x" + _word_addr(maker), "0x" + _word_addr(taker)],
        "data": data,
        "blockNumber": block,
        "blockHash": bhash,
        "transactionHash": "0x" + "b" * 64,
        "logIndex": "0x1",
        "transactionIndex": "0x0",
    }


def _raw():
    return mt.make_raw_envelope(
        "POLYGON", "polygon:137:drpc:eth_getLogs",
        "rpc:eth_getLogs:blocks:100-100:attempt:0", RECEIVED,
        json.dumps([_log()]).encode(), occurrence_sequence=0,
    )


def test_order_filled_identity_confirmation_and_reorg_handling(tmp_path) -> None:
    # Secret-like / unknown RPC providers fail closed.
    with pytest.raises(mt.MarketTruthError) as excinfo:
        oc.validate_public_rpc_url("http://user:pass@evil/rpc?token=1")
    assert excinfo.value.code == "RPC_PROVIDER_FORBIDDEN"
    assert oc.validate_public_rpc_url("drpc") == "https://polygon.drpc.org"

    raw = _raw()
    # Confirmed when depth is sufficient; identity binds chain/address/block/tx/log.
    obs = oc.decode_order_filled_v2(raw, _log(), latest_block=200, block_timestamp=1720000000, confirmation_depth=64)
    assert obs.status == "ACCEPTED" and obs.event_kind == "order_filled"
    payload = json.loads(obs.canonical_payload_json)
    assert payload["chain_id"] == 137
    assert payload["exchange_address"] == oc.CTF_EXCHANGE_V2
    assert payload["finality_state"] == "CONFIRMED"
    assert payload["source_log_id"].startswith("markettruth:polygon-log:sha256:")
    assert obs.event_time == "2024-07-03T09:46:40.000000Z"

    # Insufficient confirmations -> PENDING (still acquisition evidence).
    pending = oc.decode_order_filled_v2(raw, _log(), latest_block=110, block_timestamp=1720000000)
    assert json.loads(pending.canonical_payload_json)["finality_state"] == "PENDING"

    # Wrong topic / address quarantine while raw remains archived.
    wrong_topic = oc.decode_order_filled_v2(raw, _log(topic="0x" + "0" * 64), latest_block=200, block_timestamp=1720000000)
    assert wrong_topic.status == "QUARANTINED" and wrong_topic.error_codes == ("LOG_TOPIC_MISMATCH",)
    wrong_addr = oc.decode_order_filled_v2(raw, _log(address="0x" + "9" * 40), latest_block=200, block_timestamp=1720000000)
    assert wrong_addr.error_codes == ("ADDRESS_FORBIDDEN",)

    # Malformed data length -> LOG_DATA_INVALID.
    bad = _log()
    bad["data"] = "0x1234"
    bad_obs = oc.decode_order_filled_v2(raw, bad, latest_block=200, block_timestamp=1720000000)
    assert bad_obs.error_codes == ("LOG_DATA_INVALID",)

    # Full collection with a fake JSON-RPC transport.
    class Rpc:
        def __call__(self, url, body, timeout):
            method = json.loads(body)["method"]
            if method == "eth_chainId":
                return (200, {}, json.dumps({"jsonrpc": "2.0", "id": 1, "result": "0x89"}).encode())
            if method == "eth_getLogs":
                return (200, {}, json.dumps({"jsonrpc": "2.0", "id": 1, "result": [_log()]}).encode())
            if method == "eth_getBlockByNumber":
                return (200, {}, json.dumps({"jsonrpc": "2.0", "id": 1, "result": {"number": "0x64", "hash": "0x" + "a" * 64, "timestamp": "0x" + format(1720000000, "x")}}).encode())
            raise AssertionError(method)

    counter = {"i": 0}

    def clock():
        counter["i"] += 1
        return f"2024-07-03T11:00:{counter['i'] % 60:02d}.000000Z"

    with MarketTruthStore(tmp_path / "wp169_oc.sqlite3") as store:
        receipt = oc._collect_order_filled_logs("drpc", store, 100, 100, latest_block=200, transport=Rpc(), clock=clock)
        assert receipt.status == "OK" and receipt.normalized_count == 1
        checkpoint = store.load_checkpoint(oc.CHAIN_CHECKPOINT_KEY)
        assert json.loads(checkpoint.value_json)["last_verified_block"] == 100

    # Chain-id mismatch fails closed.
    class WrongChain:
        def __call__(self, url, body, timeout):
            return (200, {}, json.dumps({"jsonrpc": "2.0", "id": 1, "result": "0x1"}).encode())

    with MarketTruthStore(tmp_path / "wp169_oc2.sqlite3") as store:
        receipt = oc._collect_order_filled_logs("drpc", store, 100, 100, latest_block=200, transport=WrongChain(), clock=clock)
        assert receipt.status == "FAILED" and receipt.error_codes == ("CHAIN_ID_MISMATCH",)

    # Block span bound is enforced.
    with MarketTruthStore(tmp_path / "wp169_oc3.sqlite3") as store:
        receipt = oc._collect_order_filled_logs("drpc", store, 0, 10_000, latest_block=10_000, transport=Rpc(), clock=clock)
        assert receipt.status == "FAILED" and receipt.error_codes == ("INPUT_INVALID",)


class _ControlledRpc:
    def __init__(self, block_hashes, logs, latest):
        self.block_hashes = block_hashes
        self.logs = logs
        self.latest = latest

    def __call__(self, url, body, timeout):
        method = json.loads(body)["method"]
        if method == "eth_chainId":
            return (200, {}, json.dumps({"result": "0x89"}).encode())
        if method == "eth_blockNumber":
            return (200, {}, json.dumps({"result": hex(self.latest)}).encode())
        if method == "eth_getLogs":
            return (200, {}, json.dumps({"result": self.logs}).encode())
        if method == "eth_getBlockByNumber":
            bn = int(json.loads(body)["params"][0], 16)
            h = self.block_hashes.get(bn, "0x" + "e" * 64)
            return (200, {}, json.dumps({"result": {"number": hex(bn), "hash": h, "timestamp": hex(1720000000)}}).encode())
        raise AssertionError(method)


def test_pending_to_confirmed_versioning_and_adversarial_reorg(tmp_path) -> None:
    """E: PENDING->CONFIRMED creates a new version for the same source_log_id, and a
    genuine block-hash reorg appends invalidation evidence, opens a chain gap, and
    writes a REORG_INVALIDATED checkpoint while preserving prior rows."""
    counter = {"i": 0}

    def clock():
        counter["i"] += 1
        return f"2024-07-03T12:00:{counter['i'] % 60:02d}.000000Z"

    h1 = "0x" + "a" * 64
    h2 = "0x" + "c" * 64
    with MarketTruthStore(tmp_path / "wp169_reorg.sqlite3") as store:
        # Collection 1: depth 21 < 64 -> PENDING.
        oc._collect_order_filled_logs(
            "drpc", store, 100, 100, latest_block=120,
            transport=_ControlledRpc({100: h1}, [_log(block="0x64", bhash=h1)], 120), clock=clock,
        )
        pending = store._latest_pending_order_filled()
        assert len(pending) == 1 and pending[0]["finality_state"] == "PENDING"

        # Collection 2: depth 101 >= 64 -> CONFIRMED new version (same source_log_id).
        oc._collect_order_filled_logs(
            "drpc", store, 100, 100, latest_block=200,
            transport=_ControlledRpc({100: h1}, [_log(block="0x64", bhash=h1)], 200), clock=clock,
        )
        states = {
            json.loads(o.canonical_payload_json)["finality_state"]
            for o in store.iter_normalized(limit=100) if o.event_kind == "order_filled"
        }
        assert states == {"PENDING", "CONFIRMED"}

        conn = store._require()
        before = conn.execute(
            "SELECT COUNT(*) FROM chain_finality_events WHERE finality_state='REORG_INVALIDATED'"
        ).fetchone()[0]

        # Collection 3: block 100 now has a DIFFERENT hash -> reorg.
        receipt = oc._collect_order_filled_logs(
            "drpc", store, 100, 100, latest_block=200,
            transport=_ControlledRpc({100: h2}, [_log(block="0x64", bhash=h2)], 200), clock=clock,
        )
        assert receipt.status == "OK"
        invalidated = conn.execute(
            "SELECT COUNT(*) FROM chain_finality_events WHERE finality_state='REORG_INVALIDATED'"
        ).fetchone()[0]
        chain_gap = conn.execute(
            "SELECT COUNT(*) FROM gap_events WHERE reason='REORG'"
        ).fetchone()[0]
        reorg_ckpt = conn.execute(
            "SELECT COUNT(*) FROM checkpoint_history WHERE state='REORG_INVALIDATED'"
        ).fetchone()[0]
        assert invalidated > before and chain_gap >= 1 and reorg_ckpt >= 1
        # Prior evidence is preserved (append-only): original PENDING+CONFIRMED rows remain.
        remaining = [
            o for o in store.iter_normalized(limit=100) if o.event_kind == "order_filled"
        ]
        assert len(remaining) >= 2


def test_reorg_does_not_repeat_from_stale_pending_state(tmp_path) -> None:
    """#4: a reorg-invalidated log is no longer active pending; a fourth normal cadence
    after the reorg does not re-trigger the same stale invalidation, and the chain gap
    is healed after successful replacement collection."""
    counter = {"i": 0}

    def clock():
        counter["i"] += 1
        return f"2024-07-03T13:00:{counter['i'] % 60:02d}.000000Z"

    h1 = "0x" + "a" * 64
    h2 = "0x" + "c" * 64
    with MarketTruthStore(tmp_path / "wp169_reorg4.sqlite3") as store:
        conn = store._require()
        # 1. PENDING old log on hash h1.
        oc._collect_order_filled_logs(
            "drpc", store, 100, 100, latest_block=120,
            transport=_ControlledRpc({100: h1}, [_log(block="0x64", bhash=h1)], 120), clock=clock,
        )
        # 2. Retain (still pending; latest advances slightly, still < depth).
        oc._collect_order_filled_logs(
            "drpc", store, 100, 100, latest_block=130,
            transport=_ControlledRpc({100: h1}, [_log(block="0x64", bhash=h1)], 130), clock=clock,
        )
        # 3. Reorg: block 100 now on hash h2 + replacement log.
        oc._collect_order_filled_logs(
            "drpc", store, 100, 100, latest_block=200,
            transport=_ControlledRpc({100: h2}, [_log(block="0x64", bhash=h2)], 200), clock=clock,
        )
        invalidated_after_reorg = conn.execute(
            "SELECT COUNT(*) FROM chain_finality_events WHERE finality_state='REORG_INVALIDATED'"
        ).fetchone()[0]
        healed = conn.execute(
            "SELECT COUNT(*) FROM gap_events WHERE reason='REORG' AND state='HEALED'"
        ).fetchone()[0]
        assert invalidated_after_reorg >= 1
        assert healed >= 1  # chain gap healed after successful replacement collection

        # 4. Another normal cadence on the now-canonical hash h2: no NEW invalidation.
        oc._collect_order_filled_logs(
            "drpc", store, 100, 100, latest_block=300,
            transport=_ControlledRpc({100: h2}, [_log(block="0x64", bhash=h2)], 300), clock=clock,
        )
        invalidated_after_normal = conn.execute(
            "SELECT COUNT(*) FROM chain_finality_events WHERE finality_state='REORG_INVALIDATED'"
        ).fetchone()[0]
        assert invalidated_after_normal == invalidated_after_reorg, "stale pending must not re-trigger reorg"


def test_malformed_but_right_length_abi_quarantines() -> None:
    """SEED16: a right-length but non-hex ABI word (or hash) must quarantine LOG_DATA_INVALID
    rather than raise an uncaught ValueError."""
    raw = _raw()
    valid = _word_int(0) + _word_int(999) + _word_int(100) + _word_int(50) + _word_int(1) + _word_addr("0x" + "3" * 40) + ("ab" * 32)
    # Non-hex first ABI word, still exactly 7*64 chars.
    bad_word = dict(_log())
    bad_word["data"] = "0x" + ("z" * 64) + valid[64:]
    obs = oc.decode_order_filled_v2(raw, bad_word, latest_block=200, block_timestamp=1720000000)
    assert obs.status == "QUARANTINED" and obs.error_codes == ("LOG_DATA_INVALID",)
    # Non-hex builder word.
    bad_builder = dict(_log())
    bad_builder["data"] = "0x" + valid[: 5 * 64] + ("g" * 64) + valid[6 * 64:]
    obs2 = oc.decode_order_filled_v2(raw, bad_builder, latest_block=200, block_timestamp=1720000000)
    assert obs2.status == "QUARANTINED" and obs2.error_codes == ("LOG_DATA_INVALID",)
    # Malformed (non-hex) block hash.
    bad_hash = dict(_log(bhash="0xnothex"))
    obs3 = oc.decode_order_filled_v2(raw, bad_hash, latest_block=200, block_timestamp=1720000000)
    assert obs3.status == "QUARANTINED" and obs3.error_codes == ("LOG_DATA_INVALID",)
    # Impossible block relationship: log block beyond the latest block.
    obs4 = oc.decode_order_filled_v2(raw, _log(block="0x1000"), latest_block=200, block_timestamp=1720000000)
    assert obs4.status == "QUARANTINED" and obs4.error_codes == ("LOG_DATA_INVALID",)


def test_rpc_response_byte_bound_applies_before_parse_all_methods(tmp_path) -> None:
    """SEED15: every RPC method's response is byte-bounded BEFORE parse, including the first
    eth_chainId call (previously unbounded)."""
    class HugeChain:
        def __call__(self, url, body, timeout):
            return (200, {}, b'{"result":"0x89","pad":"' + b"x" * 5000 + b'"}')

    counter = {"i": 0}

    def clock():
        counter["i"] += 1
        return f"2024-07-03T14:00:{counter['i'] % 60:02d}.000000Z"

    limits = mt.AcquisitionLimits(max_response_bytes=1000)
    with MarketTruthStore(tmp_path / "wp169_rpcbound.sqlite3") as store:
        receipt = oc._collect_order_filled_logs(
            "drpc", store, 100, 100, latest_block=200,
            transport=HugeChain(), clock=clock, limits=limits,
        )
    assert receipt.status == "FAILED" and receipt.error_codes == ("RESPONSE_TOO_LARGE",)


class _RecordingRpc:
    def __init__(self, block_hashes, logs, latest):
        self.block_hashes = block_hashes
        self.logs = logs
        self.latest = latest
        self.getlogs_from: list[int] = []

    def __call__(self, url, body, timeout):
        req = json.loads(body)
        method = req["method"]
        if method == "eth_chainId":
            return (200, {}, json.dumps({"result": "0x89"}).encode())
        if method == "eth_blockNumber":
            return (200, {}, json.dumps({"result": hex(self.latest)}).encode())
        if method == "eth_getLogs":
            self.getlogs_from.append(int(req["params"][0]["fromBlock"], 16))
            return (200, {}, json.dumps({"result": self.logs}).encode())
        if method == "eth_getBlockByNumber":
            bn = int(req["params"][0], 16)
            h = self.block_hashes.get(bn, "0x" + "e" * 64)
            return (200, {}, json.dumps({"result": {"number": hex(bn), "hash": h, "timestamp": hex(1720000000)}}).encode())
        raise AssertionError(method)


def test_resume_does_not_recollect_verified_or_exceed_explicit_to_block(tmp_path) -> None:
    """SEED03 + item 12: once a checkpoint exists, resume starts at last_verified_block+1 and
    never recollects verified history NOR queries beyond the explicit inclusive to_block. Only
    when a later expanded range is requested does it collect the new tail."""
    counter = {"i": 0}

    def clock():
        counter["i"] += 1
        return f"2024-07-03T15:00:{counter['i'] % 60:02d}.000000Z"

    h1 = "0x" + "a" * 64
    rpc = _RecordingRpc({100: h1}, [_log(block="0x64", bhash=h1)], 200)
    with MarketTruthStore(tmp_path / "wp169_resume.sqlite3") as store:
        # Collection 1: explicit [100,100], latest 200 -> confirms block 100, verified=100.
        oc._collect_order_filled_logs("drpc", store, 100, 100, latest_block=200, transport=rpc, clock=clock)
        # Collection 2: same explicit to_block=100; resume point 101 > to_block -> NO new
        # eth_getLogs beyond the range (does not recollect verified history nor fabricate 101).
        oc._collect_order_filled_logs("drpc", store, 50, 100, latest_block=200, transport=rpc, clock=clock)
        assert rpc.getlogs_from == [100], rpc.getlogs_from
        # Collection 3: expanded explicit range to_block=110 -> collect exactly 101..110.
        rpc.logs = []
        oc._collect_order_filled_logs("drpc", store, 50, 110, latest_block=200, transport=rpc, clock=clock)
    assert rpc.getlogs_from == [100, 101], rpc.getlogs_from


def test_quarantined_order_filled_log_is_storable(tmp_path) -> None:
    """EV-F2: a QUARANTINED (malformed) OrderFilled log is a valid child that persists as
    raw+quarantined evidence; a malformed log in a getLogs response does not escalate the
    whole range to STORE_CONFLICT."""
    raw = _raw()
    malformed = dict(_log())
    malformed["data"] = "0x1234"  # wrong length -> QUARANTINED LOG_DATA_INVALID
    obs = oc.decode_order_filled_v2(raw, malformed, latest_block=200, block_timestamp=1720000000)
    assert obs.status == "QUARANTINED"
    with MarketTruthStore(tmp_path / "wp169_qpoly.sqlite3") as store:
        receipt = store.append(raw, (obs,))
        assert receipt.status == "OK", receipt
        assert receipt.quarantined_count == 1

    class Rpc:
        def __call__(self, url, body, timeout):
            method = json.loads(body)["method"]
            if method == "eth_chainId":
                return (200, {}, json.dumps({"result": "0x89"}).encode())
            if method == "eth_getLogs":
                return (200, {}, json.dumps({"result": [malformed]}).encode())
            if method == "eth_getBlockByNumber":
                bn = int(json.loads(body)["params"][0], 16)
                return (200, {}, json.dumps({"result": {"number": hex(bn), "hash": "0x" + "a" * 64, "timestamp": hex(1720000000)}}).encode())
            raise AssertionError(method)

    with MarketTruthStore(tmp_path / "wp169_malcol.sqlite3") as store:
        receipt = oc._collect_order_filled_logs(
            "drpc", store, 100, 100, latest_block=200,
            transport=Rpc(), clock=lambda: "2024-07-03T10:00:00.000000Z",
        )
        assert receipt.status == "OK", receipt  # malformed log quarantined, not STORE_CONFLICT
        assert receipt.quarantined_count >= 1


def test_deep_reorg_falls_back_to_prior_verified_checkpoint(tmp_path) -> None:
    """Item 13: when the latest verified checkpoint block is itself reorged, the replacement
    checkpoint falls back to the GREATEST prior hash-verified confirmed block from the
    append-only history (not straight to null)."""
    counter = {"i": 0}

    def clock():
        counter["i"] += 1
        return f"2024-07-03T16:00:{counter['i'] % 60:02d}.000000Z"

    hA = "0x" + "a" * 64
    hB = "0x" + "b" * 64
    hB2 = "0x" + "c" * 64
    with MarketTruthStore(tmp_path / "wp169_deepreorg.sqlite3") as store:
        # Collection 1: verify block 100 (hash hA).
        oc._collect_order_filled_logs(
            "drpc", store, 100, 100, latest_block=200,
            transport=_ControlledRpc({100: hA}, [_log(block="0x64", bhash=hA)], 200), clock=clock,
        )
        assert json.loads(store.load_checkpoint(oc.CHAIN_CHECKPOINT_KEY).value_json)["last_verified_block"] == 100
        # Collection 2: verify block 200 (hash hB); resume from 101.
        oc._collect_order_filled_logs(
            "drpc", store, 101, 200, latest_block=300,
            transport=_ControlledRpc({100: hA, 200: hB}, [_log(block="0xc8", bhash=hB)], 300), clock=clock,
        )
        assert json.loads(store.load_checkpoint(oc.CHAIN_CHECKPOINT_KEY).value_json)["last_verified_block"] == 200
        # Collection 3: block 200 reorged (hB -> hB2). Deep fallback must choose block 100
        # (still hash-verified), never null.
        oc._collect_order_filled_logs(
            "drpc", store, 101, 300, latest_block=300,
            transport=_ControlledRpc({100: hA, 200: hB2}, [_log(block="0xc8", bhash=hB2)], 300), clock=clock,
        )
        conn = store._require()
        rows = conn.execute(
            "SELECT value_json FROM checkpoint_history WHERE state='REORG_INVALIDATED'"
            " ORDER BY history_sequence ASC"
        ).fetchall()
        assert rows, "a REORG_INVALIDATED checkpoint must be written"
        reorg_value = json.loads(rows[-1][0])
        assert reorg_value["last_verified_block"] == 100
        assert reorg_value["last_verified_block_hash"] == hA


class _RangeRecordingRpc:
    def __init__(self, latest):
        self.latest = latest
        self.ranges: list[tuple[int, int]] = []

    def __call__(self, url, body, timeout):
        req = json.loads(body)
        method = req["method"]
        if method == "eth_chainId":
            return (200, {}, json.dumps({"result": "0x89"}).encode())
        if method == "eth_blockNumber":
            return (200, {}, json.dumps({"result": hex(self.latest)}).encode())
        if method == "eth_getLogs":
            params = req["params"][0]
            self.ranges.append((int(params["fromBlock"], 16), int(params["toBlock"], 16)))
            return (200, {}, json.dumps({"result": []}).encode())
        if method == "eth_getBlockByNumber":
            bn = int(req["params"][0], 16)
            return (200, {}, json.dumps({"result": {"number": hex(bn), "hash": "0x" + "a" * 64, "timestamp": hex(1720000000)}}).encode())
        raise AssertionError(method)


def test_resume_range_is_partitioned_into_max_block_span_calls(tmp_path) -> None:
    """Reviewer A #1: a resume range wider than max_block_span is PARTITIONED into
    max_block_span-sized eth_getLogs calls that tile the whole range -- no sub-range is
    silently skipped (the old code truncated from the left)."""
    limits = mt.AcquisitionLimits(max_block_span=100)
    rpc = _RangeRecordingRpc(latest=6000)
    with MarketTruthStore(tmp_path / "wp169_partition.sqlite3") as store:
        # Collection 1: verify block 99 (range [0,99]).
        oc._collect_order_filled_logs("drpc", store, 0, 99, latest_block=6000, transport=rpc, clock=lambda: RECEIVED, limits=limits)
        assert rpc.ranges == [(0, 99)]
        # Collection 2: caller window [200,299]; resume from verified+1=100 through to_block=299
        # must be partitioned into [100,199] and [200,299] -- covering the whole tail.
        rpc.ranges.clear()
        oc._collect_order_filled_logs("drpc", store, 200, 299, latest_block=6000, transport=rpc, clock=lambda: RECEIVED, limits=limits)
    assert rpc.ranges == [(100, 199), (200, 299)], rpc.ranges
    # The partitions tile [100, 299] with no gap and none exceeds max_block_span.
    covered = []
    for lo, hi in rpc.ranges:
        assert hi - lo + 1 <= 100
        covered.extend(range(lo, hi + 1))
    assert covered == list(range(100, 300))


def test_collect_order_filled_store_limit_stop_reason(tmp_path) -> None:
    """Reviewer round-2 #1: collect_order_filled_logs propagates STORE_LIMIT_EXCEEDED with the
    frozen stop_reason STORE_LIMIT."""
    class Rpc:
        def __call__(self, url, body, timeout):
            method = json.loads(body)["method"]
            if method == "eth_chainId":
                return (200, {}, json.dumps({"result": "0x89"}).encode())
            if method == "eth_getLogs":
                return (200, {}, json.dumps({"result": [_log()]}).encode())
            if method == "eth_getBlockByNumber":
                bn = int(json.loads(body)["params"][0], 16)
                return (200, {}, json.dumps({"result": {"number": hex(bn), "hash": "0x" + "a" * 64, "timestamp": hex(1720000000)}}).encode())
            raise AssertionError(method)

    limits = mt.AcquisitionLimits(max_store_rows=1)
    with MarketTruthStore(tmp_path / "wp169_ocstore.sqlite3", limits) as store:
        receipt = oc._collect_order_filled_logs(
            "drpc", store, 100, 100, latest_block=200,
            transport=Rpc(), clock=lambda: RECEIVED, limits=limits,
        )
    assert receipt.status == "FAILED" and receipt.error_codes == ("STORE_LIMIT_EXCEEDED",)
    assert receipt.stop_reason == "STORE_LIMIT", receipt


def test_distinct_malformed_logs_do_not_collapse(tmp_path) -> None:
    """Reviewer round-3 F1: two DISTINCT malformed logs sharing address+error (different tx
    hash / log index) produce two distinct quarantine observations, not one collapsed row."""
    raw = _raw()

    def bad_log(tx: str, li: str) -> dict:
        return {
            "address": "0x" + "9" * 40,  # ADDRESS_FORBIDDEN for both
            "topics": [oc.ORDER_FILLED_V2_TOPIC, "0x" + "f" * 64,
                       "0x" + _word_addr("0x" + "1" * 40), "0x" + _word_addr("0x" + "2" * 40)],
            "data": "0x1234",
            "blockNumber": "0x64", "blockHash": "0x" + "a" * 64,
            "transactionHash": tx, "logIndex": li, "transactionIndex": "0x0",
        }

    obs1 = oc.decode_order_filled_v2(raw, bad_log("0x" + "b" * 64, "0x1"), latest_block=200, block_timestamp=1720000000)
    obs2 = oc.decode_order_filled_v2(raw, bad_log("0x" + "c" * 64, "0x2"), latest_block=200, block_timestamp=1720000000)
    assert obs1.status == obs2.status == "QUARANTINED"
    assert obs1.error_codes == obs2.error_codes == ("ADDRESS_FORBIDDEN",)
    assert obs1.observation_id != obs2.observation_id  # distinct evidence -> distinct identity
    with MarketTruthStore(tmp_path / "wp169_distinct_q.sqlite3") as store:
        receipt = store.append(raw, (obs1, obs2))
        assert receipt.status == "OK"
        assert receipt.quarantined_count == 2


def test_accepted_order_filled_identity_is_stable_across_batching(tmp_path) -> None:
    """wp_prompt.txt 337-340 / 733-735: source_content_id for an ACCEPTED POLYGON order_filled
    is the stable source_log_id, 'so response batching and overlap do not alter event identity'.
    The SAME log decoded from two DIFFERENTLY BATCHED responses (distinct raw bytes -> distinct
    raw_id and occurrence_id) yields the SAME observation_id and is not re-promoted as a new
    normalized identity, while both raw occurrences are archived (multiplicity). Red-sensitive:
    would fail if ACCEPTED used source_content_id=raw_id (like WS/quarantine)."""
    log = _log()
    other = _log()
    other["transactionHash"] = "0x" + "e" * 64
    other["logIndex"] = "0x7"

    # Two overlapping, differently batched eth_getLogs responses containing the same log.
    raw1 = mt.make_raw_envelope(
        "POLYGON", "polygon:137:drpc:eth_getLogs",
        "rpc:eth_getLogs:blocks:100-100:attempt:0", RECEIVED,
        json.dumps([log]).encode(), occurrence_sequence=0,
    )
    raw2 = mt.make_raw_envelope(
        "POLYGON", "polygon:137:drpc:eth_getLogs",
        "rpc:eth_getLogs:blocks:99-101:attempt:0", RECEIVED,
        json.dumps([other, log]).encode(), occurrence_sequence=0,
    )
    assert raw1.raw_id != raw2.raw_id  # genuinely different batches

    obs1 = oc.decode_order_filled_v2(raw1, log, latest_block=200, block_timestamp=1720000000, confirmation_depth=64)
    obs2 = oc.decode_order_filled_v2(raw2, log, latest_block=200, block_timestamp=1720000000, confirmation_depth=64)
    assert obs1.status == obs2.status == "ACCEPTED"
    # Identity is stable across batching/overlap: same source_log_id -> same observation_id.
    assert obs1.observation_id == obs2.observation_id
    # ...but the two arrivals are distinct occurrences (multiplicity), keyed to their raws.
    assert obs1.occurrence_id != obs2.occurrence_id
    assert obs1.occurrence_id == raw1.occurrence_id and obs2.occurrence_id == raw2.occurrence_id

    with MarketTruthStore(tmp_path / "wp169_batch_identity.sqlite3") as store:
        assert store.append(raw1, (obs1,)).status == "OK"
        assert store.append(raw2, (obs2,)).status == "OK"
        conn = store._require()
        distinct_ids = conn.execute(
            "SELECT COUNT(DISTINCT observation_id) FROM normalized_occurrences"
        ).fetchone()[0]
        occurrences = conn.execute("SELECT COUNT(*) FROM normalized_occurrences").fetchone()[0]
        raw_rows = conn.execute("SELECT COUNT(*) FROM raw_occurrences").fetchone()[0]
    assert distinct_ids == 1  # a single normalized identity (not re-promoted)
    assert occurrences == 2   # both occurrences archived (multiplicity)
    assert raw_rows == 2      # both raw batches archived as evidence


# ---------------------------------------------------------------------------
# S10-DEPLOY-EXEC-01R2: the real default Polygon RPC transport (urlopen intercepted;
# a socket guard proves no test reaches the network).
# ---------------------------------------------------------------------------

import inspect
import io
import socket
import ssl
import urllib.error
import urllib.request

_DRPC_URL = "https://polygon.drpc.org"
_CHAIN_OK = json.dumps({"jsonrpc": "2.0", "id": 1, "result": "0x89"}).encode()


class _FakeResponse:
    def __init__(self, status: int, body: bytes, read_error: BaseException | None = None):
        self.status = status
        self.headers = {"Content-Type": "application/json"}
        self._body = body
        self._read_error = read_error

    def read(self) -> bytes:
        if self._read_error is not None:
            raise self._read_error
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


@pytest.fixture
def no_network(monkeypatch):
    def refuse(*args, **kwargs):
        raise AssertionError("real network attempted")

    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)
    monkeypatch.setattr(socket, "getaddrinfo", refuse)


def _install_urlopen(monkeypatch, outcome):
    calls: list[tuple[urllib.request.Request, object]] = []

    def fake_urlopen(request, timeout=None):
        calls.append((request, timeout))
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    return calls


def _http_error(code: int, body: bytes = b'{"error":"denied"}') -> urllib.error.HTTPError:
    return urllib.error.HTTPError(
        _DRPC_URL, code, "error", {"Content-Type": "application/json"}, io.BytesIO(body)
    )


def test_default_rpc_transport_sends_only_fixed_wp169_headers(monkeypatch, no_network) -> None:
    calls = _install_urlopen(monkeypatch, _FakeResponse(200, _CHAIN_OK))
    body = b'{"jsonrpc":"2.0","id":1,"method":"eth_chainId","params":[]}'
    status, _headers, response = oc._default_rpc_transport(_DRPC_URL, body, 7)
    assert (status, response) == (200, _CHAIN_OK)
    assert len(calls) == 1
    request, timeout = calls[0]
    assert timeout == 7
    assert request.get_method() == "POST"
    assert request.full_url == _DRPC_URL and request.data == body
    headers = {name.lower(): value for name, value in request.header_items()}
    assert headers == {
        "content-type": "application/json",
        "accept": "application/json",
        "user-agent": "wp169-public-market-truth/1.0",
    }
    assert "authorization" not in headers and "cookie" not in headers
    # No caller header/credential input surface exists on the transport.
    assert list(inspect.signature(oc._default_rpc_transport).parameters) == [
        "url", "body", "timeout_seconds",
    ]


@pytest.mark.parametrize("code", [403, 429, 500, 503])
def test_default_rpc_transport_preserves_http_error_status(monkeypatch, no_network, code) -> None:
    _install_urlopen(monkeypatch, _http_error(code))
    status, headers, response = oc._default_rpc_transport(_DRPC_URL, b"{}", 5)
    assert status == code
    assert response == b'{"error":"denied"}'
    assert headers.get("Content-Type") == "application/json"
    # The existing _rpc_call non-2xx rule classifies it: RESPONSE_INVALID, never NETWORK_TIMEOUT.
    _install_urlopen(monkeypatch, _http_error(code))
    with pytest.raises(mt.MarketTruthError) as excinfo:
        oc._rpc_call(oc._default_rpc_transport, _DRPC_URL, "eth_chainId", [], 5)
    assert excinfo.value.code == "RESPONSE_INVALID"


def test_http_error_with_unreadable_body_keeps_status(monkeypatch, no_network) -> None:
    error = _http_error(403)

    def broken_read(*args):
        raise ConnectionResetError()

    monkeypatch.setattr(error, "read", broken_read)
    _install_urlopen(monkeypatch, error)
    status, _headers, response = oc._default_rpc_transport(_DRPC_URL, b"{}", 5)
    assert (status, response) == (403, b"")


def test_non_2xx_body_is_never_accepted_as_jsonrpc_success(monkeypatch, no_network) -> None:
    # Even a well-formed 0x89 result body is rejected when the HTTP status is non-2xx.
    _install_urlopen(monkeypatch, _http_error(403, _CHAIN_OK))
    with pytest.raises(mt.MarketTruthError) as excinfo:
        oc._rpc_call(oc._default_rpc_transport, _DRPC_URL, "eth_chainId", [], 5)
    assert excinfo.value.code == "RESPONSE_INVALID"


@pytest.mark.parametrize(
    "failure",
    [
        urllib.error.URLError("name resolution failed"),
        urllib.error.URLError(ConnectionRefusedError()),
        TimeoutError("timed out"),
        socket.timeout("timed out"),
        ssl.SSLError("handshake failure"),
        OSError("network unreachable"),
    ],
)
def test_genuine_transport_failure_remains_network_timeout(monkeypatch, no_network, failure) -> None:
    _install_urlopen(monkeypatch, failure)
    with pytest.raises(mt.MarketTruthError) as excinfo:
        oc._default_rpc_transport(_DRPC_URL, b"{}", 5)
    assert excinfo.value.code == "NETWORK_TIMEOUT"


def test_timeout_while_reading_2xx_body_remains_network_timeout(monkeypatch, no_network) -> None:
    _install_urlopen(monkeypatch, _FakeResponse(200, b"", read_error=TimeoutError()))
    with pytest.raises(mt.MarketTruthError) as excinfo:
        oc._default_rpc_transport(_DRPC_URL, b"{}", 5)
    assert excinfo.value.code == "NETWORK_TIMEOUT"


def test_default_transport_success_and_invalid_json_paths_unchanged(monkeypatch, no_network) -> None:
    _install_urlopen(monkeypatch, _FakeResponse(200, _CHAIN_OK))
    result, raw = oc._rpc_call(oc._default_rpc_transport, _DRPC_URL, "eth_chainId", [], 5)
    assert result == "0x89" and raw == _CHAIN_OK
    _install_urlopen(monkeypatch, _FakeResponse(200, b"not-json"))
    with pytest.raises(mt.MarketTruthError) as excinfo:
        oc._rpc_call(oc._default_rpc_transport, _DRPC_URL, "eth_chainId", [], 5)
    assert excinfo.value.code == "RESPONSE_INVALID"


def test_collect_with_default_transport_classifies_outcomes(monkeypatch, no_network, tmp_path) -> None:
    # transport=None selects the real default transport inside the collection path.
    wrong_chain = json.dumps({"jsonrpc": "2.0", "id": 1, "result": "0x1"}).encode()
    cases = [
        (_http_error(403), ("RESPONSE_INVALID",)),
        (_http_error(429), ("RESPONSE_INVALID",)),
        (urllib.error.URLError("connect failed"), ("NETWORK_TIMEOUT",)),
        (_FakeResponse(200, wrong_chain), ("CHAIN_ID_MISMATCH",)),
    ]
    for index, (outcome, expected) in enumerate(cases):
        _install_urlopen(monkeypatch, outcome)
        with MarketTruthStore(tmp_path / f"r2_{index}.sqlite3") as store:
            receipt = oc._collect_order_filled_logs("drpc", store, 100, 100, latest_block=200)
        assert receipt.status == "FAILED" and receipt.error_codes == expected, (index, receipt)


def test_provider_and_method_allowlists_unchanged(monkeypatch, no_network) -> None:
    calls = _install_urlopen(monkeypatch, _FakeResponse(200, _CHAIN_OK))
    assert oc._RPC_PROVIDERS == {"drpc": _DRPC_URL}
    assert oc._ALLOWED_METHODS == frozenset(
        {"eth_chainId", "eth_blockNumber", "eth_getLogs", "eth_getBlockByNumber"}
    )
    for provider in ("alchemy", "infura", "https://polygon-rpc.com", "", None):
        with pytest.raises(mt.MarketTruthError) as excinfo:
            oc.validate_public_rpc_url(provider)
        assert excinfo.value.code == "RPC_PROVIDER_FORBIDDEN"
    for method in ("eth_sendRawTransaction", "eth_sendTransaction", "eth_sign", "personal_sign"):
        with pytest.raises(mt.MarketTruthError) as excinfo:
            oc._rpc_call(oc._default_rpc_transport, _DRPC_URL, method, [], 5)
        assert excinfo.value.code == "RPC_PROVIDER_FORBIDDEN"
    assert calls == []  # forbidden methods never reach the transport
