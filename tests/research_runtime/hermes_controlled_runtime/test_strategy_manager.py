"""Focused tests for the S10-HERMES-STRAT-01 Hermes strategy manager core (R001-R069).

Every Hermes interaction uses a deterministic FakeHermesBackend subclass: zero process,
zero network and zero real provider/model calls.
"""

from __future__ import annotations

import ast
import dataclasses
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sqlite3

import pytest

from src.research_runtime.hermes_controlled_runtime import models as HM
from src.research_runtime.hermes_controlled_runtime import strategy_manager as sm
from src.research_runtime.hermes_controlled_runtime.context_reconciliation import (
    build_evidence_item,
)
from src.research_runtime.hermes_controlled_runtime.controller import (
    run_controlled_hermes_research,
)
from src.research_runtime.hermes_controlled_runtime.models import (
    DRAFT_AUTHORITY_FLAGS,
    DRAFT_SCHEMA_VERSION,
    NON_AUTHORITY_NOTICE,
    REQUEST_SCHEMA_VERSION,
    STRATEGY_ADAPTATION_FIELDS,
    STRATEGY_ADAPTATION_KINDS,
    STRATEGY_ASSESSMENT_FIELDS,
    STRATEGY_DRAFT_OUTPUT_CONTRACT_ID,
    STRATEGY_LIFECYCLE_ACTIONS,
    STRATEGY_RECOMMENDED_HEALTH_STATES,
    STRATEGY_REQUIRED_TOP_LEVEL_FIELDS,
    STRATEGY_RISK_DIRECTIONS,
    STRATEGY_TARGET_RISK_BANDS,
    HermesResearchError,
    ValidatedStrategyAssessmentDraft,
    build_research_draft_output_schema,
    build_research_run_request,
    check_strategy_assessment_consistency,
    validate_research_draft,
)
from src.research_runtime.hermes_controlled_runtime.policy import (
    DEFAULT_HERMES_INVOCATION_POLICY,
    PolicyBroadeningError,
    build_research_envelope,
)
from src.research_runtime.hermes_controlled_runtime.runner import (
    FakeHermesBackend,
    HermesInvocationOutcome,
)
from src.strategy_lifecycle import (
    HEALTH_STATES,
    RISK_BANDS,
    append_strategy_lifecycle_record,
    build_portfolio_authority_policy,
    build_portfolio_policy_receipt,
    build_strategy_family,
    build_strategy_health_receipt,
    build_strategy_restriction_receipt,
    build_strategy_risk_allocation,
    build_strategy_version,
    canonical_json_bytes,
    initialize_strategy_lifecycle_store,
    load_strategy_lifecycle_store,
)

ROOT = Path(__file__).resolve().parents[3]
MODULE = ROOT / "src" / "research_runtime" / "hermes_controlled_runtime" / "strategy_manager.py"
SPEC = ROOT / "docs" / "wp_specs" / "S10-HERMES-STRAT-01" / "wp_spec.json"
CUTOFF = "2026-10-01T00:00:00Z"
FIXED = datetime(2026, 10, 1, 12, 0, 0, tzinfo=timezone.utc)
EVENT = "event:polymarket:0x" + "1" * 64
MARKET = "market:polymarket:123"
EXEC_MARKER = "exec-rule-marker-xyz"

STRATEGY_SPEC = {
    "thesis": {"claim": "weather forecast skill is underpriced near resolution"},
    "universe": {"category": "weather", "markets": [MARKET]},
    "entry_rule": {"signal": "forecast_gap_above"},
    "exit_rule": {"horizon": "resolution"},
    "execution_rule": {"style": "PASSIVE_MAKER", "marker": EXEC_MARKER},
    "parameters": {"lookback": 5, "edge": "0.5", "mode": "A"},
}
BOUNDS = {"lookback": {"kind": "INTEGER_RANGE", "min": 0, "max": 10}}
LIMITS = {
    "global_capital_at_risk_max_usd": "1000", "global_gross_exposure_max_usd": "1000",
    "global_daily_loss_max_usd": "100", "global_drawdown_max_usd": "200",
    "global_cumulative_loss_max_usd": "300", "exploratory_pool_max_usd": "300",
    "validated_pool_max_usd": "300", "mature_pool_max_usd": "300",
    "max_exploratory_per_strategy_usd": "100", "max_validated_per_strategy_usd": "200",
    "max_mature_per_strategy_usd": "300", "max_per_market_usd": "50",
    "max_order_notional_usd": "10", "max_active_strategies": 3, "max_active_markets": 10,
    "max_simultaneous_open_orders": 20, "max_mutations_per_minute": 60,
}


# ---------------------------------------------------------------------------
# Lifecycle world (real verified STRAT-LIFE replay snapshots)
# ---------------------------------------------------------------------------


@dataclasses.dataclass
class World:
    path: Path
    fam1: object
    fam2: object
    v1: object
    v2: object
    pol: object

    def append(self, record):
        result = append_strategy_lifecycle_record(self.path, record)
        assert result.is_valid, result.error_codes
        return result.snapshot

    def snapshot(self):
        result = load_strategy_lifecycle_store(self.path)
        assert result.is_valid
        return result.snapshot


def _policy(label="Global envelope", predecessor=None, created=10):
    return build_portfolio_authority_policy(
        predecessor_policy_id=predecessor, policy_label=label,
        account_scope_ref="account:public-scope-1", effective_from_ns=created,
        expires_at_ns=None, allowed_order_styles=("PASSIVE_MAKER",), created_time_ns=created,
        **LIMITS,
    )


def _version(fam, *, spec=None, label="v1", code="strategy_code:v1"):
    return build_strategy_version(
        strategy_family_id=fam.strategy_family_id, parent=None, strategy_label=label,
        evidence_posture="EVENT_INFORMATION", strategy_code_identity=code,
        strategy_spec=STRATEGY_SPEC if spec is None else spec, adaptive_bounds=BOUNDS,
        evidence_refs=(), created_time_ns=2, creation_provenance="unit:fixture",
    )


def make_world(tmp_path: Path, *, spec=None) -> World:
    path = tmp_path / "lifecycle.sqlite3"
    assert initialize_strategy_lifecycle_store(path).is_valid
    fam1 = build_strategy_family(family_key="alpha.family", family_label="Alpha", created_time_ns=1, creation_provenance="unit:fixture")
    fam2 = build_strategy_family(family_key="beta.family", family_label="Beta", created_time_ns=1, creation_provenance="unit:fixture")
    v1 = _version(fam1, spec=spec)
    v2 = _version(fam2, label="v2", code="strategy_code:v2")
    pol = _policy()
    world = World(path, fam1, fam2, v1, v2, pol)
    for record in (fam1, fam2, v1, v2, pol, _activate(pol)):
        world.append(record)
    return world


def _activate(pol, previous=None, t=20):
    return build_portfolio_policy_receipt(
        action="ACTIVATE", policy_id=pol.policy_id, previous_active_policy_id=previous,
        human_authorization_ref="human:karl-approval-1", created_time_ns=t,
    )


def _health(ver, previous, new, t=50):
    return build_strategy_health_receipt(
        strategy_version_id=ver.strategy_version_id, previous_health_state=previous,
        new_health_state=new, decision_ref="decision:health-1", created_time_ns=t,
    )


def _restriction(ver, key="pause.1", t=60):
    return build_strategy_restriction_receipt(
        strategy_version_id=ver.strategy_version_id, restriction_key=key, action="APPLY",
        restriction_kind="PAUSE_NEW_EXPOSURE", max_active_budget_usd=None,
        decision_ref="decision:restrict-1", created_time_ns=t,
    )


def _allocation(ver, pol, budget="50"):
    return build_strategy_risk_allocation(
        strategy_version_id=ver.strategy_version_id, policy_id=pol.policy_id,
        risk_band="EXPLORATORY_LIVE", active_budget_usd=budget, allocation_basis="DIRECT_DECISION",
        decision_ref="decision:unit-1", evidence_refs=(), valid_from_ns=100, valid_until_ns=None,
        created_time_ns=100,
    )


# ---------------------------------------------------------------------------
# Deterministic fake backend and drafts
# ---------------------------------------------------------------------------


def _usage(**overrides) -> bytes:
    doc = {
        "input_tokens": 50, "output_tokens": 80, "total_tokens": 130, "api_calls": 1,
        "estimated_cost_usd": 0.04, "cost_status": "estimated",
        "cost_source": "official_docs_snapshot", "model": "example-model",
        "provider": "example-provider", "session_id": "s1", "completed": True, "failed": False,
    }
    doc.update(overrides)
    return json.dumps(doc).encode("utf-8")


def _assessment(**overrides) -> dict:
    value = {
        "lifecycle_action": "CONTINUE",
        "recommended_health_state": "HEALTHY",
        "risk_direction": "UNCHANGED",
        "target_risk_band": None,
        "adaptation_recommendation": None,
    }
    value.update(overrides)
    return value


def _draft(request_id: str, *, strategy=None, drop=(), **overrides) -> dict:
    draft = {
        "schema_version": DRAFT_SCHEMA_VERSION,
        "request_id": request_id,
        "research_summary": "Balanced public evidence; the edge looks intact but thin.",
        "evidence_for": ["forecast skill persists"],
        "evidence_against": ["liquidity is thin"],
        "uncertainties": ["seasonality"],
        "known_missing_data": ["no fill history"],
        "falsification_checks_performed": ["searched for contrary forecast-skill studies"],
        "limitations": ["public web only"],
        "what_would_change_the_conclusion": ["forecast skill collapse"],
        "suggested_next_research_steps": ["collect fill evidence"],
        "source_references": [{"url": "https://example.com/a", "title": "A", "source_class": "reference"}],
        "confidence_label": "moderate",
        "strategy_assessment": _assessment() if strategy is None else strategy,
    }
    for flag in DRAFT_AUTHORITY_FLAGS:
        draft[flag] = True
    draft.update(overrides)
    for key in drop:
        draft.pop(key)
    return draft


def _outcome(stdout: bytes, usage: bytes | None, **overrides) -> HermesInvocationOutcome:
    fields = dict(
        stdout=stdout, stdout_truncated=False, stderr_byte_len=0, stderr_truncated=False,
        usage_file_bytes=usage, usage_file_truncated=False, exit_code=0, timed_out=False,
        launch_failed=False, duration_ms=10,
    )
    fields.update(overrides)
    return HermesInvocationOutcome(**fields)


class StrategyBackend(FakeHermesBackend):
    """FakeHermesBackend whose single response is built from the envelope request id."""

    def __init__(self, respond=None, *, outcome=None, on_invoke=None, usage=None):
        super().__init__([_outcome(b"{}", None)])
        self.respond = respond or (lambda request_id, envelope: _draft(request_id))
        self.fixed_outcome = outcome
        self.on_invoke = on_invoke
        self.usage = _usage() if usage is None else usage
        self.prompts: list[str] = []

    def invoke(self, **kwargs):
        argv = kwargs["argv"]
        self.call_count += 1
        self.recorded_argv.append(tuple(argv))
        prompt = argv[argv.index("-z") + 1]
        self.prompts.append(prompt)
        if self.on_invoke is not None:
            self.on_invoke()
        if self.fixed_outcome is not None:
            return self.fixed_outcome
        envelope = json.loads(prompt)
        body = self.respond(envelope["request_id"], envelope)
        stdout = body if isinstance(body, bytes) else json.dumps(body).encode("utf-8")
        return _outcome(stdout, self.usage)


def _manager_store(tmp_path: Path) -> Path:
    path = tmp_path / "hermes_strategy.sqlite3"
    sm.initialize_hermes_strategy_manager_store(path)
    return path


def _evidence(world, *, subjects=None, cutoff="2026-09-30T00:00:00Z", status="ADMISSIBLE",
              content="b" * 64, summary="Deterministic fill-rate evidence supports the thesis."):
    item = build_evidence_item(
        content_sha256=content, evidence_class="DETERMINISTIC_DERIVED",
        subject_refs=subjects or (world.v1.strategy_version_id,), scope_sha256="c" * 64,
        information_cutoff=cutoff, admissibility_status=status,
        origin="DETERMINISTIC_PROJECT_EVIDENCE", direction="SUPPORTING",
    )
    return sm.build_strategy_assessment_evidence(item, summary)


def run(world, store, backend=None, version=None, **overrides):
    target = version or world.v1
    kwargs = dict(
        lifecycle_snapshot=world.snapshot(), strategy_version_id=target.strategy_version_id,
        trigger="INITIAL_ASSESSMENT", trigger_ref=None,
        subject_refs=(target.strategy_version_id, target.strategy_family_id), evidence=(),
        information_cutoff=CUTOFF, decision_time_ns=1_000, provider_label="example-provider",
        model_label="example-model", backend=backend or StrategyBackend(), store_path=store,
        clock=lambda: FIXED,
    )
    kwargs.update(overrides)
    return sm.run_hermes_strategy_assessment(**kwargs)


def _prompt(backend: StrategyBackend) -> dict:
    return json.loads(backend.prompts[-1])


def _rows(store: Path) -> list[tuple]:
    connection = sqlite3.connect(store)
    try:
        return connection.execute(
            "SELECT sequence_number, record_kind, record_id, strategy_version_id, payload_json,"
            " payload_sha256, previous_entry_hash, entry_hash FROM strategy_manager_records"
            " ORDER BY sequence_number"
        ).fetchall()
    finally:
        connection.close()


def _strategy_doc(rid="r", **strategy) -> str:
    return json.dumps(_draft(rid, strategy=_assessment(**strategy)))


def _validate(raw: str, rid="r", names=("edge", "lookback", "mode")):
    return validate_research_draft(
        raw, expected_request_id=rid, max_sources=8, strategy_mode=True,
        strategy_parameter_names=names,
    )


def _code(fn, *args, **kwargs) -> str:
    with pytest.raises((sm.StrategyManagerError, HermesResearchError)) as excinfo:
        fn(*args, **kwargs)
    return excinfo.value.code


def _sd(**fields) -> ValidatedStrategyAssessmentDraft:
    base = dict(
        lifecycle_action="CONTINUE", recommended_health_state="HEALTHY", risk_direction="UNCHANGED",
        target_risk_band=None, adaptation_kind=None, adaptation_summary=None,
        adaptation_parameter_updates_json=None, research_lists=(),
    )
    base.update(fields)
    return ValidatedStrategyAssessmentDraft(**base)


def _file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# ---------------------------------------------------------------------------
# Strategy context (R001-R008)
# ---------------------------------------------------------------------------


def test_r001_strategy_version_resolves_from_verified_snapshot(tmp_path):
    world = make_world(tmp_path)
    backend = StrategyBackend()
    result = run(world, _manager_store(tmp_path), backend)
    assert result.status == sm.STATUS_ASSESSMENT_RECORDED, result.error_code
    question = json.loads(_prompt(backend)["research_question"])
    assert question["strategy_identity"]["strategy_version_id"] == world.v1.strategy_version_id
    assert question["strategy_identity"]["strategy_family_id"] == world.v1.strategy_family_id
    assert question["strategy_identity"]["strategy_label"] == "v1"
    assert result.assessment.strategy_version_id == world.v1.strategy_version_id
    assert _code(sm.strategy_lifecycle_context_preimage, object(), world.v1.strategy_version_id) == "STRATEGY_CONTEXT_INVALID"


def test_r002_missing_strategy_version_rejects(tmp_path):
    world = make_world(tmp_path)
    backend = StrategyBackend()
    result = run(world, _manager_store(tmp_path), backend, strategy_version_id="strategyversion:sha256:" + "f" * 64)
    assert (result.status, result.error_code) == (sm.STATUS_REJECTED, "STRATEGY_NOT_FOUND")
    assert backend.call_count == backend.version_probe_count == 0


def test_r003_retired_strategy_rejects(tmp_path):
    world = make_world(tmp_path)
    world.append(_health(world.v1, "NEW", "RETIRED"))
    backend = StrategyBackend()
    result = run(world, _manager_store(tmp_path), backend)
    assert (result.status, result.error_code) == (sm.STATUS_REJECTED, "STRATEGY_RETIRED")
    assert backend.call_count == backend.version_probe_count == 0


def test_r004_context_fingerprint_is_deterministic(tmp_path):
    world = make_world(tmp_path)
    snap = world.snapshot()
    sid = world.v1.strategy_version_id
    first = sm.strategy_lifecycle_context_fingerprint(snap, sid)
    assert first == sm.strategy_lifecycle_context_fingerprint(world.snapshot(), sid)
    preimage = sm.strategy_lifecycle_context_preimage(snap, sid)
    assert first == hashlib.sha256(canonical_json_bytes(preimage)).hexdigest()
    assert len(first) == 64 and int(first, 16) >= 0
    assert set(preimage) == {
        "schema_id", "schema_version", "strategy_version_id", "current_health_state",
        "current_allocation", "active_restriction_receipt_ids", "active_policy_id",
    }


def test_r005_unrelated_strategy_change_keeps_target_fingerprint(tmp_path):
    world = make_world(tmp_path)
    sid1, sid2 = world.v1.strategy_version_id, world.v2.strategy_version_id
    before = world.snapshot()
    world.append(_health(world.v2, "NEW", "QUARANTINED"))
    after = world.append(_restriction(world.v2))
    assert before.store_head_entry_hash != after.store_head_entry_hash
    assert sm.strategy_lifecycle_context_fingerprint(before, sid1) == sm.strategy_lifecycle_context_fingerprint(after, sid1)
    assert sm.strategy_lifecycle_context_fingerprint(before, sid2) != sm.strategy_lifecycle_context_fingerprint(after, sid2)


def test_r006_target_health_allocation_restriction_change_alters_fingerprint(tmp_path):
    world = make_world(tmp_path)
    sid = world.v1.strategy_version_id
    prints = [sm.strategy_lifecycle_context_fingerprint(world.snapshot(), sid)]
    prints.append(sm.strategy_lifecycle_context_fingerprint(world.append(_health(world.v1, "NEW", "HEALTHY")), sid))
    prints.append(sm.strategy_lifecycle_context_fingerprint(world.append(_allocation(world.v1, world.pol)), sid))
    prints.append(sm.strategy_lifecycle_context_fingerprint(world.append(_restriction(world.v1, t=120)), sid))
    assert len(set(prints)) == 4


def test_r007_active_policy_change_alters_fingerprint(tmp_path):
    world = make_world(tmp_path)
    sid = world.v1.strategy_version_id
    active = sm.strategy_lifecycle_context_fingerprint(world.snapshot(), sid)
    revoked_snap = world.append(build_portfolio_policy_receipt(
        action="REVOKE", policy_id=world.pol.policy_id, previous_active_policy_id=world.pol.policy_id,
        human_authorization_ref="human:karl-revoke-1", created_time_ns=30,
    ))
    revoked = sm.strategy_lifecycle_context_fingerprint(revoked_snap, sid)
    pol2 = _policy(label="Second envelope", predecessor=world.pol.policy_id, created=40)
    world.append(pol2)
    replaced = sm.strategy_lifecycle_context_fingerprint(world.append(_activate(pol2, None, 41)), sid)
    assert len({active, revoked, replaced}) == 3
    assert sm.strategy_lifecycle_context_preimage(revoked_snap, sid)["active_policy_id"] is None


def test_r008_store_head_is_provenance_not_currentness_key(tmp_path):
    world = make_world(tmp_path)
    snap = world.snapshot()
    result = run(world, _manager_store(tmp_path))
    assert result.run_record.lifecycle_store_head_entry_hash == snap.store_head_entry_hash
    assert result.assessment.lifecycle_store_head_entry_hash == snap.store_head_entry_hash
    fingerprint = sm.strategy_lifecycle_context_fingerprint(snap, world.v1.strategy_version_id)
    assert result.run_record.strategy_lifecycle_context_sha256 == fingerprint != snap.store_head_entry_hash
    preimage = sm.strategy_lifecycle_context_preimage(snap, world.v1.strategy_version_id)
    assert snap.store_head_entry_hash not in json.dumps(preimage)


# ---------------------------------------------------------------------------
# Evidence (R009-R016)
# ---------------------------------------------------------------------------


def test_r009_evidence_wrapper_binds_canonical_item(tmp_path):
    world = make_world(tmp_path)
    item = build_evidence_item(
        content_sha256="b" * 64, evidence_class="RAW_DIRECT", subject_refs=(world.v1.strategy_version_id,),
        scope_sha256="c" * 64, information_cutoff="2026-09-30T00:00:00Z", admissibility_status="ADMISSIBLE",
        origin="DETERMINISTIC_PROJECT_EVIDENCE", direction="CONTRADICTING", dq_flags=("late_feed",),
        provenance_manifest_id="manifest:unit-1",
    )
    wrapped = sm.build_strategy_assessment_evidence(item, "Raw evidence contradicts the edge.")
    assert wrapped.evidence_id == item.evidence_id and wrapped.context_item() == item
    for name in ("content_sha256", "evidence_class", "subject_refs", "scope_sha256", "information_cutoff",
                 "admissibility_status", "provenance_manifest_id", "dq_flags", "origin", "direction"):
        assert getattr(wrapped, name) == getattr(item, name)
    forged = dataclasses.replace(item, evidence_id="contextevidence:sha256:" + "d" * 64)
    assert _code(sm.build_strategy_assessment_evidence, forged, "x summary") == "EVIDENCE_INVALID"
    tampered = dataclasses.replace(wrapped, summary="Different summary text.")
    assert run(world, _manager_store(tmp_path), evidence=(dataclasses.replace(wrapped, origin="FORGED_ORIGIN"),)).error_code == "EVIDENCE_INVALID"
    assert tampered.evidence_id == item.evidence_id


def test_r010_non_admissible_evidence_rejects(tmp_path):
    world = make_world(tmp_path)
    assert _code(_evidence, world, status="INADMISSIBLE") == "EVIDENCE_INVALID"
    assert _code(_evidence, world, status="admissible") == "EVIDENCE_INVALID"


def test_r011_evidence_newer_than_cutoff_rejects(tmp_path):
    world = make_world(tmp_path)
    backend = StrategyBackend()
    late = _evidence(world, cutoff="2026-10-01T00:00:01Z")
    result = run(world, _manager_store(tmp_path), backend, evidence=(late,))
    assert (result.status, result.error_code) == (sm.STATUS_REJECTED, "EVIDENCE_INVALID")
    assert backend.call_count == backend.version_probe_count == 0
    same = _evidence(world, cutoff=CUTOFF)
    assert run(world, _manager_store(tmp_path / "x" if (tmp_path / "x").mkdir() is None else tmp_path), evidence=(same,)).status == sm.STATUS_ASSESSMENT_RECORDED


def test_r012_evidence_without_subject_overlap_rejects(tmp_path):
    world = make_world(tmp_path)
    unrelated = _evidence(world, subjects=("market:polymarket:999",))
    result = run(world, _manager_store(tmp_path), evidence=(unrelated,))
    assert result.error_code == "EVIDENCE_INVALID"


def test_r013_duplicate_evidence_rejects(tmp_path):
    world = make_world(tmp_path)
    item = _evidence(world)
    assert run(world, _manager_store(tmp_path), evidence=(item, item)).error_code == "EVIDENCE_INVALID"


def test_r014_more_than_twelve_evidence_items_rejects(tmp_path):
    world = make_world(tmp_path)
    items = tuple(_evidence(world, content=f"{n:064x}", summary=("S" * 155) + f"{n:05d}") for n in range(13))
    assert all(len(item.summary) == 160 for item in items)
    assert len({item.evidence_id for item in items}) == 13
    assert run(world, _manager_store(tmp_path), evidence=items).error_code == "EVIDENCE_INVALID"
    assert run(world, _manager_store(tmp_path), evidence=items[:12]).status == sm.STATUS_ASSESSMENT_RECORDED


def test_r015_unsafe_evidence_summary_rejects(tmp_path):
    world = make_world(tmp_path)
    for summary in (
        "", "   ", "x" * 161, "the api_key value is here", "see /etc/passwd for detail",
        "C:\\data\\fills.csv shows", "load ../secret/fills", "data/fills.csv shows",
        "we should place an order now", "line\nbreak", 0x1, None,
        "wallet 0x" + "a" * 40,
    ):
        assert _code(_evidence, world, summary=summary) == "EVIDENCE_INVALID", summary
    assert _evidence(world, summary="x" * 160).summary == "x" * 160
    assert _evidence(world, summary="See https://example.com/report for detail.").summary


def test_r016_bounded_evidence_and_public_polymarket_subjects_succeed(tmp_path):
    world = make_world(tmp_path)
    item = _evidence(world, subjects=(MARKET, EVENT), summary="Public market context supports it.")
    backend = StrategyBackend()
    refs = (world.v1.strategy_version_id, world.v1.strategy_family_id, MARKET, EVENT)
    result = run(world, _manager_store(tmp_path), backend, subject_refs=refs, evidence=(item,))
    assert result.status == sm.STATUS_ASSESSMENT_RECORDED, result.error_code
    assert result.assessment.subject_refs == tuple(sorted(refs))
    assert result.assessment.input_evidence_refs == (item.evidence_id,)
    objective = json.loads(_prompt(backend)["research_objective"])
    assert objective["project_evidence"] == [{
        "evidence_index": 1, "evidence_class": "DETERMINISTIC_DERIVED", "direction": "SUPPORTING",
        "information_cutoff": "2026-09-30T00:00:00Z", "summary": item.summary,
    }]
    assert json.loads(_prompt(backend)["public_market_context"])["subject_refs"] == list(sorted(refs))
    for bad in (refs + ("wallet:0xabc",), refs + ("account:private-1",), refs + ("/tmp/x",),
                (world.v1.strategy_version_id,), refs + (refs[0],)):
        assert run(world, _manager_store(tmp_path), subject_refs=bad).error_code == "STRATEGY_CONTEXT_INVALID"


# ---------------------------------------------------------------------------
# Request / prompt (R017-R022)
# ---------------------------------------------------------------------------


def test_r017_strategy_request_uses_existing_research_request(tmp_path, monkeypatch):
    world = make_world(tmp_path)
    calls = []

    def counting(fields):
        request = build_research_run_request(fields)
        calls.append(request)
        return request

    monkeypatch.setattr(sm, "build_research_run_request", counting)
    backend = StrategyBackend()
    result = run(world, _manager_store(tmp_path), backend)
    assert len(calls) == 1
    request = calls[0]
    assert request.schema_version == REQUEST_SCHEMA_VERSION and request.non_authority_notice == NON_AUTHORITY_NOTICE
    assert request.human_review_required is True
    assert _prompt(backend)["request_id"] == request.request_id == result.run_record.runtime_request_id
    for text in (request.research_question, request.research_objective, request.public_market_context):
        assert len(text) <= HM._MAX_LONG_TEXT


def test_r018_prompt_binds_strategy_identity_and_semantics(tmp_path):
    world = make_world(tmp_path)
    backend = StrategyBackend()
    result = run(world, _manager_store(tmp_path), backend, trigger="PERFORMANCE_UPDATE", trigger_ref="perf:window-7")
    envelope = _prompt(backend)
    question = json.loads(envelope["research_question"])
    context = json.loads(envelope["public_market_context"])
    assert question["lifecycle_state"]["strategy_lifecycle_context_sha256"] == result.run_record.strategy_lifecycle_context_sha256
    assert question["assessment_trigger"] == {"trigger": "PERFORMANCE_UPDATE", "trigger_ref": "perf:window-7"}
    assert question["information_cutoff"] == CUTOFF
    assert question["strategy_identity"]["evidence_posture"] == "EVENT_INFORMATION"
    assert question["strategy_identity"]["adaptation_class"] == "ROOT"
    assert context["strategy_definition"]["thesis"] == STRATEGY_SPEC["thesis"]
    assert context["strategy_definition"]["parameters"] == STRATEGY_SPEC["parameters"]
    assert f"current only through the stated information cutoff {CUTOFF}" in envelope["research_objective"]
    assert envelope["draft_output_schema"]["schema_id"] == STRATEGY_DRAFT_OUTPUT_CONTRACT_ID
    assert "strategy_assessment" in envelope["draft_output_schema"]["required"]
    assert "information cutoff" in envelope["strategy_instruction"]


def test_r019_execution_rule_content_excluded_hash_bound(tmp_path):
    world = make_world(tmp_path)
    backend = StrategyBackend()
    run(world, _manager_store(tmp_path), backend)
    prompt = backend.prompts[-1]
    assert EXEC_MARKER not in prompt and "execution_rule\":{" not in prompt
    question = json.loads(_prompt(backend)["research_question"])
    expected = hashlib.sha256(canonical_json_bytes(STRATEGY_SPEC["execution_rule"])).hexdigest()
    assert question["strategy_identity"]["execution_rule_sha256"] == expected


def test_r020_account_scope_ref_excluded(tmp_path):
    world = make_world(tmp_path)
    allocated = world.append(_allocation(world.v1, world.pol))
    backend = StrategyBackend()
    result = run(world, _manager_store(tmp_path), backend, lifecycle_snapshot=allocated)
    assert result.status == sm.STATUS_ASSESSMENT_RECORDED
    prompt = backend.prompts[-1]
    assert "account:public-scope-1" not in prompt and "account_scope_ref" not in prompt
    assert str(tmp_path) not in prompt and str(tmp_path).replace("\\", "\\\\") not in prompt
    assert "human:karl-approval-1" not in prompt
    question = json.loads(_prompt(backend)["research_question"])
    assert question["lifecycle_state"]["current_active_budget_usd"] == "50"


def test_r021_over_bound_context_fails_before_backend(tmp_path):
    spec = json.loads(json.dumps(STRATEGY_SPEC))
    spec["thesis"] = {"claim": "x" * 5000}
    world = make_world(tmp_path, spec=spec)
    backend = StrategyBackend()
    result = run(world, _manager_store(tmp_path), backend)
    assert (result.status, result.error_code) == (sm.STATUS_REJECTED, "STRATEGY_CONTEXT_LIMIT_EXCEEDED")
    assert backend.call_count == backend.version_probe_count == backend.startup_probe_count == 0
    assert _rows(tmp_path / "hermes_strategy.sqlite3") == []


def test_r022_no_silent_truncation(tmp_path, monkeypatch):
    claim = "forecast skill " * 150
    spec = json.loads(json.dumps(STRATEGY_SPEC))
    spec["thesis"] = {"claim": claim}
    world = make_world(tmp_path, spec=spec)
    backend = StrategyBackend()
    assert run(world, _manager_store(tmp_path), backend).status == sm.STATUS_ASSESSMENT_RECORDED
    assert json.loads(_prompt(backend)["public_market_context"])["strategy_definition"]["thesis"]["claim"] == claim

    def too_large(*_args, **_kwargs):
        raise PolicyBroadeningError("POLICY_COMMAND_LINE_TOO_LARGE")

    monkeypatch.setattr(sm, "build_hermes_argv", too_large)
    blocked = StrategyBackend()
    result = run(world, _manager_store(tmp_path), blocked)
    assert result.error_code == "STRATEGY_CONTEXT_LIMIT_EXCEEDED"
    assert blocked.call_count == blocked.version_probe_count == 0


# ---------------------------------------------------------------------------
# Strategy output mode (R023-R032)
# ---------------------------------------------------------------------------


def _generic_request():
    return build_research_run_request({
        "schema_version": REQUEST_SCHEMA_VERSION, "research_question": "Will it resolve YES?",
        "research_objective": "Assess public evidence.", "research_category": "event_outcome",
        "public_market_context": "A public market.", "allowed_research_scope": ["public_web"],
        "required_source_types": ["news"], "max_sources": 8, "provider_label": "example-provider",
        "model_label": "example-model", "max_wall_seconds": 90, "max_output_bytes": 300_000,
        "max_accepted_estimated_cost_usd": "2", "human_review_required": True,
        "non_authority_notice": NON_AUTHORITY_NOTICE,
    })


def test_r023_generic_mode_unchanged():
    request = _generic_request()
    rid = request.request_id
    base = build_research_draft_output_schema(expected_request_id=rid, max_sources=8)
    assert base == build_research_draft_output_schema(expected_request_id=rid, max_sources=8, strategy_mode=False)
    assert "additionalProperties" not in base and "strategy_assessment" not in base["properties"]
    assert "strategy_consistency_rules" not in base
    plain = build_research_envelope(request)
    assert plain.envelope_digest == build_research_envelope(request, strategy_mode=False).envelope_digest
    assert "strategy_instruction" not in plain.as_mapping()
    generic = _draft(rid, drop=("strategy_assessment",))
    raw = json.dumps(generic)
    default = validate_research_draft(raw, expected_request_id=rid, max_sources=8)
    assert default == validate_research_draft(raw, expected_request_id=rid, max_sources=8, strategy_mode=False)
    assert default.strategy_assessment is None
    receipts = []
    for kwargs in ({}, {"strategy_mode": False}):
        backend = FakeHermesBackend.from_transcript(raw.encode("utf-8"), usage_file_bytes=_usage())
        result = run_controlled_hermes_research(request, backend, clock=lambda: FIXED, **kwargs)
        receipts.append(result.receipt)
        assert result.error_code is None
    assert receipts[0] == receipts[1]


def test_r024_context_mode_unchanged():
    rid = _generic_request().request_id
    subjects = (MARKET,)
    base = build_research_draft_output_schema(expected_request_id=rid, max_sources=8, context_mode=True, allowed_subject_refs=subjects)
    assert base == build_research_draft_output_schema(
        expected_request_id=rid, max_sources=8, context_mode=True, allowed_subject_refs=subjects, strategy_mode=False,
    )
    assert base["schema_id"] == HM.CONTEXT_DRAFT_OUTPUT_CONTRACT_ID and "strategy_assessment" not in base["properties"]
    request = _generic_request()
    assert build_research_envelope(request, context_mode=True, allowed_subject_refs=subjects).envelope_digest == (
        build_research_envelope(request, context_mode=True, allowed_subject_refs=subjects, strategy_mode=False).envelope_digest
    )


def test_r025_context_and_strategy_mode_together_reject():
    request = _generic_request()
    rid = request.request_id
    assert _code(build_research_draft_output_schema, expected_request_id=rid, max_sources=8, context_mode=True,
                 allowed_subject_refs=(MARKET,), strategy_mode=True, strategy_parameter_names=()) == "STRATEGY_MODE_INVALID"
    assert _code(build_research_envelope, request, context_mode=True, allowed_subject_refs=(MARKET,),
                 strategy_mode=True, strategy_parameter_names=()) == "STRATEGY_MODE_INVALID"
    assert _code(validate_research_draft, "{}", expected_request_id=rid, max_sources=8, context_mode=True,
                 allowed_subject_refs=(MARKET,), strategy_mode=True, strategy_parameter_names=()) == "STRATEGY_MODE_INVALID"
    backend = FakeHermesBackend.from_transcript(b"{}", usage_file_bytes=_usage())
    assert _code(run_controlled_hermes_research, request, backend, context_mode=True,
                 allowed_subject_refs=(MARKET,), strategy_mode=True, strategy_parameter_names=()) == "STRATEGY_MODE_INVALID"
    assert _code(run_controlled_hermes_research, request, backend, strategy_mode=True) == "STRATEGY_MODE_INVALID"
    assert backend.version_probe_count == backend.call_count == 0


def test_r026_strategy_schema_and_validator_share_required_fields():
    names = ("lookback", "edge", "mode")
    schema = build_research_draft_output_schema(expected_request_id="r", max_sources=8, strategy_mode=True, strategy_parameter_names=names)
    assert schema["schema_id"] == STRATEGY_DRAFT_OUTPUT_CONTRACT_ID
    assert schema["required"] == list(STRATEGY_REQUIRED_TOP_LEVEL_FIELDS)
    assert schema["additionalProperties"] is False
    sub = schema["properties"]["strategy_assessment"]
    assert sub["required"] == list(STRATEGY_ASSESSMENT_FIELDS) and sub["additionalProperties"] is False
    props = sub["properties"]
    assert props["lifecycle_action"]["enum"] == list(STRATEGY_LIFECYCLE_ACTIONS)
    assert props["recommended_health_state"]["enum"] == list(STRATEGY_RECOMMENDED_HEALTH_STATES)
    assert props["risk_direction"]["enum"] == list(STRATEGY_RISK_DIRECTIONS)
    assert props["target_risk_band"]["enum"] == [*STRATEGY_TARGET_RISK_BANDS, None]
    assert list(STRATEGY_TARGET_RISK_BANDS) == list(RISK_BANDS)
    assert list(STRATEGY_RECOMMENDED_HEALTH_STATES) == [s for s in HEALTH_STATES if s != "NEW"]
    adaptation = props["adaptation_recommendation"]
    assert adaptation["required"] == list(STRATEGY_ADAPTATION_FIELDS)
    assert adaptation["properties"]["kind"]["enum"] == list(STRATEGY_ADAPTATION_KINDS)
    assert adaptation["properties"]["parameter_updates"]["propertyNames"]["enum"] == sorted(names)
    rules = schema["strategy_consistency_rules"]["lifecycle_actions"]
    assert list(rules) == list(STRATEGY_LIFECYCLE_ACTIONS)
    assert rules["ADAPT"]["risk_directions"] == list(HM.STRATEGY_ACTION_CONSISTENCY_RULES["ADAPT"]["risk_directions"])
    accepted = _validate(_strategy_doc())
    assert accepted.strategy_assessment.lifecycle_action == "CONTINUE"
    assert set(json.loads(_strategy_doc())) == set(schema["required"])
    # The schema forbids additional properties; so does the validator.
    assert _code(_validate, json.dumps(dict(json.loads(_strategy_doc()), extra=1))) == "STRATEGY_ASSESSMENT_INVALID"


def test_r027_unknown_strategy_assessment_field_rejects():
    doc = json.loads(_strategy_doc())
    doc["strategy_assessment"]["confidence"] = "high"
    assert _code(_validate, json.dumps(doc)) == "STRATEGY_ASSESSMENT_INVALID"
    doc = json.loads(_strategy_doc(lifecycle_action="ADAPT", adaptation_recommendation={
        "kind": "PARAMETER_UPDATE", "summary": "shorter lookback", "parameter_updates": {"lookback": 4}, "class": "BOUNDED"}))
    assert _code(_validate, json.dumps(doc)) == "STRATEGY_ASSESSMENT_INVALID"
    doc = json.loads(_strategy_doc())
    doc["human_approval"] = True
    assert _code(_validate, json.dumps(doc)) == "STRATEGY_ASSESSMENT_INVALID"


def test_r028_missing_strategy_assessment_field_rejects():
    for field in STRATEGY_ASSESSMENT_FIELDS:
        doc = json.loads(_strategy_doc())
        del doc["strategy_assessment"][field]
        assert _code(_validate, json.dumps(doc)) == "STRATEGY_ASSESSMENT_INVALID", field
    assert _code(_validate, json.dumps(_draft("r", drop=("strategy_assessment",)))) == "STRATEGY_ASSESSMENT_INVALID"
    for value in (None, [], "CONTINUE"):
        assert _code(_validate, json.dumps(_draft("r", strategy_assessment=value))) == "STRATEGY_ASSESSMENT_INVALID"


def test_r029_invalid_lifecycle_action_rejects():
    for action in ("HOLD", "continue", "PROMOTE", "", None, 1):
        assert _code(_validate, _strategy_doc(lifecycle_action=action)) == "STRATEGY_ASSESSMENT_INVALID", action


def test_r030_invalid_health_band_direction_rejects():
    for field, value in (("recommended_health_state", "NEW"), ("recommended_health_state", "healthy"),
                         ("target_risk_band", "LIVE"), ("target_risk_band", ""),
                         ("risk_direction", "UP"), ("risk_direction", None)):
        assert _code(_validate, _strategy_doc(**{field: value})) == "STRATEGY_ASSESSMENT_INVALID", (field, value)
    assert _validate(_strategy_doc(target_risk_band="VALIDATED_LIVE")).strategy_assessment.target_risk_band == "VALIDATED_LIVE"


def test_r031_action_risk_consistency_enforced(tmp_path):
    good = (
        dict(lifecycle_action="CONTINUE", risk_direction="UNCHANGED"),
        dict(lifecycle_action="SCALE", risk_direction="INCREASE", target_risk_band="VALIDATED_LIVE"),
        dict(lifecycle_action="REDUCE", risk_direction="DECREASE", recommended_health_state="DEGRADED"),
        dict(lifecycle_action="PAPER", risk_direction="PAPER_ONLY", target_risk_band="PAPER"),
        dict(lifecycle_action="QUARANTINE", risk_direction="ZERO", recommended_health_state="QUARANTINED"),
        dict(lifecycle_action="RETIRE", risk_direction="ZERO", recommended_health_state="RETIRED"),
    )
    bad = (
        dict(lifecycle_action="CONTINUE", risk_direction="INCREASE"),
        dict(lifecycle_action="SCALE", risk_direction="DECREASE"),
        dict(lifecycle_action="SCALE", risk_direction="INCREASE", recommended_health_state="QUARANTINED"),
        dict(lifecycle_action="SCALE", risk_direction="INCREASE", recommended_health_state="RETIRED"),
        dict(lifecycle_action="REDUCE", risk_direction="ZERO"),
        dict(lifecycle_action="PAPER", risk_direction="PAPER_ONLY", target_risk_band=None),
        dict(lifecycle_action="PAPER", risk_direction="ZERO", target_risk_band="PAPER"),
        dict(lifecycle_action="QUARANTINE", risk_direction="ZERO", recommended_health_state="WATCH"),
        dict(lifecycle_action="QUARANTINE", risk_direction="ZERO", recommended_health_state="QUARANTINED", target_risk_band="PAPER"),
        dict(lifecycle_action="RETIRE", risk_direction="DECREASE", recommended_health_state="RETIRED"),
        dict(lifecycle_action="RETIRE", risk_direction="ZERO", recommended_health_state="RETIRED", target_risk_band="PAPER"),
        dict(lifecycle_action="ADAPT", risk_direction="INCREASE", adaptation_kind="MATERIAL_REDESIGN",
             adaptation_summary="redesign", adaptation_parameter_updates_json="{}"),
    )
    for fields in good:
        assert check_strategy_assessment_consistency(_sd(**fields)), fields
    for fields in bad:
        assert not check_strategy_assessment_consistency(_sd(**fields)), fields
    world = make_world(tmp_path)
    store = _manager_store(tmp_path)
    backend = StrategyBackend(lambda rid, _e: _draft(rid, strategy=_assessment(lifecycle_action="SCALE", risk_direction="DECREASE")))
    result = run(world, store, backend)
    assert (result.status, result.error_code) == (sm.STATUS_RUN_RECORDED_NO_ASSESSMENT, "STRATEGY_OUTPUT_INCONSISTENT")
    assert [row[1] for row in _rows(store)] == [sm.RECORD_KIND_RUN]


def test_r032_raw_hermes_authority_flags_unchanged():
    assert DRAFT_AUTHORITY_FLAGS == (
        "advisory_only", "human_review_required", "no_execution_authority", "no_risk_override",
        "no_credential_request", "no_order_or_cancel_or_sign_or_submit", "no_paper_live_decision",
        "no_strategy_promotion_approval", "no_pr_approval_or_merge_readiness_claim",
    )
    for flag in DRAFT_AUTHORITY_FLAGS:
        doc = json.loads(_strategy_doc())
        doc[flag] = False
        assert _code(_validate, json.dumps(doc)) == "DRAFT_AUTHORITY_FLAG_INVALID", flag
        del doc[flag]
        assert _code(_validate, json.dumps(doc)) == "DRAFT_FIELD_MISSING", flag
    schema = build_research_draft_output_schema(expected_request_id="r", max_sources=8, strategy_mode=True, strategy_parameter_names=())
    for flag in DRAFT_AUTHORITY_FLAGS:
        assert schema["properties"][flag] == {"type": "boolean", "const": True}


# ---------------------------------------------------------------------------
# Adaptation (R033-R038)
# ---------------------------------------------------------------------------


def _adapt(kind="PARAMETER_UPDATE", updates=None, summary="Shorten the lookback window."):
    return {"kind": kind, "summary": summary, "parameter_updates": {"lookback": 4} if updates is None else updates}


def test_r033_non_adapt_requires_null_adaptation(tmp_path):
    for action, direction in (("CONTINUE", "UNCHANGED"), ("REDUCE", "DECREASE")):
        draft = _validate(_strategy_doc(lifecycle_action=action, risk_direction=direction, adaptation_recommendation=_adapt())).strategy_assessment
        assert not check_strategy_assessment_consistency(draft)
    world = make_world(tmp_path)
    backend = StrategyBackend(lambda rid, _e: _draft(rid, strategy=_assessment(adaptation_recommendation=_adapt())))
    assert run(world, _manager_store(tmp_path), backend).error_code == "STRATEGY_OUTPUT_INCONSISTENT"


def test_r034_adapt_requires_recommendation():
    draft = _validate(_strategy_doc(lifecycle_action="ADAPT", risk_direction="DECREASE")).strategy_assessment
    assert draft.adaptation_kind is None and not check_strategy_assessment_consistency(draft)
    ok = _validate(_strategy_doc(lifecycle_action="ADAPT", risk_direction="DECREASE", adaptation_recommendation=_adapt())).strategy_assessment
    assert check_strategy_assessment_consistency(ok)


def test_r035_parameter_update_keys_must_exist(tmp_path):
    doc = _strategy_doc(lifecycle_action="ADAPT", risk_direction="UNCHANGED", adaptation_recommendation=_adapt(updates={"new_param": 1}))
    assert _code(_validate, doc) == "STRATEGY_ASSESSMENT_INVALID"
    world = make_world(tmp_path)
    store = _manager_store(tmp_path)
    backend = StrategyBackend(lambda rid, _e: _draft(rid, strategy=_assessment(
        lifecycle_action="ADAPT", adaptation_recommendation=_adapt(updates={"new_param": 1}))))
    result = run(world, store, backend)
    assert (result.status, result.error_code) == (sm.STATUS_RUN_RECORDED_NO_ASSESSMENT, "STRATEGY_OUTPUT_INVALID")
    assert result.run_record.terminal_status == "OUTPUT_SCHEMA_INVALID"
    assert len(_rows(store)) == 1


def test_r036_binary_float_nan_infinity_proposal_rejects():
    for literal in ("0.5", "NaN", "Infinity", "-Infinity", "1e3", "[1.5]", "{\"x\": 2.0}"):
        raw = _strategy_doc(lifecycle_action="ADAPT", adaptation_recommendation=_adapt(updates={"lookback": "__V__"}))
        raw = raw.replace('"__V__"', literal)
        assert _code(_validate, raw) == "STRATEGY_ASSESSMENT_INVALID", literal
    ok = _validate(_strategy_doc(lifecycle_action="ADAPT", adaptation_recommendation=_adapt(updates={"edge": "0.4", "lookback": 6})))
    assert ok.strategy_assessment.adaptation_parameter_updates_json == '{"edge":"0.4","lookback":6}'


def test_r037_material_redesign_requires_empty_updates():
    redesign = _validate(_strategy_doc(lifecycle_action="ADAPT", risk_direction="PAPER_ONLY", adaptation_recommendation=_adapt("MATERIAL_REDESIGN", {}))).strategy_assessment
    assert check_strategy_assessment_consistency(redesign)
    bad_redesign = _validate(_strategy_doc(lifecycle_action="ADAPT", adaptation_recommendation=_adapt("MATERIAL_REDESIGN"))).strategy_assessment
    empty_update = _validate(_strategy_doc(lifecycle_action="ADAPT", adaptation_recommendation=_adapt("PARAMETER_UPDATE", {}))).strategy_assessment
    assert not check_strategy_assessment_consistency(bad_redesign)
    assert not check_strategy_assessment_consistency(empty_update)
    for summary in ("", "   ", "y" * 1025, "go live immediately"):
        assert _code(_validate, _strategy_doc(lifecycle_action="ADAPT", adaptation_recommendation=_adapt("MATERIAL_REDESIGN", {}, summary))) == "STRATEGY_ASSESSMENT_INVALID"


def test_r038_no_child_strategy_version_constructed(tmp_path):
    world = make_world(tmp_path)
    before_hash = _file_hash(world.path)
    before = world.snapshot()
    backend = StrategyBackend(lambda rid, _e: _draft(rid, strategy=_assessment(
        lifecycle_action="ADAPT", risk_direction="DECREASE", adaptation_recommendation=_adapt(updates={"lookback": 6}))))
    result = run(world, _manager_store(tmp_path), backend, lifecycle_snapshot=before)
    assert result.status == sm.STATUS_ASSESSMENT_RECORDED, result.error_code
    assert result.assessment.adaptation_recommendation() == {
        "kind": "PARAMETER_UPDATE", "summary": "Shorten the lookback window.", "parameter_updates": {"lookback": 6},
    }
    assert _file_hash(world.path) == before_hash
    assert world.snapshot().strategy_versions == before.strategy_versions
    assert not hasattr(sm, "build_strategy_version")


# ---------------------------------------------------------------------------
# Runtime binding (R039-R044)
# ---------------------------------------------------------------------------


def test_r039_manager_calls_controlled_runtime_once(tmp_path, monkeypatch):
    world = make_world(tmp_path)
    calls = []

    def counting(*args, **kwargs):
        calls.append(kwargs)
        return run_controlled_hermes_research(*args, **kwargs)

    monkeypatch.setattr(sm, "run_controlled_hermes_research", counting)
    backend = StrategyBackend()
    assert run(world, _manager_store(tmp_path), backend).status == sm.STATUS_ASSESSMENT_RECORDED
    assert len(calls) == 1 and calls[0]["strategy_mode"] is True
    assert calls[0]["strategy_parameter_names"] == ("edge", "lookback", "mode")
    assert (backend.version_probe_count, backend.startup_probe_count, backend.call_count) == (1, 1, 1)


def test_r040_fake_backend_only_zero_network():
    assert issubclass(StrategyBackend, FakeHermesBackend)
    tree = ast.parse(MODULE.read_text(encoding="utf-8"))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.add(node.module or "")
    for bad in ("socket", "http", "urllib", "requests", "httpx", "websockets", "subprocess", "ssl", "aiohttp"):
        assert not any(name == bad or name.startswith(bad + ".") for name in imported), bad
    assert ".runner" not in imported


def test_r041_runtime_failure_records_run_only(tmp_path):
    world = make_world(tmp_path)
    store = _manager_store(tmp_path)
    backend = StrategyBackend(outcome=_outcome(b"", None, launch_failed=True, exit_code=None))
    result = run(world, store, backend)
    assert (result.status, result.error_code) == (sm.STATUS_RUN_RECORDED_NO_ASSESSMENT, "RUNTIME_FAILURE")
    assert result.assessment is None and result.run_record.terminal_status == "TRANSPORT_FAILURE"
    assert backend.call_count == 1
    snap = sm.load_hermes_strategy_manager_store(store)
    assert len(snap.run_records) == 1 and snap.assessments == ()
    timeout = StrategyBackend(outcome=_outcome(b"", None, timed_out=True, exit_code=None))
    assert run(world, store, timeout, decision_time_ns=2_000).error_code == "RUNTIME_FAILURE"
    assert timeout.call_count == 1


def test_r042_invalid_strategy_output_records_run_only(tmp_path):
    world = make_world(tmp_path)
    store = _manager_store(tmp_path)
    backend = StrategyBackend(lambda rid, _e: _draft(rid, drop=("strategy_assessment",)))
    result = run(world, store, backend)
    assert (result.status, result.error_code) == (sm.STATUS_RUN_RECORDED_NO_ASSESSMENT, "STRATEGY_OUTPUT_INVALID")
    assert result.run_record.terminal_status == "OUTPUT_SCHEMA_INVALID"
    not_json = StrategyBackend(lambda rid, _e: b"model prose, not JSON")
    assert run(world, store, not_json, decision_time_ns=2_000).error_code == "RUNTIME_FAILURE"
    assert [row[1] for row in _rows(store)] == [sm.RECORD_KIND_RUN, sm.RECORD_KIND_RUN]


def test_r043_success_binds_runtime_request_receipt_policy(tmp_path):
    world = make_world(tmp_path)
    backend = StrategyBackend()
    result = run(world, _manager_store(tmp_path), backend)
    runrec, assessment = result.run_record, result.assessment
    assert runrec.runtime_request_id == assessment.runtime_request_id == _prompt(backend)["request_id"]
    assert runrec.runtime_receipt_id == assessment.runtime_receipt_id
    assert runrec.runtime_receipt_id.startswith("hermesresearchreceipt:sha256:")
    assert runrec.runtime_policy_id == DEFAULT_HERMES_INVOCATION_POLICY.policy_id
    assert assessment.run_record_id == runrec.run_record_id
    assert (runrec.terminal_status, runrec.provider_label, runrec.model_label) == ("RESEARCH_DRAFT_VALIDATED", "example-provider", "example-model")
    assert (runrec.estimated_cost_usd, runrec.cost_status) == ("0.04", "estimated")


def test_r044_receipt_identity_revalidated_before_run_record(tmp_path, monkeypatch):
    world = make_world(tmp_path)
    store = _manager_store(tmp_path)

    def forged(*args, **kwargs):
        result = run_controlled_hermes_research(*args, **kwargs)
        return dataclasses.replace(result, receipt=dataclasses.replace(result.receipt, terminal_status="RESEARCH_DRAFT_FORGED"))

    monkeypatch.setattr(sm, "run_controlled_hermes_research", forged)
    result = run(world, store)
    assert (result.status, result.error_code) == (sm.STATUS_REJECTED, "INTERNAL_VALIDATION_FAILED")
    assert result.run_record is None and _rows(store) == []


# ---------------------------------------------------------------------------
# Identity / history (R045-R050)
# ---------------------------------------------------------------------------


def _id_of(prefix, mapping, field):
    projected = {k: v for k, v in mapping.items() if k != field}
    return prefix + hashlib.sha256(canonical_json_bytes(projected)).hexdigest()


def test_r045_run_record_id_deterministic_and_tamper_evident(tmp_path):
    world = make_world(tmp_path)
    runrec = run(world, _manager_store(tmp_path)).run_record
    mapping = runrec.to_mapping()
    assert runrec.run_record_id == _id_of(sm.RUN_RECORD_ID_PREFIX, mapping, "run_record_id")
    assert sm.HermesStrategyRunRecord.from_mapping(mapping) == runrec
    for field, value in (("decision_time_ns", 7), ("terminal_status", "TIMEOUT"), ("trigger", "REGIME_CHANGE"),
                         ("run_record_id", sm.RUN_RECORD_ID_PREFIX + "0" * 64)):
        assert _code(sm.HermesStrategyRunRecord.from_mapping, dict(mapping, **{field: value})) == "STORE_TAMPERED", field
    for field, value in (("no_live_authority", False), ("estimated_cost_usd", 0.04), ("decision_time_ns", True)):
        changed = dict(mapping, **{field: value})
        changed["run_record_id"] = _id_of(sm.RUN_RECORD_ID_PREFIX, changed, "run_record_id") if field != "estimated_cost_usd" else mapping["run_record_id"]
        assert _code(sm.HermesStrategyRunRecord.from_mapping, changed) == "STORE_TAMPERED", field
    assert _code(sm.HermesStrategyRunRecord.from_mapping, dict(mapping, extra=1)) == "STORE_TAMPERED"


def test_r046_assessment_id_deterministic_and_tamper_evident(tmp_path):
    world = make_world(tmp_path)
    assessment = run(world, _manager_store(tmp_path)).assessment
    mapping = assessment.to_mapping()
    assert assessment.assessment_id == _id_of(sm.ASSESSMENT_ID_PREFIX, mapping, "assessment_id")
    assert sm.HermesStrategyAssessment.from_mapping(mapping) == assessment
    for field, value in (("lifecycle_action", "SCALE"), ("assessment_summary", "edited"), ("evidence_for", ["forged"])):
        assert _code(sm.HermesStrategyAssessment.from_mapping, dict(mapping, **{field: value})) == "STORE_TAMPERED", field
    assert not any("approv" in name or "reasoning" in name or "thought" in name for name in mapping)
    assert _code(sm.HermesStrategyAssessment.from_mapping, dict(mapping, human_approval_ref="human:x")) == "STORE_TAMPERED"


def test_r047_first_assessment_predecessor_null(tmp_path):
    world = make_world(tmp_path)
    store = _manager_store(tmp_path)
    result = run(world, store)
    assert result.assessment.predecessor_assessment_id is None
    assert sm.load_hermes_strategy_manager_store(store).latest_assessment_id(world.v1.strategy_version_id) == result.assessment.assessment_id


def test_r048_next_assessment_predecessor_is_prior(tmp_path):
    world = make_world(tmp_path)
    store = _manager_store(tmp_path)
    first = run(world, store).assessment
    second = run(world, store, trigger="EVIDENCE_UPDATE", decision_time_ns=2_000).assessment
    assert second.predecessor_assessment_id == first.assessment_id
    assert sm.load_hermes_strategy_manager_store(store).latest_assessment_id(world.v1.strategy_version_id) == second.assessment_id


def test_r049_stale_same_strategy_predecessor_rejects(tmp_path):
    world = make_world(tmp_path)
    store = _manager_store(tmp_path)
    nested = []
    backend = StrategyBackend(on_invoke=lambda: nested.append(run(world, store, decision_time_ns=5_000)))
    result = run(world, store, backend)
    assert nested[0].status == sm.STATUS_ASSESSMENT_RECORDED
    assert (result.status, result.error_code) == (sm.STATUS_RUN_RECORDED_NO_ASSESSMENT, "ASSESSMENT_PREDECESSOR_STALE")
    snap = sm.load_hermes_strategy_manager_store(store)
    assert len(snap.run_records) == 2 and len(snap.assessments) == 1
    assert snap.latest_assessment_id(world.v1.strategy_version_id) == nested[0].assessment.assessment_id


def test_r050_unrelated_strategy_does_not_block_chain(tmp_path):
    world = make_world(tmp_path)
    store = _manager_store(tmp_path)
    nested = []
    backend = StrategyBackend(on_invoke=lambda: nested.append(run(world, store, version=world.v2)))
    result = run(world, store, backend)
    assert nested[0].status == result.status == sm.STATUS_ASSESSMENT_RECORDED
    snap = sm.load_hermes_strategy_manager_store(store)
    assert snap.latest_assessment_id(world.v1.strategy_version_id) == result.assessment.assessment_id
    assert snap.latest_assessment_id(world.v2.strategy_version_id) == nested[0].assessment.assessment_id


# ---------------------------------------------------------------------------
# Store (R051-R059)
# ---------------------------------------------------------------------------


def test_r051_store_initialize_and_verified_load_identity(tmp_path):
    path = tmp_path / "hsm.sqlite3"
    snap = sm.initialize_hermes_strategy_manager_store(path)
    assert (snap.total_rows, snap.store_head_entry_hash, snap.run_records, snap.assessments) == (0, None, (), ())
    connection = sqlite3.connect(path)
    try:
        assert connection.execute("PRAGMA application_id").fetchone() == (1213418801,) == (sm.STORE_APPLICATION_ID,)
        assert connection.execute("PRAGMA user_version").fetchone() == (1,)
        assert connection.execute("SELECT * FROM strategy_manager_meta").fetchall() == [(1, "s10-hermes-strategy-manager-store", 1)]
    finally:
        connection.close()
    assert sm.initialize_hermes_strategy_manager_store(path) == snap == sm.load_hermes_strategy_manager_store(path)
    assert _code(sm.load_hermes_strategy_manager_store, tmp_path / "absent.sqlite3") == "STORE_PATH_INVALID"


def test_r052_connection_pragma_contract(tmp_path):
    path = _manager_store(tmp_path)
    connection = sm._connect(path, "ro")
    try:
        assert str(connection.execute("PRAGMA journal_mode").fetchone()[0]).lower() == "delete"
        assert connection.execute("PRAGMA synchronous").fetchone() == (2,)
        assert connection.execute("PRAGMA foreign_keys").fetchone() == (1,)
    finally:
        connection.close()
    raw = sqlite3.connect(path)
    raw.execute("PRAGMA journal_mode=WAL")
    raw.close()
    assert _code(sm.load_hermes_strategy_manager_store, path) == "STORE_SCHEMA_CONFLICT"


def test_r053_update_delete_blocked(tmp_path):
    world = make_world(tmp_path)
    store = _manager_store(tmp_path)
    run(world, store)
    connection = sqlite3.connect(store)
    try:
        for sql in ("UPDATE strategy_manager_records SET payload_json = 'x'", "DELETE FROM strategy_manager_records",
                    "UPDATE strategy_manager_meta SET schema_version = 1", "DELETE FROM strategy_manager_meta"):
            with pytest.raises(sqlite3.DatabaseError):
                connection.execute(sql)
    finally:
        connection.close()
    assert len(sm.load_hermes_strategy_manager_store(store).assessments) == 1


def test_r054_append_chain_verified(tmp_path):
    world = make_world(tmp_path)
    store = _manager_store(tmp_path)
    run(world, store)
    run(world, store, decision_time_ns=2_000)
    rows = _rows(store)
    assert [row[0] for row in rows] == [0, 1, 2, 3]
    previous = None
    for sequence, kind, record_id, strategy_id, payload, payload_sha, prev, current in rows:
        assert prev == previous and payload_sha == hashlib.sha256(payload.encode("utf-8")).hexdigest()
        assert current == sm.entry_hash(sequence, kind, record_id, strategy_id, payload_sha, prev)
        previous = current
    assert sm.load_hermes_strategy_manager_store(store).store_head_entry_hash == previous


def _rebuild(tmp_path: Path, rows: list[tuple], name: str) -> Path:
    path = tmp_path / f"{name}.sqlite3"
    sm.initialize_hermes_strategy_manager_store(path)
    connection = sqlite3.connect(path)
    try:
        connection.executemany("INSERT INTO strategy_manager_records VALUES (?, ?, ?, ?, ?, ?, ?, ?)", rows)
        connection.commit()
    finally:
        connection.close()
    return path


def test_r055_payload_record_id_entry_chain_tamper_rejects(tmp_path):
    world = make_world(tmp_path)
    store = _manager_store(tmp_path)
    run(world, store)
    rows = _rows(store)
    assert sm.load_hermes_strategy_manager_store(_rebuild(tmp_path, rows, "copy")).total_rows == 2
    seq, kind, rid, sid, payload, psha, prev, cur = rows[1]
    edited = payload.replace("CONTINUE", "SCALE")
    edited_sha = hashlib.sha256(edited.encode("utf-8")).hexdigest()
    cases = {
        "payload": (seq, kind, rid, sid, edited, psha, prev, cur),
        "payload_rehashed": (seq, kind, rid, sid, edited, edited_sha, prev, sm.entry_hash(seq, kind, rid, sid, edited_sha, prev)),
        "record_id": (seq, kind, sm.ASSESSMENT_ID_PREFIX + "0" * 64, sid, payload, psha, prev, cur),
        "strategy_column": (seq, kind, rid, world.v2.strategy_version_id, payload, psha, prev, cur),
        "entry_hash": (seq, kind, rid, sid, payload, psha, prev, "0" * 64),
        "previous_hash": (seq, kind, rid, sid, payload, psha, "1" * 64, cur),
    }
    for name, row in cases.items():
        path = _rebuild(tmp_path, [rows[0], row], name)
        assert _code(sm.load_hermes_strategy_manager_store, path) == "STORE_TAMPERED", name
    orphan = _rebuild(tmp_path, [(0,) + rows[1][1:6] + (None, sm.entry_hash(0, kind, rid, sid, psha, None))], "orphan")
    assert _code(sm.load_hermes_strategy_manager_store, orphan) == "STORE_TAMPERED"


def test_r056_unsafe_path_symlink_hardlink_schema_drift_rejects(tmp_path):
    for bad in (tmp_path / "store.db", tmp_path / "missing" / "s.sqlite3", "", 7, b"x.sqlite3"):
        assert _code(sm.initialize_hermes_strategy_manager_store, bad) == "STORE_PATH_INVALID", bad
    store = _manager_store(tmp_path)
    linked = tmp_path / "linked.sqlite3"
    os.link(store, linked)
    assert _code(sm.load_hermes_strategy_manager_store, linked) == "STORE_PATH_INVALID"
    os.unlink(linked)
    try:
        (tmp_path / "sym.sqlite3").symlink_to(store)
    except (OSError, NotImplementedError):
        symlink_supported = False
    else:
        symlink_supported = True
    if symlink_supported:
        assert _code(sm.load_hermes_strategy_manager_store, tmp_path / "sym.sqlite3") == "STORE_PATH_INVALID"
    raw = sqlite3.connect(store)
    raw.execute("PRAGMA application_id=1398033457")
    raw.close()
    assert _code(sm.load_hermes_strategy_manager_store, store) == "STORE_SCHEMA_CONFLICT"
    drift = _manager_store(tmp_path / "d" if (tmp_path / "d").mkdir() is None else tmp_path)
    raw = sqlite3.connect(drift)
    raw.execute("CREATE TABLE extra (x INTEGER)")
    raw.close()
    assert _code(sm.load_hermes_strategy_manager_store, drift) == "STORE_SCHEMA_CONFLICT"


def test_r057_success_persists_run_and_assessment_atomically(tmp_path):
    world = make_world(tmp_path)
    store = _manager_store(tmp_path)
    result = run(world, store)
    rows = _rows(store)
    assert [(row[1], row[2]) for row in rows] == [
        (sm.RECORD_KIND_RUN, result.run_record.run_record_id),
        (sm.RECORD_KIND_ASSESSMENT, result.assessment.assessment_id),
    ]
    assert result.store_head_entry_hash == rows[-1][7]


def test_r058_failed_transaction_leaves_no_partial_pair(tmp_path, monkeypatch):
    world = make_world(tmp_path)
    store = _manager_store(tmp_path)
    before = _file_hash(store)
    real_load = sm._load
    calls = []

    def failing_after_insert(connection):
        calls.append(1)
        if len(calls) == 2:
            raise sm.StrategyManagerError("INTERNAL_VALIDATION_FAILED")
        return real_load(connection)

    def arm():
        monkeypatch.setattr(sm, "_load", failing_after_insert)

    result = run(world, store, StrategyBackend(on_invoke=arm))
    assert (result.status, result.error_code) == (sm.STATUS_REJECTED, "INTERNAL_VALIDATION_FAILED")
    assert _file_hash(store) == before and _rows(store) == []


def test_r059_store_bounds_enforced(tmp_path, monkeypatch):
    world = make_world(tmp_path)
    store = _manager_store(tmp_path)
    monkeypatch.setattr(sm, "MAX_RECORD_PAYLOAD_BYTES", 200)
    result = run(world, store)
    assert (result.status, result.error_code) == (sm.STATUS_REJECTED, "STORE_LIMIT_EXCEEDED")
    assert _rows(store) == []
    monkeypatch.setattr(sm, "MAX_RECORD_PAYLOAD_BYTES", 262_144)
    monkeypatch.setattr(sm, "MAX_STORE_RECORDS", 1)
    capped = run(world, store)
    assert (capped.status, capped.error_code) == (sm.STATUS_RUN_RECORDED_NO_ASSESSMENT, "STORE_LIMIT_EXCEEDED")
    assert len(_rows(store)) == 1
    assert run(world, store, decision_time_ns=2_000).error_code == "STORE_LIMIT_EXCEEDED"
    assert len(_rows(store)) == 1


# ---------------------------------------------------------------------------
# Authority / non-integration (R060-R069)
# ---------------------------------------------------------------------------


def _source_tree():
    return ast.parse(MODULE.read_text(encoding="utf-8"))


def _imports() -> set[str]:
    out = set()
    for node in ast.walk(_source_tree()):
        if isinstance(node, ast.Import):
            out.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            out.add(node.module or "")
            out.update(f"{node.module}.{alias.name}" for alias in node.names)
    return out


def test_r060_no_direct_strat_life_store_append_or_open():
    names = {node.id for node in ast.walk(_source_tree()) if isinstance(node, ast.Name)}
    names |= {node.attr for node in ast.walk(_source_tree()) if isinstance(node, ast.Attribute)}
    names |= _imports()
    for forbidden in ("append_strategy_lifecycle_record", "initialize_strategy_lifecycle_store",
                      "load_strategy_lifecycle_store", "src.strategy_lifecycle.store"):
        assert not any(forbidden in name for name in names), forbidden


def test_r061_no_execution_paper_cockpit_imports():
    for name in _imports():
        for bad in ("execution_gateway", "paper_trading", "risk_engine", "operator_cockpit",
                    "strategy_modules", "polymarket", "qualification", "alpha_factory"):
            assert bad not in name, (name, bad)


def test_r062_no_credential_sign_order_live_api():
    public = [name for name in dir(sm) if not name.startswith("_") and callable(getattr(sm, name))]
    for name in public:
        lowered = name.lower()
        for bad in ("sign", "order", "credential", "live", "submit", "cancel", "wallet", "allocate", "activate"):
            assert bad not in lowered, (name, bad)
    assert "run_hermes_strategy_assessment" in public


def test_r063_no_scheduler_or_background_loop():
    for name in _imports():
        for bad in ("threading", "sched", "asyncio", "concurrent", "multiprocessing", "time"):
            assert name != bad and not name.startswith(bad + "."), name
    for node in ast.walk(_source_tree()):
        if isinstance(node, ast.While):
            assert not (isinstance(node.test, ast.Constant) and node.test.value is True)
    assert "sleep(" not in MODULE.read_text(encoding="utf-8")


def test_r064_assessment_soft_decision_and_no_authority_flags(tmp_path):
    world = make_world(tmp_path)
    assessment = run(world, _manager_store(tmp_path)).assessment
    flags = ("no_credential_authority", "no_portfolio_policy_authority", "no_hard_risk_override",
             "no_paper_execution_authority", "no_order_authority", "no_execution_authority", "no_live_authority")
    assert assessment.canonical_soft_strategy_decision is True
    assert all(getattr(assessment, flag) is True for flag in flags)
    mapping = assessment.to_mapping()
    for flag in ("canonical_soft_strategy_decision",) + flags:
        changed = dict(mapping, **{flag: False})
        changed["assessment_id"] = _id_of(sm.ASSESSMENT_ID_PREFIX, changed, "assessment_id")
        assert _code(sm.HermesStrategyAssessment.from_mapping, changed) == "STORE_TAMPERED", flag


def test_r065_scale_does_not_mutate_allocation_or_policy(tmp_path):
    world = make_world(tmp_path)
    world.append(_health(world.v1, "NEW", "HEALTHY"))
    snap = world.append(_allocation(world.v1, world.pol))
    lc_hash = _file_hash(world.path)
    backend = StrategyBackend(lambda rid, _e: _draft(rid, strategy=_assessment(
        lifecycle_action="SCALE", risk_direction="INCREASE", target_risk_band="VALIDATED_LIVE")))
    result = run(world, _manager_store(tmp_path), backend, lifecycle_snapshot=snap)
    assert result.status == sm.STATUS_ASSESSMENT_RECORDED and result.assessment.lifecycle_action == "SCALE"
    after = world.snapshot()
    assert _file_hash(world.path) == lc_hash
    assert after.allocation_of(world.v1.strategy_version_id) == snap.allocation_of(world.v1.strategy_version_id)
    assert after.allocation_of(world.v1.strategy_version_id).risk_band == "EXPLORATORY_LIVE"
    assert after.active_policy_id == snap.active_policy_id == world.pol.policy_id


def test_r066_quarantine_retire_are_strategy_local(tmp_path):
    world = make_world(tmp_path)
    store = _manager_store(tmp_path)
    quarantine = StrategyBackend(lambda rid, _e: _draft(rid, strategy=_assessment(
        lifecycle_action="QUARANTINE", recommended_health_state="QUARANTINED", risk_direction="ZERO")))
    first = run(world, store, quarantine)
    assert first.status == sm.STATUS_ASSESSMENT_RECORDED
    other = run(world, store, version=world.v2)
    assert other.status == sm.STATUS_ASSESSMENT_RECORDED and other.assessment.predecessor_assessment_id is None
    retire = StrategyBackend(lambda rid, _e: _draft(rid, strategy=_assessment(
        lifecycle_action="RETIRE", recommended_health_state="RETIRED", risk_direction="ZERO")))
    second = run(world, store, retire, decision_time_ns=2_000)
    assert second.assessment.predecessor_assessment_id == first.assessment.assessment_id
    after_v2 = run(world, store, version=world.v2, decision_time_ns=3_000)
    assert after_v2.status == sm.STATUS_ASSESSMENT_RECORDED
    assert after_v2.assessment.predecessor_assessment_id == other.assessment.assessment_id
    assert world.snapshot().health_of(world.v2.strategy_version_id) == "NEW"


def _spec() -> dict:
    return json.loads(SPEC.read_text(encoding="utf-8"))


def test_r067_strat_life_source_and_tests_outside_scope():
    spec = _spec()
    scope = spec["scope"]["required_changed_files"]
    assert not any(path.startswith(("src/strategy_lifecycle/", "tests/strategy_lifecycle/")) for path in scope)
    assert {"src/strategy_lifecycle/", "tests/strategy_lifecycle/"} <= set(spec["scope"]["forbidden_prefixes"])
    assert spec["authority"]["strategy"] is True and spec["authority"]["live"] is False


def test_r068_data03_untouched():
    data03 = json.loads((ROOT / "docs" / "wp_specs" / "S10-QUAL-DATA-03" / "wp_spec.json").read_text(encoding="utf-8"))
    code_paths = {p for p in data03["scope"]["required_changed_files"] if p.endswith(".py") and "docs" not in p}
    code_paths |= {"docs/qualification_weather_oos_accrual_contract.md"}
    assert not code_paths & set(_spec()["scope"]["required_changed_files"])
    assert "qualification_oos_accrual" not in MODULE.read_text(encoding="utf-8")


def test_r069_control_center_untouched():
    scope = _spec()["scope"]["required_changed_files"]
    for path in scope:
        assert not path.startswith(("src/operator_cockpit", ".github/", "tools/"))
        assert Path(path).name not in {"package.json", "package-lock.json", "pyproject.toml", "requirements.txt"}
    assert len(scope) == 22 and _spec()["identity"]["package_size_class"] == "XL"
