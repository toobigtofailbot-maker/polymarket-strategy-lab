"""Bounded multi-category research-candidate hunter (S10-HERMES-ALPHA-HUNTER-01), never orders.

One finite foreground invocation: NBA moneyline (merged ESPN method) and US daily rain (NWS
gridpoint PoP bounds) -> independent probability with uncertainty -> public venue checks ->
estimated after-cost margin -> hypothetical USD 2-5 small-order fit -> optional budgeted
controlled Hermes research that can only change a research tier -> deterministic ranking with an
exact funnel -> PIT/Alpha lineage. See docs/alpha_hunter_contract.md.

`run` is the only network command; `verify` re-derives every manifest cold with zero network and
zero dispatch. Research only: no StrategyVersion, Gate C permit, order, wallet or credential.
"""

from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta, timezone
from decimal import ROUND_CEILING, ROUND_FLOOR, ROUND_HALF_EVEN, Decimal
import json
from pathlib import Path
import re
import sys
import time
import urllib.parse
import urllib.request

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO)) if str(REPO) not in sys.path else None
from tools.alpha import run_shadow_alpha_cycle as S  # noqa: E402
from tools.alpha import run_s10_alpha_real_01 as R1  # noqa: E402
from src.data_layer import point_in_time_market_research as PIT  # noqa: E402
from src.data_layer.analytical_research import alpha_discovery as AD  # noqa: E402
from src.data_layer.analytical_research import alpha_factory as AF  # noqa: E402
from src.data_layer.analytical_research import alpha_factory_registry as AFR  # noqa: E402
from src.data_layer.analytical_research import nws_ndfd_history as NDFD  # noqa: E402
from src.data_layer.analytical_research import qualification_data_readiness as QDR  # noqa: E402
from src.execution_feasibility import evaluator as mechanics  # noqa: E402
from src.execution_feasibility import public_market as venue  # noqa: E402
from src.research_runtime.hermes_controlled_runtime import (  # noqa: E402
    ExternalHermesCliBackend, FakeHermesBackend, NON_AUTHORITY_NOTICE, REQUEST_SCHEMA_VERSION,
    build_research_run_request, run_controlled_hermes_research,
)

D = Decimal
Stop, need, canonical, digest = S.Stop, S.need, S.canonical, S.digest
WP_ID = 'S10-HERMES-ALPHA-HUNTER-01'
SCHEMA = 'alpha-hunter-v1'
METHOD_NBA, METHOD_RAIN = S.METHOD, 'nws-gridpoint-pop-climate-day-v1'
CATEGORIES = {'nba': 'SPORTS_NBA_MONEYLINE', 'rain': 'WEATHER_US_DAILY_RAIN'}
# Read 2026-10-27 from docs.polymarket.com/trading/fees; Gamma per-market feeSchedule stays primary.
DOCUMENTED_TAKER_RATE = {'SPORTS_NBA_MONEYLINE': '0.05', 'WEATHER_US_DAILY_RAIN': '0.05'}
SIZE_QUANTUM = D('0.01')  # size decimals 2 for every tick, as gate_c._SDK_ROUNDING_BY_TICK
CONFIG = {'schema': SCHEMA, 'wp': WP_ID, 'shares': '10', 'residual_cost_per_share': '0.005',
          'max_book_age_ns': 30_000_000_000, 'max_gets': 64, 'max_acquisition_seconds': 180,
          'nba_events': 8, 'rain_markets': 6, 'select_n': 10, 'small_order_floor_usd': '2.00',
          'small_order_cap_usd': '5.00', 'grid_max_age_ns': 6 * 3600 * 1_000_000_000,
          'documented_taker_rate': DOCUMENTED_TAKER_RATE, 'fee_docs_read': '2026-10-27'}
BUDGET_KEYS = {'provider_label', 'model_label', 'ledger_scratch_dir', 'max_runs_per_invocation',
               'max_usd_per_run', 'max_runs_per_7d', 'max_usd_per_7d'}
BUDGET_CEILINGS = {'max_runs_per_invocation': 3, 'max_usd_per_run': D('0.50'), 'max_runs_per_7d': 20,
                   'max_usd_per_7d': D('5.00')}
WEEK_NS = 7 * 24 * 3600 * 1_000_000_000
USER_AGENT = 'polymarket-strategy-lab/S10-HERMES-ALPHA-HUNTER-01 (public read-only research)'
SOURCE_PROVENANCE = WP_ID + ' hermes receipt '

M_REASONS = ('PROTOCOL_UNSUPPORTED', 'RULE_UNSUPPORTED', 'ACQUISITION_CAPACITY_EXCEEDED',
             'IDENTITY_MISMATCH', 'DUPLICATE_MARKET_CONFLICT', 'SOURCE_UNAVAILABLE', 'LOOKAHEAD',
             'SOURCE_STALE', 'EVENT_OR_CLIMATE_DAY_STARTED_UNSUPPORTED', 'SOURCE_COVERAGE_INCOMPLETE',
             'PROBABILITY_INVALID', 'INDEPENDENCE_INVALID', 'MARKET_UNAVAILABLE')
M_BUCKETS = {'eligible': M_REASONS[:3], 'source_supported': M_REASONS[3:9],
             'probability_assessed': M_REASONS[9:]}
T_REASONS = ('IDENTITY_MISMATCH', 'BOOK_STALE', 'BOOK_INCOMPLETE', 'TICK_MISMATCH', 'PRICE_OFF_TICK',
             'FEES_UNKNOWN', 'VENUE_MINIMUM_OR_DEPTH_UNSUPPORTED',
             'NO_POSITIVE_ESTIMATED_AFTER_COST_MARGIN', 'SMALL_ORDER_UNFIT', 'HERMES_CONTRARY_EVIDENCE',
             'CAPACITY_NOT_SELECTED')
SMALL_ORDER_REASONS = ('SMALL_ORDER_DEPTH_BELOW_FLOOR', 'SMALL_ORDER_GAMMA_MIN_NOTIONAL_NOT_MET_WITHIN_CAP',
                       'SMALL_ORDER_CLOB_MIN_SHARES_NOT_MET_WITHIN_CAP', 'SMALL_ORDER_MARGIN_NONPOSITIVE')
# Fixed mapping of reused native codes; anything else from a listed function is mapped by caller.
NATIVE = {'EVENT_NOT_UNIQUELY_MATCHED': 'IDENTITY_MISMATCH', 'SOURCE_TEAM_MISMATCH': 'IDENTITY_MISMATCH',
          'SOURCE_EVENT_INVALID': 'IDENTITY_MISMATCH', 'VENUE_IDENTITY_OR_SHAPE_INVALID': 'IDENTITY_MISMATCH',
          'PROBABILITY_UNAVAILABLE': 'SOURCE_UNAVAILABLE', 'SOURCE_UNAVAILABLE': 'SOURCE_UNAVAILABLE',
          'SOURCE_LOOKAHEAD': 'LOOKAHEAD', 'SOURCE_STALE': 'SOURCE_STALE', 'SOURCE_HTTP_STALE': 'SOURCE_STALE',
          'SOURCE_HTTP_CLOCK_UNKNOWN': 'SOURCE_STALE',
          'PREDICTION_NOT_PREGAME': 'EVENT_OR_CLIMATE_DAY_STARTED_UNSUPPORTED',
          'PROBABILITY_INVALID': 'PROBABILITY_INVALID', 'NUMBER_INVALID': 'PROBABILITY_INVALID',
          'CLOCK_INVALID': 'SOURCE_UNAVAILABLE', 'STATION_ID_MISMATCH': 'IDENTITY_MISMATCH',
          'STATION_METADATA_INVALID': 'SOURCE_UNAVAILABLE', 'STATION_OFFSET_UNDERIVABLE': 'SOURCE_UNAVAILABLE'}
NATIVE.update({code: code for code in M_REASONS + T_REASONS})

RAIN_EVENT = 'https://gamma-api.polymarket.com/events/slug/where-will-it-rain-on-'
NWS = 'https://api.weather.gov/'
_RAIN_EVENT_RE = re.compile(re.escape(RAIN_EVENT) + r'(?:' + '|'.join(QDR._MONTHS) + r')-[0-9]{1,2}-[0-9]{4}')
_NWS_RE = re.compile(re.escape(NWS) + r'(?:stations/K[A-Z0-9]{3}|points/-?[0-9]{1,3}(?:\.[0-9]{1,4})?,'
                     r'-?[0-9]{1,3}(?:\.[0-9]{1,4})?|gridpoints/[A-Z]{3}/[0-9]{1,3},[0-9]{1,3})')
_DURATION_RE = re.compile(r'P(?:([0-9]+)D)?(?:T(?:([0-9]+)H)?)?')


class Mapped(Exception):
    """A closed hunter reason (market or token level); never input-bearing."""


def fail(code):
    raise Mapped(code)


def mapped(error, default):
    """Map a reused native exception to the closed vocabulary (section 6.5)."""
    if isinstance(error, Mapped):
        return str(error)
    if isinstance(error, (Stop, NDFD.NdfdError)):
        code = str(error)
        need(code in NATIVE, 'UNMAPPED_NATIVE_CODE')
        return NATIVE[code]
    if isinstance(error, (KeyError, TypeError, ValueError, AttributeError, IndexError)):
        return default
    raise error


# ---------------------------------------------------------------- transport (run only)

def url_ok(url):
    return (S.url_ok(url) or _RAIN_EVENT_RE.fullmatch(url) is not None
            or _NWS_RE.fullmatch(url) is not None)


class Fetcher:
    """Bounded public GET journal; STARTED-first; no redirect; allowlisted templates only."""

    def __init__(self, operation, clock_ns=time.time_ns):
        self.operation, self.receipts, self.clock_ns = operation, [], clock_ns
        self.started = time.monotonic()

    def get(self, url):
        need(url_ok(url) and len(self.receipts) < CONFIG['max_gets']
             and time.monotonic() - self.started < CONFIG['max_acquisition_seconds'], 'NETWORK_BUDGET_OR_ENDPOINT')
        start = self.clock_ns()
        receipt = {'url': url, 'started_ns': start, 'state': 'UNAVAILABLE', 'http_date': None,
                   'sha256': None, 'raw_file': None}
        self.receipts.append(receipt)
        n = len(self.receipts)
        S.put(self.operation / f'request-{n:02d}.started.json', {'url': url, 'started_ns': start})
        try:
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), S.NoRedirect())
            request = urllib.request.Request(url, headers={'Accept': 'application/json', 'User-Agent': USER_AGENT})
            deadline = min(time.monotonic() + 20, self.started + CONFIG['max_acquisition_seconds'])
            with opener.open(request, timeout=20) as response:
                # Shadow bounded_body probes the raw socket, which live (Windows) is often already
                # gone (WinError 10038) and the failed probe empties the body; chunked read1 calls
                # with a monotonic deadline per chunk instead (each read also has the socket timeout).
                raw = bytearray()
                while True:
                    need(time.monotonic() <= deadline, 'NETWORK_DEADLINE')
                    chunk = response.read1(65536)
                    if not chunk:
                        break
                    raw.extend(chunk)
                    need(len(raw) <= S.MAX_BYTES, 'PUBLIC_BODY_LIMIT')
                raw = bytes(raw)
                need(response.status == 200 and not S.SECRET.search(raw), 'PUBLIC_BODY_INVALID')
                S.decode(raw)
                receipt['http_date'] = response.headers.get('Date')
                with (self.operation / f'source-{n:02d}.json').open('xb') as stream:
                    stream.write(raw)
                receipt.update(state='AVAILABLE', sha256=digest(raw), raw_file=f'source-{n:02d}.json')
        except Exception:
            receipt['state'] = 'UNAVAILABLE'
        receipt['received_ns'] = self.clock_ns()
        S.put(self.operation / f'receipt-{n:02d}.json', receipt)
        return data(self.operation, receipt)


def data(operation, receipt):
    if receipt is None or receipt['state'] != 'AVAILABLE':
        return None
    path = S.safe(operation / receipt['raw_file'])
    need(digest(path.read_bytes()) == receipt['sha256'], 'SOURCE_HASH_MISMATCH')
    return S.read(path)


# ---------------------------------------------------------------- pure helpers

def rain_event_url(day):
    month = ('january february march april may june july august september october november '
             'december').split()[day.month - 1]
    return f'{RAIN_EVENT}{month}-{day.day}-{day.year}'


def points_url(lat_text, lon_text):
    def four(text):
        value = D(str(text)).quantize(D('0.0001'), rounding=ROUND_HALF_EVEN)
        out = format(value, 'f').rstrip('0').rstrip('.')
        return '0' if out in ('-0', '') else out
    return f'{NWS}points/{four(lat_text)},{four(lon_text)}'


def is_v2(market, event_slug=''):
    # Live 2026-10-27: CTF markets may carry distinct positionIds; V2 lists them as the token ids.
    if str(market.get('slug', '')).startswith('polyv2-') or str(event_slug).startswith('polyv2-'):
        return True
    positions = market.get('positionIds')
    if positions in (None, [], '[]'):
        return False
    try:
        return {str(x) for x in S.array(positions)} == {str(x) for x in S.array(market.get('clobTokenIds'))}
    except Stop:
        return True


def rain_rule(market, event_day):
    """Merged parser + exact semantics + CLI resolution source; RULE_UNSUPPORTED otherwise."""
    try:
        parsed = QDR.parse_rain_slug(market.get('slug'))
        need(parsed is not None, 'RULE_UNSUPPORTED')
        semantics = QDR.parse_rule(market.get('description'))
    except (Stop, QDR.RuleExclusion, TypeError, ValueError, AttributeError):
        fail('RULE_UNSUPPORTED')
    if (semantics.finality_policy != 'LAST_BEFORE_1400_ET' or semantics.trace_qualifies is not False
            or semantics.threshold_inches != '0.01'):
        fail('RULE_UNSUPPORTED')
    source = urllib.parse.urlsplit(market.get('resolutionSource') or '')
    query = urllib.parse.parse_qs(source.query, keep_blank_values=True)
    if (source.scheme, source.netloc, source.path) != ('https', 'forecast.weather.gov', '/product.php') \
            or set(query) not in ({'product', 'issuedby'}, {'site', 'product', 'issuedby'}) \
            or any(len(v) != 1 for v in query.values()) or query['product'] != ['CLI'] \
            or query.get('site', ['NWS']) != ['NWS'] or query['issuedby'] != [semantics.station_id[1:]]:
        fail('RULE_UNSUPPORTED')
    try:
        outcomes, tokens = S.array(market.get('outcomes')), S.array(market.get('clobTokenIds'))
    except Stop:
        fail('RULE_UNSUPPORTED')
    if outcomes != ['Yes', 'No'] or len(tokens) != 2 or len(set(tokens)) != 2 \
            or not all(isinstance(t, str) and re.fullmatch(r'[0-9]{1,100}', t) for t in tokens):
        fail('RULE_UNSUPPORTED')
    if parsed[0] != event_day:
        fail('IDENTITY_MISMATCH')
    return parsed[0], semantics, tokens


def duration_hours(text):
    match = _DURATION_RE.fullmatch(text)
    if match is None or not any(match.groups()):
        fail('SOURCE_COVERAGE_INCOMPLETE')
    hours = int(match.group(1) or 0) * 24 + int(match.group(2) or 0)
    if not 0 < hours <= 31 * 24:  # bounded: a malformed huge duration is a coverage defect, not fatal
        fail('SOURCE_COVERAGE_INCOMPLETE')
    return hours


def rain_probability(grid, window, source_cutoff):
    """NWS PoP intervals -> Decimal bounds over the climate-day window (section 6.2)."""
    props = grid.get('properties') if isinstance(grid, dict) else None
    if not isinstance(props, dict):
        fail('SOURCE_UNAVAILABLE')
    try:
        updated = S.ns(props.get('updateTime'))
    except Stop:
        fail('SOURCE_UNAVAILABLE')
    if updated > source_cutoff:
        fail('LOOKAHEAD')
    if source_cutoff - updated > CONFIG['grid_max_age_ns']:
        fail('SOURCE_STALE')
    start, end = window
    if source_cutoff >= int(start.timestamp()) * 1_000_000_000:
        fail('EVENT_OR_CLIMATE_DAY_STARTED_UNSUPPORTED')
    pop = props.get('probabilityOfPrecipitation')
    values = pop.get('values') if isinstance(pop, dict) else None
    if not isinstance(values, list) or start.minute or start.second or end.minute or end.second:
        fail('SOURCE_COVERAGE_INCOMPLETE')
    intervals = []
    for item in values:  # structure and coverage first; unit and values after (closed order)
        if not isinstance(item, dict) or not isinstance(item.get('validTime'), str) or '/' not in item['validTime']:
            fail('SOURCE_COVERAGE_INCOMPLETE')
        begin_text, span = item['validTime'].split('/', 1)
        try:
            begin = datetime.fromisoformat(begin_text)
        except ValueError:
            fail('SOURCE_COVERAGE_INCOMPLETE')
        if begin.tzinfo is None:
            fail('SOURCE_COVERAGE_INCOMPLETE')
        hours = duration_hours(span)
        finish = begin + timedelta(hours=hours)
        if finish <= start or begin >= end:
            continue
        if begin.minute or begin.second or begin.microsecond:
            fail('SOURCE_COVERAGE_INCOMPLETE')
        overlap = D(int((min(finish, end) - max(begin, start)).total_seconds())) / 3600
        intervals.append((begin, finish, item.get('value'), overlap.to_integral_value(rounding=ROUND_CEILING), D(hours)))
    intervals.sort(key=lambda x: (x[0], x[1]))
    cursor = start
    for begin, finish, *_ in intervals:
        if begin > cursor:
            fail('SOURCE_COVERAGE_INCOMPLETE')
        cursor = max(cursor, finish)
    if not intervals or cursor < end:
        fail('SOURCE_COVERAGE_INCOMPLETE')
    if pop.get('uom') != 'wmoUnit:percent' or any(type(v) is not int or not 0 <= v <= 100 for _, _, v, _, _ in intervals):
        fail('PROBABILITY_INVALID')
    intervals = [(b, f, D(v) / 100, h, d) for b, f, v, h, d in intervals]
    lower = max((p for b, f, p, _, _ in intervals if b >= start and f <= end), default=D(0))
    upper = min(D(1), sum(p * h for _, _, p, h, _ in intervals))
    survive = D(1)
    for _, _, p, h, d in intervals:
        survive *= 1 - p * h / d
    point = min(max(1 - survive, lower), upper)
    return {'method': METHOD_RAIN, 'p': str(point), 'stress_lower': str(lower), 'stress_upper': str(upper),
            'uncertainty_kind': 'BOUNDS_OVER_POP_INTERVALS',
            'interval_semantics': 'RUN_LENGTH_VALUE_ASSUMED_INTERVAL_POP',
            'point_assumption': 'INTERVAL_INDEPENDENCE_AND_UNIFORM_WITHIN_INTERVAL',
            'spatial_assumption': 'GRID_CELL_EQUALS_STATION',
            'resolution_risk': 'CLI_PUBLICATION_DEADLINE_UNMODELLED',
            'accumulation_risk': 'SUB_THRESHOLD_INTERVAL_SUMS_UNMODELLED', 'calibration': 'UNPROVEN',
            'grid_update_ns': updated, 'interval_count': len(intervals)}


def taker_fee(price, shares, rate, exponent):
    return mechanics._taker_fee([(price, shares)], D(rate), exponent).quantize(D('0.00001'), rounding=ROUND_CEILING)


def gamma_state(gamma_doc, market_id, condition_id, token_id):
    try:
        facts, diagnostics = venue.normalize_gamma_market(gamma_doc, gamma_market_id=market_id,
                                                          condition_id=condition_id, token_id=token_id)
    except Exception:
        fail('IDENTITY_MISMATCH')
    if not all(facts[x] is True for x in ('active', 'accepting_orders', 'enable_order_book')) or facts['closed'] is not False:
        fail('MARKET_UNAVAILABLE')
    return facts, diagnostics


def economics(category, gamma, diagnostics, book_doc, forecast, index, token, condition_id, evaluated_ns):
    """Generalized shadow economics (numeric parity) plus small-order fit; Mapped on failure."""
    try:
        facts = venue.normalize_clob_book(book_doc, condition_id=condition_id, token_id=token)
    except Exception:
        fail('IDENTITY_MISMATCH')
    if gamma['gamma_neg_risk'] != facts['book_neg_risk']:
        fail('IDENTITY_MISMATCH')
    if not 0 <= evaluated_ns - facts['book_timestamp_ns'] <= CONFIG['max_book_age_ns']:
        fail('BOOK_STALE')
    bids, asks = facts['bids'], facts['asks']
    if not (bids and asks):
        fail('BOOK_INCOMPLETE')
    tick = D(facts['book_tick_size'])
    if gamma['gamma_tick_size'] is None or tick != D(gamma['gamma_tick_size']):
        fail('TICK_MISMATCH')
    if any(D(price) % tick for price, _ in (*asks, *bids)):
        fail('PRICE_OFF_TICK')
    if gamma['fees_enabled'] is None or diagnostics:
        fail('FEES_UNKNOWN')
    exponent, rate = 0, D(0)
    if gamma['fees_enabled']:
        if gamma['fee_taker_only'] is not True or gamma['fee_rate'] is None or gamma['fee_exponent'] is None:
            fail('FEES_UNKNOWN')
        exp = D(gamma['fee_exponent'])
        if exp != exp.to_integral_value() or not 0 <= exp <= 8:
            fail('FEES_UNKNOWN')
        exponent, rate = int(exp), D(gamma['fee_rate'])
    doc_rate = D(DOCUMENTED_TAKER_RATE[category])
    disagreement = bool(gamma['fees_enabled']) and rate != doc_rate
    gamma_min, book_min = gamma['gamma_min_order_notional_usd'], facts['book_min_order_size_raw']
    if gamma_min is None or book_min is None:
        fail('VENUE_MINIMUM_OR_DEPTH_UNSUPPORTED')
    ask, depth = D(asks[0][0]), D(asks[0][1])
    shares = D(CONFIG['shares'])
    fills, _, _ = mechanics._sweep(asks, lambda price: price <= ask, shares)
    filled = sum((q for _, q in fills), D(0))
    notional = sum((price * q for price, q in fills), D(0))
    if filled != shares or shares < D(book_min) or notional < D(gamma_min):
        fail('VENUE_MINIMUM_OR_DEPTH_UNSUPPORTED')
    p = D(forecast['p']) if index == 0 else 1 - D(forecast['p'])
    low = D(forecast['stress_lower']) if index == 0 else 1 - D(forecast['stress_upper'])
    high = D(forecast['stress_upper']) if index == 0 else 1 - D(forecast['stress_lower'])
    if category == 'SPORTS_NBA_MONEYLINE':  # cancellation resolves 50-50: keep 0.5 in the hull
        low, high = min(low, D('.5')), max(high, D('.5'))
    fee = taker_fee(ask, shares, rate, exponent) if gamma['fees_enabled'] else D(0)
    cap_fee = max(fee, taker_fee(ask, shares, doc_rate, exponent)) if disagreement else fee
    residual = shares * D(CONFIG['residual_cost_per_share'])
    margin = shares * p - notional - fee - residual
    row = {'category': category, 'token_id': token, 'outcome_index': index, 'p_estimate': str(p),
           'payout_bounds': [str(low), str(high)], 'p_market_mid': str((D(bids[0][0]) + ask) / 2),
           'bid': bids[0][0], 'ask': str(ask), 'shares': str(shares), 'notional': str(notional), 'fee': str(fee),
           'fee_rate_source': 'GAMMA_MARKET_FEE_SCHEDULE', 'fee_rate_source_disagreement': disagreement,
           'residual_cost': str(residual), 'estimated_after_cost_margin': str(margin),
           'conservative_margin': str(shares * low - notional - cap_fee - residual),
           'optimistic_margin': str(shares * high - notional - fee - residual),
           'fill_probability': None, 'fill_probability_state': 'UNMEASURED',
           'restriction_observed': gamma['restricted'], 'gamma_min_order_notional_usd': gamma_min,
           'clob_min_order_shares': book_min}
    if margin <= 0:
        row['reason'] = 'NO_POSITIVE_ESTIMATED_AFTER_COST_MARGIN'
        return row
    row.update(small_order(ask, depth, p, low, rate, doc_rate if disagreement else rate, exponent,
                           bool(gamma['fees_enabled']), D(gamma_min), D(book_min)))
    return row


def small_order(ask, depth, p, low, rate, cap_rate, exponent, fees_enabled, gamma_min, book_min):
    """Largest 0.01-share order within the best-ask level whose cap-fee cost is <= USD 5.00."""
    floor, cap = D(CONFIG['small_order_floor_usd']), D(CONFIG['small_order_cap_usd'])
    residual = D(CONFIG['residual_cost_per_share'])

    def fee_at(q, r):
        return taker_fee(ask, q, r, exponent) if fees_enabled else D(0)

    def cost(q):
        return ask * q + max(fee_at(q, rate), fee_at(q, cap_rate))

    upper = min(depth, (cap / ask).quantize(SIZE_QUANTUM, rounding=ROUND_FLOOR))
    lo, hi = 0, int(upper / SIZE_QUANTUM)
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if cost(SIZE_QUANTUM * mid) <= cap:
            lo = mid
        else:
            hi = mid - 1
    q = SIZE_QUANTUM * lo
    out = {'small_order_label': 'HYPOTHETICAL_RESEARCH_ONLY_FULL_FILL_ASSUMED_FILL_PROBABILITY_UNKNOWN',
           'small_order_shares': str(q), 'small_order_cost_usd': str(cost(q)) if lo else None,
           'small_order_estimated_margin': None, 'small_order_conservative_margin': None}
    if lo == 0 or cost(q) < floor:
        reason = SMALL_ORDER_REASONS[0]
    elif ask * q < gamma_min:
        reason = SMALL_ORDER_REASONS[1]
    elif q < book_min:
        reason = SMALL_ORDER_REASONS[2]
    else:
        estimated = q * p - ask * q - fee_at(q, rate) - residual * q
        out.update(small_order_estimated_margin=str(estimated),
                   small_order_conservative_margin=str(q * low - cost(q) - residual * q))
        reason = None if estimated > 0 else SMALL_ORDER_REASONS[3]
    out.update(small_order_fit=reason is None, small_order_reason=reason)
    return out


# ---------------------------------------------------------------- analysis (pure over stored inputs)

def by_url(receipts):
    found = {}
    for receipt in receipts:
        found.setdefault(receipt['url'], receipt)
    return found


def market_row(category, market, **extra):
    return dict({'category': category, 'gamma_market_id': str(market.get('id')),
                 'condition_id': market.get('conditionId'), 'reason': None}, **extra)


def analyze_nba(op, receipts, clocks):
    urls, cutoff = by_url(receipts), clocks['source_cutoff_ns']
    markets = data(op, urls.get(S.DISCOVERY_URL)) or []
    if not isinstance(markets, list):
        markets = []
    seen = {}
    for receipt in receipts:
        if receipt['url'].startswith(S.ESPN + 'scoreboard?'):
            board = data(op, receipt)
            for event in (board or {}).get('events', []):
                seen.setdefault(event.get('id'), event)
    events = list(seen.values())
    rows, matched = [], set()
    for _, mid, market, conflict in unique_markets((None, m) for m in markets):
        row = market_row('SPORTS_NBA_MONEYLINE', market, rule_sha256=None, forecast=None, tokens=None)
        rows.append(row)
        try:
            if is_v2(market):
                fail('PROTOCOL_UNSUPPORTED')
            try:
                outcomes, tokens, start = S.rule(market)
            except Exception:
                fail('RULE_UNSUPPORTED')
            if conflict:
                fail('DUPLICATE_MARKET_CONFLICT')
            event_id = S.matched_event(market, events)
            if event_id in matched:
                fail('DUPLICATE_MARKET_CONFLICT')
            if start <= clocks['started_ns']:
                fail('EVENT_OR_CLIMATE_DAY_STARTED_UNSUPPORTED')
            if len(matched) >= CONFIG['nba_events']:
                fail('ACQUISITION_CAPACITY_EXCEEDED')
            matched.add(event_id)
            row.update(rule_sha256=digest(market['description'].encode()), tokens=tokens, event_id=event_id)
            receipt = urls.get(S.ESPN + 'summary?event=' + event_id)
            summary = data(op, receipt)
            if summary is None:
                fail('SOURCE_UNAVAILABLE')
            if summary.get('header', {}).get('id') != event_id:
                fail('IDENTITY_MISMATCH')
            forecast = S.probability(market, summary, receipt, cutoff)
            independence(receipt, receipts, 'site.api.espn.com')
            row['forecast'] = forecast
            row['gamma'] = gamma_state(market, mid, market['conditionId'], tokens[0])
        except Exception as error:
            row['reason'] = mapped(error, 'SOURCE_UNAVAILABLE')
    return rows


def independence(source_receipt, receipts, host):
    venue_hashes = {r['sha256'] for r in receipts if r['url'].startswith('https://clob.polymarket.com/')
                    or r['url'].startswith('https://gamma-api.polymarket.com/')}
    if urllib.parse.urlsplit(source_receipt['url']).netloc != host or source_receipt['sha256'] in venue_hashes:
        fail('INDEPENDENCE_INVALID')


def station_doc(document):
    """parse_nws_station needs numeric coordinates; shared decode keeps floats as text."""
    geometry = dict(document.get('geometry') or {})
    geometry['coordinates'] = [float(x) for x in geometry.get('coordinates') or ()]
    return dict(document, geometry=geometry)


def analyze_rain(op, receipts, clocks):
    urls, cutoff = by_url(receipts), clocks['source_cutoff_ns']
    rows, taken = [], 0
    for (day, slug), mid, market, conflict in rain_candidates(op, urls, clocks):
        row = market_row('WEATHER_US_DAILY_RAIN', market, rule_sha256=None, forecast=None, tokens=None)
        rows.append(row)
        try:
            if is_v2(market, slug):
                fail('PROTOCOL_UNSUPPORTED')
            target, semantics, tokens = rain_rule(market, day)
            if conflict:
                fail('DUPLICATE_MARKET_CONFLICT')
            if taken >= CONFIG['rain_markets']:
                fail('ACQUISITION_CAPACITY_EXCEEDED')
            taken += 1
            row.update(rule_sha256=semantics.rule_text_sha256, tokens=tokens, station=semantics.station_id,
                       target_day=target.isoformat())
            station_receipt = urls.get(f'{NWS}stations/{semantics.station_id}')
            station = data(op, station_receipt)
            if station is None:
                fail('SOURCE_UNAVAILABLE')
            S.fresh_source(station_receipt, cutoff)
            meta = NDFD.parse_nws_station(station_doc(station), semantics.station_id)
            lat, lon = station['geometry']['coordinates'][1], station['geometry']['coordinates'][0]
            points_receipt = urls.get(points_url(lat, lon))
            points = data(op, points_receipt)
            if points is None:
                fail('SOURCE_UNAVAILABLE')
            S.fresh_source(points_receipt, cutoff)
            grid_url = points['properties']['forecastGridData']
            if _NWS_RE.fullmatch(grid_url or '') is None or '/gridpoints/' not in grid_url:
                fail('SOURCE_UNAVAILABLE')
            grid_receipt = urls.get(grid_url)
            grid = data(op, grid_receipt)
            if grid is None:
                fail('SOURCE_UNAVAILABLE')
            S.fresh_source(grid_receipt, cutoff)
            window = NDFD.climate_day_window(target, NDFD.standard_utc_offset_minutes(meta.time_zone, target))
            forecast = rain_probability(grid, window, cutoff)
            independence(grid_receipt, receipts, 'api.weather.gov')
            forecast.update(source_sha256=grid_receipt['sha256'], available_ns=grid_receipt['received_ns'])
            row['forecast'] = forecast
            row['gamma'] = gamma_state(market, mid, market.get('conditionId'), tokens[0])
        except Exception as error:
            row['reason'] = mapped(error, 'SOURCE_UNAVAILABLE')
    return rows


def token_rows(op, receipts, clocks, markets):
    urls, rows = by_url(receipts), []
    for market in markets:
        if market['reason'] is not None:
            continue
        gamma, diagnostics = market.pop('gamma')
        for index, token in enumerate(market['tokens']):
            base = {'category': market['category'], 'gamma_market_id': market['gamma_market_id'],
                    'condition_id': market['condition_id'], 'token_id': token, 'outcome_index': index}
            try:
                book = data(op, urls.get(venue.clob_book_url(token)))
                if book is None:
                    fail('BOOK_INCOMPLETE')
                row = economics(market['category'], gamma, diagnostics, book, market['forecast'], index,
                                token, market['condition_id'], clocks['evaluated_ns'])
                rows.append(dict(base, **row))
            except Exception as error:
                rows.append(dict(base, reason=mapped(error, 'IDENTITY_MISMATCH')))
    return rows


def rank_key(row):
    ratio = D(row['estimated_after_cost_margin']) / D(row['notional'])
    values = (ratio, D(row['conservative_margin']))
    need(all(v.is_finite() for v in values), 'RANKING_INPUT_INVALID')
    return (-values[0], -values[1], row['category'], row['gamma_market_id'], row['token_id'])


def assign(tokens, findings):
    """Final tiers, selection and the single non-selection reason on research candidates."""
    candidates = [t for t in tokens if t.get('reason') is None]
    try:
        provisional = sorted(candidates, key=rank_key)
    except (ArithmeticError, KeyError, TypeError):
        raise Stop('RANKING_INPUT_INVALID') from None
    influence = {f['token_id']: f for f in findings if f.get('influence') in ('CORROBORATED', 'CONTESTED')}
    for row in candidates:
        row['research_class'] = 'RESEARCH_CANDIDATE'
        found = influence.get(row['token_id'])
        row['research_tier'] = 1 if found is None else 0 if found['influence'] == 'CORROBORATED' else 2
    final = sorted(candidates, key=lambda r: (r['research_tier'], *rank_key(r)))
    selected = 0
    for row in final:
        if not row['small_order_fit']:
            row['reason'] = 'SMALL_ORDER_UNFIT'
        elif row['research_tier'] == 2:
            row['reason'] = 'HERMES_CONTRARY_EVIDENCE'
        elif selected >= CONFIG['select_n']:
            row['reason'] = 'CAPACITY_NOT_SELECTED'
        else:
            selected += 1
            row['selected_rank'] = selected
    for row in tokens:
        row.setdefault('research_class', 'NO_TRADE')
    return [r['token_id'] for r in provisional], [r['token_id'] for r in final]


def funnel(markets, tokens):
    def count(rows, codes):
        return {code: sum(r['reason'] == code for r in rows) for code in codes}
    out = {'observed': len(markets)}
    level = len(markets)
    for name, codes in M_BUCKETS.items():
        drop = count(markets, codes)
        level -= sum(drop.values())
        out[name], out[name + '_drops'] = level, drop
    out['assessed_tokens'] = 2 * level
    need(len(tokens) == out['assessed_tokens'], 'FUNNEL_INVALID')
    stages = (('venue_feasible', T_REASONS[:7]), ('positive_estimated_margin', T_REASONS[7:8]),
              ('small_order_fit', T_REASONS[8:9]), ('not_contested', T_REASONS[9:10]),
              ('selected', T_REASONS[10:]))
    level = len(tokens)
    for name, codes in stages:
        drop = count(tokens, codes)
        level -= sum(drop.values())
        out[name], out[name + '_drops'] = level, drop
    need(level == sum('selected_rank' in t for t in tokens), 'FUNNEL_INVALID')
    return out


def pit_discovery(op, markets, observed_ns, *, create):
    """Record observed markets in a per-operation PIT store and the native discovery queue."""
    path = op / 'pit.sqlite3'
    cutoff = S.iso(observed_ns)
    if create:
        need(PIT.initialize_point_in_time_record_store(path).is_valid, 'NATIVE_PIT_INVALID')
        records = []
        # Conflicting copies stay out of PIT (their rows already carry DUPLICATE_MARKET_CONFLICT).
        for category, mid, market, conflict in unique_markets(markets):
            if conflict or not re.fullmatch(r'[0-9]{1,32}', mid):
                continue
            try:
                outcomes, tokens = S.array(market.get('outcomes')), S.array(market.get('clobTokenIds'))
            except Stop:
                continue
            payload = {'question_text': market.get('question'), 'market_status': 'closed' if market.get('closed') else 'open',
                       'outcome_labels': outcomes, 'token_ids': ['token:polymarket:' + t for t in tokens],
                       'condition_id': market.get('conditionId'), 'category': category,
                       'resolution_date': market.get('endDate')}
            built = PIT.build_market_observation(dict(
                schema_id='point-in-time-market-research-record', schema_version='1.0.0',
                record_family='MARKET_OBSERVATION', snapshot_id='snapshot:' + digest(canonical(market)),
                ingestion_batch_id='batch:' + digest(canonical([m for _, m in markets])), event_time=None,
                observed_time=cutoff, ingestion_time=cutoff, lifecycle_state='NORMALIZED_ACCEPTED',
                classification='PRIMARY_ASSERTION', lineage_parent_ids=[], supersedes_record_version_id=None,
                normalizer_version=SCHEMA, validator_version='pit-native', parameter_set_id=SCHEMA,
                human_review_required=False, canonical_payload=payload, observation_kind='MARKET_METADATA',
                platform_id='platform:polymarket', event_id='event:polymarket:' + mid,
                market_id='market:polymarket:' + mid, token_id=None, source_id='source:polymarket:gamma-markets',
                source_assertion_id='assertion:' + mid, source_snapshot_id='source:' + digest(canonical(market))))
            if built.is_valid:
                records.append(built.record)
        if records:
            need(PIT.append_point_in_time_records(path, records).is_valid, 'NATIVE_PIT_APPEND_INVALID')
    else:
        need(PIT.load_and_verify_point_in_time_record_store(path).is_valid, 'NATIVE_PIT_INVALID')
    policy = S.policy()
    universe = AD.build_alpha_universe_snapshot(path, policy, cutoff)
    need(universe.is_valid, 'NATIVE_UNIVERSE_INVALID')
    bases = AD.build_pre_allocation_triage_bases(universe.record, policy, analysis_temporal_mode='HISTORICAL_REPLAY',
                                                 alpha_memory_temporal_posture='HISTORICAL_AVAILABILITY_UNPROVEN')
    need(bases.is_valid, 'NATIVE_TRIAGE_INVALID')
    final = AD.allocate_and_finalize_research_queue(universe.record, policy, bases.records)
    need(final.is_valid, 'NATIVE_QUEUE_INVALID')
    queue = AD.alpha_discovery_record_to_mapping(final.record)
    return {'universe_id': universe.record.alpha_universe_snapshot_id,
            'queue_id': queue['alpha_research_queue_snapshot_id'], 'gating': 'RECORDED_NOT_GATING'}


def observed_markets(op, receipts, clocks):
    urls, out = by_url(receipts), []
    for market in data(op, urls.get(S.DISCOVERY_URL)) or []:
        out.append(('SPORTS_NBA_MONEYLINE', market))
    anchor = date.fromisoformat(clocks['anchor_utc_date'])
    for offset in (1, 2):
        event = data(op, urls.get(rain_event_url(anchor + timedelta(days=offset))))
        if isinstance(event, dict):
            out.extend(('WEATHER_US_DAILY_RAIN', m) for m in event.get('markets', []))
    return out


def analyze(op, receipts, clocks, findings, categories, *, create=False):
    """Pure re-derivable analysis over stored receipts, clocks and Hermes findings."""
    markets = []
    if 'nba' in categories:
        markets += analyze_nba(op, receipts, clocks)
    if 'rain' in categories:
        markets += analyze_rain(op, receipts, clocks)
    tokens = token_rows(op, receipts, clocks, markets)
    provisional, final = assign(tokens, findings)
    discovery = pit_discovery(op, observed_markets(op, receipts, clocks), clocks['source_cutoff_ns'], create=create)
    influenced = [f for f in findings if f.get('influence') in ('CORROBORATED', 'CONTESTED')]
    real = [f for f in influenced if f.get('origin') == 'REAL_PROVIDER_REPORTED']
    return {'schema': SCHEMA, 'wp': WP_ID, 'categories': sorted(categories), 'clocks': clocks,
            'markets': markets, 'tokens': tokens, 'provisional_order': provisional, 'final_order': final,
            'funnel': funnel(markets, tokens), 'discovery': discovery, 'hermes_findings': findings,
            'run_mode': 'PUBLIC_SCREENER_NO_HERMES' if not findings else
                        'HERMES_INFLUENCED' if influenced else 'HERMES_ATTEMPTED_NO_INFLUENCE',
            'hermes_alpha_hunter_milestone': 'SATISFIED_REAL_PROVIDER_INFLUENCE' if real
                                             else 'UNSATISFIED_REAL_INFERENCE_NOT_DEMONSTRATED',
            'sizing_note': 'SIZING_DEFERRED_TO_WP2', 'calibration': 'UNPROVEN',
            'network_attempts': len(receipts), 'account_attempts': 0, 'order_attempts': 0,
            'wallet_attempts': 0, 'credential_reads': 0}


# ---------------------------------------------------------------- Hermes stage

def load_budget(path, scratch):
    if path is None:
        return None
    budget_file = S.safe(Path(path))
    need(budget_file.is_absolute() and budget_file.is_file(), 'BUDGET_INVALID')
    try:
        value = json.loads(budget_file.read_bytes(), parse_float=D, object_pairs_hook=S.venue._no_duplicates)
    except Exception:
        raise Stop('BUDGET_INVALID') from None
    need(isinstance(value, dict) and set(value) == BUDGET_KEYS, 'BUDGET_INVALID')
    need(all(isinstance(value[k], str) and value[k] for k in ('provider_label', 'model_label', 'ledger_scratch_dir')),
         'BUDGET_INVALID')
    need(Path(value['ledger_scratch_dir']) == Path(scratch), 'BUDGET_LEDGER_MISMATCH')
    for key, ceiling in BUDGET_CEILINGS.items():
        number = value[key]
        kinds = (int,) if key.startswith('max_runs') else (int, D)
        need(not isinstance(number, bool) and isinstance(number, kinds) and 0 <= D(str(number)) <= ceiling,
             'BUDGET_CEILING_EXCEEDED')
    need(value['max_runs_per_invocation'] > 0 and D(str(value['max_usd_per_run'])) > 0, 'BUDGET_ZERO')
    return value


def ledger(root, now_ns):
    runs, spent = 0, D(0)
    for sentinel in sorted(root.glob('op-*/hermes-*.sentinel.json')):
        value = S.read(sentinel)
        if now_ns - value['started_ns'] <= WEEK_NS:
            runs, spent = runs + 1, spent + D(value['reserved_usd'])
    return runs, spent


def hermes_request(budget, token_row):
    category = token_row['category']
    context = (f"Public Polymarket {category} binary market {token_row['gamma_market_id']}; outcome index "
               f"{token_row['outcome_index']}. Independent estimate {token_row['p_estimate']} with bounds "
               f"{token_row['payout_bounds'][0]}-{token_row['payout_bounds'][1]}; market mid {token_row['p_market_mid']}.")
    return build_research_run_request({
        'schema_version': REQUEST_SCHEMA_VERSION,
        'research_question': 'What public evidence contradicts or supports the independent probability for this outcome?',
        'research_objective': 'Falsification-oriented public research; report contrary evidence and missing data.',
        'research_category': 'event_outcome', 'public_market_context': context,
        'allowed_research_scope': ['public_web', 'public_news', 'public_reference'],
        'required_source_types': ['official', 'news'], 'max_sources': 5,
        'provider_label': budget['provider_label'], 'model_label': budget['model_label'],
        'max_wall_seconds': 300, 'max_output_bytes': 65536,
        'max_accepted_estimated_cost_usd': str(budget['max_usd_per_run']),
        'human_review_required': True, 'non_authority_notice': NON_AUTHORITY_NOTICE})


def map_hermes_sources(projection, receipt_id, end_utc):
    """ALPHA-REAL-01 `map_sources` semantics with this WP's provenance prefix."""
    usable, seen = [], set()
    for item in projection['source_references']:
        key = (item['url'], item['title'], item['source_class'])
        if key in seen or R1.SOURCE_CLASS_MAP.get(item['source_class']) is None:
            continue
        seen.add(key)
        built = AF.build_research_source_reference({
            'source_kind': 'PUBLIC_HTTPS', 'source_class': R1.SOURCE_CLASS_MAP[item['source_class']],
            'source_locator': item['url'], 'title': item['title'], 'observed_at': end_utc,
            'content_sha256': None, 'provenance': SOURCE_PROVENANCE + receipt_id})
        if built.is_valid:
            usable.append(built.record)
    return usable


def origin_of(backend, receipt, request):
    # isinstance (not type): CaptureBackend wraps the real backend, which is what is classified.
    if isinstance(backend, ExternalHermesCliBackend):
        verified = (receipt.verified_provider, receipt.verified_model) == (request.provider_label, request.model_label)
        return 'REAL_PROVIDER_REPORTED' if verified else 'REAL_TRANSPORT_MODEL_UNVERIFIED'
    if isinstance(backend, FakeHermesBackend):
        return 'OFFLINE_FIXTURE_MODEL_ORIGIN_UNVERIFIED'
    raise Stop('HERMES_BACKEND_UNSUPPORTED')


def judge(finding, token_row, started_ns, evaluated_ns):
    """Deterministic influence gate (section 6.7); returns influence and its reason."""
    binding = finding.get('binding') or {}
    expected = {k: token_row[k] for k in ('category', 'gamma_market_id', 'condition_id', 'token_id')}
    if finding.get('origin') != 'REAL_PROVIDER_REPORTED':
        return 'NONE', 'ORIGIN_NOT_REAL_PROVIDER_REPORTED'
    if finding.get('state') != 'VALID':
        return 'NONE', 'RUN_OR_REVALIDATION_FAILED'
    if binding != expected:
        return 'NONE', 'BINDING_MISMATCH'
    end_ns = S.ns(finding['end_utc']) if isinstance(finding.get('end_utc'), str) else -1
    if not started_ns <= end_ns <= evaluated_ns:
        return 'NONE', 'OUTSIDE_OPERATION_WINDOW'
    if finding.get('usable_source_count', 0) < 1:
        return 'NONE', 'NO_USABLE_SOURCE'
    projection = finding['projection']
    if projection['evidence_against']:
        return 'CONTESTED', 'CONTRARY_EVIDENCE_REPORTED'
    if projection['evidence_for']:
        return 'CORROBORATED', 'NO_CONTRARY_EVIDENCE_REPORTED'
    return 'NONE', 'NO_EVIDENCE_LISTED'


def hermes_stage(root, op, budget, backend, executable, home, manifest, clock_ns, controller=run_controlled_hermes_research):
    """Budgeted research over provisional research candidates; never changes probability or class."""
    need(isinstance(backend, (ExternalHermesCliBackend, FakeHermesBackend)), 'HERMES_BACKEND_UNSUPPORTED')
    findings, rows = [], {t['token_id']: t for t in manifest['tokens']}
    now = clock_ns()
    runs, spent = ledger(root, now)
    for number, token in enumerate(manifest['provisional_order'][:budget['max_runs_per_invocation']], 1):
        reserve = D(str(budget['max_usd_per_run']))
        if runs + 1 > budget['max_runs_per_7d'] or spent + reserve > D(str(budget['max_usd_per_7d'])):
            findings.append({'token_id': token, 'state': 'HERMES_BUDGET_EXHAUSTED', 'influence': 'NONE'})
            break
        row = rows[token]
        request = hermes_request(budget, row)
        binding = {k: row[k] for k in ('category', 'gamma_market_id', 'condition_id', 'token_id')}
        capture = R1.CaptureBackend(backend, op / f'hermes-{number:02d}.sentinel.json',
                                    {'started_ns': clock_ns(), 'reserved_usd': str(reserve), 'request_id': request.request_id})
        runs, spent = runs + 1, spent + reserve
        finding = {'token_id': token, 'binding': binding, 'request_id': request.request_id,
                   'origin': 'NO_RECEIPT', 'end_utc': None}
        try:
            result = controller(request, capture, executable_path=executable, hermes_home=home, context_mode=False,
                                clock=lambda: datetime.fromtimestamp(clock_ns() / 1e9, timezone.utc))
            finding['receipt'] = R1.sanitized_receipt(result.receipt)
            finding['end_utc'] = result.receipt.end_utc
            finding['origin'] = origin_of(backend, result.receipt, request)
            if result.error_code is not None or result.validated_draft is None:
                raise Stop('HERMES_RUN_FAILED')
            projection = R1.revalidate_full_draft(capture.captured_stdout, result.receipt, result.validated_draft)
            sources = map_hermes_sources(projection, result.receipt.receipt_id, result.receipt.end_utc)
            finding.update(state='VALID', projection=projection, usable_source_count=len(sources))
        except Exception:
            finding.update(state='RESEARCH_FAILED', projection=None, usable_source_count=0)
        S.put(op / f'hermes-{number:02d}.finding.json', finding)
        findings.append(finding)
    return findings


def influence(findings, tokens, started_ns, evaluated_ns):
    """Deterministic, re-derivable: flags and tiers from stored findings and two stored clocks."""
    rows = {t['token_id']: t for t in tokens}
    for finding in findings:
        state = finding.get('state')
        projection = finding.get('projection') or {}
        finding['hermes_flag'] = ('RESEARCH_FAILED' if state == 'RESEARCH_FAILED' else 'NOT_RUN' if state != 'VALID'
                                  else 'CONTRARY_EVIDENCE_REPORTED' if projection.get('evidence_against')
                                  else 'NO_CONTRARY_EVIDENCE_REPORTED')
        if state in ('VALID', 'RESEARCH_FAILED') and finding['token_id'] in rows:
            finding['influence'], finding['influence_reason'] = judge(finding, rows[finding['token_id']],
                                                                      started_ns, evaluated_ns)
        else:
            finding['influence'], finding['influence_reason'] = 'NONE', state or 'NOT_RUN'
    return findings


# ---------------------------------------------------------------- Alpha lineage

def alpha_records(manifest, registry):
    """Candidate per market (pure identity), one family per method, chained episodes per run."""
    loaded = AFR.load_and_verify_alpha_factory_registry(str(registry))
    need(loaded.is_valid and loaded.snapshot is not None, 'ALPHA_REGISTRY_INVALID')
    existing = [entry.record for entry in loaded.snapshot.entries]
    records, tokens, families, hermes_states = [], manifest['tokens'], {}, []
    for market in manifest['markets']:
        if market['reason'] in M_BUCKETS['eligible'] or market.get('rule_sha256') is None:
            continue
        category, mid, cond = market['category'], market['gamma_market_id'], market['condition_id']
        method = METHOD_NBA if category == 'SPORTS_NBA_MONEYLINE' else METHOD_RAIN
        lane = 'FUNDAMENTAL' if category == 'SPORTS_NBA_MONEYLINE' else 'WEATHER'
        if method not in families:
            built = AF.build_hypothesis_family({
                'family_version': '1', 'family_name': f'{method} independent public probability',
                'mechanism_key': method, 'mechanism_dimensions': {'method': method, 'category': category},
                'falsifiable_theme': 'An independent public probability differs from the venue price after costs.',
                'predecessor_family_id': None, 'creation_provenance': WP_ID, 'human_review_required': True})
            need(built.is_valid, 'ALPHA_FAMILY_INVALID')
            families[method] = built.record
            records.append(built.record)
        family = families[method]
        subject = [f'polymarket-market:{mid}', f'polymarket-condition:{cond}', f'rule-sha256:{market["rule_sha256"]}']
        candidate = AF.build_opportunity_candidate({
            'candidate_version': '1', 'title': f'{category} market {mid}',
            'research_question': f'Does the {method} probability exceed the venue price after costs?',
            'thesis': 'Independent public probability versus venue price, research only.',
            'subject_refs': subject, 'evidence_lanes': [lane], 'scope_key': f'alpha-hunter:{category}:{mid}',
            'mechanism_hint': method,
            'novelty_dimensions': {'subject_keys': subject, 'scope_key': f'alpha-hunter:{category}:{mid}',
                                   'mechanism_key': method},
            'discovery_provenance': WP_ID, 'human_review_required': True})
        need(candidate.is_valid, 'ALPHA_CANDIDATE_INVALID')
        records.append(candidate.record)
        mine = [t for t in tokens if t['gamma_market_id'] == mid and t['category'] == category]
        if any(t['research_class'] == 'RESEARCH_CANDIDATE' for t in mine):
            state, field = 'RESEARCH_SUPPORTIVE', ('evidence_for', ['Positive estimated after-cost margin under labelled assumptions.'])
        elif market['reason'] is None:
            state, field = 'EXECUTION_UNECONOMIC', ('evidence_against', ['No outcome token passed the venue and margin stages.'])
        else:
            state, field = 'DATA_INSUFFICIENT', ('known_missing_data', [f'Closed reason {market["reason"]}.'])
        leaves = R1._current_leaves(existing + records, candidate.record.candidate_id, family.hypothesis_family_id)
        lists = {name: [] for name in AF._EPISODE_LIST_FIELDS}
        lists.update(falsification_checks_performed=['Independence, lookahead, identity and venue checks applied.'],
                     tested_assumptions=['Uncalibrated public source probability.'],
                     limitations=['Fill probability unmeasured; research only.'])
        lists[field[0]] = field[1]
        episode = AF.build_research_episode(dict(lists, **{
            'episode_version': '1', 'candidate_id': candidate.record.candidate_id,
            'hypothesis_family_id': family.hypothesis_family_id,
            'predecessor_episode_id': leaves[0].research_episode_id if leaves else None,
            'reopened_episode_id': None, 'result_state': state, 'confidence_label': 'low',
            'evidence_lanes': [lane], 'exact_scope': {'market': mid, 'condition': cond, 'category': category},
            'evidence_regime': {'method': method, 'cutoff_ns': manifest['clocks']['source_cutoff_ns']},
            'research_question': candidate.record.research_question, 'thesis': candidate.record.thesis,
            'source_reference_ids': [],
            'deterministic_evidence_refs': ['alphahunter:sha256:' + digest(canonical(market))],
            'producer_type': 'DETERMINISTIC_ANALYSIS', 'producer_version': SCHEMA, 'producer_receipt_ref': None,
            'research_as_of': S.iso(manifest['clocks']['source_cutoff_ns']).split('.')[0].rstrip('Z') + 'Z',
            'creation_provenance': WP_ID, 'human_review_required': True}))
        need(episode.is_valid, 'ALPHA_EPISODE_INVALID')
        records.append(episode.record)
        for finding in manifest['hermes_findings']:
            if (finding.get('binding') or {}).get('gamma_market_id') == mid and finding['binding']['category'] == category:
                extra, problem = hermes_episode(finding, candidate.record.candidate_id, family,
                                                episode.record.research_episode_id, lane)
                records.extend(extra)
                hermes_states.append(problem or 'EPISODE_APPENDED')
    if records:
        result = AFR.append_alpha_factory_records(str(registry), records)
        need(result.is_valid, 'ALPHA_APPEND_INVALID')
        return {'inserted': len(result.inserted_record_ids), 'idempotent': len(result.idempotent_record_ids),
                'hermes_episodes': hermes_states}
    return {'inserted': 0, 'idempotent': 0, 'hermes_episodes': hermes_states}


# ---------------------------------------------------------------- operations

def root_init(root):
    root = S.safe(root, directory=True)
    need(root.is_dir(), 'SCRATCH_INVALID')
    config = root / 'config.json'
    if not config.exists():
        S.put(config, CONFIG)
    need(S.read(config) == json.loads(canonical(CONFIG)), 'CONFIG_INVALID')
    return root


def begin(root, clock_ns):
    operations = sorted(root.glob('op-*'))
    path = root / f'op-{len(operations) + 1:06d}'
    path.mkdir()
    started = clock_ns()
    S.put(path / 'started.json', {'schema': SCHEMA, 'started_ns': started, 'config_sha256': digest((root / 'config.json').read_bytes())})
    return path, started


def acquire(fetcher, categories, anchor, started_ns):
    if 'nba' in categories:
        markets = fetcher.get(S.DISCOVERY_URL)
        if isinstance(markets, list) and len(markets) <= 200:
            events = {}
            for day in (anchor, anchor + timedelta(days=1)):
                board = fetcher.get(S.ESPN + 'scoreboard?dates=' + day.strftime('%Y%m%d'))
                for event in (board or {}).get('events', []):
                    events.setdefault(event.get('id'), event)
            matched, copies = [], {}
            for market in markets:
                copies.setdefault(str(market.get('id')), set()).add(canonical(market))
            for market in markets:
                if len(matched) >= CONFIG['nba_events']:
                    break
                try:
                    _, tokens, start = S.rule(market)
                    event_id = S.matched_event(market, list(events.values()))
                    if (is_v2(market) or start <= started_ns or len(copies[str(market.get('id'))]) > 1
                            or event_id in [e for e, _ in matched]):
                        continue
                except Exception:
                    continue
                matched.append((event_id, tokens))
            for event_id, _ in matched:
                fetcher.get(S.ESPN + 'summary?event=' + event_id)
            yield from (t for _, tokens in matched for t in tokens)
    if 'rain' in categories:
        entries = []
        for offset in (1, 2):
            day = anchor + timedelta(days=offset)
            event = fetcher.get(rain_event_url(day))
            for market in (event or {}).get('markets', []) if isinstance(event, dict) else []:
                entries.append(((day, event.get('slug', '')), market))
        entries.sort(key=lambda item: (item[0][0], int(str(item[1].get('id'))) if str(item[1].get('id')).isdigit() else 0))
        found = []  # same order, rule, V2 and conflict filters as analyze_rain, so capacity agrees
        for (day, slug), _, market, conflict in unique_markets(entries):
            try:
                if not conflict and not is_v2(market, slug):
                    found.append((day, None, market, rain_rule(market, day)))
            except Exception:
                continue
        stations = {}
        for day, _, market, (_, semantics, tokens) in found[:CONFIG['rain_markets']]:
            if semantics.station_id not in stations:
                station = fetcher.get(f'{NWS}stations/{semantics.station_id}')
                try:
                    lat, lon = station['geometry']['coordinates'][1], station['geometry']['coordinates'][0]
                    points = fetcher.get(points_url(lat, lon))
                    grid = points['properties']['forecastGridData']
                    fetcher.get(grid)
                except Exception:
                    pass
                stations[semantics.station_id] = True
            yield from tokens


TERMINAL_STATES = ('COMPLETED', 'BLOCKED', 'INTERRUPTED_OR_UNKNOWN')


def unique_markets(entries):
    """Collapse byte-identical copies; flag ids with conflicting copies (both categories alike)."""
    contents, order = {}, []
    for key, market in entries:
        mid = str(market.get('id'))
        if mid not in contents:
            order.append((key, mid, market))
        contents.setdefault(mid, set()).add(canonical(market))
    return [(key, mid, market, len(contents[mid]) > 1) for key, mid, market in order]


def rain_candidates(op, urls, clocks):
    anchor = date.fromisoformat(clocks['anchor_utc_date'])
    found = []
    for offset in (1, 2):
        day = anchor + timedelta(days=offset)
        event = data(op, urls.get(rain_event_url(day)))
        for market in (event or {}).get('markets', []) if isinstance(event, dict) else []:
            found.append(((day, event.get('slug', '')), market))
    found.sort(key=lambda item: (item[0][0], int(str(item[1].get('id'))) if str(item[1].get('id')).isdigit() else 0))
    return unique_markets(found)


def hermes_episode(finding, candidate_id, family, predecessor_id, lane):
    """Section 6.7 mapping; returns (records, None) or ([], reason) when the builder rejects it."""
    projection = finding.get('projection')
    if finding.get('state') != 'VALID' or not projection:
        return [], 'RESEARCH_FAILED'
    against, support, missing = projection['evidence_against'], projection['evidence_for'], projection['known_missing_data']
    state = ('NO_EDGE_CURRENTLY' if against else 'RESEARCH_SUPPORTIVE' if support
             else 'DATA_INSUFFICIENT' if missing else None)
    if state is None:
        return [], 'RESEARCH_FAILED'
    receipt = finding['receipt']
    sources = map_hermes_sources(projection, receipt['receipt_id'], receipt['end_utc'])
    lists = {name: list(projection.get(name, [])) for name in AF._EPISODE_LIST_FIELDS if name != 'material_change_basis'}
    lists['material_change_basis'] = []
    lists['tested_assumptions'] = ['Public web research only; provider-reported origin ' + finding['origin'] + '.']
    built = AF.build_research_episode(dict(lists, **{
        'episode_version': '1', 'candidate_id': candidate_id, 'hypothesis_family_id': family.hypothesis_family_id,
        'predecessor_episode_id': predecessor_id, 'reopened_episode_id': None, 'result_state': state,
        'confidence_label': projection['confidence_label'], 'evidence_lanes': [lane],
        'exact_scope': {k: finding['binding'][k] for k in ('category', 'gamma_market_id', 'condition_id')},
        'evidence_regime': {'producer': 'HERMES_CONTROLLED_RESEARCH', 'origin': finding['origin']},
        'research_question': 'What public evidence contradicts or supports the independent probability for this outcome?',
        'thesis': projection['research_summary'],
        'source_reference_ids': [s.source_reference_id for s in sources],
        'deterministic_evidence_refs': ['alphahunter:sha256:' + digest(canonical(finding['binding']))],
        'producer_type': 'HERMES_CONTROLLED_RESEARCH', 'producer_version': 'hermes-controlled-research',
        'producer_receipt_ref': receipt['receipt_id'], 'research_as_of': receipt['end_utc'],
        'creation_provenance': WP_ID, 'human_review_required': True}))
    if not built.is_valid:
        return [], 'EPISODE_REJECTED'
    return [*sources, built.record], None


def mark_interrupted(root):
    for prior in sorted(root.glob('op-*')):
        S.safe(prior, directory=True)
        need(re.fullmatch(r'op-[0-9]{6}', prior.name), 'JOURNAL_INVALID')
        if not (prior / 'terminal.json').exists():
            S.put(prior / 'terminal.json', {'status': 'INTERRUPTED_OR_UNKNOWN'})


def hermes_inputs(op, tokens, clocks):
    """Re-derive flags and influence from the stored raw findings and stored clocks."""
    stored = S.read(op / 'hermes.json')
    findings = [{k: v for k, v in f.items() if k not in ('influence', 'influence_reason', 'hermes_flag')}
                for f in stored['findings']]
    return influence(findings, tokens, clocks['started_ns'], stored['influence_evaluated_ns'])

def run(scratch, registry, categories, *, budget_path=None, executable=None, home=None,
        fetcher_type=Fetcher, backend=None, clock_ns=time.time_ns, controller=run_controlled_hermes_research):
    hermes_flags = (budget_path, executable, home)
    need(all(x is None for x in hermes_flags) or all(x is not None for x in hermes_flags), 'HERMES_FLAGS_PARTIAL')
    need(set(categories) <= set(CATEGORIES) and categories, 'CATEGORIES_INVALID')
    root = root_init(scratch)
    registry = S.safe(registry)
    need(registry.is_file(), 'ALPHA_REGISTRY_INVALID')
    budget = load_budget(budget_path, root)
    if budget is not None:
        need(Path(executable).is_absolute() and Path(home).is_absolute(), 'HERMES_PATH_INVALID')
    with S.operation_lock(root):
        mark_interrupted(root)
        verify(root)
        op, started = begin(root, clock_ns)
        fetcher = fetcher_type(op)
        try:
            anchor = datetime.fromtimestamp(started // 1_000_000_000, timezone.utc).date()
            tokens = list(acquire(fetcher, categories, anchor, started))
            source_cutoff = clock_ns()
            for token in dict.fromkeys(tokens):
                fetcher.get(venue.clob_book_url(token))
            clocks = {'started_ns': started, 'anchor_utc_date': anchor.isoformat(),
                      'source_cutoff_ns': source_cutoff, 'evaluated_ns': clock_ns()}
            S.put(op / 'clocks.json', clocks)
            manifest = analyze(op, fetcher.receipts, clocks, [], categories, create=True)
            findings = []
            if budget is not None and manifest['provisional_order']:
                findings = hermes_stage(root, op, budget, backend or ExternalHermesCliBackend(), executable,
                                        home, manifest, clock_ns, controller)
                S.put(op / 'hermes.json', {'influence_evaluated_ns': clock_ns(), 'findings': findings})
                manifest = analyze(op, fetcher.receipts, clocks, hermes_inputs(op, manifest['tokens'], clocks),
                                   categories)
            S.put(op / 'manifest.json', manifest)
            alpha = alpha_records(manifest, registry)
            result = {'status': 'COMPLETED', 'manifest_sha256': digest((op / 'manifest.json').read_bytes()),
                      'run_mode': manifest['run_mode'], 'milestone': manifest['hermes_alpha_hunter_milestone'],
                      'funnel': manifest['funnel'], 'alpha': alpha,
                      'hermes_state': 'HERMES_NOT_RUN_BUDGET_ZERO' if budget is None else 'HERMES_BUDGET_PRESENT'}
        except Stop as error:
            result = {'status': 'BLOCKED', 'reason': str(error)}
        except Exception:
            result = {'status': 'BLOCKED', 'reason': 'INPUT_OR_NATIVE_INVALID'}
        result.update(network_attempts=len(fetcher.receipts), account_attempts=0, order_attempts=0)
        inputs = {p.name: digest(p.read_bytes()) for p in sorted(op.iterdir())
                  if p.is_file() and p.name != 'terminal.json' and not p.name.startswith('pit.sqlite3')}
        S.put(op / 'terminal.json', dict(result, inputs_sha256=inputs, categories=sorted(categories)))
        S.put(root / f'index-{op.name}.json', {'operation': op.name, 'status': result['status'],
                                                'terminal_sha256': digest((op / 'terminal.json').read_bytes())})
        return result


def verify(root):
    """Cold re-derivation of every operation; zero network, zero Hermes dispatch."""
    root = S.safe(root, directory=True)
    need(S.read(root / 'config.json') == json.loads(canonical(CONFIG)), 'CONFIG_INVALID')
    checked, operations = 0, sorted(root.glob('op-*'))
    indexes = {p.name for p in root.glob('index-op-*.json')}
    need(indexes <= {f'index-{op.name}.json' for op in operations}, 'VERIFY_INDEX_ORPHAN')
    for op in operations:
        S.safe(op, directory=True)
        record = S.read(op / 'terminal.json') if (op / 'terminal.json').exists() else None
        need(record is not None and record.get('status') in TERMINAL_STATES, 'VERIFY_TERMINAL_INVALID')
        index = root / f'index-{op.name}.json'
        if record['status'] == 'INTERRUPTED_OR_UNKNOWN':
            need(not index.exists(), 'VERIFY_INDEX_MISMATCH')
            continue
        need(index.exists() and S.read(index) == {'operation': op.name, 'status': record['status'],
             'terminal_sha256': digest((op / 'terminal.json').read_bytes())}, 'VERIFY_INDEX_MISMATCH')
        if record['status'] != 'COMPLETED':
            continue
        for name, sha in record['inputs_sha256'].items():
            need(digest(S.safe(op / name).read_bytes()) == sha, 'VERIFY_INPUT_CHANGED')
        receipts = [S.read(p) for p in sorted(op.glob('receipt-*.json'))]
        clocks = S.read(op / 'clocks.json')
        findings = []
        if (op / 'hermes.json').exists():
            provisional = analyze(op, receipts, clocks, [], set(record['categories']))
            findings = hermes_inputs(op, provisional['tokens'], clocks)
        manifest = analyze(op, receipts, clocks, findings, set(record['categories']))
        need(canonical(manifest) + b'\n' == (op / 'manifest.json').read_bytes(), 'VERIFY_MANIFEST_MISMATCH')
        checked += 1
    return {'status': 'VERIFIED', 'operations': checked, 'network_attempts': 0, 'hermes_dispatches': 0}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest='command', required=True)
    r = sub.add_parser('run')
    r.add_argument('--scratch-dir', required=True)
    r.add_argument('--alpha-registry', required=True)
    r.add_argument('--categories', required=True)
    r.add_argument('--research-budget')
    r.add_argument('--hermes-executable')
    r.add_argument('--hermes-home')
    v = sub.add_parser('verify')
    v.add_argument('--scratch-dir', required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == 'run':
            categories = {c for c in args.categories.split(',') if c}
            result = run(Path(args.scratch_dir), Path(args.alpha_registry), categories,
                         budget_path=args.research_budget, executable=args.hermes_executable, home=args.hermes_home)
        else:
            result = verify(Path(args.scratch_dir))
    except Stop as error:
        result = {'status': 'BLOCKED', 'reason': str(error)}
    print(json.dumps(result, sort_keys=True, default=str))
    return 0 if result.get('status') in ('COMPLETED', 'VERIFIED') else 1


if __name__ == '__main__':
    raise SystemExit(main())
