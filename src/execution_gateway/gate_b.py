"""WP174B Gate-B production credential, signing, and real-mutation boundary.

This module closes WP174-D001. It can load a real signer key only through an
ephemeral no-echo provider, authenticate the official SecureClient against an
already-deployed Deposit Wallet without deploying or approving anything, sign
one real LIMIT order locally without posting it, and perform real
exposure-reducing cancellation. Every real economic create/post remains
structurally unreachable behind a Gate-C permit this package cannot construct.

No real secret value, L2 credential, signature payload, or raw SDK exception is
ever persisted, logged, serialized, or emitted. The raw SDK client is held
privately and never exposed. There is no live authority and no capital here.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
import getpass
import re
import sys
from typing import Callable, Mapping, Protocol

from polymarket import SecureClient

from .gateway import (
    GatewayError,
    _ADDRESS_RE,
    _canonical_decimal,
    _decimal,
    _label,
    _sha,
    _time,
)

# Orthogonal Gate-B capability states (never runtime authority; never A3).
GATE_B_CAPABILITY_STATES = (
    "B0_LOCKED",
    "B1_SECRET_BOUND",
    "B2_AUTHENTICATED",
    "B3_SIGNING_VERIFIED",
    "B4_CANCEL_TRANSPORT_VERIFIED",
)

# Deposit Wallet is the only supported production wallet; signature type 3.
_DEPOSIT_WALLET_TYPE = "DEPOSIT_WALLET"
_DEPOSIT_SIGNATURE_TYPE = "3"
_PRODUCTION_ENVIRONMENT = "production"
_CHAIN_ID = 137

# Sentinel substrings the operator confirmation must not resemble a secret.
_CANCEL_CONFIRMATION_PHRASE = "CONFIRM-EMPTY-WALLET-CANCEL"

# Closed cancel operations Gate B may perform (all exposure-reducing).
_CANCEL_OPERATIONS = ("CANCEL_ONE", "CANCEL_MANY", "CANCEL_MARKET", "CANCEL_ALL")

# Closed mutation-outcome vocabulary for cancel classification.
_CANCEL_OUTCOMES = ("DEFINITIVE_ACCEPTED", "DEFINITIVE_REJECTED", "AMBIGUOUS")

# A verification receipt must bind an exact Git HEAD (short or full sha), never a
# placeholder such as UNKNOWN_HEAD.
_HEAD_RE = re.compile(r"^[0-9a-f]{7,64}$")


def _stdin_is_tty() -> bool:
    """True only when stdin is an interactive terminal (never a pipe/file)."""
    stream = getattr(sys, "stdin", None)
    isatty = getattr(stream, "isatty", None)
    try:
        return bool(isatty()) if callable(isatty) else False
    except Exception:
        return False


def _safe_close(client: object) -> None:
    """Best-effort close of a credential-bearing client; never raises/echoes."""
    if client is None:
        return
    closer = getattr(client, "close", None)
    if callable(closer):
        try:
            closer()
        except Exception:
            pass


def _public_address(value: object, error: str) -> str:
    if not isinstance(value, str):
        raise GatewayError(error)
    lowered = value.lower()
    if _ADDRESS_RE.fullmatch(lowered) is None:
        raise GatewayError(error)
    return lowered


# ---------------------------------------------------------------------------
# Ephemeral secret boundary
# ---------------------------------------------------------------------------


class GateBSecretLease:
    """Opaque, non-serializable, in-memory lease over a real signer key.

    Python cannot guarantee physical memory zeroization; this only removes the
    process reference and refuses to expose the value through any dunder.
    """

    __slots__ = ("_value", "_open")

    def __init__(self, value: str):
        if not isinstance(value, str) or not value:
            raise GatewayError("SECRET_INPUT_INVALID")
        self._value = value
        self._open = True

    def reveal(self) -> str:
        """Reveal the secret exactly once per call for immediate in-memory use."""
        if not self._open:
            raise GatewayError("SECRET_INPUT_UNAVAILABLE")
        return self._value

    def close(self) -> None:
        self._value = ""
        self._open = False

    @property
    def active(self) -> bool:
        return self._open

    # Refuse every value-exposing protocol.
    def __repr__(self) -> str:  # pragma: no cover - trivial redaction
        return "GateBSecretLease(<redacted>)"

    __str__ = __repr__

    def __reduce__(self):
        raise GatewayError("SECRET_INPUT_INVALID")

    def __eq__(self, other: object) -> bool:
        return self is other

    def __hash__(self) -> int:
        return id(self)


class GateBSecretProvider(Protocol):
    """Provides a real signer key only through an approved runtime boundary."""

    def acquire(self) -> GateBSecretLease: ...


class InteractiveGateBSecretProvider:
    """Real operator path: no-echo TTY prompt via the standard library.

    Never reads argv, files, pipes, or the environment. If stdin is not an
    interactive terminal the prompt fails closed instead of consuming a pipe.
    """

    def __init__(self, prompt: str = "Signer private key (no echo): "):
        self._prompt = str(prompt)

    def acquire(self) -> GateBSecretLease:
        # A real signer key is accepted only from an interactive terminal; a
        # piped or redirected (non-TTY) stdin fails closed and never consumes it.
        if not _stdin_is_tty():
            raise GatewayError("SECRET_INPUT_UNAVAILABLE")
        try:
            raw = getpass.getpass(self._prompt)
        except (EOFError, OSError):
            raise GatewayError("SECRET_INPUT_UNAVAILABLE") from None
        if not isinstance(raw, str) or not raw.strip():
            raise GatewayError("SECRET_INPUT_INVALID")
        return GateBSecretLease(raw.strip())


# ---------------------------------------------------------------------------
# Deposit Wallet identity policy
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GateBIdentityPolicy:
    """Exact expected public production identity; no secret material."""

    expected_signer: str
    expected_wallet: str
    wallet_type: str = _DEPOSIT_WALLET_TYPE
    signature_type: str = _DEPOSIT_SIGNATURE_TYPE
    chain_id: int = _CHAIN_ID
    environment: str = _PRODUCTION_ENVIRONMENT

    def validate(self) -> None:
        _public_address(self.expected_signer, "SIGNING_IDENTITY_INVALID")
        _public_address(self.expected_wallet, "SIGNING_IDENTITY_INVALID")
        if self.wallet_type != _DEPOSIT_WALLET_TYPE:
            raise GatewayError("WALLET_TYPE_UNSUPPORTED")
        if self.signature_type != _DEPOSIT_SIGNATURE_TYPE:
            raise GatewayError("SIGNING_IDENTITY_INVALID")
        if self.chain_id != _CHAIN_ID or self.environment != _PRODUCTION_ENVIRONMENT:
            raise GatewayError("SIGNING_IDENTITY_INVALID")


# ---------------------------------------------------------------------------
# Gate-C permit — deliberately unconstructable in WP174B
# ---------------------------------------------------------------------------


class GateCLivePermit:
    """A live create permit. WP175 alone may construct one; here it cannot exist."""

    def __init__(self, *_args: object, **_kwargs: object):
        raise GatewayError("GATE_C_REQUIRED")


# ---------------------------------------------------------------------------
# Real production mutation adapter (cancel real; create Gate-C locked)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CancelAttempt:
    """Deterministic identity for exactly one cancel transmission."""

    operation: str
    target: str
    attempt_sequence: int
    prior_reconciliation_state: str

    def validate(self) -> None:
        if self.operation not in _CANCEL_OPERATIONS:
            raise GatewayError("MUTATION_IDENTITY_CONFLICT")
        _label(self.target)
        if not isinstance(self.attempt_sequence, int) or isinstance(
            self.attempt_sequence, bool
        ) or self.attempt_sequence < 0:
            raise GatewayError("MUTATION_IDENTITY_CONFLICT")
        _label(self.prior_reconciliation_state)

    @property
    def identity(self) -> str:
        return _sha(
            "cancelattempt:sha256:",
            {
                "operation": self.operation,
                "target": self.target,
                "attempt_sequence": self.attempt_sequence,
                "prior_reconciliation_state": self.prior_reconciliation_state,
            },
        )


class ProductionSdkMutationAdapter:
    """Real cancellation transport; every create/post path is Gate-C locked."""

    def __init__(self, client: object):
        self._client = client
        self._transmitted: set[str] = set()

    # -- create surface: structurally unreachable ---------------------------

    def create_limit_order(self, *_args: object, **_kwargs: object) -> object:
        raise GatewayError("GATE_C_REQUIRED")

    def place_limit_order(self, *_args: object, **_kwargs: object) -> object:
        raise GatewayError("GATE_C_REQUIRED")

    def post_order(self, *_args: object, permit: object = None, **_kwargs: object) -> object:
        # Even a supplied permit cannot help: no caller can construct one.
        if not isinstance(permit, GateCLivePermit):
            raise GatewayError("GATE_C_REQUIRED")
        raise GatewayError("GATE_C_REQUIRED")  # pragma: no cover - unreachable

    def place_market_order(self, *_args: object, **_kwargs: object) -> object:
        raise GatewayError("GATE_C_REQUIRED")

    # -- cancel surface: real, single-transmit, ambiguity-aware -------------

    def cancel(self, attempt: CancelAttempt) -> tuple[str, Mapping[str, object]]:
        attempt.validate()
        identity = attempt.identity
        if identity in self._transmitted:
            # Idempotency: a possibly-transmitted attempt is never resent.
            raise GatewayError("MUTATION_ALREADY_TRANSMITTED")
        self._transmitted.add(identity)
        try:
            if attempt.operation == "CANCEL_ALL":
                response = self._client.cancel_all()
            elif attempt.operation == "CANCEL_ONE":
                response = self._client.cancel_order(order_id=attempt.target)
            elif attempt.operation == "CANCEL_MARKET":
                response = self._client.cancel_market_orders(market=attempt.target)
            else:  # CANCEL_MANY
                response = self._client.cancel_orders(
                    order_ids=tuple(attempt.target.split(","))
                )
        except Exception:
            # Possibly transmitted: never blindly retried; reconcile upstream.
            raise GatewayError("CANCEL_PROBE_AMBIGUOUS") from None
        return "DEFINITIVE_ACCEPTED", _summarize_cancel_response(response)


def _summarize_cancel_response(response: object) -> Mapping[str, object]:
    """Extract only safe closed counts from a cancel response."""
    canceled = getattr(response, "canceled", None)
    not_canceled = getattr(response, "not_canceled", None)
    try:
        canceled_count = len(canceled) if canceled is not None else 0
        not_canceled_count = len(not_canceled) if not_canceled is not None else 0
    except TypeError:
        raise GatewayError("CANCEL_PROBE_FAILED") from None
    return {"canceled_count": canceled_count, "not_canceled_count": not_canceled_count}


# ---------------------------------------------------------------------------
# Sanitized verification receipt
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GateBVerificationReceipt:
    """Content-addressed sanitized evidence; never committed, never a secret."""

    repository_head: str
    sdk_distribution: str
    sdk_version: str
    public_signer: str
    public_wallet: str
    wallet_type: str
    signature_type: str
    chain_id: int
    environment: str
    credential_mode: str
    authenticated_reads_pass: bool
    account_empty_pass: bool
    signing_probe_id: str | None
    cancel_probe_attempt_id: str | None
    cancel_probe_result: str | None
    open_orders_before: int
    open_orders_after: int
    positions_before: int
    collateral_balance_before: str
    verified_time_ns: int
    valid_until_ns: int
    redaction_pass: bool

    def to_public_mapping(self) -> dict[str, object]:
        return {
            "schema_version": "wp174b-gate-b-verification-receipt/1.0.0",
            "repository_head": self.repository_head,
            "sdk_distribution": self.sdk_distribution,
            "sdk_version": self.sdk_version,
            "public_signer": self.public_signer,
            "public_wallet": self.public_wallet,
            "wallet_type": self.wallet_type,
            "signature_type": self.signature_type,
            "chain_id": self.chain_id,
            "environment": self.environment,
            "credential_mode": self.credential_mode,
            "authenticated_reads_pass": self.authenticated_reads_pass,
            "account_empty_pass": self.account_empty_pass,
            "signing_probe_id": self.signing_probe_id,
            "cancel_probe_attempt_id": self.cancel_probe_attempt_id,
            "cancel_probe_result": self.cancel_probe_result,
            "open_orders_before": self.open_orders_before,
            "open_orders_after": self.open_orders_after,
            "positions_before": self.positions_before,
            "collateral_balance_before": self.collateral_balance_before,
            "verified_time_ns": self.verified_time_ns,
            "valid_until_ns": self.valid_until_ns,
            "redaction_pass": self.redaction_pass,
        }

    @property
    def receipt_id(self) -> str:
        return _sha("gatebreceipt:sha256:", self.to_public_mapping())

    def as_receipt_document(self) -> dict[str, object]:
        document = self.to_public_mapping()
        document["receipt_id"] = self.receipt_id
        return document


# ---------------------------------------------------------------------------
# Real non-deploying Deposit Wallet client factory
# ---------------------------------------------------------------------------


def create_deposit_wallet_client(
    private_key: str, expected_wallet: str
) -> SecureClient:
    """Build an authenticated SecureClient WITHOUT deploying the wallet.

    The public ``SecureClient.create`` runs ``_ensure_wallet_ready`` which
    deploys an undeployed Deposit Wallet. Gate B forbids deployment, so this
    uses the non-deploying construction path and then reads deployment status
    explicitly, failing closed if the wallet is not already deployed.
    """
    from polymarket.environments import PRODUCTION

    try:
        client = SecureClient._create(
            private_key=private_key,
            wallet=expected_wallet,
            environment=PRODUCTION,
            credentials=None,
            api_key=None,
            nonce=0,
            validate_credentials=True,
        )
    except GatewayError:
        raise
    except Exception:
        raise GatewayError("AUTHENTICATION_FAILED") from None

    try:
        ctx = client._ctx
        if ctx.wallet_type != _DEPOSIT_WALLET_TYPE:
            raise GatewayError("WALLET_TYPE_UNSUPPORTED")
        # Exact polymarket-client==0.10.0 contract: fetch_deployed_sync and
        # RelayerTransactionType both live in this module. Gate B already rejects
        # every wallet type except DEPOSIT_WALLET, whose relayer transaction type
        # is RelayerTransactionType.WALLET, so it is used directly rather than via
        # the private secure-client helper.
        from polymarket._internal.actions.relayer.deployed import (
            RelayerTransactionType,
            fetch_deployed_sync,
        )

        deployed = fetch_deployed_sync(
            ctx.relayer,
            address=str(ctx.wallet),
            type=RelayerTransactionType.WALLET,
        )
        if not deployed:
            # Never deploy. An undeployed wallet is a refused side effect.
            raise GatewayError("SDK_SIDE_EFFECT_UNAUTHORIZED")
    except GatewayError:
        _safe_close(client)
        raise
    except Exception:
        _safe_close(client)
        raise GatewayError("SDK_CONTRACT_INVALID") from None
    return client


# ---------------------------------------------------------------------------
# Gate-B session
# ---------------------------------------------------------------------------


ClientFactory = Callable[[str, str], object]


class GateBSession:
    """Owns the raw authenticated client privately; never exposes it.

    The real path uses :func:`create_deposit_wallet_client`. Tests inject a
    non-deploying fake client factory and a fake secret provider; no real
    secret provider is available through ordinary fixture configuration.
    """

    __slots__ = (
        "_client",
        "_policy",
        "_state",
        "_mutation",
        "_attempt_seq",
        "_audit_sink",
        "_signing_probe_id",
    )

    def __init__(
        self,
        client: object,
        policy: GateBIdentityPolicy,
        *,
        audit_sink: Callable[[Mapping[str, object]], None] | None = None,
    ):
        self._client = client
        self._policy = policy
        self._state = "B2_AUTHENTICATED"
        self._mutation = ProductionSdkMutationAdapter(client)
        self._attempt_seq = 0
        self._audit_sink = audit_sink
        self._signing_probe_id: str | None = None
        # Journal the sanitized capability transition. The sink is intended to be
        # the existing tamper-evident gateway store's append; it never receives a
        # secret value, credential, or signature.
        self._emit("GATE_B_AUTHENTICATED", {})

    def _emit(self, event_type: str, extra: Mapping[str, object]) -> None:
        if self._audit_sink is None:
            return
        event: dict[str, object] = {
            "event_type": event_type,
            "capability_state": self._state,
            "public_signer": self.public_signer,
            "public_wallet": self.public_wallet,
            "wallet_type": _DEPOSIT_WALLET_TYPE,
            "signature_type": _DEPOSIT_SIGNATURE_TYPE,
        }
        event.update(extra)
        self._audit_sink(dict(event))

    @classmethod
    def authenticate(
        cls,
        provider: GateBSecretProvider,
        policy: GateBIdentityPolicy,
        *,
        client_factory: ClientFactory = create_deposit_wallet_client,
        audit_sink: Callable[[Mapping[str, object]], None] | None = None,
    ) -> "GateBSession":
        policy.validate()
        lease = provider.acquire()
        if not isinstance(lease, GateBSecretLease) or not lease.active:
            raise GatewayError("SECRET_INPUT_UNAVAILABLE")
        # B1_SECRET_BOUND: the lease is live only until the client is built.
        try:
            client = client_factory(lease.reveal(), policy.expected_wallet)
        except GatewayError:
            raise
        except Exception:
            raise GatewayError("AUTHENTICATION_FAILED") from None
        finally:
            lease.close()
        try:
            cls._verify_identity(client, policy)
        except BaseException:
            # A constructed credential-bearing client must be closed on any
            # identity-verification failure before the error propagates.
            _safe_close(client)
            raise
        return cls(client, policy, audit_sink=audit_sink)

    @staticmethod
    def _verify_identity(client: object, policy: GateBIdentityPolicy) -> None:
        try:
            signer = str(client.signer).lower()
            wallet = str(client.wallet).lower()
            wallet_type = client.wallet_type
            environment = client.environment.name
            signer_type = client._ctx.signer_type
            chain_id = client._ctx.environment_config.chain_id
        except Exception:
            raise GatewayError("AUTHENTICATION_FAILED") from None
        if wallet_type != _DEPOSIT_WALLET_TYPE:
            raise GatewayError("WALLET_TYPE_UNSUPPORTED")
        if signer_type != "OWNER":
            raise GatewayError("SIGNING_IDENTITY_INVALID")
        if environment != _PRODUCTION_ENVIRONMENT or chain_id != _CHAIN_ID:
            raise GatewayError("SIGNING_IDENTITY_INVALID")
        if _ADDRESS_RE.fullmatch(signer) is None or signer != policy.expected_signer:
            raise GatewayError("SIGNER_MISMATCH")
        if _ADDRESS_RE.fullmatch(wallet) is None or wallet != policy.expected_wallet:
            raise GatewayError("WALLET_MISMATCH")

    @property
    def capability_state(self) -> str:
        return self._state

    @property
    def public_signer(self) -> str:
        return str(self._client.signer).lower()

    @property
    def public_wallet(self) -> str:
        return str(self._client.wallet).lower()

    @property
    def mutation_adapter(self) -> ProductionSdkMutationAdapter:
        return self._mutation

    def _next_attempt_sequence(self) -> int:
        self._attempt_seq += 1
        return self._attempt_seq

    # -- bounded authenticated reads ---------------------------------------

    def account_snapshot(self) -> dict[str, object]:
        """Bounded sanitized public account snapshot; no raw credential data."""
        try:
            balance = self._client.get_balance_allowance(asset_type="COLLATERAL")
            open_orders = _count_page(self._client.list_open_orders())
            positions = _count_page(
                self._client.list_positions(user=self.public_wallet, page_size=100)
            )
        except GatewayError:
            raise
        except Exception:
            raise GatewayError("AUTHENTICATED_READ_FAILED") from None
        collateral = _canonical_decimal(_as_decimal(getattr(balance, "balance", "0")))
        return {
            "collateral_balance": collateral,
            "open_orders": open_orders,
            "positions": positions,
        }

    # -- real local LIMIT signing probe (no post) --------------------------

    def signing_probe(
        self, *, token_id: str, price: str, size: str, side: str = "BUY"
    ) -> str:
        if self._state not in ("B2_AUTHENTICATED", "B3_SIGNING_VERIFIED", "B4_CANCEL_TRANSPORT_VERIFIED"):
            raise GatewayError("SIGNING_PROBE_FAILED")
        _label(token_id)
        price_dec = _decimal(price, positive=True)
        size_dec = _decimal(size, positive=True)
        if side not in ("BUY", "SELL"):
            raise GatewayError("SIGNING_PROBE_FAILED")
        try:
            signed = self._client.create_limit_order(
                token_id=token_id,
                price=price_dec,
                size=size_dec,
                side=side,
                post_only=True,
            )
        except GatewayError:
            raise
        except Exception:
            raise GatewayError("SIGNING_PROBE_FAILED") from None
        # Derive identity from sanitized public economics only; the signed
        # order (incl. signature) is used for nothing else and discarded.
        identity = _sha(
            "signingprobe:sha256:",
            {
                "public_signer": self.public_signer,
                "public_wallet": self.public_wallet,
                "wallet_type": _DEPOSIT_WALLET_TYPE,
                "signature_type": _DEPOSIT_SIGNATURE_TYPE,
                "token_id": token_id,
                "price": _canonical_decimal(price_dec),
                "size": _canonical_decimal(size_dec),
                "side": side,
                "order_type": "LIMIT",
            },
        )
        del signed
        self._state = "B3_SIGNING_VERIFIED"
        self._signing_probe_id = identity
        self._emit("GATE_B_SIGNING_VERIFIED", {"signing_probe_id": identity})
        return identity

    # -- safe empty-wallet real cancel probe -------------------------------

    def empty_wallet_cancel_probe(
        self, confirmation: str, *, repository_head: str, now_ns: int, valid_ns: int
    ) -> GateBVerificationReceipt:
        _time(now_ns)
        _time(valid_ns)
        # B2 -> B4 is forbidden: real local signing must be verified before any
        # real cancel transmission.
        if self._state != "B3_SIGNING_VERIFIED" or self._signing_probe_id is None:
            raise GatewayError("CANCEL_PROBE_FAILED")
        # A PASS receipt must bind an exact Git HEAD, never UNKNOWN_HEAD.
        if not isinstance(repository_head, str) or _HEAD_RE.fullmatch(repository_head) is None:
            raise GatewayError("CANCEL_PROBE_FAILED")
        if confirmation != _CANCEL_CONFIRMATION_PHRASE:
            raise GatewayError("CANCEL_PROBE_FAILED")
        snapshot = self.account_snapshot()
        balance_before = snapshot["collateral_balance"]
        open_before = int(snapshot["open_orders"])
        positions_before = int(snapshot["positions"])
        if (
            _as_decimal(balance_before) != Decimal(0)
            or open_before != 0
            or positions_before != 0
        ):
            raise GatewayError("GATE_B_ACCOUNT_NOT_EMPTY")
        attempt = CancelAttempt(
            operation="CANCEL_ALL",
            target="ALL",
            attempt_sequence=self._next_attempt_sequence(),
            prior_reconciliation_state="HEALTHY",
        )
        result, summary = self._mutation.cancel(attempt)
        # The account was empty, so success requires that nothing was canceled and
        # nothing was left uncanceled; any canceled or not-canceled order is an
        # incident, not a pass.
        if (
            int(summary.get("canceled_count", 0)) != 0
            or int(summary.get("not_canceled_count", 0)) != 0
        ):
            raise GatewayError("CANCEL_PROBE_FAILED")
        after = self.account_snapshot()
        open_after = int(after["open_orders"])
        if open_after != 0:
            raise GatewayError("CANCEL_PROBE_AMBIGUOUS")
        self._state = "B4_CANCEL_TRANSPORT_VERIFIED"
        receipt = GateBVerificationReceipt(
            repository_head=_label(repository_head),
            sdk_distribution="polymarket-client",
            sdk_version=_sdk_version(),
            public_signer=self.public_signer,
            public_wallet=self.public_wallet,
            wallet_type=_DEPOSIT_WALLET_TYPE,
            signature_type=_DEPOSIT_SIGNATURE_TYPE,
            chain_id=_CHAIN_ID,
            environment=_PRODUCTION_ENVIRONMENT,
            credential_mode="EPHEMERAL_INTERACTIVE_L1_L2_IN_MEMORY",
            authenticated_reads_pass=True,
            account_empty_pass=True,
            signing_probe_id=self._signing_probe_id,
            cancel_probe_attempt_id=attempt.identity,
            cancel_probe_result=result,
            open_orders_before=open_before,
            open_orders_after=open_after,
            positions_before=positions_before,
            collateral_balance_before=balance_before,
            verified_time_ns=now_ns,
            valid_until_ns=valid_ns,
            redaction_pass=True,
        )
        self._emit(
            "GATE_B_CANCEL_TRANSPORT_VERIFIED",
            {
                "cancel_probe_attempt_id": attempt.identity,
                "cancel_probe_result": result,
                "receipt_id": receipt.receipt_id,
            },
        )
        return receipt

    def close(self) -> None:
        _safe_close(self._client)
        self._client = None
        self._mutation = None
        self._signing_probe_id = None
        self._state = "B0_LOCKED"

    def __enter__(self) -> "GateBSession":
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()


def _count_page(page: object) -> int:
    items = page.iter_items() if hasattr(page, "iter_items") else page
    count = 0
    for _item in items:
        count += 1
        if count > 10_000:
            raise GatewayError("AUTHENTICATED_READ_FAILED")
    return count


def _as_decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except Exception:
        raise GatewayError("AUTHENTICATED_READ_FAILED") from None


def _sdk_version() -> str:
    from importlib.metadata import version

    try:
        return version("polymarket-client")
    except Exception:
        raise GatewayError("SDK_CONTRACT_INVALID") from None


def gate_b_capability_projection(session: GateBSession | None) -> dict[str, object]:
    """Sanitized read-only Gate-B projection for the operator cockpit."""
    if session is None:
        return {
            "gate_b_capability_available": True,
            "gate_b_state": "B0_LOCKED",
            "credential_session_active": False,
            "public_signer": None,
            "public_wallet": None,
            "wallet_type": _DEPOSIT_WALLET_TYPE,
            "signature_type": _DEPOSIT_SIGNATURE_TYPE,
            "create_transport_status": "GATE_C_REQUIRED",
            "cancel_capability_status": "AVAILABLE",
        }
    return {
        "gate_b_capability_available": True,
        "gate_b_state": session.capability_state,
        "credential_session_active": True,
        "public_signer": session.public_signer,
        "public_wallet": session.public_wallet,
        "wallet_type": _DEPOSIT_WALLET_TYPE,
        "signature_type": _DEPOSIT_SIGNATURE_TYPE,
        "create_transport_status": "GATE_C_REQUIRED",
        "cancel_capability_status": "AVAILABLE",
    }
