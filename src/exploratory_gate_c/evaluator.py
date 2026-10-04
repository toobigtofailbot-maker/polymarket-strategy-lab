"""Deterministic exploratory Gate-C evaluation and exact-intent permit derivation.

``evaluate_exploratory_gate_c`` binds, at one explicit caller-supplied evidence time:

* the current STRAT-LIFE lifecycle state, loaded from an explicit store path through the
  existing verified read-only loader (exact StrategyVersion, active global
  PortfolioAuthorityPolicy, current EXPLORATORY_LIVE allocation, portfolio capacity);
* the latest HermesStrategyAssessment for that StrategyVersion, resolved from the Hermes
  strategy-manager store through its existing verified read-only loader;
* the exact EXEC-FEAS intent / public venue snapshot / feasibility assessment, which must
  re-evaluate to the identical assessment;

into one canonical ``ExploratoryGateCDecision``. ``build_exploratory_gate_c_permit`` derives
an ``ExploratoryGateCPermit`` only from an exact ``PERMIT_ELIGIBLE`` decision.

Store paths are operational inputs only: they are never serialized, hashed or echoed, and
no store is written, created or migrated. Nothing here runs Hermes, mutates lifecycle
state, performs a network or account/access read, loads a credential, signs, submits or
cancels an order, or touches the legacy WP175 execution gateway.
"""

from __future__ import annotations

from decimal import Decimal
import os

from src.execution_feasibility import (
    ExecutionFeasibilityAssessment,
    ExecutionFeasibilityError,
    ExecutionIntent,
    PublicExecutionVenueSnapshot,
    assess_execution_feasibility,
    validate_execution_feasibility_assessment,
    validate_execution_intent,
    validate_public_venue_snapshot,
)
from src.research_runtime.hermes_controlled_runtime.strategy_manager import (
    HermesStrategyAssessment,
    load_hermes_strategy_manager_store,
    strategy_lifecycle_context_fingerprint,
)
from src.strategy_lifecycle import (
    PORTFOLIO_CAPACITY_VALID,
    StrategyLifecycleSnapshot,
    StrategyVersion,
    evaluate_portfolio_capacity,
    load_strategy_lifecycle_store,
)

from .models import (
    MAX_TIME_NS,
    PENDING_ID,
    PERMIT_COMPATIBLE_FEASIBILITY_STATUSES,
    PERMIT_ELIGIBLE,
    PERMIT_REJECTED,
    STRATEGY_VERSION_PREFIX,
    ExploratoryGateCDecision,
    ExploratoryGateCError,
    ExploratoryGateCPermit,
    decimal_text,
    gtd_effective_deadline_ns,
    intent_order_notional,
    order_reason_codes,
    validate_exploratory_gate_c_decision,
)

EXPLORATORY_RISK_BAND = "EXPLORATORY_LIVE"
# Hermes (lifecycle_action, risk_direction) pairs compatible with new exposure.
PERMIT_COMPATIBLE_HERMES_ACTIONS = (("CONTINUE", "UNCHANGED"), ("SCALE", "INCREASE"))
HERMES_HEALTH_BLOCKING_NEW_EXPOSURE = ("QUARANTINED", "RETIRED")
HERMES_TARGET_BAND_BLOCKING_NEW_EXPOSURE = "PAPER"
# EXEC-FEAS failures that mean the intent is not bound to the target StrategyVersion.
_BINDING_FAILURES = frozenset(
    {"EXECUTION_RULE_BINDING_INVALID", "STRATEGY_VERSION_INVALID", "STRATEGY_SPEC_INVALID"}
)


def _fail(code: str) -> ExploratoryGateCError:
    return ExploratoryGateCError(code)


def _require_path(value: object) -> None:
    if isinstance(value, (bool, bytes)) or not isinstance(value, (str, os.PathLike)):
        raise _fail("FIELD_TYPE_INVALID")


def _require_time(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise _fail("FIELD_TYPE_INVALID")
    if value < 0 or value > MAX_TIME_NS:
        raise _fail("FIELD_VALUE_INVALID")
    return value


# ---------------------------------------------------------------------------
# Verified store loading (read-only; paths never leave this scope).
# ---------------------------------------------------------------------------


def _load_lifecycle(path: object) -> StrategyLifecycleSnapshot:
    try:
        result = load_strategy_lifecycle_store(path)
    except Exception:
        raise _fail("LIFECYCLE_STORE_INVALID") from None
    snapshot = result.snapshot
    if (
        result.is_valid is not True
        or result.status != "STORE_LOADED_VERIFIED"
        or not isinstance(snapshot, StrategyLifecycleSnapshot)
    ):
        raise _fail("LIFECYCLE_STORE_INVALID")
    return snapshot


def _load_hermes(path: object):
    try:
        return load_hermes_strategy_manager_store(path)
    except Exception:  # StrategyManagerError and any loader failure, never echoed
        raise _fail("HERMES_STORE_INVALID") from None


def _latest_assessment(
    hermes_snapshot, strategy_version_id: str
) -> HermesStrategyAssessment | None:
    """The latest same-StrategyVersion assessment, resolved from the verified store only."""

    latest_id = hermes_snapshot.latest_assessment_id(strategy_version_id)
    if latest_id is None:
        return None
    matches = [item for item in hermes_snapshot.assessments if item.assessment_id == latest_id]
    if len(matches) != 1:
        raise _fail("HERMES_STORE_INVALID")
    assessment = matches[0]
    if (
        type(assessment) is not HermesStrategyAssessment
        or assessment.strategy_version_id != strategy_version_id
    ):
        raise _fail("HERMES_STORE_INVALID")
    return assessment


# ---------------------------------------------------------------------------
# Exact EXEC-FEAS binding.
# ---------------------------------------------------------------------------


def _bind_execution(
    version: StrategyVersion,
    execution_intent: object,
    venue_snapshot: object,
    execution_feasibility_assessment: object,
) -> tuple[ExecutionIntent, PublicExecutionVenueSnapshot, ExecutionFeasibilityAssessment]:
    if type(execution_intent) is not ExecutionIntent:
        raise _fail("EXECUTION_INTENT_INVALID")
    if type(venue_snapshot) is not PublicExecutionVenueSnapshot:
        raise _fail("VENUE_SNAPSHOT_INVALID")
    if type(execution_feasibility_assessment) is not ExecutionFeasibilityAssessment:
        raise _fail("EXECUTION_ASSESSMENT_INVALID")
    try:
        validate_execution_intent(execution_intent)
    except ExecutionFeasibilityError:
        raise _fail("EXECUTION_INTENT_INVALID") from None
    try:
        validate_execution_intent(execution_intent, strategy_version=version)
    except ExecutionFeasibilityError as failure:
        code = "EXECUTION_BINDING_INVALID" if failure.code in _BINDING_FAILURES else (
            "EXECUTION_INTENT_INVALID"
        )
        raise _fail(code) from None
    try:
        validate_public_venue_snapshot(venue_snapshot)
    except ExecutionFeasibilityError:
        raise _fail("VENUE_SNAPSHOT_INVALID") from None
    try:
        validate_execution_feasibility_assessment(execution_feasibility_assessment)
    except ExecutionFeasibilityError:
        raise _fail("EXECUTION_ASSESSMENT_INVALID") from None
    assessment = execution_feasibility_assessment
    if (
        assessment.execution_intent_id != execution_intent.execution_intent_id
        or assessment.venue_snapshot_id != venue_snapshot.venue_snapshot_id
        or assessment.strategy_version_id != version.strategy_version_id
        or execution_intent.strategy_version_id != version.strategy_version_id
    ):
        raise _fail("EXECUTION_BINDING_INVALID")
    try:
        recomputed = assess_execution_feasibility(
            execution_intent, venue_snapshot, evaluated_at_ns=assessment.evaluated_at_ns
        )
    except ExecutionFeasibilityError:
        raise _fail("EXECUTION_BINDING_INVALID") from None
    if recomputed != assessment or recomputed.to_mapping() != assessment.to_mapping():
        raise _fail("EXECUTION_BINDING_INVALID")
    return execution_intent, venue_snapshot, assessment


# ---------------------------------------------------------------------------
# Public evaluator.
# ---------------------------------------------------------------------------


def evaluate_exploratory_gate_c(
    *,
    lifecycle_store_path: object,
    hermes_manager_store_path: object,
    strategy_version_id: object,
    execution_intent: object,
    venue_snapshot: object,
    execution_feasibility_assessment: object,
    evaluated_at_ns: object,
) -> ExploratoryGateCDecision:
    """Evaluate one exact intent into a canonical exploratory Gate-C decision.

    Structural, tamper and store-load failures raise ``ExploratoryGateCError(code)``;
    valid canonical state that is simply not eligible yields ``PERMIT_REJECTED``.
    """

    _require_path(lifecycle_store_path)
    _require_path(hermes_manager_store_path)
    if not isinstance(strategy_version_id, str):
        raise _fail("FIELD_TYPE_INVALID")
    if not strategy_version_id.startswith(STRATEGY_VERSION_PREFIX) or len(
        strategy_version_id
    ) != len(STRATEGY_VERSION_PREFIX) + 64:
        raise _fail("FIELD_VALUE_INVALID")
    at_ns = _require_time(evaluated_at_ns)

    lifecycle = _load_lifecycle(lifecycle_store_path)
    version = lifecycle.version_by_id(strategy_version_id)
    if type(version) is not StrategyVersion or lifecycle.store_head_entry_hash is None:
        raise _fail("FIELD_VALUE_INVALID")
    hermes = _load_hermes(hermes_manager_store_path)
    intent, snapshot, feasibility = _bind_execution(
        version, execution_intent, venue_snapshot, execution_feasibility_assessment
    )
    if at_ns < feasibility.evaluated_at_ns:
        raise _fail("FIELD_VALUE_INVALID")

    reasons: set[str] = set()
    sid = version.strategy_version_id

    # Global policy, current allocation and STRAT-LIFE portfolio capacity (never mutated).
    policy = lifecycle.policy_by_id(lifecycle.active_policy_id)
    allocation = lifecycle.allocation_of(sid)
    capacity = evaluate_portfolio_capacity(lifecycle, at_ns)
    target = capacity.strategy_result(sid)
    target_status = None if target is None else target.status
    if capacity.status != PORTFOLIO_CAPACITY_VALID or target_status != PORTFOLIO_CAPACITY_VALID:
        reasons.add("PORTFOLIO_CAPACITY_REJECTED")
    if allocation is None or policy is None or allocation.policy_id != policy.policy_id:
        reasons.add("ALLOCATION_REQUIRED")
    if allocation is not None:
        if allocation.risk_band != EXPLORATORY_RISK_BAND:
            reasons.add("EXPLORATORY_BAND_REQUIRED")
        if not allocation.is_active_at(at_ns):
            reasons.add("ALLOCATION_NOT_ACTIVE")
        if Decimal(allocation.active_budget_usd) <= 0:
            reasons.add("ACTIVE_BUDGET_REQUIRED")

    # Latest Hermes soft judgment for this exact StrategyVersion.
    assessment = _latest_assessment(hermes, sid)
    if assessment is None:
        reasons.add("HERMES_ASSESSMENT_REQUIRED")
    else:
        if assessment.strategy_lifecycle_context_sha256 != strategy_lifecycle_context_fingerprint(
            lifecycle, sid
        ):
            reasons.add("HERMES_CONTEXT_STALE")
        if assessment.active_policy_id != lifecycle.active_policy_id:
            reasons.add("HERMES_POLICY_MISMATCH")
        if (
            (assessment.lifecycle_action, assessment.risk_direction)
            not in PERMIT_COMPATIBLE_HERMES_ACTIONS
            or assessment.recommended_health_state in HERMES_HEALTH_BLOCKING_NEW_EXPOSURE
        ):
            reasons.add("HERMES_ACTION_BLOCKS_NEW_EXPOSURE")
        if assessment.target_risk_band == HERMES_TARGET_BAND_BLOCKING_NEW_EXPOSURE:
            reasons.add("HERMES_TARGET_BAND_BLOCKS_NEW_EXPOSURE")

    # Exact EXEC-FEAS status and public-mechanics freshness.
    if feasibility.status not in PERMIT_COMPATIBLE_FEASIBILITY_STATUSES:
        reasons.add("EXECUTION_STATUS_BLOCKS_NEW_EXPOSURE")
    public_deadline = None
    if snapshot.book_timestamp_ns is not None:
        public_deadline = snapshot.book_timestamp_ns + intent.max_public_data_age_ns
        if public_deadline > MAX_TIME_NS:
            raise _fail("LIMIT_EXCEEDED")
    if public_deadline is None or at_ns >= public_deadline:
        reasons.add("EXECUTION_PUBLIC_DATA_STALE")

    # Static exact-intent policy ceilings (no account-capacity claim).
    notional = intent_order_notional(intent.requested_shares, intent.price_limit)
    if notional != Decimal(feasibility.intent_notional_at_price_limit_usd):
        raise _fail("EXECUTION_BINDING_INVALID")
    if policy is not None:
        if intent.execution_style not in policy.allowed_order_styles:
            reasons.add("ORDER_STYLE_NOT_ALLOWED")
    if allocation is not None and notional > Decimal(allocation.active_budget_usd):
        reasons.add("ORDER_NOTIONAL_EXCEEDS_ALLOCATION")
    if policy is not None:
        if notional > Decimal(policy.max_order_notional_usd):
            reasons.add("ORDER_NOTIONAL_EXCEEDS_POLICY_ORDER_MAX")
        if notional > Decimal(policy.max_per_market_usd):
            reasons.add("ORDER_NOTIONAL_EXCEEDS_POLICY_MARKET_MAX")

    # Permit window: earliest of public / policy / allocation / GTD deadlines; no TTL.
    gtd_deadline = gtd_effective_deadline_ns(intent.gtd_expiration_unix_s)
    if gtd_deadline is not None and at_ns >= gtd_deadline:
        reasons.add("GTD_EFFECTIVE_WINDOW_EXPIRED")
    deadlines = [
        public_deadline,
        None if policy is None else policy.expires_at_ns,
        None if allocation is None else allocation.valid_until_ns,
        gtd_deadline,
    ]
    present = [deadline for deadline in deadlines if deadline is not None]
    valid_until = min(present) if present else None
    if valid_until is None or at_ns >= valid_until:
        reasons.add("PERMIT_WINDOW_EMPTY")

    ordered = order_reason_codes(reasons)
    return ExploratoryGateCDecision(
        decision_id=PENDING_ID,  # type: ignore[arg-type]
        strategy_version_id=sid,
        strategy_family_id=version.strategy_family_id,
        lifecycle_store_head_entry_hash=lifecycle.store_head_entry_hash,
        active_policy_id=lifecycle.active_policy_id,
        allocation_id=None if allocation is None else allocation.allocation_id,
        hermes_manager_store_head_entry_hash=hermes.store_head_entry_hash,
        hermes_assessment_id=None if assessment is None else assessment.assessment_id,
        execution_intent_id=intent.execution_intent_id,
        venue_snapshot_id=snapshot.venue_snapshot_id,
        execution_feasibility_assessment_id=feasibility.execution_feasibility_assessment_id,
        evaluated_at_ns=at_ns,
        portfolio_capacity_status=capacity.status,
        portfolio_capacity_reason_codes=tuple(capacity.reason_codes),
        target_strategy_capacity_status=target_status,
        target_strategy_capacity_reason_codes=() if target is None else tuple(target.reason_codes),
        execution_feasibility_status=feasibility.status,
        execution_feasibility_diagnostic_codes=tuple(feasibility.diagnostic_codes),
        intent_order_notional_usd=decimal_text(notional),
        public_mechanics_deadline_ns=public_deadline,
        gtd_effective_deadline_ns=gtd_deadline,
        permit_valid_until_ns=valid_until,
        status=PERMIT_REJECTED if ordered else PERMIT_ELIGIBLE,
        reason_codes=ordered,
    )


def build_exploratory_gate_c_permit(
    decision: object, *, execution_intent: object
) -> ExploratoryGateCPermit:
    """Derive the exact-intent permit from one exact ``PERMIT_ELIGIBLE`` decision.

    No independent market, order or cap value is accepted: every scope field is copied from
    the validated decision and the exact intent it binds.
    """

    validate_exploratory_gate_c_decision(decision)
    assert isinstance(decision, ExploratoryGateCDecision)
    if decision.status != PERMIT_ELIGIBLE or decision.reason_codes:
        raise _fail("FIELD_VALUE_INVALID")
    if type(execution_intent) is not ExecutionIntent:
        raise _fail("EXECUTION_INTENT_INVALID")
    try:
        validate_execution_intent(execution_intent)
    except ExecutionFeasibilityError:
        raise _fail("EXECUTION_INTENT_INVALID") from None
    intent = execution_intent
    notional = intent_order_notional(intent.requested_shares, intent.price_limit)
    if (
        intent.execution_intent_id != decision.execution_intent_id
        or intent.strategy_version_id != decision.strategy_version_id
        or decimal_text(notional) != decision.intent_order_notional_usd
        or gtd_effective_deadline_ns(intent.gtd_expiration_unix_s)
        != decision.gtd_effective_deadline_ns
    ):
        raise _fail("EXECUTION_BINDING_INVALID")
    if (
        decision.active_policy_id is None
        or decision.allocation_id is None
        or decision.hermes_assessment_id is None
        or decision.permit_valid_until_ns is None
    ):
        raise _fail("INTERNAL_VALIDATION_FAILED")
    return ExploratoryGateCPermit(
        permit_id=PENDING_ID,  # type: ignore[arg-type]
        decision_id=decision.decision_id,
        strategy_version_id=decision.strategy_version_id,
        strategy_family_id=decision.strategy_family_id,
        lifecycle_store_head_entry_hash=decision.lifecycle_store_head_entry_hash,
        active_policy_id=decision.active_policy_id,
        allocation_id=decision.allocation_id,
        hermes_assessment_id=decision.hermes_assessment_id,
        execution_intent_id=decision.execution_intent_id,
        venue_snapshot_id=decision.venue_snapshot_id,
        execution_feasibility_assessment_id=decision.execution_feasibility_assessment_id,
        gamma_market_id=intent.gamma_market_id,
        condition_id=intent.condition_id,
        token_id=intent.token_id,
        side=intent.side,
        execution_style=intent.execution_style,
        order_type=intent.order_type,
        requested_shares=intent.requested_shares,
        price_limit=intent.price_limit,
        post_only=intent.post_only,
        gtd_expiration_unix_s=intent.gtd_expiration_unix_s,
        authorized_order_notional_usd=decision.intent_order_notional_usd,
        feasibility_status=decision.execution_feasibility_status,
        feasibility_diagnostic_codes=decision.execution_feasibility_diagnostic_codes,
        issued_at_ns=decision.evaluated_at_ns,
        valid_until_ns=decision.permit_valid_until_ns,
    )
