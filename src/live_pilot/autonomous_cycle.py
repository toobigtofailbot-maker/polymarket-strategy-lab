"""Finite native research composition; no calibrated method or economic authority.

Hermes proposes research. Original native sources can establish source bounds,
never calibration. This release has no reachable CREATE, SELL or CANCEL path.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from decimal import Decimal
import os
from pathlib import Path
import re
import time
from urllib.parse import urlsplit

from src.execution_gateway import live_orch as native
from src.execution_gateway.gateway import GatewayError, _canonical_decimal
from src.live_pilot import hunter_cycle as pilot
from src.live_pilot import pilot as common
from src.strategy_lifecycle import load_strategy_lifecycle_store
from tools.alpha import run_alpha_hunter as hunter
from tools.alpha import run_near_term_market_screener as scanner

NS = 10**9
CALIBRATED_METHODS = frozenset()  # No independently calibrated native verifier on this base.
METHODS = {'SPORTS_NBA_MONEYLINE': 'NBA_ESPN_V1', 'WEATHER_US_DAILY_RAIN': 'RAIN_NWS_V1'}
COUNTS = ('REJECTED', 'SOURCE_BOUND_ONLY', 'QUALIFIED_FOR_ADMISSION')
POLICY_KEYS = frozenset(('schema_id schema_version mode public_wallet public_signer state_root release_sha '
    'valid_from_ns valid_until_ns max_cycles max_duration_s cadence_s max_discovery_gets_per_cycle '
    'max_market_candidates_per_cycle max_provider_calls_total max_provider_cost_usd_total '
    'max_buy_mutations_per_cycle max_buy_mutations_rolling24h max_fee_inclusive_order_usd '
    'max_total_commitment_usd min_free_collateral_usd min_stress_margin_usd kill_file_name').split())
FORECAST_KEYS = frozenset(('schema_id schema_version strategy_version_id market_id condition_id token_id '
    'outcome_index resolution_rule_sha256 source_cutoff_ns evaluated_ns expires_ns native_method_id '
    'native_method_sha256 source_receipts p_point p_lower p_upper qualification_state reason_codes '
    'record_sha256').split())
JOURNAL_KEYS = frozenset(('schema_id schema_version sequence previous_sha256 policy_sha256 cycle_id '
    'cycle_index phase started_ns ended_ns reserved_gets reserved_provider_calls reserved_cost_usd '
    'actual_gets actual_provider_calls reason scanner_sha256 hunter_sha256 economic_mutation_id entry_sha256').split())
CODES = frozenset(('POLICY_INVALID LOCKED_BY_OTHER JOURNAL_UNVERIFIED KILLED CUSTODY_SUSPENDED '
    'GEOBLOCK_REFUSED ACCOUNT_UNKNOWN BUDGET_EXHAUSTED SOURCE_INDEPENDENCE_UNPROVEN '
    'FORECAST_METHOD_UNSUPPORTED CALIBRATION_NOT_VERIFIED FORECAST_STALE RULE_UNVERIFIED '
    'FEE_UNKNOWN_OR_EXPIRED MINIMUM_UNSATISFIABLE GATE_REJECTED CANARY_APPROVAL_MISSING '
    'ORDER_OUTCOME_UNKNOWN OFF OWNER_SETUP_REQUIRED RESEARCH_COMPLETE INPUT_INVALID STATE_UNAVAILABLE '
    'NO_CANDIDATES NO_TRADE').split())
SESSION_KEYS = frozenset(('activation_id activation_ledger_head previous_session_sha256').split())


def require(ok, code='INPUT_INVALID'):
    if not ok:
        raise GatewayError(code)


def canonical(value):
    return common._canonical(value)


def digest(value):
    return common._digest(value)


def seal(record, field_name):
    return dict(record, **{field_name: digest(canonical({k: v for k, v in record.items() if k != field_name}))})


def integer(value, low, high, code='POLICY_INVALID'):
    require(type(value) is int and low <= value <= high, code)
    return value


def decimal(value, low=Decimal(0), high=None, code='POLICY_INVALID'):
    require(type(value) is str, code)
    try:
        number = common._decimal(value)
        require(_canonical_decimal(number) == value and number >= low and (high is None or number <= high), code)
        return number
    except Exception:
        raise GatewayError(code) from None


def read(path, maximum=65536):
    try:
        raw = common._read(path, maximum)
        value = common._json(raw)
        require(canonical(value)+b'\n' == raw)
        return value
    except Exception:
        raise GatewayError('JOURNAL_UNVERIFIED') from None


def write(path, value):
    # Native exclusive fsync writer, with the same native safe-path check.
    hunter.S.put(common._path(path), value)


def load_policy(path, now, *, snapshot=False):
    try:
        raw = common._read(path)
        p = common._json(raw)
        renewed = type(p) is dict and p.get('schema_version') == '2.0.0'
        require(type(p) is dict and set(p) == (POLICY_KEYS | SESSION_KEYS if renewed else POLICY_KEYS) and canonical(p)+(b'\n' if snapshot else b'') == raw, 'POLICY_INVALID')
        require(p['schema_id'] == 'autonomous-cycle-policy' and p['schema_version'] in ('1.0.0', '2.0.0')
                and p['mode'] in ('OFF', 'RESEARCH', 'LIVE') and p['kill_file_name'] == 'PILOT_KILL', 'POLICY_INVALID')
        for key in ('public_wallet', 'public_signer'):
            require(type(p[key]) is str and re.fullmatch(r'0x[0-9a-fA-F]{40}', p[key]), 'POLICY_INVALID')
        require(type(p['release_sha']) is str and re.fullmatch(r'[0-9a-f]{40}', p['release_sha']), 'POLICY_INVALID')
        common._path(p['state_root'])
        integer(now, 1, 2**63-1)
        a, b = (integer(p[k], 1, 2**63-1) for k in ('valid_from_ns', 'valid_until_ns'))
        require(a <= now < b and b-a <= 7200*NS, 'POLICY_INVALID')
        for key, low, high in (
            ('max_cycles', 1, 4), ('max_duration_s', 1, 7200), ('cadence_s', 60, 3600),
            ('max_discovery_gets_per_cycle', 1, 40), ('max_market_candidates_per_cycle', 1, 10),
            ('max_provider_calls_total', 0, 4), ('max_buy_mutations_per_cycle', 0, 1),
            ('max_buy_mutations_rolling24h', 0, 2)):
            integer(p[key], low, high)
        for key, low, high in (
            ('max_provider_cost_usd_total', '0', '2'), ('max_fee_inclusive_order_usd', '2', '5'),
            ('max_total_commitment_usd', '0.00001', '30'), ('min_free_collateral_usd', '50', '100'),
            ('min_stress_margin_usd', '0', None)):
            if renewed:
                low, high = {'max_fee_inclusive_order_usd': ('2', '10'),
                             'max_total_commitment_usd': ('0.00001', '10'),
                             'min_free_collateral_usd': ('90', '100')}.get(key, (low, high))
            decimal(p[key], Decimal(low), None if high is None else Decimal(high))
        if renewed:
            for key in ('activation_id', 'activation_ledger_head'):
                require(type(p[key]) is str and re.fullmatch('[0-9a-f]{64}', p[key]), 'POLICY_INVALID')
            require(p['previous_session_sha256'] is None or type(p['previous_session_sha256']) is str
                    and re.fullmatch('[0-9a-f]{64}', p['previous_session_sha256']), 'POLICY_INVALID')
        return p, digest(canonical(p))
    except Exception:
        raise GatewayError('POLICY_INVALID') from None


def validate_forecast(record):
    """Validate shape/identity only. A valid external record never establishes trust."""
    require(type(record) is dict and set(record) == FORECAST_KEYS)
    require(record == seal(record, 'record_sha256'))
    require((record['schema_id'], record['schema_version']) == ('autonomous-forecast', '1.0.0'))
    require(type(record['strategy_version_id']) is str and re.fullmatch(r'strategyversion:sha256:[0-9a-f]{64}', record['strategy_version_id']))
    for key in ('market_id', 'token_id'):
        require(type(record[key]) is str and re.fullmatch(r'[0-9]{1,80}', record[key]))
    require(type(record['condition_id']) is str and re.fullmatch(r'0x[0-9a-f]{64}', record['condition_id']))
    for key in ('resolution_rule_sha256', 'native_method_sha256'):
        require(type(record[key]) is str and re.fullmatch(r'[0-9a-f]{64}', record[key]))
    integer(record['outcome_index'], 0, 1, 'INPUT_INVALID')
    a, b, c = (integer(record[k], 1, 2**63-1, 'INPUT_INVALID') for k in ('source_cutoff_ns', 'evaluated_ns', 'expires_ns'))
    require(a <= b < c <= b+30*NS)
    lower, point, upper = (decimal(record[k], Decimal(0), Decimal(1), 'INPUT_INVALID')
                           for k in ('p_lower', 'p_point', 'p_upper'))
    require(lower <= point <= upper and record['native_method_id'] in METHODS.values())
    require(record['qualification_state'] in COUNTS and record['reason_codes'] == ['CALIBRATION_NOT_VERIFIED'])
    sources = record['source_receipts']
    require(type(sources) is list and 1 <= len(sources) <= 8)
    seen = set()
    for source in sources:
        require(type(source) is dict and set(source) == {'source_kind', 'raw_sha256', 'received_ns', 'url_sha256'})
        require(source['source_kind'] in ('ESPN', 'NWS'))
        for key in ('raw_sha256', 'url_sha256'):
            require(type(source[key]) is str and re.fullmatch(r'[0-9a-f]{64}', source[key]))
        integer(source['received_ns'], 1, a, 'INPUT_INVALID')
        identity = (source['url_sha256'], source['raw_sha256'])
        require(identity not in seen)
        seen.add(identity)
    return True


def replay_forecasts(scratch, operation, native_policy, now):
    """Cold native replay is the only constructor of SOURCE_BOUND_ONLY records."""
    root = common._path(scratch)
    require(re.fullmatch(r'op-[0-9]{6}', operation), 'SOURCE_INDEPENDENCE_UNPROVEN')
    require(hunter.verify(root)['status'] == 'VERIFIED', 'SOURCE_INDEPENDENCE_UNPROVEN')
    op = common._path(root / operation)
    manifest = hunter.S.read(op / 'manifest.json')
    clocks = manifest['clocks']
    require(clocks['source_cutoff_ns'] <= clocks['evaluated_ns'] <= now < clocks['evaluated_ns']+30*NS, 'FORECAST_STALE')
    lifecycle = load_strategy_lifecycle_store(Path(native_policy['lifecycle_store_path']))
    require(lifecycle.is_valid and lifecycle.snapshot is not None, 'GATE_REJECTED')
    markets = {m['gamma_market_id']: m for m in manifest['markets'] if m.get('reason') is None}
    receipts = [hunter.S.read(p) for p in sorted(op.glob('receipt-*.json'))]
    records = []
    for row in manifest['tokens']:
        category = row['category']
        market = markets.get(row['gamma_market_id'])
        if market is None or category not in METHODS or category not in native_policy['categories']:
            continue
        version_id = native_policy['strategy_version_ids'][category]
        require(lifecycle.snapshot.version_by_id(version_id) is not None, 'GATE_REJECTED')
        if row.get('p_estimate') is None or row.get('payout_bounds') is None:
            continue
        sources, seen = [], set()
        for receipt in receipts:
            host = urlsplit(receipt['url']).hostname
            kind = 'ESPN' if host == 'site.api.espn.com' else 'NWS' if host == 'api.weather.gov' else None
            if kind != ('ESPN' if category == 'SPORTS_NBA_MONEYLINE' else 'NWS') or receipt['state'] != 'AVAILABLE':
                continue
            raw_sha = digest(common._read(op / receipt['raw_file'], 2_000_000))
            require(raw_sha == receipt['sha256'] and receipt['received_ns'] <= clocks['source_cutoff_ns'], 'SOURCE_INDEPENDENCE_UNPROVEN')
            key = (receipt['url'], raw_sha)
            if key in seen:
                continue
            seen.add(key)
            sources.append(dict(source_kind=kind, raw_sha256=raw_sha, received_ns=receipt['received_ns'],
                                url_sha256=digest(receipt['url'].encode())))
        if not 1 <= len(sources) <= 8:
            continue
        deadline = market['forecast']['start_ns'] if category == 'SPORTS_NBA_MONEYLINE' else common._utc(market['target_day']+'T00:00:00Z')
        expiry = min(deadline, clocks['evaluated_ns']+30*NS)
        if not now < expiry:
            continue
        record = seal(dict(schema_id='autonomous-forecast', schema_version='1.0.0', strategy_version_id=version_id,
            market_id=row['gamma_market_id'], condition_id=row['condition_id'], token_id=row['token_id'],
            outcome_index=row['outcome_index'], resolution_rule_sha256=market['rule_sha256'],
            source_cutoff_ns=clocks['source_cutoff_ns'], evaluated_ns=clocks['evaluated_ns'], expires_ns=expiry,
            native_method_id=METHODS[category], native_method_sha256=digest(Path(hunter.__file__).read_bytes()),
            source_receipts=sources, p_point=_canonical_decimal(Decimal(row['p_estimate'])),
            p_lower=_canonical_decimal(Decimal(row['payout_bounds'][0])), p_upper=_canonical_decimal(Decimal(row['payout_bounds'][1])),
            qualification_state='SOURCE_BOUND_ONLY', reason_codes=['CALIBRATION_NOT_VERIFIED']), 'record_sha256')
        validate_forecast(record)
        records.append(record)
    return records


class _ResearchAccount(native.LiveOrchestrator):
    """Narrow native recovery under its wallet lock; no alternative gateway."""
    def _recover_all(self, session):
        require(self._envelope.profile == native.AUTONOMOUS_EDGE_01_PROFILE or not session.gateway.live_orch_checkpoint()['episodes'], 'ACCOUNT_UNKNOWN')
        return super()._recover_all(session)

    def _cancel_rounds(self, session, episode_id):
        raise GatewayError('ACCOUNT_UNKNOWN')


def account(p, native_policy_path, owner_record_path, owner_record_sha256, deps):
    now = deps.clock_ns()
    np, native_policy_hash = pilot._load(native_policy_path, owner_record_path, owner_record_sha256, Path(p['state_root']), now)
    if p['schema_version'] == '2.0.0':
        require(np['schema_version'] == '3.0.0' and all(p[k] == np[k] for k in SESSION_KEYS), 'OWNER_SETUP_REQUIRED')
        require(Decimal(p['max_provider_cost_usd_total']) <= Decimal(np['provider_max_rolling24h_usd']), 'OWNER_SETUP_REQUIRED')
    suspension = Path(p['state_root']) / f'custody-suspended-{owner_record_sha256}.json'
    require(not suspension.exists() and not suspension.is_symlink(), 'CUSTODY_SUSPENDED')
    for key in ('public_wallet', 'public_signer', 'release_sha', 'state_root'):
        require(p[key] == np[key], 'OWNER_SETUP_REQUIRED')
    require(np['_owner_window'][0] <= p['valid_from_ns'] < p['valid_until_ns'] <= np['_owner_window'][1], 'OWNER_SETUP_REQUIRED')
    for auto, original, direction in (
        ('max_fee_inclusive_order_usd', 'max_order_commitment_usd', 1),
        ('max_total_commitment_usd', 'max_simultaneous_exposure_usd', 1),
        ('min_free_collateral_usd', 'min_free_collateral_after_admission_usd', -1),
        ('min_stress_margin_usd', 'experimental_margin_usd', -1)):
        require(direction*(Decimal(p[auto])-Decimal(np[original])) <= 0, 'OWNER_SETUP_REQUIRED')
    signer, provider = pilot.CUSTODY_PROVIDERS[np['custody']]
    require(deps.secret_provider_factory is getattr(pilot, provider), 'CUSTODY_SUSPENDED')
    host = native.HostCurrentnessConfig(**{k: Path(v) if k != 'ssh_port' else v for k, v in np['host'].items()}, expected_release_sha=np['release_sha'])
    config = native.LiveOrchConfig(Path(p['state_root']), p['public_signer'], p['public_wallet'],
        Path(np['lifecycle_store_path']), Path(np['hermes_store_path']), host)
    envelope = (native.LiveOrchCapitalEnvelope.autonomous_edge_01() if p['schema_version'] == '2.0.0'
                else native.LiveOrchCapitalEnvelope.hunter_pilot_02())
    orchestrator = _ResearchAccount(config, envelope=envelope,
                                    dependencies=replace(deps, signer_type=signer))
    if p['schema_version'] == '1.0.0' or not (Path(p['state_root'])/'activation.json').exists():
        require(not orchestrator.ledger()['episodes'], 'ACCOUNT_UNKNOWN')
    if p['schema_version'] == '2.0.0':
        pilot.verify_activation_baseline(np)
    orchestrator._host_current()
    try:
        orchestrator._geoblock()
    except Exception:
        raise GatewayError('GEOBLOCK_REFUSED') from None
    reconciliation = orchestrator.reconcile()
    require(reconciliation.status == 'NO_NEW_EXPOSURE_READY', 'ACCOUNT_UNKNOWN')
    if p['schema_version'] == '2.0.0':
        pilot._latch_equity(Path(p['state_root']), np, native_policy_hash, reconciliation, orchestrator.ledger())
    return np, native_policy_hash


def cycle_id(p, policy_hash, index):
    return digest(canonical(dict(public_wallet=p['public_wallet'], release_sha=p['release_sha'],
                                 policy_sha256=policy_hash, cycle_index=index)))


def replay_journal(root, p, policy_hash):
    entries, pending = [], None
    for path in root.iterdir():
        if path.name.startswith('journal-'):
            require(re.fullmatch(r'journal-[0-9]{6}\.json', path.name), 'JOURNAL_UNVERIFIED')
    for index, path in enumerate(sorted(root.glob('journal-*.json')), 1):
        require(path.name == f'journal-{index:06d}.json', 'JOURNAL_UNVERIFIED')
        try:
            e = read(path)
            require(set(e) == JOURNAL_KEYS and e == seal(e, 'entry_sha256'), 'JOURNAL_UNVERIFIED')
            require((e['schema_id'], e['schema_version']) == ('autonomous-cycle-journal', p['schema_version']), 'JOURNAL_UNVERIFIED')
            require(e['sequence'] == index and type(e['sequence']) is int and e['previous_sha256'] == (entries[-1]['entry_sha256'] if entries else None)
                    and e['policy_sha256'] == policy_hash and e['economic_mutation_id'] is None, 'JOURNAL_UNVERIFIED')
            integer(e['cycle_index'], 0, p['max_cycles']-1, 'JOURNAL_UNVERIFIED')
            require(e['cycle_id'] == cycle_id(p, policy_hash, e['cycle_index']), 'JOURNAL_UNVERIFIED')
            integer(e['started_ns'], p['valid_from_ns'], p['valid_until_ns']-1, 'JOURNAL_UNVERIFIED')
            integer(e['reserved_gets'], 1, p['max_discovery_gets_per_cycle'], 'JOURNAL_UNVERIFIED')
            integer(e['reserved_provider_calls'], 0, p['max_provider_calls_total'], 'JOURNAL_UNVERIFIED')
            decimal(e['reserved_cost_usd'], Decimal(0), Decimal(p['max_provider_cost_usd_total']), 'JOURNAL_UNVERIFIED')
            for key, reserve in (('actual_gets', 'reserved_gets'), ('actual_provider_calls', 'reserved_provider_calls')):
                integer(e[key], 0, e[reserve], 'JOURNAL_UNVERIFIED')
            for key in ('scanner_sha256', 'hunter_sha256'):
                require(e[key] is None or type(e[key]) is str and re.fullmatch(r'[0-9a-f]{64}', e[key]), 'JOURNAL_UNVERIFIED')
            if e['phase'] == 'RESERVED':
                require(pending is None and e['cycle_index'] == len(entries)//2 and e['reason'] is None
                    and e['ended_ns'] is None and e['actual_gets'] == e['actual_provider_calls'] == 0
                    and e['scanner_sha256'] is e['hunter_sha256'] is None, 'JOURNAL_UNVERIFIED')
                require(not entries or e['started_ns'] >= entries[-1]['ended_ns'], 'JOURNAL_UNVERIFIED')
                pending = e
            else:
                require(e['phase'] == 'TERMINAL' and pending is not None and e['reason'] in CODES, 'JOURNAL_UNVERIFIED')
                for key in ('cycle_id', 'cycle_index', 'started_ns', 'reserved_gets', 'reserved_provider_calls', 'reserved_cost_usd'):
                    require(e[key] == pending[key], 'JOURNAL_UNVERIFIED')
                integer(e['ended_ns'], e['started_ns'], 2**63-1, 'JOURNAL_UNVERIFIED')
                pending = None
            entries.append(e)
        except Exception:
            raise GatewayError('JOURNAL_UNVERIFIED') from None
    require(pending is None, 'JOURNAL_UNVERIFIED')
    reservations = [e for e in entries if e['phase'] == 'RESERVED']
    require(sum(e['reserved_provider_calls'] for e in reservations) <= p['max_provider_calls_total']
            and sum(Decimal(e['reserved_cost_usd']) for e in reservations) <= Decimal(p['max_provider_cost_usd_total']), 'JOURNAL_UNVERIFIED')
    return entries


def killed(root, policy_hash):
    latch = root / 'autonomous-killed.json'
    expected = dict(schema_id='autonomous-killed', schema_version='1.0.0', policy_sha256=policy_hash)
    if latch.exists():
        require(read(latch) == expected, 'JOURNAL_UNVERIFIED')
        return True
    if (root / 'PILOT_KILL').exists() or (root / 'PILOT_KILL').is_symlink():
        write(latch, expected)
        return True
    return False


def terminal(code, entries=(), counts=None):
    require(code in CODES)
    done = [e for e in entries if e['phase'] == 'TERMINAL']
    reserved = [e for e in entries if e['phase'] == 'RESERVED']
    completed_ids = {e['cycle_id'] for e in done}
    ambiguous = [e for e in reserved if e['cycle_id'] not in completed_ids]
    result = dict(status='REFUSED' if code in ('POLICY_INVALID', 'JOURNAL_UNVERIFIED', 'LOCKED_BY_OTHER', 'INPUT_INVALID', 'STATE_UNAVAILABLE') else 'NO_TRADE',
        code=code, cycles_completed=len(done), public_gets=sum(e['actual_gets'] for e in done),
        provider_calls=sum(e['actual_provider_calls'] for e in done)+sum(e['reserved_provider_calls'] for e in ambiguous),
        reserved_provider_cost_usd=_canonical_decimal(sum((Decimal(e['reserved_cost_usd']) for e in reserved), Decimal(0))),
        scanner_sha256=done[-1]['scanner_sha256'] if done else None,
        hunter_sha256=done[-1]['hunter_sha256'] if done else None,
        forecast_counts=dict.fromkeys(COUNTS, 0) if counts is None else counts,
        economic_mutation_id=None, live_active=False)
    result['public_gets'] += sum(e['reserved_gets'] for e in ambiguous)
    if code in ('JOURNAL_UNVERIFIED', 'STATE_UNAVAILABLE'):
        for key in ('cycles_completed', 'public_gets', 'provider_calls', 'reserved_provider_cost_usd'):
            result[key] = None  # An unverifiable durable spend is unknown, never a false zero.
        result['forecast_counts'] = dict(REJECTED=None, SOURCE_BOUND_ONLY=None, QUALIFIED_FOR_ADMISSION=0)
    return result


@dataclass
class AutonomousDependencies:
    native: native.LiveOrchDependencies = field(default_factory=native.LiveOrchDependencies)
    transport: object = None  # Native scanner transport seam, useful only for offline tests.
    monotonic: object = time.monotonic
    pause: object = time.sleep


def run(*, policy_path, native_policy_path=None, owner_record_path=None, owner_record_sha256=None,
        hunter_scratch_dir=None, alpha_registry_path=None, budget_path=None, executable=None, home=None,
        dependencies=None):
    """Finite opt-in research; never invokes a native economic method."""
    entries = []
    try:
        deps = dependencies or AutonomousDependencies()
        p, policy_hash = load_policy(policy_path, deps.native.clock_ns())
        if p['mode'] == 'OFF':
            return terminal('OFF')
        if any(x is None for x in (native_policy_path, owner_record_path, owner_record_sha256, hunter_scratch_dir, alpha_registry_path)):
            return terminal('OWNER_SETUP_REQUIRED')
        root = common._path(p['state_root'])
        root.mkdir(mode=0o700, parents=True, exist_ok=True)
        with common._run_lock(root):
            state_root = root
            kill_id = p.get('activation_id', policy_hash)
            prior_reservations = []
            if p['schema_version'] == '2.0.0':
                # Authorize before persisting any renewal or provider reservation.
                account(p, native_policy_path, owner_record_path, owner_record_sha256, deps.native)
                root, prior_reservations = session_root(root, p, policy_hash, owner_record_sha256, deps.native.clock_ns())
            suspension = state_root / f'custody-suspended-{owner_record_sha256}.json'
            require(not suspension.exists() and not suspension.is_symlink(), 'CUSTODY_SUSPENDED')
            binding = dict(schema_id='autonomous-state-binding', schema_version='1.0.0', public_wallet=p['public_wallet'],
                public_signer=p['public_signer'], release_sha=p['release_sha'], policy_sha256=policy_hash,
                owner_record_sha256=owner_record_sha256)
            if (root / 'binding.json').exists():
                require(read(root / 'binding.json') == binding, 'JOURNAL_UNVERIFIED')
            else:
                if killed(state_root, kill_id):
                    return terminal('KILLED')
                require({x.name for x in root.iterdir()} <= ({'policy-snapshot.json'} if p['schema_version'] == '2.0.0' else {'pilot-run.lock', 'live_orch'}), 'JOURNAL_UNVERIFIED')
                account(p, native_policy_path, owner_record_path, owner_record_sha256, deps.native)
                write(root / 'binding.json', binding)
            entries = replay_journal(root, p, policy_hash)
            if killed(state_root, kill_id):
                return terminal('KILLED', entries)
            started = deps.monotonic()
            first_started = entries[0]['started_ns'] if entries else deps.native.clock_ns()
            stop_ns = min(p['valid_until_ns'], first_started+p['max_duration_s']*NS)
            deadline = min(started+p['max_duration_s'], started+(stop_ns-deps.native.clock_ns())/NS)
            counts = dict.fromkeys(COUNTS, 0)
            while len(entries)//2 < p['max_cycles']:
                index = len(entries)//2
                require(deps.monotonic() < deadline and p['valid_from_ns'] <= deps.native.clock_ns() < p['valid_until_ns'], 'BUDGET_EXHAUSTED')
                require(not killed(state_root, kill_id), 'KILLED')
                np, native_policy_hash = account(p, native_policy_path, owner_record_path, owner_record_sha256, deps.native)
                require(digest(common._read(policy_path)) == policy_hash, 'POLICY_INVALID')
                scratch = common._path(hunter_scratch_dir)
                budget = hunter.load_budget(budget_path, scratch)
                require(all(x is None for x in (budget_path, executable, home)) or all(x is not None for x in (budget_path, executable, home)), 'POLICY_INVALID')
                calls = 0 if budget is None else budget['max_runs_per_invocation']
                cost = Decimal(0) if budget is None else calls*budget['max_usd_per_run']
                budget_bytes = None if budget is None else common._read(budget_path)
                if budget_bytes is not None:
                    # The native parser and snapshot must see the same original bytes.
                    require(hunter.load_budget(budget_path, scratch) == budget
                            and common._read(budget_path) == budget_bytes, 'POLICY_INVALID')
                spent = [e for e in entries if e['phase'] == 'RESERVED']
                rolling = prior_reservations + provider_reservations(entries)
                now = deps.native.clock_ns()
                require(all(e['started_ns'] <= now and (e['ended_ns'] is None or e['ended_ns'] <= now)
                            for e in rolling), 'JOURNAL_UNVERIFIED')
                last_observed_utc = now
                if p['schema_version'] == '2.0.0':
                    recent = [e for e in rolling if e['ended_ns'] is None or now-e['ended_ns'] < 86400*NS]
                    require(sum((Decimal(e['reserved_cost_usd']) for e in recent), Decimal(0))+cost
                            <= min(Decimal(2), Decimal(np['provider_max_rolling24h_usd'])), 'BUDGET_EXHAUSTED')
                require(sum(e['reserved_provider_calls'] for e in spent)+calls <= p['max_provider_calls_total']
                    and sum((Decimal(e['reserved_cost_usd']) for e in spent), Decimal(0))+cost <= Decimal(p['max_provider_cost_usd_total']), 'BUDGET_EXHAUSTED')
                claim = dict(schema_id='autonomous-cycle-journal', schema_version=p['schema_version'], sequence=len(entries)+1,
                    previous_sha256=entries[-1]['entry_sha256'] if entries else None, policy_sha256=policy_hash,
                    cycle_id=cycle_id(p, policy_hash, index), cycle_index=index, phase='RESERVED',
                    started_ns=deps.native.clock_ns(), ended_ns=None, reserved_gets=p['max_discovery_gets_per_cycle'],
                    reserved_provider_calls=calls, reserved_cost_usd=_canonical_decimal(cost), actual_gets=0,
                    actual_provider_calls=0, reason=None, scanner_sha256=None, hunter_sha256=None, economic_mutation_id=None)
                claim = seal(claim, 'entry_sha256')
                write(root / f'journal-{claim["sequence"]:06d}.json', claim)
                entries.append(claim)
                actual_gets = 0
                actual_provider_calls = 0
                snapshot_path = None
                if budget_bytes is not None:
                    snapshot_path = root / f'provider-budget-{index:02d}.json'
                    with common._path(snapshot_path).open('xb') as stream:
                        stream.write(budget_bytes)
                        stream.flush()
                        os.fsync(stream.fileno())

                def check_runtime():
                    nonlocal last_observed_utc
                    current_utc = deps.native.clock_ns()
                    require(current_utc >= last_observed_utc, 'JOURNAL_UNVERIFIED')
                    last_observed_utc = current_utc
                    require(not killed(state_root, kill_id), 'KILLED')
                    require(digest(common._read(policy_path)) == policy_hash, 'POLICY_INVALID')
                    require(digest(common._read(native_policy_path)) == native_policy_hash
                            and digest(common._read(owner_record_path)) == owner_record_sha256, 'OWNER_SETUP_REQUIRED')
                    require(deps.monotonic() < deadline
                            and current_utc < p['valid_until_ns'], 'BUDGET_EXHAUSTED')

                def before_get():
                    nonlocal actual_gets
                    check_runtime()
                    require(actual_gets < claim['reserved_gets'], 'BUDGET_EXHAUSTED')
                    actual_gets += 1  # Ambiguous wire requests consume their reservation.

                def controlled_research(request, backend, **kwargs):
                    nonlocal actual_provider_calls
                    check_runtime()
                    require(snapshot_path is not None and common._read(snapshot_path) == budget_bytes, 'POLICY_INVALID')
                    require(actual_provider_calls < calls
                        and Decimal(str(request.max_accepted_estimated_cost_usd)) <= budget['max_usd_per_run']
                        and deadline-deps.monotonic() >= request.max_wall_seconds, 'BUDGET_EXHAUSTED')
                    actual_provider_calls += 1  # An interrupted inference is never refunded.
                    result = hunter.run_controlled_hermes_research(request, backend, **kwargs)
                    check_runtime()
                    return result

                def transport(url, timeout, maximum):
                    before_get()
                    result = (deps.transport or scanner.public_read)(url, min(timeout, max(0.001, deadline-deps.monotonic())), maximum)
                    require(not killed(state_root, kill_id), 'KILLED')
                    return result

                class MeteredFetcher(hunter.Fetcher):
                    def get(self, url):
                        before_get()
                        result = super().get(url)
                        require(not killed(state_root, kill_id), 'KILLED')
                        return result

                reason, scanner_sha, hunter_sha = 'NO_CANDIDATES', None, None
                try:
                    capture = root / f'research-{index:02d}'
                    wide = {'all_horizons': True} if p['schema_version'] == '2.0.0' else {}
                    result = scanner.run(capture, transport=transport, clock_ns=deps.native.clock_ns, monotonic=deps.monotonic, **wide)
                    check_runtime()
                    verified = scanner.verify(capture)
                    if result['status'] == 'COMPLETED' and verified['status'] == 'VERIFIED':
                        scanner_sha = verified['manifest_sha256']
                        from src.live_pilot.structural import assess_capture
                        require(assess_capture(capture)['execution_eligible'] is False, 'GATE_REJECTED')
                    else:
                        raise GatewayError('SOURCE_INDEPENDENCE_UNPROVEN')
                    require(not killed(state_root, kill_id), 'KILLED')
                    # Native Hunter acquisition + native worst-case inference runtime must fit.
                    required_seconds = hunter.CONFIG['max_acquisition_seconds']+calls*300+30
                    require(deadline-deps.monotonic() >= required_seconds, 'BUDGET_EXHAUSTED')
                    categories = {key for key, value in hunter.CATEGORIES.items() if value in np['categories']}
                    require(categories, 'FORECAST_METHOD_UNSUPPORTED')
                    scratch.mkdir(mode=0o700, parents=True, exist_ok=True)
                    outcome = hunter.run(scratch, common._path(alpha_registry_path), categories,
                        budget_path=snapshot_path, executable=executable, home=home,
                        fetcher_type=MeteredFetcher, clock_ns=deps.native.clock_ns, controller=controlled_research)
                    require(outcome['status'] == 'COMPLETED', 'SOURCE_INDEPENDENCE_UNPROVEN')
                    require(not killed(state_root, kill_id), 'KILLED')
                    operations = sorted(scratch.glob('index-op-*.json'))
                    operation = operations[-1].stem.removeprefix('index-')
                    hunter_sha = outcome['manifest_sha256']
                    forecasts = replay_forecasts(scratch, operation, np, deps.native.clock_ns())
                    from src.live_pilot.edge_qualifier import qualify_candidate
                    # This invokes the independent admission boundary, never a model badge.
                    for forecast in forecasts:
                        require(qualify_candidate(forecast)['production_eligible'] is False, 'GATE_REJECTED')
                    for forecast in forecasts[:p['max_market_candidates_per_cycle']]:
                        counts[forecast['qualification_state']] += 1
                    reason = 'CALIBRATION_NOT_VERIFIED' if forecasts else 'NO_CANDIDATES'
                except Exception as error:
                    reason = error.code if isinstance(error, GatewayError) and error.code in CODES else 'SOURCE_INDEPENDENCE_UNPROVEN'
                end = seal(dict(claim, sequence=len(entries)+1, previous_sha256=entries[-1]['entry_sha256'],
                    phase='TERMINAL', ended_ns=deps.native.clock_ns(), actual_gets=actual_gets,
                    actual_provider_calls=actual_provider_calls, reason=reason, scanner_sha256=scanner_sha, hunter_sha256=hunter_sha), 'entry_sha256')
                write(root / f'journal-{end["sequence"]:06d}.json', end)
                entries.append(end)
                if reason not in ('CALIBRATION_NOT_VERIFIED', 'NO_CANDIDATES') or index+1 >= p['max_cycles']:
                    return terminal(reason, entries, counts)
                until = deps.monotonic()+p['cadence_s']
                while deps.monotonic() < until:
                    require(not killed(state_root, kill_id), 'KILLED')
                    require(deps.monotonic() < deadline and deps.native.clock_ns() < p['valid_until_ns'], 'BUDGET_EXHAUSTED')
                    deps.pause(min(1, until-deps.monotonic(), deadline-deps.monotonic()))
            return terminal('BUDGET_EXHAUSTED', entries, counts)
    except Exception as error:
        code = error.code if isinstance(error, GatewayError) and error.code in CODES else 'INPUT_INVALID'
        if isinstance(error, GatewayError) and error.code == 'PILOT_RUN_BUSY':
            code = 'LOCKED_BY_OTHER'
        return terminal(code, entries)


def activation_report(*, software_verified=False):
    """A software report cannot assert an account, calibrated edge or live receipt."""
    return dict(disposition='READY_BUT_ACTIVATION_BLOCKED' if software_verified else 'IMPLEMENTATION_BLOCKED',
        live_active=False, account_connected=False, orders=0,
        software_status='SOFTWARE_IMPLEMENTED_NOT_ACTIVATED' if software_verified else 'IMPLEMENTATION_BLOCKED',
        edge_status='NOT_QUALIFIED', accepted_production_methods=0, accepted_production_corpora=0,
        account_status='NOT_VERIFIED', funds_status='NOT_VERIFIED', provider_consent_status='NOT_VERIFIED',
        first_canary_status='NOT_OBSERVED', unattended_status='DISABLED',
        blockers=['CALIBRATION_NOT_VERIFIED', 'OWNER_SETUP_REQUIRED', 'CANARY_APPROVAL_MISSING'])


def evidence_activation_report(scratch=None):
    """Offline evidence checkpoint, with no inferred account/host/canary receipts."""
    from src.live_pilot.provenance import empty_report, verify_capture
    evidence = empty_report() if scratch is None else verify_capture(scratch)
    return dict(software='NOT_VERIFIED', evidence=evidence, method='NOT_QUALIFIED',
                account='NOT_OBSERVED', funding='NOT_OBSERVED', custody='NOT_OBSERVED',
                eligible_host='NOT_OBSERVED', provider_consent='NOT_OBSERVED',
                first_canary='NOT_OBSERVED', unattended='DISABLED', live_active=False)


def session_root(root, p, policy_hash, owner_hash, now):
    """Under the existing run lock: one activation, chained finite session journals."""
    activation = dict(schema_id='autonomous-activation', schema_version='2.0.0',
        activation_id=p['activation_id'], public_wallet=p['public_wallet'], state_root=str(root),
        activation_ledger_head=p['activation_ledger_head'])
    path = root/'activation.json'
    dirs = sorted(root.glob('session-*'))
    require(len(dirs) <= 256, 'JOURNAL_UNVERIFIED')
    if path.exists():
        require(read(path) == activation, 'JOURNAL_UNVERIFIED')
    else:
        require(not dirs and p['previous_session_sha256'] is None, 'JOURNAL_UNVERIFIED')
        write(path, activation)
    histories = []
    for directory in dirs:
        common._path(directory)
        old = read(directory/'policy-snapshot.json')
        validated, old_hash = load_policy(directory/'policy-snapshot.json', old['valid_from_ns'], snapshot=True)
        require(directory.name == 'session-'+old_hash and all(validated[k] == p[k] for k in
            ('activation_id', 'activation_ledger_head', 'public_wallet', 'state_root')), 'JOURNAL_UNVERIFIED')
        if old_hash == policy_hash:
            continue
        binding = read(directory/'binding.json')
        require(binding['policy_sha256'] == old_hash and binding['public_wallet'] == p['public_wallet'], 'JOURNAL_UNVERIFIED')
        entries = replay_journal(directory, old, old_hash)
        require(entries and entries[-1]['phase'] == 'TERMINAL', 'JOURNAL_UNVERIFIED')
        histories.append((old['valid_from_ns'], old, entries))
    histories.sort(key=lambda row: (row[0], row[2][-1]['entry_sha256']))
    previous = None
    reservations = []
    ended = 0
    for _, old, entries in histories:
        require(old['previous_session_sha256'] == previous and entries[0]['started_ns'] >= ended, 'JOURNAL_UNVERIFIED')
        previous = entries[-1]['entry_sha256']
        ended = entries[-1]['ended_ns']
        reservations.extend(provider_reservations(entries))
    require(p['previous_session_sha256'] == previous and ended <= now, 'JOURNAL_UNVERIFIED')
    directory = common._path(root/('session-'+policy_hash))
    if not directory.exists():
        require(len(dirs) < 256, 'BUDGET_EXHAUSTED')
        directory.mkdir(mode=0o700)
        write(directory/'policy-snapshot.json', p)
    else:
        require(read(directory/'policy-snapshot.json') == p, 'JOURNAL_UNVERIFIED')
    return directory, reservations


def provider_reservations(entries):
    """Keep the whole maximum through terminal+24h, covering every late dispatch."""
    ends = {e['cycle_id']: e['ended_ns'] for e in entries if e['phase'] == 'TERMINAL'}
    return [dict(e, ended_ns=ends.get(e['cycle_id'])) for e in entries if e['phase'] == 'RESERVED']
