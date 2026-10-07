"""S10-CC-OPS-01 focused tests: read-only Control Center portfolio-operations projection.

Every lifecycle fixture is a real verified StrategyLifecycle store built through the public
lifecycle API (shared with the S10-CC-RESEARCH-01 fixtures); capacity rejections, health,
restrictions, windows and the no-active-policy state come only from valid canonical appends.
Paper and gateway fixtures are the existing cockpit helpers; their backend DTOs are unchanged.
"""

from __future__ import annotations

import ast
import asyncio
import hashlib
import json
from pathlib import Path
import re

import pytest

import src.operator_cockpit as cockpit
import src.operator_cockpit_ops as ops
from src.strategy_lifecycle import (
    RISK_BANDS,
    StrategyLifecycleSnapshot,
    append_strategy_lifecycle_record,
    build_portfolio_policy_receipt,
    build_strategy_risk_allocation,
    build_strategy_restriction_receipt,
    evaluate_portfolio_capacity,
    initialize_strategy_lifecycle_store,
    load_strategy_lifecycle_store,
)
from tests.test_operator_cockpit import _asgi_call, _gateway_store, _get, _paper_store
from tests.test_operator_cockpit_research import LIMITS, World, _health, _restriction, make_world


ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "src" / "operator_cockpit_ops.py"
COCKPIT = ROOT / "src" / "operator_cockpit.py"
FRONTEND = ROOT / "src" / "operator_cockpit_frontend" / "src"
ROUTE = "/api/ops/portfolio"
EVALUATED_AT = 1_000
UNAVAILABLE = (503, {"error": {"code": "SOURCE_UNAVAILABLE"}})
INVALID = (400, {"error": {"code": "INVALID_INPUT"}})
TOP_LEVEL_KEYS = {
    "read_only", "evaluated_at_ns", "lifecycle_store_head_entry_hash", "active_policy",
    "capacity", "strategy_reservations", "non_authority",
}
POLICY_KEYS = {
    "policy_id", "predecessor_policy_id", "policy_label", "venue_scope", "account_scope_ref",
    "effective_from_ns", "expires_at_ns", "limits", "allowed_order_styles", "created_time_ns",
}
CAPACITY_KEYS = {
    "status", "reason_codes", "evaluated_at_ns", "policy_id", "reserved_budget_usd",
    "active_real_risk_strategy_count",
}
RESERVATION_KEYS = {
    "allocation_id", "strategy_version_id", "strategy_label", "policy_id", "risk_band",
    "active_budget_usd", "allocation_basis", "valid_from_ns", "valid_until_ns",
    "active_at_evaluation", "health_state", "capacity_status", "capacity_reason_codes",
    "active_restrictions",
}
RESTRICTION_KEYS = {
    "restriction_receipt_id", "restriction_key", "restriction_kind", "max_active_budget_usd",
    "created_time_ns",
}
NON_AUTHORITY = {
    "budget_reservation_only": True,
    "actual_account_exposure_not_measured": True,
    "orders_not_measured": True,
    "fills_not_measured": True,
    "pnl_not_measured": True,
    "gate_c_not_implied": True,
    "execution_not_implied": True,
    "live_not_implied": True,
}
OPS_KEYS = (
    '["cc", "ops", "portfolio"]',
    '["cc", "ops", "gateway", "status"]',
    '["cc", "ops", "gateway", "audit"]',
    '["cc", "ops", "paper", "summary"]',
    '["cc", "ops", "paper", "risk"]',
)
PROMOTION_PATTERNS = (
    r"trade[-_ ]ready", r"execution[-_ ]ready", r"live[-_ ]ready", r"network[-_ ]eligible",
    r"host[-_ ]current", r"actual[-_ ]live[-_ ]exposure", r"EXECUTION_HOST_CURRENT",
    r"EXECUTION_NETWORK_ELIGIBLE", r"gate[-_ ]?c[-_ ](pass|eligible)", r"live[-_ ]eligible",
    r"incident", r"real[-_ ]?time",
)


def _app(world: World | None = None, *, lifecycle: Path | None = None, paper=None, gateway=None):
    path = lifecycle if lifecycle is not None else (world.lifecycle if world else None)
    return cockpit.create_app(cockpit.CockpitConfig(None, None, paper, gateway, path))


@pytest.fixture
def world(tmp_path: Path) -> World:
    return make_world(tmp_path)


@pytest.fixture
def fixed_clock(monkeypatch: pytest.MonkeyPatch) -> list[int]:
    """One deterministic backend time per request; records every read of the clock."""
    reads: list[int] = []

    def time_ns() -> int:
        reads.append(EVALUATED_AT)
        return EVALUATED_AT

    monkeypatch.setattr(cockpit.time, "time_ns", time_ns)
    return reads


def _portfolio(app) -> dict:
    status, body = _get(app, ROUTE)
    assert status == 200, body
    return body


def _snapshot(path: Path) -> StrategyLifecycleSnapshot:
    result = load_strategy_lifecycle_store(path)
    assert result.is_valid
    return result.snapshot


def _append(world: World, record) -> None:
    result = append_strategy_lifecycle_record(world.lifecycle, record)
    assert result.is_valid, result.error_codes


def _allocation(world: World, version, *, band="EXPLORATORY_LIVE", budget="40", start=100,
                until=None, created=110, ref="decision:unit-2"):
    return build_strategy_risk_allocation(
        strategy_version_id=version.strategy_version_id, policy_id=world.policy.policy_id,
        risk_band=band, active_budget_usd=budget, allocation_basis="DIRECT_DECISION",
        decision_ref=ref, valid_from_ns=start, valid_until_ns=until, created_time_ns=created,
    )


def _windowed_world(world: World) -> World:
    """Root active now, child starts in the future, other expired before evaluation."""
    _append(world, _allocation(world, world.child, start=10_000, created=110))
    _append(world, _allocation(world, world.other, band="VALIDATED_LIVE", budget="30",
                               start=100, until=500, created=120, ref="decision:unit-3"))
    return world


def _revoked_world(world: World) -> World:
    _append(world, build_portfolio_policy_receipt(
        action="REVOKE", policy_id=world.policy.policy_id,
        previous_active_policy_id=world.policy.policy_id,
        human_authorization_ref="human:karl-revoke-1", created_time_ns=200,
    ))
    return world


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _method(app, target: str, method: str) -> int:
    return asyncio.run(_asgi_call(app, target, method=method))[0]


def _imports(source: str) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            names |= {alias.name for alias in node.names}
        elif isinstance(node, ast.ImportFrom):
            names.add(node.module or "")
            names |= {alias.name for alias in node.names}
    return names


def _module_code() -> str:
    """The projection module source without its module docstring (code + comments only)."""
    source = MODULE.read_text(encoding="utf-8")
    return source.split('"""', 2)[2]


def _ops_frontend_section() -> str:
    source = (FRONTEND / "app.tsx").read_text(encoding="utf-8")
    start = source.index("S10-CC-OPS-01 operations view")
    end = source.index("// Shell and routes")
    return source[start:end]


def _ops_stories_section() -> str:
    source = (FRONTEND / "foundation.stories.tsx").read_text(encoding="utf-8")
    return source[source.index("S10-CC-OPS-01 operations states"):]


# ---------------------------------------------------------------------------
# O01-O13 backend projection
# ---------------------------------------------------------------------------


def test_o01_verified_lifecycle_loader_only(world, fixed_clock, monkeypatch) -> None:
    calls: list[Path] = []
    real = ops.load_strategy_lifecycle_store

    def spy(path):
        calls.append(path)
        return real(path)

    monkeypatch.setattr(ops, "load_strategy_lifecycle_store", spy)
    assert _portfolio(_app(world))["read_only"] is True
    assert calls == [world.lifecycle]
    source = _module_code()
    for forbidden in ("sqlite3", ".connect(", "open(", "StrategyLifecycleSnapshot(",
                      "record_from_mapping", "from_mapping", "_replay", "store_head_entry_hash ="):
        assert forbidden not in source, forbidden


def test_o02_canonical_capacity_evaluator_once(world, fixed_clock, monkeypatch) -> None:
    calls: list[tuple[object, int]] = []
    real = ops.evaluate_portfolio_capacity

    def spy(snapshot, at_time_ns):
        calls.append((snapshot, at_time_ns))
        return real(snapshot, at_time_ns)

    monkeypatch.setattr(ops, "evaluate_portfolio_capacity", spy)
    body = _portfolio(_app(world))
    assert len(calls) == 1
    snapshot, at_time_ns = calls[0]
    assert isinstance(snapshot, StrategyLifecycleSnapshot)
    assert snapshot.store_head_entry_hash == body["lifecycle_store_head_entry_hash"]
    assert at_time_ns == EVALUATED_AT
    canonical = real(_snapshot(world.lifecycle), EVALUATED_AT)
    assert body["capacity"]["reserved_budget_usd"] == {
        "exploratory": canonical.exploratory_active_usd,
        "validated": canonical.validated_active_usd,
        "mature": canonical.mature_active_usd,
        "total": canonical.total_active_usd,
    }
    source = MODULE.read_text(encoding="utf-8")
    called = [
        node for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Call) and getattr(node.func, "id", "") == "evaluate_portfolio_capacity"
    ]
    assert len(called) == 1
    code = _module_code()
    for arithmetic in ("Decimal", "money(", "sum(", ".pool_max(", ".per_strategy_max(", " + ", " - "):
        assert arithmetic not in code, arithmetic


def test_o03_one_request_time(world, fixed_clock, monkeypatch) -> None:
    _windowed_world(world)
    seen: list[int] = []
    real = ops.evaluate_portfolio_capacity
    monkeypatch.setattr(
        ops, "evaluate_portfolio_capacity",
        lambda snapshot, at: (seen.append(at), real(snapshot, at))[1],
    )
    body = _portfolio(_app(world))
    assert fixed_clock == [EVALUATED_AT]
    assert seen == [EVALUATED_AT]
    assert body["evaluated_at_ns"] == body["capacity"]["evaluated_at_ns"] == EVALUATED_AT
    snapshot = _snapshot(world.lifecycle)
    for item in body["strategy_reservations"]:
        allocation = snapshot.allocation_of(item["strategy_version_id"])
        assert item["active_at_evaluation"] is allocation.is_active_at(EVALUATED_AT)
    cockpit_source = COCKPIT.read_text(encoding="utf-8")
    route = cockpit_source[cockpit_source.index('@app.get("/api/ops/portfolio")'):]
    route = route[: route.index("return app")]
    assert route.count("time.time_ns()") == 1
    assert route.index("INVALID_INPUT") < route.index("time.time_ns()")
    assert "ops.portfolio_projection(config.strategy_lifecycle_path, evaluated_at_ns)" in route
    # The browser clock never drives capacity semantics.
    section = _ops_frontend_section()
    for browser_clock in ("Date.now", "new Date(", "performance.now"):
        assert browser_clock not in section, browser_clock


def test_o04_active_policy_field_coverage(world, fixed_clock) -> None:
    body = _portfolio(_app(world))
    assert set(body) == TOP_LEVEL_KEYS
    policy = body["active_policy"]
    assert set(policy) == POLICY_KEYS
    assert set(policy["limits"]) == set(LIMITS) == set(ops.POLICY_LIMIT_FIELDS)
    assert len(policy["limits"]) == 17
    assert policy["limits"] == LIMITS
    expected = world.policy
    assert policy["policy_id"] == expected.policy_id
    assert policy["predecessor_policy_id"] is None
    assert policy["policy_label"] == expected.policy_label
    assert policy["venue_scope"] == list(expected.venue_scope)
    assert policy["account_scope_ref"] == expected.account_scope_ref
    assert policy["effective_from_ns"] == expected.effective_from_ns
    assert policy["expires_at_ns"] is None
    assert policy["allowed_order_styles"] == list(expected.allowed_order_styles)
    assert policy["created_time_ns"] == expected.created_time_ns
    for name in ops.POLICY_LIMIT_FIELDS:
        assert policy["limits"][name] == getattr(expected, name)
    assert set(body["capacity"]) == CAPACITY_KEYS
    assert body["capacity"]["policy_id"] == expected.policy_id
    assert body["non_authority"] == NON_AUTHORITY
    for name in policy["limits"]:
        assert not re.search(r"(?i)exposure_usd$|balance|utiliz", name.replace("gross_exposure_max", ""))


def test_o05_no_active_policy_valid_state(world, fixed_clock, tmp_path) -> None:
    body = _portfolio(_app(_revoked_world(world)))
    assert body["active_policy"] is None
    canonical = evaluate_portfolio_capacity(_snapshot(world.lifecycle), EVALUATED_AT)
    assert body["capacity"] == {
        "status": "PORTFOLIO_CAPACITY_REJECTED",
        "reason_codes": ["POLICY_NOT_ACTIVE"],
        "evaluated_at_ns": EVALUATED_AT,
        "policy_id": None,
        "reserved_budget_usd": {"exploratory": "0", "validated": "0", "mature": "0", "total": "0"},
        "active_real_risk_strategy_count": 0,
    }
    assert canonical.reason_codes == ("POLICY_NOT_ACTIVE",) and canonical.strategy_results == ()
    (reservation,) = body["strategy_reservations"]
    assert reservation["capacity_status"] is None and reservation["capacity_reason_codes"] == []
    # An empty valid store is also a 200 domain state, never SOURCE_UNAVAILABLE.
    empty = tmp_path / "empty" / "lifecycle.sqlite3"
    empty.parent.mkdir()
    assert initialize_strategy_lifecycle_store(empty).is_valid
    empty_body = _portfolio(_app(lifecycle=empty))
    assert empty_body["active_policy"] is None
    assert empty_body["capacity"]["reason_codes"] == ["POLICY_NOT_ACTIVE"]
    assert empty_body["strategy_reservations"] == []
    assert empty_body["lifecycle_store_head_entry_hash"] is None


def test_o06_to_o08_reservations_and_canonical_reasons(world, fixed_clock) -> None:
    _append(world, _health(world.root, "NEW", "WATCH", t=140))
    _append(world, build_strategy_restriction_receipt(
        strategy_version_id=world.root.strategy_version_id, restriction_key="cap.1",
        action="APPLY", restriction_kind="ACTIVE_BUDGET_CAP", max_active_budget_usd="75",
        decision_ref="decision:cap-1", created_time_ns=150,
    ))
    body = _portfolio(_app(world))
    (item,) = body["strategy_reservations"]
    assert set(item) == RESERVATION_KEYS
    allocation = world.allocation
    assert item == {
        "allocation_id": allocation.allocation_id,
        "strategy_version_id": world.root.strategy_version_id,
        "strategy_label": world.root.strategy_label,
        "policy_id": world.policy.policy_id,
        "risk_band": "EXPLORATORY_LIVE",
        "active_budget_usd": "50",
        "allocation_basis": "DIRECT_DECISION",
        "valid_from_ns": 100,
        "valid_until_ns": None,
        "active_at_evaluation": True,
        "health_state": "WATCH",
        "capacity_status": "PORTFOLIO_CAPACITY_VALID",
        "capacity_reason_codes": [],
        "active_restrictions": [item["active_restrictions"][0]],
    }
    (restriction,) = item["active_restrictions"]
    assert set(restriction) == RESTRICTION_KEYS
    assert restriction["restriction_key"] == "cap.1"
    assert restriction["restriction_kind"] == "ACTIVE_BUDGET_CAP"
    assert restriction["max_active_budget_usd"] == "75"
    assert restriction["created_time_ns"] == 150


def test_o07_windows_truthful_and_ordered(world, fixed_clock) -> None:
    body = _portfolio(_app(_windowed_world(world)))
    items = body["strategy_reservations"]
    labels = [(item["strategy_label"], item["active_at_evaluation"]) for item in items]
    # Active before inactive; then canonical risk-band order, label, version id.
    assert labels == [("root", True), ("child", False), ("other", False)]
    assert RISK_BANDS.index("EXPLORATORY_LIVE") < RISK_BANDS.index("VALIDATED_LIVE")
    future, expired = items[1], items[2]
    assert future["valid_from_ns"] == 10_000 and future["valid_until_ns"] is None
    assert expired["valid_until_ns"] == 500
    canonical = evaluate_portfolio_capacity(_snapshot(world.lifecycle), EVALUATED_AT)
    for item in items:
        result = canonical.strategy_result(item["strategy_version_id"])
        assert item["capacity_status"] == result.status
        assert item["capacity_reason_codes"] == list(result.reason_codes)
    assert body["capacity"]["reserved_budget_usd"]["total"] == "50"
    serialized = json.dumps(body)
    for promoted in ("eligible", "eligibility", "ready", "approved", "permit"):
        assert promoted not in serialized.lower(), promoted


def test_o08_o09_canonical_rejection_reasons_are_http_200(world, fixed_clock) -> None:
    _append(world, _health(world.root, "NEW", "QUARANTINED", t=140))
    _append(world, _restriction(world.root, key="pause.1", t=150))
    status, body = _get(_app(world), ROUTE)
    assert status == 200
    canonical = evaluate_portfolio_capacity(_snapshot(world.lifecycle), EVALUATED_AT)
    assert body["capacity"]["status"] == canonical.status == "PORTFOLIO_CAPACITY_REJECTED"
    assert body["capacity"]["reason_codes"] == list(canonical.reason_codes) == [
        "HEALTH_BLOCKS_ACTIVE_RISK", "RESTRICTION_BLOCKS_ACTIVE_RISK",
    ]
    (item,) = body["strategy_reservations"]
    assert item["health_state"] == "QUARANTINED"
    assert item["capacity_status"] == "PORTFOLIO_CAPACITY_REJECTED"
    assert item["capacity_reason_codes"] == ["HEALTH_BLOCKS_ACTIVE_RISK", "RESTRICTION_BLOCKS_ACTIVE_RISK"]
    assert [r["restriction_kind"] for r in item["active_restrictions"]] == ["PAUSE_NEW_EXPOSURE"]


def test_o09_to_o11_closed_errors_and_unchanged_bytes(world, fixed_clock, tmp_path, monkeypatch) -> None:
    assert _get(_app(None), ROUTE) == UNAVAILABLE
    missing = tmp_path / "missing" / "lifecycle.sqlite3"
    garbage = tmp_path / "garbage.sqlite3"
    garbage.write_bytes(b"not a sqlite database " + str(tmp_path).encode("utf-8"))
    tampered = tmp_path / "tampered.sqlite3"
    raw = world.lifecycle.read_bytes()
    label = world.policy.policy_label.encode("utf-8")
    assert label in raw
    tampered.write_bytes(raw.replace(label, b"Tampered label!"[: len(label)].ljust(len(label), b"!")))
    wrong_schema = world.hermes  # a different verified store family
    for path in (missing, garbage, tampered, wrong_schema, tmp_path):
        status, body = _get(_app(lifecycle=path), ROUTE)
        assert (status, body) == UNAVAILABLE, path
        assert str(tmp_path) not in json.dumps(body)

    def exploding_loader(_path):
        raise RuntimeError(f"secret detail {tmp_path}")

    monkeypatch.setattr(ops, "load_strategy_lifecycle_store", exploding_loader)
    assert _get(_app(world), ROUTE) == UNAVAILABLE
    monkeypatch.undo()
    monkeypatch.setattr(cockpit.time, "time_ns", lambda: EVALUATED_AT)

    def exploding_evaluator(_snapshot, _at):
        raise ValueError("raw store value")

    monkeypatch.setattr(ops, "evaluate_portfolio_capacity", exploding_evaluator)
    assert _get(_app(world), ROUTE) == UNAVAILABLE
    with pytest.raises(ops.OpsProjectionError) as caught:
        ops.portfolio_projection(world.lifecycle, True)
    assert caught.value.code == "SOURCE_UNAVAILABLE" and str(caught.value) == "SOURCE_UNAVAILABLE"
    with pytest.raises(ops.OpsProjectionError):
        ops.portfolio_projection(world.lifecycle, -1)


def test_o11_store_bytes_unchanged(world, fixed_clock) -> None:
    _windowed_world(world)
    before = _digest(world.lifecycle)
    app = _app(world)
    for _ in range(3):
        _portfolio(app)
    assert _get(app, ROUTE + "?limit=1") == INVALID
    assert _digest(world.lifecycle) == before


def test_o12_exact_route_method_query_and_total(world, fixed_clock) -> None:
    app = _app(world)
    domain = {route.path: set(route.methods or ()) for route in app.routes if route.path.startswith("/api/")}
    assert len(domain) == 27
    assert domain[ROUTE] == {"GET"}
    assert [path for path in domain if path.startswith("/api/ops")] == [ROUTE]
    for method in ("POST", "PUT", "PATCH", "DELETE"):
        assert _method(app, ROUTE, method) == 405, method
    for query in ("?limit=1", "?x", "?x=", "?a=1&a=2", "?evaluated_at_ns=1", "?at_time_ns=5"):
        assert _get(app, ROUTE + query) == INVALID, query
    assert fixed_clock == []  # query validation precedes the single clock read
    assert _get(app, ROUTE)[0] == 200


def test_o13_module_boundary() -> None:
    source = MODULE.read_text(encoding="utf-8")
    imported = _imports(source)
    assert {name for name in imported if name.startswith("src.")} == {"src.strategy_lifecycle"}
    modules = {
        node.module if isinstance(node, ast.ImportFrom) else alias.name
        for node in ast.walk(ast.parse(source))
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    assert modules == {"__future__", "pathlib", "typing", "src.strategy_lifecycle"}
    for forbidden in (
        "sqlite3", "paper_trading", "execution_gateway", "exploratory_gate_c",
        "execution_feasibility", "live_orchestration", "deploy", "subprocess", "socket",
        "urllib", "requests", "httpx", "websocket", "threading", "asyncio", "os.environ",
        "append_strategy_lifecycle_record", "initialize_strategy_lifecycle_store",
        "write_text", "write_bytes", "operator_cockpit_research", "time.time_ns", "import time", "datetime",
    ):
        assert forbidden not in _module_code(), forbidden
    calls = {
        node.func.attr if isinstance(node.func, ast.Attribute) else getattr(node.func, "id", "")
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Call)
    }
    assert not calls & {"open", "connect", "run", "Popen", "urlopen", "append", "initialize"}
    cockpit_source = COCKPIT.read_text(encoding="utf-8")
    assert "from src import operator_cockpit_ops as ops" in cockpit_source
    assert not re.search(r"@app\.(post|put|patch|delete|websocket|api_route)\(", cockpit_source)


# ---------------------------------------------------------------------------
# O13-O18 composition, frontend and Storybook
# ---------------------------------------------------------------------------


GATEWAY_STATUS_KEYS = {
    "read_only", "authority_state", "disabled", "disable_reason", "credential_configured",
    "public_signer", "public_funder", "reconciliation_state", "heartbeat_state",
    "user_stream_state", "access_state", "rate_limit_until_ns", "prepared_order_count",
    "mutation_attempt_count", "open_order_count", "gate_b_authorized",
    "restricted_live_available", "restricted_live", "gate_b",
}
GATEWAY_AUDIT_KEYS = {"sequence", "event_id", "event_type", "event_time_ns", "event_hash"}


def test_o13_gateway_composition_boundary(tmp_path) -> None:
    """OPS reads gateway state only through the existing sanitized HTTP projections."""
    app = _app(None, gateway=_gateway_store(tmp_path))
    status_code, status = _get(app, "/api/gateway/status")
    assert status_code == 200 and set(status) == GATEWAY_STATUS_KEYS
    audit_code, audit = _get(app, "/api/gateway/audit")
    assert audit_code == 200 and audit["items"]
    assert all(set(item) == GATEWAY_AUDIT_KEYS for item in audit["items"])
    assert "execution_gateway" not in _module_code()
    api_source = (FRONTEND / "api.ts").read_text(encoding="utf-8")
    assert api_source.count('"/gateway/status"') == 1 and api_source.count('"/gateway/audit"') == 1
    section = _ops_frontend_section()
    for field in ("authority_state", "access_state", "reconciliation_state", "heartbeat_state",
                  "restricted_live", "event_hash"):
        assert field in section, field
    # Recorded gateway values are labelled recorded and never fed into portfolio state.
    assert "Recorded gateway access state" in section
    assert not re.search(r"capacity[^\n]*access_state|access_state[^\n]*capacity", section)


def test_o13_paper_composition_boundary(tmp_path) -> None:
    """OPS reads simulated paper state only through the existing summary/risk projections."""
    app = _app(None, paper=_paper_store(tmp_path))
    summary_code, summary = _get(app, "/api/paper/summary")
    assert summary_code == 200 and summary["simulated_paper_only"] is True
    risk_code, risk = _get(app, "/api/paper/risk")
    assert risk_code == 200 and set(risk) == {
        "limits", "utilization", "latest_decision", "deny_count", "resolution_pending",
    }
    assert "paper_trading" not in _module_code()
    section = _ops_frontend_section()
    assert "SIMULATED PAPER ONLY." in section
    for detail in ("paperOrdersQuery", "paperFillsQuery", "paperPositionsQuery", "/paper/orders",
                   "/paper/fills", "/paper/positions"):
        assert detail not in section, detail


def test_o14_frontend_ops_route_family_and_keys() -> None:
    app_source = (FRONTEND / "app.tsx").read_text(encoding="utf-8")
    api_source = (FRONTEND / "api.ts").read_text(encoding="utf-8")
    paths = re.findall(r'\{ path: "(/[a-z]+)"', app_source)
    assert paths == ["/overview", "/markets", "/experiments", "/strategies", "/hermes", "/alpha",
                     "/ops", "/paper", "/audit"]
    assert '{ path: "/ops", label: "Operations", family: "ops", element: <OpsView /> }' in app_source
    assert re.search(r'export type QueryFamily =[^;]*"ops"', api_source)
    for key in OPS_KEYS:
        assert key in api_source, key
    assert len(re.findall(r'\["cc", "ops"', api_source)) == 5
    ops_queries = api_source[api_source.index("export const opsPortfolioQuery"):
                             api_source.index("export const paperSummaryQuery")]
    for url in ('"/ops/portfolio"', '"/gateway/status"', '"/gateway/audit"', '"/paper/summary"',
                '"/paper/risk"'):
        assert ops_queries.count(url) == 1, url
    assert 'familyKey("paper")' not in ops_queries
    # Conservative Foundation defaults are unchanged.
    for default in ("retry: false", "refetchOnWindowFocus: false", "refetchOnReconnect: false",
                    "staleTime: Infinity"):
        assert default in api_source, default


def test_o15_source_independence(world, fixed_clock, tmp_path) -> None:
    paper = _paper_store(tmp_path)
    gateway = _gateway_store(tmp_path)
    without_lifecycle = _app(None, paper=paper, gateway=gateway)
    assert _get(without_lifecycle, ROUTE) == UNAVAILABLE
    for target in ("/api/paper/summary", "/api/paper/risk", "/api/gateway/status", "/api/gateway/audit"):
        assert _get(without_lifecycle, target)[0] == 200, target
    lifecycle_only = _app(world)
    assert _get(lifecycle_only, ROUTE)[0] == 200
    for target in ("/api/paper/summary", "/api/gateway/status"):
        assert _get(lifecycle_only, target) == UNAVAILABLE, target
    section = _ops_frontend_section()
    for query in ("opsPortfolioQuery", "opsGatewayStatusQuery", "opsGatewayAuditQuery",
                  "opsPaperSummaryQuery", "opsPaperRiskQuery"):
        assert section.count(f"useQuery({query})") == 1, query
    # Each panel renders its own QueryState; no panel waits on another source.
    for panel in ("PortfolioAuthorityPanel", "RecordedGatewayPanel", "SimulatedPaperPanel",
                  "StrategyReservationsPanel", "RecordedGatewayEventsPanel"):
        body = section[section.index(f"function {panel}"):]
        body = body[: body.index("\n}\n")]
        assert "<QueryState" in body, panel
    assert "isLoading" not in section and "isError &&" not in section


def test_o15_to_o18_no_authority_promotion_or_realtime(world, fixed_clock) -> None:
    body = _portfolio(_app(world))
    serialized = json.dumps(body)
    section = _ops_frontend_section()
    for pattern in PROMOTION_PATTERNS:
        assert not re.search(pattern, serialized, re.IGNORECASE), pattern
        assert not re.search(pattern, section, re.IGNORECASE), pattern
    for wording in (
        "Budget reservations — not actual account exposure.",
        "SIMULATED PAPER ONLY.",
        "Recorded gateway state — not a fresh account, host or network check.",
        "Persisted gateway evidence;",
        "not a fresh account, host or network eligibility check.",
        "Recorded gateway access state",
        "Recorded gateway state",
        "Recent Recorded Gateway Events",
        "Recent recorded gateway events",
    ):
        assert wording in section, wording
    # Paper and reservation economics are never combined in one expression.
    assert not re.search(r"reserved_budget_usd[^\n]*(cash|pnl|equity)", section)
    assert not re.search(r"(cash|pnl|equity)[^\n]*reserved_budget_usd", section)
    for alert in ("alert", "Alert", "Incident"):
        assert f">{alert}" not in section


def test_o17_no_mutation_or_realtime_primitives() -> None:
    app_source = (FRONTEND / "app.tsx").read_text(encoding="utf-8")
    api_source = (FRONTEND / "api.ts").read_text(encoding="utf-8")
    combined = app_source + api_source + _ops_stories_section()
    for banned in ("useMutation", "WebSocket", "refetchInterval", "setInterval",
                   "setTimeout", "localStorage", "sendBeacon"):
        assert banned not in combined, banned
    # S10-CC-STREAM-01: OpsView owns no realtime loop; only the centralized shell
    # StreamRefreshController may construct the single browser stream.
    assert "EventSource" not in api_source + _ops_stories_section() + _ops_frontend_section()
    assert app_source.count("new EventSource(") == 1
    controller = app_source[app_source.index("function StreamRefreshController("):]
    controller = controller[: controller.index("\n}\n")]
    assert app_source.count("EventSource") == controller.count("EventSource")
    assert not re.search(r"\b(POST|PUT|PATCH|DELETE)\b", app_source + api_source)
    assert api_source.count('method: "GET"') == 1
    for label in (">Run<", ">Approve<", ">Apply<", ">Allocate<", ">Pause<", ">Arm<", ">Halt<",
                  ">Cancel<", ">Trade<", ">Reconcile<", ">Revoke<"):
        assert label not in app_source, label


def test_o18_storybook_closes_every_ops_request() -> None:
    stories = _ops_stories_section()
    for intercepted in ('"/api/ops/portfolio"', '"/api/ops/*"', '"/api/gateway/status"',
                        '"/api/gateway/audit"', '"/api/gateway/*"', '"/api/paper/summary"',
                        '"/api/paper/risk"', '"/api/paper/*"'):
        assert intercepted in stories, intercepted
    for story in ("OpsAllSourcesAvailable", "OpsNoActivePolicy", "OpsCapacityRejectedRestriction",
                  "OpsGatewayUnavailable", "OpsPaperUnavailable", "OpsRecordedRestrictedLive"):
        assert f"export const {story} = meta.story(" in stories, story
    assert stories.count('args: { path: "/ops" }') == 6
    assert stories.count("opsHandlers.fallback") == 6
    assert not re.search(r"https?://", stories)
    preview = (ROOT / "src" / "operator_cockpit_frontend" / ".storybook" / "preview.ts").read_text(
        encoding="utf-8"
    )
    assert 'http.all("/api/*"' in preview and "print.error()" in preview
