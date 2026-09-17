"""WP171 read-only operator cockpit contract, API, and negative-matrix tests."""

from __future__ import annotations

import asyncio
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import tomllib
from urllib.parse import urlsplit

import pytest

import src.data_layer.analytical_research as ar
from src.data_layer.polymarket import market_truth as mt
from src.data_layer.polymarket.market_truth_store import MarketTruthStore
from src.execution_gateway import ProtectedExecutionGateway
import src.operator_cockpit as cockpit
from src.paper_trading import (
    PaperEngine,
    PaperMarketEvent,
    PaperRiskLimits,
    PaperStore,
    build_paper_intent,
    build_strategy_binding,
)
from src.paper_trading.models import canonical_json_bytes
from src.research_runtime.executable_edge import (
    MarketTruthEvent,
    MarketTruthWindow,
    ResearchDecisionEvent,
    assess_executable_edge,
    build_execution_cost_model,
    build_research_decision_trace,
    identify_market_truth_window,
)
from src.data_layer.analytical_research import experiment_os as os_contract
from tests.data_layer.analytical_research.test_experiment_os_lifecycle_evidence import (
    evidence_input,
    lifecycle,
)
from tests.data_layer.analytical_research.test_experiment_registry import stack
from tests.data_layer.polymarket.test_market_truth_models_store import _book_raw
from tests.data_layer.analytical_research.test_experiment_os_preregistration import (
    experiment_stack,
)


ROOT = Path(__file__).resolve().parents[1]
BASE_SHA = "434af62f0891959d145b631a77b472b3e80915d3"
PREDECESSOR_HEAD = "8e5d83f695d2f2ef38c9f30e3a8e95eb271718da"


def _market_store(tmp_path: Path, *, populated: bool = True) -> Path:
    path = tmp_path / "market.sqlite3"
    with MarketTruthStore(path) as store:
        if populated:
            raw = _book_raw()
            assert (
                store.append(
                    raw, mt.normalize_websocket_message(raw, book_readiness={})
                ).status
                == "OK"
            )
            later = mt.make_raw_envelope(
                "WS",
                "polymarket:market-ws",
                "ws:00000000-0000-4000-8000-000000000000:frame:2",
                "2024-07-03T09:47:00.000000Z",
                raw.raw_bytes,
                occurrence_sequence=2,
            )
            assert (
                store.append(
                    later, mt.normalize_websocket_message(later, book_readiness={})
                ).status
                == "OK"
            )
            store.mark_gap("7", "OPEN", "DISCONNECT", "2024-07-03T09:47:01.000000Z")
    return path


def _experiment_store(tmp_path: Path, *, populated: bool = True) -> Path:
    path = tmp_path / "experiments.sqlite3"
    assert ar.initialize_experiment_registry(path).is_valid
    if populated:
        records = stack()
        assert ar.append_experiment_records(path, records).is_valid
        experiment = records[-1]
        receipts = lifecycle(experiment, through=5)
        assert ar.append_experiment_records(path, receipts).is_valid
        result = ar.record_experiment_evidence(
            path,
            experiment.experiment_id,
            evidence_input(records[4], "OUT_OF_SAMPLE"),
        )
        assert result.is_valid, result.error_codes
    return path


def _paper_store(tmp_path: Path) -> Path:
    model = build_execution_cost_model(
        model_version="cockpit/1",
        execution_mode="AGGRESSIVE_TAKER",
        fee_schedule_reference="local:fees:v1",
        fee_rate_bps="10",
        latency_ns=0,
        order_ttl_ns=None,
        size_grid=("1",),
        queue_ahead_multiplier="1",
        markout_horizon_ns=0,
        net_edge_threshold="0.01",
        minimum_fill_ratio="1",
        minimum_capacity_quantity="1",
        max_data_age_ns=100,
    )
    records = experiment_stack(cost_model_reference=model.cost_model_id)
    experiment = records[-1]
    receipts = lifecycle(experiment, 5)
    evidence = os_contract._build_run_evidence_receipt(
        experiment,
        records[3],
        records[4],
        records[7],
        receipts,
        (),
        evidence_input(records[4], "OUT_OF_SAMPLE"),
        allow_oos=True,
        prior_oos_release_count=0,
    ).record
    trace = build_research_decision_trace(
        experiment,
        evidence,
        (
            ResearchDecisionEvent(
                "market:a", "asset:a", 100, "BUY", "ENTER", "1", "0.5", "0.8"
            ),
        ),
    )
    book = MarketTruthEvent("BOOK", 99, 100, (("0.49", "2"),), (("0.51", "2"),))
    provisional = MarketTruthWindow(
        "",
        "ext:cockpit",
        "asset:a.POLYMARKET",
        "test/1",
        ("d" * 64 + ":0",),
        "NONE",
        True,
        100,
        100,
        (book,),
        True,
        True,
    )
    window = replace(provisional, lineage_id=identify_market_truth_window(provisional))
    assessment = assess_executable_edge(experiment, evidence, trace, model, window)
    binding = build_strategy_binding(
        assessment,
        model,
        strategy_label="cockpit",
        created_time_ns=1,
    )
    limits = PaperRiskLimits("100", "10", "20", "50", 5, "20", "20", "1", 100)
    path = tmp_path / "paper.sqlite3"
    with PaperStore(path, create=True) as store:
        engine = PaperEngine.create(
            store,
            binding,
            limits,
            assessment=assessment,
            cost_model=model,
            session_label="cockpit",
            created_time_ns=1,
        )
        engine.process_market_event(
            PaperMarketEvent(
                "BOOK",
                "market:a",
                "asset:a",
                99,
                100,
                "cockpit:book:100",
                (("0.49", "2"),),
                (("0.51", "2"),),
            )
        )
        engine.submit(
            build_paper_intent(
                binding,
                market_id="market:a",
                asset_id="asset:a",
                side="BUY",
                quantity="1",
                order_style="AGGRESSIVE_TAKER",
                reference_price="0.5",
                decision_time_ns=100,
            )
        )
        engine.process_market_event(
            PaperMarketEvent(
                "BOOK",
                "market:a",
                "asset:a",
                100,
                101,
                "cockpit:book:101",
                (("0.49", "2"),),
                (("0.51", "2"),),
            )
        )
    return path


async def _asgi_call(app, target: str, *, method: str = "GET") -> tuple[int, dict]:
    parsed = urlsplit(target)
    sent = False
    messages: list[dict] = []

    async def receive() -> dict:
        nonlocal sent
        if not sent:
            sent = True
            return {"type": "http.request", "body": b"", "more_body": False}
        return {"type": "http.disconnect"}

    async def send(message: dict) -> None:
        messages.append(message)

    scope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": parsed.path,
        "raw_path": parsed.path.encode("ascii"),
        "query_string": parsed.query.encode("ascii"),
        "root_path": "",
        "headers": [],
        "client": ("127.0.0.1", 12345),
        "server": ("127.0.0.1", 8000),
    }
    try:
        await app(scope, receive, send)
    except Exception:
        # Starlette's outer error middleware re-raises after sending the configured
        # sanitized 500 response so servers can log it. Assert the emitted response.
        if not any(message["type"] == "http.response.start" for message in messages):
            raise
    start = next(
        message for message in messages if message["type"] == "http.response.start"
    )
    body = b"".join(
        message.get("body", b"")
        for message in messages
        if message["type"] == "http.response.body"
    )
    return start["status"], json.loads(body)


def _get(app, target: str) -> tuple[int, dict]:
    return asyncio.run(_asgi_call(app, target))


def _gateway_store(tmp_path: Path) -> Path:
    path = tmp_path / "gateway.sqlite3"
    with ProtectedExecutionGateway.create(path, created_time_ns=1):
        pass
    return path


def test_wp171_predecessor_scope_and_successor_contract() -> None:
    import subprocess

    assert (
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", PREDECESSOR_HEAD, "HEAD"],
            cwd=ROOT,
        ).returncode
        == 0
    )
    spec = json.loads(
        (ROOT / "docs/wp_specs/WP171/wp_spec.json").read_text(encoding="utf-8")
    )
    assert spec["identity"]["package_size_class"] == "XL"
    assert spec["identity"]["xl_explicit_authorization"] is True
    assert spec["identity"]["required_predecessor"]["merge_sha"] == BASE_SHA
    required = spec["scope"]["required_changed_files"]
    assert required == spec["scope"]["allowed_changed_files"]
    assert len(required) == spec["scope"]["max_changed_files"] == 26
    assert spec["successor_boundary"] == {
        "next_wp": "WP172",
        "next_title": "Hermes Runtime + Alpha Factory",
        "separately_gated": True,
        "feature_validator_moved_to": "WP172",
        "forbidden_in_this_wp": spec["successor_boundary"]["forbidden_in_this_wp"],
    }
    assert not any(
        path.startswith(
            (
                "src/execution_gateway/",
                "src/risk_engine/",
                "src/strategy_modules/",
                "src/paper_trading/",
                "src/data_layer/polymarket/",
                "src/data_layer/analytical_research/",
                "tools/hermes/",
            )
        )
        for path in required
    )


def test_read_only_store_adapters_leave_database_bytes_unchanged(
    tmp_path: Path,
) -> None:
    market = _market_store(tmp_path)
    registry = _experiment_store(tmp_path)
    before = {
        market: hashlib.sha256(market.read_bytes()).hexdigest(),
        registry: hashlib.sha256(registry.read_bytes()).hexdigest(),
    }
    app = cockpit.create_app(cockpit.CockpitConfig(market, registry))
    for route in (
        "/api/health",
        "/api/overview",
        "/api/market-truth/recent?limit=100",
        "/api/experiments?limit=100",
        "/api/audit/recent?limit=100",
    ):
        assert _get(app, route)[0] == 200
    experiment_id = _get(app, "/api/experiments?limit=1")[1]["items"][0][
        "experiment_id"
    ]
    assert _get(app, f"/api/experiments/{experiment_id}")[0] == 200
    assert before == {
        market: hashlib.sha256(market.read_bytes()).hexdigest(),
        registry: hashlib.sha256(registry.read_bytes()).hexdigest(),
    }
    source = (ROOT / "src/operator_cockpit.py").read_text(encoding="utf-8")
    assert "mode=ro" in source
    assert not re.search(
        r"\b(INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|REPLACE)\b", source
    )
    for forbidden in (
        "requests",
        "httpx",
        "websockets",
        "aiohttp",
        "py_clob_client",
        "web3",
    ):
        assert f"import {forbidden}" not in source


def test_exact_routes_limits_errors_and_no_mutation_routes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    market = _market_store(tmp_path)
    registry = _experiment_store(tmp_path)
    app = cockpit.create_app(cockpit.CockpitConfig(market, registry))
    domain = {
        route.path: set(route.methods or ())
        for route in app.routes
        if route.path.startswith("/api/")
    }
    assert domain == {
        "/api/health": {"GET"},
        "/api/overview": {"GET"},
        "/api/market-truth/recent": {"GET"},
        "/api/experiments": {"GET"},
        "/api/experiments/{experiment_id}": {"GET"},
        "/api/audit/recent": {"GET"},
        "/api/paper/summary": {"GET"},
        "/api/paper/orders": {"GET"},
        "/api/paper/fills": {"GET"},
        "/api/paper/positions": {"GET"},
        "/api/paper/risk": {"GET"},
        "/api/paper/audit": {"GET"},
        "/api/gateway/status": {"GET"},
        "/api/gateway/audit": {"GET"},
    }
    assert _get(app, "/api/market-truth/recent")[1]["limit"] == 50
    for accepted in ("1", "100"):
        status, body = _get(app, f"/api/experiments?limit={accepted}")
        assert status == 200 and body["limit"] == int(accepted)
    for rejected in ("0", "101", "no", "1.0", "-1", "9" * 5_000):
        assert _get(app, f"/api/audit/recent?limit={rejected}") == (
            400,
            {"error": {"code": "INVALID_INPUT"}},
        )
    for query in ("?status=OPEN", "?source=WP169", "?limit=1&limit=2"):
        assert _get(app, "/api/market-truth/recent" + query) == (
            400,
            {"error": {"code": "INVALID_INPUT"}},
        )
    assert _get(app, "/api/experiments/not-an-id") == (
        400,
        {"error": {"code": "INVALID_INPUT"}},
    )
    missing = "experiment:sha256:" + "f" * 64
    assert _get(app, f"/api/experiments/{missing}") == (
        404,
        {"error": {"code": "NOT_FOUND"}},
    )
    unavailable = cockpit.create_app(
        cockpit.CockpitConfig(tmp_path / "secret-wp169.sqlite3", registry)
    )
    assert _get(unavailable, "/api/market-truth/recent") == (
        503,
        {"error": {"code": "SOURCE_UNAVAILABLE"}},
    )
    assert _get(unavailable, "/api/market-truth/recent?limit=0") == (
        400,
        {"error": {"code": "INVALID_INPUT"}},
    )
    monkeypatch.setattr(
        cockpit,
        "_recent_market",
        lambda *_args: (_ for _ in ()).throw(RuntimeError("C:\\secret traceback")),
    )
    assert _get(app, "/api/market-truth/recent") == (
        500,
        {"error": {"code": "INTERNAL_ERROR"}},
    )


def test_market_truth_recent_and_gap_health(tmp_path: Path) -> None:
    market = _market_store(tmp_path)
    registry = _experiment_store(tmp_path)
    app = cockpit.create_app(cockpit.CockpitConfig(market, registry))
    status, body = _get(app, "/api/market-truth/recent?limit=1")
    assert status == 200
    assert body["count"] == body["limit"] == 1
    item = body["items"][0]
    assert item["received_at"] == "2024-07-03T09:47:00.000000Z"
    assert set(item) == {
        "observation_id",
        "source_kind",
        "event_kind",
        "event_id",
        "market_id",
        "asset_id",
        "event_time",
        "received_at",
        "status",
        "error_codes",
        "book_ready",
    }
    serialized = json.dumps(body)
    assert "canonical_payload" not in serialized and "provenance" not in serialized
    overview = _get(app, "/api/overview")[1]
    assert overview["market_truth"]["normalized_count"] == 2
    assert overview["market_truth"]["open_gap_count"] == 1
    audit = _get(app, "/api/audit/recent?limit=100")[1]["items"]
    assert any(row["source"] == "WP169" and row["kind"] == "GAP" for row in audit)
    with MarketTruthStore(market) as store:
        store.mark_gap("7", "HEALED", "DISCONNECT", "2024-07-03T09:47:02.000000Z")
    assert _get(app, "/api/overview")[1]["market_truth"]["open_gap_count"] == 0
    with MarketTruthStore(market) as store:
        store.mark_gap("7", "OPEN", "DISCONNECT", "2030-01-01T00:00:00.000000Z")
        store.mark_gap("8", "OPEN", "DISCONNECT", "2020-01-01T00:00:00.000000Z")
    assert (
        cockpit._recent_gaps(market, 1)[0]["occurred_at"]
        == "2030-01-01T00:00:00.000000Z"
    )


def test_overview_quarantined_count_excludes_unsupported(tmp_path: Path) -> None:
    market = _market_store(tmp_path)
    registry = _experiment_store(tmp_path)
    unsupported_raw = mt.make_raw_envelope(
        "WS",
        "polymarket:market-ws",
        "ws:00000000-0000-4000-8000-000000000000:frame:3",
        "2024-07-03T09:47:03.000000Z",
        b"[]",
        occurrence_sequence=3,
    )
    unsupported = mt.normalize_websocket_message(unsupported_raw, book_readiness={})
    assert len(unsupported) == 1 and unsupported[0].status == "UNSUPPORTED"
    with MarketTruthStore(market) as store:
        assert store.append(unsupported_raw, unsupported).status == "OK"

    app = cockpit.create_app(cockpit.CockpitConfig(market, registry))
    summary = _get(app, "/api/overview")[1]["market_truth"]
    assert summary["normalized_count"] == 3
    assert summary["accepted_count"] == 2
    assert summary["quarantined_count"] == 0

    quarantined_raw = mt.make_raw_envelope(
        "WS",
        "polymarket:market-ws",
        "ws:00000000-0000-4000-8000-000000000000:frame:4",
        "2024-07-03T09:47:04.000000Z",
        b'"non-object-frame"',
        occurrence_sequence=4,
    )
    quarantined = mt.normalize_websocket_message(quarantined_raw, book_readiness={})
    assert len(quarantined) == 1 and quarantined[0].status == "QUARANTINED"
    with MarketTruthStore(market) as store:
        assert store.append(quarantined_raw, quarantined).status == "OK"

    summary = _get(app, "/api/overview")[1]["market_truth"]
    assert summary["normalized_count"] == 4
    assert summary["accepted_count"] == 2
    assert summary["quarantined_count"] == 1


def test_experiment_list_detail_preserves_wp170_semantics(tmp_path: Path) -> None:
    app = cockpit.create_app(
        cockpit.CockpitConfig(_market_store(tmp_path), _experiment_store(tmp_path))
    )
    status, body = _get(app, "/api/experiments?limit=1")
    assert status == 200 and body["count"] == 1
    item = body["items"][0]
    assert item["result_status"] == "OOS_CRITERIA_MET_UNCOSTED"
    assert item["oos_exposure_ordinal"] == 1
    status, detail = _get(app, f"/api/experiments/{item['experiment_id']}")
    assert status == 200
    assert detail["item"]["result_status"] == item["result_status"]
    assert detail["item"]["hypothesis_id"] == item["hypothesis_id"]
    assert detail["item"]["lifecycle_receipt_ids"]
    assert detail["item"]["evidence_receipt_ids"]
    rendered = json.dumps(detail).lower()
    assert "profitable" not in rendered and "tradeable" not in rendered


def test_overview_and_audit_are_store_derived_bounded_and_read_only(
    tmp_path: Path,
) -> None:
    app = cockpit.create_app(
        cockpit.CockpitConfig(_market_store(tmp_path), _experiment_store(tmp_path))
    )
    assert _get(app, "/api/health")[1] == {
        "status": "OK",
        "read_only": True,
        "wp169": {"configured": True, "readable": True},
        "wp170": {"configured": True, "readable": True},
        "paper": {"configured": False, "readable": False},
        "gateway": {"configured": False, "readable": False},
    }
    overview = _get(app, "/api/overview")[1]
    assert overview["read_only"] is True
    assert overview["experiments"] == {
        "experiment_count": 1,
        "lifecycle_count": 5,
        "evidence_count": 1,
    }
    first = _get(app, "/api/audit/recent?limit=2")[1]
    second = _get(app, "/api/audit/recent?limit=2")[1]
    assert first == second and first["count"] == first["limit"] == 2
    empty_root = tmp_path / "empty"
    empty_root.mkdir()
    empty = cockpit.create_app(
        cockpit.CockpitConfig(
            _market_store(empty_root, populated=False),
            _experiment_store(empty_root, populated=False),
        )
    )
    assert _get(empty, "/api/market-truth/recent")[1]["items"] == []
    assert _get(empty, "/api/experiments")[1]["items"] == []
    foreign = tmp_path / "foreign.sqlite3"
    sqlite3.connect(foreign).close()
    bad = cockpit.create_app(
        cockpit.CockpitConfig(foreign, tmp_path / "missing.sqlite3")
    )
    for route in ("/api/market-truth/recent", "/api/experiments"):
        status, body = _get(bad, route)
        assert status == 503 and body == {"error": {"code": "SOURCE_UNAVAILABLE"}}
        assert str(tmp_path) not in json.dumps(body)


def test_paper_routes_are_get_only_bounded_sanitized_and_read_only(
    tmp_path: Path,
) -> None:
    market = _market_store(tmp_path)
    registry = _experiment_store(tmp_path)
    paper = _paper_store(tmp_path)
    before = hashlib.sha256(paper.read_bytes()).hexdigest()
    app = cockpit.create_app(cockpit.CockpitConfig(market, registry, paper))
    domain = {
        route.path: set(route.methods or ())
        for route in app.routes
        if route.path.startswith("/api/paper/")
    }
    assert domain == {
        "/api/paper/summary": {"GET"},
        "/api/paper/orders": {"GET"},
        "/api/paper/fills": {"GET"},
        "/api/paper/positions": {"GET"},
        "/api/paper/risk": {"GET"},
        "/api/paper/audit": {"GET"},
    }
    summary = _get(app, "/api/paper/summary")
    assert summary[0] == 200 and summary[1]["simulated_paper_only"] is True
    assert summary[1]["control_state"] == "RUNNING"
    assert summary[1]["fill_count"] == summary[1]["markout_count"] == 1
    for route in ("orders", "fills", "positions", "audit"):
        status, body = _get(app, f"/api/paper/{route}?limit=1")
        assert status == 200 and body["limit"] == 1
        assert _get(app, f"/api/paper/{route}?limit=0") == (
            400,
            {"error": {"code": "INVALID_INPUT"}},
        )
    risk = _get(app, "/api/paper/risk")
    assert risk[0] == 200 and risk[1]["limits"]["initial_cash"] == "100"
    fills = _get(app, "/api/paper/fills?limit=1")[1]["items"]
    assert fills[0]["fill_kind"] == "SIMULATED_PAPER_FILL"
    assert fills[0]["markout_status"] == "AVAILABLE"
    assert set(fills[0]) >= {
        "spread_cost",
        "depth_slippage_cost",
        "latency_cost",
        "adverse_selection_cost",
    }
    assert _get(app, "/api/paper/summary?path=secret") == (
        200,
        summary[1],
    )
    assert before == hashlib.sha256(paper.read_bytes()).hexdigest()
    rendered = json.dumps([summary, risk])
    assert str(tmp_path) not in rendered
    unavailable = cockpit.create_app(
        cockpit.CockpitConfig(
            market,
            registry,
            tmp_path / "missing.sqlite3",
        )
    )
    assert _get(unavailable, "/api/paper/summary") == (
        503,
        {"error": {"code": "SOURCE_UNAVAILABLE"}},
    )


def test_gate_b_cockpit_projection_is_get_only_bounded_and_sanitized(
    tmp_path: Path,
) -> None:
    # WP174B R011: the Gate-B projection is read-only, bounded, sanitized, and
    # Gate-C locked; no secret value, credential input, or mutation control.
    market = _market_store(tmp_path)
    registry = _experiment_store(tmp_path)
    gateway = _gateway_store(tmp_path)
    common = {
        "capability_state": "B4_CANCEL_TRANSPORT_VERIFIED",
        "public_signer": "0x" + "a" * 40,
        "public_wallet": "0x" + "b" * 40,
        "wallet_type": "DEPOSIT_WALLET",
        "signature_type": "3",
    }
    with ProtectedExecutionGateway.open(gateway, opened_time_ns=2) as writer:
        writer.record_gate_b_event(
            "GATE_B_RECONCILED",
            common
            | {
                "gate_b_reconciliation_state": "HEALTHY",
                "collateral_balance": "0",
                "open_orders": 0,
                "account_trades": 0,
                "positions": 0,
            },
            event_time_ns=3,
        )
        writer.record_gate_b_event(
            "GATE_B_CANCEL_TRANSPORT_VERIFIED",
            common
            | {
                "cancel_attempt_id": "cancelattempt:sha256:" + "c" * 64,
                "cancel_result": "DEFINITIVE_ACCEPTED",
                "receipt_id": "gatebreceipt:sha256:" + "d" * 64,
                "verified_time_ns": 4,
                "gate_b_reconciliation_state": "HEALTHY",
            },
            event_time_ns=4,
        )
    app = cockpit.create_app(
        cockpit.CockpitConfig(market, registry, gateway_store_path=gateway)
    )
    status_code, status = _get(app, "/api/gateway/status")
    assert status_code == 200
    gate_b = status["gate_b"]
    assert gate_b["gate_b_capability_available"] is True
    assert gate_b["gate_b_state"] == "B0_LOCKED"
    assert gate_b["credential_session_active"] is False
    assert gate_b["public_signer"] == "0x" + "a" * 40
    assert gate_b["public_wallet"] == "0x" + "b" * 40
    assert gate_b["last_verification_receipt_id"] == "gatebreceipt:sha256:" + "d" * 64
    assert gate_b["last_verification_time_ns"] == 4
    assert gate_b["gate_b_reconciliation_state"] == "HEALTHY"
    assert gate_b["create_transport_status"] == "GATE_C_REQUIRED"
    assert gate_b["cancel_capability_status"] == "AVAILABLE"
    serialized = json.dumps(status)
    for banned in ("private_key", "api_key", "apiKey", "passphrase", "secret-ref:"):
        assert banned not in serialized
    post_code, _ = asyncio.run(_asgi_call(app, "/api/gateway/status", method="POST"))
    assert post_code == 405


def test_gateway_routes_are_get_only_bounded_sanitized_and_read_only(
    tmp_path: Path,
) -> None:
    market = _market_store(tmp_path)
    registry = _experiment_store(tmp_path)
    gateway = _gateway_store(tmp_path)
    before = hashlib.sha256(gateway.read_bytes()).hexdigest()
    app = cockpit.create_app(
        cockpit.CockpitConfig(market, registry, gateway_store_path=gateway)
    )
    domain = {
        route.path: set(route.methods or ())
        for route in app.routes
        if route.path.startswith("/api/gateway/")
    }
    assert domain == {
        "/api/gateway/status": {"GET"},
        "/api/gateway/audit": {"GET"},
    }
    status_code, status = _get(app, "/api/gateway/status")
    assert status_code == 200
    assert status == {
        "read_only": True,
        "authority_state": "A0_DISABLED",
        "disabled": True,
        "disable_reason": "INITIALIZED",
        "credential_configured": False,
        "public_signer": None,
        "public_funder": None,
        "reconciliation_state": "REQUIRED",
        "heartbeat_state": "DISABLED",
        "user_stream_state": "DISCONNECTED",
        "access_state": "UNKNOWN",
        "rate_limit_until_ns": None,
        "prepared_order_count": 0,
        "mutation_attempt_count": 0,
        "open_order_count": 0,
        "gate_b_authorized": False,
        "restricted_live_available": False,
        "restricted_live": {
            "armed": False,
            "halted": False,
            "arm_receipt_id": None,
            "qualification_id": None,
            "attempt_id": None,
            "create_outcome": None,
            "response_status": None,
            "venue_order_id": None,
            "market_id": None,
            "token_id": None,
            "create_attempt_count": 0,
            "capital_at_risk_pusd": "0",
                "capital_committed_pusd": "0",
                "reconciliation_state": "REQUIRED",
                "residual_position_state": "UNKNOWN",
            },
        "gate_b": {
            "gate_b_capability_available": True,
            "gate_b_state": "B0_LOCKED",
            "credential_session_active": False,
            "public_signer": None,
            "public_wallet": None,
            "wallet_type": "DEPOSIT_WALLET",
            "signature_type": "3",
            "last_verification_receipt_id": None,
            "last_verification_time_ns": None,
            "gate_b_reconciliation_state": "REQUIRED",
            "create_transport_status": "GATE_C_REQUIRED",
            "cancel_capability_status": "AVAILABLE",
        },
    }
    # WP174B: the Gate-B projection is read-only, sanitized, and Gate-C locked.
    assert status["gate_b"]["create_transport_status"] == "GATE_C_REQUIRED"
    assert status["gate_b"]["credential_session_active"] is False
    serialized = json.dumps(status)
    for banned in ("private_key", "api_key", "apiKey", "passphrase", "secret-ref:"):
        assert banned not in serialized
    audit_code, audit = _get(app, "/api/gateway/audit?limit=1")
    assert audit_code == 200 and audit["count"] == audit["limit"] == 1
    assert audit["items"][0]["event_type"] == "INITIALIZED"
    assert _get(app, "/api/gateway/audit?limit=0") == (
        400,
        {"error": {"code": "INVALID_INPUT"}},
    )
    post_code, _ = asyncio.run(_asgi_call(app, "/api/gateway/status", method="POST"))
    assert post_code == 405
    assert before == hashlib.sha256(gateway.read_bytes()).hexdigest()
    rendered = json.dumps([status, audit]).lower()
    for forbidden in (
        str(tmp_path).lower(),
        "credential_reference",
        "private_key",
        "secret",
    ):
        assert forbidden not in rendered
    unavailable = cockpit.create_app(
        cockpit.CockpitConfig(
            market,
            registry,
            gateway_store_path=tmp_path / "missing.sqlite3",
        )
    )
    assert _get(unavailable, "/api/gateway/status") == (
        503,
        {"error": {"code": "SOURCE_UNAVAILABLE"}},
    )


def test_live_canary_cockpit_projection_is_get_only(tmp_path: Path) -> None:
    """The bounded gateway route proves the Gate-C projection is GET-only."""
    test_gateway_routes_are_get_only_bounded_sanitized_and_read_only(tmp_path)


def test_paper_cockpit_rejects_consistently_rehashed_logical_divergence(
    tmp_path: Path,
) -> None:
    market = _market_store(tmp_path)
    registry = _experiment_store(tmp_path)
    paper = _paper_store(tmp_path)
    connection = sqlite3.connect(paper)
    row = connection.execute(
        "SELECT sequence,event_id,event_type,event_time_ns,payload_json,"
        "previous_event_hash FROM paper_journal ORDER BY sequence DESC LIMIT 1"
    ).fetchone()
    payload = json.loads(row[4])
    payload["state_after"]["marks"] = [["asset:a", "0.7"]]
    payload_json = canonical_json_bytes(payload).decode("utf-8")
    digest = PaperStore._event_hash(
        row[0], row[1], row[2], row[3], payload_json, row[5]
    )
    state_json = canonical_json_bytes(payload["state_after"]).decode("utf-8")
    connection.execute(
        "UPDATE paper_journal SET payload_json=?,event_hash=? WHERE sequence=?",
        (payload_json, digest, row[0]),
    )
    connection.execute(
        "UPDATE paper_checkpoint SET last_event_hash=?,state_json=?,state_hash=? "
        "WHERE singleton=1",
        (digest, state_json, hashlib.sha256(state_json.encode()).hexdigest()),
    )
    connection.commit()
    connection.close()

    app = cockpit.create_app(cockpit.CockpitConfig(market, registry, paper))
    assert _get(app, "/api/paper/summary") == (
        503,
        {"error": {"code": "SOURCE_UNAVAILABLE"}},
    )


def test_dependency_pins_security_and_historical_guards() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert project["project"]["optional-dependencies"]["cockpit"] == [
        "fastapi==0.141.1",
        "uvicorn==0.52.4",
    ]
    package = json.loads(
        (ROOT / "src/operator_cockpit_frontend/package.json").read_text(
            encoding="utf-8"
        )
    )
    assert package["engines"]["node"] == "24.18.0"
    assert package["dependencies"] == {"react": "19.3.0", "react-dom": "19.3.0"}
    assert package["devDependencies"] == {
        "@types/react": "19.3.0",
        "@types/react-dom": "19.3.0",
        "typescript": "7.0.2",
        "vite": "8.3.0",
    }
    lock = json.loads(
        (ROOT / "src/operator_cockpit_frontend/package-lock.json").read_text(
            encoding="utf-8"
        )
    )
    assert lock["lockfileVersion"] == 3
    assert lock["packages"][""]["dependencies"] == package["dependencies"]
    assert lock["packages"][""]["devDependencies"] == package["devDependencies"]


def test_contract_status_and_repo_truth_are_consistent() -> None:
    contract = (ROOT / "docs/interactive_operator_cockpit_contract.md").read_text(
        encoding="utf-8"
    )
    status = (ROOT / "docs/project_status.md").read_text(encoding="utf-8")
    index = (ROOT / "docs/repo_truth_index.md").read_text(encoding="utf-8")
    deferred = (ROOT / "docs/deferred_items_log.md").read_text(encoding="utf-8")
    frontend = (ROOT / "src/operator_cockpit_frontend/src/main.tsx").read_text(
        encoding="utf-8"
    )
    workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert "WP171 — Interactive Operator Cockpit MVP" in contract
    assert "WP171" in status and "Ready for review: YES" in status
    assert "WP170 merged: YES" in status
    assert "WP171" in index and "src/operator_cockpit.py" in index
    assert "WP170-D001" in deferred and "RESOLVED_BOUNDED_WP171_COCKPIT" in deferred
    for text in (contract, status, index):
        assert "WP172 — Hermes Runtime + Alpha Factory" in text
    assert frontend.count('"Overview"') >= 1
    assert 'node-version: "24.18.0"' in workflow
    assert "npm ci" in workflow and "npm run build" in workflow
