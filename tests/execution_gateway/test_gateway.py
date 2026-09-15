"""WP174 authority, identity, mutation, heartbeat, and access adversarial tests."""

from __future__ import annotations

from dataclasses import asdict, replace
import json
from pathlib import Path
import sqlite3
from types import SimpleNamespace

import pytest
from polymarket import SecureClient
from polymarket.models.clob.account import BalanceAllowance

from src.execution_gateway import (
    CredentialReference,
    FixtureAuthenticatedReadAdapter,
    FixtureVenueContextAdapter,
    GateASecretReferenceLoader,
    GateBLockedSdkMutationAdapter,
    GatewayError,
    ProtectedExecutionGateway,
    OfficialSdkAuthenticatedReadAdapter,
    VenueConstraints,
    VenueIdentity,
    VenueOrderSnapshot,
    UserStreamEvent,
    VenueTradeSnapshot,
    build_fixture_account_snapshot,
    read_wp173_authorization_evidence,
)
from src.paper_trading.models import (
    PaperIntent,
    PaperRiskDecision,
    PaperStrategyBinding,
    content_id,
    canonical_json_bytes,
)
from src.paper_trading.store import PaperStore
from src.paper_trading import PaperEngine, build_paper_intent
from tests.test_operator_cockpit import _paper_store


def _ids(character: str) -> str:
    return character * 64


def _binding() -> PaperStrategyBinding:
    provisional = PaperStrategyBinding(
        "1.0.0",
        "",
        "assessment:sha256:" + _ids("1"),
        "costmodel:sha256:" + _ids("2"),
        "decisiontrace:sha256:" + _ids("3"),
        "marketlineage:sha256:" + _ids("4"),
        "experiment:sha256:" + _ids("5"),
        "evidence:sha256:" + _ids("6"),
        "fixture-strategy",
        1,
        "AGGRESSIVE_TAKER",
        "1",
        "0",
        0,
        None,
        "1",
        0,
        100,
        True,
    )
    preimage = asdict(provisional)
    preimage.pop("binding_id")
    preimage.pop("simulated_paper_only")
    return replace(
        provisional,
        binding_id=content_id("paperbinding:sha256:", preimage),
    )


def _intent(
    *,
    binding: PaperStrategyBinding | None = None,
    price: str = "0.5",
    quantity: str = "2",
    side: str = "BUY",
) -> PaperIntent:
    active_binding = binding or _binding()
    provisional = PaperIntent(
        "1.0.0",
        "",
        active_binding.binding_id,
        "market-a",
        "token-a",
        side,
        quantity,
        "AGGRESSIVE_TAKER",
        price,
        10,
        None,
        True,
    )
    preimage = {
        "schema_version": provisional.schema_version,
        "binding_id": provisional.binding_id,
        "market_id": provisional.market_id,
        "asset_id": provisional.asset_id,
        "side": provisional.side,
        "quantity": provisional.quantity,
        "order_style": provisional.order_style,
        "reference_price": provisional.reference_price,
        "decision_time_ns": provisional.decision_time_ns,
        "ttl_ns": provisional.ttl_ns,
    }
    return replace(
        provisional, intent_id=content_id("paperintent:sha256:", preimage)
    )


def _risk(intent: PaperIntent, *, result: str = "ALLOW") -> PaperRiskDecision:
    limits_hash = "paperlimits:sha256:" + _ids("b")
    preimage = {
        "intent_id": intent.intent_id,
        "result": result,
        "reason_codes": [],
        "decided_time_ns": 11,
        "limits_hash": limits_hash,
    }
    return PaperRiskDecision(
        content_id("paperrisk:sha256:", preimage),
        intent.intent_id,
        result,
        (),
        11,
        limits_hash,
    )


def _authorization(tmp_path: Path):
    path = tmp_path / "paper.sqlite3"
    if not path.exists():
        _paper_store(tmp_path)
    connection = sqlite3.connect(path)
    row = connection.execute(
        "SELECT payload_json FROM paper_journal WHERE event_type='ORDER_PENDING_RISK' "
        "ORDER BY sequence LIMIT 1"
    ).fetchone()
    connection.close()
    assert row is not None
    intent_id = json.loads(row[0])["data"]["intent"]["intent_id"]
    return path, intent_id, read_wp173_authorization_evidence(path, intent_id=intent_id)


def _identity(*, exchange: str = "neg-risk-exchange") -> VenueIdentity:
    return VenueIdentity(
        137,
        "Polymarket CTF Exchange",
        "2",
        (
            "0xe2222d279d744050d28e00520010520000310f59"
            if exchange == "neg-risk-exchange"
            else "0xe111180000d2663c0091e4f400237545b87b996b"
        ),
        "0x" + "1" * 40,
        "0x" + "2" * 40,
        "EOA",
        "0",
        exchange,
    )


def _constraints(
    *,
    access_state: str = "ELIGIBLE",
    tick_size: str = "0.01",
    minimum_order_size: str = "1",
    exchange: str = "neg-risk-exchange",
    post_only_allowed: bool = True,
) -> VenueConstraints:
    return VenueConstraints(
        "market:a",
        "condition-a",
        "asset:a",
        tick_size,
        minimum_order_size,
        True,
        exchange,
        access_state,
        post_only_allowed,
        True,
        True,
        10,
        100,
        "venue-constraints-v1",
    )


def _venue_context(
    constraints: VenueConstraints | None = None,
    identity: VenueIdentity | None = None,
) -> FixtureVenueContextAdapter:
    return FixtureVenueContextAdapter(constraints or _constraints(), identity or _identity())


def _snapshot(
    *,
    open_orders=(),
    recent_trades=(),
    observed_time_ns: int = 2,
    access_state: str = "ELIGIBLE",
    venue_mode: str = "NORMAL",
):
    return build_fixture_account_snapshot(
        signer="0x" + "1" * 40,
        funder="0x" + "2" * 40,
        observed_time_ns=observed_time_ns,
        access_state=access_state,
        venue_mode=venue_mode,
        open_orders=open_orders,
        recent_trades=recent_trades,
        balances_hash="balances:sha256:" + _ids("8"),
        positions_hash="positions:sha256:" + _ids("9"),
    )


def _loader() -> GateASecretReferenceLoader:
    return GateASecretReferenceLoader(
        {"secret-ref:fixture-one": ("0x" + "1" * 40, "0x" + "2" * 40)}
    )


def _ready_gateway(tmp_path: Path) -> ProtectedExecutionGateway:
    gateway = ProtectedExecutionGateway.create(
        tmp_path / "gateway.sqlite3", created_time_ns=1
    )
    gateway.configure_credentials(
        _loader(),
        "secret-ref:fixture-one",
        event_time_ns=2,
    )
    gateway.reconcile(
        adapter=FixtureAuthenticatedReadAdapter(_snapshot()), event_time_ns=3
    )
    gateway.set_authority("A2_SHADOW", actor="fixture-operator", event_time_ns=4)
    return gateway


def _prepare(gateway: ProtectedExecutionGateway, tmp_path: Path):
    path, intent_id, evidence = _authorization(tmp_path)
    item = evidence.intent
    return gateway.prepare_limit_order(
        path,
        intent_id,
        _venue_context(),
        session_identity="paper-session-a",
        worst_acceptable_price="0.6" if item.side == "BUY" else "0.4",
        time_in_force="GTC",
        post_only=False,
        expiration=None,
        nonce=1,
        signing_time_ns=20,
    )


def test_authority_secret_isolation_and_gate_b_transport_unreachable(
    tmp_path: Path,
) -> None:
    gateway = ProtectedExecutionGateway.create(
        tmp_path / "gateway.sqlite3", created_time_ns=1
    )
    gateway.configure_credentials(_loader(), "secret-ref:fixture-one", event_time_ns=2)
    assert gateway.state.authority_state == "A0_DISABLED"
    assert gateway.cockpit_projection()["credential_configured"] is True
    assert "secret-ref:fixture-one" not in json.dumps(gateway.cockpit_projection())
    for bad in ("A3_RESTRICTED_LIVE", "RESTRICTED_LIVE", "A4"):
        with pytest.raises(GatewayError, match="AUTHORITY_STATE_INVALID"):
            gateway.set_authority(bad, actor="fixture-operator", event_time_ns=3)
    with pytest.raises(GatewayError, match="GATE_B_REQUIRED"):
        GateBLockedSdkMutationAdapter()
    with pytest.raises(GatewayError, match="GATE_B_REQUIRED"):
        gateway.place_limit_order()
    with pytest.raises(GatewayError, match="GATE_B_REQUIRED"):
        gateway.cancel()
    with pytest.raises(GatewayError, match="CREDENTIAL_REFERENCE_UNAVAILABLE"):
        gateway.configure_credentials(
            _loader(), "fixture-value", event_time_ns=4
        )
    gateway.close()
    raw = (tmp_path / "gateway.sqlite3").read_text(encoding="utf-8", errors="ignore")
    assert "fixture-value" not in raw
    assert "secret-ref:fixture-one" not in raw
    with pytest.raises(GatewayError, match="CREDENTIAL_REFERENCE_INVALID"):
        CredentialReference("secret-ref:private-key-value", True).validate()


def test_limit_order_identity_constraints_and_unsupported_surface(
    tmp_path: Path,
) -> None:
    with _ready_gateway(tmp_path) as gateway:
        path, intent_id, evidence = _authorization(tmp_path)
        first = _prepare(gateway, tmp_path)
        second = _prepare(gateway, tmp_path)
        assert first == second
        assert first.order_identity.startswith("executionorder:sha256:")
        assert first.would_submit == {
            "asset_id": "asset:a",
            "price": "0.5",
            "size": "1",
            "side": "BUY",
            "post_only": False,
            "expiration": None,
            "order_type": "LIMIT",
            "time_in_force": "GTC",
            "signed_order_hash": first.signed_order_hash,
        }
        assert first.signed_order_hash.startswith("fixturesignedorder:sha256:")
        with pytest.raises(GatewayError, match="ORDER_IDENTITY_CONFLICT"):
            gateway.prepare_limit_order(
                path,
                intent_id,
                _venue_context(),
                session_identity="paper-session-a",
                worst_acceptable_price="0.6",
                time_in_force="GTC",
                post_only=False,
                expiration=None,
                nonce=2,
                signing_time_ns=20,
            )
        for unsupported in ("MARKET", "FAK", "FOK", "IOC", "STOP"):
            with pytest.raises(GatewayError, match="UNSUPPORTED_ORDER_INSTRUCTION"):
                gateway.prepare_limit_order(
                    path,
                    intent_id,
                    _venue_context(),
                    session_identity="paper-session-b",
                    worst_acceptable_price="0.6",
                    time_in_force=unsupported,
                    post_only=False,
                    expiration=None,
                    nonce=3,
                    signing_time_ns=21,
                )
        with pytest.raises(GatewayError, match="ORDER_CONSTRAINT_INVALID"):
            gateway.prepare_limit_order(
                path,
                intent_id,
                _venue_context(_constraints(tick_size="0.03")),
                session_identity="paper-session-c",
                worst_acceptable_price="0.6",
                time_in_force="GTC",
                post_only=False,
                expiration=None,
                nonce=4,
                signing_time_ns=22,
            )
        with pytest.raises(GatewayError, match="SIGNING_IDENTITY_INVALID"):
            gateway.prepare_limit_order(
                path,
                intent_id,
                _venue_context(
                    _constraints(exchange="exchange-a"),
                    _identity(exchange="exchange-b"),
                ),
                session_identity="paper-session-d",
                worst_acceptable_price="0.6",
                time_in_force="GTC",
                post_only=False,
                expiration=None,
                nonce=5,
                signing_time_ns=23,
            )
        with pytest.raises(GatewayError, match="WP173_BINDING_INVALID"):
            gateway.prepare_limit_order(
                path,
                "paperintent:sha256:" + _ids("f"),
                _venue_context(),
                session_identity="paper-session-invalid",
                worst_acceptable_price="0.6",
                time_in_force="GTC",
                post_only=False,
                expiration=None,
                nonce=6,
                signing_time_ns=24,
            )
        signer_mismatch = replace(_identity(), signer="0x" + "3" * 40)
        with pytest.raises(GatewayError, match="SIGNING_IDENTITY_INVALID"):
            gateway.prepare_limit_order(
                path,
                intent_id,
                _venue_context(identity=signer_mismatch),
                session_identity="paper-session-e",
                worst_acceptable_price="0.7",
                time_in_force="GTC",
                post_only=False,
                expiration=None,
                nonce=6,
                signing_time_ns=24,
            )
        with pytest.raises(GatewayError, match="ACCESS_NOT_ELIGIBLE"):
            gateway.prepare_limit_order(
                path,
                intent_id,
                _venue_context(_constraints(access_state="GEOBLOCKED")),
                session_identity="paper-session-e",
                worst_acceptable_price="0.7",
                time_in_force="GTC",
                post_only=False,
                expiration=None,
                nonce=6,
                signing_time_ns=24,
            )
        with pytest.raises(GatewayError, match="VENUE_CONSTRAINTS_STALE"):
            gateway.prepare_limit_order(
                path,
                intent_id,
                _venue_context(replace(_constraints(), valid_until_ns=23)),
                session_identity="paper-session-e",
                worst_acceptable_price="0.7",
                time_in_force="GTC",
                post_only=False,
                expiration=None,
                nonce=6,
                signing_time_ns=24,
            )
        with pytest.raises(GatewayError, match="ORDER_CONSTRAINT_INVALID"):
            gateway.prepare_limit_order(
                path,
                intent_id,
                _venue_context(),
                session_identity="paper-session-e",
                worst_acceptable_price="0.4",
                time_in_force="GTC",
                post_only=False,
                expiration=None,
                nonce=6,
                signing_time_ns=24,
            )


def test_mutation_attempt_idempotency_and_no_blind_retry(tmp_path: Path) -> None:
    with _ready_gateway(tmp_path) as gateway:
        order = _prepare(gateway, tmp_path)
        accepted = gateway.record_fixture_mutation(
            order.order_identity,
            operation="CREATE",
            attempt_sequence=1,
            request=order.would_submit,
            transmitted=True,
            response_status=200,
            response_body_valid=True,
            venue_order_id="venue-order-a",
            event_time_ns=30,
        )
        duplicate = gateway.record_fixture_mutation(
            order.order_identity,
            operation="CREATE",
            attempt_sequence=1,
            request=order.would_submit,
            transmitted=True,
            response_status=200,
            response_body_valid=True,
            venue_order_id="venue-order-a",
            event_time_ns=30,
        )
        assert duplicate == accepted
        with pytest.raises(GatewayError, match="MUTATION_IDENTITY_CONFLICT"):
            gateway.record_fixture_mutation(
                order.order_identity,
                operation="CREATE",
                attempt_sequence=1,
                request=order.would_submit,
                transmitted=True,
                response_status=400,
                response_body_valid=True,
                venue_order_id=None,
                event_time_ns=30,
            )
        with pytest.raises(GatewayError, match="MUTATION_ALREADY_TRANSMITTED"):
            gateway.record_fixture_mutation(
                order.order_identity,
                operation="CREATE",
                attempt_sequence=2,
                request=order.would_submit,
                transmitted=True,
                response_status=500,
                response_body_valid=False,
                venue_order_id=None,
                event_time_ns=31,
            )
    ambiguous_root = tmp_path / "ambiguous"
    ambiguous_root.mkdir()
    with _ready_gateway(ambiguous_root) as gateway:
        order = _prepare(gateway, ambiguous_root)
        ambiguous = gateway.record_fixture_mutation(
            order.order_identity,
            operation="CREATE",
            attempt_sequence=1,
            request=order.would_submit,
            transmitted=True,
            response_status=200,
            response_body_valid=False,
            venue_order_id=None,
            event_time_ns=30,
        )
        assert ambiguous.outcome == "AMBIGUOUS"
        assert gateway.state.authority_state == "A0_DISABLED"
        assert gateway.state.reconciliation_state == "REQUIRED"
        with pytest.raises(GatewayError, match="SHADOW_AUTHORITY_REQUIRED"):
            gateway.record_fixture_mutation(
                order.order_identity,
                operation="CREATE",
                attempt_sequence=2,
                request=order.would_submit,
                transmitted=True,
                response_status=None,
                response_body_valid=False,
                venue_order_id=None,
                event_time_ns=31,
            )


def test_ambiguous_mutation_stream_gap_and_foreign_state_reconcile_or_block(
    tmp_path: Path,
) -> None:
    with _ready_gateway(tmp_path) as gateway:
        order = _prepare(gateway, tmp_path)
        gateway.record_fixture_mutation(
            order.order_identity,
            operation="CREATE",
            attempt_sequence=1,
            request=order.would_submit,
            transmitted=True,
            response_status=200,
            response_body_valid=True,
            venue_order_id="venue-order-a",
            event_time_ns=29,
        )
        lost_cancel = gateway.record_fixture_mutation(
            order.order_identity,
            operation="CANCEL_ONE",
            attempt_sequence=1,
            request={"venue_order_ids": ["venue-order-a"]},
            transmitted=True,
            response_status=None,
            response_body_valid=False,
            venue_order_id="venue-order-a",
            event_time_ns=30,
        )
        assert lost_cancel.outcome == "AMBIGUOUS"
        foreign = VenueOrderSnapshot(
            "foreign-order", "executionorder:sha256:" + _ids("f"), "OPEN", "0"
        )
        gateway.reconcile(
            adapter=FixtureAuthenticatedReadAdapter(_snapshot(open_orders=(foreign,))),
            event_time_ns=31,
        )
        assert gateway.state.reconciliation_state == "DIVERGED"
        assert gateway.state.authority_state == "A0_DISABLED"
        known = VenueOrderSnapshot(
            "venue-order-a", order.order_identity, "OPEN", "0"
        )
        gateway.reconcile(
            adapter=FixtureAuthenticatedReadAdapter(_snapshot(open_orders=(known,))),
            event_time_ns=32,
        )
        assert gateway.state.reconciliation_state == "HEALTHY"
        gateway.set_authority("A2_SHADOW", actor="fixture-operator", event_time_ns=33)
        stream_event = UserStreamEvent(
            2, "userevent:sha256:" + _ids("a"), "ORDER", "venue-order-a"
        )
        gateway.poll_user_stream(
            FixtureAuthenticatedReadAdapter(_snapshot(), user_events=(stream_event,)),
            event_time_ns=34,
        )
        assert gateway.state.reconciliation_state == "REQUIRED"
        assert gateway.state.authority_state == "A0_DISABLED"


@pytest.mark.parametrize("status", [None, 425, 429, 500, 503])
def test_transmitted_timeout_retryable_or_server_response_is_ambiguous(
    tmp_path: Path, status: int | None
) -> None:
    case_root = tmp_path / ("timeout" if status is None else f"status-{status}")
    case_root.mkdir()
    with _ready_gateway(case_root) as gateway:
        order = _prepare(gateway, case_root)
        attempt = gateway.record_fixture_mutation(
            order.order_identity,
            operation="CREATE",
            attempt_sequence=1,
            request=order.would_submit,
            transmitted=True,
            response_status=status,
            response_body_valid=status is not None,
            venue_order_id=None,
            event_time_ns=30,
        )
        assert attempt.outcome == "AMBIGUOUS"
        assert gateway.state.authority_state == "A0_DISABLED"
        assert gateway.state.reconciliation_state == "REQUIRED"


def test_identity_snapshot_trade_and_cancel_semantics_fail_closed(
    tmp_path: Path,
) -> None:
    for changes in (
        {"chain_id": 1},
        {"protocol_version": "clob-v1"},
        {"wallet_type": "PROXY"},
        {"signature_type": "PROXY"},
        {"exchange": "other-exchange"},
    ):
        with pytest.raises(GatewayError, match="SIGNING_IDENTITY_INVALID"):
            replace(_identity(), **changes).validate()
    with pytest.raises(GatewayError, match="ACCOUNT_SNAPSHOT_INVALID"):
        _snapshot(
            open_orders=(
                VenueOrderSnapshot(
                    "venue-negative",
                    "executionorder:sha256:" + _ids("d"),
                    "OPEN",
                    "-1",
                ),
            )
        )

    with _ready_gateway(tmp_path) as gateway:
        order = _prepare(gateway, tmp_path)
        gateway.record_fixture_mutation(
            order.order_identity,
            operation="CREATE",
            attempt_sequence=1,
            request=order.would_submit,
            transmitted=True,
            response_status=200,
            response_body_valid=True,
            venue_order_id="venue-order-a",
            event_time_ns=30,
        )
        with pytest.raises(GatewayError, match="ACCOUNT_SNAPSHOT_INVALID"):
            gateway.reconcile(
                adapter=FixtureAuthenticatedReadAdapter(_snapshot()),
                event_time_ns=60_000_000_003,
            )
        unrelated = VenueTradeSnapshot(
            "trade-unrelated",
            "venue-other",
            order.order_identity,
            "1",
        )
        gateway.reconcile(
            adapter=FixtureAuthenticatedReadAdapter(
                _snapshot(recent_trades=(unrelated,))
            ),
            event_time_ns=31,
        )
        assert gateway.state.reconciliation_state == "DIVERGED"

    cancel_root = tmp_path / "cancel"
    cancel_root.mkdir()
    with _ready_gateway(cancel_root) as gateway:
        order = _prepare(gateway, cancel_root)
        gateway.record_fixture_mutation(
            order.order_identity,
            operation="CREATE",
            attempt_sequence=1,
            request=order.would_submit,
            transmitted=True,
            response_status=200,
            response_body_valid=True,
            venue_order_id="venue-order-a",
            event_time_ns=30,
        )
        paper_path, _first_intent_id, _ = _authorization(cancel_root)
        with PaperStore(paper_path) as paper_store:
            paper = PaperEngine.open(paper_store)
            second_intent = build_paper_intent(
                paper.state.binding,
                market_id="market:a",
                asset_id="asset:a",
                side="BUY",
                quantity="1",
                order_style="AGGRESSIVE_TAKER",
                reference_price="0.4",
                decision_time_ns=101,
            )
            paper.submit(second_intent)
        second = gateway.prepare_limit_order(
            paper_path,
            second_intent.intent_id,
            _venue_context(),
            session_identity="paper-session-second",
            worst_acceptable_price="0.6",
            time_in_force="GTC",
            post_only=False,
            expiration=None,
            nonce=2,
            signing_time_ns=30,
        )
        gateway.record_fixture_mutation(
            second.order_identity,
            operation="CREATE",
            attempt_sequence=1,
            request=second.would_submit,
            transmitted=True,
            response_status=200,
            response_body_valid=True,
            venue_order_id="venue-order-b",
            event_time_ns=30,
        )
        with pytest.raises(GatewayError, match="MUTATION_REQUEST_INVALID"):
            gateway.record_fixture_mutation(
                order.order_identity,
                operation="CANCEL_MARKET",
                attempt_sequence=1,
                request={"venue_order_ids": ["venue-order-a"], "market_id": "wrong"},
                transmitted=False,
                response_status=None,
                response_body_valid=False,
                venue_order_id=None,
                event_time_ns=31,
            )
        with pytest.raises(GatewayError, match="MUTATION_REQUEST_INVALID"):
            gateway.record_fixture_mutation(
                order.order_identity,
                operation="CANCEL_ALL",
                attempt_sequence=1,
                request={"venue_order_ids": ["venue-other"]},
                transmitted=False,
                response_status=None,
                response_body_valid=False,
                venue_order_id=None,
                event_time_ns=31,
            )
        canceled = gateway.record_fixture_mutation(
            order.order_identity,
            operation="CANCEL_MANY",
            attempt_sequence=1,
            request={"venue_order_ids": ["venue-order-a", "venue-order-b"]},
            transmitted=True,
            response_status=200,
            response_body_valid=True,
            venue_order_id=None,
            event_time_ns=32,
        )
        assert canceled.outcome == "DEFINITIVE_ACCEPTED"
        assert gateway.state.venue_open_order_ids == ()
        with pytest.raises(GatewayError, match="MUTATION_ALREADY_TRANSMITTED"):
            gateway.record_fixture_mutation(
                order.order_identity,
                operation="CANCEL_MANY",
                attempt_sequence=2,
                request={"venue_order_ids": ["venue-order-a", "venue-order-b"]},
                transmitted=True,
                response_status=200,
                response_body_valid=True,
                venue_order_id=None,
                event_time_ns=33,
            )


def test_official_sdk_a1_read_adapter_is_bounded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = object.__new__(SecureClient)
    context = SimpleNamespace(
        environment_config=SimpleNamespace(chain_id=137), signer_type="OWNER"
    )
    monkeypatch.setattr(SecureClient, "_ctx", property(lambda self: context))
    monkeypatch.setattr(
        SecureClient, "environment", property(lambda self: SimpleNamespace(name="production"))
    )
    monkeypatch.setattr(SecureClient, "signer", property(lambda self: "0x" + "1" * 40))
    monkeypatch.setattr(SecureClient, "wallet", property(lambda self: "0x" + "2" * 40))
    monkeypatch.setattr(SecureClient, "wallet_type", property(lambda self: "EOA"))
    monkeypatch.setattr(SecureClient, "list_open_orders", lambda self: ())
    monkeypatch.setattr(SecureClient, "list_account_trades", lambda self: ())
    monkeypatch.setattr(
        SecureClient,
        "get_balance_allowance",
        lambda self, **_kwargs: BalanceAllowance(balance=10, allowances={}),
    )
    monkeypatch.setattr(SecureClient, "list_positions", lambda self, **_kwargs: ())
    monkeypatch.setattr(SecureClient, "get_closed_only_mode", lambda self: False)
    adapter = OfficialSdkAuthenticatedReadAdapter(
        client,
        observed_time_ns=2,
        order_identity_by_venue_id={},
    )
    snapshot = adapter.query_account()
    assert snapshot.fixture_only is False
    assert snapshot.access_state == "UNKNOWN"
    assert snapshot.venue_mode == "RESTARTING"
    assert adapter.query_open_orders() == ()
    assert adapter.query_recent_trades() == ()


def test_official_sdk_malformed_model_is_sanitized(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = object.__new__(SecureClient)
    context = SimpleNamespace(
        environment_config=SimpleNamespace(chain_id=137), signer_type="OWNER"
    )
    monkeypatch.setattr(SecureClient, "_ctx", property(lambda self: context))
    monkeypatch.setattr(
        SecureClient, "environment", property(lambda self: SimpleNamespace(name="production"))
    )
    monkeypatch.setattr(SecureClient, "signer", property(lambda self: "0x" + "1" * 40))
    monkeypatch.setattr(SecureClient, "wallet", property(lambda self: "0x" + "2" * 40))
    monkeypatch.setattr(SecureClient, "wallet_type", property(lambda self: "EOA"))
    monkeypatch.setattr(SecureClient, "list_open_orders", lambda self: (object(),))
    monkeypatch.setattr(SecureClient, "list_account_trades", lambda self: ())
    monkeypatch.setattr(SecureClient, "list_positions", lambda self, **_kwargs: ())
    monkeypatch.setattr(
        SecureClient,
        "get_balance_allowance",
        lambda self, **_kwargs: BalanceAllowance(balance=10, allowances={}),
    )
    monkeypatch.setattr(SecureClient, "get_closed_only_mode", lambda self: False)
    adapter = OfficialSdkAuthenticatedReadAdapter(
        client,
        observed_time_ns=2,
        order_identity_by_venue_id={},
    )
    with pytest.raises(GatewayError, match="AUTHENTICATED_READ_FAILED"):
        adapter.query_account()


def test_wp173_semantically_invalid_rehashed_journal_is_rejected(
    tmp_path: Path,
) -> None:
    path, intent_id, _ = _authorization(tmp_path)
    connection = sqlite3.connect(path)
    rows = connection.execute(
        "SELECT sequence,event_id,event_type,event_time_ns,payload_json "
        "FROM paper_journal ORDER BY sequence"
    ).fetchall()
    previous = None
    for sequence, event_id, event_type, event_time_ns, payload_json in rows:
        payload = json.loads(payload_json)
        if event_type == "ORDER_PENDING_RISK":
            payload["state_after"]["control_state"] = "KILLED"
        encoded = canonical_json_bytes(payload).decode("utf-8")
        digest = PaperStore._event_hash(
            sequence, event_id, event_type, event_time_ns, encoded, previous
        )
        connection.execute(
            "UPDATE paper_journal SET payload_json=?,previous_event_hash=?,event_hash=? "
            "WHERE sequence=?",
            (encoded, previous, digest, sequence),
        )
        previous = digest
    connection.execute(
        "UPDATE paper_checkpoint SET last_event_hash=? WHERE singleton=1", (previous,)
    )
    connection.commit()
    connection.close()
    with pytest.raises(GatewayError, match="WP173_BINDING_INVALID"):
        read_wp173_authorization_evidence(path, intent_id=intent_id)


@pytest.mark.parametrize(
    "access_state",
    ["GEOBLOCKED", "CLOSE_ONLY", "CANCEL_ONLY", "ENGINE_RESTRICTED", "UNKNOWN"],
)
def test_heartbeat_rate_limit_and_access_modes_fail_closed(
    tmp_path: Path, access_state: str
) -> None:
    gateway = _ready_gateway(tmp_path)
    gateway.exchange_heartbeat(
        FixtureAuthenticatedReadAdapter(_snapshot(), heartbeat_ack="heartbeat-a"),
        expected_id="heartbeat-a",
        event_time_ns=5,
    )
    assert gateway.state.heartbeat_state == "HEALTHY"
    until = gateway.record_rate_limit(
        {"Retry-After": "2"}, now_ns=10, event_time_ns=6
    )
    assert until == 2_000_000_010
    with pytest.raises(GatewayError, match="RATE_LIMITED"):
        _prepare(gateway, tmp_path)
    with pytest.raises(GatewayError, match="RETRY_AFTER_INVALID"):
        gateway.record_rate_limit({"Retry-After": "61"}, now_ns=10, event_time_ns=7)
    gateway.heartbeat_missed(event_time_ns=8)
    assert gateway.state.authority_state == "A0_DISABLED"
    assert gateway.state.reconciliation_state == "REQUIRED"
    gateway.reconcile(
        adapter=FixtureAuthenticatedReadAdapter(_snapshot()), event_time_ns=9
    )
    with pytest.raises(GatewayError, match="RECONCILIATION_REQUIRED"):
        gateway.set_authority("A2_SHADOW", actor="fixture-operator", event_time_ns=10)
    gateway.exchange_heartbeat(
        FixtureAuthenticatedReadAdapter(_snapshot(), heartbeat_ack="heartbeat-b"),
        expected_id="heartbeat-b",
        event_time_ns=10,
    )
    gateway.set_authority("A2_SHADOW", actor="fixture-operator", event_time_ns=10)
    gateway.record_access(access_state, event_time_ns=11)
    assert gateway.state.authority_state == "A0_DISABLED"
    with pytest.raises(GatewayError, match="SHADOW_AUTHORITY_REQUIRED"):
        _prepare(gateway, tmp_path)
    gateway.close()
