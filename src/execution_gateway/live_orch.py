"""S10-LIVE-ORCH-01 restricted live orchestration + first-live canary core.

One manual foreground orchestrator (``preflight`` / ``canary`` / ``reconcile``)
over the existing protected boundaries:

    exact current ExploratoryGateCPermit + exact ExecutionIntent
    + strict execution-host currentness / NTP PASS + fresh geoblock PASS
    + exact authenticated signer / Deposit Wallet identity
    + fresh complete bounded account truth + fresh compatible public venue
    + hard capital envelope + healthy canonical LIVE-ORCH ledger
        -> durable LIVE_ORCH_ADMISSION -> durable CREATE_STARTED
        -> at most one economic transmit -> authoritative reconciliation
        -> terminal / settlement-pending / blocked -> no-new-exposure

The first-live economic CREATE side is BUY only.  There is no daemon, scheduler,
WebSocket recovery authority, automatic CREATE retry or auto scaling.  This
module never constructs a raw SDK client: account reads go through Gate-B and
every CREATE/CANCEL transmit goes through the Gate-C LIVE-ORCH boundary.
Merged code is dormant; a real canary requires a separate exact-merge
authorization.  LIVE TRADING STATUS remains DISABLED.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass, field
from decimal import ROUND_CEILING, Decimal
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import threading
import time
from typing import Callable, Mapping, Sequence

from src.execution_feasibility import (
    ExecutionFeasibilityAssessment,
    ExecutionFeasibilityError,
    ExecutionIntent,
    PublicExecutionVenueSnapshot,
    assess_execution_feasibility,
    fetch_public_venue_snapshot,
    validate_execution_intent,
)
from src.exploratory_gate_c import (
    ExploratoryGateCError,
    ExploratoryGateCPermit,
    validate_exploratory_gate_c_permit,
)

from .gate_b import (
    GateBIdentityPolicy,
    GateBSession,
    InteractiveGateBSecretProvider,
    LiveOrchAccountTruth,
    LiveOrchOpenOrder,
    WalletSessionLock,
    _LIVE_ORCH_ISSUER,
    create_deposit_wallet_client,
)
from .gate_c import (
    GateCGeoblockProof,
    LiveOrchMutationBoundary,
    LiveOrchOrderSpec,
    query_geoblock,
)
from .gateway import (
    LIVE_ORCH_CLEAN_TERMINAL_STATES,
    GatewayError,
    ProtectedExecutionGateway,
    _ADDRESS_RE,
    _LIVE_ORCH_EVENT_ISSUER,
    _canonical_decimal,
    _sha,
    _time,
    _validate_replay,
    live_orch_episode_id,
    validate_live_orch_checkpoint,
)
from .store import GatewayStore, GatewayStoreError

# ---------------------------------------------------------------------------
# Frozen human capital envelope (no input may widen these values)
# ---------------------------------------------------------------------------

AUTHORIZED_ACCOUNT_CAPITAL_USD = Decimal("100")
TYPICAL_INITIAL_ORDER_USD = (Decimal("3"), Decimal("5"))  # operator target only
SINGLE_ORDER_WORST_CASE_MAX_USD = Decimal("5")
MAX_TOTAL_EARLY_COMMITMENT_USD = Decimal("30")
MIN_FREE_COLLATERAL_RESERVE_USD = Decimal("70")
AUTO_SCALING = False
MAX_OBSERVED_REALIZED_PNL_LOSS_USD = Decimal("5")
MAX_OBSERVED_POSITION_PNL_DRAWDOWN_USD = Decimal("7.5")
MAX_OBSERVED_CUMULATIVE_CANARY_LOSS_USD = Decimal("10")
FIRST_CANARY_SIDE = "BUY"
MAX_CREATE_PER_CANARY = 1
PASSIVE_OBSERVATION_MAX_SECONDS = 60
PASSIVE_POLL_INTERVAL_SECONDS = 1
MAX_CANCEL_RECONCILE_ROUNDS = 3
LIVE_ORCH_CONFIRMATION_PHRASE = "CONFIRM-LIVE-ORCH-ONE-BUY-CANARY"
HOST_CURRENTNESS_SCHEMA_ID = "polymarket-execution-host-currentness"
HOST_CURRENTNESS_SCHEMA_VERSION = "1.0.0"
DEFAULT_STATE_ROOT = Path("/var/lib/polymarket")
_USD_QUANTUM = Decimal("0.00001")
_NONTERMINAL_TRADE_STATUSES = ("MATCHED", "MATCHED_NOT_BROADCASTED", "MINED", "RETRYING")
_LIVE_ORDER_STATUSES = ("LIVE", "OPEN", "UNMATCHED", "DELAYED")
_DONE_ORDER_STATUSES = ("MATCHED", "FILLED", "CANCELED", "CANCELLED", "EXPIRED", "INVALID")
_UNRESOLVED_STATES = (
    "ADMITTED",
    "CREATE_STARTED",
    "CREATE_AMBIGUOUS",
    "CANCEL_STARTED",
    "RECONCILIATION_BLOCKED",
)


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _text(value: Decimal) -> str:
    if value < 0:
        raise GatewayError("ACCOUNT_COMMITMENT_INCONSISTENT")
    return _canonical_decimal(value)


@dataclass(frozen=True)
class LiveOrchCapitalEnvelope:
    """Hard Karl risk envelope; validation rejects any widened value."""

    authorized_account_capital_usd: str = "100"
    single_order_worst_case_max_usd: str = "5"
    max_total_early_commitment_usd: str = "30"
    min_free_collateral_reserve_usd: str = "70"
    auto_scaling: bool = False
    max_observed_realized_pnl_loss_usd: str = "5"
    max_observed_position_pnl_drawdown_usd: str = "7.5"
    max_observed_cumulative_canary_loss_usd: str = "10"

    def validate(self) -> None:
        expected = {
            "authorized_account_capital_usd": AUTHORIZED_ACCOUNT_CAPITAL_USD,
            "single_order_worst_case_max_usd": SINGLE_ORDER_WORST_CASE_MAX_USD,
            "max_total_early_commitment_usd": MAX_TOTAL_EARLY_COMMITMENT_USD,
            "min_free_collateral_reserve_usd": MIN_FREE_COLLATERAL_RESERVE_USD,
            "max_observed_realized_pnl_loss_usd": MAX_OBSERVED_REALIZED_PNL_LOSS_USD,
            "max_observed_position_pnl_drawdown_usd": MAX_OBSERVED_POSITION_PNL_DRAWDOWN_USD,
            "max_observed_cumulative_canary_loss_usd": MAX_OBSERVED_CUMULATIVE_CANARY_LOSS_USD,
        }
        try:
            widened = any(_d(getattr(self, key)) != value for key, value in expected.items())
        except Exception:
            widened = True
        if widened or self.auto_scaling is not False or AUTO_SCALING is not False:
            raise GatewayError("CAPITAL_ENVELOPE_INVALID")


# ---------------------------------------------------------------------------
# Closed results
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LiveOrchResult:
    """Sanitized closed command result (never a secret, signature or raw error)."""

    command: str
    status: str
    code: str
    episode_id: str | None = None
    episode_state: str | None = None
    create_transmits: int = 0
    details: Mapping[str, object] = field(default_factory=dict)

    def to_mapping(self) -> dict[str, object]:
        value = asdict(self)
        value["details"] = dict(self.details)
        return value


class _Stop(Exception):
    """Internal fail-closed exit carrying one closed code."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


# ---------------------------------------------------------------------------
# Execution-host currentness (read-only, strict, exact deployed release)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class HostCurrentnessConfig:
    repository_root: Path
    binding_file: Path
    active_release: Path
    unit_dir: Path
    ssh_port: int
    expected_release_sha: str


def run_execution_host_currentness(config: HostCurrentnessConfig) -> Mapping[str, object]:
    """Run the merged read-only strict currentness evaluator (fixed argv, no shell)."""
    argv = [
        sys.executable,
        str(config.repository_root / "tools" / "deployment" / "runtime_baseline.py"),
        "execution-host-currentness",
        "--binding-file", str(config.binding_file),
        "--active-release", str(config.active_release),
        "--expected-sha", config.expected_release_sha,
        "--unit-dir", str(config.unit_dir),
        "--strict",
        "--ssh-port", str(int(config.ssh_port)),
    ]
    try:
        completed = subprocess.run(
            argv, capture_output=True, text=True, timeout=120, check=False
        )
        document = json.loads(completed.stdout.strip().splitlines()[-1])
    except Exception:
        raise GatewayError("HOST_CURRENTNESS_UNAVAILABLE") from None
    if completed.returncode != 0 or not isinstance(document, dict):
        raise GatewayError("HOST_NOT_CURRENT")
    return document


_HOST_ID_RE = re.compile(r"pmhost-v1:[0-9a-f]{64}")
_BOOT_ID_RE = re.compile(r"pmboot-v1:[0-9a-f]{64}")
_HEX64_RE = re.compile(r"[0-9a-f]{64}")
_RELEASE_SHA_RE = re.compile(r"[0-9a-f]{40}")


def validate_host_currentness(document: object, expected_release_sha: str) -> str:
    """Require strict EXECUTION_HOST_CURRENT for the exact release; return its id.

    No fixed sleep can substitute for this PASS: NTP must be synchronized, the
    firewall SSH-only and the persistent state present for the exact release.
    """
    if (
        not isinstance(document, Mapping)
        or not isinstance(expected_release_sha, str)
        or _RELEASE_SHA_RE.fullmatch(expected_release_sha) is None
        or document.get("schema_id") != HOST_CURRENTNESS_SCHEMA_ID
        or document.get("schema_version") != HOST_CURRENTNESS_SCHEMA_VERSION
        or document.get("status") != "EXECUTION_HOST_CURRENT"
        or document.get("verification_mode") != "strict"
        or document.get("bound_release_sha") != expected_release_sha
        or document.get("active_release_sha") != expected_release_sha
        or document.get("ntp_state") != "synchronized"
        or document.get("firewall_state") != "ssh_only_inbound"
        or document.get("persistent_state") != "present"
        or not isinstance(document.get("host_instance_id"), str)
        or _HOST_ID_RE.fullmatch(document["host_instance_id"]) is None
        or not isinstance(document.get("boot_instance_id"), str)
        or _BOOT_ID_RE.fullmatch(document["boot_instance_id"]) is None
        or not isinstance(document.get("release_manifest_sha256"), str)
        or _HEX64_RE.fullmatch(document["release_manifest_sha256"]) is None
    ):
        raise GatewayError("HOST_NOT_CURRENT")
    try:
        return _sha("hostcurrentness:sha256:", dict(document))
    except Exception:
        raise GatewayError("HOST_NOT_CURRENT") from None


# ---------------------------------------------------------------------------
# Exact permit / intent authority (read-only; never regenerated or widened)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PermitAuthority:
    permit: ExploratoryGateCPermit
    intent: ExecutionIntent
    principal: Decimal


def check_first_canary_side(permit: object) -> ExploratoryGateCPermit:
    """Strict permit validation, then the BUY-only rule before anything else."""
    try:
        validated = validate_exploratory_gate_c_permit(permit)
    except ExploratoryGateCError:
        raise GatewayError("PERMIT_INVALID") from None
    if validated.side != FIRST_CANARY_SIDE:
        raise GatewayError("SIDE_UNSUPPORTED_FIRST_CANARY")
    return validated


def verify_permit_authority(
    permit: object,
    intent: object,
    *,
    lifecycle_store_path: Path,
    hermes_store_path: Path,
    now_ns: int,
) -> PermitAuthority:
    """Consume the exact current permit read-only and revalidate its lineage."""
    from src.research_runtime.hermes_controlled_runtime.strategy_manager import (
        load_hermes_strategy_manager_store,
    )
    from src.strategy_lifecycle import load_strategy_lifecycle_store

    _time(now_ns)
    validated = check_first_canary_side(permit)
    if type(intent) is not ExecutionIntent:
        raise GatewayError("EXECUTION_INTENT_INVALID")
    if validated.exact_intent_only is not True:
        raise GatewayError("PERMIT_INVALID")
    if not validated.issued_at_ns <= now_ns < validated.valid_until_ns:
        raise GatewayError("PERMIT_EXPIRED")
    try:
        lifecycle = load_strategy_lifecycle_store(lifecycle_store_path)
    except Exception:
        raise GatewayError("LIFECYCLE_STORE_INVALID") from None
    snapshot = lifecycle.snapshot
    if lifecycle.is_valid is not True or snapshot is None:
        raise GatewayError("LIFECYCLE_STORE_INVALID")
    version = snapshot.version_by_id(validated.strategy_version_id)
    allocation = snapshot.allocation_of(validated.strategy_version_id)
    if (
        version is None
        or snapshot.store_head_entry_hash != validated.lifecycle_store_head_entry_hash
        or snapshot.active_policy_id != validated.active_policy_id
        or allocation is None
        or allocation.allocation_id != validated.allocation_id
        or not allocation.is_active_at(now_ns)
    ):
        raise GatewayError("PERMIT_NOT_CURRENT")
    try:
        validate_execution_intent(intent, strategy_version=version)
    except ExecutionFeasibilityError:
        raise GatewayError("EXECUTION_INTENT_INVALID") from None
    try:
        hermes = load_hermes_strategy_manager_store(hermes_store_path)
        latest = hermes.latest_assessment_id(validated.strategy_version_id)
    except Exception:
        raise GatewayError("HERMES_STORE_INVALID") from None
    if latest != validated.hermes_assessment_id:
        raise GatewayError("PERMIT_NOT_CURRENT")
    exact = (
        intent.execution_intent_id == validated.execution_intent_id
        and intent.strategy_version_id == validated.strategy_version_id
        and (intent.gamma_market_id, intent.condition_id, intent.token_id)
        == (validated.gamma_market_id, validated.condition_id, validated.token_id)
        and intent.side == validated.side
        and intent.execution_style == validated.execution_style
        and intent.order_type == validated.order_type
        and intent.requested_shares == validated.requested_shares
        and intent.price_limit == validated.price_limit
        and intent.post_only == validated.post_only
        and intent.gtd_expiration_unix_s == validated.gtd_expiration_unix_s
    )
    principal = _d(intent.requested_shares) * _d(intent.price_limit)
    if not exact or principal != _d(validated.authorized_order_notional_usd):
        raise GatewayError("PERMIT_INTENT_MISMATCH")
    return PermitAuthority(validated, intent, principal)


# ---------------------------------------------------------------------------
# Fresh venue revalidation / drift contract and fee reserve
# ---------------------------------------------------------------------------


def seconds_delay_applicability(intent: object, snapshot: PublicExecutionVenueSnapshot) -> str:
    """The marketable-order delay gate (S10-LIVE-CANARY-01 section 4F).

    ``secondsDelay`` delays only MARKETABLE orders; a signed post-only order is rejected instead
    of taking.  An absent value is admissible solely for a post-only PASSIVE_MAKER GTC/GTD
    intent and is never read as zero; a known non-zero delay and every other intent fail closed.
    """
    if snapshot.seconds_delay == 0:
        return "CHECKED_ZERO"
    post_only_passive = (
        intent.execution_style == "PASSIVE_MAKER"
        and intent.post_only is True
        and intent.order_type in ("GTC", "GTD")
    )
    if snapshot.seconds_delay is None and post_only_passive:
        return "NOT_APPLICABLE_POST_ONLY"
    raise GatewayError("SECONDS_DELAY_UNSUPPORTED")


def revalidate_venue(
    authority: PermitAuthority,
    snapshot: PublicExecutionVenueSnapshot,
    *,
    evaluated_at_ns: int,
) -> ExecutionFeasibilityAssessment:
    """Fresh IDs/books may change; identity, intent and structure may not."""
    intent = authority.intent
    if type(snapshot) is not PublicExecutionVenueSnapshot:
        raise GatewayError("VENUE_SNAPSHOT_INVALID")
    if (snapshot.gamma_market_id, snapshot.condition_id, snapshot.token_id) != (
        intent.gamma_market_id,
        intent.condition_id,
        intent.token_id,
    ):
        raise GatewayError("VENUE_IDENTITY_DRIFT")
    try:
        assessment = assess_execution_feasibility(
            intent,
            snapshot,
            evaluated_at_ns=max(evaluated_at_ns, snapshot.acquisition_completed_ns),
        )
    except ExecutionFeasibilityError:
        raise GatewayError("VENUE_SNAPSHOT_INVALID") from None
    if (
        snapshot.active is not True
        or snapshot.closed is not False
        or snapshot.accepting_orders is not True
        or snapshot.enable_order_book is not True
    ):
        raise GatewayError("MARKET_NOT_ELIGIBLE")
    if snapshot.gamma_neg_risk is not False or snapshot.book_neg_risk is not False:
        raise GatewayError("NEG_RISK_UNSUPPORTED")
    seconds_delay_applicability(intent, snapshot)
    if assessment.tick_dimension != "PASS" or snapshot.book_tick_size is None:
        raise GatewayError("TICK_INCOMPATIBLE")
    # LIVE-ORCH independently rechecks both minimum-order dimensions.
    gamma_min = snapshot.gamma_min_order_notional_usd
    book_min = snapshot.book_min_order_size_raw
    if gamma_min is None or book_min is None:
        raise GatewayError("MINIMUM_ORDER_UNKNOWN")
    if authority.principal < _d(gamma_min) or _d(intent.requested_shares) < _d(book_min):
        raise GatewayError("MINIMUM_ORDER_NOT_MET")
    if assessment.minimum_order_dimension != "PASS":
        raise GatewayError("MINIMUM_ORDER_NOT_MET")
    if snapshot.fees_enabled is None or assessment.fee_exactness == "UNKNOWN":
        raise GatewayError("FEE_CONFIGURATION_UNKNOWN")
    if assessment.status not in ("FEASIBLE", "LIMITED"):
        raise GatewayError("VENUE_NOT_FEASIBLE")
    return assessment


def worst_case_fee_reserve(
    authority: PermitAuthority,
    snapshot: PublicExecutionVenueSnapshot,
    assessment: ExecutionFeasibilityAssessment,
) -> Decimal:
    """Zero for no-fee or a known taker-only maker order; aggressive uses 5dp bounds.

    The aggressive reserve is the fresh EXEC-FEAS conservative five-decimal upper
    bound, and never below the same fee schedule applied to the full requested
    shares at the worst price that the permit price limit allows.
    """
    exactness = assessment.fee_exactness
    if exactness in ("EXACT_ZERO_NO_FEES", "EXACT_ZERO_MAKER"):
        return Decimal(0)
    if exactness != "CONSERVATIVE_5DP_UPPER_BOUND" or assessment.fee_upper_bound_usd is None:
        raise GatewayError("FEE_CONFIGURATION_UNKNOWN")
    if snapshot.fee_rate is None or snapshot.fee_exponent is None:
        raise GatewayError("FEE_CONFIGURATION_UNKNOWN")
    rate, exponent = _d(snapshot.fee_rate), int(_d(snapshot.fee_exponent))
    worst_price = min(_d(authority.intent.price_limit), Decimal("0.5"))
    factor = (worst_price * (1 - worst_price)) ** exponent if exponent else Decimal(1)
    full = (_d(authority.intent.requested_shares) * rate * factor).quantize(
        _USD_QUANTUM, rounding=ROUND_CEILING
    )
    return max(_d(assessment.fee_upper_bound_usd), full)


# ---------------------------------------------------------------------------
# Authoritative reconciliation of one episode (one closed transition per step)
# ---------------------------------------------------------------------------


def _copy(value: object) -> dict:
    return json.loads(json.dumps(value))


def _blocked(episode: dict, reason: str) -> dict:
    episode["state"] = "RECONCILIATION_BLOCKED"
    episode["reconciliation"]["block_reason"] = reason
    return episode


def _episode_trade_records(venue_order_id: str, truth: LiveOrchAccountTruth) -> list[dict]:
    """Order-associated trades with their exact settlement status (no FAILED fill)."""
    records = []
    for trade in truth.trades:
        if trade.taker_order_id == venue_order_id:
            if trade.maker_fills:
                shares = sum((_d(fill.matched_amount) for fill in trade.maker_fills), Decimal(0))
                principal = sum(
                    (_d(fill.matched_amount) * _d(fill.price) for fill in trade.maker_fills),
                    Decimal(0),
                )
            else:
                shares = _d(trade.size)
                principal = _d(trade.size) * _d(trade.price)
        else:
            mine = [fill for fill in trade.maker_fills if fill.venue_order_id == venue_order_id]
            if not mine:
                continue
            shares = sum((_d(fill.matched_amount) for fill in mine), Decimal(0))
            principal = sum((_d(fill.matched_amount) * _d(fill.price) for fill in mine), Decimal(0))
        if shares <= 0:
            continue
        records.append(
            {
                "trade_id": trade.trade_id,
                "status": trade.status,
                "shares": _text(shares),
                "principal_usd": _text(principal),
            }
        )
    return records


def _discover_unattributed_orders(
    episode: Mapping[str, object],
    truth: LiveOrchAccountTruth,
    attributed: set[str],
) -> set[str]:
    """Order IDs on the episode token that no ledger episode already owns."""
    binding = episode["binding"]
    token = binding["token_id"]
    limit = _d(binding["price_limit"])
    requested = _d(binding["requested_shares"])
    found: set[str] = set()
    for order in truth.open_orders:
        if (
            order.venue_order_id not in attributed
            and order.token_id == token
            and order.side == "BUY"
            and _d(order.price) <= limit
            and _d(order.original_size) <= requested
        ):
            found.add(order.venue_order_id)
    for trade in truth.trades:
        if trade.token_id != token:
            continue
        if trade.trader_side == "TAKER" and trade.taker_order_id not in attributed:
            found.add(trade.taker_order_id)
        for fill in trade.maker_fills:
            if trade.trader_side == "MAKER" and fill.venue_order_id not in attributed:
                found.add(fill.venue_order_id)
    return found


def _fee_reconciliation(
    episode: dict,
    truth: LiveOrchAccountTruth,
    *,
    confirmed_principal: Decimal,
    concurrent: bool,
) -> None:
    recon = episode["reconciliation"]
    reserve = _d(episode["admission"]["worst_case_fee_reserve_usd"])
    if recon["fee_state"] in ("NOT_REQUIRED", "RECONCILED"):
        return
    if reserve == 0:
        recon["fee_state"], recon["actual_fee_usd"] = "NOT_REQUIRED", None
        return
    if confirmed_principal == 0:
        recon["fee_state"], recon["actual_fee_usd"] = "RECONCILED", "0"
        return
    # Attribute an actual fee only from dedicated-account pre/post collateral,
    # the confirmed principal and the absence of any concurrent mutation.
    delta = (
        _d(episode["admission"]["collateral_before_usd"])
        - _d(truth.collateral_balance)
        - confirmed_principal
    )
    if not concurrent and Decimal(0) <= delta <= reserve:
        recon["fee_state"], recon["actual_fee_usd"] = "RECONCILED", _text(delta)
    else:
        recon["fee_state"], recon["actual_fee_usd"] = "AMBIGUOUS", None


def reconcile_episode_step(
    episode: Mapping[str, object],
    truth: LiveOrchAccountTruth,
    *,
    attributed_order_ids: set[str],
    order_lookup: Callable[[str], LiveOrchOpenOrder],
    concurrent: bool,
    now_ns: int,
) -> dict:
    """Return the episode after exactly one legal closed transition (or unchanged)."""
    new = _copy(episode)
    state = new["state"]
    recon = new["reconciliation"]
    binding = new["binding"]
    if state in LIVE_ORCH_CLEAN_TERMINAL_STATES:
        return new
    if state == "ADMITTED":
        # No durable CREATE_STARTED means no transmit could have happened.
        new["state"] = "TERMINAL_NO_POSITION"
        reserve = _d(new["admission"]["worst_case_fee_reserve_usd"])
        recon["fee_state"] = "NOT_REQUIRED" if reserve == 0 else "RECONCILED"
        recon["actual_fee_usd"] = None if reserve == 0 else "0"
        return new
    if state == "CREATE_STARTED":
        # Possibly transmitted with no durable outcome: AMBIGUOUS, full reserve.
        new["state"] = "CREATE_AMBIGUOUS"
        new["create"]["outcome"] = "AMBIGUOUS"
        new["create"]["response_status"] = "unknown"
        return new
    if state == "CANCEL_STARTED":
        attempts = new["cancel_attempts"]
        if attempts and attempts[-1]["result"] is None:
            attempts[-1]["result"] = "AMBIGUOUS"
        new["state"] = "RECONCILING"
        recon["block_reason"] = None
        return new
    if state == "TERMINAL_KNOWN_POSITION":
        token_positions = [item for item in truth.positions if item.token_id == binding["token_id"]]
        closed = token_positions and all(
            _d(item.current_size) == 0 or item.status == "CLOSED" for item in token_positions
        )
        if closed:
            new["state"] = "TERMINAL_NO_POSITION"
        return new
    create = new["create"]
    venue_order_id = create["venue_order_id"]
    if venue_order_id is None:
        candidates = _discover_unattributed_orders(new, truth, attributed_order_ids)
        if len(candidates) > 1:
            return _blocked(new, "AMBIGUOUS_CREATE_UNATTRIBUTABLE")
        if not candidates:
            # Absence from the current REST snapshot, however long it lasts, is not
            # positive proof that the possibly transmitted CREATE was never accepted.
            # The episode stays unresolved with its full worst-case reserve.
            return new
        venue_order_id = candidates.pop()
        create["venue_order_id"] = venue_order_id
    recon["block_reason"] = None
    order = next(
        (item for item in truth.open_orders if item.venue_order_id == venue_order_id), None
    )
    if order is None:
        try:
            order = order_lookup(venue_order_id)
        except GatewayError:
            return _blocked(new, "ORDER_STATE_UNKNOWN")
    if (
        order.token_id != binding["token_id"]
        or order.side != "BUY"
        or _d(order.price) > _d(binding["price_limit"])
        or _d(order.original_size) > _d(binding["requested_shares"])
    ):
        return _blocked(new, "ORDER_IDENTITY_MISMATCH")
    if order.status in _LIVE_ORDER_STATUSES:
        live = True
        remainder = _d(order.original_size) - _d(order.size_matched)
    elif order.status in _DONE_ORDER_STATUSES:
        live, remainder = False, Decimal(0)
    else:
        return _blocked(new, "ORDER_STATE_UNKNOWN")
    previous = {item["trade_id"]: item for item in recon["trades"]}
    fresh = {item["trade_id"]: item for item in _episode_trade_records(venue_order_id, truth)}
    for trade_id, item in fresh.items():
        if item["status"] not in (
            "MATCHED", "MATCHED_NOT_BROADCASTED", "MINED", "RETRYING", "CONFIRMED", "FAILED",
        ):
            return _blocked(new, "TRADE_STATUS_UNKNOWN")
        prior = previous.get(trade_id)
        if prior is not None and prior["status"] in ("CONFIRMED", "FAILED") and prior != item:
            return _blocked(new, "TRADE_EVIDENCE_CONFLICT")
    merged = dict(previous)
    merged.update({key: value for key, value in fresh.items() if key not in previous
                   or previous[key]["status"] not in ("CONFIRMED", "FAILED")})
    trades = sorted(merged.values(), key=lambda item: item["trade_id"])
    confirmed_shares = sum((_d(t["shares"]) for t in trades if t["status"] == "CONFIRMED"), Decimal(0))
    pending_shares = sum(
        (_d(t["shares"]) for t in trades if t["status"] in _NONTERMINAL_TRADE_STATUSES), Decimal(0)
    )
    confirmed_principal = sum(
        (_d(t["principal_usd"]) for t in trades if t["status"] == "CONFIRMED"), Decimal(0)
    )
    principal_total = confirmed_principal + sum(
        (_d(t["principal_usd"]) for t in trades if t["status"] in _NONTERMINAL_TRADE_STATUSES),
        Decimal(0),
    )
    requested = _d(binding["requested_shares"])
    if (
        confirmed_shares + pending_shares + (remainder if live else 0) > requested
        or principal_total + remainder * _d(binding["price_limit"]) > _d(
            binding["authorized_order_notional_usd"]
        )
    ):
        return _blocked(new, "ACCOUNT_COMMITMENT_INCONSISTENT")
    recon["trades"] = trades
    recon["order_live"] = live
    recon["open_remainder_shares"] = _text(remainder if live else Decimal(0))
    missing_response_trades = set(create["trade_ids"]) - set(merged)
    if live:
        new["state"] = "RESTING"
    elif pending_shares > 0 or missing_response_trades:
        new["state"] = "SETTLEMENT_PENDING"
    elif confirmed_shares > 0:
        new["state"] = "TERMINAL_KNOWN_POSITION"
    else:
        new["state"] = "TERMINAL_NO_POSITION"
    if new["state"] in ("TERMINAL_KNOWN_POSITION", "TERMINAL_NO_POSITION"):
        _fee_reconciliation(
            new, truth, confirmed_principal=confirmed_principal, concurrent=concurrent
        )
    return new


# ---------------------------------------------------------------------------
# Deduplicated capital commitment, observed-PnL guards and hard risk checks
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AccountEvaluation:
    collateral: Decimal
    total_commitment: Decimal
    undebited_commitment: Decimal
    observed_realized_pnl_loss: Decimal
    observed_position_pnl_drawdown: Decimal
    observed_cumulative_canary_loss: Decimal
    allowance: Decimal | None
    blocking_codes: tuple[str, ...]


def evaluate_account(
    truth: LiveOrchAccountTruth, checkpoint: Mapping[str, object]
) -> AccountEvaluation:
    """TOTAL_EARLY_CAPITAL_COMMITTED with identity-based dedupe; never mark-to-market.

    Per token, confirmed plus nonterminal matched principal and the reported
    position entry cost describe the same shares, so the larger of the two is
    counted once.  Open BUY remainders, unreflected fee reserves and the full
    worst-case reserve of every unresolved episode are added.  ``current_value``
    is never read, so a mark-to-market decline cannot free commitment.
    """
    blocks: list[str] = []
    if truth.closed_only:
        blocks.append("ACCOUNT_CLOSE_ONLY")
    if checkpoint["restart_reconciliation_required"]:
        blocks.append("RESTART_RECONCILIATION_REQUIRED")
    episodes = list(checkpoint["episodes"])
    owned = {
        episode["create"]["venue_order_id"]
        for episode in episodes
        if isinstance(episode["create"], Mapping) and episode["create"]["venue_order_id"]
    }
    for order in truth.open_orders:
        if order.venue_order_id not in owned:
            blocks.append("ACCOUNT_UNKNOWN_OPEN_ORDER")
    undebited = Decimal(0)
    pending_total = Decimal(0)
    filled_by_token: dict[str, Decimal] = {}
    episode_tokens: set[str] = set()
    for episode in episodes:
        state = episode["state"]
        if state in LIVE_ORCH_CLEAN_TERMINAL_STATES:
            continue
        binding, admission = episode["binding"], episode["admission"]
        recon = episode["reconciliation"]
        token = binding["token_id"]
        episode_tokens.add(token)
        worst = _d(admission["worst_case_commitment_usd"])
        if state in _UNRESOLVED_STATES:
            blocks.append("UNRESOLVED_PRIOR_MUTATION")
            undebited += worst
            continue
        if state == "RESTING":
            blocks.append("RESTING_ORDER_PRESENT")
        elif state == "SETTLEMENT_PENDING":
            blocks.append("SETTLEMENT_NONTERMINAL")
        elif state in ("CREATE_ACCEPTED", "RECONCILING"):
            blocks.append("RECONCILIATION_REQUIRED")
        if recon["fee_state"] == "AMBIGUOUS":
            blocks.append("FEE_RECONCILIATION_AMBIGUOUS")
        remainder = _d(recon["open_remainder_shares"]) * _d(binding["price_limit"])
        filled = sum(
            (
                _d(trade["principal_usd"])
                for trade in recon["trades"]
                if trade["status"] != "FAILED"
            ),
            Decimal(0),
        )
        pending = sum(
            (
                _d(trade["principal_usd"])
                for trade in recon["trades"]
                if trade["status"] in _NONTERMINAL_TRADE_STATUSES
            ),
            Decimal(0),
        )
        fee = (
            _d(admission["worst_case_fee_reserve_usd"])
            if recon["fee_state"] in ("RESERVED", "AMBIGUOUS")
            else Decimal(0)
        )
        if remainder + filled > _d(admission["principal_notional_usd"]):
            blocks.append("ACCOUNT_COMMITMENT_INCONSISTENT")
            undebited += worst
            continue
        undebited += remainder + pending + fee
        pending_total += pending
        filled_by_token[token] = filled_by_token.get(token, Decimal(0)) + filled
    realized = Decimal(0)
    drawdown = Decimal(0)
    position_commitment = Decimal(0)
    entry_by_token: dict[str, Decimal] = {}
    for position in truth.positions:
        realized += max(-_d(position.realized_pnl), Decimal(0))
        drawdown += max(-_d(position.total_pnl), Decimal(0))
        if _d(position.current_size) <= 0:
            continue
        if position.token_id not in episode_tokens:
            blocks.append("ACCOUNT_POSITION_UNKNOWN")
            continue
        entry_by_token[position.token_id] = max(
            _d(position.total_cost_usdc),
            _d(position.entry_cost_usdc) + _d(position.entry_fees_usdc),
        )
    for token in set(filled_by_token) | set(entry_by_token):
        position_commitment += max(
            filled_by_token.get(token, Decimal(0)), entry_by_token.get(token, Decimal(0))
        )
    # Matched-but-unsettled principal is inside both the per-token filled amount
    # and the undebited total; count it once.
    total = position_commitment + undebited - pending_total
    allowance = dict(truth.allowance_by_exchange).get("exchange")
    return AccountEvaluation(
        collateral=_d(truth.collateral_balance),
        total_commitment=total,
        undebited_commitment=undebited,
        observed_realized_pnl_loss=realized,
        observed_position_pnl_drawdown=drawdown,
        observed_cumulative_canary_loss=max(realized, drawdown),
        allowance=None if allowance is None else _d(allowance),
        blocking_codes=tuple(dict.fromkeys(blocks)),
    )


@dataclass(frozen=True)
class AdmissionRisk:
    proposed_worst_case_commitment: Decimal
    projected_free_collateral: Decimal


def check_admission_risk(
    envelope: LiveOrchCapitalEnvelope,
    *,
    principal: Decimal,
    fee_reserve: Decimal,
    evaluation: AccountEvaluation,
) -> AdmissionRisk:
    """Independent hard pre-CREATE checks; unknown input fails closed."""
    envelope.validate()
    if evaluation.blocking_codes:
        raise GatewayError(evaluation.blocking_codes[0])
    proposed = principal + fee_reserve
    if principal <= 0 or fee_reserve < 0:
        raise GatewayError("ORDER_ECONOMICS_INVALID")
    if proposed > SINGLE_ORDER_WORST_CASE_MAX_USD:
        raise GatewayError("SINGLE_ORDER_LIMIT_EXCEEDED")
    if evaluation.total_commitment + proposed > MAX_TOTAL_EARLY_COMMITMENT_USD:
        raise GatewayError("AGGREGATE_COMMITMENT_LIMIT_EXCEEDED")
    projected_free = evaluation.collateral - evaluation.undebited_commitment - proposed
    if projected_free < MIN_FREE_COLLATERAL_RESERVE_USD:
        raise GatewayError("FREE_COLLATERAL_RESERVE_VIOLATED")
    debited = evaluation.total_commitment - evaluation.undebited_commitment
    if evaluation.collateral + max(debited, Decimal(0)) > AUTHORIZED_ACCOUNT_CAPITAL_USD:
        raise GatewayError("ACCOUNT_CAPITAL_BASIS_EXCEEDED")
    if (
        evaluation.observed_realized_pnl_loss > MAX_OBSERVED_REALIZED_PNL_LOSS_USD
        or evaluation.observed_position_pnl_drawdown > MAX_OBSERVED_POSITION_PNL_DRAWDOWN_USD
        or evaluation.observed_cumulative_canary_loss > MAX_OBSERVED_CUMULATIVE_CANARY_LOSS_USD
    ):
        raise GatewayError("OBSERVED_PNL_GUARD_EXCEEDED")
    if evaluation.allowance is None or evaluation.allowance < proposed:
        raise GatewayError("ALLOWANCE_INSUFFICIENT")
    return AdmissionRisk(proposed, projected_free)


# ---------------------------------------------------------------------------
# Foreground orchestrator: preflight / canary / reconcile
# ---------------------------------------------------------------------------


def canonical_live_orch_store_path(state_root: Path, public_wallet: str) -> Path:
    """One deterministic LIVE-ORCH ledger per persistent state root and wallet."""
    wallet = str(public_wallet).lower()
    if _ADDRESS_RE.fullmatch(wallet) is None:
        raise GatewayError("SIGNING_IDENTITY_INVALID")
    digest = hashlib.sha256(wallet.encode("ascii")).hexdigest()[:24]
    return Path(state_root) / "live_orch" / f"live-orch-wallet-{digest}.sqlite3"


def _bounded_pause(seconds: float) -> None:
    """One bounded foreground REST poll interval; never a background loop."""
    if not 0 < seconds <= PASSIVE_POLL_INTERVAL_SECONDS:
        raise GatewayError("POLL_INTERVAL_INVALID")
    threading.Event().wait(seconds)


@dataclass(frozen=True)
class LiveOrchConfig:
    state_root: Path
    expected_signer: str
    expected_wallet: str
    lifecycle_store_path: Path
    hermes_store_path: Path
    host: HostCurrentnessConfig

    def validate(self) -> None:
        for address in (self.expected_signer, self.expected_wallet):
            if not isinstance(address, str) or _ADDRESS_RE.fullmatch(address) is None:
                raise GatewayError("SIGNING_IDENTITY_INVALID")
        if _RELEASE_SHA_RE.fullmatch(str(self.host.expected_release_sha)) is None:
            raise GatewayError("RELEASE_IDENTITY_INVALID")


@dataclass
class LiveOrchDependencies:
    """Explicit runtime seams; production defaults, offline fakes in tests."""

    clock_ns: Callable[[], int] = time.time_ns
    host_currentness: Callable[[HostCurrentnessConfig], Mapping[str, object]] = (
        run_execution_host_currentness
    )
    geoblock: Callable[[], GateCGeoblockProof] = query_geoblock
    venue_fetcher: Callable[..., PublicExecutionVenueSnapshot] = fetch_public_venue_snapshot
    secret_provider_factory: Callable[[], object] = InteractiveGateBSecretProvider
    client_factory: Callable[[str, str], object] = create_deposit_wallet_client
    pause: Callable[[float], None] = _bounded_pause
    permit_authority: Callable[..., PermitAuthority] = verify_permit_authority


class _Session:
    __slots__ = ("gateway", "lock", "gate_b", "boundary")


class LiveOrchestrator:
    """Manual foreground LIVE-ORCH runtime.  No daemon, scheduler or retry loop."""

    def __init__(
        self,
        config: LiveOrchConfig,
        *,
        dependencies: LiveOrchDependencies | None = None,
        envelope: LiveOrchCapitalEnvelope | None = None,
    ) -> None:
        config.validate()
        self._config = config
        self._deps = LiveOrchDependencies() if dependencies is None else dependencies
        self._envelope = LiveOrchCapitalEnvelope() if envelope is None else envelope
        self._envelope.validate()

    # -- shared gates -------------------------------------------------------

    @property
    def store_path(self) -> Path:
        return canonical_live_orch_store_path(self._config.state_root, self._config.expected_wallet)

    def _now(self) -> int:
        value = self._deps.clock_ns()
        _time(value)
        return value

    def _host_current(self) -> str:
        document = self._deps.host_currentness(self._config.host)
        return validate_host_currentness(document, self._config.host.expected_release_sha)

    def _geoblock(self) -> GateCGeoblockProof:
        proof = self._deps.geoblock()
        if type(proof) is not GateCGeoblockProof:
            raise GatewayError("ACCESS_PROOF_INVALID")
        proof.validate(now_ns=self._now(), require_pass=True)
        return proof

    def _authority(self, permit: object, intent: object) -> PermitAuthority:
        check_first_canary_side(permit)
        authority = self._deps.permit_authority(
            permit,
            intent,
            lifecycle_store_path=self._config.lifecycle_store_path,
            hermes_store_path=self._config.hermes_store_path,
            now_ns=self._now(),
        )
        if type(authority) is not PermitAuthority:
            raise GatewayError("PERMIT_INVALID")
        return authority

    def _fresh_venue(
        self, authority: PermitAuthority
    ) -> tuple[PublicExecutionVenueSnapshot, ExecutionFeasibilityAssessment]:
        intent = authority.intent
        try:
            snapshot = self._deps.venue_fetcher(
                gamma_market_id=intent.gamma_market_id,
                condition_id=intent.condition_id,
                token_id=intent.token_id,
            )
        except ExecutionFeasibilityError:
            raise GatewayError("VENUE_SNAPSHOT_UNAVAILABLE") from None
        return snapshot, revalidate_venue(authority, snapshot, evaluated_at_ns=self._now())

    def _open_session(self) -> _Session:
        path = self.store_path
        session = _Session()
        session.gateway = session.lock = session.gate_b = session.boundary = None
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            if path.exists():
                session.gateway = ProtectedExecutionGateway.open(path, opened_time_ns=self._now())
            else:
                session.gateway = ProtectedExecutionGateway.create(path, created_time_ns=self._now())
            session.lock = WalletSessionLock(path.parent, self._config.expected_wallet).acquire()
            policy = GateBIdentityPolicy(
                expected_signer=self._config.expected_signer.lower(),
                expected_wallet=self._config.expected_wallet.lower(),
            )
            session.gate_b = GateBSession.authenticate(
                self._deps.secret_provider_factory(),
                policy,
                client_factory=self._deps.client_factory,
                gateway=session.gateway,
                wallet_lock=session.lock,
            )
            session.boundary = LiveOrchMutationBoundary(
                session.gateway, session.gate_b, issuer=_LIVE_ORCH_EVENT_ISSUER
            )
        except BaseException:
            self._close_session(session)
            raise
        return session

    @staticmethod
    def _close_session(session: _Session) -> None:
        for item in (session.gate_b, session.lock, session.gateway):
            if item is None:
                continue
            try:
                item.close()
            except Exception:
                pass

    # -- reconciliation ----------------------------------------------------

    def _truth(self, session: _Session) -> LiveOrchAccountTruth:
        truth = session.gate_b.live_orch_account_truth(
            _LIVE_ORCH_ISSUER, observed_time_ns=self._now()
        )
        if (
            truth.public_wallet != self._config.expected_wallet.lower()
            or truth.public_signer != self._config.expected_signer.lower()
        ):
            raise GatewayError("SIGNING_IDENTITY_INVALID")
        return truth

    def _reconcile_pass(self, session: _Session, *, clear_restart: bool) -> dict:
        """One authoritative REST read applied to every open episode (bounded steps)."""
        truth = self._truth(session)
        lookup = lambda venue_order_id: session.gate_b.live_orch_order(  # noqa: E731
            _LIVE_ORCH_ISSUER, venue_order_id
        )
        for _step in range(4):
            checkpoint = session.gateway.live_orch_checkpoint()
            episodes = list(checkpoint["episodes"])
            owned = {
                episode["create"]["venue_order_id"]: episode["episode_id"]
                for episode in episodes
                if isinstance(episode["create"], Mapping) and episode["create"]["venue_order_id"]
            }
            open_states = [
                episode for episode in episodes
                if episode["state"] not in LIVE_ORCH_CLEAN_TERMINAL_STATES
            ]
            concurrent = len([e for e in open_states if e["state"] != "TERMINAL_KNOWN_POSITION"]) > 1
            changed = False
            now = self._now()
            for index, episode in enumerate(episodes):
                attributed = {vid for vid, owner in owned.items() if owner != episode["episode_id"]}
                updated = reconcile_episode_step(
                    episode,
                    truth,
                    attributed_order_ids=attributed,
                    order_lookup=lookup,
                    concurrent=concurrent,
                    now_ns=now,
                )
                if updated != _copy(episode):
                    updated["reconciliation"]["last_reconciled_time_ns"] = now
                    episodes[index] = updated
                    changed = True
            clear = clear_restart and checkpoint["restart_reconciliation_required"]
            if not changed and not clear:
                break
            checkpoint["episodes"] = episodes
            if clear:
                checkpoint["restart_reconciliation_required"] = False
            session.gateway.record_live_orch_event(
                "LIVE_ORCH_RECONCILED", checkpoint,
                issuer=_LIVE_ORCH_EVENT_ISSUER, event_time_ns=now,
            )
        return session.gateway.live_orch_checkpoint()

    @staticmethod
    def _episode(checkpoint: Mapping[str, object], episode_id: str) -> Mapping[str, object]:
        for episode in checkpoint["episodes"]:
            if episode["episode_id"] == episode_id:
                return episode
        raise GatewayError("LIVE_ORCH_EPISODE_UNKNOWN")

    def _cancel_rounds(self, session: _Session, episode_id: str) -> str:
        """At most three cancel/reconcile rounds; a NEW attempt identity each round.

        A cancel is sent only when authoritative reconciliation shows the order
        definitively still live.  Unconverged recovery becomes
        RECONCILIATION_BLOCKED and never authorizes a CREATE.
        """
        state = self._episode(self._reconcile_pass(session, clear_restart=False), episode_id)
        for _round in range(MAX_CANCEL_RECONCILE_ROUNDS):
            if state["reconciliation"]["order_live"] is not True or state["state"] not in (
                "RESTING", "RECONCILING", "RECONCILIATION_BLOCKED", "CREATE_ACCEPTED",
                "CREATE_AMBIGUOUS", "SETTLEMENT_PENDING",
            ):
                return str(state["state"])
            session.boundary.cancel(episode_id, now_ns=self._now())
            state = self._episode(self._reconcile_pass(session, clear_restart=False), episode_id)
        if state["reconciliation"]["order_live"] is True:
            checkpoint = session.gateway.live_orch_checkpoint()
            episodes = list(checkpoint["episodes"])
            for index, episode in enumerate(episodes):
                if episode["episode_id"] == episode_id and episode["state"] != "RECONCILIATION_BLOCKED":
                    blocked = _blocked(_copy(episode), "CANCEL_UNCONVERGED")
                    blocked["reconciliation"]["last_reconciled_time_ns"] = self._now()
                    episodes[index] = blocked
                    checkpoint["episodes"] = episodes
                    session.gateway.record_live_orch_event(
                        "LIVE_ORCH_RECONCILED", checkpoint,
                        issuer=_LIVE_ORCH_EVENT_ISSUER, event_time_ns=self._now(),
                    )
            return "RECONCILIATION_BLOCKED"
        return str(state["state"])

    def _recover_all(self, session: _Session) -> dict:
        """restart -> no-new-exposure -> discover -> cancel/reconcile (risk-reducing only)."""
        checkpoint = self._reconcile_pass(session, clear_restart=True)
        for episode in list(checkpoint["episodes"]):
            if episode["reconciliation"]["order_live"] is True and episode["state"] not in (
                LIVE_ORCH_CLEAN_TERMINAL_STATES
            ):
                self._cancel_rounds(session, str(episode["episode_id"]))
        return self._reconcile_pass(session, clear_restart=True)

    def _observe(self, session: _Session, episode_id: str) -> str:
        """Foreground passive observation <= 60 s, REST polling >= 1 s, then cancel."""
        started = self._now()
        deadline = started + PASSIVE_OBSERVATION_MAX_SECONDS * 1_000_000_000
        state = "RECONCILING"
        try:
            for _poll in range(PASSIVE_OBSERVATION_MAX_SECONDS + 1):
                checkpoint = self._reconcile_pass(session, clear_restart=False)
                state = str(self._episode(checkpoint, episode_id)["state"])
                if state != "RESTING" or self._now() >= deadline:
                    break
                self._deps.pause(PASSIVE_POLL_INTERVAL_SECONDS)
            if state in ("RESTING", "CREATE_AMBIGUOUS", "RECONCILING", "RECONCILIATION_BLOCKED"):
                state = self._cancel_rounds(session, episode_id)
        except BaseException:
            # Normal or interrupted exit never intentionally leaves a known
            # resting order: attempt risk-reducing cancellation, then re-raise.
            try:
                self._cancel_rounds(session, episode_id)
            except BaseException:
                pass
            raise
        return state

    # -- commands ------------------------------------------------------------

    def preflight(self, permit: object, intent: object) -> LiveOrchResult:
        """Read-only checks; cannot authenticate, sign, write the ledger or mutate."""
        try:
            authority = self._authority(permit, intent)
            self._host_current()
            self._geoblock()
            snapshot, assessment = self._fresh_venue(authority)
            fee = worst_case_fee_reserve(authority, snapshot, assessment)
            if authority.principal + fee > SINGLE_ORDER_WORST_CASE_MAX_USD:
                raise GatewayError("SINGLE_ORDER_LIMIT_EXCEEDED")
            ledger = self._read_ledger()
            return LiveOrchResult(
                "preflight", "PREFLIGHT_PASS", "PREFLIGHT_PASS",
                details={
                    "venue_snapshot_id": snapshot.venue_snapshot_id,
                    "execution_feasibility_assessment_id": assessment.execution_feasibility_assessment_id,
                    "principal_notional_usd": _text(authority.principal),
                    "worst_case_fee_reserve_usd": _text(fee),
                    "ledger_episodes": len(ledger["episodes"]),
                    "seconds_delay_applicability": seconds_delay_applicability(
                        authority.intent, snapshot
                    ),
                },
            )
        except GatewayError as exc:
            return LiveOrchResult("preflight", "BLOCKED", exc.code)

    def _read_ledger(self) -> Mapping[str, object]:
        path = self.store_path
        if not path.exists():
            return {"episodes": [], "restart_reconciliation_required": False}
        store = GatewayStore(path)
        try:
            mapping, _head, events = store.load()
            if mapping is None:
                raise GatewayError("LIVE_ORCH_LEDGER_UNHEALTHY")
            state = _validate_replay(events)
            if state.to_mapping() != dict(mapping):
                raise GatewayError("LIVE_ORCH_LEDGER_UNHEALTHY")
            checkpoint = state.live_orch_checkpoint
            if checkpoint is None:
                return {"episodes": [], "restart_reconciliation_required": False}
            return validate_live_orch_checkpoint(checkpoint)
        except GatewayStoreError:
            raise GatewayError("LIVE_ORCH_LEDGER_UNHEALTHY") from None
        finally:
            store.close()

    def reconcile(self) -> LiveOrchResult:
        """Risk-reducing recovery only: never creates new exposure."""
        session: _Session | None = None
        try:
            session = self._open_session()
            checkpoint = self._recover_all(session)
            states = [str(episode["state"]) for episode in checkpoint["episodes"]]
            evaluation = evaluate_account(self._truth(session), checkpoint)
            return LiveOrchResult(
                "reconcile",
                "NO_NEW_EXPOSURE_READY" if not evaluation.blocking_codes else "BLOCKED",
                evaluation.blocking_codes[0] if evaluation.blocking_codes else "RECONCILED",
                details={
                    "episode_states": states,
                    "total_commitment_usd": _text(evaluation.total_commitment),
                },
            )
        except GatewayError as exc:
            return LiveOrchResult("reconcile", "BLOCKED", exc.code)
        finally:
            if session is not None:
                self._close_session(session)

    def canary(self, permit: object, intent: object) -> LiveOrchResult:
        """At most one BUY CREATE for one exact fresh permit, then reconcile."""
        session: _Session | None = None
        transmits = 0
        episode_id: str | None = None
        try:
            authority = self._authority(permit, intent)
            self._host_current()  # before protected authentication
            self._geoblock()
            session = self._open_session()
            checkpoint = self._recover_all(session)
            if any(
                episode["binding"]["exploratory_permit_id"] == authority.permit.permit_id
                for episode in checkpoint["episodes"]
            ):
                # One permit never reaches a second admission or CREATE_STARTED.
                raise GatewayError("PERMIT_ALREADY_CONSUMED")
            truth = self._truth(session)
            evaluation = evaluate_account(truth, checkpoint)
            if evaluation.blocking_codes:
                raise GatewayError(evaluation.blocking_codes[0])
            snapshot, assessment = self._fresh_venue(authority)
            fee = worst_case_fee_reserve(authority, snapshot, assessment)
            risk = check_admission_risk(
                self._envelope, principal=authority.principal, fee_reserve=fee,
                evaluation=evaluation,
            )
            intent_value = authority.intent
            spec = LiveOrchOrderSpec(
                token_id=intent_value.token_id,
                execution_style=intent_value.execution_style,
                order_type=intent_value.order_type,
                requested_shares=intent_value.requested_shares,
                price_limit=intent_value.price_limit,
                gtd_expiration_unix_s=intent_value.gtd_expiration_unix_s,
                principal_notional_usd=_text(authority.principal),
                worst_case_commitment_usd=_text(risk.proposed_worst_case_commitment),
                tick_size=str(snapshot.book_tick_size),
            )
            prepared = session.boundary.prepare(spec, attempt_seed=authority.permit.permit_id)
            # Immediately before admission: strict host currentness and fresh access.
            host_id = self._host_current()
            geoblock = self._geoblock()
            now = self._now()
            if not authority.permit.issued_at_ns <= now < authority.permit.valid_until_ns:
                raise GatewayError("PERMIT_EXPIRED")
            episode = build_admitted_episode(
                authority,
                snapshot=snapshot,
                assessment=assessment,
                release_sha=self._config.host.expected_release_sha,
                host_currentness_id=host_id,
                geoblock=geoblock,
                truth=truth,
                evaluation=evaluation,
                fee_reserve=fee,
                risk=risk,
                prepared=prepared,
                admitted_time_ns=now,
            )
            episode_id = str(episode["episode_id"])
            try:
                outcome = session.boundary.admit_and_transmit(prepared, episode, now_ns=now)
            except GatewayError as exc:
                if exc.code == "LIVE_ORCH_OUTCOME_PERSISTENCE_FAILED":
                    transmits = 1
                raise
            transmits = 1
            state = str(outcome["state"])
            if state != "CREATE_REJECTED":
                state = self._observe(session, episode_id)
            return LiveOrchResult(
                "canary", "CANARY_COMPLETE", "ONE_CREATE_ATTEMPTED",
                episode_id=episode_id, episode_state=state, create_transmits=transmits,
                details={"create_outcome": outcome["outcome"]},
            )
        except GatewayError as exc:
            return LiveOrchResult(
                "canary", "BLOCKED", exc.code, episode_id=episode_id,
                create_transmits=transmits,
            )
        finally:
            if session is not None:
                self._close_session(session)


def build_admitted_episode(
    authority: PermitAuthority,
    *,
    snapshot: PublicExecutionVenueSnapshot,
    assessment: ExecutionFeasibilityAssessment,
    release_sha: str,
    host_currentness_id: str,
    geoblock: GateCGeoblockProof,
    truth: LiveOrchAccountTruth,
    evaluation: AccountEvaluation,
    fee_reserve: Decimal,
    risk: AdmissionRisk,
    prepared: object,
    admitted_time_ns: int,
) -> dict:
    """Sanitized durable LIVE_ORCH_ADMISSION evidence bound before CREATE_STARTED."""
    permit, intent = authority.permit, authority.intent
    binding = {
        "exploratory_permit_id": permit.permit_id,
        "execution_intent_id": intent.execution_intent_id,
        "strategy_version_id": intent.strategy_version_id,
        "execution_rule_sha256": intent.execution_rule_sha256,
        "gamma_market_id": intent.gamma_market_id,
        "condition_id": intent.condition_id,
        "token_id": intent.token_id,
        "side": intent.side,
        "execution_style": intent.execution_style,
        "order_type": intent.order_type,
        "requested_shares": intent.requested_shares,
        "price_limit": intent.price_limit,
        "post_only": intent.post_only,
        "gtd_expiration_unix_s": intent.gtd_expiration_unix_s,
        "authorized_order_notional_usd": permit.authorized_order_notional_usd,
        "release_sha": release_sha,
        "public_signer": truth.public_signer,
        "public_wallet": truth.public_wallet,
    }
    economics = prepared.economics
    admission = {
        "decision": "ADMITTED",
        "venue_snapshot_id": snapshot.venue_snapshot_id,
        "execution_feasibility_assessment_id": assessment.execution_feasibility_assessment_id,
        "feasibility_status": assessment.status,
        "host_currentness_id": host_currentness_id,
        "geoblock_proof_id": geoblock.proof_id,
        "geoblock_observed_time_ns": geoblock.observed_time_ns,
        "account_truth_id": truth.truth_id,
        "collateral_before_usd": _text(evaluation.collateral),
        "current_committed_usd": _text(evaluation.total_commitment),
        "principal_notional_usd": _text(authority.principal),
        "worst_case_fee_reserve_usd": _text(fee_reserve),
        "worst_case_commitment_usd": _text(risk.proposed_worst_case_commitment),
        "projected_free_collateral_usd": _text(risk.projected_free_collateral),
        "observed_realized_pnl_loss_usd": _text(evaluation.observed_realized_pnl_loss),
        "observed_position_pnl_drawdown_usd": _text(evaluation.observed_position_pnl_drawdown),
        "observed_cumulative_canary_loss_usd": _text(evaluation.observed_cumulative_canary_loss),
        "signed_order_id": economics.signed_order_id,
        "signed_maker_amount": economics.maker_amount,
        "signed_taker_amount": economics.taker_amount,
        "admitted_time_ns": admitted_time_ns,
    }
    admission["admission_id"] = _sha(
        "liveorchadmission:sha256:", {"binding": binding, "admission": dict(admission)}
    )
    return {
        "episode_id": live_orch_episode_id(binding, admission["admission_id"]),
        "state": "ADMITTED",
        "binding": binding,
        "admission": admission,
        "create": None,
        "cancel_attempts": [],
        "reconciliation": {
            "order_live": None,
            "open_remainder_shares": "0",
            "trades": [],
            "fee_state": "RESERVED" if fee_reserve > 0 else "NOT_REQUIRED",
            "actual_fee_usd": None,
            "block_reason": None,
            "last_reconciled_time_ns": None,
        },
    }


# ---------------------------------------------------------------------------
# Manual CLI (foreground only)
# ---------------------------------------------------------------------------


def _load_records(permit_path: Path, intent_path: Path) -> tuple[object, object]:
    from src.exploratory_gate_c import record_from_mapping as permit_from_mapping

    try:
        permit = permit_from_mapping(json.loads(Path(permit_path).read_text(encoding="utf-8")))
        intent = ExecutionIntent.from_mapping(
            json.loads(Path(intent_path).read_text(encoding="utf-8"))
        )
    except Exception:
        raise GatewayError("PERMIT_OR_INTENT_UNREADABLE") from None
    return permit, intent


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="live_orch", description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("preflight", "canary", "reconcile"):
        command = sub.add_parser(name)
        command.add_argument("--state-root", type=Path, default=DEFAULT_STATE_ROOT)
        command.add_argument("--expected-signer", required=True)
        command.add_argument("--expected-wallet", required=True)
        command.add_argument("--lifecycle-store", type=Path, required=True)
        command.add_argument("--hermes-store", type=Path, required=True)
        command.add_argument("--repository-root", type=Path, required=True)
        command.add_argument("--binding-file", type=Path, required=True)
        command.add_argument("--active-release", type=Path, required=True)
        command.add_argument("--unit-dir", type=Path, required=True)
        command.add_argument("--ssh-port", type=int, required=True)
        command.add_argument("--expected-release-sha", required=True)
        if name != "reconcile":
            command.add_argument("--permit-json", type=Path, required=True)
            command.add_argument("--intent-json", type=Path, required=True)
    return parser


def _stdin_tty() -> bool:
    try:
        return bool(sys.stdin.isatty())
    except Exception:
        return False


def main(
    argv: Sequence[str] | None = None,
    *,
    dependencies: LiveOrchDependencies | None = None,
    confirm: Callable[[str], str] = input,
) -> int:
    args = _parser().parse_args(argv)
    try:
        config = LiveOrchConfig(
            state_root=args.state_root,
            expected_signer=args.expected_signer.lower(),
            expected_wallet=args.expected_wallet.lower(),
            lifecycle_store_path=args.lifecycle_store,
            hermes_store_path=args.hermes_store,
            host=HostCurrentnessConfig(
                repository_root=args.repository_root,
                binding_file=args.binding_file,
                active_release=args.active_release,
                unit_dir=args.unit_dir,
                ssh_port=args.ssh_port,
                expected_release_sha=args.expected_release_sha,
            ),
        )
        orchestrator = LiveOrchestrator(config, dependencies=dependencies)
        if args.command == "reconcile":
            result = orchestrator.reconcile()
        else:
            permit, intent = _load_records(args.permit_json, args.intent_json)
            if args.command == "preflight":
                result = orchestrator.preflight(permit, intent)
            else:
                # Operator confirmation is interactive only; a pipe never confirms.
                if not _stdin_tty() or confirm(
                    f"Type {LIVE_ORCH_CONFIRMATION_PHRASE} to allow at most one BUY CREATE: "
                ).strip() != LIVE_ORCH_CONFIRMATION_PHRASE:
                    raise GatewayError("OPERATOR_CONFIRMATION_REQUIRED")
                result = orchestrator.canary(permit, intent)
    except GatewayError as exc:
        result = LiveOrchResult(args.command, "BLOCKED", exc.code)
    sys.stdout.write(json.dumps(result.to_mapping(), sort_keys=True) + "\n")
    return 0 if result.status in ("PREFLIGHT_PASS", "CANARY_COMPLETE", "NO_NEW_EXPOSURE_READY") else 2


if __name__ == "__main__":  # pragma: no cover - manual foreground entry point
    raise SystemExit(main())
