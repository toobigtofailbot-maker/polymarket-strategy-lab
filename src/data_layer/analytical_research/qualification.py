"""S10-QUAL-01 deterministic qualification candidate packet.

One immutable, content-addressed ``QualificationCandidate`` binds, read-only, the
existing canonical authorities it crosses:

* the Alpha Factory registry (canonical research memory): exact opportunity
  candidate, hypothesis family and the unique current ``RESEARCH_SUPPORTIVE``
  research-episode leaf of that lineage;
* an ``AF1GateReceipt`` (research-system gate evidence) that is ``AF1_PASS`` with
  every AF1 dimension ``PASS``;
* verified ``ResearchProvenanceManifest`` records (common provenance core) whose
  cutoffs and dataset refs are consistent with the candidate cutoff and split plan;
* frozen hypothesis / feature / label / dataset-split / sample-power / test-family
  plans, the conditional B0/B1/B2 forecast-evaluation interface and
  execution-feasibility evidence availability.

The packet is advisory and explicitly NON-qualifying. It makes no qualification
PASS/FAIL/INCONCLUSIVE decision (S10-GATE-QUAL-01 owns that, separately gated), it
constructs no WP170 FeatureDefinition, LabelDefinition, dataset manifest, split,
baseline, family, preregistered experiment, lifecycle receipt or run evidence (WP170
remains the preregistration/OOS authority), and it computes no expected return,
edge, PnL, sizing or profitability (WP172 owns executable economics).

Qualification feature refs are qualification LOGICAL refs. They are deliberately not
claimed to be current WP170 FeatureDefinition ids: the current WP170 feature surface
accepts only market-observation source dependencies and cannot encode a B1
public-non-market feature set.

Wallet-dependent qualification fails closed with ``WALLET_GATE_REQUIRED`` until a
real S10-GATE-WALLET-01 receipt contract exists.

This module is pure and local: no filesystem writes, no registry, no clock, no
randomness, no environment lookup, no network, no Hermes/provider, no wallet
runtime, no paper/execution/live path.
"""

from __future__ import annotations

from dataclasses import dataclass, fields
from decimal import Decimal, InvalidOperation
import hashlib
import json
import re
from typing import Mapping, Sequence

from ..point_in_time_market_research.research_provenance import (
    RESEARCH_PROVENANCE_MANIFEST_SCHEMA_ID,
    RESEARCH_PROVENANCE_MANIFEST_SCHEMA_VERSION,
    ResearchProvenanceManifest,
    canonicalize_utc_timestamp,
    verify_research_provenance_manifest_identity,
)
from .alpha_factory import (
    HypothesisFamily,
    OpportunityCandidate,
    ResearchEpisode,
    record_to_mapping,
)
from .alpha_factory_gate import AF1_DIMENSIONS, AF1GateReceipt, validate_af1_record
from .alpha_factory_registry import AlphaFactoryRegistryEntry, AlphaFactoryRegistrySnapshot
from .experiment_os import (
    CORRECTION_POLICIES,
    EXPERIMENT_OS_SCHEMA_VERSION,
    GROUP_POLICIES,
    METRIC_DIRECTIONS,
)

QUALIFICATION_SCHEMA_VERSION = "1.0.0"
QUALIFICATION_CANDIDATE_SCHEMA_ID = "polymarket-qualification-candidate"
_CANDIDATE_ID_PREFIX = "qualificationcandidate:sha256:"

# ── Closed vocabularies ──────────────────────────────────────────────────────
QUALIFICATION_STATUSES = (
    "QUALIFICATION_CANDIDATE_VALID",
    "QUALIFICATION_CANDIDATE_REJECTED",
)
QUALIFICATION_MODES = ("BINARY_PROBABILITY", "GENERIC_METRIC")
WALLET_DEPENDENCY_MODES = ("NON_WALLET", "WALLET_DEPENDENT")
QUALIFICATION_FEATURE_SOURCE_CLASSES = (
    "PUBLIC_NON_MARKET", "MARKET_PIT", "TIME_ONLY", "MARKET_EXTERNAL_RECONSTRUCTION",
)
QUALIFICATION_PROPER_SCORE_IDS = ("BRIER_SCORE", "LOG_LOSS")
EXECUTION_FEASIBILITY_CLASSES = (
    "FEES",
    "RESOLUTION_RULES",
    "TICK_SIZE_MIN_ORDER",
    "SPREAD_DEPTH",
    "LATENCY",
    "PARTIAL_FILL",
)
EXECUTION_FEASIBILITY_STATES = ("AVAILABLE", "PARTIAL", "MISSING", "NOT_APPLICABLE")

QUALIFICATION_ERROR_CODES = (
    "SCHEMA_UNSUPPORTED",
    "FIELD_MISSING",
    "FIELD_TYPE_INVALID",
    "FIELD_VALUE_INVALID",
    "IDENTITY_DERIVATION_MISMATCH",
    "ALPHA_REGISTRY_INVALID",
    "ALPHA_LINEAGE_INVALID",
    "ALPHA_CURRENT_LEAF_INVALID",
    "ALPHA_RESULT_STATE_INVALID",
    "AF1_RECEIPT_INVALID",
    "AF1_NOT_PASS",
    "PROVENANCE_INVALID",
    "CUTOFF_INVALID",
    "HYPOTHESIS_PLAN_INVALID",
    "FEATURE_PLAN_INVALID",
    "LABEL_PLAN_INVALID",
    "DATASET_SPLIT_PLAN_INVALID",
    "POWER_PLAN_INVALID",
    "TEST_FAMILY_PLAN_INVALID",
    "FORECAST_PLAN_INVALID",
    "EXECUTION_FEASIBILITY_INVALID",
    "WALLET_GATE_REQUIRED",
    "AUTHORITY_INVARIANT_INVALID",
    "LIMIT_EXCEEDED",
    "INTERNAL_VALIDATION_FAILED",
)
_ERROR_ORDER = {code: index for index, code in enumerate(QUALIFICATION_ERROR_CODES)}

# Frozen plan literals.
FEATURE_AVAILABILITY_RULE = "FEATURE_AVAILABLE_AT_OR_BEFORE_DECISION_TIME"
FEATURE_NO_FUTURE_INFORMATION_RULE = "NO_POST_DECISION_OR_POST_OUTCOME_INFORMATION"
SPLIT_EVENT_GROUPING_RULE = "LEAKAGE_MARKET_RELATED_EXCLUSIVE"
SPLIT_PURGE_RULE = "PURGE_LABEL_AVAILABILITY_AT_OR_AFTER_NEXT_BOUNDARY"
SPLIT_INCLUSION_POLICY = "DECISION_TIME_HALF_OPEN"
SPLIT_GROUP_POLICY = "EXCLUSIVE"
# Existing WP170 ResearchSample keys the event-grouping rule isolates across roles.
SPLIT_EVENT_GROUPING_KEYS = ("leakage_group_id", "market_id", "related_group_id")
HYPOTHESIS_REVIEW_STATE = "REVIEWED"
B0_RULE_PIT_MARKET_PROBABILITY_V1 = "PIT_MARKET_PROBABILITY_V1"
# S10-QUAL-B0X-01: third-party external-reconstruction B0 (never canonical PIT). Same
# parameters and fallback mechanics; observability is external capture receipt time.
B0_RULE_EXTERNAL_PIT_MARKET_PROBABILITY_V1 = "EXTERNAL_PIT_MARKET_PROBABILITY_V1"
# Each B0 rule admits exactly one B2 market-added feature source class (no mixing).
_B0_RULE_MARKET_ADDED_SOURCE_CLASS = {
    B0_RULE_PIT_MARKET_PROBABILITY_V1: "MARKET_PIT",
    B0_RULE_EXTERNAL_PIT_MARKET_PROBABILITY_V1: "MARKET_EXTERNAL_RECONSTRUCTION",
}
FORECAST_APPLICABILITY_REQUIRED = "REQUIRED"
FORECAST_APPLICABILITY_NOT_APPLICABLE = "NOT_APPLICABLE"
_THRESHOLD_OPERATOR_FOR_DIRECTION = {"HIGHER_IS_BETTER": "GTE", "LOWER_IS_BETTER": "LTE"}
_BASELINE_RULE_FOR_DIRECTION = {
    "HIGHER_IS_BETTER": "CANDIDATE_GTE_BASELINE",
    "LOWER_IS_BETTER": "CANDIDATE_LTE_BASELINE",
}

# Upstream canonical id prefixes (structural sanity of a serialized packet).
_ALPHA_REGISTRY_ENTRY_PREFIX = "alpharegistryentry:sha256:"
_ALPHA_CANDIDATE_PREFIX = "alphacandidate:sha256:"
_ALPHA_FAMILY_PREFIX = "alphafamily:sha256:"
_ALPHA_EPISODE_PREFIX = "alphaepisode:sha256:"
_AF1_GATE_PREFIX = "af1gate:sha256:"
_PROVENANCE_MANIFEST_PREFIX = "researchmanifest:sha256:"

# ── Conservative bounds ──────────────────────────────────────────────────────
MAX_QUALIFICATION_TEXT_CHARS = 4096
MAX_QUALIFICATION_SEQUENCE_ITEMS = 256
MAX_QUALIFICATION_PROVENANCE_MANIFESTS = 256
MAX_QUALIFICATION_INPUT_DEPTH = 8
MAX_QUALIFICATION_INPUT_NODES = 8192
MAX_QUALIFICATION_PLAN_JSON_BYTES = 262_144
MAX_QUALIFICATION_COUNT = 1_000_000_000_000

_ID_RE = re.compile(r"^[A-Za-z0-9._:-]{1,512}$")
_PATH_LIKE_RE = re.compile(r"(^~)|(^[A-Za-z]:)|[\\/]")
_SHA_SUFFIX_RE = re.compile(r"^[0-9a-f]{64}$")
_UTC_RE = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,6})?Z$"
)
_DECIMAL_RE = re.compile(r"^-?(?:0|[1-9][0-9]*)(?:\.[0-9]*[1-9])?$")


# ── Records ──────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class QualificationCandidate:
    schema_id: str
    schema_version: str
    qualification_candidate_id: str
    candidate_version: str
    alpha_registry_head_entry_hash: str
    alpha_candidate_id: str
    hypothesis_family_id: str
    governing_research_episode_id: str
    af1_gate_receipt_id: str
    research_provenance_manifest_ids: tuple[str, ...]
    information_cutoff: str
    qualification_mode: str
    experiment_os_schema_version: str
    hypothesis_plan_json: str
    feature_plan_json: str
    label_plan_json: str
    dataset_split_plan_json: str
    sample_power_plan_json: str
    test_family_plan_json: str
    forecast_evaluation_plan_json: str
    execution_feasibility_plan_json: str
    wallet_dependency: str
    creation_provenance: str
    advisory_only: bool
    human_review_required: bool
    no_execution_authority: bool
    no_strategy_authority: bool
    no_qualification_authority: bool


@dataclass(frozen=True)
class QualificationControlResult:
    is_valid: bool
    status: str
    error_codes: tuple[str, ...]
    record: QualificationCandidate | None
    advisory_only: bool
    no_execution_authority: bool
    no_strategy_authority: bool
    no_qualification_authority: bool


_AUTHORITY_FIELDS = (
    "advisory_only",
    "human_review_required",
    "no_execution_authority",
    "no_strategy_authority",
    "no_qualification_authority",
)


# ── Failure/result plumbing ──────────────────────────────────────────────────
class _Failure(Exception):
    def __init__(self, code: str):
        self.code = code


def _rejected(code: str) -> QualificationControlResult:
    # Final public closure: an out-of-vocabulary code never reaches a public result.
    if code not in _ERROR_ORDER:
        code = "INTERNAL_VALIDATION_FAILED"
    return QualificationControlResult(
        False, "QUALIFICATION_CANDIDATE_REJECTED", (code,), None, True, True, True, True
    )


def _valid(record: QualificationCandidate) -> QualificationControlResult:
    return QualificationControlResult(
        True, "QUALIFICATION_CANDIDATE_VALID", (), record, True, True, True, True
    )


class _Plan:
    """Scope a plan validator so every structural failure maps to one plan code."""

    def __init__(self, code: str):
        self.code = code

    def __enter__(self) -> "_Plan":
        return self

    def __exit__(self, exc_type, exc, _tb) -> bool:
        if exc_type is None:
            return False
        if isinstance(exc, _Failure) and exc.code in {"LIMIT_EXCEEDED", self.code}:
            return False
        if isinstance(exc, (_Failure, TypeError, ValueError, KeyError)):
            raise _Failure(self.code) from None
        return False


# ── Scalar validators ────────────────────────────────────────────────────────
def _text(value: object) -> str:
    if not isinstance(value, str):
        raise _Failure("FIELD_TYPE_INVALID")
    if (
        not value or value != value.strip() or len(value) > MAX_QUALIFICATION_TEXT_CHARS
        or "\x00" in value
    ):
        raise _Failure("FIELD_VALUE_INVALID")
    return value


def _opaque(value: object) -> str:
    """Bounded opaque id in the current WP170 opaque-id grammar."""
    text = _text(value)
    if _ID_RE.fullmatch(text) is None:
        raise _Failure("FIELD_VALUE_INVALID")
    return text


def _evidence_id(value: object) -> str:
    """Bounded opaque reference that is never a filesystem-path-like value."""
    text = _opaque(value)
    if _PATH_LIKE_RE.search(text):
        raise _Failure("FIELD_VALUE_INVALID")
    return text


def _prefixed(value: object, prefix: str) -> str:
    text = _evidence_id(value)
    if not text.startswith(prefix) or _SHA_SUFFIX_RE.fullmatch(text[len(prefix):]) is None:
        raise _Failure("FIELD_VALUE_INVALID")
    return text


def _enum(value: object, allowed: Sequence[str]) -> str:
    if not isinstance(value, str):
        raise _Failure("FIELD_TYPE_INVALID")
    if value not in allowed:
        raise _Failure("FIELD_VALUE_INVALID")
    return value


def _literal(value: object, expected: str) -> str:
    return _enum(value, (expected,))


def _true(value: object) -> bool:
    if value is not True:
        raise _Failure("FIELD_VALUE_INVALID" if isinstance(value, bool) else "FIELD_TYPE_INVALID")
    return True


def _integer(value: object, minimum: int) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise _Failure("FIELD_TYPE_INVALID")
    if value < minimum or value > MAX_QUALIFICATION_COUNT:
        raise _Failure("FIELD_VALUE_INVALID")
    return value


def _decimal(value: object) -> Decimal:
    """Canonical finite decimal string (the current WP170 decimal grammar)."""
    if not isinstance(value, str):
        raise _Failure("FIELD_TYPE_INVALID")
    if _DECIMAL_RE.fullmatch(value) is None or value == "-0":
        raise _Failure("FIELD_VALUE_INVALID")
    try:
        parsed = Decimal(value)
    except InvalidOperation:
        raise _Failure("FIELD_VALUE_INVALID") from None
    if not parsed.is_finite():
        raise _Failure("FIELD_VALUE_INVALID")
    return parsed


def _utc(value: object) -> str:
    """Canonical UTC ``...Z`` timestamp (<= 6 fraction digits, no trailing zeros)."""
    if not isinstance(value, str):
        raise _Failure("FIELD_TYPE_INVALID")
    if _UTC_RE.fullmatch(value) is None:
        raise _Failure("FIELD_VALUE_INVALID")
    try:
        canonical = canonicalize_utc_timestamp(value)
    except ValueError:
        raise _Failure("FIELD_VALUE_INVALID") from None
    if canonical != value:
        raise _Failure("FIELD_VALUE_INVALID")
    return value


def _utc_key(value: str) -> tuple[str, Decimal]:
    """Order key for a canonical ``YYYY-MM-DDTHH:MM:SS[.f]Z`` timestamp."""
    seconds = value[:19]
    fraction = value[19:-1]
    return seconds, Decimal("0" + fraction) if fraction else Decimal(0)


def _mapping(value: object, keys: frozenset[str]) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise _Failure("FIELD_TYPE_INVALID")
    actual = set(value.keys())
    if any(not isinstance(key, str) for key in actual):
        raise _Failure("FIELD_TYPE_INVALID")
    if keys - actual:
        raise _Failure("FIELD_MISSING")
    if actual - keys:
        raise _Failure("FIELD_VALUE_INVALID")
    return value


def _sorted_ids(value: object, *, allow_empty: bool = False, opaque_only: bool = False) -> list[str]:
    """Sorted unique bounded references; caller duplicates reject."""
    if not isinstance(value, (list, tuple)):
        raise _Failure("FIELD_TYPE_INVALID")
    if not value and not allow_empty:
        raise _Failure("FIELD_VALUE_INVALID")
    if len(value) > MAX_QUALIFICATION_SEQUENCE_ITEMS:
        raise _Failure("LIMIT_EXCEEDED")
    check = _opaque if opaque_only else _evidence_id
    out = [check(item) for item in value]
    if len(set(out)) != len(out):
        raise _Failure("FIELD_VALUE_INVALID")
    return sorted(out)


# ── Canonical JSON ───────────────────────────────────────────────────────────
def _scan_input(value: object, depth: int, counter: list[int]) -> None:
    """Reject binary floats and non-JSON values recursively, with bounded size."""
    if depth > MAX_QUALIFICATION_INPUT_DEPTH:
        raise _Failure("LIMIT_EXCEEDED")
    counter[0] += 1
    if counter[0] > MAX_QUALIFICATION_INPUT_NODES:
        raise _Failure("LIMIT_EXCEEDED")
    if value is None or isinstance(value, (bool, str)):
        return
    if isinstance(value, int):
        return
    if isinstance(value, Mapping):
        for key in value:
            if not isinstance(key, str):
                raise _Failure("FIELD_TYPE_INVALID")
            _scan_input(value[key], depth + 1, counter)
        return
    if isinstance(value, (list, tuple)):
        for item in value:
            _scan_input(item, depth + 1, counter)
        return
    # float (incl. NaN/Infinity), Decimal, bytes, set and any other object.
    raise _Failure("FIELD_TYPE_INVALID")


def _canonical_bytes(value: object) -> bytes:
    try:
        return json.dumps(
            value, ensure_ascii=False, separators=(",", ":"), sort_keys=True,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeError):
        raise _Failure("FIELD_VALUE_INVALID") from None


def _plan_json(plan: Mapping[str, object]) -> str:
    raw = _canonical_bytes(plan)
    if len(raw) > MAX_QUALIFICATION_PLAN_JSON_BYTES:
        raise _Failure("LIMIT_EXCEEDED")
    return raw.decode("utf-8")


def _reject_constant(_token: str) -> object:
    raise ValueError("non-finite constant")


def _reject_float(_token: str) -> object:
    raise ValueError("binary float")


def _strict_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, item in pairs:
        if key in result:
            raise ValueError("duplicate key")
        result[key] = item
    return result


def _decode_plan(value: object) -> dict[str, object]:
    if not isinstance(value, str):
        raise _Failure("FIELD_TYPE_INVALID")
    if len(value.encode("utf-8")) > MAX_QUALIFICATION_PLAN_JSON_BYTES:
        raise _Failure("LIMIT_EXCEEDED")
    try:
        decoded = json.loads(
            value, object_pairs_hook=_strict_pairs, parse_constant=_reject_constant,
            parse_float=_reject_float,
        )
    except (TypeError, ValueError, UnicodeError, RecursionError):
        raise _Failure("FIELD_VALUE_INVALID") from None
    if not isinstance(decoded, dict):
        raise _Failure("FIELD_VALUE_INVALID")
    return decoded


def _digest(preimage: Mapping[str, object]) -> str:
    wrapped = {"qualification_candidate.identity_preimage": preimage}
    return _CANDIDATE_ID_PREFIX + hashlib.sha256(_canonical_bytes(wrapped)).hexdigest()


# ── Plan validators (each returns the canonical normalized plan) ─────────────
_HYPOTHESIS_KEYS = frozenset({
    "hypothesis_name", "hypothesis_version", "falsifiable_claim", "proposed_mechanism",
    "cohort", "horizon", "target", "falsification_condition", "human_review_state",
    "review_assertion", "code_version",
})
_HYPOTHESIS_OPAQUE = ("hypothesis_name", "hypothesis_version", "code_version")


def _hypothesis_plan(value: object) -> dict[str, object]:
    with _Plan("HYPOTHESIS_PLAN_INVALID"):
        plan = _mapping(value, _HYPOTHESIS_KEYS)
        out: dict[str, object] = {}
        for key in sorted(_HYPOTHESIS_KEYS):
            if key in _HYPOTHESIS_OPAQUE:
                out[key] = _opaque(plan[key])
            elif key == "human_review_state":
                out[key] = _literal(plan[key], HYPOTHESIS_REVIEW_STATE)
            else:
                out[key] = _text(plan[key])
        return out


_FEATURE_KEYS = frozenset({
    "feature_refs", "feature_source_classes", "feature_evidence_refs",
    "availability_rule", "no_future_information_rule", "missing_data_policy",
})


def _keyed_by(value: object, refs: list[str]) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise _Failure("FIELD_TYPE_INVALID")
    if any(not isinstance(key, str) for key in value) or set(value) != set(refs):
        raise _Failure("FIELD_VALUE_INVALID")
    return value


def _feature_plan(value: object) -> dict[str, object]:
    with _Plan("FEATURE_PLAN_INVALID"):
        plan = _mapping(value, _FEATURE_KEYS)
        refs = _sorted_ids(plan["feature_refs"])
        classes = _keyed_by(plan["feature_source_classes"], refs)
        evidence = _keyed_by(plan["feature_evidence_refs"], refs)
        return {
            "feature_refs": refs,
            "feature_source_classes": {
                ref: _enum(classes[ref], QUALIFICATION_FEATURE_SOURCE_CLASSES) for ref in refs
            },
            "feature_evidence_refs": {ref: _sorted_ids(evidence[ref]) for ref in refs},
            "availability_rule": _literal(plan["availability_rule"], FEATURE_AVAILABILITY_RULE),
            "no_future_information_rule": _literal(
                plan["no_future_information_rule"], FEATURE_NO_FUTURE_INFORMATION_RULE
            ),
            "missing_data_policy": _text(plan["missing_data_policy"]),
        }


_LABEL_KEYS = frozenset({
    "label_ref", "prediction_target", "horizon_rule", "target_time_rule",
    "outcome_source_rule", "availability_time_rule", "censoring_rule",
    "evidence_reference_ids",
})
_LABEL_TEXT = (
    "prediction_target", "horizon_rule", "target_time_rule", "outcome_source_rule",
    "availability_time_rule", "censoring_rule",
)


def _label_plan(value: object) -> dict[str, object]:
    with _Plan("LABEL_PLAN_INVALID"):
        plan = _mapping(value, _LABEL_KEYS)
        out: dict[str, object] = {"label_ref": _evidence_id(plan["label_ref"])}
        for key in _LABEL_TEXT:
            out[key] = _text(plan[key])
        out["evidence_reference_ids"] = _sorted_ids(plan["evidence_reference_ids"])
        return out


_SPLIT_KEYS = frozenset({
    "dataset_snapshot_reference_ids", "group_policy", "event_grouping_rule",
    "formation_start", "selection_start", "oos_start", "end_time", "purge_rule",
    "embargo_seconds", "inclusion_policy", "min_samples_per_role",
})
_SPLIT_BOUNDARIES = ("formation_start", "selection_start", "oos_start", "end_time")


def _dataset_split_plan(value: object) -> dict[str, object]:
    with _Plan("DATASET_SPLIT_PLAN_INVALID"):
        plan = _mapping(value, _SPLIT_KEYS)
        boundaries = [_utc(plan[key]) for key in _SPLIT_BOUNDARIES]
        if not all(_utc_key(boundaries[i]) < _utc_key(boundaries[i + 1]) for i in range(3)):
            raise _Failure("FIELD_VALUE_INVALID")
        group_policy = _enum(plan["group_policy"], GROUP_POLICIES)
        if group_policy != SPLIT_GROUP_POLICY:
            raise _Failure("FIELD_VALUE_INVALID")
        out: dict[str, object] = {
            "dataset_snapshot_reference_ids": _sorted_ids(plan["dataset_snapshot_reference_ids"]),
            "group_policy": group_policy,
            "event_grouping_rule": _literal(plan["event_grouping_rule"], SPLIT_EVENT_GROUPING_RULE),
            "purge_rule": _literal(plan["purge_rule"], SPLIT_PURGE_RULE),
            "embargo_seconds": _integer(plan["embargo_seconds"], 0),
            "inclusion_policy": _literal(plan["inclusion_policy"], SPLIT_INCLUSION_POLICY),
            "min_samples_per_role": _integer(plan["min_samples_per_role"], 1),
        }
        out.update(zip(_SPLIT_BOUNDARIES, boundaries))
        return out


_POWER_KEYS = frozenset({
    "analysis_unit", "available_sample_count", "available_independent_group_count",
    "required_sample_count", "required_independent_group_count", "power_method",
    "power_analysis_reference_id", "target_power", "significance_level",
    "minimum_detectable_effect",
})


def _sample_power_plan(value: object) -> dict[str, object]:
    """Freeze declared sample/power FACTS. A shortfall is a valid fact, never a
    structural rejection, and no count comparison ever qualifies a candidate."""
    with _Plan("POWER_PLAN_INVALID"):
        plan = _mapping(value, _POWER_KEYS)
        target_power = plan["target_power"]
        significance = plan["significance_level"]
        effect = plan["minimum_detectable_effect"]
        if not Decimal(0) < _decimal(target_power) <= Decimal(1):
            raise _Failure("FIELD_VALUE_INVALID")
        if not Decimal(0) < _decimal(significance) < Decimal(1):
            raise _Failure("FIELD_VALUE_INVALID")
        if not _decimal(effect) > Decimal(0):
            raise _Failure("FIELD_VALUE_INVALID")
        return {
            "analysis_unit": _text(plan["analysis_unit"]),
            "available_sample_count": _integer(plan["available_sample_count"], 0),
            "available_independent_group_count": _integer(
                plan["available_independent_group_count"], 0
            ),
            "required_sample_count": _integer(plan["required_sample_count"], 1),
            "required_independent_group_count": _integer(
                plan["required_independent_group_count"], 1
            ),
            "power_method": _text(plan["power_method"]),
            "power_analysis_reference_id": _evidence_id(plan["power_analysis_reference_id"]),
            "target_power": target_power,
            "significance_level": significance,
            "minimum_detectable_effect": effect,
        }


_TEST_FAMILY_KEYS = frozenset({
    "research_program", "metric_family", "primary_metric_name",
    "primary_metric_direction", "secondary_metric_names", "correction_policy",
    "multiplicity_method", "family_size", "acceptance_thresholds",
    "baseline_acceptance_rule",
})
_THRESHOLD_KEYS = frozenset({"primary_metric_operator", "primary_metric_threshold"})


def _test_family_plan(value: object) -> dict[str, object]:
    with _Plan("TEST_FAMILY_PLAN_INVALID"):
        plan = _mapping(value, _TEST_FAMILY_KEYS)
        direction = _enum(plan["primary_metric_direction"], METRIC_DIRECTIONS)
        correction = _enum(plan["correction_policy"], CORRECTION_POLICIES)
        family_size = _integer(plan["family_size"], 1)
        if correction == "SINGLETON" and family_size != 1:
            raise _Failure("FIELD_VALUE_INVALID")
        primary = _opaque(plan["primary_metric_name"])
        secondary = _sorted_ids(plan["secondary_metric_names"], allow_empty=True, opaque_only=True)
        if primary in secondary:
            raise _Failure("FIELD_VALUE_INVALID")
        thresholds = _mapping(plan["acceptance_thresholds"], _THRESHOLD_KEYS)
        operator = _enum(thresholds["primary_metric_operator"], ("GTE", "LTE"))
        if operator != _THRESHOLD_OPERATOR_FOR_DIRECTION[direction]:
            raise _Failure("FIELD_VALUE_INVALID")
        threshold = thresholds["primary_metric_threshold"]
        _decimal(threshold)
        baseline_rule = _enum(
            plan["baseline_acceptance_rule"], tuple(_BASELINE_RULE_FOR_DIRECTION.values())
        )
        if baseline_rule != _BASELINE_RULE_FOR_DIRECTION[direction]:
            raise _Failure("FIELD_VALUE_INVALID")
        return {
            "research_program": _text(plan["research_program"]),
            "metric_family": _text(plan["metric_family"]),
            "primary_metric_name": primary,
            "primary_metric_direction": direction,
            "secondary_metric_names": secondary,
            "correction_policy": correction,
            "multiplicity_method": _text(plan["multiplicity_method"]),
            "family_size": family_size,
            "acceptance_thresholds": {
                "primary_metric_operator": operator,
                "primary_metric_threshold": threshold,
            },
            "baseline_acceptance_rule": baseline_rule,
        }


_FORECAST_KEYS = frozenset({
    "applicability", "b0_rule", "b0_parameters", "b1_feature_refs", "b2_feature_refs",
    "b2_market_added_feature_refs", "primary_proper_score", "calibration_diagnostic",
    "same_oos_membership_required", "b1_vs_b0_required", "b2_vs_b0_required",
    "b2_vs_b1_incrementality_required",
})
_B0_PARAMETER_KEYS = frozenset({"max_midpoint_spread", "max_last_trade_age_seconds"})
_FORECAST_REQUIRED_TRUE = (
    "same_oos_membership_required", "b1_vs_b0_required", "b2_vs_b0_required",
    "b2_vs_b1_incrementality_required",
)
_NOT_APPLICABLE_FORECAST = {"applicability": FORECAST_APPLICABILITY_NOT_APPLICABLE}


def _forecast_plan(
    value: object, mode: str, feature_plan: Mapping[str, object],
    test_family_plan: Mapping[str, object],
) -> dict[str, object]:
    with _Plan("FORECAST_PLAN_INVALID"):
        if mode == "GENERIC_METRIC":
            plan = _mapping(value, frozenset({"applicability"}))
            _literal(plan["applicability"], FORECAST_APPLICABILITY_NOT_APPLICABLE)
            return dict(_NOT_APPLICABLE_FORECAST)
        plan = _mapping(value, _FORECAST_KEYS)
        _literal(plan["applicability"], FORECAST_APPLICABILITY_REQUIRED)
        b0_rule = _enum(plan["b0_rule"], tuple(_B0_RULE_MARKET_ADDED_SOURCE_CLASS))
        b0 = _mapping(plan["b0_parameters"], _B0_PARAMETER_KEYS)
        spread = b0["max_midpoint_spread"]
        if not Decimal(0) <= _decimal(spread) <= Decimal(1):
            raise _Failure("FIELD_VALUE_INVALID")
        age = _integer(b0["max_last_trade_age_seconds"], 0)
        classes = feature_plan["feature_source_classes"]
        assert isinstance(classes, Mapping)
        b1 = _sorted_ids(plan["b1_feature_refs"])
        added = _sorted_ids(plan["b2_market_added_feature_refs"])
        b2 = _sorted_ids(plan["b2_feature_refs"])
        # B1 is the independent-information set: never a market-derived input.
        if any(classes.get(ref) not in {"PUBLIC_NON_MARKET", "TIME_ONLY"} for ref in b1):
            raise _Failure("FIELD_VALUE_INVALID")
        # B2 adds only explicit market refs of the B0 rule's own source class on top of
        # the exact B1 set: MARKET_PIT for canonical B0, MARKET_EXTERNAL_RECONSTRUCTION for
        # external B0; any other or mixed class rejects.
        market_class = _B0_RULE_MARKET_ADDED_SOURCE_CLASS[b0_rule]
        if any(classes.get(ref) != market_class for ref in added):
            raise _Failure("FIELD_VALUE_INVALID")
        if b2 != sorted(set(b1) | set(added)):
            raise _Failure("FIELD_VALUE_INVALID")
        score = _enum(plan["primary_proper_score"], QUALIFICATION_PROPER_SCORE_IDS)
        for key in _FORECAST_REQUIRED_TRUE:
            _true(plan[key])
        # A binary-probability primary metric is the chosen proper score, lower is better.
        if (
            test_family_plan["primary_metric_name"] != score
            or test_family_plan["primary_metric_direction"] != "LOWER_IS_BETTER"
            or test_family_plan["baseline_acceptance_rule"] != "CANDIDATE_LTE_BASELINE"
        ):
            raise _Failure("FIELD_VALUE_INVALID")
        return {
            "applicability": FORECAST_APPLICABILITY_REQUIRED,
            "b0_rule": b0_rule,
            "b0_parameters": {
                "max_midpoint_spread": spread,
                "max_last_trade_age_seconds": age,
            },
            "b1_feature_refs": b1,
            "b2_feature_refs": b2,
            "b2_market_added_feature_refs": added,
            "primary_proper_score": score,
            "calibration_diagnostic": _text(plan["calibration_diagnostic"]),
            **{key: True for key in _FORECAST_REQUIRED_TRUE},
        }


_FEASIBILITY_ENTRY_KEYS = frozenset({"state", "evidence_reference_ids"})


def _execution_feasibility_plan(value: object) -> dict[str, object]:
    """Evidence AVAILABILITY only: no return, PnL, edge, capacity, sizing or side."""
    with _Plan("EXECUTION_FEASIBILITY_INVALID"):
        plan = _mapping(value, frozenset(EXECUTION_FEASIBILITY_CLASSES))
        out: dict[str, object] = {}
        for name in EXECUTION_FEASIBILITY_CLASSES:
            entry = _mapping(plan[name], _FEASIBILITY_ENTRY_KEYS)
            state = _enum(entry["state"], EXECUTION_FEASIBILITY_STATES)
            refs = _sorted_ids(entry["evidence_reference_ids"], allow_empty=True)
            if (state in {"AVAILABLE", "PARTIAL"}) != bool(refs):
                raise _Failure("FIELD_VALUE_INVALID")
            out[name] = {"state": state, "evidence_reference_ids": refs}
        return out


def _cross_plan(feature_plan: Mapping[str, object], label_plan: Mapping[str, object]) -> None:
    # The label/outcome is never itself a decision-time feature.
    refs = feature_plan["feature_refs"]
    assert isinstance(refs, list)
    if label_plan["label_ref"] in refs:
        raise _Failure("LABEL_PLAN_INVALID")


def _normalize_plans(
    mode: str, raw: Mapping[str, object]
) -> dict[str, dict[str, object]]:
    hypothesis = _hypothesis_plan(raw["hypothesis_plan"])
    feature = _feature_plan(raw["feature_plan"])
    label = _label_plan(raw["label_plan"])
    _cross_plan(feature, label)
    split = _dataset_split_plan(raw["dataset_split_plan"])
    power = _sample_power_plan(raw["sample_power_plan"])
    test_family = _test_family_plan(raw["test_family_plan"])
    forecast = _forecast_plan(raw["forecast_evaluation_plan"], mode, feature, test_family)
    feasibility = _execution_feasibility_plan(raw["execution_feasibility_plan"])
    return {
        "hypothesis_plan": hypothesis,
        "feature_plan": feature,
        "label_plan": label,
        "dataset_split_plan": split,
        "sample_power_plan": power,
        "test_family_plan": test_family,
        "forecast_evaluation_plan": forecast,
        "execution_feasibility_plan": feasibility,
    }


_PLAN_NAMES = (
    "hypothesis_plan", "feature_plan", "label_plan", "dataset_split_plan",
    "sample_power_plan", "test_family_plan", "forecast_evaluation_plan",
    "execution_feasibility_plan",
)


# ── Record-semantic validation (the single shared gate) ──────────────────────
def _preimage(record: QualificationCandidate) -> dict[str, object]:
    preimage: dict[str, object] = {}
    for field in fields(record):
        if field.name == "qualification_candidate_id":
            continue
        raw = getattr(record, field.name)
        preimage[field.name] = list(raw) if isinstance(raw, tuple) else raw
    return preimage


def _validate_record(record: object) -> QualificationCandidate:
    """Re-prove a record is ALREADY a canonical valid QualificationCandidate.

    Never normalizes or repairs: every nested plan is decoded, re-validated,
    re-canonicalized and compared byte-for-byte, and the identity is re-derived, so
    a directly constructed dataclass with a self-consistent id cannot bypass the
    semantic rules the builder enforces.
    """
    if type(record) is not QualificationCandidate:
        raise _Failure("FIELD_TYPE_INVALID")
    if (
        record.schema_id != QUALIFICATION_CANDIDATE_SCHEMA_ID
        or record.schema_version != QUALIFICATION_SCHEMA_VERSION
        or record.experiment_os_schema_version != EXPERIMENT_OS_SCHEMA_VERSION
    ):
        raise _Failure("SCHEMA_UNSUPPORTED")
    for name in _AUTHORITY_FIELDS:
        if getattr(record, name) is not True:
            raise _Failure("AUTHORITY_INVARIANT_INVALID")
    if record.wallet_dependency != "NON_WALLET":
        raise _Failure(
            "WALLET_GATE_REQUIRED" if record.wallet_dependency == "WALLET_DEPENDENT"
            else "FIELD_VALUE_INVALID"
        )
    _opaque(record.candidate_version)
    _prefixed(record.alpha_registry_head_entry_hash, _ALPHA_REGISTRY_ENTRY_PREFIX)
    _prefixed(record.alpha_candidate_id, _ALPHA_CANDIDATE_PREFIX)
    _prefixed(record.hypothesis_family_id, _ALPHA_FAMILY_PREFIX)
    _prefixed(record.governing_research_episode_id, _ALPHA_EPISODE_PREFIX)
    _prefixed(record.af1_gate_receipt_id, _AF1_GATE_PREFIX)
    manifest_ids = record.research_provenance_manifest_ids
    if not isinstance(manifest_ids, tuple):
        raise _Failure("FIELD_TYPE_INVALID")
    if not manifest_ids or len(manifest_ids) > MAX_QUALIFICATION_PROVENANCE_MANIFESTS:
        raise _Failure("FIELD_VALUE_INVALID")
    for manifest_id in manifest_ids:
        _prefixed(manifest_id, _PROVENANCE_MANIFEST_PREFIX)
    if list(manifest_ids) != sorted(set(manifest_ids)):
        raise _Failure("FIELD_VALUE_INVALID")
    try:
        _utc(record.information_cutoff)
    except _Failure:
        raise _Failure("CUTOFF_INVALID") from None
    mode = _enum(record.qualification_mode, QUALIFICATION_MODES)
    _text(record.creation_provenance)
    decoded = {name: _decode_plan(getattr(record, f"{name}_json")) for name in _PLAN_NAMES}
    plans = _normalize_plans(mode, decoded)
    for name in _PLAN_NAMES:
        if _plan_json(plans[name]) != getattr(record, f"{name}_json"):
            raise _Failure("FIELD_VALUE_INVALID")
    if _digest(_preimage(record)) != record.qualification_candidate_id:
        raise _Failure("IDENTITY_DERIVATION_MISMATCH")
    return record


def validate_qualification_candidate(record: object) -> QualificationControlResult:
    """Full internal record-semantic validation of a serialized/direct packet.

    This proves only the packet's own closed schema, plan semantics and identity. It
    does NOT claim the bound Alpha lineage, AF1 receipt or provenance manifests are
    still current: the future qualification gate must re-bind and re-verify them.
    """
    try:
        return _valid(_validate_record(record))
    except _Failure as failure:
        return _rejected(failure.code)
    except Exception:
        return _rejected("INTERNAL_VALIDATION_FAILED")


# ── External crossing: Alpha lineage / AF1 / provenance ──────────────────────
_ALPHA_ID_FIELD = {
    OpportunityCandidate: "candidate_id",
    HypothesisFamily: "hypothesis_family_id",
    ResearchEpisode: "research_episode_id",
}


def _recheck_alpha(record: object) -> None:
    # The existing public Alpha Factory record-semantic validator is the oracle.
    try:
        record_to_mapping(record)
    except Exception:
        raise _Failure("ALPHA_REGISTRY_INVALID") from None


def _alpha_lineage(
    snapshot: object, candidate_id: str, family_id: str, episode_id: str
) -> tuple[str, ResearchEpisode]:
    if type(snapshot) is not AlphaFactoryRegistrySnapshot:
        raise _Failure("ALPHA_REGISTRY_INVALID")
    if not all(
        getattr(snapshot, flag) is True
        for flag in (
            "advisory_only", "no_execution_authority", "no_strategy_authority",
            "no_qualification_authority",
        )
    ):
        raise _Failure("ALPHA_REGISTRY_INVALID")
    entries = snapshot.entries
    if not isinstance(entries, tuple) or not entries:
        raise _Failure("ALPHA_REGISTRY_INVALID")
    if not isinstance(snapshot.total_rows, int) or snapshot.total_rows != len(entries):
        raise _Failure("ALPHA_REGISTRY_INVALID")
    previous: str | None = None
    records: dict[str, object] = {}
    for sequence, entry in enumerate(entries):
        if type(entry) is not AlphaFactoryRegistryEntry:
            raise _Failure("ALPHA_REGISTRY_INVALID")
        if entry.sequence_number != sequence or entry.previous_entry_hash != previous:
            raise _Failure("ALPHA_REGISTRY_INVALID")
        if not isinstance(entry.entry_hash, str) or entry.record_id in records:
            raise _Failure("ALPHA_REGISTRY_INVALID")
        id_field = _ALPHA_ID_FIELD.get(type(entry.record))
        if id_field is not None and getattr(entry.record, id_field) != entry.record_id:
            raise _Failure("ALPHA_REGISTRY_INVALID")
        records[entry.record_id] = entry.record
        previous = entry.entry_hash
    head = snapshot.head_entry_hash
    if head is None or head != previous:
        raise _Failure("ALPHA_REGISTRY_INVALID")
    try:
        _prefixed(head, _ALPHA_REGISTRY_ENTRY_PREFIX)
    except _Failure:
        raise _Failure("ALPHA_REGISTRY_INVALID") from None

    candidate = records.get(candidate_id)
    family = records.get(family_id)
    episode = records.get(episode_id)
    if (
        type(candidate) is not OpportunityCandidate
        or type(family) is not HypothesisFamily
        or type(episode) is not ResearchEpisode
    ):
        raise _Failure("ALPHA_LINEAGE_INVALID")
    _recheck_alpha(candidate)
    _recheck_alpha(family)
    if episode.candidate_id != candidate_id or episode.hypothesis_family_id != family_id:
        raise _Failure("ALPHA_LINEAGE_INVALID")

    all_episodes = [r for r in records.values() if type(r) is ResearchEpisode]
    lineage = [
        e for e in all_episodes
        if e.candidate_id == candidate_id and e.hypothesis_family_id == family_id
    ]
    lineage_ids = {e.research_episode_id for e in lineage}
    for item in lineage:
        _recheck_alpha(item)
    # Current Alpha convention: an episode is non-leaf when a later episode names it as
    # predecessor or reopened episode. Any reference into this lineage from another
    # candidate/family lineage is cross-family lineage and rejects.
    parent_ids: set[str] = set()
    for item in all_episodes:
        for ref in (item.predecessor_episode_id, item.reopened_episode_id):
            if ref is None:
                continue
            if (ref in lineage_ids) != (item.research_episode_id in lineage_ids):
                raise _Failure("ALPHA_LINEAGE_INVALID")
            if ref in lineage_ids:
                parent_ids.add(ref)
    leaves = [e for e in lineage if e.research_episode_id not in parent_ids]
    if len(leaves) != 1 or leaves[0].research_episode_id != episode_id:
        raise _Failure("ALPHA_CURRENT_LEAF_INVALID")
    if leaves[0].result_state != "RESEARCH_SUPPORTIVE":
        raise _Failure("ALPHA_RESULT_STATE_INVALID")
    return head, leaves[0]


def _af1_receipt(receipt: object) -> str:
    if type(receipt) is not AF1GateReceipt:
        raise _Failure("AF1_RECEIPT_INVALID")
    try:
        validate_af1_record(receipt)
    except Exception:
        raise _Failure("AF1_RECEIPT_INVALID") from None
    statuses = receipt.dimension_statuses
    names = [name for name, _status in statuses]
    if len(names) != len(AF1_DIMENSIONS) or set(names) != set(AF1_DIMENSIONS):
        raise _Failure("AF1_RECEIPT_INVALID")
    if (
        receipt.overall_disposition != "AF1_PASS"
        or receipt.evidence_state != "FINALIZED"
        or any(status != "PASS" for _name, status in statuses)
    ):
        raise _Failure("AF1_NOT_PASS")
    return receipt.gate_receipt_id


def _provenance(manifests: object) -> tuple[list[ResearchProvenanceManifest], list[str]]:
    if isinstance(manifests, (str, bytes)) or not isinstance(manifests, (list, tuple)):
        raise _Failure("PROVENANCE_INVALID")
    if not manifests:
        raise _Failure("PROVENANCE_INVALID")
    if len(manifests) > MAX_QUALIFICATION_PROVENANCE_MANIFESTS:
        raise _Failure("LIMIT_EXCEEDED")
    for manifest in manifests:
        if type(manifest) is not ResearchProvenanceManifest:
            raise _Failure("PROVENANCE_INVALID")
        try:
            verified = verify_research_provenance_manifest_identity(manifest)
            if (
                not verified
                or manifest.schema_id != RESEARCH_PROVENANCE_MANIFEST_SCHEMA_ID
                or manifest.schema_version != RESEARCH_PROVENANCE_MANIFEST_SCHEMA_VERSION
                or canonicalize_utc_timestamp(manifest.information_cutoff)
                != manifest.information_cutoff
            ):
                raise _Failure("PROVENANCE_INVALID")
            _prefixed(manifest.research_provenance_manifest_id, _PROVENANCE_MANIFEST_PREFIX)
        except Exception:
            raise _Failure("PROVENANCE_INVALID") from None
    ids = sorted({m.research_provenance_manifest_id for m in manifests})
    return list(manifests), ids


def _cutoff_not_after(value: str, cutoff: str) -> bool:
    # Manifest cutoffs may carry up to 9 canonical fraction digits.
    return _utc_key(value) <= _utc_key(cutoff)


_INPUT_KEYS = frozenset({
    "candidate_version", "alpha_candidate_id", "hypothesis_family_id",
    "governing_research_episode_id", "information_cutoff", "qualification_mode",
    "hypothesis_plan", "feature_plan", "label_plan", "dataset_split_plan",
    "sample_power_plan", "test_family_plan", "forecast_evaluation_plan",
    "execution_feasibility_plan", "wallet_dependency", "creation_provenance",
})


def _build(
    alpha_registry_snapshot: object, af1_gate_receipt: object,
    provenance_manifests: object, input_mapping: object,
) -> QualificationCandidate:
    raw = _mapping(input_mapping, _INPUT_KEYS)
    _scan_input(raw, 0, [0])
    wallet = _enum(raw["wallet_dependency"], WALLET_DEPENDENCY_MODES)
    if wallet != "NON_WALLET":
        # No wallet-gate receipt contract exists yet: no placeholder, no bypass.
        raise _Failure("WALLET_GATE_REQUIRED")
    candidate_version = _opaque(raw["candidate_version"])
    candidate_id = _prefixed(raw["alpha_candidate_id"], _ALPHA_CANDIDATE_PREFIX)
    family_id = _prefixed(raw["hypothesis_family_id"], _ALPHA_FAMILY_PREFIX)
    episode_id = _prefixed(raw["governing_research_episode_id"], _ALPHA_EPISODE_PREFIX)
    mode = _enum(raw["qualification_mode"], QUALIFICATION_MODES)
    creation_provenance = _text(raw["creation_provenance"])

    head, leaf = _alpha_lineage(alpha_registry_snapshot, candidate_id, family_id, episode_id)
    af1_id = _af1_receipt(af1_gate_receipt)
    manifests, manifest_ids = _provenance(provenance_manifests)

    try:
        cutoff = _utc(raw["information_cutoff"])
    except _Failure:
        raise _Failure("CUTOFF_INVALID") from None
    if any(not _cutoff_not_after(m.information_cutoff, cutoff) for m in manifests):
        raise _Failure("CUTOFF_INVALID")
    if not _cutoff_not_after(leaf.research_as_of, cutoff):
        raise _Failure("CUTOFF_INVALID")

    plans = _normalize_plans(mode, raw)
    covered = {ref for manifest in manifests for ref in manifest.dataset_refs}
    split_refs = plans["dataset_split_plan"]["dataset_snapshot_reference_ids"]
    assert isinstance(split_refs, list)
    if any(ref not in covered for ref in split_refs):
        raise _Failure("PROVENANCE_INVALID")

    plan_json = {name: _plan_json(plans[name]) for name in _PLAN_NAMES}
    draft = QualificationCandidate(
        QUALIFICATION_CANDIDATE_SCHEMA_ID, QUALIFICATION_SCHEMA_VERSION, "",
        candidate_version, head, candidate_id, family_id, episode_id, af1_id,
        tuple(manifest_ids), cutoff, mode, EXPERIMENT_OS_SCHEMA_VERSION,
        plan_json["hypothesis_plan"], plan_json["feature_plan"], plan_json["label_plan"],
        plan_json["dataset_split_plan"], plan_json["sample_power_plan"],
        plan_json["test_family_plan"], plan_json["forecast_evaluation_plan"],
        plan_json["execution_feasibility_plan"], wallet, creation_provenance,
        True, True, True, True, True,
    )
    values = {field.name: getattr(draft, field.name) for field in fields(draft)}
    values["qualification_candidate_id"] = _digest(_preimage(draft))
    return _validate_record(QualificationCandidate(**values))


def build_qualification_candidate(
    alpha_registry_snapshot: object,
    af1_gate_receipt: object,
    provenance_manifests: object,
    input_mapping: object,
) -> QualificationControlResult:
    """Build the immutable non-qualifying packet from verified canonical inputs.

    No path argument, store write, clock, randomness, environment or network. The
    result never contains a qualification PASS/FAIL/INCONCLUSIVE decision.
    """
    try:
        return _valid(
            _build(alpha_registry_snapshot, af1_gate_receipt, provenance_manifests, input_mapping)
        )
    except _Failure as failure:
        return _rejected(failure.code)
    except Exception:
        return _rejected("INTERNAL_VALIDATION_FAILED")


# ── Public conversion ────────────────────────────────────────────────────────
def qualification_candidate_to_mapping(record: object) -> dict[str, object]:
    """Validate, then return the exact field mapping (tuples as lists).

    Raises ``ValueError`` whose only argument is one closed error code.
    """
    try:
        valid = _validate_record(record)
    except _Failure as failure:
        raise ValueError(failure.code) from None
    except Exception:
        raise ValueError("INTERNAL_VALIDATION_FAILED") from None
    return {
        field.name: (
            list(getattr(valid, field.name))
            if isinstance(getattr(valid, field.name), tuple)
            else getattr(valid, field.name)
        )
        for field in fields(valid)
    }


_RECORD_FIELDS = frozenset(field.name for field in fields(QualificationCandidate))


def qualification_candidate_from_mapping(mapping: object) -> QualificationControlResult:
    """Reconstruct from an exact-keyset mapping and fully re-validate it."""
    try:
        value = _mapping(mapping, _RECORD_FIELDS)
        converted = dict(value)
        ids = converted["research_provenance_manifest_ids"]
        if not isinstance(ids, list):
            raise _Failure("FIELD_TYPE_INVALID")
        converted["research_provenance_manifest_ids"] = tuple(ids)
        return _valid(_validate_record(QualificationCandidate(**converted)))
    except _Failure as failure:
        return _rejected(failure.code)
    except Exception:
        return _rejected("INTERNAL_VALIDATION_FAILED")
