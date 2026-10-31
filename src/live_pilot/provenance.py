"""Native forward receipt integrity only; independent history/finality is absent."""
from pathlib import Path
import os
import re
from urllib.parse import urlsplit

from tools.alpha import run_alpha_hunter as H

COUNTS = ('observed_rows unique_market_ids native_market_count independent_event_groups '
          'pre_event_forecasts unresolved_groups verified_settled_groups n_train n_holdout n_bucket').split()


def bounded_inventory(root):
    """Validate every native path/size before native replay can open any payload."""
    root_files = {'capture-started.json', 'capture-final.json', 'config.json', 'operation.lock',
        'index-op-000001.json', 'capture-killed.json', 'research-alpha.sqlite3',
        'research-alpha.sqlite3-wal', 'research-alpha.sqlite3-shm', 'research-alpha.sqlite3-journal'}
    op_files = set()
    for folder, limit in ((root, 12), (root/'op-000001', 170)):
        with os.scandir(H.S.safe(folder, directory=True)) as entries:
            count = 0
            for entry in entries:
                count += 1
                H.need(count <= limit, 'SOURCE_INVALID')
                path = Path(entry.path)
                if folder == root and entry.name == 'op-000001':
                    H.S.safe(path, directory=True)
                    continue
                H.S.safe(path)
                info = path.stat()
                H.need(info.st_nlink == 1, 'SOURCE_INVALID')
                if folder == root:
                    H.need(entry.name in root_files, 'SOURCE_INVALID')
                else:
                    H.need(entry.name in {'started.json', 'clocks.json', 'manifest.json', 'terminal.json',
                        'pit.sqlite3', 'pit.sqlite3-wal', 'pit.sqlite3-shm', 'pit.sqlite3-journal'} or
                        re.fullmatch(r'(?:request-(?:0[1-9]|[1-3][0-9]|40)\.started|(?:receipt|source|transport)-(?:0[1-9]|[1-3][0-9]|40))\.json', entry.name),
                        'SOURCE_INVALID')
                    op_files.add(entry.name)
                maximum = 16*1024*1024 if '.sqlite3' in entry.name else 4_000_000
                if entry.name.startswith('source-'):
                    maximum = 2_000_000
                H.need(info.st_size <= maximum, 'SOURCE_INVALID')
    terminal = H.S.read(root/'op-000001/terminal.json')
    H.need(type(terminal) is dict and type(terminal.get('inputs_sha256')) is dict, 'SOURCE_INVALID')
    H.need(set(terminal['inputs_sha256']) == {n for n in op_files
        if n != 'terminal.json' and not n.startswith('pit.sqlite3')}, 'SOURCE_INVALID')
    count = len([n for n in op_files if n.startswith('receipt-')])
    H.need(1 <= count <= 40, 'SOURCE_INVALID')
    raw_files = set()
    for i in range(1, count+1):
        receipt = H.S.read(root/f'op-000001/receipt-{i:02d}.json')
        H.need(type(receipt) is dict and set(receipt) == {'url', 'started_ns', 'received_ns',
            'state', 'http_date', 'sha256', 'raw_file'} and
            receipt['raw_file'] in (None, f'source-{i:02d}.json'), 'SOURCE_INVALID')
        H.need(receipt['state'] in ('AVAILABLE', 'UNAVAILABLE'), 'SOURCE_INVALID')
        if receipt['state'] == 'AVAILABLE':
            H.need(receipt['raw_file'] == f'source-{i:02d}.json' and type(receipt['sha256']) is str and
                   re.fullmatch('[0-9a-f]{64}', receipt['sha256']), 'SOURCE_INVALID')
            raw_files.add(receipt['raw_file'])
        else:
            H.need(receipt['raw_file'] is receipt['sha256'] is None, 'SOURCE_INVALID')
        request = H.S.read(root/f'op-000001/request-{i:02d}.started.json')
        H.need(request == dict(url=receipt['url'], started_ns=receipt['started_ns']), 'SOURCE_INVALID')
    H.need(raw_files == {n for n in op_files if n.startswith('source-')}, 'SOURCE_INVALID')


def empty_report(status='NOT_CAPTURED', reason='SOURCE_ACCESS_NOT_VERIFIED'):
    if type(status) is not str or status not in ('REPLAY_VERIFIED', 'REFUSED', 'NOT_CAPTURED'):
        status = 'REFUSED'
    if type(reason) is not str or reason not in ('FORWARD_ONLY_RESEARCH', 'SOURCE_ACCESS_NOT_VERIFIED',
            'SOURCE_INVALID', 'SOURCE_CODE_DRIFT', 'SOURCE_HASH_MISMATCH',
            'SOURCE_CLOCK_INVALID', 'SOURCE_CAPTURE_INCOMPLETE'):
        reason = 'SOURCE_INVALID'
    return dict(schema_id='edge-evidence-report', schema_version='1.0.0', status=status, reason=reason,
        capture_manifest_sha256=None, native_manifest_sha256=None, method_sha256=None,
        **dict.fromkeys(COUNTS), source_counts=dict.fromkeys(('GAMMA', 'ESPN', 'CLOB', 'NWS')),
        accepted_production_corpora=0, accepted_production_methods=0,
        production_eligible=False, evidence_class='RESEARCH_ONLY')


def verify_capture(scratch):
    """Never interprets local hashes/flags as proof of original historical origin."""
    reason = 'SOURCE_INVALID'
    try:
        from tools.alpha import run_edge_evidence_capture as capture
        root = H.S.safe(Path(scratch), directory=True)
        bounded_inventory(root)
        start = H.S.read(root/'capture-started.json')
        H.need(set(start) == {'config', 'source_hashes'} and start['config'] == capture.CONFIG, reason)
        reason = 'SOURCE_CODE_DRIFT'
        H.need(start['source_hashes'] == capture.code_hashes(), reason)
        reason = 'SOURCE_HASH_MISMATCH'
        final = H.S.read(root/'capture-final.json')
        H.need(set(final) == {'schema_id', 'schema_version', 'started_sha256',
            'native_terminal_sha256', 'network_attempts'} and
            (final['schema_id'], final['schema_version']) == ('edge-evidence-capture', '1.0.0'), reason)
        H.need(final['started_sha256'] == H.digest((root/'capture-started.json').read_bytes()) and
               final['native_terminal_sha256'] == H.digest((root/'op-000001/terminal.json').read_bytes()), reason)
        H.need(H.verify(root) == dict(status='VERIFIED', operations=1, network_attempts=0, hermes_dispatches=0), reason)
        op = root/'op-000001'
        terminal = H.S.read(op/'terminal.json')
        H.need(terminal['status'] == 'COMPLETED' and terminal['categories'] == ['rain'] and
               terminal['hermes_state'] == 'HERMES_NOT_RUN_BUDGET_ZERO', reason)
        manifest = H.S.read(op/'manifest.json')
        H.need(manifest['run_mode'] == 'PUBLIC_SCREENER_NO_HERMES' and not manifest['hermes_findings'], reason)
        receipts = [H.S.read(p) for p in sorted(op.glob('receipt-*.json'))]
        H.need(type(final['network_attempts']) is int and
               1 <= len(receipts) == final['network_attempts'] <= capture.CONFIG['max_gets'], reason)
        H.need(len(list(op.glob('request-*.started.json'))) == len(receipts) and
               len(list(op.glob('transport-*.json'))) == len(receipts), reason)
        reason = 'SOURCE_CLOCK_INVALID'
        clocks = manifest['clocks']
        H.need(all(type(clocks[k]) is int and 0 < clocks[k] < 2**63
                   for k in ('started_ns', 'source_cutoff_ns', 'evaluated_ns')), reason)
        anchor = capture.datetime.fromisoformat(clocks['anchor_utc_date']).date()
        last = clocks['started_ns']
        sources = dict.fromkeys(('GAMMA', 'ESPN', 'CLOB', 'NWS'), 0)
        for i, receipt in enumerate(receipts, 1):
            H.need(type(receipt['started_ns']) is int and type(receipt['received_ns']) is int and
                   last <= receipt['started_ns'] <= receipt['received_ns'] <= clocks['evaluated_ns'], reason)
            last = receipt['received_ns']
            H.need(capture.allowed(receipt['url'], anchor), reason)
            transport = H.S.read(op/f'transport-{i:02d}.json')
            H.need(set(transport) == {'status', 'http_status', 'receipt_sha256'} and
                   capture.valid_transport(transport['status'], transport['http_status']) and
                   transport['receipt_sha256'] == H.digest((op/f'receipt-{i:02d}.json').read_bytes()), reason)
            if receipt['state'] == 'AVAILABLE':
                H.need(transport['status'] == 'HTTP_2XX', reason)
                raw = H.S.safe(op/receipt['raw_file']).read_bytes()
                H.need(len(raw) <= capture.CONFIG['max_bytes'] and not H.S.SECRET.search(raw), reason)
                host = urlsplit(receipt['url']).hostname
                sources[{'gamma-api.polymarket.com': 'GAMMA', 'api.weather.gov': 'NWS',
                         'clob.polymarket.com': 'CLOB'}[host]] += 1
        H.need(clocks['started_ns'] <= clocks['source_cutoff_ns'] <= clocks['evaluated_ns'] and
               clocks['evaluated_ns']-clocks['started_ns'] <= capture.CONFIG['duration_s']*10**9, reason)
        markets = H.observed_markets(op, receipts, clocks)
        forecasts = [m for m in manifest['markets'] if m.get('forecast') is not None and m.get('reason') is None]
        H.need(len(forecasts) <= capture.CONFIG['max_candidates'], reason)
        # Multiple markets or cosmetic rule text cannot multiply a source outcome.
        groups = {(m['station'], m['target_day']) for m in forecasts}
        result = empty_report('REPLAY_VERIFIED', 'FORWARD_ONLY_RESEARCH')
        result.update(dict.fromkeys(COUNTS, 0))
        result.update(capture_manifest_sha256=H.digest((root/'capture-final.json').read_bytes()),
            native_manifest_sha256=H.digest((op/'manifest.json').read_bytes()),
            method_sha256=start['source_hashes']['hunter'], source_counts=sources,
            observed_rows=len(markets), unique_market_ids=len({str(m['id']) for _, m in markets}),
            native_market_count=len(manifest['markets']), independent_event_groups=0,
            pre_event_forecasts=len(forecasts), unresolved_groups=len(groups))
        return result
    except Exception:
        return empty_report('REFUSED', reason)
