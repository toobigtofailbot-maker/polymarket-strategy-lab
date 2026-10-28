"""S10-ALPHA-HUNTER-PILOT-02 offline contracts: real native stores/kernel, synthetic hunter bytes.

No test performs real network, credential, account, provider, order, capital or live
behavior.  The fake authenticated venue is the LIVE-ORCH offline harness.
"""
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from src.execution_gateway.gateway import GatewayError
from src.live_pilot import hunter_cycle as H
from tests.execution_gateway import test_live_orch as L
from tests.exploratory_gate_c import test_exploratory_gate_c as X
from tools.alpha import run_hunter_pilot as CLI

NS = H.NS
OP = 'op-000001'
START = X.AT + 3600 * NS


def utc(ns):
    return datetime.fromtimestamp(ns // NS, timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode() + b'\n'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def market(**changes):
    value = {'category': 'SPORTS_NBA_MONEYLINE', 'gamma_market_id': X.GAMMA_ID, 'condition_id': X.COND,
             'reason': None, 'tokens': [X.TOKEN, X.OTHER_TOKEN], 'forecast': {'start_ns': START}}
    value.update(changes)
    return value


def row(**changes):
    value = {'category': 'SPORTS_NBA_MONEYLINE', 'gamma_market_id': X.GAMMA_ID, 'condition_id': X.COND,
             'token_id': X.TOKEN, 'outcome_index': 0, 'research_class': 'RESEARCH_CANDIDATE',
             'reason': 'SMALL_ORDER_UNFIT', 'small_order_fit': False, 'payout_bounds': ['0.8', '0.95']}
    value.update(changes)
    return value


def finding(**changes):
    value = {'token_id': X.TOKEN, 'state': 'VALID', 'origin': 'REAL_PROVIDER_REPORTED',
             'hermes_flag': 'NO_CONTRARY_EVIDENCE_REPORTED', 'receipt': {'receipt_id': 'synthetic-receipt'},
             'end_utc': datetime.fromtimestamp(X.AT / 1e9, timezone.utc).isoformat()}
    value.update(changes)
    return value


def build(tmp_path, monkeypatch, *, custody='ATTENDED_TTY'):
    world = X.make_world(tmp_path, hermes=False)
    world.assess(t=X.AT)
    harness = L.Harness(tmp_path, world)
    harness.gamma = X.gamma_doc(orderMinSize=1)  # Gamma rate 0.0333, documented 0.05 governs
    root, scratch = tmp_path / 'state', tmp_path / 'hunter'
    scratch.mkdir()
    policy = dict(
        schema_id='polymarket-hunter-pilot-policy', schema_version='2.0.0', public_wallet=L.WALLET,
        public_signer=L.SIGNER, release_sha=L.RELEASE,
        host={k: str(v) if isinstance(v, Path) else v for k, v in vars(harness.config().host).items()
              if k != 'expected_release_sha'},
        state_root=str(root), lifecycle_store_path=str(world.lifecycle), hermes_store_path=str(world.hermes),
        categories=['SPORTS_NBA_MONEYLINE'],
        strategy_version_ids={'SPORTS_NBA_MONEYLINE': world.version.strategy_version_id}, order_type='FOK',
        valid_from_utc=utc(X.AT - H.DAY), valid_until_utc=utc(X.AT + H.DAY), experimental_margin_usd='0',
        max_order_commitment_usd='5', min_order_commitment_usd='2', max_simultaneous_exposure_usd='30',
        min_free_collateral_after_admission_usd='50', net_loss_budget_usd='30', consecutive_loss_limit=5,
        loss_pause_s=7200, max_hunter_age_s=1800, max_hermes_assessment_age_s=86400, custody=custody)
    s = SimpleNamespace(world=world, harness=harness, root=root, scratch=scratch, policy=policy,
                        policy_path=tmp_path / 'policy.json', owner_path=tmp_path / 'owner.json', owner_extra={})

    def write():
        s.policy_path.write_bytes(H._canonical(s.policy))
        s.owner = dict(schema_id='polymarket-hunter-pilot-owner-activation', schema_version='2.0.0',
                       policy_sha256=H._digest(s.policy_path.read_bytes()), initial_equity_usd='100',
                       dedicated_wallet=True, **{k: s.policy[k] for k in ('public_wallet', 'public_signer',
                       'release_sha', 'state_root', 'valid_from_utc', 'valid_until_utc')}, **s.owner_extra)
        s.write_owner()

    def write_owner(raw=None):
        raw = H._canonical(s.owner) if raw is None else raw
        s.owner_path.write_bytes(raw)
        s.owner_hash = H._digest(raw)

    def hunter(*, status='COMPLETED', rows=None, findings=None, markets=None, evaluated=X.AT, index_status=None):
        op = s.scratch / OP
        op.mkdir(exist_ok=True)
        manifest = {'clocks': {'started_ns': X.AT - NS, 'evaluated_ns': evaluated},
                    'markets': [market()] if markets is None else markets,
                    'tokens': [row()] if rows is None else rows,
                    'hermes_findings': [finding()] if findings is None else findings}
        raw = canonical(manifest)
        (op / 'manifest.json').write_bytes(raw)
        terminal = canonical({'status': status, 'manifest_sha256': sha(raw), 'inputs_sha256': {'manifest.json': sha(raw)},
                              'categories': ['nba']})
        (op / 'terminal.json').write_bytes(terminal)
        (s.scratch / f'index-{OP}.json').write_bytes(canonical(
            {'operation': OP, 'status': index_status or status, 'terminal_sha256': sha(terminal)}))

    s.write, s.write_owner, s.hunter = write, write_owner, hunter
    write()
    hunter()
    s.deps = H.HunterCycleDependencies(native=harness.deps())
    monkeypatch.setattr(H, 'InteractiveGateBSecretProvider', s.deps.native.secret_provider_factory)

    def run():
        return H.run_hunter_cycle_once(policy_path=s.policy_path, owner_record_path=s.owner_path,
                                       owner_record_sha256=s.owner_hash, state_root=s.root,
                                       hunter_scratch_dir=s.scratch, hunter_operation=OP, dependencies=s.deps)
    s.run = run
    return s


@pytest.fixture
def setup(tmp_path, monkeypatch):
    return build(tmp_path, monkeypatch)


def native_untouched(s):
    return s.harness.secret_requests == 0 and s.harness.venue.posts == [] and not (s.root / 'live_orch').exists()


def enter_position(s):
    s.harness.venue.on_post = L._accept_fill(shares='9.25', price='0.52')
    result = s.run()
    assert result['status'] == 'ENTRY_RESULT' and result['create_transmits'] == 1, result
    assert result['native_result']['status'] == 'CANARY_COMPLETE'
    return result['episode_id']


def exit_holds_without_fresh_row(tmp_path):
    """R008 support: a reconciled pilot position with no fresh hunter row is held (no SELL)."""
    with pytest.MonkeyPatch.context() as monkeypatch:
        s = build(tmp_path, monkeypatch)
        enter_position(s)
        s.hunter(rows=[], findings=[])
        result = s.run()
        return result['status'] == 'NO_TRADE' and len(s.harness.venue.posts) == 1


# --------------------------------------------------------------------------- R003

POLICY_CASES = [
    ('max_order_commitment_usd', '5.00001'), ('max_order_commitment_usd', '1.99999'),
    ('min_order_commitment_usd', '1.99999'), ('min_order_commitment_usd', '5.00001'),
    ('max_simultaneous_exposure_usd', '30.00001'), ('max_simultaneous_exposure_usd', '0'),
    ('min_free_collateral_after_admission_usd', '49.99999'), ('net_loss_budget_usd', '30.00001'),
    ('consecutive_loss_limit', 6), ('consecutive_loss_limit', 0), ('consecutive_loss_limit', True),
    ('loss_pause_s', 7199), ('max_hunter_age_s', 1801), ('max_hermes_assessment_age_s', 86401),
    ('experimental_margin_usd', '-0.01'), ('max_order_commitment_usd', 'NaN'),
    ('max_order_commitment_usd', '5e0'), ('max_order_commitment_usd', None), ('max_order_commitment_usd', 5),
    ('categories', ['CRYPTO']), ('categories', []), ('categories', ['SPORTS_NBA_MONEYLINE'] * 2),
    ('categories', ['sports_nba_moneyline']), ('strategy_version_ids', {}), ('order_type', 'FAK'),
    ('custody', 'ENVIRONMENT'), ('custody', 'attended_tty'), ('schema_version', '1.0.0'),
    ('Max_order_commitment_usd', '5'), ('valid_until_utc', utc(X.AT + 8 * H.DAY)),
]


@pytest.mark.parametrize('field,value', POLICY_CASES)
def test_policy_and_owner_record_v2_strict_canonical_and_ceilings(setup, field, value):
    s = setup
    H._load(s.policy_path, s.owner_path, s.owner_hash, s.root, X.AT)  # positive control
    s.policy[field] = value  # a case/spelling variant key is an unknown field
    s.write()
    result = s.run()
    assert result['status'] == 'REFUSED' and result['code'] == 'PILOT_POLICY_INVALID'
    assert native_untouched(s)


@pytest.mark.parametrize('change,code', [
    ('digest', 'PILOT_OWNER_RECORD_DIGEST_MISMATCH'), ('unknown', 'PILOT_OWNER_RECORD_INVALID'),
    ('prefix', 'PILOT_OWNER_RECORD_SCOPE_MISMATCH'), ('wallet', 'PILOT_OWNER_RECORD_SCOPE_MISMATCH'),
    ('signer', 'PILOT_OWNER_RECORD_SCOPE_MISMATCH'), ('expired', 'PILOT_OWNER_RECORD_WINDOW_INVALID'),
    ('newline', 'PILOT_OWNER_RECORD_INVALID'), ('dedicated', 'PILOT_OWNER_RECORD_INVALID'),
    ('equity0', 'PILOT_OWNER_RECORD_INVALID'), ('equity101', 'PILOT_OWNER_RECORD_INVALID'),
    ('session_keys_forbidden', 'PILOT_OWNER_RECORD_INVALID'), ('missing', 'PILOT_INPUT_INVALID'),
    ('noncanonical_policy', 'PILOT_POLICY_INVALID'), ('utf8', 'PILOT_INPUT_INVALID'),
])
def test_owner_record_v2_refusals_zero_native_calls(setup, change, code):
    s = setup
    if change == 'digest':
        s.owner_hash = '0' * 64
    elif change == 'missing':
        s.owner_path.unlink()
    elif change == 'noncanonical_policy':
        s.policy_path.write_bytes(json.dumps(s.policy, indent=1).encode())
    elif change == 'utf8':
        s.policy_path.write_bytes(b'\xff\xfe')
    else:
        if change == 'unknown':
            s.owner['extra'] = None
        if change == 'prefix':
            s.owner['policy_sha256'] = s.owner['policy_sha256'][:12]
        if change == 'wallet':
            s.owner['public_wallet'] = L.SIGNER
        if change == 'signer':
            s.owner['public_signer'] = L.WALLET
        if change == 'expired':
            s.owner['valid_until_utc'] = utc(X.AT - NS)
        if change == 'dedicated':
            s.owner['dedicated_wallet'] = False
        if change == 'equity0':
            s.owner['initial_equity_usd'] = '0'
        if change == 'equity101':
            s.owner['initial_equity_usd'] = '100.00001'
        if change == 'session_keys_forbidden':
            s.owner.update(session_key_address=L.SIGNER, session_key_scopes=['CLOB'],
                           session_key_valid_until_utc=utc(X.AT + 30 * H.DAY))
        s.write_owner(H._canonical(s.owner) + (b'\n' if change == 'newline' else b''))
    result = s.run()
    assert result['code'] == code and native_untouched(s)
    assert L.SECRET not in json.dumps(result)


@pytest.mark.parametrize('raw', [b'{}', b'null', b'[]', b'{', b'{"x":1,"x":2}', b'{"x":NaN}'])
def test_malformed_policy_no_echo(setup, raw):
    setup.policy_path.write_bytes(raw)
    value = setup.run()
    assert value['status'] == 'REFUSED' and native_untouched(setup)


# --------------------------------------------------------------------------- R004 / R017

def test_dynamic_fee_inclusive_sizing_market_minimums(setup, monkeypatch):
    s = setup
    candidate = H.hunter_candidates(s.scratch, OP, H._load(s.policy_path, s.owner_path, s.owner_hash, s.root,
                                                            X.AT)[0], X.AT + 1)[0][0]
    policy = s.policy

    def econ(gamma=None, book=None, **kw):
        snap = X.snap(gamma=gamma or X.gamma_doc(orderMinSize=1), clob=book or X.book_doc())
        return H.entry_economics(candidate, snap, s.world.version, policy, X.AT, **kw)

    # Gamma min below 5 sizes dynamically at the fresh best ask with r = max(0.0333, 0.05).
    value = econ()
    # Rule size 9.39 (cost 4.99999) narrows to 9.25 so the SDK cent-grid USDC amount encodes exactly.
    assert H.size_order(ask=Decimal('0.52'), depth=Decimal('10'), rate=Decimal('0.05'), exponent=1,
                        cap=Decimal('5'), floor=Decimal('2'), gamma_min=Decimal('1'), book_min=Decimal('5'),
                        seconds_delay=0) == (Decimal('9.39'), Decimal('0.11719'))
    assert (value['shares'], value['price'], value['hunter_fee']) == (Decimal('9.25'), Decimal('0.52'),
                                                                       Decimal('0.11544'))
    assert value['intent'].requested_shares == '9.25' and value['intent'].price_limit == '0.52'
    assert value['shares'] * value['price'] + value['hunter_fee'] <= 5
    # Gamma USD 5 minimum with a positive fee inside the USD 5 cap: exact closed abstain.
    with pytest.raises(GatewayError, match='MINIMUM_UNSATISFIABLE_WITHIN_FEE_INCLUSIVE_CAP'):
        econ(X.gamma_doc(orderMinSize=5))
    # Gamma rate 0 / fees disabled vs documented 0.05 still uses 0.05.
    for gamma in (X.gamma_doc(orderMinSize=1, feeSchedule={'rate': 0, 'exponent': 1, 'takerOnly': True}),
                  X.gamma_doc(orderMinSize=1, feesEnabled=False)):
        assert econ(gamma)['hunter_fee'] == Decimal('0.11544')
    # Stress EV exactly equal to the margin rejects.
    stress = value['stress']
    policy = dict(s.policy, experimental_margin_usd=str(stress))
    with pytest.raises(GatewayError, match='PILOT_MARGIN_NOT_MET'):
        H.entry_economics(candidate, X.snap(gamma=X.gamma_doc(orderMinSize=1)), s.world.version, policy, X.AT)
    for book, code in ((X.book_doc(asks=[('0.52', '9')]), 'DEPTH_BELOW_SIZE'),):
        with pytest.raises(GatewayError, match=code):
            econ(book=book)
    with pytest.raises(GatewayError, match='SECONDS_DELAY_UNSUPPORTED'):
        econ(X.gamma_doc(orderMinSize=1, secondsDelay=1))


@pytest.mark.parametrize('tie', ['stress', 'deadline', 'token'])
@pytest.mark.parametrize('reverse', [False, True])
def test_selection_tie_breaks_one_pair_only(setup, monkeypatch, tie, reverse):
    s = setup
    a = dict(token_id=X.TOKEN, deadline_ns=START, stress=Decimal('2'))
    b = dict(token_id=X.OTHER_TOKEN, deadline_ns=START + (NS if tie == 'deadline' else 0),
             stress=Decimal('1') if tie == 'stress' else Decimal('2'))
    candidates = [b, a] if reverse else [a, b]
    expected = a if tie in ('stress', 'deadline') else min(candidates, key=lambda x: x['token_id'])
    full = [dict(c, category='SPORTS_NBA_MONEYLINE', gamma_market_id=X.GAMMA_ID, condition_id=X.COND,
                 payout_lower=Decimal('.8'), deadline_code='PILOT_EVENT_STARTED', evaluated_ns=X.AT,
                 hermes_end_ns=X.AT, manifest_sha256='0' * 64, row_sha256='0' * 64) for c in candidates]
    monkeypatch.setattr(H, 'hunter_candidates', lambda *a: (full, {}))
    monkeypatch.setattr(H, 'entry_economics', lambda c, *a, **k: {
        'stress': c['stress'], 'intent': X.intent(s.world, requested_shares='8', token_id=c['token_id']),
        'assessment': None, 'hunter_fee': Decimal(0)})
    attempts = []

    def refused(**kw):
        attempts.append(kw['execution_intent'].token_id)
        return SimpleNamespace(status='PERMIT_REJECTED', hermes_assessment_id=None)
    monkeypatch.setattr(H, 'evaluate_exploratory_gate_c', refused)
    value = s.run()
    assert value['code'] == 'PILOT_PERMIT_REFUSED' and attempts == [expected['token_id']]
    assert s.harness.venue.posts == []


def snapshot(**fees):
    values = dict(fees_enabled=True, fee_taker_only=True, fee_rate='0.05', fee_exponent='1')
    values.update(fees)
    return SimpleNamespace(**values)


def test_fee_truth_and_min_order_feasibility_matrix():
    D = Decimal

    def size(ask, rate, gamma_min, depth='1000', delay=0):
        return H.size_order(ask=D(ask), depth=D(depth), rate=D(rate), exponent=1, cap=D('5'), floor=D('2'),
                            gamma_min=D(gamma_min), book_min=D('5'), seconds_delay=delay)

    q, fee = size('0.50', '0.05', '1')
    assert (q, fee, q * D('0.5') + fee) == (D('9.75'), D('0.12188'), D('4.99688'))
    assert size('0.50', '0', '5') == (D('10.00'), D('0'))
    for args in (('0.90', '0', '5'), ('0.50', '0.03', '5'), ('0.50', '0.05', '5'), ('0.10', '0.05', '5'),
                 ('0.99', '0.05', '5'), ('0.01', '0.03', '5')):
        with pytest.raises(GatewayError, match='MINIMUM_UNSATISFIABLE_WITHIN_FEE_INCLUSIVE_CAP'):
            size(*args)
    # Both sources zero is only a hypothetical documented rate of 0: Sports/Weather are 0.05.
    assert H.fee_bound(snapshot(fee_rate='0'), 'SPORTS_NBA_MONEYLINE', D('0')) == (D('0'), 1)
    for snap in (snapshot(fee_rate='0'), snapshot(fees_enabled=False), snapshot(fee_rate='0.03')):
        for category in H.CATEGORIES:
            assert H.fee_bound(snap, category) == (D('0.05'), 1)
    assert H.fee_bound(snapshot(fee_rate='0.07'), 'WEATHER_US_DAILY_RAIN') == (D('0.07'), 1)
    for bad in (snapshot(fees_enabled=None), snapshot(fee_taker_only=None), snapshot(fee_taker_only=False),
                snapshot(fee_rate=None), snapshot(fee_exponent=None), snapshot(fee_exponent='1.5'),
                snapshot(fee_rate='-0.01')):
        with pytest.raises(GatewayError, match='FEE_CONFIG_UNKNOWN'):
            H.fee_bound(bad, 'SPORTS_NBA_MONEYLINE')
    # Fee rounds UP at 0.00001 and is never underestimated.
    assert H.fee_max(D('0.01'), D('0.5'), D('0.05'), 1) == D('0.00013')
    assert H.fee_max(D('10'), D('0.5'), D('0.05'), 0) == D('0.5')
    # Cap 5 and floor 2 are unchanged ceilings; nothing is clamped.
    assert H.DECIMAL_BOUNDS['max_order_commitment_usd'] == (D('2'), D('5'))
    limits = H.native.CAPITAL_PROFILES[H.PROFILE]
    assert (limits['single_order_floor_usd'], limits['single_order_worst_case_max_usd']) == (D('2'), D('5'))


# --------------------------------------------------------------------------- R005

def test_hunter_intake_requires_verified_operation_and_real_hermes(setup, tmp_path, monkeypatch):
    s = setup
    policy = H._load(s.policy_path, s.owner_path, s.owner_hash, s.root, X.AT)[0]
    candidates, abstains = H.hunter_candidates(s.scratch, OP, policy, X.AT + 1)
    assert [c['token_id'] for c in candidates] == [X.TOKEN] and abstains == {}

    def abstained(**changes):
        s.hunter(**changes)
        return H.hunter_candidates(s.scratch, OP, policy, X.AT + 1)

    cases = [
        (dict(rows=[row(category='CRYPTO_UP_DOWN')]), 'HUNTER_ROW_INELIGIBLE'),
        (dict(markets=[market(reason='PROTOCOL_UNSUPPORTED')]), 'HUNTER_ROW_INELIGIBLE'),  # V2 market
        (dict(rows=[row(reason='HERMES_CONTRARY_EVIDENCE')]), 'HUNTER_ROW_INELIGIBLE'),
        (dict(rows=[row(research_class='NO_TRADE')]), 'HUNTER_ROW_INELIGIBLE'),
        (dict(findings=[]), 'HERMES_EVIDENCE_ABSENT'),
        (dict(findings=[finding(state='NOT_RUN', hermes_flag='NOT_RUN')]), 'HERMES_EVIDENCE_ABSENT'),
        (dict(findings=[finding(state='RESEARCH_FAILED', hermes_flag='RESEARCH_FAILED')]), 'HERMES_EVIDENCE_ABSENT'),
        (dict(findings=[finding(hermes_flag='CONTRARY_EVIDENCE_REPORTED')]), 'HERMES_EVIDENCE_ABSENT'),
        (dict(findings=[finding(origin='OFFLINE_FIXTURE_MODEL_ORIGIN_UNVERIFIED')]), 'HERMES_EVIDENCE_ABSENT'),
        (dict(findings=[finding(receipt=None)]), 'HERMES_EVIDENCE_ABSENT'),
        (dict(findings=[finding(), finding(hermes_flag='CONTRARY_EVIDENCE_REPORTED')]), 'HERMES_EVIDENCE_ABSENT'),
        (dict(evaluated=X.AT - 1801 * NS), 'HUNTER_EVIDENCE_STALE'),
        (dict(evaluated=X.AT + 2 * NS), 'HUNTER_EVIDENCE_STALE'),  # future evidence
        (dict(markets=[market(forecast={'start_ns': X.AT})]), 'PILOT_EVENT_STARTED'),
        (dict(findings=[finding(end_utc=utc(X.AT - 86402 * NS))]), 'HUNTER_EVIDENCE_STALE'),
    ]
    for changes, code in cases:
        candidates, abstains = abstained(**changes)
        assert candidates == [] and abstains == {code: 1}, (changes, abstains)
    # Rain: conservative climate-day cutoff at 00:00 UTC of the target day.
    rain = dict(category='WEATHER_US_DAILY_RAIN')
    rain_policy = dict(policy, categories=['WEATHER_US_DAILY_RAIN'])
    day = datetime.fromtimestamp(X.AT // NS, timezone.utc).strftime('%Y-%m-%d')
    s.hunter(markets=[market(**rain, target_day=day, forecast={})], rows=[row(**rain)])
    assert H.hunter_candidates(s.scratch, OP, rain_policy, X.AT + 1)[1] == {'CLIMATE_DAY_STARTED': 1}
    # Unverified operation (tamper without rehash, BLOCKED, INTERRUPTED, missing index): durable NO_TRADE.
    for mutate in ('tamper', 'blocked', 'interrupted', 'no_index', 'op_name'):
        s.hunter(status='BLOCKED' if mutate == 'blocked' else 'COMPLETED')
        if mutate == 'tamper':
            path = s.scratch / OP / 'manifest.json'
            path.write_bytes(path.read_bytes().replace(b'"0.8"', b'"0.1"'))
        if mutate == 'interrupted':
            (s.scratch / OP / 'terminal.json').write_bytes(canonical({'status': 'INTERRUPTED_OR_UNKNOWN'}))
        if mutate == 'no_index':
            (s.scratch / f'index-{OP}.json').unlink()
        with pytest.raises(GatewayError, match='HUNTER_INTAKE_INVALID|PILOT_INPUT_INVALID'):
            H.hunter_candidates(s.scratch, '../x' if mutate == 'op_name' else OP, policy, X.AT + 1)
    s.hunter(status='BLOCKED')
    result = s.run()
    assert (result['status'], result['code'], result['create_transmits']) == ('NO_TRADE', 'HUNTER_INTAKE_INVALID', 0)
    assert s.harness.venue.posts == [] and len(list((s.root / 'terminals').glob('*.json'))) == 1
    # A forged-but-rehashed hunter chain is caught by the merged hunter verify in the CLI: no src call.
    calls = []
    monkeypatch.setattr(H, 'run_hunter_cycle_once', lambda **kw: calls.append(kw))
    assert CLI.main(['run', '--policy', str(s.policy_path), '--owner-record', str(s.owner_path),
                     '--owner-record-sha256', s.owner_hash, '--state-root', str(s.root),
                     '--hunter-scratch-dir', str(s.scratch), '--hunter-operation', OP]) == 1
    assert calls == []


# --------------------------------------------------------------------------- R006

@pytest.mark.parametrize('change', ['pause', 'revoke', 'hermes', 'deadline', 'kill', 'policy'])
def test_native_authority_reverified_at_latest_point(setup, monkeypatch, change):
    from src.execution_gateway.gate_c import LiveOrchMutationBoundary
    s = setup
    original = LiveOrchMutationBoundary.prepare

    def prepare(self, *a, **kw):
        result = original(self, *a, **kw)
        if change == 'pause':
            s.world.append(X._pause(s.world.version, t=X.AT + 1))
        elif change == 'revoke':
            s.world.append(X.build_portfolio_policy_receipt(action='REVOKE', policy_id=s.world.policy.policy_id,
                previous_active_policy_id=s.world.policy.policy_id, human_authorization_ref='human:synthetic-revoke',
                created_time_ns=X.AT + 1))
        elif change == 'hermes':
            s.world.assess(t=X.AT + 1)
        elif change == 'deadline':
            s.harness.now = START
        elif change == 'kill':
            (s.root / 'PILOT_KILL').touch()
        else:
            s.policy['experimental_margin_usd'] = '0.01'
            s.policy_path.write_bytes(H._canonical(s.policy))
        return result
    monkeypatch.setattr(LiveOrchMutationBoundary, 'prepare', prepare)
    value = s.run()
    assert value['status'] == 'REFUSED' and value['create_transmits'] == 0 and s.harness.venue.posts == []
    expected = {'pause': 'PERMIT_NOT_CURRENT', 'revoke': 'PERMIT_NOT_CURRENT', 'hermes': 'PERMIT_NOT_CURRENT',
                'deadline': 'PERMIT_EXPIRED|PILOT_GUARD_REFUSED:FRESHNESS', 'kill': 'PILOT_GUARD_REFUSED:KILL',
                'policy': 'PILOT_OWNER_RECORD_SCOPE_MISMATCH'}[change]
    assert value['native_result']['code'] in expected.split('|')


# --------------------------------------------------------------------------- R010

SV = 'strategyversion:sha256:' + '3' * 64


def lifecycle(i, *, proceeds, closed_ns):
    buy = {'episode_id': f'buy-{i:02d}', 'state': 'CLOSED_RECONCILED',
           'binding': {'capital_profile': H.PROFILE, 'side': 'BUY', 'closes_episode_id': None,
                       'token_id': f'{i}', 'strategy_version_id': SV, 'price_limit': '0.5'},
           'admission': {'admitted_time_ns': closed_ns - 1, 'worst_case_fee_reserve_usd': '0.1'},
           'reconciliation': {'trades': [{'status': 'CONFIRMED', 'shares': '8', 'principal_usd': '4'}],
                              'fee_state': 'RECONCILED', 'actual_fee_usd': '0.1', 'last_reconciled_time_ns': closed_ns}}
    sell = {'episode_id': f'sell-{i:02d}', 'state': 'TERMINAL_NO_POSITION',
            'binding': {'capital_profile': H.PROFILE, 'side': 'SELL', 'closes_episode_id': f'buy-{i:02d}',
                        'token_id': f'{i}', 'strategy_version_id': SV, 'price_limit': '0.5'},
            'admission': {'admitted_time_ns': closed_ns, 'worst_case_fee_reserve_usd': '0.1'},
            'reconciliation': {'trades': [{'status': 'CONFIRMED', 'shares': '8', 'principal_usd': proceeds}],
                               'fee_state': 'RECONCILED', 'actual_fee_usd': '0.1', 'last_reconciled_time_ns': closed_ns}}
    return [buy, sell]


def ledger(*nets):
    episodes = []
    for i, proceeds in enumerate(nets, 1):
        episodes += lifecycle(i, proceeds=proceeds, closed_ns=X.AT + i * NS)
    return {'episodes': episodes}


def test_consecutive_loss_breaker_pause_and_diagnosis(tmp_path):
    policy = {'consecutive_loss_limit': 3, 'loss_pause_s': 7200, 'strategy_version_ids': {'SPORTS_NBA_MONEYLINE': SV}}
    root = tmp_path
    loss, win = '4', '4.3'  # net = proceeds - 0.1 - 4 - 0.1
    now = X.AT + 10 * NS
    H.breaker(root, policy, ledger(loss, loss), lambda t: None, now)  # limit - 1 continues
    H.breaker(root, policy, ledger(loss, loss, win, loss, loss), lambda t: None, now)  # a win resets
    paused = ledger(win, loss, loss, loss)
    with pytest.raises(GatewayError, match='LOSS_BREAKER_PAUSED'):
        H.breaker(root, policy, paused, lambda t: None, now)
    record = json.loads((root / 'loss-diagnosis-4.json').read_bytes())
    assert [x['episode_id'] for x in record['lifecycles']] == ['buy-02', 'buy-03', 'buy-04']
    assert {x['category'] for x in record['lifecycles']} == {'SPORTS_NBA_MONEYLINE'}
    end = X.AT + 4 * NS + 7200 * NS
    with pytest.raises(GatewayError, match='LOSS_BREAKER_PAUSED'):
        H.breaker(root, policy, paused, lambda t: None, end - 1)
    H.breaker(root, policy, paused, lambda t: None, end)  # exact pause end with valid diagnosis resumes
    (root / 'loss-diagnosis-4.json').write_bytes(b'{}')
    with pytest.raises(GatewayError, match='LOSS_DIAGNOSIS_INVALID'):
        H.breaker(root, policy, paused, lambda t: None, end)
    (root / 'loss-diagnosis-4.json').unlink()
    with pytest.raises(GatewayError, match='LOSS_DIAGNOSIS_INVALID'):
        H.breaker(root, policy, paused, lambda t: None, end)
    # Held-to-resolution: unknown payout counts as zero (loss), a known payout can be a win.
    held = {'episodes': [lifecycle(1, proceeds='0', closed_ns=X.AT)[0]]}
    held['episodes'][0]['reconciliation']['trades'][0]['principal_usd'] = '4'
    assert H.lifecycles(held, lambda t: None)[0]['net_usd'] == '-4.1'
    assert Decimal(H.lifecycles(held, lambda t: Decimal('1'))[0]['net_usd']) == Decimal('3.9')
    assert Decimal(H.lifecycles(held, lambda t: Decimal('2'))[0]['net_usd']) == Decimal('-4.1')


# --------------------------------------------------------------------------- R011 / R012

def test_manual_and_automatic_stops_are_separate(tmp_path, monkeypatch):
    # Manual kill at start: reconcile runs, no entry.
    s = build(tmp_path / 'start', monkeypatch)
    (s.root).mkdir(parents=True, exist_ok=True)
    (s.root / 'PILOT_KILL').touch()
    value = s.run()
    assert (value['status'], value['code']) == ('REFUSED', 'PILOT_KILLED')
    assert s.harness.secret_requests == 1 and s.harness.venue.posts == []
    # Manual kill after preflight.
    s = build(tmp_path / 'preflight', monkeypatch)
    original = H.native.LiveOrchestrator.preflight

    def preflight(self, *a):
        result = original(self, *a)
        (s.root / 'PILOT_KILL').touch()
        return result
    monkeypatch.setattr(H.native.LiveOrchestrator, 'preflight', preflight)
    value = s.run()
    assert (value['status'], value['code'], value['create_transmits']) == ('REFUSED', 'PILOT_KILLED', 0)
    monkeypatch.setattr(H.native.LiveOrchestrator, 'preflight', original)
    # Manual kill blocks an exit; an automatic stop blocks entry but permits the exit.
    s = build(tmp_path / 'exit', monkeypatch)
    enter_position(s)
    s.hunter(rows=[row(payout_bounds=['0.3', '0.95'])])
    (s.root / 'PILOT_KILL').touch()
    value = s.run()
    assert value['code'] == 'PILOT_KILLED' and len(s.harness.venue.posts) == 1
    (s.root / 'PILOT_KILL').unlink()

    def paused(*a):
        raise GatewayError('LOSS_BREAKER_PAUSED')
    monkeypatch.setattr(H, 'breaker', paused)
    monkeypatch.setattr(H.native.LiveOrchestrator, 'canary', lambda *a: pytest.fail('entry after exit'))
    s.harness.venue.on_post = lambda venue, signed: venue.fill_sell(signed, shares='9.25', price='0.5')
    value = s.run()
    assert (value['status'], value['side'], value['create_transmits']) == ('EXIT_RESULT', 'SELL', 1), value
    assert value['native_result'] == {'status': 'EXIT_COMPLETE', 'code': 'ONE_SELL_ATTEMPTED'}
    assert len(s.harness.venue.posts) == 2 and s.harness.venue.posts[-1].side == 'SELL'
    # With no position left, the automatic stop refuses new exposure.
    value = s.run()
    assert (value['status'], value['code']) == ('NO_NEW_EXPOSURE', 'LOSS_BREAKER_PAUSED')
    assert len(s.harness.venue.posts) == 2


@pytest.mark.parametrize('crash', [False, True])
def test_single_mutation_run_lock_and_crash_replay(tmp_path, monkeypatch, crash):
    s = build(tmp_path, monkeypatch)
    s.root.mkdir(parents=True, exist_ok=True)
    with H._run_lock(s.root):
        busy = s.run()
    assert busy['code'] == 'PILOT_RUN_BUSY' and native_untouched(s)
    original = H.native.LiveOrchestrator.canary
    calls = []

    def capture(self, permit, intent):
        calls.append((self, permit, intent))
        return original(self, permit, intent)
    monkeypatch.setattr(H.native.LiveOrchestrator, 'canary', capture)
    if crash:
        record = H.native.ProtectedExecutionGateway.record_live_orch_event

        def write_then_crash(self, event_type, *a, **kw):
            result = record(self, event_type, *a, **kw)
            if event_type == 'LIVE_ORCH_ADMITTED':
                raise RuntimeError('synthetic crash')
            return result
        monkeypatch.setattr(H.native.ProtectedExecutionGateway, 'record_live_orch_event', write_then_crash)
    first = s.run()
    assert len(calls) == 1 and len(s.harness.venue.posts) == (0 if crash else 1)
    assert first['create_transmits'] == (0 if crash else 1)
    replay = original(*calls[0])
    assert replay.code == 'PERMIT_ALREADY_CONSUMED' and replay.create_transmits == 0
    assert len(s.harness.venue.posts) == (0 if crash else 1)


# --------------------------------------------------------------------------- R013 / R014

FORBIDDEN_CLAIMS = ('PROFIT', 'EDGE_PROVEN', 'HERMES_LED', 'ALPHA_CONFIRMED', 'LIVE_CANARY_PASSED')


def check_terminal(s, value):
    assert value['claim'] == 'RESEARCH_ONLY' and value['order_ev'] == 'UNKNOWN'
    assert value['edge_claim'] is None and value['hermes_led_trading_claim'] is None
    assert value['realized_profit'] is None and value['code'] in H.PUBLIC_CODES
    assert set(value['abstain_reasons']) <= H.ABSTAIN_CODES
    text = json.dumps(value)
    assert L.SECRET not in text and not any(claim in text for claim in FORBIDDEN_CLAIMS)
    stored = [json.loads(p.read_bytes()) for p in (s.root / 'terminals').glob('*.json')]
    assert value in stored


def test_terminal_truthful_no_edge_or_hermes_claim(tmp_path, monkeypatch):
    s = build(tmp_path / 'entry', monkeypatch)
    entry = s.run()
    assert entry['status'] == 'ENTRY_RESULT' and entry['scenario_claim'] == 'POSITIVE_AFTER_COST_FULL_FILL_STRESS_SCENARIO'
    check_terminal(s, entry)
    s.hunter(rows=[])
    no_trade = s.run()
    assert no_trade['status'] == 'NO_TRADE'
    check_terminal(s, no_trade)
    s = build(tmp_path / 'refused', monkeypatch)
    monkeypatch.setattr(H.native.LiveOrchestrator, 'reconcile', lambda *a: (_ for _ in ()).throw(ValueError(L.SECRET)))
    refused = s.run()
    assert refused['status'] == 'REFUSED'
    check_terminal(s, refused)
    untrusted = H._terminal(s.root, 'REFUSED', 'UPPERCASE_UNTRUSTED_SENTINEL',
                            result=H.native.LiveOrchResult('exit', 'BLOCKED', 'UPPERCASE_UNTRUSTED_SENTINEL'),
                            abstains={'UPPERCASE_UNTRUSTED_SENTINEL': 1})
    assert 'UPPERCASE_UNTRUSTED_SENTINEL' not in json.dumps(untrusted)
    assert untrusted['native_result'] == {'status': 'BLOCKED', 'code': 'NATIVE_RESULT_INVALID'}


def test_authority_boundary_preserved(capsys):
    root = Path(__file__).resolve().parents[2]
    assert 'LIVE TRADING STATUS: DISABLED' in (root / 'docs/live_trading_authorization.md').read_text(encoding='utf-8')
    source = (root / 'src/live_pilot/hunter_cycle.py').read_text(encoding='utf-8')
    for forbidden in ('from tools', 'import tools', 'os.environ', 'getenv', 'while True', 'time.sleep',
                      'place_order', 'create_order', 'post_order', 'cancel_order', 'submit_order'):
        assert forbidden not in source, forbidden
    # Only live_orch.py and hunter_cycle.py reference the opt-in profile name.
    users = sorted(p.relative_to(root).as_posix() for p in (root / 'src').rglob('*.py')
                   if 'HUNTER_PILOT_02' in p.read_text(encoding='utf-8', errors='ignore'))
    assert users == ['src/execution_gateway/live_orch.py', 'src/live_pilot/hunter_cycle.py']
    # The v1 pilot keeps its exact provider allowlist and is not imported for widening.
    pilot = (root / 'src/live_pilot/pilot.py').read_text(encoding='utf-8')
    assert 'deps.secret_provider_factory is InteractiveGateBSecretProvider' in pilot
    assert 'HUNTER' not in pilot and 'SESSION_KEY' not in pilot
    # CLI: only `run`; malformed arguments never reach src.
    assert CLI.main(['loop']) == 2 and CLI.main(['run']) == 2
    assert 'PILOT_CLI_INVALID' in capsys.readouterr().out


def test_cli_verify_then_single_cycle(setup, monkeypatch, capsys):
    s = setup
    argv = ['run', '--policy', str(s.policy_path), '--owner-record', str(s.owner_path), '--owner-record-sha256',
            s.owner_hash, '--state-root', str(s.root), '--hunter-scratch-dir', str(s.scratch), '--hunter-operation', OP]
    monkeypatch.setattr(CLI.hunter, 'verify', lambda root: {'status': 'VERIFIED', 'operations': 1})
    assert CLI.main(argv, dependencies=s.deps) == 0
    out = json.loads(capsys.readouterr().out)
    assert out['status'] == 'ENTRY_RESULT' and len(s.harness.venue.posts) == 1
    monkeypatch.setattr(CLI.hunter, 'verify', lambda root: (_ for _ in ()).throw(RuntimeError(L.SECRET)))
    assert CLI.main(argv, dependencies=s.deps) == 1
    out = capsys.readouterr().out
    assert 'HUNTER_VERIFY_FAILED' in out and L.SECRET not in out and len(s.harness.venue.posts) == 1


def test_session_key_custody_attestation(tmp_path, monkeypatch):
    """R015 support (called from test_gate_b): owner-record session-key attestation and suspension."""
    assert session_key_attestation_matrix(tmp_path, monkeypatch)


def session_key_attestation_matrix(tmp_path, monkeypatch):
    from src.execution_gateway.gate_b import CredentialDirectorySessionKeyProvider
    good = dict(session_key_address=L.SIGNER, session_key_scopes=['CLOB'],
                session_key_valid_until_utc=utc(X.AT + 30 * H.DAY))
    cases = [({}, 'PILOT_OWNER_RECORD_INVALID'),  # missing attestation
             (dict(good, session_key_scopes=['TRADE']), 'SESSION_KEY_ATTESTATION_INVALID'),
             (dict(good, session_key_scopes=['CLOB', 'ALL']), 'SESSION_KEY_ATTESTATION_INVALID'),
             (dict(good, session_key_address=L.WALLET), 'SESSION_KEY_ATTESTATION_INVALID'),
             (dict(good, session_key_valid_until_utc=utc(X.AT + H.DAY)), 'SESSION_KEY_ATTESTATION_INVALID'),
             (dict(good, session_key_valid_until_utc=utc(X.AT - NS)), 'SESSION_KEY_ATTESTATION_INVALID')]
    for i, (extra, code) in enumerate(cases):
        s = build(tmp_path / f'case-{i}', monkeypatch, custody='SESSION_KEY_CREDENTIAL_DIRECTORY')
        s.owner_extra = extra
        s.write()
        value = s.run()
        assert value['code'] == code and native_untouched(s), (extra, value)
    # Valid attestation: the interactive provider is not allowlisted for SESSION_KEY custody.
    s = build(tmp_path / 'valid', monkeypatch, custody='SESSION_KEY_CREDENTIAL_DIRECTORY')
    s.owner_extra = dict(good, session_key_scopes=['ALL'])
    s.write()
    assert s.run()['code'] == 'PILOT_CUSTODY_UNAVAILABLE' and native_untouched(s)
    # A simulated venue authentication rejection latches suspension until a new owner digest.
    s.deps.native.secret_provider_factory = CredentialDirectorySessionKeyProvider
    monkeypatch.setattr(H.native.LiveOrchestrator, 'reconcile',
                        lambda self: H.native.LiveOrchResult('reconcile', 'BLOCKED', 'AUTHENTICATION_FAILED'))
    first = s.run()
    assert (first['status'], first['code']) == ('REFUSED', 'CUSTODY_SUSPENDED')
    assert (s.root / f'custody-suspended-{s.owner_hash}.json').exists()
    monkeypatch.setattr(H.native.LiveOrchestrator, 'reconcile',
                        lambda self: H.native.LiveOrchResult('reconcile', 'NO_NEW_EXPOSURE_READY', 'RECONCILED',
                                                             details={'collateral_usd': '100'}))
    assert s.run()['code'] == 'CUSTODY_SUSPENDED'  # stays latched; reconcile still ran
    s.owner_extra = dict(good, session_key_scopes=['CLOB'])
    s.write()  # new owner record digest clears it
    assert s.run()['code'] != 'CUSTODY_SUSPENDED'
    return True
