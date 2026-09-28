"""Manual foreground operator for S10-GATE-AF1.

All commands are local by default.  The only command capable of activating the
existing bounded public-population / controlled-research surfaces is ``run-real``;
it requires the separately approved activation envelope and two explicit opt-ins.

Exact command grammar (every ``--workspace`` is resolved beneath
``local_data/s10_gate_af1/`` of this repository):

  prepare             --workspace W
  run-real            --workspace W --activation-envelope W/AF1_RUNTIME_AUTHORIZATION_ENVELOPE.json
                      --provider-label P --model-label M
                      --acknowledgement I_AUTHORIZE_EXACT_S10_GATE_AF1_RUNTIME_ENVELOPE
                      --allow-public-network --allow-hermes-provider
                      --hermes-executable ABSOLUTE_EXE --hermes-home ABSOLUTE_RESEARCH_HOME
  verify-run          --workspace W
  build-review-bundle --workspace W
  verify-review       --workspace W --review W/AF1_SIDE12_BLIND_REVIEW_DECISION.json
  finalize            --workspace W [--review W/AF1_SIDE12_BLIND_REVIEW_DECISION.json]
  verify-final        --evidence docs/gate_evidence/S10-GATE-AF1/af1_gate_evidence.json

``--hermes-executable`` and ``--hermes-home`` are machine-local, noncanonical runtime
launch parameters.  Both are validated, and the pinned executable passes the existing
offline version and startup probes, BEFORE the population sentinel exists: any failure
is PHASE_B_LOCAL_EVIDENCE_DEFECT with zero calls and the attempt stays unconsumed.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, fields
from decimal import Decimal, InvalidOperation
import hashlib
import json
import os
from pathlib import Path
import re
import sys
from typing import Callable, Mapping, Sequence
import zipfile

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.data_layer.analytical_research.alpha_discovery import (  # noqa: E402
    AlphaResearchQueueSnapshot,
    AlphaDiscoveryPolicy,
    AlphaUniverseSnapshot,
    MarketTriageDecision,
    ObservedMarketState,
    allocate_and_finalize_research_queue,
    build_alpha_discovery_policy,
    build_alpha_universe_snapshot,
    build_pre_allocation_triage_bases,
)
from src.data_layer.analytical_research.alpha_factory_gate import (  # noqa: E402
    AF1_A1_REASON,
    AF1_A2_REASON,
    AF1_REAL_CASE_IDS,
    AF1_REAL_CASE_TERMINAL_REASONS,
    AF1_REVIEW_COMPLETED_REASON,
    AF1_REVIEW_LABELS,
    AF1_REVIEW_REASON_CODES,
    AF1_REVIEW_SLOTS,
    AF1_RUNTIME_UNAVAILABLE_REASON,
    AF1_SCHEMA_VERSION,
    AF1_SEEDED_CASE_IDS,
    AF1BenchmarkManifest,
    AF1BlindReviewRecord,
    AF1GateReceipt,
    AF1RealCaseEvidence,
    AF1SeededCaseResult,
    af1_record_from_mapping,
    af1_record_to_mapping,
    build_af1_benchmark_manifest,
    build_af1_blind_review_record,
    build_af1_gate_receipt,
    build_af1_real_case_evidence,
    canonical_json_bytes,
    derive_af1_dimension_statuses,
    evaluate_seeded_af1_cases,
)
from src.data_layer.point_in_time_market_research import (  # noqa: E402
    initialize_manifest_store,
    initialize_point_in_time_record_store,
    load_and_verify_manifest_store,
    load_and_verify_point_in_time_record_store,
)
from src.data_layer.point_in_time_market_research.polymarket_public_population import (  # noqa: E402
    PolymarketPublicPopulationConfig,
    PolymarketPublicPopulationResult,
    populate_initial_polymarket_public_data,
)
from src.data_layer.point_in_time_market_research.research_provenance import (  # noqa: E402
    canonicalize_utc_timestamp,
)
from src.research_runtime.hermes_controlled_runtime import (  # noqa: E402
    DEFAULT_HERMES_INVOCATION_POLICY,
    KNOWN_COST_STATUSES,
    ContextCampaignScope,
    ContextArtifactStore,
    ExternalHermesCliBackend,
    HermesResearchRunReceipt,
    build_version_argv,
    is_clean_research_home_control_plane,
    is_safe_research_home,
    is_supported_hermes_version,
    run_blind_phase,
)
from src.research_runtime.hermes_controlled_runtime.controller import (  # noqa: E402
    _STARTUP_PROBE_MAX_BYTES,
    _STARTUP_PROBE_MAX_SECONDS,
    _VERSION_PROBE_MAX_BYTES,
    _VERSION_PROBE_MAX_SECONDS,
    build_startup_argv,
)
from src.research_runtime.hermes_controlled_runtime.policy import (  # noqa: E402
    PolicyBroadeningError,
    validate_executable_path,
)


WP_ID = "S10-GATE-AF1"
# Current certified base: PR #195 (S10-HERMES-CTX-03) merge commit. PR #194
# (S10-HERMES-CTX-02, merge 15097f70f5f5358879fde73b2b30d26ecdb80402) and the WP164A runtime
# dependency (PR #193, runtime-certified head 1c7de22f31cd093771d6bc0748c440ad5284b105,
# merge 70f867bdcd5e97b0dc05d4008c2c023feb461658) are ancestors of this base.
BASE_SHA = "1ccf42df0e95586b98c79a0bf912343f9c34df31"
PREDECESSOR_PR = 195
PREDECESSOR_HEAD_SHA = "ddc25d189359b6e365edcf08c762cb0552b7170a"
PREDECESSOR_MERGE_SHA = BASE_SHA
RUNTIME_ACKNOWLEDGEMENT = "I_AUTHORIZE_EXACT_S10_GATE_AF1_RUNTIME_ENVELOPE"
ACTIVATION_ENVELOPE_SCHEMA_ID = "s10-gate-af1-runtime-authorization-envelope"
ACTIVATION_ENVELOPE_SCHEMA_VERSION = "1.0.0"
WORKSPACE_ROOT_PARTS = ("local_data", "s10_gate_af1")
ATTEMPT_DIRECTORY_RE = re.compile(r"^attempt-[0-9]{2}$")
# Historical, permanently consumed attempts. Attempt-03 was consumed at Phase-A head
# 777b33d5e3eb3ae6814716f45f3dc6a8a673ed16 (TRUE_STOP / PHASE_B_LOCAL_EVIDENCE_DEFECT, AF1 gate
# result NONE) and can never be reused, renamed or replayed.
CONSUMED_ATTEMPT_DIRECTORIES = frozenset({"attempt-01", "attempt-02", "attempt-03"})
# The only runtime instance this Phase-A head can ever serve. There is no automatic
# attempt increment: a later attempt requires a new Phase-A package and authorization.
AUTHORIZED_ATTEMPT_DIRECTORY = "attempt-04"
ACTIVATION_ENVELOPE_FILENAME = "AF1_RUNTIME_AUTHORIZATION_ENVELOPE.json"
POPULATION_INVOCATION_FILENAME = "AF1_PUBLIC_POPULATION_INVOCATION.json"
POPULATION_RESULT_FILENAME = "AF1_PUBLIC_POPULATION_RESULT.json"
RUNTIME_RESULT_FILENAME = "AF1_RUNTIME_RESULT.json"
PREPARE_FILENAME = "AF1_PREPARE.json"
REVIEW_BUNDLE_FILENAME = "AF1_BLIND_REVIEW_BUNDLE.zip"
REVIEW_DECISION_FILENAME = "AF1_SIDE12_BLIND_REVIEW_DECISION.json"
FINAL_EVIDENCE_FILENAME = "AF1_FINAL_GATE_EVIDENCE.json"
RECORD_STORE_FILENAME = "pit_records.sqlite3"
MANIFEST_STORE_FILENAME = "pit_manifests.sqlite3"
CONTEXT_STORE_DIRNAME = "context_artifacts"
REVIEW_INSTRUCTIONS_NAME = "00_REVIEW_INSTRUCTIONS.txt"
REVIEW_WRAPPER_SCHEMA_ID = "s10-gate-af1-blind-review-wrapper"
REVIEW_DECISION_SCHEMA_ID = "s10-gate-af1-side12-blind-review-decision"
FROZEN_CONTRACT_PATHS = (
    ("wp_prompt_sha256", "docs/wp_specs/S10-GATE-AF1/wp_prompt.txt"),
    ("wp_spec_sha256", "docs/wp_specs/S10-GATE-AF1/wp_spec.json"),
    ("gate_contract_sha256", "docs/alpha_factory_research_system_gate_contract.md"),
)
RESEARCH_QUESTION = (
    "Independently research the public, resolution-relevant evidence for this exact "
    "market scope. Identify material supporting and contradicting evidence, "
    "uncertainties, falsification checks, known missing information, and what would "
    "change the conclusion."
)
WP164_LABELS = {
    "manifest_id": "manifest:s10-gate-af1:benchmark:1.0.0",
    "parameter_set_id": "params:s10-gate-af1:benchmark-population:1.0.0",
    "normalizer_version": "normalizer:s10-gate-af1:wp164:1.0.0",
    "validator_version": "validator:s10-gate-af1:wp164:1.0.0",
}
MARKETS_LIMIT = 25
ORDER_BOOKS_LIMIT = 1
MAX_AF1_CASE_CALLS = 3
MAX_CASE_COST_USD = Decimal("5")
MAX_AGGREGATE_COST_USD = Decimal("15")
# The exact current merged WP164A PolymarketPublicPopulationResult field contract.
POPULATION_RESULT_FIELDS = (
    "is_valid", "status", "error_codes", "record_store_error_codes",
    "registration_error_codes", "warning_codes", "snapshot_id", "captured_at_utc",
    "requested_markets_limit", "bounded_markets_limit", "requested_order_books_limit",
    "bounded_order_books_limit", "fetched_market_count", "fetched_order_book_count",
    "built_record_count", "inserted_record_count", "dataset_snapshot_reference_id",
    "manifest_entry_id", "record_store_status", "registration_status", "network_used",
    "recovery_required", "advisory_only", "no_execution_authority", "batch_is_valid",
    "batch_status", "batch_error_codes", "batch_warning_codes",
    "batch_accepted_record_version_ids", "batch_exact_duplicate_record_version_ids",
    "batch_quarantined_record_version_ids", "canonical_batch_sha256",
    "build_failure_observation_kind", "build_status", "build_error_codes",
    "build_warning_codes", "build_quarantine_id", "build_input_fingerprint_sha256",
)
_POPULATION_RESULT_KEYS = frozenset(POPULATION_RESULT_FIELDS)
A1_ERROR_TUPLES = (("POPULATION_FETCH_FAILED",), ("POPULATION_RESPONSE_INVALID",))
HERMES_TERMINAL_MAP = {
    "TRANSPORT_FAILURE": AF1_RUNTIME_UNAVAILABLE_REASON,
    "TIMEOUT": AF1_RUNTIME_UNAVAILABLE_REASON,
    "EXIT_CODE_NONZERO": AF1_RUNTIME_UNAVAILABLE_REASON,
    "RESPONSE_CAPTURE_FAILED": "RESEARCH_OUTPUT_INVALID",
    "OUTPUT_SCHEMA_INVALID": "RESEARCH_OUTPUT_INVALID",
    "SAFETY_VALIDATION_FAILED": "RESEARCH_OUTPUT_INVALID",
    "USAGE_EVIDENCE_INVALID": "USAGE_EVIDENCE_INVALID",
    "PROVIDER_MODEL_MISMATCH": "PROVIDER_MODEL_MISMATCH",
    "COST_EVIDENCE_UNAVAILABLE": "SUCCESSFUL_RUN_COST_UNKNOWN",
    "BUDGET_EXCEEDED": "CASE_COST_LIMIT_BREACH",
}
LOCAL_DEFECT_STATUSES = frozenset({"VERSION_MISMATCH", "STARTUP_PREFLIGHT_FAILED"})
ACTIVATION_ENVELOPE_KEYS = frozenset({
    "schema_id", "schema_version", "wp_id", "base_sha", "phase_a_commit_sha",
    "wp_prompt_sha256", "wp_spec_sha256", "gate_contract_sha256",
    "workspace_attempt_id", "provider_label", "model_label",
    "hermes_invocation_policy_id", "manifest_id", "parameter_set_id",
    "normalizer_version", "validator_version", "markets_limit",
    "order_books_limit", "analysis_temporal_mode", "alpha_memory_temporal_posture",
    "alpha_registry_path", "alpha_registry_head_entry_hash", "max_provider_calls",
    "max_case_cost_usd", "max_aggregate_cost_usd", "retry_limit",
    "provider_model_fallback", "replacement_benchmark_case", "fourth_call_authorized",
    "credentials_authorized", "scheduler_authorized",
    "strategy_qualification_economics_authorized", "paper_execution_authorized",
    "live_execution_authorized", "gate_c_authorized", "signing_or_orders_authorized",
    "h1_fifth_invocation_authorized", "merge_authorized",
})
_AUTHORITY_FLAGS = {
    "advisory_only": True, "human_review_required": True, "no_execution_authority": True,
    "no_strategy_authority": True, "no_qualification_authority": True,
}
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
REVIEW_INSTRUCTIONS = (
    "S10-GATE-AF1 blinded research-usefulness review.\n"
    "Review REVIEW-01, REVIEW-02 and REVIEW-03 independently. Each file contains one\n"
    "opaque review_slot, its review_body_sha256 and the review_body. Judge research\n"
    "usefulness only; this review grants no trading, qualification or merge authority.\n"
    "Return one JSON decision with exactly: schema_id="
    + REVIEW_DECISION_SCHEMA_ID + ", schema_version=1.0.0, reviewer_alias=SIDE12,\n"
    "reviews=[three objects with exactly review_slot, review_body_sha256, label,\n"
    "reason_codes (nonempty)].\n"
    "Labels: " + ", ".join(AF1_REVIEW_LABELS) + ".\n"
    "Reason codes: " + ", ".join(AF1_REVIEW_REASON_CODES) + ".\n"
)


class AF1OperatorError(RuntimeError):
    """Closed, sanitized operator stop.

    ``str(error)`` is always the closed stop code; ``reason`` optionally carries a
    precise internal diagnostic (never a path, credential or raw output).
    """

    def __init__(self, code: str, reason: str | None = None) -> None:
        super().__init__(code)
        self.reason = reason


def raw_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_sha256(value: object) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _strict_equal(left: object, right: object) -> bool:
    # bool is an int subclass; ``0 == False`` must never satisfy a closed field.
    return type(left) is type(right) and left == right


def _is_sha256(value: object) -> bool:
    return isinstance(value, str) and _SHA256_RE.fullmatch(value) is not None


def _is_commit(value: object) -> bool:
    return isinstance(value, str) and _COMMIT_RE.fullmatch(value) is not None


def _repo_root(repo_root: Path | None) -> Path:
    return Path(repo_root if repo_root is not None else REPO_ROOT).resolve()


def frozen_contract_digests(repo_root: Path | None = None) -> dict[str, str]:
    """Raw-byte SHA-256 of the three frozen gate-criterion files."""
    root = _repo_root(repo_root)
    return {key: raw_sha256(root / relative) for key, relative in FROZEN_CONTRACT_PATHS}


# ── Workspace boundary ────────────────────────────────────────────────────────


def resolve_workspace(raw: object, *, repo_root: Path | None = None) -> Path:
    """Resolve a caller-selected workspace strictly beneath local_data/s10_gate_af1.

    A relative argument is interpreted against the repository root, so the intended
    repository-root invocation always yields an absolute workspace.  ``..`` parts,
    symlinked components and any path outside the boundary are rejected.
    """
    root = _repo_root(repo_root)
    boundary = root.joinpath(*WORKSPACE_ROOT_PARTS)
    raw_path = Path(os.fspath(raw)) if isinstance(raw, (str, os.PathLike)) else None
    if raw_path is None or ".." in raw_path.parts or not raw_path.parts:
        raise AF1OperatorError("WORKSPACE_PATH_INVALID")
    candidate = raw_path if raw_path.is_absolute() else root / raw_path
    if boundary.resolve(strict=False) != boundary:
        raise AF1OperatorError("WORKSPACE_PATH_ESCAPE")
    resolved = candidate.resolve(strict=False)
    try:
        relative = resolved.relative_to(boundary)
    except ValueError:
        raise AF1OperatorError("WORKSPACE_OUTSIDE_LOCAL_DATA") from None
    if not relative.parts:
        raise AF1OperatorError("WORKSPACE_PATH_INVALID")
    current = boundary
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise AF1OperatorError("WORKSPACE_PATH_ESCAPE")
    return resolved


def context_store_root(workspace: Path, ordinal: int) -> Path:
    """Absolute per-case ContextArtifactStore root beneath the resolved workspace."""
    if not workspace.is_absolute() or ".." in workspace.parts:
        raise AF1OperatorError("WORKSPACE_PATH_INVALID")
    if ordinal not in range(1, MAX_AF1_CASE_CALLS + 1):
        raise AF1OperatorError("PHASE_B_LOCAL_EVIDENCE_DEFECT")
    child = workspace / CONTEXT_STORE_DIRNAME / f"case-{ordinal}"
    current = workspace
    for part in (CONTEXT_STORE_DIRNAME, f"case-{ordinal}"):
        current = current / part
        if current.is_symlink():
            raise AF1OperatorError("WORKSPACE_PATH_ESCAPE")
    if child.resolve(strict=False).parent.parent != workspace.resolve(strict=False):
        raise AF1OperatorError("WORKSPACE_PATH_ESCAPE")
    return child


# ── Fixed benchmark configuration ─────────────────────────────────────────────


def benchmark_population_config(*, allow_network: bool) -> PolymarketPublicPopulationConfig:
    return PolymarketPublicPopulationConfig(
        **WP164_LABELS, markets_limit=MARKETS_LIMIT, order_books_limit=ORDER_BOOKS_LIMIT,
        allow_network=allow_network,
    )


def benchmark_discovery_policy() -> AlphaDiscoveryPolicy:
    result = build_alpha_discovery_policy({
        "schema_version": "1.0.0",
        "policy_version": "BENCHMARK_STARTING_POLICY_NOT_EMPIRICALLY_CALIBRATED",
        "eligible_market_statuses": ["open"],
        "metadata_freshness_seconds": 60,
        "order_book_freshness_seconds": 30,
        "resolution_rule_freshness_seconds": 120,
        "soft_last_trade_price_abs_delta": "0.1",
        "soft_mid_price_abs_delta": "0.1",
        "soft_spread_abs_delta": "0.05",
        "soft_top_depth_relative_delta": "0.25",
        "queue_capacity": 3,
        "exploration_slots": 1,
        "audit_slots": 1,
        "max_per_category": 2,
        "audit_seed": "s10-gate-af1-v1",
        "research_archetype_taxonomy_version": "alpha-archetypes/1",
        "advisory_only": True,
        "no_execution_authority": True,
        "no_strategy_authority": True,
        "no_qualification_authority": True,
    })
    if not result.is_valid or not isinstance(result.record, AlphaDiscoveryPolicy):
        raise AF1OperatorError("PHASE_B_LOCAL_EVIDENCE_DEFECT")
    return result.record


# ── Exact HERMES-CTX case scope ───────────────────────────────────────────────


def market_is_research_executable(market: ObservedMarketState) -> bool:
    return isinstance(market.question_text, str) and bool(market.question_text.strip())


def exact_market_scope(market: ObservedMarketState) -> tuple[str, dict[str, object], tuple[str, ...]]:
    """Return (scope_key, exact_scope_json, subject_refs) for one selected market.

    The exact scope carries only canonical identities; lane, rank, priority, cost,
    provider/model, review slot, gate outcome and Alpha-memory metadata never enter it.
    """
    if not market_is_research_executable(market):
        raise AF1OperatorError("PHASE_B_LOCAL_EVIDENCE_DEFECT")
    token_ids = tuple(sorted(set(market.token_ids)))
    subject_refs = tuple(sorted({market.market_id, market.event_id, *token_ids}))
    scope_key = "af1-market-scope:" + hashlib.sha256(market.market_id.encode("utf-8")).hexdigest()
    exact_scope = {"market_id": market.market_id, "event_id": market.event_id, "token_ids": list(token_ids)}
    return scope_key, exact_scope, subject_refs


def context_campaign(
    market: ObservedMarketState, *, cutoff: str, provider_label: str,
    model_label: str, phase_a_commit_sha: str,
) -> ContextCampaignScope:
    scope_key, exact_scope, subject_refs = exact_market_scope(market)
    return ContextCampaignScope.create(
        research_question=RESEARCH_QUESTION,
        subject_refs=subject_refs,
        scope_key=scope_key,
        exact_scope_json=exact_scope,
        information_cutoff=cutoff,
        allowed_public_research_classes=("public_web",),
        requested_provider_label=provider_label,
        requested_model_label=model_label,
        policy_id=DEFAULT_HERMES_INVOCATION_POLICY.policy_id,
        base_repo_code_identity=phase_a_commit_sha,
    )


def map_hermes_terminal_status(status: str, *, has_valid_receipt: bool = True) -> tuple[str, str | None]:
    if not has_valid_receipt or status in LOCAL_DEFECT_STATUSES:
        return "STOP", "PHASE_B_LOCAL_EVIDENCE_DEFECT"
    if status in HERMES_TERMINAL_MAP:
        return "FINALIZE", HERMES_TERMINAL_MAP[status]
    if status == "RESEARCH_DRAFT_VALIDATED":
        return "INSPECT_SUCCESS", None
    raise AF1OperatorError("PHASE_B_LOCAL_EVIDENCE_DEFECT")


# ── Blind review bodies / wrappers ────────────────────────────────────────────


def review_body_from_blind_result(*, exact_scope: Mapping[str, object], blind_result: object) -> dict[str, object]:
    run = getattr(blind_result, "run_result", None)
    draft = getattr(run, "validated_draft", None)
    if draft is None or getattr(blind_result, "blind_artifact", None) is None:
        raise AF1OperatorError("RESEARCH_OUTPUT_INVALID")
    urls = tuple(draft.source_urls)
    refs = tuple(draft.source_references)
    if len(urls) != len(refs):
        raise AF1OperatorError("RESEARCH_OUTPUT_INVALID")
    sources = []
    for url, ref in zip(urls, refs, strict=True):
        digest = hashlib.sha256(url.encode("utf-8")).hexdigest()
        if digest != ref.url_digest:
            raise AF1OperatorError("RESEARCH_OUTPUT_INVALID")
        sources.append({"url": url, "url_digest": ref.url_digest, "source_class": ref.source_class})
    claims = [{
        "claim_statement": claim.claim_statement,
        "claim_kind": claim.claim_kind,
        "subject_refs": list(claim.subject_refs),
        "direction": claim.direction,
        "source_reference_indices": list(claim.source_reference_indices),
        "assumptions": list(claim.assumptions),
        "uncertainty_note": claim.uncertainty_note,
    } for claim in draft.context_claims]
    return {
        "research_scope": dict(exact_scope),
        "research_summary": draft.research_summary,
        "confidence_label": draft.confidence_label,
        "sources": sources,
        "falsification_checks_performed": list(draft.falsification_checks_performed),
        "context_claims": claims,
    }


def review_wrappers(bodies: Sequence[Mapping[str, object]]) -> tuple[dict[str, object], ...]:
    """Hash lane-independent bodies first, then derive opaque slots from sorted hashes."""
    keyed = sorted((canonical_sha256(dict(body)), dict(body)) for body in bodies)
    if len(keyed) != 3 or len({digest for digest, _ in keyed}) != 3:
        raise AF1OperatorError("BLIND_REVIEW_PACKET_IDENTITY_COLLISION")
    return tuple({
        "schema_id": REVIEW_WRAPPER_SCHEMA_ID,
        "schema_version": AF1_SCHEMA_VERSION,
        "review_slot": slot,
        "review_body_sha256": digest,
        "review_body": body,
    } for slot, (digest, body) in zip(AF1_REVIEW_SLOTS, keyed, strict=True))


# ── Local evidence files ──────────────────────────────────────────────────────


def _reject_constant(value: str) -> object:
    raise ValueError("AF1_JSON_CONSTANT_FORBIDDEN")


def _reject_float(value: str) -> object:
    raise ValueError("AF1_BINARY_FLOAT_FORBIDDEN")


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("AF1_JSON_DUPLICATE_KEY")
        result[key] = value
    return result


def _json(path: Path) -> object:
    return json.loads(
        path.read_bytes().decode("utf-8"), object_pairs_hook=_unique_object,
        parse_constant=_reject_constant, parse_float=_reject_float,
    )


def _write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json_bytes(value) + b"\n")


def _write_exclusive_bytes(path: Path, payload: bytes) -> None:
    """Durably create one non-recyclable local evidence file (never overwritten)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0)
    descriptor = os.open(path, flags, 0o600)
    try:
        view = memoryview(payload)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                raise OSError("exclusive evidence write failed")
            view = view[written:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _write_exclusive(path: Path, value: object) -> None:
    _write_exclusive_bytes(path, canonical_json_bytes(value))


# ── Activation envelope ───────────────────────────────────────────────────────


def expected_workspace_attempt_id(workspace: Path) -> str:
    return "s10-gate-af1-" + workspace.name


def validate_activation_envelope(
    envelope: object, *, workspace: Path, provider_label: str | None = None,
    model_label: str | None = None, repo_root: Path | None = None,
) -> tuple[Mapping[str, object], str]:
    """Validate the exact closed schema, bound values, frozen digests and workspace.

    Returns ``(envelope, runtime_authorization_envelope_sha256)``; the digest is
    computed only after every check passes.
    """
    if not isinstance(envelope, Mapping) or set(envelope) != ACTIVATION_ENVELOPE_KEYS:
        raise AF1OperatorError("STATE_DRIFT")
    if provider_label is None:
        provider_label = envelope.get("provider_label")  # type: ignore[assignment]
    if model_label is None:
        model_label = envelope.get("model_label")  # type: ignore[assignment]
    if not isinstance(provider_label, str) or not provider_label or not isinstance(model_label, str) or not model_label:
        raise AF1OperatorError("STATE_DRIFT")
    required = {
        "schema_id": ACTIVATION_ENVELOPE_SCHEMA_ID,
        "schema_version": ACTIVATION_ENVELOPE_SCHEMA_VERSION,
        "wp_id": WP_ID, "base_sha": BASE_SHA,
        "provider_label": provider_label, "model_label": model_label,
        "hermes_invocation_policy_id": DEFAULT_HERMES_INVOCATION_POLICY.policy_id,
        **WP164_LABELS,
        "markets_limit": MARKETS_LIMIT, "order_books_limit": ORDER_BOOKS_LIMIT,
        "analysis_temporal_mode": "HISTORICAL_REPLAY",
        "alpha_memory_temporal_posture": "HISTORICAL_AVAILABILITY_UNPROVEN",
        "alpha_registry_path": None, "alpha_registry_head_entry_hash": None,
        "max_provider_calls": MAX_AF1_CASE_CALLS, "max_case_cost_usd": "5",
        "max_aggregate_cost_usd": "15", "retry_limit": 0,
        "provider_model_fallback": 0, "replacement_benchmark_case": 0,
        "fourth_call_authorized": False, "credentials_authorized": False,
        "scheduler_authorized": False,
        "strategy_qualification_economics_authorized": False,
        "paper_execution_authorized": False, "live_execution_authorized": False,
        "gate_c_authorized": False, "signing_or_orders_authorized": False,
        "h1_fifth_invocation_authorized": False, "merge_authorized": False,
    }
    if any(not _strict_equal(envelope[key], value) for key, value in required.items()):
        raise AF1OperatorError("STATE_DRIFT")
    if not _is_commit(envelope["phase_a_commit_sha"]):
        raise AF1OperatorError("STATE_DRIFT")
    digests = frozen_contract_digests(repo_root)
    for key, digest in digests.items():
        if not _is_sha256(envelope[key]) or envelope[key] != digest:
            raise AF1OperatorError("STATE_DRIFT")
    root = _repo_root(repo_root)
    try:
        relative = workspace.relative_to(root.joinpath(*WORKSPACE_ROOT_PARTS))
    except ValueError:
        raise AF1OperatorError("STATE_DRIFT") from None
    attempt_directory = workspace.name
    if (
        relative.parts != (envelope["phase_a_commit_sha"], attempt_directory)
        or ATTEMPT_DIRECTORY_RE.fullmatch(attempt_directory) is None
        or attempt_directory in CONSUMED_ATTEMPT_DIRECTORIES
        or attempt_directory != AUTHORIZED_ATTEMPT_DIRECTORY
        or envelope["workspace_attempt_id"] != expected_workspace_attempt_id(workspace)
    ):
        raise AF1OperatorError("STATE_DRIFT")
    return envelope, canonical_sha256(dict(envelope))


def load_activation_envelope(
    workspace: Path, *, provider_label: str | None = None, model_label: str | None = None,
    repo_root: Path | None = None,
) -> tuple[Mapping[str, object], str]:
    path = workspace / ACTIVATION_ENVELOPE_FILENAME
    if not path.is_file() or path.is_symlink():
        raise AF1OperatorError("STATE_DRIFT")
    return validate_activation_envelope(
        _json(path), workspace=workspace, provider_label=provider_label,
        model_label=model_label, repo_root=repo_root,
    )


# ── WP164A population: sentinel, retained result, classification ─────────────


def population_invocation_mapping(
    *, phase_a_commit_sha: str, envelope_sha256: str, workspace_attempt_id: str,
) -> dict[str, object]:
    return {
        "schema_id": "s10-gate-af1-public-population-invocation",
        "schema_version": "1.0.0",
        "phase_a_commit_sha": phase_a_commit_sha,
        "runtime_authorization_envelope_sha256": envelope_sha256,
        "workspace_attempt_id": workspace_attempt_id,
        "requested_markets_limit": MARKETS_LIMIT,
        "requested_order_books_limit": ORDER_BOOKS_LIMIT,
        "invocation_state": "STARTED",
    }


def population_result_mapping(result: object) -> dict[str, object]:
    """Complete canonical mapping of the exact current 38-field typed result."""
    if type(result) is not PolymarketPublicPopulationResult:
        raise AF1OperatorError("PHASE_B_LOCAL_EVIDENCE_DEFECT")
    if tuple(field.name for field in fields(PolymarketPublicPopulationResult)) != POPULATION_RESULT_FIELDS:
        raise AF1OperatorError("PHASE_B_LOCAL_EVIDENCE_DEFECT")
    try:
        # Canonical JSON round-trip converts tuple fields to their durable JSON-array
        # representation without dropping any typed dataclass field.
        mapping = json.loads(canonical_json_bytes(asdict(result)))
    except ValueError as exc:
        raise AF1OperatorError("PHASE_B_LOCAL_EVIDENCE_DEFECT") from exc
    if set(mapping) != _POPULATION_RESULT_KEYS:
        raise AF1OperatorError("PHASE_B_LOCAL_EVIDENCE_DEFECT")
    return mapping


def persist_population_result(workspace: Path, result: PolymarketPublicPopulationResult) -> tuple[dict[str, object], str]:
    mapping = population_result_mapping(result)
    path = workspace / POPULATION_RESULT_FILENAME
    original = canonical_json_bytes(mapping)
    try:
        _write_exclusive(path, mapping)
        readback_bytes = path.read_bytes()
        retained = _json(path)
    except (OSError, ValueError) as exc:
        raise AF1OperatorError("PHASE_B_LOCAL_EVIDENCE_DEFECT") from exc
    if readback_bytes != original or retained != mapping or canonical_json_bytes(retained) != original:
        raise AF1OperatorError("PHASE_B_LOCAL_EVIDENCE_DEFECT")
    return mapping, hashlib.sha256(original).hexdigest()


def _str_list(value: object) -> tuple[str, ...]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise AF1OperatorError("PHASE_B_LOCAL_EVIDENCE_DEFECT")
    return tuple(value)


def _stores_valid_empty(record_store_result: object, manifest_store_result: object) -> bool:
    record_snapshot = getattr(record_store_result, "snapshot", None)
    manifest_snapshot = getattr(manifest_store_result, "snapshot", None)
    return bool(
        getattr(record_store_result, "is_valid", False) is True
        and getattr(manifest_store_result, "is_valid", False) is True
        and record_snapshot is not None and manifest_snapshot is not None
        and tuple(getattr(record_snapshot, "records", (None,))) == ()
        and tuple(getattr(manifest_snapshot, "dataset_references", (None,))) == ()
        and tuple(getattr(manifest_snapshot, "manifest_entries", (None,))) == ()
    )


def classify_public_population_result(
    mapping: object, *, record_store_result: object, manifest_store_result: object,
) -> str:
    """Closed WP164A classification over the retained typed result and verified stores.

    Returns ``PUBLIC_POPULATION_EXTERNAL_UNAVAILABLE`` (A1) or ``POPULATION_VALID``;
    every other shape is a true ``PHASE_B_LOCAL_EVIDENCE_DEFECT`` stop.
    """
    if not isinstance(mapping, Mapping) or set(mapping) != _POPULATION_RESULT_KEYS:
        raise AF1OperatorError("PHASE_B_LOCAL_EVIDENCE_DEFECT")
    errors = _str_list(mapping["error_codes"])
    lists = {
        key: _str_list(mapping[key]) for key in (
            "record_store_error_codes", "registration_error_codes", "warning_codes",
            "batch_error_codes", "batch_warning_codes", "batch_accepted_record_version_ids",
            "batch_exact_duplicate_record_version_ids", "batch_quarantined_record_version_ids",
            "build_error_codes", "build_warning_codes",
        )
    }
    if mapping["advisory_only"] is not True or mapping["no_execution_authority"] is not True:
        raise AF1OperatorError("PHASE_B_LOCAL_EVIDENCE_DEFECT")
    if (
        mapping["requested_markets_limit"] != MARKETS_LIMIT
        or mapping["requested_order_books_limit"] != ORDER_BOOKS_LIMIT
        or type(mapping["requested_markets_limit"]) is not int
        or type(mapping["requested_order_books_limit"]) is not int
    ):
        raise AF1OperatorError("PHASE_B_LOCAL_EVIDENCE_DEFECT")
    build_diagnostics_absent = (
        mapping["build_failure_observation_kind"] is None and mapping["build_status"] is None
        and lists["build_error_codes"] == () and lists["build_warning_codes"] == ()
        and mapping["build_quarantine_id"] is None and mapping["build_input_fingerprint_sha256"] is None
    )
    if mapping["is_valid"] is False:
        # A1 exactness: a sole external acquisition error on a network-used rejected
        # result with no contradictory store/build/batch/registration evidence.
        a1 = (
            mapping["status"] == "POPULATION_REJECTED"
            and mapping["network_used"] is True
            and errors in A1_ERROR_TUPLES
            and lists["record_store_error_codes"] == () and lists["registration_error_codes"] == ()
            and mapping["recovery_required"] is False
            and mapping["inserted_record_count"] == 0
            and mapping["record_store_status"] is None and mapping["registration_status"] is None
            and mapping["dataset_snapshot_reference_id"] is None and mapping["manifest_entry_id"] is None
            and mapping["batch_is_valid"] is None and mapping["batch_status"] is None
            and lists["batch_error_codes"] == () and lists["batch_accepted_record_version_ids"] == ()
            and lists["batch_exact_duplicate_record_version_ids"] == ()
            and lists["batch_quarantined_record_version_ids"] == ()
            and mapping["canonical_batch_sha256"] is None
            and build_diagnostics_absent
            and _stores_valid_empty(record_store_result, manifest_store_result)
        )
        if a1:
            return AF1_A1_REASON
        raise AF1OperatorError("PHASE_B_LOCAL_EVIDENCE_DEFECT")
    counts = (
        "bounded_markets_limit", "bounded_order_books_limit", "fetched_market_count",
        "fetched_order_book_count", "built_record_count", "inserted_record_count",
    )
    if any(type(mapping[key]) is not int for key in counts):
        raise AF1OperatorError("PHASE_B_LOCAL_EVIDENCE_DEFECT")
    fetched_markets = mapping["fetched_market_count"]
    fetched_books = mapping["fetched_order_book_count"]
    built = mapping["built_record_count"]
    accepted = lists["batch_accepted_record_version_ids"]
    captured = mapping["captured_at_utc"]
    try:
        cutoff_is_canonical = isinstance(captured, str) and bool(canonicalize_utc_timestamp(captured))
    except ValueError:
        cutoff_is_canonical = False
    # Fresh success is judged on ACTUAL returned counts, never on request limits;
    # POPULATION_ALREADY_REGISTERED means reused/recovered state in a fresh workspace.
    success = (
        mapping["is_valid"] is True
        and mapping["status"] == "POPULATION_PERSISTED_AND_REGISTERED"
        and errors == ()
        and mapping["network_used"] is True
        and mapping["bounded_markets_limit"] == MARKETS_LIMIT
        and mapping["bounded_order_books_limit"] == ORDER_BOOKS_LIMIT
        and 1 <= fetched_markets <= MARKETS_LIMIT
        and 0 <= fetched_books <= ORDER_BOOKS_LIMIT
        and built == fetched_markets + fetched_books
        and mapping["inserted_record_count"] == built
        and build_diagnostics_absent
        and mapping["batch_is_valid"] is True
        and lists["batch_error_codes"] == ()
        and lists["batch_quarantined_record_version_ids"] == ()
        and lists["batch_exact_duplicate_record_version_ids"] == ()
        and len(accepted) == built and len(set(accepted)) == built
        and _is_sha256(mapping["canonical_batch_sha256"])
        and mapping["record_store_status"] == "RECORD_STORE_APPEND_COMMITTED"
        and mapping["registration_status"] == "ADAPTER_PERSISTED"
        and lists["record_store_error_codes"] == () and lists["registration_error_codes"] == ()
        and mapping["recovery_required"] is False
        and isinstance(mapping["snapshot_id"], str) and bool(mapping["snapshot_id"])
        and cutoff_is_canonical
        and isinstance(mapping["dataset_snapshot_reference_id"], str)
        and isinstance(mapping["manifest_entry_id"], str)
    )
    if not success:
        raise AF1OperatorError("PHASE_B_LOCAL_EVIDENCE_DEFECT")
    # Stores are independent integrity evidence, never substitutes for typed facts.
    record_snapshot = getattr(record_store_result, "snapshot", None)
    manifest_snapshot = getattr(manifest_store_result, "snapshot", None)
    if getattr(record_store_result, "is_valid", False) is not True or record_snapshot is None:
        raise AF1OperatorError("PHASE_B_LOCAL_EVIDENCE_DEFECT")
    if getattr(manifest_store_result, "is_valid", False) is not True or manifest_snapshot is None:
        raise AF1OperatorError("PHASE_B_LOCAL_EVIDENCE_DEFECT")
    stored_ids = [getattr(getattr(record, "envelope", None), "record_version_id", None) for record in record_snapshot.records]
    if len(stored_ids) != built or len(set(stored_ids)) != built or set(stored_ids) != set(accepted):
        raise AF1OperatorError("PHASE_B_LOCAL_EVIDENCE_DEFECT")
    references = [
        item for item in manifest_snapshot.dataset_references
        if item.dataset_snapshot_reference_id == mapping["dataset_snapshot_reference_id"]
    ]
    entries = [
        item for item in manifest_snapshot.manifest_entries
        if item.manifest_entry_id == mapping["manifest_entry_id"]
    ]
    if (
        len(references) != 1 or len(entries) != 1
        or entries[0].dataset_snapshot_reference_id != mapping["dataset_snapshot_reference_id"]
        or entries[0].manifest_id != WP164_LABELS["manifest_id"]
        or entries[0].parameter_set_id != WP164_LABELS["parameter_set_id"]
        or references[0].parameter_set_id != WP164_LABELS["parameter_set_id"]
        or references[0].validator_version != WP164_LABELS["validator_version"]
        or references[0].validated_batch_sha256 != mapping["canonical_batch_sha256"]
    ):
        raise AF1OperatorError("PHASE_B_LOCAL_EVIDENCE_DEFECT")
    return "POPULATION_VALID"


def verify_population_stores(record_store: Path, manifest_store: Path) -> tuple[object, object]:
    record_result = load_and_verify_point_in_time_record_store(record_store)
    manifest_result = load_and_verify_manifest_store(manifest_store)
    if getattr(record_result, "is_valid", False) is not True or getattr(manifest_result, "is_valid", False) is not True:
        raise AF1OperatorError("PHASE_B_LOCAL_EVIDENCE_DEFECT")
    return record_result, manifest_result


def invoke_public_population_once(
    workspace: Path, *, record_store: Path, manifest_store: Path,
    config: PolymarketPublicPopulationConfig, phase_a_commit_sha: str,
    envelope_sha256: str, workspace_attempt_id: str,
) -> tuple[PolymarketPublicPopulationResult, dict[str, object], str]:
    """One coordinator call guarded by a durable, never-recycled pre-call sentinel."""
    sentinel = workspace / POPULATION_INVOCATION_FILENAME
    if sentinel.exists() or (workspace / POPULATION_RESULT_FILENAME).exists():
        raise AF1OperatorError("PHASE_B_LOCAL_EVIDENCE_DEFECT")
    invocation = population_invocation_mapping(
        phase_a_commit_sha=phase_a_commit_sha,
        envelope_sha256=envelope_sha256,
        workspace_attempt_id=workspace_attempt_id,
    )
    try:
        _write_exclusive(sentinel, invocation)
    except OSError as exc:
        raise AF1OperatorError("PHASE_B_LOCAL_EVIDENCE_DEFECT") from exc
    try:
        result = populate_initial_polymarket_public_data(record_store, manifest_store, config)
    except Exception as exc:  # the sentinel stays: this workspace is consumed
        raise AF1OperatorError("PHASE_B_LOCAL_EVIDENCE_DEFECT") from exc
    mapping, digest = persist_population_result(workspace, result)
    return result, mapping, digest


# ── Hermes cost / authority inspection ────────────────────────────────────────


def known_receipt_cost(receipt: HermesResearchRunReceipt) -> Decimal | None:
    """Known finite non-negative cost under the existing HERMES cost-status semantics."""
    if receipt.cost_status not in KNOWN_COST_STATUSES or receipt.estimated_cost_usd is None:
        return None
    try:
        amount = Decimal(receipt.estimated_cost_usd)
    except (InvalidOperation, TypeError, ValueError):
        return None
    if not amount.is_finite() or amount < 0:
        return None
    if receipt.cost_status == "included" and amount != 0:
        return None
    return amount


def _cost_text(amount: Decimal) -> str:
    return str(amount)


_RECEIPT_AUTHORITY_FLAGS = (
    "human_review_required", "no_execution_authority", "no_live_authority",
    "no_credential_authority", "no_risk_authority", "no_paper_authority",
)


def _authority_invariants_hold(receipt: HermesResearchRunReceipt, blind_result: object) -> bool:
    artifact = getattr(blind_result, "blind_artifact", None)
    return (
        all(getattr(receipt, name, None) is True for name in _RECEIPT_AUTHORITY_FLAGS)
        and artifact is not None
        and getattr(artifact, "alpha_context_present", None) is False
    )


def _inspect_success(
    *, blind_result: object, receipt: HermesResearchRunReceipt, session: object,
    exact_scope: Mapping[str, object], accepted_total: Decimal,
) -> tuple[str | None, Decimal | None, dict[str, object] | None]:
    """Section-18 RESEARCH_DRAFT_VALIDATED checks over sanitized evidence only."""
    if session is not None and tuple(getattr(session, "unexpected_tool_names", ())):
        return "UNEXPECTED_RESEARCH_TOOL", known_receipt_cost(receipt), None
    cost = known_receipt_cost(receipt)
    if cost is None:
        return "SUCCESSFUL_RUN_COST_UNKNOWN", None, None
    if cost > MAX_CASE_COST_USD:
        return "CASE_COST_LIMIT_BREACH", None, None
    if accepted_total + cost > MAX_AGGREGATE_COST_USD:
        return "AGGREGATE_COST_LIMIT_BREACH", None, None
    if not _authority_invariants_hold(receipt, blind_result):
        return "AUTHORITY_BOUNDARY_BREACH", cost, None
    try:
        body = review_body_from_blind_result(exact_scope=exact_scope, blind_result=blind_result)
    except AF1OperatorError:
        return "RESEARCH_OUTPUT_INVALID", cost, None
    return None, cost, body


# ── Pre-sentinel Hermes runtime-environment preflight (zero network) ──────────


def _preflight_defect(reason: str) -> AF1OperatorError:
    return AF1OperatorError("PHASE_B_LOCAL_EVIDENCE_DEFECT", reason)


def _outside_repository(resolved: str, repo_root: Path | None) -> bool:
    if "local_data" in Path(resolved).parts:
        return False
    lowered = os.path.normcase(resolved)
    root = os.path.normcase(str(_repo_root(repo_root)))
    return lowered != root and not lowered.startswith(root + os.sep)


def _resolve_launch_path(raw: object, *, reason: str, repo_root: Path | None) -> str:
    """Absolute, traversal-free, alias-free real path outside the repository."""
    if not isinstance(raw, str) or not raw.strip() or not os.path.isabs(raw) or ".." in Path(raw).parts:
        raise _preflight_defect(reason)
    resolved = os.path.realpath(raw)
    if os.path.normcase(resolved) != os.path.normcase(os.path.abspath(raw)):
        raise _preflight_defect(reason)  # symlink/junction alias ambiguity
    if not _outside_repository(resolved, repo_root):
        raise _preflight_defect(reason)
    return resolved


def validate_hermes_runtime_environment(
    hermes_executable: object, hermes_home: object, *, backend: object | None = None,
    repo_root: Path | None = None,
) -> tuple[str, str]:
    """Prove the exact pinned executable and research home are usable, offline.

    Reuses the merged HERMES-CTX mechanisms: executable-path validation, the
    update-check-disabled version probe, the offline ``--help`` startup/profile-init
    probe and the safe/clean research-home checks (names only; no credential is read).
    Returns the validated ``(executable_path, hermes_home)`` passed to every case.
    """
    executable = _resolve_launch_path(hermes_executable, reason="HERMES_EXECUTABLE_INVALID", repo_root=repo_root)
    if not os.path.isfile(executable):
        raise _preflight_defect("HERMES_EXECUTABLE_INVALID")
    try:
        validate_executable_path(executable)
        version_argv = build_version_argv(executable)
        startup_argv = build_startup_argv(executable)
    except PolicyBroadeningError:
        raise _preflight_defect("HERMES_EXECUTABLE_INVALID") from None
    home = _resolve_launch_path(hermes_home, reason="HERMES_HOME_INVALID", repo_root=repo_root)
    if not os.path.isdir(home) or not is_safe_research_home(home):
        raise _preflight_defect("HERMES_HOME_INVALID")
    if not is_clean_research_home_control_plane(home):
        raise _preflight_defect("HERMES_HOME_CONTROL_PLANE_INVALID")
    probe_backend = backend if backend is not None else ExternalHermesCliBackend()
    version = probe_backend.probe_version(  # type: ignore[attr-defined]
        version_argv=version_argv, max_output_bytes=_VERSION_PROBE_MAX_BYTES,
        max_wall_seconds=_VERSION_PROBE_MAX_SECONDS,
    )
    if (
        not version.launched or version.timed_out or version.exit_code != 0
        or version.stdout_truncated or not is_supported_hermes_version(version.version_text)
    ):
        raise _preflight_defect("HERMES_VERSION_PREFLIGHT_FAILED")
    startup = probe_backend.probe_startup(  # type: ignore[attr-defined]
        startup_argv=startup_argv, max_output_bytes=_STARTUP_PROBE_MAX_BYTES,
        max_wall_seconds=_STARTUP_PROBE_MAX_SECONDS,
    )
    if not startup.launched or startup.timed_out or startup.exit_code != 0:
        raise _preflight_defect("HERMES_STARTUP_PREFLIGHT_FAILED")
    return executable, home


# ── Runtime phase ─────────────────────────────────────────────────────────────


def _default_backend_factory() -> Callable[[ContextCampaignScope], object]:
    backend = ExternalHermesCliBackend()
    return lambda campaign: backend


def _runtime_result_base(envelope: Mapping[str, object], envelope_digest: str) -> dict[str, object]:
    return {
        "schema_id": "s10-gate-af1-runtime-result", "schema_version": "1.0.0",
        "wp_id": WP_ID, "base_sha": BASE_SHA,
        "phase_a_commit_sha": envelope["phase_a_commit_sha"],
        "wp_prompt_sha256": envelope["wp_prompt_sha256"],
        "wp_spec_sha256": envelope["wp_spec_sha256"],
        "gate_contract_sha256": envelope["gate_contract_sha256"],
        "workspace_attempt_id": envelope["workspace_attempt_id"],
        "runtime_authorization_envelope_sha256": envelope_digest,
        "public_population_result_sha256": None,
        "runtime_state": None, "terminal_reason": None, "stop_code": None,
        "known_within_limits": None,
        "benchmark_manifest": None, "real_case_evidence": [], "review_bodies": [],
        "controller_invocation_count": 0,
    }


def _require_cutoff_chain(cutoff: str, universe: AlphaUniverseSnapshot, campaigns: Sequence[ContextCampaignScope]) -> None:
    """One canonical PIT cutoff: result.captured_at_utc == universe.as_of == scope cutoffs."""
    canonical = canonicalize_utc_timestamp(cutoff)
    if universe.as_of != cutoff or canonicalize_utc_timestamp(universe.as_of) != canonical:
        raise AF1OperatorError("PHASE_B_LOCAL_EVIDENCE_DEFECT")
    if any(campaign.information_cutoff != canonical for campaign in campaigns):
        raise AF1OperatorError("PHASE_B_LOCAL_EVIDENCE_DEFECT")


def execute_real_phase(
    workspace: Path, envelope: Mapping[str, object], *, provider_label: str,
    model_label: str, hermes_executable: str, hermes_home: str,
    repo_root: Path | None = None,
    backend_factory: Callable[[ContextCampaignScope], object] | None = None,
    preflight_backend: object | None = None,
) -> dict[str, object]:
    """Perform the single bounded Phase-B composition after external authorization.

    No retry loop exists: population runs once and each frozen case reaches
    ``run_blind_phase`` at most once.  Any terminal prevents later paid calls.
    """
    envelope, envelope_digest = validate_activation_envelope(
        envelope, workspace=workspace, provider_label=provider_label,
        model_label=model_label, repo_root=repo_root,
    )
    sentinel_or_result = (
        workspace / POPULATION_INVOCATION_FILENAME, workspace / POPULATION_RESULT_FILENAME,
        workspace / RUNTIME_RESULT_FILENAME,
    )
    if any(path.exists() for path in sentinel_or_result):
        raise AF1OperatorError("PHASE_B_LOCAL_EVIDENCE_DEFECT")
    record_store = workspace / RECORD_STORE_FILENAME
    manifest_store = workspace / MANIFEST_STORE_FILENAME
    if record_store.exists() or manifest_store.exists() or (workspace / CONTEXT_STORE_DIRNAME).exists():
        raise AF1OperatorError("STATE_DRIFT")
    # Pre-sentinel: nothing below may run unless the exact Hermes runtime is usable.
    executable_path, research_home = validate_hermes_runtime_environment(
        hermes_executable, hermes_home, backend=preflight_backend, repo_root=repo_root,
    )
    if not initialize_point_in_time_record_store(record_store).is_valid:
        raise AF1OperatorError("PHASE_B_LOCAL_EVIDENCE_DEFECT")
    if not initialize_manifest_store(manifest_store).is_valid:
        raise AF1OperatorError("PHASE_B_LOCAL_EVIDENCE_DEFECT")
    phase_a_commit_sha = str(envelope["phase_a_commit_sha"])
    _, population_mapping, population_digest = invoke_public_population_once(
        workspace, record_store=record_store, manifest_store=manifest_store,
        config=benchmark_population_config(allow_network=True),
        phase_a_commit_sha=phase_a_commit_sha, envelope_sha256=envelope_digest,
        workspace_attempt_id=str(envelope["workspace_attempt_id"]),
    )
    result = _runtime_result_base(envelope, envelope_digest)
    result["public_population_result_sha256"] = population_digest
    try:
        record_result, manifest_result = verify_population_stores(record_store, manifest_store)
        classification = classify_public_population_result(
            population_mapping, record_store_result=record_result,
            manifest_store_result=manifest_result,
        )
        if classification == AF1_A1_REASON:
            result.update(runtime_state="RUNTIME_TERMINAL", terminal_reason=AF1_A1_REASON)
            _write_exclusive(workspace / RUNTIME_RESULT_FILENAME, result)
            return result
        _run_benchmark(
            result, workspace=workspace, envelope=envelope, envelope_digest=envelope_digest,
            population_mapping=population_mapping, population_digest=population_digest,
            record_store=record_store, provider_label=provider_label, model_label=model_label,
            executable_path=executable_path, hermes_home=research_home, backend_factory=backend_factory,
        )
    except AF1OperatorError as exc:
        # TRUE STOP: retain local audit evidence, never a gate receipt, never retried.
        result.update(runtime_state="TRUE_STOP", stop_code=str(exc), terminal_reason=None)
        _write_exclusive(workspace / RUNTIME_RESULT_FILENAME, result)
        raise
    _write_exclusive(workspace / RUNTIME_RESULT_FILENAME, result)
    return result


def _run_benchmark(
    result: dict[str, object], *, workspace: Path, envelope: Mapping[str, object],
    envelope_digest: str, population_mapping: Mapping[str, object], population_digest: str,
    record_store: Path, provider_label: str, model_label: str, executable_path: str,
    hermes_home: str,
    backend_factory: Callable[[ContextCampaignScope], object] | None,
) -> None:
    cutoff = str(population_mapping["captured_at_utc"])
    policy = benchmark_discovery_policy()
    universe_result = build_alpha_universe_snapshot(record_store, policy, cutoff)
    if not universe_result.is_valid or not isinstance(universe_result.record, AlphaUniverseSnapshot):
        raise AF1OperatorError("PHASE_B_LOCAL_EVIDENCE_DEFECT")
    universe = universe_result.record
    _require_cutoff_chain(cutoff, universe, ())
    basis_result = build_pre_allocation_triage_bases(
        universe, policy, analysis_temporal_mode="HISTORICAL_REPLAY",
        alpha_memory_temporal_posture="HISTORICAL_AVAILABILITY_UNPROVEN",
        alpha_registry_path=None, prior=None, material_changes=(),
    )
    if not basis_result.is_valid:
        raise AF1OperatorError("PHASE_B_LOCAL_EVIDENCE_DEFECT")
    queue_result = allocate_and_finalize_research_queue(universe, policy, basis_result.records)
    if not queue_result.is_valid or not isinstance(queue_result.record, AlphaResearchQueueSnapshot):
        raise AF1OperatorError("PHASE_B_LOCAL_EVIDENCE_DEFECT")
    queue = queue_result.record
    decisions = {item.market_triage_decision_id: item for item in queue_result.records if isinstance(item, MarketTriageDecision)}
    market_by_id = {item.market_id: item for item in universe.markets}
    # Coverage accounting: one historical-posture disposition per observed market.
    if (
        queue.analysis_temporal_mode != "HISTORICAL_REPLAY"
        or queue.alpha_memory_temporal_posture != "HISTORICAL_AVAILABILITY_UNPROVEN"
        or queue.alpha_registry_head_entry_hash is not None
        or set(queue.all_triage_ids) != set(decisions)
        or sorted(item.market_id for item in decisions.values()) != sorted(market_by_id)
        or any(
            item.analysis_temporal_mode != "HISTORICAL_REPLAY"
            or item.alpha_registry_head_entry_hash is not None
            for item in decisions.values()
        )
    ):
        raise AF1OperatorError("PHASE_B_LOCAL_EVIDENCE_DEFECT")
    selected_ids = (
        queue.core_triage_ids[0] if queue.core_triage_ids else None,
        queue.exploration_triage_ids[0] if queue.exploration_triage_ids else None,
        queue.audit_triage_ids[0] if queue.audit_triage_ids else None,
    )
    selected_markets: list[ObservedMarketState] = []
    for triage_id in selected_ids:
        if triage_id is not None:
            decision = decisions.get(triage_id)
            if decision is None or decision.market_id not in market_by_id:
                raise AF1OperatorError("PHASE_B_LOCAL_EVIDENCE_DEFECT")
            selected_markets.append(market_by_id[decision.market_id])
    if any(item is None for item in selected_ids):
        coverage = "REQUIRED_LANE_ABSENT"
    elif not all(market_is_research_executable(market) for market in selected_markets):
        # Genuine lanes whose public market lacks usable question_text: A2 coverage,
        # not a software defect, and no question is invented from other fields.
        coverage = "REQUIRED_LANE_NOT_RESEARCH_EXECUTABLE"
    else:
        coverage = "COMPLETE"
    manifest = build_af1_benchmark_manifest({
        "schema_id": "af1-benchmark-manifest", "schema_version": "1.0.0", "manifest_id": "",
        "wp_id": WP_ID, "base_sha": BASE_SHA,
        "phase_a_commit_sha": envelope["phase_a_commit_sha"],
        "wp_prompt_sha256": envelope["wp_prompt_sha256"],
        "wp_spec_sha256": envelope["wp_spec_sha256"],
        "gate_contract_sha256": envelope["gate_contract_sha256"],
        "runtime_authorization_envelope_sha256": envelope_digest,
        "public_population_result_sha256": population_digest,
        "population_manifest_id": WP164_LABELS["manifest_id"],
        "parameter_set_id": WP164_LABELS["parameter_set_id"],
        "normalizer_version": WP164_LABELS["normalizer_version"],
        "validator_version": WP164_LABELS["validator_version"],
        "alpha_discovery_policy_id": policy.alpha_discovery_policy_id,
        "analysis_temporal_mode": "HISTORICAL_REPLAY",
        "alpha_memory_temporal_posture": "HISTORICAL_AVAILABILITY_UNPROVEN",
        "alpha_registry_head_entry_hash": None, "cutoff": cutoff,
        "universe_snapshot_id": universe.alpha_universe_snapshot_id,
        "research_queue_snapshot_id": queue.alpha_research_queue_snapshot_id,
        "requested_market_count": MARKETS_LIMIT, "requested_order_book_count": ORDER_BOOKS_LIMIT,
        "actual_market_count": population_mapping["fetched_market_count"],
        "actual_order_book_count": population_mapping["fetched_order_book_count"],
        "provider_label": provider_label, "model_label": model_label,
        "hermes_invocation_policy_id": DEFAULT_HERMES_INVOCATION_POLICY.policy_id,
        "max_provider_calls": MAX_AF1_CASE_CALLS, "max_case_cost_usd": "5", "max_aggregate_cost_usd": "15",
        "retry_limit": 0, "coverage_terminal": coverage,
        "selected_core_triage_id": selected_ids[0], "selected_exploration_triage_id": selected_ids[1],
        "selected_audit_triage_id": selected_ids[2],
        **_AUTHORITY_FLAGS,
    })
    result["benchmark_manifest"] = af1_record_to_mapping(manifest)
    if coverage != "COMPLETE":
        result.update(runtime_state="RUNTIME_TERMINAL", terminal_reason=AF1_A2_REASON)
        return

    campaigns = tuple(
        context_campaign(
            market, cutoff=cutoff, provider_label=provider_label, model_label=model_label,
            phase_a_commit_sha=str(envelope["phase_a_commit_sha"]),
        )
        for market in selected_markets
    )
    _require_cutoff_chain(cutoff, universe, campaigns)
    factory = backend_factory if backend_factory is not None else _default_backend_factory()
    accepted_total = Decimal("0")
    bodies: list[dict[str, object]] = []
    real_cases: list[dict[str, object]] = []
    result["real_case_evidence"] = real_cases
    for ordinal, (triage_id, market, campaign) in enumerate(zip(selected_ids, selected_markets, campaigns, strict=True), start=1):
        _, exact_scope, _ = exact_market_scope(market)
        store = ContextArtifactStore(context_store_root(workspace, ordinal))
        # Exactly one controller invocation per fixed case; counted before the call so
        # an exception still consumes the case and blocks any retry or replacement.
        result["controller_invocation_count"] = ordinal
        try:
            blind = run_blind_phase(
                campaign=campaign, store=store, backend=factory(campaign),
                executable_path=executable_path,
                policy=DEFAULT_HERMES_INVOCATION_POLICY, hermes_home=hermes_home,
            )
        except Exception as exc:
            raise AF1OperatorError("PHASE_B_LOCAL_EVIDENCE_DEFECT") from exc
        run = getattr(blind, "run_result", None)
        receipt = getattr(run, "receipt", None)
        if type(receipt) is not HermesResearchRunReceipt:
            raise AF1OperatorError("PHASE_B_LOCAL_EVIDENCE_DEFECT")
        action, reason = map_hermes_terminal_status(receipt.terminal_status)
        if action == "STOP":
            raise AF1OperatorError(str(reason))
        session = run.session_evidence
        accepted_cost: Decimal | None = None
        review_body = None
        if action == "INSPECT_SUCCESS":
            reason, accepted_cost, review_body = _inspect_success(
                blind_result=blind, receipt=receipt, session=session,
                exact_scope=exact_scope, accepted_total=accepted_total,
            )
        elif reason == AF1_RUNTIME_UNAVAILABLE_REASON:
            known = known_receipt_cost(receipt)
            if known is not None and known <= MAX_CASE_COST_USD:
                accepted_cost = known
        if accepted_cost is not None:
            accepted_total += accepted_cost
        body_digest = canonical_sha256(review_body) if review_body is not None else None
        artifact = blind.blind_artifact
        real = build_af1_real_case_evidence({
            "schema_id": "af1-real-case-evidence", "schema_version": "1.0.0", "real_case_evidence_id": "",
            "manifest_id": manifest.manifest_id, "case_id": AF1_REAL_CASE_IDS[ordinal - 1],
            "selected_triage_id": triage_id, "campaign_id": campaign.campaign_id,
            "blind_artifact_id": artifact.blind_artifact_id if artifact is not None else None,
            "run_receipt_id": receipt.receipt_id, "run_terminal_status": receipt.terminal_status,
            "session_evidence_id": session.session_evidence_id if session is not None else None,
            "session_evidence_status": session.transcript_evidence_status if session is not None else "UNAVAILABLE",
            "requested_provider_label": provider_label, "requested_model_label": model_label,
            "verified_provider_label": receipt.verified_provider,
            "verified_model_label": receipt.verified_model,
            "backend_telemetry_status": session.actual_backend_attestation_status if session is not None else "UNAVAILABLE",
            "accepted_estimated_cost_usd": _cost_text(accepted_cost) if accepted_cost is not None else None,
            "review_body_sha256": body_digest,
            "terminal_reason": reason, **_AUTHORITY_FLAGS,
        })
        real_cases.append(af1_record_to_mapping(real))
        if review_body is not None:
            bodies.append(review_body)
        if reason is not None:
            known_within = None
            if reason == AF1_RUNTIME_UNAVAILABLE_REASON:
                known_within = accepted_cost is not None and accepted_total <= MAX_AGGREGATE_COST_USD
            result.update(runtime_state="RUNTIME_TERMINAL", terminal_reason=reason, known_within_limits=known_within)
            return
    review_wrappers(bodies)  # distinct-hash precondition (true stop on collision)
    result["review_bodies"] = bodies
    result.update(runtime_state="BLIND_REVIEW_REQUIRED", terminal_reason=None)


# ── Verification / review / finalization (all local, zero network) ────────────


_RUNTIME_RESULT_KEYS = frozenset({
    "schema_id", "schema_version", "wp_id", "base_sha", "phase_a_commit_sha",
    "wp_prompt_sha256", "wp_spec_sha256", "gate_contract_sha256", "workspace_attempt_id",
    "runtime_authorization_envelope_sha256", "public_population_result_sha256",
    "runtime_state", "terminal_reason", "stop_code", "known_within_limits",
    "benchmark_manifest", "real_case_evidence", "review_bodies",
    "controller_invocation_count",
})


def verify_run(workspace: Path, *, repo_root: Path | None = None) -> dict[str, object]:
    """Recompute every local binding of a finalizable runtime result."""
    envelope, envelope_digest = load_activation_envelope(workspace, repo_root=repo_root)
    result = _json(workspace / RUNTIME_RESULT_FILENAME)
    if not isinstance(result, dict) or set(result) != _RUNTIME_RESULT_KEYS:
        raise AF1OperatorError("RUN_EVIDENCE_INVALID")
    expected = _runtime_result_base(envelope, envelope_digest)
    for key in ("schema_id", "schema_version", "wp_id", "base_sha", "phase_a_commit_sha", "wp_prompt_sha256", "wp_spec_sha256", "gate_contract_sha256", "workspace_attempt_id", "runtime_authorization_envelope_sha256"):
        if result[key] != expected[key]:
            raise AF1OperatorError("RUN_EVIDENCE_INVALID")
    if result["runtime_state"] == "TRUE_STOP":
        raise AF1OperatorError("RUNTIME_TRUE_STOP_NOT_FINALIZABLE")
    sentinel = _json(workspace / POPULATION_INVOCATION_FILENAME)
    if sentinel != population_invocation_mapping(
        phase_a_commit_sha=str(envelope["phase_a_commit_sha"]), envelope_sha256=envelope_digest,
        workspace_attempt_id=str(envelope["workspace_attempt_id"]),
    ):
        raise AF1OperatorError("RUN_EVIDENCE_INVALID")
    population_path = workspace / POPULATION_RESULT_FILENAME
    population = _json(population_path)
    if (
        not isinstance(population, dict) or set(population) != _POPULATION_RESULT_KEYS
        or population_path.read_bytes() != canonical_json_bytes(population)
        or canonical_sha256(population) != result["public_population_result_sha256"]
    ):
        raise AF1OperatorError("RUN_EVIDENCE_INVALID")
    state, reason = result["runtime_state"], result["terminal_reason"]
    manifest_mapping = result["benchmark_manifest"]
    real_mappings = result["real_case_evidence"]
    bodies = result["review_bodies"]
    count = result["controller_invocation_count"]
    if not isinstance(real_mappings, list) or not isinstance(bodies, list) or type(count) is not int:
        raise AF1OperatorError("RUN_EVIDENCE_INVALID")
    if reason == AF1_A1_REASON:
        if state != "RUNTIME_TERMINAL" or manifest_mapping is not None or real_mappings or bodies or count != 0:
            raise AF1OperatorError("RUN_EVIDENCE_INVALID")
        return result
    manifest = af1_record_from_mapping(AF1BenchmarkManifest, manifest_mapping)
    assert isinstance(manifest, AF1BenchmarkManifest)
    if (
        manifest.runtime_authorization_envelope_sha256 != envelope_digest
        or manifest.public_population_result_sha256 != result["public_population_result_sha256"]
        or manifest.phase_a_commit_sha != envelope["phase_a_commit_sha"]
        or manifest.base_sha != BASE_SHA
        or manifest.provider_label != envelope["provider_label"]
        or manifest.model_label != envelope["model_label"]
        or manifest.cutoff != population["captured_at_utc"]
        or manifest.actual_market_count != population["fetched_market_count"]
        or manifest.actual_order_book_count != population["fetched_order_book_count"]
    ):
        raise AF1OperatorError("RUN_EVIDENCE_INVALID")
    real = tuple(af1_record_from_mapping(AF1RealCaseEvidence, item) for item in real_mappings)
    if (
        len(real) != count or count > MAX_AF1_CASE_CALLS
        or tuple(item.case_id for item in real) != AF1_REAL_CASE_IDS[:count]
        or any(item.manifest_id != manifest.manifest_id for item in real)
        or any(item.terminal_reason is not None for item in real[:-1])
    ):
        raise AF1OperatorError("RUN_EVIDENCE_INVALID")
    if reason == AF1_A2_REASON:
        if state != "RUNTIME_TERMINAL" or manifest.coverage_terminal == "COMPLETE" or real or bodies:
            raise AF1OperatorError("RUN_EVIDENCE_INVALID")
        return result
    if manifest.coverage_terminal != "COMPLETE" or not real:
        raise AF1OperatorError("RUN_EVIDENCE_INVALID")
    if reason in AF1_REAL_CASE_TERMINAL_REASONS:
        if state != "RUNTIME_TERMINAL" or real[-1].terminal_reason != reason or bodies:
            raise AF1OperatorError("RUN_EVIDENCE_INVALID")
        if (reason == AF1_RUNTIME_UNAVAILABLE_REASON) != isinstance(result["known_within_limits"], bool):
            raise AF1OperatorError("RUN_EVIDENCE_INVALID")
        return result
    if state != "BLIND_REVIEW_REQUIRED" or reason is not None or count != 3 or real[-1].terminal_reason is not None:
        raise AF1OperatorError("RUN_EVIDENCE_INVALID")
    hashes = tuple(canonical_sha256(body) for body in bodies)
    if len(bodies) != 3 or hashes != tuple(item.review_body_sha256 for item in real) or len(set(hashes)) != 3:
        raise AF1OperatorError("RUN_EVIDENCE_INVALID")
    return result


def build_review_bundle(workspace: Path, *, repo_root: Path | None = None) -> Path:
    result = verify_run(workspace, repo_root=repo_root)
    if result["runtime_state"] != "BLIND_REVIEW_REQUIRED":
        raise AF1OperatorError("BLIND_REVIEW_NOT_APPLICABLE_BY_TERMINAL_PATH")
    wrappers = review_wrappers(result["review_bodies"])  # type: ignore[arg-type]
    path = workspace / REVIEW_BUNDLE_FILENAME
    if path.exists():
        raise AF1OperatorError("REVIEW_BUNDLE_ALREADY_EXISTS")
    members = [(REVIEW_INSTRUCTIONS_NAME, REVIEW_INSTRUCTIONS.encode("utf-8"))]
    members += [(f"{item['review_slot']}.json", canonical_json_bytes(item)) for item in wrappers]
    temporary = workspace / (REVIEW_BUNDLE_FILENAME + ".partial")
    with zipfile.ZipFile(temporary, "x", compression=zipfile.ZIP_STORED) as archive:
        for name, payload in members:
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            archive.writestr(info, payload)
    _write_exclusive_bytes(path, temporary.read_bytes())
    temporary.unlink()
    return path


def _review_wrappers_from_bundle(workspace: Path) -> tuple[dict[str, object], ...]:
    with zipfile.ZipFile(workspace / REVIEW_BUNDLE_FILENAME) as archive:
        names = sorted(archive.namelist())
        if names != sorted([REVIEW_INSTRUCTIONS_NAME, *(f"{slot}.json" for slot in AF1_REVIEW_SLOTS)]):
            raise AF1OperatorError("REVIEW_BUNDLE_INVALID")
        wrappers = []
        for slot in AF1_REVIEW_SLOTS:
            wrapper = json.loads(
                archive.read(f"{slot}.json").decode("utf-8"), object_pairs_hook=_unique_object,
                parse_constant=_reject_constant, parse_float=_reject_float,
            )
            if not isinstance(wrapper, dict) or set(wrapper) != {"schema_id", "schema_version", "review_slot", "review_body_sha256", "review_body"}:
                raise AF1OperatorError("REVIEW_BUNDLE_INVALID")
            wrappers.append(wrapper)
    return tuple(wrappers)


def verify_review(workspace: Path, review_path: Path, *, repo_root: Path | None = None) -> dict[str, dict[str, object]]:
    """Bind the Side12 decision to immutable real-case hashes; returns slot -> binding."""
    result = verify_run(workspace, repo_root=repo_root)
    if result["runtime_state"] != "BLIND_REVIEW_REQUIRED":
        raise AF1OperatorError("BLIND_REVIEW_NOT_APPLICABLE_BY_TERMINAL_PATH")
    real = [af1_record_from_mapping(AF1RealCaseEvidence, item) for item in result["real_case_evidence"]]  # type: ignore[union-attr]
    immutable = {item.review_body_sha256: item for item in real}  # type: ignore[union-attr]
    wrappers = _review_wrappers_from_bundle(workspace)
    recomputed = []
    for wrapper in wrappers:
        digest = canonical_sha256(wrapper["review_body"])
        if (
            wrapper["schema_id"] != REVIEW_WRAPPER_SCHEMA_ID or wrapper["schema_version"] != AF1_SCHEMA_VERSION
            or wrapper["review_body_sha256"] != digest or digest not in immutable
        ):
            raise AF1OperatorError("REVIEW_BUNDLE_INVALID")
        recomputed.append(digest)
    if len(set(recomputed)) != 3:
        raise AF1OperatorError("BLIND_REVIEW_PACKET_IDENTITY_COLLISION")
    slot_hash = dict(zip(AF1_REVIEW_SLOTS, sorted(recomputed), strict=True))
    if any(wrapper["review_slot"] not in slot_hash or slot_hash[wrapper["review_slot"]] != wrapper["review_body_sha256"] for wrapper in wrappers):
        raise AF1OperatorError("REVIEW_BUNDLE_INVALID")
    resolved = Path(review_path).resolve(strict=True)
    if resolved.parent != workspace.resolve(strict=True):
        raise AF1OperatorError("REVIEW_DECISION_INVALID")
    decision = _json(resolved)
    if (
        not isinstance(decision, dict)
        or set(decision) != {"schema_id", "schema_version", "reviewer_alias", "reviews"}
        or decision["schema_id"] != REVIEW_DECISION_SCHEMA_ID or decision["schema_version"] != "1.0.0"
        or decision["reviewer_alias"] != "SIDE12" or not isinstance(decision["reviews"], list)
        or len(decision["reviews"]) != 3
    ):
        raise AF1OperatorError("REVIEW_DECISION_INVALID")
    bindings: dict[str, dict[str, object]] = {}
    for item in decision["reviews"]:
        if not isinstance(item, dict) or set(item) != {"review_slot", "review_body_sha256", "label", "reason_codes"}:
            raise AF1OperatorError("REVIEW_DECISION_INVALID")
        slot, digest, label, reasons = item["review_slot"], item["review_body_sha256"], item["label"], item["reason_codes"]
        if (
            slot not in slot_hash or slot in bindings or digest != slot_hash[slot]
            or label not in AF1_REVIEW_LABELS or not isinstance(reasons, list) or not reasons
            or any(code not in AF1_REVIEW_REASON_CODES for code in reasons)
        ):
            raise AF1OperatorError("REVIEW_DECISION_INVALID")
        bindings[slot] = {"real_case": immutable[digest], "review_body_sha256": digest, "label": label, "reason_codes": list(reasons)}
    return bindings


def _finalize_evidence(workspace: Path, review_path: Path | None, repo_root: Path | None, *, replay_consistent: bool) -> dict[str, object]:
    result = verify_run(workspace, repo_root=repo_root)
    state, reason = result["runtime_state"], result["terminal_reason"]
    seeded = evaluate_seeded_af1_cases(
        phase_a_commit_sha=str(result["phase_a_commit_sha"]),
        wp_prompt_sha256=str(result["wp_prompt_sha256"]), wp_spec_sha256=str(result["wp_spec_sha256"]),
        gate_contract_sha256=str(result["gate_contract_sha256"]),
        alpha_discovery_policy_id=benchmark_discovery_policy().alpha_discovery_policy_id,
    )
    real = [af1_record_from_mapping(AF1RealCaseEvidence, item) for item in result["real_case_evidence"]]  # type: ignore[union-attr]
    reviews: list[AF1BlindReviewRecord] = []
    labels: tuple[str, ...] = ()
    known_within = result["known_within_limits"] if reason == AF1_RUNTIME_UNAVAILABLE_REASON else None
    if state == "BLIND_REVIEW_REQUIRED":
        if review_path is None:
            raise AF1OperatorError("AF1_BLIND_REVIEW_REQUIRED")
        bindings = verify_review(workspace, review_path, repo_root=repo_root)
        by_case = {binding["real_case"].case_id: (slot, binding) for slot, binding in bindings.items()}  # type: ignore[union-attr]
        for case in real:
            slot, binding = by_case[case.case_id]  # type: ignore[union-attr]
            reviews.append(build_af1_blind_review_record({
                "schema_id": "af1-blind-review-record", "schema_version": "1.0.0", "blind_review_record_id": "",
                "real_case_evidence_id": case.real_case_evidence_id, "case_id": case.case_id,  # type: ignore[union-attr]
                "review_slot": slot, "review_body_sha256": binding["review_body_sha256"],
                "reviewer_alias": "SIDE12", "label": binding["label"], "reason_codes": binding["reason_codes"],
                **_AUTHORITY_FLAGS,
            }))
        labels = tuple(item.label for item in reviews)
        reason = AF1_REVIEW_COMPLETED_REASON
    elif review_path is not None:
        raise AF1OperatorError("BLIND_REVIEW_NOT_APPLICABLE_BY_TERMINAL_PATH")
    dimensions = derive_af1_dimension_statuses(
        terminal_reason=str(reason), seeded_results=seeded, known_within_limits=known_within,
        review_labels=labels, replay_consistent=replay_consistent,
    )
    manifest_mapping = result["benchmark_manifest"]
    receipt = build_af1_gate_receipt({
        "schema_id": "af1-gate-receipt", "schema_version": "1.0.0", "gate_receipt_id": "",
        "phase_a_commit_sha": result["phase_a_commit_sha"], "wp_prompt_sha256": result["wp_prompt_sha256"],
        "wp_spec_sha256": result["wp_spec_sha256"], "gate_contract_sha256": result["gate_contract_sha256"],
        "runtime_authorization_envelope_sha256": result["runtime_authorization_envelope_sha256"],
        "public_population_result_sha256": result["public_population_result_sha256"],
        "manifest_id": manifest_mapping["manifest_id"] if isinstance(manifest_mapping, dict) else None,
        "seeded_case_result_ids": [item.seeded_case_result_id for item in seeded],
        "real_case_evidence_ids": [item.real_case_evidence_id for item in real],  # type: ignore[union-attr]
        "blind_review_record_ids": [item.blind_review_record_id for item in reviews],
        "evidence_state": "FINALIZED", "terminal_reason": reason,
        "dimension_statuses": dimensions,
        "overall_disposition": _disposition(dimensions),
        **_AUTHORITY_FLAGS,
    })
    return {
        "schema_id": "s10-gate-af1-evidence", "schema_version": "1.0.0", "wp_id": WP_ID,
        "base_sha": BASE_SHA, "evidence_state": "FINALIZED",
        "phase_a_commit_sha": result["phase_a_commit_sha"], "wp_prompt_sha256": result["wp_prompt_sha256"],
        "wp_spec_sha256": result["wp_spec_sha256"], "gate_contract_sha256": result["gate_contract_sha256"],
        "runtime_authorization_envelope_sha256": result["runtime_authorization_envelope_sha256"],
        "public_population_result_sha256": result["public_population_result_sha256"],
        "benchmark_manifest": manifest_mapping,
        "seeded_case_results": [af1_record_to_mapping(item) for item in seeded],
        "real_case_evidence": [af1_record_to_mapping(item) for item in real],
        "blind_review_records": [af1_record_to_mapping(item) for item in reviews],
        "gate_receipt": af1_record_to_mapping(receipt),
    }


def _disposition(dimensions: Mapping[str, str]) -> str:
    if "FAIL" in dimensions.values():
        return "AF1_FAIL"
    if "INCONCLUSIVE" in dimensions.values():
        return "AF1_INCONCLUSIVE"
    return "AF1_PASS"


def finalize(workspace: Path, *, review_path: Path | None = None, repo_root: Path | None = None) -> dict[str, object]:
    """Deterministic finalization; an independent replay must reproduce identical bytes."""
    evidence = _finalize_evidence(workspace, review_path, repo_root, replay_consistent=True)
    replay = _finalize_evidence(workspace, review_path, repo_root, replay_consistent=True)
    if canonical_json_bytes(replay) != canonical_json_bytes(evidence):
        evidence = _finalize_evidence(workspace, review_path, repo_root, replay_consistent=False)
    verify_evidence(evidence, require_final=True)
    _write_exclusive(workspace / FINAL_EVIDENCE_FILENAME, evidence)
    return evidence


_FORBIDDEN_EVIDENCE_TEXT = ("local_data", "hermes_home", "\\users\\", "/home/", "/users/")


def _sanitized(value: object) -> bool:
    if isinstance(value, str):
        lowered = value.lower()
        return not any(token in lowered for token in _FORBIDDEN_EVIDENCE_TEXT) and re.match(r"^[a-z]:[\\/]", lowered) is None
    if isinstance(value, list):
        return all(_sanitized(item) for item in value)
    if isinstance(value, dict):
        return all(_sanitized(item) for item in value.values())
    return True


def verify_evidence(payload: object, *, require_final: bool) -> None:
    if not isinstance(payload, Mapping):
        raise AF1OperatorError("FINAL_EVIDENCE_INVALID")
    phase_a_keys = {
        "schema_id", "schema_version", "wp_id", "base_sha", "evidence_state",
        "benchmark_manifest", "gate_receipt",
    }
    final_keys = {
        "schema_id", "schema_version", "wp_id", "base_sha", "evidence_state",
        "phase_a_commit_sha", "wp_prompt_sha256", "wp_spec_sha256",
        "gate_contract_sha256", "runtime_authorization_envelope_sha256",
        "public_population_result_sha256",
        "benchmark_manifest", "seeded_case_results", "real_case_evidence",
        "blind_review_records", "gate_receipt",
    }
    if set(payload) not in (phase_a_keys, final_keys):
        raise AF1OperatorError("FINAL_EVIDENCE_INVALID")
    if payload["schema_id"] != "s10-gate-af1-evidence" or payload["schema_version"] != "1.0.0" or payload["wp_id"] != WP_ID or payload["base_sha"] != BASE_SHA:
        raise AF1OperatorError("FINAL_EVIDENCE_INVALID")
    if require_final and payload["evidence_state"] != "FINALIZED":
        raise AF1OperatorError("FINAL_EVIDENCE_INVALID")
    if payload["evidence_state"] == "PHASE_A_IMPLEMENTED_RUNTIME_NOT_AUTHORIZED":
        if set(payload) != phase_a_keys or payload["benchmark_manifest"] is not None or payload["gate_receipt"] is not None:
            raise AF1OperatorError("FINAL_EVIDENCE_INVALID")
        return
    if set(payload) != final_keys or payload["evidence_state"] != "FINALIZED" or not _sanitized(dict(payload)):
        raise AF1OperatorError("FINAL_EVIDENCE_INVALID")
    try:
        manifest_mapping = payload["benchmark_manifest"]
        manifest = None if manifest_mapping is None else af1_record_from_mapping(AF1BenchmarkManifest, manifest_mapping)
        seeded = tuple(af1_record_from_mapping(AF1SeededCaseResult, item) for item in payload["seeded_case_results"])
        real = tuple(af1_record_from_mapping(AF1RealCaseEvidence, item) for item in payload["real_case_evidence"])
        reviews = tuple(af1_record_from_mapping(AF1BlindReviewRecord, item) for item in payload["blind_review_records"])
        receipt = af1_record_from_mapping(AF1GateReceipt, payload["gate_receipt"])
    except (TypeError, ValueError) as exc:
        raise AF1OperatorError("FINAL_EVIDENCE_INVALID") from exc
    assert isinstance(receipt, AF1GateReceipt)
    if len(seeded) != len(AF1_SEEDED_CASE_IDS) or tuple(item.case_id for item in seeded) != AF1_SEEDED_CASE_IDS:
        raise AF1OperatorError("FINAL_EVIDENCE_INVALID")
    if tuple(item.seeded_case_result_id for item in seeded) != receipt.seeded_case_result_ids or tuple(item.real_case_evidence_id for item in real) != receipt.real_case_evidence_ids or tuple(item.blind_review_record_id for item in reviews) != receipt.blind_review_record_ids:
        raise AF1OperatorError("FINAL_EVIDENCE_INVALID")
    for key in ("phase_a_commit_sha", "wp_prompt_sha256", "wp_spec_sha256", "gate_contract_sha256", "runtime_authorization_envelope_sha256", "public_population_result_sha256"):
        if getattr(receipt, key) != payload[key]:
            raise AF1OperatorError("FINAL_EVIDENCE_INVALID")
    for item in seeded:
        if (item.phase_a_commit_sha, item.wp_prompt_sha256, item.wp_spec_sha256, item.gate_contract_sha256) != (payload["phase_a_commit_sha"], payload["wp_prompt_sha256"], payload["wp_spec_sha256"], payload["gate_contract_sha256"]):
            raise AF1OperatorError("FINAL_EVIDENCE_INVALID")
    population_digest = payload["public_population_result_sha256"]
    if manifest is None:
        if receipt.terminal_reason != AF1_A1_REASON or receipt.manifest_id is not None:
            raise AF1OperatorError("FINAL_EVIDENCE_INVALID")
    else:
        assert isinstance(manifest, AF1BenchmarkManifest)
        if (
            receipt.manifest_id != manifest.manifest_id
            or manifest.public_population_result_sha256 != population_digest
            or manifest.runtime_authorization_envelope_sha256 != payload["runtime_authorization_envelope_sha256"]
            or manifest.phase_a_commit_sha != payload["phase_a_commit_sha"]
            or any(item.manifest_id != manifest.manifest_id for item in real)
        ):
            raise AF1OperatorError("FINAL_EVIDENCE_INVALID")
    real_ids = {item.real_case_evidence_id: item for item in real}
    for review in reviews:
        case = real_ids.get(review.real_case_evidence_id)
        if case is None or case.review_body_sha256 != review.review_body_sha256 or case.case_id != review.case_id:
            raise AF1OperatorError("FINAL_EVIDENCE_INVALID")
    if reviews:
        ordered = sorted(item.review_body_sha256 for item in reviews)
        if any(AF1_REVIEW_SLOTS[ordered.index(item.review_body_sha256)] != item.review_slot for item in reviews):
            raise AF1OperatorError("FINAL_EVIDENCE_INVALID")
    known_within = None
    if receipt.terminal_reason == AF1_RUNTIME_UNAVAILABLE_REASON:
        costs = [Decimal(item.accepted_estimated_cost_usd) for item in real if item.accepted_estimated_cost_usd is not None]
        known_within = real[-1].accepted_estimated_cost_usd is not None and sum(costs, Decimal("0")) <= MAX_AGGREGATE_COST_USD
    labels = tuple(item.label for item in reviews)
    try:
        # Replay the closed derivation; the receipt's stored statuses must match it.
        expected = derive_af1_dimension_statuses(
            terminal_reason=receipt.terminal_reason, seeded_results=seeded,
            known_within_limits=known_within, review_labels=labels,
        )
    except ValueError as exc:
        raise AF1OperatorError("FINAL_EVIDENCE_INVALID") from exc
    stored = dict(receipt.dimension_statuses)
    if stored != expected and not (
        labels and {**expected, "RESEARCH_USEFULNESS_REPRODUCIBILITY": "FAIL"} == stored
    ):
        raise AF1OperatorError("FINAL_EVIDENCE_INVALID")


# ── CLI ───────────────────────────────────────────────────────────────────────


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("prepare", "verify-run", "build-review-bundle"):
        item = sub.add_parser(name)
        item.add_argument("--workspace", required=True)
    for name, required in (("verify-review", True), ("finalize", False)):
        item = sub.add_parser(name)
        item.add_argument("--workspace", required=True)
        item.add_argument("--review", required=required)
    real = sub.add_parser("run-real")
    real.add_argument("--workspace", required=True)
    real.add_argument("--activation-envelope", required=True)
    real.add_argument("--provider-label", required=True)
    real.add_argument("--model-label", required=True)
    real.add_argument("--acknowledgement", required=True)
    real.add_argument("--allow-public-network", action="store_true")
    real.add_argument("--allow-hermes-provider", action="store_true")
    real.add_argument("--hermes-executable", required=True)
    real.add_argument("--hermes-home", required=True)
    verify_final = sub.add_parser("verify-final")
    verify_final.add_argument("--evidence", type=Path, required=True)
    return parser


def _prepare(workspace: Path) -> None:
    _write(workspace / PREPARE_FILENAME, {
        "wp_id": WP_ID, "base_sha": BASE_SHA,
        "predecessor": {"pr_number": PREDECESSOR_PR, "head_sha": PREDECESSOR_HEAD_SHA, "merge_sha": PREDECESSOR_MERGE_SHA},
        "network_used": False, "controller_invocation_count": 0,
        "population_config": asdict(benchmark_population_config(allow_network=False)),
        "alpha_discovery_policy_id": benchmark_discovery_policy().alpha_discovery_policy_id,
        "hermes_invocation_policy_id": DEFAULT_HERMES_INVOCATION_POLICY.policy_id,
        "frozen_contract_digests": frozen_contract_digests(),
        "activation_envelope_keys": sorted(ACTIVATION_ENVELOPE_KEYS),
    })


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "verify-final":
            verify_evidence(_json(args.evidence), require_final=True)
            print("FINAL_EVIDENCE_VALID")
            return 0
        workspace = resolve_workspace(args.workspace)
        if args.command == "prepare":
            _prepare(workspace)
            print("AF1_PREPARED_ZERO_NETWORK")
            return 0
        if args.command == "run-real":
            if not (args.allow_public_network and args.allow_hermes_provider and args.acknowledgement == RUNTIME_ACKNOWLEDGEMENT):
                raise AF1OperatorError("AF1_RUNTIME_AUTHORIZATION_REQUIRED")
            envelope_path = Path(args.activation_envelope)
            envelope_path = envelope_path if envelope_path.is_absolute() else REPO_ROOT / envelope_path
            if envelope_path.resolve(strict=False) != workspace / ACTIVATION_ENVELOPE_FILENAME:
                raise AF1OperatorError("STATE_DRIFT")
            envelope, _ = load_activation_envelope(
                workspace, provider_label=args.provider_label, model_label=args.model_label,
            )
            result = execute_real_phase(
                workspace, envelope, provider_label=args.provider_label,
                model_label=args.model_label, hermes_executable=args.hermes_executable,
                hermes_home=args.hermes_home,
            )
            print(result["terminal_reason"] or result["runtime_state"])
            return 0
        if args.command == "verify-run":
            result = verify_run(workspace)
            print("RUN_EVIDENCE_VALID " + str(result["terminal_reason"] or result["runtime_state"]))
            return 0
        if args.command == "build-review-bundle":
            build_review_bundle(workspace)
            print("AF1_BLIND_REVIEW_REQUIRED")
            return 0
        review = None
        if args.review is not None:
            review = Path(args.review)
            review = review if review.is_absolute() else REPO_ROOT / review
        if args.command == "verify-review":
            verify_review(workspace, review)  # type: ignore[arg-type]
            print("REVIEW_DECISION_VALID")
            return 0
        evidence = finalize(workspace, review_path=review)
        print(evidence["gate_receipt"]["overall_disposition"])  # type: ignore[index]
        return 0
    except (AF1OperatorError, ValueError, OSError, zipfile.BadZipFile) as exc:
        reason = getattr(exc, "reason", None)
        print(str(exc) + (f" {reason}" if reason else ""), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
