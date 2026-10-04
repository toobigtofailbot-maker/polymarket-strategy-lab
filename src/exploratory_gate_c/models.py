"""Canonical records for the S10-GATE-C-EXPLORE-01 exploratory Gate-C policy-permit core.

Two immutable, closed-schema, content-addressed records live here:

* ``ExploratoryGateCDecision`` -- the canonical hard eligibility decision for one exact
  execution intent (``PERMIT_ELIGIBLE`` or ``PERMIT_REJECTED``);
* ``ExploratoryGateCPermit`` -- a short-lived exact-intent exploratory permit that can be
  derived only from an exact ``PERMIT_ELIGIBLE`` decision.

This module is pure: it performs no network, filesystem, clock or environment access.
Neither record carries credential, signing, order, execution-transport or live authority,
and both fix the later runtime account/access/reconciliation/identity revalidation
requirements to true. Each content id is the SHA-256 of the canonical JSON of every other
top-level field, including the fixed authority/revalidation truths.
"""

from __future__ import annotations

from dataclasses import dataclass, fields
from decimal import Context, Decimal, DivisionByZero, Inexact, InvalidOperation, Overflow
import hashlib
import json
import re
from typing import ClassVar, Mapping

from src.execution_feasibility import (
    DIAGNOSTIC_CODES as EXECUTION_DIAGNOSTIC_CODES,
    EXECUTION_FEASIBILITY_STATUSES,
    EXECUTION_STYLES,
    ORDER_TYPES,
    SIDES,
)
from src.strategy_lifecycle import CAPACITY_REASON_CODES, PORTFOLIO_CAPACITY_STATUSES

SCHEMA_VERSION = "1.0.0"
DECISION_SCHEMA_ID = "polymarket-exploratory-gate-c-decision"
PERMIT_SCHEMA_ID = "polymarket-exploratory-gate-c-permit"
DECISION_ID_PREFIX = "exploratorygatecdecision:sha256:"
PERMIT_ID_PREFIX = "exploratorygatecpermit:sha256:"

ERROR_CODES = (
    "FIELD_TYPE_INVALID",
    "FIELD_VALUE_INVALID",
    "LIMIT_EXCEEDED",
    "LIFECYCLE_STORE_INVALID",
    "HERMES_STORE_INVALID",
    "EXECUTION_INTENT_INVALID",
    "VENUE_SNAPSHOT_INVALID",
    "EXECUTION_ASSESSMENT_INVALID",
    "EXECUTION_BINDING_INVALID",
    "IDENTITY_DERIVATION_MISMATCH",
    "INTERNAL_VALIDATION_FAILED",
)

PERMIT_ELIGIBLE = "PERMIT_ELIGIBLE"
PERMIT_REJECTED = "PERMIT_REJECTED"
DECISION_STATUSES = (PERMIT_ELIGIBLE, PERMIT_REJECTED)

# Frozen Gate-C reason order; reasons are unique and always emitted in this order.
REASON_CODES = (
    "PORTFOLIO_CAPACITY_REJECTED",
    "ALLOCATION_REQUIRED",
    "EXPLORATORY_BAND_REQUIRED",
    "ALLOCATION_NOT_ACTIVE",
    "ACTIVE_BUDGET_REQUIRED",
    "HERMES_ASSESSMENT_REQUIRED",
    "HERMES_CONTEXT_STALE",
    "HERMES_POLICY_MISMATCH",
    "HERMES_ACTION_BLOCKS_NEW_EXPOSURE",
    "HERMES_TARGET_BAND_BLOCKS_NEW_EXPOSURE",
    "EXECUTION_STATUS_BLOCKS_NEW_EXPOSURE",
    "EXECUTION_PUBLIC_DATA_STALE",
    "ORDER_STYLE_NOT_ALLOWED",
    "ORDER_NOTIONAL_EXCEEDS_ALLOCATION",
    "ORDER_NOTIONAL_EXCEEDS_POLICY_ORDER_MAX",
    "ORDER_NOTIONAL_EXCEEDS_POLICY_MARKET_MAX",
    "GTD_EFFECTIVE_WINDOW_EXPIRED",
    "PERMIT_WINDOW_EMPTY",
)
_REASON_RANK = {code: index for index, code in enumerate(REASON_CODES)}
_CAPACITY_RANK = {code: index for index, code in enumerate(CAPACITY_REASON_CODES)}
_DIAGNOSTIC_RANK = {code: index for index, code in enumerate(EXECUTION_DIAGNOSTIC_CODES)}

PERMIT_COMPATIBLE_FEASIBILITY_STATUSES = ("FEASIBLE", "LIMITED")
_PORTFOLIO_CAPACITY_VALID = "PORTFOLIO_CAPACITY_VALID"
_STYLE_ORDER_TYPES = {"AGGRESSIVE_TAKER": ("FOK", "FAK"), "PASSIVE_MAKER": ("GTC", "GTD")}

GTD_SECURITY_MARGIN_NS = 60_000_000_000
MAX_TIME_NS = 2**63 - 1
MAX_RECORD_BYTES = 65_536
MAX_DIAGNOSTICS = 64
MAX_DECIMAL_CHARS = 128

# Exact arithmetic: any rounding raises instead of silently losing precision.
_EXACT = Context(prec=4_000, traps=[Inexact, InvalidOperation, DivisionByZero, Overflow])

_HEX64_RE = re.compile(r"[0-9a-f]{64}")
_GAMMA_ID_RE = re.compile(r"[0-9]{1,32}")
_TOKEN_ID_RE = re.compile(r"[0-9]{1,100}")
_CONDITION_ID_RE = re.compile(r"0x[0-9a-f]{64}")
_CANONICAL_DECIMAL_RE = re.compile(r"(?:0|[1-9][0-9]*)(?:\.[0-9]*[1-9])?")

STRATEGY_VERSION_PREFIX = "strategyversion:sha256:"
STRATEGY_FAMILY_PREFIX = "strategyfamily:sha256:"
POLICY_PREFIX = "portfolioauthoritypolicy:sha256:"
ALLOCATION_PREFIX = "strategyriskallocation:sha256:"
HERMES_ASSESSMENT_PREFIX = "hermesstrategyassessment:sha256:"
INTENT_PREFIX = "executionintent:sha256:"
SNAPSHOT_PREFIX = "executionsnapshot:sha256:"
FEASIBILITY_PREFIX = "executionfeasibility:sha256:"

# Fixed runtime-revalidation and non-authority truths shared by both records.
REVALIDATION_FIELDS = (
    "requires_runtime_account_revalidation",
    "requires_access_revalidation",
    "requires_reconciliation_revalidation",
    "requires_runtime_identity_revalidation",
)
NON_AUTHORITY_FIELDS = (
    "no_credential_authority",
    "no_signing_authority",
    "no_order_authority",
    "no_execution_transport_authority",
    "no_live_authority",
)


class ExploratoryGateCError(ValueError):
    """Closed, payload-free failure; its string is exactly one closed code.

    It never carries a path, payload, upstream exception text or account value.
    """

    def __init__(self, code: str) -> None:
        if code not in ERROR_CODES:
            code = "INTERNAL_VALIDATION_FAILED"
        super().__init__(code)
        self.code = code


def _fail(code: str) -> ExploratoryGateCError:
    return ExploratoryGateCError(code)


# ---------------------------------------------------------------------------
# Canonical JSON, decimals and small validators.
# ---------------------------------------------------------------------------


def canonical_json_bytes(value: object) -> bytes:
    """Frozen canonical JSON (sorted keys, compact, UTF-8, no NaN); floats reject."""

    def check(item: object) -> None:
        if item is None or isinstance(item, (bool, str)):
            return
        if isinstance(item, int):
            if abs(item) > MAX_TIME_NS:
                raise _fail("FIELD_VALUE_INVALID")
            return
        if isinstance(item, list):
            for element in item:
                check(element)
            return
        if isinstance(item, dict):
            for key, element in item.items():
                if not isinstance(key, str):
                    raise _fail("FIELD_TYPE_INVALID")
                check(element)
            return
        raise _fail("FIELD_TYPE_INVALID")

    check(value)
    try:
        text = json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
        )
    except (TypeError, ValueError):
        raise _fail("FIELD_VALUE_INVALID") from None
    return text.encode("utf-8")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def decimal_text(value: Decimal) -> str:
    """Canonical non-negative decimal text: no exponent, sign or redundant zeros."""

    if not isinstance(value, Decimal) or not value.is_finite() or value < 0:
        raise _fail("FIELD_VALUE_INVALID")
    if value == 0:
        return "0"
    text = format(value.normalize(), "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    if len(text) > MAX_DECIMAL_CHARS:
        raise _fail("LIMIT_EXCEEDED")
    return text


def parse_decimal(value: object) -> Decimal:
    if not isinstance(value, str):
        raise _fail("FIELD_TYPE_INVALID")
    if len(value) > MAX_DECIMAL_CHARS:
        raise _fail("LIMIT_EXCEEDED")
    if _CANONICAL_DECIMAL_RE.fullmatch(value) is None:
        raise _fail("FIELD_VALUE_INVALID")
    return Decimal(value)


def _require_str(value: object) -> str:
    if not isinstance(value, str):
        raise _fail("FIELD_TYPE_INVALID")
    return value


def _require_bool(value: object) -> bool:
    if not isinstance(value, bool):
        raise _fail("FIELD_TYPE_INVALID")
    return value


def _require_int(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise _fail("FIELD_TYPE_INVALID")
    if value < 0 or value > MAX_TIME_NS:
        raise _fail("FIELD_VALUE_INVALID")
    return value


def _optional_int(value: object) -> int | None:
    return None if value is None else _require_int(value)


def _choice(value: object, choices: tuple[str, ...]) -> str:
    if _require_str(value) not in choices:
        raise _fail("FIELD_VALUE_INVALID")
    return value  # type: ignore[return-value]


def _optional_choice(value: object, choices: tuple[str, ...]) -> str | None:
    return None if value is None else _choice(value, choices)


def _prefixed_id(value: object, prefix: str) -> str:
    text = _require_str(value)
    if not text.startswith(prefix) or _HEX64_RE.fullmatch(text[len(prefix):]) is None:
        raise _fail("FIELD_VALUE_INVALID")
    return text


def _optional_prefixed_id(value: object, prefix: str) -> str | None:
    return None if value is None else _prefixed_id(value, prefix)


def _hex64(value: object) -> str:
    if _HEX64_RE.fullmatch(_require_str(value)) is None:
        raise _fail("FIELD_VALUE_INVALID")
    return value  # type: ignore[return-value]


def _optional_hex64(value: object) -> str | None:
    return None if value is None else _hex64(value)


def _ordered_codes(value: object, rank: Mapping[str, int], limit: int) -> tuple[str, ...]:
    """Bounded, unique, closed codes in their frozen vocabulary order."""

    if not isinstance(value, tuple):
        raise _fail("FIELD_TYPE_INVALID")
    if len(value) > limit:
        raise _fail("LIMIT_EXCEEDED")
    if any(not isinstance(code, str) or code not in rank for code in value):
        raise _fail("FIELD_VALUE_INVALID")
    ranks = [rank[code] for code in value]
    if ranks != sorted(set(ranks)):
        raise _fail("FIELD_VALUE_INVALID")
    return value


def order_reason_codes(codes: object) -> tuple[str, ...]:
    """Deduplicate closed Gate-C reasons into the frozen precedence order."""

    unique = set(codes)  # type: ignore[arg-type]
    if not all(isinstance(code, str) and code in _REASON_RANK for code in unique):
        raise _fail("INTERNAL_VALIDATION_FAILED")
    return tuple(sorted(unique, key=_REASON_RANK.__getitem__))


def gtd_effective_deadline_ns(gtd_expiration_unix_s: int | None) -> int | None:
    """GTD expiration minus the venue's one-minute security margin, in nanoseconds."""

    if gtd_expiration_unix_s is None:
        return None
    deadline = gtd_expiration_unix_s * 1_000_000_000 - GTD_SECURITY_MARGIN_NS
    if deadline < 0 or deadline > MAX_TIME_NS:
        raise _fail("LIMIT_EXCEEDED")
    return deadline


def intent_order_notional(requested_shares: str, price_limit: str) -> Decimal:
    """Exact Decimal ``requested_shares * price_limit`` (no rounding)."""

    shares, price = parse_decimal(requested_shares), parse_decimal(price_limit)
    try:
        return _EXACT.multiply(shares, price)
    except ArithmeticError:
        raise _fail("LIMIT_EXCEEDED") from None


# ---------------------------------------------------------------------------
# Record base.
# ---------------------------------------------------------------------------


class _PendingId:
    __slots__ = ()


PENDING_ID = _PendingId()


def _plain(value: object) -> object:
    if isinstance(value, tuple):
        return [_plain(item) for item in value]
    return value


class _Record:
    SCHEMA_ID: ClassVar[str]
    ID_FIELD: ClassVar[str]
    ID_PREFIX: ClassVar[str]
    INVARIANT_TRUE_FIELDS: ClassVar[tuple[str, ...]]
    TUPLE_FIELDS: ClassVar[tuple[str, ...]]

    def _validate(self) -> None:  # pragma: no cover - overridden
        raise NotImplementedError

    def __post_init__(self) -> None:
        if not isinstance(getattr(self, "schema_id"), str) or not isinstance(
            getattr(self, "schema_version"), str
        ):
            raise _fail("FIELD_TYPE_INVALID")
        if getattr(self, "schema_id") != self.SCHEMA_ID or getattr(
            self, "schema_version"
        ) != SCHEMA_VERSION:
            raise _fail("FIELD_VALUE_INVALID")
        for name in self.INVARIANT_TRUE_FIELDS:
            if getattr(self, name) is not True:
                raise _fail("FIELD_VALUE_INVALID")
        self._validate()
        encoded = canonical_json_bytes(self.identity_preimage())
        if len(encoded) > MAX_RECORD_BYTES:
            raise _fail("LIMIT_EXCEEDED")
        computed = self.ID_PREFIX + sha256_hex(encoded)
        current = getattr(self, self.ID_FIELD)
        if current is PENDING_ID:
            object.__setattr__(self, self.ID_FIELD, computed)
            return
        _prefixed_id(current, self.ID_PREFIX)
        if current != computed:
            raise _fail("IDENTITY_DERIVATION_MISMATCH")

    def identity_preimage(self) -> dict[str, object]:
        """Every top-level field except the record's own content id."""

        return {
            item.name: _plain(getattr(self, item.name))
            for item in fields(self)  # type: ignore[arg-type]
            if item.name != self.ID_FIELD
        }

    def to_mapping(self) -> dict[str, object]:
        """Public JSON-compatible mapping (tuples become lists)."""

        return {
            item.name: _plain(getattr(self, item.name))
            for item in fields(self)  # type: ignore[arg-type]
        }

    @property
    def record_id(self) -> str:
        return getattr(self, self.ID_FIELD)

    @classmethod
    def from_mapping(cls, mapping: object):
        """Strictly load one exact public mapping and re-derive its content id."""

        if not isinstance(mapping, Mapping):
            raise _fail("FIELD_TYPE_INVALID")
        names = [item.name for item in fields(cls)]  # type: ignore[arg-type]
        if set(mapping) != set(names):
            raise _fail("FIELD_VALUE_INVALID")
        if not isinstance(mapping[cls.ID_FIELD], str):
            raise _fail("FIELD_TYPE_INVALID")
        values: dict[str, object] = {}
        for name in names:
            value = mapping[name]
            if name in cls.TUPLE_FIELDS:
                if not isinstance(value, list):
                    raise _fail("FIELD_TYPE_INVALID")
                value = tuple(value)
            values[name] = value
        return cls(**values)


# ---------------------------------------------------------------------------
# Record 1: ExploratoryGateCDecision.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ExploratoryGateCDecision(_Record):
    """Canonical hard exploratory eligibility decision for one exact execution intent.

    Eligibility authority only: it establishes no account, access, reconciliation or
    runtime-identity truth and carries no credential, signing, order, transport or live
    authority.
    """

    decision_id: str
    strategy_version_id: str
    strategy_family_id: str
    lifecycle_store_head_entry_hash: str
    active_policy_id: str | None
    allocation_id: str | None
    hermes_manager_store_head_entry_hash: str | None
    hermes_assessment_id: str | None
    execution_intent_id: str
    venue_snapshot_id: str
    execution_feasibility_assessment_id: str
    evaluated_at_ns: int
    portfolio_capacity_status: str
    portfolio_capacity_reason_codes: tuple[str, ...]
    target_strategy_capacity_status: str | None
    target_strategy_capacity_reason_codes: tuple[str, ...]
    execution_feasibility_status: str
    execution_feasibility_diagnostic_codes: tuple[str, ...]
    intent_order_notional_usd: str
    public_mechanics_deadline_ns: int | None
    gtd_effective_deadline_ns: int | None
    permit_valid_until_ns: int | None
    status: str
    reason_codes: tuple[str, ...]
    schema_id: str = DECISION_SCHEMA_ID
    schema_version: str = SCHEMA_VERSION
    canonical_hard_eligibility_decision: bool = True
    requires_runtime_account_revalidation: bool = True
    requires_access_revalidation: bool = True
    requires_reconciliation_revalidation: bool = True
    requires_runtime_identity_revalidation: bool = True
    no_credential_authority: bool = True
    no_signing_authority: bool = True
    no_order_authority: bool = True
    no_execution_transport_authority: bool = True
    no_live_authority: bool = True

    SCHEMA_ID: ClassVar[str] = DECISION_SCHEMA_ID
    ID_FIELD: ClassVar[str] = "decision_id"
    ID_PREFIX: ClassVar[str] = DECISION_ID_PREFIX
    INVARIANT_TRUE_FIELDS: ClassVar[tuple[str, ...]] = (
        "canonical_hard_eligibility_decision",
        *REVALIDATION_FIELDS,
        *NON_AUTHORITY_FIELDS,
    )
    TUPLE_FIELDS: ClassVar[tuple[str, ...]] = (
        "portfolio_capacity_reason_codes",
        "target_strategy_capacity_reason_codes",
        "execution_feasibility_diagnostic_codes",
        "reason_codes",
    )

    def _validate(self) -> None:
        _prefixed_id(self.strategy_version_id, STRATEGY_VERSION_PREFIX)
        _prefixed_id(self.strategy_family_id, STRATEGY_FAMILY_PREFIX)
        _hex64(self.lifecycle_store_head_entry_hash)
        _optional_prefixed_id(self.active_policy_id, POLICY_PREFIX)
        _optional_prefixed_id(self.allocation_id, ALLOCATION_PREFIX)
        _optional_hex64(self.hermes_manager_store_head_entry_hash)
        _optional_prefixed_id(self.hermes_assessment_id, HERMES_ASSESSMENT_PREFIX)
        _prefixed_id(self.execution_intent_id, INTENT_PREFIX)
        _prefixed_id(self.venue_snapshot_id, SNAPSHOT_PREFIX)
        _prefixed_id(self.execution_feasibility_assessment_id, FEASIBILITY_PREFIX)
        evaluated = _require_int(self.evaluated_at_ns)

        global_status = _choice(self.portfolio_capacity_status, PORTFOLIO_CAPACITY_STATUSES)
        global_reasons = _ordered_codes(
            self.portfolio_capacity_reason_codes, _CAPACITY_RANK, len(CAPACITY_REASON_CODES)
        )
        if (global_status == _PORTFOLIO_CAPACITY_VALID) != (not global_reasons):
            raise _fail("FIELD_VALUE_INVALID")
        target_status = _optional_choice(
            self.target_strategy_capacity_status, PORTFOLIO_CAPACITY_STATUSES
        )
        target_reasons = _ordered_codes(
            self.target_strategy_capacity_reason_codes,
            _CAPACITY_RANK,
            len(CAPACITY_REASON_CODES),
        )
        if target_status is None:
            if target_reasons:
                raise _fail("FIELD_VALUE_INVALID")
        elif (target_status == _PORTFOLIO_CAPACITY_VALID) != (not target_reasons):
            raise _fail("FIELD_VALUE_INVALID")

        feasibility = _choice(self.execution_feasibility_status, EXECUTION_FEASIBILITY_STATUSES)
        _ordered_codes(self.execution_feasibility_diagnostic_codes, _DIAGNOSTIC_RANK, MAX_DIAGNOSTICS)
        parse_decimal(self.intent_order_notional_usd)
        public_deadline = _optional_int(self.public_mechanics_deadline_ns)
        gtd_deadline = _optional_int(self.gtd_effective_deadline_ns)
        valid_until = _optional_int(self.permit_valid_until_ns)
        if valid_until is not None:
            if any(d is not None and valid_until > d for d in (public_deadline, gtd_deadline)):
                raise _fail("FIELD_VALUE_INVALID")
        elif public_deadline is not None or gtd_deadline is not None:
            raise _fail("FIELD_VALUE_INVALID")

        status = _choice(self.status, DECISION_STATUSES)
        reasons = _ordered_codes(self.reason_codes, _REASON_RANK, len(REASON_CODES))
        if (status == PERMIT_ELIGIBLE) != (not reasons):
            raise _fail("FIELD_VALUE_INVALID")
        # Reasons that are pure functions of recorded fields must agree with them.
        derived = {
            "PORTFOLIO_CAPACITY_REJECTED": global_status != _PORTFOLIO_CAPACITY_VALID
            or target_status != _PORTFOLIO_CAPACITY_VALID,
            "ALLOCATION_REQUIRED": None if self.allocation_id is not None else True,
            "HERMES_ASSESSMENT_REQUIRED": self.hermes_assessment_id is None,
            "EXECUTION_STATUS_BLOCKS_NEW_EXPOSURE": feasibility
            not in PERMIT_COMPATIBLE_FEASIBILITY_STATUSES,
            "EXECUTION_PUBLIC_DATA_STALE": public_deadline is None or evaluated >= public_deadline,
            "GTD_EFFECTIVE_WINDOW_EXPIRED": gtd_deadline is not None and evaluated >= gtd_deadline,
            "PERMIT_WINDOW_EMPTY": valid_until is None or evaluated >= valid_until,
        }
        for code, expected in derived.items():
            if expected is not None and (code in reasons) != expected:
                raise _fail("FIELD_VALUE_INVALID")
        if self.hermes_assessment_id is not None and self.hermes_manager_store_head_entry_hash is None:
            raise _fail("FIELD_VALUE_INVALID")
        if self.active_policy_id is None and status == PERMIT_ELIGIBLE:
            raise _fail("FIELD_VALUE_INVALID")


def validate_exploratory_gate_c_decision(decision: object) -> ExploratoryGateCDecision:
    """Exact-type plus exact closed round-trip validation (tamper rejection)."""

    if type(decision) is not ExploratoryGateCDecision:
        raise _fail("FIELD_TYPE_INVALID")
    if ExploratoryGateCDecision.from_mapping(decision.to_mapping()) != decision:
        raise _fail("IDENTITY_DERIVATION_MISMATCH")
    return decision


# ---------------------------------------------------------------------------
# Record 2: ExploratoryGateCPermit.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ExploratoryGateCPermit(_Record):
    """Short-lived exploratory permit for exactly one validated execution intent.

    ``authorized_order_notional_usd`` is the exact intent notional, never a reusable cap.
    The permit is necessary-but-not-sufficient future evidence: later protected runtime
    must still revalidate account, access, reconciliation and runtime identity, and the
    permit itself carries no credential, signing, order, transport or live authority.
    """

    permit_id: str
    decision_id: str
    strategy_version_id: str
    strategy_family_id: str
    lifecycle_store_head_entry_hash: str
    active_policy_id: str
    allocation_id: str
    hermes_assessment_id: str
    execution_intent_id: str
    venue_snapshot_id: str
    execution_feasibility_assessment_id: str
    gamma_market_id: str
    condition_id: str
    token_id: str
    side: str
    execution_style: str
    order_type: str
    requested_shares: str
    price_limit: str
    post_only: bool
    gtd_expiration_unix_s: int | None
    authorized_order_notional_usd: str
    feasibility_status: str
    feasibility_diagnostic_codes: tuple[str, ...]
    issued_at_ns: int
    valid_until_ns: int
    schema_id: str = PERMIT_SCHEMA_ID
    schema_version: str = SCHEMA_VERSION
    exact_intent_only: bool = True
    requires_runtime_account_revalidation: bool = True
    requires_access_revalidation: bool = True
    requires_reconciliation_revalidation: bool = True
    requires_runtime_identity_revalidation: bool = True
    no_credential_authority: bool = True
    no_signing_authority: bool = True
    no_order_authority: bool = True
    no_execution_transport_authority: bool = True
    no_live_authority: bool = True

    SCHEMA_ID: ClassVar[str] = PERMIT_SCHEMA_ID
    ID_FIELD: ClassVar[str] = "permit_id"
    ID_PREFIX: ClassVar[str] = PERMIT_ID_PREFIX
    INVARIANT_TRUE_FIELDS: ClassVar[tuple[str, ...]] = (
        "exact_intent_only",
        *REVALIDATION_FIELDS,
        *NON_AUTHORITY_FIELDS,
    )
    TUPLE_FIELDS: ClassVar[tuple[str, ...]] = ("feasibility_diagnostic_codes",)

    def _validate(self) -> None:
        _prefixed_id(self.decision_id, DECISION_ID_PREFIX)
        _prefixed_id(self.strategy_version_id, STRATEGY_VERSION_PREFIX)
        _prefixed_id(self.strategy_family_id, STRATEGY_FAMILY_PREFIX)
        _hex64(self.lifecycle_store_head_entry_hash)
        _prefixed_id(self.active_policy_id, POLICY_PREFIX)
        _prefixed_id(self.allocation_id, ALLOCATION_PREFIX)
        _prefixed_id(self.hermes_assessment_id, HERMES_ASSESSMENT_PREFIX)
        _prefixed_id(self.execution_intent_id, INTENT_PREFIX)
        _prefixed_id(self.venue_snapshot_id, SNAPSHOT_PREFIX)
        _prefixed_id(self.execution_feasibility_assessment_id, FEASIBILITY_PREFIX)
        for value, pattern in (
            (self.gamma_market_id, _GAMMA_ID_RE),
            (self.condition_id, _CONDITION_ID_RE),
            (self.token_id, _TOKEN_ID_RE),
        ):
            if pattern.fullmatch(_require_str(value)) is None:
                raise _fail("FIELD_VALUE_INVALID")
        _choice(self.side, SIDES)
        style = _choice(self.execution_style, EXECUTION_STYLES)
        order_type = _choice(self.order_type, ORDER_TYPES)
        if order_type not in _STYLE_ORDER_TYPES[style]:
            raise _fail("FIELD_VALUE_INVALID")
        if _require_bool(self.post_only) != (style == "PASSIVE_MAKER"):
            raise _fail("FIELD_VALUE_INVALID")
        expiration = _optional_int(self.gtd_expiration_unix_s)
        if (expiration is not None) != (order_type == "GTD"):
            raise _fail("FIELD_VALUE_INVALID")
        if parse_decimal(self.requested_shares) <= 0:
            raise _fail("FIELD_VALUE_INVALID")
        price = parse_decimal(self.price_limit)
        if not Decimal(0) < price < Decimal(1):
            raise _fail("FIELD_VALUE_INVALID")
        authorized = parse_decimal(self.authorized_order_notional_usd)
        if authorized != intent_order_notional(self.requested_shares, self.price_limit):
            raise _fail("FIELD_VALUE_INVALID")
        _choice(self.feasibility_status, PERMIT_COMPATIBLE_FEASIBILITY_STATUSES)
        _ordered_codes(self.feasibility_diagnostic_codes, _DIAGNOSTIC_RANK, MAX_DIAGNOSTICS)
        issued = _require_int(self.issued_at_ns)
        valid_until = _require_int(self.valid_until_ns)
        if issued >= valid_until:
            raise _fail("FIELD_VALUE_INVALID")
        gtd_deadline = gtd_effective_deadline_ns(expiration)
        if gtd_deadline is not None and valid_until > gtd_deadline:
            raise _fail("FIELD_VALUE_INVALID")


def validate_exploratory_gate_c_permit(permit: object) -> ExploratoryGateCPermit:
    """Exact-type plus exact closed round-trip validation (tamper rejection)."""

    if type(permit) is not ExploratoryGateCPermit:
        raise _fail("FIELD_TYPE_INVALID")
    if ExploratoryGateCPermit.from_mapping(permit.to_mapping()) != permit:
        raise _fail("IDENTITY_DERIVATION_MISMATCH")
    return permit


RECORD_TYPES: dict[str, type] = {
    DECISION_SCHEMA_ID: ExploratoryGateCDecision,
    PERMIT_SCHEMA_ID: ExploratoryGateCPermit,
}


def record_from_mapping(mapping: object):
    """Exact closed loader for the two Gate-C record schemas (selected by ``schema_id``)."""

    if not isinstance(mapping, Mapping):
        raise _fail("FIELD_TYPE_INVALID")
    schema_id = mapping.get("schema_id")
    if not isinstance(schema_id, str):
        raise _fail("FIELD_TYPE_INVALID")
    cls = RECORD_TYPES.get(schema_id)
    if cls is None:
        raise _fail("FIELD_VALUE_INVALID")
    return cls.from_mapping(mapping)
