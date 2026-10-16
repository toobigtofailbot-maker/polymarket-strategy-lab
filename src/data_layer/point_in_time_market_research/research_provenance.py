"""Shared research provenance, point-in-time (PIT) time, data-quality (DQ), and
replay contracts (S10-WALLET-01).

This module is the FIRST implementation of the accepted common R1-R4 provenance
contract (adoption items R1R4-006/007/008/009). It is deliberately ONE common
core rather than a competing manifest family. Wallet and other domains add a
one-way domain extension that references the immutable core; the core never
references any domain extension (non-circular by construction).

Posture: local, offline, stdlib-only, deterministic, content-addressed,
in-memory. No file, network, credential, scheduler, strategy, paper, order,
risk, or execution authority. This module records observability provenance only;
no provenance object implies wallet skill, profitability, qualification, or
execution authority.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
import re

from .records import canonical_json_bytes, sha256_hex


RESEARCH_PROVENANCE_LABEL = "SHARED_RESEARCH_PROVENANCE_PIT_DQ_REPLAY_CORE"
RESEARCH_PROVENANCE_POSTURE = "LOCAL_OFFLINE_STDLIB_ONLY_CONTENT_ADDRESSED"

RAW_EVIDENCE_REFERENCE_SCHEMA_ID = "research-raw-evidence-reference"
RAW_EVIDENCE_REFERENCE_SCHEMA_VERSION = "1.0.0"
RESEARCH_PROVENANCE_MANIFEST_SCHEMA_ID = "research-provenance-manifest-core"
RESEARCH_PROVENANCE_MANIFEST_SCHEMA_VERSION = "1.0.0"

RAW_EVIDENCE_REFERENCE_ID_PREFIX = "rawevidence:sha256:"
RESEARCH_PROVENANCE_MANIFEST_ID_PREFIX = "researchmanifest:sha256:"

# ---------------------------------------------------------------------------
# 9.1 Shared PIT time model.
# ---------------------------------------------------------------------------
PIT_TIME_FIELDS = (
    "event_time",
    "chain_block_time",
    "source_publish_time",
    "public_available_time",
    "local_first_seen_time",
    "ingestion_time",
    "confirmation_or_finality_time",
    "correction_or_revision_time",
    "resolution_time",
)

# ---------------------------------------------------------------------------
# 9.2 Shared data-quality vocabulary. Core project-level set plus the bounded
# wallet/domain extensions authorized for this WP. Canonical sorted/deduped.
# ---------------------------------------------------------------------------
DATA_QUALITY_CORE = (
    "OK",
    "MISSING",
    "STALE",
    "DELAYED",
    "CORRECTED",
    "BACKFILLED",
    "PARTIALLY_OBSERVED",
    "DUPLICATED",
    "SEQUENCE_GAP",
    "TIMESTAMP_UNCERTAIN",
    "SOURCE_UNAVAILABLE",
    "SCHEMA_DRIFT",
    "SOURCE_DISAGREEMENT",
)
DATA_QUALITY_WALLET_EXTENSIONS = (
    "REORGED",
    "UNFINALIZED",
    "IDENTITY_AMBIGUOUS",
    "COST_BASIS_INCOMPLETE",
    "BOOK_UNAVAILABLE",
)
DATA_QUALITY_FLAGS = tuple(
    sorted(set(DATA_QUALITY_CORE) | set(DATA_QUALITY_WALLET_EXTENSIONS))
)
_DATA_QUALITY_SET = frozenset(DATA_QUALITY_FLAGS)

# ---------------------------------------------------------------------------
# 9.3 Replay fidelity closed set.
# ---------------------------------------------------------------------------
REPLAY_FIDELITY_STATES = ("EXACT", "FAITHFUL", "PARTIAL", "UNREPLAYABLE")
_REPLAY_FIDELITY_SET = frozenset(REPLAY_FIDELITY_STATES)

# ---------------------------------------------------------------------------
# 9.6 Shared PIT replay admissibility contract.
# ---------------------------------------------------------------------------
REPLAY_ADMISSIBILITY_STATUSES = ("ADMISSIBLE", "NOT_ADMISSIBLE", "INDETERMINATE")
REPLAY_ADMISSIBILITY_BASES = (
    "LOCAL_FIRST_SEEN",
    "PUBLIC_AVAILABLE",
    "NOT_YET_SEEN",
    "CORRECTION_AFTER_CUTOFF",
    "TIMESTAMP_UNCERTAIN",
    "NO_OBSERVABILITY_EVIDENCE",
)

RESEARCH_PROVENANCE_ERROR_CODES = (
    "TIMESTAMP_FORMAT_INVALID",
    "TIMESTAMP_NOT_UTC",
    "TIMESTAMP_TYPE_INVALID",
    "PIT_FIELD_UNKNOWN",
    "DQ_FLAG_UNKNOWN",
    "DQ_OK_EXCLUSIVITY_VIOLATION",
    "DQ_EMPTY",
    "REPLAY_FIDELITY_UNSUPPORTED",
    "REPLAY_FIDELITY_EXACT_WITHOUT_RAW",
    "FIELD_TYPE_INVALID",
    "FIELD_VALUE_INVALID",
    "SHA256_FORMAT_INVALID",
    "BYTE_LENGTH_INVALID",
    "MANIFEST_CIRCULAR_REFERENCE",
    "IDENTITY_DERIVATION_MISMATCH",
)

_TIMESTAMP_RE = re.compile(
    r"^(?P<date>[0-9]{4}-[0-9]{2}-[0-9]{2})T"
    r"(?P<time>[0-9]{2}:[0-9]{2}:[0-9]{2})"
    r"(?P<fraction>\.[0-9]{1,9})?(?P<zone>Z|[+-][0-9]{2}:[0-9]{2})$"
)
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _error(code: str) -> ValueError:
    return ValueError(code)


# ---------------------------------------------------------------------------
# Timestamp canonicalization (explicit UTC, canonical Z, deterministic).
# ---------------------------------------------------------------------------
def canonicalize_utc_timestamp(value: object) -> str:
    """Return a canonical ``...Z`` UTC timestamp string or raise a stable error.

    Rejects naive timestamps, non-UTC offsets, and non-string input. A trailing
    ``+00:00`` normalizes to ``Z``. Fractional seconds are preserved but trailing
    zero fractions are dropped so equivalent spellings canonicalize identically.
    """

    if not isinstance(value, str):
        raise _error("TIMESTAMP_TYPE_INVALID")
    match = _TIMESTAMP_RE.match(value)
    if match is None:
        raise _error("TIMESTAMP_FORMAT_INVALID")
    # Validate real calendar/time values deterministically.
    normalized = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:  # pragma: no cover - regex already constrains shape
        raise _error("TIMESTAMP_FORMAT_INVALID") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(None):
        raise _error("TIMESTAMP_NOT_UTC")
    fraction = match.group("fraction") or ""
    if fraction:
        fraction = fraction.rstrip("0")
        if fraction == ".":
            fraction = ""
    return f"{match.group('date')}T{match.group('time')}{fraction}Z"


@dataclass(frozen=True)
class PitTimestamps:
    """The shared point-in-time timestamp vocabulary. Each field is nullable and
    UNKNOWN when not directly evidenced. No timestamp substitution is performed;
    event_time never implies public availability or local first-seen."""

    event_time: str | None = None
    chain_block_time: str | None = None
    source_publish_time: str | None = None
    public_available_time: str | None = None
    local_first_seen_time: str | None = None
    ingestion_time: str | None = None
    confirmation_or_finality_time: str | None = None
    correction_or_revision_time: str | None = None
    resolution_time: str | None = None

    def to_dict(self) -> dict[str, str | None]:
        return {field: getattr(self, field) for field in PIT_TIME_FIELDS}


def build_pit_timestamps(**values: object) -> PitTimestamps:
    """Validate and canonicalize an explicit PIT timestamp mapping.

    Only the frozen ``PIT_TIME_FIELDS`` names are accepted; unknown names reject.
    Each supplied non-null value is canonicalized to a UTC ``...Z`` string.
    """

    unknown = set(values) - set(PIT_TIME_FIELDS)
    if unknown:
        raise _error("PIT_FIELD_UNKNOWN")
    canonical: dict[str, str | None] = {}
    for field in PIT_TIME_FIELDS:
        raw = values.get(field)
        if raw is None:
            canonical[field] = None
        else:
            canonical[field] = canonicalize_utc_timestamp(raw)
    return PitTimestamps(**canonical)


# ---------------------------------------------------------------------------
# Data-quality helpers.
# ---------------------------------------------------------------------------
def canonicalize_dq_flags(flags: Sequence[str]) -> tuple[str, ...]:
    """Return a canonical sorted/deduped DQ tuple or raise a stable error.

    - every member must be a recognized DQ flag (unknown state rejects);
    - ``OK`` cannot coexist with any non-OK flag;
    - multiple simultaneous non-OK states are preserved;
    - absence of evidence is never silently coerced to ``OK`` here.
    """

    if isinstance(flags, str) or not isinstance(flags, Sequence):
        raise _error("FIELD_TYPE_INVALID")
    if len(flags) == 0:
        raise _error("DQ_EMPTY")
    seen: set[str] = set()
    for flag in flags:
        if not isinstance(flag, str):
            raise _error("FIELD_TYPE_INVALID")
        if flag not in _DATA_QUALITY_SET:
            raise _error("DQ_FLAG_UNKNOWN")
        seen.add(flag)
    if "OK" in seen and len(seen) > 1:
        raise _error("DQ_OK_EXCLUSIVITY_VIOLATION")
    return tuple(sorted(seen))


def validate_replay_fidelity(state: object) -> str:
    if not isinstance(state, str) or state not in _REPLAY_FIDELITY_SET:
        raise _error("REPLAY_FIDELITY_UNSUPPORTED")
    return state


def _validate_sha256(value: object) -> str:
    if not isinstance(value, str) or not _SHA256_RE.match(value):
        raise _error("SHA256_FORMAT_INVALID")
    return value


# ---------------------------------------------------------------------------
# 9.4 RawEvidenceReference (content-addressed; run-agnostic; no ingest_run_key).
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class RawEvidenceReference:
    """Immutable, content-addressed reference to one raw source observation.

    The identity is SHA-256 over the complete logical record excluding ONLY its
    own id. It carries no secret/header material, no arbitrary local path, and no
    ``ingest_run_key`` field: the same reference remains reusable by any research
    consumer without becoming run-specific.
    """

    raw_evidence_reference_id: str
    schema_id: str
    schema_version: str
    source_system: str
    endpoint: str
    retrieval_method: str
    request_parameters: tuple[tuple[str, str], ...]
    cursor_anchor: str | None
    pit: PitTimestamps
    content_sha256: str
    byte_length: int
    media_type: str
    api_version: str | None
    raw_snapshot_ref: str | None
    dq_flags: tuple[str, ...]
    replay_fidelity: str

    def logical_preimage(self) -> dict[str, object]:
        """Return the identity preimage (everything except the id itself)."""

        return {
            "schema_id": self.schema_id,
            "schema_version": self.schema_version,
            "source_system": self.source_system,
            "endpoint": self.endpoint,
            "retrieval_method": self.retrieval_method,
            "request_parameters": [list(pair) for pair in self.request_parameters],
            "cursor_anchor": self.cursor_anchor,
            "pit": self.pit.to_dict(),
            "content_sha256": self.content_sha256,
            "byte_length": self.byte_length,
            "media_type": self.media_type,
            "api_version": self.api_version,
            "raw_snapshot_ref": self.raw_snapshot_ref,
            "dq_flags": list(self.dq_flags),
            "replay_fidelity": self.replay_fidelity,
        }


def _canonical_request_parameters(
    request_parameters: object,
) -> tuple[tuple[str, str], ...]:
    if request_parameters is None:
        return ()
    if isinstance(request_parameters, Mapping):
        items = request_parameters.items()
    elif isinstance(request_parameters, Sequence) and not isinstance(
        request_parameters, str
    ):
        items = []
        for pair in request_parameters:
            if (
                not isinstance(pair, Sequence)
                or isinstance(pair, str)
                or len(pair) != 2
            ):
                raise _error("FIELD_TYPE_INVALID")
            items.append((pair[0], pair[1]))
    else:
        raise _error("FIELD_TYPE_INVALID")
    canonical: list[tuple[str, str]] = []
    for key, value in items:
        if not isinstance(key, str) or not isinstance(value, str):
            raise _error("FIELD_TYPE_INVALID")
        canonical.append((key, value))
    return tuple(sorted(canonical))


def build_raw_evidence_reference(
    *,
    source_system: str,
    endpoint: str,
    retrieval_method: str,
    content_sha256: str,
    byte_length: int,
    media_type: str,
    pit: PitTimestamps,
    dq_flags: Sequence[str],
    replay_fidelity: str,
    request_parameters: object = None,
    cursor_anchor: str | None = None,
    api_version: str | None = None,
    raw_snapshot_ref: str | None = None,
) -> RawEvidenceReference:
    """Construct a content-addressed :class:`RawEvidenceReference`.

    ``replay_fidelity == "EXACT"`` requires a durable ``raw_snapshot_ref`` so that
    hash-only evidence can never claim byte-identical EXACT replay.
    """

    for name, value in (
        ("source_system", source_system),
        ("endpoint", endpoint),
        ("retrieval_method", retrieval_method),
        ("media_type", media_type),
    ):
        if not isinstance(value, str) or not value:
            raise _error("FIELD_VALUE_INVALID")
    if not isinstance(pit, PitTimestamps):
        raise _error("FIELD_TYPE_INVALID")
    if not isinstance(byte_length, int) or isinstance(byte_length, bool) or byte_length < 0:
        raise _error("BYTE_LENGTH_INVALID")
    content_sha256 = _validate_sha256(content_sha256)
    fidelity = validate_replay_fidelity(replay_fidelity)
    canonical_flags = canonicalize_dq_flags(dq_flags)
    canonical_params = _canonical_request_parameters(request_parameters)
    for optional in (cursor_anchor, api_version, raw_snapshot_ref):
        if optional is not None and not isinstance(optional, str):
            raise _error("FIELD_TYPE_INVALID")
    if fidelity == "EXACT" and not raw_snapshot_ref:
        raise _error("REPLAY_FIDELITY_EXACT_WITHOUT_RAW")

    draft = RawEvidenceReference(
        raw_evidence_reference_id="",
        schema_id=RAW_EVIDENCE_REFERENCE_SCHEMA_ID,
        schema_version=RAW_EVIDENCE_REFERENCE_SCHEMA_VERSION,
        source_system=source_system,
        endpoint=endpoint,
        retrieval_method=retrieval_method,
        request_parameters=canonical_params,
        cursor_anchor=cursor_anchor,
        pit=pit,
        content_sha256=content_sha256,
        byte_length=byte_length,
        media_type=media_type,
        api_version=api_version,
        raw_snapshot_ref=raw_snapshot_ref,
        dq_flags=canonical_flags,
        replay_fidelity=fidelity,
    )
    identity = RAW_EVIDENCE_REFERENCE_ID_PREFIX + sha256_hex(
        canonical_json_bytes(draft.logical_preimage())
    )
    return _replace_id(draft, "raw_evidence_reference_id", identity)


def verify_raw_evidence_reference_identity(reference: RawEvidenceReference) -> bool:
    expected = RAW_EVIDENCE_REFERENCE_ID_PREFIX + sha256_hex(
        canonical_json_bytes(reference.logical_preimage())
    )
    return reference.raw_evidence_reference_id == expected


# ---------------------------------------------------------------------------
# 9.5 ResearchProvenanceManifest core (non-circular; no ingest_run_key).
# ---------------------------------------------------------------------------
# Frozen forbidden substrings: the core manifest must never contain a field or
# value that points BACK to a wallet/domain extension. Direction is one-way:
# WalletProvenanceExtension -> ResearchProvenanceManifest.
_MANIFEST_FORBIDDEN_KEY_SUBSTRINGS = (
    "wallet_provenance_extension",
    "wallet_extension",
    "domain_extension",
    "ingest_run_key",
)


@dataclass(frozen=True)
class ResearchProvenanceManifest:
    """The single common content-addressed provenance manifest core.

    Non-circularity is frozen: this record MUST NOT contain any wallet/domain
    extension id, hash, or back-reference, and MUST NOT carry ``ingest_run_key``.
    Its identity is computable without any extension existing.
    """

    research_provenance_manifest_id: str
    schema_id: str
    schema_version: str
    repo_code_identity: str
    information_cutoff: str
    input_evidence_reference_ids: tuple[str, ...]
    input_content_hashes: tuple[str, ...]
    dataset_refs: tuple[str, ...]
    request_source_version_refs: tuple[str, ...]
    dq_flags: tuple[str, ...]
    replay_fidelity: str
    gap_summary: str
    output_identity: str
    output_hash: str

    def logical_preimage(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "schema_version": self.schema_version,
            "repo_code_identity": self.repo_code_identity,
            "information_cutoff": self.information_cutoff,
            "input_evidence_reference_ids": list(self.input_evidence_reference_ids),
            "input_content_hashes": list(self.input_content_hashes),
            "dataset_refs": list(self.dataset_refs),
            "request_source_version_refs": list(self.request_source_version_refs),
            "dq_flags": list(self.dq_flags),
            "replay_fidelity": self.replay_fidelity,
            "gap_summary": self.gap_summary,
            "output_identity": self.output_identity,
            "output_hash": self.output_hash,
        }


def _assert_no_extension_backreference(preimage: Mapping[str, object]) -> None:
    for key in preimage:
        lowered = key.lower()
        for forbidden in _MANIFEST_FORBIDDEN_KEY_SUBSTRINGS:
            if forbidden in lowered:
                raise _error("MANIFEST_CIRCULAR_REFERENCE")


def _validate_str_tuple(value: object) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str) or not isinstance(value, Sequence):
        raise _error("FIELD_TYPE_INVALID")
    out: list[str] = []
    for item in value:
        if not isinstance(item, str):
            raise _error("FIELD_TYPE_INVALID")
        out.append(item)
    return tuple(out)


def build_research_provenance_manifest(
    *,
    repo_code_identity: str,
    information_cutoff: str,
    output_identity: str,
    output_hash: str,
    input_evidence_reference_ids: Sequence[str] = (),
    input_content_hashes: Sequence[str] = (),
    dataset_refs: Sequence[str] = (),
    request_source_version_refs: Sequence[str] = (),
    dq_flags: Sequence[str] = ("OK",),
    replay_fidelity: str = "FAITHFUL",
    gap_summary: str = "",
) -> ResearchProvenanceManifest:
    """Construct the immutable content-addressed manifest core.

    The identity is SHA-256 over the complete logical core excluding ONLY the
    manifest id. It deliberately holds no back-reference to any wallet/domain
    extension, so rebuilding an extension can never change this id.
    """

    for name, value in (
        ("repo_code_identity", repo_code_identity),
        ("output_identity", output_identity),
        ("output_hash", output_hash),
    ):
        if not isinstance(value, str) or not value:
            raise _error("FIELD_VALUE_INVALID")
    if not isinstance(gap_summary, str):
        raise _error("FIELD_TYPE_INVALID")
    information_cutoff = canonicalize_utc_timestamp(information_cutoff)
    draft = ResearchProvenanceManifest(
        research_provenance_manifest_id="",
        schema_id=RESEARCH_PROVENANCE_MANIFEST_SCHEMA_ID,
        schema_version=RESEARCH_PROVENANCE_MANIFEST_SCHEMA_VERSION,
        repo_code_identity=repo_code_identity,
        information_cutoff=information_cutoff,
        input_evidence_reference_ids=_validate_str_tuple(input_evidence_reference_ids),
        input_content_hashes=_validate_str_tuple(input_content_hashes),
        dataset_refs=_validate_str_tuple(dataset_refs),
        request_source_version_refs=_validate_str_tuple(request_source_version_refs),
        dq_flags=canonicalize_dq_flags(dq_flags),
        replay_fidelity=validate_replay_fidelity(replay_fidelity),
        gap_summary=gap_summary,
        output_identity=output_identity,
        output_hash=output_hash,
    )
    preimage = draft.logical_preimage()
    _assert_no_extension_backreference(preimage)
    identity = RESEARCH_PROVENANCE_MANIFEST_ID_PREFIX + sha256_hex(
        canonical_json_bytes(preimage)
    )
    return _replace_id(draft, "research_provenance_manifest_id", identity)


def verify_research_provenance_manifest_identity(
    manifest: ResearchProvenanceManifest,
) -> bool:
    preimage = manifest.logical_preimage()
    _assert_no_extension_backreference(preimage)
    expected = RESEARCH_PROVENANCE_MANIFEST_ID_PREFIX + sha256_hex(
        canonical_json_bytes(preimage)
    )
    return manifest.research_provenance_manifest_id == expected


# ---------------------------------------------------------------------------
# 9.6 Shared PIT replay admissibility.
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ObservabilityEvidence:
    """Explicit observability evidence for a replay-admissibility decision.

    ``event_time`` is informational only and NEVER an admissibility clock.
    """

    local_first_seen_time: str | None = None
    public_available_time: str | None = None
    event_time: str | None = None
    is_correction_after_cutoff: bool = False
    is_backfilled: bool = False
    source_unavailable: bool = False
    persisted: bool = True
    decisive_clock_uncertain: bool = False


@dataclass(frozen=True)
class ReplayAdmissibilityResult:
    status: str
    basis: str
    retained_dq_flags: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "basis": self.basis,
            "retained_dq_flags": list(self.retained_dq_flags),
        }


def _retained_dq_flags(evidence: ObservabilityEvidence) -> tuple[str, ...]:
    retained: set[str] = set()
    if evidence.is_backfilled:
        retained.add("BACKFILLED")
    if evidence.source_unavailable:
        retained.add("SOURCE_UNAVAILABLE")
    if evidence.is_correction_after_cutoff:
        retained.add("CORRECTED")
    if evidence.decisive_clock_uncertain:
        retained.add("TIMESTAMP_UNCERTAIN")
    return tuple(sorted(retained))


def _utc_instant_key(canonical_timestamp: str) -> tuple[str, int]:
    """Order validated canonical UTC strings without losing fractional precision."""
    whole_second, _, fraction = canonical_timestamp[:-1].partition(".")
    return whole_second, int(fraction.ljust(9, "0"))


def evaluate_replay_admissibility(
    cutoff: str,
    evidence: ObservabilityEvidence,
) -> ReplayAdmissibilityResult:
    """Deterministically decide whether ``evidence`` was observable at ``cutoff``.

    This is the single shared PIT admissibility contract. Consumers (wallet,
    Hermes, Alpha, QUAL) MUST use it rather than inventing local eligibility
    rules. ``event_time`` alone can never make evidence admissible.
    """

    cutoff = canonicalize_utc_timestamp(cutoff)
    if not isinstance(evidence, ObservabilityEvidence):
        raise _error("FIELD_TYPE_INVALID")
    local_first_seen = (
        canonicalize_utc_timestamp(evidence.local_first_seen_time)
        if evidence.local_first_seen_time is not None
        else None
    )
    public_available = (
        canonicalize_utc_timestamp(evidence.public_available_time)
        if evidence.public_available_time is not None
        else None
    )
    retained = _retained_dq_flags(evidence)
    cutoff_key = _utc_instant_key(cutoff)

    # Rule 5: a correction/revision first observed or published after cutoff is
    # not admissible at that cutoff. The prior immutable observation is evaluated
    # independently as its own evidence object.
    if evidence.is_correction_after_cutoff:
        return ReplayAdmissibilityResult(
            "NOT_ADMISSIBLE", "CORRECTION_AFTER_CUTOFF", retained
        )

    # Rule 8: if uncertainty affects the decisive observability clock, the result
    # is INDETERMINATE. Uncertainty only in event_time never reaches here.
    if evidence.decisive_clock_uncertain:
        return ReplayAdmissibilityResult(
            "INDETERMINATE", "TIMESTAMP_UNCERTAIN", retained
        )

    # Rule 2/3: exact local first-seen is the strongest observability clock.
    if local_first_seen is not None:
        if _utc_instant_key(local_first_seen) <= cutoff_key:
            return ReplayAdmissibilityResult(
                "ADMISSIBLE", "LOCAL_FIRST_SEEN", retained
            )
        return ReplayAdmissibilityResult("NOT_ADMISSIBLE", "NOT_YET_SEEN", retained)

    # Rule 4: fall back to an exact directly evidenced public-available time.
    if public_available is not None:
        if _utc_instant_key(public_available) <= cutoff_key:
            return ReplayAdmissibilityResult(
                "ADMISSIBLE", "PUBLIC_AVAILABLE", retained
            )
        return ReplayAdmissibilityResult("NOT_ADMISSIBLE", "NOT_YET_SEEN", retained)

    # Rule 7 (no first-seen/public) and default: no observability evidence.
    return ReplayAdmissibilityResult(
        "NOT_ADMISSIBLE", "NO_OBSERVABILITY_EVIDENCE", retained
    )


# Backwards-compatible alias for the shorter contract name used in the WP text.
def observable_at(cutoff: str, evidence: ObservabilityEvidence) -> ReplayAdmissibilityResult:
    return evaluate_replay_admissibility(cutoff, evidence)


# ---------------------------------------------------------------------------
# Internal helpers.
# ---------------------------------------------------------------------------
def _replace_id(record, field_name: str, identity: str):
    from dataclasses import replace

    return replace(record, **{field_name: identity})
