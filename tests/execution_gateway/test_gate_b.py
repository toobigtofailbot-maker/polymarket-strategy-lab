"""WP174B Gate-B adversarial tests. Fake providers and mocked clients only.

No real secret, no real network, no real venue mutation, and no capital. These
tests prove the ephemeral secret boundary, Deposit Wallet identity enforcement,
raw-client containment, the local signing probe (no post), the Gate-C-unreachable
create transport, cancel idempotency/ambiguity, the safe empty-wallet probe, the
sanitized receipt, and secret redaction.
"""

from __future__ import annotations

from pathlib import Path
import time
from types import SimpleNamespace
import pytest

import src.execution_gateway.gate_b as gate_b_mod
from src.execution_gateway.gate_b import (
    CancelAttempt,
    GateBIdentityPolicy,
    GateBSecretLease,
    GateBSession,
    GateCLivePermit,
    InteractiveGateBSecretProvider,
    WalletSessionLock,
    gate_b_capability_projection,
)
from src.execution_gateway.gateway import GatewayError, ProtectedExecutionGateway
from src.paper_trading import PaperEngine, build_paper_intent
from src.paper_trading.store import PaperStore
from tests.execution_gateway.test_gateway import (
    _authorization,
    _prepare,
    _ready_gateway,
    _venue_context,
)

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
    def __init__(self, canceled=(), not_canceled=None):
        self.canceled = tuple(canceled)
        self.not_canceled = dict(not_canceled or {})


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
        trades=(),
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
        self._trades = list(trades)
        self._cancel_response = cancel_response or _CancelResponse()
        self._cancel_raises = cancel_raises
        self.cancel_all_calls = 0
        self.cancel_one_calls = []
        self.cancel_many_calls = []
        self.cancel_market_calls = []
        self.place_calls = 0
        self.read_calls = {"balance": 0, "open_orders": 0, "trades": 0, "positions": 0}

    def get_balance_allowance(self, *, asset_type):
        assert asset_type == "COLLATERAL"
        self.read_calls["balance"] += 1
        return _Balance(self._balance)

    def list_open_orders(self, **_kw):
        self.read_calls["open_orders"] += 1
        return _Page(self._open)

    def list_account_trades(self, **_kw):
        self.read_calls["trades"] += 1
        return _Page(self._trades)

    def list_positions(self, **_kw):
        assert _kw == {"user": WALLET, "page_size": 100}
        self.read_calls["positions"] += 1
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
        self.cancel_one_calls.append(order_id)
        if self._cancel_raises:
            raise RuntimeError(f"venue error leaking {SECRET_SENTINEL}")
        return self._cancel_response

    def cancel_orders(self, *, order_ids):
        self.cancel_many_calls.append(tuple(order_ids))
        if self._cancel_raises:
            raise RuntimeError(f"venue error leaking {SECRET_SENTINEL}")
        return self._cancel_response

    def cancel_market_orders(self, *, market):
        self.cancel_market_calls.append(market)
        if self._cancel_raises:
            raise RuntimeError(f"venue error leaking {SECRET_SENTINEL}")
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
    return GateBSession.authenticate(
        _provider(), _policy(), client_factory=_factory(client)
    )


def _durable_session(tmp_path: Path, client: FakeClient):
    store_path = tmp_path / "gateway.sqlite3"
    gateway = (
        ProtectedExecutionGateway.open(store_path, opened_time_ns=time.time_ns())
        if store_path.exists()
        else ProtectedExecutionGateway.create(store_path, created_time_ns=1)
    )
    lock = WalletSessionLock(tmp_path, WALLET).acquire()
    session = GateBSession.authenticate(
        _provider(),
        _policy(),
        client_factory=_factory(client),
        gateway=gateway,
        wallet_lock=lock,
    )
    return store_path, gateway, lock, session


def _empty_cancel_attempt(*, sequence: int = 1) -> CancelAttempt:
    return CancelAttempt(
        operation="CANCEL_ALL",
        request_target_ids=(),
        request_target_bindings=(),
        request_market_id=None,
        attempt_sequence=sequence,
        prior_reconciliation_state="HEALTHY",
    )


def _durable_probe(
    tmp_path: Path,
    client: FakeClient,
    confirmation: str = "CONFIRM-EMPTY-WALLET-CANCEL",
    repository_head: str = "deadbee",
):
    _store, gateway, lock, session = _durable_session(tmp_path, client)
    try:
        receipt = _probe(
            session, confirmation=confirmation, repository_head=repository_head
        )
        return receipt, session.capability_state
    finally:
        session.close()
        lock.close()
        gateway.close()


def _known_order_session(tmp_path: Path, client: FakeClient, *, count: int = 2):
    gateway = _ready_gateway(tmp_path)
    first = _prepare(gateway, tmp_path)
    gateway.record_fixture_mutation(
        first.order_identity,
        operation="CREATE",
        attempt_sequence=1,
        request=first.would_submit,
        transmitted=True,
        response_status=200,
        response_body_valid=True,
        venue_order_id="venue-order-a",
        event_time_ns=30,
    )
    orders = [("venue-order-a", first.order_identity)]
    if count == 2:
        paper_path, _first_intent_id, _evidence = _authorization(tmp_path)
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
            signing_time_ns=31,
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
            event_time_ns=32,
        )
        orders.append(("venue-order-b", second.order_identity))
    lock = WalletSessionLock(tmp_path, WALLET).acquire()
    session = GateBSession.authenticate(
        _provider(),
        _policy(),
        client_factory=_factory(client),
        gateway=gateway,
        wallet_lock=lock,
    )
    session._record_reconciliation(
        {
            "collateral_balance": "0",
            "open_orders": count,
            "account_trades": 0,
            "positions": 0,
        }
    )
    return gateway, lock, session, tuple(orders)


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


def test_gate_c_market_metadata_comes_from_official_models_and_fails_closed():
    client = FakeClient()
    client.get_market = lambda *, id: SimpleNamespace(
        id=id,
        condition_id="condition-a",
        state=SimpleNamespace(
            active=True, closed=False, accepting_orders=True,
            enable_order_book=True, neg_risk=False,
        ),
        trading=SimpleNamespace(seconds_delay=0, fees_enabled=False),
        outcomes=SimpleNamespace(
            yes=SimpleNamespace(token_id=TOKEN),
            no=SimpleNamespace(token_id="other-token"),
        ),
    )
    client.get_order_book = lambda *, token_id: SimpleNamespace(
        asset_id=token_id, condition_id="condition-a", neg_risk=False,
        tick_size="0.01", min_order_size="1",
    )
    session = _session(client)
    metadata = session.gate_c_market_metadata(
        gate_b_mod._GATE_C_ISSUER, market_id="market-a", token_id=TOKEN,
        observed_time_ns=100,
    )
    assert metadata.market_id == "market-a"
    assert metadata.condition_id == "condition-a"
    assert metadata.token_id == TOKEN
    client.get_market = lambda *, id: SimpleNamespace(
        id=id, condition_id="condition-a",
        state=SimpleNamespace(
            active=True, closed=False, accepting_orders=True,
            enable_order_book=True, neg_risk=False,
        ),
        trading=SimpleNamespace(seconds_delay=0, fees_enabled=True),
        outcomes=SimpleNamespace(
            yes=SimpleNamespace(token_id=TOKEN),
            no=SimpleNamespace(token_id="other-token"),
        ),
    )
    with pytest.raises(GatewayError, match="MARKET_METADATA_INVALID"):
        session.gate_c_market_metadata(
            gate_b_mod._GATE_C_ISSUER, market_id="market-a", token_id=TOKEN,
            observed_time_ns=100,
        )


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
    assert snap == {
        "collateral_balance": "0",
        "allowance_by_exchange": {},
        "open_orders": 0,
        "account_trades": 0,
        "positions": 0,
        "position_quantities": {},
        "market_exposures_pusd": {},
        "gross_exposure_pusd": "0",
        "committed_exposure_pusd": "0",
        "realized_loss_pusd": "0",
        "drawdown_pusd": "0",
        "cumulative_loss_pusd": "0",
        "active_markets": 0,
    }


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


@pytest.mark.parametrize(
    "method",
    ["create_limit_order", "place_limit_order", "post_order", "place_market_order"],
)
def test_create_transport_is_gate_c_locked(method):
    adapter = gate_b_mod._ProductionSdkMutationTransport(FakeClient())
    with pytest.raises(GatewayError, match="GATE_C_REQUIRED"):
        getattr(adapter, method)(token_id=TOKEN, price="0.10", size="5", side="BUY")


# --------------------------------------------------------------------------- cancel transport


def test_cancel_attempt_identity_deterministic():
    a = _empty_cancel_attempt()
    b = _empty_cancel_attempt()
    assert a.identity == b.identity and a.identity.startswith("cancelattempt:sha256:")


def test_cancel_single_transmit_then_idempotent_block():
    adapter = gate_b_mod._ProductionSdkMutationTransport(FakeClient())
    attempt = _empty_cancel_attempt()
    result, summary = adapter.cancel(attempt)
    assert result == "DEFINITIVE_ACCEPTED"
    assert summary["canceled_count"] == 0
    with pytest.raises(GatewayError, match="MUTATION_ALREADY_TRANSMITTED"):
        adapter.cancel(attempt)


def test_cancel_exception_is_ambiguous_and_redacted():
    adapter = gate_b_mod._ProductionSdkMutationTransport(FakeClient(cancel_raises=True))
    attempt = _empty_cancel_attempt()
    with pytest.raises(GatewayError) as exc:
        adapter.cancel(attempt)
    assert exc.value.code == "CANCEL_PROBE_AMBIGUOUS"
    assert SECRET_SENTINEL not in str(exc.value)


# --------------------------------------------------------------------------- empty-wallet probe


def _probe(
    session, confirmation="CONFIRM-EMPTY-WALLET-CANCEL", repository_head="deadbee"
):
    # B3 (verified signing) is a precondition for any cancel transmission.
    if session.capability_state == "B2_AUTHENTICATED":
        session.signing_probe(token_id=TOKEN, price="0.10", size="5")
    return session.empty_wallet_cancel_probe(
        confirmation, repository_head=repository_head, now_ns=1, valid_ns=2
    )


def test_empty_wallet_probe_pass_produces_sanitized_receipt(tmp_path: Path):
    client = FakeClient(balance="0", open_orders=(), positions=())
    receipt, state = _durable_probe(tmp_path, client)
    assert state == "B4_CANCEL_TRANSPORT_VERIFIED"
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
    for banned in (
        "private_key",
        "apikey",
        "api_key",
        "passphrase",
        '"secret"',
        "signature_bytes",
    ):
        assert banned not in lowered


def test_empty_wallet_probe_aborts_on_nonzero_balance(tmp_path: Path):
    with pytest.raises(GatewayError, match="GATE_B_ACCOUNT_NOT_EMPTY"):
        _durable_probe(tmp_path, FakeClient(balance="5"))


def test_empty_wallet_probe_aborts_on_open_orders(tmp_path: Path):
    with pytest.raises(GatewayError, match="GATE_B_ACCOUNT_NOT_EMPTY"):
        _durable_probe(tmp_path, FakeClient(open_orders=("o1",)))


def test_empty_wallet_probe_aborts_on_positions(tmp_path: Path):
    with pytest.raises(GatewayError, match="GATE_B_ACCOUNT_NOT_EMPTY"):
        _durable_probe(tmp_path, FakeClient(positions=("p1",)))


def test_empty_wallet_probe_requires_confirmation(tmp_path: Path):
    with pytest.raises(GatewayError, match="CANCEL_PROBE_FAILED"):
        _durable_probe(tmp_path, FakeClient(), confirmation="nope")


def test_unexpected_cancellation_is_incident(tmp_path: Path):
    # Empty account precheck passes, but cancel_all reports a canceled order.
    client = FakeClient(cancel_response=_CancelResponse(canceled=["o9"]))
    with pytest.raises(GatewayError, match="CANCEL_PROBE_AMBIGUOUS"):
        _durable_probe(tmp_path, client)


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
    for banned in (
        "client",
        "secure_client",
        "credentials",
        "private_key",
        "api_key",
        "secret",
        "passphrase",
        "mutation_adapter",
    ):
        assert not hasattr(session, banned)
    import src.execution_gateway as execution_gateway

    assert not hasattr(execution_gateway, "ProductionSdkMutationAdapter")


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
    for banned in (
        "client",
        "secure_client",
        "credentials",
        "private_key",
        "api_key",
        "secret",
        "passphrase",
    ):
        assert not hasattr(session, banned)
    with pytest.raises(GatewayError, match="GATE_C_REQUIRED"):
        GateCLivePermit()


def test_create_transport_is_gate_c_unreachable():
    adapter = gate_b_mod._ProductionSdkMutationTransport(FakeClient())
    for method in (
        "create_limit_order",
        "place_limit_order",
        "post_order",
        "place_market_order",
    ):
        with pytest.raises(GatewayError, match="GATE_C_REQUIRED"):
            getattr(adapter, method)(token_id=TOKEN, price="0.1", size="5", side="BUY")


def test_gate_c_transport_handle_requires_the_opaque_permit():
    adapter = gate_b_mod._ProductionSdkMutationTransport(FakeClient())
    with pytest.raises(GatewayError, match="GATE_C_REQUIRED"):
        adapter.gate_c_transport(object())


def test_cancel_transport_idempotency_ambiguity_and_reconcile():
    adapter = gate_b_mod._ProductionSdkMutationTransport(FakeClient())
    attempt = _empty_cancel_attempt()
    result, _summary = adapter.cancel(attempt)
    assert result == "DEFINITIVE_ACCEPTED"
    with pytest.raises(GatewayError, match="MUTATION_ALREADY_TRANSMITTED"):
        adapter.cancel(attempt)
    amb = gate_b_mod._ProductionSdkMutationTransport(FakeClient(cancel_raises=True))
    with pytest.raises(GatewayError, match="CANCEL_PROBE_AMBIGUOUS"):
        amb.cancel(_empty_cancel_attempt())


def test_empty_account_cancel_probe_and_sanitized_receipt(tmp_path: Path):
    receipt, _state = _durable_probe(tmp_path, FakeClient())
    doc = receipt.as_receipt_document()
    assert doc["account_empty_pass"] is True
    assert doc["cancel_probe_result"] == "DEFINITIVE_ACCEPTED"
    assert SECRET_SENTINEL not in repr(doc)
    nonempty = tmp_path / "nonempty"
    nonempty.mkdir()
    with pytest.raises(GatewayError, match="GATE_B_ACCOUNT_NOT_EMPTY"):
        _durable_probe(nonempty, FakeClient(balance="5"))


def test_restart_returns_capability_to_b0_and_audit_persists(tmp_path: Path):
    events = []
    path = tmp_path / "gateway.sqlite3"
    gateway = ProtectedExecutionGateway.create(path, created_time_ns=1)
    lock = WalletSessionLock(tmp_path, WALLET).acquire()
    session = GateBSession.authenticate(
        _provider(),
        _policy(),
        client_factory=_factory(FakeClient()),
        audit_sink=events.append,
        gateway=gateway,
        wallet_lock=lock,
    )
    session.signing_probe(token_id=TOKEN, price="0.10", size="5")
    _probe(session)
    kinds = [e["event_type"] for e in events]
    assert "GATE_B_AUTHENTICATED" in kinds
    assert "GATE_B_SIGNING_VERIFIED" in kinds
    assert "GATE_B_CANCEL_TRANSPORT_VERIFIED" in kinds
    assert all(SECRET_SENTINEL not in repr(e) for e in events)
    session.close()
    lock.close()
    gateway.close()
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
            "CONFIRM-EMPTY-WALLET-CANCEL",
            repository_head="deadbee",
            now_ns=1,
            valid_ns=2,
        )


def test_receipt_is_content_addressed_over_signing_probe_id(tmp_path: Path):
    _store, gateway, lock, session = _durable_session(tmp_path, FakeClient())
    try:
        probe_id = session.signing_probe(token_id=TOKEN, price="0.10", size="5")
        receipt = session.empty_wallet_cancel_probe(
            "CONFIRM-EMPTY-WALLET-CANCEL",
            repository_head="deadbee",
            now_ns=1,
            valid_ns=2,
        )
    finally:
        session.close()
        lock.close()
        gateway.close()
    doc = receipt.as_receipt_document()
    # The signing probe id is bound into the receipt content BEFORE the id is derived.
    assert doc["signing_probe_id"] == probe_id
    recomputed = gate_b_mod._sha("gatebreceipt:sha256:", receipt.to_public_mapping())
    assert recomputed == doc["receipt_id"]
    # Changing the bound signing_probe_id changes the content address.
    import dataclasses

    mutated = dataclasses.replace(
        receipt, signing_probe_id="signingprobe:sha256:" + "0" * 64
    )
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
        GateBSession.authenticate(
            _provider(), _policy(), client_factory=_factory(client)
        )
    assert client.closed is True


def test_not_canceled_orders_is_incident(tmp_path: Path):
    # Empty account precheck passes, but cancel reports a not-canceled order.
    client = FakeClient(cancel_response=_CancelResponse(not_canceled={"o7": "no"}))
    with pytest.raises(GatewayError, match="CANCEL_PROBE_AMBIGUOUS"):
        _durable_probe(tmp_path, client)


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


def test_real_gateway_store_persists_gate_b_evidence_across_restart(tmp_path: Path):
    store_path, gateway, lock, session = _durable_session(tmp_path, FakeClient())
    session.signing_probe(token_id=TOKEN, price="0.10", size="5")
    receipt = _probe(session)
    session.close()
    lock.close()
    gateway.close()

    reopened = ProtectedExecutionGateway.open(store_path, opened_time_ns=time.time_ns())
    assert reopened.state.authority_state == "A0_DISABLED"
    kinds = [event.event_type for event in reopened.gate_b_events()]
    assert kinds == [
        "GATE_B_AUTHENTICATED",
        "GATE_B_SIGNING_VERIFIED",
        "GATE_B_RECONCILED",
        "GATE_B_CANCEL_ATTEMPT_STARTED",
        "GATE_B_CANCEL_ATTEMPT_RESULT",
        "GATE_B_CANCEL_TRANSPORT_VERIFIED",
    ]
    started = next(
        event
        for event in reopened.gate_b_events()
        if event.event_type == "GATE_B_CANCEL_ATTEMPT_STARTED"
    )
    assert started.data["request_target_ids"] == []
    assert started.data["request_target_bindings"] == []
    assert started.data["request_market_id"] is None
    assert receipt.receipt_id in repr(
        [dict(event.data) for event in reopened.gate_b_events()]
    )
    reopened.close()


@pytest.mark.parametrize("forbidden", ["secret", "signed_payload", "raw_response"])
def test_persistent_gate_b_journal_redaction_rejects_forbidden_fields(
    tmp_path: Path, forbidden: str
):
    path = tmp_path / "gateway.sqlite3"
    with ProtectedExecutionGateway.create(path, created_time_ns=1) as gateway:
        data = {
            "capability_state": "B2_AUTHENTICATED",
            "public_signer": SIGNER,
            "public_wallet": WALLET,
            "wallet_type": "DEPOSIT_WALLET",
            "signature_type": "3",
            forbidden: "forbidden-value",
        }
        with pytest.raises(GatewayError, match="INVALID_AUDIT_DATA"):
            gateway.record_gate_b_event("GATE_B_AUTHENTICATED", data)
        assert gateway.gate_b_events() == ()


@pytest.mark.parametrize(
    "defect",
    [
        "identity",
        "duplicate_target",
        "binding_mismatch",
        "market_missing",
        "unexpected_market",
        "over_bound",
    ],
)
def test_gate_b_started_event_structural_negative_matrix(tmp_path: Path, defect: str):
    owner = "executionorder:sha256:" + "1" * 64
    attempt = CancelAttempt(
        operation="CANCEL_ONE",
        request_target_ids=("venue-order-a",),
        request_target_bindings=(("venue-order-a", owner),),
        request_market_id=None,
        attempt_sequence=1,
        prior_reconciliation_state="HEALTHY",
    )
    data = {
        "capability_state": "B2_AUTHENTICATED",
        "public_signer": SIGNER,
        "public_wallet": WALLET,
        "wallet_type": "DEPOSIT_WALLET",
        "signature_type": "3",
        "cancel_attempt_id": attempt.identity,
        "operation": attempt.operation,
        "request_target_ids": list(attempt.request_target_ids),
        "request_target_bindings": [list(attempt.request_target_bindings[0])],
        "request_market_id": None,
        "attempt_sequence": 1,
        "prior_reconciliation_state": "HEALTHY",
    }
    if defect == "identity":
        data["cancel_attempt_id"] = "cancelattempt:sha256:" + "0" * 64
    elif defect == "duplicate_target":
        data["operation"] = "CANCEL_MANY"
        data["request_target_ids"] = ["venue-order-a", "venue-order-a"]
        data["request_target_bindings"] = [
            ["venue-order-a", owner],
            ["venue-order-a", owner],
        ]
    elif defect == "binding_mismatch":
        data["request_target_bindings"] = [["venue-order-b", owner]]
    elif defect == "market_missing":
        data["operation"] = "CANCEL_MARKET"
    elif defect == "unexpected_market":
        data["request_market_id"] = "market:a"
    else:
        data["operation"] = "CANCEL_MANY"
        data["request_target_ids"] = [f"venue-{index:03d}" for index in range(101)]
        data["request_target_bindings"] = [
            [target, owner] for target in data["request_target_ids"]
        ]
    with ProtectedExecutionGateway.create(
        tmp_path / "gateway.sqlite3", created_time_ns=1
    ) as gateway:
        with pytest.raises(GatewayError, match="INVALID_AUDIT_DATA"):
            gateway.record_gate_b_event("GATE_B_CANCEL_ATTEMPT_STARTED", data)
        assert gateway.gate_b_events() == ()


def test_cancel_attempt_is_committed_before_transport(tmp_path: Path):
    holder = {}

    class InspectingClient(FakeClient):
        def cancel_all(self):
            events = holder["gateway"].gate_b_events()
            assert events[-1].event_type == "GATE_B_CANCEL_ATTEMPT_STARTED"
            return super().cancel_all()

    _store, gateway, lock, session = _durable_session(tmp_path, InspectingClient())
    holder["gateway"] = gateway
    _probe(session)
    session.close()
    lock.close()
    gateway.close()


def test_restart_never_resends_started_without_result(tmp_path: Path):
    store_path, gateway, lock, session = _durable_session(tmp_path, FakeClient())
    attempt = _empty_cancel_attempt()
    session._emit(
        "GATE_B_CANCEL_ATTEMPT_STARTED",
        {
            "cancel_attempt_id": attempt.identity,
            "operation": attempt.operation,
            "request_target_ids": [],
            "request_target_bindings": [],
            "request_market_id": None,
            "attempt_sequence": attempt.attempt_sequence,
            "prior_reconciliation_state": attempt.prior_reconciliation_state,
        },
    )
    session.close()
    lock.close()
    gateway.close()

    client = FakeClient()
    _store, reopened, second_lock, restarted = _durable_session(tmp_path, client)
    restarted.signing_probe(token_id=TOKEN, price="0.10", size="5")
    with pytest.raises(GatewayError, match="RECONCILIATION_REQUIRED"):
        _probe(restarted)
    assert client.cancel_all_calls == 0
    restarted.close()
    second_lock.close()
    reopened.close()


@pytest.mark.parametrize(
    "response",
    [
        object(),
        type("MissingNotCanceled", (), {"canceled": []})(),
        type("Bad", (), {"canceled": 1, "not_canceled": []})(),
        type("StringCanceled", (), {"canceled": "o1", "not_canceled": {}})(),
        type("BytesCanceled", (), {"canceled": b"o1", "not_canceled": {}})(),
        type("ListNotCanceled", (), {"canceled": (), "not_canceled": ["o1"]})(),
        type("BadReason", (), {"canceled": (), "not_canceled": {"o1": 1}})(),
    ],
)
def test_malformed_cancel_response_is_ambiguous_not_accepted(tmp_path: Path, response):
    client = FakeClient(cancel_response=response)
    _store, gateway, lock, session = _durable_session(tmp_path, client)
    with pytest.raises(GatewayError, match="CANCEL_PROBE_AMBIGUOUS"):
        _probe(session)
    results = [
        dict(event.data)["cancel_result"]
        for event in gateway.gate_b_events()
        if event.event_type == "GATE_B_CANCEL_ATTEMPT_RESULT"
    ]
    assert results == ["AMBIGUOUS"]
    session.close()
    lock.close()
    gateway.close()


def test_ambiguous_attempt_survives_restart_and_blocks_retry(tmp_path: Path):
    from polymarket.models.clob.cancel import CancelOrdersResponse

    store_path, gateway, lock, session = _durable_session(
        tmp_path,
        FakeClient(
            cancel_response=CancelOrdersResponse(
                canceled=("unexpected-order",), not_canceled={}
            )
        ),
    )
    with pytest.raises(GatewayError, match="CANCEL_PROBE_AMBIGUOUS") as exc:
        _probe(session)
    assert SECRET_SENTINEL not in str(exc.value)
    session.close()
    lock.close()
    gateway.close()

    client = FakeClient()
    _store, reopened, second_lock, restarted = _durable_session(tmp_path, client)
    restarted.signing_probe(token_id=TOKEN, price="0.10", size="5")
    with pytest.raises(GatewayError, match="RECONCILIATION_REQUIRED"):
        _probe(restarted)
    assert client.cancel_all_calls == 0
    restarted.close()
    second_lock.close()
    reopened.close()


def test_wallet_session_lock_is_exclusive_and_released(tmp_path: Path):
    first = WalletSessionLock(tmp_path, WALLET).acquire()
    with pytest.raises(GatewayError, match="GATE_B_OWNERSHIP_LOCKED"):
        WalletSessionLock(tmp_path, WALLET).acquire()
    assert SECRET_SENTINEL not in first.path.read_text(encoding="ascii")
    first.close()
    WalletSessionLock(tmp_path, WALLET).acquire().close()


@pytest.mark.parametrize(
    "operation",
    ["CANCEL_ONE", "CANCEL_MANY", "CANCEL_MARKET", "CANCEL_ALL"],
)
def test_every_cancel_operation_persists_started_before_one_transport_call(
    tmp_path: Path, operation: str
):
    holder = {}

    class InspectingClient(FakeClient):
        def _assert_started(self, expected):
            event = holder["gateway"].gate_b_events()[-1]
            assert event.event_type == "GATE_B_CANCEL_ATTEMPT_STARTED"
            assert event.data["operation"] == expected

        def cancel_order(self, *, order_id):
            self._assert_started("CANCEL_ONE")
            self.cancel_one_calls.append(order_id)
            return _CancelResponse(canceled=(order_id,))

        def cancel_orders(self, *, order_ids):
            self._assert_started("CANCEL_MANY")
            self.cancel_many_calls.append(tuple(order_ids))
            return _CancelResponse(canceled=order_ids)

        def cancel_market_orders(self, *, market):
            self._assert_started("CANCEL_MARKET")
            self.cancel_market_calls.append(market)
            return _CancelResponse(canceled=("venue-order-a", "venue-order-b"))

        def cancel_all(self):
            self._assert_started("CANCEL_ALL")
            self.cancel_all_calls += 1
            return _CancelResponse(canceled=("venue-order-a", "venue-order-b"))

    client = InspectingClient()
    gateway, lock, session, bindings = _known_order_session(tmp_path, client)
    holder["gateway"] = gateway
    ids = tuple(target for target, _owner in bindings)
    try:
        if operation == "CANCEL_ONE":
            result = session.cancel_one(
                request_target_ids=ids[:1],
                request_target_bindings=bindings[:1],
            )
        elif operation == "CANCEL_MANY":
            result = session.cancel_many(
                request_target_ids=tuple(reversed(ids)),
                request_target_bindings=tuple(reversed(bindings)),
            )
        elif operation == "CANCEL_MARKET":
            result = session.cancel_market(
                request_market_id="market:a",
                request_target_ids=tuple(reversed(ids)),
                request_target_bindings=tuple(reversed(bindings)),
            )
        else:
            result = session.cancel_all()
        assert result["cancel_result"] == "DEFINITIVE_ACCEPTED"
        calls = (
            len(client.cancel_one_calls)
            + len(client.cancel_many_calls)
            + len(client.cancel_market_calls)
            + client.cancel_all_calls
        )
        assert calls == 1
        events = gateway.gate_b_events()
        assert events[-2].event_type == "GATE_B_CANCEL_ATTEMPT_STARTED"
        assert events[-1].event_type == "GATE_B_CANCEL_ATTEMPT_RESULT"
    finally:
        session.close()
        lock.close()
        gateway.close()


def test_cancel_many_canonical_identity_and_structured_sdk_targets(tmp_path: Path):
    identities = []
    for name, reverse in (("first", False), ("second", True)):
        root = tmp_path / name
        root.mkdir()
        client = FakeClient(
            cancel_response=_CancelResponse(canceled=("venue-order-a", "venue-order-b"))
        )
        gateway, lock, session, bindings = _known_order_session(root, client)
        ids = tuple(target for target, _owner in bindings)
        if reverse:
            ids = tuple(reversed(ids))
            bindings = tuple(reversed(bindings))
        try:
            result = session.cancel_many(
                request_target_ids=ids,
                request_target_bindings=bindings,
            )
            identities.append(result["cancel_attempt_id"])
            assert client.cancel_many_calls == [("venue-order-a", "venue-order-b")]
        finally:
            session.close()
            lock.close()
            gateway.close()
    assert identities[0] == identities[1]


def test_structured_cancel_cardinality_duplicates_and_comma_encoding_fail_closed(
    tmp_path: Path,
):
    client = FakeClient()
    gateway, lock, session, bindings = _known_order_session(tmp_path, client)
    ids = tuple(target for target, _owner in bindings)
    invalid_calls = (
        lambda: session.cancel_one(request_target_ids=(), request_target_bindings=()),
        lambda: session.cancel_one(
            request_target_ids=ids, request_target_bindings=bindings
        ),
        lambda: session.cancel_many(request_target_ids=(), request_target_bindings=()),
        lambda: session.cancel_many(
            request_target_ids=(ids[0], ids[0]),
            request_target_bindings=(bindings[0], bindings[0]),
        ),
        lambda: session.cancel_many(
            request_target_ids=ids,
            request_target_bindings=bindings[:1],
        ),
        lambda: session.cancel_many(
            request_target_ids=tuple(f"venue-{index}" for index in range(101)),
            request_target_bindings=tuple(
                (f"venue-{index}", bindings[0][1]) for index in range(101)
            ),
        ),
        lambda: session.cancel_many(
            request_target_ids=("venue-order-a,venue-order-b",),
            request_target_bindings=(("venue-order-a,venue-order-b", bindings[0][1]),),
        ),
    )
    try:
        for call in invalid_calls:
            with pytest.raises(GatewayError, match="MUTATION_REQUEST_INVALID"):
                call()
        assert client.cancel_one_calls == []
        assert client.cancel_many_calls == []
    finally:
        session.close()
        lock.close()
        gateway.close()


def test_cancel_market_requires_complete_known_exact_market_scope(tmp_path: Path):
    client = FakeClient()
    gateway, lock, session, bindings = _known_order_session(tmp_path, client)
    ids = tuple(target for target, _owner in bindings)
    try:
        for market_id, target_ids, target_bindings in (
            ("market:a", ids[:1], bindings[:1]),
            ("market:unknown", ids, bindings),
            ("market:a", (), ()),
        ):
            with pytest.raises(GatewayError, match="MUTATION_REQUEST_INVALID"):
                session.cancel_market(
                    request_market_id=market_id,
                    request_target_ids=target_ids,
                    request_target_bindings=target_bindings,
                )
        assert client.cancel_market_calls == []
    finally:
        session.close()
        lock.close()
        gateway.close()


def test_cancel_all_persists_complete_locally_known_scope(tmp_path: Path):
    client = FakeClient(
        cancel_response=_CancelResponse(canceled=("venue-order-a", "venue-order-b"))
    )
    gateway, lock, session, bindings = _known_order_session(tmp_path, client)
    try:
        session.cancel_all()
        started = [
            event
            for event in gateway.gate_b_events()
            if event.event_type == "GATE_B_CANCEL_ATTEMPT_STARTED"
        ][-1]
        assert tuple(started.data["request_target_ids"]) == (
            "venue-order-a",
            "venue-order-b",
        )
        assert (
            tuple(tuple(item) for item in started.data["request_target_bindings"])
            == bindings
        )
    finally:
        session.close()
        lock.close()
        gateway.close()


def test_started_persistence_failure_prevents_sdk_transmit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    client = FakeClient()
    gateway, lock, session, bindings = _known_order_session(tmp_path, client)
    original = gateway.record_gate_b_event

    def fail_started(event_type, data, **kwargs):
        if event_type == "GATE_B_CANCEL_ATTEMPT_STARTED":
            raise GatewayError("STORE_WRITE_FAILED")
        return original(event_type, data, **kwargs)

    monkeypatch.setattr(gateway, "record_gate_b_event", fail_started)
    try:
        with pytest.raises(GatewayError, match="STORE_WRITE_FAILED"):
            session.cancel_one(
                request_target_ids=(bindings[0][0],),
                request_target_bindings=(bindings[0],),
            )
        assert client.cancel_one_calls == []
    finally:
        session.close()
        lock.close()
        gateway.close()


def test_all_authenticated_reads_are_exercised_and_bounded():
    client = FakeClient(trades=("t1",))
    snapshot = _session(client).account_snapshot()
    assert snapshot["account_trades"] == 1
    assert client.read_calls == {
        "balance": 1,
        "open_orders": 1,
        "trades": 1,
        "positions": 1,
    }
    with pytest.raises(GatewayError, match="AUTHENTICATED_READ_FAILED"):
        _session(FakeClient(trades=range(101))).account_snapshot()


def test_receipt_binds_all_before_and_after_account_fields(tmp_path: Path):
    receipt, _state = _durable_probe(tmp_path, FakeClient())
    document = receipt.as_receipt_document()
    for field in (
        "open_orders_before",
        "open_orders_after",
        "positions_before",
        "positions_after",
        "collateral_balance_before",
        "collateral_balance_after",
        "gate_b_reconciliation_state",
    ):
        assert field in document
    assert (
        gate_b_mod._sha("gatebreceipt:sha256:", receipt.to_public_mapping())
        == receipt.receipt_id
    )


def test_nonzero_after_state_prevents_pass(tmp_path: Path):
    class ChangedBalanceClient(FakeClient):
        def get_balance_allowance(self, *, asset_type):
            self.read_calls["balance"] += 1
            return _Balance("0" if self.read_calls["balance"] == 1 else "1")

    with pytest.raises(GatewayError, match="CANCEL_PROBE_AMBIGUOUS"):
        _durable_probe(tmp_path, ChangedBalanceClient())


# --- WP174B installed-SDK deployment-contract regression (real 0.10.0 import path) ---


def test_installed_sdk_cancel_response_contract_and_scope_classification():
    from polymarket.models.clob.cancel import CancelOrdersResponse

    empty = CancelOrdersResponse(canceled=(), not_canceled={})
    assert gate_b_mod._summarize_cancel_response(empty, expected_target_ids=()) == (
        "DEFINITIVE_ACCEPTED",
        {"canceled_count": 0, "not_canceled_count": 0},
    )

    accepted = CancelOrdersResponse(
        canceled=("venue-order-a", "venue-order-b"), not_canceled={}
    )
    assert (
        gate_b_mod._summarize_cancel_response(
            accepted, expected_target_ids=("venue-order-a", "venue-order-b")
        )[0]
        == "DEFINITIVE_ACCEPTED"
    )

    rejected = CancelOrdersResponse(
        canceled=(),
        not_canceled={
            "venue-order-a": SECRET_SENTINEL,
            "venue-order-b": "different private venue reason",
        },
    )
    rejected_result = gate_b_mod._summarize_cancel_response(
        rejected, expected_target_ids=("venue-order-a", "venue-order-b")
    )
    assert rejected_result == (
        "DEFINITIVE_REJECTED",
        {"canceled_count": 0, "not_canceled_count": 2},
    )
    assert SECRET_SENTINEL not in repr(rejected_result)

    ambiguous_responses = (
        CancelOrdersResponse(canceled=("venue-order-a",), not_canceled={}),
        CancelOrdersResponse(
            canceled=("venue-order-a",),
            not_canceled={"venue-order-b": SECRET_SENTINEL},
        ),
        CancelOrdersResponse(canceled=("unexpected-order",), not_canceled={}),
        CancelOrdersResponse(
            canceled=(), not_canceled={"unexpected-order": SECRET_SENTINEL}
        ),
    )
    for response in ambiguous_responses:
        result = gate_b_mod._summarize_cancel_response(
            response, expected_target_ids=("venue-order-a", "venue-order-b")
        )
        assert result[0] == "AMBIGUOUS"
        assert SECRET_SENTINEL not in repr(result)


def test_installed_sdk_rejection_reason_never_enters_durable_output(tmp_path: Path):
    from polymarket.models.clob.cancel import CancelOrdersResponse

    client = FakeClient(
        cancel_response=CancelOrdersResponse(
            canceled=(), not_canceled={"venue-order-a": SECRET_SENTINEL}
        )
    )
    gateway, lock, session, bindings = _known_order_session(tmp_path, client, count=1)
    try:
        result = session.cancel_one(
            request_target_ids=(bindings[0][0],),
            request_target_bindings=(bindings[0],),
        )
        assert result["cancel_result"] == "DEFINITIVE_REJECTED"
        assert result["not_canceled_count"] == 1
        assert SECRET_SENTINEL not in repr(result)
        assert SECRET_SENTINEL not in repr(
            [dict(event.data) for event in gateway.gate_b_events()]
        )
    finally:
        session.close()
        lock.close()
        gateway.close()

    ambiguous_root = tmp_path / "ambiguous"
    ambiguous_root.mkdir()
    ambiguous_client = FakeClient(
        cancel_response=CancelOrdersResponse(
            canceled=("venue-order-a",),
            not_canceled={"venue-order-b": SECRET_SENTINEL},
        )
    )
    gateway, lock, session, _bindings = _known_order_session(
        ambiguous_root, ambiguous_client
    )
    try:
        with pytest.raises(GatewayError, match="CANCEL_PROBE_AMBIGUOUS") as exc:
            session.cancel_all()
        assert SECRET_SENTINEL not in str(exc.value)
        assert SECRET_SENTINEL not in repr(
            [dict(event.data) for event in gateway.gate_b_events()]
        )
    finally:
        session.close()
        lock.close()
        gateway.close()


class _RealPathCtx:
    wallet_type = "DEPOSIT_WALLET"
    wallet = WALLET
    relayer = object()


class _RealPathClient:
    def __init__(self):
        self._ctx = _RealPathCtx()
        self.closed = False
        self.deployed_called = False

    def close(self):
        self.closed = True

    def _deploy_default_deposit_wallet(self):  # must never be called
        self.deployed_called = True


def _patch_sdk_path(monkeypatch, *, deployed: bool):
    """Mock the real 0.10.0 construction + deployment read; record the type arg."""
    import polymarket._internal.actions.relayer.deployed as dep

    holder = {}
    calls = {}

    def _fake_create(**_kw):
        holder["client"] = _RealPathClient()
        return holder["client"]

    monkeypatch.setattr(gate_b_mod.SecureClient, "_create", staticmethod(_fake_create))

    def _fake_fetch(_relayer, *, address, type=None):
        calls["type"] = type
        calls["address"] = address
        return deployed

    monkeypatch.setattr(dep, "fetch_deployed_sync", _fake_fetch)
    return holder, calls, dep


def test_installed_sdk_deployment_contract_imports_resolve():
    # (1) The exact 0.10.0 module contract Side named must import cleanly.
    from polymarket._internal.actions.relayer.deployed import (
        RelayerTransactionType,
        fetch_deployed_sync,
    )

    assert hasattr(RelayerTransactionType, "WALLET")
    assert callable(fetch_deployed_sync)


def test_deposit_wallet_deployment_lookup_uses_wallet_type_and_returns_client(
    monkeypatch,
):
    from polymarket._internal.actions.relayer.deployed import RelayerTransactionType

    holder, calls, _dep = _patch_sdk_path(monkeypatch, deployed=True)
    out = gate_b_mod.create_deposit_wallet_client("0xnonfunctional", WALLET)
    # (2) DEPOSIT_WALLET deployment lookup uses RelayerTransactionType.WALLET
    assert calls["type"] == RelayerTransactionType.WALLET
    # (3) deployed=True returns the constructed client
    assert out is holder["client"]
    # (5) no deployment method invoked
    assert holder["client"].deployed_called is False


def test_undeployed_wallet_fails_closed_and_client_closed(monkeypatch):
    holder, _calls, _dep = _patch_sdk_path(monkeypatch, deployed=False)
    # (4) deployed=False fails SDK_SIDE_EFFECT_UNAUTHORIZED
    with pytest.raises(GatewayError, match="SDK_SIDE_EFFECT_UNAUTHORIZED"):
        gate_b_mod.create_deposit_wallet_client("0xnonfunctional", WALLET)
    # (5) no deployment method invoked; (6) credential client closed on failure
    assert holder["client"].deployed_called is False
    assert holder["client"].closed is True


# --------------------------------------------------------------------------- S10-LIVE-ORCH-01 (R002)

LIVE_ORCH_EXCHANGE = "0xe111180000d2663c0091e4f400237545b87b996b"


class _LiveOrchClient(FakeClient):
    """FakeClient plus the bounded LIVE-ORCH read surface; no mutation is reachable."""

    def __init__(self, **kw):
        super().__init__(**kw)
        self._ctx.environment_config.standard_exchange = LIVE_ORCH_EXCHANGE
        self._ctx.environment_config.neg_risk_exchange = "0x" + "e" * 40
        self.calls: list[str] = []
        self.market_builds: list[dict] = []

    def get_balance_allowance(self, *, asset_type):
        self.calls.append("balance")
        return SimpleNamespace(balance=97_500_000, allowances={LIVE_ORCH_EXCHANGE: 50_000_000})

    def get_closed_only_mode(self):
        self.calls.append("closed_only")
        return False

    def get_order(self, *, order_id):
        self.calls.append("get_order")
        return _open_order(order_id, status="CANCELED")

    def create_market_order(self, **kwargs):
        self.market_builds.append(dict(kwargs))
        return _SignedOrder()

    def __getattr__(self, name):
        # Any wallet deployment / approval / relayer / redemption surface is absent.
        raise AttributeError(name)


def _open_order(order_id, *, status="LIVE", matched="0"):
    return SimpleNamespace(
        id=order_id, asset_id=TOKEN, condition_id="0x" + "ab" * 32, side="BUY", price="0.51",
        original_size="8", size_matched=matched, status=status, order_type="GTC",
    )


def _trade(trade_id, *, status, taker="0x" + "1" * 64):
    return SimpleNamespace(
        id=trade_id, status=status, asset_id=TOKEN, side="BUY", taker_order_id=taker,
        trader_side="TAKER", price="0.52", size="8",
        maker_orders=(SimpleNamespace(order_id="0x" + "9" * 64, price="0.52", matched_amount="8"),),
    )


def _position(**changes):
    values = dict(
        asset_id=TOKEN, condition_id="0x" + "ab" * 32, current_size="8", entry_cost_usdc="4.16",
        entry_fees_usdc="0.06", total_cost_usdc="4.22", realized_pnl="-0.5", total_pnl="-1",
        status=SimpleNamespace(value="OPEN"), current_value="0.01",
    )
    values.update(changes)
    return SimpleNamespace(**values)


def test_live_orch_account_truth_is_bounded_exact_and_sanitized():
    client = _LiveOrchClient(
        open_orders=[_open_order("0x" + "2" * 64)],
        trades=[_trade("trade-a", status="TRADE_STATUS_MINED"),
                _trade("trade-b", status="CONFIRMED"), _trade("trade-c", status="FAILED")],
        positions=[_position()],
    )
    session = _session(client)
    with pytest.raises(GatewayError, match="LIVE_ORCH_REQUIRED"):
        session.live_orch_account_truth(object(), observed_time_ns=5)
    truth = session.live_orch_account_truth(gate_b_mod._LIVE_ORCH_ISSUER, observed_time_ns=5)
    assert truth.collateral_balance == "97.5"
    assert dict(truth.allowance_by_exchange) == {"exchange": "50"}
    assert [(t.trade_id, t.status) for t in truth.trades] == [
        ("trade-a", "MINED"), ("trade-b", "CONFIRMED"), ("trade-c", "FAILED")]
    assert truth.trades[0].maker_fills[0].matched_amount == "8"
    assert truth.open_orders[0].venue_order_id == "0x" + "2" * 64
    position = truth.positions[0]
    assert (position.total_cost_usdc, position.realized_pnl, position.total_pnl) == ("4.22", "-0.5", "-1")
    assert not hasattr(position, "current_value")
    assert truth.truth_id.startswith("liveorchaccount:sha256:")
    assert SECRET_SENTINEL not in repr(truth)
    # Reads only: no post, cancel, deploy, approval or relayer call.
    assert client.place_calls == 0 and client.cancel_one_calls == [] and client.cancel_all_calls == 0
    assert set(client.calls) == {"balance", "closed_only"}
    order = session.live_orch_order(gate_b_mod._LIVE_ORCH_ISSUER, "0x" + "3" * 64)
    assert order.status == "CANCELED"


@pytest.mark.parametrize("kind", ["open_orders", "trades", "positions"])
def test_live_orch_account_history_over_100_items_fails_closed(kind):
    items = {
        "open_orders": [_open_order("0x" + format(n, "064x")) for n in range(101)],
        "trades": [_trade(f"t-{n}", status="CONFIRMED") for n in range(101)],
        "positions": [_position(asset_id=str(10**40 + n)) for n in range(101)],
    }[kind]
    session = _session(_LiveOrchClient(**{kind: items}))
    with pytest.raises(GatewayError, match="ACCOUNT_HISTORY_LIMIT_EXCEEDED"):
        session.live_orch_account_truth(gate_b_mod._LIVE_ORCH_ISSUER, observed_time_ns=5)


def test_live_orch_read_errors_and_malformed_models_are_sanitized():
    client = _LiveOrchClient(trades=[_trade("t", status="CONFIRMED")])

    def boom(**_kw):
        raise RuntimeError(f"upstream failure leaking {SECRET_SENTINEL}")

    client.list_account_trades = boom
    session = _session(client)
    with pytest.raises(GatewayError) as excinfo:
        session.live_orch_account_truth(gate_b_mod._LIVE_ORCH_ISSUER, observed_time_ns=5)
    assert excinfo.value.code == "AUTHENTICATED_READ_FAILED"
    assert SECRET_SENTINEL not in str(excinfo.value)
    bad = _session(_LiveOrchClient(positions=[_position(total_cost_usdc="-1")]))
    with pytest.raises(GatewayError, match="ACCOUNT_TRUTH_INVALID"):
        bad.live_orch_account_truth(gate_b_mod._LIVE_ORCH_ISSUER, observed_time_ns=5)


def test_local_limit_and_aggressive_buy_construction_never_posts():
    client = _LiveOrchClient()
    session = _session(client)
    permit = GateCLivePermit._issue(gate_b_mod._GATE_C_ISSUER, "liveorchcreate:sha256:" + "1" * 64)
    handle = session.gate_c_transport(permit)
    handle.build(asset_id=TOKEN, price=0.51, size=8, side="BUY", post_only=True)
    from decimal import Decimal

    handle.build_aggressive_buy(asset_id=TOKEN, amount=Decimal("4.4"), max_spend=Decimal("4.4666"),
                                max_price=Decimal("0.55"), order_type="FOK")
    assert client.market_builds == [{"token_id": TOKEN, "side": "BUY", "amount": Decimal("4.4"),
                                     "max_spend": Decimal("4.4666"), "max_price": Decimal("0.55"),
                                     "order_type": "FOK"}]
    with pytest.raises(GatewayError, match="ORDER_ENCODING_UNSUPPORTED"):
        handle.build_aggressive_buy(asset_id=TOKEN, amount=Decimal("1"), max_spend=Decimal("1"),
                                    max_price=Decimal("0.5"), order_type="GTC")
    # Building never posts; transmit stays locked until Gate-C consumes the permit.
    assert client.place_calls == 0
    with pytest.raises(GatewayError, match="GATE_C_REQUIRED"):
        handle.transmit(object())


def test_live_orch_cancel_requires_gate_c_and_never_resends_an_identity(tmp_path):
    client = _LiveOrchClient(cancel_response=_CancelResponse(canceled=("0x" + "4" * 64,)))
    _store, gateway, lock, session = _durable_session(tmp_path, client)
    try:
        attempt = CancelAttempt(
            operation="CANCEL_ONE", request_target_ids=("0x" + "4" * 64,),
            request_target_bindings=(("0x" + "4" * 64, "liveorchepisode:sha256:" + "5" * 64),),
            request_market_id=None, attempt_sequence=1, prior_reconciliation_state="HEALTHY",
        )
        with pytest.raises(GatewayError, match="LIVE_ORCH_REQUIRED"):
            session.live_orch_cancel(object(), attempt, prior_attempt_ids=())
        seeded = CancelAttempt(
            operation="CANCEL_ONE", request_target_ids=attempt.request_target_ids,
            request_target_bindings=attempt.request_target_bindings, request_market_id=None,
            attempt_sequence=2, prior_reconciliation_state="HEALTHY",
        )
        with pytest.raises(GatewayError, match="MUTATION_ALREADY_TRANSMITTED"):
            session.live_orch_cancel(gate_b_mod._GATE_C_ISSUER, seeded,
                                     prior_attempt_ids=(seeded.identity,))
        assert client.cancel_one_calls == [] and seeded.identity != attempt.identity
        result, _summary = session.live_orch_cancel(gate_b_mod._GATE_C_ISSUER, attempt, prior_attempt_ids=())
        assert result == "DEFINITIVE_ACCEPTED" and client.cancel_one_calls == ["0x" + "4" * 64]
        with pytest.raises(GatewayError, match="MUTATION_ALREADY_TRANSMITTED"):
            session.live_orch_cancel(gate_b_mod._GATE_C_ISSUER, attempt, prior_attempt_ids=())
    finally:
        session.close()
        lock.close()
        gateway.close()


def test_fee_enabled_standard_market_metadata_usable_for_live_orch():
    client = FakeClient()
    client.get_market = lambda *, id: SimpleNamespace(
        id=id, condition_id="condition-a",
        state=SimpleNamespace(active=True, closed=False, accepting_orders=True,
                              enable_order_book=True, neg_risk=False),
        trading=SimpleNamespace(seconds_delay=0, fees_enabled=True,
                                fee_schedule=SimpleNamespace(rate="0.0333", taker_only=True)),
        outcomes=SimpleNamespace(yes=SimpleNamespace(token_id=TOKEN),
                                 no=SimpleNamespace(token_id="other-token")),
    )
    client.get_order_book = lambda *, token_id: SimpleNamespace(
        asset_id=token_id, condition_id="condition-a", neg_risk=False,
        tick_size="0.01", min_order_size="5",
    )
    session = _session(client)
    with pytest.raises(GatewayError, match="MARKET_METADATA_INVALID"):
        session.gate_c_market_metadata(gate_b_mod._GATE_C_ISSUER, market_id="516710",
                                       token_id=TOKEN, observed_time_ns=100)
    metadata = session.gate_c_market_metadata(
        gate_b_mod._GATE_C_ISSUER, market_id="516710", token_id=TOKEN, observed_time_ns=100,
        fees_enabled_allowed=True,
    )
    assert metadata.fee_rate_bps == "333"
    # Gamma market id, condition id and token id stay distinct.
    assert (metadata.market_id, metadata.condition_id, metadata.token_id) == (
        "516710", "condition-a", TOKEN)


# --------------------------------------------------------------------------- S10-ALPHA-HUNTER-PILOT-02

# Synthetic, non-secret 0x-prefixed 64-hex sentinel (never a real key).
SESSION_SENTINEL = "0x" + "5e55" * 16


def _write_key(directory: Path, raw: bytes, mode: int = 0o600) -> Path:
    import os

    path = directory / "polymarket-session-key"
    path.write_bytes(raw)
    os.chmod(path, mode)
    return path


def test_credential_directory_session_key_provider_fail_closed(tmp_path, monkeypatch):
    import os

    from src.execution_gateway.gate_b import CredentialDirectorySessionKeyProvider

    provider = CredentialDirectorySessionKeyProvider()
    assert "CREDENTIALS_DIRECTORY" not in repr(provider) and SESSION_SENTINEL not in repr(provider)
    # Non-POSIX hosts refuse before any environment or file access.
    monkeypatch.setattr(gate_b_mod.os, "name", "nt")
    monkeypatch.setenv("CREDENTIALS_DIRECTORY", str(tmp_path))
    with pytest.raises(GatewayError, match="SECRET_INPUT_UNAVAILABLE"):
        provider.acquire()
    monkeypatch.undo()
    if os.name != "posix":
        pytest.skip("POSIX credential-file checks (O_NOFOLLOW/fstat owner/mode) run on POSIX hosts only")
    credentials = tmp_path / "credentials"
    credentials.mkdir()
    monkeypatch.delenv("CREDENTIALS_DIRECTORY", raising=False)
    with pytest.raises(GatewayError, match="SECRET_INPUT_UNAVAILABLE"):
        provider.acquire()
    monkeypatch.setenv("CREDENTIALS_DIRECTORY", "relative/credentials")
    with pytest.raises(GatewayError, match="SECRET_INPUT_INVALID"):
        provider.acquire()
    monkeypatch.setenv("CREDENTIALS_DIRECTORY", str(credentials))
    with pytest.raises(GatewayError, match="SECRET_INPUT_UNAVAILABLE"):
        provider.acquire()  # missing file
    path = _write_key(credentials, SESSION_SENTINEL.encode() + b"\n")
    lease = provider.acquire()  # synthetic non-secret positive control
    assert lease.reveal() == SESSION_SENTINEL and SESSION_SENTINEL not in repr(lease)
    lease.close()
    cases = [
        (0o640, SESSION_SENTINEL.encode()), (0o604, SESSION_SENTINEL.encode()), (0o610, SESSION_SENTINEL.encode()),
        (0o600, SESSION_SENTINEL.encode() + b"\n" * 2), (0o600, SESSION_SENTINEL[2:].encode()),
        (0o600, SESSION_SENTINEL[:-1].encode()), (0o600, (SESSION_SENTINEL + "\n" + SESSION_SENTINEL).encode()),
        (0o600, SESSION_SENTINEL.upper().encode()), (0o600, b" " + SESSION_SENTINEL.encode()),
        (0o600, b"x" * 129), (0o600, b""), (0o600, SESSION_SENTINEL.encode() + b"\x00"),
    ]
    for mode, raw in cases:
        path.unlink()
        _write_key(credentials, raw, mode)
        with pytest.raises(GatewayError, match="SECRET_INPUT_INVALID") as error:
            provider.acquire()
        assert SESSION_SENTINEL not in str(error.value) and SESSION_SENTINEL not in repr(error.value)
    path.unlink()
    target = _write_key(tmp_path, SESSION_SENTINEL.encode())
    os.symlink(target, path)
    with pytest.raises(GatewayError, match="SECRET_INPUT_INVALID"):
        provider.acquire()  # symlink is never followed
    path.unlink()
    path.mkdir()
    with pytest.raises(GatewayError, match="SECRET_INPUT_INVALID"):
        provider.acquire()  # not a regular file
    path.rmdir()
    _write_key(credentials, SESSION_SENTINEL.encode())
    other_uid = os.geteuid() + 1
    monkeypatch.setattr(gate_b_mod.os, "geteuid", lambda: other_uid)
    with pytest.raises(GatewayError, match="SECRET_INPUT_INVALID"):
        provider.acquire()  # wrong owner
    monkeypatch.undo()
    monkeypatch.setenv("CREDENTIALS_DIRECTORY", str(credentials))
    # Signer mismatch: a valid key whose client signer differs from policy refuses (no order).
    policy = GateBIdentityPolicy(SIGNER, WALLET, signer_type="SESSION_KEY")
    with pytest.raises(GatewayError, match="SIGNER_MISMATCH"):
        GateBSession.authenticate(provider, policy, client_factory=_factory(
            FakeClient(signer="0x" + "c" * 40, signer_type="SESSION_KEY")))


def test_session_key_identity_bound_to_custody_policy(tmp_path, monkeypatch):
    from src.execution_gateway.gate_b import CredentialDirectorySessionKeyProvider
    from src.execution_gateway import live_orch as LO_SRC
    from tests.execution_gateway import test_gateway as TG
    from tests.execution_gateway import test_live_orch as LO
    from tests.exploratory_gate_c import test_exploratory_gate_c as XG
    from tests.live_pilot import test_hunter_cycle as HC

    acquired = []
    monkeypatch.setattr(CredentialDirectorySessionKeyProvider, "acquire",
                        lambda self: acquired.append(1) or GateBSecretLease(SESSION_SENTINEL))
    session_policy = GateBIdentityPolicy(SIGNER, WALLET, signer_type="SESSION_KEY")
    # OWNER policy + an owner key paired with a non-derived wallet (SDK classifies SESSION_KEY).
    with pytest.raises(GatewayError, match="SIGNING_IDENTITY_INVALID"):
        _session(FakeClient(signer_type="SESSION_KEY"))
    # SESSION_KEY policy + OWNER-classified client.
    with pytest.raises(GatewayError, match="SIGNING_IDENTITY_INVALID"):
        GateBSession.authenticate(CredentialDirectorySessionKeyProvider(), session_policy,
                                  client_factory=_factory(FakeClient(signer_type="OWNER")))
    # SESSION_KEY policy with a non-allowlisted provider refuses before acquire().
    interactive = InteractiveGateBSecretProvider()
    monkeypatch.setattr(interactive, "acquire", lambda: pytest.fail("acquire before custody check"))
    for provider in (interactive, _provider()):
        with pytest.raises(GatewayError, match="SIGNING_IDENTITY_INVALID"):
            GateBSession.authenticate(provider, session_policy, client_factory=_factory(
                FakeClient(signer_type="SESSION_KEY")))
    for bad in ("session_key", "", None, "SESSION-KEY"):
        with pytest.raises(GatewayError, match="SIGNING_IDENTITY_INVALID"):
            GateBIdentityPolicy(SIGNER, WALLET, signer_type=bad).validate()
    # Synthetic SESSION_KEY positive control authenticates; OWNER default is unchanged.
    acquired.clear()
    session = GateBSession.authenticate(CredentialDirectorySessionKeyProvider(), session_policy,
                                        client_factory=_factory(FakeClient(signer_type="SESSION_KEY")))
    assert acquired == [1] and session.public_signer == SIGNER and GateBIdentityPolicy(SIGNER, WALLET).signer_type == "OWNER"
    _session(FakeClient())
    test_non_owner_signer_type_rejected()
    # SESSION_KEY under V1_CANARY refuses before any secret request or ledger write.
    world = XG.make_world(tmp_path / "world")
    harness = LO.Harness(tmp_path / "v1", world)
    deps = harness.deps()
    deps.signer_type = "SESSION_KEY"
    result = LO_SRC.LiveOrchestrator(harness.config(), dependencies=deps).reconcile()
    assert (result.status, result.code) == ("BLOCKED", "SIGNING_IDENTITY_INVALID")
    assert harness.secret_requests == 0 and not harness.orchestrator().store_path.exists()
    # Read adapter default rejects SESSION_KEY; owner-record attestation and suspension latch.
    TG.test_read_adapter_accepted_signer_type_defaults_to_owner(monkeypatch)
    monkeypatch.undo()
    with pytest.MonkeyPatch.context() as patch:
        assert HC.session_key_attestation_matrix(tmp_path / "hunter", patch)
