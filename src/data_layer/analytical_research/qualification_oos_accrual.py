"""S10-QUAL-DATA-03 prospective weather qualification OOS accrual (pure, offline, deterministic).

Mechanical prospective evidence accrual frozen by S10-QUAL-PLAN-01
(``docs/qualification_plans/S10-QUAL-PLAN-01/weather_plan_v1.json``): pending/terminal
classification types, label-free prospective row identity, the stable chronological prefix, the
frozen external B0 materialization, q/L feature materialization as canonical decimal strings,
feature-column and internal label-store identities, the OOS-membership preimage/id, the MR12
execution-evidence classification and the closed visible-report schema (pre-release exposure
firewall).

ACCRUAL ONLY. This module never computes a B1/B2 forecast, never fits a model, never computes a
Brier/log-loss/comparison statistic, never constructs a QualificationCandidate, never runs the
qualification gate and never builds a WP170 object. It performs no network access and writes no
files. Identities are SHA-256 over canonical JSON (UTF-8, sorted keys, compact separators, no
floats) and exclude absolute paths, host names and transport timing.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_EVEN, Decimal, InvalidOperation
from typing import Mapping, Sequence

from . import pendulumflow_v3 as v3
from . import qualification_data_readiness as qd

WP_ID = "S10-QUAL-DATA-03"

# ── Frozen PLAN-01 binding ────────────────────────────────────────────────────

PLAN_PATH = "docs/qualification_plans/S10-QUAL-PLAN-01/weather_plan_v1.json"
POWER_DOC_PATH = "docs/qualification_plans/S10-QUAL-PLAN-01/power_analysis_v1.md"
PLAN_SHA256 = "3b2a99abea8bbd18794c8117d6c1ab696ac817217cd5713367b2ee9a76aa9463"
POWER_DOC_SHA256_LF = "f20f24a26444c93389b10a34ed1a88530aca0f64bc7efb694dccce826c6ee884"
PLAN_MERGE_SHA = "75e17927155dc7ffb5aebfba2f1d97ddd5c2f8b9"
PLAN_MERGE_PARENTS = ("e2edb21e25e7841376c3cb51c27a622fbc0cbc83", "11244eed9686b01e29ede83ea6578bb0a781db6f")
PLAN_MERGE_COMMITTER = "GitHub"
PLAN_MERGE_TIME = "2026-10-01T02:39:26Z"
FREEZE_DEADLINE = "2026-10-14T00:00:00Z"
OOS_START = "2026-10-15T00:00:00Z"
EMBARGO_SECONDS = 172800
EMBARGO_LOWER_BOUND = "2026-10-17T00:00:00Z"
CAP = "2027-02-12T00:00:00Z"
DATA02_BUNDLE_ID = "weatherqualbundle:sha256:a5911ab05cc8c650377447aa46f65f3b2002fc458e3c51a64f8705b1adcc69ae"
DATA02_DATASET_ID = "weatherqualdataset:sha256:a3e98a35ea052e1dfeb5225239a74beaee47d04111ebb34e6d27717490d9ac39"
DATA02_OOS_STATUS = "HISTORICAL_NON_OOS"

SCAN_START = date(2026, 10, 15)
SCAN_END = date(2027, 2, 11)
DISCOVERY_HOURS_UTC = (11, 12)
LABEL_WINDOW = timedelta(minutes=30)
PLAN_TARGET_EFFECTIVE_DATES = 50  # the frozen PLAN-01 literals (binding checks)
PLAN_MIN_SAMPLES_PER_ROLE = 100
TARGET_EFFECTIVE_DATES = PLAN_TARGET_EFFECTIVE_DATES
MIN_OOS_ROWS = PLAN_MIN_SAMPLES_PER_ROLE
MAX_CONSIDERED_TARGET_DATES = 120

MAX_QUALIFICATION_PROVENANCE_MANIFESTS = 256  # equals qualification.MAX_QUALIFICATION_PROVENANCE_MANIFESTS
MANIFESTS_PER_DATE_MINIMUM = 3  # one ready shard per required source family
PROSPECTIVE_MANIFEST_RESERVE = TARGET_EFFECTIVE_DATES * MANIFESTS_PER_DATE_MINIMUM  # 150

B0_RULE = "EXTERNAL_PIT_MARKET_PROBABILITY_V1"
MAX_MIDPOINT_SPREAD = Decimal("0.1")
MAX_LAST_TRADE_AGE_SECONDS = 86400
Q_CLIP = (Decimal("0.01"), Decimal("0.99"))
L_QUANTUM = Decimal("1E-12")
FEATURE_REFS = ("mkt.ext_b0_probability_v1", "time.ndfd_lead_hours_v1", "wx.ndfd_pop12_max_climate_day_v1")
LABEL_REF = "label.polymarket_nws_cli_rain_yes_v1"

FEE_DOC_URL = "https://help.polymarket.com/en/articles/13364478-trading-fees"
FEE_DOC_HOST = "help.polymarket.com"

# ── Identity prefixes ─────────────────────────────────────────────────────────

ROW_ID_PREFIX = "weatherqualoosrow:sha256:"
MEMBERSHIP_ID_PREFIX = "oosmembership:sha256:"
BUNDLE_ID_PREFIX = "weatherqualoosbundle:sha256:"
FEATURE_COLUMN_ID_PREFIX = "weatherqualoosfeaturecolumn:sha256:"
LABEL_STORE_ID_PREFIX = "weatherqualooslabelstore:sha256:"
LEDGER_ENTRY_PREFIX = "weatherqualoosledger:sha256:"
SEALED_RECORD_PREFIX = "weatherqualoossealed:sha256:"
CAPTURE_ID_PREFIX = "weatherqualooscapture:sha256:"
LEDGER_GENESIS = "GENESIS"

# ── States and closed vocabularies ────────────────────────────────────────────

STATE_NOT_STARTED = "DATA03_IMPLEMENTED_NOT_STARTED"
STATE_INCOMPLETE = "ACCRUAL_INCOMPLETE"
STATE_SEALED = "OOS_MEMBERSHIP_SEALED"
STATE_ROWS_INSUFFICIENT = "QUAL_OOS_ROWS_INSUFFICIENT"
STATE_INSUFFICIENT_AT_CAP = "QUAL_OOS_INSUFFICIENT_AT_CAP"
FINAL_STATES = (STATE_SEALED, STATE_ROWS_INSUFFICIENT, STATE_INSUFFICIENT_AT_CAP)
STATES = (STATE_NOT_STARTED, STATE_INCOMPLETE, *FINAL_STATES)

PENDING_LABEL_FINALITY = "PENDING_LABEL_FINALITY"
STRUCTURAL_PENDING = "STRUCTURAL_CLASSIFICATION_PENDING"
PENDING_STATES = (PENDING_LABEL_FINALITY, STRUCTURAL_PENDING)

DATE_ELIGIBLE = "ELIGIBLE"
DATE_EXCLUDED = "EXCLUDED"
DATE_PENDING = "PENDING"

SEAL_NOT_READY = "NOT_SEALABLE"

B0_BASIS_MIDPOINT = "MIDPOINT"
B0_BASIS_TRADE = "LAST_TRADE"
B0_BASES = (B0_BASIS_MIDPOINT, B0_BASIS_TRADE)
LTP_STATE_SEARCH_INCOMPLETE = "NOT_OBSERVED_SEARCH_INCOMPLETE_SOURCE_READ_FAILED"

# Exactly the PLAN-01 ``prospective_data_seal.exclusion_reason_codes`` (one reason per subject).
MARKET_EXCLUSION_REASONS = (
    "BUDGET_EXHAUSTED_BEFORE_EVALUATION",
    "GAMMA_UNAVAILABLE",
    "GAMMA_V3_IDENTITY_MISMATCH",
    "LABEL_SOURCE_DISAGREEMENT",
    "LABEL_V3_RESOLUTION_MISSING",
    "LABEL_V3_SOURCE_READ_FAILED",
    "RULE_CLIMATE_DAY_MISSING",
    "RULE_SEMANTICS_UNSUPPORTED",
    "RULE_STATION_AMBIGUOUS",
    "RULE_STATION_MISSING",
    "RULE_THRESHOLD_MISSING",
    "SLUG_NOT_DAILY_RAIN_FAMILY",
    "STATION_METADATA_INVALID",
    "STATION_METADATA_UNAVAILABLE",
    "STATION_OFFSET_UNDERIVABLE",
    "TARGET_DATE_OUTSIDE_CORPUS",
    "V3_MARKET_IDENTITY_INCONSISTENT",
)
ROW_EXCLUSION_REASONS = (
    "B0_UNAVAILABLE",
    "BUDGET_EXHAUSTED_BEFORE_EVALUATION",
    "CHECKPOINT_B_MARKET_NOT_OPEN_60M",
    "GRID_BINDING_INVALID",
    "LABEL_RESOLVED_BEFORE_CHECKPOINT",
    "MARKET_HISTORY_COVERAGE_INADMISSIBLE",
    "MARKET_HISTORY_NOT_OBSERVED_IN_LOOKBACK",
    "MARKET_HISTORY_SOURCE_INVALID",
    "WEATHER_NO_ELIGIBLE_VINTAGE",
    "WEATHER_NO_OVERLAPPING_PERIOD",
    "WEATHER_SOURCE_INVALID",
    "WEATHER_VALUE_MISSING",
)
DATE_EXCLUSION_REASONS = (
    "OOS_DATE_DECISION_AT_OR_AFTER_CAP",
    "OOS_DATE_DECISION_BEFORE_START",
    "OOS_DATE_DECISION_IN_WP170_EMBARGO",
    "OOS_DATE_NO_ELIGIBLE_ROW",
)
# Codes in the frozen vocabulary that DATA-03 never mints: per-run budget exhaustion leaves the
# affected subjects pending, and prospective label finality is a pending state, never an exclusion.
NEVER_MINTED_REASONS = frozenset({"BUDGET_EXHAUSTED_BEFORE_EVALUATION"})
FORBIDDEN_PROSPECTIVE_REASONS = frozenset({"LABEL_GAMMA_NOT_FINAL"})
SUBJECT_KINDS = ("DATE", "MARKET", "ROW")
CHECKPOINT_IDS = qd.CHECKPOINT_IDS

MEMBERSHIP_PREIMAGE_KEYS = (
    "cap", "data03_bundle_id", "end_time", "oos_exclusions", "oos_row_ids", "oos_start", "oos_target_dates",
    "plan_01_plan_sha256",
)
EXCLUSION_ITEM_KEYS = ("reason_code", "subject_id", "subject_kind", "target_date")

EXECUTION_CLASSES = ("FEES", "LATENCY", "PARTIAL_FILL", "RESOLUTION_RULES", "SPREAD_DEPTH", "TICK_SIZE_MIN_ORDER")
EXECUTION_STATES = ("AVAILABLE", "PARTIAL", "MISSING")
EXECUTION_REQUIRED_CAPTURES = {
    "FEES": ("OFFICIAL_FEE_DOCUMENTATION", "CURRENT_OPEN_DAILY_RAIN_GAMMA_MARKET_DOCUMENTS"),
    "LATENCY": ("ORDER_PLACEMENT_LATENCY_MEASUREMENT",),
    "PARTIAL_FILL": ("FILL_RATE_EVIDENCE",),
    "RESOLUTION_RULES": ("CURRENT_OPEN_DAILY_RAIN_GAMMA_MARKET_DOCUMENTS", "CURRENT_RESOLUTION_RULE_TEXT_AND_COHORT_SEMANTICS"),
    "SPREAD_DEPTH": ("DECISION_TIME_ORDER_BOOK_DEPTH", "DECISION_TIME_TOP_OF_BOOK_SPREAD"),
    "TICK_SIZE_MIN_ORDER": ("CURRENT_ORDER_MIN_SIZE", "CURRENT_ORDER_PRICE_MIN_TICK_SIZE", "V3_TICK_SIZE_CHANGE_HISTORY"),
}

ACCRUAL_ERROR_CODES = (
    "ACCRUAL_INPUT_INVALID",
    "PLAN_FREEZE_INVALID",
    "LEDGER_CHAIN_INVALID",
    "MEMBERSHIP_REPRODUCTION_FAILED",
    "VISIBLE_SCHEMA_VIOLATION",
)

_RAIN_QUESTION_RE = re.compile(r"Will it rain in .+ on .+\?")
_SHA_RE = re.compile(r"^[0-9a-f]{64}$")


class AccrualError(ValueError):
    """Closed, no-echo rejection. ``str(error)`` is exactly the closed code."""

    def __init__(self, code: str) -> None:
        if code not in ACCRUAL_ERROR_CODES:
            code = "ACCRUAL_INPUT_INVALID"
        super().__init__(code)
        self.code = code


# ── Canonical JSON, decimals and time ─────────────────────────────────────────


def canonical_json_bytes(value: object) -> bytes:
    try:
        return qd.canonical_json_bytes(value)
    except qd.ReadinessError:
        raise AccrualError("ACCRUAL_INPUT_INVALID") from None


def content_id(prefix: str, value: object) -> str:
    return prefix + hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def parse_utc(text: object) -> datetime:
    try:
        return qd.parse_utc(text)
    except qd.ReadinessError:
        raise AccrualError("ACCRUAL_INPUT_INVALID") from None


def utc_text(moment: datetime) -> str:
    return qd.utc_text(moment)


def canonical_decimal(value: Decimal) -> str:
    """Plain (never exponent) decimal text without trailing zeros; ``0`` for zero."""

    if not isinstance(value, Decimal) or not value.is_finite():
        raise AccrualError("ACCRUAL_INPUT_INVALID")
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    if text in ("", "-0"):
        text = "0"
    return text


def _decimal(text: object) -> Decimal:
    if not isinstance(text, str) or not re.fullmatch(r"-?\d+(\.\d+)?", text):
        raise AccrualError("ACCRUAL_INPUT_INVALID")
    try:
        return Decimal(text)
    except InvalidOperation:
        raise AccrualError("ACCRUAL_INPUT_INVALID") from None


def sha256_lf(data: bytes) -> str:
    return hashlib.sha256(data.replace(b"\r\n", b"\n")).hexdigest()


# ── PLAN-01 binding (zero network) ────────────────────────────────────────────


def _require(condition: object) -> None:
    if not condition:
        raise AccrualError("PLAN_FREEZE_INVALID")


def verify_plan_binding(plan_bytes: bytes, power_bytes: bytes) -> dict[str, object]:
    """Verify the exact merged PLAN-01 bytes and every literal DATA-03 depends on."""

    _require(isinstance(plan_bytes, bytes) and hashlib.sha256(plan_bytes).hexdigest() == PLAN_SHA256)
    _require(isinstance(power_bytes, bytes) and sha256_lf(power_bytes) == POWER_DOC_SHA256_LF)
    try:
        plan = json.loads(plan_bytes.decode("utf-8"))
        seal = plan["prospective_data_seal"]
        eligibility = seal["eligibility"]
        membership = seal["membership_seal"]
        split = plan["dataset_split_plan"]
        corpus = plan["lineage"]["historical_corpus"]
        parameters = plan["wp170_handoff"]["parameters"]
        power = plan["sample_power_plan"]
        q_def = plan["feature_plan"]["feature_definitions"]["wx.ndfd_pop12_max_climate_day_v1"]
        label = plan["label_plan"]
    except (ValueError, KeyError, TypeError, UnicodeDecodeError):
        raise AccrualError("PLAN_FREEZE_INVALID") from None
    _require(plan.get("wp_id") == "S10-QUAL-PLAN-01")
    _require(seal.get("oos_start") == OOS_START and seal.get("cap") == CAP and seal.get("freeze_deadline") == FREEZE_DEADLINE)
    _require(eligibility.get("row_decision_time_lower_bound") == OOS_START)
    _require(eligibility.get("row_decision_time_upper_bound_exclusive") == CAP)
    _require(eligibility.get("wp170_embargo_lower_bound") == EMBARGO_LOWER_BOUND)
    _require(eligibility.get("target_effective_dates") == PLAN_TARGET_EFFECTIVE_DATES)
    _require(eligibility.get("pending_state") == PENDING_LABEL_FINALITY)
    _require(eligibility.get("replacement_after_entry") is False)
    _require(tuple(membership.get("preimage_keys", ())) == MEMBERSHIP_PREIMAGE_KEYS)
    _require(tuple(membership.get("oos_exclusion_item_keys", ())) == EXCLUSION_ITEM_KEYS)
    _require(tuple(membership.get("oos_exclusion_subject_kinds", ())) == SUBJECT_KINDS)
    _require(membership.get("id_prefix") == MEMBERSHIP_ID_PREFIX)
    codes = seal.get("exclusion_reason_codes", {})
    _require(tuple(codes.get("market", ())) == MARKET_EXCLUSION_REASONS)
    _require(tuple(codes.get("row", ())) == ROW_EXCLUSION_REASONS)
    _require(tuple(codes.get("date", ())) == DATE_EXCLUSION_REASONS)
    _require(split["candidate_plan"].get("embargo_seconds") == EMBARGO_SECONDS)
    _require(split["candidate_plan"].get("oos_start") == OOS_START)
    _require(split["candidate_plan"].get("min_samples_per_role") == PLAN_MIN_SAMPLES_PER_ROLE)
    _require(split["row_definition"].get("market_history_lookback_seconds") == 86400)
    _require(split["row_definition"].get("ndfd_vintage_lookback_seconds") == 172800)
    _require(tuple(split["row_definition"].get("checkpoints", ())) == CHECKPOINT_IDS)
    _require(corpus.get("bundle_id") == DATA02_BUNDLE_ID and corpus.get("logical_dataset_id") == DATA02_DATASET_ID)
    _require(corpus.get("oos_status") == DATA02_OOS_STATUS and corpus.get("oos_status_permanent") is True)
    _require(parameters.get("b0_rule") == B0_RULE)
    _require(parameters.get("max_midpoint_spread") == canonical_decimal(MAX_MIDPOINT_SPREAD))
    _require(parameters.get("max_last_trade_age_seconds") == MAX_LAST_TRADE_AGE_SECONDS)
    _require(power.get("power_analysis_doc_path") == POWER_DOC_PATH)
    _require(power.get("power_analysis_doc_sha256_lf") == POWER_DOC_SHA256_LF)
    _require((q_def.get("clip_lower"), q_def.get("clip_upper")) == tuple(canonical_decimal(v) for v in Q_CLIP))
    _require(label["candidate_plan"].get("label_ref") == LABEL_REF and label.get("label_resolution_timeout") is False)
    _require(tuple(sorted(plan["feature_plan"]["candidate_plan"]["feature_refs"])) == FEATURE_REFS)
    return {"plan_sha256": PLAN_SHA256, "power_doc_sha256_lf": POWER_DOC_SHA256_LF, "oos_start": OOS_START, "cap": CAP,
            "embargo_lower_bound": EMBARGO_LOWER_BOUND}


def verify_freeze_event(merge_sha: str, parents: Sequence[str], committer: str, committer_time: str) -> dict[str, str]:
    """The PLAN-01 freeze is the GitHub server merge on main at or before the deadline."""

    _require(merge_sha == PLAN_MERGE_SHA and tuple(parents) == PLAN_MERGE_PARENTS)
    _require(committer == PLAN_MERGE_COMMITTER)
    try:  # git %cI carries the committer's local offset; the instant is what binds
        moment = datetime.fromisoformat(committer_time.strip().replace("Z", "+00:00"))
    except (AttributeError, ValueError):
        raise AccrualError("PLAN_FREEZE_INVALID") from None
    _require(moment.tzinfo is not None)
    moment = moment.astimezone(parse_utc(OOS_START).tzinfo)
    _require(utc_text(moment) == PLAN_MERGE_TIME and moment <= parse_utc(FREEZE_DEADLINE))
    return {"plan_merge_sha": PLAN_MERGE_SHA, "plan_merge_time": PLAN_MERGE_TIME, "freeze_deadline": FREEZE_DEADLINE}


# ── Frozen census ─────────────────────────────────────────────────────────────


def scan_days() -> tuple[date, ...]:
    days = (SCAN_END - SCAN_START).days + 1
    return tuple(SCAN_START + timedelta(days=offset) for offset in range(days))


def window_dates() -> tuple[str, ...]:
    """Every target date that can enter this plan (the frozen 120-day scan window)."""

    return tuple(day.isoformat() for day in scan_days())


def discovery_hour(day: date, hh: int) -> str:
    if hh not in DISCOVERY_HOURS_UTC:
        raise AccrualError("ACCRUAL_INPUT_INVALID")
    return f"{day.isoformat()}/{hh:02d}"


def required_discovery_hours(target_day: date) -> tuple[str, ...]:
    """The frozen 11/12 UTC ``new_market`` hours every scan day through ``target_day`` (inclusive)."""

    last = min(target_day, SCAN_END)
    return tuple(discovery_hour(day, hh) for day in scan_days() if day <= last for hh in DISCOVERY_HOURS_UTC)


def census_closed(target_day: date, successful_hours: Sequence[str] | frozenset[str]) -> bool:
    """A target-date census closes only when every required discovery hour through that date was
    successfully read; a failed or unpublished hour never closes it (it stays structural pending)."""

    if target_day < SCAN_START or target_day > SCAN_END:
        return False
    done = set(successful_hours)
    return all(hour in done for hour in required_discovery_hours(target_day))


def is_rain_family_event(event: v3.V3Event) -> bool:
    return ((event.field("slug") or "").startswith("where-will-it-rain-on-")
            or bool(_RAIN_QUESTION_RE.fullmatch(event.field("question") or "")))


@dataclass(frozen=True)
class DateCensus:
    target_date: str
    candidates: tuple[qd.MarketCandidate, ...]
    inconsistent_market_ids: tuple[str, ...]


def assign_census(events_by_hour: Mapping[str, Sequence[v3.V3Event]], target_day: date) -> DateCensus:
    """Markets of one target date: frozen-family witness copies from the census hours of scan days
    ``<= target_day``, collapsed by Gamma market id (earliest receive wins), whose earliest copy's slug
    names ``target_day``. Copies in later hours never move a market's earliest receive."""

    hours = set(required_discovery_hours(target_day))
    events = [e for hour, items in sorted(events_by_hour.items()) if hour in hours for e in items if is_rain_family_event(e)]
    try:
        candidates, inconsistent = qd.candidates_from_new_market(events)
    except qd.ReadinessError:
        raise AccrualError("ACCRUAL_INPUT_INVALID") from None
    chosen = tuple(c for c in candidates if (qd.parse_rain_slug(c.slug) or (None,))[0] == target_day)
    flagged: list[str] = []
    for item in inconsistent:
        copies = v3.order_events([e for e in events if e.market_id == item["market_id"]])
        if copies and (qd.parse_rain_slug(copies[0].field("slug")) or (None,))[0] == target_day:
            flagged.append(item["market_id"])
    return DateCensus(target_day.isoformat(), chosen, tuple(sorted(flagged, key=lambda m: (len(m), m))))


# ── Row identity and exclusion subjects ───────────────────────────────────────


def prospective_row_id(*, target_date: str, market_id: str, condition_id: str, checkpoint_id: str,
                       decision_time: str, yes_token_id: str) -> str:
    """Label-free, value-free row identity over exactly the six frozen fields."""

    if checkpoint_id not in CHECKPOINT_IDS:
        raise AccrualError("ACCRUAL_INPUT_INVALID")
    date.fromisoformat(target_date)
    body = {
        "target_date": target_date,
        "market_id": market_id,
        "condition_id": condition_id,
        "checkpoint_id": checkpoint_id,
        "decision_time": utc_text(parse_utc(decision_time)),
        "yes_token_id": yes_token_id,
    }
    if not all(isinstance(v, str) and v for v in body.values()):
        raise AccrualError("ACCRUAL_INPUT_INVALID")
    return content_id(ROW_ID_PREFIX, body)


def row_subject_id(market_id: str, checkpoint_id: str) -> str:
    if checkpoint_id not in CHECKPOINT_IDS:
        raise AccrualError("ACCRUAL_INPUT_INVALID")
    return f"{market_id}:{checkpoint_id}"


def oos_exclusion(target_date: str, subject_kind: str, subject_id: str, reason_code: str) -> dict[str, str]:
    vocab = {"DATE": DATE_EXCLUSION_REASONS, "MARKET": MARKET_EXCLUSION_REASONS, "ROW": ROW_EXCLUSION_REASONS}
    if subject_kind not in vocab or reason_code not in vocab[subject_kind] or reason_code in NEVER_MINTED_REASONS:
        raise AccrualError("ACCRUAL_INPUT_INVALID")
    if subject_kind == "DATE" and subject_id != target_date:
        raise AccrualError("ACCRUAL_INPUT_INVALID")
    return {"target_date": target_date, "subject_kind": subject_kind, "subject_id": subject_id, "reason_code": reason_code}


def _exclusion_key(item: Mapping[str, str]) -> tuple[str, str, str]:
    return (item["target_date"], item["subject_kind"], item["subject_id"])


# ── B0 and feature materialization (sealed values) ────────────────────────────


@dataclass(frozen=True)
class B0Result:
    available: bool
    basis: str | None
    value: str | None


def materialize_b0(history: Mapping[str, object], decision_time: datetime) -> B0Result:
    """EXTERNAL_PIT_MARKET_PROBABILITY_V1 (spread 0.1, trade age 86400 s by ``timestamp_received``).

    The spread is recomputed from bid/ask (a source spread field is never trusted). A valid
    two-sided Yes book (``0 < bid <= ask < 1``) with spread ``<= 0.1`` yields the midpoint;
    otherwise the latest successfully searched Yes-token trade aged ``<= 86400`` s; an incomplete
    required trade search after a source-read failure is ``MARKET_HISTORY_SOURCE_INVALID``; a
    complete search with no eligible book/trade is ``B0_UNAVAILABLE`` (returned unavailable).
    """

    bba = history.get("best_bid_ask")
    if not isinstance(bba, Mapping):
        raise AccrualError("ACCRUAL_INPUT_INVALID")
    for event in (bba, history.get("last_trade_price")):
        if isinstance(event, Mapping) and parse_utc(event.get("timestamp_received")) > decision_time:
            raise AccrualError("ACCRUAL_INPUT_INVALID")  # look-ahead
    bid_text, ask_text = bba.get("best_bid"), bba.get("best_ask")
    if isinstance(bid_text, str) and isinstance(ask_text, str):
        bid, ask = _decimal(bid_text), _decimal(ask_text)
        if Decimal(0) < bid <= ask < Decimal(1) and ask - bid <= MAX_MIDPOINT_SPREAD:
            return B0Result(True, B0_BASIS_MIDPOINT, canonical_decimal((bid + ask) / 2))
    trade = history.get("last_trade_price")
    if isinstance(trade, Mapping):
        price = _decimal(trade.get("price"))
        age = decision_time - parse_utc(trade.get("timestamp_received"))
        if Decimal(0) <= price <= Decimal(1) and timedelta(0) <= age <= timedelta(seconds=MAX_LAST_TRADE_AGE_SECONDS):
            return B0Result(True, B0_BASIS_TRADE, canonical_decimal(price))
    if history.get("last_trade_price_state") == LTP_STATE_SEARCH_INCOMPLETE:
        raise qd.RuleExclusion("MARKET_HISTORY_SOURCE_INVALID")
    return B0Result(False, None, None)


def materialize_q(weather: Mapping[str, object]) -> str:
    """q = clip(max overlapping PoP12_percent / 100, 0.01, 0.99) as a canonical decimal string."""

    periods = weather.get("periods")
    if not isinstance(periods, list) or not periods:
        raise AccrualError("ACCRUAL_INPUT_INVALID")
    values = [p.get("pop12_percent") for p in periods if isinstance(p, Mapping)]
    if len(values) != len(periods) or not all(type(v) is int and 0 <= v <= 100 for v in values):
        raise AccrualError("ACCRUAL_INPUT_INVALID")
    q = Decimal(max(values)) / Decimal(100)
    return canonical_decimal(min(max(q, Q_CLIP[0]), Q_CLIP[1]))


def materialize_l(weather: Mapping[str, object]) -> tuple[str, str]:
    """L = (climate_day_start - vintage_public_available_time) / 24 h: the exact signed second count
    (microsecond resolution) and its quotient rounded half-even to 1e-12 days; L may be negative."""

    delta = parse_utc(weather.get("climate_day_start")) - parse_utc(weather.get("public_available_time"))
    micros = (delta.days * 86400 + delta.seconds) * 1_000_000 + delta.microseconds
    seconds = Decimal(micros) / Decimal(1_000_000)
    days = (seconds / Decimal(86400)).quantize(L_QUANTUM, rounding=ROUND_HALF_EVEN)
    return canonical_decimal(seconds), canonical_decimal(days)


# ── Stable chronological prefix and seal decision ─────────────────────────────


@dataclass(frozen=True)
class PrefixState:
    eligible_dates: tuple[str, ...]
    earliest_pending_date: str | None
    pending_dates: int
    complete: bool
    window_terminal: bool


def stable_prefix(date_states: Mapping[str, str], window: Sequence[str] | None = None) -> PrefixState:
    """Walk the considered window ascending: PENDING stops the walk (never leapfrogged), EXCLUDED is
    skipped, ELIGIBLE counts. Dates after D50 never affect the prefix."""

    ordered = tuple(window if window is not None else window_dates())
    if list(ordered) != sorted(set(ordered)) or len(ordered) > MAX_CONSIDERED_TARGET_DATES:
        raise AccrualError("ACCRUAL_INPUT_INVALID")
    eligible: list[str] = []
    first_pending: str | None = None
    for day in ordered:
        state = date_states.get(day, DATE_PENDING)
        if state not in (DATE_ELIGIBLE, DATE_EXCLUDED, DATE_PENDING):
            raise AccrualError("ACCRUAL_INPUT_INVALID")
        if state == DATE_PENDING:
            first_pending = day
            break
        if state == DATE_ELIGIBLE:
            eligible.append(day)
            if len(eligible) == TARGET_EFFECTIVE_DATES:
                break
    pending = sum(1 for day in ordered if date_states.get(day, DATE_PENDING) == DATE_PENDING)
    complete = len(eligible) == TARGET_EFFECTIVE_DATES
    return PrefixState(tuple(eligible), first_pending, pending, complete, first_pending is None and not complete)


def seal_decision(prefix: PrefixState, rows_by_date: Mapping[str, Sequence[str]]) -> str:
    """Mechanical seal outcome: sealed / rows-insufficient for a stable 50-date prefix,
    insufficient-at-cap only when the whole in-window population is terminal, else not sealable."""

    if prefix.complete:
        rows = sum(len(rows_by_date.get(day, ())) for day in prefix.eligible_dates)
        return STATE_SEALED if rows >= MIN_OOS_ROWS else STATE_ROWS_INSUFFICIENT
    if prefix.window_terminal:
        return STATE_INSUFFICIENT_AT_CAP
    return SEAL_NOT_READY


def classify_date(target_date: str, row_decision_times: Mapping[str, str]) -> tuple[str, str | None]:
    """Date-level classification of a terminally classified date from its included (eligible) rows
    (one closed reason; precedence before-start, embargo, cap, no-eligible-row)."""

    if not row_decision_times:
        return DATE_EXCLUDED, "OOS_DATE_NO_ELIGIBLE_ROW"
    times = [parse_utc(t) for t in row_decision_times.values()]
    if any(t < parse_utc(OOS_START) for t in times):
        return DATE_EXCLUDED, "OOS_DATE_DECISION_BEFORE_START"
    if any(t < parse_utc(OOS_START) + timedelta(seconds=EMBARGO_SECONDS) for t in times):
        return DATE_EXCLUDED, "OOS_DATE_DECISION_IN_WP170_EMBARGO"
    if any(t >= parse_utc(CAP) for t in times):
        return DATE_EXCLUDED, "OOS_DATE_DECISION_AT_OR_AFTER_CAP"
    return DATE_ELIGIBLE, None


def mr09_end_time(row_decision_times: Sequence[str]) -> str:
    """MR09: maximum OOS row decision_time truncated to the whole UTC second, plus one second."""

    if not row_decision_times:
        raise AccrualError("ACCRUAL_INPUT_INVALID")
    latest = max(parse_utc(t) for t in row_decision_times).replace(microsecond=0)
    return utc_text(latest + timedelta(seconds=1))


# ── Ledger (hash-chained, label-free) and sealed records ──────────────────────


def chain_entry(prev: str, body: Mapping[str, object]) -> dict[str, object]:
    if "entry_hash" in body or "prev" in body:
        raise AccrualError("ACCRUAL_INPUT_INVALID")
    record = {"prev": prev, **body}
    return {**record, "entry_hash": content_id(LEDGER_ENTRY_PREFIX, record)}


def verify_chain(entries: Sequence[Mapping[str, object]], prefix: str = LEDGER_ENTRY_PREFIX) -> str:
    """Return the chain head; any reordering, deletion or mutation is LEDGER_CHAIN_INVALID."""

    previous = LEDGER_GENESIS
    for entry in entries:
        if not isinstance(entry, Mapping) or entry.get("prev") != previous:
            raise AccrualError("LEDGER_CHAIN_INVALID")
        body = {k: v for k, v in entry.items() if k != "entry_hash"}
        if entry.get("entry_hash") != content_id(prefix, body):
            raise AccrualError("LEDGER_CHAIN_INVALID")
        previous = str(entry["entry_hash"])
    return previous


def chain_append(entries: Sequence[Mapping[str, object]], bodies: Sequence[Mapping[str, object]],
                 prefix: str = LEDGER_ENTRY_PREFIX) -> list[dict[str, object]]:
    head = verify_chain(entries, prefix)
    out = [dict(e) for e in entries]
    for body in bodies:
        if "entry_hash" in body or "prev" in body:
            raise AccrualError("ACCRUAL_INPUT_INVALID")
        record = {"prev": head, **body}
        entry = {**record, "entry_hash": content_id(prefix, record)}
        out.append(entry)
        head = str(entry["entry_hash"])
    return out


def assert_terminal_entries_unchanged(previous: Sequence[Mapping[str, object]], current: Sequence[Mapping[str, object]]) -> None:
    """Committed terminal entries are immutable: the new chain must extend the old one byte-exactly."""

    if len(current) < len(previous) or any(canonical_json_bytes(a) != canonical_json_bytes(b)
                                           for a, b in zip(previous, current)):
        raise AccrualError("LEDGER_CHAIN_INVALID")


# ── Feature-column, label-store, bundle and membership identities ─────────────


def feature_column_id(feature_ref: str, values_by_row: Mapping[str, str]) -> str:
    if feature_ref not in FEATURE_REFS or not values_by_row:
        raise AccrualError("ACCRUAL_INPUT_INVALID")
    return content_id(FEATURE_COLUMN_ID_PREFIX, {"feature_ref": feature_ref,
                                                  "values": [[r, values_by_row[r]] for r in sorted(values_by_row)]})


def label_store_id(labels_by_row: Mapping[str, Mapping[str, object]]) -> str:
    if not labels_by_row:
        raise AccrualError("ACCRUAL_INPUT_INVALID")
    return content_id(LABEL_STORE_ID_PREFIX, {"label_ref": LABEL_REF,
                                               "labels": [[r, dict(labels_by_row[r])] for r in sorted(labels_by_row)]})


def build_data03_bundle(*, ledger_head: str, oos_target_dates: Sequence[str], oos_row_ids: Sequence[str],
                        oos_exclusions: Sequence[Mapping[str, str]], provenance_manifest_ids: Sequence[str],
                        execution_evidence: Mapping[str, Mapping[str, object]], raw_index_sha256: str,
                        terminal: str) -> dict[str, object]:
    """Structural DATA-03 bundle (value-free): sealed values are bound through the raw evidence and
    the ledger chain, and their feature-column / label-store ids live only in the sealed store."""

    if terminal not in FINAL_STATES or not _SHA_RE.fullmatch(raw_index_sha256):
        raise AccrualError("ACCRUAL_INPUT_INVALID")
    body = {
        "schema_id": "weather-qualification-oos-accrual-bundle",
        "schema_version": "1.0.0",
        "wp_id": WP_ID,
        "plan_01_plan_sha256": PLAN_SHA256,
        "plan_01_merge_sha": PLAN_MERGE_SHA,
        "data02_bundle_id": DATA02_BUNDLE_ID,
        "data02_oos_status": DATA02_OOS_STATUS,
        "ledger_head": ledger_head,
        "raw_index_sha256": raw_index_sha256,
        "oos_target_dates": list(oos_target_dates),
        "oos_row_ids": sorted(oos_row_ids),
        "oos_exclusions": sorted((dict(e) for e in oos_exclusions), key=_exclusion_key),
        "provenance_manifest_ids": sorted(provenance_manifest_ids),
        "execution_evidence": {k: dict(execution_evidence[k]) for k in sorted(execution_evidence)},
        "feature_refs": list(FEATURE_REFS),
        "label_ref": LABEL_REF,
        "terminal": terminal,
    }
    return {"bundle_id": content_id(BUNDLE_ID_PREFIX, body), **body}


def build_membership_preimage(*, data03_bundle_id: str, oos_target_dates: Sequence[str],
                              row_decision_times: Mapping[str, str],
                              oos_exclusions: Sequence[Mapping[str, str]]) -> dict[str, object]:
    preimage = {
        "plan_01_plan_sha256": PLAN_SHA256,
        "oos_start": OOS_START,
        "cap": CAP,
        "end_time": mr09_end_time(list(row_decision_times.values())),
        "oos_target_dates": list(oos_target_dates),
        "oos_row_ids": sorted(row_decision_times),
        "oos_exclusions": sorted((dict(e) for e in oos_exclusions), key=_exclusion_key),
        "data03_bundle_id": data03_bundle_id,
    }
    validate_membership_preimage(preimage)
    return preimage


def membership_id(preimage: Mapping[str, object]) -> str:
    validate_membership_preimage(preimage)
    return content_id(MEMBERSHIP_ID_PREFIX, dict(preimage))


def validate_membership_preimage(preimage: Mapping[str, object]) -> None:
    """Closed keys, exact ordering, uniqueness, frozen literals and vocabularies."""

    def need(condition: object) -> None:
        if not condition:
            raise AccrualError("MEMBERSHIP_REPRODUCTION_FAILED")

    need(isinstance(preimage, Mapping) and tuple(sorted(preimage)) == MEMBERSHIP_PREIMAGE_KEYS)
    need(preimage["plan_01_plan_sha256"] == PLAN_SHA256 and preimage["oos_start"] == OOS_START and preimage["cap"] == CAP)
    bundle = preimage["data03_bundle_id"]
    need(isinstance(bundle, str) and bundle.startswith(BUNDLE_ID_PREFIX) and _SHA_RE.fullmatch(bundle[len(BUNDLE_ID_PREFIX):]))
    dates = preimage["oos_target_dates"]
    need(isinstance(dates, list) and len(dates) == TARGET_EFFECTIVE_DATES and dates == sorted(set(dates)))
    need(all(isinstance(d, str) and d in window_dates() for d in dates))
    rows = preimage["oos_row_ids"]
    need(isinstance(rows, list) and rows and rows == sorted(set(rows)))
    need(all(isinstance(r, str) and r.startswith(ROW_ID_PREFIX) and _SHA_RE.fullmatch(r[len(ROW_ID_PREFIX):]) for r in rows))
    exclusions = preimage["oos_exclusions"]
    need(isinstance(exclusions, list))
    keys = []
    for item in exclusions:
        need(isinstance(item, Mapping) and tuple(sorted(item)) == EXCLUSION_ITEM_KEYS)
        try:
            oos_exclusion(item["target_date"], item["subject_kind"], item["subject_id"], item["reason_code"])
        except AccrualError:
            raise AccrualError("MEMBERSHIP_REPRODUCTION_FAILED") from None
        # Scope: considered dates from the first through D50; an entered date is never date-excluded.
        need(item["target_date"] in window_dates() and item["target_date"] <= dates[-1])
        need(not (item["subject_kind"] == "DATE" and item["target_date"] in dates))
        keys.append(_exclusion_key(item))
    need(keys == sorted(set(keys)))
    end = preimage["end_time"]
    need(isinstance(end, str) and parse_utc(end) <= parse_utc(CAP) + timedelta(seconds=1))


def expected_membership(date_entries: Sequence[Mapping[str, object]], prefix: PrefixState,
                        data03_bundle_id: str) -> dict[str, object]:
    """Re-derive the membership preimage from the committed date entries (zero network)."""

    if not prefix.complete:
        raise AccrualError("MEMBERSHIP_REPRODUCTION_FAILED")
    by_date = {str(e["target_date"]): e for e in date_entries}
    last = prefix.eligible_dates[-1]
    times: dict[str, str] = {}
    exclusions: list[dict[str, str]] = []
    for day in window_dates():
        if day > last:
            break
        entry = by_date.get(day)
        if entry is None or entry.get("classification") not in (DATE_ELIGIBLE, DATE_EXCLUDED):
            raise AccrualError("MEMBERSHIP_REPRODUCTION_FAILED")
        exclusions.extend(dict(x) for x in entry["exclusions"])  # type: ignore[union-attr]
        if day in prefix.eligible_dates:
            times.update(entry["row_decision_times"])  # type: ignore[arg-type]
    return build_membership_preimage(data03_bundle_id=data03_bundle_id, oos_target_dates=prefix.eligible_dates,
                                     row_decision_times=times, oos_exclusions=exclusions)


def verify_membership(stored: Mapping[str, object], date_entries: Sequence[Mapping[str, object]],
                      prefix: PrefixState, data03_bundle_id: str) -> str:
    expected = expected_membership(date_entries, prefix, data03_bundle_id)
    if not isinstance(stored, Mapping) or canonical_json_bytes(dict(stored.get("preimage", {}))) != canonical_json_bytes(expected):
        raise AccrualError("MEMBERSHIP_REPRODUCTION_FAILED")
    identity = membership_id(expected)
    if stored.get("oos_membership_id") != identity:
        raise AccrualError("MEMBERSHIP_REPRODUCTION_FAILED")
    return identity


def mr15_prospective_sample_ids(preimage: Mapping[str, object]) -> tuple[str, ...]:
    """MR15 prospective contribution: exactly the sealed ``oos_row_ids`` (never an excluded-date,
    post-D50 or pre-start row); the DATA-02 FORMATION/SELECTION rows are added by REAL-01."""

    validate_membership_preimage(preimage)
    return tuple(preimage["oos_row_ids"])  # type: ignore[arg-type]


# ── Provenance ceiling ────────────────────────────────────────────────────────


def historical_n2(bundle: Mapping[str, object], *, bundle_id: str = DATA02_BUNDLE_ID,
                  dataset_id: str = DATA02_DATASET_ID) -> tuple[int, tuple[str, ...]]:
    """N2: DATA-02 ready manifests required by the MR14 FORMATION/SELECTION rows (dates with at
    least one evidence-complete row whose external B0 and both B1 features are available)."""

    try:
        qd.verify_bundle(bundle)
    except qd.ReadinessError:
        raise AccrualError("PLAN_FREEZE_INVALID") from None
    if bundle.get("bundle_id") != bundle_id or bundle.get("logical_dataset_id") != dataset_id:
        raise AccrualError("PLAN_FREEZE_INVALID")
    eligible: set[str] = set()
    manifests_by_date: dict[str, set[str]] = {}
    for row in bundle["rows"]:  # type: ignore[union-attr]
        day = str(row["target_date"])
        manifests_by_date.setdefault(day, set()).update(row["provenance_manifest_ids"])
        try:
            decision = parse_utc(row["checkpoint_time"])
            b0 = materialize_b0(row["feature_evidence"]["market_history"], decision)
            weather = row["feature_evidence"]["weather"]
            materialize_q(weather)
            materialize_l(weather)
        except qd.RuleExclusion:
            continue  # a closed source-invalid row is genuinely ineligible
        except (AccrualError, KeyError, TypeError):
            raise AccrualError("PLAN_FREEZE_INVALID") from None  # never undercount N2 on an unreadable row
        if b0.available:
            eligible.add(day)
    dates = tuple(sorted(eligible))
    return len({m for day in dates for m in manifests_by_date[day]}), dates


def provenance_pre_gate(n2: int) -> bool:
    return n2 + PROSPECTIVE_MANIFEST_RESERVE <= MAX_QUALIFICATION_PROVENANCE_MANIFESTS


def projected_manifest_count(n2: int, prefix_manifest_counts: Sequence[int]) -> int:
    """N2 + actual manifests of the stable-prefix dates + the frozen minimum for the remaining dates."""

    taken = list(prefix_manifest_counts)[:TARGET_EFFECTIVE_DATES]
    return n2 + sum(taken) + MANIFESTS_PER_DATE_MINIMUM * (TARGET_EFFECTIVE_DATES - len(taken))


# ── MR12 execution evidence (current, never backdated) ────────────────────────


def capture_id(key: str, sha256: str, run: int, captured_at: str) -> str:
    return content_id(CAPTURE_ID_PREFIX, {"key": key, "sha256": sha256, "run": run, "captured_at": captured_at})


def fee_document_valid(url: str, status: int, body: bytes) -> bool:
    """Source contract of the frozen official fee page: the exact URL, HTTP 200, a decodable HTML
    document that names trading fees and the weather category."""

    if url != FEE_DOC_URL or status != 200 or not body or len(body) > 8 * 1024 * 1024:
        return False
    try:
        text = body.decode("utf-8").lower()
    except UnicodeDecodeError:
        return False
    return "<html" in text and "fee" in text and "weather" in text


def classify_execution_evidence(markets: Sequence[Mapping[str, object]], fee_captures: Sequence[Mapping[str, object]],
                                cutoff: datetime, oos_rows_with_spread: int, oos_rows: int) -> dict[str, dict[str, object]]:
    """MR12 over the D1..D50 markets: AVAILABLE iff every required capture of a class meets the
    criteria, PARTIAL iff some do, MISSING iff none do. Captures after ``cutoff`` never count
    (current evidence is never backdated); evidence ids are the sorted qualifying capture ids."""

    def usable(capture: Mapping[str, object]) -> bool:
        return parse_utc(capture["captured_at"]) <= cutoff

    fee_ok = sorted(str(c["capture_id"]) for c in fee_captures
                    if usable(c) and c.get("url") == FEE_DOC_URL and c.get("contract_valid") is True)
    cohorts: dict[str, list[str]] = {}
    per_market: list[dict[str, object]] = []
    for market in markets:
        captures = [c for c in market["gamma_captures"] if usable(c)]  # type: ignore[union-attr]
        cohort = market.get("rule_cohort_id")
        for c in captures:
            if c.get("pre_close") is True and c.get("parsed_rule_cohort_id") is not None:
                cohorts.setdefault(str(c["parsed_rule_cohort_id"]), []).append(str(c["capture_id"]))
        per_market.append({
            "cohort": cohort,
            "fees": [str(c["capture_id"]) for c in captures if c.get("fees_enabled_known") is True],
            "tick": [str(c["capture_id"]) for c in captures if c.get("tick_known") is True],
            "min_size": [str(c["capture_id"]) for c in captures if c.get("min_size_known") is True],
            "tick_history_complete": market.get("tick_history_complete") is True,
            "tick_history_ids": list(market.get("tick_history_capture_ids", [])),  # type: ignore[arg-type]
        })
    have_markets = bool(per_market)
    market_cohorts = {str(m["cohort"]) for m in per_market if m["cohort"] is not None}
    cohorts_open = have_markets and all(m["cohort"] is not None for m in per_market) and market_cohorts <= set(cohorts)
    open_ids = sorted({i for cohort in market_cohorts for i in cohorts.get(cohort, [])})
    every = lambda field: have_markets and all(m[field] for m in per_market)  # noqa: E731
    pick = lambda field: sorted({i for m in per_market for i in m[field]})  # type: ignore[union-attr]  # noqa: E731
    criteria: dict[str, dict[str, tuple[bool, list[str]]]] = {
        "FEES": {
            "OFFICIAL_FEE_DOCUMENTATION": (bool(fee_ok), fee_ok[-1:]),
            "CURRENT_OPEN_DAILY_RAIN_GAMMA_MARKET_DOCUMENTS": (cohorts_open and every("fees"), open_ids + pick("fees")),
        },
        "RESOLUTION_RULES": {
            "CURRENT_OPEN_DAILY_RAIN_GAMMA_MARKET_DOCUMENTS": (cohorts_open, open_ids),
            "CURRENT_RESOLUTION_RULE_TEXT_AND_COHORT_SEMANTICS": (cohorts_open, open_ids),
        },
        "TICK_SIZE_MIN_ORDER": {
            "CURRENT_ORDER_MIN_SIZE": (every("min_size"), pick("min_size")),
            "CURRENT_ORDER_PRICE_MIN_TICK_SIZE": (every("tick"), pick("tick")),
            "V3_TICK_SIZE_CHANGE_HISTORY": (have_markets and all(m["tick_history_complete"] for m in per_market),
                                            pick("tick_history_ids")),
        },
        "SPREAD_DEPTH": {
            "DECISION_TIME_ORDER_BOOK_DEPTH": (False, []),
            "DECISION_TIME_TOP_OF_BOOK_SPREAD": (oos_rows > 0 and oos_rows_with_spread == oos_rows, []),
        },
        "LATENCY": {"ORDER_PLACEMENT_LATENCY_MEASUREMENT": (False, [])},
        "PARTIAL_FILL": {"FILL_RATE_EVIDENCE": (False, [])},
    }
    result: dict[str, dict[str, object]] = {}
    for cls in EXECUTION_CLASSES:
        items = criteria[cls]
        if sorted(items) != sorted(EXECUTION_REQUIRED_CAPTURES[cls]):
            raise AccrualError("ACCRUAL_INPUT_INVALID")
        met = [name for name, (ok, _ids) in items.items() if ok]
        state = "AVAILABLE" if len(met) == len(items) else ("PARTIAL" if met else "MISSING")
        ids = sorted({i for name in met for i in items[name][1]})
        result[cls] = {
            "state": state,
            "required_captures": {name: ok for name, (ok, _ids) in sorted(items.items())},
            "evidence_reference_ids": [] if state == "MISSING" else ids,
            "basis": "CURRENT_CAPTURE_NOT_HISTORICAL",
        }
    result["TICK_SIZE_MIN_ORDER"]["official_tick_change_semantics"] = "NOT_CAPTURED_NO_AUTHORIZED_EXACT_SOURCE"
    return result


# ── Visible-report firewall (closed schemas, closed string shapes) ────────────

_ID_PATTERN = r"[a-z0-9]+:sha256:[0-9a-f]{64}"
_STRING_SHAPES = {
    "kind": r"PREPARE|PROBE|ACCRUE|SEAL|VERIFY_FINAL",
    "wp": re.escape(WP_ID),
    "state": "|".join((*STATES, SEAL_NOT_READY)),
    "status": r"PREPARED|PREPARED_IDEMPOTENT|PROBE_PASS|ACCRUED|SEALED|VERIFIED",
    "sha": r"[0-9a-f]{64}",
    "gitsha": r"[0-9a-f]{40}",
    "id": _ID_PATTERN,
    "utc": r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z",
    "date": r"\d{4}-\d{2}-\d{2}",
    "exec_state": "|".join(EXECUTION_STATES),
    "probe_check": r"PASS|FIRST_PUBLISHED_FINAL|LATEST_BEFORE_2359_ET|LAST_BEFORE_1400_ET",
    "budget": r"[A-Z_]{1,64}",
    "ledger_head": rf"{_ID_PATTERN}|{LEDGER_GENESIS}",
}
_COUNT = "int"
_COUNTS_BY_REASON = ("map", tuple(MARKET_EXCLUSION_REASONS + ROW_EXCLUSION_REASONS + DATE_EXCLUSION_REASONS), _COUNT)
_BY_CHECKPOINT = ("map", tuple(CHECKPOINT_IDS), _COUNT)
_NETWORK = {
    "attempts": _COUNT, "bytes": _COUNT, "retries": _COUNT, "throttle_retries": _COUNT, "transport_retries": _COUNT,
    "backoff_seconds": _COUNT, "max_single_response": _COUNT, "refusals": _COUNT, "pendulumflow_hours": _COUNT,
    "attempts_by_host": ("map", ("archive.pendulumflow.com", "noaa-ndfd-pds.s3.amazonaws.com", "gamma-api.polymarket.com",
                                 "api.weather.gov", FEE_DOC_HOST), _COUNT),
    "statuses": ("map", r"\d{3}|TRANSPORT_ERROR", _COUNT),
    "artifacts_reused": _COUNT, "artifacts_new": _COUNT, "failed_reads": _COUNT,
}
_EXEC_STATES = ("map", EXECUTION_CLASSES, ("str", "exec_state"))
VISIBLE_SCHEMAS: dict[str, dict[str, object]] = {
    "PREPARE": {
        "kind": ("str", "kind"), "wp_id": ("str", "wp"), "status": ("str", "status"), "state": ("str", "state"),
        "plan_sha256": ("str", "sha"), "plan_merge_sha": ("str", "gitsha"), "plan_merge_time": ("str", "utc"),
        "repo_code_identity": ("str", "gitsha"), "workspace_plan_sha256": ("str", "sha"),
        "data02_bundle_id": ("str", "id"), "data02_dataset_id": ("str", "id"), "data02_eligible_dates": _COUNT,
        "n2": _COUNT, "n2_plus_reserve": _COUNT, "provenance_ceiling": _COUNT, "provenance_pre_gate": "bool",
    },
    "PROBE": {
        "kind": ("str", "kind"), "wp_id": ("str", "wp"), "status": ("str", "status"), "plan_sha256": ("str", "sha"),
        "checks": ("map", ("fee_document", "pendulumflow_audit", "pendulumflow_discovery", "gamma_identity",
                           "rule_semantics", "nws_station", "pendulumflow_targeted_read", "ndfd_listing_object"),
                   ("str", "probe_check")),
        "network": dict(_NETWORK),
        "oos_or_prospective_data_created": "bool",
    },
    "ACCRUE": {
        "kind": ("str", "kind"), "wp_id": ("str", "wp"), "status": ("str", "status"), "state": ("str", "state"),
        "run": _COUNT, "resumed": "bool", "as_of": ("str", "utc"), "plan_sha256": ("str", "sha"),
        "workspace_plan_sha256": ("str", "sha"), "ledger_entries": _COUNT,
        "budget_exhausted": ("opt", ("str", "budget")),
        "counts": {
            "discovered_markets": _COUNT, "outside_window_markets": _COUNT, "terminal_markets": _COUNT,
            "terminal_dates": _COUNT, "eligible_dates": _COUNT, "discovery_hours_read": _COUNT,
            "discovery_hours_pending": _COUNT,
            "date_exclusions_by_reason": _COUNTS_BY_REASON, "market_exclusions_by_reason": _COUNTS_BY_REASON,
            "row_exclusions_by_reason": ("map", tuple(CHECKPOINT_IDS), _COUNTS_BY_REASON),
            "eligible_rows_by_checkpoint": _BY_CHECKPOINT, "eligible_dates_by_checkpoint": _BY_CHECKPOINT,
            "b0_available": _COUNT, "b0_unavailable": _COUNT, "b0_basis": ("map", B0_BASES, _COUNT),
            "coverage_classes": ("map", tuple(v3.COVERAGE_CLASSES) + ("UNCLASSIFIED",), _COUNT),
        },
        "prefix": {
            "length": _COUNT, "target": _COUNT, "earliest_pending_date": ("opt", ("str", "date")),
            "pending_dates": _COUNT, "pending_markets": _COUNT, "seal_decision": ("str", "state"),
        },
        "provenance": {"n2": _COUNT, "prefix_manifests": _COUNT, "projected_final_manifests": _COUNT, "ceiling": _COUNT},
        "execution_evidence_states": _EXEC_STATES,
        "network": {"run": dict(_NETWORK), "cumulative": dict(_NETWORK)},
    },
    "SEAL": {
        "kind": ("str", "kind"), "wp_id": ("str", "wp"), "status": ("str", "status"), "state": ("str", "state"),
        "plan_sha256": ("str", "sha"), "ledger_head": ("str", "ledger_head"),
        "oos_membership_id": ("opt", ("str", "id")), "data03_bundle_id": ("opt", ("str", "id")),
        "oos_target_dates": _COUNT, "oos_rows": _COUNT, "oos_exclusions": _COUNT, "end_time": ("opt", ("str", "utc")),
        "provenance": {"n2": _COUNT, "prospective": _COUNT, "total": _COUNT, "ceiling": _COUNT},
        "execution_evidence_states": _EXEC_STATES,
    },
    "VERIFY_FINAL": {
        "kind": ("str", "kind"), "wp_id": ("str", "wp"), "status": ("str", "status"), "state": ("str", "state"),
        "network_calls": _COUNT, "runs_replayed": _COUNT, "raw_rehashed": _COUNT, "ledger_head": ("str", "ledger_head"),
        "oos_membership_id": ("opt", ("str", "id")), "data03_bundle_id": ("opt", ("str", "id")),
        "plan_sha256": ("str", "sha"), "network": {"cumulative": dict(_NETWORK)},
    },
}


def _validate_value(spec: object, value: object) -> None:
    def fail() -> None:
        raise AccrualError("VISIBLE_SCHEMA_VIOLATION")

    if spec == "int":
        if type(value) is not int or value < 0:
            fail()
    elif spec == "bool":
        if type(value) is not bool:
            fail()
    elif isinstance(spec, dict):
        if not isinstance(value, dict) or set(value) != set(spec):
            fail()
        for key, sub in spec.items():
            _validate_value(sub, value[key])  # type: ignore[index]
    elif isinstance(spec, tuple) and spec[0] == "str":
        if not isinstance(value, str) or not re.fullmatch(_STRING_SHAPES[spec[1]], value):
            fail()
    elif isinstance(spec, tuple) and spec[0] == "opt":
        if value is not None:
            _validate_value(spec[1], value)
    elif isinstance(spec, tuple) and spec[0] == "map":
        if not isinstance(value, dict):
            fail()
        allowed = spec[1]
        for key, item in value.items():  # type: ignore[union-attr]
            if not isinstance(key, str):
                fail()
            if isinstance(allowed, tuple):
                if key not in allowed:
                    fail()
            elif not re.fullmatch(allowed, key):
                fail()
            _validate_value(spec[2], item)
    else:  # pragma: no cover - schema programming error
        fail()


def validate_visible_report(report: Mapping[str, object]) -> dict[str, object]:
    """Allowlisted visible schema: an extra/missing key, an unknown reason key or any string outside
    its closed shape is a hard VISIBLE_SCHEMA_VIOLATION (no label/outcome/value text can pass)."""

    if not isinstance(report, Mapping) or report.get("kind") not in VISIBLE_SCHEMAS:
        raise AccrualError("VISIBLE_SCHEMA_VIOLATION")
    _validate_value(VISIBLE_SCHEMAS[str(report["kind"])], dict(report))
    canonical_json_bytes(dict(report))
    return dict(report)


def _bump(bucket: dict[str, int], key: str) -> None:
    bucket[key] = bucket.get(key, 0) + 1


def structural_counts(market_entries: Sequence[Mapping[str, object]], date_entries: Sequence[Mapping[str, object]],
                      *, discovered_markets: int, outside_window_markets: int, discovery_hours_read: int,
                      discovery_hours_pending: int, coverage_classes: Mapping[str, int]) -> dict[str, object]:
    """Visible counts derived only from structural (label-free, value-free) ledger content."""

    market_reasons: dict[str, int] = {}
    row_reasons: dict[str, dict[str, int]] = {cp: {} for cp in CHECKPOINT_IDS}
    date_reasons: dict[str, int] = {}
    rows_by_cp = {cp: 0 for cp in CHECKPOINT_IDS}
    dates_by_cp: dict[str, set[str]] = {cp: set() for cp in CHECKPOINT_IDS}
    basis: dict[str, int] = {}
    b0_unavailable = 0
    for entry in market_entries:
        if entry.get("market_exclusion"):
            _bump(market_reasons, str(entry["market_exclusion"]))
        for row in entry.get("rows", []):  # type: ignore[union-attr]
            if row.get("b0_basis") in B0_BASES:
                _bump(basis, str(row["b0_basis"]))
            if row.get("reason") == "B0_UNAVAILABLE":
                b0_unavailable += 1
    eligible_dates = 0
    for entry in date_entries:
        if entry.get("classification") == DATE_ELIGIBLE:
            eligible_dates += 1
        elif entry.get("reason"):
            _bump(date_reasons, str(entry["reason"]))
        for item in entry.get("exclusions", []):  # type: ignore[union-attr]
            if item["subject_kind"] == "ROW":
                _bump(row_reasons[str(item["subject_id"]).rsplit(":", 1)[1]], str(item["reason_code"]))
        if entry.get("classification") == DATE_ELIGIBLE:
            for cp, count in entry.get("eligible_rows_by_checkpoint", {}).items():  # type: ignore[union-attr]
                rows_by_cp[cp] += int(count)
                if count:
                    dates_by_cp[cp].add(str(entry["target_date"]))
    return {
        "discovered_markets": discovered_markets,
        "outside_window_markets": outside_window_markets,
        "terminal_markets": len(market_entries),
        "terminal_dates": len(date_entries),
        "eligible_dates": eligible_dates,
        "discovery_hours_read": discovery_hours_read,
        "discovery_hours_pending": discovery_hours_pending,
        "date_exclusions_by_reason": dict(sorted(date_reasons.items())),
        "market_exclusions_by_reason": dict(sorted(market_reasons.items())),
        "row_exclusions_by_reason": {cp: dict(sorted(v.items())) for cp, v in row_reasons.items()},
        "eligible_rows_by_checkpoint": rows_by_cp,
        "eligible_dates_by_checkpoint": {cp: len(v) for cp, v in dates_by_cp.items()},
        "b0_available": sum(basis.values()),
        "b0_unavailable": b0_unavailable,
        "b0_basis": dict(sorted(basis.items())),
        "coverage_classes": dict(sorted(coverage_classes.items())),
    }
