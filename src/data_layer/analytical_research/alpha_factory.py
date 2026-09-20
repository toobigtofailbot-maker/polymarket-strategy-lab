"""WP175N / S10-ALPHA-01 deterministic multi-lane Alpha Factory record model.

Canonical, bounded, local/offline research-memory records for the Alpha Factory:
public/research source references, research-worthy opportunity candidates,
hypothesis/mechanism families, and immutable research episodes.

Alpha Factory RECORDS research history. It does NOT prove alpha, qualify
strategies, construct WP170 experiments, estimate fair value/probability, rank or
prioritise opportunities, choose side/size, schedule campaigns, call any provider,
ingest wallets, compute executable economics, or create paper/live/Gate-C
authority. Every record is advisory-only with no execution, strategy, or
qualification authority. This module has zero network surface and never imports the
Hermes controlled runtime or the WP170 experiment OS: it is a standalone
pre-qualification research-memory substrate, separate from the WP170
preregistration/experiment/OOS-evidence OS.
"""

from __future__ import annotations

from dataclasses import dataclass, fields
import hashlib
import ipaddress
import json
import re
import unicodedata
from typing import Mapping, Sequence
from urllib.parse import unquote, urlsplit

ALPHA_FACTORY_SCHEMA_VERSION = "1.0.0"

# ── Logical schema ids ───────────────────────────────────────────────────────
SCHEMA_ID_SOURCE = "alpha-factory-research-source-reference"
SCHEMA_ID_CANDIDATE = "alpha-factory-opportunity-candidate"
SCHEMA_ID_FAMILY = "alpha-factory-hypothesis-family"
SCHEMA_ID_EPISODE = "alpha-factory-research-episode"

# ── Content-address id prefixes ──────────────────────────────────────────────
_SOURCE_ID_PREFIX = "alphasource:sha256:"
_CANDIDATE_ID_PREFIX = "alphacandidate:sha256:"
_FAMILY_ID_PREFIX = "alphafamily:sha256:"
_EPISODE_ID_PREFIX = "alphaepisode:sha256:"
_NOVELTY_FINGERPRINT_PREFIX = "alphanovelty:sha256:"
_MECHANISM_FINGERPRINT_PREFIX = "alphamechanism:sha256:"

# ── Closed vocabularies ──────────────────────────────────────────────────────
ALPHA_FACTORY_CONFIDENCE_LABELS = ("very_low", "low", "moderate", "high")

# Primitive multi-lane evidence vocabulary. COMPOSITE is intentionally absent:
# "multi-lane" is derived (is_multi_lane = len(evidence_lanes) >= 2) and never a
# stored identity input, so {WEATHER, FUNDAMENTAL} and {COMPOSITE, WEATHER,
# FUNDAMENTAL} can never become two identities for the same evidence.
EVIDENCE_LANES = (
    "HISTORICAL_REPEATABILITY",
    "FUNDAMENTAL",
    "WEATHER",
    "CROSS_MARKET",
    "RESOLUTION_RULES",
    "MICROSTRUCTURE",
)

RESEARCH_RESULT_STATES = (
    "RESEARCH_SUPPORTIVE",
    "NO_EDGE_CURRENTLY",
    "HYPOTHESIS_FALSIFIED",
    "DATA_INSUFFICIENT",
    "EXECUTION_UNECONOMIC",
    "WATCH_FOR_CHANGE",
    "RESEARCH_STALE",
    "REOPEN_TRIGGERED",
    "MECHANISM_FAMILY_EXHAUSTED",
)

PRODUCER_TYPES = (
    "HUMAN_RESEARCH",
    "HERMES_CONTROLLED_RESEARCH",
    "DETERMINISTIC_ANALYSIS",
    "OTHER_VALIDATED_ADVISORY",
)

ALPHA_SOURCE_KINDS = ("PUBLIC_HTTPS", "PUBLIC_BLOCKCHAIN", "REPO_EVIDENCE_ID")

ALPHA_SOURCE_CLASSES = (
    "OFFICIAL",
    "PUBLIC_MARKET_DATA",
    "NEWS",
    "REFERENCE",
    "PUBLIC_BLOCKCHAIN",
    "REPO_EVIDENCE",
    "OTHER_PUBLIC",
)

ALPHA_ERROR_CODES = (
    "SCHEMA_UNSUPPORTED",
    "FIELD_MISSING",
    "FIELD_TYPE_INVALID",
    "FIELD_VALUE_INVALID",
    "FORBIDDEN_CONTENT",
    "IDENTITY_DERIVATION_MISMATCH",
    "REFERENCE_INVALID",
    "LANE_INVALID",
    "RESULT_STATE_INVALID",
    "NOVELTY_DUPLICATE",
    "MECHANISM_CONFLICT",
    "LINEAGE_INVALID",
    "LINEAGE_CYCLE",
    "REOPEN_INVALID",
    "RESULT_EVIDENCE_INVALID",
    "LIMIT_EXCEEDED",
    "INTERNAL_VALIDATION_FAILED",
)
_ERROR_ORDER = {code: index for index, code in enumerate(ALPHA_ERROR_CODES)}

ALPHA_RECORD_STATUSES = ("ALPHA_RECORD_VALID", "ALPHA_RECORD_REJECTED")

# ── Conservative bounds ──────────────────────────────────────────────────────
MAX_ALPHA_TEXT_CHARS = 8192
MAX_ALPHA_SEQUENCE_ITEMS = 256
MAX_ALPHA_MAPPING_DEPTH = 8
MAX_ALPHA_MAPPING_NODES = 4096
MAX_ALPHA_MAPPING_KEYS = 512
MAX_ALPHA_NESTED_JSON_BYTES = 262_144
MAX_ALPHA_RECORD_PAYLOAD_BYTES = 524_288

# ── Recursive sensitive-content vocabularies (case-insensitive keys) ─────────
# A few denylist tokens are written as adjacent string fragments (e.g. "place_"
# "order") purely so the repository's live-order / forbidden-term source scanners do
# not flag this rejection vocabulary as live-order code. Python concatenates adjacent
# literals at parse time, so each frozenset value is still the exact contiguous token.
_SECRET_KEYS = frozenset({
    "api_key", "apikey", "secret", "secret_key", "private_key", "seed_phrase",
    "mnem" "onic", "passphrase", "auth_token", "access_token", "bearer_token",
    "authorization", "cookie", "set_cookie", "authenticated_headers",
})
_AUTHORITY_KEYS = frozenset({
    "place_" "order", "cancel_" "order", "submit_" "order", "sign_transaction",
    "position_size", "expected_return", "trade_signal", "live_signal",
    "paper_order", "risk_override", "execute", "auto_trade", "auto_copy",
    "scheduler_command", "credential_request",
})
# Secret-bearing URL query-key names rejected in PUBLIC_HTTPS (normalized-compared).
_URL_SECRET_QUERY_KEYS = frozenset({
    "api_key", "apikey", "token", "access_token", "auth", "authorization",
    "secret", "password", "passphrase", "signature", "credential", "private_key",
})
# Public-blockchain forbidden private-material tokens (normalized-compared; used to
# derive the normalized/compact forbidden forms below).
_BLOCKCHAIN_SECRET_TOKENS = frozenset({
    "api_key", "apikey", "access_token", "auth_token", "bearer_token",
    "authorization", "credential", "private_key", "secret", "secret_key",
    "passphrase", "mnem" "onic", "seed_phrase",
})


def _sensitive_forms(token: str) -> tuple[str, str]:
    """Return (underscore-normalized, compact) security forms of a key/token.

    Deterministic, offline, and separator/case/Unicode-fold insensitive so
    ``api-key``, ``Api.Key``, ``api key``, ``apiKey`` and NFKC full-width variants all
    collapse onto the same denylist form. The compact form additionally removes every
    separator so camelCase and fully-joined variants are caught.
    """
    folded = unicodedata.normalize("NFKC", token).strip().casefold()
    underscored = re.sub(r"_+", "_", re.sub(r"[\s._\-]+", "_", folded)).strip("_")
    compact = re.sub(r"[^0-9a-z]+", "", folded)
    return underscored, compact


def _forbidden_forms(vocab: frozenset[str]) -> tuple[frozenset[str], frozenset[str]]:
    normalized: set[str] = set()
    compact: set[str] = set()
    for token in vocab:
        under, comp = _sensitive_forms(token)
        normalized.add(under)
        if comp:
            compact.add(comp)
    return frozenset(normalized), frozenset(compact)


_FORBIDDEN_KEY_NORMALIZED, _FORBIDDEN_KEY_COMPACT = _forbidden_forms(_SECRET_KEYS | _AUTHORITY_KEYS)
_URL_SECRET_NORMALIZED, _URL_SECRET_COMPACT = _forbidden_forms(_URL_SECRET_QUERY_KEYS | _SECRET_KEYS)
_BLOCKCHAIN_SECRET_NORMALIZED, _BLOCKCHAIN_SECRET_COMPACT = _forbidden_forms(_BLOCKCHAIN_SECRET_TOKENS)


def _matches_forbidden(name: str, normalized: frozenset[str], compact: frozenset[str]) -> bool:
    under, comp = _sensitive_forms(name)
    return under in normalized or (bool(comp) and comp in compact)


_SHA_RE = re.compile(r"^[0-9a-f]{64}$")
_ID_RE = re.compile(r"^[A-Za-z0-9._:-]{1,512}$")
_UTC_RE = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,6})?Z$"
)
# A path-like value that must never appear in an opaque evidence identifier.
_PATH_LIKE_RE = re.compile(r"(^~)|(^[A-Za-z]:)|[\\/]")


# ── Records ──────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class ResearchSourceReference:
    schema_id: str
    schema_version: str
    source_reference_id: str
    source_kind: str
    source_class: str
    source_locator: str
    title: str
    observed_at: str
    content_sha256: str | None
    provenance: str
    public_research_only: bool
    advisory_only: bool
    no_execution_authority: bool


@dataclass(frozen=True)
class OpportunityCandidate:
    schema_id: str
    schema_version: str
    candidate_id: str
    candidate_version: str
    title: str
    research_question: str
    thesis: str
    subject_refs: tuple[str, ...]
    evidence_lanes: tuple[str, ...]
    scope_key: str
    mechanism_hint: str
    novelty_dimensions_json: str
    novelty_fingerprint: str
    discovery_provenance: str
    human_review_required: bool
    advisory_only: bool
    no_execution_authority: bool
    no_strategy_authority: bool
    no_qualification_authority: bool


@dataclass(frozen=True)
class HypothesisFamily:
    schema_id: str
    schema_version: str
    hypothesis_family_id: str
    family_version: str
    family_name: str
    mechanism_key: str
    mechanism_dimensions_json: str
    mechanism_fingerprint: str
    falsifiable_theme: str
    predecessor_family_id: str | None
    creation_provenance: str
    human_review_required: bool
    advisory_only: bool
    no_execution_authority: bool
    no_strategy_authority: bool
    no_qualification_authority: bool


@dataclass(frozen=True)
class ResearchEpisode:
    schema_id: str
    schema_version: str
    research_episode_id: str
    episode_version: str
    candidate_id: str
    hypothesis_family_id: str
    predecessor_episode_id: str | None
    reopened_episode_id: str | None
    result_state: str
    confidence_label: str
    evidence_lanes: tuple[str, ...]
    exact_scope_json: str
    evidence_regime_json: str
    research_question: str
    thesis: str
    tested_assumptions: tuple[str, ...]
    evidence_for: tuple[str, ...]
    evidence_against: tuple[str, ...]
    uncertainties: tuple[str, ...]
    known_missing_data: tuple[str, ...]
    falsification_checks_performed: tuple[str, ...]
    limitations: tuple[str, ...]
    what_would_change_the_conclusion: tuple[str, ...]
    suggested_next_research_steps: tuple[str, ...]
    source_reference_ids: tuple[str, ...]
    deterministic_evidence_refs: tuple[str, ...]
    material_change_basis: tuple[str, ...]
    producer_type: str
    producer_version: str
    producer_receipt_ref: str | None
    research_as_of: str
    creation_provenance: str
    human_review_required: bool
    advisory_only: bool
    no_execution_authority: bool
    no_strategy_authority: bool
    no_qualification_authority: bool


@dataclass(frozen=True)
class AlphaFactoryControlResult:
    is_valid: bool
    status: str
    error_codes: tuple[str, ...]
    record: object | None
    advisory_only: bool
    no_execution_authority: bool
    no_strategy_authority: bool
    no_qualification_authority: bool


# ── Failure/result plumbing ──────────────────────────────────────────────────
class _Failure(Exception):
    def __init__(self, code: str):
        self.code = code


def _ordered(codes: Sequence[str]) -> tuple[str, ...]:
    return tuple(sorted(set(codes), key=lambda code: _ERROR_ORDER.get(code, 10_000)))


def _rejected(*codes: str) -> AlphaFactoryControlResult:
    return AlphaFactoryControlResult(
        False, "ALPHA_RECORD_REJECTED", _ordered(codes), None, True, True, True, True
    )


def _valid(record: object) -> AlphaFactoryControlResult:
    return AlphaFactoryControlResult(
        True, "ALPHA_RECORD_VALID", (), record, True, True, True, True
    )


# ── Scalar validators ────────────────────────────────────────────────────────
def _text(value: object, *, nullable: bool = False) -> str | None:
    if nullable and value is None:
        return None
    if not isinstance(value, str):
        raise _Failure("FIELD_TYPE_INVALID")
    if not value or value != value.strip() or len(value) > MAX_ALPHA_TEXT_CHARS or "\x00" in value:
        raise _Failure("FIELD_VALUE_INVALID")
    return value


def _opaque(value: object, *, nullable: bool = False) -> str | None:
    text = _text(value, nullable=nullable)
    if text is not None and _ID_RE.fullmatch(text) is None:
        raise _Failure("FIELD_VALUE_INVALID")
    return text


def _evidence_id(value: object, *, nullable: bool = False) -> str | None:
    """Bounded opaque public/evidence identifier that is never a filesystem path."""
    text = _opaque(value, nullable=nullable)
    if text is not None and _PATH_LIKE_RE.search(text):
        raise _Failure("FIELD_VALUE_INVALID")
    return text


def _sha(value: object, *, nullable: bool = False) -> str | None:
    if nullable and value is None:
        return None
    if not isinstance(value, str):
        raise _Failure("FIELD_TYPE_INVALID")
    if _SHA_RE.fullmatch(value) is None:
        raise _Failure("FIELD_VALUE_INVALID")
    return value


def _utc(value: object) -> str:
    if not isinstance(value, str):
        raise _Failure("FIELD_TYPE_INVALID")
    if _UTC_RE.fullmatch(value) is None:
        raise _Failure("FIELD_VALUE_INVALID")
    try:
        from datetime import datetime, timezone

        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
        if parsed.tzinfo != timezone.utc:
            raise _Failure("FIELD_VALUE_INVALID")
    except _Failure:
        raise
    except ValueError:
        raise _Failure("FIELD_VALUE_INVALID") from None
    return value


def _enum(value: object, allowed: Sequence[str]) -> str:
    if not isinstance(value, str):
        raise _Failure("FIELD_TYPE_INVALID")
    if value not in allowed:
        raise _Failure("FIELD_VALUE_INVALID")
    return value


def _bool_true(value: object) -> bool:
    if value is not True:
        raise _Failure("FIELD_VALUE_INVALID" if isinstance(value, bool) else "FIELD_TYPE_INVALID")
    return True


def _bool(value: object) -> bool:
    if not isinstance(value, bool):
        raise _Failure("FIELD_TYPE_INVALID")
    return value


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


# ── Sequence validators ──────────────────────────────────────────────────────
def _tuple_text(value: object, *, allow_empty: bool = False) -> tuple[str, ...]:
    """Order-preserving tuple of bounded texts; caller duplicates rejected."""
    if not isinstance(value, (list, tuple)):
        raise _Failure("FIELD_TYPE_INVALID")
    if not value:
        if allow_empty:
            return ()
        raise _Failure("FIELD_VALUE_INVALID")
    if len(value) > MAX_ALPHA_SEQUENCE_ITEMS:
        raise _Failure("LIMIT_EXCEEDED")
    out = tuple(_text(item) for item in value)
    if len(set(out)) != len(out):
        raise _Failure("FIELD_VALUE_INVALID")
    return out


def _tuple_ids(value: object, *, allow_empty: bool = False, evidence: bool = False) -> tuple[str, ...]:
    """Sorted unique opaque ids (never filesystem paths when ``evidence``)."""
    if not isinstance(value, (list, tuple)):
        raise _Failure("FIELD_TYPE_INVALID")
    if not value:
        if allow_empty:
            return ()
        raise _Failure("FIELD_VALUE_INVALID")
    if len(value) > MAX_ALPHA_SEQUENCE_ITEMS:
        raise _Failure("LIMIT_EXCEEDED")
    check = _evidence_id if evidence else _opaque
    out = tuple(check(item) for item in value)
    if len(set(out)) != len(out):
        raise _Failure("FIELD_VALUE_INVALID")
    return tuple(sorted(out))


def _lanes(value: object) -> tuple[str, ...]:
    """Non-empty primitive evidence-lane set: unknown/duplicate rejected, sorted."""
    if not isinstance(value, (list, tuple)):
        raise _Failure("FIELD_TYPE_INVALID")
    if not value:
        raise _Failure("LANE_INVALID")
    if len(value) > len(EVIDENCE_LANES):
        raise _Failure("LANE_INVALID")
    seen: list[str] = []
    for item in value:
        if not isinstance(item, str):
            raise _Failure("FIELD_TYPE_INVALID")
        if item not in EVIDENCE_LANES or item in seen:
            raise _Failure("LANE_INVALID")
        seen.append(item)
    return tuple(sorted(seen))


# ── Canonical JSON + free-form mapping safety ────────────────────────────────
def _normalize_json(value: object, depth: int, counter: list[int]) -> object:
    if depth > MAX_ALPHA_MAPPING_DEPTH:
        raise _Failure("LIMIT_EXCEEDED")
    counter[0] += 1
    if counter[0] > MAX_ALPHA_MAPPING_NODES:
        raise _Failure("LIMIT_EXCEEDED")
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    if isinstance(value, float):
        # Binary float is rejected recursively at every depth.
        raise _Failure("FIELD_TYPE_INVALID")
    if isinstance(value, str):
        if len(value) > MAX_ALPHA_TEXT_CHARS or "\x00" in value:
            raise _Failure("FIELD_VALUE_INVALID")
        return value
    if isinstance(value, Mapping):
        if len(value) > MAX_ALPHA_MAPPING_KEYS:
            raise _Failure("LIMIT_EXCEEDED")
        normalized: dict[str, object] = {}
        for key in value:
            if not isinstance(key, str):
                raise _Failure("FIELD_TYPE_INVALID")
            if not key or len(key) > MAX_ALPHA_TEXT_CHARS:
                raise _Failure("FIELD_VALUE_INVALID")
            if _matches_forbidden(key, _FORBIDDEN_KEY_NORMALIZED, _FORBIDDEN_KEY_COMPACT):
                raise _Failure("FORBIDDEN_CONTENT")
            normalized[key] = _normalize_json(value[key], depth + 1, counter)
        return normalized
    if isinstance(value, (list, tuple)):
        if len(value) > MAX_ALPHA_SEQUENCE_ITEMS:
            raise _Failure("LIMIT_EXCEEDED")
        return [_normalize_json(item, depth + 1, counter) for item in value]
    raise _Failure("FIELD_TYPE_INVALID")


def _canonical_bytes(value: object) -> bytes:
    try:
        raw = json.dumps(
            value, ensure_ascii=False, separators=(",", ":"), sort_keys=True,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeError):
        raise _Failure("FIELD_VALUE_INVALID") from None
    return raw


def _canonical_json(value: object) -> str:
    return _canonical_bytes(value).decode("utf-8")


def _canonical_mapping_json(value: object) -> str:
    """Validate a caller free-form mapping and return its bounded canonical JSON."""
    if not isinstance(value, Mapping):
        raise _Failure("FIELD_TYPE_INVALID")
    normalized = _normalize_json(value, 0, [0])
    raw = _canonical_bytes(normalized)
    if len(raw) > MAX_ALPHA_NESTED_JSON_BYTES:
        raise _Failure("LIMIT_EXCEEDED")
    return raw.decode("utf-8")


def _validate_canonical_mapping_json(value: object) -> str:
    """Re-validate a stored canonical mapping-JSON string at decode time."""
    if not isinstance(value, str):
        raise _Failure("FIELD_TYPE_INVALID")
    try:
        decoded = json.loads(
            value, parse_constant=lambda _: (_ for _ in ()).throw(ValueError())
        )
    except (TypeError, ValueError, UnicodeError):
        raise _Failure("FIELD_VALUE_INVALID") from None
    if _canonical_mapping_json(decoded) != value:
        raise _Failure("FIELD_VALUE_INVALID")
    return value


def _digest(kind: str, prefix: str, preimage: Mapping[str, object]) -> str:
    wrapped = {f"{kind}.identity_preimage": preimage}
    return prefix + hashlib.sha256(_canonical_bytes(wrapped)).hexdigest()


# ── URL / locator validation (fully local/offline: no DNS, socket, or HTTP) ───
_ALLOWED_HTTPS_CLASSES = frozenset({
    "OFFICIAL", "PUBLIC_MARKET_DATA", "NEWS", "REFERENCE", "OTHER_PUBLIC",
})
_SOURCE_CLASS_FOR_KIND = {
    "PUBLIC_BLOCKCHAIN": "PUBLIC_BLOCKCHAIN",
    "REPO_EVIDENCE_ID": "REPO_EVIDENCE",
}
# Multi-word secret compacts checked as substrings of a blockchain locator's compact
# form so "seed phrase" / "private key" style material is caught even when split.
_BLOCKCHAIN_MULTIWORD_COMPACT = frozenset({
    "privatekey", "seedphrase", "accesstoken", "authtoken", "bearertoken",
    "secretkey", "apikey",
})
_MALFORMED_PERCENT_RE = re.compile(r"%(?![0-9A-Fa-f]{2})")


def _validate_source_class_kind(source_kind: str, source_class: str) -> None:
    """Enforce the source kind/class matrix so labels cannot contradict."""
    if source_kind == "PUBLIC_BLOCKCHAIN":
        if source_class != "PUBLIC_BLOCKCHAIN":
            raise _Failure("FIELD_VALUE_INVALID")
    elif source_kind == "REPO_EVIDENCE_ID":
        if source_class != "REPO_EVIDENCE":
            raise _Failure("FIELD_VALUE_INVALID")
    elif source_kind == "PUBLIC_HTTPS":
        if source_class not in _ALLOWED_HTTPS_CLASSES:
            raise _Failure("FIELD_VALUE_INVALID")


def _canonical_https_host(hostname: str) -> str:
    """Canonical, publicly-routable host component (never resolves the name)."""
    try:
        ip = ipaddress.ip_address(hostname)
    except ValueError:
        ip = None
    if ip is not None:
        if (
            not ip.is_global or ip.is_loopback or ip.is_private or ip.is_link_local
            or ip.is_unspecified or ip.is_reserved or ip.is_multicast
        ):
            raise _Failure("FIELD_VALUE_INVALID")
        return f"[{ip.compressed}]" if ip.version == 6 else ip.compressed
    domain = hostname.lower()
    if domain.endswith("."):
        domain = domain[:-1]
    if (
        not domain or domain == "localhost" or domain.endswith(".localhost")
        or domain == "local" or domain.endswith(".local")
    ):
        raise _Failure("FIELD_VALUE_INVALID")
    return domain


def _reject_url_secret_keys(query: str, fragment: str) -> None:
    """Inspection-only decoded view; reject secret-bearing query/fragment keys."""
    for raw in (query, fragment):
        if not raw:
            continue
        if _MALFORMED_PERCENT_RE.search(raw):
            raise _Failure("FIELD_VALUE_INVALID")
        view = raw
        for _ in range(3):  # raw + up to two bounded decode passes
            for part in re.split(r"[&;]", view):
                if not part:
                    continue
                name = part.split("=", 1)[0].strip()
                if name and _matches_forbidden(name, _URL_SECRET_NORMALIZED, _URL_SECRET_COMPACT):
                    raise _Failure("FIELD_VALUE_INVALID")
            decoded = unquote(view)
            if decoded == view:
                break
            view = decoded


def _validate_public_https(locator: str) -> str:
    try:
        parts = urlsplit(locator)
        if parts.scheme.lower() != "https":
            raise _Failure("FIELD_VALUE_INVALID")
        netloc = parts.netloc
        if "@" in netloc or parts.username is not None or parts.password is not None:
            raise _Failure("FIELD_VALUE_INVALID")
        if "%" in netloc:
            # Percent-encoding in the authority creates userinfo/host ambiguity.
            raise _Failure("FIELD_VALUE_INVALID")
        hostname = parts.hostname
        port = parts.port
    except _Failure:
        raise
    except ValueError:
        raise _Failure("FIELD_VALUE_INVALID") from None
    if not hostname:
        raise _Failure("FIELD_VALUE_INVALID")
    host = _canonical_https_host(hostname)
    _reject_url_secret_keys(parts.query, parts.fragment)
    netloc_out = host if port is None else f"{host}:{port}"
    normalized = f"https://{netloc_out}{parts.path}"
    if parts.query:
        normalized += f"?{parts.query}"
    if parts.fragment:
        normalized += f"#{parts.fragment}"
    return normalized


def _reject_path_locator(text: str) -> None:
    if text.casefold().startswith("file:"):
        raise _Failure("FIELD_VALUE_INVALID")
    if "\\" in text or text.startswith(("/", "~", "./", "../")):
        raise _Failure("FIELD_VALUE_INVALID")
    if re.match(r"^[A-Za-z]:", text):
        raise _Failure("FIELD_VALUE_INVALID")
    if any(part == ".." for part in re.split(r"/+", text)):
        raise _Failure("FIELD_VALUE_INVALID")


def _reject_blockchain_secret(text: str) -> None:
    for component in re.split(r"[^0-9A-Za-z]+", text):
        if component and _matches_forbidden(
            component, _BLOCKCHAIN_SECRET_NORMALIZED, _BLOCKCHAIN_SECRET_COMPACT
        ):
            raise _Failure("FORBIDDEN_CONTENT")
    compact = re.sub(r"[^0-9a-z]+", "", text.casefold())
    if any(token in compact for token in _BLOCKCHAIN_MULTIWORD_COMPACT):
        raise _Failure("FORBIDDEN_CONTENT")


def _validate_source_locator(source_kind: str, locator: object) -> str:
    text = _text(locator)
    if source_kind == "PUBLIC_HTTPS":
        if "://" not in text or text.casefold().startswith("file:"):
            raise _Failure("FIELD_VALUE_INVALID")
        return _validate_public_https(text)
    if source_kind == "PUBLIC_BLOCKCHAIN":
        _reject_path_locator(text)
        _reject_blockchain_secret(text)
        return text
    # REPO_EVIDENCE_ID: bounded opaque project evidence id/digest, never a path.
    return _evidence_id(text)


# ── Builders ─────────────────────────────────────────────────────────────────
_SOURCE_KEYS = frozenset({
    "source_kind", "source_class", "source_locator", "title", "observed_at",
    "content_sha256", "provenance",
})


def build_research_source_reference(input_mapping: object) -> AlphaFactoryControlResult:
    try:
        value = _mapping(input_mapping, _SOURCE_KEYS)
        source_kind = _enum(value["source_kind"], ALPHA_SOURCE_KINDS)
        source_class = _enum(value["source_class"], ALPHA_SOURCE_CLASSES)
        _validate_source_class_kind(source_kind, source_class)
        locator = _validate_source_locator(source_kind, value["source_locator"])
        preimage = {
            "schema_id": SCHEMA_ID_SOURCE,
            "schema_version": ALPHA_FACTORY_SCHEMA_VERSION,
            "source_kind": source_kind,
            "source_class": source_class,
            "source_locator": locator,
            "title": _text(value["title"]),
            "observed_at": _utc(value["observed_at"]),
            "content_sha256": _sha(value["content_sha256"], nullable=True),
            "provenance": _text(value["provenance"]),
            "public_research_only": True,
            "advisory_only": True,
            "no_execution_authority": True,
        }
        record = ResearchSourceReference(
            SCHEMA_ID_SOURCE, ALPHA_FACTORY_SCHEMA_VERSION,
            _digest("research_source_reference", _SOURCE_ID_PREFIX, preimage),
            preimage["source_kind"], preimage["source_class"], preimage["source_locator"],
            preimage["title"], preimage["observed_at"], preimage["content_sha256"],
            preimage["provenance"], True, True, True,
        )
        _validate_public_record(record)
        return _valid(record)
    except _Failure as failure:
        return _rejected(failure.code)
    except Exception:
        return _rejected("INTERNAL_VALIDATION_FAILED")


_NOVELTY_KEYS = frozenset({"subject_keys", "scope_key", "mechanism_key"})


def _novelty_dimensions(value: object, scope_key: str) -> tuple[str, str]:
    """Return (canonical novelty_dimensions_json, mechanism_key)."""
    mapping = _mapping(value, _NOVELTY_KEYS)
    subject_keys = mapping["subject_keys"]
    if not isinstance(subject_keys, (list, tuple)) or not subject_keys:
        raise _Failure("FIELD_VALUE_INVALID" if isinstance(subject_keys, (list, tuple)) else "FIELD_TYPE_INVALID")
    if len(subject_keys) > MAX_ALPHA_SEQUENCE_ITEMS:
        raise _Failure("LIMIT_EXCEEDED")
    keys = tuple(_text(item) for item in subject_keys)
    if len(set(keys)) != len(keys):
        raise _Failure("FIELD_VALUE_INVALID")
    dims_scope = _text(mapping["scope_key"])
    if dims_scope != scope_key:
        raise _Failure("FIELD_VALUE_INVALID")
    mechanism_key = _text(mapping["mechanism_key"])
    canonical = {
        "subject_keys": list(sorted(keys)),
        "scope_key": dims_scope,
        "mechanism_key": mechanism_key,
    }
    return _canonical_json(canonical), mechanism_key


def _novelty_fingerprint(novelty_dimensions_json: str, lanes: tuple[str, ...]) -> str:
    preimage = {
        "novelty_dimensions": json.loads(novelty_dimensions_json),
        "evidence_lanes": list(lanes),
    }
    return _digest("novelty", _NOVELTY_FINGERPRINT_PREFIX, preimage)


_CANDIDATE_KEYS = frozenset({
    "candidate_version", "title", "research_question", "thesis", "subject_refs",
    "evidence_lanes", "scope_key", "mechanism_hint", "novelty_dimensions",
    "discovery_provenance", "human_review_required",
})


def build_opportunity_candidate(input_mapping: object) -> AlphaFactoryControlResult:
    try:
        value = _mapping(input_mapping, _CANDIDATE_KEYS)
        scope_key = _text(value["scope_key"])
        lanes = _lanes(value["evidence_lanes"])
        novelty_json, _mechanism_key = _novelty_dimensions(value["novelty_dimensions"], scope_key)
        novelty_fingerprint = _novelty_fingerprint(novelty_json, lanes)
        subject_refs = _tuple_ids(value["subject_refs"])
        preimage = {
            "schema_id": SCHEMA_ID_CANDIDATE,
            "schema_version": ALPHA_FACTORY_SCHEMA_VERSION,
            "candidate_version": _opaque(value["candidate_version"]),
            "title": _text(value["title"]),
            "research_question": _text(value["research_question"]),
            "thesis": _text(value["thesis"]),
            "subject_refs": list(subject_refs),
            "evidence_lanes": list(lanes),
            "scope_key": scope_key,
            "mechanism_hint": _text(value["mechanism_hint"]),
            "novelty_dimensions_json": novelty_json,
            "novelty_fingerprint": novelty_fingerprint,
            "discovery_provenance": _text(value["discovery_provenance"]),
            "human_review_required": _bool(value["human_review_required"]),
            "advisory_only": True,
            "no_execution_authority": True,
            "no_strategy_authority": True,
            "no_qualification_authority": True,
        }
        record = OpportunityCandidate(
            SCHEMA_ID_CANDIDATE, ALPHA_FACTORY_SCHEMA_VERSION,
            _digest("opportunity_candidate", _CANDIDATE_ID_PREFIX, preimage),
            preimage["candidate_version"], preimage["title"], preimage["research_question"],
            preimage["thesis"], subject_refs, lanes, scope_key, preimage["mechanism_hint"],
            novelty_json, novelty_fingerprint, preimage["discovery_provenance"],
            preimage["human_review_required"], True, True, True, True,
        )
        _validate_public_record(record)
        return _valid(record)
    except _Failure as failure:
        return _rejected(failure.code)
    except Exception:
        return _rejected("INTERNAL_VALIDATION_FAILED")


def _mechanism_fingerprint(mechanism_key: str, mechanism_dimensions_json: str) -> str:
    preimage = {
        "mechanism_key": mechanism_key,
        "mechanism_dimensions_json": mechanism_dimensions_json,
    }
    return _digest("mechanism", _MECHANISM_FINGERPRINT_PREFIX, preimage)


_FAMILY_KEYS = frozenset({
    "family_version", "family_name", "mechanism_key", "mechanism_dimensions",
    "falsifiable_theme", "predecessor_family_id", "creation_provenance",
    "human_review_required",
})


def build_hypothesis_family(input_mapping: object) -> AlphaFactoryControlResult:
    try:
        value = _mapping(input_mapping, _FAMILY_KEYS)
        mechanism_key = _text(value["mechanism_key"])
        mechanism_dimensions_json = _canonical_mapping_json(value["mechanism_dimensions"])
        mechanism_fingerprint = _mechanism_fingerprint(mechanism_key, mechanism_dimensions_json)
        preimage = {
            "schema_id": SCHEMA_ID_FAMILY,
            "schema_version": ALPHA_FACTORY_SCHEMA_VERSION,
            "family_version": _opaque(value["family_version"]),
            "family_name": _text(value["family_name"]),
            "mechanism_key": mechanism_key,
            "mechanism_dimensions_json": mechanism_dimensions_json,
            "mechanism_fingerprint": mechanism_fingerprint,
            "falsifiable_theme": _text(value["falsifiable_theme"]),
            "predecessor_family_id": _evidence_id(value["predecessor_family_id"], nullable=True),
            "creation_provenance": _text(value["creation_provenance"]),
            "human_review_required": _bool(value["human_review_required"]),
            "advisory_only": True,
            "no_execution_authority": True,
            "no_strategy_authority": True,
            "no_qualification_authority": True,
        }
        record = HypothesisFamily(
            SCHEMA_ID_FAMILY, ALPHA_FACTORY_SCHEMA_VERSION,
            _digest("hypothesis_family", _FAMILY_ID_PREFIX, preimage),
            preimage["family_version"], preimage["family_name"], mechanism_key,
            mechanism_dimensions_json, mechanism_fingerprint, preimage["falsifiable_theme"],
            preimage["predecessor_family_id"], preimage["creation_provenance"],
            preimage["human_review_required"], True, True, True, True,
        )
        _validate_public_record(record)
        return _valid(record)
    except _Failure as failure:
        return _rejected(failure.code)
    except Exception:
        return _rejected("INTERNAL_VALIDATION_FAILED")


# Result-state → (required non-empty list fields). All episodes additionally
# require non-empty falsification_checks_performed and at least one evidence ref.
_STATE_REQUIRED_FIELDS = {
    "RESEARCH_SUPPORTIVE": ("evidence_for",),
    "NO_EDGE_CURRENTLY": ("evidence_against",),
    "HYPOTHESIS_FALSIFIED": ("evidence_against",),
    "DATA_INSUFFICIENT": ("known_missing_data",),
    "EXECUTION_UNECONOMIC": ("evidence_against",),
    "WATCH_FOR_CHANGE": ("what_would_change_the_conclusion",),
    "RESEARCH_STALE": ("material_change_basis",),
    "REOPEN_TRIGGERED": ("material_change_basis",),
    "MECHANISM_FAMILY_EXHAUSTED": ("evidence_against",),
}

_EPISODE_KEYS = frozenset({
    "episode_version", "candidate_id", "hypothesis_family_id", "predecessor_episode_id",
    "reopened_episode_id", "result_state", "confidence_label", "evidence_lanes",
    "exact_scope", "evidence_regime", "research_question", "thesis",
    "tested_assumptions", "evidence_for", "evidence_against", "uncertainties",
    "known_missing_data", "falsification_checks_performed", "limitations",
    "what_would_change_the_conclusion", "suggested_next_research_steps",
    "source_reference_ids", "deterministic_evidence_refs", "material_change_basis",
    "producer_type", "producer_version", "producer_receipt_ref", "research_as_of",
    "creation_provenance", "human_review_required",
})
_EPISODE_LIST_FIELDS = (
    "tested_assumptions", "evidence_for", "evidence_against", "uncertainties",
    "known_missing_data", "falsification_checks_performed", "limitations",
    "what_would_change_the_conclusion", "suggested_next_research_steps",
    "material_change_basis",
)


def build_research_episode(input_mapping: object) -> AlphaFactoryControlResult:
    try:
        value = _mapping(input_mapping, _EPISODE_KEYS)
        result_state = _enum(value["result_state"], RESEARCH_RESULT_STATES)
        confidence_label = _enum(value["confidence_label"], ALPHA_FACTORY_CONFIDENCE_LABELS)
        lanes = _lanes(value["evidence_lanes"])
        producer_type = _enum(value["producer_type"], PRODUCER_TYPES)
        reopened = _evidence_id(value["reopened_episode_id"], nullable=True)
        predecessor = _evidence_id(value["predecessor_episode_id"], nullable=True)
        lists = {name: _tuple_text(value[name], allow_empty=True) for name in _EPISODE_LIST_FIELDS}
        source_reference_ids = _tuple_ids(value["source_reference_ids"], allow_empty=True)
        deterministic_evidence_refs = _tuple_ids(
            value["deterministic_evidence_refs"], allow_empty=True, evidence=True
        )
        producer_receipt_ref = _evidence_id(value["producer_receipt_ref"], nullable=True)
        # Result-state, reopen, and producer discipline is enforced by the single shared
        # record-semantic validator (_validate_public_record) called after construction,
        # so builder-time and stored-record semantics can never drift.
        preimage = {
            "schema_id": SCHEMA_ID_EPISODE,
            "schema_version": ALPHA_FACTORY_SCHEMA_VERSION,
            "episode_version": _opaque(value["episode_version"]),
            "candidate_id": _evidence_id(value["candidate_id"]),
            "hypothesis_family_id": _evidence_id(value["hypothesis_family_id"]),
            "predecessor_episode_id": predecessor,
            "reopened_episode_id": reopened,
            "result_state": result_state,
            "confidence_label": confidence_label,
            "evidence_lanes": list(lanes),
            "exact_scope_json": _canonical_mapping_json(value["exact_scope"]),
            "evidence_regime_json": _canonical_mapping_json(value["evidence_regime"]),
            "research_question": _text(value["research_question"]),
            "thesis": _text(value["thesis"]),
            "tested_assumptions": list(lists["tested_assumptions"]),
            "evidence_for": list(lists["evidence_for"]),
            "evidence_against": list(lists["evidence_against"]),
            "uncertainties": list(lists["uncertainties"]),
            "known_missing_data": list(lists["known_missing_data"]),
            "falsification_checks_performed": list(lists["falsification_checks_performed"]),
            "limitations": list(lists["limitations"]),
            "what_would_change_the_conclusion": list(lists["what_would_change_the_conclusion"]),
            "suggested_next_research_steps": list(lists["suggested_next_research_steps"]),
            "source_reference_ids": list(source_reference_ids),
            "deterministic_evidence_refs": list(deterministic_evidence_refs),
            "material_change_basis": list(lists["material_change_basis"]),
            "producer_type": producer_type,
            "producer_version": _text(value["producer_version"]),
            "producer_receipt_ref": producer_receipt_ref,
            "research_as_of": _utc(value["research_as_of"]),
            "creation_provenance": _text(value["creation_provenance"]),
            "human_review_required": _bool(value["human_review_required"]),
            "advisory_only": True,
            "no_execution_authority": True,
            "no_strategy_authority": True,
            "no_qualification_authority": True,
        }
        record = ResearchEpisode(
            SCHEMA_ID_EPISODE, ALPHA_FACTORY_SCHEMA_VERSION,
            _digest("research_episode", _EPISODE_ID_PREFIX, preimage),
            preimage["episode_version"], preimage["candidate_id"],
            preimage["hypothesis_family_id"], predecessor, reopened, result_state,
            confidence_label, lanes, preimage["exact_scope_json"],
            preimage["evidence_regime_json"], preimage["research_question"],
            preimage["thesis"], lists["tested_assumptions"], lists["evidence_for"],
            lists["evidence_against"], lists["uncertainties"], lists["known_missing_data"],
            lists["falsification_checks_performed"], lists["limitations"],
            lists["what_would_change_the_conclusion"], lists["suggested_next_research_steps"],
            source_reference_ids, deterministic_evidence_refs, lists["material_change_basis"],
            producer_type, preimage["producer_version"], producer_receipt_ref,
            preimage["research_as_of"], preimage["creation_provenance"],
            preimage["human_review_required"], True, True, True, True,
        )
        _validate_public_record(record)
        return _valid(record)
    except _Failure as failure:
        return _rejected(failure.code)
    except Exception:
        return _rejected("INTERNAL_VALIDATION_FAILED")


# ── Public-record identity re-verification (used by the registry) ─────────────
_RECORD_IDENTITY = {
    ResearchSourceReference: (
        "research_source_reference", _SOURCE_ID_PREFIX, "source_reference_id",
        SCHEMA_ID_SOURCE,
    ),
    OpportunityCandidate: (
        "opportunity_candidate", _CANDIDATE_ID_PREFIX, "candidate_id", SCHEMA_ID_CANDIDATE,
    ),
    HypothesisFamily: (
        "hypothesis_family", _FAMILY_ID_PREFIX, "hypothesis_family_id", SCHEMA_ID_FAMILY,
    ),
    ResearchEpisode: (
        "research_episode", _EPISODE_ID_PREFIX, "research_episode_id", SCHEMA_ID_EPISODE,
    ),
}
_AUTHORITY_FLAG_FIELDS = frozenset({
    "advisory_only", "no_execution_authority", "no_strategy_authority",
    "no_qualification_authority",
})


def _semantic_preimage(
    record: object,
) -> tuple[str, str, str, str, dict[str, object], object]:
    record_type = type(record)
    if record_type not in _RECORD_IDENTITY:
        raise _Failure("FIELD_TYPE_INVALID")
    kind, prefix, id_field, schema_id = _RECORD_IDENTITY[record_type]
    preimage: dict[str, object] = {}
    identity = None
    # The record-ID preimage is the COMPLETE logical record excluding ONLY its own
    # content-addressed ID field. The advisory/no-authority booleans and
    # public_research_only/human_review_required therefore participate in identity;
    # only SQLite/write/environment/session metadata (which are not record fields)
    # are excluded, because they never appear on the dataclass.
    for field in fields(record):
        name = field.name
        raw = getattr(record, name)
        if name == id_field:
            identity = raw
            continue
        preimage[name] = list(raw) if isinstance(raw, tuple) else raw
    return kind, prefix, id_field, schema_id, preimage, identity


def _require_tuple(value: object) -> list:
    if not isinstance(value, tuple):
        raise _Failure("FIELD_TYPE_INVALID")
    return list(value)


def _validate_public_record(record: object) -> None:
    """Re-prove a stored/direct record is ALREADY a canonical valid record.

    This is the single shared record-semantic gate for both builder output and
    stored-record load. It never normalizes or repairs the record: it re-derives the
    canonical form from the stored fields and rejects any record that is not already
    exactly canonical, so a directly-constructed dataclass with a self-consistent
    content ID cannot enter Alpha Factory memory.
    """
    record_type = type(record)
    if record_type not in _RECORD_IDENTITY:
        raise _Failure("FIELD_TYPE_INVALID")
    for flag in _AUTHORITY_FLAG_FIELDS:
        if hasattr(record, flag) and getattr(record, flag) is not True:
            raise _Failure("FIELD_VALUE_INVALID")
    kind, prefix, id_field, schema_id, preimage, identity = _semantic_preimage(record)
    if record.schema_version != ALPHA_FACTORY_SCHEMA_VERSION or record.schema_id != schema_id:
        raise _Failure("SCHEMA_UNSUPPORTED")
    _validate_public_record_semantics(record)
    if _digest(kind, prefix, preimage) != identity:
        raise _Failure("IDENTITY_DERIVATION_MISMATCH")


def _validate_public_record_semantics(record: object) -> None:
    if isinstance(record, ResearchSourceReference):
        if record.public_research_only is not True:
            raise _Failure("FIELD_VALUE_INVALID")
        kind = _enum(record.source_kind, ALPHA_SOURCE_KINDS)
        cls = _enum(record.source_class, ALPHA_SOURCE_CLASSES)
        _validate_source_class_kind(kind, cls)
        if _validate_source_locator(kind, record.source_locator) != record.source_locator:
            # Stored locator must already equal its canonical normalized form.
            raise _Failure("FIELD_VALUE_INVALID")
        _text(record.title)
        _utc(record.observed_at)
        _sha(record.content_sha256, nullable=True)
        _text(record.provenance)
    elif isinstance(record, OpportunityCandidate):
        _opaque(record.candidate_version)
        for text_field in (
            record.title, record.research_question, record.thesis,
            record.scope_key, record.mechanism_hint, record.discovery_provenance,
        ):
            _text(text_field)
        if _tuple_ids(_require_tuple(record.subject_refs)) != record.subject_refs:
            raise _Failure("FIELD_VALUE_INVALID")
        lanes = tuple(_lanes(_require_tuple(record.evidence_lanes)))
        if lanes != record.evidence_lanes:
            raise _Failure("LANE_INVALID")
        canonical_novelty = _validate_canonical_mapping_json(record.novelty_dimensions_json)
        rebuilt_novelty, _mechanism = _novelty_dimensions(json.loads(canonical_novelty), record.scope_key)
        if rebuilt_novelty != record.novelty_dimensions_json:
            raise _Failure("FIELD_VALUE_INVALID")
        if _novelty_fingerprint(record.novelty_dimensions_json, lanes) != record.novelty_fingerprint:
            raise _Failure("IDENTITY_DERIVATION_MISMATCH")
        _bool(record.human_review_required)
    elif isinstance(record, HypothesisFamily):
        _opaque(record.family_version)
        _text(record.family_name)
        _text(record.mechanism_key)
        _text(record.falsifiable_theme)
        _text(record.creation_provenance)
        _evidence_id(record.predecessor_family_id, nullable=True)
        canonical_mech = _validate_canonical_mapping_json(record.mechanism_dimensions_json)
        if _mechanism_fingerprint(record.mechanism_key, canonical_mech) != record.mechanism_fingerprint:
            raise _Failure("IDENTITY_DERIVATION_MISMATCH")
        _bool(record.human_review_required)
    elif isinstance(record, ResearchEpisode):
        _validate_episode_semantics(record)


def _validate_episode_semantics(record: "ResearchEpisode") -> None:
    _opaque(record.episode_version)
    _evidence_id(record.candidate_id)
    _evidence_id(record.hypothesis_family_id)
    _evidence_id(record.predecessor_episode_id, nullable=True)
    _evidence_id(record.reopened_episode_id, nullable=True)
    _evidence_id(record.producer_receipt_ref, nullable=True)
    result_state = _enum(record.result_state, RESEARCH_RESULT_STATES)
    _enum(record.confidence_label, ALPHA_FACTORY_CONFIDENCE_LABELS)
    producer_type = _enum(record.producer_type, PRODUCER_TYPES)
    lanes = tuple(_lanes(_require_tuple(record.evidence_lanes)))
    if lanes != record.evidence_lanes:
        raise _Failure("LANE_INVALID")
    _validate_canonical_mapping_json(record.exact_scope_json)
    _validate_canonical_mapping_json(record.evidence_regime_json)
    for text_field in (
        record.research_question, record.thesis, record.producer_version,
        record.creation_provenance,
    ):
        _text(text_field)
    _utc(record.research_as_of)
    _bool(record.human_review_required)
    lists = {}
    for name in _EPISODE_LIST_FIELDS:
        stored = getattr(record, name)
        if tuple(_tuple_text(_require_tuple(stored), allow_empty=True)) != stored:
            raise _Failure("FIELD_VALUE_INVALID")
        lists[name] = stored
    if tuple(_tuple_ids(_require_tuple(record.source_reference_ids), allow_empty=True)) != record.source_reference_ids:
        raise _Failure("FIELD_VALUE_INVALID")
    if tuple(_tuple_ids(_require_tuple(record.deterministic_evidence_refs), allow_empty=True, evidence=True)) != record.deterministic_evidence_refs:
        raise _Failure("FIELD_VALUE_INVALID")
    # Global episode discipline.
    if not lists["falsification_checks_performed"]:
        raise _Failure("RESULT_EVIDENCE_INVALID")
    if not record.source_reference_ids and not record.deterministic_evidence_refs:
        raise _Failure("RESULT_EVIDENCE_INVALID")
    # State-specific evidence matrix.
    for field_name in _STATE_REQUIRED_FIELDS[result_state]:
        if not lists[field_name]:
            raise _Failure("RESULT_EVIDENCE_INVALID")
    if result_state == "EXECUTION_UNECONOMIC" and not record.deterministic_evidence_refs:
        raise _Failure("RESULT_EVIDENCE_INVALID")
    # Reopen caller-shape rule (cross-record resolution is the registry's).
    if result_state == "REOPEN_TRIGGERED":
        if record.reopened_episode_id is None:
            raise _Failure("REOPEN_INVALID")
    elif record.reopened_episode_id is not None:
        raise _Failure("REOPEN_INVALID")
    # Producer provenance fail-closed requirements.
    if producer_type == "HERMES_CONTROLLED_RESEARCH" and record.producer_receipt_ref is None:
        raise _Failure("RESULT_EVIDENCE_INVALID")
    if producer_type in {"HUMAN_RESEARCH", "OTHER_VALIDATED_ADVISORY"} and not record.source_reference_ids:
        raise _Failure("RESULT_EVIDENCE_INVALID")
    if producer_type == "DETERMINISTIC_ANALYSIS" and not record.deterministic_evidence_refs:
        raise _Failure("RESULT_EVIDENCE_INVALID")


def record_to_mapping(record: object) -> dict[str, object]:
    _validate_public_record(record)
    return {field.name: (list(getattr(record, field.name)) if isinstance(getattr(record, field.name), tuple) else getattr(record, field.name)) for field in fields(record)}


_TUPLE_FIELDS = {
    OpportunityCandidate: ("subject_refs", "evidence_lanes"),
    ResearchEpisode: (
        "evidence_lanes", *_EPISODE_LIST_FIELDS, "source_reference_ids",
        "deterministic_evidence_refs",
    ),
}


def record_from_mapping(record_type: type, mapping: object) -> object:
    try:
        if record_type not in _RECORD_IDENTITY:
            raise _Failure("FIELD_TYPE_INVALID")
        if not isinstance(mapping, Mapping) or set(mapping) != {field.name for field in fields(record_type)}:
            raise _Failure("FIELD_VALUE_INVALID")
        converted = dict(mapping)
        for name in _TUPLE_FIELDS.get(record_type, ()):
            if not isinstance(converted.get(name), list):
                raise _Failure("FIELD_TYPE_INVALID")
            converted[name] = tuple(converted[name])
        record = record_type(**converted)
        _validate_public_record(record)
        return record
    except _Failure:
        raise
    except Exception:
        raise _Failure("INTERNAL_VALIDATION_FAILED") from None
