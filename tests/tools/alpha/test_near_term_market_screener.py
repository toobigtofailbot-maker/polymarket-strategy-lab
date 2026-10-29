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
    result = N.run(root, transport=transport or fake, clock_ns=lambda: NOW, **kwargs)
    manifest = json.loads((root / 'op-000001/manifest.json').read_bytes())
    return root, result, manifest, calls


def test_category_neutral_pagination_and_bounded_denominators(tmp_path):
    pages = [[market(i, ['Crypto', 'Sports', 'novel category'][i % 3]) for i in range(1, 101)],
             [market(101, 'Politics'), market(1, 'Sports')]]
    root, result, m, calls = execute(tmp_path, pages)
    assert result['status'] == 'COMPLETED'
    assert calls[:2] == [N.discovery_url(0), N.discovery_url(100)]
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
        N.discovery_url(1)
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
    assert N.public_read(N.discovery_url(0),15,9)==('OVERSIZE',None)
    assert N.public_read(N.discovery_url(0),15,10)==('HTTP_2XX',b'0123456789')
    assert calls[0][0].get_method()=='GET' and calls[0][1]==15
    with pytest.raises(N.RedirectRefused):
        N.NoRedirect().redirect_request(None,None,302,'',{},'https://localhost/')
    def fail(*args,**kwargs):
        raise urllib.error.HTTPError('https://fixed/',302,'UNSAFE_VENDOR',{},None)
    monkeypatch.setattr(Opener,'open',fail)
    assert N.public_read(N.discovery_url(0),15,10)==('REDIRECT_REFUSED',None)
    def timeout(*args,**kwargs):
        raise TimeoutError('UNSAFE_VENDOR')
    monkeypatch.setattr(Opener,'open',timeout)
    assert N.public_read(N.discovery_url(0),15,10)==('TRANSPORT_UNAVAILABLE',None)


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
