"""Explicit foreground entry point; never installs or starts a service."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.live_pilot.autonomous_cycle import activation_report, run  # noqa: E402


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise ValueError('INPUT_INVALID')


def main(argv=None):
    parser = Parser(description=__doc__)
    parser.add_argument('--report', action='store_true')
    for option in ('policy-path', 'native-policy-path', 'owner-record-path', 'owner-record-sha256',
                   'hunter-scratch-dir', 'alpha-registry-path', 'budget-path', 'executable', 'home'):
        parser.add_argument('--'+option)
    try:
        args = vars(parser.parse_args(argv))
        report = args.pop('report')
        result = activation_report() if report else run(**args)
    except (ValueError, TypeError):
        result = {'status': 'REFUSED', 'code': 'INPUT_INVALID', 'live_active': False}
    print(json.dumps(result, sort_keys=True, separators=(',', ':')))
    return 0 if result.get('status') == 'NO_TRADE' else 1


if __name__ == '__main__':
    raise SystemExit(main())
