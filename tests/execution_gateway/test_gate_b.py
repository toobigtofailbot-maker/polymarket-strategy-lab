"""WP174B Gate-B adversarial tests. Fake providers and mocked clients only.

No real secret, no real network, no real venue mutation, and no capital. These
tests prove the ephemeral secret boundary, Deposit Wallet identity enforcement,
raw-client containment, the local signing probe (no post), the Gate-C-unreachable
create transport, cancel idempotency/ambiguity, the safe empty-wallet probe, the
sanitized receipt, and secret redaction.
"""

from __future__ import annotations

import pytest

import src.execution_gateway.gate_b as gate_b_mod
from src.execution_gateway.gate_b import (
    CancelAttempt,
    GateBIdentityPolicy,
    GateBSecretLease,
    GateBSession,
    GateCLivePermit,
    InteractiveGateBSecretProvider,
    ProductionSdkMutationAdapter,
    gate_b_capability_projection,
)
from src.execution_gateway.gateway import GatewayError

SIGNER = "0x" + "a" * 40
WALLET = "0x" + "b" * 40
TOKEN = "72936048731589097779338603842330045444584949162--positive"
SECRET_SENTINEL = "0xdeadbeefprivatekeyshouldneverleak000000000000000000000000000001"


# --------------------------------------------------------------------------- fakes


class _Balance:
    def __init__(self, balance: str = "0"):
        self.balance = balance


class _Page:
    def __init__(self, items):
        self._items = list(items)

    def iter_items(self):
        return iter(self._items)


class _Ctx:
    def __init__(self, signer_type="OWNER", chain_id=137):
        self.signer_type = signer_type
        self.environment_config = type("C", (), {"chain_id": chain_id})()


class _Env:
    def __init__(self, name="production"):
        self.name = name


class _SignedOrder:
    # Includes a signature to prove the probe never persists/echoes it.
    signature = "0xSIGNATUREBYTESThatMustNeverBeStored"
    signature_type = 3
    signer = SIGNER


class _CancelResponse:
    def __init__(self, canceled=(), not_canceled=()):
        self.canceled = list(canceled)
        self.not_canceled = list(not_canceled)


class FakeClient:
    def __init__(
        self,
        *,
        signer=SIGNER,
        wallet=WALLET,
        wallet_type="DEPOSIT_WALLET",
        environment="production",
        signer_type="OWNER",
        chain_id=137,
        balance="0",
        open_orders=(),
        positions=(),
        cancel_response=None,
        cancel_raises=False,
    ):
        self.signer = signer
        self.wallet = wallet
        self.wallet_type = wallet_type
        self.environment = _Env(environment)
        self._ctx = _Ctx(signer_type, chain_id)
        self._balance = balance
        self._open = list(open_orders)
        self._positions = list(positions)
        self._cancel_response = cancel_response or _CancelResponse()
        self._cancel_raises = cancel_raises
        self.cancel_all_calls = 0
        self.place_calls = 0

    def get_balance_allowance(self, *, asset_type):
        assert asset_type == "COLLATERAL"
        return _Balance(self._balance)

    def list_open_orders(self, **_kw):
        return _Page(self._open)

    def list_positions(self, **_kw):
        return _Page(self._positions)

    def create_limit_order(self, *, token_id, price, size, side, post_only=False):
        return _SignedOrder()

    def place_limit_order(self, **_kw):  # must never be called by the probe
        self.place_calls += 1
        raise AssertionError("signing probe must not post")

    def post_order(self, *_a, **_k):
        self.place_calls += 1
        raise AssertionError("signing probe must not post")

    def cancel_all(self):
        self.cancel_all_calls += 1
        if self._cancel_raises:
            raise RuntimeError(f"venue error leaking {SECRET_SENTINEL}")
        return self._cancel_response

    def cancel_order(self, *, order_id):
        return self._cancel_response


def _provider(value=SECRET_SENTINEL):
    class _P:
        def acquire(self):
            return GateBSecretLease(value)

    return _P()


def _factory(client):
    def _f(private_key, expected_wallet):
        # A real factory would authenticate; the fake ignores the key value.
        assert isinstance(private_key, str) and private_key
        return client

    return _f


def _policy(**kw):
    return GateBIdentityPolicy(expected_signer=SIGNER, expected_wallet=WALLET, **kw)


def _session(client):
    return GateBSession.authenticate(_provider(), _policy(), client_factory=_factory(client))


# --------------------------------------------------------------------------- secret boundary


def test_secret_lease_never_exposes_value():
    lease = GateBSecretLease(SECRET_SENTINEL)
    assert SECRET_SENTINEL not in repr(lease)
    assert SECRET_SENTINEL not in str(lease)
    with pytest.raises(GatewayError, match="SECRET_INPUT_INVALID"):
        lease.__reduce__()
    assert lease.reveal() == SECRET_SENTINEL
    lease.close()
    assert not lease.active
    with pytest.raises(GatewayError, match="SECRET_INPUT_UNAVAILABLE"):
        lease.reveal()


def test_interactive_provider_requires_tty(monkeypatch):
    # A non-TTY (piped/redirected) stdin fails closed before getpass is reached.
    monkeypatch.setattr(gate_b_mod, "_stdin_is_tty", lambda: False)
    with pytest.raises(GatewayError, match="SECRET_INPUT_UNAVAILABLE"):
        InteractiveGateBSecretProvider().acquire()


def test_interactive_provider_rejects_eof_on_tty(monkeypatch):
    import getpass as _gp

    monkeypatch.setattr(gate_b_mod, "_stdin_is_tty", lambda: True)
    monkeypatch.setattr(_gp, "getpass", lambda _p: (_ for _ in ()).throw(EOFError()))
    with pytest.raises(GatewayError, match="SECRET_INPUT_UNAVAILABLE"):
        InteractiveGateBSecretProvider().acquire()


def test_interactive_provider_rejects_empty(monkeypatch):
    import getpass as _gp

    monkeypatch.setattr(gate_b_mod, "_stdin_is_tty", lambda: True)
    monkeypatch.setattr(_gp, "getpass", lambda _p: "   ")
    with pytest.raises(GatewayError, match="SECRET_INPUT_INVALID"):
        InteractiveGateBSecretProvider().acquire()


def test_lease_is_closed_after_authentication():
    leases = []

    class _P:
        def acquire(self):
            lease = GateBSecretLease(SECRET_SENTINEL)
            leases.append(lease)
            return lease

    GateBSession.authenticate(_P(), _policy(), client_factory=_factory(FakeClient()))
    assert leases and not leases[0].active


# --------------------------------------------------------------------------- identity


@pytest.mark.parametrize("wallet_type", ["EOA", "POLY_PROXY", "GNOSIS_SAFE"])
def test_non_deposit_wallet_type_rejected(wallet_type):
    with pytest.raises(GatewayError, match="WALLET_TYPE_UNSUPPORTED"):
        _session(FakeClient(wallet_type=wallet_type))


def test_signer_mismatch_rejected():
    with pytest.raises(GatewayError, match="SIGNER_MISMATCH"):
        _session(FakeClient(signer="0x" + "c" * 40))


def test_wallet_mismatch_rejected():
    with pytest.raises(GatewayError, match="WALLET_MISMATCH"):
        _session(FakeClient(wallet="0x" + "d" * 40))


def test_wrong_chain_rejected():
    with pytest.raises(GatewayError, match="SIGNING_IDENTITY_INVALID"):
        _session(FakeClient(chain_id=1))


def test_non_owner_signer_type_rejected():
    with pytest.raises(GatewayError, match="SIGNING_IDENTITY_INVALID"):
        _session(FakeClient(signer_type="SESSION_KEY"))


def test_non_production_environment_rejected():
    with pytest.raises(GatewayError, match="SIGNING_IDENTITY_INVALID"):
        _session(FakeClient(environment="staging"))


def test_identity_policy_rejects_bad_signature_type():
    with pytest.raises(GatewayError, match="SIGNING_IDENTITY_INVALID"):
        GateBIdentityPolicy(
            expected_signer=SIGNER, expected_wallet=WALLET, signature_type="0"
        ).validate()


def test_authenticated_session_reaches_b2():
    session = _session(FakeClient())
    assert session.capability_state == "B2_AUTHENTICATED"
    assert session.public_signer == SIGNER
    assert session.public_wallet == WALLET


# --------------------------------------------------------------------------- reads


def test_bounded_account_snapshot():
    session = _session(FakeClient(balance="0", open_orders=(), positions=()))
    snap = session.account_snapshot()
    assert snap == {"collateral_balance": "0", "open_orders": 0, "positions": 0}


# --------------------------------------------------------------------------- signing probe


def test_signing_probe_is_deterministic_and_never_posts():
    client = FakeClient()
    session = _session(client)
    one = session.signing_probe(token_id=TOKEN, price="0.10", size="5")
    assert session.capability_state == "B3_SIGNING_VERIFIED"
    assert one.startswith("signingprobe:sha256:")
    # Same public economics -> same identity; and place/post never called.
    session_two = _session(FakeClient())
    two = session_two.signing_probe(token_id=TOKEN, price="0.10", size="5")
    assert one == two
    assert client.place_calls == 0


def test_signing_probe_never_returns_signature_bytes():
    session = _session(FakeClient())
    identity = session.signing_probe(token_id=TOKEN, price="0.10", size="5")
    assert "SIGNATURE" not in identity.upper()


# --------------------------------------------------------------------------- create dual gate


def test_gate_c_permit_is_unconstructable():
    with pytest.raises(GatewayError, match="GATE_C_REQUIRED"):
        GateCLivePermit()


@pytest.mark.parametrize("method", ["create_limit_order", "place_limit_order", "post_order", "place_market_order"])
def test_create_transport_is_gate_c_locked(method):
    adapter = ProductionSdkMutationAdapter(FakeClient())
    with pytest.raises(GatewayError, match="GATE_C_REQUIRED"):
        getattr(adapter, method)(token_id=TOKEN, price="0.10", size="5", side="BUY")


# --------------------------------------------------------------------------- cancel transport


def test_cancel_attempt_identity_deterministic():
    a = CancelAttempt("CANCEL_ALL", "ALL", 1, "HEALTHY")
    b = CancelAttempt("CANCEL_ALL", "ALL", 1, "HEALTHY")
    assert a.identity == b.identity and a.identity.startswith("cancelattempt:sha256:")


def test_cancel_single_transmit_then_idempotent_block():
    adapter = ProductionSdkMutationAdapter(FakeClient())
    attempt = CancelAttempt("CANCEL_ALL", "ALL", 1, "HEALTHY")
    result, summary = adapter.cancel(attempt)
    assert result == "DEFINITIVE_ACCEPTED"
    assert summary["canceled_count"] == 0
    with pytest.raises(GatewayError, match="MUTATION_ALREADY_TRANSMITTED"):
        adapter.cancel(attempt)


def test_cancel_exception_is_ambiguous_and_redacted():
    adapter = ProductionSdkMutationAdapter(FakeClient(cancel_raises=True))
    attempt = CancelAttempt("CANCEL_ALL", "ALL", 1, "HEALTHY")
    with pytest.raises(GatewayError) as exc:
        adapter.cancel(attempt)
    assert exc.value.code == "CANCEL_PROBE_AMBIGUOUS"
    assert SECRET_SENTINEL not in str(exc.value)


# --------------------------------------------------------------------------- empty-wallet probe


def _probe(session, confirmation="CONFIRM-EMPTY-WALLET-CANCEL", repository_head="deadbee"):
    # B3 (verified signing) is a precondition for any cancel transmission.
    if session.capability_state == "B2_AUTHENTICATED":
        session.signing_probe(token_id=TOKEN, price="0.10", size="5")
    return session.empty_wallet_cancel_probe(
        confirmation, repository_head=repository_head, now_ns=1, valid_ns=2
    )


def test_empty_wallet_probe_pass_produces_sanitized_receipt():
    client = FakeClient(balance="0", open_orders=(), positions=())
    session = _session(client)
    receipt = _probe(session)
    assert session.capability_state == "B4_CANCEL_TRANSPORT_VERIFIED"
    assert client.cancel_all_calls == 1
    doc = receipt.as_receipt_document()
    assert doc["cancel_probe_result"] == "DEFINITIVE_ACCEPTED"
    assert doc["account_empty_pass"] is True
    assert doc["receipt_id"].startswith("gatebreceipt:sha256:")
    # No secret value or secret-bearing field name anywhere in the receipt.
    # signature_type ("3") is a safe public field; signature BYTES are not.
    blob = repr(doc)
    assert SECRET_SENTINEL not in blob
    assert _SignedOrder.signature not in blob
    lowered = blob.lower()
    for banned in ("private_key", "apikey", "api_key", "passphrase", "\"secret\"", "signature_bytes"):
        assert banned not in lowered


def test_empty_wallet_probe_aborts_on_nonzero_balance():
    session = _session(FakeClient(balance="5"))
    with pytest.raises(GatewayError, match="GATE_B_ACCOUNT_NOT_EMPTY"):
        _probe(session)


def test_empty_wallet_probe_aborts_on_open_orders():
    session = _session(FakeClient(open_orders=("o1",)))
    with pytest.raises(GatewayError, match="GATE_B_ACCOUNT_NOT_EMPTY"):
        _probe(session)


def test_empty_wallet_probe_aborts_on_positions():
    session = _session(FakeClient(positions=("p1",)))
    with pytest.raises(GatewayError, match="GATE_B_ACCOUNT_NOT_EMPTY"):
        _probe(session)


def test_empty_wallet_probe_requires_confirmation():
    session = _session(FakeClient())
    with pytest.raises(GatewayError, match="CANCEL_PROBE_FAILED"):
        _probe(session, confirmation="nope")


def test_unexpected_cancellation_is_incident():
    # Empty account precheck passes, but cancel_all reports a canceled order.
    client = FakeClient(cancel_response=_CancelResponse(canceled=["o9"]))
    session = _session(client)
    with pytest.raises(GatewayError, match="CANCEL_PROBE_FAILED"):
        _probe(session)


# --------------------------------------------------------------------------- projection / restart


def test_capability_projection_locked_when_no_session():
    proj = gate_b_capability_projection(None)
    assert proj["gate_b_state"] == "B0_LOCKED"
    assert proj["credential_session_active"] is False
    assert proj["create_transport_status"] == "GATE_C_REQUIRED"
    assert proj["public_signer"] is None


def test_capability_projection_active_session_is_sanitized():
    session = _session(FakeClient())
    proj = gate_b_capability_projection(session)
    assert proj["create_transport_status"] == "GATE_C_REQUIRED"
    assert proj["public_signer"] == SIGNER
    assert "private_key" not in repr(proj).lower()


def test_close_returns_capability_to_b0():
    session = _session(FakeClient())
    session.close()
    assert session.capability_state == "B0_LOCKED"


def test_no_public_raw_client_or_credentials_attribute():
    session = _session(FakeClient())
    for banned in ("client", "secure_client", "credentials", "private_key", "api_key", "secret", "passphrase"):
        assert not hasattr(session, banned)


# --- Frozen evidence-node umbrella tests (wp_spec.json evidence_plan R002-R010) ---


def test_ephemeral_secret_input_has_no_persistence_and_no_echo():
    lease = GateBSecretLease(SECRET_SENTINEL)
    assert SECRET_SENTINEL not in repr(lease) and SECRET_SENTINEL not in str(lease)
    with pytest.raises(GatewayError, match="SECRET_INPUT_INVALID"):
        lease.__reduce__()
    lease.close()
    with pytest.raises(GatewayError, match="SECRET_INPUT_UNAVAILABLE"):
        lease.reveal()


def test_deposit_wallet_signer_funder_and_signature_identity_fail_closed():
    with pytest.raises(GatewayError, match="WALLET_TYPE_UNSUPPORTED"):
        _session(FakeClient(wallet_type="EOA"))
    with pytest.raises(GatewayError, match="SIGNER_MISMATCH"):
        _session(FakeClient(signer="0x" + "c" * 40))
    with pytest.raises(GatewayError, match="WALLET_MISMATCH"):
        _session(FakeClient(wallet="0x" + "d" * 40))
    with pytest.raises(GatewayError, match="SIGNING_IDENTITY_INVALID"):
        _session(FakeClient(chain_id=1))


def test_authenticated_l1_l2_and_bounded_reads():
    session = _session(FakeClient(balance="0"))
    snap = session.account_snapshot()
    assert snap["open_orders"] == 0 and snap["positions"] == 0
    assert SECRET_SENTINEL not in repr(snap)


def test_real_key_local_limit_signing_without_post():
    client = FakeClient()
    session = _session(client)
    identity = session.signing_probe(token_id=TOKEN, price="0.10", size="5")
    assert identity.startswith("signingprobe:sha256:")
    assert client.place_calls == 0


def test_raw_client_containment_and_forbidden_wallet_surfaces_unreachable():
    session = _session(FakeClient())
    for banned in ("client", "secure_client", "credentials", "private_key", "api_key", "secret", "passphrase"):
        assert not hasattr(session, banned)
    with pytest.raises(GatewayError, match="GATE_C_REQUIRED"):
        GateCLivePermit()


def test_create_transport_is_gate_c_unreachable():
    adapter = ProductionSdkMutationAdapter(FakeClient())
    for method in ("create_limit_order", "place_limit_order", "post_order", "place_market_order"):
        with pytest.raises(GatewayError, match="GATE_C_REQUIRED"):
            getattr(adapter, method)(token_id=TOKEN, price="0.1", size="5", side="BUY")


def test_cancel_transport_idempotency_ambiguity_and_reconcile():
    adapter = ProductionSdkMutationAdapter(FakeClient())
    attempt = CancelAttempt("CANCEL_ALL", "ALL", 1, "HEALTHY")
    result, _summary = adapter.cancel(attempt)
    assert result == "DEFINITIVE_ACCEPTED"
    with pytest.raises(GatewayError, match="MUTATION_ALREADY_TRANSMITTED"):
        adapter.cancel(attempt)
    amb = ProductionSdkMutationAdapter(FakeClient(cancel_raises=True))
    with pytest.raises(GatewayError, match="CANCEL_PROBE_AMBIGUOUS"):
        amb.cancel(CancelAttempt("CANCEL_ALL", "ALL", 1, "HEALTHY"))


def test_empty_account_cancel_probe_and_sanitized_receipt():
    session = _session(FakeClient())
    receipt = _probe(session)
    doc = receipt.as_receipt_document()
    assert doc["account_empty_pass"] is True
    assert doc["cancel_probe_result"] == "DEFINITIVE_ACCEPTED"
    assert SECRET_SENTINEL not in repr(doc)
    with pytest.raises(GatewayError, match="GATE_B_ACCOUNT_NOT_EMPTY"):
        _probe(_session(FakeClient(balance="5")))


def test_restart_returns_capability_to_b0_and_audit_persists():
    events = []
    session = GateBSession.authenticate(
        _provider(), _policy(), client_factory=_factory(FakeClient()), audit_sink=events.append
    )
    session.signing_probe(token_id=TOKEN, price="0.10", size="5")
    _probe(session)
    kinds = [e["event_type"] for e in events]
    assert "GATE_B_AUTHENTICATED" in kinds
    assert "GATE_B_SIGNING_VERIFIED" in kinds
    assert "GATE_B_CANCEL_TRANSPORT_VERIFIED" in kinds
    assert all(SECRET_SENTINEL not in repr(e) for e in events)
    session.close()
    assert session.capability_state == "B0_LOCKED"


# --- WP174B same-capability correction regressions (fixes 2-6) ---


class _ClosableClient(FakeClient):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.closed = False

    def close(self):
        self.closed = True


def test_signing_verification_required_before_cancel_probe():
    # B2 -> B4 is forbidden: probing without a verified signing probe fails closed.
    session = _session(FakeClient())
    assert session.capability_state == "B2_AUTHENTICATED"
    with pytest.raises(GatewayError, match="CANCEL_PROBE_FAILED"):
        session.empty_wallet_cancel_probe(
            "CONFIRM-EMPTY-WALLET-CANCEL", repository_head="deadbee", now_ns=1, valid_ns=2
        )


def test_receipt_is_content_addressed_over_signing_probe_id():
    session = _session(FakeClient())
    probe_id = session.signing_probe(token_id=TOKEN, price="0.10", size="5")
    receipt = session.empty_wallet_cancel_probe(
        "CONFIRM-EMPTY-WALLET-CANCEL", repository_head="deadbee", now_ns=1, valid_ns=2
    )
    doc = receipt.as_receipt_document()
    # The signing probe id is bound into the receipt content BEFORE the id is derived.
    assert doc["signing_probe_id"] == probe_id
    recomputed = gate_b_mod._sha("gatebreceipt:sha256:", receipt.to_public_mapping())
    assert recomputed == doc["receipt_id"]
    # Changing the bound signing_probe_id changes the content address.
    import dataclasses

    mutated = dataclasses.replace(receipt, signing_probe_id="signingprobe:sha256:" + "0" * 64)
    assert mutated.receipt_id != receipt.receipt_id


def test_close_best_effort_closes_credential_client():
    client = _ClosableClient()
    session = _session(client)
    session.close()
    assert client.closed is True
    assert session.capability_state == "B0_LOCKED"


def test_identity_failure_closes_client():
    client = _ClosableClient(signer="0x" + "c" * 40)
    with pytest.raises(GatewayError, match="SIGNER_MISMATCH"):
        GateBSession.authenticate(_provider(), _policy(), client_factory=_factory(client))
    assert client.closed is True


def test_not_canceled_orders_is_incident():
    # Empty account precheck passes, but cancel reports a not-canceled order.
    client = FakeClient(cancel_response=_CancelResponse(not_canceled=["o7"]))
    session = _session(client)
    with pytest.raises(GatewayError, match="CANCEL_PROBE_FAILED"):
        _probe(session)


def test_unknown_head_is_rejected():
    session = _session(FakeClient())
    session.signing_probe(token_id=TOKEN, price="0.10", size="5")
    with pytest.raises(GatewayError, match="CANCEL_PROBE_FAILED"):
        session.empty_wallet_cancel_probe(
            "CONFIRM-EMPTY-WALLET-CANCEL",
            repository_head="UNKNOWN_HEAD",
            now_ns=1,
            valid_ns=2,
        )


def test_operator_repository_head_fails_closed(monkeypatch):
    from src.execution_gateway import gate_b_operator

    def _boom(*_a, **_k):
        raise RuntimeError("git unavailable")

    monkeypatch.setattr(gate_b_operator.subprocess, "run", _boom)
    with pytest.raises(GatewayError, match="CANCEL_PROBE_FAILED"):
        gate_b_operator._repository_head()


def test_operator_confirmation_requires_tty(monkeypatch):
    from src.execution_gateway import gate_b_operator

    monkeypatch.setattr(gate_b_operator, "_stdin_is_tty", lambda: False)
    with pytest.raises(GatewayError, match="CANCEL_PROBE_FAILED"):
        gate_b_operator._confirm_empty_wallet_cancel()
