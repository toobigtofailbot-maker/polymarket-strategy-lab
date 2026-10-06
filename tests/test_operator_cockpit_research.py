"""S10-CC-RESEARCH-01 focused tests: read-only StrategyLifecycle + Hermes projection.

Every fixture is a real verified canonical store built through the public lifecycle and
Hermes strategy-manager APIs with a deterministic fake Hermes backend (no provider, model
or network). Stale context is produced only by valid canonical lifecycle transitions.
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
    assert len(domain) == 18
    for route in RESEARCH_ROUTES:
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


def test_r16_no_alpha_import_or_mapping(world: World) -> None:
    source = MODULE.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported |= {alias.name for alias in node.names}
        elif isinstance(node, ast.ImportFrom):
            imported.add(node.module or "")
            imported |= {alias.name for alias in node.names}
    assert {name for name in imported if name.startswith("src.")} == {
        "src.research_runtime.hermes_controlled_runtime.strategy_manager",
        "src.strategy_lifecycle",
        "src.strategy_lifecycle.models",
    }
    for forbidden in (
        "sqlite3", "requests", "httpx", "urllib", "socket", "websocket", "paper_trading",
        "execution_gateway", "execution_feasibility", "exploratory_gate_c", "alpha_factory",
        "alpha_discovery", "qualification", "run_controlled_hermes_research",
        "run_hermes_strategy_assessment", "append_strategy_lifecycle_record",
        "initialize_strategy_lifecycle_store", "initialize_hermes_strategy_manager_store",
        "OpportunityCandidate", "HypothesisFamily", "ResearchEpisode", "write_text",
        "write_bytes", "threading", "asyncio", "setInterval",
    ):
        assert forbidden not in source, forbidden
    assert re.search(r"(?i)\balpha\b", re.sub(r'""".*?"""', "", source, flags=re.S)) is None
    cockpit_source = (ROOT / "src" / "operator_cockpit.py").read_text(encoding="utf-8")
    assert "alpha" not in cockpit_source.lower()
    for route in RESEARCH_ROUTES:
        assert f'@app.get("{route}")' in cockpit_source
    assert not re.search(r"@app\.(post|put|patch|delete|websocket|api_route)\(", cockpit_source)


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
    assert not re.search(r"(POST|PUT|PATCH|DELETE)", combined)
    for label in (">Run<", ">Reassess<", ">Approve<", ">Apply<", ">Allocate<", ">Pause<",
                  ">Scale<", ">Trade<"):
        assert label not in app_source, label
    assert "soft research judgments" in app_source
    assert "not actual exposure" in app_source
    for intercepted in ("/api/strategies", "/api/hermes/assessments"):
        assert intercepted in stories
