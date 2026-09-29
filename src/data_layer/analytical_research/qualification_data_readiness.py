"""S10-QUAL-DATA-01 weather qualification-data readiness assembly (offline, deterministic).

Candidate-specific data formation for the PR #200 NON_WALLET daily-rain Alpha lineage:
census/exclusion records, checkpoint rows, rule cohorts, label agreement, evidence and
provenance binding, factual counts, the execution-feasibility factual inventory, the B0
source-authority compatibility state and the content-addressed
``WeatherQualificationDataReadinessBundle``.

DATA FORMATION ONLY. This module never constructs a QualificationCandidate, never calls the
qualification gate, never computes a predictive metric, never chooses sample-power thresholds
and never labels third-party PendulumFlow evidence canonical PIT. It performs no network access
and writes no files. Identities are SHA-256 over canonical JSON and exclude absolute paths,
host names, wall-clock execution time, transport latency and retry timing.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Mapping, Sequence

from ..point_in_time_market_research.research_provenance import (
    RawEvidenceReference,
    ResearchProvenanceManifest,
    build_pit_timestamps,
    build_raw_evidence_reference,
    build_research_provenance_manifest,
    verify_raw_evidence_reference_identity,
    verify_research_provenance_manifest_identity,
)
from . import nws_ndfd_history as ndfd
from . import pendulumflow_v3 as v3

WP_ID = "S10-QUAL-DATA-01"
BUNDLE_SCHEMA_ID = "weather-qualification-data-readiness-bundle"
BUNDLE_SCHEMA_VERSION = "1.0.0"
DATASET_ID_PREFIX = "weatherqualdataset:sha256:"
BUNDLE_ID_PREFIX = "weatherqualbundle:sha256:"
ROW_ID_PREFIX = "weatherqualrow:sha256:"
RULE_COHORT_PREFIX = "weatherrulecohort:sha256:"
SHARD_ID_PREFIX = "weatherqualshard:sha256:"

# ── Frozen lineage ────────────────────────────────────────────────────────────

ALPHA_CANDIDATE_ID = "alphacandidate:sha256:2d1523c8086acf536ad07512e1eaffed9cb9405b65e83c87b89b40ba77ee3add"
ALPHA_FAMILY_ID = "alphafamily:sha256:136000bd56f2fc27cf490cf675ddf2715b0acfc1ee934aa5cdf2579925c208d8"
ALPHA_EPISODE_ID = "alphaepisode:sha256:2e4c0f484649930ba2677bc360070f0e9ba6ef0e09ecd23b383a32ff3b69000c"
ALPHA_REGISTRY_HEAD = "alpharegistryentry:sha256:4b9a20f7f0e931dfea7cced80a64d7a4be7ccc58e265dbb9ebde15edb2d79847"
ALPHA_REGISTRY_ROWS = 15
ALPHA_RESULT_STATE = "RESEARCH_SUPPORTIVE"
AF1_RECEIPT_ID = "af1gate:sha256:281c5e05f5e4f8e30687f232e0289b99b0719c87fab61c8b1d1d417dc0b5cbb2"

# ── Frozen corpus, checkpoints and windows ────────────────────────────────────

CORPUS_START = date(2026, 8, 18)
CORPUS_END = date(2026, 9, 26)
CHECKPOINT_A = "MARKET_OBSERVABLE_PLUS_60M_V1"
CHECKPOINT_B = "TARGET_CLIMATE_DAY_START_V1"
CHECKPOINT_IDS = (CHECKPOINT_A, CHECKPOINT_B)
CHECKPOINT_A_OFFSET = timedelta(minutes=60)
CHECKPOINT_B_MIN_OPEN = timedelta(minutes=60)
MARKET_HISTORY_LOOKBACK = timedelta(hours=24)
NDFD_VINTAGE_LOOKBACK = timedelta(hours=48)
GAMMA_OPEN_TRUST_WINDOW = timedelta(hours=24)

# ── Closed vocabularies ───────────────────────────────────────────────────────

FINALITY_POLICIES = ("FIRST_PUBLISHED_FINAL", "LATEST_BEFORE_2359_ET", "LAST_BEFORE_1400_ET")
EXECUTION_CLASSES = ("FEES", "RESOLUTION_RULES", "TICK_SIZE_MIN_ORDER")
EXECUTION_STATES = ("HISTORICALLY_EVIDENCED", "CURRENT_ONLY", "MISSING", "SOURCE_DISAGREEMENT")
_EXECUTION_RANK = {"MISSING": 0, "CURRENT_ONLY": 1, "HISTORICALLY_EVIDENCED": 2}
B0_CANONICAL = "CANONICAL_PIT_AVAILABLE"
B0_EXTERNAL_ONLY = "EXTERNAL_ONLY_REQUIRES_SEPARATE_COMPATIBILITY_DECISION"
B0_STATES = (B0_CANONICAL, B0_EXTERNAL_ONLY)
TERMINAL_READY = "QUAL_DATA_READY"
TERMINAL_INSUFFICIENT = "QUAL_DATA_INSUFFICIENT"
TERMINALS = (TERMINAL_READY, TERMINAL_INSUFFICIENT)
TERMINAL_REASONS = (
    "EVIDENCE_COMPLETE_ROWS_PRESENT",
    "NO_EVIDENCE_COMPLETE_ROW",
    "FROZEN_BUDGET_EXHAUSTED",
    "SOURCE_UNAVAILABLE",
)
SOURCE_AUTHORITY = {
    "market_history": v3.B0_SOURCE_AUTHORITY,
    "market_history_source_class": v3.SOURCE_CLASS,
    "weather": ndfd.SOURCE_CLASS,
    "rules_and_labels": "PUBLIC_VENUE_METADATA_AND_THIRD_PARTY_RESOLUTION_CAPTURE",
    "station_reference": "OFFICIAL_CURRENT_REFERENCE_METADATA_NOT_PREDICTIVE",
}
FORBIDDEN_AUTHORITY_LABELS = frozenset({"SOURCE_KIND_CANONICAL_PIT", "MARKET_PIT", "CANONICAL_PIT"})
NO_AUTHORITY_FLAGS = {
    "advisory_only": True,
    "data_formation_only": True,
    "no_qualification_candidate": True,
    "no_qualification_gate_run": True,
    "no_predictive_metric": True,
    "no_sample_power_threshold": True,
    "no_canonical_pit_claim": True,
    "no_strategy_authority": True,
    "no_paper_authority": True,
    "no_execution_authority": True,
    "no_live_authority": True,
}

MARKET_EXCLUSION_REASONS = (
    "SLUG_NOT_DAILY_RAIN_FAMILY",
    "TARGET_DATE_OUTSIDE_CORPUS",
    "V3_MARKET_IDENTITY_INCONSISTENT",
    "GAMMA_UNAVAILABLE",
    "GAMMA_V3_IDENTITY_MISMATCH",
    "RULE_STATION_MISSING",
    "RULE_STATION_AMBIGUOUS",
    "RULE_THRESHOLD_MISSING",
    "RULE_CLIMATE_DAY_MISSING",
    "RULE_SEMANTICS_UNSUPPORTED",
    "STATION_METADATA_UNAVAILABLE",
    "STATION_METADATA_INVALID",
    "STATION_OFFSET_UNDERIVABLE",
    "LABEL_GAMMA_NOT_FINAL",
    "LABEL_V3_RESOLUTION_MISSING",
    "LABEL_SOURCE_DISAGREEMENT",
    "BUDGET_EXHAUSTED_BEFORE_EVALUATION",
)
ROW_EXCLUSION_REASONS = (
    "CHECKPOINT_B_MARKET_NOT_OPEN_60M",
    "LABEL_RESOLVED_BEFORE_CHECKPOINT",
    "MARKET_HISTORY_NOT_OBSERVED_IN_LOOKBACK",
    "MARKET_HISTORY_COVERAGE_INADMISSIBLE",
    "MARKET_HISTORY_SOURCE_INVALID",
    "WEATHER_NO_ELIGIBLE_VINTAGE",
    "WEATHER_SOURCE_INVALID",
    "WEATHER_NO_OVERLAPPING_PERIOD",
    "WEATHER_VALUE_MISSING",
    "GRID_BINDING_INVALID",
    "BUDGET_EXHAUSTED_BEFORE_EVALUATION",
)

READINESS_ERROR_CODES = (
    "READINESS_INPUT_INVALID",
    "READINESS_WINDOW_INVALID",
    "READINESS_AUTHORITY_LAUNDERING",
    "READINESS_LOOK_AHEAD",
    "READINESS_COUNTS_FABRICATED",
    "READINESS_MANIFEST_NOT_READY",
    "READINESS_IDENTITY_MISMATCH",
    "READINESS_B0_CANONICAL_BINDING_UNSUPPORTED",
)


class ReadinessError(ValueError):
    """Closed, no-echo rejection. ``str(error)`` is exactly the closed code."""

    def __init__(self, code: str) -> None:
        if code not in READINESS_ERROR_CODES:
            code = "READINESS_INPUT_INVALID"
        super().__init__(code)
        self.code = code


# ── Canonical JSON and time helpers ───────────────────────────────────────────


def _check_canonical(value: object, depth: int = 0) -> None:
    if depth > 32:
        raise ReadinessError("READINESS_INPUT_INVALID")
    if value is None or isinstance(value, (bool, str)):
        return
    if isinstance(value, int):
        return
    if isinstance(value, float):
        raise ReadinessError("READINESS_INPUT_INVALID")  # floats never enter identities
    if isinstance(value, (list, tuple)):
        for item in value:
            _check_canonical(item, depth + 1)
        return
    if isinstance(value, Mapping):
        for key, item in value.items():
            if not isinstance(key, str):
                raise ReadinessError("READINESS_INPUT_INVALID")
            _check_canonical(item, depth + 1)
        return
    raise ReadinessError("READINESS_INPUT_INVALID")


def canonical_json_bytes(value: object) -> bytes:
    _check_canonical(value)
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def content_id(prefix: str, value: object) -> str:
    return prefix + hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def parse_utc(text: object) -> datetime:
    if not isinstance(text, str) or not text:
        raise ReadinessError("READINESS_INPUT_INVALID")
    candidate = text.strip().replace(" ", "T")
    if candidate.endswith("Z"):
        candidate = candidate[:-1] + "+00:00"
    if re.search(r"[+-]\d{2}$", candidate):
        candidate += ":00"
    try:
        moment = datetime.fromisoformat(candidate)
    except ValueError:
        raise ReadinessError("READINESS_INPUT_INVALID") from None
    if moment.tzinfo is None or moment.utcoffset() != timedelta(0):
        raise ReadinessError("READINESS_INPUT_INVALID")
    return moment.astimezone(timezone.utc)


def utc_text(moment: datetime) -> str:
    utc = moment.astimezone(timezone.utc)
    if utc.microsecond:
        return utc.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    return utc.strftime("%Y-%m-%dT%H:%M:%SZ")


def target_dates() -> tuple[str, ...]:
    days = (CORPUS_END - CORPUS_START).days + 1
    return tuple((CORPUS_START + timedelta(days=offset)).isoformat() for offset in range(days))


def assert_frozen_windows(market_history: timedelta, ndfd_lookback: timedelta) -> None:
    """Reject any attempt to widen (or narrow) the frozen lookback windows."""

    if market_history != MARKET_HISTORY_LOOKBACK or ndfd_lookback != NDFD_VINTAGE_LOOKBACK:
        raise ReadinessError("READINESS_WINDOW_INVALID")


# ── Checkpoints ───────────────────────────────────────────────────────────────


def gamma_open_time_if_trustworthy(gamma_start: object, v3_receive: datetime) -> datetime | None:
    """A Gamma start/open time is trustworthy only if it parses as canonical UTC and lies within
    24 hours of the v3 capture receive time of the same market."""

    if gamma_start is None:
        return None
    try:
        moment = parse_utc(gamma_start)
    except ReadinessError:
        return None
    if abs(moment - v3_receive) > GAMMA_OPEN_TRUST_WINDOW:
        return None
    return moment


def observable_time(v3_receive: datetime, gamma_open: datetime | None) -> datetime:
    return max(v3_receive, gamma_open) if gamma_open is not None else v3_receive


def checkpoint_a(v3_receive: datetime, gamma_open: datetime | None) -> datetime:
    """MARKET_OBSERVABLE_PLUS_60M_V1."""

    return observable_time(v3_receive, gamma_open) + CHECKPOINT_A_OFFSET


def checkpoint_b(target_day: date, standard_offset_minutes: int, observable: datetime) -> tuple[datetime, bool]:
    """TARGET_CLIMATE_DAY_START_V1: LST midnight of the target date; eligible only when the market
    was observably open at least 60 minutes before it."""

    start, _end = ndfd.climate_day_window(target_day, standard_offset_minutes)
    return start, observable + CHECKPOINT_B_MIN_OPEN <= start


# ── Family, rule and Gamma normalization ──────────────────────────────────────

_MONTHS = ("january", "february", "march", "april", "may", "june", "july", "august", "september",
           "october", "november", "december")
_SLUG_RE = re.compile(r"^where-will-it-rain-on-(" + "|".join(_MONTHS) + r")-(\d{1,2})-(\d{4})-([a-z0-9]+(?:-[a-z0-9]+)*)$")


def parse_rain_slug(slug: object) -> tuple[date, str] | None:
    """Target date and city slug of the exact daily-rain family, else ``None``."""

    match = _SLUG_RE.fullmatch(slug) if isinstance(slug, str) else None
    if match is None:
        return None
    month, day, year, city = match.groups()
    try:
        return date(int(year), _MONTHS.index(month) + 1, int(day)), city
    except ValueError:
        return None


@dataclass(frozen=True)
class RuleSemantics:
    station_id: str
    product: str
    threshold_inches: str
    trace_qualifies: bool
    climate_day: str
    finality_policy: str
    rule_text_sha256: str
    rule_cohort_id: str

    def to_mapping(self) -> dict[str, object]:
        return {
            "station_id": self.station_id,
            "product": self.product,
            "threshold_inches": self.threshold_inches,
            "trace_qualifies": self.trace_qualifies,
            "climate_day": self.climate_day,
            "finality_policy": self.finality_policy,
            "rule_text_sha256": self.rule_text_sha256,
            "rule_cohort_id": self.rule_cohort_id,
        }


# Each frozen finality policy is recognized by one or more alternative wordings; every pattern of
# one alternative must match. The second alternatives of LATEST_BEFORE_2359_ET and
# LAST_BEFORE_1400_ET are the observed real Gamma word orders (S10-QUAL-DATA-01-D008): the cutoff
# is stated once ("... before 11:59 PM ET ..." / "... published by 2:00 PM ET ...") and "the last
# version published before (that time|11:59 PM ET) governs" selects the latest version. No fourth
# policy exists; a rule matching zero or more than one policy stays RULE_SEMANTICS_UNSUPPORTED.
_FINALITY_PATTERNS: dict[str, tuple[tuple[str, ...], ...]] = {
    "FIRST_PUBLISHED_FINAL": (
        (
            r"\bfirst published (?:precipitation )?(?:figure|value)\b",
            r"\b(?:subsequent )?revisions or corrections\b.{0,80}\bwill not be considered\b",
        ),
    ),
    "LATEST_BEFORE_2359_ET": (
        (
            r"\b(?:latest|most recent) (?:published )?(?:precipitation )?(?:figure|value|report)\b.{0,120}\b(?:11:59 ?pm et|23:59 et)\b",
        ),
        (
            r"\bbased on the most recent cli report published for the observation date\b",
            r"\bthe last version published before 11:59 ?pm et on the day following the observation date governs\b",
        ),
    ),
    "LAST_BEFORE_1400_ET": (
        (
            r"\b(?:last|latest|most recent|final) (?:published )?(?:precipitation )?(?:figure|value|report)\b.{0,120}\b(?:2:00 ?pm et|2 ?pm et|14:00 et)\b",
        ),
        (
            r"\bresolve according to the nws daily climate report as published by 2:00 ?pm et on the day following the observation date\b",
            r"\bthe last version published before that time governs\b",
        ),
    ),
}


def parse_rule(description: object) -> RuleSemantics:
    """Parse one Gamma rule text into normalized semantics; closed ``RULE_*`` codes otherwise."""

    if not isinstance(description, str) or not description.strip():
        raise RuleExclusion("RULE_STATION_MISSING")
    text = " ".join(description.split())
    lowered = text.lower()
    stations = set(re.findall(r"\b(?:climate day for|\(CLI\) for|CLI\) for)\s+(K[A-Z0-9]{3})\b", text))
    if not stations:
        raise RuleExclusion("RULE_STATION_MISSING")
    if len(stations) != 1:
        raise RuleExclusion("RULE_STATION_AMBIGUOUS")
    if "daily climate report (cli)" not in lowered:
        raise RuleExclusion("RULE_STATION_MISSING")
    if not re.search(r"\b0\.01 inches or more\b", lowered) or "measurable precipitation" not in lowered:
        raise RuleExclusion("RULE_THRESHOLD_MISSING")
    if not re.search(r"midnight to midnight local standard time", lowered):
        raise RuleExclusion("RULE_CLIMATE_DAY_MISSING")
    trace_excluded = bool(re.search(r'trace \("t"\) does not qualify', lowered))
    matched = [
        policy for policy, alternatives in _FINALITY_PATTERNS.items()
        if any(all(re.search(pattern, lowered) for pattern in patterns) for patterns in alternatives)
    ]
    if len(matched) != 1 or not trace_excluded:
        raise RuleExclusion("RULE_SEMANTICS_UNSUPPORTED")
    semantics = {
        "product": "NWS_DAILY_CLIMATE_REPORT_CLI_PRECIPITATION_IN",
        "threshold_inches": "0.01",
        "trace_qualifies": False,
        "climate_day": "NWS_CLIMATE_DAY_MIDNIGHT_TO_MIDNIGHT_LOCAL_STANDARD_TIME",
        "finality_policy": matched[0],
    }
    return RuleSemantics(
        station_id=stations.pop(),
        product=semantics["product"],
        threshold_inches=semantics["threshold_inches"],
        trace_qualifies=False,
        climate_day=semantics["climate_day"],
        finality_policy=matched[0],
        rule_text_sha256=hashlib.sha256(description.encode("utf-8")).hexdigest(),
        # The cohort commits the normalized semantics only; the station and date are per-market
        # bindings recorded separately.
        rule_cohort_id=content_id(RULE_COHORT_PREFIX, semantics),
    )


class RuleExclusion(ValueError):
    """A closed market-level exclusion reason (not an input-contract error)."""

    def __init__(self, code: str) -> None:
        if code not in MARKET_EXCLUSION_REASONS and code not in ROW_EXCLUSION_REASONS:
            code = "RULE_SEMANTICS_UNSUPPORTED"
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class MarketCandidate:
    market_id: str
    condition_id: str
    asset_ids: tuple[str, ...]
    outcomes: tuple[str, ...]
    question: str
    slug: str
    first_received: str
    discovery_hour: str

    def to_mapping(self) -> dict[str, object]:
        return {
            "market_id": self.market_id,
            "condition_id": self.condition_id,
            "asset_ids": list(self.asset_ids),
            "outcomes": list(self.outcomes),
            "question": self.question,
            "slug": self.slug,
            "first_received": self.first_received,
            "discovery_hour": self.discovery_hour,
        }


def candidates_from_new_market(events: Sequence[v3.V3Event]) -> tuple[tuple[MarketCandidate, ...], tuple[dict[str, str], ...]]:
    """Collapse v3 ``new_market`` witness copies by market id (earliest receive wins) and mark a
    market whose copies disagree on identity as inconsistent."""

    by_id: dict[str, list[v3.V3Event]] = {}
    for event in events:
        if event.family != "new_market" or event.market_id is None:
            raise ReadinessError("READINESS_INPUT_INVALID")
        by_id.setdefault(event.market_id, []).append(event)
    candidates: list[MarketCandidate] = []
    inconsistent: list[dict[str, str]] = []
    for market_id in sorted(by_id, key=lambda m: (len(m), m)):
        copies = v3.order_events(by_id[market_id])
        identity = {(e.condition_id, e.field("assets_ids"), e.field("outcomes"), e.field("slug")) for e in copies}
        first = copies[0]
        if len(identity) != 1:
            inconsistent.append({"market_id": market_id, "reason": "V3_MARKET_IDENTITY_INCONSISTENT"})
            continue
        candidates.append(MarketCandidate(
            market_id=market_id,
            condition_id=first.condition_id,
            asset_ids=tuple((first.field("assets_ids") or "").split(",")),
            outcomes=tuple((first.field("outcomes") or "").split("\u001f")),
            question=first.field("question") or "",
            slug=first.field("slug") or "",
            first_received=first.timestamp_received,
            discovery_hour=first.hour,
        ))
    return tuple(candidates), tuple(inconsistent)


def _json_list(value: object) -> list[object]:
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            raise RuleExclusion("GAMMA_V3_IDENTITY_MISMATCH") from None
    if type(value) is not list:
        raise RuleExclusion("GAMMA_V3_IDENTITY_MISMATCH")
    return value


@dataclass(frozen=True)
class GammaFacts:
    market_id: str
    condition_id: str
    token_by_outcome: tuple[tuple[str, str], ...]
    open_time: str | None
    closed_time: str | None
    winning_outcome: str | None
    description: str
    resolution_source: str
    fees_enabled: bool | None
    fee_type: str | None
    fee_schedule: tuple[tuple[str, str], ...] | None
    order_min_size: str | None
    order_price_min_tick_size: str | None


def _decimal_text(value: object) -> str | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return format(value, ".10g")
    if isinstance(value, str) and re.fullmatch(r"-?\d+(\.\d+)?", value):
        return value
    return None


def normalize_gamma_market(document: object, candidate: MarketCandidate) -> GammaFacts:
    """Validate a Gamma-by-id response against the v3 market identity (closed exclusions)."""

    if not isinstance(document, Mapping):
        raise RuleExclusion("GAMMA_UNAVAILABLE")
    if str(document.get("id")) != candidate.market_id:
        raise RuleExclusion("GAMMA_V3_IDENTITY_MISMATCH")
    condition = document.get("conditionId")
    if not isinstance(condition, str) or condition.lower() != candidate.condition_id:
        raise RuleExclusion("GAMMA_V3_IDENTITY_MISMATCH")
    if document.get("slug") != candidate.slug:
        raise RuleExclusion("GAMMA_V3_IDENTITY_MISMATCH")
    tokens = [str(t) for t in _json_list(document.get("clobTokenIds"))]
    outcomes = [str(o) for o in _json_list(document.get("outcomes"))]
    if len(tokens) != len(outcomes) or len(set(tokens)) != len(tokens):
        raise RuleExclusion("GAMMA_V3_IDENTITY_MISMATCH")
    gamma_pairs = dict(zip(outcomes, tokens))
    v3_pairs = dict(zip(candidate.outcomes, candidate.asset_ids))
    if gamma_pairs != v3_pairs or set(outcomes) != {"Yes", "No"}:
        raise RuleExclusion("GAMMA_V3_IDENTITY_MISMATCH")
    winning: str | None = None
    prices = document.get("outcomePrices")
    try:
        price_list = [str(p) for p in _json_list(prices)] if prices is not None else []
    except RuleExclusion:
        price_list = []
    if (
        document.get("closed") is True
        and document.get("umaResolutionStatus") == "resolved"
        and len(price_list) == len(outcomes)
        and sorted(price_list) == ["0", "1"]
    ):
        winning = outcomes[price_list.index("1")]
    closed_time = document.get("closedTime")
    try:
        closed_text = utc_text(parse_utc(closed_time)) if closed_time is not None else None
    except ReadinessError:
        closed_text = None
    start = document.get("startDate")
    schedule = document.get("feeSchedule")
    fee_schedule = None
    if isinstance(schedule, Mapping):
        fee_schedule = tuple(sorted((str(k), json.dumps(v, sort_keys=True)) for k, v in schedule.items()))
    fees_enabled = document.get("feesEnabled")
    return GammaFacts(
        market_id=candidate.market_id,
        condition_id=candidate.condition_id,
        token_by_outcome=tuple(sorted(gamma_pairs.items())),
        open_time=start if isinstance(start, str) else None,
        closed_time=closed_text,
        winning_outcome=winning,
        description=document.get("description") if isinstance(document.get("description"), str) else "",
        resolution_source=document.get("resolutionSource") if isinstance(document.get("resolutionSource"), str) else "",
        fees_enabled=fees_enabled if isinstance(fees_enabled, bool) else None,
        fee_type=document.get("feeType") if isinstance(document.get("feeType"), str) else None,
        fee_schedule=fee_schedule,
        order_min_size=_decimal_text(document.get("orderMinSize")),
        order_price_min_tick_size=_decimal_text(document.get("orderPriceMinTickSize")),
    )


def yes_token(gamma: GammaFacts) -> str:
    return dict(gamma.token_by_outcome)["Yes"]


# ── Labels (post-outcome evidence, never feature evidence) ────────────────────


@dataclass(frozen=True)
class LabelEvidence:
    winning_outcome: str
    winning_token_id: str
    v3_resolution_received: str
    gamma_closed_time: str | None

    def to_mapping(self, rule: RuleSemantics) -> dict[str, object]:
        return {
            "post_outcome_evidence": True,
            "winning_outcome": self.winning_outcome,
            "winning_token_id": self.winning_token_id,
            "v3_resolution_received": self.v3_resolution_received,
            "gamma_closed_time": self.gamma_closed_time,
            "rule_cohort_id": rule.rule_cohort_id,
            "rule_text_sha256": rule.rule_text_sha256,
            "finality_policy": rule.finality_policy,
            "station_id": rule.station_id,
        }


def resolve_label(gamma: GammaFacts, resolutions: Sequence[v3.V3Event]) -> LabelEvidence:
    """Require a final Gamma outcome and v3 ``market_resolved`` agreement."""

    if gamma.winning_outcome is None:
        raise RuleExclusion("LABEL_GAMMA_NOT_FINAL")
    relevant = [e for e in resolutions if e.family == "market_resolved" and e.condition_id == gamma.condition_id]
    if not relevant:
        raise RuleExclusion("LABEL_V3_RESOLUTION_MISSING")
    token_to_outcome = {token: outcome for outcome, token in gamma.token_by_outcome}
    winners = {(e.field("winning_asset_id"), e.field("winning_outcome")) for e in relevant}
    if len(winners) != 1:
        raise RuleExclusion("LABEL_SOURCE_DISAGREEMENT")
    token, outcome = winners.pop()
    if token not in token_to_outcome or token_to_outcome[token] != outcome or outcome != gamma.winning_outcome:
        raise RuleExclusion("LABEL_SOURCE_DISAGREEMENT")
    first = v3.order_events(relevant)[0]
    return LabelEvidence(outcome, token, first.timestamp_received, gamma.closed_time)


# ── Checkpoint feature evidence ───────────────────────────────────────────────


def select_latest_market_event(
    events: Sequence[v3.V3Event],
    *,
    family: str,
    asset_id: str,
    checkpoint: datetime,
    lookback: timedelta,
    scanned_hours: Sequence[str],
    hour_coverage: Mapping[str, str],
) -> v3.V3Event:
    """Latest event of ``family`` for ``asset_id`` received in ``[checkpoint - lookback,
    checkpoint]``; every hour from that event's hour through the checkpoint hour must have been
    scanned and be admissible (FULL / SINGLE-BY-DESIGN), otherwise a later event could be
    missing and the row is excluded."""

    if lookback != MARKET_HISTORY_LOOKBACK:
        raise ReadinessError("READINESS_WINDOW_INVALID")
    low = checkpoint - lookback
    eligible = [
        e for e in events
        if e.family == family and e.asset_id == asset_id and low <= parse_utc(e.timestamp_received) <= checkpoint
    ]
    if not eligible:
        raise RuleExclusion("MARKET_HISTORY_NOT_OBSERVED_IN_LOOKBACK")
    latest = v3.order_events(eligible)[-1]
    needed = v3.hours_between(parse_utc(latest.timestamp_received), checkpoint)
    scanned = set(scanned_hours)
    for hour in needed:
        if hour not in scanned:
            raise RuleExclusion("MARKET_HISTORY_NOT_OBSERVED_IN_LOOKBACK")
        if hour_coverage.get(hour) not in v3.ADMISSIBLE_COVERAGE_CLASSES:
            raise RuleExclusion("MARKET_HISTORY_COVERAGE_INADMISSIBLE")
    return latest


def market_history_evidence(
    bba: v3.V3Event,
    ltp: v3.V3Event | None,
    checkpoint: datetime,
    bba_coverage: Mapping[str, str],
    ltp_coverage: Mapping[str, str],
    ltp_searched_hours: Sequence[str],
) -> dict[str, object]:
    for event in (bba, ltp):
        if event is not None and parse_utc(event.timestamp_received) > checkpoint:
            raise ReadinessError("READINESS_LOOK_AHEAD")
    record: dict[str, object] = {
        "source_class": v3.SOURCE_CLASS,
        "source_authority": v3.B0_SOURCE_AUTHORITY,
        "ordering_basis": "timestamp_received",
        "best_bid_ask": {
            "asset_id": bba.asset_id,
            "best_bid": bba.field("best_bid"),
            "best_ask": bba.field("best_ask"),
            "spread": bba.field("spread"),
            "timestamp_received": bba.timestamp_received,
            "venue_timestamp": bba.venue_timestamp,
            "hour": bba.hour,
            "coverage_class": bba_coverage[bba.hour],
        },
        "last_trade_price": None,
        "last_trade_price_state": "NOT_OBSERVED_IN_SEARCHED_HOURS",
        "last_trade_price_searched_hours": sorted(set(ltp_searched_hours)),
    }
    if ltp is not None:
        record["last_trade_price"] = {
            "asset_id": ltp.asset_id,
            "price": ltp.field("price"),
            "side": ltp.field("side"),
            "fee_rate_bps": ltp.field("fee_rate_bps"),
            "timestamp_received": ltp.timestamp_received,
            "venue_timestamp": ltp.venue_timestamp,
            "hour": ltp.hour,
            "coverage_class": ltp_coverage[ltp.hour],
        }
        record["last_trade_price_state"] = "OBSERVED"
    return record


def _grid_text(value: float) -> str:
    return f"{value:.6f}"


def weather_evidence(
    vintage: ndfd.NdfdObject,
    object_sha256: str,
    decoded: Sequence[tuple[ndfd.MessageSlice, ndfd.DecodedPop12]],
    station: ndfd.StationMetadata,
    standard_offset_minutes: int,
    target_day: date,
    checkpoint: datetime,
) -> dict[str, object]:
    """Weather feature evidence from ONE eligible vintage: every PoP12 period overlapping the
    target climate day, raw values preserved, no combination into a probability."""

    if parse_utc(vintage.public_available_time) > checkpoint:
        raise ReadinessError("READINESS_LOOK_AHEAD")
    window_start, window_end = ndfd.climate_day_window(target_day, standard_offset_minutes)
    headers = [item.header for _slice, item in decoded]
    overlapping = ndfd.intervals_overlapping(headers, window_start, window_end)
    if not overlapping:
        raise RuleExclusion("WEATHER_NO_OVERLAPPING_PERIOD")
    periods = []
    binding: dict[str, object] | None = None
    for index in overlapping:
        piece, item = decoded[index]
        values = [v for v in item.station_values if v.station_id == station.station_id]
        if len(values) != 1:
            raise RuleExclusion("GRID_BINDING_INVALID")
        value = values[0]
        if value.pop12_percent is None:
            raise RuleExclusion("WEATHER_VALUE_MISSING")
        current = {
            "grid_index": value.grid_index,
            "grid_latitude": _grid_text(value.grid_latitude),
            "grid_longitude": _grid_text(value.grid_longitude),
            "distance_km": f"{value.distance_km:.3f}",
        }
        if binding is not None and binding != current:
            raise RuleExclusion("GRID_BINDING_INVALID")
        binding = current
        periods.append({
            "message_index": piece.index,
            "message_sha256": piece.sha256,
            "reference_time": item.header.reference_time,
            "valid_start": item.header.valid_start,
            "valid_end": item.header.valid_end,
            "pop12_percent": value.pop12_percent,
        })
    return {
        "source_class": ndfd.SOURCE_CLASS,
        "object_key": vintage.key,
        "object_sha256": object_sha256,
        "bulletin_time": vintage.bulletin_time,
        "public_available_time": vintage.public_available_time,
        "availability_basis": vintage.availability_basis,
        "periods": periods,
        "station": {
            "station_id": station.station_id,
            "latitude": _grid_text(station.latitude),
            "longitude": _grid_text(station.longitude),
            "time_zone": station.time_zone,
            "standard_utc_offset_minutes": standard_offset_minutes,
            "reference_only_not_predictive": True,
        },
        "grid": binding,
        "climate_day_start": utc_text(window_start),
        "climate_day_end": utc_text(window_end),
    }


# ── Execution-feasibility factual inventory ───────────────────────────────────


def _weakest(states: Sequence[str]) -> str:
    if "SOURCE_DISAGREEMENT" in states:
        return "SOURCE_DISAGREEMENT"
    return min(states, key=lambda s: _EXECUTION_RANK[s])


def execution_facts(
    gamma: GammaFacts,
    rule: RuleSemantics | None,
    trade_events: Sequence[v3.V3Event],
    tick_events: Sequence[v3.V3Event],
) -> dict[str, object]:
    """Factual per-market states; never forces AVAILABLE and never backdates current metadata."""

    fee_rates = sorted({e.field("fee_rate_bps") for e in trade_events if e.field("fee_rate_bps") is not None})
    if fee_rates:
        disagree = gamma.fees_enabled is False and any(rate not in ("0",) for rate in fee_rates)
        fees_state = "SOURCE_DISAGREEMENT" if disagree else "HISTORICALLY_EVIDENCED"
    elif gamma.fees_enabled is not None:
        fees_state = "CURRENT_ONLY"
    else:
        fees_state = "MISSING"
    rules_state = "CURRENT_ONLY" if rule is not None else "MISSING"
    ticks = sorted({(e.timestamp_received, e.field("old_tick_size"), e.field("new_tick_size")) for e in tick_events})
    tick_state = "HISTORICALLY_EVIDENCED" if ticks else ("CURRENT_ONLY" if gamma.order_price_min_tick_size else "MISSING")
    min_order_state = "CURRENT_ONLY" if gamma.order_min_size else "MISSING"
    return {
        "FEES": {
            "state": fees_state,
            "v3_fee_rate_bps_observed": fee_rates,
            "gamma_current_fees_enabled": gamma.fees_enabled,
            "gamma_current_fee_type": gamma.fee_type,
            "current_category_docs_role": "SUPPORTING_CONTEXT_ONLY_NEVER_BACKDATED",
        },
        "RESOLUTION_RULES": {
            "state": rules_state,
            "basis": "GAMMA_RULE_TEXT_RETRIEVED_POST_RESOLUTION_NOT_INDEPENDENTLY_TIMESTAMPED",
            "rule_cohort_id": rule.rule_cohort_id if rule else None,
            "rule_text_sha256": rule.rule_text_sha256 if rule else None,
            "station_id": rule.station_id if rule else None,
            "threshold_inches": rule.threshold_inches if rule else None,
            "climate_day": rule.climate_day if rule else None,
            "finality_policy": rule.finality_policy if rule else None,
        },
        "TICK_SIZE_MIN_ORDER": {
            "state": _weakest([tick_state, min_order_state]),
            "tick_size_state": tick_state,
            "min_order_state": min_order_state,
            "v3_tick_size_changes": [list(t) for t in ticks],
            "gamma_current_tick_size": gamma.order_price_min_tick_size,
            "gamma_current_min_order_size": gamma.order_min_size,
        },
    }


# ── Rows and exclusions ───────────────────────────────────────────────────────


def build_row(
    *,
    candidate: MarketCandidate,
    target_day: date,
    checkpoint_id: str,
    checkpoint_time: datetime,
    yes_token_id: str,
    market_history: Mapping[str, object],
    weather: Mapping[str, object],
    label: Mapping[str, object],
    manifest_ids: Sequence[str],
) -> dict[str, object]:
    if checkpoint_id not in CHECKPOINT_IDS:
        raise ReadinessError("READINESS_INPUT_INVALID")
    for authority in (market_history.get("source_authority"), market_history.get("source_class"), weather.get("source_class")):
        if authority in FORBIDDEN_AUTHORITY_LABELS:
            raise ReadinessError("READINESS_AUTHORITY_LAUNDERING")
    if market_history.get("source_authority") != v3.B0_SOURCE_AUTHORITY or market_history.get("source_class") != v3.SOURCE_CLASS:
        raise ReadinessError("READINESS_AUTHORITY_LAUNDERING")
    if label.get("post_outcome_evidence") is not True:
        raise ReadinessError("READINESS_INPUT_INVALID")
    body = {
        "market_id": candidate.market_id,
        "condition_id": candidate.condition_id,
        "yes_token_id": yes_token_id,
        "target_date": target_day.isoformat(),
        "checkpoint_id": checkpoint_id,
        "checkpoint_time": utc_text(checkpoint_time),
        "feature_evidence": {"market_history": dict(market_history), "weather": dict(weather)},
        "label_evidence": dict(label),
        "source_authority": dict(SOURCE_AUTHORITY),
        "provenance_manifest_ids": sorted(manifest_ids),
    }
    return {"row_id": content_id(ROW_ID_PREFIX, body), **body}


def exclusion(market_id: str, reason: str, checkpoint_id: str | None = None, target_date: str | None = None) -> dict[str, object]:
    if checkpoint_id is None and reason not in MARKET_EXCLUSION_REASONS:
        raise ReadinessError("READINESS_INPUT_INVALID")
    if checkpoint_id is not None and (checkpoint_id not in CHECKPOINT_IDS or reason not in ROW_EXCLUSION_REASONS):
        raise ReadinessError("READINESS_INPUT_INVALID")
    return {"market_id": market_id, "checkpoint_id": checkpoint_id, "target_date": target_date, "reason": reason}


def _row_sort_key(row: Mapping[str, object]) -> tuple[object, ...]:
    return (row["target_date"], len(str(row["market_id"])), row["market_id"], row["checkpoint_id"])


def _exclusion_sort_key(item: Mapping[str, object]) -> tuple[object, ...]:
    return (item.get("target_date") or "", len(str(item["market_id"])), item["market_id"], item["checkpoint_id"] or "", item["reason"])


# ── Counts (factual only) ─────────────────────────────────────────────────────


def derive_counts(
    discovered_candidates: int,
    rows: Sequence[Mapping[str, object]],
    market_exclusions: Sequence[Mapping[str, object]],
    row_exclusions: Sequence[Mapping[str, object]],
    hour_coverage: Mapping[str, str],
    ndfd_vintage_keys: Sequence[str],
) -> dict[str, object]:
    """Actual derived counts. No required sample, group, power, MDE or significance threshold."""

    included = discovered_candidates - len(market_exclusions)
    per_checkpoint = {cp: sum(1 for r in rows if r["checkpoint_id"] == cp) for cp in CHECKPOINT_IDS}
    dates = {cp: len({r["target_date"] for r in rows if r["checkpoint_id"] == cp}) for cp in CHECKPOINT_IDS}
    market_reasons: dict[str, int] = {}
    for item in market_exclusions:
        market_reasons[str(item["reason"])] = market_reasons.get(str(item["reason"]), 0) + 1
    row_reasons: dict[str, dict[str, int]] = {cp: {} for cp in CHECKPOINT_IDS}
    for item in row_exclusions:
        bucket = row_reasons[str(item["checkpoint_id"])]
        bucket[str(item["reason"])] = bucket.get(str(item["reason"]), 0) + 1
    coverage: dict[str, int] = {name: 0 for name in v3.COVERAGE_CLASSES}
    for klass in hour_coverage.values():
        coverage[klass] = coverage.get(klass, 0) + 1
    return {
        "discovered_candidates": discovered_candidates,
        "included_markets": included,
        "excluded_markets": len(market_exclusions),
        "market_exclusion_reasons": dict(sorted(market_reasons.items())),
        "checkpoint_usable_rows": per_checkpoint,
        "checkpoint_row_exclusion_reasons": {cp: dict(sorted(v.items())) for cp, v in row_reasons.items()},
        "independent_target_dates": {**dates, "ANY_CHECKPOINT": len({r["target_date"] for r in rows})},
        "market_history_rows_available": len(rows),
        "pendulumflow_hours_by_coverage_class": coverage,
        "ndfd_vintages_selected": len(set(ndfd_vintage_keys)),
    }


def verify_counts(counts: Mapping[str, object], recomputed: Mapping[str, object]) -> None:
    if canonical_json_bytes(counts) != canonical_json_bytes(recomputed):
        raise ReadinessError("READINESS_COUNTS_FABRICATED")
    forbidden = {"required_samples", "min_samples_per_role", "target_power", "mde", "alpha", "required_independent_groups"}
    if forbidden & set(counts):
        raise ReadinessError("READINESS_COUNTS_FABRICATED")


# ── B0 compatibility ──────────────────────────────────────────────────────────


def derive_b0_compatibility(canonical_pit_evidence_ids: Sequence[str] = ()) -> str:
    """External-only unless genuine canonical PIT evidence is independently bound. This WP has no
    route that can independently verify such a binding, so any supplied claim is rejected rather
    than trusted (no laundering of PendulumFlow into canonical PIT)."""

    if canonical_pit_evidence_ids:
        raise ReadinessError("READINESS_B0_CANONICAL_BINDING_UNSUPPORTED")
    return B0_EXTERNAL_ONLY


# ── Provenance binding (reuses the common provenance core unchanged) ──────────


@dataclass(frozen=True)
class RetainedArtifact:
    """One retained raw source artifact (content-addressed; no local path, no wall-clock)."""

    source_system: str
    endpoint: str
    retrieval_method: str
    request_parameters: tuple[tuple[str, str], ...]
    content_sha256: str
    byte_length: int
    media_type: str
    public_available_time: str | None
    event_time: str | None
    resolution_time: str | None
    dq_flags: tuple[str, ...]
    replay_fidelity: str


def raw_reference(artifact: RetainedArtifact) -> RawEvidenceReference:
    pit = build_pit_timestamps(
        public_available_time=artifact.public_available_time,
        event_time=artifact.event_time,
        resolution_time=artifact.resolution_time,
    )
    return build_raw_evidence_reference(
        source_system=artifact.source_system,
        endpoint=artifact.endpoint,
        retrieval_method=artifact.retrieval_method,
        content_sha256=artifact.content_sha256,
        byte_length=artifact.byte_length,
        media_type=artifact.media_type,
        pit=pit,
        dq_flags=artifact.dq_flags,
        replay_fidelity=artifact.replay_fidelity,
        request_parameters=artifact.request_parameters,
        raw_snapshot_ref="rawsnapshot:sha256:" + artifact.content_sha256,
    )


_FIDELITY_RANK = {"EXACT": 0, "FAITHFUL": 1, "PARTIAL": 2, "UNREPLAYABLE": 3}
MAX_MANIFEST_ITEMS = 256


def build_shard_manifests(
    *,
    target_date: str,
    shard_kind: str,
    references: Sequence[RawEvidenceReference],
    output_records: Sequence[Mapping[str, object]],
    information_cutoff: datetime,
    repo_code_identity: str,
    dataset_refs: Sequence[str],
) -> tuple[ResearchProvenanceManifest, ...]:
    """Deterministic <=256-item provenance shards for one date/source family."""

    if shard_kind not in ("PENDULUMFLOW_MARKET_HISTORY", "NOAA_NDFD_WEATHER", "GAMMA_NWS_RULE_LABEL_METADATA"):
        raise ReadinessError("READINESS_INPUT_INVALID")
    ordered = sorted(references, key=lambda r: r.raw_evidence_reference_id)
    if not ordered:
        return ()
    chunks = [ordered[i : i + MAX_MANIFEST_ITEMS] for i in range(0, len(ordered), MAX_MANIFEST_ITEMS)]
    manifests = []
    for number, chunk in enumerate(chunks):
        flags = sorted({flag for ref in chunk for flag in ref.dq_flags})
        dq = ("OK",) if flags == ["OK"] else tuple(flag for flag in flags if flag != "OK")
        fidelity = max((ref.replay_fidelity for ref in chunk), key=lambda f: _FIDELITY_RANK[f])
        gap = "" if dq == ("OK",) and fidelity in ("EXACT", "FAITHFUL") else "SOURCE_COVERAGE_OR_FIDELITY_DEGRADED"
        output_body = {"target_date": target_date, "shard_kind": shard_kind, "chunk": number,
                       "records": [dict(r) for r in output_records]}
        manifests.append(build_research_provenance_manifest(
            repo_code_identity=repo_code_identity,
            information_cutoff=utc_text(information_cutoff),
            output_identity=content_id(SHARD_ID_PREFIX, {"target_date": target_date, "shard_kind": shard_kind, "chunk": number}),
            output_hash=hashlib.sha256(canonical_json_bytes(output_body)).hexdigest(),
            input_evidence_reference_ids=[ref.raw_evidence_reference_id for ref in chunk],
            input_content_hashes=[ref.content_sha256 for ref in chunk],
            dataset_refs=sorted(dataset_refs),
            request_source_version_refs=[],
            dq_flags=dq,
            replay_fidelity=fidelity,
            gap_summary=gap,
        ))
    return tuple(manifests)


def is_ready_manifest(manifest: ResearchProvenanceManifest) -> bool:
    return (
        manifest.dq_flags == ("OK",)
        and manifest.replay_fidelity in ("EXACT", "FAITHFUL")
        and manifest.gap_summary == ""
        and len(manifest.input_evidence_reference_ids) <= MAX_MANIFEST_ITEMS
        and verify_research_provenance_manifest_identity(manifest)
    )


def split_ready_manifests(
    manifests: Sequence[ResearchProvenanceManifest],
) -> tuple[tuple[ResearchProvenanceManifest, ...], tuple[ResearchProvenanceManifest, ...]]:
    ready = tuple(m for m in manifests if is_ready_manifest(m))
    diagnostic = tuple(m for m in manifests if not is_ready_manifest(m))
    return ready, diagnostic


def require_ready_manifests(manifests: Sequence[ResearchProvenanceManifest]) -> None:
    for manifest in manifests:
        if not is_ready_manifest(manifest):
            raise ReadinessError("READINESS_MANIFEST_NOT_READY")


def verify_references(references: Sequence[RawEvidenceReference]) -> None:
    for reference in references:
        if not verify_raw_evidence_reference_identity(reference):
            raise ReadinessError("READINESS_IDENTITY_MISMATCH")


# ── Bundle ────────────────────────────────────────────────────────────────────


def checkpoint_definitions() -> dict[str, object]:
    return {
        CHECKPOINT_A: "max(v3 new_market timestamp_received, trustworthy Gamma open time) + 60 minutes",
        CHECKPOINT_B: "target-date midnight in rule-station local standard time; eligible only if observably open >= 60 minutes before",
        "market_history_lookback_hours": 24,
        "ndfd_vintage_lookback_hours": 48,
        "gamma_open_trust_window_hours": 24,
    }


def build_bundle(
    *,
    rows: Sequence[Mapping[str, object]],
    market_exclusions: Sequence[Mapping[str, object]],
    row_exclusions: Sequence[Mapping[str, object]],
    counts: Mapping[str, object],
    execution_evidence: Mapping[str, Mapping[str, object]],
    ready_manifest_ids: Sequence[str],
    diagnostic_manifest_ids: Sequence[str],
    external_dataset_ids: Sequence[str],
    source_facts: Mapping[str, object],
    terminal_reason: str,
    canonical_pit_evidence_ids: Sequence[str] = (),
) -> dict[str, object]:
    """Seal the WeatherQualificationDataReadinessBundle with its logical dataset id."""

    if terminal_reason not in TERMINAL_REASONS:
        raise ReadinessError("READINESS_INPUT_INVALID")
    ordered_rows = sorted((dict(r) for r in rows), key=_row_sort_key)
    for row in ordered_rows:
        body = {k: v for k, v in row.items() if k != "row_id"}
        if row["row_id"] != content_id(ROW_ID_PREFIX, body):
            raise ReadinessError("READINESS_IDENTITY_MISMATCH")
        if set(row["provenance_manifest_ids"]) - set(ready_manifest_ids):  # type: ignore[arg-type]
            raise ReadinessError("READINESS_MANIFEST_NOT_READY")
    b0 = derive_b0_compatibility(canonical_pit_evidence_ids)
    if terminal_reason == "EVIDENCE_COMPLETE_ROWS_PRESENT":
        if not ordered_rows:
            raise ReadinessError("READINESS_COUNTS_FABRICATED")
        terminal = TERMINAL_READY
    else:
        terminal = TERMINAL_INSUFFICIENT
        if terminal_reason == "NO_EVIDENCE_COMPLETE_ROW" and ordered_rows:
            raise ReadinessError("READINESS_COUNTS_FABRICATED")
    execution_summary: dict[str, dict[str, int]] = {cls: {} for cls in EXECUTION_CLASSES}
    for facts in execution_evidence.values():
        for cls in EXECUTION_CLASSES:
            state = str(facts[cls]["state"])  # type: ignore[index]
            if state not in EXECUTION_STATES:
                raise ReadinessError("READINESS_INPUT_INVALID")
            execution_summary[cls][state] = execution_summary[cls].get(state, 0) + 1
    dataset = {
        "schema_id": BUNDLE_SCHEMA_ID,
        "schema_version": BUNDLE_SCHEMA_VERSION,
        "wp_id": WP_ID,
        "lineage": {
            "alpha_candidate_id": ALPHA_CANDIDATE_ID,
            "alpha_family_id": ALPHA_FAMILY_ID,
            "alpha_episode_id": ALPHA_EPISODE_ID,
            "alpha_registry_head": ALPHA_REGISTRY_HEAD,
            "alpha_result_state": ALPHA_RESULT_STATE,
            "af1_receipt_id": AF1_RECEIPT_ID,
        },
        "corpus": {"first_target_date": CORPUS_START.isoformat(), "last_target_date": CORPUS_END.isoformat(),
                   "target_date_count": len(target_dates())},
        "checkpoints": checkpoint_definitions(),
        "source_authority": dict(SOURCE_AUTHORITY),
        "row_ids": [r["row_id"] for r in ordered_rows],
        "ready_manifest_ids": sorted(ready_manifest_ids),
        "diagnostic_manifest_ids": sorted(diagnostic_manifest_ids),
        "external_dataset_ids": sorted(external_dataset_ids),
        "counts": dict(counts),
        "execution_evidence_summary": {cls: dict(sorted(v.items())) for cls, v in execution_summary.items()},
        "b0_contract_compatibility": b0,
        "b0_source_authority": v3.B0_SOURCE_AUTHORITY,
        "no_authority_flags": dict(NO_AUTHORITY_FLAGS),
    }
    logical_dataset_id = content_id(DATASET_ID_PREFIX, dataset)
    bundle_body = {
        "logical_dataset_id": logical_dataset_id,
        "dataset": dataset,
        "rows": ordered_rows,
        "market_exclusions": sorted((dict(e) for e in market_exclusions), key=_exclusion_sort_key),
        "row_exclusions": sorted((dict(e) for e in row_exclusions), key=_exclusion_sort_key),
        "execution_evidence": {k: dict(v) for k, v in sorted(execution_evidence.items(), key=lambda kv: (len(kv[0]), kv[0]))},
        "source_facts": dict(source_facts),
        "terminal": terminal,
        "terminal_reason": terminal_reason,
        "market_history_rows_available": len(ordered_rows),
    }
    return {"bundle_id": content_id(BUNDLE_ID_PREFIX, bundle_body), **bundle_body}


def verify_bundle(bundle: Mapping[str, object]) -> None:
    """Re-derive the dataset and bundle identities and every row id (zero network)."""

    if not isinstance(bundle, Mapping):
        raise ReadinessError("READINESS_INPUT_INVALID")
    body = {k: v for k, v in bundle.items() if k != "bundle_id"}
    if bundle.get("bundle_id") != content_id(BUNDLE_ID_PREFIX, body):
        raise ReadinessError("READINESS_IDENTITY_MISMATCH")
    dataset = bundle.get("dataset")
    if bundle.get("logical_dataset_id") != content_id(DATASET_ID_PREFIX, dataset):
        raise ReadinessError("READINESS_IDENTITY_MISMATCH")
    rows = bundle.get("rows")
    if not isinstance(rows, list) or not isinstance(dataset, Mapping):
        raise ReadinessError("READINESS_INPUT_INVALID")
    if [r.get("row_id") for r in rows] != dataset.get("row_ids"):
        raise ReadinessError("READINESS_IDENTITY_MISMATCH")
    for row in rows:
        if row.get("row_id") != content_id(ROW_ID_PREFIX, {k: v for k, v in row.items() if k != "row_id"}):
            raise ReadinessError("READINESS_IDENTITY_MISMATCH")
    if dataset.get("b0_contract_compatibility") not in B0_STATES or bundle.get("terminal") not in TERMINALS:
        raise ReadinessError("READINESS_INPUT_INVALID")
    if dataset.get("no_authority_flags") != NO_AUTHORITY_FLAGS:
        raise ReadinessError("READINESS_AUTHORITY_LAUNDERING")
    serialized = canonical_json_bytes(bundle).decode("utf-8")
    for label in FORBIDDEN_AUTHORITY_LABELS:
        if f'"{label}"' in serialized:
            raise ReadinessError("READINESS_AUTHORITY_LAUNDERING")
