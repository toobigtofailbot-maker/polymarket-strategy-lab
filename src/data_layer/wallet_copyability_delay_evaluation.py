"""Local/offline/read-only wallet copyability delay evaluation from validated fixtures.

Consumes only already-loaded/validated WP78 LoadedWalletTradeEventRecord objects
and explicit in-memory DelayWindowObservation fixtures. Produces deterministic
advisory WalletCopyabilityDelayEvaluation records for each
(wallet, market, condition, delay_window) combination.

This module is advisory research metadata only.

It does not:
- fetch wallet data from any network or API source;
- monitor real wallets;
- copy wallets;
- compute dollar PnL, expected return, or position size;
- produce buy/sell/trade/execute/position-sizing/live-signal instructions;
- place orders, cancel orders, size positions, or override risk;
- modify scoring weights;
- write files;
- access credentials or authentication clients;
- invoke an LLM, AI agent, scheduler, dashboard, or bot loop;
- run paper or live trading.

Stdlib-only. No network access. No credentials. No file writes.

Added in WP81.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping


# ---------------------------------------------------------------------------
# Advisory labels
# ---------------------------------------------------------------------------

EVAL_ADVISORY_LABEL = "ADVISORY_ONLY_COPYABILITY_DELAY_EVALUATION"
EVAL_UNAVAILABLE_LABEL = "ADVISORY_ONLY_COPYABILITY_DELAY_EVALUATION_UNAVAILABLE"

# ---------------------------------------------------------------------------
# Allowed delay window labels (exact)
# ---------------------------------------------------------------------------

VALID_DELAY_WINDOWS: frozenset[str] = frozenset({
    "1_second",
    "5_seconds",
    "30_seconds",
    "2_minutes",
    "10_minutes",
})

DELAY_WINDOW_ORDER: tuple[str, ...] = (
    "1_second",
    "5_seconds",
    "30_seconds",
    "2_minutes",
    "10_minutes",
)

# ---------------------------------------------------------------------------
# Allowed evaluation statuses
# ---------------------------------------------------------------------------

STATUS_NOT_EVALUATED = "NOT_EVALUATED"
STATUS_INSUFFICIENT_CONTEXT = "INSUFFICIENT_CONTEXT"
STATUS_RESEARCH_PROMISING = "RESEARCH_PROMISING"
STATUS_RESEARCH_WEAK = "RESEARCH_WEAK"
STATUS_UNCOPYABLE_FAST_FLOW = "UNCOPYABLE_FAST_FLOW"
STATUS_UNCOPYABLE_TOO_ILLIQUID = "UNCOPYABLE_TOO_ILLIQUID"
STATUS_SUSPICIOUS_FLOW_DO_NOT_COPY = "SUSPICIOUS_FLOW_DO_NOT_COPY"
STATUS_HUMAN_REVIEW_REQUIRED = "HUMAN_REVIEW_REQUIRED"

ALLOWED_EVALUATION_STATUSES: frozenset[str] = frozenset({
    STATUS_NOT_EVALUATED,
    STATUS_INSUFFICIENT_CONTEXT,
    STATUS_RESEARCH_PROMISING,
    STATUS_RESEARCH_WEAK,
    STATUS_UNCOPYABLE_FAST_FLOW,
    STATUS_UNCOPYABLE_TOO_ILLIQUID,
    STATUS_SUSPICIOUS_FLOW_DO_NOT_COPY,
    STATUS_HUMAN_REVIEW_REQUIRED,
})

# Forbidden output values — must never appear in any evaluation output
FORBIDDEN_OUTPUT_VALUES: frozenset[str] = frozenset({
    "BUY",
    "SELL",
    "TRADE",
    "EXECUTE",
    "OPEN_POSITION",
    "CLOSE_POSITION",
    "POSITION_SIZE",
    "EXPECTED_RETURN",
    "PROFIT_TARGET",
    "STOP_LOSS",
    "TAKE_PROFIT",
    "LIVE_SIGNAL",
    "AUTO_COPY",
    "PNL_TARGET",
    "TRADE_READY",
    "COPY_READY",
    "LIVE_READY",
    "BUY_SIGNAL",
    "SELL_SIGNAL",
})


# ---------------------------------------------------------------------------
# Delay window observation fixture (in-memory only)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class DelayWindowObservation:
    """Advisory local fixture record for one delay window after a wallet event.

    This is not a live market feed, trade signal, order input, or copy instruction.
    It is a local in-memory advisory research fixture only.

    All fields must be provided explicitly from local fixture records.
    No network, API, authentication, or credential access is allowed.
    """

    wallet_id_or_address: str
    market_id: str
    condition_id: str
    delay_window: str
    delayed_price_observed: object | None
    spread_context_available: bool
    liquidity_context_available: bool
    fee_context_available: bool
    size_limit_context_available: bool
    resolved_outcome_available: bool
    suspicious_flow_flag: bool
    fast_flow_flag: bool
    liquidity_insufficient_flag: bool


# ---------------------------------------------------------------------------
# Evaluation output dataclass
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class WalletCopyabilityDelayEvaluation:
    """Advisory local copyability delay evaluation record.

    This is not a trade signal, trade recommendation, copy instruction,
    buy/sell order, position sizing input, expected-return estimate, PnL
    computation, or live execution permission. It is advisory research
    metadata only. Human review is required before any use.

    Added in WP81.
    """

    wallet_id_or_address: str
    market_id: str
    condition_id: str
    market_category: str
    signal_category: str
    delay_window: str
    event_price_observed: object
    delayed_price_observed: object | None
    spread_context_available: bool
    liquidity_context_available: bool
    fee_context_available: bool
    size_limit_context_available: bool
    resolved_outcome_available: bool
    evaluation_status: str
    research_interpretation: str
    human_review_required: bool
    warnings: tuple[str, ...]
    advisory_label: str


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_str(section: Mapping[str, object], key: str) -> str:
    val = section.get(key)
    return str(val).strip() if isinstance(val, str) and val.strip() else ""


def _get_bool(section: Mapping[str, object], key: str) -> bool:
    return bool(section.get(key))


def _as_mapping(record: Mapping[str, object], key: str) -> Mapping[str, object]:
    val = record.get(key)
    return val if isinstance(val, Mapping) else {}


def _is_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _extract_event_fields(loaded_record: object) -> dict | None:
    """Extract evaluation-relevant fields from a LoadedWalletTradeEventRecord.

    Returns None if the record is not a valid-shaped object.
    Uses duck-typing to accept both real records and test fakes.
    """
    record = getattr(loaded_record, "record", None)
    if not isinstance(record, Mapping):
        return None

    validation = getattr(loaded_record, "validation", None)
    is_valid = getattr(validation, "is_valid", False) if validation is not None else False

    wallet_ref = _as_mapping(record, "wallet_reference")
    market_ref = _as_mapping(record, "market_reference")
    observation = _as_mapping(record, "observation")
    context = _as_mapping(record, "context")
    review = _as_mapping(record, "review")

    wallet_id = _get_str(wallet_ref, "wallet_id_or_address") or "UNKNOWN_WALLET"
    market_id = _get_str(market_ref, "market_id") or "UNKNOWN_MARKET"
    condition_id = _get_str(market_ref, "condition_id") or "UNKNOWN_CONDITION"
    market_category = _get_str(market_ref, "market_category")

    price_observed = observation.get("price_observed")
    suspicious_flow_flag = _get_bool(review, "suspicious_flow_flag")
    human_review_required = _get_bool(review, "human_review_required")
    copyability_context_available = _get_bool(context, "copyability_context_available")

    return {
        "wallet_id": wallet_id,
        "market_id": market_id,
        "condition_id": condition_id,
        "market_category": market_category,
        "price_observed": price_observed,
        "suspicious_flow_flag": suspicious_flow_flag,
        "human_review_required": human_review_required,
        "copyability_context_available": copyability_context_available,
        "is_valid": is_valid,
    }


def _group_events(
    loaded_records: Iterable[object],
) -> dict[tuple[str, str, str], list[dict]]:
    """Group extracted event fields by (wallet_id, market_id, condition_id)."""
    groups: dict[tuple[str, str, str], list[dict]] = {}
    for loaded_record in loaded_records:
        fields = _extract_event_fields(loaded_record)
        if fields is None:
            continue
        key = (fields["wallet_id"], fields["market_id"], fields["condition_id"])
        groups.setdefault(key, []).append(fields)
    return groups


def _index_observations(
    delay_observations: Iterable[DelayWindowObservation],
) -> dict[tuple[str, str, str, str], DelayWindowObservation]:
    """Index delay observations by (wallet_id, market_id, condition_id, delay_window).

    If multiple observations share the same key, the last one wins.
    Only observations with valid delay_window labels are indexed.
    """
    index: dict[tuple[str, str, str, str], DelayWindowObservation] = {}
    for obs in delay_observations:
        if obs.delay_window not in VALID_DELAY_WINDOWS:
            continue
        key = (obs.wallet_id_or_address, obs.market_id, obs.condition_id, obs.delay_window)
        index[key] = obs
    return index


def _derive_signal_category(fields: dict) -> str:
    """Derive a simple advisory signal category from event fields."""
    if fields["suspicious_flow_flag"]:
        return "SUSPICIOUS_TIMING"
    if not fields["copyability_context_available"]:
        return "UNCOPYABLE_FAST_FLOW"
    if not fields["is_valid"]:
        return "UNKNOWN_WALLET_SIGNAL"
    return "SPECIALIST_ENTRY"


def _evaluate_one(
    event_fields: dict,
    delay_window: str,
    obs: DelayWindowObservation | None,
) -> WalletCopyabilityDelayEvaluation:
    """Produce one advisory evaluation for a (wallet, market, condition, delay_window)."""
    warnings: list[str] = []

    if not event_fields["is_valid"]:
        warnings.append(
            "Source wallet trade event record is invalid per WP78 validator; "
            "evaluation is derived from partial data only."
        )

    # Suspicious-flow boundary: must not become a strategy to follow privileged info.
    # Treat as active if either the wallet event record OR the delay observation is flagged.
    _suspicious = event_fields["suspicious_flow_flag"] or (obs is not None and obs.suspicious_flow_flag)
    if _suspicious:
        return WalletCopyabilityDelayEvaluation(
            wallet_id_or_address=event_fields["wallet_id"],
            market_id=event_fields["market_id"],
            condition_id=event_fields["condition_id"],
            market_category=event_fields["market_category"],
            signal_category=_derive_signal_category(event_fields),
            delay_window=delay_window,
            event_price_observed=event_fields["price_observed"],
            delayed_price_observed=obs.delayed_price_observed if obs else None,
            spread_context_available=obs.spread_context_available if obs else False,
            liquidity_context_available=obs.liquidity_context_available if obs else False,
            fee_context_available=obs.fee_context_available if obs else False,
            size_limit_context_available=obs.size_limit_context_available if obs else False,
            resolved_outcome_available=obs.resolved_outcome_available if obs else False,
            evaluation_status=STATUS_SUSPICIOUS_FLOW_DO_NOT_COPY,
            research_interpretation=(
                "Suspicious flow detected. This event is blocked from copyability "
                "evaluation. Do not use for copy-trading research."
            ),
            human_review_required=True,
            warnings=tuple(warnings + [
                "Suspicious flow flag is active: evaluation status is "
                "SUSPICIOUS_FLOW_DO_NOT_COPY. Human review required. "
                "This event must not be used to inform copy-trading decisions."
            ]),
            advisory_label=EVAL_ADVISORY_LABEL,
        )

    if event_fields["human_review_required"]:
        warnings.append(
            "Human review required flag is set on the source wallet event record."
        )

    # No matching delay observation
    if obs is None:
        return WalletCopyabilityDelayEvaluation(
            wallet_id_or_address=event_fields["wallet_id"],
            market_id=event_fields["market_id"],
            condition_id=event_fields["condition_id"],
            market_category=event_fields["market_category"],
            signal_category=_derive_signal_category(event_fields),
            delay_window=delay_window,
            event_price_observed=event_fields["price_observed"],
            delayed_price_observed=None,
            spread_context_available=False,
            liquidity_context_available=False,
            fee_context_available=False,
            size_limit_context_available=False,
            resolved_outcome_available=False,
            evaluation_status=STATUS_INSUFFICIENT_CONTEXT,
            research_interpretation=(
                f"No delay-window observation fixture is available for delay "
                f"window '{delay_window}'. Context is insufficient for evaluation."
            ),
            human_review_required=event_fields["human_review_required"],
            warnings=tuple(warnings + [
                f"No delay-window observation found for delay_window='{delay_window}'; "
                "evaluation status is INSUFFICIENT_CONTEXT."
            ]),
            advisory_label=EVAL_UNAVAILABLE_LABEL,
        )

    # Observation present: check fast-flow and illiquid signals first
    if obs.fast_flow_flag:
        return WalletCopyabilityDelayEvaluation(
            wallet_id_or_address=event_fields["wallet_id"],
            market_id=event_fields["market_id"],
            condition_id=event_fields["condition_id"],
            market_category=event_fields["market_category"],
            signal_category=_derive_signal_category(event_fields),
            delay_window=delay_window,
            event_price_observed=event_fields["price_observed"],
            delayed_price_observed=obs.delayed_price_observed,
            spread_context_available=obs.spread_context_available,
            liquidity_context_available=obs.liquidity_context_available,
            fee_context_available=obs.fee_context_available,
            size_limit_context_available=obs.size_limit_context_available,
            resolved_outcome_available=obs.resolved_outcome_available,
            evaluation_status=STATUS_UNCOPYABLE_FAST_FLOW,
            research_interpretation=(
                "Wallet entered too fast for any realistic follower at this delay window. "
                "This event is not copyable at the observed delay."
            ),
            human_review_required=True,
            warnings=tuple(warnings + [
                f"Fast-flow flag is set for delay_window='{delay_window}': "
                "UNCOPYABLE_FAST_FLOW."
            ]),
            advisory_label=EVAL_ADVISORY_LABEL,
        )

    if obs.liquidity_insufficient_flag:
        return WalletCopyabilityDelayEvaluation(
            wallet_id_or_address=event_fields["wallet_id"],
            market_id=event_fields["market_id"],
            condition_id=event_fields["condition_id"],
            market_category=event_fields["market_category"],
            signal_category=_derive_signal_category(event_fields),
            delay_window=delay_window,
            event_price_observed=event_fields["price_observed"],
            delayed_price_observed=obs.delayed_price_observed,
            spread_context_available=obs.spread_context_available,
            liquidity_context_available=obs.liquidity_context_available,
            fee_context_available=obs.fee_context_available,
            size_limit_context_available=obs.size_limit_context_available,
            resolved_outcome_available=obs.resolved_outcome_available,
            evaluation_status=STATUS_UNCOPYABLE_TOO_ILLIQUID,
            research_interpretation=(
                "Insufficient liquidity observed at this delay window for a realistic "
                "follower entry. This event is not copyable at the observed liquidity level."
            ),
            human_review_required=True,
            warnings=tuple(warnings + [
                f"Liquidity insufficient flag is set for delay_window='{delay_window}': "
                "UNCOPYABLE_TOO_ILLIQUID."
            ]),
            advisory_label=EVAL_ADVISORY_LABEL,
        )

    # Check delayed price presence
    if obs.delayed_price_observed is None or not _is_number(obs.delayed_price_observed):
        warnings.append(
            f"Delayed price observation is absent for delay_window='{delay_window}'."
        )
        return WalletCopyabilityDelayEvaluation(
            wallet_id_or_address=event_fields["wallet_id"],
            market_id=event_fields["market_id"],
            condition_id=event_fields["condition_id"],
            market_category=event_fields["market_category"],
            signal_category=_derive_signal_category(event_fields),
            delay_window=delay_window,
            event_price_observed=event_fields["price_observed"],
            delayed_price_observed=None,
            spread_context_available=obs.spread_context_available,
            liquidity_context_available=obs.liquidity_context_available,
            fee_context_available=obs.fee_context_available,
            size_limit_context_available=obs.size_limit_context_available,
            resolved_outcome_available=obs.resolved_outcome_available,
            evaluation_status=STATUS_INSUFFICIENT_CONTEXT,
            research_interpretation=(
                f"Delayed price observation is missing for delay_window='{delay_window}'. "
                "Context is insufficient for evaluation."
            ),
            human_review_required=event_fields["human_review_required"],
            warnings=tuple(warnings),
            advisory_label=EVAL_UNAVAILABLE_LABEL,
        )

    # Gather missing context warnings
    missing_contexts: list[str] = []
    if not obs.spread_context_available:
        missing_contexts.append("spread")
    if not obs.liquidity_context_available:
        missing_contexts.append("liquidity")
    if not obs.fee_context_available:
        missing_contexts.append("fee")
    if not obs.size_limit_context_available:
        missing_contexts.append("size_limit")

    for ctx in missing_contexts:
        warnings.append(
            f"Missing context: {ctx}_context_available is False for "
            f"delay_window='{delay_window}'. Evaluation may be incomplete."
        )

    # If any required context is missing, yield INSUFFICIENT_CONTEXT
    if missing_contexts:
        return WalletCopyabilityDelayEvaluation(
            wallet_id_or_address=event_fields["wallet_id"],
            market_id=event_fields["market_id"],
            condition_id=event_fields["condition_id"],
            market_category=event_fields["market_category"],
            signal_category=_derive_signal_category(event_fields),
            delay_window=delay_window,
            event_price_observed=event_fields["price_observed"],
            delayed_price_observed=obs.delayed_price_observed,
            spread_context_available=obs.spread_context_available,
            liquidity_context_available=obs.liquidity_context_available,
            fee_context_available=obs.fee_context_available,
            size_limit_context_available=obs.size_limit_context_available,
            resolved_outcome_available=obs.resolved_outcome_available,
            evaluation_status=STATUS_INSUFFICIENT_CONTEXT,
            research_interpretation=(
                f"One or more required context fields are unavailable for "
                f"delay_window='{delay_window}': {', '.join(missing_contexts)}. "
                "Context is insufficient for a complete evaluation."
            ),
            human_review_required=event_fields["human_review_required"],
            warnings=tuple(warnings),
            advisory_label=EVAL_ADVISORY_LABEL,
        )

    # Full context available: advisory determination based on price comparison
    # This is purely advisory — no PnL, no expected-return, no trade signal.
    event_price = event_fields["price_observed"]
    delayed_price = obs.delayed_price_observed

    if _is_number(event_price) and _is_number(delayed_price):
        price_diff_pct = abs(float(delayed_price) - float(event_price)) / max(float(event_price), 1e-9)
        if price_diff_pct <= 0.05:
            status = STATUS_RESEARCH_PROMISING
            interpretation = (
                f"Delayed price at delay_window='{delay_window}' is within 5% of event "
                f"price. Advisory context appears favorable for research review. "
                "This is advisory research metadata only, not a trade signal."
            )
        else:
            status = STATUS_RESEARCH_WEAK
            interpretation = (
                f"Delayed price at delay_window='{delay_window}' has moved more than "
                f"5% from event price. Advisory context appears unfavorable for research "
                "review. This is advisory research metadata only, not a trade signal."
            )
    else:
        status = STATUS_RESEARCH_WEAK
        interpretation = (
            f"Event price or delayed price is non-numeric for delay_window='{delay_window}'. "
            "Advisory context is weak. This is not a trade signal."
        )
        warnings.append(
            f"Non-numeric price values at delay_window='{delay_window}'; "
            "advisory status set to RESEARCH_WEAK."
        )

    if event_fields["human_review_required"]:
        status = STATUS_HUMAN_REVIEW_REQUIRED
        interpretation = (
            f"Human review required flag is set. Evaluation at delay_window='{delay_window}' "
            "requires human judgment before any research use."
        )

    return WalletCopyabilityDelayEvaluation(
        wallet_id_or_address=event_fields["wallet_id"],
        market_id=event_fields["market_id"],
        condition_id=event_fields["condition_id"],
        market_category=event_fields["market_category"],
        signal_category=_derive_signal_category(event_fields),
        delay_window=delay_window,
        event_price_observed=event_fields["price_observed"],
        delayed_price_observed=obs.delayed_price_observed,
        spread_context_available=obs.spread_context_available,
        liquidity_context_available=obs.liquidity_context_available,
        fee_context_available=obs.fee_context_available,
        size_limit_context_available=obs.size_limit_context_available,
        resolved_outcome_available=obs.resolved_outcome_available,
        evaluation_status=status,
        research_interpretation=interpretation,
        human_review_required=(
            event_fields["human_review_required"]
            or status in (STATUS_SUSPICIOUS_FLOW_DO_NOT_COPY, STATUS_HUMAN_REVIEW_REQUIRED)
        ),
        warnings=tuple(warnings),
        advisory_label=EVAL_ADVISORY_LABEL,
    )


# ---------------------------------------------------------------------------
# Public evaluation function
# ---------------------------------------------------------------------------

def evaluate_copyability_delay(
    loaded_records: Iterable[object],
    delay_observations: Iterable[DelayWindowObservation],
) -> tuple[WalletCopyabilityDelayEvaluation, ...]:
    """Produce deterministic advisory copyability delay evaluations from local fixtures.

    Consumes:
    - loaded_records: already-loaded/validated WP78 LoadedWalletTradeEventRecord
      objects (or duck-typed equivalents). Records that cannot be parsed are
      ignored.
    - delay_observations: local in-memory DelayWindowObservation fixture objects.
      Observations with unrecognized delay_window labels are ignored.

    Groups events by (wallet_id_or_address, market_id, condition_id). For each
    group, evaluates all five supported delay windows. Returns a deterministic
    tuple sorted by (wallet_id, market_id, condition_id, delay_window).

    This function is advisory research metadata only. It does not fetch network
    data, compute dollar PnL, expected return, or position size, produce
    buy/sell signals, place orders, write files, access credentials, or run
    paper/live trading.
    """
    groups = _group_events(loaded_records)
    obs_index = _index_observations(delay_observations)

    evaluations: list[WalletCopyabilityDelayEvaluation] = []

    for group_key in sorted(groups.keys()):
        wallet_id, market_id, condition_id = group_key
        field_list = groups[group_key]

        # Aggregate event-level fields across all records in the group
        first = field_list[0]
        market_category = first["market_category"]
        price_observed = first["price_observed"]
        suspicious_flow_flag = any(f["suspicious_flow_flag"] for f in field_list)
        human_review_required = any(f["human_review_required"] for f in field_list)
        copyability_context_available = all(f["copyability_context_available"] for f in field_list)
        all_valid = all(f["is_valid"] for f in field_list)

        aggregated_fields = {
            "wallet_id": wallet_id,
            "market_id": market_id,
            "condition_id": condition_id,
            "market_category": market_category,
            "price_observed": price_observed,
            "suspicious_flow_flag": suspicious_flow_flag,
            "human_review_required": human_review_required,
            "copyability_context_available": copyability_context_available,
            "is_valid": all_valid,
        }

        for delay_window in DELAY_WINDOW_ORDER:
            obs_key = (wallet_id, market_id, condition_id, delay_window)
            obs = obs_index.get(obs_key)
            evaluation = _evaluate_one(aggregated_fields, delay_window, obs)
            evaluations.append(evaluation)

    evaluations.sort(
        key=lambda e: (e.wallet_id_or_address, e.market_id, e.condition_id, e.delay_window)
    )
    return tuple(evaluations)
