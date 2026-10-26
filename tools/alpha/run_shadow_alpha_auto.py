"""Bounded foreground repeat driver over the PR254 shadow alpha operator, never orders.

It only schedules native `cycle`/`update_outcomes` and summarizes the native ledger.
No daemon, retry, catch-up burst or new source. See docs/shadow_alpha_auto_cycle_contract.md.
"""
from __future__ import annotations

import argparse
from collections import Counter
from contextlib import contextmanager
import json
import os
from pathlib import Path
import re
import signal
import sys
import time

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO)) if str(REPO) not in sys.path else None
from tools.alpha import run_shadow_alpha_cycle as native  # noqa: E402

D = native.D
Stop, need, put, read, digest = native.Stop, native.need, native.put, native.read, native.digest
SCHEMA = 'shadow-alpha-auto-v1'
MAX_CYCLES = 12
MAX_RUNTIME_S = 6 * 3600
MIN_RUNTIME_S = 300
# Native acquisition deadline is 120 s; analysis/outcome replay needs headroom.
DISPATCH_RESERVE_S = 150
LATE_TOLERANCE_S = 5
DRIFT_TOLERANCE_S = 5
MAX_CONSECUTIVE_BLOCKED = 3
POLL_S = 1
ROOT_ENTRY = re.compile(r'(config\.json|operation\.lock|auto\.lock|op-[0-9]{6}|auto-[0-9]{6})')
EVENT = re.compile(r'event-[0-9]{3}\.json')


class Clock:
    """Injectable clocks: monotonic schedules and deadlines, wall time is recorded and drift-checked."""
    monotonic = staticmethod(time.monotonic)
    wall_ns = staticmethod(time.time_ns)
    sleep = staticmethod(time.sleep)


def scratch(root):
    root = native.root_check(root)
    for entry in root.iterdir():
        # Anything not produced by the two operators (e.g. an authority claim) fails closed.
        need(ROOT_ENTRY.fullmatch(entry.name) is not None, 'SCRATCH_UNEXPECTED_ENTRY')
        native.safe(entry, directory=entry.name.startswith(('op-', 'auto-')))
    return root


@contextmanager
def session_lock(root):
    # Same kernel-held lock discipline as the native operator, on a separate file:
    # the native per-operation lock must stay free for the native call itself.
    path = native.safe(root / 'auto.lock')
    with path.open('a+b') as handle:
        if os.name == 'nt':
            import msvcrt
            try:
                # Reading a byte another handle has locked raises too: that is contention.
                handle.seek(0)
                if not handle.read(1):
                    handle.write(b'0')
                    handle.flush()
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError:
                raise Stop('AUTO_SESSION_BUSY') from None
        else:
            import fcntl
            try:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError:
                raise Stop('AUTO_SESSION_BUSY') from None
        try:
            yield
        finally:
            if os.name == 'nt':
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)


def sessions(root):
    found = sorted(root.glob('auto-*'))
    for ordinal, path in enumerate(found, 1):
        need(path.name == f'auto-{ordinal:06d}', 'AUTO_JOURNAL_INVALID')
    return found


def events(session):
    files = sorted(p for p in session.iterdir() if p.name.startswith('event-'))
    for index, path in enumerate(files, 1):
        need(path.name == f'event-{index:03d}.json', 'AUTO_JOURNAL_INVALID')
    return files


def verify_sessions(root):
    """Cold check of driver evidence and its bindings to native terminals; writes nothing."""
    rows = []
    for session in sessions(root):
        started = read(session / 'started.json')
        need(started.get('schema') == SCHEMA, 'AUTO_JOURNAL_INVALID')
        names = {p.name for p in session.iterdir()}
        need(names <= {'started.json', 'terminal.json'} | {p.name for p in events(session)}, 'AUTO_JOURNAL_INVALID')
        log = [read(p) for p in events(session)]
        for item in log:
            if item.get('state') in ('COMPLETED', 'NATIVE_BLOCKED'):
                op = native.safe(root / item['native_operation'] / 'terminal.json')
                need(digest(op.read_bytes()) == item['native_terminal_sha256'], 'AUTO_NATIVE_BINDING_MISMATCH')
        terminal = read(session / 'terminal.json') if 'terminal.json' in names else None
        if terminal is not None and terminal['status'] != 'INTERRUPTED_OR_UNKNOWN':
            need(terminal['events_sha256'] == {p.name: digest(p.read_bytes()) for p in events(session)}, 'AUTO_JOURNAL_HASH_MISMATCH')
        rows.append({'session': session.name, 'status': terminal['status'] if terminal else 'IN_PROGRESS_OR_UNKNOWN',
                     'events': log})
    return rows


def summarize(root):
    """Derive (never redefine) counts from the verified native ledger. Missing is UNKNOWN, not zero."""
    checked = native.verify(root)
    auto = verify_sessions(root)
    kinds, statuses, requests = Counter(), Counter(), Counter()
    market_occurrences, markets, forecast_occurrences = 0, set(), 0
    predictions, events_seen, actions, reasons = set(), set(), Counter(), Counter()
    scored = unscorable = 0
    research_ev, learning, outcome_states, delays = [], None, Counter(), {}
    for op, terminal in native.all_results(root):
        kind = read(op / 'started.json')['kind']
        result = terminal['result']
        kinds[kind] += 1
        statuses[f"{kind}:{result['status']}"] += 1
        for receipt in terminal['receipts']:
            requests[receipt['state']] += 1
        if kind == 'CYCLE':
            for receipt in terminal['receipts']:
                if receipt['url'] == native.DISCOVERY_URL and receipt['state'] == 'AVAILABLE':
                    # Latest frozen discovery value per market; an observation, not a venue admission check.
                    for market in native.source_data(op, receipt):
                        delays[market['id']] = str(market.get('secondsDelay', 'ABSENT'))
            rows = result.get('market_rows', [])
            market_occurrences += len(rows)
            markets.update(r['market_id'] for r in rows)
            forecast_occurrences += len(result.get('forecasts', []))
            predictions.update(f['prediction_id'] for f in result.get('forecasts', []))
            events_seen.update(f['event_id'] for f in result.get('forecasts', []))
            for score in result.get('scores', []):
                actions[score['action']] += 1
                reasons[score['reason']] += 1
                if score.get('completion_ev') is None:
                    unscorable += 1
                else:
                    scored += 1
                if score['action'] == 'RESEARCH':
                    research_ev.append(D(score['conservative_ev_if_filled']))
        if kind == 'OUTCOMES' and result['status'] == 'OUTCOMES_RECORDED':
            outcome_states.update(o['state'] for o in result['outcomes'])
            learning = result['learning']
    metrics = learning['metrics'] if learning else []
    def mean(key, field):
        return str(sum(D(m[key][field]) for m in metrics) / len(metrics)) if metrics else 'UNKNOWN'
    actionable = actions['SHADOW_CANDIDATE']
    return {'schema': SCHEMA, 'native_verify': checked,
        'operations': dict(kinds), 'operation_status': dict(statuses),
        'requests': {'attempted': checked['recorded_network_attempts'], 'succeeded': requests['AVAILABLE'],
                     'failed': requests['UNAVAILABLE'], 'outcome_unknown': checked['network_attempt_outcome_unknown'],
                     'interrupted_operations': checked['interrupted_or_unknown'], 'fresh_attempts': 0},
        'markets': {'unique': len(markets), 'occurrences': market_occurrences},
        'forecasts': {'unique_predictions': len(predictions), 'unique_events': len(events_seen),
                      'occurrences': forecast_occurrences},
        'outcome_candidates': {'scorable': scored, 'unscorable': unscorable, 'actions': dict(actions),
                               'reasons': dict(reasons)},
        'economics': {'evidence_class': 'CONDITIONAL_FULL_FILL_SCENARIO_NOT_ACTIONABLE',
                      'research_scenarios': len(research_ev),
                      'conservative_ev_if_filled_range': [str(min(research_ev)), str(max(research_ev))] if research_ev else None,
                      'per_intended_order_ev': 'UNKNOWN_UNMEASURED_FILL_RATE', 'fill_probability': 'UNKNOWN'},
        'forecast_quality': {'evidence_class': 'PUBLISHER_FORECAST_VS_MARKET_MIDPOINT',
                             'outcome_states': dict(outcome_states),
                             'independent_resolved_events': learning['independent_events'] if learning else 0,
                             'mean_brier': {'forecast': mean('forecast', 'brier'), 'market': mean('market', 'brier')},
                             'mean_log_loss': {'forecast': mean('forecast', 'log_loss'), 'market': mean('market', 'log_loss')},
                             'improvement': learning['status'] if learning else 'IMPROVEMENT_NOT_YET_MEASURABLE'},
        'discovery_seconds_delay': dict(Counter(delays.values())),
        'paper': 'NATIVE_RESEARCH_PAPER_UNLINKED' if kinds['PAPER'] else 'NO_PAPER_SESSION',
        'live_filled_pnl': None, 'realized_profit': None,
        'actionability': 'ACTIONABLE_SHADOW_CANDIDATES' if actionable else 'NO_ACTIONABLE_EDGE',
        'edge_claim': 'NOT_ESTABLISHED', 'statistical_significance': 'NOT_ESTABLISHED',
        'auto_sessions': [{'session': s['session'], 'status': s['status'],
                           'states': dict(Counter(e['state'] for e in s['events'] if 'state' in e))} for s in auto],
        'account_attempts': 0, 'wallet_attempts': 0, 'order_attempts': 0, 'provider_calls': 0}


def begin(root, settings, clock):
    prior = sessions(root)
    for session in prior:
        safe_session = native.safe(session, directory=True)
        if not (safe_session / 'terminal.json').exists():
            need((safe_session / 'started.json').is_file(), 'AUTO_JOURNAL_INVALID')
            # Marker only; earlier events and every native sub-ledger stay untouched.
            put(safe_session / 'terminal.json', {'status': 'INTERRUPTED_OR_UNKNOWN',
                'started_sha256': digest((safe_session / 'started.json').read_bytes())})
    path = root / f'auto-{len(prior) + 1:06d}'
    path.mkdir()
    put(path / 'started.json', dict(schema=SCHEMA, ordinal=len(prior) + 1, started_ns=clock.wall_ns(), **settings))
    return path


class Session:
    def __init__(self, path, clock):
        self.path, self.clock, self.count = path, clock, 0

    def log(self, **event):
        self.count += 1
        put(self.path / f'event-{self.count:03d}.json', dict(event, wall_ns=self.clock.wall_ns()))
        return event


def dispatch(root, session, slot, kind, call, fetcher_type):
    before = len(list(root.glob('op-*')))
    session.log(slot=slot, kind=kind, type='DISPATCH_STARTED', native_operation=f'op-{before + 1:06d}')
    try:
        result = call(root, fetcher_type=fetcher_type)
    except Stop as error:
        # Native refused before or during its own journal (busy, corrupt history): stop the session.
        return session.log(slot=slot, kind=kind, state='FAILED_CLOSED', reason=str(error))
    except OSError:
        # On Windows native lock contention surfaces as an OS error before OPERATION_BUSY.
        return session.log(slot=slot, kind=kind, state='FAILED_CLOSED', reason='NATIVE_IO_OR_LOCK_ERROR')
    op = native.safe(root / f'op-{before + 1:06d}', directory=True)
    need(read(op / 'started.json')['kind'] == kind, 'AUTO_NATIVE_BINDING_MISMATCH')
    state = 'NATIVE_BLOCKED' if result['status'] == 'BLOCKED' else 'COMPLETED'
    return session.log(slot=slot, kind=kind, state=state, native_operation=op.name,
                       native_status=result['status'], native_reason=result.get('reason'),
                       native_terminal_sha256=digest((op / 'terminal.json').read_bytes()))


def run(root, *, max_cycles, interval_seconds, outcome_every, max_runtime_seconds=MAX_RUNTIME_S,
        clock=Clock, fetcher_type=native.Fetcher):
    need(type(max_cycles) is int and 1 <= max_cycles <= MAX_CYCLES, 'SCHEDULE_INVALID')
    need(type(interval_seconds) is int and 60 <= interval_seconds <= 3600, 'SCHEDULE_INVALID')
    need(type(outcome_every) is int and 1 <= outcome_every <= MAX_CYCLES, 'SCHEDULE_INVALID')
    need(type(max_runtime_seconds) is int and MIN_RUNTIME_S <= max_runtime_seconds <= MAX_RUNTIME_S, 'SCHEDULE_INVALID')
    root = scratch(root)
    settings = {'max_cycles': max_cycles, 'interval_seconds': interval_seconds, 'outcome_every': outcome_every,
                'max_runtime_seconds': max_runtime_seconds}
    with session_lock(root):
        # Cold history check before any new evidence or dispatch.
        native.verify(root)
        verify_sessions(root)
        path = begin(root, settings, clock)
        session = Session(path, clock)
        mono0, wall0 = clock.monotonic(), clock.wall_ns()
        deadline = mono0 + max_runtime_seconds
        status, blocked = 'COMPLETED', 0

        def check():
            drift = (clock.wall_ns() - wall0) / 1e9 - (clock.monotonic() - mono0)
            if abs(drift) > DRIFT_TOLERANCE_S:
                return 'CLOCK_DRIFT'
            return 'DEADLINE' if clock.monotonic() >= deadline else None

        def reserve():
            return deadline - clock.monotonic() >= DISPATCH_RESERVE_S

        try:
            for slot in range(1, max_cycles + 1):
                target = mono0 + (slot - 1) * interval_seconds
                if target >= deadline:
                    session.log(slot=slot, kind='CYCLE', state='NOT_REACHED_DEADLINE')
                    continue
                while clock.monotonic() < target:
                    stop = check()
                    if stop:
                        break
                    clock.sleep(min(POLL_S, target - clock.monotonic()))
                stop = check()
                if stop:
                    status = stop
                    break
                if clock.monotonic() - target > LATE_TOLERANCE_S:
                    # Never compress missed slots into a burst; the slot stays visible.
                    session.log(slot=slot, kind='CYCLE', state='MISSED_LATE')
                    continue
                if not reserve():
                    session.log(slot=slot, kind='CYCLE', state='SKIPPED_DEADLINE_RESERVE')
                    continue
                event = dispatch(root, session, slot, 'CYCLE', native.cycle, fetcher_type)
                if event['state'] == 'FAILED_CLOSED':
                    status = 'FAILED_CLOSED'
                    break
                blocked = blocked + 1 if event['state'] == 'NATIVE_BLOCKED' else 0
                if blocked >= MAX_CONSECUTIVE_BLOCKED:
                    status = 'CONSECUTIVE_BLOCKED'
                    break
                if slot % outcome_every == 0:
                    stop = check()
                    if stop:
                        status = stop
                        break
                    if not reserve():
                        session.log(slot=slot, kind='OUTCOMES', state='SKIPPED_DEADLINE_RESERVE')
                        continue
                    event = dispatch(root, session, slot, 'OUTCOMES', native.update_outcomes, fetcher_type)
                    if event['state'] == 'FAILED_CLOSED':
                        status = 'FAILED_CLOSED'
                        break
        except KeyboardInterrupt:
            # A native operation left without terminal is marked INTERRUPTED_OR_UNKNOWN by the next native call.
            session.log(type='OPERATOR_INTERRUPT', state='INTERRUPTED')
            status = 'INTERRUPTED'
        summary = summarize(root)
        for row in summary['auto_sessions']:
            if row['session'] == path.name:
                row['status'] = status
        put(path / 'terminal.json', {'status': status, 'ended_ns': clock.wall_ns(),
            'elapsed_monotonic_ms': int((clock.monotonic() - mono0) * 1000), 'summary': summary,
            'events_sha256': {p.name: digest(p.read_bytes()) for p in events(path)}})
    return dict(summary, session=path.name, session_status=status)


def status(root):
    return summarize(scratch(root))


def human(result):
    lines = [f"session {result.get('session', '-')}: {result.get('session_status', 'STATUS_ONLY')}",
             f"native operations {result['operations']} (interrupted {result['requests']['interrupted_operations']})",
             f"requests attempted {result['requests']['attempted']} ok {result['requests']['succeeded']} "
             f"failed {result['requests']['failed']} unknown {result['requests']['outcome_unknown']}",
             f"markets unique {result['markets']['unique']} / occurrences {result['markets']['occurrences']}; "
             f"forecast events {result['forecasts']['unique_events']} / occurrences {result['forecasts']['occurrences']}",
             f"outcome candidates scorable {result['outcome_candidates']['scorable']} unscorable "
             f"{result['outcome_candidates']['unscorable']} actions {result['outcome_candidates']['actions']}",
             f"resolved events {result['forecast_quality']['independent_resolved_events']}; "
             f"brier forecast {result['forecast_quality']['mean_brier']['forecast']} market {result['forecast_quality']['mean_brier']['market']}",
             f"{result['actionability']}; per-order EV {result['economics']['per_intended_order_ev']}; "
             'orders/accounts/provider calls 0']
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    go = sub.add_parser('run')
    go.add_argument('--scratch-dir', required=True)
    go.add_argument('--max-cycles', type=int, required=True)
    go.add_argument('--interval-seconds', type=int, required=True)
    go.add_argument('--outcome-every', type=int, required=True)
    go.add_argument('--max-runtime-seconds', type=int, default=MAX_RUNTIME_S)
    sub.add_parser('status').add_argument('--scratch-dir', required=True)
    args = parser.parse_args()
    def terminate(*_):
        raise KeyboardInterrupt
    # Graceful termination takes the same recorded INTERRUPTED path as Ctrl+C.
    signal.signal(signal.SIGTERM, terminate)
    try:
        root = native.safe(args.scratch_dir, directory=True)
        if args.command == 'run':
            result = run(root, max_cycles=args.max_cycles, interval_seconds=args.interval_seconds,
                         outcome_every=args.outcome_every, max_runtime_seconds=args.max_runtime_seconds)
        else:
            result = status(root)
        # Ledger-derived aggregates only; raw public metadata stays in the scratch journal.
        print(human(result), file=sys.stderr)
        print(json.dumps(result, sort_keys=True, default=str))
        return 0 if result.get('session_status', 'COMPLETED') == 'COMPLETED' else 1
    except Exception as error:
        print(json.dumps({'status': 'BLOCKED', 'reason': str(error) if isinstance(error, Stop) else 'INPUT_OR_PATH_INVALID'}))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
