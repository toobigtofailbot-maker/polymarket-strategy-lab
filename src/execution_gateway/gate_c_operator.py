"""Manual foreground-only WP175 operator surface.

The command is deliberately a thin adapter.  It never reads secrets from
argv/files/environment, starts a service, or exposes a browser mutation route.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from .gate_b import GateBSession
from .gate_c import (
    GateCGeoblockProof,
    GateCMarketMetadata,
    GateCSession,
    GateCStrategyQualification,
)
from .gateway import ProtectedExecutionGateway, GatewayError


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


def main(argv: list[str] | None = None) -> int:
    """Expose only a foreground diagnostic command; activation is separate."""
    parser = argparse.ArgumentParser(description="Run the WP175 foreground canary operator")
    parser.add_argument("--gateway-store", required=True, type=Path)
    parser.add_argument("--now-ns", type=int)
    args = parser.parse_args(argv)
    if not bool(getattr(sys.stdin, "isatty", lambda: False)()):
        parser.error("WP175 requires a foreground TTY")
    now = args.now_ns
    if now is None:
        import time
        now = time.time_ns()
    with ProtectedExecutionGateway.open(args.gateway_store, opened_time_ns=now) as gateway:
        # Deliberately no implicit authentication, arm, create, cancel, or
        # activation occurs.  A later exact-head human decision is required.
        print({"authority_state": gateway.state.authority_state, "gate_c_activation": "PENDING"})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
