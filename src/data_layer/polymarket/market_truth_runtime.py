"""WP169 manual foreground market-truth runtime orchestration.

Starts the Market WebSocket plus bounded periodic public HTTPS / Polygon RPC
acquisition in one asyncio task group, shares a single stop event and network
budget, and returns one deterministically aggregated receipt. There is no OS
scheduler, daemon, installed service, child process, import-time task, or
unbounded sleep/retry: every loop is interruptible by the shared stop event and
bounded by an explicit caller duration.
"""

from __future__ import annotations

import asyncio
import json
import re
from collections.abc import Callable, Mapping

from .market_truth import (
    AcquisitionLimits,
    AcquisitionReceipt,
    MarketTruthError,
    MarketTruthRuntimeConfig,
    normalize_public_record,
    order_error_codes,
    validate_asset_ids,
)
from .market_truth_data_api import (
    NetworkBudgetExhausted,
    PublicMarketDataClient,
    RateLimiter,
    archive_page_attempts,
    collect_public_page,
)
from .market_truth_store import MarketTruthStore
from .market_truth_websocket import _run_market_websocket, run_market_websocket

_WALLET_RE = re.compile(r"^0x[0-9a-f]{40}$")
_CONDITION_RE = re.compile(r"^0x[0-9a-f]{64}$")

def _failed(code: str) -> AcquisitionReceipt:
    return AcquisitionReceipt(
        status="FAILED",
        error_codes=(code,),
        raw_count=0,
        normalized_count=0,
        quarantined_count=0,
        gap_count=0,
        checkpoint_sequence=0,
        store_bytes=0,
        stop_reason="NONE",
    )


def _validate_config(config: MarketTruthRuntimeConfig, limits: AcquisitionLimits) -> str | None:
    if not isinstance(config, MarketTruthRuntimeConfig):
        return "INPUT_INVALID"
    has_assets = bool(config.asset_ids)
    if has_assets == config.discover_active:
        return "INPUT_INVALID"
    if has_assets:
        try:
            validate_asset_ids(config.asset_ids, maximum=100)
        except MarketTruthError:
            return "INPUT_INVALID"
    if not isinstance(config.duration_seconds, int) or isinstance(config.duration_seconds, bool):
        return "INPUT_INVALID"
    if not 1 <= config.duration_seconds <= limits.max_runtime_seconds:
        return "INPUT_INVALID"
    if not isinstance(config.max_pages, int) or not 1 <= config.max_pages <= limits.max_pages:
        return "INPUT_INVALID"
    if not isinstance(config.onchain_lookback_blocks, int) or not 1 <= config.onchain_lookback_blocks <= limits.max_block_span:
        return "INPUT_INVALID"
    if config.wallet is not None and _WALLET_RE.fullmatch(config.wallet) is None:
        return "INPUT_INVALID"
    if config.condition_id is not None and _CONDITION_RE.fullmatch(config.condition_id) is None:
        return "INPUT_INVALID"
    fb, tb = config.from_block, config.to_block
    if (fb is None) != (tb is None):
        return "INPUT_INVALID"
    if fb is not None:
        if not all(isinstance(v, int) and not isinstance(v, bool) for v in (fb, tb)):
            return "INPUT_INVALID"
        if fb < 0 or tb < fb or (tb - fb + 1) > limits.max_block_span:
            return "INPUT_INVALID"
    if config.rpc_provider != "drpc":
        return "RPC_PROVIDER_FORBIDDEN"
    return None


def _discover_active_market(
    client: PublicMarketDataClient,
    store: MarketTruthStore,
    max_pages: int,
    stop_event: asyncio.Event,
) -> tuple[tuple[str, ...], str] | AcquisitionReceipt | None:
    """Return the first eligible active market as (asset_ids, condition_id), a terminal
    AcquisitionReceipt on a store/budget/response failure, or None on exhaustion.

    Uses the SAME shared raw-first / store-failure / page-bound implementation as
    collect_public_page (archive_page_attempts), rather than a bespoke archive loop.
    """
    for page in range(max_pages):
        if stop_event.is_set():
            return None
        result = client.get_page(
            "markets", {"limit": 100, "offset": page * 100, "active": True, "closed": False}
        )
        records, raw, terminal = archive_page_attempts(
            store, "markets", result, 100, client._limits
        )
        if terminal is not None:
            return terminal  # store/budget/response terminal propagates
        for index, record in enumerate(records):
            if not isinstance(record, Mapping):
                continue
            if record.get("active") is not True or record.get("closed") is not False:
                continue
            if record.get("acceptingOrders") is not True:
                continue
            condition = record.get("conditionId")
            if not isinstance(condition, str) or _CONDITION_RE.fullmatch(condition) is None:
                continue
            token_ids = _decode_token_ids(record.get("clobTokenIds"))
            if token_ids is None:
                continue
            # Normalize and store the SELECTED Gamma market as a dynamic_config observation
            # so it is available as certified PIT context/evidence, not raw-only. The raw
            # occurrence is already archived; the store is idempotent on the raw and simply
            # adds the normalized child (no double-count). A store failure here is terminal.
            selected = normalize_public_record(raw, endpoint="markets", record_index=index)
            append_receipt = store.append(raw, (selected,))
            if append_receipt.status != "OK":
                return append_receipt
            return token_ids, condition
    return None


def _decode_token_ids(value: object) -> tuple[str, ...] | None:
    if isinstance(value, str):
        try:
            decoded = json.loads(value)
        except ValueError:
            return None
    elif isinstance(value, list):
        decoded = value
    else:
        return None
    if not isinstance(decoded, list):
        return None
    try:
        return validate_asset_ids(decoded, maximum=100)
    except MarketTruthError:
        return None


async def run_market_truth_runtime(
    config: MarketTruthRuntimeConfig,
    stop_event: asyncio.Event,
    *,
    limits: AcquisitionLimits | None = None,
    websocket_runner: Callable | None = None,
) -> AcquisitionReceipt:
    """Run one manual bounded foreground market-truth acquisition (frozen signature).

    Delegates to the private implementation, which additionally carries the internal
    data/RPC transport, clock, and wait seams used by tests. The default production path
    performs the full certified Polygon RPC acquisition (no transport injection required).
    """
    return await _run_market_truth_runtime(
        config, stop_event, limits=limits, websocket_runner=websocket_runner,
    )


async def _run_market_truth_runtime(
    config: MarketTruthRuntimeConfig,
    stop_event: asyncio.Event,
    *,
    limits: AcquisitionLimits | None = None,
    websocket_runner: Callable | None = None,
    data_transport: Callable | None = None,
    rpc_transport: Callable | None = None,
    clock: Callable[[], str] | None = None,
    wait_fn: Callable | None = None,
) -> AcquisitionReceipt:
    """Manual bounded foreground market-truth acquisition implementation and aggregation."""
    active = limits or AcquisitionLimits()
    invalid = _validate_config(config, active)
    if invalid is not None:
        return _failed(invalid)

    try:
        store = MarketTruthStore(config.output_db, active)
        store.initialize()
    except MarketTruthError as error:
        return _failed(error.error_codes[0])

    internal_stop = asyncio.Event()
    duration_expired = {"value": False}

    async def watchdog() -> None:
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=config.duration_seconds)
        except asyncio.TimeoutError:
            duration_expired["value"] = True
        internal_stop.set()

    async def caller_bridge() -> None:
        await stop_event.wait()
        internal_stop.set()

    wait = wait_fn or _default_wait
    # One shared monotonic token bucket enforces the per-source rate caps and the single
    # foreground network-call budget across the HTTP and RPC surfaces.
    rate_limiter = RateLimiter(active)
    try:
        client = PublicMarketDataClient(active, transport=data_transport, clock=clock)
        # Attach the single shared foreground network budget via the private seam so the
        # public client signature stays exactly frozen.
        client._rate_limiter = rate_limiter
        asset_ids: tuple[str, ...] = tuple(config.asset_ids)
        condition_id = config.condition_id
        if config.discover_active:
            discovered = await asyncio.to_thread(
                _discover_active_market, client, store, config.max_pages, internal_stop
            )
            if discovered is None:
                store.close()
                return _failed("RESPONSE_INVALID")
            if isinstance(discovered, AcquisitionReceipt):
                # A store/budget/response terminal during discovery propagates exactly.
                store.close()
                return discovered
            asset_ids, condition_id = discovered

        receipts: list[AcquisitionReceipt] = []

        async def ws_task() -> None:
            if websocket_runner is not None:
                # An injected runner has the exact frozen run_market_websocket signature.
                receipt = await websocket_runner(
                    asset_ids, store, internal_stop, limits=active
                )
            else:
                # The default runner shares the single foreground network budget via the
                # private rate_limiter seam (kept off the frozen public signature).
                receipt = await _run_market_websocket(
                    asset_ids, store, internal_stop, limits=active, rate_limiter=rate_limiter
                )
            receipts.append(receipt)
            # Item 10: any terminal WS receipt is the first terminal outcome -> immediately
            # signal siblings to stop (no sibling may run a further cadence pass).
            if receipt.status in ("FAILED", "STOPPED"):
                internal_stop.set()

        async def data_loop() -> None:
            receipts.extend(
                await _run_recurring(
                    lambda: _data_pass(client, store, condition_id, config, internal_stop),
                    active.data_poll_seconds, internal_stop, wait,
                )
            )

        async def config_loop() -> None:
            receipts.extend(
                await _run_recurring(
                    lambda: _config_pass(client, store, asset_ids, condition_id, internal_stop),
                    active.clob_poll_seconds, internal_stop, wait,
                )
            )

        async def rpc_loop() -> None:
            receipts.extend(
                await _run_recurring(
                    lambda: _rpc_pass(store, config, active, rpc_transport, clock, rate_limiter),
                    active.rpc_poll_seconds, internal_stop, wait,
                )
            )

        async def _guard(coro) -> None:
            # First terminal outcome -> signal siblings to stop -> controlled cleanup. An
            # unexpected task exception is recorded as a sanitized FAILED receipt (no
            # traceback/raw text) AND immediately sets the shared stop so no sibling keeps
            # issuing network calls after a peer has died.
            try:
                await coro
            except MarketTruthError as error:
                internal_stop.set()
                receipts.append(store.receipt("FAILED", error.error_codes, "NONE"))
            except Exception:
                internal_stop.set()
                receipts.append(
                    store.receipt("FAILED", ("INTERNAL_CLOSED_FAILURE",), "NONE")
                )

        watch = asyncio.ensure_future(watchdog())
        bridge = asyncio.ensure_future(caller_bridge())
        await asyncio.gather(
            _guard(ws_task()), _guard(data_loop()), _guard(config_loop()), _guard(rpc_loop())
        )
        internal_stop.set()
        for task in (watch, bridge):
            task.cancel()
        await asyncio.gather(watch, bridge, return_exceptions=True)

        return _aggregate(store, receipts, stop_event, duration_expired["value"])
    finally:
        store.close()


async def _default_wait(poll_seconds: int, stop_event: asyncio.Event) -> bool:
    """Interruptible wait; returns True if the stop event fired before the interval."""
    try:
        await asyncio.wait_for(stop_event.wait(), timeout=poll_seconds)
        return True
    except asyncio.TimeoutError:
        return False


async def _run_recurring(
    pass_fn: Callable[[], AcquisitionReceipt],
    poll_seconds: int,
    stop_event: asyncio.Event,
    wait: Callable,
) -> list[AcquisitionReceipt]:
    """Immediate + recurring acquisition until stop; the blocking pass runs in a thread
    and the inter-pass wait is interruptible. The first terminal error propagates and
    signals siblings to stop. No OS scheduler/daemon is created."""
    receipts: list[AcquisitionReceipt] = []
    while True:
        # Run the immediate pass, then honor a stop signalled by any sibling's first terminal
        # outcome: this surface performs its one immediate pass but never a further cadence
        # pass once the shared stop is set.
        receipt = await asyncio.to_thread(pass_fn)
        receipts.append(receipt)
        # First terminal outcome (FAILED, or a STOPPED such as NETWORK_CALL_LIMIT)
        # halts recurrence and signals siblings to stop.
        if receipt.status in ("FAILED", "STOPPED"):
            stop_event.set()
            break
        if stop_event.is_set():
            break
        stopped = await wait(poll_seconds, stop_event)
        if stopped:
            break
    return receipts


def _combine_surface_receipts(
    store: MarketTruthStore, receipts: list[AcquisitionReceipt]
) -> AcquisitionReceipt:
    """Aggregate per-surface receipts: any FAILED -> FAILED via frozen precedence; else
    any STOPPED -> STOPPED with its stop reason; else OK. Counts come from the store."""
    errors: list[str] = []
    stop_reason: str | None = None
    for receipt in receipts:
        if receipt.status == "FAILED":
            errors.extend(receipt.error_codes)
        elif receipt.status == "STOPPED":
            stop_reason = receipt.stop_reason
    if errors:
        ordered = order_error_codes(errors)
        # Preserve the terminal stop_reason of the FAILED surface that produced the winning
        # error (e.g. STORE_LIMIT for a store bound) rather than discarding it as NONE.
        winning = ordered[0]
        failed_stop_reason = "NONE"
        for receipt in receipts:
            if receipt.status == "FAILED" and winning in receipt.error_codes and receipt.stop_reason != "NONE":
                failed_stop_reason = receipt.stop_reason
                break
        return store.receipt("FAILED", ordered, failed_stop_reason)
    if stop_reason is not None:
        return store.receipt("STOPPED", (), stop_reason)
    return store.receipt("OK", (), "NONE")


def _data_pass(
    client: PublicMarketDataClient,
    store: MarketTruthStore,
    condition_id,
    config: MarketTruthRuntimeConfig,
    stop_event: "asyncio.Event | None" = None,
) -> AcquisitionReceipt:
    """One DATA-surface acquisition pass. Every surface receipt is inspected; a terminal
    outcome stops the remaining calls in this pass and propagates deterministically. The
    shared stop is passed through so no new multi-page HTTP page starts after a terminal."""
    receipts: list[AcquisitionReceipt] = []
    wallet = config.wallet

    def run(endpoint: str, params: dict, max_pages: int = 1) -> bool:
        receipt = collect_public_page(
            client, store, endpoint, params, max_pages=max_pages, stop_event=stop_event
        )
        receipts.append(receipt)
        return receipt.status == "OK"

    # Single shared /trades: the same market filter is included with the user when both
    # a condition and a wallet are known (the /trades call is shared, never duplicated).
    if condition_id is not None or wallet is not None:
        trades_params: dict = {"limit": 100}
        if condition_id is not None:
            trades_params["market"] = condition_id
        if wallet is not None:
            trades_params["user"] = wallet
        if not run("trades", trades_params, config.max_pages):
            return _combine_surface_receipts(store, receipts)
    if condition_id is not None:
        if not run("holders", {"limit": 20, "market": condition_id}):
            return _combine_surface_receipts(store, receipts)
    if wallet is not None:
        # The known market filter is included in all three wallet surfaces.
        activity_params: dict = {"limit": 100, "user": wallet}
        positions_params: dict = {"limit": 100, "user": wallet}
        if condition_id is not None:
            activity_params["market"] = condition_id
            positions_params["market"] = condition_id
        if not run("activity", activity_params, config.max_pages):
            return _combine_surface_receipts(store, receipts)
        if not run("positions", positions_params, config.max_pages):
            return _combine_surface_receipts(store, receipts)
    return _combine_surface_receipts(store, receipts)


def _config_pass(
    client: PublicMarketDataClient,
    store: MarketTruthStore,
    asset_ids,
    condition_id,
    stop_event: "asyncio.Event | None" = None,
) -> AcquisitionReceipt:
    """One CLOB config acquisition pass. Terminal outcomes stop and propagate."""
    receipts: list[AcquisitionReceipt] = []

    def run(endpoint: str, params: dict) -> bool:
        receipt = collect_public_page(
            client, store, endpoint, params, max_pages=1, stop_event=stop_event
        )
        receipts.append(receipt)
        return receipt.status == "OK"

    for asset_id in asset_ids:
        if not run("book", {"token_id": asset_id}):
            return _combine_surface_receipts(store, receipts)
        if not run("fee-rate", {"token_id": asset_id}):
            return _combine_surface_receipts(store, receipts)
    if condition_id is not None:
        if not run("clob-market-info", {"condition_id": condition_id}):
            return _combine_surface_receipts(store, receipts)
    return _combine_surface_receipts(store, receipts)


def _rpc_pass(
    store: MarketTruthStore,
    config: MarketTruthRuntimeConfig,
    limits: AcquisitionLimits,
    rpc_transport,
    clock,
    rate_limiter,
) -> AcquisitionReceipt:
    """One Polygon RPC acquisition pass; resumes from the chain checkpoint each time.

    Every runtime invocation performs the certified Polygon chain checks and collection.
    The default production path resolves the real read-only RPC transport; a test may inject
    a fake transport. There is no silent skip path.
    """
    from . import market_truth_onchain as _oc

    transport = rpc_transport if rpc_transport is not None else _oc._default_rpc_transport
    url = _oc.validate_public_rpc_url(config.rpc_provider)
    try:
        if rate_limiter is not None:
            rate_limiter.acquire("POLYGON")
        chain_result, _r = _oc._rpc_call(
            transport, url, "eth_chainId", [], limits.request_timeout_seconds,
            limits.max_response_bytes,
        )
        if _oc._hex_to_int(chain_result) != _oc.POLYGON_CHAIN_ID:
            return store.receipt("FAILED", ("CHAIN_ID_MISMATCH",), "NONE")
        if rate_limiter is not None:
            rate_limiter.acquire("POLYGON")
        latest_result, _r2 = _oc._rpc_call(
            transport, url, "eth_blockNumber", [], limits.request_timeout_seconds,
            limits.max_response_bytes,
        )
        latest = _oc._hex_to_int(latest_result)
    except NetworkBudgetExhausted:
        # Shared budget spent: frozen terminal STOPPED / NETWORK_CALL_LIMIT.
        return store.receipt("STOPPED", (), "NETWORK_CALL_LIMIT")
    except MarketTruthError as error:
        return store.receipt("FAILED", error.error_codes, "NONE")
    if latest is None:
        return store.receipt("FAILED", ("RESPONSE_INVALID",), "NONE")
    if config.from_block is not None and config.to_block is not None:
        from_block, to_block = config.from_block, config.to_block
    else:
        from_block = max(0, latest - config.onchain_lookback_blocks + 1)
        to_block = latest
    try:
        return _oc._collect_order_filled_logs(
            config.rpc_provider, store, from_block, to_block, latest_block=latest,
            limits=limits, transport=transport, clock=clock, rate_limiter=rate_limiter,
        )
    except NetworkBudgetExhausted:
        return store.receipt("STOPPED", (), "NETWORK_CALL_LIMIT")


def _aggregate(
    store: MarketTruthStore,
    receipts,
    stop_event: asyncio.Event,
    duration_expired: bool,
) -> AcquisitionReceipt:
    errors: list[str] = []
    any_failed = False
    surface_stop_reasons: list[str] = []
    for receipt in receipts:
        if receipt.status == "FAILED":
            any_failed = True
            errors.extend(receipt.error_codes)
        elif receipt.status == "STOPPED" and receipt.stop_reason != "NONE":
            surface_stop_reasons.append(receipt.stop_reason)
    base = store.receipt()
    if any_failed:
        ordered = order_error_codes(errors)
        winning = ordered[0] if ordered else "INTERNAL_CLOSED_FAILURE"
        # Preserve the stop_reason from the surface receipt that produced the winning error,
        # rather than re-deriving from a code-only table. Each surface already sets the
        # spec-correct stop_reason at its own boundary: only the WS reconnect-exhaustion path
        # carries RECONNECT_LIMIT, while an HTTP/RPC RETRY_EXHAUSTED carries NONE.
        stop_reason = "NONE"
        for receipt in receipts:
            if receipt.status == "FAILED" and winning in receipt.error_codes and receipt.stop_reason != "NONE":
                stop_reason = receipt.stop_reason
                break
        return AcquisitionReceipt(
            status="FAILED",
            error_codes=ordered,
            raw_count=base.raw_count,
            normalized_count=base.normalized_count,
            quarantined_count=base.quarantined_count,
            gap_count=base.gap_count,
            checkpoint_sequence=base.checkpoint_sequence,
            store_bytes=base.store_bytes,
            stop_reason=stop_reason,
        )
    # No failure: an explicit resource terminal reported by a surface (NETWORK_CALL_LIMIT)
    # MUST be preserved and never overwritten with a fabricated DURATION_EXPIRED. Otherwise
    # caller stop, then duration.
    if "NETWORK_CALL_LIMIT" in surface_stop_reasons:
        stop_reason = "NETWORK_CALL_LIMIT"
    elif stop_event.is_set() and not duration_expired:
        stop_reason = "CALLER_STOP"
    else:
        stop_reason = "DURATION_EXPIRED"
    return AcquisitionReceipt(
        status="STOPPED",
        error_codes=(),
        raw_count=base.raw_count,
        normalized_count=base.normalized_count,
        quarantined_count=base.quarantined_count,
        gap_count=base.gap_count,
        checkpoint_sequence=base.checkpoint_sequence,
        store_bytes=base.store_bytes,
        stop_reason=stop_reason,
    )
