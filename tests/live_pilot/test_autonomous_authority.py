"""Exact package certificate and native owner-account denial tests."""
from dataclasses import replace
from pathlib import Path
import subprocess

from src.live_pilot import autonomous_cycle as A
from tests.live_pilot.test_autonomous_cycle import harness, policy, save
from tests.tools.alpha.test_near_term_market_screener import NOW


def test_protected_activation_chain():
    root = Path(__file__).resolve().parents[2]
    package = root/'docs/wp_specs/S10-AUTONOMOUS-EDGE-TO-LIVE-01'
    command = ['python', '-B', str(root/'tools/wp/wp_readiness_gate.py'), '--wp', str(package/'wp_prompt.txt'),
        '--spec', str(package/'wp_spec.json'), '--certificate', str(package/'draftability_certificate.json'),
        '--repo-root', str(root), '--format', 'json']
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    assert result.returncode == 0 and '"certificate_hash_bound":true' in result.stdout


def test_secure_account_access_and_wallet_binding(tmp_path, monkeypatch):
    s = harness(tmp_path, monkeypatch)
    s.policy['public_wallet'] = '0x'+'f'*40
    save(s.path, s.policy)
    result = A.run(**s.args)
    assert result['code'] == 'OWNER_SETUP_REQUIRED' and not s.calls
    assert s.native.harness.secret_requests == 0 and not s.native.harness.venue.posts


def test_first_live_canary_activation_fails_closed(tmp_path):
    p = policy(tmp_path, mode='LIVE')
    path = save(tmp_path/'auto.json', p)
    deps = A.AutonomousDependencies(native=replace(A.native.LiveOrchDependencies(), clock_ns=lambda: NOW))
    result = A.run(policy_path=path, dependencies=deps)
    assert result['code'] == 'OWNER_SETUP_REQUIRED' and not result['live_active']
    assert not (tmp_path/'state').exists()
    source = Path(A.__file__).read_text()
    assert '.canary(' not in source and '.exit_sell(' not in source and '.cancel(' not in source


def test_consolidated_owner_handoff():
    report = A.activation_report(software_verified=True)
    assert report['blockers'] == ['CALIBRATION_NOT_VERIFIED', 'OWNER_SETUP_REQUIRED', 'CANARY_APPROVAL_MISSING']
    assert 'private' not in str(report) and report['orders'] == 0


def test_native_reuse_no_bypass():
    from src.live_pilot import edge_qualifier as E
    from src.execution_gateway import live_orch as L
    assert A.native is L and A.pilot.native is L
    assert not E.PRODUCTION_METHODS and not A.CALIBRATED_METHODS
    assert '.canary(' not in Path(A.__file__).read_text()


def test_native_custody_and_account_fail_closed(tmp_path, monkeypatch):
    s = harness(tmp_path, monkeypatch)
    s.native.owner['dedicated_wallet'] = False
    s.native.write_owner()
    s.args['owner_record_sha256'] = s.native.owner_hash
    result = A.run(**s.args)
    assert result['status'] == 'REFUSED' and not s.calls and not s.native.harness.venue.posts


def test_first_canary_unattended_denied(tmp_path, monkeypatch):
    from src.execution_gateway import live_orch as L
    from tests.live_pilot import test_hunter_cycle as H
    s = H.build(tmp_path, monkeypatch)
    ex = H.X.execution(s.world)
    decision = H.X.evaluate(s.world,ex)
    from src.exploratory_gate_c import build_exploratory_gate_c_permit
    permit = build_exploratory_gate_c_permit(decision, execution_intent=ex.intent)
    orch = L.LiveOrchestrator(s.harness.config(), envelope=L.LiveOrchCapitalEnvelope.autonomous_edge_01(),
                             dependencies=s.harness.deps())
    result = orch.canary(permit,ex.intent)
    assert result.status == 'BLOCKED' and result.create_transmits == 0 and not s.harness.venue.posts


def test_default_v1_marked_strategy_refuses_under_wallet_lock(tmp_path,monkeypatch):
    from copy import deepcopy
    import pytest
    from src.execution_gateway.gateway import GatewayError
    from src.execution_gateway.gate_b import WalletSessionLock
    from src.live_pilot import edge_qualifier as E
    from tests.execution_gateway import test_live_orch as T
    spec=deepcopy(T.X.STRATEGY_SPEC)
    spec['execution_rule']['autonomous_edge']=dict(method_id='NBA_ESPN_V1',method_sha256='a'*64,corpus_proof_sha256='b'*64)
    monkeypatch.setattr(T.X,'STRATEGY_SPEC',spec)
    world=T.X.make_world(tmp_path);h=T.Harness(tmp_path,world)
    permit,intent=T.make_permit(world)
    original=E.require_native_edge;seen=[]
    def locked(version,current,**kwargs):
        with pytest.raises(GatewayError):
            WalletSessionLock(h.orchestrator().store_path.parent,T.WALLET).acquire()
        seen.append(True)
        return original(version,current,**kwargs)
    monkeypatch.setattr(E,'require_native_edge',locked)
    deps=h.deps();deps.admission_guard=lambda *a:None
    result=T.L.LiveOrchestrator(h.config(),dependencies=deps).canary(permit,intent)
    assert seen and result.code=='CALIBRATION_NOT_VERIFIED' and result.create_transmits==0 and not h.venue.posts


def test_invented_minimal_canary_receipt_is_refused(tmp_path):
    import pytest
    from src.execution_gateway.gateway import GatewayError
    from src.live_pilot import hunter_cycle as H
    raw=H._canonical(dict(schema_id='polymarket-live-canary-receipt',evidence_class='NATIVE_PRODUCTION',
        status='CANARY_COMPLETE',calls={'order':1},live_orch={'episode_id':'invented'}))
    (tmp_path/'first-canary.json').write_bytes(raw)
    with pytest.raises(GatewayError):
        H.verify_first_canary({'state_root':str(tmp_path),'first_canary_receipt_sha256':H._digest(raw)}, {'episodes':[]})


def test_no_secret_echo_and_source_authority(tmp_path):
    from src.live_pilot import edge_qualifier as E
    r = E.qualify_candidate({'unexpected': 'untrusted-do-not-echo'})
    assert not r['production_eligible'] and 'untrusted-do-not-echo' not in str(r)
    p = save(tmp_path/'bad.json',dict(policy(tmp_path), max_provider_cost_usd_total='NaN'))
    r = A.run(policy_path=p)
    assert r['code'] == 'POLICY_INVALID' and 'NaN' not in str(r)


def test_truthful_owner_handoff_and_activation_report():
    from src.live_pilot import calibration as C, edge_qualifier as E
    r = A.activation_report(software_verified=True)
    assert r['disposition'] == 'READY_BUT_ACTIVATION_BLOCKED'
    assert not r['live_active'] and not r['account_connected'] and r['orders'] == 0
    assert not C.PRODUCTION_CORPORA and not E.PRODUCTION_METHODS


def test_owner_account_host_custody_denials(tmp_path, monkeypatch):
    test_native_custody_and_account_fail_closed(tmp_path, monkeypatch)
    assert A.evidence_activation_report()['eligible_host'] == 'NOT_OBSERVED'


def test_first_canary_remains_attended(tmp_path, monkeypatch):
    test_first_canary_unattended_denied(tmp_path, monkeypatch)
    assert A.evidence_activation_report()['first_canary'] == 'NOT_OBSERVED'


def test_truthful_activation_checkpoint(tmp_path, monkeypatch):
    from tests.tools.alpha.test_edge_evidence_capture import execute
    root, evidence, _ = execute(tmp_path)
    monkeypatch.setattr(A, 'account', lambda *a: (_ for _ in ()).throw(AssertionError('unexpected account read')))
    report = A.evidence_activation_report(root)
    assert report['evidence'] == evidence and report['software'] == 'NOT_VERIFIED'
    assert report['method'] == 'NOT_QUALIFIED' and report['unattended'] == 'DISABLED'
    assert all(report[k] == 'NOT_OBSERVED' for k in ('account', 'funding', 'custody',
        'eligible_host', 'provider_consent', 'first_canary'))
    assert set(report) == {'software', 'evidence', 'method', 'account', 'funding', 'custody',
        'eligible_host', 'provider_consent', 'first_canary', 'unattended', 'live_active'}
    assert report['live_active'] is False
