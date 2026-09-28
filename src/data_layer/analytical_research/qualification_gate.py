"""S10-GATE-QUAL-01 deterministic qualification packet acceptance gate.

One immutable, content-addressed ``QualificationGateReceipt`` records a
qualification-only decision over an existing S10-QUAL-01 ``QualificationCandidate``:

    existing immutable NON_WALLET QualificationCandidate
    + current verified AlphaFactoryRegistrySnapshot (append-only descendant)
    + exact candidate-bound AF1GateReceipt
    + exact candidate-bound ResearchProvenanceManifest set
        -> structural revalidation / exact external rebinding
        -> eight closed qualification-readiness dimensions
        -> QUAL_PASS / QUAL_FAIL / QUAL_INCONCLUSIVE

Structural control rejection is separate from the substantive decision: malformed,
tampered, unbound or authority-broadened inputs return ``QUALIFICATION_GATE_REJECTED``
with one closed error code and NO receipt; they are never relabelled QUAL_FAIL or
QUAL_INCONCLUSIVE.

QUAL_PASS means only: the exact candidate packet and the evidence bound by this
policy are sufficiently ready to BEGIN separately authorized candidate-specific WP170
work. It is not predictive edge, OOS success, executable edge, profitability, paper,
live or Gate-C authority, and it does not itself authorize WP170.

The gate binds existing authorities by content id and re-proves the supplied
in-memory objects with their existing canonical validators; it adds no registry,
file writer, clock, randomness, environment lookup, network, Hermes/provider,
wallet runtime, WP170 object or economics.
"""

from __future__ import annotations

from dataclasses import dataclass, fields
from decimal import Decimal
import hashlib
import json
import re
from typing import Mapping

from ..point_in_time_market_research.research_provenance import (
    RESEARCH_PROVENANCE_MANIFEST_SCHEMA_ID,
    RESEARCH_PROVENANCE_MANIFEST_SCHEMA_VERSION,
    ResearchProvenanceManifest,
    canonicalize_dq_flags,
    canonicalize_utc_timestamp,
    validate_replay_fidelity,
    verify_research_provenance_manifest_identity,
)
from . import alpha_factory_registry as _afr
from .alpha_factory import HypothesisFamily, OpportunityCandidate, ResearchEpisode
from .alpha_factory_gate import AF1_DIMENSIONS, AF1GateReceipt, validate_af1_record
from .experiment_os import EXPERIMENT_OS_SCHEMA_VERSION
from .qualification import QualificationCandidate, validate_qualification_candidate

QUALIFICATION_GATE_SCHEMA_VERSION = "1.0.0"
QUALIFICATION_GATE_RECEIPT_SCHEMA_ID = "polymarket-qualification-gate-receipt"
QUALIFICATION_GATE_POLICY_VERSION = "qualification-gate-policy/1.0.0"
_RECEIPT_ID_PREFIX = "qualificationgate:sha256:"

# ── Closed vocabularies ──────────────────────────────────────────────────────
QUALIFICATION_GATE_STATUSES = (
    "QUALIFICATION_GATE_VALID",
    "QUALIFICATION_GATE_REJECTED",
)
QUALIFICATION_GATE_DIMENSIONS = (
    "PACKET_INTEGRITY",
    "CURRENT_RESEARCH_LINEAGE",
    "PREDECESSOR_EVIDENCE",
    "PIT_PROVENANCE_READINESS",
    "SAMPLE_POWER_READINESS",
    "WP170_CROSSING_READINESS",
    "EXECUTION_EVIDENCE_READINESS",
    "AUTHORITY_CONTAINMENT",
)
QUALIFICATION_GATE_DIMENSION_STATUSES = ("PASS", "FAIL", "INCONCLUSIVE")
QUALIFICATION_GATE_DISPOSITIONS = ("QUAL_PASS", "QUAL_FAIL", "QUAL_INCONCLUSIVE")
QUALIFICATION_GATE_ERROR_CODES = (
    "SCHEMA_UNSUPPORTED",
    "FIELD_TYPE_INVALID",
    "FIELD_VALUE_INVALID",
    "IDENTITY_DERIVATION_MISMATCH",
    "CANDIDATE_INVALID",
    "ALPHA_REGISTRY_INVALID",
    "ALPHA_ANCESTRY_INVALID",
    "AF1_RECEIPT_INVALID",
    "AF1_BINDING_INVALID",
    "PROVENANCE_INVALID",
    "PROVENANCE_BINDING_INVALID",
    "AUTHORITY_INVARIANT_INVALID",
    "LIMIT_EXCEEDED",
    "INTERNAL_VALIDATION_FAILED",
)
_ERROR_SET = frozenset(QUALIFICATION_GATE_ERROR_CODES)

# Statuses each dimension can legitimately take in an emitted receipt. Structural
# failures of the PASS-only dimensions yield no receipt at all.
_ALLOWED_DIMENSION_STATUSES = {
    "PACKET_INTEGRITY": ("PASS",),
    "CURRENT_RESEARCH_LINEAGE": ("PASS", "FAIL"),
    "PREDECESSOR_EVIDENCE": ("PASS",),
    "PIT_PROVENANCE_READINESS": ("PASS", "INCONCLUSIVE"),
    "SAMPLE_POWER_READINESS": ("PASS", "INCONCLUSIVE"),
    "WP170_CROSSING_READINESS": ("PASS",),
    "EXECUTION_EVIDENCE_READINESS": ("PASS", "INCONCLUSIVE"),
    "AUTHORITY_CONTAINMENT": ("PASS",),
}

# Minimum execution-evidence foundation for qualification entry. SPREAD_DEPTH,
# LATENCY and PARTIAL_FILL are carried forward in the candidate for WP172.
_CRITICAL_EXECUTION_CLASSES = ("FEES", "RESOLUTION_RULES", "TICK_SIZE_MIN_ORDER")
_READY_REPLAY_FIDELITY = frozenset({"EXACT", "FAITHFUL"})
_FORMATION_SELECTION_OOS_ROLES = 3

# Upstream canonical id prefixes.
_CANDIDATE_ID_PREFIX = "qualificationcandidate:sha256:"
_ALPHA_REGISTRY_ENTRY_PREFIX = "alpharegistryentry:sha256:"
_ALPHA_CANDIDATE_PREFIX = "alphacandidate:sha256:"
_ALPHA_FAMILY_PREFIX = "alphafamily:sha256:"
_ALPHA_EPISODE_PREFIX = "alphaepisode:sha256:"
_AF1_GATE_PREFIX = "af1gate:sha256:"
_PROVENANCE_MANIFEST_PREFIX = "researchmanifest:sha256:"

# ── Conservative bounds ──────────────────────────────────────────────────────
_MAX_PROVENANCE_MANIFESTS = 256
_MAX_TEXT_CHARS = 4096
_MAX_INPUT_DEPTH = 8
_MAX_INPUT_NODES = 4096

_ID_RE = re.compile(r"^[A-Za-z0-9._:-]{1,512}$")
_SHA_SUFFIX_RE = re.compile(r"^[0-9a-f]{64}$")
_UTC_RE = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,6})?Z$"
)

_SNAPSHOT_AUTHORITY_FIELDS = (
    "advisory_only", "no_execution_authority", "no_strategy_authority",
    "no_qualification_authority",
)
_AF1_AUTHORITY_FIELDS = (
    "advisory_only", "human_review_required", "no_execution_authority",
    "no_strategy_authority", "no_qualification_authority",
)


# ── Records ──────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class QualificationGateReceipt:
    schema_id: str
    schema_version: str
    qualification_gate_receipt_id: str
    policy_version: str
    qualification_candidate_id: str
    candidate_version: str
    candidate_information_cutoff: str
    candidate_alpha_registry_head_entry_hash: str
    current_alpha_registry_head_entry_hash: str
    alpha_candidate_id: str
    hypothesis_family_id: str
    governing_research_episode_id: str
    af1_gate_receipt_id: str
    research_provenance_manifest_ids: tuple[str, ...]
    experiment_os_schema_version: str
    dimension_statuses: tuple[tuple[str, str], ...]
    overall_disposition: str
    wp170_entry_eligible: bool
    successor_authorization_required: bool
    no_strategy_authority: bool
    no_paper_authority: bool
    no_execution_authority: bool
    no_live_authority: bool
    no_gate_c_authority: bool


@dataclass(frozen=True)
class QualificationGateControlResult:
    is_valid: bool
    status: str
    error_codes: tuple[str, ...]
    receipt: QualificationGateReceipt | None
    no_strategy_authority: bool
    no_paper_authority: bool
    no_execution_authority: bool
    no_live_authority: bool
    no_gate_c_authority: bool


_RECEIPT_AUTHORITY_FIELDS = (
    "successor_authorization_required",
    "no_strategy_authority",
    "no_paper_authority",
    "no_execution_authority",
    "no_live_authority",
    "no_gate_c_authority",
)


# ── Failure/result plumbing ──────────────────────────────────────────────────
class _Failure(Exception):
    def __init__(self, code: str):
        self.code = code


def _rejected(code: str) -> QualificationGateControlResult:
    # Final public closure: an out-of-vocabulary code never reaches a public result.
    if code not in _ERROR_SET:
        code = "INTERNAL_VALIDATION_FAILED"
    return QualificationGateControlResult(
        False, "QUALIFICATION_GATE_REJECTED", (code,), None, True, True, True, True, True
    )


def _valid(receipt: QualificationGateReceipt) -> QualificationGateControlResult:
    return QualificationGateControlResult(
        True, "QUALIFICATION_GATE_VALID", (), receipt, True, True, True, True, True
    )


# ── Scalar validators ────────────────────────────────────────────────────────
def _text(value: object) -> str:
    if not isinstance(value, str):
        raise _Failure("FIELD_TYPE_INVALID")
    if not value or value != value.strip() or len(value) > _MAX_TEXT_CHARS or "\x00" in value:
        raise _Failure("FIELD_VALUE_INVALID")
    return value


def _opaque(value: object) -> str:
    text = _text(value)
    if _ID_RE.fullmatch(text) is None:
        raise _Failure("FIELD_VALUE_INVALID")
    return text


def _prefixed(value: object, prefix: str) -> str:
    text = _opaque(value)
    if not text.startswith(prefix) or _SHA_SUFFIX_RE.fullmatch(text[len(prefix):]) is None:
        raise _Failure("FIELD_VALUE_INVALID")
    return text


def _utc(value: object) -> str:
    """Canonical UTC ``...Z`` timestamp (<= 6 fraction digits, no trailing zeros)."""
    if not isinstance(value, str):
        raise _Failure("FIELD_TYPE_INVALID")
    if _UTC_RE.fullmatch(value) is None:
        raise _Failure("FIELD_VALUE_INVALID")
    try:
        canonical = canonicalize_utc_timestamp(value)
    except ValueError:
        raise _Failure("FIELD_VALUE_INVALID") from None
    if canonical != value:
        raise _Failure("FIELD_VALUE_INVALID")
    return value


def _utc_key(value: str) -> tuple[str, Decimal]:
    """Order key for a canonical ``YYYY-MM-DDTHH:MM:SS[.f]Z`` timestamp."""
    fraction = value[19:-1]
    return value[:19], Decimal("0" + fraction) if fraction else Decimal(0)


def _not_after(value: object, cutoff: str, code: str) -> bool:
    try:
        if not isinstance(value, str) or canonicalize_utc_timestamp(value) != value:
            raise ValueError("non-canonical timestamp")
    except ValueError:
        raise _Failure(code) from None
    return _utc_key(value) <= _utc_key(cutoff)


def _scan_input(value: object, depth: int, counter: list[int]) -> None:
    """Reject binary floats and non-JSON values recursively, with bounded size."""
    if depth > _MAX_INPUT_DEPTH:
        raise _Failure("LIMIT_EXCEEDED")
    counter[0] += 1
    if counter[0] > _MAX_INPUT_NODES:
        raise _Failure("LIMIT_EXCEEDED")
    if value is None or isinstance(value, (bool, str, int)):
        return
    if isinstance(value, Mapping):
        for key in value:
            if not isinstance(key, str):
                raise _Failure("FIELD_TYPE_INVALID")
            _scan_input(value[key], depth + 1, counter)
        return
    if isinstance(value, (list, tuple)):
        for item in value:
            _scan_input(item, depth + 1, counter)
        return
    # float (incl. NaN/Infinity), Decimal, bytes, set and any other object.
    raise _Failure("FIELD_TYPE_INVALID")


def _canonical_bytes(value: object) -> bytes:
    try:
        return json.dumps(
            value, ensure_ascii=False, separators=(",", ":"), sort_keys=True, allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeError):
        raise _Failure("FIELD_VALUE_INVALID") from None


# ── Receipt identity / aggregation ───────────────────────────────────────────
def _aggregate(statuses: tuple[tuple[str, str], ...]) -> str:
    values = [status for _name, status in statuses]
    if "FAIL" in values:
        return "QUAL_FAIL"
    if "INCONCLUSIVE" in values:
        return "QUAL_INCONCLUSIVE"
    return "QUAL_PASS"


def _preimage(receipt: QualificationGateReceipt) -> dict[str, object]:
    preimage: dict[str, object] = {}
    for field in fields(receipt):
        if field.name == "qualification_gate_receipt_id":
            continue
        raw = getattr(receipt, field.name)
        if field.name == "dimension_statuses":
            preimage[field.name] = [[name, status] for name, status in raw]
        else:
            preimage[field.name] = list(raw) if isinstance(raw, tuple) else raw
    return preimage


def _digest(preimage: Mapping[str, object]) -> str:
    wrapped = {"qualification_gate_receipt.identity_preimage": preimage}
    return _RECEIPT_ID_PREFIX + hashlib.sha256(_canonical_bytes(wrapped)).hexdigest()


def _dimension_statuses(value: object) -> tuple[tuple[str, str], ...]:
    if not isinstance(value, tuple):
        raise _Failure("FIELD_TYPE_INVALID")
    if len(value) != len(QUALIFICATION_GATE_DIMENSIONS):
        raise _Failure("FIELD_VALUE_INVALID")
    for expected, pair in zip(QUALIFICATION_GATE_DIMENSIONS, value):
        if not isinstance(pair, tuple) or len(pair) != 2:
            raise _Failure("FIELD_TYPE_INVALID")
        name, status = pair
        if not isinstance(name, str) or not isinstance(status, str):
            raise _Failure("FIELD_TYPE_INVALID")
        if name != expected or status not in _ALLOWED_DIMENSION_STATUSES[name]:
            raise _Failure("FIELD_VALUE_INVALID")
    return value


def _validate_receipt(receipt: object) -> QualificationGateReceipt:
    """Re-prove a receipt's own closed schema, aggregation and identity.

    This never re-binds the external candidate / Alpha / AF1 / provenance evidence:
    only ``evaluate_qualification_gate`` performs current external rebinding.
    """
    if type(receipt) is not QualificationGateReceipt:
        raise _Failure("FIELD_TYPE_INVALID")
    if (
        receipt.schema_id != QUALIFICATION_GATE_RECEIPT_SCHEMA_ID
        or receipt.schema_version != QUALIFICATION_GATE_SCHEMA_VERSION
        or receipt.policy_version != QUALIFICATION_GATE_POLICY_VERSION
        or receipt.experiment_os_schema_version != EXPERIMENT_OS_SCHEMA_VERSION
    ):
        raise _Failure("SCHEMA_UNSUPPORTED")
    for name in _RECEIPT_AUTHORITY_FIELDS:
        if getattr(receipt, name) is not True:
            raise _Failure("AUTHORITY_INVARIANT_INVALID")
    _prefixed(receipt.qualification_gate_receipt_id, _RECEIPT_ID_PREFIX)
    _prefixed(receipt.qualification_candidate_id, _CANDIDATE_ID_PREFIX)
    _opaque(receipt.candidate_version)
    _utc(receipt.candidate_information_cutoff)
    _prefixed(receipt.candidate_alpha_registry_head_entry_hash, _ALPHA_REGISTRY_ENTRY_PREFIX)
    _prefixed(receipt.current_alpha_registry_head_entry_hash, _ALPHA_REGISTRY_ENTRY_PREFIX)
    _prefixed(receipt.alpha_candidate_id, _ALPHA_CANDIDATE_PREFIX)
    _prefixed(receipt.hypothesis_family_id, _ALPHA_FAMILY_PREFIX)
    _prefixed(receipt.governing_research_episode_id, _ALPHA_EPISODE_PREFIX)
    _prefixed(receipt.af1_gate_receipt_id, _AF1_GATE_PREFIX)
    manifest_ids = receipt.research_provenance_manifest_ids
    if not isinstance(manifest_ids, tuple):
        raise _Failure("FIELD_TYPE_INVALID")
    if len(manifest_ids) > _MAX_PROVENANCE_MANIFESTS:
        raise _Failure("LIMIT_EXCEEDED")
    if not manifest_ids:
        raise _Failure("FIELD_VALUE_INVALID")
    for manifest_id in manifest_ids:
        _prefixed(manifest_id, _PROVENANCE_MANIFEST_PREFIX)
    if list(manifest_ids) != sorted(set(manifest_ids)):
        raise _Failure("FIELD_VALUE_INVALID")
    statuses = _dimension_statuses(receipt.dimension_statuses)
    if not isinstance(receipt.overall_disposition, str):
        raise _Failure("FIELD_TYPE_INVALID")
    if receipt.overall_disposition != _aggregate(statuses):
        raise _Failure("FIELD_VALUE_INVALID")
    if not isinstance(receipt.wp170_entry_eligible, bool):
        raise _Failure("FIELD_TYPE_INVALID")
    if receipt.wp170_entry_eligible is not (receipt.overall_disposition == "QUAL_PASS"):
        raise _Failure("FIELD_VALUE_INVALID")
    if _digest(_preimage(receipt)) != receipt.qualification_gate_receipt_id:
        raise _Failure("IDENTITY_DERIVATION_MISMATCH")
    return receipt


# ── Structural admission: candidate ──────────────────────────────────────────
def _admit_candidate(candidate: object) -> QualificationCandidate:
    # The existing S10-QUAL-01 record-semantic validator is the packet oracle.
    result = validate_qualification_candidate(candidate)
    if not result.is_valid or type(result.record) is not QualificationCandidate:
        code = result.error_codes[0] if result.error_codes else ""
        raise _Failure(
            "AUTHORITY_INVARIANT_INVALID" if code == "AUTHORITY_INVARIANT_INVALID"
            else "CANDIDATE_INVALID"
        )
    record = result.record
    if record.experiment_os_schema_version != EXPERIMENT_OS_SCHEMA_VERSION:
        raise _Failure("CANDIDATE_INVALID")
    return record


# ── Structural admission: Alpha snapshot, ancestry, current lineage ──────────
def _verified_entries(snapshot: object) -> tuple[_afr.AlphaFactoryRegistryEntry, ...]:
    """Re-prove the caller-supplied snapshot against the registry's own hash chain.

    Every entry payload digest and entry hash is re-derived with the Alpha registry's
    own serialization and chain derivation, and the registry's cross-record
    invariants are re-run, so a fabricated snapshot object cannot bypass the gate.
    """
    if type(snapshot) is not _afr.AlphaFactoryRegistrySnapshot:
        raise _Failure("ALPHA_REGISTRY_INVALID")
    for flag in _SNAPSHOT_AUTHORITY_FIELDS:
        if getattr(snapshot, flag) is not True:
            raise _Failure("AUTHORITY_INVARIANT_INVALID")
    if (
        snapshot.schema_id != _afr._SNAPSHOT_SCHEMA_ID
        or snapshot.schema_version != _afr._SNAPSHOT_SCHEMA_VERSION
    ):
        raise _Failure("ALPHA_REGISTRY_INVALID")
    entries = snapshot.entries
    if not isinstance(entries, tuple) or not entries:
        raise _Failure("ALPHA_REGISTRY_INVALID")
    if len(entries) > _afr.MAX_ALPHA_REGISTRY_RECORDS:
        raise _Failure("LIMIT_EXCEEDED")
    if type(snapshot.total_rows) is not int or snapshot.total_rows != len(entries):
        raise _Failure("ALPHA_REGISTRY_INVALID")
    previous: str | None = None
    total_bytes = 0
    record_ids: set[str] = set()
    try:
        for sequence, entry in enumerate(entries):
            if type(entry) is not _afr.AlphaFactoryRegistryEntry:
                raise _Failure("ALPHA_REGISTRY_INVALID")
            if entry.sequence_number != sequence or entry.previous_entry_hash != previous:
                raise _Failure("ALPHA_REGISTRY_INVALID")
            kind, record_id, payload, payload_sha = _afr._serialize(entry.record)
            if (
                kind != entry.record_kind or record_id != entry.record_id
                or payload_sha != entry.payload_sha256 or record_id in record_ids
            ):
                raise _Failure("ALPHA_REGISTRY_INVALID")
            expected_hash = _afr._entry_hash(sequence, kind, record_id, payload_sha, previous)
            if entry.entry_hash != expected_hash:
                raise _Failure("ALPHA_REGISTRY_INVALID")
            record_ids.add(record_id)
            total_bytes += len(payload.encode("utf-8"))
            previous = expected_hash
        if snapshot.head_entry_hash != previous or snapshot.total_payload_bytes != total_bytes:
            raise _Failure("ALPHA_REGISTRY_INVALID")
        _afr._verify_cross_record_invariants(snapshot)
    except _Failure:
        raise
    except Exception:
        raise _Failure("ALPHA_REGISTRY_INVALID") from None
    return entries


def _admit_ancestry(
    entries: tuple[_afr.AlphaFactoryRegistryEntry, ...], candidate: QualificationCandidate
) -> None:
    """The candidate-bound head must be an ancestor of, or equal to, the current head.

    Equality with the current head is NOT required: the Alpha registry is
    append-only, so unrelated later records never invalidate an older packet.
    """
    bound = candidate.alpha_registry_head_entry_hash
    positions = [index for index, entry in enumerate(entries) if entry.entry_hash == bound]
    if len(positions) != 1:
        raise _Failure("ALPHA_ANCESTRY_INVALID")
    history = {entry.record_id: entry.record for entry in entries[: positions[0] + 1]}
    alpha_candidate = history.get(candidate.alpha_candidate_id)
    family = history.get(candidate.hypothesis_family_id)
    episode = history.get(candidate.governing_research_episode_id)
    if (
        type(alpha_candidate) is not OpportunityCandidate
        or type(family) is not HypothesisFamily
        or type(episode) is not ResearchEpisode
        or episode.candidate_id != candidate.alpha_candidate_id
        or episode.hypothesis_family_id != candidate.hypothesis_family_id
    ):
        raise _Failure("ALPHA_ANCESTRY_INVALID")
    if not _not_after(
        episode.research_as_of, candidate.information_cutoff, "ALPHA_ANCESTRY_INVALID"
    ):
        raise _Failure("ALPHA_ANCESTRY_INVALID")


def _current_lineage_status(
    entries: tuple[_afr.AlphaFactoryRegistryEntry, ...], candidate: QualificationCandidate
) -> str:
    """PASS iff the exact lineage still has ONE current leaf: the governing supportive
    episode. Any later same-lineage episode, ambiguity or non-supportive leaf is FAIL
    (the packet no longer meets the current-lineage criterion; it is not relabelled
    as a falsified hypothesis)."""
    lineage = [
        entry.record for entry in entries
        if type(entry.record) is ResearchEpisode
        and entry.record.candidate_id == candidate.alpha_candidate_id
        and entry.record.hypothesis_family_id == candidate.hypothesis_family_id
    ]
    # Current Alpha convention: an episode is non-leaf when a later episode names it
    # as predecessor or reopened episode (registry invariants keep these in-lineage).
    parents = {
        ref for episode in lineage
        for ref in (episode.predecessor_episode_id, episode.reopened_episode_id)
        if ref is not None
    }
    leaves = [episode for episode in lineage if episode.research_episode_id not in parents]
    if (
        len(leaves) == 1
        and leaves[0].research_episode_id == candidate.governing_research_episode_id
        and leaves[0].result_state == "RESEARCH_SUPPORTIVE"
    ):
        return "PASS"
    return "FAIL"


# ── Structural admission: AF1 predecessor ────────────────────────────────────
def _admit_af1(receipt: object, candidate: QualificationCandidate) -> str:
    if type(receipt) is not AF1GateReceipt:
        raise _Failure("AF1_RECEIPT_INVALID")
    for flag in _AF1_AUTHORITY_FIELDS:
        if getattr(receipt, flag) is not True:
            raise _Failure("AUTHORITY_INVARIANT_INVALID")
    try:
        validate_af1_record(receipt)
    except Exception:
        raise _Failure("AF1_RECEIPT_INVALID") from None
    statuses = receipt.dimension_statuses
    names = [name for name, _status in statuses]
    if len(names) != len(AF1_DIMENSIONS) or set(names) != set(AF1_DIMENSIONS):
        raise _Failure("AF1_RECEIPT_INVALID")
    if (
        receipt.evidence_state != "FINALIZED"
        or receipt.overall_disposition != "AF1_PASS"
        or any(status != "PASS" for _name, status in statuses)
    ):
        raise _Failure("AF1_RECEIPT_INVALID")
    if receipt.gate_receipt_id != candidate.af1_gate_receipt_id:
        raise _Failure("AF1_BINDING_INVALID")
    return receipt.gate_receipt_id


# ── Structural admission: provenance binding ─────────────────────────────────
def _string_tuple(value: object) -> tuple[str, ...]:
    if not isinstance(value, tuple) or any(not isinstance(item, str) for item in value):
        raise _Failure("PROVENANCE_INVALID")
    return value


def _admit_provenance(
    manifests: object, candidate: QualificationCandidate, split_plan: Mapping[str, object]
) -> list[ResearchProvenanceManifest]:
    if isinstance(manifests, (str, bytes)) or not isinstance(manifests, (list, tuple)):
        raise _Failure("PROVENANCE_INVALID")
    if not manifests:
        raise _Failure("PROVENANCE_INVALID")
    if len(manifests) > _MAX_PROVENANCE_MANIFESTS:
        raise _Failure("LIMIT_EXCEEDED")
    admitted: list[ResearchProvenanceManifest] = []
    for manifest in manifests:
        if type(manifest) is not ResearchProvenanceManifest:
            raise _Failure("PROVENANCE_INVALID")
        try:
            if (
                not verify_research_provenance_manifest_identity(manifest)
                or manifest.schema_id != RESEARCH_PROVENANCE_MANIFEST_SCHEMA_ID
                or manifest.schema_version != RESEARCH_PROVENANCE_MANIFEST_SCHEMA_VERSION
                or canonicalize_utc_timestamp(manifest.information_cutoff)
                != manifest.information_cutoff
                or canonicalize_dq_flags(manifest.dq_flags) != manifest.dq_flags
                or validate_replay_fidelity(manifest.replay_fidelity) != manifest.replay_fidelity
                or not isinstance(manifest.gap_summary, str)
            ):
                raise _Failure("PROVENANCE_INVALID")
            _prefixed(manifest.research_provenance_manifest_id, _PROVENANCE_MANIFEST_PREFIX)
            _string_tuple(manifest.input_evidence_reference_ids)
            _string_tuple(manifest.dataset_refs)
        except Exception:
            raise _Failure("PROVENANCE_INVALID") from None
        admitted.append(manifest)
    supplied = [manifest.research_provenance_manifest_id for manifest in admitted]
    if len(set(supplied)) != len(supplied):
        raise _Failure("PROVENANCE_BINDING_INVALID")
    if tuple(sorted(supplied)) != candidate.research_provenance_manifest_ids:
        raise _Failure("PROVENANCE_BINDING_INVALID")
    cutoff = candidate.information_cutoff
    if any(not _not_after(m.information_cutoff, cutoff, "PROVENANCE_INVALID") for m in admitted):
        raise _Failure("PROVENANCE_BINDING_INVALID")
    covered = {ref for manifest in admitted for ref in manifest.dataset_refs}
    split_refs = split_plan["dataset_snapshot_reference_ids"]
    if not isinstance(split_refs, list) or any(ref not in covered for ref in split_refs):
        raise _Failure("PROVENANCE_BINDING_INVALID")
    return admitted


# ── Readiness dimensions (after full structural admission) ───────────────────
def _plans(candidate: QualificationCandidate) -> dict[str, dict[str, object]]:
    # The candidate already passed full S10-QUAL-01 validation, so every plan is
    # canonical float-free JSON; decoding never rewrites plan semantics.
    names = ("feature_plan", "label_plan", "dataset_split_plan", "sample_power_plan",
             "execution_feasibility_plan")
    plans: dict[str, dict[str, object]] = {}
    for name in names:
        decoded = json.loads(getattr(candidate, f"{name}_json"))
        if not isinstance(decoded, dict):
            raise _Failure("CANDIDATE_INVALID")
        plans[name] = decoded
    return plans


def _declared_evidence_refs(plans: Mapping[str, Mapping[str, object]]) -> set[str]:
    declared: set[str] = set()
    feature_refs = plans["feature_plan"]["feature_evidence_refs"]
    assert isinstance(feature_refs, Mapping)
    for refs in feature_refs.values():
        declared.update(refs)
    declared.update(plans["label_plan"]["evidence_reference_ids"])
    declared.add(plans["sample_power_plan"]["power_analysis_reference_id"])
    for entry in plans["execution_feasibility_plan"].values():
        assert isinstance(entry, Mapping)
        declared.update(entry["evidence_reference_ids"])
    return declared


def _pit_provenance_status(
    manifests: list[ResearchProvenanceManifest], declared: set[str], bound: set[str]
) -> str:
    if not declared <= bound:
        return "INCONCLUSIVE"
    for manifest in manifests:
        if (
            manifest.dq_flags != ("OK",)
            or manifest.replay_fidelity not in _READY_REPLAY_FIDELITY
            or manifest.gap_summary != ""
        ):
            return "INCONCLUSIVE"
    return "PASS"


def _sample_power_status(power: Mapping[str, object], split: Mapping[str, object]) -> str:
    """Declared-count sufficiency only; no universal power calculation.

    The three-role check is a necessary aggregate feasibility condition for the
    future formation / selection / OOS roles; no role membership is materialized.
    """
    available = power["available_sample_count"]
    groups = power["available_independent_group_count"]
    required = power["required_sample_count"]
    required_groups = power["required_independent_group_count"]
    per_role = split["min_samples_per_role"]
    for value in (available, groups, required, required_groups, per_role):
        if type(value) is not int:
            raise _Failure("CANDIDATE_INVALID")
    if (
        available >= required
        and groups >= required_groups
        and available >= _FORMATION_SELECTION_OOS_ROLES * per_role
    ):
        return "PASS"
    return "INCONCLUSIVE"


def _execution_evidence_status(feasibility: Mapping[str, object], bound: set[str]) -> str:
    for name in _CRITICAL_EXECUTION_CLASSES:
        entry = feasibility[name]
        assert isinstance(entry, Mapping)
        refs = entry["evidence_reference_ids"]
        if entry["state"] != "AVAILABLE" or not refs or any(ref not in bound for ref in refs):
            return "INCONCLUSIVE"
    return "PASS"


def _evaluate(
    candidate: object, alpha_registry_snapshot: object, af1_gate_receipt: object,
    provenance_manifests: object,
) -> QualificationGateReceipt:
    record = _admit_candidate(candidate)
    entries = _verified_entries(alpha_registry_snapshot)
    _admit_ancestry(entries, record)
    af1_id = _admit_af1(af1_gate_receipt, record)
    plans = _plans(record)
    manifests = _admit_provenance(provenance_manifests, record, plans["dataset_split_plan"])

    bound = {ref for manifest in manifests for ref in manifest.input_evidence_reference_ids}
    statuses = (
        ("PACKET_INTEGRITY", "PASS"),
        ("CURRENT_RESEARCH_LINEAGE", _current_lineage_status(entries, record)),
        ("PREDECESSOR_EVIDENCE", "PASS"),
        ("PIT_PROVENANCE_READINESS",
         _pit_provenance_status(manifests, _declared_evidence_refs(plans), bound)),
        ("SAMPLE_POWER_READINESS",
         _sample_power_status(plans["sample_power_plan"], plans["dataset_split_plan"])),
        # Crossing readiness for candidate-specific WP170 successor work only; this
        # does not claim current WP170 feature definitions can encode B1 inputs.
        ("WP170_CROSSING_READINESS", "PASS"),
        ("EXECUTION_EVIDENCE_READINESS",
         _execution_evidence_status(plans["execution_feasibility_plan"], bound)),
        ("AUTHORITY_CONTAINMENT", "PASS"),
    )
    disposition = _aggregate(statuses)
    draft = QualificationGateReceipt(
        QUALIFICATION_GATE_RECEIPT_SCHEMA_ID, QUALIFICATION_GATE_SCHEMA_VERSION, "",
        QUALIFICATION_GATE_POLICY_VERSION, record.qualification_candidate_id,
        record.candidate_version, record.information_cutoff,
        record.alpha_registry_head_entry_hash, entries[-1].entry_hash,
        record.alpha_candidate_id, record.hypothesis_family_id,
        record.governing_research_episode_id, af1_id,
        record.research_provenance_manifest_ids, record.experiment_os_schema_version,
        statuses, disposition, disposition == "QUAL_PASS",
        True, True, True, True, True, True,
    )
    values = {field.name: getattr(draft, field.name) for field in fields(draft)}
    values["qualification_gate_receipt_id"] = _digest(_preimage(draft))
    try:
        return _validate_receipt(QualificationGateReceipt(**values))
    except _Failure:
        raise _Failure("INTERNAL_VALIDATION_FAILED") from None


# ── Public API ───────────────────────────────────────────────────────────────
def evaluate_qualification_gate(
    candidate: object,
    alpha_registry_snapshot: object,
    af1_gate_receipt: object,
    provenance_manifests: object,
) -> QualificationGateControlResult:
    """Deterministically evaluate one existing candidate under the frozen gate policy.

    No path argument, store write, clock, random seed, environment or network.
    Structural failure returns a closed rejection with no receipt; only a fully
    admitted evaluation emits QUAL_PASS / QUAL_FAIL / QUAL_INCONCLUSIVE.
    """
    try:
        return _valid(
            _evaluate(candidate, alpha_registry_snapshot, af1_gate_receipt, provenance_manifests)
        )
    except _Failure as failure:
        return _rejected(failure.code)
    except Exception:
        return _rejected("INTERNAL_VALIDATION_FAILED")


def validate_qualification_gate_receipt(receipt: object) -> QualificationGateControlResult:
    """Prove only the receipt's own closed schema, aggregation and identity."""
    try:
        return _valid(_validate_receipt(receipt))
    except _Failure as failure:
        return _rejected(failure.code)
    except Exception:
        return _rejected("INTERNAL_VALIDATION_FAILED")


def qualification_gate_receipt_to_mapping(receipt: object) -> dict[str, object]:
    """Validate, then return the exact field mapping.

    ``research_provenance_manifest_ids`` is a list and ``dimension_statuses`` an
    ordered ``{dimension: status}`` mapping. Raises ``ValueError`` whose only argument
    is one closed error code.
    """
    try:
        valid = _validate_receipt(receipt)
    except _Failure as failure:
        raise ValueError(failure.code) from None
    except Exception:
        raise ValueError("INTERNAL_VALIDATION_FAILED") from None
    mapping: dict[str, object] = {}
    for field in fields(valid):
        value = getattr(valid, field.name)
        if field.name == "dimension_statuses":
            mapping[field.name] = {name: status for name, status in value}
        elif isinstance(value, tuple):
            mapping[field.name] = list(value)
        else:
            mapping[field.name] = value
    return mapping


_RECEIPT_FIELDS = frozenset(field.name for field in fields(QualificationGateReceipt))


def qualification_gate_receipt_from_mapping(mapping: object) -> QualificationGateControlResult:
    """Reconstruct from an exact-keyset mapping and fully re-validate it."""
    try:
        if not isinstance(mapping, Mapping):
            raise _Failure("FIELD_TYPE_INVALID")
        if any(not isinstance(key, str) for key in mapping) or set(mapping) != _RECEIPT_FIELDS:
            raise _Failure("FIELD_VALUE_INVALID")
        _scan_input(mapping, 0, [0])
        converted = dict(mapping)
        ids = converted["research_provenance_manifest_ids"]
        if not isinstance(ids, list):
            raise _Failure("FIELD_TYPE_INVALID")
        converted["research_provenance_manifest_ids"] = tuple(ids)
        dimensions = converted["dimension_statuses"]
        if not isinstance(dimensions, Mapping):
            raise _Failure("FIELD_TYPE_INVALID")
        if set(dimensions) != set(QUALIFICATION_GATE_DIMENSIONS):
            raise _Failure("FIELD_VALUE_INVALID")
        # Canonical dimension order: caller mapping order never alters identity.
        converted["dimension_statuses"] = tuple(
            (name, dimensions[name]) for name in QUALIFICATION_GATE_DIMENSIONS
        )
        return _valid(_validate_receipt(QualificationGateReceipt(**converted)))
    except _Failure as failure:
        return _rejected(failure.code)
    except Exception:
        return _rejected("INTERNAL_VALIDATION_FAILED")
