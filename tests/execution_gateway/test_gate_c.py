"""WP175 restricted-live canary contract and negative matrix tests.

All tests use synthetic public IDs and never invoke a venue or a real secret.
"""

from __future__ import annotations

from dataclasses import asdict, replace
from decimal import Decimal
import inspect
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
import polymarket
from polymarket import SecureClient
from polymarket.models.clob.account import BalanceAllowance
from polymarket.models.clob.order_response import AcceptedOrder, RejectedOrder
from polymarket.models.clob.orders import SignedOrder

import src.execution_gateway.gate_b as gate_b_mod
import src.execution_gateway.gate_c as gate_c_mod
from src.execution_gateway import (
    CanaryRiskEnvelope,
    GateCGeoblockProof,
    GateCMarketMetadata,
    GateCCanaryReceipt,
    GateCLivePermit,
    GatewayError,
    ProtectedExecutionGateway,
)
from src.execution_gateway.gate_c import (
    FINAL_MERGE_SMOKE_CREATE_ATTEMPTS,
    FIRST_LIVE_ACTIVATION_CANARY_CREATE_ATTEMPTS,
    MAX_CANARY_WALLET_PUSD,
    MAX_CREATE_ATTEMPTS_PER_SESSION,
    MAX_GROSS_LIVE_EXPOSURE_PUSD,
    MAX_PER_MARKET_EXPOSURE_PUSD,
    MAX_PER_ORDER_COMMITTED_PUSD,
    GateCSession,
    canonical_gateway_store_path,
    runtime_repository_identity,
    _id,
)
from src.execution_gateway.gate_c_operator import GateCOperator
from src.execution_gateway.gateway import _GATE_C_EVENT_ISSUER
from tests.execution_gateway.test_gateway import _prepare, _ready_gateway
from src.paper_trading import PaperEngine, PaperStore
from tests.paper_trading.conftest import edge_stack, generous_limits
from tests.paper_trading.test_models import _research_binding


def test_dormant_merge_needs_zero_real_creates_but_one_post_merge_canary() -> None:
    # Dormant code merge requires zero real economic CREATEs.
    assert FINAL_MERGE_SMOKE_CREATE_ATTEMPTS == 0
    assert gate_c_mod.FINAL_MERGE_SMOKE_CREATE_ATTEMPTS == 0
    # The single real CREATE belongs only to the post-merge first live activation canary.
    assert FIRST_LIVE_ACTIVATION_CANARY_CREATE_ATTEMPTS == 1
    # The runtime one-attempt-per-session live limit is unchanged.
    assert MAX_CREATE_ATTEMPTS_PER_SESSION == 1
    # Merge-ready evidence (zero creates) is never live-activation readiness: the
    # exported constants keep the merge requirement and the live-canary requirement
    # distinct, and neither disables the single-attempt live cap.
    assert FINAL_MERGE_SMOKE_CREATE_ATTEMPTS != FIRST_LIVE_ACTIVATION_CANARY_CREATE_ATTEMPTS


def test_fixed_risk_envelope_cannot_be_widened() -> None:
    envelope = CanaryRiskEnvelope()
    envelope.validate()
    assert Decimal(envelope.max_canary_wallet_pusd) == MAX_CANARY_WALLET_PUSD
    assert Decimal(envelope.max_gross_live_exposure_pusd) == MAX_GROSS_LIVE_EXPOSURE_PUSD
    assert Decimal(envelope.max_per_market_exposure_pusd) == MAX_PER_MARKET_EXPOSURE_PUSD
    assert Decimal(envelope.max_per_order_committed_pusd) == MAX_PER_ORDER_COMMITTED_PUSD
    with pytest.raises(GatewayError, match="RISK_ENVELOPE_INVALID"):
        CanaryRiskEnvelope(max_canary_wallet_pusd="500").validate()


def test_geoblock_proof_discards_jurisdiction_and_fails_closed() -> None:
    proof = GateCGeoblockProof.from_response(
        {"blocked": False, "ip": "203.0.113.1", "country": "ZZ", "region": "x"},
        observed_time_ns=100,
    )
    proof.validate(now_ns=100, require_pass=True)
    assert "203.0.113.1" not in json.dumps(asdict(proof))
    blocked = GateCGeoblockProof.from_response({"blocked": True}, observed_time_ns=100)
    with pytest.raises(GatewayError, match="ACCESS_NOT_ELIGIBLE"):
        blocked.validate(now_ns=100, require_pass=True)


def test_market_metadata_rejects_neg_risk_delayed_and_stale() -> None:
    values = dict(
        market_id="market-a", condition_id="condition-a", token_id="token-a",
        observed_time_ns=100, valid_until_ns=200,
    )
    GateCMarketMetadata(**values).validate(now_ns=100)
    with pytest.raises(GatewayError, match="MARKET_NOT_ELIGIBLE"):
        GateCMarketMetadata(**values, neg_risk=True).validate(now_ns=100)
    with pytest.raises(GatewayError, match="MARKET_NOT_ELIGIBLE"):
        GateCMarketMetadata(**values, delayed=True).validate(now_ns=100)
    with pytest.raises(GatewayError, match="MARKET_METADATA_STALE"):
        GateCMarketMetadata(**values).validate(now_ns=201)


def test_generic_authority_setter_cannot_enter_a3(tmp_path: Path) -> None:
    path = tmp_path / "gateway.sqlite3"
    gateway = ProtectedExecutionGateway.create(path, created_time_ns=1)
    try:
        with pytest.raises(GatewayError, match="AUTHORITY_STATE_INVALID"):
            gateway.set_authority("A3_RESTRICTED_LIVE", actor="operator", event_time_ns=2)
        with pytest.raises(GatewayError, match="GATE_C_REQUIRED"):
            GateCLivePermit()
    finally:
        gateway.close()


def test_a3_cannot_be_rehydrated_from_restart(tmp_path: Path) -> None:
    path = tmp_path / "gateway.sqlite3"
    gateway = ProtectedExecutionGateway.create(path, created_time_ns=1)
    checkpoint = {
        "armed": False, "halted": True, "authority_state": "A0_DISABLED",
        "disable_reason": "OPERATOR_KILL", "reconciliation_state": "BLOCKED",
        "access_state": "UNKNOWN",
    }
    gateway.record_gate_c_event(
        "GATE_C_HALTED", checkpoint,
        issuer=_GATE_C_EVENT_ISSUER, event_time_ns=2,
    )
    gateway.close()
    with ProtectedExecutionGateway.open(path, opened_time_ns=3) as reopened:
        assert reopened.state.authority_state == "A0_DISABLED"
        assert reopened.state.reconciliation_state == "REQUIRED"


def test_installed_sdk_contract_is_exact() -> None:
    """Pin the implementation to the installed official 0.10.0 model surface."""
    assert polymarket.__version__ == "0.10.0"
    create = inspect.signature(SecureClient.create_limit_order)
    assert set(create.parameters) >= {
        "asset_id", "token_id", "price", "size", "side", "post_only", "expiration"
    }
    assert inspect.signature(SecureClient.post_order).parameters.keys() == {"self", "signed_order"}
    assert inspect.signature(SecureClient.get_balance_allowance).parameters["asset_type"].kind is inspect.Parameter.KEYWORD_ONLY
    assert inspect.signature(SecureClient.get_order_book).parameters["token_id"].kind is inspect.Parameter.KEYWORD_ONLY
    assert AcceptedOrder.__annotations__["status"]
    assert RejectedOrder.__annotations__["code"]
    assert BalanceAllowance.__annotations__
    adapter = gate_b_mod._ProductionSdkMutationTransport(object())
    with pytest.raises(GatewayError, match="GATE_C_REQUIRED"):
        adapter.post_order(object())


def test_arm_is_single_use_head_bound_and_restart_disabled(tmp_path: Path) -> None:
    """The restart and constructor gates remain closed without a TTY receipt."""
    test_a3_cannot_be_rehydrated_from_restart(tmp_path)
    with pytest.raises(GatewayError, match="QUALIFICATION_REQUIRES_TTY"):
        from src.execution_gateway.gate_c import GateCStrategyQualification

        GateCStrategyQualification.issue(
            repository_head="abcdef1",
            binding=object(),
            assessment=object(),
            cost_model=object(),
            paper_store_path=tmp_path / "paper.sqlite3",
            operator_nonce="nonce",
            issued_at_ns=1,
            operator_is_tty=False,
        )


def test_gate_c_rejects_research_paper_binding_and_store(tmp_path: Path, monkeypatch) -> None:
    from src.execution_gateway.gate_c import (
        QUALIFICATION_VALIDITY_MINUTES,
        GateCStrategyQualification,
    )

    model, _experiment, _evidence, _trace, _window, assessment, qualified = edge_stack()
    repository_head = "a" * 40
    monkeypatch.setattr(gate_c_mod, "runtime_repository_identity", lambda: (Path.cwd(), repository_head))
    issued_at_ns = 1
    valid_until_ns = issued_at_ns + QUALIFICATION_VALIDITY_MINUTES * 60_000_000_000
    paper_store_head = "paperhead:sha256:" + "b" * 64
    paper_session_id = "papersession:sha256:" + "c" * 64
    preimage = {
        "repository_head": repository_head,
        "binding_id": qualified.binding_id,
        "assessment_id": assessment.assessment_id,
        "cost_model_id": model.cost_model_id,
        "paper_store_head": paper_store_head,
        "paper_session_id": paper_session_id,
        "paper_reconciliation_state": "HEALTHY",
        "operator_nonce": "synthetic-test-nonce",
        "issued_at_ns": issued_at_ns,
        "valid_until_ns": valid_until_ns,
        "issued_interactively": True,
    }
    qualification = GateCStrategyQualification(
        _id("gatecqualification:sha256:", preimage), repository_head, qualified,
        assessment, model, paper_store_head, paper_session_id, "HEALTHY",
        "synthetic-test-nonce", issued_at_ns, valid_until_ns, True,
    )
    qualification.validate(now_ns=1)

    research_path = tmp_path / "research.sqlite3"
    with PaperStore(research_path, create=True) as store:
        research_engine = PaperEngine.create_research(
            store,
            _research_binding(),
            generous_limits(),
            session_label="research",
            created_time_ns=100,
        )
        research_head = store.current_head()
        assert research_head is not None
        research_session_id = research_engine.state.session_id
    research = _research_binding()
    research_preimage = dict(preimage)
    research_preimage.update({
        "binding_id": research.binding_id,
        "paper_store_head": research_head.last_event_hash,
        "paper_session_id": research_session_id,
    })
    research_qualification = GateCStrategyQualification(
        _id("gatecqualification:sha256:", research_preimage), repository_head,
        research,  # type: ignore[arg-type]
        assessment, model, research_head.last_event_hash, research_session_id,
        "HEALTHY", "synthetic-test-nonce", issued_at_ns, valid_until_ns, True,
    )
    with pytest.raises(GatewayError, match="QUALIFICATION_INVALID"):
        research_qualification.validate(now_ns=1)


def test_access_identity_binding_and_market_fail_closed() -> None:
    blocked = GateCGeoblockProof.from_response({"blocked": True}, observed_time_ns=100)
    with pytest.raises(GatewayError, match="ACCESS_NOT_ELIGIBLE"):
        blocked.validate(now_ns=100, require_pass=True)
    values = dict(
        market_id="market-a", condition_id="condition-a", token_id="token-a",
        observed_time_ns=100, valid_until_ns=200,
    )
    with pytest.raises(GatewayError, match="MARKET_NOT_ELIGIBLE"):
        GateCMarketMetadata(**values, neg_risk=True).validate(now_ns=100)
    with pytest.raises(GatewayError, match="MARKET_METADATA_STALE"):
        GateCMarketMetadata(**values).validate(now_ns=201)


def test_every_live_risk_cap_and_reduce_only_boundary() -> None:
    envelope = CanaryRiskEnvelope()
    envelope.validate()
    assert envelope.max_active_markets == 1
    assert envelope.max_simultaneous_open_orders == 1
    assert envelope.max_create_attempts_per_session == 1
    with pytest.raises(GatewayError, match="RISK_ENVELOPE_INVALID"):
        replace(envelope, max_per_order_committed_pusd="10.01").validate()
    with pytest.raises(GatewayError, match="RECEIPT_INVALID"):
        _receipt_for_evidence(capital_at_risk_pusd="10.01").validate(now_ns=100)
    session = object.__new__(GateCSession)
    session._gateway = SimpleNamespace(
        state=SimpleNamespace(gate_c_checkpoint={})
    )
    snapshot = {
        "collateral_balance": "10", "gross_exposure_pusd": "1",
        "market_exposure_pusd": "1", "committed_exposure_pusd": "1",
        "realized_loss_pusd": "0", "drawdown_pusd": "0",
        "cumulative_loss_pusd": "0", "active_markets": 1,
        "open_orders": 0, "position_quantity": "1",
    }
    with pytest.raises(GatewayError, match="OVERSELL_FORBIDDEN"):
        session._risk_check(
            side="SELL", quantity=Decimal("1.01"), notional=Decimal("0.5"),
            snapshot=snapshot, reduce_only=True,
        )
    session._risk_check(
        side="SELL", quantity=Decimal("1"), notional=Decimal("0.5"),
        snapshot=snapshot, reduce_only=True,
    )
    buy_snapshot = {
        **snapshot,
        "allowance_by_exchange": {"exchange": "10"},
        "realized_loss_pusd": "0.01",
        "active_markets": 0,
        "market_exposure_pusd": "0",
    }
    session._market = GateCMarketMetadata(
        "market-a", "condition-a", "token-a", observed_time_ns=1,
        valid_until_ns=2,
    )
    with pytest.raises(GatewayError, match="RISK_LIMIT_EXCEEDED"):
        session._risk_check(
            side="BUY", quantity=Decimal("10"), notional=Decimal("5"),
            snapshot=buy_snapshot, reduce_only=False,
        )


def _synthetic_session(response: object) -> tuple[GateCSession, object, object]:
    order_identity = "preparedorder:sha256:" + "1" * 64
    prepared = SimpleNamespace(
        order_identity=order_identity, token_id="token-a", market_id="market-a",
        condition_id="condition-a", side="BUY", post_only=False, expiration=None,
        quantity="2", limit_price="0.5",
        would_submit={"asset_id": "token-a"},
    )
    checkpoint = {
        "armed": True, "halted": False,
        "arm_receipt_id": "gatecarm:sha256:" + "2" * 64,
        "token_id": "token-a", "create_attempt_count": 0,
    }
    state = SimpleNamespace(
        authority_state="A3_RESTRICTED_LIVE", gate_c_checkpoint=checkpoint,
        prepared_orders=(prepared,), last_event_time_ns=10,
        venue_open_order_ids=(), reconciliation_state="HEALTHY",
    )

    class Gateway:
        head = "gatewayjournal:sha256:" + "3" * 64

        def __init__(self) -> None:
            self.state = state
            self.events: list[tuple[str, dict[str, object]]] = []

        def record_gate_c_event(self, event_type: str, value: object, **kwargs: object) -> None:
            mapping = dict(value)  # type: ignore[arg-type]
            self.events.append((event_type, mapping))
            self.state.gate_c_checkpoint = mapping
            self.state.authority_state = mapping.get(
                "authority_state", self.state.authority_state
            )
            self.state.reconciliation_state = mapping.get(
                "reconciliation_state", self.state.reconciliation_state
            )
            self.state.last_event_time_ns = int(mapping["last_event_time_ns"])

    class Transport:
        def __init__(self) -> None:
            self.transmit_count = 0

        def build(self, **kwargs: object) -> object:
            self.build_kwargs = kwargs
            return SignedOrder(
                builder="0x" + "0" * 40, expiration=0,
                maker="0x" + "2" * 40, maker_amount=1_000_000,
                metadata="0x", order_type="GTC", salt=7, side="BUY",
                signature="0xsynthetic", signature_type=3,
                signer="0x" + "1" * 40, taker_amount=2_000_000,
                timestamp=99, token_id="token-a", post_only=False,
            )

        def transmit(self, signed: object) -> object:
            self.transmit_count += 1
            return response

    transport = Transport()

    class GateB:
        def gate_c_transport(self, permit: object) -> object:
            return transport

        def account_snapshot(self) -> dict[str, object]:
            return {
                "collateral_balance": "10", "open_orders": 0,
                "account_trades": 0, "positions": 0,
                "allowance_by_exchange": {"exchange": "10"},
                "position_quantities": {}, "market_exposures_pusd": {},
                "gross_exposure_pusd": "0", "committed_exposure_pusd": "0",
                "realized_loss_pusd": "0", "drawdown_pusd": "0",
                "cumulative_loss_pusd": "0", "active_markets": 0,
            }

    session = object.__new__(GateCSession)
    session._gateway = Gateway()
    session._gate_b = GateB()
    session._qualification = SimpleNamespace(
        qualification_id="gatecqualification:sha256:" + "4" * 64,
        binding=SimpleNamespace(binding_id="paperbinding:sha256:" + "5" * 64),
    )
    session._arm_receipt = SimpleNamespace(
        arm_receipt_id=checkpoint["arm_receipt_id"], repository_head="abcdef1",
        public_signer="0x" + "1" * 40, public_wallet="0x" + "2" * 40,
        issued_at_ns=100, validate=lambda now_ns=None: None,
    )
    session._market = GateCMarketMetadata(
        "market-a", "condition-a", "token-a", observed_time_ns=100,
        valid_until_ns=200,
    )
    session._risk = CanaryRiskEnvelope()
    return session, session._gateway, transport


def test_create_started_before_exactly_one_post_and_never_retries() -> None:
    response = AcceptedOrder(
        order_id="venue-order-a", status="matched", making_amount=Decimal("1"),
        taking_amount=Decimal("0.5"), trade_ids=(), transactions_hashes=(),
    )
    session, gateway, transport = _synthetic_session(response)
    receipt = session.create_limit_order(
        price="0.5", size="2", event_time_ns=100,
        order_identity="preparedorder:sha256:" + "1" * 64,
    )
    assert [event for event, _value in gateway.events] == [
        "GATE_C_CREATE_STARTED", "GATE_C_CREATE_OUTCOME"
    ]
    assert transport.transmit_count == 1
    assert receipt.reconciliation_state == "REQUIRED"
    assert receipt.residual_position_state == "UNKNOWN"
    assert receipt.halted is True
    started = gateway.events[0][1]
    expected = {
        "repository_head": "abcdef1",
        "store_head": "gatewayjournal:sha256:" + "3" * 64,
        "public_signer": "0x" + "1" * 40,
        "public_wallet": "0x" + "2" * 40,
        "qualification_id": "gatecqualification:sha256:" + "4" * 64,
        "strategy_binding_id": "paperbinding:sha256:" + "5" * 64,
        "order_identity": "preparedorder:sha256:" + "1" * 64,
        "asset_id": "token-a", "price": "0.5", "size": "2", "side": "BUY",
        "post_only": False, "expiration": None, "order_type": "LIMIT",
        "time_in_force": "GTC", "market_id": "market-a",
        "condition_id": "condition-a", "arm_receipt_id": "gatecarm:sha256:" + "2" * 64,
        "risk_envelope_id": CanaryRiskEnvelope().envelope_id,
        "reduce_only": False, "builder_code": None, "sequence": 1,
        "signed_order": {
            "builder": "0x" + "0" * 40, "expiration": 0,
            "maker": "0x" + "2" * 40, "maker_amount": 1_000_000,
            "metadata": "0x", "order_type": "GTC", "salt": 7,
            "side": "BUY", "signature_type": 3,
            "signer": "0x" + "1" * 40, "taker_amount": 2_000_000,
            "timestamp": 99, "token_id": "token-a", "post_only": False,
        },
    }
    assert started["mutation_identity"] == _id("gatecattempt:sha256:", expected)


def test_exact_order_response_classification() -> None:
    session = object.__new__(GateCSession)
    accepted = AcceptedOrder(
        order_id="venue-order-a", status="live", making_amount=Decimal("1"),
        taking_amount=Decimal("0.5"), trade_ids=(), transactions_hashes=(),
    )
    rejected = RejectedOrder(code="unmatched", message="not matched")
    assert session._classify(accepted) == ("DEFINITIVE_ACCEPTED", "live", "venue-order-a")
    assert session._classify(rejected) == ("DEFINITIVE_REJECTED", "rejected", None)
    assert session._classify(object()) == ("AMBIGUOUS", "unknown", None)


def test_authoritative_reconciliation_and_restart_blocking(tmp_path: Path) -> None:
    test_a3_cannot_be_rehydrated_from_restart(tmp_path)
    assert "RESTART_RECONCILIATION_REQUIRED" in inspect.getsource(ProtectedExecutionGateway.open)


def test_resting_order_uses_durable_gate_b_cancel() -> None:
    source = inspect.getsource(GateCSession.cancel_resting_order)
    assert "cancel_one" in source
    assert "GATE_B_STORE_REQUIRED" not in source
    assert "order_identity" in source and "venue_order_id" in source


def _receipt_for_evidence(*, capital_at_risk_pusd: str = "0") -> GateCCanaryReceipt:
    values = dict(
        receipt_id="gatecreceipt:sha256:" + "0" * 64,
        repository_head="abcdef1",
        arm_receipt_id="gatecarm:sha256:" + "1" * 64,
        attempt_id="mutationattempt:sha256:" + "2" * 64,
        outcome="DEFINITIVE_REJECTED",
        response_status="rejected",
        venue_order_id=None,
        market_id="market-a",
        token_id="token-a",
        create_attempt_count=1,
        capital_at_risk_pusd=capital_at_risk_pusd,
        capital_committed_pusd="0",
        reconciliation_state="HEALTHY",
        residual_position_state="NONE",
        halted=True,
        issued_at_ns=100,
        valid_until_ns=100 + 10 * 60_000_000_000,
    )
    provisional = GateCCanaryReceipt(**values)
    values["receipt_id"] = _id(
        "gatecreceipt:sha256:",
        {key: value for key, value in asdict(provisional).items() if key != "receipt_id"},
    )
    return GateCCanaryReceipt(**values)


def test_canary_receipt_and_every_output_are_sanitized() -> None:
    receipt = _receipt_for_evidence()
    receipt.validate(now_ns=100)
    serialized = json.dumps(receipt.to_public_mapping(), sort_keys=True)
    assert "private_key" not in serialized
    assert "api_key" not in serialized
    assert "secret" not in serialized.lower()
    assert receipt.receipt_id == _id(
        "gatecreceipt:sha256:",
        {key: value for key, value in asdict(receipt).items() if key != "receipt_id"},
    )


def test_runtime_head_is_derived_and_dirty_or_unavailable_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    results = iter((
        SimpleNamespace(stdout=str(tmp_path) + "\n"),
        SimpleNamespace(stdout="a" * 40 + "\n"),
        SimpleNamespace(stdout=""),
    ))
    monkeypatch.setattr(gate_c_mod.subprocess, "run", lambda *_a, **_k: next(results))
    assert runtime_repository_identity(cwd=tmp_path) == (tmp_path.resolve(), "a" * 40)

    dirty = iter((
        SimpleNamespace(stdout=str(tmp_path) + "\n"),
        SimpleNamespace(stdout="b" * 40 + "\n"),
        SimpleNamespace(stdout=" M file.py\n"),
    ))
    monkeypatch.setattr(gate_c_mod.subprocess, "run", lambda *_a, **_k: next(dirty))
    with pytest.raises(GatewayError, match="HEAD_BINDING_INVALID"):
        runtime_repository_identity(cwd=tmp_path)
    monkeypatch.setattr(
        gate_c_mod.subprocess, "run",
        lambda *_a, **_k: (_ for _ in ()).throw(OSError("git unavailable")),
    )
    with pytest.raises(GatewayError, match="HEAD_BINDING_INVALID"):
        runtime_repository_identity(cwd=tmp_path)


def test_canonical_wallet_ledger_is_deterministic_and_wallet_specific(tmp_path: Path) -> None:
    first = canonical_gateway_store_path(tmp_path, "0x" + "1" * 40)
    assert first == canonical_gateway_store_path(tmp_path, "0x" + "1" * 40)
    assert first != canonical_gateway_store_path(tmp_path, "0x" + "2" * 40)
    assert first.parent == (tmp_path / "local_data" / "gate_c").resolve()


def test_risk_check_rejects_missing_state_and_preserves_durable_loss() -> None:
    session = object.__new__(GateCSession)
    session._market = GateCMarketMetadata(
        "market-a", "condition-a", "token-a", observed_time_ns=1,
        valid_until_ns=2,
    )
    checkpoint = {"realized_loss_pusd": "4", "drawdown_pusd": "0", "cumulative_loss_pusd": "0"}
    session._gateway = SimpleNamespace(
        state=SimpleNamespace(gate_c_checkpoint=checkpoint)
    )
    snapshot = {
        "collateral_balance": "10", "allowance_by_exchange": {"exchange": "10"},
        "gross_exposure_pusd": "0", "market_exposure_pusd": "0",
        "committed_exposure_pusd": "0", "realized_loss_pusd": "0",
        "drawdown_pusd": "0", "cumulative_loss_pusd": "0",
        "active_markets": 0, "open_orders": 0,
    }
    missing = dict(snapshot)
    missing.pop("cumulative_loss_pusd")
    with pytest.raises(GatewayError, match="ACCOUNT_SNAPSHOT_INVALID"):
        session._risk_check(
            side="BUY", quantity=Decimal("1"), notional=Decimal("1"),
            snapshot=missing, reduce_only=False,
        )
    with pytest.raises(GatewayError, match="RISK_LIMIT_EXCEEDED"):
        session._risk_check(
            side="BUY", quantity=Decimal("2"), notional=Decimal("2"),
            snapshot=snapshot, reduce_only=False,
        )


def test_ambiguous_create_runs_three_read_probes_without_resend(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session, gateway, transport = _synthetic_session(object())
    receipt = session.create_limit_order(
        price="0.5", size="2", event_time_ns=100,
        order_identity="preparedorder:sha256:" + "1" * 64,
    )
    probes: list[int] = []

    def adapter(_issuer: object, *, observed_time_ns: int, **_kwargs: object) -> object:
        probes.append(observed_time_ns)
        return object()

    session._gate_b.gate_c_reconciliation_adapter = adapter
    monkeypatch.setattr(
        GateCSession, "reconcile",
        lambda *_a, **_k: (_ for _ in ()).throw(GatewayError("READ_AMBIGUOUS")),
    )
    proof = GateCGeoblockProof.from_response({"blocked": False}, observed_time_ns=102)
    terminal = session.reconcile_bounded(geoblock=proof, event_time_ns=102)
    assert receipt.outcome == "AMBIGUOUS"
    assert probes == [103, 104, 105]
    assert transport.transmit_count == 1
    assert terminal["reconciliation_state"] == "BLOCKED"
    assert terminal["halted"] is True
    assert gateway.state.gate_c_checkpoint["reconciliation_probe_count"] == 3


def test_real_gateway_store_persists_ambiguous_mutation_without_resend(
    tmp_path: Path,
) -> None:
    gateway = _ready_gateway(tmp_path)
    prepared = _prepare(gateway, tmp_path)
    armed = {
        "authority_state": "A3_RESTRICTED_LIVE", "disable_reason": "",
        "armed": True, "halted": False,
        "arm_receipt_id": "gatecarm:sha256:" + "2" * 64,
        "qualification_id": "gatecqualification:sha256:" + "4" * 64,
        "attempt_id": None, "create_outcome": None, "response_status": None,
        "venue_order_id": None, "market_id": prepared.market_id,
        "condition_id": prepared.condition_id, "token_id": prepared.token_id,
        "strategy_label": "fixture", "create_attempt_count": 0,
        "capital_at_risk_pusd": "0", "capital_committed_pusd": "0",
        "realized_loss_pusd": "0", "drawdown_pusd": "0",
        "cumulative_loss_pusd": "0", "reconciliation_state": "HEALTHY",
        "residual_position_state": "NONE", "access_state": "ELIGIBLE",
        "receipt_id": None, "last_event_time_ns": 30,
    }
    gateway.record_gate_c_event(
        "GATE_C_ARMED", armed, issuer=_GATE_C_EVENT_ISSUER,
        event_time_ns=30,
    )

    class Transport:
        transmit_count = 0

        @staticmethod
        def build(**_kwargs: object) -> SignedOrder:
            return SignedOrder(
                builder="0x" + "0" * 40, expiration=0,
                maker="0x" + "2" * 40, maker_amount=500_000,
                metadata="0x", order_type="GTC", salt=7, side="BUY",
                signature="0xsynthetic", signature_type=3,
                signer="0x" + "1" * 40, taker_amount=1_000_000,
                timestamp=99, token_id=prepared.token_id, post_only=False,
            )

        def transmit(self, _signed: object) -> object:
            self.transmit_count += 1
            return object()

    transport = Transport()

    class GateB:
        @staticmethod
        def gate_c_transport(_permit: object) -> Transport:
            return transport

        @staticmethod
        def account_snapshot() -> dict[str, object]:
            return {
                "collateral_balance": "10", "open_orders": 0,
                "account_trades": 0, "positions": 0,
                "allowance_by_exchange": {"exchange": "10"},
                "position_quantities": {}, "market_exposures_pusd": {},
                "gross_exposure_pusd": "0", "committed_exposure_pusd": "0",
                "realized_loss_pusd": "0", "drawdown_pusd": "0",
                "cumulative_loss_pusd": "0", "active_markets": 0,
            }

    session = object.__new__(GateCSession)
    session._gateway = gateway
    session._gate_b = GateB()
    session._qualification = SimpleNamespace(
        qualification_id=armed["qualification_id"],
        binding=SimpleNamespace(binding_id="paperbinding:sha256:" + "5" * 64),
    )
    session._arm_receipt = SimpleNamespace(
        arm_receipt_id=armed["arm_receipt_id"], repository_head="abcdef1",
        public_signer="0x" + "1" * 40, public_wallet="0x" + "2" * 40,
        issued_at_ns=30, validate=lambda now_ns=None: None,
    )
    session._market = GateCMarketMetadata(
        prepared.market_id, prepared.condition_id, prepared.token_id,
        observed_time_ns=30, valid_until_ns=200,
    )
    session._risk = CanaryRiskEnvelope()
    receipt = session.create_limit_order(
        price="0.5", size="1", event_time_ns=31,
        order_identity=prepared.order_identity,
    )
    assert receipt.outcome == "AMBIGUOUS"
    assert transport.transmit_count == 1
    assert len(gateway.state.mutation_attempts) == 1
    assert gateway.state.mutation_attempts[0].outcome == "AMBIGUOUS"
    gateway.close()


def test_foreground_operator_orders_arm_create_reconcile_and_terminal_evidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Tty:
        @staticmethod
        def isatty() -> bool:
            return True

    monkeypatch.setattr("src.execution_gateway.gate_c_operator.sys.stdin", Tty())
    calls: list[str] = []

    class Receipt:
        outcome = "AMBIGUOUS"

        @staticmethod
        def to_public_mapping() -> dict[str, object]:
            return {"outcome": "AMBIGUOUS"}

    class Session:
        arm_receipt = SimpleNamespace(
            to_public_mapping=lambda: {"arm_receipt_id": "arm"}
        )

        def create_limit_order(self, **_kwargs: object) -> Receipt:
            calls.append("create")
            return Receipt()

        def reconcile_bounded(self, **_kwargs: object) -> None:
            calls.append("reconcile")

        def cockpit_projection(self) -> dict[str, object]:
            calls.append("terminal")
            return {"halted": True, "reconciliation_state": "BLOCKED"}

    operator = GateCOperator(SimpleNamespace())  # type: ignore[arg-type]
    monkeypatch.setattr(
        operator, "arm",
        lambda *_a, **_k: calls.append("arm") or Session(),
    )
    evidence = operator.run_one_shot(
        SimpleNamespace(), SimpleNamespace(),  # type: ignore[arg-type]
        market=SimpleNamespace(), geoblock=SimpleNamespace(),
        price="0.5", size="2", side="BUY", post_only=False,
        expiration=None, reduce_only=False,
        order_identity="preparedorder:sha256:" + "1" * 64, now_ns=100,
    )
    assert calls == ["arm", "create", "reconcile", "terminal"]
    assert evidence["terminal"] == {
        "halted": True, "reconciliation_state": "BLOCKED"
    }


def test_foreground_operator_reconciles_restart_before_arm() -> None:
    attempt = SimpleNamespace(
        operation="CREATE", venue_order_id="venue-a",
        order_identity="preparedorder:sha256:" + "1" * 64,
    )
    state = SimpleNamespace(
        mutation_attempts=(attempt,), reconciliation_state="REQUIRED"
    )

    class Gateway:
        def __init__(self) -> None:
            self.state = state
            self.adapter = None

        def reconcile(self, *, adapter: object, event_time_ns: int) -> None:
            self.adapter = adapter
            assert event_time_ns == 100
            self.state.reconciliation_state = "HEALTHY"

    class GateB:
        def gate_c_reconciliation_adapter(self, issuer: object, **kwargs: object) -> object:
            assert issuer is gate_b_mod._GATE_C_ISSUER
            assert kwargs["order_identity_by_venue_id"] == {
                "venue-a": "preparedorder:sha256:" + "1" * 64
            }
            return "official-adapter"

    gateway = Gateway()
    operator = GateCOperator(gateway)  # type: ignore[arg-type]
    operator.reconcile_before_arm(
        GateB(),  # type: ignore[arg-type]
        geoblock=GateCGeoblockProof.from_response(
            {"blocked": False}, observed_time_ns=100
        ),
        now_ns=100,
    )
    assert gateway.adapter == "official-adapter"


# ---------------------------------------------------------------------------
# S10-LIVE-ORCH-01 (R003): one-transmit classification, trade status, cancel recovery
# ---------------------------------------------------------------------------


def test_unknown_create_rejection_is_ambiguous_in_historical_and_live_orch_paths() -> None:
    """Defect F: RejectedOrder code "unknown" never proves non-acceptance."""
    from src.execution_gateway.gate_c import classify_live_orch_create_response

    session = object.__new__(GateCSession)
    unknown = RejectedOrder(code="unknown", message="unrecognized venue error")
    assert session._classify(unknown) == ("AMBIGUOUS", "unknown", None)
    assert classify_live_orch_create_response(unknown)["outcome"] == "AMBIGUOUS"
    for code in ("unmatched", "market_not_ready", "not_enough_balance", "invalid_nonce",
                 "invalid_expiration", "post_only_would_cross", "post_only_mode",
                 "fok_not_filled", "fak_not_filled"):
        result = classify_live_orch_create_response(RejectedOrder(code=code, message="x"))
        assert result["outcome"] == "DEFINITIVE_REJECTED", code
    accepted = classify_live_orch_create_response(AcceptedOrder(
        order_id="0x" + "1" * 64, status="matched", making_amount=Decimal("4.16"),
        taking_amount=Decimal("8"), trade_ids=("trade-2", "trade-1"), transactions_hashes=()))
    assert (accepted["outcome"], accepted["response_status"]) == ("DEFINITIVE_ACCEPTED", "matched")
    assert accepted["trade_ids"] == ["trade-1", "trade-2"]
    assert accepted["making_amount"] == "4.16" and accepted["taking_amount"] == "8"
    garbled = AcceptedOrder(order_id="bad id with spaces", status="live", making_amount=Decimal("0"),
                            taking_amount=Decimal("0"), trade_ids=(), transactions_hashes=())
    assert classify_live_orch_create_response(garbled)["outcome"] == "AMBIGUOUS"


def _live_orch_boundary(tmp_path: Path, client):
    from src.execution_gateway.gate_b import GateBIdentityPolicy, GateBSecretLease, WalletSessionLock
    from src.execution_gateway.gate_c import LiveOrchMutationBoundary
    from src.execution_gateway.gateway import _LIVE_ORCH_EVENT_ISSUER

    gateway = ProtectedExecutionGateway.create(tmp_path / "liveorch.sqlite3", created_time_ns=1)
    lock = WalletSessionLock(tmp_path, client.wallet).acquire()

    class _Provider:
        def acquire(self):
            return GateBSecretLease("synthetic-test-key-material")

    session = gate_b_mod.GateBSession.authenticate(
        _Provider(),
        GateBIdentityPolicy(expected_signer=client.signer, expected_wallet=client.wallet),
        client_factory=lambda key, wallet: client, gateway=gateway, wallet_lock=lock,
    )
    with pytest.raises(GatewayError, match="LIVE_ORCH_REQUIRED"):
        LiveOrchMutationBoundary(gateway, session, issuer=object())
    return gateway, lock, session, LiveOrchMutationBoundary(gateway, session, issuer=_LIVE_ORCH_EVENT_ISSUER)


def _episode_for(prepared, *, token_id):
    from src.execution_gateway.gateway import live_orch_episode_id

    binding = {
        "exploratory_permit_id": "exploratorygatecpermit:sha256:" + "1" * 64,
        "execution_intent_id": "executionintent:sha256:" + "2" * 64,
        "strategy_version_id": "strategyversion:sha256:" + "3" * 64,
        "execution_rule_sha256": "executionrule:sha256:" + "4" * 64,
        "gamma_market_id": "516710", "condition_id": "0x" + "ab" * 32, "token_id": token_id,
        "side": "BUY", "execution_style": "PASSIVE_MAKER", "order_type": "GTC",
        "requested_shares": "8", "price_limit": "0.51", "post_only": True,
        "gtd_expiration_unix_s": None, "authorized_order_notional_usd": "4.08",
        "release_sha": "c" * 40, "public_signer": "0x" + "a" * 40, "public_wallet": "0x" + "b" * 40,
    }
    admission = {
        "admission_id": "liveorchadmission:sha256:" + "5" * 64, "decision": "ADMITTED",
        "venue_snapshot_id": "executionsnapshot:sha256:" + "6" * 64,
        "execution_feasibility_assessment_id": "executionfeasibility:sha256:" + "7" * 64,
        "feasibility_status": "FEASIBLE", "host_currentness_id": "hostcurrentness:sha256:" + "8" * 64,
        "geoblock_proof_id": "geoblockproof:sha256:" + "9" * 64, "geoblock_observed_time_ns": 1,
        "account_truth_id": "liveorchaccount:sha256:" + "a" * 64, "collateral_before_usd": "100",
        "current_committed_usd": "0", "principal_notional_usd": "4.08",
        "worst_case_fee_reserve_usd": "0", "worst_case_commitment_usd": "4.08",
        "projected_free_collateral_usd": "95.92", "observed_realized_pnl_loss_usd": "0",
        "observed_position_pnl_drawdown_usd": "0", "observed_cumulative_canary_loss_usd": "0",
        "signed_order_id": prepared.economics.signed_order_id,
        "signed_maker_amount": prepared.economics.maker_amount,
        "signed_taker_amount": prepared.economics.taker_amount, "admitted_time_ns": 5,
    }
    return {
        "episode_id": live_orch_episode_id(binding, admission["admission_id"]), "state": "ADMITTED",
        "binding": binding, "admission": admission, "create": None, "cancel_attempts": [],
        "reconciliation": {"order_live": None, "open_remainder_shares": "0", "trades": [],
                           "fee_state": "NOT_REQUIRED", "actual_fee_usd": None,
                           "block_reason": None, "last_reconciled_time_ns": None},
    }


class _LiveOrchFakeClient:
    signer, wallet, wallet_type = "0x" + "a" * 40, "0x" + "b" * 40, "DEPOSIT_WALLET"

    def __init__(self, response, cancel=None):
        self.environment = SimpleNamespace(name="production")
        self._ctx = SimpleNamespace(signer_type="OWNER", environment_config=SimpleNamespace(chain_id=137))
        self.response = response
        self.cancel = cancel
        self.posts = []
        self.cancels = []

    def create_limit_order(self, *, asset_id=None, token_id=None, price, size, side,
                           post_only=False, expiration=None, builder_code=None):
        return SignedOrder(
            builder="0x" + "0" * 64, expiration=0, maker=self.wallet, maker_amount=4_080_000,
            metadata="0x" + "0" * 64, order_type="GTC", salt=1, side="BUY", signature="0xsig",
            signature_type=3, signer=self.wallet, taker_amount=8_000_000,
            timestamp=1, token_id=asset_id or token_id, post_only=post_only,
        )

    def post_order(self, signed):
        self.posts.append(signed)
        if isinstance(self.response, BaseException):
            raise self.response
        return self.response

    def cancel_order(self, *, order_id):
        self.cancels.append(order_id)
        if self.cancel is None:
            raise TimeoutError("lost")
        return self.cancel


def _passive_spec(token_id):
    from src.execution_gateway.gate_c import LiveOrchOrderSpec

    return LiveOrchOrderSpec(
        token_id=token_id, execution_style="PASSIVE_MAKER", order_type="GTC", requested_shares="8",
        price_limit="0.51", gtd_expiration_unix_s=None, principal_notional_usd="4.08",
        worst_case_commitment_usd="4.08", tick_size="0.01",
    )


def test_live_orch_boundary_single_transmit_and_trade_ids_retained(tmp_path: Path) -> None:
    token = "71321045679252212594626385532706912750332728571942532289631379312455583992563"
    response = AcceptedOrder(order_id="0x" + "c" * 64, status="matched",
                             making_amount=Decimal("4.08"), taking_amount=Decimal("8"),
                             trade_ids=("trade-x",), transactions_hashes=())
    client = _LiveOrchFakeClient(response)
    gateway, lock, session, boundary = _live_orch_boundary(tmp_path, client)
    try:
        prepared = boundary.prepare(_passive_spec(token), attempt_seed="permit-anchor")
        assert client.posts == []  # local construction never posts
        episode = _episode_for(prepared, token_id=token)
        with pytest.raises(GatewayError, match="LIVE_ORCH_ADMISSION_INVALID"):
            boundary.admit_and_transmit(prepared, {**episode, "state": "CREATE_STARTED"}, now_ns=10)
        outcome = boundary.admit_and_transmit(prepared, episode, now_ns=10)
        assert outcome["state"] == "CREATE_ACCEPTED" and len(client.posts) == 1
        record = gateway.live_orch_checkpoint()["episodes"][0]
        assert record["create"]["trade_ids"] == ["trade-x"]
        assert record["create"]["venue_order_id"] == "0x" + "c" * 64
        with pytest.raises(GatewayError, match="GATE_C_REQUIRED"):
            boundary.admit_and_transmit(prepared, episode, now_ns=11)
        assert len(client.posts) == 1
    finally:
        session.close()
        lock.close()
        gateway.close()


def test_live_orch_boundary_transport_failure_is_ambiguous_never_retried(tmp_path: Path) -> None:
    token = "71321045679252212594626385532706912750332728571942532289631379312455583992563"
    client = _LiveOrchFakeClient(ConnectionResetError("reset by peer"))
    gateway, lock, session, boundary = _live_orch_boundary(tmp_path, client)
    try:
        prepared = boundary.prepare(_passive_spec(token), attempt_seed="permit-anchor")
        outcome = boundary.admit_and_transmit(prepared, _episode_for(prepared, token_id=token), now_ns=10)
        assert outcome["state"] == "CREATE_AMBIGUOUS" and outcome["venue_order_id"] is None
        assert len(client.posts) == 1
    finally:
        session.close()
        lock.close()
        gateway.close()


def test_live_orch_cancel_recovery_uses_new_identity_each_round(tmp_path: Path) -> None:
    token = "71321045679252212594626385532706912750332728571942532289631379312455583992563"
    response = AcceptedOrder(order_id="0x" + "d" * 64, status="live", making_amount=Decimal("0"),
                             taking_amount=Decimal("0"), trade_ids=(), transactions_hashes=())
    client = _LiveOrchFakeClient(response)
    gateway, lock, session, boundary = _live_orch_boundary(tmp_path, client)
    try:
        prepared = boundary.prepare(_passive_spec(token), attempt_seed="permit-anchor")
        episode = _episode_for(prepared, token_id=token)
        boundary.admit_and_transmit(prepared, episode, now_ns=10)
        assert boundary.cancel(episode["episode_id"], now_ns=20) == "AMBIGUOUS"
        client.cancel = SimpleNamespace(canceled=("0x" + "d" * 64,), not_canceled={})
        assert boundary.cancel(episode["episode_id"], now_ns=30) == "DEFINITIVE_ACCEPTED"
        attempts = gateway.live_orch_checkpoint()["episodes"][0]["cancel_attempts"]
        assert [a["sequence"] for a in attempts] == [1, 2]
        assert attempts[0]["cancel_attempt_id"] != attempts[1]["cancel_attempt_id"]
        assert [a["result"] for a in attempts] == ["AMBIGUOUS", "DEFINITIVE_ACCEPTED"]
        assert client.cancels == ["0x" + "d" * 64] * 2
        events = [e.event_type for e in gateway._store.load()[2] if e.event_type.startswith("LIVE_ORCH_")]
        assert events == ["LIVE_ORCH_ADMITTED", "LIVE_ORCH_CREATE_STARTED", "LIVE_ORCH_CREATE_OUTCOME",
                          "LIVE_ORCH_CANCEL_STARTED", "LIVE_ORCH_CANCEL_OUTCOME",
                          "LIVE_ORCH_CANCEL_STARTED", "LIVE_ORCH_CANCEL_OUTCOME"]
    finally:
        session.close()
        lock.close()
        gateway.close()


def test_live_orch_gate_c_keeps_market_condition_and_token_distinct() -> None:
    source = inspect.getsource(gate_c_mod.LiveOrchMutationBoundary)
    assert "condition_id" not in source  # the boundary never substitutes market identity
    spec_fields = set(gate_c_mod.LiveOrchOrderSpec.__dataclass_fields__)
    assert "token_id" in spec_fields and "market_id" not in spec_fields


# ---------------------------------------------------------------------------
# S10-LIVE-CANARY-UA-01: fixed public User-Agent on the official geoblock GET.
# ---------------------------------------------------------------------------

_UA_01_USER_AGENT = "wp169-public-market-truth/1.0"


class _UA01Response:
    def __init__(self, payload: bytes) -> None:
        self.status = 200
        self.payload = payload
        self.read_sizes: list[int] = []

    def read(self, size: int) -> bytes:
        self.read_sizes.append(size)
        return self.payload[:size]

    def __enter__(self) -> "_UA01Response":
        return self

    def __exit__(self, *_exc: object) -> None:
        return None


def _ua_01_effective_headers(request) -> dict[str, str]:
    """Headers urllib would actually send after its default-header pass (offline)."""
    import urllib.request

    handler = urllib.request.HTTPSHandler()
    handler.parent = urllib.request.build_opener()  # carries the implicit Python-urllib UA
    prepared = handler.do_request_(request)
    items = (*prepared.headers.items(), *prepared.unredirected_hdrs.items())
    return {key.lower(): value for key, value in items}


def test_s10_live_canary_ua_01_geoblock_request_sends_fixed_user_agent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list = []
    response = _UA01Response(json.dumps({"blocked": False, "country": "XX"}).encode())

    def fake_urlopen(request, timeout):
        calls.append((request, timeout))
        return response

    monkeypatch.setattr(gate_c_mod, "urlopen", fake_urlopen)
    proof = gate_c_mod.query_geoblock(now_ns=1_000)
    assert type(proof) is GateCGeoblockProof and proof.blocked is False
    proof.validate(now_ns=1_000, require_pass=True)
    assert len(calls) == 1
    request, timeout = calls[0]
    assert request.full_url == gate_c_mod._GEOBLOCK_URL == "https://polymarket.com/api/geoblock"
    assert request.get_method() == "GET" and request.data is None and timeout == 5
    assert dict(request.header_items()) == {
        "Accept": "application/json",
        "User-agent": _UA_01_USER_AGENT,
    }
    assert response.read_sizes == [64 * 1024]
    sent = _ua_01_effective_headers(request)
    assert sent["user-agent"] == _UA_01_USER_AGENT
    assert "authorization" not in sent and "cookie" not in sent


def test_s10_live_canary_ua_01_geoblock_has_no_implicit_or_overridable_headers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import urllib.request

    # Negative control: the pre-repair request shape would carry Python's implicit UA.
    bare = urllib.request.Request(gate_c_mod._GEOBLOCK_URL, method="GET",
                                  headers={"Accept": "application/json"})
    assert _ua_01_effective_headers(bare)["user-agent"].startswith("Python-urllib/")
    # No caller header surface; the endpoint stays fixed.
    assert set(inspect.signature(gate_c_mod.query_geoblock).parameters) == {"url", "now_ns"}
    with pytest.raises(GatewayError) as excinfo:
        gate_c_mod.query_geoblock(url="https://evil.test/api/geoblock", now_ns=1)
    assert excinfo.value.code == "ACCESS_PROOF_INVALID"
    # The environment cannot inject or override headers.
    for name in ("HTTP_USER_AGENT", "USER_AGENT", "HTTP_COOKIE"):
        monkeypatch.setenv(name, "injected-value")
    calls: list = []

    def fake_urlopen(request, timeout):
        calls.append(request)
        return _UA01Response(b'{"blocked": true}')

    monkeypatch.setattr(gate_c_mod, "urlopen", fake_urlopen)
    blocked = gate_c_mod.query_geoblock(now_ns=1_000)
    assert blocked.blocked is True and len(calls) == 1
    sent = _ua_01_effective_headers(calls[0])
    assert sent["user-agent"] == _UA_01_USER_AGENT
    assert not sent["user-agent"].startswith("Python-urllib/")
    assert "injected-value" not in sent.values()
    assert "authorization" not in sent and "cookie" not in sent


# ---------------------------------------------------------------------------
# S10-ALPHA-HUNTER-PILOT-02: additive LIVE-ORCH reduce-only FOK SELL contract (R016)
# ---------------------------------------------------------------------------


def test_live_orch_reduce_only_sell_contract(tmp_path) -> None:
    from src.execution_gateway.gate_c import (
        LiveOrchSellSpec, inspect_live_orch_signed_buy, inspect_live_orch_signed_sell,
    )
    from tests.execution_gateway import test_live_orch as LO
    from tests.exploratory_gate_c import test_exploratory_gate_c as XG

    venue = LO.FakeVenue()
    wallet = LO.WALLET
    closes = "liveorchepisode:sha256:" + "1" * 64
    spec = LiveOrchSellSpec(token_id=LO.TOKEN, order_type="FOK", shares="8", min_price="0.5", tick_size="0.01",
                            closes_episode_id=closes, fee_reserve_usd="0.0666")
    signed = venue.create_market_order(token_id=LO.TOKEN, side="SELL", shares=Decimal("8"),
                                       min_price=Decimal("0.5"), order_type="FOK")
    economics = inspect_live_orch_signed_sell(signed, spec, public_wallet=wallet)
    assert (economics.maker_amount, economics.taker_amount) == (8_000_000, 4_000_000)
    other = "0x" + "c" * 40
    mismatches = {
        "SIGNED_ORDER_IDENTITY_MISMATCH": [dict(side="BUY"), dict(maker=other), dict(signer=other),
                                           dict(signature_type=2), dict(builder="0x" + "0" * 63 + "1"),
                                           dict(token_id="1")],
        "ORDER_ENCODING_UNSUPPORTED": [dict(order_type="FAK"), dict(post_only=True), dict(expiration=1),
                                       dict(maker_amount=8_000_001), dict(maker_amount=7_990_000),
                                       dict(taker_amount=3_999_999), dict(taker_amount=0)],
    }
    for code, changes in mismatches.items():
        for change in changes:
            with pytest.raises(GatewayError, match=code):
                inspect_live_orch_signed_sell(replace(signed, **change), spec, public_wallet=wallet)
    for bad in (dict(order_type="FAK"), dict(shares="8.001"), dict(shares="0"), dict(min_price="1"),
                dict(min_price="0.505"), dict(tick_size="0.02"), dict(fee_reserve_usd="-0.1"),
                dict(fee_reserve_usd="0.000001"), dict(closes_episode_id="")):
        with pytest.raises(GatewayError):
            inspect_live_orch_signed_sell(signed, replace(spec, **bad), public_wallet=wallet)
    # The BUY inspector is unchanged: a signed SELL never passes it.
    with pytest.raises(GatewayError, match="SIGNED_ORDER_IDENTITY_MISMATCH"):
        inspect_live_orch_signed_buy(signed, LO._spec(), public_wallet=wallet)

    world = XG.make_world(tmp_path / "world")

    def position(name, **fill):
        harness = LO.Harness(tmp_path / name, world)
        permit, intent = LO.make_permit(world)
        harness.venue.on_post = LO._accept_fill(**fill)
        result = LO.hunter_orchestrator(harness).canary(permit, intent)
        return harness, result.episode_id

    def sell(harness, buy_id, **permit_kw):
        permit, intent = LO.sell_permit(world, **permit_kw)
        return LO.hunter_orchestrator(harness).exit_sell(permit, intent, closes_episode_id=buy_id), permit, intent

    # Valid synthetic SELL admits once; the same permit never transmits twice.
    harness, buy_id = position("valid")
    harness.venue.on_post = lambda v, s: v.fill_sell(s, shares="8", price="0.5")
    result, permit, intent = sell(harness, buy_id)
    assert (result.status, result.create_transmits) == ("EXIT_COMPLETE", 1)
    replay = LO.hunter_orchestrator(harness).exit_sell(permit, intent, closes_episode_id=buy_id)
    assert replay.code == "PERMIT_ALREADY_CONSUMED" and replay.create_transmits == 0
    assert [p.side for p in harness.venue.posts] == ["BUY", "SELL"]
    sell_episode = harness.ledger()["episodes"][1]
    assert sell_episode["binding"]["closes_episode_id"] == buy_id and sell_episode["binding"]["side"] == "SELL"
    assert sell_episode["admission"]["worst_case_commitment_usd"] == sell_episode["admission"]["worst_case_fee_reserve_usd"]

    # Second SELL while one is non-terminal, then shares above reconciled minus pending SELL.
    harness, buy_id = position("pending")
    harness.venue.on_post = lambda v, s: v.fill_sell(s, shares="5", price="0.5", status="MINED", remaining="8")
    first, *_ = sell(harness, buy_id, shares="5")
    assert first.create_transmits == 1 and first.episode_state == "SETTLEMENT_PENDING"
    for shares in ("6", "7"):  # 8 held - 5 pending: both exceed the unreserved 3
        result, *_ = sell(harness, buy_id, shares=shares)
        assert result.status == "BLOCKED" and result.create_transmits == 0
        assert result.code in ("SETTLEMENT_NONTERMINAL", "SELL_ALREADY_PENDING")
    assert len(harness.venue.posts) == 2

    # Unconfirmed BUY trade and an open order on the token both refuse before signing.
    harness, buy_id = position("unconfirmed", status="MINED")
    result, *_ = sell(harness, buy_id)
    assert result.status == "BLOCKED" and result.create_transmits == 0 and len(harness.venue.posts) == 1
    harness, buy_id = position("open")
    harness.venue.orders[LO.oid(77)] = {"id": LO.oid(77), "price": "0.6", "size": "5", "type": "GTC",
                                        "status": "LIVE", "side": "SELL"}
    result, *_ = sell(harness, buy_id)
    assert result.status == "BLOCKED" and result.create_transmits == 0 and len(harness.venue.posts) == 1

    # Crash after a durable CREATE_STARTED SELL: replay never re-transmits; it stays ambiguous.
    harness, buy_id = position("crash")
    original = ProtectedExecutionGateway.record_live_orch_event

    def crash(self, event_type, *a, **kw):
        value = original(self, event_type, *a, **kw)
        if event_type == "LIVE_ORCH_CREATE_STARTED" and "SELL" in json.dumps(a[0] if a else kw):
            raise RuntimeError("synthetic crash")
        return value
    ProtectedExecutionGateway.record_live_orch_event = crash
    try:
        with pytest.raises(RuntimeError):
            sell(harness, buy_id)
    finally:
        ProtectedExecutionGateway.record_live_orch_event = original
    assert len(harness.venue.posts) == 1
    result, *_ = sell(harness, buy_id)
    assert result.status == "BLOCKED" and result.create_transmits == 0 and len(harness.venue.posts) == 1
    states = [e["state"] for e in harness.ledger()["episodes"]]
    assert states == ["TERMINAL_KNOWN_POSITION", "CREATE_AMBIGUOUS"]
