"""S10-LIVE-ORCH-01 offline LIVE-ORCH matrix (R005 and supporting R003/R004 evidence).

Every test is deterministic and local: real verified STRAT-LIFE / Hermes strategy-manager
stores and real ExploratoryGateCPermit records, fixed in-memory public venue payloads, the
real pinned polymarket-client 0.10.0 response/account models and order-amount math, and an
offline fake authenticated client.  No test performs real network, credential, account,
order, capital or live behavior.
"""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
import json
from pathlib import Path
import sqlite3

import pytest
from polymarket._internal.actions.orders.limit import _compute_limit_order_amounts
from polymarket._internal.actions.orders.market import _compute_market_order_amounts
from polymarket.models.clob.account import BalanceAllowance, ClobTrade, OpenOrder
from polymarket.models.clob.order_response import AcceptedOrder, RejectedOrder
from polymarket.models.clob.orders import SignedOrder
from polymarket.models.data.portfolio import Position

import src.execution_gateway.live_orch as L
from src.execution_gateway.gate_b import GateBSecretLease
from src.execution_gateway.gate_c import (
    GateCGeoblockProof,
    LiveOrchOrderSpec,
    classify_live_orch_create_response,
    inspect_live_orch_signed_buy,
)
from src.execution_gateway.gateway import (
    LIVE_ORCH_EPISODE_STATES,
    GatewayError,
    ProtectedExecutionGateway,
)
from src.exploratory_gate_c import build_exploratory_gate_c_permit
from tests.exploratory_gate_c import test_exploratory_gate_c as X

SIGNER = "0x" + "a" * 40
WALLET = "0x" + "b" * 40
EXCHANGE = "0xe111180000d2663c0091e4f400237545b87b996b"
RELEASE = "c" * 40
SECRET = "0xfeedfacefeedfacefeedfacefeedfacefeedfacefeedfacefeedfacefeedface"
ZERO32 = "0x" + "0" * 64
TOKEN, COND = X.TOKEN, X.COND


def oid(n: int) -> str:
    return "0x" + format(n, "064x")


# ---------------------------------------------------------------------------
# Offline SDK-shaped fake venue (real 0.10.0 models and amount math)
# ---------------------------------------------------------------------------


class _Ctx:
    signer_type = "OWNER"

    def __init__(self) -> None:
        self.environment_config = type(
            "Cfg", (), {"chain_id": 137, "standard_exchange": EXCHANGE,
                        "neg_risk_exchange": "0x" + "e" * 40}
        )()


class FakeVenue:
    """Authenticated-client stand-in.  ``place_*`` and approvals are never reachable."""

    def __init__(self, *, balance: str = "100", allowance: str = "100") -> None:
        self.signer, self.wallet = SIGNER, WALLET
        self.wallet_type = "DEPOSIT_WALLET"
        self.environment = type("Env", (), {"name": "production"})()
        self._ctx = _Ctx()
        self.balance = Decimal(balance)
        self.allowance = Decimal(allowance)
        self.orders: dict[str, dict] = {}
        self.trades: list[dict] = []
        self.positions: list[dict] = []
        self.posts: list[SignedOrder] = []
        self.cancels: list[str] = []
        self.on_post = lambda venue, signed: RejectedOrder(code="fok_not_filled", message="x")
        self.on_cancel = lambda venue, order_id: venue.cancel_live(order_id)
        self.market_amount_override = None
        self.next_order = 1
        self.read_error = None
        self.closed = False

    # reads ----------------------------------------------------------------
    def get_balance_allowance(self, *, asset_type):
        assert asset_type == "COLLATERAL"
        if self.read_error:
            raise RuntimeError(f"read failed {SECRET}")
        return BalanceAllowance.model_validate({
            "balance": str(int(self.balance * 1_000_000)),
            "allowances": {EXCHANGE: str(int(self.allowance * 1_000_000))},
        })

    def _order_model(self, row: dict) -> OpenOrder:
        return OpenOrder.model_validate({
            "id": row["id"], "market": COND, "asset_id": row.get("token", TOKEN),
            "owner": "owner", "maker_address": WALLET, "side": "BUY", "price": row["price"],
            "original_size": row["size"], "size_matched": row.get("matched", "0"),
            "outcome": "Yes", "order_type": row["type"], "status": row["status"],
            "created_at": 1760000000,
        })

    def list_open_orders(self, **_kw):
        return [self._order_model(row) for row in self.orders.values() if row["status"] == "LIVE"]

    def get_order(self, *, order_id):
        if order_id not in self.orders:
            raise RuntimeError(f"not found {SECRET}")
        return self._order_model(self.orders[order_id])

    def list_account_trades(self, **_kw):
        return [ClobTrade.model_validate(row) for row in self.trades]

    def list_positions(self, **kw):
        assert kw == {"user": WALLET, "page_size": 100}
        return [Position.model_validate(row) for row in self.positions]

    def get_closed_only_mode(self):
        return False

    # local signing (never posts) -----------------------------------------
    def _signed(self, *, maker, taker, order_type, expiration=0, post_only=False):
        return SignedOrder(
            builder=ZERO32, expiration=expiration, maker=WALLET, maker_amount=maker,
            metadata=ZERO32, order_type=order_type, salt=7, side="BUY",
            signature="0xsignaturebytesneverpersisted", signature_type=3, signer=WALLET,
            taker_amount=taker, timestamp=1, token_id=TOKEN, post_only=post_only,
        )

    def create_limit_order(self, *, asset_id=None, token_id=None, price, size, side,
                           post_only=False, expiration=None, builder_code=None):
        maker, taker = _compute_limit_order_amounts(
            price=Decimal(price), size=Decimal(size), side=side, tick_size=Decimal("0.01")
        )
        return self._signed(maker=maker, taker=taker,
                            order_type="GTC" if expiration is None else "GTD",
                            expiration=expiration or 0, post_only=post_only)

    def create_market_order(self, *, asset_id=None, token_id=None, side, amount=None,
                            shares=None, max_spend=None, max_price=None, min_price=None,
                            order_type="FAK", builder_code=None):
        assert side == "BUY" and max_price is not None and max_spend is not None
        if self.market_amount_override is not None:
            amount = self.market_amount_override
        maker, taker = _compute_market_order_amounts(
            amount=Decimal(amount), price=Decimal(max_price), side="BUY",
            tick_size=Decimal("0.01"), protect_price=True,
        )
        return self._signed(maker=maker, taker=taker, order_type=order_type)

    # mutations --------------------------------------------------------------
    def post_order(self, signed):
        self.posts.append(signed)
        return self.on_post(self, signed)

    def cancel_order(self, *, order_id):
        self.cancels.append(order_id)
        return self.on_cancel(self, order_id)

    def place_limit_order(self, **_kw):
        raise AssertionError("place_limit_order is forbidden")

    def place_market_order(self, **_kw):
        raise AssertionError("place_market_order is forbidden")

    def approve(self, *_a, **_k):
        raise AssertionError("approval is forbidden")

    def close(self):
        self.closed = True

    # venue simulation helpers ----------------------------------------------
    def rest(self, signed, *, price: str, size: str) -> AcceptedOrder:
        order_id = oid(self.next_order)
        self.next_order += 1
        self.orders[order_id] = {"id": order_id, "price": price, "size": size,
                                 "type": signed.order_type, "status": "LIVE"}
        return AcceptedOrder(order_id=order_id, status="live", making_amount="0",
                             taking_amount="0", trade_ids=(), transactions_hashes=())

    def cancel_live(self, order_id: str):
        row = self.orders.get(order_id)
        if row is not None and row["status"] == "LIVE":
            row["status"] = "CANCELED"
            return type("R", (), {"canceled": (order_id,), "not_canceled": {}})()
        return type("R", (), {"canceled": (), "not_canceled": {order_id: "not live"}})()

    def fill_taker(self, signed, *, shares: str, price: str, status: str = "CONFIRMED",
                   trade_id: str = "trade-1", fee: str = "0") -> AcceptedOrder:
        order_id = oid(self.next_order)
        self.next_order += 1
        self.orders[order_id] = {"id": order_id, "price": price, "size": shares,
                                 "matched": shares, "type": signed.order_type,
                                 "status": "MATCHED"}
        self.add_trade(trade_id, taker=order_id, shares=shares, price=price, status=status)
        principal = Decimal(shares) * Decimal(price)
        self.balance -= principal + Decimal(fee)
        self.set_position(shares=shares, cost=str(principal), fees=fee)
        return AcceptedOrder(order_id=order_id, status="matched",
                             making_amount=str(principal), taking_amount=shares,
                             trade_ids=(trade_id,), transactions_hashes=())

    def add_trade(self, trade_id, *, taker, shares, price, status):
        self.trades.append({
            "id": trade_id, "market": COND, "asset_id": TOKEN, "owner": "owner",
            "maker_address": WALLET, "taker_order_id": taker, "side": "BUY",
            "trader_side": "TAKER", "price": price, "size": shares, "outcome": "Yes",
            "status": status, "fee_rate_bps": "0", "bucket_index": 0,
            "transaction_hash": "0x" + "9" * 64,
            "maker_orders": [{"order_id": oid(999), "asset_id": TOKEN,
                              "maker_address": "0x" + "d" * 40, "owner": "other",
                              "side": "SELL", "price": price, "matched_amount": shares,
                              "outcome": "Yes"}],
            "match_time": 1760000000, "last_update": 1760000001,
        })

    def set_position(self, *, shares, cost, fees="0", token=TOKEN, realized="0",
                     total=None, value=None, status="OPEN"):
        total_cost = str(Decimal(cost) + Decimal(fees))
        self.positions = [row for row in self.positions if row["token_id"] != token]
        self.positions.append({
            "proxy_wallet": WALLET, "token_id": token, "condition_id": COND,
            "current_size": shares, "avg_price": "0.5", "entry_cost_usdc": cost,
            "entry_fees_usdc": fees, "total_cost_usdc": total_cost,
            "current_price": "0.5", "current_value": value or cost, "total_size": shares,
            "realized_pnl": realized, "unrealized_pnl": "0",
            "total_pnl": total if total is not None else realized, "percent_pnl": "0",
            "percent_realized_pnl": "0", "status": status, "redeemable": False,
            "mergeable": False, "negative_risk": False, "archived": False, "verified": True,
        })


# ---------------------------------------------------------------------------
# Harness: real permit + offline dependencies
# ---------------------------------------------------------------------------


GAMMA = X.gamma_doc(orderMinSize=1)


def make_permit(world, **intent_changes):
    values = dict(requested_shares="8")
    values.update(intent_changes)
    intent = X.intent(world, **values)
    ex = X.execution(world, i=intent, s=X.snap(gamma=GAMMA))
    decision = X.evaluate(world, ex)
    assert decision.status == "PERMIT_ELIGIBLE", decision.reason_codes
    return build_exploratory_gate_c_permit(decision, execution_intent=intent), intent


PASSIVE = dict(execution_style="PASSIVE_MAKER", order_type="GTC", post_only=True,
               price_limit="0.51")


def host_doc(**changes):
    doc = {
        "schema_id": "polymarket-execution-host-currentness", "schema_version": "1.0.0",
        "status": "EXECUTION_HOST_CURRENT", "verification_mode": "strict",
        "host_instance_id": "pmhost-v1:" + "1" * 64, "boot_instance_id": "pmboot-v1:" + "2" * 64,
        "bound_release_sha": RELEASE, "active_release_sha": RELEASE,
        "release_manifest_sha256": "3" * 64, "critical_probe_unit_sha256": "4" * 64,
        "critical_probe_state": "inactive", "telemetry_timer_state": "active",
        "research_target_state": "active", "ntp_state": "synchronized",
        "firewall_state": "ssh_only_inbound", "persistent_state": "present",
    }
    doc.update(changes)
    return doc


class Harness:
    def __init__(self, tmp_path: Path, world, venue: FakeVenue | None = None) -> None:
        self.tmp = tmp_path
        self.world = world
        self.venue = venue or FakeVenue()
        self.now = X.AT + 1_000
        self.host = host_doc()
        self.blocked = False
        self.gamma = GAMMA
        self.book = X.book_doc()
        self.pauses: list[float] = []
        self.secret_requests = 0
        self.pause_hook = None

    def clock(self) -> int:
        self.now += 1_000_000
        return self.now

    def deps(self) -> L.LiveOrchDependencies:
        harness = self

        class _Provider:
            def acquire(self):
                harness.secret_requests += 1
                return GateBSecretLease(SECRET)

        def pause(seconds):
            harness.pauses.append(seconds)
            harness.now += int(seconds * 1_000_000_000)
            if harness.pause_hook is not None:
                harness.pause_hook(harness)

        return L.LiveOrchDependencies(
            clock_ns=self.clock,
            host_currentness=lambda _config: dict(self.host),
            geoblock=lambda: GateCGeoblockProof.from_response(
                {"blocked": self.blocked, "country": "ZZ"}, observed_time_ns=self.now
            ),
            venue_fetcher=lambda **kw: X.snap(
                gamma=self.gamma, clob=self.book, completed=self.clock()
            ),
            secret_provider_factory=_Provider,
            client_factory=lambda key, wallet: self.venue,
            pause=pause,
        )

    def config(self) -> L.LiveOrchConfig:
        return L.LiveOrchConfig(
            state_root=self.tmp / "state", expected_signer=SIGNER, expected_wallet=WALLET,
            lifecycle_store_path=self.world.lifecycle, hermes_store_path=self.world.hermes,
            host=L.HostCurrentnessConfig(
                repository_root=self.tmp, binding_file=self.tmp / "b.json",
                active_release=self.tmp / "r", unit_dir=self.tmp / "u", ssh_port=22,
                expected_release_sha=RELEASE,
            ),
        )

    def orchestrator(self) -> L.LiveOrchestrator:
        return L.LiveOrchestrator(self.config(), dependencies=self.deps())

    def ledger(self) -> dict:
        path = self.orchestrator().store_path
        with ProtectedExecutionGateway.open(path, opened_time_ns=self.clock()) as gateway:
            return gateway.live_orch_checkpoint()

    def events(self) -> list[str]:
        path = self.orchestrator().store_path
        connection = sqlite3.connect(path)
        try:
            return [row[0] for row in connection.execute(
                "SELECT event_type FROM gateway_journal ORDER BY sequence")]
        finally:
            connection.close()


@pytest.fixture
def world(tmp_path):
    return X.make_world(tmp_path)


@pytest.fixture
def harness(tmp_path, world):
    return Harness(tmp_path, world)


def _accept_fill(shares="8", price="0.52", status="CONFIRMED", fee="0"):
    return lambda venue, signed: venue.fill_taker(
        signed, shares=shares, price=price, status=status, fee=fee
    )


# ---------------------------------------------------------------------------
# Capital envelope, side policy and authority gates
# ---------------------------------------------------------------------------


def test_capital_envelope_is_frozen_and_cannot_scale() -> None:
    envelope = L.LiveOrchCapitalEnvelope()
    envelope.validate()
    assert (L.AUTHORIZED_ACCOUNT_CAPITAL_USD, L.SINGLE_ORDER_WORST_CASE_MAX_USD,
            L.MAX_TOTAL_EARLY_COMMITMENT_USD, L.MIN_FREE_COLLATERAL_RESERVE_USD) == (
        Decimal("100"), Decimal("5"), Decimal("30"), Decimal("70"))
    assert L.AUTO_SCALING is False and L.MAX_CREATE_PER_CANARY == 1
    assert L.TYPICAL_INITIAL_ORDER_USD == (Decimal("3"), Decimal("5"))
    assert (L.MAX_OBSERVED_REALIZED_PNL_LOSS_USD, L.MAX_OBSERVED_POSITION_PNL_DRAWDOWN_USD,
            L.MAX_OBSERVED_CUMULATIVE_CANARY_LOSS_USD) == (Decimal("5"), Decimal("7.5"), Decimal("10"))
    for widened in (dict(single_order_worst_case_max_usd="6"),
                    dict(max_total_early_commitment_usd="31"),
                    dict(min_free_collateral_reserve_usd="69"),
                    dict(authorized_account_capital_usd="1000"),
                    dict(auto_scaling=True),
                    dict(max_observed_realized_pnl_loss_usd="50")):
        with pytest.raises(GatewayError, match="CAPITAL_ENVELOPE_INVALID"):
            L.LiveOrchCapitalEnvelope(**widened).validate()


def test_sell_permit_rejected_before_admission_signing_or_transmit(harness, world) -> None:
    permit, intent = make_permit(world, side="SELL", price_limit="0.49")
    result = harness.orchestrator().canary(permit, intent)
    assert (result.status, result.code) == ("BLOCKED", "SIDE_UNSUPPORTED_FIRST_CANARY")
    assert result.create_transmits == 0 and harness.venue.posts == []
    assert harness.secret_requests == 0
    assert not harness.orchestrator().store_path.exists()


def test_host_currentness_ntp_geoblock_and_permit_gates_block_before_auth(harness, world) -> None:
    permit, intent = make_permit(world)
    cases = [
        ("ntp_state", "unsynchronized", "HOST_NOT_CURRENT"),
        ("active_release_sha", "d" * 40, "HOST_NOT_CURRENT"),
        ("verification_mode", "observe", "HOST_NOT_CURRENT"),
        ("firewall_state", "open", "HOST_NOT_CURRENT"),
    ]
    for key, value, code in cases:
        harness.host = host_doc(**{key: value})
        assert harness.orchestrator().canary(permit, intent).code == code
    harness.host = host_doc()
    harness.blocked = True
    assert harness.orchestrator().canary(permit, intent).code == "ACCESS_NOT_ELIGIBLE"
    harness.blocked = False
    harness.now = permit.valid_until_ns + 1
    assert harness.orchestrator().canary(permit, intent).code == "PERMIT_EXPIRED"
    assert harness.secret_requests == 0 and harness.venue.posts == []


def test_permit_lineage_must_remain_current(harness, world) -> None:
    permit, intent = make_permit(world)
    world.assess(t=2_000)  # a newer Hermes assessment supersedes the permit-bound one
    assert harness.orchestrator().canary(permit, intent).code == "PERMIT_NOT_CURRENT"
    other_permit, other_intent = make_permit(world)
    world.append(X._pause(world.version, t=70))  # lifecycle head moves after issuance
    assert harness.orchestrator().canary(other_permit, other_intent).code == "PERMIT_NOT_CURRENT"
    assert harness.venue.posts == [] and harness.secret_requests == 0


def test_permit_intent_mismatch_and_tamper_fail_closed(harness, world) -> None:
    permit, _intent = make_permit(world)
    _other_permit, other_intent = make_permit(world, requested_shares="7")
    assert harness.orchestrator().canary(permit, other_intent).code == "PERMIT_INTENT_MISMATCH"
    forged = dict(permit.to_mapping(), requested_shares="9")
    assert harness.orchestrator().canary(forged, other_intent).code == "PERMIT_INVALID"
    assert harness.venue.posts == []


# ---------------------------------------------------------------------------
# Fresh venue drift contract
# ---------------------------------------------------------------------------


def test_fresh_snapshot_ids_and_books_may_change(harness, world) -> None:
    permit, intent = make_permit(world)
    harness.book = X.book_doc(asks=[("0.51", "50"), ("0.54", "5")], bids=[("0.49", "7")])
    harness.venue.on_post = lambda venue, signed: RejectedOrder(code="fok_not_filled", message="x")
    result = harness.orchestrator().canary(permit, intent)
    assert result.code == "ONE_CREATE_ATTEMPTED" and result.create_transmits == 1
    admission = harness.ledger()["episodes"][0]["admission"]
    assert admission["venue_snapshot_id"] != permit.venue_snapshot_id
    assert admission["execution_feasibility_assessment_id"] != permit.execution_feasibility_assessment_id
    assert admission["decision"] == "ADMITTED"


@pytest.mark.parametrize("gamma_changes, book_changes, code", [
    ({"negRisk": True}, {"neg_risk": True}, "NEG_RISK_UNSUPPORTED"),
    ({"secondsDelay": 3}, {}, "SECONDS_DELAY_UNSUPPORTED"),
    ({"closed": True}, {}, "MARKET_NOT_ELIGIBLE"),
    ({"acceptingOrders": False}, {}, "MARKET_NOT_ELIGIBLE"),
    ({"enableOrderBook": False}, {}, "MARKET_NOT_ELIGIBLE"),
    ({}, {"tick_size": "0.001"}, "TICK_INCOMPATIBLE"),
    ({"orderMinSize": 5}, {}, "MINIMUM_ORDER_NOT_MET"),
    ({}, {"min_order_size": "9"}, "MINIMUM_ORDER_NOT_MET"),
    ({"feesEnabled": X._DROP}, {}, "FEE_CONFIGURATION_UNKNOWN"),
])
def test_forbidden_fresh_drift_rejects_before_admission(harness, world, gamma_changes,
                                                        book_changes, code) -> None:
    permit, intent = make_permit(world)
    gamma = dict(GAMMA)
    for key, value in gamma_changes.items():
        if value is X._DROP:
            gamma.pop(key)
            gamma.pop("feeSchedule", None)
        else:
            gamma[key] = value
    harness.gamma = gamma
    harness.book = X.book_doc(**book_changes)
    result = harness.orchestrator().canary(permit, intent)
    assert result.code == code and result.create_transmits == 0
    assert harness.venue.posts == [] and harness.ledger()["episodes"] == []


def test_identity_drift_rejected(world) -> None:
    permit, intent = make_permit(world)
    authority = L.PermitAuthority(permit, intent, Decimal("4.4"))
    gamma = dict(GAMMA, clobTokenIds=json.dumps([X.OTHER_TOKEN, TOKEN]))
    other = X.P.build_public_venue_snapshot(
        gamma_market_id=X.GAMMA_ID, condition_id=COND, token_id=X.OTHER_TOKEN,
        acquisition_started_ns=X.T0 - 10, acquisition_completed_ns=X.T0,
        gamma=X.P.SourceFetchResult("BODY", json.dumps(gamma).encode()),
        clob=X.P.SourceFetchResult("BODY", json.dumps(X.book_doc(asset_id=X.OTHER_TOKEN)).encode()),
    )
    with pytest.raises(GatewayError, match="VENUE_IDENTITY_DRIFT"):
        L.revalidate_venue(authority, other, evaluated_at_ns=X.T0)
    with pytest.raises(GatewayError, match="VENUE_SNAPSHOT_INVALID"):
        L.revalidate_venue(authority, object(), evaluated_at_ns=X.T0)


# ---------------------------------------------------------------------------
# Durable admission, idempotency and response classification
# ---------------------------------------------------------------------------


def test_durable_admission_precedes_create_started_and_one_transmit(harness, world) -> None:
    permit, intent = make_permit(world)
    harness.venue.on_post = lambda venue, signed: RejectedOrder(code="fok_not_filled", message="x")
    result = harness.orchestrator().canary(permit, intent)
    assert result.create_transmits == 1 and len(harness.venue.posts) == 1
    events = [e for e in harness.events() if e.startswith("LIVE_ORCH_")]
    assert events[:3] == ["LIVE_ORCH_ADMITTED", "LIVE_ORCH_CREATE_STARTED", "LIVE_ORCH_CREATE_OUTCOME"]
    episode = harness.ledger()["episodes"][0]
    assert episode["state"] == "CREATE_REJECTED"
    admission = episode["admission"]
    for key in ("venue_snapshot_id", "execution_feasibility_assessment_id", "host_currentness_id",
                "geoblock_proof_id", "account_truth_id", "current_committed_usd",
                "principal_notional_usd", "worst_case_fee_reserve_usd",
                "worst_case_commitment_usd", "projected_free_collateral_usd",
                "observed_realized_pnl_loss_usd", "observed_position_pnl_drawdown_usd",
                "observed_cumulative_canary_loss_usd"):
        assert admission[key] is not None, key
    binding = episode["binding"]
    assert (binding["exploratory_permit_id"], binding["execution_intent_id"]) == (
        permit.permit_id, intent.execution_intent_id)
    assert (binding["gamma_market_id"], binding["condition_id"], binding["token_id"]) == (
        X.GAMMA_ID, COND, TOKEN)
    assert binding["gamma_market_id"] != binding["condition_id"]
    assert binding["release_sha"] == RELEASE and binding["side"] == "BUY"
    raw = harness.orchestrator().store_path.read_bytes()
    assert SECRET.encode() not in raw and b"signaturebytes" not in raw
    assert b"203.0.113" not in raw and b'"ZZ"' not in raw


def test_admission_persistence_failure_means_zero_transmit(harness, world, monkeypatch) -> None:
    permit, intent = make_permit(world)
    original = ProtectedExecutionGateway.record_live_orch_event

    def fail_admission(self, event_type, checkpoint, **kw):
        if event_type == "LIVE_ORCH_ADMITTED":
            raise GatewayError("STORE_UNAVAILABLE")
        return original(self, event_type, checkpoint, **kw)

    monkeypatch.setattr(ProtectedExecutionGateway, "record_live_orch_event", fail_admission)
    result = harness.orchestrator().canary(permit, intent)
    assert result.code == "LIVE_ORCH_ADMISSION_PERSISTENCE_FAILED"
    assert result.create_transmits == 0 and harness.venue.posts == []


def test_one_permit_one_create_and_no_automatic_retry(harness, world) -> None:
    permit, intent = make_permit(world)
    harness.venue.on_post = lambda venue, signed: (_ for _ in ()).throw(TimeoutError("timeout"))
    first = harness.orchestrator().canary(permit, intent)
    assert first.create_transmits == 1 and len(harness.venue.posts) == 1
    episode = harness.ledger()["episodes"][0]
    assert episode["state"] in ("CREATE_AMBIGUOUS", "RECONCILING", "RECONCILIATION_BLOCKED")
    second = harness.orchestrator().canary(permit, intent)
    assert second.create_transmits == 0 and len(harness.venue.posts) == 1
    assert second.code in ("UNRESOLVED_PRIOR_MUTATION", "PERMIT_ALREADY_CONSUMED")


def test_unknown_create_response_is_ambiguous_never_rejected() -> None:
    assert classify_live_orch_create_response(RejectedOrder(code="unknown", message="x"))[
        "outcome"] == "AMBIGUOUS"
    assert classify_live_orch_create_response(object())["outcome"] == "AMBIGUOUS"
    assert classify_live_orch_create_response(None)["outcome"] == "AMBIGUOUS"
    rejected = classify_live_orch_create_response(RejectedOrder(code="fok_not_filled", message="x"))
    assert rejected["outcome"] == "DEFINITIVE_REJECTED" and rejected["venue_order_id"] is None
    accepted = classify_live_orch_create_response(AcceptedOrder(
        order_id=oid(5), status="matched", making_amount="4.16", taking_amount="8",
        trade_ids=("trade-b", "trade-a"), transactions_hashes=()))
    assert accepted["outcome"] == "DEFINITIVE_ACCEPTED"
    assert accepted["trade_ids"] == ["trade-a", "trade-b"] and accepted["venue_order_id"] == oid(5)
    delayed = classify_live_orch_create_response(AcceptedOrder(
        order_id=oid(6), status="delayed", making_amount="0", taking_amount="0",
        trade_ids=(), transactions_hashes=()))
    assert delayed["outcome"] == "AMBIGUOUS" and delayed["venue_order_id"] == oid(6)


def test_ambiguous_create_reserves_full_commitment_and_blocks(harness, world) -> None:
    permit, intent = make_permit(world)
    harness.venue.on_post = lambda venue, signed: (_ for _ in ()).throw(OSError("reset"))
    result = harness.orchestrator().canary(permit, intent)
    assert result.create_transmits == 1
    ledger = harness.ledger()
    truth = _truth(harness)
    evaluation = L.evaluate_account(truth, {**ledger, "restart_reconciliation_required": False})
    assert "UNRESOLVED_PRIOR_MUTATION" in evaluation.blocking_codes
    worst = Decimal(ledger["episodes"][0]["admission"]["worst_case_commitment_usd"])
    assert evaluation.total_commitment == worst


# ---------------------------------------------------------------------------
# Aggressive BUY construction: no widening, pinned 0.10.0 rounding regression
# ---------------------------------------------------------------------------


def _spec(**changes) -> LiveOrchOrderSpec:
    values = dict(token_id=TOKEN, execution_style="AGGRESSIVE_TAKER", order_type="FOK",
                  requested_shares="8", price_limit="0.55", gtd_expiration_unix_s=None,
                  principal_notional_usd="4.4", worst_case_commitment_usd="4.4666",
                  tick_size="0.01")
    values.update(changes)
    return LiveOrchOrderSpec(**values)


def test_aggressive_fok_fak_encoding_never_widens() -> None:
    venue = FakeVenue()
    ok = venue._signed(maker=4_400_000, taker=8_000_000, order_type="FOK")
    assert inspect_live_orch_signed_buy(ok, _spec(), public_wallet=WALLET).taker_amount == 8_000_000
    for maker, taker, order_type, code in (
        (4_400_001, 8_000_000, "FOK", "ORDER_ENCODING_UNSUPPORTED"),   # principal widened
        (4_000_000, 8_000_001, "FAK", "ORDER_ENCODING_UNSUPPORTED"),   # shares widened
        (4_400_000, 7_900_000, "FOK", "ORDER_ENCODING_UNSUPPORTED"),   # price > limit / FOK short
        (4_400_000, 8_000_000, "FAK", "ORDER_ENCODING_UNSUPPORTED"),   # order type drift
    ):
        signed = venue._signed(maker=maker, taker=taker, order_type=order_type)
        with pytest.raises(GatewayError, match=code):
            inspect_live_orch_signed_buy(signed, _spec(), public_wallet=WALLET)
    fak = venue._signed(maker=4_000_000, taker=7_500_000, order_type="FAK")
    assert inspect_live_orch_signed_buy(fak, _spec(order_type="FAK"), public_wallet=WALLET)
    with pytest.raises(GatewayError, match="SIGNED_ORDER_IDENTITY_MISMATCH"):
        inspect_live_orch_signed_buy(replace(ok, maker="0x" + "f" * 40), _spec(), public_wallet=WALLET)
    with pytest.raises(GatewayError, match="SIGNED_ORDER_IDENTITY_MISMATCH"):
        inspect_live_orch_signed_buy(replace(ok, side="SELL"), _spec(), public_wallet=WALLET)
    with pytest.raises(GatewayError, match="SIGNED_ORDER_IDENTITY_MISMATCH"):
        inspect_live_orch_signed_buy(replace(ok, builder="0x" + "1" * 64), _spec(), public_wallet=WALLET)


def test_pinned_0_10_rounding_sensitive_buy_fails_order_encoding_unsupported() -> None:
    """NR012: 7.33 shares x 0.57 = 4.1781 USD; pinned 0.10.0 rounds the BUY amount down to
    2 decimals and the protected taker shares up, so the FOK target cannot equal 7.33."""
    maker, taker = _compute_market_order_amounts(
        amount=Decimal("4.1781"), price=Decimal("0.57"), side="BUY",
        tick_size=Decimal("0.01"), protect_price=True,
    )
    assert (maker, taker) == (4_170_000, 7_315_800)
    signed = FakeVenue()._signed(maker=maker, taker=taker, order_type="FOK")
    spec = _spec(requested_shares="7.33", price_limit="0.57", principal_notional_usd="4.1781",
                 worst_case_commitment_usd="4.3")
    with pytest.raises(GatewayError, match="ORDER_ENCODING_UNSUPPORTED"):
        inspect_live_orch_signed_buy(signed, spec, public_wallet=WALLET)


def test_rounding_sensitive_canary_never_admits_or_transmits(harness, world) -> None:
    permit, intent = make_permit(world)
    harness.venue.market_amount_override = "4.39"  # SDK-side drift below the exact principal
    result = harness.orchestrator().canary(permit, intent)
    assert result.code == "ORDER_ENCODING_UNSUPPORTED" and result.create_transmits == 0
    assert harness.venue.posts == [] and harness.ledger()["episodes"] == []


# ---------------------------------------------------------------------------
# Fills, settlement statuses, fees and commitment accounting
# ---------------------------------------------------------------------------


def _truth(harness):
    from src.execution_gateway.gate_b import (
        GateBIdentityPolicy, GateBSession, _LIVE_ORCH_ISSUER,
    )

    class _P:
        def acquire(self):
            return GateBSecretLease(SECRET)

    session = GateBSession.authenticate(
        _P(), GateBIdentityPolicy(expected_signer=SIGNER, expected_wallet=WALLET),
        client_factory=lambda key, wallet: harness.venue,
    )
    return session.live_orch_account_truth(_LIVE_ORCH_ISSUER, observed_time_ns=harness.clock())


def test_aggressive_fill_becomes_known_position_with_fee_reconciled(harness, world) -> None:
    permit, intent = make_permit(world)
    harness.venue.on_post = _accept_fill(fee="0.05")
    result = harness.orchestrator().canary(permit, intent)
    episode = harness.ledger()["episodes"][0]
    assert result.episode_state == "TERMINAL_KNOWN_POSITION" == episode["state"]
    assert episode["create"]["trade_ids"] == ["trade-1"]
    assert episode["reconciliation"]["trades"] == [
        {"trade_id": "trade-1", "status": "CONFIRMED", "shares": "8", "principal_usd": "4.16"}]
    assert episode["reconciliation"]["fee_state"] == "RECONCILED"
    assert episode["reconciliation"]["actual_fee_usd"] == "0.05"


def test_fee_ambiguity_retains_reserve_and_blocks(harness, world) -> None:
    permit, intent = make_permit(world)
    harness.venue.on_post = _accept_fill(fee="0.5")  # larger than the conservative reserve
    harness.orchestrator().canary(permit, intent)
    episode = harness.ledger()["episodes"][0]
    assert episode["reconciliation"]["fee_state"] == "AMBIGUOUS"
    evaluation = L.evaluate_account(_truth(harness), harness.ledger() | {
        "restart_reconciliation_required": False})
    assert "FEE_RECONCILIATION_AMBIGUOUS" in evaluation.blocking_codes
    second, second_intent = make_permit(world, requested_shares="7")
    assert harness.orchestrator().canary(second, second_intent).code == "FEE_RECONCILIATION_AMBIGUOUS"


@pytest.mark.parametrize("status", ["MATCHED", "MINED", "RETRYING", "MATCHED_NOT_BROADCASTED"])
def test_nonterminal_settlement_blocks_new_exposure(harness, world, status) -> None:
    permit, intent = make_permit(world)
    harness.venue.on_post = _accept_fill(status=status)
    result = harness.orchestrator().canary(permit, intent)
    assert result.episode_state == "SETTLEMENT_PENDING"
    second, second_intent = make_permit(world, requested_shares="7")
    blocked = harness.orchestrator().canary(second, second_intent)
    assert blocked.code == "SETTLEMENT_NONTERMINAL" and len(harness.venue.posts) == 1
    harness.venue.trades[0]["status"] = "CONFIRMED"
    assert harness.orchestrator().reconcile().details["episode_states"] == ["TERMINAL_KNOWN_POSITION"]


def test_failed_trade_is_not_a_fill(harness, world) -> None:
    permit, intent = make_permit(world)
    harness.venue.on_post = _accept_fill(status="FAILED")
    harness.venue.positions = []

    def post(venue, signed):
        response = venue.fill_taker(signed, shares="8", price="0.52", status="FAILED")
        venue.positions = []
        venue.balance += Decimal("4.16")
        return response

    harness.venue.on_post = post
    result = harness.orchestrator().canary(permit, intent)
    episode = harness.ledger()["episodes"][0]
    assert result.episode_state == "TERMINAL_NO_POSITION" == episode["state"]
    assert episode["reconciliation"]["trades"][0]["status"] == "FAILED"


def test_partial_fill_principal_partitions_are_deduplicated() -> None:
    episode = {
        "episode_id": "liveorchepisode:sha256:" + "1" * 64, "state": "RESTING",
        "binding": {"token_id": TOKEN, "price_limit": "0.5"},
        "admission": {"worst_case_commitment_usd": "4", "worst_case_fee_reserve_usd": "0",
                      "principal_notional_usd": "4"},
        "create": {"venue_order_id": oid(1)}, "cancel_attempts": [],
        "reconciliation": {"order_live": True, "open_remainder_shares": "3", "fee_state": "NOT_REQUIRED",
                           "actual_fee_usd": None, "block_reason": None,
                           "trades": [{"trade_id": "t1", "status": "CONFIRMED", "shares": "4",
                                       "principal_usd": "2"},
                                      {"trade_id": "t2", "status": "MINED", "shares": "1",
                                       "principal_usd": "0.5"}]},
    }
    truth = _fake_truth(orders=[oid(1)], positions=[("4", "1.9", "0.1", "2")])
    evaluation = L.evaluate_account(truth, {"episodes": [episode], "restart_reconciliation_required": False})
    # remainder 3 x 0.5 = 1.5; filled (confirmed 2 + nonterminal 0.5) = 2.5 vs entry 2 -> 2.5 once.
    assert evaluation.total_commitment == Decimal("4")
    assert evaluation.undebited_commitment == Decimal("2")  # remainder + nonterminal
    assert "RESTING_ORDER_PRESENT" in evaluation.blocking_codes


def test_mark_to_market_decline_does_not_free_commitment(harness) -> None:
    from src.execution_gateway.gate_b import LiveOrchPosition

    # current_value is never part of the sanitized truth, so it cannot reduce the budget.
    assert "current_value" not in LiveOrchPosition.__dataclass_fields__
    cp = {"episodes": [_known_episode()], "restart_reconciliation_required": False}
    totals = []
    for value in ("4.16", "0.01"):
        harness.venue.set_position(shares="8", cost="4.16", fees="0.06", value=value)
        totals.append(L.evaluate_account(_truth(harness), cp).total_commitment)
    assert totals == [Decimal("4.22"), Decimal("4.22")]


def test_unknown_position_and_unknown_open_order_block() -> None:
    truth = _fake_truth(positions=[("5", "2", "0", "2")], orders=[oid(77)])
    evaluation = L.evaluate_account(truth, {"episodes": [], "restart_reconciliation_required": False})
    assert {"ACCOUNT_POSITION_UNKNOWN", "ACCOUNT_UNKNOWN_OPEN_ORDER"} <= set(evaluation.blocking_codes)


def test_hard_risk_guards_independently_fail_closed() -> None:
    envelope = L.LiveOrchCapitalEnvelope()

    def ev(**changes):
        values = dict(collateral=Decimal("100"), total_commitment=Decimal("0"),
                      undebited_commitment=Decimal("0"), observed_realized_pnl_loss=Decimal("0"),
                      observed_position_pnl_drawdown=Decimal("0"),
                      observed_cumulative_canary_loss=Decimal("0"), allowance=Decimal("100"),
                      blocking_codes=())
        values.update(changes)
        return L.AccountEvaluation(**values)

    def check(principal="4.4", fee="0.0666", **changes):
        return L.check_admission_risk(envelope, principal=Decimal(principal),
                                      fee_reserve=Decimal(fee), evaluation=ev(**changes))

    risk = check()
    assert risk.proposed_worst_case_commitment == Decimal("4.4666")
    assert risk.projected_free_collateral == Decimal("95.5334")
    assert check(principal="4.95", fee="0.05").proposed_worst_case_commitment == Decimal("5")
    cases = [
        (dict(principal="4.95", fee="0.06"), "SINGLE_ORDER_LIMIT_EXCEEDED"),
        (dict(total_commitment=Decimal("26"), collateral=Decimal("74"),
              undebited_commitment=Decimal("0")), "AGGREGATE_COMMITMENT_LIMIT_EXCEEDED"),
        (dict(collateral=Decimal("74"), total_commitment=Decimal("0"),
              undebited_commitment=Decimal("0")), "FREE_COLLATERAL_RESERVE_VIOLATED"),
        (dict(collateral=Decimal("100.01")), "ACCOUNT_CAPITAL_BASIS_EXCEEDED"),
        (dict(observed_realized_pnl_loss=Decimal("5.01")), "OBSERVED_PNL_GUARD_EXCEEDED"),
        (dict(observed_position_pnl_drawdown=Decimal("7.51")), "OBSERVED_PNL_GUARD_EXCEEDED"),
        (dict(observed_cumulative_canary_loss=Decimal("10.01")), "OBSERVED_PNL_GUARD_EXCEEDED"),
        (dict(allowance=Decimal("4")), "ALLOWANCE_INSUFFICIENT"),
        (dict(allowance=None), "ALLOWANCE_INSUFFICIENT"),
        (dict(blocking_codes=("UNRESOLVED_PRIOR_MUTATION",)), "UNRESOLVED_PRIOR_MUTATION"),
    ]
    for changes, code in cases:
        with pytest.raises(GatewayError, match=code):
            check(**changes)
    # Exactly at the $30 aggregate and $70 free-collateral boundaries passes.
    edge = check(principal="5", fee="0", total_commitment=Decimal("25"), collateral=Decimal("75"),
                 undebited_commitment=Decimal("0"))
    assert edge.projected_free_collateral == Decimal("70")


def test_observed_pnl_guards_use_truthful_position_fields() -> None:
    truth = _fake_truth(positions=[("0", "0", "0", "0", "-3", "-8")])
    evaluation = L.evaluate_account(truth, {"episodes": [], "restart_reconciliation_required": False})
    assert evaluation.observed_realized_pnl_loss == Decimal("3")
    assert evaluation.observed_position_pnl_drawdown == Decimal("8")
    assert evaluation.observed_cumulative_canary_loss == Decimal("8")


def test_profit_cannot_widen_limits(harness, world) -> None:
    permit, intent = make_permit(world)
    harness.venue.balance = Decimal("150")
    result = harness.orchestrator().canary(permit, intent)
    assert result.code == "ACCOUNT_CAPITAL_BASIS_EXCEEDED" and harness.venue.posts == []


# ---------------------------------------------------------------------------
# Passive observation, cancel recovery and no unattended resting order
# ---------------------------------------------------------------------------


def _rest(venue, signed):
    return venue.rest(signed, price="0.51", size="8")


def test_passive_observation_is_bounded_then_cancels_remainder(harness, world) -> None:
    permit, intent = make_permit(world, **PASSIVE)
    harness.venue.on_post = _rest
    result = harness.orchestrator().canary(permit, intent)
    assert result.create_transmits == 1 and result.episode_state == "TERMINAL_NO_POSITION"
    assert all(seconds == L.PASSIVE_POLL_INTERVAL_SECONDS >= 1 for seconds in harness.pauses)
    assert len(harness.pauses) <= L.PASSIVE_OBSERVATION_MAX_SECONDS
    assert len(harness.venue.cancels) == 1
    assert not [row for row in harness.venue.orders.values() if row["status"] == "LIVE"]
    episode = harness.ledger()["episodes"][0]
    assert episode["admission"]["worst_case_fee_reserve_usd"] == "0"
    assert len(episode["cancel_attempts"]) == 1


def test_passive_partial_fill_then_cancel_keeps_matched_fill(harness, world) -> None:
    permit, intent = make_permit(world, **PASSIVE)
    harness.venue.on_post = _rest

    def partial(h):
        order = next(iter(h.venue.orders.values()))
        if order.get("matched") is None:
            order["matched"] = "3"
            h.venue.trades.append({
                **_maker_trade(order["id"], "3"), "status": "CONFIRMED"})
            h.venue.set_position(shares="3", cost="1.53")
            h.venue.balance -= Decimal("1.53")

    harness.pause_hook = partial
    result = harness.orchestrator().canary(permit, intent)
    assert result.episode_state == "TERMINAL_KNOWN_POSITION"
    episode = harness.ledger()["episodes"][0]
    assert episode["reconciliation"]["trades"][0]["shares"] == "3"
    assert episode["reconciliation"]["open_remainder_shares"] == "0"


def test_cancel_ambiguity_uses_fresh_attempt_identities_then_blocks(harness, world) -> None:
    permit, intent = make_permit(world, **PASSIVE)
    harness.venue.on_post = _rest
    harness.venue.on_cancel = lambda venue, order_id: (_ for _ in ()).throw(TimeoutError(SECRET))
    result = harness.orchestrator().canary(permit, intent)
    episode = harness.ledger()["episodes"][0]
    attempts = episode["cancel_attempts"]
    assert len(attempts) == L.MAX_CANCEL_RECONCILE_ROUNDS == len(harness.venue.cancels)
    assert len({item["cancel_attempt_id"] for item in attempts}) == 3
    assert all(item["result"] == "AMBIGUOUS" for item in attempts)
    assert result.episode_state == episode["state"] == "RECONCILIATION_BLOCKED"
    assert episode["reconciliation"]["block_reason"] == "CANCEL_UNCONVERGED"
    # No CREATE while blocked; a later foreground reconcile continues with NEW identities.
    blocked = L.evaluate_account(_truth(harness), harness.ledger() | {
        "restart_reconciliation_required": False})
    assert "UNRESOLVED_PRIOR_MUTATION" in blocked.blocking_codes
    harness.venue.on_cancel = lambda venue, order_id: venue.cancel_live(order_id)
    recovered = harness.orchestrator().reconcile()
    assert recovered.details["episode_states"] == ["TERMINAL_NO_POSITION"]
    ids = [item["cancel_attempt_id"] for item in harness.ledger()["episodes"][0]["cancel_attempts"]]
    assert len(ids) == len(set(ids)) == 4 and len(harness.venue.posts) == 1


def test_cancel_not_sent_when_authoritative_reconcile_shows_not_live(harness, world) -> None:
    permit, intent = make_permit(world, **PASSIVE)
    harness.venue.on_post = _rest

    def filled(h):
        order = next(iter(h.venue.orders.values()))
        order["status"], order["matched"] = "MATCHED", "8"
        if not h.venue.trades:
            h.venue.trades.append({**_maker_trade(order["id"], "8"), "status": "CONFIRMED"})
            h.venue.set_position(shares="8", cost="4.08")
            h.venue.balance -= Decimal("4.08")

    harness.pause_hook = filled
    result = harness.orchestrator().canary(permit, intent)
    assert harness.venue.cancels == [] and result.episode_state == "TERMINAL_KNOWN_POSITION"


def test_interrupted_observation_cancels_before_reraising(harness, world) -> None:
    permit, intent = make_permit(world, **PASSIVE)
    harness.venue.on_post = _rest

    def interrupt(h):
        raise KeyboardInterrupt

    harness.pause_hook = interrupt
    with pytest.raises(KeyboardInterrupt):
        harness.orchestrator().canary(permit, intent)
    assert len(harness.venue.cancels) == 1
    assert not [row for row in harness.venue.orders.values() if row["status"] == "LIVE"]


# ---------------------------------------------------------------------------
# Restart safety, multi-episode recovery and residual positions
# ---------------------------------------------------------------------------


def test_clean_terminal_episode_allows_later_fresh_permit_after_restart(harness, world) -> None:
    permit, intent = make_permit(world)
    harness.venue.on_post = lambda venue, signed: RejectedOrder(code="fok_not_filled", message="x")
    assert harness.orchestrator().canary(permit, intent).episode_state == "CREATE_REJECTED"
    second, second_intent = make_permit(world, requested_shares="7")
    result = harness.orchestrator().canary(second, second_intent)  # new process = restart
    assert result.create_transmits == 1 and len(harness.ledger()["episodes"]) == 2
    assert "RESTARTED" in harness.events()


def test_known_residual_position_survives_restart_and_is_counted(harness, world) -> None:
    permit, intent = make_permit(world)
    harness.venue.on_post = _accept_fill()
    assert harness.orchestrator().canary(permit, intent).episode_state == "TERMINAL_KNOWN_POSITION"
    ledger = harness.ledger()
    evaluation = L.evaluate_account(_truth(harness), ledger | {"restart_reconciliation_required": False})
    assert evaluation.blocking_codes == () and evaluation.total_commitment == Decimal("4.16")
    second, second_intent = make_permit(world, requested_shares="7")
    harness.venue.on_post = lambda venue, signed: RejectedOrder(code="fok_not_filled", message="x")
    result = harness.orchestrator().canary(second, second_intent)
    assert result.create_transmits == 1
    episodes = harness.ledger()["episodes"]
    assert episodes[0]["state"] == "TERMINAL_KNOWN_POSITION"
    assert episodes[1]["admission"]["current_committed_usd"] == "4.16"


def test_crash_after_admission_before_create_started_is_zero_transmit(harness, world, monkeypatch) -> None:
    permit, intent = make_permit(world)
    original = ProtectedExecutionGateway.record_live_orch_event

    def crash(self, event_type, checkpoint, **kw):
        if event_type == "LIVE_ORCH_CREATE_STARTED":
            raise GatewayError("STORE_UNAVAILABLE")
        return original(self, event_type, checkpoint, **kw)

    monkeypatch.setattr(ProtectedExecutionGateway, "record_live_orch_event", crash)
    result = harness.orchestrator().canary(permit, intent)
    assert result.code == "LIVE_ORCH_CREATE_STARTED_PERSISTENCE_FAILED"
    assert harness.venue.posts == []
    monkeypatch.setattr(ProtectedExecutionGateway, "record_live_orch_event", original)
    assert harness.orchestrator().reconcile().details["episode_states"] == ["TERMINAL_NO_POSITION"]


def test_crash_after_transmit_before_outcome_recovers_as_ambiguous(harness, world, monkeypatch) -> None:
    permit, intent = make_permit(world, **PASSIVE)
    harness.venue.on_post = _rest
    original = ProtectedExecutionGateway.record_live_orch_event

    def crash(self, event_type, checkpoint, **kw):
        if event_type == "LIVE_ORCH_CREATE_OUTCOME":
            raise GatewayError("STORE_UNAVAILABLE")
        return original(self, event_type, checkpoint, **kw)

    monkeypatch.setattr(ProtectedExecutionGateway, "record_live_orch_event", crash)
    result = harness.orchestrator().canary(permit, intent)
    assert result.code == "LIVE_ORCH_OUTCOME_PERSISTENCE_FAILED" and result.create_transmits == 1
    assert harness.ledger()["episodes"][0]["state"] == "CREATE_STARTED"
    monkeypatch.setattr(ProtectedExecutionGateway, "record_live_orch_event", original)
    # restart -> no-new-exposure -> discover the resting order -> cancel -> reconcile
    recovered = harness.orchestrator().reconcile()
    assert recovered.details["episode_states"] == ["TERMINAL_NO_POSITION"]
    episode = harness.ledger()["episodes"][0]
    assert episode["create"]["outcome"] == "AMBIGUOUS" and episode["create"]["venue_order_id"] == oid(1)
    assert len(harness.venue.cancels) == 1 and len(harness.venue.posts) == 1


def test_crash_after_cancel_started_resumes_with_new_identity(harness, world, monkeypatch) -> None:
    permit, intent = make_permit(world, **PASSIVE)
    harness.venue.on_post = _rest
    original = ProtectedExecutionGateway.record_live_orch_event
    harness.venue.on_cancel = lambda venue, order_id: (_ for _ in ()).throw(TimeoutError("lost"))

    def crash(self, event_type, checkpoint, **kw):
        if event_type == "LIVE_ORCH_CANCEL_OUTCOME":
            raise GatewayError("STORE_UNAVAILABLE")
        return original(self, event_type, checkpoint, **kw)

    monkeypatch.setattr(ProtectedExecutionGateway, "record_live_orch_event", crash)
    result = harness.orchestrator().canary(permit, intent)
    assert result.status == "BLOCKED"
    assert harness.ledger()["episodes"][0]["state"] == "CANCEL_STARTED"
    monkeypatch.setattr(ProtectedExecutionGateway, "record_live_orch_event", original)
    harness.venue.on_cancel = lambda venue, order_id: venue.cancel_live(order_id)
    assert harness.orchestrator().reconcile().details["episode_states"] == ["TERMINAL_NO_POSITION"]
    attempts = harness.ledger()["episodes"][0]["cancel_attempts"]
    ids = [a["cancel_attempt_id"] for a in attempts]
    assert attempts[0]["result"] == "AMBIGUOUS" and len(ids) == len(set(ids)) >= 2
    assert all(a["result"] is not None for a in attempts) and len(harness.venue.posts) == 1


def test_unbound_ambiguous_create_converges_only_after_minimum_age(harness, world) -> None:
    permit, intent = make_permit(world)
    harness.venue.on_post = lambda venue, signed: (_ for _ in ()).throw(TimeoutError("timeout"))
    harness.orchestrator().canary(permit, intent)
    assert harness.ledger()["episodes"][0]["state"] in ("CREATE_AMBIGUOUS", "RECONCILING")
    assert harness.orchestrator().reconcile().code == "UNRESOLVED_PRIOR_MUTATION"
    harness.now += L.AMBIGUOUS_CREATE_CONVERGENCE_MIN_AGE_NS
    assert harness.orchestrator().reconcile().details["episode_states"] == ["TERMINAL_NO_POSITION"]


def test_preflight_cannot_mutate_and_reconcile_cannot_create(harness, world) -> None:
    permit, intent = make_permit(world)
    result = harness.orchestrator().preflight(permit, intent)
    assert result.status == "PREFLIGHT_PASS"
    assert not harness.orchestrator().store_path.exists() and harness.secret_requests == 0
    reconcile = harness.orchestrator().reconcile()
    assert reconcile.status == "NO_NEW_EXPOSURE_READY" and harness.venue.posts == []
    assert [e for e in harness.events() if e.startswith("LIVE_ORCH_ADMITTED")] == []


def test_account_history_over_100_items_forbids_new_exposure(harness, world) -> None:
    permit, intent = make_permit(world)
    for n in range(101):
        harness.venue.add_trade(f"old-{n}", taker=oid(5000 + n), shares="1", price="0.5",
                                status="CONFIRMED")
    result = harness.orchestrator().canary(permit, intent)
    assert result.code == "ACCOUNT_HISTORY_LIMIT_EXCEEDED" and harness.venue.posts == []


def test_cli_requires_interactive_confirmation_and_reports_closed_codes(tmp_path, world) -> None:
    harness = Harness(tmp_path, world)
    permit, intent = make_permit(world)
    (tmp_path / "permit.json").write_text(json.dumps(permit.to_mapping()), encoding="utf-8")
    (tmp_path / "intent.json").write_text(json.dumps(intent.to_mapping()), encoding="utf-8")
    args = ["canary", "--state-root", str(tmp_path / "state"), "--expected-signer", SIGNER,
            "--expected-wallet", WALLET, "--lifecycle-store", str(world.lifecycle),
            "--hermes-store", str(world.hermes), "--repository-root", str(tmp_path),
            "--binding-file", "b", "--active-release", "r", "--unit-dir", "u", "--ssh-port", "22",
            "--expected-release-sha", RELEASE, "--permit-json", str(tmp_path / "permit.json"),
            "--intent-json", str(tmp_path / "intent.json")]
    assert L.main(args, dependencies=harness.deps(), confirm=lambda prompt: "yes") == 2
    assert harness.venue.posts == [] and harness.secret_requests == 0
    preflight = ["preflight"] + args[1:]
    assert L.main(preflight, dependencies=harness.deps()) == 0


def test_live_orch_source_has_no_raw_client_daemon_or_ui_surface() -> None:
    source = Path(L.__file__).read_text(encoding="utf-8")
    for forbidden in ("SecureClient", "while True", "time.sleep", "schedule(", "websocket",
                      "place_limit_order", "place_market_order", "post_order", "os.environ",
                      "fastapi", "approve(", "redeem", "session_key", "builder_code"):
        assert forbidden not in source, forbidden
    assert "_LIVE_ORCH_EVENT_ISSUER" in source and "LiveOrchMutationBoundary" in source
    assert set(LIVE_ORCH_EPISODE_STATES) == {
        "ADMISSION_PENDING", "ADMITTED", "CREATE_STARTED", "CREATE_REJECTED", "CREATE_ACCEPTED",
        "CREATE_AMBIGUOUS", "RESTING", "CANCEL_STARTED", "RECONCILING", "SETTLEMENT_PENDING",
        "TERMINAL_NO_POSITION", "TERMINAL_KNOWN_POSITION", "RECONCILIATION_BLOCKED"}


# ---------------------------------------------------------------------------
# Offline truth builders
# ---------------------------------------------------------------------------


def _maker_trade(order_id: str, shares: str) -> dict:
    return {
        "id": f"maker-trade-{shares}", "market": COND, "asset_id": TOKEN, "owner": "owner",
        "maker_address": WALLET, "taker_order_id": oid(888), "side": "SELL",
        "trader_side": "MAKER", "price": "0.51", "size": shares, "outcome": "Yes",
        "status": "CONFIRMED", "fee_rate_bps": "0", "bucket_index": 0,
        "transaction_hash": "0x" + "8" * 64,
        "maker_orders": [{"order_id": order_id, "asset_id": TOKEN, "maker_address": WALLET,
                          "owner": "owner", "side": "BUY", "price": "0.51",
                          "matched_amount": shares, "outcome": "Yes"}],
        "match_time": 1760000000, "last_update": 1760000001,
    }


def _known_episode() -> dict:
    return {
        "episode_id": "liveorchepisode:sha256:" + "2" * 64, "state": "TERMINAL_KNOWN_POSITION",
        "binding": {"token_id": TOKEN, "price_limit": "0.55"},
        "admission": {"worst_case_commitment_usd": "4.4666", "worst_case_fee_reserve_usd": "0.0666",
                      "principal_notional_usd": "4.4"},
        "create": {"venue_order_id": oid(2)}, "cancel_attempts": [],
        "reconciliation": {"order_live": False, "open_remainder_shares": "0",
                           "fee_state": "RECONCILED", "actual_fee_usd": "0.06", "block_reason": None,
                           "trades": [{"trade_id": "t", "status": "CONFIRMED", "shares": "8",
                                       "principal_usd": "4.16"}]},
    }


def _fake_truth(*, orders=(), positions=()):
    from src.execution_gateway.gate_b import (
        LiveOrchAccountTruth, LiveOrchOpenOrder, LiveOrchPosition,
    )

    return LiveOrchAccountTruth(
        SIGNER, WALLET, 1, "90", (("exchange", "100"),), False,
        tuple(LiveOrchOpenOrder(o, TOKEN, COND, "BUY", "0.5", "8", "5", "LIVE", "GTC") for o in orders),
        (),
        tuple(LiveOrchPosition(TOKEN, COND, p[0], p[1], p[2], p[3],
                               p[4] if len(p) > 4 else "0", p[5] if len(p) > 5 else "0", "OPEN")
              for p in positions),
    )
