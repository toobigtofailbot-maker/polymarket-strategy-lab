"""WP169 public Polygon read-only JSON-RPC OrderFilled V2 acquisition.

Only the enum provider ``drpc`` maps to the committed public no-query HTTPS URL,
and only the four read-only JSON-RPC methods eth_chainId, eth_blockNumber,
eth_getLogs, and eth_getBlockByNumber are used. Credential-like URLs, userinfo,
query strings, fragments, environment interpolation, and caller tokens are
structurally impossible. Malformed or unmatched logs remain raw evidence and are
quarantined; nothing is silently dropped.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping, Sequence

from .market_truth import (
    AcquisitionLimits,
    AcquisitionReceipt,
    MarketTruthError,
    NormalizedObservation,
    RawEnvelope,
    canonical_json_bytes,
    compute_observation_id,
    compute_source_log_id,
    epoch_seconds_to_rfc3339,
    make_raw_envelope,
    order_error_codes,
    sha256_hex,
)
from .market_truth_store import MarketTruthStore

POLYGON_CHAIN_ID = 137
POLYGON_CHAIN_ID_HEX = "0x89"
_RPC_PROVIDERS = {"drpc": "https://polygon.drpc.org"}
CTF_EXCHANGE_V2 = "0xe111180000d2663c0091e4f400237545b87b996b"
NEGRISK_CTF_EXCHANGE_V2 = "0xe2222d279d744050d28e00520010520000310f59"
_EXCHANGE_ADDRESSES = frozenset({CTF_EXCHANGE_V2, NEGRISK_CTF_EXCHANGE_V2})
ORDER_FILLED_V2_TOPIC = (
    "0xd543adfd945773f1a62f74f0ee55a5e3b9b1a28262980ba90b1a89f2ea84d8ee"
)
_ALLOWED_METHODS = frozenset(
    {"eth_chainId", "eth_blockNumber", "eth_getLogs", "eth_getBlockByNumber"}
)
_NORMALIZER = "wp169-normalizer/1.0.0"
# Default RPC response byte bound (the certified AcquisitionLimits default); callers thread
# their own limits.max_response_bytes through _rpc_call.
_LIMIT_DEFAULT_MAX_RESPONSE_BYTES = AcquisitionLimits().max_response_bytes


def validate_public_rpc_url(provider: str) -> str:
    """Map the enum provider to its committed public URL or fail closed."""
    if not isinstance(provider, str) or provider not in _RPC_PROVIDERS:
        raise MarketTruthError("RPC_PROVIDER_FORBIDDEN")
    return _RPC_PROVIDERS[provider]


import re as _re

_HEX_WORD_RE = _re.compile(r"^[0-9a-fA-F]{64}$")
_HEX_HASH_RE = _re.compile(r"^0x[0-9a-fA-F]{64}$")


def _hex_to_int(value: object) -> int | None:
    if not isinstance(value, str) or not value.startswith("0x"):
        return None
    try:
        return int(value, 16)
    except ValueError:
        return None


def _word_to_int(word: object) -> int | None:
    """Parse one 32-byte ABI word (exactly 64 hex chars) to int, else None.

    Right-length but non-hex words return None so a malformed log is quarantined rather
    than raising an uncaught ValueError.
    """
    if not isinstance(word, str) or _HEX_WORD_RE.fullmatch(word) is None:
        return None
    return int(word, 16)


def _is_hex_hash(value: object) -> bool:
    """True for a canonical 0x + 64 lowercase/uppercase hex hash string."""
    return isinstance(value, str) and _HEX_HASH_RE.fullmatch(value) is not None


def _address_from_word(word: str) -> str | None:
    if not isinstance(word, str) or _HEX_WORD_RE.fullmatch(word) is None:
        return None
    if word[:24] != "0" * 24:
        return None
    return "0x" + word[24:]


def _provenance_polygon(exchange_address: str, child_index: int) -> str:
    return canonical_json_bytes(
        {
            "normalizer_version": _NORMALIZER,
            "chain_id": POLYGON_CHAIN_ID,
            "exchange_address": exchange_address,
            "child_index": child_index,
        }
    ).decode("utf-8")


def _polygon_observation(
    raw: RawEnvelope,
    *,
    source_content_id: str,
    event_id: str | None,
    market_id: str | None,
    asset_id: str | None,
    event_time: str | None,
    payload: Mapping[str, object],
    status: str,
    error_codes: Sequence[str],
    child_index: int,
    exchange_address: str,
) -> NormalizedObservation:
    provenance_json = _provenance_polygon(exchange_address, child_index)
    canonical_payload_json = canonical_json_bytes(payload).decode("utf-8")
    canonical_payload_sha256 = sha256_hex(canonical_payload_json.encode("utf-8"))
    ordered = order_error_codes(error_codes)
    observation_id = compute_observation_id(
        source_content_id=source_content_id,
        source_kind="POLYGON",
        event_kind="order_filled",
        event_id=event_id,
        market_id=market_id,
        asset_id=asset_id,
        event_time=event_time,
        canonical_payload_sha256=canonical_payload_sha256,
        status=status,
        error_codes=ordered,
        book_ready=False,
        provenance_json=provenance_json,
    )
    return NormalizedObservation(
        observation_id=observation_id,
        occurrence_id=raw.occurrence_id,
        raw_id=raw.raw_id,
        source_kind="POLYGON",
        event_kind="order_filled",
        event_id=event_id,
        market_id=market_id,
        asset_id=asset_id,
        event_time=event_time,
        received_at=raw.received_at,
        canonical_payload_json=canonical_payload_json,
        canonical_payload_sha256=canonical_payload_sha256,
        status=status,
        error_codes=ordered,
        book_ready=False,
        provenance_json=provenance_json,
    )


def decode_order_filled_v2(
    raw: RawEnvelope,
    log: Mapping[str, object],
    *,
    latest_block: int,
    block_timestamp: int,
    confirmation_depth: int = 64,
) -> NormalizedObservation:
    """Decode one V2 OrderFilled log into a normalized acquisition observation.

    order_filled is acquisition evidence only in WP169: it carries no price,
    market, or event id and never promotes to a canonical PIT record.
    """
    child_index = 0
    address = log.get("address")
    address_lower = address.lower() if isinstance(address, str) else ""

    def quarantine(code: str, exchange: str) -> NormalizedObservation:
        # Distinguish DISTINCT malformed logs (even when they share an exchange address and
        # error code) by their outer on-chain identity, so two different events in one
        # eth_getLogs response never collapse into a single quarantine observation (which
        # would silently undercount evidence). source_content_id stays raw_id (the store's
        # quarantine identity rule); the per-log outer fields make the payload -- and thus
        # the observation_id -- distinct.
        raw_topics = log.get("topics")
        topic0 = (
            raw_topics[0]
            if isinstance(raw_topics, list) and raw_topics and isinstance(raw_topics[0], str)
            else None
        )

        def _str_or_none(value: object) -> str | None:
            return value if isinstance(value, str) else None

        payload = {
            "source_log_id": "markettruth:polygon-log:sha256:invalid",
            "error": code,
            "exchange_address": exchange or "0x",
            "block_number": _str_or_none(log.get("blockNumber")),
            "block_hash": _str_or_none(log.get("blockHash")),
            "transaction_hash": _str_or_none(log.get("transactionHash")),
            "log_index": _str_or_none(log.get("logIndex")),
            "event_topic": topic0,
        }
        return _polygon_observation(
            raw,
            source_content_id=raw.raw_id,
            event_id=None,
            market_id=None,
            asset_id=None,
            event_time=None,
            payload=payload,
            status="QUARANTINED",
            error_codes=(code,),
            child_index=child_index,
            exchange_address=exchange or "0x",
        )

    if address_lower not in _EXCHANGE_ADDRESSES:
        return quarantine("ADDRESS_FORBIDDEN", address_lower or "0x")
    topics = log.get("topics")
    if not isinstance(topics, list) or not topics or (
        not isinstance(topics[0], str) or topics[0].lower() != ORDER_FILLED_V2_TOPIC
    ):
        return quarantine("LOG_TOPIC_MISMATCH", address_lower)
    if len(topics) != 4:
        return quarantine("LOG_DATA_INVALID", address_lower)
    data = log.get("data")
    if not isinstance(data, str) or not data.startswith("0x"):
        return quarantine("LOG_DATA_INVALID", address_lower)
    body = data[2:]
    if len(body) != 7 * 64:
        return quarantine("LOG_DATA_INVALID", address_lower)
    words = [body[i * 64 : (i + 1) * 64] for i in range(7)]
    order_hash = topics[1]
    if not _is_hex_hash(order_hash):
        return quarantine("LOG_DATA_INVALID", address_lower)
    maker = _address_from_word(topics[2][2:] if isinstance(topics[2], str) and topics[2].startswith("0x") else "")
    taker = _address_from_word(topics[3][2:] if isinstance(topics[3], str) and topics[3].startswith("0x") else "")
    if maker is None or taker is None:
        return quarantine("LOG_DATA_INVALID", address_lower)
    # Every ABI word must be exactly 64 hex chars; a right-length non-hex word fails closed
    # rather than raising an uncaught ValueError.
    side_word = _word_to_int(words[0])
    if side_word is None or side_word not in (0, 1):
        return quarantine("LOG_DATA_INVALID", address_lower)
    side = "BUY" if side_word == 0 else "SELL"
    token_word = _word_to_int(words[1])
    maker_word = _word_to_int(words[2])
    taker_word = _word_to_int(words[3])
    fee_word = _word_to_int(words[4])
    builder = _address_from_word(words[5])
    if (
        token_word is None or maker_word is None or taker_word is None
        or fee_word is None or builder is None or _HEX_WORD_RE.fullmatch(words[6]) is None
    ):
        return quarantine("LOG_DATA_INVALID", address_lower)
    token_id = str(token_word)
    maker_amount = str(maker_word)
    taker_amount = str(taker_word)
    fee = str(fee_word)
    metadata = "0x" + words[6]
    block_number = _hex_to_int(log.get("blockNumber"))
    block_hash = log.get("blockHash")
    transaction_hash = log.get("transactionHash")
    log_index = _hex_to_int(log.get("logIndex"))
    if (
        block_number is None
        or not _is_hex_hash(block_hash)
        or not _is_hex_hash(transaction_hash)
        or log_index is None
        or log_index < 0
    ):
        return quarantine("LOG_DATA_INVALID", address_lower)
    if (
        not isinstance(latest_block, int) or isinstance(latest_block, bool)
        or block_number < 0 or block_number > latest_block
    ):
        # Impossible latest/log block relationship: never fabricate a non-positive
        # confirmation count -- fail the log closed as malformed.
        return quarantine("LOG_DATA_INVALID", address_lower)
    source_log_id = compute_source_log_id(
        chain_id=POLYGON_CHAIN_ID,
        exchange_address=address_lower,
        block_number=block_number,
        block_hash=block_hash,
        transaction_hash=transaction_hash,
        log_index=log_index,
        event_topic=ORDER_FILLED_V2_TOPIC,
    )
    confirmations = latest_block - block_number + 1
    finality_state = "CONFIRMED" if confirmations >= confirmation_depth else "PENDING"
    try:
        event_time = epoch_seconds_to_rfc3339(block_timestamp)
    except MarketTruthError:
        return quarantine("LOG_DATA_INVALID", address_lower)
    payload = {
        "source_log_id": source_log_id,
        "chain_id": POLYGON_CHAIN_ID,
        "exchange_address": address_lower,
        "order_hash": order_hash,
        "maker": maker,
        "taker": taker,
        "side": side,
        "token_id": token_id,
        "maker_amount_filled": maker_amount,
        "taker_amount_filled": taker_amount,
        "fee": fee,
        "builder": builder,
        "metadata": metadata,
        "block_number": block_number,
        "block_hash": block_hash,
        "block_timestamp": block_timestamp,
        "transaction_hash": transaction_hash,
        "log_index": log_index,
        "confirmation_count": confirmations,
        "finality_state": finality_state,
    }
    return _polygon_observation(
        raw,
        source_content_id=source_log_id,
        event_id=None,
        market_id=None,
        asset_id=token_id,
        event_time=event_time,
        payload=payload,
        status="ACCEPTED",
        error_codes=(),
        child_index=child_index,
        exchange_address=address_lower,
    )


CHAIN_CHECKPOINT_KEY = "chain:137:order-filled-v2"


def _rpc_call(
    transport: Callable[..., tuple[int, Mapping[str, str], bytes]],
    url: str,
    method: str,
    params: list[object],
    timeout: int,
    max_response_bytes: int = _LIMIT_DEFAULT_MAX_RESPONSE_BYTES,
) -> object:
    if method not in _ALLOWED_METHODS:
        raise MarketTruthError("RPC_PROVIDER_FORBIDDEN")
    body = json.dumps(
        {"jsonrpc": "2.0", "id": 1, "method": method, "params": params},
        separators=(",", ":"),
    ).encode("utf-8")
    status, _headers, response = transport(url, body, timeout)
    if status < 200 or status >= 300:
        raise MarketTruthError("RESPONSE_INVALID")
    # Byte-bound the response BEFORE decode/parse for EVERY allowed method (eth_chainId,
    # eth_blockNumber, eth_getLogs, eth_getBlockByNumber) -- not only the final logs call.
    if len(response) > max_response_bytes:
        raise MarketTruthError("RESPONSE_TOO_LARGE")
    try:
        document = json.loads(response.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        raise MarketTruthError("RESPONSE_INVALID")
    if not isinstance(document, Mapping) or "result" not in document:
        raise MarketTruthError("RESPONSE_INVALID")
    return document["result"], response


def _log_sort_key(entry: Mapping[str, object]) -> tuple[int, int, int, str]:
    return (
        _hex_to_int(entry.get("blockNumber")) or 0,
        _hex_to_int(entry.get("transactionIndex")) or 0,
        _hex_to_int(entry.get("logIndex")) or 0,
        str(entry.get("address", "")).lower(),
    )


def _collect_log_chunk(
    rpc, store, chunk_from, chunk_to, latest_block, active, received_at, seen_log_ids,
) -> AcquisitionReceipt | None:
    """Collect one inclusive [chunk_from, chunk_to] eth_getLogs partition (<= max_block_span
    blocks): archive the raw response, decode/dedupe accepted logs, append children, and
    record finality. Returns a terminal FAILED receipt on error, else None.

    S10-DEPLOY-EXEC-01R3: a multi-block range whose eth_getLogs response exceeds the frozen
    max_response_bytes is deterministically bisected into inclusive [from, mid] and
    [mid + 1, to] (mid = floor((from + to) / 2)), collected left-first through the same rate-
    limited rpc closure, received_at and seen_log_ids. A single-block oversize stays terminal
    RESPONSE_TOO_LARGE; every other error is terminal and never subdivided."""
    params = [{
        "fromBlock": hex(chunk_from), "toBlock": hex(chunk_to),
        "address": [CTF_EXCHANGE_V2, NEGRISK_CTF_EXCHANGE_V2],
        "topics": [ORDER_FILLED_V2_TOPIC],
    }]
    try:
        logs_result, response = rpc("eth_getLogs", params)
    except MarketTruthError as error:
        if error.error_codes == ("RESPONSE_TOO_LARGE",) and chunk_from < chunk_to:
            midpoint = (chunk_from + chunk_to) // 2
            left_error = _collect_log_chunk(
                rpc, store, chunk_from, midpoint, latest_block, active, received_at, seen_log_ids,
            )
            if left_error is not None:
                return left_error
            return _collect_log_chunk(
                rpc, store, midpoint + 1, chunk_to, latest_block, active, received_at, seen_log_ids,
            )
        return store.receipt("FAILED", error.error_codes, "NONE")
    if len(response) > active.max_response_bytes:
        return store.receipt("FAILED", ("RESPONSE_TOO_LARGE",), "NONE")
    if not isinstance(logs_result, list):
        return store.receipt("FAILED", ("RESPONSE_INVALID",), "NONE")
    cursor = f"rpc:eth_getLogs:blocks:{chunk_from}-{chunk_to}:attempt:0"
    raw = make_raw_envelope(
        "POLYGON", "polygon:137:drpc:eth_getLogs", cursor, received_at, response,
        occurrence_sequence=0, limits=active,
    )
    block_meta: dict[int, tuple[int, str]] = {}
    for log in logs_result:
        if not isinstance(log, Mapping):
            return store.receipt("FAILED", ("RESPONSE_INVALID",), "NONE")
        block_number = _hex_to_int(log.get("blockNumber"))
        if block_number is None:
            return store.receipt("FAILED", ("RESPONSE_INVALID",), "NONE")
        if block_number not in block_meta:
            try:
                meta = _get_block(rpc, block_number)
            except MarketTruthError as error:
                return store.receipt("FAILED", error.error_codes, "NONE")
            if meta is None:
                return store.receipt("FAILED", ("RESPONSE_INVALID",), "NONE")
            block_meta[block_number] = meta
    observations: list[NormalizedObservation] = []
    for log in sorted(logs_result, key=_log_sort_key):
        block_number = _hex_to_int(log.get("blockNumber"))
        block_hash = log.get("blockHash")
        meta = block_meta.get(block_number)
        if meta is None or meta[1] != block_hash:
            return store.receipt("FAILED", ("RESPONSE_INVALID",), "NONE")
        obs = decode_order_filled_v2(
            raw, log, latest_block=latest_block, block_timestamp=meta[0],
            confirmation_depth=active.confirmation_depth,
        )
        if obs.status == "ACCEPTED":
            log_id = json.loads(obs.canonical_payload_json)["source_log_id"]
            if log_id in seen_log_ids:
                continue
            seen_log_ids.add(log_id)
            if store._has_observation(obs.observation_id):
                continue
        observations.append(obs)
    append_receipt = store.append(raw, observations)
    if append_receipt.status != "OK":
        return append_receipt
    for obs in observations:
        if obs.status == "ACCEPTED":
            payload = json.loads(obs.canonical_payload_json)
            store._append_finality(
                payload["source_log_id"], payload["block_hash"],
                payload["finality_state"], received_at,
            )
    return None


def _get_block(rpc, block: int) -> tuple[int, str] | None:
    """Return (timestamp, hash) for a block, or None on invalid/missing data."""
    result, _r = rpc("eth_getBlockByNumber", [hex(block), False])
    if not isinstance(result, Mapping):
        return None
    ts = _hex_to_int(result.get("timestamp"))
    bhash = result.get("hash")
    if ts is None or not isinstance(bhash, str) or _hex_to_int(result.get("number")) != block:
        return None
    return ts, bhash


def collect_order_filled_logs(
    provider: str,
    store: MarketTruthStore,
    from_block: int,
    to_block: int,
    *,
    latest_block: int,
    limits: AcquisitionLimits | None = None,
    transport: Callable[..., tuple[int, Mapping[str, str], bytes]] | None = None,
) -> AcquisitionReceipt:
    """Collect OrderFilled V2 logs (exact frozen public signature).

    Delegates to the private implementation, which additionally carries the internal
    clock and shared-rate-limiter seams used by the runtime and by tests.
    """
    return _collect_order_filled_logs(
        provider, store, from_block, to_block,
        latest_block=latest_block, limits=limits, transport=transport,
    )


def _collect_order_filled_logs(
    provider: str,
    store: MarketTruthStore,
    from_block: int,
    to_block: int,
    *,
    latest_block: int,
    limits: AcquisitionLimits | None = None,
    transport: Callable[..., tuple[int, Mapping[str, str], bytes]] | None = None,
    clock: Callable[[], str] | None = None,
    rate_limiter: object | None = None,
) -> AcquisitionReceipt:
    """Collect OrderFilled V2 logs with checkpoint resume, hash revalidation, reorg
    handling, no-log verified progress, and PENDING->CONFIRMED versioning."""
    active = limits or AcquisitionLimits()
    url = validate_public_rpc_url(provider)
    if transport is None:
        transport = _default_rpc_transport
    now = clock or _default_clock
    timeout = active.request_timeout_seconds

    def _rpc(method: str, params: list[object]):
        if rate_limiter is not None:
            rate_limiter.acquire("POLYGON")
        return _rpc_call(transport, url, method, params, timeout, active.max_response_bytes)
    if not all(isinstance(v, int) and not isinstance(v, bool) for v in (from_block, to_block, latest_block)):
        return store.receipt("FAILED", ("INPUT_INVALID",), "NONE")
    if from_block < 0 or to_block < from_block or (to_block - from_block + 1) > active.max_block_span:
        return store.receipt("FAILED", ("INPUT_INVALID",), "NONE")

    try:
        chain_result, _resp = _rpc("eth_chainId", [])
    except MarketTruthError as error:
        return store.receipt("FAILED", error.error_codes, "NONE")
    if _hex_to_int(chain_result) != POLYGON_CHAIN_ID:
        return store.receipt("FAILED", ("CHAIN_ID_MISMATCH",), "NONE")

    # 1. Load prior chain checkpoint (verified block/hash) and retained pending logs.
    prior = store.load_checkpoint(CHAIN_CHECKPOINT_KEY)
    prior_block: int | None = None
    prior_hash: str | None = None
    if prior is not None:
        value = json.loads(prior.value_json)
        pb, ph = value.get("last_verified_block"), value.get("last_verified_block_hash")
        if isinstance(pb, int) and isinstance(ph, str):
            prior_block, prior_hash = pb, ph
    pending = list(store._latest_pending_order_filled())
    pending_hashes: dict[int, str] = {}
    for entry in pending:
        bn, bh = entry.get("block_number"), entry.get("block_hash")
        if isinstance(bn, int) and isinstance(bh, str):
            pending_hashes[bn] = bh

    # 2. Hash revalidation of the checkpoint block and every pending block.
    revalidate: dict[int, str] = dict(pending_hashes)
    if prior_block is not None and prior_hash is not None:
        revalidate[prior_block] = prior_hash
    reorg_block: int | None = None
    for block in sorted(revalidate):
        try:
            fetched = _get_block(_rpc, block)
        except MarketTruthError as error:
            return store.receipt("FAILED", error.error_codes, "NONE")
        if fetched is None:
            return store.receipt("FAILED", ("RESPONSE_INVALID",), "NONE")
        if fetched[1] != revalidate[block]:
            reorg_block = block if reorg_block is None else min(reorg_block, block)

    replacement_block: int | None = prior_block
    replacement_hash: str | None = prior_hash
    if reorg_block is not None:
        # 3. Reorg: append invalidation evidence, open a chain gap, and write a
        # REORG_INVALIDATED checkpoint to the greatest prior hash-verified confirmed
        # block below the reorg (or null); preserve all prior rows and recollect.
        received = now()
        store.mark_gap("chain:137", "OPEN", "REORG", received)
        for entry in store._latest_order_filled():
            if isinstance(entry.get("block_number"), int) and entry["block_number"] >= reorg_block:
                store._append_finality(
                    str(entry["source_log_id"]), str(entry["block_hash"]),
                    "REORG_INVALIDATED", received,
                )
        # Deep-reorg rollback: fall back to the greatest prior hash-verified confirmed block
        # strictly below the reorg, searched over the append-only checkpoint history (not just
        # the latest checkpoint); null only when no prior verified block still verifies.
        replacement_block, replacement_hash = None, None
        seen_candidates: set[tuple[int, str]] = set()
        for value in store._checkpoint_history_values(CHAIN_CHECKPOINT_KEY):
            cand_block = value.get("last_verified_block")
            cand_hash = value.get("last_verified_block_hash")
            if isinstance(cand_block, int) and isinstance(cand_hash, str) and cand_block < reorg_block:
                seen_candidates.add((cand_block, cand_hash))
        for cand_block, cand_hash in sorted(seen_candidates, reverse=True):
            try:
                fetched = _get_block(_rpc, cand_block)
            except MarketTruthError as error:
                return store.receipt("FAILED", error.error_codes, "NONE")
            if fetched is not None and fetched[1] == cand_hash:
                replacement_block, replacement_hash = cand_block, cand_hash
                break
        store.write_checkpoint(
            CHAIN_CHECKPOINT_KEY,
            {"chain_id": POLYGON_CHAIN_ID, "last_verified_block": replacement_block,
             "last_verified_block_hash": replacement_hash},
            "REORG_INVALIDATED",
        )
        collect_from = reorg_block
    else:
        # 4. Resume inclusively from min(last_verified_block+1, oldest_pending_block); the
        # caller from_block is used ONLY when no checkpoint AND no pending tail exists.
        # Including from_block once a checkpoint exists would recollect verified history.
        resume_candidates: list[int] = []
        if prior_block is not None:
            resume_candidates.append(prior_block + 1)
        if pending_hashes:
            resume_candidates.append(min(pending_hashes))
        collect_from = min(resume_candidates) if resume_candidates else from_block
    # Explicit from/to is an inclusive bound: never fabricate a block beyond the requested
    # to_block once the in-range tail is exhausted (item 12).
    collect_to = to_block
    if collect_from > collect_to:
        # The requested inclusive range is already fully verified/collected; issue no new
        # eth_getLogs outside the range. The existing checkpoint stands.
        return store.receipt("OK", (), "NONE")

    # Partition [collect_from, collect_to] into inclusive max_block_span-sized eth_getLogs
    # calls so the ENTIRE unconfirmed tail is revisited; no sub-range is ever skipped.
    received_at = now()
    seen_log_ids: set[str] = set()
    chunk_from = collect_from
    while chunk_from <= collect_to:
        chunk_to = min(chunk_from + active.max_block_span - 1, collect_to)
        error = _collect_log_chunk(
            _rpc, store, chunk_from, chunk_to, latest_block, active, received_at, seen_log_ids
        )
        if error is not None:
            return error
        chunk_from = chunk_to + 1

    # 5. last_verified_block = greatest block with depth >= confirmation_depth, even
    # when it holds no returned log; its hash is obtained explicitly.
    verified_ceiling = latest_block - active.confirmation_depth + 1
    last_verified_block: int | None = replacement_block
    last_hash: str | None = replacement_hash
    ceiling = min(collect_to, verified_ceiling)
    if ceiling >= collect_from and ceiling >= 0:
        try:
            fetched = _get_block(_rpc, ceiling)
        except MarketTruthError as error:
            return store.receipt("FAILED", error.error_codes, "NONE")
        if fetched is None:
            return store.receipt("FAILED", ("RESPONSE_INVALID",), "NONE")
        last_verified_block, last_hash = ceiling, fetched[1]

    store.write_checkpoint(
        CHAIN_CHECKPOINT_KEY,
        {"chain_id": POLYGON_CHAIN_ID, "last_verified_block": last_verified_block,
         "last_verified_block_hash": last_hash},
        "ACTIVE",
    )
    if reorg_block is not None:
        # The reorged range was recollected on the new canonical hash: heal the chain
        # gap with an append-only HEALED transition (OPEN evidence is preserved).
        store.mark_gap("chain:137", "HEALED", "REORG", received_at)
    return store.receipt("OK", (), "NONE")


def _default_clock() -> str:  # pragma: no cover - wall clock
    import datetime

    moment = datetime.datetime.now(datetime.timezone.utc)
    return f"{moment:%Y-%m-%dT%H:%M:%S}.{moment.microsecond:06d}Z"


def _default_rpc_transport(
    url: str, body: bytes, timeout_seconds: int
) -> tuple[int, Mapping[str, str], bytes]:
    # Fixed WP169 production headers only (no caller headers). An HTTP error response is
    # returned as (status, headers, body) so _rpc_call's non-2xx rule classifies it; only a
    # genuine transport failure (DNS/connect/TLS/socket timeout) is NETWORK_TIMEOUT.
    import urllib.error
    import urllib.request

    request = urllib.request.Request(
        url, data=body, method="POST",
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "wp169-public-market-truth/1.0",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            return int(response.status), dict(response.headers), response.read()
    except urllib.error.HTTPError as error:
        try:
            error_body = error.read() or b""
        except Exception:
            error_body = b""
        return int(error.code), dict(error.headers or {}), error_body
    except Exception:
        raise MarketTruthError("NETWORK_TIMEOUT")
