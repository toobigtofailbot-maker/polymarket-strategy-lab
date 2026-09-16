"""WP175 restricted-live canary boundary.

This module is intentionally small and manual-only.  It consumes the opaque
Gate-B session handle, writes a sanitized checkpoint through the existing
GatewayStore, and permits one LIMIT transmit.  No scheduler, browser route,
strategy runner, or credential source is present here.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from decimal import Decimal, InvalidOperation, ROUND_CEILING, ROUND_FLOOR, ROUND_HALF_EVEN
import hashlib
import json
import subprocess
import time
from collections.abc import Mapping
from pathlib import Path
from urllib.request import Request, urlopen

from polymarket.models.clob.order_response import AcceptedOrder, RejectedOrder
from polymarket.models.clob.orders import SignedOrder

from src.paper_trading.engine import _replay_journal
from src.paper_trading.models import (
    PaperStrategyBinding,
    validate_strategy_binding,
)
from src.paper_trading.store import PaperStore, PaperTradingError
from src.research_runtime.executable_edge import (
    ExecutableEdgeAssessment,
    ExecutionCostModel,
    validate_assessment,
    validate_execution_cost_model,
)

from .gate_b import (
    GateBSession,
    GateCLivePermit,
    _GATE_C_ISSUER,
)
from .gateway import (
    MAX_ACCOUNT_SNAPSHOT_AGE_NS,
    MutationAttempt,
    OfficialSdkAuthenticatedReadAdapter,
    ProtectedExecutionGateway,
    VenueConstraints,
    GatewayError,
    _GATE_C_EVENT_ISSUER,
    _ADDRESS_RE,
    _canonical_decimal,
    _decimal,
    _label,
    _sha,
    _time,
)


QUALIFICATION_VALIDITY_MINUTES = 10
ARM_RECEIPT_VALIDITY_MINUTES = 10
MAX_LIVE_SESSION_DURATION_MINUTES = 30
MAX_CANARY_WALLET_PUSD = Decimal("50.00")
MAX_GROSS_LIVE_EXPOSURE_PUSD = Decimal("20.00")
MAX_PER_MARKET_EXPOSURE_PUSD = Decimal("15.00")
MAX_PER_ORDER_COMMITTED_PUSD = Decimal("10.00")
MAX_ACTIVE_MARKETS = 1
MAX_SIMULTANEOUS_OPEN_ORDERS = 1
MAX_CREATE_ATTEMPTS_PER_SESSION = 1
MAX_REALIZED_LOSS_PER_UTC_DAY_PUSD = Decimal("5.00")
MAX_CANARY_EQUITY_DRAWDOWN_PUSD = Decimal("7.50")
MAX_CUMULATIVE_CANARY_LOSS_PUSD = Decimal("10.00")
FINAL_MERGE_SMOKE_CREATE_ATTEMPTS = 1
MAX_RECONCILIATION_PROBES = 3
_NS_PER_MINUTE = 60_000_000_000
_HEAD_RE = __import__("re").compile(r"^[0-9a-f]{7,64}$")
_ID_RE = __import__("re").compile(r"^[a-z][a-z0-9_-]*:sha256:[0-9a-f]{64}$")
_GEOBLOCK_URL = "https://polymarket.com/api/geoblock"
_SDK_ROUNDING_BY_TICK = {
    Decimal("0.1"): (3, 1, 2),
    Decimal("0.01"): (4, 2, 2),
    Decimal("0.005"): (5, 3, 2),
    Decimal("0.0025"): (6, 4, 2),
    Decimal("0.001"): (5, 3, 2),
    Decimal("0.0001"): (6, 4, 2),
}


def _json(value: object) -> str:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError, RecursionError):
        raise GatewayError("FIELD_VALUE_INVALID") from None


def _id(prefix: str, value: object) -> str:
    return prefix + hashlib.sha256(_json(value).encode("utf-8")).hexdigest()


def _nonempty_label(value: object, code: str = "FIELD_VALUE_INVALID") -> str:
    try:
        return _label(value)
    except GatewayError:
        raise GatewayError(code) from None


def _safe_decimal(value: object, code: str = "RISK_LIMIT_EXCEEDED") -> Decimal:
    try:
        if isinstance(value, Decimal):
            parsed = value
        elif isinstance(value, (int, float)) and not isinstance(value, bool):
            parsed = Decimal(str(value))
        elif isinstance(value, str):
            parsed = Decimal(value)
        else:
            raise ValueError
        if not parsed.is_finite() or parsed < 0:
            raise ValueError
        return parsed
    except (InvalidOperation, ValueError):
        raise GatewayError(code) from None


def _safe_int(value: object, code: str = "RISK_LIMIT_EXCEEDED") -> int:
    if isinstance(value, bool):
        raise GatewayError(code)
    try:
        parsed = int(value)
    except (TypeError, ValueError, OverflowError):
        raise GatewayError(code) from None
    if parsed < 0 or str(parsed) != str(value) and not isinstance(value, int):
        raise GatewayError(code)
    return parsed


def _head(value: object) -> str:
    if not isinstance(value, str) or _HEAD_RE.fullmatch(value) is None:
        raise GatewayError("HEAD_BINDING_INVALID")
    return value


def runtime_repository_identity(*, cwd: Path | None = None) -> tuple[Path, str]:
    """Derive the actual clean repository root and HEAD or fail closed."""
    try:
        root_result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"], cwd=cwd,
            capture_output=True, text=True, check=True, timeout=30,
        )
        root = Path(root_result.stdout.strip()).resolve(strict=True)
        head_result = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=root,
            capture_output=True, text=True, check=True, timeout=30,
        )
        status_result = subprocess.run(
            ["git", "status", "--porcelain=v1"], cwd=root,
            capture_output=True, text=True, check=True, timeout=30,
        )
        head = head_result.stdout.strip().lower()
    except Exception:
        raise GatewayError("HEAD_BINDING_INVALID") from None
    if _HEAD_RE.fullmatch(head) is None or status_result.stdout.strip():
        raise GatewayError("HEAD_BINDING_INVALID")
    return root, head


def canonical_gateway_store_path(repository_root: Path, public_wallet: str) -> Path:
    """One deterministic ledger location per repository and public wallet."""
    wallet = public_wallet.lower()
    if _ADDRESS_RE.fullmatch(wallet) is None:
        raise GatewayError("SIGNING_IDENTITY_INVALID")
    digest = hashlib.sha256(wallet.encode("ascii")).hexdigest()[:24]
    return (
        repository_root / "local_data" / "gate_c" /
        f"gate-c-wallet-{digest}.sqlite3"
    ).resolve(strict=False)


def _expected_signed_amounts(
    *, price: Decimal, size: Decimal, side: str, tick: Decimal
) -> tuple[int, int]:
    config = _SDK_ROUNDING_BY_TICK.get(tick)
    if config is None:
        raise GatewayError("ORDER_CONSTRAINT_INVALID")
    amount_decimals, _price_decimals, size_decimals = config

    def places(value: Decimal) -> int:
        exponent = value.normalize().as_tuple().exponent
        return 0 if isinstance(exponent, str) else max(0, -exponent)

    def rounded(value: Decimal, decimals: int, mode: str) -> Decimal:
        if places(value) <= decimals:
            return value
        return value.quantize(Decimal(10) ** -decimals, rounding=mode)

    base_size = rounded(size, size_decimals, ROUND_FLOOR)
    product = base_size * price
    if places(product) > amount_decimals:
        product = rounded(product, amount_decimals + 4, ROUND_CEILING)
        product = rounded(product, amount_decimals, ROUND_FLOOR)

    def units(value: Decimal) -> int:
        return int(
            (value * Decimal(1_000_000)).quantize(Decimal(1), rounding=ROUND_HALF_EVEN)
        )

    return (
        (units(product), units(base_size))
        if side == "BUY"
        else (units(base_size), units(product))
    )


@dataclass(frozen=True)
class GateCGeoblockProof:
    """Sanitized proof from the actual execution host's geoblock endpoint."""

    blocked: bool
    observed_time_ns: int
    valid_until_ns: int
    proof_id: str

    @classmethod
    def from_response(
        cls, response: Mapping[str, object], *, observed_time_ns: int,
        validity_ns: int = MAX_ACCOUNT_SNAPSHOT_AGE_NS,
    ) -> "GateCGeoblockProof":
        if not isinstance(response, Mapping) or type(response.get("blocked")) is not bool:
            raise GatewayError("ACCESS_PROOF_INVALID")
        _time(observed_time_ns)
        if (
            not isinstance(validity_ns, int)
            or isinstance(validity_ns, bool)
            or validity_ns <= 0
            or validity_ns > MAX_ACCOUNT_SNAPSHOT_AGE_NS
        ):
            raise GatewayError("ACCESS_PROOF_INVALID")
        valid_until = observed_time_ns + validity_ns
        proof = cls(False, observed_time_ns, valid_until, "")
        proof = cls(
            response["blocked"], observed_time_ns, valid_until,
            _id("geoblockproof:sha256:", {
                "blocked": response["blocked"],
                "observed_time_ns": observed_time_ns,
                "valid_until_ns": valid_until,
            }),
        )
        proof.validate()
        return proof

    def validate(self, *, now_ns: int | None = None, require_pass: bool = False) -> None:
        if type(self.blocked) is not bool:
            raise GatewayError("ACCESS_PROOF_INVALID")
        _time(self.observed_time_ns)
        _time(self.valid_until_ns)
        if self.valid_until_ns <= self.observed_time_ns:
            raise GatewayError("ACCESS_PROOF_INVALID")
        if self.valid_until_ns - self.observed_time_ns > MAX_ACCOUNT_SNAPSHOT_AGE_NS:
            raise GatewayError("ACCESS_PROOF_INVALID")
        expected = _id("geoblockproof:sha256:", {
            "blocked": self.blocked,
            "observed_time_ns": self.observed_time_ns,
            "valid_until_ns": self.valid_until_ns,
        })
        if self.proof_id != expected:
            raise GatewayError("ACCESS_PROOF_INVALID")
        if now_ns is not None:
            _time(now_ns)
            if now_ns < self.observed_time_ns or now_ns > self.valid_until_ns:
                raise GatewayError("ACCESS_PROOF_STALE")
        if require_pass and self.blocked:
            raise GatewayError("ACCESS_NOT_ELIGIBLE")


def query_geoblock(*, url: str = _GEOBLOCK_URL, now_ns: int | None = None) -> GateCGeoblockProof:
    """Perform one bounded official GET; failures are sanitized and fail closed."""
    observed = time.time_ns() if now_ns is None else now_ns
    _time(observed)
    if url != _GEOBLOCK_URL:
        raise GatewayError("ACCESS_PROOF_INVALID")
    try:
        request = Request(url, method="GET", headers={"Accept": "application/json"})
        with urlopen(request, timeout=5) as response:  # noqa: S310 - fixed official GET
            if getattr(response, "status", 200) != 200:
                raise GatewayError("ACCESS_PROOF_UNAVAILABLE")
            payload = json.loads(response.read(64 * 1024).decode("utf-8"))
        return GateCGeoblockProof.from_response(payload, observed_time_ns=observed)
    except GatewayError:
        raise
    except Exception:
        raise GatewayError("ACCESS_PROOF_UNAVAILABLE") from None


@dataclass(frozen=True)
class GateCMarketMetadata:
    market_id: str
    condition_id: str
    token_id: str
    exchange: str = "exchange"
    active: bool = True
    accepting_orders: bool = True
    binary: bool = True
    orderbook_enabled: bool = True
    neg_risk: bool = False
    delayed: bool = False
    tick_size: str = "0.01"
    minimum_order_size: str = "1"
    fee_rate_bps: str = "0"
    observed_time_ns: int = 0
    valid_until_ns: int = 0

    @classmethod
    def from_constraints(cls, constraints: VenueConstraints) -> "GateCMarketMetadata":
        constraints.validate()
        return cls(
            constraints.market_id,
            constraints.condition_id,
            constraints.token_id,
            exchange=constraints.exchange,
            accepting_orders=constraints.access_state == "ELIGIBLE",
            neg_risk=constraints.neg_risk,
            tick_size=constraints.tick_size,
            minimum_order_size=constraints.minimum_order_size,
            observed_time_ns=constraints.observed_time_ns,
            valid_until_ns=constraints.valid_until_ns,
        )

    def validate(self, *, now_ns: int | None = None) -> None:
        for value in (self.market_id, self.condition_id, self.token_id):
            _nonempty_label(value, "MARKET_METADATA_INVALID")
        if self.exchange != "exchange":
            raise GatewayError("MARKET_NOT_ELIGIBLE")
        if any(type(value) is not bool for value in (
            self.active, self.accepting_orders, self.binary, self.orderbook_enabled,
            self.neg_risk, self.delayed,
        )) or self.neg_risk or self.delayed:
            raise GatewayError("MARKET_NOT_ELIGIBLE")
        tick = _decimal(self.tick_size, positive=True)
        if tick not in _SDK_ROUNDING_BY_TICK:
            raise GatewayError("MARKET_METADATA_INVALID")
        _decimal(self.minimum_order_size, positive=True)
        fee_rate = _decimal(self.fee_rate_bps)
        if fee_rate < 0:
            raise GatewayError("MARKET_METADATA_INVALID")
        _time(self.observed_time_ns)
        _time(self.valid_until_ns)
        if self.valid_until_ns < self.observed_time_ns:
            raise GatewayError("MARKET_METADATA_INVALID")
        if self.valid_until_ns - self.observed_time_ns > MAX_ACCOUNT_SNAPSHOT_AGE_NS:
            raise GatewayError("MARKET_METADATA_INVALID")
        if now_ns is not None and not self.observed_time_ns <= now_ns <= self.valid_until_ns:
            raise GatewayError("MARKET_METADATA_STALE")
        if not self.active or not self.accepting_orders or not self.binary or not self.orderbook_enabled:
            raise GatewayError("MARKET_NOT_ELIGIBLE")


@dataclass(frozen=True)
class CanaryRiskEnvelope:
    """Hard-coded maxima; no caller/config/env value can widen them."""

    max_canary_wallet_pusd: str = "50.00"
    max_gross_live_exposure_pusd: str = "20.00"
    max_per_market_exposure_pusd: str = "15.00"
    max_per_order_committed_pusd: str = "10.00"
    max_active_markets: int = MAX_ACTIVE_MARKETS
    max_simultaneous_open_orders: int = MAX_SIMULTANEOUS_OPEN_ORDERS
    max_create_attempts_per_session: int = MAX_CREATE_ATTEMPTS_PER_SESSION
    max_live_session_duration_minutes: int = MAX_LIVE_SESSION_DURATION_MINUTES
    max_realized_loss_per_utc_day_pusd: str = "5.00"
    max_canary_equity_drawdown_pusd: str = "7.50"
    max_cumulative_canary_loss_pusd: str = "10.00"

    def validate(self) -> None:
        expected = {
            "max_canary_wallet_pusd": MAX_CANARY_WALLET_PUSD,
            "max_gross_live_exposure_pusd": MAX_GROSS_LIVE_EXPOSURE_PUSD,
            "max_per_market_exposure_pusd": MAX_PER_MARKET_EXPOSURE_PUSD,
            "max_per_order_committed_pusd": MAX_PER_ORDER_COMMITTED_PUSD,
            "max_realized_loss_per_utc_day_pusd": MAX_REALIZED_LOSS_PER_UTC_DAY_PUSD,
            "max_canary_equity_drawdown_pusd": MAX_CANARY_EQUITY_DRAWDOWN_PUSD,
            "max_cumulative_canary_loss_pusd": MAX_CUMULATIVE_CANARY_LOSS_PUSD,
        }
        for name, maximum in expected.items():
            if _safe_decimal(getattr(self, name), "RISK_ENVELOPE_INVALID") != maximum:
                raise GatewayError("RISK_ENVELOPE_INVALID")
        if (
            self.max_active_markets != MAX_ACTIVE_MARKETS
            or self.max_simultaneous_open_orders != MAX_SIMULTANEOUS_OPEN_ORDERS
            or self.max_create_attempts_per_session != MAX_CREATE_ATTEMPTS_PER_SESSION
            or self.max_live_session_duration_minutes != MAX_LIVE_SESSION_DURATION_MINUTES
        ):
            raise GatewayError("RISK_ENVELOPE_INVALID")

    @property
    def envelope_id(self) -> str:
        self.validate()
        return _id("canaryrisk:sha256:", asdict(self))


@dataclass
class GateCStrategyQualification:
    """Interactive, exact-head, single-use provenance assertion."""

    qualification_id: str
    repository_head: str
    binding: PaperStrategyBinding
    assessment: ExecutableEdgeAssessment
    cost_model: ExecutionCostModel
    paper_store_head: str
    paper_session_id: str
    paper_reconciliation_state: str
    operator_nonce: str
    issued_at_ns: int
    valid_until_ns: int
    issued_interactively: bool = True
    _consumed: bool = False

    @classmethod
    def issue(
        cls,
        *,
        repository_head: str,
        binding: PaperStrategyBinding,
        assessment: ExecutableEdgeAssessment,
        cost_model: ExecutionCostModel,
        paper_store_path: Path,
        operator_nonce: str,
        issued_at_ns: int,
        operator_is_tty: bool | None = None,
    ) -> "GateCStrategyQualification":
        if operator_is_tty is None:
            import sys
            operator_is_tty = bool(getattr(sys.stdin, "isatty", lambda: False)())
        if operator_is_tty is not True:
            raise GatewayError("QUALIFICATION_REQUIRES_TTY")
        _head(repository_head)
        _root, actual_head = runtime_repository_identity()
        if repository_head != actual_head:
            raise GatewayError("HEAD_BINDING_INVALID")
        _time(issued_at_ns)
        _nonempty_label(operator_nonce, "QUALIFICATION_INVALID")
        try:
            validate_strategy_binding(binding)
            validate_assessment(assessment)
            validate_execution_cost_model(cost_model)
        except Exception:
            raise GatewayError("QUALIFICATION_INVALID") from None
        if (
            assessment.status != "EXECUTABLE_EDGE_PASS"
            or not assessment.wp173_evaluation_eligible
            or assessment.cost_model_id != cost_model.cost_model_id
            or binding.assessment_id != assessment.assessment_id
            or binding.cost_model_id != cost_model.cost_model_id
            or not binding.simulated_paper_only
        ):
            raise GatewayError("QUALIFICATION_INVALID")
        store: PaperStore | None = None
        try:
            store = PaperStore(paper_store_path)
            if store.reconciliation_blocked:
                raise GatewayError("PAPER_RECONCILIATION_BLOCKED")
            state_mapping, events, head = store.recovery_snapshot()
            if state_mapping is None or head is None or not events:
                raise GatewayError("PAPER_EVIDENCE_INVALID")
            state = _replay_journal(events)
            if state.binding != binding or state.control_state != "RUNNING":
                raise GatewayError("PAPER_EVIDENCE_INVALID")
            paper_session_id = state.session_id
            paper_head = head.event_hash
        except GatewayError:
            raise
        except PaperTradingError:
            raise GatewayError("PAPER_EVIDENCE_INVALID") from None
        except Exception:
            raise GatewayError("PAPER_EVIDENCE_INVALID") from None
        finally:
            try:
                if store is not None:
                    store.close()
            except Exception:
                pass
        valid_until_ns = issued_at_ns + QUALIFICATION_VALIDITY_MINUTES * _NS_PER_MINUTE
        preimage = {
            "repository_head": repository_head,
            "binding_id": binding.binding_id,
            "assessment_id": assessment.assessment_id,
            "cost_model_id": cost_model.cost_model_id,
            "paper_store_head": paper_head,
            "paper_session_id": paper_session_id,
            "paper_reconciliation_state": "HEALTHY",
            "operator_nonce": operator_nonce,
            "issued_at_ns": issued_at_ns,
            "valid_until_ns": valid_until_ns,
            "issued_interactively": True,
        }
        return cls(
            _id("gatecqualification:sha256:", preimage), repository_head, binding,
            assessment, cost_model, paper_head, paper_session_id, "HEALTHY",
            operator_nonce, issued_at_ns, valid_until_ns, True,
        )

    create = issue

    def validate(self, *, now_ns: int | None = None) -> None:
        _head(self.repository_head)
        try:
            validate_strategy_binding(self.binding)
            validate_assessment(self.assessment)
            validate_execution_cost_model(self.cost_model)
        except Exception:
            raise GatewayError("QUALIFICATION_INVALID") from None
        if (
            self.assessment.status != "EXECUTABLE_EDGE_PASS"
            or not self.assessment.wp173_evaluation_eligible
            or self.binding.assessment_id != self.assessment.assessment_id
            or self.binding.cost_model_id != self.cost_model.cost_model_id
            or self.assessment.cost_model_id != self.cost_model.cost_model_id
            or not self.binding.simulated_paper_only
            or self.paper_reconciliation_state != "HEALTHY"
            or not self.issued_interactively
            or not isinstance(self.operator_nonce, str)
            or not self.operator_nonce
            or _ID_RE.fullmatch(self.qualification_id) is None
            or _ID_RE.fullmatch(self.paper_store_head) is None
            or _ID_RE.fullmatch(self.paper_session_id) is None
        ):
            raise GatewayError("QUALIFICATION_INVALID")
        _time(self.issued_at_ns)
        _time(self.valid_until_ns)
        if self.valid_until_ns != self.issued_at_ns + QUALIFICATION_VALIDITY_MINUTES * _NS_PER_MINUTE:
            raise GatewayError("QUALIFICATION_INVALID")
        expected = _id("gatecqualification:sha256:", {
            "repository_head": self.repository_head,
            "binding_id": self.binding.binding_id,
            "assessment_id": self.assessment.assessment_id,
            "cost_model_id": self.cost_model.cost_model_id,
            "paper_store_head": self.paper_store_head,
            "paper_session_id": self.paper_session_id,
            "paper_reconciliation_state": self.paper_reconciliation_state,
            "operator_nonce": self.operator_nonce,
            "issued_at_ns": self.issued_at_ns,
            "valid_until_ns": self.valid_until_ns,
            "issued_interactively": self.issued_interactively,
        })
        if self.qualification_id != expected:
            raise GatewayError("QUALIFICATION_INVALID")
        if now_ns is not None:
            _time(now_ns)
            if now_ns < self.issued_at_ns or now_ns > self.valid_until_ns:
                raise GatewayError("QUALIFICATION_EXPIRED")

    def consume(self, *, now_ns: int) -> None:
        self.validate(now_ns=now_ns)
        if self._consumed:
            raise GatewayError("QUALIFICATION_ALREADY_USED")
        self._consumed = True


@dataclass(frozen=True)
class GateCArmReceipt:
    arm_receipt_id: str
    repository_head: str
    store_head: str
    public_signer: str
    public_wallet: str
    qualification_id: str
    market_id: str
    condition_id: str
    token_id: str
    risk_envelope_id: str
    geoblock_proof_id: str
    account_evidence_id: str
    operator_nonce: str
    issued_at_ns: int
    valid_until_ns: int

    def to_public_mapping(self) -> dict[str, object]:
        return asdict(self)

    @property
    def receipt_id(self) -> str:
        return self.arm_receipt_id

    def validate(self, *, now_ns: int | None = None) -> None:
        _head(self.repository_head)
        _head(self.store_head)
        if _ADDRESS_RE.fullmatch(self.public_signer) is None or _ADDRESS_RE.fullmatch(self.public_wallet) is None:
            raise GatewayError("ARM_RECEIPT_INVALID")
        for value in (self.market_id, self.condition_id, self.token_id, self.operator_nonce):
            _nonempty_label(value, "ARM_RECEIPT_INVALID")
        for value in (
            self.qualification_id, self.risk_envelope_id, self.geoblock_proof_id,
            self.account_evidence_id,
        ):
            if not isinstance(value, str) or _ID_RE.fullmatch(value) is None:
                raise GatewayError("ARM_RECEIPT_INVALID")
        _time(self.issued_at_ns)
        _time(self.valid_until_ns)
        if self.valid_until_ns != self.issued_at_ns + ARM_RECEIPT_VALIDITY_MINUTES * _NS_PER_MINUTE:
            raise GatewayError("ARM_RECEIPT_INVALID")
        if now_ns is not None and not self.issued_at_ns <= now_ns <= self.valid_until_ns:
            raise GatewayError("ARM_RECEIPT_EXPIRED")
        expected = _id("gatecarm:sha256:", {
            key: value for key, value in self.to_public_mapping().items()
            if key != "arm_receipt_id"
        })
        if self.arm_receipt_id != expected:
            raise GatewayError("ARM_RECEIPT_INVALID")


@dataclass(frozen=True)
class GateCCanaryReceipt:
    receipt_id: str
    repository_head: str
    arm_receipt_id: str
    attempt_id: str
    outcome: str
    response_status: str
    venue_order_id: str | None
    market_id: str
    token_id: str
    create_attempt_count: int
    capital_at_risk_pusd: str
    capital_committed_pusd: str
    reconciliation_state: str
    residual_position_state: str
    halted: bool
    issued_at_ns: int
    valid_until_ns: int

    def to_public_mapping(self) -> dict[str, object]:
        return asdict(self)

    def validate(self, *, now_ns: int | None = None) -> None:
        _head(self.repository_head)
        for value in (self.receipt_id, self.arm_receipt_id, self.attempt_id):
            if not isinstance(value, str) or _ID_RE.fullmatch(value) is None:
                raise GatewayError("RECEIPT_INVALID")
        _nonempty_label(self.market_id, "RECEIPT_INVALID")
        _nonempty_label(self.token_id, "RECEIPT_INVALID")
        if self.outcome not in ("DEFINITIVE_ACCEPTED", "DEFINITIVE_REJECTED", "AMBIGUOUS"):
            raise GatewayError("RECEIPT_INVALID")
        if self.response_status not in ("live", "matched", "delayed", "rejected", "unknown"):
            raise GatewayError("RECEIPT_INVALID")
        if self.reconciliation_state not in ("HEALTHY", "REQUIRED", "BLOCKED", "DIVERGED"):
            raise GatewayError("RECEIPT_INVALID")
        if self.residual_position_state not in ("NONE", "PRESENT", "UNKNOWN"):
            raise GatewayError("RECEIPT_INVALID")
        if type(self.halted) is not bool or self.create_attempt_count != 1:
            raise GatewayError("RECEIPT_INVALID")
        at_risk = _safe_decimal(self.capital_at_risk_pusd, "RECEIPT_INVALID")
        committed = _safe_decimal(self.capital_committed_pusd, "RECEIPT_INVALID")
        if at_risk > MAX_PER_ORDER_COMMITTED_PUSD or committed > MAX_GROSS_LIVE_EXPOSURE_PUSD:
            raise GatewayError("RECEIPT_INVALID")
        if self.outcome == "DEFINITIVE_ACCEPTED" and self.response_status not in ("live", "matched"):
            raise GatewayError("RECEIPT_INVALID")
        if self.outcome == "DEFINITIVE_REJECTED" and self.response_status != "rejected":
            raise GatewayError("RECEIPT_INVALID")
        if self.outcome == "AMBIGUOUS" and self.response_status not in ("delayed", "unknown"):
            raise GatewayError("RECEIPT_INVALID")
        if self.outcome == "AMBIGUOUS" and self.residual_position_state == "NONE":
            raise GatewayError("RECEIPT_INVALID")
        if self.venue_order_id is not None and self.outcome == "DEFINITIVE_REJECTED":
            raise GatewayError("RECEIPT_INVALID")
        _time(self.issued_at_ns)
        _time(self.valid_until_ns)
        if self.valid_until_ns != self.issued_at_ns + ARM_RECEIPT_VALIDITY_MINUTES * _NS_PER_MINUTE:
            raise GatewayError("RECEIPT_INVALID")
        if self.venue_order_id is not None:
            _nonempty_label(self.venue_order_id, "RECEIPT_INVALID")
        if now_ns is not None:
            _time(now_ns)
            if not self.issued_at_ns <= now_ns <= self.valid_until_ns:
                raise GatewayError("RECEIPT_EXPIRED")
        expected = _id("gatecreceipt:sha256:", {
            key: value for key, value in self.to_public_mapping().items()
            if key != "receipt_id"
        })
        if self.receipt_id != expected:
            raise GatewayError("RECEIPT_INVALID")


def _checkpoint(**values: object) -> dict[str, object]:
    base: dict[str, object] = {
        "schema_version": "wp175-gate-c-checkpoint/1.0.0",
        "authority_state": "A0_DISABLED",
        "disable_reason": "INITIALIZED",
        "armed": False,
        "halted": False,
        "arm_receipt_id": None,
        "qualification_id": None,
        "attempt_id": None,
        "create_outcome": None,
        "response_status": None,
        "venue_order_id": None,
        "market_id": None,
        "condition_id": None,
        "token_id": None,
        "strategy_label": None,
        "create_attempt_count": 0,
        "capital_at_risk_pusd": "0",
        "capital_committed_pusd": "0",
        "realized_loss_pusd": "0",
        "drawdown_pusd": "0",
        "reconciliation_state": "REQUIRED",
        "residual_position_state": "UNKNOWN",
        "access_state": "UNKNOWN",
        "receipt_id": None,
        "last_event_time_ns": 0,
    }
    base.update(values)
    return base


class GateCSession:
    """One manually armed foreground canary session."""

    def __init__(
        self,
        gateway: ProtectedExecutionGateway,
        gate_b_session: GateBSession,
        qualification: GateCStrategyQualification,
        arm_receipt: GateCArmReceipt,
        market: GateCMarketMetadata,
        risk: CanaryRiskEnvelope,
    ) -> None:
        self._gateway = gateway
        self._gate_b = gate_b_session
        self._qualification = qualification
        self._arm_receipt = arm_receipt
        self._market = market
        self._risk = risk
        self._session_id = arm_receipt.arm_receipt_id
        arm_receipt.validate()
        market.validate()
        risk.validate()

    @classmethod
    def arm(
        cls,
        gateway: ProtectedExecutionGateway,
        gate_b_session: GateBSession,
        qualification: GateCStrategyQualification,
        *,
        market: GateCMarketMetadata | VenueConstraints,
        geoblock: GateCGeoblockProof,
        operator_nonce: str | None = None,
        account_snapshot: Mapping[str, object] | None = None,
        now_ns: int | None = None,
        risk: CanaryRiskEnvelope | None = None,
    ) -> "GateCSession":
        if type(gateway) is not ProtectedExecutionGateway or type(gate_b_session) is not GateBSession:
            raise GatewayError("GATE_C_SESSION_INVALID")
        now = time.time_ns() if now_ns is None else now_ns
        _time(now)
        if gateway.state.authority_state == "A3_RESTRICTED_LIVE":
            raise GatewayError("ALREADY_ARMED")
        if gateway.state.reconciliation_state != "HEALTHY":
            raise GatewayError("RECONCILIATION_REQUIRED")
        prior_checkpoint = gateway.state.gate_c_checkpoint or {}
        if (
            prior_checkpoint.get("halted") is True
            and prior_checkpoint.get("reconciliation_state") != "HEALTHY"
            or prior_checkpoint.get("create_outcome") == "AMBIGUOUS"
            or prior_checkpoint.get("residual_position_state") in ("PRESENT", "UNKNOWN")
            and prior_checkpoint.get("create_attempt_count", 0) != 0
        ):
            raise GatewayError("RECONCILIATION_REQUIRED")
        if getattr(gate_b_session, "_gateway", None) is not gateway:
            raise GatewayError("GATE_B_STORE_REQUIRED")
        if getattr(gate_b_session, "_wallet_lock", None) is None or not gate_b_session._wallet_lock.active:
            raise GatewayError("GATE_B_OWNERSHIP_REQUIRED")
        try:
            signer = gate_b_session.public_signer
            wallet = gate_b_session.public_wallet
        except Exception:
            raise GatewayError("SIGNING_IDENTITY_INVALID") from None
        repository_root, actual_head = runtime_repository_identity()
        if qualification.repository_head != actual_head:
            raise GatewayError("HEAD_BINDING_INVALID")
        if gateway.store_path != canonical_gateway_store_path(repository_root, wallet):
            raise GatewayError("CANONICAL_LEDGER_REQUIRED")
        if (
            gateway.state.public_signer is not None
            and gateway.state.public_signer != signer
            or gateway.state.public_funder is not None
            and gateway.state.public_funder != wallet
        ):
            raise GatewayError("SIGNING_IDENTITY_INVALID")
        if type(qualification) is not GateCStrategyQualification:
            raise GatewayError("QUALIFICATION_INVALID")
        if type(geoblock) is not GateCGeoblockProof:
            raise GatewayError("ACCESS_PROOF_INVALID")
        qualification.validate(now_ns=now)
        geoblock.validate(now_ns=now, require_pass=True)
        if isinstance(market, VenueConstraints):
            active_market = GateCMarketMetadata.from_constraints(market)
        elif type(market) is GateCMarketMetadata:
            active_market = market
        else:
            raise GatewayError("MARKET_METADATA_INVALID")
        active_market.validate(now_ns=now)
        nonce = qualification.operator_nonce if operator_nonce is None else operator_nonce
        if nonce != qualification.operator_nonce:
            raise GatewayError("OPERATOR_NONCE_INVALID")
        risk = CanaryRiskEnvelope() if risk is None else risk
        if type(risk) is not CanaryRiskEnvelope:
            raise GatewayError("RISK_ENVELOPE_INVALID")
        risk.validate()
        if account_snapshot is not None:
            raise GatewayError("ACCOUNT_SNAPSHOT_INVALID")
        raw_snapshot = gate_b_session.account_snapshot()
        if not isinstance(raw_snapshot, Mapping):
            raise GatewayError("ACCOUNT_SNAPSHOT_INVALID")
        snapshot = dict(raw_snapshot)
        required_snapshot_fields = (
            "collateral_balance", "allowance_by_exchange", "open_orders",
            "account_trades", "positions", "position_quantities",
            "market_exposures_pusd", "gross_exposure_pusd",
            "committed_exposure_pusd", "realized_loss_pusd", "drawdown_pusd",
            "cumulative_loss_pusd", "active_markets",
        )
        if any(field not in snapshot for field in required_snapshot_fields):
            raise GatewayError("ACCOUNT_SNAPSHOT_INVALID")
        snapshot["observed_time_ns"] = now
        if "observed_time_ns" in snapshot:
            observed = snapshot["observed_time_ns"]
            if not isinstance(observed, int) or isinstance(observed, bool):
                raise GatewayError("ACCOUNT_SNAPSHOT_INVALID")
            if observed > now or now - observed > MAX_ACCOUNT_SNAPSHOT_AGE_NS:
                raise GatewayError("ACCOUNT_SNAPSHOT_STALE")
        else:
            raise GatewayError("ACCOUNT_SNAPSHOT_STALE")
        for identity_key, expected in (("public_signer", signer), ("signer", signer), ("public_wallet", wallet), ("wallet", wallet)):
            if identity_key in snapshot and snapshot[identity_key] != expected:
                raise GatewayError("SIGNING_IDENTITY_INVALID")
        balance = _safe_decimal(snapshot.get("collateral_balance", "0"), "ACCOUNT_SNAPSHOT_INVALID")
        if balance > MAX_CANARY_WALLET_PUSD:
            raise GatewayError("RISK_LIMIT_EXCEEDED")
        open_orders = _safe_int(snapshot.get("open_orders"), "ACCOUNT_SNAPSHOT_INVALID")
        account_trades = _safe_int(snapshot.get("account_trades"), "ACCOUNT_SNAPSHOT_INVALID")
        positions = _safe_int(snapshot.get("positions"), "ACCOUNT_SNAPSHOT_INVALID")
        if open_orders != 0:
            raise GatewayError("RISK_LIMIT_EXCEEDED")
        snapshot.update({
            "open_orders": open_orders,
            "account_trades": account_trades,
            "positions": positions,
        })
        # Reuse the same authoritative Gate-B account evidence for the live arm
        # and make its durable cancel path eligible.  No raw response is kept.
        gate_b_record = getattr(gate_b_session, "_record_reconciliation", None)
        if callable(gate_b_record):
            gate_b_record(snapshot)
        account_id = _id("canaryaccount:sha256:", {
            "collateral_balance": _canonical_decimal(balance),
            "open_orders": open_orders,
            "account_trades": account_trades,
            "positions": positions,
        })
        store_head = gateway.head
        valid_until = now + ARM_RECEIPT_VALIDITY_MINUTES * _NS_PER_MINUTE
        preimage = {
            "repository_head": qualification.repository_head,
            "store_head": store_head,
            "public_signer": gate_b_session.public_signer,
            "public_wallet": gate_b_session.public_wallet,
            "qualification_id": qualification.qualification_id,
            "market_id": active_market.market_id,
            "condition_id": active_market.condition_id,
            "token_id": active_market.token_id,
            "risk_envelope_id": risk.envelope_id,
            "geoblock_proof_id": geoblock.proof_id,
            "account_evidence_id": account_id,
            "operator_nonce": nonce,
            "issued_at_ns": now,
            "valid_until_ns": valid_until,
        }
        arm = GateCArmReceipt(_id("gatecarm:sha256:", preimage), **{k: preimage[k] for k in preimage})
        arm.validate(now_ns=now)
        realized_loss = max(
            _safe_decimal(snapshot["realized_loss_pusd"]),
            _safe_decimal(prior_checkpoint.get("realized_loss_pusd", "0")),
        )
        drawdown = max(
            _safe_decimal(snapshot["drawdown_pusd"]),
            _safe_decimal(prior_checkpoint.get("drawdown_pusd", "0")),
        )
        cumulative_loss = max(
            _safe_decimal(snapshot["cumulative_loss_pusd"]),
            _safe_decimal(prior_checkpoint.get("cumulative_loss_pusd", "0")),
        )
        checkpoint = _checkpoint(
            authority_state="A3_RESTRICTED_LIVE",
            disable_reason="",
            armed=True,
            halted=False,
            arm_receipt_id=arm.arm_receipt_id,
            qualification_id=qualification.qualification_id,
            market_id=active_market.market_id,
            condition_id=active_market.condition_id,
            token_id=active_market.token_id,
            strategy_label=qualification.binding.strategy_label,
            reconciliation_state="HEALTHY",
            residual_position_state="NONE",
            access_state="ELIGIBLE",
            realized_loss_pusd=_canonical_decimal(realized_loss),
            drawdown_pusd=_canonical_decimal(drawdown),
            cumulative_loss_pusd=_canonical_decimal(cumulative_loss),
            last_event_time_ns=now,
        )
        gateway.record_gate_c_event(
            "GATE_C_ARMED", checkpoint,
            issuer=_GATE_C_EVENT_ISSUER, event_time_ns=now,
        )
        qualification.consume(now_ns=now)
        return cls(gateway, gate_b_session, qualification, arm, active_market, risk)

    def _require_live(self, now_ns: int) -> Mapping[str, object]:
        _time(now_ns)
        self._arm_receipt.validate(now_ns=now_ns)
        checkpoint = self._gateway.state.gate_c_checkpoint or {}
        if (
            self._gateway.state.authority_state != "A3_RESTRICTED_LIVE"
            or checkpoint.get("armed") is not True
            or checkpoint.get("halted") is True
            or checkpoint.get("arm_receipt_id") != self._arm_receipt.arm_receipt_id
            or _safe_int(checkpoint.get("create_attempt_count", 0))
            >= MAX_CREATE_ATTEMPTS_PER_SESSION
        ):
            raise GatewayError("CANARY_NOT_ARMED")
        if now_ns - self._arm_receipt.issued_at_ns > MAX_LIVE_SESSION_DURATION_MINUTES * _NS_PER_MINUTE:
            raise GatewayError("LIVE_SESSION_EXPIRED")
        return checkpoint

    def _risk_check(
        self,
        *,
        side: str,
        quantity: Decimal,
        notional: Decimal,
        snapshot: Mapping[str, object],
        reduce_only: bool,
    ) -> tuple[Decimal, Decimal]:
        if side not in ("BUY", "SELL"):
            raise GatewayError("ORDER_CONSTRAINT_INVALID")
        if side == "SELL" and not reduce_only:
            raise GatewayError("OVERSELL_FORBIDDEN")
        required = {
            "collateral_balance", "gross_exposure_pusd", "market_exposure_pusd",
            "committed_exposure_pusd", "realized_loss_pusd", "drawdown_pusd",
            "cumulative_loss_pusd", "active_markets", "open_orders",
        }
        if not required.issubset(snapshot):
            raise GatewayError("ACCOUNT_SNAPSHOT_INVALID")
        wallet = _safe_decimal(snapshot["collateral_balance"])
        gross = _safe_decimal(snapshot["gross_exposure_pusd"])
        market = _safe_decimal(snapshot["market_exposure_pusd"])
        committed = _safe_decimal(snapshot["committed_exposure_pusd"])
        daily = max(
            _safe_decimal(snapshot["realized_loss_pusd"]),
            _safe_decimal((self._gateway.state.gate_c_checkpoint or {}).get("realized_loss_pusd", "0")),
        )
        drawdown = max(
            _safe_decimal(snapshot["drawdown_pusd"]),
            _safe_decimal((self._gateway.state.gate_c_checkpoint or {}).get("drawdown_pusd", "0")),
        )
        cumulative = max(
            _safe_decimal(snapshot["cumulative_loss_pusd"]),
            _safe_decimal((self._gateway.state.gate_c_checkpoint or {}).get("cumulative_loss_pusd", "0")),
        )
        active_markets = _safe_int(snapshot["active_markets"])
        open_orders = _safe_int(snapshot["open_orders"])
        if not reduce_only:
            allowance_by_exchange = snapshot.get("allowance_by_exchange")
            if not isinstance(allowance_by_exchange, Mapping):
                raise GatewayError("INSUFFICIENT_ALLOWANCE")
            allowance_value = allowance_by_exchange.get(self._market.exchange)
            if wallet < notional:
                raise GatewayError("INSUFFICIENT_BALANCE")
            if allowance_value is None or _safe_decimal(allowance_value) < notional:
                raise GatewayError("INSUFFICIENT_ALLOWANCE")
        if not reduce_only:
            if (
                wallet > MAX_CANARY_WALLET_PUSD
                or notional > MAX_PER_ORDER_COMMITTED_PUSD
                or gross + notional > MAX_GROSS_LIVE_EXPOSURE_PUSD
                or market + notional > MAX_PER_MARKET_EXPOSURE_PUSD
                or committed + notional > MAX_GROSS_LIVE_EXPOSURE_PUSD
                or active_markets > MAX_ACTIVE_MARKETS
                or active_markets >= MAX_ACTIVE_MARKETS and market == 0
                or open_orders >= MAX_SIMULTANEOUS_OPEN_ORDERS
                or daily + notional > MAX_REALIZED_LOSS_PER_UTC_DAY_PUSD
                or drawdown + notional > MAX_CANARY_EQUITY_DRAWDOWN_PUSD
                or cumulative + notional > MAX_CUMULATIVE_CANARY_LOSS_PUSD
            ):
                raise GatewayError("RISK_LIMIT_EXCEEDED")
        if side == "SELL" and reduce_only:
            if "position_quantity" not in snapshot:
                raise GatewayError("ACCOUNT_SNAPSHOT_INVALID")
            position = _safe_decimal(snapshot["position_quantity"])
            if quantity > position:
                raise GatewayError("OVERSELL_FORBIDDEN")
        return wallet, committed + (Decimal(0) if reduce_only else notional)

    def create_limit_order(
        self,
        *,
        price: str,
        size: str,
        side: str = "BUY",
        post_only: bool = False,
        expiration: int | None = None,
        event_time_ns: int | None = None,
        account_snapshot: Mapping[str, object] | None = None,
        reduce_only: bool = False,
        order_identity: str | None = None,
    ) -> GateCCanaryReceipt:
        now = time.time_ns() if event_time_ns is None else event_time_ns
        checkpoint = self._require_live(now)
        if type(post_only) is not bool or type(reduce_only) is not bool:
            raise GatewayError("UNSUPPORTED_ORDER_INSTRUCTION")
        if expiration is not None and (
            not isinstance(expiration, int) or isinstance(expiration, bool) or expiration <= 0
        ):
            raise GatewayError("UNSUPPORTED_ORDER_INSTRUCTION")
        if order_identity is not None and _ID_RE.fullmatch(order_identity) is None:
            raise GatewayError("ORDER_IDENTITY_CONFLICT")
        if self._market.token_id != checkpoint.get("token_id"):
            raise GatewayError("MARKET_BINDING_INVALID")
        price_dec = _decimal(price, positive=True)
        size_dec = _decimal(size, positive=True)
        tick = _decimal(self._market.tick_size, positive=True)
        minimum = _decimal(self._market.minimum_order_size, positive=True)
        if price_dec > 1 or price_dec % tick != 0 or size_dec < minimum:
            raise GatewayError("ORDER_CONSTRAINT_INVALID")
        prepared = next(
            (
                item for item in self._gateway.state.prepared_orders
                if item.order_identity == order_identity
            ),
            None,
        )
        if prepared is None and order_identity is None:
            candidates = [
                item for item in self._gateway.state.prepared_orders
                if item.token_id == self._market.token_id
                and item.market_id == self._market.market_id
            ]
            if len(candidates) == 1:
                prepared = candidates[0]
                order_identity = prepared.order_identity
        if prepared is None:
            raise GatewayError("ORDER_NOT_PREPARED")
        prepared_request = dict(prepared.would_submit)
        if (
            prepared.token_id != self._market.token_id
            or prepared.market_id != self._market.market_id
            or prepared.condition_id != self._market.condition_id
            or prepared.side != side
            or prepared.post_only != post_only
            or prepared.expiration != expiration
            or prepared.quantity != _canonical_decimal(size_dec)
            or prepared.limit_price != _canonical_decimal(price_dec)
            or prepared_request.get("asset_id") != self._market.token_id
        ):
            raise GatewayError("ORDER_IDENTITY_CONFLICT")
        notional = price_dec * size_dec
        if account_snapshot is not None:
            raise GatewayError("ACCOUNT_SNAPSHOT_INVALID")
        live_snapshot = dict(self._gate_b.account_snapshot())
        quantities = live_snapshot.get("position_quantities", {})
        exposures = live_snapshot.get("market_exposures_pusd", {})
        if not isinstance(quantities, Mapping) or not isinstance(exposures, Mapping):
            raise GatewayError("ACCOUNT_SNAPSHOT_INVALID")
        live_snapshot["position_quantity"] = quantities.get(self._market.token_id, "0")
        live_snapshot["market_exposure_pusd"] = exposures.get(self._market.condition_id, "0")
        wallet, committed = self._risk_check(
            side=side, quantity=size_dec, notional=notional,
            snapshot=live_snapshot,
            reduce_only=reduce_only,
        )
        request = {
            "repository_head": self._arm_receipt.repository_head,
            "store_head": self._gateway.head,
            "public_signer": self._arm_receipt.public_signer,
            "public_wallet": self._arm_receipt.public_wallet,
            "qualification_id": self._qualification.qualification_id,
            "strategy_binding_id": self._qualification.binding.binding_id,
            "order_identity": prepared.order_identity,
            "asset_id": self._market.token_id,
            "price": _canonical_decimal(price_dec),
            "size": _canonical_decimal(size_dec),
            "side": side,
            "post_only": post_only,
            "expiration": expiration,
            "order_type": "LIMIT",
            "time_in_force": "GTC" if expiration is None else "GTD",
            "market_id": self._market.market_id,
            "condition_id": self._market.condition_id,
            "arm_receipt_id": self._arm_receipt.arm_receipt_id,
            "risk_envelope_id": self._risk.envelope_id,
            "reduce_only": reduce_only,
            "builder_code": None,
            "sequence": 1,
        }
        intent_id = _id("gatecintent:sha256:", request)
        permit = GateCLivePermit._issue(_GATE_C_ISSUER, intent_id)
        try:
            transport = self._gate_b.gate_c_transport(permit)
            signed = transport.build(
                asset_id=self._market.token_id,
                price=price_dec,
                size=size_dec,
                side=side,
                post_only=post_only,
                expiration=expiration,
            )
        except GatewayError:
            raise
        except Exception:
            raise GatewayError("SIGNING_FAILED") from None
        if type(signed) is not SignedOrder:
            raise GatewayError("SIGNING_FAILED")
        try:
            signed_economics = {
                "builder": str(signed.builder),
                "expiration": int(signed.expiration),
                "maker": str(signed.maker).lower(),
                "maker_amount": int(signed.maker_amount),
                "metadata": str(signed.metadata),
                "order_type": str(signed.order_type),
                "salt": int(signed.salt),
                "side": str(signed.side),
                "signature_type": int(signed.signature_type),
                "signer": str(signed.signer).lower(),
                "taker_amount": int(signed.taker_amount),
                "timestamp": int(signed.timestamp),
                "token_id": str(signed.token_id),
                "post_only": bool(signed.post_only),
            }
        except (AttributeError, TypeError, ValueError, OverflowError):
            raise GatewayError("SIGNING_FAILED") from None
        if (
            signed_economics["token_id"] != self._market.token_id
            or signed_economics["side"] != side
            or signed_economics["post_only"] is not post_only
            or signed_economics["signer"] != self._arm_receipt.public_signer
            or signed_economics["maker"] != self._arm_receipt.public_wallet
            or signed_economics["maker_amount"] <= 0
            or signed_economics["taker_amount"] <= 0
        ):
            raise GatewayError("SIGNED_ORDER_IDENTITY_MISMATCH")
        expected_maker, expected_taker = _expected_signed_amounts(
            price=price_dec, size=size_dec, side=side, tick=tick,
        )
        if (
            signed_economics["maker_amount"] != expected_maker
            or signed_economics["taker_amount"] != expected_taker
        ):
            raise GatewayError("SIGNED_ORDER_IDENTITY_MISMATCH")
        request["signed_order"] = signed_economics
        attempt_id = _id("gatecattempt:sha256:", request)
        started = dict(checkpoint)
        started.update({
            "attempt_id": attempt_id,
            "order_identity": prepared.order_identity,
            "mutation_identity": attempt_id,
            "mutation_request_digest": _sha("mutationrequest:sha256:", request),
            "side": side,
            "limit_price": _canonical_decimal(price_dec),
            "quantity": _canonical_decimal(size_dec),
            "post_only": post_only,
            "expiration": expiration,
            "reduce_only": reduce_only,
            "time_in_force": request["time_in_force"],
            "sequence": 1,
            "store_head": "gatewayjournal:sha256:" + str(request["store_head"]),
            "create_attempt_count": 1,
            "capital_at_risk_pusd": _canonical_decimal(notional),
            "capital_committed_pusd": _canonical_decimal(committed),
            "last_event_time_ns": now,
        })
        # This commit is the hard no-duplicate boundary: no transmit occurs
        # until the durable STARTED identity is accepted by GatewayStore.
        self._gateway.record_gate_c_event(
            "GATE_C_CREATE_STARTED", started,
            issuer=_GATE_C_EVENT_ISSUER, event_time_ns=now,
        )
        permit._consume(intent_id)
        try:
            response = transport.transmit(signed)
        except GatewayError:
            return self._finish_ambiguous(
                attempt_id, now, "unknown", notional, committed,
                order_identity=prepared.order_identity,
                prepared_request=prepared_request,
            )
        outcome, status, venue_order_id = self._classify(response)
        if outcome == "AMBIGUOUS":
            return self._finish_ambiguous(
                attempt_id, now, status, notional, committed,
                order_identity=prepared.order_identity,
                prepared_request=prepared_request,
                venue_order_id=venue_order_id,
            )
        post_create_read_ok = True
        if outcome == "DEFINITIVE_ACCEPTED":
            try:
                self._gate_b.account_snapshot()
            except GatewayError:
                post_create_read_ok = False
        request_digest = _sha("mutationrequest:sha256:", {
            "order_identity": prepared.order_identity,
            "operation": "CREATE",
            "request": prepared_request,
            "target_bindings": [],
        })
        mutation_id = _sha("mutationattempt:sha256:", {
            "order_identity": prepared.order_identity,
            "operation": "CREATE",
            "attempt_sequence": 1,
            "prior_reconciliation_state": "HEALTHY",
            "request_digest": request_digest,
            "request_target_bindings": [],
        })
        mutation = MutationAttempt(
            mutation_id, prepared.order_identity, "CREATE", 1, "HEALTHY", (), (), None,
            request_digest, True, outcome, venue_order_id, 200 if outcome == "DEFINITIVE_ACCEPTED" else 400,
            now, False,
        )
        final = dict(started)
        accepted = outcome == "DEFINITIVE_ACCEPTED"
        final.update({
            "authority_state": "A0_DISABLED",
            "disable_reason": (
                "CREATE_ACCEPTED_RECONCILIATION_REQUIRED"
                if accepted
                else "CANARY_ATTEMPT_COMPLETE"
            ),
            "armed": False,
            "create_outcome": outcome,
            "response_status": status,
            "venue_order_id": venue_order_id,
            "reconciliation_state": "BLOCKED" if accepted and not post_create_read_ok else "REQUIRED" if accepted else "HEALTHY",
            "residual_position_state": "UNKNOWN" if accepted else "NONE",
            "halted": accepted,
            "last_event_time_ns": now,
        })
        open_ids = list(self._gateway.state.venue_open_order_ids)
        if outcome == "DEFINITIVE_ACCEPTED" and status == "live" and venue_order_id:
            open_ids = sorted(set(open_ids) | {venue_order_id})
        self._gateway.record_gate_c_event(
            "GATE_C_CREATE_OUTCOME", final, event_time_ns=max(now, self._gateway.state.last_event_time_ns + 1),
            issuer=_GATE_C_EVENT_ISSUER,
            mutation_attempt=mutation, venue_open_order_ids=open_ids,
        )
        if outcome == "DEFINITIVE_ACCEPTED" and status == "live" and venue_order_id:
            # A resting accepted order is reduced through the existing durable
            # Gate-B cancel path in the same foreground command.  Any failure
            # is persisted as a halt; it is never retried blindly.
            try:
                cancel = self._gate_b.cancel_one(
                    request_target_ids=(venue_order_id,),
                    request_target_bindings=((venue_order_id, order_identity),),
                )
            except GatewayError:
                halted = dict(final)
                halted.update({
                    "authority_state": "A0_DISABLED",
                    "disable_reason": "CANCEL_RECONCILIATION_REQUIRED",
                    "halted": True,
                    "reconciliation_state": "BLOCKED",
                    "last_event_time_ns": max(now, self._gateway.state.last_event_time_ns + 1),
                })
                self._gateway.record_gate_c_event(
                    "GATE_C_HALTED", halted,
                    issuer=_GATE_C_EVENT_ISSUER,
                    event_time_ns=int(halted["last_event_time_ns"]),
                )
                return self._receipt(halted, int(halted["last_event_time_ns"]))
            if cancel.get("cancel_result") != "DEFINITIVE_ACCEPTED":
                halted = dict(final)
                halted.update({
                    "authority_state": "A0_DISABLED",
                    "disable_reason": "CANCEL_RECONCILIATION_REQUIRED",
                    "halted": True,
                    "reconciliation_state": "BLOCKED",
                    "last_event_time_ns": max(now, self._gateway.state.last_event_time_ns + 1),
                })
                self._gateway.record_gate_c_event(
                    "GATE_C_HALTED", halted,
                    issuer=_GATE_C_EVENT_ISSUER,
                    event_time_ns=int(halted["last_event_time_ns"]),
                )
                return self._receipt(halted, int(halted["last_event_time_ns"]))
            try:
                self._gate_b.account_snapshot()
            except GatewayError:
                halted = dict(final)
                halted.update({
                    "authority_state": "A0_DISABLED",
                    "disable_reason": "CANCEL_RECONCILIATION_REQUIRED",
                    "halted": True,
                    "reconciliation_state": "BLOCKED",
                    "last_event_time_ns": max(now, self._gateway.state.last_event_time_ns + 1),
                })
                self._gateway.record_gate_c_event(
                    "GATE_C_HALTED", halted,
                    issuer=_GATE_C_EVENT_ISSUER,
                    event_time_ns=int(halted["last_event_time_ns"]),
                )
                return self._receipt(halted, int(halted["last_event_time_ns"]))
            settled = dict(final)
            settled.update({
                "disable_reason": "CANCEL_ACCEPTED_RECONCILIATION_REQUIRED",
                "reconciliation_state": "REQUIRED",
                "residual_position_state": "UNKNOWN",
                "halted": True,
                "last_event_time_ns": max(now, self._gateway.state.last_event_time_ns + 1),
            })
            self._gateway.record_gate_c_event(
                "GATE_C_HALTED", settled,
                issuer=_GATE_C_EVENT_ISSUER,
                event_time_ns=int(settled["last_event_time_ns"]),
            )
            return self._receipt(settled, int(settled["last_event_time_ns"]))
        return self._receipt(final, now)

    def _classify(self, response: object) -> tuple[str, str, str | None]:
        if type(response) is AcceptedOrder:
            status = str(response.status)
            try:
                order_id = _nonempty_label(str(response.order_id), "CREATE_RESPONSE_INVALID")
            except GatewayError:
                return "AMBIGUOUS", "unknown", None
            if status in ("live", "matched"):
                return "DEFINITIVE_ACCEPTED", status, order_id
            return "AMBIGUOUS", "delayed", order_id
        if type(response) is RejectedOrder:
            if str(response.code) not in {
                "unmatched", "market_not_ready", "not_enough_balance", "invalid_nonce",
                "invalid_expiration", "post_only_would_cross", "post_only_mode",
                "fok_not_filled", "fak_not_filled", "unknown",
            }:
                return "AMBIGUOUS", "unknown", None
            return "DEFINITIVE_REJECTED", "rejected", None
        return "AMBIGUOUS", "unknown", None

    def _finish_ambiguous(
        self,
        attempt_id: str,
        now: int,
        status: str,
        notional: Decimal,
        committed: Decimal,
        *,
        order_identity: str,
        prepared_request: Mapping[str, object],
        venue_order_id: str | None = None,
    ) -> GateCCanaryReceipt:
        final = dict(self._gateway.state.gate_c_checkpoint or {})
        final.update({
            "authority_state": "A0_DISABLED",
            "disable_reason": "AMBIGUOUS_CREATE",
            "armed": False,
            "halted": True,
            "attempt_id": attempt_id,
            "create_attempt_count": 1,
            "create_outcome": "AMBIGUOUS",
            "response_status": status,
            "venue_order_id": venue_order_id,
            "capital_at_risk_pusd": _canonical_decimal(notional),
            "capital_committed_pusd": _canonical_decimal(committed),
            "reconciliation_state": "BLOCKED",
            "residual_position_state": "UNKNOWN",
            "last_event_time_ns": now,
        })
        request_digest = _sha("mutationrequest:sha256:", {
            "order_identity": order_identity,
            "operation": "CREATE",
            "request": dict(prepared_request),
            "target_bindings": [],
        })
        mutation_id = _sha("mutationattempt:sha256:", {
            "order_identity": order_identity,
            "operation": "CREATE",
            "attempt_sequence": 1,
            "prior_reconciliation_state": "HEALTHY",
            "request_digest": request_digest,
            "request_target_bindings": [],
        })
        mutation = MutationAttempt(
            mutation_id, order_identity, "CREATE", 1, "HEALTHY", (), (), None,
            request_digest, True, "AMBIGUOUS", venue_order_id,
            200 if venue_order_id is not None else None, now, False,
        )
        open_ids = list(self._gateway.state.venue_open_order_ids)
        if venue_order_id is not None:
            open_ids = sorted(set(open_ids) | {venue_order_id})
        self._gateway.record_gate_c_event(
            "GATE_C_CREATE_OUTCOME", final,
            issuer=_GATE_C_EVENT_ISSUER,
            event_time_ns=max(now, self._gateway.state.last_event_time_ns + 1),
            mutation_attempt=mutation,
            venue_open_order_ids=open_ids,
        )
        return self._receipt(final, now)

    def _receipt(self, checkpoint: Mapping[str, object], now: int) -> GateCCanaryReceipt:
        preimage = {
            "repository_head": self._arm_receipt.repository_head,
            "arm_receipt_id": self._arm_receipt.arm_receipt_id,
            "attempt_id": checkpoint.get("attempt_id"),
            "outcome": checkpoint.get("create_outcome"),
            "response_status": checkpoint.get("response_status") or "unknown",
            "venue_order_id": checkpoint.get("venue_order_id"),
            "market_id": checkpoint.get("market_id"),
            "token_id": checkpoint.get("token_id"),
            "create_attempt_count": 1,
            "capital_at_risk_pusd": checkpoint.get("capital_at_risk_pusd", "0"),
            "capital_committed_pusd": checkpoint.get("capital_committed_pusd", "0"),
            "reconciliation_state": checkpoint.get("reconciliation_state", "REQUIRED"),
            "residual_position_state": checkpoint.get("residual_position_state", "UNKNOWN"),
            "halted": bool(checkpoint.get("halted")),
            "issued_at_ns": now,
            "valid_until_ns": now + ARM_RECEIPT_VALIDITY_MINUTES * _NS_PER_MINUTE,
        }
        return GateCCanaryReceipt(_id("gatecreceipt:sha256:", preimage), **preimage)

    def cancel_resting_order(self, *, order_identity: str, venue_order_id: str, now_ns: int | None = None) -> Mapping[str, object]:
        now = time.time_ns() if now_ns is None else now_ns
        _time(now)
        if self._gateway.state.authority_state == "A3_RESTRICTED_LIVE":
            raise GatewayError("CANARY_STILL_ARMED")
        return self._gate_b.cancel_one(
            request_target_ids=(venue_order_id,),
            request_target_bindings=((venue_order_id, order_identity),),
        )

    def reconcile(self, *, adapter: object, event_time_ns: int) -> None:
        if type(adapter) is not OfficialSdkAuthenticatedReadAdapter:
            raise GatewayError("AUTHENTICATED_READ_ADAPTER_INVALID")
        self._gateway.reconcile(adapter=adapter, event_time_ns=event_time_ns)
        checkpoint = dict(self._gateway.state.gate_c_checkpoint or {})
        outcome = checkpoint.get("create_outcome")
        residual = checkpoint.get("residual_position_state", "UNKNOWN")
        reconciliation = self._gateway.state.reconciliation_state
        halted = reconciliation != "HEALTHY"
        if outcome == "DEFINITIVE_ACCEPTED":
            snapshot = adapter.query_account()
            venue_order_id = checkpoint.get("venue_order_id")
            order_identity = checkpoint.get("order_identity")
            filled = sum(
                (
                    _decimal(trade.quantity)
                    for trade in snapshot.recent_trades
                    if trade.venue_order_id == venue_order_id
                    and trade.order_identity == order_identity
                ),
                Decimal(0),
            )
            order = (
                adapter.query_order(venue_order_id)
                if isinstance(venue_order_id, str)
                else None
            )
            if filled > 0 or order is not None and _decimal(order.filled_quantity) > 0:
                residual = "PRESENT"
                reconciliation = "BLOCKED"
                halted = True
            elif order is not None and order.status == "CANCELED":
                residual = "NONE"
            else:
                residual = "UNKNOWN"
                reconciliation = "BLOCKED"
                halted = True
        elif outcome == "DEFINITIVE_REJECTED":
            residual = "NONE"
        elif outcome == "AMBIGUOUS":
            snapshot = adapter.query_account()
            venue_order_id = checkpoint.get("venue_order_id")
            order_identity = checkpoint.get("order_identity")
            order = (
                adapter.query_order(venue_order_id)
                if isinstance(venue_order_id, str)
                else None
            )
            filled = sum(
                (
                    _decimal(trade.quantity)
                    for trade in snapshot.recent_trades
                    if trade.venue_order_id == venue_order_id
                    and trade.order_identity == order_identity
                ),
                Decimal(0),
            )
            uniquely_bound = (
                order is not None
                and order.order_identity == order_identity
                and order.venue_order_id == venue_order_id
            )
            if filled > 0 or uniquely_bound and _decimal(order.filled_quantity) > 0:
                residual = "PRESENT"
                reconciliation = "BLOCKED"
                halted = True
            elif uniquely_bound and order.status == "CANCELED":
                residual = "NONE"
                reconciliation = self._gateway.state.reconciliation_state
                halted = reconciliation != "HEALTHY"
            else:
                residual = "UNKNOWN"
                reconciliation = "BLOCKED"
                halted = True
        checkpoint.update({
            "authority_state": "A0_DISABLED",
            "armed": False,
            "halted": halted,
            "reconciliation_state": reconciliation,
            "residual_position_state": residual,
            "access_state": self._gateway.state.access_state,
            "last_event_time_ns": event_time_ns,
        })
        self._gateway.record_gate_c_event(
            "GATE_C_RECONCILED", checkpoint,
            issuer=_GATE_C_EVENT_ISSUER,
            event_time_ns=max(event_time_ns, self._gateway.state.last_event_time_ns + 1),
        )

    def reconcile_bounded(
        self,
        *,
        geoblock: GateCGeoblockProof,
        event_time_ns: int | None = None,
    ) -> Mapping[str, object]:
        """Run the fixed official-read recovery sequence; never resend CREATE."""
        start = time.time_ns() if event_time_ns is None else event_time_ns
        _time(start)
        geoblock.validate(now_ns=start)
        checkpoint = dict(self._gateway.state.gate_c_checkpoint or {})
        venue_order_id = checkpoint.get("venue_order_id")
        order_identity = checkpoint.get("order_identity")
        identities = (
            {str(venue_order_id): str(order_identity)}
            if isinstance(venue_order_id, str) and isinstance(order_identity, str)
            else {}
        )
        cancel_attempted = False
        for probe in range(1, MAX_RECONCILIATION_PROBES + 1):
            observed = start + probe
            try:
                adapter = self._gate_b.gate_c_reconciliation_adapter(
                    _GATE_C_ISSUER,
                    observed_time_ns=observed,
                    order_identity_by_venue_id=identities,
                    geoblock_eligible=not geoblock.blocked,
                )
                self.reconcile(adapter=adapter, event_time_ns=observed)
            except GatewayError:
                checkpoint = dict(self._gateway.state.gate_c_checkpoint or checkpoint)
                checkpoint.update({
                    "authority_state": "A0_DISABLED",
                    "armed": False,
                    "halted": True,
                    "reconciliation_state": "BLOCKED",
                    "reconciliation_probe_count": probe,
                    "last_event_time_ns": max(
                        observed, self._gateway.state.last_event_time_ns + 1
                    ),
                })
                self._gateway.record_gate_c_event(
                    "GATE_C_HALTED", checkpoint,
                    issuer=_GATE_C_EVENT_ISSUER,
                    event_time_ns=int(checkpoint["last_event_time_ns"]),
                )
                continue
            checkpoint = dict(self._gateway.state.gate_c_checkpoint or {})
            checkpoint["reconciliation_probe_count"] = probe
            checkpoint["last_event_time_ns"] = max(
                observed, self._gateway.state.last_event_time_ns + 1
            )
            terminal = (
                checkpoint.get("reconciliation_state") == "HEALTHY"
                and checkpoint.get("residual_position_state") == "NONE"
            )
            cancelable = (
                not cancel_attempted
                and checkpoint.get("create_outcome") == "AMBIGUOUS"
                and isinstance(venue_order_id, str)
                and isinstance(order_identity, str)
                and venue_order_id in self._gateway.state.venue_open_order_ids
                and checkpoint.get("residual_position_state") == "UNKNOWN"
            )
            if cancelable:
                cancel_attempted = True
                try:
                    self._gate_b.cancel_one(
                        request_target_ids=(venue_order_id,),
                        request_target_bindings=((venue_order_id, order_identity),),
                    )
                except GatewayError:
                    pass
            self._gateway.record_gate_c_event(
                "GATE_C_RECONCILED" if terminal else "GATE_C_HALTED",
                checkpoint,
                issuer=_GATE_C_EVENT_ISSUER,
                event_time_ns=int(checkpoint["last_event_time_ns"]),
            )
            if terminal:
                break
        return self.cockpit_projection()

    def halt(self, *, reason: str = "OPERATOR_KILL", event_time_ns: int | None = None) -> None:
        now = time.time_ns() if event_time_ns is None else event_time_ns
        _nonempty_label(reason)
        checkpoint = dict(self._gateway.state.gate_c_checkpoint or {})
        checkpoint.update({
            "authority_state": "A0_DISABLED",
            "disable_reason": reason,
            "armed": False,
            "halted": True,
            "reconciliation_state": "BLOCKED",
            "last_event_time_ns": now,
        })
        self._gateway.record_gate_c_event(
            "GATE_C_HALTED", checkpoint,
            issuer=_GATE_C_EVENT_ISSUER, event_time_ns=now,
        )

    kill = halt

    @property
    def arm_receipt(self) -> GateCArmReceipt:
        return self._arm_receipt

    @property
    def market(self) -> GateCMarketMetadata:
        return self._market

    def cockpit_projection(self) -> dict[str, object]:
        checkpoint = dict(self._gateway.state.gate_c_checkpoint or {})
        return {
            "restricted_live_available": self._gateway.state.authority_state == "A3_RESTRICTED_LIVE",
            "authority_state": self._gateway.state.authority_state,
            "armed": bool(checkpoint.get("armed")),
            "halted": bool(checkpoint.get("halted")),
            "arm_receipt_id": checkpoint.get("arm_receipt_id"),
            "qualification_id": checkpoint.get("qualification_id"),
            "attempt_id": checkpoint.get("attempt_id"),
            "create_outcome": checkpoint.get("create_outcome"),
            "response_status": checkpoint.get("response_status"),
            "venue_order_id": checkpoint.get("venue_order_id"),
            "market_id": checkpoint.get("market_id"),
            "token_id": checkpoint.get("token_id"),
            "create_attempt_count": int(checkpoint.get("create_attempt_count", 0)),
            "capital_at_risk_pusd": checkpoint.get("capital_at_risk_pusd", "0"),
            "capital_committed_pusd": checkpoint.get("capital_committed_pusd", "0"),
            "reconciliation_state": checkpoint.get("reconciliation_state"),
            "read_only": True,
        }


# Friendly aliases used by operator-facing callers and tests.
ArmReceipt = GateCArmReceipt
CanaryReceipt = GateCCanaryReceipt
GeoblockProof = GateCGeoblockProof
RestrictedLiveCanary = GateCSession
