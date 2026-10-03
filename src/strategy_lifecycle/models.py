"""Immutable strategy-lifecycle records (S10-STRAT-LIFE-01).

Local, deterministic, stdlib-only records for the V2.1 strategy lifecycle and global
portfolio-authority substrate: strategy families and versions with parent lineage,
derived bounded-vs-material adaptation classification, the global
PortfolioAuthorityPolicy and its activation/revocation receipts, strategy health
receipts, strategy risk allocations, and strategy-local restriction receipts.

Every record is frozen and content-addressed: its ID is a fixed prefix plus the
SHA-256 of the canonical JSON of its public mapping with the ID field excluded. No
time, environment, or randomness is generated here. Records carry no credential,
order, paper, execution, or live authority; they are lifecycle metadata only.
Errors are closed stable codes that never echo caller payload.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, fields
from decimal import Decimal, InvalidOperation
import hashlib
import json
import re
from typing import ClassVar


SCHEMA_VERSION = "1.0.0"

FAMILY_SCHEMA_ID = "polymarket-strategy-family"
VERSION_SCHEMA_ID = "polymarket-strategy-version"
POLICY_SCHEMA_ID = "polymarket-portfolio-authority-policy"
POLICY_RECEIPT_SCHEMA_ID = "polymarket-portfolio-policy-receipt"
HEALTH_RECEIPT_SCHEMA_ID = "polymarket-strategy-health-receipt"
ALLOCATION_SCHEMA_ID = "polymarket-strategy-risk-allocation"
RESTRICTION_RECEIPT_SCHEMA_ID = "polymarket-strategy-restriction-receipt"

FAMILY_ID_PREFIX = "strategyfamily:sha256:"
VERSION_ID_PREFIX = "strategyversion:sha256:"
POLICY_ID_PREFIX = "portfolioauthoritypolicy:sha256:"
POLICY_RECEIPT_ID_PREFIX = "portfoliopolicyreceipt:sha256:"
HEALTH_RECEIPT_ID_PREFIX = "strategyhealth:sha256:"
ALLOCATION_ID_PREFIX = "strategyriskallocation:sha256:"
RESTRICTION_RECEIPT_ID_PREFIX = "strategyrestriction:sha256:"

ERROR_CODES = (
    "FIELD_TYPE_INVALID",
    "FIELD_VALUE_INVALID",
    "SCHEMA_CONFLICT",
    "INTEGRITY_TAMPER",
    "IDENTITY_CONFLICT",
    "REFERENCE_INVALID",
    "LINEAGE_INVALID",
    "ADAPTATION_INVALID",
    "POLICY_INVALID",
    "POLICY_TRANSITION_INVALID",
    "HEALTH_TRANSITION_INVALID",
    "ALLOCATION_INVALID",
    "RESTRICTION_TRANSITION_INVALID",
    "CAPACITY_INVALID",
    "LIMIT_EXCEEDED",
    "INTERNAL_VALIDATION_FAILED",
)

EVIDENCE_POSTURES = (
    "REPEATABLE_STATISTICAL",
    "EVENT_INFORMATION",
    "RELATIVE_VALUE_STRUCTURAL",
    "MICROSTRUCTURE_MAKER",
    "WALLET_DEPENDENT",
    "NOVEL_EXPLORATORY",
)
ADAPTATION_CLASSES = ("ROOT", "BOUNDED_ADAPTATION", "MATERIAL_ADAPTATION")
RISK_BANDS = ("PAPER", "EXPLORATORY_LIVE", "VALIDATED_LIVE", "MATURE_LIVE")
HEALTH_STATES = ("NEW", "HEALTHY", "WATCH", "DEGRADED", "QUARANTINED", "RETIRED")
ALLOCATION_BASES = ("DIRECT_DECISION", "PARENT_INHERITANCE")
POLICY_RECEIPT_ACTIONS = ("ACTIVATE", "REVOKE")
RESTRICTION_ACTIONS = ("APPLY", "CLEAR")
RESTRICTION_KINDS = ("PAUSE_NEW_EXPOSURE", "PAPER_ONLY", "ACTIVE_BUDGET_CAP")
ORDER_STYLES = ("AGGRESSIVE_TAKER", "PASSIVE_MAKER")
VENUE_SCOPE = ("POLYMARKET",)
ADAPTIVE_BOUND_KINDS = ("INTEGER_RANGE", "DECIMAL_RANGE", "ENUM")
STRATEGY_SPEC_KEYS = (
    "thesis",
    "universe",
    "entry_rule",
    "exit_rule",
    "execution_rule",
    "parameters",
)
STRATEGY_RULE_KEYS = STRATEGY_SPEC_KEYS[:5]

MAX_STRATEGY_SPEC_BYTES = 65_536
MAX_JSON_DEPTH = 8
MAX_JSON_NODES = 4_096
MAX_PARAMETERS = 256
MAX_EVIDENCE_REFS = 256
MAX_ENUM_VALUES = 256
MAX_TIME_NS = 2**63 - 1
_MAX_ABS_INT = 2**63 - 1

_ID_HEX_RE = re.compile(r"[0-9a-f]{64}")
_FAMILY_KEY_RE = re.compile(r"[a-z][a-z0-9_.-]{0,127}")
_PARAMETER_RE = re.compile(r"[a-z][a-z0-9_]{0,63}")
_RESTRICTION_KEY_RE = re.compile(r"[a-z][a-z0-9_.-]{0,127}")
_REF_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:@+=#-]{0,255}")
_DRIVE_PREFIX_RE = re.compile(r"[A-Za-z]:")
_PRIVATE_KEY_HEX_RE = re.compile(r"0x[0-9a-f]{64}(?![0-9a-f])", re.IGNORECASE)
_SECRET_MARKERS = (
    "secret",
    "password",
    "passwd",
    "passphrase",
    "mnemon",
    "privatekey",
    "apikey",
    "seedphrase",
    "bearer",
    "credential",
    "authtoken",
    "accesstoken",
)
_DECIMAL_RE = re.compile(r"-?(?:0|[1-9][0-9]{0,29})(?:\.[0-9]{0,17}[1-9])?")
_MONEY_RE = re.compile(r"(?:0|[1-9][0-9]{0,29})(?:\.[0-9]{0,17}[1-9])?")
_MAX_LABEL_CHARS = 200
_MAX_ENUM_VALUE_CHARS = 128


class StrategyLifecycleError(ValueError):
    """Closed, payload-free lifecycle validation failure."""

    def __init__(self, code: str) -> None:
        if code not in ERROR_CODES:
            code = "INTERNAL_VALIDATION_FAILED"
        super().__init__(code)
        self.code = code


def _fail(code: str) -> StrategyLifecycleError:
    return StrategyLifecycleError(code)


# ---------------------------------------------------------------------------
# Canonical JSON.
# ---------------------------------------------------------------------------


def _check_json_value(value: object, depth: int, counter: list[int]) -> None:
    counter[0] += 1
    if counter[0] > MAX_JSON_NODES:
        raise _fail("LIMIT_EXCEEDED")
    if value is None or isinstance(value, (bool, str)):
        return
    if isinstance(value, int):
        if abs(value) > _MAX_ABS_INT:
            raise _fail("FIELD_VALUE_INVALID")
        return
    if isinstance(value, float):
        raise _fail("FIELD_TYPE_INVALID")
    if isinstance(value, (list, tuple)):
        if depth >= MAX_JSON_DEPTH:
            raise _fail("LIMIT_EXCEEDED")
        for item in value:
            _check_json_value(item, depth + 1, counter)
        return
    if isinstance(value, Mapping):
        if depth >= MAX_JSON_DEPTH:
            raise _fail("LIMIT_EXCEEDED")
        for key, item in value.items():
            if not isinstance(key, str):
                raise _fail("FIELD_TYPE_INVALID")
            _check_json_value(item, depth + 1, counter)
        return
    raise _fail("FIELD_TYPE_INVALID")


def canonical_json_text(value: object) -> str:
    """Return the frozen canonical JSON text; floats, NaN and non-JSON types reject."""

    _check_json_value(value, 0, [0])
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
    except (TypeError, ValueError):
        raise _fail("FIELD_VALUE_INVALID") from None


def canonical_json_bytes(value: object) -> bytes:
    return canonical_json_text(value).encode("utf-8")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise _fail("FIELD_VALUE_INVALID")
        result[key] = value
    return result


def _reject_constant(_token: str) -> object:
    raise _fail("FIELD_TYPE_INVALID")


def _reject_float(_token: str) -> object:
    raise _fail("FIELD_TYPE_INVALID")


def strict_json_loads(text: object) -> object:
    """Strict decode: duplicate keys, floats, NaN and Infinity reject."""

    if not isinstance(text, str):
        raise _fail("FIELD_TYPE_INVALID")
    try:
        return json.loads(
            text,
            object_pairs_hook=_reject_duplicate_keys,
            parse_float=_reject_float,
            parse_constant=_reject_constant,
        )
    except StrategyLifecycleError:
        raise
    except (ValueError, TypeError, RecursionError):
        raise _fail("FIELD_VALUE_INVALID") from None


# ---------------------------------------------------------------------------
# Field validators.
# ---------------------------------------------------------------------------


def _require_str(value: object) -> str:
    if not isinstance(value, str):
        raise _fail("FIELD_TYPE_INVALID")
    return value


def _require_int(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise _fail("FIELD_TYPE_INVALID")
    return value


def _time_ns(value: object) -> int:
    number = _require_int(value)
    if not 0 <= number <= MAX_TIME_NS:
        raise _fail("FIELD_VALUE_INVALID")
    return number


def _optional_time_ns(value: object) -> int | None:
    return None if value is None else _time_ns(value)


def _count(value: object) -> int:
    number = _require_int(value)
    if not 0 <= number <= _MAX_ABS_INT:
        raise _fail("FIELD_VALUE_INVALID")
    return number


def _choice(value: object, choices: tuple[str, ...]) -> str:
    text = _require_str(value)
    if text not in choices:
        raise _fail("FIELD_VALUE_INVALID")
    return text


def _label(value: object) -> str:
    text = _require_str(value)
    if (
        not 1 <= len(text) <= _MAX_LABEL_CHARS
        or text != text.strip()
        or not text.isprintable()
    ):
        raise _fail("FIELD_VALUE_INVALID")
    return text


def _is_secret_like(text: str) -> bool:
    normalized = re.sub(r"[_.:@+=#-]", "", text.lower())
    if any(marker in normalized for marker in _SECRET_MARKERS):
        return True
    return _PRIVATE_KEY_HEX_RE.search(text) is not None


def opaque_ref(value: object) -> str:
    """Validate a bounded, non-path, non-secret opaque reference."""

    text = _require_str(value)
    if (
        _REF_RE.fullmatch(text) is None
        or ".." in text
        or _DRIVE_PREFIX_RE.match(text) is not None
        or _is_secret_like(text)
    ):
        raise _fail("FIELD_VALUE_INVALID")
    return text


def _record_id(value: object, prefix: str) -> str:
    text = _require_str(value)
    if not text.startswith(prefix) or _ID_HEX_RE.fullmatch(text[len(prefix):]) is None:
        raise _fail("FIELD_VALUE_INVALID")
    return text


def _optional_record_id(value: object, prefix: str) -> str | None:
    return None if value is None else _record_id(value, prefix)


def _evidence_refs(value: object) -> tuple[str, ...]:
    if not isinstance(value, tuple):
        raise _fail("FIELD_TYPE_INVALID")
    if len(value) > MAX_EVIDENCE_REFS:
        raise _fail("LIMIT_EXCEEDED")
    refs = tuple(opaque_ref(item) for item in value)
    if len(set(refs)) != len(refs) or list(refs) != sorted(refs):
        raise _fail("FIELD_VALUE_INVALID")
    return refs


def money(value: object) -> Decimal:
    """Parse one canonical non-negative decimal-string USD amount."""

    text = _require_str(value)
    if _MONEY_RE.fullmatch(text) is None:
        raise _fail("FIELD_VALUE_INVALID")
    return Decimal(text)


def _signed_decimal(value: object) -> Decimal:
    text = _require_str(value)
    if _DECIMAL_RE.fullmatch(text) is None or text == "-0":
        raise _fail("FIELD_VALUE_INVALID")
    try:
        return Decimal(text)
    except InvalidOperation:  # pragma: no cover - grammar already enforced
        raise _fail("FIELD_VALUE_INVALID") from None


def decimal_to_canonical(value: Decimal) -> str:
    """Render a finite non-negative Decimal in the canonical money grammar."""

    if not value.is_finite() or value < 0:
        raise _fail("INTERNAL_VALIDATION_FAILED")
    if value == 0:
        return "0"
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


def _ordered_tuple(value: object, vocabulary: tuple[str, ...]) -> tuple[str, ...]:
    if not isinstance(value, tuple) or not value:
        raise _fail("FIELD_VALUE_INVALID" if isinstance(value, tuple) else "FIELD_TYPE_INVALID")
    for item in value:
        _choice(item, vocabulary)
    if len(set(value)) != len(value) or list(value) != sorted(value, key=vocabulary.index):
        raise _fail("FIELD_VALUE_INVALID")
    return value


# ---------------------------------------------------------------------------
# Strategy specification and adaptive bounds.
# ---------------------------------------------------------------------------


def _canonical_json_object_text(value: object, *, max_bytes: int) -> dict[str, object]:
    text = _require_str(value)
    if len(text.encode("utf-8")) > max_bytes:
        raise _fail("LIMIT_EXCEEDED")
    decoded = strict_json_loads(text)
    if not isinstance(decoded, dict):
        raise _fail("FIELD_VALUE_INVALID")
    if canonical_json_text(decoded) != text:
        raise _fail("FIELD_VALUE_INVALID")
    return decoded


def parse_strategy_spec(value: object) -> dict[str, object]:
    """Validate canonical strategy_spec_json text and return its decoded object."""

    spec = _canonical_json_object_text(value, max_bytes=MAX_STRATEGY_SPEC_BYTES)
    if set(spec) != set(STRATEGY_SPEC_KEYS):
        raise _fail("FIELD_VALUE_INVALID")
    for key in STRATEGY_SPEC_KEYS:
        if not isinstance(spec[key], dict):
            raise _fail("FIELD_VALUE_INVALID")
    parameters = spec["parameters"]
    if len(parameters) > MAX_PARAMETERS:
        raise _fail("LIMIT_EXCEEDED")
    for name in parameters:
        if _PARAMETER_RE.fullmatch(name) is None:
            raise _fail("FIELD_VALUE_INVALID")
    return spec


def _validate_bound(bound: object) -> dict[str, object]:
    if not isinstance(bound, dict):
        raise _fail("FIELD_VALUE_INVALID")
    kind = bound.get("kind")
    if kind == "INTEGER_RANGE":
        if set(bound) != {"kind", "min", "max"}:
            raise _fail("FIELD_VALUE_INVALID")
        low, high = _require_int(bound["min"]), _require_int(bound["max"])
        if low > high:
            raise _fail("FIELD_VALUE_INVALID")
    elif kind == "DECIMAL_RANGE":
        if set(bound) != {"kind", "min", "max"}:
            raise _fail("FIELD_VALUE_INVALID")
        if _signed_decimal(bound["min"]) > _signed_decimal(bound["max"]):
            raise _fail("FIELD_VALUE_INVALID")
    elif kind == "ENUM":
        if set(bound) != {"kind", "values"}:
            raise _fail("FIELD_VALUE_INVALID")
        values = bound["values"]
        if not isinstance(values, list) or not 1 <= len(values) <= MAX_ENUM_VALUES:
            raise _fail("FIELD_VALUE_INVALID")
        for item in values:
            text = _require_str(item)
            if not 1 <= len(text) <= _MAX_ENUM_VALUE_CHARS or not text.isprintable():
                raise _fail("FIELD_VALUE_INVALID")
        if len(set(values)) != len(values):
            raise _fail("FIELD_VALUE_INVALID")
    else:
        raise _fail("FIELD_VALUE_INVALID")
    return bound


def value_within_bound(value: object, bound: Mapping[str, object]) -> bool:
    """Mechanical bound membership; malformed values are simply outside."""

    kind = bound["kind"]
    if kind == "INTEGER_RANGE":
        return (
            isinstance(value, int)
            and not isinstance(value, bool)
            and bound["min"] <= value <= bound["max"]  # type: ignore[operator]
        )
    if kind == "DECIMAL_RANGE":
        try:
            number = _signed_decimal(value)
        except StrategyLifecycleError:
            return False
        return Decimal(bound["min"]) <= number <= Decimal(bound["max"])  # type: ignore[arg-type]
    return isinstance(value, str) and value in bound["values"]  # type: ignore[operator]


def parse_adaptive_bounds(value: object, spec: Mapping[str, object]) -> dict[str, object]:
    """Validate canonical adaptive_bounds_json against its own strategy spec.

    A bound frozen on a version limits how far a bounded child may move that
    parameter; it does not constrain the declaring version's own value.
    """

    bounds = _canonical_json_object_text(value, max_bytes=MAX_STRATEGY_SPEC_BYTES)
    parameters = spec["parameters"]
    for name, bound in bounds.items():
        if name not in parameters:  # type: ignore[operator]
            raise _fail("FIELD_VALUE_INVALID")
        _validate_bound(bound)
    return bounds


# ---------------------------------------------------------------------------
# Content-addressed record base.
# ---------------------------------------------------------------------------


class _PendingId:
    __slots__ = ()

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return "<pending-id>"


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
    TUPLE_FIELDS: ClassVar[tuple[str, ...]] = ()

    def _validate(self) -> None:  # pragma: no cover - overridden
        raise NotImplementedError

    def __post_init__(self) -> None:
        if getattr(self, "schema_id") != self.SCHEMA_ID or getattr(
            self, "schema_version"
        ) != SCHEMA_VERSION:
            raise _fail("FIELD_VALUE_INVALID")
        self._validate()
        computed = self.ID_PREFIX + sha256_hex(canonical_json_bytes(self._preimage()))
        current = getattr(self, self.ID_FIELD)
        if current is _PENDING_ID:
            object.__setattr__(self, self.ID_FIELD, computed)
            return
        _record_id(current, self.ID_PREFIX)
        if current != computed:
            raise _fail("IDENTITY_CONFLICT")

    def _preimage(self) -> dict[str, object]:
        return {
            item.name: _plain(getattr(self, item.name))
            for item in fields(self)  # type: ignore[arg-type]
            if item.name != self.ID_FIELD
        }

    @property
    def record_id(self) -> str:
        return getattr(self, self.ID_FIELD)

    def to_mapping(self) -> dict[str, object]:
        """Return the public JSON-compatible mapping (tuples become lists)."""

        return {
            item.name: _plain(getattr(self, item.name))
            for item in fields(self)  # type: ignore[arg-type]
        }

    @classmethod
    def from_mapping(cls, mapping: object):
        """Strictly load one exact public mapping and revalidate its content ID."""

        if not isinstance(mapping, Mapping):
            raise _fail("FIELD_TYPE_INVALID")
        names = [item.name for item in fields(cls)]  # type: ignore[arg-type]
        if set(mapping) != set(names):
            raise _fail("FIELD_VALUE_INVALID")
        values: dict[str, object] = {}
        for name in names:
            value = mapping[name]
            if name in cls.TUPLE_FIELDS:
                if not isinstance(value, list):
                    raise _fail("FIELD_TYPE_INVALID")
                value = tuple(value)
            values[name] = value
        if values[cls.ID_FIELD] is _PENDING_ID:
            raise _fail("FIELD_TYPE_INVALID")
        return cls(**values)


def _sorted_refs(refs: object) -> tuple[str, ...]:
    if isinstance(refs, (str, bytes, Mapping)) or not isinstance(refs, Iterable):
        raise _fail("FIELD_TYPE_INVALID")
    items = tuple(refs)
    if not all(isinstance(item, str) for item in items):
        raise _fail("FIELD_TYPE_INVALID")
    return tuple(sorted(items))


def _spec_text(value: object) -> str:
    if isinstance(value, Mapping):
        return canonical_json_text(dict(value))
    return _require_str(value)


# ---------------------------------------------------------------------------
# Strategy family / version.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class StrategyFamily(_Record):
    """Lineage grouping only; membership carries no trading/evidence/risk meaning."""

    strategy_family_id: str
    family_key: str
    family_label: str
    created_time_ns: int
    creation_provenance: str
    schema_id: str = FAMILY_SCHEMA_ID
    schema_version: str = SCHEMA_VERSION

    RECORD_KIND: ClassVar[str] = "STRATEGY_FAMILY"
    SCHEMA_ID: ClassVar[str] = FAMILY_SCHEMA_ID
    ID_FIELD: ClassVar[str] = "strategy_family_id"
    ID_PREFIX: ClassVar[str] = FAMILY_ID_PREFIX

    def _validate(self) -> None:
        if _FAMILY_KEY_RE.fullmatch(_require_str(self.family_key)) is None:
            raise _fail("FIELD_VALUE_INVALID")
        _label(self.family_label)
        _time_ns(self.created_time_ns)
        opaque_ref(self.creation_provenance)


@dataclass(frozen=True)
class StrategyVersion(_Record):
    """Immutable strategy version; evidence posture is advisory metadata only."""

    strategy_version_id: str
    strategy_family_id: str
    parent_strategy_version_id: str | None
    strategy_label: str
    evidence_posture: str
    strategy_code_identity: str
    strategy_spec_json: str
    adaptive_bounds_json: str
    evidence_refs: tuple[str, ...]
    created_time_ns: int
    creation_provenance: str
    adaptation_class: str
    schema_id: str = VERSION_SCHEMA_ID
    schema_version: str = SCHEMA_VERSION

    RECORD_KIND: ClassVar[str] = "STRATEGY_VERSION"
    SCHEMA_ID: ClassVar[str] = VERSION_SCHEMA_ID
    ID_FIELD: ClassVar[str] = "strategy_version_id"
    ID_PREFIX: ClassVar[str] = VERSION_ID_PREFIX
    TUPLE_FIELDS: ClassVar[tuple[str, ...]] = ("evidence_refs",)

    def _validate(self) -> None:
        _record_id(self.strategy_family_id, FAMILY_ID_PREFIX)
        _optional_record_id(self.parent_strategy_version_id, VERSION_ID_PREFIX)
        _label(self.strategy_label)
        _choice(self.evidence_posture, EVIDENCE_POSTURES)
        opaque_ref(self.strategy_code_identity)
        spec = parse_strategy_spec(self.strategy_spec_json)
        parse_adaptive_bounds(self.adaptive_bounds_json, spec)
        _evidence_refs(self.evidence_refs)
        _time_ns(self.created_time_ns)
        opaque_ref(self.creation_provenance)
        adaptation = _choice(self.adaptation_class, ADAPTATION_CLASSES)
        if (self.parent_strategy_version_id is None) != (adaptation == "ROOT"):
            raise _fail("ADAPTATION_INVALID")

    def semantic_key(self) -> tuple[str, str, str, str]:
        """The fields whose equality makes a child a forbidden no-op."""

        return (
            self.evidence_posture,
            self.strategy_code_identity,
            self.strategy_spec_json,
            self.adaptive_bounds_json,
        )


def _classify_child(
    parent: StrategyVersion,
    *,
    evidence_posture: str,
    strategy_code_identity: str,
    strategy_spec_json: str,
    adaptive_bounds_json: str,
) -> str:
    if (
        evidence_posture,
        strategy_code_identity,
        strategy_spec_json,
        adaptive_bounds_json,
    ) == parent.semantic_key():
        raise _fail("ADAPTATION_INVALID")
    if (
        evidence_posture != parent.evidence_posture
        or strategy_code_identity != parent.strategy_code_identity
        or adaptive_bounds_json != parent.adaptive_bounds_json
    ):
        return "MATERIAL_ADAPTATION"
    parent_spec = parse_strategy_spec(parent.strategy_spec_json)
    child_spec = parse_strategy_spec(strategy_spec_json)
    if any(parent_spec[key] != child_spec[key] for key in STRATEGY_RULE_KEYS):
        return "MATERIAL_ADAPTATION"
    parent_parameters = parent_spec["parameters"]
    child_parameters = child_spec["parameters"]
    if set(parent_parameters) != set(child_parameters):  # type: ignore[arg-type]
        return "MATERIAL_ADAPTATION"
    bounds = parse_adaptive_bounds(parent.adaptive_bounds_json, parent_spec)
    changed = [
        name
        for name in parent_parameters  # type: ignore[union-attr]
        if parent_parameters[name] != child_parameters[name]  # type: ignore[index]
    ]
    if not changed:
        return "MATERIAL_ADAPTATION"
    for name in changed:
        if name not in bounds or not value_within_bound(
            child_parameters[name], bounds[name]  # type: ignore[index]
        ):
            return "MATERIAL_ADAPTATION"
    return "BOUNDED_ADAPTATION"


def derive_adaptation_class(
    child: StrategyVersion, parent: StrategyVersion | None
) -> str:
    """Derive the mechanical adaptation class of ``child`` against its exact parent.

    Only mechanical boundedness is classified; no judgment of adaptation quality.
    """

    if not isinstance(child, StrategyVersion):
        raise _fail("FIELD_TYPE_INVALID")
    if parent is None:
        if child.parent_strategy_version_id is not None:
            raise _fail("REFERENCE_INVALID")
        return "ROOT"
    if not isinstance(parent, StrategyVersion):
        raise _fail("FIELD_TYPE_INVALID")
    if child.parent_strategy_version_id != parent.strategy_version_id:
        raise _fail("LINEAGE_INVALID")
    if child.strategy_family_id != parent.strategy_family_id:
        raise _fail("LINEAGE_INVALID")
    return _classify_child(
        parent,
        evidence_posture=child.evidence_posture,
        strategy_code_identity=child.strategy_code_identity,
        strategy_spec_json=child.strategy_spec_json,
        adaptive_bounds_json=child.adaptive_bounds_json,
    )


def validate_strategy_version_lineage(
    child: StrategyVersion, parent: StrategyVersion | None
) -> None:
    """Require exact lineage and declared == derived adaptation class."""

    derived = derive_adaptation_class(child, parent)
    if parent is not None and child.created_time_ns < parent.created_time_ns:
        raise _fail("LINEAGE_INVALID")
    if child.adaptation_class != derived:
        raise _fail("ADAPTATION_INVALID")


def build_strategy_family(
    *,
    family_key: str,
    family_label: str,
    created_time_ns: int,
    creation_provenance: str,
) -> StrategyFamily:
    return StrategyFamily(
        strategy_family_id=_PENDING_ID,  # type: ignore[arg-type]
        family_key=family_key,
        family_label=family_label,
        created_time_ns=created_time_ns,
        creation_provenance=creation_provenance,
    )


def build_strategy_version(
    *,
    strategy_family_id: str,
    parent: StrategyVersion | None,
    strategy_label: str,
    evidence_posture: str,
    strategy_code_identity: str,
    strategy_spec: Mapping[str, object] | str,
    adaptive_bounds: Mapping[str, object] | str,
    evidence_refs: Iterable[str] = (),
    created_time_ns: int,
    creation_provenance: str,
    adaptation_class: str | None = None,
) -> StrategyVersion:
    """Build a version; the adaptation class is derived from the exact parent."""

    if parent is not None and not isinstance(parent, StrategyVersion):
        raise _fail("FIELD_TYPE_INVALID")
    spec_text = _spec_text(strategy_spec)
    bounds_text = _spec_text(adaptive_bounds)
    if parent is None:
        derived = "ROOT"
    else:
        if parent.strategy_family_id != strategy_family_id:
            raise _fail("LINEAGE_INVALID")
        # Field validation runs before classification so malformed input fails closed.
        _choice(evidence_posture, EVIDENCE_POSTURES)
        opaque_ref(strategy_code_identity)
        parse_adaptive_bounds(bounds_text, parse_strategy_spec(spec_text))
        derived = _classify_child(
            parent,
            evidence_posture=evidence_posture,
            strategy_code_identity=strategy_code_identity,
            strategy_spec_json=spec_text,
            adaptive_bounds_json=bounds_text,
        )
    if adaptation_class is not None and adaptation_class != derived:
        raise _fail("ADAPTATION_INVALID")
    version = StrategyVersion(
        strategy_version_id=_PENDING_ID,  # type: ignore[arg-type]
        strategy_family_id=strategy_family_id,
        parent_strategy_version_id=None if parent is None else parent.strategy_version_id,
        strategy_label=strategy_label,
        evidence_posture=evidence_posture,
        strategy_code_identity=strategy_code_identity,
        strategy_spec_json=spec_text,
        adaptive_bounds_json=bounds_text,
        evidence_refs=_sorted_refs(evidence_refs),
        created_time_ns=created_time_ns,
        creation_provenance=creation_provenance,
        adaptation_class=derived,
    )
    validate_strategy_version_lineage(version, parent)
    return version


# ---------------------------------------------------------------------------
# Global portfolio authority policy and its receipts.
# ---------------------------------------------------------------------------

POLICY_MONEY_FIELDS = (
    "global_capital_at_risk_max_usd",
    "global_gross_exposure_max_usd",
    "global_daily_loss_max_usd",
    "global_drawdown_max_usd",
    "global_cumulative_loss_max_usd",
    "exploratory_pool_max_usd",
    "validated_pool_max_usd",
    "mature_pool_max_usd",
    "max_exploratory_per_strategy_usd",
    "max_validated_per_strategy_usd",
    "max_mature_per_strategy_usd",
    "max_per_market_usd",
    "max_order_notional_usd",
)
POLICY_COUNT_FIELDS = (
    "max_active_strategies",
    "max_active_markets",
    "max_simultaneous_open_orders",
    "max_mutations_per_minute",
)


@dataclass(frozen=True)
class PortfolioAuthorityPolicy(_Record):
    """Human-defined global outer envelope; a proposal until an ACTIVATE receipt exists.

    It creates no order and grants no paper, execution, credential or live authority.
    """

    policy_id: str
    predecessor_policy_id: str | None
    policy_label: str
    venue_scope: tuple[str, ...]
    account_scope_ref: str
    effective_from_ns: int
    expires_at_ns: int | None
    global_capital_at_risk_max_usd: str
    global_gross_exposure_max_usd: str
    global_daily_loss_max_usd: str
    global_drawdown_max_usd: str
    global_cumulative_loss_max_usd: str
    exploratory_pool_max_usd: str
    validated_pool_max_usd: str
    mature_pool_max_usd: str
    max_exploratory_per_strategy_usd: str
    max_validated_per_strategy_usd: str
    max_mature_per_strategy_usd: str
    max_per_market_usd: str
    max_active_strategies: int
    max_active_markets: int
    max_simultaneous_open_orders: int
    max_order_notional_usd: str
    max_mutations_per_minute: int
    allowed_order_styles: tuple[str, ...]
    created_time_ns: int
    schema_id: str = POLICY_SCHEMA_ID
    schema_version: str = SCHEMA_VERSION

    RECORD_KIND: ClassVar[str] = "PORTFOLIO_AUTHORITY_POLICY"
    SCHEMA_ID: ClassVar[str] = POLICY_SCHEMA_ID
    ID_FIELD: ClassVar[str] = "policy_id"
    ID_PREFIX: ClassVar[str] = POLICY_ID_PREFIX
    TUPLE_FIELDS: ClassVar[tuple[str, ...]] = ("venue_scope", "allowed_order_styles")

    def _validate(self) -> None:
        _optional_record_id(self.predecessor_policy_id, POLICY_ID_PREFIX)
        _label(self.policy_label)
        if not isinstance(self.venue_scope, tuple):
            raise _fail("FIELD_TYPE_INVALID")
        if self.venue_scope != VENUE_SCOPE:
            raise _fail("FIELD_VALUE_INVALID")
        opaque_ref(self.account_scope_ref)
        created = _time_ns(self.created_time_ns)
        effective = _time_ns(self.effective_from_ns)
        expires = _optional_time_ns(self.expires_at_ns)
        amounts = {name: money(getattr(self, name)) for name in POLICY_MONEY_FIELDS}
        for name in POLICY_COUNT_FIELDS:
            _count(getattr(self, name))
        _ordered_tuple(self.allowed_order_styles, ORDER_STYLES)
        if created > effective or (expires is not None and expires <= effective):
            raise _fail("POLICY_INVALID")
        if (
            amounts["exploratory_pool_max_usd"]
            + amounts["validated_pool_max_usd"]
            + amounts["mature_pool_max_usd"]
            > amounts["global_capital_at_risk_max_usd"]
            or amounts["max_exploratory_per_strategy_usd"] > amounts["exploratory_pool_max_usd"]
            or amounts["max_validated_per_strategy_usd"] > amounts["validated_pool_max_usd"]
            or amounts["max_mature_per_strategy_usd"] > amounts["mature_pool_max_usd"]
            or amounts["max_per_market_usd"] > amounts["global_gross_exposure_max_usd"]
            or amounts["max_order_notional_usd"] > amounts["max_per_market_usd"]
        ):
            raise _fail("POLICY_INVALID")

    def pool_max(self, risk_band: str) -> Decimal:
        return {
            "EXPLORATORY_LIVE": money(self.exploratory_pool_max_usd),
            "VALIDATED_LIVE": money(self.validated_pool_max_usd),
            "MATURE_LIVE": money(self.mature_pool_max_usd),
        }[risk_band]

    def per_strategy_max(self, risk_band: str) -> Decimal:
        return {
            "PAPER": Decimal(0),
            "EXPLORATORY_LIVE": money(self.max_exploratory_per_strategy_usd),
            "VALIDATED_LIVE": money(self.max_validated_per_strategy_usd),
            "MATURE_LIVE": money(self.max_mature_per_strategy_usd),
        }[risk_band]


def build_portfolio_authority_policy(
    *,
    predecessor_policy_id: str | None = None,
    policy_label: str,
    account_scope_ref: str,
    effective_from_ns: int,
    expires_at_ns: int | None,
    allowed_order_styles: Iterable[str],
    created_time_ns: int,
    venue_scope: Iterable[str] = VENUE_SCOPE,
    **limits: object,
) -> PortfolioAuthorityPolicy:
    """Build a policy; order styles are normalized to canonical vocabulary order."""

    expected = set(POLICY_MONEY_FIELDS) | set(POLICY_COUNT_FIELDS)
    if set(limits) != expected:
        raise _fail("FIELD_VALUE_INVALID")
    if isinstance(allowed_order_styles, (str, bytes)) or isinstance(venue_scope, (str, bytes)):
        raise _fail("FIELD_TYPE_INVALID")
    styles = tuple(allowed_order_styles)
    for style in styles:
        _choice(style, ORDER_STYLES)
    if len(set(styles)) != len(styles):
        raise _fail("FIELD_VALUE_INVALID")
    return PortfolioAuthorityPolicy(
        policy_id=_PENDING_ID,  # type: ignore[arg-type]
        predecessor_policy_id=predecessor_policy_id,
        policy_label=policy_label,
        venue_scope=tuple(venue_scope),
        account_scope_ref=account_scope_ref,
        effective_from_ns=effective_from_ns,
        expires_at_ns=expires_at_ns,
        allowed_order_styles=tuple(sorted(styles, key=ORDER_STYLES.index)),
        created_time_ns=created_time_ns,
        **limits,  # type: ignore[arg-type]
    )


@dataclass(frozen=True)
class PortfolioPolicyReceipt(_Record):
    """ACTIVATE/REVOKE receipt; activation needs a non-secret human authorization ref."""

    policy_receipt_id: str
    action: str
    policy_id: str
    previous_active_policy_id: str | None
    human_authorization_ref: str
    created_time_ns: int
    schema_id: str = POLICY_RECEIPT_SCHEMA_ID
    schema_version: str = SCHEMA_VERSION

    RECORD_KIND: ClassVar[str] = "PORTFOLIO_POLICY_RECEIPT"
    SCHEMA_ID: ClassVar[str] = POLICY_RECEIPT_SCHEMA_ID
    ID_FIELD: ClassVar[str] = "policy_receipt_id"
    ID_PREFIX: ClassVar[str] = POLICY_RECEIPT_ID_PREFIX

    def _validate(self) -> None:
        action = _choice(self.action, POLICY_RECEIPT_ACTIONS)
        policy_id = _record_id(self.policy_id, POLICY_ID_PREFIX)
        previous = _optional_record_id(self.previous_active_policy_id, POLICY_ID_PREFIX)
        opaque_ref(self.human_authorization_ref)
        _time_ns(self.created_time_ns)
        if action == "ACTIVATE" and previous == policy_id:
            raise _fail("POLICY_TRANSITION_INVALID")
        if action == "REVOKE" and previous != policy_id:
            raise _fail("POLICY_TRANSITION_INVALID")


def build_portfolio_policy_receipt(
    *,
    action: str,
    policy_id: str,
    previous_active_policy_id: str | None,
    human_authorization_ref: str,
    created_time_ns: int,
) -> PortfolioPolicyReceipt:
    return PortfolioPolicyReceipt(
        policy_receipt_id=_PENDING_ID,  # type: ignore[arg-type]
        action=action,
        policy_id=policy_id,
        previous_active_policy_id=previous_active_policy_id,
        human_authorization_ref=human_authorization_ref,
        created_time_ns=created_time_ns,
    )


# ---------------------------------------------------------------------------
# Strategy health, risk allocation, and strategy-local restrictions.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class StrategyHealthReceipt(_Record):
    """Health transition; independent of risk band and of any authority."""

    health_receipt_id: str
    strategy_version_id: str
    previous_health_state: str
    new_health_state: str
    decision_ref: str
    evidence_refs: tuple[str, ...]
    created_time_ns: int
    schema_id: str = HEALTH_RECEIPT_SCHEMA_ID
    schema_version: str = SCHEMA_VERSION

    RECORD_KIND: ClassVar[str] = "STRATEGY_HEALTH_RECEIPT"
    SCHEMA_ID: ClassVar[str] = HEALTH_RECEIPT_SCHEMA_ID
    ID_FIELD: ClassVar[str] = "health_receipt_id"
    ID_PREFIX: ClassVar[str] = HEALTH_RECEIPT_ID_PREFIX
    TUPLE_FIELDS: ClassVar[tuple[str, ...]] = ("evidence_refs",)

    def _validate(self) -> None:
        _record_id(self.strategy_version_id, VERSION_ID_PREFIX)
        previous = _choice(self.previous_health_state, HEALTH_STATES)
        new = _choice(self.new_health_state, HEALTH_STATES)
        opaque_ref(self.decision_ref)
        _evidence_refs(self.evidence_refs)
        _time_ns(self.created_time_ns)
        if new == "NEW" or previous == new or previous == "RETIRED":
            raise _fail("HEALTH_TRANSITION_INVALID")


def build_strategy_health_receipt(
    *,
    strategy_version_id: str,
    previous_health_state: str,
    new_health_state: str,
    decision_ref: str,
    evidence_refs: Iterable[str] = (),
    created_time_ns: int,
) -> StrategyHealthReceipt:
    return StrategyHealthReceipt(
        health_receipt_id=_PENDING_ID,  # type: ignore[arg-type]
        strategy_version_id=strategy_version_id,
        previous_health_state=previous_health_state,
        new_health_state=new_health_state,
        decision_ref=decision_ref,
        evidence_refs=_sorted_refs(evidence_refs),
        created_time_ns=created_time_ns,
    )


@dataclass(frozen=True)
class StrategyRiskAllocation(_Record):
    """Active budget reservation under the global policy; no order or live authority."""

    allocation_id: str
    strategy_version_id: str
    policy_id: str
    risk_band: str
    active_budget_usd: str
    allocation_basis: str
    decision_ref: str
    evidence_refs: tuple[str, ...]
    valid_from_ns: int
    valid_until_ns: int | None
    created_time_ns: int
    schema_id: str = ALLOCATION_SCHEMA_ID
    schema_version: str = SCHEMA_VERSION

    RECORD_KIND: ClassVar[str] = "STRATEGY_RISK_ALLOCATION"
    SCHEMA_ID: ClassVar[str] = ALLOCATION_SCHEMA_ID
    ID_FIELD: ClassVar[str] = "allocation_id"
    ID_PREFIX: ClassVar[str] = ALLOCATION_ID_PREFIX
    TUPLE_FIELDS: ClassVar[tuple[str, ...]] = ("evidence_refs",)

    def _validate(self) -> None:
        _record_id(self.strategy_version_id, VERSION_ID_PREFIX)
        _record_id(self.policy_id, POLICY_ID_PREFIX)
        band = _choice(self.risk_band, RISK_BANDS)
        money(self.active_budget_usd)
        _choice(self.allocation_basis, ALLOCATION_BASES)
        opaque_ref(self.decision_ref)
        _evidence_refs(self.evidence_refs)
        valid_from = _time_ns(self.valid_from_ns)
        valid_until = _optional_time_ns(self.valid_until_ns)
        _time_ns(self.created_time_ns)
        if band == "PAPER" and self.active_budget_usd != "0":
            raise _fail("ALLOCATION_INVALID")
        if valid_until is not None and valid_until <= valid_from:
            raise _fail("ALLOCATION_INVALID")

    def is_active_at(self, at_time_ns: int) -> bool:
        return self.valid_from_ns <= at_time_ns and (
            self.valid_until_ns is None or at_time_ns < self.valid_until_ns
        )


def build_strategy_risk_allocation(
    *,
    strategy_version_id: str,
    policy_id: str,
    risk_band: str,
    active_budget_usd: str,
    allocation_basis: str,
    decision_ref: str,
    evidence_refs: Iterable[str] = (),
    valid_from_ns: int,
    valid_until_ns: int | None,
    created_time_ns: int,
) -> StrategyRiskAllocation:
    return StrategyRiskAllocation(
        allocation_id=_PENDING_ID,  # type: ignore[arg-type]
        strategy_version_id=strategy_version_id,
        policy_id=policy_id,
        risk_band=risk_band,
        active_budget_usd=active_budget_usd,
        allocation_basis=allocation_basis,
        decision_ref=decision_ref,
        evidence_refs=_sorted_refs(evidence_refs),
        valid_from_ns=valid_from_ns,
        valid_until_ns=valid_until_ns,
        created_time_ns=created_time_ns,
    )


@dataclass(frozen=True)
class StrategyRestrictionReceipt(_Record):
    """Strategy-local APPLY/CLEAR restriction; never a global restriction."""

    restriction_receipt_id: str
    strategy_version_id: str
    restriction_key: str
    action: str
    restriction_kind: str
    max_active_budget_usd: str | None
    decision_ref: str
    evidence_refs: tuple[str, ...]
    created_time_ns: int
    schema_id: str = RESTRICTION_RECEIPT_SCHEMA_ID
    schema_version: str = SCHEMA_VERSION

    RECORD_KIND: ClassVar[str] = "STRATEGY_RESTRICTION_RECEIPT"
    SCHEMA_ID: ClassVar[str] = RESTRICTION_RECEIPT_SCHEMA_ID
    ID_FIELD: ClassVar[str] = "restriction_receipt_id"
    ID_PREFIX: ClassVar[str] = RESTRICTION_RECEIPT_ID_PREFIX
    TUPLE_FIELDS: ClassVar[tuple[str, ...]] = ("evidence_refs",)

    def _validate(self) -> None:
        _record_id(self.strategy_version_id, VERSION_ID_PREFIX)
        if _RESTRICTION_KEY_RE.fullmatch(_require_str(self.restriction_key)) is None:
            raise _fail("FIELD_VALUE_INVALID")
        _choice(self.action, RESTRICTION_ACTIONS)
        kind = _choice(self.restriction_kind, RESTRICTION_KINDS)
        if kind == "ACTIVE_BUDGET_CAP":
            if self.max_active_budget_usd is None:
                raise _fail("FIELD_VALUE_INVALID")
            money(self.max_active_budget_usd)
        elif self.max_active_budget_usd is not None:
            raise _fail("FIELD_VALUE_INVALID")
        opaque_ref(self.decision_ref)
        _evidence_refs(self.evidence_refs)
        _time_ns(self.created_time_ns)


def build_strategy_restriction_receipt(
    *,
    strategy_version_id: str,
    restriction_key: str,
    action: str,
    restriction_kind: str,
    max_active_budget_usd: str | None = None,
    decision_ref: str,
    evidence_refs: Iterable[str] = (),
    created_time_ns: int,
) -> StrategyRestrictionReceipt:
    return StrategyRestrictionReceipt(
        restriction_receipt_id=_PENDING_ID,  # type: ignore[arg-type]
        strategy_version_id=strategy_version_id,
        restriction_key=restriction_key,
        action=action,
        restriction_kind=restriction_kind,
        max_active_budget_usd=max_active_budget_usd,
        decision_ref=decision_ref,
        evidence_refs=_sorted_refs(evidence_refs),
        created_time_ns=created_time_ns,
    )


LifecycleRecord = (
    StrategyFamily
    | StrategyVersion
    | PortfolioAuthorityPolicy
    | PortfolioPolicyReceipt
    | StrategyHealthReceipt
    | StrategyRiskAllocation
    | StrategyRestrictionReceipt
)

RECORD_TYPES: dict[str, type] = {
    cls.RECORD_KIND: cls
    for cls in (
        StrategyFamily,
        StrategyVersion,
        PortfolioAuthorityPolicy,
        PortfolioPolicyReceipt,
        StrategyHealthReceipt,
        StrategyRiskAllocation,
        StrategyRestrictionReceipt,
    )
}
RECORD_KINDS = tuple(RECORD_TYPES)


def record_kind_of(record: object) -> str:
    for kind, cls in RECORD_TYPES.items():
        if type(record) is cls:
            return kind
    raise _fail("FIELD_TYPE_INVALID")


def record_from_mapping(record_kind: str, mapping: object) -> LifecycleRecord:
    """Load one exact public mapping of a closed record kind."""

    cls = RECORD_TYPES.get(record_kind) if isinstance(record_kind, str) else None
    if cls is None:
        raise _fail("FIELD_VALUE_INVALID")
    return cls.from_mapping(mapping)
