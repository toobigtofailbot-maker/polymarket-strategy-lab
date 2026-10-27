"""S10-HERMES-ALPHA-HUNTER-01: R001-R012, one node per requirement, zero network.

Fixtures: the rain market, station, points and gridpoint values are trimmed real public payloads
captured 2026-10-27 (Gamma market 6296029, api.weather.gov KNYC / OKX 34,45). The NBA Gamma market
6000460 identity is real (2026-10-27); its ESPN summary and every CLOB book are recorded-shape
harness payloads, never empirical evidence.
"""
from copy import deepcopy
from datetime import date, datetime, timezone
from decimal import Decimal as D
from email.utils import format_datetime
import json
from pathlib import Path
import socket

import pytest

from tools.alpha import run_alpha_hunter as H
from tools.alpha import run_shadow_alpha_cycle as S
from src.data_layer.analytical_research import alpha_factory as AF
from src.data_layer.analytical_research import alpha_factory_registry as AFR
from src.research_runtime.hermes_controlled_runtime import (
    DRAFT_AUTHORITY_FLAGS, DRAFT_SCHEMA_VERSION, ExternalHermesCliBackend, FakeHermesBackend,
)

NOW = S.ns('2026-10-27T12:00:00Z')
NBA_TOKENS = ['11409777207328165390919279256789740022452522804467947761029121495487617647709',
              '92481387921872041058661072348695943856309399117361555404084696545266952026678']
RAIN_TOKENS = ['91555782816137612161706581242357330382148515173873612805379166659971565705225',
               '88542497651765030591586427284353151820449886394943561361913418648914652607231']
NBA_DESC = ('In the upcoming NBA game, scheduled for October 27 at 8:00PM ET:\n'
            'If the Kings win, the market will resolve to "Kings".\n'
            'If the Spurs win, the market will resolve to "Spurs".\n'
            'If the game is postponed, this market will remain open until the game has been completed.\n'
            'If the game is canceled entirely, with no make-up game, this market will resolve 50-50.\n'
            'The result will be determined based on the final score including any overtime periods.')
RAIN_DESC = (
    'This market will resolve to "Yes" if New York, NY records measurable precipitation on October 28, 2026. '
    'Otherwise, this market will resolve to "No".\n\nMeasurable precipitation means 0.01 inches or more as '
    'reported by the PRECIPITATION (IN) figure in the NWS Daily Climate Report (CLI) for the city\'s station.\n\n'
    'A report of trace ("T") does not qualify.\n\nThe PRECIPITATION (IN) figure measures total liquid-equivalent '
    'precipitation and does not distinguish between precipitation types.\n\nThe observation period is the NWS '
    'climate day for KNYC: midnight to midnight local standard time. The final CLI report for a climate day is '
    'issued the following morning.\n\nThis market will resolve according to the NWS Daily Climate Report as '
    'published by 2:00 PM ET on the day following the observation date. If multiple versions of the report are '
    'issued, the last version published before that time governs. If no figure has been published by that time, '
    'this market will resolve to "No".\n\nThe resolution source for this market is the NWS Daily Climate Report '
    '(CLI) for KNYC, published at https://forecast.weather.gov/product.php?site=NWS&product=CLI&issuedby=NYC.')
VENUE = {'active': True, 'closed': False, 'acceptingOrders': True, 'enableOrderBook': True,
         'restricted': True, 'negRisk': False, 'orderMinSize': 5, 'feesEnabled': True,
         'feeSchedule': {'exponent': 1, 'rate': 0, 'takerOnly': True, 'rebateRate': 0}}


def nba_market():
    return dict(VENUE, id='6000460', conditionId='0x6fe90c6a80569ce724246416ed52d373c5e7cfaed153c596ce274a11a9491de7',
                question='Kings vs. Spurs', outcomes='["Kings", "Spurs"]', clobTokenIds=json.dumps(NBA_TOKENS),
                gameStartTime='2026-10-28 00:00:00+00', slug='nba-sac-sas-2026-10-27', sportsMarketType='moneyline',
                resolutionSource='https://www.nba.com/', orderPriceMinTickSize='0.01', description=NBA_DESC,
                endDate='2026-10-28T00:00:00Z', positionIds=['801981622870127801312002439073243400611991479377279001641867010565967183872',
                                                             '801981622870127801312002439073243400611991479377279001641867010565967183873'])


def nba_summary():
    competitors = [{'team': {'id': '23', 'name': 'Kings'}, 'homeAway': 'away'},
                   {'team': {'id': '24', 'name': 'Spurs'}, 'homeAway': 'home'}]
    return {'header': {'id': '401900001', 'league': {'slug': 'nba'}, 'competitions': [
        {'date': '2026-10-28T00:00Z', 'competitors': competitors, 'status': {'type': {'state': 'pre'}}}]},
        'predictor': {'header': 'Matchup Predictor', 'homeTeam': {'id': '24', 'gameProjection': '38.0'},
                      'awayTeam': {'id': '23', 'gameProjection': '62.0'}}}


def rain_market():
    return dict(VENUE, id='6296029', conditionId='0x3120a03bd223f3f58879d39ef6aff25bf5a89bdf57b3bc60a76528a4820470e3',
                question='Will it rain in New York, NY on October 28?', outcomes='["Yes", "No"]',
                clobTokenIds=json.dumps(RAIN_TOKENS), slug='where-will-it-rain-on-october-28-2026-new-york-ny',
                resolutionSource='https://forecast.weather.gov/product.php?site=NWS&product=CLI&issuedby=NYC',
                orderPriceMinTickSize='0.001', description=RAIN_DESC, endDate='2026-10-29T18:00:00Z', positionIds=None)


def station():
    return {'geometry': {'type': 'Point', 'coordinates': ['-73.96667', '40.78333']},
            'properties': {'stationIdentifier': 'KNYC', 'timeZone': 'America/New_York', 'name': 'New York City, Central Park'}}


def grid(values=None, update='2026-10-27T10:00:05+00:00', uom='wmoUnit:percent'):
    values = values if values is not None else [
        {'validTime': '2026-10-28T00:00:00+00:00/PT6H', 'value': 0},
        {'validTime': '2026-10-28T06:00:00+00:00/PT6H', 'value': 1},
        {'validTime': '2026-10-28T12:00:00+00:00/P3DT12H', 'value': 0}]
    return {'properties': {'updateTime': update, 'probabilityOfPrecipitation': {'uom': uom, 'values': values}}}


def book(market, token, ask='0.97', bid='0.95', size='100', tick='0.001', minimum='5'):
    return {'market': market['conditionId'], 'asset_id': token, 'timestamp': str(NOW // 1_000_000), 'hash': 'abc123',
            'neg_risk': False, 'tick_size': tick, 'min_order_size': minimum, 'last_trade_price': bid,
            'bids': [{'price': bid, 'size': size}], 'asks': [{'price': ask, 'size': size}]}


def payloads():
    rain, nba = rain_market(), nba_market()
    out = {S.DISCOVERY_URL: [nba],
           S.ESPN + 'scoreboard?dates=20261027': {'events': [{'id': '401900001', 'competitions': nba_summary()['header']['competitions']}]},
           S.ESPN + 'scoreboard?dates=20261028': {'events': []},
           S.ESPN + 'summary?event=401900001': nba_summary(),
           H.rain_event_url(date(2026, 10, 28)): {'slug': 'where-will-it-rain-on-october-28-2026', 'markets': [rain]},
           H.rain_event_url(date(2026, 10, 29)): None,
           H.NWS + 'stations/KNYC': station(),
           H.NWS + 'points/40.7833,-73.9667': {'properties': {'forecastGridData': H.NWS + 'gridpoints/OKX/34,45'}},
           H.NWS + 'gridpoints/OKX/34,45': grid()}
    out[S.venue.clob_book_url(NBA_TOKENS[0])] = book(nba, NBA_TOKENS[0], ask='0.55', bid='0.54', tick='0.01')
    out[S.venue.clob_book_url(NBA_TOKENS[1])] = book(nba, NBA_TOKENS[1], ask='0.46', bid='0.45', tick='0.01')
    out[S.venue.clob_book_url(RAIN_TOKENS[0])] = book(rain, RAIN_TOKENS[0], ask='0.03', bid='0.02')
    out[S.venue.clob_book_url(RAIN_TOKENS[1])] = book(rain, RAIN_TOKENS[1], ask='0.97', bid='0.96')
    return out


def replica(data):
    class Replica:
        def __init__(self, operation):
            self.operation, self.receipts = operation, []

        def get(self, url):
            assert H.url_ok(url), url
            value = data.get(url)
            n = len(self.receipts) + 1
            receipt = {'url': url, 'started_ns': NOW - 2_000_000, 'received_ns': NOW - 1_000_000,
                       'http_date': format_datetime(datetime.fromtimestamp(NOW // 1_000_000_000, timezone.utc)),
                       'state': 'UNAVAILABLE', 'sha256': None, 'raw_file': None}
            S.put(self.operation / f'request-{n:02d}.started.json', {'url': url})
            if value is not None:
                raw = S.canonical(value)
                (self.operation / f'source-{n:02d}.json').write_bytes(raw)
                receipt.update(state='AVAILABLE', sha256=S.digest(raw), raw_file=f'source-{n:02d}.json')
            self.receipts.append(receipt)
            S.put(self.operation / f'receipt-{n:02d}.json', receipt)
            return H.data(self.operation, receipt)
    return Replica


@pytest.fixture
def offline(monkeypatch):
    monkeypatch.setattr(socket, 'socket', lambda *a, **k: pytest.fail('network dispatched in offline test'))


def setup(tmp_path):
    root = tmp_path / 'hunter'
    root.mkdir()
    registry = tmp_path / 'alpha.sqlite3'
    assert AFR.initialize_alpha_factory_registry(str(registry)).is_valid
    return root, registry


def clock():
    ticks = iter(range(NOW, NOW + 10_000_000_000, 1_000_000))
    return lambda: next(ticks)


def run(tmp_path, data=None, **kw):
    root, registry = setup(tmp_path)
    result = H.run(root, registry, {'nba', 'rain'}, fetcher_type=replica(data or payloads()), clock_ns=clock(), **kw)
    return root, registry, result


def manifest(root, n=1):
    return S.read(root / f'op-{n:06d}' / 'manifest.json')


def gamma(market):
    return H.gamma_state(market, market['id'], market['conditionId'], S.array(market['clobTokenIds'])[0])


# ------------------------------------------------------------------ R001

def test_two_category_source_to_candidate_demonstration(tmp_path, offline):
    root, _, result = run(tmp_path)
    assert result['status'] == 'COMPLETED', result
    m = manifest(root)
    methods = {mk['category']: mk['forecast']['method'] for mk in m['markets'] if mk['forecast']}
    assert methods == {'SPORTS_NBA_MONEYLINE': S.METHOD, 'WEATHER_US_DAILY_RAIN': H.METHOD_RAIN}
    assert m['funnel']['probability_assessed'] == 2 and m['funnel']['assessed_tokens'] == 4
    assert {t['category'] for t in m['tokens'] if t['research_class'] == 'RESEARCH_CANDIDATE'} == {
        'SPORTS_NBA_MONEYLINE', 'WEATHER_US_DAILY_RAIN'}
    assert m['run_mode'] == 'PUBLIC_SCREENER_NO_HERMES'
    assert m['hermes_alpha_hunter_milestone'] == 'UNSATISFIED_REAL_INFERENCE_NOT_DEMONSTRATED'
    assert result['hermes_state'] == 'HERMES_NOT_RUN_BUDGET_ZERO'
    assert H.verify(root) == {'status': 'VERIFIED', 'operations': 1, 'network_attempts': 0, 'hermes_dispatches': 0}


# ------------------------------------------------------------------ R002

def test_rain_climate_day_probability_bounds_and_labels():
    window = (datetime(2026, 10, 28, 5, tzinfo=timezone.utc), datetime(2026, 10, 29, 5, tzinfo=timezone.utc))
    real = H.rain_probability(grid(), window, NOW)
    assert (D(real['stress_lower']), D(real['stress_upper']), D(real['p'])) == (D('0.01'), D('0.06'), D('0.01'))
    assert real['point_assumption'] == 'INTERVAL_INDEPENDENCE_AND_UNIFORM_WITHIN_INTERVAL'
    assert real['spatial_assumption'] == 'GRID_CELL_EQUALS_STATION' and real['calibration'] == 'UNPROVEN'
    straddle = H.rain_probability(grid([{'validTime': '2026-10-28T00:00:00+00:00/PT12H', 'value': 50},
                                        {'validTime': '2026-10-28T12:00:00+00:00/PT18H', 'value': 20}]), window, NOW)
    # Neither interval lies fully inside the window: the lower bound is 0, never the straddling 0.50.
    assert D(straddle['stress_lower']) == 0
    assert D(straddle['stress_upper']) == min(D(1), D('0.5') * 7 + D('0.2') * 17)
    assert D(straddle['stress_lower']) <= D(straddle['p']) <= D(straddle['stress_upper'])
    nba = nba_market()
    no_row = H.economics('WEATHER_US_DAILY_RAIN', *gamma(rain_market()), book(rain_market(), RAIN_TOKENS[1]),
                         real, 1, RAIN_TOKENS[1], rain_market()['conditionId'], NOW)
    assert no_row['p_estimate'] == str(1 - D('0.01')) and no_row['payout_bounds'] == [str(1 - D('0.06')), str(1 - D('0.01'))]
    assert nba['id'] == '6000460'


# ------------------------------------------------------------------ R003

def test_venue_economics_parity_fee_minimum_depth():
    market = nba_market()
    market['feeSchedule'] = {'exponent': 1, 'rate': '0.02', 'takerOnly': True}
    forecast = {'p': '0.62', 'stress_lower': '0.52', 'stress_upper': '0.72', 'event_id': '401900001'}
    receipt = {'started_ns': NOW - 2, 'received_ns': NOW - 1, 'sha256': 'b' * 64,
               'http_date': format_datetime(datetime.fromtimestamp(NOW // 1_000_000_000, timezone.utc))}
    for index, ask in ((0, '0.55'), (1, '0.60')):
        b = book(market, NBA_TOKENS[index], ask=ask, bid='0.30', tick='0.01')
        native = S.economics(market, b, forecast, index, receipt, NOW)
        mine = H.economics('SPORTS_NBA_MONEYLINE', *gamma(market), b, forecast, index, NBA_TOKENS[index],
                           market['conditionId'], NOW)
        for key, theirs in (('notional', None), ('fee', 'fee'), ('residual_cost', 'residual_cost'),
                            ('estimated_after_cost_margin', 'completion_ev')):
            if theirs:
                assert D(mine[key]) == D(native[theirs])
        assert D(mine['estimated_after_cost_margin']) + D(mine['fee']) + D(mine['residual_cost']) == D(native['gross_completion_ev']) + 0
        assert mine['fee_rate_source_disagreement'] is True
    for change, code in ((dict(minimum='20'), 'VENUE_MINIMUM_OR_DEPTH_UNSUPPORTED'),
                         (dict(size='5'), 'VENUE_MINIMUM_OR_DEPTH_UNSUPPORTED')):
        with pytest.raises(H.Mapped, match=code):
            H.economics('SPORTS_NBA_MONEYLINE', *gamma(market), book(market, NBA_TOKENS[0], ask='0.55', bid='0.50', tick='0.01', **change),
                        forecast, 0, NBA_TOKENS[0], market['conditionId'], NOW)
    rich = dict(market, orderMinSize=7)
    with pytest.raises(H.Mapped, match='VENUE_MINIMUM_OR_DEPTH_UNSUPPORTED'):
        H.economics('SPORTS_NBA_MONEYLINE', *gamma(rich), book(market, NBA_TOKENS[0], ask='0.55', bid='0.50', tick='0.01'),
                    forecast, 0, NBA_TOKENS[0], market['conditionId'], NOW)


# ------------------------------------------------------------------ R004

def test_candidate_classification_no_edge_and_restriction_distinctions():
    args = dict(p=D('0.9'), low=D('0.8'), rate=D(0), cap_rate=D(0), exponent=1, gamma_min=D('5'), book_min=D('5'))
    fit = H.small_order(D('0.50'), D('100'), fees_enabled=False, **args)
    assert fit['small_order_fit'] is True and D(fit['small_order_cost_usd']) == D('5') and D(fit['small_order_shares']) == 10
    assert fit['small_order_label'] == 'HYPOTHETICAL_RESEARCH_ONLY_FULL_FILL_ASSUMED_FILL_PROBABILITY_UNKNOWN'
    # Any positive fee pushes the largest 0.01-share order under the USD 5 Gamma minimum.
    fee = H.small_order(D('0.50'), D('100'), fees_enabled=True, **dict(args, rate=D('0.05'), cap_rate=D('0.05')))
    assert D(fee['small_order_cost_usd']) <= 5 and fee['small_order_reason'] == 'SMALL_ORDER_GAMMA_MIN_NOTIONAL_NOT_MET_WITHIN_CAP'
    assert H.small_order(D('0.50'), D('3'), fees_enabled=False, **args)['small_order_reason'] == 'SMALL_ORDER_DEPTH_BELOW_FLOOR'
    assert H.small_order(D('0.50'), D('100'), fees_enabled=False, **dict(args, book_min=D('12')))['small_order_reason'] == \
        'SMALL_ORDER_CLOB_MIN_SHARES_NOT_MET_WITHIN_CAP'
    assert H.small_order(D('0.50'), D('100'), fees_enabled=False, **dict(args, p=D('0.50')))['small_order_reason'] == \
        'SMALL_ORDER_MARGIN_NONPOSITIVE'
    # Fee-source disagreement: the larger documented fee is the cap fee.
    cap = H.small_order(D('0.50'), D('100'), fees_enabled=True, **dict(args, cap_rate=D('0.05')))
    assert D(cap['small_order_shares']) < 10
    rows = manifest_rows()
    candidates = [t for t in rows if t['research_class'] == 'RESEARCH_CANDIDATE']
    assert candidates and all(t['reason'] in (None, 'SMALL_ORDER_UNFIT', 'HERMES_CONTRARY_EVIDENCE', 'CAPACITY_NOT_SELECTED')
                              for t in candidates)
    assert all(t['research_class'] == 'NO_TRADE' for t in rows if t['reason'] == 'NO_POSITIVE_ESTIMATED_AFTER_COST_MARGIN')
    assert all(t['restriction_observed'] is True for t in rows if 'restriction_observed' in t)
    assert any(t['reason'] == 'SMALL_ORDER_UNFIT' and t['small_order_reason'] for t in candidates)


_ROWS = {}


def manifest_rows():
    if 'rows' not in _ROWS:
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            root, _, result = run(Path(tmp))
            assert result['status'] == 'COMPLETED', result
            _ROWS['rows'] = manifest(root)['tokens']
    return _ROWS['rows']


# ------------------------------------------------------------------ R005

def test_market_price_never_used_as_independent_probability():
    receipts = [{'url': S.venue.clob_book_url('1'), 'sha256': 'a' * 64}]
    for bad in ({'url': 'https://gamma-api.polymarket.com/markets/1', 'sha256': 'c' * 64},
                {'url': H.NWS + 'gridpoints/OKX/34,45', 'sha256': 'a' * 64}):
        with pytest.raises(H.Mapped, match='INDEPENDENCE_INVALID'):
            H.independence(bad, receipts, 'api.weather.gov')
    H.independence({'url': H.NWS + 'gridpoints/OKX/34,45', 'sha256': 'd' * 64}, receipts, 'api.weather.gov')


# ------------------------------------------------------------------ R006

WINDOW = (datetime(2026, 10, 28, 5, tzinfo=timezone.utc), datetime(2026, 10, 29, 5, tzinfo=timezone.utc))


@pytest.mark.parametrize('payload, cutoff, code', [
    (grid(update='2026-10-27T12:30:00+00:00'), NOW, 'LOOKAHEAD'),
    (grid(update='2026-10-27T03:00:00+00:00'), NOW, 'SOURCE_STALE'),
    (grid(update='2026-10-28T05:00:00+00:00'), S.ns('2026-10-28T06:00:00Z'), 'EVENT_OR_CLIMATE_DAY_STARTED_UNSUPPORTED'),
    (grid([{'validTime': '2026-10-28T06:00:00+00:00/PT6H', 'value': 1}]), NOW, 'SOURCE_COVERAGE_INCOMPLETE'),
    (grid(uom='wmoUnit:degC'), NOW, 'PROBABILITY_INVALID'),
    (grid([{'validTime': '2026-10-28T00:30:00+00:00/P2D', 'value': 1}]), NOW, 'SOURCE_COVERAGE_INCOMPLETE'),
    (grid([{'validTime': '2026-10-28T00:00:00+00:00/P2DT1M', 'value': 1}]), NOW, 'SOURCE_COVERAGE_INCOMPLETE'),
    (grid([{'validTime': '2026-10-28T00:00:00+00:00/P2D', 'value': 101}]), NOW, 'PROBABILITY_INVALID'),
])
def test_lookahead_stale_identity_protocol_and_rule_rejections(payload, cutoff, code):
    with pytest.raises(H.Mapped, match=code):
        H.rain_probability(payload, WINDOW, cutoff)
    day = date(2026, 10, 28)
    assert H.rain_rule(rain_market(), day)[1].station_id == 'KNYC'
    no_site = dict(rain_market(), resolutionSource='https://forecast.weather.gov/product.php?issuedby=NYC&product=CLI')
    assert H.rain_rule(no_site, day)[1].station_id == 'KNYC'
    for change in (dict(resolutionSource='https://forecast.weather.gov/product.php?site=NWS&product=CLI&issuedby=LGA'),
                   dict(description=RAIN_DESC.replace('2:00 PM ET', '11:59 PM ET')), dict(slug='rain-in-nyc'),
                   dict(outcomes='["No", "Yes"]')):
        with pytest.raises(H.Mapped, match='RULE_UNSUPPORTED'):
            H.rain_rule(dict(rain_market(), **change), day)
    with pytest.raises(H.Mapped, match='IDENTITY_MISMATCH'):
        H.rain_rule(rain_market(), date(2026, 10, 29))
    assert H.is_v2(nba_market()) is False and H.is_v2(rain_market()) is False
    assert H.is_v2(dict(rain_market(), positionIds=list(reversed(RAIN_TOKENS)))) is True
    assert H.is_v2(rain_market(), 'polyv2-where-will-it-rain-on-october-28-2026-new-york-ny') is True
    assert H.points_url('40.78333', '-73.96667') == H.NWS + 'points/40.7833,-73.9667'
    assert H.points_url('40.70000', '-74.00004') == H.NWS + 'points/40.7,-74'
    market = rain_market()
    for change, code in ((dict(asset_id=RAIN_TOKENS[0]), 'IDENTITY_MISMATCH'),
                         (dict(timestamp=str((NOW - 31_000_000_000) // 1_000_000)), 'BOOK_STALE'),
                         (dict(asks=[]), 'BOOK_INCOMPLETE'), (dict(tick_size='0.01'), 'TICK_MISMATCH')):
        bad = dict(book(market, RAIN_TOKENS[1]), **change)
        with pytest.raises(H.Mapped, match=code):
            H.economics('WEATHER_US_DAILY_RAIN', *gamma(market), bad, {'p': '0.01', 'stress_lower': '0', 'stress_upper': '0.06'},
                        1, RAIN_TOKENS[1], market['conditionId'], NOW)
    assert H.mapped(S.Stop('PREDICTION_NOT_PREGAME'), 'X') == 'EVENT_OR_CLIMATE_DAY_STARTED_UNSUPPORTED'
    assert H.mapped(H.NDFD.NdfdError('STATION_ID_MISMATCH'), 'X') == 'IDENTITY_MISMATCH'
    assert H.mapped(KeyError('x'), 'SOURCE_UNAVAILABLE') == 'SOURCE_UNAVAILABLE'
    with pytest.raises(S.Stop, match='UNMAPPED_NATIVE_CODE'):
        H.mapped(S.Stop('SOMETHING_NEW'), 'X')


# ------------------------------------------------------------------ R007

def row(category, market, token, margin, conservative='0', fit=True):
    return {'category': category, 'gamma_market_id': market, 'token_id': token, 'reason': None,
            'estimated_after_cost_margin': margin, 'notional': '1', 'conservative_margin': conservative,
            'small_order_fit': fit}


def test_funnel_denominators_and_deterministic_ranking():
    tokens = [row('B', '2', 't2', '0.1'), row('A', '9', 't9', '0.1'), row('A', '1', 't1', '0.1'), row('A', '1', 't0', '0.2')]
    provisional, final = H.assign(tokens, [])
    assert provisional == final == ['t0', 't1', 't9', 't2']
    with pytest.raises(S.Stop, match='RANKING_INPUT_INVALID'):
        H.assign([row('A', '1', 't1', 'NaN')], [])
    funnel = manifest_rows_funnel()
    assert funnel['observed'] == 2 and funnel['assessed_tokens'] == 4
    drops = sum(sum(funnel[name + '_drops'].values()) for name in
                ('venue_feasible', 'positive_estimated_margin', 'small_order_fit', 'not_contested', 'selected'))
    assert funnel['assessed_tokens'] - drops == funnel['selected']


def manifest_rows_funnel():
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        root, _, _ = run(Path(tmp))
        return manifest(root)['funnel']


# ------------------------------------------------------------------ R008

def draft_stdout(request_id, against):
    draft = {'schema_version': DRAFT_SCHEMA_VERSION, 'request_id': request_id,
             'research_summary': 'Balanced public evidence summary.', 'evidence_for': ['official forecast unchanged'],
             'evidence_against': against, 'uncertainties': ['timing'], 'known_missing_data': ['none'],
             'falsification_checks_performed': ['searched disconfirming sources'], 'limitations': ['public web only'],
             'what_would_change_the_conclusion': ['new forecast'], 'suggested_next_research_steps': ['recheck'],
             'source_references': [{'url': 'https://www.weather.gov/okx/', 'title': 'NWS OKX', 'source_class': 'official'}],
             'confidence_label': 'low'}
    draft.update({flag: True for flag in DRAFT_AUTHORITY_FLAGS})
    return json.dumps(draft).encode()


def usage(provider='example-provider', model='example-model'):
    return json.dumps({'input_tokens': 5, 'output_tokens': 8, 'total_tokens': 13, 'api_calls': 1,
                       'estimated_cost_usd': 0.01, 'cost_status': 'estimated', 'cost_source': 'official_docs_snapshot',
                       'model': model, 'provider': provider, 'session_id': 's1', 'completed': True, 'failed': False}).encode()


class ScriptedExternal(ExternalHermesCliBackend):
    """Test-only seam: an External-class backend with scripted outcomes, never a real process."""

    def __init__(self, stdout, usage_bytes):
        self.inner = FakeHermesBackend.from_transcript(stdout, usage_file_bytes=usage_bytes)

    def probe_version(self, **kw):
        return self.inner.probe_version(**kw)

    def probe_startup(self, **kw):
        return self.inner.probe_startup(**kw)

    def invoke(self, **kw):
        return self.inner.invoke(**kw)


BUDGET = {'provider_label': 'example-provider', 'model_label': 'example-model', 'max_runs_per_invocation': 1,
          'max_usd_per_run': D('0.50'), 'max_runs_per_7d': 20, 'max_usd_per_7d': D('5.00')}


def hermes(tmp_path, backend_for, rows):
    op = tmp_path / 'op-000001'
    op.mkdir(parents=True)
    token = rows['provisional_order'][0]
    target = next(t for t in rows['tokens'] if t['token_id'] == token)
    request = H.hermes_request(BUDGET, target)
    findings = H.hermes_stage(tmp_path, op, BUDGET, backend_for(request.request_id), '/opt/hermes', None, rows, clock())
    return H.influence(findings, rows['tokens'], NOW - 10, NOW + 10_000_000_000)


def test_hermes_research_origin_labels_and_no_probability_authority(tmp_path, offline):
    base = deepcopy(manifest_full())
    target = base['provisional_order'][0]
    before = {k: v for k, v in next(t for t in base['tokens'] if t['token_id'] == target).items()}
    fake = hermes(tmp_path / 'f', lambda rid: FakeHermesBackend.from_transcript(draft_stdout(rid, ['contrary report']),
                                                                                usage_file_bytes=usage()), deepcopy(base))
    assert fake[0]['origin'] == 'OFFLINE_FIXTURE_MODEL_ORIGIN_UNVERIFIED' and fake[0]['influence'] == 'NONE'
    contested = hermes(tmp_path / 'c', lambda rid: ScriptedExternal(draft_stdout(rid, ['contrary report']), usage()), deepcopy(base))
    assert contested[0]['origin'] == 'REAL_PROVIDER_REPORTED' and contested[0]['influence'] == 'CONTESTED'
    corroborated = hermes(tmp_path / 'k', lambda rid: ScriptedExternal(draft_stdout(rid, []), usage()), deepcopy(base))
    assert corroborated[0]['influence'] == 'CORROBORATED'
    tokens = deepcopy(base['tokens'])
    for t in tokens:
        t.pop('reason', None) if t.get('research_class') == 'RESEARCH_CANDIDATE' else None
        t.pop('selected_rank', None)
    H.assign(tokens, contested)
    hit = next(t for t in tokens if t['token_id'] == target)
    assert hit['research_tier'] == 2 and 'selected_rank' not in hit
    assert all(hit[k] == before[k] for k in ('p_estimate', 'estimated_after_cost_margin', 'payout_bounds', 'small_order_fit'))
    good = contested[0]
    expected = good['binding']
    for change, why in ((dict(binding=dict(expected, token_id='999')), 'BINDING_MISMATCH'),
                        (dict(end_utc='2026-10-26T00:00:00Z'), 'OUTSIDE_OPERATION_WINDOW'),
                        (dict(usable_source_count=0), 'NO_USABLE_SOURCE'),
                        (dict(state='RESEARCH_FAILED'), 'RUN_OR_REVALIDATION_FAILED'),
                        (dict(origin='OFFLINE_FIXTURE_MODEL_ORIGIN_UNVERIFIED'), 'ORIGIN_NOT_REAL_PROVIDER_REPORTED')):
        trow = next(t for t in base['tokens'] if t['token_id'] == target)
        assert H.judge(dict(good, **change), trow, NOW - 10, NOW + 10_000_000_000) == ('NONE', why)
    no_trade = next(t for t in base['tokens'] if t['research_class'] == 'NO_TRADE')
    tokens = deepcopy(base['tokens'])
    H.assign(tokens, [dict(good, token_id=no_trade['token_id'], influence='CORROBORATED')])
    assert next(t for t in tokens if t['token_id'] == no_trade['token_id'])['research_class'] == 'NO_TRADE'
    with pytest.raises(S.Stop, match='HERMES_BACKEND_UNSUPPORTED'):
        H.hermes_stage(tmp_path, tmp_path, BUDGET, object(), '/opt/hermes', None, deepcopy(base), clock())


_FULL = {}


def manifest_full():
    if 'm' not in _FULL:
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            root, _, _ = run(Path(tmp))
            _FULL['m'] = manifest(root)
    return _FULL['m']


# ------------------------------------------------------------------ R009

def test_research_budget_zero_default_caps_and_exhaustion(tmp_path, offline):
    root, registry = setup(tmp_path)
    with pytest.raises(S.Stop, match='HERMES_FLAGS_PARTIAL'):
        H.run(root, registry, {'rain'}, budget_path=str(tmp_path / 'b.json'), fetcher_type=replica(payloads()))
    budget = dict(provider_label='p', model_label='m', ledger_scratch_dir=str(root), max_runs_per_invocation=1,
                  max_usd_per_run=0.5, max_runs_per_7d=20, max_usd_per_7d=5)
    for change, code in ((dict(max_usd_per_run=0.51), 'BUDGET_CEILING_EXCEEDED'), (dict(max_runs_per_invocation=4), 'BUDGET_CEILING_EXCEEDED'),
                         (dict(ledger_scratch_dir=str(tmp_path)), 'BUDGET_LEDGER_MISMATCH'), (dict(extra=1), 'BUDGET_INVALID'),
                         (dict(max_runs_per_invocation=0), 'BUDGET_ZERO')):
        path = tmp_path / 'budget.json'
        path.write_text(json.dumps(dict(budget, **change)))
        with pytest.raises(S.Stop, match=code):
            H.load_budget(path, root)
    op = root / 'op-000001'
    op.mkdir()
    for n in range(20):  # crashed reservations: sentinel present, no finding
        S.put(op / f'hermes-{n:02d}.sentinel.json', {'started_ns': NOW - 1, 'reserved_usd': '0.25', 'request_id': 'r'})
    assert H.ledger(root, NOW) == (20, D('5.00'))
    m = deepcopy(manifest_full())
    findings = H.hermes_stage(root, op, BUDGET, FakeHermesBackend.from_transcript(b'{}', usage_file_bytes=usage()),
                              '/opt/hermes', None, m, clock())
    assert findings == [{'token_id': m['provisional_order'][0], 'state': 'HERMES_BUDGET_EXHAUSTED', 'influence': 'NONE'}]


# ------------------------------------------------------------------ R010

def test_restart_duplicate_and_cold_verify_immutability(tmp_path, offline):
    root, registry, first = run(tmp_path)
    second = H.run(root, registry, {'nba', 'rain'}, fetcher_type=replica(payloads()), clock_ns=clock())
    assert first['status'] == second['status'] == 'COMPLETED'
    assert second['alpha']['idempotent'] >= 2 and second['alpha']['inserted'] >= 2
    records = [e.record for e in AFR.load_and_verify_alpha_factory_registry(str(registry)).snapshot.entries]
    candidates = [r for r in records if isinstance(r, AF.OpportunityCandidate)]
    episodes = [r for r in records if isinstance(r, AF.ResearchEpisode)]
    assert len(candidates) == 2 and len(episodes) == 4
    assert sum(e.predecessor_episode_id is not None for e in episodes) == 2
    (root / 'op-000003').mkdir()
    S.put(root / 'op-000003' / 'started.json', {'schema': H.SCHEMA})
    assert H.verify(root)['operations'] == 2
    assert H.run(root, registry, {'rain'}, fetcher_type=replica(payloads()), clock_ns=clock())['status'] == 'COMPLETED'
    assert S.read(root / 'op-000003' / 'terminal.json') == {'status': 'INTERRUPTED_OR_UNKNOWN'}
    source = root / 'op-000001' / 'source-01.json'
    source.write_bytes(source.read_bytes() + b' ')
    with pytest.raises(S.Stop, match='VERIFY_INPUT_CHANGED'):
        H.verify(root)
    with S.operation_lock(root):
        with pytest.raises((S.Stop, PermissionError, OSError)):
            H.run(root, registry, {'rain'}, fetcher_type=replica(payloads()), clock_ns=clock())


# ------------------------------------------------------------------ R011

def test_alpha_factory_records_carry_no_economic_authority(tmp_path, offline):
    _, registry, _ = run(tmp_path)
    records = [e.record for e in AFR.load_and_verify_alpha_factory_registry(str(registry)).snapshot.entries]
    text = json.dumps([AF.record_to_mapping(r) for r in records])
    for word in ('estimated_after_cost_margin', 'expected_return', 'position_size', 'small_order', 'notional'):
        assert word not in text
    assert all(r.no_execution_authority and r.advisory_only for r in records)
    episode = next(r for r in records if isinstance(r, AF.ResearchEpisode))
    assert episode.producer_type == 'DETERMINISTIC_ANALYSIS' and episode.deterministic_evidence_refs
    bad = AF.build_hypothesis_family({'family_version': '1', 'family_name': 'x', 'mechanism_key': 'm',
                                      'mechanism_dimensions': {'expected_return': '1'}, 'falsifiable_theme': 't',
                                      'predecessor_family_id': None, 'creation_provenance': 'p', 'human_review_required': True})
    assert not bad.is_valid


# ------------------------------------------------------------------ R012

def test_zero_economic_authenticated_and_unallowlisted_calls(tmp_path, offline, monkeypatch):
    for url in ('https://clob.polymarket.com/order', 'https://api.weather.gov/points/40.78333,-73.96667',
                'https://evil.example/stations/KNYC', 'https://gamma-api.polymarket.com/events?slug=x',
                'https://api.weather.gov/alerts/active'):
        assert not H.url_ok(url)
    source = Path(H.__file__).read_text(encoding='utf-8')
    for forbidden in ('execution_gateway', 'live_pilot', 'os.environ', 'getenv', '.env', 'POST', 'private_key'):
        assert forbidden not in source
    root, _, result = run(tmp_path)
    assert result['status'] == 'COMPLETED'
    m = manifest(root)
    assert (m['order_attempts'], m['account_attempts'], m['wallet_attempts'], m['credential_reads']) == (0, 0, 0, 0)
    assert result['order_attempts'] == result['account_attempts'] == 0
