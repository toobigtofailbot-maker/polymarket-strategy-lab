"""Protected composition tests; all sources, wallets and sessions are synthetic."""
from copy import deepcopy
from dataclasses import replace
from decimal import Decimal
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from src.execution_gateway.gateway import GatewayError
from src.live_pilot import autonomous_cycle as A
from tests.tools.alpha import test_alpha_hunter as sources
from tests.tools.alpha import test_near_term_market_screener as near
from tests.live_pilot import test_hunter_cycle as native_test

NOW = near.NOW


def policy(tmp_path, now=near.NOW, **changes):
    value = dict(schema_id='autonomous-cycle-policy', schema_version='1.0.0', mode='OFF',
        public_wallet='0x'+'1'*40, public_signer='0x'+'2'*40, state_root=str(tmp_path/'state'),
        release_sha='a'*40, valid_from_ns=now-A.NS, valid_until_ns=now+7200*A.NS-A.NS,
        max_cycles=1, max_duration_s=7200, cadence_s=60, max_discovery_gets_per_cycle=40,
        max_market_candidates_per_cycle=10, max_provider_calls_total=0, max_provider_cost_usd_total='0',
        max_buy_mutations_per_cycle=1, max_buy_mutations_rolling24h=2,
        max_fee_inclusive_order_usd='5', max_total_commitment_usd='30', min_free_collateral_usd='50',
        min_stress_margin_usd='0', kill_file_name='PILOT_KILL')
    value.update(changes)
    return value


def save(path, value):
    path.write_bytes(A.canonical(value))
    return path


def harness(tmp_path, monkeypatch, **changes):
    s = native_test.build(tmp_path, monkeypatch)
    p = policy(tmp_path, native_test.X.AT, mode='RESEARCH', public_wallet=s.policy['public_wallet'],
        public_signer=s.policy['public_signer'], release_sha=s.policy['release_sha'], **changes)
    path = save(tmp_path/'autonomous.json', p)
    calls = []

    def transport(url, timeout, maximum):
        calls.append(url)
        return 'HTTP_2XX', b'[]'  # Bounded empty metadata; never a claim about real markets.

    deps = A.AutonomousDependencies(native=s.deps.native, transport=transport)
    args = dict(policy_path=path, native_policy_path=s.policy_path, owner_record_path=s.owner_path,
        owner_record_sha256=s.owner_hash, hunter_scratch_dir=tmp_path/'source-replay',
        alpha_registry_path=tmp_path/'alpha.sqlite3', dependencies=deps)
    return SimpleNamespace(native=s, policy=p, path=path, args=args, calls=calls)


def no_wire_hunter(monkeypatch):
    # Native source acquisition is separately covered by the cold-replay test below.
    monkeypatch.setattr(A.hunter, 'run', lambda *a, **k: {'status': 'BLOCKED'})


def test_native_reuse_and_no_direct_order_bypass(tmp_path, monkeypatch):
    s = harness(tmp_path, monkeypatch)
    no_wire_hunter(monkeypatch)
    result = A.run(**s.args)
    assert result['economic_mutation_id'] is None and result['live_active'] is False
    assert not s.native.harness.venue.posts
    assert A.CALIBRATED_METHODS == frozenset()
    assert s.calls and all(url.startswith('https://gamma-api.polymarket.com/markets?') for url in s.calls)


def test_bounded_scan_and_abstention(tmp_path, monkeypatch):
    s = harness(tmp_path, monkeypatch, max_discovery_gets_per_cycle=1)
    no_wire_hunter(monkeypatch)
    result = A.run(**s.args)
    assert result['status'] == 'NO_TRADE' and result['public_gets'] <= 1
    assert result['forecast_counts']['QUALIFIED_FOR_ADMISSION'] == 0
    assert result['scanner_sha256'] is not None
    assert A.scanner.verify(Path(s.policy['state_root'])/'research-00')['status'] == 'VERIFIED'


def source_record():
    return A.seal(dict(schema_id='autonomous-forecast', schema_version='1.0.0',
        strategy_version_id='strategyversion:sha256:'+'1'*64, market_id='1', condition_id='0x'+'2'*64,
        token_id='3', outcome_index=0, resolution_rule_sha256='3'*64, source_cutoff_ns=10,
        evaluated_ns=11, expires_ns=12, native_method_id='NBA_ESPN_V1', native_method_sha256='4'*64,
        source_receipts=[dict(source_kind='ESPN', raw_sha256='5'*64, received_ns=9, url_sha256='6'*64)],
        p_point='0.95', p_lower='0.9', p_upper='1', qualification_state='SOURCE_BOUND_ONLY',
        reason_codes=['CALIBRATION_NOT_VERIFIED']), 'record_sha256')


def test_bounded_cycle_quota_and_restart(tmp_path, monkeypatch):
    s = harness(tmp_path,monkeypatch,max_discovery_gets_per_cycle=1)
    no_wire_hunter(monkeypatch)
    first = A.run(**s.args)
    calls = len(s.calls)
    again = A.run(**s.args)
    assert first['status'] == again['status'] == 'NO_TRADE'
    assert len(s.calls) == calls and first['public_gets'] == again['public_gets']


def test_unknown_exposure_restart_and_kill(tmp_path, monkeypatch):
    s = harness(tmp_path,monkeypatch)
    root=Path(s.policy['state_root']);root.mkdir()
    (root/'PILOT_KILL').write_text('stop')
    assert A.run(**s.args)['code'] == 'KILLED' and not s.calls
    (root/'PILOT_KILL').unlink()
    assert A.run(**s.args)['code'] == 'KILLED' and not s.calls


def test_session_chain_retains_reservations_and_refuses_resets(tmp_path):
    p=policy(tmp_path,schema_version='2.0.0',max_total_commitment_usd='10',
        min_free_collateral_usd='90',activation_id='a'*64,activation_ledger_head='b'*64,
        previous_session_sha256=None,max_provider_cost_usd_total='2',max_provider_calls_total=2)
    root=tmp_path/'state';root.mkdir()
    h=A.digest(A.canonical(p))
    directory,prior=A.session_root(root,p,h,'c'*64,NOW)
    assert prior==[]
    A.write(directory/'binding.json',dict(policy_sha256=h,public_wallet=p['public_wallet']))
    claim=A.seal(dict(schema_id='autonomous-cycle-journal',schema_version='2.0.0',sequence=1,
        previous_sha256=None,policy_sha256=h,cycle_id=A.cycle_id(p,h,0),cycle_index=0,
        phase='RESERVED',started_ns=NOW,ended_ns=None,reserved_gets=1,reserved_provider_calls=1,
        reserved_cost_usd='1.5',actual_gets=0,actual_provider_calls=0,reason=None,
        scanner_sha256=None,hunter_sha256=None,economic_mutation_id=None),'entry_sha256')
    A.write(directory/'journal-000001.json',claim)
    next_p=dict(p,valid_from_ns=NOW+10,valid_until_ns=NOW+1000,previous_session_sha256='d'*64)
    nh=A.digest(A.canonical(next_p))
    with pytest.raises(GatewayError):
        A.session_root(root,next_p,nh,'c'*64,NOW+20)
    end=A.seal(dict(claim,sequence=2,previous_sha256=claim['entry_sha256'],phase='TERMINAL',
        ended_ns=NOW+1,reason='NO_CANDIDATES'),'entry_sha256')
    A.write(directory/'journal-000002.json',end)
    next_p['previous_session_sha256']=end['entry_sha256'];nh=A.digest(A.canonical(next_p))
    directory2,prior=A.session_root(root,next_p,nh,'c'*64,NOW+20)
    assert len(prior)==1 and prior[0]['reserved_cost_usd']=='1.5' and directory2!=directory
    bad=dict(next_p,activation_id='e'*64)
    with pytest.raises(GatewayError):
        A.session_root(root,bad,A.digest(A.canonical(bad)),'c'*64,NOW+21)


def test_rolling_budget_counts_late_dispatch_after_cycle_start_expires():
    start=1000*A.NS
    entries=[dict(phase='RESERVED',cycle_id='x',started_ns=start,ended_ns=None,reserved_cost_usd='2'),
             dict(phase='TERMINAL',cycle_id='x',started_ns=start,ended_ns=start+600*A.NS)]
    reserved=A.provider_reservations(entries)
    now=start+86401*A.NS
    assert now-reserved[0]['started_ns']>86400*A.NS
    assert now-reserved[0]['ended_ns']<86400*A.NS
    assert sum(Decimal(e['reserved_cost_usd']) for e in reserved
               if e['ended_ns'] is None or now-e['ended_ns']<86400*A.NS)==2
    assert A.provider_reservations(entries[:1])[0]['ended_ns'] is None


def test_same_policy_resume_rejects_backward_utc_before_new_reservation(tmp_path,monkeypatch):
    s=harness(tmp_path,monkeypatch,max_cycles=2)
    no_wire_hunter(monkeypatch)
    assert A.run(**s.args)['cycles_completed']==1
    root=Path(s.policy['state_root'])
    terminal_path=root/'journal-000002.json'
    end=A.read(terminal_path)
    start=end['started_ns']
    # A faithful completed journal from before the clock adjustment.
    end=A.seal(dict(end,ended_ns=start+600*A.NS),'entry_sha256')
    terminal_path.write_bytes(A.canonical(end)+b'\n')
    s.native.harness.now=start+300*A.NS  # Fresh official-access proof after clock adjustment.
    monkeypatch.setattr(s.native.harness,'clock',lambda:start+300*A.NS)
    s.args['dependencies'].native.clock_ns=lambda:start+300*A.NS
    calls=len(s.calls)
    result=A.run(**s.args)
    assert result['code']=='JOURNAL_UNVERIFIED' and len(s.calls)==calls
    assert not (root/'journal-000003.json').exists()


def test_in_cycle_backward_utc_stops_next_source_dispatch(tmp_path,monkeypatch):
    s=harness(tmp_path,monkeypatch)
    no_wire_hunter(monkeypatch)
    original=s.args['dependencies'].transport
    def rewind(url,timeout,maximum):
        result=original(url,timeout,maximum)
        now=s.args['dependencies'].native.clock_ns()
        s.args['dependencies'].native.clock_ns=lambda:now-100*A.NS
        return result
    s.args['dependencies'].transport=rewind
    result=A.run(**s.args)
    assert len(s.calls)==1 and not s.native.harness.venue.posts
    assert result['code']=='JOURNAL_UNVERIFIED'


def test_real_hermes_evidence_and_no_fake_edge(tmp_path, monkeypatch):
    record = source_record()
    assert A.validate_forecast(record)
    # Shaped/rehashed confidence is never an admission method.
    forged = A.seal(dict(record, qualification_state='QUALIFIED_FOR_ADMISSION'), 'record_sha256')
    assert A.validate_forecast(forged) and not A.CALIBRATED_METHODS
    generic = A.seal(dict(record, native_method_id='GENERIC_HERMES'), 'record_sha256')
    with pytest.raises(GatewayError):
        A.validate_forecast(generic)
    # A real native cold replay over recorded-shape synthetic raw source bytes.
    s = native_test.build(tmp_path, monkeypatch)
    root, registry = tmp_path/'raw-native', tmp_path/'native-alpha.sqlite3'
    root.mkdir()
    assert sources.AFR.initialize_alpha_factory_registry(str(registry)).is_valid
    result = A.hunter.run(root, registry, {'nba'}, fetcher_type=sources.replica(sources.payloads()), clock_ns=sources.clock())
    assert result['status'] == 'COMPLETED'
    records = A.replay_forecasts(root, 'op-000001', s.policy, sources.NOW+10*A.NS)
    assert records and all(r['qualification_state'] == 'SOURCE_BOUND_ONLY' for r in records)
    assert all(r['reason_codes'] == ['CALIBRATION_NOT_VERIFIED'] for r in records)
    raw = next((root/'op-000001').glob('source-*.json'))
    raw.write_bytes(raw.read_bytes()+b' ')
    with pytest.raises(Exception):
        A.replay_forecasts(root, 'op-000001', s.policy, sources.NOW+10*A.NS)


def test_native_fee_minimum_risk_and_cap():
    with pytest.raises(GatewayError) as caught:
        A.pilot.size_order(ask=Decimal('0.5'), depth=Decimal(100), rate=Decimal('0.05'), exponent=1,
            cap=Decimal(5), floor=Decimal(2), gamma_min=Decimal(5), book_min=Decimal(1), seconds_delay=0)
    assert caught.value.code == 'MINIMUM_UNSATISFIABLE_WITHIN_FEE_INCLUSIVE_CAP'
    q, fee = A.pilot.size_order(ask=Decimal('0.5'), depth=Decimal(100), rate=Decimal('0.05'), exponent=1,
        cap=Decimal(5), floor=Decimal(2), gamma_min=Decimal(1), book_min=Decimal(1), seconds_delay=0)
    assert Decimal(2) <= q*Decimal('0.5')+fee <= Decimal(5)
    assert not A.CALIBRATED_METHODS  # Mechanically possible does not mean qualified.


def test_risk_kill_recovery_and_reconciliation(tmp_path, monkeypatch):
    s = harness(tmp_path, monkeypatch)
    # Race after read-only ledger: lock-held native checkpoint must reject a resting order.
    monkeypatch.setattr(A._ResearchAccount, 'ledger', lambda self: {'episodes': []})
    original = A._ResearchAccount._recover_all

    def raced(self, session):
        gateway = SimpleNamespace(live_orch_checkpoint=lambda: {'episodes': [{'state': 'RESTING'}]})
        return original(self, SimpleNamespace(gateway=gateway))

    monkeypatch.setattr(A._ResearchAccount, '_recover_all', raced)
    result = A.run(**s.args)
    assert result['code'] == 'ACCOUNT_UNKNOWN' and not s.calls and not s.native.harness.venue.posts
    with pytest.raises(GatewayError, match='ACCOUNT_UNKNOWN'):
        A._ResearchAccount._cancel_rounds(None, None, 'synthetic')


def test_unattended_singleton_budget_restart(tmp_path, monkeypatch):
    s = harness(tmp_path, monkeypatch)
    no_wire_hunter(monkeypatch)
    first = A.run(**s.args)
    assert first['cycles_completed'] == 1
    call_count = len(s.calls)
    again = A.run(**s.args)
    assert again['code'] == 'BUDGET_EXHAUSTED' and len(s.calls) == call_count
    root = Path(s.policy['state_root'])
    terminal_path = root/'journal-000002.json'
    # Copy is a crash fixture: remove only a test-created terminal, never production state.
    terminal_path.unlink()
    result = A.run(**s.args)
    assert result['code'] == 'JOURNAL_UNVERIFIED' and len(s.calls) == call_count
    assert result['provider_calls'] is None and result['reserved_provider_cost_usd'] is None
    with A.common._run_lock(root):
        assert A.run(**s.args)['code'] == 'LOCKED_BY_OTHER'


def test_authority_denial_and_evidence_replay(tmp_path, monkeypatch):
    s = harness(tmp_path, monkeypatch)
    no_wire_hunter(monkeypatch)
    A.run(**s.args)
    root = Path(s.policy['state_root'])
    entries = A.replay_journal(root, s.policy, A.digest(A.canonical(s.policy)))
    assert len(entries) == 2
    path = root/'journal-000002.json'
    entry = A.read(path)
    entry['actual_gets'] = entry['reserved_gets']+1
    entry = A.seal(entry, 'entry_sha256')
    path.write_bytes(A.canonical(entry)+b'\n')
    assert A.run(**s.args)['code'] == 'JOURNAL_UNVERIFIED'
    assert not s.native.harness.venue.posts


def test_truthful_activation_report():
    assert A.activation_report()['disposition'] == 'IMPLEMENTATION_BLOCKED'
    report = A.activation_report(software_verified=True)
    assert report['disposition'] == 'READY_BUT_ACTIVATION_BLOCKED'
    assert report['orders'] == 0 and not report['account_connected'] and not report['live_active']
    assert 'CALIBRATION_NOT_VERIFIED' in report['blockers']


@pytest.mark.parametrize('field,value', [('max_cycles', True), ('max_cycles', 5), ('mode', 'AUTO'),
    ('max_provider_cost_usd_total', 'NaN'), ('max_fee_inclusive_order_usd', '5.01'),
    ('min_free_collateral_usd', '49'), ('kill_file_name', '../KILL'), ('extra', 'secret-sentinel')])
def test_strict_policy_negative_matrix(tmp_path, field, value):
    p = policy(tmp_path)
    p[field] = value
    path = save(tmp_path/'policy.json', p)
    deps = A.AutonomousDependencies(native=replace(A.native.LiveOrchDependencies(), clock_ns=lambda: near.NOW))
    result = A.run(policy_path=path, dependencies=deps)
    assert result['code'] == 'POLICY_INVALID' and 'secret-sentinel' not in json.dumps(result)
    assert not (tmp_path/'state').exists()


def test_forecast_identity_and_negative_matrix():
    record = source_record()
    assert A.seal(dict(reversed(list(record.items()))), 'record_sha256') == record
    changed = deepcopy(record)
    changed['source_receipts'].append(dict(changed['source_receipts'][0], url_sha256='7'*64))
    forward = A.seal(changed, 'record_sha256')
    changed['source_receipts'].reverse()
    assert A.seal(changed, 'record_sha256')['record_sha256'] != forward['record_sha256']
    for field, value in [('p_lower', '0.99'), ('p_upper', 'Infinity'), ('outcome_index', True),
                         ('source_cutoff_ns', 0), ('extra', 'never-echo')]:
        with pytest.raises(GatewayError):
            A.validate_forecast(A.seal(dict(record, **{field: value}), 'record_sha256'))


def test_kill_latches_and_no_provider_default(tmp_path, monkeypatch):
    s = harness(tmp_path, monkeypatch)
    root = Path(s.policy['state_root'])
    root.mkdir(exist_ok=True)
    (root/'PILOT_KILL').touch()
    # First kill must stop even before native authentication, binding or acquisition.
    result = A.run(**s.args)
    assert result['code'] == 'KILLED' and not s.calls
    (root/'PILOT_KILL').unlink()
    assert A.run(**s.args)['code'] == 'KILLED'


def budget_harness(tmp_path, monkeypatch):
    s = harness(tmp_path, monkeypatch, max_provider_calls_total=1, max_provider_cost_usd_total='0.01')
    scratch = s.args['hunter_scratch_dir']
    budget = dict(provider_label='synthetic', model_label='offline', ledger_scratch_dir=str(scratch),
        max_runs_per_invocation=1, max_usd_per_run=0.01, max_runs_per_7d=1, max_usd_per_7d=0.01)
    path = tmp_path/'budget.json'
    path.write_text(json.dumps(budget))
    s.args.update(budget_path=path, executable=str(tmp_path/'hermes'), home=str(tmp_path/'home'))
    return s, path, budget


def test_provider_budget_snapshot_and_dispatch_ceiling(tmp_path, monkeypatch):
    s, budget_path, original = budget_harness(tmp_path, monkeypatch)
    sent = []
    native_transport = s.args['dependencies'].transport

    def changing_transport(*args):
        budget_path.write_text(json.dumps(dict(original, max_runs_per_invocation=3, max_usd_per_run=0.5)))
        return native_transport(*args)

    s.args['dependencies'].transport = changing_transport
    monkeypatch.setattr(A.hunter, 'run_controlled_hermes_research', lambda *a, **k: sent.append(True))

    def run(*args, **kwargs):
        snapshot = A.hunter.load_budget(kwargs['budget_path'], s.args['hunter_scratch_dir'])
        assert snapshot['max_runs_per_invocation'] == 1 and snapshot['max_usd_per_run'] == Decimal('0.01')
        request = SimpleNamespace(max_accepted_estimated_cost_usd='0.01', max_wall_seconds=300)
        kwargs['controller'](request, object())
        with pytest.raises(GatewayError, match='BUDGET_EXHAUSTED'):
            kwargs['controller'](request, object())
        return {'status': 'BLOCKED'}

    monkeypatch.setattr(A.hunter, 'run', run)
    result = A.run(**s.args)
    assert sent == [True] and result['provider_calls'] == 1
    assert result['reserved_provider_cost_usd'] == '0.01'
    assert not s.native.harness.venue.posts


def test_kill_between_each_inference(tmp_path, monkeypatch):
    s, _, _ = budget_harness(tmp_path, monkeypatch)
    sent = []

    def dispatch(*args, **kwargs):
        sent.append(True)
        (Path(s.policy['state_root'])/'PILOT_KILL').touch()

    monkeypatch.setattr(A.hunter, 'run_controlled_hermes_research', dispatch)

    def run(*args, **kwargs):
        for _ in range(3):  # Native stage catches failed research; wrapper must still stop dispatch.
            with pytest.raises(GatewayError, match='KILLED'):
                kwargs['controller'](SimpleNamespace(max_accepted_estimated_cost_usd='0.01', max_wall_seconds=300), object())
        return {'status': 'BLOCKED'}

    monkeypatch.setattr(A.hunter, 'run', run)
    result = A.run(**s.args)
    assert sent == [True] and result['provider_calls'] == 1 and not result['live_active']


def test_ambiguous_reservation_and_mutated_owner_never_dispatch(tmp_path, monkeypatch):
    s, _, _ = budget_harness(tmp_path, monkeypatch)
    sent = []
    monkeypatch.setattr(A.hunter, 'run_controlled_hermes_research', lambda *a, **k: sent.append(True))

    def run(*args, **kwargs):
        s.native.owner_path.write_bytes(b'changed-native-owner')
        with pytest.raises(GatewayError, match='OWNER_SETUP_REQUIRED'):
            kwargs['controller'](SimpleNamespace(max_accepted_estimated_cost_usd='0.01', max_wall_seconds=300), object())
        return {'status': 'BLOCKED'}

    monkeypatch.setattr(A.hunter, 'run', run)
    result = A.run(**s.args)
    assert sent == [] and result['reserved_provider_cost_usd'] == '0.01'


def test_native_verified_policy_hash_survives_to_dispatch(tmp_path, monkeypatch):
    s = harness(tmp_path, monkeypatch)
    original = A.account
    checked = []

    def change_after_validation(*args):
        value = original(*args)
        checked.append(True)
        if len(checked) == 2:
            s.native.policy_path.write_bytes(b'changed-after-native-validation')
        return value

    monkeypatch.setattr(A, 'account', change_after_validation)
    result = A.run(**s.args)
    assert result['code'] == 'OWNER_SETUP_REQUIRED' and not s.calls
    assert not s.native.harness.venue.posts


def test_native_custody_suspension_prevents_authentication(tmp_path, monkeypatch):
    s = harness(tmp_path, monkeypatch)
    root = Path(s.policy['state_root'])
    root.mkdir(exist_ok=True)
    (root/f'custody-suspended-{s.native.owner_hash}.json').write_text('{}')
    result = A.run(**s.args)
    assert result['code'] == 'CUSTODY_SUSPENDED'
    assert s.native.harness.secret_requests == 0 and not s.calls


def test_exact_output_fields_and_recursive_no_echo(tmp_path, monkeypatch):
    terminal_fields = set(('status code cycles_completed public_gets provider_calls reserved_provider_cost_usd '
        'scanner_sha256 hunter_sha256 forecast_counts economic_mutation_id live_active').split())
    report_fields = {'disposition', 'live_active', 'account_connected', 'orders', 'blockers',
        'software_status', 'edge_status', 'accepted_production_methods', 'accepted_production_corpora',
        'account_status', 'funds_status', 'provider_consent_status', 'first_canary_status', 'unattended_status'}
    assert set(A.terminal('OFF')) == terminal_fields
    assert set(A.activation_report()) == report_fields
    assert set(source_record()) == A.FORECAST_KEYS and len(A.FORECAST_KEYS) == 20
    marker = 'untrusted-echo-sentinel'
    s = harness(tmp_path, monkeypatch)
    monkeypatch.setattr(A.scanner, 'run', lambda *a, **k: (_ for _ in ()).throw(RuntimeError(marker)))
    result = A.run(**s.args)
    assert set(result) == terminal_fields and marker not in json.dumps(result)
    assert result['code'] == 'SOURCE_INDEPENDENCE_UNPROVEN'
    for code in A.CODES:
        safe = A.terminal(code)
        assert set(safe) == terminal_fields and marker not in json.dumps(safe)


def test_corrupt_binding_preserves_unknown_spend(tmp_path, monkeypatch):
    s = harness(tmp_path, monkeypatch)
    no_wire_hunter(monkeypatch)
    assert A.run(**s.args)['cycles_completed'] == 1
    (Path(s.policy['state_root'])/'binding.json').write_bytes(b'{"broken-untrusted-state":')
    result = A.run(**s.args)
    assert result['code'] == 'JOURNAL_UNVERIFIED'
    assert result['provider_calls'] is result['reserved_provider_cost_usd'] is None
    assert not s.native.harness.venue.posts


def test_bounded_evidence_session_restart_no_rearm(tmp_path, monkeypatch):
    test_same_policy_resume_rejects_backward_utc_before_new_reservation(tmp_path, monkeypatch)
