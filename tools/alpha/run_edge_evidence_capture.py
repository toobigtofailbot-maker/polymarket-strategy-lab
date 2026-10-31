"""One finite NWS research capture; hashes/replay never grant trading authority."""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime, format_datetime
from pathlib import Path
import socket
import sys
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from tools.alpha import run_alpha_hunter as H
from tools.alpha import run_near_term_market_screener as scanner
from src.data_layer.analytical_research import alpha_factory_registry as registry

CONFIG = dict(max_gets=40, max_candidates=6, timeout_s=10, max_bytes=2_000_000,
              duration_s=7200, categories=['rain'], provider_budget_usd='0')
STATUSES = frozenset(('HTTP_2XX HTTP_4XX HTTP_5XX REDIRECT_REFUSED TIMEOUT OVERSIZE '
    'TRANSPORT_UNAVAILABLE ENDPOINT_REFUSED CLOCK_REFUSED BUDGET_EXHAUSTED').split())


def code_hashes():
    """Exact code bytes, including native rule/forecast parsers; not source attestation."""
    return {name: H.digest(Path(module.__file__).read_bytes()) for name, module in
            (('hunter', H), ('shadow', H.S), ('venue', H.venue), ('rules', H.QDR), ('weather', H.NDFD))}


def allowed(url, anchor):
    if type(url) is not str or len(url) > 512:
        return False
    return (url in {H.rain_event_url(anchor+timedelta(days=i)) for i in (1, 2)}
            or H._NWS_RE.fullmatch(url) is not None
            or url.startswith('https://clob.polymarket.com/book?token_id=') and H.S.url_ok(url))


def public_read(url, timeout, maximum):
    """Fixed caller-validated endpoint, no proxies/cookies/redirects or retry."""
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), scanner.NoRedirect())
    request = urllib.request.Request(url, headers={'Accept': 'application/json',
        'User-Agent': 'polymarket-strategy-lab/S10-EDGE-EVIDENCE-ACTIVATION-01 (public research)'})
    deadline = time.monotonic()+timeout
    try:
        with opener.open(request, timeout=timeout) as response:
            length = response.headers.get('Content-Length')
            if length is not None and (not length.isascii() or not length.isdecimal() or int(length) > maximum):
                return 'OVERSIZE', None, None, response.status
            raw = bytearray()
            while True:
                remaining = deadline-time.monotonic()
                H.need(remaining > 0, 'TIMEOUT')
                # A closed socket means its bytes are already buffered (not a new read).
                stream = getattr(getattr(response, 'fp', None), 'raw', None)
                sock = getattr(stream, '_sock', None)
                if sock is not None and sock.fileno() >= 0:
                    sock.settimeout(remaining)
                chunk = response.read1(min(65536, maximum+1-len(raw)))
                if time.monotonic() > deadline:
                    return 'TIMEOUT', None, None, None
                if not chunk:
                    break
                raw.extend(chunk)
                if len(raw) > maximum:
                    return 'OVERSIZE', None, None, None
            if length is not None and len(raw) != int(length):
                return 'TRANSPORT_UNAVAILABLE', None, None, None
            return 'HTTP_2XX', bytes(raw), response.headers.get('Date'), response.status
    except urllib.error.HTTPError as error:
        status = error.code
        error.close()
        return ('REDIRECT_REFUSED' if 300 <= status < 400 else
                'HTTP_4XX' if status < 500 else 'HTTP_5XX'), None, None, status
    except scanner.RedirectRefused:
        return 'REDIRECT_REFUSED', None, None, None
    except (TimeoutError, socket.timeout):
        return 'TIMEOUT', None, None, None
    except Exception:
        return 'TRANSPORT_UNAVAILABLE', None, None, None


class Fetcher:
    def __init__(self, operation, *, clock_ns=time.time_ns, monotonic=time.monotonic, transport=public_read):
        self.operation, self.receipts = operation, []
        self.clock_ns, self.monotonic, self.transport = clock_ns, monotonic, transport
        self.last_ns = clock_ns()
        self.anchor = datetime.fromtimestamp(self.last_ns//10**9, timezone.utc).date()
        self.start = monotonic()
        self.refusal = None

    def check(self, ok, code):
        if not ok:
            self.refusal = code
        H.need(self.refusal is None, self.refusal or code)

    def get(self, url):
        kill = self.operation.parent/'capture-killed.json'
        self.check(not (kill.exists() or kill.is_symlink()), 'KILLED')
        self.check(allowed(url, self.anchor), 'ENDPOINT_REFUSED')
        self.check(len(self.receipts) < CONFIG['max_gets'] and
               0 <= self.monotonic()-self.start < CONFIG['duration_s'], 'BUDGET_EXHAUSTED')
        started = self.clock_ns()
        self.check(type(started) is int and started >= self.last_ns, 'CLOCK_REFUSED')
        i = len(self.receipts)+1
        receipt = dict(url=url, started_ns=started, state='UNAVAILABLE', http_date=None,
                       sha256=None, raw_file=None)
        self.receipts.append(receipt)
        H.S.put(self.operation/f'request-{i:02d}.started.json', dict(url=url, started_ns=started))
        status, raw, date, http = self.transport(url, CONFIG['timeout_s'], CONFIG['max_bytes'])
        self.check(valid_transport(status, http), 'INPUT_INVALID')
        received = self.clock_ns()
        self.check(type(received) is int and received >= started, 'CLOCK_REFUSED')
        self.last_ns = received
        if (status == 'HTTP_2XX' and type(raw) is bytes and len(raw) <= CONFIG['max_bytes']
                and not H.S.SECRET.search(raw)):
            try:
                H.S.decode(raw)
                name = f'source-{i:02d}.json'
                with H.S.safe(self.operation/name).open('xb') as stream:
                    stream.write(raw)
                try:
                    stamp = parsedate_to_datetime(date)
                    H.need(stamp.tzinfo is not None, 'INPUT_INVALID')
                    date = format_datetime(stamp.astimezone(timezone.utc), usegmt=True)
                except Exception:
                    date = None
                receipt.update(state='AVAILABLE', sha256=H.digest(raw), raw_file=name, http_date=date)
            except (ValueError, H.Stop):
                pass
        receipt['received_ns'] = received
        H.S.put(self.operation/f'receipt-{i:02d}.json', receipt)
        H.S.put(self.operation/f'transport-{i:02d}.json', dict(status=status, http_status=http,
            receipt_sha256=H.digest((self.operation/f'receipt-{i:02d}.json').read_bytes())))
        self.check(http not in (401, 403, 451) and status != 'REDIRECT_REFUSED', 'ENDPOINT_REFUSED')
        return H.data(self.operation, receipt)


def valid_transport(status, http):
    if type(status) is not str or status not in STATUSES:
        return False
    if http is not None and (type(http) is not int or not 100 <= http <= 599):
        return False
    ranges = dict(HTTP_2XX=(200, 299), HTTP_4XX=(400, 499), HTTP_5XX=(500, 599), REDIRECT_REFUSED=(300, 399))
    if status == 'HTTP_2XX' and http is None:
        return False
    return http is None or status not in ranges or ranges[status][0] <= http <= ranges[status][1]


def run(scratch, *, transport=public_read, clock_ns=time.time_ns, monotonic=time.monotonic):
    """New external scratch only. Native hunter does all rule/forecast/Alpha work."""
    from src.live_pilot.provenance import empty_report, verify_capture
    try:
        root = H.S.safe(Path(scratch), directory=True)
        H.need(not root.exists(), 'INPUT_INVALID')
        root.mkdir(mode=0o700)
        H.S.put(root/'capture-started.json', dict(config=CONFIG, source_hashes=code_hashes()))
        alpha = root/'research-alpha.sqlite3'
        H.need(registry.initialize_alpha_factory_registry(str(alpha)).is_valid, 'INPUT_INVALID')
        def factory(op):
            return Fetcher(op, clock_ns=clock_ns, monotonic=monotonic, transport=transport)
        result = H.run(root, alpha, {'rain'}, fetcher_type=factory, clock_ns=clock_ns)
        H.S.put(root/'capture-final.json', dict(schema_id='edge-evidence-capture', schema_version='1.0.0',
            started_sha256=H.digest((root/'capture-started.json').read_bytes()),
            native_terminal_sha256=H.digest((root/'op-000001/terminal.json').read_bytes()),
            network_attempts=result['network_attempts']))
        return verify_capture(root)
    except Exception:
        return empty_report('REFUSED', 'SOURCE_CAPTURE_INCOMPLETE')


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise ValueError('INPUT_INVALID')


def main(argv=None):
    from src.live_pilot.provenance import empty_report, verify_capture
    try:
        parser = Parser(description=__doc__)
        parser.add_argument('command', choices=('run', 'verify'))
        parser.add_argument('--scratch-dir', required=True)
        args = parser.parse_args(argv)
        result = run(args.scratch_dir) if args.command == 'run' else verify_capture(args.scratch_dir)
    except Exception:
        result = empty_report('REFUSED', 'SOURCE_INVALID')
    print(H.canonical(result).decode())
    return 0 if result['status'] == 'REPLAY_VERIFIED' else 1


if __name__ == '__main__':
    raise SystemExit(main())
