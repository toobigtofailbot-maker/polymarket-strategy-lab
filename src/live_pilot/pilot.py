"""One attended, owner-bounded NBA pilot invocation; no activation on import."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from dataclasses import replace
from datetime import datetime, timezone
from decimal import Decimal, localcontext
from email.utils import parsedate_to_datetime
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import uuid
from zoneinfo import ZoneInfo

from src.execution_gateway import live_orch as native
from src.execution_gateway.gate_b import InteractiveGateBSecretProvider
from src.execution_gateway.gateway import GatewayError
from src.execution_feasibility import (
    assess_execution_feasibility, build_execution_intent,
)
from src.exploratory_gate_c import evaluate_exploratory_gate_c, build_exploratory_gate_c_permit
from src.research_runtime.hermes_controlled_runtime.strategy_manager import load_hermes_strategy_manager_store
from src.strategy_lifecycle import load_strategy_lifecycle_store

NS = 1_000_000_000
DAY = 86400 * NS
DISCOVERY_URL = ('https://gamma-api.polymarket.com/markets?tag_id=745&'
                 'sports_market_types=moneyline&closed=false&limit=200&order=gameStartTime&ascending=true')
ESPN = 'https://site.api.espn.com/apis/site/v2/sports/basketball/nba/'
HOST_KEYS = {'repository_root', 'binding_file', 'active_release', 'unit_dir', 'ssh_port'}
OWNER_KEYS = {'schema_id', 'schema_version', 'policy_sha256', 'public_wallet', 'public_signer',
              'release_sha', 'state_root', 'valid_from_utc', 'valid_until_utc'}
DECIMAL_CEILINGS = {
    'max_total_commitment_usd': Decimal('10'), 'max_order_commitment_usd': Decimal('5'),
    'max_realized_pnl_loss_usd': native.MAX_OBSERVED_REALIZED_PNL_LOSS_USD,
    'max_position_pnl_drawdown_usd': native.MAX_OBSERVED_POSITION_PNL_DRAWDOWN_USD,
    'max_cumulative_loss_usd': native.MAX_OBSERVED_CUMULATIVE_CANARY_LOSS_USD,
}
INTEGER_CEILINGS = {'max_admissions_24h': 2, 'max_feeder_age_s': 1800,
                    'max_hermes_assessment_age_s': 86400}
POLICY_KEYS = {
    'schema_id', 'schema_version', 'public_wallet', 'public_signer', 'release_sha', 'host',
    'state_root', 'feeder_root', 'lifecycle_store_path', 'hermes_store_path', 'strategy_version_id',
    'market_predicate', 'side', 'order_type', 'valid_from_utc', 'valid_until_utc',
    'experimental_margin_usd', *DECIMAL_CEILINGS, *INTEGER_CEILINGS,
}
PUBLIC_CODES = frozenset({
    'PILOT_INPUT_INVALID', 'PILOT_PATH_INVALID', 'PILOT_POLICY_INVALID', 'PILOT_TIME_INVALID',
    'PILOT_OWNER_RECORD_INVALID', 'PILOT_OWNER_RECORD_DIGEST_MISMATCH', 'PILOT_OWNER_RECORD_SCOPE_MISMATCH',
    'PILOT_OWNER_RECORD_WINDOW_INVALID', 'PILOT_RUN_BUSY', 'PILOT_STATE_UNAVAILABLE',
    'PILOT_FEEDER_INVALID', 'PILOT_FEEDER_STALE', 'PILOT_EVENT_STARTED', 'PILOT_ASSESSMENT_STALE',
    'PILOT_MARKET_MISMATCH', 'PILOT_VENUE_INVALID', 'MINIMUM_EXCEEDS_CAP', 'PILOT_MARGIN_NOT_MET',
    'PILOT_CUSTODY_UNAVAILABLE', 'PILOT_STRATEGY_UNAVAILABLE', 'PILOT_ASSESSMENT_UNAVAILABLE',
    'PILOT_PERMIT_REFUSED', 'PILOT_PREFLIGHT_REFUSED', 'PILOT_KILLED', 'PILOT_GUARD_MISSING',
    'PILOT_GUARD_REFUSED', 'PILOT_NATIVE_REFUSED',
    *(f'PILOT_GUARD_REFUSED:{suffix}' for suffix in ('POLICY_CHANGED', 'KILL', 'MARKET_BINDING',
       'OWNER_WINDOW', 'LEDGER_TIME', 'ADMISSIONS', 'COMMITMENT', 'LOSS')),
})
NATIVE_CODES = PUBLIC_CODES | frozenset({
    'ONE_CREATE_ATTEMPTED', 'PERMIT_EXPIRED', 'PERMIT_NOT_CURRENT', 'PERMIT_ALREADY_CONSUMED',
    'PERMIT_INVALID', 'PERMIT_INTENT_MISMATCH', 'EXECUTION_INTENT_INVALID', 'LIFECYCLE_STORE_INVALID',
    'HERMES_STORE_INVALID', 'GATE_B_OWNERSHIP_LOCKED', 'UNRESOLVED_PRIOR_MUTATION',
    'RESTART_RECONCILIATION_REQUIRED', 'VENUE_NOT_FEASIBLE', 'LIVE_ORCH_ADMISSION_PERSISTENCE_FAILED',
    'LIVE_ORCH_OUTCOME_PERSISTENCE_FAILED', 'SINGLE_ORDER_LIMIT_EXCEEDED', 'AGGREGATE_COMMITMENT_LIMIT_EXCEEDED',
    'FREE_COLLATERAL_RESERVE_VIOLATED', 'OBSERVED_PNL_GUARD_EXCEEDED', 'SECRET_INPUT_UNAVAILABLE',
})


def _require(condition, code):
    if not condition:
        raise GatewayError(code)


def _digest(raw):
    return hashlib.sha256(raw).hexdigest()


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
                      allow_nan=False).encode('utf-8')


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        _require(key not in result, 'PILOT_INPUT_INVALID')
        result[key] = value
    return result


def _constant(_value):
    raise GatewayError('PILOT_INPUT_INVALID')


def _json(raw):
    value = json.loads(raw.decode('utf-8'), object_pairs_hook=_pairs,
                       parse_float=str, parse_constant=_constant)
    def bounded(item, depth=0):
        _require(depth <= 24, 'PILOT_INPUT_INVALID')
        if isinstance(item, str):
            _require(len(item) <= 16384, 'PILOT_INPUT_INVALID')
        elif isinstance(item, dict):
            _require(len(item) <= 1024, 'PILOT_INPUT_INVALID')
            for key, child in item.items():
                bounded(key, depth + 1)
                bounded(child, depth + 1)
        elif isinstance(item, list):
            _require(len(item) <= 1024, 'PILOT_INPUT_INVALID')
            for child in item:
                bounded(child, depth + 1)
    bounded(value)
    return value


def _path(value):
    _require(isinstance(value, (str, Path)), 'PILOT_PATH_INVALID')
    p = Path(value)
    _require(p.is_absolute(), 'PILOT_PATH_INVALID')
    for part in (p, *p.parents):
        _require(part.name.lower() not in {'.git', '.ssh', 'secrets', 'credentials', 'agent_memory', 'local_data'}
                 and not part.name.lower().startswith('.env'), 'PILOT_PATH_INVALID')
        if part.exists() or part.is_symlink():
            mode = part.lstat()
            _require(not part.is_symlink() and not (getattr(mode, 'st_file_attributes', 0)
                     & stat.FILE_ATTRIBUTE_REPARSE_POINT), 'PILOT_PATH_INVALID')
    return p


def _read(path, maximum=65536):
    p = _path(path)
    _require(p.is_file(), 'PILOT_INPUT_INVALID')
    with p.open('rb') as stream:
        raw = stream.read(maximum + 1)
    _require(len(raw) <= maximum, 'PILOT_INPUT_INVALID')
    return raw


def _document(path):
    return _json(_read(path, 4_000_000))


def _decimal(value):
    _require(type(value) is str and re.fullmatch(r'-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?', value)
             is not None and len(value) <= 100, 'PILOT_POLICY_INVALID')
    result = Decimal(value)
    _require(result.is_finite(), 'PILOT_POLICY_INVALID')
    return result


def _time(value):
    _require(type(value) is int and 0 < value < 2**63, 'PILOT_TIME_INVALID')
    return value


def _utc(value):
    _require(type(value) is str and re.fullmatch(r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ', value)
             is not None, 'PILOT_POLICY_INVALID')
    return int(datetime.strptime(value, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc).timestamp()) * NS


def _source_time(value):
    _require(type(value) is str, 'PILOT_FEEDER_INVALID')
    dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
    _require(dt.tzinfo is not None, 'PILOT_FEEDER_INVALID')
    return int(dt.timestamp()) * NS + dt.microsecond * 1000


def _load_policy(policy_path, owner_record_path, owner_record_sha256, state_root, feeder_root, now, *, clock_ns=None):
    raw = _read(policy_path)
    policy = _json(raw)
    _require(type(policy) is dict and set(policy) == POLICY_KEYS and _canonical(policy) == raw,
             'PILOT_POLICY_INVALID')
    _require((policy['schema_id'], policy['schema_version']) == ('polymarket-live-pilot-policy', '1.0.0')
             and policy['market_predicate'] == 'NBA_MONEYLINE_PREGAME_V1'
             and policy['side'] == 'BUY' and policy['order_type'] == 'FOK', 'PILOT_POLICY_INVALID')
    _require(type(policy['host']) is dict and set(policy['host']) == HOST_KEYS
             and type(policy['host']['ssh_port']) is int and 1 <= policy['host']['ssh_port'] <= 65535,
             'PILOT_POLICY_INVALID')
    for key in HOST_KEYS - {'ssh_port'}:
        _path(policy['host'][key])
    for key in ('public_wallet', 'public_signer'):
        _require(type(policy[key]) is str and re.fullmatch(r'0x[0-9a-fA-F]{40}', policy[key]) is not None,
                 'PILOT_POLICY_INVALID')
    _require(type(policy['release_sha']) is str and re.fullmatch(r'[0-9a-f]{40}', policy['release_sha']) is not None
             and type(policy['strategy_version_id']) is str
             and re.fullmatch(r'strategyversion:sha256:[0-9a-f]{64}', policy['strategy_version_id']) is not None,
             'PILOT_POLICY_INVALID')
    for key in ('state_root', 'feeder_root', 'lifecycle_store_path', 'hermes_store_path'):
        _path(policy[key])
    _require(policy['state_root'] == str(state_root) and policy['feeder_root'] == str(feeder_root),
             'PILOT_POLICY_INVALID')
    _require(feeder_root.resolve().is_relative_to(state_root.resolve())
             and feeder_root.resolve() != state_root.resolve(), 'PILOT_POLICY_INVALID')
    for key, ceiling in DECIMAL_CEILINGS.items():
        _require(0 < _decimal(policy[key]) <= ceiling, 'PILOT_POLICY_INVALID')
    for key, ceiling in INTEGER_CEILINGS.items():
        _require(type(policy[key]) is int and 1 <= policy[key] <= ceiling, 'PILOT_POLICY_INVALID')
    _require(_decimal(policy['experimental_margin_usd']) >= 0, 'PILOT_POLICY_INVALID')
    start, end = _utc(policy['valid_from_utc']), _utc(policy['valid_until_utc'])
    _require(0 < end - start <= 7 * DAY and start <= now < end, 'PILOT_POLICY_INVALID')
    policy_hash = _digest(raw)
    record_raw = _read(owner_record_path)
    _require(type(owner_record_sha256) is str and re.fullmatch(r'[0-9a-f]{64}', owner_record_sha256) is not None
             and _digest(record_raw) == owner_record_sha256, 'PILOT_OWNER_RECORD_DIGEST_MISMATCH')
    try:
        record = _json(record_raw)
        _require(type(record) is dict and set(record) == OWNER_KEYS and _canonical(record) == record_raw
                 and (record['schema_id'], record['schema_version']) ==
                 ('polymarket-live-pilot-owner-activation', '1.0.0'), 'PILOT_OWNER_RECORD_INVALID')
    except Exception:
        raise GatewayError('PILOT_OWNER_RECORD_INVALID') from None
    _require(record['policy_sha256'] == policy_hash and all(record[k] == policy[k] for k in
             ('public_wallet', 'public_signer', 'release_sha', 'state_root')), 'PILOT_OWNER_RECORD_SCOPE_MISMATCH')
    try:
        a, b = _utc(record['valid_from_utc']), _utc(record['valid_until_utc'])
        _require(start <= a < b <= end and a <= now < b, 'PILOT_OWNER_RECORD_WINDOW_INVALID')
    except Exception:
        raise GatewayError('PILOT_OWNER_RECORD_WINDOW_INVALID') from None
    at = now if clock_ns is None else _time(clock_ns())
    _require(start <= at < end and a <= at < b, 'PILOT_OWNER_RECORD_WINDOW_INVALID')
    # Retain the narrower immutable owner deadline for the guard's final clock check.
    return dict(policy, _owner_window=(a, b)), policy_hash


@contextmanager
def _run_lock(root):
    flags = os.O_RDWR | os.O_CREAT | getattr(os, 'O_NOFOLLOW', 0)
    fd = os.open(_path(root / 'pilot-run.lock'), flags, 0o600)
    with os.fdopen(fd, 'r+b') as handle:
        try:
            if os.name == 'nt':
                import msvcrt
                if not handle.read(1):
                    handle.write(b'0')
                    handle.flush()
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            raise GatewayError('PILOT_RUN_BUSY') from None
        try:
            yield
        finally:
            if os.name == 'nt':
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)


def _terminal(root, status, code, result=None, scenario=None):
    # No policy/source/exception text or credential-bearing dependencies are serialized.
    value = {'schema_id': 'polymarket-live-pilot-terminal', 'schema_version': '1.0.0',
             'status': status, 'code': code, 'claim': 'RESEARCH_ONLY',
             'unconditional_order_ev': 'UNKNOWN', 'realized_profit': None, 'episode_id': None,
             'create_transmits': 0, 'native_result': None, 'scenario_claim': None,
             'full_fill_stress_usd': None}
    if scenario is not None:
        value['scenario_claim'] = 'POSITIVE_AFTER_COST_FULL_FILL_STRESS_SCENARIO'
        value['full_fill_stress_usd'] = format(scenario, 'f')
    if result is not None:
        episode = result.episode_id
        if isinstance(episode, str) and re.fullmatch(r'liveorchepisode:sha256:[0-9a-f]{64}', episode):
            value['episode_id'] = episode
        value['create_transmits'] = result.create_transmits
        value['native_result'] = {
            'status': result.status if result.status in ('BLOCKED', 'CANARY_COMPLETE') else 'NATIVE_RESULT_INVALID',
            'code': result.code if result.code in NATIVE_CODES else 'NATIVE_RESULT_INVALID',
        }
    directory = _path(root / 'terminals')
    directory.mkdir(exist_ok=True)
    with (directory / (uuid.uuid4().hex + '.json')).open('xb') as stream:
        stream.write(_canonical(value))
        stream.flush()
        os.fsync(stream.fileno())
    return value


def _rule(market):
    def array(value):
        return _json(value.encode()) if type(value) is str else value
    outcomes, tokens = array(market['outcomes']), array(market['clobTokenIds'])
    _require(type(outcomes) is list and type(tokens) is list and len(outcomes) == len(tokens) == 2
             and all(type(x) is str for x in outcomes + tokens)
             and len(set(outcomes)) == len(set(tokens)) == 2, 'PILOT_FEEDER_INVALID')
    _require(all(re.fullmatch(r'[A-Za-z][A-Za-z0-9 .-]{0,48}', x) for x in outcomes)
             and all(re.fullmatch(r'[0-9]{1,100}', x) for x in tokens), 'PILOT_FEEDER_INVALID')
    start = _source_time(market['gameStartTime'])
    local = datetime.fromtimestamp(start // NS, ZoneInfo('America/New_York'))
    month = ('January February March April May June July August September October November December').split()[local.month-1]
    clock = f'{local.hour % 12 or 12}:{local.minute:02d}{"AM" if local.hour < 12 else "PM"}'
    description = (f'In the upcoming NBA game, scheduled for {month} {local.day} at {clock} ET:\n'
        f'If the {outcomes[0]} win, the market will resolve to "{outcomes[0]}".\n'
        f'If the {outcomes[1]} win, the market will resolve to "{outcomes[1]}".\n'
        'If the game is postponed, this market will remain open until the game has been completed.\n'
        'If the game is canceled entirely, with no make-up game, this market will resolve 50-50.\n'
        'The result will be determined based on the final score including any overtime periods.')
    _require(market['description'] == description and market['question'] == f'{outcomes[0]} vs. {outcomes[1]}'
             and market['sportsMarketType'] == 'moneyline' and market['negRisk'] is False
             and market['resolutionSource'] in ('https://www.nba.com', 'https://www.nba.com/')
             and re.fullmatch(r'nba-[a-z]{2,4}-[a-z]{2,4}-' + local.strftime('%Y-%m-%d'), market['slug']),
             'PILOT_FEEDER_INVALID')
    return outcomes, tokens, start


def _fresh(candidate, policy, now, assessment_time=None):
    _require(now < candidate['start_ns'], 'PILOT_EVENT_STARTED')
    for received in candidate['received_ns']:
        _require(0 <= now - _time(received) <= policy['max_feeder_age_s'] * NS, 'PILOT_FEEDER_STALE')
    if assessment_time is not None:
        _require(0 <= now - _time(assessment_time) <= policy['max_hermes_assessment_age_s'] * NS,
                 'PILOT_ASSESSMENT_STALE')


def _feeder_candidates(root, policy, now):
    """Read frozen completed occurrences; rederive from raw sources, never scores."""
    latest, identities = {}, {}
    operations = sorted(root.glob('op-*'))
    _require(len(operations) <= 10000, 'PILOT_FEEDER_INVALID')
    for op in operations:
        _require(re.fullmatch(r'op-[0-9]{6}', op.name), 'PILOT_FEEDER_INVALID')
        if not (op / 'terminal.json').exists():
            continue
        terminal, started = _document(op / 'terminal.json'), _document(op / 'started.json')
        if started['kind'] != 'CYCLE' or terminal['status'] != 'COMPLETED':
            continue
        if terminal['result'].get('status') == 'BLOCKED':
            continue
        ordinal = int(op.name[3:])
        _require(type(started['ordinal']) is int and started['ordinal'] == ordinal,
                 'PILOT_FEEDER_INVALID')
        inputs = terminal['inputs_sha256']
        _require(type(inputs) is dict and len(inputs) <= 128 and 'started.json' in inputs,
                 'PILOT_FEEDER_INVALID')
        for name, digest in inputs.items():
            _require(type(name) is str and Path(name).name == name and name not in ('.', '..', 'terminal.json')
                     and _digest(_read(op / name, 64_000_000)) == digest, 'PILOT_FEEDER_INVALID')
        receipts = terminal['receipts']
        _require(type(receipts) is list and 1 <= len(receipts) <= 32, 'PILOT_FEEDER_INVALID')
        for index, receipt in enumerate(receipts, 1):
            name = f'receipt-{index:02d}.json'
            _require(name in inputs and _document(op / name) == receipt, 'PILOT_FEEDER_INVALID')
        cutoff = _time(terminal['result']['cutoff_ns'])
        _require(cutoff <= now, 'PILOT_FEEDER_INVALID')
        def source(url):
            matches = [x for x in receipts if x['url'] == url]
            _require(len(matches) == 1, 'PILOT_FEEDER_INVALID')
            receipt = matches[0]
            filename = receipt['raw_file']
            _require(receipt['state'] == 'AVAILABLE' and type(filename) is str
                     and re.fullmatch(r'source-[0-9]{2}\.json', filename) and filename in inputs,
                     'PILOT_FEEDER_INVALID')
            raw = _read(op / filename, 2_000_000)
            _require(_digest(raw) == receipt['sha256'] and
                     _time(receipt['started_ns']) <= _time(receipt['received_ns']) <= cutoff,
                     'PILOT_FEEDER_INVALID')
            http_time = _source_time(parsedate_to_datetime(receipt['http_date']).isoformat())
            _require(cutoff - receipt['received_ns'] <= 300 * NS
                     and -2 * NS <= receipt['received_ns'] - http_time <= 300 * NS,
                     'PILOT_FEEDER_INVALID')
            return _json(raw), receipt['received_ns']
        markets, gamma_time = source(DISCOVERY_URL)
        _require(type(markets) is list and len(markets) <= 200, 'PILOT_FEEDER_INVALID')
        _require(len({m['id'] for m in markets}) == len(markets), 'PILOT_FEEDER_INVALID')
        for receipt in receipts:
            url = receipt['url']
            if not re.fullmatch(re.escape(ESPN) + r'summary\?event=[0-9]{1,16}', url) or receipt['state'] != 'AVAILABLE':
                continue
            summary, espn_time = source(url)
            header = summary['header']
            event_id = url.split('event=')[1]
            _require(header['id'] == event_id and header['league']['slug'] == 'nba'
                     and len(header['competitions']) == 1, 'PILOT_FEEDER_INVALID')
            competition = header['competitions'][0]
            if competition['status']['type']['state'] != 'pre':
                continue
            competitors = competition['competitors']
            _require(len(competitors) == 2, 'PILOT_FEEDER_INVALID')
            by_id = {c['team']['id']: c['team']['name'] for c in competitors}
            found = []
            for market in markets:
                try:
                    outcomes, tokens, start = _rule(market)
                except (GatewayError, KeyError, TypeError, ValueError):
                    continue
                if set(outcomes) == set(by_id.values()) and start == _source_time(competition['date']):
                    found.append((market, outcomes, tokens, start))
            _require(len(found) <= 1, 'PILOT_FEEDER_INVALID')
            if not found:
                continue
            market, outcomes, tokens, start = found[0]
            predictor = summary['predictor']
            _require(predictor['header'] == 'Matchup Predictor', 'PILOT_FEEDER_INVALID')
            values = {by_id[predictor[k]['id']]: _decimal(str(predictor[k]['gameProjection'])) / 100
                      for k in ('homeTeam', 'awayTeam')}
            _require(set(values) == set(outcomes) and sum(values.values()) == 1
                     and all(0 <= x <= 1 for x in values.values()), 'PILOT_FEEDER_INVALID')
            identity = (market['id'], market['conditionId'], tuple(tokens), tuple(outcomes), start)
            _require(event_id not in identities or identities[event_id] == identity, 'PILOT_FEEDER_INVALID')
            identities[event_id] = identity
            candidates = [dict(event_id=event_id, gamma_market_id=str(market['id']), condition_id=market['conditionId'],
                               token_id=token, start_ns=start, probability=values[outcomes[index]],
                               received_ns=(gamma_time, espn_time)) for index, token in enumerate(tokens)]
            key = (espn_time, ordinal)
            if event_id not in latest or key > latest[event_id][0]:
                latest[event_id] = (key, candidates)
    result, seen = [], set()
    for _, candidates in latest.values():
        for candidate in candidates:
            pair = candidate['event_id'], candidate['token_id']
            _require(pair not in seen, 'PILOT_FEEDER_INVALID')
            seen.add(pair)
            try:
                _fresh(candidate, policy, now)
            except GatewayError:
                continue
            result.append(candidate)
    return result


def _economics(candidate, snapshot, version, policy, now):
    _require((snapshot.gamma_market_id, snapshot.condition_id, snapshot.token_id) ==
             (candidate['gamma_market_id'], candidate['condition_id'], candidate['token_id']), 'PILOT_MARKET_MISMATCH')
    _require(snapshot.seconds_delay == 0 and snapshot.gamma_neg_risk is False and snapshot.book_neg_risk is False
             and bool(snapshot.asks), 'PILOT_VENUE_INVALID')
    price = min(Decimal(level[0]) for level in snapshot.asks)
    _require(0 < price < 1, 'PILOT_VENUE_INVALID')
    cap = _decimal(policy['max_order_commitment_usd'])
    with localcontext() as context:
        context.prec = 256
        shares = cap / price
        _require(shares * 100 == (shares * 100).to_integral_value() and shares * price == cap,
                 'MINIMUM_EXCEEDS_CAP')
        intent = build_execution_intent(strategy_version=version, gamma_market_id=candidate['gamma_market_id'],
            condition_id=candidate['condition_id'], token_id=candidate['token_id'], side='BUY',
            execution_style='AGGRESSIVE_TAKER', order_type='FOK', requested_shares=format(shares, 'f'),
            price_limit=format(price, 'f'), post_only=False, gtd_expiration_unix_s=None,
            information_cutoff_ns=snapshot.acquisition_completed_ns, max_public_data_age_ns=30 * NS)
        assessment = assess_execution_feasibility(intent, snapshot, evaluated_at_ns=max(now, snapshot.acquisition_completed_ns))
        _require(assessment.status in ('FEASIBLE', 'LIMITED') and assessment.minimum_order_dimension == 'PASS'
                 and assessment.tick_dimension == 'PASS', 'PILOT_VENUE_INVALID')
        _require(sum((Decimal(q) for p, q in snapshot.asks if Decimal(p) == price), Decimal(0)) >= shares,
                 'PILOT_VENUE_INVALID')
        # Principal already uses the full cap: any positive/unknown native fee abstains.
        _require(assessment.fee_exactness == 'EXACT_ZERO_NO_FEES' or
                 (assessment.fee_exactness == 'CONSERVATIVE_5DP_UPPER_BOUND' and
                  snapshot.fee_rate is not None and Decimal(snapshot.fee_rate) == 0), 'MINIMUM_EXCEEDS_CAP')
        fee = Decimal(0)
        payout_lower = min(max(Decimal(0), candidate['probability'] - Decimal('.10')), Decimal('.5'))
        stress = shares * payout_lower - shares * price - fee - Decimal('.005') * shares
        _require(stress > _decimal(policy['experimental_margin_usd']), 'PILOT_MARGIN_NOT_MET')
    return stress, intent, assessment


def _guard(policy, policy_hash, reload_policy, deps, candidate, permit, intent, assessment_time, killed):
    def check(checkpoint, evaluation, risk):
        current, digest = reload_policy(_time(deps.clock_ns()))
        _require(current == policy and digest == policy_hash, 'PILOT_GUARD_REFUSED:POLICY_CHANGED')
        _require(not killed(), 'PILOT_GUARD_REFUSED:KILL')
        _require((intent.gamma_market_id, intent.condition_id, intent.token_id, intent.strategy_version_id) ==
                 (candidate['gamma_market_id'], candidate['condition_id'], candidate['token_id'], policy['strategy_version_id']),
                 'PILOT_GUARD_REFUSED:MARKET_BINDING')
        native.verify_permit_authority(permit, intent, lifecycle_store_path=Path(policy['lifecycle_store_path']),
            hermes_store_path=Path(policy['hermes_store_path']), now_ns=_time(deps.clock_ns()))
        current, digest = reload_policy(_time(deps.clock_ns()))
        _require(current == policy and digest == policy_hash, 'PILOT_GUARD_REFUSED:POLICY_CHANGED')
        _require(not killed(), 'PILOT_GUARD_REFUSED:KILL')
        now = _time(deps.clock_ns())
        _fresh(candidate, policy, now, assessment_time)
        _require(_utc(policy['valid_from_utc']) <= now < _utc(policy['valid_until_utc'])
                 and policy['_owner_window'][0] <= now < policy['_owner_window'][1],
                 'PILOT_GUARD_REFUSED:OWNER_WINDOW')
        count = 0
        for episode in checkpoint['episodes']:
            admitted = _time(episode['admission']['admitted_time_ns'])
            _require(admitted <= now, 'PILOT_GUARD_REFUSED:LEDGER_TIME')
            count += admitted >= now - DAY
        _require(count < policy['max_admissions_24h'], 'PILOT_GUARD_REFUSED:ADMISSIONS')
        _require(evaluation.total_commitment + risk.proposed_worst_case_commitment <=
                 _decimal(policy['max_total_commitment_usd']) and risk.proposed_worst_case_commitment <=
                 _decimal(policy['max_order_commitment_usd']), 'PILOT_GUARD_REFUSED:COMMITMENT')
        for observed, key in ((evaluation.observed_realized_pnl_loss, 'max_realized_pnl_loss_usd'),
                              (evaluation.observed_position_pnl_drawdown, 'max_position_pnl_drawdown_usd'),
                              (evaluation.observed_cumulative_canary_loss, 'max_cumulative_loss_usd')):
            _require(observed <= _decimal(policy[key]), 'PILOT_GUARD_REFUSED:LOSS')
    return check


def run_pilot_once(*, policy_path, owner_record_path, owner_record_sha256, state_root, feeder_root, dependencies=None):
    """Foreground composition only; all protected operations stay native."""
    root = None
    try:
        root, feeder = _path(state_root), _path(feeder_root)
        root.mkdir(parents=True, exist_ok=True)
        with _run_lock(root):
            deps = native.LiveOrchDependencies() if dependencies is None else dependencies
            reload_policy = lambda now: _load_policy(policy_path, owner_record_path, owner_record_sha256,
                                                    root, feeder, now, clock_ns=deps.clock_ns)
            policy, policy_hash = reload_policy(_time(deps.clock_ns()))
            # Allowlist the actual native provider class, never duck-typed custody.
            _require(deps.secret_provider_factory is InteractiveGateBSecretProvider, 'PILOT_CUSTODY_UNAVAILABLE')
            latched = False
            def killed():
                nonlocal latched
                _require(root.is_dir(), 'PILOT_STATE_UNAVAILABLE')
                flag = root / 'PILOT_KILL'
                # lstat fails closed for unreadable roots and broken/reparse flags.
                try:
                    flag.lstat()
                    latched = True
                except FileNotFoundError:
                    pass
                return latched
            killed()
            host = native.HostCurrentnessConfig(**{k: Path(v) if k != 'ssh_port' else v
                for k, v in policy['host'].items()}, expected_release_sha=policy['release_sha'])
            config = native.LiveOrchConfig(state_root=root, expected_signer=policy['public_signer'],
                expected_wallet=policy['public_wallet'], lifecycle_store_path=Path(policy['lifecycle_store_path']),
                hermes_store_path=Path(policy['hermes_store_path']), host=host)
            orchestrator = native.LiveOrchestrator(config, dependencies=deps)
            reconciliation = orchestrator.reconcile()
            if reconciliation.status != 'NO_NEW_EXPOSURE_READY' or killed():
                return _terminal(root, 'REFUSED', 'PILOT_RECONCILIATION_OR_KILL')
            lifecycle = load_strategy_lifecycle_store(config.lifecycle_store_path)
            _require(lifecycle.is_valid is True and lifecycle.snapshot is not None, 'PILOT_STRATEGY_UNAVAILABLE')
            version = lifecycle.snapshot.version_by_id(policy['strategy_version_id'])
            _require(version is not None, 'PILOT_STRATEGY_UNAVAILABLE')
            hermes = load_hermes_strategy_manager_store(config.hermes_store_path)
            assessment_id = hermes.latest_assessment_id(policy['strategy_version_id'])
            assessments = [a for a in hermes.assessments if a.assessment_id == assessment_id]
            _require(len(assessments) == 1, 'PILOT_ASSESSMENT_UNAVAILABLE')
            assessment_time = assessments[0].decision_time_ns
            candidates = _feeder_candidates(feeder, policy, _time(deps.clock_ns()))
            eligible = []
            for candidate in candidates:
                try:
                    _fresh(candidate, policy, _time(deps.clock_ns()), assessment_time)
                    snapshot = deps.venue_fetcher(**{k: candidate[k] for k in ('gamma_market_id', 'condition_id', 'token_id')})
                    stress, intent, feasibility = _economics(candidate, snapshot, version, policy, _time(deps.clock_ns()))
                    eligible.append((stress, candidate, snapshot, intent, feasibility))
                except Exception:
                    continue
            if not eligible:
                return _terminal(root, 'NO_TRADE', 'PILOT_NO_ELIGIBLE_PAIR')
            stress, candidate, snapshot, intent, feasibility = min(eligible,
                key=lambda x: (-x[0], x[1]['start_ns'], x[1]['token_id']))
            decision = evaluate_exploratory_gate_c(lifecycle_store_path=config.lifecycle_store_path,
                hermes_manager_store_path=config.hermes_store_path, strategy_version_id=policy['strategy_version_id'],
                execution_intent=intent, venue_snapshot=snapshot, execution_feasibility_assessment=feasibility,
                evaluated_at_ns=_time(deps.clock_ns()))
            _require(decision.status == 'PERMIT_ELIGIBLE' and decision.hermes_assessment_id == assessment_id,
                     'PILOT_PERMIT_REFUSED')
            permit = build_exploratory_gate_c_permit(decision, execution_intent=intent)
            guard = _guard(policy, policy_hash, reload_policy, deps, candidate, permit, intent, assessment_time, killed)
            guarded = replace(deps, admission_guard=guard)
            orchestrator = native.LiveOrchestrator(config, dependencies=guarded)
            _require(orchestrator.preflight(permit, intent).status == 'PREFLIGHT_PASS', 'PILOT_PREFLIGHT_REFUSED')
            _require(not killed(), 'PILOT_KILLED')
            _require(guarded.admission_guard is guard, 'PILOT_GUARD_MISSING')
            result = orchestrator.canary(permit, intent)
            return _terminal(root, 'REFUSED' if result.status == 'BLOCKED' else 'LIVE_ORCH_RESULT',
                             'PILOT_NATIVE_REFUSED' if result.status == 'BLOCKED' else 'PILOT_NATIVE_RESULT',
                             result, stress)
    except Exception as error:
        code = error.code if isinstance(error, GatewayError) else 'PILOT_INPUT_INVALID'
        # Only module-owned closed codes survive; native details remain in its ledger.
        if not isinstance(code, str) or code not in PUBLIC_CODES:
            code = 'PILOT_NATIVE_REFUSED'
        if root is not None:
            try:
                return _terminal(root, 'REFUSED', code)
            except Exception:
                pass
        return {'status': 'REFUSED', 'code': 'PILOT_STATE_UNAVAILABLE', 'terminal_persisted': False}


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        raise GatewayError('PILOT_CLI_INVALID')


def main(argv=None):
    parser = _Parser(description='Finite attended pilot; separate activation required.')
    parser.add_argument('command', choices=['run'])
    for name in ('policy', 'owner-record', 'owner-record-sha256', 'state-root', 'feeder-root'):
        parser.add_argument('--' + name, required=True)
    try:
        args = parser.parse_args(argv)
    except GatewayError:
        print('{"status":"REFUSED","code":"PILOT_CLI_INVALID"}')
        return 2
    result = run_pilot_once(policy_path=args.policy, owner_record_path=args.owner_record,
        owner_record_sha256=args.owner_record_sha256, state_root=args.state_root, feeder_root=args.feeder_root)
    print(_canonical(result).decode('utf-8'))
    return 0 if result['status'] in ('NO_TRADE', 'LIVE_ORCH_RESULT') else 1


if __name__ == '__main__':
    raise SystemExit(main())
