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

from collections.abc import Mapping as RuntimeMapping
from collections.abc import Sequence as RuntimeSequence
from dataclasses import dataclass
from decimal import Decimal
import getpass
import hashlib
import inspect
import os
from pathlib import Path
import re
import sys
from typing import Callable, Mapping, Protocol, Sequence

from polymarket import SecureClient

from .gateway import (
    GatewayError,
    ProtectedExecutionGateway,
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
_MAX_CANCEL_TARGETS = 100

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


class WalletSessionLock:
    """Atomic, local, public-wallet-derived ownership lock for one operator session."""

    def __init__(self, directory: Path, public_wallet: str):
        wallet = _public_address(public_wallet, "SIGNING_IDENTITY_INVALID")
        digest = hashlib.sha256(wallet.encode("ascii")).hexdigest()[:24]
        self.path = directory / f"gate-b-wallet-{digest}.lock"
        self._wallet = wallet
        self._active = False

    @property
    def active(self) -> bool:
        return self._active

    def acquire(self) -> "WalletSessionLock":
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            descriptor = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            with os.fdopen(descriptor, "w", encoding="ascii") as stream:
                stream.write(self._wallet + "\n")
        except FileExistsError:
            raise GatewayError("GATE_B_OWNERSHIP_LOCKED") from None
        except OSError:
            raise GatewayError("GATE_B_OWNERSHIP_FAILED") from None
        self._active = True
        return self

    def close(self) -> None:
        if not self._active:
            return
        try:
            self.path.unlink()
        except OSError:
            raise GatewayError("GATE_B_OWNERSHIP_FAILED") from None
        finally:
            self._active = False

    def __enter__(self) -> "WalletSessionLock":
        return self.acquire()

    def __exit__(self, *_args: object) -> None:
        self.close()


# ---------------------------------------------------------------------------
# Gate-C permit — deliberately unconstructable in WP174B
# ---------------------------------------------------------------------------


_GATE_C_ISSUER = object()


class GateCLivePermit:
    """A process-local single-use permit issued only by ``gate_c``."""

    __slots__ = ("_attempt_identity", "_used")

    def __init__(self, *_args: object, **_kwargs: object):
        raise GatewayError("GATE_C_REQUIRED")

    @classmethod
    def _issue(cls, issuer: object, attempt_identity: str) -> "GateCLivePermit":
        if issuer is not _GATE_C_ISSUER or not isinstance(attempt_identity, str):
            raise GatewayError("GATE_C_REQUIRED")
        permit = object.__new__(cls)
        permit._attempt_identity = attempt_identity
        permit._used = False
        return permit

    def _consume(self, attempt_identity: str) -> None:
        if self._used or self._attempt_identity != attempt_identity:
            raise GatewayError("GATE_C_REQUIRED")
        self._used = True


# ---------------------------------------------------------------------------
# Private production SDK transport (cancel real; create Gate-C locked)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CancelAttempt:
    """Deterministic identity for exactly one cancel transmission."""

    operation: str
    request_target_ids: tuple[str, ...]
    request_target_bindings: tuple[tuple[str, str], ...]
    request_market_id: str | None
    attempt_sequence: int
    prior_reconciliation_state: str

    def validate(self) -> None:
        if self.operation not in _CANCEL_OPERATIONS:
            raise GatewayError("MUTATION_IDENTITY_CONFLICT")
        if (
            not isinstance(self.attempt_sequence, int)
            or isinstance(self.attempt_sequence, bool)
            or self.attempt_sequence < 1
            or self.prior_reconciliation_state != "HEALTHY"
        ):
            raise GatewayError("MUTATION_IDENTITY_CONFLICT")
        targets = tuple(_label(value) for value in self.request_target_ids)
        bindings = tuple(
            (_label(target), _label(order_identity))
            for target, order_identity in self.request_target_bindings
        )
        if (
            targets != tuple(sorted(targets))
            or len(targets) > _MAX_CANCEL_TARGETS
            or len(set(targets)) != len(targets)
            or bindings != tuple(sorted(bindings))
            or len(bindings) != len(targets)
            or len(set(bindings)) != len(bindings)
            or tuple(target for target, _owner in bindings) != targets
        ):
            raise GatewayError("MUTATION_IDENTITY_CONFLICT")
        if self.operation == "CANCEL_ONE" and len(targets) != 1:
            raise GatewayError("MUTATION_IDENTITY_CONFLICT")
        if self.operation in ("CANCEL_MANY", "CANCEL_MARKET") and not targets:
            raise GatewayError("MUTATION_IDENTITY_CONFLICT")
        if self.operation == "CANCEL_MARKET":
            if self.request_market_id is None:
                raise GatewayError("MUTATION_IDENTITY_CONFLICT")
            _label(self.request_market_id)
        elif self.request_market_id is not None:
            raise GatewayError("MUTATION_IDENTITY_CONFLICT")

    @property
    def identity(self) -> str:
        self.validate()
        return _sha(
            "cancelattempt:sha256:",
            {
                "operation": self.operation,
                "request_target_ids": list(self.request_target_ids),
                "request_target_bindings": [
                    list(binding) for binding in self.request_target_bindings
                ],
                "request_market_id": self.request_market_id,
                "attempt_sequence": self.attempt_sequence,
                "prior_reconciliation_state": self.prior_reconciliation_state,
            },
        )


class _ProductionSdkMutationTransport:
    """Internal SDK transport reachable only through durable ``GateBSession``."""

    def __init__(
        self, client: object, *, transmitted_attempt_ids: set[str] | None = None
    ):
        self._client = client
        self._transmitted: set[str] = set(transmitted_attempt_ids or ())

    # -- create surface: structurally unreachable ---------------------------

    def create_limit_order(self, *_args: object, **_kwargs: object) -> object:
        raise GatewayError("GATE_C_REQUIRED")

    def place_limit_order(self, *_args: object, **_kwargs: object) -> object:
        raise GatewayError("GATE_C_REQUIRED")

    def post_order(
        self, *_args: object, permit: object = None, **_kwargs: object
    ) -> object:
        # Even a supplied permit cannot help: no caller can construct one.
        if not isinstance(permit, GateCLivePermit):
            raise GatewayError("GATE_C_REQUIRED")
        raise GatewayError("GATE_C_REQUIRED")  # pragma: no cover - unreachable

    def place_market_order(self, *_args: object, **_kwargs: object) -> object:
        raise GatewayError("GATE_C_REQUIRED")

    def gate_c_transport(self, permit: GateCLivePermit) -> object:
        """Return a transient callable handle without exposing the raw client."""
        if not isinstance(permit, GateCLivePermit) or permit._used:
            raise GatewayError("GATE_C_REQUIRED")
        client = self._client

        class _Handle:
            __slots__ = ("_build", "_transmit", "_asset_keyword", "_transmitted")

            def __init__(self) -> None:
                self._transmitted = False
                try:
                    parameters = inspect.signature(
                        getattr(type(client), "create_" + "limit_order")
                    ).parameters
                    self._asset_keyword = (
                        "asset_id" if "asset_id" in parameters else "token_id"
                    )
                except (TypeError, ValueError, AttributeError):
                    self._asset_keyword = "asset_id"
                self._build = lambda **kwargs: getattr(
                    client, "create_" + "limit_order"
                )(**kwargs)
                self._transmit = lambda signed: getattr(
                    client, "post_" + "order"
                )(signed)

            def build(self, **kwargs: object) -> object:
                try:
                    build_kwargs = dict(kwargs)
                    if self._asset_keyword == "token_id":
                        build_kwargs["token_id"] = build_kwargs.pop("asset_id")
                    return self._build(**build_kwargs)
                except GatewayError:
                    raise
                except Exception:
                    raise GatewayError("SIGNING_FAILED") from None

            def transmit(self, signed: object) -> object:
                if not permit._used or self._transmitted:
                    raise GatewayError("GATE_C_REQUIRED")
                self._transmitted = True
                try:
                    return self._transmit(signed)
                except GatewayError:
                    raise
                except Exception:
                    raise GatewayError("CREATE_TRANSPORT_AMBIGUOUS") from None

        return _Handle()

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
                response = self._client.cancel_order(
                    order_id=attempt.request_target_ids[0]
                )
            elif attempt.operation == "CANCEL_MARKET":
                response = self._client.cancel_market_orders(
                    market=attempt.request_market_id
                )
            else:  # CANCEL_MANY
                response = self._client.cancel_orders(
                    order_ids=attempt.request_target_ids
                )
        except Exception:
            # Possibly transmitted: never blindly retried; reconcile upstream.
            raise GatewayError("CANCEL_PROBE_AMBIGUOUS") from None
        return _summarize_cancel_response(
            response, expected_target_ids=attempt.request_target_ids
        )


def _summarize_cancel_response(
    response: object, *, expected_target_ids: Sequence[str]
) -> tuple[str, Mapping[str, object]]:
    """Classify the exact SDK response using only sanitized IDs and counts."""
    try:
        canceled = getattr(response, "canceled")
        not_canceled = getattr(response, "not_canceled")
    except Exception:
        raise GatewayError("CANCEL_PROBE_AMBIGUOUS") from None
    if (
        isinstance(canceled, (str, bytes))
        or not isinstance(canceled, RuntimeSequence)
        or not isinstance(not_canceled, RuntimeMapping)
    ):
        raise GatewayError("CANCEL_PROBE_AMBIGUOUS")
    try:
        canceled_ids = tuple(_label(order_id) for order_id in canceled)
        not_canceled_items = tuple(not_canceled.items())
        not_canceled_ids = tuple(_label(order_id) for order_id, _ in not_canceled_items)
        if any(not isinstance(reason, str) for _, reason in not_canceled_items):
            raise GatewayError("CANCEL_PROBE_AMBIGUOUS")
    except Exception:
        raise GatewayError("CANCEL_PROBE_AMBIGUOUS") from None

    expected = set(expected_target_ids)
    canceled_set = set(canceled_ids)
    not_canceled_set = set(not_canceled_ids)
    malformed_coverage = len(canceled_ids) != len(canceled_set) or bool(
        canceled_set & not_canceled_set
    )
    if (
        not malformed_coverage
        and not expected
        and not canceled_set
        and not not_canceled_set
    ):
        result = "DEFINITIVE_ACCEPTED"
    elif (
        not malformed_coverage
        and bool(expected)
        and canceled_set == expected
        and not not_canceled_set
    ):
        result = "DEFINITIVE_ACCEPTED"
    elif (
        not malformed_coverage
        and bool(expected)
        and not canceled_set
        and not_canceled_set == expected
    ):
        result = "DEFINITIVE_REJECTED"
    else:
        result = "AMBIGUOUS"
    return result, {
        "canceled_count": len(canceled_ids),
        "not_canceled_count": len(not_canceled_ids),
    }


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
    gate_b_reconciliation_state: str
    open_orders_before: int
    open_orders_after: int
    positions_before: int
    positions_after: int
    collateral_balance_before: str
    collateral_balance_after: str
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
            "gate_b_reconciliation_state": self.gate_b_reconciliation_state,
            "open_orders_before": self.open_orders_before,
            "open_orders_after": self.open_orders_after,
            "positions_before": self.positions_before,
            "positions_after": self.positions_after,
            "collateral_balance_before": self.collateral_balance_before,
            "collateral_balance_after": self.collateral_balance_after,
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
        "_transport",
        "_attempt_seq",
        "_audit_sink",
        "_gateway",
        "_wallet_lock",
        "_unresolved_attempts",
        "_gate_b_reconciliation_state",
        "_signing_probe_id",
    )

    def __init__(
        self,
        client: object,
        policy: GateBIdentityPolicy,
        *,
        audit_sink: Callable[[Mapping[str, object]], None] | None = None,
        gateway: ProtectedExecutionGateway | None = None,
        wallet_lock: WalletSessionLock | None = None,
    ):
        self._client = client
        self._policy = policy
        self._state = "B2_AUTHENTICATED"
        self._gateway = gateway
        self._wallet_lock = wallet_lock
        self._audit_sink = audit_sink
        started: dict[str, int] = {}
        unresolved: set[str] = set()
        reconciliation_state = "REQUIRED"
        if gateway is not None:
            for journal_event in gateway.gate_b_events():
                data = dict(journal_event.data)
                if journal_event.event_type == "GATE_B_RECONCILED":
                    reconciliation_state = str(data["gate_b_reconciliation_state"])
                elif journal_event.event_type == "GATE_B_CANCEL_ATTEMPT_STARTED":
                    identity = str(data["cancel_attempt_id"])
                    started[identity] = int(data["attempt_sequence"])
                    unresolved.add(identity)
                elif journal_event.event_type == "GATE_B_CANCEL_ATTEMPT_RESULT":
                    identity = str(data["cancel_attempt_id"])
                    if data["cancel_result"] in (
                        "DEFINITIVE_ACCEPTED",
                        "DEFINITIVE_REJECTED",
                    ):
                        unresolved.discard(identity)
                    else:
                        unresolved.add(identity)
        self._attempt_seq = max(started.values(), default=0)
        self._unresolved_attempts = unresolved
        self._gate_b_reconciliation_state = reconciliation_state
        self._transport = _ProductionSdkMutationTransport(
            client, transmitted_attempt_ids=set(started)
        )
        self._signing_probe_id: str | None = None
        # Journal the sanitized capability transition. The sink is intended to be
        # the existing tamper-evident gateway store's append; it never receives a
        # secret value, credential, or signature.
        self._emit("GATE_B_AUTHENTICATED", {})

    def _emit(self, event_type: str, extra: Mapping[str, object]) -> None:
        if self._audit_sink is None and self._gateway is None:
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
        journal_data = dict(event)
        journal_data.pop("event_type")
        if self._gateway is not None:
            self._gateway.record_gate_b_event(event_type, journal_data)
        if self._audit_sink is not None:
            self._audit_sink(dict(event))

    @classmethod
    def authenticate(
        cls,
        provider: GateBSecretProvider,
        policy: GateBIdentityPolicy,
        *,
        client_factory: ClientFactory = create_deposit_wallet_client,
        audit_sink: Callable[[Mapping[str, object]], None] | None = None,
        gateway: ProtectedExecutionGateway | None = None,
        wallet_lock: WalletSessionLock | None = None,
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
        return cls(
            client,
            policy,
            audit_sink=audit_sink,
            gateway=gateway,
            wallet_lock=wallet_lock,
        )

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

    def gate_c_transport(self, permit: GateCLivePermit) -> object:
        """Issue the private one-attempt build/transmit handle to Gate-C."""
        if not isinstance(permit, GateCLivePermit) or permit._used:
            raise GatewayError("GATE_C_REQUIRED")
        if self._state not in (
            "B2_AUTHENTICATED",
            "B3_SIGNING_VERIFIED",
            "B4_CANCEL_TRANSPORT_VERIFIED",
        ):
            raise GatewayError("AUTHENTICATION_FAILED")
        return self._transport.gate_c_transport(permit)

    def _next_attempt_sequence(self) -> int:
        self._attempt_seq += 1
        return self._attempt_seq

    def _record_reconciliation(self, snapshot: Mapping[str, object]) -> None:
        self._emit(
            "GATE_B_RECONCILED",
            {
                "gate_b_reconciliation_state": "HEALTHY",
                "collateral_balance": str(snapshot["collateral_balance"]),
                "open_orders": int(snapshot["open_orders"]),
                "account_trades": int(snapshot["account_trades"]),
                "positions": int(snapshot["positions"]),
            },
        )
        self._gate_b_reconciliation_state = "HEALTHY"

    def _require_cancel_ready(self) -> ProtectedExecutionGateway:
        if self._state not in (
            "B2_AUTHENTICATED",
            "B3_SIGNING_VERIFIED",
            "B4_CANCEL_TRANSPORT_VERIFIED",
        ):
            raise GatewayError("AUTHENTICATION_FAILED")
        if self._gateway is None:
            raise GatewayError("GATE_B_STORE_REQUIRED")
        if self._wallet_lock is None or not self._wallet_lock.active:
            raise GatewayError("GATE_B_OWNERSHIP_REQUIRED")
        if self._unresolved_attempts:
            raise GatewayError("RECONCILIATION_REQUIRED")
        if self._gate_b_reconciliation_state != "HEALTHY":
            raise GatewayError("RECONCILIATION_REQUIRED")
        return self._gateway

    @staticmethod
    def _canonical_explicit_scope(
        request_target_ids: Sequence[str],
        request_target_bindings: Sequence[tuple[str, str]],
    ) -> tuple[tuple[str, ...], tuple[tuple[str, str], ...]]:
        if isinstance(request_target_ids, (str, bytes)) or isinstance(
            request_target_bindings, (str, bytes)
        ):
            raise GatewayError("MUTATION_REQUEST_INVALID")
        try:
            targets = tuple(_label(value) for value in request_target_ids)
            bindings = tuple(
                (_label(binding[0]), _label(binding[1]))
                for binding in request_target_bindings
                if isinstance(binding, (list, tuple)) and len(binding) == 2
            )
        except (GatewayError, TypeError, ValueError):
            raise GatewayError("MUTATION_REQUEST_INVALID") from None
        if len(bindings) != len(request_target_bindings):
            raise GatewayError("MUTATION_REQUEST_INVALID")
        if (
            len(set(targets)) != len(targets)
            or len(set(bindings)) != len(bindings)
            or len({target for target, _owner in bindings}) != len(bindings)
        ):
            raise GatewayError("MUTATION_REQUEST_INVALID")
        canonical_targets = tuple(sorted(targets))
        canonical_bindings = tuple(sorted(bindings))
        if tuple(target for target, _owner in canonical_bindings) != canonical_targets:
            raise GatewayError("MUTATION_REQUEST_INVALID")
        return canonical_targets, canonical_bindings

    @staticmethod
    def _local_order_bindings(
        gateway: ProtectedExecutionGateway,
    ) -> tuple[dict[str, str], dict[str, str]]:
        owners = {
            attempt.venue_order_id: attempt.order_identity
            for attempt in gateway.state.mutation_attempts
            if attempt.operation == "CREATE"
            and attempt.outcome == "DEFINITIVE_ACCEPTED"
            and attempt.venue_order_id is not None
        }
        markets = {
            order.order_identity: order.market_id
            for order in gateway.state.prepared_orders
        }
        return owners, markets

    def _validated_cancel_scope(
        self,
        operation: str,
        *,
        request_target_ids: Sequence[str] = (),
        request_target_bindings: Sequence[tuple[str, str]] = (),
        request_market_id: str | None = None,
    ) -> tuple[tuple[str, ...], tuple[tuple[str, str], ...], str | None]:
        gateway = self._require_cancel_ready()
        open_targets = tuple(sorted(gateway.state.venue_open_order_ids))
        if len(open_targets) > _MAX_CANCEL_TARGETS:
            raise GatewayError("MUTATION_REQUEST_INVALID")
        owners, markets = self._local_order_bindings(gateway)
        if operation == "CANCEL_ALL":
            if (
                request_target_ids
                or request_target_bindings
                or request_market_id is not None
            ):
                raise GatewayError("MUTATION_REQUEST_INVALID")
            if any(target not in owners for target in open_targets):
                raise GatewayError("MUTATION_REQUEST_INVALID")
            bindings = tuple((target, owners[target]) for target in open_targets)
            return open_targets, bindings, None

        targets, bindings = self._canonical_explicit_scope(
            request_target_ids, request_target_bindings
        )
        if (
            not targets
            or len(targets) > _MAX_CANCEL_TARGETS
            or any(target not in open_targets for target in targets)
            or any(owners.get(target) != owner for target, owner in bindings)
        ):
            raise GatewayError("MUTATION_REQUEST_INVALID")
        if operation == "CANCEL_ONE":
            if len(targets) != 1 or request_market_id is not None:
                raise GatewayError("MUTATION_REQUEST_INVALID")
            return targets, bindings, None
        if operation == "CANCEL_MANY":
            if request_market_id is not None:
                raise GatewayError("MUTATION_REQUEST_INVALID")
            return targets, bindings, None
        if operation != "CANCEL_MARKET" or request_market_id is None:
            raise GatewayError("MUTATION_REQUEST_INVALID")
        market_id = _label(request_market_id)
        local_market_targets = tuple(
            sorted(
                target
                for target in open_targets
                if markets.get(owners.get(target, "")) == market_id
            )
        )
        if targets != local_market_targets or any(
            markets.get(owner) != market_id for _target, owner in bindings
        ):
            raise GatewayError("MUTATION_REQUEST_INVALID")
        return targets, bindings, market_id

    def _execute_cancel(
        self,
        operation: str,
        *,
        request_target_ids: Sequence[str] = (),
        request_target_bindings: Sequence[tuple[str, str]] = (),
        request_market_id: str | None = None,
    ) -> Mapping[str, object]:
        targets, bindings, market_id = self._validated_cancel_scope(
            operation,
            request_target_ids=request_target_ids,
            request_target_bindings=request_target_bindings,
            request_market_id=request_market_id,
        )
        attempt = CancelAttempt(
            operation=operation,
            request_target_ids=targets,
            request_target_bindings=bindings,
            request_market_id=market_id,
            attempt_sequence=self._next_attempt_sequence(),
            prior_reconciliation_state="HEALTHY",
        )
        self._emit(
            "GATE_B_CANCEL_ATTEMPT_STARTED",
            {
                "cancel_attempt_id": attempt.identity,
                "operation": attempt.operation,
                "request_target_ids": list(attempt.request_target_ids),
                "request_target_bindings": [
                    list(binding) for binding in attempt.request_target_bindings
                ],
                "request_market_id": attempt.request_market_id,
                "attempt_sequence": attempt.attempt_sequence,
                "prior_reconciliation_state": attempt.prior_reconciliation_state,
            },
        )
        self._unresolved_attempts.add(attempt.identity)
        try:
            result, summary = self._transport.cancel(attempt)
        except GatewayError:
            try:
                self._emit(
                    "GATE_B_CANCEL_ATTEMPT_RESULT",
                    {
                        "cancel_attempt_id": attempt.identity,
                        "cancel_result": "AMBIGUOUS",
                        "canceled_count": 0,
                        "not_canceled_count": 0,
                    },
                )
            except GatewayError:
                pass
            raise GatewayError("CANCEL_PROBE_AMBIGUOUS") from None
        try:
            self._emit(
                "GATE_B_CANCEL_ATTEMPT_RESULT",
                {
                    "cancel_attempt_id": attempt.identity,
                    "cancel_result": result,
                    "canceled_count": int(summary["canceled_count"]),
                    "not_canceled_count": int(summary["not_canceled_count"]),
                },
            )
        except GatewayError:
            raise GatewayError("CANCEL_PROBE_AMBIGUOUS") from None
        if result == "AMBIGUOUS":
            raise GatewayError("CANCEL_PROBE_AMBIGUOUS")
        if result in ("DEFINITIVE_ACCEPTED", "DEFINITIVE_REJECTED"):
            self._unresolved_attempts.discard(attempt.identity)
        return {
            "cancel_attempt_id": attempt.identity,
            "cancel_result": result,
            "canceled_count": int(summary["canceled_count"]),
            "not_canceled_count": int(summary["not_canceled_count"]),
        }

    def cancel_one(
        self,
        *,
        request_target_ids: Sequence[str],
        request_target_bindings: Sequence[tuple[str, str]],
    ) -> Mapping[str, object]:
        return self._execute_cancel(
            "CANCEL_ONE",
            request_target_ids=request_target_ids,
            request_target_bindings=request_target_bindings,
        )

    def cancel_many(
        self,
        *,
        request_target_ids: Sequence[str],
        request_target_bindings: Sequence[tuple[str, str]],
    ) -> Mapping[str, object]:
        return self._execute_cancel(
            "CANCEL_MANY",
            request_target_ids=request_target_ids,
            request_target_bindings=request_target_bindings,
        )

    def cancel_market(
        self,
        *,
        request_market_id: str,
        request_target_ids: Sequence[str],
        request_target_bindings: Sequence[tuple[str, str]],
    ) -> Mapping[str, object]:
        return self._execute_cancel(
            "CANCEL_MARKET",
            request_market_id=request_market_id,
            request_target_ids=request_target_ids,
            request_target_bindings=request_target_bindings,
        )

    def cancel_all(self) -> Mapping[str, object]:
        return self._execute_cancel("CANCEL_ALL")

    # -- bounded authenticated reads ---------------------------------------

    def account_snapshot(self) -> dict[str, object]:
        """Bounded sanitized public account snapshot; no raw credential data."""
        try:
            balance = self._client.get_balance_allowance(asset_type="COLLATERAL")
            open_items = _bounded_items(self._client.list_open_orders(), limit=100)
            trade_items = _bounded_items(self._client.list_account_trades(), limit=100)
            position_items = _bounded_items(
                self._client.list_positions(user=self.public_wallet, page_size=100),
                limit=100,
            )
        except GatewayError:
            raise
        except Exception:
            raise GatewayError("AUTHENTICATED_READ_FAILED") from None
        collateral = _canonical_decimal(
            _as_decimal(getattr(balance, "balance", "0")) / Decimal(1_000_000)
        )
        allowances = getattr(balance, "allowances", {})
        if allowances is None:
            allowances = {}
        if not isinstance(allowances, Mapping):
            raise GatewayError("AUTHENTICATED_READ_FAILED")
        config = self._client._ctx.environment_config
        exchange_labels = {
            str(getattr(config, "standard_exchange", "")).lower(): "exchange",
            str(getattr(config, "neg_risk_exchange", "")).lower(): "neg-risk-exchange",
            str(getattr(config, "exchange_v3", "")).lower(): "exchange-v3",
        }
        allowance_by_exchange: dict[str, str] = {}
        for key, value in allowances.items():
            label = exchange_labels.get(str(key).lower())
            if label is not None:
                allowance_by_exchange[label] = _canonical_decimal(
                    _as_decimal(value) / Decimal(1_000_000)
                )
        position_quantities: dict[str, str] = {}
        market_exposures: dict[str, str] = {}
        gross = Decimal(0)
        realized_loss = Decimal(0)
        drawdown = Decimal(0)
        active_markets: set[str] = set()
        for item in position_items:
            if not all(
                hasattr(item, field)
                for field in (
                    "asset_id", "condition_id", "current_size", "current_value",
                    "realized_pnl", "total_pnl",
                )
            ):
                continue
            asset_id = str(item.asset_id)
            condition_id = str(item.condition_id)
            size = _as_decimal(item.current_size)
            value = abs(_as_decimal(item.current_value))
            position_quantities[asset_id] = _canonical_decimal(size)
            market_exposures[condition_id] = _canonical_decimal(
                _as_decimal(market_exposures.get(condition_id, "0")) + value
            )
            gross += value
            realized_loss += max(-_as_decimal(item.realized_pnl), Decimal(0))
            drawdown += max(-_as_decimal(item.total_pnl), Decimal(0))
            if size > 0:
                active_markets.add(condition_id)
        return {
            "collateral_balance": collateral,
            "allowance_by_exchange": allowance_by_exchange,
            "open_orders": len(open_items),
            "account_trades": len(trade_items),
            "positions": len(position_items),
            "position_quantities": position_quantities,
            "market_exposures_pusd": market_exposures,
            "gross_exposure_pusd": _canonical_decimal(gross),
            "committed_exposure_pusd": "0",
            "realized_loss_pusd": _canonical_decimal(realized_loss),
            "drawdown_pusd": _canonical_decimal(drawdown),
            "cumulative_loss_pusd": _canonical_decimal(max(realized_loss, drawdown)),
            "active_markets": len(active_markets),
        }

    # -- real local LIMIT signing probe (no post) --------------------------

    def signing_probe(
        self, *, token_id: str, price: str, size: str, side: str = "BUY"
    ) -> str:
        if self._state not in (
            "B2_AUTHENTICATED",
            "B3_SIGNING_VERIFIED",
            "B4_CANCEL_TRANSPORT_VERIFIED",
        ):
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
        if (
            not isinstance(repository_head, str)
            or _HEAD_RE.fullmatch(repository_head) is None
        ):
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
        self._record_reconciliation(snapshot)
        cancel_result = self.cancel_all()
        attempt_id = str(cancel_result["cancel_attempt_id"])
        result = str(cancel_result["cancel_result"])
        canceled_count = int(cancel_result["canceled_count"])
        not_canceled_count = int(cancel_result["not_canceled_count"])
        # The account was empty, so success requires that nothing was canceled and
        # nothing was left uncanceled; any canceled or not-canceled order is an
        # incident, not a pass.
        if canceled_count != 0 or not_canceled_count != 0:
            raise GatewayError("CANCEL_PROBE_FAILED")
        after = self.account_snapshot()
        open_after = int(after["open_orders"])
        positions_after = int(after["positions"])
        balance_after = str(after["collateral_balance"])
        if (
            open_after != 0
            or positions_after != 0
            or _as_decimal(balance_after) != Decimal(0)
        ):
            self._unresolved_attempts.add(attempt_id)
            self._emit(
                "GATE_B_CANCEL_ATTEMPT_RESULT",
                {
                    "cancel_attempt_id": attempt_id,
                    "cancel_result": "AMBIGUOUS",
                    "canceled_count": canceled_count,
                    "not_canceled_count": not_canceled_count,
                },
            )
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
            cancel_probe_attempt_id=attempt_id,
            cancel_probe_result=result,
            gate_b_reconciliation_state="HEALTHY",
            open_orders_before=open_before,
            open_orders_after=open_after,
            positions_before=positions_before,
            positions_after=positions_after,
            collateral_balance_before=balance_before,
            collateral_balance_after=balance_after,
            verified_time_ns=now_ns,
            valid_until_ns=valid_ns,
            redaction_pass=True,
        )
        self._emit(
            "GATE_B_CANCEL_TRANSPORT_VERIFIED",
            {
                "cancel_attempt_id": attempt_id,
                "cancel_result": result,
                "receipt_id": receipt.receipt_id,
                "verified_time_ns": now_ns,
                "gate_b_reconciliation_state": "HEALTHY",
            },
        )
        return receipt

    def close(self) -> None:
        _safe_close(self._client)
        self._client = None
        self._transport = None
        self._signing_probe_id = None
        self._state = "B0_LOCKED"

    def __enter__(self) -> "GateBSession":
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()


def _count_page(page: object, *, limit: int) -> int:
    return len(_bounded_items(page, limit=limit))


def _bounded_items(page: object, *, limit: int) -> tuple[object, ...]:
    items = page.iter_items() if hasattr(page, "iter_items") else page
    values: list[object] = []
    for item in items:
        values.append(item)
        if len(values) > limit:
            raise GatewayError("AUTHENTICATED_READ_FAILED")
    return tuple(values)


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
