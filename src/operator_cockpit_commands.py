"""S10-CC-CMD-01 protected Control Center lifecycle-governance commands.

Default-off. When the cockpit is started with ``--enable-commands`` on a TTY, one local
operator authenticates with a command secret read once through ``getpass`` (never argv,
environment, file, query, cookie or browser storage). The process keeps only the secret's
SHA-256 digest and at most one ephemeral in-memory bearer session (900 s, 32 random bytes,
stored as a digest). A process restart, a new login, a revoke or the failed-login lock
invalidates it.

Exactly five commands exist, and each maps to one existing canonical StrategyLifecycle
record built through the public builders:

- ``STRATEGY_PAUSE``: APPLY ``PAUSE_NEW_EXPOSURE`` restriction receipt;
- ``STRATEGY_RESUME``: CLEAR of one exact ``PAUSE_NEW_EXPOSURE`` restriction receipt;
- ``STRATEGY_QUARANTINE``: health receipt to ``QUARANTINED``;
- ``POLICY_ACTIVATE``: ACTIVATE portfolio policy receipt for an existing policy;
- ``POLICY_REVOKE``: REVOKE portfolio policy receipt for the exact active policy.

The canonical lifecycle record is the durable receipt and audit event; this module owns no
lifecycle state, no command database or queue and no retry. Every command derives its
identity from the authenticated operator plus the exact normalized request, builds the exact
candidate record from request fields and fixed semantics only, resolves an exact lost-response
retry through the store's duplicate-first preview before any mutable-state precondition, and
then appends through the conditional expected-head store primitive. Outward results are the
sanitized receipt or one closed error code. Nothing here has product-network, account,
credential, paper, execution, Gate-C, LIVE-ORCH, order, capital or live authority.
"""

from __future__ import annotations

from dataclasses import dataclass
import getpass
import hashlib
import hmac
import re
import secrets
import sys
import time
from pathlib import Path
from typing import Any, Callable

from src.strategy_lifecycle import (
    HEALTH_STATES,
    PORTFOLIO_CAPACITY_VALID,
    StrategyLifecycleError,
    StrategyLifecycleSnapshot,
    build_portfolio_policy_receipt,
    build_strategy_health_receipt,
    build_strategy_restriction_receipt,
    canonical_json_bytes,
    evaluate_portfolio_capacity,
)
from src.strategy_lifecycle.models import (
    MAX_TIME_NS,
    LifecycleRecord,
    money,
    opaque_ref,
    record_kind_of,
    sha256_hex,
    strict_json_loads,
)
from src.strategy_lifecycle.store import (
    conditional_append_strategy_lifecycle_record,
    preview_strategy_lifecycle_record,
)


RECEIPT_SCHEMA_VERSION = "1.0.0"
AUTH_MODE = "EPHEMERAL_BEARER_SESSION"
SESSION_TTL_SECONDS = 900
MAX_ACTIVE_SESSIONS = 1
SESSION_TOKEN_BYTES = 32
MAX_FAILED_LOGINS = 5
MAX_CLOCK_SKEW_MS = 5_000
MIN_SECRET_CHARS = 32
MAX_SECRET_CHARS = 256
MAX_COMMAND_BODY_BYTES = 4_096
MAX_SAFE_INTEGER = 2**53 - 1

COMMAND_KINDS = (
    "STRATEGY_PAUSE",
    "STRATEGY_RESUME",
    "STRATEGY_QUARANTINE",
    "POLICY_ACTIVATE",
    "POLICY_REVOKE",
)
CONFIRMATION_PHRASES = {
    "STRATEGY_PAUSE": "CONFIRM-PAUSE",
    "STRATEGY_RESUME": "CONFIRM-RESUME",
    "STRATEGY_QUARANTINE": "CONFIRM-QUARANTINE",
    "POLICY_ACTIVATE": "CONFIRM-ACTIVATE-POLICY",
    "POLICY_REVOKE": "CONFIRM-REVOKE-POLICY",
}
COMMON_FIELDS = (
    "command_kind",
    "expected_lifecycle_store_head_entry_hash",
    "issued_at_ms",
    "confirmation_phrase",
)
TARGET_FIELDS = {
    "STRATEGY_PAUSE": ("strategy_version_id",),
    "STRATEGY_RESUME": ("strategy_version_id", "restriction_key"),
    "STRATEGY_QUARANTINE": ("strategy_version_id", "previous_health_state"),
    "POLICY_ACTIVATE": ("policy_id", "previous_active_policy_id"),
    "POLICY_REVOKE": ("policy_id",),
}
COMMAND_ERROR_STATUS = {
    "COMMANDS_DISABLED": 403,
    "AUTH_REQUIRED": 401,
    "AUTH_FAILED": 401,
    "AUTH_LOCKED": 403,
    "SESSION_EXPIRED": 401,
    "INVALID_COMMAND": 400,
    "INVALID_CONFIRMATION": 400,
    "STALE_STATE": 409,
    "COMMAND_PRECONDITION_FAILED": 409,
    "SOURCE_UNAVAILABLE": 503,
    "INTERNAL_ERROR": 500,
}
COMMAND_ERROR_CODES = tuple(COMMAND_ERROR_STATUS)
NON_AUTHORITY = {
    "no_product_network": True,
    "no_account_access": True,
    "no_order_authority": True,
    "no_gate_c_authority": True,
    "no_live_authority": True,
}

OPERATOR_ID_RE = re.compile(r"^op-[a-z0-9][a-z0-9_-]{0,30}$")
_BEARER_RE = re.compile(r"^Bearer ([A-Za-z0-9_-]{43})$")
_HEAD_RE = re.compile(r"^[0-9a-f]{64}$")
_VERSION_ID_RE = re.compile(r"^strategyversion:sha256:[0-9a-f]{64}$")
_POLICY_ID_RE = re.compile(r"^portfolioauthoritypolicy:sha256:[0-9a-f]{64}$")
_RESTRICTION_KEY_RE = re.compile(r"^[a-z][a-z0-9_.-]{0,127}$")
_PAUSE = "PAUSE_NEW_EXPOSURE"
_BLOCKED_RESUME_HEALTH = frozenset({"QUARANTINED", "RETIRED"})
_SAFETY_REDUCING_LOCAL_REASONS = frozenset(
    {"HEALTH_BLOCKS_ACTIVE_RISK", "RESTRICTION_BLOCKS_ACTIVE_RISK"}
)
# Canonical store failures that mean the configured source cannot be read or verified. The
# command record itself is already builder-validated, so field failures here are path/source.
_SOURCE_CODES = frozenset(
    {"SCHEMA_CONFLICT", "INTEGRITY_TAMPER", "FIELD_TYPE_INVALID", "FIELD_VALUE_INVALID"}
)


def _default_now_ms() -> int:
    return time.time_ns() // 1_000_000


def _default_new_token() -> str:
    return secrets.token_urlsafe(SESSION_TOKEN_BYTES)


def _stdin_is_tty() -> bool:
    try:
        return bool(sys.stdin is not None and sys.stdin.isatty())
    except (AttributeError, OSError, ValueError):
        return False


# Internal deterministic test seams. Production uses the wall clock and stdlib ``secrets``.
# They are not reachable through HTTP, CLI or configuration.
_now_ms: Callable[[], int] = _default_now_ms
_new_token: Callable[[], str] = _default_new_token


class CommandError(Exception):
    """Closed, payload-free command failure; never carries request, secret or path text."""

    def __init__(self, code: str, canonical_error_code: str | None = None) -> None:
        if code not in COMMAND_ERROR_STATUS:
            code = "INTERNAL_ERROR"
        super().__init__(code)
        self.code = code
        self.canonical_error_code = (
            StrategyLifecycleError(canonical_error_code).code
            if canonical_error_code is not None
            else None
        )

    @property
    def http_status(self) -> int:
        return COMMAND_ERROR_STATUS[self.code]

    def body(self) -> dict[str, Any]:
        error: dict[str, Any] = {"code": self.code}
        if self.canonical_error_code is not None:
            error["canonical_error_code"] = self.canonical_error_code
        return {"error": error}


class CommandBootstrapError(Exception):
    """Closed startup failure: OPERATOR_ID_INVALID, TTY_REQUIRED or SECRET_INVALID."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _digest(text: str) -> bytes | None:
    try:
        return hashlib.sha256(text.encode("utf-8")).digest()
    except UnicodeEncodeError:
        return None


@dataclass(frozen=True)
class _Session:
    token_digest: bytes
    started_at_ms: int
    expires_at_ms: int


_BOOTSTRAP = object()


class CommandAuth:
    """In-memory operator authentication for one cockpit process.

    Holds the operator id, the SHA-256 digest of the bootstrap secret, at most one bearer
    session (token digest only) and a cumulative failed-login count. Constructed only by
    ``bootstrap_command_auth``. Its repr never exposes digest or token material.
    """

    __slots__ = ("_operator_id", "_secret_digest", "_session", "_failed_logins")

    def __init__(self, operator_id: str, secret_digest: bytes, *, _token: object = None) -> None:
        if _token is not _BOOTSTRAP:
            raise TypeError("CommandAuth is created only by bootstrap_command_auth")
        self._operator_id = operator_id
        self._secret_digest = secret_digest
        self._session: _Session | None = None
        self._failed_logins = 0

    def __repr__(self) -> str:
        return f"CommandAuth(operator_id={self._operator_id!r})"

    def __reduce__(self):  # pragma: no cover - defensive: never serialize auth state
        raise TypeError("CommandAuth is not serializable")

    @property
    def operator_id(self) -> str:
        return self._operator_id

    @property
    def locked(self) -> bool:
        return self._failed_logins >= MAX_FAILED_LOGINS

    def has_active_session(self) -> bool:
        session = self._session
        return session is not None and _now_ms() < session.expires_at_ms

    def login(self, secret: str) -> dict[str, Any]:
        if self.locked:
            raise CommandError("AUTH_LOCKED")
        candidate = _digest(secret)
        if candidate is None or not hmac.compare_digest(candidate, self._secret_digest):
            self._failed_logins += 1
            if self.locked:
                # The lock is authority-reducing: it also ends any current session.
                self._session = None
            raise CommandError("AUTH_FAILED")
        token = _new_token()
        token_digest = _digest(token)
        if token_digest is None or _BEARER_RE.fullmatch("Bearer " + token) is None:
            raise CommandError("INTERNAL_ERROR")
        now = _now_ms()
        # MAX_ACTIVE_SESSIONS == 1: a successful login replaces any prior session.
        self._session = _Session(token_digest, now, now + SESSION_TTL_SECONDS * 1_000)
        return {
            "operator_id": self._operator_id,
            "session_token": token,
            "expires_at_ms": self._session.expires_at_ms,
        }

    def authenticate(self, authorization: list[str]) -> _Session:
        if len(authorization) != 1:
            raise CommandError("AUTH_REQUIRED")
        match = _BEARER_RE.fullmatch(authorization[0])
        session = self._session
        if match is None or session is None:
            raise CommandError("AUTH_REQUIRED")
        presented = _digest(match.group(1))
        if presented is None or not hmac.compare_digest(presented, session.token_digest):
            raise CommandError("AUTH_REQUIRED")
        if _now_ms() >= session.expires_at_ms:
            self._session = None
            raise CommandError("SESSION_EXPIRED")
        return session

    def revoke(self, authorization: list[str]) -> dict[str, Any]:
        self.authenticate(authorization)
        self._session = None
        return {
            "schema_version": RECEIPT_SCHEMA_VERSION,
            "status": "SESSION_REVOKED",
            "active_session": False,
        }


def _command_ref_probe(operator_id: str) -> str:
    return f"cccmd:{operator_id}:sha256:{'0' * 64}"


def validate_operator_id(operator_id: object) -> str:
    """Closed operator-id check; the resulting command_ref must stay a valid opaque ref.

    The digest part of a command_ref is lowercase hex only, so validating the operator id
    with a fixed digest is exact for every later command_ref.
    """

    if not isinstance(operator_id, str) or OPERATOR_ID_RE.fullmatch(operator_id) is None:
        raise CommandBootstrapError("OPERATOR_ID_INVALID")
    try:
        opaque_ref(_command_ref_probe(operator_id))
    except StrategyLifecycleError:
        raise CommandBootstrapError("OPERATOR_ID_INVALID") from None
    return operator_id


def bootstrap_command_auth(
    operator_id: object,
    *,
    is_tty: Callable[[], bool] | None = None,
    read_secret: Callable[[str], str] | None = None,
) -> CommandAuth:
    """Startup-only TTY bootstrap: read the command secret once and keep only its digest."""

    checked = validate_operator_id(operator_id)
    if not (is_tty or _stdin_is_tty)():
        raise CommandBootstrapError("TTY_REQUIRED")
    try:
        secret = (read_secret or getpass.getpass)("Control Center command secret: ")
    except (EOFError, KeyboardInterrupt, OSError):
        raise CommandBootstrapError("SECRET_INVALID") from None
    if (
        not isinstance(secret, str)
        or not MIN_SECRET_CHARS <= len(secret) <= MAX_SECRET_CHARS
        or not secret.isprintable()
    ):
        raise CommandBootstrapError("SECRET_INVALID")
    secret_digest = _digest(secret)
    del secret
    if secret_digest is None:
        raise CommandBootstrapError("SECRET_INVALID")
    return CommandAuth(checked, secret_digest, _token=_BOOTSTRAP)


def command_status(auth: CommandAuth | None) -> dict[str, Any]:
    """Safe, non-secret command capability status."""

    return {
        "read_only": False,
        "commands_enabled": auth is not None,
        "auth_mode": AUTH_MODE,
        "session_ttl_seconds": SESSION_TTL_SECONDS,
        "active_session": auth is not None and auth.has_active_session(),
        "supported_commands": list(COMMAND_KINDS),
        **NON_AUTHORITY,
    }


def require_enabled(auth: CommandAuth | None) -> CommandAuth:
    if auth is None:
        raise CommandError("COMMANDS_DISABLED")
    return auth


def _json_object(raw: bytes) -> dict[str, Any]:
    if not isinstance(raw, bytes) or len(raw) > MAX_COMMAND_BODY_BYTES:
        raise CommandError("INVALID_COMMAND")
    try:
        value = strict_json_loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, StrategyLifecycleError):
        raise CommandError("INVALID_COMMAND") from None
    if not isinstance(value, dict):
        raise CommandError("INVALID_COMMAND")
    return value


def login(auth: CommandAuth, raw: bytes) -> dict[str, Any]:
    """Exact ``{"secret": "..."}`` body; the secret is never echoed, logged or retained."""

    if auth.locked:
        raise CommandError("AUTH_LOCKED")
    body = _json_object(raw)
    if set(body) != {"secret"} or not isinstance(body["secret"], str):
        raise CommandError("INVALID_COMMAND")
    return auth.login(body["secret"])


# ---------------------------------------------------------------------------
# Request normalization and identity.
# ---------------------------------------------------------------------------


def _string(value: object, pattern: re.Pattern[str]) -> str:
    if not isinstance(value, str) or pattern.fullmatch(value) is None:
        raise CommandError("INVALID_COMMAND")
    return value


def normalize_command_request(body: object) -> dict[str, Any]:
    """Strict closed request shape; unknown, extra or missing keys fail closed."""

    if not isinstance(body, dict):
        raise CommandError("INVALID_COMMAND")
    kind = body.get("command_kind")
    if not isinstance(kind, str) or kind not in TARGET_FIELDS:
        raise CommandError("INVALID_COMMAND")
    if set(body) != set(COMMON_FIELDS) | set(TARGET_FIELDS[kind]):
        raise CommandError("INVALID_COMMAND")
    head = body["expected_lifecycle_store_head_entry_hash"]
    if head is not None:
        head = _string(head, _HEAD_RE)
    issued = body["issued_at_ms"]
    if (
        isinstance(issued, bool)
        or not isinstance(issued, int)
        or not 0 <= issued <= MAX_SAFE_INTEGER
    ):
        raise CommandError("INVALID_COMMAND")
    request: dict[str, Any] = {
        "command_kind": kind,
        "expected_lifecycle_store_head_entry_hash": head,
        "issued_at_ms": issued,
    }
    if "strategy_version_id" in body:
        request["strategy_version_id"] = _string(body["strategy_version_id"], _VERSION_ID_RE)
    if "restriction_key" in body:
        request["restriction_key"] = _string(body["restriction_key"], _RESTRICTION_KEY_RE)
    if "previous_health_state" in body:
        state = body["previous_health_state"]
        if not isinstance(state, str) or state not in HEALTH_STATES:
            raise CommandError("INVALID_COMMAND")
        request["previous_health_state"] = state
    if "policy_id" in body:
        request["policy_id"] = _string(body["policy_id"], _POLICY_ID_RE)
    if "previous_active_policy_id" in body:
        previous = body["previous_active_policy_id"]
        request["previous_active_policy_id"] = (
            None if previous is None else _string(previous, _POLICY_ID_RE)
        )
    phrase = body["confirmation_phrase"]
    if not isinstance(phrase, str):
        raise CommandError("INVALID_COMMAND")
    if phrase != CONFIRMATION_PHRASES[kind]:
        raise CommandError("INVALID_CONFIRMATION")
    request["confirmation_phrase"] = phrase
    return request


@dataclass(frozen=True)
class CommandIdentity:
    command_digest: str
    command_ref: str
    created_time_ns: int


def command_identity(operator_id: str, request: dict[str, Any]) -> CommandIdentity:
    """Deterministic identity from the authenticated operator and the exact normalized request."""

    digest = sha256_hex(canonical_json_bytes({"command": request, "operator_id": operator_id}))
    ref = f"cccmd:{operator_id}:sha256:{digest}"
    created = request["issued_at_ms"] * 1_000_000
    if created > MAX_TIME_NS:
        raise CommandError("INVALID_COMMAND")
    try:
        opaque_ref(ref)
    except StrategyLifecycleError:
        raise CommandError("INVALID_COMMAND") from None
    return CommandIdentity(digest, ref, created)


def _check_issued_window(session: _Session, issued_at_ms: int) -> None:
    if (
        issued_at_ms < session.started_at_ms
        or issued_at_ms >= session.expires_at_ms
        or issued_at_ms > _now_ms() + MAX_CLOCK_SKEW_MS
    ):
        raise CommandError("INVALID_COMMAND")


# ---------------------------------------------------------------------------
# Canonical candidates (request fields + fixed command semantics only).
# ---------------------------------------------------------------------------


def build_command_record(request: dict[str, Any], identity: CommandIdentity) -> LifecycleRecord:
    kind = request["command_kind"]
    ref = identity.command_ref
    created = identity.created_time_ns
    if kind == "STRATEGY_PAUSE":
        return build_strategy_restriction_receipt(
            strategy_version_id=request["strategy_version_id"],
            restriction_key="cc.pause." + identity.command_digest[:24],
            action="APPLY",
            restriction_kind=_PAUSE,
            max_active_budget_usd=None,
            decision_ref=ref,
            evidence_refs=(),
            created_time_ns=created,
        )
    if kind == "STRATEGY_RESUME":
        return build_strategy_restriction_receipt(
            strategy_version_id=request["strategy_version_id"],
            restriction_key=request["restriction_key"],
            action="CLEAR",
            restriction_kind=_PAUSE,
            max_active_budget_usd=None,
            decision_ref=ref,
            evidence_refs=(),
            created_time_ns=created,
        )
    if kind == "STRATEGY_QUARANTINE":
        return build_strategy_health_receipt(
            strategy_version_id=request["strategy_version_id"],
            previous_health_state=request["previous_health_state"],
            new_health_state="QUARANTINED",
            decision_ref=ref,
            evidence_refs=(),
            created_time_ns=created,
        )
    if kind == "POLICY_ACTIVATE":
        return build_portfolio_policy_receipt(
            action="ACTIVATE",
            policy_id=request["policy_id"],
            previous_active_policy_id=request["previous_active_policy_id"],
            human_authorization_ref=ref,
            created_time_ns=created,
        )
    return build_portfolio_policy_receipt(
        action="REVOKE",
        policy_id=request["policy_id"],
        previous_active_policy_id=request["policy_id"],
        human_authorization_ref=ref,
        created_time_ns=created,
    )


# ---------------------------------------------------------------------------
# Command-specific preconditions (new PREVIEW_READY mutations only).
# ---------------------------------------------------------------------------


def _precondition(ok: bool) -> None:
    if not ok:
        raise CommandError("COMMAND_PRECONDITION_FAILED")


def _capacity_reasons(candidate: StrategyLifecycleSnapshot, at_time_ns: int):
    """One canonical evaluation; split top-level reasons into strategy-local and global."""

    capacity = evaluate_portfolio_capacity(candidate, at_time_ns)
    local: set[str] = set()
    for item in capacity.strategy_results:
        local |= set(item.reason_codes)
    return capacity, local, set(capacity.reason_codes) - local


def _check_pause(request, before: StrategyLifecycleSnapshot, _candidate, _at: int) -> None:
    version_id = request["strategy_version_id"]
    _precondition(before.version_by_id(version_id) is not None)
    _precondition(before.health_of(version_id) != "RETIRED")
    _precondition(
        not any(item.restriction_kind == _PAUSE for item in before.restrictions_of(version_id))
    )


def _check_resume(request, before: StrategyLifecycleSnapshot, candidate, at: int) -> None:
    version_id = request["strategy_version_id"]
    _precondition(before.version_by_id(version_id) is not None)
    _precondition(before.health_of(version_id) not in _BLOCKED_RESUME_HEALTH)
    active = {item.restriction_key: item for item in before.restrictions_of(version_id)}
    target = active.get(request["restriction_key"])
    _precondition(
        target is not None
        and target.restriction_kind == _PAUSE
        and target.max_active_budget_usd is None
    )
    capacity, _local, global_reasons = _capacity_reasons(candidate, at)
    _precondition(not global_reasons)
    allocation = candidate.allocation_of(version_id)
    if (
        allocation is not None
        and allocation.is_active_at(at)
        and money(allocation.active_budget_usd) > 0
    ):
        own = capacity.strategy_result(version_id)
        _precondition(own is not None and own.status == PORTFOLIO_CAPACITY_VALID)


def _check_quarantine(request, before: StrategyLifecycleSnapshot, _candidate, _at: int) -> None:
    version_id = request["strategy_version_id"]
    previous = request["previous_health_state"]
    _precondition(before.version_by_id(version_id) is not None)
    _precondition(before.health_of(version_id) == previous)
    _precondition(previous not in _BLOCKED_RESUME_HEALTH)


def _check_activate(request, before: StrategyLifecycleSnapshot, candidate, at: int) -> None:
    policy = before.policy_by_id(request["policy_id"])
    _precondition(policy is not None)
    _precondition(before.active_policy_id == request["previous_active_policy_id"])
    _precondition(before.active_policy_id != request["policy_id"])
    _precondition(at >= policy.effective_from_ns)  # type: ignore[union-attr]
    _precondition(policy.expires_at_ns is None or at < policy.expires_at_ns)  # type: ignore[union-attr]
    _capacity, local, global_reasons = _capacity_reasons(candidate, at)
    _precondition(not global_reasons)
    _precondition(not (local - _SAFETY_REDUCING_LOCAL_REASONS))


def _check_revoke(request, before: StrategyLifecycleSnapshot, _candidate, _at: int) -> None:
    _precondition(before.active_policy_id == request["policy_id"])


_CHECKS = {
    "STRATEGY_PAUSE": _check_pause,
    "STRATEGY_RESUME": _check_resume,
    "STRATEGY_QUARANTINE": _check_quarantine,
    "POLICY_ACTIVATE": _check_activate,
    "POLICY_REVOKE": _check_revoke,
}


# ---------------------------------------------------------------------------
# Execution.
# ---------------------------------------------------------------------------


def _canonical_failure(error_codes: tuple[str, ...]) -> CommandError:
    code = error_codes[0] if error_codes else "INTERNAL_VALIDATION_FAILED"
    if code in _SOURCE_CODES:
        return CommandError("SOURCE_UNAVAILABLE")
    if code == "INTERNAL_VALIDATION_FAILED":
        return CommandError("INTERNAL_ERROR")
    return CommandError("COMMAND_PRECONDITION_FAILED", code)


def _receipt(
    status: str,
    request: dict[str, Any],
    identity: CommandIdentity,
    operator_id: str,
    record: LifecycleRecord,
    head: str | None,
) -> dict[str, Any]:
    return {
        "schema_version": RECEIPT_SCHEMA_VERSION,
        "status": status,
        "command_ref": identity.command_ref,
        "command_kind": request["command_kind"],
        "operator_id": operator_id,
        "canonical_record_kind": record_kind_of(record),
        "canonical_record_id": record.record_id,
        "lifecycle_store_head_entry_hash": head,
        "issued_at_ms": request["issued_at_ms"],
        **NON_AUTHORITY,
    }


def execute_command(
    auth: CommandAuth,
    session: _Session,
    lifecycle_path: Path | None,
    raw: bytes,
) -> dict[str, Any]:
    """Run one authenticated command; no automatic retry of any step."""

    request = normalize_command_request(_json_object(raw))
    _check_issued_window(session, request["issued_at_ms"])
    identity = command_identity(auth.operator_id, request)
    if lifecycle_path is None:
        raise CommandError("SOURCE_UNAVAILABLE")
    try:
        record = build_command_record(request, identity)
    except StrategyLifecycleError as failure:
        raise CommandError("COMMAND_PRECONDITION_FAILED", failure.code) from None
    expected = request["expected_lifecycle_store_head_entry_hash"]
    preview = preview_strategy_lifecycle_record(lifecycle_path, record, expected)
    if preview.status == "IDEMPOTENT_REPLAY":
        # Exact lost-response retry: success before any current-state precondition.
        return _receipt(
            "IDEMPOTENT_REPLAY", request, identity, auth.operator_id, record,
            preview.store_head_entry_hash,
        )
    if preview.status == "STALE_HEAD":
        raise CommandError("STALE_STATE")
    if (
        preview.status != "PREVIEW_READY"
        or preview.before_snapshot is None
        or preview.candidate_snapshot is None
    ):
        raise _canonical_failure(preview.error_codes)
    _CHECKS[request["command_kind"]](
        request, preview.before_snapshot, preview.candidate_snapshot, identity.created_time_ns
    )
    result = conditional_append_strategy_lifecycle_record(lifecycle_path, record, expected)
    if result.status in ("COMMITTED", "IDEMPOTENT_REPLAY"):
        return _receipt(
            result.status, request, identity, auth.operator_id, record,
            result.store_head_entry_hash,
        )
    if result.status == "STALE_HEAD":
        raise CommandError("STALE_STATE")
    raise _canonical_failure(result.error_codes)
