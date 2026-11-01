"""Finite weather finality research audit; local consistency is never source authority."""
from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import os
from pathlib import Path
import re
import sys
import time
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from tools.alpha import run_signal_candidate_bridge as B
from tools.alpha import run_edge_evidence_capture as capture
from src.data_layer.analytical_research import pendulumflow_v3 as V3

H, QDR = B.H, B.H.QDR
NS = 1_000_000_000
MAX_REPLY, MAX_TOTAL, MAX_GETS = 2_000_000, 32_000_000, 24
REQUEST_FIELDS = frozenset('schema_id schema_version analysis_mode capture_dir evidence_bundle_file'.split())
BUNDLE_FIELDS = frozenset('schema_id schema_version evaluated_ns receipts synthetic_complete_groups'.split())
ENTRY_FIELDS = frozenset('kind market_id body_file sha256 url started_ns received_ns status http_status http_date'.split())
COMPLETE_FIELDS = frozenset('schema_id schema_version receipt_sha256'.split())
COMPLETE_CLASSIFICATION = {key: 'scanned' for key in COMPLETE_FIELDS}
RESULT_FIELDS = frozenset(('schema_id schema_version receipt_id status reasons analysis_mode tool_sha256 '
    'source_replay_state source_origin method_state source_bindings input_hashes original_group_count groups '
    'source_verified_group_count synthetic_verified_group_count unknown_group_count disagreement_group_count '
    'independent_event_groups accepted_production_methods accepted_production_corpora production_eligible '
    'no_live no_order real_orders real_event_to_order actual_get_attempts retained_http_attempts retained_bytes').split())
GROUP_FIELDS = frozenset(('station_id target_day instruments climate_start_ns climate_end_ns rule_cutoff_ns '
    'source_cutoff_ns forecast_issue_ns forecast_grid_update_ns forecast_received_ns entry_window forecast_channel '
    'near_resolution_channel candidate cli_status venue_status venue_candidate_winner local_agreement agreement reasons').split())
# Every field, including nested objects and invalid results, is scanned as canonical bytes.
OUTPUT_CLASSIFICATION = {key: 'scanned' for key in RESULT_FIELDS}
GROUP_CLASSIFICATION = {key: 'scanned' for key in GROUP_FIELDS}
REASONS = frozenset(('INPUT_INVALID SOURCE_UNVERIFIED SOURCE_CODE_DRIFT CLOCK_INVALID IDENTITY_MISMATCH '
    'STORE_CHANGED PATH_REFUSED OUTPUT_REFUSED RECEIPT_MISMATCH NETWORK_NOT_AUTHORIZED '
    'SOURCE_MISSING CLI_UNAVAILABLE CLI_INVALID CLI_AFTER_CUTOFF CLI_CONFLICT CUTOFF_NOT_ELAPSED '
    'REVISION_COVERAGE_UNPROVEN VENUE_WITNESS_MISSING VENUE_UNPROVEN VENUE_DISAGREEMENT EVALUATION_TIME_UNAVAILABLE '
    'BUDGET_EXHAUSTED ENDPOINT_REFUSED').split())


class Refused(B.Refused):
    def __init__(self, code):
        self.code = code if code in REASONS else 'INPUT_INVALID'
        self.status = 'REFUSED'


def require(ok, reason='INPUT_INVALID'):
    if not ok:
        raise Refused(reason)


class Reads(B._Reads):
    """Evidence bodies are direct siblings of their bundle, with a bounded file inventory."""
    evidence_files = None

    def inventory(self, root):
        names = set()
        with os.scandir(root) as entries:
            for count, entry in enumerate(entries, 1):
                require(count <= 256)
                if not entry.is_dir(follow_symlinks=False):
                    B._safe(entry.path)
                    names.add(entry.name)
        return names

    def check(self):
        super().check()
        if self.evidence_files is not None:
            root, names = self.evidence_files
            require(self.inventory(root) == names, 'STORE_CHANGED')


def seal(result):
    require(set(result) == RESULT_FIELDS)
    require(all(set(g) == GROUP_FIELDS for g in result['groups']))
    require(not H.S.SECRET.search(B.canonical(result)))
    result['receipt_id'] = 'weatherfinality:sha256:' + B.digest(B.canonical(
        {k: v for k, v in result.items() if k != 'receipt_id'}))
    return result


def empty(reason=None):
    result = dict.fromkeys(RESULT_FIELDS)
    result.update(schema_id='weather-finality-receipt', schema_version='1.0.0',
        status='REFUSED', reasons=[] if reason is None else [reason if reason in REASONS else 'INPUT_INVALID'],
        analysis_mode=None, tool_sha256=B.digest(Path(__file__).read_bytes()),
        source_replay_state='UNVERIFIED', source_origin='UNVERIFIED', method_state='METHOD_NOT_QUALIFIED',
        source_bindings=[], input_hashes=[], groups=[], source_verified_group_count=0, synthetic_verified_group_count=0,
        independent_event_groups=0, accepted_production_methods=0, accepted_production_corpora=0,
        production_eligible=False, no_live=True, no_order=True, real_orders=0,
        real_event_to_order='UNMEASURED', actual_get_attempts=0, retained_http_attempts=0, retained_bytes=0)
    return result


def window(end_ns, observed_ns):
    """Remaining ns to the LST day close; half-open buckets, final upper bound inclusive."""
    B._time(end_ns); B._time(observed_ns)
    hours = Decimal(end_ns-observed_ns) / Decimal(3600*NS)
    for low, high, label in ((0, 6, '0_6H'), (6, 12, '6_12H'), (12, 24, '12_24H'), (24, 48, '24_48H')):
        if low <= hours < high or hours == high == 48:
            return label
    return 'OUTSIDE_WINDOWS'


def sources(reads, request):
    """Reuse the bridge's unchanged native source binding; never its sizing or store path."""
    B._shape(request, REQUEST_FIELDS, 'weather-finality-request')
    require(request['analysis_mode'] in ('ORIGINAL_CAPTURE', 'SYNTHETIC_ONLY'))
    root = B._safe(request['capture_dir'], directory=True)
    B.provenance.bounded_inventory(root)
    require(not any(root.rglob('*.sqlite3-wal')) and not any(root.rglob('*.sqlite3-shm'))
            and not any(root.rglob('*.sqlite3-journal')), 'SOURCE_UNVERIFIED')
    manifest = reads.document(str(root/'op-000001/manifest.json'), 4_000_000)
    rows = [m for m in manifest['markets'] if m.get('forecast') is not None and m.get('reason') is None]
    require(1 <= len(rows) <= 6, 'SOURCE_UNVERIFIED')
    groups = {}
    for row in rows:
        replay, payload, evaluated = B._source(reads, dict(capture_dir=str(root), gamma_market_id=row['gamma_market_id']))
        key = (payload['station_id'], payload['target_day'])
        item = groups.setdefault(key, dict(payload=payload, payloads=[], replay=replay, forecast=row['forecast'],
                                          evaluated=evaluated, instruments=[]))
        require(payload['gamma_market_id'] not in [i['market_id'] for i in item['instruments']], 'IDENTITY_MISMATCH')
        item['instruments'].append(dict(market_id=payload['gamma_market_id'], condition_id=payload['condition_id'],
            token_ids=payload['token_ids'], rule_sha256=payload['resolution_rule_sha256']))
        item['payloads'].append(payload)
    reads.check()
    return groups


def index_url(payload):
    start = datetime.fromtimestamp(payload['event_deadline_ns']//NS, timezone.utc)
    end = cutoff(payload['target_day'])
    values = dict(location=payload['station_id'][1:], type='CLI', start=start.isoformat().replace('+00:00', 'Z'),
                  end=end.isoformat().replace('+00:00', 'Z'), limit=500)
    return 'https://api.weather.gov/products?' + urlencode(values)


def cutoff(day):
    following = date.fromisoformat(day) + timedelta(days=1)
    return datetime(following.year, following.month, following.day, 14,
                    tzinfo=ZoneInfo('America/New_York')).astimezone(timezone.utc)


def ns(moment):
    return int(moment.timestamp())*NS + moment.microsecond*1000


def product_url(product_id):
    require(type(product_id) is str and re.fullmatch(r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}', product_id))
    return 'https://api.weather.gov/products/' + product_id


def cli_candidate(doc, group):
    """Narrow full-day CLI grammar; unsupported layouts stay unknown, never guessed."""
    try:
        p = group['payload']
        require(type(doc) is dict and doc.get('productCode') == 'CLI')
        product_url(doc['id'])
        issued = QDR.parse_utc(doc['issuanceTime'])
        text = doc['productText']
        require(type(text) is str and 'VALID AS OF' not in text.upper())
        lines = text.upper().splitlines()
        pil = [x.strip() for x in lines if re.fullmatch(r'CLI[A-Z0-9]{3}', x.strip())]
        require(pil == ['CLI'+p['station_id'][1:]])
        headers = re.findall(r'^CDUS\d{2} (K[A-Z]{3}) (\d{6})(?: [A-Z]{3})?\s*$', text.upper(), re.M)
        require(len(headers) == 1 and headers[0] == (doc['issuingOffice'], issued.strftime('%d%H%M')))
        stamp = re.findall(r'^\s*(\d{3,4}) (AM|PM) (EST|EDT|CST|CDT|MST|MDT|PST|PDT) '
                           r'[A-Z]{3} ([A-Z]{3}) (\d{1,2}) (\d{4})\s*$', text.upper(), re.M)
        require(len(stamp) == 1)
        clock, ampm, zone, month, day, year = stamp[0]
        local = datetime.strptime(f'{clock.zfill(4)} {ampm} {month} {day} {year}', '%I%M %p %b %d %Y')
        offsets = dict(EST=-5, EDT=-4, CST=-6, CDT=-5, MST=-7, MDT=-6, PST=-8, PDT=-7)
        require(local.replace(tzinfo=timezone(timedelta(hours=offsets[zone]))).astimezone(timezone.utc) == issued)
        summaries = re.findall(r'CLIMATE SUMMARY FOR ([A-Z]+) (\d{1,2}) (\d{4})', ' '.join(lines))
        require(len(summaries) == 1)
        summary = datetime.strptime(' '.join(summaries[0]), '%B %d %Y').date()
        require(summary.isoformat() == p['target_day'])
        start = p['event_deadline_ns']; end = start+24*3600*NS
        require(ns(issued) >= end)
        if ns(issued) >= ns(cutoff(p['target_day'])):
            return None, 'CLI_AFTER_CUTOFF'
        sections = re.split(r'^\s*PRECIPITATION \(IN\)\s*$', text.upper(), flags=re.M)
        require(len(sections) == 2)
        section = re.split(r'^\s*(?:SNOWFALL|SNOW DEPTH|DEGREE DAYS|WIND|RELATIVE HUMIDITY)\b', sections[1], flags=re.M)[0]
        totals = re.findall(r'^\s*(?:TODAY|YESTERDAY)\s+(T|TRACE|M|\d+\.\d{2})(?:\s+[^\n]*)?$', section, re.M)
        require(len(totals) == 1 and totals[0] != 'M')
        value = totals[0]
        outcome = 'No' if value in ('T', 'TRACE') or Decimal(value) < Decimal('0.01') else 'Yes'
        return dict(product_id=doc['id'], issued_ns=ns(issued), precipitation_inches=value,
                    outcome=outcome), None
    except Exception:
        return None, 'CLI_INVALID'


def load_evidence(reads, request, groups):
    if request['evidence_bundle_file'] is None:
        return None, [], 0
    bundle = reads.document(request['evidence_bundle_file'], 1_048_576)
    evidence_root = Path(request['evidence_bundle_file']).parent
    if isinstance(reads, Reads):
        reads.evidence_files = (evidence_root, reads.inventory(evidence_root))
    B._shape(bundle, BUNDLE_FIELDS, 'weather-finality-evidence')
    B._time(bundle['evaluated_ns'])
    entries = bundle['receipts']
    require(type(entries) is list and len(entries) <= MAX_GETS)
    require(type(bundle['synthetic_complete_groups']) is list and len(bundle['synthetic_complete_groups']) <= 6)
    require(all(type(x) is str for x in bundle['synthetic_complete_groups']))
    # An input flag cannot certify historical publication coverage or archive authenticity.
    require(request['analysis_mode'] == 'SYNTHETIC_ONLY' or not bundle['synthetic_complete_groups'])
    bodies, total, seen = [], 0, set()
    known = {p['gamma_market_id']: p for g in groups.values() for p in g['payloads']}
    listed = set()
    for e in entries:
        require(type(e) is dict and set(e) == ENTRY_FIELDS)
        require(e['kind'] in ('NWS_INDEX', 'NWS_PRODUCT', 'GAMMA', 'V3_RESOLUTION'))
        require(e['market_id'] in known, 'IDENTITY_MISMATCH')
        p = known[e['market_id']]
        B._time(e['started_ns']); B._time(e['received_ns'])
        require(e['started_ns'] <= e['received_ns'] <= bundle['evaluated_ns'], 'CLOCK_INVALID')
        require((e['http_status'] is None or type(e['http_status']) is int) and type(e['status']) is str)
        require(e['http_date'] is None or type(e['http_date']) is str and len(e['http_date']) <= 128)
        require(capture.valid_transport(e['status'], e['http_status']))
        require((e['kind'], e['market_id'], e['url']) not in seen)
        seen.add((e['kind'], e['market_id'], e['url']))
        if e['kind'] == 'NWS_INDEX':
            require(e['url'] == index_url(p))
        elif e['kind'] == 'NWS_PRODUCT':
            require((e['market_id'], e['url']) in listed)
        elif e['kind'] == 'GAMMA':
            require(e['url'] == 'https://gamma-api.polymarket.com/markets/'+p['gamma_market_id'])
        else:
            require(e['url'] is None)  # Offline witness only; no additional acquisition host.
        if e['body_file'] is None:
            require(e['sha256'] is None and e['status'] != 'HTTP_2XX')
            continue
        require(e['status'] == 'HTTP_2XX')
        require(Path(e['body_file']).parent == evidence_root)
        raw = reads.read(e['body_file'], MAX_REPLY)
        require(not H.S.SECRET.search(raw) and B.digest(raw) == e['sha256'])
        total += len(raw); require(total <= MAX_TOTAL)
        doc = H.S.decode(raw)
        if e['kind'] == 'NWS_INDEX':
            require(type(doc) is dict and type(doc.get('@graph')) is list and len(doc['@graph']) <= 500)
            for item in doc['@graph']:
                listed.add((e['market_id'], product_url(item['id'])))
        if e['kind'] == 'NWS_PRODUCT':
            require(product_url(doc['id']) == e['url'])
        bodies.append((e, doc))
    reads.check()
    return bundle, bodies, total


def venue_one(p, bodies):
    """Reuse QDR agreement semantics, without elevating a JSON row into an archive witness."""
    try:
        gammas = [doc for e, doc in bodies if e['kind'] == 'GAMMA' and e['market_id'] == p['gamma_market_id']]
        events = [(e, doc) for e, doc in bodies if e['kind'] == 'V3_RESOLUTION' and e['market_id'] == p['gamma_market_id']]
        if len(gammas) != 1 or not events:
            return None, 'VENUE_WITNESS_MISSING'
        gamma = gammas[0]
        target, rule, tokens = H.rain_rule(gamma, date.fromisoformat(p['target_day']))
        require(rule.rule_text_sha256 == p['resolution_rule_sha256'] and tokens == p['token_ids'])
        candidate = QDR.MarketCandidate(p['gamma_market_id'], p['condition_id'], tuple(tokens),
            ('Yes', 'No'), '', gamma['slug'], '', '')
        normalized = QDR.normalize_gamma_market(gamma, candidate)
        rows = []
        for receipt, doc in events:
            require(type(doc) is list and 1 <= len(doc) <= 64)
            for row in doc:
                require(type(row) is dict and row['id'] == p['gamma_market_id'] and row['assets_ids'] == tokens)
                parsed = dict(row)
                parsed['timestamp_received'] = QDR.parse_utc(row['timestamp_received'])
                parsed['timestamp'] = QDR.parse_utc(row['timestamp'])
                event = V3.normalize_row('market_resolved', parsed['timestamp_received'].strftime('%Y-%m-%dT%H:00:00Z'), 0, parsed)
                require(event.condition_id == p['condition_id'])
                require(ns(parsed['timestamp_received']) >= p['event_deadline_ns']+24*3600*NS)
                require(ns(parsed['timestamp']) <= ns(parsed['timestamp_received']) <= receipt['received_ns'])
                rows.append(event)
        label = QDR.resolve_label(normalized, rows)
        return label.winning_outcome, None
    except Exception:
        return None, 'VENUE_DISAGREEMENT'


def venue_candidate(group, bodies):
    outcomes = [venue_one(p, bodies) for p in group['payloads']]
    for instrument, (winner, reason) in zip(group['instruments'], outcomes):
        instrument['venue_candidate_winner'] = winner
    if any(reason is not None for _, reason in outcomes):
        return None, 'VENUE_DISAGREEMENT' if any(r == 'VENUE_DISAGREEMENT' for _, r in outcomes) else 'VENUE_WITNESS_MISSING'
    winners = {winner for winner, _ in outcomes}
    return (winners.pop(), None) if len(winners) == 1 else (None, 'VENUE_DISAGREEMENT')


def evaluate(request, reads):
    result = empty()
    groups = sources(reads, request)
    bundle, bodies, total = load_evidence(reads, request, groups)
    result.update(status='COMPLETED_RESEARCH', analysis_mode=request['analysis_mode'],
        source_replay_state='REPLAY_VERIFIED', original_group_count=len(groups), unknown_group_count=len(groups),
        disagreement_group_count=0, retained_http_attempts=len(bundle['receipts']) if bundle else 0, retained_bytes=total)
    for key, group in sorted(groups.items()):
        p, f = group['payload'], group['forecast']
        result['source_bindings'].append(dict(method_id=p['method_id'], source_method=p['source_method'],
            source_hashes=p['source_hashes'], capture_manifest_sha256=group['replay']['capture_manifest_sha256'],
            native_manifest_sha256=group['replay']['native_manifest_sha256']))
        cut = ns(cutoff(p['target_day']))
        candidates, reasons = [], []
        for e, doc in bodies:
            if e['kind'] == 'NWS_PRODUCT' and e['market_id'] in {i['market_id'] for i in group['instruments']}:
                c, reason = cli_candidate(doc, group)
                if c is not None and c['issued_ns'] <= e['received_ns']:
                    c['raw_sha256'] = e['sha256']
                    candidates.append(c)
                else:
                    reasons.append(reason or 'CLOCK_INVALID')
        candidate = max(candidates, key=lambda c: c['issued_ns']) if candidates else None
        conflict = len({c['raw_sha256'] for c in candidates if candidate and c['issued_ns'] == candidate['issued_ns']}) > 1
        if conflict:
            candidate = None; reasons.append('CLI_CONFLICT')
        if not candidates:
            reasons.append('CLI_UNAVAILABLE')
        venue, reason = venue_candidate(group, bodies)
        if reason:
            reasons.append(reason)
        synthetic = request['analysis_mode'] == 'SYNTHETIC_ONLY'
        complete = bool(synthetic and bundle and ':'.join(key) in bundle['synthetic_complete_groups'])
        elapsed = bool(bundle and bundle['evaluated_ns'] >= cut)
        if bundle is None:
            reasons.append('EVALUATION_TIME_UNAVAILABLE')
        elif not elapsed:
            reasons.append('CUTOFF_NOT_ELAPSED')
        if not complete:
            reasons.append('REVISION_COVERAGE_UNPROVEN')
        if venue is not None and not synthetic:
            reasons.append('VENUE_UNPROVEN')
        # Missing venue is independent of parsing/coverage of the CLI channel.
        cli_ok = bool(candidate and complete and elapsed and not conflict and
                      not any(r in reasons for r in ('CLI_INVALID', 'CLOCK_INVALID', 'CLI_AFTER_CUTOFF')))
        venue_ok = venue is not None and synthetic
        local_agreement = ('VERIFIED' if candidate['outcome'] == venue else 'DISAGREEMENT') if candidate and venue else 'UNKNOWN'
        agreement = 'UNKNOWN'
        if cli_ok and venue_ok:
            agreement = 'VERIFIED' if candidate['outcome'] == venue else 'DISAGREEMENT'
            result['unknown_group_count'] -= 1
            result['synthetic_verified_group_count' if agreement == 'VERIFIED' else 'disagreement_group_count'] += 1
        end = p['event_deadline_ns']+24*3600*NS
        row = dict(station_id=key[0], target_day=key[1], instruments=group['instruments'],
            climate_start_ns=p['event_deadline_ns'], climate_end_ns=end, rule_cutoff_ns=cut,
            source_cutoff_ns=p['source_cutoff_ns'], forecast_issue_ns=None, forecast_grid_update_ns=f['grid_update_ns'],
            forecast_received_ns=f['available_ns'], entry_window=window(end, p['source_cutoff_ns']),
            forecast_channel='ORIGINAL_PRE_EVENT_RECEIPT', near_resolution_channel='NOT_OBSERVED',
            candidate=candidate, cli_status='VERIFIED' if cli_ok else 'UNKNOWN',
            venue_status='VERIFIED' if venue_ok else 'UNKNOWN', venue_candidate_winner=venue,
            local_agreement=local_agreement, agreement=agreement, reasons=sorted(set(reasons)))
        result['groups'].append(row)
    reads.check()
    result['input_hashes'] = sorted({B.digest(B.canonical(request)), *(v[1] for v in reads.files.values())})
    return seal(result)


def audit(request):
    try:
        return evaluate(request, Reads())
    except B.Refused as error:
        return seal(empty(error.code))
    except Exception:
        return seal(empty('INPUT_INVALID'))


def verify(request, receipt):
    expected = audit(request)
    try:
        if receipt_matches(expected, receipt):
            return expected
    except Exception:
        pass
    return seal(empty('RECEIPT_MISMATCH'))


def receipt_matches(expected, receipt):
    # Invocation-local GETs differ on cold replay; the retained attempt inventory does not.
    require(type(receipt) is dict and type(receipt.get('actual_get_attempts')) is int)
    require(receipt['actual_get_attempts'] in (0, expected['retained_http_attempts']))
    bound = dict(expected, actual_get_attempts=receipt['actual_get_attempts'])
    return B.canonical(seal(bound)) == B.canonical(receipt)


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise B.Refused('INPUT_INVALID')


def write_new(path, raw, reads):
    path = B._safe(str(path))
    require(not path.exists() and path not in reads.files, 'OUTPUT_REFUSED')
    with B._parent_handle(path) as parent:
        reads.check()
        fd = os.open(path.name if parent is not None else str(path),
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_NOFOLLOW', 0), 0o600, dir_fd=parent)
        with os.fdopen(fd, 'wb') as stream:
            stream.write(raw); stream.flush(); os.fsync(stream.fileno())
        if isinstance(reads, Reads) and reads.evidence_files is not None:
            root, names = reads.evidence_files
            if path.parent == root:
                reads.evidence_files = (root, names | {path.name})


def main(argv=None):
    invocation_started = time.monotonic()
    try:
        parser = Parser(add_help=False)
        parser.add_argument('command', choices=('audit', 'verify', 'fetch-once'))
        parser.add_argument('--request-file', required=True)
        parser.add_argument('--output-dir')
        parser.add_argument('--receipt-file')
        parser.add_argument('--authorize-public-get', action='store_true')
        args = parser.parse_args(argv)
        require((args.command == 'verify' and args.receipt_file and not args.output_dir and not args.authorize_public_get)
                or (args.command != 'verify' and args.output_dir and not args.receipt_file
                    and (args.command == 'fetch-once' or not args.authorize_public_get)))
    except Exception:
        print(B.canonical(seal(empty('INPUT_INVALID'))).decode()); return 2
    try:
        reads, cli_reads = Reads(), B._Reads()
        request = cli_reads.document(args.request_file, 65_536)
        if args.command == 'verify':
            receipt = cli_reads.document(args.receipt_file, 1_048_576)
            complete = cli_reads.document(str(Path(args.receipt_file).parent/'complete.json'), 4096)
            B._shape(complete, COMPLETE_FIELDS, 'weather-finality-complete')
            require(complete['receipt_sha256'] == B.digest(cli_reads.read(args.receipt_file, 1_048_576)), 'RECEIPT_MISMATCH')
            result = evaluate(request, reads)
            require(receipt_matches(result, receipt), 'RECEIPT_MISMATCH')
        else:
            if args.command == 'fetch-once' and not args.authorize_public_get:
                print(B.canonical(seal(empty('NETWORK_NOT_AUTHORIZED'))).decode()); return 1
            groups = sources(reads, request)
            if args.command == 'fetch-once':
                require(time.monotonic()-invocation_started < 300, 'BUDGET_EXHAUSTED')
            output = B._safe(args.output_dir, directory=True)
            require(not output.exists() and not output.is_relative_to(Path(request['capture_dir'])), 'OUTPUT_REFUSED')
            require(not any(p.is_relative_to(output) for p in reads.files), 'OUTPUT_REFUSED')
            with B._parent_handle(output):
                reads.check(); output.mkdir(mode=0o700)
                if args.command == 'fetch-once':
                    request = fetch_once(request, output, reads, groups, authorized=True, started=invocation_started)
                write_new(output/'request.json', B.canonical(request)+b'\n', reads)
                result = evaluate(request, reads)
                result['actual_get_attempts'] = getattr(reads, 'network_attempts', 0)
                seal(result)
                require(result['status'] != 'REFUSED')
                if args.command == 'fetch-once':
                    require(time.monotonic()-invocation_started < 300, 'BUDGET_EXHAUSTED')
                raw = B.canonical(result)+b'\n'
                write_new(output/'receipt.json', raw, reads)
                # Validate the data output before publishing an exclusive terminal marker.
                # Nothing is deleted on failure, and no input checks can fail after commit.
                reads.check(); cli_reads.check()
                complete = dict(schema_id='weather-finality-complete', schema_version='1.0.0', receipt_sha256=B.digest(raw))
                require(set(complete) == COMPLETE_FIELDS and not H.S.SECRET.search(B.canonical(complete)))
                if args.command == 'fetch-once':
                    require(time.monotonic()-invocation_started < 300, 'BUDGET_EXHAUSTED')
                write_new(output/'complete.json', B.canonical(complete)+b'\n', reads)
        if args.command == 'verify':
            reads.check(); cli_reads.check()
        print(B.canonical(result).decode())
        return 1 if result['status'] == 'REFUSED' else 0
    except B.Refused as error:
        result = seal(empty(error.code))
    except Exception:
        result = seal(empty('OUTPUT_REFUSED'))
    result['actual_get_attempts'] = getattr(locals().get('reads'), 'network_attempts', 0)
    seal(result)
    print(B.canonical(result).decode()); return 1


def fetch_once(request, output, reads, groups, *, authorized=False, transport=None,
               clock_ns=time.time_ns, monotonic=time.monotonic, started=None):
    """One finite acquisition. Injected tests use the same bounds; no retries or pagination."""
    require(authorized is True)
    require(1 <= len(groups) <= 6)
    require(request['analysis_mode'] == 'ORIGINAL_CAPTURE' and request['evidence_bundle_file'] is None)
    transport = capture.public_read if transport is None else transport
    begin, last, total, entries = monotonic() if started is None else started, 0, 0, []
    def get(kind, group, url):
        nonlocal last, total
        require(len(entries) < MAX_GETS and 0 <= monotonic()-begin < 300)
        p = group['payload']
        allowed = {index_url(p), 'https://gamma-api.polymarket.com/markets/'+p['gamma_market_id']}
        require(url in allowed or (kind == 'NWS_PRODUCT' and url in listed))
        started = B._time(clock_ns()); require(started >= last)
        remaining = 300-(monotonic()-begin)
        require(remaining > 0 and total < MAX_TOTAL)
        write_new(output/f'attempt-{len(entries):02d}.started.json',
                  B.canonical(dict(url=url, started_ns=started)), reads)
        reads.network_attempts = getattr(reads, 'network_attempts', 0)+1
        try:
            status, raw, http_date, http = transport(url, min(12, remaining), min(MAX_REPLY, MAX_TOTAL-total))
        except Exception:
            status, raw, http_date, http = 'TRANSPORT_UNAVAILABLE', None, None, None
        received = B._time(clock_ns()); last = received
        require(received >= started and monotonic()-begin <= 300)
        require(capture.valid_transport(status, http))
        require(raw is None or type(raw) is bytes and len(raw) <= min(MAX_REPLY, MAX_TOTAL-total)
                and not H.S.SECRET.search(raw))
        require((status == 'HTTP_2XX') == (raw is not None))
        body = None; digest = None
        if raw is not None:
            digest = B.digest(raw); total += len(raw)
            body = str(output/f'body-{len(entries):02d}.json')
            write_new(Path(body), raw, reads)
        entries.append(dict(kind=kind, market_id=p['gamma_market_id'], body_file=body, sha256=digest,
            url=url, started_ns=started, received_ns=received, status=status, http_status=http, http_date=http_date))
        return H.S.decode(raw) if raw is not None else None
    lists = []
    for group in groups.values():
        listed = set()
        doc = get('NWS_INDEX', group, index_url(group['payload']))
        if doc is not None:
            require(type(doc.get('@graph')) is list and len(doc['@graph']) <= 500)
            listed = {product_url(item['id']) for item in doc['@graph']}
        lists.append((group, sorted(listed)))
        get('GAMMA', group, 'https://gamma-api.polymarket.com/markets/'+group['payload']['gamma_market_id'])
    for group, urls in lists:
        listed = set(urls)
        for url in urls[:MAX_GETS-len(entries)]:
            get('NWS_PRODUCT', group, url)
    bundle = dict(schema_id='weather-finality-evidence', schema_version='1.0.0',
        evaluated_ns=last, receipts=entries, synthetic_complete_groups=[])
    evidence = output/'evidence.json'
    write_new(evidence, B.canonical(bundle)+b'\n', reads)
    result = dict(request, evidence_bundle_file=str(evidence))
    return result


if __name__ == '__main__':
    raise SystemExit(main())
