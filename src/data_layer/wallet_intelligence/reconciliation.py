"""API / chain reconciliation for public wallet evidence (S10-WALLET-01).

Reconciliation is APPEND-ONLY: it emits immutable links and never destructively
rewrites original evidence. It preserves chain-native identity, deterministic
ordering, finality/reorg representation, and the strict rule that weak
similarity (same wallet, nearby time, similar amount) never silently merges
distinct events.

Posture: local, offline, stdlib-only, deterministic, in-memory. No network,
credentials, indexer, or execution authority. Chain acquisition is a separately
gated adapter; this module normalizes explicit LOCAL chain observations only.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from .contracts import (
    _FINALITY_SET,
    WalletContractError,
    WalletEvidenceEvent,
    WalletReconciliationLink,
    build_wallet_reconciliation_link,
    canonicalize_identifier,
)

# Re-export the reconciliation/finality vocabularies for consumers.
from .contracts import RECONCILIATION_STATES, RECONCILIATION_RELATION_KINDS  # noqa: F401


RECONCILIATION_LABEL = "PUBLIC_WALLET_API_CHAIN_RECONCILIATION"
RECONCILIATION_POSTURE = "LOCAL_OFFLINE_APPEND_ONLY_DETERMINISTIC"

# Economic fields that are directly comparable across observations. combo_state
# is intentionally EXCLUDED: UNKNOWN vs FALSE/TRUE is a labeling difference, not a
# proven economic disagreement.
_COMPARABLE_ECONOMIC_FIELDS = (
    "price",
    "size",
    "notional",
    "side",
    "condition_value",
    "token_value",
)


def _err(code: str) -> WalletContractError:
    return WalletContractError(code)


# ---------------------------------------------------------------------------
# Chain event evidence (11 - preserve explicit public chain observation fields).
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ChainEventEvidence:
    chain_id: int
    block_number: int
    block_hash: str
    transaction_hash: str
    transaction_index: int
    log_index: int
    removed: bool
    finality_state: str
    confirmation_or_finality_time: str | None

    def native_identity(self) -> tuple[int, str, int]:
        return (self.chain_id, self.transaction_hash, self.log_index)

    def ordering_key(self) -> tuple[int, int, int]:
        return (self.block_number, self.transaction_index, self.log_index)


def build_chain_event_evidence(
    *,
    chain_id: int,
    block_number: int,
    block_hash: str,
    transaction_hash: str,
    transaction_index: int,
    log_index: int,
    removed: bool = False,
    finality_state: str = "UNKNOWN",
    confirmation_or_finality_time: str | None = None,
) -> ChainEventEvidence:
    for name, value in (
        ("chain_id", chain_id),
        ("block_number", block_number),
        ("transaction_index", transaction_index),
        ("log_index", log_index),
    ):
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise _err("FIELD_VALUE")
    if not isinstance(removed, bool):
        raise _err("FIELD_TYPE")
    finality = finality_state if finality_state in _FINALITY_SET else None
    if finality is None:
        raise _err("FIELD_VALUE")
    if confirmation_or_finality_time is not None and not isinstance(
        confirmation_or_finality_time, str
    ):
        raise _err("FIELD_TYPE")
    return ChainEventEvidence(
        chain_id=chain_id,
        block_number=block_number,
        block_hash=canonicalize_identifier("BLOCK_HASH", block_hash),
        transaction_hash=canonicalize_identifier("TRANSACTION_HASH", transaction_hash),
        transaction_index=transaction_index,
        log_index=log_index,
        removed=removed,
        finality_state=finality,
        confirmation_or_finality_time=confirmation_or_finality_time,
    )


def order_chain_evidence(
    events: Sequence[ChainEventEvidence],
) -> tuple[ChainEventEvidence, ...]:
    """Deterministically order chain evidence by (block_number, transaction_index,
    log_index). A shared block timestamp never collapses distinct logs."""

    return tuple(sorted(events, key=lambda e: e.ordering_key() + (e.transaction_hash,)))


def dedupe_chain_evidence(
    events: Sequence[ChainEventEvidence],
) -> tuple[ChainEventEvidence, ...]:
    """Dedupe strictly by chain-native identity (chain_id, tx_hash, log_index).

    The same transaction with different log indices yields distinct entries; two
    logs sharing a timestamp are never merged.
    """

    seen: dict[tuple[int, str, int], ChainEventEvidence] = {}
    for event in order_chain_evidence(events):
        key = event.native_identity()
        if key not in seen:
            seen[key] = event
    return tuple(seen.values())


# ---------------------------------------------------------------------------
# Finality policy (versioned/configurable; no hardcoded block-count assumption).
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class FinalityPolicy:
    policy_version: str
    min_confirmations_for_confirmed: int
    min_confirmations_for_finalized: int

    def validate(self) -> None:
        if not isinstance(self.policy_version, str) or not self.policy_version:
            raise _err("FIELD_VALUE")
        for value in (
            self.min_confirmations_for_confirmed,
            self.min_confirmations_for_finalized,
        ):
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise _err("FIELD_VALUE")


def classify_finality(confirmations: int, policy: FinalityPolicy, *, removed: bool = False) -> str:
    """Classify finality ONLY under an explicit, versioned policy. There is no
    default block-count folklore; callers with no policy leave finality UNKNOWN."""

    policy.validate()
    if removed:
        return "REORGED"
    if not isinstance(confirmations, int) or isinstance(confirmations, bool) or confirmations < 0:
        raise _err("FIELD_VALUE")
    if confirmations >= policy.min_confirmations_for_finalized:
        return "FINALIZED"
    if confirmations >= policy.min_confirmations_for_confirmed:
        return "CONFIRMED"
    return "UNFINALIZED"


# ---------------------------------------------------------------------------
# Event equivalence / disagreement assessment (11 / 11.1 / 15.7 / R-V2-03).
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ReconciliationAssessment:
    same_event: bool
    reconciliation_state: str
    relation_kind: str
    dq_flags: tuple[str, ...]
    conflict_fields: tuple[str, ...]


def _strong_identity(event: WalletEvidenceEvent):
    if (
        event.transaction_hash is not None
        and event.log_index is not None
        and event.chain_id is not None
    ):
        return ("chain", event.chain_id, event.transaction_hash, event.log_index)
    if event.native_event_id and event.source_system_family:
        return ("api", event.source_system_family, event.native_event_id)
    return None


def _comparable_conflicts(a: WalletEvidenceEvent, b: WalletEvidenceEvent) -> tuple[str, ...]:
    conflicts: list[str] = []
    for field_name in _COMPARABLE_ECONOMIC_FIELDS:
        va = getattr(a, field_name)
        vb = getattr(b, field_name)
        if va is not None and vb is not None and va != vb:
            conflicts.append(field_name)
    # A condition/token value only conflicts when its context also matches; a
    # different context is a different namespace, not a disagreement.
    if "condition_value" in conflicts and a.condition_context != b.condition_context:
        conflicts.remove("condition_value")
    if "token_value" in conflicts and a.token_context != b.token_context:
        conflicts.remove("token_value")
    return tuple(conflicts)


def assess_event_equivalence(
    event_a: WalletEvidenceEvent,
    event_b: WalletEvidenceEvent,
    *,
    deterministic_protocol_relation: bool = False,
) -> ReconciliationAssessment:
    """Decide whether two canonical events are the same underlying economic event.

    Same wallet + same canonical event type + strong deterministic native/chain
    identity (or matching protocol-object key, or an explicit deterministic
    protocol relation) + no conflicting canonical economics => one event.
    Weak similarity alone never merges; material conflict is SOURCE_DISAGREEMENT.
    """

    if not isinstance(event_a, WalletEvidenceEvent) or not isinstance(
        event_b, WalletEvidenceEvent
    ):
        raise _err("FIELD_TYPE")

    if event_a.canonical_wallet != event_b.canonical_wallet or (
        event_a.canonical_event_type != event_b.canonical_event_type
    ):
        return ReconciliationAssessment(
            same_event=False,
            reconciliation_state="UNRESOLVED",
            relation_kind="UNRESOLVED",
            dq_flags=("IDENTITY_AMBIGUOUS",),
            conflict_fields=(),
        )

    conflicts = _comparable_conflicts(event_a, event_b)
    if conflicts:
        return ReconciliationAssessment(
            same_event=False,
            reconciliation_state="SOURCE_DISAGREEMENT",
            relation_kind="DISAGREEMENT",
            dq_flags=("SOURCE_DISAGREEMENT",),
            conflict_fields=conflicts,
        )

    strong_a = _strong_identity(event_a)
    strong_b = _strong_identity(event_b)
    strong_match = strong_a is not None and strong_a == strong_b
    object_key_match = bool(event_a.economic_object_key) and (
        event_a.economic_object_key == event_b.economic_object_key
    )

    if strong_match or object_key_match or deterministic_protocol_relation:
        strengths = {event_a.identity_strength, event_b.identity_strength}
        has_chain = "CHAIN_NATIVE_STRONG" in strengths
        has_api = bool(
            strengths & {"API_NATIVE_STRONG", "SOURCE_CONTENT_DERIVED", "WEAK_PARTIAL"}
        )
        if has_chain and has_api:
            state, relation = "API_AND_CHAIN_CONFIRMED", "CHAIN_CONFIRMATION"
        elif has_chain:
            state, relation = "CHAIN_ONLY", "SAME_EVENT_EQUIVALENCE"
        else:
            state, relation = "API_ONLY", "SAME_EVENT_EQUIVALENCE"
        return ReconciliationAssessment(
            same_event=True,
            reconciliation_state=state,
            relation_kind=relation,
            dq_flags=("OK",),
            conflict_fields=(),
        )

    # Same wallet/type, no conflict, but no strong identity evidence: do NOT merge.
    return ReconciliationAssessment(
        same_event=False,
        reconciliation_state="UNRESOLVED",
        relation_kind="UNRESOLVED",
        dq_flags=("IDENTITY_AMBIGUOUS",),
        conflict_fields=(),
    )


def build_reconciliation_link_from_assessment(
    event_a: WalletEvidenceEvent,
    event_b: WalletEvidenceEvent,
    assessment: ReconciliationAssessment,
    *,
    finality_state: str = "UNKNOWN",
    notes: str = "",
) -> WalletReconciliationLink:
    """Emit an append-only reconciliation link for an assessed event pair."""

    return build_wallet_reconciliation_link(
        reconciliation_state=assessment.reconciliation_state,
        relation_kind=assessment.relation_kind,
        event_ids=(event_a.wallet_event_id, event_b.wallet_event_id),
        finality_state=finality_state,
        notes=notes,
    )


def build_supersession_link(
    *,
    predecessor_event_id: str,
    successor_event_id: str,
    notes: str = "",
) -> WalletReconciliationLink:
    """Append-only supersession link: a corrected source becomes a new observation
    linked to the prior one. The prior evidence remains retrievable."""

    if predecessor_event_id == successor_event_id:
        raise _err("RECONCILIATION")
    return build_wallet_reconciliation_link(
        reconciliation_state="SUPERSEDED_BY_STRONGER_EVIDENCE",
        relation_kind="SUPERSESSION",
        event_ids=(predecessor_event_id, successor_event_id),
        predecessor_event_id=predecessor_event_id,
        successor_event_id=successor_event_id,
        notes=notes,
    )
