"""Local/offline/read-only wallet signal research profile builder and research queue annotation.

Consumes only already-loaded/validated WP78 LoadedWalletTradeEventRecord objects.
Produces deterministic advisory wallet signal classifications and research queue
annotations.

This module is advisory research metadata only.

It does not:
- fetch wallet data from any network or API source;
- monitor real wallets;
- copy wallets;
- rank wallets for trading;
- compute copyability PnL or expected return;
- produce buy/sell/trade/execute/position-sizing instructions;
- modify scoring weights;
- place orders, cancel orders, size positions, or override risk;
- write files;
- access credentials or authentication clients;
- invoke LLM, Hermes, scheduler, dashboard, or bot loop;
- run paper or live trading.

Stdlib-only. No network access. No credentials. No file writes.

Added in WP79.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping


# ---------------------------------------------------------------------------
# Advisory labels
# ---------------------------------------------------------------------------

PROFILE_ADVISORY_LABEL = "ADVISORY_ONLY_WALLET_SIGNAL_RESEARCH_PROFILE"
ANNOTATION_ADVISORY_LABEL = "ADVISORY_ONLY_WALLET_RESEARCH_QUEUE_ANNOTATION"

# ---------------------------------------------------------------------------
# Allowed status constants
# ---------------------------------------------------------------------------

SAMPLE_SIZE_SINGLE_EVENT = "SINGLE_EVENT_LOW_SAMPLE"
SAMPLE_SIZE_SMALL = "SMALL_SAMPLE_REVIEW_ONLY"
SAMPLE_SIZE_SUFFICIENT = "SUFFICIENT_FOR_RESEARCH_CONTEXT"
SAMPLE_SIZE_NOT_EVALUATED = "NOT_EVALUATED"

SIGNAL_SPECIALIST_ENTRY = "SPECIALIST_ENTRY"
SIGNAL_MULTI_WALLET_CLUSTER = "MULTI_WALLET_CLUSTER"
SIGNAL_EARLY_ENTRY = "EARLY_ENTRY_BEFORE_PRICE_MOVE"
SIGNAL_LATE_CHASER = "LATE_CHASER"
SIGNAL_MARKET_MAKER = "MARKET_MAKER_FLOW"
SIGNAL_ARBITRAGE = "ARBITRAGE_FLOW"
SIGNAL_SUSPICIOUS_TIMING = "SUSPICIOUS_TIMING"
SIGNAL_LOW_SAMPLE_OUTLIER = "LOW_SAMPLE_OUTLIER"
SIGNAL_UNCOPYABLE_FAST = "UNCOPYABLE_FAST_FLOW"
SIGNAL_UNKNOWN = "UNKNOWN_WALLET_SIGNAL"

ALLOWED_SIGNAL_CATEGORIES: frozenset[str] = frozenset({
    SIGNAL_SPECIALIST_ENTRY,
    SIGNAL_MULTI_WALLET_CLUSTER,
    SIGNAL_EARLY_ENTRY,
    SIGNAL_LATE_CHASER,
    SIGNAL_MARKET_MAKER,
    SIGNAL_ARBITRAGE,
    SIGNAL_SUSPICIOUS_TIMING,
    SIGNAL_LOW_SAMPLE_OUTLIER,
    SIGNAL_UNCOPYABLE_FAST,
    SIGNAL_UNKNOWN,
})

SPEC_MATCH_MATCHED = "MATCHED_CATEGORY_CONTEXT"
SPEC_MATCH_UNMATCHED = "UNMATCHED_CATEGORY_CONTEXT"
SPEC_MATCH_UNKNOWN = "UNKNOWN_CATEGORY_CONTEXT"

SUSPICIOUS_NO_FLAG = "NO_SUSPICIOUS_FLOW_FLAG"
SUSPICIOUS_WATCH_ONLY = "SUSPICIOUS_FLOW_RESEARCH_WATCH_ONLY"
SUSPICIOUS_HUMAN_REVIEW = "SUSPICIOUS_FLOW_HUMAN_REVIEW_REQUIRED"

COPY_NOT_EVALUATED = "NOT_EVALUATED"
COPY_UNPROVEN = "COPYABILITY_UNPROVEN"
COPY_UNCOPYABLE_FAST = "UNCOPYABLE_FAST_FLOW"
COPY_SUSPICIOUS_DO_NOT_COPY = "SUSPICIOUS_FLOW_DO_NOT_COPY"

EFFECT_NO_CHANGE = "NO_CHANGE"
EFFECT_LOW_BOOST = "LOW_RESEARCH_BOOST"
EFFECT_MEDIUM_BOOST = "MEDIUM_RESEARCH_BOOST"
EFFECT_HIGH_BOOST = "HIGH_RESEARCH_BOOST"
EFFECT_CAP = "CAP_RESEARCH_PRIORITY"
EFFECT_REQUIRE_HUMAN_REVIEW = "REQUIRE_HUMAN_REVIEW"
EFFECT_BLOCK_FROM_AUTOMATION = "BLOCK_FROM_AUTOMATION"

ALLOWED_RESEARCH_PRIORITY_EFFECTS: frozenset[str] = frozenset({
    EFFECT_NO_CHANGE,
    EFFECT_LOW_BOOST,
    EFFECT_MEDIUM_BOOST,
    EFFECT_HIGH_BOOST,
    EFFECT_CAP,
    EFFECT_REQUIRE_HUMAN_REVIEW,
    EFFECT_BLOCK_FROM_AUTOMATION,
})

# Forbidden trade-like values that must never appear in outputs
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
    "LIVE_SIGNAL",
    "AUTO_COPY",
    "TRADE_READY",
    "COPY_READY",
    "LIVE_READY",
    "BUY_SIGNAL",
    "SELL_SIGNAL",
})

# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class WalletSignalResearchProfile:
    """Advisory wallet signal research profile derived from local validated fixtures.

    This is not a wallet ranking, copy-trading instruction, buy/sell signal,
    expected-return estimate, position sizing input, or live-trading permission.
    Human review is required before any use.
    """

    wallet_id_or_address: str
    market_id: str
    condition_id: str
    market_category: str
    event_count: int
    sample_size_status: str
    signal_category: str
    wallet_specialization_match: str
    suspicious_flow_status: str
    copyability_status: str
    research_priority_effect: str
    human_review_required: bool
    warnings: tuple[str, ...]
    advisory_label: str


@dataclass(frozen=True)
class WalletResearchQueueAnnotation:
    """Advisory research queue annotation derived from a wallet signal research profile.

    This is not a trade signal, position sizing instruction, expected return, or
    execution input. It is advisory metadata for human research queue ordering only.
    Human review is required before any use.
    """

    wallet_id_or_address: str
    market_id: str
    condition_id: str
    research_priority_effect: str
    human_review_required: bool
    suspicious_flow_status: str
    sample_size_status: str
    signal_category: str
    advisory_label: str
    advisory_notice: str


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


def _classify_sample_size(event_count: int) -> str:
    if event_count <= 0:
        return SAMPLE_SIZE_NOT_EVALUATED
    if event_count == 1:
        return SAMPLE_SIZE_SINGLE_EVENT
    if event_count < 5:
        return SAMPLE_SIZE_SMALL
    return SAMPLE_SIZE_SUFFICIENT


def _classify_signal(
    event_count: int,
    suspicious_flow: bool,
    copyability_context_available: bool,
    market_category: str,
) -> str:
    if event_count <= 0:
        return SIGNAL_UNKNOWN
    if suspicious_flow:
        return SIGNAL_SUSPICIOUS_TIMING
    if not copyability_context_available:
        return SIGNAL_UNCOPYABLE_FAST
    if event_count == 1:
        return SIGNAL_LOW_SAMPLE_OUTLIER
    if market_category and market_category.strip():
        return SIGNAL_SPECIALIST_ENTRY
    return SIGNAL_UNKNOWN


def _classify_specialization(market_category: str) -> str:
    cat = market_category.strip() if isinstance(market_category, str) else ""
    if not cat or cat.upper() in ("", "UNKNOWN", "N/A", "NONE"):
        return SPEC_MATCH_UNKNOWN
    return SPEC_MATCH_MATCHED


def _classify_suspicious_flow(suspicious_flow_flag: bool, human_review_required: bool) -> str:
    if not suspicious_flow_flag:
        return SUSPICIOUS_NO_FLAG
    if human_review_required:
        return SUSPICIOUS_HUMAN_REVIEW
    return SUSPICIOUS_WATCH_ONLY


def _classify_copyability(suspicious_flow_flag: bool, copyability_context_available: bool) -> str:
    if suspicious_flow_flag:
        return COPY_SUSPICIOUS_DO_NOT_COPY
    if not copyability_context_available:
        return COPY_UNCOPYABLE_FAST
    return COPY_UNPROVEN


def _determine_research_priority_effect(
    suspicious_flow_status: str,
    sample_size_status: str,
    signal_category: str,
) -> str:
    if suspicious_flow_status == SUSPICIOUS_HUMAN_REVIEW:
        return EFFECT_BLOCK_FROM_AUTOMATION
    if suspicious_flow_status == SUSPICIOUS_WATCH_ONLY:
        return EFFECT_REQUIRE_HUMAN_REVIEW
    if sample_size_status == SAMPLE_SIZE_NOT_EVALUATED:
        return EFFECT_NO_CHANGE
    if sample_size_status == SAMPLE_SIZE_SINGLE_EVENT:
        return EFFECT_NO_CHANGE
    if signal_category in (SIGNAL_UNKNOWN, SIGNAL_UNCOPYABLE_FAST):
        return EFFECT_NO_CHANGE
    if sample_size_status == SAMPLE_SIZE_SMALL:
        return EFFECT_LOW_BOOST
    return EFFECT_MEDIUM_BOOST


def _build_warnings(
    suspicious_flow_status: str,
    sample_size_status: str,
    copyability_status: str,
    event_count: int,
    record_valid: bool,
) -> tuple[str, ...]:
    warnings: list[str] = []
    if not record_valid:
        warnings.append(
            "Record is invalid per WP78 validator; profile is derived from partial data only."
        )
    if suspicious_flow_status == SUSPICIOUS_HUMAN_REVIEW:
        warnings.append(
            "Suspicious flow detected: human review required; record blocked from automation."
        )
    elif suspicious_flow_status == SUSPICIOUS_WATCH_ONLY:
        warnings.append(
            "Suspicious flow watch: research-watch-only; human review recommended."
        )
    if sample_size_status == SAMPLE_SIZE_SINGLE_EVENT:
        warnings.append(
            "Single event only: low sample — advisory context only, not sufficient for research conclusions."
        )
    elif sample_size_status == SAMPLE_SIZE_SMALL:
        warnings.append(
            "Small sample: fewer than 5 events — review-only context, not sufficient for research conclusions."
        )
    if copyability_status == COPY_SUSPICIOUS_DO_NOT_COPY:
        warnings.append(
            "Suspicious flow: do not use for copyability evaluation or copy-trading research."
        )
    elif copyability_status == COPY_UNCOPYABLE_FAST:
        warnings.append(
            "Copyability context unavailable: flow may be too fast to copy; context not proven."
        )
    return tuple(warnings)


# ---------------------------------------------------------------------------
# Key extraction
# ---------------------------------------------------------------------------

def _extract_profile_fields(
    loaded_record: object,
) -> dict | None:
    """Extract profile fields from a LoadedWalletTradeEventRecord.

    Returns None if the record is not a valid-shaped object.
    Accepts both valid and invalid records but warns on invalid.
    """
    # Use duck-typing so tests can pass lightweight objects or real records.
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

    wallet_id = _get_str(wallet_ref, "wallet_id_or_address")
    market_id = _get_str(market_ref, "market_id")
    condition_id = _get_str(market_ref, "condition_id")
    market_category = _get_str(market_ref, "market_category")

    suspicious_flow_flag = _get_bool(review, "suspicious_flow_flag")
    human_review_required = _get_bool(review, "human_review_required")
    copyability_context_available = _get_bool(context, "copyability_context_available")

    if not wallet_id:
        wallet_id = "UNKNOWN_WALLET"
    if not market_id:
        market_id = "UNKNOWN_MARKET"
    if not condition_id:
        condition_id = "UNKNOWN_CONDITION"

    return {
        "wallet_id": wallet_id,
        "market_id": market_id,
        "condition_id": condition_id,
        "market_category": market_category,
        "suspicious_flow_flag": suspicious_flow_flag,
        "human_review_required": human_review_required,
        "copyability_context_available": copyability_context_available,
        "is_valid": is_valid,
    }


# ---------------------------------------------------------------------------
# Grouping key: (wallet_id, market_id, condition_id)
# ---------------------------------------------------------------------------

def _group_records(
    loaded_records: Iterable[object],
) -> dict[tuple[str, str, str], list[dict]]:
    groups: dict[tuple[str, str, str], list[dict]] = {}
    for loaded_record in loaded_records:
        fields = _extract_profile_fields(loaded_record)
        if fields is None:
            continue
        key = (fields["wallet_id"], fields["market_id"], fields["condition_id"])
        groups.setdefault(key, []).append(fields)
    return groups


# ---------------------------------------------------------------------------
# Profile builder
# ---------------------------------------------------------------------------

def build_wallet_signal_research_profiles(
    loaded_records: Iterable[object],
) -> tuple[WalletSignalResearchProfile, ...]:
    """Build deterministic advisory wallet signal research profiles.

    Consumes only already-loaded/validated WP78 LoadedWalletTradeEventRecord
    objects (or duck-typed equivalents). Groups records by
    (wallet_id_or_address, market_id, condition_id) and emits one profile
    per group.

    Returns a deterministic tuple sorted by (wallet_id, market_id, condition_id).

    This function is advisory research metadata only. It does not fetch
    network data, compute copyability PnL, produce buy/sell signals, place
    orders, size positions, modify scoring weights, write files, or run
    paper/live trading.
    """
    groups = _group_records(loaded_records)
    profiles: list[WalletSignalResearchProfile] = []

    for key in sorted(groups.keys()):
        field_list = groups[key]
        wallet_id, market_id, condition_id = key

        # Use first record for scalar fields; aggregate event_count
        first = field_list[0]
        event_count = len(field_list)
        market_category = first["market_category"]

        # Any suspicious flow in the group propagates
        suspicious_flow_flag = any(f["suspicious_flow_flag"] for f in field_list)
        # Any human review required propagates
        human_review_required = any(f["human_review_required"] for f in field_list)
        # Copyability context available only if ALL have it available
        copyability_context_available = all(f["copyability_context_available"] for f in field_list)
        # Record valid if all records are valid
        all_valid = all(f["is_valid"] for f in field_list)

        sample_size_status = _classify_sample_size(event_count)
        suspicious_flow_status = _classify_suspicious_flow(
            suspicious_flow_flag, human_review_required
        )
        copyability_status = _classify_copyability(
            suspicious_flow_flag, copyability_context_available
        )
        signal_category = _classify_signal(
            event_count, suspicious_flow_flag, copyability_context_available, market_category
        )
        wallet_specialization_match = _classify_specialization(market_category)
        research_priority_effect = _determine_research_priority_effect(
            suspicious_flow_status, sample_size_status, signal_category
        )
        human_review_required_output = (
            human_review_required
            or suspicious_flow_status == SUSPICIOUS_HUMAN_REVIEW
            or suspicious_flow_status == SUSPICIOUS_WATCH_ONLY
        )
        warnings = _build_warnings(
            suspicious_flow_status, sample_size_status, copyability_status,
            event_count, all_valid
        )

        profiles.append(
            WalletSignalResearchProfile(
                wallet_id_or_address=wallet_id,
                market_id=market_id,
                condition_id=condition_id,
                market_category=market_category,
                event_count=event_count,
                sample_size_status=sample_size_status,
                signal_category=signal_category,
                wallet_specialization_match=wallet_specialization_match,
                suspicious_flow_status=suspicious_flow_status,
                copyability_status=copyability_status,
                research_priority_effect=research_priority_effect,
                human_review_required=human_review_required_output,
                warnings=warnings,
                advisory_label=PROFILE_ADVISORY_LABEL,
            )
        )

    return tuple(profiles)


# ---------------------------------------------------------------------------
# Annotation builder
# ---------------------------------------------------------------------------

_ANNOTATION_NOTICE = (
    "ADVISORY_ONLY_WALLET_RESEARCH_QUEUE_ANNOTATION — This annotation is derived "
    "from local validated wallet trade event fixture records for advisory research "
    "queue context only. It does not prove wallet skill, prove copyability, fetch "
    "network data, create trade recommendations, place orders, size positions, "
    "override risk parameters, or authorize any live or paper trading. Human review "
    "is required before any use."
)


def build_wallet_research_queue_annotations(
    profiles: Iterable[WalletSignalResearchProfile],
) -> tuple[WalletResearchQueueAnnotation, ...]:
    """Build deterministic advisory research queue annotations from profiles.

    Returns a deterministic tuple sorted by (wallet_id, market_id, condition_id).

    This function is advisory-only. It does not modify research_priority_score
    weights, create trade signals, expected-return outputs, or position-size
    outputs. Human review is required before any use.
    """
    annotations: list[WalletResearchQueueAnnotation] = []
    for profile in sorted(
        profiles,
        key=lambda p: (p.wallet_id_or_address, p.market_id, p.condition_id),
    ):
        annotations.append(
            WalletResearchQueueAnnotation(
                wallet_id_or_address=profile.wallet_id_or_address,
                market_id=profile.market_id,
                condition_id=profile.condition_id,
                research_priority_effect=profile.research_priority_effect,
                human_review_required=profile.human_review_required,
                suspicious_flow_status=profile.suspicious_flow_status,
                sample_size_status=profile.sample_size_status,
                signal_category=profile.signal_category,
                advisory_label=ANNOTATION_ADVISORY_LABEL,
                advisory_notice=_ANNOTATION_NOTICE,
            )
        )
    return tuple(annotations)
