"""WP174B Gate-B operator command (manual foreground, real no-echo secret).

Run only by the operator in a separate local terminal. Claude/Codex must never
run this command or receive the private key. The private key is entered through
a no-echo prompt; it is never accepted via argv, a file, a pipe, or the
environment. Only a sanitized receipt is written and printed.

Usage:
  python -m src.execution_gateway.gate_b_operator verify \\
    --expected-signer 0xPUBLIC_SIGNER \\
    --wallet 0xPUBLIC_DEPOSIT_WALLET \\
    --probe-token PUBLIC_TOKEN_ID \\
    --probe-price 0.10 --probe-size 5 \\
    --gateway-store local_data/gate_b/gateway.sqlite3 \\
    --receipt local_data/gate_b/verification_receipt.json
"""

from __future__ import annotations

import argparse
import getpass
import json
from pathlib import Path
import subprocess
import time

from .gate_b import (
    GateBIdentityPolicy,
    GateBSession,
    InteractiveGateBSecretProvider,
    WalletSessionLock,
    _CANCEL_CONFIRMATION_PHRASE,
    _HEAD_RE,
    _stdin_is_tty,
)
from .gateway import GatewayError, ProtectedExecutionGateway


def _repository_head() -> str:
    """Return the exact current Git HEAD sha, failing closed if unavailable.

    A PASS receipt must bind a real HEAD; this never returns a placeholder.
    """
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        )
        head = out.stdout.strip().lower()
    except Exception:
        raise GatewayError("CANCEL_PROBE_FAILED") from None
    if _HEAD_RE.fullmatch(head) is None:
        raise GatewayError("CANCEL_PROBE_FAILED")
    return head


def _confirm_empty_wallet_cancel() -> str:
    """Separate no-echo confirmation, distinct from the private-key prompt."""
    if not _stdin_is_tty():
        raise GatewayError("CANCEL_PROBE_FAILED")
    try:
        phrase = getpass.getpass(
            f"Type '{_CANCEL_CONFIRMATION_PHRASE}' to authorize the empty-wallet "
            "cancel probe (no echo): "
        )
    except (EOFError, OSError):
        raise GatewayError("CANCEL_PROBE_FAILED") from None
    return phrase.strip()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="gate_b_operator")
    sub = parser.add_subparsers(dest="command", required=True)
    verify = sub.add_parser("verify", help="Run the Gate-B verification probe.")
    verify.add_argument("--expected-signer", required=True)
    verify.add_argument("--wallet", required=True)
    verify.add_argument("--probe-token", required=True)
    verify.add_argument("--probe-price", default="0.10")
    verify.add_argument("--probe-size", default="5")
    verify.add_argument("--receipt", required=True)
    verify.add_argument("--gateway-store", default="local_data/gate_b/gateway.sqlite3")
    verify.add_argument(
        "--valid-minutes", type=int, default=60, help="Receipt validity window."
    )
    return parser


def run_verify(args: argparse.Namespace) -> int:
    policy = GateBIdentityPolicy(
        expected_signer=args.expected_signer.lower(),
        expected_wallet=args.wallet.lower(),
    )
    provider = InteractiveGateBSecretProvider()
    store_path = Path(args.gateway_store)
    store_path.parent.mkdir(parents=True, exist_ok=True)
    opened_ns = time.time_ns()
    gateway = (
        ProtectedExecutionGateway.open(store_path, opened_time_ns=opened_ns)
        if store_path.exists()
        else ProtectedExecutionGateway.create(store_path, created_time_ns=opened_ns)
    )
    lock = None
    session = None
    try:
        lock = WalletSessionLock(store_path.parent, policy.expected_wallet).acquire()
        session = GateBSession.authenticate(
            provider, policy, gateway=gateway, wallet_lock=lock
        )
        now_ns = time.time_ns()
        valid_ns = now_ns + max(1, int(args.valid_minutes)) * 60 * 1_000_000_000
        signing_probe_id = session.signing_probe(
            token_id=args.probe_token,
            price=str(args.probe_price),
            size=str(args.probe_size),
            side="BUY",
        )
        confirmation = _confirm_empty_wallet_cancel()
        receipt = session.empty_wallet_cancel_probe(
            confirmation,
            repository_head=_repository_head(),
            now_ns=now_ns,
            valid_ns=valid_ns,
        )
        # The signing probe id is bound INTO the receipt before receipt_id is
        # derived (content-addressed), so no post-hoc mutation is needed here.
        assert receipt.signing_probe_id == signing_probe_id
        document = receipt.as_receipt_document()
        receipt_path = Path(args.receipt)
        receipt_path.parent.mkdir(parents=True, exist_ok=True)
        receipt_path.write_text(
            json.dumps(document, indent=2, sort_keys=True), encoding="utf-8"
        )
    finally:
        if session is not None:
            session.close()
        if lock is not None and lock.active:
            lock.close()
        gateway.close()
    # Print only sanitized public fields.
    print("GATE_B_VERIFICATION: PASS")
    print("  capability_state: B4_CANCEL_TRANSPORT_VERIFIED")
    print(f"  receipt_id: {document['receipt_id']}")
    print(f"  signing_probe_id: {signing_probe_id}")
    print(f"  cancel_probe_result: {document['cancel_probe_result']}")
    print(f"  receipt_path: {receipt_path}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "verify":
            return run_verify(args)
    except GatewayError as exc:
        # Closed, sanitized failure code only; never a raw exception or secret.
        print(f"GATE_B_VERIFICATION: FAIL {exc.code}")
        return 2
    return 2


if __name__ == "__main__":  # pragma: no cover - manual operator entry point
    raise SystemExit(main())
