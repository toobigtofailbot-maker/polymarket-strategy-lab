"""Seven WP requirement nodes; synthetic sources only, never market observations."""
from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal
import json
from pathlib import Path
import socket

import pytest

from tools.alpha import run_near_term_market_screener as N

NOW = 1793188800 * 10**9  # 2026-10-28T12:00:00Z


def test_all_horizons_is_explicit_bounded_and_cold_replayed(tmp_path):
    root,result,manifest,calls=execute(tmp_path,[[market(1,delta=86400)]],all_horizons=True)
    assert result['status']=='COMPLETED' and N.verify(root)['status']=='VERIFIED'
    assert len(calls)==3 and 'end_date_max' not in calls[0]
    assert manifest['coverage']['external_universe_completeness']=='UNPROVEN'
    assert manifest['markets'][0]['selection_state']=='SELECTED'
    _,_,legacy,_=execute(tmp_path,[[market(1,delta=86400)]])
    assert legacy['markets'][0]['selection_state']=='INELIGIBLE'
POSSIBLE = 'MECHANICALLY_POSSIBLE_WITH_BOUNDED_ASSUMPTIONS'
MINIMUM = 'MINIMUM_UNSATISFIABLE_WITHIN_FEE_INCLUSIVE_CAP'
UNKNOWN = 'INCONCLUSIVE_MECHANICS'


def text_time(ns):
    return datetime.fromtimestamp(ns / 10**9, timezone.utc).isoformat().replace('+00:00', 'Z')


def market(mid=1, category='Crypto', delta=60, **changes):
    return dict(id=str(mid), conditionId='0x' + format(mid, '064x'),
                clobTokenIds=json.dumps([str(mid * 2 + 100), str(mid * 2 + 101)]),
                positionIds=None, category=category, endDate=text_time(NOW + delta * 10**9),
                active=True, closed=False, acceptingOrders=True, enableOrderBook=True,
                negRisk=False, feesEnabled=True, feeSchedule={'rate': '0.07', 'exponent': 1,
                'takerOnly': True, 'rebateRate': '0'}, orderMinSize='1',
                orderPriceMinTickSize='0.01', secondsDelay=0, **changes)


def book(m, token, **changes):
    return dict(market=m['conditionId'], asset_id=token, timestamp=str(NOW // 10**6),
                hash='fixture', bids=[{'price': '0.49', 'size': '100'}],
                asks=[{'price': '0.50', 'size': '100'}], min_order_size='5',
                tick_size='0.01', neg_risk=False, last_trade_price='0.49', **changes)


def execute(tmp_path, pages, change_book=None, transport=None, **kwargs):
    calls = []
    by_token = {t: m for page in pages if isinstance(page, list) for m in page
                if isinstance(m, dict) for t in json.loads(m.get('clobTokenIds', '[]'))}

    def fake(url, timeout, maximum):
        calls.append(url)
        assert 0 < timeout <= 15 and maximum == 2 * 1024 * 1024
        if '/markets?' in url:
            i = int(url.split('offset=')[1]) // 100
            value = pages[i] if i < len(pages) else []
        else:
            token = url.split('token_id=')[1]
            value = book(by_token[token], token)
            if change_book:
                value = change_book(value)
        if isinstance(value, bytes):
            return 'HTTP_2XX', value
        return 'HTTP_2XX', json.dumps(value).encode()

    root = tmp_path / ('capture-' + str(len(list(tmp_path.iterdir()))))
    result = N.run(root, transport=transport or fake, clock_ns=kwargs.pop('clock_ns',lambda: NOW), **kwargs)
    manifest = json.loads((root / 'op-000001/manifest.json').read_bytes())
    return root, result, manifest, calls


def test_category_neutral_pagination_and_bounded_denominators(tmp_path):
    pages = [[market(i, ['Crypto', 'Sports', 'novel category'][i % 3]) for i in range(1, 101)],
             [market(101, 'Politics'), market(1, 'Sports')]]
    root, result, m, calls = execute(tmp_path, pages)
    assert result['status'] == 'COMPLETED'
    assert calls[:2] == [N.discovery_url(0,NOW), N.discovery_url(100,NOW)]
    assert all('tag' not in u and 'order=' not in u and 'active=' not in u for u in calls)
    assert m['coverage']['raw_rows'] == 102
    assert m['coverage']['unique_ids'] == 101
    assert m['coverage']['identical_duplicates'] == 1
    assert sum(c['market_count'] for c in m['categories']) == 101
    assert len(calls) == 22 and len(m['tokens']) == 20
    assert m['summary']['unacquired_market_count'] == 91
    assert N.verify(root)['status'] == 'VERIFIED'
    # A repeated full page at another offset is churn, not another 100 unique markets.
    _, _, repeated, repeated_calls = execute(tmp_path, [pages[0], pages[0]])
    assert repeated['coverage']['stop_reason'] == 'SORT_OR_PAGINATION_UNVERIFIED'
    assert repeated['coverage']['raw_rows'] == 200
    assert repeated['coverage']['identical_duplicates'] == 100
    assert repeated['summary']['assessment'] == 'EVIDENCE_INCOMPLETE'
    assert len([u for u in repeated_calls if '/markets?' in u]) == 2
    # Maximum finite traversal, no 21st page or automatic smaller-page retry.
    _, _, capped, capped_calls = execute(tmp_path, [[market(i + 100*p) for i in range(1, 101)] for p in range(20)])
    assert capped['coverage']['stop_reason'] == 'COVERAGE_TRUNCATED'
    assert capped['coverage']['raw_rows'] == 2000 and len(capped_calls) <= 40


@pytest.mark.parametrize('end,expected', [
    (text_time(NOW), 'EXPIRED'), (text_time(NOW+10**9), 'IN_WINDOW'),
    (text_time(NOW+7200*10**9), 'IN_WINDOW'), (text_time(NOW+7201*10**9), 'FUTURE_OUTSIDE'),
    (None, 'MISSING'), ('', 'MALFORMED'), ('2026-10-28', 'DATE_ONLY'),
    ('2026-10-28T13:00:00', 'TIMEZONE_MISSING'), ('not a date', 'MALFORMED'),
    (True, 'MALFORMED'), ('2026-10-28T14:00:00+01:00', 'IN_WINDOW'),
])
def test_two_hour_timestamp_filter_and_resolution_uncertainty(tmp_path, end, expected):
    mkt = market(); mkt['endDate'] = end
    _, _, m, _ = execute(tmp_path, [[mkt]])
    assert m['markets'][0]['time_state'] == expected
    assert m['summary']['resolution_within_120m_confirmed_count'] == 0
    assert m['summary']['external_universe_completeness'] == 'UNPROVEN'
    assert m['summary']['claim'] == 'RESEARCH_ONLY'


@pytest.mark.parametrize('payload', [b'[]', b'{}', b'null', b'[null]', b'[{', b'\xff',
    b'[{"id":"1","id":"2"}]', b'[NaN]', b'[Infinity]', b'[] '*800000,
    b'[{"metadata":1e1000000000}]',b'[{"question":"\\ud800"}]'],
    ids=['empty','object','null','null-row','truncated','utf8','duplicate-key','nan','infinity','oversize','exponent','surrogate'])
def test_fail_closed_transport_and_malformed_market_pages(tmp_path, payload):
    root, result, m, calls = execute(tmp_path, [payload])
    assert len(calls) == 1 and result['status'] == 'COMPLETED'
    if payload != b'[]':
        assert m['summary']['assessment'] == 'EVIDENCE_INCOMPLETE'
    assert N.verify(root)['status'] == 'VERIFIED'
    for status in ['HTTP_4XX', 'HTTP_5XX', 'REDIRECT_REFUSED', 'TRANSPORT_UNAVAILABLE']:
        root, _, m, calls = execute(tmp_path, [], transport=lambda *args: (status, None))
        assert m['coverage']['unavailable'] == 1
        assert m['summary']['assessment'] == 'EVIDENCE_INCOMPLETE'
        assert N.verify(root)['status'] == 'VERIFIED'
    for path in [Path('relative'), tmp_path, Path.cwd() / 'forbidden-capture']:
        assert N.run(path, transport=lambda *args: pytest.fail('must not dispatch'))['status'] == 'BLOCKED'
    with pytest.raises(N.Refused):
        N.discovery_url(1,NOW)
    with pytest.raises(N.Refused):
        N.checked_url('http://localhost/book?token_id=1')


@pytest.mark.parametrize('change,book_change,state', [
    ({}, None, POSSIBLE), ({'orderMinSize':'5'}, None, MINIMUM),
    ({'category':'unmapped'}, None, UNKNOWN), ({'feeSchedule':None}, None, UNKNOWN),
    ({'secondsDelay':1}, None, UNKNOWN), ({'active':None}, None, None),
    ({'positionIds':['102','103']}, None, None),
    ({}, {'timestamp':str(NOW//10**6-30001)}, UNKNOWN),
    ({}, {'timestamp':str(NOW//10**6+1)}, UNKNOWN),
    ({}, {'tick_size':'0.001'}, UNKNOWN),
    ({}, {'version':'unknown-version'}, UNKNOWN),
    ({}, {'asks':[{'price':'0.5','size':'1'}]}, UNKNOWN),
    ({'feesEnabled':False}, None, UNKNOWN),
])
def test_candidate_market_economics_with_native_mechanics(tmp_path, change, book_change, state):
    mkt = market(); mkt.update(change)
    _, _, m, _ = execute(tmp_path, [[mkt]], lambda b: dict(b, **(book_change or {})))
    if state is None:
        assert not m['tokens']
    else:
        assert len(m['tokens']) == 2 and all(t['state'] == state for t in m['tokens'])
        if state == POSSIBLE:
            for t in m['tokens']:
                assert Decimal('2') <= Decimal(t['all_in_usd']) <= Decimal('5')
                assert Decimal(t['principal_usd']) >= Decimal(t['gamma_notional_min_usd'])
                assert Decimal(t['shares']) >= Decimal(t['clob_min_shares'])
                assert Decimal(t['principal_usd']) % Decimal('.01') == 0
                assert set(t['dimension_codes'].values()) == {'PASS'}
        else:
            assert all(t['shares'] is None and t['all_in_usd'] is None for t in m['tokens'])


def test_all_market_scope_denominator_and_no_false_universe_claim(tmp_path):
    conflict = market(); conflict['orderMinSize'] = '9'
    v2 = market(2); v2['positionIds'] = json.loads(v2['clobTokenIds'])
    absent = market(3); absent.pop('endDate'); absent.pop('category')
    _, _, m, _ = execute(tmp_path, [[market(), conflict, v2, absent]])
    assert m['coverage']['conflicting_ids'] == 1
    assert m['coverage']['raw_rows'] == 4 and m['coverage']['unique_ids'] == 3
    assert len(m['markets']) == 3 and len(m['categories']) == 2
    assert m['coverage']['protocol_counts']['V2'] == 1
    assert not m['tokens'] and m['summary']['assessment'] == 'EVIDENCE_INCOMPLETE'


@pytest.mark.parametrize('target', ['manifest.json','terminal.json','receipt-01.json','raw-01.bin',
    'request-01.started.json','started.json','missing','extra','index','config'])
def test_cold_verify_tamper_and_replay_no_network(tmp_path, monkeypatch, target):
    root, result, m, _ = execute(tmp_path, [[market()]])
    monkeypatch.setattr(socket, 'socket', lambda *a, **k: pytest.fail('network in verify'))
    before = {p.relative_to(root):p.read_bytes() for p in root.rglob('*') if p.is_file()}
    assert N.verify(root)['status'] == 'VERIFIED'
    assert before == {p.relative_to(root):p.read_bytes() for p in root.rglob('*') if p.is_file()}
    op = root/'op-000001'
    if target == 'extra': (op/'untrusted.json').write_text('{}')
    elif target == 'missing': (op/'raw-01.bin').unlink()
    else:
        p = root/'index-op-000001.json' if target=='index' else root/'config.json' if target=='config' else op/target
        p.write_bytes(p.read_bytes()+b' ')
    assert N.verify(root)['status'] == 'BLOCKED'


def test_existing_hunter_pilot_and_authority_unchanged(tmp_path, monkeypatch, capsys):
    from src.live_pilot import hunter_cycle
    monkeypatch.setattr(hunter_cycle, 'run_hunter_cycle_once', lambda **kw: pytest.fail('pilot invoked'))
    mkt = market(); mkt['question'] = 'UNTRUSTED_DESCRIPTION_DO_NOT_ECHO'
    root, terminal, manifest, _ = execute(tmp_path, [[mkt]])
    assert 'UNTRUSTED_DESCRIPTION' not in json.dumps(manifest)
    assert set(terminal) == {'schema_version','status','error_codes','manifest_sha256','summary'}
    assert set(manifest) == {'schema_version','config_sha256','started_sha256','as_of_utc',
        'mechanics_evaluated_ns','fee_policy_version','sources','coverage','categories','markets','tokens','summary'}
    assert set(manifest['tokens'][0]) == set(N.FIELDS['token'])
    assert N.main(['verify','--scratch-dir',str(root)]) == 0
    assert 'UNTRUSTED_DESCRIPTION' not in capsys.readouterr().out
    assert hunter_cycle.DECIMAL_BOUNDS['max_order_commitment_usd'] == (Decimal('2'),Decimal('5'))
    assert not (root/'alpha.sqlite3').exists()


def test_transport_adapter_limits_without_network(monkeypatch):
    import io
    import urllib.error
    calls=[]
    class Response(io.BytesIO):
        pass
    class Opener:
        def open(self, request, timeout):
            calls.append((request,timeout))
            return Response(b'0123456789')
    def opener(*handlers):
        assert handlers[0].proxies == {}
        assert isinstance(handlers[1],N.NoRedirect)
        return Opener()
    monkeypatch.setattr(N.urllib.request,'build_opener',opener)
    assert N.public_read(N.discovery_url(0,NOW),15,9)==('OVERSIZE',None)
    assert N.public_read(N.discovery_url(0,NOW),15,10)==('HTTP_2XX',b'0123456789')
    assert calls[0][0].get_method()=='GET' and calls[0][1]==15
    with pytest.raises(N.RedirectRefused):
        N.NoRedirect().redirect_request(None,None,302,'',{},'https://localhost/')
    def fail(*args,**kwargs):
        raise urllib.error.HTTPError('https://fixed/',302,'UNSAFE_VENDOR',{},None)
    monkeypatch.setattr(Opener,'open',fail)
    assert N.public_read(N.discovery_url(0,NOW),15,10)==('REDIRECT_REFUSED',None)
    def timeout(*args,**kwargs):
        raise TimeoutError('UNSAFE_VENDOR')
    monkeypatch.setattr(Opener,'open',timeout)
    assert N.public_read(N.discovery_url(0,NOW),15,10)==('TIMEOUT',None)


def test_budget_expiry_fee_expiry_and_unknown_precedence(tmp_path):
    ticks=iter([0,0,0,239,241,241])
    root,result,m,calls=execute(tmp_path,[[market()]],monotonic=lambda:next(ticks,241))
    assert not calls and m['summary']['assessment']=='EVIDENCE_INCOMPLETE'
    assert N.verify(root)['status']=='VERIFIED'
    # A known USD5 minimum cannot override a stale/unknown fee source.
    _,_,m,_=execute(tmp_path,[[dict(market(),orderMinSize='5')]],
        lambda b:dict(b,timestamp=str(NOW//10**6-31000)))
    assert all(t['state']==UNKNOWN for t in m['tokens'])
    mkt=market();item=(mkt,{'market_id':'1','status_state':'ACTIVE'})
    raw=json.dumps(book(mkt,'102')).encode()
    receipt=dict(body_state='AVAILABLE',raw_file='fixture',request_index=2,
        endpoint_kind='BOOK',started_utc=text_time(NOW),received_utc=text_time(NOW))
    token=N.economics(item,'102',0,receipt,lambda n:raw,N.FEE_EXPIRY)
    assert token['state']==UNKNOWN and token['first_reason']=='FEE_UNKNOWN'


def test_distinct_request_identity_preserves_equal_body_hashes(tmp_path):
    # Same tokens in two conflicting venue identities: retain all requests, and
    # normalize each identity independently. Equal bodies alone are not tamper.
    first=market();second=market(2)
    second['clobTokenIds']=first['clobTokenIds']
    root,_,m,calls=execute(tmp_path,[[first,second]])
    receipts=[json.loads(p.read_bytes()) for p in sorted((root/'op-000001').glob('receipt-*.json'))]
    assert receipts[1]['raw_sha256']==receipts[3]['raw_sha256']
    assert receipts[1]['raw_file']!=receipts[3]['raw_file']
    assert [t['source_request_index'] for t in m['tokens']]==[2,3,4,5]
    assert N.verify(root)['status']=='VERIFIED'


def test_output_field_coverage_and_invalid_recursive_no_echo(tmp_path):
    # Independently freeze every schema from the contract, not an allowlist
    # generated from the implementation. New fields must be classified here.
    contract=(Path(__file__).parents[3]/'docs/near_term_market_screener_contract.md').read_text()
    table={}
    names={'request STARTED':'request','source reference':'source','terminal / run stdout':'terminal','verify stdout':'verify'}
    for line in contract.splitlines():
        if line.startswith('| ') and ', ' in line:
            _,name,fields,_=line.split('|')
            table[names.get(name.strip(),name.strip())]=set(fields.strip().split(', '))
    assert table=={k:set(v) for k,v in N.FIELDS.items()}
    unsafe='UNTRUSTED_PAYLOAD_DO_NOT_ECHO'
    mkt=market();mkt.update(active=unsafe,metadata={unsafe:[unsafe]},question=unsafe,category=unsafe)
    root,terminal,manifest,_=execute(tmp_path,[[mkt]])
    objects=[terminal,manifest,N.verify(root),N.run(root)]
    objects += [json.loads(p.read_bytes()) for p in root.rglob('*.json')]
    def scan(value):
        if isinstance(value,dict):
            for k,v in value.items():
                assert unsafe not in k
                scan(v)
        elif isinstance(value,list):
            for item in value:scan(item)
        elif isinstance(value,str):assert unsafe not in value
        else:assert value is None or type(value) in (int,bool)
    for obj in objects:scan(obj)
    assert manifest['summary']['assessment']=='EVIDENCE_INCOMPLETE'
    assert not manifest['tokens']


def test_rehashed_invalid_source_state_refused(tmp_path):
    root,_,_,_=execute(tmp_path,[[]])
    op=root/'op-000001'
    receipt=json.loads((op/'receipt-01.json').read_bytes())
    receipt['body_state']='INVALID'
    (op/'receipt-01.json').write_bytes(N.canonical(receipt)+b'\n')
    # Refresh every outer hash so refusal must come from source consistency.
    receipts=[json.loads(p.read_bytes()) for p in sorted(op.glob('receipt-*.json'))]
    manifest=N.analyze(root,json.loads((op/'started.json').read_bytes()),receipts,NOW)
    (op/'manifest.json').write_bytes(N.canonical(manifest)+b'\n')
    terminal=N.terminal('COMPLETED',N.digest((op/'manifest.json').read_bytes()),manifest['summary'])
    (op/'terminal.json').write_bytes(N.canonical(terminal)+b'\n')
    (root/'index-op-000001.json').write_bytes(N.canonical(dict(operation='op-000001',
        terminal_sha256=N.digest((op/'terminal.json').read_bytes())))+b'\n')
    assert N.verify(root)['status']=='BLOCKED'


def test_reparse_component_refused_without_dispatch(tmp_path,monkeypatch):
    from types import SimpleNamespace
    original=Path.lstat
    def reparse(path,*args,**kwargs):
        info=original(path,*args,**kwargs)
        return SimpleNamespace(st_mode=info.st_mode,st_file_attributes=0x400) if path==tmp_path else info
    monkeypatch.setattr(Path,'lstat',reparse)
    assert N.run(tmp_path/'capture',transport=lambda *a:pytest.fail('reparse dispatch'))['status']=='BLOCKED'


@pytest.mark.parametrize('tokens',[None,'bad',[],['bad','103']])
def test_malformed_identity_preserves_unknown_denominator(tmp_path,tokens):
    mkt=market();mkt['clobTokenIds']=tokens
    root,result,m,calls=execute(tmp_path,[json.dumps([mkt]).encode()])
    assert result['status']=='COMPLETED' and len(calls)==1
    assert m['coverage']['protocol_counts']['UNKNOWN']==1
    assert m['summary']['assessment']=='EVIDENCE_INCOMPLETE'
    assert N.verify(root)['status']=='VERIFIED'


def test_resolved_scratch_ancestor_cannot_alias_checkout(tmp_path,monkeypatch):
    import os
    if os.name=='nt':
        for suffix in ['.',' ']:
            with pytest.raises(N.Refused):
                N.safe(Path(str(N.REPO)+suffix)/'never-created')
    original=Path.resolve
    def alias(path,*args,**kwargs):
        return N.REPO if path==tmp_path else original(path,*args,**kwargs)
    monkeypatch.setattr(Path,'resolve',alias)
    with pytest.raises(N.Refused):
        N.safe(tmp_path/'never-created')


# S10-ALPHA-NEAR-TERM-02: offline red regressions; no public transport.
def test_documented_time_filtered_gamma_discovery(tmp_path):
    from urllib.parse import parse_qs, urlsplit
    root, _, manifest, calls = execute(tmp_path, [[market(delta=7201), market(2)]])
    query = parse_qs(urlsplit(calls[0]).query)
    assert query['end_date_min'] == [text_time(NOW)]
    assert query['end_date_max'] == [text_time(NOW+7200*N.NS)]
    assert manifest['markets'][0]['filter_state'] == 'FILTER_MISMATCH'
    assert manifest['coverage']['filter_counts']['FILTER_MISMATCH'] == 1
    assert N.verify(root)['status'] == 'VERIFIED'


def test_missing_category_and_conservative_fee_bound_provenance(tmp_path):
    m = market(version='v1', comboStatus='disabled', feeType='politics_fees')
    m.pop('category')
    root, _, result, _ = execute(tmp_path, [[m]])
    assert result['categories'][0]['label'] == 'UNKNOWN'
    assert len(result['tokens']) == 2
    assert all(t['state'] == POSSIBLE for t in result['tokens'])
    assert all(t['fee_method'] == 'DOCUMENTED_WORST_CASE_CATEGORY_UNKNOWN' for t in result['tokens'])
    assert all(Decimal(t['fee_rate_bound']) >= Decimal('.07') for t in result['tokens'])
    assert N.verify(root)['status'] == 'VERIFIED'


@pytest.mark.parametrize('changes', [
    {'feeType': None}, {'feeType': 'zero_fees'}, {'feeType': 'crypto_fees_v2'},
    {'feeType': 'POLITICS_FEES'}, {'feeType': ''}, {'feeType': []},
    {'version': None}, {'version': 'ctf'}, {'comboStatus': None}, {'comboStatus': 'enabled'},
    {'feeSchedule': None}, {'feeSchedule': {}}, {'feeSchedule': {'rate': None}},
    {'feeSchedule': {'rate': '.04', 'exponent': 2, 'takerOnly': True}},
    {'category': 'unmapped'}, {'category': ''},
])
def test_unknown_fee_class_does_not_become_mechanical_pass(tmp_path, changes):
    m=market(version='v1',comboStatus='disabled',feeType='politics_fees');m.pop('category')
    m.update(changes)
    root,_,result,_=execute(tmp_path,[[m]])
    assert all(t['state']==UNKNOWN and t['fee_method']=='UNKNOWN' for t in result['tokens'])
    assert result['summary']['assessment']=='EVIDENCE_INCOMPLETE'
    assert N.verify(root)['status']=='VERIFIED'


def test_transport_failure_classification_and_sanitized_receipts(tmp_path, monkeypatch):
    import urllib.error
    class Opener:
        def open(self,*args,**kwargs):raise TimeoutError('DO_NOT_ECHO_VENDOR')
    monkeypatch.setattr(N.urllib.request,'build_opener',lambda *args:Opener())
    assert N.public_read(N.discovery_url(0,NOW),15,100)==('TIMEOUT',None)
    root,_,m,calls=execute(tmp_path,[],transport=lambda *args:N.public_read(*args))
    receipt=json.loads((root/'op-000001/receipt-01.json').read_bytes())
    assert len(calls)==0 and receipt['status_class']=='TIMEOUT'
    assert receipt['body_state']=='UNAVAILABLE' and (root/'op-000001/request-01.started.json').exists()
    assert 'DO_NOT_ECHO' not in json.dumps(receipt)
    assert m['coverage']['stop_reason']=='SOURCE_UNAVAILABLE'
    assert N.verify(root)['status']=='VERIFIED'
    for error in [urllib.error.URLError(TimeoutError('secret')),urllib.error.URLError(OSError('secret'))]:
        def fail(*args,**kwargs):raise error
        monkeypatch.setattr(Opener,'open',fail)
        expected='TIMEOUT' if isinstance(error.reason,TimeoutError) else 'TRANSPORT_UNAVAILABLE'
        assert N.public_read(N.discovery_url(0,NOW),15,100)==(expected,None)
    root,_,m,_=execute(tmp_path,[],transport=lambda *args:('HTTP_4XX',None))
    assert m['coverage']['stop_reason']=='FILTER_CONTRACT_UNVERIFIED'
    assert N.verify(root)['status']=='VERIFIED'


def test_native_fee_inclusive_mechanics_after_filtered_discovery(tmp_path):
    m=market(version='v1',comboStatus='disabled',feeType='politics_fees');m.pop('category')
    m['feeSchedule']['rate']='0.08'  # Higher declared rate must dominate the documented floor.
    root,_,result,calls=execute(tmp_path,[[m]])
    assert len(calls)==3 and len(result['tokens'])==2
    assert all(t['state']==POSSIBLE and Decimal(t['fee_rate_bound'])==Decimal('.08') for t in result['tokens'])
    for token in result['tokens']:
        q=Decimal(token['shares']);p=Decimal(token['best_ask']);fee=Decimal(token['fee_bound_usd'])
        assert fee==N.fee_max(q,p,Decimal('.08'),1)
        assert Decimal('2')<=q*p+fee<=Decimal('5') and q>=Decimal(token['clob_min_shares'])
        assert q*p>=Decimal(token['gamma_notional_min_usd']) and q*p%Decimal('.01')==0
    _,_,result,_=execute(tmp_path,[[dict(m,orderMinSize='5')]])
    assert all(t['state']==MINIMUM for t in result['tokens'])
    _,_,result,_=execute(tmp_path,[[dict(m,orderMinSize='5')]],lambda b:dict(b,timestamp=str(NOW//10**6-30001)))
    assert all(t['state']==UNKNOWN for t in result['tokens'])
    _,_,result,_=execute(tmp_path,[[m]],lambda b:dict(b,asks=[{'price':'0.5','size':'1'}]))
    assert all(t['state']==UNKNOWN and t['first_reason']=='DEPTH_BELOW_SIZE' for t in result['tokens'])
    assert N.verify(root)['status']=='VERIFIED'


def _rehash_outer(root):
    op=root/'op-000001';manifest=json.loads((op/'manifest.json').read_bytes())
    term=N.terminal('COMPLETED',N.digest((op/'manifest.json').read_bytes()),manifest['summary'])
    (op/'terminal.json').write_bytes(N.canonical(term)+b'\n')
    (root/'index-op-000001.json').write_bytes(N.canonical(dict(operation='op-000001',terminal_sha256=N.digest((op/'terminal.json').read_bytes())))+b'\n')


def test_cold_replay_schema_and_legacy_evidence_compatibility(tmp_path,monkeypatch):
    root,_,m,_=execute(tmp_path,[[market()]])
    assert m['schema_version']=='near-term-market-screen@2.0.0'
    monkeypatch.setattr(socket,'socket',lambda *a,**k:pytest.fail('cold network'))
    before={p.relative_to(root):p.read_bytes() for p in root.rglob('*') if p.is_file()}
    assert N.verify(root)['status']=='VERIFIED'
    assert before=={p.relative_to(root):p.read_bytes() for p in root.rglob('*') if p.is_file()}
    path=root/'op-000001/manifest.json';m['tokens'][0]['fee_method']='DOCUMENTED_WORST_CASE_CATEGORY_UNKNOWN'
    path.write_bytes(N.canonical(m)+b'\n');_rehash_outer(root)
    assert N.verify(root)['status']=='BLOCKED'
    # v1 verifier identity/command is pinned, not an implicit new-schema reinterpretation.
    contract=(Path(__file__).parents[3]/'docs/near_term_market_screener_contract.md').read_text()
    assert 'd0765424ecfa1857770ba8cc5d23f577e9bf05fb' in contract
    assert 'cca41e755b87357790321b838ed1ef599ff229925a336f535391b9f6fec2cfef' in contract
    root,_,_,_=execute(tmp_path,[[]])
    op=root/'op-000001';receipt=json.loads((op/'receipt-01.json').read_bytes())
    receipt['url']=N.discovery_url(0,NOW+N.NS)
    (op/'receipt-01.json').write_bytes(N.canonical(receipt)+b'\n')
    request={k:receipt[k] for k in N.FIELDS['request']}
    (op/'request-01.started.json').write_bytes(N.canonical(request)+b'\n')
    manifest=N.analyze(root,json.loads((op/'started.json').read_bytes()),[receipt],NOW)
    (op/'manifest.json').write_bytes(N.canonical(manifest)+b'\n');_rehash_outer(root)
    assert N.verify(root)['status']=='BLOCKED'


def test_authority_and_existing_hunter_unchanged(tmp_path,monkeypatch,capsys):
    # This WP explicitly extends Hunter with a distinct v3 profile. Keep the
    # historical v2 bounds and scanner's inability to invoke it under test.
    from src.live_pilot import hunter_cycle as H
    assert H.POLICY_SCHEMA == ('polymarket-hunter-pilot-policy', '2.0.0')
    assert H.DECIMAL_BOUNDS['max_order_commitment_usd'] == (Decimal(2),Decimal(5))
    assert H.DECIMAL_BOUNDS['max_simultaneous_exposure_usd'] == (Decimal('0.00001'),Decimal(30))
    assert N.CONFIG['request_cap']==64 and N.CONFIG['page_cap']==20 and N.CONFIG['market_cap']==10
    assert N.FEE_EXPIRY==1793750400*N.NS
    test_existing_hunter_pilot_and_authority_unchanged(tmp_path,monkeypatch,capsys)


def test_denominator_and_non_claim_integrity(tmp_path):
    outside=market(1,delta=7201);unknown=market(2);unknown.pop('category');unknown['endDate']=None
    near=market(3,version='v1',comboStatus='disabled',feeType='politics_fees');near.pop('category')
    root,_,m,_=execute(tmp_path,[[outside,unknown,near]])
    assert sum(c['market_count'] for c in m['categories'])==3
    assert m['coverage']['filter_counts']=={'MATCH':1,'FILTER_MISMATCH':1,'UNKNOWN':1}
    assert m['coverage']['fee_method_counts']=={'TOP_LEVEL_CATEGORY':0,'DOCUMENTED_WORST_CASE_CATEGORY_UNKNOWN':2,'UNKNOWN':0}
    assert m['summary']['possible_count']==2 and m['summary']['in_window_count']==1
    assert m['summary']['resolution_within_120m_confirmed_count']==0
    assert m['summary']['external_universe_completeness']=='UNPROVEN'
    assert m['summary']['assessment']=='EVIDENCE_INCOMPLETE'
    assert N.verify(root)['status']=='VERIFIED'


# Derived field projection of original pages; receipt raw hashes are provenance, not projection hashes.
HISTORICAL_PROJECTION_B85 = (
    'c-ri}U2`4Fm8SPs9K04fGP5cxEBn%6U--f?j%i(4t#H&Q36TUC0H~v*iTUq-p4<SZ`*dvqBt*zP-ZN_H91z?9iM3a)^{)5h4}bV?'
    '@2=N(|NJiJI^_87ckh<loAvtP`u67k@WbIRQ$LhB_G^xNh;z*)hPu{ep5r<!G4=a2rzwne&1qZ5y)SW1-'
    'IB(bw$gWV@g+aq&cDC?xbc$ryyhSN^<9^`ZcHh}8bXO(j(wL)Nn?nm)RJ-'
    '+QtJC$_+U<P=wsKVT=}%V8{@!d)!GlK*4p(U{_DHn{V)IeF6ANDE{37>e0V5152^Dd>cAf?_WZ+GQy)S|L+TT+HSnTw?8Y(-'
    '{Gm!6OV`KL#X6*aefLMc?=QFakAD+<+kbdB)|_(bbI0f9J|td^FW7hdB@8M01w$TU9>)@^-$do#LJeKw_r%-'
    '{V+m#KLM}D&;(xza>)!qGcklkZ-QDx8^4I%ke~R~?zP{(5|8jlxr|X+9*EjF4ZofWU&D(x^w_T-'
    '>{IP5|>;E=AY<!v@xC)W~{66&moa;Y_@PG3O)ADfrXMX+R?(5cmiuW5eu}`1wH-'
    'B;2zC7^C|K)DwYd?L~b~DYNw)V0A_4fAT(}!=i_y6_!{^Pgby>Hv^fBoXu{_A#k`~UE-_wU+A|7H2GtzSR!EC21?_LncWH`~p_yM'
    'K<qdw18q)$qG_57Wo(?!Vl8`t|9x@3xs=`>&^8|L^Tp?*I4pZLCk9a_jf=e_r4G%k^LRr2P1S|Lg90+4$)1ua}RfUkU#dLi9cGdA'
    '|LZhw0&~^}0R2)_?!qzkRQygZE0<`?}7x>?JP4ILEC|)3C;2>(;Gy>zLPhFKZwBaqD<DjoV!6HjX*>^H%qg58o@98tH<CZ_($PGP'
    'O*B#2Cv^`%tZoOfiqVG1Ayq>Y0j3iBI5-G;|~X90KoLK7M+yjAhJyEPf-Q@R}(Mfwy^0F^n;ek#gky$Va-'
    '+mBf1|j$xquqF=M}zhlVbz$=cF;px3{Tz|h@fBJOwe){wE&DG8J%l+-=t6%uXhYzg=$E$Vwe7o?2y<V=q+-'
    '>*QD?jY(>C@HC?dR*8$-'
    'mgEJdD3B)$uA)s^d>D)ziQJXR6fo`u?a?yMt2QhIv`i9@jObyli=+6Vm#^UX~$Dg`aa=YQOV?UiX~mI?Z9-'
    'R(|H&Qaf7hVX4wZ!_ZfXtIK`uJ6@5_O~FuuCD5wrWqc&r=>xUdr&>Z6$3*|_>FYG&(uZNJfy(PowMz3YLntW?{Kmd?l<pAtzmd|7'
    '1HUtlnd0tis$ESfk7?u?MRnGJf46W0?}(my&FT4Cojz@UnQqp*>*?xtnfR=$<@WAj`|Eet?dfm*Qn#<E+y0<#`-'
    'MrM9~eRAOk>@93VGa1H;r+Mi9%VoC6v4|g6t~~*1b|bd78FqUwR7Zux_o;nCNWOCv7%Y9=YAXztK?Xf6gY6w@DesL^<+xJ1Vf_J1'
    'oo@^k4>*k=enSBoC*ujWl9PIa72_9n@_OJl0cJ_;$)jI}aUyLK<wOZU^2{j3lYgeBqS*R%pVJ;iwyHKR#QwU$%$sYX180aQ*&zd;'
    'k5#I+jbZzOq>JL9wnw9x19+mo3z8VO&lOZuG9M@J&X>=92b>VRoceQ|%XOtsfW>=7H{3m&0PE;|+D}YVSin@TF;ZBL(PG;QY#$<e'
    'x`I<H+<Isvn|<GUqZ&Q>4xgRBLEW`c$k`X$^GY>?G0AoGrwm;}c7=jQdKR^D2z!sqY*(n3z*n`S+feWo9V!b9!%AUoa2+>GuA^)%'
    '}O*%k|yucb6((^HQp>EY;zlREN0IXoiIWV2k~>Qj*=wHZ~8_y3E}|FCF?}sc9SMd7t;hQ+2HKIP@j0{X87^Rn|C4hAF_W%LBUaN7'
    'ga68k=a~9~cp6hJ`h-XPM#um}03{N{$h9WY}dJWToR19!oWb?0cj#3?#NlCJ|qb8G=vow{?-'
    'Xj{TGJciCgcU|wbxVcDdm^PSMSQ(?~FkDH#Y)nB&ztIxMCP2XFnCH9v>ePyARgF;=#JuZ7*`#lX?*nuL(eH-hZrZRVF=w^y;*<-'
    ')2TbXzM0(bZ9+|4s1;?^JI5$xKQVD4?3w6;{}b~H#H=pl^45|v&{!=zxDCp%W}6uO=|W7cH_8%Ihp4kZ=(_Nh>rHCWDt8<>1E|C`'
    'y^nR1yaC~}spfj2^-(-'
    'r}TffdaemzSl$2P(I7)#594Jy6QCb$b7>efhB6TuoQ^pRXT2e1BWLRO_p&bv&rn8u*3ECe`s19=9}ac~~<`$~+Bmv<UXJkMrIwK5'
    '%_dC+azEjE8H8+wlZI`8bdEpg}y|UA34`tM%7+Or#x;YvD5+XU7r*sKiuR>5H9{C>t6h32Tz|JdTg(*+8j{eJ{qwS_O{a+{*A8Xv'
    '>T#L9~pP%Qsp4%*t3Z(qnmv0Qf+~(x?-!K(Fqet=5mz=jqdQ^<lcZyT1SaX|<1+T76}$)+0!utJAto4WJy>g&k<$x-'
    'j*9+;f?j7y){D=B{}Xe2h#Ai~>`gX~XodupgsW>^rfi*oq@<$GDK~r;e4(udMyFR43NLo52B<HJ|FtLz_OCLK7Pq?-'
    'zFbet4|afvqXnhk5$<wpQ9_$J>DFWQxtL#2HKnCJDX{Fc*ECugaXtH)E4c&L9pCK*G<XS9jaPVr%{7!}Y`G?e6=_wG5YXeO<Yp*7'
    'o0&Yvd%s0LnwMg0J>l4O`qsN_EcLwt)zQdFsb;-'
    '@ARC>0?9LS+PpjP4hJNQ#~x#G*~xT=!p5YeQj|udn=usl_v_jQ_qZ*m4?WtRxl`#c;HdGF#~U)mGTkxyr<SmU#I=kiWz?gTPA}oT'
    'NWLfhMYw7X_~x2S_Aho0;oU<Q@*+LD8VQB{-7u4=K-'
    'vn^;dBI`w!dn{iQl~=~Ak%EY+hMTIpBT{bh^OR@aq=$8NHXc~2|2YTl+Uv3Jdpzq&ee4h!>8wqa#+k7Y~!7LRcNPiHj9-'
    'pz&*0z9SiavFI=yOXmt(FUV4C^bjJv%mmM+1MF&d+`Fs-c0?~{@ZfJTw9%i0ZS=QwyDT5jzN@h6p*2}r8-'
    'Jjlz<J4)$DUAd#M^l#q8}K@EDPEcmWV_b9H-vf4lGBU#VlhRO%}$_2`0C*{g*869=m`b~^_G+8-rFp|T-'
    '`ZKEE<o;J3sj{3;MPVwz?2s4oEaiy}Kd#dCiAH_+TF0-YYMtU0aD&SS{%E@z^-U*~tsL&il0cet*LHROlTC7`q^a-'
    ')*+IR}&>l+623v_`xXUgr|t1`C)>XFC)ICA7-'
    'HlUwZj;+z94rIWSYHE;HeZEjXPj?@$map@4^WBBYyX#V@uPoHV`_(vhtWN8c7)L{%sDOFS`$nyS^lt;lt;j4pvpxf1am5_Bg<~j%'
    '#j4eh>zVr%045bm^{_FGY)d0oR5}`mCJ#&;7MKcngtHe>zFp-'
    'a$~4OM1vmhqz!K)up)2sA^3+qACqxM7yTG<oAm>&=C~&Oe@isbY&~z)aaqy@GWY9aMj>5Nrk{4^>o01yvd{3Pz#p{Q^e*A$+l{e('
    '2R$p1GM>nf=*|-'
    'J`f&cBsY3irU`E$yAgJr4H()DXvw!X4Ut$n{RS(dakSaldDP_F*CsRFBdlj7>cy2jK<EjdSW19M_cT(K%oXR4V8Jy>c-'
    '!*#SB9Z!=r$}=2jX%KjQqy>yUa8ss7^BcISGR#u`RWJ&E05brnM6s9CGYivfv4PS;nGD$4vc~~lm+62vWPG+#@1`#wrVWU7y1Thu'
    'K3*WJe?YY!9j(~=1KfbkBPt6C%NI+}v{8(C=A_TUAGbggTgMotaV^yEu<mQ#e0p=jI<8hwRI1J!J&%7*pe*5h2T^v3Z4?}zi50FF'
    '8&(Aq=>3q(Jo`VDCW(Myfu$YL>9MiWjv=?uE+K}A{d26M)R|9<D^#0Lc^#kij-'
    '<WqnkiVUj8@A9pr(dj+35S{`zkbmjm3&;_<_dCz;h|pSC;D0(aQaMj$xg)xeF^r3!$%{VYF<$tg5)uWml#^e)MUl9K`=~m_cK?U@'
    'bMC83K9^`i!OQGCbB<r3NV}E=u%MXjdLiS@T6f>9^5Al+E4A7Dg1a?7($j$f@{3r&_HpMA=Twh6G7LD3uM1xq$znu7P6N$mDAQ0M'
    'wB&fbYLn*EhZl>m0W*T0LF7$l-dXRv)h6Sxuk5pS04KOP#*9PLFO@-'
    '3Ae9sdeI^3uYPTj;B8}Dm{^ww*q4Y7_<AjuESjG!o_l;XAQ6f^AhGbAJ!?gzz9Im(KvxegD?@Dt-'
    '1sG5pGz$FcM#cgFz=YkcYPO^C*XH#Wv4xkVVT3@ooQ)KFYc6(tsm<m`4Nz)nru;Hq7cP$?xLoB{PNb)#Z(Uh5RCakoMhJ2*J{SZm'
    'qiJr~2vBc6B>*5cvKJ>xByN>S{f@S#<+=X<68?>8Rtv6_u6-'
    '*PGJZyRc+ycjYF~tsRA&$|Mez!!pL5nheKXm1WzGXRY;AtHi(xBr7#FHZnGt7~|{+%E~FL7ZT0h`5SN0qZF%^X8|v$k9UA95r(0c'
    '(<~4GLu;e9_zCv!Dw9g=pF6C`00^s>*X&p;vSufij0kIncKb32;3L)g>ko9*3k2}mIz75qbt_xaRMNBz^UNf$L9^PodF4vQ0bqsl'
    '40OOmI;WM}dY|Xa9hPV4JcMmbQ+MX+pFKG-m2$I!_~-'
    '3jULW<s%J10;;AnKI?}Px_(|eFR<<7%33iOFug(L_}`Z%aM(b93*r5t?$N#*)?9$<l>SeiKILO1Z*1w>%8PQnCKwkQO{M9i*sd?p'
    'ZYdcj)t;q%q@dAj-PZuPwgK)saeD@(N;-'
    'KwZTY0!CFQ=CNXIZdtdmKjE8rdD97#pV|GeO;)jX<uX6S1_QoqZ~M9t;#sbUO`!)I#2b<O0A+zjJiyurTv4?V_;C|{Xz!uar*SIF'
    'U^GSScdH50RT--V@nkQer8cnQcet`Iu&LLaeql%)cQa(&Q>br4zR$C3_i<5p@hdHFN4YRJ@q|hN4;Ku=5Oova##Ha)auc(ih9cX%'
    ')T^jJ5V|YD=2>;0SlL^yi#M-'
    'mSie;EGr9;$IvB@Q}FTLff*dPRf+`SDB~`JYH%_IqLQFOS8YH*_70GpX2n)}pXE{vX`Io66qBg;{p{8B@vaJ&50DBHH9eV2aI5&}'
    'e86|YGUmlrS{76o9`OxHXy^g(Y;f!6V#P+~6f52Pc>v(Aw;%4n|36Qk*Xic^`-'
    'g!3vRb{iS`QCaUEMaG@Y|F;pVxVXjyG=<Ex6{wi2$-'
    '{;D{<;aAi#yA{$jgp0!m4jb}P56`I;<l#>_GL+>$__R3B!(Mn~M|IMs9D#HSF03lU@1#_iHssf9mcDX$aPx3?tWC~R{jo!*A%5`6'
    'o>fjQ^8pa`3PC$`Y)pS@*u*IGw1(DAchhV-?6iH1#KLp(V3SxEp<%f;{m$v%aLOnWIEfb4AOAo6)OH&n?4+Xs-'
    '58Gkd27a`3zH#JIz=TlH2aLl$QQCFqU@+!$T7ZOD%9)kg;mB0g^L2uqv_z?=Md;p1lV0eZROFN1$2p4W)l<PRHq46O^4L~c^*mU$'
    'p&PC$uK~y^2^MAmz=Gl}nSsp1(5@5$u(}OOZ^7FrWoKeV!c`QvzJLPo;pS@J9v-'
    '&4&p&WotrsfbtBdvMVm0pbGQ)b>(n6`A0GxVgQ!@u4Dh!CVtkd503uUo)tXhKeD>~OHO<-Buats0V9+SYGd=@i&s?SD!Eun-'
    'u0##*W;#40RW!C#YWlKp39H7aPk{#3$$fgSQ5dvVS_CCsgIp1=QQgq0HHh7DLk;Po>>fbol-'
    '~gO&y$VqFeG|3<D!Ab>^C}pBzF4QbZN2((`{@Trs~{tnN_}Oe9$l;W(xJ?o#W4c0_RGrpfqrG!X=?k_F&C^@6wq%$2gVg1%eGA$9'
    'B7v5X+ATps*mavyhz&b)#<t2L)wR(%2Cx(m!&Mr<D-z-jQS?Tm-NTf$-oLXhH-Qh41Ik5Gu#epRhV#r%b0_iDw>}Gt+bQl%6otpj'
    '`FJQ=<NL}45C7B53#&km<SkFxj}R<Vpbsu;I#Vi{fg^&VFA3hQjd;Rv`A(@*-c^U)~YP3YzyN+87GE-'
    '33dvFv{GncMa_byg?<RxngJFVARH^Kz%W&)aw1an$66y3h1&rglF9<yq&lTM1@BhUxJuIwvM&Mavn=&4^GS|0>(wJ%)kz$XMn(NH'
    'mVmcPoq{SLfg550Xa1<U0Oi@9`W%SC`x$#d$2@P?(WPSRz42_N&ePq*@&Csz0BN`^Rj)18qk9#*%uKl=s@_3?;yjP5$Rx%u6zkBX'
    'd6{slz~Ke@+`RHohHI7AkwKvAHb#eIjg_rWQk4i*a$Bdx@t6+c_rZ(OXv2fm!me)}F-'
    'Nk!>mtC~PZbW509n775gvCcq$tt?_(KeG4`i~oi!4ugwm_co;9+2?tov#Td1q9)vc9gvZx;RvV>6=3&p-'
    'V?@L$s%d)24wn}^%)o>eb}`pQB*I#t0uVd1B-&g+)vF>dQj6(I|x1y5;N*J<E507-'
    'fQZXG6lftE7SRI3V>dhB9B4O$t4{f;7H=cdAo3@QZu%`at?nM$Sc$WI#d@EoVlN|k{*Xc?<Ejbfyaht<KMK}Uf>t~PHW$$y;;E%t'
    'kQElWM)MUqv;ppw;YF%)MRD*#lwvoKQVtU>R6zNdb={_B;JmF@d)RXJZ4s@E3k;jJnx`z$V$$C;lk>J*;WR3~5n762Os85Zu6!-'
    'QWDswzrwf+;8f1h)>7>oKURb5`)K$t;oF<wuo!I;^PQ^JGNrfLVE1a&x2L=(3QmsAi^Fg?x^cQSsvA`cE6CLHDWvyJkD&J0ZwC;k'
    'N}%1bS)OG-'
    's+_MiyVeTY{Gdcmm)GinH0*y7;`dYToW{uD7duL@RvK_wQ7f!|H2`bv(LOG2)Hgj8K)`e!;(LMP9w{9M|!%s%w({SNLDrA0}|!R='
    'K%O>?teHT@+a1SXre$1VEHQQ@1rRDpjZ$o^e{G?E#BYhRmH=PG1&N>Ll`GZBb=JSH)0BS0pF$Y=61{0Kp2WGAD3SuvZ2L1V&xd1k'
    'uwNfGjUo9A$Z90Q$=mP_w0xOKrPa^((x@8|VuYz}4rkcV9kye_!PbUrP0rrFwL%YTcA-TFL^-'
    'ALp!a9{mcBQFs6&+kXYELV3081cc;@krTXUQnoxV{W%*e1x>D0T%5euheiMtqh$>Wx>@xKS9Ky}I^b!|d;kaAivjJ{`;*+MAph#A'
    'uWAhh5GBFdU$^9g7crjbgVuk(E25wnH-CGl&2~_2<v^>&1*3vfgq`>K#`<ZS@2I*zO`o^>%b@zkb(#)I)qS2Q)^1}x*;by--8{?#'
    'v}puXiU6~)4~5LMid_|MEDLkwM7{1EN7s1n`R{hr5KQnS{*UG<VFj}2ps^(?z}^dfl*cdBAM{QM>apdx6iJ5sgxf*%v8D3thC9d{'
    '!4uzKNn!*^UqO}A!lZh)M3sc91OYQpA220oyhi&CmS}RW4KHx5;68PKt7*lhMBlbVj}BCHqHXX&2qd(CI%$_$wr-'
    'kMp2`cpf6%OzQSY^B_V=_z+*iP<Ftx-ac01msTx{CyNupFIT_pGwa%u}c+mmA{{3$=kNT4r;^rzqxJ!|B{fs1=6-84O!Rq-'
    '1;d9F;xEcD_L!Q~z$q4Gf{T7g>aC{F*(eV=cenU?9B+o@J7v{Z(OmrzvSZ?|{vH+KHp+aFk`E_M3KIz75g;f|7#O7HVLtg7zT1qR'
    '?YMvhYa6aJO3qBekaY^yl&Q_54BCO#LqzlX_sto(Bf)lQX8>1r-'
    'RuWuYD4*YGwf{4#Kl&TS|f_5Tx8nwaT!j&5iz!FAr@x}j#0gz4_8l&-hyahC0D)3aF^-'
    'YDM0~?1S`2;#rHKGAfEyIg#mmP|F7N>oIshUjc`)#_QQ~#h!J-SUT9-'
    '<bEs6eF>jz73l>~urb0A*Ywm#dU<rHtFY>bV=11>y=lwr(D?`ZHo`mM8izy-'
    't{jk&r5MQ`hK+rQE$=Z=iOu0*IoE_wHrjuFY+lqtnSMg$Xqd-w^*snktRo=j=-'
    'z2JfYw3iy3~zf3GNT$xq61i@|@T3JWAuUs`ei>Wt!{-OW*Zr-N*hf9UNafKe<q<D5SaYlIk+NFAT<RH#ZHZM$$Fi-ald}x{%?SbW'
    'VbU3Z>;GLOaA*mi){s6tR!%GHqDJnjtImt_=;$g4pl^Z&h<q^rlmA0z1S9Ydq$ugggGNKuX%ahj6UxFjhEQEvhuhz0oD@t8KV;Lj'
    'Z(2{ys^@Xg2{24$1yx<O{y=rZ6EZ@oV5B>F*>DQaB73ZDGR7ooLm!A6O6?=4=;&eZijXOW$f7GXoq`VniC+r(`z>rVkvTp1`>`gs'
    'X0P45{oT7eah)m0H+*6Y{CY}`RN<(bg(C%cn?r|SHVU)cGWuUYoR!-%{&b!3%Qo8_|021^l%*S<K3JOE6V*e&WDc-WGuO8d*3xlB'
    '7WLO7Ra51e^8gIHAPwyDU;LgE9$AV`I_Vx>`f6H^fy9}vsUZ#hKDRvs<(eP4WM(_BkgjIALI;t@bWgk$Wj)<$kqlnE&Q(MyW#GnA'
    'e+AZT5Tq;R9Wj5sj&Gf0wl#WuPT0tM`qrUv38Yqd<(Sl{@#1YlV2p`WJcG;(jT<9lvD#q4cO{zYBdb-Lwk@u41q<ABxN;?I8G}J*'
    '00V#$|0;5)|`eHNXO5pM&_7ZohyX}{&U#FY*mok0hGCev=VTuC0A0hT9_a_Q0a2@5daiSXILNp3P03$3K70PU<D)6vkBN|~*alb!'
    '?Pdi<C`sPAO--T;;BJVRrx==N`omSDK2J6%jH&4|g%mIF3>iVQ-'
    ';p2SLqumdqW}77R{XI2Cu1%f3sZs{?UEx#;GeG}f0EKp61w!?$;w`o_;KCpP?hG%vN<G|O-'
    'QL}Pz5BRbs`PEEw1&f2m2tx%b>Y;AWePSa{iM?aPfMt&J%ax=lK`;gy7ghf512iF_sFwZgMD{QN1+m>>wCSFF~vfzphQoe&?ZVDQ'
    '))~9^dy(RNt}wc#UR<DdEk^JMJy$Mvrl7<Yy5AHyPZib$^~Rud52|Dquwe0dSVBR5({axz6bbjnK_srJl-'
    '1cgZl4z7gc2bAE&!@y8m!JU8d8wuGFJ*)WX?jU-qeP>f|7t(5Kj}#sVcJV5q(>U0k73?;!EB7S-'
    'VUu@M5p%K7xn<#cQ|f4#g@%}~$`P(N^<G&QFn`Cd5AE0ZqLQ=37x))kG!50WJ=pn8V8>LYDhO>47D7clK?sgAiOVl|&s4pV)*qIU'
    'i{b81E@?FO6sW>^_z0xE$8W$0c2P3iLcV~5jAmA<k{kB(8e`45}dA|k1%yP5Mn#*-'
    '0AD#j={Q0}l$NK7HxZG(@x!=Fa!zruRTP*%#?o!g-'
    '_K!vcvqTWQ#z2dvU$FeC^NoYzBmFOcs>coQ{FnG5bRaaLt&%i^yT;*^5)N=MpuXA8B{K_YM(m|-'
    'P0??|O`J?<*H_R%^Wj)LN=Zv9mr2;~l@Av|CKi282{fj$4ij+&KzHzA@9i`NMc92fdo+iU6a7>MG`q+EmNKta*itSXGGq!09rl|}'
    '3`)=NOIxjF+w(*P?g%m!J%yx7Vk(YbQQ=FT8FFd9Cp79Z_V789Cc1~*HDEdY)ZtAp}oArNr?5L9V(6Q2&s|MEon&1{^FSa8!15gI'
    'o#)Jf#2U`mfVvvw}ot<jMbb;EEk%!OA`@YT?Qoo<@PI-'
    'TOsna*E)1#vl`#q*<Iy7glQ5;K$of=$CkXiu$Cxl7kg6^bjtTl0FYz;vDQAz-'
    'xJsppz5(Rmxhh`xu9@g0PilQyNQL<h2d{n)n8g?SBK%T#bC-zhh{4~#`C(t*a|Jbb4MIox%Yj0lq1Dn%kS`|P+jt!YrjHUL~d#QJ'
    '?sx?qj2B?)Az5N9$)T@slrkk6~egCaX^ynJJH57D|<ry{qszzi1#3x0KBabDzjtf^LJk#1ea-u$h={*dtJx8iA)-'
    'x`Y4v7>)P~1dWRP}Ymo!jTS;(i&VlA5VeKDSdgl3H{c7X=>SjSZ`!YIq8Ah2zx8RRuwnhLT$zRnm8op*0vLs7#<YBEVokS$zx=#$'
    'M|Buf~?KM@nl6F9@S*6sZT|DEJG%^wPI3)Waw$ohAvTgwr<~c)RV(y2I@U!N(m1?}<J12>Wz9o0k>8G;FD`N?D*NQBZL^lcGAdEx'
    '#9dYGbLaB`r)f_LXU>3vbc5OtWaGRAvGrF&h&l=~e~mZ)#<Ef=-'
    'R!%_gQXNxP9*@KmC8sgn=m0v#G&im6wYe~Vz%0@EuPf(BhMB*>%}P^I33@K2wwzI>V<ZoXgDf2q?~)@eBu^ewch9rX#GQfurNeyW'
    'o+PV`Yd*gtW<IHgVSPXU!ys$(#o0xeaCe408tR!LbFKC;^~q+P_Q_b!-G(%VN~KTEq-'
    '5TK)APeI;^cUFo?g;OzM@DwZkB$F~8Q1$ev5davhXhCxb<~x-'
    '@AcxP<)r=y=D=k`R$j!kj7_*&}3VQr!=6D|BpReCf5T)<GOgHfR-(QOL&5QNW)XyKIRuj1O%{}Q;95u(u(@}+l%FwrY$Jr-'
    'F0a&TbuSKpX4wWRV?2mo=KMttfDdUt)ilY|8Vm4N~Hd3Bs=3Zk8-F%xNy7K`&)QD<--'
    '6OvvDpk(sK1EYgy562j%coFpLg$ng9o6&27G>ReM3w2H4&{{p6AZK%N`r4XM#)KKWO%+<KkyUVK41N5+xNTc3sw5fEA=pj3M)y%r'
    '&)_^Y&`7Qq(J<Gv_H^w0;@Zgrh?}W!s&oXdJbFOyFuf0z@hmJ54E?UH6=g%Rp}*sm(X2ogxQtG+*2@7Q}`MWhAMLt(v_{4fkNvY&'
    'Ey&Kx65g@C?#%7JW<AP%&&E+$E6ySWR7|=N5Gs4##2rX(hK-'
    '{I$%fzY)7m7{PTaqbmE?LzfZRhAFnT9|JxQSwQ`i|v&h@*LGW=x6{qw}1(XjXmHX)I;S+RfW$QwFl1NJ<CuIQ?fC?~7`Hc2tXo1r'
    'bPxabwHoegqfFV`i-Yk417#}=tMvc)~xT5DyCfi=kpEEE821zA6q5TbTWi(Ldbc#x6dSIcCa#(zsthQQgRZO-hM5Kh77-'
    '*tJKH=DApy!|cD<kUt^5OdX6MZff`pODDI!A@M-'
    '<VIQwXDea=7k+)RtB}B<TpXJngTS1iF_0wtGaNo!g9j=hq;5KdF~uF`go;KMlBw)cUa)9ChOO-LQ4}$shO2CzYcy4K-'
    'GBio6<1NtCJr5xqBp_>ez!yfU4yH8bt9^3t}B~m*R`abkWKux<VDXEleA(UvLMUTd@q#qHXZK(7iB!`eD1Y(Kj#Bbm)yr0cH%P>k'
    '?Jy0}~O7GOr^sKEMDJrVTC8I}LnF_@nNDN)?W0lwI~S;b;VrXkStr-'
    '?W;)lU?C;iQt(o?=I*>?NFf5E(yc)xDE|YGB#?kDLT|X7OCR>VhWnFKotO5p3);@0|^9Fd11GzpzxY@nNPRc_5~G6siihATYAg$t'
    '@P9Om#Z(+s_Dd~Oy9Un4+E!C#lkQ23kklsOk;jlJIJNzq*vfkWc);;1=sFb8Pl?F#7x1SW?vyIeIAY(ed>`?GwD~NOg*F0>s683{'
    '^Z(KjU;t_(A3w4YbGU~RdWb6`8=LAJE6ovdb&il<Wq5_7O!4gmf9$x)Q_pO9@5DMt!vCvfz;xpDm}$*-'
    '+XJeuHa!WyzT!P`pJh|u2Gkc`qrg-m^Z~jG%|~U^XxkGPMjI_K-'
    'n=x*9r<5DzPburZMfSa*i;c;_T0^)nb3AGaHl<JuW#y>&az{y7Tc1z^OM$qw<+N&D9<JNrh>WQ&m*k7oGV)r*aFScwF@<u%?h!_^'
    '*?%Px`F*;IyY{SS1){eaZlkA0=4IsGwVB1N>`CxQaEuAZ&sd-'
    '>XkDP_MVImpXmJIt3n&hc;7?N=zi3@b2YqIjRH2A|0H6GYE&Bf1@;eHYak^eRj?Zo_+=46#vE=b;cDP4BlCA)cU*`mU9U5c+~8n1'
    '}m-Cd&(fl)CAJHQglW~XES%fs9G3LdKykSBS~rzL6EH1Y5Lo^Pap!G1?b7mWs2(b`L85P6u@|k>`kF-_-'
    ')p~?~#S_<@WyZ?}2an5AVb!d=K$S@&<jaQDCgo4x<sSG<j)}F8qSXoe7z~bB!zR?E=M5<6Xgv|NUMqzx(64x73%f)biEs*9X|LJJ'
    'DFakIEH)C%=88l&ioSCI0j`%H!|;_D;F^`sveeiu>_XURB-'
    'O&3`Cv`JqSXz{HUi2WpBMTtKxG04BEnQ2lYGwjpW~u}tBVMoMjLgaJTs;o1t6b;j{WV>22f2*An8mxE}FQ_%{oajOBO?2{~4O(E@'
    '1w=<H*MAU46r5tOef9WZmLJPpr$G$J#i}RZ`sZU03oWm$a;K^T$7O33}BfMpz*siu$c4x(e2nb$aO#P?TVPW|Vulno#zwf)-'
    'r){}(-Pd+qMH`3GlmYORg&+Tkp-'
    'c*r_PjK0^hCG9^^f3Ga)0^jj{A&D3K2kHv0Q?Xv*7r5OsN``rdTm_ULNHwZX&93;zrd;dvbd>H!_*dLnV$9^Q(jA(0HYi_IL=`up'
    'jp=-TOy7uL3HrRJ1kE6}*->ZOcy+jRkhl%~#;TBvoMp*jHIjHE)ZkN9zl+sNYY2rXp{)U+!-'
    '|UyAchiZdRH`*D}#N6L?RLuJaDA2#Yht`B?8#+621-'
    '>OIjzn=(irS6OP7Iqcz1M4}&DmFJ0*?SD3L!;@b)~jafB@bcQSV=}y^L91p)fW?_H0VC1@2(<frVwro-'
    '<+p_x{~o2Nz95<mPG1!au>pns<zIn-=%pO{N~gQQmPSDyhrp{mA~LyB)$j>Xmjgyb-PS_mT8m^+g~qr`X+UH1X`tqXFJM$ZOS?1E'
    'Hmd#&ij2rjH0-nM?C(0a8kJSYl_cMHBDGhGlVg0ozeGorlQiGqiCu@I(+TEJ-'
    '($*K`mu=4Z8Ev!L{(~+LO8E@yaPtU(F{synYBzd_PW3+-'
    'U8bovV`sEFG<SJy`YngG1}%J~WVx(=80D(DGPDS=3S8Ait;AL+Ay5J`dZ~{Pp4C`u+9x{!*TAQl3X(mFJoT8_8i>CVqO5`|HMH-'
    '$_gDI7-Py0+cFwCSMv4e@K3-'
    'wi1D6YQV|y@Y$<d>hv+8E7GFP+#AhC&*D(*{#*{=zrZfVS5Oa%B8Egwx=`5lM5($KBl#^E%~bQT8UJ|PYO{gqfMGbfs<3heU970b'
    'Y9Ooh!Fb}hNOQ5^iwMLEit_~ff0({p-'
    '`!qH^G!<gm?=$gBpY<zBMRtQg4D9CJo7hW`3OISCbA)sVzCIT56EF2(VDJijIpwwDNP>e@Jp<r)4~H%N;xYYs76YFp=t_E%d;Df8'
    'c!PqY1Eamyt?>#l2YrGA3G;&eNBz+Cp4PeiZqTI%siE%>dNNSnk4pl>W{u1=-J#3_!?%fv3++kwqBq)C0-'
    'KtDZKvcOKrYQZRTT)f7ZdAw#bii5jdUqwbUK`$+!XU^xRFk0Fd1au*y$&ERLpi&v^Jk??3ZYPwGs4Vn<WYS!;?{cB!onnv&_2^b3'
    'rR%?!fpypc~BMw>kyOh%WjGCn0rw!^AQ6zNW=RiYX_im-Go5>-KodMdF3p8U$6v(#2*0C_N7^FdR-nqLql@e8!5&$mK6m%4n5x;$'
    'b;lLQHjzLRgl*)z&H#p8Sk6DhqY>pXFC6h#`fg=L$tncj$#q(FgkFiAnrcMRy8FxpGObLdo1(oSD|2i)%Ih|$bZk)|OvQ~ti?Mgo'
    'IIWp}+OscVgKX5aLBNz#j}RcStIE>%hXYSN8T&A+$U)J!88W+j@AvI9e-qVOkifYAAjdhTC9iQXQxIlubl!}Y`G-'
    '||c^1^SZ;^a#nvBWhLuhA>Y?9;VSFqP(4-'
    'ZSScGIdsB8x~%iotjl<^&OAZsLeTb>Za$+ek&V|B{1Qg&oz3~7m^UI#Z?I|V!mogtr@J=JL5CemO9TJ@5#KKAnjXC)X^{Hx+8tZa'
    'c`w)B`+#zl(VeSBR1f<3SEYQAuS9M~qgz__%4+HKKuIrgJNXrS{Qko>U5fK<igP@+;lo20WC?cjwv8x7$%1f`j%M$48P`ZnN%)!1'
    'hJr&!folqzZ|Vs_#Rct5nu%-'
    'jcp`9~x@6Lnr<WAfY{{7yRVWXhM^)q1<^*X@53_1#WS)F%KIy4>LRrzyEa*(`s%2jkfajG&HyHucl~SQPQy4TM`W`*KD%*?NSxBk'
    'U3FUdJ-'
    'g}PqH&?&je!Y4BANZt~>ikL7d2}b50lcx&8zJDsgF<Q#lOCcTKky#=XA~Q_Kzj|H>1Ju0O_0FVbQ5Zq^%2j|pNu2T%>z$E{kFg8m'
    'eWgBlJe1b`$mj1TWXcdgW4F$zD<%^kgCTI+D$#NNZr5P*T<9bj?<|ce)oNCQhBx;90~TN9l!r;Hd?2C)PqxRBt`UEAH(yV^CM|c@'
    'SZ+QcXz+d+Pf6z&neD697^$KO?N=9aUy3O8fJ1yeTL8T95+rp{f4(mPd&!9+17S_ljXx94XT~a*qE8u0G=MaIT|0<3yt@Nl=93rC'
    'raym7ocVgVZI}akX0)$84gL*`dKPnehSzDKN{S~fu?lk*9?U>fOZoIPmD(A*sbtXp)>thFCI{;;)YckQJ>$=Bw)yIetz<VJo?4K6'
    'T^sy50~<Mlkz;e7H#_mpM$G9LXeC>6j&!pQGg|iabP9lyfa0gh`{wANn4ruudeQKA|D#w>6zYHReo~d?ya)ataE8<66bvyJ7apNG'
    '+j(aCkzrtNzL_H+Kc2-D$|cbPyQBFKB_V)O$EYl&nJe7Q6vlku_?2FiPZfunCd>s#G6}GG@Ule<2b4NG?;iE>71#-'
    '>xaL7yzE48RGjHBLl+NSe#UvjJ{N1p9nv~zl1MwHiI?8K^BXG<b`;FL?z)QFH8cgdCrj`6&R$H>X;wM{i>%U;kXpQxxeo0%E;Fh3'
    '&Lj-li9-'
    '%HPw`GSagg;WcvR98ui5!kV2Vm?DZ14oeb#)`;Jl$#o$k;r{#;I;A(KwKd;%wU9Vod0m|F5Y4e#OWr~7NJ?K8oT>!mv1q&g4d$Tz'
    'Sg@^SIaE&axGawcVbk9opZKg_W1@OkWD<|#uW>}h3r-'
    '()lMi3w}n=?o0dXAfpP_g=+^=FjXiwSn&5Aaje+%PqE94<6%0s9QLBu_5*@_*4`$>PP2CJ#z+K`lzx&8Xq8Pvv%y82UOR%cY`|>o'
    'p?}~qF;oqngW(PO*a*>(zyS57=FFInLe#o{3t$uxfJJ{6zAcMh>pf}h-'
    'V$Qzlsl;DagIKIjrt0r)qXx>~wMk{v6HFNn7VFXQyD9_l`GqwH(1hXeRjFXi{T{Dh@FUl3S4wIV+78{W^>%4If#g)FJDO&ZZ;rO~'
    '>cQ=Q_x~hNW)ovi7}As?*cJL?3l+b+TD{Jh(OZPtv1ROYv)+$xcxbp6%F1`hCUur^}=LZR+#zP84)d;Cf!LZdzs<&|c=6RyZG(ym'
    '7?Kn2)j>5#&UV<*JFki8ZN`rGrv5ZRgJGtWdTyiqYCLzsZG2JX2&xBXW>SD@T)DGIH3bg+zI*dkn7@r}?_w6T_alanxK)0AGI6Da'
    '&b46Hpsrv*^)Jd!#vglJfKq7gS%#!BjOvO?*Q*hCWZBySe`O@tU3e({DY<FSYrTYV+t;q!1Yj5-'
    'd5qNR(&nTF_EO6SF6{ry&Yti*kZT>=B3|#kvGL-EC7(*KcQd$3ZHvt|O*HXntEHWE$2)&6yJ_?LBLHUvdkx1EZ9v+%<Nma*m{+Lj'
    '`B;o(}A?LfD{8dq(M0jMf{}HdDpUm^|gF>7m(2c_jk3*IdWoywhFZERrh4w4@h!k=-'
    'EkAZhgB0w}#vbsimxj1ZgVIz!~twPuIu5hkK>IIt@eD$|yFy>d;&>#-g|=Q-!5WYfcQJg!bnY-'
    '9<`q>l#a1c~n^+sl|s9xVmr8`wmlBCb>BPAZ7Av6joRd5U{LdaO-ZMKa&o)83lXb8OHgzuhgBIS;xw>yqctt2v%8;Hke=q-'
    'o`vK5z_pzHvTa<owI@>B8rHo4P!@5izlG^dlt%<Ytax)>MYHP;Bs!$no^vO{7N~4}{b&OmA4^%wZkJHG59#x-'
    '*iwU_yd1i%FjPppUrQyT(gAR86K$t@fA|J8R8=W^J2wBuR2UT$qfqd$JgpZ<^(3Hgz)XQ|l+tb(x_|3*06RgP;-'
    'fi0?|<{LP5w&A@+{nu`%7ek1hO=hvY>Q$!!H?f~QOf0;gCp6YK?pGQ}s5Z8St$Zl>Lj8&6nbjCArc5LZO#=n`dGA*1e6ESzQVKUk'
    'w?g%&51^0*J1G~(3yIwHxM%(0OJ(fzN$_an^%RI1kV0NRCs@dt!K*e(T?3yjE_1u>y9KJ0*j2XI@jja+>gE~1XjarezWg0bjFrXR'
    '8-yxGPW}sO0Zq)R6wr~FB1(D29K;GjxHsAi%uK7}&Kc_hJ;gtw|+rnde#j{~dYjBPWvd#ilV#ao3b{{Zw*aBG%Mk-'
    'I*<CBED%~&|@XS~HsLo~i#!l)LY+TrA8bEltJ=Y(l8a%`a?=Fh0`lx`U;*lg&iK{uLzKdtM^jiTubot%6Fa7X=c*>gNUX&FYj_fD'
    'dI(VR|zDL`j%Jmtu4l&K6Q*8LYaHZgL3{(ArMQkid3nTPS<9mmT|B*Te%=Ht<r?l`fr!|!A_UhA;$n1<%Y`zR5+F>FY}#$vqB$H#'
    'R*@nqs6lVm6J!Y4XUUzBV5;mIfFUk9_jl~wktYiXBlfb^aoWoBw84mSF9Afj5En$x3_o)9efF#dXvsjxs`H0dHrC-zvWby;)0b8l'
    ')1<jw*^a~VngkzSDweksnMRGjIMZHx~%UiR3CvhI+(M9KnAb~Uf$gV&AWGJ?662_M{^oJRK*I@grBW#)}T=P}AD0B#nS5IT?Ltm#'
    '71F(G<+Y)0W@)2bQ!#jw#gx?2<}YL|1FB2+d@b$mjR48*JYkaGDn0muKaW;F{@3H64A=>{bnK&f|1k=1%MvqpLL&JmjDjbr%xgfC'
    'v|^e5Hn(Wz*yge{brjc1BzfN5_tt<jHgb;o;|?PDGGWm3B9>4!;m_bkYXuc#<K-'
    'i=s~H674Xgw<IF20MvM4^tym<^s+`I4k>5+~H%KR%?>2yL>T$-'
    'Wo3bw^LDb7uVBCYDhITyl)GZ4&h3S`Aqu1miWC;R?zIBMM3njS?*|#ljKLSIKAMGxp-'
    'b*rn^s<>U^u}Jh~O>PMcLU6cidO@rh7E1UkVxIbN<zkt^!PG<9o&HAe~~DGVxs(Hs$dGo2YeDIr!Uco?)f>#v#7oDPl#F6jT!*;)'
    ';Aq>9^il!TO2*EjlG@*oAU8J{wj=&L;9Jw^`0Nzq360z28FLz9Ehi}_+|<9UGw26UP{8DsBJKD0P{be}{2s%)@JdH$sGJj?*6ZrF'
    'k5P2*QHJ0Q_5JcyS>PFNw?4wE}tCwnoH4YV8G#w<twB)tZAu`_~p@8!vZcvj4-'
    '=FH(zFIo?m#>&gaEEZ`aw6%**YCa(>N!rp;moP@?qTw-'
    'h0qJqnRKaUK3;d{AUz8i))+P7#=6*kF5|T8<bG*=jEW7Wkrw>x=+DD#$$X{au@^QM{+261@4|PR&fdLkY7NNq7m@4<6o08DbTh98'
    '6b-0Fc+av%?gCy|JkqH1w5Ei%j%;L@?HF*X%{flk8nzb;hybR$K*g;FBlXY&{*)-'
    '(AOk1A5Jl2~NZSz)Y`87`#OkHEjYkQ}69p6U^joZOFXf%<IwaEBTy~h;|D>()oh%)qB{x?X3A!B?}e!-'
    '*tueTrW=$W6V&+Bw^eJRg3DbJ&05hUYnAv398Qp=`?y2*d2ylut8CN|G7*7a?YL|jNsCa-'
    '>mqD;JE#2makV_$1(C+GFp4Cf5=FnK#`$;};y<`&J1M~$JJ()0J|fPqe~nH)76dt((f4u9;O#?NSf%QIbD8zx)1e6_*%qe7FU?2>'
    'w=vKtZ~<?bsz(UVzI+|bmR9^GHyW5>@FtHrC^8C?ESoo`Z|M<=66LhvF;uEzny4<ChnSxh75>Zr43uCPMNMxG*mATz*rz(X_vm2!'
    'eVlSJR?jjSLu3;nQz^OUu_^}5N30-3w153SEzE3DXQ+2es+TPWh-Di7LJpUjobUlP9zE@v$Mn%p%No7#FoEYG8*YoSfX;Y8mbEn|'
    '$0i&H6xRnVlAFY$t$8bGD%?P|ULd|8U#s5Xy9Mesf{ppi<)swKTjosG0Pm2KcNu#!O^asR4eo2D42k|%|cTUFz+omttFnlqgNyC%'
    '%k*#KZQs9GLQv2gl<4~E4(3WI{j_Rc49)=NfYK4~TY6h~(oSZE|=k53J+*F4$tm1c_+a&G`wmXQpw6qO7I<Hi_eS?zpBRlf|frTU'
    '|JbeGEfIh8qt;~W~<m6oGOW}Wz6JYMTNxmPwIvJyFMZcDFxBkdY?OR<1636p6$4own%k1c$$p*a#dweb==r=;49Y33ISA<Y*!BuS'
    'Dlx+l=ujpS_pV2USWd}77xz@Ue+nKqJ;eMl=<_8Ju$7oNR}cY`KLoiq@)bG{~xIW}y5R6lRiuFtRQ4<By1u`_bs-'
    '(O#h7T%^hkM2bdk_gycEGp>;8)q6?-'
    'K18Ms}M#XVo1C4cH$H!{fDul@0m48|Kv|`hCC;5Pub~n%*!>doBFpwZTV<d1eLV7JP=V~GT_{}g)4Pu^pshQsO{8hJ~}5!qo?<>k'
    'N3`(#YKp28da_vP|MpONl0oUBc(|6SA!dxY6SgTY}_aArY(2zS?eUcUhnU3e;ey@sm-'
    '5Mn@8uOiuiY0jBMH07SjcC<Y|%f%MRs@#hsN1LNZ9x)_i7i6Y0VdnQ2YSnJ8qV4Aii*nk&g<yyRRX#G{=nlV>)X*zAsKc%oX$WFj'
    '}ua}Ak;>%4UcDK34poEvH*&bx&dAI=UbJhdG^c`p>rcYNn0UFoDUdu}qW(~!FwPWzQPAn^sa%)gc2c`47IRGvpyqO`&R*_XVm!0<'
    'f5ZCL!!Nu5nwk0KMy5z5DIG_mS7e){vSR&xrvdY|FMQ)w+r&I`9z+K(Wk=19$UUQ$sN_wm49UEwKW8fLGWxJfbSc$!|*MjuB`F7o'
    'P(Jgs+5vnTg1uk<=OP_J=pcY9=SLnF(1;IHk@-'
    'l^#bT7NoT$bfpD1j66*1?GIi(mXm50T99L+=gw^dvzzaqtBCv6q1jJ5nIlE+WT$A`Vboi`p#U2c_NBt?mWMbXDsKcria1nr`IPT@'
    'F+<`k$Eqz*d@K`h$JsF6w>i{Tx+DnqUHSI45|9PIcqiyUY~7#d+}_qJ&2Edq5RSRAlZP66f~caFz4M=y$BQ(8nI${zH>IEp?NI70'
    'Oo9FogcRM_uECo{zk=lbRdG931-'
    'P|Jx}o7_m(|K&M`m6DNY;iNK^t1kCV_;FinC8icNfBw`bX)<#uQE8nT>fOKde8&IlR$oXG&qz(Yxh8@Zz++Me73VS~M}sfAQno+?'
    '%D(No@`+z{|0lVtlAJ*(eMH0hhR*<xy4;zGlfz&3Re(X&M9ha+!qw1)~0)ow3%uA3$^-'
    '+jH1Ki;f7k4{9J(S|!*&9$2A!V`O8=u80cgvIQ8BbC!jwMW=NvWb(Qu<OJf#N@d#_vZu~+6}Xa1f?6w)g@p=r_Lq<KCSVk<sj?+#'
    'bwBQW-q6GkY_j85_8M({&v6Qsh>2a(-urxF?9$A>j&g|a$<7FN1+5Ysc(Fc&c`}aZ5$hs)a-'
    '9nBrou%c`oGmQldYpM32ry{0JvZjN_u#fn1|~2RsUB*%R6gvbdqk*L9gG-'
    'R#PZDfd)1)@~eaq|zU|fFO;eDn*LuZ19>ueI%$$H}X*K+^8`eNE6^vTjO1Iblz_C59d>_jyAoqf0{f8Be;tOVO`shJi=E~T3RGBr'
    'y}<r#h?7*sC0=Bm`SIy-PFXYw26m)>FVpEjW6~2lj`&6P_&t+!I%akiDej1V`kBa%j^oRXsaZ0({y$pygW>&h?9KLs)pQnY-'
    'b7SDCgq1TIhw13~)#*I<3L7!9$Issd7UDx<TEfAf@^5+AheJGA5Qg5T(S1{uI5fc#Tfz?Ah2Xs*K#i4L|UtbrNbaoazj(12|Iytr'
    'NmM;FCtjRhHghbMCrV1sY$<^Cy+((XD9UXx;|T75&gKXU>%c>>V(E^CF{v>?$|;WcSv9B^4c5cN@+%A4eH@y41$Yme=eL+=h@?jG'
    'jh&{Wj@kUE_K*4JHp_jgUtFA3Htmu!xCj((n{xtjmm#Y5c%cwdpO-Zz@I_jg1Mw?-'
    'J~EM<2D)G1Eh`Xf=gSM+qhaiSs`5e>}?gQky@gHcL2U&vngJ7LLZup)xXd;=ElK3_m7}Xru}QHASL~!9Pc{Va(9Nv3p@Rf--'
    '+54n|8Pp4C_<F##G+*zB@32<e-'
    '|0$|)!7=sFenMG7h3pQW^Xu+{=;o)RM`=n(bwD%kgdmCgX13AGvq6kk;VIo!_Oq$#Io{BBWKrRXDyH0M%&}2+4H$MJwfbpd?e^O~'
    '4or-u?*KuWW?}#nHE6I3^+9BOAP76p$ORkAWDA|S;D@1~dsbn}x#2YF`I(I6HI&o$bGlJ0<^5OA39OEeklQK-'
    '2;s9Nm%kJ@L(6YljeAE?3d^G9($s6U#mD?9&F%rqF+9rX9dM;O}>2*njpRGK*k4X~|($WrGfk)MfiMND}G|PN`MQ-'
    't>I)74i9vzFyu(0{UE)L7emdxU^V;jpqZ2JuRXzk}MO$gT$1`8%zOp0$+Y_k5Mbw86&6f|#FP>xlDHDheMMs&`E&E8ewa80KtGxK'
    'Nm0;w&h)1iJ`9D7XD0F`<qCk<{?_P?TegICS51s&Nl4M8yJxU_H?7b<}%Z&S$FCCfWYjQ&&9mf<C7#W-'
    '@~0eyA*%XV|wh~B0;53{uUWrBJ%p&D8`g0gvhP96418!#mX-Sf&(U7qF0HIp0XhO|AXsAR=YTiup3nhgMUi&1^94|N{j&HauhT$-'
    's2&)z{5vGEwLN%fQsgC|l}2v-'
    '$k^xBMc<CAYE5WQ=7&^6YygK%<_ubwh_*0V}=uIr}9o0DMbE69|#jKTP<Ad^q+Cm(&04aog+k+T29%KYQ+{_t;W^XOPKB@%~mrr|'
    'Uc)+Nu<)@PP<G?<V-@cY_aSa`Tsh;o=K<g$8)nVI-D<rv4$b=8-Bf0FC+6bJ8dWk(XyTx)o`TPAGuG&~zzqiSm4U}B-'
    'U#iQo$(&QKmo){p4@uNGrTDQ@=WKjs^Ro;oytEOb++#DQ@b>pt-'
    '?Y+~wTgzqV*d!n71*GGT+eL}_rhW71Rs;ulA{yI0y&o6dJ~nJ<f}%GS;yNFIX-'
    ';k^^SB#}N{3se08P>~=QDbZPL!M*J7v=nVW0^?X0LWnEfw60vWf2QNxeSt0+v*n;HXSuHz@^0JhUHcv)!FcH)@0u6JVo_R;O67Ps'
    'YiX-wKjS{e#gLtDkMkNKU=z>C~fEvz@sA3w#m3z9)6??)}$Ga_igF=Fy=D0x|6-Zgv^rcT7Q2HJo+tBvqsZo(8NCjA{rw=n-'
    'b3CMFYRWroZ%{x!!AHG)n+N2A`_8qT%QYXhpQhVHs30IWs@o~qD`IRv4luq#$$ru2>!+`=iz$B7f>X$!hG6-25rEztWU-'
    '#g%@TBR;Ei_fZvzHi2KcFEF6pw1ZlqP(g+JpV)|OV|hcrD?uVVIG}_44)jj8P0{;i&dv==pOSTZ<ltn&LN^9lFLEM3T2y<tPoN+@'
    'S9~*IriZefOM;Bt_SToY+7|VfsRGd2L2yD)Pu$&`~mpyWY}-'
    '=kc8kO=@ZvP9$osDDa<x5V?=#&ZBKk%XwAkpJKj@LHF>BlRWLhcL@69%=;Zp!>|r%WUp&7canPsv)y)-'
    'usGDuQSbM!qeU69r3KS$#x7@F2gZmBpxe3W7&-'
    'W#2z}nB#j${HUN4HyN7|GJyR&MNDMJ9ag#4Ry2%Ly)~0t0tyTLj=}o`5Z}<Yv|Yj$}@TDk9nNI>bwt3tA|3>e@wxo*JjQ8GLyzlv'
    '$3wCd#6yJi%$c?Sjc7RQ06I#?n?pt~Ivf_sAUq9_1?Kaj9+p&uKOI`@L*KZ&;f3kT^GXvmV=N+0-'
    'm*^crxZ;j<xjB5j}2&H|$=H;lTCO&)(^SRV?BVKE(3jz`sy2Ecf)vAdZk2=2|9ySDQXo09P_wMo$#GtI&(o<}8dDqe5Ey?9f36kw'
    'j@!(gE{&(15o%5|B|<{iib8QTrBorZc#U-'
    'R!4Jmdf8LBKB>@sZ*Se2%~HOFYr1OMJnbROWbi7@CkQ&cm?m)aR@yXUTQNzPPTKc8)z;{M5x|8@owoS)@axy0T9U<_f2&oCzEhX}'
    '34R&5T0&MzBNAG=yCdCE(|1mQXUTKqfE~q`F?yshdB@s6?15e0rw$CyUwKGT#J1Y3MTOcyjlrR90R<$8VnX*)gHhM2R9l2{@FzDG'
    '3RU7XRYHyeNp?rZA7rLagIzhTyp`p`S=6(ClN5;O=-'
    'PaLJ@(_7xHPf~}VVhh58ejN##ia7(IZ60_6;vHQ@a1}PV**%d>#^jevkibC(AAoq<~w6-X0x+--'
    'Frlf6{J9TNvt;1t!>Jp!2D9b_`TcRc_4^>%pEtb5Wjfrde5XBoUZLWI1<TVtGX!$Lb(}1n#H=%94TJFAHERNr%GLKF|%g&Q_cML<'
    '%#shrwYD2IKR)?GV?v>WrEZPC*`6rk4QSC<1kDL3;8M`@gNEe%^6s^khph1H86a!#%p)(T3>eSN6eO&jLsFb61TZO%5yi!|F4zfl'
    'Wu<dlhMa}n%ixbO!X!6cpt@~)udsfqCg}RMHDCHe8_RSJLINNqQg1*2Pe){nFYWqCheBD01rZ~&*L-'
    '^<RpG$E*Q=CT^A*vGOXl4&$)0r_*AZ%#KTO~A$G~vjvz=)?oV&n-'
    '61l}A)1*?uHKJ518j6_4Vqe5~P8gZne50X(BdUy4zELharf+J~-'
    'anN{Hvs`lHc|@J)c+iiU9*<AQbcGw@?ZFY$3OiXU^nSM5N|$#H?SQNp1@w|NI6+UjPOh|ckgR0M6y*Me>bCv*{sR!%$NyaQ`Q`Q#'
    'KjG#6J8JZwLjPQu{!_|tRjKvxc8Ls!_!q1daO#@6ZowWN)1*l!uXV;K9;sWx?RePc4R3DL#0gX66^E~01DUNqb6MAZp6O3IuvTxu'
    '#^=+S&Pl5*R&Y|w5l-'
    's2s54@2`ZejI%!$1ZZp!SDY}}IJs*EOMI(lElF~Q7teGdhdN@F}}AVP=rjA_J%MmE7_%40oBT9p*=irlQb?aSBs(>0g(e_yRPx1X'
    '<Xrpv?r?@*;jS4=u)gf^GgF!jU@!l+y)ZahBp<w~Zq;zYAY_9x;CSbQV*%Yr<Pn>J`uJZC!>yz)RK(nP8KKj2Rv<KyYpZlEi_Tv`'
    '(K<Fq=+M)DHnc2mZd<O<pOk^j*=>ezg^5QXNkL@U+orcv<J8)s=tCTHqD$E46CaJo3BMlR8ep~_1E%X)!1&3c9L+_GIt^o>jO=$M'
    '&EVeN4AKnFZc2CPyp18N0gi3ScwVma7-'
    'B@DVr%S76aE(ZrNnLsmTRgQ6a9b&mra>!wAKLuh!v1~RDU_?chCZIXUk|Egm&XwU5f>m2yVUZjU>1b?J`p1FPd~C5L2T)2KTuQ$i'
    'p(wLDs^e~Ixkyq@G@NzlkZWx_9oi8owBV2M5>@8s=?)qD-Pig0_EM#9T%|{6&C10{JuSX8Gf&9fu<MoQ<Ic=zd=?9Q4^!R>+T+eb'
    'Rl+=LudP)=J#%u0=2>))mjWE67U_xrH%_lt_#E`dqLt=QT6Q4Sl}*$D45j}?UAL)6*&=Y8`0S^kOskW2ELLU05$#ilZf)h-'
    'Wz_iK;j!1k2~leoycKZ(9qhOIEU61Ia^W>Gu9rgn>4kc9<|I|PhqAQbf;?`U$3cv^JMu7Bqka>+lo=WrEY+PsmA)DoS+S9);x_Q2'
    'dPYaghE9JpV<4Jr;E*aFubDRJ5^%e0rebuVu%|&o^4O!!#hxUaU5KD4_)-0aiHay`BQdlqfx-'
    '_3Ztd2uO_)AmCJu9puWn0no282AK>{r$cye&E03&!lAqE-o&DF2BUvJ+32bs~OQh$1-'
    '9vwXUsjhj%svBzs5PRlCl$o=4c#faVZHZITtaBpR&q`&iC!^uogu(gDuHSgVVm@p|($~2-O8L~rt4hJw!ElsI5-'
    'gzx1Hd_I3c696NmF(jhS@zaMa<bWYo=(xO*O-'
    'Jrr!oNo1SGyJ>;thD{m~G?nZ7g`YI&xir~?y3+;wrkmu{tT`!gT(<}8*8rM6aqTA##Nlb@2U+zvw+|e0ROM4hMI3;0;0H{mga*v#'
    'IThPWWnNOI9b6n7*Tk&w>#pz-@G%6DgG`;DW`hG<R*WThWkU$$wmo8WRmepRIam_Az;@gSJds_k>HF1kKfpVoH-'
    'U{}lKM0J_>YbAYZEFRNvgb-xHfgKMcj|SBD6fdpyp-wBF4Mzf=t|Fo*EC0Vdcrxvz!56Ry#(~(>KWOhb`YM$WLV4^D&F&P>!&rCZ'
    'VlJu3?$`w$`!j=c$n}a`%?=!8YZYe>lFVqHrIH~Kx&JYC8!{^dz3yP!OMVp%_nCt3zc{d?MVDTpZVF~%u$YB^@fl=#^<K$bQ)-'
    'HlR+_)q|w|UFj>sC{CFJkrAmK#mBwS9Q(2dU9*+C_+5!aNjH2s|!#X45WFrTI;=e>vw}4?oK(vIJn1O+%9E(1TwRA!Sa(AmYGE;Z'
    '><ckXoS-G)I0&MYkB2#`Ukz_ox`$)X!`YP3vJJKV~Ns&>~kyPLSIKZHo-eehpg<h92*;0JOnwK3)W0isj|F4>{1U{?rjuxZ+>k>9'
    'Eh5FMA_2^I<0>Bh}JemzaKD&HBGX$(k(bEpYgxx=Q!d#>z&-ghk6&DesF%~XDXHpTGE4-'
    'Q6<+0#;SE!SDtTuM+K5~r}#MhIw$bXQTr#~&qA_@A%P+?a7C(9dNES~~2WtSRDC)3*BW0M^ksf3PejDuQHm3hr((e*1kuBtQ1inN'
    '}OGrXTTm0o=y_GrQ&nt#2qU@isw#szz5z33vsuEBLF;W$rJEDRCOPyqk<+w9aBEWNk`Cl!RA-44X5U;U0alu+3-'
    '3zhC*)%+s!GXRmgrd*;9saZ)(z)3VcZAf~VrY051lmaJ(A?2dP*@?qv*HRIlPWzBmf}EA!KqZBwYDx4cF;_FItmC86axJHPPKIC{'
    'OnG1E&}=H55ujWh@(X(F*>KoPnf~-'
    'L?GMcys2_yMP@Y!NBO`*LM==%9X!*63pEf6c5@Oe3p=V`aERU+#imvY7$81um@N6*FMQp*?R8rp(*cm0<+RbtY|I!sSwve~bGPMl'
    'IuHsii+w3(rdz=6q6N3I@3=LiLA~V91d9;OY%Jm;aR=IHbvgRhX7-'
    'ZHl)u8@99hPHz{qTZq3Inl+tNj}j|FZkPd9@y$r+UQ{TbxD_)n?{SBGNdIK&x|{#RKF()Av9x;hI8SNtwvGx%tFW&u8$|8XJ|)V6'
    'C8(zSAea=!8sn^@y)_P8MIXK->P)J4s57rtpj&PHL3x_)l9ElZu8B;96+$ykO}}rg|PS3e$#sK_mcOBU4-'
    'Ly63?tFny6nLTUHe?7O6Y9#5U`%#-`LUGDsEUZqFpsa4#PL3Q;pJezU|BYN9-'
    'Vq#4a^4<+AO>~!B%viXtVPjg|1A{7O*N~6Z$|6!yMl`b1IoYgjTC9QF`Y%*De_GwTmwVaw@>zV+a~;s1T!H+kEy>eus<BE<oEa3D'
    'nk=i+&0vVUSz}EH;3gLQxGwk3yUwRw%lvGfq`VoTyV>&{b^f&>R1HtP45)8irAN0ZnhrU0JJkG~iA|#V)?p+0y=+B$5;#++=uJ?9'
    'jZ$`j)f&K0CyD@%(KE3M9)Z%MC!PJQDT{&mqn`ME3!78>p@TS&bLUC<cSRu*0(lJ;UBa5dRDE(IY4J%me(zXOi!okQ(qa{@)dEL)'
    '^(n?Kd1s~9CckbmU&)ju<7-q<z03e_)5d8hW$xppPT#mr4=+>r;w;-'
    'n2zOR*hwx%Cc94YGeW3|W13W&S@fy{bONU69#RyU=@v>~}`!PhNimo<8Z{y)~U{)x~&8R);J@<F2Lv$Hq#FRJ^J<lsC!BV806rg4'
    ')(OaMF#`u`0Dr4q*<G+fjBHE2IcKY<!a8HwZD_q>P*`7E8aI!VyL{Ot|>2xo#V%Bc#!}QAqNPYV%J-SMTX-OTB>89VD^rLwxI_Jz'
    '#J0_pojWFFQeBUO{0zB|(x`Z%5s+vHpj)BzNszOs7x3t=(#;9N7;QCEJbo4ZZ!N+hBGJ={S6wiJR4^;$;NBd}ec73W+AN5u3o>u~'
    'ODJL5}2V}n2()`BMnW~^p&bUhJm5;jZ8_*Ej8$gNb4=PM9CHk{Vv>sigb~0!1Ys}h(2TV$MjDwUCNeB8EHZ1J%C(*xQocfBbz0c?'
    'gt5I|#9*xeJK~S5WG*L;+9^ab<L{eSfSw*E;MoHs0VS5nb?^HmkKrxyd6qTJQH*r*XGAi+&>h)6<A6+!GkYocnjX&0vlz+~e?g3b'
    'hf~KCq+^woS{?WlyVnUU!@`5KmbLr==_m_wLTi58(J!(hPJi*9ckZoWHu|o=3A^DjuyBUWG^u%Jb;ljKiA{|x|8kk=<G*s~Yft-'
    '#_$f9Rgz2td?s<D~CDEBG!@R~I6k35rWyM9XD?`(POR6wKl(V$tVLxE|Wk8qT$e%AS+x!l3hGn=063Y0at^@&gga~^5Joe?#IZhW'
    'N~K}ekG1sA-'
    '1>C^lI{wZkb`)PZ)G}5;&(sUR|H>uqO@4=Nhtni_jP!Wrgj5w`qRnn%04l!who+9NFdwWQ!6o^n%IF^(4robtUw_16Y_cq6dZz>d'
    '^@EZ7(rIR=;HcE97p;rtd)wyeiP{CRDNf*Uebo-C$_CfsJq#)EPA<-_PGkwumkl>K2M}){M3l@-'
    'ph(Z&+_<Mj9USQ7rk%HTVqAtk(n^)=40g7f5h^m=adQVvuo#5iQvP3b45-E!}MAu9g7k<9REa^wGF1mw&Ku-'
    'D0L`pR%K*|F4EeI?~*OMuwIhnjBLlcFmG;~tl)R_g=8;CfFA9=AdIWc^b<EzY*!AdXY{Mw?JEPP*81VLe*YC!=6gA}zviT;AdC4M'
    'Nkn5DsZ&+cUoI}abe-dyx1Z(XEE=cf$Jgay=&cy#77NT1t*DaCIv%$qta$iSl(=u_+Db9kqm$SoX5s_V8qg>nvrQl6(AbZB976bV'
    '=mPwA>rldjO_bug~t5|K>3k=);0!Fz*~<f^cR^K55Zdm{4FlvM=)La`y~GtMif7P}am0?@;g)2R71ErKl6hPNsYNG<qAnw3(m=Y4'
    'iQ-'
    'd*26TvL17=S!8oag`pPo$$D2^~Fb=&5EKVVPOWYuf~5>#ZSY+wu2Yx4&!e}`#jHuc~y>cuYcLO1X>DJ#%G94=&XIC4o~dlKJiCG4'
    '^7yX@;o+{s5jN5^(Z?LkLe%{Q0wscWO=WkS_&$&Ws{~V^y^QV4|<)J7XPgZr5WqV@=mItqRx;lP{(``{m*LCtiHs6^vib9?!A4L4'
    'u{84mGgxxFih)Kp5ZHZA5uNH9tGbDgvwkxOfdYBYA_FMI6SV}-'
    '@&pY@;h#4xO|$5N&X1B+qXPeS1H=2#AtwlqGMA~`>bfh^ZP0ALy5C46Kzxu&0z0wchWr)%(D~YM<ZQLIb%oC*hjm)K{=Hmsjg6LQ'
    'Y|!(bAj34S*sua{CZE-'
    '7l@!A;6@PywoG@Q{)0{KrA~i(ogM=Ey9u<5&wK$R^n1&U*$%E{%!TUoS8n&9`2hPsko*Of&24!j(0dADKi={6{x(dmIqHn=@Gamb'
    '>V?Dqjm<-'
    'aeV)f}agVojJ!*Q%1mnyu`MTpP`G15;Wt?VjPmHJN_N`!XSLW0xT@R9q@Ih56IJD(VY~OgC7UM_@ZEUSx0@e$d(btHeKTa35{y(H'
    'lj}UzfBIcEh5Ij&63+1U9I+P7dGl-`!P9#k;sKP)Y-^LsniW3Wpvh0g~x5uNY$qRZg_RZ+-'
    '6vZjc#A&s}mQoX>+v$&Q<aaWFO!HEHBSWjo6Rk_MD*yJ(4=PkrgK;~(r(C5v&-%p%+?IJB_Fnq4F3#1Hs~rFOL`E^#g!ch^-'
    'OKEA=eudWoSojZNHP34RGCDQx)~37%EN=w9oH6AH6xt^qCKN$dSe{GP|0Y34nHv*=DN%a%gQpHF?crMqj<2i(m;w7D~T_GKIPmZk'
    'E2nb{F;aMAZQATBv#ZtM%fv>-'
    '0J!f)8~2ZsHt02Q2ozX>lh%gs;d;GZES7QJG!(zOJ)?$fL<#Vr7cXx^1BpGy}&=}W+m_D>!(YNzHyBnYD~<DC!}Fy(dP+{X%b^1t'
    '5bDDZk`RxJZ;kE$rOp8rVGybUcybT&2c~Dah8pq;nCW(&P8T3gb&P2qJ&TcbP`3QKIAQ{TUZGm=-'
    '3SIhuC87^xfkZ#`2V<4C1Lv3MEIa7FE`~SxgX*ElR|62uJKuTb@CUNiriWIR|U9rXE`tRld^m%M%=vKLeLeH#e8D^v%okFr5hr#X'
    '3T98kG~ru;EiW7c-NWK60<u4n^+iZU9)%F*R}1-'
    '?%>&t$T(u3X|dFpCf0E?kUSe4L;arQdQLw5vyXn(YdlSTv@6;AQc}NCGfX1X0z`3M%Xvt!CAnNaLsspz6Tj4!l889?9kAe2kO5fs'
    '_Hf9F~7c-'
    'GGJm;ElnQv0xW8~yJjr?czt&{kiK=5c85@u0mwWj7qxk_x24|a{k$Pmf}0Nms*v5Z#w7r$_TW+MCY79rU8?kSjsZQi9ow^euQLfI'
    'drqc7Y)B;EXY?Q-'
    's?<~`zR?>h1ixe=J)@_=dICp0<e#dPi@lNcQm0I1hH5&h2y_8Uj=un|`bwK<&;7MGeMA#Le%aotWgmsEKx%x!h4dpaO&@VRneIPG'
    'g}zkk+g9qK+ZpQ!dp@Kh{P2s9Vn#~HLv!Ce?K8%^gZVf3>*Ihr30t+~q(s8)4j^#6=4bQbn|`h;){7ECSokG=D##mK2wo?5zg>p3'
    '-!<f}A-jwkf>YIq21bu3WeGK>RYbKlDjcz%0Ry_0T%!EmKZvp?UOVbjrMQnz_5_e+K!exv#U-'
    'znmsm;t>6Yy8tB2{=Pq%mKp|;B{>dg!G(EF_I(1qjDL|;Pm#9klp=QV9<uArr1GT#%{X-'
    'P!db_)%4AEcs?NwS=w?R!rRZstnsY}V#<tG{PLr81lMgErEXphx`JI$^O2HOANM(HMu$q`hy(5;9YZHULGVzZM&+xvqGYf`89UG*'
    'foHVrD7LeQfc{Y6Gf%=T+v5R+T9{AJ6#k;T9b<b$fq*eW}y8uG8VrW?v(GjzDQq3OdcG^YQ4>hHTbha_yFWBVsHJJ1fn!H4jI~(y'
    'U&@JLO|Sbk_LX1ShjU)%H_K!G$I@EP(X}E(}O&X~H{WK>M+Uj`*;)mUC`Fp+)EDM=A7ZV3_u)4x_0BJB@9~$c?2RWb8HLQ|%`C^R'
    '%HN#8c$5Kx;8kN?VrDzhq8bF6ik$q)5v#k#EM`gu_mc@`(|0W-Z=OMHLw*P&qJ{7}s&BVW&jst#e-'
    'R?Tva%b6!1jjI!xPNq2+Fe9iV%@Vnz!u7)fN7}5XOvRv=gl$hR7S|DD~FhVVA^Wb|52@lQ-O(s<u!-'
    'VO!I0HaY0rN)~;KZ$YO4WYS#fhe>WqQlEmu78~MvOJQ!0YsOQ&M^%NWFE5j)&ZnZZ>LZP6(fNczk=zYq5=T%@G+dvo|Mp_f@MsK6'
    'B#=1Y>2zM}(9A@$;TV-'
    'y)0lGit56=o=Mbq>b4kUhx@4>7ugsgKki{r9+q#DU8+WTI$WJ3{Rn=QlF$()zHpPy&#pg6L9;gch{`U%2^^CRVJ!N;nMSKTe{lNV'
    'Qe!4@(bch9=59w+xz?N;lrg$-?&PT&QNSLD4-'
    '^Ecl1pj>zGNkpphLP{v899bzwCjM!cIh;_(8XrZE#qWO2d3XDeqGetk`)LOD0;y~iV$=k1`K${=fbkkLmMRS9Y=o{s!xG%AbIr<7'
    'kzL#yJUf7<wEpK=fz?9RMH^yG8WRhi#A2g^w8C8nqa2+dASKX>!OhjI!hYk?^+W?vN>eyP--U8(Wt7B!(9Vf!GSnY9Rw-XurKbUf'
    'lp%#2v@LS^g6ryqVl_Po>76I-@RL3Xt|cIDM*eAG9mrG^)`b8U3pmc*M}m?TXp`h=^m&0`x%wS08{H#C%5M_k%`Nl$gEE+y-'
    'V&T||XRUDr|lP7s@<P*iBEfm`M+c1gfG@)Rsml(zK-#b`sjQ{kb0pgb${pmG&bc@OxFuz14;vMlcS-LbWaji3!e0$!eI<Kp#ce@y'
    'ss^}seJ}nrY1N^6S29y#D8ay#Y6;7wqXJg^H%WEfTeja3#{uJTJ@hCO26wW)|Sv!lGxkD<{lbBSZsV+T|_082W*eRJo2B`0|ebBW'
    '>0Sn+4Uy8N9YnhS^w@F27C-'
    '~n&^<J>!pHC9Ml<7||({wnRl10X?sdg|+*3B~$<%mrWN7G`+<J|WXr&2a1>78@wsOEivODz;xkG1*wH*0;X4}UbSSyG*Tc^=>8Nx'
    'Q~3v6J3;*~c@u5|B|dEpH6zzMb^>#mCXq@aL`}pWp)k_ipfdL+8*4*Lt97ye|S9T3A^$mYgQ){MsB)2Hk=EJze<mOz}&V{`4w6v^'
    'eY568BYM5!ep?kUZ7NfuhyTW!N=chGR-qguS1{9o3u8%8@rLrinN?-tmo?=h&{?-'
    'e>UWR;~w+o;k$;9;5F1#x;$mjrrtnr_gA?J#dwm`Fc`EJuXlTB6{tBWf|Vssf})Ps8M}Dy44ojd{l#cfqIfzxua?DV}2wbR*wn=b'
    '^PIc@k^2Z^ddbvLygl;Diq5M3elONlY`R)p$S_aoxxaAkUe9%@97i0{!Tt=U3x60;hs$RMxXKFb4oPMSx%sq5kC8?Si2~`926r+o'
    'Dik&10%5kjn;Mbv-'
    'O7b9N%Eo@{}~rK2`lZ*{J~kF*n~;6GyYoroaf^O4}u%IG7ggR9X8$P%Ylnk|{>hRfZS9rGG1F{8Fhuy;6_vPcznL`05c@63HI#(L'
    'S-Zbl_5HWyHg7kDN$!`rxL7KUU;V-1rj<KXH-twk@2?f)p9ms#zaiJsVBKkumC3iOW&7=M{BK*>^)1n`*x{B0fcK@9i7Kpg!K8Ix'
    'Qs>g)00*DaEibdUR^R;=TOS!RShAUwzal0h_u^W=M!N$SL%gAc~OsAI==V6zNYd(!=N-'
    'uzEZoXP%ks1O*xwiAXLaW8bt1>T@UMnU4@Eth3G#eCCcnzhR;>rTQ}&&wA?yAKQa#kOOJ)QlM|6dkrY3;bVhWqtxVk%~wkI2vt^9'
    '$-'
    'X)F#_~L6nBf*lnFeW2jG7vww5m&elLs1vW&~<<Q}V1}Ad7_PY_1syu!$}}1MG9*WzF>S!Vhx$JDo@`$)zu>(sHPMX0Jie1Wu0y-'
    '#ln4wyx;%cl#&%1|g=pN_2+q1VJL0sb$;iymUVK&qz!fieK!LO)({2Nl|KFUR0K#dD6e!<Px6pv7LoFlc41dW>u&x>!WWhWzhcvj'
    'EZtb-H~*RFtjAKO65VW09xt^W3BNMgMhx7rOH@=_OtmtdI9hs39tPNz$of+-'
    '9Fzg{1iEtewpqbeq~s_dAPeh{o*}k!vSF09}rDFR`CEnu=4MpzonVp|F&p{R<!;9?_29jYxZzZg-Qa0UmJ;RKxEa33A{ANH73~ln'
    'WYMYi5`<PTqNOCfv{$5c@Xmzi7RIeqpJ!#09!ihAbsA%aE<Y(W3xs&Ga}G8N!}OZgn!C#>Xo!84;|#?F<5&A_{KkNDm;k$!uN9f#'
    '8*2BE3xVD<z0K@&nIUJuqntV<Jb<TG;S}pTw@)Sx#Yg6WdCg!y_D=fqGZQI%Jiy}`J${CBPni=bUA8u;O@kXFuKUEso*Rvg(Rbx4'
    '*jygr~)X6=>F&9VZd#vtxzgHJgYMeh%X`e^w@6FUh_zi@H{pmDUWnppjcK?1Es@{cF%d}o+y6yY~BMLr0Ak<T3Sg`-'
    '5Q%}$LCCICPi-*D`SZ#@~cO=5?Yva>P`Zy*EiV@w_oos1^crL_K-bIQe;6%icF7q=$VOfL;1`S#O_QA&n8`E+<1nsd+4@l5HpBuW'
    '$fx8plLkANsXpLNHbw+A|uj!JQ^uhClS^b8Ci9V9EGg_!g^_{&BZ_K_-s5cof48>|HMhv-'
    'Z!eD65JP;1#{IAph)dgZ3+?~DAju>;LTyck8D(J0(D3qJQ--sl3zmcf40S53ib^OHXU(Ph%XsXp)B}I?4Y46Q%b2gZIWoF?1?dP;'
    'YkkHkGmC}5sx2mf+cW?9d%7P7Nzte0MX;7h-'
    'U7aW#wRW89Th(=`5DT8Z^4NF+gBwmRq=v7C!PwTildp=#OU7seOu&zJBOI8UfwZ90~KNJPqgom>aOA6o#qTOiE4rqLgibUdRDnSW'
    'Eqz9k$igJbh}3(YO267w-'
    'ReSL@Rhus+r*GtZ?QUssNYE~jkO_(|YZzOP1t7arzuM#jHaOiXjyCU`06QQ`DW%&xeem%4fvfa=HTYCPj9Rhvb#qGmvTX?SsLF49'
    '7!o;r2b?;4#?*<MREA0(xSyvmf)k~Def50B1gz46f6oG`1JH#N$ZlDMkNn!-'
    'P<&rM17iLM$&)7{eqpqkaBl%VG%7#9=AE6VZiu^fkXlDm}SkMH?BNRQAc%*>Xe-vcB*`bc6|V#s4fA^{pGe_!cj$~yT;PCioAJg1'
    'o-veW2r%ra#IN?s%xB9-6isxOwr=I`8Dbpp!v+Mzj-8Hg&8-'
    'soEvDgE;`E=4>t#3!r$Y*e(1d=cRf%}P4hSrMrii=K4T1(h28Cy!F_4mxMj+HSRSPI~F9{oe-mkBjl{x4n@m`cjOq>Wy7IOw!pV+'
    'g;pY-'
    '8tG(MBtd1m8vEo?~xxk>?a9)u=vVUb>8i*DWaj_N1r3=HIHZG^sL09(LLjy<p8rjx7erHP$h%UMx&p)zGdDfeMy3jyNnk6w(e<x*'
    'KwC|(Jb?7)*e;WVkE(u24haBz9JQhTILO-'
    '38aL>B=3)T)Ml9_V)4hwslK8fpPD1DcB#kL)#IU_ndUK#YC<5!^JCp%tApHkb({0b5osUv8{7J=ZbNg`+uGIM?pXJ=J2N`wmQ6!l'
    '(8<)qB?BXCbG2{CXRj4bubTt9q`uKgN7c=vPPv1Nz3I>TnvLINBA(vWo79%M=dDUQ6`M|{89x&MP^+GLMnChbty8j0L5eDRO9qdo'
    'M&;!61JCMP7Mi=O*xu5Y8vNl0w3hUTw)ncu0b7q-'
    'RVG0m6F4M`Hj#M!yh602YfS_8xr#y93Kn8>Y(cb6ETZxmzFlk%BC>^bZ;qZGS(){GGOAv$aC)q)W0lf|)JyVgi3<iXGjGass$xs!'
    'n_L;1hxn&{x?{_7PDb*<XGVkE4pbtf=16%ujbjTdF}$&~A%P>3Cw@_Yl)iK0{tbQk>;1pK6+JE3mwV<bnxw|aM>lu&-l-'
    '!iG%hs2b!;-pZlypO;-'
    '+rji{Rxn;_8G)?hXLoPa52kIfh;?9}keUvaxSo3xlc*P#l&JwM5?2Wq(pnRmX<j*6dy#o99DpKA}SD*+?>V@#QJ@zCCgIp7;&L_9'
    '(l#Hm_!V$Qyp&`1aDEybUP{8RX&1MAiPmq|{Njr~F+2=A|}&er;-%eAGMFrEi`gWZB^-'
    'sy+@wGNc`b;b2HIY!E<KTF}Bw36b825Qvv`V~isb_Y5B-'
    'G}@)7AIL|rHY6FfWG3zMngZI#X)raEEnCNjqS3w4ioQ8`ic`0i;$!F3$EnxUti|5?Ehv4mdkTuG^enpKsF`P09W>!b00lld2;u8}'
    'BB@U`UCJ*g%_i^!p(IJ{>ivi7`%lv~^7+rxUw+v>efn(`ma9M&#-'
    'Cn=kH7mr`!ihe!(m4FK6|9b`Gz0VmhopGP!S|@F67lh0%7|u#@Xx3FmX`db~-6P(9AatE_qBwZZbIh9-'
    '1L|mMG`ety`TppI&R)tiZCi=XYa$8l2F)!TNTBPsS#V#^OEFJQX^3jceDtg;zHq=1l!Wg(l4$Gb%(d$Y|2WPj)^SRCd~a>DvgLJ0'
    'JU}O8jzr|M)k-'
    'xBZ8ArE9yorYNzUXPHTP`0JSx6;FAe=TF0yHcCJp3>yVaaF=fxd`6#1EE(Fs{`Y&e?%f~%wpQu`WRt7wn?Fyh#uL}Sfb!4VetXxt'
    'dinp#+veu$r%%7B^v6$mRjF?`2bF#pHAZkFhNGdbia|%WA#p(hnl^gn2#l%EUB7{CI>_Rr*M%wJq+24|r=<>OXd``dSTxidI9wqq'
    'KWvyFSzH{cecxnnymTndxh%AG#-H(^*-lmdG-'
    '__jo$8xB#Or1;2uGjOph2`!5w1|i;F=nt2sCK3S5HRfKK+@7Y5j)fh(*!YO?OJirJlU``iAOt_T%#@I356e*-_eHHYC-'
    'QXf=LW>-161V5m*1Vm5{r0b>0At^EC7t(-6Qo9$t``E~m6_3HNP!@sTXE3Ot-{GqQvcCUu~KUclKu-uQ(d|-PRm@B-'
    'f*h45?34EkwbD7@&@TVq=kJ^~Cv+om6`F+`vPAH&5X?Z-'
    'b9w1huwbeCNJ~ON|k5leVG4&xgG(voSY#o~2kQ=2n>LL~NkkHA(s59WDC(22S=ItC%KvC7L77t5u0$IbV19sF()hv@i>hz$SFPor'
    '=D*9GM?WGN>VCOq5cNK!l2ED4vW0AlLZ`MH7Y~-IjEvW{kR7(foMTgk#x@-Z0Y0+;7aJX&3f4^7D=ga-C%-'
    '%QmAAkL|l{*$KUq9ZpVd&d{{y%Mxe_72RhM)n?b1vn81w&=gtCYZKH6=5X1gd}np_SmsiYXOl05}2lummAnZ2%7IMkO5s5-'
    'oIZ5N$PRwE3OrRGKvrFw}7nY?VVLsj7=Dx}18Zd?^#o6U^Vv(B_^$nNRCa$(Zb{Ew`$P1!Tf#nAx|aXe|opl7la%ntIgXI(X~yal'
    '@6hSqb^g9G842dr%cZQ0K+m;SHBDo@WT7QKytlYizz@(Lopxy{T4uVRXh23P+oAotuK~@AqndW0=_(`x#w+)7~#r|7%7e2k0ZF%z'
    '~|zl-SC4N!P~@i%i_YTZTDk>*atGBmk^}ZF_>z#m5Q2gjCD$pKv2S4r22tt5sT)b31|PiP0_=O0Ic_(Akx_1g+O)cDpvVRY7t#+o'
    'xlCvmSa%2QG4BqbY+x&|}ldsIO@wMltp>NJ1>lt0mY{^@st9sb&v&*NAO08?=*&FI+$8?dtmT7q)MHz64u?l`Pxm85FsTjT&<)$X'
    'BhQ4u(e+*@MD$o8c%#Suvw;eVXuL<AJ%uk;xr}x`hmq2W}^vj76LK9iyZp%`rcgIkfrx7^=cCwm5LcwsPvvLhEXYfzcbBXW&7a0+'
    'YHlT1+e$pc%sJ|J&ZVZr5=n>Gg$-'
    'Syh>J$$St0^XlbQR}tm~GDu0yd3x_1=YTzS*BMZt4m}>%OsiYs1tf()WW*QWMPn6)oNMPE&96qY#o4xX4;|HdjmEcW&aM!rdW-'
    '{886?)4eJOdd7j|h)y5<r$`k-'
    '*q8^5z6eer+!bk^cuU5kAB`=joNo<LF{Qh|OE(NcentPr?^N|<$)z$S=314>8IYB!+eLRz?QZk1iTl^go(A#ALe8j-'
    '>1uBuNkPrv+X-&HFI2o0<tNL9t;loFQg*j5Q9Xl?Bl#f<zyJdi!Wk1=#j!Z$;G^0eZlUGxT!_9C|-'
    'IkPrim5pcV^>l0F@T+Gw+MND7h_CbGm*okx_}$}|2R6|6f2tn)`^sJZsUDZ-ufKk|ROEmEJ$+wM{!25yR+s;heokdp&+<p}E%s?i'
    '<r0b0=mv4FZsezcAJ;nb@1IY(R@VK>u~)_xN*E^M4Q4jO*q-t&hE@bcnl?Gg{$qA)+YnhBjxv}q=p-'
    's%J4U!7aWH%S1?Xs%t7vmgb-m=NahuRnHH<EWH8hJ=D;QS5#U+SVsq8B_uikh=-'
    'aVKj*ytV5342sc3BDr_fcpD{c_oGS^bFzPe@q{@&){GmCjRw5JupZ<eEGYq1Pk`l)9(-I!f@Tb9N&cV-'
    'Njk|Il8Acdc?xUykg(lOt=cp7OYpBS6BA-btQMY?nqiA0&pV5ip>~eAz@a4&L|I|YeROq@sd}au=SnpWK02snOxN>wAMC7D-'
    '?c5o%gmzHH+qfS8M9arC2Y3KHLLeUUFBrUNTL+m=|+K)4IABSMa7ChD1#?Wy`Zl>1H<2N=TxDfV#dflz8d>Y>~eI{BHU<J$#-'
    '3YrjN|{xLl?^(@i9yhM+93oIm4kE6;8UqLD%<gR96^Felnv=#W5_@8kuOS8bS;bV{zlpFrTA~754cTAo!dPh4T1EyusXd><4XbV&'
    '?WrhW1*=lvw7~Ch3x+qU!UX-|M>c!~0{9?MsXu#V{cOC4}(S8THXT6tUQ_v}YJt|qC<Ui=kR=rLOgDA~z-'
    'Pt9?3LpI05?$TJKhICkpQ1iLZD$X?OMxB|7o6URo5p>G^`>tzuHrGBh))O9Y5;Lrdnf7@iReaMO=wwWml(JXNJ8f3cGw?vBz=K3y'
    'VVV~TCZwPdc&h!msyrPVO&@aQdwo$C|$kyX=D?vVqA<Ksz_Gd%h*K3fQ~`_3TkC?gj>3CX<=bj%OyuZiMP(y*}!yDsa3<iLc~6*P'
    'a5abr^hE|&=0>%>*b;U^!4Evs`D(;zq&||R(8y*pu|Emr4oB>EV%}^YvyD;?Fv7}ebW?r7PDDdizsJ=S<Sq%DN(pLD6uv;wwbK3I'
    '<|8zx4rTJfm9WIjR|YU`>F}(#9rlp3qi{42BLS3PZ2!v5}~FmKn+vOFc9_~x9M^*;0~dMRduM~z0cNaj;{gscVSnWww;#k-'
    '7EsG)_=N8VI-0RFn!g1%^KZ5L?eB@Kyz~z=yw<Bp}Y!K6tSoP{1grv7HBM~?4(cuF0B;MEacy;9h6z7IXr>Jb<qYDq5{5w-7U_x-'
    'Ai>AJx>t{eNPgYun|*gHnK+<s~bG@G7rompkui8L8$HZNYOTs4gH1x1^O>cDN)ALQW6|0{e_Za-lT4UGS^JL)U>*n#;6am*XEQX&'
    'CRft!2{HvEzo}j>16tR_u+Gt=i_vi=U-l)<<MY_KDnd*E0|cRrrYHWvSh3aG1Id85vXqF;1U4PFMN*2op3ca`T{LsZ`<3s)4-'
    '8H;-*Mu30<C074Ws@NQ8dBiL6w43W1q>nF)PB)vTJQ-}^nl*9&{LM!bYwbBqiDfF+AF+^W?HiYI}*%i-?D-'
    'a84rg8lSnt$>6Nbg*JBNZ*Nhe%t0XUs)JJzkd4jt9*A>==W6UU}9)G6a>zy^SP6v7{F3h1u20O44Z`dj1o`u18&v-'
    'Pb&%p3|Z)JY38-Z;j%g2lW2}f{;SEl62TSaCk3k2GkP1Typ2^0vZR`tn(WFYhoVs}0N^!*fE5wn6>cgL!_^<OMybm_?2NK-'
    'Te8C&bu}pARyL@xOBBG4&#&W~AQAxA#&5~5WAaaAqEC-zraZsjzTi|HC!-'
    'JBXF#WSy!9Zh^TYJz+xJ^%54`=4zcQ;%U;l4G_Wv1#2vMkqjzD|erNu4_54b6O%!*J-xH-'
    '?eAyLu>5lkl;BRj|`1Y062*`s$1s<$=YNcU^hN72s|nKEhOb|SnKI%pN7BI|HZ7%%O&T=<nKfB~>oRZ&zJWVu}4@Zn_?jmp)fNZT'
    'vsOm`qDEb??EC+cRY?KMxlmj|t^G!$-'
    'x2|8~BdbcQVsO627I&WY8AeHJ`r$nhjD?SVMjs<&!K+TBo5_fhuDW0aKvYKs<MbHM^1inrWO>|kLh0`XWPel`z&KaKOxa>E)RR$g'
    'SNrmoZ(Pn2tG0zaUNYQecQK-tht?rN!GH4mT>wI~{O0LgO64HF(e=9KvKTMgqu(C#{3w{xWUxrudDO8<qN4<YdwivZtx#$yVw-'
    'R6Z!<n6)f3RRLbxOguU(Ry9U%4LPQ9P7rT8Cv^>8S8Ei18a1{C+LCWge%+nYAozScqy!s9LnD#=25M2Vv^R{k3SfMl+>804tLQz<'
    'j#I;EnimO$Q&PewioPl$>a5sJMz61Bq4Mm4K~u>VN64(XT~F!|{TTGI}O(Vi+Y|H%7Z?o?_~SQI`x0=CvEjrc<UWGm`>oyWfH7|N'
    'G@?m0GO7eo6gVuy-ujqZ9sQ=|F5<#!LtGRfX}|qL0OxTGU+s=oMUG<`ty<VQ$&$e93e`r7V}ImVe%@ER7PH!9fL0V>(oBLg1gmR?'
    '3*vq)|ZUxr*7@7#5|}9zVmKZB!>?sa*?J=RnPX%nxL~mG_qnTInP1%KBEvXcnN>EdC0E?g7wG>DYR)^36r^YrtJUR<PGfy%g<Pv-'
    'hmoLkiRci4BHRox4__z=g0sQh~six@N5_Z0!m15SIXg0d=lQ5Tdy8^L?A~6vuE?gqrX$o0hIWYGb`t!6OsTsV-etwLsV3g3*C)nD'
    'qA_^#ic3#*ov}afffof1p)HuLVf}>NOBoCo6>|OD!-'
    'w76m^hR2s<It2P@&s7CDu<hKkZtTa0_Gu~LU1glOLzpCleS*`c3)+2D0b9vo3;U_>;jr#TSUAabu)A};)3;_f8E6%E@z}G@0<IFn'
    'j+OOAjxuLC<CF)^aiYJe9@e-'
    'dsp$=m5S!WDpO<gNt(6NCDErG7;@TSp^B7%_J=&p8E7Zi0jcKkTmhr@6a0^QEduE?);pKC8p!v3kch-_E8I~tX3OtmcT_B$L{FU1'
    'Np^(AWWKM-'
    'T@KSwR9A3BPoWc<u1WH+e);*hFOIqWm4^0Y2Hd{HFbjVILwd!EghGHk3CPCko=qV)#Q&lpOlV{Z~8<%PD9^})0gMeUS;0|^+RN^k'
    '39GZGnKzXHMMyObqrQJ_xXW&hXUmo98nb`wE^+PxS{sUMI=s!R+<Zd-5Oz`VjzrOqo7QpGjGf0&>2@4B-'
    'f<$k90KKotPAw{Pv#?2DU?TM9sPYD8c9-F0h+c-jDLMBU*@hqY<OhWq7Fs6BBz}#@WXoh)S&7eSGwRuj&pMYXYH-'
    'h}=Rf3ehx4g^d>AKHTCz|Z1IFM>)p+t&88QS2yCyl7wY+8@?^gXtF%I#_o)CN;339}|+S0a+a!-'
    'MSn(MZ55u}_04su)Thow8BVF=+8IsAuQbZ^JG1)qePivpg(%KY<U+Z`cjIn|`H5B33<{;g2>$D={C2prNnWVa|`_oK33ryJ?~qVo'
    '&7_J;eSSE5(W$aN5{JfRy;bIADxB(D`!99X-2wSD_-8YgKIK=M-'
    '(svrCM|k(8;b)n4{U_)zm`8Zrs$)X4+Yj=FsjcL01vwu%RS3eL)=CL*&(vD|QBE^9Jvm}K^3I>^Se9-'
    'ULo<(1T2CHcQvitYbaiDx1HwS{<uac*oTHoz(ATEQ5G9Y2W?L`oQQLVVPm;42Mz=bpspnVy*U(r!|W8h4*#5|h^BtUoL#qK$49hM'
    '4i+3Nd*<lXht#HigLN3mwoBFgwUSr5F@Braa%}>-'
    'AkqygnHbacZ&BS#@bicH2g6#}HMnRC~};osX_#n~@Ug{F+dw2CKh+9h6UJN4#et9*u`(wKr{eT#&H4Yg4sJe#<*?ke(qokCusThT'
    '>a-t3I<{!voRcbQo_$K^w6v1w;tOkVjrs$Vg-GI+X)wDNxkmX#7JlfVYj(lUHvCO-'
    'h&Rg;jrDtW$JC?W6_lz2avH_(qy@X);;IYGWJGesYX=o3e)j(rQ%M%UuzYcl&;w?wQX*yk{XEqLNJHI5_jUXH(8-'
    'jKH(!tik<62DHsFZ98i&$xkdSu#u5_Sfd6tETrikcSNXf+*~XHn~-N5Fm9bEvne8g<?OO!1T$x|n1fqqCW-'
    'M)`u8L~9|z6+#&51agYh{LUD}0#MQ1LA8X|LZjE86?8p}&EOGjzvAe7md&=(Dp9UkH+o6_s~q}^GF_bkLCs1cJXUdyQ&vC@Ts-as'
    'cp%P{lmVt|75ZC<s?@4T|$`GZfsR-'
    '`OAFqI0CkjDx)VMV2pp1akt2aqT<*vnRT0N@8ur<Q3e##0Oni901ToJ=CtjEH0y`YW>|s{mruW5c$l^^SmG6gz$+r0L~H)(BfVeV'
    'aBe;oogYYhBrQH9~ZI2~MxW<NaBP_bkLC6j3_v%sWi6;G9c9Q_BUML{SJtVQ?_ve6x!mCq>>3Tq82bwj?Y<+~e5a2pOd`BnKyN*4'
    'zm-Tb6D~r{cFuTVgK};f|6q;>P>6n4f%LmhGfB8Vj$cOxGDPg|&&dL_J9cZ5y<n?)4}M|1%|+qZ^9s4X)yyspM|<{PH1LQt-'
    ')IK70q}J)DJj&qAz+X}3dJ&DI2*Np?V7?H7d?gfKBXvUH$4-'
    '^dv2NomjsI_rr54H!cN93<<lup5tgj)NYf`R}aqyw|2l3vs?rPYwOfv`FeAy~c}6tzkLN#YAC6tM};@&ISh5XhXwEJ@p!6biF|i&'
    '83C`6-V=zz3h}O?0D7On-K+uu22X_$7n}>Kd&#%<5`GzEX4N6!iIV(%gnAaYFjgL{G)t;W>(D`@gh?#DZ>#<vO>m<JRC-'
    '}nXLvb25`=CNA%2W-GF6lP=3+&RPTSXBg{#P+Jn-QVjYg-'
    '3X1YkDrKYH=^zm4CFc4x`@l+pYc%N4$XQthyNZyuxw)Ndj=mdKCO@o%`c1V^+`F~fjX?pa(fInZQqDrWXCbzSX-'
    'b^y7W~3d^G@MC0R3kI*6urOpQpLbJ3+RPC<qH-udO63tpfz1%G$!A;`khG(;6aiODW`N4@_2)PNk#S3HoYSe7)xr1&)e$8ikdkI<'
    '!{DI9`7#ncWLL-'
    '4I)aJykmy9g(D2@crOO)LytG@dJ3(n+OrpG1qao)0b56P?kpa5Hpn5TVg#c@t&1<=yeY|4Mm$Gn=#2PrXk~qo93O<URey$>MYG}7'
    'b=<5TdbJIaF`||WL|D$C${<pd09jH5Ed=UX~UwfDDD|#g=_L5EmsGtWO>G*XZEqN3SF2Fg}*_5F>a)kY-sG_^uxv+Bu!_carQEUB'
    'H@mwnXeK?T3x_`=A-'
    '$M=FWV37b0O6q1O@Z<}Af~mg3QIrA6leu1o=zeF6;LJ4B636Wc62n!*wTakrT;5p6S8F$G3Mt4kGj2QYc_4b}q%1-'
    'skSV~!?1reT5~N;1U?o(KiDJHui--+qBZtq08Crg66V8?X%5@{-ua-B0fMAlE4Cim!*(P(o-'
    'C2@ZhUf`;1QD?U#e7SeNTSiISd{emzo>^o==ZF^SYJuC6(x&o`A;or*~4DAInW2WYsZPrI~fhq>S06yUigq^n?R@tz4E}oYj+wr='
    'Lw@ivU`3PNj73<cb39aNC=eIUcMr*0pgkT7tWhTkqSR*gdT4HLZr3dp1SuBO3yt%~C;Chvf@#;OG*anNd@=-'
    '@z)f&Cz9S?$r)m1%2!{J`~gl6~Yb%}VJ9?*z=)I0Dj$iKEA|Mp-0+qaSw89aiwf%8y$x5g6n{m#w+0W7bb>VgFz2VeUMCgG+-'
    'q$(K#4ac>q1cdMd>Wv+`3j;rJKA15@ivvz5T2@hnF1+f<l9pIit&VXujS6rI(-'
    '@k@`hs@IF{bLKe6<p9gBea6)KeDte9)zh5jTY3su?-'
    '52t+a$R^vZqj{AoaL+>T5%lh#rzEYFY!9H)(!@mChFwIZDZ;Ea{!c5d%<LfnY^TYJpClt8M7!S-'
    'Z5ByFZ`29ZgZTG;RCcce7`01?m7qwGr_vl9GosR}K@5FV@Wktn+Kum2GItQu*%YuF%)<p8$X4HId9dj@2H9M;FxF0|4VKJvWu|mh'
    '>Gd}nRYvyYBd*e35*4#x%p%Jp#x|a2wlrm)Nl%n*~oL^2efQ-'
    'i6WQRpX6K*kltWo)`_0OWO%9pt|8BS|zUG}eFR*HC5@gN1~f3kMl`M7fVBH*utJ_jG}-s-Ine9=90^{m>zh;-'
    '(i?Wp07t`<z7E6tBVVJ4pw($9zqoC&Q|tqIz8$gY{-'
    '>e7rk7w=6s6W@u5{8lI(pm=gd^wg5|1E)$oX>+;hR8sQU<s#XIFboVb)yw5tZe&-'
    '&sK}o0Me>RjX#l3*t6cLoI6wN2SM8C^1Z^aknG4>8ja(lRvd9?Y3qn;o1BW+lz^L5+xuVTCiWc9J2VnUJ2A2npp$~A3_}|mO@Gok'
    '!8dw~y@=I!FbGTvWnikWuwG-8iHzD8F5+5&6zL7{W6+kCg;|jtj(r&m{qBxk2r&fcOG?d2*MxfChYBZxxON}&!2FFc^CP`s-'
    '7mA~CUXAl?r_>8$Bh>3|<S#J0nKwMWU5X?+(DNMLGrg(DT6nd=PHThx5xbP3H^52^v%nSl$MA!-t@-'
    'y4;0F`Jje_Mj{V+Hir2c{K{QzkD07>&K*uSV?HSj%JvnG<ZH@xCSd+-'
    '{@7zPjuUj&&GQe!7fvDd<2i)k!r$!SwWJLQ%C>ZTi+@~uE;cF7*>XiU>^+Q#tg5Y3VdK1PBKM4{pg;`<I(HMEzMn^r#r00U#sUP4'
    '2PmrVU(d()aU^XOHi8*NMB77ddO61zk(mpDwy%GC70=!8*feFQM-'
    'L;vcc^^Q;a^M}X(`P<|Az~AA_@e$$J!}R#PK0p2XAKI$;|LswLev}VAi(Pu!b%lFAd2X5Dx~U#8h><7+lsYINdC$?7b&3a;ozQu#'
    'If363C-oa}z-'
    'ZZ(V28Kr!b5Ip42KjqidCoBq8fsOCYP#Wq#b*dr1eHqIr(T24`07I#ziWa{&KQ42CI_^g(<?TRIAw`0x?aJ=*4EA>Y-'
    '#NbLb+>Ua+R!#HiKR`RDvwevf4A`M1wc-'
    ';(Z@>BA%S`U#^WyyEae0x@_Ay1NAsoN1wdrj_b{d2~?9#?7r0DhVEZUR#XYcf?>U^=;Zw?o7=lnQd6|1nx7n*uWPUn~N#hAVS9nC'
    'DjNDaiIwb(GQWoqNAWdsvd-KJ2G`_FvXMlWJ2gg5*#kgiVq7!&gkDFYXPhbbK-JTb);b%YeI~!6<odKJ_CN~xK(AMm<K}7tsz=B2'
    '36zk<j~x-'
    'ub1fbVf#CgcPoECoi+M1YxK}EPA(7!&t>;hj8<nuV~a8z&lpacbWw6K_GzXbVJfYpf16OxDc<O!z3Y!pO}#doFv*Lj9`IVQ(71|='
    'I4Q?rU;qy_5hLqkG)5Yhh*P7y+;A+D!}NitWnM2$-UJ|6@)b3B>-'
    '6bY2kFlq9ebOLSdOEU7zF!T4H1yUDSa0@&Et&7g`oF(Fvk1o3x;vOK0P~+o;CUtYxFSK3p*I_7Cxmo9<5c6){S!~4B<-'
    '9GQj_iKkQ%%JrOVTFw;@+j!VeKdrqd!4YMO&b7sfhV1kQ>jNt<ey{&w>FuJZHR655QUe`x@yl}k|w2<zAbX_p~tG>szN_`m^{ur`'
    'JgPUoToklVy*h00d@|Xs5GZ<KP1e51SvFp?Ypj4GuayEFqMqlh;f47kmmG#Th=d+*w%v$XZ1G#WB7-'
    'n6LI^t}hTi~cYst2R}tfEP|+hoO0tk{$Jw`@*8L*xvl7AJ)5h8etRTC6Gx6q8h7A7t%Z8|%;;Qq|)~$88?#V#*@Q9$<k^;}_$E{O'
    'ODxxn9{!f&~UT!wE5<kvVg)@HB>J$*v}IHO`?1B>1~e@e4_I0`;P5a|Cuc6pY>L+tcSS8=L;S#}Ab3S))I*MvsV26QRo$W*xZH0='
    'E-L6K5kf{AGgQG)@}7^Y*VY;&wAW-'
    'L$%`l7j^eblvlf(75V>9faN>+oDv0cBz}97V)C9W871DfaPX3dL4!(SED~7^`zTjBL)ySee~1FTNLc_!vt-Me%(u7Nj~n?ZAsdDv'
    '{ShQ#b|Q+s;0?VPlQ2W%&?8uc}{<yet+b(XL;P7pU+PEQ>!!`9#<z4hlnFshhYt-367gv9=3hoH?f`pU1geCog@y!-'
    'q`iFX2=6g?Qew=^+wGGTdA@6aU0UorMSh60Xi8aE<jX5ZqaLq$mUN~YuV+Nr1NW7!!_5*RHxUZ$hYdP>5OV)HF<-'
    '3tDKT3;x57rrBSIO3Ti<S1#9%-hM{5}X#Nh#2A%ZRcO3Tlqdifo@6S5@nRR-'
    '^kOH+wQ#5fcB2RXmRtcEe{Vci~Lvow>f9BG(U~R}1bVj3&#BFaBvEjgVqfR3PLpVs`dGb7}A%SLYqw+Qi%khy`%Ma`w8X=cx*QvC'
    'K?O!5jF($lEFZ5+^pboqerL2DV0hE7dh9M1-'
    '<z6mSquX|bYpMOvCE0{peqFbF9{f=cxz`Q1fBO;^+ptp3^8AVAc^LhIsJERfhtOG=l%yAnij<;Z6T;yI2G>N24vflYdeVV|U`!2T'
    '+NDSRb|XP6h5pQgrelH|QVEB)A^bKv?T7m4YA!{Nl)X}rs!UyJn<Qu`cq)>vtY$+F^oSX*28h1%aT4v~n5B<G(GbaIs|cNysVXhW'
    '%G_O=2K6K|U($CN!hiYl_2KJwmgi3`&m$TN(-'
    '{qNE8;m65HvpcrZn2{D#GRnItt386>18$@sOdRkwAm)Q4W*4vD{F9T#_%P*>l7UmXjZHG?3UVU#ig`QG<-'
    'fAxr@g0|gzkGb&TDTrcUlM7I3(mDjJsky8}aDKnA{<d4!ujkeeOXb3Kf$5=Tptn-'
    'b_lE<ee>V6DyT>Xw<RyKS5-QGWb`h1q?&n(fyOVi}>QOq30`oiax*PCX=^wk&4;R!10HdJ%ls@S(PvTEl(N-)u&<<)e90-a*$Gp-'
    'GcJrA*EgVZ-(=q2YlF6PjE6s?UUFjI1j7N)Q&4c5O+R^gD-'
    '3+aUC+w+rl3ks6Wp=TZ~UHHHnq|rKxitk@+j9I24Zyr#}wTwl}V_DKj^mT~z>jzBWr%%67lj~WeKeI^3L!N$5hE{>8#~DdW*S1dl'
    'cJPE7*1F&byDf-3SIse(tY<5x#iOaN#2NsU-'
    'oTyIp=V1%R~c)G-X`)?O>mVdl}yXj{Gmv69`(TXcppB)Kw%VF(K>GYR-}WtKSQkoJTLb6%k?6<ofifX-qGQpS8!sOMhX+U>=#8SO'
    '1bGvA<%S$s(rOcmv<A9){oPt<vfS})Dk^3(1h@Woi@kum8+y)Adx~jXZ}OnwaTM*8)xpN`vkL^1mXp82@wBYF!O4T&!NSbUuwnpY'
    'KKjLB&eUfxMSq9bN8hCg_qVSbIAl&)lZV7io&H7?(q7=*Yqv3AbXfM|E={Rkv*bnzNFO`Q!AX3BrHWE2C`z~8YDo;ITh?uIKU6{c'
    'G{?AeziuaJs$h_PrrR4IqUu7`QZQ5Lam3<>>Dc(W+4dVN7i<jJ>+J9FKPOQ9%`K@tuM)CU$O8)EnoIL7Z)qekcj4wAABa=EdNL`s'
    'PTYIhJ%-'
    'N?X+Ot%Yue!rz%PulW9N+2rLw5P0^&_>?b`UnycoCVZc8DI}vPa1@eO?v7WM=eVb4Th<3HA<pG;?<u2M8j*(R4uj}2c)kgMp<cWC'
    '9$L+(z$L)Ff?fLPn(w|tR{n4dqo+bcs*7|kF_%QDzxz-iS8UfJ_7h(`8?T9<cc?&NxY3-2tr`a=7gFoF30+h(PeH6N$@fJ-JMu<G'
    'NdVYz7nwF{eTpvC<Y(ezCt_j`<TaQS5=S{PDaeU8O#YXHF$IVW@zhfsq4k9(%lm;c%Xf@Wr5M#ZVbdy(#Zybz{cKj+;SfPH;=Jb`'
    'i{O$Q8|GLg1{h392bZUaiL{R2PEWtcu+`hqBVmV^4+o!4x^`vJPie~a&^W0OF9gUV*Z{y`}klo*ke505I-'
    'C=&T7jc!@s`|ouxvU;RlZ%m(Qf`{&6?rm+r%yE|w|tIB#agT{{Acd^yzDe(7^o5Q20uHjM+}0u9??nhm7zBY=OuN_?)1I7X69o36'
    'RR324^^)NP#+(eOlhWHdG&ueDJDO+P7j0MR3!6&FH<FqXq!ACQANAVQ5|YVNYK(w7V1p3FbxUnDf>UZvu(X$RF{mr@-'
    '^>+gQszEBN5pCW_+-K6r<%3r+Z%R#_!W+F?)N;(x!mx#oXJM<hM|c2BTlsMsKP>6A^G|@_U~zH+&kaMx7TN)nqvXxs~>d{gxD-VJ'
    'W|U68*3}nU?wf>sg>bvp^3`j&Xi)Ggbhaz(q5<)3jAtn`;;*LD8E<+&g(4S~+Y+79rW6`OfW_r>Bn`cP3un5~R}h0;3NemfVPnYf'
    '~{0pwnVLhxl%gbQh^vK&lLut){T`1;%H{G<GxM+UdjIJH5cOkr|l~xII@?sQr8am^!3Qve5*v1SIj-'
    '2+`6<k0IoBZ`n_e%M&ovXF@S1gE7uB{fT9IbZw&F(HDuoUikDQyYIoGNWf;MG&FnBgFTbsG7tEI(z)gx+7nhM7>srEG7q;_Cs~{l'
    '<mr)}W?urEKDkNb63xRv*yXS48!C>^@2<#VHk}}hwoUNTC$wC5e2@8T`8wy&;^pIYF6_Ojbm7-'
    '%5C=!DULqC$sPZoaELwv~g;FQTmtxQbUtjV0_x$krkLkl78~=0`=}#=uV|(Nwk&;Q5+Mq%0m_4z>vl$H_PFz9vVdF$UL(3ls(wde'
    '8TMysR0*`NkRk|HZpOa{hal(>6j1Q6uC8OCGBIR+dgJomJt4<FP^R$h?cp{=Ow4$Z4f=%_V?blv9=sU|dfv6_$RqjN=MZxE;hK)~'
    'eAhxI1qP$dE3A7VicPG&~g}^UqwDUci(?{7QU(a#$=T_*^$!S=J*}MWip`M4j4Wm1-c+5;#@~5?*Hh9f-'
    '<8F$uv}3`7RjO?n=1@3@HaA>CsY1%9xnvgDE>*$7<!rl%Y^hqzHp)i?mcXUhk2-^2lM6f>RVS;jH-'
    '4bJ#JlLe*oIGpj4AuE$*l^hp`R4V`kn+@X;W=PxflV$zNFJP_kB&yj3(9u>N`sG{qzxx6mOH~=MyLWxm9{}bLz<$0-'
    'fRQo|G3i3;3mnP*nG8gW{gLSae^2<V=O>V+)*=`=vI75u<{>6}-'
    '`e)w|bu=<{Z<d!g*?bY@|RGI>JMe+uee#AX>2+`0vUu=d{m{jxEQ@VeYrPo=GaMTR90TAqZ+uQzF9(1i*%UK`f(T|^OAp@CLCAH9'
    '~nOiv=dCM5E`zT8h=OlCXh(VtwRM>i+fqrjldYABX=<W0H5sjOgN0$?fo9v&WuC}O&zxg+9Wrc`;+^Ijv6^~PD00^x;^NCWq4Z%C'
    'ub1jSIn7)6ybt84DU2{+cVs==dSS)+Bw-GB4|aiy0~lYmvaEc0+{y{u&<|CRl5z4=8_P9jKC3scv59i~h+s;c$`6(X%We+Sih`!G'
    'Fz(kSY~)0ZzNl>hUp)Pe8_ePZl{`IO)@iD>Sip)jD}c8rt6(qS&sw4)Z)(1r}m0W)TEf@aM_U2cvCQqwo+k*!zCqJEA>*LkA%Ldr'
    'iddd6km-py<}N_mpIB&sj>w24pz5T^7($OoT~y!JuFfd=bBm1R1q_Unui)GP%|AiIMxQ#X3qNBTDEKB3ZHvA#a}<99Gj;ExjJHhu'
    'obQy&FKJt2Pjg~~J}^Xt>|^x<2X{&RUY{3rj{Cjb9kp5IxWhmt0FLQqE<DzTV3Na5&My8=FLP@;?q0%j!Cs9<ci;^j=R7OfRk31B'
    'LvcD&OY@>aEMEK)%9m6x|HD|u9|sf0=3ND_%SQgA`C4Ut!$L##cR%GSzpxb{#!NMk;i0k5p@t?gD%QbT6V4(4vpl-tUaEgFZrLFu'
    '8QfuH}(R|j3$rR#fo=%>do@4ikr?tT0>@BFLviC5Hc*60tlQ1*x;7XD5HTV$}&5+Tjm;P}CdrcSe--'
    '{_mi1$HUN{nb&_$yK*LI@r|B`G(Jqde0o;23eSL&`H!ubhsc(+Tr%G8M$bOubI+O{>Cf@*L`!lDC_YhX$JH*Hy4|;s9;lE0bjxJq'
    'n@cpT}Y{LTJ|Mu0Y;&B{S>5WinKL?*lgj~aVJZ1-9A1od<wtS==A*fuTP);%@hATE!+9L{}uhSEk~FrN)RZ^eBo~xkBk*v(`-'
    's0YcNha6W(MqHzgi_nI=6q{8<$<WRqqtnDY%cZlFb#C;c;P&txqzVETHqvjdM>x$2a4&+Yw^FcpDA{UA|<5jAPtBuz?QX#J)T5sl'
    'BDMSFwhL`@q%RuX^`Z8esi$6kLEZ>a`w_Ld_Z+;p$-_7g>|`MYZKdHeOZ`NQM#Z#w8%op-BF>}-'
    'x`BrG2Ij$rA$I1IvKQ=7&*4UJ@)aM+z8jW8zy&O`Jh={f>MP&MzlvOFD!7Di61E@D<*JgcLm`Qj~z;X!y(BxvyB*=c_RA|&m@5F5'
    'i@Tm4Q=@(>TbHqOpxy0yrlq1t9$mXhX8#jm_UTC=8)nw|+1^v(jk-'
    'sGK8vPLs#&m)hj|5KgwALA$B)69E+7UvzFb<mzeIlU}3Ny{T#J8U3wks3OqQ>K!bH2Z=>iErnGf{9ldBNOvdf$6RH`Gy-AAiNSiV'
    '8>907<{Syz4?~jda7nk+CTDT;O&!U=-Q&3S{-'
    'w?s7zVX6yim`)W)zXUvG#A^?nF?tCm!*U*@<DnwT?{C|7D+t2%Xi5z5e94fORqOZ87S&$B>(N`W5Eok)}FjGLo;bz+fLtrd6uy12'
    '{l%$pp_H(i=$nEBg;A30e5j?V+{JllPH+&*D*s7^|1HzcfN&A>FVGt;9QvZZRIRsC)lSAgnHl-'
    '3h3c+u=x&xm5G(sgxLg49T`i{)RZlcd74m221P?dP3I<|$OFOO_Wj7ye9*jhxCXg7~RKDC}F?=kt4tb^3gk=UvM4X!e9mPZC4FtS'
    'sWtL6OfB#7XM)#z4n{4pj(CGJ-d`H;vjQXttmWX)g_bm~JJBL{2N+P11ZHFFTuz9!$F8`9$ks%X-bGq^p<-'
    't^hxS`@7a8t;ruL60@87?UH2jW(c1QeF%#@4V$Qa@l@qfVy1menGs6wA%2JpR+vm_GR>yd>(Kx926~q09ZR$x-'
    '8$PIuxPLBJuM44bkLOyZNl4|X-'
    '8Yv!xWilSL7~bj`9R)xA^N|UQ!XyWBYs~*MYr6*AaT0K6jokDOX(^y9ip)av?52a*~}20Xik<6~iC+%NXrIh;$;q9+4uZ+d&ib2w'
    'EOLbJPJcIR%(RtK(jgCgmM9vONb|DGxjCR==LcJC%}a8u}YMC~PO-'
    'r1j}6&%2c8(UG&_jK`iqQs<`bd{EZjkXMY8BLtDAow3WA`0i=p(cOjwO9T$df};+Cdz_w+%hL+dk!}b>hDa|Cu(G=36pfTkh+y1I'
    'I^HH}NWJQk6l;96&uWSTZ~aTgLycRync1BIBZlJ`^$BOG384s+LKChKM$|DMFjE*`;%`FX%0+AHops1>A3)Cny<>sq!`M3H#w6qP'
    'd8=69Hi(tMddPF<lT6HeaST;gN3M3##-2R~>yecR&u}5xx??s|?Lvl;Lz$F)$Q24_z3wF3sSlCuuC>@;R}5bUuUC$h5|o-'
    'I;+IDAI=>y^0X~BtrEjTm5Wd`&xkRQh^mP&Gjg%nb?a--+4R`>xs5=)tBNi#|H}}s^p9JEG$T=(YE){x2t_R250YEp?-'
    'xor{z~Lcva2z7^nA^_Gt4?AQn9sss*c+#ls;Z{4Y%2-0^#-}#LIZvm5aJP*W5-'
    'Vo&w4wdL14P$!4~1kRw?3fbBJ}Df&%%}SzN|+`)x-'
    'u^}RQpPS5eqOfsr5f|J`z?^XH1N0;EtB4mJx@uBYcgFI$tY8g&OeEvWOJxlbiC7O=*B-'
    '3KkG&d{kq&!RwhWD^TX>YKSH*j$HO6$l?(`fF=#JjSJL?y54c;X(v@|_mUy@rZxHk1_SqgKOtgBGf8U<Q2jmb~W4rf9P*@z8g2^6'
    'Zi(%r;Uw`OUp}JRnM<Bl-ayS(VzkvR6ZLOz`gA@SE^x<}{Fu!Sz>`3*Gufz#uy6*u$J#-'
    '`GTVp7_W01exvt(dTr;SLWZy1o*y|mVuMyeKCA)nyI}R&}ODED;LdWfz33|Dw!rX70QYZ+n~6=vBdkJvchOKD>PqibAm@eOiU1to'
    'o-ATk&iyiCMvjlQ%$Ygx}hLRn|fVFuZE2Zi&LaBQF_wnf>1h^i+Kq@kAmi_$#p1uq|LTr7BUtwDf~VV9;CzzhBtT6vp(-'
    'vpNBs8NREjy@(8JYgBG>byjrd~t1P-5a^38=;T<{>+_bGUwVmlOtq@A)8*F6>Ad=+-'
    'AoX4Hgsu`eB0PDG#Xyau(YGnPcPI5B;FW`hAw|1J`J;V=HojPlfkBxC4pc<LG`lgvl6wux6sme%Plh{aKav&7^>Ub;0s6?H@BLk?'
    'uFvU>&GVP->G_w(vpDZkoJS1Mu|;(>E0S!QS!&R}^9jVCX&GV9?;HN$N-8qmwp4116a=+=+AhB0Sd-n_-'
    '+RMwbjR_Y)5V%(0)xH^zyzMj4cMs$B+&m-'
    'R8H38sf67Vw2{$v2YKqsUdnxhjt+X**2o7bay`ZIwQuHiH_W>gK=O3Tw|gPT28hwGHIw4&r4weVZ=XKT^1NSp9=bS;3BwS^xdjae'
    'lw_FnJK?s;EW`~qa=UMIz_nCNM*<3OdFmlLp{QRt+jr@fK;E-'
    'vfaasqC94X=`|Lr<n<u5&Yt$q@$vhlUp}mNu*~%>QyumC^L#RFbm(=;z5>^8j13)V(fD{@+9;lM>G{%idr&8z9YV>TzJim=bze#J'
    '}?8i>Ua^#Y}se8Vg{+J#g&+5F#UUcZ+KrrYyZ|dDUv**`=kkGAJWBtIZVM*Oo@LFb>C@a%nCB$yQ=%E?$3Lls5hE;fk<yC!hnL0I'
    'SWM0+UOG1-'
    'UjuP>TMF(ZQ9y}D8v<tZyvdTEdTWts~KkMasWO+BC0%5MzWG9&$UfTHi)M7~Hniv(5ZX#7oKtBhTv&at9dCdE0^BvI(x4P$9p7$%'
    'y;pqC#M#TLcGdr`oK;$`f;uwy+m^)H8lVdxp2A<Ne5*VWWCTUFiiR!ro9q-t-fr?0hGXf$hb}vB^)nl2dQ3yzyT|0z9gel(U&QMg'
    'whB6YQa053@RPXTX<IXvARA|JHalz>>2YyALiaAWC?Q~jJ3a{C1jHJdbXs=V0D2*{R$k1!v+B;c^-'
    'krGoeQNUvQW~%VWAcN6+;#|!D2qHVkqHBfDOr=9IiLpEu@-F@hv#<Zb!W%VsE?0pQxBR!r!kWa%&6-'
    'mb<z;ETGnHkepYlB>1?1ielT@~-FF}YEZKHR_9MP7UW~!hg`wwg;O+b(t@k3NA-*moTHvS-RUuMj@(p1M*~Sjl$EC`<yF9!%x6ZR'
    'V?^d1T(bav~ctO!=tZ84sjOI)VxFF)xDy`^<1tEr(6x!0krvtkm76X;LW)XZ^y5p;RGEt$`c;2vix}1R>=EvE%^yW6uxJH1iX0yd'
    '^r>K&fP$TJB?@&I${_V@y$;Z*j(ZV)*P9soHqBP}HBW%e%Dw_e~rKpW`aD(aw*RIj$ACgF~2#KBRt)273hsRG(k0&YQKIM4`DYX-'
    '9k!fqqD#k=?%jVJRr-USaBwb0nPm+@pWxNN{iPV@q3cCC}HS_UWBpF^onn4cb%2uM#eAhLXiymmCxBp-'
    '<ntnWpc(TF(tTRbw*>)02hVdI`K8zeG$xiZgAK{>C=cF-'
    '3K$E^B9`H+~C`V$`;Ma!kBt|UBf!0B<&2Mj>XMx_aKo4mlyw=!;kd?$!+wExvhVS-FGbIEWs`5TV&ftxQ$i%Boj>6Oz*mhHg+YJP'
    '}3lZw*U<88c<LrefhkP@;N&|z&y<JCTIBr>VNMBFSjRHShAl1c7CBe|X>XrN=eODkiX!M{$Ut4>9Z38rlNZN?AAB|>G!pY`uDt(T'
    '?WVuj`r<~uB;2E*_=E?Kvj}uY42clGu08a+XG&j13;0!kJs|oHs3O6X9gwP9%ClnoAG<ljgNOlA&HAN0nztQ&Q8)=EXq7e0H%$P-'
    '0Mg+sb0M#rp>=y>n9e_^7K>jae;$*?Px=Y<C`ZO`I4ljwGf}r5|P?WVHlaFUWxIW{W)%KA}rxDYrD?@SQq-'
    '9_Inmf57O5aUI&gJdLqO&&dQ=8o(6NEc7hxE<>k7df5*PxB#pg!-tNr{|sF#TMZ@+OcVE|-'
    ')r2@C$PX_NVO>}vyo$O4mZ$=_A!o(!OD(=@Us7;t)xJDj@s4D#QzU?jhs=ucK~WI&gh4F3qD>9nww=&9~g#%PMrW!54|N}fddb>-'
    'R1W%2_tJ-cRwY^my@XQ|e1cw^T*iOBb>%_A&npY=paI4n_=L?879kr8a;o<hXFw#NvJMSja=pY%9jBT2yZ>q59!TH5uvZ}J@To@X'
    'yX3MyDu<Y~|ov(3>XdgnHuLjt53oe2o;LUcWMa2{Y&<614}t|KSLOtj#^bz6gPUUmzvgmK7FqrVq3yc%V1{2GlB;ObC%b#~OUfI&'
    '3{gg@?^`{r4lcdO1r4hX^U1kUWKEZwX#&BQAU`VQk*LHV@FuH5N4yymXZ7Fq5&U)mL6+8uM~6piS31RaAd#Oz^p=6qxFr+K0jK<A'
    'ZJHN+2%{>f;_rM)$3CUkS^f%Ud~k!c!kI2g%o28h2S_j2YAzY6s8t|?Y|h@&h(gDN=_ygZ3IW%B1x9L@JNZ)SOZ40oHeH2?Zts7p'
    's!l8HlL?aYNxJQLQ*mm_omg`f5geJ1&`B0t-daZqOD><sASe8g!USDPEJI@%zi%B0p(Ax0C+JGJl0h-'
    'a1yW}I?H^`87gxlE`Glx{9!PQ4qx8Hra0a@J<9F}A}HQ0_w7)@ejyVO#d@@@zoH9qJM`dZ*%7>a?$?Y0Fw3jknck@y(s{tj@bt=O'
    'F<^p@aB0fpOVHY=9#Yka#9p!{N<u_$lE?KMz_R?Q`9FC`ya~0}>?KXPIu8E6GgCI(2A>q-'
    '$KZbSQhkNE=&{$>HPND5lhCiLgY~NR7Nr%1Fl$t>tp}l8n?CU5^IYN889^IHTsudc3!F8n~c2b26XS3?=rTqVc_V0R8N%L{s6XJi'
    'fVeK7S?CYdy>JF6DU?Hd8^13WY}E!AKC|z7px7J>g0TP42#IAsBl@@tolzGugGik?g$Wb5CGO#}B(EH9>V#%+`iUB61`8ST^Q0yp'
    '&Bo<Ru5Pte310{X^KEfXbs{xm`t4%~hbOF^yzR_8=ugV+3;!Mt%X*YA`Q%M86!fjy1gFs!o}Xen5`^DQHmPTQjB~Xr5<*-'
    'mgFpDIoN)731S^2H9peFA|TS!f&%j!OcYBwMSrFSmRClAnh1!96FE5i)3k!DIo4I25SL>n?@H|#6V2Fx!K+(DKjPX!PnF&$81gIK'
    ';CqUDq`&r`6gRmdf|YmSE@$GMX(pEcT%&I1x>RFwIcC4&=a8`$vOMAp=*zh^Mj<7DrHF;=$qT;=g-'
    'sf?zhk6%bvT@eM<BQR$BNMtgoAHHQZRXM%6C+QJsiISgDg~g-'
    'WcXNa7Exjp0cA&01TzO~=<F4Q8_;2JATcba)1b0N+LICVkXPk3onwH)hlbM3BMRD2yM%&$E-U!6r5|FC~g7SwA`v(NS-'
    '@!R)x+^N?QNWAN^)F8NyS7PqpCdtIwhEe{AVs9aCR)Zqtu=vk$AuF^w7$T%!J|BmZEtovZlksP&gUbe8_00!m#*OZ%Yh8PbVN*cG'
    '!`kmBS3_!OV0F$@&##qHMZllsYswDPC9kC%=5gMXi&0`Krj=nT3G`SJZ^t<H7=`iwQQP;(>ooz|6r#VO-JjIyIx9xRf)F?UPztL|'
    '-YNx_dz8t7(nlCFFe`&nbwQudD1SCEFf-l%vp7$uvBZO(&wy~#;0(b&JE&9Jp2Lcv_0NNQ62-'
    '4F{7})eAAJd*l>=^T=rU!~>J$~omG}A$izGn3Faw$ko#}%rt2Dr<6Yh)Ey{W-&&#xr{p*@(12VS3{|a{Wg-XVy+cgGD!ft^<vHIW'
    'I+~%qYmz!&^8&;+*N;{E}+j0htt~pg<DkVw~;XPW3zs^sWVZ1T(GstVIW2HNBi*yl07uN8ko(KC$17lbj|j!q5>j*wF~FQ=U1|lQ'
    'i4!eBW__c9(=>{Xs?*ZP^Z%U3J2~Qvs7=i!NB8e9&TEG2czq1@(_doE=;oGhZQ4es^Oe#dv1|4s~iUk}IOO!evL~eNZaG1gtxwS`'
    'uZU_FHOQH79-9znWJIbkdr8-F~Is_-vl_`BUoikh2sbaI)iUN7&2{pz<4GNaV<bD{KU`Vnz!%gi3BHd&Aq$!m*m)1p<G=h@myLo!'
    '6YU)k%{pL1m{eX3;14Q}Q&tfhWnDY&(OYoskK~1lpy@eQU(*uPA8l!yk+Xe)IuXC8EJY8RLxy^E6>$)Y!Y)VbyW+i}2`c70S=xB>'
    '?Es5qIq0{JbM_|NQjjJiXtiJdbct>7E4%9AoFo5uW3azHfxcNbba?4qg(aHm-'
    '<{;&?s`(_El1Gw4yUHxlGH?XVk3GiIAH<ABl_%{Vd$p^J4IAZnB~632M8>p{eq3u3N}i@t+~=g^lWDPn2Bk49CPT9NX<+@wMw2PQ'
    'RyFtk${ItKb$l+?9iRUA^2;?AUbh;qB`2OjvdMDJLl^+*f{A!y>WI`jT^I&F{#Oa2ztpVZbwC@e%|*+uJuHyzoBh~E2^K!ho0t-'
    '@{`lJr8Nr|JA|o=jl%j)TT)GYRU(U@0b#lMJh);qRUKFHIQW6djU`efM;5wOUFx<;XHr91Ji}{VJ#m-'
    'E5Pi*|S1Ro|E`fbYaJ6DvgWMU@)hX_26&ftx(gaZGN6Uzdx(<9vAp}go6?f0}BK66M>u39jX+Anx)|pPZRd?^HSFa>(8kz5<=R9m'
    'k1k9M~0kQxb;RRmsuI&nUaoOw1GX9r*ZnBsyJ(^+h7CID`5<GZq7hef;%&TcgtRjFfdU@)T`FWGrGo}QGcyKtI1ppsB%E`ch(kE+'
    'NuH$<BWM0Z1Vh>+{?1EC+2{xq4=BI=UJcktIxhU+TZDa8;)~;ODS(0+DYIVv0R{HSMv)dZ03QVnswP%0H(reb6qRv&M;#Ftvpr|!'
    'zpI0)puKlu{0(raHEmJ+>O93buw;!<U19@k&>w=hy`o~dBn`J>eKa(<bp3juV_312mlX6+a*<R%$}pQt&Vum{Y$|xL@C6aNx{6ZZ'
    'fibmi4T%$eslBueL4+7?o*maoBKRuGL208ZQ#tWICz6>5(rPIHaq&lwQ(lSuyLVZ%p3B6jvXj^58wFZM!u2e+x+0Zi&0RHJg=+na'
    'IP)k4blx)rz5WYrpfe%8mN3@<Sddt-LYAv%JqaK)@f)wtr+rBs5#m1J>^Sr0TGa#oK+f|C>y+x96?=tNMuHeL?XW<KEMyO&a*o2R'
    'Gsb7V&t$#tY$@xNo+BMA<A;y815E=j0`c@m(?sb)~9~9;c+x4YqO)VGIe&#jeH{|K;{K1Ru8{KVR6Gc6bE%;J8j(Kh1oe(Y8BE3='
    '~#@&jwlUDeMggCqP6L~Iv>kP5-Bw-&XBM+(%p05{c7M%*KSOM%bL#nYxM@iC-'
    'q3+UHXlcH+RlIP`Q8n_4B*O=aa;AkIjgc;Rsuj;)CUvTM!|{=s9ruB1wi6j^6z{ZF+72w)5<p4-'
    '4o?X&~yE<TLfhE;gnJX@R80yGa^G4+zOSiduGN6S?GwfvV_0$_5zZX2gS^RlZ9EF*Lq^>7c0DSg`=7%qV7r<XUOECS^!hmSHa#>d'
    'k4?^Oj#Mu&TzY<_kr>Q#d#3o!oUl&_T~Cy>pf3qZJ8K$Piw}v_*vP+==LI>qOQo8aPT+YEdBqVbx^`pk_@Qiw6)s8JvPRH@ud#--'
    'Kc$d#^F%wK1tf(A;ah1drDIgHeG-4dR@`D2*}H@IxeM7EKm7V!jxCj*-h@D>lTd3}LzelP=5~_*I-'
    'O)P7dI8HDLuk6+ZNMj;Hk^^z6GFPna#lYZR({<xf~_xlv+AyI?}T!4F;2z}R8E~6Dj_6A`IFIvPM1A=#9ak62tW*FREh>c~hf@-'
    '(l3_I!!=1{F>^57*RrW%dl;nRd76OVu<jdN$bZB(t(aHVy2-'
    'im;_95;*pwAT~7HuS#Nn%F7{DVl?Ye`wK6sR^d32cjJJBva_b5LoY9)y93KAs0{lWBs8vdY0(@O0+v-'
    'iQohV0K}F)!>@$FB(6lcW;B}<4t0|rBAaL<XcG;zU~Gf;_ueU4Tdqzd|6HP-oT5>I`d~~^R#&7NlUutvgH15!^u<#f+-'
    'b^SyVdFjJP620PCyrFTIE`z!6z|~+i+Le^4X8rs1K3jWI3ywa|qCESz{b|p<3^h2p@4R>kWU0pZ5bjlzh$iXL;VGJdaQ&qB-'
    '#8hA_Ww9+Z$6H?TgzJiFPuk^aU;2V?mO%YG%$gPw;g17~?g*R{PB$mI)fxX@_yL9dL%Oj%`@=D1l<N-'
    '*r6Mtz&2Mf)zMAL~1sa%hIG@toH;K3tYHK^{yuZlsvXQ0{Hb&_a464~*SJpGT7}O~9eBNsNx?BS~YH5gX1TKh#3c3cXi__D5&<Og'
    'Nm!AsF=Fof^80JEkDS9_%fVG274*b;ReEeRvx-'
    'KEXu2L#^MtO&_{iZqV$Kg=nTB^P*W>+Q|dgS4G2G=Fs^Xvtlh9<tF+nDu2&fkB-_ecFwrQ#9Z&3gU&SJf(QSPb*o&=8GHBokR-'
    '$B(-'
    '4g6Rd?LQ7lNjshHjd#q_SD(2lPyDY@ko?9?!S^9zaunc!BT9irIL;J4hc?9EM8mz5|CYZoZ_#t&>7won0~focnb)DUeYVR|XuDk9'
    '(&_Zhl3BS=9;~M<o5yR3ea{<n2)>T75m0%w1@GI2^nAv_aTpT2z5dM|?TJtArm-'
    'f^pqpmDig)cy&~J^iDANaBk!$^C7@KAwqfiH0;P=54lWzu=(D;#Gkc!r`kM>fd$MY$e`n%3D<Z5N8fnGIkU4At>B<uH6e(!n`TJZ'
    'BlD7TfiIpCxiYo+n4Apq!=}<IH=@4@P7dzOEH<5dxmKk+?Qb-cpb39(w;A=q%@_&~ewczz6`tcaw>lp3+(lQE%UpE~4F+FV!n`|j'
    'y2|D0PW>f1$%kGEotTyT6o-3$>u*)bJ-z>cS=|}4d7tV$)F9Ehz&<C`!g;2{G@889=Z1~ct;uy4_ZsAy_=;?5;W4O1CeI9-'
    '5(w#y+dI`lqh^KnwN^2rF`{=PWx~?lU@hrW*C@Sc^zh=NQgTd^uHVWw1c=gAjS&Z=#_Ww==8|eo-'
    '|Xu3ve*2E)kh3TV`PQL;Pnzn{Z-'
    '7H>HJeQ7n|CmLuq+?=RE84e)V~n0$cQ|+52(toZZ?5z!Q<&H1#0#eJGFTeoL5oLLT7)TCw;Bw`b~vBHGOP*bPjxSpaf#g{Tr;<D4'
    ';jC6=aYr?B7FU8ETHYLSUFbr-'
    'I(ZcG3JO5|vEFE+Gc5yGDCJ!sS}RA&8X(8r)dh@)#!Amz_ws&!HK9FQcK$~Dn;Da)#_!&@&%PtV&gPbV$;E~VKW%HJ~%v-'
    'llO5lY?f+7>~xTg8CL<<jX5ttJk%96+&9CK&;waUUgG2teJ?#_9G@U7qD<hB++#GxlupqrppOk!{z@a+kI&1Z3=CBxr?+d<hS`dg'
    'X;A{cC!G{?S-NQOz23W4%D7c?Jj%3yMZsLW#$JOx84pA@(eKZ<VxMex!At)p@7t<mo$tlZeS&+i+6Cfes?kIt^-#3(yjYMm&mGD-'
    'Bd5A@3N8&`n8zHL3&kN5d+ALtG38SO&6Y?=p^!d>KL<q|ZE0uxPy}PuixY;9MV#^>k;+VPy<0FY=A*x9Av?Uu~L$L4*oaXvvy{ju'
    'C-qn6ZT|MV@h0LkP2qTP<$-XsFQqzy_2ww{K-'
    'FA@TV1`Rj+@r%z`<$6fFw%I1i?#6E(~eIYT%Lk;8Q>ZN?bs9{*wRTdrYU>W~Uz$L+;3AhR7e7AB{D(MD2B=UzPZUpEfD;b8|V1C;'
    'e0k6`JrAz4=7Gx%tY8qk=#FCLwf>I;${(^V1GbO2=^xa+vfH_qXo<3s^4l0avOs4i5<BS*sycrEbq>!d+*n`PhHfiSVc;{K8_pZ@'
    '&gn8<aj2l>ArxD=D<4{P3c*9prJ_$9Vd<o$~{V_H>q|kPOqCB>%`E1;oZXDjFu`BM)&X~&PsVV?@t&p4yl`S`sUmQZ=2rkk$gwh&'
    'ii>k2KJy*rY^^qUVGG@>5jcz>rbS_*7@3NvIMRnLPxX^QWsv%xd`Y~#@SUfAZ^yQGob?sZX_vd#{E7kb<v=O;mi5`KU3&=aPq%Gk'
    'ruNwnYyJdwL-{TO*S-'
    'zu>t{d?&qrQbuN3i~EMVJ;e9_&`jjl&Ued2Bj^4oib}o3um&t~Dkx&^7#MK}3guD2vFb>9D;lW}2<*4t%55t>&ALh~`dl^=y6anQ'
    '!T=Za$VCRZr25W^e_euk-'
    'B(y6S5*<)R8ODNdFn@^+W7vr6w?rAItFTp5Oe1JX+KX?XM}{o0ZGLbRKJY33cj19CRua$+LV!W+TLcA<5_1jT;wMxab<T8zh^F?2'
    '<AQdviEKk05X>c;RIMaTMl@=c9yAf_Km>u`D30#vj3B1P#%1<zBiTepG{UUD@nW+9pe!r)NFPk~kq;TE!w+h=hI6}HlLf)_u4t5#'
    'E{w~CC<BE5H!c84-K!(RqhByO53JrnYBA)I(tccEz)eC6G&%0!w+hHbC&f%GKW9N}Fz>~5-ar-JqIa#5GL89|xsQsWSzM%e%k?w|'
    'TB_8NPdC~s_6l9kLtC5xHLd~vFcC>hT}e8?tVZCyiKYn0#I;N{B5;uIONDTq+Ikp<19hD=F+Jum~H);GTPpPzpF^6p`oo}Y+FI7i'
    'a^6zLIU-zql(1s%vBPKe;UnGI<g37eT9FHd9yZk*nix$fk1adYYs9_N`(%HfmDq#K>IHFKSnTA79Ea5O*J%R*5}y0Q6jH3Xj0{6@'
    '8GlAc)W+c0Y|(Mzx>8RBtmr9kh@!BwfJV7~IYP!~HxXxfLuBwOH}X<YoiC6_jVP-&ejYg9r$yea^OH^291o!-'
    'Ar`$OArsL1oOhVG~$_~6byjW~!o-'
    'yxF+04K$GOe?3SVP}m_3lYae(O`jxms5L87iq(UUQv?WGMjE46QMRXGTt?@)#wSll$V~GG%S<(Rqzs09t3)jD>r@ygX@b=pG`WMH'
    'e;mFgj?ufFd{PrWIdVly#|gsqUAc7d3I54!7<$N+V8BaJ!n_*4>i+udVk8|?^U9Q5I(pP3EC4yg`5+*2uX4S)H;d@ow3_|J8-'
    '`Tkc3{c<!<lea)iE)YNbovNI5JDjkKsu-at88*02tvl=NP3t?5jMZ=@&X8g-'
    'U0*@bZHD5t8Mt%jgYei0~TSxlU$`nWKKL_}vh4N9biMkZJ_6u~t3QRRnjA{^?SbsIanyc4E@rvJfCdKT&ZiuBN(iMu>&Jy^bWiyq'
    'BU9j!A}gLiEztW<2{6;geI0A*|eqU7~LZrWk&O~>91Y|_;^v+>Y_wMP~?^0ws3DM+8;<~2ruraQT(B{^~-'
    '|8yc4WACEbz6_;yW}bHgY?Y5lKG9;7BU6s_?l=o*%^-'
    '8s7rs;Rp|5im?NYJFx9f}7^>3x!ecALD`MjOlr2Ew85kv|o&%4N;zA>hOJ<)DvMo>2WiA)a#^RVwaVEe>3^<||fK}nYih))hkJ$7'
    'eGPKK7HtPnwWv)^3e<F?L0bJTr2M8Um*$;KhJP6hmLZ+;R#MgRIvuZQc6zC?(kVy7(2wAZJplYI(Z%9H8^Ea)!5@bXcl3_7Z|LIp'
    'CQsCENm`|<5f^sLakR_LMo4OdW+pp5*OM$`a7^`v&0byW;E;4P(AiI`(Z-7>E|xe601d0H0pYN^NcP*s@8Y-'
    '=Y@Q?~SYVz~}Xh|S$AyB4#OiJ5rW(rcgq9**d!G+l!fG#`QO^b#r8DYI`3P3RTpIT;wt?E+NHw-'
    'L8;5exd=5Nzg%mE~(dU8gmzudUYMZ|<OfKhtOKa;87@z5%Ic1Oz==jFjsmp%9mEssJIp!3Tgwgv~6bA7H*Xdo7>6WG>m{!{ZDE$G'
    'se-(Oh`)#pOh(X*3-'
    'ZcylymNiIq2S;#p+Nl2sVje&DAOxlnbrK|O#O!=_))WS~N8+CxKGCX5AW#MaR(uc!+m0K@J8ed$k%+&7UgD+xLnjh$$XKmi6Z(c3'
    'F{!b1GneH>yStZx&GRyj~7z4i;aJVxuuIo-ca$AbfY`h(4o}2TbUN-p#!>JVrYPDx-'
    '^_J6xn}_xSJe81cXxpf7nCJCIcRTY5iyV1CDK1A|;!Uyn=6o~MaJqFoP(A`r1spdU#--'
    'BKJcVA!wNtZnAul%$y4v7U_>!Yr!@T5Ny|Hid6FxqH;GflbkLo-WeSq#TbB<wESOx;QDksfEOjp^#k#>VWQrRo%31lPgUY+2T)MZ'
    '7QtnugZt8QpqnAL^kuJ`&wxw6AE7Dm9aD7<bo#)(n$w$7|#)6=CIB-'
    'i>b2dVTWXq(aws))uTzWus@@hz>6OyLwhh_8nED5MlM$h_&aXc;9XDA5!>zo))?yX5$+&%3?sbf?4A!?l?P3G{H6m@l!iD=WM^P<'
    'fn}z?ZsJCL0ZvPyEQ~Gu2r~Pe>gK>5d6_UD)QhKEp#c*D%63<=h2lsWZ`N7y~34LS+edo;0KFw2b%M&KC<CwtA&2y~#S3cLz8{W~'
    '}}pDxI1df_OeybY3NOwB~A^ViHD^<~tPRh1|K5D-'
    'BlgR^rGXkDvLs_xbUphu)<+kLJ#GK+mzx>k#?HEiv%z62u^aK8W4kICYNO?lpcF>*ffLs&48~*zMTd-'
    '2j!?lbQL<wU)xEoP&|Ujf*?`pbK53%(ynuK6PP?TtYfriEM5KbTXif&Zg#G%CjnhGj|5Gy#!_?Fd(zZo*GwvwM*3hpni@48F~}ns'
    ';Q$%^ARk^*9Ko~Z|<IFh2FD5b3QcvUf_LbV!#-;zyd|nAv}(sUCrxE1Y*J61~-SXOo%=U1-'
    'jyoGcbO_y1&5=rAb8|_F%<mzofHbWAl_EPnpm}!*GsbQwuDgUIkn=Vw<iQVt`hYMtbbEKy_D=ByY%URf$wBN(SQW%^tCwm93YfxB'
    '&Ei1t%c%M$Z+$V3O`6w$k!u=G`A(pKw+F<t)y744?Vva)j!AH%t(R+NBWo4y|s2%*_9xCtfJs6}=}=Cw>miwpUb23odxe3{+}HN5'
    '0iR^^~WYXqCDhw?SUgw4n`qJN_?eY#S!EywHOyb(XJG^hgA&a+9*GN_#yWQMmL)CeK!_W|e~PQdFHMsl_Upl>^e{emP2W)&(4ZRs'
    'LR>lZ+`0MNM6Ld;dHO^sg<@zy0lh0roE6TL'
)


def test_prior_public_scan_replay_and_near_term_counterexample(tmp_path):
    import base64,zlib,hashlib
    pages=json.loads(zlib.decompress(base64.b85decode(HISTORICAL_PROJECTION_B85)))
    assert [len(p) for p in pages]==[100,100,100]
    assert len({m['id'] for p in pages for m in p})==300
    assert sum('category' not in m for p in pages for m in p)==300
    source_asof=N.timestamp('2026-10-29T03:13:08.875576Z')
    calls=[]
    def transport(url,*args):
        calls.append(url);index=len(calls)-1
        return ('HTTP_2XX',json.dumps(pages[index]).encode()) if index<3 else ('TRANSPORT_UNAVAILABLE',None)
    root,_,m,_=execute(tmp_path,[],transport=transport,clock_ns=lambda:source_asof)
    assert len(calls)==4 and not m['tokens']
    assert m['coverage']['raw_rows']==m['coverage']['unique_ids']==300
    assert m['coverage']['time_counts']['IN_WINDOW']==0
    assert m['coverage']['time_counts']['EXPIRED']==2 and m['coverage']['time_counts']['FUTURE_OUTSIDE']==298
    assert m['coverage']['stop_reason']=='SOURCE_UNAVAILABLE'
    assert m['coverage']['filter_counts']['FILTER_MISMATCH']==300
    assert m['categories']==[{'category_key':'UNKNOWN','label':'UNKNOWN','market_count':300,'malformed_count':300}]
    assert m['summary']['assessment']=='EVIDENCE_INCOMPLETE'
    assert N.verify(root)['status']=='VERIFIED'
    test_missing_category_and_conservative_fee_bound_provenance(tmp_path)
