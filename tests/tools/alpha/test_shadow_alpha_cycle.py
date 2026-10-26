"""Synthetic offline replicas test logic only; genuine public receipts are separate."""
from copy import deepcopy
from datetime import datetime, timezone
from email.utils import format_datetime
import json
from pathlib import Path
import socket

import pytest

from tools.alpha import run_shadow_alpha_cycle as tool

NOW = tool.ns('2026-10-26T18:00:00Z')
START = tool.ns('2026-10-27T23:30:00Z')


def market():
    return {'id': '12345', 'conditionId': '0x' + 'a' * 64, 'sportsMarketType': 'moneyline',
        'question': 'Nets vs. Celtics', 'outcomes': '["Nets","Celtics"]', 'clobTokenIds': '["111","222"]',
        'gameStartTime': '2026-10-27T23:30:00Z', 'slug': 'nba-bkn-bos-2026-10-27',
        'resolutionSource': 'https://www.nba.com/', 'endDate': '2026-10-27T23:30:00Z',
        'active': True, 'closed': False, 'acceptingOrders': True, 'enableOrderBook': True,
        'restricted': True, 'negRisk': False, 'orderMinSize': '5', 'orderPriceMinTickSize': '0.01',
        'feesEnabled': True, 'feeSchedule': {'rate': '0.02', 'exponent': 1, 'takerOnly': True},
        'description': 'In the upcoming NBA game, scheduled for October 27 at 7:30PM ET:\n'
            'If the Nets win, the market will resolve to "Nets".\n'
            'If the Celtics win, the market will resolve to "Celtics".\n'
            'If the game is postponed, this market will remain open until the game has been completed.\n'
            'If the game is canceled entirely, with no make-up game, this market will resolve 50-50.\n'
            'The result will be determined based on the final score including any overtime periods.'}


def summary():
    competitors = [{'team': {'id': '17', 'name': 'Nets'}, 'homeAway': 'away'},
                   {'team': {'id': '2', 'name': 'Celtics'}, 'homeAway': 'home'}]
    return {'header': {'id': '401909877', 'league': {'slug': 'nba'}, 'competitions': [
        {'date': '2026-10-27T23:30:00Z', 'competitors': competitors,
         'status': {'type': {'state': 'pre', 'completed': False}}}]},
        'predictor': {'header': 'Matchup Predictor', 'homeTeam': {'id': '2', 'gameProjection': '83.3'},
                      'awayTeam': {'id': '17', 'gameProjection': '16.7'}}}


def book(token='111', ask='0.60'):
    return {'market': market()['conditionId'], 'asset_id': token, 'timestamp': str(NOW // 1_000_000),
        'hash': 'abc123', 'neg_risk': False, 'tick_size': '0.01', 'min_order_size': '5',
        'last_trade_price': '0.59', 'bids': [{'price': '0.58', 'size': '100'}],
        'asks': [{'price': ask, 'size': '100'}]}


def receipt(now=NOW):
    return {'started_ns': now - 1_000_000, 'received_ns': now, 'sha256': 'b' * 64,
            'http_date': format_datetime(datetime.fromtimestamp(now // 1_000_000_000, timezone.utc))}


def forecast():
    value = tool.probability(market(), summary(), receipt(), NOW)
    value.update(market_id='12345', condition_id=market()['conditionId'],
        token_ids=['111', '222'], outcomes=['Nets', 'Celtics'],
        rule_sha256=tool.digest(market()['description'].encode()), cutoff_ns=NOW, prediction_id='forecast-1')
    return value


@pytest.fixture
def clock(monkeypatch):
    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 10, 26, 18, tzinfo=timezone.utc)
    monkeypatch.setattr(tool, 'datetime', Clock)
    monkeypatch.setattr(tool.time, 'time_ns', lambda: NOW)
    monkeypatch.setattr(socket, 'socket', lambda *a, **k: pytest.fail('network dispatched in offline test'))


class ReplicaFetcher:
    """Recorded-input harness; never treated as empirical provider evidence."""
    markets = None

    def __init__(self, operation):
        self.operation, self.receipts = operation, []

    def get(self, url):
        m = market()
        if url == tool.DISCOVERY_URL:
            data = self.markets if self.markets is not None else [m]
        elif url.startswith(tool.ESPN + 'scoreboard?'):
            data = {'events': [{'id': '401909877', 'competitions': summary()['header']['competitions']}]}
        elif url.startswith(tool.ESPN + 'summary?'):
            data = summary()
        else:
            data = book('222' if '222' in url else '111')
        raw = tool.canonical(data)
        name = f'source-{len(self.receipts) + 1:02d}.json'
        (self.operation / name).write_bytes(raw)
        r = dict(receipt(), url=url, state='AVAILABLE', publication_time=None, raw_file=name, sha256=tool.digest(raw))
        self.receipts.append(r)
        tool.put(self.operation / f'request-{len(self.receipts):02d}.started.json', {'url': url, 'started_ns': r['started_ns']})
        tool.put(self.operation / f'receipt-{len(self.receipts):02d}.json', r)
        return data


def init(tmp_path):
    root = tmp_path / 'shadow'
    root.mkdir()
    tool.put(root / 'config.json', tool.CONFIG)
    return root


def test_real_source_method_and_exact_market_predicate():
    p = forecast()
    assert p['p'] == '0.167' and p['conditional_on'] == 'COMPLETED_GAME'
    assert p['publication_time'] is None and p['provider_model_version'] == 'NOT_PUBLISHED'
    assert p['uncertainty_kind'] == 'UNCALIBRATED_SENSITIVITY'
    m = market()
    m['description'] = m['description'].replace('including any overtime periods', 'excluding overtime')
    with pytest.raises(tool.Stop, match='RULE_UNSUPPORTED'):
        tool.probability(m, summary(), receipt(), NOW)


def test_discovery_coverage_skips_and_repeated_attempt_denominators(tmp_path, clock):
    root = init(tmp_path)
    first = tool.cycle(root, fetcher_type=ReplicaFetcher)
    assert first['status'] == 'SHADOW_INTELLIGENCE_REAL_EVIDENCE_PASS', first
    assert first['denominators']['observed'] == first['denominators']['screened'] == 1
    assert len(first['native_discovery']['triage']) == 1
    second = tool.cycle(root, fetcher_type=ReplicaFetcher)
    assert first['forecasts'][0]['prediction_id'] == second['forecasts'][0]['prediction_id']
    verified = tool.verify(root)
    assert verified['occurrences'] == 2 and verified['fresh_attempts'] == 0
    assert verified['recorded_network_attempts'] == 12


def test_net_ev_uncertainty_fee_queue_and_nonfill():
    score = tool.economics(market(), book(), forecast(), 0, receipt(), NOW)
    assert score['gross_completion_ev'] == '-4.330'
    assert score['fee'] == '0.04800' and score['completion_ev'] == '-4.42800'
    assert score['fill_scenarios']['zero_fill_ev'] == '0' and score['realized_profit'] is None
    assert tool.economics(market(), book(), forecast(), 0, receipt(), NOW, style='MAKER')['reason'] == 'MAKER_FILL_UNMEASURED'
    tiny = book()
    tiny['asks'][0]['size'] = '1'
    assert tool.economics(market(), tiny, forecast(), 0, receipt(), NOW)['admissible'] is False


def test_shadow_policy_positive_negative_and_uncertain_ev():
    assert tool.economics(market(), book(), forecast(), 0, receipt(), NOW)['action'] == 'NO_TRADE'
    # A supported uncertain forecast can have positive scenario EV without near-certainty.
    f = forecast()
    f.update(p='0.75', stress_lower='0.65', stress_upper='0.85')
    m = market()
    m['orderMinSize'] = '1'
    b = book(ask='0.40')
    b['bids'][0]['price'] = '0.39'
    score = tool.economics(m, b, f, 0, receipt(), NOW)
    assert score['action'] == 'RESEARCH' and tool.D(score['completion_ev']) > 0
    assert score['fill_probability'] is None and tool.D(score['per_order_ev_identification_bound'][0]) < 0


@pytest.mark.parametrize('change,code', [('future', 'SOURCE_LOOKAHEAD'), ('stale', 'SOURCE_STALE'),
                                       ('teams', 'SOURCE_TEAM_MISMATCH'), ('started', 'PREDICTION_NOT_PREGAME')])
def test_source_cutoff_market_identity_and_lookahead_rejections(change, code):
    s, r = summary(), receipt()
    if change == 'future':
        r['received_ns'] += 1
    elif change == 'stale':
        r['received_ns'] -= 301_000_000_000
        r['started_ns'] = r['received_ns']
    elif change == 'teams':
        s['header']['competitions'][0]['competitors'][0]['team']['name'] = 'Different'
    else:
        s['header']['competitions'][0]['status']['type']['state'] = 'in'
    with pytest.raises(tool.Stop, match=code):
        tool.probability(market(), s, r, NOW)


def finished():
    m, s, f = market(), summary(), forecast()
    m.update(closed=True, umaResolutionStatus='resolved', outcomePrices='["0","1"]', closedTime='2026-10-28T02:30:00Z')
    s['header']['competitions'][0]['status']['type'].update(state='post', completed=True)
    s['header']['competitions'][0]['competitors'][1]['winner'] = True
    later = START + 12_000_000_000_000
    return f, m, s, receipt(later), later


def test_nonbinary_void_tie_and_disputed_resolution_rules():
    f, m, s, r, t = finished()
    m['outcomePrices'] = '["0.5","0.5"]'
    s['header']['competitions'][0]['status']['type']['name'] = 'STATUS_CANCELED'
    assert tool.resolution(f, m, s, r, t)['state'] == 'VOID_HALF_PAY'
    m['umaResolutionStatus'] = 'disputed'
    assert tool.resolution(f, m, s, r, t)['state'] == 'UNRESOLVED'
    m['umaResolutionStatus'], m['outcomePrices'] = 'resolved', '["0.2","0.8"]'
    with pytest.raises(tool.Stop, match='OUTCOME_PAYOUT_UNSUPPORTED'):
        tool.resolution(f, m, s, r, t)


def test_independent_resolution_metrics_against_market_baseline():
    f, m, s, r, t = finished()
    assert tool.resolution(f, m, s, r, t)['payout'] == '0'
    rows = [dict(event_id=str(i), p='0.2', market_p='0.4', y='0', cutoff_ns=i,
                 outcome_available_ns=i + 1) for i in (1, 2)]
    results = tool.learning(rows + [rows[0]])
    assert results['independent_events'] == 2
    assert results['metrics'][0]['forecast']['brier'] == '0.04'
    assert results['metrics'][0]['market']['brier'] == '0.16'
    assert tool.D(results['metrics'][0]['forecast']['log_loss']) > 0


def test_versioned_improvement_oos_or_insufficient_data():
    assert tool.learning([])['status'] == 'IMPROVEMENT_NOT_YET_MEASURABLE'
    rows = [dict(event_id=str(i), p='0.8', market_p='0.2', y='0', cutoff_ns=i * 10,
                 outcome_available_ns=i * 10 + 1) for i in range(20)]
    learned = tool.learning(rows)
    assert learned['adopted'] is False and learned['proposal']['blend_weight'] == '0.25'
    assert learned['proposal']['formation_events'] == learned['proposal']['holdout_events'] == 10
    later = dict(rows[0], event_id='delayed', cutoff_ns=-1)
    assert tool.learning(rows + [later])['proposal_id'] == learned['proposal_id']
    rows[0]['outcome_available_ns'] = 9999
    assert tool.learning(rows)['reason'] == 'FORMATION_LABELS_NOT_AVAILABLE_BEFORE_HOLDOUT'


def test_shadow_paper_live_evidence_never_conflated(tmp_path, clock):
    result = tool.cycle(init(tmp_path), fetcher_type=ReplicaFetcher)
    assert result['paper'] == 'NO_PAPER_SESSION'
    assert result['realized_profit'] is None and result['order_attempts'] == result['account_attempts'] == 0
    assert all(s['realized_profit'] is None for s in result['scores'])
    from tests.research_runtime.hermes_controlled_runtime.test_autonomous_feedback import paper_store
    source = tmp_path / 'research-paper.sqlite3'
    paper_store(source, 'alphacandidate:sha256:' + 'a' * 64)
    before = source.read_bytes()
    linked = tool.link_paper(tmp_path / 'shadow', source)
    assert linked['evidence_class'] == 'NATIVE_RESEARCH_PAPER' and linked['link'] == 'UNLINKED_NOT_CAUSAL'
    assert linked['snapshot']['fill_count'] > 0 and linked['shadow_fill_credit'] is None
    assert source.read_bytes() == before
    assert tool.verify(tmp_path / 'shadow')['fresh_attempts'] == 0


def test_partial_crash_replay_and_protected_boundary(tmp_path, clock):
    root = init(tmp_path)
    op = tool.begin(root, 'CYCLE')
    tool.put(op / 'request-01.started.json', {'url': tool.DISCOVERY_URL, 'started_ns': NOW})
    result = tool.cycle(root, fetcher_type=ReplicaFetcher)
    assert result['status'] != 'BLOCKED', result
    assert tool.read(op / 'terminal.json')['status'] == 'INTERRUPTED_OR_UNKNOWN'
    assert tool.verify(root)['interrupted_or_unknown'] == 1
    assert tool.verify(root)['network_attempt_outcome_unknown'] == 1
    raw = root / 'op-000002/source-01.json'
    raw.write_bytes(b'[]')
    with pytest.raises(tool.Stop, match='JOURNAL_HASH_MISMATCH|SOURCE_HASH_MISMATCH'):
        tool.verify(root)
    with pytest.raises(tool.Stop):
        tool.cycle(root, fetcher_type=ReplicaFetcher)
    with pytest.raises(tool.Stop, match='PATH_FORBIDDEN'):
        tool.safe(tool.REPO / 'out.json')
    assert not tool.url_ok('https://gamma-api.polymarket.com/markets?authorization=bad')
    other = tmp_path / 'another-checkout'
    other.mkdir()
    (other / '.git').write_text('gitdir: ignored-by-test')
    with pytest.raises(tool.Stop, match='PATH_FORBIDDEN'):
        tool.safe(other / 'scratch', directory=True)


def test_public_source_unavailable_is_honest_block(tmp_path, clock):
    class Missing(ReplicaFetcher):
        def get(self, url):
            return None
    result = tool.cycle(init(tmp_path), fetcher_type=Missing)
    assert result['status'] == 'BLOCKED' and result['reason'] == 'DISCOVERY_UNAVAILABLE'
    assert 'forecasts' not in result


def test_provider_payload_depth_and_decimal_representation():
    nested = {'a': {'b': {'c': {'d': {'e': {'f': {'g': {'h': {'i': {'j': {'k': {'l': {'m': 1}}}}}}}}}}}}}
    assert tool.decode(tool.canonical(nested)) == nested
    assert tool.decode(b'{"quote":0.60}') == {'quote': '0.60'}
    with pytest.raises(Exception):
        tool.decode(b'{"quote":1,"quote":2}')
    with pytest.raises(Exception):
        tool.decode(b'{"quote":NaN}')


def test_resolution_corroboration_clocks_and_journal_replay(tmp_path, clock, monkeypatch):
    root = init(tmp_path)
    tool.cycle(root, fetcher_type=ReplicaFetcher)
    f, m, s, r, later = finished()
    m['closedTime'] = '2026-10-26T16:00:00Z'
    with pytest.raises(tool.Stop, match='RESOLUTION_CLOCK_INVALID'):
        tool.resolution(f, m, s, r, later)
    m['closedTime'], m['outcomePrices'] = '2026-10-28T02:30:00Z', '["0.5","0.5"]'
    with pytest.raises(tool.Stop, match='CANCELLATION_NOT_CORROBORATED'):
        tool.resolution(f, m, s, r, later)
    # No later games yet: this still freezes and re-derives an empty outcome update.
    result = tool.update_outcomes(root, fetcher_type=ReplicaFetcher)
    assert result['new_observations'] == [] and result['learning']['independent_events'] == 0
    path = root / 'op-000002/terminal.json'
    terminal = tool.read(path)
    terminal['result']['learning']['independent_events'] = 99
    path.write_bytes(tool.canonical(terminal) + b'\n')
    with pytest.raises(tool.Stop, match='REPLAY_MISMATCH'):
        tool.verify(root)


def test_inadmissible_quotes_and_token_reassignment(tmp_path, clock):
    class TooSmall(ReplicaFetcher):
        def get(self, url):
            data = super().get(url)
            if 'book?' in url:
                data['min_order_size'] = '20'
                raw = tool.canonical(data)
                r = self.receipts[-1]
                (self.operation / r['raw_file']).write_bytes(raw)
                r['sha256'] = tool.digest(raw)
                (self.operation / f'receipt-{len(self.receipts):02d}.json').write_bytes(tool.canonical(r) + b'\n')
            return data
    result = tool.cycle(init(tmp_path), fetcher_type=TooSmall)
    assert result['status'] == 'DATA_INSUFFICIENT'
    assert result['denominators']['scored_outcomes'] == 0 and result['denominators']['unscorable_outcomes'] == 2
    f, m, s, r, t = finished()
    m['clobTokenIds'] = '["222","111"]'
    with pytest.raises(tool.Stop, match='OUTCOME_TOKEN_OR_ORDER_CHANGED'):
        tool.resolution(f, m, s, r, t)


def test_network_deadline_and_outcome_progress(tmp_path, monkeypatch):
    class Socket:
        def settimeout(self, value):
            assert 0 < value <= 20
    class Response:
        from types import SimpleNamespace
        fp = SimpleNamespace(raw=SimpleNamespace(_sock=Socket()))
        def read1(self, count):
            return b'x'
    ticks = iter((10, 11, 30))
    monkeypatch.setattr(tool.time, 'monotonic', lambda: next(ticks))
    with pytest.raises(tool.Stop, match='NETWORK_DEADLINE'):
        tool.bounded_body(Response(), 20)
    prior = [(None, {'result': {'forecasts': [dict(event_id=str(i), market_id=str(i), cutoff_ns=i, start_ns=1)
        for i in range(9)], 'scores': [dict(market_id=str(i), outcome_index=0, p_market='0.5') for i in range(9)]}})]
    pending, _ = tool.pending_forecasts(prior)
    assert len(pending) == 9
    first = [event for event, _ in pending[:8]]
    prior.append((None, {'result': {'outcomes': [{'event_id': event, 'state': 'UNRESOLVED'} for event in first]}}))
    next_batch, _ = tool.pending_forecasts(prior)
    assert next_batch[0][0] == '8' and len(next_batch[:8]) == 8
