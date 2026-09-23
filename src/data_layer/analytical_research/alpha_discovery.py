"""Deterministic S10-ALPHA-02 observed-universe research control plane.

This module is deliberately local/offline and advisory-only.  It reads the
canonical PIT and Alpha Factory registries, but writes neither.  Its outputs are
content-addressed research evidence; they are not forecasts, qualifications,
strategies, orders, or execution instructions.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, fields, is_dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import json
import re
from typing import Mapping, Sequence

from src.data_layer.point_in_time_market_research.as_of_query import (
    QUERY_ENGINE_VERSION,
    PointInTimeQuerySpec,
    query_point_in_time_record_set,
)
from src.data_layer.point_in_time_market_research.record_store import (
    load_and_verify_point_in_time_record_store,
)
from src.data_layer.point_in_time_market_research.records import (
    MarketObservationRecord,
    ResolutionRuleSnapshotRecord,
    SourceSnapshotRecord,
)
from .alpha_factory import HypothesisFamily, OpportunityCandidate, ResearchEpisode
from .alpha_factory_registry import load_and_verify_alpha_factory_registry


ALPHA_DISCOVERY_SCHEMA_VERSION = "1.0.0"
ALPHA_DISCOVERY_PARAMETER_SET_ID = "s10-alpha-02:1.0.0"
ALPHA_DISCOVERY_STATUSES = (
    "ALPHA_DISCOVERY_VALID",
    "ALPHA_DISCOVERY_REJECTED",
)
ALPHA_DISCOVERY_ERROR_CODES = (
    "SCHEMA_UNSUPPORTED",
    "FIELD_MISSING",
    "FIELD_TYPE_INVALID",
    "FIELD_VALUE_INVALID",
    "FORBIDDEN_FIELD",
    "LIMIT_EXCEEDED",
    "PIT_STORE_INVALID",
    "PIT_QUERY_INVALID",
    "PIT_QUERY_INPUT_LIMIT_EXCEEDED",
    "ALPHA_REGISTRY_INVALID",
    "TEMPORAL_POSTURE_INVALID",
    "COMPARISON_INVALID",
    "REFERENCE_INVALID",
    "IDENTITY_DERIVATION_MISMATCH",
    "INTERNAL_VALIDATION_FAILED",
)

ANALYSIS_TEMPORAL_MODES = ("HISTORICAL_REPLAY", "CURRENT_BUILD_ANALYSIS")
ALPHA_MEMORY_TEMPORAL_POSTURES = (
    "HISTORICAL_AVAILABILITY_UNPROVEN",
    "CURRENT_REGISTRY_BUILD_TIME_ONLY",
)
FRESHNESS_STATES = ("FRESH", "STALE", "MISSING", "INVALID_CLOCK")
PRIORITY_CLASSES = (
    "MATERIAL_REOPEN",
    "EXISTING_RESEARCH_FOLLOWUP",
    "NEW_RESEARCH",
    "MARKET_EVIDENCE_ONLY",
    "EXISTING_OTHER",
    "DEFER_CAPTURE_REFRESH",
    "INELIGIBLE",
)
READINESS_STATES = ("READY", "READY_WITH_CAPTURE_GAPS", "DEFERRED", "INELIGIBLE")
FINAL_DISPOSITIONS = (
    "CORE_PRIORITY",
    "EXPLORATION",
    "AUDIT",
    "DEFERRED",
    "SKIPPED_INELIGIBLE",
    "SKIPPED_CAPACITY",
)
CAPTURE_REQUEST_TYPES = (
    "MARKET_METADATA_REFRESH",
    "ORDER_BOOK",
    "RESOLUTION_RULE",
    "SOURCE_SNAPSHOT",
)
REOPEN_DISPOSITIONS = (
    "REOPEN_ELIGIBLE",
    "REOPEN_REVIEW_REQUIRED",
    "NO_REOPEN",
    "NO_AUTOMATIC_REOPEN",
    "REOPEN_UNAVAILABLE_DATA",
    "REOPEN_UNAVAILABLE_HISTORICAL_ALPHA_MEMORY",
)
RESEARCH_ARCHETYPES = (
    "resolution_contract",
    "cross_market_logic",
    "fundamental_public_info",
    "calibration_probability",
    "wallet_public_flow",
    "microstructure",
    "maker_liquidity",
    "latency_information_arrival",
    "behavioral_structural",
    "domain_specific",
    "combinatorial_portfolio",
    "semantic_model_assisted",
    "settlement_capital_lock",
    "data_publication_latency",
)
COVERAGE_STATES = ("SUPPORTED", "PARTIAL", "DATA_MISSING", "NOT_APPLICABLE", "UNKNOWN")

HARD_CHANGE_CLASSES = (
    "MARKET_STATUS_CHANGED", "CONDITION_ID_CHANGED", "TOKEN_SET_CHANGED",
    "OUTCOME_SET_CHANGED", "RESOLUTION_RULE_CHANGED", "RESOLUTION_SOURCE_CHANGED",
    "TICK_SIZE_CHANGED", "MIN_ORDER_SIZE_CHANGED",
)
SOFT_CHANGE_CLASSES = (
    "LAST_TRADE_PRICE_MOVED", "MID_PRICE_MOVED", "SPREAD_CHANGED", "TOP_DEPTH_CHANGED",
)
REVIEW_CHANGE_CLASSES = ("QUESTION_TEXT_CHANGED", "CATEGORY_TEXT_CHANGED")

_PRIORITY_RANK = {name: rank for rank, name in enumerate(PRIORITY_CLASSES)}
_READINESS_RANK = {name: rank for rank, name in enumerate(READINESS_STATES)}
_ID_RE = re.compile(r"^[A-Za-z0-9._:-]+$")
_HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
_DECIMAL_RE = re.compile(r"^(?:0|[1-9][0-9]*)(?:\.[0-9]+)?$")
_AUTHORITY_FIELDS = {
    "expected_return", "fair_probability", "position_size", "trade_signal", "strategy",
    "qualification", "signing", "paper_order", "live_order",
    "api_key", "private_key", "credential", "scheduler_command",
}
DATA_GAP_CODES = (
    "REQUIRED_METADATA_MISSING", "OPTIONAL_METADATA_MISSING", "METADATA_CONFLICT",
    "ORDER_BOOK_MISSING", "ORDER_BOOK_STALE", "ORDER_BOOK_CONFLICT",
    "RULE_EVIDENCE_MISSING", "RULE_EVIDENCE_STALE", "RULE_EVIDENCE_CONFLICT",
    "SOURCE_EVIDENCE_MISSING", "SOURCE_EVIDENCE_STALE", "SOURCE_EVIDENCE_CONFLICT",
)
ELIGIBILITY_STATES = ("ELIGIBLE", "DEFERRED", "INELIGIBLE")
ALLOCATION_LANES = ("CORE_PRIORITY", "EXPLORATION", "AUDIT")
TRIAGE_REASON_CODES = (
    "MARKET_STATUS_INELIGIBLE", "REQUIRED_METADATA_MISSING", "METADATA_CONFLICT",
    "METADATA_STALE", "METADATA_CLOCK_INVALID", "ALPHA_MEMORY_HISTORICAL_UNPROVEN",
    "ALPHA_NO_CANONICAL_MATCH", "MATERIAL_CHANGE_REOPEN_ELIGIBLE",
    "MATERIAL_CHANGE_EXISTING_RESEARCH", "EXISTING_RESEARCH_FOLLOWUP",
    "EXISTING_RESEARCH_NO_CURRENT_TRIGGER", "NEWLY_OBSERVED_LOCALLY",
    "OPTIONAL_METADATA_MISSING", "RULE_EVIDENCE_MISSING", "RULE_EVIDENCE_STALE",
    "RULE_EVIDENCE_CONFLICT", "SOURCE_EVIDENCE_MISSING", "SOURCE_EVIDENCE_STALE",
    "SOURCE_EVIDENCE_CONFLICT", "ORDER_BOOK_MISSING", "ORDER_BOOK_STALE",
    "ORDER_BOOK_CONFLICT",
)
COMPARISON_DIAGNOSTICS = ("DATA_MISSING",)
UNUSED_CAPACITY_REASON_CODES = ("EXPLORATION_POOL_EXHAUSTED", "AUDIT_POOL_EXHAUSTED")
_MAX_TEXT = 8192
_MAX_ITEMS = 1024
_MAX_QUERY_INPUT = 256


@dataclass(frozen=True)
class AlphaDiscoveryPolicy:
    schema_version: str
    policy_version: str
    eligible_market_statuses: tuple[str, ...]
    metadata_freshness_seconds: int
    order_book_freshness_seconds: int
    resolution_rule_freshness_seconds: int
    soft_last_trade_price_abs_delta: str
    soft_mid_price_abs_delta: str
    soft_spread_abs_delta: str
    soft_top_depth_relative_delta: str
    queue_capacity: int
    exploration_slots: int
    audit_slots: int
    max_per_category: int
    audit_seed: str
    research_archetype_taxonomy_version: str
    advisory_only: bool
    no_execution_authority: bool
    no_strategy_authority: bool
    no_qualification_authority: bool
    alpha_discovery_policy_id: str


@dataclass(frozen=True)
class ResolutionRuleState:
    resolution_source_id: str
    rule_content_sha256: str
    rule_record_version_id: str
    rule_observed_time: str
    rule_freshness: str
    source_snapshot_id: str
    source_record_version_id: str | None
    source_observed_time: str | None
    source_freshness: str
    source_query_spec_sha256: str | None


@dataclass(frozen=True)
class OrderBookState:
    token_id: str
    record_version_id: str | None
    observed_time: str | None
    freshness: str
    tick_size: str | None
    minimum_order_size: str | None
    last_trade_price: str | None
    best_bid: str | None
    best_ask: str | None
    midpoint: str | None
    spread: str | None
    top_depth: str | None
    state: str


@dataclass(frozen=True)
class ObservedMarketState:
    market_id: str
    event_id: str
    market_status: str | None
    condition_id: str | None
    token_ids: tuple[str, ...]
    outcome_labels: tuple[str, ...]
    resolution_date: str | None
    category: str | None
    question_text: str | None
    metadata_record_version_id: str
    metadata_observed_time: str
    metadata_freshness: str
    metadata_query_spec_sha256: str
    rule_query_spec_sha256: str
    book_query_spec_sha256: str
    rules: tuple[ResolutionRuleState, ...]
    books: tuple[OrderBookState, ...]
    data_gap_codes: tuple[str, ...]


@dataclass(frozen=True)
class AlphaUniverseSnapshot:
    schema_version: str
    policy_id: str
    as_of: str
    cutoff_mode: str
    query_engine_version: str
    query_parameter_set_id: str
    coverage_scope: str
    external_universe_completeness: str
    markets: tuple[ObservedMarketState, ...]
    advisory_only: bool
    no_execution_authority: bool
    no_strategy_authority: bool
    no_qualification_authority: bool
    alpha_universe_snapshot_id: str


@dataclass(frozen=True)
class MaterialChangeEvent:
    schema_version: str
    policy_id: str
    prior_universe_id: str
    current_universe_id: str
    market_id: str
    hard_change_classes: tuple[str, ...]
    soft_change_classes: tuple[str, ...]
    review_only_change_classes: tuple[str, ...]
    affected_token_ids: tuple[tuple[str, tuple[str, ...]], ...]
    affected_resolution_source_ids: tuple[str, ...]
    before_record_version_ids: tuple[str, ...]
    after_record_version_ids: tuple[str, ...]
    comparison_diagnostics: tuple[str, ...]
    advisory_only: bool
    no_execution_authority: bool
    no_strategy_authority: bool
    no_qualification_authority: bool
    material_change_event_id: str

    @property
    def reopen_material(self) -> bool:
        return bool(self.hard_change_classes or self.soft_change_classes)


@dataclass(frozen=True)
class CaptureRequest:
    request_type: str
    market_id: str
    token_id: str | None
    universe_id: str
    policy_id: str
    comparison_prior_universe_id: str | None
    reason_code: str
    priority_class: str
    pre_allocation_semantic_key: str


@dataclass(frozen=True)
class PreAllocationTriageBasis:
    market_id: str
    event_id: str
    category: str | None
    eligibility: str
    priority_class: str
    reopen_disposition: str
    readiness: str
    reason_codes: tuple[str, ...]
    capture_requests: tuple[CaptureRequest, ...]
    hard_material_change_count: int
    soft_material_change_count: int
    material_change_event_id: str | None
    newly_observed_locally: bool
    comparison_prior_universe_id: str | None
    analysis_temporal_mode: str
    alpha_memory_temporal_posture: str
    alpha_registry_head_entry_hash: str | None
    matched_candidate_ids: tuple[str, ...]
    matched_hypothesis_family_ids: tuple[str, ...]
    matched_research_episode_ids: tuple[str, ...]
    coverage: tuple[tuple[str, str], ...]
    core_eligible: bool
    exploration_eligible: bool
    audit_eligible: bool

    @property
    def priority_vector(self) -> tuple[object, ...]:
        return (
            _PRIORITY_RANK[self.priority_class], -self.hard_material_change_count,
            -self.soft_material_change_count, _READINESS_RANK[self.readiness], self.market_id,
        )


@dataclass(frozen=True)
class MarketTriageDecision:
    schema_version: str
    policy_id: str
    universe_id: str
    comparison_prior_universe_id: str | None
    market_id: str
    event_id: str
    category: str | None
    eligibility: str
    priority_class: str
    reopen_disposition: str
    readiness: str
    reason_codes: tuple[str, ...]
    capture_requests: tuple[CaptureRequest, ...]
    material_change_event_id: str | None
    newly_observed_locally: bool
    final_disposition: str
    selected_lane: str | None
    audit_digest: str | None
    audit_eligible_pool_size: int | None
    audit_selection_fraction_numerator: int | None
    audit_selection_fraction_denominator: int | None
    analysis_temporal_mode: str
    alpha_memory_temporal_posture: str
    alpha_registry_head_entry_hash: str | None
    historical_alpha_memory_available: bool
    historical_selection_replay_valid: bool
    historical_replay_valid_for_alpha_memory: bool
    matched_candidate_ids: tuple[str, ...]
    matched_hypothesis_family_ids: tuple[str, ...]
    matched_research_episode_ids: tuple[str, ...]
    coverage: tuple[tuple[str, str], ...]
    advisory_only: bool
    no_execution_authority: bool
    no_strategy_authority: bool
    no_qualification_authority: bool
    market_triage_decision_id: str


@dataclass(frozen=True)
class AlphaResearchQueueSnapshot:
    schema_version: str
    policy_id: str
    universe_id: str
    comparison_prior_universe_id: str | None
    analysis_temporal_mode: str
    alpha_memory_temporal_posture: str
    alpha_registry_head_entry_hash: str | None
    historical_alpha_memory_available: bool
    historical_selection_replay_valid: bool
    core_triage_ids: tuple[str, ...]
    exploration_triage_ids: tuple[str, ...]
    audit_triage_ids: tuple[str, ...]
    deferred_triage_ids: tuple[str, ...]
    skipped_ineligible_triage_ids: tuple[str, ...]
    skipped_capacity_triage_ids: tuple[str, ...]
    all_triage_ids: tuple[str, ...]
    prior_only_market_ids: tuple[str, ...]
    queue_capacity: int
    configured_exploration_slots: int
    configured_audit_slots: int
    exploration_selected_count: int
    audit_selected_count: int
    unused_exploration_slots: int
    unused_audit_slots: int
    unused_capacity_reason_codes: tuple[str, ...]
    max_per_category: int
    advisory_only: bool
    no_execution_authority: bool
    no_strategy_authority: bool
    no_qualification_authority: bool
    alpha_research_queue_snapshot_id: str


@dataclass(frozen=True)
class AlphaDiscoveryResult:
    is_valid: bool
    status: str
    error_codes: tuple[str, ...]
    record: object | None
    records: tuple[object, ...]
    advisory_only: bool = True
    no_execution_authority: bool = True
    no_strategy_authority: bool = True
    no_qualification_authority: bool = True


class _Failure(Exception):
    def __init__(self, code: str):
        self.code = code


def _reject(code: str) -> AlphaDiscoveryResult:
    if code not in ALPHA_DISCOVERY_ERROR_CODES:
        code = "INTERNAL_VALIDATION_FAILED"
    return AlphaDiscoveryResult(False, "ALPHA_DISCOVERY_REJECTED", (code,), None, ())


def _ok(record: object | None = None, records: Sequence[object] = ()) -> AlphaDiscoveryResult:
    return AlphaDiscoveryResult(True, "ALPHA_DISCOVERY_VALID", (), record, tuple(records))


def _walk(value: object, depth: int = 0) -> None:
    if depth > 10:
        raise _Failure("LIMIT_EXCEEDED")
    if isinstance(value, float):
        raise _Failure("FIELD_TYPE_INVALID")
    if isinstance(value, str) and len(value) > _MAX_TEXT:
        raise _Failure("LIMIT_EXCEEDED")
    if isinstance(value, Mapping):
        if len(value) > _MAX_ITEMS:
            raise _Failure("LIMIT_EXCEEDED")
        for key, item in value.items():
            if not isinstance(key, str):
                raise _Failure("FIELD_TYPE_INVALID")
            if key.lower() in _AUTHORITY_FIELDS:
                raise _Failure("FORBIDDEN_FIELD")
            _walk(item, depth + 1)
    elif isinstance(value, (tuple, list)):
        if len(value) > _MAX_ITEMS:
            raise _Failure("LIMIT_EXCEEDED")
        for item in value:
            _walk(item, depth + 1)


def _canonical(value: object) -> object:
    if is_dataclass(value):
        return {f.name: _canonical(getattr(value, f.name)) for f in fields(value)}
    if isinstance(value, Mapping):
        return {str(k): _canonical(v) for k, v in sorted(value.items())}
    if isinstance(value, (tuple, list)):
        return [_canonical(v) for v in value]
    return value


def _bytes(value: object) -> bytes:
    _walk(value)
    return json.dumps(_canonical(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def _id(prefix: str, mapping: Mapping[str, object]) -> str:
    return prefix + hashlib.sha256(_bytes(mapping)).hexdigest()


def _without_id(record: object, id_field: str) -> dict[str, object]:
    mapping = _canonical(record)
    assert isinstance(mapping, dict)
    mapping.pop(id_field)
    return mapping


def _utc(value: object) -> str:
    if not isinstance(value, str):
        raise _Failure("FIELD_TYPE_INVALID")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise _Failure("FIELD_VALUE_INVALID") from None
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise _Failure("FIELD_VALUE_INVALID")
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _decimal(value: object, *, nonnegative: bool = True) -> str:
    if not isinstance(value, str) or not _DECIMAL_RE.fullmatch(value):
        raise _Failure("FIELD_VALUE_INVALID")
    try:
        number = Decimal(value)
    except InvalidOperation:
        raise _Failure("FIELD_VALUE_INVALID") from None
    if not number.is_finite() or (nonnegative and number < 0):
        raise _Failure("FIELD_VALUE_INVALID")
    normalized = format(number.normalize(), "f")
    return "0" if normalized in {"-0", "0E+0"} else normalized


def _strict_mapping(value: object, expected: set[str]) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise _Failure("FIELD_TYPE_INVALID")
    _walk(value)
    keys = set(value)
    if keys != expected:
        raise _Failure("FIELD_MISSING" if expected - keys else "FORBIDDEN_FIELD")
    return value


def _sorted_unique(values: tuple[object, ...], *, key=None) -> bool:
    return len(values) == len(set(values)) and values == tuple(sorted(values, key=key))


def _require_text(value: object) -> str:
    if not isinstance(value, str) or not value or len(value) > _MAX_TEXT:
        raise _Failure("FIELD_VALUE_INVALID")
    return value


def _require_id(value: object, prefix: str | None = None) -> str:
    text = _require_text(value)
    if not _ID_RE.fullmatch(text) or (prefix is not None and not text.startswith(prefix)):
        raise _Failure("FIELD_VALUE_INVALID")
    return text


def _require_hash(value: object) -> str:
    text = _require_text(value)
    if not _HEX64_RE.fullmatch(text):
        raise _Failure("FIELD_VALUE_INVALID")
    return text


def _require_content_id(value: object, prefix: str) -> str:
    text = _require_text(value)
    if not text.startswith(prefix) or not _HEX64_RE.fullmatch(text[len(prefix):]):
        raise _Failure("FIELD_VALUE_INVALID")
    return text


def _require_authority(record: object) -> None:
    for name in ("advisory_only", "no_execution_authority", "no_strategy_authority", "no_qualification_authority"):
        if getattr(record, name, None) is not True:
            raise _Failure("FIELD_VALUE_INVALID")


def _require_temporal_posture(record: object) -> bool:
    mode = getattr(record, "analysis_temporal_mode", None)
    historical = mode == "HISTORICAL_REPLAY"
    if mode not in ANALYSIS_TEMPORAL_MODES:
        raise _Failure("TEMPORAL_POSTURE_INVALID")
    expected = "HISTORICAL_AVAILABILITY_UNPROVEN" if historical else "CURRENT_REGISTRY_BUILD_TIME_ONLY"
    if (getattr(record, "alpha_memory_temporal_posture", None) != expected
            or getattr(record, "historical_alpha_memory_available", None) is not False
            or getattr(record, "historical_selection_replay_valid", None) is not historical):
        raise _Failure("TEMPORAL_POSTURE_INVALID")
    head = getattr(record, "alpha_registry_head_entry_hash", None)
    if historical and head is not None:
        raise _Failure("TEMPORAL_POSTURE_INVALID")
    if not historical and head is None:
        raise _Failure("TEMPORAL_POSTURE_INVALID")
    if head is not None:
        _require_content_id(head, "alpharegistryentry:sha256:")
    return historical


def _validate_capture_request(request: CaptureRequest) -> None:
    if request.request_type not in CAPTURE_REQUEST_TYPES or request.priority_class not in PRIORITY_CLASSES:
        raise _Failure("FIELD_VALUE_INVALID")
    _require_id(request.market_id, "market:")
    if request.token_id is not None:
        _require_id(request.token_id, "token:")
    _require_content_id(request.universe_id, "alphauniverse:sha256:")
    _require_content_id(request.policy_id, "alphadiscoverypolicy:sha256:")
    if request.comparison_prior_universe_id is not None:
        _require_content_id(request.comparison_prior_universe_id, "alphauniverse:sha256:")
    if request.reason_code not in (*DATA_GAP_CODES, "METADATA_STALE", "METADATA_CLOCK_INVALID"):
        raise _Failure("FIELD_VALUE_INVALID")
    expected = hashlib.sha256(_bytes((request.request_type, request.market_id, request.token_id,
        request.universe_id, request.policy_id, request.comparison_prior_universe_id,
        request.reason_code, request.priority_class))).hexdigest()
    if request.pre_allocation_semantic_key != expected:
        raise _Failure("IDENTITY_DERIVATION_MISMATCH")


def _validate_policy(record: AlphaDiscoveryPolicy) -> None:
    if record.schema_version != ALPHA_DISCOVERY_SCHEMA_VERSION:
        raise _Failure("SCHEMA_UNSUPPORTED")
    for value in (record.policy_version, record.audit_seed, record.research_archetype_taxonomy_version):
        _require_text(value)
    if (not _sorted_unique(record.eligible_market_statuses)
            or not record.eligible_market_statuses
            or any(not isinstance(x, str) or not x for x in record.eligible_market_statuses)):
        raise _Failure("FIELD_VALUE_INVALID")
    for value in (record.metadata_freshness_seconds, record.order_book_freshness_seconds,
            record.resolution_rule_freshness_seconds, record.queue_capacity, record.exploration_slots,
            record.audit_slots, record.max_per_category):
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise _Failure("FIELD_VALUE_INVALID")
    if record.exploration_slots + record.audit_slots > record.queue_capacity:
        raise _Failure("FIELD_VALUE_INVALID")
    for value in (record.soft_last_trade_price_abs_delta, record.soft_mid_price_abs_delta,
            record.soft_spread_abs_delta, record.soft_top_depth_relative_delta):
        if _decimal(value) != value:
            raise _Failure("FIELD_VALUE_INVALID")
    _require_authority(record)


def _validate_rule_state(rule: ResolutionRuleState) -> None:
    _require_id(rule.resolution_source_id)
    _require_hash(rule.rule_content_sha256)
    _require_content_id(rule.rule_record_version_id, "record:sha256:")
    if (_utc(rule.rule_observed_time) != rule.rule_observed_time
            or rule.rule_freshness not in FRESHNESS_STATES or rule.rule_freshness == "MISSING"):
        raise _Failure("FIELD_VALUE_INVALID")
    _require_content_id(rule.source_snapshot_id, "srcsnap:sha256:")
    if rule.source_record_version_id is None:
        if rule.source_observed_time is not None or rule.source_freshness != "MISSING" or rule.source_query_spec_sha256 is not None:
            raise _Failure("FIELD_VALUE_INVALID")
    else:
        _require_content_id(rule.source_record_version_id, "record:sha256:")
        if rule.source_observed_time is None or _utc(rule.source_observed_time) != rule.source_observed_time:
            raise _Failure("FIELD_VALUE_INVALID")
        if rule.source_freshness not in FRESHNESS_STATES or rule.source_query_spec_sha256 is None:
            raise _Failure("FIELD_VALUE_INVALID")
        _require_hash(rule.source_query_spec_sha256)


def _validate_book_state(book: OrderBookState) -> None:
    _require_id(book.token_id, "token:")
    if book.state not in ("ORDER_BOOK_VALID", "ORDER_BOOK_MISSING", "ORDER_BOOK_CONFLICT"):
        raise _Failure("FIELD_VALUE_INVALID")
    if book.freshness not in FRESHNESS_STATES:
        raise _Failure("FIELD_VALUE_INVALID")
    if book.record_version_id is None:
        if book.observed_time is not None or book.state == "ORDER_BOOK_VALID":
            raise _Failure("FIELD_VALUE_INVALID")
    else:
        _require_content_id(book.record_version_id, "record:sha256:")
        if book.observed_time is None or _utc(book.observed_time) != book.observed_time:
            raise _Failure("FIELD_VALUE_INVALID")
    for value in (book.tick_size, book.minimum_order_size, book.last_trade_price, book.best_bid,
            book.best_ask, book.midpoint, book.spread, book.top_depth):
        if value is not None and _decimal(value) != value:
            raise _Failure("FIELD_VALUE_INVALID")


def _validate_market_state(market: ObservedMarketState) -> None:
    _require_id(market.market_id, "market:")
    _require_id(market.event_id, "event:")
    required_metadata_missing = "REQUIRED_METADATA_MISSING" in market.data_gap_codes
    if market.market_status is not None:
        _require_text(market.market_status)
    if market.condition_id is not None: _require_text(market.condition_id)
    if ((not required_metadata_missing and (market.market_status is None or not market.token_ids or not market.outcome_labels))
            or not _sorted_unique(market.token_ids)
            or any(not _require_id(x, "token:") for x in market.token_ids)
            or not _sorted_unique(market.outcome_labels)
            or any(not isinstance(x, str) or not x for x in market.outcome_labels)):
        raise _Failure("FIELD_VALUE_INVALID")
    _require_content_id(market.metadata_record_version_id, "record:sha256:")
    if _utc(market.metadata_observed_time) != market.metadata_observed_time or market.metadata_freshness not in FRESHNESS_STATES:
        raise _Failure("FIELD_VALUE_INVALID")
    for value in (market.metadata_query_spec_sha256, market.rule_query_spec_sha256, market.book_query_spec_sha256):
        _require_hash(value)
    if (tuple(r.resolution_source_id for r in market.rules) != tuple(sorted(r.resolution_source_id for r in market.rules))
            or len({r.resolution_source_id for r in market.rules}) != len(market.rules)):
        raise _Failure("FIELD_VALUE_INVALID")
    if (tuple(b.token_id for b in market.books) != tuple(sorted(b.token_id for b in market.books))
            or len({b.token_id for b in market.books}) != len(market.books)
            or set(b.token_id for b in market.books) != set(market.token_ids)):
        raise _Failure("FIELD_VALUE_INVALID")
    for rule in market.rules: _validate_rule_state(rule)
    for book in market.books: _validate_book_state(book)
    if not _sorted_unique(market.data_gap_codes) or any(x not in DATA_GAP_CODES for x in market.data_gap_codes):
        raise _Failure("FIELD_VALUE_INVALID")


def _validate_universe(record: AlphaUniverseSnapshot) -> None:
    if (record.schema_version != ALPHA_DISCOVERY_SCHEMA_VERSION
            or record.cutoff_mode != "AS_OF_INGESTION_TIME"
            or record.query_engine_version != QUERY_ENGINE_VERSION
            or record.query_parameter_set_id != ALPHA_DISCOVERY_PARAMETER_SET_ID
            or record.coverage_scope != "BOUNDED_OBSERVED_UNIVERSE"
            or record.external_universe_completeness != "UNPROVEN"):
        raise _Failure("FIELD_VALUE_INVALID")
    _require_content_id(record.policy_id, "alphadiscoverypolicy:sha256:")
    if _utc(record.as_of) != record.as_of:
        raise _Failure("FIELD_VALUE_INVALID")
    if (tuple(m.market_id for m in record.markets) != tuple(sorted(m.market_id for m in record.markets))
            or len({m.market_id for m in record.markets}) != len(record.markets)):
        raise _Failure("FIELD_VALUE_INVALID")
    for market in record.markets: _validate_market_state(market)
    _require_authority(record)


def _validate_change(record: MaterialChangeEvent) -> None:
    if record.schema_version != ALPHA_DISCOVERY_SCHEMA_VERSION or record.prior_universe_id == record.current_universe_id:
        raise _Failure("FIELD_VALUE_INVALID")
    _require_content_id(record.policy_id, "alphadiscoverypolicy:sha256:")
    _require_content_id(record.prior_universe_id, "alphauniverse:sha256:")
    _require_content_id(record.current_universe_id, "alphauniverse:sha256:")
    _require_id(record.market_id, "market:")
    for actual, vocabulary in ((record.hard_change_classes, HARD_CHANGE_CLASSES),
            (record.soft_change_classes, SOFT_CHANGE_CLASSES),
            (record.review_only_change_classes, REVIEW_CHANGE_CLASSES)):
        if actual != tuple(x for x in vocabulary if x in set(actual)) or len(actual) != len(set(actual)):
            raise _Failure("FIELD_VALUE_INVALID")
    token_classes = {"TICK_SIZE_CHANGED", "MIN_ORDER_SIZE_CHANGED", *SOFT_CHANGE_CLASSES}
    if tuple(x[0] for x in record.affected_token_ids) != tuple(sorted(x[0] for x in record.affected_token_ids)):
        raise _Failure("FIELD_VALUE_INVALID")
    for change_class, token_ids in record.affected_token_ids:
        if change_class not in token_classes or change_class not in set(record.hard_change_classes + record.soft_change_classes):
            raise _Failure("FIELD_VALUE_INVALID")
        if not _sorted_unique(token_ids): raise _Failure("FIELD_VALUE_INVALID")
        for token_id in token_ids: _require_id(token_id, "token:")
    emitted_token_classes = token_classes.intersection(record.hard_change_classes + record.soft_change_classes)
    if {change_class for change_class, _ in record.affected_token_ids} != emitted_token_classes:
        raise _Failure("FIELD_VALUE_INVALID")
    if not _sorted_unique(record.affected_resolution_source_ids): raise _Failure("FIELD_VALUE_INVALID")
    for source_id in record.affected_resolution_source_ids: _require_id(source_id)
    emitted_source_change = bool({"RESOLUTION_RULE_CHANGED", "RESOLUTION_SOURCE_CHANGED"}.intersection(record.hard_change_classes))
    if bool(record.affected_resolution_source_ids) != emitted_source_change:
        raise _Failure("FIELD_VALUE_INVALID")
    for ids in (record.before_record_version_ids, record.after_record_version_ids):
        if not ids or not _sorted_unique(ids): raise _Failure("FIELD_VALUE_INVALID")
        for value in ids: _require_content_id(value, "record:sha256:")
    if not _sorted_unique(record.comparison_diagnostics) or any(x not in COMPARISON_DIAGNOSTICS for x in record.comparison_diagnostics):
        raise _Failure("FIELD_VALUE_INVALID")
    if not (record.hard_change_classes or record.soft_change_classes
            or record.review_only_change_classes or record.comparison_diagnostics):
        raise _Failure("FIELD_VALUE_INVALID")
    _require_authority(record)


def _validate_triage(record: MarketTriageDecision) -> None:
    if record.schema_version != ALPHA_DISCOVERY_SCHEMA_VERSION:
        raise _Failure("SCHEMA_UNSUPPORTED")
    _require_content_id(record.policy_id, "alphadiscoverypolicy:sha256:")
    _require_content_id(record.universe_id, "alphauniverse:sha256:")
    if record.comparison_prior_universe_id is not None:
        _require_content_id(record.comparison_prior_universe_id, "alphauniverse:sha256:")
    _require_id(record.market_id, "market:"); _require_id(record.event_id, "event:")
    if (record.eligibility not in ELIGIBILITY_STATES or record.priority_class not in PRIORITY_CLASSES
            or record.reopen_disposition not in REOPEN_DISPOSITIONS or record.readiness not in READINESS_STATES
            or record.final_disposition not in FINAL_DISPOSITIONS):
        raise _Failure("FIELD_VALUE_INVALID")
    if not _sorted_unique(record.reason_codes) or any(x not in TRIAGE_REASON_CODES for x in record.reason_codes):
        raise _Failure("FIELD_VALUE_INVALID")
    for request in record.capture_requests: _validate_capture_request(request)
    if tuple(record.capture_requests) != tuple(sorted(record.capture_requests, key=lambda r: (r.request_type, r.token_id or "", r.reason_code))):
        raise _Failure("FIELD_VALUE_INVALID")
    if record.material_change_event_id is not None: _require_content_id(record.material_change_event_id, "alphachange:sha256:")
    if record.selected_lane is None:
        if record.final_disposition in ALLOCATION_LANES: raise _Failure("FIELD_VALUE_INVALID")
    elif record.selected_lane not in ALLOCATION_LANES or record.final_disposition != record.selected_lane:
        raise _Failure("FIELD_VALUE_INVALID")
    audit_values = (record.audit_digest, record.audit_eligible_pool_size,
        record.audit_selection_fraction_numerator, record.audit_selection_fraction_denominator)
    if record.selected_lane == "AUDIT":
        if any(x is None for x in audit_values): raise _Failure("FIELD_VALUE_INVALID")
        _require_hash(record.audit_digest)
        if any(isinstance(x, bool) or not isinstance(x, int) or x <= 0 for x in audit_values[1:]):
            raise _Failure("FIELD_VALUE_INVALID")
    elif any(x is not None for x in audit_values):
        raise _Failure("FIELD_VALUE_INVALID")
    expected_unallocated = {
        "ELIGIBLE": "SKIPPED_CAPACITY", "DEFERRED": "DEFERRED", "INELIGIBLE": "SKIPPED_INELIGIBLE",
    }
    if record.selected_lane is None and record.final_disposition != expected_unallocated[record.eligibility]:
        raise _Failure("FIELD_VALUE_INVALID")
    if record.selected_lane is not None and record.eligibility != "ELIGIBLE":
        raise _Failure("FIELD_VALUE_INVALID")
    historical = _require_temporal_posture(record)
    if record.historical_replay_valid_for_alpha_memory is not False:
        raise _Failure("TEMPORAL_POSTURE_INVALID")
    for values in (record.matched_candidate_ids, record.matched_hypothesis_family_ids, record.matched_research_episode_ids):
        if not _sorted_unique(values): raise _Failure("FIELD_VALUE_INVALID")
        for value in values: _require_id(value)
    if historical and (record.matched_candidate_ids or record.matched_hypothesis_family_ids or record.matched_research_episode_ids):
        raise _Failure("TEMPORAL_POSTURE_INVALID")
    if record.coverage != tuple((name, dict(record.coverage).get(name)) for name in RESEARCH_ARCHETYPES):
        raise _Failure("FIELD_VALUE_INVALID")
    if any(state not in COVERAGE_STATES for _, state in record.coverage): raise _Failure("FIELD_VALUE_INVALID")
    if historical and any(state != "UNKNOWN" for _, state in record.coverage): raise _Failure("TEMPORAL_POSTURE_INVALID")
    _require_authority(record)


def _validate_queue(record: AlphaResearchQueueSnapshot) -> None:
    if record.schema_version != ALPHA_DISCOVERY_SCHEMA_VERSION:
        raise _Failure("SCHEMA_UNSUPPORTED")
    _require_content_id(record.policy_id, "alphadiscoverypolicy:sha256:")
    _require_content_id(record.universe_id, "alphauniverse:sha256:")
    if record.comparison_prior_universe_id is not None: _require_content_id(record.comparison_prior_universe_id, "alphauniverse:sha256:")
    _require_temporal_posture(record)
    groups = (record.core_triage_ids, record.exploration_triage_ids, record.audit_triage_ids,
        record.deferred_triage_ids, record.skipped_ineligible_triage_ids, record.skipped_capacity_triage_ids)
    flattened = tuple(x for group in groups for x in group)
    if len(flattened) != len(set(flattened)) or set(record.all_triage_ids) != set(flattened) or len(record.all_triage_ids) != len(set(record.all_triage_ids)):
        raise _Failure("FIELD_VALUE_INVALID")
    for value in record.all_triage_ids: _require_content_id(value, "alphatriage:sha256:")
    if not _sorted_unique(record.prior_only_market_ids): raise _Failure("FIELD_VALUE_INVALID")
    for value in record.prior_only_market_ids: _require_id(value, "market:")
    positive_ints = (record.queue_capacity, record.configured_exploration_slots,
        record.configured_audit_slots, record.max_per_category)
    nonnegative_ints = (record.exploration_selected_count, record.audit_selected_count,
        record.unused_exploration_slots, record.unused_audit_slots)
    if (any(isinstance(x, bool) or not isinstance(x, int) or x <= 0 for x in positive_ints)
            or any(isinstance(x, bool) or not isinstance(x, int) or x < 0 for x in nonnegative_ints)):
        raise _Failure("FIELD_VALUE_INVALID")
    if record.configured_exploration_slots + record.configured_audit_slots > record.queue_capacity:
        raise _Failure("FIELD_VALUE_INVALID")
    if (record.exploration_selected_count != len(record.exploration_triage_ids)
            or record.audit_selected_count != len(record.audit_triage_ids)
            or record.unused_exploration_slots != record.configured_exploration_slots - record.exploration_selected_count
            or record.unused_audit_slots != record.configured_audit_slots - record.audit_selected_count
            or min(record.unused_exploration_slots, record.unused_audit_slots) < 0
            or len(record.core_triage_ids) + record.exploration_selected_count + record.audit_selected_count > record.queue_capacity):
        raise _Failure("FIELD_VALUE_INVALID")
    expected_reasons = tuple(x for x, count in (("EXPLORATION_POOL_EXHAUSTED", record.unused_exploration_slots),
        ("AUDIT_POOL_EXHAUSTED", record.unused_audit_slots)) if count > 0)
    if record.unused_capacity_reason_codes != expected_reasons: raise _Failure("FIELD_VALUE_INVALID")
    _require_authority(record)


_RECORD_PREFIXES = {
    AlphaDiscoveryPolicy: ("alpha_discovery_policy_id", "alphadiscoverypolicy:sha256:"),
    AlphaUniverseSnapshot: ("alpha_universe_snapshot_id", "alphauniverse:sha256:"),
    MaterialChangeEvent: ("material_change_event_id", "alphachange:sha256:"),
    MarketTriageDecision: ("market_triage_decision_id", "alphatriage:sha256:"),
    AlphaResearchQueueSnapshot: ("alpha_research_queue_snapshot_id", "alphaqueue:sha256:"),
}


def _semantic_validate(record: object) -> None:
    validators = {AlphaDiscoveryPolicy: _validate_policy, AlphaUniverseSnapshot: _validate_universe,
        MaterialChangeEvent: _validate_change, MarketTriageDecision: _validate_triage,
        AlphaResearchQueueSnapshot: _validate_queue}
    validator = validators.get(type(record))
    if validator is None: raise _Failure("FIELD_TYPE_INVALID")
    validator(record)  # type: ignore[arg-type]
    id_field, prefix = _RECORD_PREFIXES[type(record)]
    _require_content_id(getattr(record, id_field), prefix)
    if getattr(record, id_field) != _id(prefix, _without_id(record, id_field)):
        raise _Failure("IDENTITY_DERIVATION_MISMATCH")


def _validate_alpha_discovery_record(record: object) -> None:
    """Shared semantic and identity gate for builders, mappings, append, and load."""
    try:
        _semantic_validate(record)
    except _Failure as failure:
        raise ValueError(f"alpha discovery semantic validation failed: {failure.code}") from None


def _validated_ok(record: object) -> AlphaDiscoveryResult:
    _semantic_validate(record)
    return _ok(record)


def build_alpha_discovery_policy(value: object) -> AlphaDiscoveryResult:
    names = {f.name for f in fields(AlphaDiscoveryPolicy)} - {"alpha_discovery_policy_id"}
    try:
        item = _strict_mapping(value, names)
        statuses = item["eligible_market_statuses"]
        if not isinstance(statuses, (list, tuple)) or not statuses or any(not isinstance(x, str) or not x for x in statuses):
            raise _Failure("FIELD_VALUE_INVALID")
        statuses_t = tuple(sorted(set(statuses)))
        if len(statuses_t) != len(statuses):
            raise _Failure("FIELD_VALUE_INVALID")
        ints = {}
        for key in ("metadata_freshness_seconds", "order_book_freshness_seconds", "resolution_rule_freshness_seconds", "queue_capacity", "exploration_slots", "audit_slots", "max_per_category"):
            raw = item[key]
            if isinstance(raw, bool) or not isinstance(raw, int) or raw <= 0:
                raise _Failure("FIELD_VALUE_INVALID")
            ints[key] = raw
        if ints["exploration_slots"] + ints["audit_slots"] > ints["queue_capacity"]:
            raise _Failure("FIELD_VALUE_INVALID")
        authority = {}
        for key in ("advisory_only", "no_execution_authority", "no_strategy_authority", "no_qualification_authority"):
            if item[key] is not True:
                raise _Failure("FIELD_VALUE_INVALID")
            authority[key] = True
        preimage = {
            "schema_version": item["schema_version"], "policy_version": item["policy_version"],
            "eligible_market_statuses": statuses_t, **ints,
            "soft_last_trade_price_abs_delta": _decimal(item["soft_last_trade_price_abs_delta"]),
            "soft_mid_price_abs_delta": _decimal(item["soft_mid_price_abs_delta"]),
            "soft_spread_abs_delta": _decimal(item["soft_spread_abs_delta"]),
            "soft_top_depth_relative_delta": _decimal(item["soft_top_depth_relative_delta"]),
            "audit_seed": item["audit_seed"],
            "research_archetype_taxonomy_version": item["research_archetype_taxonomy_version"],
            **authority,
        }
        if preimage["schema_version"] != ALPHA_DISCOVERY_SCHEMA_VERSION:
            raise _Failure("SCHEMA_UNSUPPORTED")
        if not all(isinstance(preimage[k], str) and preimage[k] for k in ("policy_version", "audit_seed", "research_archetype_taxonomy_version")):
            raise _Failure("FIELD_VALUE_INVALID")
        return _validated_ok(AlphaDiscoveryPolicy(**preimage, alpha_discovery_policy_id=_id("alphadiscoverypolicy:sha256:", preimage)))
    except _Failure as failure:
        return _reject(failure.code)
    except Exception:
        return _reject("INTERNAL_VALIDATION_FAILED")


def freshness_state(observed_time: str | None, as_of: str, threshold_seconds: int) -> str:
    if observed_time is None:
        return "MISSING"
    try:
        observed = datetime.fromisoformat(observed_time.replace("Z", "+00:00"))
        cutoff = datetime.fromisoformat(_utc(as_of).replace("Z", "+00:00"))
    except (ValueError, _Failure):
        return "INVALID_CLOCK"
    if observed.tzinfo is None or observed.utcoffset() != timezone.utc.utcoffset(observed) or observed > cutoff:
        return "INVALID_CLOCK"
    return "FRESH" if Decimal(str((cutoff - observed).total_seconds())) <= threshold_seconds else "STALE"


def _payload(record: object) -> Mapping[str, object]:
    try:
        value = json.loads(getattr(record, "canonical_payload_json"), parse_float=lambda _: (_ for _ in ()).throw(ValueError()))
    except (TypeError, ValueError, json.JSONDecodeError):
        raise _Failure("PIT_QUERY_INVALID") from None
    if not isinstance(value, Mapping):
        raise _Failure("PIT_QUERY_INVALID")
    return value


def _projection(records: Sequence[object], predicate) -> tuple[object, ...]:
    by_id = {r.envelope.record_version_id: r for r in records}
    selected = {rid for rid, record in by_id.items() if predicate(record)}
    pending = list(selected)
    while pending:
        record = by_id[pending.pop()]
        parents = (*record.envelope.lineage_parent_ids, record.envelope.supersedes_record_version_id)
        for parent in parents:
            if parent is not None and parent in by_id and parent not in selected:
                selected.add(parent)
                pending.append(parent)
    if len(selected) > _MAX_QUERY_INPUT:
        raise _Failure("PIT_QUERY_INPUT_LIMIT_EXCEEDED")
    return tuple(by_id[rid] for rid in sorted(selected))


def _query(records: Sequence[object], *, qid: str, as_of: str, view: str, families: tuple[str, ...], kinds: tuple[str, ...] = (), market_ids: tuple[str, ...] = (), source_ids: tuple[str, ...] = ()):
    spec = PointInTimeQuerySpec(qid, "AS_OF_INGESTION_TIME", as_of, view, families, kinds,
        (), (), market_ids, (), source_ids, (), None, True, False, ALPHA_DISCOVERY_PARAMETER_SET_ID)
    result = query_point_in_time_record_set(records, spec)
    if not result.is_valid or result.receipt is None:
        raise _Failure("PIT_QUERY_INVALID")
    return result


def _book_state(record: MarketObservationRecord | None, token_id: str, as_of: str, threshold: int, conflict: bool = False) -> OrderBookState:
    if record is None:
        return OrderBookState(token_id, None, None, "MISSING", None, None, None, None, None, None, None, None,
            "ORDER_BOOK_CONFLICT" if conflict else "ORDER_BOOK_MISSING")
    p = _payload(record)
    try:
        tick = _decimal(p.get("tick_size")) if p.get("tick_size") is not None else None
        minimum = _decimal(p.get("minimum_order_size")) if p.get("minimum_order_size") is not None else None
        last = _decimal(p.get("last_trade_price")) if p.get("last_trade_price") is not None else None
        bids = [(_decimal(x["price"]), _decimal(x["size"])) for x in p.get("bids", [])]
        asks = [(_decimal(x["price"]), _decimal(x["size"])) for x in p.get("asks", [])]
        if any(Decimal(price) > 1 for price, _ in bids + asks):
            raise _Failure("FIELD_VALUE_INVALID")
        best_bid = max((Decimal(price) for price, _ in bids), default=None)
        best_ask = min((Decimal(price) for price, _ in asks), default=None)
        if best_bid is not None and best_ask is not None and best_ask < best_bid:
            raise _Failure("FIELD_VALUE_INVALID")
        midpoint = spread = depth = None
        if best_bid is not None and best_ask is not None:
            midpoint = (best_bid + best_ask) / Decimal("2")
            spread = best_ask - best_bid
            depth = sum(Decimal(s) for p_, s in bids if Decimal(p_) == best_bid) + sum(Decimal(s) for p_, s in asks if Decimal(p_) == best_ask)
        fmt = lambda x: None if x is None else _decimal(format(x, "f"))
        return OrderBookState(token_id, record.envelope.record_version_id, record.envelope.observed_time,
            freshness_state(record.envelope.observed_time, as_of, threshold), tick, minimum, last,
            fmt(best_bid), fmt(best_ask), fmt(midpoint), fmt(spread), fmt(depth),
            "ORDER_BOOK_CONFLICT" if conflict else "ORDER_BOOK_VALID")
    except (KeyError, TypeError, _Failure):
        return OrderBookState(token_id, record.envelope.record_version_id, record.envelope.observed_time,
            "INVALID_CLOCK", None, None, None, None, None, None, None, None, "ORDER_BOOK_CONFLICT")


def build_alpha_universe_snapshot(store_path: object, policy: AlphaDiscoveryPolicy, as_of: str) -> AlphaDiscoveryResult:
    try:
        cutoff = _utc(as_of)
        if not isinstance(policy, AlphaDiscoveryPolicy):
            raise _Failure("FIELD_TYPE_INVALID")
        loaded = load_and_verify_point_in_time_record_store(store_path)
        if not loaded.is_valid or loaded.status != "RECORD_STORE_LOADED_VERIFIED" or loaded.snapshot is None:
            raise _Failure("PIT_STORE_INVALID")
        all_records = loaded.snapshot.records
        candidate_ids = sorted({r.market_id for r in all_records if isinstance(r, MarketObservationRecord) and r.observation_kind == "MARKET_METADATA" and r.source_id == "source:polymarket:gamma-markets"})
        markets: list[ObservedMarketState] = []
        for market_id in candidate_ids:
            metadata_input = _projection(all_records, lambda r: isinstance(r, MarketObservationRecord) and r.market_id == market_id and r.observation_kind == "MARKET_METADATA" and r.source_id == "source:polymarket:gamma-markets")
            meta_q = _query(metadata_input, qid=f"alpha02-metadata:{market_id}", as_of=cutoff, view="AUTHORITATIVE_CURRENT_STATE", families=("MARKET_OBSERVATION",), kinds=("MARKET_METADATA",), market_ids=(market_id,), source_ids=("source:polymarket:gamma-markets",))
            metadata = [r for r in meta_q.authoritative_records if isinstance(r, MarketObservationRecord)]
            if not metadata:
                continue
            if len(metadata) != 1:
                raise _Failure("PIT_QUERY_INVALID")
            meta = metadata[0]
            p = _payload(meta)
            raw_tokens = p.get("token_ids")
            raw_outcomes = p.get("outcome_labels")
            token_values = [f"token:polymarket:{x}" if isinstance(x, str) and not x.startswith("token:") else x for x in raw_tokens] if isinstance(raw_tokens, list) else []
            tokens = tuple(sorted(set(token_values))) if all(isinstance(x, str) and _ID_RE.fullmatch(x) for x in token_values) else ()
            outcomes = tuple(sorted(set(raw_outcomes))) if isinstance(raw_outcomes, list) and all(isinstance(x, str) and x for x in raw_outcomes) else ()
            gaps: set[str] = set()
            if any(isinstance(r, MarketObservationRecord) and r.market_id == market_id
                    and r.observation_kind == "MARKET_METADATA" for r in meta_q.review_conflict_records):
                gaps.add("METADATA_CONFLICT")
            if (not isinstance(p.get("market_status"), str) or not tokens or not outcomes
                    or len(tokens) != len(token_values)
                    or (isinstance(raw_outcomes, list) and len(outcomes) != len(raw_outcomes))):
                gaps.add("REQUIRED_METADATA_MISSING")
            if any(p.get(k) in (None, "") for k in ("condition_id", "category", "resolution_date")):
                gaps.add("OPTIONAL_METADATA_MISSING")
            book_input = _projection(all_records, lambda r: isinstance(r, MarketObservationRecord) and r.market_id == market_id and r.observation_kind == "ORDER_BOOK" and r.source_id == "source:polymarket:clob-book")
            book_q = _query(book_input, qid=f"alpha02-book:{market_id}", as_of=cutoff, view="AUTHORITATIVE_CURRENT_STATE", families=("MARKET_OBSERVATION",), kinds=("ORDER_BOOK",), market_ids=(market_id,), source_ids=("source:polymarket:clob-book",))
            by_token: dict[str, list[MarketObservationRecord]] = {}
            for book in book_q.authoritative_records:
                if isinstance(book, MarketObservationRecord) and book.token_id:
                    by_token.setdefault(book.token_id, []).append(book)
            conflicted_tokens = {r.token_id for r in book_q.review_conflict_records
                if isinstance(r, MarketObservationRecord) and r.market_id == market_id
                and r.observation_kind == "ORDER_BOOK" and r.token_id in tokens}
            books = []
            for token in tokens:
                found = by_token.get(token, [])
                conflict = len(found) > 1 or token in conflicted_tokens
                books.append(_book_state(found[0] if len(found) == 1 else None, token, cutoff, policy.order_book_freshness_seconds, conflict))
                if not found:
                    gaps.add("ORDER_BOOK_CONFLICT" if conflict else "ORDER_BOOK_MISSING")
                elif conflict or books[-1].state == "ORDER_BOOK_CONFLICT":
                    gaps.add("ORDER_BOOK_CONFLICT")
                elif books[-1].freshness == "STALE":
                    gaps.add("ORDER_BOOK_STALE")
                elif books[-1].freshness == "INVALID_CLOCK":
                    gaps.add("ORDER_BOOK_CONFLICT")
            rule_input = _projection(all_records, lambda r: isinstance(r, ResolutionRuleSnapshotRecord) and r.market_id == market_id)
            rule_q = _query(rule_input, qid=f"alpha02-rule:{market_id}", as_of=cutoff, view="AUTHORITATIVE_CURRENT_STATE", families=("RESOLUTION_RULE_SNAPSHOT",), market_ids=(market_id,))
            rule_states: list[ResolutionRuleState] = []
            rules = [r for r in rule_q.authoritative_records if isinstance(r, ResolutionRuleSnapshotRecord)]
            conflicted_rules = {(r.market_id, r.resolution_source_id) for r in rule_q.review_conflict_records
                if isinstance(r, ResolutionRuleSnapshotRecord) and r.market_id == market_id}
            if not rules:
                gaps.add("RULE_EVIDENCE_MISSING")
            if conflicted_rules:
                gaps.add("RULE_EVIDENCE_CONFLICT")
            rules_by_source: dict[str, list[ResolutionRuleSnapshotRecord]] = {}
            for rule in rules:
                rules_by_source.setdefault(rule.resolution_source_id, []).append(rule)
            for resolution_source_id in sorted(rules_by_source):
                competing = rules_by_source[resolution_source_id]
                if len(competing) != 1:
                    gaps.add("RULE_EVIDENCE_CONFLICT")
                    continue
                rule = competing[0]
                candidate_sources = sorted({r.source_id for r in all_records if isinstance(r, SourceSnapshotRecord) and r.envelope.source_snapshot_id == rule.source_snapshot_id})
                visible: dict[str, SourceSnapshotRecord] = {}
                qhash = None
                for source_id in candidate_sources:
                    source_input = _projection(all_records, lambda r, sid=source_id: isinstance(r, SourceSnapshotRecord) and r.source_id == sid)
                    source_q = _query(source_input, qid=f"alpha02-source:{market_id}:{source_id}", as_of=cutoff, view="VISIBLE_HISTORY", families=("SOURCE_SNAPSHOT",), source_ids=(source_id,))
                    qhash = source_q.receipt.query_spec_sha256
                    if any(isinstance(item, SourceSnapshotRecord)
                            and item.source_id == source_id
                            and item.envelope.source_snapshot_id == rule.source_snapshot_id
                            for item in source_q.review_conflict_records):
                        gaps.add("SOURCE_EVIDENCE_CONFLICT")
                    for source in source_q.history_records:
                        if isinstance(source, SourceSnapshotRecord) and source.envelope.source_snapshot_id == rule.source_snapshot_id:
                            visible[source.envelope.record_version_id] = source
                source = next(iter(visible.values())) if len(visible) == 1 else None
                if not visible:
                    gaps.add("SOURCE_EVIDENCE_MISSING")
                elif len(visible) > 1:
                    gaps.add("SOURCE_EVIDENCE_CONFLICT")
                rule_fresh = freshness_state(rule.envelope.observed_time, cutoff, policy.resolution_rule_freshness_seconds)
                source_fresh = freshness_state(source.envelope.observed_time if source else None, cutoff, policy.resolution_rule_freshness_seconds)
                if rule_fresh == "STALE": gaps.add("RULE_EVIDENCE_STALE")
                if rule_fresh == "INVALID_CLOCK": gaps.add("RULE_EVIDENCE_CONFLICT")
                if source_fresh == "STALE": gaps.add("SOURCE_EVIDENCE_STALE")
                if source_fresh == "INVALID_CLOCK": gaps.add("SOURCE_EVIDENCE_CONFLICT")
                rule_states.append(ResolutionRuleState(rule.resolution_source_id, rule.rule_content_sha256,
                    rule.envelope.record_version_id, rule.envelope.observed_time, rule_fresh,
                    rule.source_snapshot_id, source.envelope.record_version_id if source else None,
                    source.envelope.observed_time if source else None, source_fresh, qhash if source else None))
            markets.append(ObservedMarketState(meta.market_id, meta.event_id,
                p.get("market_status") if isinstance(p.get("market_status"), str) else None,
                p.get("condition_id") if isinstance(p.get("condition_id"), str) and p.get("condition_id") else None,
                tokens, outcomes, p.get("resolution_date") if isinstance(p.get("resolution_date"), str) else None,
                p.get("category") if isinstance(p.get("category"), str) else None,
                p.get("question_text") if isinstance(p.get("question_text"), str) else None,
                meta.envelope.record_version_id, meta.envelope.observed_time,
                freshness_state(meta.envelope.observed_time, cutoff, policy.metadata_freshness_seconds),
                meta_q.receipt.query_spec_sha256, rule_q.receipt.query_spec_sha256,
                book_q.receipt.query_spec_sha256, tuple(rule_states), tuple(books), tuple(sorted(gaps))))
        preimage = dict(schema_version=ALPHA_DISCOVERY_SCHEMA_VERSION, policy_id=policy.alpha_discovery_policy_id,
            as_of=cutoff, cutoff_mode="AS_OF_INGESTION_TIME", query_engine_version=QUERY_ENGINE_VERSION,
            query_parameter_set_id=ALPHA_DISCOVERY_PARAMETER_SET_ID, coverage_scope="BOUNDED_OBSERVED_UNIVERSE",
            external_universe_completeness="UNPROVEN", markets=tuple(sorted(markets, key=lambda m: m.market_id)),
            advisory_only=True, no_execution_authority=True, no_strategy_authority=True, no_qualification_authority=True)
        return _validated_ok(AlphaUniverseSnapshot(**preimage, alpha_universe_snapshot_id=_id("alphauniverse:sha256:", preimage)))
    except _Failure as failure:
        return _reject(failure.code)
    except Exception:
        return _reject("INTERNAL_VALIDATION_FAILED")


def _delta(before: str | None, after: str | None) -> Decimal | None:
    if before is None or after is None:
        return None
    try:
        return abs(Decimal(after) - Decimal(before))
    except InvalidOperation:
        return None


def compare_alpha_universes(prior: AlphaUniverseSnapshot, current: AlphaUniverseSnapshot, policy: AlphaDiscoveryPolicy) -> AlphaDiscoveryResult:
    try:
        for record in (prior, current, policy):
            _semantic_validate(record)
        if prior.policy_id != current.policy_id or current.policy_id != policy.alpha_discovery_policy_id or _utc(prior.as_of) >= _utc(current.as_of):
            raise _Failure("COMPARISON_INVALID")
        prior_by = {m.market_id: m for m in prior.markets}
        current_by = {m.market_id: m for m in current.markets}
        changes: list[MaterialChangeEvent] = []
        thresholds = {
            "LAST_TRADE_PRICE_MOVED": Decimal(policy.soft_last_trade_price_abs_delta),
            "MID_PRICE_MOVED": Decimal(policy.soft_mid_price_abs_delta),
            "SPREAD_CHANGED": Decimal(policy.soft_spread_abs_delta),
            "TOP_DEPTH_CHANGED": Decimal(policy.soft_top_depth_relative_delta),
        }
        for market_id in sorted(prior_by.keys() & current_by.keys()):
            before, after = prior_by[market_id], current_by[market_id]
            hard: set[str] = set(); soft: set[str] = set(); review: set[str] = set(); diagnostics: set[str] = set()
            affected: dict[str, set[str]] = {}; affected_sources: set[str] = set()
            for cls, field in (("MARKET_STATUS_CHANGED", "market_status"), ("CONDITION_ID_CHANGED", "condition_id"), ("TOKEN_SET_CHANGED", "token_ids"), ("OUTCOME_SET_CHANGED", "outcome_labels")):
                if getattr(before, field) != getattr(after, field): hard.add(cls)
            for cls, field in (("QUESTION_TEXT_CHANGED", "question_text"), ("CATEGORY_TEXT_CHANGED", "category")):
                if getattr(before, field) != getattr(after, field): review.add(cls)
            brules = {r.resolution_source_id: r for r in before.rules}; arules = {r.resolution_source_id: r for r in after.rules}
            if not brules or not arules:
                diagnostics.add("DATA_MISSING")
            if set(brules) != set(arules):
                hard.add("RESOLUTION_SOURCE_CHANGED"); affected_sources.update(set(brules) ^ set(arules))
            for source in set(brules) & set(arules):
                if brules[source].rule_content_sha256 != arules[source].rule_content_sha256:
                    hard.add("RESOLUTION_RULE_CHANGED"); affected_sources.add(source)
            bbooks = {b.token_id: b for b in before.books}; abooks = {b.token_id: b for b in after.books}
            for token in sorted(set(bbooks) & set(abooks)):
                left, right = bbooks[token], abooks[token]
                for cls, field in (("TICK_SIZE_CHANGED", "tick_size"), ("MIN_ORDER_SIZE_CHANGED", "minimum_order_size")):
                    if getattr(left, field) is None or getattr(right, field) is None:
                        diagnostics.add("DATA_MISSING")
                    elif Decimal(getattr(left, field)) != Decimal(getattr(right, field)):
                        hard.add(cls); affected.setdefault(cls, set()).add(token)
                for cls, field in (("LAST_TRADE_PRICE_MOVED", "last_trade_price"), ("MID_PRICE_MOVED", "midpoint"), ("SPREAD_CHANGED", "spread")):
                    change = _delta(getattr(left, field), getattr(right, field))
                    if change is None: diagnostics.add("DATA_MISSING")
                    elif change >= thresholds[cls]: soft.add(cls); affected.setdefault(cls, set()).add(token)
                if left.top_depth is None or right.top_depth is None:
                    diagnostics.add("DATA_MISSING")
                else:
                    ld, rd = Decimal(left.top_depth), Decimal(right.top_depth)
                    rel = Decimal(0) if ld == rd == 0 else abs(rd - ld) / max(abs(ld), abs(rd))
                    if rel >= thresholds["TOP_DEPTH_CHANGED"]:
                        soft.add("TOP_DEPTH_CHANGED"); affected.setdefault("TOP_DEPTH_CHANGED", set()).add(token)
            if not (hard or soft or review or diagnostics):
                continue
            preimage = dict(schema_version=ALPHA_DISCOVERY_SCHEMA_VERSION, policy_id=policy.alpha_discovery_policy_id,
                prior_universe_id=prior.alpha_universe_snapshot_id, current_universe_id=current.alpha_universe_snapshot_id,
                market_id=market_id, hard_change_classes=tuple(x for x in HARD_CHANGE_CLASSES if x in hard),
                soft_change_classes=tuple(x for x in SOFT_CHANGE_CLASSES if x in soft),
                review_only_change_classes=tuple(x for x in REVIEW_CHANGE_CLASSES if x in review),
                affected_token_ids=tuple((k, tuple(sorted(v))) for k, v in sorted(affected.items())),
                affected_resolution_source_ids=tuple(sorted(affected_sources)),
                before_record_version_ids=tuple(sorted({before.metadata_record_version_id, *(r.rule_record_version_id for r in before.rules), *(b.record_version_id for b in before.books if b.record_version_id)})),
                after_record_version_ids=tuple(sorted({after.metadata_record_version_id, *(r.rule_record_version_id for r in after.rules), *(b.record_version_id for b in after.books if b.record_version_id)})),
                comparison_diagnostics=tuple(sorted(diagnostics)), advisory_only=True, no_execution_authority=True,
                no_strategy_authority=True, no_qualification_authority=True)
            change = MaterialChangeEvent(**preimage, material_change_event_id=_id("alphachange:sha256:", preimage))
            _semantic_validate(change)
            changes.append(change)
        return _ok(records=changes)
    except _Failure as failure:
        return _reject(failure.code)
    except Exception:
        return _reject("INTERNAL_VALIDATION_FAILED")


def canonical_market_subject_refs(market: ObservedMarketState) -> tuple[str, ...]:
    return tuple(sorted({market.market_id, market.event_id, *market.token_ids}))


def _coverage(episodes: Sequence[ResearchEpisode], historical: bool) -> tuple[tuple[str, str], ...]:
    result = {name: "UNKNOWN" for name in RESEARCH_ARCHETYPES}
    if historical:
        return tuple(result.items())
    rank = {"UNKNOWN": 0, "PARTIAL": 1, "SUPPORTED": 2}
    def promote(name: str, state: str) -> None:
        if rank[state] > rank[result[name]]: result[name] = state
    for episode in episodes:
        lanes = set(episode.evidence_lanes)
        if "RESOLUTION_RULES" in lanes: promote("resolution_contract", "SUPPORTED"); promote("settlement_capital_lock", "PARTIAL")
        if "CROSS_MARKET" in lanes: promote("cross_market_logic", "SUPPORTED"); promote("combinatorial_portfolio", "PARTIAL")
        if "FUNDAMENTAL" in lanes: promote("fundamental_public_info", "SUPPORTED")
        if "HISTORICAL_REPEATABILITY" in lanes: promote("calibration_probability", "PARTIAL")
        if "MICROSTRUCTURE" in lanes: promote("microstructure", "SUPPORTED"); promote("maker_liquidity", "PARTIAL")
        if "WEATHER" in lanes: promote("domain_specific", "SUPPORTED")
        if episode.producer_type == "HERMES_CONTROLLED_RESEARCH": promote("semantic_model_assisted", "SUPPORTED")
    return tuple(result.items())


def _latest_leaf(episodes: Sequence[ResearchEpisode]) -> tuple[ResearchEpisode | None, bool]:
    if not episodes: return None, True
    parent_ids = {x for e in episodes for x in (e.predecessor_episode_id, e.reopened_episode_id) if x}
    leaves = [e for e in episodes if e.research_episode_id not in parent_ids]
    return (leaves[0], False) if len(leaves) == 1 else (None, True)


def _governing_leaf(candidate_ids: Sequence[str], episodes: Sequence[ResearchEpisode]) -> tuple[ResearchEpisode | None, bool]:
    groups: dict[tuple[str, str], list[ResearchEpisode]] = {}
    for episode in episodes:
        groups.setdefault((episode.candidate_id, episode.hypothesis_family_id), []).append(episode)
    if (not candidate_ids or any(not any(key[0] == candidate_id for key in groups) for candidate_id in candidate_ids)
            or len(groups) != 1):
        return None, True
    return _latest_leaf(next(iter(groups.values())))


def _reopen(candidate_ids: Sequence[str], episodes: Sequence[ResearchEpisode], material: bool) -> str:
    leaf, ambiguous = _governing_leaf(candidate_ids, episodes)
    if ambiguous: return "REOPEN_REVIEW_REQUIRED"
    if not material: return "NO_REOPEN"
    assert leaf is not None
    if leaf.result_state in {"WATCH_FOR_CHANGE", "RESEARCH_STALE"}: return "REOPEN_ELIGIBLE"
    if leaf.result_state in {"RESEARCH_SUPPORTIVE", "REOPEN_TRIGGERED"}: return "NO_AUTOMATIC_REOPEN"
    return "REOPEN_REVIEW_REQUIRED"


def _capture(market: ObservedMarketState, universe_id: str, policy_id: str, prior_id: str | None, priority: str, reason: str, request: str, token: str | None = None) -> CaptureRequest:
    parts = (request, market.market_id, token, universe_id, policy_id, prior_id, reason, priority)
    key = hashlib.sha256(_bytes(parts)).hexdigest()
    return CaptureRequest(request, market.market_id, token, universe_id, policy_id, prior_id, reason, priority, key)


def build_pre_allocation_triage_bases(current: AlphaUniverseSnapshot, policy: AlphaDiscoveryPolicy, *, analysis_temporal_mode: str, alpha_memory_temporal_posture: str, alpha_registry_path: object | None = None, prior: AlphaUniverseSnapshot | None = None, material_changes: Sequence[MaterialChangeEvent] = ()) -> AlphaDiscoveryResult:
    try:
        for record in (current, policy, *(() if prior is None else (prior,)), *material_changes):
            _semantic_validate(record)
        expected = "HISTORICAL_AVAILABILITY_UNPROVEN" if analysis_temporal_mode == "HISTORICAL_REPLAY" else "CURRENT_REGISTRY_BUILD_TIME_ONLY" if analysis_temporal_mode == "CURRENT_BUILD_ANALYSIS" else None
        if expected is None or alpha_memory_temporal_posture != expected:
            raise _Failure("TEMPORAL_POSTURE_INVALID")
        if current.policy_id != policy.alpha_discovery_policy_id:
            raise _Failure("REFERENCE_INVALID")
        prior_id = prior.alpha_universe_snapshot_id if prior else None
        if prior is not None and prior.policy_id != current.policy_id:
            raise _Failure("COMPARISON_INVALID")
        head = None; candidates: list[OpportunityCandidate] = []; families: list[HypothesisFamily] = []; episodes: list[ResearchEpisode] = []
        if analysis_temporal_mode == "HISTORICAL_REPLAY":
            if alpha_registry_path is not None: raise _Failure("TEMPORAL_POSTURE_INVALID")
        else:
            if alpha_registry_path is None: raise _Failure("TEMPORAL_POSTURE_INVALID")
            loaded = load_and_verify_alpha_factory_registry(alpha_registry_path)
            if not loaded.is_valid or loaded.snapshot is None: raise _Failure("ALPHA_REGISTRY_INVALID")
            head = loaded.snapshot.head_entry_hash
            for entry in loaded.snapshot.entries:
                if isinstance(entry.record, OpportunityCandidate): candidates.append(entry.record)
                elif isinstance(entry.record, HypothesisFamily): families.append(entry.record)
                elif isinstance(entry.record, ResearchEpisode): episodes.append(entry.record)
        prior_ids = {m.market_id for m in prior.markets} if prior else set()
        changes = {c.market_id: c for c in material_changes}
        bases = []
        for market in current.markets:
            refs = set(canonical_market_subject_refs(market))
            matched_candidates = sorted(c.candidate_id for c in candidates if refs.intersection(c.subject_refs))
            known_family_ids = {f.hypothesis_family_id for f in families}
            matched_episodes = [e for e in episodes if e.candidate_id in matched_candidates and e.hypothesis_family_id in known_family_ids]
            matched_family_ids = sorted({e.hypothesis_family_id for e in matched_episodes})
            change = changes.get(market.market_id); material = bool(change and change.reopen_material)
            reasons: set[str] = set(); requests: list[CaptureRequest] = []
            status_eligible = market.market_status in policy.eligible_market_statuses
            if not status_eligible:
                eligibility, priority, reopen, readiness = "INELIGIBLE", "INELIGIBLE", "NO_REOPEN", "INELIGIBLE"; reasons.add("MARKET_STATUS_INELIGIBLE")
            elif {"REQUIRED_METADATA_MISSING", "METADATA_CONFLICT"}.intersection(market.data_gap_codes):
                eligibility, priority, reopen, readiness = "DEFERRED", "DEFER_CAPTURE_REFRESH", "REOPEN_UNAVAILABLE_DATA", "DEFERRED"
                reasons.add("METADATA_CONFLICT" if "METADATA_CONFLICT" in market.data_gap_codes else "REQUIRED_METADATA_MISSING")
            elif market.metadata_freshness in {"STALE", "INVALID_CLOCK"}:
                eligibility, priority, reopen, readiness = "DEFERRED", "DEFER_CAPTURE_REFRESH", "REOPEN_UNAVAILABLE_DATA", "DEFERRED"; reasons.add("METADATA_STALE" if market.metadata_freshness == "STALE" else "METADATA_CLOCK_INVALID")
            elif analysis_temporal_mode == "HISTORICAL_REPLAY":
                eligibility, priority, reopen, readiness = "ELIGIBLE", "MARKET_EVIDENCE_ONLY", "REOPEN_UNAVAILABLE_HISTORICAL_ALPHA_MEMORY", "READY"; reasons.add("ALPHA_MEMORY_HISTORICAL_UNPROVEN")
            elif not matched_candidates:
                eligibility, priority, reopen, readiness = "ELIGIBLE", "NEW_RESEARCH", "NO_REOPEN", "READY"; reasons.add("ALPHA_NO_CANONICAL_MATCH")
            else:
                reopen = _reopen(matched_candidates, matched_episodes, material)
                eligibility, readiness = "ELIGIBLE", "READY"
                if material and reopen == "REOPEN_ELIGIBLE": priority = "MATERIAL_REOPEN"; reasons.add("MATERIAL_CHANGE_REOPEN_ELIGIBLE")
                elif material: priority = "EXISTING_RESEARCH_FOLLOWUP"; reasons.add("MATERIAL_CHANGE_EXISTING_RESEARCH")
                else:
                    leaf, ambiguous = _governing_leaf(matched_candidates, matched_episodes)
                    if ambiguous or (leaf and leaf.result_state in {"RESEARCH_SUPPORTIVE", "DATA_INSUFFICIENT"}): priority = "EXISTING_RESEARCH_FOLLOWUP"; reasons.add("EXISTING_RESEARCH_FOLLOWUP")
                    else: priority = "EXISTING_OTHER"; reopen = "NO_REOPEN"; reasons.add("EXISTING_RESEARCH_NO_CURRENT_TRIGGER")
            newly = prior is not None and market.market_id not in prior_ids
            if newly: reasons.add("NEWLY_OBSERVED_LOCALLY")
            if priority == "DEFER_CAPTURE_REFRESH":
                metadata_reason = next((x for x in ("METADATA_CONFLICT", "REQUIRED_METADATA_MISSING",
                    "METADATA_STALE", "METADATA_CLOCK_INVALID") if x in reasons), None)
                if metadata_reason is not None:
                    requests.append(_capture(market, current.alpha_universe_snapshot_id,
                        policy.alpha_discovery_policy_id, prior_id, priority, metadata_reason,
                        "MARKET_METADATA_REFRESH"))
            if priority not in {"INELIGIBLE", "DEFER_CAPTURE_REFRESH"}:
                overlays = {
                    "OPTIONAL_METADATA_MISSING": "MARKET_METADATA_REFRESH", "RULE_EVIDENCE_MISSING": "RESOLUTION_RULE",
                    "RULE_EVIDENCE_STALE": "RESOLUTION_RULE", "RULE_EVIDENCE_CONFLICT": "RESOLUTION_RULE",
                    "SOURCE_EVIDENCE_MISSING": "SOURCE_SNAPSHOT",
                    "SOURCE_EVIDENCE_STALE": "SOURCE_SNAPSHOT", "SOURCE_EVIDENCE_CONFLICT": "SOURCE_SNAPSHOT",
                    "ORDER_BOOK_MISSING": "ORDER_BOOK", "ORDER_BOOK_STALE": "ORDER_BOOK", "ORDER_BOOK_CONFLICT": "ORDER_BOOK",
                }
                for reason, request in overlays.items():
                    if reason in market.data_gap_codes:
                        readiness = "READY_WITH_CAPTURE_GAPS"; reasons.add(reason)
                        if request == "ORDER_BOOK":
                            for book in market.books:
                                if reason.replace("ORDER_BOOK_", "ORDER_BOOK_") in {book.state, f"ORDER_BOOK_{book.freshness}"}:
                                    requests.append(_capture(market, current.alpha_universe_snapshot_id, policy.alpha_discovery_policy_id, prior_id, priority, reason, request, book.token_id))
                            if not any(r.request_type == request and r.reason_code == reason for r in requests):
                                requests.append(_capture(market, current.alpha_universe_snapshot_id, policy.alpha_discovery_policy_id, prior_id, priority, reason, request))
                        else: requests.append(_capture(market, current.alpha_universe_snapshot_id, policy.alpha_discovery_policy_id, prior_id, priority, reason, request))
            alloc = eligibility == "ELIGIBLE"
            bases.append(PreAllocationTriageBasis(market.market_id, market.event_id, market.category, eligibility, priority, reopen, readiness,
                tuple(sorted(reasons)), tuple(sorted(requests, key=lambda r: (r.request_type, r.token_id or "", r.reason_code))),
                len(change.hard_change_classes) if change else 0, len(change.soft_change_classes) if change else 0,
                change.material_change_event_id if change else None, newly, prior_id, analysis_temporal_mode,
                alpha_memory_temporal_posture, head, tuple(matched_candidates), tuple(matched_family_ids),
                tuple(sorted(e.research_episode_id for e in matched_episodes)), _coverage(matched_episodes, analysis_temporal_mode == "HISTORICAL_REPLAY"), alloc, alloc, alloc))
        return _ok(records=tuple(sorted(bases, key=lambda b: b.market_id)))
    except _Failure as failure:
        return _reject(failure.code)
    except Exception:
        return _reject("INTERNAL_VALIDATION_FAILED")


def allocate_and_finalize_research_queue(current: AlphaUniverseSnapshot, policy: AlphaDiscoveryPolicy, bases: Sequence[PreAllocationTriageBasis], *, prior: AlphaUniverseSnapshot | None = None) -> AlphaDiscoveryResult:
    try:
        for record in (current, policy, *(() if prior is None else (prior,))):
            _semantic_validate(record)
        by_id = {b.market_id: b for b in bases}
        if len(by_id) != len(bases) or set(by_id) != {m.market_id for m in current.markets}:
            raise _Failure("REFERENCE_INVALID")
        eligible = [b for b in bases if b.core_eligible]
        selected: dict[str, str] = {}; lane_order = {"CORE_PRIORITY": [], "EXPLORATION": [], "AUDIT": []}; category_counts: dict[str, int] = {}
        def category(b): return b.category or "UNKNOWN_CATEGORY"
        core_capacity = policy.queue_capacity - policy.exploration_slots - policy.audit_slots
        for basis in sorted(eligible, key=lambda b: b.priority_vector):
            cat = category(basis)
            if len([x for x in selected.values() if x == "CORE_PRIORITY"]) >= core_capacity: break
            if category_counts.get(cat, 0) < policy.max_per_category:
                selected[basis.market_id] = "CORE_PRIORITY"; lane_order["CORE_PRIORITY"].append(basis.market_id); category_counts[cat] = category_counts.get(cat, 0) + 1
        for _ in range(policy.exploration_slots):
            remaining = [b for b in eligible if b.market_id not in selected and category_counts.get(category(b), 0) < policy.max_per_category]
            if not remaining: break
            def explore_key(b):
                coverage = dict(b.coverage)
                return (category_counts.get(category(b), 0), sum(v == "SUPPORTED" for v in coverage.values()), sum(v == "PARTIAL" for v in coverage.values()), b.priority_vector, b.market_id)
            chosen = min(remaining, key=explore_key); selected[chosen.market_id] = "EXPLORATION"; lane_order["EXPLORATION"].append(chosen.market_id)
            category_counts[category(chosen)] = category_counts.get(category(chosen), 0) + 1
        audit_pool = [b for b in eligible if b.market_id not in selected]
        audit_digest = {b.market_id: hashlib.sha256(f"{policy.alpha_discovery_policy_id}|{current.alpha_universe_snapshot_id}|{policy.audit_seed}|{b.market_id}".encode()).hexdigest() for b in audit_pool}
        audit_chosen = sorted(audit_pool, key=lambda b: (audit_digest[b.market_id], b.market_id))[:policy.audit_slots]
        for b in audit_chosen: selected[b.market_id] = "AUDIT"; lane_order["AUDIT"].append(b.market_id)
        decisions = []
        for basis in sorted(bases, key=lambda b: b.market_id):
            lane = selected.get(basis.market_id)
            if lane: disposition = lane
            elif basis.eligibility == "DEFERRED": disposition = "DEFERRED"
            elif basis.eligibility == "INELIGIBLE": disposition = "SKIPPED_INELIGIBLE"
            else: disposition = "SKIPPED_CAPACITY"
            preimage = dict(schema_version=ALPHA_DISCOVERY_SCHEMA_VERSION, policy_id=policy.alpha_discovery_policy_id,
                universe_id=current.alpha_universe_snapshot_id, comparison_prior_universe_id=basis.comparison_prior_universe_id,
                market_id=basis.market_id, event_id=basis.event_id, category=basis.category, eligibility=basis.eligibility,
                priority_class=basis.priority_class, reopen_disposition=basis.reopen_disposition, readiness=basis.readiness,
                reason_codes=basis.reason_codes, capture_requests=basis.capture_requests,
                material_change_event_id=basis.material_change_event_id, newly_observed_locally=basis.newly_observed_locally,
                final_disposition=disposition, selected_lane=lane,
                audit_digest=audit_digest.get(basis.market_id) if lane == "AUDIT" else None,
                audit_eligible_pool_size=len(audit_pool) if lane == "AUDIT" else None,
                audit_selection_fraction_numerator=len(audit_chosen) if lane == "AUDIT" else None,
                audit_selection_fraction_denominator=len(audit_pool) if lane == "AUDIT" and audit_pool else None,
                analysis_temporal_mode=basis.analysis_temporal_mode,
                alpha_memory_temporal_posture=basis.alpha_memory_temporal_posture,
                alpha_registry_head_entry_hash=basis.alpha_registry_head_entry_hash,
                historical_alpha_memory_available=False,
                historical_selection_replay_valid=basis.analysis_temporal_mode == "HISTORICAL_REPLAY",
                historical_replay_valid_for_alpha_memory=False, matched_candidate_ids=basis.matched_candidate_ids,
                matched_hypothesis_family_ids=basis.matched_hypothesis_family_ids,
                matched_research_episode_ids=basis.matched_research_episode_ids, coverage=basis.coverage,
                advisory_only=True, no_execution_authority=True, no_strategy_authority=True, no_qualification_authority=True)
            decision = MarketTriageDecision(**preimage, market_triage_decision_id=_id("alphatriage:sha256:", preimage))
            _semantic_validate(decision)
            decisions.append(decision)
        decision_by_market = {d.market_id: d for d in decisions}
        def ids(disposition):
            if disposition in lane_order:
                return tuple(decision_by_market[mid].market_triage_decision_id for mid in lane_order[disposition])
            return tuple(d.market_triage_decision_id for d in decisions if d.final_disposition == disposition)
        unused_explore = policy.exploration_slots - len(ids("EXPLORATION")); unused_audit = policy.audit_slots - len(ids("AUDIT"))
        reasons = tuple(x for x, count in (("EXPLORATION_POOL_EXHAUSTED", unused_explore), ("AUDIT_POOL_EXHAUSTED", unused_audit)) if count > 0)
        prior_only = tuple(sorted({m.market_id for m in prior.markets} - {m.market_id for m in current.markets})) if prior else ()
        first = bases[0] if bases else None
        qpre = dict(schema_version=ALPHA_DISCOVERY_SCHEMA_VERSION, policy_id=policy.alpha_discovery_policy_id,
            universe_id=current.alpha_universe_snapshot_id, comparison_prior_universe_id=prior.alpha_universe_snapshot_id if prior else None,
            analysis_temporal_mode=first.analysis_temporal_mode if first else "HISTORICAL_REPLAY",
            alpha_memory_temporal_posture=first.alpha_memory_temporal_posture if first else "HISTORICAL_AVAILABILITY_UNPROVEN",
            alpha_registry_head_entry_hash=first.alpha_registry_head_entry_hash if first else None,
            historical_alpha_memory_available=False, historical_selection_replay_valid=(first is None or first.analysis_temporal_mode == "HISTORICAL_REPLAY"),
            core_triage_ids=ids("CORE_PRIORITY"), exploration_triage_ids=ids("EXPLORATION"), audit_triage_ids=ids("AUDIT"),
            deferred_triage_ids=ids("DEFERRED"), skipped_ineligible_triage_ids=ids("SKIPPED_INELIGIBLE"),
            skipped_capacity_triage_ids=ids("SKIPPED_CAPACITY"), all_triage_ids=tuple(d.market_triage_decision_id for d in decisions),
            prior_only_market_ids=prior_only, queue_capacity=policy.queue_capacity,
            configured_exploration_slots=policy.exploration_slots, configured_audit_slots=policy.audit_slots,
            exploration_selected_count=len(ids("EXPLORATION")), audit_selected_count=len(ids("AUDIT")),
            unused_exploration_slots=unused_explore, unused_audit_slots=unused_audit, unused_capacity_reason_codes=reasons,
            max_per_category=policy.max_per_category, advisory_only=True, no_execution_authority=True,
            no_strategy_authority=True, no_qualification_authority=True)
        queue = AlphaResearchQueueSnapshot(**qpre, alpha_research_queue_snapshot_id=_id("alphaqueue:sha256:", qpre))
        _semantic_validate(queue)
        return _ok(queue, (*decisions, queue))
    except _Failure as failure:
        return _reject(failure.code)
    except Exception:
        return _reject("INTERNAL_VALIDATION_FAILED")


_RECORD_ID_FIELDS = {
    AlphaDiscoveryPolicy: "alpha_discovery_policy_id", AlphaUniverseSnapshot: "alpha_universe_snapshot_id",
    MaterialChangeEvent: "material_change_event_id", MarketTriageDecision: "market_triage_decision_id",
    AlphaResearchQueueSnapshot: "alpha_research_queue_snapshot_id",
}


def alpha_discovery_record_to_mapping(record: object) -> dict[str, object]:
    if type(record) not in _RECORD_ID_FIELDS:
        raise ValueError("unsupported alpha discovery record")
    _validate_alpha_discovery_record(record)
    return _canonical(record)  # type: ignore[return-value]


def alpha_discovery_record_from_mapping(record_type: type, mapping: object) -> object:
    if record_type not in _RECORD_ID_FIELDS or not isinstance(mapping, Mapping):
        raise ValueError("unsupported alpha discovery record")
    # Registry decode uses this closed recursive reconstruction path.
    nested = {
        AlphaUniverseSnapshot: {"markets": (ObservedMarketState, {"rules": ResolutionRuleState, "books": OrderBookState})},
        MarketTriageDecision: {"capture_requests": (CaptureRequest, {})},
    }
    _walk(mapping)
    def tuplify(value):
        if isinstance(value, list): return tuple(tuplify(x) for x in value)
        return value
    def construct(cls, data, children=None):
        expected = {f.name for f in fields(cls)}
        if set(data) != expected: raise ValueError("closed field mismatch")
        values = dict(data)
        for name, spec in (children or {}).items():
            child, grand = spec if isinstance(spec, tuple) else (spec, {})
            values[name] = tuple(construct(child, x, grand) for x in values[name])
        for f in fields(cls):
            values[f.name] = tuplify(values[f.name])
        return cls(**values)
    record = construct(record_type, mapping, nested.get(record_type, {}))
    _validate_alpha_discovery_record(record)
    return record
