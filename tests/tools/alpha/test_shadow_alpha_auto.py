"""Offline replicas and fake clocks test scheduling logic only; real receipts are separate."""
from datetime import datetime, timezone
import inspect
import json
from pathlib import Path
import socket
import subprocess
import sys

import pytest

from tools.alpha import run_shadow_alpha_auto as auto
from tools.alpha import run_shadow_alpha_cycle as tool
from tests.tools.alpha import test_shadow_alpha_cycle as base

NOW, START = base.NOW, base.START
LATER = START + 12_000_000_000_000


class FakeClock:
    def __init__(self):
        self.mono, self.wall = 1000.0, NOW

    def monotonic(self):
        return self.mono

    def wall_ns(self):
        return self.wall

    def sleep(self, seconds):
        self.advance(seconds)

    def advance(self, seconds):
        self.mono += seconds
        self.wall += int(seconds * 1_000_000_000)


class Replica:
    """Recorded-input harness: per-GET cost on the fake clock and optional data mutation."""
    clock, cost, now = None, 1, NOW

    def __init__(self, operation):
        self.operation, self.receipts = operation, []

    def payload(self, url):
        if url == tool.DISCOVERY_URL:
            return [base.market()]
        if url.startswith(tool.ESPN + 'scoreboard?'):
            return {'events': [{'id': '401909877', 'competitions': base.summary()['header']['competitions']}]}
        if url.startswith(tool.ESPN + 'summary?'):
            return base.finished()[2] if self.now == LATER else base.summary()
        if url == tool.venue.gamma_market_url('12345'):
            return base.finished()[1]
        return base.book('222' if '222' in url else '111')

    def mutate(self, url, data):
        return data

    def get(self, url):
        if self.clock is not None:
            self.clock.advance(self.cost)
        data = self.mutate(url, self.payload(url))
        raw = tool.canonical(data)
        name = f'source-{len(self.receipts) + 1:02d}.json'
        (self.operation / name).write_bytes(raw)
        r = dict(base.receipt(self.now), url=url, state='AVAILABLE', publication_time=None, raw_file=name, sha256=tool.digest(raw))
        self.receipts.append(r)
        tool.put(self.operation / f'request-{len(self.receipts):02d}.started.json', {'url': url, 'started_ns': r['started_ns']})
        tool.put(self.operation / f'receipt-{len(self.receipts):02d}.json', r)
        return data


@pytest.fixture
def native_clock(monkeypatch):
    state = {'now': NOW}
    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 10, 26, 18, tzinfo=timezone.utc)
    monkeypatch.setattr(tool, 'datetime', Clock)
    monkeypatch.setattr(tool.time, 'time_ns', lambda: state['now'])
    monkeypatch.setattr(socket, 'socket', lambda *a, **k: pytest.fail('network dispatched in offline test'))
    return state


def fetcher(clock, cost=1, **overrides):
    return type('F', (Replica,), dict(clock=clock, cost=cost, **overrides))


def go(root, clock, fetcher_type, **kwargs):
    settings = dict(max_cycles=2, interval_seconds=60, outcome_every=12, max_runtime_seconds=600)
    settings.update(kwargs)
    return auto.run(root, clock=clock, fetcher_type=fetcher_type, **settings)


def session_events(root, name='auto-000001'):
    return [tool.read(p) for p in sorted((root / name).glob('event-*.json'))]


def states(root, name='auto-000001'):
    return [e['state'] for e in session_events(root, name) if 'state' in e]


def fresh(tmp_path, name):
    (tmp_path / name).mkdir()
    return base.init(tmp_path / name)


def files(root):
    return {str(p.relative_to(root)): tool.digest(p.read_bytes()) for p in sorted(root.rglob('*')) if p.is_file()}


def test_schedule_bounds(tmp_path, native_clock):
    for bad in (dict(max_cycles=13), dict(max_cycles=0), dict(max_cycles=True), dict(interval_seconds=59),
                dict(interval_seconds=3601), dict(outcome_every=0), dict(max_runtime_seconds=21601),
                dict(max_runtime_seconds=299)):
        with pytest.raises(tool.Stop, match='SCHEDULE_INVALID'):
            go(fresh(tmp_path, str(len(list(tmp_path.iterdir())))), FakeClock(), Replica, **bad)
    clock = FakeClock()
    root = fresh(tmp_path, 'cadence')
    result = go(root, clock, fetcher(clock), max_cycles=3)
    assert result['session_status'] == 'COMPLETED' and states(root) == ['COMPLETED'] * 3
    starts = [e['wall_ns'] for e in session_events(root) if e.get('type') == 'DISPATCH_STARTED']
    assert all(b - a >= 60_000_000_000 for a, b in zip(starts, starts[1:]))
    # A slow cycle overruns the next slot: it is recorded as missed, never burst-dispatched.
    clock = FakeClock()
    root = fresh(tmp_path, 'slow')
    assert go(root, clock, fetcher(clock, cost=20), max_cycles=3, outcome_every=2)['session_status'] == 'COMPLETED'
    # The missed slot's due outcome update is visibly skipped too, never deferred into a burst.
    assert [(e['kind'], e['state']) for e in session_events(root) if 'state' in e] == [
        ('CYCLE', 'COMPLETED'), ('CYCLE', 'MISSED_LATE'), ('OUTCOMES', 'MISSED_LATE'), ('CYCLE', 'COMPLETED')]
    # Deadline: insufficient reserve and unreachable slots never dispatch.
    clock = FakeClock()
    root = fresh(tmp_path, 'deadline')
    go(root, clock, fetcher(clock), max_cycles=3, interval_seconds=500, max_runtime_seconds=600)
    assert states(root) == ['COMPLETED', 'SKIPPED_DEADLINE_RESERVE', 'NOT_REACHED_DEADLINE']
    assert tool.read(root / 'auto-000001/terminal.json')['elapsed_monotonic_ms'] <= 600_000
    # Wall-clock drift against the monotonic schedule terminates instead of compressing time.
    clock = FakeClock()
    jump = fetcher(clock, mutate=lambda self, url, data: (setattr(self.clock, 'wall', self.clock.wall + 10_000_000_000), data)[1])
    root = fresh(tmp_path, 'drift')
    assert go(root, clock, jump, max_cycles=3)['session_status'] == 'CLOCK_DRIFT'
    assert states(root) == ['COMPLETED']
    # Ctrl+C while waiting for a slot is recorded; nothing dispatches afterwards.
    class Interrupted(FakeClock):
        def sleep(self, seconds):
            raise KeyboardInterrupt
    clock = Interrupted()
    root = fresh(tmp_path, 'interrupt')
    assert go(root, clock, fetcher(clock), max_cycles=3)['session_status'] == 'INTERRUPTED'
    assert states(root) == ['COMPLETED', 'INTERRUPTED'] and len(list(root.glob('op-*'))) == 1
    assert inspect.signature(auto.run).parameters['fetcher_type'].default is tool.Fetcher


def test_native_reuse(tmp_path, native_clock, monkeypatch):
    calls = []
    for name in ('cycle', 'update_outcomes'):
        original = getattr(tool, name)
        def spy(root, *, fetcher_type, original=original, name=name):
            calls.append(name)
            return original(root, fetcher_type=fetcher_type)
        monkeypatch.setattr(tool, name, spy)
    clock = FakeClock()
    root = base.init(tmp_path)
    result = go(root, clock, fetcher(clock), max_cycles=2, outcome_every=2)
    assert calls == ['cycle', 'cycle', 'update_outcomes']
    kinds = [tool.read(op / 'started.json')['kind'] for op in sorted(root.glob('op-*'))]
    assert kinds == ['CYCLE', 'CYCLE', 'OUTCOMES']
    # The native terminal is the record; the driver only binds its hash.
    for event in session_events(root):
        if event.get('state') == 'COMPLETED':
            assert event['native_terminal_sha256'] == tool.digest((root / event['native_operation'] / 'terminal.json').read_bytes())
    native = tool.read(root / 'op-000001/terminal.json')['result']
    assert result['forecasts']['unique_predictions'] == 1
    assert native['forecasts'][0]['p'] == '0.167' and native['forecasts'][0]['method'] == tool.METHOD
    assert result['native_verify']['completed'] == 3 and result['native_verify']['fresh_attempts'] == 0
    assert result['session_public_requests'] == 12
    source = Path(auto.__file__).read_text()
    for duplicate in ('def probability', 'def economics', 'def learning', 'def resolution', 'urllib', 'espn.com'):
        assert duplicate not in source


def test_evidence_denominator(tmp_path, native_clock):
    clock = FakeClock()
    root = fresh(tmp_path, 'ok')
    result = go(root, clock, fetcher(clock))
    assert result['markets'] == {'unique': 1, 'occurrences': 2}
    assert result['forecasts'] == {'unique_predictions': 1, 'unique_events': 1, 'occurrences': 2}
    assert result['requests'] == {'attempted': 12, 'succeeded': 12, 'failed': 0, 'outcome_unknown': 0,
                                  'interrupted_operations': 0}
    candidates = result['outcome_candidates']
    assert candidates['scorable'] + candidates['unscorable'] == 4 == sum(candidates['actions'].values())
    # Failed public requests are counted; three blocked cycles stop the session.
    class Down(Replica):
        def get(self, url):
            r = {'url': url, 'started_ns': NOW, 'state': 'UNAVAILABLE', 'http_date': None, 'publication_time': None,
                 'sha256': None, 'raw_file': None, 'received_ns': NOW}
            self.receipts.append(r)
            tool.put(self.operation / f'request-{len(self.receipts):02d}.started.json', {'url': url, 'started_ns': NOW})
            tool.put(self.operation / f'receipt-{len(self.receipts):02d}.json', r)
    root = fresh(tmp_path, 'down')
    down = go(root, FakeClock(), Down, max_cycles=5, max_runtime_seconds=900)
    assert down['session_status'] == 'CONSECUTIVE_BLOCKED' and states(root) == ['NATIVE_BLOCKED'] * 3
    assert down['requests']['attempted'] == down['requests']['failed'] == 3
    assert down['operation_status'] == {'CYCLE:BLOCKED': 3}
    # Session lock contention refuses; native lock contention fails closed with no native occurrence.
    root = fresh(tmp_path, 'busy')
    with auto.session_lock(root):
        with pytest.raises(tool.Stop, match='AUTO_SESSION_BUSY'):
            go(root, FakeClock(), Replica)
    with tool.operation_lock(root):
        busy = go(root, FakeClock(), Replica)
    assert busy['session_status'] == 'FAILED_CLOSED' and not list(root.glob('op-*'))
    assert len(list(root.glob('auto-*'))) == 1 and session_events(root)[-1]['reason'] in ('OPERATION_BUSY', 'NATIVE_IO_OR_LOCK_ERROR')


class Mutating(Replica):
    changes = {}

    def mutate(self, url, data):
        for key, change in self.changes.items():
            if key in url:
                change(data)
        return data


def test_source_invariants(tmp_path, native_clock):
    def stale(book):
        book['timestamp'] = str((NOW - 60_000_000_000) // 1_000_000)
    def unknown_fees(markets):
        del markets[0]['feesEnabled']
    def changed_rule(markets):
        markets[0]['description'] = markets[0]['description'].replace('including any', 'excluding')
    def started(summary):
        summary['header']['competitions'][0]['status']['type']['state'] = 'in'
    scored = 'CYCLE:SHADOW_INTELLIGENCE_REAL_EVIDENCE_PASS'
    cases = {'book?': (stale, {'BOOK_STALE': 2}, 1, 'CYCLE:DATA_INSUFFICIENT'),
             'gamma-api': (unknown_fees, None, 1, 'CYCLE:DATA_INSUFFICIENT'),
             'summary?': (started, {}, 0, 'CYCLE:DATA_INSUFFICIENT'),
             'gamma-api.polymarket.com/markets?tag': (changed_rule, {}, 0, 'CYCLE:DATA_INSUFFICIENT')}
    for key, (change, reasons, forecasts, status) in cases.items():
        root = fresh(tmp_path, str(len(list(tmp_path.iterdir()))))
        result = go(root, FakeClock(), type('M', (Mutating,), {'changes': {key: change}}), max_cycles=1)
        candidates = result['outcome_candidates']
        # Native fail-closed decisions arrive unchanged: nothing becomes scorable or actionable.
        assert candidates['scorable'] == 0 and result['actionability'] == 'NO_ACTIONABLE_EDGE', key
        assert result['operation_status'] == {status: 1} and status != scored, key
        assert result['forecasts']['occurrences'] == forecasts, key
        if reasons is not None:
            assert candidates['reasons'] == reasons, key
    # No outcome lookahead: before kickoff the native outcome update dispatches nothing.
    root = fresh(tmp_path, 'early')
    result = go(root, FakeClock(), Replica, max_cycles=1, outcome_every=1)
    assert result['operation_status'] == {'CYCLE:SHADOW_INTELLIGENCE_REAL_EVIDENCE_PASS': 1, 'OUTCOMES:OUTCOMES_RECORDED': 1}
    assert tool.read(root / 'op-000002/terminal.json')['receipts'] == []
    # Venue delay is observed from the frozen discovery bytes, never assumed.
    assert result['discovery_seconds_delay'] == {'ABSENT': 1}
    def delayed(markets):
        markets[0]['secondsDelay'] = 3
    root = fresh(tmp_path, 'delayed')
    result = go(root, FakeClock(), type('S', (Mutating,), {'changes': {'tag_id': delayed}}), max_cycles=1)
    assert result['discovery_seconds_delay'] == {'3': 1}
    assert not tool.url_ok('https://example.com/markets') and tool.DISCOVERY_URL.startswith('https://gamma-api.polymarket.com/')


def test_restart_safety(tmp_path, native_clock):
    clock = FakeClock()
    root = fresh(tmp_path, 'shadow')
    go(root, clock, fetcher(clock), max_cycles=1)
    before = files(root)
    status = auto.status(root)
    assert files(root) == before and status['native_verify']['fresh_attempts'] == 0
    assert tool.verify(root)['fresh_attempts'] == 0 and files(root) == before
    # Interrupt mid-cycle: recorded, nothing further dispatched in that session.
    class Crash(Replica):
        def get(self, url):
            if len(self.receipts) == 2:
                raise KeyboardInterrupt
            return super().get(url)
    crashed = go(root, FakeClock(), Crash, max_cycles=3)
    assert crashed['session_status'] == 'INTERRUPTED' and states(root, 'auto-000002') == ['INTERRUPTED']
    assert not (root / 'op-000002/terminal.json').exists() and len(list(root.glob('op-*'))) == 2
    # A crashed session without terminal gets only a marker; native recovery marks the open operation.
    auto.begin(root, {}, FakeClock())
    resumed = go(root, FakeClock(), Replica, max_cycles=1)
    assert tool.read(root / 'auto-000003/terminal.json')['status'] == 'INTERRUPTED_OR_UNKNOWN'
    assert not list((root / 'auto-000003').glob('event-*'))
    assert tool.read(root / 'op-000002/terminal.json')['status'] == 'INTERRUPTED_OR_UNKNOWN'
    assert resumed['native_verify']['interrupted_or_unknown'] == 1 and len(list(root.glob('op-*'))) == 3
    # Requests inside the interrupted operation stay in the denominator.
    requests = resumed['requests']
    assert requests['attempted'] == requests['succeeded'] + requests['failed'] + requests['outcome_unknown'] == 14
    # Tampered driver or native evidence fails closed before any new dispatch.
    event = root / 'auto-000001/event-002.json'
    original = event.read_bytes()
    event.write_bytes(original.replace(b'COMPLETED', b'NATIVE_BLOCKED'))
    with pytest.raises(tool.Stop, match='AUTO_JOURNAL_HASH_MISMATCH'):
        auto.status(root)
    event.write_bytes(original.replace(b'"op-000001"', b'"../other/op-000001"'))
    with pytest.raises(tool.Stop, match='AUTO_JOURNAL_INVALID'):
        auto.status(root)
    event.write_bytes(original)
    marker = root / 'auto-000003/started.json'
    marker_raw = marker.read_bytes()
    marker.write_bytes(marker_raw.replace(b'"ordinal":3', b'"ordinal":9'))
    with pytest.raises(tool.Stop, match='AUTO_JOURNAL_HASH_MISMATCH'):
        auto.status(root)
    marker.write_bytes(marker_raw)
    (root / 'op-000001/source-01.json').write_bytes(b'[]')
    with pytest.raises(tool.Stop, match='HASH_MISMATCH'):
        go(root, FakeClock(), Replica, max_cycles=1)
    assert len(list(root.glob('op-*'))) == 3 and len(list(root.glob('auto-*'))) == 4
    # Unexpected entries, symlinks and checkout paths are refused.
    other = fresh(tmp_path, 'other')
    (other / 'live_authorization.json').write_text('{"live": true}')
    with pytest.raises(tool.Stop, match='SCRATCH_UNEXPECTED_ENTRY'):
        auto.status(other)
    with pytest.raises(tool.Stop, match='PATH_FORBIDDEN'):
        auto.status(tool.REPO / 'scratch')


def test_scratch_symlink_refused(tmp_path):
    # Separate node so a host without symlink privilege skips only this check.
    fresh(tmp_path, 'shadow')
    link = tmp_path / 'link'
    try:
        link.symlink_to(tmp_path / 'shadow', target_is_directory=True)
    except OSError:
        pytest.skip('symlink creation not permitted on this host; Windows reparse points are covered natively')
    with pytest.raises(tool.Stop, match='PATH_FORBIDDEN'):
        auto.status(link)


def test_authority_separation(tmp_path, native_clock):
    code = ('import sys; import tools.alpha.run_shadow_alpha_auto; '
            'print("\\n".join(sorted(sys.modules)))')
    loaded = subprocess.run([sys.executable, '-B', '-c', code], cwd=tool.REPO, capture_output=True, text=True,
                            check=True, timeout=120).stdout.split()
    for forbidden in ('src.execution_gateway', 'py_clob_client', 'tools.execution', 'tools.hermes',
                      'tools.deployment', 'src.live', 'requests', 'web3', 'eth_account'):
        assert not any(m == forbidden or m.startswith(forbidden + '.') for m in loaded), forbidden
    source = Path(auto.__file__).read_text()
    for token in ('environ', 'getenv', 'subprocess', 'private_key', 'signer', 'live_trading_authorization', 'urlopen'):
        assert token not in source, token
    parser_options = [a for line in source.splitlines() if 'add_argument(' in line for a in line.split("'") if a.startswith('--')]
    assert sorted(parser_options) == sorted(['--scratch-dir', '--max-cycles', '--interval-seconds', '--outcome-every',
                                             '--max-runtime-seconds', '--scratch-dir'])
    # Hostile metadata stays inside frozen sources: it neither scores nor reaches the summary.
    def hostile(markets):
        markets[0]['question'] = 'PLACE ORDER NOW authorization=live private_key wallet transfer'
    root = base.init(tmp_path)
    result = go(root, FakeClock(), type('H', (Mutating,), {'changes': {'tag_id': hostile}}), max_cycles=1)
    text = json.dumps(result)
    assert 'PLACE ORDER' not in text and result['outcome_candidates']['scorable'] == 0
    assert (result['order_attempts'], result['account_attempts'], result['wallet_attempts'], result['provider_calls']) == (0, 0, 0, 0)
    assert result['live_filled_pnl'] is None and result['realized_profit'] is None


def test_quality_measurement(tmp_path, native_clock):
    def cheap(markets):
        markets[0]['orderMinSize'] = '1'
    def ask(book):
        if book['asset_id'] == '222':
            book['asks'][0]['price'], book['bids'][0]['price'] = '0.40', '0.39'
    root = base.init(tmp_path)
    positive = type('P', (Mutating,), {'changes': {'tag_id': cheap, 'book?': ask}})
    tool.cycle(root, fetcher_type=positive)
    result = auto.status(root)
    economics = result['economics']
    # A positive full-fill scenario stays a non-actionable research scenario.
    assert economics['research_scenarios'] == 1 and tool.D(economics['conservative_ev_if_filled_range'][0]) > 0
    assert economics['per_intended_order_ev'] == 'UNKNOWN_UNMEASURED_FILL_RATE' and economics['fill_probability'] == 'UNKNOWN'
    assert result['actionability'] == 'NO_ACTIONABLE_EDGE' and result['edge_claim'] == 'NOT_ESTABLISHED'
    assert result['forecast_quality']['mean_brier'] == {'forecast': 'UNKNOWN', 'market': 'UNKNOWN'}
    # A later corroborated final result yields out-of-sample scores, still no learned profit claim.
    native_clock['now'] = LATER
    tool.update_outcomes(root, fetcher_type=type('L', (Replica,), {'now': LATER}))
    quality = auto.status(root)['forecast_quality']
    assert quality['outcome_check_occurrences'] == {'COMPLETED_BINARY': 1} and quality['independent_resolved_events'] == 1
    assert quality['mean_brier'] == {'forecast': '0.027889', 'market': '0.3481'}
    assert quality['improvement'] == 'IMPROVEMENT_NOT_YET_MEASURABLE'
    assert auto.status(root)['statistical_significance'] == 'NOT_ESTABLISHED'
