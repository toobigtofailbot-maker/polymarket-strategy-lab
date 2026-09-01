"""Read-only Polymarket public data adapter.

This module provides GET-only access to public Polymarket endpoints.
It uses Python standard library only (urllib, json).

PROHIBITED — this module must never contain:
- POST, PUT, PATCH, DELETE requests.
- Credentials, private keys, wallet keys, API tokens, mnemonics.
- Order methods of any kind (placement, cancellation, signing).
- Authenticated headers.
- Background loops or scheduled polling.
- Any trading or execution method.

See docs/polymarket_readonly_adapter_evaluation.md for the full decision record.
Endpoint contracts are NOT confirmed as stable production agreements.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Optional

from .errors import (
    PolymarketEndpointNotVerifiedError,
    PolymarketHTTPError,
    PolymarketReadOnlyError,
    PolymarketResponseError,
)
from .models import (
    AdapterResult,
    MarketSummary,
    OrderBookLevel,
    OrderBookSnapshot,
    ReadOnlyRequestInfo,
)

# Endpoint map with verification status.
# UNVERIFIED = endpoint path is derived from public documentation and repo audit
# but has not been confirmed against a live production response in this project.
# WP9 updated: three endpoints confirmed via controlled GET-only probes (2026-05-18).
# CLOB /health returned HTTP 404 and remains unverified.
_ENDPOINT_MAP = {
    "gamma_markets": {
        "base_url_key": "gamma_base_url",
        "path": "/markets",
        "verified": True,
        "verified_in_wp": "WP9",
        "verified_at_utc": "2026-05-18",
        "notes": (
            "HTTP 200. Returns a JSON list of market dicts. "
            "clobTokenIds field is a JSON-encoded string (not a Python list). "
            "outcomes and outcomePrices fields are also JSON-encoded strings. "
            "Correct identifier for /markets/{id} is the integer id field."
        ),
    },
    "gamma_market_by_id": {
        "base_url_key": "gamma_base_url",
        "path": "/markets/{identifier}",
        "verified": True,
        "verified_in_wp": "WP9",
        "verified_at_utc": "2026-05-18",
        "notes": (
            "HTTP 200. Returns a single market dict (same shape as list items). "
            "Identifier must be the integer id field (e.g. '540817'), not the conditionId hash. "
            "Using conditionId returns HTTP 422."
        ),
    },
    "clob_book": {
        "base_url_key": "clob_base_url",
        "path": "/book",
        "verified": True,
        "verified_in_wp": "WP9",
        "verified_at_utc": "2026-05-18",
        "notes": (
            "HTTP 200. Returns a dict with keys: asks, asset_id, bids, hash, "
            "last_trade_price, market, min_order_size, neg_risk, tick_size, timestamp. "
            "bids and asks are lists of {price, size} dicts (string values). "
            "token_id must be obtained by JSON-parsing the clobTokenIds field from /markets."
        ),
    },
    "clob_health": {
        "base_url_key": "clob_base_url",
        "path": "/health",
        "verified": False,
        "verified_in_wp": None,
        "verified_at_utc": None,
        "notes": (
            "WP9 probe returned HTTP 404. Endpoint does not respond at /health. "
            "Not confirmed for any production use. Kept in map as unverified candidate."
        ),
    },
    "gamma_markets_keyset": {
        "base_url_key": "gamma_base_url",
        "path": "/markets/keyset",
        "verified": False,
        "verified_in_wp": None,
        "verified_at_utc": None,
        "notes": (
            "Official Polymarket documentation checked 2026-08-30: GET-only Gamma "
            "keyset pagination endpoint. Documented limit range 1..100 (default 20); "
            "after_cursor accepts the previous next_cursor; offset is explicitly "
            "rejected. The response is a wrapper object with a markets list and an "
            "optional next_cursor omitted on the last page. NOT historically "
            "live-probed by this repo's WP9 process; documented-but-repo-unverified "
            "and gated behind an explicit opt-in before any real network use."
        ),
    },
}

DEFAULT_GAMMA_BASE_URL = "https://gamma-api.polymarket.com"
DEFAULT_CLOB_BASE_URL = "https://clob.polymarket.com"
DEFAULT_TIMEOUT_SECONDS = 10
DEFAULT_USER_AGENT = "polymarket-strategy-lab/wp9-contract-validation"


class PolymarketPublicClient:
    """Read-only client for public Polymarket market data endpoints.

    Performs GET-only requests. No credentials. No trading methods.
    All endpoint contracts are marked UNVERIFIED until confirmed.
    """

    def __init__(
        self,
        gamma_base_url: str = DEFAULT_GAMMA_BASE_URL,
        clob_base_url: str = DEFAULT_CLOB_BASE_URL,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        user_agent: str = DEFAULT_USER_AGENT,
        allow_unverified_endpoints: bool = True,
    ) -> None:
        self._gamma_base_url = gamma_base_url.rstrip("/")
        self._clob_base_url = clob_base_url.rstrip("/")
        self._timeout = timeout_seconds
        self._user_agent = user_agent
        self._allow_unverified = allow_unverified_endpoints

    def _base_url_for(self, key: str) -> str:
        if key == "gamma_base_url":
            return self._gamma_base_url
        if key == "clob_base_url":
            return self._clob_base_url
        raise ValueError(f"Unknown base URL key: {key!r}")

    def _get_json(
        self,
        base_url: str,
        path: str,
        query: Optional[dict[str, str]] = None,
        endpoint_key: str = "",
    ) -> tuple[object, ReadOnlyRequestInfo]:
        if query:
            path = path + "?" + urllib.parse.urlencode(query)
        url = base_url + path

        req = urllib.request.Request(
            url,
            method="GET",
            headers={"User-Agent": self._user_agent, "Accept": "application/json"},
        )

        start = time.monotonic()
        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                status = resp.status
                body = resp.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            latency_ms = (time.monotonic() - start) * 1000
            info = ReadOnlyRequestInfo(
                method="GET", url=url, status_code=exc.code, latency_ms=latency_ms
            )
            raise PolymarketHTTPError(exc.code, url, body) from exc
        except urllib.error.URLError as exc:
            raise PolymarketReadOnlyError(f"Network error fetching {url}: {exc}") from exc

        latency_ms = (time.monotonic() - start) * 1000
        info = ReadOnlyRequestInfo(
            method="GET", url=url, status_code=status, latency_ms=latency_ms
        )

        if status < 200 or status >= 300:
            raise PolymarketHTTPError(status, url, body)

        try:
            data = json.loads(body)
        except json.JSONDecodeError as exc:
            raise PolymarketResponseError(
                f"Non-JSON response from {url}: {body[:200]!r}"
            ) from exc

        return data, info

    def _check_endpoint_verified(self, endpoint_key: str) -> None:
        entry = _ENDPOINT_MAP.get(endpoint_key, {})
        if not entry.get("verified", False) and not self._allow_unverified:
            raise PolymarketEndpointNotVerifiedError(
                f"Endpoint {endpoint_key!r} is not confirmed as a stable production contract. "
                "Pass allow_unverified_endpoints=True to proceed anyway."
            )

    def get_markets(self, limit: Optional[int] = None) -> AdapterResult:
        """Fetch a list of market summaries from the Gamma API.

        Endpoint: GET /markets
        Contract status: UNVERIFIED — derived from public docs and WP2 audit.
        """
        self._check_endpoint_verified("gamma_markets")
        query: dict[str, str] = {}
        if limit is not None:
            query["limit"] = str(limit)
        data, info = self._get_json(
            self._gamma_base_url, "/markets", query=query or None, endpoint_key="gamma_markets"
        )
        return AdapterResult(data=data, request_info=info)

    def get_markets_keyset(
        self,
        *,
        limit: int = 100,
        after_cursor: Optional[str] = None,
    ) -> AdapterResult:
        """Fetch exactly ONE Gamma keyset page of markets.

        Endpoint: GET /markets/keyset
        Contract status: UNVERIFIED — documented 2026-08-30 but not live-probed by
        this repo. GET-only. The query always includes ``limit``; ``after_cursor``
        is included only when non-null. ``offset`` is NEVER sent. There is no
        automatic cursor loop; the caller receives the response ``next_cursor`` (if
        present) for a later manual invocation.
        """
        self._check_endpoint_verified("gamma_markets_keyset")
        query: dict[str, str] = {"limit": str(limit)}
        if after_cursor is not None:
            query["after_cursor"] = str(after_cursor)
        data, info = self._get_json(
            self._gamma_base_url,
            "/markets/keyset",
            query=query,
            endpoint_key="gamma_markets_keyset",
        )
        return AdapterResult(data=data, request_info=info)

    def get_market(self, identifier: str) -> AdapterResult:
        """Fetch metadata for a single market by condition_id or market_id.

        Endpoint: GET /markets/{identifier}
        Contract status: UNVERIFIED — derived from public docs and WP2 audit.
        """
        self._check_endpoint_verified("gamma_market_by_id")
        safe_id = urllib.parse.quote(str(identifier), safe="")
        data, info = self._get_json(
            self._gamma_base_url,
            f"/markets/{safe_id}",
            endpoint_key="gamma_market_by_id",
        )
        return AdapterResult(data=data, request_info=info)

    def get_order_book_snapshot(self, token_id: str) -> AdapterResult:
        """Fetch a read-only order-book snapshot for an outcome token.

        Endpoint: GET /book?token_id={token_id}
        Contract status: UNVERIFIED — derived from public docs and WP2 audit.

        Returns raw JSON. Use parse_order_book_snapshot() to get a typed model.
        """
        self._check_endpoint_verified("clob_book")
        data, info = self._get_json(
            self._clob_base_url,
            "/book",
            query={"token_id": str(token_id)},
            endpoint_key="clob_book",
        )
        return AdapterResult(data=data, request_info=info)

    def get_health(self) -> AdapterResult:
        """Fetch the CLOB API health status.

        Endpoint: GET /health
        Contract status: UNVERIFIED — derived from public docs and WP2 audit.
        """
        self._check_endpoint_verified("clob_health")
        data, info = self._get_json(
            self._clob_base_url, "/health", endpoint_key="clob_health"
        )
        return AdapterResult(data=data, request_info=info)

    @staticmethod
    def _parse_json_string_or_list(value: object) -> list:
        """Parse a value that may be a JSON-encoded string or already a list.

        WP9 finding: Gamma API returns clobTokenIds and outcomes as
        JSON-encoded strings (e.g. '["a","b"]'), not Python lists.
        """
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            stripped = value.strip()
            if stripped.startswith("["):
                try:
                    parsed = json.loads(stripped)
                    if isinstance(parsed, list):
                        return parsed
                except json.JSONDecodeError:
                    pass
        return []

    @staticmethod
    def parse_market_summary(raw: object) -> MarketSummary:
        """Parse a raw market dict into a MarketSummary.

        Raises PolymarketResponseError if required fields are missing.

        WP9 notes on actual field shapes:
        - clobTokenIds is a JSON-encoded string (e.g. '["token1","token2"]')
        - outcomes is a JSON-encoded string (e.g. '["Yes","No"]')
        - id is a string representation of an integer (e.g. '540817')
        - Use id (not conditionId) as the identifier for /markets/{id} lookups
        """
        if not isinstance(raw, dict):
            raise PolymarketResponseError(f"Expected dict, got {type(raw).__name__}")
        try:
            # WP9: clobTokenIds arrives as a JSON-encoded string
            raw_tokens = raw.get("tokens") or raw.get("clobTokenIds", [])
            token_list = PolymarketPublicClient._parse_json_string_or_list(raw_tokens)
            token_ids = tuple(
                str(t) if isinstance(t, str) else str(t.get("token_id", ""))
                for t in token_list
            )
            # WP9: outcomes also arrives as a JSON-encoded string
            raw_outcomes = raw.get("outcomes") or raw.get("outcomeLabels", [])
            outcomes = PolymarketPublicClient._parse_json_string_or_list(raw_outcomes)
            return MarketSummary(
                market_id=str(raw.get("id", raw.get("marketId", ""))),
                condition_id=str(raw.get("conditionId", raw.get("condition_id", ""))),
                question=str(raw.get("question", "")),
                market_status=str(raw.get("active", raw.get("status", "unknown"))),
                outcome_labels=tuple(str(o) for o in outcomes),
                token_ids=token_ids,
                resolution_date=raw.get("endDate", raw.get("resolutionDate")),
                category=raw.get("category"),
                raw=None,
            )
        except (KeyError, TypeError, AttributeError) as exc:
            raise PolymarketResponseError(f"Cannot parse MarketSummary: {exc}") from exc

    @staticmethod
    def parse_order_book_snapshot(
        token_id: str, raw: object, snapshot_timestamp: str, source_url: str
    ) -> OrderBookSnapshot:
        """Parse a raw order-book dict into an OrderBookSnapshot.

        Raises PolymarketResponseError if the structure is unexpected.
        Field names are based on WP2 audit; may differ from actual API response.
        """
        if not isinstance(raw, dict):
            raise PolymarketResponseError(f"Expected dict, got {type(raw).__name__}")
        try:
            bids = tuple(
                OrderBookLevel(price=str(b["price"]), size=str(b["size"]))
                for b in raw.get("bids", [])
            )
            asks = tuple(
                OrderBookLevel(price=str(a["price"]), size=str(a["size"]))
                for a in raw.get("asks", [])
            )
            return OrderBookSnapshot(
                token_id=str(token_id),
                bids=bids,
                asks=asks,
                snapshot_timestamp=snapshot_timestamp,
                source_url=source_url,
            )
        except (KeyError, TypeError) as exc:
            raise PolymarketResponseError(
                f"Cannot parse OrderBookSnapshot: {exc}"
            ) from exc
