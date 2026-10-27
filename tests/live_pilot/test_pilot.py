"""Offline contracts with real native stores/kernel and synthetic source bytes."""
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timezone
from decimal import Decimal
import json
from pathlib import Path
import shutil
from types import SimpleNamespace

import pytest

from src.live_pilot import pilot as P
from src.execution_gateway.gateway import GatewayError
from tests.execution_gateway import test_live_orch as L
from tests.exploratory_gate_c import test_exploratory_gate_c as X
from tests.tools.alpha import test_shadow_alpha_cycle as F


def utc(ns):
    return datetime.fromtimestamp(ns // P.NS, timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


@pytest.fixture
def setup(tmp_path, monkeypatch):
    world = X.make_world(tmp_path,hermes=False)
    world.assess(t=X.AT)
    harness = L.Harness(tmp_path, world)
    root = tmp_path / 'state'
    feeder = root / 'feeder'
    feeder.mkdir(parents=True)
    policy = dict(schema_id='polymarket-live-pilot-policy', schema_version='1.0.0',
        public_wallet=L.WALLET, public_signer=L.SIGNER, release_sha=L.RELEASE,
        host={k: str(v) if isinstance(v, Path) else v for k, v in vars(harness.config().host).items()
              if k != 'expected_release_sha'}, state_root=str(root), feeder_root=str(feeder),
        lifecycle_store_path=str(world.lifecycle), hermes_store_path=str(world.hermes),
        strategy_version_id=world.version.strategy_version_id, market_predicate='NBA_MONEYLINE_PREGAME_V1',
        side='BUY', order_type='FOK', valid_from_utc=utc(X.AT - P.DAY), valid_until_utc=utc(X.AT + P.DAY),
        max_admissions_24h=2, max_total_commitment_usd='10', max_order_commitment_usd='5',
        max_feeder_age_s=1800, max_hermes_assessment_age_s=86400,
        max_realized_pnl_loss_usd='5', max_position_pnl_drawdown_usd='7.5', max_cumulative_loss_usd='10',
        experimental_margin_usd='0')
    s = SimpleNamespace(world=world, harness=harness, root=root, feeder=feeder, policy=policy,
                        policy_path=tmp_path/'policy.json', owner_path=tmp_path/'owner.json')
    def write():
        s.policy_path.write_bytes(P._canonical(s.policy))
        s.owner = dict(schema_id='polymarket-live-pilot-owner-activation', schema_version='1.0.0',
            policy_sha256=P._digest(s.policy_path.read_bytes()),
            **{k:s.policy[k] for k in ('public_wallet','public_signer','release_sha','state_root','valid_from_utc','valid_until_utc')})
        s.owner_path.write_bytes(P._canonical(s.owner))
        s.owner_hash=P._digest(s.owner_path.read_bytes())
    s.write=write
    write()
    s.deps=harness.deps()
    monkeypatch.setattr(P, 'InteractiveGateBSecretProvider', s.deps.secret_provider_factory)
    s.candidate=dict(event_id='fixture', gamma_market_id=X.GAMMA_ID, condition_id=X.COND, token_id=X.TOKEN,
        start_ns=X.AT+3600*P.NS, probability=Decimal('.90'), received_ns=(X.AT, X.AT))
    def run():
        return P.run_pilot_once(policy_path=s.policy_path,owner_record_path=s.owner_path,
            owner_record_sha256=s.owner_hash,state_root=s.root,feeder_root=s.feeder,dependencies=s.deps)
    s.run=run
    return s


def load(s, now=X.AT):
    return P._load_policy(s.policy_path,s.owner_path,s.owner_hash,s.root,s.feeder,now)


@pytest.mark.parametrize('field,value', [
    ('max_admissions_24h',3),('max_admissions_24h',True),('max_admissions_24h',0),
    ('max_order_commitment_usd','5.01'),('max_total_commitment_usd','10.01'),
    ('max_feeder_age_s',1801),('max_hermes_assessment_age_s',86401),
    ('max_realized_pnl_loss_usd','5.01'),('max_position_pnl_drawdown_usd','7.51'),
    ('max_cumulative_loss_usd','10.01'),('experimental_margin_usd','-0.01'),
    ('max_order_commitment_usd','NaN'),('experimental_margin_usd','Infinity'),
    ('max_order_commitment_usd','5e0'),('max_order_commitment_usd',None),
    ('side','SELL'),('order_type','FAK'),('strategy_version_id',''),
])
def test_policy_requires_owner_record_and_bounds(setup,field,value):
    s=setup
    assert load(s)[0]['experimental_margin_usd']=='0'
    s.policy[field]=value
    s.write()
    result=s.run()
    assert result['status']=='REFUSED' and s.harness.secret_requests==0
    assert s.harness.venue.posts==[]


@pytest.mark.parametrize('change,code', [
    ('digest','PILOT_OWNER_RECORD_DIGEST_MISMATCH'),('unknown','PILOT_OWNER_RECORD_INVALID'),
    ('prefix','PILOT_OWNER_RECORD_SCOPE_MISMATCH'),('wallet','PILOT_OWNER_RECORD_SCOPE_MISMATCH'),
    ('expired','PILOT_OWNER_RECORD_WINDOW_INVALID'),('newline','PILOT_OWNER_RECORD_INVALID'),
    ('missing','PILOT_INPUT_INVALID'),
])
def test_owner_record_serialization(setup,change,code):
    s=setup
    if change=='digest': s.owner_hash='0'*64
    elif change=='missing': s.owner_path.unlink()
    else:
        if change=='unknown': s.owner['extra']=None
        if change=='prefix': s.owner['policy_sha256']=s.owner['policy_sha256'][:12]
        if change=='wallet': s.owner['public_wallet']=L.SIGNER
        if change=='expired': s.owner['valid_until_utc']=utc(X.AT-1*P.NS)
        raw=P._canonical(s.owner)+(b'\n' if change=='newline' else b'')
        s.owner_path.write_bytes(raw);s.owner_hash=P._digest(raw)
    assert s.run()['code']==code
    assert s.harness.secret_requests==0


@pytest.mark.parametrize('raw', [b'{}',b'null',b'[]',b'\xff',b'{',b'{"x":1,"x":2}',b'{"x":NaN}'])
def test_malformed_no_echo(setup,raw):
    setup.policy_path.write_bytes(raw)
    value=setup.run()
    assert value['status']=='REFUSED' and setup.harness.secret_requests==0
    assert L.SECRET not in json.dumps(value)


def evaluations(total='0',proposed='5',loss='0'):
    return SimpleNamespace(total_commitment=Decimal(total),observed_realized_pnl_loss=Decimal(loss),
        observed_position_pnl_drawdown=Decimal(loss),observed_cumulative_canary_loss=Decimal(loss)), \
        SimpleNamespace(proposed_worst_case_commitment=Decimal(proposed))


def guard_for(s,monkeypatch,**changes):
    monkeypatch.setattr(P.native,'verify_permit_authority',lambda *a,**kw:None)
    permit,intent=L.make_permit(s.world)
    intent=X.intent(s.world,requested_shares='8',**changes) if changes else intent
    policy,digest=load(s)
    return P._guard(policy,digest,lambda now:load(s,now),s.deps,s.candidate,permit,intent,X.AT,lambda:False)


def test_pilot_caps_counted_in_lock(setup,monkeypatch):
    s=setup
    guard=guard_for(s,monkeypatch)
    evaluation,risk=evaluations()
    guard({'episodes':[]},evaluation,risk)
    for count in (2,3):
        with pytest.raises(GatewayError,match='ADMISSIONS'):
            guard({'episodes':[{'admission':{'admitted_time_ns':X.AT}}]*count},evaluation,risk)
    for total,proposed,loss in [('5.01','5','0'),('0','5.01','0'),('0','5','5.01')]:
        with pytest.raises(GatewayError):guard({'episodes':[]},*evaluations(total,proposed,loss))
    with P._run_lock(s.root):
        result=s.run()
    assert result['code']=='PILOT_RUN_BUSY' and s.harness.secret_requests==0
    assert not s.harness.orchestrator().store_path.exists()


def test_market_binding_rejects_unrelated_market(setup,monkeypatch):
    guard=guard_for(setup,monkeypatch,token_id=X.OTHER_TOKEN)
    with pytest.raises(GatewayError,match='MARKET_BINDING'):
        guard({'episodes':[]},*evaluations())


def test_latest_authority_revalidation(setup,monkeypatch):
    guard=guard_for(setup,monkeypatch)
    def refused(*a,**kw):raise GatewayError('PERMIT_NOT_CURRENT')
    monkeypatch.setattr(P.native,'verify_permit_authority',refused)
    with pytest.raises(GatewayError,match='PERMIT_NOT_CURRENT'):guard({'episodes':[]},*evaluations())


@pytest.mark.parametrize('boundary', ['event','feeder','hermes','future'])
def test_latest_deadlines_after_authentication(setup,monkeypatch,boundary):
    s=setup
    guard=guard_for(s,monkeypatch)
    if boundary=='event':s.harness.now=s.candidate['start_ns']
    if boundary=='feeder':s.harness.now=X.AT+1801*P.NS
    if boundary=='hermes':
        s.policy['max_hermes_assessment_age_s']=1;s.write();guard=guard_for(s,monkeypatch)
        s.harness.now=X.AT+2*P.NS
    if boundary=='future':s.candidate['received_ns']=(X.AT+100*P.NS,)
    with pytest.raises(GatewayError):guard({'episodes':[]},*evaluations())


@pytest.mark.parametrize('boundary',['event','owner','policy','feeder','hermes'])
def test_final_file_io_cannot_outlive_deadline(setup,monkeypatch,boundary):
    s=setup
    guard=guard_for(s,monkeypatch)
    policy,digest=load(s)
    if boundary=='owner':policy['_owner_window']=(X.AT-1,X.AT+P.NS)
    if boundary=='policy':policy['valid_until_utc']=utc(X.AT+P.NS)
    if boundary=='hermes':policy['max_hermes_assessment_age_s']=1
    calls=[]
    def reload(now):
        calls.append(now)
        if len(calls)==2:
            s.harness.now=(s.candidate['start_ns'] if boundary=='event' else
                           X.AT+1801*P.NS if boundary=='feeder' else X.AT+2*P.NS)
        return policy,digest
    guard=P._guard(policy,digest,reload,s.deps,s.candidate,None,
        X.intent(s.world,requested_shares='8'),X.AT,lambda:False)
    with pytest.raises(GatewayError):guard({'episodes':[]},*evaluations())
    assert len(calls)==2


def test_exact_freshness_boundaries(setup):
    s=setup
    candidate=dict(s.candidate,received_ns=(X.AT-1800*P.NS,),start_ns=X.AT+1)
    P._fresh(candidate,s.policy,X.AT,X.AT-86400*P.NS)
    with pytest.raises(GatewayError,match='EVENT_STARTED'):P._fresh(candidate,s.policy,X.AT+1,X.AT)


def test_admission_economics_fok_only(setup):
    s=setup
    snap=X.snap(gamma=X.gamma_doc(orderMinSize=5,feesEnabled=False,secondsDelay=0),
                clob=X.book_doc(bids=[('0.39','100')],asks=[('0.40','100')]))
    stress,intent,assessment=P._economics(s.candidate,snap,s.world.version,s.policy,X.AT)
    assert stress==Decimal('1.1875') and Decimal(intent.price_limit)==Decimal('0.40') and Decimal(intent.requested_shares)==Decimal('12.5')
    assert (intent.side,intent.execution_style,intent.order_type,intent.post_only,intent.gtd_expiration_unix_s)==('BUY','AGGRESSIVE_TAKER','FOK',False,None)
    for price in ('0.55','0.52'):
        with pytest.raises(GatewayError,match='MINIMUM_EXCEEDS_CAP'):
            P._economics(s.candidate,X.snap(gamma=X.gamma_doc(orderMinSize=5,feesEnabled=False,secondsDelay=0),
                clob=X.book_doc(asks=[(price,'100')])),s.world.version,s.policy,X.AT)
    for gamma,book in [(X.gamma_doc(orderMinSize=6,feesEnabled=False,secondsDelay=0),X.book_doc(bids=[('0.39','100')],asks=[('0.40','100')])),
                       (X.gamma_doc(orderMinSize=5,feesEnabled=False,secondsDelay=1),X.book_doc(bids=[('0.39','100')],asks=[('0.40','100')])),
                       (X.gamma_doc(orderMinSize=5,feesEnabled=False,secondsDelay=0),X.book_doc(bids=[('0.39','100')],asks=[('0.40','1')]))]:
        with pytest.raises(GatewayError):P._economics(s.candidate,X.snap(gamma=gamma,clob=book),s.world.version,s.policy,X.AT)


def make_feeder(root):
    op=root/'op-000001';op.mkdir()
    raw_sources=[(P.DISCOVERY_URL,[F.market()]),(P.ESPN+'summary?event=401909877',F.summary())]
    started=dict(kind='CYCLE',ordinal=1)
    (op/'started.json').write_bytes(P._canonical(started))
    receipts=[]
    for i,(url,data) in enumerate(raw_sources,1):
        raw=P._canonical(data);name=f'source-{i:02d}.json';(op/name).write_bytes(raw)
        receipt=dict(url=url,state='AVAILABLE',raw_file=name,sha256=P._digest(raw),started_ns=F.NOW-1,received_ns=F.NOW,http_date='Mon, 26 Oct 2026 18:00:00 GMT')
        receipts.append(receipt);(op/f'receipt-{i:02d}.json').write_bytes(P._canonical(receipt))
    terminal=dict(status='COMPLETED',result={'status':'PASS','cutoff_ns':F.NOW,'forecasts':[{'p':'1'}]},receipts=receipts,
        inputs_sha256={p.name:P._digest(p.read_bytes()) for p in op.iterdir()})
    (op/'terminal.json').write_bytes(P._canonical(terminal))
    return op


def test_feeder_intake_verified(setup):
    s=setup;op=make_feeder(s.feeder)
    candidates=P._feeder_candidates(s.feeder,s.policy,F.NOW)
    assert len(candidates)==2
    assert {c['probability'] for c in candidates}=={Decimal('.167'),Decimal('.833')}
    assert P._feeder_candidates(s.feeder,s.policy,F.NOW+1801*P.NS)==[]
    assert P._feeder_candidates(s.feeder,s.policy,F.START)==[]
    (op/'source-02.json').write_bytes(b'{}')
    with pytest.raises(GatewayError):P._feeder_candidates(s.feeder,s.policy,F.NOW)


@pytest.mark.parametrize('http_date',[None,'bad','Mon, 26 Oct 2026 17:54:59 GMT','Mon, 26 Oct 2026 18:00:03 GMT'])
def test_feeder_http_evidence_fails_closed(setup,http_date):
    op=make_feeder(setup.feeder)
    terminal=json.loads((op/'terminal.json').read_bytes())
    terminal['receipts'][1]['http_date']=http_date
    path=op/'receipt-02.json';path.write_bytes(P._canonical(terminal['receipts'][1]))
    terminal['inputs_sha256'][path.name]=P._digest(path.read_bytes())
    (op/'terminal.json').write_bytes(P._canonical(terminal))
    with pytest.raises(Exception):P._feeder_candidates(setup.feeder,setup.policy,F.NOW)


@pytest.mark.parametrize('mode',['latest','conflict','duplicate'])
def test_feeder_latest_and_identity_conflicts(setup,mode):
    first=make_feeder(setup.feeder)
    second=setup.feeder/'op-000002';shutil.copytree(first,second)
    started=json.loads((second/'started.json').read_bytes());started['ordinal']=2
    (second/'started.json').write_bytes(P._canonical(started))
    terminal=json.loads((second/'terminal.json').read_bytes())
    if mode=='conflict':
        raw=json.loads((second/'source-01.json').read_bytes())
        raw[0]['clobTokenIds']='["333","444"]'
        path=second/'source-01.json';path.write_bytes(P._canonical(raw))
        terminal['receipts'][0]['sha256']=P._digest(path.read_bytes())
    else:
        raw=json.loads((second/'source-02.json').read_bytes())
        raw['predictor']['homeTeam']['gameProjection']='90'
        raw['predictor']['awayTeam']['gameProjection']='10'
        path=second/'source-02.json';path.write_bytes(P._canonical(raw))
        terminal['receipts'][1]['sha256']=P._digest(path.read_bytes())
    if mode=='duplicate':terminal['receipts'].append(dict(terminal['receipts'][1]))
    for i,receipt in enumerate(terminal['receipts'],1):
        (second/f'receipt-{i:02d}.json').write_bytes(P._canonical(receipt))
    terminal['inputs_sha256']={p.name:P._digest(p.read_bytes()) for p in second.iterdir() if p.name!='terminal.json'}
    (second/'terminal.json').write_bytes(P._canonical(terminal))
    if mode=='latest':
        values=P._feeder_candidates(setup.feeder,setup.policy,F.NOW)
        assert {c['probability'] for c in values}=={Decimal('.1'),Decimal('.9')}
    else:
        with pytest.raises(GatewayError):P._feeder_candidates(setup.feeder,setup.policy,F.NOW)


def prepare_run(s,monkeypatch):
    s.harness.gamma=X.gamma_doc(orderMinSize=5,feesEnabled=False,secondsDelay=0)
    s.harness.book=X.book_doc(bids=[('0.39','100')],asks=[('0.40','100')])
    monkeypatch.setattr(P,'_feeder_candidates',lambda *a:[s.candidate])


def test_kill_switch_blocks_new_exposure_only(setup,monkeypatch):
    s=setup;prepare_run(s,monkeypatch)
    flag=s.root/'PILOT_KILL';flag.touch()
    original=P.native.LiveOrchestrator.reconcile
    calls=[]
    def reconcile(self):
        calls.append('reconcile');flag.unlink();return original(self)
    monkeypatch.setattr(P.native.LiveOrchestrator,'reconcile',reconcile)
    result=s.run()
    assert result['status']=='REFUSED' and calls==['reconcile'] and s.harness.secret_requests==1
    assert s.harness.venue.posts==[]


def test_kill_raised_after_prepare(setup,monkeypatch):
    from src.execution_gateway.gate_c import LiveOrchMutationBoundary
    s=setup;prepare_run(s,monkeypatch)
    original=LiveOrchMutationBoundary.prepare
    def prepare(self,*a,**kw):
        result=original(self,*a,**kw)
        (s.root/'PILOT_KILL').touch()
        return result
    monkeypatch.setattr(LiveOrchMutationBoundary,'prepare',prepare)
    result=s.run()
    assert result['status']=='REFUSED' and result['create_transmits']==0
    assert result['native_result']['code']=='PILOT_GUARD_REFUSED:KILL'
    assert s.harness.venue.posts==[]


@pytest.mark.parametrize('change',['pause','head','hermes','revoke'])
def test_real_late_native_authority_change(setup,monkeypatch,change):
    from src.execution_gateway.gate_c import LiveOrchMutationBoundary
    s=setup;prepare_run(s,monkeypatch)
    original=LiveOrchMutationBoundary.prepare
    def prepare(self,*a,**kw):
        result=original(self,*a,**kw)
        if change=='pause':s.world.append(X._pause(s.world.version,t=X.AT+1))
        elif change=='head':s.world.append(X._pause(s.world.other_version,t=X.AT+1))
        elif change=='revoke':s.world.append(X.build_portfolio_policy_receipt(action='REVOKE',
            policy_id=s.world.policy.policy_id,previous_active_policy_id=s.world.policy.policy_id,
            human_authorization_ref='human:synthetic-revoke',created_time_ns=X.AT+1))
        else:s.world.assess(t=X.AT+1)
        return result
    monkeypatch.setattr(LiveOrchMutationBoundary,'prepare',prepare)
    value=s.run()
    assert value['status']=='REFUSED' and value['native_result']['code']=='PERMIT_NOT_CURRENT'
    assert value['create_transmits']==0 and s.harness.venue.posts==[]


@pytest.mark.parametrize('tie',['score','start','token'])
@pytest.mark.parametrize('reverse',[False,True])
def test_deterministic_selection_and_no_fallback(setup,monkeypatch,tie,reverse):
    s=setup;prepare_run(s,monkeypatch)
    a=dict(s.candidate,stress=Decimal('2'),token_id=X.TOKEN)
    b=dict(s.candidate,stress=Decimal('1') if tie=='score' else Decimal('2'),token_id=X.OTHER_TOKEN,
           start_ns=a['start_ns']+P.NS if tie=='start' else a['start_ns'])
    candidates=[b,a] if reverse else [a,b]
    expected=a if tie in ('score','start') else min(candidates,key=lambda x:x['token_id'])
    monkeypatch.setattr(P,'_feeder_candidates',lambda *a:candidates)
    monkeypatch.setattr(P,'_economics',lambda c,*a:(c['stress'],X.intent(s.world,requested_shares='8',token_id=c['token_id']),None))
    attempts=[]
    def refused(**kw):
        attempts.append(kw['execution_intent'].token_id)
        return SimpleNamespace(status='PERMIT_REJECTED')
    monkeypatch.setattr(P,'evaluate_exploratory_gate_c',refused)
    value=s.run()
    assert value['code']=='PILOT_PERMIT_REFUSED' and attempts==[expected['token_id']]
    assert s.harness.venue.posts==[]


def test_custody_provider_allowlist(setup):
    s=setup
    s.deps.secret_provider_factory=lambda:None
    assert s.run()['code']=='PILOT_CUSTODY_UNAVAILABLE' and s.harness.secret_requests==0


@pytest.mark.parametrize('crash',[False,True])
def test_restart_never_second_transmit(setup,monkeypatch,crash):
    s=setup;prepare_run(s,monkeypatch)
    original=P.native.LiveOrchestrator.canary
    calls=[]
    def capture(self,permit,intent):
        calls.append((self,permit,intent))
        return original(self,permit,intent)
    monkeypatch.setattr(P.native.LiveOrchestrator,'canary',capture)
    if crash:
        record=P.native.ProtectedExecutionGateway.record_live_orch_event
        def write_then_crash(self,event_type,*a,**kw):
            result=record(self,event_type,*a,**kw)
            if event_type=='LIVE_ORCH_ADMITTED':raise RuntimeError('synthetic crash')
            return result
        monkeypatch.setattr(P.native.ProtectedExecutionGateway,'record_live_orch_event',write_then_crash)
    first=s.run()
    assert len(calls)==1
    assert len(s.harness.venue.posts)==(0 if crash else 1)
    replay=original(*calls[0])
    assert replay.code=='PERMIT_ALREADY_CONSUMED' and replay.create_transmits==0
    assert len(s.harness.venue.posts)==(0 if crash else 1)


def test_terminal_truthful_no_edge_claim(setup,monkeypatch):
    s=setup
    monkeypatch.setattr(P.native.LiveOrchestrator,'reconcile',lambda *a:(_ for _ in ()).throw(ValueError(L.SECRET)))
    result=s.run()
    assert result['status']=='REFUSED' and result['realized_profit'] is None
    assert result['unconditional_order_ev']=='UNKNOWN' and L.SECRET not in json.dumps(result)
    records=list((s.root/'terminals').glob('*.json'))
    assert len(records)==1 and json.loads(records[0].read_bytes())==result


def test_terminal_native_refusal_and_uppercase_no_echo(setup,capsys):
    result=P._terminal(setup.root,'REFUSED','PILOT_NATIVE_REFUSED',
        P.native.LiveOrchResult('canary','BLOCKED','UPPERCASE_UNTRUSTED_SENTINEL'),Decimal('1'))
    assert result['native_result']=={'status':'BLOCKED','code':'NATIVE_RESULT_INVALID'}
    assert result['scenario_claim']=='POSITIVE_AFTER_COST_FULL_FILL_STRESS_SCENARIO'
    assert 'UPPERCASE_UNTRUSTED_SENTINEL' not in json.dumps(result)
    assert P.main(['UPPERCASE_UNTRUSTED_SENTINEL'])==2
    assert 'UPPERCASE_UNTRUSTED_SENTINEL' not in capsys.readouterr().out


def test_pilot_authority_boundary():
    root=Path(__file__).resolve().parents[2]
    source=(root/'src/live_pilot/pilot.py').read_text()
    assert 'LIVE TRADING STATUS: DISABLED' in (root/'docs/live_trading_authorization.md').read_text()
    assert 'from tools' not in source and 'import tools' not in source
    assert 'os.environ' not in source and 'getenv' not in source
    assert 'while True' not in source and 'time.sleep' not in source
