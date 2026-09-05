"""WP169 Market WebSocket ingestion: book reconstruction, subscription control,
and the manual foreground WebSocket runner.

Import-safe, standard-library-only at import time (the optional ``websockets``
dependency is imported lazily only when a production connection is actually
opened; tests inject a connection factory instead). No import-time network,
thread, task, process, scheduler, or file side effect.
"""

from __future__ import annotations

import asyncio
import decimal
import json
import re
from collections.abc import Callable, Mapping, Sequence
from typing import AsyncContextManager

from .market_truth import (
    AcquisitionLimits,
    AcquisitionReceipt,
    BookApplyResult,
    BookFramePlan,
    BookStateTransition,
    Checkpoint,
    GAP_REASONS,
    MarketTruthError,
    NormalizedObservation,
    SubscriptionControlResult,
    SubscriptionUpdate,
    canonical_decimal,
    canonical_json_bytes,
    make_raw_envelope,
    normalize_websocket_message,
    rfc3339_to_epoch_ms,
    validate_asset_ids,
)
from .market_truth_data_api import NetworkBudgetExhausted, RateLimiter
from .market_truth_store import MarketTruthStore

MARKET_WS_URL = "wss://ws-subscriptions-clob.polymarket.com/ws/market"
_BACKOFF_SCHEDULE = (1, 2, 4, 8, 16, 30)
_DEFAULT_MAX_LEVELS = 5000
_CONDITION_RE = re.compile(r"^0x[0-9a-f]{64}$")
_OBS_ID_RE = re.compile(r"^markettruth:observation:sha256:[0-9a-f]{64}$")
_OCC_ID_RE = re.compile(r"^markettruth:occurrence:sha256:[0-9a-f]{64}$")
_MAX_SIZE = decimal.Decimal(10) ** 30
_ZERO = decimal.Decimal(0)
_ONE = decimal.Decimal(1)


def _dec(value: str) -> decimal.Decimal:
    return decimal.Decimal(value)


# ---------------------------------------------------------------------------
# Per-asset book reconstruction.
# ---------------------------------------------------------------------------


def _blank_asset() -> dict[str, object]:
    return {
        "state": "NOT_READY",
        "market_id": None,
        "last_timestamp_ms": None,
        "last_hash": None,
        "bids": {},
        "asks": {},
        "last_observation_id": None,
    }


class MarketBookState:
    """Deterministic decimal-only per-asset order-book reconstruction."""

    def __init__(self, asset_ids: Sequence[str]) -> None:
        validated = validate_asset_ids(asset_ids)
        self._assets: dict[str, dict[str, object]] = {}
        self._order: list[str] = []
        # Private effective per-side level cap (frozen default max_book_levels_per_side); the
        # runtime privately binds a stricter caller value without changing the public
        # signature. Standalone construction keeps the default.
        self._max_levels: int = _DEFAULT_MAX_LEVELS
        for asset_id in validated:
            self._assets[asset_id] = _blank_asset()
            self._order.append(asset_id)

    # -- membership ------------------------------------------------------
    _MAX_ASSETS = 500

    def subscribe(self, asset_ids: Sequence[str]) -> None:
        validated = validate_asset_ids(asset_ids)
        additions = [a for a in validated if a not in self._assets]
        # Cumulative dynamic membership must never exceed the 500-asset reusable API cap;
        # validate the POST-update total before any mutation.
        if len(self._assets) + len(additions) > self._MAX_ASSETS:
            raise MarketTruthError("INPUT_INVALID")
        for asset_id in additions:
            self._assets[asset_id] = _blank_asset()
            self._order.append(asset_id)

    def unsubscribe(self, asset_ids: Sequence[str]) -> None:
        validated = validate_asset_ids(asset_ids)
        for asset_id in validated:
            if asset_id in self._assets:
                del self._assets[asset_id]
                self._order.remove(asset_id)

    def mark_disconnect(self, received_at: str) -> None:
        for asset in self._assets.values():
            if asset["state"] == "READY":
                asset["state"] = "GAPPED"

    def is_ready(self, asset_id: str) -> bool:
        asset = self._assets.get(asset_id)
        return bool(asset is not None and asset["state"] == "READY")

    def _readiness(self) -> dict[str, bool]:
        return {a: (s["state"] == "READY") for a, s in self._assets.items()}

    def _subscribed_assets(self) -> tuple[str, ...]:
        """Current authoritative subscribed asset set in subscription order."""
        return tuple(self._order)

    # -- serialization ---------------------------------------------------
    def _asset_json(self, asset: Mapping[str, object]) -> dict[str, object]:
        bids = sorted(asset["bids"].items(), key=lambda kv: _dec(kv[0]), reverse=True)
        asks = sorted(asset["asks"].items(), key=lambda kv: _dec(kv[0]))
        return {
            "state": asset["state"],
            "market_id": asset["market_id"],
            "last_timestamp_ms": asset["last_timestamp_ms"],
            "last_hash": asset["last_hash"],
            "last_observation_id": asset["last_observation_id"],
            "bids": [[price, size] for price, size in bids],
            "asks": [[price, size] for price, size in asks],
        }

    def _state_dict(self) -> dict[str, object]:
        ordered = sorted(self._assets, key=lambda a: int(a))
        return {"assets": {a: self._asset_json(self._assets[a]) for a in ordered}}

    def snapshot_json(self) -> str:
        return canonical_json_bytes(self._state_dict()).decode("utf-8")

    # -- planning / commit ----------------------------------------------
    def plan(self, observations: Sequence[NormalizedObservation]) -> BookFramePlan:
        working = _clone(self._assets)
        _results, transitions = _apply_frame(working, observations, self._max_levels)
        planned = MarketBookState.__new__(MarketBookState)
        planned._assets = working
        planned._order = list(self._order)
        planned._max_levels = self._max_levels
        state_json = planned.snapshot_json()
        return BookFramePlan(
            observations=tuple(observations),
            transitions=tuple(transitions),
            state_json=state_json,
        )

    def commit(self, plan: BookFramePlan) -> tuple[BookApplyResult, ...]:
        results, _transitions = _apply_frame(self._assets, plan.observations, self._max_levels)
        return tuple(results)

    def discard(
        self, plan: BookFramePlan, reason: str = "STORAGE_FAILURE"
    ) -> tuple[BookApplyResult, ...]:
        # Closed vocabulary: reason must be a frozen gap/discard reason.
        if reason not in GAP_REASONS:
            raise MarketTruthError("INPUT_INVALID")
        affected: list[str] = []
        for obs in plan.observations:
            if obs.event_kind in ("book", "price_change") and obs.asset_id in self._assets:
                if obs.asset_id not in affected:
                    affected.append(obs.asset_id)
        results: list[BookApplyResult] = []
        for asset_id in affected:
            self._assets[asset_id]["state"] = "GAPPED"
            results.append(
                BookApplyResult(
                    status="GAPPED",
                    error_codes=("CONTINUITY_GAP",),
                    asset_id=asset_id,
                    ready=False,
                    gap_open=True,
                    applied=False,
                )
            )
        return tuple(results)

    @classmethod
    def from_checkpoint(cls, checkpoint: Checkpoint) -> "MarketBookState":
        # Recompute/verify the value hash, then validate EVERY frozen ws-checkpoint invariant
        # (exact keys, 1..500 unique ordered asset ids, ws key digest, exact per-asset schema,
        # domains, and level invariants) before any restore. Any violation -> STORE_CONFLICT,
        # no partial restore.
        from .market_truth import BOOK_STATES, compute_checkpoint_sha256

        expected_sha256 = compute_checkpoint_sha256(
            checkpoint_key=checkpoint.checkpoint_key,
            sequence=checkpoint.sequence,
            state=checkpoint.state,
            value_json=checkpoint.value_json,
            previous_sha256=checkpoint.previous_sha256,
        )
        if expected_sha256 != checkpoint.value_sha256:
            raise MarketTruthError("STORE_CONFLICT")
        try:
            value = json.loads(checkpoint.value_json)
        except ValueError:
            raise MarketTruthError("STORE_CONFLICT")
        if not isinstance(value, dict) or set(value) != {"asset_ids", "last_occurrence_id", "book_states"}:
            raise MarketTruthError("STORE_CONFLICT")
        asset_ids = value["asset_ids"]
        # 1..500 valid unique ordered token ids; the ws key must be derived from exactly them.
        try:
            validated = validate_asset_ids(asset_ids)
        except MarketTruthError:
            raise MarketTruthError("STORE_CONFLICT")
        if list(asset_ids) != list(validated) or checkpoint.checkpoint_key != _ws_checkpoint_key(asset_ids):
            raise MarketTruthError("STORE_CONFLICT")
        last_occurrence_id = value["last_occurrence_id"]
        if not (last_occurrence_id is None or (isinstance(last_occurrence_id, str) and _OCC_ID_RE.fullmatch(last_occurrence_id))):
            raise MarketTruthError("STORE_CONFLICT")
        book_states = value["book_states"]
        if not isinstance(book_states, dict) or set(book_states) != {"assets"}:
            raise MarketTruthError("STORE_CONFLICT")
        assets_obj = book_states["assets"]
        if not isinstance(assets_obj, dict) or set(assets_obj) != set(asset_ids):
            raise MarketTruthError("STORE_CONFLICT")
        instance = cls.__new__(cls)
        instance._assets = {}
        instance._order = []
        instance._max_levels = _DEFAULT_MAX_LEVELS
        for asset_id in asset_ids:
            entry = assets_obj[asset_id]
            if not isinstance(entry, dict) or set(entry) != {
                "state", "market_id", "last_timestamp_ms", "last_hash", "last_observation_id", "bids", "asks"
            }:
                raise MarketTruthError("STORE_CONFLICT")
            state = entry["state"]
            market_id = entry["market_id"]
            last_ms = entry["last_timestamp_ms"]
            last_hash = entry["last_hash"]
            last_obs = entry["last_observation_id"]
            if state not in BOOK_STATES:
                raise MarketTruthError("STORE_CONFLICT")
            if not (market_id is None or (isinstance(market_id, str) and _CONDITION_RE.fullmatch(market_id))):
                raise MarketTruthError("STORE_CONFLICT")
            if not (last_ms is None or (isinstance(last_ms, int) and not isinstance(last_ms, bool) and last_ms >= 0)):
                raise MarketTruthError("STORE_CONFLICT")
            if not (last_hash is None or (isinstance(last_hash, str) and last_hash != "")):
                raise MarketTruthError("STORE_CONFLICT")
            if not (last_obs is None or (isinstance(last_obs, str) and _OBS_ID_RE.fullmatch(last_obs))):
                raise MarketTruthError("STORE_CONFLICT")
            bids = _restore_side(entry["bids"], instance._max_levels)
            asks = _restore_side(entry["asks"], instance._max_levels)
            if bids is None or asks is None or _crossed(bids, asks):
                raise MarketTruthError("STORE_CONFLICT")
            instance._assets[asset_id] = {
                "state": state, "market_id": market_id, "last_timestamp_ms": last_ms,
                "last_hash": last_hash, "bids": bids, "asks": asks,
                "last_observation_id": last_obs,
            }
            instance._order.append(asset_id)
        return instance


def _restore_side(levels: object, max_levels: int = _DEFAULT_MAX_LEVELS) -> dict[str, str] | None:
    """Validate a serialized [[price,size],...] side on checkpoint restore, else None.

    Enforces canonical price/size, price in [0,1], size in (0, MAX], unique prices, and the
    per-side level cap -- the same invariants the live full-book applier enforces.
    """
    if not isinstance(levels, list) or len(levels) > max_levels:
        return None
    out: dict[str, str] = {}
    for level in levels:
        if not isinstance(level, (list, tuple)) or len(level) != 2:
            return None
        price = canonical_decimal(level[0])
        size = canonical_decimal(level[1])
        if price is None or size is None or price != level[0] or size != level[1]:
            return None
        if not (_ZERO <= _dec(price) <= _ONE) or not (_ZERO < _dec(size) <= _MAX_SIZE):
            return None
        if price in out:
            return None
        out[price] = size
    return out


def _clone(assets: Mapping[str, dict[str, object]]) -> dict[str, dict[str, object]]:
    out: dict[str, dict[str, object]] = {}
    for asset_id, state in assets.items():
        out[asset_id] = {
            "state": state["state"],
            "market_id": state["market_id"],
            "last_timestamp_ms": state["last_timestamp_ms"],
            "last_hash": state["last_hash"],
            "bids": dict(state["bids"]),
            "asks": dict(state["asks"]),
            "last_observation_id": state["last_observation_id"],
        }
    return out


def _apply_frame(
    assets: dict[str, dict[str, object]],
    observations: Sequence[NormalizedObservation],
    max_levels: int = _DEFAULT_MAX_LEVELS,
) -> tuple[list[BookApplyResult], list[BookStateTransition]]:
    order: list[str] = []
    from_states: dict[str, str] = {}
    last_result: dict[str, BookApplyResult] = {}
    for obs in observations:
        if obs.event_kind not in ("book", "price_change"):
            continue
        asset_id = obs.asset_id
        if asset_id is None or asset_id not in assets:
            continue
        if asset_id not in from_states:
            from_states[asset_id] = str(assets[asset_id]["state"])
            order.append(asset_id)
        result, reason = _apply_one(assets[asset_id], obs, max_levels)
        last_result[asset_id] = (result, reason)
    results = [last_result[a][0] for a in order]
    transitions = [
        BookStateTransition(
            asset_id=a,
            from_state=from_states[a],
            to_state=str(assets[a]["state"]),
            reason=last_result[a][1] or _transition_reason(last_result[a][0]),
        )
        for a in order
    ]
    return results, transitions


def _transition_reason(result: BookApplyResult) -> str:
    if result.status == "APPLIED":
        return "APPLIED"
    if result.status == "GAPPED":
        return result.error_codes[0] if result.error_codes else "CONTINUITY_GAP"
    if result.status == "NO_CHANGE":
        return "NO_CHANGE"
    return "REJECTED"


def _gap(
    asset: dict[str, object], asset_id: str, code: str, reason: str
) -> tuple[BookApplyResult, str]:
    asset["state"] = "GAPPED"
    return (
        BookApplyResult(
            status="GAPPED",
            error_codes=(code,),
            asset_id=asset_id,
            ready=False,
            gap_open=True,
            applied=False,
        ),
        reason,
    )


def _apply_one(
    asset: dict[str, object], obs: NormalizedObservation, max_levels: int = _DEFAULT_MAX_LEVELS
) -> tuple[BookApplyResult, str | None]:
    asset_id = obs.asset_id
    # Exact duplicate of the immediately prior observation.
    if obs.observation_id == asset["last_observation_id"]:
        return (
            BookApplyResult(
                status="NO_CHANGE",
                error_codes=(),
                asset_id=asset_id,
                ready=asset["state"] == "READY",
                gap_open=asset["state"] == "GAPPED",
                applied=False,
            ),
            None,
        )
    payload = json.loads(obs.canonical_payload_json)
    new_ms = rfc3339_to_epoch_ms(obs.event_time) if obs.event_time else None

    if obs.event_kind == "book":
        if obs.status != "ACCEPTED":
            return _gap(asset, asset_id, "EVENT_INVALID", "PARSE_FAULT")
        return _apply_full_book(asset, obs, payload, new_ms, max_levels)

    # price_change delta
    if asset["state"] != "READY":
        return (
            BookApplyResult(
                status="GAPPED" if asset["state"] == "GAPPED" else "NO_CHANGE",
                error_codes=("BOOK_GAP_ACTIVE",),
                asset_id=asset_id,
                ready=False,
                gap_open=asset["state"] == "GAPPED",
                applied=False,
            ),
            None,  # already gapped/not-ready: no new gap-open transition
        )
    if obs.status != "ACCEPTED":
        return _gap(asset, asset_id, "EVENT_INVALID", "PARSE_FAULT")
    return _apply_delta(asset, obs, payload, new_ms, max_levels)


def _validate_levels(raw_levels: object) -> dict[str, str] | None:
    if not isinstance(raw_levels, list):
        return None
    levels: dict[str, str] = {}
    for level in raw_levels:
        if not isinstance(level, (list, tuple)) or len(level) != 2:
            if isinstance(level, Mapping) and set(level) == {"price", "size"}:
                price = canonical_decimal(level.get("price"))
                size = canonical_decimal(level.get("size"))
            else:
                return None
        else:
            price = canonical_decimal(level[0])
            size = canonical_decimal(level[1])
        if price is None or size is None:
            return None
        if not (_ZERO <= _dec(price) <= _ONE):
            return None
        if not (_ZERO < _dec(size) <= _MAX_SIZE):
            return None
        if price in levels:
            return None
        levels[price] = size
    return levels


def _crossed(bids: Mapping[str, str], asks: Mapping[str, str]) -> bool:
    if not bids or not asks:
        return False
    best_bid = max(_dec(p) for p in bids)
    best_ask = min(_dec(p) for p in asks)
    return best_bid >= best_ask


def _apply_full_book(
    asset: dict[str, object],
    obs: NormalizedObservation,
    payload: Mapping[str, object],
    new_ms: int | None,
    max_levels: int = _DEFAULT_MAX_LEVELS,
) -> tuple[BookApplyResult, str | None]:
    bids = _validate_levels(payload.get("bids"))
    asks = _validate_levels(payload.get("asks"))
    if bids is None or asks is None:
        return _gap(asset, obs.asset_id, "EVENT_INVALID", "PARSE_FAULT")
    if len(bids) > max_levels or len(asks) > max_levels:
        return _gap(asset, obs.asset_id, "QUEUE_LIMIT_EXCEEDED", "QUEUE_OVERFLOW")
    if _crossed(bids, asks):
        return _gap(asset, obs.asset_id, "EVENT_INVALID", "PARSE_FAULT")
    asset["bids"] = bids
    asset["asks"] = asks
    asset["state"] = "READY"
    asset["market_id"] = obs.market_id
    asset["last_timestamp_ms"] = new_ms
    asset["last_hash"] = json.loads(obs.canonical_payload_json).get("hash")
    asset["last_observation_id"] = obs.observation_id
    return (
        BookApplyResult(
            status="APPLIED",
            error_codes=(),
            asset_id=obs.asset_id,
            ready=True,
            gap_open=False,
            applied=True,
        ),
        None,
    )


def _apply_delta(
    asset: dict[str, object],
    obs: NormalizedObservation,
    payload: Mapping[str, object],
    new_ms: int | None,
    max_levels: int = _DEFAULT_MAX_LEVELS,
) -> tuple[BookApplyResult, str | None]:
    last_ms = asset["last_timestamp_ms"]
    new_hash = payload.get("hash")
    # Timestamp regression / same-timestamp hash conflict -> exact gap reasons.
    if last_ms is not None and new_ms is not None:
        if new_ms < last_ms:
            return _gap(asset, obs.asset_id, "CONTINUITY_GAP", "TIMESTAMP_REGRESSION")
        if new_ms == last_ms and new_hash is not None and asset["last_hash"] is not None and new_hash != asset["last_hash"]:
            return _gap(asset, obs.asset_id, "CONTINUITY_GAP", "HASH_CONFLICT")
    price = canonical_decimal(payload.get("price"))
    size = canonical_decimal(payload.get("size"))
    side = payload.get("side")
    if price is None or size is None or side not in ("BUY", "SELL"):
        return _gap(asset, obs.asset_id, "CONTINUITY_GAP", "PARSE_FAULT")
    if not (_ZERO <= _dec(price) <= _ONE) or _dec(size) > _MAX_SIZE:
        return _gap(asset, obs.asset_id, "CONTINUITY_GAP", "PARSE_FAULT")
    # Atomicity: compute the mutation on a TRIAL copy of the affected side and validate
    # every invariant against it; only after all checks pass is the live book mutated. A
    # rejected delta must never leave a partial mutation committed (applied=False keeps the
    # last valid level set intact until a fresh full snapshot heals the gap).
    trial = dict(asset["bids"] if side == "BUY" else asset["asks"])
    changed = False
    if _dec(size) == _ZERO:
        if price not in trial:
            return _gap(asset, obs.asset_id, "CONTINUITY_GAP", "PARSE_FAULT")
        del trial[price]
        changed = True
    else:
        if trial.get(price) == size:
            changed = False  # redundant upsert -> NO_CHANGE but advance ts/hash
        else:
            trial[price] = size
            changed = True
    trial_bids = trial if side == "BUY" else asset["bids"]
    trial_asks = trial if side == "SELL" else asset["asks"]
    if len(trial_bids) > max_levels or len(trial_asks) > max_levels:
        return _gap(asset, obs.asset_id, "QUEUE_LIMIT_EXCEEDED", "QUEUE_OVERFLOW")
    if _crossed(trial_bids, trial_asks):
        return _gap(asset, obs.asset_id, "CONTINUITY_GAP", "PARSE_FAULT")
    # Provided best_bid / best_ask must equal reconstructed extrema when present.
    best_bid = payload.get("best_bid")
    best_ask = payload.get("best_ask")
    if best_bid is not None:
        recon = max((_dec(p) for p in trial_bids), default=None)
        if recon is None or _dec(canonical_decimal(best_bid) or "-1") != recon:
            return _gap(asset, obs.asset_id, "CONTINUITY_GAP", "PARSE_FAULT")
    if best_ask is not None:
        recon = min((_dec(p) for p in trial_asks), default=None)
        if recon is None or _dec(canonical_decimal(best_ask) or "-1") != recon:
            return _gap(asset, obs.asset_id, "CONTINUITY_GAP", "PARSE_FAULT")
    # All invariants hold: commit the validated trial side into the live book.
    if side == "BUY":
        asset["bids"] = trial
    else:
        asset["asks"] = trial
    asset["last_timestamp_ms"] = new_ms if new_ms is not None else last_ms
    if new_hash is not None:
        asset["last_hash"] = new_hash
    asset["last_observation_id"] = obs.observation_id
    if not changed:
        return (
            BookApplyResult(
                status="NO_CHANGE",
                error_codes=(),
                asset_id=obs.asset_id,
                ready=True,
                gap_open=False,
                applied=False,
            ),
            None,
        )
    return (
        BookApplyResult(
            status="APPLIED",
            error_codes=(),
            asset_id=obs.asset_id,
            ready=True,
            gap_open=False,
            applied=True,
        ),
        None,
    )


# ---------------------------------------------------------------------------
# Subscription controller (owns the bounded queue exclusively).
# ---------------------------------------------------------------------------


class SubscriptionController:
    """Owns an asyncio queue with a bounded size; callers never receive it."""

    def __init__(self, limits: AcquisitionLimits | None = None) -> None:
        self._limits = limits or AcquisitionLimits()
        self._queue: asyncio.Queue[SubscriptionUpdate] = asyncio.Queue(
            maxsize=self._limits.max_queue_items
        )
        self._overflowed = False
        # Private projected-membership binding: the intended subscribed set as updates are
        # submitted (before consumption). It lets submit reject state-relative no-ops
        # (duplicate subscribe / absent unsubscribe / >500 total) without a public signature
        # change; the runner seeds it with the initial book membership via _bind.
        self._projected: set[str] = set()

    def _bind(self, asset_ids: Sequence[str]) -> None:
        self._projected = set(asset_ids)

    def submit(self, update: SubscriptionUpdate) -> SubscriptionControlResult:
        if not isinstance(update, SubscriptionUpdate) or update.operation not in (
            "subscribe",
            "unsubscribe",
        ):
            return SubscriptionControlResult("REJECTED", ("INPUT_INVALID",), False, self._queue.qsize())
        try:
            validated = validate_asset_ids(update.asset_ids)
        except MarketTruthError:
            return SubscriptionControlResult("REJECTED", ("INPUT_INVALID",), False, self._queue.qsize())
        # State-relative no-op rejection against the projected membership: a subscribe that
        # adds nothing new, an unsubscribe of an absent asset, or a projected total over the
        # 500-asset cap is REJECTED / INPUT_INVALID with no wire send.
        if update.operation == "subscribe":
            additions = [a for a in validated if a not in self._projected]
            if not additions or len(self._projected) + len(additions) > MarketBookState._MAX_ASSETS:
                return SubscriptionControlResult("REJECTED", ("INPUT_INVALID",), False, self._queue.qsize())
            projected_delta = ("subscribe", additions)
        else:
            removals = [a for a in validated if a in self._projected]
            if not removals:
                return SubscriptionControlResult("REJECTED", ("INPUT_INVALID",), False, self._queue.qsize())
            projected_delta = ("unsubscribe", removals)
        try:
            self._queue.put_nowait(update)
        except asyncio.QueueFull:
            # QueueFull must not mutate the projection.
            self._overflowed = True
            return SubscriptionControlResult(
                "REJECTED", ("QUEUE_LIMIT_EXCEEDED",), False, self._queue.qsize()
            )
        op, assets = projected_delta
        if op == "subscribe":
            self._projected.update(assets)
        else:
            self._projected.difference_update(assets)
        return SubscriptionControlResult("QUEUED", (), True, self._queue.qsize())

    async def get(self) -> SubscriptionUpdate:
        return await self._queue.get()

    def overflowed(self) -> bool:
        return self._overflowed


# ---------------------------------------------------------------------------
# Manual foreground WebSocket runner.
# ---------------------------------------------------------------------------


def _initial_payload(asset_ids: Sequence[str]) -> str:
    return json.dumps(
        {"assets_ids": list(asset_ids), "type": "market", "custom_feature_enabled": True},
        separators=(",", ":"),
    )


async def run_market_websocket(
    asset_ids: Sequence[str],
    store: MarketTruthStore,
    stop_event: asyncio.Event,
    *,
    limits: AcquisitionLimits | None = None,
    websocket_url: str = MARKET_WS_URL,
    connection_factory: Callable[..., AsyncContextManager] | None = None,
    subscription_controller: SubscriptionController | None = None,
) -> AcquisitionReceipt:
    """Run one manual foreground Market WebSocket acquisition session (frozen signature).

    Delegates to the private implementation, which additionally carries the internal clock,
    heartbeat, and shared-rate-limiter seams used by the runtime and by tests.
    """
    return await _run_market_websocket(
        asset_ids, store, stop_event, limits=limits, websocket_url=websocket_url,
        connection_factory=connection_factory,
        subscription_controller=subscription_controller,
    )


async def _run_market_websocket(
    asset_ids: Sequence[str],
    store: MarketTruthStore,
    stop_event: asyncio.Event,
    *,
    limits: AcquisitionLimits | None = None,
    websocket_url: str = MARKET_WS_URL,
    connection_factory: Callable[..., AsyncContextManager] | None = None,
    subscription_controller: SubscriptionController | None = None,
    now: Callable[[], str] | None = None,
    heartbeat_waiter: Callable[[], "asyncio.Future | None"] | None = None,
    rate_limiter: RateLimiter | None = None,
) -> AcquisitionReceipt:
    """Manual foreground Market WebSocket acquisition session implementation."""
    active = limits or AcquisitionLimits()
    if websocket_url != MARKET_WS_URL:
        raise MarketTruthError("INPUT_INVALID")
    validated = validate_asset_ids(asset_ids)
    if connection_factory is None:
        connection_factory = _default_connection_factory
    clock = now or _default_clock

    async def _default_heartbeat() -> None:
        await asyncio.sleep(active.heartbeat_seconds)

    heartbeat = heartbeat_waiter or _default_heartbeat

    book = MarketBookState(validated)
    book._max_levels = active.max_book_levels_per_side  # honor a stricter caller cap
    if subscription_controller is not None:
        subscription_controller._bind(validated)  # projected-membership no-op rejection
    import uuid

    session_id = str(uuid.uuid4())  # frozen grammar: lowercase UUID4 session ids
    store.mark_session(session_id, "IDLE", clock())
    reconnect_attempts = 0
    frame_sequence = 0
    # Durable open-gap tracking: asset_id -> reason, to persist OPEN/HEALED transitions
    # without duplicate OPEN spam across the whole session.
    open_gaps: dict[str, str] = {}

    def _current() -> tuple[str, ...]:
        return book._subscribed_assets()

    while True:
        if stop_event.is_set():
            store.mark_session(session_id, "STOPPED", clock())
            _checkpoint_ws(store, _current(), book)
            return store.receipt("STOPPED", (), "CALLER_STOP")
        # #3: one shared foreground network budget; a connection attempt is a network
        # call. Exhaustion is the frozen terminal STOPPED / NETWORK_CALL_LIMIT.
        if rate_limiter is not None:
            try:
                rate_limiter.acquire("WS")
            except NetworkBudgetExhausted:
                store.mark_session(session_id, "STOPPED", clock())
                _checkpoint_ws(store, _current(), book)
                return store.receipt("STOPPED", (), "NETWORK_CALL_LIMIT")
        store.mark_session(session_id, "CONNECTING", clock())
        try:
            async with connection_factory(websocket_url, active.max_frame_bytes) as socket:
                store.mark_session(session_id, "STREAMING", clock())
                # #5: reconnect/resubscribe the CURRENT authoritative asset set.
                await socket.send(_initial_payload(_current()))
                outcome = await _stream(
                    socket, store, book, stop_event, active, session_id, clock,
                    subscription_controller, frame_sequence, heartbeat, open_gaps,
                )
                frame_sequence = outcome["frame_sequence"]
                if outcome["terminal"] == "STOP":
                    store.mark_session(session_id, "STOPPED", clock())
                    _checkpoint_ws(store, _current(), book)
                    return store.receipt("STOPPED", (), "CALLER_STOP")
                if outcome["terminal"] == "QUEUE":
                    # Queue overflow gaps ALL subscribed assets (READY and NOT_READY), each
                    # with durable OPEN QUEUE_OVERFLOW evidence, then the exact queue terminal.
                    _gap_all_assets(store, book, open_gaps, clock(), "QUEUE_OVERFLOW")
                    store.mark_session(session_id, "FAILED", clock())
                    _checkpoint_ws(store, _current(), book)
                    return store.receipt("FAILED", ("QUEUE_LIMIT_EXCEEDED",), "QUEUE_LIMIT")
                if outcome["terminal"] == "STORE":
                    store.mark_session(session_id, "FAILED", clock())
                    _checkpoint_ws(store, _current(), book)
                    return store.receipt("FAILED", ("STORE_LIMIT_EXCEEDED",), "STORE_LIMIT")
                if outcome["reset_backoff"]:
                    reconnect_attempts = 0
        except (ConnectionError, OSError, asyncio.IncompleteReadError, _WebSocketClosed):
            pass
        except Exception:
            # An unexpected (non connection-closed) exception is a closed terminal failure,
            # never an ordinary reconnect: sanitized FAILED / INTERNAL_CLOSED_FAILURE.
            store.mark_session(session_id, "FAILED", clock())
            try:
                _checkpoint_ws(store, _current(), book)
            except Exception:
                pass
            return store.receipt("FAILED", ("INTERNAL_CLOSED_FAILURE",), "NONE")
        # disconnect -> gap ready assets (persisted) -> reconnect wait
        _apply_disconnect(store, book, open_gaps, clock(), "DISCONNECT")
        store.mark_session(session_id, "RECONNECT_WAIT", clock())
        reconnect_attempts += 1
        if reconnect_attempts > active.max_reconnect_attempts:
            store.mark_session(session_id, "FAILED", clock())
            _checkpoint_ws(store, _current(), book)
            return store.receipt("FAILED", ("RETRY_EXHAUSTED",), "RECONNECT_LIMIT")
        if stop_event.is_set():
            store.mark_session(session_id, "STOPPED", clock())
            _checkpoint_ws(store, _current(), book)
            return store.receipt("STOPPED", (), "CALLER_STOP")
        delay = _BACKOFF_SCHEDULE[min(reconnect_attempts - 1, len(_BACKOFF_SCHEDULE) - 1)]
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=delay)
        except asyncio.TimeoutError:
            continue
        store.mark_session(session_id, "STOPPED", clock())
        _checkpoint_ws(store, _current(), book)
        return store.receipt("STOPPED", (), "CALLER_STOP")


def _apply_disconnect(
    store: MarketTruthStore,
    book: MarketBookState,
    open_gaps: dict[str, str],
    received_at: str,
    reason: str,
) -> None:
    """Gap every currently-ready asset on disconnect and persist an OPEN gap event."""
    was_ready = [asset for asset, ready in book._readiness().items() if ready]
    book.mark_disconnect(received_at)
    for asset in was_ready:
        if asset not in open_gaps:
            store.mark_gap(asset, "OPEN", reason, received_at)
            open_gaps[asset] = reason


def _gap_all_assets(
    store: MarketTruthStore,
    book: MarketBookState,
    open_gaps: dict[str, str],
    received_at: str,
    reason: str,
) -> None:
    """Gap EVERY subscribed asset (READY and NOT_READY) and persist an OPEN gap event for
    each not already open. Used by the queue-overflow terminal, where the contract makes all
    assets GAPPED (no asset may remain falsely READY)."""
    for asset in book._subscribed_assets():
        book._assets[asset]["state"] = "GAPPED"
        if asset not in open_gaps:
            store.mark_gap(asset, "OPEN", reason, received_at)
            open_gaps[asset] = reason


def _reconcile_gaps(
    store: MarketTruthStore,
    transitions: Sequence[BookStateTransition],
    open_gaps: dict[str, str],
    received_at: str,
) -> None:
    """Persist OPEN/HEALED gap events from book transitions without duplicate OPENs."""
    for transition in transitions:
        if transition.to_state == "GAPPED" and transition.asset_id not in open_gaps:
            reason = transition.reason if transition.reason in GAP_REASONS else "PARSE_FAULT"
            store.mark_gap(transition.asset_id, "OPEN", reason, received_at)
            open_gaps[transition.asset_id] = reason
        elif transition.to_state == "READY" and transition.asset_id in open_gaps:
            store.mark_gap(transition.asset_id, "HEALED", open_gaps[transition.asset_id], received_at)
            del open_gaps[transition.asset_id]


def _persist_discard_gaps(
    store: MarketTruthStore,
    discarded: Sequence[BookApplyResult],
    open_gaps: dict[str, str],
    received_at: str,
) -> None:
    """Persist OPEN STORAGE_FAILURE gap events for a storage-failure discard."""
    for result in discarded:
        if result.asset_id is not None and result.asset_id not in open_gaps:
            store.mark_gap(result.asset_id, "OPEN", "STORAGE_FAILURE", received_at)
            open_gaps[result.asset_id] = "STORAGE_FAILURE"


class _WebSocketClosed(Exception):
    pass


def _is_closed_exc(exc: BaseException) -> bool:
    """True for a connection-closed / network exception (ordinary reconnect); False for an
    unexpected internal exception (terminal INTERNAL_CLOSED_FAILURE). The websockets
    library's ConnectionClosed* / WebSocketException are matched by name so this module
    stays import-safe without importing websockets."""
    if isinstance(
        exc, (StopAsyncIteration, ConnectionError, OSError, asyncio.IncompleteReadError, EOFError)
    ):
        return True
    names = {klass.__name__ for klass in type(exc).__mro__}
    return bool(
        names
        & {"ConnectionClosed", "ConnectionClosedOK", "ConnectionClosedError", "WebSocketException"}
    )


async def _stream(
    socket,
    store: MarketTruthStore,
    book: MarketBookState,
    stop_event: asyncio.Event,
    limits: AcquisitionLimits,
    session_id: str,
    clock: Callable[[], str],
    controller: SubscriptionController | None,
    frame_sequence: int,
    heartbeat: Callable[[], "asyncio.Future | None"],
    open_gaps: dict[str, str],
) -> dict[str, object]:
    reset_backoff = False
    recv_task = asyncio.ensure_future(socket.recv())
    stop_task = asyncio.ensure_future(stop_event.wait())
    heartbeat_task = asyncio.ensure_future(heartbeat())
    sub_task = asyncio.ensure_future(controller.get()) if controller is not None else None

    def _cancel_all() -> None:
        for task in (recv_task, stop_task, heartbeat_task, sub_task):
            if task is not None and not task.done():
                task.cancel()

    try:
        while True:
            if controller is not None and controller.overflowed():
                _cancel_all()
                return {"terminal": "QUEUE", "frame_sequence": frame_sequence, "reset_backoff": reset_backoff}
            waits = {recv_task, stop_task, heartbeat_task}
            if sub_task is not None:
                waits.add(sub_task)
            done, _pending = await asyncio.wait(waits, return_when=asyncio.FIRST_COMPLETED)

            if stop_task in done:
                _cancel_all()
                return {"terminal": "STOP", "frame_sequence": frame_sequence, "reset_backoff": reset_backoff}

            # B: periodic outgoing PING at the certified heartbeat interval.
            if heartbeat_task in done:
                await socket.send("PING")
                heartbeat_task = asyncio.ensure_future(heartbeat())
                continue

            # A: consume one dynamic subscription update; send wire message then mutate
            # book membership only after a successful send. Invalid/no-op are dropped.
            if sub_task is not None and sub_task in done:
                update = sub_task.result()
                await _process_subscription_update(socket, book, update)
                sub_task = asyncio.ensure_future(controller.get())
                continue

            if recv_task in done:
                try:
                    message = recv_task.result()
                except Exception as exc:
                    _cancel_all()
                    if _is_closed_exc(exc):
                        raise _WebSocketClosed()
                    raise  # unexpected -> terminal INTERNAL_CLOSED_FAILURE at the runner
                recv_task = asyncio.ensure_future(socket.recv())
                if message is None:
                    _cancel_all()
                    raise _WebSocketClosed()
                if isinstance(message, str) and message.strip() in ("PONG", "PING"):
                    if message.strip() == "PING":
                        await socket.send("PONG")
                    continue
                raw_bytes = message.encode("utf-8") if isinstance(message, str) else bytes(message)
                # J: an oversize frame is a visible continuity fault. Do not store the
                # unbounded bytes; gap every currently ready asset and record gap events
                # so no book is left falsely READY.
                if len(raw_bytes) > limits.max_frame_bytes:
                    # J + item 9: an oversize frame is a continuity fault; gap ready assets,
                    # persist gap events, do not store the unbounded bytes, and leave STREAMING
                    # via the reconnect path (STREAMING -> RECONNECT_WAIT).
                    _apply_disconnect(store, book, open_gaps, clock(), "PARSE_FAULT")
                    _cancel_all()
                    return {"terminal": "RECONNECT", "frame_sequence": frame_sequence, "reset_backoff": reset_backoff}
                received_at = clock()
                cursor = f"ws:{session_id}:frame:{frame_sequence}"
                raw = make_raw_envelope(
                    "WS", "polymarket:market-ws", cursor, received_at, raw_bytes,
                    occurrence_sequence=frame_sequence, limits=limits,
                )
                frame_sequence += 1
                observations = normalize_websocket_message(raw, book_readiness=book._readiness())
                plan = book.plan(observations)
                receipt = store.append(raw, observations)
                if receipt.status == "FAILED" and "STORE_LIMIT_EXCEEDED" in receipt.error_codes:
                    discarded = book.discard(plan, "STORAGE_FAILURE")
                    _persist_discard_gaps(store, discarded, open_gaps, clock())
                    _cancel_all()
                    return {"terminal": "STORE", "frame_sequence": frame_sequence, "reset_backoff": reset_backoff}
                if receipt.status == "FAILED":
                    # A non-store-limit child-store failure (e.g. STORE_CONFLICT) gaps the
                    # affected assets and leaves STREAMING via the reconnect path rather than
                    # silently continuing on a gapped book; the raw occurrence remains.
                    discarded = book.discard(plan, "STORAGE_FAILURE")
                    _persist_discard_gaps(store, discarded, open_gaps, clock())
                    _cancel_all()
                    return {"terminal": "RECONNECT", "frame_sequence": frame_sequence, "reset_backoff": reset_backoff}
                results = book.commit(plan)
                # #6: persist OPEN/HEALED gap events for the frame's book transitions.
                _reconcile_gaps(store, plan.transitions, open_gaps, received_at)
                for result in results:
                    if result.applied and result.ready:
                        reset_backoff = True
                # Item 9: a NEW continuity gap (a READY asset transitioning to GAPPED via a
                # timestamp/hash/invalid-delta/parse fault) leaves STREAMING via the reconnect
                # path; the gapped asset stays GAPPED until a fresh accepted full snapshot.
                if any(
                    t.to_state == "GAPPED" and t.from_state != "GAPPED"
                    for t in plan.transitions
                ):
                    _cancel_all()
                    return {"terminal": "RECONNECT", "frame_sequence": frame_sequence, "reset_backoff": reset_backoff}
    finally:
        _cancel_all()


async def _process_subscription_update(
    socket, book: MarketBookState, update: SubscriptionUpdate
) -> None:
    readiness = book._readiness()
    if update.operation == "subscribe":
        new_assets = [a for a in update.asset_ids if a not in readiness]
        if not new_assets:
            return  # no-op: no wire send
        if len(readiness) + len(new_assets) > MarketBookState._MAX_ASSETS:
            return  # cumulative 500-asset cap exceeded: reject (no wire send, no mutation)
        await socket.send(
            json.dumps(
                {"assets_ids": list(new_assets), "operation": "subscribe", "type": "market"},
                separators=(",", ":"),
            )
        )
        book.subscribe(new_assets)  # NOT_READY only after successful send
    else:  # unsubscribe
        existing = [a for a in update.asset_ids if a in readiness]
        if not existing:
            return  # no-op
        await socket.send(
            json.dumps(
                {"assets_ids": list(existing), "operation": "unsubscribe", "type": "market"},
                separators=(",", ":"),
            )
        )
        book.unsubscribe(existing)  # removed only after successful send


def _checkpoint_ws(
    store: MarketTruthStore, asset_ids: Sequence[str], book: MarketBookState
) -> Checkpoint:
    key = _ws_checkpoint_key(asset_ids)
    value = {
        "asset_ids": list(asset_ids),
        "last_occurrence_id": None,
        "book_states": json.loads(book.snapshot_json()),
    }
    return store.write_checkpoint(key, value, "STOPPED")


def _ws_checkpoint_key(asset_ids: Sequence[str]) -> str:
    from .market_truth import sha256_hex

    digest = sha256_hex(canonical_json_bytes(list(asset_ids)))
    return "ws:market:assets:sha256:" + digest


def _default_clock() -> str:
    import datetime

    moment = datetime.datetime.now(datetime.timezone.utc)
    return f"{moment:%Y-%m-%dT%H:%M:%S}.{moment.microsecond:06d}Z"


def _default_connection_factory(url: str, max_size: int):  # pragma: no cover - network
    import websockets

    return websockets.connect(url, max_size=max_size)
