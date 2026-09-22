"""Deterministic point-in-time wallet profile snapshots (S10-WALLET-02).

The module reads a verified WALLET-01 ledger and emits immutable research
evidence.  It has no persistence, network, qualification, strategy, paper, or
execution surface.  Historical action time is never used as an observability
clock; all eligibility is decided by the shared replay-admissibility contract.
"""

from __future__ import annotations

from dataclasses import dataclass, fields, replace
from decimal import Decimal, ROUND_HALF_EVEN, localcontext
import hashlib
from typing import Mapping, Sequence

from src.data_layer.point_in_time_market_research.research_provenance import (
    ObservabilityEvidence,
    ResearchProvenanceManifest,
    canonicalize_dq_flags,
    canonicalize_utc_timestamp,
    evaluate_replay_admissibility,
    validate_replay_fidelity,
    verify_research_provenance_manifest_identity,
)

from .contracts import (
    canonicalize_evm_address,
    canonicalize_identifier,
    wallet_canonical_json_bytes,
)
from .ledger import load_and_verify_wallet_evidence_ledger


WALLET_PROFILE_SCHEMA_VERSION = "1.0.0"
WALLET_PROFILE_POLICY_VERSION = "wallet-profile-policy/1.0.0"
WALLET_PROFILE_CONTEXT_POLICY_VERSION = "wallet-profile-context-policy/1.0.0"
WALLET_PROFILE_COHORT_POLICY_VERSION = "wallet-profile-cohort-policy/1.0.0"

INSTRUMENT_CLASSES = ("STANDARD_BINARY_OUTCOME", "COMBO_POSITION", "OTHER", "UNKNOWN")
DISCOVERY_METHODS = (
    "CALLER_SUPPLIED_PIT_SET",
    "PUBLIC_LEADERBOARD_CAPTURE",
    "ALPHA_RESEARCH_COHORT",
    "OTHER_VERIFIED_PUBLIC_SET",
)
COHORT_ROLES = ("CANDIDATE", "CONTROL")
SAMPLE_STRENGTH_STATUSES = (
    "KNOWN_INDEPENDENT_GROUPS",
    "UNKNOWN_INDEPENDENCE",
    "NO_ELIGIBLE_DIRECTIONAL_EVIDENCE",
)
DIRECTIONAL_SKILL_STATUSES = (
    "ESTIMATED_UNCALIBRATED",
    "INSUFFICIENT_DIRECTIONAL_EVIDENCE",
    "UNKNOWN_INDEPENDENCE",
)
SPECIALIZATION_DIMENSION_STATUSES = (
    "DESCRIPTIVE_UNCALIBRATED",
    "UNKNOWN_INDEPENDENCE",
    "UNKNOWN_CONTEXT",
)
SCOPE_KINDS = ("OVERALL", "CATEGORY", "MECHANISM", "HORIZON")
ARCHETYPE_CLASSES = (
    "DIRECTIONAL",
    "MARKET_MAKING",
    "ARBITRAGE_CONVERSION",
    "INCENTIVE_REBATE",
    "SETTLEMENT",
    "TRANSFER_CAPITAL_FLOW",
)

PROFILE_ERROR_CODES = (
    "PROFILE_FIELD_TYPE_INVALID",
    "PROFILE_FIELD_VALUE_INVALID",
    "PROFILE_SCHEMA_UNSUPPORTED",
    "PROFILE_IDENTITY_MISMATCH",
    "PROFILE_UNKNOWN_FIELD",
    "PROFILE_PIT_NOT_ADMISSIBLE",
    "PROFILE_PROVENANCE_INVALID",
    "PROFILE_LEDGER_INVALID",
    "PROFILE_COHORT_ROLE_CONFLICT",
    "PROFILE_REFERENCE_INVALID",
    "PROFILE_INTERNAL_VALIDATION_FAILED",
)

_Q18 = Decimal("0.000000000000000001")
_IDENTITY_RANK = {
    "CHAIN_NATIVE_STRONG": 0,
    "API_NATIVE_STRONG": 1,
    "SOURCE_CONTENT_DERIVED": 2,
    "WEAK_PARTIAL": 3,
}
_STRONG_RELATION_CLASSES = frozenset(("PROTOCOL_DECLARED", "ONCHAIN_CONFIRMED"))
_ARBITRAGE_EVENTS = frozenset(
    ("SPLIT", "MERGE", "CONVERSION", "COMBO_COMPRESS", "COMBO_WRAP", "COMBO_UNWRAP")
)
_INCENTIVE_EVENTS = frozenset(("REWARD", "TAKER_REBATE", "REFERRAL_REWARD", "YIELD"))
_TRANSFER_EVENTS = frozenset(("TRANSFER_IN", "TRANSFER_OUT", "DEPOSIT", "WITHDRAWAL"))


class WalletProfileError(Exception):
    """Closed, no-echo public failure for profile construction and loading."""

    def __init__(self, public_code: str) -> None:
        code = public_code if public_code in PROFILE_ERROR_CODES else "PROFILE_INTERNAL_VALIDATION_FAILED"
        self.public_code = code
        super().__init__(code)


def _fail(code: str) -> WalletProfileError:
    return WalletProfileError(code)


def _reject_float(value: object) -> None:
    if isinstance(value, float):
        raise _fail("PROFILE_FIELD_TYPE_INVALID")
    if isinstance(value, Mapping):
        for key, item in value.items():
            if not isinstance(key, str):
                raise _fail("PROFILE_FIELD_TYPE_INVALID")
            _reject_float(item)
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for item in value:
            _reject_float(item)


def _strict_keys(value: object, expected: Sequence[str]) -> Mapping[str, object]:
    _reject_float(value)
    if not isinstance(value, Mapping):
        raise _fail("PROFILE_FIELD_TYPE_INVALID")
    if set(value) != set(expected):
        raise _fail("PROFILE_UNKNOWN_FIELD" if set(value) - set(expected) else "PROFILE_FIELD_VALUE_INVALID")
    return value


def _nonempty(value: object, *, maximum: int = 512) -> str:
    if not isinstance(value, str):
        raise _fail("PROFILE_FIELD_TYPE_INVALID")
    if not value or len(value) > maximum or "\x00" in value:
        raise _fail("PROFILE_FIELD_VALUE_INVALID")
    return value


def _optional_label(value: object) -> str | None:
    if value is None:
        return None
    return _nonempty(value, maximum=128)


def _enum(value: object, allowed: Sequence[str]) -> str:
    if not isinstance(value, str):
        raise _fail("PROFILE_FIELD_TYPE_INVALID")
    if value not in allowed:
        raise _fail("PROFILE_FIELD_VALUE_INVALID")
    return value


def _strings(value: object, *, nonempty: bool = False, maximum: int = 512) -> tuple[str, ...]:
    if isinstance(value, str) or not isinstance(value, Sequence):
        raise _fail("PROFILE_FIELD_TYPE_INVALID")
    out: list[str] = []
    for item in value:
        if not isinstance(item, str) or len(item) > maximum or "\x00" in item:
            raise _fail("PROFILE_FIELD_TYPE_INVALID")
        if nonempty and not item:
            raise _fail("PROFILE_FIELD_VALUE_INVALID")
        out.append(item)
    return tuple(sorted(set(out)))


def _sequence(value: object) -> Sequence[object]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise _fail("PROFILE_FIELD_TYPE_INVALID")
    return value


def _bool_true(value: object) -> bool:
    if value is not True:
        raise _fail("PROFILE_FIELD_VALUE_INVALID")
    return True


def _timestamp(value: object) -> str:
    try:
        return canonicalize_utc_timestamp(value)
    except (TypeError, ValueError):
        raise _fail("PROFILE_FIELD_VALUE_INVALID") from None


def _dq(value: object) -> tuple[str, ...]:
    try:
        return canonicalize_dq_flags(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        raise _fail("PROFILE_FIELD_VALUE_INVALID") from None


def _fidelity(value: object) -> str:
    try:
        return validate_replay_fidelity(value)
    except (TypeError, ValueError):
        raise _fail("PROFILE_FIELD_VALUE_INVALID") from None


def _identifier(context: object, value: object) -> tuple[str, str]:
    c = _nonempty(context, maximum=64)
    try:
        return c, canonicalize_identifier(c, value)
    except (TypeError, ValueError):
        raise _fail("PROFILE_FIELD_VALUE_INVALID") from None


def _address(value: object) -> str:
    try:
        return canonicalize_evm_address(value)
    except (TypeError, ValueError):
        raise _fail("PROFILE_FIELD_VALUE_INVALID") from None


def _decimal(value: object) -> Decimal:
    if isinstance(value, bool) or isinstance(value, float):
        raise _fail("PROFILE_FIELD_TYPE_INVALID")
    try:
        result = Decimal(value) if isinstance(value, (str, int, Decimal)) else None
    except Exception:
        result = None
    if result is None or not result.is_finite():
        raise _fail("PROFILE_FIELD_VALUE_INVALID")
    return result


def _decimal_text(value: Decimal) -> str:
    with localcontext() as ctx:
        ctx.prec = 50
        quantized = value.quantize(_Q18, rounding=ROUND_HALF_EVEN)
    text = format(quantized, "f").rstrip("0").rstrip(".")
    return text if text and text != "-0" else "0"


def _identity(prefix: str, value: Mapping[str, object]) -> str:
    return prefix + hashlib.sha256(wallet_canonical_json_bytes(value)).hexdigest()


def _observability_to_mapping(value: ObservabilityEvidence) -> dict[str, object]:
    return {
        "local_first_seen_time": value.local_first_seen_time,
        "public_available_time": value.public_available_time,
        "event_time": value.event_time,
        "is_correction_after_cutoff": value.is_correction_after_cutoff,
        "is_backfilled": value.is_backfilled,
        "source_unavailable": value.source_unavailable,
        "persisted": value.persisted,
        "decisive_clock_uncertain": value.decisive_clock_uncertain,
    }


def _observability_from_mapping(value: object) -> ObservabilityEvidence:
    data = _strict_keys(value, tuple(f.name for f in fields(ObservabilityEvidence)))
    times: dict[str, str | None] = {}
    for name in ("local_first_seen_time", "public_available_time", "event_time"):
        raw = data[name]
        times[name] = None if raw is None else _timestamp(raw)
    booleans: dict[str, bool] = {}
    for name in (
        "is_correction_after_cutoff",
        "is_backfilled",
        "source_unavailable",
        "persisted",
        "decisive_clock_uncertain",
    ):
        if not isinstance(data[name], bool):
            raise _fail("PROFILE_FIELD_TYPE_INVALID")
        booleans[name] = data[name]  # type: ignore[assignment]
    return ObservabilityEvidence(**times, **booleans)


def _canonical_observability(value: object) -> ObservabilityEvidence:
    if not isinstance(value, ObservabilityEvidence):
        raise _fail("PROFILE_FIELD_TYPE_INVALID")
    return _observability_from_mapping(_observability_to_mapping(value))


@dataclass(frozen=True)
class WalletProfileMarketContext:
    wallet_profile_market_context_id: str
    schema_version: str
    context_policy_version: str
    condition_context: str
    condition_value: str
    token_context: str
    token_value: str
    instrument_class: str
    category_label: str | None
    mechanism_label: str | None
    horizon_label: str | None
    independence_group_id: str | None
    metadata_observability: ObservabilityEvidence
    metadata_dq_flags: tuple[str, ...]
    metadata_replay_fidelity: str
    resolved_token_value: str | None
    resolution_observability: ObservabilityEvidence | None
    resolution_dq_flags: tuple[str, ...]
    resolution_replay_fidelity: str | None
    research_provenance_manifest_ids: tuple[str, ...]
    advisory_only: bool
    no_execution_authority: bool
    no_strategy_authority: bool
    no_qualification_authority: bool

    def logical_preimage(self) -> dict[str, object]:
        data = wallet_profile_market_context_to_mapping(self)
        data.pop("wallet_profile_market_context_id")
        return data


@dataclass(frozen=True)
class WalletDiscoveryCohortMember:
    canonical_wallet: str
    cohort_role: str
    discovery_reason: str
    discovery_evidence_reference_ids: tuple[str, ...]
    discovery_provenance_manifest_ids: tuple[str, ...]
    discovery_observability: ObservabilityEvidence


@dataclass(frozen=True)
class WalletDiscoveryCohortSnapshot:
    wallet_discovery_cohort_snapshot_id: str
    schema_version: str
    cohort_policy_version: str
    discovery_cutoff: str
    evaluation_start: str
    evaluation_end: str
    discovery_method: str
    selection_policy_id: str
    selection_policy_version: str
    members: tuple[WalletDiscoveryCohortMember, ...]
    discovery_evidence_reference_ids: tuple[str, ...]
    discovery_provenance_manifest_ids: tuple[str, ...]
    inactive_retention_policy: str
    advisory_only: bool
    no_execution_authority: bool
    no_strategy_authority: bool
    no_qualification_authority: bool

    def logical_preimage(self) -> dict[str, object]:
        data = wallet_discovery_cohort_to_mapping(self)
        data.pop("wallet_discovery_cohort_snapshot_id")
        return data


@dataclass(frozen=True)
class ProfileEvidenceDecision:
    wallet_event_id: str
    selected_observation_id: str | None
    disposition: str
    reason_code: str
    admissibility_status: str
    admissibility_basis: str
    dq_flags: tuple[str, ...]
    replay_fidelity: str | None


@dataclass(frozen=True)
class RelatedAddressEvidence:
    wallet_account_identity_evidence_id: str
    canonical_wallet: str
    related_account: str | None
    evidence_link_class: str
    aggregation_safe: bool
    reason_code: str
    admissibility_status: str
    admissibility_basis: str


@dataclass(frozen=True)
class SampleStrengthEvidence:
    raw_trade_event_count: int
    admissible_trade_event_count: int
    eligible_directional_episode_count: int
    independent_event_group_count: int | None
    effective_sample_size_groups: int | None
    group_episode_counts: tuple[tuple[str, int], ...]
    max_group_episode_share: str | None
    group_episode_hhi: str | None
    excluded_event_count: int
    exclusion_summary: tuple[tuple[str, int], ...]
    status: str


@dataclass(frozen=True)
class DirectionalSkillEvidence:
    status: str
    success_group_count: int
    failure_group_count: int
    neutral_group_count: int
    mean_signed_entry_residual: str | None
    jeffreys_alpha: str | None
    jeffreys_beta: str | None
    jeffreys_posterior_mean: str | None
    jeffreys_posterior_variance: str | None


@dataclass(frozen=True)
class SpecializationDimensionEvidence:
    dimension: str
    status: str
    group_counts: tuple[tuple[str, int], ...]
    group_shares: tuple[tuple[str, str], ...]
    group_hhi: str | None
    dominant_label: str | None


@dataclass(frozen=True)
class SpecializationEvidence:
    dimensions: tuple[SpecializationDimensionEvidence, ...]


@dataclass(frozen=True)
class ArchetypeEvidence:
    classified_event_counts: tuple[tuple[str, int], ...]
    classified_event_shares: tuple[tuple[str, str], ...]
    unclassified_event_count: int
    resolved_archetype: str


@dataclass(frozen=True)
class ProfileScopeCell:
    scope_kind: str
    scope_value: str | None
    sample_strength: SampleStrengthEvidence
    directional_skill: DirectionalSkillEvidence


@dataclass(frozen=True)
class WalletProfileSnapshot:
    wallet_profile_snapshot_id: str
    schema_version: str
    profile_policy_version: str
    subject_cluster_id: str
    representative_wallet: str
    subject_wallets: tuple[str, ...]
    cohort_snapshot_id: str
    cohort_role: str
    as_of: str
    evidence_window_start: str
    evidence_window_end: str
    wallet_ledger_head_hash: str
    considered_wallet_event_ids: tuple[str, ...]
    included_wallet_event_ids: tuple[str, ...]
    selected_wallet_event_observation_ids: tuple[str, ...]
    evidence_decisions: tuple[ProfileEvidenceDecision, ...]
    wallet_profile_market_context_ids: tuple[str, ...]
    research_provenance_manifest_ids: tuple[str, ...]
    retained_dq_admissibility_basis: tuple[str, ...]
    related_address_evidence: tuple[RelatedAddressEvidence, ...]
    scope_cells: tuple[ProfileScopeCell, ...]
    sample_strength: SampleStrengthEvidence
    directional_skill: DirectionalSkillEvidence
    specialization: SpecializationEvidence
    archetype: ArchetypeEvidence
    advisory_only: bool
    no_execution_authority: bool
    no_strategy_authority: bool
    no_qualification_authority: bool

    def logical_preimage(self) -> dict[str, object]:
        data = wallet_profile_snapshot_to_mapping(self)
        data.pop("wallet_profile_snapshot_id")
        return data


def build_wallet_profile_market_context(
    *,
    condition_context: str,
    condition_value: object,
    token_context: str,
    token_value: object,
    instrument_class: str,
    metadata_observability: ObservabilityEvidence,
    metadata_dq_flags: Sequence[str],
    metadata_replay_fidelity: str,
    research_provenance_manifest_ids: Sequence[str],
    category_label: str | None = None,
    mechanism_label: str | None = None,
    horizon_label: str | None = None,
    independence_group_id: str | None = None,
    resolved_token_value: str | None = None,
    resolution_observability: ObservabilityEvidence | None = None,
    resolution_dq_flags: Sequence[str] = ("OK",),
    resolution_replay_fidelity: str | None = None,
    context_policy_version: str = WALLET_PROFILE_CONTEXT_POLICY_VERSION,
) -> WalletProfileMarketContext:
    condition_context, condition_value = _identifier(condition_context, condition_value)
    token_context, token_value = _identifier(token_context, token_value)
    instrument = _enum(instrument_class, INSTRUMENT_CLASSES)
    if resolved_token_value not in (None, "0", "1"):
        raise _fail("PROFILE_FIELD_VALUE_INVALID")
    resolution_obs = None if resolution_observability is None else _canonical_observability(resolution_observability)
    if resolved_token_value is None:
        if resolution_obs is not None or resolution_replay_fidelity is not None:
            raise _fail("PROFILE_FIELD_VALUE_INVALID")
    elif resolution_obs is None or resolution_replay_fidelity is None:
        raise _fail("PROFILE_FIELD_VALUE_INVALID")
    draft = WalletProfileMarketContext(
        wallet_profile_market_context_id="",
        schema_version=WALLET_PROFILE_SCHEMA_VERSION,
        context_policy_version=_nonempty(context_policy_version, maximum=128),
        condition_context=condition_context,
        condition_value=condition_value,
        token_context=token_context,
        token_value=token_value,
        instrument_class=instrument,
        category_label=_optional_label(category_label),
        mechanism_label=_optional_label(mechanism_label),
        horizon_label=_optional_label(horizon_label),
        independence_group_id=_optional_label(independence_group_id),
        metadata_observability=_canonical_observability(metadata_observability),
        metadata_dq_flags=_dq(metadata_dq_flags),
        metadata_replay_fidelity=_fidelity(metadata_replay_fidelity),
        resolved_token_value=resolved_token_value,
        resolution_observability=resolution_obs,
        resolution_dq_flags=_dq(resolution_dq_flags),
        resolution_replay_fidelity=None if resolution_replay_fidelity is None else _fidelity(resolution_replay_fidelity),
        research_provenance_manifest_ids=_strings(research_provenance_manifest_ids, nonempty=True),
        advisory_only=True,
        no_execution_authority=True,
        no_strategy_authority=True,
        no_qualification_authority=True,
    )
    return replace(draft, wallet_profile_market_context_id=_identity("walletmarketctx:sha256:", draft.logical_preimage()))


def build_wallet_discovery_cohort_snapshot(
    *,
    discovery_cutoff: str,
    evaluation_start: str,
    evaluation_end: str,
    discovery_method: str,
    selection_policy_id: str,
    selection_policy_version: str,
    members: Sequence[WalletDiscoveryCohortMember],
    provenance_manifests: Sequence[ResearchProvenanceManifest],
    cohort_policy_version: str = WALLET_PROFILE_COHORT_POLICY_VERSION,
) -> WalletDiscoveryCohortSnapshot:
    cutoff = _timestamp(discovery_cutoff)
    start = _timestamp(evaluation_start)
    end = _timestamp(evaluation_end)
    if start < cutoff or end <= start:
        raise _fail("PROFILE_FIELD_VALUE_INVALID")
    manifests: dict[str, ResearchProvenanceManifest] = {}
    for manifest in _sequence(provenance_manifests):
        if not isinstance(manifest, ResearchProvenanceManifest) or not verify_research_provenance_manifest_identity(manifest):
            raise _fail("PROFILE_PROVENANCE_INVALID")
        manifests[manifest.research_provenance_manifest_id] = manifest
    canonical: dict[str, WalletDiscoveryCohortMember] = {}
    roles: dict[str, str] = {}
    for member in _sequence(members):
        if not isinstance(member, WalletDiscoveryCohortMember):
            raise _fail("PROFILE_FIELD_TYPE_INVALID")
        wallet = _address(member.canonical_wallet)
        role = _enum(member.cohort_role, COHORT_ROLES)
        if wallet in roles and roles[wallet] != role:
            raise _fail("PROFILE_COHORT_ROLE_CONFLICT")
        obs = _canonical_observability(member.discovery_observability)
        if evaluate_replay_admissibility(cutoff, obs).status != "ADMISSIBLE":
            raise _fail("PROFILE_PIT_NOT_ADMISSIBLE")
        manifest_ids = _strings(member.discovery_provenance_manifest_ids, nonempty=True)
        for manifest_id in manifest_ids:
            manifest = manifests.get(manifest_id)
            if manifest is None or _timestamp(manifest.information_cutoff) > cutoff:
                raise _fail("PROFILE_PROVENANCE_INVALID")
        normalized = WalletDiscoveryCohortMember(
            canonical_wallet=wallet,
            cohort_role=role,
            discovery_reason=_nonempty(member.discovery_reason, maximum=128),
            discovery_evidence_reference_ids=_strings(member.discovery_evidence_reference_ids, nonempty=True),
            discovery_provenance_manifest_ids=manifest_ids,
            discovery_observability=obs,
        )
        if wallet in canonical and canonical[wallet] != normalized:
            raise _fail("PROFILE_FIELD_VALUE_INVALID")
        canonical[wallet] = normalized
        roles[wallet] = role
    ordered = tuple(sorted(canonical.values(), key=lambda item: item.canonical_wallet))
    if not ordered or not any(member.cohort_role == "CANDIDATE" for member in ordered):
        raise _fail("PROFILE_FIELD_VALUE_INVALID")
    evidence_ids = tuple(sorted({item for member in ordered for item in member.discovery_evidence_reference_ids}))
    manifest_ids = tuple(sorted({item for member in ordered for item in member.discovery_provenance_manifest_ids}))
    draft = WalletDiscoveryCohortSnapshot(
        wallet_discovery_cohort_snapshot_id="",
        schema_version=WALLET_PROFILE_SCHEMA_VERSION,
        cohort_policy_version=_nonempty(cohort_policy_version, maximum=128),
        discovery_cutoff=cutoff,
        evaluation_start=start,
        evaluation_end=end,
        discovery_method=_enum(discovery_method, DISCOVERY_METHODS),
        selection_policy_id=_nonempty(selection_policy_id, maximum=128),
        selection_policy_version=_nonempty(selection_policy_version, maximum=128),
        members=ordered,
        discovery_evidence_reference_ids=evidence_ids,
        discovery_provenance_manifest_ids=manifest_ids,
        inactive_retention_policy="RETAIN_MEMBERS_IMMUTABLY",
        advisory_only=True,
        no_execution_authority=True,
        no_strategy_authority=True,
        no_qualification_authority=True,
    )
    return replace(draft, wallet_discovery_cohort_snapshot_id=_identity("walletcohort:sha256:", draft.logical_preimage()))


def _member_to_mapping(member: WalletDiscoveryCohortMember) -> dict[str, object]:
    return {
        "canonical_wallet": member.canonical_wallet,
        "cohort_role": member.cohort_role,
        "discovery_reason": member.discovery_reason,
        "discovery_evidence_reference_ids": list(member.discovery_evidence_reference_ids),
        "discovery_provenance_manifest_ids": list(member.discovery_provenance_manifest_ids),
        "discovery_observability": _observability_to_mapping(member.discovery_observability),
    }


def wallet_profile_market_context_to_mapping(value: WalletProfileMarketContext) -> dict[str, object]:
    if not isinstance(value, WalletProfileMarketContext):
        raise _fail("PROFILE_FIELD_TYPE_INVALID")
    return {
        "wallet_profile_market_context_id": value.wallet_profile_market_context_id,
        "schema_version": value.schema_version,
        "context_policy_version": value.context_policy_version,
        "condition_context": value.condition_context,
        "condition_value": value.condition_value,
        "token_context": value.token_context,
        "token_value": value.token_value,
        "instrument_class": value.instrument_class,
        "category_label": value.category_label,
        "mechanism_label": value.mechanism_label,
        "horizon_label": value.horizon_label,
        "independence_group_id": value.independence_group_id,
        "metadata_observability": _observability_to_mapping(value.metadata_observability),
        "metadata_dq_flags": list(value.metadata_dq_flags),
        "metadata_replay_fidelity": value.metadata_replay_fidelity,
        "resolved_token_value": value.resolved_token_value,
        "resolution_observability": None if value.resolution_observability is None else _observability_to_mapping(value.resolution_observability),
        "resolution_dq_flags": list(value.resolution_dq_flags),
        "resolution_replay_fidelity": value.resolution_replay_fidelity,
        "research_provenance_manifest_ids": list(value.research_provenance_manifest_ids),
        "advisory_only": value.advisory_only,
        "no_execution_authority": value.no_execution_authority,
        "no_strategy_authority": value.no_strategy_authority,
        "no_qualification_authority": value.no_qualification_authority,
    }


def wallet_profile_market_context_from_mapping(value: object) -> WalletProfileMarketContext:
    names = tuple(f.name for f in fields(WalletProfileMarketContext))
    data = _strict_keys(value, names)
    if data["schema_version"] != WALLET_PROFILE_SCHEMA_VERSION:
        raise _fail("PROFILE_SCHEMA_UNSUPPORTED")
    for name in ("advisory_only", "no_execution_authority", "no_strategy_authority", "no_qualification_authority"):
        _bool_true(data[name])
    built = build_wallet_profile_market_context(
        condition_context=data["condition_context"],
        condition_value=data["condition_value"],
        token_context=data["token_context"],
        token_value=data["token_value"],
        instrument_class=data["instrument_class"],
        category_label=data["category_label"],
        mechanism_label=data["mechanism_label"],
        horizon_label=data["horizon_label"],
        independence_group_id=data["independence_group_id"],
        metadata_observability=_observability_from_mapping(data["metadata_observability"]),
        metadata_dq_flags=data["metadata_dq_flags"],
        metadata_replay_fidelity=data["metadata_replay_fidelity"],
        resolved_token_value=data["resolved_token_value"],
        resolution_observability=None if data["resolution_observability"] is None else _observability_from_mapping(data["resolution_observability"]),
        resolution_dq_flags=data["resolution_dq_flags"],
        resolution_replay_fidelity=data["resolution_replay_fidelity"],
        research_provenance_manifest_ids=data["research_provenance_manifest_ids"],
        context_policy_version=data["context_policy_version"],
    )
    if data["wallet_profile_market_context_id"] != built.wallet_profile_market_context_id:
        raise _fail("PROFILE_IDENTITY_MISMATCH")
    return built


def wallet_discovery_cohort_to_mapping(value: WalletDiscoveryCohortSnapshot) -> dict[str, object]:
    if not isinstance(value, WalletDiscoveryCohortSnapshot):
        raise _fail("PROFILE_FIELD_TYPE_INVALID")
    return {
        "wallet_discovery_cohort_snapshot_id": value.wallet_discovery_cohort_snapshot_id,
        "schema_version": value.schema_version,
        "cohort_policy_version": value.cohort_policy_version,
        "discovery_cutoff": value.discovery_cutoff,
        "evaluation_start": value.evaluation_start,
        "evaluation_end": value.evaluation_end,
        "discovery_method": value.discovery_method,
        "selection_policy_id": value.selection_policy_id,
        "selection_policy_version": value.selection_policy_version,
        "members": [_member_to_mapping(member) for member in value.members],
        "discovery_evidence_reference_ids": list(value.discovery_evidence_reference_ids),
        "discovery_provenance_manifest_ids": list(value.discovery_provenance_manifest_ids),
        "inactive_retention_policy": value.inactive_retention_policy,
        "advisory_only": value.advisory_only,
        "no_execution_authority": value.no_execution_authority,
        "no_strategy_authority": value.no_strategy_authority,
        "no_qualification_authority": value.no_qualification_authority,
    }


def wallet_discovery_cohort_from_mapping(
    value: object, *, provenance_manifests: Sequence[ResearchProvenanceManifest]
) -> WalletDiscoveryCohortSnapshot:
    names = tuple(f.name for f in fields(WalletDiscoveryCohortSnapshot))
    data = _strict_keys(value, names)
    if data["schema_version"] != WALLET_PROFILE_SCHEMA_VERSION:
        raise _fail("PROFILE_SCHEMA_UNSUPPORTED")
    if data["inactive_retention_policy"] != "RETAIN_MEMBERS_IMMUTABLY":
        raise _fail("PROFILE_FIELD_VALUE_INVALID")
    for name in ("advisory_only", "no_execution_authority", "no_strategy_authority", "no_qualification_authority"):
        _bool_true(data[name])
    if isinstance(data["members"], str) or not isinstance(data["members"], Sequence):
        raise _fail("PROFILE_FIELD_TYPE_INVALID")
    member_names = tuple(f.name for f in fields(WalletDiscoveryCohortMember))
    members = []
    for raw in data["members"]:
        item = _strict_keys(raw, member_names)
        members.append(WalletDiscoveryCohortMember(
            canonical_wallet=item["canonical_wallet"], cohort_role=item["cohort_role"],
            discovery_reason=item["discovery_reason"],
            discovery_evidence_reference_ids=_strings(item["discovery_evidence_reference_ids"], nonempty=True),
            discovery_provenance_manifest_ids=_strings(item["discovery_provenance_manifest_ids"], nonempty=True),
            discovery_observability=_observability_from_mapping(item["discovery_observability"]),
        ))
    built = build_wallet_discovery_cohort_snapshot(
        discovery_cutoff=data["discovery_cutoff"], evaluation_start=data["evaluation_start"], evaluation_end=data["evaluation_end"],
        discovery_method=data["discovery_method"], selection_policy_id=data["selection_policy_id"],
        selection_policy_version=data["selection_policy_version"], members=members,
        provenance_manifests=provenance_manifests, cohort_policy_version=data["cohort_policy_version"],
    )
    if data["wallet_discovery_cohort_snapshot_id"] != built.wallet_discovery_cohort_snapshot_id:
        raise _fail("PROFILE_IDENTITY_MISMATCH")
    if data["discovery_evidence_reference_ids"] != list(built.discovery_evidence_reference_ids) or data["discovery_provenance_manifest_ids"] != list(built.discovery_provenance_manifest_ids):
        raise _fail("PROFILE_FIELD_VALUE_INVALID")
    return built


def _validate_cohort_for_profile(value: WalletDiscoveryCohortSnapshot) -> None:
    if value.schema_version != WALLET_PROFILE_SCHEMA_VERSION:
        raise _fail("PROFILE_SCHEMA_UNSUPPORTED")
    if value.inactive_retention_policy != "RETAIN_MEMBERS_IMMUTABLY":
        raise _fail("PROFILE_FIELD_VALUE_INVALID")
    for flag in (
        value.advisory_only,
        value.no_execution_authority,
        value.no_strategy_authority,
        value.no_qualification_authority,
    ):
        _bool_true(flag)
    cutoff = _timestamp(value.discovery_cutoff)
    start, end = _timestamp(value.evaluation_start), _timestamp(value.evaluation_end)
    if start < cutoff or end <= start:
        raise _fail("PROFILE_FIELD_VALUE_INVALID")
    if _enum(value.discovery_method, DISCOVERY_METHODS) != value.discovery_method:
        raise _fail("PROFILE_FIELD_VALUE_INVALID")
    wallets: list[str] = []
    for member in value.members:
        wallet = _address(member.canonical_wallet)
        _enum(member.cohort_role, COHORT_ROLES)
        _nonempty(member.discovery_reason, maximum=128)
        _strings(member.discovery_evidence_reference_ids, nonempty=True)
        _strings(member.discovery_provenance_manifest_ids, nonempty=True)
        if evaluate_replay_admissibility(cutoff, _canonical_observability(member.discovery_observability)).status != "ADMISSIBLE":
            raise _fail("PROFILE_PIT_NOT_ADMISSIBLE")
        wallets.append(wallet)
    if wallets != sorted(set(wallets)) or not any(member.cohort_role == "CANDIDATE" for member in value.members):
        raise _fail("PROFILE_FIELD_VALUE_INVALID")
    expected = _identity("walletcohort:sha256:", value.logical_preimage())
    if value.wallet_discovery_cohort_snapshot_id != expected:
        raise _fail("PROFILE_IDENTITY_MISMATCH")


def _entry_maps(snapshot) -> dict[str, dict[str, dict]]:
    grouped: dict[str, dict[str, dict]] = {}
    for entry in snapshot.entries:
        grouped.setdefault(entry.record_kind, {})[entry.record_id] = entry.payload
    return grouped


def _obs_from_event_payload(payload: Mapping[str, object], cutoff: str) -> ObservabilityEvidence:
    pit = payload.get("pit")
    if not isinstance(pit, Mapping):
        raise _fail("PROFILE_LEDGER_INVALID")
    dq = payload.get("dq_flags")
    dq_values = tuple(dq) if isinstance(dq, list) else ()
    correction = pit.get("correction_or_revision_time")
    return ObservabilityEvidence(
        local_first_seen_time=pit.get("local_first_seen_time"),  # type: ignore[arg-type]
        public_available_time=pit.get("public_available_time"),  # type: ignore[arg-type]
        event_time=pit.get("event_time"),  # type: ignore[arg-type]
        is_correction_after_cutoff=isinstance(correction, str) and correction > cutoff,
        is_backfilled="BACKFILLED" in dq_values,
        source_unavailable="SOURCE_UNAVAILABLE" in dq_values,
        persisted=True,
        decisive_clock_uncertain="TIMESTAMP_UNCERTAIN" in dq_values,
    )


def _active_relation(payload: Mapping[str, object], cutoff: str) -> bool:
    start = payload.get("effective_start")
    end = payload.get("effective_end")
    return (start is None or start <= cutoff) and (end is None or cutoff <= end)


def _cluster_and_relations(
    *, target_wallet: str, cohort: WalletDiscoveryCohortSnapshot,
    identity_payloads: Mapping[str, Mapping[str, object]],
    identity_observability: Mapping[str, ObservabilityEvidence],
) -> tuple[tuple[str, ...], tuple[RelatedAddressEvidence, ...]]:
    relations: list[RelatedAddressEvidence] = []
    safe_edges: list[tuple[str, str, str]] = []
    for evidence_id, payload in sorted(identity_payloads.items()):
        wallet = payload.get("canonical_wallet")
        related = payload.get("related_account")
        link_class = payload.get("evidence_link_class")
        if not isinstance(wallet, str) or link_class is None:
            continue
        obs = identity_observability.get(evidence_id)
        if obs is None:
            status, basis = "NOT_ADMISSIBLE", "NO_OBSERVABILITY_EVIDENCE"
        else:
            result = evaluate_replay_admissibility(cohort.discovery_cutoff, _canonical_observability(obs))
            status, basis = result.status, result.basis
        safe = (
            isinstance(related, str) and link_class in _STRONG_RELATION_CLASSES and
            status == "ADMISSIBLE" and _active_relation(payload, cohort.discovery_cutoff)
        )
        reason = "AGGREGATION_SAFE" if safe else (
            "WEAK_RELATION_CLASS" if link_class not in _STRONG_RELATION_CLASSES else
            "RELATION_NOT_EFFECTIVE" if not _active_relation(payload, cohort.discovery_cutoff) else
            "RELATION_NOT_ADMISSIBLE"
        )
        relations.append(RelatedAddressEvidence(
            wallet_account_identity_evidence_id=evidence_id,
            canonical_wallet=wallet,
            related_account=related if isinstance(related, str) else None,
            evidence_link_class=str(link_class), aggregation_safe=safe, reason_code=reason,
            admissibility_status=status, admissibility_basis=basis,
        ))
        if safe:
            safe_edges.append((wallet, related, evidence_id))  # type: ignore[arg-type]
    subject = {target_wallet}
    changed = True
    while changed:
        changed = False
        for left, right, _ in safe_edges:
            if left in subject or right in subject:
                before = len(subject)
                subject.update((left, right))
                changed = changed or len(subject) != before
    roles = {member.canonical_wallet: member.cohort_role for member in cohort.members}
    cluster_roles = {roles[wallet] for wallet in subject if wallet in roles}
    if len(cluster_roles) > 1:
        raise _fail("PROFILE_COHORT_ROLE_CONFLICT")
    connected_ids = {edge_id for left, right, edge_id in safe_edges if left in subject and right in subject}
    normalized_relations = tuple(
        replace(item, aggregation_safe=item.wallet_account_identity_evidence_id in connected_ids)
        for item in relations if item.canonical_wallet in subject or item.related_account in subject
    )
    return tuple(sorted(subject)), tuple(sorted(normalized_relations, key=lambda item: item.wallet_account_identity_evidence_id))


def _sample_and_skill(
    episodes: Sequence[tuple[str, str, str, Decimal, WalletProfileMarketContext]],
    *, raw_count: int, admissible_count: int, excluded: Mapping[str, int], missing_grouping: bool,
) -> tuple[SampleStrengthEvidence, DirectionalSkillEvidence, dict[str, list[tuple[str, str, Decimal, WalletProfileMarketContext]]]]:
    by_key: dict[tuple[str, str, str], tuple[str, str, str, Decimal, WalletProfileMarketContext]] = {}
    for episode in episodes:
        event_id, event_time, condition_token, residual, context = episode
        group = context.independence_group_id
        if group is None:
            continue
        key = (group, context.condition_value, context.token_value)
        current = by_key.get(key)
        if current is None or (event_time, event_id) < (current[1], current[0]):
            by_key[key] = episode
    groups: dict[str, list[tuple[str, str, Decimal, WalletProfileMarketContext]]] = {}
    for event_id, event_time, _condition_token, residual, context in by_key.values():
        groups.setdefault(context.independence_group_id or "", []).append((event_id, event_time, residual, context))
    if missing_grouping:
        sample_status = "UNKNOWN_INDEPENDENCE"
        group_count = effective = None
    elif not groups:
        sample_status = "NO_ELIGIBLE_DIRECTIONAL_EVIDENCE"
        group_count = effective = 0
    else:
        sample_status = "KNOWN_INDEPENDENT_GROUPS"
        group_count = len(groups)
        effective = 0
    counts = tuple(sorted((group, len(items)) for group, items in groups.items()))
    total = sum(count for _, count in counts)
    max_share = hhi = None
    if total:
        shares = [Decimal(count) / Decimal(total) for _, count in counts]
        max_share = _decimal_text(max(shares))
        hhi = _decimal_text(sum((share * share for share in shares), Decimal(0)))
    successes = failures = neutral = 0
    residuals: list[Decimal] = []
    if not missing_grouping:
        for items in groups.values():
            mean = sum((item[2] for item in items), Decimal(0)) / Decimal(len(items))
            residuals.append(mean)
            if mean > 0:
                successes += 1
            elif mean < 0:
                failures += 1
            else:
                neutral += 1
        effective = successes + failures
    sample = SampleStrengthEvidence(
        raw_trade_event_count=raw_count,
        admissible_trade_event_count=admissible_count,
        eligible_directional_episode_count=len(episodes),
        independent_event_group_count=group_count,
        effective_sample_size_groups=effective,
        group_episode_counts=counts,
        max_group_episode_share=max_share,
        group_episode_hhi=hhi,
        excluded_event_count=sum(excluded.values()),
        exclusion_summary=tuple(sorted(excluded.items())),
        status=sample_status,
    )
    if missing_grouping:
        skill = DirectionalSkillEvidence("UNKNOWN_INDEPENDENCE", 0, 0, 0, None, None, None, None, None)
    elif successes + failures == 0:
        skill = DirectionalSkillEvidence("INSUFFICIENT_DIRECTIONAL_EVIDENCE", successes, failures, neutral, _decimal_text(sum(residuals, Decimal(0)) / Decimal(len(residuals))) if residuals else None, None, None, None, None)
    else:
        with localcontext() as ctx:
            ctx.prec = 50
            alpha = Decimal(successes) + Decimal("0.5")
            beta = Decimal(failures) + Decimal("0.5")
            posterior = alpha / (alpha + beta)
            variance = alpha * beta / ((alpha + beta) ** 2 * (alpha + beta + 1))
            mean_residual = sum(residuals, Decimal(0)) / Decimal(len(residuals))
        skill = DirectionalSkillEvidence(
            "ESTIMATED_UNCALIBRATED", successes, failures, neutral,
            _decimal_text(mean_residual), _decimal_text(alpha), _decimal_text(beta),
            _decimal_text(posterior), _decimal_text(variance),
        )
    return sample, skill, groups


def _dimension_evidence(
    dimension: str, groups: Mapping[str, Sequence[tuple[str, str, Decimal, WalletProfileMarketContext]]],
    *, unknown_independence: bool,
) -> SpecializationDimensionEvidence:
    if unknown_independence:
        return SpecializationDimensionEvidence(dimension, "UNKNOWN_INDEPENDENCE", (), (), None, None)
    attr = {"CATEGORY": "category_label", "MECHANISM": "mechanism_label", "HORIZON": "horizon_label"}[dimension]
    labels: list[str] = []
    for items in groups.values():
        known = {getattr(item[3], attr) for item in items if getattr(item[3], attr) is not None}
        labels.append("UNKNOWN" if not known else next(iter(known)) if len(known) == 1 else "MIXED")
    if not labels or all(label == "UNKNOWN" for label in labels):
        return SpecializationDimensionEvidence(dimension, "UNKNOWN_CONTEXT", (), (), None, None)
    counts_map = {label: labels.count(label) for label in sorted(set(labels))}
    total = Decimal(len(labels))
    shares = tuple((label, _decimal_text(Decimal(count) / total)) for label, count in counts_map.items())
    hhi = _decimal_text(sum((Decimal(count) / total) ** 2 for count in counts_map.values()))
    maximum = max(counts_map.values())
    winners = [label for label, count in counts_map.items() if count == maximum]
    return SpecializationDimensionEvidence(
        dimension, "DESCRIPTIVE_UNCALIBRATED", tuple(counts_map.items()), shares, hhi,
        winners[0] if len(winners) == 1 else None,
    )


def _archetype(classified: Sequence[str], unclassified: int) -> ArchetypeEvidence:
    counts = tuple((name, classified.count(name)) for name in ARCHETYPE_CLASSES if name in classified)
    total = sum(count for _, count in counts)
    shares = tuple((name, _decimal_text(Decimal(count) / Decimal(total))) for name, count in counts) if total else ()
    resolved = "UNKNOWN" if not counts else counts[0][0] if len(counts) == 1 else "MIXED"
    return ArchetypeEvidence(counts, shares, unclassified, resolved)


def build_wallet_profile_snapshot(
    *,
    wallet_ledger_path: object,
    cohort_snapshot: WalletDiscoveryCohortSnapshot,
    target_wallet: str,
    as_of: str,
    market_contexts: Sequence[WalletProfileMarketContext],
    identity_observability: Mapping[str, ObservabilityEvidence] | None = None,
    profile_policy_version: str = WALLET_PROFILE_POLICY_VERSION,
) -> WalletProfileSnapshot:
    if not isinstance(cohort_snapshot, WalletDiscoveryCohortSnapshot):
        raise _fail("PROFILE_FIELD_TYPE_INVALID")
    _validate_cohort_for_profile(cohort_snapshot)
    if identity_observability is None:
        identity_observability = {}
    if not isinstance(identity_observability, Mapping):
        raise _fail("PROFILE_FIELD_TYPE_INVALID")
    wallet = _address(target_wallet)
    member = next((item for item in cohort_snapshot.members if item.canonical_wallet == wallet), None)
    if member is None:
        raise _fail("PROFILE_REFERENCE_INVALID")
    cutoff = _timestamp(as_of)
    if cutoff < cohort_snapshot.evaluation_start:
        raise _fail("PROFILE_FIELD_VALUE_INVALID")
    window_end = min(cutoff, cohort_snapshot.evaluation_end)
    loaded = load_and_verify_wallet_evidence_ledger(wallet_ledger_path)
    if not loaded.is_valid or loaded.snapshot is None:
        raise _fail("PROFILE_LEDGER_INVALID")
    grouped = _entry_maps(loaded.snapshot)
    manifests = grouped.get("RESEARCH_PROVENANCE_MANIFEST", {})
    for manifest_id in cohort_snapshot.discovery_provenance_manifest_ids:
        manifest = manifests.get(manifest_id)
        if manifest is None or manifest.get("information_cutoff") > cohort_snapshot.discovery_cutoff:
            raise _fail("PROFILE_PROVENANCE_INVALID")
    context_by_key: dict[tuple[str, str, str, str], WalletProfileMarketContext] = {}
    valid_contexts: list[WalletProfileMarketContext] = []
    for context in _sequence(market_contexts):
        canonical = wallet_profile_market_context_from_mapping(wallet_profile_market_context_to_mapping(context))
        for manifest_id in canonical.research_provenance_manifest_ids:
            if manifest_id not in manifests:
                raise _fail("PROFILE_PROVENANCE_INVALID")
        metadata = evaluate_replay_admissibility(cutoff, canonical.metadata_observability)
        if metadata.status != "ADMISSIBLE" or canonical.metadata_dq_flags != ("OK",) or canonical.metadata_replay_fidelity not in ("EXACT", "FAITHFUL"):
            continue
        key = (canonical.condition_context, canonical.condition_value, canonical.token_context, canonical.token_value)
        if key in context_by_key and context_by_key[key] != canonical:
            raise _fail("PROFILE_FIELD_VALUE_INVALID")
        context_by_key[key] = canonical
        valid_contexts.append(canonical)
    identity_payloads = grouped.get("WALLET_ACCOUNT_IDENTITY_EVIDENCE", {})
    subject_wallets, relations = _cluster_and_relations(
        target_wallet=wallet, cohort=cohort_snapshot, identity_payloads=identity_payloads,
        identity_observability=identity_observability,
    )
    cluster_id = _identity("walletcluster:sha256:", {
        "subject_wallets": list(subject_wallets),
        "aggregating_relation_ids": [item.wallet_account_identity_evidence_id for item in relations if item.aggregation_safe],
    })
    events = grouped.get("WALLET_EVIDENCE_EVENT", {})
    observations = grouped.get("WALLET_EVENT_OBSERVATION", {})
    observations_by_event: dict[str, list[tuple[str, Mapping[str, object]]]] = {}
    for observation_id, payload in observations.items():
        event_id = payload.get("wallet_event_id")
        if isinstance(event_id, str):
            observations_by_event.setdefault(event_id, []).append((observation_id, payload))
    excluded_links: dict[str, str] = {}
    parent: dict[str, str] = {}
    def find(item: str) -> str:
        parent.setdefault(item, item)
        if parent[item] != item:
            parent[item] = find(parent[item])
        return parent[item]
    def union(left: str, right: str) -> None:
        a, b = find(left), find(right)
        if a != b:
            parent[max(a, b)] = min(a, b)
    supersession: dict[str, str] = {}
    for payload in grouped.get("WALLET_RECONCILIATION_LINK", {}).values():
        event_ids = payload.get("event_ids")
        ids = [item for item in event_ids if isinstance(item, str)] if isinstance(event_ids, list) else []
        state, relation = payload.get("reconciliation_state"), payload.get("relation_kind")
        if state in ("SOURCE_DISAGREEMENT", "REORGED_OR_REMOVED"):
            for event_id in ids:
                excluded_links[event_id] = str(state)
        elif relation in ("SAME_EVENT_EQUIVALENCE", "CHAIN_CONFIRMATION") and state not in ("UNRESOLVED",):
            for other in ids[1:]:
                union(ids[0], other)
        elif relation == "SUPERSESSION":
            predecessor, successor = payload.get("predecessor_event_id"), payload.get("successor_event_id")
            if isinstance(predecessor, str) and isinstance(successor, str):
                supersession[predecessor] = successor
    selected_obs: dict[str, tuple[str, Mapping[str, object], object]] = {}
    for event_id, candidates in observations_by_event.items():
        admissible = []
        for observation_id, payload in candidates:
            result = evaluate_replay_admissibility(cutoff, _obs_from_event_payload(payload, cutoff))
            if result.status == "ADMISSIBLE":
                admissible.append((observation_id, payload, result))
        if admissible:
            selected_obs[event_id] = min(admissible, key=lambda item: item[0])
    components: dict[str, list[str]] = {}
    for event_id in events:
        components.setdefault(find(event_id), []).append(event_id)
    canonical_ids: set[str] = set()
    for ids in components.values():
        available = [item for item in ids if item in selected_obs]
        if available:
            canonical_ids.add(min(available, key=lambda item: (_IDENTITY_RANK.get(str(events[item].get("identity_strength")), 99), item)))
    for predecessor, successor in supersession.items():
        if successor in selected_obs and successor not in excluded_links:
            canonical_ids.discard(predecessor)
            canonical_ids.add(successor)
        elif predecessor in selected_obs and predecessor not in excluded_links:
            canonical_ids.add(predecessor)
    decisions: list[ProfileEvidenceDecision] = []
    episodes: list[tuple[str, str, str, Decimal, WalletProfileMarketContext]] = []
    raw_trade_count = admissible_trade_count = 0
    missing_grouping = False
    exclusions: dict[str, int] = {}
    classified: list[str] = []
    unclassified = 0
    included_ids: list[str] = []
    selected_observation_ids: list[str] = []
    retained_basis: set[str] = set()
    for event_id, event in sorted(events.items()):
        if event.get("canonical_wallet") not in subject_wallets:
            continue
        event_time = event.get("event_time")
        in_window = isinstance(event_time, str) and cohort_snapshot.evaluation_start <= event_time <= window_end
        if event.get("canonical_event_type") == "TRADE_FILL" and in_window:
            raw_trade_count += 1
        selected = selected_obs.get(event_id)
        if selected is None:
            reason, status, basis, dq_flags, fidelity = "PIT_NOT_ADMISSIBLE", "NOT_ADMISSIBLE", "NO_ADMISSIBLE_OBSERVATION", (), None
        else:
            observation_id, observation, result = selected
            status, basis = result.status, result.basis
            dq_flags = tuple(observation.get("dq_flags", ()))
            fidelity = observation.get("replay_fidelity")
            retained_basis.add(basis)
            retained_basis.update(result.retained_dq_flags)
            reason = "INCLUDED_CANONICAL"
            if event_id in excluded_links:
                reason = excluded_links[event_id]
            elif event_id not in canonical_ids:
                reason = "RECONCILED_DUPLICATE"
            elif not in_window:
                reason = "OUTSIDE_EVIDENCE_WINDOW"
            elif dq_flags != ("OK",):
                reason = "DQ_NOT_OK"
            elif fidelity not in ("EXACT", "FAITHFUL"):
                reason = "REPLAY_NOT_ELIGIBLE"
        included = selected is not None and reason == "INCLUDED_CANONICAL"
        if included:
            included_ids.append(event_id)
            selected_observation_ids.append(selected[0])
            if event.get("canonical_event_type") == "TRADE_FILL":
                admissible_trade_count += 1
        else:
            exclusions[reason] = exclusions.get(reason, 0) + 1
        decisions.append(ProfileEvidenceDecision(
            wallet_event_id=event_id,
            selected_observation_id=selected[0] if selected is not None else None,
            disposition="INCLUDED" if included else "EXCLUDED",
            reason_code=reason, admissibility_status=status, admissibility_basis=basis,
            dq_flags=tuple(dq_flags), replay_fidelity=fidelity if isinstance(fidelity, str) else None,
        ))
        if not included:
            continue
        event_type = event.get("canonical_event_type")
        eligible_directional = False
        if event_type == "TRADE_FILL" and event.get("side") == "BUY":
            key = (event.get("condition_context"), event.get("condition_value"), event.get("token_context"), event.get("token_value"))
            context = context_by_key.get(key)  # type: ignore[arg-type]
            if context is not None and context.instrument_class == "STANDARD_BINARY_OUTCOME" and event.get("price") is not None and context.resolved_token_value in ("0", "1") and context.resolution_observability is not None:
                resolution = evaluate_replay_admissibility(cutoff, context.resolution_observability)
                decisive = context.resolution_observability.local_first_seen_time or context.resolution_observability.public_available_time
                if (resolution.status == "ADMISSIBLE" and context.resolution_dq_flags == ("OK",) and context.resolution_replay_fidelity in ("EXACT", "FAITHFUL") and isinstance(event_time, str) and decisive is not None and event_time < decisive):
                    price = _decimal(event.get("price"))
                    if Decimal(0) <= price <= Decimal(1):
                        if context.independence_group_id is None:
                            missing_grouping = True
                        else:
                            residual = Decimal(context.resolved_token_value) - price
                            episodes.append((event_id, event_time, f"{context.condition_value}/{context.token_value}", residual, context))
                            eligible_directional = True
        if eligible_directional:
            classified.append("DIRECTIONAL")
        elif event_type == "MAKER_REBATE":
            classified.append("MARKET_MAKING")
        elif event_type in _ARBITRAGE_EVENTS:
            classified.append("ARBITRAGE_CONVERSION")
        elif event_type in _INCENTIVE_EVENTS:
            classified.append("INCENTIVE_REBATE")
        elif event_type == "REDEEM_SETTLEMENT":
            classified.append("SETTLEMENT")
        elif event_type in _TRANSFER_EVENTS:
            classified.append("TRANSFER_CAPITAL_FLOW")
        else:
            unclassified += 1
    sample, skill, groups = _sample_and_skill(
        episodes, raw_count=raw_trade_count, admissible_count=admissible_trade_count,
        excluded=exclusions, missing_grouping=missing_grouping,
    )
    specialization = SpecializationEvidence(tuple(
        _dimension_evidence(name, groups, unknown_independence=missing_grouping)
        for name in ("CATEGORY", "MECHANISM", "HORIZON")
    ))
    cells: list[ProfileScopeCell] = [ProfileScopeCell("OVERALL", None, sample, skill)]
    if not missing_grouping:
        for scope_kind, attr in (("CATEGORY", "category_label"), ("MECHANISM", "mechanism_label"), ("HORIZON", "horizon_label")):
            labels = sorted({getattr(item[4], attr) for item in episodes if getattr(item[4], attr) is not None})
            for label in labels:
                subset = [item for item in episodes if getattr(item[4], attr) == label]
                cell_sample, cell_skill, _ = _sample_and_skill(subset, raw_count=len(subset), admissible_count=len(subset), excluded={}, missing_grouping=False)
                cells.append(ProfileScopeCell(scope_kind, label, cell_sample, cell_skill))
    used_contexts = tuple(sorted(context.wallet_profile_market_context_id for context in valid_contexts))
    provenance_ids = tuple(sorted(set(cohort_snapshot.discovery_provenance_manifest_ids).union(
        item for context in valid_contexts for item in context.research_provenance_manifest_ids
    )))
    draft = WalletProfileSnapshot(
        wallet_profile_snapshot_id="", schema_version=WALLET_PROFILE_SCHEMA_VERSION,
        profile_policy_version=_nonempty(profile_policy_version, maximum=128),
        subject_cluster_id=cluster_id, representative_wallet=min(subject_wallets), subject_wallets=subject_wallets,
        cohort_snapshot_id=cohort_snapshot.wallet_discovery_cohort_snapshot_id, cohort_role=member.cohort_role,
        as_of=cutoff, evidence_window_start=cohort_snapshot.evaluation_start, evidence_window_end=window_end,
        wallet_ledger_head_hash=loaded.snapshot.head_hash,
        considered_wallet_event_ids=tuple(item.wallet_event_id for item in decisions),
        included_wallet_event_ids=tuple(sorted(included_ids)),
        selected_wallet_event_observation_ids=tuple(sorted(selected_observation_ids)),
        evidence_decisions=tuple(decisions), wallet_profile_market_context_ids=used_contexts,
        research_provenance_manifest_ids=provenance_ids,
        retained_dq_admissibility_basis=tuple(sorted(retained_basis)), related_address_evidence=relations,
        scope_cells=tuple(cells), sample_strength=sample, directional_skill=skill,
        specialization=specialization, archetype=_archetype(classified, unclassified),
        advisory_only=True, no_execution_authority=True, no_strategy_authority=True, no_qualification_authority=True,
    )
    return replace(draft, wallet_profile_snapshot_id=_identity("walletprofile:sha256:", draft.logical_preimage()))


def _pairs_to_mapping(value: Sequence[tuple[str, object]]) -> list[list[object]]:
    return [[key, item] for key, item in value]


def _sample_to_mapping(value: SampleStrengthEvidence) -> dict[str, object]:
    return {
        "raw_trade_event_count": value.raw_trade_event_count, "admissible_trade_event_count": value.admissible_trade_event_count,
        "eligible_directional_episode_count": value.eligible_directional_episode_count,
        "independent_event_group_count": value.independent_event_group_count,
        "effective_sample_size_groups": value.effective_sample_size_groups,
        "group_episode_counts": _pairs_to_mapping(value.group_episode_counts),
        "max_group_episode_share": value.max_group_episode_share, "group_episode_hhi": value.group_episode_hhi,
        "excluded_event_count": value.excluded_event_count, "exclusion_summary": _pairs_to_mapping(value.exclusion_summary),
        "status": value.status,
    }


def _skill_to_mapping(value: DirectionalSkillEvidence) -> dict[str, object]:
    return {field.name: getattr(value, field.name) for field in fields(DirectionalSkillEvidence)}


def wallet_profile_snapshot_to_mapping(value: WalletProfileSnapshot) -> dict[str, object]:
    if not isinstance(value, WalletProfileSnapshot):
        raise _fail("PROFILE_FIELD_TYPE_INVALID")
    return {
        "wallet_profile_snapshot_id": value.wallet_profile_snapshot_id, "schema_version": value.schema_version,
        "profile_policy_version": value.profile_policy_version, "subject_cluster_id": value.subject_cluster_id,
        "representative_wallet": value.representative_wallet, "subject_wallets": list(value.subject_wallets),
        "cohort_snapshot_id": value.cohort_snapshot_id, "cohort_role": value.cohort_role, "as_of": value.as_of,
        "evidence_window_start": value.evidence_window_start, "evidence_window_end": value.evidence_window_end,
        "wallet_ledger_head_hash": value.wallet_ledger_head_hash,
        "considered_wallet_event_ids": list(value.considered_wallet_event_ids), "included_wallet_event_ids": list(value.included_wallet_event_ids),
        "selected_wallet_event_observation_ids": list(value.selected_wallet_event_observation_ids),
        "evidence_decisions": [{field.name: (list(getattr(item, field.name)) if field.name == "dq_flags" else getattr(item, field.name)) for field in fields(ProfileEvidenceDecision)} for item in value.evidence_decisions],
        "wallet_profile_market_context_ids": list(value.wallet_profile_market_context_ids),
        "research_provenance_manifest_ids": list(value.research_provenance_manifest_ids),
        "retained_dq_admissibility_basis": list(value.retained_dq_admissibility_basis),
        "related_address_evidence": [{field.name: getattr(item, field.name) for field in fields(RelatedAddressEvidence)} for item in value.related_address_evidence],
        "scope_cells": [{"scope_kind": item.scope_kind, "scope_value": item.scope_value, "sample_strength": _sample_to_mapping(item.sample_strength), "directional_skill": _skill_to_mapping(item.directional_skill)} for item in value.scope_cells],
        "sample_strength": _sample_to_mapping(value.sample_strength), "directional_skill": _skill_to_mapping(value.directional_skill),
        "specialization": {"dimensions": [{"dimension": item.dimension, "status": item.status, "group_counts": _pairs_to_mapping(item.group_counts), "group_shares": _pairs_to_mapping(item.group_shares), "group_hhi": item.group_hhi, "dominant_label": item.dominant_label} for item in value.specialization.dimensions]},
        "archetype": {"classified_event_counts": _pairs_to_mapping(value.archetype.classified_event_counts), "classified_event_shares": _pairs_to_mapping(value.archetype.classified_event_shares), "unclassified_event_count": value.archetype.unclassified_event_count, "resolved_archetype": value.archetype.resolved_archetype},
        "advisory_only": value.advisory_only, "no_execution_authority": value.no_execution_authority,
        "no_strategy_authority": value.no_strategy_authority, "no_qualification_authority": value.no_qualification_authority,
    }


def _nonnegative_int(value: object, *, nullable: bool = False) -> int | None:
    if nullable and value is None:
        return None
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise _fail("PROFILE_FIELD_TYPE_INVALID")
    return value


def _pairs(value: object, *, integers: bool) -> tuple[tuple[str, object], ...]:
    if isinstance(value, str) or not isinstance(value, Sequence):
        raise _fail("PROFILE_FIELD_TYPE_INVALID")
    out = []
    for pair in value:
        if isinstance(pair, str) or not isinstance(pair, Sequence) or len(pair) != 2 or not isinstance(pair[0], str):
            raise _fail("PROFILE_FIELD_TYPE_INVALID")
        item = _nonnegative_int(pair[1]) if integers else _decimal_text(_decimal(pair[1]))
        out.append((pair[0], item))
    if out != sorted(out) or len({key for key, _ in out}) != len(out):
        raise _fail("PROFILE_FIELD_VALUE_INVALID")
    return tuple(out)


def _sample_from_mapping(value: object) -> SampleStrengthEvidence:
    data = _strict_keys(value, tuple(f.name for f in fields(SampleStrengthEvidence)))
    return SampleStrengthEvidence(
        raw_trade_event_count=_nonnegative_int(data["raw_trade_event_count"]), admissible_trade_event_count=_nonnegative_int(data["admissible_trade_event_count"]),
        eligible_directional_episode_count=_nonnegative_int(data["eligible_directional_episode_count"]),
        independent_event_group_count=_nonnegative_int(data["independent_event_group_count"], nullable=True),
        effective_sample_size_groups=_nonnegative_int(data["effective_sample_size_groups"], nullable=True),
        group_episode_counts=_pairs(data["group_episode_counts"], integers=True),
        max_group_episode_share=None if data["max_group_episode_share"] is None else _decimal_text(_decimal(data["max_group_episode_share"])),
        group_episode_hhi=None if data["group_episode_hhi"] is None else _decimal_text(_decimal(data["group_episode_hhi"])),
        excluded_event_count=_nonnegative_int(data["excluded_event_count"]), exclusion_summary=_pairs(data["exclusion_summary"], integers=True),
        status=_enum(data["status"], SAMPLE_STRENGTH_STATUSES),
    )


def _skill_from_mapping(value: object) -> DirectionalSkillEvidence:
    data = _strict_keys(value, tuple(f.name for f in fields(DirectionalSkillEvidence)))
    decimals = {}
    for name in ("mean_signed_entry_residual", "jeffreys_alpha", "jeffreys_beta", "jeffreys_posterior_mean", "jeffreys_posterior_variance"):
        decimals[name] = None if data[name] is None else _decimal_text(_decimal(data[name]))
    return DirectionalSkillEvidence(
        status=_enum(data["status"], DIRECTIONAL_SKILL_STATUSES), success_group_count=_nonnegative_int(data["success_group_count"]),
        failure_group_count=_nonnegative_int(data["failure_group_count"]), neutral_group_count=_nonnegative_int(data["neutral_group_count"]), **decimals,
    )


def wallet_profile_snapshot_from_mapping(value: object) -> WalletProfileSnapshot:
    names = tuple(f.name for f in fields(WalletProfileSnapshot))
    data = _strict_keys(value, names)
    if data["schema_version"] != WALLET_PROFILE_SCHEMA_VERSION:
        raise _fail("PROFILE_SCHEMA_UNSUPPORTED")
    for name in ("advisory_only", "no_execution_authority", "no_strategy_authority", "no_qualification_authority"):
        _bool_true(data[name])
    decision_names = tuple(f.name for f in fields(ProfileEvidenceDecision))
    decisions = []
    for raw in _sequence(data["evidence_decisions"]):
        item = _strict_keys(raw, decision_names)
        decisions.append(ProfileEvidenceDecision(
            wallet_event_id=_nonempty(item["wallet_event_id"]), selected_observation_id=None if item["selected_observation_id"] is None else _nonempty(item["selected_observation_id"]),
            disposition=_enum(item["disposition"], ("INCLUDED", "EXCLUDED")), reason_code=_nonempty(item["reason_code"]),
            admissibility_status=_enum(item["admissibility_status"], ("ADMISSIBLE", "NOT_ADMISSIBLE", "INDETERMINATE")),
            admissibility_basis=_nonempty(item["admissibility_basis"]), dq_flags=_strings(item["dq_flags"], nonempty=True),
            replay_fidelity=None if item["replay_fidelity"] is None else _fidelity(item["replay_fidelity"]),
        ))
    relation_names = tuple(f.name for f in fields(RelatedAddressEvidence))
    relations = []
    for raw in _sequence(data["related_address_evidence"]):
        item = _strict_keys(raw, relation_names)
        if not isinstance(item["aggregation_safe"], bool):
            raise _fail("PROFILE_FIELD_TYPE_INVALID")
        relations.append(RelatedAddressEvidence(
            wallet_account_identity_evidence_id=_nonempty(item["wallet_account_identity_evidence_id"]), canonical_wallet=_address(item["canonical_wallet"]),
            related_account=None if item["related_account"] is None else _address(item["related_account"]), evidence_link_class=_nonempty(item["evidence_link_class"]),
            aggregation_safe=item["aggregation_safe"], reason_code=_nonempty(item["reason_code"]), admissibility_status=_nonempty(item["admissibility_status"]), admissibility_basis=_nonempty(item["admissibility_basis"]),
        ))
    cells = []
    for raw in _sequence(data["scope_cells"]):
        item = _strict_keys(raw, ("scope_kind", "scope_value", "sample_strength", "directional_skill"))
        cells.append(ProfileScopeCell(_enum(item["scope_kind"], SCOPE_KINDS), _optional_label(item["scope_value"]), _sample_from_mapping(item["sample_strength"]), _skill_from_mapping(item["directional_skill"])))
    spec_data = _strict_keys(data["specialization"], ("dimensions",))
    dimensions = []
    for raw in _sequence(spec_data["dimensions"]):
        item = _strict_keys(raw, tuple(f.name for f in fields(SpecializationDimensionEvidence)))
        dimensions.append(SpecializationDimensionEvidence(
            _enum(item["dimension"], ("CATEGORY", "MECHANISM", "HORIZON")), _enum(item["status"], SPECIALIZATION_DIMENSION_STATUSES),
            _pairs(item["group_counts"], integers=True), _pairs(item["group_shares"], integers=False),
            None if item["group_hhi"] is None else _decimal_text(_decimal(item["group_hhi"])), _optional_label(item["dominant_label"]),
        ))
    archetype_data = _strict_keys(data["archetype"], tuple(f.name for f in fields(ArchetypeEvidence)))
    snapshot = WalletProfileSnapshot(
        wallet_profile_snapshot_id=data["wallet_profile_snapshot_id"], schema_version=WALLET_PROFILE_SCHEMA_VERSION,
        profile_policy_version=_nonempty(data["profile_policy_version"]), subject_cluster_id=_nonempty(data["subject_cluster_id"]),
        representative_wallet=_address(data["representative_wallet"]), subject_wallets=tuple(_address(item) for item in _strings(data["subject_wallets"], nonempty=True)),
        cohort_snapshot_id=_nonempty(data["cohort_snapshot_id"]), cohort_role=_enum(data["cohort_role"], COHORT_ROLES), as_of=_timestamp(data["as_of"]),
        evidence_window_start=_timestamp(data["evidence_window_start"]), evidence_window_end=_timestamp(data["evidence_window_end"]),
        wallet_ledger_head_hash=_nonempty(data["wallet_ledger_head_hash"]), considered_wallet_event_ids=_strings(data["considered_wallet_event_ids"], nonempty=True),
        included_wallet_event_ids=_strings(data["included_wallet_event_ids"], nonempty=True), selected_wallet_event_observation_ids=_strings(data["selected_wallet_event_observation_ids"], nonempty=True),
        evidence_decisions=tuple(decisions), wallet_profile_market_context_ids=_strings(data["wallet_profile_market_context_ids"], nonempty=True),
        research_provenance_manifest_ids=_strings(data["research_provenance_manifest_ids"], nonempty=True), retained_dq_admissibility_basis=_strings(data["retained_dq_admissibility_basis"]),
        related_address_evidence=tuple(relations), scope_cells=tuple(cells), sample_strength=_sample_from_mapping(data["sample_strength"]), directional_skill=_skill_from_mapping(data["directional_skill"]),
        specialization=SpecializationEvidence(tuple(dimensions)), archetype=ArchetypeEvidence(
            _pairs(archetype_data["classified_event_counts"], integers=True), _pairs(archetype_data["classified_event_shares"], integers=False),
            _nonnegative_int(archetype_data["unclassified_event_count"]), _enum(archetype_data["resolved_archetype"], (*ARCHETYPE_CLASSES, "MIXED", "UNKNOWN")),
        ), advisory_only=True, no_execution_authority=True, no_strategy_authority=True, no_qualification_authority=True,
    )
    if not snapshot.subject_wallets or snapshot.representative_wallet != min(snapshot.subject_wallets) or snapshot.evidence_window_end < snapshot.evidence_window_start:
        raise _fail("PROFILE_FIELD_VALUE_INVALID")
    relation_ids = [item.wallet_account_identity_evidence_id for item in snapshot.related_address_evidence]
    if len(relation_ids) != len(set(relation_ids)):
        raise _fail("PROFILE_FIELD_VALUE_INVALID")
    expected_cluster = _identity("walletcluster:sha256:", {
        "subject_wallets": list(snapshot.subject_wallets),
        "aggregating_relation_ids": sorted(
            item.wallet_account_identity_evidence_id
            for item in snapshot.related_address_evidence if item.aggregation_safe
        ),
    })
    if snapshot.subject_cluster_id != expected_cluster:
        raise _fail("PROFILE_FIELD_VALUE_INVALID")
    decision_ids = tuple(item.wallet_event_id for item in snapshot.evidence_decisions)
    if decision_ids != snapshot.considered_wallet_event_ids or decision_ids != tuple(sorted(set(decision_ids))):
        raise _fail("PROFILE_FIELD_VALUE_INVALID")
    included_ids = tuple(sorted(item.wallet_event_id for item in snapshot.evidence_decisions if item.disposition == "INCLUDED"))
    observation_ids = tuple(sorted(
        item.selected_observation_id for item in snapshot.evidence_decisions
        if item.disposition == "INCLUDED" and item.selected_observation_id is not None
    ))
    if included_ids != snapshot.included_wallet_event_ids or observation_ids != snapshot.selected_wallet_event_observation_ids:
        raise _fail("PROFILE_FIELD_VALUE_INVALID")
    expected_cell_order = sorted(
        snapshot.scope_cells,
        key=lambda item: (SCOPE_KINDS.index(item.scope_kind), item.scope_value or ""),
    )
    if list(snapshot.scope_cells) != expected_cell_order or not snapshot.scope_cells:
        raise _fail("PROFILE_FIELD_VALUE_INVALID")
    overall = snapshot.scope_cells[0]
    if overall.scope_kind != "OVERALL" or overall.scope_value is not None or overall.sample_strength != snapshot.sample_strength or overall.directional_skill != snapshot.directional_skill:
        raise _fail("PROFILE_FIELD_VALUE_INVALID")
    if snapshot.sample_strength.status == "UNKNOWN_INDEPENDENCE":
        if snapshot.sample_strength.independent_event_group_count is not None or snapshot.sample_strength.effective_sample_size_groups is not None or snapshot.directional_skill.status != "UNKNOWN_INDEPENDENCE":
            raise _fail("PROFILE_FIELD_VALUE_INVALID")
    elif snapshot.sample_strength.independent_event_group_count != len(snapshot.sample_strength.group_episode_counts):
        raise _fail("PROFILE_FIELD_VALUE_INVALID")
    nonneutral = snapshot.directional_skill.success_group_count + snapshot.directional_skill.failure_group_count
    if snapshot.sample_strength.status != "UNKNOWN_INDEPENDENCE" and snapshot.sample_strength.effective_sample_size_groups != nonneutral:
        raise _fail("PROFILE_FIELD_VALUE_INVALID")
    if nonneutral:
        with localcontext() as ctx:
            ctx.prec = 50
            alpha = Decimal(snapshot.directional_skill.success_group_count) + Decimal("0.5")
            beta = Decimal(snapshot.directional_skill.failure_group_count) + Decimal("0.5")
            expected_beta = (
                _decimal_text(alpha), _decimal_text(beta),
                _decimal_text(alpha / (alpha + beta)),
                _decimal_text(alpha * beta / ((alpha + beta) ** 2 * (alpha + beta + 1))),
            )
        actual_beta = (
            snapshot.directional_skill.jeffreys_alpha,
            snapshot.directional_skill.jeffreys_beta,
            snapshot.directional_skill.jeffreys_posterior_mean,
            snapshot.directional_skill.jeffreys_posterior_variance,
        )
        if snapshot.directional_skill.status != "ESTIMATED_UNCALIBRATED" or actual_beta != expected_beta:
            raise _fail("PROFILE_FIELD_VALUE_INVALID")
    elif any(value is not None for value in (
        snapshot.directional_skill.jeffreys_alpha,
        snapshot.directional_skill.jeffreys_beta,
        snapshot.directional_skill.jeffreys_posterior_mean,
        snapshot.directional_skill.jeffreys_posterior_variance,
    )):
        raise _fail("PROFILE_FIELD_VALUE_INVALID")
    if tuple(item.dimension for item in snapshot.specialization.dimensions) != ("CATEGORY", "MECHANISM", "HORIZON"):
        raise _fail("PROFILE_FIELD_VALUE_INVALID")
    archetype_total = sum(count for _, count in snapshot.archetype.classified_event_counts)
    expected_archetype_shares = tuple(
        (name, _decimal_text(Decimal(count) / Decimal(archetype_total)))
        for name, count in snapshot.archetype.classified_event_counts
    ) if archetype_total else ()
    expected_archetype = "UNKNOWN" if not snapshot.archetype.classified_event_counts else (
        snapshot.archetype.classified_event_counts[0][0]
        if len(snapshot.archetype.classified_event_counts) == 1 else "MIXED"
    )
    if snapshot.archetype.classified_event_shares != expected_archetype_shares or snapshot.archetype.resolved_archetype != expected_archetype:
        raise _fail("PROFILE_FIELD_VALUE_INVALID")
    expected = _identity("walletprofile:sha256:", snapshot.logical_preimage())
    if snapshot.wallet_profile_snapshot_id != expected:
        raise _fail("PROFILE_IDENTITY_MISMATCH")
    return snapshot
