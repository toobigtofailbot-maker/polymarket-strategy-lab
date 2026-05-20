"""Manual finite read-only Polymarket public market-data runner."""

from __future__ import annotations

import dataclasses
import datetime
from typing import Callable, List, Optional, Protocol, Sequence

from .errors import PolymarketHTTPError, PolymarketReadOnlyError, PolymarketResponseError
from .models import AdapterResult
from .polling_policy import PollingPlanValidationResult, default_polling_policy, validate_polling_policy
from .public_client import PolymarketPublicClient
from .rate_limit_guard import RateLimitDecision, RateLimitGuard


class ReadonlyPollingClient(Protocol):
    def get_markets(self, limit: Optional[int] = None) -> AdapterResult:
        ...

    def get_order_book_snapshot(self, token_id: str) -> AdapterResult:
        ...


@dataclasses.dataclass(frozen=True)
class ReadonlyPollingRequest:
    endpoint_key: str
    label: str
    token_id: Optional[str] = None
    limit: Optional[int] = None

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)


@dataclasses.dataclass(frozen=True)
class ReadonlyPollingDecisionLog:
    request: ReadonlyPollingRequest
    decision: RateLimitDecision
    monotonic_time: float

    def to_dict(self) -> dict:
        return {
            "request": self.request.to_dict(),
            "decision": self.decision.to_dict(),
            "monotonic_time": self.monotonic_time,
        }


@dataclasses.dataclass(frozen=True)
class ReadonlyPollingOutcome:
    request: ReadonlyPollingRequest
    attempted: bool
    success: bool
    status_code: Optional[int]
    outcome: str
    detail: str = ""
    public_item_count: int = 0

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)


@dataclasses.dataclass(frozen=True)
class ReadonlyPollingRunConfig:
    allow_network: bool = False
    markets_limit: int = 3
    order_books_limit: int = 0
    token_ids: Sequence[str] = ()

    def __post_init__(self) -> None:
        if self.markets_limit < 0:
            raise ValueError("markets_limit must be non-negative")
        if self.order_books_limit < 0:
            raise ValueError("order_books_limit must be non-negative")
        object.__setattr__(self, "token_ids", tuple(str(token) for token in self.token_ids))


@dataclasses.dataclass(frozen=True)
class ReadonlyPollingRunSummary:
    started_at_utc: str
    completed_at_utc: str
    allow_network: bool
    dry_run: bool
    policy_validation: dict
    requested_markets_limit: int
    requested_order_books_limit: int
    planned_request_list: List[ReadonlyPollingRequest]
    guard_decisions: List[ReadonlyPollingDecisionLog]
    outcomes: List[ReadonlyPollingOutcome]
    stopped_reason: str

    @property
    def attempted_request_count(self) -> int:
        return sum(1 for outcome in self.outcomes if outcome.attempted)

    @property
    def successful_request_count(self) -> int:
        return sum(1 for outcome in self.outcomes if outcome.success)

    def to_dict(self) -> dict:
        return {
            "started_at_utc": self.started_at_utc,
            "completed_at_utc": self.completed_at_utc,
            "allow_network": self.allow_network,
            "dry_run": self.dry_run,
            "policy_validation": self.policy_validation,
            "requested_markets_limit": self.requested_markets_limit,
            "requested_order_books_limit": self.requested_order_books_limit,
            "planned_request_list": [request.to_dict() for request in self.planned_request_list],
            "guard_decisions": [decision.to_dict() for decision in self.guard_decisions],
            "outcomes": [outcome.to_dict() for outcome in self.outcomes],
            "attempted_request_count": self.attempted_request_count,
            "successful_request_count": self.successful_request_count,
            "stopped_reason": self.stopped_reason,
        }


def build_readonly_polling_plan(config: ReadonlyPollingRunConfig) -> List[ReadonlyPollingRequest]:
    policy = default_polling_policy()
    gamma_policy = policy.endpoints["gamma_markets"]
    clob_policy = policy.endpoints["clob_book"]

    markets_limit = min(config.markets_limit, gamma_policy.max_markets_per_run)
    order_books_limit = min(
        config.order_books_limit,
        clob_policy.max_tokens_per_run,
        len(config.token_ids),
    )

    plan: List[ReadonlyPollingRequest] = []
    if markets_limit > 0:
        plan.append(
            ReadonlyPollingRequest(
                endpoint_key="gamma_markets",
                label="gamma_markets",
                limit=markets_limit,
            )
        )

    for token_id in config.token_ids[:order_books_limit]:
        if token_id:
            plan.append(
                ReadonlyPollingRequest(
                    endpoint_key="clob_book",
                    label="clob_book",
                    token_id=token_id,
                )
            )
    return plan


def run_readonly_polling(
    config: ReadonlyPollingRunConfig,
    *,
    client: Optional[ReadonlyPollingClient] = None,
    guard: Optional[RateLimitGuard] = None,
    now_provider: Optional[Callable[[], float]] = None,
    utcnow_provider: Optional[Callable[[], datetime.datetime]] = None,
) -> ReadonlyPollingRunSummary:
    policy = default_polling_policy()
    validation = validate_polling_policy(policy)
    plan = build_readonly_polling_plan(config)
    rate_guard = guard or RateLimitGuard(policy.endpoint_budgets())
    monotonic_now = now_provider or (lambda: 0.0)
    utc_now = utcnow_provider or (lambda: datetime.datetime.now(datetime.UTC))
    started_at = _format_utc(utc_now())

    decisions: List[ReadonlyPollingDecisionLog] = []
    outcomes: List[ReadonlyPollingOutcome] = []
    stopped_reason = "completed"

    if not validation.passed:
        stopped_reason = "policy_validation_failed"
    elif not config.allow_network:
        stopped_reason = "dry_run_no_network"
    else:
        active_client = client or PolymarketPublicClient()
        for request in plan:
            decision_time = float(monotonic_now())
            decision = rate_guard.record_allowed(request.endpoint_key, now=decision_time)
            decisions.append(
                ReadonlyPollingDecisionLog(
                    request=request,
                    decision=decision,
                    monotonic_time=decision_time,
                )
            )
            if not decision.allowed:
                outcomes.append(
                    ReadonlyPollingOutcome(
                        request=request,
                        attempted=False,
                        success=False,
                        status_code=None,
                        outcome="guard_denied",
                        detail=decision.reason,
                    )
                )
                continue

            outcome = _execute_request(active_client, request)
            outcomes.append(outcome)
            if outcome.outcome in {"http_429", "http_5xx", "network_error"}:
                stopped_reason = outcome.outcome
                break

    completed_at = _format_utc(utc_now())
    return ReadonlyPollingRunSummary(
        started_at_utc=started_at,
        completed_at_utc=completed_at,
        allow_network=config.allow_network,
        dry_run=not config.allow_network,
        policy_validation=_validation_to_dict(validation),
        requested_markets_limit=config.markets_limit,
        requested_order_books_limit=config.order_books_limit,
        planned_request_list=plan,
        guard_decisions=decisions,
        outcomes=outcomes,
        stopped_reason=stopped_reason,
    )


def _execute_request(
    client: ReadonlyPollingClient,
    request: ReadonlyPollingRequest,
) -> ReadonlyPollingOutcome:
    try:
        if request.endpoint_key == "gamma_markets":
            result = client.get_markets(limit=request.limit)
        elif request.endpoint_key == "clob_book" and request.token_id:
            result = client.get_order_book_snapshot(request.token_id)
        else:
            return ReadonlyPollingOutcome(
                request=request,
                attempted=False,
                success=False,
                status_code=None,
                outcome="unsupported_request",
                detail=request.endpoint_key,
            )
    except PolymarketHTTPError as exc:
        if exc.status == 429:
            label = "http_429"
        elif 500 <= exc.status <= 599:
            label = "http_5xx"
        else:
            label = "http_error"
        return ReadonlyPollingOutcome(
            request=request,
            attempted=True,
            success=False,
            status_code=exc.status,
            outcome=label,
            detail=f"HTTP {exc.status}",
        )
    except (PolymarketReadOnlyError, PolymarketResponseError, OSError) as exc:
        return ReadonlyPollingOutcome(
            request=request,
            attempted=True,
            success=False,
            status_code=None,
            outcome="network_error",
            detail=type(exc).__name__,
        )

    return ReadonlyPollingOutcome(
        request=request,
        attempted=True,
        success=True,
        status_code=result.request_info.status_code,
        outcome="success",
        detail=result.read_only_provenance,
        public_item_count=_public_item_count(result.data),
    )


def _public_item_count(data: object) -> int:
    if isinstance(data, list):
        return len(data)
    if isinstance(data, dict):
        return 1
    return 0


def _validation_to_dict(validation: PollingPlanValidationResult) -> dict:
    return validation.to_dict()


def _format_utc(value: datetime.datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=datetime.UTC)
    return value.astimezone(datetime.UTC).isoformat().replace("+00:00", "Z")
