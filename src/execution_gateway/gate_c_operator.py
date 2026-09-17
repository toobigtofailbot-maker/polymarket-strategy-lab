"""Manual foreground-only WP175 operator surface.

The command is deliberately a thin adapter.  It never reads secrets from
argv/files/environment, starts a service, or exposes a browser mutation route.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time

from src.paper_trading.models import PaperStrategyBinding, dataclass_from_mapping
from src.research_runtime.executable_edge import (
    ExecutableEdgeAssessment,
    ExecutionCostModel,
    deserialize_assessment,
    validate_execution_cost_model,
)

from .gate_b import (
    GateBIdentityPolicy,
    GateBSession,
    InteractiveGateBSecretProvider,
    WalletSessionLock,
    _GATE_C_ISSUER,
)
from .gate_c import (
    GateCGeoblockProof,
    GateCMarketMetadata,
    GateCSession,
    GateCStrategyQualification,
    canonical_gateway_store_path,
    query_geoblock,
    runtime_repository_identity,
)
from .gateway import ProtectedExecutionGateway, GatewayError


_ACTIVATION_PHRASE = "ARM EXACT-HEAD WP175 ONE-SHOT CANARY"
_MAX_ARTIFACT_BYTES = 1_048_576


class GateCOperator:
    """Explicit foreground orchestration; callers own the human approvals."""

    def __init__(self, gateway: ProtectedExecutionGateway, *, operator_name: str = "operator"):
        self.gateway = gateway
        self.operator_name = operator_name
        self._qualification_issued = False

    def issue_qualification(self, **kwargs: object) -> GateCStrategyQualification:
        if not bool(getattr(sys.stdin, "isatty", lambda: False)()):
            raise GatewayError("QUALIFICATION_REQUIRES_TTY")
        if self._qualification_issued:
            raise GatewayError("QUALIFICATION_ALREADY_USED")
        qualification = GateCStrategyQualification.issue(
            **kwargs, operator_is_tty=True  # type: ignore[arg-type]
        )
        self._qualification_issued = True
        return qualification

    def arm(
        self,
        gate_b_session: GateBSession,
        qualification: GateCStrategyQualification,
        *,
        market: GateCMarketMetadata,
        geoblock: GateCGeoblockProof,
        now_ns: int,
    ) -> GateCSession:
        if not bool(getattr(sys.stdin, "isatty", lambda: False)()):
            raise GatewayError("QUALIFICATION_REQUIRES_TTY")
        return GateCSession.arm(
            self.gateway,
            gate_b_session,
            qualification,
            market=market,
            geoblock=geoblock,
            operator_nonce=qualification.operator_nonce,
            now_ns=now_ns,
        )

    def reconcile_before_arm(
        self,
        gate_b_session: GateBSession,
        *,
        geoblock: GateCGeoblockProof,
        now_ns: int,
    ) -> None:
        """Converge the restarted canonical ledger before any A3 arm."""
        owners = {
            str(attempt.venue_order_id): str(attempt.order_identity)
            for attempt in self.gateway.state.mutation_attempts
            if attempt.operation == "CREATE"
            and attempt.venue_order_id is not None
        }
        adapter = gate_b_session.gate_c_reconciliation_adapter(
            _GATE_C_ISSUER,
            observed_time_ns=now_ns,
            order_identity_by_venue_id=owners,
            geoblock_eligible=not geoblock.blocked,
        )
        self.gateway.reconcile(adapter=adapter, event_time_ns=now_ns)
        if self.gateway.state.reconciliation_state != "HEALTHY":
            raise GatewayError("RECONCILIATION_REQUIRED")

    def run_one_shot(
        self,
        gate_b_session: GateBSession,
        qualification: GateCStrategyQualification,
        *,
        market: GateCMarketMetadata,
        geoblock: GateCGeoblockProof,
        price: str,
        size: str,
        side: str,
        post_only: bool,
        expiration: int | None,
        reduce_only: bool,
        order_identity: str,
        now_ns: int,
    ) -> dict[str, object]:
        """Arm, send exactly once, reconcile/cancel, and return public evidence."""
        session = self.arm(
            gate_b_session, qualification, market=market,
            geoblock=geoblock, now_ns=now_ns,
        )
        receipt = session.create_limit_order(
            price=price, size=size, side=side, post_only=post_only,
            expiration=expiration, reduce_only=reduce_only,
            order_identity=order_identity, event_time_ns=now_ns + 1,
        )
        if receipt.outcome in ("DEFINITIVE_ACCEPTED", "AMBIGUOUS"):
            session.reconcile_bounded(
                geoblock=geoblock, event_time_ns=now_ns + 2,
            )
        return {
            "arm_receipt": session.arm_receipt.to_public_mapping(),
            "canary_receipt": receipt.to_public_mapping(),
            "terminal": session.cockpit_projection(),
        }


def _artifact_bytes(path: Path) -> bytes:
    try:
        absolute = path.resolve(strict=True)
        if (
            path.suffix != ".json"
            or path.is_symlink()
            or not path.is_file()
            or path.stat().st_nlink != 1
            or path.stat().st_size > _MAX_ARTIFACT_BYTES
            or any(parent.is_symlink() for parent in absolute.parents)
        ):
            raise GatewayError("QUALIFICATION_INPUT_INVALID")
        return path.read_bytes()
    except GatewayError:
        raise
    except Exception:
        raise GatewayError("QUALIFICATION_INPUT_INVALID") from None


def _mapping(path: Path) -> dict[str, object]:
    try:
        value = json.loads(_artifact_bytes(path).decode("utf-8"))
        if not isinstance(value, dict):
            raise ValueError
        return value
    except GatewayError:
        raise
    except Exception:
        raise GatewayError("QUALIFICATION_INPUT_INVALID") from None


def _load_qualification_artifacts(
    *, binding_path: Path, assessment_path: Path, cost_model_path: Path,
) -> tuple[PaperStrategyBinding, ExecutableEdgeAssessment, ExecutionCostModel]:
    try:
        binding = dataclass_from_mapping(PaperStrategyBinding, _mapping(binding_path))
        assessment = deserialize_assessment(_artifact_bytes(assessment_path))
        cost_data = _mapping(cost_model_path)
        cost_data["size_grid"] = tuple(cost_data["size_grid"])
        cost_model = ExecutionCostModel(**cost_data)
        validate_execution_cost_model(cost_model)
    except GatewayError:
        raise
    except Exception:
        raise GatewayError("QUALIFICATION_INPUT_INVALID") from None
    return binding, assessment, cost_model


def main(argv: list[str] | None = None) -> int:
    """Run the explicitly confirmed manual foreground one-shot workflow."""
    parser = argparse.ArgumentParser(description="Run the WP175 foreground canary operator")
    sub = parser.add_subparsers(dest="command", required=True)
    canary = sub.add_parser("canary")
    canary.add_argument("--expected-signer", required=True)
    canary.add_argument("--expected-wallet", required=True)
    canary.add_argument("--binding", required=True, type=Path)
    canary.add_argument("--assessment", required=True, type=Path)
    canary.add_argument("--cost-model", required=True, type=Path)
    canary.add_argument("--paper-store", required=True, type=Path)
    canary.add_argument("--operator-nonce", required=True)
    canary.add_argument("--market-id", required=True)
    canary.add_argument("--token-id", required=True)
    canary.add_argument("--order-identity", required=True)
    canary.add_argument("--price", required=True)
    canary.add_argument("--size", required=True)
    canary.add_argument("--side", required=True, choices=("BUY", "SELL"))
    canary.add_argument("--post-only", action="store_true")
    canary.add_argument("--expiration", type=int)
    canary.add_argument("--reduce-only", action="store_true")
    args = parser.parse_args(argv)
    if not bool(getattr(sys.stdin, "isatty", lambda: False)()):
        parser.error("WP175 requires a foreground TTY")
    root, head = runtime_repository_identity()
    ledger = canonical_gateway_store_path(root, args.expected_wallet)
    if not ledger.is_file():
        raise GatewayError("CANONICAL_LEDGER_REQUIRED")
    binding, assessment, cost_model = _load_qualification_artifacts(
        binding_path=args.binding, assessment_path=args.assessment,
        cost_model_path=args.cost_model,
    )
    confirmation = input(
        f'Type exactly "{_ACTIVATION_PHRASE}" to continue: '
    )
    if confirmation != _ACTIVATION_PHRASE:
        raise GatewayError("GATE_C_ACTIVATION_NOT_CONFIRMED")
    now = time.time_ns()
    policy = GateBIdentityPolicy(args.expected_signer, args.expected_wallet)
    with ProtectedExecutionGateway.open(ledger, opened_time_ns=now) as gateway:
        with WalletSessionLock(ledger.parent, args.expected_wallet) as wallet_lock:
            with GateBSession.authenticate(
                InteractiveGateBSecretProvider(), policy,
                gateway=gateway, wallet_lock=wallet_lock,
            ) as gate_b_session:
                geoblock = query_geoblock()
                operation_time = max(
                    time.time_ns(), gateway.state.last_event_time_ns + 1
                )
                operator = GateCOperator(gateway)
                operator.reconcile_before_arm(
                    gate_b_session, geoblock=geoblock,
                    now_ns=operation_time,
                )
                operation_time = max(
                    time.time_ns(), gateway.state.last_event_time_ns + 1
                )
                market = gate_b_session.gate_c_market_metadata(
                    _GATE_C_ISSUER, market_id=args.market_id,
                    token_id=args.token_id, observed_time_ns=operation_time,
                )
                qualification = operator.issue_qualification(
                    repository_head=head, binding=binding,
                    assessment=assessment, cost_model=cost_model,
                    paper_store_path=args.paper_store,
                    operator_nonce=args.operator_nonce,
                    issued_at_ns=operation_time,
                )
                evidence = operator.run_one_shot(
                    gate_b_session, qualification, market=market,
                    geoblock=geoblock, price=args.price, size=args.size,
                    side=args.side, post_only=args.post_only,
                    expiration=args.expiration, reduce_only=args.reduce_only,
                    order_identity=args.order_identity,
                    now_ns=max(
                        time.time_ns(), gateway.state.last_event_time_ns + 1
                    ),
                )
                print(json.dumps(evidence, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
