"""Local/offline/read-only Market Research Priority Scoring core scorer.

WP49 minimal implementation. Advisory-only. Not a trading signal. Not expected
return. Not investment advice. Not position sizing. Not an execution instruction.
Human review required before any use.

This module is stdlib-only, performs no network access, reads no files, writes
no files, adds no CLI, and has no trading, execution, credential, account,
wallet, Hermes, LLM, database, dashboard, scheduler, or polling behavior.
"""

from __future__ import annotations

ADVISORY_LABEL = "ADVISORY_ONLY_HUMAN_REVIEW_REQUIRED"
SCHEMA_VERSION = "1.0"

FORBIDDEN_USE_NOTICE = (
    "This output is not a trading signal, not expected return, not position "
    "sizing, and not an execution instruction. It is for human research triage "
    "only. ADVISORY_ONLY_HUMAN_REVIEW_REQUIRED."
)

FORBIDDEN_OUTPUT_FIELDS: frozenset[str] = frozenset({
    "trade_signal",
    "alpha_score",
    "opportunity_score",
    "expected_return",
    "profit_probability",
    "buy_recommendation",
    "sell_recommendation",
    "entry",
    "exit",
    "position_size",
    "leverage",
    "execution_confidence",
    "order_params",
    "strategy_signal",
    "paper_trade_authorization",
    "live_trade_authorization",
})

REQUIRED_TOP_LEVEL_FIELDS: tuple[str, ...] = (
    "schema_version",
    "generated_at_utc",
    "run_id",
    "source_artifacts",
    "advisory_label",
    "human_review_required",
    "scope",
    "markets",
    "contract_warnings",
    "forbidden_use_notice",
)

REQUIRED_MARKET_FIELDS: tuple[str, ...] = (
    "market_id",
    "question",
    "category",
    "active_status",
    "research_priority_score",
    "score_rank",
    "score_components",
    "staleness",
    "provenance",
    "missing_data",
    "quality_gates",
    "component_explanation",
    "advisory_label",
    "human_review_required",
    "forbidden_use_notice",
)

POSITIVE_COMPONENTS: tuple[str, ...] = (
    "data_completeness",
    "snapshot_freshness",
    "quality_gate_status",
    "market_activity_metadata",
    "category_coverage",
    "token_outcome_completeness",
    "order_book_availability",
    "spread_structure_observed",
    "visible_local_liquidity_proxy",
    "guard_provenance_quality",
)

PENALTY_COMPONENTS: tuple[str, ...] = (
    "duplicate_conflict_penalty",
    "missing_data_penalty",
    "deferred_item_caveat_penalty",
)

RESEARCH_PRIORITY_COMPONENTS: tuple[str, ...] = POSITIVE_COMPONENTS + PENALTY_COMPONENTS

_STALE_CAP = 0.3
_MISSING_PROVENANCE_CAP = 0.2
_MISSING_DATA_CAP = 0.5
_DEGRADED_QUALITY_CAP = 0.5
_FAILING_QUALITY_CAP = 0.2
_UNKNOWN_QUALITY_CAP = 0.5
_ACCEPTABLE_QUALITY_STATUSES = frozenset({"ACCEPTABLE"})


class MarketResearchPriorityOutputError(ValueError):
    """Raised when market research priority scoring output fails validation."""


def compute_research_priority_score(
    score_components: dict,
    staleness: dict,
    provenance: dict,
    missing_data: dict,
    quality_gates: dict,
) -> float:
    """Compute a deterministic bounded research-priority score in [0.0, 1.0].

    Higher means higher priority for human research triage only — this market has
    more complete, fresh, and quality-checked local data. Not a trading signal.

    Missing positive components default to 0.0 (never default high).
    Stale, missing-provenance, missing-data, and poor-quality-gate inputs are capped.
    """
    # Positive components: missing/None → 0.0 (not neutral, not high)
    positive_vals: list[float] = []
    for key in POSITIVE_COMPONENTS:
        val = score_components.get(key)
        if val is None:
            positive_vals.append(0.0)
        else:
            positive_vals.append(max(0.0, min(1.0, float(val))))

    positive_avg = sum(positive_vals) / len(POSITIVE_COMPONENTS)

    # Penalty components: missing/None → 0.0 (no unearned penalty assumed)
    penalty_vals: list[float] = []
    for key in PENALTY_COMPONENTS:
        val = score_components.get(key)
        if val is None:
            penalty_vals.append(0.0)
        else:
            penalty_vals.append(max(-1.0, min(0.0, float(val))))

    penalty_avg = sum(penalty_vals) / len(PENALTY_COMPONENTS)

    score = positive_avg + penalty_avg

    # Staleness cap: stale data must never default high
    if staleness.get("staleness_flag"):
        score = min(score, _STALE_CAP)

    # Missing provenance cap: unidentified sources degrade score
    manifest_ids = provenance.get("snapshot_manifest_ids") or []
    export_paths = provenance.get("source_export_paths") or []
    if not manifest_ids and not export_paths:
        score = min(score, _MISSING_PROVENANCE_CAP)

    # Missing data cap
    if missing_data.get("missing_data_warning"):
        score = min(score, _MISSING_DATA_CAP)

    # Quality gate cap
    quality_status = quality_gates.get("quality_status", "UNKNOWN")
    if quality_status == "FAILING":
        score = min(score, _FAILING_QUALITY_CAP)
    elif quality_status in ("DEGRADED", "UNKNOWN"):
        cap = _DEGRADED_QUALITY_CAP if quality_status == "DEGRADED" else _UNKNOWN_QUALITY_CAP
        score = min(score, cap)

    return float(max(0.0, min(1.0, score)))


def _collect_contract_warnings(
    score_components: dict,
    staleness: dict,
    provenance: dict,
    missing_data: dict,
    quality_gates: dict,
    market_id: str | None = None,
) -> list[str]:
    """Collect human-readable warnings for degraded scoring inputs."""
    warnings: list[str] = []
    prefix = f"[{market_id}] " if market_id else ""

    for key in POSITIVE_COMPONENTS:
        if score_components.get(key) is None:
            warnings.append(
                f"{prefix}Missing positive component '{key}' treated as 0.0."
            )

    if staleness.get("staleness_flag"):
        msg = staleness.get("staleness_warning") or "Stale data detected."
        warnings.append(
            f"{prefix}Staleness: {msg} Score capped at {_STALE_CAP}."
        )

    manifest_ids = provenance.get("snapshot_manifest_ids") or []
    export_paths = provenance.get("source_export_paths") or []
    if not manifest_ids and not export_paths:
        warnings.append(
            f"{prefix}Missing provenance: no snapshot_manifest_ids or "
            f"source_export_paths. Score capped at {_MISSING_PROVENANCE_CAP}."
        )

    if missing_data.get("missing_data_warning"):
        reason = (
            missing_data.get("insufficient_coverage_reason")
            or "Insufficient data coverage."
        )
        warnings.append(
            f"{prefix}Missing data warning: {reason} "
            f"Score capped at {_MISSING_DATA_CAP}."
        )

    quality_status = quality_gates.get("quality_status", "UNKNOWN")
    if quality_status == "FAILING":
        warnings.append(
            f"{prefix}Quality gate FAILING. Score capped at {_FAILING_QUALITY_CAP}."
        )
    elif quality_status == "DEGRADED":
        warnings.append(
            f"{prefix}Quality gate DEGRADED. Score capped at {_DEGRADED_QUALITY_CAP}."
        )
    elif quality_status == "UNKNOWN":
        warnings.append(
            f"{prefix}Quality gate UNKNOWN. Score capped at {_UNKNOWN_QUALITY_CAP}."
        )

    return warnings


def build_market_research_priority_output(
    run_context: dict,
    market_context: dict,
) -> dict:
    """Build an in-memory contract-shaped market research priority scoring output.

    Returns a dict shaped per the WP48 output contract. Advisory-only.
    Not a trading signal. Human review required before any use.
    """
    market_id = market_context.get("market_id", "")
    score_components: dict = market_context.get("score_components") or {}
    staleness: dict = market_context.get("staleness") or {}
    provenance: dict = market_context.get("provenance") or {}
    missing_data: dict = market_context.get("missing_data") or {}
    quality_gates: dict = market_context.get("quality_gates") or {}

    score = compute_research_priority_score(
        score_components, staleness, provenance, missing_data, quality_gates
    )
    warnings = _collect_contract_warnings(
        score_components, staleness, provenance, missing_data, quality_gates,
        market_id=str(market_id) if market_id else None,
    )

    market_obj: dict = {
        "market_id": market_id,
        "question": market_context.get("question", ""),
        "category": market_context.get("category"),
        "active_status": market_context.get("active_status"),
        "research_priority_score": score,
        # score_rank is None in WP49 — ranking across multiple markets not implemented.
        # Not a trading rank.
        "score_rank": None,
        "score_components": score_components,
        "staleness": staleness,
        "provenance": provenance,
        "missing_data": missing_data,
        "quality_gates": quality_gates,
        "component_explanation": market_context.get("component_explanation", ""),
        "advisory_label": ADVISORY_LABEL,
        "human_review_required": True,
        "forbidden_use_notice": FORBIDDEN_USE_NOTICE,
    }

    output: dict = {
        "schema_version": SCHEMA_VERSION,
        "generated_at_utc": run_context.get("generated_at_utc", ""),
        "run_id": run_context.get("run_id", ""),
        "source_artifacts": run_context.get("source_artifacts") or {},
        "advisory_label": ADVISORY_LABEL,
        "human_review_required": True,
        "scope": run_context.get("scope") or {},
        "markets": [market_obj],
        "contract_warnings": warnings,
        "forbidden_use_notice": FORBIDDEN_USE_NOTICE,
    }

    return output


def validate_market_research_priority_output(output: dict) -> list[str]:
    """Validate a market research priority scoring output dict.

    Returns a list of human-readable error strings. Empty list means valid.
    Does not raise; returns all errors for caller inspection.
    """
    errors: list[str] = []

    forbidden_found = contains_forbidden_output_fields(output)
    for field in forbidden_found:
        errors.append(f"Forbidden field found in output: '{field}'")

    for field in REQUIRED_TOP_LEVEL_FIELDS:
        if field not in output:
            errors.append(f"Missing required top-level field: '{field}'")

    if output.get("advisory_label") != ADVISORY_LABEL:
        errors.append(
            f"advisory_label must be exactly '{ADVISORY_LABEL}', "
            f"got: {output.get('advisory_label')!r}"
        )

    if output.get("human_review_required") is not True:
        errors.append(
            f"human_review_required must be True, "
            f"got: {output.get('human_review_required')!r}"
        )

    markets = output.get("markets")
    if not isinstance(markets, list):
        errors.append("'markets' must be a list")
    else:
        for i, market in enumerate(markets):
            errors.extend(_validate_market_object(market, index=i))

    return errors


def _validate_market_object(market: object, index: int = 0) -> list[str]:
    """Validate a single market object. Returns list of error strings."""
    errors: list[str] = []
    prefix = f"market[{index}]"

    if not isinstance(market, dict):
        errors.append(f"{prefix}: not a dict")
        return errors

    for field in REQUIRED_MARKET_FIELDS:
        if field not in market:
            errors.append(f"{prefix}: missing required field '{field}'")

    score = market.get("research_priority_score")
    if score is not None:
        try:
            score_f = float(score)
            if score_f < 0.0:
                errors.append(
                    f"{prefix}: research_priority_score {score_f} < 0.0"
                )
            if score_f > 1.0:
                errors.append(
                    f"{prefix}: research_priority_score {score_f} > 1.0"
                )
        except (TypeError, ValueError):
            errors.append(
                f"{prefix}: research_priority_score is not a number: {score!r}"
            )

    if market.get("advisory_label") != ADVISORY_LABEL:
        errors.append(
            f"{prefix}: advisory_label must be exactly '{ADVISORY_LABEL}', "
            f"got: {market.get('advisory_label')!r}"
        )

    if market.get("human_review_required") is not True:
        errors.append(
            f"{prefix}: human_review_required must be True, "
            f"got: {market.get('human_review_required')!r}"
        )

    return errors


def assert_market_research_priority_output(output: dict) -> None:
    """Assert that output passes validation.

    Raises MarketResearchPriorityOutputError listing all validation errors
    if validation fails. No-op if validation passes.
    """
    errors = validate_market_research_priority_output(output)
    if errors:
        msg = (
            "Market research priority scoring output validation failed:\n"
            + "\n".join(f"  - {e}" for e in errors)
        )
        raise MarketResearchPriorityOutputError(msg)


def contains_forbidden_output_fields(output: object) -> list[str]:
    """Recursively scan output for forbidden field names.

    Returns a list of forbidden field names found anywhere in the structure
    (including nested dicts and lists). Each name appears at most once.
    """
    found: list[str] = []
    _scan_forbidden(output, found)
    return found


def _scan_forbidden(obj: object, found: list[str]) -> None:
    """Recursive helper for contains_forbidden_output_fields."""
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key in FORBIDDEN_OUTPUT_FIELDS and key not in found:
                found.append(key)
            _scan_forbidden(value, found)
    elif isinstance(obj, (list, tuple)):
        for item in obj:
            _scan_forbidden(item, found)
