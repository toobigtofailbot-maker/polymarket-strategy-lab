"""WP169 public unauthenticated Data / Gamma / CLOB GET acquisition.

GET-only, standard-library-only transport (urllib) with an injectable transport
seam for tests. No credentials, authenticated headers, or non-GET methods are
structurally reachable. Every response is byte-bounded before JSON parse and
each raw attempt is archived before normalization.
"""

from __future__ import annotations

import asyncio
import json
import os
import pathlib
import tempfile
import threading
import time
import urllib.parse
from collections.abc import Callable, Mapping, Sequence


class NetworkBudgetExhausted(Exception):
    """Raised by the shared budget when the single foreground network-call budget is
    spent. This is a graceful terminal signal (STOPPED / NETWORK_CALL_LIMIT), never a
    failure -- it is distinct from MarketTruthError so callers map it to the frozen
    terminal outcome rather than to a closed error code."""

from .market_truth import (
    AcquisitionLimits,
    AcquisitionReceipt,
    MarketTruthError,
    PublicPageResult,
    RawEnvelope,
    build_page_quarantine,
    canonical_decimal,
    canonical_json_bytes,
    make_raw_envelope,
    is_rfc3339_micros,
    normalize_public_record,
    sha256_hex,
)
from .market_truth_store import MarketTruthStore

DATA_BASE = "https://data-api.polymarket.com"
GAMMA_BASE = "https://gamma-api.polymarket.com"
CLOB_BASE = "https://clob.polymarket.com"

_CONDITION_RE = __import__("re").compile(r"^0x[0-9a-f]{64}$")
_TOKEN_RE = __import__("re").compile(r"^(?:0|[1-9][0-9]{0,77})$")
_DECIMAL_RE = __import__("re").compile(r"^(?:0|[1-9][0-9]*)(?:\.[0-9]+)?$")
_EVENT_ID_RE = __import__("re").compile(r"^[1-9][0-9]*$")

_ACTIVITY_TYPES = frozenset(
    {
        "TRADE", "SPLIT", "MERGE", "REDEEM", "REWARD", "CONVERSION", "DEPOSIT",
        "WITHDRAWAL", "YIELD", "MAKER_REBATE", "TAKER_REBATE", "REFERRAL_REWARD",
    }
)
_RETRYABLE = frozenset({429, 502, 503, 504})

# endpoint token -> (base, path template, source_kind, paged, offset_max, limit_range)
_ENDPOINTS: dict[str, dict[str, object]] = {
    "trades": {"base": DATA_BASE, "path": "/trades", "kind": "DATA", "paged": True, "offset_max": 10_000, "limit": (1, 10_000)},
    "activity": {"base": DATA_BASE, "path": "/activity", "kind": "DATA", "paged": True, "offset_max": 5_000, "limit": (1, 500)},
    "positions": {"base": DATA_BASE, "path": "/positions", "kind": "DATA", "paged": True, "offset_max": 10_000, "limit": (1, 500)},
    "holders": {"base": DATA_BASE, "path": "/holders", "kind": "DATA", "paged": False, "offset_max": None, "limit": (1, 20)},
    "markets": {"base": GAMMA_BASE, "path": "/markets", "kind": "GAMMA", "paged": False, "offset_max": 100_000, "limit": (1, 100)},
    "market-by-id": {"base": GAMMA_BASE, "path": "/markets/{id}", "kind": "GAMMA", "paged": False, "offset_max": None, "limit": None},
    "book": {"base": CLOB_BASE, "path": "/book", "kind": "CLOB", "paged": False, "offset_max": None, "limit": None},
    "fee-rate": {"base": CLOB_BASE, "path": "/fee-rate", "kind": "CLOB", "paged": False, "offset_max": None, "limit": None},
    "clob-market-info": {"base": CLOB_BASE, "path": "/clob-markets/{condition_id}", "kind": "CLOB", "paged": False, "offset_max": None, "limit": None},
}
_SOURCE_ID = {
    "DATA": "polymarket:data-api:",
    "GAMMA": "polymarket:gamma:",
    "CLOB": "polymarket:clob:",
}


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _comma_list(value: object, item_re, *, maximum: int = 50) -> list[str] | None:
    if not isinstance(value, str) or not value:
        return None
    items = value.split(",")
    if not 1 <= len(items) <= maximum or len(set(items)) != len(items):
        return None
    for item in items:
        if item_re.fullmatch(item) is None:
            return None
    return items


def _normalize_params(endpoint: str, params: Mapping[str, object]) -> dict[str, str]:
    """Validate and normalize params to their canonical string form, or fail closed."""
    if endpoint not in _ENDPOINTS:
        raise MarketTruthError("ENDPOINT_FORBIDDEN")
    if not isinstance(params, Mapping):
        raise MarketTruthError("ENDPOINT_FORBIDDEN")
    allowed = _ALLOWED_KEYS[endpoint]
    for key in params:
        if not isinstance(key, str) or key not in allowed:
            raise MarketTruthError("ENDPOINT_FORBIDDEN")
    out: dict[str, str] = {}
    validator = _VALIDATORS[endpoint]
    validator(params, out)
    return out


def _string_int(value: object, low: int, high: int) -> str | None:
    if _is_int(value) and low <= value <= high:
        return str(value)
    if isinstance(value, str) and value.isdigit() and low <= int(value) <= high:
        return str(int(value))
    return None


def _bool_str(value: object) -> str | None:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value in ("true", "false"):
        return value
    return None


def _require_limit(endpoint: str, params: Mapping[str, object], out: dict[str, str]) -> None:
    limit_range = _ENDPOINTS[endpoint]["limit"]
    if "limit" in params:
        low, high = limit_range  # type: ignore[misc]
        normalized = _string_int(params["limit"], low, high)
        if normalized is None:
            raise MarketTruthError("INPUT_INVALID")
        out["limit"] = normalized


def _require_offset(endpoint: str, params: Mapping[str, object], out: dict[str, str]) -> None:
    offset_max = _ENDPOINTS[endpoint]["offset_max"]
    if "offset" in params:
        if offset_max is None:
            raise MarketTruthError("ENDPOINT_FORBIDDEN")
        normalized = _string_int(params["offset"], 0, int(offset_max))
        if normalized is None:
            raise MarketTruthError("INPUT_INVALID")
        out["offset"] = normalized


def _validate_market_or_event(params: Mapping[str, object], out: dict[str, str]) -> None:
    if "market" in params and "eventId" in params:
        raise MarketTruthError("INPUT_INVALID")
    if "market" in params:
        items = _comma_list(params["market"], _CONDITION_RE)
        if items is None:
            raise MarketTruthError("INPUT_INVALID")
        out["market"] = ",".join(items)
    if "eventId" in params:
        items = _comma_list(params["eventId"], _EVENT_ID_RE)
        if items is None:
            raise MarketTruthError("INPUT_INVALID")
        out["eventId"] = ",".join(items)


def _validate_trades(params: Mapping[str, object], out: dict[str, str]) -> None:
    _require_limit("trades", params, out)
    _require_offset("trades", params, out)
    _validate_market_or_event(params, out)
    if "user" in params:
        if not isinstance(params["user"], str) or __import__("re").fullmatch(
            r"^0x[0-9a-fA-F]{40}$", params["user"]
        ) is None:
            raise MarketTruthError("INPUT_INVALID")
        out["user"] = params["user"].lower()
    if "side" in params:
        if params["side"] not in ("BUY", "SELL"):
            raise MarketTruthError("INPUT_INVALID")
        out["side"] = params["side"]
    _validate_common_filters(params, out)


def _validate_activity(params: Mapping[str, object], out: dict[str, str]) -> None:
    _require_limit("activity", params, out)
    _require_offset("activity", params, out)
    if "user" not in params:
        raise MarketTruthError("INPUT_INVALID")
    if __import__("re").fullmatch(r"^0x[0-9a-fA-F]{40}$", str(params["user"])) is None:
        raise MarketTruthError("INPUT_INVALID")
    out["user"] = str(params["user"]).lower()
    _validate_market_or_event(params, out)
    types: list[str] | None = None
    if "type" in params:
        types = _comma_list(params["type"], __import__("re").compile(r"^[A-Z_]+$"))
        if types is None or any(item not in _ACTIVITY_TYPES for item in types):
            raise MarketTruthError("INPUT_INVALID")
        out["type"] = ",".join(types)
    if "excludeDepositsWithdrawals" in params:
        value = _bool_str(params["excludeDepositsWithdrawals"])
        if value is None:
            raise MarketTruthError("INPUT_INVALID")
        out["excludeDepositsWithdrawals"] = value
    if types is not None and ({"DEPOSIT", "WITHDRAWAL"} & set(types)):
        if out.get("excludeDepositsWithdrawals") != "false":
            raise MarketTruthError("INPUT_INVALID")
    if "sortBy" in params:
        if params["sortBy"] not in ("TIMESTAMP", "TOKENS", "CASH"):
            raise MarketTruthError("INPUT_INVALID")
        out["sortBy"] = params["sortBy"]
    if "side" in params:
        # side is a frozen accepted /activity key (BUY/SELL); an invalid side must fail
        # closed rather than be silently dropped, and a valid side is preserved.
        if params["side"] not in ("BUY", "SELL"):
            raise MarketTruthError("INPUT_INVALID")
        out["side"] = params["side"]
    _validate_common_filters(params, out)


def _validate_positions(params: Mapping[str, object], out: dict[str, str]) -> None:
    _require_limit("positions", params, out)
    _require_offset("positions", params, out)
    if "user" not in params:
        raise MarketTruthError("INPUT_INVALID")
    if __import__("re").fullmatch(r"^0x[0-9a-fA-F]{40}$", str(params["user"])) is None:
        raise MarketTruthError("INPUT_INVALID")
    out["user"] = str(params["user"]).lower()
    _validate_market_or_event(params, out)
    for flag in ("redeemable", "mergeable", "includeArchived"):
        if flag in params:
            value = _bool_str(params[flag])
            if value is None:
                raise MarketTruthError("INPUT_INVALID")
            out[flag] = value
    if "sizeThreshold" in params:
        threshold = canonical_decimal(str(params["sizeThreshold"]))
        if threshold is None:
            raise MarketTruthError("INPUT_INVALID")
        out["sizeThreshold"] = threshold
    if "sortBy" in params:
        if params["sortBy"] not in (
            "CURRENT", "INITIAL", "TOKENS", "CASHPNL", "PERCENTPNL", "TITLE",
            "RESOLVING", "PRICE", "AVGPRICE",
        ):
            raise MarketTruthError("INPUT_INVALID")
        out["sortBy"] = params["sortBy"]
    if "title" in params:
        if not isinstance(params["title"], str) or not 1 <= len(params["title"]) <= 100:
            raise MarketTruthError("INPUT_INVALID")
        out["title"] = params["title"]
    if "sortDirection" in params:
        if params["sortDirection"] not in ("ASC", "DESC"):
            raise MarketTruthError("INPUT_INVALID")
        out["sortDirection"] = params["sortDirection"]


def _validate_holders(params: Mapping[str, object], out: dict[str, str]) -> None:
    _require_limit("holders", params, out)
    if "market" not in params:
        raise MarketTruthError("INPUT_INVALID")
    items = _comma_list(params["market"], _CONDITION_RE)
    if items is None:
        raise MarketTruthError("INPUT_INVALID")
    out["market"] = ",".join(items)
    if "minBalance" in params:
        normalized = _string_int(params["minBalance"], 0, 999_999)
        if normalized is None:
            raise MarketTruthError("INPUT_INVALID")
        out["minBalance"] = normalized


def _validate_common_filters(params: Mapping[str, object], out: dict[str, str]) -> None:
    if "start" in params or "end" in params:
        start = params.get("start")
        end = params.get("end")
        s = _string_int(start, 0, 99_999_999_999) if start is not None else None
        e = _string_int(end, 0, 99_999_999_999) if end is not None else None
        if start is not None:
            if s is None:
                raise MarketTruthError("INPUT_INVALID")
            out["start"] = s
        if end is not None:
            if e is None:
                raise MarketTruthError("INPUT_INVALID")
            out["end"] = e
        if s is not None and e is not None and int(s) > int(e):
            raise MarketTruthError("INPUT_INVALID")
    if "filterAmount" in params or "filterType" in params:
        if "filterType" not in params or "filterAmount" not in params:
            raise MarketTruthError("INPUT_INVALID")
        if params["filterType"] not in ("CASH", "TOKENS"):
            raise MarketTruthError("INPUT_INVALID")
        # Canonical nonnegative decimal: equivalent spellings ("1","01","1.0","1.00") must
        # normalize to one canonical form so they cannot produce distinct query/checkpoint
        # identities; exponent/negative/negative-zero are rejected.
        amount = canonical_decimal(str(params["filterAmount"]))
        if amount is None:
            raise MarketTruthError("INPUT_INVALID")
        out["filterType"] = str(params["filterType"])
        out["filterAmount"] = amount
    for passthrough in ("takerOnly", "excludeDepositsWithdrawals"):
        if passthrough in params and passthrough not in out:
            value = _bool_str(params[passthrough])
            if value is None:
                raise MarketTruthError("INPUT_INVALID")
            out[passthrough] = value
    if "sortDirection" in params and "sortDirection" not in out:
        if params["sortDirection"] not in ("ASC", "DESC"):
            raise MarketTruthError("INPUT_INVALID")
        out["sortDirection"] = params["sortDirection"]


def _validate_markets(params: Mapping[str, object], out: dict[str, str]) -> None:
    _require_limit("markets", params, out)
    _require_offset("markets", params, out)
    for flag in ("active", "closed"):
        if flag in params:
            value = _bool_str(params[flag])
            if value is None:
                raise MarketTruthError("INPUT_INVALID")
            out[flag] = value


def _validate_market_by_id(params: Mapping[str, object], out: dict[str, str]) -> None:
    if "id" not in params or _EVENT_ID_RE.fullmatch(str(params["id"])) is None:
        raise MarketTruthError("INPUT_INVALID")
    out["id"] = str(params["id"])


def _validate_token_id(params: Mapping[str, object], out: dict[str, str]) -> None:
    if "token_id" not in params or not _TOKEN_RE.fullmatch(str(params.get("token_id", ""))):
        raise MarketTruthError("INPUT_INVALID")
    out["token_id"] = str(params["token_id"])


def _validate_clob_market_info(params: Mapping[str, object], out: dict[str, str]) -> None:
    if "condition_id" not in params or _CONDITION_RE.fullmatch(str(params.get("condition_id", ""))) is None:
        raise MarketTruthError("INPUT_INVALID")
    out["condition_id"] = str(params["condition_id"])


_ALLOWED_KEYS: dict[str, frozenset[str]] = {
    "trades": frozenset({"limit", "offset", "takerOnly", "filterType", "filterAmount", "market", "eventId", "user", "side", "start", "end"}),
    "activity": frozenset({"limit", "offset", "user", "market", "eventId", "type", "excludeDepositsWithdrawals", "start", "end", "sortBy", "sortDirection", "side"}),
    "positions": frozenset({"user", "market", "eventId", "sizeThreshold", "redeemable", "mergeable", "includeArchived", "limit", "offset", "sortBy", "sortDirection", "title"}),
    "holders": frozenset({"limit", "market", "minBalance"}),
    "markets": frozenset({"limit", "offset", "active", "closed"}),
    "market-by-id": frozenset({"id"}),
    "book": frozenset({"token_id"}),
    "fee-rate": frozenset({"token_id"}),
    "clob-market-info": frozenset({"condition_id"}),
}
_VALIDATORS: dict[str, Callable[[Mapping[str, object], dict[str, str]], None]] = {
    "trades": _validate_trades,
    "activity": _validate_activity,
    "positions": _validate_positions,
    "holders": _validate_holders,
    "markets": _validate_markets,
    "market-by-id": _validate_market_by_id,
    "book": _validate_token_id,
    "fee-rate": _validate_token_id,
    "clob-market-info": _validate_clob_market_info,
}


def _build_url(endpoint: str, params: Mapping[str, str]) -> tuple[str, dict[str, str]]:
    spec = _ENDPOINTS[endpoint]
    path = str(spec["path"])
    query = dict(params)
    if "{id}" in path:
        path = path.replace("{id}", urllib.parse.quote(query.pop("id"), safe=""))
    if "{condition_id}" in path:
        path = path.replace("{condition_id}", urllib.parse.quote(query.pop("condition_id"), safe=""))
    url = str(spec["base"]) + path
    if query:
        url = url + "?" + urllib.parse.urlencode(sorted(query.items()))
    return url, query


class RateLimiter:
    """Monotonic in-process token bucket with a shared network-call budget.

    Per-source caps: DATA/GAMMA/CLOB use their calls-per-10-second caps; POLYGON uses
    its per-second cap. `acquire` delays (via the injectable sleeper) only enough to
    respect the cap and never exceeds `max_network_calls`. Both the monotonic clock and
    the sleeper are injectable so tests assert exact rate decisions deterministically.
    """

    def __init__(
        self,
        limits: AcquisitionLimits | None = None,
        *,
        monotonic: Callable[[], float] | None = None,
        sleeper: Callable[[float], None] | None = None,
    ) -> None:
        self._limits = limits or AcquisitionLimits()
        self._monotonic = monotonic or time.monotonic
        self._sleeper = sleeper or time.sleep
        self._events: dict[str, list[float]] = {}
        self.network_calls = 0
        # One shared budget is consulted concurrently by the event-loop thread (WS) and
        # to_thread workers (HTTP/RPC); all accounting is serialized.
        self._lock = threading.Lock()

    def _cap_window(self, source_kind: str) -> tuple[int, float]:
        if source_kind == "DATA":
            return self._limits.data_calls_per_10_seconds, 10.0
        if source_kind == "GAMMA":
            return self._limits.gamma_calls_per_10_seconds, 10.0
        if source_kind == "CLOB":
            return self._limits.clob_calls_per_10_seconds, 10.0
        if source_kind == "POLYGON":
            return self._limits.rpc_calls_per_second, 1.0
        return self._limits.max_network_calls, 10.0

    def budget_exhausted(self) -> bool:
        with self._lock:
            return self.network_calls >= self._limits.max_network_calls

    def acquire(self, source_kind: str) -> float:
        """Reserve one call for source_kind, delaying to respect the per-source cap.

        Raises NetworkBudgetExhausted (a graceful terminal signal) when the single
        shared foreground network budget is spent. Thread-safe; the cap delay is slept
        outside the lock so concurrent surfaces are not blocked by one another's wait.
        """
        cap, window = self._cap_window(source_kind)
        total_delay = 0.0
        while True:
            with self._lock:
                if self.network_calls >= self._limits.max_network_calls:
                    raise NetworkBudgetExhausted()
                now = self._monotonic()
                stamps = [t for t in self._events.get(source_kind, []) if now - t < window]
                # Re-check the per-source cap under the lock before EVERY grant, including
                # after waking from the sleeper, so two concurrent same-source callers can
                # never both grant beyond the cap for the current window.
                if len(stamps) < cap:
                    stamps.append(now)
                    self._events[source_kind] = stamps
                    self.network_calls += 1
                    return total_delay
                delay = window - (now - stamps[0])
            if delay <= 0:
                continue  # window edge already passed; re-evaluate under the lock
            self._sleeper(delay)
            total_delay += delay


class PublicMarketDataClient:
    """GET-only public data client with retry, byte bounds and no-echo failures."""

    def __init__(
        self,
        limits: AcquisitionLimits | None = None,
        transport: Callable[..., tuple[int, Mapping[str, str], bytes]] | None = None,
        clock: Callable[[], str] | None = None,
    ) -> None:
        self._limits = limits or AcquisitionLimits()
        self._transport = transport or _default_transport
        self._clock = clock or _default_clock
        # Private injectable seams NOT part of the exact frozen public signature: the
        # runtime attaches a shared RateLimiter (single foreground network budget) and
        # tests may substitute a deterministic sleeper. Both default to production values.
        self._sleeper: Callable[[float], None] = time.sleep
        self._rate_limiter: RateLimiter | None = None
        self.retry_delays: list[float] = []
        # Only the bounded TS01 orchestration enables this producer-owned capture.
        self._ts01_attempts: list[dict[str, object]] | None = None

    def get_page(self, endpoint: str, params: Mapping[str, str | int]) -> PublicPageResult:
        normalized = _normalize_params(endpoint, params)
        url, _query = _build_url(endpoint, normalized)
        spec = _ENDPOINTS[endpoint]
        source_kind = str(spec["kind"])
        source_id = _SOURCE_ID[source_kind] + endpoint
        offset = normalized.get("offset", "0")
        attempts: list[RawEnvelope] = []
        headers = {"Accept": "application/json", "User-Agent": "wp169-public-market-truth/1.0"}
        backoff_index = 0
        for attempt in range(self._limits.max_retries + 1):
            cursor = f"http:{endpoint}:offset:{offset}:attempt:{attempt}"
            if self._rate_limiter is not None:
                # NETWORK_CALL_LIMIT is a stop reason, NOT a closed error code, so it must
                # never appear in PublicPageResult.error_codes. Propagate the private
                # NetworkBudgetExhausted signal; collect/runtime translate it to the frozen
                # terminal STOPPED / () / NETWORK_CALL_LIMIT at the receipt boundary.
                self._rate_limiter.acquire(source_kind)
            try:
                if self._ts01_attempts is not None:
                    started_at = self._clock()
                    started_ns = time.monotonic_ns()
                status, resp_headers, body = self._transport(
                    url, headers, self._limits.request_timeout_seconds
                )
                if self._ts01_attempts is not None:
                    elapsed_ns = time.monotonic_ns() - started_ns
                    completed_at = self._clock()
            except MarketTruthError:
                return PublicPageResult("FAILED", ("NETWORK_TIMEOUT",), tuple(attempts), None)
            except Exception:
                return PublicPageResult("FAILED", ("NETWORK_TIMEOUT",), tuple(attempts), None)
            received_at = self._clock()
            if len(body) > self._limits.max_response_bytes:
                return PublicPageResult("FAILED", ("RESPONSE_TOO_LARGE",), tuple(attempts), None)
            raw = make_raw_envelope(
                source_kind, source_id, cursor, received_at, body,
                occurrence_sequence=attempt, limits=self._limits,
            )
            attempts.append(raw)
            if self._ts01_attempts is not None:
                self._ts01_attempts.append({
                    "endpoint": endpoint, "params": normalized, "url": url,
                    "http_status": status, "request_started_at": started_at,
                    "response_completed_at": completed_at, "duration_ns": elapsed_ns,
                    **{key: getattr(raw, key) for key in _TS01_RAW_FIELDS},
                })
            if 200 <= status < 300:
                return PublicPageResult("OK", (), tuple(attempts), len(attempts) - 1)
            if status in _RETRYABLE and attempt < self._limits.max_retries:
                retry_after = None
                for key, value in resp_headers.items():
                    if key.lower() == "retry-after":
                        retry_after = value
                        break
                if retry_after is not None:
                    if not (isinstance(retry_after, str) and retry_after.isdigit()) or not (
                        0 <= int(retry_after) <= self._limits.retry_after_max_seconds
                    ):
                        return PublicPageResult(
                            "FAILED", ("RETRY_AFTER_INVALID",), tuple(attempts), None
                        )
                    delay = float(int(retry_after))
                else:
                    # Deterministic exponential backoff 1,2,4,... capped at max_backoff.
                    delay = float(min(2 ** backoff_index, self._limits.max_backoff_seconds))
                self.retry_delays.append(delay)
                if delay > 0:
                    self._sleeper(delay)
                backoff_index += 1
                continue
            if status in _RETRYABLE:
                return PublicPageResult("FAILED", ("RETRY_EXHAUSTED",), tuple(attempts), None)
            return PublicPageResult("FAILED", ("RESPONSE_INVALID",), tuple(attempts), None)
        return PublicPageResult("FAILED", ("RETRY_EXHAUSTED",), tuple(attempts), None)


def _http_checkpoint_key(endpoint: str, params: Mapping[str, str]) -> str:
    without_offset = {k: v for k, v in params.items() if k != "offset"}
    digest = sha256_hex(canonical_json_bytes(without_offset))
    return "http:" + endpoint + ":query:sha256:" + digest


def archive_page_attempts(
    store: MarketTruthStore,
    endpoint: str,
    result: PublicPageResult,
    limit: int,
    limits: AcquisitionLimits,
) -> tuple[list[object], RawEnvelope | None, AcquisitionReceipt | None]:
    """Shared raw-first archival, budget/transport, and page-bound handling.

    This is the single literally-shared implementation used by both collect_public_page and
    runtime active-market discovery, so both have identical raw-first / store-failure /
    page-bound behavior. Returns (records, success_raw, terminal_receipt): when
    terminal_receipt is not None the page is terminal (records/raw are empty/None) and the
    caller must return that receipt; otherwise records+success_raw are ready to normalize.
    """
    # Archive every attempt before parsing; a raw-persistence failure (store row/byte
    # exhaustion or conflict) is terminal and visible -- nothing is silently dropped.
    for raw in result.attempts:
        archive_receipt = store.append(raw)
        if archive_receipt.status != "OK":
            return [], None, archive_receipt
    if result.status != "OK" or result.successful_attempt_index is None:
        return [], None, store.receipt("FAILED", result.error_codes, "NONE")
    raw = result.attempts[result.successful_attempt_index]
    records = _extract_records(raw)
    # Enforce page/record bounds BEFORE normalization; on violation commit only the raw
    # envelope plus one sanitized quarantined observation (no partial children).
    bound_error = _page_bound_error(records, endpoint, limit, limits)
    if bound_error is not None:
        store.append(raw, (build_page_quarantine(raw, endpoint, bound_error),))
        return [], None, store.receipt("FAILED", (bound_error,), "NONE")
    return records, raw, None


def collect_public_page(
    client: PublicMarketDataClient,
    store: MarketTruthStore,
    endpoint: str,
    params: Mapping[str, str | int],
    *,
    max_pages: int = 1,
    stop_event: "asyncio.Event | None" = None,
) -> AcquisitionReceipt:
    """Archive every attempt and normalize successful pages, advancing offsets."""
    if endpoint not in _ENDPOINTS:
        return store.receipt("FAILED", ("ENDPOINT_FORBIDDEN",), "NONE")
    if not _is_int(max_pages) or not 1 <= max_pages <= client._limits.max_pages:
        return store.receipt("FAILED", ("LIMIT_INVALID",), "NONE")
    spec = _ENDPOINTS[endpoint]
    paged = bool(spec["paged"]) and spec["offset_max"] is not None
    try:
        normalized = _normalize_params(endpoint, params)
    except MarketTruthError as error:
        return store.receipt("FAILED", error.error_codes, "NONE")

    # collect_public_page manages paged offsets via ACTIVE checkpoints, so it accepts only
    # an omitted offset or offset=0; a nonzero caller offset must not be silently ignored.
    # (Direct get_page remains available for any validated offset.)
    if paged and normalized.get("offset", "0") != "0":
        return store.receipt("FAILED", ("INPUT_INVALID",), "NONE")
    normalized.pop("offset", None)

    checkpoint_key = _http_checkpoint_key(endpoint, normalized) if paged else None
    offset = 0
    limit = int(normalized.get("limit", spec["limit"][1] if spec["limit"] else 1))  # type: ignore[index]
    if paged:
        existing = store.load_checkpoint(checkpoint_key) if checkpoint_key else None
        if existing is not None and existing.state == "ACTIVE":
            offset = int(json.loads(existing.value_json).get("next_offset", 0))

    pages = 0
    while pages < max_pages:
        # Item 11: an in-flight bounded request (page 1) may finish; a NEXT page must not
        # begin once the shared stop is set (caller/sibling terminal). The stop is therefore
        # checked before page 2+, not before the first page of this cadence's request.
        if pages > 0 and stop_event is not None and stop_event.is_set():
            return store.receipt("STOPPED", (), "CALLER_STOP")
        page_params = dict(normalized)
        if paged:
            page_params["offset"] = str(offset)
        try:
            result = client.get_page(endpoint, page_params)
        except NetworkBudgetExhausted:
            # Shared foreground budget spent: frozen terminal STOPPED / () / NETWORK_CALL_LIMIT
            # (NETWORK_CALL_LIMIT is a stop reason, never a public error code).
            return store.receipt("STOPPED", (), "NETWORK_CALL_LIMIT")
        records, raw, terminal = archive_page_attempts(
            store, endpoint, result, limit, client._limits
        )
        if terminal is not None:
            return terminal
        observations = []
        for index, _record in enumerate(records):
            observations.append(normalize_public_record(raw, endpoint=endpoint, record_index=index))
        append_receipt = store.append(raw, observations)
        if append_receipt.status != "OK":
            return append_receipt
        pages += 1
        if not paged:
            break
        record_count = len(records)
        offset_max = int(spec["offset_max"])  # type: ignore[arg-type]
        if record_count < limit or offset + limit > offset_max:
            store.write_checkpoint(
                checkpoint_key, {"endpoint": endpoint, "next_offset": 0, "last_raw_id": raw.raw_id}, "SUPERSEDED"
            )
            return store.receipt("OK", (), "NONE")
        offset += limit
        store.write_checkpoint(
            checkpoint_key, {"endpoint": endpoint, "next_offset": offset, "last_raw_id": raw.raw_id}, "ACTIVE"
        )
    return store.receipt("OK", (), "NONE")


def _page_bound_error(
    records: list[object], endpoint: str, limit: int, limits: AcquisitionLimits
) -> str | None:
    """Return a closed error code if the page violates record-count/byte bounds."""
    spec = _ENDPOINTS[endpoint]
    count = len(records)
    if count > limits.max_records_per_page:
        return "RESPONSE_INVALID"
    # Paged endpoints must not return more than the requested page maximum.
    if bool(spec["paged"]) and spec["offset_max"] is not None and count > limit:
        return "RESPONSE_INVALID"
    for record in records:
        try:
            encoded = json.dumps(record, separators=(",", ":")).encode("utf-8")
        except (TypeError, ValueError):
            return "RESPONSE_INVALID"
        if len(encoded) > limits.max_record_bytes:
            return "RESPONSE_TOO_LARGE"
    return None


def _extract_records(raw: RawEnvelope) -> list[object]:
    try:
        document = json.loads(raw.raw_bytes.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return [None]
    if isinstance(document, list):
        return list(document) if document else []
    return [document]


def _default_clock() -> str:  # pragma: no cover - wall clock
    import datetime

    moment = datetime.datetime.now(datetime.timezone.utc)
    return f"{moment:%Y-%m-%dT%H:%M:%S}.{moment.microsecond:06d}Z"


def _default_transport(
    url: str, headers: Mapping[str, str], timeout_seconds: int
) -> tuple[int, Mapping[str, str], bytes]:  # pragma: no cover - network
    import urllib.request

    request = urllib.request.Request(url, method="GET")
    for key, value in headers.items():
        request.add_header(key, value)
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            body = response.read()
            return int(response.status), dict(response.headers), body
    except urllib.error.HTTPError as error:  # type: ignore[attr-defined]
        return int(error.code), dict(error.headers or {}), error.read() or b""
    except Exception:
        raise MarketTruthError("NETWORK_TIMEOUT")


import urllib.error  # noqa: E402  (used by _default_transport)


# TS01 is an additive local witness, never signed upstream provenance or permission.
_TS01_RAW_FIELDS = (
    "raw_id", "occurrence_id", "source_kind", "source_id", "source_cursor",
    "received_at", "media_type", "raw_sha256", "byte_length",
)
_TS01_RECEIPT_BYTES = 65_536


def _ts01_json(payload: bytes) -> object:
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise MarketTruthError("RESPONSE_INVALID")
            result[key] = value
        return result

    return json.loads(payload, object_pairs_hook=unique)


def _ts01_bounded_body(response, maximum: int) -> bytes:
    declared = response.headers.get("Content-Length")
    if declared is not None and (
        not isinstance(declared, str) or not declared.isascii() or not declared.isdigit()
        or len(declared) > 10 or int(declared) > maximum
    ):
        raise MarketTruthError("RESPONSE_TOO_LARGE")
    body = response.read(maximum + 1)
    if len(body) > maximum:
        raise MarketTruthError("RESPONSE_TOO_LARGE")
    if declared is not None and int(declared) != len(body):
        raise MarketTruthError("RESPONSE_INVALID")
    return body


def _ts01_transport(maximum: int):
    import urllib.request

    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None

    def get(url, headers, timeout):
        request = urllib.request.Request(url, headers=dict(headers), method="GET")
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
        try:
            response = opener.open(request, timeout=timeout)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            return int(response.code), dict(response.headers), _ts01_bounded_body(response, maximum)

    return get


def _ts01_pair_link(gamma: RawEnvelope, book: RawEnvelope | None, market_id: str,
                    limits: AcquisitionLimits) -> str:
    market = _ts01_json(gamma.raw_bytes)
    if (not isinstance(market, dict) or isinstance(market.get("id"), bool)
            or not isinstance(market.get("id"), (str, int))
            or str(market["id"]) != market_id
            or not isinstance(market.get("conditionId"), str)
            or _CONDITION_RE.fullmatch(market["conditionId"]) is None):
        raise MarketTruthError("RESPONSE_INVALID")
    tokens = market.get("clobTokenIds")
    if isinstance(tokens, str):
        tokens = _ts01_json(tokens.encode("utf-8"))
    if (not isinstance(tokens, list) or not 1 <= len(tokens) <= 100
            or any(not isinstance(token, str) or not _TOKEN_RE.fullmatch(token) for token in tokens)
            or len(set(tokens)) != len(tokens)):
        raise MarketTruthError("RESPONSE_INVALID")
    token = tokens[0]
    if book is not None:
        document = _ts01_json(book.raw_bytes)
        if (not isinstance(document, dict) or document.get("asset_id") != token
                or document.get("market") != market["conditionId"]):
            raise MarketTruthError("RESPONSE_INVALID")
        for side in ("bids", "asks"):
            levels = document.get(side)
            if not isinstance(levels, list) or len(levels) > limits.max_book_levels_per_side:
                raise MarketTruthError("RESPONSE_INVALID")
            for level in levels:
                if (not isinstance(level, dict)
                        or not isinstance(level.get("price"), str)
                        or not isinstance(level.get("size"), str)
                        or canonical_decimal(level["price"]) is None
                        or canonical_decimal(level["size"]) is None
                        or not 0 <= __import__("decimal").Decimal(level["price"]) <= 1):
                    raise MarketTruthError("RESPONSE_INVALID")
    return token


def _ts01_paths(path):
    # Reuse the store's existing path validation without creating or opening it.
    store = MarketTruthStore(path)
    database = store._path
    receipt = database.with_suffix(".ts01.json")
    if receipt.is_symlink() or (receipt.exists() and (
        not receipt.is_file() or receipt.stat().st_nlink != 1
    )):
        raise MarketTruthError("STORE_CONFLICT")
    return database, receipt


def _ts01_verify(database, receipt, limits):
    with receipt.open("rb") as stream:
        payload = stream.read(_TS01_RECEIPT_BYTES + 1)
    if len(payload) > _TS01_RECEIPT_BYTES:
        raise MarketTruthError("RESPONSE_TOO_LARGE")
    document = _ts01_json(payload)
    if not isinstance(document, dict) or set(document) != {"body", "sha256"}:
        raise MarketTruthError("RESPONSE_INVALID")
    body = document["body"]
    if (not isinstance(body, dict) or set(body) != {
                "schema", "market_id", "token_id", "attempts", "selected", "transport_mode"}
            or body["schema"] != "ts01-local-producer-witness-v1"
            or body["transport_mode"] not in ("INJECTED", "NATIVE_HTTP")
            or sha256_hex(canonical_json_bytes(body)) != document["sha256"]
            or canonical_json_bytes(document) != payload):
        raise MarketTruthError("RESPONSE_INVALID")
    market_id = body["market_id"]
    if not isinstance(market_id, str) or _normalize_params("market-by-id", {"id": market_id}) != {"id": market_id}:
        raise MarketTruthError("RESPONSE_INVALID")
    attempts = body["attempts"]
    if not isinstance(attempts, list) or not 2 <= len(attempts) <= 2 * (limits.max_retries + 1):
        raise MarketTruthError("RESPONSE_INVALID")
    raw_rows = MarketTruthStore._read_raw_occurrences(
        database, [item["occurrence_id"] for item in attempts], limits,
    )
    selected = []
    previous_receive = ""
    phase = "market-by-id"
    attempt_index = 0
    success_rows = []
    ledger = []
    witness_fields = set(_TS01_RAW_FIELDS) | {
        "endpoint", "params", "url", "http_status", "request_started_at",
        "response_completed_at", "duration_ns",
    }
    for item, raw in zip(attempts, raw_rows):
        expected_params = {"id": market_id} if phase == "market-by-id" else {"token_id": body["token_id"]}
        normalized = _normalize_params(phase, expected_params)
        start, end = item["request_started_at"], item["response_completed_at"]
        status = item["http_status"]
        if (set(item) != witness_fields or item["endpoint"] != phase
                or item["params"] != normalized or item["url"] != _build_url(phase, normalized)[0]
                or any(item[key] != getattr(raw, key) for key in _TS01_RAW_FIELDS)
                or raw.source_kind != ("GAMMA" if phase == "market-by-id" else "CLOB")
                or raw.source_id != _SOURCE_ID[raw.source_kind] + phase
                or raw.source_cursor != f"http:{phase}:offset:0:attempt:{attempt_index}"
                or not is_rfc3339_micros(start) or not is_rfc3339_micros(end)
                or not previous_receive <= start <= end <= raw.received_at
                or not _is_int(item["duration_ns"]) or item["duration_ns"] < 0
                or not _is_int(status) or not 100 <= status <= 599):
            raise MarketTruthError("RESPONSE_INVALID")
        previous_receive = raw.received_at
        ledger.append({**item, "raw_bytes": raw.raw_bytes})
        if 200 <= status < 300:
            if _page_bound_error([_ts01_json(raw.raw_bytes)], phase, 1, limits) is not None:
                raise MarketTruthError("RESPONSE_INVALID")
            selected.append(raw.occurrence_id)
            success_rows.append(raw)
            if phase == "market-by-id":
                if _ts01_pair_link(raw, None, market_id, limits) != body["token_id"]:
                    raise MarketTruthError("RESPONSE_INVALID")
                phase = "book"
                attempt_index = 0
            else:
                phase = "complete"
        elif status in _RETRYABLE and attempt_index < limits.max_retries:
            attempt_index += 1
        else:
            raise MarketTruthError("RESPONSE_INVALID")
    if phase != "complete" or body["selected"] != selected or len(success_rows) != 2:
        raise MarketTruthError("RESPONSE_INVALID")
    _ts01_pair_link(*success_rows, market_id, limits)
    return {"status": "ADMITTED", "proof_level": "LOCAL_PRODUCER_WITNESS",
            "transport_mode": body["transport_mode"],
            "market_id": market_id, "token_id": body["token_id"],
            "receipt_sha256": document["sha256"], "attempts": ledger, "selected": selected}


def export_trusted_research_pair(path, *, limits: AcquisitionLimits | None = None) -> dict:
    """Cold reopen only; never create, repair, write or infer a missing receipt."""
    try:
        database, receipt = _ts01_paths(path)
        return _ts01_verify(database, receipt, limits or AcquisitionLimits())
    except Exception:
        return {"status": "NOT_ADMITTED", "error_code": "RESPONSE_INVALID"}


def collect_trusted_research_pair(
    path, market_id: str, *, transport=None, clock=None, limits: AcquisitionLimits | None = None,
) -> dict:
    """One foreground pair; injected transport proves software invariants only.

    A sidecar is a trusted local producer receipt, not tamper-proof attestation.
    Callers must protect it and the archive as operator evidence.
    """
    lock_fd = None
    temporary = None
    try:
        active = limits or AcquisitionLimits()
        normalized = _normalize_params("market-by-id", {"id": market_id})
        market_id = normalized["id"]
        database, receipt = _ts01_paths(path)
        lock = receipt.with_suffix(".lock")
        lock_fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        if receipt.exists():
            result = _ts01_verify(database, receipt, active)
            if result["market_id"] != market_id:
                raise MarketTruthError("STORE_CONFLICT")
            return result
        underlying = transport or _ts01_transport(active.max_response_bytes)

        def bounded(url, headers, timeout):
            status, response_headers, body = underlying(url, headers, timeout)
            if (not _is_int(status) or not 100 <= status <= 599
                    or not isinstance(body, bytes) or len(body) > active.max_response_bytes):
                raise MarketTruthError("RESPONSE_INVALID")
            return status, response_headers, body

        client = PublicMarketDataClient(active, transport=bounded, clock=clock)
        client._rate_limiter = RateLimiter(active)
        client._ts01_attempts = []
        successes = []
        with MarketTruthStore(database, active) as store:
            for endpoint in ("market-by-id", "book"):
                params = normalized if endpoint == "market-by-id" else {"token_id": token}
                page = client.get_page(endpoint, params)
                _, raw, terminal = archive_page_attempts(store, endpoint, page, 1, active)
                if terminal is not None or raw is None:
                    raise MarketTruthError("RESPONSE_INVALID")
                successes.append(raw)
                token = _ts01_pair_link(successes[0], None, market_id, active)
            _ts01_pair_link(*successes, market_id, active)
        body = {"schema": "ts01-local-producer-witness-v1", "market_id": market_id,
                "transport_mode": "INJECTED" if transport is not None else "NATIVE_HTTP",
                "token_id": token, "attempts": client._ts01_attempts,
                "selected": [raw.occurrence_id for raw in successes]}
        payload = canonical_json_bytes({"body": body, "sha256": sha256_hex(canonical_json_bytes(body))})
        if len(payload) > _TS01_RECEIPT_BYTES:
            raise MarketTruthError("RESPONSE_TOO_LARGE")
        fd, temporary = tempfile.mkstemp(prefix=".ts01-", dir=receipt.parent)
        with os.fdopen(fd, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        # Verify the staged receipt against the cold committed archive before promotion.
        result = _ts01_verify(database, pathlib.Path(temporary), active)
        if receipt.exists() or receipt.is_symlink():
            raise MarketTruthError("STORE_CONFLICT")
        os.rename(temporary, receipt)
        temporary = None
        if os.name != "nt":
            directory_fd = os.open(receipt.parent, os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        return result
    except Exception:
        return {"status": "NOT_ADMITTED", "error_code": "RESPONSE_INVALID"}
    finally:
        if temporary is not None:
            try:
                os.unlink(temporary)
            except OSError:
                pass  # A cleanup failure cannot leak an operator path via the API.
        if lock_fd is not None:
            os.close(lock_fd)
            try:
                os.unlink(lock)
            except OSError:
                pass  # A surviving admission lock fails closed on the next attempt.
