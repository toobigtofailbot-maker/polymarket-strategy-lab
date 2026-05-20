"""Offline polling policy for future public market-data request planners.

The budgets here are local safety budgets, not confirmed venue limits. WP16
does not add a runner and does not perform network I/O.
"""

from __future__ import annotations

import dataclasses
from typing import Dict, Iterable, List, Mapping, Optional

from .rate_limit_guard import EndpointBudget, RateLimitWindow


NETWORK_ENDPOINT_KEYS = frozenset(
    {
        "gamma_markets",
        "gamma_market_detail",
        "clob_book",
        "clob_price",
        "clob_spread",
        "clob_midpoint",
        "manual_snapshot_capture",
        "sandbox_probe",
    }
)


@dataclasses.dataclass(frozen=True)
class PollingEndpointPolicy:
    """Conservative local policy for one future endpoint class."""

    endpoint_key: str
    enabled_by_default: bool
    max_requests_per_window: int
    window_seconds: int
    minimum_interval_seconds: float
    max_markets_per_run: int = 0
    max_tokens_per_run: int = 0
    requires_explicit_network: bool = True
    allow_automated_loop: bool = False
    notes: str = ""

    def to_budget(self) -> EndpointBudget:
        return EndpointBudget(
            endpoint_key=self.endpoint_key,
            window=RateLimitWindow(
                max_requests=self.max_requests_per_window,
                window_seconds=float(self.window_seconds),
            ),
            minimum_interval_seconds=self.minimum_interval_seconds,
            burst_capacity=1,
        )

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)


@dataclasses.dataclass(frozen=True)
class PollingPolicy:
    """Collection of endpoint policies for offline validation."""

    policy_id: str
    description: str
    endpoints: Dict[str, PollingEndpointPolicy]
    wp8_d002_status: str = "OPEN"
    automated_polling_enabled: bool = False

    def endpoint_budgets(self) -> Dict[str, EndpointBudget]:
        return {key: policy.to_budget() for key, policy in self.endpoints.items()}

    def to_dict(self) -> dict:
        return {
            "policy_id": self.policy_id,
            "description": self.description,
            "wp8_d002_status": self.wp8_d002_status,
            "automated_polling_enabled": self.automated_polling_enabled,
            "endpoints": {
                key: endpoint.to_dict() for key, endpoint in sorted(self.endpoints.items())
            },
        }


@dataclasses.dataclass(frozen=True)
class PollingPlanIssue:
    """One offline policy validation issue."""

    severity: str
    code: str
    endpoint_key: str
    message: str

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)


@dataclasses.dataclass(frozen=True)
class PollingPlanValidationResult:
    """Result of offline polling policy validation."""

    passed: bool
    issues: List[PollingPlanIssue]

    @property
    def error_count(self) -> int:
        return sum(1 for issue in self.issues if issue.severity == "ERROR")

    @property
    def warning_count(self) -> int:
        return sum(1 for issue in self.issues if issue.severity == "WARNING")

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "issues": [issue.to_dict() for issue in self.issues],
        }


def default_polling_policy() -> PollingPolicy:
    """Return the conservative WP16 policy with every future endpoint disabled."""

    endpoints = {
        "gamma_markets": PollingEndpointPolicy(
            endpoint_key="gamma_markets",
            enabled_by_default=False,
            max_requests_per_window=6,
            window_seconds=60,
            minimum_interval_seconds=10.0,
            max_markets_per_run=25,
            requires_explicit_network=True,
            allow_automated_loop=False,
            notes="Manual bounded market-list checks only until public rate limits are confirmed.",
        ),
        "gamma_market_detail": PollingEndpointPolicy(
            endpoint_key="gamma_market_detail",
            enabled_by_default=False,
            max_requests_per_window=12,
            window_seconds=60,
            minimum_interval_seconds=5.0,
            max_markets_per_run=25,
            requires_explicit_network=True,
            allow_automated_loop=False,
            notes="Manual detail lookups must stay bounded and observable.",
        ),
        "clob_book": PollingEndpointPolicy(
            endpoint_key="clob_book",
            enabled_by_default=False,
            max_requests_per_window=10,
            window_seconds=60,
            minimum_interval_seconds=6.0,
            max_tokens_per_run=20,
            requires_explicit_network=True,
            allow_automated_loop=False,
            notes="Order-book reads require explicit network approval and local guard enforcement.",
        ),
        "clob_price": PollingEndpointPolicy(
            endpoint_key="clob_price",
            enabled_by_default=False,
            max_requests_per_window=12,
            window_seconds=60,
            minimum_interval_seconds=5.0,
            max_tokens_per_run=20,
            requires_explicit_network=True,
            allow_automated_loop=False,
            notes="Price reads remain disabled until a later bounded runner WP.",
        ),
        "clob_spread": PollingEndpointPolicy(
            endpoint_key="clob_spread",
            enabled_by_default=False,
            max_requests_per_window=12,
            window_seconds=60,
            minimum_interval_seconds=5.0,
            max_tokens_per_run=20,
            requires_explicit_network=True,
            allow_automated_loop=False,
            notes="Spread reads remain manual and bounded.",
        ),
        "clob_midpoint": PollingEndpointPolicy(
            endpoint_key="clob_midpoint",
            enabled_by_default=False,
            max_requests_per_window=12,
            window_seconds=60,
            minimum_interval_seconds=5.0,
            max_tokens_per_run=20,
            requires_explicit_network=True,
            allow_automated_loop=False,
            notes="Midpoint reads remain manual and bounded.",
        ),
        "manual_snapshot_capture": PollingEndpointPolicy(
            endpoint_key="manual_snapshot_capture",
            enabled_by_default=False,
            max_requests_per_window=3,
            window_seconds=60,
            minimum_interval_seconds=20.0,
            max_markets_per_run=10,
            max_tokens_per_run=20,
            requires_explicit_network=True,
            allow_automated_loop=False,
            notes="Existing capture tools stay manual; this policy does not convert them.",
        ),
        "sandbox_probe": PollingEndpointPolicy(
            endpoint_key="sandbox_probe",
            enabled_by_default=False,
            max_requests_per_window=1,
            window_seconds=60,
            minimum_interval_seconds=60.0,
            max_markets_per_run=3,
            max_tokens_per_run=3,
            requires_explicit_network=True,
            allow_automated_loop=False,
            notes="Official-client sandbox probes remain tools-only and explicit-network.",
        ),
    }
    return PollingPolicy(
        policy_id="WP16_CONSERVATIVE_READONLY_POLICY",
        description=(
            "Offline policy for future bounded public market-data polling. "
            "All automated polling remains disabled."
        ),
        endpoints=endpoints,
    )


def validate_polling_policy(
    policy: PollingPolicy,
    *,
    conservative_reference: Optional[PollingPolicy] = None,
) -> PollingPlanValidationResult:
    """Validate a local polling policy without performing network work."""

    reference = conservative_reference or default_polling_policy()
    reference_endpoints = reference.endpoints
    issues: List[PollingPlanIssue] = []

    if policy.automated_polling_enabled:
        issues.append(
            PollingPlanIssue(
                severity="ERROR",
                code="AUTOMATED_POLLING_ENABLED",
                endpoint_key="*",
                message="WP16 policy cannot enable automated polling.",
            )
        )

    for key, endpoint in sorted(policy.endpoints.items()):
        issues.extend(_validate_endpoint(key, endpoint, reference_endpoints))

    for endpoint_key in sorted(NETWORK_ENDPOINT_KEYS - set(policy.endpoints)):
        issues.append(
            PollingPlanIssue(
                severity="ERROR",
                code="MISSING_ENDPOINT_KEY",
                endpoint_key=endpoint_key,
                message="Required endpoint policy is missing.",
            )
        )

    return PollingPlanValidationResult(
        passed=not any(issue.severity == "ERROR" for issue in issues),
        issues=issues,
    )


def validate_polling_plan(
    endpoints: Iterable[PollingEndpointPolicy] | Mapping[str, PollingEndpointPolicy],
) -> PollingPlanValidationResult:
    """Validate a proposed endpoint-policy collection."""

    if isinstance(endpoints, Mapping):
        endpoint_map = dict(endpoints)
    else:
        endpoint_map = {endpoint.endpoint_key: endpoint for endpoint in endpoints}
    return validate_polling_policy(
        PollingPolicy(
            policy_id="LOCAL_PROPOSED_PLAN",
            description="Local proposed polling plan.",
            endpoints=endpoint_map,
        )
    )


def _validate_endpoint(
    key: str,
    endpoint: PollingEndpointPolicy,
    reference_endpoints: Mapping[str, PollingEndpointPolicy],
) -> List[PollingPlanIssue]:
    issues: List[PollingPlanIssue] = []

    if not endpoint.endpoint_key.strip():
        issues.append(_issue("ERROR", "MISSING_ENDPOINT_KEY", key, "Endpoint key is empty."))
    if key != endpoint.endpoint_key:
        issues.append(
            _issue(
                "ERROR",
                "ENDPOINT_KEY_MISMATCH",
                key,
                "Endpoint map key must match endpoint_key.",
            )
        )
    if endpoint.endpoint_key not in NETWORK_ENDPOINT_KEYS:
        issues.append(
            _issue(
                "ERROR",
                "UNKNOWN_ENDPOINT_KEY",
                endpoint.endpoint_key,
                "Endpoint key is not recognized by the WP16 policy.",
            )
        )
    if endpoint.window_seconds <= 0:
        issues.append(_issue("ERROR", "NON_POSITIVE_WINDOW", key, "window_seconds must be positive."))
    if endpoint.max_requests_per_window <= 0:
        issues.append(
            _issue("ERROR", "NON_POSITIVE_MAX_REQUESTS", key, "max_requests_per_window must be positive.")
        )
    if endpoint.minimum_interval_seconds < 0:
        issues.append(
            _issue("ERROR", "NEGATIVE_MINIMUM_INTERVAL", key, "minimum_interval_seconds cannot be negative.")
        )
    if endpoint.endpoint_key in NETWORK_ENDPOINT_KEYS and not endpoint.requires_explicit_network:
        issues.append(
            _issue(
                "ERROR",
                "NETWORK_ENDPOINT_WITHOUT_EXPLICIT_NETWORK",
                key,
                "Future external endpoint policies must require explicit network approval.",
            )
        )
    if endpoint.enabled_by_default and endpoint.requires_explicit_network:
        issues.append(
            _issue(
                "ERROR",
                "ENABLED_NETWORK_ENDPOINT",
                key,
                "Future network endpoint policies must remain disabled by default in WP16.",
            )
        )
    if endpoint.allow_automated_loop:
        issues.append(
            _issue(
                "ERROR",
                "AUTOMATED_LOOP_ENABLED",
                key,
                "WP16 endpoint policies cannot allow automated loops.",
            )
        )
    if not endpoint.notes.strip():
        issues.append(_issue("ERROR", "MISSING_NOTES", key, "Endpoint policy needs local rationale."))

    reference = reference_endpoints.get(endpoint.endpoint_key)
    if reference is not None:
        if endpoint.max_requests_per_window > reference.max_requests_per_window:
            issues.append(
                _issue(
                    "ERROR",
                    "EXCESSIVE_LOCAL_BUDGET",
                    key,
                    "max_requests_per_window exceeds the conservative WP16 default.",
                )
            )
        if endpoint.window_seconds < reference.window_seconds:
            issues.append(
                _issue(
                    "ERROR",
                    "SHORTER_THAN_DEFAULT_WINDOW",
                    key,
                    "window_seconds is shorter than the conservative WP16 default.",
                )
            )
        if endpoint.minimum_interval_seconds < reference.minimum_interval_seconds:
            issues.append(
                _issue(
                    "ERROR",
                    "MINIMUM_INTERVAL_BELOW_DEFAULT",
                    key,
                    "minimum_interval_seconds is below the conservative WP16 default.",
                )
            )

    return issues


def _issue(severity: str, code: str, endpoint_key: str, message: str) -> PollingPlanIssue:
    return PollingPlanIssue(
        severity=severity,
        code=code,
        endpoint_key=endpoint_key,
        message=message,
    )
