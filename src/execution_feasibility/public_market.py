"""Bounded, unauthenticated, GET-only current public Gamma/CLOB acquisition.

Exactly two fixed-host HTTPS GETs per explicit foreground call (Gamma market, then the
CLOB book), no redirects, no retries, no backoff, no session state, no credential
headers and capped body reads. This module never evaluates feasibility, never touches account
state and has no order, execution or live authority. Transport and body failures become
closed source states and diagnostics; raw upstream text is never echoed.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
import hashlib
import http.client
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request

from .models import (
    _PENDING_ID,
    MAX_BOOK_LEVELS,
    MAX_JSON_DEPTH,
    MAX_JSON_NODES,
    MAX_SECONDS_DELAY,
    MAX_STRING_CHARS,
    MAX_TIME_NS,
    ExecutionFeasibilityError,
    PublicExecutionVenueSnapshot,
    observed_decimal_text,
    order_diagnostics,
    validate_condition_id,
    validate_gamma_market_id,
    validate_token_id,
)

GAMMA_HOST = "gamma-api.polymarket.com"
CLOB_HOST = "clob.polymarket.com"
ALLOWED_HOSTS = (GAMMA_HOST, CLOB_HOST)
REQUEST_TIMEOUT_S = 5
GAMMA_MAX_BYTES = 1_048_576
CLOB_MAX_BYTES = 4_194_304
MAX_REQUESTS_PER_ACQUISITION = 2

_BODY = "BODY"
_UNAVAILABLE = "UNAVAILABLE"
_OVERSIZE = "OVERSIZE"
_PLAIN_DECIMAL_RE = re.compile(r"-?[0-9]+(?:\.[0-9]+)?")
_DIGITS_RE = re.compile(r"[0-9]{1,19}")
_GAMMA_PATH_RE = re.compile(r"/markets/[0-9]{1,32}")
_CLOB_QUERY_RE = re.compile(r"token_id=[0-9]{1,100}")


@dataclass(frozen=True)
class SourceFetchResult:
    """Outcome of one capped public read; ``body`` is set only when outcome is BODY."""

    outcome: str
    body: bytes | None = None


class _Invalid(Exception):
    """Internal marker: the source body/shape/schema/identity is invalid."""

    def __init__(self, *codes: str) -> None:
        super().__init__()
        self.codes = codes


class _RedirectRejected(Exception):
    pass


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Reject every redirect; nothing is followed."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: D401
        raise _RedirectRejected()


def _default_opener():
    # An empty ProxyHandler disables proxy discovery from the process environment.
    return urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirectHandler())


def gamma_market_url(gamma_market_id: str) -> str:
    return f"https://{GAMMA_HOST}/markets/{validate_gamma_market_id(gamma_market_id)}"


def clob_book_url(token_id: str) -> str:
    return f"https://{CLOB_HOST}/book?" + urllib.parse.urlencode(
        {"token_id": validate_token_id(token_id)}
    )


def _check_request(url: str, method: str) -> None:
    """Fail closed unless the request is exactly one of the two authorized endpoint shapes.

    Gamma: GET https://gamma-api.polymarket.com/markets/<digits>, no query or fragment.
    CLOB:  GET https://clob.polymarket.com/book?token_id=<digits>, exactly that one parameter.
    Path, query, fragment, userinfo or port deviations are NETWORK_HOST_FORBIDDEN (endpoint).
    """

    if method != "GET":
        raise ExecutionFeasibilityError("NETWORK_METHOD_FORBIDDEN")
    parts = urllib.parse.urlsplit(url)
    if parts.scheme != "https":
        raise ExecutionFeasibilityError("NETWORK_SCHEME_FORBIDDEN")
    host = parts.hostname
    if host not in ALLOWED_HOSTS or parts.netloc not in (host, f"{host}:443") or "#" in url:
        raise ExecutionFeasibilityError("NETWORK_HOST_FORBIDDEN")
    if host == GAMMA_HOST:
        allowed = "?" not in url and _GAMMA_PATH_RE.fullmatch(parts.path) is not None
    else:
        allowed = parts.path == "/book" and _CLOB_QUERY_RE.fullmatch(parts.query) is not None
    if not allowed:
        raise ExecutionFeasibilityError("NETWORK_HOST_FORBIDDEN")


def public_get(url: str, *, max_bytes: int, opener=None, method: str = "GET") -> SourceFetchResult:
    """One capped GET; transport failures map to UNAVAILABLE, oversize bodies to OVERSIZE."""

    _check_request(url, method)
    request = urllib.request.Request(url, method="GET", headers={"Accept": "application/json"})
    active_opener = _default_opener() if opener is None else opener
    try:
        response = active_opener.open(request, timeout=REQUEST_TIMEOUT_S)
    except (_RedirectRejected, urllib.error.URLError, http.client.HTTPException, OSError,
            ValueError):
        return SourceFetchResult(_UNAVAILABLE)
    try:
        status = getattr(response, "status", None)
        if status != 200:
            return SourceFetchResult(_UNAVAILABLE)
        length = response.headers.get("Content-Length") if response.headers else None
        if length is not None and _DIGITS_RE.fullmatch(length.strip()) and int(length) > max_bytes:
            return SourceFetchResult(_OVERSIZE)
        body = response.read(max_bytes + 1)
        if not isinstance(body, bytes):
            return SourceFetchResult(_UNAVAILABLE)
        if len(body) > max_bytes:
            return SourceFetchResult(_OVERSIZE)
        return SourceFetchResult(_BODY, body)
    except (http.client.HTTPException, OSError, ValueError):
        return SourceFetchResult(_UNAVAILABLE)
    finally:
        close = getattr(response, "close", None)
        if close is not None:
            try:
                close()
            except (OSError, ValueError):
                pass


# ---------------------------------------------------------------------------
# Decimal-preserving bounded JSON decode.
# ---------------------------------------------------------------------------


def _reject_constant(_token: str) -> object:
    raise _Invalid()


def _no_duplicates(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise _Invalid()
        result[key] = value
    return result


def _check_bounds(value: object, depth: int, counter: list[int]) -> None:
    counter[0] += 1
    if counter[0] > MAX_JSON_NODES:
        raise _Invalid()
    # Same nesting bound as canonical records: at most 12 container levels.
    if isinstance(value, (list, dict)) and depth >= MAX_JSON_DEPTH:
        raise _Invalid()
    if isinstance(value, str) and len(value) > MAX_STRING_CHARS:
        raise _Invalid()
    if isinstance(value, list):
        for item in value:
            _check_bounds(item, depth + 1, counter)
    elif isinstance(value, dict):
        for item in value.values():
            _check_bounds(item, depth + 1, counter)


def decode_public_json(body: bytes) -> object:
    try:
        decoded = json.loads(
            body.decode("utf-8"),
            parse_float=Decimal,
            parse_constant=_reject_constant,
            object_pairs_hook=_no_duplicates,
        )
    except (UnicodeDecodeError, ValueError, RecursionError):
        raise _Invalid() from None
    _check_bounds(decoded, 0, [0])
    return decoded


def _decimal(value: object) -> Decimal:
    if isinstance(value, bool):
        raise _Invalid()
    if isinstance(value, int):
        number = Decimal(value)
    elif isinstance(value, Decimal):
        number = value
    elif isinstance(value, str) and _PLAIN_DECIMAL_RE.fullmatch(value):
        number = Decimal(value)
    else:
        raise _Invalid()
    if not number.is_finite():
        raise _Invalid()
    return number


def _decimal_text(value: object, *, low: Decimal, high: Decimal | None = None,
                  low_inclusive: bool = False) -> str:
    number = _decimal(value)
    if number < low or (number == low and not low_inclusive):
        raise _Invalid()
    if high is not None and number >= high:
        raise _Invalid()
    try:
        return observed_decimal_text(number)
    except ExecutionFeasibilityError:
        raise _Invalid() from None


def _optional(document: dict, key: str, parse):
    value = document.get(key)
    return None if value is None else parse(value)


def _boolean(value: object) -> bool:
    if not isinstance(value, bool):
        raise _Invalid()
    return value


# ---------------------------------------------------------------------------
# Gamma / CLOB normalization.
# ---------------------------------------------------------------------------

_ZERO = Decimal(0)
_ONE = Decimal(1)


def _token_ids(value: object) -> list[str]:
    if isinstance(value, str):
        try:
            value = json.loads(value, parse_float=_reject_constant, parse_constant=_reject_constant)
        except (ValueError, _Invalid):
            raise _Invalid() from None
    if not isinstance(value, list) or not value or len(value) > 64:
        raise _Invalid()
    for item in value:
        try:
            validate_token_id(item)
        except ExecutionFeasibilityError:
            raise _Invalid() from None
    return value


def _fee_schedule(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        raise _Invalid()
    return {
        "fee_rate": _decimal_text(value.get("rate"), low=_ZERO, low_inclusive=True),
        "fee_exponent": _decimal_text(value.get("exponent"), low=_ZERO, low_inclusive=True),
        "fee_taker_only": _boolean(value.get("takerOnly")),
        "fee_rebate_rate": _optional(
            value, "rebateRate", lambda v: _decimal_text(v, low=_ZERO, low_inclusive=True)
        ),
    }


def _seconds_delay(value: object) -> int:
    number = _decimal(value)
    if number != number.to_integral_value() or not 0 <= number <= MAX_SECONDS_DELAY:
        raise _Invalid()
    return int(number)


def normalize_gamma_market(
    document: object, *, gamma_market_id: str, condition_id: str, token_id: str
) -> tuple[dict[str, object], tuple[str, ...]]:
    """Extract only the contract facts; identity must match exactly or the source is INVALID."""

    if not isinstance(document, dict):
        raise _Invalid()
    returned_id = document.get("id")
    if isinstance(returned_id, int) and not isinstance(returned_id, bool):
        returned_id = str(returned_id)
    if not isinstance(returned_id, str) or not isinstance(document.get("conditionId"), str):
        raise _Invalid()
    tokens = _token_ids(document.get("clobTokenIds"))
    if (returned_id != gamma_market_id or document["conditionId"] != condition_id
            or token_id not in tokens):
        raise _Invalid("SOURCE_IDENTITY_MISMATCH")
    facts: dict[str, object] = {
        "active": _optional(document, "active", _boolean),
        "closed": _optional(document, "closed", _boolean),
        "accepting_orders": _optional(document, "acceptingOrders", _boolean),
        "enable_order_book": _optional(document, "enableOrderBook", _boolean),
        "restricted": _optional(document, "restricted", _boolean),
        "gamma_neg_risk": _optional(document, "negRisk", _boolean),
        "gamma_tick_size": _optional(
            document, "orderPriceMinTickSize", lambda v: _decimal_text(v, low=_ZERO, high=_ONE)
        ),
        "gamma_min_order_notional_usd": _optional(
            document, "orderMinSize", lambda v: _decimal_text(v, low=_ZERO)
        ),
        "fees_enabled": _optional(document, "feesEnabled", _boolean),
        "seconds_delay": _optional(document, "secondsDelay", _seconds_delay),
        "fee_rate": None,
        "fee_exponent": None,
        "fee_taker_only": None,
        "fee_rebate_rate": None,
    }
    diagnostics: tuple[str, ...] = ()
    schedule = document.get("feeSchedule")
    if schedule is not None:
        try:
            facts.update(_fee_schedule(schedule))
        except _Invalid:
            diagnostics = ("FEE_CONFIG_UNKNOWN",)
    return facts, diagnostics


def _book_levels(value: object, *, descending: bool) -> tuple[tuple[str, str], ...]:
    if not isinstance(value, list) or len(value) > MAX_BOOK_LEVELS:
        raise _Invalid("BOOK_INVALID")
    parsed: dict[Decimal, tuple[str, str]] = {}
    for level in value:
        if not isinstance(level, dict) or set(level) != {"price", "size"}:
            raise _Invalid("BOOK_INVALID")
        try:
            price = _decimal_text(level["price"], low=_ZERO, high=_ONE)
            size = _decimal_text(level["size"], low=_ZERO)
        except _Invalid:
            raise _Invalid("BOOK_INVALID") from None
        key = Decimal(price)
        if key in parsed:
            raise _Invalid("BOOK_INVALID")
        parsed[key] = (price, size)
    return tuple(parsed[key] for key in sorted(parsed, reverse=descending))


def _last_trade_price(value: object) -> str | None:
    if value is None or value == "":
        return None
    if _decimal(value) > _ONE:
        raise _Invalid()
    return _decimal_text(value, low=_ZERO, low_inclusive=True)


_BOOK_KEYS = ("market", "asset_id", "timestamp", "hash", "bids", "asks", "min_order_size",
              "tick_size", "neg_risk", "last_trade_price")


def normalize_clob_book(
    document: object, *, condition_id: str, token_id: str
) -> dict[str, object]:
    """Normalize the public book: bids descending, asks ascending; never trust wire order."""

    if not isinstance(document, dict) or any(key not in document for key in _BOOK_KEYS):
        raise _Invalid()
    if not isinstance(document["market"], str) or not isinstance(document["asset_id"], str):
        raise _Invalid()
    if document["market"] != condition_id or document["asset_id"] != token_id:
        raise _Invalid("SOURCE_IDENTITY_MISMATCH")
    timestamp = document["timestamp"]
    if isinstance(timestamp, int) and not isinstance(timestamp, bool):
        timestamp = str(timestamp)
    if not isinstance(timestamp, str) or _DIGITS_RE.fullmatch(timestamp) is None:
        raise _Invalid()
    book_ns = int(timestamp) * 1_000_000
    book_hash = document["hash"]
    if book_ns > MAX_TIME_NS or not isinstance(book_hash, str) or not re.fullmatch(
        r"[0-9A-Za-z]{1,128}", book_hash
    ):
        raise _Invalid()
    bids = _book_levels(document["bids"], descending=True)
    asks = _book_levels(document["asks"], descending=False)
    if bids and asks and Decimal(bids[0][0]) >= Decimal(asks[0][0]):
        raise _Invalid("BOOK_INVALID")
    last = document["last_trade_price"]
    return {
        "book_condition_id": condition_id,
        "book_token_id": token_id,
        "book_timestamp_ns": book_ns,
        "book_hash": book_hash,
        "book_neg_risk": _boolean(document["neg_risk"]),
        "book_tick_size": _decimal_text(document["tick_size"], low=_ZERO, high=_ONE),
        "book_min_order_size_raw": _decimal_text(document["min_order_size"], low=_ZERO),
        "last_trade_price": _last_trade_price(last),
        "bids": bids,
        "asks": asks,
    }


_GAMMA_NULLS = {
    name: None
    for name in ("active", "closed", "accepting_orders", "enable_order_book", "restricted",
                 "gamma_neg_risk", "gamma_tick_size", "gamma_min_order_notional_usd",
                 "fees_enabled", "fee_rate", "fee_exponent", "fee_taker_only",
                 "fee_rebate_rate", "seconds_delay")
}
_CLOB_NULLS = {
    "book_condition_id": None, "book_token_id": None, "book_timestamp_ns": None,
    "book_hash": None, "book_neg_risk": None, "book_tick_size": None,
    "book_min_order_size_raw": None, "last_trade_price": None, "bids": (), "asks": (),
}


def _source(result: SourceFetchResult, label: str, normalize):
    """Return (state, payload_sha256, facts, diagnostics) for one source result."""

    if not isinstance(result, SourceFetchResult) or result.outcome not in (
        _BODY, _UNAVAILABLE, _OVERSIZE
    ):
        raise ExecutionFeasibilityError("INTERNAL_VALIDATION_FAILED")
    if result.outcome == _UNAVAILABLE:
        return "UNAVAILABLE", None, None, (f"SOURCE_{label}_UNAVAILABLE",)
    if result.outcome == _OVERSIZE or not isinstance(result.body, bytes):
        return "INVALID", None, None, (f"SOURCE_{label}_INVALID",)
    digest = hashlib.sha256(result.body).hexdigest()
    try:
        facts, extra = normalize(decode_public_json(result.body))
    except _Invalid as invalid:
        return "INVALID", digest, None, (f"SOURCE_{label}_INVALID", *invalid.codes)
    return "AVAILABLE", digest, facts, extra


def build_public_venue_snapshot(
    *,
    gamma_market_id: str,
    condition_id: str,
    token_id: str,
    acquisition_started_ns: int,
    acquisition_completed_ns: int,
    gamma: SourceFetchResult,
    clob: SourceFetchResult,
) -> PublicExecutionVenueSnapshot:
    """Pure, deterministic snapshot construction from explicit read results and clocks."""

    validate_gamma_market_id(gamma_market_id)
    validate_condition_id(condition_id)
    validate_token_id(token_id)
    gamma_state, gamma_sha, gamma_facts, gamma_codes = _source(
        gamma, "GAMMA", lambda doc: normalize_gamma_market(
            doc, gamma_market_id=gamma_market_id, condition_id=condition_id, token_id=token_id
        ),
    )
    clob_state, clob_sha, clob_facts, clob_codes = _source(
        clob, "CLOB", lambda doc: (
            normalize_clob_book(doc, condition_id=condition_id, token_id=token_id), ()
        ),
    )

    def assemble(state, facts, codes):
        return PublicExecutionVenueSnapshot(
            venue_snapshot_id=_PENDING_ID,  # type: ignore[arg-type]
            gamma_market_id=gamma_market_id,
            condition_id=condition_id,
            token_id=token_id,
            acquisition_started_ns=acquisition_started_ns,
            acquisition_completed_ns=acquisition_completed_ns,
            gamma_source_state=gamma_state,
            gamma_payload_sha256=gamma_sha,
            clob_source_state=state,
            clob_payload_sha256=clob_sha,
            **(gamma_facts or _GAMMA_NULLS),
            **(facts or _CLOB_NULLS),
            diagnostic_codes=order_diagnostics((*gamma_codes, *codes)),
        )

    try:
        return assemble(clob_state, clob_facts, clob_codes)
    except ExecutionFeasibilityError as error:
        if error.code != "LIMIT_EXCEEDED" or clob_state != "AVAILABLE":
            raise
    # A book too large for the bounded canonical record is an invalid public source.
    return assemble("INVALID", None, ("SOURCE_CLOB_INVALID", "BOOK_INVALID"))


def fetch_public_venue_snapshot(
    *,
    gamma_market_id: str,
    condition_id: str,
    token_id: str,
    opener=None,
    clock_ns=None,
) -> PublicExecutionVenueSnapshot:
    """One explicit foreground acquisition: Gamma GET then CLOB book GET, nothing else.

    Structurally invalid caller input raises before any network. ``opener`` and
    ``clock_ns`` are deterministic test seams; by default a no-redirect, no-proxy stdlib
    opener and ``time.time_ns`` are used.
    """

    gamma_url = gamma_market_url(gamma_market_id)
    validate_condition_id(condition_id)
    clob_url = clob_book_url(token_id)
    clock = time.time_ns if clock_ns is None else clock_ns
    active_opener = _default_opener() if opener is None else opener
    started = clock()
    gamma = public_get(gamma_url, max_bytes=GAMMA_MAX_BYTES, opener=active_opener)
    clob = public_get(clob_url, max_bytes=CLOB_MAX_BYTES, opener=active_opener)
    completed = clock()
    return build_public_venue_snapshot(
        gamma_market_id=gamma_market_id,
        condition_id=condition_id,
        token_id=token_id,
        acquisition_started_ns=started,
        acquisition_completed_ns=completed,
        gamma=gamma,
        clob=clob,
    )
