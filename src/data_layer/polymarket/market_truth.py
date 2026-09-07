"""WP169 public market-truth foundation.

Import-safe, standard-library-only, offline, no import-time network / thread /
process / scheduler / file side effect. This module holds the canonical-JSON
serializer, closed error precedence, content/occurrence identities, the frozen
public records, the WebSocket and public-record normalizers, the recursive
no-echo sanitization boundary, and the point-in-time promotion adapter that
hands accepted observations to the existing unchanged PIT builder.

PROHIBITED here and in every sibling market_truth_* module: credentials, API
keys, wallet/private keys, authenticated headers, POST/PUT/PATCH/DELETE product
calls, order create/cancel, signing, OMS, strategy, paper/live trading, Hermes
runtime, dashboard, generic scheduler, installed service, or background loop.
"""

from __future__ import annotations

import dataclasses
import datetime
import hashlib
import json
import pathlib
import re
from collections.abc import Mapping, Sequence
from typing import Any, Callable

from ..point_in_time_market_research.records import (
    PointInTimeBuildResult,
    build_market_observation,
    build_source_snapshot,
)

# ---------------------------------------------------------------------------
# Closed error precedence (exact order from the frozen contract).
# ---------------------------------------------------------------------------

ERROR_PRECEDENCE: tuple[str, ...] = (
    "INPUT_INVALID",
    "LIMIT_INVALID",
    "RAW_TOO_LARGE",
    "SERIALIZATION_INVALID",
    "STORE_NOT_INITIALIZED",
    "STORE_LIMIT_EXCEEDED",
    "QUEUE_LIMIT_EXCEEDED",
    "STORE_CONFLICT",
    "ENDPOINT_FORBIDDEN",
    "RPC_PROVIDER_FORBIDDEN",
    "NETWORK_TIMEOUT",
    "HTTP_STATUS_RETRYABLE",
    "RETRY_AFTER_INVALID",
    "RETRY_EXHAUSTED",
    "RESPONSE_TOO_LARGE",
    "RESPONSE_INVALID",
    "EVENT_UNSUPPORTED",
    "EVENT_INVALID",
    "BOOK_GAP_ACTIVE",
    "CONTINUITY_GAP",
    "CHAIN_ID_MISMATCH",
    "ADDRESS_FORBIDDEN",
    "LOG_TOPIC_MISMATCH",
    "LOG_DATA_INVALID",
    "CONFIRMATIONS_INSUFFICIENT",
    "REORG_DETECTED",
    "PIT_PROMOTION_FORBIDDEN",
    "PIT_BUILD_INVALID",
    "STOP_REQUESTED",
    "INTERNAL_CLOSED_FAILURE",
)
_ERROR_RANK = {code: index for index, code in enumerate(ERROR_PRECEDENCE)}


def order_error_codes(codes: Sequence[str]) -> tuple[str, ...]:
    """Deduplicate and order closed error codes by the frozen precedence."""
    seen: dict[str, int] = {}
    for occurrence, code in enumerate(codes):
        if code in _ERROR_RANK:
            seen.setdefault(code, occurrence)
    return tuple(
        sorted(seen, key=lambda code: (_ERROR_RANK[code], seen[code]))
    )


class MarketTruthError(Exception):
    """Closed error carrying only ordered closed codes -- never raw values."""

    def __init__(self, *codes: str) -> None:
        ordered = order_error_codes(codes)
        if not ordered:
            ordered = ("INTERNAL_CLOSED_FAILURE",)
        self.error_codes: tuple[str, ...] = ordered
        self.code: str = ordered[0]
        super().__init__(self.code)


# ---------------------------------------------------------------------------
# Canonical JSON serialization (deterministic, bounded, float-free).
# ---------------------------------------------------------------------------

MAX_CANON_DEPTH = 12
MAX_CANON_NODES = 10_000
MAX_CANON_KEYS = 512
MAX_CANON_ITEMS = 10_000
MAX_CANON_STRING = 262_144
MAX_CANON_BYTES = 262_144


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _canon(value: object, depth: int, counter: list[int]) -> object:
    counter[0] += 1
    if counter[0] > MAX_CANON_NODES or depth > MAX_CANON_DEPTH:
        raise MarketTruthError("SERIALIZATION_INVALID")
    if value is None or isinstance(value, bool) or _is_int(value):
        return value
    if isinstance(value, str):
        if len(value) > MAX_CANON_STRING:
            raise MarketTruthError("SERIALIZATION_INVALID")
        return value
    if isinstance(value, Mapping):
        if len(value) > MAX_CANON_KEYS:
            raise MarketTruthError("SERIALIZATION_INVALID")
        out: dict[str, object] = {}
        for key, item in value.items():
            if not isinstance(key, str) or len(key) > MAX_CANON_STRING:
                raise MarketTruthError("SERIALIZATION_INVALID")
            out[key] = _canon(item, depth + 1, counter)
        return out
    if isinstance(value, (list, tuple)):
        if len(value) > MAX_CANON_ITEMS:
            raise MarketTruthError("SERIALIZATION_INVALID")
        return [_canon(item, depth + 1, counter) for item in value]
    raise MarketTruthError("SERIALIZATION_INVALID")


def canonical_json_bytes(value: object, *, max_bytes: int = MAX_CANON_BYTES) -> bytes:
    """Return deterministic UTF-8 canonical JSON bytes or fail closed.

    Sorted keys, compact separators, explicit nulls, preserved array order, and
    only null/bool/int/string/array/object values. Any float, NaN, Infinity,
    non-string key, or excessive depth/nodes/keys/items/string/bytes fails
    closed with a closed error code.
    """
    if not _is_int(max_bytes) or not 1 <= max_bytes <= MAX_CANON_BYTES:
        raise MarketTruthError("LIMIT_INVALID")
    normalized = _canon(value, 1, [0])
    data = json.dumps(
        normalized,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    if len(data) > max_bytes:
        raise MarketTruthError("SERIALIZATION_INVALID")
    return data


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# ---------------------------------------------------------------------------
# Closed vocabularies.
# ---------------------------------------------------------------------------

SOURCE_KINDS = ("WS", "CLOB", "GAMMA", "DATA", "POLYGON")
OBSERVATION_STATUSES = ("ACCEPTED", "QUARANTINED", "UNSUPPORTED")
RECEIPT_STATUSES = ("OK", "STOPPED", "FAILED")
STOP_REASONS = (
    "NONE",
    "CALLER_STOP",
    "DURATION_EXPIRED",
    "NETWORK_CALL_LIMIT",
    "RECONNECT_LIMIT",
    "QUEUE_LIMIT",
    "STORE_LIMIT",
)
BOOK_APPLY_STATUSES = ("APPLIED", "NO_CHANGE", "REJECTED", "GAPPED")
BOOK_STATES = ("NOT_READY", "READY", "GAPPED")
SESSION_STATES = (
    "IDLE",
    "CONNECTING",
    "STREAMING",
    "RECONNECT_WAIT",
    "STOPPED",
    "FAILED",
)
GAP_STATES = ("OPEN", "HEALED")
CHECKPOINT_STATES = ("ACTIVE", "STOPPED", "REORG_INVALIDATED", "SUPERSEDED")
GAP_REASONS = (
    "DISCONNECT",
    "TIMESTAMP_REGRESSION",
    "HASH_CONFLICT",
    "PARSE_FAULT",
    "QUEUE_OVERFLOW",
    "STORAGE_FAILURE",
    "REORG",
)

# Frozen source and event ranks for deterministic ordering.
SOURCE_RANKS = {"WS": 10, "CLOB": 20, "GAMMA": 30, "DATA": 40, "POLYGON": 50}
EVENT_RANKS = {
    "book": 10,
    "price_change": 20,
    "last_trade_price": 30,
    "tick_size_change": 40,
    "best_bid_ask": 50,
    "new_market": 60,
    "market_resolved": 70,
    "trade": 80,
    "activity": 90,
    "position": 100,
    "holders": 110,
    "dynamic_config": 120,
    "order_filled": 130,
    "unsupported": 900,
}

NORMALIZER_VERSION = "wp169-normalizer/1.0.0"
RETRIEVAL_VERSION = "wp169:1.0.0"
VALIDATOR_VERSION = "pit-validator:1.0.0"
PARAMETER_SET_ID = "params:wp169-public-truth:1.0.0"

_RFC3339_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}Z$"
)
_DECIMAL_RE = re.compile(r"^(?:0|[1-9][0-9]*)(?:\.[0-9]+)?$")


def is_rfc3339_micros(value: object) -> bool:
    if not isinstance(value, str) or _RFC3339_RE.fullmatch(value) is None:
        return False
    try:
        datetime.datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%fZ")
    except ValueError:
        return False
    return True


def epoch_ms_to_rfc3339(milliseconds: int) -> str:
    if not _is_int(milliseconds) or milliseconds < 0:
        raise MarketTruthError("EVENT_INVALID")
    seconds, millis = divmod(milliseconds, 1000)
    try:
        moment = datetime.datetime(1970, 1, 1, tzinfo=datetime.timezone.utc) + (
            datetime.timedelta(seconds=seconds, microseconds=millis * 1000)
        )
    except (OverflowError, OSError, ValueError):
        raise MarketTruthError("EVENT_INVALID")
    return f"{moment:%Y-%m-%dT%H:%M:%S}.{moment.microsecond:06d}Z"


def epoch_seconds_to_rfc3339(seconds: int) -> str:
    if not _is_int(seconds) or seconds < 0:
        raise MarketTruthError("EVENT_INVALID")
    try:
        moment = datetime.datetime(1970, 1, 1, tzinfo=datetime.timezone.utc) + (
            datetime.timedelta(seconds=seconds)
        )
    except (OverflowError, OSError, ValueError):
        raise MarketTruthError("EVENT_INVALID")
    return f"{moment:%Y-%m-%dT%H:%M:%S}.000000Z"


def rfc3339_to_epoch_ms(value: object) -> int | None:
    """Return integer epoch milliseconds for a canonical RFC3339 micros value."""
    if not is_rfc3339_micros(value):
        return None
    moment = datetime.datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%fZ").replace(
        tzinfo=datetime.timezone.utc
    )
    epoch = datetime.datetime(1970, 1, 1, tzinfo=datetime.timezone.utc)
    delta = moment - epoch
    return delta.days * 86_400_000 + delta.seconds * 1000 + delta.microseconds // 1000


def canonical_decimal(value: object) -> str | None:
    """Return the numeric-canonical decimal string for an exact decimal, else None.

    Accepts official noncanonical-but-exact spellings such as "0.50" and returns
    the canonical "0.5"; rejects exponents, negative zero, and non-decimals.
    """
    if isinstance(value, bool) or not isinstance(value, str):
        return None
    if _DECIMAL_RE.fullmatch(value) is None:
        # Accept exact spellings with redundant zeros, then canonicalize.
        if not re.fullmatch(r"[0-9]+(?:\.[0-9]+)?", value):
            return None
    if "." in value:
        integer, fraction = value.split(".", 1)
    else:
        integer, fraction = value, ""
    if len(fraction) > 18:
        return None
    integer = integer.lstrip("0") or "0"
    fraction = fraction.rstrip("0")
    return f"{integer}.{fraction}" if fraction else integer


# ---------------------------------------------------------------------------
# Content and occurrence identities.
# ---------------------------------------------------------------------------

RAW_ID_PREFIX = "markettruth:raw:sha256:"
OCCURRENCE_ID_PREFIX = "markettruth:occurrence:sha256:"
OBSERVATION_ID_PREFIX = "markettruth:observation:sha256:"
SOURCE_LOG_ID_PREFIX = "markettruth:polygon-log:sha256:"
CHECKPOINT_VERSION = "wp169-checkpoint/1.0.0"


def compute_raw_id(
    *, source_kind: str, source_id: str, media_type: str, raw_sha256: str, byte_length: int
) -> str:
    digest = sha256_hex(
        canonical_json_bytes(
            {
                "version": "wp169-raw/1.0.0",
                "source_kind": source_kind,
                "source_id": source_id,
                "media_type": media_type,
                "raw_sha256": raw_sha256,
                "byte_length": byte_length,
            }
        )
    )
    return RAW_ID_PREFIX + digest


def compute_occurrence_id(
    *,
    raw_id: str,
    received_at: str,
    source_id: str,
    source_cursor: str,
    occurrence_sequence: int,
) -> str:
    digest = sha256_hex(
        canonical_json_bytes(
            {
                "version": "wp169-occurrence/1.0.0",
                "raw_id": raw_id,
                "received_at": received_at,
                "source_id": source_id,
                "source_cursor": source_cursor,
                "occurrence_sequence": occurrence_sequence,
            }
        )
    )
    return OCCURRENCE_ID_PREFIX + digest


def compute_observation_id(
    *,
    source_content_id: str,
    source_kind: str,
    event_kind: str,
    event_id: str | None,
    market_id: str | None,
    asset_id: str | None,
    event_time: str | None,
    canonical_payload_sha256: str,
    status: str,
    error_codes: Sequence[str],
    book_ready: bool,
    provenance_json: str,
) -> str:
    digest = sha256_hex(
        canonical_json_bytes(
            {
                "version": "wp169-normalizer/1.0.0",
                "source_content_id": source_content_id,
                "source_kind": source_kind,
                "event_kind": event_kind,
                "event_id": event_id,
                "market_id": market_id,
                "asset_id": asset_id,
                "event_time": event_time,
                "canonical_payload_sha256": canonical_payload_sha256,
                "status": status,
                "error_codes": list(error_codes),
                "book_ready": book_ready,
                "provenance_json": provenance_json,
            }
        )
    )
    return OBSERVATION_ID_PREFIX + digest


def compute_source_log_id(
    *,
    chain_id: int,
    exchange_address: str,
    block_number: int,
    block_hash: str,
    transaction_hash: str,
    log_index: int,
    event_topic: str,
) -> str:
    digest = sha256_hex(
        canonical_json_bytes(
            {
                "version": "wp169-order-filled-v2/1.0.0",
                "chain_id": chain_id,
                "exchange_address": exchange_address,
                "block_number": block_number,
                "block_hash": block_hash,
                "transaction_hash": transaction_hash,
                "log_index": log_index,
                "event_topic": event_topic,
            }
        )
    )
    return SOURCE_LOG_ID_PREFIX + digest


def compute_checkpoint_sha256(
    *,
    checkpoint_key: str,
    sequence: int,
    state: str,
    value_json: str,
    previous_sha256: str | None,
) -> str:
    return sha256_hex(
        canonical_json_bytes(
            {
                "version": CHECKPOINT_VERSION,
                "checkpoint_key": checkpoint_key,
                "sequence": sequence,
                "state": state,
                "value_json": value_json,
                "previous_sha256": previous_sha256,
            }
        )
    )


# ---------------------------------------------------------------------------
# Frozen public records.
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class RawEnvelope:
    raw_id: str
    occurrence_id: str
    source_kind: str
    source_id: str
    source_cursor: str
    received_at: str
    media_type: str
    raw_bytes: bytes
    byte_length: int
    raw_sha256: str


@dataclasses.dataclass(frozen=True)
class NormalizedObservation:
    observation_id: str
    occurrence_id: str
    raw_id: str
    source_kind: str
    event_kind: str
    event_id: str | None
    market_id: str | None
    asset_id: str | None
    event_time: str | None
    received_at: str
    canonical_payload_json: str
    canonical_payload_sha256: str
    status: str
    error_codes: tuple[str, ...]
    book_ready: bool
    provenance_json: str


_LIMIT_DEFAULTS: dict[str, int] = {
    "max_frame_bytes": 1_048_576,
    "max_response_bytes": 4_194_304,
    "max_record_bytes": 262_144,
    "max_records_per_page": 10_000,
    "max_pages": 10,
    "max_retries": 3,
    "request_timeout_seconds": 20,
    "retry_after_max_seconds": 30,
    "max_backoff_seconds": 30,
    "max_queue_items": 10_000,
    "max_store_rows": 1_000_000,
    "max_store_bytes": 4_294_967_296,
    "heartbeat_seconds": 10,
    "max_block_span": 2_000,
    "confirmation_depth": 64,
    "max_network_calls": 1_000,
    "max_reconnect_attempts": 100,
    "max_book_levels_per_side": 5_000,
    "data_calls_per_10_seconds": 100,
    "gamma_calls_per_10_seconds": 100,
    "clob_calls_per_10_seconds": 100,
    "rpc_calls_per_second": 10,
    "data_poll_seconds": 10,
    "gamma_poll_seconds": 60,
    "clob_poll_seconds": 60,
    "rpc_poll_seconds": 12,
    "max_runtime_seconds": 86_400,
}


@dataclasses.dataclass(frozen=True)
class AcquisitionLimits:
    max_frame_bytes: int = _LIMIT_DEFAULTS["max_frame_bytes"]
    max_response_bytes: int = _LIMIT_DEFAULTS["max_response_bytes"]
    max_record_bytes: int = _LIMIT_DEFAULTS["max_record_bytes"]
    max_records_per_page: int = _LIMIT_DEFAULTS["max_records_per_page"]
    max_pages: int = _LIMIT_DEFAULTS["max_pages"]
    max_retries: int = _LIMIT_DEFAULTS["max_retries"]
    request_timeout_seconds: int = _LIMIT_DEFAULTS["request_timeout_seconds"]
    retry_after_max_seconds: int = _LIMIT_DEFAULTS["retry_after_max_seconds"]
    max_backoff_seconds: int = _LIMIT_DEFAULTS["max_backoff_seconds"]
    max_queue_items: int = _LIMIT_DEFAULTS["max_queue_items"]
    max_store_rows: int = _LIMIT_DEFAULTS["max_store_rows"]
    max_store_bytes: int = _LIMIT_DEFAULTS["max_store_bytes"]
    heartbeat_seconds: int = _LIMIT_DEFAULTS["heartbeat_seconds"]
    max_block_span: int = _LIMIT_DEFAULTS["max_block_span"]
    confirmation_depth: int = _LIMIT_DEFAULTS["confirmation_depth"]
    max_network_calls: int = _LIMIT_DEFAULTS["max_network_calls"]
    max_reconnect_attempts: int = _LIMIT_DEFAULTS["max_reconnect_attempts"]
    max_book_levels_per_side: int = _LIMIT_DEFAULTS["max_book_levels_per_side"]
    data_calls_per_10_seconds: int = _LIMIT_DEFAULTS["data_calls_per_10_seconds"]
    gamma_calls_per_10_seconds: int = _LIMIT_DEFAULTS["gamma_calls_per_10_seconds"]
    clob_calls_per_10_seconds: int = _LIMIT_DEFAULTS["clob_calls_per_10_seconds"]
    rpc_calls_per_second: int = _LIMIT_DEFAULTS["rpc_calls_per_second"]
    data_poll_seconds: int = _LIMIT_DEFAULTS["data_poll_seconds"]
    gamma_poll_seconds: int = _LIMIT_DEFAULTS["gamma_poll_seconds"]
    clob_poll_seconds: int = _LIMIT_DEFAULTS["clob_poll_seconds"]
    rpc_poll_seconds: int = _LIMIT_DEFAULTS["rpc_poll_seconds"]
    max_runtime_seconds: int = _LIMIT_DEFAULTS["max_runtime_seconds"]

    def __post_init__(self) -> None:
        for field_name, default in _LIMIT_DEFAULTS.items():
            value = getattr(self, field_name)
            if not _is_int(value) or value < 1 or value > default:
                raise MarketTruthError("LIMIT_INVALID")


@dataclasses.dataclass(frozen=True)
class AcquisitionReceipt:
    status: str
    error_codes: tuple[str, ...]
    raw_count: int
    normalized_count: int
    quarantined_count: int
    gap_count: int
    checkpoint_sequence: int
    store_bytes: int
    stop_reason: str


@dataclasses.dataclass(frozen=True)
class BookApplyResult:
    status: str
    error_codes: tuple[str, ...]
    asset_id: str | None
    ready: bool
    gap_open: bool
    applied: bool


@dataclasses.dataclass(frozen=True)
class BookStateTransition:
    asset_id: str
    from_state: str
    to_state: str
    reason: str


@dataclasses.dataclass(frozen=True)
class BookFramePlan:
    observations: tuple[NormalizedObservation, ...]
    transitions: tuple[BookStateTransition, ...]
    state_json: str


@dataclasses.dataclass(frozen=True)
class SubscriptionUpdate:
    operation: str
    asset_ids: tuple[str, ...]


@dataclasses.dataclass(frozen=True)
class SubscriptionControlResult:
    status: str
    error_codes: tuple[str, ...]
    accepted: bool
    queued: int


@dataclasses.dataclass(frozen=True)
class PublicPageResult:
    status: str
    error_codes: tuple[str, ...]
    attempts: tuple[RawEnvelope, ...]
    successful_attempt_index: int | None


@dataclasses.dataclass(frozen=True)
class PitPromotionResult:
    is_valid: bool
    status: str
    error_codes: tuple[str, ...]
    source_snapshot_result: PointInTimeBuildResult | None
    observation_result: PointInTimeBuildResult | None


@dataclasses.dataclass(frozen=True)
class Checkpoint:
    sequence: int
    history_sequence: int
    checkpoint_key: str
    value_json: str
    value_sha256: str
    previous_sha256: str | None
    state: str


@dataclasses.dataclass(frozen=True)
class MarketTruthRuntimeConfig:
    output_db: pathlib.Path
    asset_ids: tuple[str, ...] = ()
    discover_active: bool = False
    duration_seconds: int = 60
    max_pages: int = 1
    wallet: str | None = None
    condition_id: str | None = None
    rpc_provider: str = "drpc"
    from_block: int | None = None
    to_block: int | None = None
    onchain_lookback_blocks: int = 100


# ---------------------------------------------------------------------------
# Asset-id and identifier validation.
# ---------------------------------------------------------------------------

_TOKEN_ID_RE = re.compile(r"^(?:0|[1-9][0-9]{0,77})$")
_WALLET_RE = re.compile(r"^0x[0-9a-f]{40}$")
_CONDITION_RE = re.compile(r"^0x[0-9a-f]{64}$")
# Canonical positive base-10 identifier: no leading zeros, not "0". Used for event ids
# so that padded spellings such as "007" are rejected rather than silently accepted.
_POSITIVE_INT_RE = re.compile(r"^[1-9][0-9]*$")


def _canonical_event_id(value: object) -> str | None:
    """Return the canonical positive base-10 event id for a str/int, else None.

    Rejects leading zeros (e.g. "007") and non-positive values, matching the frozen
    "positive canonical base-10 id" requirement for new_market and Gamma event ids.
    """
    if isinstance(value, str) and _POSITIVE_INT_RE.fullmatch(value) is not None:
        return value
    if _is_int(value) and value > 0:
        return str(value)
    return None


def _decode_token_list(value: object) -> list[object] | None:
    """Return a token list from a decoded array or a JSON-array string, else None.

    Gamma's clobTokenIds is documented as either an already-decoded array or a
    JSON-encoded array string; both must yield a list so containment checks are exact.
    """
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            decoded = json.loads(value)
        except ValueError:
            return None
        return decoded if isinstance(decoded, list) else None
    return None


def is_valid_token_id(value: object) -> bool:
    return isinstance(value, str) and _TOKEN_ID_RE.fullmatch(value) is not None


def validate_asset_ids(asset_ids: Sequence[str], *, maximum: int = 500) -> tuple[str, ...]:
    if not isinstance(asset_ids, (list, tuple)) or not 1 <= len(asset_ids) <= maximum:
        raise MarketTruthError("INPUT_INVALID")
    seen: set[str] = set()
    for asset_id in asset_ids:
        if not is_valid_token_id(asset_id) or asset_id in seen:
            raise MarketTruthError("INPUT_INVALID")
        seen.add(asset_id)
    return tuple(asset_ids)


# ---------------------------------------------------------------------------
# Raw envelope construction.
# ---------------------------------------------------------------------------


def make_raw_envelope(
    source_kind: str,
    source_id: str,
    source_cursor: str,
    received_at: str,
    raw_bytes: bytes,
    *,
    occurrence_sequence: int,
    limits: AcquisitionLimits | None = None,
) -> RawEnvelope:
    """Build one immutable raw evidence envelope with content/occurrence ids."""
    active = limits or AcquisitionLimits()
    if source_kind not in SOURCE_KINDS:
        raise MarketTruthError("INPUT_INVALID")
    if not isinstance(source_id, str) or not source_id:
        raise MarketTruthError("INPUT_INVALID")
    if not isinstance(source_cursor, str) or not source_cursor:
        raise MarketTruthError("INPUT_INVALID")
    if not is_rfc3339_micros(received_at):
        raise MarketTruthError("INPUT_INVALID")
    if not isinstance(raw_bytes, (bytes, bytearray)):
        raise MarketTruthError("INPUT_INVALID")
    if not _is_int(occurrence_sequence) or occurrence_sequence < 0:
        raise MarketTruthError("INPUT_INVALID")
    payload = bytes(raw_bytes)
    byte_length = len(payload)
    if byte_length > active.max_response_bytes:
        raise MarketTruthError("RAW_TOO_LARGE")
    media_type = "application/json"
    raw_sha256 = sha256_hex(payload)
    raw_id = compute_raw_id(
        source_kind=source_kind,
        source_id=source_id,
        media_type=media_type,
        raw_sha256=raw_sha256,
        byte_length=byte_length,
    )
    occurrence_id = compute_occurrence_id(
        raw_id=raw_id,
        received_at=received_at,
        source_id=source_id,
        source_cursor=source_cursor,
        occurrence_sequence=occurrence_sequence,
    )
    return RawEnvelope(
        raw_id=raw_id,
        occurrence_id=occurrence_id,
        source_kind=source_kind,
        source_id=source_id,
        source_cursor=source_cursor,
        received_at=received_at,
        media_type=media_type,
        raw_bytes=payload,
        byte_length=byte_length,
        raw_sha256=raw_sha256,
    )


# ---------------------------------------------------------------------------
# Normalizer helpers.
# ---------------------------------------------------------------------------


def _provenance_ws(frame_event_type: str | None, child_index: int, event_hash: str | None) -> str:
    return canonical_json_bytes(
        {
            "normalizer_version": NORMALIZER_VERSION,
            "frame_event_type": frame_event_type,
            "child_index": child_index,
            "event_hash": event_hash,
        }
    ).decode("utf-8")


def _provenance_http(endpoint: str, child_index: int) -> str:
    return canonical_json_bytes(
        {
            "normalizer_version": NORMALIZER_VERSION,
            "endpoint": endpoint,
            "child_index": child_index,
        }
    ).decode("utf-8")


def _provenance_polygon(chain_id: int, exchange_address: str, child_index: int) -> str:
    return canonical_json_bytes(
        {
            "normalizer_version": NORMALIZER_VERSION,
            "chain_id": chain_id,
            "exchange_address": exchange_address,
            "child_index": child_index,
        }
    ).decode("utf-8")


def _build_observation(
    *,
    raw: RawEnvelope,
    source_content_id: str,
    event_kind: str,
    event_id: str | None,
    market_id: str | None,
    asset_id: str | None,
    event_time: str | None,
    payload: Mapping[str, object],
    status: str,
    error_codes: Sequence[str],
    book_ready: bool,
    provenance_json: str,
) -> NormalizedObservation:
    canonical_payload_json = canonical_json_bytes(payload).decode("utf-8")
    canonical_payload_sha256 = sha256_hex(canonical_payload_json.encode("utf-8"))
    ordered = order_error_codes(error_codes)
    observation_id = compute_observation_id(
        source_content_id=source_content_id,
        source_kind=raw.source_kind,
        event_kind=event_kind,
        event_id=event_id,
        market_id=market_id,
        asset_id=asset_id,
        event_time=event_time,
        canonical_payload_sha256=canonical_payload_sha256,
        status=status,
        error_codes=ordered,
        book_ready=book_ready,
        provenance_json=provenance_json,
    )
    return NormalizedObservation(
        observation_id=observation_id,
        occurrence_id=raw.occurrence_id,
        raw_id=raw.raw_id,
        source_kind=raw.source_kind,
        event_kind=event_kind,
        event_id=event_id,
        market_id=market_id,
        asset_id=asset_id,
        event_time=event_time,
        received_at=raw.received_at,
        canonical_payload_json=canonical_payload_json,
        canonical_payload_sha256=canonical_payload_sha256,
        status=status,
        error_codes=ordered,
        book_ready=book_ready,
        provenance_json=provenance_json,
    )


def _parse_json(raw_bytes: bytes) -> object | None:
    try:
        text = raw_bytes.decode("utf-8")
    except UnicodeDecodeError:
        return None
    try:
        return json.loads(text)
    except (ValueError, RecursionError):
        return None


def _string_or_none(value: object) -> str | None:
    return value if isinstance(value, str) else None


def _decimal_or_none(value: object) -> str | None:
    return canonical_decimal(value)


def _event_time_from_ms(value: object) -> str | None:
    if isinstance(value, str) and value.isdigit():
        try:
            return epoch_ms_to_rfc3339(int(value))
        except MarketTruthError:
            return None
    if _is_int(value) and value >= 0:
        try:
            return epoch_ms_to_rfc3339(value)
        except MarketTruthError:
            return None
    return None


def _event_time_from_seconds(value: object) -> str | None:
    if isinstance(value, str) and value.isdigit():
        try:
            return epoch_seconds_to_rfc3339(int(value))
        except MarketTruthError:
            return None
    if _is_int(value) and value >= 0:
        try:
            return epoch_seconds_to_rfc3339(value)
        except MarketTruthError:
            return None
    return None


def _levels(raw_levels: object) -> list[dict[str, str]] | None:
    if not isinstance(raw_levels, list):
        return None
    out: list[dict[str, str]] = []
    for level in raw_levels:
        if not isinstance(level, Mapping):
            return None
        price = canonical_decimal(level.get("price"))
        size = canonical_decimal(level.get("size"))
        if price is None or size is None:
            return None
        out.append({"price": price, "size": size})
    return out


# WebSocket event decoders return (event_kind, market_id, asset_id, event_time, payload).
def normalize_websocket_message(
    raw: RawEnvelope,
    *,
    book_readiness: Mapping[str, bool],
) -> tuple[NormalizedObservation, ...]:
    """Normalize one Market WebSocket frame into ordered observations.

    Unknown or malformed frames are preserved as raw evidence and returned as a
    single UNSUPPORTED or QUARANTINED observation; nothing is silently dropped.
    """
    if raw.source_kind != "WS":
        raise MarketTruthError("INPUT_INVALID")
    document = _parse_json(raw.raw_bytes)
    messages: list[object]
    if isinstance(document, list):
        messages = list(document)
    elif isinstance(document, Mapping):
        messages = [document]
    else:
        return (
            _build_observation(
                raw=raw,
                source_content_id=raw.raw_id,
                event_kind="unsupported",
                event_id=None,
                market_id=None,
                asset_id=None,
                event_time=None,
                payload={"reason": "NON_OBJECT_FRAME"},
                status="QUARANTINED",
                error_codes=("EVENT_INVALID",),
                book_ready=False,
                provenance_json=_provenance_ws(None, 0, None),
            ),
        )
    observations: list[NormalizedObservation] = []
    child_index = 0
    for message in messages:
        if not isinstance(message, Mapping):
            observations.append(
                _build_observation(
                    raw=raw,
                    source_content_id=raw.raw_id,
                    event_kind="unsupported",
                    event_id=None,
                    market_id=None,
                    asset_id=None,
                    event_time=None,
                    payload={"reason": "NON_OBJECT_MESSAGE"},
                    status="QUARANTINED",
                    error_codes=("EVENT_INVALID",),
                    book_ready=False,
                    provenance_json=_provenance_ws(None, child_index, None),
                )
            )
            child_index += 1
            continue
        observations.extend(
            _normalize_ws_message(raw, message, book_readiness, child_index)
        )
        child_index += 1
    if not observations:
        observations.append(
            _build_observation(
                raw=raw,
                source_content_id=raw.raw_id,
                event_kind="unsupported",
                event_id=None,
                market_id=None,
                asset_id=None,
                event_time=None,
                payload={"reason": "EMPTY_FRAME"},
                status="UNSUPPORTED",
                error_codes=("EVENT_UNSUPPORTED",),
                book_ready=False,
                provenance_json=_provenance_ws(None, 0, None),
            )
        )
    return tuple(observations)


def _normalize_ws_message(
    raw: RawEnvelope,
    message: Mapping[str, object],
    book_readiness: Mapping[str, bool],
    child_index: int,
) -> list[NormalizedObservation]:
    event_type = message.get("event_type")
    event_hash = _string_or_none(message.get("hash"))
    market_id = _string_or_none(message.get("market"))

    if event_type == "book":
        asset_id = _string_or_none(message.get("asset_id"))
        event_time = _event_time_from_ms(message.get("timestamp"))
        bids = _levels(message.get("bids"))
        asks = _levels(message.get("asks"))
        if asset_id is None or bids is None or asks is None:
            return [
                _build_observation(
                    raw=raw,
                    source_content_id=raw.raw_id,
                    event_kind="book",
                    event_id=None,
                    market_id=market_id,
                    asset_id=asset_id,
                    event_time=event_time,
                    payload={"reason": "BOOK_FIELDS_INVALID"},
                    status="QUARANTINED",
                    error_codes=("EVENT_INVALID",),
                    book_ready=False,
                    provenance_json=_provenance_ws("book", child_index, event_hash),
                )
            ]
        payload = {
            "market": market_id,
            "asset_id": asset_id,
            "timestamp": event_time,
            "hash": event_hash,
            "bids": bids,
            "asks": asks,
        }
        return [
            _build_observation(
                raw=raw,
                source_content_id=raw.raw_id,
                event_kind="book",
                event_id=None,
                market_id=market_id,
                asset_id=asset_id,
                event_time=event_time,
                payload=payload,
                status="ACCEPTED",
                error_codes=(),
                book_ready=True,
                provenance_json=_provenance_ws("book", child_index, event_hash),
            )
        ]

    if event_type == "price_change":
        changes = message.get("price_changes") or message.get("changes")
        event_time = _event_time_from_ms(message.get("timestamp"))
        if not isinstance(changes, list):
            return [
                _build_observation(
                    raw=raw,
                    source_content_id=raw.raw_id,
                    event_kind="price_change",
                    event_id=None,
                    market_id=market_id,
                    asset_id=None,
                    event_time=event_time,
                    payload={"reason": "PRICE_CHANGE_INVALID"},
                    status="QUARANTINED",
                    error_codes=("EVENT_INVALID",),
                    book_ready=False,
                    provenance_json=_provenance_ws("price_change", child_index, event_hash),
                )
            ]
        results: list[NormalizedObservation] = []
        for change in changes:
            if not isinstance(change, Mapping):
                results.append(
                    _build_observation(
                        raw=raw,
                        source_content_id=raw.raw_id,
                        event_kind="price_change",
                        event_id=None,
                        market_id=market_id,
                        asset_id=None,
                        event_time=event_time,
                        payload={"reason": "PRICE_CHANGE_ITEM_INVALID"},
                        status="QUARANTINED",
                        error_codes=("EVENT_INVALID",),
                        book_ready=False,
                        provenance_json=_provenance_ws(
                            "price_change", child_index, event_hash
                        ),
                    )
                )
                continue
            asset_id = _string_or_none(change.get("asset_id"))
            price = _decimal_or_none(change.get("price"))
            size = _decimal_or_none(change.get("size"))
            side = _string_or_none(change.get("side"))
            ready = bool(book_readiness.get(asset_id)) if asset_id is not None else False
            payload = {
                "market": market_id,
                "asset_id": asset_id,
                "timestamp": event_time,
                "price": price,
                "size": size,
                "side": side,
                "hash": event_hash,
                "best_bid": _decimal_or_none(change.get("best_bid")),
                "best_ask": _decimal_or_none(change.get("best_ask")),
            }
            if asset_id is None or price is None or size is None or side not in ("BUY", "SELL"):
                status, errors, book_ready = "QUARANTINED", ("EVENT_INVALID",), False
            elif not ready:
                status, errors, book_ready = "QUARANTINED", ("BOOK_GAP_ACTIVE",), False
            else:
                status, errors, book_ready = "ACCEPTED", (), True
            results.append(
                _build_observation(
                    raw=raw,
                    source_content_id=raw.raw_id,
                    event_kind="price_change",
                    event_id=None,
                    market_id=market_id,
                    asset_id=asset_id,
                    event_time=event_time,
                    payload=payload,
                    status=status,
                    error_codes=errors,
                    book_ready=book_ready,
                    provenance_json=_provenance_ws("price_change", child_index, event_hash),
                )
            )
        return results

    simple_kinds = {
        "last_trade_price": "last_trade_price",
        "tick_size_change": "tick_size_change",
        "best_bid_ask": "best_bid_ask",
        "new_market": "new_market",
        "market_resolved": "market_resolved",
    }
    if isinstance(event_type, str) and event_type in simple_kinds:
        kind = simple_kinds[event_type]
        asset_id = _string_or_none(message.get("asset_id"))
        event_time = _event_time_from_ms(message.get("timestamp"))
        event_id = None
        if kind == "new_market":
            event_message = message.get("event_message")
            if isinstance(event_message, Mapping):
                # event_id is the positive canonical base-10 event_message.id (no leading
                # zeros); the top-level id is the Gamma market id, not an event id.
                event_id = _canonical_event_id(event_message.get("id"))
        payload = _ws_simple_payload(kind, message, market_id, asset_id, event_time, event_hash)
        return [
            _build_observation(
                raw=raw,
                source_content_id=raw.raw_id,
                event_kind=kind,
                event_id=event_id,
                market_id=market_id,
                asset_id=asset_id,
                event_time=event_time,
                payload=payload,
                status="ACCEPTED",
                error_codes=(),
                book_ready=False,
                provenance_json=_provenance_ws(kind, child_index, event_hash),
            )
        ]

    return [
        _build_observation(
            raw=raw,
            source_content_id=raw.raw_id,
            event_kind="unsupported",
            event_id=None,
            market_id=market_id,
            asset_id=_string_or_none(message.get("asset_id")),
            event_time=None,
            payload={"event_type": event_type if isinstance(event_type, str) else None},
            status="UNSUPPORTED",
            error_codes=("EVENT_UNSUPPORTED",),
            book_ready=False,
            provenance_json=_provenance_ws(
                event_type if isinstance(event_type, str) else None, child_index, event_hash
            ),
        )
    ]


def _ws_simple_payload(
    kind: str,
    message: Mapping[str, object],
    market_id: str | None,
    asset_id: str | None,
    event_time: str | None,
    event_hash: str | None,
) -> dict[str, object]:
    if kind == "last_trade_price":
        return {
            "market": market_id,
            "asset_id": asset_id,
            "timestamp": event_time,
            "price": _decimal_or_none(message.get("price")),
            "size": _decimal_or_none(message.get("size")),
            "side": _string_or_none(message.get("side")),
            "fee_rate_bps": _string_or_none(message.get("fee_rate_bps")),
            "transaction_hash": _string_or_none(message.get("transaction_hash")),
        }
    if kind == "tick_size_change":
        return {
            "market": market_id,
            "asset_id": asset_id,
            "timestamp": event_time,
            "old_tick_size": _decimal_or_none(message.get("old_tick_size")),
            "new_tick_size": _decimal_or_none(message.get("new_tick_size")),
        }
    if kind == "best_bid_ask":
        return {
            "market": market_id,
            "asset_id": asset_id,
            "timestamp": event_time,
            "best_bid": _decimal_or_none(message.get("best_bid")),
            "best_ask": _decimal_or_none(message.get("best_ask")),
            "spread": _decimal_or_none(message.get("spread")),
        }
    # new_market / market_resolved lifecycle metadata (raw lifecycle fields).
    return {
        "market": market_id,
        "asset_id": asset_id,
        "timestamp": event_time,
        "condition_id": _string_or_none(message.get("condition_id")),
        "question": _string_or_none(message.get("question")),
        "description": _string_or_none(message.get("description")),
        "slug": _string_or_none(message.get("slug")),
        "outcomes": message.get("outcomes") if isinstance(message.get("outcomes"), list) else None,
        "winner": _string_or_none(message.get("winner")),
        "status": _string_or_none(message.get("status")),
    }


# ---------------------------------------------------------------------------
# Public HTTP record normalizer.
# ---------------------------------------------------------------------------

_HTTP_ENDPOINT_KINDS = {
    "trades": "trade",
    "activity": "activity",
    "positions": "position",
    "holders": "holders",
    "markets": "dynamic_config",
    "market-by-id": "dynamic_config",
    "book": "dynamic_config",
    "fee-rate": "dynamic_config",
    "clob-market-info": "dynamic_config",
}


def normalize_public_record(
    raw: RawEnvelope,
    *,
    endpoint: str,
    record_index: int,
) -> NormalizedObservation:
    """Normalize one already-archived public HTTP record into an observation."""
    if endpoint not in _HTTP_ENDPOINT_KINDS:
        raise MarketTruthError("ENDPOINT_FORBIDDEN")
    if not _is_int(record_index) or record_index < 0:
        raise MarketTruthError("INPUT_INVALID")
    kind = _HTTP_ENDPOINT_KINDS[endpoint]
    parsed = _parse_json(raw.raw_bytes)
    provenance = _provenance_http(endpoint, record_index)
    if isinstance(parsed, list):
        document = parsed[record_index] if 0 <= record_index < len(parsed) else None
    else:
        document = parsed
    if not isinstance(document, Mapping):
        return _build_observation(
            raw=raw,
            source_content_id=raw.raw_id,
            event_kind=kind,
            event_id=None,
            market_id=None,
            asset_id=None,
            event_time=None,
            payload={"reason": "NON_OBJECT_RECORD"},
            status="QUARANTINED",
            error_codes=("RESPONSE_INVALID",),
            book_ready=False,
            provenance_json=provenance,
        )
    market_id = _string_or_none(document.get("conditionId") or document.get("market") or document.get("condition_id"))
    asset_id = _string_or_none(document.get("asset") or document.get("token_id") or document.get("tokenId"))
    # Public Data/Gamma/CLOB timestamps are certified as Unix SECONDS (unlike the
    # WebSocket epoch-millisecond values), converted with integer arithmetic only.
    event_time = _event_time_from_seconds(document.get("timestamp"))
    payload = _http_payload(kind, endpoint, document, market_id, asset_id, event_time)
    return _build_observation(
        raw=raw,
        source_content_id=raw.raw_id,
        event_kind=kind,
        event_id=None,
        market_id=market_id,
        asset_id=asset_id,
        event_time=event_time,
        payload=payload,
        status="ACCEPTED",
        error_codes=(),
        book_ready=False,
        provenance_json=provenance,
    )


def _bool_or_none(value: object) -> bool | None:
    return value if isinstance(value, bool) else None


def _dynamic_config_payload(
    endpoint: str,
    document: Mapping[str, object],
    market_id: str | None,
    asset_id: str | None,
) -> dict[str, object]:
    """Normalize the full frozen Gamma/CLOB dynamic-config allowlist.

    Absent optional fields are preserved as explicit null so a later observation
    with a changed parameter yields a new PIT version without rewriting history.
    Unknown upstream keys remain in raw evidence, never in normalization.
    """
    clob_tokens = document.get("clobTokenIds")
    return {
        "endpoint": endpoint,
        "market": market_id,
        "asset_id": asset_id,
        # CLOB /book config.
        "min_order_size": _string_or_none(document.get("min_order_size") or document.get("minimum_order_size")),
        "tick_size": _string_or_none(document.get("tick_size") or document.get("minimum_tick_size")),
        "neg_risk": _bool_or_none(document.get("neg_risk")),
        "last_trade_price": _string_or_none(document.get("last_trade_price")),
        # CLOB /fee-rate.
        "base_fee": _string_or_none(document.get("base_fee") or document.get("baseFee")),
        # CLOB market-info config (mos/mts/mbf/tbf/rfqe/itode/ibce/fd/oas/rewards/tokens).
        "mos": _string_or_none(document.get("mos")),
        "mts": _string_or_none(document.get("mts")),
        "mbf": _string_or_none(document.get("mbf")),
        "tbf": _string_or_none(document.get("tbf")),
        "rfqe": _bool_or_none(document.get("rfqe")),
        "itode": _bool_or_none(document.get("itode")),
        "ibce": _bool_or_none(document.get("ibce")),
        "fd": _string_or_none(document.get("fd")),
        "oas": _bool_or_none(document.get("oas")),
        "rewards": document.get("rewards") if isinstance(document.get("rewards"), (dict, list)) else None,
        "tokens": document.get("tokens") if isinstance(document.get("tokens"), list) else None,
        # Gamma market metadata / lifecycle.
        "id": _string_or_none(document.get("id")) if isinstance(document.get("id"), str) else (str(document.get("id")) if _is_int(document.get("id")) else None),
        "conditionId": _string_or_none(document.get("conditionId")),
        "question": _string_or_none(document.get("question")),
        "description": _string_or_none(document.get("description")),
        "slug": _string_or_none(document.get("slug")),
        "resolutionSource": _string_or_none(document.get("resolutionSource")),
        "endDate": _string_or_none(document.get("endDate")),
        "active": _bool_or_none(document.get("active")),
        "closed": _bool_or_none(document.get("closed")),
        "archived": _bool_or_none(document.get("archived")),
        "acceptingOrders": _bool_or_none(document.get("acceptingOrders")),
        "orderPriceMinTickSize": _string_or_none(document.get("orderPriceMinTickSize")),
        "orderMinSize": _string_or_none(document.get("orderMinSize")),
        "umaResolutionStatus": _string_or_none(document.get("umaResolutionStatus")),
        "automaticallyResolved": _bool_or_none(document.get("automaticallyResolved")),
        "secondsDelay": document.get("secondsDelay") if _is_int(document.get("secondsDelay")) else None,
        "feesEnabled": _bool_or_none(document.get("feesEnabled")),
        "outcomes": document.get("outcomes") if isinstance(document.get("outcomes"), list) else None,
        "clobTokenIds": clob_tokens if isinstance(clob_tokens, (str, list)) else None,
        "event_id": _derive_gamma_event_id(document.get("events")),
    }


def _derive_gamma_event_id(events: object) -> str | None:
    """Gamma event_id is set only for an exact singleton events[] with a positive
    canonical base-10 id (no leading zeros)."""
    if not isinstance(events, list) or len(events) != 1 or not isinstance(events[0], Mapping):
        return None
    return _canonical_event_id(events[0].get("id"))


def build_page_quarantine(
    raw: RawEnvelope, endpoint: str, code: str, record_index: int = 0
) -> NormalizedObservation:
    """Build one sanitized quarantined observation for a page-level bound failure.

    No raw values are echoed; only the closed code and endpoint kind are recorded.
    """
    kind = _HTTP_ENDPOINT_KINDS.get(endpoint, "unsupported")
    return _build_observation(
        raw=raw,
        source_content_id=raw.raw_id,
        event_kind=kind,
        event_id=None,
        market_id=None,
        asset_id=None,
        event_time=None,
        payload={"reason": code},
        status="QUARANTINED",
        error_codes=(code,),
        book_ready=False,
        provenance_json=_provenance_http(endpoint, record_index),
    )


def _http_payload(
    kind: str,
    endpoint: str,
    document: Mapping[str, object],
    market_id: str | None,
    asset_id: str | None,
    event_time: str | None,
) -> dict[str, object]:
    if kind == "dynamic_config":
        return _dynamic_config_payload(endpoint, document, market_id, asset_id)
    # trade / activity / position / holders
    return {
        "endpoint": endpoint,
        "market": market_id,
        "asset_id": asset_id,
        "timestamp": event_time,
        "side": _string_or_none(document.get("side")),
        "type": _string_or_none(document.get("type")),
        "price": _string_or_none(document.get("price")),
        "size": _string_or_none(document.get("size")),
        "outcome": _string_or_none(document.get("outcome")),
        "user": _string_or_none(document.get("proxyWallet") or document.get("user")),
        "transactionHash": _string_or_none(document.get("transactionHash") or document.get("transaction_hash")),
        "title": _string_or_none(document.get("title")),
        "slug": _string_or_none(document.get("slug")),
    }


# ---------------------------------------------------------------------------
# Recursive no-echo sanitization boundary.
# ---------------------------------------------------------------------------

# Field classification per public dataclass: 'scalar' trusted, 'scan' recursively
# scanned, 'raw_evidence' authorized bytes-only boundary. Adding an unclassified
# field must fail the coverage test.
FIELD_CLASSIFICATION: dict[str, dict[str, str]] = {
    "RawEnvelope": {
        "raw_id": "scalar",
        "occurrence_id": "scalar",
        "source_kind": "scalar",
        "source_id": "scalar",
        "source_cursor": "scalar",
        "received_at": "scalar",
        "media_type": "scalar",
        "raw_bytes": "raw_evidence",
        "byte_length": "scalar",
        "raw_sha256": "scalar",
    },
    "NormalizedObservation": {
        "observation_id": "scalar",
        "occurrence_id": "scalar",
        "raw_id": "scalar",
        "source_kind": "scalar",
        "event_kind": "scalar",
        "event_id": "scalar",
        "market_id": "scalar",
        "asset_id": "scalar",
        "event_time": "scalar",
        "received_at": "scalar",
        "canonical_payload_json": "scan",
        "canonical_payload_sha256": "scalar",
        "status": "scalar",
        "error_codes": "scalar",
        "book_ready": "scalar",
        "provenance_json": "scan",
    },
    "AcquisitionReceipt": {
        "status": "scalar",
        "error_codes": "scalar",
        "raw_count": "scalar",
        "normalized_count": "scalar",
        "quarantined_count": "scalar",
        "gap_count": "scalar",
        "checkpoint_sequence": "scalar",
        "store_bytes": "scalar",
        "stop_reason": "scalar",
    },
    "BookApplyResult": {
        "status": "scalar",
        "error_codes": "scalar",
        "asset_id": "scalar",
        "ready": "scalar",
        "gap_open": "scalar",
        "applied": "scalar",
    },
    "BookStateTransition": {
        "asset_id": "scalar",
        "from_state": "scalar",
        "to_state": "scalar",
        "reason": "scalar",
    },
    "BookFramePlan": {
        "observations": "scan",
        "transitions": "scan",
        "state_json": "scan",
    },
    "SubscriptionUpdate": {
        "operation": "scalar",
        "asset_ids": "scalar",
    },
    "SubscriptionControlResult": {
        "status": "scalar",
        "error_codes": "scalar",
        "accepted": "scalar",
        "queued": "scalar",
    },
    "PublicPageResult": {
        "status": "scalar",
        "error_codes": "scalar",
        "attempts": "raw_evidence",
        "successful_attempt_index": "scalar",
    },
    "PitPromotionResult": {
        "is_valid": "scalar",
        "status": "scalar",
        "error_codes": "scalar",
        "source_snapshot_result": "scan",
        "observation_result": "scan",
    },
    "Checkpoint": {
        "sequence": "scalar",
        "history_sequence": "scalar",
        "checkpoint_key": "scalar",
        "value_json": "scan",
        "value_sha256": "scalar",
        "previous_sha256": "scalar",
        "state": "scalar",
    },
}

# Tokens that must never appear in a sanitized diagnostic surface.
_FORBIDDEN_ECHO_RE = re.compile(
    r"https?://|wss?://|[A-Za-z]:[\\/]|(?:^|[\s\"'])/[A-Za-z0-9._/-]+|"
    r"Traceback|Exception|Authorization|Bearer |api[_-]?key",
    re.IGNORECASE,
)


def scan_no_echo(value: object) -> bool:
    """Return True when a sanitized value carries no forbidden echo content."""
    if value is None or isinstance(value, (bool, int)):
        return True
    if isinstance(value, str):
        return _FORBIDDEN_ECHO_RE.search(value) is None
    if isinstance(value, (list, tuple)):
        return all(scan_no_echo(item) for item in value)
    if isinstance(value, Mapping):
        return all(
            isinstance(key, str) and scan_no_echo(key) and scan_no_echo(item)
            for key, item in value.items()
        )
    return False


# ---------------------------------------------------------------------------
# Point-in-time promotion adapter.
# ---------------------------------------------------------------------------

_SOURCE_ID_BY_KIND = {
    "WS": "source:polymarket:market-ws",
    "DATA": "source:polymarket:data-api",
    "GAMMA": "source:polymarket:gamma",
    "CLOB": "source:polymarket:clob",
    "POLYGON": "source:polymarket:polygon",
}
_MARKET_STATUS_VALUES = ("ACTIVE", "INACTIVE", "CLOSED", "RESOLVED")


def _reject(code: str) -> PitPromotionResult:
    return PitPromotionResult(
        is_valid=False,
        status="REJECTED",
        error_codes=(code,),
        source_snapshot_result=None,
        observation_result=None,
    )


def _payload_of(observation: NormalizedObservation) -> dict[str, object]:
    return json.loads(observation.canonical_payload_json)


def build_point_in_time_observation(
    raw: RawEnvelope,
    observation: NormalizedObservation,
    *,
    ingestion_batch_id: str,
    snapshot_id: str,
    configuration: NormalizedObservation | None = None,
    market_context: NormalizedObservation | None = None,
) -> PitPromotionResult:
    """Promote one accepted supported observation through the existing PIT builder."""
    eligibility = _pit_eligibility(observation, configuration, market_context)
    if eligibility is None:
        return _reject("PIT_PROMOTION_FORBIDDEN")
    observation_kind, token_id, event_id, condition_id, pit_payload = eligibility

    source_id = _SOURCE_ID_BY_KIND.get(observation.source_kind)
    if source_id is None:
        return _reject("PIT_PROMOTION_FORBIDDEN")

    source_input = {
        "schema_id": "point-in-time-market-research-record",
        "schema_version": "1.0.0",
        "record_family": "SOURCE_SNAPSHOT",
        "snapshot_id": snapshot_id,
        "ingestion_batch_id": ingestion_batch_id,
        "event_time": None,
        "observed_time": raw.received_at,
        "ingestion_time": raw.received_at,
        "lifecycle_state": "RAW_CAPTURED",
        "classification": "PRIMARY_ASSERTION",
        "lineage_parent_ids": [],
        "supersedes_record_version_id": None,
        "source_id": source_id,
        "source_type": "POLYMARKET_PUBLIC_API",
        "source_reference": raw.source_id,
        "media_type": raw.media_type,
        "raw_content_sha256": raw.raw_sha256,
        "byte_length": raw.byte_length,
        "retrieval_method": "PUBLIC_NETWORK_CAPTURE",
        "retrieval_version": RETRIEVAL_VERSION,
        "upstream_revision": None,
        "prior_source_snapshot_id": None,
        "access_classification": "PUBLIC",
        "normalizer_version": "wp169-normalizer:1.0.0",
        "validator_version": VALIDATOR_VERSION,
        "parameter_set_id": PARAMETER_SET_ID,
        "human_review_required": False,
        "canonical_payload": {
            "raw_id": raw.raw_id,
            "source_kind": observation.source_kind,
            "source_id": raw.source_id,
            "source_cursor": raw.source_cursor,
        },
    }
    source_result = build_source_snapshot(source_input)
    if not source_result.is_valid or source_result.record is None:
        return PitPromotionResult(
            is_valid=False,
            status="REJECTED",
            error_codes=("PIT_BUILD_INVALID",),
            source_snapshot_result=source_result,
            observation_result=None,
        )

    source_snapshot_id = source_result.record.envelope.source_snapshot_id
    source_assertion_id = observation.observation_id[len("markettruth:observation:"):]
    observation_input = {
        "schema_id": "point-in-time-market-research-record",
        "schema_version": "1.0.0",
        "record_family": "MARKET_OBSERVATION",
        "observation_kind": observation_kind,
        "platform_id": "platform:polymarket",
        "event_id": "event:polymarket:" + event_id,
        "market_id": "market:polymarket:" + condition_id,
        "token_id": ("token:polymarket:" + token_id) if token_id is not None else None,
        "source_id": source_id,
        "source_snapshot_id": source_snapshot_id,
        "source_assertion_id": source_assertion_id,
        "snapshot_id": snapshot_id,
        "ingestion_batch_id": ingestion_batch_id,
        "event_time": observation.event_time,
        "observed_time": observation.received_at,
        "ingestion_time": observation.received_at,
        "lifecycle_state": "NORMALIZED_ACCEPTED",
        "classification": "PRIMARY_ASSERTION",
        "lineage_parent_ids": [],
        "supersedes_record_version_id": None,
        "normalizer_version": "wp169-normalizer:1.0.0",
        "validator_version": VALIDATOR_VERSION,
        "parameter_set_id": PARAMETER_SET_ID,
        "human_review_required": False,
        "canonical_payload": pit_payload,
    }
    observation_result = build_market_observation(observation_input)
    if not observation_result.is_valid or observation_result.record is None:
        return PitPromotionResult(
            is_valid=False,
            status="REJECTED",
            error_codes=("PIT_BUILD_INVALID",),
            source_snapshot_result=source_result,
            observation_result=observation_result,
        )
    return PitPromotionResult(
        is_valid=True,
        status="ACCEPTED",
        error_codes=(),
        source_snapshot_result=source_result,
        observation_result=observation_result,
    )


def _market_status(payload: Mapping[str, object], event_kind: str) -> str | None:
    if event_kind == "market_resolved":
        return "RESOLVED"
    uma = payload.get("umaResolutionStatus")
    if isinstance(uma, str) and uma.lower() == "resolved":
        return "RESOLVED"
    if payload.get("automaticallyResolved") is True:
        return "RESOLVED"
    if payload.get("closed") is True:
        return "CLOSED"
    if payload.get("active") is True and payload.get("acceptingOrders") is True:
        return "ACTIVE"
    return "INACTIVE"


def _metadata_from(observation: NormalizedObservation) -> tuple[str, str, str, dict[str, object]] | None:
    """Return (event_id, condition_id, market_status, pit_payload) for metadata, else None."""
    if observation.status != "ACCEPTED":
        return None
    payload = _payload_of(observation)
    if observation.event_kind not in ("new_market", "market_resolved", "dynamic_config"):
        return None
    condition_id = payload.get("condition_id") or observation.market_id
    question = payload.get("question")
    outcomes = payload.get("outcomes")
    event_id = observation.event_id
    if observation.event_kind == "new_market":
        if _canonical_event_id(event_id) is None:
            return None
    elif observation.event_kind == "market_resolved":
        event_id = None
    else:  # dynamic_config Gamma market: event_id derived from a singleton events[].
        payload_event_id = payload.get("event_id")
        event_id = payload_event_id if isinstance(payload_event_id, str) else None
    market_status = _market_status(payload, observation.event_kind)
    if (
        not isinstance(condition_id, str)
        or not _CONDITION_RE.fullmatch(condition_id)
        or not isinstance(question, str)
        or not question
        or not isinstance(outcomes, list)
        or not outcomes
        or any(not isinstance(item, str) for item in outcomes)
        or market_status is None
    ):
        return None
    if event_id is None:
        return None
    return (
        event_id,
        condition_id,
        market_status,
        {
            "question_text": question,
            "market_status": market_status,
            "outcome_labels": list(outcomes),
        },
    )


def _pit_eligibility(
    observation: NormalizedObservation,
    configuration: NormalizedObservation | None,
    market_context: NormalizedObservation | None,
) -> tuple[str, str | None, str, str, dict[str, object]] | None:
    """Return (observation_kind, token_id, event_id, condition_id, payload) or None."""
    if observation.status != "ACCEPTED":
        return None

    # MARKET_METADATA
    if observation.event_kind in ("new_market", "market_resolved"):
        context_meta = None
        if market_context is not None:
            context_meta = _metadata_from(market_context)
        self_meta = _metadata_from(observation)
        if observation.event_kind == "market_resolved":
            if context_meta is None:
                return None
            # market_resolved has no event id of its own and requires an as-of, market-id-
            # matching context whose token list contains the candidate asset when present --
            # the same guards the book/trade paths enforce via _resolve_context. A context
            # received after the candidate is not-as-of and rejects.
            if (
                not is_rfc3339_micros(market_context.received_at)
                or market_context.received_at > observation.received_at
            ):
                return None
            event_id, condition_id, _status, payload = context_meta
            candidate_condition = observation.market_id
            if candidate_condition is None:
                candidate_payload_condition = _payload_of(observation).get("condition_id")
                candidate_condition = (
                    candidate_payload_condition
                    if isinstance(candidate_payload_condition, str)
                    else None
                )
            if candidate_condition is not None and condition_id != candidate_condition:
                return None
            if observation.asset_id is not None:
                ctx_tokens = _decode_token_list(_payload_of(market_context).get("clobTokenIds"))
                if isinstance(ctx_tokens, list) and observation.asset_id not in ctx_tokens:
                    return None
            return ("MARKET_METADATA", None, event_id, condition_id, payload)
        if self_meta is None:
            return None
        event_id, condition_id, _status, payload = self_meta
        return ("MARKET_METADATA", None, event_id, condition_id, payload)

    payload = _payload_of(observation)

    # ORDER_BOOK requires accepted dynamic_config for same asset, as-of.
    if observation.event_kind == "book":
        if configuration is None or configuration.status != "ACCEPTED":
            return None
        if configuration.event_kind != "dynamic_config" or configuration.asset_id != observation.asset_id:
            return None
        if not is_rfc3339_micros(configuration.received_at) or configuration.received_at > observation.received_at:
            return None
        config_payload = _payload_of(configuration)
        tick = canonical_decimal(config_payload.get("tick_size"))
        mos = canonical_decimal(config_payload.get("min_order_size"))
        if tick is None or mos is None:
            return None
        context = _resolve_context(observation, market_context)
        if context is None:
            return None
        event_id, condition_id, token_id = context
        bids = payload.get("bids")
        asks = payload.get("asks")
        if not isinstance(bids, list) or not isinstance(asks, list):
            return None
        return (
            "ORDER_BOOK",
            token_id,
            event_id,
            condition_id,
            {
                "bids": bids,
                "asks": asks,
                "tick_size": tick,
                "minimum_order_size": mos,
            },
        )

    # PUBLIC_TRADE
    is_trade = observation.event_kind in ("last_trade_price", "trade") or (
        observation.event_kind == "activity" and payload.get("type") == "TRADE"
    )
    if is_trade:
        price = canonical_decimal(payload.get("price"))
        size = canonical_decimal(payload.get("size"))
        side = payload.get("side")
        side_map = {"BUY": "BUY_OBSERVED", "SELL": "SELL_OBSERVED"}
        tx = payload.get("transaction_hash") or payload.get("transactionHash")
        if price is None or size is None or side not in side_map or not isinstance(tx, str) or not tx:
            return None
        context = _resolve_context(observation, market_context)
        if context is None:
            return None
        event_id, condition_id, token_id = context
        if token_id is None:
            return None
        return (
            "PUBLIC_TRADE",
            token_id,
            event_id,
            condition_id,
            {
                "price": price,
                "size": size,
                "side_observed": side_map[side],
                "transaction_reference": tx,
            },
        )

    return None


def _resolve_context(
    observation: NormalizedObservation,
    market_context: NormalizedObservation | None,
) -> tuple[str, str, str | None] | None:
    """Resolve (event_id, condition_id, token_id) from the observation or context."""
    token_id = observation.asset_id
    condition_id = observation.market_id
    if market_context is not None:
        context_meta = _metadata_from(market_context)
        if context_meta is None:
            return None
        ctx_event_id, ctx_condition, _status, _payload = context_meta
        if not is_rfc3339_micros(market_context.received_at) or market_context.received_at > observation.received_at:
            return None
        # context token list must contain the candidate asset when one exists. Gamma
        # returns clobTokenIds either as a decoded array or as a JSON-array STRING; a
        # string must be decoded before the containment check so it is not bypassed.
        ctx_payload = _payload_of(market_context)
        ctx_tokens = _decode_token_list(ctx_payload.get("clobTokenIds"))
        if token_id is not None and isinstance(ctx_tokens, list) and token_id not in ctx_tokens:
            return None
        if condition_id is not None and ctx_condition != condition_id:
            return None
        condition_id = ctx_condition
        event_id = ctx_event_id
    else:
        event_id = observation.event_id
    if event_id is None or not isinstance(condition_id, str) or not _CONDITION_RE.fullmatch(condition_id):
        return None
    return (event_id, condition_id, token_id)
