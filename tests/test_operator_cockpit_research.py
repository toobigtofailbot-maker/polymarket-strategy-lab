"""S10-CC-RESEARCH-01/02 focused tests: read-only Control Center research projections.

Every fixture is a real verified canonical store built through the public lifecycle,
Hermes strategy-manager, Alpha Factory and Alpha Discovery APIs (deterministic fake Hermes
backend; no provider, model or network). Stale context is produced only by valid canonical
lifecycle transitions; Alpha lineage and head mismatches only by valid canonical appends.
"""

from __future__ import annotations

import ast
import asyncio
import dataclasses
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re

import pytest

import src.operator_cockpit as cockpit
import src.operator_cockpit_research as research
from src.research_runtime.hermes_controlled_runtime import strategy_manager as sm
from src.research_runtime.hermes_controlled_runtime.models import (
    DRAFT_AUTHORITY_FLAGS,
    DRAFT_SCHEMA_VERSION,
)
from src.research_runtime.hermes_controlled_runtime.runner import (
    FakeHermesBackend,
    HermesInvocationOutcome,
)
from src.strategy_lifecycle import (
    append_strategy_lifecycle_record,
    build_portfolio_authority_policy,
    build_portfolio_policy_receipt,
    build_strategy_family,
    build_strategy_health_receipt,
    build_strategy_restriction_receipt,
    build_strategy_risk_allocation,
    build_strategy_version,
    initialize_strategy_lifecycle_store,
    load_strategy_lifecycle_store,
)
from src.data_layer.analytical_research import alpha_discovery as AD
from src.data_layer.analytical_research import alpha_discovery_registry as ADR
from src.data_layer.analytical_research import alpha_factory as AF
from src.data_layer.analytical_research import alpha_factory_registry as AFR
from tests.data_layer.analytical_research.test_alpha_discovery import (
    _change, _market, _policy, _universe,
)
from tests.data_layer.analytical_research.test_alpha_factory_records import (
    candidate_input, episode_input, family_input, source_input,
)
from tests.test_operator_cockpit import _asgi_call, _get


ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "src" / "operator_cockpit_research.py"
FRONTEND = ROOT / "src" / "operator_cockpit_frontend" / "src"
HERMES_CUTOFF = "2026-10-01T00:00:00Z"
FIXED_CLOCK = datetime(2026, 10, 1, 12, 0, 0, tzinfo=timezone.utc)
UNAVAILABLE = (503, {"error": {"code": "SOURCE_UNAVAILABLE"}})
INVALID = (400, {"error": {"code": "INVALID_INPUT"}})
NOT_FOUND = (404, {"error": {"code": "NOT_FOUND"}})
RESEARCH_ROUTES = (
    "/api/strategies",
    "/api/strategies/{strategy_version_id}",
    "/api/hermes/assessments",
    "/api/hermes/assessments/{assessment_id}",
)
ALPHA_ROUTES = (
    "/api/alpha/memory",
    "/api/alpha/candidates",
    "/api/alpha/candidates/{candidate_id}",
    "/api/alpha/episodes/{research_episode_id}",
    "/api/alpha/discovery/queue",
    "/api/alpha/discovery/triage/{market_triage_decision_id}",
)
STRATEGY_SPEC = {
    "thesis": {"claim": "fixture thesis"},
    "universe": {"category": "weather"},
    "entry_rule": {"signal": "fixture"},
    "exit_rule": {"horizon": "resolution"},
    "execution_rule": {"style": "AGGRESSIVE_TAKER", "max_slippage": "0.02"},
    "parameters": {"lookback": 5},
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
RAW_DRAFT_URL = "https://example.com/raw-source"


# ---------------------------------------------------------------------------
# Real verified store fixtures
# ---------------------------------------------------------------------------


def _judgment(**overrides) -> dict:
    value = {
        "lifecycle_action": "CONTINUE", "recommended_health_state": "HEALTHY",
        "risk_direction": "UNCHANGED", "target_risk_band": None,
        "adaptation_recommendation": None,
    }
    value.update(overrides)
    return value


def _draft(request_id: str, strategy: dict) -> dict:
    draft = {
        "schema_version": DRAFT_SCHEMA_VERSION, "request_id": request_id,
        "research_summary": "Balanced public evidence; the edge looks intact but thin.",
        "evidence_for": ["forecast skill persists"], "evidence_against": ["liquidity is thin"],
        "uncertainties": ["seasonality"], "known_missing_data": ["no fill history"],
        "falsification_checks_performed": ["searched for contrary forecast-skill studies"],
        "limitations": ["public web only"],
        "what_would_change_the_conclusion": ["forecast skill collapse"],
        "suggested_next_research_steps": ["collect fill evidence"],
        "source_references": [{"url": RAW_DRAFT_URL, "title": "A", "source_class": "reference"}],
        "confidence_label": "moderate", "strategy_assessment": strategy,
    }
    for flag in DRAFT_AUTHORITY_FLAGS:
        draft[flag] = True
    return draft


def _usage() -> bytes:
    return json.dumps({
        "input_tokens": 50, "output_tokens": 80, "total_tokens": 130, "api_calls": 1,
        "estimated_cost_usd": 0.04, "cost_status": "estimated",
        "cost_source": "official_docs_snapshot", "model": "example-model",
        "provider": "example-provider", "session_id": "s1", "completed": True, "failed": False,
    }).encode("utf-8")


def _outcome(stdout: bytes) -> HermesInvocationOutcome:
    return HermesInvocationOutcome(
        stdout=stdout, stdout_truncated=False, stderr_byte_len=0, stderr_truncated=False,
        usage_file_bytes=_usage(), usage_file_truncated=False, exit_code=0,
        timed_out=False, launch_failed=False, duration_ms=10,
    )


class _StrategyBackend(FakeHermesBackend):
    """Deterministic fake Hermes backend returning one strategy-mode draft."""

    def __init__(self, strategy: dict):
        super().__init__([_outcome(b"{}")])
        self.strategy = strategy

    def invoke(self, **kwargs):
        argv = kwargs["argv"]
        self.call_count += 1
        envelope = json.loads(argv[argv.index("-z") + 1])
        return _outcome(json.dumps(_draft(envelope["request_id"], self.strategy)).encode("utf-8"))


@dataclasses.dataclass
class World:
    lifecycle: Path
    hermes: Path
    family: object
    root: object
    child: object
    grandchild: object
    other: object
    policy: object
    allocation: object

    def append(self, record) -> None:
        result = append_strategy_lifecycle_record(self.lifecycle, record)
        assert result.is_valid, result.error_codes

    def snapshot(self):
        result = load_strategy_lifecycle_store(self.lifecycle)
        assert result.is_valid
        return result.snapshot

    def assess(self, version, *, t: int, strategy: dict | None = None):
        result = sm.run_hermes_strategy_assessment(
            lifecycle_snapshot=self.snapshot(), strategy_version_id=version.strategy_version_id,
            trigger="INITIAL_ASSESSMENT", trigger_ref=None,
            subject_refs=(version.strategy_version_id, version.strategy_family_id), evidence=(),
            information_cutoff=HERMES_CUTOFF, decision_time_ns=t,
            provider_label="example-provider", model_label="example-model",
            backend=_StrategyBackend(_judgment() if strategy is None else strategy),
            store_path=self.hermes, clock=lambda: FIXED_CLOCK,
        )
        assert result.status == sm.STATUS_ASSESSMENT_RECORDED, result.error_code
        return result.assessment

    def app(self, *, lifecycle=True, hermes=True):
        return cockpit.create_app(
            cockpit.CockpitConfig(
                None, None, None, None,
                self.lifecycle if lifecycle else None,
                self.hermes if hermes else None,
            )
        )


def _version(family, parent, label, created, *, lookback=5, refs=()):
    spec = dict(STRATEGY_SPEC)
    spec["parameters"] = {"lookback": lookback}
    return build_strategy_version(
        strategy_family_id=family.strategy_family_id, parent=parent, strategy_label=label,
        evidence_posture="REPEATABLE_STATISTICAL", strategy_code_identity="strategy_code:v1",
        strategy_spec=spec, adaptive_bounds=BOUNDS, evidence_refs=refs, created_time_ns=created,
        creation_provenance="unit:fixture",
    )


def make_world(tmp_path: Path, *, name: str = "stores", label_suffix: str = "") -> World:
    base = tmp_path / name
    base.mkdir(parents=True)
    lifecycle = base / "lifecycle.sqlite3"
    hermes = base / "hermes_strategy.sqlite3"
    assert initialize_strategy_lifecycle_store(lifecycle).is_valid
    sm.initialize_hermes_strategy_manager_store(hermes)
    family = build_strategy_family(
        family_key="research.family" + label_suffix, family_label="Research family",
        created_time_ns=1, creation_provenance="unit:fixture",
    )
    other_family = build_strategy_family(
        family_key="other.family" + label_suffix, family_label="Other family",
        created_time_ns=1, creation_provenance="unit:fixture",
    )
    root = _version(family, None, "root" + label_suffix, 2, refs=("evidence:ref-a", "evidence:ref-b"))
    child = _version(family, root, "child" + label_suffix, 3, lookback=6)
    grandchild = _version(family, child, "grandchild" + label_suffix, 4, lookback=7)
    other = _version(other_family, None, "other" + label_suffix, 3)
    policy = build_portfolio_authority_policy(
        predecessor_policy_id=None, policy_label="Global envelope",
        account_scope_ref="account:public-scope-1", effective_from_ns=10, expires_at_ns=None,
        allowed_order_styles=("AGGRESSIVE_TAKER", "PASSIVE_MAKER"), created_time_ns=10, **LIMITS,
    )
    activate = build_portfolio_policy_receipt(
        action="ACTIVATE", policy_id=policy.policy_id, previous_active_policy_id=None,
        human_authorization_ref="human:karl-approval-1", created_time_ns=20,
    )
    allocation = build_strategy_risk_allocation(
        strategy_version_id=root.strategy_version_id, policy_id=policy.policy_id,
        risk_band="EXPLORATORY_LIVE", active_budget_usd="50", allocation_basis="DIRECT_DECISION",
        decision_ref="decision:unit-1", valid_from_ns=100, valid_until_ns=None, created_time_ns=100,
    )
    world = World(lifecycle, hermes, family, root, child, grandchild, other, policy, allocation)
    for record in (family, other_family, root, child, grandchild, other, policy, activate, allocation):
        world.append(record)
    return world


def _restriction(version, key="pause.1", t=60):
    return build_strategy_restriction_receipt(
        strategy_version_id=version.strategy_version_id, restriction_key=key, action="APPLY",
        restriction_kind="PAUSE_NEW_EXPOSURE", decision_ref="decision:restrict-1",
        created_time_ns=t,
    )


def _health(version, previous, new, t=50):
    return build_strategy_health_receipt(
        strategy_version_id=version.strategy_version_id, previous_health_state=previous,
        new_health_state=new, decision_ref="decision:health-1", created_time_ns=t,
    )


@pytest.fixture
def world(tmp_path: Path) -> World:
    return make_world(tmp_path)


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _method(app, target: str, method: str) -> int:
    return asyncio.run(_asgi_call(app, target, method=method))[0]


# ---------------------------------------------------------------------------
# R01-R17
# ---------------------------------------------------------------------------


def test_r01_verified_loaders_only(world: World, monkeypatch: pytest.MonkeyPatch) -> None:
    world.assess(world.root, t=1_000)
    calls: list[tuple[str, Path]] = []
    real_lifecycle = research.load_strategy_lifecycle_store
    real_hermes = research.load_hermes_strategy_manager_store

    def lifecycle_spy(path):
        calls.append(("lifecycle", path))
        return real_lifecycle(path)

    def hermes_spy(path):
        calls.append(("hermes", path))
        return real_hermes(path)

    monkeypatch.setattr(research, "load_strategy_lifecycle_store", lifecycle_spy)
    monkeypatch.setattr(research, "load_hermes_strategy_manager_store", hermes_spy)
    app = world.app()
    assessment_id = _get(app, "/api/hermes/assessments")[1]["items"][0]["assessment_id"]
    for target in (
        "/api/strategies",
        f"/api/strategies/{world.root.strategy_version_id}",
        "/api/hermes/assessments",
        f"/api/hermes/assessments/{assessment_id}",
    ):
        assert _get(app, target)[0] == 200
    assert {kind for kind, _ in calls} == {"lifecycle", "hermes"}
    assert all(
        path == (world.lifecycle if kind == "lifecycle" else world.hermes) for kind, path in calls
    )
    source = MODULE.read_text(encoding="utf-8")
    assert "import sqlite3" not in source and "sqlite3" not in source
    assert ".connect(" not in source and "open(" not in source
    assert "StrategyLifecycleSnapshot(" not in source
    assert "HermesStrategyManagerStoreSnapshot(" not in source


def test_r02_strategy_list_ordering_and_limit(world: World) -> None:
    app = world.app()
    status, body = _get(app, "/api/strategies")
    assert status == 200 and body["limit"] == 50 and body["count"] == 4
    ids = [item["strategy_version_id"] for item in body["items"]]
    tied = sorted([world.child.strategy_version_id, world.other.strategy_version_id])
    assert ids == [world.grandchild.strategy_version_id, *tied, world.root.strategy_version_id]
    status, body = _get(app, "/api/strategies?limit=2")
    assert status == 200 and body["count"] == 2 and body["limit"] == 2
    assert [item["strategy_version_id"] for item in body["items"]] == ids[:2]
    root = next(item for item in _get(app, "/api/strategies")[1]["items"]
                if item["strategy_version_id"] == world.root.strategy_version_id)
    assert set(root) == {
        "strategy_version_id", "strategy_family_id", "parent_strategy_version_id",
        "strategy_label", "evidence_posture", "adaptation_class", "created_time_ns",
        "current_health_state", "current_allocation", "active_restriction_count",
        "evidence_ref_count", "latest_hermes_assessment",
    }
    assert root["current_allocation"] == {
        "allocation_id": world.allocation.allocation_id, "policy_id": world.policy.policy_id,
        "risk_band": "EXPLORATORY_LIVE", "active_budget_usd": "50",
        "allocation_basis": "DIRECT_DECISION", "valid_from_ns": 100, "valid_until_ns": None,
    }
    assert root["evidence_ref_count"] == 2 and root["latest_hermes_assessment"] is None


def test_r03_strategy_detail_projection(world: World) -> None:
    world.append(_restriction(world.root))
    snapshot = world.snapshot()
    status, body = _get(world.app(), f"/api/strategies/{world.root.strategy_version_id}")
    assert status == 200
    item = body["item"]
    assert item["family"] == {
        "strategy_family_id": world.family.strategy_family_id,
        "family_key": "research.family", "family_label": "Research family",
    }
    assert item["strategy_code_identity"] == "strategy_code:v1"
    assert item["creation_provenance"] == "unit:fixture"
    assert item["evidence_refs"] == ["evidence:ref-a", "evidence:ref-b"]
    assert item["strategy_definition"] == STRATEGY_SPEC
    assert item["adaptive_bounds"] == BOUNDS
    state = item["current_state"]
    assert state["health_state"] == snapshot.health_of(world.root.strategy_version_id)
    assert state["active_policy_id"] == world.policy.policy_id
    assert state["allocation"]["allocation_id"] == world.allocation.allocation_id
    receipt = snapshot.restrictions_of(world.root.strategy_version_id)[0]
    assert state["active_restrictions"] == [{
        "restriction_receipt_id": receipt.restriction_receipt_id,
        "restriction_key": "pause.1", "restriction_kind": "PAUSE_NEW_EXPOSURE",
        "max_active_budget_usd": None, "created_time_ns": 60,
    }]
    assert state["strategy_lifecycle_context_sha256"] == sm.strategy_lifecycle_context_fingerprint(
        snapshot, world.root.strategy_version_id
    )
    assert item["latest_hermes_assessment"] is None
    summary = next(entry for entry in _get(world.app(), "/api/strategies")[1]["items"]
                   if entry["strategy_version_id"] == world.root.strategy_version_id)
    assert summary["active_restriction_count"] == 1


def test_r03_lineage_is_exact_root_to_target(world: World) -> None:
    app = world.app()
    expected = [
        world.root.strategy_version_id,
        world.child.strategy_version_id,
        world.grandchild.strategy_version_id,
    ]
    item = _get(app, f"/api/strategies/{world.grandchild.strategy_version_id}")[1]["item"]
    assert item["lineage_strategy_version_ids"] == expected
    assert item["parent_strategy_version_id"] == world.child.strategy_version_id
    assert item["adaptation_class"] == "BOUNDED_ADAPTATION"
    root = _get(app, f"/api/strategies/{world.root.strategy_version_id}")[1]["item"]
    assert root["lineage_strategy_version_ids"] == [world.root.strategy_version_id]
    other = _get(app, f"/api/strategies/{world.other.strategy_version_id}")[1]["item"]
    assert other["lineage_strategy_version_ids"] == [world.other.strategy_version_id]


def test_r04_latest_assessment_uses_verified_manager_mapping(
    world: World, monkeypatch: pytest.MonkeyPatch
) -> None:
    first = world.assess(world.root, t=1_000)
    second = world.assess(world.root, t=2_000, strategy=_judgment(lifecycle_action="CONTINUE"))
    assert second.predecessor_assessment_id == first.assessment_id
    app = world.app()
    latest = _get(app, f"/api/strategies/{world.root.strategy_version_id}")[1]["item"][
        "latest_hermes_assessment"
    ]
    assert latest["assessment_id"] == second.assessment_id
    # Prove the projection follows the verified manager mapping, not timestamp/order:
    # point the mapping at the older assessment and the projection must follow it.
    real = sm.load_hermes_strategy_manager_store(world.hermes)
    remapped = dataclasses.replace(
        real,
        latest_assessment_by_strategy_version=((world.root.strategy_version_id, first.assessment_id),),
    )
    monkeypatch.setattr(research, "load_hermes_strategy_manager_store", lambda _path: remapped)
    for target in ("/api/strategies", f"/api/strategies/{world.root.strategy_version_id}"):
        body = _get(app, target)[1]
        entries = body["items"] if "items" in body else [body["item"]]
        root = next(e for e in entries if e["strategy_version_id"] == world.root.strategy_version_id)
        assert root["latest_hermes_assessment"]["assessment_id"] == first.assessment_id
        others = [e for e in entries if e["strategy_version_id"] != world.root.strategy_version_id]
        assert all(e["latest_hermes_assessment"] is None for e in others)


def test_r05_exact_current_context_is_current(world: World) -> None:
    assessment = world.assess(world.root, t=1_000)
    app = world.app()
    item = _get(app, "/api/hermes/assessments")[1]["items"][0]
    assert item["assessment_id"] == assessment.assessment_id
    assert item["context_status"] == "CURRENT"
    assert assessment.strategy_lifecycle_context_sha256 == sm.strategy_lifecycle_context_fingerprint(
        world.snapshot(), world.root.strategy_version_id
    )
    latest = _get(app, "/api/strategies")[1]["items"]
    root = next(e for e in latest if e["strategy_version_id"] == world.root.strategy_version_id)
    assert root["latest_hermes_assessment"]["context_status"] == "CURRENT"
    # An unrelated strategy's canonical transition does not change this context.
    world.append(_health(world.other, "NEW", "HEALTHY"))
    assert _get(app, "/api/hermes/assessments")[1]["items"][0]["context_status"] == "CURRENT"


@pytest.mark.parametrize("transition", ["health", "allocation", "restriction"])
def test_r06_lifecycle_transition_after_assessment_is_stale_context(
    tmp_path: Path, transition: str
) -> None:
    world = make_world(tmp_path)
    assessment = world.assess(world.root, t=1_000)
    app = world.app()
    assert _get(app, "/api/hermes/assessments")[1]["items"][0]["context_status"] == "CURRENT"
    if transition == "health":
        world.append(_health(world.root, "NEW", "WATCH"))
    elif transition == "allocation":
        world.append(build_strategy_risk_allocation(
            strategy_version_id=world.root.strategy_version_id, policy_id=world.policy.policy_id,
            risk_band="PAPER", active_budget_usd="0", allocation_basis="DIRECT_DECISION",
            decision_ref="decision:unit-2", valid_from_ns=200, valid_until_ns=None,
            created_time_ns=200,
        ))
    else:
        world.append(_restriction(world.root))
    item = _get(app, "/api/hermes/assessments")[1]["items"][0]
    assert item["assessment_id"] == assessment.assessment_id
    assert item["context_status"] == "STALE_CONTEXT"
    detail = _get(app, f"/api/hermes/assessments/{assessment.assessment_id}")[1]["item"]
    assert detail["context_status"] == "STALE_CONTEXT"
    latest = _get(app, f"/api/strategies/{world.root.strategy_version_id}")[1]["item"][
        "latest_hermes_assessment"
    ]
    assert latest["context_status"] == "STALE_CONTEXT"


def test_r07_different_lifecycle_target_is_target_missing(tmp_path: Path) -> None:
    world = make_world(tmp_path)
    assessment = world.assess(world.root, t=1_000)
    elsewhere = make_world(tmp_path, name="elsewhere", label_suffix="-b")
    assert elsewhere.snapshot().version_by_id(world.root.strategy_version_id) is None
    app = cockpit.create_app(
        cockpit.CockpitConfig(None, None, None, None, elsewhere.lifecycle, world.hermes)
    )
    item = _get(app, "/api/hermes/assessments")[1]["items"][0]
    assert item["assessment_id"] == assessment.assessment_id
    assert item["context_status"] == "TARGET_MISSING"
    detail = _get(app, f"/api/hermes/assessments/{assessment.assessment_id}")
    assert detail[0] == 200 and detail[1]["item"]["context_status"] == "TARGET_MISSING"
    for strategy in _get(app, "/api/strategies")[1]["items"]:
        assert strategy["latest_hermes_assessment"] is None
    assert set(research.CONTEXT_STATUSES) == {"CURRENT", "STALE_CONTEXT", "TARGET_MISSING"}


def test_r08_lifecycle_usable_while_hermes_unavailable(world: World) -> None:
    world.assess(world.root, t=1_000)
    tampered = world.hermes.parent / "tampered_hermes.sqlite3"
    tampered.write_bytes(b"not a hermes store" * 64)
    for app in (
        world.app(hermes=False),
        cockpit.create_app(
            cockpit.CockpitConfig(None, None, None, None, world.lifecycle, tampered)
        ),
    ):
        status, body = _get(app, "/api/strategies")
        assert status == 200 and body["count"] == 4
        assert all(item["latest_hermes_assessment"] is None for item in body["items"])
        status, body = _get(app, f"/api/strategies/{world.root.strategy_version_id}")
        assert status == 200 and body["item"]["latest_hermes_assessment"] is None
        assert _get(app, "/api/hermes/assessments") == UNAVAILABLE
        assert _get(app, "/api/hermes/assessments/hermesstrategyassessment:sha256:" + "a" * 64) == UNAVAILABLE
    # Hermes routes need the lifecycle snapshot to derive context status.
    assert _get(world.app(lifecycle=False), "/api/hermes/assessments") == UNAVAILABLE


def test_r09_invalid_sources_map_to_source_unavailable_only(world: World) -> None:
    base = world.lifecycle.parent
    garbage = base / "garbage.sqlite3"
    garbage.write_bytes(b"\x00garbage" * 128)
    wrong_suffix = base / "lifecycle.db"
    wrong_suffix.write_bytes(world.lifecycle.read_bytes())
    tampered = base / "tampered_lifecycle.sqlite3"
    raw = bytearray(world.lifecycle.read_bytes())
    assert raw.count(b"research.family") >= 1
    tampered.write_bytes(bytes(raw).replace(b"research.family", b"tampered.family"))
    assert not load_strategy_lifecycle_store(tampered).is_valid
    candidates = (
        None, base / "missing.sqlite3", garbage, wrong_suffix, tampered,
        world.hermes,  # valid file, wrong schema / application id
    )
    for candidate in candidates:
        app = cockpit.create_app(
            cockpit.CockpitConfig(None, None, None, None, candidate, world.hermes)
        )
        assert _get(app, "/api/strategies") == UNAVAILABLE
        assert _get(app, f"/api/strategies/{world.root.strategy_version_id}") == UNAVAILABLE
        assert _get(app, "/api/hermes/assessments") == UNAVAILABLE
    for candidate in (None, base / "missing.sqlite3", garbage, world.lifecycle):
        app = cockpit.create_app(
            cockpit.CockpitConfig(None, None, None, None, world.lifecycle, candidate)
        )
        assert _get(app, "/api/hermes/assessments") == UNAVAILABLE
        assert _get(app, "/api/strategies")[0] == 200


def test_r10_identifier_validation(world: World) -> None:
    app = world.app()
    for bad in (
        "not-an-id", "strategyversion:sha256:" + "A" * 64, "strategyversion:sha256:" + "a" * 63,
        "strategyfamily:sha256:" + "a" * 64, "strategyversion:sha256:" + "a" * 65,
        "hermesstrategyassessment:sha256:" + "a" * 64,
    ):
        status, body = _get(app, f"/api/strategies/{bad}")
        assert (status, body) == INVALID and bad not in json.dumps(body)
    for bad in (
        "not-an-id", "hermesstrategyassessment:sha256:" + "G" * 64,
        "strategyversion:sha256:" + "a" * 64, "hermesstrategyrun:sha256:" + "a" * 64,
    ):
        status, body = _get(app, f"/api/hermes/assessments/{bad}")
        assert (status, body) == INVALID and bad not in json.dumps(body)
    assert _get(app, "/api/strategies/strategyversion:sha256:" + "f" * 64) == NOT_FOUND
    assert _get(app, "/api/hermes/assessments/hermesstrategyassessment:sha256:" + "f" * 64) == NOT_FOUND
    # Malformed ids are rejected before any source is consulted.
    unconfigured = cockpit.create_app(cockpit.CockpitConfig(None, None))
    assert _get(unconfigured, "/api/strategies/not-an-id") == INVALID
    assert _get(unconfigured, "/api/strategies/strategyversion:sha256:" + "f" * 64) == UNAVAILABLE


def test_r11_list_query_closure(world: World) -> None:
    world.assess(world.root, t=1_000)
    world.assess(world.other, t=1_000)
    app = world.app()
    for route in ("/api/strategies", "/api/hermes/assessments"):
        for query in ("?limit=0", "?limit=101", "?limit=no", "?limit=1.0", "?limit=-1",
                      "?limit=1&limit=2", "?status=CURRENT", "?limit=1&x=1"):
            assert _get(app, route + query) == INVALID, (route, query)
        status, body = _get(app, route + "?limit=1")
        assert status == 200 and body["count"] == 1 and body["limit"] == 1
        assert _get(app, route + "?limit=100")[1]["limit"] == 100
    items = _get(app, "/api/hermes/assessments")[1]["items"]
    assert [item["assessment_id"] for item in items] == sorted(
        (item["assessment_id"] for item in items)
    )  # equal decision_time_ns -> assessment_id ASC
    later = world.assess(world.root, t=5_000)
    first = _get(app, "/api/hermes/assessments?limit=1")[1]["items"][0]
    assert first["assessment_id"] == later.assessment_id  # decision_time_ns DESC


def test_r12_research_routes_are_get_only(world: World) -> None:
    app = world.app()
    domain = {
        route.path: set(route.methods or ())
        for route in app.routes
        if route.path.startswith("/api/")
    }
    assert len(domain) == 25
    for route in RESEARCH_ROUTES + ALPHA_ROUTES:
        assert domain[route] == {"GET"}
    targets = (
        "/api/strategies",
        f"/api/strategies/{world.root.strategy_version_id}",
        "/api/hermes/assessments",
        "/api/hermes/assessments/hermesstrategyassessment:sha256:" + "a" * 64,
    )
    for target in targets:
        for method in ("POST", "PUT", "PATCH", "DELETE"):
            assert _method(app, target, method) == 405, (target, method)


def test_r13_store_bytes_unchanged_after_reads(world: World) -> None:
    assessment = world.assess(world.root, t=1_000)
    before = {world.lifecycle: _digest(world.lifecycle), world.hermes: _digest(world.hermes)}
    app = world.app()
    for target in (
        "/api/strategies?limit=100",
        f"/api/strategies/{world.root.strategy_version_id}",
        f"/api/strategies/{world.grandchild.strategy_version_id}",
        "/api/hermes/assessments?limit=100",
        f"/api/hermes/assessments/{assessment.assessment_id}",
    ):
        assert _get(app, target)[0] == 200
    after = {world.lifecycle: _digest(world.lifecycle), world.hermes: _digest(world.hermes)}
    assert before == after
    assert sorted(p.name for p in world.lifecycle.parent.iterdir()) == [
        "hermes_strategy.sqlite3", "lifecycle.sqlite3",
    ]


def test_r14_dto_sanitization(world: World) -> None:
    assessment = world.assess(world.root, t=1_000)
    app = world.app()
    bodies = [
        _get(app, target)[1]
        for target in (
            "/api/strategies",
            f"/api/strategies/{world.root.strategy_version_id}",
            "/api/hermes/assessments",
            f"/api/hermes/assessments/{assessment.assessment_id}",
        )
    ]
    serialized = json.dumps(bodies)
    for banned in (
        str(world.lifecycle), str(world.hermes), str(world.lifecycle.parent), "sqlite",
        "Traceback", "Exception", RAW_DRAFT_URL, "https://", "source_references",
        "research_summary", "\"request_id\"", "stdout", "stderr", "prompt", "account:public-scope-1",
        "human:karl-approval-1", "private_key", "api_key", "passphrase", "mnemonic",
    ):
        assert banned not in serialized, banned
    errors = json.dumps([
        _get(cockpit.create_app(cockpit.CockpitConfig(None, None, None, None,
                                                      world.lifecycle.parent / "x.sqlite3")),
             "/api/strategies")[1],
    ])
    assert errors == json.dumps([{"error": {"code": "SOURCE_UNAVAILABLE"}}])


def test_r15_no_authority_promotion_or_raw_output(world: World) -> None:
    assessment = world.assess(world.root, t=1_000)
    app = world.app()
    detail = _get(app, f"/api/hermes/assessments/{assessment.assessment_id}")[1]["item"]
    assert detail["canonical_soft_strategy_decision"] is True
    assert detail["non_authority"] == {
        "canonical_soft_strategy_decision": True, "no_credential_authority": True,
        "no_portfolio_policy_authority": True, "no_hard_risk_override": True,
        "no_paper_execution_authority": True, "no_order_authority": True,
        "no_execution_authority": True, "no_live_authority": True,
    }
    assert detail["run"] == {
        "provider_label": "example-provider", "model_label": "example-model",
        "hermes_version": detail["run"]["hermes_version"], "terminal_status": detail["run"]["terminal_status"],
        "start_utc": detail["run"]["start_utc"], "end_utc": detail["run"]["end_utc"],
        "estimated_cost_usd": detail["run"]["estimated_cost_usd"],
        "cost_status": detail["run"]["cost_status"], "cost_source": detail["run"]["cost_source"],
    }
    assert detail["evidence_for"] == ["forecast skill persists"]
    assert detail["falsification_checks_performed"] == ["searched for contrary forecast-skill studies"]
    assert detail["adaptation_recommendation"] is None
    bodies = [
        _get(app, "/api/strategies")[1],
        _get(app, f"/api/strategies/{world.root.strategy_version_id}")[1],
        _get(app, "/api/hermes/assessments")[1],
        {"item": detail},
    ]

    def keys(value) -> set[str]:
        found: set[str] = set()
        if isinstance(value, dict):
            for key, item in value.items():
                found.add(key)
                found |= keys(item)
        elif isinstance(value, list):
            for item in value:
                found |= keys(item)
        return found

    all_keys = set().union(*(keys(body) for body in bodies))
    for banned in ("approved", "approval", "eligible", "eligibility", "tradeable", "permit",
                   "live_ready", "execution_ready", "gate_c", "raw", "prompt", "reasoning",
                   "chain_of_thought", "stdout", "draft"):
        assert not any(banned in key for key in all_keys), banned
    assert not re.search(r"(?i)approved|gate-?c\s*pass|live[-_ ]eligible", json.dumps(bodies))


def test_r17_existing_cockpit_contract_preserved(world: World) -> None:
    config = cockpit.CockpitConfig(None, None, None, None)
    assert config.strategy_lifecycle_path is None and config.hermes_strategy_manager_path is None
    positional = cockpit.CockpitConfig(None, None, None, None, world.lifecycle, world.hermes)
    assert positional.strategy_lifecycle_path == world.lifecycle
    assert positional.hermes_strategy_manager_path == world.hermes
    with pytest.raises(TypeError):
        cockpit.CockpitConfig(None, None, None, None, str(world.lifecycle))
    unconfigured = cockpit.create_app(config)
    for target in ("/api/strategies", "/api/hermes/assessments"):
        assert _get(unconfigured, target) == UNAVAILABLE
    health = _get(unconfigured, "/api/health")[1]
    assert set(health) == {"status", "read_only", "wp169", "wp170", "paper", "gateway"}
    cockpit_source = (ROOT / "src" / "operator_cockpit.py").read_text(encoding="utf-8")
    for flag in ("--strategy-lifecycle-store", "--hermes-strategy-manager-store"):
        assert f'parser.add_argument("{flag}", type=Path)' in cockpit_source
    assert "environ" not in cockpit_source and "getenv" not in cockpit_source


def test_frontend_research_surface_is_read_only_and_bounded() -> None:
    app_source = (FRONTEND / "app.tsx").read_text(encoding="utf-8")
    api_source = (FRONTEND / "api.ts").read_text(encoding="utf-8")
    stories = (FRONTEND / "foundation.stories.tsx").read_text(encoding="utf-8")
    for route in ("/overview", "/markets", "/experiments", "/strategies", "/hermes", "/paper", "/audit"):
        assert f'path="{route.lstrip("/")}"' in app_source or f'"{route}"' in app_source, route
    for key in ('"strategies", "list"', '"strategies", "detail"', '"hermes", "list"', '"hermes", "detail"'):
        assert key in api_source, key
    combined = app_source + api_source
    for banned in ("setInterval", "refetchInterval", "EventSource", "WebSocket", "localStorage",
                   "zustand", "error.message", "useMutation"):
        assert banned not in combined, banned
    assert not re.search(r"\b(POST|PUT|PATCH|DELETE)\b", combined)
    for label in (">Run<", ">Reassess<", ">Approve<", ">Apply<", ">Allocate<", ">Pause<",
                  ">Scale<", ">Trade<"):
        assert label not in app_source, label
    assert "soft research judgments" in app_source
    assert "not actual exposure" in app_source
    for intercepted in ("/api/strategies", "/api/hermes/assessments"):
        assert intercepted in stories


# ---------------------------------------------------------------------------
# S10-CC-RESEARCH-02: Alpha Factory + Alpha Discovery fixtures (real verified stores)
# ---------------------------------------------------------------------------


ALPHA_AUTHORITY = {
    "advisory_only": True, "no_execution_authority": True,
    "no_strategy_authority": True, "no_qualification_authority": True,
}
BANNED_ALPHA_KEYS = (
    "qualified", "qualification_ready", "approved", "approval", "tradeable", "profitable",
    "expected_return", "strategy_selected", "execution_ready", "paper_ready", "live_ready",
    "gate_c", "strategy_version", "assessment_id",
)


def _ok(result):
    assert result.is_valid, result.error_codes
    return result.record


@dataclasses.dataclass
class AlphaWorld:
    alpha: Path
    discovery: Path
    sources: dict
    candidates: dict
    families: dict
    episodes: dict
    triage: dict
    queue: object
    replay_queue: object | None
    change: object
    policy: object
    universe: object

    def app(self, *, alpha=True, discovery=True, alpha_path=None, discovery_path=None):
        return cockpit.create_app(
            cockpit.CockpitConfig(
                None, None, None, None, None, None,
                alpha_path if alpha_path is not None else (self.alpha if alpha else None),
                discovery_path if discovery_path is not None else (self.discovery if discovery else None),
            )
        )

    def alpha_snapshot(self):
        result = AFR.load_and_verify_alpha_factory_registry(self.alpha)
        assert result.is_valid
        return result.snapshot

    def sequence(self, record_id: str) -> int:
        return next(e.sequence_number for e in self.alpha_snapshot().entries if e.record_id == record_id)


def _episode(candidate, family, state, sources, refs, *, pred=None, reopened=None, tag=""):
    return _ok(AF.build_research_episode(episode_input(
        candidate_id=candidate.candidate_id, hypothesis_family_id=family.hypothesis_family_id,
        predecessor_episode_id=pred.research_episode_id if pred else None,
        reopened_episode_id=reopened.research_episode_id if reopened else None,
        result_state=state, exact_scope={"market": candidate.scope_key, "tag": tag or state},
        source_reference_ids=[s.source_reference_id for s in sources],
        deterministic_evidence_refs=list(refs), evidence_for=[f"for {tag or state}"],
        evidence_against=[f"against {tag or state}"], known_missing_data=[f"missing {tag or state}"],
        material_change_basis=[f"material {tag or state}"],
    )))


def _candidate(name: str, lanes: list[str]):
    return _ok(AF.build_opportunity_candidate(candidate_input(
        title=f"Candidate {name}", scope_key=f"scope-{name}", evidence_lanes=lanes,
        subject_refs=[f"market:polymarket:{name}"],
        novelty_dimensions={"subject_keys": [name], "scope_key": f"scope-{name}",
                            "mechanism_key": f"mechanism-{name}"},
    )))


def _family(name: str):
    return _ok(AF.build_hypothesis_family(family_input(
        family_name=f"Family {name}", mechanism_key=f"mechanism-family-{name}",
        mechanism_dimensions={"driver": name},
    )))


def make_alpha_world(tmp_path: Path, *, replay: bool = False, name: str = "alpha_stores") -> AlphaWorld:
    base = tmp_path / name
    base.mkdir(parents=True)
    alpha = (base / "alpha_factory.sqlite3").resolve()
    discovery = (base / "alpha_discovery.sqlite3").resolve()
    assert AFR.initialize_alpha_factory_registry(alpha).is_valid
    s1 = _ok(AF.build_research_source_reference(source_input()))
    s2 = _ok(AF.build_research_source_reference(source_input(
        source_class="REFERENCE", source_locator="https://example.org/reference", title="Reference")))
    cand_a = _candidate("alpha", ["WEATHER", "FUNDAMENTAL"])
    fam_1, fam_2 = _family("one"), _family("two")
    # A/F1 lineage: e1 root; e2 and e3 are divergent siblings of e1; e4 reopens e3.
    e1 = _episode(cand_a, fam_1, "WATCH_FOR_CHANGE", (s1,), ("det-a-1",), tag="e1")
    e2 = _episode(cand_a, fam_1, "RESEARCH_SUPPORTIVE", (s1, s2), ("det-a-1", "det-a-2"), pred=e1, tag="e2")
    e3 = _episode(cand_a, fam_1, "NO_EDGE_CURRENTLY", (s1,), ("det-a-3",), pred=e1, tag="e3")
    e4 = _episode(cand_a, fam_1, "REOPEN_TRIGGERED", (s1,), ("det-a-4",), reopened=e3, tag="e4")
    # A/F2 lineage: one research leaf.
    e5 = _episode(cand_a, fam_2, "DATA_INSUFFICIENT", (s2,), ("det-a-5",), tag="e5")
    appended = AFR.append_alpha_factory_records(alpha, [s1, s2, cand_a, fam_1, fam_2, e1, e2, e3, e4, e5])
    assert appended.is_valid, appended.error_codes
    cand_b = _candidate("beta", ["WEATHER"])
    fam_b = _family("beta")
    e6 = _episode(cand_b, fam_b, "RESEARCH_SUPPORTIVE", (s2,), ("det-b-1",), tag="e6")
    appended = AFR.append_alpha_factory_records(alpha, [cand_b, fam_b, e6])
    assert appended.is_valid, appended.error_codes

    policy = _policy()
    markets = [
        _market("alpha"), _market("beta"), _market("epsilon"), _market("zeta"),
        dataclasses.replace(_market("gamma"), market_status="closed"),
        dataclasses.replace(_market("delta"), data_gap_codes=("METADATA_CONFLICT",)),
    ]
    prior = _universe(policy, [m for m in markets if m.market_id != "market:polymarket:zeta"] + [_market("omega")],
                      as_of="2026-01-01T00:00:00Z")
    current = _universe(policy, markets)
    change = _change(policy, prior, current, markets[0])
    bases = AD.build_pre_allocation_triage_bases(
        current, policy, analysis_temporal_mode="CURRENT_BUILD_ANALYSIS",
        alpha_memory_temporal_posture="CURRENT_REGISTRY_BUILD_TIME_ONLY",
        alpha_registry_path=alpha, prior=prior, material_changes=(change,),
    )
    assert bases.is_valid, bases.error_codes
    allocated = AD.allocate_and_finalize_research_queue(current, policy, bases.records, prior=prior)
    assert allocated.is_valid, allocated.error_codes
    assert ADR.initialize_alpha_discovery_registry(discovery).is_valid
    appended = ADR.append_alpha_discovery_records(discovery, [policy, prior, current, change, *allocated.records])
    assert appended.is_valid, appended.error_codes
    triage = {r.market_id.split(":")[-1]: r for r in allocated.records if isinstance(r, AD.MarketTriageDecision)}
    replay_queue = None
    if replay:
        later = _universe(policy, markets, as_of="2026-01-01T00:05:00Z")
        replay_bases = AD.build_pre_allocation_triage_bases(
            later, policy, analysis_temporal_mode="HISTORICAL_REPLAY",
            alpha_memory_temporal_posture="HISTORICAL_AVAILABILITY_UNPROVEN",
        )
        assert replay_bases.is_valid, replay_bases.error_codes
        replayed = AD.allocate_and_finalize_research_queue(later, policy, replay_bases.records)
        assert replayed.is_valid, replayed.error_codes
        appended = ADR.append_alpha_discovery_records(discovery, [later, *replayed.records])
        assert appended.is_valid, appended.error_codes
        replay_queue = replayed.record
        for record in replayed.records:
            if isinstance(record, AD.MarketTriageDecision):
                triage["replay-" + record.market_id.split(":")[-1]] = record
    return AlphaWorld(
        alpha, discovery, {"s1": s1, "s2": s2}, {"a": cand_a, "b": cand_b},
        {"one": fam_1, "two": fam_2, "beta": fam_b},
        {"e1": e1, "e2": e2, "e3": e3, "e4": e4, "e5": e5, "e6": e6},
        triage, allocated.record, replay_queue, change, policy, current,
    )


@pytest.fixture
def alpha_world(tmp_path: Path) -> AlphaWorld:
    return make_alpha_world(tmp_path)


def _keys(value) -> set[str]:
    found: set[str] = set()
    if isinstance(value, dict):
        for key, item in value.items():
            found.add(key)
            found |= _keys(item)
    elif isinstance(value, list):
        for item in value:
            found |= _keys(item)
    return found


def _alpha_targets(world: AlphaWorld) -> tuple[str, ...]:
    return (
        "/api/alpha/memory",
        "/api/alpha/candidates?limit=100",
        f"/api/alpha/candidates/{world.candidates['a'].candidate_id}",
        f"/api/alpha/episodes/{world.episodes['e2'].research_episode_id}",
        "/api/alpha/discovery/queue",
        f"/api/alpha/discovery/triage/{world.triage['alpha'].market_triage_decision_id}",
    )


# ---------------------------------------------------------------------------
# A01-A39
# ---------------------------------------------------------------------------


def test_a01_alpha_factory_verified_loader_only(alpha_world: AlphaWorld, monkeypatch) -> None:
    calls: list[Path] = []
    real = research.load_and_verify_alpha_factory_registry

    def spy(path):
        calls.append(path)
        return real(path)

    monkeypatch.setattr(research, "load_and_verify_alpha_factory_registry", spy)
    app = alpha_world.app()
    for target in _alpha_targets(alpha_world)[:4]:
        assert _get(app, target)[0] == 200, target
    assert len(calls) == 4 and all(path == alpha_world.alpha for path in calls)
    # The triage route consults Alpha memory only through the same verified loader.
    assert _get(app, _alpha_targets(alpha_world)[5])[0] == 200
    assert calls[-1] == alpha_world.alpha and len(calls) == 5


def test_a02_alpha_discovery_verified_loader_only(alpha_world: AlphaWorld, monkeypatch) -> None:
    calls: list[Path] = []
    real = research.load_and_verify_alpha_discovery_registry

    def spy(path):
        calls.append(path)
        return real(path)

    monkeypatch.setattr(research, "load_and_verify_alpha_discovery_registry", spy)
    app = alpha_world.app()
    for target in _alpha_targets(alpha_world)[4:]:
        assert _get(app, target)[0] == 200, target
    for target in _alpha_targets(alpha_world)[:4]:
        assert _get(app, target)[0] == 200, target
    assert calls == [alpha_world.discovery, alpha_world.discovery]


def test_a03_research_module_alpha_boundary() -> None:
    source = MODULE.read_text(encoding="utf-8")
    tree = ast.parse(source)
    modules: set[str] = set()
    names: dict[str, set[str]] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules |= {alias.name for alias in node.names}
        elif isinstance(node, ast.ImportFrom):
            modules.add(node.module or "")
            names.setdefault(node.module or "", set()).update(alias.name for alias in node.names)
    assert {name for name in modules if name.startswith("src.")} == {
        "src.research_runtime.hermes_controlled_runtime.strategy_manager",
        "src.strategy_lifecycle",
        "src.strategy_lifecycle.models",
        "src.data_layer.analytical_research.alpha_factory",
        "src.data_layer.analytical_research.alpha_factory_registry",
        "src.data_layer.analytical_research.alpha_discovery",
        "src.data_layer.analytical_research.alpha_discovery_registry",
    }
    # Alpha imports: record types plus verified read-only loaders only.
    assert names["src.data_layer.analytical_research.alpha_factory"] == {
        "HypothesisFamily", "OpportunityCandidate", "ResearchEpisode", "ResearchSourceReference",
    }
    assert names["src.data_layer.analytical_research.alpha_factory_registry"] == {
        "AlphaFactoryRegistrySnapshot", "load_and_verify_alpha_factory_registry",
    }
    assert names["src.data_layer.analytical_research.alpha_discovery"] == {
        "AlphaDiscoveryPolicy", "AlphaResearchQueueSnapshot", "AlphaUniverseSnapshot",
        "MarketTriageDecision", "MaterialChangeEvent",
    }
    assert names["src.data_layer.analytical_research.alpha_discovery_registry"] == {
        "AlphaDiscoveryRegistrySnapshot", "load_and_verify_alpha_discovery_registry",
    }
    network = {"requests", "httpx", "urllib", "socket", "websocket", "websockets", "aiohttp",
               "subprocess", "sqlite3", "http"}
    assert not any(name.split(".")[0] in network for name in modules)
    assert not any("qualification" in name or "gate" in name or "experiment" in name for name in modules)
    for forbidden in (
        "sqlite3", ".connect(", "open(", "paper_trading", "execution_gateway",
        "execution_feasibility", "exploratory_gate_c", "qualification_gate", "QualificationCandidate",
        "alpha_factory_gate", "experiment_registry", "build_preregistered_experiment", "gate_evidence",
        "run_controlled_hermes_research", "run_hermes_strategy_assessment",
        "append_strategy_lifecycle_record", "initialize_strategy_lifecycle_store",
        "initialize_hermes_strategy_manager_store", "append_alpha_factory_records",
        "initialize_alpha_factory_registry", "append_alpha_discovery_records",
        "initialize_alpha_discovery_registry", "build_pre_allocation_triage_bases",
        "allocate_and_finalize_research_queue", "build_alpha_universe_snapshot",
        "compare_alpha_universes", "PreAllocationTriageBasis", "AlphaFactoryRegistrySnapshot(",
        "AlphaDiscoveryRegistrySnapshot(", "StrategyLifecycleSnapshot(",
        "HermesStrategyManagerStoreSnapshot(", "write_text", "write_bytes", "threading", "asyncio",
        "setInterval", "environ", "getenv", "local_data", "worktree", "audit_seed\"",
    ):
        assert forbidden not in source, forbidden
    cockpit_source = (ROOT / "src" / "operator_cockpit.py").read_text(encoding="utf-8")
    for route in RESEARCH_ROUTES + ALPHA_ROUTES:
        assert f'@app.get("{route}")' in cockpit_source
    assert not re.search(r"@app\.(post|put|patch|delete|websocket|api_route)\(", cockpit_source)
    # The cockpit reaches Alpha state only through the research projection module.
    cockpit_imports = {
        node.module or "" for node in ast.walk(ast.parse(cockpit_source)) if isinstance(node, ast.ImportFrom)
    }
    assert not any("alpha" in name for name in cockpit_imports)


def test_a04_a05_memory_summary(alpha_world: AlphaWorld, tmp_path: Path) -> None:
    snapshot = alpha_world.alpha_snapshot()
    status, body = _get(alpha_world.app(), "/api/alpha/memory")
    assert status == 200
    assert body == {
        "head_entry_hash": snapshot.head_entry_hash,
        "total_rows": snapshot.total_rows,
        "total_payload_bytes": snapshot.total_payload_bytes,
        "record_counts": {
            "research_source_references": 2, "opportunity_candidates": 2,
            "hypothesis_families": 3, "research_episodes": 6,
        },
        **ALPHA_AUTHORITY,
    }
    assert snapshot.total_rows == 13
    empty = (tmp_path / "empty_alpha.sqlite3").resolve()
    assert AFR.initialize_alpha_factory_registry(empty).is_valid
    app = cockpit.create_app(cockpit.CockpitConfig(None, None, None, None, None, None, empty))
    status, body = _get(app, "/api/alpha/memory")
    assert status == 200 and body["head_entry_hash"] is None and body["total_rows"] == 0
    assert set(body["record_counts"].values()) == {0}
    assert _get(app, "/api/alpha/candidates") == (200, {"items": [], "count": 0, "limit": 50})


def test_a06_candidate_list_ordering_and_limit(alpha_world: AlphaWorld) -> None:
    app = alpha_world.app()
    status, body = _get(app, "/api/alpha/candidates")
    assert status == 200 and body["count"] == 2 and body["limit"] == 50
    a, b = alpha_world.candidates["a"], alpha_world.candidates["b"]
    # B was appended in a later batch: greater registry sequence -> listed first.
    assert alpha_world.sequence(b.candidate_id) > alpha_world.sequence(a.candidate_id)
    assert [item["candidate_id"] for item in body["items"]] == [b.candidate_id, a.candidate_id]
    first, second = body["items"]
    assert set(first) == {
        "sequence_number", "candidate_id", "candidate_version", "title", "research_question",
        "subject_refs", "evidence_lanes", "is_multi_lane", "scope_key", "mechanism_hint",
        "novelty_fingerprint", "human_review_required", "family_count", "episode_count",
        "leaf_episode_count",
    }
    assert first["is_multi_lane"] is False and second["is_multi_lane"] is True
    assert second["evidence_lanes"] == list(a.evidence_lanes) and "COMPOSITE" not in json.dumps(body)
    assert (second["family_count"], second["episode_count"], second["leaf_episode_count"]) == (2, 5, 3)
    assert (first["family_count"], first["episode_count"], first["leaf_episode_count"]) == (1, 1, 1)
    assert second["sequence_number"] == alpha_world.sequence(a.candidate_id)
    status, body = _get(app, "/api/alpha/candidates?limit=1")
    assert status == 200 and body["count"] == 1 and body["items"][0]["candidate_id"] == b.candidate_id
    for query in ("?limit=0", "?limit=101", "?limit=x", "?limit=1&limit=2", "?q=alpha", "?limit=1&x=1"):
        assert _get(app, "/api/alpha/candidates" + query) == INVALID, query
    assert _get(app, "/api/alpha/candidates?limit=100")[1]["limit"] == 100


def test_a07_candidate_detail_lineage(alpha_world: AlphaWorld) -> None:
    w = alpha_world
    a, e = w.candidates["a"], w.episodes
    status, body = _get(w.app(), f"/api/alpha/candidates/{a.candidate_id}")
    assert status == 200
    assert set(body) == {"candidate", "hypothesis_families", "research_episodes", "source_references",
                         "deterministic_evidence_refs", "lineage_summary"}
    candidate = body["candidate"]
    assert candidate["candidate_id"] == a.candidate_id and candidate["thesis"] == a.thesis
    assert candidate["novelty_dimensions_json"] == a.novelty_dimensions_json
    assert candidate["is_multi_lane"] is True
    assert {k: candidate[k] for k in ALPHA_AUTHORITY} == ALPHA_AUTHORITY
    families = body["hypothesis_families"]
    expected_families = sorted((w.families["one"], w.families["two"]),
                               key=lambda f: (w.sequence(f.hypothesis_family_id), f.hypothesis_family_id))
    assert [f["hypothesis_family_id"] for f in families] == [f.hypothesis_family_id for f in expected_families]
    assert w.families["beta"].hypothesis_family_id not in json.dumps(body)
    episode_ids = [item["research_episode_id"] for item in body["research_episodes"]]
    expected = sorted((e[k] for k in ("e1", "e2", "e3", "e4", "e5")),
                      key=lambda x: w.sequence(x.research_episode_id))
    assert episode_ids == [x.research_episode_id for x in expected]
    assert e["e6"].research_episode_id not in json.dumps(body)
    assert [s["source_reference_id"] for s in body["source_references"]] == sorted(
        (w.sources["s1"].source_reference_id, w.sources["s2"].source_reference_id),
        key=w.sequence,
    )
    assert set(body["deterministic_evidence_refs"]) == {"det-a-1", "det-a-2", "det-a-3", "det-a-4", "det-a-5"}
    assert len(body["deterministic_evidence_refs"]) == 5
    assert body["lineage_summary"]["family_count"] == 2 and body["lineage_summary"]["episode_count"] == 5


def test_a08_a09_research_leaves(alpha_world: AlphaWorld) -> None:
    w = alpha_world
    e = w.episodes
    body = _get(w.app(), f"/api/alpha/candidates/{w.candidates['a'].candidate_id}")[1]
    by_family = {f["hypothesis_family_id"]: f for f in body["hypothesis_families"]}
    one = by_family[w.families["one"].hypothesis_family_id]
    two = by_family[w.families["two"].hypothesis_family_id]
    # e1 is a predecessor and e3 was reopened by e4: both are non-leaves. e2 (divergent
    # sibling of e3) and e4 are two simultaneous research leaves of the same lineage.
    assert set(one["leaf_episode_ids"]) == {e["e2"].research_episode_id, e["e4"].research_episode_id}
    assert one["episode_count"] == 4
    assert two["leaf_episode_ids"] == [e["e5"].research_episode_id] and two["episode_count"] == 1
    summary = body["lineage_summary"]
    assert summary["leaf_episode_count"] == 3
    assert set(summary["leaf_episode_ids"]) == {
        e["e2"].research_episode_id, e["e4"].research_episode_id, e["e5"].research_episode_id,
    }
    assert e["e1"].research_episode_id not in summary["leaf_episode_ids"]
    assert e["e3"].research_episode_id not in summary["leaf_episode_ids"]
    by_id = {item["research_episode_id"]: item for item in body["research_episodes"]}
    assert by_id[e["e4"].research_episode_id]["reopened_episode_id"] == e["e3"].research_episode_id
    assert by_id[e["e3"].research_episode_id]["result_state"] == "NO_EDGE_CURRENTLY"  # history unchanged
    assert by_id[e["e2"].research_episode_id]["predecessor_episode_id"] == e["e1"].research_episode_id
    # Leaf derivation is per exact (candidate, family) lineage only.
    assert research._research_leaf_ids([w.episodes["e1"], w.episodes["e5"]]) == {
        e["e1"].research_episode_id, e["e5"].research_episode_id,
    }
    assert not re.search(r"(?i)qualified|approved|tradeable", json.dumps(body))


def test_a10_episode_detail_source_refs(alpha_world: AlphaWorld) -> None:
    w = alpha_world
    e2 = w.episodes["e2"]
    status, body = _get(w.app(), f"/api/alpha/episodes/{e2.research_episode_id}")
    assert status == 200
    item = body["item"]
    assert set(item) == {
        "research_episode_id", "episode_version", "candidate_id", "hypothesis_family_id",
        "predecessor_episode_id", "reopened_episode_id", "result_state", "confidence_label",
        "evidence_lanes", "is_multi_lane", "exact_scope_json", "evidence_regime_json",
        "research_question", "thesis", "tested_assumptions", "evidence_for", "evidence_against",
        "uncertainties", "known_missing_data", "falsification_checks_performed", "limitations",
        "what_would_change_the_conclusion", "suggested_next_research_steps", "source_reference_ids",
        "source_references", "deterministic_evidence_refs", "material_change_basis", "producer_type",
        "producer_version", "producer_receipt_ref", "research_as_of", "creation_provenance",
        "human_review_required", *ALPHA_AUTHORITY,
    }
    for field in ("evidence_for", "evidence_against", "uncertainties", "known_missing_data",
                  "falsification_checks_performed", "limitations",
                  "what_would_change_the_conclusion", "suggested_next_research_steps"):
        assert item[field] == list(getattr(e2, field)), field
    assert item["exact_scope_json"] == e2.exact_scope_json
    assert item["predecessor_episode_id"] == w.episodes["e1"].research_episode_id
    s1, s2 = w.sources["s1"], w.sources["s2"]
    assert item["source_reference_ids"] == list(e2.source_reference_ids)
    assert set(e2.source_reference_ids) == {s1.source_reference_id, s2.source_reference_id}
    assert [s["source_reference_id"] for s in item["source_references"]] == list(e2.source_reference_ids)
    resolved = {s["source_reference_id"]: s for s in item["source_references"]}
    assert resolved[s1.source_reference_id] == {
        "source_reference_id": s1.source_reference_id, "source_kind": "PUBLIC_HTTPS",
        "source_class": "OFFICIAL", "source_locator": "https://docs.polymarket.com/rules",
        "title": "Resolution rules", "observed_at": s1.observed_at, "content_sha256": None,
        "provenance": "human_research", "public_research_only": True,
        "advisory_only": True, "no_execution_authority": True,
    }
    assert resolved[s2.source_reference_id]["source_class"] == "REFERENCE"
    # A source reference the verified snapshot cannot resolve fails closed.
    real = AFR.load_and_verify_alpha_factory_registry(w.alpha)
    pruned = dataclasses.replace(real.snapshot, entries=tuple(
        entry for entry in real.snapshot.entries if entry.record_id != s2.source_reference_id))
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(research, "load_and_verify_alpha_factory_registry",
                      lambda _path: dataclasses.replace(real, snapshot=pruned))
        assert _get(w.app(), f"/api/alpha/episodes/{e2.research_episode_id}") == UNAVAILABLE


def test_a11_deterministic_refs_opaque(alpha_world: AlphaWorld) -> None:
    w = alpha_world
    item = _get(w.app(), f"/api/alpha/episodes/{w.episodes['e2'].research_episode_id}")[1]["item"]
    assert item["deterministic_evidence_refs"] == list(w.episodes["e2"].deterministic_evidence_refs)
    body = _get(w.app(), f"/api/alpha/candidates/{w.candidates['a'].candidate_id}")[1]
    first_seen: list[str] = []
    for summary in body["research_episodes"]:  # registry sequence order
        episode = next(e for e in w.episodes.values() if e.research_episode_id == summary["research_episode_id"])
        first_seen += [ref for ref in episode.deterministic_evidence_refs if ref not in first_seen]
    assert body["deterministic_evidence_refs"] == first_seen
    serialized = json.dumps([item, body])
    # Opaque: no derived type, URL, file, experiment, gate or route for evidence refs.
    for derived in ("det-a-1/", "/api/experiments", "experiment:", "evidence_ref_type",
                    "evidence_ref_url", "file://"):
        assert derived not in serialized, derived


def test_a12_research_supportive_not_promoted(alpha_world: AlphaWorld) -> None:
    w = alpha_world
    app = w.app()
    bodies = [_get(app, target)[1] for target in _alpha_targets(w)]
    bodies.append(_get(app, f"/api/alpha/episodes/{w.episodes['e6'].research_episode_id}")[1])
    assert bodies[-1]["item"]["result_state"] == "RESEARCH_SUPPORTIVE"
    all_keys = set().union(*(_keys(body) for body in bodies))
    for banned in BANNED_ALPHA_KEYS:
        assert not any(banned in key for key in all_keys), banned
    serialized = json.dumps(bodies)
    for banned in ("QUAL_PASS", "qualified", "tradeable", "live_ready", "paper_ready", "profitable"):
        assert banned not in serialized, banned
    for flag in ALPHA_AUTHORITY:
        assert f'"{flag}": false' not in serialized


def test_a13_latest_recorded_queue(tmp_path: Path) -> None:
    world = make_alpha_world(tmp_path, replay=True)
    snapshot = ADR.load_and_verify_alpha_discovery_registry(world.discovery).snapshot
    queues = [e for e in snapshot.entries if isinstance(e.record, AD.AlphaResearchQueueSnapshot)]
    assert len(queues) == 2
    latest = max(queues, key=lambda e: e.sequence_number)
    assert latest.record == world.replay_queue
    status, body = _get(world.app(), "/api/alpha/discovery/queue")
    assert status == 200
    assert body["queue"]["alpha_research_queue_snapshot_id"] == world.replay_queue.alpha_research_queue_snapshot_id
    assert body["queue_sequence_number"] == latest.sequence_number
    assert body["discovery_registry_head_entry_hash"] == snapshot.head_entry_hash
    # A verified Discovery registry without any queue has no latest recorded queue.
    empty = (tmp_path / "no_queue.sqlite3").resolve()
    assert ADR.initialize_alpha_discovery_registry(empty).is_valid
    assert ADR.append_alpha_discovery_records(empty, [world.policy]).is_valid
    app = cockpit.create_app(cockpit.CockpitConfig(None, None, None, None, None, None, None, empty))
    assert _get(app, "/api/alpha/discovery/queue") == NOT_FOUND


def test_a14_a15_queue_cross_refs_and_completeness(alpha_world: AlphaWorld) -> None:
    w = alpha_world
    status, body = _get(w.app(), "/api/alpha/discovery/queue")
    assert status == 200
    assert set(body) == {"discovery_registry_head_entry_hash", "queue_sequence_number", "queue",
                         "policy", "universe", "lanes"}
    queue = body["queue"]
    assert queue["alpha_research_queue_snapshot_id"] == w.queue.alpha_research_queue_snapshot_id
    assert queue["policy_id"] == w.policy.alpha_discovery_policy_id == body["policy"]["alpha_discovery_policy_id"]
    assert queue["universe_id"] == w.universe.alpha_universe_snapshot_id == body["universe"]["alpha_universe_snapshot_id"]
    assert queue["prior_only_market_ids"] == ["market:polymarket:omega"]
    assert queue["alpha_registry_head_entry_hash"] == w.alpha_snapshot().head_entry_hash
    assert {k: queue[k] for k in ALPHA_AUTHORITY} == ALPHA_AUTHORITY
    assert "audit_seed" not in body["policy"] and "fixture-seed" not in json.dumps(body)
    assert body["policy"]["queue_capacity"] == w.policy.queue_capacity
    universe = body["universe"]
    assert universe["coverage_scope"] == "BOUNDED_OBSERVED_UNIVERSE"
    assert universe["external_universe_completeness"] == "UNPROVEN"
    assert universe["market_count"] == 6 and universe["as_of"] == w.universe.as_of


def test_a16_lane_accounting(alpha_world: AlphaWorld) -> None:
    w = alpha_world
    lanes = _get(w.app(), "/api/alpha/discovery/queue")[1]["lanes"]
    assert list(lanes) == ["core", "exploration", "audit", "deferred", "skipped_ineligible", "skipped_capacity"]
    for lane, field in research.DISCOVERY_LANES:
        assert [t["market_triage_decision_id"] for t in lanes[lane]] == list(getattr(w.queue, field)), lane
    total = sum(len(items) for items in lanes.values())
    assert total == len(w.queue.all_triage_ids) == 6
    assert [t["market_id"] for t in lanes["skipped_ineligible"]] == ["market:polymarket:gamma"]
    assert [t["market_id"] for t in lanes["deferred"]] == ["market:polymarket:delta"]
    assert lanes["core"] and lanes["audit"]
    summary = lanes["core"][0]
    assert set(summary) == {
        "market_triage_decision_id", "market_id", "event_id", "category", "eligibility",
        "priority_class", "reopen_disposition", "readiness", "reason_codes",
        "material_change_event_id", "newly_observed_locally", "final_disposition", "selected_lane",
        "analysis_temporal_mode", "alpha_memory_temporal_posture", "alpha_registry_head_entry_hash",
        "matched_candidate_ids", "matched_hypothesis_family_ids", "matched_research_episode_ids",
        "coverage",
    }
    assert summary["coverage"][0] == {
        "research_archetype": AD.RESEARCH_ARCHETYPES[0],
        "coverage_state": dict(w.triage[summary["market_id"].split(":")[-1]].coverage)[AD.RESEARCH_ARCHETYPES[0]],
    }
    zeta = next(t for items in lanes.values() for t in items if t["market_id"] == "market:polymarket:zeta")
    assert zeta["newly_observed_locally"] is True


def test_a17_a18_triage_market_and_material_change(alpha_world: AlphaWorld) -> None:
    w = alpha_world
    triage = w.triage["alpha"]
    status, body = _get(w.app(), f"/api/alpha/discovery/triage/{triage.market_triage_decision_id}")
    assert status == 200
    assert set(body) == {"triage", "universe_market", "material_change", "alpha_memory_resolution"}
    detail = body["triage"]
    assert detail["market_triage_decision_id"] == triage.market_triage_decision_id
    assert detail["universe_id"] == w.universe.alpha_universe_snapshot_id
    assert detail["final_disposition"] == triage.final_disposition
    assert detail["historical_replay_valid_for_alpha_memory"] is False
    assert {k: detail[k] for k in ALPHA_AUTHORITY} == ALPHA_AUTHORITY
    market = body["universe_market"]
    assert market["market_id"] == "market:polymarket:alpha"
    assert market["token_ids"] == ["token:polymarket:alpha"]
    assert market["order_book_count"] == 1 and market["resolution_rule_count"] == 0
    assert "books" not in market and "rules" not in market
    change = body["material_change"]
    assert change["material_change_event_id"] == w.change.material_change_event_id == triage.material_change_event_id
    assert change["hard_change_classes"] == ["MARKET_STATUS_CHANGED"] and change["reopen_material"] is True
    assert change["affected_token_ids"] == []
    assert {k: change[k] for k in ALPHA_AUTHORITY} == ALPHA_AUTHORITY
    beta = _get(w.app(), f"/api/alpha/discovery/triage/{w.triage['beta'].market_triage_decision_id}")[1]
    assert beta["material_change"] is None
    delta = _get(w.app(), f"/api/alpha/discovery/triage/{w.triage['delta'].market_triage_decision_id}")[1]
    assert [r["request_type"] for r in delta["triage"]["capture_requests"]] == ["MARKET_METADATA_REFRESH"]


def test_a19_matched_ids_only(alpha_world: AlphaWorld) -> None:
    w = alpha_world
    triage = w.triage["alpha"]
    assert triage.matched_candidate_ids == (w.candidates["a"].candidate_id,)
    resolution = _get(w.app(), f"/api/alpha/discovery/triage/{triage.market_triage_decision_id}")[1][
        "alpha_memory_resolution"]
    assert resolution["status"] == "RESOLVED"
    assert [c["candidate_id"] for c in resolution["candidates"]] == list(triage.matched_candidate_ids)
    assert [f["hypothesis_family_id"] for f in resolution["hypothesis_families"]] == list(
        triage.matched_hypothesis_family_ids)
    assert [e["research_episode_id"] for e in resolution["research_episodes"]] == list(
        triage.matched_research_episode_ids)
    serialized = json.dumps(resolution)
    assert w.candidates["b"].candidate_id not in serialized
    assert w.episodes["e6"].research_episode_id not in serialized
    # Markets with no canonical match resolve to an exactly empty set (no textual join).
    zeta = _get(w.app(), f"/api/alpha/discovery/triage/{w.triage['zeta'].market_triage_decision_id}")[1]
    assert zeta["alpha_memory_resolution"]["status"] == "RESOLVED"
    assert zeta["alpha_memory_resolution"]["candidates"] == []


def test_a20_a21_a22_a24_head_binding(tmp_path: Path) -> None:
    w = make_alpha_world(tmp_path, replay=True)
    triage = w.triage["alpha"]
    target = f"/api/alpha/discovery/triage/{triage.market_triage_decision_id}"
    resolution = _get(w.app(), target)[1]["alpha_memory_resolution"]
    assert resolution["status"] == "RESOLVED"
    assert resolution["bound_alpha_registry_head_entry_hash"] == triage.alpha_registry_head_entry_hash
    assert triage.alpha_registry_head_entry_hash == w.alpha_snapshot().head_entry_hash
    # A22: replayed triage has no bound head -> NOT_BOUND, nothing resolved.
    replayed = w.triage["replay-alpha"]
    assert replayed.alpha_registry_head_entry_hash is None
    body = _get(w.app(), f"/api/alpha/discovery/triage/{replayed.market_triage_decision_id}")[1]
    assert body["alpha_memory_resolution"] == {
        "status": "NOT_BOUND", "bound_alpha_registry_head_entry_hash": None,
        "candidates": [], "hypothesis_families": [], "research_episodes": [],
    }
    # A24: matching head but a matched id missing from the snapshot is impossible -> 503.
    real = AFR.load_and_verify_alpha_factory_registry(w.alpha)
    pruned = dataclasses.replace(real.snapshot, entries=tuple(
        e for e in real.snapshot.entries if e.record_id != w.candidates["a"].candidate_id))
    assert pruned.head_entry_hash == triage.alpha_registry_head_entry_hash
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(research, "load_and_verify_alpha_factory_registry",
                      lambda _path: dataclasses.replace(real, snapshot=pruned))
        assert _get(w.app(), target) == UNAVAILABLE
    # A21: a valid later Alpha append moves the head -> HEAD_MISMATCH, nothing resolved.
    later = _candidate("later", ["CROSS_MARKET"])
    assert AFR.append_alpha_factory_records(w.alpha, [later]).is_valid
    resolution = _get(w.app(), target)[1]["alpha_memory_resolution"]
    assert resolution == {
        "status": "HEAD_MISMATCH",
        "bound_alpha_registry_head_entry_hash": triage.alpha_registry_head_entry_hash,
        "candidates": [], "hypothesis_families": [], "research_episodes": [],
    }
    assert w.alpha_snapshot().head_entry_hash != triage.alpha_registry_head_entry_hash
    assert set(research.ALPHA_RESOLUTION_STATUSES) == {"NOT_BOUND", "UNAVAILABLE", "HEAD_MISMATCH", "RESOLVED"}


def test_a23_source_independence(alpha_world: AlphaWorld) -> None:
    w = alpha_world
    triage_target = f"/api/alpha/discovery/triage/{w.triage['alpha'].market_triage_decision_id}"
    garbage = w.alpha.parent / "garbage_alpha.sqlite3"
    garbage.write_bytes(b"\x00not an alpha registry" * 64)
    for app in (w.app(alpha=False), w.app(alpha_path=garbage)):
        for target in _alpha_targets(w)[:4]:
            assert _get(app, target) == UNAVAILABLE, target
        assert _get(app, "/api/alpha/discovery/queue")[0] == 200
        status, body = _get(app, triage_target)
        assert status == 200
        resolution = body["alpha_memory_resolution"]
        assert resolution["status"] == "UNAVAILABLE"
        assert resolution["candidates"] == [] and resolution["research_episodes"] == []
        # Canonical matched ids stay visible on the triage record itself.
        assert body["triage"]["matched_candidate_ids"] == [w.candidates["a"].candidate_id]
    app = w.app(discovery=False)
    for target in _alpha_targets(w)[:4]:
        assert _get(app, target)[0] == 200, target
    for target in _alpha_targets(w)[4:]:
        assert _get(app, target) == UNAVAILABLE, target


def test_a25_a26_a27_identifier_and_source_errors(alpha_world: AlphaWorld) -> None:
    w = alpha_world
    app = w.app()
    bad_ids = {
        "/api/alpha/candidates/": ("not-an-id", "alphacandidate:sha256:" + "A" * 64,
                                   "alphacandidate:sha256:" + "a" * 63, "alphaepisode:sha256:" + "a" * 64),
        "/api/alpha/episodes/": ("not-an-id", "alphaepisode:sha256:" + "g" * 64,
                                 "alphacandidate:sha256:" + "a" * 64),
        "/api/alpha/discovery/triage/": ("not-an-id", "alphatriage:sha256:" + "a" * 65,
                                         "alphaqueue:sha256:" + "a" * 64),
    }
    unconfigured = cockpit.create_app(cockpit.CockpitConfig(None, None))
    for prefix, values in bad_ids.items():
        for bad in values:
            for target_app in (app, unconfigured):
                status, body = _get(target_app, prefix + bad)
                assert (status, body) == INVALID and bad not in json.dumps(body), (prefix, bad)
    assert _get(app, "/api/alpha/candidates/alphacandidate:sha256:" + "f" * 64) == NOT_FOUND
    assert _get(app, "/api/alpha/episodes/alphaepisode:sha256:" + "f" * 64) == NOT_FOUND
    assert _get(app, "/api/alpha/discovery/triage/alphatriage:sha256:" + "f" * 64) == NOT_FOUND
    assert _get(unconfigured, "/api/alpha/candidates/alphacandidate:sha256:" + "f" * 64) == UNAVAILABLE
    base = w.alpha.parent
    garbage = base / "garbage.sqlite3"
    garbage.write_bytes(b"\x00garbage" * 128)
    wrong_suffix = base / "alpha_factory.db"
    wrong_suffix.write_bytes(w.alpha.read_bytes())
    tampered = base / "tampered_alpha.sqlite3"
    raw = w.alpha.read_bytes()
    assert raw.count(b"Candidate alpha") >= 1
    tampered.write_bytes(raw.replace(b"Candidate alpha", b"Candidate ALPHA"))
    assert not AFR.load_and_verify_alpha_factory_registry(tampered).is_valid
    tampered_discovery = base / "tampered_discovery.sqlite3"
    draw = w.discovery.read_bytes()
    assert draw.count(b"market:polymarket:alpha") >= 1
    tampered_discovery.write_bytes(draw.replace(b"market:polymarket:alpha", b"market:polymarket:alphA"))
    assert not ADR.load_and_verify_alpha_discovery_registry(tampered_discovery).is_valid
    for candidate in (base / "missing.sqlite3", garbage, wrong_suffix, tampered, w.discovery):
        bad = w.app(alpha_path=candidate)
        for target in _alpha_targets(w)[:4]:
            assert _get(bad, target) == UNAVAILABLE, (candidate.name, target)
    for candidate in (base / "missing.sqlite3", garbage, tampered_discovery, w.alpha):
        bad = w.app(discovery_path=candidate)
        for target in _alpha_targets(w)[4:]:
            assert _get(bad, target) == UNAVAILABLE, (candidate.name, target)
    unconfigured_bodies = [_get(unconfigured, target) for target in _alpha_targets(w)]
    assert all(result == UNAVAILABLE for result in unconfigured_bodies)


def test_a28_store_bytes_unchanged(tmp_path: Path) -> None:
    w = make_alpha_world(tmp_path, replay=True)
    before = {path: _digest(path) for path in (w.alpha, w.discovery)}
    listing = sorted(p.name for p in w.alpha.parent.iterdir())
    app = w.app()
    targets = list(_alpha_targets(w)) + [
        f"/api/alpha/candidates/{w.candidates['b'].candidate_id}",
        f"/api/alpha/episodes/{w.episodes['e4'].research_episode_id}",
        f"/api/alpha/discovery/triage/{w.triage['replay-beta'].market_triage_decision_id}",
    ]
    for target in targets:
        assert _get(app, target)[0] == 200, target
    assert {path: _digest(path) for path in (w.alpha, w.discovery)} == before
    assert sorted(p.name for p in w.alpha.parent.iterdir()) == listing == [
        "alpha_discovery.sqlite3", "alpha_factory.sqlite3",
    ]


def test_a29_a30_alpha_routes_get_only_total_24(alpha_world: AlphaWorld) -> None:
    app = alpha_world.app()
    domain = {route.path: set(route.methods or ()) for route in app.routes if route.path.startswith("/api/")}
    assert len(domain) == 25
    for route in ALPHA_ROUTES:
        assert domain[route] == {"GET"}
    for target in _alpha_targets(alpha_world):
        for method in ("POST", "PUT", "PATCH", "DELETE"):
            assert _method(app, target, method) == 405, (target, method)


def test_a31_cockpit_config_alpha_fields(alpha_world: AlphaWorld, world: World) -> None:
    legacy = cockpit.CockpitConfig(None, None, None, None, world.lifecycle, world.hermes)
    assert legacy.alpha_factory_registry_path is None and legacy.alpha_discovery_registry_path is None
    full = cockpit.CockpitConfig(None, None, None, None, world.lifecycle, world.hermes,
                                 alpha_world.alpha, alpha_world.discovery)
    assert full.alpha_factory_registry_path == alpha_world.alpha
    assert full.alpha_discovery_registry_path == alpha_world.discovery
    with pytest.raises(TypeError):
        cockpit.CockpitConfig(None, None, None, None, None, None, str(alpha_world.alpha))
    app = cockpit.create_app(full)
    assert _get(app, "/api/strategies")[0] == 200 and _get(app, "/api/alpha/memory")[0] == 200
    cockpit_source = (ROOT / "src" / "operator_cockpit.py").read_text(encoding="utf-8")
    for flag in ("--alpha-factory-registry", "--alpha-discovery-registry"):
        assert f'parser.add_argument("{flag}", type=Path)' in cockpit_source
    assert "environ" not in cockpit_source and "getenv" not in cockpit_source


def test_a32_no_strategy_hermes_inference(alpha_world: AlphaWorld, world: World) -> None:
    world.assess(world.root, t=1_000)
    full = cockpit.create_app(cockpit.CockpitConfig(
        None, None, None, None, world.lifecycle, world.hermes, alpha_world.alpha, alpha_world.discovery))
    bodies = [_get(full, target)[1] for target in _alpha_targets(alpha_world)]
    serialized = json.dumps(bodies)
    for banned in ("strategyversion:", "strategyfamily:", "hermesstrategyassessment:", "hermes",
                   "strategy_version_id", "strategy_family_id", "lifecycle"):
        assert banned not in serialized.lower(), banned
    strategies = json.dumps(_get(full, "/api/strategies")[1])
    assert "alpha" not in strategies.lower()
    source = MODULE.read_text(encoding="utf-8")
    alpha_part = source[source.index("# S10-CC-RESEARCH-02: Alpha Factory research memory"):]
    for token in ("lifecycle", "Lifecycle", "hermes", "Hermes", "strategy_version", "StrategyVersion"):
        assert token not in alpha_part, token


def test_a33_no_qualification_af1_synthesis() -> None:
    source = MODULE.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported = [
        node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)
    ] + [alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names]
    for name in imported:
        for forbidden in ("qualification", "alpha_factory_gate", "experiment", "gate_evidence"):
            assert forbidden not in name, name
    for token in ("QualificationCandidate", "QualificationGateReceipt", "AF1GateReceipt",
                  "af1_gate_evidence", "S10-GATE-AF1", "PreregisteredExperiment", "QUAL_PASS"):
        assert token not in source, token
    cockpit_source = (ROOT / "src" / "operator_cockpit.py").read_text(encoding="utf-8")
    code = " ".join(line.split("#")[0] for line in cockpit_source.splitlines()).lower()
    assert "qualification" not in code and "af1" not in code


def test_a34_alpha_dto_sanitization(alpha_world: AlphaWorld) -> None:
    w = alpha_world
    app = w.app()
    bodies = [_get(app, target)[1] for target in _alpha_targets(w)]
    serialized = json.dumps(bodies)
    for banned in (str(w.alpha), str(w.discovery), str(w.alpha.parent), "sqlite", "Traceback",
                   "Exception", "REGISTRY_INTEGRITY", "REGISTRY_SCHEMA", "REGISTRY_REJECTED", "REFERENCE_INVALID", "INTERNAL_VALIDATION_FAILED",
                   "audit_seed", "fixture-seed", "private_key", "api_key", "passphrase", "mnemonic",
                   "pre_allocation_basis", "core_eligible"):
        assert banned not in serialized, banned
    tampered = w.alpha.parent / "broken.sqlite3"
    tampered.write_bytes(b"broken" * 64)
    errors = [_get(w.app(alpha_path=tampered, discovery_path=tampered), target)[1]
              for target in _alpha_targets(w)]
    assert errors == [{"error": {"code": "SOURCE_UNAVAILABLE"}}] * len(errors)


def test_a35_to_a39_frontend_alpha_surface() -> None:
    app_source = (FRONTEND / "app.tsx").read_text(encoding="utf-8")
    api_source = (FRONTEND / "api.ts").read_text(encoding="utf-8")
    stories = (FRONTEND / "foundation.stories.tsx").read_text(encoding="utf-8")
    # A35: /alpha is the only new primary route, in the frozen navigation order.
    paths = re.findall(r'\{ path: "(/[a-z]+)"', app_source)
    assert paths == ["/overview", "/markets", "/experiments", "/strategies", "/hermes", "/alpha", "/ops", "/paper", "/audit"]
    # A36: alpha query family and exactly the six alpha key families.
    assert re.search(r'export type QueryFamily =[^;]*"alpha"', api_source)
    for key in ('["cc", "alpha", "memory"]', '["cc", "alpha", "candidates", "list"]',
                '["cc", "alpha", "candidates", "detail", candidateId]',
                '["cc", "alpha", "episodes", "detail", researchEpisodeId]',
                '["cc", "alpha", "discovery", "queue"]',
                '["cc", "alpha", "discovery", "triage", marketTriageDecisionId]'):
        assert key in api_source, key
    assert len(re.findall(r'\["cc", "alpha"', api_source)) == 6
    # A37: no polling, realtime, mutation or automatic source fetch.
    combined = app_source + api_source
    for banned in ("setInterval", "refetchInterval", "EventSource", "WebSocket", "useMutation",
                   "localStorage", "zustand", "error.message", "<iframe", "href={source"):
        assert banned not in combined, banned
    assert not re.search(r"\b(POST|PUT|PATCH|DELETE)\b", combined)
    for label in (">Run<", ">Approve<", ">Qualify<", ">Promote<", ">Trade<", ">Reopen<", ">Allocate<"):
        assert label not in app_source, label
    # A38: Storybook intercepts every /api/alpha surface.
    for intercepted in ("/api/alpha/memory", "/api/alpha/candidates", "/api/alpha/candidates/:candidateId",
                        "/api/alpha/episodes/:researchEpisodeId", "/api/alpha/discovery/queue",
                        "/api/alpha/discovery/triage/:marketTriageDecisionId", "/api/alpha/*"):
        assert intercepted in stories, intercepted
    # A39: required non-authority wording.
    for wording in (
        "Alpha Factory records research history.",
        "RESEARCH_SUPPORTIVE is not qualification, executable edge, profitability or trading authority.",
        "Discovery priority is research allocation only.",
        "It is not strategy selection or trade priority.",
        "latest recorded discovery queue",
        "research leaf",
    ):
        assert wording in app_source, wording
    for banned in ("live queue", "current market queue", "real-time", "up to date now"):
        assert banned not in app_source.lower(), banned
