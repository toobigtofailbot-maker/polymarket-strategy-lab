"""Synthetic mathematical cases; none is an authenticated production corpus."""
from copy import deepcopy
from decimal import Decimal, localcontext

import pytest

from src.execution_gateway.gateway import GatewayError
from src.live_pilot import calibration as C


def rows(n=200):
    return [dict(event_group=f'event:{i}', source_cutoff_ns=1000+2*i, resolved_ns=1001+2*i,
        method_id='NBA_ESPN_V1', method_sha256='a'*64, rule_sha256='b'*64, horizon_s=3600,
        p_point='0.95', payout=0 if i < 40 else 1, raw_sha256=f'{i:064x}') for i in range(n)]


def evaluate(data=None, **changes):
    args = dict(p_point='0.95', method_id='NBA_ESPN_V1', method_sha256='a'*64,
        rule_sha256='b'*64, horizon_s=3600, decision_ns=10000, method_frozen_ns=1)
    args.update(changes)
    return C.historical_bound(rows() if data is None else data, **args)


def test_historical_causal_calibration_and_wilson():
    r = evaluate()
    assert r['status'] == 'DIAGNOSTIC_READY' and r['n_train'] == 140 and r['n_holdout'] == 60
    assert r['n_bucket'] == r['k'] == 60 and Decimal(r['lower']) < 1
    assert Decimal(r['model_brier']) <= Decimal(r['baseline_brier'])
    assert not r['production_eligible'] and r['evidence_class'] == 'TEST_ONLY'
    assert C.wilson_lower(0, 50) == 0 and C.wilson_lower(50, 50) == Decimal('0.948666')
    assert [C.bucket(p) for p in ('0', '0.099999', '0.1', '0.9', '1')] == [0, 0, 1, 9, 9]
    with localcontext() as ctx:
        ctx.prec = 5
        assert evaluate()['record_sha256'] == r['record_sha256']


@pytest.mark.parametrize('change', [
    {'source_cutoff_ns': 1001}, {'resolved_ns': 10000}, {'payout': True},
    {'p_point': 'NaN'}, {'p_point': 'Infinity'}, {'p_point': ''}, {'p_point': None},
    {'p_point': 0.95}, {'method_id': 'HERMES'}, {'raw_sha256': 'invalid'},
    {'horizon_s': 1}, {'extra': 'untrusted-value'},
])
def test_invalid_rows_never_echo_or_qualify(change):
    data = rows(); data[0].update(change)
    r = evaluate(data)
    assert r['reason'] == 'CALIBRATION_INVALID' and r['lower'] is None
    assert 'untrusted-value' not in str(r) and not r['production_eligible']


def test_group_leakage_split_and_freeze():
    data = rows(); data[1]['event_group'] = data[0]['event_group']
    assert evaluate(data)['reason'] == 'CALIBRATION_INVALID'
    data=rows()
    for r in data:
        r['horizon_s']=1
    data[0]['horizon_s']=True
    assert evaluate(data,horizon_s=1)['reason']=='CALIBRATION_INVALID'
    data = rows(); data[140]['resolved_ns'] = data[139]['resolved_ns']
    assert evaluate(data)['reason'] == 'CALIBRATION_INVALID'
    assert evaluate(method_frozen_ns=1300)['reason'] == 'CALIBRATION_INVALID'
    assert evaluate([])['reason'] == 'CALIBRATION_INSUFFICIENT'
    assert evaluate(rows(100))['n_bucket'] == 30
    assert evaluate(list(reversed(rows()))) == evaluate()
    data = rows(); del data[0]['event_group']
    assert evaluate(data)['reason'] == 'CALIBRATION_INVALID'


def test_source_cutoff_fee_expiry_and_no_live_claims():
    from tools.alpha.run_near_term_market_screener import FEE_EXPIRY
    assert FEE_EXPIRY == 1793750400 * 10**9
    assert not C.PRODUCTION_CORPORA and not evaluate()['production_eligible']
    assert evaluate(rows(), decision_ns=1100)['reason'] == 'CALIBRATION_INVALID'
    for k,n in ((-1,50),(51,50),(1,0),(True,50)):
        with pytest.raises(GatewayError):
            C.wilson_lower(k,n)


def test_all_public_fields_and_digest_projection():
    from src.live_pilot import pilot
    r = evaluate()
    assert set(r) == {'status','reason','evidence_class','production_eligible','method_id',
        'method_sha256','rule_sha256','horizon_s','bucket','n_train','n_holdout','n_bucket','k',
        'lower','model_brier','baseline_brier','training_prevalence','training_end_ns',
        'holdout_start_ns','holdout_end_ns','dataset_sha256','raw_sha256','record_sha256'}
    projection = {k:v for k,v in r.items() if k != 'record_sha256'}
    assert r['record_sha256'] == pilot._digest(pilot._canonical(projection))
    assert pilot._canonical(projection) == pilot._canonical(dict(reversed(list(projection.items()))))
    other = deepcopy(projection); other['k'] += 1
    assert pilot._digest(pilot._canonical(other)) != r['record_sha256']
    other = deepcopy(projection); other['raw_sha256'].reverse()
    assert pilot._digest(pilot._canonical(other)) != r['record_sha256']


def test_causal_holdout_and_group_deduplication():
    data = rows()
    assert evaluate(data)['n_bucket'] == 60
    data[140]['source_cutoff_ns'] = data[139]['resolved_ns']
    r = evaluate(data)
    assert r['reason'] == 'CALIBRATION_INVALID' and r['lower'] is None
    assert not r['production_eligible']
    data = rows(); data[140]['event_group'] = data[0]['event_group']
    assert evaluate(data)['reason'] == 'CALIBRATION_INVALID'


def test_verified_empirical_bound_and_fail_closed():
    from src.live_pilot import edge_qualifier as E
    from tests.live_pilot.test_autonomous_cycle import source_record
    r = evaluate()
    assert r['n_bucket'] >= 50 and Decimal(r['lower']) == C.wilson_lower(r['k'], r['n_bucket'])
    assert r['evidence_class'] == 'TEST_ONLY' and not C.PRODUCTION_CORPORA
    assert not E.qualify_candidate(source_record(), r)['production_eligible']
