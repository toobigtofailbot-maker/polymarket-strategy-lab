"""Bounded real/public Polymarket initial point-in-time population coordinator.

This module performs the FIRST bounded real/public Polymarket population into the
already-merged point-in-time research foundation:

* WP156 immutable validated records,
* WP162 validated-batch -> WP160 reference -> WP161 manifest registration,
* WP163 durable local SQLite record store.

It defaults to zero network activity. When ``allow_network=True`` it performs
only the already-existing public GET-only Polymarket reads (Gamma ``GET /markets``
and optional CLOB ``GET /book``) through the existing GET-only public client, and
consults the existing conservative local polling guard before every request. The
public responses are normalized into immutable WP156 ``MarketObservationRecord``
objects, the complete batch is validated before persistence, records are
persisted through WP163, and the exact validated batch is registered through
WP162 into WP161.

This module is an INITIAL SEED only. It requires an empty WP163 record store and
never invents cross-run lineage/provenance. It has no scheduler, retry, sleep,
backoff, credential, authenticated, trading, or execution authority.

It NEVER imports a direct network library, a credential/wallet module, an order or
execution module, ``os.environ``, ``subprocess``, or the historical WP10 JSONL
snapshot writer. Its only network authority is the existing GET-only public client
gated by the existing local rate-limit guard. Every result fails closed: an
invalid result carries only a fixed status and bounded closed error codes, never a
path, URL, raw response, question text, source payload, record repr, exception
text, or credential. Only ordinary ``Exception`` is ever contained; ``BaseException``
always escapes.
"""

from __future__ import annotations

import datetime
import json
from dataclasses import dataclass

from ..polymarket.polling_policy import default_polling_policy, validate_polling_policy
from ..polymarket.public_client import PolymarketPublicClient
from ..polymarket.rate_limit_guard import RateLimitGuard
from .dataset_persistence_adapter import persist_validated_record_batch_snapshot
from .manifest_store import load_and_verify_manifest_store
from .record_store import (
    append_point_in_time_records,
    load_and_verify_point_in_time_record_store,
)
from .records import (
    MarketObservationRecord,
    SUPPORTED_SCHEMA_ID,
    SUPPORTED_SCHEMA_VERSION,
    build_market_observation,
    canonical_json_bytes,
    sha256_hex,
    validate_record_batch,
)


# ── Locked labels, posture, statuses, and error precedence (WP164) ────────────

POLYMARKET_PUBLIC_POPULATION_LABEL = (
    "POLYMARKET_REAL_PUBLIC_INITIAL_POINT_IN_TIME_POPULATION"
)
POLYMARKET_PUBLIC_POPULATION_POSTURE = (
    "EXPLICIT_NETWORK_GET_ONLY_BOUNDED_INITIAL_SEED_NO_TRADING_AUTHORITY"
)

POLYMARKET_PUBLIC_POPULATION_STATUSES = (
    "POPULATION_DRY_RUN",
    "POPULATION_PERSISTED_AND_REGISTERED",
    "POPULATION_ALREADY_REGISTERED",
    "POPULATION_RECORDS_PERSISTED_REGISTRATION_FAILED",
    "POPULATION_RECOVERED_REGISTRATION",
    "POPULATION_REJECTED",
)

POLYMARKET_PUBLIC_POPULATION_ERROR_CODES = (
    "POPULATION_INPUT_INVALID",
    "POPULATION_RECORD_STORE_INVALID",
    "POPULATION_MANIFEST_STORE_INVALID",
    "POPULATION_RECORD_STORE_NOT_EMPTY",
    "POPULATION_POLICY_INVALID",
    "POPULATION_GUARD_DENIED",
    "POPULATION_FETCH_FAILED",
    "POPULATION_RESPONSE_INVALID",
    "POPULATION_BUILD_FAILED",
    "POPULATION_BATCH_INVALID",
    "POPULATION_RECORD_APPEND_FAILED",
    "POPULATION_REGISTRATION_FAILED",
    "POPULATION_RECOVERY_INVALID",
    "POPULATION_UNEXPECTED_ERROR",
)

_ERROR_ORDER = {
    code: index for index, code in enumerate(POLYMARKET_PUBLIC_POPULATION_ERROR_CODES)
}

# Fixed public Polymarket identifiers for this bounded package.
_PLATFORM_ID = "platform:polymarket"
_GAMMA_SOURCE_ID = "source:polymarket:gamma-markets"
_CLOB_SOURCE_ID = "source:polymarket:clob-book"
_GAMMA_ENDPOINT_KEY = "gamma_markets"
_CLOB_ENDPOINT_KEY = "clob_book"

# Bounds mirrored from the config field grammar (the authoritative WP16 polling
# policy min values apply on top of these).
_MAX_MARKETS_LIMIT = 25
_MAX_ORDER_BOOKS_LIMIT = 20
_MAX_SCALAR = 256
_MAX_RECOVERY_RECORDS = 45

# Exact WP164 canonical payload key sets, re-proved during offline recovery.
_GAMMA_PAYLOAD_KEYS = frozenset(
    {
        "question_text",
        "market_status",
        "outcome_labels",
        "condition_id",
        "token_ids",
        "resolution_date",
        "category",
        "raw_field_names",
    }
)
_CLOB_PAYLOAD_KEYS = frozenset(
    {
        "bids",
        "asks",
        "tick_size",
        "minimum_order_size",
        "clob_timestamp",
        "book_hash",
        "last_trade_price",
        "raw_field_names",
    }
)


# ── Public immutable config and result ────────────────────────────────────────


@dataclass(frozen=True)
class PolymarketPublicPopulationConfig:
    manifest_id: str
    parameter_set_id: str
    normalizer_version: str
    validator_version: str
    markets_limit: int = 3
    order_books_limit: int = 0
    allow_network: bool = False


@dataclass(frozen=True)
class PolymarketPublicPopulationResult:
    is_valid: bool
    status: str
    error_codes: tuple[str, ...]
    record_store_error_codes: tuple[str, ...]
    registration_error_codes: tuple[str, ...]
    warning_codes: tuple[str, ...]
    snapshot_id: str | None
    captured_at_utc: str | None
    requested_markets_limit: int
    bounded_markets_limit: int
    requested_order_books_limit: int
    bounded_order_books_limit: int
    fetched_market_count: int
    fetched_order_book_count: int
    built_record_count: int
    inserted_record_count: int
    dataset_snapshot_reference_id: str | None
    manifest_entry_id: str | None
    record_store_status: str | None
    registration_status: str | None
    network_used: bool
    recovery_required: bool
    advisory_only: bool
    no_execution_authority: bool


# ── Internal control-flow rejection ───────────────────────────────────────────


class _PopulationReject(Exception):
    """Carry only a closed WP164 error code out of a bounded helper."""

    def __init__(self, code: str):
        self.code = code


def _order(codes: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(
        sorted(set(codes), key=lambda code: _ERROR_ORDER.get(code, len(_ERROR_ORDER)))
    )


def _result(
    *,
    is_valid: bool,
    status: str,
    error_codes: tuple[str, ...] = (),
    record_store_error_codes: tuple[str, ...] = (),
    registration_error_codes: tuple[str, ...] = (),
    snapshot_id: str | None = None,
    captured_at_utc: str | None = None,
    requested_markets_limit: int = 0,
    bounded_markets_limit: int = 0,
    requested_order_books_limit: int = 0,
    bounded_order_books_limit: int = 0,
    fetched_market_count: int = 0,
    fetched_order_book_count: int = 0,
    built_record_count: int = 0,
    inserted_record_count: int = 0,
    dataset_snapshot_reference_id: str | None = None,
    manifest_entry_id: str | None = None,
    record_store_status: str | None = None,
    registration_status: str | None = None,
    network_used: bool = False,
    recovery_required: bool = False,
) -> PolymarketPublicPopulationResult:
    return PolymarketPublicPopulationResult(
        is_valid=is_valid,
        status=status,
        error_codes=_order(error_codes),
        record_store_error_codes=tuple(record_store_error_codes),
        registration_error_codes=tuple(registration_error_codes),
        warning_codes=(),
        snapshot_id=snapshot_id,
        captured_at_utc=captured_at_utc,
        requested_markets_limit=requested_markets_limit,
        bounded_markets_limit=bounded_markets_limit,
        requested_order_books_limit=requested_order_books_limit,
        bounded_order_books_limit=bounded_order_books_limit,
        fetched_market_count=fetched_market_count,
        fetched_order_book_count=fetched_order_book_count,
        built_record_count=built_record_count,
        inserted_record_count=inserted_record_count,
        dataset_snapshot_reference_id=dataset_snapshot_reference_id,
        manifest_entry_id=manifest_entry_id,
        record_store_status=record_store_status,
        registration_status=registration_status,
        network_used=network_used,
        recovery_required=recovery_required,
        advisory_only=True,
        no_execution_authority=True,
    )


def _rejected(
    code: str,
    *,
    requested_markets_limit: int = 0,
    requested_order_books_limit: int = 0,
) -> PolymarketPublicPopulationResult:
    return _result(
        is_valid=False,
        status="POPULATION_REJECTED",
        error_codes=(code,),
        requested_markets_limit=requested_markets_limit,
        requested_order_books_limit=requested_order_books_limit,
    )


# ── Config / public input boundary (R001-R004) ────────────────────────────────


def _valid_scalar(value: object) -> bool:
    return type(value) is str and 0 < len(value) <= _MAX_SCALAR and value == value.strip()


def _validate_config(config: object) -> None:
    if type(config) is not PolymarketPublicPopulationConfig:
        raise _PopulationReject("POPULATION_INPUT_INVALID")
    if type(config.allow_network) is not bool:
        raise _PopulationReject("POPULATION_INPUT_INVALID")
    if type(config.markets_limit) is not int or type(config.markets_limit) is bool:
        raise _PopulationReject("POPULATION_INPUT_INVALID")
    if not (0 <= config.markets_limit <= _MAX_MARKETS_LIMIT):
        raise _PopulationReject("POPULATION_INPUT_INVALID")
    if (
        type(config.order_books_limit) is not int
        or type(config.order_books_limit) is bool
    ):
        raise _PopulationReject("POPULATION_INPUT_INVALID")
    if not (0 <= config.order_books_limit <= _MAX_ORDER_BOOKS_LIMIT):
        raise _PopulationReject("POPULATION_INPUT_INVALID")
    for value in (
        config.manifest_id,
        config.parameter_set_id,
        config.normalizer_version,
        config.validator_version,
    ):
        if not _valid_scalar(value):
            raise _PopulationReject("POPULATION_INPUT_INVALID")


# ── Store preconditions (R005-R008) ───────────────────────────────────────────


def _verify_empty_record_store(record_store_path: object) -> None:
    try:
        loaded = load_and_verify_point_in_time_record_store(record_store_path)
    except Exception:
        raise _PopulationReject("POPULATION_RECORD_STORE_INVALID")
    if (
        not loaded.is_valid
        or loaded.status != "RECORD_STORE_LOADED_VERIFIED"
        or loaded.snapshot is None
    ):
        raise _PopulationReject("POPULATION_RECORD_STORE_INVALID")
    if loaded.snapshot.records:
        raise _PopulationReject("POPULATION_RECORD_STORE_NOT_EMPTY")


def _verify_manifest_store(manifest_store_path: object) -> None:
    try:
        loaded = load_and_verify_manifest_store(manifest_store_path)
    except Exception:
        raise _PopulationReject("POPULATION_MANIFEST_STORE_INVALID")
    if (
        not loaded.is_valid
        or loaded.status != "STORE_LOADED_VERIFIED"
        or loaded.snapshot is None
    ):
        raise _PopulationReject("POPULATION_MANIFEST_STORE_INVALID")


# ── Policy authority and bounded limits (R010-R011) ───────────────────────────


def _bounded_limits(config: PolymarketPublicPopulationConfig) -> tuple[int, int]:
    try:
        policy = default_polling_policy()
        validation = validate_polling_policy(policy)
    except Exception:
        raise _PopulationReject("POPULATION_POLICY_INVALID")
    if not validation.passed:
        raise _PopulationReject("POPULATION_POLICY_INVALID")
    gamma_policy = policy.endpoints.get(_GAMMA_ENDPOINT_KEY)
    clob_policy = policy.endpoints.get(_CLOB_ENDPOINT_KEY)
    if gamma_policy is None or clob_policy is None:
        raise _PopulationReject("POPULATION_POLICY_INVALID")
    bounded_markets = min(config.markets_limit, gamma_policy.max_markets_per_run)
    bounded_books = min(config.order_books_limit, clob_policy.max_tokens_per_run)
    return bounded_markets, bounded_books


def _build_guard(guard: object | None) -> RateLimitGuard:
    if guard is not None:
        return guard  # type: ignore[return-value]
    return RateLimitGuard(default_polling_policy().endpoint_budgets())


# ── Guarded GET-only reads (R012-R018) ────────────────────────────────────────


def _consult_guard(guard: RateLimitGuard, endpoint_key: str, now_provider) -> None:
    """Consult the existing local guard, which remains the request authority.

    When no ``now_provider`` is injected the guard uses its native monotonic
    clock; back-to-back requests inside the conservative interval are denied.
    A denial never sleeps, waits, or retries.
    """

    try:
        if now_provider is None:
            decision = guard.record_allowed(endpoint_key)
        else:
            decision = guard.record_allowed(endpoint_key, now=float(now_provider()))
    except Exception:
        raise _PopulationReject("POPULATION_GUARD_DENIED")
    if not getattr(decision, "allowed", False):
        raise _PopulationReject("POPULATION_GUARD_DENIED")


def _require_get_2xx(result: object) -> None:
    request_info = getattr(result, "request_info", None)
    if request_info is None:
        raise _PopulationReject("POPULATION_RESPONSE_INVALID")
    if getattr(request_info, "method", None) != "GET":
        raise _PopulationReject("POPULATION_RESPONSE_INVALID")
    status_code = getattr(request_info, "status_code", None)
    if type(status_code) is not int or not (200 <= status_code < 300):
        raise _PopulationReject("POPULATION_RESPONSE_INVALID")


def _get_markets(
    client: PolymarketPublicClient,
    bounded_markets_limit: int,
) -> list[dict]:
    # The caller consults the guard immediately before this GET so network use is
    # tracked truthfully; this helper is a pure GET plus response boundary.
    try:
        result = client.get_markets(limit=bounded_markets_limit)
    except _PopulationReject:
        raise
    except Exception:
        raise _PopulationReject("POPULATION_FETCH_FAILED")
    _require_get_2xx(result)
    data = getattr(result, "data", None)
    if type(data) is not list:
        raise _PopulationReject("POPULATION_RESPONSE_INVALID")
    if not (1 <= len(data) <= bounded_markets_limit):
        raise _PopulationReject("POPULATION_RESPONSE_INVALID")
    for item in data:
        if type(item) is not dict:
            raise _PopulationReject("POPULATION_RESPONSE_INVALID")
    return data


def _get_order_book(
    client: PolymarketPublicClient,
    raw_token_id: str,
) -> dict:
    # The caller consults the guard immediately before this GET.
    try:
        result = client.get_order_book_snapshot(raw_token_id)
    except _PopulationReject:
        raise
    except Exception:
        raise _PopulationReject("POPULATION_FETCH_FAILED")
    _require_get_2xx(result)
    data = getattr(result, "data", None)
    if type(data) is not dict:
        raise _PopulationReject("POPULATION_RESPONSE_INVALID")
    asset_id = data.get("asset_id")
    if asset_id is not None and str(asset_id) != raw_token_id:
        raise _PopulationReject("POPULATION_RESPONSE_INVALID")
    return data


# ── Normalization into WP156 records (R021-R024) ──────────────────────────────


def _optional_str(value: object) -> str | None:
    return value if type(value) is str else None


def _parse_markets(raw_items: list[dict]) -> list[tuple[str, str, dict]]:
    """Return ``(namespaced_market_id, raw_gamma_id, normalized)`` for each market.

    Every selected item is parsed through the public market parser; a malformed
    selected market rejects the whole run rather than being silently skipped.
    Duplicate raw Gamma market IDs are rejected.
    """

    parsed: list[tuple[str, str, dict]] = []
    seen_gamma_ids: set[str] = set()
    for raw_item in raw_items:
        try:
            summary = PolymarketPublicClient.parse_market_summary(raw_item)
        except _PopulationReject:
            raise
        except Exception:
            raise _PopulationReject("POPULATION_RESPONSE_INVALID")
        raw_gamma_id = summary.market_id
        if not raw_gamma_id:
            raise _PopulationReject("POPULATION_RESPONSE_INVALID")
        if raw_gamma_id in seen_gamma_ids:
            raise _PopulationReject("POPULATION_RESPONSE_INVALID")
        seen_gamma_ids.add(raw_gamma_id)
        market_id = "market:polymarket:" + raw_gamma_id
        condition_id = summary.condition_id.strip() if summary.condition_id else ""
        if condition_id:
            event_id = "event:polymarket:" + condition_id
        else:
            event_id = "event:polymarket:market-" + raw_gamma_id
        payload = {
            "question_text": summary.question,
            "market_status": summary.market_status,
            "outcome_labels": list(summary.outcome_labels),
            "condition_id": summary.condition_id,
            "token_ids": [str(token) for token in summary.token_ids],
            "resolution_date": _optional_str(summary.resolution_date),
            "category": _optional_str(summary.category),
            "raw_field_names": sorted(str(key) for key in raw_item.keys()),
        }
        normalized = {
            "market_id": market_id,
            "event_id": event_id,
            "raw_gamma_id": raw_gamma_id,
            "raw_token_ids": [str(token) for token in summary.token_ids],
            "payload": payload,
        }
        parsed.append((market_id, raw_gamma_id, normalized))
    parsed.sort(key=lambda entry: entry[0])
    return parsed


def _content_id(prefix: str, preimage: dict) -> str:
    return prefix + sha256_hex(canonical_json_bytes(preimage))


def _build_gamma_record(
    normalized: dict,
    *,
    snapshot_id: str,
    ingestion_batch_id: str,
    captured_at_utc: str,
    config: PolymarketPublicPopulationConfig,
) -> MarketObservationRecord:
    market_id = normalized["market_id"]
    event_id = normalized["event_id"]
    payload = normalized["payload"]
    source_snapshot_id = _content_id(
        "srcsnap:sha256:",
        {
            "source_id": _GAMMA_SOURCE_ID,
            "market_id": market_id,
            "snapshot_id": snapshot_id,
            "canonical_payload": payload,
        },
    )
    source_assertion_id = _content_id(
        "assertion:sha256:",
        {
            "source_snapshot_id": source_snapshot_id,
            "observation_kind": "MARKET_METADATA",
            "market_id": market_id,
            "event_id": event_id,
            "token_id": None,
        },
    )
    input_record = {
        "schema_id": SUPPORTED_SCHEMA_ID,
        "schema_version": SUPPORTED_SCHEMA_VERSION,
        "record_family": "MARKET_OBSERVATION",
        "observation_kind": "MARKET_METADATA",
        "platform_id": _PLATFORM_ID,
        "event_id": event_id,
        "market_id": market_id,
        "token_id": None,
        "source_id": _GAMMA_SOURCE_ID,
        "source_assertion_id": source_assertion_id,
        "source_snapshot_id": source_snapshot_id,
        "snapshot_id": snapshot_id,
        "ingestion_batch_id": ingestion_batch_id,
        "event_time": None,
        "observed_time": captured_at_utc,
        "ingestion_time": captured_at_utc,
        "lifecycle_state": "NORMALIZED_ACCEPTED",
        "classification": "PRIMARY_ASSERTION",
        "lineage_parent_ids": [],
        "supersedes_record_version_id": None,
        "normalizer_version": config.normalizer_version,
        "validator_version": config.validator_version,
        "parameter_set_id": config.parameter_set_id,
        "human_review_required": False,
        "canonical_payload": payload,
    }
    return _build_or_reject(input_record)


def _normalize_order_book(raw_book: dict, raw_token_id: str) -> dict:
    for side in ("bids", "asks"):
        if type(raw_book.get(side)) is not list:
            raise _PopulationReject("POPULATION_RESPONSE_INVALID")
    tick_size = raw_book.get("tick_size")
    min_order_size = raw_book.get("min_order_size")
    if type(tick_size) is not str or type(min_order_size) is not str:
        raise _PopulationReject("POPULATION_RESPONSE_INVALID")

    def _levels(side: str) -> list[dict]:
        levels: list[dict] = []
        for level in raw_book.get(side, []):
            if type(level) is not dict or set(level) != {"price", "size"}:
                raise _PopulationReject("POPULATION_RESPONSE_INVALID")
            price = level.get("price")
            size = level.get("size")
            if type(price) is not str or type(size) is not str:
                raise _PopulationReject("POPULATION_RESPONSE_INVALID")
            levels.append({"price": price, "size": size})
        return levels

    return {
        "bids": _levels("bids"),
        "asks": _levels("asks"),
        "tick_size": tick_size,
        "minimum_order_size": min_order_size,
        "clob_timestamp": _optional_str(raw_book.get("timestamp")),
        "book_hash": _optional_str(raw_book.get("hash")),
        "last_trade_price": _optional_str(raw_book.get("last_trade_price")),
        "raw_field_names": sorted(str(key) for key in raw_book.keys()),
    }


def _build_order_book_record(
    parent: dict,
    raw_token_id: str,
    payload: dict,
    *,
    snapshot_id: str,
    ingestion_batch_id: str,
    captured_at_utc: str,
    config: PolymarketPublicPopulationConfig,
) -> MarketObservationRecord:
    market_id = parent["market_id"]
    event_id = parent["event_id"]
    token_id = "token:polymarket:" + raw_token_id
    source_snapshot_id = _content_id(
        "srcsnap:sha256:",
        {
            "source_id": _CLOB_SOURCE_ID,
            "market_id": market_id,
            "token_id": token_id,
            "snapshot_id": snapshot_id,
            "canonical_payload": payload,
        },
    )
    source_assertion_id = _content_id(
        "assertion:sha256:",
        {
            "source_snapshot_id": source_snapshot_id,
            "observation_kind": "ORDER_BOOK",
            "market_id": market_id,
            "event_id": event_id,
            "token_id": token_id,
        },
    )
    input_record = {
        "schema_id": SUPPORTED_SCHEMA_ID,
        "schema_version": SUPPORTED_SCHEMA_VERSION,
        "record_family": "MARKET_OBSERVATION",
        "observation_kind": "ORDER_BOOK",
        "platform_id": _PLATFORM_ID,
        "event_id": event_id,
        "market_id": market_id,
        "token_id": token_id,
        "source_id": _CLOB_SOURCE_ID,
        "source_assertion_id": source_assertion_id,
        "source_snapshot_id": source_snapshot_id,
        "snapshot_id": snapshot_id,
        "ingestion_batch_id": ingestion_batch_id,
        "event_time": None,
        "observed_time": captured_at_utc,
        "ingestion_time": captured_at_utc,
        "lifecycle_state": "NORMALIZED_ACCEPTED",
        "classification": "PRIMARY_ASSERTION",
        "lineage_parent_ids": [],
        "supersedes_record_version_id": None,
        "normalizer_version": config.normalizer_version,
        "validator_version": config.validator_version,
        "parameter_set_id": config.parameter_set_id,
        "human_review_required": False,
        "canonical_payload": payload,
    }
    return _build_or_reject(input_record)


def _build_or_reject(input_record: dict) -> MarketObservationRecord:
    try:
        built = build_market_observation(input_record)
    except _PopulationReject:
        raise
    except Exception:
        raise _PopulationReject("POPULATION_BUILD_FAILED")
    if not built.is_valid or built.record is None:
        raise _PopulationReject("POPULATION_BUILD_FAILED")
    if type(built.record) is not MarketObservationRecord:
        raise _PopulationReject("POPULATION_BUILD_FAILED")
    return built.record


# ── Deterministic token selection and run identities (R014, R019-R020) ────────


def _select_tokens(parsed_markets: list[tuple[str, str, dict]], bounded_books: int):
    """Deterministically select unique tokens and map each to a unique market.

    Any token that maps to more than one distinct market rejects the run rather
    than guessing parent authority.
    """

    token_to_market: dict[str, dict] = {}
    for _market_id, _raw_gamma_id, normalized in parsed_markets:
        for raw_token in normalized["raw_token_ids"]:
            existing = token_to_market.get(raw_token)
            if existing is not None and existing["market_id"] != normalized["market_id"]:
                raise _PopulationReject("POPULATION_RESPONSE_INVALID")
            token_to_market.setdefault(raw_token, normalized)

    ordered_tokens: list[str] = []
    seen: set[str] = set()
    for _market_id, _raw_gamma_id, normalized in parsed_markets:
        for raw_token in normalized["raw_token_ids"]:
            if raw_token and raw_token not in seen:
                seen.add(raw_token)
                ordered_tokens.append(raw_token)
    return ordered_tokens[:bounded_books], token_to_market


def _capture_time(utcnow_provider) -> str:
    try:
        value = utcnow_provider()
        if value.tzinfo is None:
            value = value.replace(tzinfo=datetime.UTC)
        value = value.astimezone(datetime.UTC)
        text = value.isoformat().replace("+00:00", "Z")
    except Exception:
        raise _PopulationReject("POPULATION_UNEXPECTED_ERROR")
    if not text.endswith("Z"):
        raise _PopulationReject("POPULATION_UNEXPECTED_ERROR")
    return text


def _run_identities(
    *,
    captured_at_utc: str,
    gamma_payload_hashes: list[str],
    clob_payload_hashes: list[str],
    config: PolymarketPublicPopulationConfig,
) -> tuple[str, str]:
    base = {
        "label": POLYMARKET_PUBLIC_POPULATION_LABEL,
        "captured_at_utc": captured_at_utc,
        "gamma_payload_sha256_ordered": list(gamma_payload_hashes),
        "clob_payload_sha256_ordered": list(clob_payload_hashes),
        "parameter_set_id": config.parameter_set_id,
        "normalizer_version": config.normalizer_version,
        "validator_version": config.validator_version,
    }
    snapshot_id = _content_id("snapshot:sha256:", dict(base, identity_kind="snapshot_id"))
    ingestion_batch_id = _content_id(
        "ingest:sha256:", dict(base, identity_kind="ingestion_batch_id")
    )
    return snapshot_id, ingestion_batch_id


# ── Batch validation, append, and registration (R025-R032) ────────────────────


def _validate_batch(records: tuple[MarketObservationRecord, ...]) -> None:
    if not records or len(records) > 256:
        raise _PopulationReject("POPULATION_BATCH_INVALID")
    try:
        batch = validate_record_batch(records)
    except _PopulationReject:
        raise
    except Exception:
        raise _PopulationReject("POPULATION_BATCH_INVALID")
    if batch.is_valid is not True:
        raise _PopulationReject("POPULATION_BATCH_INVALID")
    if batch.quarantined_record_version_ids:
        raise _PopulationReject("POPULATION_BATCH_INVALID")
    accepted = tuple(batch.accepted_record_version_ids)
    if len(accepted) != len(records) or len(set(accepted)) != len(accepted):
        raise _PopulationReject("POPULATION_BATCH_INVALID")


def _append_records(
    record_store_path: object,
    records: tuple[MarketObservationRecord, ...],
) -> tuple[str, tuple[str, ...]]:
    try:
        appended = append_point_in_time_records(record_store_path, records)
    except Exception:
        raise _AppendFailure(())
    expected = {record.envelope.record_version_id for record in records}
    if (
        not appended.is_valid
        or appended.status != "RECORD_STORE_APPEND_COMMITTED"
        or appended.snapshot is None
        or set(appended.inserted_record_version_ids) != expected
    ):
        raise _AppendFailure(tuple(appended.error_codes))
    return appended.status, tuple(sorted(expected))


class _AppendFailure(Exception):
    def __init__(self, store_error_codes: tuple[str, ...]):
        self.store_error_codes = store_error_codes


def _safe_register(
    manifest_store_path: object,
    records: tuple[MarketObservationRecord, ...],
    config: PolymarketPublicPopulationConfig,
    *,
    effective_time: str,
) -> tuple[bool, object, tuple[str, ...]]:
    """Register the validated batch, containing every ordinary failure mode.

    Returns ``(ok, registration_or_none, closed_error_codes)``. A raised
    ``Exception`` yields ``(False, None, ())`` with no echo; an invalid adapter
    result yields ``(False, result, closed_adapter_codes)``. This never raises, so
    a registration failure after a committed record append can never be reported
    as a generic unrecoverable rejection.
    """

    try:
        registration = persist_validated_record_batch_snapshot(
            manifest_store_path,
            records,
            manifest_id=config.manifest_id,
            effective_time=effective_time,
            parameter_set_id=config.parameter_set_id,
            validator_version=config.validator_version,
        )
    except Exception:
        return False, None, ()
    if registration.is_valid is not True or registration.status not in (
        "ADAPTER_PERSISTED",
        "ADAPTER_ALREADY_PERSISTED",
    ):
        return False, registration, tuple(getattr(registration, "error_codes", ()))
    return True, registration, ()


# ── Public coordinator ────────────────────────────────────────────────────────


def populate_initial_polymarket_public_data(
    record_store_path: object,
    manifest_store_path: object,
    config: object,
    *,
    client: object | None = None,
    guard: object | None = None,
    now_provider: object | None = None,
    utcnow_provider: object | None = None,
) -> PolymarketPublicPopulationResult:
    """Perform the bounded real/public initial Polymarket point-in-time seed.

    With the default ``allow_network=False`` this makes zero network calls and
    returns a valid dry-run result. It never mutates a store on any failure path
    other than the locked records-first/reference-second ordering, and every
    invalid result is bounded and echo-free.
    """

    try:
        try:
            _validate_config(config)
        except _PopulationReject as reject:
            return _rejected(reject.code)

        assert isinstance(config, PolymarketPublicPopulationConfig)
        requested_markets = config.markets_limit
        requested_books = config.order_books_limit

        try:
            _verify_empty_record_store(record_store_path)
            _verify_manifest_store(manifest_store_path)
            bounded_markets, bounded_books = _bounded_limits(config)
        except _PopulationReject as reject:
            return _rejected(
                reject.code,
                requested_markets_limit=requested_markets,
                requested_order_books_limit=requested_books,
            )

        if not config.allow_network:
            return _result(
                is_valid=True,
                status="POPULATION_DRY_RUN",
                requested_markets_limit=requested_markets,
                bounded_markets_limit=bounded_markets,
                requested_order_books_limit=requested_books,
                bounded_order_books_limit=bounded_books,
                record_store_status="RECORD_STORE_LOADED_VERIFIED",
                network_used=False,
            )

        # ``_run_network_population`` owns its own rejection handling so that
        # ``network_used`` is truthful (False until the Gamma GET is attempted).
        return _run_network_population(
            record_store_path,
            manifest_store_path,
            config,
            client=client,
            guard=guard,
            now_provider=now_provider,
            utcnow_provider=utcnow_provider,
            requested_markets=requested_markets,
            requested_books=requested_books,
            bounded_markets=bounded_markets,
            bounded_books=bounded_books,
        )
    except Exception:
        return _result(
            is_valid=False,
            status="POPULATION_REJECTED",
            error_codes=("POPULATION_UNEXPECTED_ERROR",),
        )


def _run_network_population(
    record_store_path: object,
    manifest_store_path: object,
    config: PolymarketPublicPopulationConfig,
    *,
    client: object | None,
    guard: object | None,
    now_provider: object | None,
    utcnow_provider: object | None,
    requested_markets: int,
    requested_books: int,
    bounded_markets: int,
    bounded_books: int,
) -> PolymarketPublicPopulationResult:
    limits = dict(
        requested_markets_limit=requested_markets,
        bounded_markets_limit=bounded_markets,
        requested_order_books_limit=requested_books,
        bounded_order_books_limit=bounded_books,
    )

    if bounded_markets <= 0:
        # A network population must fetch at least one market; an empty network
        # seed is rejected rather than registered. No GET is attempted.
        return _result(
            is_valid=False,
            status="POPULATION_REJECTED",
            error_codes=("POPULATION_INPUT_INVALID",),
            network_used=False,
            **limits,
        )

    rate_guard = _build_guard(guard)
    utc_now = (
        (lambda: datetime.datetime.now(datetime.UTC))
        if utcnow_provider is None
        else utcnow_provider
    )

    # ``network_used`` stays False until the Gamma GET is actually attempted, so a
    # guard denial before the first GET is reported honestly as no network use.
    network_used = False
    try:
        active_client = client
        if active_client is None:
            try:
                active_client = PolymarketPublicClient(allow_unverified_endpoints=False)
            except Exception:
                raise _PopulationReject("POPULATION_FETCH_FAILED")

        _consult_guard(rate_guard, _GAMMA_ENDPOINT_KEY, now_provider)
        network_used = True
        raw_markets = _get_markets(active_client, bounded_markets)
        fetched_market_count = len(raw_markets)
        parsed_markets = _parse_markets(raw_markets)

        selected_tokens, token_to_market = _select_tokens(parsed_markets, bounded_books)
        raw_books: list[tuple[dict, str, dict]] = []
        for raw_token in selected_tokens:
            _consult_guard(rate_guard, _CLOB_ENDPOINT_KEY, now_provider)
            parent = token_to_market[raw_token]
            raw_book = _get_order_book(active_client, raw_token)
            payload = _normalize_order_book(raw_book, raw_token)
            raw_books.append((parent, raw_token, payload))
        fetched_order_book_count = len(raw_books)

        captured_at_utc = _capture_time(utc_now)

        # Payload hashes computed in the deterministic WP164 record order so an
        # offline recovery can recompute the exact same run identities.
        gamma_sorted = sorted(parsed_markets, key=lambda entry: entry[0])
        book_sorted = sorted(
            raw_books,
            key=lambda item: (item[0]["market_id"], "token:polymarket:" + item[1]),
        )
        gamma_payload_hashes = [
            sha256_hex(canonical_json_bytes(normalized["payload"]))
            for _market_id, _raw_gamma_id, normalized in gamma_sorted
        ]
        clob_payload_hashes = [
            sha256_hex(canonical_json_bytes(payload))
            for _parent, _token, payload in book_sorted
        ]
        snapshot_id, ingestion_batch_id = _run_identities(
            captured_at_utc=captured_at_utc,
            gamma_payload_hashes=gamma_payload_hashes,
            clob_payload_hashes=clob_payload_hashes,
            config=config,
        )

        gamma_records = [
            _build_gamma_record(
                normalized,
                snapshot_id=snapshot_id,
                ingestion_batch_id=ingestion_batch_id,
                captured_at_utc=captured_at_utc,
                config=config,
            )
            for _market_id, _raw_gamma_id, normalized in parsed_markets
        ]
        book_records = [
            _build_order_book_record(
                parent,
                raw_token,
                payload,
                snapshot_id=snapshot_id,
                ingestion_batch_id=ingestion_batch_id,
                captured_at_utc=captured_at_utc,
                config=config,
            )
            for parent, raw_token, payload in raw_books
        ]

        gamma_records.sort(key=lambda record: record.market_id)
        book_records.sort(key=lambda record: (record.market_id, record.token_id or ""))
        records = tuple(gamma_records) + tuple(book_records)
        built_record_count = len(records)

        _validate_batch(records)
    except _PopulationReject as reject:
        return _result(
            is_valid=False,
            status="POPULATION_REJECTED",
            error_codes=(reject.code,),
            network_used=network_used,
            **limits,
        )

    # ── Records first (locked), then reference registration. ──────────────────
    try:
        record_store_status, inserted_ids = _append_records(record_store_path, records)
    except _AppendFailure as failure:
        return _result(
            is_valid=False,
            status="POPULATION_REJECTED",
            error_codes=("POPULATION_RECORD_APPEND_FAILED",),
            record_store_error_codes=failure.store_error_codes,
            snapshot_id=snapshot_id,
            captured_at_utc=captured_at_utc,
            fetched_market_count=fetched_market_count,
            fetched_order_book_count=fetched_order_book_count,
            built_record_count=built_record_count,
            network_used=True,
            **limits,
        )

    inserted_record_count = len(inserted_ids)

    ok, registration, registration_error_codes = _safe_register(
        manifest_store_path, records, config, effective_time=captured_at_utc
    )
    if not ok:
        # Records committed (fail-safe ordering); the immutable WP163 records are
        # never deleted. EVERY registration failure mode after a committed append
        # — invalid result, raised exception, or malformed result — reports the
        # recoverable partial status. Recovery re-registers offline with no fetch.
        return _result(
            is_valid=False,
            status="POPULATION_RECORDS_PERSISTED_REGISTRATION_FAILED",
            error_codes=("POPULATION_REGISTRATION_FAILED",),
            registration_error_codes=registration_error_codes,
            snapshot_id=snapshot_id,
            captured_at_utc=captured_at_utc,
            fetched_market_count=fetched_market_count,
            fetched_order_book_count=fetched_order_book_count,
            built_record_count=built_record_count,
            inserted_record_count=inserted_record_count,
            record_store_status=record_store_status,
            registration_status=None,
            network_used=True,
            recovery_required=True,
            **limits,
        )

    status = (
        "POPULATION_PERSISTED_AND_REGISTERED"
        if registration.status == "ADAPTER_PERSISTED"
        else "POPULATION_ALREADY_REGISTERED"
    )
    return _result(
        is_valid=True,
        status=status,
        snapshot_id=snapshot_id,
        captured_at_utc=captured_at_utc,
        fetched_market_count=fetched_market_count,
        fetched_order_book_count=fetched_order_book_count,
        built_record_count=built_record_count,
        inserted_record_count=inserted_record_count,
        dataset_snapshot_reference_id=(
            registration.dataset_reference.dataset_snapshot_reference_id
            if registration.dataset_reference is not None
            else None
        ),
        manifest_entry_id=(
            registration.manifest_entry.manifest_entry_id
            if registration.manifest_entry is not None
            else None
        ),
        record_store_status=record_store_status,
        registration_status=registration.status,
        network_used=True,
        **limits,
    )


# ── Offline registration recovery (R033-R035) ─────────────────────────────────


def recover_initial_polymarket_public_registration(
    record_store_path: object,
    manifest_store_path: object,
    config: object,
) -> PolymarketPublicPopulationResult:
    """Re-register a committed WP164 seed offline after registration failed.

    This performs ZERO network activity, never constructs a client, never writes
    records, and only re-registers a store proven to be exactly one valid
    unregistered/retryable WP164 initial seed.
    """

    try:
        try:
            _validate_config(config)
        except _PopulationReject as reject:
            return _rejected(reject.code)
        assert isinstance(config, PolymarketPublicPopulationConfig)

        try:
            records = _load_recovery_records(record_store_path)
            _verify_manifest_store(manifest_store_path)
            _verify_recovery_records(records, config)
            _prove_wp164_construction(records, config)
        except _PopulationReject as reject:
            return _result(
                is_valid=False,
                status="POPULATION_REJECTED",
                error_codes=(reject.code,),
                requested_markets_limit=config.markets_limit,
                requested_order_books_limit=config.order_books_limit,
            )

        snapshot_id = records[0].envelope.snapshot_id
        ingestion_time = records[0].envelope.ingestion_time
        ordered = _wp164_sort(records)

        _validate_batch(ordered)

        ok, registration, registration_error_codes = _safe_register(
            manifest_store_path, ordered, config, effective_time=ingestion_time
        )
        if not ok:
            return _result(
                is_valid=False,
                status="POPULATION_REJECTED",
                error_codes=("POPULATION_REGISTRATION_FAILED",),
                registration_error_codes=registration_error_codes,
                snapshot_id=snapshot_id,
                captured_at_utc=ingestion_time,
                requested_markets_limit=config.markets_limit,
                requested_order_books_limit=config.order_books_limit,
                built_record_count=len(ordered),
                record_store_status="RECORD_STORE_LOADED_VERIFIED",
            )

        status = (
            "POPULATION_RECOVERED_REGISTRATION"
            if registration.status == "ADAPTER_PERSISTED"
            else "POPULATION_ALREADY_REGISTERED"
        )
        return _result(
            is_valid=True,
            status=status,
            snapshot_id=snapshot_id,
            captured_at_utc=ingestion_time,
            requested_markets_limit=config.markets_limit,
            requested_order_books_limit=config.order_books_limit,
            built_record_count=len(ordered),
            record_store_status="RECORD_STORE_LOADED_VERIFIED",
            dataset_snapshot_reference_id=(
                registration.dataset_reference.dataset_snapshot_reference_id
                if registration.dataset_reference is not None
                else None
            ),
            manifest_entry_id=(
                registration.manifest_entry.manifest_entry_id
                if registration.manifest_entry is not None
                else None
            ),
            registration_status=registration.status,
            network_used=False,
            recovery_required=False,
        )
    except Exception:
        return _result(
            is_valid=False,
            status="POPULATION_REJECTED",
            error_codes=("POPULATION_UNEXPECTED_ERROR",),
        )


def _load_recovery_records(record_store_path: object) -> tuple[MarketObservationRecord, ...]:
    try:
        loaded = load_and_verify_point_in_time_record_store(record_store_path)
    except Exception:
        raise _PopulationReject("POPULATION_RECORD_STORE_INVALID")
    if (
        not loaded.is_valid
        or loaded.status != "RECORD_STORE_LOADED_VERIFIED"
        or loaded.snapshot is None
    ):
        raise _PopulationReject("POPULATION_RECORD_STORE_INVALID")
    records = loaded.snapshot.records
    if not records:
        raise _PopulationReject("POPULATION_RECOVERY_INVALID")
    return records


def _verify_recovery_records(
    records: tuple[object, ...], config: PolymarketPublicPopulationConfig
) -> None:
    if not (1 <= len(records) <= _MAX_RECOVERY_RECORDS):
        raise _PopulationReject("POPULATION_RECOVERY_INVALID")
    gamma_count = 0
    book_count = 0
    snapshot_ids: set[str] = set()
    ingestion_batch_ids: set[str] = set()
    observed_times: set[str] = set()
    ingestion_times: set[str] = set()
    for record in records:
        if type(record) is not MarketObservationRecord:
            raise _PopulationReject("POPULATION_RECOVERY_INVALID")
        envelope = record.envelope
        if record.platform_id != _PLATFORM_ID:
            raise _PopulationReject("POPULATION_RECOVERY_INVALID")
        if record.source_id == _GAMMA_SOURCE_ID:
            if record.observation_kind != "MARKET_METADATA":
                raise _PopulationReject("POPULATION_RECOVERY_INVALID")
            gamma_count += 1
        elif record.source_id == _CLOB_SOURCE_ID:
            if record.observation_kind != "ORDER_BOOK":
                raise _PopulationReject("POPULATION_RECOVERY_INVALID")
            book_count += 1
        else:
            raise _PopulationReject("POPULATION_RECOVERY_INVALID")
        if envelope.classification != "PRIMARY_ASSERTION":
            raise _PopulationReject("POPULATION_RECOVERY_INVALID")
        if envelope.lifecycle_state != "NORMALIZED_ACCEPTED":
            raise _PopulationReject("POPULATION_RECOVERY_INVALID")
        if envelope.lineage_parent_ids:
            raise _PopulationReject("POPULATION_RECOVERY_INVALID")
        if envelope.supersedes_record_version_id is not None:
            raise _PopulationReject("POPULATION_RECOVERY_INVALID")
        if (
            envelope.parameter_set_id != config.parameter_set_id
            or envelope.normalizer_version != config.normalizer_version
            or envelope.validator_version != config.validator_version
        ):
            raise _PopulationReject("POPULATION_RECOVERY_INVALID")
        snapshot_ids.add(envelope.snapshot_id)
        ingestion_batch_ids.add(envelope.ingestion_batch_id)
        observed_times.add(envelope.observed_time)
        ingestion_times.add(envelope.ingestion_time)
    if gamma_count > _MAX_MARKETS_LIMIT or book_count > _MAX_ORDER_BOOKS_LIMIT:
        raise _PopulationReject("POPULATION_RECOVERY_INVALID")
    if (
        len(snapshot_ids) != 1
        or len(ingestion_batch_ids) != 1
        or len(observed_times) != 1
        or len(ingestion_times) != 1
    ):
        raise _PopulationReject("POPULATION_RECOVERY_INVALID")
    if next(iter(observed_times)) != next(iter(ingestion_times)):
        raise _PopulationReject("POPULATION_RECOVERY_INVALID")


def _parse_recovery_payload(canonical_payload_json: object) -> dict:
    if type(canonical_payload_json) is not str:
        raise _PopulationReject("POPULATION_RECOVERY_INVALID")
    try:
        payload = json.loads(canonical_payload_json)
    except Exception:
        raise _PopulationReject("POPULATION_RECOVERY_INVALID")
    if type(payload) is not dict:
        raise _PopulationReject("POPULATION_RECOVERY_INVALID")
    return payload


def _prove_wp164_construction(
    records: tuple[object, ...], config: PolymarketPublicPopulationConfig
) -> None:
    """Re-prove that the stored records are a genuine WP164 build, not a forgery.

    A caller can craft WP156-valid records that merely reuse the WP164 source IDs
    and share arbitrary snapshot/batch IDs. This re-derives every WP164
    construction invariant — payload key sets, identifiers, content-addressed
    source-snapshot/assertion IDs, unique token parentage, and the content-addressed
    run identities — and requires an exact match. Any deviation rejects.
    """

    gamma = [r for r in records if r.source_id == _GAMMA_SOURCE_ID]
    clob = [r for r in records if r.source_id == _CLOB_SOURCE_ID]
    if not gamma:
        # A book-only store cannot be a genuine WP164 seed.
        raise _PopulationReject("POPULATION_RECOVERY_INVALID")

    unique_snapshot_id = records[0].envelope.snapshot_id
    unique_captured = records[0].envelope.observed_time

    # Token ownership derived only from parsed Gamma payloads.
    token_owner: dict[str, list[tuple[str, str]]] = {}
    gamma_payloads: dict[str, dict] = {}
    for record in gamma:
        payload = _parse_recovery_payload(record.canonical_payload_json)
        if frozenset(payload) != _GAMMA_PAYLOAD_KEYS:
            raise _PopulationReject("POPULATION_RECOVERY_INVALID")
        prefix = "market:polymarket:"
        if not record.market_id.startswith(prefix):
            raise _PopulationReject("POPULATION_RECOVERY_INVALID")
        raw_gamma_id = record.market_id[len(prefix):]
        if not raw_gamma_id:
            raise _PopulationReject("POPULATION_RECOVERY_INVALID")
        if record.token_id is not None:
            raise _PopulationReject("POPULATION_RECOVERY_INVALID")
        condition_id = payload["condition_id"]
        condition_norm = (
            condition_id.strip() if isinstance(condition_id, str) and condition_id else ""
        )
        expected_event = (
            "event:polymarket:" + condition_norm
            if condition_norm
            else "event:polymarket:market-" + raw_gamma_id
        )
        if record.event_id != expected_event:
            raise _PopulationReject("POPULATION_RECOVERY_INVALID")
        expected_srcsnap = _content_id(
            "srcsnap:sha256:",
            {
                "source_id": _GAMMA_SOURCE_ID,
                "market_id": record.market_id,
                "snapshot_id": unique_snapshot_id,
                "canonical_payload": payload,
            },
        )
        if record.envelope.source_snapshot_id != expected_srcsnap:
            raise _PopulationReject("POPULATION_RECOVERY_INVALID")
        expected_assertion = _content_id(
            "assertion:sha256:",
            {
                "source_snapshot_id": expected_srcsnap,
                "observation_kind": "MARKET_METADATA",
                "market_id": record.market_id,
                "event_id": record.event_id,
                "token_id": None,
            },
        )
        if record.source_assertion_id != expected_assertion:
            raise _PopulationReject("POPULATION_RECOVERY_INVALID")
        token_ids = payload["token_ids"]
        if type(token_ids) is not list:
            raise _PopulationReject("POPULATION_RECOVERY_INVALID")
        for raw_token in token_ids:
            if type(raw_token) is not str:
                raise _PopulationReject("POPULATION_RECOVERY_INVALID")
            token_owner.setdefault(raw_token, []).append(
                (record.market_id, record.event_id)
            )
        gamma_payloads[record.market_id] = payload

    for record in clob:
        payload = _parse_recovery_payload(record.canonical_payload_json)
        if frozenset(payload) != _CLOB_PAYLOAD_KEYS:
            raise _PopulationReject("POPULATION_RECOVERY_INVALID")
        prefix = "token:polymarket:"
        if record.token_id is None or not record.token_id.startswith(prefix):
            raise _PopulationReject("POPULATION_RECOVERY_INVALID")
        raw_token = record.token_id[len(prefix):]
        owners = token_owner.get(raw_token, [])
        if len(owners) != 1:
            # Orphan (no Gamma parent) or ambiguous (multiple parents).
            raise _PopulationReject("POPULATION_RECOVERY_INVALID")
        parent_market_id, parent_event_id = owners[0]
        if record.market_id != parent_market_id or record.event_id != parent_event_id:
            raise _PopulationReject("POPULATION_RECOVERY_INVALID")
        expected_srcsnap = _content_id(
            "srcsnap:sha256:",
            {
                "source_id": _CLOB_SOURCE_ID,
                "market_id": record.market_id,
                "token_id": record.token_id,
                "snapshot_id": unique_snapshot_id,
                "canonical_payload": payload,
            },
        )
        if record.envelope.source_snapshot_id != expected_srcsnap:
            raise _PopulationReject("POPULATION_RECOVERY_INVALID")
        expected_assertion = _content_id(
            "assertion:sha256:",
            {
                "source_snapshot_id": expected_srcsnap,
                "observation_kind": "ORDER_BOOK",
                "market_id": record.market_id,
                "event_id": record.event_id,
                "token_id": record.token_id,
            },
        )
        if record.source_assertion_id != expected_assertion:
            raise _PopulationReject("POPULATION_RECOVERY_INVALID")

    # Recompute the content-addressed run identities in deterministic WP164 order
    # and require exact equality with the stored unique identities.
    gamma_sorted = sorted(gamma, key=lambda record: record.market_id)
    clob_sorted = sorted(
        clob, key=lambda record: (record.market_id, record.token_id or "")
    )
    gamma_payload_hashes = [
        sha256_hex(record.canonical_payload_json) for record in gamma_sorted
    ]
    clob_payload_hashes = [
        sha256_hex(record.canonical_payload_json) for record in clob_sorted
    ]
    recomputed_snapshot_id, recomputed_ingestion_batch_id = _run_identities(
        captured_at_utc=unique_captured,
        gamma_payload_hashes=gamma_payload_hashes,
        clob_payload_hashes=clob_payload_hashes,
        config=config,
    )
    if recomputed_snapshot_id != unique_snapshot_id:
        raise _PopulationReject("POPULATION_RECOVERY_INVALID")
    if recomputed_ingestion_batch_id != records[0].envelope.ingestion_batch_id:
        raise _PopulationReject("POPULATION_RECOVERY_INVALID")


def _wp164_sort(
    records: tuple[MarketObservationRecord, ...],
) -> tuple[MarketObservationRecord, ...]:
    gamma = sorted(
        (r for r in records if r.source_id == _GAMMA_SOURCE_ID),
        key=lambda record: record.market_id,
    )
    books = sorted(
        (r for r in records if r.source_id == _CLOB_SOURCE_ID),
        key=lambda record: (record.market_id, record.token_id or ""),
    )
    return tuple(gamma) + tuple(books)
