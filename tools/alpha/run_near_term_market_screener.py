"""Finite scratch-only market metadata/mechanics research; never trading authority."""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal, localcontext
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
import time
import urllib.error
import urllib.request

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
from src.execution_feasibility import public_market as venue  # noqa: E402
from src.live_pilot.hunter_cycle import fee_max, size_order  # noqa: E402
from tools.alpha.run_alpha_hunter import is_v2  # noqa: E402

SCHEMA = 'near-term-market-screen@1.0.0'
NS = 10**9
D = Decimal
FEE_POLICY = 'documented-fees-20261028'
FEE_EXPIRY = 1793750400 * NS  # 2026-11-04T00:00:00Z
FEE_RATES = dict(crypto='0.07', sports='0.05', finance='0.04', politics='0.04',
                 economics='0.05', culture='0.05', weather='0.05', mentions='0.04',
                 tech='0.04', geopolitics='0', **{'other/general': '0.05'})
CONFIG = dict(schema_version=SCHEMA, page_limit=100, page_cap=20, market_cap=10,
              book_cap=20, request_cap=64, max_body_bytes=2*1024*1024,
              socket_timeout_s=15, acquisition_budget_s=240, window_s=7200,
              book_age_s=30, fee_policy_version=FEE_POLICY)
TIME_STATES = ('MISSING', 'MALFORMED', 'DATE_ONLY', 'TIMEZONE_MISSING', 'EXPIRED',
               'FUTURE_OUTSIDE', 'IN_WINDOW')
DIMENSIONS = ('identity', 'freshness', 'status', 'tick', 'delay', 'fee', 'minimum', 'depth', 'sdk_grid')
POSSIBLE = 'MECHANICALLY_POSSIBLE_WITH_BOUNDED_ASSUMPTIONS'
MINIMUM = 'MINIMUM_UNSATISFIABLE_WITHIN_FEE_INCLUSIVE_CAP'
UNKNOWN = 'INCONCLUSIVE_MECHANICS'
FIELDS = {
    'config': tuple(CONFIG),
    'started': ('schema_version','as_of_utc','as_of_ns','started_monotonic_ns','config_sha256'),
    'request': ('schema_version','request_index','endpoint_kind','url','started_utc','started_monotonic_ns'),
    'receipt': ('schema_version','request_index','endpoint_kind','url','started_utc','received_utc',
                'started_monotonic_ns','received_monotonic_ns','status_class','body_state',
                'raw_file','raw_sha256','byte_count'),
    'manifest': ('schema_version','config_sha256','started_sha256','as_of_utc',
                 'mechanics_evaluated_ns','fee_policy_version','sources','coverage','categories','markets','tokens','summary'),
    'coverage': ('pages_requested','available','unavailable','invalid','raw_rows','unique_ids',
                 'identical_duplicates','conflicting_ids','stop_reason','external_universe_completeness',
                 'status_counts','protocol_counts','time_counts','selection_counts','book_counts'),
    'category': ('category_key','label','market_count','malformed_count'),
    'market': ('market_id','source_request_index','source_row_index','category_key','protocol_state',
               'status_state','time_state','end_time_utc','selection_state','reason_codes'),
    'token': ('market_id','token_id','outcome_index','source_request_index','state','first_reason',
              'dimension_codes','gamma_notional_min_usd','clob_min_shares','best_ask','best_ask_depth_shares',
              'gamma_tick','clob_tick','seconds_delay','book_timestamp_ns','age_ns_at_evaluation',
              'fee_rate_bound','fee_exponent','shares','principal_usd','fee_bound_usd','all_in_usd',
              'sdk_grid_state','derived_gamma_sha256'),
    'summary': ('assessment','category_count','market_count','in_window_count','selected_market_count',
                'unacquired_market_count','book_count','fresh_book_count','possible_count','minimum_failure_count',
                'inconclusive_count','resolution_within_120m_confirmed_count','external_universe_completeness','claim'),
    'terminal': ('schema_version','status','error_codes','manifest_sha256','summary'),
    'index': ('operation','terminal_sha256'),
    'verify': ('schema_version','status','error_codes','manifest_sha256','verified_operation_count',
               'network_attempts','provider_dispatches'),
    'source': ('request_index','receipt_sha256','raw_sha256'),
}


class Refused(ValueError):
    """Internal closed refusal; exceptions are never copied into results."""


class RedirectRefused(Refused):
    """Distinguish a redirect from a deadline/shape refusal in receipts."""


def require(value):
    if not value:
        raise Refused()


def canonical(value):
    def decimal(value):
        if isinstance(value, Decimal) and value.is_finite():
            require(-64<=value.adjusted()<=64 and len(value.as_tuple().digits)<=64)
            return format(value, 'f')
        raise Refused()
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
                      allow_nan=False, default=decimal).encode('utf-8')


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def record(kind, **values):
    require(set(values) == set(FIELDS[kind]))
    return values


def safe(path):
    path = Path(path)
    require(path.is_absolute() and '..' not in path.parts and not path.is_relative_to(REPO))
    for part in (path, *path.parents):
        try:
            info = part.lstat()
        except FileNotFoundError:
            continue
        require(not stat.S_ISLNK(info.st_mode) and not getattr(info, 'st_file_attributes', 0) & 0x400)
    return path


def read_bytes(path, limit=8*1024*1024):
    path = safe(path)
    require(path.is_file() and stat.S_ISREG(path.stat().st_mode) and path.stat().st_size <= limit)
    with path.open('rb') as stream:
        raw = stream.read(limit+1)
    require(len(raw) <= limit)
    return raw


def read_record(path):
    raw = read_bytes(path)
    # Public payloads use venue.decode_public_json. These derived records may
    # contain 2000 projected rows, so their separate bound is the frozen schema.
    def reject(_value):
        raise Refused()
    value = json.loads(raw.decode('utf-8'), object_pairs_hook=venue._no_duplicates,
                       parse_constant=reject)
    require(canonical(value)+b'\n' == raw)
    return value


def write(path, value):
    with safe(path).open('xb') as stream:
        stream.write(canonical(value)+b'\n')
        stream.flush()
        os.fsync(stream.fileno())


def utc(ns):
    seconds, nano = divmod(ns, NS)
    return datetime.fromtimestamp(seconds, timezone.utc).replace(microsecond=nano//1000).isoformat().replace('+00:00','Z')


def timestamp(value):
    require(type(value) is str and re.fullmatch(
        r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d{1,6})?(?:Z|[+-]\d\d:\d\d)', value))
    parsed = datetime.fromisoformat(value.replace('Z','+00:00')).astimezone(timezone.utc)
    seconds = int(parsed.replace(microsecond=0).timestamp())
    return seconds*NS + parsed.microsecond*1000


def time_bucket(value, as_of):
    if value is None:
        return 'MISSING', None
    if type(value) is str and re.fullmatch(r'\d{4}-\d\d-\d\d', value):
        return 'DATE_ONLY', None
    if type(value) is str and re.fullmatch(r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d{1,6})?', value):
        return 'TIMEZONE_MISSING', None
    try:
        end = timestamp(value)
    except (ValueError, OverflowError, OSError):
        return 'MALFORMED', None
    return ('EXPIRED' if end<=as_of else 'FUTURE_OUTSIDE' if end-as_of>7200*NS else 'IN_WINDOW'), end


def discovery_url(offset):
    require(type(offset) is int and 0<=offset<=1900 and offset%100==0)
    return f'https://gamma-api.polymarket.com/markets?closed=false&limit=100&offset={offset}'


def checked_url(url):
    if url in {discovery_url(i*100) for i in range(20)}:
        return url
    match = re.fullmatch(r'https://clob\.polymarket\.com/book\?token_id=([0-9]{1,100})', url)
    require(match is not None and venue.clob_book_url(match[1]) == url)
    return url


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise RedirectRefused()


def public_read(url, timeout, maximum):
    """The sole real transport. Call only after separately authorized public run."""
    checked_url(url)
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    request = urllib.request.Request(url, headers={'Accept':'application/json',
        'User-Agent':'polymarket-strategy-lab/S10-ALPHA-NEAR-TERM-01'})
    deadline = time.monotonic()+timeout
    try:
        with opener.open(request, timeout=timeout) as response:
            raw = bytearray()
            while True:
                require(time.monotonic() <= deadline)
                chunk = response.read1(min(65536, maximum+1-len(raw)))
                if not chunk:
                    break
                raw.extend(chunk)
                if len(raw)>maximum:
                    return 'OVERSIZE', None
            return 'HTTP_2XX', bytes(raw)
    except urllib.error.HTTPError as error:
        error.close()
        return ('REDIRECT_REFUSED' if 300<=error.code<400 else 'HTTP_4XX' if 400<=error.code<500 else 'HTTP_5XX'), None
    except RedirectRefused:
        return 'REDIRECT_REFUSED', None
    except (OSError, ValueError):
        return 'TRANSPORT_UNAVAILABLE', None


def source_body(receipt, body):
    if receipt['body_state'] != 'AVAILABLE':
        return None
    value = venue.decode_public_json(body(receipt['raw_file']))
    canonical(value)  # same bounded, UTF8-encodable scalar gate as acquisition
    if receipt['endpoint_kind']=='DISCOVERY':
        require(type(value) is list and len(value)<=100 and all(type(m) is dict for m in value))
    else:
        require(type(value) is dict)
    return value


def identity(market):
    try:
        mid = market.get('id')
        if type(mid) is int:
            mid = str(mid)
        venue.validate_gamma_market_id(mid)
        venue.validate_condition_id(market.get('conditionId'))
        tokens = venue._token_ids(market.get('clobTokenIds'))
        require(len(tokens)==2 and len(set(tokens))==2)
        for token in tokens:
            venue.validate_token_id(token)
        if is_v2(market) or market.get('version')=='v2':
            return mid, tokens, 'V2'
        require(market.get('version') in (None,'ctf','v1'))
        return mid, tokens, 'CTF'
    except (ValueError, TypeError, KeyError, venue._Invalid):
        return None, [], 'UNKNOWN'


def status(market):
    checks = [('active',True),('closed',False),('acceptingOrders',True),('enableOrderBook',True)]
    if any(type(market.get(k)) is not bool for k, v in checks):
        return 'UNKNOWN'
    return 'ACTIVE' if all(market[k] is v for k,v in checks) else 'INACTIVE'


def category(value):
    if type(value) is not str or not 0<len(value)<=128:
        return 'UNKNOWN', 'UNKNOWN', True
    key = value.casefold()
    return digest(canonical(value)), key.upper() if key in FEE_RATES else 'OPAQUE_CATEGORY', False


def catalog(receipts, body, as_of):
    entries, seen, conflicts, page_hashes = [], {}, set(), set()
    pages = [r for r in receipts if r['endpoint_kind']=='DISCOVERY']
    raw_rows = duplicates = 0
    stop = 'SOURCE_UNAVAILABLE'
    for r in pages:
        if r['body_state']!='AVAILABLE':
            stop = 'SOURCE_INVALID' if r['body_state'] in ('INVALID','OVERSIZE') else 'SOURCE_UNAVAILABLE'
            break
        rows = source_body(r, body)
        raw_rows += len(rows)
        page_hash = digest(canonical(rows))
        repeated=len(rows)==100 and page_hash in page_hashes
        page_hashes.add(page_hash)
        for ordinal, market in enumerate(rows):
            raw_mid = market.get('id')
            mid = str(raw_mid) if type(raw_mid) is int else raw_mid
            valid_id = type(mid) is str and re.fullmatch(r'[0-9]{1,32}',mid)
            key = mid if valid_id else ('invalid',r['request_index'],ordinal)
            fingerprint = digest(canonical(market))
            if key in seen:
                if seen[key][0]==fingerprint:
                    duplicates += 1
                else:
                    conflicts.add(key)
                continue
            ckey, label, malformed = category(market.get('category'))
            _, tokens, protocol = identity(market)
            bucket, end = time_bucket(market.get('endDate'),as_of)
            row = record('market',market_id=mid if valid_id else None,
                source_request_index=r['request_index'],source_row_index=ordinal,category_key=ckey,
                protocol_state=protocol,status_state=status(market),time_state=bucket,
                end_time_utc=None if end is None else utc(end),selection_state='INELIGIBLE',reason_codes=[])
            item = (market,row,tokens,end,label,malformed)
            seen[key]=(fingerprint,item)
            entries.append(item)
        if repeated:
            stop = 'SORT_OR_PAGINATION_UNVERIFIED'
            break
        stop = 'PAGE_BOUND_REACHED' if len(rows)<100 else 'COVERAGE_TRUNCATED' if len(pages)==20 else 'ACQUISITION_BUDGET_EXHAUSTED'
        if len(rows)<100:
            break
    for key, (_,item) in seen.items():
        market,row,tokens,end,label,malformed=item
        reasons=row['reason_codes']
        if key in conflicts: reasons.append('PAGE_CONFLICT')
        if row['market_id'] is None or row['protocol_state']=='UNKNOWN': reasons.append('IDENTITY_UNKNOWN')
        if row['status_state']!='ACTIVE': reasons.append('STATUS_NOT_ACTIVE')
        if row['protocol_state']!='CTF': reasons.append('PROTOCOL_UNSUPPORTED')
        if market.get('negRisk') is not False: reasons.append('NEG_RISK_UNSUPPORTED')
        if row['time_state']!='IN_WINDOW': reasons.append('TIME_UNKNOWN_OR_OUTSIDE')
        if not reasons: row['selection_state']='NOT_ACQUIRED'
    candidates = sorted((e for e in entries if not e[1]['reason_codes']),key=lambda e:(e[3],int(e[1]['market_id'])))
    selected=candidates[:10]
    for item in selected:
        item[1]['selection_state']='SELECTED'
    coverage=dict(pages_requested=len(pages),available=sum(r['body_state']=='AVAILABLE' for r in pages),
        unavailable=sum(r['body_state']=='UNAVAILABLE' for r in pages),
        invalid=sum(r['body_state'] in ('INVALID','OVERSIZE') for r in pages),raw_rows=raw_rows,
        unique_ids=sum(type(k) is str for k in seen),identical_duplicates=duplicates,
        conflicting_ids=len(conflicts),stop_reason=stop,external_universe_completeness='UNPROVEN')
    return entries,selected,coverage


def decimal(value, *, positive=False):
    require(type(value) in (str,int,Decimal) and len(str(value))<=64)
    result=D(value)
    require(result.is_finite() and -64<=result.adjusted()<=64
        and len(result.as_tuple().digits)<=64
        and (result>0 if positive else result>=0) and result<=D('1000000000000000'))
    return result


def economics(item, token, outcome, receipt, body, evaluated):
    market,mrow,*_=item
    row={key:None for key in FIELDS['token']}
    row.update(market_id=mrow['market_id'],token_id=token,outcome_index=outcome,
        source_request_index=None if receipt is None else receipt['request_index'],state=UNKNOWN,
        first_reason='BOOK_NOT_ACQUIRED',dimension_codes={k:'UNKNOWN' for k in DIMENSIONS},sdk_grid_state='UNKNOWN')
    dimensions=row['dimension_codes']
    if receipt is None or receipt['body_state']!='AVAILABLE':
        row['first_reason']='BOOK_NOT_ACQUIRED' if receipt is None else 'BOOK_UNAVAILABLE'
        return row
    try:
        raw=source_body(receipt,body)
        require(raw.get('version') in (None,'ctf','v1'))
        snapshot=venue.build_public_venue_snapshot(gamma_market_id=mrow['market_id'],
            condition_id=market['conditionId'],token_id=token,
            acquisition_started_ns=timestamp(receipt['started_utc']),
            acquisition_completed_ns=timestamp(receipt['received_utc']),
            gamma=venue.SourceFetchResult('BODY',canonical(market)),
            clob=venue.SourceFetchResult('BODY',body(receipt['raw_file'])))
        row['derived_gamma_sha256']=digest(canonical(market))
        require(snapshot.gamma_source_state=='AVAILABLE' and snapshot.clob_source_state=='AVAILABLE')
        dimensions['identity']='PASS' if snapshot.gamma_neg_risk is False and snapshot.book_neg_risk is False else 'FAIL'
        dimensions['status']='PASS' if mrow['status_state']=='ACTIVE' else 'FAIL'
        age=evaluated-snapshot.book_timestamp_ns
        dimensions['freshness']='PASS' if 0<=age<=30*NS else 'FAIL'
        row.update(gamma_notional_min_usd=snapshot.gamma_min_order_notional_usd,
            clob_min_shares=snapshot.book_min_order_size_raw,gamma_tick=snapshot.gamma_tick_size,
            clob_tick=snapshot.book_tick_size,seconds_delay=snapshot.seconds_delay,
            book_timestamp_ns=snapshot.book_timestamp_ns,age_ns_at_evaluation=age)
        require(snapshot.asks)
        ask=min(D(p) for p,q in snapshot.asks)
        depth=sum((D(q) for p,q in snapshot.asks if D(p)==ask),D(0))
        require(0<ask<1)
        tick=decimal(snapshot.book_tick_size,positive=True)
        dimensions['tick']='PASS' if (tick in map(D,('0.1','0.01','0.005','0.0025','0.001','0.0001'))
            and snapshot.gamma_tick_size is not None and tick==D(snapshot.gamma_tick_size)
            and all(D(p)%tick==0 for p,q in (*snapshot.bids,*snapshot.asks))) else 'FAIL'
        dimensions['delay']='PASS' if snapshot.seconds_delay==0 else 'FAIL'
        row.update(best_ask=str(ask),best_ask_depth_shares=str(depth))
        gamma_min=decimal(snapshot.gamma_min_order_notional_usd,positive=True)
        book_min=decimal(snapshot.book_min_order_size_raw,positive=True)
        key=market.get('category')
        require(type(key) is str and key.casefold() in FEE_RATES and evaluated<FEE_EXPIRY
            and type(snapshot.fees_enabled) is bool and snapshot.fee_taker_only is True
            and decimal(snapshot.fee_exponent)==1)
        gamma_rate=decimal(snapshot.fee_rate)
        require(gamma_rate<=1 and (snapshot.fees_enabled or gamma_rate==0))
        rate=max(gamma_rate if snapshot.fees_enabled else D(0),D(FEE_RATES[key.casefold()]))
        dimensions['fee']='PASS'
        row.update(fee_rate_bound=str(rate),fee_exponent=1)
        # Unknown dimensions dominate; a stale source never proves a current negative.
        if any(dimensions[k]!='PASS' for k in ('identity','status','freshness','tick','delay')):
            row['first_reason']='SOURCE_OR_VENUE_DIMENSION_INVALID'
            return row
        try:
            q,fee=size_order(ask=ask,depth=depth,rate=rate,exponent=1,cap=D('5'),floor=D('2'),
                            gamma_min=gamma_min,book_min=book_min,seconds_delay=snapshot.seconds_delay)
        except Exception as error:
            if getattr(error,'code',None)==MINIMUM:
                row.update(state=MINIMUM,first_reason=MINIMUM)
                dimensions['minimum']='FAIL'
            else:
                row['first_reason']='DEPTH_BELOW_SIZE'
                dimensions['depth']='FAIL'
            return row
        while q>0 and (q*ask)%D('.01'):
            q-=D('.01')
        fee=fee_max(q,ask,rate,1)
        if q*ask+fee<D('2') or q*ask<gamma_min or q<book_min:
            row.update(state=MINIMUM,first_reason=MINIMUM,sdk_grid_state='FAIL')
            dimensions['minimum']='FAIL'
            return row
        require(q>0 and q*ask+fee<=5 and depth>=q)
        dimensions.update(minimum='PASS',depth='PASS',sdk_grid='PASS')
        row.update(state=POSSIBLE,first_reason=None,sdk_grid_state='PASS',shares=str(q),
                   principal_usd=str(q*ask),fee_bound_usd=str(fee),all_in_usd=str(q*ask+fee))
    except (ValueError,TypeError,KeyError,ArithmeticError):
        row['first_reason']='FEE_UNKNOWN' if dimensions['identity']=='PASS' and dimensions['fee']=='UNKNOWN' else 'NATIVE_SOURCE_INVALID'
    return row


def counts(rows,key,states):
    observed=Counter(r[key] for r in rows)
    return {state:observed[state] for state in states}


def analyze(root,started,receipts,evaluated):
    body=lambda name:read_bytes(root/'op-000001'/name,CONFIG['max_body_bytes'])
    entries,selected,coverage=catalog(receipts,body,started['as_of_ns'])
    rows=[item[1] for item in entries]
    books=[r for r in receipts if r['endpoint_kind']=='BOOK']
    expected=[venue.clob_book_url(t) for item in selected for t in sorted(item[2],key=int)]
    require([r['url'] for r in books]==expected[:len(books)])
    tokens=[]
    ordinal=0
    for item in selected:
        original=item[2]
        for token in sorted(original,key=int):
            receipt=books[ordinal] if ordinal<len(books) else None
            ordinal+=1
            tokens.append(economics(item,token,original.index(token),receipt,body,evaluated))
    categories={}
    for market,row,ts,end,label,malformed in entries:
        c=categories.setdefault(row['category_key'],record('category',category_key=row['category_key'],
            label=label,market_count=0,malformed_count=0))
        c['market_count']+=1
        c['malformed_count']+=int(malformed)
    category_rows=[categories[k] for k in sorted(categories)]
    coverage.update(status_counts=counts(rows,'status_state',('ACTIVE','INACTIVE','UNKNOWN')),
        protocol_counts=counts(rows,'protocol_state',('CTF','V2','UNKNOWN')),
        time_counts=counts(rows,'time_state',TIME_STATES),
        selection_counts=counts(rows,'selection_state',('SELECTED','NOT_ACQUIRED','INELIGIBLE')),
        book_counts=dict(AVAILABLE=sum(r['body_state']=='AVAILABLE' for r in books),
            FRESH=sum(t['dimension_codes']['freshness']=='PASS' for t in tokens),
            STALE=sum(t['dimension_codes']['freshness']=='FAIL' for t in tokens),
            INVALID=sum(r['body_state'] in ('INVALID','OVERSIZE') for r in books),
            UNAVAILABLE=sum(r['body_state']=='UNAVAILABLE' for r in books),
            NOT_ACQUIRED=len(expected)-len(books)))
    incomplete=(coverage['stop_reason']!='PAGE_BOUND_REACHED' or coverage['conflicting_ids']
        or any(r['body_state']!='AVAILABLE' for r in receipts)
        or any(t['state']==UNKNOWN for t in tokens)
        or any(r['selection_state']=='NOT_ACQUIRED' or r['time_state'] in TIME_STATES[:4]
               or r['status_state']=='UNKNOWN' or r['protocol_state']=='UNKNOWN' for r in rows)
        or any(r['time_state']=='IN_WINDOW' and r['selection_state']=='INELIGIBLE' for r in rows))
    summary=record('summary',assessment='EVIDENCE_INCOMPLETE' if incomplete else 'MECHANICS_OBSERVATIONS_COMPLETE_FOR_CAPTURE',
        category_count=len(categories),market_count=len(rows),in_window_count=sum(r['time_state']=='IN_WINDOW' for r in rows),
        selected_market_count=len(selected),unacquired_market_count=sum(r['selection_state']=='NOT_ACQUIRED' for r in rows),
        book_count=len(books),fresh_book_count=coverage['book_counts']['FRESH'],
        possible_count=sum(t['state']==POSSIBLE for t in tokens),minimum_failure_count=sum(t['state']==MINIMUM for t in tokens),
        inconclusive_count=sum(t['state']==UNKNOWN for t in tokens),resolution_within_120m_confirmed_count=0,
        external_universe_completeness='UNPROVEN',claim='RESEARCH_ONLY')
    return record('manifest',schema_version=SCHEMA,config_sha256=started['config_sha256'],
        started_sha256=digest(read_bytes(root/'op-000001/started.json')),as_of_utc=started['as_of_utc'],
        mechanics_evaluated_ns=evaluated,fee_policy_version=FEE_POLICY,
        sources=[record('source',request_index=r['request_index'],receipt_sha256=digest(canonical(r)+b'\n'),
                        raw_sha256=r['raw_sha256']) for r in receipts],coverage=record('coverage',**coverage),
        categories=category_rows,markets=rows,tokens=tokens,summary=summary)


def terminal(status='BLOCKED',manifest_sha256=None,summary=None):
    return record('terminal',schema_version=SCHEMA,status=status,
        error_codes=[] if status=='COMPLETED' else ['CAPTURE_REFUSED'],manifest_sha256=manifest_sha256,summary=summary)


def run(scratch_dir, *, transport=None, clock_ns=time.time_ns, monotonic=time.monotonic):
    root=None
    owned=False
    try:
        root=safe(scratch_dir)
        if not root.exists(): root.mkdir(mode=0o700)
        require(root.is_dir() and not any(root.iterdir()))
        write(root/'config.json',CONFIG)
        op=root/'op-000001';op.mkdir(mode=0o700)
        owned=True
        as_of=clock_ns()//1000*1000
        mono=monotonic();deadline=mono+240
        started=record('started',schema_version=SCHEMA,as_of_utc=utc(as_of),as_of_ns=as_of,
            started_monotonic_ns=int(mono*NS),config_sha256=digest(read_bytes(root/'config.json')))
        write(op/'started.json',started)
        receipts=[]

        def collect(kind,url):
            require(len(receipts)<64 and monotonic()<deadline)
            checked_url(url)
            i=len(receipts)+1
            start=utc(clock_ns()//1000*1000);sm=int(monotonic()*NS)
            request=record('request',schema_version=SCHEMA,request_index=i,endpoint_kind=kind,
                url=url,started_utc=start,started_monotonic_ns=sm)
            write(op/f'request-{i:02d}.started.json',request)
            status_class,raw='TRANSPORT_UNAVAILABLE',None
            try:
                remaining=deadline-monotonic()
                require(remaining>0)
                status_class,raw=(transport or public_read)(url,min(15,remaining),CONFIG['max_body_bytes'])
                require(status_class in ('HTTP_2XX','HTTP_4XX','HTTP_5XX','REDIRECT_REFUSED','TRANSPORT_UNAVAILABLE','OVERSIZE'))
            except Exception:
                status_class,raw='TRANSPORT_UNAVAILABLE',None
            state='UNAVAILABLE';name=sha=None;size=0
            if status_class=='OVERSIZE' or isinstance(raw,bytes) and len(raw)>CONFIG['max_body_bytes']:
                status_class,state='OVERSIZE','OVERSIZE'
            elif status_class=='HTTP_2XX' and isinstance(raw,bytes):
                name=f'raw-{i:02d}.bin';sha=digest(raw);size=len(raw)
                with safe(op/name).open('xb') as stream:stream.write(raw)
                try:
                    parsed=venue.decode_public_json(raw)
                    canonical(parsed)
                    require((kind=='DISCOVERY' and type(parsed) is list and len(parsed)<=100 and all(type(x) is dict for x in parsed))
                            or (kind=='BOOK' and type(parsed) is dict))
                    state='AVAILABLE'
                except Exception:state='INVALID'
            receipt=record('receipt',**request,received_utc=utc(clock_ns()//1000*1000),
                received_monotonic_ns=int(monotonic()*NS),status_class=status_class,body_state=state,
                raw_file=name,raw_sha256=sha,byte_count=size)
            write(op/f'receipt-{i:02d}.json',receipt);receipts.append(receipt)
            return receipt

        page_hashes=set()
        for offset in range(0,2000,100):
            if monotonic()>=deadline:break
            receipt=collect('DISCOVERY',discovery_url(offset))
            if receipt['body_state']!='AVAILABLE':break
            page=source_body(receipt,lambda n:read_bytes(op/n,CONFIG['max_body_bytes']))
            page_hash=digest(canonical(page))
            if len(page)<100 or page_hash in page_hashes:break
            page_hashes.add(page_hash)
        _,selected,_=catalog(receipts,lambda n:read_bytes(op/n,CONFIG['max_body_bytes']),as_of)
        for item in selected:
            if len(receipts)+2>64:break
            for token in sorted(item[2],key=int):
                if monotonic()>=deadline:break
                collect('BOOK',venue.clob_book_url(token))
        evaluated=clock_ns()//1000*1000
        with localcontext() as context:
            context.prec=80
            manifest=analyze(root,started,receipts,evaluated)
        write(op/'manifest.json',manifest)
        result=terminal('COMPLETED',digest(read_bytes(op/'manifest.json')),manifest['summary'])
        write(op/'terminal.json',result)
        write(root/'index-op-000001.json',record('index',operation='op-000001',terminal_sha256=digest(read_bytes(op/'terminal.json'))))
        return result
    except Exception:
        # Never repair a partial operation or expose input/exception text.
        result=terminal()
        if owned:
            try:
                if not (op/'terminal.json').exists():
                    write(op/'terminal.json',result)
                if not (root/'index-op-000001.json').exists():
                    write(root/'index-op-000001.json',record('index',operation='op-000001',
                        terminal_sha256=digest(read_bytes(op/'terminal.json'))))
            except (OSError,ValueError):
                pass  # incomplete storage remains unverifiable; never repair it
        return result


def verify(scratch_dir):
    result=record('verify',schema_version=SCHEMA,status='BLOCKED',error_codes=['VERIFY_REFUSED'],
        manifest_sha256=None,verified_operation_count=0,network_attempts=0,provider_dispatches=0)
    try:
        root=safe(scratch_dir);op=root/'op-000001'
        require({p.name for p in root.iterdir()}=={'config.json','op-000001','index-op-000001.json'})
        require(read_record(root/'config.json')==CONFIG)
        started=read_record(op/'started.json')
        require(set(started)==set(FIELDS['started']) and started['schema_version']==SCHEMA
            and type(started['as_of_ns']) is int and utc(started['as_of_ns'])==started['as_of_utc']
            and started['config_sha256']==digest(read_bytes(root/'config.json')))
        manifest=read_record(op/'manifest.json')
        evaluated=manifest['mechanics_evaluated_ns']
        require(type(evaluated) is int and evaluated>=started['as_of_ns'])
        receipts=[];expected_files={'started.json','manifest.json','terminal.json'};books=False;pages=0
        discovery_stopped=False;page_hashes=set()
        previous_received=started['started_monotonic_ns']
        paths=sorted(op.glob('receipt-*.json'));require(len(paths)<=64)
        for i,path in enumerate(paths,1):
            require(path.name==f'receipt-{i:02d}.json')
            receipt=read_record(path);require(set(receipt)==set(FIELDS['receipt']))
            require(type(receipt['request_index']) is int and receipt['request_index']==i
                and receipt['schema_version']==SCHEMA and receipt['endpoint_kind'] in ('DISCOVERY','BOOK'))
            if receipt['endpoint_kind']=='DISCOVERY':
                require(not books and not discovery_stopped and pages<20 and receipt['url']==discovery_url(pages*100));pages+=1
            else:books=True
            checked_url(receipt['url'])
            require(started['as_of_ns']<=timestamp(receipt['started_utc'])<=timestamp(receipt['received_utc'])<=evaluated)
            require(type(receipt['started_monotonic_ns']) is int and type(receipt['received_monotonic_ns']) is int
                and previous_received<=receipt['started_monotonic_ns']<=receipt['received_monotonic_ns'])
            require(receipt['received_monotonic_ns']-receipt['started_monotonic_ns']<=30*NS
                and receipt['received_monotonic_ns']-started['started_monotonic_ns']<=255*NS)
            previous_received=receipt['received_monotonic_ns']
            require(receipt['status_class'] in ('HTTP_2XX','HTTP_4XX','HTTP_5XX','REDIRECT_REFUSED','TRANSPORT_UNAVAILABLE','OVERSIZE'))
            require(receipt['body_state'] in ('AVAILABLE','UNAVAILABLE','INVALID','OVERSIZE'))
            require(receipt['started_monotonic_ns']-started['started_monotonic_ns']<240*NS)
            request={k:receipt[k] for k in FIELDS['request']}
            name=f'request-{i:02d}.started.json'
            require(read_record(op/name)==request)
            expected_files.update((name,path.name))
            if receipt['raw_file'] is not None:
                require(receipt['raw_file']==f'raw-{i:02d}.bin')
                raw=read_bytes(op/receipt['raw_file'],CONFIG['max_body_bytes'])
                require(type(receipt['byte_count']) is int and receipt['byte_count']==len(raw) and digest(raw)==receipt['raw_sha256'])
                expected_files.add(receipt['raw_file'])
                require(receipt['status_class']=='HTTP_2XX' and receipt['body_state'] in ('AVAILABLE','INVALID'))
                probe=dict(receipt,body_state='AVAILABLE')
                try:
                    parsed=source_body(probe,lambda n:read_bytes(op/n,CONFIG['max_body_bytes']))
                    valid=True
                except Exception:
                    valid=False
                require((receipt['body_state']=='AVAILABLE') is valid)
            else:
                require(receipt['body_state'] in ('UNAVAILABLE','OVERSIZE') and receipt['raw_sha256'] is None and receipt['byte_count']==0)
                require((receipt['body_state']=='OVERSIZE') == (receipt['status_class']=='OVERSIZE'))
            if receipt['endpoint_kind']=='DISCOVERY':
                if receipt['body_state']!='AVAILABLE':discovery_stopped=True
                else:
                    fingerprint=digest(canonical(parsed))
                    discovery_stopped=len(parsed)<100 or fingerprint in page_hashes
                    page_hashes.add(fingerprint)
            receipts.append(receipt)
        require({p.name for p in op.iterdir()}==expected_files)
        with localcontext() as context:
            context.prec=80
            derived=analyze(root,started,receipts,evaluated)
        require(canonical(derived)==canonical(manifest))
        sha=digest(read_bytes(op/'manifest.json'))
        require(read_record(op/'terminal.json')==terminal('COMPLETED',sha,derived['summary']))
        require(read_record(root/'index-op-000001.json')==record('index',operation='op-000001',terminal_sha256=digest(read_bytes(op/'terminal.json'))))
        result.update(status='VERIFIED',error_codes=[],manifest_sha256=sha,verified_operation_count=1)
    except Exception:
        pass
    return result


class Parser(argparse.ArgumentParser):
    def error(self,message):
        raise Refused()


def main(argv=None):
    try:
        parser=Parser(description=__doc__)
        parser.add_argument('command',choices=['run','verify'])
        parser.add_argument('--scratch-dir',required=True)
        args=parser.parse_args(argv)
        result=run(args.scratch_dir) if args.command=='run' else verify(args.scratch_dir)
    except Exception:
        result=terminal()
    print(canonical(result).decode('utf-8'))
    return 0 if result['status'] in ('COMPLETED','VERIFIED') else 1


if __name__=='__main__':
    raise SystemExit(main())
