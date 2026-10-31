"""Independent arithmetic and native economic refusals, synthetic inputs only."""
from decimal import Decimal
from types import SimpleNamespace
from dataclasses import replace
import json
import pytest
from src.execution_gateway.gateway import GatewayError
from src.execution_gateway import live_orch as L
from src.live_pilot import edge_qualifier as E
from tests.live_pilot.test_autonomous_cycle import source_record
from tests.live_pilot.test_calibration import evaluate


def test_statistical_forecast_verified_or_abstained():
    r = E.qualify_candidate(source_record(), evaluate())
    assert r['status'] == 'NO_TRADE' and r['p_lower'] is None and not r['production_eligible']
    fake = dict(evaluate(), production_eligible=True, evidence_class='NATIVE_PRODUCTION')
    assert not E.qualify_candidate(source_record(),fake)['production_eligible']
    assert not E.PRODUCTION_METHODS


def test_owner_pilot_cap_and_minimum_fee_inclusive():
    from src.live_pilot.hunter_cycle import size_order
    assert L.LiveOrchCapitalEnvelope().validate()['single_order_worst_case_max_usd'] == 5
    assert L.LiveOrchCapitalEnvelope.hunter_pilot_02().validate()['single_order_worst_case_max_usd'] == 5
    e = L.LiveOrchCapitalEnvelope.autonomous_edge_01()
    assert e.validate()['single_order_worst_case_max_usd'] == 10
    with pytest.raises(GatewayError):
        replace(e,single_order_worst_case_max_usd='10.01').validate()
    args = dict(ask=Decimal('0.5'),depth=Decimal(100),rate=Decimal('0.05'),exponent=1,
                floor=Decimal(2),gamma_min=Decimal(5),book_min=Decimal(1),seconds_delay=0)
    with pytest.raises(GatewayError):
        size_order(**args, cap=Decimal(5))
    q,fee = size_order(**args, cap=Decimal(10))
    assert 5 <= q*Decimal('0.5') < q*Decimal('0.5')+fee <= 10


def closed(eid, cost, *, closes=None, side='BUY'):
    return dict(episode_id=eid, state='CLOSED_RECONCILED',
        binding=dict(side=side,closes_episode_id=closes),
        reconciliation=dict(trades=[dict(status='CONFIRMED',principal_usd=cost)],
                            fee_state='NOT_REQUIRED',actual_fee_usd=None))


def test_gains_never_reset_lifetime_losses_and_reserves_count_once():
    cp = {'episodes':[closed('loss','4'),closed('gain','1'),closed('sell','8',closes='gain',side='SELL')]}
    ev = SimpleNamespace(blocking_codes=(),total_commitment=Decimal(3))
    assert E.combined_loss(cp,ev,Decimal(3),activation_ledger_head='a'*64) == 10
    with pytest.raises(GatewayError,match='EDGE_COMBINED_LOSS_LIMIT'):
        E.combined_loss(cp,ev,Decimal('3.01'),activation_ledger_head='a'*64)
    cp['episodes'].append(cp['episodes'][0])
    with pytest.raises(GatewayError):
        E.combined_loss(cp,ev,Decimal(0),activation_ledger_head='a'*64)


def test_closed_v1_first_canary_loss_cannot_disappear():
    first=closed('first-canary','5');first['state']='TERMINAL_NO_POSITION'
    cp={'episodes':[first]}
    ev=SimpleNamespace(blocking_codes=(),total_commitment=Decimal(0))
    with pytest.raises(GatewayError,match='EDGE_COMBINED_LOSS_LIMIT'):
        E.combined_loss(cp,ev,Decimal(6),activation_ledger_head='a'*64)


def test_integration_admission_negative_matrix():
    for marker in (None,{},True,{'method_id':'NBA_ESPN_V1','method_sha256':'a'*64,'corpus_proof_sha256':'b'*64}):
        version = SimpleNamespace(strategy_spec_json=json.dumps({'execution_rule':{'autonomous_edge':marker}}))
        with pytest.raises(GatewayError):
            E.require_native_edge(version,None,required=True)
    with pytest.raises(GatewayError,match='EDGE_PROOF_REQUIRED'):
        E.require_native_edge(SimpleNamespace(strategy_spec_json='{"execution_rule":{}}'),None,required=True)


def test_evidence_activation_protected_gate():
    from pathlib import Path
    import subprocess
    import sys
    root = Path(__file__).resolve().parents[2]
    package = root/'docs/wp_specs/S10-EDGE-EVIDENCE-ACTIVATION-01'
    result = subprocess.run([sys.executable, '-B', str(root/'tools/wp/wp_readiness_gate.py'),
        '--wp', str(package/'wp_prompt.txt'), '--spec', str(package/'wp_spec.json'),
        '--certificate', str(package/'draftability_certificate.json'), '--repo-root', str(root),
        '--format', 'json'], capture_output=True, text=True, check=False)
    assert result.returncode == 0
    assert json.loads(result.stdout)['certificate_hash_bound'] is True


def test_native_paths_cannot_be_bypassed(tmp_path, monkeypatch):
    from tests.live_pilot.test_autonomous_authority import test_default_v1_marked_strategy_refuses_under_wallet_lock
    test_default_v1_marked_strategy_refuses_under_wallet_lock(tmp_path, monkeypatch)
    assert not E.PRODUCTION_METHODS


def test_admit_only_verified_after_cost_edge(tmp_path):
    from tests.tools.alpha.test_edge_evidence_capture import execute
    root, _, _ = execute(tmp_path)
    result = E.evidence_diagnosis(root)
    assert set(result) == {'status', 'reason', 'p_lower', 'production_eligible', 'evidence'}
    assert result['reason'] == 'CALIBRATION_NOT_VERIFIED'
    assert result['evidence']['status'] == 'REPLAY_VERIFIED'
    assert result['p_lower'] is None and result['production_eligible'] is False
    assert result['status'] == 'NO_TRADE' and not E.PRODUCTION_METHODS
    assert not E.qualify_candidate(source_record(), dict(production_eligible=True, p_lower='1'))['production_eligible']
    invalid = E.evidence_diagnosis(tmp_path/'missing')
    assert set(invalid) == set(result) and invalid['evidence']['status'] == 'REFUSED'


def test_profile_risk_pilot_and_legacy_canary_unchanged():
    test_owner_pilot_cap_and_minimum_fee_inclusive()
    test_gains_never_reset_lifetime_losses_and_reserves_count_once()
    test_closed_v1_first_canary_loss_cannot_disappear()
