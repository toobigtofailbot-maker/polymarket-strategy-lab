"""Two-leg synthetic arithmetic never establishes atomic execution."""
from copy import deepcopy
import pytest
from src.live_pilot import structural as S


def record(**changes):
    r = dict(condition_id='0x'+'a'*64, rule_sha256='b'*64, token_ids=['1','2'],
        outcome_indices=[0,1], payouts=['1','1'], asks=['0.4','0.5'], shares='10',
        fees_usd=['0.1','0.1'], reserve_usd='0.1', margin_usd='0.1', source_ns=10,
        evaluated_ns=11, settlement_kind='BINARY_CTF_EXACTLY_ONE_WINNER',
        neg_risk=False, combo=False, raw_sha256='c'*64)
    r.update(changes)
    return r


def test_complement_payoff_identity_and_fee_cost():
    r = S.verify_complement(record(), now_ns=12)
    assert r['status'] == 'STRUCTURAL_CANDIDATE' and r['theoretical_margin_usd'] == '0.7'
    assert not r['execution_eligible'] and r['evidence_class'] == 'RESEARCH_ONLY'
    assert set(r)=={'status','reason','theoretical_margin_usd','execution_eligible','evidence_class','record_sha256'}


@pytest.mark.parametrize('changes', [dict(neg_risk=True),dict(combo=True),dict(token_ids=['1','1']),
    dict(settlement_kind='UNKNOWN'),dict(payouts=['1','0']),dict(asks=['NaN','0.5']),
    dict(source_ns=13),dict(fees_usd=['-1','0']),dict(outcome_indices=[False,True]),
    dict(shares=None),dict(raw_sha256=''),dict(extra='do-not-echo')])
def test_invalid_complements(changes):
    r = S.verify_complement(record(**changes), now_ns=12)
    assert r['status'] == 'NO_TRADE' and not r['execution_eligible'] and 'do-not-echo' not in str(r)


def test_partial_leg_exposure_refuses_execution():
    for outcome in ('FIRST_FILLED_SECOND_REJECTED','PARTIAL','CANCEL_AMBIGUOUS','RESTART'):
        # No advertised execution flag or leg outcome can mint the missing native route.
        r = record(); r['all_leg_atomic'] = True; r['leg_outcome'] = outcome
        assert not S.verify_complement(r,now_ns=12)['execution_eligible']
    assert S.verify_complement(record(),now_ns=30*10**9+10)['status'] == 'NO_TRADE'
    r = record(); del r['raw_sha256']
    assert S.verify_complement(r,now_ns=12)['status'] == 'NO_TRADE'


def test_raw_capture_without_settlement_theorem_abstains(tmp_path):
    from tests.tools.alpha.test_near_term_market_screener import execute,market
    root,_,_,_=execute(tmp_path,[[market()]])
    r=S.assess_capture(root)
    assert r['reason']=='SETTLEMENT_UNVERIFIED' and r['source_manifest_sha256'] and not r['execution_eligible']
    assert set(r)=={'status','reason','execution_eligible','source_manifest_sha256'}
    assert S.assess_capture(tmp_path/'missing')['reason']=='STRUCTURAL_SOURCE_UNVERIFIED'


def test_unproven_atomic_leg_execution_never_trades():
    test_partial_leg_exposure_refuses_execution()
    r = S.verify_complement(record(), now_ns=12)
    assert r['evidence_class'] == 'RESEARCH_ONLY' and not r['execution_eligible']
