"""Synthetic source/report fixtures exercise mechanics, never original historical finality."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import socket

import pytest

from tools.alpha import run_weather_finality as W
from tests.tools.alpha import test_edge_evidence_capture as C
from tests.tools.alpha import test_alpha_hunter as T


def put(path, value):
    path.write_bytes(W.B.canonical(value))
    return str(path)


@pytest.fixture
def case(tmp_path):
    root, report, _ = C.execute(tmp_path)
    assert report['status'] == 'REPLAY_VERIFIED'
    request = dict(schema_id='weather-finality-request', schema_version='1.0.0', analysis_mode='SYNTHETIC_ONLY',
                   capture_dir=str(root), evidence_bundle_file=None)
    group = next(iter(W.sources(W.B._Reads(), request).values()))
    return request, group, tmp_path


def cli(group, amount='0.01', *, issue_delta=0):
    p = group['payload']
    issued = W.cutoff(p['target_day'])-timedelta(hours=2)+timedelta(seconds=issue_delta)
    local = issued.astimezone(timezone(timedelta(hours=-5)))
    text = (f"CDUS41 KOKX {issued:%d%H%M}\nCLI{p['station_id'][1:]}\nCLIMATE REPORT\n"
            f"NATIONAL WEATHER SERVICE NEW YORK NY\n{local:%I%M %p} EST {local:%a %b %d %Y}\n"
            f"...THE CITY CLIMATE SUMMARY FOR {datetime.fromisoformat(p['target_day']):%B %d %Y}...\n"
            f"PRECIPITATION (IN)\n  YESTERDAY {amount} 0.00 0.00 0.00\n"
            "  MONTH TO DATE 0.00\nSNOWFALL (IN)\n  YESTERDAY 0.0\n")
    return dict(id='12345678-1234-1234-1234-123456789abc', issuingOffice='KOKX', issuanceTime=issued.isoformat(),
                productCode='CLI', productText=text)


def evidence(case, *, amount='0.01', winner='Yes', complete=True):
    request, group, tmp = case
    p = group['payload']; mid = p['gamma_market_id']
    cutoff = W.ns(W.cutoff(p['target_day']))
    received = cutoff+W.NS
    product = cli(group, amount)
    data = T.payloads()
    gamma = deepcopy(next(v['markets'][0] for v in data.values() if isinstance(v, dict) and v.get('markets')))
    gamma.update(closed=True, umaResolutionStatus='resolved', outcomePrices=['1', '0'] if winner == 'Yes' else ['0', '1'],
                 closedTime=W.cutoff(p['target_day']).isoformat())
    index = {'@graph': [{'id': product['id']}]}
    event = [dict(id=mid, market=p['condition_id'], assets_ids=p['token_ids'],
        winning_asset_id=p['token_ids'][0 if winner == 'Yes' else 1], winning_outcome=winner,
        timestamp_received=W.cutoff(p['target_day']).isoformat(), timestamp=W.cutoff(p['target_day']).isoformat())]
    entries = []
    for kind, doc, url in [('NWS_INDEX', index, W.index_url(p)),
            ('NWS_PRODUCT', product, W.product_url(product['id'])),
            ('GAMMA', gamma, 'https://gamma-api.polymarket.com/markets/'+mid), ('V3_RESOLUTION', event, None)]:
        path = tmp/(kind+'.json'); put(path, doc)
        entries.append(dict(kind=kind, market_id=mid, body_file=str(path), sha256=W.B.digest(path.read_bytes()),
            url=url, started_ns=received, received_ns=received, status='HTTP_2XX', http_status=200, http_date=None))
    bundle = dict(schema_id='weather-finality-evidence', schema_version='1.0.0', evaluated_ns=received,
                  receipts=entries, synthetic_complete_groups=[p['station_id']+':'+p['target_day']] if complete else [])
    request['evidence_bundle_file'] = put(tmp/'evidence.json', bundle)
    return request, bundle


def safe(result):
    assert set(result) == W.RESULT_FIELDS == set(W.OUTPUT_CLASSIFICATION)
    assert all(set(row) == W.GROUP_FIELDS == set(W.GROUP_CLASSIFICATION) for row in result['groups'])
    assert all(value == 'scanned' for value in W.OUTPUT_CLASSIFICATION.values())
    assert all(value == 'scanned' for value in W.GROUP_CLASSIFICATION.values())
    assert result['no_live'] is result['no_order'] is True
    assert result['production_eligible'] is False
    assert result['real_orders'] == result['accepted_production_methods'] == result['accepted_production_corpora'] == 0
    assert result['source_verified_group_count'] == result['independent_event_groups'] == 0
    assert result['source_origin'] == 'UNVERIFIED'
    assert not W.H.S.SECRET.search(W.B.canonical(result))


def test_no_authority_or_source_mutation(case, monkeypatch):
    request, _, _ = case
    before = {str(p): W.B.digest(p.read_bytes()) for p in Path(request['capture_dir']).rglob('*') if p.is_file()}
    monkeypatch.setattr(socket, 'create_connection', lambda *a, **k: pytest.fail('network'))
    monkeypatch.setattr(W.capture, 'public_read', lambda *a, **k: pytest.fail('public GET'))
    result = W.audit(request)
    safe(result)
    assert result['status'] == 'COMPLETED_RESEARCH'
    assert result['actual_get_attempts'] == 0
    assert before == {str(p): W.B.digest(p.read_bytes()) for p in Path(request['capture_dir']).rglob('*') if p.is_file()}


def test_verified_original_capture_lineage_and_missing_archive(case):
    request, group, tmp = case
    request['analysis_mode'] = 'ORIGINAL_CAPTURE'
    result = W.audit(request)
    safe(result)
    assert result['original_group_count'] == result['unknown_group_count'] == 1
    row = result['groups'][0]
    assert row['station_id'] == group['payload']['station_id']
    assert row['instruments'][0]['token_ids'] == group['payload']['token_ids']
    assert row['cli_status'] == row['venue_status'] == row['agreement'] == 'UNKNOWN'
    assert 'CLI_UNAVAILABLE' in row['reasons']
    request['capture_dir'] = str(tmp/'absent')
    invalid = W.audit(request)
    safe(invalid)
    assert invalid['status'] == 'REFUSED' and invalid['original_group_count'] is None


def test_cli_station_day_issue_cutoff_revision(case):
    _, group, _ = case
    for value, outcome in [('0.00', 'No'), ('T', 'No'), ('TRACE', 'No'), ('0.01', 'Yes'), ('1.00', 'Yes')]:
        candidate, reason = W.cli_candidate(cli(group, value), group)
        assert reason is None and candidate['outcome'] == outcome
    for value in ('M', '-0.01', '0.001', 'NaN'):
        assert W.cli_candidate(cli(group, value), group)[0] is None
    assert W.cli_candidate(cli(group, issue_delta=7200), group) == (None, 'CLI_AFTER_CUTOFF')
    for change in ('station', 'date', 'office', 'partial', 'duplicate', 'timestamp'):
        doc = cli(group)
        if change == 'station': doc['productText'] = doc['productText'].replace('CLI'+group['payload']['station_id'][1:], 'CLILAX')
        if change == 'date': doc['productText'] = doc['productText'].replace('CLIMATE SUMMARY FOR', 'CLIMATE SUMMARY FOR WRONG')
        if change == 'office': doc['issuingOffice'] = 'KLAX'
        if change == 'partial': doc['productText'] += '\nVALID AS OF 0500 PM\n'
        if change == 'duplicate': doc['productText'] += '\nPRECIPITATION (IN)\nYESTERDAY 0.00\n'
        if change == 'timestamp': doc['issuanceTime'] = doc['issuanceTime'].replace('T', 'T00')
        assert W.cli_candidate(doc, group)[0] is None, change
    assert W.cutoff('2026-10-31').isoformat() == '2026-11-01T19:00:00+00:00'
    assert W.cutoff('2026-03-07').isoformat() == '2026-03-08T18:00:00+00:00'
    request, bundle = evidence(case, complete=False)
    row = W.audit(request)['groups'][0]
    assert row['candidate'] and row['cli_status'] == 'UNKNOWN'
    bundle['evaluated_ns'] = W.ns(W.cutoff(group['payload']['target_day']))-1
    for e in bundle['receipts']: e['received_ns'] = e['started_ns'] = bundle['evaluated_ns']
    put(Path(request['evidence_bundle_file']), bundle)
    assert 'CUTOFF_NOT_ELAPSED' in W.audit(request)['groups'][0]['reasons']


def test_venue_resolution_independence_and_disagreement(case):
    request, bundle = evidence(case)
    result = W.audit(request)
    safe(result)
    assert result['synthetic_verified_group_count'] == 1
    assert result['groups'][0]['agreement'] == 'VERIFIED'
    bundle['receipts'] = [e for e in bundle['receipts'] if e['kind'] != 'V3_RESOLUTION']
    put(Path(request['evidence_bundle_file']), bundle)
    row = W.audit(request)['groups'][0]
    assert row['venue_status'] == row['agreement'] == 'UNKNOWN'
    request, _ = evidence(case, winner='No')
    result = W.audit(request)
    assert result['groups'][0]['agreement'] == 'DISAGREEMENT'
    assert result['disagreement_group_count'] == 1 and result['synthetic_verified_group_count'] == 0
    request, bundle = evidence(case)
    request['analysis_mode'] = 'ORIGINAL_CAPTURE'
    bundle['synthetic_complete_groups'] = []
    put(Path(request['evidence_bundle_file']), bundle)
    row = W.audit(request)['groups'][0]
    assert row['cli_status'] == row['venue_status'] == row['agreement'] == 'UNKNOWN'
    assert 'VENUE_UNPROVEN' in row['reasons']
    assert row['venue_candidate_winner'] == 'Yes' and row['local_agreement'] == 'VERIFIED'


def test_no_information_leak_and_entry_windows(case):
    request, _ = evidence(case)
    row = W.audit(request)['groups'][0]
    assert row['forecast_issue_ns'] is None
    assert row['forecast_grid_update_ns'] <= row['forecast_received_ns'] <= row['source_cutoff_ns'] < row['climate_start_ns']
    assert row['near_resolution_channel'] == 'NOT_OBSERVED'
    end = 10**18
    for hours, expected in [(0, '0_6H'), (6, '6_12H'), (12, '12_24H'), (24, '24_48H'),
                            (48, '24_48H'), (49, 'OUTSIDE_WINDOWS'), (-1, 'OUTSIDE_WINDOWS')]:
        assert W.window(end, end-hours*3600*W.NS) == expected
    with pytest.raises(W.B.Refused): W.window(end, True)


def test_group_dedup_and_historical_method_separation(case, monkeypatch):
    request, group, _ = case
    result = W.audit(request)
    assert result['original_group_count'] == len(result['groups']) == 1
    assert len(result['groups'][0]['instruments'][0]['token_ids']) == 2
    assert group['payload']['source_method'] == 'nws-gridpoint-pop-climate-day-v1'
    fake = deepcopy(request); fake['method'] = 'NDFD_POP12'
    assert W.audit(fake)['status'] == 'REFUSED'
    # Native code/manifest tamper remains rejected by unchanged provenance verifier.
    manifest = Path(request['capture_dir'])/'op-000001/manifest.json'
    raw = json.loads(manifest.read_bytes()); raw['markets'][0]['forecast']['method'] = 'NDFD_POP12'
    put(manifest, raw)
    assert W.audit(request)['status'] == 'REFUSED'


def test_public_get_allowlist_budget_and_refusal(case, monkeypatch):
    request, group, tmp = case
    request['analysis_mode'] = 'ORIGINAL_CAPTURE'
    with pytest.raises(W.B.Refused):
        W.fetch_once(request, tmp, W.B._Reads(), {('x', 'y'): group})
    calls = []
    def transport(url, timeout, maximum):
        calls.append((url, timeout, maximum))
        doc = {'@graph': []} if url.startswith('https://api.weather.gov/products?') else {}
        return 'HTTP_2XX', W.B.canonical(doc), None, 200
    out = tmp/'fetch'; out.mkdir()
    fetched = W.fetch_once(request, out, W.B._Reads(), {('x', 'y'): group}, authorized=True,
        transport=transport, clock_ns=lambda: 2*10**18, monotonic=lambda: 100)
    assert len(calls) == 2 and all(t <= 12 and m <= 2_000_000 for _, t, m in calls)
    assert calls[0][0] == W.index_url(group['payload'])
    assert calls[1][0] == 'https://gamma-api.polymarket.com/markets/'+group['payload']['gamma_market_id']
    result = W.audit(fetched)
    assert result['status'] == 'COMPLETED_RESEARCH' and result['retained_http_attempts'] == 2
    before = len(calls)
    reqfile = put(tmp/'request.json', request)
    assert W.main(['fetch-once', '--request-file', reqfile, '--output-dir', str(tmp/'denied')]) == 1
    assert not (tmp/'denied').exists() and len(calls) == before
    request, bundle = evidence(case)
    bundle['receipts'][0]['url'] = 'https://example.com/private'
    put(Path(request['evidence_bundle_file']), bundle)
    assert W.audit(request)['status'] == 'REFUSED'
    assert W.MAX_GETS == 24 and W.MAX_REPLY == 2_000_000 and W.MAX_TOTAL == 32_000_000


def test_receipt_cold_replay_integrity_and_no_echo(case, capsys):
    request, _ = evidence(case)
    receipt = W.audit(request)
    assert W.verify(request, receipt) == receipt
    altered = deepcopy(receipt); altered['groups'][0]['candidate']['outcome'] = 'No'
    assert W.verify(request, altered)['status'] == 'REFUSED'
    tmp = case[2]
    reqfile = put(tmp/'request.json', request)
    output = tmp/'output'
    assert W.main(['audit', '--request-file', reqfile, '--output-dir', str(output)]) == 0
    terminal = json.loads((output/'complete.json').read_bytes())
    assert set(terminal) == W.COMPLETE_FIELDS == set(W.COMPLETE_CLASSIFICATION)
    assert terminal['receipt_sha256'] == W.B.digest((output/'receipt.json').read_bytes())
    assert W.main(['verify', '--request-file', reqfile, '--receipt-file', str(output/'receipt.json')]) == 0
    assert W.main(['verify', '--request-file', str(output/'request.json'), '--receipt-file', str(output/'receipt.json')]) == 0
    assert W.main(['audit', '--request-file', reqfile, '--output-dir', str(output)]) == 1
    assert W.main(['audit', '--request-file', '/untrusted-input-marker', '--output-dir', str(tmp/'bad')]) == 1
    assert 'untrusted-input-marker' not in capsys.readouterr().out
    product = tmp/'NWS_PRODUCT.json'; product.write_bytes(product.read_bytes()+b' ')
    assert W.audit(request)['status'] == 'REFUSED'
    invalid = W.audit({'untrusted-input-marker': 'untrusted-input-marker'})
    safe(invalid)
    assert 'untrusted-input-marker' not in W.B.canonical(invalid).decode()


def test_no_live_qualifier_or_bridge_promotion(case, monkeypatch):
    request, _ = evidence(case)
    monkeypatch.setattr(W.B, '_mechanics', lambda *a: pytest.fail('sizing'))
    monkeypatch.setattr(W.B, '_version', lambda *a: pytest.fail('lifecycle store'))
    monkeypatch.setattr(W.B, 'load_strategy_lifecycle_store', lambda *a: pytest.fail('store'))
    result = W.audit(request)
    safe(result)
    assert result['synthetic_verified_group_count'] == 1 and result['source_verified_group_count'] == 0
    assert result['method_state'] == 'METHOD_NOT_QUALIFIED'


def test_truthful_finality_counts_and_cadence_default_off(case):
    request, _ = evidence(case, complete=False)
    result = W.audit(request)
    safe(result)
    assert result['unknown_group_count'] == 1 and result['retained_http_attempts'] == 4
    assert result['actual_get_attempts'] == 0 and result['retained_bytes'] > 0
    assert result['real_event_to_order'] == 'UNMEASURED'
    assert result['groups'][0]['forecast_channel'] == 'ORIGINAL_PRE_EVENT_RECEIPT'
    assert result['groups'][0]['near_resolution_channel'] == 'NOT_OBSERVED'


def test_unavailable_http_provenance_and_attempt_cap(case):
    request, group, tmp = case
    request['analysis_mode'] = 'ORIGINAL_CAPTURE'
    calls = []
    def unavailable(url, timeout, maximum):
        calls.append(url)
        return 'TIMEOUT', None, None, None
    output = tmp/'unavailable'; output.mkdir()
    reads = W.Reads()
    fetched = W.fetch_once(request, output, reads, {('x', 'y'): group}, authorized=True,
        transport=unavailable, clock_ns=lambda: 2*10**18, monotonic=lambda: 100)
    result = W.audit(fetched)
    assert result['status'] == 'COMPLETED_RESEARCH' and result['unknown_group_count'] == 1
    assert result['retained_http_attempts'] == reads.network_attempts == len(calls) == 2
    assert len(list(output.glob('attempt-*.started.json'))) == 2
    saved = json.loads(Path(fetched['evidence_bundle_file']).read_bytes())
    assert all(e['http_date'] is e['http_status'] is None for e in saved['receipts'])
    def many(url, timeout, maximum):
        calls.append(url)
        doc = {'@graph': [{'id': f'{i:08x}-1234-1234-1234-123456789abc'} for i in range(40)]} if '?' in url else {}
        return 'HTTP_2XX', W.B.canonical(doc), 'Sun, 01 Nov 2026 20:00:00 GMT', 200
    output = tmp/'capped'; output.mkdir(); calls.clear(); reads = W.Reads()
    fetched = W.fetch_once(request, output, reads, {('x', 'y'): group}, authorized=True,
        transport=many, clock_ns=lambda: 2*10**18, monotonic=lambda: 100)
    assert len(calls) == reads.network_attempts == 24
    assert len(set(calls)) == 24
    saved = json.loads(Path(fetched['evidence_bundle_file']).read_bytes())
    assert len(saved['receipts']) == 24 and all(e['http_date'] for e in saved['receipts'])
    with pytest.raises(W.Refused):
        W.fetch_once(request, output, W.Reads(), {str(i): group for i in range(7)}, authorized=True)


def test_fetch_cli_counts_and_cold_replay(case, monkeypatch, capsys):
    request, _, tmp = case
    request['analysis_mode'] = 'ORIGINAL_CAPTURE'
    calls = []
    def unavailable(url, timeout, maximum):
        calls.append(url)
        return 'TIMEOUT', None, None, None
    monkeypatch.setattr(W.capture, 'public_read', unavailable)
    reqfile = put(tmp/'request.json', request)
    output = tmp/'fetch-cli'
    assert W.main(['fetch-once', '--request-file', reqfile, '--output-dir', str(output), '--authorize-public-get']) == 0
    result = json.loads(capsys.readouterr().out)
    assert result['actual_get_attempts'] == len(calls) == result['retained_http_attempts'] == 2
    assert W.main(['verify', '--request-file', str(output/'request.json'), '--receipt-file', str(output/'receipt.json')]) == 0
    assert json.loads(capsys.readouterr().out)['actual_get_attempts'] == 0 and len(calls) == 2
    # A transport exception still represents an attempted GET, never a hidden retry.
    def broken(*args): raise OSError('untrusted-error-marker')
    monkeypatch.setattr(W.capture, 'public_read', broken)
    output = tmp/'fetch-errors'
    assert W.main(['fetch-once', '--request-file', reqfile, '--output-dir', str(output), '--authorize-public-get']) == 0
    result = json.loads(capsys.readouterr().out)
    assert result['actual_get_attempts'] == result['retained_http_attempts'] == 2
    assert 'untrusted-error-marker' not in json.dumps(result)


def test_revision_conflicts_future_witness_and_sidecars(case):
    request, bundle = evidence(case)
    product = deepcopy(json.loads((case[2]/'NWS_PRODUCT.json').read_bytes()))
    product['id'] = '87654321-1234-1234-1234-123456789abc'
    product['productText'] = product['productText'].replace('YESTERDAY 0.01', 'YESTERDAY 0.00')
    path = case[2]/'second.json'; put(path, product)
    index = json.loads((case[2]/'NWS_INDEX.json').read_bytes()); index['@graph'].append({'id': product['id']})
    put(case[2]/'NWS_INDEX.json', index)
    bundle['receipts'][0]['sha256'] = W.B.digest((case[2]/'NWS_INDEX.json').read_bytes())
    entry = dict(bundle['receipts'][1], body_file=str(path), sha256=W.B.digest(path.read_bytes()), url=W.product_url(product['id']))
    bundle['receipts'].append(entry); put(Path(request['evidence_bundle_file']), bundle)
    row = W.audit(request)['groups'][0]
    assert row['candidate'] is None and 'CLI_CONFLICT' in row['reasons']
    request, bundle = evidence(case)
    eventpath = case[2]/'V3_RESOLUTION.json'
    events = json.loads(eventpath.read_bytes()); events[0]['timestamp'] = '2099-01-01T00:00:00Z'
    put(eventpath, events); bundle['receipts'][-1]['sha256'] = W.B.digest(eventpath.read_bytes())
    put(Path(request['evidence_bundle_file']), bundle)
    assert W.audit(request)['groups'][0]['venue_status'] == 'UNKNOWN'
    (Path(request['capture_dir'])/'research-alpha.sqlite3-wal').write_bytes(b'')
    assert W.audit(request)['status'] == 'REFUSED'


def test_evidence_inventory_and_raw_digest(case, monkeypatch):
    request, bundle = evidence(case)
    path = case[2]/'NWS_PRODUCT.json'
    path.write_text(json.dumps(json.loads(path.read_bytes()), indent=2))
    bundle['receipts'][1]['sha256'] = W.B.digest(path.read_bytes()); put(Path(request['evidence_bundle_file']), bundle)
    assert W.audit(request)['groups'][0]['candidate']['raw_sha256'] == W.B.digest(path.read_bytes())
    original = W.cli_candidate
    def addition(*args):
        (case[2]/'new-evidence.json').write_text('{}')
        return original(*args)
    monkeypatch.setattr(W, 'cli_candidate', addition)
    assert W.audit(request)['status'] == 'REFUSED'


def test_native_raw_gamma_decimal_compatibility(case):
    request, bundle = evidence(case)
    path = case[2]/'GAMMA.json'
    doc = json.loads(path.read_bytes()); doc.update(bestAsk=0.51, volume=1253.75, liquidity=100.25)
    path.write_text(json.dumps(doc))
    bundle['receipts'][2]['sha256'] = W.B.digest(path.read_bytes())
    put(Path(request['evidence_bundle_file']), bundle)
    result = W.audit(request)
    assert result['status'] == 'COMPLETED_RESEARCH'
    assert result['groups'][0]['venue_candidate_winner'] == 'Yes'
    assert result['groups'][0]['agreement'] == 'VERIFIED'


def test_final_input_change_cannot_leave_completion_marker(case, monkeypatch):
    request, _ = evidence(case)
    tmp = case[2]; reqfile = put(tmp/'request.json', request)
    original = W.write_new
    def concurrent_change(path, raw, reads):
        value = original(path, raw, reads)
        if path.name == 'receipt.json':
            source = Path(request['capture_dir'])/'op-000001/manifest.json'
            source.write_bytes(source.read_bytes()+b' ')
        return value
    monkeypatch.setattr(W, 'write_new', concurrent_change)
    output = tmp/'concurrent-output'
    assert W.main(['audit', '--request-file', reqfile, '--output-dir', str(output)]) == 1
    assert (output/'receipt.json').exists()  # Forensic data, not a completed bundle.
    assert not (output/'complete.json').exists()


@pytest.mark.parametrize('mutation', ['bool_clock', 'duplicate_keys', 'extra_field', 'hardlink', 'oversize', 'inventory'])
def test_external_evidence_boundaries(case, mutation, monkeypatch):
    request, bundle = evidence(case)
    tmp = case[2]
    if mutation == 'bool_clock':
        bundle['receipts'][0]['received_ns'] = True; put(Path(request['evidence_bundle_file']), bundle)
    elif mutation == 'duplicate_keys':
        Path(request['evidence_bundle_file']).write_text('{"receipts":[],"receipts":[]}')
    elif mutation == 'extra_field':
        bundle['unchecked'] = True; put(Path(request['evidence_bundle_file']), bundle)
    elif mutation == 'hardlink':
        target = tmp/'NWS_PRODUCT.json'; os.link(target, tmp/'link')
    elif mutation == 'oversize':
        (tmp/'NWS_PRODUCT.json').write_bytes(b' '*2_000_001)
    else:
        original = W.cli_candidate
        def add_file(*args):
            (Path(request['capture_dir'])/'unexpected.json').write_text('{}')
            return original(*args)
        monkeypatch.setattr(W, 'cli_candidate', add_file)
    result = W.audit(request)
    safe(result)
    assert result['status'] == 'REFUSED'
