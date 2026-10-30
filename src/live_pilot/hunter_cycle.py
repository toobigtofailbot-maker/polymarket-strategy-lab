"""S10-ALPHA-HUNTER-PILOT-02: one finite, default-off hunter pilot cycle; no activation on import.

Per invocation: run lock -> policy/owner validation -> kill latch -> native
reconcile -> manual kill -> reduce-only exit phase -> automatic stops -> entry
phase -> one durable terminal.  At most one economic mutation, never a loop,
retry, timer or daemon.  Every protected operation stays in the native Gate C ->
LIVE-ORCH -> Gate B kernel under the opt-in HUNTER_PILOT_02 capital profile.
Hunter output is input, never authority.  Merged code is dormant; activation,
custody, provider budget and capital are separate owner decisions.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from decimal import ROUND_CEILING, ROUND_FLOOR, Decimal, localcontext
import json
import os
from pathlib import Path
import re
from typing import Callable, Mapping
import uuid

from src.execution_gateway import live_orch as native
from src.execution_gateway.gate_b import (
    CredentialDirectorySessionKeyProvider,
    InteractiveGateBSecretProvider,
)
from src.execution_gateway.gateway import GatewayError, _canonical_decimal
from src.execution_feasibility import assess_execution_feasibility, build_execution_intent
from src.exploratory_gate_c import build_exploratory_gate_c_permit, evaluate_exploratory_gate_c
from src.live_pilot import pilot as v1
from src.research_runtime.hermes_controlled_runtime.strategy_manager import load_hermes_strategy_manager_store
from src.strategy_lifecycle import load_strategy_lifecycle_store

NS = v1.NS
DAY = v1.DAY
PROFILE = native.HUNTER_PILOT_02_PROFILE
POLICY_SCHEMA = ('polymarket-hunter-pilot-policy', '2.0.0')
EDGE_POLICY_SCHEMA = ('polymarket-hunter-pilot-policy', '3.0.0')
EDGE_FIELDS = {'activation_id', 'activation_ledger_head', 'previous_session_sha256', 'provider_max_rolling24h_usd', 'first_canary_receipt_sha256'}
OWNER_SCHEMA = ('polymarket-hunter-pilot-owner-activation', '2.0.0')
TERMINAL_SCHEMA = ('polymarket-hunter-pilot-terminal', '2.0.0')
CATEGORIES = ('SPORTS_NBA_MONEYLINE', 'WEATHER_US_DAILY_RAIN')
# Official fees page (read 2026-10-27): Sports 0.05, Weather 0.05.
DOCUMENTED_TAKER_RATE = {'SPORTS_NBA_MONEYLINE': Decimal('0.05'), 'WEATHER_US_DAILY_RAIN': Decimal('0.05')}
CUSTODY_PROVIDERS = {'ATTENDED_TTY': ('OWNER', 'InteractiveGateBSecretProvider'),
                     'SESSION_KEY_CREDENTIAL_DIRECTORY': ('SESSION_KEY', 'CredentialDirectorySessionKeyProvider')}
SESSION_FIELDS = {'session_key_address', 'session_key_scopes', 'session_key_valid_until_utc'}
SESSION_KEY_MARGIN_NS = 86400 * NS
SHARE_QUANTUM = Decimal('0.01')
USD_QUANTUM = Decimal('0.00001')
RESIDUAL_COST_PER_SHARE = Decimal('0.005')
DECIMAL_BOUNDS = {  # key: (lower, upper); inclusive, never clamped
    'max_order_commitment_usd': (Decimal('2'), Decimal('5')),
    'max_simultaneous_exposure_usd': (Decimal('0.00001'), Decimal('30')),
    'min_free_collateral_after_admission_usd': (Decimal('50'), Decimal('100')),
    'net_loss_budget_usd': (Decimal('0.00001'), Decimal('30')),
}
INTEGER_BOUNDS = {'consecutive_loss_limit': (1, 5), 'loss_pause_s': (7200, 2**31),
                  'max_hunter_age_s': (1, 1800), 'max_hermes_assessment_age_s': (1, 86400)}
POLICY_KEYS = {
    'schema_id', 'schema_version', 'public_wallet', 'public_signer', 'release_sha', 'host', 'state_root',
    'lifecycle_store_path', 'hermes_store_path', 'categories', 'strategy_version_ids', 'order_type',
    'valid_from_utc', 'valid_until_utc', 'experimental_margin_usd', 'min_order_commitment_usd', 'custody',
    *DECIMAL_BOUNDS, *INTEGER_BOUNDS,
}
OWNER_FIELDS = v1.OWNER_KEYS | {'initial_equity_usd', 'dedicated_wallet'}
ROW_REASONS_ALLOWED = (None, 'SMALL_ORDER_UNFIT', 'CAPACITY_NOT_SELECTED')
ABSTAIN_CODES = frozenset({
    'HUNTER_ROW_INELIGIBLE', 'HERMES_EVIDENCE_ABSENT', 'HUNTER_EVIDENCE_STALE', 'PILOT_EVENT_STARTED',
    'CLIMATE_DAY_STARTED', 'FEE_CONFIG_UNKNOWN', 'MINIMUM_UNSATISFIABLE_WITHIN_FEE_INCLUSIVE_CAP',
    'DEPTH_BELOW_SIZE', 'SECONDS_DELAY_UNSUPPORTED', 'PILOT_MARKET_MISMATCH', 'PILOT_VENUE_INVALID',
    'PILOT_MARGIN_NOT_MET', 'PILOT_STRATEGY_UNAVAILABLE', 'PILOT_ASSESSMENT_STALE',
})
PUBLIC_CODES = frozenset({
    'PILOT_INPUT_INVALID', 'PILOT_PATH_INVALID', 'PILOT_POLICY_INVALID', 'PILOT_TIME_INVALID',
    'PILOT_OWNER_RECORD_INVALID', 'PILOT_OWNER_RECORD_DIGEST_MISMATCH', 'PILOT_OWNER_RECORD_SCOPE_MISMATCH',
    'PILOT_OWNER_RECORD_WINDOW_INVALID', 'PILOT_RUN_BUSY', 'PILOT_STATE_UNAVAILABLE', 'PILOT_CUSTODY_UNAVAILABLE',
    'SESSION_KEY_ATTESTATION_INVALID', 'CUSTODY_SUSPENDED', 'PILOT_RECONCILIATION_BLOCKED', 'PILOT_KILLED',
    'INITIAL_EQUITY_UNVERIFIED', 'HUNTER_INTAKE_INVALID', 'LOSS_BREAKER_PAUSED', 'LOSS_DIAGNOSIS_INVALID',
    'PILOT_NO_ELIGIBLE_PAIR', 'PILOT_EXIT_HOLD', 'PILOT_PERMIT_REFUSED', 'PILOT_PREFLIGHT_REFUSED',
    'PILOT_NATIVE_REFUSED', 'PILOT_NATIVE_RESULT', 'PILOT_GUARD_MISSING', 'PILOT_STRATEGY_UNAVAILABLE',
    'PILOT_ASSESSMENT_UNAVAILABLE',
    *(f'PILOT_GUARD_REFUSED:{s}' for s in ('POLICY_CHANGED', 'KILL', 'MARKET_BINDING', 'OWNER_WINDOW',
      'FRESHNESS', 'ORDER_BOUNDS', 'EXPOSURE', 'NET_LOSS_BUDGET', 'CUSTODY')),
}) | ABSTAIN_CODES
NATIVE_CODES = PUBLIC_CODES | v1.NATIVE_CODES | frozenset({
    'ONE_SELL_ATTEMPTED', 'SELL_NOT_PILOT_OWNED', 'SELL_TRADES_NOT_FINAL', 'SELL_OPEN_ORDER_PRESENT',
    'SELL_ALREADY_PENDING', 'SELL_EXCEEDS_RECONCILED_POSITION', 'ORDER_BELOW_PROFILE_FLOOR',
    'SIDE_UNSUPPORTED_FIRST_CANARY', 'SIGNING_IDENTITY_INVALID', 'AUTHENTICATION_FAILED',
    'SECRET_INPUT_INVALID', 'ORDER_ENCODING_UNSUPPORTED',
})
# Venue authentication rejections that latch custody suspension under SESSION_KEY.
CUSTODY_REJECTION_CODES = frozenset({'AUTHENTICATION_FAILED', 'SIGNER_MISMATCH', 'WALLET_MISMATCH'})

_require, _digest, _canonical, _path, _read, _decimal, _time, _utc = (
    v1._require, v1._digest, v1._canonical, v1._path, v1._read, v1._decimal, v1._time, v1._utc)


@dataclass
class HunterCycleDependencies:
    """Explicit seams: the native LIVE-ORCH dependencies plus a resolved-payout source.

    ``resolved_payout(token_id)`` returns the public resolved payout per share or
    ``None``; an unknown payout is counted as zero (a loss), never as a gain.
    """

    native: native.LiveOrchDependencies = field(default_factory=native.LiveOrchDependencies)
    resolved_payout: Callable[[str], Decimal | None] = lambda _token: None


# --------------------------------------------------------------------------- policy

def _load(policy_path, owner_record_path, owner_record_sha256, state_root, now):
    """Strict canonical v2 policy and owner record; refusal before any native call."""
    raw = _read(policy_path)
    policy = v1._json(raw)
    edge = type(policy) is dict and (policy.get('schema_id'), policy.get('schema_version')) == EDGE_POLICY_SCHEMA
    _require(type(policy) is dict and set(policy) == (POLICY_KEYS | EDGE_FIELDS if edge else POLICY_KEYS) and _canonical(policy) == raw
             and (policy['schema_id'], policy['schema_version']) in (POLICY_SCHEMA, EDGE_POLICY_SCHEMA)
             and policy['order_type'] == 'FOK' and policy['custody'] in CUSTODY_PROVIDERS, 'PILOT_POLICY_INVALID')
    _require(type(policy['host']) is dict and set(policy['host']) == v1.HOST_KEYS
             and type(policy['host']['ssh_port']) is int and 1 <= policy['host']['ssh_port'] <= 65535,
             'PILOT_POLICY_INVALID')
    for key in v1.HOST_KEYS - {'ssh_port'}:
        _path(policy['host'][key])
    for key in ('public_wallet', 'public_signer'):
        _require(type(policy[key]) is str and re.fullmatch(r'0x[0-9a-fA-F]{40}', policy[key]) is not None,
                 'PILOT_POLICY_INVALID')
    _require(type(policy['release_sha']) is str and re.fullmatch(r'[0-9a-f]{40}', policy['release_sha']) is not None,
             'PILOT_POLICY_INVALID')
    for key in ('state_root', 'lifecycle_store_path', 'hermes_store_path'):
        _path(policy[key])
    _require(policy['state_root'] == str(state_root), 'PILOT_POLICY_INVALID')
    categories, versions = policy['categories'], policy['strategy_version_ids']
    _require(type(categories) is list and categories and categories == sorted(set(categories))
             and all(c in CATEGORIES for c in categories) and type(versions) is dict
             and set(versions) == set(categories) and len(set(versions.values())) == len(versions)
             and all(type(v) is str and re.fullmatch(r'strategyversion:sha256:[0-9a-f]{64}', v)
                     for v in versions.values()), 'PILOT_POLICY_INVALID')
    bounds = dict(DECIMAL_BOUNDS)
    if edge:
        bounds.update(max_order_commitment_usd=(Decimal(2), Decimal(10)),
                      max_simultaneous_exposure_usd=(Decimal('0.00001'), Decimal(10)),
                      min_free_collateral_after_admission_usd=(Decimal(90), Decimal(100)),
                      net_loss_budget_usd=(Decimal('0.00001'), Decimal(10)))
        for key in ('activation_id', 'activation_ledger_head'):
            _require(type(policy[key]) is str and re.fullmatch('[0-9a-f]{64}', policy[key]), 'PILOT_POLICY_INVALID')
        for key in ('previous_session_sha256', 'first_canary_receipt_sha256'):
            _require(policy[key] is None or type(policy[key]) is str and re.fullmatch('[0-9a-f]{64}', policy[key]), 'PILOT_POLICY_INVALID')
        _require(0 <= _decimal(policy['provider_max_rolling24h_usd']) <= 2, 'PILOT_POLICY_INVALID')
    for key, (low, high) in bounds.items():
        _require(low <= _decimal(policy[key]) <= high, 'PILOT_POLICY_INVALID')
    _require(Decimal(2) <= _decimal(policy['min_order_commitment_usd']) <= _decimal(policy['max_order_commitment_usd'])
             and _decimal(policy['experimental_margin_usd']) >= 0, 'PILOT_POLICY_INVALID')
    for key, (low, high) in INTEGER_BOUNDS.items():
        _require(type(policy[key]) is int and low <= policy[key] <= high, 'PILOT_POLICY_INVALID')
    start, end = _utc(policy['valid_from_utc']), _utc(policy['valid_until_utc'])
    _require(0 < end - start <= 7 * DAY and start <= now < end, 'PILOT_POLICY_INVALID')
    policy_hash = _digest(raw)
    record_raw = _read(owner_record_path)
    _require(type(owner_record_sha256) is str and re.fullmatch(r'[0-9a-f]{64}', owner_record_sha256) is not None
             and _digest(record_raw) == owner_record_sha256, 'PILOT_OWNER_RECORD_DIGEST_MISMATCH')
    session = policy['custody'] == 'SESSION_KEY_CREDENTIAL_DIRECTORY'
    try:
        record = v1._json(record_raw)
        # Session-key attestation keys are required iff SESSION_KEY custody (exact keys).
        _require(type(record) is dict and set(record) == ((OWNER_FIELDS | (EDGE_FIELDS if edge else set())) | (SESSION_FIELDS if session else set()))
                 and _canonical(record) == record_raw
                 and (record['schema_id'], record['schema_version']) == (OWNER_SCHEMA[0], '3.0.0' if edge else '2.0.0')
                 and record['dedicated_wallet'] is True
                 and Decimal(0) < _decimal(record['initial_equity_usd']) <= Decimal(100), 'PILOT_OWNER_RECORD_INVALID')
    except Exception:
        raise GatewayError('PILOT_OWNER_RECORD_INVALID') from None
    _require(record['policy_sha256'] == policy_hash and all(record[k] == policy[k] for k in
             ('public_wallet', 'public_signer', 'release_sha', 'state_root')), 'PILOT_OWNER_RECORD_SCOPE_MISMATCH')
    try:
        a, b = _utc(record['valid_from_utc']), _utc(record['valid_until_utc'])
        _require(start <= a < b <= end and a <= now < b, 'PILOT_OWNER_RECORD_WINDOW_INVALID')
    except Exception:
        raise GatewayError('PILOT_OWNER_RECORD_WINDOW_INVALID') from None
    if edge:
        _require(all(record[k] == policy[k] for k in EDGE_FIELDS), 'PILOT_OWNER_RECORD_SCOPE_MISMATCH')
    if session:
        try:
            until = _utc(record['session_key_valid_until_utc'])
            _require(record['session_key_address'] == policy['public_signer']
                     and record['session_key_scopes'] in ((['CLOB'],) if edge else (['CLOB'], ['ALL']))
                     and now < until - SESSION_KEY_MARGIN_NS, 'SESSION_KEY_ATTESTATION_INVALID')
        except Exception:
            raise GatewayError('SESSION_KEY_ATTESTATION_INVALID') from None
        b = min(b, until - SESSION_KEY_MARGIN_NS)
    # Retain the narrower immutable owner deadline for the guard's final clock check.
    return dict(policy, _owner_window=(a, b), _initial_equity=_decimal(record['initial_equity_usd'])), policy_hash


@contextmanager
def _run_lock(root):
    """Kernel-held per-state-root run lock (same primitive as the v1 pilot)."""
    flags = os.O_RDWR | os.O_CREAT | getattr(os, 'O_NOFOLLOW', 0)
    fd = os.open(_path(root / 'hunter-pilot-run.lock'), flags, 0o600)
    with os.fdopen(fd, 'r+b') as handle:
        try:
            if os.name == 'nt':
                import msvcrt
                if not handle.read(1):
                    handle.write(b'0')
                    handle.flush()
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            raise GatewayError('PILOT_RUN_BUSY') from None
        try:
            yield
        finally:
            if os.name == 'nt':
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)


def _exclusive(path, value):
    with _path(path).open('xb') as stream:
        stream.write(_canonical(value))
        stream.flush()
        os.fsync(stream.fileno())


def _terminal(root, status, code, *, side=None, result=None, scenario=None, abstains=None):
    # Closed codes and the research label only: no policy, source, exception or credential text.
    value = {'schema_id': TERMINAL_SCHEMA[0], 'schema_version': TERMINAL_SCHEMA[1], 'status': status,
             'code': code if code in PUBLIC_CODES else 'PILOT_NATIVE_REFUSED', 'side': side,
             'claim': 'RESEARCH_ONLY', 'order_ev': 'UNKNOWN', 'edge_claim': None, 'hermes_led_trading_claim': None,
             'realized_profit': None, 'episode_id': None, 'create_transmits': 0, 'native_result': None,
             'scenario_claim': None, 'full_fill_stress_usd': None,
             'abstain_reasons': {k: v for k, v in sorted((abstains or {}).items()) if k in ABSTAIN_CODES}}
    if scenario is not None:
        value['scenario_claim'] = 'POSITIVE_AFTER_COST_FULL_FILL_STRESS_SCENARIO'
        value['full_fill_stress_usd'] = format(scenario, 'f')
    if result is not None:
        if isinstance(result.episode_id, str) and re.fullmatch(r'liveorchepisode:sha256:[0-9a-f]{64}', result.episode_id):
            value['episode_id'] = result.episode_id
        value['create_transmits'] = result.create_transmits if result.create_transmits in (0, 1) else 1
        value['native_result'] = {
            'status': result.status if result.status in ('BLOCKED', 'CANARY_COMPLETE', 'EXIT_COMPLETE')
            else 'NATIVE_RESULT_INVALID',
            'code': result.code if result.code in NATIVE_CODES else 'NATIVE_RESULT_INVALID',
        }
    directory = _path(root / 'terminals')
    directory.mkdir(exist_ok=True)
    _exclusive(directory / (uuid.uuid4().hex + '.json'), value)
    return value


# --------------------------------------------------------------------------- hunter intake

def _bounded_json(raw):
    try:
        return json.loads(raw.decode('utf-8'), object_pairs_hook=v1._pairs, parse_float=str,
                          parse_constant=v1._constant)
    except Exception:
        raise GatewayError('HUNTER_INTAKE_INVALID') from None


def hunter_candidates(scratch, operation, policy, now):
    """Re-read and re-hash one verified COMPLETED hunter operation; bind each eligible row.

    Returns ``(candidates, abstains)``.  ``small_order_fit`` is never trusted
    (sizing is recomputed); only a VALID real-provider Hermes finding with no
    contrary evidence and present receipts makes a row eligible.
    """
    _require(type(operation) is str and re.fullmatch(r'op-[0-9]{6}', operation), 'HUNTER_INTAKE_INVALID')
    op = _path(scratch / operation)
    index_raw = _read(scratch / f'index-{operation}.json', 1_000_000)
    terminal_raw = _read(op / 'terminal.json', 4_000_000)
    manifest_raw = _read(op / 'manifest.json', 64_000_000)
    index, terminal, manifest = (_bounded_json(x) for x in (index_raw, terminal_raw, manifest_raw))
    manifest_sha = _digest(manifest_raw)
    _require(type(index) is dict and index == {'operation': operation, 'status': 'COMPLETED',
             'terminal_sha256': _digest(terminal_raw)} and type(terminal) is dict
             and terminal.get('status') == 'COMPLETED' and terminal.get('manifest_sha256') == manifest_sha
             and type(terminal.get('inputs_sha256')) is dict
             and terminal['inputs_sha256'].get('manifest.json') == manifest_sha
             and type(manifest) is dict and type(manifest.get('clocks')) is dict
             and type(manifest.get('tokens')) is list and type(manifest.get('markets')) is list
             and type(manifest.get('hermes_findings')) is list, 'HUNTER_INTAKE_INVALID')
    evaluated = manifest['clocks'].get('evaluated_ns')
    _require(type(evaluated) is int and evaluated > 0, 'HUNTER_INTAKE_INVALID')
    abstains, candidates = {}, []

    def abstain(code):
        abstains[code] = abstains.get(code, 0) + 1

    if not 0 <= now - evaluated <= policy['max_hunter_age_s'] * NS:
        abstain('HUNTER_EVIDENCE_STALE')
        return candidates, abstains
    markets = {}
    for market in manifest['markets']:
        if type(market) is dict and market.get('reason') is None and type(market.get('gamma_market_id')) is str:
            _require(market['gamma_market_id'] not in markets, 'HUNTER_INTAKE_INVALID')
            markets[market['gamma_market_id']] = market
    for row in manifest['tokens']:
        try:
            _require(type(row) is dict, 'HUNTER_INTAKE_INVALID')
            market = markets.get(row.get('gamma_market_id'))
            category = row.get('category')
            if (market is None or category not in policy['categories'] or market.get('category') != category
                    or row.get('research_class') != 'RESEARCH_CANDIDATE' or row.get('reason') not in ROW_REASONS_ALLOWED
                    or row.get('condition_id') != market.get('condition_id')
                    or row.get('token_id') not in (market.get('tokens') or ())):
                abstain('HUNTER_ROW_INELIGIBLE')
                continue
            token = row['token_id']
            findings = [f for f in manifest['hermes_findings'] if type(f) is dict and f.get('token_id') == token]
            real = [f for f in findings if f.get('state') == 'VALID' and f.get('origin') == 'REAL_PROVIDER_REPORTED'
                    and f.get('hermes_flag') == 'NO_CONTRARY_EVIDENCE_REPORTED'
                    and type(f.get('receipt')) is dict and f['receipt']]
            if len(findings) != 1 or len(real) != 1:
                abstain('HERMES_EVIDENCE_ABSENT')
                continue
            end = real[0].get('end_utc')
            _require(type(end) is str, 'HUNTER_INTAKE_INVALID')
            end_dt = datetime.fromisoformat(end.replace('Z', '+00:00'))
            _require(end_dt.tzinfo is not None, 'HUNTER_INTAKE_INVALID')
            end_ns = int(end_dt.timestamp()) * NS + end_dt.microsecond * 1000
            if not 0 <= now - end_ns <= policy['max_hermes_assessment_age_s'] * NS:
                abstain('HUNTER_EVIDENCE_STALE')
                continue
            bounds = row.get('payout_bounds')
            _require(type(bounds) is list and len(bounds) == 2, 'HUNTER_INTAKE_INVALID')
            lower = v1._decimal(bounds[0])
            _require(0 <= lower <= 1, 'HUNTER_INTAKE_INVALID')
            if category == 'SPORTS_NBA_MONEYLINE':
                deadline = (market.get('forecast') or {}).get('start_ns')
                _require(type(deadline) is int and deadline > 0, 'HUNTER_INTAKE_INVALID')
                code = 'PILOT_EVENT_STARTED'
            else:
                day = market.get('target_day')
                _require(type(day) is str and re.fullmatch(r'\d{4}-\d\d-\d\d', day), 'HUNTER_INTAKE_INVALID')
                # Conservative climate-day cutoff: 00:00 UTC precedes every US local-standard
                # climate-day start (all US offsets are negative).
                deadline = int(datetime.strptime(day, '%Y-%m-%d').replace(tzinfo=timezone.utc).timestamp()) * NS
                code = 'CLIMATE_DAY_STARTED'
            if now >= deadline:
                abstain(code)
                continue
            candidates.append({'category': category, 'gamma_market_id': row['gamma_market_id'],
                               'condition_id': row['condition_id'], 'token_id': token, 'payout_lower': lower,
                               'deadline_ns': deadline, 'deadline_code': code, 'evaluated_ns': evaluated,
                               'hermes_end_ns': end_ns, 'manifest_sha256': manifest_sha,
                               'row_sha256': _digest(_canonical(row))})
        except Exception:  # malformed row: abstain, never trade
            abstain('HUNTER_ROW_INELIGIBLE')
    return candidates, abstains


def _fresh(candidate, policy, now):
    _require(now < candidate['deadline_ns'], candidate['deadline_code'])
    _require(0 <= now - candidate['evaluated_ns'] <= policy['max_hunter_age_s'] * NS
             and 0 <= now - candidate['hermes_end_ns'] <= policy['max_hermes_assessment_age_s'] * NS,
             'HUNTER_EVIDENCE_STALE')


# --------------------------------------------------------------------------- economics

def fee_bound(snapshot, category, documented_rate=None):
    """(rate, exponent) that never underestimates: max(Gamma rate, documented category rate).

    Builder-profile fee fields are never fee evidence.  Missing or non-taker-only
    Gamma fee configuration abstains ``FEE_CONFIG_UNKNOWN``.
    """
    documented = DOCUMENTED_TAKER_RATE[category] if documented_rate is None else documented_rate
    _require(type(snapshot.fees_enabled) is bool and snapshot.fee_taker_only is True
             and snapshot.fee_rate is not None and snapshot.fee_exponent is not None, 'FEE_CONFIG_UNKNOWN')
    exponent = Decimal(snapshot.fee_exponent)
    _require(exponent == exponent.to_integral_value() and 0 <= exponent <= 8, 'FEE_CONFIG_UNKNOWN')
    gamma = Decimal(snapshot.fee_rate) if snapshot.fees_enabled else Decimal(0)
    _require(gamma.is_finite() and gamma >= 0 and documented >= 0, 'FEE_CONFIG_UNKNOWN')
    return max(gamma, documented), int(exponent)


def fee_max(shares, price, rate, exponent):
    """``q x r x (p(1-p))^e`` rounded UP to 0.00001 (native ``_taker_fee`` form)."""
    with localcontext() as context:
        context.prec = 64
        factor = (price * (1 - price)) ** exponent if exponent else Decimal(1)
        return (shares * rate * factor).quantize(USD_QUANTUM, rounding=ROUND_CEILING)


def size_order(*, ask, depth, rate, exponent, cap, floor, gamma_min, book_min, seconds_delay):
    """Largest 0.01-share q with q*ask + fee_max(q) <= cap at the fresh best ask; else a closed abstain."""
    _require(0 < ask < 1, 'PILOT_VENUE_INVALID')
    hi = int((cap / ask / SHARE_QUANTUM).to_integral_value(rounding=ROUND_FLOOR))
    lo = 0
    while lo < hi:
        mid = (lo + hi + 1) // 2
        q = SHARE_QUANTUM * mid
        if q * ask + fee_max(q, ask, rate, exponent) <= cap:
            lo = mid
        else:
            hi = mid - 1
    q = SHARE_QUANTUM * lo
    fee = fee_max(q, ask, rate, exponent)
    _require(lo > 0 and q * ask + fee >= floor and q * ask >= gamma_min and q >= book_min,
             'MINIMUM_UNSATISFIABLE_WITHIN_FEE_INCLUSIVE_CAP')
    _require(depth >= q, 'DEPTH_BELOW_SIZE')
    _require(seconds_delay == 0, 'SECONDS_DELAY_UNSUPPORTED')
    return q, fee


def _venue(snapshot, candidate):
    _require((snapshot.gamma_market_id, snapshot.condition_id, snapshot.token_id) ==
             (candidate['gamma_market_id'], candidate['condition_id'], candidate['token_id']), 'PILOT_MARKET_MISMATCH')
    _require(snapshot.gamma_neg_risk is False and snapshot.book_neg_risk is False
             and snapshot.gamma_min_order_notional_usd is not None and snapshot.book_min_order_size_raw is not None,
             'PILOT_VENUE_INVALID')
    return Decimal(snapshot.gamma_min_order_notional_usd), Decimal(snapshot.book_min_order_size_raw)


def entry_economics(candidate, snapshot, version, policy, now, documented_rate=None):
    """Dynamic fee-inclusive USD 2-5 sizing at the fresh best ask, then the stress-EV margin."""
    gamma_min, book_min = _venue(snapshot, candidate)
    _require(bool(snapshot.asks), 'PILOT_VENUE_INVALID')
    ask = min(Decimal(level[0]) for level in snapshot.asks)
    depth = sum((Decimal(q) for p, q in snapshot.asks if Decimal(p) == ask), Decimal(0))
    rate, exponent = fee_bound(snapshot, candidate['category'], documented_rate)
    q, fee = size_order(ask=ask, depth=depth, rate=rate, exponent=exponent,
                        cap=_decimal(policy['max_order_commitment_usd']),
                        floor=_decimal(policy['min_order_commitment_usd']),
                        gamma_min=gamma_min, book_min=book_min, seconds_delay=snapshot.seconds_delay)
    # The pinned SDK encodes a FOK BUY's USDC amount on a 0.01 grid and the native
    # inspector requires exact shares, so narrow (never widen) q until q*ask is on it.
    while q > 0 and (q * ask) % SHARE_QUANTUM:
        q -= SHARE_QUANTUM
    fee = fee_max(q, ask, rate, exponent)
    _require(q * ask + fee >= _decimal(policy['min_order_commitment_usd']) and q * ask >= gamma_min
             and q >= book_min, 'MINIMUM_UNSATISFIABLE_WITHIN_FEE_INCLUSIVE_CAP')
    stress = q * candidate['payout_lower'] - q * ask - fee - RESIDUAL_COST_PER_SHARE * q
    _require(stress > _decimal(policy['experimental_margin_usd']), 'PILOT_MARGIN_NOT_MET')
    intent = build_execution_intent(strategy_version=version, gamma_market_id=candidate['gamma_market_id'],
        condition_id=candidate['condition_id'], token_id=candidate['token_id'], side='BUY',
        execution_style='AGGRESSIVE_TAKER', order_type='FOK', requested_shares=_canonical_decimal(q),
        price_limit=_canonical_decimal(ask), post_only=False, gtd_expiration_unix_s=None,
        information_cutoff_ns=snapshot.acquisition_completed_ns, max_public_data_age_ns=30 * NS)
    assessment = assess_execution_feasibility(intent, snapshot, evaluated_at_ns=max(now, snapshot.acquisition_completed_ns))
    _require(assessment.status in ('FEASIBLE', 'LIMITED') and assessment.minimum_order_dimension == 'PASS'
             and assessment.tick_dimension == 'PASS', 'PILOT_VENUE_INVALID')
    return {'stress': stress, 'intent': intent, 'assessment': assessment, 'shares': q, 'price': ask,
            'hunter_fee': fee}


def exit_economics(candidate, snapshot, version, shares, now, documented_rate=None):
    """SELL iff bid*s - fee_max(s) >= s*payout_lower_current at the fresh best bid; else hold."""
    gamma_min, book_min = _venue(snapshot, candidate)
    _require(bool(snapshot.bids), 'PILOT_VENUE_INVALID')
    bid = max(Decimal(level[0]) for level in snapshot.bids)
    depth = sum((Decimal(q) for p, q in snapshot.bids if Decimal(p) == bid), Decimal(0))
    _require(0 < bid < 1, 'PILOT_VENUE_INVALID')
    rate, exponent = fee_bound(snapshot, candidate['category'], documented_rate)
    fee = fee_max(shares, bid, rate, exponent)
    _require(shares >= book_min and bid * shares >= gamma_min, 'MINIMUM_UNSATISFIABLE_WITHIN_FEE_INCLUSIVE_CAP')
    _require(depth >= shares, 'DEPTH_BELOW_SIZE')
    _require(snapshot.seconds_delay == 0, 'SECONDS_DELAY_UNSUPPORTED')
    _require(bid * shares - fee >= shares * candidate['payout_lower'], 'PILOT_MARGIN_NOT_MET')
    intent = build_execution_intent(strategy_version=version, gamma_market_id=candidate['gamma_market_id'],
        condition_id=candidate['condition_id'], token_id=candidate['token_id'], side='SELL',
        execution_style='AGGRESSIVE_TAKER', order_type='FOK', requested_shares=_canonical_decimal(shares),
        price_limit=_canonical_decimal(bid), post_only=False, gtd_expiration_unix_s=None,
        information_cutoff_ns=snapshot.acquisition_completed_ns, max_public_data_age_ns=30 * NS)
    assessment = assess_execution_feasibility(intent, snapshot, evaluated_at_ns=max(now, snapshot.acquisition_completed_ns))
    _require(assessment.status in ('FEASIBLE', 'LIMITED') and assessment.minimum_order_dimension == 'PASS'
             and assessment.tick_dimension == 'PASS', 'PILOT_VENUE_INVALID')
    return {'intent': intent, 'assessment': assessment}


# --------------------------------------------------------------------------- ledger views

def _pilot_buys(checkpoint, *, profile=PROFILE):
    return [e for e in checkpoint['episodes']
            if e['binding'].get('capital_profile') == profile and e['binding']['side'] == 'BUY']


def _confirmed(episode, field_name):
    return sum((Decimal(t[field_name]) for t in episode['reconciliation']['trades'] if t['status'] == 'CONFIRMED'),
               Decimal(0))


def _fee(episode):
    recon = episode['reconciliation']
    if recon['fee_state'] == 'NOT_REQUIRED':
        return Decimal(0)
    if recon['fee_state'] == 'RECONCILED':
        return Decimal(recon['actual_fee_usd'])
    return Decimal(episode['admission']['worst_case_fee_reserve_usd'])


def lifecycles(checkpoint, resolved_payout, *, profile=PROFILE):
    """Completed pilot lifecycles (CLOSED_RECONCILED BUY episodes) in close order with their net.

    net = confirmed SELL proceeds - SELL fees - BUY principal - BUY fee, plus the
    public resolved payout on shares held to resolution (unknown payout = 0).
    """
    sells = {}
    for episode in checkpoint['episodes']:
        closes = episode['binding'].get('closes_episode_id')
        if closes is not None:
            sells.setdefault(closes, []).append(episode)
    result = []
    for buy in _pilot_buys(checkpoint, profile=profile):
        if buy['state'] != 'CLOSED_RECONCILED':
            continue
        exits = sells.get(buy['episode_id'], [])
        sold = sum((_confirmed(e, 'shares') for e in exits), Decimal(0))
        proceeds = sum((_confirmed(e, 'principal_usd') for e in exits), Decimal(0))
        sell_fees = sum((_fee(e) for e in exits), Decimal(0))
        held = max(_confirmed(buy, 'shares') - sold, Decimal(0))
        payout = None
        if held > 0:
            per_share = resolved_payout(buy['binding']['token_id'])
            payout = held * (per_share if isinstance(per_share, Decimal) and 0 <= per_share <= 1 else Decimal(0))
        net = proceeds - sell_fees - _confirmed(buy, 'principal_usd') - _fee(buy) + (payout or Decimal(0))
        result.append({'episode_id': buy['episode_id'], 'closed_ns': buy['reconciliation']['last_reconciled_time_ns'] or 0,
                       'strategy_version_id': buy['binding']['strategy_version_id'],
                       'entry_price': buy['binding']['price_limit'], 'entry_shares': format(_confirmed(buy, 'shares'), 'f'),
                       'exit_proceeds_usd': format(proceeds, 'f'),
                       'resolution_payout_usd': None if payout is None else format(payout, 'f'),
                       'fees_usd': format(_fee(buy) + sell_fees, 'f'), 'net_usd': format(net, 'f')})
    return sorted(result, key=lambda item: (item['closed_ns'], item['episode_id']))


def _diagnosis(n, window, policy, entries):
    categories = {v: k for k, v in policy['strategy_version_ids'].items()}
    return {'schema_id': 'polymarket-hunter-pilot-loss-diagnosis', 'schema_version': '2.0.0', 'trigger': n,
            'lifecycles': [dict(item, category=categories.get(item['strategy_version_id'], 'UNKNOWN'),
                                forecast_payout_lower=entries.get(item['episode_id'], 'UNKNOWN'))
                           for item in window]}


def breaker(root, policy, checkpoint, resolved_payout, now):
    """consecutive_loss_limit completed net-losing lifecycles -> diagnosis record + loss_pause_s pause.

    Resume only after the pause ends AND the diagnosis record exists and validates.
    """
    entries = {}
    for path in sorted(_path(root / 'hunter-entries').glob('*.json')) if (root / 'hunter-entries').exists() else ():
        try:
            item = v1._json(_read(path))
            entries[item['episode_id']] = item['payout_lower']
        except Exception:
            continue
    streak, last = [], None
    for n, item in enumerate(lifecycles(checkpoint, resolved_payout, profile=profile_of(policy)), 1):
        # A winning (or break-even) lifecycle resets the count; each trigger starts a new streak.
        streak = streak + [item] if Decimal(item['net_usd']) < 0 else []
        if len(streak) == policy['consecutive_loss_limit']:
            last, streak = (n, item, streak), []
    if last is None:
        return
    n, item, window = last
    record = _diagnosis(n, window, policy, entries)
    path = root / f'loss-diagnosis-{n}.json'
    if now < item['closed_ns'] + policy['loss_pause_s'] * NS:
        if not path.exists():
            _exclusive(path, record)
        raise GatewayError('LOSS_BREAKER_PAUSED')
    try:
        _require(_read(path) == _canonical(record), 'LOSS_DIAGNOSIS_INVALID')
    except GatewayError:
        raise GatewayError('LOSS_DIAGNOSIS_INVALID') from None


def _latch_equity(root, policy, policy_hash, reconciliation, checkpoint):
    """E0 latched once per policy digest, exclusive-create, never rewritten."""
    edge = policy.get('schema_version') == '3.0.0'
    identity = policy['activation_id'] if edge else policy_hash
    path = root / f'hunter-pilot-equity-{identity}.json'
    expected = ({'activation_id': identity, 'activation_ledger_head': policy['activation_ledger_head']}
                if edge else {'policy_sha256': policy_hash})
    expected['initial_equity_usd'] = format(policy['_initial_equity'], 'f')
    if path.exists():
        _require(v1._json(_read(path)) == expected, 'INITIAL_EQUITY_UNVERIFIED')
        return
    details = reconciliation.details
    _require((not checkpoint['episodes'] if edge else not _pilot_buys(checkpoint)) and reconciliation.status == 'NO_NEW_EXPOSURE_READY'
             and Decimal(str(details.get('collateral_usd'))) >= policy['_initial_equity'], 'INITIAL_EQUITY_UNVERIFIED')
    _exclusive(path, expected)


# --------------------------------------------------------------------------- guard

def _guard(policy, policy_hash, reload_policy, deps, candidate, permit, intent, killed, *, side, hunter_fee=None,
           authority=native.verify_permit_authority):
    """In-lock latest-point recheck (PR #256 hook): authority, freshness, kill, policy, budget."""
    def check(checkpoint, evaluation, risk):
        current, digest = reload_policy(_time(deps.clock_ns()))
        _require(current == policy and digest == policy_hash, 'PILOT_GUARD_REFUSED:POLICY_CHANGED')
        _require(not killed(), 'PILOT_GUARD_REFUSED:KILL')
        _require((intent.gamma_market_id, intent.condition_id, intent.token_id, intent.side) ==
                 (candidate['gamma_market_id'], candidate['condition_id'], candidate['token_id'], side),
                 'PILOT_GUARD_REFUSED:MARKET_BINDING')
        authority(permit, intent, lifecycle_store_path=Path(policy['lifecycle_store_path']),
                  hermes_store_path=Path(policy['hermes_store_path']), now_ns=_time(deps.clock_ns()))
        current, digest = reload_policy(_time(deps.clock_ns()))
        _require(current == policy and digest == policy_hash, 'PILOT_GUARD_REFUSED:POLICY_CHANGED')
        _require(not killed(), 'PILOT_GUARD_REFUSED:KILL')
        now = _time(deps.clock_ns())
        try:
            _fresh(candidate, policy, now)
        except GatewayError:
            raise GatewayError('PILOT_GUARD_REFUSED:FRESHNESS') from None
        _require(_utc(policy['valid_from_utc']) <= now < _utc(policy['valid_until_utc'])
                 and policy['_owner_window'][0] <= now < policy['_owner_window'][1], 'PILOT_GUARD_REFUSED:OWNER_WINDOW')
        if side == 'SELL':
            return  # reduce-only: exposure, reserve and budget checks do not apply
        proposed = max(risk.proposed_worst_case_commitment, Decimal(intent.requested_shares) *
                       Decimal(intent.price_limit) + hunter_fee)
        _require(_decimal(policy['min_order_commitment_usd']) <= proposed <= _decimal(policy['max_order_commitment_usd']),
                 'PILOT_GUARD_REFUSED:ORDER_BOUNDS')
        _require(evaluation.total_commitment + proposed <= _decimal(policy['max_simultaneous_exposure_usd']),
                 'PILOT_GUARD_REFUSED:EXPOSURE')
        if policy.get('schema_version') == '3.0.0':
            from src.live_pilot.edge_qualifier import combined_loss
            verify_activation_baseline(policy)
            verify_first_canary(policy, checkpoint)
            combined_loss(checkpoint, evaluation, proposed, activation_ledger_head=policy['activation_ledger_head'])
        # Worst case: every open position and pending/ambiguous reserve valued at zero.
        projected_free = evaluation.collateral - evaluation.undebited_commitment - proposed
        _require(projected_free >= max(_decimal(policy['min_free_collateral_after_admission_usd']),
                                       policy['_initial_equity'] - _decimal(policy['net_loss_budget_usd'])),
                 'PILOT_GUARD_REFUSED:NET_LOSS_BUDGET')
    return check


def _permit(config, policy, version_id, intent, snapshot, assessment, now):
    decision = evaluate_exploratory_gate_c(lifecycle_store_path=config.lifecycle_store_path,
        hermes_manager_store_path=config.hermes_store_path, strategy_version_id=version_id,
        execution_intent=intent, venue_snapshot=snapshot, execution_feasibility_assessment=assessment,
        evaluated_at_ns=now)
    hermes = load_hermes_strategy_manager_store(config.hermes_store_path)
    _require(decision.status == 'PERMIT_ELIGIBLE'
             and decision.hermes_assessment_id == hermes.latest_assessment_id(version_id), 'PILOT_PERMIT_REFUSED')
    return build_exploratory_gate_c_permit(decision, execution_intent=intent)


# --------------------------------------------------------------------------- cycle

def run_hunter_cycle_once(*, policy_path, owner_record_path, owner_record_sha256, state_root, hunter_scratch_dir,
                          hunter_operation, dependencies=None) -> Mapping[str, object]:
    """Foreground composition only; at most one economic mutation; one durable terminal."""
    root = None
    try:
        root, scratch = _path(state_root), _path(hunter_scratch_dir)
        root.mkdir(parents=True, exist_ok=True)
        with _run_lock(root):
            deps = HunterCycleDependencies() if dependencies is None else dependencies
            clock = deps.native.clock_ns
            reload_policy = lambda now: _load(policy_path, owner_record_path, owner_record_sha256, root, now)  # noqa: E731
            policy, policy_hash = reload_policy(_time(clock()))
            signer_type, provider_name = CUSTODY_PROVIDERS[policy['custody']]
            provider = {'InteractiveGateBSecretProvider': InteractiveGateBSecretProvider,
                        'CredentialDirectorySessionKeyProvider': CredentialDirectorySessionKeyProvider}[provider_name]
            # Allowlist the exact native provider class selected by policy custody, never duck-typed.
            _require(deps.native.secret_provider_factory is provider, 'PILOT_CUSTODY_UNAVAILABLE')
            native_deps = replace(deps.native, signer_type=signer_type)
            latched = False

            def killed():
                nonlocal latched
                _require(root.is_dir(), 'PILOT_STATE_UNAVAILABLE')
                try:
                    (root / 'PILOT_KILL').lstat()
                    latched = True
                except FileNotFoundError:
                    pass
                return latched
            killed()
            suspension = root / f'custody-suspended-{owner_record_sha256}.json'
            host = native.HostCurrentnessConfig(**{k: Path(v) if k != 'ssh_port' else v
                for k, v in policy['host'].items()}, expected_release_sha=policy['release_sha'])
            config = native.LiveOrchConfig(state_root=root, expected_signer=policy['public_signer'],
                expected_wallet=policy['public_wallet'], lifecycle_store_path=Path(policy['lifecycle_store_path']),
                hermes_store_path=Path(policy['hermes_store_path']), host=host)
            envelope = (native.LiveOrchCapitalEnvelope.autonomous_edge_01() if policy['schema_version'] == '3.0.0'
                        else native.LiveOrchCapitalEnvelope.hunter_pilot_02())

            def orchestrator(guard=None):
                return native.LiveOrchestrator(config, envelope=envelope,
                                               dependencies=replace(native_deps, admission_guard=guard))

            def suspend_on(result):
                if signer_type == 'SESSION_KEY' and result.code in CUSTODY_REJECTION_CODES and not suspension.exists():
                    _exclusive(suspension, {'owner_record_sha256': owner_record_sha256, 'reason': 'VENUE_AUTH_REJECTED'})

            reconciliation = orchestrator().reconcile()
            suspend_on(reconciliation)
            if suspension.exists():
                return _terminal(root, 'REFUSED', 'CUSTODY_SUSPENDED')
            if killed():
                return _terminal(root, 'REFUSED', 'PILOT_KILLED')
            if reconciliation.status != 'NO_NEW_EXPOSURE_READY':
                return _terminal(root, 'REFUSED', 'PILOT_RECONCILIATION_BLOCKED')
            checkpoint = orchestrator().ledger()
            _latch_equity(root, policy, policy_hash, reconciliation, checkpoint)
            lifecycle = load_strategy_lifecycle_store(config.lifecycle_store_path)
            _require(lifecycle.is_valid is True and lifecycle.snapshot is not None, 'PILOT_STRATEGY_UNAVAILABLE')
            try:
                candidates, abstains = hunter_candidates(scratch, hunter_operation, policy, _time(clock()))
            except GatewayError:
                # Unverified/tampered/blocked hunter output: durable no trade (exits hold too).
                return _terminal(root, 'NO_TRADE', 'HUNTER_INTAKE_INVALID')
            by_token = {c['token_id']: c for c in candidates}

            # ---- exit phase (allowed during automatic stops; never during manual kill)
            sold = {}
            for episode in checkpoint['episodes']:
                if episode['binding'].get('closes_episode_id') is not None:
                    sold[episode['binding']['closes_episode_id']] = sold.get(
                        episode['binding']['closes_episode_id'], Decimal(0)) + _confirmed(episode, 'shares')
            for buy in sorted(_pilot_buys(checkpoint, profile=profile_of(policy)), key=lambda e: e['admission']['admitted_time_ns']):
                candidate = by_token.get(buy['binding']['token_id'])
                if buy['state'] != 'TERMINAL_KNOWN_POSITION' or candidate is None:
                    continue  # no fresh verified row: hold to resolution
                shares = ((_confirmed(buy, 'shares') - sold.get(buy['episode_id'], Decimal(0))) / SHARE_QUANTUM
                          ).to_integral_value(rounding=ROUND_FLOOR) * SHARE_QUANTUM
                version_id = buy['binding']['strategy_version_id']
                version = lifecycle.snapshot.version_by_id(version_id)
                try:
                    _require(shares > 0 and version is not None, 'PILOT_EXIT_HOLD')
                    snapshot = native_deps.venue_fetcher(**{k: candidate[k] for k in
                                                            ('gamma_market_id', 'condition_id', 'token_id')})
                    economics = exit_economics(candidate, snapshot, version, shares, _time(clock()))
                    permit = _permit(config, policy, version_id, economics['intent'], snapshot,
                                     economics['assessment'], _time(clock()))
                except Exception:
                    continue  # hold; native authority or economics refusal is never overridden
                guard = _guard(policy, policy_hash, reload_policy, native_deps, candidate, permit, economics['intent'],
                               killed, side='SELL', authority=native.verify_sell_permit_authority)
                _require(not killed(), 'PILOT_KILLED')
                result = orchestrator(guard).exit_sell(permit, economics['intent'], closes_episode_id=buy['episode_id'])
                suspend_on(result)
                if result.create_transmits:
                    return _terminal(root, 'EXIT_RESULT', 'PILOT_NATIVE_RESULT', side='SELL', result=result)
                # Refused before transmit: hold this position; no further exit this invocation.
                break

            # ---- automatic stops (new exposure only)
            try:
                breaker(root, policy, checkpoint, deps.resolved_payout, _time(clock()))
            except GatewayError as error:
                return _terminal(root, 'NO_NEW_EXPOSURE', error.code, abstains=abstains)

            # ---- entry phase: at most one BUY
            hermes = load_hermes_strategy_manager_store(config.hermes_store_path)
            eligible = []
            for candidate in candidates:
                try:
                    version_id = policy['strategy_version_ids'][candidate['category']]
                    version = lifecycle.snapshot.version_by_id(version_id)
                    _require(version is not None, 'PILOT_STRATEGY_UNAVAILABLE')
                    assessment_id = hermes.latest_assessment_id(version_id)
                    assessments = [a for a in hermes.assessments if a.assessment_id == assessment_id]
                    _require(len(assessments) == 1 and 0 <= _time(clock()) - assessments[0].decision_time_ns
                             <= policy['max_hermes_assessment_age_s'] * NS, 'PILOT_ASSESSMENT_STALE')
                    _fresh(candidate, policy, _time(clock()))
                    snapshot = native_deps.venue_fetcher(**{k: candidate[k] for k in
                                                            ('gamma_market_id', 'condition_id', 'token_id')})
                    economics = entry_economics(candidate, snapshot, version, policy, _time(clock()))
                    eligible.append((economics['stress'], candidate, snapshot, economics, version_id))
                except GatewayError as error:
                    code = error.code if error.code in ABSTAIN_CODES else 'PILOT_VENUE_INVALID'
                    abstains[code] = abstains.get(code, 0) + 1
                except Exception:
                    abstains['PILOT_VENUE_INVALID'] = abstains.get('PILOT_VENUE_INVALID', 0) + 1
            if not eligible:
                return _terminal(root, 'NO_TRADE', 'PILOT_NO_ELIGIBLE_PAIR', abstains=abstains)
            stress, candidate, snapshot, economics, version_id = min(
                eligible, key=lambda x: (-x[0], x[1]['deadline_ns'], x[1]['token_id']))
            intent = economics['intent']
            permit = _permit(config, policy, version_id, intent, snapshot, economics['assessment'], _time(clock()))
            guard = _guard(policy, policy_hash, reload_policy, native_deps, candidate, permit, intent, killed,
                           side='BUY', hunter_fee=economics['hunter_fee'])
            guarded = orchestrator(guard)
            _require(guarded.preflight(permit, intent).status == 'PREFLIGHT_PASS', 'PILOT_PREFLIGHT_REFUSED')
            _require(not killed(), 'PILOT_KILLED')
            result = orchestrator(guard).canary(permit, intent)
            suspend_on(result)
            if result.create_transmits and isinstance(result.episode_id, str):
                entries = _path(root / 'hunter-entries')
                entries.mkdir(exist_ok=True)
                try:
                    _exclusive(entries / (result.episode_id.split(':')[-1] + '.json'),
                               {'episode_id': result.episode_id, 'category': candidate['category'],
                                'payout_lower': format(candidate['payout_lower'], 'f'),
                                'manifest_sha256': candidate['manifest_sha256'], 'row_sha256': candidate['row_sha256']})
                except Exception:
                    pass  # diagnosis then reports the forecast as UNKNOWN; never a second mutation
            return _terminal(root, 'REFUSED' if result.status == 'BLOCKED' else 'ENTRY_RESULT',
                             'PILOT_NATIVE_REFUSED' if result.status == 'BLOCKED' else 'PILOT_NATIVE_RESULT',
                             side='BUY', result=result, scenario=stress, abstains=abstains)
    except Exception as error:
        code = error.code if isinstance(error, GatewayError) else 'PILOT_INPUT_INVALID'
        # Only module-owned closed codes survive; native details remain in its ledger.
        if not isinstance(code, str) or code not in PUBLIC_CODES:
            code = 'PILOT_NATIVE_REFUSED'
        if root is not None:
            try:
                return _terminal(root, 'REFUSED', code)
            except Exception:
                pass
        return {'status': 'REFUSED', 'code': 'PILOT_STATE_UNAVAILABLE', 'terminal_persisted': False}


def verify_first_canary(policy, checkpoint):
    """Exact owner-bound original composer/Stage-A records and canonical episode."""
    from src.execution_gateway import live_canary as attended
    code = 'PILOT_GUARD_REFUSED:CANARY'
    _require(policy.get('first_canary_receipt_sha256') is not None, code)
    raw = _read(_path(Path(policy['state_root'])/'first-canary.json'))
    _require(_digest(raw) == policy['first_canary_receipt_sha256'], code)
    record = v1._json(raw)
    keys = set(attended._receipt('run', False)) | {'receipt_id'}
    _require(type(record) is dict and set(record) in (keys, keys|{'reconcile_required'}), code)
    original = {k:v for k,v in record.items() if k != 'receipt_id'}
    _require(attended._finish(original) == record and record['command'] == 'run'
             and record['schema_version'] == '1.0.0' and record['schema_id'] == 'polymarket-live-canary-receipt'
             and record['evidence_class'] == 'NATIVE_PRODUCTION' and record['status'] == 'CANARY_COMPLETE'
             and record['stage_a_binding'] == attended.STAGE_A_BINDING and record['bridge_status'] == 'PASS', code)
    _require(type(record['calls']) is dict and set(record['calls']) == {'oauth_dispatch','confirmation_prompt','canary','order'}
             and all(type(n) is int and n == 1 for n in record['calls'].values()), code)
    _require(type(record['bridge_receipt_id']) is str and re.fullmatch('[a-z]+:sha256:[0-9a-f]{64}', record['bridge_receipt_id']), code)
    outcome = record['live_orch']
    _require(type(outcome) is dict and outcome.get('command') == 'canary'
             and outcome.get('status') == 'CANARY_COMPLETE' and type(outcome.get('create_transmits')) is int
             and outcome['create_transmits'] == 1, code)
    episodes = [e for e in checkpoint['episodes'] if e['episode_id'] == outcome.get('episode_id')]
    _require(len(episodes) == 1, code)
    episode = episodes[0]; binding = episode['binding']
    _require(binding.get('capital_profile') is None and binding['side'] == 'BUY'
             and record['permit_id'] == binding['exploratory_permit_id']
             and record['execution_intent_id'] == binding['execution_intent_id']
             and episode['state'] in ('CLOSED_RECONCILED', 'TERMINAL_KNOWN_POSITION', 'TERMINAL_NO_POSITION')
             and episode['reconciliation']['fee_state'] in ('NOT_REQUIRED', 'RECONCILED'), code)
    stage_raw = _read(_path(Path(policy['state_root'])/'first-canary-stage-a.json'))
    _require(_digest(stage_raw) == record['stage_a_authorization_sha256'], code)
    stage = v1._json(stage_raw)
    _require(type(stage) is dict and set(stage) == attended._STAGE_A_KEYS
             and (stage['schema_id'],stage['schema_version']) == attended.STAGE_A_SCHEMA
             and stage['deposit_wallet_address'].lower() == policy['public_wallet'].lower()
             and stage['release_sha'] == binding['release_sha'] and stage['side'] == 'BUY'
             and type(stage['max_create_attempts']) is int and stage['max_create_attempts'] == 1
             and _utc(stage['valid_from_utc']) <= episode['admission']['admitted_time_ns'] < _utc(stage['valid_until_utc']), code)
    _require(any(all(menu[k] == binding[k] for k in ('strategy_version_id','gamma_market_id','condition_id','token_id'))
                 for menu in stage['approved_menu']), code)


def verify_activation_baseline(policy):
    """A renewal cannot replace or omit the original canonical native ledger history."""
    from src.execution_gateway.gateway import _validate_replay
    from src.execution_gateway.store import GatewayStore
    path = native.canonical_live_orch_store_path(Path(policy['state_root']), policy['public_wallet'])
    store = GatewayStore(path)
    try:
        mapping, head, events = store.load()
        _require(mapping is not None and _validate_replay(events).to_mapping() == dict(mapping)
                 and policy['activation_ledger_head'] in {e.event_hash for e in events}, 'PILOT_GUARD_REFUSED:BASELINE')
        return head
    finally:
        store.close()


def profile_of(policy):
    return native.AUTONOMOUS_EDGE_01_PROFILE if policy.get('schema_version') == '3.0.0' else PROFILE
