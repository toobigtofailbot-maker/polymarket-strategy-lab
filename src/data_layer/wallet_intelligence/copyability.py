"""Read-only source admission and in-memory conditional wallet research (WALLET-03)."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, fields, is_dataclass, replace
from datetime import datetime, timedelta
from decimal import Decimal, localcontext
from hashlib import sha256
import json
import re

from ..point_in_time_market_research.research_provenance import (
    ObservabilityEvidence,
    RawEvidenceReference,
    ResearchProvenanceManifest,
    build_raw_evidence_reference,
    build_research_provenance_manifest,
    canonicalize_dq_flags,
    canonicalize_utc_timestamp,
    evaluate_replay_admissibility,
    validate_replay_fidelity,
)
from .contracts import WalletContractError, wallet_canonical_json_bytes
from .ledger import load_and_verify_wallet_evidence_ledger
from .profile import (
    WalletDiscoveryCohortSnapshot,
    WalletProfileError,
    WalletProfileMarketContext,
    WalletProfileSnapshot,
    build_wallet_profile_snapshot,
    wallet_discovery_cohort_from_mapping,
    wallet_discovery_cohort_to_mapping,
    wallet_profile_market_context_from_mapping,
    wallet_profile_market_context_to_mapping,
    wallet_profile_snapshot_from_mapping,
    wallet_profile_snapshot_to_mapping,
)

SCHEMA_VERSION = "1.0.0"
POLICY_VERSION = "wallet-copyability-research/1.0.0"
_MAX_EVENTS, _MAX_QUOTES, _MAX_PARAMETERS = 512, 256, 8
_ID = re.compile(r"[a-z][a-z0-9_-]*:sha256:[0-9a-f]{64}\Z")
_HASH = re.compile(r"[0-9a-f]{64}\Z")
_DECIMAL = re.compile(r"(?:0|[1-9][0-9]*)(?:\.[0-9]*[1-9])?\Z")
_EVENT_REASONS = frozenset(
    {
        "ELIGIBLE",
        "UNSUPPORTED_ACTIVITY",
        "AMBIGUOUS_IDENTITY",
        "UNSUPPORTED_INSTRUMENT",
        "MISSING_CONTEXT",
        "CONTEXT_NOT_PIT",
        "AFTER_OUTCOME",
        "PIT_NOT_ADMISSIBLE",
        "SOURCE_DISAGREEMENT",
        "REORGED_OR_REMOVED",
        "RECONCILED_DUPLICATE",
        "OUTSIDE_EVIDENCE_WINDOW",
        "DQ_NOT_OK",
        "REPLAY_NOT_ELIGIBLE",
    }
)
_QUOTE_STATES = frozenset(
    {"OBSERVED", "SCENARIO_ONLY", "PIT_NOT_ADMISSIBLE", "DQ_NOT_OK"}
)
_ERRORS = frozenset(
    {
        "COPYABILITY_FIELD_INVALID",
        "COPYABILITY_LIMIT_EXCEEDED",
        "COPYABILITY_SOURCE_INVALID",
        "COPYABILITY_PROFILE_MISMATCH",
        "COPYABILITY_SOURCE_DRIFT",
        "COPYABILITY_BINDING_INVALID",
        "COPYABILITY_SCHEMA_INVALID",
        "COPYABILITY_IDENTITY_MISMATCH",
        "COPYABILITY_RESULT_INVALID",
    }
)


class WalletCopyabilityError(ValueError):
    """Closed public codes only; source paths, content and exception text never escape."""

    def __init__(self, code: str):
        super().__init__(
            code
            if isinstance(code, str) and code in _ERRORS
            else "COPYABILITY_FIELD_INVALID"
        )


@dataclass(frozen=True)
class WalletCopyabilityCostScenario:
    """Explicit assumptions: USD per outcome share, plus required outcome shares."""

    taker_fee_per_share: str | None
    slippage_per_share: str | None
    transaction_cost_per_share: str | None
    required_depth_shares: str | None


@dataclass(frozen=True)
class WalletCopyabilityQuoteWitness:
    """Input witness, not acquisition or a new canonical source of truth."""

    condition_context: str
    condition_value: str
    token_context: str
    token_value: str
    price_direction_sign: int
    price: str
    top_level_depth_shares: str | None
    observability: ObservabilityEvidence
    dq_flags: tuple[str, ...]
    replay_fidelity: str
    raw_reference: RawEvidenceReference | None = None
    provenance_manifest: ResearchProvenanceManifest | None = None
    raw_content: bytes | None = None


@dataclass(frozen=True)
class _EventEvidence:
    wallet_event_id: str
    selected_observation_id: str | None
    instrument_key: str | None
    market_context_id: str | None
    observed_at: str | None
    outcome_bound_at: str | None
    reference_price: str | None
    price_direction_sign: int | None
    reason: str


@dataclass(frozen=True)
class _QuoteEvidence:
    witness_id: str
    instrument_key: str
    price_direction_sign: int
    price: str
    top_level_depth_shares: str | None
    observed_at: str | None
    observability_id: str
    source_status: str
    raw_reference_id: str | None
    provenance_manifest_id: str | None
    raw_content_sha256: str | None


@dataclass(frozen=True)
class _DelayResult:
    delay_seconds: str
    considered_event_count: int
    eligible_event_count: int
    excluded_reason_counts: tuple[tuple[str, int], ...]
    independently_observable_quote_count: int
    context_coverage_count: int
    outcome_reason_counts: tuple[tuple[str, int], ...]
    selected_quote_ids: tuple[tuple[str, str], ...]
    scenario_differences: tuple[tuple[str, str, str], ...]
    best_scenario_price_difference_after_costs: str | None
    worst_scenario_price_difference_after_costs: str | None
    status: str


@dataclass(frozen=True)
class WalletCopyabilityResearchAssessment:
    wallet_copyability_research_assessment_id: str
    schema_version: str
    policy_version: str
    wallet_profile_snapshot_id: str
    wallet_ledger_head_hash: str
    subject_cluster_id: str
    cohort_snapshot_id: str
    analysis_cutoff: str
    market_context_ids: tuple[str, ...]
    delay_seconds: tuple[str, ...]
    cost_scenarios: tuple[WalletCopyabilityCostScenario, ...]
    event_evidence: tuple[_EventEvidence, ...]
    quote_evidence: tuple[_QuoteEvidence, ...]
    delay_results: tuple[_DelayResult, ...]
    advisory_only: bool
    no_execution_authority: bool
    no_strategy_authority: bool
    no_qualification_authority: bool


def _mapping(value):
    if is_dataclass(value):
        return {
            field.name: _mapping(getattr(value, field.name)) for field in fields(value)
        }
    if isinstance(value, (tuple, list)):
        return [_mapping(item) for item in value]
    return value


def _identity(prefix, value):
    return (
        prefix
        + ":sha256:"
        + sha256(wallet_canonical_json_bytes(_mapping(value))).hexdigest()
    )


def _decimal(value, *, signed=False, price=False):
    if not isinstance(value, str) or len(value) > 48:
        raise WalletCopyabilityError("COPYABILITY_FIELD_INVALID")
    magnitude = value[1:] if signed and value.startswith("-") else value
    if not _DECIMAL.fullmatch(magnitude) or value == "-0":
        raise WalletCopyabilityError("COPYABILITY_FIELD_INVALID")
    result = Decimal(value)
    if result.copy_abs() > Decimal("1000000000") or result.as_tuple().exponent < -18:
        raise WalletCopyabilityError("COPYABILITY_FIELD_INVALID")
    if price and not Decimal(0) <= result <= Decimal(1):
        raise WalletCopyabilityError("COPYABILITY_FIELD_INVALID")
    return result


def _text(value):
    rendered = format(value, "f")
    rendered = rendered.rstrip("0").rstrip(".") if "." in rendered else rendered
    return "0" if value == 0 else rendered


def _time(value):
    if not isinstance(value, str) or canonicalize_utc_timestamp(value) != value:
        raise WalletCopyabilityError("COPYABILITY_FIELD_INVALID")
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _sequence(value, maximum):
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise WalletCopyabilityError("COPYABILITY_FIELD_INVALID")
    if len(value) > maximum:
        raise WalletCopyabilityError("COPYABILITY_LIMIT_EXCEEDED")
    return value


def _identifier(value, *, nullable=False, digest=False, prefix=None):
    if nullable and value is None:
        return
    if not isinstance(value, str) or not (_HASH if digest else _ID).fullmatch(value):
        raise WalletCopyabilityError("COPYABILITY_FIELD_INVALID")
    if prefix is not None and not value.startswith(prefix + ":sha256:"):
        raise WalletCopyabilityError("COPYABILITY_FIELD_INVALID")


def _observability(value):
    if type(value) is not ObservabilityEvidence:
        raise WalletCopyabilityError("COPYABILITY_FIELD_INVALID")
    for field in fields(value):
        item = getattr(value, field.name)
        if field.name.endswith("time"):
            if item is not None:
                _time(item)
        elif type(item) is not bool:
            raise WalletCopyabilityError("COPYABILITY_FIELD_INVALID")
    return value


def _clock(value):
    return value.local_first_seen_time or value.public_available_time


def _instrument(condition_context, condition_value, token_context, token_value):
    # Reuse the context-typed native identifier grammar; never join untyped IDs.
    from .contracts import canonicalize_identifier

    condition = canonicalize_identifier(condition_context, condition_value)
    token = canonicalize_identifier(token_context, token_value)
    return _identity(
        "walletinstrument", [condition_context, condition, token_context, token]
    )


def _scenarios(values):
    values = _sequence(values, _MAX_PARAMETERS)
    if not values or any(
        type(value) is not WalletCopyabilityCostScenario for value in values
    ):
        raise WalletCopyabilityError("COPYABILITY_FIELD_INVALID")
    for value in values:
        for field in fields(value):
            text = getattr(value, field.name)
            if text is not None:
                amount = _decimal(text)
                if field.name == "required_depth_shares" and amount <= 0:
                    raise WalletCopyabilityError("COPYABILITY_FIELD_INVALID")
    ordered = tuple(
        sorted(values, key=lambda item: wallet_canonical_json_bytes(_mapping(item)))
    )
    if len(set(ordered)) != len(ordered):
        raise WalletCopyabilityError("COPYABILITY_FIELD_INVALID")
    return ordered


def _delays(values):
    values = _sequence(values, _MAX_PARAMETERS)
    if not values or len(set(values)) != len(values):
        raise WalletCopyabilityError("COPYABILITY_FIELD_INVALID")
    for value in values:
        amount = _decimal(value)
        if amount > 86400 or amount.as_tuple().exponent < -6:
            raise WalletCopyabilityError("COPYABILITY_FIELD_INVALID")
    return tuple(sorted(values, key=Decimal))


def _manifest(payload):
    return build_research_provenance_manifest(
        **{
            key: value
            for key, value in payload.items()
            if key
            not in {
                "record_kind",
                "schema_id",
                "schema_version",
                "research_provenance_manifest_id",
            }
        }
    )


def _source(profile, path, expected_head, cohort, target, as_of, contexts, identities):
    _identifier(expected_head, digest=True)
    if (
        type(profile) is not WalletProfileSnapshot
        or type(cohort) is not WalletDiscoveryCohortSnapshot
    ):
        raise WalletCopyabilityError("COPYABILITY_FIELD_INVALID")
    contexts = _sequence(contexts, _MAX_EVENTS)
    if any(type(context) is not WalletProfileMarketContext for context in contexts):
        raise WalletCopyabilityError("COPYABILITY_FIELD_INVALID")
    wallet_profile_snapshot_from_mapping(wallet_profile_snapshot_to_mapping(profile))
    loaded = load_and_verify_wallet_evidence_ledger(path)
    if not loaded.is_valid or loaded.snapshot is None:
        raise WalletCopyabilityError("COPYABILITY_SOURCE_INVALID")
    if (
        loaded.snapshot.head_hash != expected_head
        or profile.wallet_ledger_head_hash != expected_head
    ):
        raise WalletCopyabilityError("COPYABILITY_SOURCE_DRIFT")
    grouped = {}
    for entry in loaded.snapshot.entries:
        grouped.setdefault(entry.record_kind, {})[entry.record_id] = entry.payload
    manifests = tuple(
        _manifest(payload)
        for payload in grouped.get("RESEARCH_PROVENANCE_MANIFEST", {}).values()
    )
    wallet_discovery_cohort_from_mapping(
        wallet_discovery_cohort_to_mapping(cohort), provenance_manifests=manifests
    )
    normalized_contexts = tuple(
        wallet_profile_market_context_from_mapping(
            wallet_profile_market_context_to_mapping(context)
        )
        for context in contexts
    )
    if len({context.wallet_profile_market_context_id for context in contexts}) != len(
        contexts
    ):
        raise WalletCopyabilityError("COPYABILITY_FIELD_INVALID")
    identities = {} if identities is None else identities
    if not isinstance(identities, Mapping) or len(identities) > _MAX_EVENTS:
        raise WalletCopyabilityError("COPYABILITY_FIELD_INVALID")
    if set(identities) - set(grouped.get("WALLET_ACCOUNT_IDENTITY_EVIDENCE", {})):
        raise WalletCopyabilityError("COPYABILITY_BINDING_INVALID")
    for evidence in identities.values():
        _observability(evidence)
    rebuilt = build_wallet_profile_snapshot(
        wallet_ledger_path=path,
        cohort_snapshot=cohort,
        target_wallet=target,
        as_of=as_of,
        market_contexts=normalized_contexts,
        identity_observability=identities,
    )
    if rebuilt != profile or wallet_profile_snapshot_to_mapping(
        rebuilt
    ) != wallet_profile_snapshot_to_mapping(profile):
        raise WalletCopyabilityError("COPYABILITY_PROFILE_MISMATCH")
    # Detect changes between the loader and canonical builder without mutable caches.
    final = load_and_verify_wallet_evidence_ledger(path)
    if not final.is_valid or final.snapshot != loaded.snapshot:
        raise WalletCopyabilityError("COPYABILITY_SOURCE_DRIFT")
    _sequence(profile.evidence_decisions, _MAX_EVENTS)
    return grouped, normalized_contexts


def _events(profile, grouped, contexts):
    by_key = {
        _instrument(
            context.condition_context,
            context.condition_value,
            context.token_context,
            context.token_value,
        ): context
        for context in contexts
        if context.wallet_profile_market_context_id
        in profile.wallet_profile_market_context_ids
    }
    events = grouped.get("WALLET_EVIDENCE_EVENT", {})
    observations = grouped.get("WALLET_EVENT_OBSERVATION", {})
    result = []
    for decision in profile.evidence_decisions:
        event = events[decision.wallet_event_id]
        observation = observations.get(decision.selected_observation_id)
        seen = (
            None
            if observation is None
            else _clock(
                ObservabilityEvidence(
                    local_first_seen_time=observation["pit"]["local_first_seen_time"],
                    public_available_time=observation["pit"]["public_available_time"],
                )
            )
        )
        key = context_id = bound = price = sign = None
        reason = "ELIGIBLE"
        if decision.disposition != "INCLUDED":
            reason = decision.reason_code
            if reason not in _EVENT_REASONS:
                raise WalletCopyabilityError("COPYABILITY_FIELD_INVALID")
        elif event["canonical_event_type"] != "TRADE_FILL" or event["side"] not in {
            "BUY",
            "SELL",
        }:
            reason = "UNSUPPORTED_ACTIVITY"
        elif event["identity_ambiguous"] or event["identity_strength"] not in {
            "API_NATIVE_STRONG",
            "CHAIN_NATIVE_STRONG",
        }:
            reason = "AMBIGUOUS_IDENTITY"
        elif event["combo_state"] != "FALSE" or event["price"] is None:
            reason = "UNSUPPORTED_INSTRUMENT"
        else:
            key = _instrument(
                event["condition_context"],
                event["condition_value"],
                event["token_context"],
                event["token_value"],
            )
            context = by_key.get(key)
            if context is None:
                reason = "MISSING_CONTEXT"
            else:
                context_id = context.wallet_profile_market_context_id
                bound = (
                    None
                    if context.resolution_observability is None
                    else _clock(context.resolution_observability)
                )
                if context.instrument_class != "STANDARD_BINARY_OUTCOME":
                    reason = "UNSUPPORTED_INSTRUMENT"
                elif (
                    seen is None
                    or evaluate_replay_admissibility(
                        seen, context.metadata_observability
                    ).status
                    != "ADMISSIBLE"
                ):
                    reason = "CONTEXT_NOT_PIT"
                elif bound is not None and _time(seen) >= _time(bound):
                    reason = "AFTER_OUTCOME"
                else:
                    _decimal(event["price"], price=True)
                    price = event["price"]
                    sign = 1 if event["side"] == "BUY" else -1
        result.append(
            _EventEvidence(
                decision.wallet_event_id,
                decision.selected_observation_id,
                key,
                context_id,
                seen,
                bound,
                price,
                sign,
                reason,
            )
        )
    return tuple(sorted(result, key=lambda item: item.wallet_event_id))


def _no_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise WalletCopyabilityError("COPYABILITY_BINDING_INVALID")
        result[key] = value
    return result


def _quote(witness, grouped, cutoff):
    if type(witness) is not WalletCopyabilityQuoteWitness:
        raise WalletCopyabilityError("COPYABILITY_FIELD_INVALID")
    if type(
        witness.price_direction_sign
    ) is not int or witness.price_direction_sign not in {-1, 1}:
        raise WalletCopyabilityError("COPYABILITY_FIELD_INVALID")
    _decimal(witness.price, price=True)
    if witness.top_level_depth_shares is not None:
        _decimal(witness.top_level_depth_shares)
    obs = _observability(witness.observability)
    flags = canonicalize_dq_flags(witness.dq_flags)
    fidelity = validate_replay_fidelity(witness.replay_fidelity)
    key = _instrument(
        witness.condition_context,
        witness.condition_value,
        witness.token_context,
        witness.token_value,
    )
    state = "SCENARIO_ONLY"
    raw_id = manifest_id = content_hash = None
    raw, manifest, content = (
        witness.raw_reference,
        witness.provenance_manifest,
        witness.raw_content,
    )
    if content is not None:
        if type(content) is not bytes or len(content) > 65536:
            raise WalletCopyabilityError("COPYABILITY_FIELD_INVALID")
        content_hash = sha256(content).hexdigest()
    if raw is not None:
        if type(raw) is not RawEvidenceReference:
            raise WalletCopyabilityError("COPYABILITY_FIELD_INVALID")
        preimage = raw.logical_preimage()
        preimage.pop("schema_id")
        preimage.pop("schema_version")
        from ..point_in_time_market_research.research_provenance import (
            build_pit_timestamps,
        )

        preimage["pit"] = build_pit_timestamps(**preimage["pit"])
        if build_raw_evidence_reference(**preimage) != raw:
            raise WalletCopyabilityError("COPYABILITY_BINDING_INVALID")
        raw_id = raw.raw_evidence_reference_id
        if content is not None and (
            raw.content_sha256 != content_hash or raw.byte_length != len(content)
        ):
            raise WalletCopyabilityError("COPYABILITY_BINDING_INVALID")
    if manifest is not None:
        if (
            type(manifest) is not ResearchProvenanceManifest
            or _manifest(_mapping(manifest)) != manifest
        ):
            raise WalletCopyabilityError("COPYABILITY_BINDING_INVALID")
        manifest_id = manifest.research_provenance_manifest_id
    if raw is not None and manifest is not None and content is not None:
        stored_raw = grouped.get("RAW_EVIDENCE_REFERENCE", {}).get(raw_id)
        stored_manifest = grouped.get("RESEARCH_PROVENANCE_MANIFEST", {}).get(
            manifest_id
        )
        raw_matches = stored_raw is not None and wallet_canonical_json_bytes(
            _mapping(raw)
        ) == wallet_canonical_json_bytes(
            {name: value for name, value in stored_raw.items() if name != "record_kind"}
        )
        manifest_matches = stored_manifest is not None and wallet_canonical_json_bytes(
            _mapping(manifest)
        ) == wallet_canonical_json_bytes(
            {
                name: value
                for name, value in stored_manifest.items()
                if name != "record_kind"
            }
        )
        bound = (
            raw_id in manifest.input_evidence_reference_ids
            and content_hash in manifest.input_content_hashes
        )
        native = (
            raw.source_system == "POLYMARKET_CLOB"
            and raw.endpoint == "/book"
            and raw.retrieval_method == "GET"
            and raw.media_type == "application/json"
        )
        if raw_matches and manifest_matches and bound and native:
            document = json.loads(content, object_pairs_hook=_no_duplicate_keys)
            if (
                not isinstance(document, dict)
                or document.get("market") != witness.condition_value
                or document.get("asset_id") != witness.token_value
            ):
                raise WalletCopyabilityError("COPYABILITY_BINDING_INVALID")
            if dict(raw.request_parameters).get("token_id") != witness.token_value:
                raise WalletCopyabilityError("COPYABILITY_BINDING_INVALID")
            if (
                raw.pit.local_first_seen_time != obs.local_first_seen_time
                or raw.pit.public_available_time != obs.public_available_time
            ):
                raise WalletCopyabilityError("COPYABILITY_BINDING_INVALID")
            levels = document.get(
                "asks" if witness.price_direction_sign == 1 else "bids"
            )
            levels = _sequence(levels, 256)
            if not levels:
                raise WalletCopyabilityError("COPYABILITY_BINDING_INVALID")
            parsed = []
            for level in levels:
                if not isinstance(level, dict) or set(level) != {"price", "size"}:
                    raise WalletCopyabilityError("COPYABILITY_BINDING_INVALID")
                parsed.append(
                    (_decimal(level["price"], price=True), _decimal(level["size"]))
                )
            top = (min if witness.price_direction_sign == 1 else max)(
                price for price, _ in parsed
            )
            with localcontext() as precision:
                precision.prec = 80
                depth = sum(
                    (size for price, size in parsed if price == top), Decimal(0)
                )
            if _decimal(witness.price) != top or (
                witness.top_level_depth_shares is not None
                and _decimal(witness.top_level_depth_shares) != depth
            ):
                raise WalletCopyabilityError("COPYABILITY_BINDING_INVALID")
            state = "OBSERVED"
            if (
                raw.dq_flags != ("OK",)
                or manifest.dq_flags != ("OK",)
                or raw.replay_fidelity not in {"EXACT", "FAITHFUL"}
                or manifest.replay_fidelity not in {"EXACT", "FAITHFUL"}
            ):
                state = "DQ_NOT_OK"
    seen = _clock(obs)
    if (
        evaluate_replay_admissibility(cutoff, obs).status != "ADMISSIBLE"
        or obs.source_unavailable
        or obs.is_backfilled
        or not obs.persisted
    ):
        state = "PIT_NOT_ADMISSIBLE"
    elif flags != ("OK",) or fidelity not in {"EXACT", "FAITHFUL"}:
        state = "DQ_NOT_OK"
    if manifest is not None and (
        seen is None or _time(manifest.information_cutoff) > _time(seen)
    ):
        state = "PIT_NOT_ADMISSIBLE"
    if (
        raw is not None
        and raw.pit.ingestion_time is not None
        and _time(raw.pit.ingestion_time) > _time(cutoff)
    ):
        state = "PIT_NOT_ADMISSIBLE"
    if raw is not None and (
        raw.pit.resolution_time is not None
        or (
            raw.pit.correction_or_revision_time is not None
            and (
                seen is None or _time(raw.pit.correction_or_revision_time) > _time(seen)
            )
        )
    ):
        state = "PIT_NOT_ADMISSIBLE"
    draft = _QuoteEvidence(
        "",
        key,
        witness.price_direction_sign,
        witness.price,
        witness.top_level_depth_shares,
        seen,
        _identity("walletobservability", obs),
        state,
        raw_id,
        manifest_id,
        content_hash,
    )
    return replace(
        draft,
        witness_id=_identity("walletquote", _mapping(draft) | {"witness_id": None}),
    )


def _results(events, quotes, delays, scenarios):
    excluded = tuple(
        sorted(
            Counter(
                event.reason for event in events if event.reason != "ELIGIBLE"
            ).items()
        )
    )
    eligible = [event for event in events if event.reason == "ELIGIBLE"]
    results = []
    with localcontext() as precision:
        precision.prec = 80
        for delay in delays:
            selected, differences, outcomes = [], [], Counter()
            observed_quote_ids = set()
            for event in eligible:
                threshold = _time(event.observed_at) + timedelta(
                    microseconds=int(Decimal(delay) * 1000000)
                )
                candidates = [
                    quote
                    for quote in quotes
                    if quote.instrument_key == event.instrument_key
                    and quote.price_direction_sign == event.price_direction_sign
                    and quote.observed_at is not None
                    and _time(quote.observed_at) >= threshold
                    and quote.source_status in {"OBSERVED", "SCENARIO_ONLY"}
                    and (
                        event.outcome_bound_at is None
                        or _time(quote.observed_at) < _time(event.outcome_bound_at)
                    )
                ]
                if not candidates:
                    outcomes["NO_ADMISSIBLE_QUOTE"] += 1
                    continue
                # Earliest captured quote, not the most favorable price. Independent
                # conflicting quotes at the same time cannot be silently selected.
                earliest = min(_time(quote.observed_at) for quote in candidates)
                first = [
                    quote
                    for quote in candidates
                    if _time(quote.observed_at) == earliest
                ]
                if (
                    len(
                        {(quote.price, quote.top_level_depth_shares) for quote in first}
                    )
                    != 1
                ):
                    outcomes["CONTRADICTORY_QUOTES"] += 1
                    continue
                quote = min(
                    first,
                    key=lambda item: (
                        item.source_status != "OBSERVED",
                        item.witness_id,
                    ),
                )
                selected.append((event.wallet_event_id, quote.witness_id))
                if quote.source_status == "OBSERVED":
                    observed_quote_ids.add(quote.witness_id)
                if any(
                    any(
                        getattr(scenario, field.name) is None
                        for field in fields(scenario)
                    )
                    for scenario in scenarios
                ):
                    outcomes["MISSING_COST_ASSUMPTION"] += 1
                elif quote.top_level_depth_shares is None:
                    outcomes["MISSING_DEPTH"] += 1
                elif any(
                    Decimal(quote.top_level_depth_shares)
                    < Decimal(scenario.required_depth_shares)
                    for scenario in scenarios
                ):
                    outcomes["INSUFFICIENT_DEPTH"] += 1
                else:
                    outcomes[quote.source_status] += 1
                    for scenario in scenarios:
                        cost = sum(
                            (
                                Decimal(scenario.taker_fee_per_share),
                                Decimal(scenario.slippage_per_share),
                                Decimal(scenario.transaction_cost_per_share),
                            ),
                            Decimal(0),
                        )
                        difference = (
                            Decimal(event.reference_price) - Decimal(quote.price)
                        ) * event.price_direction_sign - cost
                        differences.append(
                            (
                                event.wallet_event_id,
                                _identity("walletcostscenario", scenario),
                                _text(difference),
                            )
                        )
            if not eligible:
                status = "INSUFFICIENT_CONTEXT"
            elif outcomes["NO_ADMISSIBLE_QUOTE"] == len(eligible):
                status = "UNOBSERVABLE"
            elif set(outcomes) <= {"OBSERVED", "SCENARIO_ONLY"}:
                status = (
                    "SCENARIO_ONLY"
                    if outcomes["SCENARIO_ONLY"]
                    else "OBSERVABLE_CONDITIONAL"
                )
            else:
                status = "INSUFFICIENT_CONTEXT"
            values = [Decimal(item[2]) for item in differences]
            results.append(
                _DelayResult(
                    delay,
                    len(events),
                    len(eligible),
                    excluded,
                    len(observed_quote_ids),
                    sum(event.market_context_id is not None for event in events),
                    tuple(sorted(outcomes.items())),
                    tuple(selected),
                    tuple(differences),
                    _text(max(values)) if values else None,
                    _text(min(values)) if values else None,
                    status,
                )
            )
    return tuple(results)


def build_wallet_copyability_research_assessment(
    *,
    profile: WalletProfileSnapshot,
    wallet_ledger_path: object,
    expected_ledger_head: str,
    cohort_snapshot: WalletDiscoveryCohortSnapshot,
    target_wallet: str,
    as_of: str,
    market_contexts: Sequence[WalletProfileMarketContext],
    quote_witnesses: Sequence[WalletCopyabilityQuoteWitness],
    delay_seconds: Sequence[str],
    cost_scenarios: Sequence[WalletCopyabilityCostScenario],
    identity_observability: Mapping[str, ObservabilityEvidence] | None = None,
) -> WalletCopyabilityResearchAssessment:
    """Verify original sources read-only, then calculate conditional research in memory."""
    try:
        _time(as_of)
        delays, scenarios = _delays(delay_seconds), _scenarios(cost_scenarios)
        witnesses = _sequence(quote_witnesses, _MAX_QUOTES)
        grouped, contexts = _source(
            profile,
            wallet_ledger_path,
            expected_ledger_head,
            cohort_snapshot,
            target_wallet,
            as_of,
            market_contexts,
            identity_observability,
        )
        events = _events(profile, grouped, contexts)
        quotes = tuple(
            sorted(
                (_quote(witness, grouped, as_of) for witness in witnesses),
                key=lambda item: item.witness_id,
            )
        )
        if len({quote.witness_id for quote in quotes}) != len(quotes) or len(
            {
                quote.raw_reference_id
                for quote in quotes
                if quote.raw_reference_id is not None
            }
        ) != sum(quote.raw_reference_id is not None for quote in quotes):
            raise WalletCopyabilityError("COPYABILITY_BINDING_INVALID")
        draft = WalletCopyabilityResearchAssessment(
            "",
            SCHEMA_VERSION,
            POLICY_VERSION,
            profile.wallet_profile_snapshot_id,
            expected_ledger_head,
            profile.subject_cluster_id,
            profile.cohort_snapshot_id,
            as_of,
            tuple(
                sorted(context.wallet_profile_market_context_id for context in contexts)
            ),
            delays,
            scenarios,
            events,
            quotes,
            _results(events, quotes, delays, scenarios),
            True,
            True,
            True,
            True,
        )
        preimage = _mapping(draft)
        preimage.pop("wallet_copyability_research_assessment_id")
        result = replace(
            draft,
            wallet_copyability_research_assessment_id=_identity(
                "walletcopyability", preimage
            ),
        )
        return wallet_copyability_research_assessment_from_mapping(_mapping(result))
    except WalletCopyabilityError:
        raise
    except (
        ValueError,
        TypeError,
        KeyError,
        AttributeError,
        OverflowError,
        WalletContractError,
        WalletProfileError,
    ):
        raise WalletCopyabilityError("COPYABILITY_FIELD_INVALID") from None


def _strict(value, cls):
    if not isinstance(value, Mapping) or set(value) != {
        field.name for field in fields(cls)
    }:
        raise WalletCopyabilityError("COPYABILITY_SCHEMA_INVALID")
    return value


def wallet_copyability_research_assessment_to_mapping(
    value: WalletCopyabilityResearchAssessment,
) -> dict:
    if type(value) is not WalletCopyabilityResearchAssessment:
        raise WalletCopyabilityError("COPYABILITY_FIELD_INVALID")
    mapping = _mapping(value)
    wallet_copyability_research_assessment_from_mapping(mapping)
    return mapping


def wallet_copyability_research_assessment_from_mapping(
    value: object,
) -> WalletCopyabilityResearchAssessment:
    """Check closed mapping and deterministic invariants; not source authenticity."""
    try:
        data = dict(_strict(value, WalletCopyabilityResearchAssessment))
        if (
            data["schema_version"] != SCHEMA_VERSION
            or data["policy_version"] != POLICY_VERSION
        ):
            raise WalletCopyabilityError("COPYABILITY_SCHEMA_INVALID")
        for name in (
            "advisory_only",
            "no_execution_authority",
            "no_strategy_authority",
            "no_qualification_authority",
        ):
            if data[name] is not True:
                raise WalletCopyabilityError("COPYABILITY_FIELD_INVALID")
        for name, prefix in (
            ("wallet_copyability_research_assessment_id", "walletcopyability"),
            ("wallet_profile_snapshot_id", "walletprofile"),
            ("subject_cluster_id", "walletcluster"),
            ("cohort_snapshot_id", "walletcohort"),
        ):
            _identifier(data[name], prefix=prefix)
        _identifier(data["wallet_ledger_head_hash"], digest=True)
        cutoff = data["analysis_cutoff"]
        _time(cutoff)
        contexts = tuple(_sequence(data["market_context_ids"], _MAX_EVENTS))
        for identifier in contexts:
            _identifier(identifier, prefix="walletmarketctx")
        if contexts != tuple(sorted(set(contexts))):
            raise WalletCopyabilityError("COPYABILITY_RESULT_INVALID")
        delays = _delays(data["delay_seconds"])
        scenarios = _scenarios(
            tuple(
                WalletCopyabilityCostScenario(
                    **_strict(raw, WalletCopyabilityCostScenario)
                )
                for raw in _sequence(data["cost_scenarios"], _MAX_PARAMETERS)
            )
        )
        events = tuple(
            _EventEvidence(**_strict(raw, _EventEvidence))
            for raw in _sequence(data["event_evidence"], _MAX_EVENTS)
        )
        quotes = tuple(
            _QuoteEvidence(**_strict(raw, _QuoteEvidence))
            for raw in _sequence(data["quote_evidence"], _MAX_QUOTES)
        )
        if tuple(event.wallet_event_id for event in events) != tuple(
            sorted({event.wallet_event_id for event in events})
        ):
            raise WalletCopyabilityError("COPYABILITY_RESULT_INVALID")
        for event in events:
            _identifier(event.wallet_event_id, prefix="walletevent")
            for name, prefix in (
                ("selected_observation_id", "walletobs"),
                ("instrument_key", "walletinstrument"),
                ("market_context_id", "walletmarketctx"),
            ):
                _identifier(getattr(event, name), nullable=True, prefix=prefix)
            if event.reason not in _EVENT_REASONS or (
                event.market_context_id is not None
                and event.market_context_id not in contexts
            ):
                raise WalletCopyabilityError("COPYABILITY_RESULT_INVALID")
            for at in (event.observed_at, event.outcome_bound_at):
                if at is not None:
                    _time(at)
            if event.reference_price is not None:
                _decimal(event.reference_price, price=True)
            if event.price_direction_sign is not None and (
                type(event.price_direction_sign) is not int
                or event.price_direction_sign not in {-1, 1}
            ):
                raise WalletCopyabilityError("COPYABILITY_FIELD_INVALID")
            if event.reason == "ELIGIBLE" and (
                any(
                    item is None
                    for item in (
                        event.selected_observation_id,
                        event.instrument_key,
                        event.market_context_id,
                        event.observed_at,
                        event.reference_price,
                    )
                )
                or type(event.price_direction_sign) is not int
                or event.price_direction_sign not in {-1, 1}
                or _time(event.observed_at) > _time(cutoff)
                or (
                    event.outcome_bound_at is not None
                    and _time(event.observed_at) >= _time(event.outcome_bound_at)
                )
            ):
                raise WalletCopyabilityError("COPYABILITY_RESULT_INVALID")
        if tuple(quote.witness_id for quote in quotes) != tuple(
            sorted({quote.witness_id for quote in quotes})
        ):
            raise WalletCopyabilityError("COPYABILITY_RESULT_INVALID")
        raw_ids = [
            quote.raw_reference_id
            for quote in quotes
            if quote.raw_reference_id is not None
        ]
        if len(raw_ids) != len(set(raw_ids)):
            raise WalletCopyabilityError("COPYABILITY_RESULT_INVALID")
        for quote in quotes:
            for name, prefix in (
                ("witness_id", "walletquote"),
                ("instrument_key", "walletinstrument"),
                ("observability_id", "walletobservability"),
            ):
                _identifier(getattr(quote, name), prefix=prefix)
            for name, prefix in (
                ("raw_reference_id", "rawevidence"),
                ("provenance_manifest_id", "researchmanifest"),
            ):
                _identifier(getattr(quote, name), nullable=True, prefix=prefix)
            _identifier(quote.raw_content_sha256, nullable=True, digest=True)
            _decimal(quote.price, price=True)
            if quote.top_level_depth_shares is not None:
                _decimal(quote.top_level_depth_shares)
            if (
                type(quote.price_direction_sign) is not int
                or quote.price_direction_sign not in {-1, 1}
                or quote.source_status not in _QUOTE_STATES
            ):
                raise WalletCopyabilityError("COPYABILITY_FIELD_INVALID")
            if quote.observed_at is not None:
                _time(quote.observed_at)
            if quote.source_status in {"OBSERVED", "SCENARIO_ONLY"} and (
                quote.observed_at is None or _time(quote.observed_at) > _time(cutoff)
            ):
                raise WalletCopyabilityError("COPYABILITY_RESULT_INVALID")
            if quote.source_status == "OBSERVED" and any(
                item is None
                for item in (
                    quote.raw_reference_id,
                    quote.provenance_manifest_id,
                    quote.raw_content_sha256,
                )
            ):
                raise WalletCopyabilityError("COPYABILITY_RESULT_INVALID")
            preimage = _mapping(quote) | {"witness_id": None}
            if quote.witness_id != _identity("walletquote", preimage):
                raise WalletCopyabilityError("COPYABILITY_IDENTITY_MISMATCH")
        expected_results = _results(events, quotes, delays, scenarios)
        if wallet_canonical_json_bytes(
            _mapping(expected_results)
        ) != wallet_canonical_json_bytes(data["delay_results"]):
            raise WalletCopyabilityError("COPYABILITY_RESULT_INVALID")
        data.update(
            market_context_ids=contexts,
            delay_seconds=delays,
            cost_scenarios=scenarios,
            event_evidence=events,
            quote_evidence=quotes,
            delay_results=expected_results,
        )
        result = WalletCopyabilityResearchAssessment(**data)
        preimage = _mapping(result)
        preimage.pop("wallet_copyability_research_assessment_id")
        if result.wallet_copyability_research_assessment_id != _identity(
            "walletcopyability", preimage
        ):
            raise WalletCopyabilityError("COPYABILITY_IDENTITY_MISMATCH")
        if _mapping(result) != value:
            raise WalletCopyabilityError("COPYABILITY_SCHEMA_INVALID")
        return result
    except WalletCopyabilityError:
        raise
    except (
        ValueError,
        TypeError,
        KeyError,
        AttributeError,
        OverflowError,
        WalletContractError,
    ):
        raise WalletCopyabilityError("COPYABILITY_FIELD_INVALID") from None
