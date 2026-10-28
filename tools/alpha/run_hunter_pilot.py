"""S10-ALPHA-HUNTER-PILOT-02 foreground CLI: hunter verify, then one run_hunter_cycle_once.

    run --policy P --owner-record R --owner-record-sha256 H --state-root S
        --hunter-scratch-dir D --hunter-operation OP

``verify`` re-derives every hunter operation with zero network and zero Hermes
dispatch; any failure prints a refused terminal and the src cycle is never
called.  stdout is the terminal JSON.  No other subcommand, loop, timer or
daemon.  Dormant: activation, custody and capital are separate owner decisions.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO)) if str(REPO) not in sys.path else None
from tools.alpha import run_alpha_hunter as hunter  # noqa: E402
from src.execution_gateway.gateway import GatewayError  # noqa: E402
from src.live_pilot import hunter_cycle  # noqa: E402


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        raise GatewayError('PILOT_CLI_INVALID')


def main(argv=None, *, dependencies=None):
    parser = _Parser(description='Finite foreground hunter pilot cycle; separate activation required.')
    parser.add_argument('command', choices=['run'])
    for name in ('policy', 'owner-record', 'owner-record-sha256', 'state-root', 'hunter-scratch-dir',
                 'hunter-operation'):
        parser.add_argument('--' + name, required=True)
    try:
        args = parser.parse_args(argv)
    except GatewayError:
        print('{"code":"PILOT_CLI_INVALID","status":"REFUSED"}')
        return 2
    try:
        verified = hunter.verify(Path(args.hunter_scratch_dir))
        ok = isinstance(verified, dict) and verified.get('status') == 'VERIFIED'
    except Exception:
        ok = False
    if not ok:
        print('{"code":"HUNTER_VERIFY_FAILED","status":"REFUSED"}')
        return 1
    result = hunter_cycle.run_hunter_cycle_once(
        policy_path=args.policy, owner_record_path=args.owner_record,
        owner_record_sha256=args.owner_record_sha256, state_root=args.state_root,
        hunter_scratch_dir=args.hunter_scratch_dir, hunter_operation=args.hunter_operation,
        dependencies=dependencies)
    print(hunter_cycle._canonical(result).decode('utf-8'))
    return 0 if result['status'] in ('NO_TRADE', 'NO_NEW_EXPOSURE', 'EXIT_RESULT', 'ENTRY_RESULT') else 1


if __name__ == '__main__':
    raise SystemExit(main())
