"""Original-source claims cannot be made from local integrity or mock outcomes."""
import json
import pytest

from src.live_pilot import provenance as P
from tests.tools.alpha.test_edge_evidence_capture import execute


def test_original_source_and_resolution_provenance(tmp_path):
    root, result, _ = execute(tmp_path)
    assert result['evidence_class'] == 'RESEARCH_ONLY' and result['reason'] == 'FORWARD_ONLY_RESEARCH'
    assert result['verified_settled_groups'] == result['accepted_production_methods'] == 0
    assert result['pre_event_forecasts'] == 1 and not result['production_eligible']
    # A caller's self-description cannot create the absent final-settlement path.
    P.H.S.put(root/'caller-settlement.json', dict(production_eligible=True, finality=True, payout=1))
    assert P.verify_capture(root)['status'] == 'REFUSED'


@pytest.mark.parametrize('filename', ['source-01.json', 'receipt-01.json', 'manifest.json', 'transport-01.json'])
def test_mutated_raw_native_or_transport_evidence_refuses(tmp_path, filename):
    root, _, _ = execute(tmp_path)
    (root/'op-000001'/filename).write_bytes(b'{"untrusted-provenance-sentinel":true}')
    result = P.verify_capture(root)
    assert result['status'] == 'REFUSED' and result['pre_event_forecasts'] is None
    assert result['verified_settled_groups'] is None and not result['production_eligible']
    assert 'untrusted-provenance-sentinel' not in json.dumps(result)


def test_invalid_source_no_echo_and_host_refusal(tmp_path, monkeypatch):
    from src.live_pilot import autonomous_cycle as A
    marker = 'untrusted-invalid-source'
    result = P.verify_capture(tmp_path/marker)
    assert marker not in json.dumps(result) and result['status'] == 'REFUSED'
    assert result['source_counts'] == dict.fromkeys(('GAMMA', 'ESPN', 'CLOB', 'NWS'))
    monkeypatch.setattr(A, 'account', lambda *a: pytest.fail('authenticated account read'))
    report = A.evidence_activation_report(tmp_path/marker)
    assert report['eligible_host'] == report['account'] == 'NOT_OBSERVED'
    assert not report['live_active'] and report['unattended'] == 'DISABLED'


def test_source_code_drift_and_incomplete_capture_refuse(tmp_path, monkeypatch):
    from tools.alpha import run_edge_evidence_capture as C
    root, _, _ = execute(tmp_path)
    monkeypatch.setattr(C, 'code_hashes', lambda: {})
    result = P.verify_capture(root)
    assert result['reason'] == 'SOURCE_CODE_DRIFT' and result['method_sha256'] is None


def test_exact_public_fields_valid_invalid_and_unobserved(tmp_path):
    fields = {'schema_id', 'schema_version', 'status', 'reason', 'capture_manifest_sha256',
        'native_manifest_sha256', 'method_sha256', 'observed_rows', 'unique_market_ids',
        'native_market_count', 'independent_event_groups', 'pre_event_forecasts', 'unresolved_groups',
        'verified_settled_groups', 'n_train', 'n_holdout', 'n_bucket', 'source_counts',
        'accepted_production_corpora', 'accepted_production_methods', 'production_eligible', 'evidence_class'}
    _, result, _ = execute(tmp_path)
    for record in (result, P.empty_report(), P.verify_capture(tmp_path/'missing')):
        assert set(record) == fields
        assert record['accepted_production_methods'] == record['accepted_production_corpora'] == 0
        assert record['production_eligible'] is False
        assert set(record['source_counts']) == {'GAMMA', 'ESPN', 'CLOB', 'NWS'}


def reseal(root):
    """Attacker can rehash a local file; this must never grant origin authority."""
    op = root/'op-000001'
    terminal = P.H.S.read(op/'terminal.json')
    terminal['inputs_sha256'] = {name: P.H.digest((op/name).read_bytes()) for name in terminal['inputs_sha256']}
    (op/'terminal.json').write_bytes(P.H.canonical(terminal)+b'\n')
    index = dict(operation='op-000001', status=terminal['status'], terminal_sha256=P.H.digest((op/'terminal.json').read_bytes()))
    (root/'index-op-000001.json').write_bytes(P.H.canonical(index)+b'\n')
    final = P.H.S.read(root/'capture-final.json')
    final['native_terminal_sha256'] = P.H.digest((op/'terminal.json').read_bytes())
    (root/'capture-final.json').write_bytes(P.H.canonical(final)+b'\n')


@pytest.mark.parametrize('name', ['../../external-nonsecret.bin', '/external-nonsecret.bin', 'nested/file'])
def test_forged_native_input_paths_never_open_external_file(tmp_path, monkeypatch, name):
    from pathlib import Path
    root, _, _ = execute(tmp_path)
    path = root/'op-000001/terminal.json'
    terminal = P.H.S.read(path)
    terminal['inputs_sha256'][name] = 'a'*64
    path.write_bytes(P.H.canonical(terminal)+b'\n')
    final = P.H.S.read(root/'capture-final.json')
    final['native_terminal_sha256'] = P.H.digest(path.read_bytes())
    (root/'capture-final.json').write_bytes(P.H.canonical(final)+b'\n')
    index = P.H.S.read(root/'index-op-000001.json')
    index['terminal_sha256'] = final['native_terminal_sha256']
    (root/'index-op-000001.json').write_bytes(P.H.canonical(index)+b'\n')
    opened = []
    original = Path.read_bytes
    def read_bytes(path):
        opened.append(path)
        return original(path)
    monkeypatch.setattr(Path, 'read_bytes', read_bytes)
    result = P.verify_capture(root)
    assert result['status'] == 'REFUSED'
    assert all(p.resolve().is_relative_to(root.resolve()) for p in opened)


@pytest.mark.parametrize('http', [True, '200', 201.0, 99, 600, 404, None])
def test_rehashed_transport_still_requires_numeric_matching_http(tmp_path, http):
    root, _, _ = execute(tmp_path)
    path = root/'op-000001/transport-01.json'
    value = P.H.S.read(path); value['http_status'] = http
    path.write_bytes(P.H.canonical(value)+b'\n')
    reseal(root)
    assert P.verify_capture(root)['status'] == 'REFUSED'


def test_rehashed_available_receipt_cannot_claim_failed_http(tmp_path):
    root, _, _ = execute(tmp_path)
    path = root/'op-000001/transport-01.json'
    value = P.H.S.read(path); value.update(status='HTTP_4XX', http_status=404)
    path.write_bytes(P.H.canonical(value)+b'\n'); reseal(root)
    assert P.verify_capture(root)['status'] == 'REFUSED'


def test_same_station_day_rule_text_cannot_multiply_unresolved_groups(tmp_path):
    from copy import deepcopy
    from tests.tools.alpha import test_alpha_hunter as T
    data = T.payloads()
    url = T.H.rain_event_url(T.date(2026, 10, 28))
    first = data[url]['markets'][0]
    duplicate = deepcopy(first); duplicate['id'] = str(int(first['id'])+1)
    duplicate['description'] += '\n'
    data[url]['markets'].append(duplicate)
    _, result, _ = execute(tmp_path, data=data)
    assert result['pre_event_forecasts'] == 2 and result['unresolved_groups'] == 1
    assert result['independent_event_groups'] == result['verified_settled_groups'] == 0


def test_oversized_inventory_rejected_before_payload_read(tmp_path, monkeypatch):
    from pathlib import Path
    root, _, _ = execute(tmp_path)
    path = root/'op-000001/source-01.json'
    with path.open('wb') as stream:
        stream.seek(4_100_000)
        stream.write(b'0')
    original = Path.read_bytes
    def read_bytes(value):
        assert value != path, 'oversized body was read before bound check'
        return original(value)
    monkeypatch.setattr(Path, 'read_bytes', read_bytes)
    assert P.verify_capture(root)['status'] == 'REFUSED'


def test_empty_report_never_echoes_invalid_status_or_reason():
    marker = 'untrusted-status-sentinel'
    for bad in (marker, None, {}, [], True):
        record = P.empty_report(bad, bad)
        assert record['status'] == 'REFUSED' and record['reason'] == 'SOURCE_INVALID'
        assert marker not in json.dumps(record)
