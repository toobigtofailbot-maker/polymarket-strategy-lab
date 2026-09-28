"""Zero-network adversarial oracles for the S10-GATE-AF1 manual operator.

The end-to-end chain drives the REAL merged WP164A coordinator (fake public client),
REAL PIT stores, REAL ALPHA-02 universe/triage/allocation and the REAL HERMES-CTX
``run_blind_phase`` (fake Hermes backend).  No product, provider or Firecrawl call
is possible from these tests.
"""

from __future__ import annotations

import argparse
import dataclasses
import datetime
import hashlib
import json
import os
from dataclasses import asdict, fields, replace
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
import zipfile

import pytest

import tools.alpha.run_s10_gate_af1 as operator
from tools.alpha.run_s10_gate_af1 import (
    ACTIVATION_ENVELOPE_FILENAME,
    ACTIVATION_ENVELOPE_KEYS,
    POPULATION_INVOCATION_FILENAME,
    POPULATION_RESULT_FIELDS,
    POPULATION_RESULT_FILENAME,
    REVIEW_BUNDLE_FILENAME,
    REVIEW_DECISION_FILENAME,
    RUNTIME_ACKNOWLEDGEMENT,
    RUNTIME_RESULT_FILENAME,
    AF1OperatorError,
    benchmark_discovery_policy,
    benchmark_population_config,
    canonical_sha256,
    classify_public_population_result,
    context_campaign,
    context_store_root,
    exact_market_scope,
    execute_real_phase,
    invoke_public_population_once,
    main,
    map_hermes_terminal_status,
    persist_population_result,
    population_result_mapping,
    resolve_workspace,
    review_wrappers,
    validate_activation_envelope,
)
from src.data_layer.analytical_research.alpha_discovery import ObservedMarketState
from src.data_layer.analytical_research.alpha_factory_gate import (
    AF1BenchmarkManifest,
    AF1GateReceipt,
    af1_record_from_mapping,
)
from src.data_layer.point_in_time_market_research import polymarket_public_population as wp164
from src.data_layer.point_in_time_market_research.polymarket_public_population import (
    PolymarketPublicPopulationResult,
)
from src.data_layer.polymarket.models import AdapterResult, ReadOnlyRequestInfo
from src.research_runtime.hermes_controlled_runtime import (
    ContextArtifactStore,
    DEFAULT_HERMES_INVOCATION_POLICY,
    FakeHermesBackend,
    HermesInvocationOutcome,
    run_blind_phase,
)
from src.research_runtime.hermes_controlled_runtime.context_controller import _context_request


PHASE_SHA = "2" * 40
PROVIDER = "example-provider"
MODEL = "example-model"
CAPTURED = datetime.datetime(2026, 1, 2, 3, 4, 5, 123450, tzinfo=datetime.UTC)
CAPTURED_TEXT = "2026-01-02T03:04:05.123450Z"
HERMES_CANONICAL_CUTOFF = "2026-01-02T03:04:05.12345Z"


# ── Offline public-data and Hermes fakes ──────────────────────────────────────


def _request_info() -> ReadOnlyRequestInfo:
    return ReadOnlyRequestInfo(method="GET", url="https://example.invalid", status_code=200, latency_ms=1.0)


def _live_condition_id(gamma_id: str) -> str:
    """Live-shaped Polymarket condition id: 0x + exactly 64 lowercase hex digits."""
    return "0x" + hashlib.sha256(f"condition-{gamma_id}".encode()).hexdigest()


def _live_token_id(gamma_id: str, outcome: str) -> str:
    """Live-shaped CLOB token id: a 77-digit positive decimal string."""
    digest = int(hashlib.sha256(f"token-{gamma_id}-{outcome}".encode()).hexdigest(), 16)
    return str(10**76 + digest % (9 * 10**76))


def _gamma(gamma_id: str, *, question: str | None = None, category: str = "Sports") -> dict:
    # Live-shaped Gamma payload: the WP164A coordinator derives canonical
    # market:polymarket:<gamma id>, event:polymarket:0x<64 hex> and
    # token:polymarket:<decimal> refs from it, exactly as Attempt-03 observed.
    return {
        "id": gamma_id, "conditionId": _live_condition_id(gamma_id),
        "question": question if question is not None else f"Will public event {gamma_id} resolve Yes?",
        "active": True, "closed": False, "outcomes": json.dumps(["Yes", "No"]),
        "clobTokenIds": json.dumps([_live_token_id(gamma_id, "a"), _live_token_id(gamma_id, "b")]),
        "endDate": "2026-12-31", "category": category,
    }


def _book(token_id: str) -> dict:
    return {
        "asset_id": token_id, "bids": [{"price": "0.40", "size": "10"}],
        "asks": [{"price": "0.60", "size": "5"}], "tick_size": "0.01", "min_order_size": "1",
        "timestamp": "1700000000", "hash": "bookhash", "last_trade_price": "0.5",
    }


class FakePublicClient:
    def __init__(self, markets, *, fail=False):
        self.markets = markets
        self.fail = fail
        self.market_calls = 0
        self.book_calls: list[str] = []

    def get_markets(self, limit=None):
        self.market_calls += 1
        if self.fail:
            raise OSError("simulated public outage")
        return AdapterResult(data=self.markets[:limit], request_info=_request_info())

    def get_order_book_snapshot(self, token_id):
        self.book_calls.append(token_id)
        return AdapterResult(data=_book(token_id), request_info=_request_info())


def _usage(**overrides) -> bytes:
    doc = {
        "input_tokens": 50, "output_tokens": 80, "total_tokens": 130, "api_calls": 1,
        "estimated_cost_usd": 0.04, "cost_status": "estimated",
        "cost_source": "official_docs_snapshot", "model": MODEL, "provider": PROVIDER,
        "session_id": "s1", "completed": True, "failed": False,
    }
    doc.update(overrides)
    return json.dumps(doc).encode("utf-8")


def _context_stdout(request_id: str, subject_ref: str, url: str) -> bytes:
    doc = {
        "schema_version": "hermes-research-draft/1.0.0", "request_id": request_id,
        "research_summary": "Balanced public evidence for the frozen scope.", "confidence_label": "moderate",
        "evidence_for": ["support"], "evidence_against": ["counter"], "uncertainties": ["uncertain"],
        "known_missing_data": ["missing"], "falsification_checks_performed": ["searched for contrary evidence"],
        "limitations": ["public only"], "what_would_change_the_conclusion": ["new source"],
        "suggested_next_research_steps": ["observe"],
        "source_references": [{"url": url, "title": "A", "source_class": "reference"}],
        "context_claims": [{
            "claim_statement": "Public evidence supports the scoped claim.", "claim_kind": "INFERENCE",
            "subject_refs": [subject_ref], "direction": "SUPPORTING", "source_reference_indices": [0],
            "assumptions": ["the public source is accurate"], "uncertainty_note": "The record may be incomplete.",
        }],
    }
    for flag in (
        "advisory_only", "human_review_required", "no_execution_authority", "no_risk_override",
        "no_credential_request", "no_order_or_cancel_or_sign_or_submit", "no_paper_live_decision",
        "no_strategy_promotion_approval", "no_pr_approval_or_merge_readiness_claim",
    ):
        doc[flag] = True
    return json.dumps(doc).encode("utf-8")


def _timeout_outcome() -> HermesInvocationOutcome:
    return HermesInvocationOutcome(
        stdout=b"", stdout_truncated=False, stderr_byte_len=0, stderr_truncated=False,
        usage_file_bytes=None, usage_file_truncated=False, exit_code=None,
        timed_out=True, launch_failed=False, duration_ms=1,
    )


class BackendPlan:
    """Per-case backend factory; records every controller invocation."""

    def __init__(self, kinds=("ok", "ok", "ok"), *, usage=None):
        self.kinds = list(kinds)
        self.usage = usage or {}
        self.campaigns = []
        self.backends = []

    def __call__(self, campaign):
        kind = self.kinds[len(self.campaigns)]
        self.campaigns.append(campaign)
        if kind == "timeout":
            backend = FakeHermesBackend([_timeout_outcome(), _timeout_outcome()])
        else:
            request = _context_request(campaign)
            market_id = json.loads(campaign.exact_scope_json)["market_id"]
            usage = self.usage.get(len(self.campaigns), {})
            backend = FakeHermesBackend.from_transcript(
                _context_stdout(request.request_id, market_id, f"https://example.com/{market_id}"),
                usage_file_bytes=_usage(**usage),
            )
        self.backends.append(backend)
        return backend

    @property
    def physical_calls(self):
        return sum(item.call_count for item in self.backends)


# ── Repository / workspace / envelope fixtures ────────────────────────────────


@pytest.fixture
def repo(tmp_path, monkeypatch):
    root = tmp_path / "repo"
    for _, relative in operator.FROZEN_CONTRACT_PATHS:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(f"frozen {relative}\n".encode())
    monkeypatch.setattr(operator, "REPO_ROOT", root)
    return root


def _runtime(repo: Path, **probe_overrides) -> dict:
    """Machine-local launch parameters outside the repository plus an offline probe."""
    bin_dir = repo.parent / "hermes-runtime"
    bin_dir.mkdir(exist_ok=True)
    executable = bin_dir / "hermes.exe"
    if not executable.exists():
        executable.write_bytes(b"fake pinned executable")
    home = repo.parent / "research-home"
    home.mkdir(exist_ok=True)
    return {
        "hermes_executable": str(executable), "hermes_home": str(home),
        "preflight_backend": FakeHermesBackend([_timeout_outcome()], **probe_overrides),
    }


def _workspace(root: Path, attempt: str = "attempt-04", phase: str = PHASE_SHA) -> Path:
    workspace = root / "local_data" / "s10_gate_af1" / phase / attempt
    workspace.mkdir(parents=True)
    return workspace.resolve()


def _envelope(root: Path, workspace: Path, **overrides) -> dict:
    digests = operator.frozen_contract_digests(root)
    envelope = {
        "schema_id": "s10-gate-af1-runtime-authorization-envelope", "schema_version": "1.0.0",
        "wp_id": "S10-GATE-AF1", "base_sha": operator.BASE_SHA, "phase_a_commit_sha": PHASE_SHA,
        **digests, "workspace_attempt_id": "s10-gate-af1-" + workspace.name,
        "provider_label": PROVIDER, "model_label": MODEL,
        "hermes_invocation_policy_id": DEFAULT_HERMES_INVOCATION_POLICY.policy_id,
        **operator.WP164_LABELS, "markets_limit": 25, "order_books_limit": 1,
        "analysis_temporal_mode": "HISTORICAL_REPLAY",
        "alpha_memory_temporal_posture": "HISTORICAL_AVAILABILITY_UNPROVEN",
        "alpha_registry_path": None, "alpha_registry_head_entry_hash": None,
        "max_provider_calls": 3, "max_case_cost_usd": "5", "max_aggregate_cost_usd": "15",
        "retry_limit": 0, "provider_model_fallback": 0, "replacement_benchmark_case": 0,
        "fourth_call_authorized": False, "credentials_authorized": False,
        "scheduler_authorized": False, "strategy_qualification_economics_authorized": False,
        "paper_execution_authorized": False, "live_execution_authorized": False,
        "gate_c_authorized": False, "signing_or_orders_authorized": False,
        "h1_fifth_invocation_authorized": False, "merge_authorized": False,
    }
    envelope.update(overrides)
    (workspace / ACTIVATION_ENVELOPE_FILENAME).write_text(json.dumps(envelope), encoding="utf-8")
    return envelope


def _patch_population(monkeypatch, markets, *, fail=False, calls=None):
    calls = calls if calls is not None else []

    def coordinator(record_store, manifest_store, config):
        calls.append(config)
        return wp164.populate_initial_polymarket_public_data(
            record_store, manifest_store, config,
            client=FakePublicClient(markets, fail=fail), utcnow_provider=lambda: CAPTURED,
        )

    monkeypatch.setattr(operator, "populate_initial_polymarket_public_data", coordinator)
    return calls


def _run(repo, monkeypatch, *, markets=None, plan=None, fail=False):
    workspace = _workspace(repo)
    envelope = _envelope(repo, workspace)
    calls = _patch_population(monkeypatch, markets if markets is not None else [_gamma(str(100 + i)) for i in range(25)], fail=fail)
    plan = plan or BackendPlan()
    result = execute_real_phase(
        workspace, envelope, provider_label=PROVIDER, model_label=MODEL,
        repo_root=repo, backend_factory=plan, **_runtime(repo),
    )
    return workspace, result, calls, plan


def _result(**overrides) -> PolymarketPublicPopulationResult:
    values = dict(
        is_valid=True, status="POPULATION_PERSISTED_AND_REGISTERED", error_codes=(),
        record_store_error_codes=(), registration_error_codes=(), warning_codes=(),
        snapshot_id="snapshot", captured_at_utc="2026-09-23T00:00:00Z",
        requested_markets_limit=25, bounded_markets_limit=25,
        requested_order_books_limit=1, bounded_order_books_limit=1,
        fetched_market_count=2, fetched_order_book_count=1, built_record_count=3,
        inserted_record_count=3, dataset_snapshot_reference_id="reference",
        manifest_entry_id="entry", record_store_status="RECORD_STORE_APPEND_COMMITTED",
        registration_status="ADAPTER_PERSISTED", network_used=True,
        recovery_required=False, advisory_only=True, no_execution_authority=True,
        batch_is_valid=True, batch_status="VALID_WITH_WARNINGS", batch_error_codes=(),
        batch_warning_codes=("EVENT_TIME_MISSING_ALLOWED",),
        batch_accepted_record_version_ids=("r1", "r2", "r3"),
        canonical_batch_sha256="a" * 64,
    )
    values.update(overrides)
    return PolymarketPublicPopulationResult(**values)


def _stores(ids=("r1", "r2", "r3"), *, reference="reference", entry="entry", batch="a" * 64, empty=False):
    records = () if empty else tuple(SimpleNamespace(envelope=SimpleNamespace(record_version_id=item)) for item in ids)
    references = () if empty else (SimpleNamespace(
        dataset_snapshot_reference_id=reference, parameter_set_id=operator.WP164_LABELS["parameter_set_id"],
        validator_version=operator.WP164_LABELS["validator_version"], validated_batch_sha256=batch,
    ),)
    entries = () if empty else (SimpleNamespace(
        manifest_entry_id=entry, dataset_snapshot_reference_id=reference,
        manifest_id=operator.WP164_LABELS["manifest_id"], parameter_set_id=operator.WP164_LABELS["parameter_set_id"],
    ),)
    return (
        SimpleNamespace(is_valid=True, snapshot=SimpleNamespace(records=records)),
        SimpleNamespace(is_valid=True, snapshot=SimpleNamespace(dataset_references=references, manifest_entries=entries)),
    )


def _classify(result, stores=None):
    record, manifest = stores or _stores(tuple(result.batch_accepted_record_version_ids))
    return classify_public_population_result(
        population_result_mapping(result), record_store_result=record, manifest_store_result=manifest,
    )


# ── A. Exact current 38-field result ──────────────────────────────────────────


def test_population_result_contract_is_exact_current_38_fields():
    names = tuple(field.name for field in fields(PolymarketPublicPopulationResult))
    assert names == POPULATION_RESULT_FIELDS and len(POPULATION_RESULT_FIELDS) == 38
    mapping = population_result_mapping(_result())
    assert tuple(mapping) == POPULATION_RESULT_FIELDS or set(mapping) == set(POPULATION_RESULT_FIELDS)
    assert len(mapping) == 38
    assert mapping["batch_warning_codes"] == ["EVENT_TIME_MISSING_ALLOWED"]


def test_complete_result_is_written_read_back_and_digest_stable(tmp_path):
    mapping, digest = persist_population_result(tmp_path, _result())
    raw = (tmp_path / POPULATION_RESULT_FILENAME).read_bytes()
    assert raw == operator.canonical_json_bytes(mapping)
    assert digest == hashlib.sha256(raw).hexdigest() == canonical_sha256(mapping)
    assert set(json.loads(raw)) == set(POPULATION_RESULT_FIELDS)
    with pytest.raises(AF1OperatorError):  # exclusive: never overwritten or recycled
        persist_population_result(tmp_path, _result())


def test_non_typed_or_subclassed_result_is_local_defect(tmp_path):
    with pytest.raises(AF1OperatorError, match="PHASE_B_LOCAL_EVIDENCE_DEFECT"):
        persist_population_result(tmp_path, SimpleNamespace(**asdict(_result())))


def test_population_result_persistence_readback_mismatch_fails_closed(tmp_path, monkeypatch):
    original = operator._write_exclusive

    def corrupt(path, value):
        altered = dict(value)
        altered["fetched_market_count"] += 1
        original(path, altered)

    monkeypatch.setattr(operator, "_write_exclusive", corrupt)
    with pytest.raises(AF1OperatorError, match="PHASE_B_LOCAL_EVIDENCE_DEFECT"):
        persist_population_result(tmp_path, _result())


# ── B/C/D. Actual counts, warnings and fresh-success status ───────────────────


@pytest.mark.parametrize("markets,books", [(25, 1), (2, 1), (11, 0), (1, 0)])
def test_success_uses_actual_returned_counts_not_request_limits(markets, books):
    ids = tuple(f"r{i}" for i in range(markets + books))
    result = _result(
        fetched_market_count=markets, fetched_order_book_count=books,
        built_record_count=markets + books, inserted_record_count=markets + books,
        batch_accepted_record_version_ids=ids,
    )
    assert _classify(result) == "POPULATION_VALID"


@pytest.mark.parametrize("overrides", [
    dict(built_record_count=4),
    dict(inserted_record_count=2),
    dict(fetched_market_count=0, built_record_count=1, inserted_record_count=1),
    dict(batch_accepted_record_version_ids=("r1", "r2")),
    dict(batch_accepted_record_version_ids=("r1", "r1", "r2")),
    dict(bounded_markets_limit=17),
    dict(canonical_batch_sha256=None),
    dict(record_store_status="RECORD_STORE_APPENDED"),
    dict(registration_status="ADAPTER_ALREADY_PERSISTED"),
    dict(recovery_required=True),
    dict(captured_at_utc="2026-09-23T00:00:00"),
    dict(captured_at_utc=None),
    dict(batch_error_codes=("RECORD_VERSION_HASH_COLLISION_OR_MISMATCH",)),
    dict(batch_quarantined_record_version_ids=("r3",)),
    dict(batch_exact_duplicate_record_version_ids=("r3",)),
    dict(batch_is_valid=False),
    dict(build_status="BUILD_REJECTED"),
    dict(network_used=False),
])
def test_malformed_success_is_local_evidence_defect(overrides):
    with pytest.raises(AF1OperatorError, match="PHASE_B_LOCAL_EVIDENCE_DEFECT"):
        _classify(_result(**overrides), _stores())


def test_event_time_missing_warning_keeps_valid_population_and_is_retained():
    result = _result()
    assert _classify(result) == "POPULATION_VALID"
    assert population_result_mapping(result)["batch_warning_codes"] == ["EVENT_TIME_MISSING_ALLOWED"]


def test_already_registered_in_fresh_workspace_is_local_defect():
    with pytest.raises(AF1OperatorError, match="PHASE_B_LOCAL_EVIDENCE_DEFECT"):
        _classify(_result(status="POPULATION_ALREADY_REGISTERED"))


@pytest.mark.parametrize("stores", [
    _stores(("r1", "r2")),
    _stores(("r1", "r2", "rX")),
    _stores(reference="other"),
    _stores(entry="other"),
    _stores(batch="b" * 64),
])
def test_contradictory_store_evidence_is_local_defect(stores):
    with pytest.raises(AF1OperatorError, match="PHASE_B_LOCAL_EVIDENCE_DEFECT"):
        _classify(_result(), stores)


# ── E. A1 exactness ───────────────────────────────────────────────────────────


def _a1(code, **overrides):
    values = dict(
        is_valid=False, status="POPULATION_REJECTED", error_codes=(code,), snapshot_id=None,
        captured_at_utc=None, fetched_market_count=0, fetched_order_book_count=0,
        built_record_count=0, inserted_record_count=0, dataset_snapshot_reference_id=None,
        manifest_entry_id=None, record_store_status=None, registration_status=None,
        batch_is_valid=None, batch_status=None, batch_warning_codes=(),
        batch_accepted_record_version_ids=(), canonical_batch_sha256=None,
    )
    values.update(overrides)
    return _result(**values)


@pytest.mark.parametrize("code", ["POPULATION_FETCH_FAILED", "POPULATION_RESPONSE_INVALID"])
def test_a1_requires_exact_single_external_error_tuple(code):
    assert _classify(_a1(code), _stores(empty=True)) == "PUBLIC_POPULATION_EXTERNAL_UNAVAILABLE"
    for invalid in (
        _a1(code, network_used=False),
        _a1(code, error_codes=(code, "POPULATION_RESPONSE_INVALID")),
        _a1(code, error_codes=(code, "POPULATION_BUILD_FAILED")),
        _a1(code, build_status="BUILD_REJECTED"),
        _a1(code, batch_is_valid=False),
        _a1(code, inserted_record_count=1),
    ):
        with pytest.raises(AF1OperatorError, match="PHASE_B_LOCAL_EVIDENCE_DEFECT"):
            _classify(invalid, _stores(empty=True))
    with pytest.raises(AF1OperatorError, match="PHASE_B_LOCAL_EVIDENCE_DEFECT"):
        _classify(_a1(code), _stores())  # contradictory non-empty stores


@pytest.mark.parametrize("code", [
    "POPULATION_INPUT_INVALID", "POPULATION_RECORD_STORE_INVALID",
    "POPULATION_MANIFEST_STORE_INVALID", "POPULATION_RECORD_STORE_NOT_EMPTY",
    "POPULATION_POLICY_INVALID", "POPULATION_GUARD_DENIED", "POPULATION_BUILD_FAILED",
    "POPULATION_BATCH_INVALID", "POPULATION_RECORD_APPEND_FAILED",
    "POPULATION_REGISTRATION_FAILED", "POPULATION_RECOVERY_INVALID",
    "POPULATION_UNEXPECTED_ERROR",
])
def test_local_population_errors_never_become_a1(code):
    with pytest.raises(AF1OperatorError, match="PHASE_B_LOCAL_EVIDENCE_DEFECT"):
        _classify(_a1(code), _stores(empty=True))


def test_build_and_batch_diagnostics_are_retained_not_collapsed(tmp_path):
    build = _a1(
        "POPULATION_BUILD_FAILED", build_failure_observation_kind="ORDER_BOOK",
        build_status="BUILD_REJECTED", build_error_codes=("PAYLOAD_SEQUENCE_LIMIT_EXCEEDED",),
        build_quarantine_id="q", build_input_fingerprint_sha256="c" * 64,
    )
    mapping, _ = persist_population_result(tmp_path, build)
    assert mapping["build_error_codes"] == ["PAYLOAD_SEQUENCE_LIMIT_EXCEEDED"]
    assert mapping["build_input_fingerprint_sha256"] == "c" * 64
    with pytest.raises(AF1OperatorError, match="PHASE_B_LOCAL_EVIDENCE_DEFECT"):
        _classify(build, _stores(empty=True))


# ── F. Sentinel / process failure ─────────────────────────────────────────────


def test_population_sentinel_precedes_call_and_result_is_immediately_persisted(tmp_path, monkeypatch):
    workspace = tmp_path
    calls = []

    def fake(record_store, manifest_store, config):
        assert json.loads((workspace / POPULATION_INVOCATION_FILENAME).read_text(encoding="utf-8")) == {
            "schema_id": "s10-gate-af1-public-population-invocation", "schema_version": "1.0.0",
            "phase_a_commit_sha": PHASE_SHA, "runtime_authorization_envelope_sha256": "3" * 64,
            "workspace_attempt_id": "s10-gate-af1-attempt-04",
            "requested_markets_limit": 25, "requested_order_books_limit": 1, "invocation_state": "STARTED",
        }
        assert not (workspace / POPULATION_RESULT_FILENAME).exists()
        calls.append(config)
        return _result()

    monkeypatch.setattr(operator, "populate_initial_polymarket_public_data", fake)
    returned, mapping, digest = invoke_public_population_once(
        workspace, record_store=workspace / "r", manifest_store=workspace / "m",
        config=benchmark_population_config(allow_network=True), phase_a_commit_sha=PHASE_SHA,
        envelope_sha256="3" * 64, workspace_attempt_id="s10-gate-af1-attempt-04",
    )
    assert len(calls) == 1 and calls[0] == benchmark_population_config(allow_network=True)
    assert json.loads((workspace / POPULATION_RESULT_FILENAME).read_text(encoding="utf-8")) == mapping
    assert digest == canonical_sha256(mapping)


def test_exception_after_sentinel_is_permanently_nonretryable(tmp_path, monkeypatch):
    calls = 0

    def explode(*args, **kwargs):
        nonlocal calls
        calls += 1
        raise RuntimeError("simulated process failure")

    monkeypatch.setattr(operator, "populate_initial_polymarket_public_data", explode)
    kwargs = dict(
        record_store=tmp_path / "r", manifest_store=tmp_path / "m",
        config=benchmark_population_config(allow_network=True), phase_a_commit_sha=PHASE_SHA,
        envelope_sha256="3" * 64, workspace_attempt_id="s10-gate-af1-attempt-04",
    )
    with pytest.raises(AF1OperatorError, match="PHASE_B_LOCAL_EVIDENCE_DEFECT"):
        invoke_public_population_once(tmp_path, **kwargs)
    assert (tmp_path / POPULATION_INVOCATION_FILENAME).is_file()
    assert not (tmp_path / POPULATION_RESULT_FILENAME).exists()
    with pytest.raises(AF1OperatorError, match="PHASE_B_LOCAL_EVIDENCE_DEFECT"):
        invoke_public_population_once(tmp_path, **kwargs)
    assert calls == 1


def test_rerun_of_consumed_workspace_makes_zero_coordinator_or_provider_calls(repo, monkeypatch):
    workspace, _, calls, plan = _run(repo, monkeypatch)
    assert len(calls) == 1
    envelope = json.loads((workspace / ACTIVATION_ENVELOPE_FILENAME).read_text(encoding="utf-8"))
    second_plan = BackendPlan()
    with pytest.raises(AF1OperatorError, match="PHASE_B_LOCAL_EVIDENCE_DEFECT"):
        execute_real_phase(workspace, envelope, provider_label=PROVIDER, model_label=MODEL, repo_root=repo, **_runtime(repo), backend_factory=second_plan)
    assert len(calls) == 1 and second_plan.campaigns == []


def test_process_failure_after_sentinel_records_true_stop_and_blocks_rerun(repo, monkeypatch):
    workspace = _workspace(repo)
    envelope = _envelope(repo, workspace)
    monkeypatch.setattr(operator, "populate_initial_polymarket_public_data", lambda *a: (_ for _ in ()).throw(RuntimeError("x")))
    with pytest.raises(AF1OperatorError, match="PHASE_B_LOCAL_EVIDENCE_DEFECT"):
        execute_real_phase(workspace, envelope, provider_label=PROVIDER, model_label=MODEL, repo_root=repo, **_runtime(repo), backend_factory=BackendPlan())
    assert (workspace / POPULATION_INVOCATION_FILENAME).is_file()
    calls = _patch_population(monkeypatch, [_gamma("1")])
    with pytest.raises(AF1OperatorError):
        execute_real_phase(workspace, envelope, provider_label=PROVIDER, model_label=MODEL, repo_root=repo, **_runtime(repo), backend_factory=BackendPlan())
    assert calls == []


# ── End-to-end offline chain: G (cutoff), H (ALPHA-02), J (Hermes control) ────


def test_offline_chain_25_1_three_lanes_review_required(repo, monkeypatch):
    workspace, result, calls, plan = _run(repo, monkeypatch)
    assert len(calls) == 1 and result["runtime_state"] == "BLIND_REVIEW_REQUIRED"
    population = json.loads((workspace / POPULATION_RESULT_FILENAME).read_text(encoding="utf-8"))
    assert (population["fetched_market_count"], population["fetched_order_book_count"], population["built_record_count"]) == (25, 1, 26)
    manifest = af1_record_from_mapping(AF1BenchmarkManifest, result["benchmark_manifest"])
    assert manifest.coverage_terminal == "COMPLETE"
    assert (manifest.actual_market_count, manifest.actual_order_book_count) == (25, 1)
    assert manifest.public_population_result_sha256 == canonical_sha256(population)
    assert manifest.analysis_temporal_mode == "HISTORICAL_REPLAY"
    assert manifest.alpha_registry_head_entry_hash is None
    # Exactly three controller invocations, one physical backend call each here.
    assert result["controller_invocation_count"] == 3 and len(plan.campaigns) == 3 and plan.physical_calls == 3
    assert [item["case_id"] for item in result["real_case_evidence"]] == ["AF1-C1", "AF1-C2", "AF1-C3"]
    hashes = [item["review_body_sha256"] for item in result["real_case_evidence"]]
    assert hashes == [canonical_sha256(body) for body in result["review_bodies"]] and len(set(hashes)) == 3
    assert not (workspace / "local_data").exists()


def test_one_canonical_cutoff_even_after_delayed_processing(repo, monkeypatch):
    # The captured instant lies months before "now": no later wall clock is sampled.
    workspace, result, _, plan = _run(repo, monkeypatch)
    population = json.loads((workspace / POPULATION_RESULT_FILENAME).read_text(encoding="utf-8"))
    assert population["captured_at_utc"] == CAPTURED_TEXT
    assert result["benchmark_manifest"]["cutoff"] == CAPTURED_TEXT
    assert {campaign.information_cutoff for campaign in plan.campaigns} == {HERMES_CANONICAL_CUTOFF}
    assert datetime.datetime.fromisoformat(HERMES_CANONICAL_CUTOFF.replace("Z", "+00:00")) == CAPTURED


def test_cutoff_chain_rejects_substituted_later_cutoff():
    universe = SimpleNamespace(as_of=CAPTURED_TEXT)
    later = SimpleNamespace(information_cutoff="2026-01-02T03:04:06Z")
    with pytest.raises(AF1OperatorError, match="PHASE_B_LOCAL_EVIDENCE_DEFECT"):
        operator._require_cutoff_chain(CAPTURED_TEXT, universe, (later,))
    with pytest.raises(AF1OperatorError, match="PHASE_B_LOCAL_EVIDENCE_DEFECT"):
        operator._require_cutoff_chain(CAPTURED_TEXT, SimpleNamespace(as_of="2026-01-02T03:04:06Z"), ())


def test_cli_reuses_exact_historical_alpha02_and_exact_identity_hermes_scope_contract(repo, monkeypatch):
    seen = {}
    original = operator.build_pre_allocation_triage_bases

    def spy(*args, **kwargs):
        seen.update(kwargs)
        return original(*args, **kwargs)

    monkeypatch.setattr(operator, "build_pre_allocation_triage_bases", spy)
    monkeypatch.setattr(
        "src.data_layer.analytical_research.alpha_discovery.load_and_verify_alpha_factory_registry",
        lambda *a, **k: pytest.fail("no Alpha registry may be read"), raising=False,
    )
    workspace, result, _, _ = _run(repo, monkeypatch)
    assert seen == {
        "analysis_temporal_mode": "HISTORICAL_REPLAY",
        "alpha_memory_temporal_posture": "HISTORICAL_AVAILABILITY_UNPROVEN",
        "alpha_registry_path": None, "prior": None, "material_changes": (),
    }
    assert not any(path.suffix == ".sqlite3" and "alpha" in path.name for path in workspace.iterdir())


def test_three_same_category_markets_fill_core_exploration_audit(repo, monkeypatch):
    markets = [_gamma(str(100 + i), category="Sports") for i in range(3)]
    workspace, result, _, plan = _run(repo, monkeypatch, markets=markets)
    manifest = result["benchmark_manifest"]
    assert manifest["coverage_terminal"] == "COMPLETE"
    assert None not in (manifest["selected_core_triage_id"], manifest["selected_exploration_triage_id"], manifest["selected_audit_triage_id"])
    assert len(plan.campaigns) == 3
    # Two of the three markets have no order book: capture gaps do not block selection.
    population = json.loads((workspace / POPULATION_RESULT_FILENAME).read_text(encoding="utf-8"))
    assert population["fetched_order_book_count"] == 1


def test_missing_lane_is_a2_with_zero_hermes_calls(repo, monkeypatch):
    workspace, result, _, plan = _run(repo, monkeypatch, markets=[_gamma("100"), _gamma("101")])
    assert result["terminal_reason"] == "BENCHMARK_REQUIRED_LANE_ABSENT"
    assert result["benchmark_manifest"]["coverage_terminal"] == "REQUIRED_LANE_ABSENT"
    assert result["benchmark_manifest"]["selected_audit_triage_id"] is None
    assert plan.campaigns == [] and result["controller_invocation_count"] == 0


def test_selected_market_without_question_text_is_a2_with_zero_hermes_calls(repo, monkeypatch):
    markets = [_gamma(str(100 + i), question="   ") for i in range(3)]
    workspace, result, _, plan = _run(repo, monkeypatch, markets=markets)
    assert result["terminal_reason"] == "BENCHMARK_REQUIRED_LANE_ABSENT"
    assert result["benchmark_manifest"]["coverage_terminal"] == "REQUIRED_LANE_NOT_RESEARCH_EXECUTABLE"
    assert plan.campaigns == []


def test_a1_external_unavailable_has_no_manifest_and_zero_hermes(repo, monkeypatch):
    workspace, result, calls, plan = _run(repo, monkeypatch, fail=True)
    assert result["terminal_reason"] == "PUBLIC_POPULATION_EXTERNAL_UNAVAILABLE"
    assert result["benchmark_manifest"] is None and plan.campaigns == [] and len(calls) == 1
    assert result["public_population_result_sha256"] == canonical_sha256(
        json.loads((workspace / POPULATION_RESULT_FILENAME).read_text(encoding="utf-8"))
    )


def test_runtime_stops_on_first_failed_real_case_and_never_retries(repo, monkeypatch):
    plan = BackendPlan(("ok", "timeout", "ok"))
    workspace, result, _, _ = _run(repo, monkeypatch, plan=plan)
    assert result["terminal_reason"] == "CONTROLLED_RUNTIME_UNAVAILABLE_TRUTHFULLY_CAPTURED"
    assert len(plan.campaigns) == 2 and result["controller_invocation_count"] == 2
    # The failed case was never retried by AF1: its queued second outcome is unused.
    assert plan.backends[1].call_count == 1
    assert result["real_case_evidence"][-1]["terminal_reason"] == "CONTROLLED_RUNTIME_UNAVAILABLE_TRUTHFULLY_CAPTURED"
    assert result["review_bodies"] == []


def test_cost_and_telemetry_rules_preserve_unknowns(repo, monkeypatch):
    plan = BackendPlan(usage={1: {"cost_status": "unknown", "estimated_cost_usd": None}})
    _, result, _, _ = _run(repo, monkeypatch, plan=plan)
    assert result["terminal_reason"] in ("SUCCESSFUL_RUN_COST_UNKNOWN",)
    assert result["real_case_evidence"][0]["accepted_estimated_cost_usd"] is None
    assert len(plan.campaigns) == 1


@pytest.mark.parametrize("kind,expected", [
    ("unexpected_tool", "UNEXPECTED_RESEARCH_TOOL"),
    ("case_cost", "CASE_COST_LIMIT_BREACH"),
    ("aggregate", "AGGREGATE_COST_LIMIT_BREACH"),
    ("authority", "AUTHORITY_BOUNDARY_BREACH"),
    ("unknown_cost", "SUCCESSFUL_RUN_COST_UNKNOWN"),
    ("bad_digest", "RESEARCH_OUTPUT_INVALID"),
])
def test_post_success_checks_use_sanitized_evidence_only(kind, expected):
    ref = SimpleNamespace(url_digest=hashlib.sha256(b"https://example.com/a").hexdigest(), source_class="reference")
    draft = SimpleNamespace(
        source_urls=("https://example.com/a",), source_references=(ref,), context_claims=(),
        research_summary="s", confidence_label="moderate", falsification_checks_performed=(),
    )
    artifact = SimpleNamespace(alpha_context_present=False)
    blind = SimpleNamespace(run_result=SimpleNamespace(validated_draft=draft), blind_artifact=artifact)
    flags = {name: True for name in operator._RECEIPT_AUTHORITY_FLAGS}
    receipt = SimpleNamespace(cost_status="estimated", estimated_cost_usd="1", **flags)
    session = SimpleNamespace(unexpected_tool_names=())
    total = Decimal("0")
    if kind == "unexpected_tool":
        session = SimpleNamespace(unexpected_tool_names=("terminal",))
    elif kind == "case_cost":
        receipt.estimated_cost_usd = "5.01"
    elif kind == "aggregate":
        total = Decimal("14.5")
    elif kind == "authority":
        receipt.no_live_authority = False
    elif kind == "unknown_cost":
        receipt.cost_status = "unknown"
    elif kind == "bad_digest":
        draft.source_references = (SimpleNamespace(url_digest="0" * 64, source_class="reference"),)
    reason, _, body = operator._inspect_success(blind_result=blind, receipt=receipt, session=session, exact_scope={"market_id": "m"}, accepted_total=total)
    assert reason == expected and body is None


def test_truthful_unknown_backend_attestation_is_not_fallback():
    ref = SimpleNamespace(url_digest=hashlib.sha256(b"https://example.com/a").hexdigest(), source_class="reference")
    draft = SimpleNamespace(source_urls=("https://example.com/a",), source_references=(ref,), context_claims=(), research_summary="s", confidence_label="moderate", falsification_checks_performed=())
    blind = SimpleNamespace(run_result=SimpleNamespace(validated_draft=draft), blind_artifact=SimpleNamespace(alpha_context_present=False))
    receipt = SimpleNamespace(cost_status="estimated", estimated_cost_usd="0.5", **{name: True for name in operator._RECEIPT_AUTHORITY_FLAGS})
    session = SimpleNamespace(unexpected_tool_names=(), actual_backend_attestation_status="NOT_DIRECTLY_ATTESTED", exact_provider_attempt_count="UNKNOWN")
    reason, cost, body = operator._inspect_success(blind_result=blind, receipt=receipt, session=session, exact_scope={"market_id": "m"}, accepted_total=Decimal("0"))
    assert reason is None and cost == Decimal("0.5") and body is not None


def test_hermes_exception_before_receipt_is_true_stop_and_consumes_case(repo, monkeypatch):
    def explode(**kwargs):
        raise RuntimeError("startup failure")

    monkeypatch.setattr(operator, "run_blind_phase", explode)
    workspace = _workspace(repo)
    envelope = _envelope(repo, workspace)
    _patch_population(monkeypatch, [_gamma(str(100 + i)) for i in range(3)])
    with pytest.raises(AF1OperatorError, match="PHASE_B_LOCAL_EVIDENCE_DEFECT"):
        execute_real_phase(workspace, envelope, provider_label=PROVIDER, model_label=MODEL, repo_root=repo, **_runtime(repo), backend_factory=BackendPlan())
    stop = json.loads((workspace / RUNTIME_RESULT_FILENAME).read_text(encoding="utf-8"))
    assert stop["runtime_state"] == "TRUE_STOP" and stop["controller_invocation_count"] == 1
    with pytest.raises(AF1OperatorError, match="RUNTIME_TRUE_STOP_NOT_FINALIZABLE"):
        operator.verify_run(workspace, repo_root=repo)


@pytest.mark.parametrize("status,action,reason", [
    ("VERSION_MISMATCH", "STOP", "PHASE_B_LOCAL_EVIDENCE_DEFECT"),
    ("STARTUP_PREFLIGHT_FAILED", "STOP", "PHASE_B_LOCAL_EVIDENCE_DEFECT"),
    ("TRANSPORT_FAILURE", "FINALIZE", "CONTROLLED_RUNTIME_UNAVAILABLE_TRUTHFULLY_CAPTURED"),
    ("TIMEOUT", "FINALIZE", "CONTROLLED_RUNTIME_UNAVAILABLE_TRUTHFULLY_CAPTURED"),
    ("EXIT_CODE_NONZERO", "FINALIZE", "CONTROLLED_RUNTIME_UNAVAILABLE_TRUTHFULLY_CAPTURED"),
    ("RESPONSE_CAPTURE_FAILED", "FINALIZE", "RESEARCH_OUTPUT_INVALID"),
    ("OUTPUT_SCHEMA_INVALID", "FINALIZE", "RESEARCH_OUTPUT_INVALID"),
    ("SAFETY_VALIDATION_FAILED", "FINALIZE", "RESEARCH_OUTPUT_INVALID"),
    ("USAGE_EVIDENCE_INVALID", "FINALIZE", "USAGE_EVIDENCE_INVALID"),
    ("PROVIDER_MODEL_MISMATCH", "FINALIZE", "PROVIDER_MODEL_MISMATCH"),
    ("COST_EVIDENCE_UNAVAILABLE", "FINALIZE", "SUCCESSFUL_RUN_COST_UNKNOWN"),
    ("BUDGET_EXCEEDED", "FINALIZE", "CASE_COST_LIMIT_BREACH"),
    ("RESEARCH_DRAFT_VALIDATED", "INSPECT_SUCCESS", None),
])
def test_actual_hermes_terminal_status_mapping_and_dimension_overrides(status, action, reason):
    assert map_hermes_terminal_status(status) == (action, reason)
    assert map_hermes_terminal_status(status, has_valid_receipt=False) == ("STOP", "PHASE_B_LOCAL_EVIDENCE_DEFECT")


def test_every_controller_terminal_status_is_mapped():
    from src.research_runtime.hermes_controlled_runtime import controller

    statuses = {value for name, value in vars(controller).items() if name.startswith("_STATUS_")}
    for status in statuses:
        map_hermes_terminal_status(status)
    with pytest.raises(AF1OperatorError):
        map_hermes_terminal_status("NEW_UNMAPPED_STATUS")


def test_af1_retry_is_zero_while_managed_hermes_recovery_stays_truthful():
    policy = DEFAULT_HERMES_INVOCATION_POLICY
    assert policy.api_max_retries == 1  # upstream same-provider recovery, not AF1 retry
    assert policy.managed_fallback_providers == ()
    assert (policy.web_backend, policy.web_search_backend, policy.web_extract_backend) == ("firecrawl",) * 3
    assert policy.keyless_fallback is False and policy.keyless_rescue is False
    assert operator.MAX_AF1_CASE_CALLS == 3


# ── I. Workspace and context-store root ───────────────────────────────────────


def test_relative_repository_root_workspace_resolves_absolute(repo):
    resolved = resolve_workspace(f"local_data/s10_gate_af1/{PHASE_SHA}/attempt-04", repo_root=repo)
    assert resolved.is_absolute()
    assert resolved == (repo / "local_data" / "s10_gate_af1" / PHASE_SHA / "attempt-04").resolve()
    root = context_store_root(resolved, 1)
    assert root.is_absolute() and root.parent.parent == resolved
    store = ContextArtifactStore(root)  # accepted: no ARTIFACT_PATH_INVALID
    assert store.root == root.resolve()


@pytest.mark.parametrize("raw", [
    "local_data/s10_gate_af1/../escape",
    "local_data/other/attempt-04",
    "local_data/s10_gate_af1",
    "../outside",
])
def test_workspace_escape_attempts_reject(repo, raw):
    with pytest.raises(AF1OperatorError):
        resolve_workspace(raw, repo_root=repo)


def test_absolute_workspace_outside_boundary_rejects(repo, tmp_path):
    with pytest.raises(AF1OperatorError, match="WORKSPACE_OUTSIDE_LOCAL_DATA"):
        resolve_workspace(str(tmp_path / "elsewhere"), repo_root=repo)


def test_symlink_workspace_escape_rejects(repo, tmp_path):
    boundary = repo / "local_data" / "s10_gate_af1"
    boundary.mkdir(parents=True)
    outside = tmp_path / "outside"
    outside.mkdir()
    try:
        os.symlink(outside, boundary / "link", target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symlink creation unavailable")
    with pytest.raises(AF1OperatorError):
        resolve_workspace("local_data/s10_gate_af1/link/attempt-04", repo_root=repo)


def test_unresolved_relative_context_root_is_never_passed(tmp_path):
    with pytest.raises(AF1OperatorError, match="WORKSPACE_PATH_INVALID"):
        context_store_root(Path("local_data/s10_gate_af1/x"), 1)
    with pytest.raises(Exception, match="ARTIFACT_PATH_INVALID"):
        ContextArtifactStore(Path("relative/context"))


# ── Activation envelope ───────────────────────────────────────────────────────


def test_activation_envelope_exact_closed_schema_and_digest(repo):
    workspace = _workspace(repo)
    envelope = _envelope(repo, workspace)
    assert set(envelope) == ACTIVATION_ENVELOPE_KEYS and len(ACTIVATION_ENVELOPE_KEYS) == 38
    validated, digest = validate_activation_envelope(envelope, workspace=workspace, provider_label=PROVIDER, model_label=MODEL, repo_root=repo)
    assert digest == canonical_sha256(envelope) == canonical_sha256(dict(reversed(list(envelope.items()))))


@pytest.mark.parametrize("mutation", [
    lambda value: value.pop("retry_limit"),
    lambda value: value.update(retry_limit=1),
    lambda value: value.update(retry_limit=False),
    lambda value: value.update(project_level_retry=0),
    lambda value: value.update(unknown_key=False),
    lambda value: value.update(base_sha="46bc862018208b30971228ed719c7e9337142b41"),
    lambda value: value.update(wp_prompt_sha256="0" * 64),
    lambda value: value.update(workspace_attempt_id="s10-gate-af1-attempt-02"),
    lambda value: value.update(merge_authorized=0),
    lambda value: value.update(max_provider_calls=4),
    lambda value: value.update(phase_a_commit_sha="3" * 40),
])
def test_activation_envelope_rejects_missing_nonzero_alias_unknown_and_stale(repo, mutation):
    workspace = _workspace(repo)
    envelope = _envelope(repo, workspace)
    mutation(envelope)
    with pytest.raises(AF1OperatorError, match="STATE_DRIFT"):
        validate_activation_envelope(envelope, workspace=workspace, provider_label=PROVIDER, model_label=MODEL, repo_root=repo)


@pytest.mark.parametrize("attempt", ["attempt-01", "attempt-02", "attempt-03"])
def test_consumed_attempt_workspaces_are_rejected(repo, attempt):
    workspace = _workspace(repo, attempt)
    envelope = _envelope(repo, workspace)
    with pytest.raises(AF1OperatorError, match="STATE_DRIFT"):
        validate_activation_envelope(envelope, workspace=workspace, provider_label=PROVIDER, model_label=MODEL, repo_root=repo)


@pytest.mark.parametrize("attempt", ["attempt-00", "attempt-05", "attempt-99"])
def test_only_attempt_04_is_authorizable_without_automatic_increment(repo, attempt):
    assert operator.AUTHORIZED_ATTEMPT_DIRECTORY == "attempt-04"
    assert "attempt-03" in operator.CONSUMED_ATTEMPT_DIRECTORIES
    workspace = _workspace(repo, attempt)
    envelope = _envelope(repo, workspace)
    with pytest.raises(AF1OperatorError, match="STATE_DRIFT"):
        validate_activation_envelope(envelope, workspace=workspace, provider_label=PROVIDER, model_label=MODEL, repo_root=repo)


def test_attempt_04_envelope_binds_attempt_04_identity(repo):
    workspace = _workspace(repo)
    envelope = _envelope(repo, workspace)
    assert workspace.name == "attempt-04" and envelope["workspace_attempt_id"] == "s10-gate-af1-attempt-04"
    assert len(envelope) == 38 and set(envelope) == ACTIVATION_ENVELOPE_KEYS
    assert (envelope["schema_id"], envelope["schema_version"]) == ("s10-gate-af1-runtime-authorization-envelope", "1.0.0")
    assert envelope["base_sha"] == operator.BASE_SHA == "1ccf42df0e95586b98c79a0bf912343f9c34df31"
    validate_activation_envelope(envelope, workspace=workspace, provider_label=PROVIDER, model_label=MODEL, repo_root=repo)


@pytest.mark.parametrize("mutation", [
    # Historical Attempt-03 identity / base cannot authorize Attempt-04.
    lambda value: value.update(workspace_attempt_id="s10-gate-af1-attempt-03"),
    lambda value: value.update(base_sha="15097f70f5f5358879fde73b2b30d26ecdb80402"),
    lambda value: value.update(phase_a_commit_sha="777b33d5e3eb3ae6814716f45f3dc6a8a673ed16"),
    lambda value: value.update(gate_contract_sha256="0" * 64),
    lambda value: value.update(wp_spec_sha256="0" * 64),
    # Type coercion is never accepted.
    lambda value: value.update(markets_limit="25"),
    lambda value: value.update(order_books_limit=1.0),
    lambda value: value.update(max_case_cost_usd=5),
    lambda value: value.update(fourth_call_authorized=0),
    lambda value: value.update(alpha_registry_path=""),
])
def test_attempt_03_envelope_or_coerced_values_cannot_authorize_attempt_04(repo, mutation):
    workspace = _workspace(repo)
    envelope = _envelope(repo, workspace)
    mutation(envelope)
    with pytest.raises(AF1OperatorError, match="STATE_DRIFT"):
        validate_activation_envelope(envelope, workspace=workspace, provider_label=PROVIDER, model_label=MODEL, repo_root=repo)


def test_historical_attempt_03_workspace_never_collides_with_attempt_04(repo, monkeypatch):
    historical = _workspace(repo, "attempt-03")
    historical_files = {
        ACTIVATION_ENVELOPE_FILENAME: b'{"historical": "attempt-03"}',
        POPULATION_INVOCATION_FILENAME: b'{"historical": "sentinel"}',
        POPULATION_RESULT_FILENAME: b'{"historical": "result"}',
    }
    for name, payload in historical_files.items():
        (historical / name).write_bytes(payload)
    workspace, result, calls, _ = _run(repo, monkeypatch)
    assert workspace.name == "attempt-04" and workspace.parent == historical.parent
    assert len(calls) == 1 and result["runtime_state"] == "BLIND_REVIEW_REQUIRED"
    # Fresh population into new empty Attempt-04 stores: nothing is imported from Attempt-03.
    assert (calls[0].markets_limit, calls[0].order_books_limit) == (25, 1)
    assert {path.name: path.read_bytes() for path in historical.iterdir()} == historical_files
    invocation = json.loads((workspace / POPULATION_INVOCATION_FILENAME).read_text(encoding="utf-8"))
    assert invocation["workspace_attempt_id"] == "s10-gate-af1-attempt-04"


# ── HERMES-CTX exact scope ────────────────────────────────────────────────────


def _market(question="Will the evidence resolve this market?"):
    return ObservedMarketState(
        market_id="m1", event_id="e1", market_status="open", condition_id="condition",
        token_ids=("token-b", "token-a", "token-b"), outcome_labels=("Yes", "No"),
        resolution_date="2026-12-31", category="Test", question_text=question,
        metadata_record_version_id="record", metadata_observed_time="2026-09-23T00:00:00Z",
        metadata_freshness="FRESH", metadata_query_spec_sha256="1" * 64,
        rule_query_spec_sha256="2" * 64, book_query_spec_sha256="3" * 64,
        rules=(), books=(), data_gap_codes=(),
    )


def test_exact_scope_key_scope_json_and_subject_refs():
    scope_key, exact_scope, subject_refs = exact_market_scope(_market())
    assert exact_scope == {"market_id": "m1", "event_id": "e1", "token_ids": ["token-a", "token-b"]}
    assert scope_key == "af1-market-scope:" + hashlib.sha256(b"m1").hexdigest()
    assert subject_refs == tuple(sorted({"m1", "e1", "token-a", "token-b"}))
    campaign = context_campaign(_market(), cutoff=CAPTURED_TEXT, provider_label=PROVIDER, model_label=MODEL, phase_a_commit_sha=PHASE_SHA)
    assert json.loads(campaign.exact_scope_json) == exact_scope
    assert campaign.research_question == operator.RESEARCH_QUESTION
    assert campaign.allowed_public_research_classes == ("public_web",)
    assert campaign.policy_id == DEFAULT_HERMES_INVOCATION_POLICY.policy_id
    assert campaign.base_repo_code_identity == PHASE_SHA
    assert (campaign.requested_provider_label, campaign.requested_model_label) == (PROVIDER, MODEL)


def test_real_campaign_is_accepted_by_run_blind_phase(tmp_path):
    campaign = context_campaign(_market(), cutoff=CAPTURED_TEXT, provider_label=PROVIDER, model_label=MODEL, phase_a_commit_sha=PHASE_SHA)
    backend = BackendPlan()(campaign)
    blind = run_blind_phase(campaign=campaign, store=ContextArtifactStore(tmp_path / "ctx"), backend=backend, policy=DEFAULT_HERMES_INVOCATION_POLICY)
    assert blind.run_result.receipt.terminal_status == "RESEARCH_DRAFT_VALIDATED"
    body = operator.review_body_from_blind_result(exact_scope={"market_id": "m1"}, blind_result=blind)
    assert set(body) == {"research_scope", "research_summary", "confidence_label", "sources", "falsification_checks_performed", "context_claims"}


# ── Live-shaped canonical public identifiers (post-S10-HERMES-CTX-03) ────────
#
# Cross-layer AF1 regression for the Attempt-03 stop: the AF1 case construction →
# ContextCampaignScope → public_market_context → build_research_run_request →
# run_blind_phase seam must carry live-shaped canonical refs to the (offline, fake)
# Hermes backend. The full HERMES-CTX-03 negative matrix is owned by that package.

LIVE_MARKET_ID = "market:polymarket:516710"
LIVE_EVENT_ID = "event:polymarket:0x" + hashlib.sha256(b"af1-live-shaped-condition").hexdigest()
LIVE_TOKEN_IDS = (
    "token:polymarket:" + _live_token_id("516710", "yes"),
    "token:polymarket:" + _live_token_id("516710", "no"),
)
CANONICAL_MARKET_RE = r"market:polymarket:[1-9][0-9]*"
CANONICAL_EVENT_RE = r"event:polymarket:0x[0-9a-f]{64}"
CANONICAL_TOKEN_RE = r"token:polymarket:[1-9][0-9]{69,77}"


def _live_market():
    return replace(_market(), market_id=LIVE_MARKET_ID, event_id=LIVE_EVENT_ID, token_ids=LIVE_TOKEN_IDS)


def test_live_shaped_fixture_matches_attempt_03_identifier_shapes():
    import re

    assert re.fullmatch(CANONICAL_MARKET_RE, LIVE_MARKET_ID)
    assert re.fullmatch(CANONICAL_EVENT_RE, LIVE_EVENT_ID) and len(LIVE_EVENT_ID) == len("event:polymarket:0x") + 64
    for token in LIVE_TOKEN_IDS:
        digits = token[len("token:polymarket:"):]
        assert re.fullmatch(CANONICAL_TOKEN_RE, token) and 70 <= len(digits) <= 78
    # The generic long-hex secret rule (global, unchanged by CTX-03) flags the event id alone.
    from src.research_runtime.hermes_controlled_runtime import models as hermes_models

    assert hermes_models._LONG_HEX_SECRET_PATTERN.search(LIVE_EVENT_ID)


def test_live_shaped_canonical_refs_reach_offline_hermes_backend_through_af1_seam(tmp_path):
    campaign = context_campaign(_live_market(), cutoff=CAPTURED_TEXT, provider_label=PROVIDER, model_label=MODEL, phase_a_commit_sha=PHASE_SHA)
    assert set(campaign.subject_refs) == {LIVE_MARKET_ID, LIVE_EVENT_ID, *LIVE_TOKEN_IDS}
    assert json.loads(campaign.exact_scope_json) == {"market_id": LIVE_MARKET_ID, "event_id": LIVE_EVENT_ID, "token_ids": sorted(LIVE_TOKEN_IDS)}
    request = _context_request(campaign)  # public_market_context → build_research_run_request
    for ref in (LIVE_MARKET_ID, LIVE_EVENT_ID, *LIVE_TOKEN_IDS):
        assert ref in request.public_market_context
    backend = BackendPlan()(campaign)
    blind = run_blind_phase(campaign=campaign, store=ContextArtifactStore(tmp_path / "ctx"), backend=backend, policy=DEFAULT_HERMES_INVOCATION_POLICY)
    assert backend.call_count == 1  # the fake/offline backend was reached; no real process
    assert blind.run_result.receipt.terminal_status == "RESEARCH_DRAFT_VALIDATED"


def test_live_shaped_regression_fails_if_pre_ctx03_long_hex_false_positive_returns(tmp_path, monkeypatch):
    from src.research_runtime.hermes_controlled_runtime import models as hermes_models

    campaign = context_campaign(_live_market(), cutoff=CAPTURED_TEXT, provider_label=PROVIDER, model_label=MODEL, phase_a_commit_sha=PHASE_SHA)
    backend = BackendPlan()(campaign)
    # Reintroduce the pre-CTX-03 behaviour: the ordinary strict scan on public_market_context.
    monkeypatch.setattr(hermes_models, "_require_public_market_context", hermes_models._require_str)
    with pytest.raises(Exception, match="REQUEST_SECRET_DETECTED"):
        run_blind_phase(campaign=campaign, store=ContextArtifactStore(tmp_path / "ctx"), backend=backend, policy=DEFAULT_HERMES_INVOCATION_POLICY)
    assert backend.call_count == 0  # exactly the Attempt-03 stop: before any Hermes launch


def test_live_shaped_population_chain_reaches_offline_backend_for_all_three_cases(repo, monkeypatch):
    import re

    workspace, result, calls, plan = _run(repo, monkeypatch)
    assert len(calls) == 1 and result["runtime_state"] == "BLIND_REVIEW_REQUIRED"
    assert len(plan.campaigns) == 3 and plan.physical_calls == 3
    for campaign in plan.campaigns:
        scope = json.loads(campaign.exact_scope_json)
        assert re.fullmatch(CANONICAL_MARKET_RE, scope["market_id"])
        assert re.fullmatch(CANONICAL_EVENT_RE, scope["event_id"])
        assert scope["token_ids"] and all(re.fullmatch(CANONICAL_TOKEN_RE, token) for token in scope["token_ids"])


# ── L/M. Blind review, finalization, identity ─────────────────────────────────


def test_blind_wrappers_are_hash_sorted_and_hide_internal_identity():
    wrappers = review_wrappers(tuple({"research_scope": {"market_id": value}} for value in ("b", "a", "c")))
    hashes = tuple(item["review_body_sha256"] for item in wrappers)
    assert hashes == tuple(sorted(hashes))
    assert tuple(item["review_slot"] for item in wrappers) == ("REVIEW-01", "REVIEW-02", "REVIEW-03")
    for item in wrappers:
        assert set(item) == {"schema_id", "schema_version", "review_slot", "review_body_sha256", "review_body"}
        assert "AF1-C" not in json.dumps(item)
        assert item["review_body_sha256"] == canonical_sha256(item["review_body"])


def test_duplicate_review_hash_is_true_stop():
    with pytest.raises(AF1OperatorError, match="IDENTITY_COLLISION"):
        review_wrappers(({"same": True}, {"same": True}, {"other": True}))


def _decision(workspace, labels=("USEFUL_RESEARCH_OUTPUT",) * 3):
    with zipfile.ZipFile(workspace / REVIEW_BUNDLE_FILENAME) as archive:
        wrappers = [json.loads(archive.read(f"REVIEW-0{i}.json")) for i in (1, 2, 3)]
    decision = {
        "schema_id": "s10-gate-af1-side12-blind-review-decision", "schema_version": "1.0.0",
        "reviewer_alias": "SIDE12",
        "reviews": [
            {"review_slot": item["review_slot"], "review_body_sha256": item["review_body_sha256"], "label": label, "reason_codes": ["CLEAR_SCOPE"]}
            for item, label in zip(wrappers, labels)
        ],
    }
    path = workspace / REVIEW_DECISION_FILENAME
    path.write_text(json.dumps(decision), encoding="utf-8")
    return path, decision


def test_review_path_bundle_verify_finalize_and_verify_final(repo, monkeypatch):
    workspace, result, _, _ = _run(repo, monkeypatch)
    bundle = operator.build_review_bundle(workspace, repo_root=repo)
    with zipfile.ZipFile(bundle) as archive:
        assert sorted(archive.namelist()) == ["00_REVIEW_INSTRUCTIONS.txt", "REVIEW-01.json", "REVIEW-02.json", "REVIEW-03.json"]
        exposed = b"".join(archive.read(name) for name in archive.namelist())
    for hidden in (b"AF1-C", b"CORE_PRIORITY", b"EXPLORATION", b"AUDIT", PROVIDER.encode(), MODEL.encode(), b"estimated_cost"):
        assert hidden not in exposed
    path, _ = _decision(workspace)
    bindings = operator.verify_review(workspace, path, repo_root=repo)
    assert sorted(bindings) == ["REVIEW-01", "REVIEW-02", "REVIEW-03"]
    evidence = operator.finalize(workspace, review_path=path, repo_root=repo)
    receipt = af1_record_from_mapping(AF1GateReceipt, evidence["gate_receipt"])
    assert receipt.terminal_reason == "BLIND_REVIEW_COMPLETED" and receipt.overall_disposition == "AF1_PASS"
    assert receipt.public_population_result_sha256 == evidence["benchmark_manifest"]["public_population_result_sha256"]
    operator.verify_evidence(evidence, require_final=True)
    assert "local_data" not in json.dumps(evidence) and "https://" not in json.dumps(evidence)


def test_partial_usefulness_fails_and_tampered_decision_rejects(repo, monkeypatch):
    workspace, _, _, _ = _run(repo, monkeypatch)
    operator.build_review_bundle(workspace, repo_root=repo)
    path, decision = _decision(workspace, ("USEFUL_RESEARCH_OUTPUT", "PARTIALLY_USEFUL_RESEARCH_OUTPUT", "USEFUL_RESEARCH_OUTPUT"))
    tampered = json.loads(json.dumps(decision))
    tampered["reviews"][0]["review_body_sha256"] = "0" * 64
    path.write_text(json.dumps(tampered), encoding="utf-8")
    with pytest.raises(AF1OperatorError, match="REVIEW_DECISION_INVALID"):
        operator.verify_review(workspace, path, repo_root=repo)
    path.write_text(json.dumps(decision), encoding="utf-8")
    evidence = operator.finalize(workspace, review_path=path, repo_root=repo)
    assert evidence["gate_receipt"]["dimension_statuses"]["RESEARCH_USEFULNESS_REPRODUCIBILITY"] == "FAIL"
    assert evidence["gate_receipt"]["overall_disposition"] == "AF1_FAIL"


@pytest.mark.parametrize("scenario,reason,disposition", [
    ("a1", "PUBLIC_POPULATION_EXTERNAL_UNAVAILABLE", "AF1_INCONCLUSIVE"),
    ("a2", "BENCHMARK_REQUIRED_LANE_ABSENT", "AF1_INCONCLUSIVE"),
    ("timeout", "CONTROLLED_RUNTIME_UNAVAILABLE_TRUTHFULLY_CAPTURED", "AF1_INCONCLUSIVE"),
    ("unknown_cost", "SUCCESSFUL_RUN_COST_UNKNOWN", "AF1_FAIL"),
])
def test_early_terminals_finalize_without_review(repo, monkeypatch, scenario, reason, disposition):
    kwargs = {}
    if scenario == "a1":
        kwargs["fail"] = True
    elif scenario == "a2":
        kwargs["markets"] = [_gamma("100")]
    elif scenario == "timeout":
        kwargs["plan"] = BackendPlan(("timeout",))
    else:
        kwargs["plan"] = BackendPlan(usage={1: {"cost_status": "unknown", "estimated_cost_usd": None}})
    workspace, result, _, _ = _run(repo, monkeypatch, **kwargs)
    with pytest.raises(AF1OperatorError, match="BLIND_REVIEW_NOT_APPLICABLE_BY_TERMINAL_PATH"):
        operator.build_review_bundle(workspace, repo_root=repo)
    evidence = operator.finalize(workspace, repo_root=repo)
    receipt = evidence["gate_receipt"]
    assert receipt["terminal_reason"] == reason and receipt["overall_disposition"] == disposition
    assert len(receipt["dimension_statuses"]) == 10 and receipt["blind_review_record_ids"] == []
    assert (evidence["benchmark_manifest"] is None) == (scenario == "a1")
    assert receipt["public_population_result_sha256"] == result["public_population_result_sha256"]
    if scenario == "timeout":
        assert receipt["dimension_statuses"]["BUDGET"] == "INCONCLUSIVE"  # no known cost
    operator.verify_evidence(evidence, require_final=True)
    assert main(["verify-final", "--evidence", str(workspace / operator.FINAL_EVIDENCE_FILENAME)]) == 0


def test_population_digest_mutation_propagates_to_manifest_and_receipt(repo, monkeypatch):
    workspace, result, _, _ = _run(repo, monkeypatch)
    manifest = dict(result["benchmark_manifest"])
    mutated = {**manifest, "public_population_result_sha256": "f" * 64, "manifest_id": ""}
    rebuilt = operator.build_af1_benchmark_manifest(mutated)
    assert rebuilt.manifest_id != manifest["manifest_id"]


def test_verify_final_rejects_forged_dimensions(repo, monkeypatch):
    workspace, _, _, _ = _run(repo, monkeypatch, fail=True)
    evidence = operator.finalize(workspace, repo_root=repo)
    forged = json.loads(json.dumps(evidence))
    receipt = forged["gate_receipt"]
    receipt["dimension_statuses"]["PIT_PROVENANCE"] = "PASS"
    receipt["overall_disposition"] = "AF1_INCONCLUSIVE"
    receipt["gate_receipt_id"] = operator.build_af1_gate_receipt({**receipt, "gate_receipt_id": ""}).gate_receipt_id
    with pytest.raises(AF1OperatorError, match="FINAL_EVIDENCE_INVALID"):
        operator.verify_evidence(forged, require_final=True)


# ── CLI surface / N. authority ────────────────────────────────────────────────


def test_prepare_defaults_to_zero_network(repo):
    workspace = f"local_data/s10_gate_af1/{PHASE_SHA}/attempt-04"
    assert main(["prepare", "--workspace", workspace]) == 0
    payload = json.loads((repo / workspace / "AF1_PREPARE.json").read_text())
    assert payload["network_used"] is False and payload["controller_invocation_count"] == 0
    assert payload["population_config"] == {**operator.WP164_LABELS, "markets_limit": 25, "order_books_limit": 1, "allow_network": False}
    assert payload["activation_envelope_keys"] == sorted(ACTIVATION_ENVELOPE_KEYS)
    assert payload["predecessor"] == {"pr_number": 195, "head_sha": "ddc25d189359b6e365edcf08c762cb0552b7170a", "merge_sha": operator.BASE_SHA}


def test_run_real_requires_exact_explicit_activation(repo, monkeypatch):
    calls = _patch_population(monkeypatch, [_gamma("1")])
    workspace = _workspace(repo)
    _envelope(repo, workspace)
    env = _runtime(repo)
    base = ["run-real", "--workspace", str(workspace), "--activation-envelope", str(workspace / ACTIVATION_ENVELOPE_FILENAME), "--provider-label", PROVIDER, "--model-label", MODEL, "--hermes-executable", env["hermes_executable"], "--hermes-home", env["hermes_home"]]
    assert main([*base, "--acknowledgement", RUNTIME_ACKNOWLEDGEMENT]) == 2
    assert main([*base, "--acknowledgement", "yes", "--allow-public-network", "--allow-hermes-provider"]) == 2
    assert main([*base, "--acknowledgement", RUNTIME_ACKNOWLEDGEMENT, "--allow-public-network"]) == 2
    assert calls == [] and not (workspace / POPULATION_INVOCATION_FILENAME).exists()


def test_cli_default_and_prepare_paths_make_zero_network_or_provider_calls(repo, monkeypatch):
    monkeypatch.setattr(operator, "populate_initial_polymarket_public_data", lambda *a, **k: pytest.fail("network"))
    monkeypatch.setattr(operator, "run_blind_phase", lambda *a, **k: pytest.fail("provider"))
    workspace = f"local_data/s10_gate_af1/{PHASE_SHA}/attempt-04"
    assert main(["prepare", "--workspace", workspace]) == 0
    for command in (["verify-run"], ["build-review-bundle"], ["finalize"]):
        assert main([*command, "--workspace", workspace]) == 2


def test_placeholder_evidence_is_phase_a_only():
    root = Path(__file__).resolve().parents[3]
    payload = json.loads((root / "docs" / "gate_evidence" / "S10-GATE-AF1" / "af1_gate_evidence.json").read_text(encoding="utf-8"))
    assert payload == {
        "schema_id": "s10-gate-af1-evidence", "schema_version": "1.0.0", "wp_id": "S10-GATE-AF1",
        "base_sha": operator.BASE_SHA, "evidence_state": "PHASE_A_IMPLEMENTED_RUNTIME_NOT_AUTHORIZED",
        "benchmark_manifest": None, "gate_receipt": None,
    }
    operator.verify_evidence(payload, require_final=False)
    with pytest.raises(AF1OperatorError):
        operator.verify_evidence(payload, require_final=True)


def test_benchmark_policy_is_exact_uncalibrated_starting_policy():
    config = benchmark_population_config(allow_network=True)
    assert (config.markets_limit, config.order_books_limit, config.allow_network) == (25, 1, True)
    policy = benchmark_discovery_policy()
    assert policy.policy_version == "BENCHMARK_STARTING_POLICY_NOT_EMPIRICALLY_CALIBRATED"
    assert (policy.queue_capacity, policy.exploration_slots, policy.audit_slots, policy.max_per_category) == (3, 1, 1, 2)
    assert (policy.metadata_freshness_seconds, policy.order_book_freshness_seconds, policy.resolution_rule_freshness_seconds) == (60, 30, 120)


def test_cli_selects_exact_core_exploration_audit_cases_without_cherry_pick(repo, monkeypatch):
    markets = [_gamma(str(100 + i)) for i in range(6)]
    selections = []
    for phase, ordered in ((PHASE_SHA, markets), ("4" * 40, list(reversed(markets)))):
        workspace = _workspace(repo, phase=phase)
        envelope = _envelope(repo, workspace, phase_a_commit_sha=phase)
        _patch_population(monkeypatch, ordered)
        plan = BackendPlan()
        result = execute_real_phase(workspace, envelope, provider_label=PROVIDER, model_label=MODEL, repo_root=repo, **_runtime(repo), backend_factory=plan)
        manifest = result["benchmark_manifest"]
        selections.append((
            manifest["selected_core_triage_id"], manifest["selected_exploration_triage_id"],
            manifest["selected_audit_triage_id"], tuple(json.loads(c.exact_scope_json)["market_id"] for c in plan.campaigns),
        ))
    # Input order never changes the deterministic C1/C2/C3 selection.
    assert selections[0] == selections[1] and len(set(selections[0][:3])) == 3


def test_phase_continuation_freezes_code_contract_and_detects_state_drift(repo, monkeypatch):
    workspace = _workspace(repo)
    envelope = _envelope(repo, workspace)
    calls = _patch_population(monkeypatch, [_gamma("1")])
    # Post-authorization drift of a frozen gate-criterion file blocks the first call.
    contract = repo / "docs" / "alpha_factory_research_system_gate_contract.md"
    contract.write_bytes(contract.read_bytes() + b"drift\n")
    with pytest.raises(AF1OperatorError, match="STATE_DRIFT"):
        execute_real_phase(workspace, envelope, provider_label=PROVIDER, model_label=MODEL, repo_root=repo, **_runtime(repo), backend_factory=BackendPlan())
    assert calls == [] and not (workspace / POPULATION_INVOCATION_FILENAME).exists()
    # A workspace not bound to the envelope's Phase-A SHA is also drift.
    other = repo / "local_data" / "s10_gate_af1" / ("9" * 40) / "attempt-04"
    other.mkdir(parents=True)
    with pytest.raises(AF1OperatorError, match="STATE_DRIFT"):
        validate_activation_envelope(envelope, workspace=other.resolve(), provider_label=PROVIDER, model_label=MODEL, repo_root=repo)
    # A different authorized provider/model at run time is drift.
    with pytest.raises(AF1OperatorError, match="STATE_DRIFT"):
        validate_activation_envelope(envelope, workspace=workspace, provider_label="other", model_label=MODEL, repo_root=repo)


# ── Pre-sentinel Hermes runtime-environment preflight (oracles A-M) ───────────


def _preflight_case(repo, monkeypatch, **overrides):
    workspace = _workspace(repo)
    envelope = _envelope(repo, workspace)
    calls = _patch_population(monkeypatch, [_gamma(str(100 + i)) for i in range(3)])
    plan = BackendPlan()
    kwargs = {**_runtime(repo), **overrides}
    return workspace, envelope, calls, plan, kwargs


def _assert_unconsumed(workspace, calls, plan):
    assert calls == [] and plan.campaigns == []
    for name in (POPULATION_INVOCATION_FILENAME, POPULATION_RESULT_FILENAME, RUNTIME_RESULT_FILENAME, "pit_records.sqlite3", "pit_manifests.sqlite3"):
        assert not (workspace / name).exists(), name


def _cli_base(repo, workspace):
    return ["run-real", "--workspace", str(workspace), "--activation-envelope", str(workspace / ACTIVATION_ENVELOPE_FILENAME),
            "--provider-label", PROVIDER, "--model-label", MODEL, "--acknowledgement", RUNTIME_ACKNOWLEDGEMENT,
            "--allow-public-network", "--allow-hermes-provider"]


@pytest.mark.parametrize("missing", ["--hermes-executable", "--hermes-home"])
def test_preflight_missing_runtime_argument_rejects_before_sentinel(repo, monkeypatch, missing):
    workspace, _, calls, plan, env = _preflight_case(repo, monkeypatch)
    args = _cli_base(repo, workspace)
    if missing != "--hermes-executable":
        args += ["--hermes-executable", env["hermes_executable"]]
    if missing != "--hermes-home":
        args += ["--hermes-home", env["hermes_home"]]
    with pytest.raises(SystemExit) as exc:
        main(args)
    assert exc.value.code == 2
    _assert_unconsumed(workspace, calls, plan)


@pytest.mark.parametrize("field,value,reason", [
    ("hermes_executable", "relative/hermes.exe", "HERMES_EXECUTABLE_INVALID"),
    ("hermes_executable", "", "HERMES_EXECUTABLE_INVALID"),
    ("hermes_executable", "MISSING", "HERMES_EXECUTABLE_INVALID"),
    ("hermes_executable", "DIRECTORY", "HERMES_EXECUTABLE_INVALID"),
    ("hermes_executable", "INSIDE_REPO", "HERMES_EXECUTABLE_INVALID"),
    ("hermes_executable", "TRAVERSAL", "HERMES_EXECUTABLE_INVALID"),
    ("hermes_home", "relative/home", "HERMES_HOME_INVALID"),
    ("hermes_home", "MISSING", "HERMES_HOME_INVALID"),
    ("hermes_home", "INSIDE_REPO", "HERMES_HOME_INVALID"),
    ("hermes_home", "INSIDE_LOCAL_DATA", "HERMES_HOME_INVALID"),
    ("hermes_home", "TRAVERSAL", "HERMES_HOME_INVALID"),
])
def test_preflight_invalid_paths_reject_before_sentinel(repo, monkeypatch, field, value, reason):
    workspace, envelope, calls, plan, env = _preflight_case(repo, monkeypatch)
    outside = repo.parent
    if value == "MISSING":
        value = str(outside / "absent" / ("hermes.exe" if field == "hermes_executable" else "home"))
    elif value == "DIRECTORY":
        value = str(outside)
    elif value == "INSIDE_REPO":
        target = repo / "tools" / ("hermes.exe" if field == "hermes_executable" else "home")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"x") if field == "hermes_executable" else target.mkdir(exist_ok=True)
        value = str(target)
    elif value == "INSIDE_LOCAL_DATA":
        target = outside / "local_data" / "home"
        target.mkdir(parents=True, exist_ok=True)
        value = str(target)
    elif value == "TRAVERSAL":
        value = str(Path(env[field]).parent / ".." / Path(env[field]).parent.name / Path(env[field]).name)
    env[field] = value
    with pytest.raises(AF1OperatorError, match="PHASE_B_LOCAL_EVIDENCE_DEFECT") as exc:
        execute_real_phase(workspace, envelope, provider_label=PROVIDER, model_label=MODEL, repo_root=repo, backend_factory=plan, **env)
    assert exc.value.reason == reason
    assert env["preflight_backend"].version_probe_count == 0  # nothing launched
    _assert_unconsumed(workspace, calls, plan)


@pytest.mark.parametrize("overrides,reason", [
    ({"version_text": "hermes-agent 0.21.4"}, "HERMES_VERSION_PREFLIGHT_FAILED"),
    ({"version_text": None}, "HERMES_VERSION_PREFLIGHT_FAILED"),
    ({"version_launched": False}, "HERMES_VERSION_PREFLIGHT_FAILED"),
    ({"version_timed_out": True}, "HERMES_VERSION_PREFLIGHT_FAILED"),
    ({"version_exit_code": 1}, "HERMES_VERSION_PREFLIGHT_FAILED"),
    ({"version_stdout_truncated": True}, "HERMES_VERSION_PREFLIGHT_FAILED"),
    ({"startup_exit_code": 1}, "HERMES_STARTUP_PREFLIGHT_FAILED"),
    ({"startup_launched": False}, "HERMES_STARTUP_PREFLIGHT_FAILED"),
    ({"startup_timed_out": True}, "HERMES_STARTUP_PREFLIGHT_FAILED"),
])
def test_preflight_version_or_startup_failure_rejects_before_sentinel(repo, monkeypatch, overrides, reason):
    workspace, envelope, calls, plan, env = _preflight_case(repo, monkeypatch)
    env["preflight_backend"] = FakeHermesBackend([_timeout_outcome()], **overrides)
    with pytest.raises(AF1OperatorError, match="PHASE_B_LOCAL_EVIDENCE_DEFECT") as exc:
        execute_real_phase(workspace, envelope, provider_label=PROVIDER, model_label=MODEL, repo_root=repo, backend_factory=plan, **env)
    assert exc.value.reason == reason
    assert env["preflight_backend"].call_count == 0  # probes only; never a research invocation
    _assert_unconsumed(workspace, calls, plan)


@pytest.mark.parametrize("marker", ["config.yaml", "SOUL.md", "plugins/plugin.py"])
def test_preflight_unclean_research_home_rejects_before_sentinel(repo, monkeypatch, marker):
    workspace, envelope, calls, plan, env = _preflight_case(repo, monkeypatch)
    target = Path(env["hermes_home"]) / marker
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(b"x")
    with pytest.raises(AF1OperatorError, match="PHASE_B_LOCAL_EVIDENCE_DEFECT") as exc:
        execute_real_phase(workspace, envelope, provider_label=PROVIDER, model_label=MODEL, repo_root=repo, backend_factory=plan, **env)
    assert exc.value.reason == "HERMES_HOME_CONTROL_PLANE_INVALID"
    _assert_unconsumed(workspace, calls, plan)


def test_preflight_symlink_alias_cannot_bypass_boundary(repo, monkeypatch):
    workspace, envelope, calls, plan, env = _preflight_case(repo, monkeypatch)
    alias = repo.parent / "alias-home"
    try:
        os.symlink(env["hermes_home"], alias, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symlink creation unavailable")
    env["hermes_home"] = str(alias)
    with pytest.raises(AF1OperatorError, match="PHASE_B_LOCAL_EVIDENCE_DEFECT"):
        execute_real_phase(workspace, envelope, provider_label=PROVIDER, model_label=MODEL, repo_root=repo, backend_factory=plan, **env)
    _assert_unconsumed(workspace, calls, plan)


def test_valid_environment_preflight_precedes_population_and_binds_exact_paths(repo, monkeypatch):
    workspace, envelope, _, plan, env = _preflight_case(repo, monkeypatch)
    order = []
    probe = env["preflight_backend"]
    original_version, original_startup = probe.probe_version, probe.probe_startup

    def version(**kwargs):
        order.append(("version", tuple(kwargs["version_argv"])))
        return original_version(**kwargs)

    def startup(**kwargs):
        order.append(("startup", tuple(kwargs["startup_argv"])))
        return original_startup(**kwargs)

    probe.probe_version, probe.probe_startup = version, startup
    calls = []

    def coordinator(record_store, manifest_store, config):
        assert (workspace / POPULATION_INVOCATION_FILENAME).is_file()
        order.append(("population", None))
        calls.append(config)
        return wp164.populate_initial_polymarket_public_data(
            record_store, manifest_store, config,
            client=FakePublicClient([_gamma(str(100 + i)) for i in range(3)]), utcnow_provider=lambda: CAPTURED,
        )

    monkeypatch.setattr(operator, "populate_initial_polymarket_public_data", coordinator)
    result = execute_real_phase(workspace, envelope, provider_label=PROVIDER, model_label=MODEL, repo_root=repo, backend_factory=plan, **env)
    exe, home = os.path.realpath(env["hermes_executable"]), os.path.realpath(env["hermes_home"])
    assert [item[0] for item in order] == ["version", "startup", "population"]
    assert order[0][1] == (exe, "--version") and order[1][1] == (exe, "--help")
    assert result["runtime_state"] == "BLIND_REVIEW_REQUIRED" and len(calls) == 1
    for backend in plan.backends:
        # Exact validated executable and research home reach every real case; no
        # PATH "hermes" or default-home substitution is possible.
        assert backend.recorded_argv and all(argv[0] == exe for argv in backend.recorded_argv)
        assert backend.recorded_startup_argv == [(exe, "--help")]
        assert backend.recorded_hermes_home == [home]
        assert all(argv[0] != "hermes" for argv in backend.recorded_argv)


def test_run_real_cli_passes_explicit_runtime_parameters(repo, monkeypatch):
    workspace, _, calls, plan, env = _preflight_case(repo, monkeypatch)
    seen = {}

    def fake_execute(workspace_arg, envelope_arg, **kwargs):
        seen.update(kwargs)
        return {"terminal_reason": None, "runtime_state": "BLIND_REVIEW_REQUIRED"}

    monkeypatch.setattr(operator, "execute_real_phase", fake_execute)
    args = _cli_base(repo, workspace) + ["--hermes-executable", env["hermes_executable"], "--hermes-home", env["hermes_home"]]
    assert main(args) == 0
    assert seen["hermes_executable"] == env["hermes_executable"] and seen["hermes_home"] == env["hermes_home"]
