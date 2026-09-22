"""Deterministic blind-first context campaign protocol.

Hermes prose is data.  Only these frozen, content-addressed records and the
append-only :mod:`context_store` may advance a campaign.
"""

from __future__ import annotations

import dataclasses
import json
from types import MappingProxyType
from typing import Mapping, Sequence

from src.data_layer.point_in_time_market_research.research_provenance import (
    canonicalize_utc_timestamp,
)

from .models import canonical_json_bytes, content_address, sha256_hex

CONTEXT_PROTOCOL_VERSION = "hermes-context-protocol/1.0.0"
CONTEXT_STATES = (
    "SCOPE_FROZEN", "BLIND_RESEARCH", "BLIND_FROZEN", "REVEAL_ELIGIBILITY",
    "CONTEXT_REVEALED", "RECONCILIATION", "EVIDENCE_VERIFY",
    "REVISION_REQUIRED", "TERMINAL_FAILED", "TERMINAL_ACCEPTED",
)
TERMINAL_CONTEXT_STATES = frozenset({"TERMINAL_FAILED", "TERMINAL_ACCEPTED"})
_FORWARD = {
    "SCOPE_FROZEN": ("BLIND_RESEARCH",),
    "BLIND_RESEARCH": ("BLIND_FROZEN",),
    "BLIND_FROZEN": ("REVEAL_ELIGIBILITY",),
    "REVEAL_ELIGIBILITY": ("CONTEXT_REVEALED", "TERMINAL_FAILED"),
    "CONTEXT_REVEALED": ("RECONCILIATION",),
    "RECONCILIATION": ("EVIDENCE_VERIFY",),
    "EVIDENCE_VERIFY": ("REVISION_REQUIRED", "TERMINAL_FAILED", "TERMINAL_ACCEPTED"),
    "REVISION_REQUIRED": ("RECONCILIATION",),
    "TERMINAL_FAILED": (),
    "TERMINAL_ACCEPTED": (),
}


class ContextProtocolError(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _fail(code: str) -> ContextProtocolError:
    return ContextProtocolError(code)


def _text(value: object, *, limit: int = 8192) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise _fail("CONTEXT_FIELD_INVALID")
    return value


def _tokens(values: Sequence[str], *, allow_empty: bool = False) -> tuple[str, ...]:
    if isinstance(values, (str, bytes)) or not isinstance(values, Sequence):
        raise _fail("CONTEXT_FIELD_INVALID")
    out = tuple(sorted({_text(value, limit=512) for value in values}))
    if (not allow_empty and not out) or len(out) > 128:
        raise _fail("CONTEXT_FIELD_INVALID")
    return out


def _sha(value: object) -> str:
    if not isinstance(value, str) or len(value) != 64:
        raise _fail("CONTEXT_FIELD_INVALID")
    try:
        int(value, 16)
    except ValueError:
        raise _fail("CONTEXT_FIELD_INVALID") from None
    return value.lower()


def _canonical_scope(value: object) -> tuple[str, str]:
    try:
        parsed = json.loads(value) if isinstance(value, str) else value
        if not isinstance(parsed, Mapping):
            raise ValueError
        raw = canonical_json_bytes(dict(parsed))
    except (TypeError, ValueError, RecursionError):
        raise _fail("CONTEXT_SCOPE_INVALID") from None
    return raw.decode("utf-8"), sha256_hex(raw)


@dataclasses.dataclass(frozen=True)
class ContextCampaignScope:
    campaign_id: str
    schema_version: str
    research_question: str
    subject_refs: tuple[str, ...]
    scope_key: str
    exact_scope_json: str
    exact_scope_sha256: str
    information_cutoff: str
    allowed_public_research_classes: tuple[str, ...]
    requested_provider_label: str
    requested_model_label: str
    policy_id: str
    base_repo_code_identity: str
    advisory_only: bool
    no_execution_authority: bool
    no_risk_authority: bool
    no_credential_authority: bool
    no_order_authority: bool

    @classmethod
    def create(
        cls, *, research_question: str, subject_refs: Sequence[str], scope_key: str,
        exact_scope_json: object, information_cutoff: str,
        allowed_public_research_classes: Sequence[str], requested_provider_label: str,
        requested_model_label: str, policy_id: str, base_repo_code_identity: str,
    ) -> "ContextCampaignScope":
        exact_json, exact_sha = _canonical_scope(exact_scope_json)
        partial = cls(
            "", CONTEXT_PROTOCOL_VERSION, _text(research_question), _tokens(subject_refs),
            _text(scope_key, limit=512), exact_json, exact_sha,
            canonicalize_utc_timestamp(information_cutoff),
            _tokens(allowed_public_research_classes), _text(requested_provider_label, limit=128),
            _text(requested_model_label, limit=128), _text(policy_id, limit=512),
            _text(base_repo_code_identity, limit=512), True, True, True, True, True,
        )
        return dataclasses.replace(
            partial, campaign_id=content_address("contextcampaign:sha256:", partial.identity_fields())
        )

    def identity_fields(self) -> dict[str, object]:
        return {field.name: _json_value(getattr(self, field.name)) for field in dataclasses.fields(self) if field.name != "campaign_id"}


@dataclasses.dataclass(frozen=True)
class ContextCampaignStateRecord:
    state_record_id: str
    schema_version: str
    campaign_id: str
    state: str
    predecessor_state_record_id: str | None
    caused_by_artifact_id: str | None
    revision_ordinal: int

    @classmethod
    def create(
        cls, *, campaign_id: str, state: str,
        predecessor: "ContextCampaignStateRecord | None" = None,
        caused_by_artifact_id: str | None = None, revision_ordinal: int = 0,
    ) -> "ContextCampaignStateRecord":
        if state not in CONTEXT_STATES or isinstance(revision_ordinal, bool) or revision_ordinal < 0:
            raise _fail("STATE_TRANSITION_INVALID")
        if predecessor is None:
            if state != "SCOPE_FROZEN":
                raise _fail("STATE_TRANSITION_INVALID")
            predecessor_id = None
        else:
            if predecessor.campaign_id != campaign_id or state not in _FORWARD[predecessor.state]:
                raise _fail("STATE_TRANSITION_INVALID")
            if predecessor.state == "REVISION_REQUIRED" and state == "RECONCILIATION" and not caused_by_artifact_id:
                raise _fail("REVISION_ARTIFACT_REQUIRED")
            predecessor_id = predecessor.state_record_id
        partial = cls("", CONTEXT_PROTOCOL_VERSION, _text(campaign_id, limit=512), state, predecessor_id, caused_by_artifact_id, revision_ordinal)
        return dataclasses.replace(partial, state_record_id=content_address("contextstate:sha256:", partial.identity_fields()))

    def identity_fields(self) -> dict[str, object]:
        return {field.name: getattr(self, field.name) for field in dataclasses.fields(self) if field.name != "state_record_id"}


@dataclasses.dataclass(frozen=True)
class BlindResearchArtifact:
    blind_artifact_id: str
    schema_version: str
    campaign_id: str
    scope_key: str
    exact_scope_sha256: str
    information_cutoff: str
    blind_request_id: str
    prompt_envelope_sha256: str
    context_output_contract_sha256: str
    validated_draft_sha256: str
    source_reference_digests: tuple[str, ...]
    context_claims_sha256: str
    session_evidence_id: str | None
    alpha_context_present: bool
    reveal_set_id: None
    predecessor_state_record_id: str

    @classmethod
    def create(cls, *, campaign: ContextCampaignScope, blind_request_id: str,
               prompt_envelope_sha256: str, context_output_contract_sha256: str,
               validated_draft_sha256: str, source_reference_digests: Sequence[str],
               context_claims_sha256: str, session_evidence_id: str | None,
               predecessor_state_record_id: str) -> "BlindResearchArtifact":
        partial = cls(
            "", CONTEXT_PROTOCOL_VERSION, campaign.campaign_id, campaign.scope_key,
            campaign.exact_scope_sha256, campaign.information_cutoff,
            _text(blind_request_id, limit=512), _sha(prompt_envelope_sha256),
            _sha(context_output_contract_sha256), _sha(validated_draft_sha256),
            tuple(sorted(_sha(item) for item in source_reference_digests)),
            _sha(context_claims_sha256), session_evidence_id, False, None,
            _text(predecessor_state_record_id, limit=512),
        )
        return dataclasses.replace(partial, blind_artifact_id=content_address("blindartifact:sha256:", artifact_identity_fields(partial)))


@dataclasses.dataclass(frozen=True)
class RevealEligibilityRecord:
    reveal_eligibility_id: str
    schema_version: str
    campaign_id: str
    blind_artifact_id: str
    registry_head_hash: str
    eligible_record_ids: tuple[str, ...]
    manifest_ids: tuple[str, ...]
    admissibility_digest: str
    predecessor_state_record_id: str


@dataclasses.dataclass(frozen=True)
class RevealedContextSet:
    reveal_set_id: str
    schema_version: str
    campaign_id: str
    blind_artifact_id: str
    information_cutoff: str
    registry_head_hash: str
    entry_bindings: tuple[Mapping[str, object], ...]
    provenance_manifest_ids: tuple[str, ...]
    replay_results: tuple[Mapping[str, object], ...]
    dependency_record_ids: tuple[str, ...]
    untrusted_context_json: str
    predecessor_state_record_id: str


@dataclasses.dataclass(frozen=True)
class ContextResearchRevision:
    revision_id: str
    schema_version: str
    campaign_id: str
    blind_artifact_id: str
    reveal_set_id: str
    predecessor_reconciliation_id: str | None
    revision_ordinal: int
    context_output_contract_sha256: str
    validated_draft_sha256: str
    claim_graph_sha256: str

    @classmethod
    def create(cls, **values: object) -> "ContextResearchRevision":
        partial = cls(revision_id="", schema_version=CONTEXT_PROTOCOL_VERSION, **values)  # type: ignore[arg-type]
        return dataclasses.replace(partial, revision_id=content_address("contextrevision:sha256:", artifact_identity_fields(partial)))


@dataclasses.dataclass(frozen=True)
class EvidenceVerificationRecord:
    verification_id: str
    schema_version: str
    campaign_id: str
    reconciliation_id: str
    context_output_contract_sha256: str
    structural_validity: str
    substantive_research_quality: str
    claim_dispositions: tuple[Mapping[str, object], ...]
    falsification_results: tuple[Mapping[str, object], ...]
    unsupported_claim_count: int
    unexpected_tool_names: tuple[str, ...]
    predecessor_state_record_id: str

    @classmethod
    def create(cls, **values: object) -> "EvidenceVerificationRecord":
        for key in ("claim_dispositions", "falsification_results"):
            raw = values.get(key)
            if isinstance(raw, tuple):
                values[key] = tuple(_freeze_value(item) for item in raw)
        partial = cls(verification_id="", schema_version=CONTEXT_PROTOCOL_VERSION, **values)  # type: ignore[arg-type]
        return dataclasses.replace(partial, verification_id=content_address("contextverification:sha256:", artifact_identity_fields(partial)))


@dataclasses.dataclass(frozen=True)
class ContextTerminalDisposition:
    terminal_disposition_id: str
    schema_version: str
    campaign_id: str
    verification_id: str
    terminal_state: str
    context_output_contract_sha256: str
    predecessor_state_record_id: str

    @classmethod
    def create(cls, **values: object) -> "ContextTerminalDisposition":
        state = values.get("terminal_state")
        if state not in TERMINAL_CONTEXT_STATES:
            raise _fail("STATE_TRANSITION_INVALID")
        partial = cls(terminal_disposition_id="", schema_version=CONTEXT_PROTOCOL_VERSION, **values)  # type: ignore[arg-type]
        return dataclasses.replace(partial, terminal_disposition_id=content_address("contextterminal:sha256:", artifact_identity_fields(partial)))


def _json_value(value: object) -> object:
    if dataclasses.is_dataclass(value):
        return {field.name: _json_value(getattr(value, field.name)) for field in dataclasses.fields(value)}
    if isinstance(value, tuple):
        return [_json_value(item) for item in value]
    if isinstance(value, Mapping):
        return {str(key): _json_value(item) for key, item in sorted(value.items())}
    return value


def _freeze_value(value: object) -> object:
    if isinstance(value, Mapping):
        return MappingProxyType({str(key): _freeze_value(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_value(item) for item in value)
    return value


def artifact_identity_fields(record: object) -> dict[str, object]:
    if not dataclasses.is_dataclass(record):
        raise _fail("CONTEXT_ARTIFACT_INVALID")
    fields = dataclasses.fields(record)
    id_names = {field.name for field in fields if field.name.endswith("_id") and field.name.split("_")[0] in {"blind", "reveal", "revision", "verification", "terminal"}}
    # Each record has exactly one own derived id as its first field.
    own_id = fields[0].name
    return {field.name: _json_value(getattr(record, field.name)) for field in fields if field.name != own_id}


def artifact_mapping(record: object) -> dict[str, object]:
    if not dataclasses.is_dataclass(record):
        raise _fail("CONTEXT_ARTIFACT_INVALID")
    return {field.name: _json_value(getattr(record, field.name)) for field in dataclasses.fields(record)}


def artifact_id(record: object) -> str:
    if not dataclasses.is_dataclass(record):
        raise _fail("CONTEXT_ARTIFACT_INVALID")
    value = getattr(record, dataclasses.fields(record)[0].name)
    return _text(value, limit=512)
