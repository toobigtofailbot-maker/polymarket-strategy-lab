"""Local/offline/read-only wallet intelligence report generator.

Builds an in-memory WalletIntelligenceReport from:
- WalletSignalResearchProfile records (WP79)
- WalletResearchQueueAnnotation records (WP79)
- WalletCopyabilityDelayEvaluation records (WP81)
- Optional explicit local metadata supplied by callers

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

Added in WP82.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping


# ---------------------------------------------------------------------------
# Advisory label
# ---------------------------------------------------------------------------

REPORT_ADVISORY_LABEL = "ADVISORY_ONLY_WALLET_INTELLIGENCE_REPORT"

REPORT_TYPE = "WALLET_INTELLIGENCE_ADVISORY_REPORT_V1"

# ---------------------------------------------------------------------------
# Forbidden output values — must never appear in any report output
# ---------------------------------------------------------------------------

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
# Forbidden output substrings — used for metadata sanitization
# ---------------------------------------------------------------------------

_FORBIDDEN_OUTPUT_SUBSTRINGS: tuple[str, ...] = (
    "buy", "sell", "trade",
    "execute",
    "open_position", "close_position",
    "position_size", "position sizing", "position-size",
    "expected_return", "expected return", "expected-return",
    "profit_target", "profit target",
    "stop_loss", "stop loss",
    "take_profit", "take profit",
    "live_signal", "live signal",
    "auto_copy", "auto copy",
    "pnl_target", "pnl target",
    "paper_trading_candidate", "paper trading candidate",
    "strategy_signal", "strategy signal",
)


def _contains_forbidden_substring(s: str) -> bool:
    low = s.lower()
    return any(sub in low for sub in _FORBIDDEN_OUTPUT_SUBSTRINGS)


def _sanitize_metadata(
    raw: Mapping[str, object],
) -> tuple[dict[str, object], bool]:
    """Sanitize caller-supplied metadata.

    Forbidden keys are replaced with neutral redaction placeholders.
    Forbidden string values are replaced with a neutral redaction sentinel.
    Non-string values that are not str are passed through unchanged.
    Returns (sanitized_dict, was_redacted).
    """
    result: dict[str, object] = {}
    redacted = False
    redacted_key_counter = 0
    for k, v in raw.items():
        if _contains_forbidden_substring(k):
            safe_key = f"unsafe_metadata_key_redacted_{redacted_key_counter:03d}"
            redacted_key_counter += 1
            redacted = True
        else:
            safe_key = k
        if isinstance(v, str) and _contains_forbidden_substring(v):
            safe_val: object = "metadata_value_redacted"
            redacted = True
        else:
            safe_val = v
        result[safe_key] = safe_val
    return result, redacted


# ---------------------------------------------------------------------------
# Advisory notice text
# ---------------------------------------------------------------------------

_ADVISORY_NOTICE = (
    "ADVISORY_ONLY_WALLET_INTELLIGENCE_REPORT — This report is derived from "
    "local observation fixture records, wallet signal research profiles, and "
    "copyability delay evaluations. It is for human analyst review only. "
    "It does not prove a wallet is usable for automated following. "
    "It does not estimate performance. "
    "It does not create account-action guidance. "
    "It does not place or simulate account orders. "
    "Manual research and human review are required before any use."
)

_LIMITATIONS_NOTICE = (
    "This report is generated from local/offline fixture data only. "
    "No live wallet data, live market prices, or real-time API feeds were used. "
    "Evaluation results reflect static local research fixtures, not current market "
    "conditions. All findings require human review before any research use."
)

_NO_AUTOMATED_ACTION_NOTICE = (
    "This report contains no automated-action guidance, no account-action "
    "recommendations, no sizing inputs, no performance estimates, "
    "no automated-following instructions, and no live-account inputs of any kind."
)

_NO_LIVE_DATA_NOTICE = (
    "No live market data, live wallet data, authenticated API access, or "
    "real-time pricing was used to generate this report."
)

# ---------------------------------------------------------------------------
# Safety flags (all must be True in every report)
# ---------------------------------------------------------------------------

_SAFETY_FLAGS: dict[str, bool] = {
    "manual_research_only": True,
    "not_automated_copy_trading": True,
    "no_live_execution": True,
    "no_order_placement": True,
    "no_position_sizing": True,
    "no_risk_override": True,
    "no_parameter_auto_change": True,
}

# ---------------------------------------------------------------------------
# Deferred items section
# ---------------------------------------------------------------------------

_DEFERRED_ITEMS: dict[str, str] = {
    "wallet_signal_paper_strategy_contract": "DEFERRED_TO_WP83",
    "real_wallet_api_ingestion": "FORBIDDEN_UNTIL_APPROVED_WP",
    "automated_following_forbidden": "FORBIDDEN",
    "live_account_action_forbidden": "FORBIDDEN",
    "wallet_api_ingestion_forbidden": "FORBIDDEN",
}

# ---------------------------------------------------------------------------
# Report dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class WalletIntelligenceReport:
    """Advisory local wallet intelligence report.

    This is not a trade signal, copy-trading instruction, position sizing
    input, expected-return estimate, buy/sell recommendation, PnL computation,
    or live execution permission. It is advisory research metadata only.
    Human review is required before any use.

    Added in WP82.
    """

    report_type: str
    advisory_label: str
    advisory_notice: str
    report_identity: Mapping[str, object]
    input_summary: Mapping[str, object]
    wallet_signal_summary: Mapping[str, object]
    copyability_delay_summary: Mapping[str, object]
    research_queue_implications: Mapping[str, object]
    suspicious_flow_review: Mapping[str, object]
    limitations: Mapping[str, object]
    deferred_items: Mapping[str, object]
    safety: Mapping[str, bool]
    warnings: tuple[str, ...]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _safe_str(val: object) -> str:
    return str(val).strip() if isinstance(val, str) else ""


def _count_by(items: list[object], attr: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        key = _safe_str(getattr(item, attr, None))
        if not key:
            key = "UNKNOWN"
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))


def _build_report_identity(
    wp_version: str,
    metadata: Mapping[str, object] | None,
) -> dict[str, object]:
    return {
        "report_type": REPORT_TYPE,
        "wp_version": wp_version,
        "advisory_only_notice": _ADVISORY_NOTICE,
        "design_example_only": False,
        "source_metadata": dict(metadata) if metadata else {},
    }


def _build_input_summary(
    profiles: list[object],
    evaluations: list[object],
    annotations: list[object],
) -> dict[str, object]:
    market_ids: set[str] = set()
    condition_ids: set[str] = set()
    for p in profiles:
        mid = _safe_str(getattr(p, "market_id", None))
        cid = _safe_str(getattr(p, "condition_id", None))
        if mid:
            market_ids.add(mid)
        if cid:
            condition_ids.add(cid)

    return {
        "wallet_signal_profile_count": len(profiles),
        "copyability_delay_evaluation_count": len(evaluations),
        "research_queue_annotation_count": len(annotations),
        "market_count": len(market_ids),
        "condition_count": len(condition_ids),
        "fixture_validation_status": "LOCAL_FIXTURE_ONLY",
        "no_live_data": True,
        "no_network": True,
        "advisory_only_notice": _ADVISORY_NOTICE,
    }


def _build_wallet_signal_summary(
    profiles: list[object],
) -> dict[str, object]:
    suspicious_count = sum(
        1 for p in profiles
        if _safe_str(getattr(p, "suspicious_flow_status", None)) not in (
            "NO_SUSPICIOUS_FLOW_FLAG", ""
        )
    )
    human_review_count = sum(
        1 for p in profiles
        if getattr(p, "human_review_required", False)
    )
    signal_distribution = _count_by(profiles, "signal_category")

    return {
        "profile_count": len(profiles),
        "signal_category_distribution": signal_distribution,
        "suspicious_flow_count": suspicious_count,
        "human_review_required_count": human_review_count,
        "advisory_only_notice": _ADVISORY_NOTICE,
    }


def _build_copyability_delay_summary(
    evaluations: list[object],
) -> dict[str, object]:
    status_distribution = _count_by(evaluations, "evaluation_status")

    suspicious_blocked = sum(
        1 for e in evaluations
        if _safe_str(getattr(e, "evaluation_status", None))
        == "SUSPICIOUS_FLOW_DO_NOT_COPY"
    )
    uncopyable_fast = sum(
        1 for e in evaluations
        if _safe_str(getattr(e, "evaluation_status", None))
        == "UNCOPYABLE_FAST_FLOW"
    )
    uncopyable_illiquid = sum(
        1 for e in evaluations
        if _safe_str(getattr(e, "evaluation_status", None))
        == "UNCOPYABLE_TOO_ILLIQUID"
    )
    insufficient_context = sum(
        1 for e in evaluations
        if _safe_str(getattr(e, "evaluation_status", None))
        == "INSUFFICIENT_CONTEXT"
    )
    human_review_count = sum(
        1 for e in evaluations
        if getattr(e, "human_review_required", False)
    )

    delay_windows_assessed = list(dict.fromkeys(
        _safe_str(getattr(e, "delay_window", None))
        for e in evaluations
        if _safe_str(getattr(e, "delay_window", None))
    ))
    delay_windows_assessed.sort()

    return {
        "evaluation_count": len(evaluations),
        "delay_windows_assessed": delay_windows_assessed,
        "evaluation_status_distribution": status_distribution,
        "suspicious_flow_blocked_count": suspicious_blocked,
        "uncopyable_fast_flow_count": uncopyable_fast,
        "uncopyable_illiquid_count": uncopyable_illiquid,
        "insufficient_context_count": insufficient_context,
        "human_review_required_count": human_review_count,
        "advisory_only_notice": _ADVISORY_NOTICE,
    }


def _build_research_queue_implications(
    annotations: list[object],
) -> dict[str, object]:
    effect_distribution = _count_by(annotations, "research_priority_effect")
    human_review_additions = sum(
        1 for a in annotations
        if getattr(a, "human_review_required", False)
    )
    markets_flagged = sum(
        1 for a in annotations
        if _safe_str(getattr(a, "research_priority_effect", None))
        not in ("NO_CHANGE", "NOT_EVALUATED", "")
    )

    return {
        "annotation_count": len(annotations),
        "markets_flagged_for_research": markets_flagged,
        "research_priority_effect_summary": effect_distribution,
        "human_review_queue_additions": human_review_additions,
        "advisory_only_notice": _ADVISORY_NOTICE,
    }


def _build_suspicious_flow_review(
    profiles: list[object],
    evaluations: list[object],
) -> dict[str, object]:
    suspicious_profiles = [
        p for p in profiles
        if _safe_str(getattr(p, "suspicious_flow_status", None))
        not in ("NO_SUSPICIOUS_FLOW_FLAG", "")
    ]
    suspicious_evals = [
        e for e in evaluations
        if _safe_str(getattr(e, "evaluation_status", None))
        == "SUSPICIOUS_FLOW_DO_NOT_COPY"
    ]

    event_references: list[dict[str, object]] = []
    for p in suspicious_profiles:
        event_references.append({
            "wallet_id_or_address": _safe_str(getattr(p, "wallet_id_or_address", None)),
            "market_id": _safe_str(getattr(p, "market_id", None)),
            "condition_id": _safe_str(getattr(p, "condition_id", None)),
            "suspicious_flow_status": _safe_str(getattr(p, "suspicious_flow_status", None)),
            "required_action": "HUMAN_REVIEW_REQUIRED",
            "blocked_from_automation": True,
        })

    return {
        "suspicious_profile_count": len(suspicious_profiles),
        "suspicious_evaluation_count": len(suspicious_evals),
        "suspicious_flow_events": event_references,
        "required_action_for_all": "HUMAN_REVIEW_REQUIRED",
        "blocked_from_automation": True,
        "advisory_only_notice": _ADVISORY_NOTICE,
    }


def _build_limitations() -> dict[str, object]:
    return {
        "data_source_limitations": _LIMITATIONS_NOTICE,
        "no_live_data_notice": _NO_LIVE_DATA_NOTICE,
        "no_automated_action_notice": _NO_AUTOMATED_ACTION_NOTICE,
        "evaluation_limitations": (
            "Evaluations are derived from local fixture data only. "
            "Spread context, liquidity context, fee context, size limit context, "
            "and resolved outcome context may be absent or incomplete."
        ),
        "advisory_only_notice": _ADVISORY_NOTICE,
    }


def _collect_warnings(
    profiles: list[object],
    evaluations: list[object],
    annotations: list[object],
    metadata_was_redacted: bool = False,
) -> tuple[str, ...]:
    warnings: list[str] = []

    if metadata_was_redacted:
        warnings.append(
            "One or more metadata entries were redacted because they violated "
            "the advisory report vocabulary boundary."
        )

    if not profiles:
        warnings.append(
            "No wallet signal research profiles provided; report sections derived "
            "from profiles will reflect zero counts."
        )
    if not evaluations:
        warnings.append(
            "No copyability delay evaluations provided; delay summary reflects "
            "zero counts."
        )
    if not annotations:
        warnings.append(
            "No research queue annotations provided; research queue implications "
            "section reflects zero counts."
        )

    suspicious_count = sum(
        1 for p in profiles
        if _safe_str(getattr(p, "suspicious_flow_status", None))
        not in ("NO_SUSPICIOUS_FLOW_FLAG", "")
    )
    if suspicious_count > 0:
        warnings.append(
            f"{suspicious_count} wallet signal profile(s) have suspicious flow "
            "flags. Human review is required. These profiles are blocked from "
            "automation use."
        )

    human_review_eval_count = sum(
        1 for e in evaluations
        if getattr(e, "human_review_required", False)
    )
    if human_review_eval_count > 0:
        warnings.append(
            f"{human_review_eval_count} copyability delay evaluation(s) require "
            "human review."
        )

    return tuple(warnings)


# ---------------------------------------------------------------------------
# Public report builder
# ---------------------------------------------------------------------------

def build_wallet_intelligence_report(
    profiles: Iterable[object],
    evaluations: Iterable[object],
    annotations: Iterable[object],
    wp_version: str = "WP82",
    metadata: Mapping[str, object] | None = None,
) -> WalletIntelligenceReport:
    """Build a deterministic advisory wallet intelligence report from local fixtures.

    Consumes:
    - profiles: WalletSignalResearchProfile records (WP79) or duck-typed equivalents.
    - evaluations: WalletCopyabilityDelayEvaluation records (WP81) or duck-typed equivalents.
    - annotations: WalletResearchQueueAnnotation records (WP79) or duck-typed equivalents.
    - wp_version: string identifying the work package that generated this report.
    - metadata: optional explicit local metadata dict; not fetched from network.

    Returns a frozen WalletIntelligenceReport with all required advisory sections.

    This function is advisory research metadata only. It does not fetch network
    data, compute dollar PnL, expected return, or position size, produce
    buy/sell signals, place orders, write files, access credentials, or run
    paper/live trading.
    """
    profile_list = sorted(
        profiles,
        key=lambda p: (
            _safe_str(getattr(p, "wallet_id_or_address", None)),
            _safe_str(getattr(p, "market_id", None)),
            _safe_str(getattr(p, "condition_id", None)),
        ),
    )
    eval_list = sorted(
        evaluations,
        key=lambda e: (
            _safe_str(getattr(e, "wallet_id_or_address", None)),
            _safe_str(getattr(e, "market_id", None)),
            _safe_str(getattr(e, "condition_id", None)),
            _safe_str(getattr(e, "delay_window", None)),
        ),
    )
    annotation_list = sorted(
        annotations,
        key=lambda a: (
            _safe_str(getattr(a, "wallet_id_or_address", None)),
            _safe_str(getattr(a, "market_id", None)),
            _safe_str(getattr(a, "condition_id", None)),
        ),
    )

    sanitized_metadata: Mapping[str, object] | None = None
    metadata_was_redacted = False
    if metadata:
        sanitized_metadata, metadata_was_redacted = _sanitize_metadata(metadata)

    report_identity = _build_report_identity(wp_version, sanitized_metadata)
    input_summary = _build_input_summary(profile_list, eval_list, annotation_list)
    wallet_signal_summary = _build_wallet_signal_summary(profile_list)
    copyability_delay_summary = _build_copyability_delay_summary(eval_list)
    research_queue_implications = _build_research_queue_implications(annotation_list)
    suspicious_flow_review = _build_suspicious_flow_review(profile_list, eval_list)
    limitations = _build_limitations()
    warnings = _collect_warnings(
        profile_list, eval_list, annotation_list, metadata_was_redacted
    )

    return WalletIntelligenceReport(
        report_type=REPORT_TYPE,
        advisory_label=REPORT_ADVISORY_LABEL,
        advisory_notice=_ADVISORY_NOTICE,
        report_identity=report_identity,
        input_summary=input_summary,
        wallet_signal_summary=wallet_signal_summary,
        copyability_delay_summary=copyability_delay_summary,
        research_queue_implications=research_queue_implications,
        suspicious_flow_review=suspicious_flow_review,
        limitations=limitations,
        deferred_items=_DEFERRED_ITEMS,
        safety=_SAFETY_FLAGS,
        warnings=warnings,
    )
