"""Canonical records for the S10-EXEC-FEAS-01 current public execution-feasibility core.

Three immutable content-addressed records live here: ExecutionIntent,
PublicExecutionVenueSnapshot and ExecutionFeasibilityAssessment. This module is pure:
it performs no network, filesystem, clock or environment access, and it has no
account, Gate-C, order, execution or live authority.
"""

from __future__ import annotations

from dataclasses import dataclass, fields
from decimal import Decimal, InvalidOperation
import hashlib
import json
import re
from typing import ClassVar, Mapping

from src.strategy_lifecycle import StrategyLifecycleError, StrategyVersion
from src.strategy_lifecycle import canonical_json_text as _lifecycle_canonical_text
from src.strategy_lifecycle import record_from_mapping as _lifecycle_record_from_mapping

SCHEMA_VERSION = "1.0.0"
INTENT_SCHEMA_ID = "polymarket-execution-intent"
SNAPSHOT_SCHEMA_ID = "polymarket-public-execution-venue-snapshot"
ASSESSMENT_SCHEMA_ID = "polymarket-execution-feasibility-assessment"

INTENT_ID_PREFIX = "executionintent:sha256:"
SNAPSHOT_ID_PREFIX = "executionsnapshot:sha256:"
ASSESSMENT_ID_PREFIX = "executionfeasibility:sha256:"
EXECUTION_RULE_PREFIX = "executionrule:sha256:"
STRATEGY_VERSION_PREFIX = "strategyversion:sha256:"

ERROR_CODES = (
    "SCHEMA_UNSUPPORTED",
    "FIELD_MISSING",
    "FIELD_TYPE_INVALID",
    "FIELD_VALUE_INVALID",
    "LIMIT_EXCEEDED",
    "IDENTITY_DERIVATION_MISMATCH",
    "STRATEGY_VERSION_INVALID",
    "STRATEGY_SPEC_INVALID",
    "EXECUTION_RULE_BINDING_INVALID",
    "NETWORK_SCHEME_FORBIDDEN",
    "NETWORK_HOST_FORBIDDEN",
    "NETWORK_METHOD_FORBIDDEN",
    "SOURCE_RESPONSE_TOO_LARGE",
    "SOURCE_RESPONSE_INVALID",
    "INTERNAL_VALIDATION_FAILED",
)

DIAGNOSTIC_CODES = (
    "SOURCE_GAMMA_UNAVAILABLE",
    "SOURCE_CLOB_UNAVAILABLE",
    "SOURCE_GAMMA_INVALID",
    "SOURCE_CLOB_INVALID",
    "SOURCE_IDENTITY_MISMATCH",
    "MARKET_INACTIVE",
    "MARKET_CLOSED",
    "MARKET_NOT_ACCEPTING_ORDERS",
    "ORDER_BOOK_DISABLED",
    "TICK_SOURCE_CONFLICT",
    "MIN_ORDER_SOURCE_CONFLICT",
    "NEG_RISK_SOURCE_CONFLICT",
    "BOOK_TIMESTAMP_INVALID",
    "BOOK_STALE",
    "BOOK_INVALID",
    "PRICE_OFF_TICK",
    "MINIMUM_ORDER_NOTIONAL_NOT_MET",
    "MINIMUM_ORDER_SHARES_NOT_MET",
    "NO_VISIBLE_OPPOSING_LIQUIDITY",
    "FOK_INSUFFICIENT_VISIBLE_DEPTH",
    "FAK_PARTIAL_VISIBLE_FILL",
    "POST_ONLY_WOULD_CROSS",
    "FEE_CONFIG_UNKNOWN",
    "FEE_EXPONENT_UNSUPPORTED",
    "MARKETABLE_ORDER_DELAY",
    "CLIENT_LATENCY_UNKNOWN",
    "PASSIVE_FILL_UNKNOWN",
    "ADVERSE_SELECTION_UNKNOWN",
)
_DIAGNOSTIC_RANK = {code: index for index, code in enumerate(DIAGNOSTIC_CODES)}
SNAPSHOT_DIAGNOSTIC_CODES = (
    "SOURCE_GAMMA_UNAVAILABLE",
    "SOURCE_CLOB_UNAVAILABLE",
    "SOURCE_GAMMA_INVALID",
    "SOURCE_CLOB_INVALID",
    "SOURCE_IDENTITY_MISMATCH",
    "BOOK_INVALID",
    "FEE_CONFIG_UNKNOWN",
)

SIDES = ("BUY", "SELL")
EXECUTION_STYLES = ("AGGRESSIVE_TAKER", "PASSIVE_MAKER")
ORDER_TYPES = ("FOK", "FAK", "GTC", "GTD")
STYLE_ORDER_TYPES = {"AGGRESSIVE_TAKER": ("FOK", "FAK"), "PASSIVE_MAKER": ("GTC", "GTD")}
SOURCE_STATES = ("AVAILABLE", "UNAVAILABLE", "INVALID")
EXECUTION_FEASIBILITY_STATUSES = ("FEASIBLE", "LIMITED", "INCONCLUSIVE", "NOT_FEASIBLE")
EXECUTION_DIMENSION_STATES = ("PASS", "LIMITED", "FAIL", "UNKNOWN", "NOT_APPLICABLE")
FEE_EXACTNESS = (
    "EXACT_ZERO_NO_FEES",
    "EXACT_ZERO_MAKER",
    "CONSERVATIVE_5DP_UPPER_BOUND",
    "UNKNOWN",
)
DIMENSIONS = (
    "market_dimension",
    "identity_dimension",
    "freshness_dimension",
    "tick_dimension",
    "minimum_order_dimension",
    "book_dimension",
    "fill_dimension",
    "fee_dimension",
    "delay_dimension",
)
V1_LIMITATIONS = ("FAK_PARTIAL_VISIBLE_FILL", "MARKETABLE_ORDER_DELAY")

MAX_RECORD_BYTES = 262_144
MAX_JSON_DEPTH = 12
MAX_JSON_NODES = 20_000
MAX_STRING_CHARS = 262_144
MAX_DIAGNOSTICS = 64
MAX_BOOK_LEVELS = 5_000
MAX_TOKEN_ID_CHARS = 100
MAX_GAMMA_MARKET_ID_CHARS = 32
MAX_CONDITION_ID_CHARS = 66
MAX_PUBLIC_DATA_AGE_NS = 60_000_000_000
GTD_MIN_LEAD_S = 180
MAX_TIME_NS = 2**63 - 1
MAX_SECONDS_DELAY = 86_400
MAX_INPUT_INTEGER_DIGITS = 30
MAX_INPUT_FRACTION_DIGITS = 18
MAX_DERIVED_DECIMAL_CHARS = 2_048

_GAMMA_ID_RE = re.compile(r"[0-9]{1,32}")
_TOKEN_ID_RE = re.compile(r"[0-9]{1,100}")
_CONDITION_ID_RE = re.compile(r"0x[0-9a-f]{64}")
_HEX64_RE = re.compile(r"[0-9a-f]{64}")
_BOOK_HASH_RE = re.compile(r"[0-9A-Za-z]{1,128}")
_CANONICAL_DECIMAL_RE = re.compile(r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]*[1-9])?")


class ExecutionFeasibilityError(ValueError):
    """Closed, payload-free failure; its string is exactly one closed code."""

    def __init__(self, code: str) -> None:
        if code not in ERROR_CODES:
            code = "INTERNAL_VALIDATION_FAILED"
        super().__init__(code)
        self.code = code


def _fail(code: str) -> ExecutionFeasibilityError:
    return ExecutionFeasibilityError(code)


# ---------------------------------------------------------------------------
# Canonical JSON and decimals.
# ---------------------------------------------------------------------------


def _check_json_value(value: object, depth: int, counter: list[int]) -> None:
    counter[0] += 1
    if counter[0] > MAX_JSON_NODES:
        raise _fail("LIMIT_EXCEEDED")
    if value is None or isinstance(value, bool):
        return
    if isinstance(value, int):
        if abs(value) > MAX_TIME_NS:
            raise _fail("FIELD_VALUE_INVALID")
        return
    if isinstance(value, str):
        if len(value) > MAX_STRING_CHARS:
            raise _fail("LIMIT_EXCEEDED")
        return
    if isinstance(value, (list, tuple)):
        if depth >= MAX_JSON_DEPTH:
            raise _fail("LIMIT_EXCEEDED")
        for item in value:
            _check_json_value(item, depth + 1, counter)
        return
    if isinstance(value, dict):
        if depth >= MAX_JSON_DEPTH:
            raise _fail("LIMIT_EXCEEDED")
        for key, item in value.items():
            if not isinstance(key, str):
                raise _fail("FIELD_TYPE_INVALID")
            _check_json_value(item, depth + 1, counter)
        return
    raise _fail("FIELD_TYPE_INVALID")


def canonical_json_text(value: object) -> str:
    """Frozen canonical JSON; floats, Decimals and non-JSON types reject."""

    _check_json_value(value, 0, [0])
    try:
        return json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
        )
    except (TypeError, ValueError):
        raise _fail("FIELD_VALUE_INVALID") from None


def canonical_json_bytes(value: object) -> bytes:
    return canonical_json_text(value).encode("utf-8")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def decimal_text(value: Decimal) -> str:
    """Canonical decimal text: no exponent, sign or redundant zeros; finite only."""

    if not isinstance(value, Decimal) or not value.is_finite():
        raise _fail("FIELD_VALUE_INVALID")
    if value == 0:
        return "0"
    text = format(value.normalize(), "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


def parse_decimal(value: object, *, derived: bool = False) -> Decimal:
    """Parse one canonical decimal string; input values also have bounded precision."""

    if not isinstance(value, str):
        raise _fail("FIELD_TYPE_INVALID")
    if len(value) > MAX_DERIVED_DECIMAL_CHARS or _CANONICAL_DECIMAL_RE.fullmatch(value) is None:
        raise _fail("FIELD_VALUE_INVALID")
    if value == "-0":
        raise _fail("FIELD_VALUE_INVALID")
    if not derived:
        whole, _, fraction = value.lstrip("-").partition(".")
        if len(whole) > MAX_INPUT_INTEGER_DIGITS or len(fraction) > MAX_INPUT_FRACTION_DIGITS:
            raise _fail("FIELD_VALUE_INVALID")
    return Decimal(value)


def observed_decimal_text(value: Decimal) -> str:
    """Canonical text for an externally observed decimal (bounded input precision)."""

    text = decimal_text(value)
    parse_decimal(text)
    return text


def _optional_decimal(value: object, *, derived: bool = False) -> Decimal | None:
    return None if value is None else parse_decimal(value, derived=derived)


def _require_str(value: object) -> str:
    if not isinstance(value, str):
        raise _fail("FIELD_TYPE_INVALID")
    return value


def _require_bool(value: object) -> bool:
    if not isinstance(value, bool):
        raise _fail("FIELD_TYPE_INVALID")
    return value


def _optional_bool(value: object) -> bool | None:
    return None if value is None else _require_bool(value)


def _require_int(value: object, *, low: int = 0, high: int = MAX_TIME_NS) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise _fail("FIELD_TYPE_INVALID")
    if value < low or value > high:
        raise _fail("FIELD_VALUE_INVALID")
    return value


def _optional_int(value: object, *, high: int = MAX_TIME_NS) -> int | None:
    return None if value is None else _require_int(value, high=high)


def _choice(value: object, choices: tuple[str, ...]) -> str:
    if _require_str(value) not in choices:
        raise _fail("FIELD_VALUE_INVALID")
    return value  # type: ignore[return-value]


def _prefixed_id(value: object, prefix: str) -> str:
    text = _require_str(value)
    if not text.startswith(prefix) or _HEX64_RE.fullmatch(text[len(prefix):]) is None:
        raise _fail("FIELD_VALUE_INVALID")
    return text


def _optional_hex64(value: object) -> str | None:
    if value is None:
        return None
    if _HEX64_RE.fullmatch(_require_str(value)) is None:
        raise _fail("FIELD_VALUE_INVALID")
    return value  # type: ignore[return-value]


def validate_gamma_market_id(value: object) -> str:
    if _GAMMA_ID_RE.fullmatch(_require_str(value)) is None:
        raise _fail("FIELD_VALUE_INVALID")
    return value  # type: ignore[return-value]


def validate_condition_id(value: object) -> str:
    if _CONDITION_ID_RE.fullmatch(_require_str(value)) is None:
        raise _fail("FIELD_VALUE_INVALID")
    return value  # type: ignore[return-value]


def validate_token_id(value: object) -> str:
    if _TOKEN_ID_RE.fullmatch(_require_str(value)) is None:
        raise _fail("FIELD_VALUE_INVALID")
    return value  # type: ignore[return-value]


def order_diagnostics(codes: object) -> tuple[str, ...]:
    """Deduplicate closed diagnostic codes into the frozen precedence order."""

    unique = set(codes)  # type: ignore[arg-type]
    if not all(isinstance(code, str) and code in _DIAGNOSTIC_RANK for code in unique):
        raise _fail("FIELD_VALUE_INVALID")
    return tuple(sorted(unique, key=_DIAGNOSTIC_RANK.__getitem__))


def _diagnostics(value: object, allowed: tuple[str, ...]) -> tuple[str, ...]:
    if not isinstance(value, tuple):
        raise _fail("FIELD_TYPE_INVALID")
    if len(value) > MAX_DIAGNOSTICS:
        raise _fail("LIMIT_EXCEEDED")
    if any(not isinstance(code, str) or code not in allowed for code in value):
        raise _fail("FIELD_VALUE_INVALID")
    if value != order_diagnostics(value):
        raise _fail("FIELD_VALUE_INVALID")
    return value


# ---------------------------------------------------------------------------
# Record base.
# ---------------------------------------------------------------------------


class _PendingId:
    __slots__ = ()


_PENDING_ID = _PendingId()


def _plain(value: object) -> object:
    if isinstance(value, tuple):
        return [_plain(item) for item in value]
    return value


class _Record:
    RECORD_KIND: ClassVar[str]
    SCHEMA_ID: ClassVar[str]
    ID_FIELD: ClassVar[str]
    ID_PREFIX: ClassVar[str]
    INVARIANT_TRUE_FIELDS: ClassVar[tuple[str, ...]]

    def _validate(self) -> None:  # pragma: no cover - overridden
        raise NotImplementedError

    def __post_init__(self) -> None:
        if getattr(self, "schema_id") != self.SCHEMA_ID or getattr(
            self, "schema_version"
        ) != SCHEMA_VERSION:
            raise _fail("SCHEMA_UNSUPPORTED")
        for name in self.INVARIANT_TRUE_FIELDS:
            if getattr(self, name) is not True:
                raise _fail("FIELD_VALUE_INVALID")
        self._validate()
        mapping = self.to_mapping(include_id=False)
        encoded = canonical_json_bytes(mapping)
        if len(encoded) > MAX_RECORD_BYTES:
            raise _fail("LIMIT_EXCEEDED")
        computed = self.ID_PREFIX + sha256_hex(canonical_json_bytes(self.identity_preimage()))
        current = getattr(self, self.ID_FIELD)
        if current is _PENDING_ID:
            object.__setattr__(self, self.ID_FIELD, computed)
            return
        _prefixed_id(current, self.ID_PREFIX)
        if current != computed:
            raise _fail("IDENTITY_DERIVATION_MISMATCH")

    def _field_value(self, name: str) -> object:
        return _plain(getattr(self, name))

    def to_mapping(self, *, include_id: bool = True) -> dict[str, object]:
        """Public JSON-compatible mapping (tuples become lists)."""

        return {
            item.name: self._field_value(item.name)
            for item in fields(self)  # type: ignore[arg-type]
            if include_id or item.name != self.ID_FIELD
        }

    def identity_preimage(self) -> dict[str, object]:
        """Every field except the content ID and the invariant authority booleans."""

        excluded = {self.ID_FIELD, *self.INVARIANT_TRUE_FIELDS}
        return {
            item.name: self._field_value(item.name)
            for item in fields(self)  # type: ignore[arg-type]
            if item.name not in excluded
        }

    @property
    def record_id(self) -> str:
        return getattr(self, self.ID_FIELD)

    @classmethod
    def _coerce(cls, name: str, value: object) -> object:
        if isinstance(value, list):
            return tuple(value)
        return value

    @classmethod
    def from_mapping(cls, mapping: object):
        """Strictly load one exact public mapping and re-derive its content ID."""

        if not isinstance(mapping, Mapping):
            raise _fail("FIELD_TYPE_INVALID")
        names = [item.name for item in fields(cls)]  # type: ignore[arg-type]
        if any(name not in mapping for name in names):
            raise _fail("FIELD_MISSING")
        if set(mapping) != set(names):
            raise _fail("FIELD_VALUE_INVALID")
        if not isinstance(mapping[cls.ID_FIELD], str):
            raise _fail("FIELD_TYPE_INVALID")
        return cls(**{name: cls._coerce(name, mapping[name]) for name in names})


# ---------------------------------------------------------------------------
# StrategyVersion binding.
# ---------------------------------------------------------------------------


def _reject_json_constant(_token: str) -> object:
    raise _fail("STRATEGY_SPEC_INVALID")


def bind_strategy_version(strategy_version: object) -> tuple[str, str]:
    """Return (strategy_version_id, execution_rule_sha256) for one exact StrategyVersion.

    The StrategyVersion is revalidated by the STRAT-LIFE canonical round trip and is never
    mutated; the digest is always derived here and never accepted from a caller.
    """

    if type(strategy_version) is not StrategyVersion:
        raise _fail("STRATEGY_VERSION_INVALID")
    try:
        reloaded = _lifecycle_record_from_mapping(
            strategy_version.RECORD_KIND, strategy_version.to_mapping()
        )
    except StrategyLifecycleError:
        raise _fail("STRATEGY_VERSION_INVALID") from None
    if reloaded != strategy_version:
        raise _fail("STRATEGY_VERSION_INVALID")
    text = strategy_version.strategy_spec_json
    try:
        spec = json.loads(
            text, parse_float=_reject_json_constant, parse_constant=_reject_json_constant
        )
        canonical = _lifecycle_canonical_text(spec)
    except (ValueError, StrategyLifecycleError):
        raise _fail("STRATEGY_SPEC_INVALID") from None
    if not isinstance(spec, dict) or canonical != text:
        raise _fail("STRATEGY_SPEC_INVALID")
    rule = spec.get("execution_rule")
    if not isinstance(rule, dict):
        raise _fail("STRATEGY_SPEC_INVALID")
    digest = sha256_hex(canonical_json_bytes({"execution_rule": rule}))
    return strategy_version.strategy_version_id, EXECUTION_RULE_PREFIX + digest


# ---------------------------------------------------------------------------
# Record 1: ExecutionIntent.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ExecutionIntent(_Record):
    """One exact prospective execution intent; it is advisory and carries no authority."""

    execution_intent_id: str
    strategy_version_id: str
    execution_rule_sha256: str
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
    information_cutoff_ns: int
    max_public_data_age_ns: int
    schema_id: str = INTENT_SCHEMA_ID
    schema_version: str = SCHEMA_VERSION
    advisory_only: bool = True
    no_order_authority: bool = True
    no_execution_authority: bool = True
    no_live_authority: bool = True

    RECORD_KIND: ClassVar[str] = "EXECUTION_INTENT"
    SCHEMA_ID: ClassVar[str] = INTENT_SCHEMA_ID
    ID_FIELD: ClassVar[str] = "execution_intent_id"
    ID_PREFIX: ClassVar[str] = INTENT_ID_PREFIX
    INVARIANT_TRUE_FIELDS: ClassVar[tuple[str, ...]] = (
        "advisory_only",
        "no_order_authority",
        "no_execution_authority",
        "no_live_authority",
    )

    def _validate(self) -> None:
        _prefixed_id(self.strategy_version_id, STRATEGY_VERSION_PREFIX)
        _prefixed_id(self.execution_rule_sha256, EXECUTION_RULE_PREFIX)
        validate_gamma_market_id(self.gamma_market_id)
        validate_condition_id(self.condition_id)
        validate_token_id(self.token_id)
        _choice(self.side, SIDES)
        style = _choice(self.execution_style, EXECUTION_STYLES)
        order_type = _choice(self.order_type, ORDER_TYPES)
        if parse_decimal(self.requested_shares) <= 0:
            raise _fail("FIELD_VALUE_INVALID")
        price = parse_decimal(self.price_limit)
        if not Decimal(0) < price < Decimal(1):
            raise _fail("FIELD_VALUE_INVALID")
        post_only = _require_bool(self.post_only)
        cutoff = _require_int(self.information_cutoff_ns)
        _require_int(self.max_public_data_age_ns, low=1, high=MAX_PUBLIC_DATA_AGE_NS)
        expiration = self.gtd_expiration_unix_s
        if expiration is not None:
            _require_int(expiration)
        if order_type not in STYLE_ORDER_TYPES[style]:
            raise _fail("FIELD_VALUE_INVALID")
        if style == "AGGRESSIVE_TAKER":
            if post_only or expiration is not None:
                raise _fail("FIELD_VALUE_INVALID")
            return
        if not post_only:
            raise _fail("FIELD_VALUE_INVALID")
        if order_type == "GTC":
            if expiration is not None:
                raise _fail("FIELD_VALUE_INVALID")
        elif expiration is None:
            raise _fail("FIELD_MISSING")
        elif expiration < cutoff // 1_000_000_000 + GTD_MIN_LEAD_S:
            raise _fail("FIELD_VALUE_INVALID")


def build_execution_intent(
    *,
    strategy_version: StrategyVersion,
    gamma_market_id: str,
    condition_id: str,
    token_id: str,
    side: str,
    execution_style: str,
    order_type: str,
    requested_shares: str,
    price_limit: str,
    post_only: bool,
    information_cutoff_ns: int,
    max_public_data_age_ns: int,
    gtd_expiration_unix_s: int | None = None,
) -> ExecutionIntent:
    """Build an intent bound to the exact StrategyVersion and its derived execution rule."""

    strategy_version_id, rule_digest = bind_strategy_version(strategy_version)
    return ExecutionIntent(
        execution_intent_id=_PENDING_ID,  # type: ignore[arg-type]
        strategy_version_id=strategy_version_id,
        execution_rule_sha256=rule_digest,
        gamma_market_id=gamma_market_id,
        condition_id=condition_id,
        token_id=token_id,
        side=side,
        execution_style=execution_style,
        order_type=order_type,
        requested_shares=requested_shares,
        price_limit=price_limit,
        post_only=post_only,
        gtd_expiration_unix_s=gtd_expiration_unix_s,
        information_cutoff_ns=information_cutoff_ns,
        max_public_data_age_ns=max_public_data_age_ns,
    )


def validate_execution_intent(
    intent: object, *, strategy_version: StrategyVersion | None = None
) -> ExecutionIntent:
    """Exact-type, round-trip and (optionally) StrategyVersion-binding validation."""

    if type(intent) is not ExecutionIntent:
        raise _fail("FIELD_TYPE_INVALID")
    if ExecutionIntent.from_mapping(intent.to_mapping()) != intent:
        raise _fail("INTERNAL_VALIDATION_FAILED")
    if strategy_version is not None:
        if bind_strategy_version(strategy_version) != (
            intent.strategy_version_id,
            intent.execution_rule_sha256,
        ):
            raise _fail("EXECUTION_RULE_BINDING_INVALID")
    return intent


# ---------------------------------------------------------------------------
# Record 2: PublicExecutionVenueSnapshot.
# ---------------------------------------------------------------------------

GAMMA_FACT_FIELDS = (
    "active",
    "closed",
    "accepting_orders",
    "enable_order_book",
    "restricted",
    "gamma_neg_risk",
    "gamma_tick_size",
    "gamma_min_order_notional_usd",
    "fees_enabled",
    "fee_rate",
    "fee_exponent",
    "fee_taker_only",
    "fee_rebate_rate",
    "seconds_delay",
)
CLOB_FACT_FIELDS = (
    "book_condition_id",
    "book_token_id",
    "book_timestamp_ns",
    "book_hash",
    "book_neg_risk",
    "book_tick_size",
    "book_min_order_size_raw",
    "last_trade_price",
)
_REQUIRED_CLOB_FACTS = CLOB_FACT_FIELDS[:-1]


def _levels(value: object, *, descending: bool) -> tuple[tuple[str, str], ...]:
    if not isinstance(value, tuple):
        raise _fail("FIELD_TYPE_INVALID")
    if len(value) > MAX_BOOK_LEVELS:
        raise _fail("LIMIT_EXCEEDED")
    prices: list[Decimal] = []
    for level in value:
        if not isinstance(level, tuple) or len(level) != 2:
            raise _fail("FIELD_TYPE_INVALID")
        price, size = parse_decimal(level[0]), parse_decimal(level[1])
        if not Decimal(0) < price < Decimal(1) or size <= 0:
            raise _fail("FIELD_VALUE_INVALID")
        prices.append(price)
    ordered = sorted(prices, reverse=descending)
    if prices != ordered or len(set(prices)) != len(prices):
        raise _fail("FIELD_VALUE_INVALID")
    return value


@dataclass(frozen=True)
class PublicExecutionVenueSnapshot(_Record):
    """Bounded current public Gamma/CLOB facts; unavailable facts stay null."""

    venue_snapshot_id: str
    gamma_market_id: str
    condition_id: str
    token_id: str
    acquisition_started_ns: int
    acquisition_completed_ns: int
    gamma_source_state: str
    gamma_payload_sha256: str | None
    clob_source_state: str
    clob_payload_sha256: str | None
    active: bool | None
    closed: bool | None
    accepting_orders: bool | None
    enable_order_book: bool | None
    restricted: bool | None
    gamma_neg_risk: bool | None
    gamma_tick_size: str | None
    gamma_min_order_notional_usd: str | None
    fees_enabled: bool | None
    fee_rate: str | None
    fee_exponent: str | None
    fee_taker_only: bool | None
    fee_rebate_rate: str | None
    seconds_delay: int | None
    book_condition_id: str | None
    book_token_id: str | None
    book_timestamp_ns: int | None
    book_hash: str | None
    book_neg_risk: bool | None
    book_tick_size: str | None
    book_min_order_size_raw: str | None
    last_trade_price: str | None
    bids: tuple[tuple[str, str], ...]
    asks: tuple[tuple[str, str], ...]
    diagnostic_codes: tuple[str, ...]
    schema_id: str = SNAPSHOT_SCHEMA_ID
    schema_version: str = SCHEMA_VERSION
    public_only: bool = True
    no_account_state: bool = True
    no_order_authority: bool = True
    no_execution_authority: bool = True
    no_live_authority: bool = True

    RECORD_KIND: ClassVar[str] = "PUBLIC_EXECUTION_VENUE_SNAPSHOT"
    SCHEMA_ID: ClassVar[str] = SNAPSHOT_SCHEMA_ID
    ID_FIELD: ClassVar[str] = "venue_snapshot_id"
    ID_PREFIX: ClassVar[str] = SNAPSHOT_ID_PREFIX
    INVARIANT_TRUE_FIELDS: ClassVar[tuple[str, ...]] = (
        "public_only",
        "no_account_state",
        "no_order_authority",
        "no_execution_authority",
        "no_live_authority",
    )

    def _field_value(self, name: str) -> object:
        if name in ("bids", "asks"):
            return [{"price": p, "size": s} for p, s in getattr(self, name)]
        return _plain(getattr(self, name))

    @classmethod
    def _coerce(cls, name: str, value: object) -> object:
        if name in ("bids", "asks"):
            if not isinstance(value, list):
                raise _fail("FIELD_TYPE_INVALID")
            levels = []
            for level in value:
                if not isinstance(level, Mapping) or set(level) != {"price", "size"}:
                    raise _fail("FIELD_VALUE_INVALID")
                levels.append((level["price"], level["size"]))
            return tuple(levels)
        return super()._coerce(name, value)

    def _validate(self) -> None:
        validate_gamma_market_id(self.gamma_market_id)
        validate_condition_id(self.condition_id)
        validate_token_id(self.token_id)
        started = _require_int(self.acquisition_started_ns)
        if _require_int(self.acquisition_completed_ns) < started:
            raise _fail("FIELD_VALUE_INVALID")
        gamma_state = _choice(self.gamma_source_state, SOURCE_STATES)
        clob_state = _choice(self.clob_source_state, SOURCE_STATES)
        for state, digest in (
            (gamma_state, _optional_hex64(self.gamma_payload_sha256)),
            (clob_state, _optional_hex64(self.clob_payload_sha256)),
        ):
            if (state == "AVAILABLE" and digest is None) or (
                state == "UNAVAILABLE" and digest is not None
            ):
                raise _fail("FIELD_VALUE_INVALID")
        for name in ("active", "closed", "accepting_orders", "enable_order_book",
                     "restricted", "gamma_neg_risk", "fees_enabled", "fee_taker_only",
                     "book_neg_risk"):
            _optional_bool(getattr(self, name))
        for name in ("gamma_tick_size", "book_tick_size"):
            tick = _optional_decimal(getattr(self, name))
            if tick is not None and not Decimal(0) < tick < Decimal(1):
                raise _fail("FIELD_VALUE_INVALID")
        for name in ("gamma_min_order_notional_usd", "book_min_order_size_raw"):
            minimum = _optional_decimal(getattr(self, name))
            if minimum is not None and minimum <= 0:
                raise _fail("FIELD_VALUE_INVALID")
        for name in ("fee_rate", "fee_exponent", "fee_rebate_rate"):
            amount = _optional_decimal(getattr(self, name))
            if amount is not None and amount < 0:
                raise _fail("FIELD_VALUE_INVALID")
        _optional_int(self.seconds_delay, high=MAX_SECONDS_DELAY)
        last = _optional_decimal(self.last_trade_price)
        if last is not None and not Decimal(0) <= last <= Decimal(1):
            raise _fail("FIELD_VALUE_INVALID")
        _optional_int(self.book_timestamp_ns)
        if self.book_hash is not None and _BOOK_HASH_RE.fullmatch(
            _require_str(self.book_hash)
        ) is None:
            raise _fail("FIELD_VALUE_INVALID")
        if self.book_condition_id is not None:
            validate_condition_id(self.book_condition_id)
        if self.book_token_id is not None:
            validate_token_id(self.book_token_id)
        bids = _levels(self.bids, descending=True)
        asks = _levels(self.asks, descending=False)
        if bids and asks and Decimal(bids[0][0]) >= Decimal(asks[0][0]):
            raise _fail("FIELD_VALUE_INVALID")
        if gamma_state != "AVAILABLE" and any(
            getattr(self, name) is not None for name in GAMMA_FACT_FIELDS
        ):
            raise _fail("FIELD_VALUE_INVALID")
        if clob_state != "AVAILABLE":
            if bids or asks or any(getattr(self, n) is not None for n in CLOB_FACT_FIELDS):
                raise _fail("FIELD_VALUE_INVALID")
        else:
            if any(getattr(self, name) is None for name in _REQUIRED_CLOB_FACTS):
                raise _fail("FIELD_VALUE_INVALID")
            if (self.book_condition_id, self.book_token_id) != (
                self.condition_id,
                self.token_id,
            ):
                raise _fail("FIELD_VALUE_INVALID")
        codes = _diagnostics(self.diagnostic_codes, SNAPSHOT_DIAGNOSTIC_CODES)
        expected = {
            "SOURCE_GAMMA_UNAVAILABLE": gamma_state == "UNAVAILABLE",
            "SOURCE_CLOB_UNAVAILABLE": clob_state == "UNAVAILABLE",
            "SOURCE_GAMMA_INVALID": gamma_state == "INVALID",
            "SOURCE_CLOB_INVALID": clob_state == "INVALID",
        }
        for code, present in expected.items():
            if (code in codes) != present:
                raise _fail("FIELD_VALUE_INVALID")
        if "SOURCE_IDENTITY_MISMATCH" in codes and "INVALID" not in (gamma_state, clob_state):
            raise _fail("FIELD_VALUE_INVALID")
        if "BOOK_INVALID" in codes and clob_state != "INVALID":
            raise _fail("FIELD_VALUE_INVALID")
        if "FEE_CONFIG_UNKNOWN" in codes and (
            gamma_state != "AVAILABLE"
            or any(getattr(self, n) is not None for n in
                   ("fee_rate", "fee_exponent", "fee_taker_only", "fee_rebate_rate"))
        ):
            raise _fail("FIELD_VALUE_INVALID")


def validate_public_venue_snapshot(snapshot: object) -> PublicExecutionVenueSnapshot:
    if type(snapshot) is not PublicExecutionVenueSnapshot:
        raise _fail("FIELD_TYPE_INVALID")
    if PublicExecutionVenueSnapshot.from_mapping(snapshot.to_mapping()) != snapshot:
        raise _fail("INTERNAL_VALIDATION_FAILED")
    return snapshot


# ---------------------------------------------------------------------------
# Record 3: ExecutionFeasibilityAssessment.
# ---------------------------------------------------------------------------

_ASSESSMENT_DECIMAL_FIELDS = (
    "best_bid",
    "best_ask",
    "spread",
    "requested_shares",
    "visible_fill_shares",
    "fill_ratio",
    "weighted_execution_price",
    "slippage_per_share",
    "slippage_cost_usd",
    "visible_depth_capacity_shares",
    "price_bound_capacity_shares",
    "minimum_order_notional_usd",
    "intent_notional_at_price_limit_usd",
    "theoretical_fee_unrounded_usd",
    "fee_upper_bound_usd",
    "maker_rebate_rate",
)
_AGGRESSIVE_METRIC_FIELDS = (
    "visible_fill_shares",
    "fill_ratio",
    "weighted_execution_price",
    "slippage_per_share",
    "slippage_cost_usd",
    "visible_depth_capacity_shares",
    "price_bound_capacity_shares",
)


def derive_status(dimensions: Mapping[str, str]) -> str:
    """Frozen precedence: hard FAIL > required UNKNOWN > V1 LIMITED > FEASIBLE."""

    states = [dimensions[name] for name in DIMENSIONS]
    if "FAIL" in states:
        return "NOT_FEASIBLE"
    if "UNKNOWN" in states:
        return "INCONCLUSIVE"
    if "LIMITED" in states:
        return "LIMITED"
    return "FEASIBLE"


@dataclass(frozen=True)
class ExecutionFeasibilityAssessment(_Record):
    """Current-public mechanical feasibility of one exact intent; no profitability claim."""

    execution_feasibility_assessment_id: str
    strategy_version_id: str
    execution_rule_sha256: str
    execution_intent_id: str
    venue_snapshot_id: str
    information_cutoff_ns: int
    evaluated_at_ns: int
    status: str
    market_dimension: str
    identity_dimension: str
    freshness_dimension: str
    tick_dimension: str
    minimum_order_dimension: str
    book_dimension: str
    fill_dimension: str
    fee_dimension: str
    delay_dimension: str
    best_bid: str | None
    best_ask: str | None
    spread: str | None
    requested_shares: str
    visible_fill_shares: str | None
    fill_ratio: str | None
    weighted_execution_price: str | None
    slippage_per_share: str | None
    slippage_cost_usd: str | None
    visible_depth_capacity_shares: str | None
    price_bound_capacity_shares: str | None
    minimum_order_notional_usd: str | None
    intent_notional_at_price_limit_usd: str
    fee_exactness: str
    theoretical_fee_unrounded_usd: str | None
    fee_upper_bound_usd: str | None
    maker_rebate_rate: str | None
    expected_maker_rebate_usd: None
    seconds_delay: int | None
    client_latency_state: str
    client_latency_ns: None
    passive_fill_state: str
    passive_fill_probability: None
    adverse_selection_state: str
    adverse_selection_cost: None
    diagnostic_codes: tuple[str, ...]
    schema_id: str = ASSESSMENT_SCHEMA_ID
    schema_version: str = SCHEMA_VERSION
    public_mechanics_only: bool = True
    no_profitability_claim: bool = True
    no_account_capacity_claim: bool = True
    no_gate_c_authority: bool = True
    no_order_authority: bool = True
    no_execution_authority: bool = True
    no_live_authority: bool = True

    RECORD_KIND: ClassVar[str] = "EXECUTION_FEASIBILITY_ASSESSMENT"
    SCHEMA_ID: ClassVar[str] = ASSESSMENT_SCHEMA_ID
    ID_FIELD: ClassVar[str] = "execution_feasibility_assessment_id"
    ID_PREFIX: ClassVar[str] = ASSESSMENT_ID_PREFIX
    INVARIANT_TRUE_FIELDS: ClassVar[tuple[str, ...]] = (
        "public_mechanics_only",
        "no_profitability_claim",
        "no_account_capacity_claim",
        "no_gate_c_authority",
        "no_order_authority",
        "no_execution_authority",
        "no_live_authority",
    )

    def _validate(self) -> None:
        _prefixed_id(self.strategy_version_id, STRATEGY_VERSION_PREFIX)
        _prefixed_id(self.execution_rule_sha256, EXECUTION_RULE_PREFIX)
        _prefixed_id(self.execution_intent_id, INTENT_ID_PREFIX)
        _prefixed_id(self.venue_snapshot_id, SNAPSHOT_ID_PREFIX)
        _require_int(self.information_cutoff_ns)
        _require_int(self.evaluated_at_ns)
        dims = {name: _choice(getattr(self, name), EXECUTION_DIMENSION_STATES)
                for name in DIMENSIONS}
        if _choice(self.status, EXECUTION_FEASIBILITY_STATUSES) != derive_status(dims):
            raise _fail("FIELD_VALUE_INVALID")
        values = {name: _optional_decimal(getattr(self, name), derived=True)
                  for name in _ASSESSMENT_DECIMAL_FIELDS}
        if values["requested_shares"] is None or values["requested_shares"] <= 0:
            raise _fail("FIELD_VALUE_INVALID")
        if values["intent_notional_at_price_limit_usd"] is None:
            raise _fail("FIELD_VALUE_INVALID")
        if any(value is not None and value < 0 for value in values.values()):
            raise _fail("FIELD_VALUE_INVALID")
        exactness = _choice(self.fee_exactness, FEE_EXACTNESS)
        unrounded, bound = values["theoretical_fee_unrounded_usd"], values["fee_upper_bound_usd"]
        if (exactness == "UNKNOWN") != (unrounded is None) or (unrounded is None) != (
            bound is None
        ):
            raise _fail("FIELD_VALUE_INVALID")
        if exactness in ("EXACT_ZERO_NO_FEES", "EXACT_ZERO_MAKER") and (
            unrounded != 0 or bound != 0
        ):
            raise _fail("FIELD_VALUE_INVALID")
        if unrounded is not None and bound < unrounded:  # type: ignore[operator]
            raise _fail("FIELD_VALUE_INVALID")
        _optional_int(self.seconds_delay, high=MAX_SECONDS_DELAY)
        passive = self.delay_dimension == "NOT_APPLICABLE"
        frozen_unknowns = (
            self.expected_maker_rebate_usd,
            self.client_latency_ns,
            self.passive_fill_probability,
            self.adverse_selection_cost,
        )
        if any(value is not None for value in frozen_unknowns):
            raise _fail("FIELD_VALUE_INVALID")
        if self.client_latency_state != "UNKNOWN" or self.adverse_selection_state != "UNKNOWN":
            raise _fail("FIELD_VALUE_INVALID")
        if self.passive_fill_state != ("UNKNOWN" if passive else "NOT_APPLICABLE"):
            raise _fail("FIELD_VALUE_INVALID")
        if passive and any(values[name] is not None for name in _AGGRESSIVE_METRIC_FIELDS):
            raise _fail("FIELD_VALUE_INVALID")
        codes = _diagnostics(self.diagnostic_codes, DIAGNOSTIC_CODES)
        for code in ("CLIENT_LATENCY_UNKNOWN", "ADVERSE_SELECTION_UNKNOWN"):
            if code not in codes:
                raise _fail("FIELD_VALUE_INVALID")
        if ("PASSIVE_FILL_UNKNOWN" in codes) != passive:
            raise _fail("FIELD_VALUE_INVALID")


RECORD_TYPES: dict[str, type] = {
    cls.RECORD_KIND: cls
    for cls in (ExecutionIntent, PublicExecutionVenueSnapshot, ExecutionFeasibilityAssessment)
}
RECORD_KINDS = tuple(RECORD_TYPES)


def record_from_mapping(record_kind: str, mapping: object):
    """Exact closed loader for the three content-addressed record kinds."""

    cls = RECORD_TYPES.get(record_kind) if isinstance(record_kind, str) else None
    if cls is None:
        raise _fail("SCHEMA_UNSUPPORTED")
    return cls.from_mapping(mapping)
