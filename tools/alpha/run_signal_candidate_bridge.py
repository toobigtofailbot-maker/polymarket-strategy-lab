"""Finite offline rain-to-FOK research receipt; never an order or method approval."""
from __future__ import annotations

import argparse
from contextlib import ExitStack, contextmanager
from datetime import date
from decimal import Decimal, ROUND_FLOOR, localcontext
import hashlib
import json
from math import gcd
import os
from pathlib import Path
import stat
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.alpha import run_alpha_hunter as H
from tools.alpha import run_near_term_market_screener as scanner
from src.live_pilot import hunter_cycle as sizing, provenance
from src.execution_feasibility import build_execution_intent, assess_execution_feasibility
from src.execution_feasibility import models as M, public_market as venue
from src.strategy_lifecycle import load_strategy_lifecycle_store
from src.strategy_lifecycle.models import strict_json_loads

NS = 1_000_000_000
AGE = 30 * NS
CATEGORY = 'WEATHER_US_DAILY_RAIN'
REQUEST_FIELDS = frozenset(('schema_id schema_version analysis_mode capture_dir lifecycle_store_path '
    'expected_lifecycle_head strategy_version_id gamma_market_id outcome_index decision_ns venue_bundle_file').split())
BUNDLE_FIELDS = frozenset(('schema_id schema_version gamma_body_file clob_body_file '
    'acquisition_started_ns acquisition_completed_ns venue_snapshot').split())
RESULT_FIELDS = tuple(('schema_id schema_version receipt_id status reason_codes analysis_mode '
    'source_replay_state source_origin method_id source_method method_state binding_payload '
    'signal_binding_ref capture_manifest_sha256 native_manifest_sha256 lifecycle_head strategy_version_id '
    'gamma_market_id condition_id token_id outcome_index source_cutoff_ns native_evaluated_ns decision_ns '
    'event_deadline_ns venue_snapshot_id execution_intent native_assessment shares principal_usd '
    'conservative_fee_usd all_in_usd fee_policy_version fee_policy_expiry_ns source_counts unresolved_groups '
    'independent_event_groups accepted_production_methods accepted_production_corpora production_eligible '
    'permit signed_order no_live no_order real_event_to_order').split())
REASONS = frozenset(('INPUT_INVALID PATH_REFUSED SOURCE_UNVERIFIED SOURCE_CODE_DRIFT IDENTITY_MISMATCH '
    'VERSION_INVALID STORE_CHANGED CLOCK_INVALID SOURCE_EXPIRED BOOK_STALE VENUE_UNKNOWN FEE_UNKNOWN '
    'FEE_POLICY_EXPIRED MINIMUM_UNSATISFIABLE DEPTH_INSUFFICIENT SDK_GRID_UNSATISFIABLE '
    'NATIVE_NOT_FEASIBLE RECEIPT_MISMATCH OUTPUT_REFUSED').split())
STATUSES = frozenset(('REFUSED INCONCLUSIVE MECHANICALLY_NOT_FEASIBLE '
    'MECHANICALLY_FEASIBLE_RESEARCH_ONLY').split())
# Strings are recursively scanned; primitives are exempt because they contain no text.
OUTPUT_CLASSIFICATION = {k: ('exempt' if k in {
    'outcome_index', 'source_cutoff_ns', 'native_evaluated_ns', 'decision_ns', 'event_deadline_ns',
    'fee_policy_expiry_ns', 'unresolved_groups', 'independent_event_groups', 'accepted_production_methods',
    'accepted_production_corpora', 'production_eligible', 'permit', 'signed_order', 'no_live', 'no_order'
} else 'scanned') for k in RESULT_FIELDS}


class Refused(ValueError):
    def __init__(self, code, status='REFUSED'):
        self.code = code if code in REASONS else 'INPUT_INVALID'
        self.status = status if status in STATUSES else 'REFUSED'


def require(ok, code='INPUT_INVALID', status='REFUSED'):
    if not ok:
        raise Refused(code, status)


def canonical(value):
    return M.canonical_json_bytes(value)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def _seal(result):
    body = {k: v for k, v in result.items() if k != 'receipt_id'}
    result['receipt_id'] = 'signalcandidate:sha256:' + digest(canonical({'receipt': body}))
    require(set(result) == set(RESULT_FIELDS))
    # A hand-built dictionary is not a full output-surface scan unless a field-coverage test
    # proves it covers every public field.
    require(not H.S.SECRET.search(canonical(result)))
    return result


def _empty(code=None, status='REFUSED'):
    result = dict.fromkeys(RESULT_FIELDS)
    result.update(schema_id='signal-candidate-receipt', schema_version='1.0.0', status=status,
        reason_codes=[] if code is None else [code], source_replay_state='UNVERIFIED',
        source_origin='UNVERIFIED', method_state='METHOD_NOT_QUALIFIED',
        independent_event_groups=0, accepted_production_methods=0, accepted_production_corpora=0,
        production_eligible=False, no_live=True, no_order=True, real_event_to_order='UNMEASURED')
    return result


def _safe(value, *, directory=False):
    require(type(value) is str and 0 < len(value) <= 4096, 'PATH_REFUSED')
    path = Path(value)
    require('..' not in path.parts, 'PATH_REFUSED')
    try:
        path = H.S.safe(path, directory=directory)
        if path.exists():
            info = path.lstat()
            require(stat.S_ISDIR(info.st_mode) if directory else
                    stat.S_ISREG(info.st_mode) and info.st_nlink == 1, 'PATH_REFUSED')
        return path
    except Refused:
        raise
    except Exception:
        raise Refused('PATH_REFUSED') from None


@contextmanager
def _parent_handle(path):
    """Pin directories: no-follow openat on POSIX; deny rename/delete on Windows."""
    parents = list(reversed(path.parent.parents)) + [path.parent]
    with ExitStack() as stack:
        if os.name == 'nt':
            import ctypes
            from ctypes import wintypes
            kernel = ctypes.WinDLL('kernel32', use_last_error=True)
            create = kernel.CreateFileW
            create.argtypes = (wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, wintypes.LPVOID,
                               wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE)
            create.restype = wintypes.HANDLE
            close = kernel.CloseHandle
            close.argtypes = (wintypes.HANDLE,)
            for parent in parents:
                _safe(str(parent), directory=True)
                # READ_ATTRIBUTES, SHARE_READ|SHARE_WRITE (no DELETE), OPEN_EXISTING,
                # BACKUP_SEMANTICS|OPEN_REPARSE_POINT. No file content is read here.
                handle = create(str(parent), 0x80, 3, None, 3, 0x02200000, None)
                require(handle != wintypes.HANDLE(-1).value, 'PATH_REFUSED')
                stack.callback(close, handle)
                _safe(str(parent), directory=True)
            yield None
        else:
            fd = os.open(path.anchor, os.O_RDONLY | os.O_DIRECTORY)
            stack.callback(os.close, fd)
            for part in path.parent.parts[1:]:
                fd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                stack.callback(os.close, fd)
            yield fd


class _Reads:
    """One invocation's bounded read set; changed source bytes invalidate the result."""
    def __init__(self):
        self.files = {}
        self.capture_files = None

    def read(self, value, maximum):
        path = _safe(value)
        with _parent_handle(path) as parent:
            _safe(str(path))
            flags = os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_BINARY', 0)
            fd = os.open(path.name if parent is not None else str(path), flags, dir_fd=parent)
            with os.fdopen(fd, 'rb') as stream:
                before = os.fstat(stream.fileno())
                require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1 and
                        before.st_size <= maximum and os.path.samestat(before, path.lstat()), 'PATH_REFUSED')
                _safe(str(path))  # Detect final-component replacement before reading its contents.
                raw = stream.read(maximum + 1)
                after = os.fstat(stream.fileno())
                require(len(raw) <= maximum and
                        (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) ==
                        (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns), 'INPUT_INVALID')
        item = (maximum, digest(raw), before.st_dev, before.st_ino,
                before.st_size, before.st_mtime_ns, before.st_ctime_ns)
        require(path not in self.files or self.files[path] == item, 'STORE_CHANGED')
        self.files[path] = item
        return raw

    def document(self, value, maximum):
        raw = self.read(value, maximum)
        require(not H.S.SECRET.search(raw))
        return strict_json_loads(raw.decode('utf-8'))

    def check(self):
        for path, item in tuple(self.files.items()):
            self.read(str(path), item[0])
        if self.capture_files is not None:
            root, names = self.capture_files
            require({str(p.relative_to(root)) for p in root.rglob('*') if p.is_file()} == names,
                    'STORE_CHANGED')


def _shape(value, fields, schema):
    require(type(value) is dict and set(value) == fields)
    require(value['schema_id'] == schema and value['schema_version'] == '1.0.0')
    canonical(value)  # Native limits: no floats/nonfinite values, depth12/nodes20000.


def _time(value):
    require(type(value) is int and 0 < value <= 2**63-1, 'CLOCK_INVALID')
    return value


def _source(reads, request):
    root = _safe(request['capture_dir'], directory=True)
    try:
        provenance.bounded_inventory(root)
        files = [p for p in root.rglob('*') if p.is_file()]
        reads.capture_files = (root, {str(p.relative_to(root)) for p in files})
        for path in files:
            reads.read(str(path), 16*1024*1024 if '.sqlite3' in path.name else 4_000_000)
        report = provenance.verify_capture(root)
        require(report['status'] == 'REPLAY_VERIFIED',
                'SOURCE_CODE_DRIFT' if report['reason'] == 'SOURCE_CODE_DRIFT' else 'SOURCE_UNVERIFIED')
        op = root/'op-000001'
        manifest = reads.document(str(op/'manifest.json'), 4_000_000)
        rows = [m for m in manifest['markets'] if m['gamma_market_id'] == request['gamma_market_id']]
        require(len(rows) == 1, 'IDENTITY_MISMATCH')
        market = rows[0]
        require(market['category'] == CATEGORY and market['reason'] is None and
                market.get('forecast', {}).get('method') == H.METHOD_RAIN, 'SOURCE_UNVERIFIED')
        tokens = market['tokens']
        for index, token in enumerate(tokens):
            selected = [r for r in manifest['tokens'] if r['gamma_market_id'] == market['gamma_market_id']
                        and r['token_id'] == token]
            require(len(selected) == 1 and selected[0]['outcome_index'] == index and
                    selected[0]['condition_id'] == market['condition_id'], 'IDENTITY_MISMATCH')
        receipts = [H.S.read(p) for p in sorted(op.glob('receipt-*.json'))]
        raw = [item for item in H.rain_candidates(op, H.by_url(receipts), manifest['clocks'])
               if item[1] == market['gamma_market_id']]
        require(len(raw) == 1 and not raw[0][3], 'IDENTITY_MISMATCH')
        target, semantics, bound_tokens = H.rain_rule(raw[0][2], raw[0][0][0])
        require(bound_tokens == tokens and semantics.rule_text_sha256 == market['rule_sha256'],
                'IDENTITY_MISMATCH')
        station = H.data(op, H.by_url(receipts).get(H.NWS+'stations/'+market['station']))
        meta = H.NDFD.parse_nws_station(H.station_doc(station), market['station'])
        offset = H.NDFD.standard_utc_offset_minutes(meta.time_zone, target)
        start, _ = H.NDFD.climate_day_window(target, offset)
        deadline = int(start.timestamp()) * NS
        cutoff = manifest['clocks']['source_cutoff_ns']
        # The native cutoff freezes forecast sources; CLOB acquisition follows it.
        require(all(r['received_ns'] <= cutoff for r in receipts
                    if r['state'] == 'AVAILABLE' and r['url'].startswith(H.NWS)), 'CLOCK_INVALID')
        payload = dict(schema_id='signal-binding', schema_version='1.0.0', method_id='RAIN_NWS_V1',
            source_method=H.METHOD_RAIN, source_hashes=H.S.read(root/'capture-started.json')['source_hashes'],
            native_manifest_sha256=report['native_manifest_sha256'], gamma_market_id=market['gamma_market_id'],
            condition_id=market['condition_id'], token_ids=tokens, resolution_rule_sha256=market['rule_sha256'],
            target_day=market['target_day'], station_id=market['station'], event_deadline_ns=deadline,
            source_cutoff_ns=cutoff)
        return report, payload, manifest['clocks']['evaluated_ns']
    except Refused:
        raise
    except Exception:
        raise Refused('SOURCE_UNVERIFIED') from None


def _version(reads, request, binding):
    path = request['lifecycle_store_path']
    reads.read(path, 16*1024*1024)
    # A hot SQLite sidecar would be mutable uncommitted input, not a frozen read source.
    require(not any(Path(path + suffix).exists() for suffix in ('-wal', '-shm', '-journal')),
            'VERSION_INVALID')
    loaded = load_strategy_lifecycle_store(path)
    require(loaded.is_valid and loaded.snapshot is not None, 'VERSION_INVALID')
    snapshot = loaded.snapshot
    require(snapshot.store_head_entry_hash == request['expected_lifecycle_head'], 'STORE_CHANGED')
    version = snapshot.version_by_id(request['strategy_version_id'])
    require(version is not None and version.created_time_ns <= request['decision_ns'] and
            snapshot.health_of(version.strategy_version_id) != 'RETIRED', 'VERSION_INVALID')
    require([r for r in version.evidence_refs if r.startswith('signalbinding:sha256:')] == [binding],
            'VERSION_INVALID')
    return version, snapshot.store_head_entry_hash


def _venue(reads, request, payload):
    bundle = reads.document(request['venue_bundle_file'], 1_048_576)
    _shape(bundle, BUNDLE_FIELDS, 'signal-candidate-venue-bundle')
    gamma = reads.read(bundle['gamma_body_file'], 2_000_000)
    clob = reads.read(bundle['clob_body_file'], 2_000_000)
    require(not H.S.SECRET.search(gamma) and not H.S.SECRET.search(clob))
    token = payload['token_ids'][request['outcome_index']]
    snapshot = venue.build_public_venue_snapshot(gamma_market_id=payload['gamma_market_id'],
        condition_id=payload['condition_id'], token_id=token,
        acquisition_started_ns=_time(bundle['acquisition_started_ns']),
        acquisition_completed_ns=_time(bundle['acquisition_completed_ns']),
        gamma=venue.SourceFetchResult('BODY', gamma), clob=venue.SourceFetchResult('BODY', clob))
    require(snapshot.to_mapping() == bundle['venue_snapshot'], 'IDENTITY_MISMATCH')
    raw_gamma = H.S.decode(gamma)
    try:
        target, rule, tokens = H.rain_rule(raw_gamma, date.fromisoformat(payload['target_day']))
        require(raw_gamma['id'] == payload['gamma_market_id'] and
                raw_gamma['conditionId'] == payload['condition_id'] and tokens == payload['token_ids'] and
                rule.station_id == payload['station_id'] and
                rule.rule_text_sha256 == payload['resolution_rule_sha256'], 'IDENTITY_MISMATCH')
    except Refused:
        raise
    except Exception:
        raise Refused('IDENTITY_MISMATCH') from None
    return snapshot


def _mechanics(result, request, version, snapshot):
    now = request['decision_ns']
    require(snapshot.acquisition_completed_ns <= now, 'CLOCK_INVALID')
    require(snapshot.book_timestamp_ns is not None and
            0 <= now-snapshot.acquisition_completed_ns <= AGE and
            0 <= now-snapshot.book_timestamp_ns <= AGE, 'BOOK_STALE', 'INCONCLUSIVE')
    require(snapshot.gamma_source_state == snapshot.clob_source_state == 'AVAILABLE' and
            snapshot.asks and snapshot.gamma_min_order_notional_usd is not None and
            snapshot.book_min_order_size_raw is not None, 'VENUE_UNKNOWN', 'INCONCLUSIVE')
    # This research contract gives unknown venue dimensions precedence over sizing failures.
    require(all(type(value) is bool for value in (snapshot.active, snapshot.closed,
                snapshot.accepting_orders, snapshot.enable_order_book,
                snapshot.gamma_neg_risk, snapshot.book_neg_risk)) and
            snapshot.seconds_delay is not None and snapshot.gamma_tick_size is not None and
            snapshot.gamma_tick_size == snapshot.book_tick_size and
            snapshot.gamma_neg_risk == snapshot.book_neg_risk, 'VENUE_UNKNOWN', 'INCONCLUSIVE')
    require(now < scanner.FEE_EXPIRY, 'FEE_POLICY_EXPIRED', 'INCONCLUSIVE')
    require(snapshot.fee_exponent == '1', 'FEE_UNKNOWN', 'INCONCLUSIVE')
    try:
        rate, exponent = sizing.fee_bound(snapshot, CATEGORY, Decimal(scanner.FEE_RATES['weather']))
    except Exception:
        raise Refused('FEE_UNKNOWN', 'INCONCLUSIVE') from None
    result.update(fee_policy_version=scanner.FEE_POLICY, fee_policy_expiry_ns=scanner.FEE_EXPIRY)
    try:
        gamma_min, book_min = sizing._venue(snapshot, result)
    except Exception:
        raise Refused('NATIVE_NOT_FEASIBLE', 'MECHANICALLY_NOT_FEASIBLE') from None
    ask = Decimal(snapshot.asks[0][0])
    depth = sum((Decimal(q) for p, q in snapshot.asks if Decimal(p) == ask), Decimal(0))
    try:
        q, _ = sizing.size_order(ask=ask, depth=depth, rate=rate, exponent=exponent,
            cap=Decimal(5), floor=Decimal(2), gamma_min=gamma_min,
            book_min=book_min, seconds_delay=snapshot.seconds_delay)
    except Exception as error:
        code = getattr(error, 'code', '')
        reason = ('MINIMUM_UNSATISFIABLE' if code == 'MINIMUM_UNSATISFIABLE_WITHIN_FEE_INCLUSIVE_CAP'
                  else 'DEPTH_INSUFFICIENT' if code == 'DEPTH_BELOW_SIZE' else 'NATIVE_NOT_FEASIBLE')
        raise Refused(reason, 'MECHANICALLY_NOT_FEASIBLE') from None
    # Exact SDK principal grid without a potentially unbounded decrement loop.
    numerator, denominator = ask.as_integer_ratio()
    step = Decimal('0.01') * (denominator // gcd(numerator, denominator))
    q = (q / step).to_integral_value(rounding=ROUND_FLOOR) * step
    require(q > 0, 'SDK_GRID_UNSATISFIABLE', 'MECHANICALLY_NOT_FEASIBLE')
    fee = sizing.fee_max(q, ask, rate, exponent)
    principal = q * ask
    require(2 <= principal+fee <= 5 and principal >= Decimal(snapshot.gamma_min_order_notional_usd)
            and q >= Decimal(snapshot.book_min_order_size_raw) and depth >= q,
            'MINIMUM_UNSATISFIABLE', 'MECHANICALLY_NOT_FEASIBLE')
    intent = build_execution_intent(strategy_version=version, gamma_market_id=snapshot.gamma_market_id,
        condition_id=snapshot.condition_id, token_id=snapshot.token_id, side='BUY',
        execution_style='AGGRESSIVE_TAKER', order_type='FOK', requested_shares=M.decimal_text(q),
        price_limit=M.decimal_text(ask), post_only=False, information_cutoff_ns=now,
        max_public_data_age_ns=AGE)
    assessment = assess_execution_feasibility(intent, snapshot, evaluated_at_ns=now)
    result.update(execution_intent=intent.to_mapping(), native_assessment=assessment.to_mapping(),
        shares=M.decimal_text(q), principal_usd=M.decimal_text(principal),
        conservative_fee_usd=M.decimal_text(fee), all_in_usd=M.decimal_text(principal+fee))
    require(assessment.status == 'FEASIBLE', 'NATIVE_NOT_FEASIBLE',
            'INCONCLUSIVE' if assessment.status == 'INCONCLUSIVE' else 'MECHANICALLY_NOT_FEASIBLE')
    result.update(status='MECHANICALLY_FEASIBLE_RESEARCH_ONLY', reason_codes=[])


def _evaluate(request, reads):
    result = _empty()
    try:
        _shape(request, REQUEST_FIELDS, 'signal-candidate-request')
        require(len(canonical(request)) <= 65_536)
        require(request['analysis_mode'] in ('SYNTHETIC_ONLY', 'RESEARCH_HISTORICAL'))
        require(type(request['outcome_index']) is int and request['outcome_index'] in (0, 1))
        _time(request['decision_ns'])
        M.validate_gamma_market_id(request['gamma_market_id'])
        require(type(request['expected_lifecycle_head']) is str and
                type(request['strategy_version_id']) is str)
        report, payload, evaluated = _source(reads, request)
        binding = 'signalbinding:sha256:' + digest(canonical({'binding_payload': payload}))
        result.update(analysis_mode=request['analysis_mode'], source_replay_state='REPLAY_VERIFIED',
            method_id=payload['method_id'], source_method=payload['source_method'], binding_payload=payload,
            signal_binding_ref=binding, capture_manifest_sha256=report['capture_manifest_sha256'],
            native_manifest_sha256=report['native_manifest_sha256'], gamma_market_id=payload['gamma_market_id'],
            condition_id=payload['condition_id'], token_id=payload['token_ids'][request['outcome_index']],
            outcome_index=request['outcome_index'], source_cutoff_ns=payload['source_cutoff_ns'],
            native_evaluated_ns=evaluated, decision_ns=request['decision_ns'],
            event_deadline_ns=payload['event_deadline_ns'], source_counts=report['source_counts'],
            unresolved_groups=report['unresolved_groups'])
        version, head = _version(reads, request, binding)
        result.update(strategy_version_id=version.strategy_version_id, lifecycle_head=head)
        now = request['decision_ns']
        require(payload['source_cutoff_ns'] <= evaluated <= now, 'CLOCK_INVALID')
        require(now < min(evaluated+AGE, payload['event_deadline_ns']), 'SOURCE_EXPIRED')
        snapshot = _venue(reads, request, payload)
        result['venue_snapshot_id'] = snapshot.venue_snapshot_id
        with localcontext() as ctx:
            ctx.prec = 200
            _mechanics(result, request, version, snapshot)
    except Refused as error:
        result.update(status=error.status, reason_codes=[error.code])
    except Exception:
        result = _empty('INPUT_INVALID')
    reads.check()
    return _seal(result)


def evaluate_request(request):
    """Evaluate explicit offline files; no store creation, acquisition or dispatch."""
    try:
        return _evaluate(request, _Reads())
    except Exception:
        return _seal(_empty('STORE_CHANGED'))


def verify_receipt(request, receipt):
    """Cold rederive all inputs and require exact closed receipt equality."""
    expected = evaluate_request(request)
    if type(receipt) is dict and type(receipt.get('production_eligible')) is bool:
        try:
            if canonical(receipt) == canonical(expected):
                return expected
        except Exception:
            pass
    return _seal(_empty('RECEIPT_MISMATCH'))


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        raise Refused('INPUT_INVALID')


def main(argv=None):
    try:
        parser = _Parser(description=__doc__, add_help=False)
        parser.add_argument('command', choices=('run', 'verify'))
        parser.add_argument('--request-file', required=True)
        parser.add_argument('--output-file')
        parser.add_argument('--receipt-file')
        args = parser.parse_args(argv)
        require((args.command == 'run' and args.output_file and not args.receipt_file) or
                (args.command == 'verify' and args.receipt_file and not args.output_file))
    except Exception:
        print(canonical(_seal(_empty('INPUT_INVALID'))).decode())
        return 2
    try:
        reads = _Reads()
        request = reads.document(args.request_file, 65_536)
        result = _evaluate(request, reads)
        if args.command == 'verify':
            receipt = reads.document(args.receipt_file, 1_048_576)
            require(canonical(receipt) == canonical(result), 'RECEIPT_MISMATCH')
        else:
            output = _safe(args.output_file)
            require(not output.exists() and output not in reads.files and
                    not any(output.is_relative_to(Path(p)) for p in (request['capture_dir'],)),
                    'OUTPUT_REFUSED')
            with _parent_handle(output) as parent:
                reads.check()
                flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_NOFOLLOW', 0)
                fd = os.open(output.name if parent is not None else str(output), flags, 0o600, dir_fd=parent)
                with os.fdopen(fd, 'wb') as stream:
                    stream.write(canonical(result)+b'\n')
                    stream.flush()
                    os.fsync(stream.fileno())
        print(canonical(result).decode())
        return 1 if result['status'] == 'REFUSED' else 0
    except Refused as error:
        result = _seal(_empty(error.code))
    except Exception:
        result = _seal(_empty('OUTPUT_REFUSED'))
    print(canonical(result).decode())
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
