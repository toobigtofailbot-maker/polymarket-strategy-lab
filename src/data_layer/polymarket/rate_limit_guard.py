"""Deterministic local rate-limit guard for future read-only request planners.

This module is offline-only. It records local request-attempt timestamps and
returns structured allow/deny decisions. It does not execute requests, wait,
start recurring work, or create clients.
"""

from __future__ import annotations

import dataclasses
import time
from collections import defaultdict, deque
from typing import Deque, Dict, Iterable, Mapping, Optional


@dataclasses.dataclass(frozen=True)
class RateLimitWindow:
    """Maximum local attempts allowed inside a rolling time window."""

    max_requests: int
    window_seconds: float

    def validate(self) -> None:
        if self.max_requests <= 0:
            raise ValueError("max_requests must be positive")
        if self.window_seconds <= 0:
            raise ValueError("window_seconds must be positive")


@dataclasses.dataclass(frozen=True)
class EndpointBudget:
    """Local request budget for one endpoint key."""

    endpoint_key: str
    window: RateLimitWindow
    minimum_interval_seconds: float = 0.0
    burst_capacity: int = 1

    def validate(self) -> None:
        if not self.endpoint_key.strip():
            raise ValueError("endpoint_key must be non-empty")
        self.window.validate()
        if self.minimum_interval_seconds < 0:
            raise ValueError("minimum_interval_seconds must be non-negative")
        if self.burst_capacity <= 0:
            raise ValueError("burst_capacity must be positive")
        if self.burst_capacity > self.window.max_requests:
            raise ValueError("burst_capacity cannot exceed max_requests")


@dataclasses.dataclass(frozen=True)
class RateLimitDecision:
    """Structured local decision for a planned request attempt."""

    allowed: bool
    endpoint_key: str
    reason: str
    retry_after_seconds: float
    requests_in_window: int
    next_allowed_at: float

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)


@dataclasses.dataclass
class RateLimitState:
    """Current local timestamp state by endpoint key."""

    attempts_by_endpoint: Dict[str, Deque[float]] = dataclasses.field(
        default_factory=lambda: defaultdict(deque)
    )

    def reset(self, endpoint_key: Optional[str] = None) -> None:
        if endpoint_key is None:
            self.attempts_by_endpoint.clear()
            return
        self.attempts_by_endpoint.pop(endpoint_key, None)


class RateLimitGuard:
    """Offline guard that evaluates and records local request attempts."""

    def __init__(
        self,
        budgets: Iterable[EndpointBudget] | Mapping[str, EndpointBudget],
        *,
        state: Optional[RateLimitState] = None,
    ) -> None:
        if isinstance(budgets, Mapping):
            budget_values = list(budgets.values())
        else:
            budget_values = list(budgets)

        self._budgets: Dict[str, EndpointBudget] = {}
        for budget in budget_values:
            budget.validate()
            if budget.endpoint_key in self._budgets:
                raise ValueError(f"duplicate endpoint budget: {budget.endpoint_key}")
            self._budgets[budget.endpoint_key] = budget
        self.state = state or RateLimitState()

    @property
    def endpoint_keys(self) -> tuple[str, ...]:
        return tuple(sorted(self._budgets))

    def evaluate(self, endpoint_key: str, *, now: Optional[float] = None) -> RateLimitDecision:
        """Evaluate a planned attempt without recording it."""

        current_time = _now(now)
        budget = self._require_budget(endpoint_key)
        attempts = self.state.attempts_by_endpoint[endpoint_key]
        _prune_window(attempts, current_time, budget.window.window_seconds)

        requests_in_window = len(attempts)
        if not attempts:
            return RateLimitDecision(
                allowed=True,
                endpoint_key=endpoint_key,
                reason="first_request_allowed",
                retry_after_seconds=0.0,
                requests_in_window=0,
                next_allowed_at=current_time,
            )

        interval_next_at = attempts[-1] + budget.minimum_interval_seconds
        window_next_at = (
            attempts[0] + budget.window.window_seconds
            if requests_in_window >= budget.window.max_requests
            else current_time
        )
        burst_next_at = _burst_next_allowed_at(
            attempts=attempts,
            current_time=current_time,
            minimum_interval_seconds=budget.minimum_interval_seconds,
            burst_capacity=budget.burst_capacity,
        )
        next_allowed_at = max(interval_next_at, window_next_at, burst_next_at, current_time)

        if requests_in_window >= budget.window.max_requests:
            return _deny(
                endpoint_key=endpoint_key,
                reason="window_exhausted",
                current_time=current_time,
                next_allowed_at=next_allowed_at,
                requests_in_window=requests_in_window,
            )

        if current_time < interval_next_at and not _within_burst_capacity(
            attempts=attempts,
            current_time=current_time,
            minimum_interval_seconds=budget.minimum_interval_seconds,
            burst_capacity=budget.burst_capacity,
        ):
            return _deny(
                endpoint_key=endpoint_key,
                reason="minimum_interval_not_elapsed",
                current_time=current_time,
                next_allowed_at=next_allowed_at,
                requests_in_window=requests_in_window,
            )

        return RateLimitDecision(
            allowed=True,
            endpoint_key=endpoint_key,
            reason="allowed",
            retry_after_seconds=0.0,
            requests_in_window=requests_in_window,
            next_allowed_at=current_time,
        )

    def record_allowed(
        self,
        endpoint_key: str,
        *,
        now: Optional[float] = None,
    ) -> RateLimitDecision:
        """Evaluate and record an attempt only when the local guard allows it."""

        decision = self.evaluate(endpoint_key, now=now)
        if decision.allowed:
            self.state.attempts_by_endpoint[endpoint_key].append(_now(now))
        return decision

    def reset(self, endpoint_key: Optional[str] = None) -> None:
        self.state.reset(endpoint_key)

    def _require_budget(self, endpoint_key: str) -> EndpointBudget:
        try:
            return self._budgets[endpoint_key]
        except KeyError as exc:
            raise KeyError(f"unknown endpoint budget: {endpoint_key}") from exc


def _now(value: Optional[float]) -> float:
    return float(value if value is not None else time.monotonic())


def _prune_window(attempts: Deque[float], current_time: float, window_seconds: float) -> None:
    cutoff = current_time - window_seconds
    while attempts and attempts[0] <= cutoff:
        attempts.popleft()


def _deny(
    *,
    endpoint_key: str,
    reason: str,
    current_time: float,
    next_allowed_at: float,
    requests_in_window: int,
) -> RateLimitDecision:
    return RateLimitDecision(
        allowed=False,
        endpoint_key=endpoint_key,
        reason=reason,
        retry_after_seconds=max(0.0, next_allowed_at - current_time),
        requests_in_window=requests_in_window,
        next_allowed_at=next_allowed_at,
    )


def _within_burst_capacity(
    *,
    attempts: Deque[float],
    current_time: float,
    minimum_interval_seconds: float,
    burst_capacity: int,
) -> bool:
    if burst_capacity <= 1 or minimum_interval_seconds <= 0:
        return False
    burst_floor = current_time - minimum_interval_seconds
    recent_count = sum(1 for ts in attempts if ts > burst_floor)
    return recent_count < burst_capacity


def _burst_next_allowed_at(
    *,
    attempts: Deque[float],
    current_time: float,
    minimum_interval_seconds: float,
    burst_capacity: int,
) -> float:
    if burst_capacity <= 1 or minimum_interval_seconds <= 0:
        return current_time
    burst_floor = current_time - minimum_interval_seconds
    recent = [ts for ts in attempts if ts > burst_floor]
    if len(recent) < burst_capacity:
        return current_time
    return min(recent) + minimum_interval_seconds
