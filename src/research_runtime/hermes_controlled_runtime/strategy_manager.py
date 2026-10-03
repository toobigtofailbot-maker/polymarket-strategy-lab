"""Hermes strategy manager core: V2.1 canonical soft strategy judgment (S10-HERMES-STRAT-01).

One foreground, caller-invoked function turns

  verified STRAT-LIFE snapshot + one exact StrategyVersion + bounded admissible evidence
  -> exactly one existing controlled Hermes run in default-off strategy mode
  -> deterministic repository validation of the untrusted strategy-mode draft
  -> canonical append-only soft strategy decision history

The raw Hermes output stays untrusted (every raw draft authority flag is still required to
be true); only this separately authorized module converts a strictly validated draft into
a canonical :class:`HermesStrategyAssessment`. That assessment is a soft strategy
decision, never a hard authorization: it allocates no budget, changes no
PortfolioAuthorityPolicy, claims no execution feasibility or Gate-C permission and creates
no exposure. This module never writes or opens the STRAT-LIFE store (it consumes an
already verified :class:`StrategyLifecycleSnapshot`), creates no child StrategyVersion,
holds no credential, signs nothing, places/cancels no order, runs no paper/live path and
has no scheduler, daemon, polling loop or automatic retry.

History lives in one explicit caller-selected append-only, hash-chained SQLite store
(application id 0x48534D31). Errors are closed codes that never echo model output,
rejected prompt/context, paths, secrets or raw exception text.
"""

from __future__ import annotations

import dataclasses
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
from typing import Callable, Mapping, Sequence

from src.data_layer.point_in_time_market_research.research_provenance import (
    canonicalize_utc_timestamp,
)
from src.strategy_lifecycle import (
    HEALTH_STATES,
    RISK_BANDS,
    StrategyLifecycleError,
    StrategyLifecycleSnapshot,
    StrategyVersion,
    canonical_json_bytes as _lc_canonical_bytes,
    canonical_json_text as _lc_canonical_text,
)
from src.strategy_lifecycle.models import (
    opaque_ref as _lc_opaque_ref,
    parse_strategy_spec as _lc_parse_strategy_spec,
    strict_json_loads as _lc_strict_json_loads,
)

from . import models as _models
from .context_reconciliation import ContextEvidenceItem, build_evidence_item
from .controller import HermesControlledRunResult, run_controlled_hermes_research
from .models import (
    CONFIDENCE_LABELS,
    DRAFT_LIST_FIELDS,
    DRAFT_LIST_ITEM_MAX_LEN,
    DRAFT_LIST_MAX_ITEMS,
    DRAFT_RESEARCH_SUMMARY_MAX_LEN,
    NON_AUTHORITY_NOTICE,
    REQUEST_SCHEMA_VERSION,
    STRATEGY_ADAPTATION_KINDS,
    STRATEGY_LIFECYCLE_ACTIONS,
    STRATEGY_RECOMMENDED_HEALTH_STATES,
    STRATEGY_RISK_DIRECTIONS,
    STRATEGY_TARGET_RISK_BANDS,
    HermesResearchError,
    HermesResearchRunReceipt,
    HermesResearchRunRequest,
    ValidatedStrategyAssessmentDraft,
    build_research_run_request,
    check_strategy_assessment_consistency,
    derive_receipt_id,
)
from .policy import (
    DEFAULT_HERMES_INVOCATION_POLICY,
    USAGE_FILE_NAME,
    HermesInvocationPolicy,
    PolicyBroadeningError,
    build_hermes_argv,
    build_research_envelope,
)

# The strategy-mode vocabulary must stay the exact STRAT-LIFE vocabulary (minus the
# derived-only NEW health state). Drift fails at import, never silently.
if tuple(STRATEGY_TARGET_RISK_BANDS) != tuple(RISK_BANDS) or tuple(
    STRATEGY_RECOMMENDED_HEALTH_STATES
) != tuple(state for state in HEALTH_STATES if state != "NEW"):
    raise ImportError("strategy-mode vocabulary drifted from STRAT-LIFE")

# ---------------------------------------------------------------------------
# Constants / closed vocabularies
# ---------------------------------------------------------------------------

SCHEMA_VERSION = "1.0.0"
RUN_RECORD_SCHEMA_ID = "hermes-strategy-run"
ASSESSMENT_SCHEMA_ID = "hermes-strategy-assessment"
CONTEXT_SCHEMA_ID = "hermes-strategy-lifecycle-context"
RUN_RECORD_ID_PREFIX = "hermesstrategyrun:sha256:"
ASSESSMENT_ID_PREFIX = "hermesstrategyassessment:sha256:"

ASSESSMENT_TRIGGERS = (
    "INITIAL_ASSESSMENT",
    "PERFORMANCE_UPDATE",
    "EVIDENCE_UPDATE",
    "REGIME_CHANGE",
    "ADAPTATION_REVIEW",
    "RESTRICTION_REVIEW",
    "OPERATOR_REASSESSMENT",
)

MAX_EVIDENCE_ITEMS = 12
MAX_EVIDENCE_SUMMARY_CHARS = 160
MAX_SUBJECT_REFS = 32

STATUS_ASSESSMENT_RECORDED = "STRATEGY_ASSESSMENT_RECORDED"
STATUS_RUN_RECORDED_NO_ASSESSMENT = "STRATEGY_RUN_RECORDED_NO_ASSESSMENT"
STATUS_REJECTED = "STRATEGY_MANAGER_REJECTED"
MANAGER_STATUSES = (
    STATUS_ASSESSMENT_RECORDED,
    STATUS_RUN_RECORDED_NO_ASSESSMENT,
    STATUS_REJECTED,
)

ERROR_CODES = (
    "STRATEGY_NOT_FOUND",
    "STRATEGY_RETIRED",
    "STRATEGY_CONTEXT_INVALID",
    "STRATEGY_CONTEXT_LIMIT_EXCEEDED",
    "EVIDENCE_INVALID",
    "INFORMATION_CUTOFF_INVALID",
    "TRIGGER_INVALID",
    "RUNTIME_FAILURE",
    "STRATEGY_OUTPUT_INVALID",
    "STRATEGY_OUTPUT_INCONSISTENT",
    "ASSESSMENT_PREDECESSOR_STALE",
    "STORE_PATH_INVALID",
    "STORE_SCHEMA_CONFLICT",
    "STORE_TAMPERED",
    "STORE_LIMIT_EXCEEDED",
    "INTERNAL_VALIDATION_FAILED",
)

# Conservative strategy-run request maxima, all within (never above) the existing
# controlled-runtime absolute caps. No global Hermes cap is changed.
STRATEGY_REQUEST_MAX_SOURCES = 10
STRATEGY_REQUEST_MAX_WALL_SECONDS = 240
STRATEGY_REQUEST_MAX_OUTPUT_BYTES = 200_000
STRATEGY_REQUEST_MAX_ACCEPTED_COST_USD = "1"
STRATEGY_REQUEST_CATEGORY = "general_public"
STRATEGY_REQUEST_SCOPE = ("public_web", "public_news", "public_reference", "public_market_data")
STRATEGY_REQUEST_SOURCE_TYPES = ("official", "reference", "public_market_data")
# Existing request text-field hard bound (not changed by this WP).
REQUEST_TEXT_FIELD_MAX_CHARS = _models._MAX_LONG_TEXT

STRATEGY_ASSESSMENT_QUESTION = (
    "Assess what this exact StrategyVersion appears to deserve under its current "
    "lifecycle state: CONTINUE, SCALE, REDUCE, ADAPT, PAPER, QUARANTINE or RETIRE."
)

# Store identity (section 22).
STORE_FORMAT_ID = "s10-hermes-strategy-manager-store"
STORE_SCHEMA_VERSION = 1
STORE_APPLICATION_ID = 0x48534D31  # 1213418801 ("HSM1")
STORE_USER_VERSION = 1
STORE_JOURNAL_MODE = "delete"
STORE_SYNCHRONOUS_FULL = 2
MAX_STORE_RECORDS = 100_000
MAX_RECORD_PAYLOAD_BYTES = 262_144
MAX_AGGREGATE_PAYLOAD_BYTES = 536_870_912
RECORD_KIND_RUN = "HERMES_STRATEGY_RUN"
RECORD_KIND_ASSESSMENT = "HERMES_STRATEGY_ASSESSMENT"
RECORD_KINDS = (RECORD_KIND_RUN, RECORD_KIND_ASSESSMENT)

_HEX64_RE = re.compile(r"[0-9a-f]{64}")
_CUTOFF_RE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z")
_LABEL_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}")
_TOKEN_RE = re.compile(r"[A-Z][A-Z0-9_]{0,63}")
_LOWER_TOKEN_RE = re.compile(r"[a-z][a-z0-9_]{0,63}")
_DQ_FLAG_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,63}")
_VERSION_TEXT_RE = re.compile(r"[0-9A-Za-z][0-9A-Za-z.+-]{0,63}")
_COST_RE = re.compile(r"[0-9]+(?:\.[0-9]+)?")
_MAX_TIME_NS = 2**63 - 1
_SUBJECT_FORBIDDEN_MARKERS = ("wallet", "account", "address", "credential", "proxy")
_EVIDENCE_ID_PREFIX = "contextevidence:sha256:"


class StrategyManagerError(Exception):
    """Closed, payload-free strategy-manager failure."""

    def __init__(self, code: str) -> None:
        if code not in ERROR_CODES:
            code = "INTERNAL_VALIDATION_FAILED"
        super().__init__(code)
        self.code = code


def _fail(code: str) -> StrategyManagerError:
    return StrategyManagerError(code)


# ---------------------------------------------------------------------------
# Small validators
# ---------------------------------------------------------------------------


def _canonical_bytes(mapping: Mapping[str, object]) -> bytes:
    try:
        return _lc_canonical_bytes(dict(mapping))
    except StrategyLifecycleError:
        raise _fail("INTERNAL_VALIDATION_FAILED") from None


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _hex64(value: object) -> bool:
    return isinstance(value, str) and _HEX64_RE.fullmatch(value) is not None


def _prefixed_id(value: object, prefix: str) -> bool:
    return isinstance(value, str) and value.startswith(prefix) and _hex64(value[len(prefix):])


def _time_ns(value: object) -> bool:
    return (
        isinstance(value, int) and not isinstance(value, bool) and 0 <= value <= _MAX_TIME_NS
    )


def validate_information_cutoff(value: object) -> str:
    """Exact whole-second UTC ``YYYY-MM-DDTHH:MM:SSZ`` (no fractional cutoff)."""
    if not isinstance(value, str) or _CUTOFF_RE.fullmatch(value) is None:
        raise _fail("INFORMATION_CUTOFF_INVALID")
    try:
        datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        raise _fail("INFORMATION_CUTOFF_INVALID") from None
    return value


def _cutoff_moment(value: str) -> datetime:
    canonical = canonicalize_utc_timestamp(value)
    return datetime.fromisoformat(canonical.replace("Z", "+00:00")).astimezone(timezone.utc)


def _validate_trigger(trigger: object, trigger_ref: object) -> None:
    if not isinstance(trigger, str) or trigger not in ASSESSMENT_TRIGGERS:
        raise _fail("TRIGGER_INVALID")
    if trigger_ref is None:
        return
    try:
        _lc_opaque_ref(trigger_ref)
        _models._scan_secret(trigger_ref)  # type: ignore[arg-type]
        _models._scan_authority(trigger_ref)  # type: ignore[arg-type]
    except (StrategyLifecycleError, HermesResearchError):
        raise _fail("TRIGGER_INVALID") from None


def _subject_ref_is_safe(ref: object) -> bool:
    if not isinstance(ref, str):
        return False
    try:
        _lc_opaque_ref(ref)
        _models._scan_public_market_context_secret(ref)
        _models._scan_authority(ref)
    except (StrategyLifecycleError, HermesResearchError):
        return False
    lowered = ref.lower()
    return not any(marker in lowered for marker in _SUBJECT_FORBIDDEN_MARKERS)


def _text_is_non_path(text: str) -> bool:
    if "\\" in text or "~/" in text:
        return False
    for token in text.split():
        if _models._PATH_TRAVERSAL.search(token) or _models._ABSOLUTE_PATH.search(token):
            return False
        if "/" in token and not token.lower().startswith("https://"):
            return False
    return True


def _validate_summary(summary: object) -> str:
    if (
        not isinstance(summary, str)
        or not summary.strip()
        or len(summary) > MAX_EVIDENCE_SUMMARY_CHARS
        or not summary.isprintable()
        or not _text_is_non_path(summary)
    ):
        raise _fail("EVIDENCE_INVALID")
    try:
        # Strict scan (no public-identifier masking): summaries are carried in the
        # strictly scanned research_objective request field.
        _models._scan_secret(summary)
        _models._scan_authority(summary)
    except HermesResearchError:
        raise _fail("EVIDENCE_INVALID") from None
    return summary


# ---------------------------------------------------------------------------
# Strategy-local lifecycle context fingerprint (section 14)
# ---------------------------------------------------------------------------


def _require_snapshot(snapshot: object) -> StrategyLifecycleSnapshot:
    # The snapshot class can only be constructed by verified STRAT-LIFE replay.
    if not isinstance(snapshot, StrategyLifecycleSnapshot):
        raise _fail("STRATEGY_CONTEXT_INVALID")
    return snapshot


def _resolve_version(snapshot: StrategyLifecycleSnapshot, strategy_version_id: object) -> StrategyVersion:
    if not isinstance(strategy_version_id, str):
        raise _fail("STRATEGY_NOT_FOUND")
    version = snapshot.version_by_id(strategy_version_id)
    if version is None:
        raise _fail("STRATEGY_NOT_FOUND")
    return version


def strategy_lifecycle_context_preimage(
    snapshot: StrategyLifecycleSnapshot, strategy_version_id: str
) -> dict[str, object]:
    """Exact strategy-local/current-authority preimage of the context fingerprint.

    Covers only the target strategy's current health state, current allocation identity
    with exact band/budget/validity (or null), sorted active restriction receipt ids and
    the active PortfolioAuthorityPolicy id (or null). The global store head is NOT part
    of it: an unrelated strategy mutation never changes the fingerprint.
    """
    snapshot = _require_snapshot(snapshot)
    version = _resolve_version(snapshot, strategy_version_id)
    sid = version.strategy_version_id
    allocation = snapshot.allocation_of(sid)
    current_allocation = None
    if allocation is not None:
        current_allocation = {
            "allocation_id": allocation.allocation_id,
            "policy_id": allocation.policy_id,
            "risk_band": allocation.risk_band,
            "active_budget_usd": allocation.active_budget_usd,
            "valid_from_ns": allocation.valid_from_ns,
            "valid_until_ns": allocation.valid_until_ns,
        }
    return {
        "schema_id": CONTEXT_SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "strategy_version_id": sid,
        "current_health_state": snapshot.health_of(sid),
        "current_allocation": current_allocation,
        "active_restriction_receipt_ids": sorted(
            receipt.restriction_receipt_id for receipt in snapshot.restrictions_of(sid)
        ),
        "active_policy_id": snapshot.active_policy_id,
    }


def strategy_lifecycle_context_fingerprint(
    snapshot: StrategyLifecycleSnapshot, strategy_version_id: str
) -> str:
    """``strategy_lifecycle_context_sha256``: sha256 of the canonical preimage (no prefix)."""
    return _sha256(_canonical_bytes(strategy_lifecycle_context_preimage(snapshot, strategy_version_id)))


# ---------------------------------------------------------------------------
# Strategy assessment evidence (section 16)
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class StrategyAssessmentEvidence:
    """One existing canonical ContextEvidenceItem bound to one bounded model-facing summary.

    ``evidence_id`` is the item's own canonical id; no second evidence identity exists.
    """

    evidence_id: str
    content_sha256: str
    evidence_class: str
    subject_refs: tuple[str, ...]
    scope_sha256: str
    information_cutoff: str
    admissibility_status: str
    provenance_manifest_id: str | None
    dq_flags: tuple[str, ...]
    origin: str
    direction: str
    summary: str

    def context_item(self) -> ContextEvidenceItem:
        return ContextEvidenceItem(
            self.evidence_id, self.content_sha256, self.evidence_class, self.subject_refs,
            self.scope_sha256, self.information_cutoff, self.admissibility_status,
            self.provenance_manifest_id, self.dq_flags, self.origin, self.direction,
        )

    def model_facing(self, evidence_index: int) -> dict[str, object]:
        """Compact bounded model-facing view. ``evidence_index`` (1-based) maps exactly to
        the sorted ``input_evidence_refs`` of the assessment, which bind the full item."""
        return {
            "evidence_index": evidence_index,
            "evidence_class": self.evidence_class,
            "direction": self.direction,
            "information_cutoff": self.information_cutoff,
            "summary": self.summary,
        }


def build_strategy_assessment_evidence(
    item: ContextEvidenceItem, summary: str
) -> StrategyAssessmentEvidence:
    """Bind one validated, ADMISSIBLE canonical evidence item to a bounded summary."""
    if not isinstance(item, ContextEvidenceItem):
        raise _fail("EVIDENCE_INVALID")
    if (
        not _hex64(item.content_sha256)
        or not _hex64(item.scope_sha256)
        or not isinstance(item.evidence_class, str)
        or not isinstance(item.origin, str)
        or _TOKEN_RE.fullmatch(item.origin) is None
        or not isinstance(item.subject_refs, tuple)
        or not item.subject_refs
        or len(item.subject_refs) > MAX_SUBJECT_REFS
        or not all(_subject_ref_is_safe(ref) for ref in item.subject_refs)
        or not isinstance(item.dq_flags, tuple)
        or not all(isinstance(flag, str) and _DQ_FLAG_RE.fullmatch(flag) for flag in item.dq_flags)
        or item.admissibility_status != "ADMISSIBLE"
        or item.direction not in ("SUPPORTING", "CONTRADICTING")
        or not _prefixed_id(item.evidence_id, _EVIDENCE_ID_PREFIX)
    ):
        raise _fail("EVIDENCE_INVALID")
    if item.provenance_manifest_id is not None:
        try:
            _lc_opaque_ref(item.provenance_manifest_id)
        except StrategyLifecycleError:
            raise _fail("EVIDENCE_INVALID") from None
    try:
        _cutoff_moment(item.information_cutoff)
        rebuilt = build_evidence_item(
            content_sha256=item.content_sha256, evidence_class=item.evidence_class,
            subject_refs=item.subject_refs, scope_sha256=item.scope_sha256,
            information_cutoff=item.information_cutoff,
            admissibility_status=item.admissibility_status, origin=item.origin,
            direction=item.direction, provenance_manifest_id=item.provenance_manifest_id,
            dq_flags=item.dq_flags,
        )
    except Exception:
        raise _fail("EVIDENCE_INVALID") from None
    # The canonical item must re-derive exactly (forged ids or unsorted fields reject).
    if rebuilt != item:
        raise _fail("EVIDENCE_INVALID")
    return StrategyAssessmentEvidence(
        item.evidence_id, item.content_sha256, item.evidence_class, item.subject_refs,
        item.scope_sha256, item.information_cutoff, item.admissibility_status,
        item.provenance_manifest_id, item.dq_flags, item.origin, item.direction,
        _validate_summary(summary),
    )


def _validate_evidence_set(
    evidence: object, *, subject_refs: tuple[str, ...], information_cutoff: str
) -> tuple[StrategyAssessmentEvidence, ...]:
    if isinstance(evidence, (str, bytes, Mapping)) or not isinstance(evidence, Sequence):
        raise _fail("EVIDENCE_INVALID")
    items = tuple(evidence)
    if len(items) > MAX_EVIDENCE_ITEMS:
        raise _fail("EVIDENCE_INVALID")
    cutoff = _cutoff_moment(information_cutoff)
    subjects = frozenset(subject_refs)
    seen: set[str] = set()
    out: list[StrategyAssessmentEvidence] = []
    for entry in items:
        if not isinstance(entry, StrategyAssessmentEvidence):
            raise _fail("EVIDENCE_INVALID")
        # Re-derive from the canonical item: the wrapper itself is never trusted.
        if build_strategy_assessment_evidence(entry.context_item(), entry.summary) != entry:
            raise _fail("EVIDENCE_INVALID")
        if entry.evidence_id in seen:
            raise _fail("EVIDENCE_INVALID")
        seen.add(entry.evidence_id)
        if _cutoff_moment(entry.information_cutoff) > cutoff:
            raise _fail("EVIDENCE_INVALID")
        if not subjects.intersection(entry.subject_refs):
            raise _fail("EVIDENCE_INVALID")
        out.append(entry)
    return tuple(sorted(out, key=lambda item: item.evidence_id))


def _validate_subject_refs(
    subject_refs: object, version: StrategyVersion
) -> tuple[str, ...]:
    if isinstance(subject_refs, (str, bytes, Mapping)) or not isinstance(subject_refs, Sequence):
        raise _fail("STRATEGY_CONTEXT_INVALID")
    refs = tuple(subject_refs)
    if (
        not refs
        or len(refs) > MAX_SUBJECT_REFS
        or len(set(refs)) != len(refs)
        or not all(_subject_ref_is_safe(ref) for ref in refs)
        or version.strategy_version_id not in refs
        or version.strategy_family_id not in refs
    ):
        raise _fail("STRATEGY_CONTEXT_INVALID")
    return tuple(sorted(refs))


# ---------------------------------------------------------------------------
# Canonical records (sections 18, 19)
# ---------------------------------------------------------------------------


class _PendingId:
    __slots__ = ()


_PENDING = _PendingId()


def _plain(value: object) -> object:
    if isinstance(value, tuple):
        return [_plain(item) for item in value]
    return value


class _Record:
    SCHEMA_ID = ""
    ID_FIELD = ""
    ID_PREFIX = ""
    RECORD_KIND = ""
    TUPLE_FIELDS: tuple[str, ...] = ()

    def _validate(self) -> None:  # pragma: no cover - overridden
        raise NotImplementedError

    def __post_init__(self) -> None:
        if getattr(self, "schema_id") != self.SCHEMA_ID or getattr(self, "schema_version") != SCHEMA_VERSION:
            raise _fail("STORE_TAMPERED")
        self._validate()
        computed = self.ID_PREFIX + _sha256(_canonical_bytes(self._preimage()))
        current = getattr(self, self.ID_FIELD)
        if current is _PENDING:
            object.__setattr__(self, self.ID_FIELD, computed)
        elif current != computed:
            raise _fail("STORE_TAMPERED")

    def _preimage(self) -> dict[str, object]:
        return {
            item.name: _plain(getattr(self, item.name))
            for item in dataclasses.fields(self)  # type: ignore[arg-type]
            if item.name != self.ID_FIELD
        }

    @property
    def record_id(self) -> str:
        return getattr(self, self.ID_FIELD)

    def to_mapping(self) -> dict[str, object]:
        return {
            item.name: _plain(getattr(self, item.name))
            for item in dataclasses.fields(self)  # type: ignore[arg-type]
        }

    @classmethod
    def from_mapping(cls, mapping: object):
        if not isinstance(mapping, Mapping):
            raise _fail("STORE_TAMPERED")
        names = [item.name for item in dataclasses.fields(cls)]  # type: ignore[arg-type]
        if set(mapping) != set(names):
            raise _fail("STORE_TAMPERED")
        values: dict[str, object] = {}
        for name in names:
            value = mapping[name]
            if name in cls.TUPLE_FIELDS:
                if not isinstance(value, list):
                    raise _fail("STORE_TAMPERED")
                value = tuple(value)
            values[name] = value
        if not isinstance(values[cls.ID_FIELD], str):
            raise _fail("STORE_TAMPERED")
        return cls(**values)


def _check(condition: bool) -> None:
    if not condition:
        raise _fail("STORE_TAMPERED")


def _optional_token(value: object) -> bool:
    return value is None or (isinstance(value, str) and _LOWER_TOKEN_RE.fullmatch(value) is not None)


def _utc_second(value: object) -> bool:
    try:
        validate_information_cutoff(value)
    except StrategyManagerError:
        return False
    return True


def _trigger_ok(trigger: object, trigger_ref: object) -> bool:
    try:
        _validate_trigger(trigger, trigger_ref)
    except StrategyManagerError:
        return False
    return True


@dataclasses.dataclass(frozen=True)
class HermesStrategyRunRecord(_Record):
    """Strategy-specific lineage of one controlled Hermes run (successful or failed)."""

    schema_id: str
    schema_version: str
    run_record_id: str
    strategy_version_id: str
    strategy_family_id: str
    strategy_lifecycle_context_sha256: str
    lifecycle_store_head_entry_hash: str | None
    trigger: str
    trigger_ref: str | None
    information_cutoff: str
    runtime_request_id: str
    runtime_receipt_id: str
    runtime_policy_id: str
    provider_label: str
    model_label: str
    hermes_version: str
    terminal_status: str
    start_utc: str
    end_utc: str
    estimated_cost_usd: str | None
    cost_status: str | None
    cost_source: str | None
    decision_time_ns: int
    no_credential_authority: bool
    no_order_authority: bool
    no_execution_authority: bool
    no_live_authority: bool

    SCHEMA_ID = RUN_RECORD_SCHEMA_ID
    ID_FIELD = "run_record_id"
    ID_PREFIX = RUN_RECORD_ID_PREFIX
    RECORD_KIND = RECORD_KIND_RUN

    def _validate(self) -> None:
        _check(_prefixed_id(self.strategy_version_id, "strategyversion:sha256:"))
        _check(_prefixed_id(self.strategy_family_id, "strategyfamily:sha256:"))
        _check(_hex64(self.strategy_lifecycle_context_sha256))
        _check(self.lifecycle_store_head_entry_hash is None or _hex64(self.lifecycle_store_head_entry_hash))
        _check(_trigger_ok(self.trigger, self.trigger_ref))
        _check(_utc_second(self.information_cutoff))
        _check(_prefixed_id(self.runtime_request_id, "hermesresearchrequest:sha256:"))
        _check(_prefixed_id(self.runtime_receipt_id, "hermesresearchreceipt:sha256:"))
        _check(_prefixed_id(self.runtime_policy_id, "hermesinvocationpolicy:sha256:"))
        for label in (self.provider_label, self.model_label):
            _check(isinstance(label, str) and _LABEL_RE.fullmatch(label) is not None)
        _check(isinstance(self.hermes_version, str) and _VERSION_TEXT_RE.fullmatch(self.hermes_version) is not None)
        _check(isinstance(self.terminal_status, str) and _TOKEN_RE.fullmatch(self.terminal_status) is not None)
        _check(_utc_second(self.start_utc) and _utc_second(self.end_utc))
        _check(self.estimated_cost_usd is None or (
            isinstance(self.estimated_cost_usd, str) and _COST_RE.fullmatch(self.estimated_cost_usd) is not None
        ))
        _check(_optional_token(self.cost_status) and _optional_token(self.cost_source))
        _check(_time_ns(self.decision_time_ns))
        _check(all(flag is True for flag in (
            self.no_credential_authority, self.no_order_authority,
            self.no_execution_authority, self.no_live_authority,
        )))


_ASSESSMENT_LIST_FIELDS = DRAFT_LIST_FIELDS


@dataclasses.dataclass(frozen=True)
class HermesStrategyAssessment(_Record):
    """Canonical V2.1 soft strategy decision for one exact StrategyVersion.

    A soft judgment, never a hard authorization. No per-strategy human-approval field and
    no hidden-reasoning field exists.
    """

    schema_id: str
    schema_version: str
    assessment_id: str
    strategy_version_id: str
    strategy_family_id: str
    predecessor_assessment_id: str | None
    run_record_id: str
    runtime_request_id: str
    runtime_receipt_id: str
    trigger: str
    trigger_ref: str | None
    strategy_lifecycle_context_sha256: str
    lifecycle_store_head_entry_hash: str | None
    active_policy_id: str | None
    information_cutoff: str
    subject_refs: tuple[str, ...]
    input_evidence_refs: tuple[str, ...]
    assessment_summary: str
    confidence_label: str
    evidence_for: tuple[str, ...]
    evidence_against: tuple[str, ...]
    uncertainties: tuple[str, ...]
    known_missing_data: tuple[str, ...]
    falsification_checks_performed: tuple[str, ...]
    limitations: tuple[str, ...]
    what_would_change_the_conclusion: tuple[str, ...]
    suggested_next_research_steps: tuple[str, ...]
    lifecycle_action: str
    recommended_health_state: str
    risk_direction: str
    target_risk_band: str | None
    adaptation_recommendation_json: str | None
    decision_time_ns: int
    canonical_soft_strategy_decision: bool
    no_credential_authority: bool
    no_portfolio_policy_authority: bool
    no_hard_risk_override: bool
    no_paper_execution_authority: bool
    no_order_authority: bool
    no_execution_authority: bool
    no_live_authority: bool

    SCHEMA_ID = ASSESSMENT_SCHEMA_ID
    ID_FIELD = "assessment_id"
    ID_PREFIX = ASSESSMENT_ID_PREFIX
    RECORD_KIND = RECORD_KIND_ASSESSMENT
    TUPLE_FIELDS = ("subject_refs", "input_evidence_refs", *_ASSESSMENT_LIST_FIELDS)

    def _validate(self) -> None:
        _check(_prefixed_id(self.strategy_version_id, "strategyversion:sha256:"))
        _check(_prefixed_id(self.strategy_family_id, "strategyfamily:sha256:"))
        _check(self.predecessor_assessment_id is None or _prefixed_id(self.predecessor_assessment_id, ASSESSMENT_ID_PREFIX))
        _check(_prefixed_id(self.run_record_id, RUN_RECORD_ID_PREFIX))
        _check(_prefixed_id(self.runtime_request_id, "hermesresearchrequest:sha256:"))
        _check(_prefixed_id(self.runtime_receipt_id, "hermesresearchreceipt:sha256:"))
        _check(_trigger_ok(self.trigger, self.trigger_ref))
        _check(_hex64(self.strategy_lifecycle_context_sha256))
        _check(self.lifecycle_store_head_entry_hash is None or _hex64(self.lifecycle_store_head_entry_hash))
        _check(self.active_policy_id is None or _prefixed_id(self.active_policy_id, "portfolioauthoritypolicy:sha256:"))
        _check(_utc_second(self.information_cutoff))
        _check(isinstance(self.subject_refs, tuple) and 0 < len(self.subject_refs) <= MAX_SUBJECT_REFS)
        _check(list(self.subject_refs) == sorted(set(self.subject_refs)))
        _check(all(_subject_ref_is_safe(ref) for ref in self.subject_refs))
        _check(self.strategy_version_id in self.subject_refs and self.strategy_family_id in self.subject_refs)
        _check(isinstance(self.input_evidence_refs, tuple) and len(self.input_evidence_refs) <= MAX_EVIDENCE_ITEMS)
        _check(list(self.input_evidence_refs) == sorted(set(self.input_evidence_refs)))
        _check(all(_prefixed_id(ref, _EVIDENCE_ID_PREFIX) for ref in self.input_evidence_refs))
        _check(
            isinstance(self.assessment_summary, str)
            and bool(self.assessment_summary.strip())
            and len(self.assessment_summary) <= DRAFT_RESEARCH_SUMMARY_MAX_LEN
        )
        _check(self.confidence_label in CONFIDENCE_LABELS)
        for name in _ASSESSMENT_LIST_FIELDS:
            value = getattr(self, name)
            _check(isinstance(value, tuple) and len(value) <= DRAFT_LIST_MAX_ITEMS)
            _check(all(isinstance(item, str) and len(item) <= DRAFT_LIST_ITEM_MAX_LEN for item in value))
        _check(bool(self.falsification_checks_performed))
        _check(self.lifecycle_action in STRATEGY_LIFECYCLE_ACTIONS)
        _check(self.recommended_health_state in STRATEGY_RECOMMENDED_HEALTH_STATES)
        _check(self.risk_direction in STRATEGY_RISK_DIRECTIONS)
        _check(self.target_risk_band is None or self.target_risk_band in STRATEGY_TARGET_RISK_BANDS)
        _check(_time_ns(self.decision_time_ns))
        _check(all(flag is True for flag in (
            self.canonical_soft_strategy_decision, self.no_credential_authority,
            self.no_portfolio_policy_authority, self.no_hard_risk_override,
            self.no_paper_execution_authority, self.no_order_authority,
            self.no_execution_authority, self.no_live_authority,
        )))
        _check(check_strategy_assessment_consistency(self.strategy_draft()))

    def adaptation_recommendation(self) -> dict[str, object] | None:
        if self.adaptation_recommendation_json is None:
            return None
        try:
            decoded = _lc_strict_json_loads(self.adaptation_recommendation_json)
        except StrategyLifecycleError:
            raise _fail("STORE_TAMPERED") from None
        _check(isinstance(decoded, dict) and set(decoded) == {"kind", "summary", "parameter_updates"})
        _check(_lc_canonical_text(decoded) == self.adaptation_recommendation_json)  # type: ignore[arg-type]
        return decoded  # type: ignore[return-value]

    def strategy_draft(self) -> ValidatedStrategyAssessmentDraft:
        adaptation = self.adaptation_recommendation()
        kind = summary = updates = None
        if adaptation is not None:
            kind = adaptation["kind"]
            summary = adaptation["summary"]
            _check(kind in STRATEGY_ADAPTATION_KINDS and isinstance(summary, str) and summary.strip() != "")
            _check(isinstance(adaptation["parameter_updates"], dict))
            updates = _lc_canonical_text(adaptation["parameter_updates"])
        return ValidatedStrategyAssessmentDraft(
            lifecycle_action=self.lifecycle_action,
            recommended_health_state=self.recommended_health_state,
            risk_direction=self.risk_direction,
            target_risk_band=self.target_risk_band,
            adaptation_kind=kind,  # type: ignore[arg-type]
            adaptation_summary=summary,  # type: ignore[arg-type]
            adaptation_parameter_updates_json=updates,
            research_lists=tuple((name, getattr(self, name)) for name in _ASSESSMENT_LIST_FIELDS),
        )


_RECORD_TYPES = {RECORD_KIND_RUN: HermesStrategyRunRecord, RECORD_KIND_ASSESSMENT: HermesStrategyAssessment}


def record_from_mapping(record_kind: str, mapping: object) -> HermesStrategyRunRecord | HermesStrategyAssessment:
    record_type = _RECORD_TYPES.get(record_kind)
    if record_type is None:
        raise _fail("STORE_TAMPERED")
    return record_type.from_mapping(mapping)


# ---------------------------------------------------------------------------
# Append-only SQLite history store (section 22)
# ---------------------------------------------------------------------------

_KIND_SQL = ", ".join(f"'{kind}'" for kind in RECORD_KINDS)
_CREATE_META = (
    "CREATE TABLE strategy_manager_meta ("
    " singleton INTEGER PRIMARY KEY NOT NULL CHECK (singleton = 1),"
    f" format_id TEXT NOT NULL CHECK (format_id = '{STORE_FORMAT_ID}'),"
    f" schema_version INTEGER NOT NULL CHECK (schema_version = {STORE_SCHEMA_VERSION})"
    ")"
)
_CREATE_RECORDS = (
    "CREATE TABLE strategy_manager_records ("
    " sequence_number INTEGER PRIMARY KEY NOT NULL CHECK (sequence_number >= 0),"
    f" record_kind TEXT NOT NULL CHECK (record_kind IN ({_KIND_SQL})),"
    " record_id TEXT NOT NULL UNIQUE,"
    " strategy_version_id TEXT NOT NULL,"
    " payload_json TEXT NOT NULL,"
    " payload_sha256 TEXT NOT NULL,"
    " previous_entry_hash TEXT,"
    " entry_hash TEXT NOT NULL UNIQUE"
    ")"
)


def _trigger_sql(table: str, operation: str) -> str:
    return (
        f"CREATE TRIGGER {table}_no_{operation.lower()} BEFORE {operation} ON {table}"
        f" BEGIN SELECT RAISE(ABORT, '{table} is append-only'); END"
    )


_EXPECTED_OBJECTS = {
    ("table", "strategy_manager_meta"): _CREATE_META,
    ("table", "strategy_manager_records"): _CREATE_RECORDS,
    ("trigger", "strategy_manager_meta_no_delete"): _trigger_sql("strategy_manager_meta", "DELETE"),
    ("trigger", "strategy_manager_meta_no_update"): _trigger_sql("strategy_manager_meta", "UPDATE"),
    ("trigger", "strategy_manager_records_no_delete"): _trigger_sql("strategy_manager_records", "DELETE"),
    ("trigger", "strategy_manager_records_no_update"): _trigger_sql("strategy_manager_records", "UPDATE"),
}


def entry_hash(
    sequence_number: int,
    record_kind: str,
    record_id: str,
    strategy_version_id: str,
    payload_sha256: str,
    previous_entry_hash: str | None,
) -> str:
    """SHA-256 of the canonical JSON binding one entry to its exact predecessor."""
    return _sha256(_canonical_bytes({
        "sequence_number": sequence_number,
        "record_kind": record_kind,
        "record_id": record_id,
        "strategy_version_id": strategy_version_id,
        "payload_sha256": payload_sha256,
        "previous_entry_hash": previous_entry_hash,
    }))


@dataclasses.dataclass(frozen=True)
class HermesStrategyManagerStoreSnapshot:
    """History projection derived only by verified replay."""

    store_head_entry_hash: str | None
    total_rows: int
    total_payload_bytes: int
    run_records: tuple[HermesStrategyRunRecord, ...]
    assessments: tuple[HermesStrategyAssessment, ...]
    latest_assessment_by_strategy_version: tuple[tuple[str, str], ...]

    def latest_assessment_id(self, strategy_version_id: str) -> str | None:
        return dict(self.latest_assessment_by_strategy_version).get(strategy_version_id)


class _ManagerState:
    def __init__(self) -> None:
        self.runs: dict[str, HermesStrategyRunRecord] = {}
        self.assessments: dict[str, HermesStrategyAssessment] = {}
        self.assessed_runs: set[str] = set()
        self.latest: dict[str, str] = {}

    def apply(self, record: object, *, stale_code: str) -> None:
        if isinstance(record, HermesStrategyRunRecord):
            _check(record.run_record_id not in self.runs)
            self.runs[record.run_record_id] = record
            return
        _check(isinstance(record, HermesStrategyAssessment))
        assert isinstance(record, HermesStrategyAssessment)
        run = self.runs.get(record.run_record_id)
        _check(run is not None and record.run_record_id not in self.assessed_runs)
        assert run is not None
        _check(
            run.strategy_version_id == record.strategy_version_id
            and run.strategy_family_id == record.strategy_family_id
            and run.runtime_request_id == record.runtime_request_id
            and run.runtime_receipt_id == record.runtime_receipt_id
            and run.trigger == record.trigger
            and run.trigger_ref == record.trigger_ref
            and run.information_cutoff == record.information_cutoff
            and run.strategy_lifecycle_context_sha256 == record.strategy_lifecycle_context_sha256
            and run.lifecycle_store_head_entry_hash == record.lifecycle_store_head_entry_hash
            and run.decision_time_ns == record.decision_time_ns
        )
        if record.predecessor_assessment_id != self.latest.get(record.strategy_version_id):
            raise _fail(stale_code)
        self.assessments[record.assessment_id] = record
        self.assessed_runs.add(record.run_record_id)
        self.latest[record.strategy_version_id] = record.assessment_id


@dataclasses.dataclass(frozen=True)
class _Loaded:
    state: _ManagerState
    head: str | None
    rows: int
    payload_bytes: int

    def snapshot(self) -> HermesStrategyManagerStoreSnapshot:
        return HermesStrategyManagerStoreSnapshot(
            store_head_entry_hash=self.head,
            total_rows=self.rows,
            total_payload_bytes=self.payload_bytes,
            run_records=tuple(self.state.runs.values()),
            assessments=tuple(self.state.assessments.values()),
            latest_assessment_by_strategy_version=tuple(sorted(self.state.latest.items())),
        )


def _normalize_ddl(sql: object) -> str | None:
    return " ".join(sql.replace("(", " ( ").replace(")", " ) ").split()) if isinstance(sql, str) else None


def _validated_path(path: object, *, must_exist: bool) -> Path:
    if isinstance(path, (bool, bytes)) or not isinstance(path, (str, os.PathLike)):
        raise _fail("STORE_PATH_INVALID")
    raw = os.fspath(path)
    if not isinstance(raw, str) or not raw.strip() or "\x00" in raw:
        raise _fail("STORE_PATH_INVALID")
    target = Path(raw).absolute()
    try:
        if target.suffix != ".sqlite3":
            raise _fail("STORE_PATH_INVALID")
        parent = target.parent
        if not parent.is_dir() or any(item.is_symlink() for item in (parent, *parent.parents)):
            raise _fail("STORE_PATH_INVALID")
        if target.is_symlink():
            raise _fail("STORE_PATH_INVALID")
        if target.exists():
            if not target.is_file() or target.lstat().st_nlink != 1:
                raise _fail("STORE_PATH_INVALID")
        elif must_exist:
            raise _fail("STORE_PATH_INVALID")
    except OSError:
        raise _fail("STORE_PATH_INVALID") from None
    return target


def _verify_connection_contract(connection: sqlite3.Connection) -> None:
    journal = connection.execute("PRAGMA journal_mode").fetchone()
    if (
        journal is None
        or str(journal[0]).lower() != STORE_JOURNAL_MODE
        or connection.execute("PRAGMA synchronous").fetchone() != (STORE_SYNCHRONOUS_FULL,)
        or connection.execute("PRAGMA foreign_keys").fetchone() != (1,)
    ):
        raise _fail("STORE_SCHEMA_CONFLICT")


def _connect(path: Path, mode: str) -> sqlite3.Connection:
    """Open one connection satisfying the exact PRAGMA contract, or fail closed.

    A file not already in DELETE journal mode (e.g. WAL drift) is never converted.
    """
    try:
        connection = sqlite3.connect(
            f"{path.as_uri()}?mode={mode}", uri=True, isolation_level=None, timeout=0.0
        )
    except sqlite3.Error:
        raise _fail("STORE_SCHEMA_CONFLICT") from None
    try:
        journal = connection.execute("PRAGMA journal_mode").fetchone()
        if journal is None or str(journal[0]).lower() != STORE_JOURNAL_MODE:
            raise _fail("STORE_SCHEMA_CONFLICT")
        connection.execute("PRAGMA journal_mode=DELETE")
        connection.execute("PRAGMA synchronous=FULL")
        connection.execute("PRAGMA foreign_keys=ON")
        _verify_connection_contract(connection)
    except (StrategyManagerError, sqlite3.Error):
        connection.close()
        raise _fail("STORE_SCHEMA_CONFLICT") from None
    return connection


def _verify_schema(connection: sqlite3.Connection) -> None:
    if connection.execute("PRAGMA application_id").fetchone() != (STORE_APPLICATION_ID,):
        raise _fail("STORE_SCHEMA_CONFLICT")
    if connection.execute("PRAGMA user_version").fetchone() != (STORE_USER_VERSION,):
        raise _fail("STORE_SCHEMA_CONFLICT")
    objects = connection.execute(
        "SELECT type, name, sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'"
    ).fetchall()
    actual = {(kind, name): _normalize_ddl(sql) for kind, name, sql in objects}
    expected = {key: _normalize_ddl(sql) for key, sql in _EXPECTED_OBJECTS.items()}
    if len(objects) != len(actual) or actual != expected:
        raise _fail("STORE_SCHEMA_CONFLICT")
    if connection.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
        raise _fail("STORE_TAMPERED")
    if connection.execute(
        "SELECT singleton, format_id, schema_version FROM strategy_manager_meta"
    ).fetchall() != [(1, STORE_FORMAT_ID, STORE_SCHEMA_VERSION)]:
        raise _fail("STORE_TAMPERED")


def _load(connection: sqlite3.Connection) -> _Loaded:
    _verify_connection_contract(connection)
    _verify_schema(connection)
    count = connection.execute("SELECT COUNT(*) FROM strategy_manager_records").fetchone()[0]
    if count > MAX_STORE_RECORDS:
        raise _fail("STORE_TAMPERED")
    rows = connection.execute(
        "SELECT sequence_number, record_kind, record_id, strategy_version_id, payload_json,"
        " payload_sha256, previous_entry_hash, entry_hash FROM strategy_manager_records"
        " ORDER BY sequence_number"
    ).fetchall()
    state = _ManagerState()
    previous: str | None = None
    total_bytes = 0
    for index, row in enumerate(rows):
        sequence, kind, record_id, strategy_id, payload_json, payload_sha, previous_hash, current = row
        _check(
            sequence == index
            and kind in RECORD_KINDS
            and isinstance(record_id, str)
            and isinstance(strategy_id, str)
            and isinstance(payload_json, str)
            and isinstance(payload_sha, str)
            and previous_hash == previous
            and isinstance(current, str)
        )
        payload_bytes = payload_json.encode("utf-8")
        total_bytes += len(payload_bytes)
        _check(len(payload_bytes) <= MAX_RECORD_PAYLOAD_BYTES and total_bytes <= MAX_AGGREGATE_PAYLOAD_BYTES)
        _check(_sha256(payload_bytes) == payload_sha)
        try:
            decoded = _lc_strict_json_loads(payload_json)
        except StrategyLifecycleError:
            raise _fail("STORE_TAMPERED") from None
        _check(isinstance(decoded, dict) and _canonical_bytes(decoded) == payload_bytes)
        record = record_from_mapping(kind, decoded)
        _check(record.record_id == record_id and record.strategy_version_id == strategy_id)  # type: ignore[union-attr]
        _check(entry_hash(sequence, kind, record_id, strategy_id, payload_sha, previous_hash) == current)
        state.apply(record, stale_code="STORE_TAMPERED")
        previous = current
    return _Loaded(state, previous, len(rows), total_bytes)


def _guarded(action: Callable[[], HermesStrategyManagerStoreSnapshot]) -> HermesStrategyManagerStoreSnapshot:
    try:
        return action()
    except StrategyManagerError:
        raise
    except sqlite3.Error:
        raise _fail("STORE_TAMPERED") from None
    except Exception:
        raise _fail("INTERNAL_VALIDATION_FAILED") from None


def _load_path(target: Path) -> HermesStrategyManagerStoreSnapshot:
    def action() -> HermesStrategyManagerStoreSnapshot:
        connection = _connect(target, "ro")
        try:
            return _load(connection).snapshot()
        finally:
            connection.close()

    return _guarded(action)


def initialize_hermes_strategy_manager_store(path: object) -> HermesStrategyManagerStoreSnapshot:
    """Create the exact empty store at an explicit path, or verify an existing one."""
    target = _validated_path(path, must_exist=False)
    if target.exists():
        return _load_path(target)
    try:
        descriptor = os.open(str(target), os.O_CREAT | os.O_EXCL | os.O_RDWR, 0o600)
        os.close(descriptor)
    except OSError:
        raise _fail("STORE_PATH_INVALID") from None
    connection = None
    committed = False
    try:
        connection = _connect(target, "rw")
        connection.execute("BEGIN IMMEDIATE")
        for sql in _EXPECTED_OBJECTS.values():
            connection.execute(sql)
        connection.execute(
            "INSERT INTO strategy_manager_meta (singleton, format_id, schema_version) VALUES (?, ?, ?)",
            (1, STORE_FORMAT_ID, STORE_SCHEMA_VERSION),
        )
        connection.execute(f"PRAGMA application_id={STORE_APPLICATION_ID}")
        connection.execute(f"PRAGMA user_version={STORE_USER_VERSION}")
        connection.execute("COMMIT")
        committed = True
    except (StrategyManagerError, sqlite3.Error):
        pass
    finally:
        if connection is not None:
            if connection.in_transaction:
                try:
                    connection.execute("ROLLBACK")
                except sqlite3.Error:
                    pass
            connection.close()
        if not committed:
            try:
                target.unlink()
            except OSError:
                pass
    if not committed:
        raise _fail("INTERNAL_VALIDATION_FAILED")
    return _load_path(target)


def load_hermes_strategy_manager_store(path: object) -> HermesStrategyManagerStoreSnapshot:
    """Read one existing store read-only and fully verify it by replay."""
    return _load_path(_validated_path(path, must_exist=True))


def _append_records(
    path: object, records: Sequence[HermesStrategyRunRecord | HermesStrategyAssessment]
) -> HermesStrategyManagerStoreSnapshot:
    """Append records in ONE transaction after full verification; all-or-nothing.

    Each assessment re-checks its same-strategy predecessor against replay inside the
    transaction (ASSESSMENT_PREDECESSOR_STALE). Any failure rolls everything back.
    """
    target = _validated_path(path, must_exist=True)
    prepared: list[tuple[str, str, str, str, str]] = []
    for record in records:
        if record_from_mapping(record.RECORD_KIND, record.to_mapping()) != record:
            raise _fail("INTERNAL_VALIDATION_FAILED")
        payload = _canonical_bytes(record.to_mapping())
        if len(payload) > MAX_RECORD_PAYLOAD_BYTES:
            raise _fail("STORE_LIMIT_EXCEEDED")
        prepared.append((
            record.RECORD_KIND, record.record_id, record.strategy_version_id,
            payload.decode("utf-8"), _sha256(payload),
        ))

    def action() -> HermesStrategyManagerStoreSnapshot:
        connection = _connect(target, "rw")
        try:
            connection.execute("BEGIN IMMEDIATE")
            loaded = _load(connection)
            if loaded.rows + len(prepared) > MAX_STORE_RECORDS or loaded.payload_bytes + sum(
                len(item[3].encode("utf-8")) for item in prepared
            ) > MAX_AGGREGATE_PAYLOAD_BYTES:
                raise _fail("STORE_LIMIT_EXCEEDED")
            head = loaded.head
            sequence = loaded.rows
            for record, (kind, record_id, strategy_id, payload_json, payload_sha) in zip(records, prepared):
                if record_id in loaded.state.runs or record_id in loaded.state.assessments:
                    raise _fail("INTERNAL_VALIDATION_FAILED")
                loaded.state.apply(record, stale_code="ASSESSMENT_PREDECESSOR_STALE")
                current = entry_hash(sequence, kind, record_id, strategy_id, payload_sha, head)
                connection.execute(
                    "INSERT INTO strategy_manager_records (sequence_number, record_kind, record_id,"
                    " strategy_version_id, payload_json, payload_sha256, previous_entry_hash,"
                    " entry_hash) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (sequence, kind, record_id, strategy_id, payload_json, payload_sha, head, current),
                )
                head = current
                sequence += 1
            verified = _load(connection)
            if verified.head != head or verified.rows != sequence:
                raise _fail("INTERNAL_VALIDATION_FAILED")
            connection.execute("COMMIT")
            return verified.snapshot()
        finally:
            if connection.in_transaction:
                try:
                    connection.execute("ROLLBACK")
                except sqlite3.Error:
                    pass
            connection.close()

    return _guarded(action)


# ---------------------------------------------------------------------------
# Foreground manager entrypoint (sections 24-27)
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class HermesStrategyManagerResult:
    """Small closed manager result. Never echoes model output, context, paths or secrets."""

    status: str
    error_code: str | None
    run_record: HermesStrategyRunRecord | None
    assessment: HermesStrategyAssessment | None
    store_head_entry_hash: str | None


def _rejected(code: str) -> HermesStrategyManagerResult:
    return HermesStrategyManagerResult(STATUS_REJECTED, StrategyManagerError(code).code, None, None, None)


@dataclasses.dataclass(frozen=True)
class _Prepared:
    request: HermesResearchRunRequest
    version: StrategyVersion
    parameter_names: tuple[str, ...]
    fingerprint: str
    store_head: str | None
    active_policy_id: str | None
    subject_refs: tuple[str, ...]
    evidence: tuple[StrategyAssessmentEvidence, ...]
    predecessor_assessment_id: str | None


def _strategy_request_fields(
    *, snapshot: StrategyLifecycleSnapshot, version: StrategyVersion, spec: Mapping[str, object],
    fingerprint: str, trigger: str, trigger_ref: str | None, information_cutoff: str,
    subject_refs: tuple[str, ...], evidence: tuple[StrategyAssessmentEvidence, ...],
    provider_label: object, model_label: object,
) -> dict[str, object]:
    """Deterministic bounded model-facing context. Never account_scope_ref, credentials,
    paths or raw execution_rule content (bound by SHA-256 only)."""
    sid = version.strategy_version_id
    allocation = snapshot.allocation_of(sid)
    question = _lc_canonical_text({
        "assessment_question": STRATEGY_ASSESSMENT_QUESTION,
        "strategy_identity": {
            "strategy_version_id": sid,
            "strategy_family_id": version.strategy_family_id,
            "parent_strategy_version_id": version.parent_strategy_version_id,
            "strategy_label": version.strategy_label,
            "evidence_posture": version.evidence_posture,
            "adaptation_class": version.adaptation_class,
            "strategy_code_identity": version.strategy_code_identity,
            "execution_rule_sha256": _sha256(_lc_canonical_bytes(spec["execution_rule"])),
            "adaptive_bounds_sha256": _sha256(version.adaptive_bounds_json.encode("utf-8")),
        },
        "lifecycle_state": {
            "current_health_state": snapshot.health_of(sid),
            "current_allocation_id": None if allocation is None else allocation.allocation_id,
            "current_risk_band": None if allocation is None else allocation.risk_band,
            "current_active_budget_usd": None if allocation is None else allocation.active_budget_usd,
            "active_restriction_receipt_ids": sorted(
                receipt.restriction_receipt_id for receipt in snapshot.restrictions_of(sid)
            ),
            "active_policy_id": snapshot.active_policy_id,
            "strategy_lifecycle_context_sha256": fingerprint,
        },
        "assessment_trigger": {"trigger": trigger, "trigger_ref": trigger_ref},
        "information_cutoff": information_cutoff,
    })
    objective = _lc_canonical_text({
        "objective": (
            "Produce a soft strategy assessment of the StrategyVersion in research_question. "
            "The assessment is current only through the stated information cutoff "
            f"{information_cutoff}. Evidence posture guides the approach and is not a "
            "pass/fail gate."
        ),
        # Bounded project evidence; evidence_index i is input_evidence_refs[i - 1].
        "project_evidence": [item.model_facing(index) for index, item in enumerate(evidence, 1)],
    })
    context = _lc_canonical_text({
        "strategy_definition": {
            "thesis": spec["thesis"],
            "universe": spec["universe"],
            "entry_rule": spec["entry_rule"],
            "exit_rule": spec["exit_rule"],
            "parameters": spec["parameters"],
        },
        "subject_refs": list(subject_refs),
    })
    for text in (question, objective, context):
        if len(text) > REQUEST_TEXT_FIELD_MAX_CHARS:
            raise _fail("STRATEGY_CONTEXT_LIMIT_EXCEEDED")
    return {
        "schema_version": REQUEST_SCHEMA_VERSION,
        "research_question": question,
        "research_objective": objective,
        "research_category": STRATEGY_REQUEST_CATEGORY,
        "public_market_context": context,
        "allowed_research_scope": list(STRATEGY_REQUEST_SCOPE),
        "required_source_types": list(STRATEGY_REQUEST_SOURCE_TYPES),
        "max_sources": STRATEGY_REQUEST_MAX_SOURCES,
        "provider_label": provider_label,
        "model_label": model_label,
        "max_wall_seconds": STRATEGY_REQUEST_MAX_WALL_SECONDS,
        "max_output_bytes": STRATEGY_REQUEST_MAX_OUTPUT_BYTES,
        "max_accepted_estimated_cost_usd": STRATEGY_REQUEST_MAX_ACCEPTED_COST_USD,
        "human_review_required": True,
        "non_authority_notice": NON_AUTHORITY_NOTICE,
    }


def _prepare(
    *, lifecycle_snapshot: object, strategy_version_id: object, trigger: object,
    trigger_ref: object, subject_refs: object, evidence: object, information_cutoff: object,
    decision_time_ns: object, provider_label: object, model_label: object, store_path: object,
    executable_path: str, policy: HermesInvocationPolicy,
) -> _Prepared:
    """Every pre-spawn check. Nothing here touches the backend."""
    _validate_trigger(trigger, trigger_ref)
    cutoff = validate_information_cutoff(information_cutoff)
    if not _time_ns(decision_time_ns):
        raise _fail("STRATEGY_CONTEXT_INVALID")
    if not isinstance(policy, HermesInvocationPolicy):
        raise _fail("STRATEGY_CONTEXT_INVALID")
    snapshot = _require_snapshot(lifecycle_snapshot)
    version = _resolve_version(snapshot, strategy_version_id)
    if snapshot.health_of(version.strategy_version_id) == "RETIRED":
        raise _fail("STRATEGY_RETIRED")
    try:
        spec = _lc_parse_strategy_spec(version.strategy_spec_json)
    except StrategyLifecycleError:
        raise _fail("STRATEGY_CONTEXT_INVALID") from None
    refs = _validate_subject_refs(subject_refs, version)
    items = _validate_evidence_set(evidence, subject_refs=refs, information_cutoff=cutoff)
    fingerprint = strategy_lifecycle_context_fingerprint(snapshot, version.strategy_version_id)
    history = load_hermes_strategy_manager_store(store_path)
    fields = _strategy_request_fields(
        snapshot=snapshot, version=version, spec=spec, fingerprint=fingerprint,
        trigger=trigger, trigger_ref=trigger_ref, information_cutoff=cutoff,  # type: ignore[arg-type]
        subject_refs=refs, evidence=items, provider_label=provider_label, model_label=model_label,
    )
    try:
        request = build_research_run_request(fields)
    except HermesResearchError as exc:
        if exc.code == "REQUEST_BOUND_EXCEEDED":
            raise _fail("STRATEGY_CONTEXT_LIMIT_EXCEEDED") from None
        raise _fail("STRATEGY_CONTEXT_INVALID") from None
    parameter_names = tuple(sorted(spec["parameters"]))  # type: ignore[arg-type]
    # Fail closed BEFORE any spawn if the exact prompt or command line cannot fit the
    # existing hard bounds. Nothing is ever truncated or summarized to force admission.
    try:
        envelope = build_research_envelope(
            request, strategy_mode=True, strategy_parameter_names=parameter_names,
        )
        build_hermes_argv(executable_path, request, envelope.to_prompt_string(), policy, USAGE_FILE_NAME)
    except PolicyBroadeningError as exc:
        if str(exc) in ("POLICY_PROMPT_TOO_LARGE", "POLICY_COMMAND_LINE_TOO_LARGE"):
            raise _fail("STRATEGY_CONTEXT_LIMIT_EXCEEDED") from None
        raise _fail("STRATEGY_CONTEXT_INVALID") from None
    except HermesResearchError:
        raise _fail("STRATEGY_CONTEXT_INVALID") from None
    return _Prepared(
        request=request,
        version=version,
        parameter_names=parameter_names,
        fingerprint=fingerprint,
        store_head=snapshot.store_head_entry_hash,
        active_policy_id=snapshot.active_policy_id,
        subject_refs=refs,
        evidence=items,
        predecessor_assessment_id=history.latest_assessment_id(version.strategy_version_id),
    )


def _build_run_record(
    prepared: _Prepared, receipt: HermesResearchRunReceipt, *, trigger: str,
    trigger_ref: str | None, information_cutoff: str, decision_time_ns: int,
) -> HermesStrategyRunRecord:
    return HermesStrategyRunRecord(
        schema_id=RUN_RECORD_SCHEMA_ID,
        schema_version=SCHEMA_VERSION,
        run_record_id=_PENDING,  # type: ignore[arg-type]
        strategy_version_id=prepared.version.strategy_version_id,
        strategy_family_id=prepared.version.strategy_family_id,
        strategy_lifecycle_context_sha256=prepared.fingerprint,
        lifecycle_store_head_entry_hash=prepared.store_head,
        trigger=trigger,
        trigger_ref=trigger_ref,
        information_cutoff=information_cutoff,
        runtime_request_id=receipt.request_id,
        runtime_receipt_id=receipt.receipt_id,
        runtime_policy_id=receipt.policy_id,
        provider_label=receipt.provider_label,
        model_label=receipt.model_label,
        hermes_version=receipt.hermes_version,
        terminal_status=receipt.terminal_status,
        start_utc=receipt.start_utc,
        end_utc=receipt.end_utc,
        estimated_cost_usd=receipt.estimated_cost_usd,
        cost_status=receipt.cost_status,
        cost_source=receipt.cost_source,
        decision_time_ns=decision_time_ns,
        no_credential_authority=True,
        no_order_authority=True,
        no_execution_authority=True,
        no_live_authority=True,
    )


def _build_assessment(
    prepared: _Prepared, run: HermesStrategyRunRecord, *, research_summary: str,
    confidence_label: str, draft: ValidatedStrategyAssessmentDraft,
) -> HermesStrategyAssessment:
    adaptation_json = None
    if draft.adaptation_kind is not None:
        try:
            updates = _lc_strict_json_loads(draft.adaptation_parameter_updates_json)
            adaptation_json = _lc_canonical_text({
                "kind": draft.adaptation_kind,
                "summary": draft.adaptation_summary,
                "parameter_updates": updates,
            })
        except StrategyLifecycleError:
            raise _fail("STRATEGY_OUTPUT_INVALID") from None
        if not isinstance(updates, dict) or not set(updates).issubset(prepared.parameter_names):
            raise _fail("STRATEGY_OUTPUT_INVALID")
    lists = dict(draft.research_lists)
    try:
        return HermesStrategyAssessment(
            schema_id=ASSESSMENT_SCHEMA_ID,
            schema_version=SCHEMA_VERSION,
            assessment_id=_PENDING,  # type: ignore[arg-type]
            strategy_version_id=run.strategy_version_id,
            strategy_family_id=run.strategy_family_id,
            predecessor_assessment_id=prepared.predecessor_assessment_id,
            run_record_id=run.run_record_id,
            runtime_request_id=run.runtime_request_id,
            runtime_receipt_id=run.runtime_receipt_id,
            trigger=run.trigger,
            trigger_ref=run.trigger_ref,
            strategy_lifecycle_context_sha256=run.strategy_lifecycle_context_sha256,
            lifecycle_store_head_entry_hash=run.lifecycle_store_head_entry_hash,
            active_policy_id=prepared.active_policy_id,
            information_cutoff=run.information_cutoff,
            subject_refs=prepared.subject_refs,
            input_evidence_refs=tuple(item.evidence_id for item in prepared.evidence),
            assessment_summary=research_summary,
            confidence_label=confidence_label,
            evidence_for=tuple(lists["evidence_for"]),
            evidence_against=tuple(lists["evidence_against"]),
            uncertainties=tuple(lists["uncertainties"]),
            known_missing_data=tuple(lists["known_missing_data"]),
            falsification_checks_performed=tuple(lists["falsification_checks_performed"]),
            limitations=tuple(lists["limitations"]),
            what_would_change_the_conclusion=tuple(lists["what_would_change_the_conclusion"]),
            suggested_next_research_steps=tuple(lists["suggested_next_research_steps"]),
            lifecycle_action=draft.lifecycle_action,
            recommended_health_state=draft.recommended_health_state,
            risk_direction=draft.risk_direction,
            target_risk_band=draft.target_risk_band,
            adaptation_recommendation_json=adaptation_json,
            decision_time_ns=run.decision_time_ns,
            canonical_soft_strategy_decision=True,
            no_credential_authority=True,
            no_portfolio_policy_authority=True,
            no_hard_risk_override=True,
            no_paper_execution_authority=True,
            no_order_authority=True,
            no_execution_authority=True,
            no_live_authority=True,
        )
    except StrategyManagerError:
        raise _fail("STRATEGY_OUTPUT_INVALID") from None


def _record_run_only(store_path: object, run: HermesStrategyRunRecord, code: str) -> HermesStrategyManagerResult:
    try:
        snapshot = _append_records(store_path, (run,))
    except StrategyManagerError as exc:
        return _rejected(exc.code)
    return HermesStrategyManagerResult(
        STATUS_RUN_RECORDED_NO_ASSESSMENT, code, run, None, snapshot.store_head_entry_hash
    )


def _receipt_is_bound(
    result: object, request: HermesResearchRunRequest, policy: HermesInvocationPolicy
) -> bool:
    if not isinstance(result, HermesControlledRunResult):
        return False
    receipt = result.receipt
    return (
        isinstance(receipt, HermesResearchRunReceipt)
        and derive_receipt_id(receipt) == receipt.receipt_id
        and receipt.request_id == request.request_id == result.request_id
        and receipt.policy_id == policy.policy_id == result.policy_id
        and receipt.provider_label == request.provider_label
        and receipt.model_label == request.model_label
    )


def run_hermes_strategy_assessment(
    *,
    lifecycle_snapshot: StrategyLifecycleSnapshot,
    strategy_version_id: str,
    trigger: str,
    trigger_ref: str | None,
    subject_refs: Sequence[str],
    evidence: Sequence[StrategyAssessmentEvidence],
    information_cutoff: str,
    decision_time_ns: int,
    provider_label: str,
    model_label: str,
    backend: object,
    store_path: object,
    executable_path: str = "hermes",
    policy: HermesInvocationPolicy = DEFAULT_HERMES_INVOCATION_POLICY,
    hermes_home: str | None = None,
    clock: Callable[[], datetime] | None = None,
) -> HermesStrategyManagerResult:
    """Run ONE foreground controlled Hermes strategy assessment for one StrategyVersion.

    Exactly one existing controlled runtime call; no retry, fallback, scheduler or
    STRAT-LIFE mutation. Returns a closed result; never raises for ordinary failures.
    """
    try:
        prepared = _prepare(
            lifecycle_snapshot=lifecycle_snapshot, strategy_version_id=strategy_version_id,
            trigger=trigger, trigger_ref=trigger_ref, subject_refs=subject_refs,
            evidence=evidence, information_cutoff=information_cutoff,
            decision_time_ns=decision_time_ns, provider_label=provider_label,
            model_label=model_label, store_path=store_path, executable_path=executable_path,
            policy=policy,
        )
    except StrategyManagerError as exc:
        return _rejected(exc.code)
    except Exception:
        return _rejected("INTERNAL_VALIDATION_FAILED")

    try:
        result = run_controlled_hermes_research(
            prepared.request, backend,  # type: ignore[arg-type]
            executable_path=executable_path, policy=policy, clock=clock,
            hermes_home=hermes_home, strategy_mode=True,
            strategy_parameter_names=prepared.parameter_names,
        )
    except Exception:
        return _rejected("RUNTIME_FAILURE")

    # Revalidate the receipt identity before any strategy run record is constructed.
    if not _receipt_is_bound(result, prepared.request, policy):
        return _rejected("INTERNAL_VALIDATION_FAILED")
    try:
        run = _build_run_record(
            prepared, result.receipt, trigger=trigger, trigger_ref=trigger_ref,
            information_cutoff=information_cutoff, decision_time_ns=decision_time_ns,
        )
    except StrategyManagerError:
        return _rejected("INTERNAL_VALIDATION_FAILED")

    draft = result.validated_draft
    if result.error_code is not None or draft is None:
        code = "STRATEGY_OUTPUT_INVALID" if result.error_code == "STRATEGY_ASSESSMENT_INVALID" else "RUNTIME_FAILURE"
        return _record_run_only(store_path, run, code)
    strategy = draft.strategy_assessment
    if strategy is None:
        return _record_run_only(store_path, run, "STRATEGY_OUTPUT_INVALID")
    if not check_strategy_assessment_consistency(strategy):
        return _record_run_only(store_path, run, "STRATEGY_OUTPUT_INCONSISTENT")
    try:
        assessment = _build_assessment(
            prepared, run, research_summary=draft.research_summary,
            confidence_label=draft.confidence_label, draft=strategy,
        )
    except StrategyManagerError as exc:
        return _record_run_only(store_path, run, exc.code)

    try:
        snapshot = _append_records(store_path, (run, assessment))
    except StrategyManagerError as exc:
        if exc.code in ("ASSESSMENT_PREDECESSOR_STALE", "STORE_LIMIT_EXCEEDED"):
            # The pair rolled back; the run itself is still durably associated.
            return _record_run_only(store_path, run, exc.code)
        return _rejected(exc.code)
    return HermesStrategyManagerResult(
        STATUS_ASSESSMENT_RECORDED, None, run, assessment, snapshot.store_head_entry_hash
    )


__all__ = [
    "ASSESSMENT_ID_PREFIX",
    "ASSESSMENT_TRIGGERS",
    "ERROR_CODES",
    "MANAGER_STATUSES",
    "MAX_EVIDENCE_ITEMS",
    "RECORD_KINDS",
    "RUN_RECORD_ID_PREFIX",
    "STORE_APPLICATION_ID",
    "STORE_FORMAT_ID",
    "HermesStrategyAssessment",
    "HermesStrategyManagerResult",
    "HermesStrategyManagerStoreSnapshot",
    "HermesStrategyRunRecord",
    "StrategyAssessmentEvidence",
    "StrategyManagerError",
    "build_strategy_assessment_evidence",
    "initialize_hermes_strategy_manager_store",
    "load_hermes_strategy_manager_store",
    "record_from_mapping",
    "run_hermes_strategy_assessment",
    "strategy_lifecycle_context_fingerprint",
    "strategy_lifecycle_context_preimage",
    "validate_information_cutoff",
]
