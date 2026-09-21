"""Canonical public wallet event model and contracts (S10-WALLET-01).

This module defines the deterministic, content-addressed record contracts for the
public wallet evidence foundation: canonical economic events, immutable source
observations, feed-page evidence, account-identity evidence, reconciliation
links, the wallet provenance extension, and the ingest-run receipt, plus the
context-typed external-identifier canonicalization, decimal canonicalization,
data-quality/replay integration, and the frozen closed public error vocabulary.

Posture: local, offline, stdlib-only, deterministic, in-memory. It records
observable PUBLIC evidence only. It has ZERO qualification, ranking, promotion,
copyability, profitability, sizing, order, signing, paper, live, scheduler, or
execution authority. No surface here decides whether a wallet is skilled or
copyable, and no field asserts human identity, beneficial ownership, or insider
allegations.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from decimal import Decimal
import json
import re
import unicodedata

from ..point_in_time_market_research.records import sha256_hex
from ..point_in_time_market_research.research_provenance import (
    PitTimestamps,
    canonicalize_dq_flags,
    canonicalize_utc_timestamp,
    validate_replay_fidelity,
)


WALLET_CONTRACTS_LABEL = "PUBLIC_WALLET_EVIDENCE_CANONICAL_CONTRACTS"
WALLET_CONTRACTS_POSTURE = "LOCAL_OFFLINE_STDLIB_ONLY_CONTENT_ADDRESSED_PUBLIC_ONLY"
IDENTITY_SCHEMA_VERSION = "1.0.0"

# ===========================================================================
# 19. Closed public error vocabulary + total internal -> public mapping.
# ===========================================================================
WALLET_PUBLIC_ERROR_CODES = (
    "FIELD_TYPE_INVALID",
    "FIELD_VALUE_INVALID",
    "SCHEMA_UNSUPPORTED",
    "ADDRESS_INVALID",
    "DECIMAL_INVALID",
    "IDENTITY_DERIVATION_MISMATCH",
    "REFERENCE_INVALID",
    "REFERENCE_TYPE_INVALID",
    "REFERENCE_CYCLE",
    "PIT_NOT_ADMISSIBLE",
    "PROVENANCE_INCOMPLETE",
    "DQ_STATE_INVALID",
    "CURSOR_INVALID",
    "CURSOR_GAP",
    "SOURCE_DISAGREEMENT",
    "SOURCE_UNAVAILABLE",
    "SOURCE_RESPONSE_INVALID",
    "RATE_LIMIT_GUARD_DENIED",
    "NETWORK_DISABLED",
    "NETWORK_HOST_FORBIDDEN",
    "NETWORK_SCHEME_FORBIDDEN",
    "RECONCILIATION_INVALID",
    "LEDGER_IDENTITY_CONFLICT",
    "LEDGER_INTEGRITY_TAMPER",
    "LIMIT_EXCEEDED",
    "INTERNAL_VALIDATION_FAILED",
)
_PUBLIC_ERROR_SET = frozenset(WALLET_PUBLIC_ERROR_CODES)

# Total mapping from internal failure category to closed public code.
WALLET_INTERNAL_TO_PUBLIC_ERROR = {
    "SCHEMA_VERSION_UNSUPPORTED": "SCHEMA_UNSUPPORTED",
    "FIELD_MISSING": "FIELD_VALUE_INVALID",
    "FIELD_TYPE": "FIELD_TYPE_INVALID",
    "FIELD_VALUE": "FIELD_VALUE_INVALID",
    "ADDRESS": "ADDRESS_INVALID",
    "DECIMAL": "DECIMAL_INVALID",
    "IDENTITY": "IDENTITY_DERIVATION_MISMATCH",
    "REFERENCE_MISSING": "REFERENCE_INVALID",
    "REFERENCE_WRONG_TYPE": "REFERENCE_TYPE_INVALID",
    "REFERENCE_CYCLE": "REFERENCE_CYCLE",
    "PIT_INADMISSIBLE": "PIT_NOT_ADMISSIBLE",
    "PROVENANCE": "PROVENANCE_INCOMPLETE",
    "DQ": "DQ_STATE_INVALID",
    "CURSOR": "CURSOR_INVALID",
    "GAP": "CURSOR_GAP",
    "DISAGREEMENT": "SOURCE_DISAGREEMENT",
    "SOURCE_UNAVAILABLE": "SOURCE_UNAVAILABLE",
    "RESPONSE": "SOURCE_RESPONSE_INVALID",
    "GUARD": "RATE_LIMIT_GUARD_DENIED",
    "NETWORK_OFF": "NETWORK_DISABLED",
    "HOST": "NETWORK_HOST_FORBIDDEN",
    "SCHEME": "NETWORK_SCHEME_FORBIDDEN",
    "RECONCILIATION": "RECONCILIATION_INVALID",
    "LEDGER_IDENTITY": "LEDGER_IDENTITY_CONFLICT",
    "LEDGER_TAMPER": "LEDGER_INTEGRITY_TAMPER",
    "LIMIT": "LIMIT_EXCEEDED",
    "UNEXPECTED": "INTERNAL_VALIDATION_FAILED",
}

# Provenance-core ValueError codes translated into the internal vocabulary so the
# public surface stays closed even when shared helpers raise.
_PROVENANCE_CODE_TO_INTERNAL = {
    "TIMESTAMP_FORMAT_INVALID": "FIELD_VALUE",
    "TIMESTAMP_NOT_UTC": "FIELD_VALUE",
    "TIMESTAMP_TYPE_INVALID": "FIELD_TYPE",
    "PIT_FIELD_UNKNOWN": "FIELD_VALUE",
    "DQ_FLAG_UNKNOWN": "DQ",
    "DQ_OK_EXCLUSIVITY_VIOLATION": "DQ",
    "DQ_EMPTY": "DQ",
    "REPLAY_FIDELITY_UNSUPPORTED": "FIELD_VALUE",
    "REPLAY_FIDELITY_EXACT_WITHOUT_RAW": "PROVENANCE",
    "FIELD_TYPE_INVALID": "FIELD_TYPE",
    "FIELD_VALUE_INVALID": "FIELD_VALUE",
    "SHA256_FORMAT_INVALID": "FIELD_VALUE",
    "BYTE_LENGTH_INVALID": "FIELD_VALUE",
    "MANIFEST_CIRCULAR_REFERENCE": "REFERENCE_CYCLE",
    "IDENTITY_DERIVATION_MISMATCH": "IDENTITY",
}


class WalletContractError(Exception):
    """Public wallet error. Its string is ONLY a closed public code; it never
    echoes arbitrary exception text, raw response bodies, URLs, or paths."""

    def __init__(self, internal_code: str) -> None:
        self.internal_code = internal_code
        self.public_code = map_internal_failure_to_public(internal_code)
        super().__init__(self.public_code)


def map_internal_failure_to_public(internal_code: object) -> str:
    """Total map: any unrecognized internal code collapses to the closed fallback."""

    if isinstance(internal_code, str):
        return WALLET_INTERNAL_TO_PUBLIC_ERROR.get(
            internal_code, "INTERNAL_VALIDATION_FAILED"
        )
    return "INTERNAL_VALIDATION_FAILED"


def _err(internal_code: str) -> WalletContractError:
    return WalletContractError(internal_code)


# ---------------------------------------------------------------------------
# Wallet canonical JSON. Same byte output as the shared PIT canonicalizer for
# small inputs (so record identities are unchanged), but with generous bounds so
# a terminal receipt referencing up to the 3000-row hard bound of observation
# ids still serializes and hashes deterministically. Binary floats are rejected
# so they never participate in content-addressed identity.
# ---------------------------------------------------------------------------
_WALLET_JSON_MAX_DEPTH = 40
_WALLET_JSON_MAX_NODES = 500_000
_WALLET_JSON_MAX_ITEMS = 200_000
_WALLET_JSON_MAX_KEYS = 4_096
_WALLET_JSON_MAX_STRING = 16_384
_WALLET_JSON_MAX_BYTES = 8_388_608


def wallet_canonical_json_bytes(value: object) -> bytes:
    node_count = 0

    def normalize(current: object, depth: int) -> object:
        nonlocal node_count
        node_count += 1
        if node_count > _WALLET_JSON_MAX_NODES or depth > _WALLET_JSON_MAX_DEPTH:
            raise _err("LIMIT")
        if current is None or isinstance(current, bool):
            return current
        if isinstance(current, int):
            return current
        if isinstance(current, float):
            raise _err("DECIMAL")
        if isinstance(current, str):
            if len(current) > _WALLET_JSON_MAX_STRING:
                raise _err("LIMIT")
            return current
        if isinstance(current, Mapping):
            if len(current) > _WALLET_JSON_MAX_KEYS:
                raise _err("LIMIT")
            out: dict[str, object] = {}
            for key in sorted(current.keys()):
                if not isinstance(key, str):
                    raise _err("FIELD_TYPE")
                out[key] = normalize(current[key], depth + 1)
            return out
        if isinstance(current, (list, tuple)):
            if len(current) > _WALLET_JSON_MAX_ITEMS:
                raise _err("LIMIT")
            return [normalize(item, depth + 1) for item in current]
        raise _err("FIELD_TYPE")

    normalized = normalize(value, 0)
    encoded = json.dumps(
        normalized, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")
    if len(encoded) > _WALLET_JSON_MAX_BYTES:
        raise _err("LIMIT")
    return encoded


def _wrap_provenance(func, *args, **kwargs):
    """Call a shared provenance helper, translating its ValueError to a closed
    public wallet error."""

    try:
        return func(*args, **kwargs)
    except ValueError as exc:
        code = str(exc)
        internal = _PROVENANCE_CODE_TO_INTERNAL.get(code, "UNEXPECTED")
        raise WalletContractError(internal) from None


# ===========================================================================
# 10.1 Address / account role / wallet type enums.
# ===========================================================================
GENERIC_ACCOUNT_ROLES = (
    "ACCOUNT_WALLET",
    "SIGNER",
    "PROTOCOL_CONTRACT",
    "OTHER_CONTRACT",
    "UNKNOWN",
)
POLYMARKET_WALLET_TYPES = (
    "EOA",
    "POLY_PROXY",
    "GNOSIS_SAFE",
    "DEPOSIT_WALLET",
    "UNKNOWN",
)
EVIDENCE_LINK_CLASSES = (
    "PROTOCOL_DECLARED",
    "ONCHAIN_CONFIRMED",
    "SOURCE_REPORTED",
    "STATISTICAL_SIMILARITY",
    "UNKNOWN",
)
_GENERIC_ROLE_SET = frozenset(GENERIC_ACCOUNT_ROLES)
_WALLET_TYPE_SET = frozenset(POLYMARKET_WALLET_TYPES)
_EVIDENCE_LINK_SET = frozenset(EVIDENCE_LINK_CLASSES)

# ===========================================================================
# 10.2 Canonical event vocabulary and source-type maps.
# ===========================================================================
CANONICAL_EVENT_TYPES = (
    "TRADE_FILL",
    "TRANSFER_IN",
    "TRANSFER_OUT",
    "SPLIT",
    "MERGE",
    "CONVERSION",
    "REDEEM_SETTLEMENT",
    "DEPOSIT",
    "WITHDRAWAL",
    "REWARD",
    "MAKER_REBATE",
    "TAKER_REBATE",
    "REFERRAL_REWARD",
    "YIELD",
    "MIGRATION",
    "TIP",
    "COMBO_COMPRESS",
    "COMBO_WRAP",
    "COMBO_UNWRAP",
    "FEE",
    "UNKNOWN_PUBLIC_ACTIVITY",
)
_CANONICAL_EVENT_SET = frozenset(CANONICAL_EVENT_TYPES)

STANDARD_ACTIVITY_TYPE_MAP = {
    "TRADE": "TRADE_FILL",
    "SPLIT": "SPLIT",
    "MERGE": "MERGE",
    "REDEEM": "REDEEM_SETTLEMENT",
    "REWARD": "REWARD",
    "CONVERSION": "CONVERSION",
    "MIGRATION": "MIGRATION",
    "DEPOSIT": "DEPOSIT",
    "WITHDRAWAL": "WITHDRAWAL",
    "YIELD": "YIELD",
    "MAKER_REBATE": "MAKER_REBATE",
    "TAKER_REBATE": "TAKER_REBATE",
    "REFERRAL_REWARD": "REFERRAL_REWARD",
    "TIP": "TIP",
}
COMBO_ACTIVITY_TYPE_MAP = {
    "SPLIT": "SPLIT",
    "MERGE": "MERGE",
    "CONVERT": "CONVERSION",
    "COMPRESS": "COMBO_COMPRESS",
    "WRAP": "COMBO_WRAP",
    "UNWRAP": "COMBO_UNWRAP",
    "REDEEM": "REDEEM_SETTLEMENT",
}

# ===========================================================================
# 10.5 / 10.6 Cost basis, identity strength, combo state.
# ===========================================================================
COST_BASIS_STATES = ("KNOWN", "PARTIAL", "UNKNOWN", "NOT_APPLICABLE")
_COST_BASIS_SET = frozenset(COST_BASIS_STATES)

IDENTITY_STRENGTHS = (
    "CHAIN_NATIVE_STRONG",
    "API_NATIVE_STRONG",
    "SOURCE_CONTENT_DERIVED",
    "WEAK_PARTIAL",
)
_IDENTITY_STRENGTH_SET = frozenset(IDENTITY_STRENGTHS)

TRADE_COMBO_STATES = ("FALSE", "TRUE", "UNKNOWN")
_TRADE_COMBO_SET = frozenset(TRADE_COMBO_STATES)

SIDE_VALUES = ("BUY", "SELL", "IN", "OUT")
_SIDE_SET = frozenset(SIDE_VALUES)

# ===========================================================================
# 10.3 External identifier canonicalization contexts.
# ===========================================================================
IDENTIFIER_CONTEXTS = (
    "TRANSACTION_HASH",
    "BLOCK_HASH",
    "DATA_API_RESPONSE_CONDITION_ID",
    "PROTOCOL_STANDARD_CONDITION_ID",
    "MARKET_SELECTOR_CONDITION_ID",
    "COMBO_CONDITION_ID",
    "GAMMA_MARKET_ID",
    "GAMMA_EVENT_ID",
    "CLOB_TOKEN_ID",
    "COMBO_POSITION_ID",
    "SOURCE_NATIVE_EVENT_ID",
    "EVM_ADDRESS",
)
_IDENTIFIER_CONTEXT_SET = frozenset(IDENTIFIER_CONTEXTS)

_ADDRESS_RE = re.compile(r"^0x[0-9a-fA-F]{40}$")
_BYTES32_RE = re.compile(r"^0x[0-9a-fA-F]{64}$")
_HEX_BODY_RE = re.compile(r"^0x[0-9a-fA-F]+$")
_UNSIGNED_INT_RE = re.compile(r"^[0-9]+$")

# Record ledger record-kind names (used for identity prefixes and ledger ranks).
RECORD_KIND_RAW_EVIDENCE_REFERENCE = "RAW_EVIDENCE_REFERENCE"
RECORD_KIND_WALLET_ACCOUNT_IDENTITY_EVIDENCE = "WALLET_ACCOUNT_IDENTITY_EVIDENCE"
RECORD_KIND_WALLET_EVIDENCE_EVENT = "WALLET_EVIDENCE_EVENT"
RECORD_KIND_WALLET_FEED_PAGE_EVIDENCE = "WALLET_FEED_PAGE_EVIDENCE"
RECORD_KIND_WALLET_EVENT_OBSERVATION = "WALLET_EVENT_OBSERVATION"
RECORD_KIND_WALLET_INGEST_RUN_RECEIPT = "WALLET_INGEST_RUN_RECEIPT"
RECORD_KIND_RESEARCH_PROVENANCE_MANIFEST = "RESEARCH_PROVENANCE_MANIFEST"
RECORD_KIND_WALLET_PROVENANCE_EXTENSION = "WALLET_PROVENANCE_EXTENSION"
RECORD_KIND_WALLET_RECONCILIATION_LINK = "WALLET_RECONCILIATION_LINK"

INGEST_RUN_KEY_PREFIX = "walletingestrun:sha256:"
_ID_PREFIXES = {
    RECORD_KIND_WALLET_ACCOUNT_IDENTITY_EVIDENCE: "walletacct:sha256:",
    RECORD_KIND_WALLET_EVIDENCE_EVENT: "walletevent:sha256:",
    RECORD_KIND_WALLET_FEED_PAGE_EVIDENCE: "walletpage:sha256:",
    RECORD_KIND_WALLET_EVENT_OBSERVATION: "walletobs:sha256:",
    RECORD_KIND_WALLET_INGEST_RUN_RECEIPT: "walletreceipt:sha256:",
    RECORD_KIND_WALLET_PROVENANCE_EXTENSION: "walletprovext:sha256:",
    RECORD_KIND_WALLET_RECONCILIATION_LINK: "walletrecon:sha256:",
}


# ---------------------------------------------------------------------------
# Address canonicalization (10.1).
# ---------------------------------------------------------------------------
def canonicalize_evm_address(value: object) -> str:
    """Return a canonical lowercase ``0x`` + 40-hex address or raise ADDRESS_INVALID.

    Input must be ASCII. Surrounding ASCII whitespace is stripped. Case is not
    checksum-validated; any syntactically valid mixed-case address lowercases.
    Unicode/full-width/lookalike characters reject. EIP-55 is not implemented.
    """

    if not isinstance(value, str):
        raise _err("ADDRESS")
    try:
        value.encode("ascii")
    except UnicodeEncodeError:
        raise _err("ADDRESS") from None
    stripped = value.strip(" \t\r\n")
    if not _ADDRESS_RE.match(stripped):
        raise _err("ADDRESS")
    return stripped.lower()


def is_canonical_evm_address(value: object) -> bool:
    if not isinstance(value, str):
        return False
    return bool(_ADDRESS_RE.match(value)) and value == value.lower()


# ---------------------------------------------------------------------------
# Context-typed external identifier canonicalization (10.3).
# ---------------------------------------------------------------------------
def canonicalize_identifier(context: str, value: object) -> str:
    """Canonicalize an external identifier under an explicit context/namespace.

    No generic ``str(value)`` identity path exists; each context uses its own
    verified grammar. Contexts never silently reuse another context's helper.
    """

    if context not in _IDENTIFIER_CONTEXT_SET:
        raise _err("FIELD_VALUE")

    if context in ("TRANSACTION_HASH", "BLOCK_HASH"):
        return _canonicalize_bytes32(value)
    if context == "EVM_ADDRESS":
        return canonicalize_evm_address(value)
    if context == "DATA_API_RESPONSE_CONDITION_ID":
        return _canonicalize_data_api_condition_id(value)
    if context == "PROTOCOL_STANDARD_CONDITION_ID":
        return _canonicalize_protocol_standard_condition_id(value)
    if context == "MARKET_SELECTOR_CONDITION_ID":
        return _canonicalize_market_selector_condition_id(value)
    if context == "COMBO_CONDITION_ID":
        return _canonicalize_combo_condition_id(value)
    if context in ("GAMMA_MARKET_ID", "GAMMA_EVENT_ID", "CLOB_TOKEN_ID"):
        return _canonicalize_unsigned_integer(value)
    # COMBO_POSITION_ID and SOURCE_NATIVE_EVENT_ID: source-native opaque ids.
    return _canonicalize_opaque(value)


def _ascii_hex_string(value: object) -> str:
    if not isinstance(value, str):
        raise _err("FIELD_TYPE")
    try:
        value.encode("ascii")
    except UnicodeEncodeError:
        raise _err("FIELD_VALUE") from None
    return value


def _canonicalize_bytes32(value: object) -> str:
    text = _ascii_hex_string(value)
    if not _BYTES32_RE.match(text):
        raise _err("FIELD_VALUE")
    return text.lower()


def _canonicalize_data_api_condition_id(value: object) -> str:
    # Current inspected SDK response validator: string, lowercase 0x prefix,
    # non-empty hex remainder, no fixed byte-length rule.
    text = _ascii_hex_string(value)
    if not text.startswith("0x"):
        raise _err("FIELD_VALUE")
    if not _HEX_BODY_RE.match(text):
        raise _err("FIELD_VALUE")
    return text.lower()


def _canonicalize_protocol_standard_condition_id(value: object) -> str:
    # Verified to_condition_id grammar: 31-byte form total length 64 incl 0x, or
    # 32-byte form total length 66 incl 0x. Lowercase for identity; no padding.
    text = _ascii_hex_string(value)
    if not _HEX_BODY_RE.match(text):
        raise _err("FIELD_VALUE")
    if len(text) not in (64, 66):
        raise _err("FIELD_VALUE")
    return text.lower()


def _canonicalize_market_selector_condition_id(value: object) -> str:
    # Verified to_market_condition_id: 32-byte condition (len 66) stays; 31-byte
    # market form (len 64) starting 0x01 or 0x02 lowercases and appends "00".
    text = _ascii_hex_string(value)
    if not _HEX_BODY_RE.match(text):
        raise _err("FIELD_VALUE")
    lowered = text.lower()
    if len(lowered) == 66:
        return lowered
    if len(lowered) == 64 and lowered[:4] in ("0x01", "0x02"):
        return lowered + "00"
    raise _err("FIELD_VALUE")


def _canonicalize_combo_condition_id(value: object) -> str:
    # Verified to_combo_condition_id: canonical len 64 incl 0x starts 0x03; the
    # accepted 32-byte source form (len 66) starts 0x03 and ends 00 or 01, and
    # canonicalizes by lowercasing and removing the final byte (two hex chars).
    text = _ascii_hex_string(value)
    if not _HEX_BODY_RE.match(text):
        raise _err("FIELD_VALUE")
    lowered = text.lower()
    if len(lowered) == 64 and lowered.startswith("0x03"):
        return lowered
    if len(lowered) == 66 and lowered.startswith("0x03") and lowered[-2:] in ("00", "01"):
        return lowered[:-2]
    raise _err("FIELD_VALUE")


def _canonicalize_unsigned_integer(value: object) -> str:
    # 10.3.G: non-negative int (excluding bool) or ASCII decimal string; canonical
    # unsigned base-10; no +, whitespace, exponent, float, or leading zeros.
    if isinstance(value, bool):
        raise _err("FIELD_TYPE")
    if isinstance(value, int):
        if value < 0:
            raise _err("FIELD_VALUE")
        return str(value)
    if isinstance(value, str):
        if not _UNSIGNED_INT_RE.match(value):
            raise _err("FIELD_VALUE")
        return str(int(value))
    raise _err("FIELD_TYPE")


def _canonicalize_opaque(value: object) -> str:
    # 10.3.I: preserve exact source string; 1..256 scalar values; UTF-8 <= 1024
    # bytes; reject NUL, C0/C1 controls, unpaired surrogates, and edge whitespace.
    if not isinstance(value, str):
        raise _err("FIELD_TYPE")
    if len(value) < 1 or len(value) > 256:
        raise _err("FIELD_VALUE")
    if value != value.strip():
        raise _err("FIELD_VALUE")
    try:
        encoded = value.encode("utf-8")
    except UnicodeEncodeError:
        raise _err("FIELD_VALUE") from None
    if len(encoded) > 1024:
        raise _err("FIELD_VALUE")
    for ch in value:
        code = ord(ch)
        if code == 0 or code < 0x20 or 0x7F <= code <= 0x9F:
            raise _err("FIELD_VALUE")
        if unicodedata.category(ch) == "Cs":
            raise _err("FIELD_VALUE")
    return value


# ---------------------------------------------------------------------------
# Decimal canonicalization (10.4).
# ---------------------------------------------------------------------------
_DECIMAL_STR_RE = re.compile(r"^-?[0-9]+(?:\.[0-9]+)?$")


def canonicalize_decimal(value: object) -> str:
    """Return an exact base-10 canonical decimal string or raise DECIMAL.

    Accepts Decimal, int, or decimal string. Rejects bool, float, NaN, +/-Inf,
    and malformed strings. Output has no exponent, no leading +, no unnecessary
    trailing zeros, no trailing point; -0/0.00 canonicalize to ``0``. Binary
    floats never participate in content-addressed identity.
    """

    if isinstance(value, bool):
        raise _err("DECIMAL")
    if isinstance(value, float):
        raise _err("DECIMAL")
    if isinstance(value, int):
        dec = Decimal(value)
    elif isinstance(value, Decimal):
        if not value.is_finite():
            raise _err("DECIMAL")
        dec = value
    elif isinstance(value, str):
        if not _DECIMAL_STR_RE.match(value):
            raise _err("DECIMAL")
        dec = Decimal(value)
    else:
        raise _err("DECIMAL")
    if not dec.is_finite():
        raise _err("DECIMAL")
    text = format(dec, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    if text in ("", "-", "-0"):
        text = "0"
    return text


def canonicalize_price(value: object) -> str:
    text = canonicalize_decimal(value)
    dec = Decimal(text)
    if dec < 0 or dec > 1:
        raise _err("FIELD_VALUE")
    return text


def canonicalize_quantity(value: object) -> str:
    text = canonicalize_decimal(value)
    if Decimal(text) <= 0:
        raise _err("FIELD_VALUE")
    return text


def canonicalize_amount(value: object) -> str:
    text = canonicalize_decimal(value)
    if Decimal(text) < 0:
        raise _err("FIELD_VALUE")
    return text


# ---------------------------------------------------------------------------
# Event-type mapping (10.2).
# ---------------------------------------------------------------------------
def map_standard_activity_type(source_type: object) -> str:
    """Map a standard /v2/activity source type to a canonical event type.

    A recognized current type maps to its frozen canonical event. A genuinely
    unrecognized type maps to UNKNOWN_PUBLIC_ACTIVITY (never fabricated).
    """

    if not isinstance(source_type, str):
        raise _err("FIELD_TYPE")
    return STANDARD_ACTIVITY_TYPE_MAP.get(source_type, "UNKNOWN_PUBLIC_ACTIVITY")


def map_combo_activity_type(source_type: object) -> str:
    if not isinstance(source_type, str):
        raise _err("FIELD_TYPE")
    return COMBO_ACTIVITY_TYPE_MAP.get(source_type, "UNKNOWN_PUBLIC_ACTIVITY")


def build_economic_object_key(
    components: Sequence[Sequence[str]],
) -> tuple[tuple[str, str, str], ...]:
    """Deterministic namespaced economic-object key.

    Each component is ``(namespace, context, canonical_value)``. The result is a
    sorted tuple of tuples so that identical comparable identifiers converge and
    genuinely different identifiers do not silently merge.
    """

    out: list[tuple[str, str, str]] = []
    for comp in components:
        if (
            not isinstance(comp, Sequence)
            or isinstance(comp, str)
            or len(comp) != 3
            or not all(isinstance(part, str) for part in comp)
        ):
            raise _err("FIELD_TYPE")
        out.append((comp[0], comp[1], comp[2]))
    return tuple(sorted(out))


# ===========================================================================
# Records.
# ===========================================================================
def _validate_enum(value: object, allowed: frozenset[str], code: str = "FIELD_VALUE") -> str:
    if not isinstance(value, str) or value not in allowed:
        raise _err(code)
    return value


def _identity(kind: str, preimage: object) -> str:
    return _ID_PREFIXES[kind] + sha256_hex(wallet_canonical_json_bytes(preimage))


# --- A. WalletAccountIdentityEvidence -------------------------------------
@dataclass(frozen=True)
class WalletAccountIdentityEvidence:
    wallet_account_identity_evidence_id: str
    canonical_wallet: str
    generic_account_role: str
    polymarket_wallet_type: str
    evidence_link_class: str
    related_account: str | None
    source_reference: str
    effective_start: str | None
    effective_end: str | None

    def logical_preimage(self) -> dict[str, object]:
        return {
            "canonical_wallet": self.canonical_wallet,
            "generic_account_role": self.generic_account_role,
            "polymarket_wallet_type": self.polymarket_wallet_type,
            "evidence_link_class": self.evidence_link_class,
            "related_account": self.related_account,
            "source_reference": self.source_reference,
            "effective_start": self.effective_start,
            "effective_end": self.effective_end,
        }


def build_wallet_account_identity_evidence(
    *,
    canonical_wallet: str,
    generic_account_role: str,
    polymarket_wallet_type: str,
    evidence_link_class: str,
    source_reference: str,
    related_account: str | None = None,
    effective_start: str | None = None,
    effective_end: str | None = None,
) -> WalletAccountIdentityEvidence:
    wallet = canonicalize_evm_address(canonical_wallet)
    role = _validate_enum(generic_account_role, _GENERIC_ROLE_SET)
    wtype = _validate_enum(polymarket_wallet_type, _WALLET_TYPE_SET)
    link = _validate_enum(evidence_link_class, _EVIDENCE_LINK_SET)
    if not isinstance(source_reference, str) or not source_reference:
        raise _err("FIELD_VALUE")
    related = canonicalize_evm_address(related_account) if related_account is not None else None
    start = _wrap_provenance(canonicalize_utc_timestamp, effective_start) if effective_start is not None else None
    end = _wrap_provenance(canonicalize_utc_timestamp, effective_end) if effective_end is not None else None
    draft = WalletAccountIdentityEvidence(
        wallet_account_identity_evidence_id="",
        canonical_wallet=wallet,
        generic_account_role=role,
        polymarket_wallet_type=wtype,
        evidence_link_class=link,
        related_account=related,
        source_reference=source_reference,
        effective_start=start,
        effective_end=end,
    )
    return replace(
        draft,
        wallet_account_identity_evidence_id=_identity(
            RECORD_KIND_WALLET_ACCOUNT_IDENTITY_EVIDENCE, draft.logical_preimage()
        ),
    )


# --- B. WalletEvidenceEvent -----------------------------------------------
@dataclass(frozen=True)
class WalletEvidenceEvent:
    wallet_event_id: str
    identity_schema_version: str
    identity_strength: str
    canonical_event_type: str
    canonical_wallet: str
    combo_state: str | None
    source_system_family: str | None
    chain_id: int | None
    condition_context: str | None
    condition_value: str | None
    token_context: str | None
    token_value: str | None
    side: str | None
    price: str | None
    size: str | None
    notional: str | None
    payout: str | None
    event_time: str | None
    transaction_hash: str | None
    log_index: int | None
    block_hash: str | None
    source_contract_address: str | None
    native_event_id: str | None
    economic_object_key: tuple[tuple[str, str, str], ...]
    cost_basis_state: str
    identity_ambiguous: bool

    def identity_preimage(self) -> dict[str, object]:
        # Pagination / acquisition / provenance fields are NEVER part of the
        # economic event identity (10.6). The preimage is strength-specific.
        if self.identity_strength == "CHAIN_NATIVE_STRONG":
            return {
                "identity_schema_version": self.identity_schema_version,
                "identity_strength": self.identity_strength,
                "chain_id": self.chain_id,
                "canonical_event_type": self.canonical_event_type,
                "canonical_wallet": self.canonical_wallet,
                "transaction_hash": self.transaction_hash,
                "log_index": self.log_index,
                "source_contract_address": self.source_contract_address,
            }
        if self.identity_strength == "API_NATIVE_STRONG":
            return {
                "identity_schema_version": self.identity_schema_version,
                "identity_strength": self.identity_strength,
                "source_system_family": self.source_system_family,
                "native_event_id": self.native_event_id,
                "canonical_wallet": self.canonical_wallet,
                "canonical_event_type": self.canonical_event_type,
                "combo_state": self.combo_state,
            }
        # SOURCE_CONTENT_DERIVED and WEAK_PARTIAL share a content preimage; weak
        # rows additionally carry identity_ambiguous=True and never claim strong
        # identity strength.
        return {
            "identity_schema_version": self.identity_schema_version,
            "identity_strength": self.identity_strength,
            "source_system_family": self.source_system_family,
            "canonical_wallet": self.canonical_wallet,
            "canonical_event_type": self.canonical_event_type,
            "combo_state": self.combo_state,
            "condition_context": self.condition_context,
            "condition_value": self.condition_value,
            "token_context": self.token_context,
            "token_value": self.token_value,
            "side": self.side,
            "price": self.price,
            "size": self.size,
            "notional": self.notional,
            "payout": self.payout,
            "event_time": self.event_time,
            "transaction_hash": self.transaction_hash,
            "native_event_id": self.native_event_id,
            "economic_object_key": [list(part) for part in self.economic_object_key],
        }


def build_wallet_evidence_event(
    *,
    identity_strength: str,
    canonical_event_type: str,
    canonical_wallet: str,
    combo_state: str | None = None,
    source_system_family: str | None = None,
    chain_id: int | None = None,
    condition_context: str | None = None,
    condition_value: str | None = None,
    token_context: str | None = None,
    token_value: str | None = None,
    side: str | None = None,
    price: str | None = None,
    size: str | None = None,
    notional: str | None = None,
    payout: str | None = None,
    event_time: str | None = None,
    transaction_hash: str | None = None,
    log_index: int | None = None,
    block_hash: str | None = None,
    source_contract_address: str | None = None,
    native_event_id: str | None = None,
    economic_object_key: Sequence[Sequence[str]] = (),
    cost_basis_state: str = "NOT_APPLICABLE",
    identity_ambiguous: bool = False,
) -> WalletEvidenceEvent:
    """Construct a canonical, content-addressed :class:`WalletEvidenceEvent`.

    The id is reusable across pages, endpoints, and runs; it never carries an
    ``ingest_run_key`` and never changes because another run re-observes the same
    event. Combo state UNKNOWN is a first-class value and is never coerced to
    FALSE.
    """

    strength = _validate_enum(identity_strength, _IDENTITY_STRENGTH_SET)
    event_type = _validate_enum(canonical_event_type, _CANONICAL_EVENT_SET)
    wallet = canonicalize_evm_address(canonical_wallet)
    cost_basis = _validate_enum(cost_basis_state, _COST_BASIS_SET)
    if combo_state is not None:
        combo_state = _validate_enum(combo_state, _TRADE_COMBO_SET)
    if side is not None:
        side = _validate_enum(side, _SIDE_SET)
        if event_type == "TRADE_FILL" and side not in ("BUY", "SELL"):
            raise _err("FIELD_VALUE")
        if event_type == "TIP" and side not in ("IN", "OUT"):
            raise _err("FIELD_VALUE")
    if chain_id is not None and (not isinstance(chain_id, int) or isinstance(chain_id, bool)):
        raise _err("FIELD_TYPE")
    if log_index is not None and (not isinstance(log_index, int) or isinstance(log_index, bool) or log_index < 0):
        raise _err("FIELD_VALUE")
    if transaction_hash is not None:
        transaction_hash = canonicalize_identifier("TRANSACTION_HASH", transaction_hash)
    if block_hash is not None:
        block_hash = canonicalize_identifier("BLOCK_HASH", block_hash)
    if source_contract_address is not None:
        source_contract_address = canonicalize_evm_address(source_contract_address)
    if event_time is not None:
        event_time = _wrap_provenance(canonicalize_utc_timestamp, event_time)
    if price is not None:
        price = canonicalize_price(price)
    if size is not None:
        size = canonicalize_quantity(size)
    if notional is not None:
        notional = canonicalize_amount(notional)
    if payout is not None:
        payout = canonicalize_amount(payout)
    key = build_economic_object_key(economic_object_key)

    # Strength-specific required-field gates (10.6).
    if strength == "CHAIN_NATIVE_STRONG":
        if transaction_hash is None or log_index is None or chain_id is None:
            raise _err("IDENTITY")
    elif strength == "API_NATIVE_STRONG":
        if not native_event_id or source_system_family is None:
            raise _err("IDENTITY")
    elif strength == "SOURCE_CONTENT_DERIVED":
        if event_type == "TRADE_FILL" and combo_state is None:
            raise _err("IDENTITY")

    draft = WalletEvidenceEvent(
        wallet_event_id="",
        identity_schema_version=IDENTITY_SCHEMA_VERSION,
        identity_strength=strength,
        canonical_event_type=event_type,
        canonical_wallet=wallet,
        combo_state=combo_state,
        source_system_family=source_system_family,
        chain_id=chain_id,
        condition_context=condition_context,
        condition_value=condition_value,
        token_context=token_context,
        token_value=token_value,
        side=side,
        price=price,
        size=size,
        notional=notional,
        payout=payout,
        event_time=event_time,
        transaction_hash=transaction_hash,
        log_index=log_index,
        block_hash=block_hash,
        source_contract_address=source_contract_address,
        native_event_id=native_event_id,
        economic_object_key=key,
        cost_basis_state=cost_basis,
        identity_ambiguous=bool(identity_ambiguous),
    )
    return replace(
        draft,
        wallet_event_id=_identity(
            RECORD_KIND_WALLET_EVIDENCE_EVENT, draft.identity_preimage()
        ),
    )


# --- D. WalletFeedPageEvidence --------------------------------------------
WALLET_FEED_KEYS = ("TRADES", "STANDARD_ACTIVITY", "COMBO_ACTIVITY")
_WALLET_FEED_KEY_SET = frozenset(WALLET_FEED_KEYS)


@dataclass(frozen=True)
class WalletFeedPageEvidence:
    wallet_feed_page_evidence_id: str
    raw_evidence_reference_id: str
    ingest_run_key: str
    feed_key: str
    canonical_request_identity: tuple[tuple[str, str], ...]
    requested_page_size: int
    incoming_cursor: str | None
    outgoing_cursor: str | None
    has_more: bool
    local_first_seen_time: str
    ingestion_time: str
    freshness_ref: str | None
    api_source_parser_version: str
    dq_flags: tuple[str, ...]
    replay_fidelity: str
    source_row_count: int
    normalized_event_count: int
    observation_count: int

    def logical_preimage(self) -> dict[str, object]:
        return {
            "raw_evidence_reference_id": self.raw_evidence_reference_id,
            "ingest_run_key": self.ingest_run_key,
            "feed_key": self.feed_key,
            "canonical_request_identity": [list(p) for p in self.canonical_request_identity],
            "requested_page_size": self.requested_page_size,
            "incoming_cursor": self.incoming_cursor,
            "outgoing_cursor": self.outgoing_cursor,
            "has_more": self.has_more,
            "local_first_seen_time": self.local_first_seen_time,
            "ingestion_time": self.ingestion_time,
            "freshness_ref": self.freshness_ref,
            "api_source_parser_version": self.api_source_parser_version,
            "dq_flags": list(self.dq_flags),
            "replay_fidelity": self.replay_fidelity,
            "source_row_count": self.source_row_count,
            "normalized_event_count": self.normalized_event_count,
            "observation_count": self.observation_count,
        }


def build_wallet_feed_page_evidence(
    *,
    raw_evidence_reference_id: str,
    ingest_run_key: str,
    feed_key: str,
    canonical_request_identity: object,
    requested_page_size: int,
    has_more: bool,
    local_first_seen_time: str,
    ingestion_time: str,
    api_source_parser_version: str,
    dq_flags: Sequence[str],
    replay_fidelity: str,
    source_row_count: int,
    normalized_event_count: int,
    observation_count: int,
    incoming_cursor: str | None = None,
    outgoing_cursor: str | None = None,
    freshness_ref: str | None = None,
) -> WalletFeedPageEvidence:
    if not isinstance(raw_evidence_reference_id, str) or not raw_evidence_reference_id:
        raise _err("REFERENCE_MISSING")
    _validate_ingest_run_key(ingest_run_key)
    feed = _validate_enum(feed_key, _WALLET_FEED_KEY_SET)
    request_identity = _canonical_pairs(canonical_request_identity)
    for name, value in (
        ("requested_page_size", requested_page_size),
        ("source_row_count", source_row_count),
        ("normalized_event_count", normalized_event_count),
        ("observation_count", observation_count),
    ):
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise _err("FIELD_VALUE")
    if not isinstance(has_more, bool):
        raise _err("FIELD_TYPE")
    first_seen = _wrap_provenance(canonicalize_utc_timestamp, local_first_seen_time)
    ingestion = _wrap_provenance(canonicalize_utc_timestamp, ingestion_time)
    if not isinstance(api_source_parser_version, str) or not api_source_parser_version:
        raise _err("FIELD_VALUE")
    for cursor in (incoming_cursor, outgoing_cursor):
        _validate_optional_cursor(cursor)
    if freshness_ref is not None and not isinstance(freshness_ref, str):
        raise _err("FIELD_TYPE")
    flags = _wrap_provenance(canonicalize_dq_flags, dq_flags)
    fidelity = _wrap_provenance(validate_replay_fidelity, replay_fidelity)
    draft = WalletFeedPageEvidence(
        wallet_feed_page_evidence_id="",
        raw_evidence_reference_id=raw_evidence_reference_id,
        ingest_run_key=ingest_run_key,
        feed_key=feed,
        canonical_request_identity=request_identity,
        requested_page_size=requested_page_size,
        incoming_cursor=incoming_cursor,
        outgoing_cursor=outgoing_cursor,
        has_more=has_more,
        local_first_seen_time=first_seen,
        ingestion_time=ingestion,
        freshness_ref=freshness_ref,
        api_source_parser_version=api_source_parser_version,
        dq_flags=flags,
        replay_fidelity=fidelity,
        source_row_count=source_row_count,
        normalized_event_count=normalized_event_count,
        observation_count=observation_count,
    )
    return replace(
        draft,
        wallet_feed_page_evidence_id=_identity(
            RECORD_KIND_WALLET_FEED_PAGE_EVIDENCE, draft.logical_preimage()
        ),
    )


# --- C. WalletEventObservation --------------------------------------------
@dataclass(frozen=True)
class WalletEventObservation:
    wallet_event_observation_id: str
    wallet_event_id: str
    wallet_feed_page_evidence_id: str
    ingest_run_key: str
    raw_evidence_reference_id: str | None
    source_system: str
    endpoint: str
    source_activity_type: str
    pit: PitTimestamps
    dq_flags: tuple[str, ...]
    replay_fidelity: str

    def logical_preimage(self) -> dict[str, object]:
        return {
            "wallet_event_id": self.wallet_event_id,
            "wallet_feed_page_evidence_id": self.wallet_feed_page_evidence_id,
            "ingest_run_key": self.ingest_run_key,
            "raw_evidence_reference_id": self.raw_evidence_reference_id,
            "source_system": self.source_system,
            "endpoint": self.endpoint,
            "source_activity_type": self.source_activity_type,
            "pit": self.pit.to_dict(),
            "dq_flags": list(self.dq_flags),
            "replay_fidelity": self.replay_fidelity,
        }


def build_wallet_event_observation(
    *,
    wallet_event_id: str,
    wallet_feed_page_evidence_id: str,
    ingest_run_key: str,
    source_system: str,
    endpoint: str,
    source_activity_type: str,
    pit: PitTimestamps,
    dq_flags: Sequence[str],
    replay_fidelity: str,
    raw_evidence_reference_id: str | None = None,
) -> WalletEventObservation:
    if not isinstance(wallet_event_id, str) or not wallet_event_id:
        raise _err("REFERENCE_MISSING")
    if not isinstance(wallet_feed_page_evidence_id, str) or not wallet_feed_page_evidence_id:
        raise _err("REFERENCE_MISSING")
    _validate_ingest_run_key(ingest_run_key)
    if raw_evidence_reference_id is not None and not isinstance(raw_evidence_reference_id, str):
        raise _err("FIELD_TYPE")
    for name, value in (("source_system", source_system), ("endpoint", endpoint), ("source_activity_type", source_activity_type)):
        if not isinstance(value, str) or not value:
            raise _err("FIELD_VALUE")
    if not isinstance(pit, PitTimestamps):
        raise _err("FIELD_TYPE")
    flags = _wrap_provenance(canonicalize_dq_flags, dq_flags)
    fidelity = _wrap_provenance(validate_replay_fidelity, replay_fidelity)
    draft = WalletEventObservation(
        wallet_event_observation_id="",
        wallet_event_id=wallet_event_id,
        wallet_feed_page_evidence_id=wallet_feed_page_evidence_id,
        ingest_run_key=ingest_run_key,
        raw_evidence_reference_id=raw_evidence_reference_id,
        source_system=source_system,
        endpoint=endpoint,
        source_activity_type=source_activity_type,
        pit=pit,
        dq_flags=flags,
        replay_fidelity=fidelity,
    )
    return replace(
        draft,
        wallet_event_observation_id=_identity(
            RECORD_KIND_WALLET_EVENT_OBSERVATION, draft.logical_preimage()
        ),
    )


# --- E. WalletReconciliationLink ------------------------------------------
RECONCILIATION_STATES = (
    "API_ONLY",
    "CHAIN_ONLY",
    "API_AND_CHAIN_CONFIRMED",
    "SOURCE_DISAGREEMENT",
    "SUPERSEDED_BY_STRONGER_EVIDENCE",
    "REORGED_OR_REMOVED",
    "UNRESOLVED",
)
_RECONCILIATION_STATE_SET = frozenset(RECONCILIATION_STATES)
RECONCILIATION_RELATION_KINDS = (
    "SAME_EVENT_EQUIVALENCE",
    "SUPERSESSION",
    "CHAIN_CONFIRMATION",
    "DISAGREEMENT",
    "REORG_REMOVAL",
    "UNRESOLVED",
)
_RECONCILIATION_RELATION_SET = frozenset(RECONCILIATION_RELATION_KINDS)
FINALITY_STATES = ("UNKNOWN", "UNFINALIZED", "CONFIRMED", "FINALIZED", "REORGED")
_FINALITY_SET = frozenset(FINALITY_STATES)


@dataclass(frozen=True)
class WalletReconciliationLink:
    wallet_reconciliation_link_id: str
    reconciliation_state: str
    relation_kind: str
    event_ids: tuple[str, ...]
    predecessor_event_id: str | None
    successor_event_id: str | None
    finality_state: str
    notes: str

    def logical_preimage(self) -> dict[str, object]:
        return {
            "reconciliation_state": self.reconciliation_state,
            "relation_kind": self.relation_kind,
            "event_ids": list(self.event_ids),
            "predecessor_event_id": self.predecessor_event_id,
            "successor_event_id": self.successor_event_id,
            "finality_state": self.finality_state,
            "notes": self.notes,
        }


def build_wallet_reconciliation_link(
    *,
    reconciliation_state: str,
    relation_kind: str,
    event_ids: Sequence[str],
    predecessor_event_id: str | None = None,
    successor_event_id: str | None = None,
    finality_state: str = "UNKNOWN",
    notes: str = "",
) -> WalletReconciliationLink:
    state = _validate_enum(reconciliation_state, _RECONCILIATION_STATE_SET, "RECONCILIATION")
    relation = _validate_enum(relation_kind, _RECONCILIATION_RELATION_SET, "RECONCILIATION")
    finality = _validate_enum(finality_state, _FINALITY_SET, "RECONCILIATION")
    if isinstance(event_ids, str) or not isinstance(event_ids, Sequence):
        raise _err("FIELD_TYPE")
    ids: list[str] = []
    for eid in event_ids:
        if not isinstance(eid, str) or not eid:
            raise _err("REFERENCE_MISSING")
        ids.append(eid)
    if len(ids) == 0:
        raise _err("RECONCILIATION")
    for optional in (predecessor_event_id, successor_event_id):
        if optional is not None and (not isinstance(optional, str) or not optional):
            raise _err("REFERENCE_MISSING")
    if not isinstance(notes, str):
        raise _err("FIELD_TYPE")
    draft = WalletReconciliationLink(
        wallet_reconciliation_link_id="",
        reconciliation_state=state,
        relation_kind=relation,
        event_ids=tuple(ids),
        predecessor_event_id=predecessor_event_id,
        successor_event_id=successor_event_id,
        finality_state=finality,
        notes=notes,
    )
    return replace(
        draft,
        wallet_reconciliation_link_id=_identity(
            RECORD_KIND_WALLET_RECONCILIATION_LINK, draft.logical_preimage()
        ),
    )


# --- F. WalletProvenanceExtension -----------------------------------------
@dataclass(frozen=True)
class WalletProvenanceExtension:
    wallet_provenance_extension_id: str
    research_provenance_manifest_id: str
    chain_metadata: tuple[tuple[str, str], ...]
    indexer_metadata: tuple[tuple[str, str], ...]
    source_metadata: tuple[tuple[str, str], ...]
    cursor_metadata: tuple[tuple[str, str], ...]
    first_seen_metadata: tuple[tuple[str, str], ...]
    gap_metadata: tuple[tuple[str, str], ...]
    reconciliation_metadata: tuple[tuple[str, str], ...]
    ingest_run_key: str | None

    def logical_preimage(self) -> dict[str, object]:
        return {
            "research_provenance_manifest_id": self.research_provenance_manifest_id,
            "chain_metadata": [list(p) for p in self.chain_metadata],
            "indexer_metadata": [list(p) for p in self.indexer_metadata],
            "source_metadata": [list(p) for p in self.source_metadata],
            "cursor_metadata": [list(p) for p in self.cursor_metadata],
            "first_seen_metadata": [list(p) for p in self.first_seen_metadata],
            "gap_metadata": [list(p) for p in self.gap_metadata],
            "reconciliation_metadata": [list(p) for p in self.reconciliation_metadata],
            "ingest_run_key": self.ingest_run_key,
        }


def build_wallet_provenance_extension(
    *,
    research_provenance_manifest_id: str,
    chain_metadata: object = None,
    indexer_metadata: object = None,
    source_metadata: object = None,
    cursor_metadata: object = None,
    first_seen_metadata: object = None,
    gap_metadata: object = None,
    reconciliation_metadata: object = None,
    ingest_run_key: str | None = None,
) -> WalletProvenanceExtension:
    """Build the one-way wallet extension that references the immutable core
    manifest id. The core never references this extension; changing the manifest
    changes the extension identity, but rebuilding this extension can never change
    the manifest id."""

    if not isinstance(research_provenance_manifest_id, str) or not research_provenance_manifest_id:
        raise _err("REFERENCE_MISSING")
    if ingest_run_key is not None:
        _validate_ingest_run_key(ingest_run_key)
    draft = WalletProvenanceExtension(
        wallet_provenance_extension_id="",
        research_provenance_manifest_id=research_provenance_manifest_id,
        chain_metadata=_canonical_pairs(chain_metadata),
        indexer_metadata=_canonical_pairs(indexer_metadata),
        source_metadata=_canonical_pairs(source_metadata),
        cursor_metadata=_canonical_pairs(cursor_metadata),
        first_seen_metadata=_canonical_pairs(first_seen_metadata),
        gap_metadata=_canonical_pairs(gap_metadata),
        reconciliation_metadata=_canonical_pairs(reconciliation_metadata),
        ingest_run_key=ingest_run_key,
    )
    return replace(
        draft,
        wallet_provenance_extension_id=_identity(
            RECORD_KIND_WALLET_PROVENANCE_EXTENSION, draft.logical_preimage()
        ),
    )


# --- G. WalletIngestRunReceipt + FeedAcquisitionReceipt --------------------
FEED_COMPLETION_STATES = (
    "COMPLETE",
    "PARTIAL_LIMIT",
    "PARTIAL_SOURCE_FAILURE",
    "PARTIAL_CURSOR_GAP",
    "PARTIAL_SCHEMA_DRIFT",
    "NOT_STARTED",
    "REJECTED",
)
_FEED_COMPLETION_SET = frozenset(FEED_COMPLETION_STATES)
COLLECTION_COMPLETION_STATES = (
    "DRY_RUN",
    "COMPLETE",
    "PARTIAL_LIMIT",
    "PARTIAL_SOURCE_FAILURE",
    "PARTIAL_CURSOR_GAP",
    "PARTIAL_SCHEMA_DRIFT",
    "PARTIAL_INTERRUPTED",
    "REJECTED_BEFORE_ACQUISITION",
)
_COLLECTION_COMPLETION_SET = frozenset(COLLECTION_COMPLETION_STATES)
TIME_FILTER_CAPABILITIES = ("SUPPORTED", "NOT_SUPPORTED")
_TIME_FILTER_SET = frozenset(TIME_FILTER_CAPABILITIES)
ACQUISITION_SCOPES = (
    "REQUESTED_TIME_WINDOW",
    "ALL_AVAILABLE_AS_OF_RUN",
    "CONDITION_SCOPED_ALL_AVAILABLE_AS_OF_RUN",
)
_ACQUISITION_SCOPE_SET = frozenset(ACQUISITION_SCOPES)


@dataclass(frozen=True)
class FeedAcquisitionReceipt:
    feed_key: str
    endpoint: str
    source_contract_version: str
    canonical_wallet: str
    time_filter_capability: str
    requested_start: str | None
    requested_end: str | None
    condition_scope: tuple[str, ...]
    frozen_filters: tuple[tuple[str, str], ...]
    acquisition_scope: str
    requested_page_size: int
    page_count: int
    source_row_count: int
    page_evidence_ids: tuple[str, ...]
    cursor_chain: tuple[tuple[str | None, str | None], ...]
    terminal_has_more: bool
    feed_completion_state: str
    feed_failure_codes: tuple[str, ...]
    feed_dq_flags: tuple[str, ...]
    feed_replay_fidelity: str

    def to_dict(self) -> dict[str, object]:
        return {
            "feed_key": self.feed_key,
            "endpoint": self.endpoint,
            "source_contract_version": self.source_contract_version,
            "canonical_wallet": self.canonical_wallet,
            "time_filter_capability": self.time_filter_capability,
            "requested_start": self.requested_start,
            "requested_end": self.requested_end,
            "condition_scope": list(self.condition_scope),
            "frozen_filters": [list(p) for p in self.frozen_filters],
            "acquisition_scope": self.acquisition_scope,
            "requested_page_size": self.requested_page_size,
            "page_count": self.page_count,
            "source_row_count": self.source_row_count,
            "page_evidence_ids": list(self.page_evidence_ids),
            "cursor_chain": [list(p) for p in self.cursor_chain],
            "terminal_has_more": self.terminal_has_more,
            "feed_completion_state": self.feed_completion_state,
            "feed_failure_codes": list(self.feed_failure_codes),
            "feed_dq_flags": list(self.feed_dq_flags),
            "feed_replay_fidelity": self.feed_replay_fidelity,
        }


def build_feed_acquisition_receipt(
    *,
    feed_key: str,
    endpoint: str,
    source_contract_version: str,
    canonical_wallet: str,
    time_filter_capability: str,
    acquisition_scope: str,
    requested_page_size: int,
    feed_completion_state: str,
    feed_replay_fidelity: str,
    requested_start: str | None = None,
    requested_end: str | None = None,
    condition_scope: Sequence[str] = (),
    frozen_filters: object = None,
    page_count: int = 0,
    source_row_count: int = 0,
    page_evidence_ids: Sequence[str] = (),
    cursor_chain: Sequence[Sequence[str | None]] = (),
    terminal_has_more: bool = False,
    feed_failure_codes: Sequence[str] = (),
    feed_dq_flags: Sequence[str] = ("OK",),
) -> FeedAcquisitionReceipt:
    feed = _validate_enum(feed_key, _WALLET_FEED_KEY_SET)
    capability = _validate_enum(time_filter_capability, _TIME_FILTER_SET)
    scope = _validate_enum(acquisition_scope, _ACQUISITION_SCOPE_SET)
    completion = _validate_enum(feed_completion_state, _FEED_COMPLETION_SET)
    wallet = canonicalize_evm_address(canonical_wallet)
    start = _wrap_provenance(canonicalize_utc_timestamp, requested_start) if requested_start is not None else None
    end = _wrap_provenance(canonicalize_utc_timestamp, requested_end) if requested_end is not None else None
    # COMBO_ACTIVITY must report NOT_SUPPORTED and null start/end (15.6).
    if capability == "NOT_SUPPORTED" and (start is not None or end is not None):
        raise _err("FIELD_VALUE")
    if scope == "REQUESTED_TIME_WINDOW" and (start is None or end is None):
        raise _err("FIELD_VALUE")
    cursors: list[tuple[str | None, str | None]] = []
    for pair in cursor_chain:
        if not isinstance(pair, Sequence) or isinstance(pair, str) or len(pair) != 2:
            raise _err("FIELD_TYPE")
        incoming, outgoing = pair
        _validate_optional_cursor(incoming)
        _validate_optional_cursor(outgoing)
        cursors.append((incoming, outgoing))
    return FeedAcquisitionReceipt(
        feed_key=feed,
        endpoint=str(endpoint),
        source_contract_version=str(source_contract_version),
        canonical_wallet=wallet,
        time_filter_capability=capability,
        requested_start=start,
        requested_end=end,
        condition_scope=tuple(str(c) for c in condition_scope),
        frozen_filters=_canonical_pairs(frozen_filters),
        acquisition_scope=scope,
        requested_page_size=int(requested_page_size),
        page_count=int(page_count),
        source_row_count=int(source_row_count),
        page_evidence_ids=tuple(str(p) for p in page_evidence_ids),
        cursor_chain=tuple(cursors),
        terminal_has_more=bool(terminal_has_more),
        feed_completion_state=completion,
        feed_failure_codes=tuple(str(c) for c in feed_failure_codes),
        feed_dq_flags=_wrap_provenance(canonicalize_dq_flags, feed_dq_flags),
        feed_replay_fidelity=_wrap_provenance(validate_replay_fidelity, feed_replay_fidelity),
    )


@dataclass(frozen=True)
class WalletIngestRunReceipt:
    wallet_ingest_run_receipt_id: str
    ingest_run_key: str
    schema_version: str
    canonical_wallet: str
    run_started_at: str
    run_ended_at: str
    feed_receipts: tuple[FeedAcquisitionReceipt, ...]
    all_page_evidence_ids: tuple[str, ...]
    referenced_raw_evidence_ids: tuple[str, ...]
    freshness_refs: tuple[str, ...]
    collection_completion_state: str
    aggregate_dq_flags: tuple[str, ...]
    collection_replay_fidelity: str
    aggregate_page_count: int
    aggregate_source_row_count: int
    aggregate_event_count: int
    aggregate_observation_count: int
    ordered_event_ids: tuple[str, ...]
    ordered_observation_ids: tuple[str, ...]

    def logical_preimage(self) -> dict[str, object]:
        return {
            "ingest_run_key": self.ingest_run_key,
            "schema_version": self.schema_version,
            "canonical_wallet": self.canonical_wallet,
            "run_started_at": self.run_started_at,
            "run_ended_at": self.run_ended_at,
            "feed_receipts": [r.to_dict() for r in self.feed_receipts],
            "all_page_evidence_ids": list(self.all_page_evidence_ids),
            "referenced_raw_evidence_ids": list(self.referenced_raw_evidence_ids),
            "freshness_refs": list(self.freshness_refs),
            "collection_completion_state": self.collection_completion_state,
            "aggregate_dq_flags": list(self.aggregate_dq_flags),
            "collection_replay_fidelity": self.collection_replay_fidelity,
            "aggregate_page_count": self.aggregate_page_count,
            "aggregate_source_row_count": self.aggregate_source_row_count,
            "aggregate_event_count": self.aggregate_event_count,
            "aggregate_observation_count": self.aggregate_observation_count,
            "ordered_event_ids": list(self.ordered_event_ids),
            "ordered_observation_ids": list(self.ordered_observation_ids),
        }


def build_wallet_ingest_run_receipt(
    *,
    ingest_run_key: str,
    canonical_wallet: str,
    run_started_at: str,
    run_ended_at: str,
    feed_receipts: Sequence[FeedAcquisitionReceipt],
    collection_completion_state: str,
    collection_replay_fidelity: str,
    all_page_evidence_ids: Sequence[str] = (),
    referenced_raw_evidence_ids: Sequence[str] = (),
    freshness_refs: Sequence[str] = (),
    aggregate_dq_flags: Sequence[str] = ("OK",),
    aggregate_page_count: int = 0,
    aggregate_source_row_count: int = 0,
    aggregate_event_count: int = 0,
    aggregate_observation_count: int = 0,
    ordered_event_ids: Sequence[str] = (),
    ordered_observation_ids: Sequence[str] = (),
    schema_version: str = IDENTITY_SCHEMA_VERSION,
) -> WalletIngestRunReceipt:
    _validate_ingest_run_key(ingest_run_key)
    wallet = canonicalize_evm_address(canonical_wallet)
    started = _wrap_provenance(canonicalize_utc_timestamp, run_started_at)
    ended = _wrap_provenance(canonicalize_utc_timestamp, run_ended_at)
    completion = _validate_enum(collection_completion_state, _COLLECTION_COMPLETION_SET)
    for r in feed_receipts:
        if not isinstance(r, FeedAcquisitionReceipt):
            raise _err("FIELD_TYPE")
    draft = WalletIngestRunReceipt(
        wallet_ingest_run_receipt_id="",
        ingest_run_key=ingest_run_key,
        schema_version=schema_version,
        canonical_wallet=wallet,
        run_started_at=started,
        run_ended_at=ended,
        feed_receipts=tuple(feed_receipts),
        all_page_evidence_ids=tuple(str(p) for p in all_page_evidence_ids),
        referenced_raw_evidence_ids=tuple(str(p) for p in referenced_raw_evidence_ids),
        freshness_refs=tuple(str(p) for p in freshness_refs),
        collection_completion_state=completion,
        aggregate_dq_flags=_wrap_provenance(canonicalize_dq_flags, aggregate_dq_flags),
        collection_replay_fidelity=_wrap_provenance(validate_replay_fidelity, collection_replay_fidelity),
        aggregate_page_count=int(aggregate_page_count),
        aggregate_source_row_count=int(aggregate_source_row_count),
        aggregate_event_count=int(aggregate_event_count),
        aggregate_observation_count=int(aggregate_observation_count),
        ordered_event_ids=tuple(str(p) for p in ordered_event_ids),
        ordered_observation_ids=tuple(str(p) for p in ordered_observation_ids),
    )
    return replace(
        draft,
        wallet_ingest_run_receipt_id=_identity(
            RECORD_KIND_WALLET_INGEST_RUN_RECEIPT, draft.logical_preimage()
        ),
    )


# ---------------------------------------------------------------------------
# Shared helpers.
# ---------------------------------------------------------------------------
_MAX_CURSOR_CHARS = 4096


def _validate_optional_cursor(cursor: object) -> None:
    if cursor is None:
        return
    if not isinstance(cursor, str):
        raise _err("CURSOR")
    if len(cursor) == 0 or len(cursor) > _MAX_CURSOR_CHARS:
        raise _err("CURSOR")


def _validate_ingest_run_key(value: object) -> str:
    if not isinstance(value, str) or not value.startswith(INGEST_RUN_KEY_PREFIX):
        raise _err("FIELD_VALUE")
    remainder = value[len(INGEST_RUN_KEY_PREFIX):]
    if not re.match(r"^[0-9a-f]{64}$", remainder):
        raise _err("FIELD_VALUE")
    return value


def _canonical_pairs(value: object) -> tuple[tuple[str, str], ...]:
    if value is None:
        return ()
    if isinstance(value, Mapping):
        items = list(value.items())
    elif isinstance(value, Sequence) and not isinstance(value, str):
        items = []
        for pair in value:
            if not isinstance(pair, Sequence) or isinstance(pair, str) or len(pair) != 2:
                raise _err("FIELD_TYPE")
            items.append((pair[0], pair[1]))
    else:
        raise _err("FIELD_TYPE")
    out: list[tuple[str, str]] = []
    for key, val in items:
        if not isinstance(key, str) or not isinstance(val, str):
            raise _err("FIELD_TYPE")
        out.append((key, val))
    return tuple(sorted(out))


def derive_ingest_run_key(preimage: Mapping[str, object]) -> str:
    """Deterministically derive a pre-run ``ingest_run_key`` from a bounded
    pre-run preimage. The preimage must contain ONLY pre-run scope fields; page
    refs, response hashes, discovered cursors, counts, and outcomes are excluded
    by the caller (15.2)."""

    if not isinstance(preimage, Mapping):
        raise _err("FIELD_TYPE")
    return INGEST_RUN_KEY_PREFIX + sha256_hex(wallet_canonical_json_bytes(dict(preimage)))
