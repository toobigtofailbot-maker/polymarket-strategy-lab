"""Synthetic native fixtures prove offline mechanics, never original-source or method skill."""
from copy import deepcopy
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess

import pytest

from tools.alpha import run_signal_candidate_bridge as B
from tests.tools.alpha import test_alpha_hunter as T
from tests.tools.alpha import test_edge_evidence_capture as C
from src.strategy_lifecycle import (
    initialize_strategy_lifecycle_store, append_strategy_lifecycle_record,
    build_strategy_family, build_strategy_version, load_strategy_lifecycle_store,
    build_strategy_health_receipt,
)


def put(path, value):
    path.write_bytes(B.canonical(value))
    return str(path)


def tree_hash(root):
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob('*') if p.is_file()}


def make_case(tmp_path, *, outcome=0, gamma_changes=None, book_changes=None):
    """All acquisition is an injected local fixture, prepared BEFORE the tested tool."""
    data = T.payloads()
    root, report, _ = C.execute(tmp_path, data=data)
    assert report['status'] == 'REPLAY_VERIFIED', report
    request = dict(schema_id='signal-candidate-request', schema_version='1.0.0',
        analysis_mode='SYNTHETIC_ONLY', capture_dir=str(root), lifecycle_store_path=str(tmp_path/'life.sqlite3'),
        expected_lifecycle_head='', strategy_version_id='', gamma_market_id='6296029', outcome_index=outcome,
        decision_ns=T.NOW, venue_bundle_file=str(tmp_path/'venue.json'))
    _, payload, evaluated = B._source(B._Reads(), request)
    request['decision_ns'] = evaluated
    binding = 'signalbinding:sha256:' + B.digest(B.canonical({'binding_payload': payload}))
    store = Path(request['lifecycle_store_path'])
    assert initialize_strategy_lifecycle_store(store).is_valid
    family = build_strategy_family(family_key='rain.fixture', family_label='Synthetic rain',
        created_time_ns=1, creation_provenance='synthetic:fixture')
    assert append_strategy_lifecycle_record(store, family).is_valid
    version = build_strategy_version(strategy_family_id=family.strategy_family_id, parent=None,
        strategy_label='Synthetic rain', evidence_posture='REPEATABLE_STATISTICAL',
        strategy_code_identity='synthetic:rain', strategy_spec=dict(thesis={}, universe={}, entry_rule={},
        exit_rule={}, execution_rule={'style': 'AGGRESSIVE_TAKER'}, parameters={}), adaptive_bounds={},
        evidence_refs=[binding], created_time_ns=2, creation_provenance='synthetic:fixture')
    assert append_strategy_lifecycle_record(store, version).is_valid
    request['strategy_version_id'] = version.strategy_version_id
    request['expected_lifecycle_head'] = load_strategy_lifecycle_store(store).snapshot.store_head_entry_hash
    gamma = deepcopy(next(v['markets'][0] for v in data.values() if isinstance(v, dict) and v.get('markets')))
    # Repricing uses separately supplied synthetic venue facts, not rewritten source receipts.
    gamma.update(orderMinSize=1, secondsDelay=0)
    gamma.update(gamma_changes or {})
    token = payload['token_ids'][outcome]
    book = T.book(gamma, token, ask='0.5', bid='0.49', size='1000', tick='0.001')
    book.update(book_changes or {})
    return request, gamma, book, write_venue(request, gamma, book)


def write_venue(request, gamma, book, **clocks):
    path = Path(request['venue_bundle_file'])
    gpath, bpath = path.with_name('gamma.json'), path.with_name('book.json')
    graw, braw = B.canonical(gamma), B.canonical(book)
    gpath.write_bytes(graw); bpath.write_bytes(braw)
    now = request['decision_ns']
    values = dict(acquisition_started_ns=now-1_000_000, acquisition_completed_ns=now)
    values.update(clocks)
    snapshot = B.venue.build_public_venue_snapshot(gamma_market_id=request['gamma_market_id'],
        condition_id=gamma['conditionId'], token_id=T.RAIN_TOKENS[request['outcome_index']],
        **values, gamma=B.venue.SourceFetchResult('BODY', graw), clob=B.venue.SourceFetchResult('BODY', braw))
    bundle = dict(schema_id='signal-candidate-venue-bundle', schema_version='1.0.0',
        gamma_body_file=str(gpath), clob_body_file=str(bpath), **values, venue_snapshot=snapshot.to_mapping())
    put(path, bundle)
    return bundle


def safe_result(result):
    assert set(result) == set(B.RESULT_FIELDS) == set(B.OUTPUT_CLASSIFICATION)
    assert result['production_eligible'] is False and result['no_order'] is True and result['no_live'] is True
    assert result['permit'] is result['signed_order'] is None
    assert result['method_state'] == 'METHOD_NOT_QUALIFIED' and result['source_origin'] == 'UNVERIFIED'
    assert result['real_event_to_order'] == 'UNMEASURED'
    assert not B.H.S.SECRET.search(B.canonical(result))


def test_read_only_import_and_authority():
    assert B.CATEGORY == 'WEATHER_US_DAILY_RAIN'
    assert B.AGE == 30_000_000_000
    assert set(B.RESULT_FIELDS) == set(B.OUTPUT_CLASSIFICATION)


def test_native_rain_replay_and_identity_binding(tmp_path):
    request, gamma, book, _ = make_case(tmp_path)
    result = B.evaluate_request(request)
    assert result['source_replay_state'] == 'REPLAY_VERIFIED', result
    assert result['binding_payload']['token_ids'] == T.RAIN_TOKENS
    assert result['source_method'] == 'nws-gridpoint-pop-climate-day-v1'
    assert result['event_deadline_ns'] == B.H.S.ns('2026-10-28T05:00:00Z')
    for mutation in ('condition', 'tokens', 'rule'):
        bad = deepcopy(gamma)
        if mutation == 'condition': bad['conditionId'] = '0x'+'0'*64
        if mutation == 'tokens': bad['clobTokenIds'] = json.dumps(list(reversed(T.RAIN_TOKENS)))
        if mutation == 'rule': bad['description'] = bad['description'].replace('0.01 inches', '0.02 inches')
        write_venue(request, bad, book)
        assert B.evaluate_request(request)['status'] == 'REFUSED'
    put(Path(request['capture_dir'])/'capture-started.json', {})
    assert B.evaluate_request(request)['source_replay_state'] == 'UNVERIFIED'


def test_exact_verified_version_binding(tmp_path):
    request, _, _, _ = make_case(tmp_path)
    assert B.evaluate_request(request)['strategy_version_id'] == request['strategy_version_id']
    for key in ('strategy_version_id', 'expected_lifecycle_head'):
        bad = dict(request, **{key: 'wrong'})
        assert B.evaluate_request(bad)['status'] == 'REFUSED'
    version = B.load_strategy_lifecycle_store(request['lifecycle_store_path']).snapshot.version_by_id(request['strategy_version_id'])
    assert version.evidence_refs[0].startswith('signalbinding:sha256:')
    other = dict(request, outcome_index=1)
    # Both outcomes bind the same ordered source pair; venue token must still match selection.
    assert B.evaluate_request(other)['status'] == 'REFUSED'
    for refs, created in [(version.evidence_refs, request['decision_ns']+1),
                          (['unbound:fixture'], 3)]:
        incompatible = build_strategy_version(strategy_family_id=version.strategy_family_id, parent=None,
            strategy_label='Incompatible fixture', evidence_posture=version.evidence_posture,
            strategy_code_identity=version.strategy_code_identity, strategy_spec=version.strategy_spec_json,
            adaptive_bounds=version.adaptive_bounds_json, evidence_refs=refs, created_time_ns=created,
            creation_provenance='synthetic:incompatible')
        assert append_strategy_lifecycle_record(request['lifecycle_store_path'], incompatible).is_valid
        bad = dict(request, strategy_version_id=incompatible.strategy_version_id,
            expected_lifecycle_head=load_strategy_lifecycle_store(request['lifecycle_store_path']).snapshot.store_head_entry_hash)
        assert B.evaluate_request(bad)['reason_codes'] == ['VERSION_INVALID']
    health = build_strategy_health_receipt(strategy_version_id=version.strategy_version_id,
        previous_health_state='NEW', new_health_state='RETIRED', decision_ref='synthetic:retire',
        created_time_ns=3)
    assert append_strategy_lifecycle_record(request['lifecycle_store_path'], health).is_valid
    request['expected_lifecycle_head'] = load_strategy_lifecycle_store(request['lifecycle_store_path']).snapshot.store_head_entry_hash
    assert B.evaluate_request(request)['reason_codes'] == ['VERSION_INVALID']


def test_decision_time_currentness_and_replay_denial(tmp_path):
    request, gamma, book, _ = make_case(tmp_path)
    for offset in (-1, B.AGE, 86400*B.NS):
        bad = dict(request, decision_ns=request['decision_ns']+offset)
        assert B.evaluate_request(bad)['status'] == 'REFUSED'
    now = request['decision_ns']
    book['timestamp'] = str((now-B.AGE)//1_000_000)
    write_venue(request, gamma, book, acquisition_started_ns=now-B.AGE, acquisition_completed_ns=now)
    assert B.evaluate_request(request)['status'] == 'MECHANICALLY_FEASIBLE_RESEARCH_ONLY'
    book['timestamp'] = str((now-B.AGE-1_000_000)//1_000_000)
    write_venue(request, gamma, book)
    result = B.evaluate_request(request)
    assert result['status'] == 'INCONCLUSIVE' and result['reason_codes'] == ['BOOK_STALE']
    book['timestamp'] = str((now+B.NS)//1_000_000)
    write_venue(request, gamma, book)
    assert B.evaluate_request(request)['status'] == 'INCONCLUSIVE'


@pytest.mark.parametrize('outcome', [0, 1])
def test_reachable_fok_mechanics_remains_research_only(tmp_path, outcome):
    request, _, _, _ = make_case(tmp_path, outcome=outcome)
    result = B.evaluate_request(request)
    assert result['status'] == 'MECHANICALLY_FEASIBLE_RESEARCH_ONLY', result
    assert result['native_assessment']['status'] == 'FEASIBLE'
    assert result['token_id'] == T.RAIN_TOKENS[outcome] and result['outcome_index'] == outcome
    assert result['execution_intent']['order_type'] == 'FOK'
    assert Decimal(result['all_in_usd']) <= 5
    assert Decimal(result['principal_usd']) % Decimal('.01') == 0
    assert Decimal(result['conservative_fee_usd']) > Decimal(result['native_assessment']['fee_upper_bound_usd'])
    safe_result(result)


@pytest.mark.parametrize('change', ['minimum', 'shares', 'depth', 'tick', 'delay', 'fee', 'expiry'])
def test_fee_minimum_depth_ticks_delay_and_expiry(tmp_path, change):
    request, gamma, book, _ = make_case(tmp_path)
    if change == 'minimum': gamma['orderMinSize'] = 5
    if change == 'shares': book['min_order_size'] = '100'
    if change == 'depth': book['asks'][0]['size'] = '1'
    if change == 'tick': book['tick_size'] = '0.01'
    if change == 'delay': gamma['secondsDelay'] = 2
    if change == 'fee': gamma['feeSchedule']['exponent'] = 2
    if change == 'expiry':
        # Isolate the economics boundary with existing immutable native inputs.
        reads = B._Reads(); _, payload, _ = B._source(reads, request)
        binding = 'signalbinding:sha256:'+B.digest(B.canonical({'binding_payload': payload}))
        version, _ = B._version(reads, request, binding)
        snapshot = B._venue(reads, request, payload)
        from dataclasses import replace
        at = B.scanner.FEE_EXPIRY
        snapshot = replace(snapshot, acquisition_started_ns=at-1, acquisition_completed_ns=at,
                           book_timestamp_ns=at, venue_snapshot_id=B.M._PENDING_ID)
        with pytest.raises(B.Refused) as exc:
            B._mechanics(B._empty(), dict(request, decision_ns=at), version, snapshot)
        assert exc.value.code == 'FEE_POLICY_EXPIRED'
        return
    write_venue(request, gamma, book)
    result = B.evaluate_request(request)
    assert result['status'] in ('INCONCLUSIVE', 'MECHANICALLY_NOT_FEASIBLE'), result
    assert result['production_eligible'] is False


def test_no_method_or_financial_edge_promotion(tmp_path):
    request, _, _, _ = make_case(tmp_path)
    for field in ('p_lower', 'qualified', 'PRODUCTION_METHODS', 'provider', 'cap'):
        result = B.evaluate_request(dict(request, **{field: True}))
        assert result['status'] == 'REFUSED' and result['production_eligible'] is False
    historical = B.evaluate_request(dict(request, analysis_mode='RESEARCH_HISTORICAL'))
    assert historical['analysis_mode'] == 'RESEARCH_HISTORICAL'
    safe_result(historical)
    assert 'p_lower' not in B.canonical(historical).decode()


def test_receipt_cold_replay_tamper_and_no_echo(tmp_path, capsys):
    request, gamma, book, _ = make_case(tmp_path)
    result = B.evaluate_request(request)
    assert B.verify_receipt(request, result) == result
    for key in result:
        bad = dict(result, **{key: 'untrusted-sentinel'})
        refusal = B.verify_receipt(request, bad)
        assert refusal['status'] == 'REFUSED' and 'untrusted-sentinel' not in json.dumps(refusal)
    request_path = tmp_path/'request.json'; put(request_path, request)
    output = tmp_path/'receipt.json'
    assert B.main(['run', '--request-file', str(request_path), '--output-file', str(output)]) == 0
    assert B.main(['verify', '--request-file', str(request_path), '--receipt-file', str(output)]) == 0
    original = output.read_bytes()
    assert B.main(['run', '--request-file', str(request_path), '--output-file', str(output)]) == 1
    assert output.read_bytes() == original
    assert B.main(['untrusted-sentinel']) == 2
    assert 'untrusted-sentinel' not in capsys.readouterr().out
    (tmp_path/'gamma.json').write_bytes(b'{"access_token":"untrusted-sentinel"}')
    assert 'untrusted-sentinel' not in json.dumps(B.evaluate_request(request))
    link = tmp_path/'linked.json'
    os.link(tmp_path/'book.json', link)
    assert B.evaluate_request(request)['status'] == 'REFUSED'


def test_offline_no_network_account_or_orders(tmp_path, monkeypatch):
    request, _, _, _ = make_case(tmp_path)
    before = tree_hash(tmp_path)
    def forbidden(*args, **kwargs):
        raise AssertionError('forbidden dispatch')
    for module, name in ((socket, 'create_connection'), (subprocess, 'Popen'),
                         (B.H, 'run'), (B.scanner, 'run'), (B.H, 'run_controlled_hermes_research')):
        monkeypatch.setattr(module, name, forbidden)
    result = B.evaluate_request(request)
    assert result['status'] == 'MECHANICALLY_FEASIBLE_RESEARCH_ONLY', result
    assert B.verify_receipt(request, result) == result
    assert tree_hash(tmp_path) == before


def test_bound_output_field_coverage_and_denominators(tmp_path):
    request, _, _, _ = make_case(tmp_path)
    for value in [request, {}, None, dict(request, decision_ns=True), dict(request, outcome_index=2)]:
        result = B.evaluate_request(value)
        safe_result(result)
        assert result['accepted_production_methods'] == result['accepted_production_corpora'] == 0
        assert result['independent_event_groups'] == 0
    assert B.evaluate_request(request)['source_counts']['NWS'] == 3
    invalid = B.evaluate_request({})
    assert invalid['source_counts'] is None and invalid['unresolved_groups'] is None
    for field in request:
        for value in (None, [], {}, ''):
            bad = dict(request, **{field: value})
            assert B.evaluate_request(bad)['status'] == 'REFUSED'


@pytest.mark.parametrize('missing', ['active', 'closed', 'acceptingOrders', 'enableOrderBook',
                                    'secondsDelay', 'orderPriceMinTickSize'])
def test_unknown_venue_precedes_known_minimum_failure(tmp_path, missing):
    request, gamma, book, _ = make_case(tmp_path)
    gamma['orderMinSize'] = 5
    gamma.pop(missing)
    write_venue(request, gamma, book)
    result = B.evaluate_request(request)
    assert result['status'] == 'INCONCLUSIVE' and result['reason_codes'] == ['VENUE_UNKNOWN']
    assert result['execution_intent'] is None


@pytest.mark.parametrize('gamma_flag,book_flag,minimum,outcome,status,reason', [
    (True, True, 1, 0, 'MECHANICALLY_NOT_FEASIBLE', 'NATIVE_NOT_FEASIBLE'),
    ('absent', False, 5, 0, 'INCONCLUSIVE', 'VENUE_UNKNOWN'),
    (None, False, 5, 0, 'INCONCLUSIVE', 'VENUE_UNKNOWN'),
    (True, False, 1, 0, 'INCONCLUSIVE', 'VENUE_UNKNOWN'),
    (False, True, 1, 0, 'INCONCLUSIVE', 'VENUE_UNKNOWN'),
    (False, False, 1, 0, 'MECHANICALLY_FEASIBLE_RESEARCH_ONLY', None),
    (False, False, 1, 1, 'MECHANICALLY_FEASIBLE_RESEARCH_ONLY', None),
])
def test_native_single_leg_neg_risk_boundary(tmp_path, gamma_flag, book_flag, minimum,
                                           outcome, status, reason, monkeypatch):
    request, gamma, book, _ = make_case(tmp_path, outcome=outcome)
    gamma.update(negRisk=gamma_flag, orderMinSize=minimum)
    if gamma_flag == 'absent':
        gamma.pop('negRisk')
    book['neg_risk'] = book_flag
    write_venue(request, gamma, book)
    if reason is not None:
        def no_sizing(**kwargs):
            pytest.fail('unsupported or unknown neg-risk reached sizing')
        monkeypatch.setattr(B.sizing, 'size_order', no_sizing)
    result = B.evaluate_request(request)
    safe_result(result)
    assert result['status'] == status, result
    assert result['reason_codes'] == ([] if reason is None else [reason])
    if reason is not None:
        assert result['execution_intent'] is None


@pytest.mark.parametrize('book_flag', ['absent', None, 'false'])
def test_invalid_clob_neg_risk_retains_native_normalization(tmp_path, book_flag):
    request, gamma, book, _ = make_case(tmp_path)
    book['neg_risk'] = book_flag
    if book_flag == 'absent':
        book.pop('neg_risk')
    bundle = write_venue(request, gamma, book)
    assert bundle['venue_snapshot']['clob_source_state'] == 'INVALID'
    result = B.evaluate_request(request)
    safe_result(result)
    # Invalid native normalization clears the timestamp; retain the earlier book refusal.
    assert result['status'] == 'INCONCLUSIVE' and result['reason_codes'] == ['BOOK_STALE']
    assert result['execution_intent'] is None


def test_raw_code_drift_duplicate_json_and_path_boundaries(tmp_path, capsys):
    request, _, _, _ = make_case(tmp_path)
    started = Path(request['capture_dir'])/'capture-started.json'
    original = started.read_bytes()
    changed = json.loads(original)
    changed['source_hashes']['hunter'] = '0'*64
    put(started, changed)
    assert B.evaluate_request(request)['reason_codes'] == ['SOURCE_CODE_DRIFT']
    started.write_bytes(original)
    req = tmp_path/'request.json'
    req.write_text('{"schema_id":"untrusted-sentinel","schema_id":"duplicate"}')
    output = tmp_path/'out.json'
    assert B.main(['run','--request-file',str(req),'--output-file',str(output)]) == 1
    assert not output.exists()
    req.write_bytes(b'{')
    assert B.main(['run','--request-file',str(req),'--output-file',str(output)]) == 1
    req.write_bytes(b'x'*65_537)
    assert B.main(['run','--request-file',str(req),'--output-file',str(output)]) == 1
    assert 'untrusted-sentinel' not in capsys.readouterr().out
    assert B.evaluate_request(dict(request, capture_dir=str(B.ROOT)))['status'] == 'REFUSED'
    try:
        link = tmp_path/'symlink'
        link.symlink_to(Path(request['capture_dir']), target_is_directory=True)
    except OSError:
        return  # Host may disallow symlink creation; Linux and hosted tests exercise this case.
    assert B.evaluate_request(dict(request, capture_dir=str(link)))['status'] == 'REFUSED'


def test_restored_bytes_and_concurrent_store_change_refuse(tmp_path, monkeypatch):
    request, _, _, _ = make_case(tmp_path)
    path = Path(request['lifecycle_store_path'])
    reads = B._Reads()
    original = reads.read(str(path), 16*1024*1024)
    info = path.stat()
    path.write_bytes(original)
    os.utime(path, ns=(info.st_atime_ns, info.st_mtime_ns+B.NS))
    with pytest.raises(B.Refused) as failure:
        reads.check()
    assert failure.value.code == 'STORE_CHANGED'
    mechanics = B._mechanics
    def change_after_mechanics(*args):
        mechanics(*args)
        current = path.stat()
        os.utime(path, ns=(current.st_atime_ns, current.st_mtime_ns+B.NS))
    monkeypatch.setattr(B, '_mechanics', change_after_mechanics)
    result = B.evaluate_request(request)
    assert result['reason_codes'] == ['STORE_CHANGED'] and result['execution_intent'] is None
