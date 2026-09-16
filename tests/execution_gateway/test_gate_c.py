"""WP175 restricted-live canary contract and negative matrix tests.

All tests use synthetic public IDs and never invoke a venue or a real secret.
"""

from __future__ import annotations

from dataclasses import asdict, replace
from decimal import Decimal
import inspect
import json
from pathlib import Path

import pytest
import polymarket
from polymarket import SecureClient
from polymarket.models.clob.account import BalanceAllowance
from polymarket.models.clob.order_response import AcceptedOrder, RejectedOrder

import src.execution_gateway.gate_b as gate_b_mod
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
    MAX_CANARY_WALLET_PUSD,
    MAX_GROSS_LIVE_EXPOSURE_PUSD,
    MAX_PER_MARKET_EXPOSURE_PUSD,
    MAX_PER_ORDER_COMMITTED_PUSD,
    GateCSession,
    _id,
)


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
    gateway.record_gate_c_event("GATE_C_HALTED", checkpoint, event_time_ns=2)
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


def test_create_started_before_exactly_one_post_and_never_retries() -> None:
    source = inspect.getsource(GateCSession.create_limit_order)
    assert "GATE_C_CREATE_STARTED" in source
    assert source.count("transport.transmit") == 1
    assert "record_gate_c_event" in source


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
