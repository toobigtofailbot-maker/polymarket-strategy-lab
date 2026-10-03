"""Risk-band inheritance, verified lifecycle replay, and portfolio capacity (S10-STRAT-LIFE-01).

Pure deterministic helpers over the immutable lifecycle records:

* ``derive_inherited_risk_band_ceiling`` -- automatic inheritance ceiling only; it
  never grants live authority;
* the lifecycle replay state machine that derives the current projection
  (``StrategyLifecycleSnapshot``) from an ordered record sequence -- the projection
  is constructed only by verified replay and is not independently writable;
* ``evaluate_portfolio_capacity`` -- budget reservation accounting against the
  current global ``PortfolioAuthorityPolicy`` at an explicit evaluation time.

Nothing here models orders, market exposure, fills, PnL, or reconciliation, and
nothing here has credential, paper-execution, order, execution, or live authority.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from .models import (
    ADAPTATION_CLASSES,
    RISK_BANDS,
    PortfolioAuthorityPolicy,
    PortfolioPolicyReceipt,
    StrategyFamily,
    StrategyHealthReceipt,
    StrategyLifecycleError,
    StrategyRestrictionReceipt,
    StrategyRiskAllocation,
    StrategyVersion,
    decimal_to_canonical,
    money,
    validate_strategy_version_lineage,
)


SNAPSHOT_SCHEMA_ID = "polymarket-strategy-lifecycle-snapshot"
SNAPSHOT_SCHEMA_VERSION = "1.0.0"

PORTFOLIO_CAPACITY_VALID = "PORTFOLIO_CAPACITY_VALID"
PORTFOLIO_CAPACITY_REJECTED = "PORTFOLIO_CAPACITY_REJECTED"
PORTFOLIO_CAPACITY_STATUSES = (PORTFOLIO_CAPACITY_VALID, PORTFOLIO_CAPACITY_REJECTED)
CAPACITY_REASON_CODES = (
    "POLICY_NOT_ACTIVE",
    "POLICY_NOT_EFFECTIVE",
    "POLICY_EXPIRED",
    "ALLOCATION_POLICY_MISMATCH",
    "ALLOCATION_INVALID",
    "PER_STRATEGY_LIMIT_EXCEEDED",
    "EXPLORATORY_POOL_EXCEEDED",
    "VALIDATED_POOL_EXCEEDED",
    "MATURE_POOL_EXCEEDED",
    "GLOBAL_CAPITAL_LIMIT_EXCEEDED",
    "MAX_ACTIVE_STRATEGIES_EXCEEDED",
    "HEALTH_BLOCKS_ACTIVE_RISK",
    "RESTRICTION_BLOCKS_ACTIVE_RISK",
    "ACTIVE_BUDGET_CAP_EXCEEDED",
    "INTERNAL_VALIDATION_FAILED",
)
_GLOBAL_AGGREGATE_REASONS = frozenset(
    {
        "EXPLORATORY_POOL_EXCEEDED",
        "VALIDATED_POOL_EXCEEDED",
        "MATURE_POOL_EXCEEDED",
        "GLOBAL_CAPITAL_LIMIT_EXCEEDED",
        "MAX_ACTIVE_STRATEGIES_EXCEEDED",
    }
)
_POOL_REASON = {
    "EXPLORATORY_LIVE": "EXPLORATORY_POOL_EXCEEDED",
    "VALIDATED_LIVE": "VALIDATED_POOL_EXCEEDED",
    "MATURE_LIVE": "MATURE_POOL_EXCEEDED",
}
_LIVE_BANDS = tuple(_POOL_REASON)
_BLOCKING_HEALTH = frozenset({"QUARANTINED", "RETIRED"})
_BLOCKING_RESTRICTIONS = frozenset({"PAUSE_NEW_EXPOSURE", "PAPER_ONLY"})


def _fail(code: str) -> StrategyLifecycleError:
    return StrategyLifecycleError(code)


def _ordered_reasons(reasons: set[str]) -> tuple[str, ...]:
    return tuple(code for code in CAPACITY_REASON_CODES if code in reasons)


def derive_inherited_risk_band_ceiling(
    parent_band: str | None, adaptation_class: str
) -> str | None:
    """Automatic inheritance ceiling only; it never grants live authority.

    BOUNDED_ADAPTATION -> at most the exact parent band.
    MATERIAL_ADAPTATION -> min(parent band, EXPLORATORY_LIVE).
    ROOT -> no inherited parent band (``None``).
    """

    if adaptation_class not in ADAPTATION_CLASSES:
        raise _fail("FIELD_VALUE_INVALID")
    if adaptation_class == "ROOT":
        if parent_band is not None:
            raise _fail("LINEAGE_INVALID")
        return None
    if parent_band not in RISK_BANDS:
        raise _fail("FIELD_VALUE_INVALID")
    if adaptation_class == "BOUNDED_ADAPTATION":
        return parent_band
    return RISK_BANDS[min(RISK_BANDS.index(parent_band), RISK_BANDS.index("EXPLORATORY_LIVE"))]


# ---------------------------------------------------------------------------
# Verified replay projection.
# ---------------------------------------------------------------------------

_REPLAY_TOKEN = object()


@dataclass(frozen=True)
class StrategyLifecycleSnapshot:
    """Current lifecycle projection derived only by verified replay.

    Pair tuples are ordered by strategy version ID; families, versions and policies
    are in append order. The authority truths are fixed and cannot be promoted.
    """

    store_head_entry_hash: str | None
    total_rows: int
    total_payload_bytes: int
    active_policy_id: str | None
    families: tuple[StrategyFamily, ...]
    strategy_versions: tuple[StrategyVersion, ...]
    policies: tuple[PortfolioAuthorityPolicy, ...]
    current_health_by_strategy_version: tuple[tuple[str, str], ...]
    current_allocation_by_strategy_version: tuple[tuple[str, StrategyRiskAllocation], ...]
    active_restrictions_by_strategy_version: tuple[
        tuple[str, tuple[StrategyRestrictionReceipt, ...]], ...
    ]
    schema_id: str = SNAPSHOT_SCHEMA_ID
    schema_version: str = SNAPSHOT_SCHEMA_VERSION
    no_credential_authority: bool = True
    no_paper_execution_authority: bool = True
    no_order_authority: bool = True
    no_execution_authority: bool = True
    no_live_authority: bool = True
    _replay_token: object = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self._replay_token is not _REPLAY_TOKEN:
            raise _fail("INTERNAL_VALIDATION_FAILED")
        if (
            self.schema_id != SNAPSHOT_SCHEMA_ID
            or self.schema_version != SNAPSHOT_SCHEMA_VERSION
            or not all(
                flag is True
                for flag in (
                    self.no_credential_authority,
                    self.no_paper_execution_authority,
                    self.no_order_authority,
                    self.no_execution_authority,
                    self.no_live_authority,
                )
            )
        ):
            raise _fail("INTERNAL_VALIDATION_FAILED")

    def version_by_id(self, strategy_version_id: str) -> StrategyVersion | None:
        for version in self.strategy_versions:
            if version.strategy_version_id == strategy_version_id:
                return version
        return None

    def policy_by_id(self, policy_id: str | None) -> PortfolioAuthorityPolicy | None:
        for policy in self.policies:
            if policy.policy_id == policy_id:
                return policy
        return None

    def health_of(self, strategy_version_id: str) -> str | None:
        return dict(self.current_health_by_strategy_version).get(strategy_version_id)

    def allocation_of(self, strategy_version_id: str) -> StrategyRiskAllocation | None:
        return dict(self.current_allocation_by_strategy_version).get(strategy_version_id)

    def restrictions_of(
        self, strategy_version_id: str
    ) -> tuple[StrategyRestrictionReceipt, ...]:
        return dict(self.active_restrictions_by_strategy_version).get(strategy_version_id, ())


class _LifecycleState:
    """Mutable replay accumulator; callers apply to a copy for atomic semantics."""

    def __init__(self) -> None:
        self.families: dict[str, StrategyFamily] = {}
        self.family_keys: set[str] = set()
        self.versions: dict[str, StrategyVersion] = {}
        self.policies: dict[str, PortfolioAuthorityPolicy] = {}
        self.receipt_ids: set[str] = set()
        self.active_policy_id: str | None = None
        self.health: dict[str, str] = {}
        self.allocations: dict[str, StrategyRiskAllocation] = {}
        self.restrictions: dict[str, dict[str, StrategyRestrictionReceipt]] = {}

    def copy(self) -> "_LifecycleState":
        other = _LifecycleState()
        other.families = dict(self.families)
        other.family_keys = set(self.family_keys)
        other.versions = dict(self.versions)
        other.policies = dict(self.policies)
        other.receipt_ids = set(self.receipt_ids)
        other.active_policy_id = self.active_policy_id
        other.health = dict(self.health)
        other.allocations = dict(self.allocations)
        other.restrictions = {key: dict(value) for key, value in self.restrictions.items()}
        return other

    def snapshot(
        self,
        *,
        store_head_entry_hash: str | None,
        total_rows: int,
        total_payload_bytes: int,
    ) -> StrategyLifecycleSnapshot:
        return StrategyLifecycleSnapshot(
            store_head_entry_hash=store_head_entry_hash,
            total_rows=total_rows,
            total_payload_bytes=total_payload_bytes,
            active_policy_id=self.active_policy_id,
            families=tuple(self.families.values()),
            strategy_versions=tuple(self.versions.values()),
            policies=tuple(self.policies.values()),
            current_health_by_strategy_version=tuple(sorted(self.health.items())),
            current_allocation_by_strategy_version=tuple(sorted(self.allocations.items())),
            active_restrictions_by_strategy_version=tuple(
                (version_id, tuple(receipts[key] for key in sorted(receipts)))
                for version_id, receipts in sorted(self.restrictions.items())
                if receipts
            ),
            _replay_token=_REPLAY_TOKEN,
        )

    def apply(self, record: object) -> None:
        if isinstance(record, StrategyFamily):
            self._apply_family(record)
        elif isinstance(record, StrategyVersion):
            self._apply_version(record)
        elif isinstance(record, PortfolioAuthorityPolicy):
            self._apply_policy(record)
        elif isinstance(record, PortfolioPolicyReceipt):
            self._apply_policy_receipt(record)
        elif isinstance(record, StrategyHealthReceipt):
            self._apply_health(record)
        elif isinstance(record, StrategyRiskAllocation):
            self._apply_allocation(record)
        elif isinstance(record, StrategyRestrictionReceipt):
            self._apply_restriction(record)
        else:
            raise _fail("FIELD_TYPE_INVALID")

    def _apply_family(self, family: StrategyFamily) -> None:
        if family.family_key in self.family_keys:
            raise _fail("IDENTITY_CONFLICT")
        self.families[family.strategy_family_id] = family
        self.family_keys.add(family.family_key)

    def _apply_version(self, version: StrategyVersion) -> None:
        family = self.families.get(version.strategy_family_id)
        if family is None:
            raise _fail("REFERENCE_INVALID")
        if version.created_time_ns < family.created_time_ns:
            raise _fail("LINEAGE_INVALID")
        parent = None
        if version.parent_strategy_version_id is not None:
            parent = self.versions.get(version.parent_strategy_version_id)
            if parent is None:
                raise _fail("REFERENCE_INVALID")
        validate_strategy_version_lineage(version, parent)
        self.versions[version.strategy_version_id] = version
        self.health[version.strategy_version_id] = "NEW"

    def _apply_policy(self, policy: PortfolioAuthorityPolicy) -> None:
        if (
            policy.predecessor_policy_id is not None
            and policy.predecessor_policy_id not in self.policies
        ):
            raise _fail("REFERENCE_INVALID")
        self.policies[policy.policy_id] = policy

    def _apply_policy_receipt(self, receipt: PortfolioPolicyReceipt) -> None:
        policy = self.policies.get(receipt.policy_id)
        if policy is None:
            raise _fail("REFERENCE_INVALID")
        if receipt.previous_active_policy_id != self.active_policy_id:
            raise _fail("POLICY_TRANSITION_INVALID")
        if receipt.action == "ACTIVATE":
            if (
                receipt.policy_id == self.active_policy_id
                or receipt.created_time_ns < policy.created_time_ns
                or (
                    policy.expires_at_ns is not None
                    and receipt.created_time_ns >= policy.expires_at_ns
                )
            ):
                raise _fail("POLICY_TRANSITION_INVALID")
            self.active_policy_id = receipt.policy_id
        else:
            if receipt.policy_id != self.active_policy_id:
                raise _fail("POLICY_TRANSITION_INVALID")
            self.active_policy_id = None
        self.receipt_ids.add(receipt.policy_receipt_id)

    def _apply_health(self, receipt: StrategyHealthReceipt) -> None:
        current = self.health.get(receipt.strategy_version_id)
        if current is None:
            raise _fail("REFERENCE_INVALID")
        if receipt.previous_health_state != current or current == "RETIRED":
            raise _fail("HEALTH_TRANSITION_INVALID")
        self.health[receipt.strategy_version_id] = receipt.new_health_state

    def _apply_restriction(self, receipt: StrategyRestrictionReceipt) -> None:
        if receipt.strategy_version_id not in self.versions:
            raise _fail("REFERENCE_INVALID")
        active = self.restrictions.setdefault(receipt.strategy_version_id, {})
        existing = active.get(receipt.restriction_key)
        if receipt.action == "APPLY":
            if existing is not None:
                raise _fail("RESTRICTION_TRANSITION_INVALID")
            active[receipt.restriction_key] = receipt
            return
        if (
            existing is None
            or existing.restriction_kind != receipt.restriction_kind
            or existing.max_active_budget_usd != receipt.max_active_budget_usd
        ):
            raise _fail("RESTRICTION_TRANSITION_INVALID")
        del active[receipt.restriction_key]
        if not active:
            del self.restrictions[receipt.strategy_version_id]

    def _apply_allocation(self, allocation: StrategyRiskAllocation) -> None:
        version = self.versions.get(allocation.strategy_version_id)
        policy = self.policies.get(allocation.policy_id)
        if version is None or policy is None:
            raise _fail("REFERENCE_INVALID")
        if allocation.policy_id != self.active_policy_id:
            raise _fail("ALLOCATION_INVALID")
        if allocation.valid_from_ns < policy.effective_from_ns or (
            policy.expires_at_ns is not None
            and (
                allocation.valid_until_ns is None
                or allocation.valid_until_ns > policy.expires_at_ns
            )
        ):
            raise _fail("ALLOCATION_INVALID")
        if allocation.allocation_basis == "PARENT_INHERITANCE":
            if version.parent_strategy_version_id is None:
                raise _fail("ALLOCATION_INVALID")
            parent_allocation = self.allocations.get(version.parent_strategy_version_id)
            if parent_allocation is None:
                raise _fail("ALLOCATION_INVALID")
            ceiling = derive_inherited_risk_band_ceiling(
                parent_allocation.risk_band, version.adaptation_class
            )
            if RISK_BANDS.index(allocation.risk_band) > RISK_BANDS.index(ceiling):  # type: ignore[arg-type]
                raise _fail("ALLOCATION_INVALID")
        self.allocations[allocation.strategy_version_id] = allocation
        self._check_allocation_capacity(allocation)

    def _check_allocation_capacity(self, allocation: StrategyRiskAllocation) -> None:
        """Reject an allocation that is itself blocked or creates an aggregate overflow.

        Capacity is piecewise constant and only rises at allocation start times, so
        the new allocation is checked at its own start and at every other current
        allocation's start inside its validity window. Pre-existing strategy-local
        blocks on unrelated strategies never block this strategy.
        """

        snapshot = self.snapshot(
            store_head_entry_hash=None, total_rows=0, total_payload_bytes=0
        )
        end = allocation.valid_until_ns
        checkpoints = {allocation.valid_from_ns}
        for other in self.allocations.values():
            if other.valid_from_ns >= allocation.valid_from_ns and (
                end is None or other.valid_from_ns < end
            ):
                checkpoints.add(other.valid_from_ns)
        for at_time_ns in sorted(checkpoints):
            result = evaluate_portfolio_capacity(snapshot, at_time_ns)
            own = result.strategy_result(allocation.strategy_version_id)
            if (
                set(result.reason_codes) & _GLOBAL_AGGREGATE_REASONS
                or own is None
                or own.status != PORTFOLIO_CAPACITY_VALID
            ):
                raise _fail("CAPACITY_INVALID")


def _replay(records: tuple[object, ...]) -> _LifecycleState:
    state = _LifecycleState()
    for record in records:
        state.apply(record)
    return state


# ---------------------------------------------------------------------------
# Portfolio capacity evaluation.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class StrategyCapacityResult:
    strategy_version_id: str
    status: str
    reason_codes: tuple[str, ...]
    risk_band: str
    active_budget_usd: str


@dataclass(frozen=True)
class PortfolioCapacityResult:
    """Budget-reservation verdict only; it measures no orders, exposure, fills or PnL."""

    status: str
    reason_codes: tuple[str, ...]
    at_time_ns: int | None
    policy_id: str | None
    exploratory_active_usd: str
    validated_active_usd: str
    mature_active_usd: str
    total_active_usd: str
    active_real_risk_strategy_count: int
    strategy_results: tuple[StrategyCapacityResult, ...]

    @property
    def is_valid(self) -> bool:
        return self.status == PORTFOLIO_CAPACITY_VALID

    def strategy_result(self, strategy_version_id: str) -> StrategyCapacityResult | None:
        for item in self.strategy_results:
            if item.strategy_version_id == strategy_version_id:
                return item
        return None


def _rejected_result(
    reasons: set[str], at_time_ns: int | None, policy_id: str | None
) -> PortfolioCapacityResult:
    return PortfolioCapacityResult(
        status=PORTFOLIO_CAPACITY_REJECTED,
        reason_codes=_ordered_reasons(reasons),
        at_time_ns=at_time_ns,
        policy_id=policy_id,
        exploratory_active_usd="0",
        validated_active_usd="0",
        mature_active_usd="0",
        total_active_usd="0",
        active_real_risk_strategy_count=0,
        strategy_results=(),
    )


def evaluate_portfolio_capacity(
    snapshot: StrategyLifecycleSnapshot, at_time_ns: int
) -> PortfolioCapacityResult:
    """Evaluate active budget reservations against the active global policy at ``at_time_ns``."""

    if not isinstance(snapshot, StrategyLifecycleSnapshot) or (
        isinstance(at_time_ns, bool)
        or not isinstance(at_time_ns, int)
        or at_time_ns < 0
    ):
        return _rejected_result({"INTERNAL_VALIDATION_FAILED"}, None, None)
    policy = snapshot.policy_by_id(snapshot.active_policy_id)
    if policy is None:
        return _rejected_result({"POLICY_NOT_ACTIVE"}, at_time_ns, None)
    if at_time_ns < policy.effective_from_ns:
        return _rejected_result({"POLICY_NOT_EFFECTIVE"}, at_time_ns, policy.policy_id)
    if policy.expires_at_ns is not None and at_time_ns >= policy.expires_at_ns:
        return _rejected_result({"POLICY_EXPIRED"}, at_time_ns, policy.policy_id)

    band_totals = {band: Decimal(0) for band in _LIVE_BANDS}
    active_count = 0
    reasons: set[str] = set()
    strategy_results: list[StrategyCapacityResult] = []
    for version_id, allocation in snapshot.current_allocation_by_strategy_version:
        own: set[str] = set()
        try:
            budget = money(allocation.active_budget_usd)
        except StrategyLifecycleError:
            budget = Decimal(0)
            own.add("ALLOCATION_INVALID")
        if not allocation.is_active_at(at_time_ns):
            budget = Decimal(0)
        counted = True
        if budget > 0:
            if allocation.policy_id != policy.policy_id:
                own.add("ALLOCATION_POLICY_MISMATCH")
                counted = False
            if allocation.risk_band not in _LIVE_BANDS or snapshot.version_by_id(version_id) is None:
                own.add("ALLOCATION_INVALID")
                counted = False
            if snapshot.health_of(version_id) in _BLOCKING_HEALTH:
                own.add("HEALTH_BLOCKS_ACTIVE_RISK")
            restrictions = snapshot.restrictions_of(version_id)
            if any(item.restriction_kind in _BLOCKING_RESTRICTIONS for item in restrictions):
                own.add("RESTRICTION_BLOCKS_ACTIVE_RISK")
            caps = [
                money(item.max_active_budget_usd)
                for item in restrictions
                if item.restriction_kind == "ACTIVE_BUDGET_CAP"
            ]
            if caps and budget > min(caps):
                own.add("ACTIVE_BUDGET_CAP_EXCEEDED")
            if counted:
                if budget > policy.per_strategy_max(allocation.risk_band):
                    own.add("PER_STRATEGY_LIMIT_EXCEEDED")
                band_totals[allocation.risk_band] += budget
                active_count += 1
        reasons |= own
        strategy_results.append(
            StrategyCapacityResult(
                strategy_version_id=version_id,
                status=PORTFOLIO_CAPACITY_REJECTED if own else PORTFOLIO_CAPACITY_VALID,
                reason_codes=_ordered_reasons(own),
                risk_band=allocation.risk_band,
                active_budget_usd=decimal_to_canonical(budget),
            )
        )
    for band in _LIVE_BANDS:
        if band_totals[band] > policy.pool_max(band):
            reasons.add(_POOL_REASON[band])
    total = sum(band_totals.values(), Decimal(0))
    if total > money(policy.global_capital_at_risk_max_usd):
        reasons.add("GLOBAL_CAPITAL_LIMIT_EXCEEDED")
    if active_count > policy.max_active_strategies:
        reasons.add("MAX_ACTIVE_STRATEGIES_EXCEEDED")
    return PortfolioCapacityResult(
        status=PORTFOLIO_CAPACITY_REJECTED if reasons else PORTFOLIO_CAPACITY_VALID,
        reason_codes=_ordered_reasons(reasons),
        at_time_ns=at_time_ns,
        policy_id=policy.policy_id,
        exploratory_active_usd=decimal_to_canonical(band_totals["EXPLORATORY_LIVE"]),
        validated_active_usd=decimal_to_canonical(band_totals["VALIDATED_LIVE"]),
        mature_active_usd=decimal_to_canonical(band_totals["MATURE_LIVE"]),
        total_active_usd=decimal_to_canonical(total),
        active_real_risk_strategy_count=active_count,
        strategy_results=tuple(strategy_results),
    )
