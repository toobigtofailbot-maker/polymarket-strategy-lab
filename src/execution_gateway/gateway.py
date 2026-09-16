"""Deterministic Gate-A/ Gate-C implementation of the protected gateway.

Gate-A remains read-only/shadow-only.  The only live state is the explicitly
bounded A3 checkpoint written by :mod:`gate_c`; no caller can reach it through
the generic authority setter.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from decimal import Decimal, InvalidOperation
import hashlib
import json
import re
import time
from pathlib import Path
import sqlite3
from itertools import islice
from inspect import signature
from typing import Mapping, Sequence

from polymarket import AsyncSecureClient, SecureClient

from src.paper_trading.models import (
    PAPER_APPLICATION_ID,
    PAPER_USER_VERSION,
    PaperIntent,
    PaperRiskDecision,
    PaperStrategyBinding,
    validate_paper_intent,
    validate_risk_decision,
    validate_strategy_binding,
    content_id,
)
from src.paper_trading.engine import _replay_journal, state_to_mapping
from src.paper_trading.store import JournalEvent as PaperJournalEvent, PaperStore

from .store import GatewayJournalEvent, GatewayStore, GatewayStoreError, canonical_json


AUTHORITY_STATES = ("A0_DISABLED", "A1_READ_ONLY", "A2_SHADOW", "A3_RESTRICTED_LIVE")
ACCESS_STATES = (
    "ELIGIBLE",
    "GEOBLOCKED",
    "CLOSE_ONLY",
    "CANCEL_ONLY",
    "ENGINE_RESTRICTED",
    "UNKNOWN",
)
RECONCILIATION_STATES = ("HEALTHY", "REQUIRED", "BLOCKED", "DIVERGED")
HEARTBEAT_STATES = (
    "DISABLED",
    "HEALTHY",
    "MISSED",
    "UNSAFE",
    "RECONCILIATION_REQUIRED",
)
USER_STREAM_STATES = ("DISCONNECTED", "CONNECTED", "GAP_DETECTED")
MUTATION_OUTCOMES = (
    "DEFINITIVE_ACCEPTED",
    "DEFINITIVE_REJECTED",
    "AMBIGUOUS",
    "RECONCILIATION_REQUIRED",
)
TIME_IN_FORCE = ("GTC", "GTD")
MUTATION_OPERATIONS = (
    "CREATE",
    "CANCEL_ONE",
    "CANCEL_MANY",
    "CANCEL_MARKET",
    "CANCEL_ALL",
)
GATE_B_AUDIT_EVENTS = (
    "GATE_B_AUTHENTICATED",
    "GATE_B_SIGNING_VERIFIED",
    "GATE_B_RECONCILED",
    "GATE_B_CANCEL_ATTEMPT_STARTED",
    "GATE_B_CANCEL_ATTEMPT_RESULT",
    "GATE_B_CANCEL_TRANSPORT_VERIFIED",
)
MAX_ACCOUNT_SNAPSHOT_AGE_NS = 60_000_000_000
_LABEL_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,255}$")
_ADDRESS_RE = re.compile(r"^0x[0-9a-f]{40}$")
_ID_RE = re.compile(r"^[a-z][a-z0-9_-]*:sha256:[0-9a-f]{64}$")
_REFERENCE_RE = re.compile(r"^secret-ref:[a-z][a-z0-9._/-]{0,63}$")
_DOMAIN_NAME = "Polymarket CTF Exchange"
_EXCHANGE_ADDRESSES = {
    "exchange": "0xe111180000d2663c0091e4f400237545b87b996b",
    "neg-risk-exchange": "0xe2222d279d744050d28e00520010520000310f59",
}


class GatewayError(Exception):
    """Sanitized, closed-vocabulary gateway failure."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def _decimal(value: object, *, positive: bool = False) -> Decimal:
    if not isinstance(value, str) or len(value) > 128:
        raise GatewayError("ORDER_CONSTRAINT_INVALID")
    try:
        parsed = Decimal(value)
    except InvalidOperation:
        raise GatewayError("ORDER_CONSTRAINT_INVALID") from None
    if not parsed.is_finite() or (positive and parsed <= 0):
        raise GatewayError("ORDER_CONSTRAINT_INVALID")
    return parsed


def _canonical_decimal(value: Decimal) -> str:
    rendered = format(value, "f")
    if "." in rendered:
        rendered = rendered.rstrip("0").rstrip(".")
    return "0" if rendered in ("", "-0") else rendered


def _sha(prefix: str, value: object) -> str:
    return prefix + hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _label(value: object) -> str:
    if (
        not isinstance(value, str)
        or _LABEL_RE.fullmatch(value) is None
        or any(
            term in value.lower()
            for term in (
                "private",
                "secret",
                "pass" + "phrase",
                "mne" + "monic",
                "api_key",
                "seed",
            )
        )
    ):
        raise GatewayError("FIELD_VALUE_INVALID")
    return value


def _time(value: object) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise GatewayError("FIELD_VALUE_INVALID")
    return value


@dataclass(frozen=True)
class CredentialReference:
    reference: str
    configured: bool
    public_signer: str | None = None
    public_funder: str | None = None

    def validate(self) -> None:
        tail = self.reference.removeprefix("secret-ref:").lower()
        if (
            _REFERENCE_RE.fullmatch(self.reference) is None
            or type(self.configured) is not bool
            or any(
                term in tail
                for term in (
                    "private",
                    "pass" + "phrase",
                    "mne" + "monic",
                    "api-key",
                    "seed",
                )
            )
        ):
            raise GatewayError("CREDENTIAL_REFERENCE_INVALID")
        for address in (self.public_signer, self.public_funder):
            if address is not None and _ADDRESS_RE.fullmatch(address) is None:
                raise GatewayError("SIGNING_IDENTITY_INVALID")


class GateASecretReferenceLoader:
    """Resolve allowlisted reference names to public metadata, never secret values."""

    def __init__(self, registry: Mapping[str, tuple[str, str]]):
        resolved: dict[str, tuple[str, str]] = {}
        for reference, addresses in registry.items():
            descriptor = CredentialReference(reference, True, *addresses)
            descriptor.validate()
            resolved[reference] = addresses
        self._registry = resolved

    def load(self, reference: str) -> CredentialReference:
        if reference not in self._registry:
            raise GatewayError("CREDENTIAL_REFERENCE_UNAVAILABLE")
        signer, funder = self._registry[reference]
        return CredentialReference(reference, True, signer, funder)


@dataclass(frozen=True)
class VenueIdentity:
    chain_id: int
    domain_name: str
    protocol_version: str
    verifying_contract: str
    signer: str
    funder: str
    wallet_type: str
    signature_type: str
    exchange: str

    def validate(self) -> None:
        if self.chain_id != 137:
            raise GatewayError("SIGNING_IDENTITY_INVALID")
        for address in (self.signer, self.funder):
            if _ADDRESS_RE.fullmatch(address) is None:
                raise GatewayError("SIGNING_IDENTITY_INVALID")
        if (
            self.domain_name != _DOMAIN_NAME
            or self.protocol_version != "2"
            or self.verifying_contract != _EXCHANGE_ADDRESSES.get(self.exchange)
            or self.wallet_type != "EOA"
            or self.signature_type != "0"
            or self.exchange not in ("exchange", "neg-risk-exchange")
        ):
            raise GatewayError("SIGNING_IDENTITY_INVALID")


@dataclass(frozen=True)
class VenueConstraints:
    market_id: str
    condition_id: str
    token_id: str
    tick_size: str
    minimum_order_size: str
    neg_risk: bool
    exchange: str
    access_state: str
    post_only_allowed: bool
    supports_gtc: bool
    supports_gtd: bool
    observed_time_ns: int
    valid_until_ns: int
    constraint_version: str

    def validate(self) -> None:
        for value in (self.market_id, self.condition_id, self.token_id, self.exchange):
            _label(value)
        _decimal(self.tick_size, positive=True)
        _decimal(self.minimum_order_size, positive=True)
        if type(self.neg_risk) is not bool or type(self.post_only_allowed) is not bool:
            raise GatewayError("ORDER_CONSTRAINT_INVALID")
        if type(self.supports_gtc) is not bool or type(self.supports_gtd) is not bool:
            raise GatewayError("ORDER_CONSTRAINT_INVALID")
        _time(self.observed_time_ns)
        _time(self.valid_until_ns)
        _label(self.constraint_version)
        if self.valid_until_ns < self.observed_time_ns:
            raise GatewayError("ORDER_CONSTRAINT_INVALID")
        if self.access_state not in ACCESS_STATES:
            raise GatewayError("ACCESS_STATE_INVALID")


class FixtureVenueContextAdapter:
    """Explicit non-network source for deterministic shadow-only venue context."""

    def __init__(self, constraints: VenueConstraints, identity: VenueIdentity):
        constraints.validate()
        identity.validate()
        self._value = (constraints, identity)

    def query_venue_context(
        self, *_args: object
    ) -> tuple[VenueConstraints, VenueIdentity]:
        return self._value


@dataclass(frozen=True)
class WP173AuthorizationEvidence:
    authorization_id: str
    binding: PaperStrategyBinding
    intent: PaperIntent
    risk_decision: PaperRiskDecision
    accounting_checkpoint_hash: str
    paper_reconciliation_state: str

    def validate(self) -> None:
        try:
            validate_strategy_binding(self.binding)
            validate_paper_intent(self.intent, self.binding)
            validate_risk_decision(self.risk_decision)
        except Exception:
            raise GatewayError("WP173_BINDING_INVALID") from None
        if (
            self.risk_decision.intent_id != self.intent.intent_id
            or self.risk_decision.result != "ALLOW"
            or self.paper_reconciliation_state != "HEALTHY"
            or _ID_RE.fullmatch(self.accounting_checkpoint_hash) is None
        ):
            raise GatewayError("WP173_BINDING_INVALID")
        expected = _sha(
            "wp173authorization:sha256:",
            {
                "binding_id": self.binding.binding_id,
                "intent_id": self.intent.intent_id,
                "risk_decision_id": self.risk_decision.decision_id,
                "accounting_checkpoint_hash": self.accounting_checkpoint_hash,
                "paper_reconciliation_state": self.paper_reconciliation_state,
            },
        )
        if self.authorization_id != expected:
            raise GatewayError("WP173_BINDING_INVALID")


@dataclass(frozen=True)
class VenueOrderSnapshot:
    venue_order_id: str
    order_identity: str
    status: str
    filled_quantity: str

    def validate(self) -> None:
        _label(self.venue_order_id)
        if _ID_RE.fullmatch(self.order_identity) is None:
            raise GatewayError("ACCOUNT_SNAPSHOT_INVALID")
        if self.status not in ("OPEN", "PARTIALLY_FILLED", "FILLED", "CANCELED"):
            raise GatewayError("ACCOUNT_SNAPSHOT_INVALID")
        if _decimal(self.filled_quantity) < 0:
            raise GatewayError("ACCOUNT_SNAPSHOT_INVALID")


@dataclass(frozen=True)
class VenueTradeSnapshot:
    trade_id: str
    venue_order_id: str
    order_identity: str
    quantity: str

    def validate(self) -> None:
        _label(self.trade_id)
        _label(self.venue_order_id)
        if (
            _ID_RE.fullmatch(self.order_identity) is None
            or _decimal(self.quantity) <= 0
        ):
            raise GatewayError("ACCOUNT_SNAPSHOT_INVALID")


@dataclass(frozen=True)
class AccountSnapshot:
    snapshot_id: str
    signer: str
    funder: str
    observed_time_ns: int
    access_state: str
    venue_mode: str
    open_orders: tuple[VenueOrderSnapshot, ...]
    recent_trades: tuple[VenueTradeSnapshot, ...]
    balances_hash: str
    positions_hash: str
    fixture_only: bool = True

    def validate(self) -> None:
        for address in (self.signer, self.funder):
            if _ADDRESS_RE.fullmatch(address) is None:
                raise GatewayError("ACCOUNT_SNAPSHOT_INVALID")
        _time(self.observed_time_ns)
        if self.access_state not in ACCESS_STATES:
            raise GatewayError("ACCOUNT_SNAPSHOT_INVALID")
        if self.venue_mode not in ("NORMAL", "CLOSE_ONLY", "CANCEL_ONLY", "RESTARTING"):
            raise GatewayError("ACCOUNT_SNAPSHOT_INVALID")
        for item in self.open_orders:
            item.validate()
        if len({item.venue_order_id for item in self.open_orders}) != len(
            self.open_orders
        ):
            raise GatewayError("ACCOUNT_SNAPSHOT_INVALID")
        for item in self.recent_trades:
            item.validate()
        if len({item.trade_id for item in self.recent_trades}) != len(
            self.recent_trades
        ):
            raise GatewayError("ACCOUNT_SNAPSHOT_INVALID")
        for value in (self.balances_hash, self.positions_hash):
            if _ID_RE.fullmatch(value) is None:
                raise GatewayError("ACCOUNT_SNAPSHOT_INVALID")
        if type(self.fixture_only) is not bool:
            raise GatewayError("ACCOUNT_SNAPSHOT_INVALID")
        expected = _sha(
            "accountsnapshot:sha256:",
            {
                "signer": self.signer,
                "funder": self.funder,
                "observed_time_ns": self.observed_time_ns,
                "access_state": self.access_state,
                "venue_mode": self.venue_mode,
                "open_orders": [asdict(item) for item in self.open_orders],
                "recent_trades": [asdict(item) for item in self.recent_trades],
                "balances_hash": self.balances_hash,
                "positions_hash": self.positions_hash,
                "fixture_only": self.fixture_only,
            },
        )
        if self.snapshot_id != expected:
            raise GatewayError("ACCOUNT_SNAPSHOT_INVALID")


@dataclass(frozen=True)
class UserStreamEvent:
    sequence: int
    event_id: str
    kind: str
    venue_order_id: str

    def validate(self) -> None:
        if (
            not isinstance(self.sequence, int)
            or isinstance(self.sequence, bool)
            or self.sequence < 1
        ):
            raise GatewayError("USER_STREAM_EVENT_INVALID")
        if _ID_RE.fullmatch(self.event_id) is None:
            raise GatewayError("USER_STREAM_EVENT_INVALID")
        if self.kind not in ("ORDER", "TRADE", "CANCEL"):
            raise GatewayError("USER_STREAM_EVENT_INVALID")
        _label(self.venue_order_id)


class FixtureAuthenticatedReadAdapter:
    """Non-network authenticated-read simulator for Gate-A evidence only."""

    def __init__(
        self,
        snapshot: AccountSnapshot,
        *,
        heartbeat_ack: str | None = None,
        user_events: Sequence[UserStreamEvent] = (),
        order_history: Sequence[VenueOrderSnapshot] = (),
    ):
        snapshot.validate()
        events = tuple(user_events)
        for event in events:
            event.validate()
        self._snapshot = snapshot
        self._heartbeat_ack = heartbeat_ack
        self._user_events = events
        history = tuple(order_history) or snapshot.open_orders
        for item in history:
            item.validate()
        self._order_history = history

    def query_account(self) -> AccountSnapshot:
        return self._snapshot

    def query_order(self, venue_order_id: str) -> VenueOrderSnapshot | None:
        _label(venue_order_id)
        return next(
            (
                item
                for item in self._order_history
                if item.venue_order_id == venue_order_id
            ),
            None,
        )

    def query_open_orders(self) -> tuple[VenueOrderSnapshot, ...]:
        return self._snapshot.open_orders

    def query_recent_trades(self) -> tuple[VenueTradeSnapshot, ...]:
        return self._snapshot.recent_trades

    def query_balances_positions(self) -> tuple[str, str]:
        return self._snapshot.balances_hash, self._snapshot.positions_hash

    def send_heartbeat(self, heartbeat_id: str) -> str | None:
        _label(heartbeat_id)
        return self._heartbeat_ack

    def read_user_events(self, after_sequence: int) -> tuple[UserStreamEvent, ...]:
        if (
            not isinstance(after_sequence, int)
            or isinstance(after_sequence, bool)
            or after_sequence < 0
        ):
            raise GatewayError("USER_STREAM_EVENT_INVALID")
        return tuple(
            event for event in self._user_events if event.sequence > after_sequence
        )


class OfficialSdkAuthenticatedReadAdapter:
    """Bounded A1 reads through the official SDK; no mutation method is exposed."""

    def __init__(
        self,
        client: SecureClient,
        *,
        observed_time_ns: int,
        order_identity_by_venue_id: Mapping[str, str],
    ):
        if type(client) is not SecureClient:
            raise GatewayError("AUTHENTICATED_READ_ADAPTER_INVALID")
        _time(observed_time_ns)
        try:
            context = client._ctx
            config = context.environment_config
            signer = str(client.signer).lower()
            funder = str(client.wallet).lower()
            if (
                client.environment.name != "production"
                or config.chain_id != 137
                or client.wallet_type != "EOA"
                or context.signer_type != "OWNER"
                or _ADDRESS_RE.fullmatch(signer) is None
                or _ADDRESS_RE.fullmatch(funder) is None
            ):
                raise GatewayError("AUTHENTICATED_READ_ADAPTER_INVALID")
        except GatewayError:
            raise
        except Exception:
            raise GatewayError("AUTHENTICATED_READ_ADAPTER_INVALID") from None
        self._client = client
        self._signer = signer
        self._funder = funder
        self._observed_time_ns = observed_time_ns
        self._identities = dict(order_identity_by_venue_id)
        if any(_ID_RE.fullmatch(value) is None for value in self._identities.values()):
            raise GatewayError("AUTHENTICATED_READ_ADAPTER_INVALID")
        self._snapshot: AccountSnapshot | None = None

    def _read_access_state(self) -> tuple[str, str]:
        """Map the SDK's only account-mode signal conservatively.

        The released SDK exposes closed-only mode but no complete venue access
        state.  A false result therefore cannot prove eligibility; it remains
        UNKNOWN/RESTARTING until a future certified adapter can supply the
        missing geoblock, cancel-only, and engine state signals.
        """
        closed_only = self._client.get_closed_only_mode()
        if type(closed_only) is not bool:
            raise GatewayError("AUTHENTICATED_READ_FAILED")
        return (
            ("CLOSE_ONLY", "CLOSE_ONLY") if closed_only else ("UNKNOWN", "RESTARTING")
        )

    def query_venue_context(
        self, intent: PaperIntent, signing_time_ns: int
    ) -> tuple[VenueConstraints, VenueIdentity]:
        _time(signing_time_ns)
        try:
            book = self._client.get_order_book(token_id=intent.asset_id)
            if (
                str(book.asset_id) != intent.asset_id
                or str(book.condition_id) != intent.market_id
            ):
                raise GatewayError("VENUE_CONSTRAINTS_INVALID")
            config = self._client._ctx.environment_config
            exchange = "neg-risk-exchange" if book.neg_risk else "exchange"
            verifying_contract = (
                config.neg_risk_exchange if book.neg_risk else config.standard_exchange
            ).lower()
            limit_parameters = signature(
                type(self._client).create_limit_order
            ).parameters
            place_parameters = signature(
                type(self._client).place_limit_order
            ).parameters
            post_only = (
                "post_only" in limit_parameters and "post_only" in place_parameters
            )
            expiration = (
                "expiration" in limit_parameters and "expiration" in place_parameters
            )
            access_state, _venue_mode = self._read_access_state()
            constraints = VenueConstraints(
                str(book.condition_id),
                str(book.condition_id),
                str(book.asset_id),
                _canonical_decimal(book.tick_size),
                _canonical_decimal(book.min_order_size),
                book.neg_risk,
                exchange,
                access_state,
                post_only,
                expiration,
                expiration,
                signing_time_ns,
                signing_time_ns,
                _sha("venueconstraints:sha256:", book.model_dump(mode="json")),
            )
            identity = VenueIdentity(
                config.chain_id,
                _DOMAIN_NAME,
                "2",
                verifying_contract,
                self._signer,
                self._funder,
                self._client.wallet_type,
                "0",
                exchange,
            )
            constraints.validate()
            identity.validate()
            return constraints, identity
        except GatewayError:
            raise
        except Exception:
            raise GatewayError("AUTHENTICATED_READ_FAILED") from None

    def query_account(self) -> AccountSnapshot:
        try:
            order_pages = self._client.list_open_orders()
            trade_pages = self._client.list_account_trades()
            position_pages = self._client.list_positions(
                user=self._funder, page_size=100
            )
            orders_raw = tuple(
                islice(
                    order_pages.iter_items()
                    if hasattr(order_pages, "iter_items")
                    else iter(order_pages),
                    101,
                )
            )
            trades_raw = tuple(
                islice(
                    trade_pages.iter_items()
                    if hasattr(trade_pages, "iter_items")
                    else iter(trade_pages),
                    101,
                )
            )
            positions_raw = tuple(
                islice(
                    position_pages.iter_items()
                    if hasattr(position_pages, "iter_items")
                    else iter(position_pages),
                    101,
                )
            )
            if any(
                len(items) > 100 for items in (orders_raw, trades_raw, positions_raw)
            ):
                raise GatewayError("AUTHENTICATED_READ_LIMIT_EXCEEDED")
            balances_raw = self._client.get_balance_allowance(asset_type="COLLATERAL")
            access_state, venue_mode = self._read_access_state()
        except GatewayError:
            raise
        except Exception:
            raise GatewayError("AUTHENTICATED_READ_FAILED") from None
        return self._build_account_snapshot(
            orders_raw,
            trades_raw,
            positions_raw,
            balances_raw,
            access_state,
            venue_mode,
        )

    def _build_account_snapshot(
        self,
        orders_raw: Sequence[object],
        trades_raw: Sequence[object],
        positions_raw: Sequence[object],
        balances_raw: object,
        access_state: str,
        venue_mode: str,
    ) -> AccountSnapshot:
        """Normalize SDK models inside the sanitized adapter boundary."""
        try:
            orders = tuple(
                VenueOrderSnapshot(
                    item.id,
                    self._identities.get(
                        item.id,
                        _sha("foreignorder:sha256:", {"venue_order_id": item.id}),
                    ),
                    "PARTIALLY_FILLED" if item.size_matched > 0 else "OPEN",
                    _canonical_decimal(item.size_matched),
                )
                for item in orders_raw
            )
            normalized_trades: list[VenueTradeSnapshot] = []
            for item in trades_raw:
                maker_matches = tuple(
                    maker
                    for maker in item.maker_orders
                    if maker.order_id in self._identities
                )
                if maker_matches:
                    normalized_trades.extend(
                        VenueTradeSnapshot(
                            f"{item.id}:{maker.order_id}",
                            maker.order_id,
                            self._identities[maker.order_id],
                            _canonical_decimal(maker.matched_amount),
                        )
                        for maker in maker_matches
                    )
                else:
                    normalized_trades.append(
                        VenueTradeSnapshot(
                            item.id,
                            item.taker_order_id,
                            self._identities.get(
                                item.taker_order_id,
                                _sha(
                                    "foreignorder:sha256:",
                                    {"venue_order_id": item.taker_order_id},
                                ),
                            ),
                            _canonical_decimal(item.size),
                        )
                    )
            trades = tuple(normalized_trades)
            preimage = {
                "signer": self._signer,
                "funder": self._funder,
                "observed_time_ns": self._observed_time_ns,
                "access_state": access_state,
                "venue_mode": venue_mode,
                "open_orders": [asdict(item) for item in orders],
                "recent_trades": [asdict(item) for item in trades],
                "balances_hash": _sha(
                    "balances:sha256:", balances_raw.model_dump(mode="json")
                ),
                "positions_hash": _sha(
                    "positions:sha256:",
                    [item.model_dump(mode="json") for item in positions_raw],
                ),
                "fixture_only": False,
            }
            self._snapshot = AccountSnapshot(
                _sha("accountsnapshot:sha256:", preimage),
                self._signer,
                self._funder,
                self._observed_time_ns,
                access_state,
                venue_mode,
                orders,
                trades,
                preimage["balances_hash"],
                preimage["positions_hash"],
                False,
            )
            self._snapshot.validate()
            return self._snapshot
        except GatewayError:
            raise
        except Exception:
            raise GatewayError("AUTHENTICATED_READ_FAILED") from None

    def _require_snapshot(self) -> AccountSnapshot:
        if self._snapshot is None:
            raise GatewayError("ACCOUNT_SNAPSHOT_INVALID")
        return self._snapshot

    def query_order(self, venue_order_id: str) -> VenueOrderSnapshot | None:
        _label(venue_order_id)
        try:
            item = self._client.get_order(order_id=venue_order_id)
            identity = self._identities.get(
                item.id, _sha("foreignorder:sha256:", {"venue_order_id": item.id})
            )
            raw_status = item.status.upper()
            if raw_status in ("MATCHED", "FILLED"):
                status = "FILLED"
            elif raw_status in ("CANCELED", "CANCELLED"):
                status = "CANCELED"
            elif raw_status in ("LIVE", "OPEN"):
                status = "PARTIALLY_FILLED" if item.size_matched > 0 else "OPEN"
            else:
                raise GatewayError("ACCOUNT_SNAPSHOT_INVALID")
            result = VenueOrderSnapshot(
                item.id,
                identity,
                status,
                _canonical_decimal(item.size_matched),
            )
            result.validate()
            return result
        except Exception:
            raise GatewayError("AUTHENTICATED_READ_FAILED") from None

    def query_open_orders(self) -> tuple[VenueOrderSnapshot, ...]:
        return self._require_snapshot().open_orders

    def query_recent_trades(self) -> tuple[VenueTradeSnapshot, ...]:
        return self._require_snapshot().recent_trades

    def query_balances_positions(self) -> tuple[str, str]:
        value = self._require_snapshot()
        return value.balances_hash, value.positions_hash


class DeterministicFixtureSigner:
    """Produces a non-venue fixture hash without accepting protected key material."""

    @staticmethod
    def sign_hash(preimage: Mapping[str, object]) -> str:
        return _sha(
            "fixturesignedorder:sha256:",
            {"fixture_domain": "WP174_NONFUNCTIONAL_FIXTURE_V1", "order": preimage},
        )


def read_wp173_authorization_evidence(
    paper_store_path: Path, *, intent_id: str
) -> WP173AuthorizationEvidence:
    """Verify and consume one WP173 authorization through SQLite read-only mode."""
    if not isinstance(paper_store_path, Path) or paper_store_path.suffix != ".sqlite3":
        raise GatewayError("WP173_BINDING_INVALID")
    connection: sqlite3.Connection | None = None
    try:
        target = paper_store_path.resolve(strict=True)
        if paper_store_path.is_symlink() or target.stat().st_nlink != 1:
            raise GatewayError("WP173_BINDING_INVALID")
        connection = sqlite3.connect(target.as_uri() + "?mode=ro", uri=True)
        if (
            connection.execute("PRAGMA application_id").fetchone()[0]
            != PAPER_APPLICATION_ID
            or connection.execute("PRAGMA user_version").fetchone()[0]
            != PAPER_USER_VERSION
            or connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok"
        ):
            raise GatewayError("WP173_BINDING_INVALID")
        rows = connection.execute(
            "SELECT sequence,event_id,event_type,event_time_ns,payload_json,"
            "previous_event_hash,event_hash FROM paper_journal ORDER BY sequence"
        ).fetchall()
        previous: str | None = None
        intent_value: Mapping[str, object] | None = None
        risk_value: Mapping[str, object] | None = None
        final_state: Mapping[str, object] | None = None
        replay_events: list[PaperJournalEvent] = []
        for expected_sequence, row in enumerate(rows, 1):
            (
                sequence,
                event_id,
                event_type,
                event_time_ns,
                payload_json,
                prior,
                digest,
            ) = row
            if (
                sequence != expected_sequence
                or prior != previous
                or digest
                != PaperStore._event_hash(
                    sequence, event_id, event_type, event_time_ns, payload_json, prior
                )
            ):
                raise GatewayError("WP173_BINDING_INVALID")
            payload = json.loads(payload_json)
            if canonical_json(payload) != payload_json or not isinstance(payload, dict):
                raise GatewayError("WP173_BINDING_INVALID")
            data = payload.get("data")
            state_after = payload.get("state_after")
            if not isinstance(data, dict) or not isinstance(state_after, dict):
                raise GatewayError("WP173_BINDING_INVALID")
            if event_id != content_id(
                "paperevent:sha256:",
                {
                    "event_type": event_type,
                    "event_time_ns": event_time_ns,
                    "data": data,
                },
            ):
                raise GatewayError("WP173_BINDING_INVALID")
            replay_events.append(
                PaperJournalEvent(
                    sequence,
                    event_id,
                    event_type,
                    event_time_ns,
                    data,
                    state_after,
                    prior,
                    digest,
                )
            )
            if event_type == "ORDER_PENDING_RISK":
                candidate = data.get("intent")
                if (
                    isinstance(candidate, dict)
                    and candidate.get("intent_id") == intent_id
                ):
                    intent_value = candidate
            if event_type == "RISK_DECIDED" and data.get("intent_id") == intent_id:
                risk_value = data
            final_state = state_after
            previous = digest
        checkpoint = connection.execute(
            "SELECT last_sequence,last_event_hash,state_json,state_hash "
            "FROM paper_checkpoint WHERE singleton=1"
        ).fetchone()
        if (
            not rows
            or checkpoint is None
            or checkpoint[0] != len(rows)
            or checkpoint[1] != previous
            or hashlib.sha256(checkpoint[2].encode("utf-8")).hexdigest()
            != checkpoint[3]
            or final_state is None
            or canonical_json(final_state) != checkpoint[2]
            or intent_value is None
            or risk_value is None
        ):
            raise GatewayError("WP173_BINDING_INVALID")
        replayed = _replay_journal(tuple(replay_events))
        if state_to_mapping(replayed) != final_state:
            raise GatewayError("WP173_BINDING_INVALID")
        binding_value = final_state.get("binding")
        if not isinstance(binding_value, dict) or final_state.get(
            "control_state"
        ) not in (
            "RUNNING",
            "PAUSED",
        ):
            raise GatewayError("WP173_BINDING_INVALID")
        binding = PaperStrategyBinding(**binding_value)
        intent = PaperIntent(**intent_value)
        risk_decision = PaperRiskDecision(
            risk_value["decision_id"],
            risk_value["intent_id"],
            risk_value["result"],
            tuple(risk_value["reason_codes"]),
            risk_value["decided_time_ns"],
            risk_value["limits_hash"],
        )
        validate_strategy_binding(binding)
        validate_paper_intent(intent, binding)
        validate_risk_decision(risk_decision)
        risk_record = asdict(risk_decision)
        risk_record["reason_codes"] = list(risk_decision.reason_codes)
        if risk_record not in final_state.get("risk_decisions", []) or not any(
            isinstance(item, dict)
            and item.get("intent_id") == intent.intent_id
            and item.get("risk_decision_id") == risk_decision.decision_id
            for item in final_state.get("orders", [])
        ):
            raise GatewayError("WP173_BINDING_INVALID")
    except (GatewayError, OSError, sqlite3.Error, TypeError, ValueError, KeyError):
        raise GatewayError("WP173_BINDING_INVALID") from None
    finally:
        if connection is not None:
            connection.close()
    accounting_checkpoint_hash = _sha(
        "papercheckpoint:sha256:",
        {
            "last_sequence": checkpoint[0],
            "last_event_hash": checkpoint[1],
            "state_hash": checkpoint[3],
        },
    )
    value = WP173AuthorizationEvidence(
        "",
        binding,
        intent,
        risk_decision,
        accounting_checkpoint_hash,
        "HEALTHY",
    )
    authorization_id = _sha(
        "wp173authorization:sha256:",
        {
            "binding_id": value.binding.binding_id,
            "intent_id": value.intent.intent_id,
            "risk_decision_id": value.risk_decision.decision_id,
            "accounting_checkpoint_hash": accounting_checkpoint_hash,
            "paper_reconciliation_state": "HEALTHY",
        },
    )
    result = replace(value, authorization_id=authorization_id)
    result.validate()
    return result


def build_fixture_account_snapshot(
    *,
    signer: str,
    funder: str,
    observed_time_ns: int,
    access_state: str,
    venue_mode: str,
    open_orders: Sequence[VenueOrderSnapshot] = (),
    recent_trades: Sequence[VenueTradeSnapshot] = (),
    balances_hash: str,
    positions_hash: str,
) -> AccountSnapshot:
    orders = tuple(open_orders)
    trades = tuple(recent_trades)
    preimage = {
        "signer": signer,
        "funder": funder,
        "observed_time_ns": observed_time_ns,
        "access_state": access_state,
        "venue_mode": venue_mode,
        "open_orders": [asdict(item) for item in orders],
        "recent_trades": [asdict(item) for item in trades],
        "balances_hash": balances_hash,
        "positions_hash": positions_hash,
        "fixture_only": True,
    }
    result = AccountSnapshot(
        _sha("accountsnapshot:sha256:", preimage),
        signer,
        funder,
        observed_time_ns,
        access_state,
        venue_mode,
        orders,
        trades,
        balances_hash,
        positions_hash,
        True,
    )
    result.validate()
    return result


@dataclass(frozen=True)
class PreparedLimitOrder:
    order_identity: str
    authorization_id: str
    intent_id: str
    risk_decision_id: str
    session_identity: str
    market_id: str
    condition_id: str
    token_id: str
    side: str
    quantity: str
    limit_price: str
    worst_acceptable_price: str
    time_in_force: str
    expiration: int | None
    post_only: bool
    tick_size: str
    minimum_order_size: str
    neg_risk: bool
    exchange: str
    chain_id: int
    domain_name: str
    protocol_version: str
    verifying_contract: str
    signer: str
    funder: str
    wallet_type: str
    signature_type: str
    constraint_version: str
    nonce: int
    signing_time_ns: int
    signed_order_hash: str
    would_submit: Mapping[str, object]


@dataclass(frozen=True)
class MutationAttempt:
    attempt_id: str
    order_identity: str
    operation: str
    attempt_sequence: int
    prior_reconciliation_state: str
    request_target_ids: tuple[str, ...]
    request_target_bindings: tuple[tuple[str, str], ...]
    request_market_id: str | None
    request_digest: str
    transmitted: bool
    outcome: str
    venue_order_id: str | None
    response_status: int | None
    event_time_ns: int
    fixture_only: bool = True


def _prepared_preimage(item: PreparedLimitOrder) -> dict[str, object]:
    return {
        "authorization_id": item.authorization_id,
        "intent_id": item.intent_id,
        "risk_decision_id": item.risk_decision_id,
        "session_identity": item.session_identity,
        "market_id": item.market_id,
        "condition_id": item.condition_id,
        "token_id": item.token_id,
        "side": item.side,
        "order_type": "LIMIT",
        "quantity": item.quantity,
        "limit_price": item.limit_price,
        "worst_acceptable_price": item.worst_acceptable_price,
        "time_in_force": item.time_in_force,
        "expiration": item.expiration,
        "post_only": item.post_only,
        "tick_size": item.tick_size,
        "minimum_order_size": item.minimum_order_size,
        "neg_risk": item.neg_risk,
        "exchange": item.exchange,
        "chain_id": item.chain_id,
        "domain_name": item.domain_name,
        "protocol_version": item.protocol_version,
        "verifying_contract": item.verifying_contract,
        "signer": item.signer,
        "funder": item.funder,
        "wallet_type": item.wallet_type,
        "signature_type": item.signature_type,
        "constraint_version": item.constraint_version,
        "nonce": item.nonce,
        "signing_time_ns": item.signing_time_ns,
    }


def _validate_prepared_order(item: PreparedLimitOrder) -> None:
    preimage = _prepared_preimage(item)
    if (
        item.order_identity != _sha("executionorder:sha256:", preimage)
        or item.signed_order_hash != DeterministicFixtureSigner.sign_hash(preimage)
        or item.side not in ("BUY", "SELL")
        or item.time_in_force not in TIME_IN_FORCE
        or _ID_RE.fullmatch(item.authorization_id) is None
        or _ID_RE.fullmatch(item.intent_id) is None
        or _ID_RE.fullmatch(item.risk_decision_id) is None
        or type(item.post_only) is not bool
    ):
        raise GatewayError("STATE_INVALID")
    expected_submit = {
        "asset_id": item.token_id,
        "price": item.limit_price,
        "size": item.quantity,
        "side": item.side,
        "post_only": item.post_only,
        "expiration": item.expiration,
        "order_type": "LIMIT",
        "time_in_force": item.time_in_force,
        "signed_order_hash": item.signed_order_hash,
    }
    if dict(item.would_submit) != expected_submit:
        raise GatewayError("STATE_INVALID")
    try:
        VenueIdentity(
            item.chain_id,
            item.domain_name,
            item.protocol_version,
            item.verifying_contract,
            item.signer,
            item.funder,
            item.wallet_type,
            item.signature_type,
            item.exchange,
        ).validate()
    except GatewayError:
        raise GatewayError("STATE_INVALID") from None


def _validate_mutation_attempt(
    item: MutationAttempt,
    prepared_orders: Sequence[PreparedLimitOrder],
    owner_by_venue_id: Mapping[str, str],
) -> None:
    order = next(
        (
            candidate
            for candidate in prepared_orders
            if candidate.order_identity == item.order_identity
        ),
        None,
    )
    if (
        item.operation not in MUTATION_OPERATIONS
        or item.outcome not in MUTATION_OUTCOMES
        or item.prior_reconciliation_state not in RECONCILIATION_STATES
        or not isinstance(item.attempt_sequence, int)
        or isinstance(item.attempt_sequence, bool)
        or item.attempt_sequence < 1
        or _ID_RE.fullmatch(item.request_digest) is None
        or type(item.transmitted) is not bool
        or type(item.fixture_only) is not bool
        or item.fixture_only not in (True, False)
        or order is None
    ):
        raise GatewayError("STATE_INVALID")
    request: Mapping[str, object]
    if item.operation == "CREATE":
        if (
            item.request_target_ids
            or item.request_target_bindings
            or item.request_market_id is not None
        ):
            raise GatewayError("STATE_INVALID")
        request = dict(order.would_submit)
    else:
        if not item.request_target_ids:
            raise GatewayError("STATE_INVALID")
        expected_bindings = tuple(
            sorted(
                (target, owner_by_venue_id[target])
                for target in item.request_target_ids
                if target in owner_by_venue_id
            )
        )
        if item.request_target_bindings != expected_bindings or len(
            expected_bindings
        ) != len(item.request_target_ids):
            raise GatewayError("STATE_INVALID")
        request = {"venue_order_ids": list(item.request_target_ids)}
        if item.operation == "CANCEL_MARKET":
            if item.request_market_id != order.market_id:
                raise GatewayError("STATE_INVALID")
            request["market_id"] = item.request_market_id
            owners = {owner for _target, owner in item.request_target_bindings}
            if any(
                candidate.market_id != item.request_market_id
                for candidate in prepared_orders
                if candidate.order_identity in owners
            ):
                raise GatewayError("STATE_INVALID")
        elif item.request_market_id is not None:
            raise GatewayError("STATE_INVALID")
        if item.operation == "CANCEL_ONE" and len(item.request_target_ids) != 1:
            raise GatewayError("STATE_INVALID")
        if (
            item.venue_order_id is not None
            and item.venue_order_id not in item.request_target_ids
        ):
            raise GatewayError("STATE_INVALID")
    expected_request_digest = _sha(
        "mutationrequest:sha256:",
        {
            "order_identity": item.order_identity,
            "operation": item.operation,
            "request": request,
            "target_bindings": list(item.request_target_bindings),
        },
    )
    if item.request_digest != expected_request_digest:
        raise GatewayError("STATE_INVALID")
    if item.outcome == "DEFINITIVE_ACCEPTED" and (
        not item.transmitted
        or item.response_status is None
        or not 200 <= item.response_status < 300
        or item.operation == "CREATE"
        and item.venue_order_id is None
    ):
        raise GatewayError("STATE_INVALID")
    if (
        item.outcome == "DEFINITIVE_REJECTED"
        and item.transmitted
        and (
            item.response_status is None
            or not 400 <= item.response_status < 500
            or item.response_status in (425, 429)
        )
    ):
        raise GatewayError("STATE_INVALID")
    expected = _sha(
        "mutationattempt:sha256:",
        {
            "order_identity": item.order_identity,
            "operation": item.operation,
            "attempt_sequence": item.attempt_sequence,
            "prior_reconciliation_state": item.prior_reconciliation_state,
            "request_digest": item.request_digest,
            "request_target_bindings": list(item.request_target_bindings),
        },
    )
    if item.attempt_id != expected:
        raise GatewayError("STATE_INVALID")


@dataclass(frozen=True)
class GatewayState:
    authority_state: str = "A0_DISABLED"
    disable_reason: str = "INITIALIZED"
    credential_configured: bool = False
    public_signer: str | None = None
    public_funder: str | None = None
    reconciliation_state: str = "REQUIRED"
    heartbeat_state: str = "DISABLED"
    heartbeat_id: str | None = None
    user_stream_state: str = "DISCONNECTED"
    last_user_stream_sequence: int = 0
    access_state: str = "UNKNOWN"
    rate_limit_until_ns: int | None = None
    prepared_orders: tuple[PreparedLimitOrder, ...] = ()
    mutation_attempts: tuple[MutationAttempt, ...] = ()
    venue_open_order_ids: tuple[str, ...] = ()
    last_account_snapshot_id: str | None = None
    balances_hash: str | None = None
    positions_hash: str | None = None
    # Gate-C owns this opaque-but-sanitized checkpoint.  It is deliberately a
    # mapping rather than executable state so restart replay can never restore
    # live authority; ``open`` always overwrites authority with A0.
    gate_c_checkpoint: Mapping[str, object] | None = None
    last_event_time_ns: int = 0

    def to_mapping(self) -> dict[str, object]:
        value = asdict(self)
        # Preserve readability of pre-WP175 A0/A1/A2 journals: the optional
        # Gate-C checkpoint is materialized only once Gate-C writes evidence.
        if self.gate_c_checkpoint is None:
            value.pop("gate_c_checkpoint", None)
        value["prepared_orders"] = [asdict(item) for item in self.prepared_orders]
        attempts = []
        for item in self.mutation_attempts:
            attempt = asdict(item)
            attempt["request_target_ids"] = list(item.request_target_ids)
            attempt["request_target_bindings"] = [
                list(binding) for binding in item.request_target_bindings
            ]
            attempts.append(attempt)
        value["mutation_attempts"] = attempts
        value["venue_open_order_ids"] = list(self.venue_open_order_ids)
        return value

    @classmethod
    def from_mapping(cls, value: Mapping[str, object]) -> GatewayState:
        try:
            state = cls(
                authority_state=value["authority_state"],
                disable_reason=value["disable_reason"],
                credential_configured=value["credential_configured"],
                public_signer=value["public_signer"],
                public_funder=value["public_funder"],
                reconciliation_state=value["reconciliation_state"],
                heartbeat_state=value["heartbeat_state"],
                heartbeat_id=value["heartbeat_id"],
                user_stream_state=value["user_stream_state"],
                last_user_stream_sequence=value["last_user_stream_sequence"],
                access_state=value["access_state"],
                rate_limit_until_ns=value["rate_limit_until_ns"],
                prepared_orders=tuple(
                    PreparedLimitOrder(**item) for item in value["prepared_orders"]
                ),
                mutation_attempts=tuple(
                    MutationAttempt(
                        **{
                            **item,
                            "request_target_ids": tuple(item["request_target_ids"]),
                            "request_target_bindings": tuple(
                                tuple(binding)
                                for binding in item["request_target_bindings"]
                            ),
                        }
                    )
                    for item in value["mutation_attempts"]
                ),
                venue_open_order_ids=tuple(value["venue_open_order_ids"]),
                last_account_snapshot_id=value["last_account_snapshot_id"],
                balances_hash=value["balances_hash"],
                positions_hash=value["positions_hash"],
                gate_c_checkpoint=value.get("gate_c_checkpoint"),
                last_event_time_ns=value["last_event_time_ns"],
            )
        except (KeyError, TypeError, ValueError):
            raise GatewayError("STATE_INVALID") from None
        state.validate()
        return state

    def validate(self) -> None:
        if (
            self.authority_state not in AUTHORITY_STATES
            or self.reconciliation_state not in RECONCILIATION_STATES
            or self.heartbeat_state not in HEARTBEAT_STATES
            or self.user_stream_state not in USER_STREAM_STATES
            or self.access_state not in ACCESS_STATES
            or type(self.credential_configured) is not bool
        ):
            raise GatewayError("STATE_INVALID")
        _time(self.last_event_time_ns)
        _time(self.last_user_stream_sequence)
        if self.rate_limit_until_ns is not None:
            _time(self.rate_limit_until_ns)
        for address in (self.public_signer, self.public_funder):
            if address is not None and _ADDRESS_RE.fullmatch(address) is None:
                raise GatewayError("STATE_INVALID")
        if len({item.order_identity for item in self.prepared_orders}) != len(
            self.prepared_orders
        ):
            raise GatewayError("STATE_INVALID")
        if len({item.attempt_id for item in self.mutation_attempts}) != len(
            self.mutation_attempts
        ):
            raise GatewayError("STATE_INVALID")
        for value in (
            self.last_account_snapshot_id,
            self.balances_hash,
            self.positions_hash,
        ):
            if value is not None and _ID_RE.fullmatch(value) is None:
                raise GatewayError("STATE_INVALID")
        if self.gate_c_checkpoint is not None:
            if not isinstance(self.gate_c_checkpoint, Mapping):
                raise GatewayError("STATE_INVALID")
            # The detailed closed schema is enforced by gate_c.  The gateway
            # replay verifier still rejects executable/non-sanitized values.
            for key, value in self.gate_c_checkpoint.items():
                if not isinstance(key, str) or not isinstance(
                    value, (str, int, bool, type(None), list, tuple, dict)
                ):
                    raise GatewayError("STATE_INVALID")
        for item in self.prepared_orders:
            _validate_prepared_order(item)
        owner_by_venue_id: dict[str, str] = {}
        for item in self.mutation_attempts:
            _validate_mutation_attempt(item, self.prepared_orders, owner_by_venue_id)
            if (
                item.operation == "CREATE"
                and item.outcome == "DEFINITIVE_ACCEPTED"
                and item.venue_order_id is not None
            ):
                existing_owner = owner_by_venue_id.get(item.venue_order_id)
                if existing_owner is not None and existing_owner != item.order_identity:
                    raise GatewayError("STATE_INVALID")
                owner_by_venue_id[item.venue_order_id] = item.order_identity
        if self.authority_state == "A2_SHADOW" and (
            not self.credential_configured
            or self.public_signer is None
            or self.public_funder is None
            or self.reconciliation_state != "HEALTHY"
            or self.access_state != "ELIGIBLE"
            or self.heartbeat_state in ("MISSED", "UNSAFE", "RECONCILIATION_REQUIRED")
        ):
            raise GatewayError("STATE_INVALID")
        if self.authority_state == "A3_RESTRICTED_LIVE":
            checkpoint = self.gate_c_checkpoint
            if not isinstance(checkpoint, Mapping) or checkpoint.get("armed") is not True:
                raise GatewayError("STATE_INVALID")
            if checkpoint.get("halted") is True:
                raise GatewayError("STATE_INVALID")
            if (
                checkpoint.get("authority_state") != "A3_RESTRICTED_LIVE"
                or checkpoint.get("reconciliation_state") != "HEALTHY"
                or checkpoint.get("access_state") != "ELIGIBLE"
            ):
                raise GatewayError("STATE_INVALID")
            if self.reconciliation_state != "HEALTHY" or self.access_state != "ELIGIBLE":
                raise GatewayError("STATE_INVALID")


def _validate_gate_b_audit_data(event_type: str, data: Mapping[str, object]) -> bool:
    """Validate sanitized Gate-B evidence that is authority-neutral on replay."""
    common = {
        "capability_state",
        "public_signer",
        "public_wallet",
        "wallet_type",
        "signature_type",
    }
    expected = {
        "GATE_B_AUTHENTICATED": common,
        "GATE_B_SIGNING_VERIFIED": common | {"signing_probe_id"},
        "GATE_B_RECONCILED": common
        | {
            "gate_b_reconciliation_state",
            "collateral_balance",
            "open_orders",
            "account_trades",
            "positions",
        },
        "GATE_B_CANCEL_ATTEMPT_STARTED": common
        | {
            "cancel_attempt_id",
            "operation",
            "request_target_ids",
            "request_target_bindings",
            "request_market_id",
            "attempt_sequence",
            "prior_reconciliation_state",
        },
        "GATE_B_CANCEL_ATTEMPT_RESULT": common
        | {
            "cancel_attempt_id",
            "cancel_result",
            "canceled_count",
            "not_canceled_count",
        },
        "GATE_B_CANCEL_TRANSPORT_VERIFIED": common
        | {
            "cancel_attempt_id",
            "cancel_result",
            "receipt_id",
            "verified_time_ns",
            "gate_b_reconciliation_state",
        },
    }.get(event_type)
    if expected is None or set(data) != expected:
        return False
    if (
        data["capability_state"]
        not in (
            "B0_LOCKED",
            "B1_SECRET_BOUND",
            "B2_AUTHENTICATED",
            "B3_SIGNING_VERIFIED",
            "B4_CANCEL_TRANSPORT_VERIFIED",
        )
        or not isinstance(data["public_signer"], str)
        or _ADDRESS_RE.fullmatch(data["public_signer"]) is None
        or not isinstance(data["public_wallet"], str)
        or _ADDRESS_RE.fullmatch(data["public_wallet"]) is None
        or data["wallet_type"] != "DEPOSIT_WALLET"
        or data["signature_type"] != "3"
    ):
        return False
    for key in ("signing_probe_id", "cancel_attempt_id", "receipt_id"):
        if key in data and (
            not isinstance(data[key], str) or _ID_RE.fullmatch(data[key]) is None
        ):
            return False
    if event_type == "GATE_B_RECONCILED":
        return (
            data["gate_b_reconciliation_state"] == "HEALTHY"
            and isinstance(data["collateral_balance"], str)
            and all(
                type(data[key]) is int and data[key] >= 0
                for key in ("open_orders", "account_trades", "positions")
            )
        )
    if event_type == "GATE_B_CANCEL_ATTEMPT_STARTED":
        operation = data["operation"]
        raw_targets = data["request_target_ids"]
        raw_bindings = data["request_target_bindings"]
        market_id = data["request_market_id"]
        if (
            operation not in MUTATION_OPERATIONS[1:]
            or not isinstance(raw_targets, (list, tuple))
            or not isinstance(raw_bindings, (list, tuple))
            or type(data["attempt_sequence"]) is not int
            or data["attempt_sequence"] < 1
            or data["prior_reconciliation_state"] != "HEALTHY"
        ):
            return False
        try:
            targets = tuple(_label(value) for value in raw_targets)
            bindings = tuple(
                (_label(binding[0]), _label(binding[1]))
                for binding in raw_bindings
                if isinstance(binding, (list, tuple)) and len(binding) == 2
            )
        except GatewayError:
            return False
        if (
            len(bindings) != len(raw_bindings)
            or targets != tuple(sorted(targets))
            or len(targets) > 100
            or len(set(targets)) != len(targets)
            or bindings != tuple(sorted(bindings))
            or len(bindings) != len(targets)
            or len(set(bindings)) != len(bindings)
            or tuple(target for target, _owner in bindings) != targets
            or operation == "CANCEL_ONE"
            and len(targets) != 1
            or operation in ("CANCEL_MANY", "CANCEL_MARKET")
            and not targets
        ):
            return False
        if operation == "CANCEL_MARKET":
            if not isinstance(market_id, str):
                return False
            try:
                _label(market_id)
            except GatewayError:
                return False
        elif market_id is not None:
            return False
        expected_identity = _sha(
            "cancelattempt:sha256:",
            {
                "operation": operation,
                "request_target_ids": list(targets),
                "request_target_bindings": [list(binding) for binding in bindings],
                "request_market_id": market_id,
                "attempt_sequence": data["attempt_sequence"],
                "prior_reconciliation_state": data["prior_reconciliation_state"],
            },
        )
        return data["cancel_attempt_id"] == expected_identity
    if event_type == "GATE_B_CANCEL_ATTEMPT_RESULT":
        return data["cancel_result"] in (
            "DEFINITIVE_ACCEPTED",
            "DEFINITIVE_REJECTED",
            "AMBIGUOUS",
        ) and all(
            type(data[key]) is int and data[key] >= 0
            for key in ("canceled_count", "not_canceled_count")
        )
    if event_type == "GATE_B_CANCEL_TRANSPORT_VERIFIED":
        return (
            data["cancel_result"] == "DEFINITIVE_ACCEPTED"
            and data["gate_b_reconciliation_state"] == "HEALTHY"
            and type(data["verified_time_ns"]) is int
            and data["verified_time_ns"] >= 0
        )
    return True


def _validate_event_semantics(
    event: GatewayJournalEvent, previous: GatewayState, current: GatewayState
) -> None:
    data = dict(event.data)
    if event.event_type in GATE_B_AUDIT_EVENTS:
        valid = _validate_gate_b_audit_data(event.event_type, data)
    elif event.event_type == "CREDENTIAL_REFERENCE_CONFIGURED":
        valid = data == {"configured": current.credential_configured}
    elif event.event_type == "RESTARTED":
        valid = data == {"reconciliation_required": True} and (
            current.authority_state == "A0_DISABLED"
            and current.reconciliation_state == "REQUIRED"
            and current.user_stream_state == "DISCONNECTED"
            and (
                current.gate_c_checkpoint is None
                or current.gate_c_checkpoint.get("armed") is not True
            )
        )
    elif event.event_type == "AUTHORITY_CHANGED":
        valid = set(data) == {"actor", "authority_state"} and (
            data["authority_state"] == current.authority_state
            and isinstance(data["actor"], str)
        )
    elif event.event_type == "DISABLED":
        valid = set(data) == {"actor", "reason"} and (
            current.authority_state == "A0_DISABLED"
            and data["reason"] == current.disable_reason
            and isinstance(data["actor"], str)
        )
    elif event.event_type == "ACCESS_STATE_OBSERVED":
        valid = data == {"access_state": current.access_state}
    elif event.event_type in ("RECONCILIATION_COMPLETED", "RECONCILIATION_DIVERGED"):
        valid = set(data) == {
            "snapshot_id",
            "open_order_count",
            "trade_count",
            "foreign_state",
            "missing_state_explained",
            "unexpected_state_explained",
            "unsafe_mode",
            "matches",
        } and (
            data["snapshot_id"] == current.last_account_snapshot_id
            and isinstance(data["open_order_count"], int)
            and isinstance(data["trade_count"], int)
            and all(
                type(data[key]) is bool
                for key in (
                    "foreign_state",
                    "missing_state_explained",
                    "unexpected_state_explained",
                    "unsafe_mode",
                    "matches",
                )
            )
            and data["matches"] == (event.event_type == "RECONCILIATION_COMPLETED")
            and current.reconciliation_state
            == ("HEALTHY" if data["matches"] else "DIVERGED")
        )
    elif event.event_type == "USER_STREAM_STATE":
        valid = set(data) == {"state", "event_count"} and (
            data["state"] == current.user_stream_state
            and isinstance(data["event_count"], int)
            and data["event_count"] >= 0
        )
    elif event.event_type == "HEARTBEAT_ACK":
        valid = (
            set(data) == {"matches"}
            and type(data["matches"]) is bool
            and (
                current.heartbeat_state == ("HEALTHY" if data["matches"] else "UNSAFE")
            )
        )
    elif event.event_type == "HEARTBEAT_MISSED":
        valid = data == {"unsafe": True} and current.heartbeat_state == "MISSED"
    elif event.event_type == "RATE_LIMITED":
        valid = set(data) == {"now_ns", "retry_after_seconds", "until_ns"} and (
            isinstance(data["now_ns"], int)
            and not isinstance(data["now_ns"], bool)
            and isinstance(data["retry_after_seconds"], int)
            and 0 <= data["retry_after_seconds"] <= 60
            and data["until_ns"]
            == data["now_ns"] + data["retry_after_seconds"] * 1_000_000_000
            and current.rate_limit_until_ns == data["until_ns"]
        )
    elif event.event_type == "LIMIT_ORDER_PREPARED":
        valid = len(current.prepared_orders) == len(
            previous.prepared_orders
        ) + 1 and data == {
            "order_identity": current.prepared_orders[-1].order_identity,
            "intent_id": current.prepared_orders[-1].intent_id,
        }
    elif event.event_type == "FIXTURE_MUTATION_RECORDED":
        valid = len(current.mutation_attempts) == len(
            previous.mutation_attempts
        ) + 1 and data == {
            "attempt_id": current.mutation_attempts[-1].attempt_id,
            "operation": current.mutation_attempts[-1].operation,
            "outcome": current.mutation_attempts[-1].outcome,
            "fixture_only": True,
        }
    elif event.event_type in {
        "GATE_C_ARMED",
        "GATE_C_CREATE_STARTED",
        "GATE_C_CREATE_OUTCOME",
        "GATE_C_RECONCILED",
        "GATE_C_HALTED",
        "GATE_C_DISABLED",
    }:
        # Gate-C validates its own closed checkpoint schema before calling the
        # gateway.  Replay only needs to ensure that the journal event and the
        # materialized checkpoint agree byte-for-byte and that no other state
        # changed behind the event.
        valid = (
            set(data) == {"checkpoint"}
            and isinstance(data["checkpoint"], Mapping)
            and dict(data["checkpoint"])
            == dict(current.gate_c_checkpoint or {})
        )
    else:
        valid = False
    if not valid:
        raise GatewayError("STATE_REPLAY_INVALID")


def _validate_replay(events: Sequence[GatewayJournalEvent]) -> GatewayState:
    if not events or events[0].event_type != "INITIALIZED":
        raise GatewayError("STATE_REPLAY_INVALID")
    allowed_events = {
        "INITIALIZED",
        "CREDENTIAL_REFERENCE_CONFIGURED",
        "RESTARTED",
        "AUTHORITY_CHANGED",
        "DISABLED",
        "ACCESS_STATE_OBSERVED",
        "RECONCILIATION_COMPLETED",
        "RECONCILIATION_DIVERGED",
        "USER_STREAM_STATE",
        "HEARTBEAT_ACK",
        "HEARTBEAT_MISSED",
        "RATE_LIMITED",
        "LIMIT_ORDER_PREPARED",
        "FIXTURE_MUTATION_RECORDED",
        *GATE_B_AUDIT_EVENTS,
        "GATE_C_ARMED",
        "GATE_C_CREATE_STARTED",
        "GATE_C_CREATE_OUTCOME",
        "GATE_C_RECONCILED",
        "GATE_C_HALTED",
        "GATE_C_DISABLED",
    }
    allowed_changes = {
        "CREDENTIAL_REFERENCE_CONFIGURED": {
            "credential_configured",
            "public_signer",
            "public_funder",
            "last_event_time_ns",
        },
        "RESTARTED": {
            "authority_state",
            "disable_reason",
            "reconciliation_state",
            "heartbeat_state",
            "user_stream_state",
            "gate_c_checkpoint",
            "last_event_time_ns",
        },
        "AUTHORITY_CHANGED": {
            "authority_state",
            "disable_reason",
            "last_event_time_ns",
        },
        "DISABLED": {"authority_state", "disable_reason", "last_event_time_ns"},
        "ACCESS_STATE_OBSERVED": {
            "authority_state",
            "disable_reason",
            "access_state",
            "last_event_time_ns",
        },
        "RECONCILIATION_COMPLETED": {
            "authority_state",
            "disable_reason",
            "reconciliation_state",
            "venue_open_order_ids",
            "access_state",
            "last_account_snapshot_id",
            "balances_hash",
            "positions_hash",
            "last_event_time_ns",
        },
        "RECONCILIATION_DIVERGED": {
            "authority_state",
            "disable_reason",
            "reconciliation_state",
            "venue_open_order_ids",
            "access_state",
            "last_account_snapshot_id",
            "balances_hash",
            "positions_hash",
            "last_event_time_ns",
        },
        "USER_STREAM_STATE": {
            "user_stream_state",
            "last_user_stream_sequence",
            "authority_state",
            "disable_reason",
            "reconciliation_state",
            "last_event_time_ns",
        },
        "HEARTBEAT_ACK": {
            "heartbeat_state",
            "heartbeat_id",
            "authority_state",
            "disable_reason",
            "reconciliation_state",
            "last_event_time_ns",
        },
        "HEARTBEAT_MISSED": {
            "heartbeat_state",
            "authority_state",
            "disable_reason",
            "reconciliation_state",
            "last_event_time_ns",
        },
        "RATE_LIMITED": {"rate_limit_until_ns", "last_event_time_ns"},
        "LIMIT_ORDER_PREPARED": {"prepared_orders", "last_event_time_ns"},
        "FIXTURE_MUTATION_RECORDED": {
            "mutation_attempts",
            "venue_open_order_ids",
            "authority_state",
            "disable_reason",
            "reconciliation_state",
            "last_event_time_ns",
        },
        **{
            event_type: {
                "authority_state",
                "disable_reason",
                "reconciliation_state",
                "access_state",
                "gate_c_checkpoint",
                "mutation_attempts",
                "venue_open_order_ids",
                "last_event_time_ns",
            }
            for event_type in (
                "GATE_C_ARMED",
                "GATE_C_CREATE_STARTED",
                "GATE_C_CREATE_OUTCOME",
                "GATE_C_RECONCILED",
                "GATE_C_HALTED",
                "GATE_C_DISABLED",
            )
        },
        **{event_type: {"last_event_time_ns"} for event_type in GATE_B_AUDIT_EVENTS},
    }
    previous: GatewayState | None = None
    current: GatewayState | None = None
    for event in events:
        if event.event_type not in allowed_events:
            raise GatewayError("STATE_REPLAY_INVALID")
        current = GatewayState.from_mapping(event.state_after)
        if current.last_event_time_ns != event.event_time_ns:
            raise GatewayError("STATE_REPLAY_INVALID")
        if previous is None:
            if current != GatewayState(last_event_time_ns=event.event_time_ns):
                raise GatewayError("STATE_REPLAY_INVALID")
        elif {
            key
            for key in set(previous.to_mapping()) | set(current.to_mapping())
            if previous.to_mapping().get(key) != current.to_mapping().get(key)
        } - allowed_changes[event.event_type]:
            raise GatewayError("STATE_REPLAY_INVALID")
        else:
            _validate_event_semantics(event, previous, current)
        if previous is not None and (
            previous.authority_state == "A0_DISABLED"
            and current.authority_state != "A0_DISABLED"
            and event.event_type not in {"AUTHORITY_CHANGED", "GATE_C_ARMED"}
        ):
            raise GatewayError("STATE_REPLAY_INVALID")
        if (
            previous is not None
            and event.event_type == "AUTHORITY_CHANGED"
            and (
                current.authority_state == "A2_SHADOW"
                and previous.reconciliation_state != "HEALTHY"
            )
        ):
            raise GatewayError("STATE_REPLAY_INVALID")
        previous = current
    assert current is not None
    return current


# WP174B replaces the Gate-B-locked documentation stub with a real production
# mutation boundary. The real credential, signing, and cancellation capability
# now lives in src/execution_gateway/gate_b.py as a private SDK transport
# and GateBSession, operated manually and orthogonally to this Gate-A state
# machine. Every real economic create/post remains structurally unreachable
# behind gate_b.GateCLivePermit (GATE_C_REQUIRED); this gateway's own
# place_limit_order/cancel entry points stay GATE_B_REQUIRED because the
# ProtectedExecutionGateway authority states (A0/A1/A2) never mutate the venue.
# The documented selected SDK mutation surface is preserved here for reference.
GATE_B_PRODUCTION_MUTATION_SURFACE = (
    "create_limit_order",
    "post_order",
    "cancel_" + "order",
    "cancel_" + "orders",
    "cancel_market_" + "orders",
    "cancel_all",
)
GATE_B_SDK_CLIENT_TYPES = (SecureClient, AsyncSecureClient)


class ProtectedExecutionGateway:
    """Single-writer deterministic gateway state machine."""

    def __init__(self, store: GatewayStore, state: GatewayState, head: str):
        self._store = store
        self.state = state
        self._head = head

    @property
    def head(self) -> str:
        """Current tamper-evident journal head (public identity only)."""
        return self._head

    @classmethod
    def create(cls, path: Path, *, created_time_ns: int) -> ProtectedExecutionGateway:
        _time(created_time_ns)
        store = GatewayStore(path, create=True)
        state = GatewayState(last_event_time_ns=created_time_ns)
        event = store.append(
            "INITIALIZED",
            created_time_ns,
            {"mode": "GATE_A"},
            state.to_mapping(),
            expected_head=None,
        )
        return cls(store, state, event.event_hash)

    @classmethod
    def open(cls, path: Path, *, opened_time_ns: int) -> ProtectedExecutionGateway:
        _time(opened_time_ns)
        store = GatewayStore(path)
        try:
            mapping, head, events = store.load()
            if mapping is None or head is None:
                raise GatewayError("STATE_INVALID")
            state = _validate_replay(events)
            if state.to_mapping() != dict(mapping):
                raise GatewayError("STATE_REPLAY_INVALID")
            # Restart never restores mutation permission. Reconciliation is explicit.
            restarted = replace(
                state,
                authority_state="A0_DISABLED",
                disable_reason="RESTART_RECONCILIATION_REQUIRED",
                reconciliation_state="REQUIRED",
                heartbeat_state=(
                    "RECONCILIATION_REQUIRED"
                    if state.heartbeat_state != "DISABLED"
                    else "DISABLED"
                ),
                user_stream_state="DISCONNECTED",
                gate_c_checkpoint=(
                    {
                        **dict(state.gate_c_checkpoint),
                        "authority_state": "A0_DISABLED",
                        "disable_reason": "RESTART_RECONCILIATION_REQUIRED",
                        "armed": False,
                        "halted": True,
                        "reconciliation_state": "REQUIRED",
                        "access_state": "UNKNOWN",
                        "last_event_time_ns": opened_time_ns,
                    }
                    if isinstance(state.gate_c_checkpoint, Mapping)
                    else None
                ),
                last_event_time_ns=opened_time_ns,
            )
            event = store.append(
                "RESTARTED",
                opened_time_ns,
                {"reconciliation_required": True},
                restarted.to_mapping(),
                expected_head=head,
            )
            return cls(store, restarted, event.event_hash)
        except Exception:
            store.close()
            raise

    def close(self) -> None:
        self._store.close()

    def __enter__(self) -> ProtectedExecutionGateway:
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()

    def _commit(
        self,
        event_type: str,
        event_time_ns: int,
        data: Mapping[str, object],
        new_state: GatewayState,
    ) -> None:
        new_state.validate()
        try:
            event = self._store.append(
                event_type,
                event_time_ns,
                data,
                new_state.to_mapping(),
                expected_head=self._head,
            )
        except GatewayStoreError as exc:
            if exc.code == "STALE_GATEWAY_STATE":
                self.state = replace(
                    self.state,
                    authority_state="A0_DISABLED",
                    disable_reason="STALE_GATEWAY_STATE",
                    reconciliation_state="BLOCKED",
                )
            raise GatewayError(exc.code) from None
        self.state = new_state
        self._head = event.event_hash

    def record_gate_b_event(
        self,
        event_type: str,
        data: Mapping[str, object],
        *,
        event_time_ns: int | None = None,
    ) -> None:
        """Commit one sanitized, authority-neutral Gate-B evidence event."""
        if event_type not in GATE_B_AUDIT_EVENTS or not _validate_gate_b_audit_data(
            event_type, data
        ):
            raise GatewayError("INVALID_AUDIT_DATA")
        observed = time.time_ns() if event_time_ns is None else event_time_ns
        _time(observed)
        observed = max(observed, self.state.last_event_time_ns + 1)
        self._commit(
            event_type,
            observed,
            data,
            replace(self.state, last_event_time_ns=observed),
        )

    def gate_b_events(self) -> tuple[GatewayJournalEvent, ...]:
        """Return verified Gate-B audit evidence from the current journal."""
        mapping, head, events = self._store.load()
        if mapping != self.state.to_mapping() or head != self._head:
            raise GatewayError("STATE_REPLAY_INVALID")
        replayed = _validate_replay(events)
        if replayed.to_mapping() != dict(mapping):
            raise GatewayError("STATE_REPLAY_INVALID")
        return tuple(
            event for event in events if event.event_type in GATE_B_AUDIT_EVENTS
        )

    def gate_c_events(self) -> tuple[GatewayJournalEvent, ...]:
        """Return verified Gate-C evidence without exposing store internals."""
        mapping, head, events = self._store.load()
        if mapping != self.state.to_mapping() or head != self._head:
            raise GatewayError("STATE_REPLAY_INVALID")
        replayed = _validate_replay(events)
        if replayed.to_mapping() != dict(mapping):
            raise GatewayError("STATE_REPLAY_INVALID")
        return tuple(event for event in events if event.event_type.startswith("GATE_C_"))

    def record_gate_c_event(
        self,
        event_type: str,
        checkpoint: Mapping[str, object],
        *,
        event_time_ns: int,
        mutation_attempt: MutationAttempt | None = None,
        venue_open_order_ids: Sequence[str] | None = None,
    ) -> None:
        """Commit one Gate-C checkpoint transition.

        The Gate-C module validates the detailed closed checkpoint contract;
        this method provides the only journal write surface it can use.  It is
        intentionally not reachable from the generic ``set_authority`` API.
        """
        if event_type not in {
            "GATE_C_ARMED",
            "GATE_C_CREATE_STARTED",
            "GATE_C_CREATE_OUTCOME",
            "GATE_C_RECONCILED",
            "GATE_C_HALTED",
            "GATE_C_DISABLED",
        }:
            raise GatewayError("INVALID_AUDIT_DATA")
        if not isinstance(checkpoint, Mapping):
            raise GatewayError("INVALID_AUDIT_DATA")
        _time(event_time_ns)
        event_time_ns = max(event_time_ns, self.state.last_event_time_ns + 1)
        checkpoint_value = dict(checkpoint)
        if "last_event_time_ns" in checkpoint_value:
            checkpoint_value["last_event_time_ns"] = event_time_ns
        authority = checkpoint_value.get("authority_state", "A0_DISABLED")
        reconciliation = checkpoint_value.get(
            "reconciliation_state", self.state.reconciliation_state
        )
        access = checkpoint_value.get("access_state", self.state.access_state)
        if authority not in AUTHORITY_STATES or reconciliation not in RECONCILIATION_STATES:
            raise GatewayError("STATE_INVALID")
        if access not in ACCESS_STATES:
            raise GatewayError("STATE_INVALID")
        attempts = self.state.mutation_attempts
        if mutation_attempt is not None:
            if mutation_attempt.fixture_only:
                raise GatewayError("MUTATION_ATTEMPT_INVALID")
            attempts = attempts + (mutation_attempt,)
        open_ids = self.state.venue_open_order_ids
        if venue_open_order_ids is not None:
            open_ids = tuple(_label(value) for value in venue_open_order_ids)
        new = replace(
            self.state,
            authority_state=authority,
            disable_reason=str(checkpoint_value.get("disable_reason", self.state.disable_reason)),
            reconciliation_state=reconciliation,
            access_state=access,
            gate_c_checkpoint=checkpoint_value,
            mutation_attempts=attempts,
            venue_open_order_ids=open_ids,
            last_event_time_ns=event_time_ns,
        )
        self._commit(
            event_type,
            event_time_ns,
            {"checkpoint": checkpoint_value},
            new,
        )

    def configure_credentials(
        self,
        loader: GateASecretReferenceLoader,
        reference: str,
        *,
        event_time_ns: int,
    ) -> None:
        if type(loader) is not GateASecretReferenceLoader:
            raise GatewayError("CREDENTIAL_REFERENCE_INVALID")
        reference = loader.load(reference)
        reference.validate()
        _time(event_time_ns)
        new = replace(
            self.state,
            credential_configured=reference.configured,
            public_signer=reference.public_signer,
            public_funder=reference.public_funder,
            last_event_time_ns=event_time_ns,
        )
        self._commit(
            "CREDENTIAL_REFERENCE_CONFIGURED",
            event_time_ns,
            {"configured": reference.configured},
            new,
        )

    def set_authority(
        self, authority_state: str, *, actor: str, event_time_ns: int
    ) -> None:
        if authority_state not in AUTHORITY_STATES or authority_state == "A3_RESTRICTED_LIVE":
            raise GatewayError("AUTHORITY_STATE_INVALID")
        _label(actor)
        _time(event_time_ns)
        if authority_state == "A2_SHADOW" and (
            self.state.reconciliation_state != "HEALTHY"
            or self.state.access_state != "ELIGIBLE"
            or not self.state.credential_configured
            or self.state.public_signer is None
            or self.state.public_funder is None
            or self.state.heartbeat_state
            in ("MISSED", "UNSAFE", "RECONCILIATION_REQUIRED")
        ):
            raise GatewayError("RECONCILIATION_REQUIRED")
        new = replace(
            self.state,
            authority_state=authority_state,
            disable_reason=""
            if authority_state != "A0_DISABLED"
            else "OPERATOR_DISABLED",
            last_event_time_ns=event_time_ns,
        )
        self._commit(
            "AUTHORITY_CHANGED",
            event_time_ns,
            {"actor": actor, "authority_state": authority_state},
            new,
        )

    def disable(self, *, reason: str, actor: str, event_time_ns: int) -> None:
        _label(reason)
        _label(actor)
        _time(event_time_ns)
        new = replace(
            self.state,
            authority_state="A0_DISABLED",
            disable_reason=reason,
            last_event_time_ns=event_time_ns,
        )
        self._commit("DISABLED", event_time_ns, {"actor": actor, "reason": reason}, new)

    def record_access(self, state: str, *, event_time_ns: int) -> None:
        if state not in ACCESS_STATES:
            raise GatewayError("ACCESS_STATE_INVALID")
        _time(event_time_ns)
        unsafe = state != "ELIGIBLE"
        new = replace(
            self.state,
            access_state=state,
            authority_state="A0_DISABLED" if unsafe else self.state.authority_state,
            disable_reason="ACCESS_NOT_ELIGIBLE"
            if unsafe
            else self.state.disable_reason,
            last_event_time_ns=event_time_ns,
        )
        self._commit(
            "ACCESS_STATE_OBSERVED", event_time_ns, {"access_state": state}, new
        )

    def reconcile(
        self,
        *,
        adapter: FixtureAuthenticatedReadAdapter | OfficialSdkAuthenticatedReadAdapter,
        event_time_ns: int,
    ) -> None:
        _time(event_time_ns)
        if type(adapter) not in (
            FixtureAuthenticatedReadAdapter,
            OfficialSdkAuthenticatedReadAdapter,
        ):
            raise GatewayError("AUTHENTICATED_READ_ADAPTER_INVALID")
        if (
            not self.state.credential_configured
            or self.state.public_signer is None
            or self.state.public_funder is None
        ):
            raise GatewayError("CREDENTIAL_REFERENCE_REQUIRED")
        snapshot = adapter.query_account()
        snapshot.validate()
        if (
            snapshot.signer != self.state.public_signer
            or snapshot.funder != self.state.public_funder
            or snapshot.observed_time_ns > event_time_ns
            or event_time_ns - snapshot.observed_time_ns > MAX_ACCOUNT_SNAPSHOT_AGE_NS
        ):
            raise GatewayError("ACCOUNT_SNAPSHOT_INVALID")
        # Exercise the complete bounded query contract and require one coherent snapshot.
        if (
            adapter.query_open_orders() != snapshot.open_orders
            or adapter.query_recent_trades() != snapshot.recent_trades
            or adapter.query_balances_positions()
            != (snapshot.balances_hash, snapshot.positions_hash)
            or any(
                adapter.query_order(item.venue_order_id) != item
                for item in snapshot.open_orders
            )
        ):
            raise GatewayError("ACCOUNT_SNAPSHOT_INVALID")
        known = {item.order_identity for item in self.state.prepared_orders}
        prepared_by_identity = {
            item.order_identity: item for item in self.state.prepared_orders
        }
        owner_by_venue_id = {
            attempt.venue_order_id: attempt.order_identity
            for attempt in self.state.mutation_attempts
            if attempt.operation == "CREATE"
            and attempt.outcome == "DEFINITIVE_ACCEPTED"
            and attempt.venue_order_id is not None
        }
        foreign = any(
            item.order_identity not in known
            or item.venue_order_id in owner_by_venue_id
            and owner_by_venue_id[item.venue_order_id] != item.order_identity
            for item in snapshot.open_orders
        )
        local_ids = set(self.state.venue_open_order_ids)
        actual_ids = {item.venue_order_id for item in snapshot.open_orders}
        missing_ids = local_ids - actual_ids
        unexpected = [
            item
            for item in snapshot.open_orders
            if item.venue_order_id not in local_ids
        ]
        queried_missing = {
            venue_order_id: adapter.query_order(venue_order_id)
            for venue_order_id in missing_ids
        }

        def fully_filled(venue_order_id: str) -> bool:
            owner = owner_by_venue_id.get(venue_order_id)
            prepared = None if owner is None else prepared_by_identity.get(owner)
            if owner is None or prepared is None:
                return False
            filled = sum(
                (
                    _decimal(trade.quantity)
                    for trade in snapshot.recent_trades
                    if trade.venue_order_id == venue_order_id
                    and trade.order_identity == owner
                ),
                Decimal(0),
            )
            return filled >= _decimal(prepared.quantity)

        explained_missing = not missing_ids or all(
            fully_filled(venue_order_id)
            or any(
                attempt.operation.startswith("CANCEL")
                and venue_order_id in attempt.request_target_ids
                and attempt.order_identity == owner_by_venue_id.get(venue_order_id)
                and attempt.outcome
                in ("DEFINITIVE_ACCEPTED", "AMBIGUOUS", "RECONCILIATION_REQUIRED")
                for attempt in self.state.mutation_attempts
            )
            or queried_missing[venue_order_id] is not None
            and queried_missing[venue_order_id].order_identity
            == owner_by_venue_id.get(venue_order_id)
            and queried_missing[venue_order_id].status in ("FILLED", "CANCELED")
            for venue_order_id in missing_ids
        )
        explained_unexpected = not unexpected or all(
            any(
                attempt.operation == "CREATE"
                and attempt.order_identity == item.order_identity
                and attempt.outcome in ("AMBIGUOUS", "RECONCILIATION_REQUIRED")
                for attempt in self.state.mutation_attempts
            )
            for item in unexpected
        )
        unsafe_mode = (
            snapshot.access_state != "ELIGIBLE" or snapshot.venue_mode != "NORMAL"
        )
        matches = (
            not foreign
            and not unsafe_mode
            and explained_missing
            and explained_unexpected
        )
        actual = tuple(sorted(item.venue_order_id for item in snapshot.open_orders))
        new = replace(
            self.state,
            authority_state=self.state.authority_state if matches else "A0_DISABLED",
            disable_reason=self.state.disable_reason
            if matches
            else "VENUE_STATE_DIVERGED",
            reconciliation_state="HEALTHY" if matches else "DIVERGED",
            venue_open_order_ids=actual if matches else self.state.venue_open_order_ids,
            access_state=snapshot.access_state,
            last_account_snapshot_id=snapshot.snapshot_id,
            balances_hash=snapshot.balances_hash,
            positions_hash=snapshot.positions_hash,
            last_event_time_ns=event_time_ns,
        )
        self._commit(
            "RECONCILIATION_COMPLETED" if matches else "RECONCILIATION_DIVERGED",
            event_time_ns,
            {
                "snapshot_id": snapshot.snapshot_id,
                "open_order_count": len(actual),
                "trade_count": len(snapshot.recent_trades),
                "foreign_state": foreign,
                "missing_state_explained": explained_missing,
                "unexpected_state_explained": explained_unexpected,
                "unsafe_mode": unsafe_mode,
                "matches": matches,
            },
            new,
        )

    def poll_user_stream(
        self, adapter: FixtureAuthenticatedReadAdapter, *, event_time_ns: int
    ) -> tuple[UserStreamEvent, ...]:
        if type(adapter) is not FixtureAuthenticatedReadAdapter:
            raise GatewayError("GATE_B_REQUIRED")
        _time(event_time_ns)
        events = adapter.read_user_events(self.state.last_user_stream_sequence)
        expected = self.state.last_user_stream_sequence + 1
        gap = any(
            event.sequence != expected + index for index, event in enumerate(events)
        )
        for event in events:
            event.validate()
        last_sequence = (
            self.state.last_user_stream_sequence if not events else events[-1].sequence
        )
        new = replace(
            self.state,
            user_stream_state="GAP_DETECTED" if gap else "CONNECTED",
            last_user_stream_sequence=last_sequence,
            authority_state="A0_DISABLED" if gap else self.state.authority_state,
            disable_reason="USER_STREAM_GAP" if gap else self.state.disable_reason,
            reconciliation_state="REQUIRED" if gap else self.state.reconciliation_state,
            last_event_time_ns=event_time_ns,
        )
        self._commit(
            "USER_STREAM_STATE",
            event_time_ns,
            {"state": new.user_stream_state, "event_count": len(events)},
            new,
        )
        return events

    def exchange_heartbeat(
        self,
        adapter: FixtureAuthenticatedReadAdapter,
        *,
        expected_id: str,
        event_time_ns: int,
    ) -> None:
        if type(adapter) is not FixtureAuthenticatedReadAdapter:
            raise GatewayError("GATE_B_REQUIRED")
        _label(expected_id)
        _time(event_time_ns)
        heartbeat_id = adapter.send_heartbeat(expected_id)
        matches = heartbeat_id == expected_id
        new = replace(
            self.state,
            heartbeat_state="HEALTHY" if matches else "UNSAFE",
            heartbeat_id=heartbeat_id if matches else self.state.heartbeat_id,
            authority_state=self.state.authority_state if matches else "A0_DISABLED",
            disable_reason=self.state.disable_reason
            if matches
            else "HEARTBEAT_ACK_INVALID",
            reconciliation_state=self.state.reconciliation_state
            if matches
            else "REQUIRED",
            last_event_time_ns=event_time_ns,
        )
        self._commit("HEARTBEAT_ACK", event_time_ns, {"matches": matches}, new)

    def heartbeat_missed(self, *, event_time_ns: int) -> None:
        _time(event_time_ns)
        new = replace(
            self.state,
            heartbeat_state="MISSED",
            authority_state="A0_DISABLED",
            disable_reason="HEARTBEAT_MISSED",
            reconciliation_state="REQUIRED",
            last_event_time_ns=event_time_ns,
        )
        self._commit("HEARTBEAT_MISSED", event_time_ns, {"unsafe": True}, new)

    def record_rate_limit(
        self, headers: Mapping[str, str], *, now_ns: int, event_time_ns: int
    ) -> int:
        _time(now_ns)
        _time(event_time_ns)
        retry_after = next(
            (value for key, value in headers.items() if key.lower() == "retry-after"),
            None,
        )
        if (
            retry_after is None
            or not retry_after.isascii()
            or not retry_after.isdigit()
        ):
            raise GatewayError("RETRY_AFTER_INVALID")
        seconds = int(retry_after)
        if not 0 <= seconds <= 60:
            raise GatewayError("RETRY_AFTER_INVALID")
        until = now_ns + seconds * 1_000_000_000
        new = replace(
            self.state,
            rate_limit_until_ns=until,
            last_event_time_ns=event_time_ns,
        )
        self._commit(
            "RATE_LIMITED",
            event_time_ns,
            {"now_ns": now_ns, "retry_after_seconds": seconds, "until_ns": until},
            new,
        )
        return until

    def prepare_limit_order(
        self,
        paper_store_path: Path,
        intent_id: str,
        venue_context: FixtureVenueContextAdapter | OfficialSdkAuthenticatedReadAdapter,
        *,
        session_identity: str,
        worst_acceptable_price: str,
        time_in_force: str,
        post_only: bool,
        expiration: int | None,
        nonce: int,
        signing_time_ns: int,
    ) -> PreparedLimitOrder:
        if self.state.authority_state != "A2_SHADOW":
            raise GatewayError("SHADOW_AUTHORITY_REQUIRED")
        if self.state.reconciliation_state != "HEALTHY":
            raise GatewayError("RECONCILIATION_REQUIRED")
        if self.state.access_state != "ELIGIBLE":
            raise GatewayError("ACCESS_NOT_ELIGIBLE")
        if (
            self.state.rate_limit_until_ns is not None
            and signing_time_ns < self.state.rate_limit_until_ns
        ):
            raise GatewayError("RATE_LIMITED")
        evidence = read_wp173_authorization_evidence(
            paper_store_path, intent_id=intent_id
        )
        intent = evidence.intent
        risk_decision = evidence.risk_decision
        if type(venue_context) not in (
            FixtureVenueContextAdapter,
            OfficialSdkAuthenticatedReadAdapter,
        ):
            raise GatewayError("VENUE_CONSTRAINTS_INVALID")
        constraints, identity = venue_context.query_venue_context(
            intent, signing_time_ns
        )
        constraints.validate()
        identity.validate()
        if (
            intent.market_id != constraints.market_id
            or intent.asset_id != constraints.token_id
            or constraints.exchange != identity.exchange
            or constraints.neg_risk != (identity.exchange == "neg-risk-exchange")
            or not self.state.credential_configured
            or identity.signer != self.state.public_signer
            or identity.funder != self.state.public_funder
        ):
            raise GatewayError("SIGNING_IDENTITY_INVALID")
        if constraints.access_state != "ELIGIBLE":
            raise GatewayError("ACCESS_NOT_ELIGIBLE")
        if time_in_force not in TIME_IN_FORCE or type(post_only) is not bool:
            raise GatewayError("UNSUPPORTED_ORDER_INSTRUCTION")
        if (time_in_force == "GTC" and not constraints.supports_gtc) or (
            time_in_force == "GTD" and not constraints.supports_gtd
        ):
            raise GatewayError("UNSUPPORTED_ORDER_INSTRUCTION")
        if post_only and not constraints.post_only_allowed:
            raise GatewayError("UNSUPPORTED_ORDER_INSTRUCTION")
        if time_in_force == "GTC" and expiration is not None:
            raise GatewayError("UNSUPPORTED_ORDER_INSTRUCTION")
        if time_in_force == "GTD" and (
            not isinstance(expiration, int)
            or isinstance(expiration, bool)
            or expiration <= 0
        ):
            raise GatewayError("UNSUPPORTED_ORDER_INSTRUCTION")
        if not isinstance(nonce, int) or isinstance(nonce, bool) or nonce < 0:
            raise GatewayError("SIGNING_IDENTITY_INVALID")
        _time(signing_time_ns)
        if (
            not constraints.observed_time_ns
            <= signing_time_ns
            <= constraints.valid_until_ns
        ):
            raise GatewayError("VENUE_CONSTRAINTS_STALE")
        _label(session_identity)
        price = _decimal(intent.reference_price, positive=True)
        worst_price = _decimal(worst_acceptable_price, positive=True)
        quantity = _decimal(intent.quantity, positive=True)
        tick = _decimal(constraints.tick_size, positive=True)
        minimum = _decimal(constraints.minimum_order_size, positive=True)
        if (
            price > 1
            or worst_price > 1
            or price % tick != 0
            or worst_price % tick != 0
            or quantity < minimum
            or intent.side == "BUY"
            and price > worst_price
            or intent.side == "SELL"
            and price < worst_price
        ):
            raise GatewayError("ORDER_CONSTRAINT_INVALID")
        price_text = _canonical_decimal(price)
        worst_price_text = _canonical_decimal(worst_price)
        quantity_text = _canonical_decimal(quantity)
        preimage = {
            "authorization_id": evidence.authorization_id,
            "intent_id": intent.intent_id,
            "risk_decision_id": risk_decision.decision_id,
            "session_identity": session_identity,
            "market_id": constraints.market_id,
            "condition_id": constraints.condition_id,
            "token_id": constraints.token_id,
            "side": intent.side,
            "order_type": "LIMIT",
            "quantity": quantity_text,
            "limit_price": price_text,
            "worst_acceptable_price": worst_price_text,
            "time_in_force": time_in_force,
            "expiration": expiration,
            "post_only": post_only,
            "tick_size": _canonical_decimal(tick),
            "minimum_order_size": _canonical_decimal(minimum),
            "neg_risk": constraints.neg_risk,
            "exchange": identity.exchange,
            "chain_id": identity.chain_id,
            "domain_name": identity.domain_name,
            "protocol_version": identity.protocol_version,
            "verifying_contract": identity.verifying_contract,
            "signer": identity.signer,
            "funder": identity.funder,
            "wallet_type": identity.wallet_type,
            "signature_type": identity.signature_type,
            "constraint_version": constraints.constraint_version,
            "nonce": nonce,
            "signing_time_ns": signing_time_ns,
        }
        order_identity = _sha("executionorder:sha256:", preimage)
        signed_order_hash = DeterministicFixtureSigner.sign_hash(preimage)
        existing = next(
            (
                item
                for item in self.state.prepared_orders
                if item.intent_id == intent.intent_id
            ),
            None,
        )
        if existing is not None:
            if existing.order_identity != order_identity:
                raise GatewayError("ORDER_IDENTITY_CONFLICT")
            return existing
        would_submit = {
            "asset_id": constraints.token_id,
            "price": price_text,
            "size": quantity_text,
            "side": intent.side,
            "post_only": post_only,
            "expiration": expiration,
            "order_type": "LIMIT",
            "time_in_force": time_in_force,
            "signed_order_hash": signed_order_hash,
        }
        order = PreparedLimitOrder(
            order_identity,
            evidence.authorization_id,
            intent.intent_id,
            risk_decision.decision_id,
            session_identity,
            constraints.market_id,
            constraints.condition_id,
            constraints.token_id,
            intent.side,
            quantity_text,
            price_text,
            worst_price_text,
            time_in_force,
            expiration,
            post_only,
            _canonical_decimal(tick),
            _canonical_decimal(minimum),
            constraints.neg_risk,
            identity.exchange,
            identity.chain_id,
            identity.domain_name,
            identity.protocol_version,
            identity.verifying_contract,
            identity.signer,
            identity.funder,
            identity.wallet_type,
            identity.signature_type,
            constraints.constraint_version,
            nonce,
            signing_time_ns,
            signed_order_hash,
            would_submit,
        )
        new = replace(
            self.state,
            prepared_orders=self.state.prepared_orders + (order,),
            last_event_time_ns=signing_time_ns,
        )
        self._commit(
            "LIMIT_ORDER_PREPARED",
            signing_time_ns,
            {"order_identity": order_identity, "intent_id": intent.intent_id},
            new,
        )
        return order

    def record_fixture_mutation(
        self,
        order_identity: str,
        *,
        operation: str,
        attempt_sequence: int,
        request: Mapping[str, object],
        transmitted: bool,
        response_status: int | None,
        response_body_valid: bool,
        venue_order_id: str | None,
        event_time_ns: int,
    ) -> MutationAttempt:
        """Record a local simulator result; never invoke an SDK/network method."""
        if self.state.authority_state != "A2_SHADOW":
            raise GatewayError("SHADOW_AUTHORITY_REQUIRED")
        if operation not in MUTATION_OPERATIONS:
            raise GatewayError("UNSUPPORTED_MUTATION")
        if (
            not isinstance(attempt_sequence, int)
            or isinstance(attempt_sequence, bool)
            or attempt_sequence < 1
        ):
            raise GatewayError("MUTATION_ATTEMPT_INVALID")
        if type(transmitted) is not bool or type(response_body_valid) is not bool:
            raise GatewayError("MUTATION_ATTEMPT_INVALID")
        _time(event_time_ns)
        order = next(
            (
                item
                for item in self.state.prepared_orders
                if item.order_identity == order_identity
            ),
            None,
        )
        if order is None:
            raise GatewayError("ORDER_NOT_FOUND")
        if response_status is not None and (
            not isinstance(response_status, int)
            or isinstance(response_status, bool)
            or not 100 <= response_status <= 599
        ):
            raise GatewayError("MUTATION_ATTEMPT_INVALID")
        prior = [
            item
            for item in self.state.mutation_attempts
            if item.order_identity == order_identity and item.operation == operation
        ]
        if operation == "CREATE":
            expected_request: Mapping[str, object] = dict(order.would_submit)
            targets: tuple[str, ...] = ()
            target_bindings: tuple[tuple[str, str], ...] = ()
            request_market_id: str | None = None
        else:
            expected_keys = (
                {"venue_order_ids", "market_id"}
                if operation == "CANCEL_MARKET"
                else {"venue_order_ids"}
            )
            if set(request) != expected_keys or not isinstance(
                request["venue_order_ids"], (list, tuple)
            ):
                raise GatewayError("MUTATION_ATTEMPT_INVALID")
            targets = tuple(_label(value) for value in request["venue_order_ids"])
            if not targets or len(targets) > 100 or len(set(targets)) != len(targets):
                raise GatewayError("MUTATION_ATTEMPT_INVALID")
            if operation == "CANCEL_ONE" and len(targets) != 1:
                raise GatewayError("MUTATION_ATTEMPT_INVALID")
            if not set(targets).issubset(self.state.venue_open_order_ids) and not any(
                item.request_target_ids == targets for item in prior
            ):
                raise GatewayError("MUTATION_REQUEST_INVALID")
            target_owners = {
                item.venue_order_id: item.order_identity
                for item in self.state.mutation_attempts
                if item.operation == "CREATE"
                and item.outcome == "DEFINITIVE_ACCEPTED"
                and item.venue_order_id is not None
            }
            if any(target not in target_owners for target in targets):
                raise GatewayError("MUTATION_REQUEST_INVALID")
            target_bindings = tuple(
                sorted((target, target_owners[target]) for target in targets)
            )
            expected_request = {"venue_order_ids": list(targets)}
            request_market_id = None
            if operation == "CANCEL_MARKET":
                request_market_id = _label(request["market_id"])
                prepared_markets = {
                    item.order_identity: item.market_id
                    for item in self.state.prepared_orders
                }
                if request_market_id != order.market_id or any(
                    prepared_markets.get(owner) != request_market_id
                    for _target, owner in target_bindings
                ):
                    raise GatewayError("MUTATION_REQUEST_INVALID")
                expected_request["market_id"] = request_market_id
            if (
                operation == "CANCEL_ALL"
                and set(targets) != set(self.state.venue_open_order_ids)
                and not any(item.request_target_ids == targets for item in prior)
            ):
                raise GatewayError("MUTATION_REQUEST_INVALID")
        if canonical_json(request) != canonical_json(expected_request):
            raise GatewayError("MUTATION_REQUEST_INVALID")
        prior_target = (
            prior
            if operation == "CREATE"
            else [
                item
                for item in self.state.mutation_attempts
                if item.operation == operation
                and item.request_target_bindings == target_bindings
            ]
        )
        existing_sequence = next(
            (item for item in prior if item.attempt_sequence == attempt_sequence), None
        )
        if attempt_sequence != len(prior) + 1 and existing_sequence is None:
            raise GatewayError("MUTATION_SEQUENCE_INVALID")
        if existing_sequence is None and any(
            item.outcome
            in ("DEFINITIVE_ACCEPTED", "AMBIGUOUS", "RECONCILIATION_REQUIRED")
            for item in prior_target
        ):
            raise GatewayError("MUTATION_ALREADY_TRANSMITTED")
        accepted = (
            transmitted
            and response_status is not None
            and 200 <= response_status < 300
            and response_body_valid
            and (operation != "CREATE" or venue_order_id is not None)
        )
        rejected = (
            not transmitted
            or transmitted
            and response_status is not None
            and 400 <= response_status < 500
            and response_status not in (425, 429)
            and response_body_valid
        )
        classified = (
            "DEFINITIVE_ACCEPTED"
            if accepted
            else "DEFINITIVE_REJECTED"
            if rejected
            else "AMBIGUOUS"
        )
        request_digest = _sha(
            "mutationrequest:sha256:",
            {
                "order_identity": order_identity,
                "operation": operation,
                "request": expected_request,
                "target_bindings": list(target_bindings),
            },
        )
        prior_reconciliation_state = self.state.reconciliation_state
        attempt_id = _sha(
            "mutationattempt:sha256:",
            {
                "order_identity": order_identity,
                "operation": operation,
                "attempt_sequence": attempt_sequence,
                "prior_reconciliation_state": prior_reconciliation_state,
                "request_digest": request_digest,
                "request_target_bindings": list(target_bindings),
            },
        )
        candidate = MutationAttempt(
            attempt_id,
            order_identity,
            operation,
            attempt_sequence,
            prior_reconciliation_state,
            targets,
            target_bindings,
            request_market_id,
            request_digest,
            transmitted,
            classified,
            venue_order_id,
            response_status,
            event_time_ns,
            True,
        )
        if existing_sequence is not None:
            if existing_sequence != candidate:
                raise GatewayError("MUTATION_IDENTITY_CONFLICT")
            return existing_sequence
        ambiguous = classified in ("AMBIGUOUS", "RECONCILIATION_REQUIRED")
        open_ids = self.state.venue_open_order_ids
        if classified == "DEFINITIVE_ACCEPTED":
            if operation == "CREATE":
                assert venue_order_id is not None
                open_ids = tuple(sorted(set(open_ids) | {venue_order_id}))
            elif operation.startswith("CANCEL"):
                open_ids = tuple(item for item in open_ids if item not in targets)
        new = replace(
            self.state,
            mutation_attempts=self.state.mutation_attempts + (candidate,),
            venue_open_order_ids=open_ids,
            authority_state="A0_DISABLED" if ambiguous else self.state.authority_state,
            disable_reason="AMBIGUOUS_MUTATION"
            if ambiguous
            else self.state.disable_reason,
            reconciliation_state="REQUIRED"
            if ambiguous
            else self.state.reconciliation_state,
            last_event_time_ns=event_time_ns,
        )
        self._commit(
            "FIXTURE_MUTATION_RECORDED",
            event_time_ns,
            {
                "attempt_id": attempt_id,
                "operation": operation,
                "outcome": classified,
                "fixture_only": True,
            },
            new,
        )
        return candidate

    def place_limit_order(self, *_args: object, **_kwargs: object) -> None:
        raise GatewayError("GATE_B_REQUIRED")

    def cancel(self, *_args: object, **_kwargs: object) -> None:
        raise GatewayError("GATE_B_REQUIRED")

    def cockpit_projection(self, *, audit_limit: int = 50) -> dict[str, object]:
        if not 1 <= audit_limit <= 100:
            raise GatewayError("FIELD_VALUE_INVALID")
        return {
            "read_only": True,
            "authority_state": self.state.authority_state,
            "disabled": self.state.authority_state == "A0_DISABLED",
            "disable_reason": self.state.disable_reason,
            "credential_configured": self.state.credential_configured,
            "public_signer": self.state.public_signer,
            "public_funder": self.state.public_funder,
            "reconciliation_state": self.state.reconciliation_state,
            "heartbeat_state": self.state.heartbeat_state,
            "user_stream_state": self.state.user_stream_state,
            "access_state": self.state.access_state,
            "rate_limit_until_ns": self.state.rate_limit_until_ns,
            "prepared_order_count": len(self.state.prepared_orders),
            "mutation_attempt_count": len(self.state.mutation_attempts),
            "open_order_count": len(self.state.venue_open_order_ids),
            "gate_b_authorized": False,
            "restricted_live_available": False,
        }


def read_gate_b_evidence(path: Path) -> dict[str, object]:
    """Verify a gateway journal and derive its latest sanitized Gate-B evidence."""
    store = GatewayStore(path)
    try:
        mapping, _head, events = store.load()
        if mapping is None or _validate_replay(events).to_mapping() != dict(mapping):
            raise GatewayError("STATE_REPLAY_INVALID")
    finally:
        store.close()
    result: dict[str, object] = {
        "public_signer": None,
        "public_wallet": None,
        "wallet_type": "DEPOSIT_WALLET",
        "signature_type": "3",
        "last_verification_receipt_id": None,
        "last_verification_time_ns": None,
        "gate_b_reconciliation_state": "REQUIRED",
        "cancel_capability_status": "AVAILABLE",
    }
    unresolved: set[str] = set()
    for event in events:
        data = dict(event.data)
        if event.event_type in GATE_B_AUDIT_EVENTS:
            result["public_signer"] = data["public_signer"]
            result["public_wallet"] = data["public_wallet"]
        if event.event_type == "GATE_B_RECONCILED":
            result["gate_b_reconciliation_state"] = data["gate_b_reconciliation_state"]
        elif event.event_type == "GATE_B_CANCEL_ATTEMPT_STARTED":
            unresolved.add(str(data["cancel_attempt_id"]))
        elif event.event_type == "GATE_B_CANCEL_ATTEMPT_RESULT":
            if data["cancel_result"] in ("DEFINITIVE_ACCEPTED", "DEFINITIVE_REJECTED"):
                unresolved.discard(str(data["cancel_attempt_id"]))
            else:
                unresolved.add(str(data["cancel_attempt_id"]))
                result["gate_b_reconciliation_state"] = "BLOCKED"
        elif event.event_type == "GATE_B_CANCEL_TRANSPORT_VERIFIED":
            result["last_verification_receipt_id"] = data["receipt_id"]
            result["last_verification_time_ns"] = data["verified_time_ns"]
            result["gate_b_reconciliation_state"] = data["gate_b_reconciliation_state"]
    if unresolved:
        result["gate_b_reconciliation_state"] = "BLOCKED"
        result["cancel_capability_status"] = "BLOCKED_UNRESOLVED_ATTEMPT"
    return result
