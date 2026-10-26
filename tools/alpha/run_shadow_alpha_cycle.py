"""Bounded public NBA forecast -> shadow economics -> outcome learning, never orders.

All state is explicit external scratch. Each manual cycle is a new occurrence;
verify reads frozen sources only. See docs/shadow_alpha_cycle_contract.md.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_CEILING, localcontext
from email.utils import parsedate_to_datetime
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
import time
import urllib.parse
import urllib.request
from zoneinfo import ZoneInfo

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO)) if str(REPO) not in sys.path else None
from src.data_layer.analytical_research import alpha_discovery as AD  # noqa: E402
from src.data_layer import point_in_time_market_research as PIT  # noqa: E402
from src.execution_feasibility import public_market as venue  # noqa: E402
from src.execution_feasibility import evaluator as mechanics  # noqa: E402

D = Decimal
METHOD = 'espn-nba-pregame-v1'
SCHEMA = 'shadow-alpha-v1'
DISCOVERY_URL = ('https://gamma-api.polymarket.com/markets?tag_id=745&'
                 'sports_market_types=moneyline&closed=false&limit=200&order=gameStartTime&ascending=true')
ESPN = 'https://site.api.espn.com/apis/site/v2/sports/basketball/nba/'
MAX_BYTES = 2_000_000
CONFIG = {'schema': SCHEMA, 'method': METHOD, 'shares': '10', 'forecast_stress': '0.10',
          'residual_cost_per_share': '0.005', 'max_book_age_ns': 30_000_000_000}
DANGEROUS = {'.git', '.ssh', '.aws', '.hermes', 'credentials', 'secrets', 'agent_memory', 'local_data'}
SECRET = re.compile(rb'(?i)(sk-[a-z0-9_-]{16,}|-----BEGIN [A-Z ]*PRIVATE KEY|bearer\s+[a-z0-9._-]{8,}|"(?:api_key|private_key|access_token|refresh_token|password|passphrase|authorization|cookie)"\s*:)')


class Stop(Exception):
    """Only closed, non-input-bearing codes reach the operator."""


def need(ok, code):
    if not ok:
        raise Stop(code)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode()


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def decimal(value):
    need(isinstance(value, (str, int)) and not isinstance(value, bool), 'NUMBER_INVALID')
    need(re.fullmatch(r'-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?', str(value)) is not None, 'NUMBER_INVALID')
    result = D(str(value))
    need(result.is_finite(), 'NUMBER_INVALID')
    return result


def ns(text):
    need(isinstance(text, str), 'CLOCK_INVALID')
    try:
        dt = datetime.fromisoformat(text.replace('Z', '+00:00'))
        need(dt.tzinfo is not None, 'CLOCK_INVALID')
        return int(dt.timestamp()) * 1_000_000_000 + dt.microsecond * 1000
    except (ValueError, OverflowError):
        raise Stop('CLOCK_INVALID') from None


def iso(value):
    return datetime.fromtimestamp(value // 1_000_000_000, timezone.utc).replace(
        microsecond=(value % 1_000_000_000) // 1000).isoformat().replace('+00:00', 'Z')


def safe(path, *, directory=False):
    p = Path(path)
    need(p.is_absolute() and not any(x.lower() in DANGEROUS for x in p.parts), 'PATH_FORBIDDEN')
    for part in (p, *p.parents):
        need(not (part / '.git').exists(), 'PATH_FORBIDDEN')
        if part.exists() or part.is_symlink():
            s = part.lstat()
            need(not part.is_symlink() and not (getattr(s, 'st_file_attributes', 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT), 'PATH_FORBIDDEN')
    resolved = p.resolve()
    need(not resolved.is_relative_to(REPO.resolve()), 'PATH_FORBIDDEN')
    if p.exists():
        need(p.is_dir() if directory else p.is_file(), 'PATH_FORBIDDEN')
    return p


def put(path, value):
    safe(path)
    raw = canonical(value) + b'\n'
    with path.open('xb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def read(path):
    safe(path)
    raw = path.read_bytes()
    need(len(raw) <= MAX_BYTES * 2 and not SECRET.search(raw), 'INPUT_INVALID')
    try:
        return decode(raw)
    except Exception:
        raise Stop('INPUT_INVALID') from None


def decode(raw):
    # ESPN contains deeper display metadata than a native venue snapshot. Its
    # bounded input wrapper retains native duplicate/nonfinite rejection.
    value = json.loads(raw, parse_float=str, parse_constant=venue._reject_constant,
                       object_pairs_hook=venue._no_duplicates)
    count = 0
    def check(item, depth=0):
        nonlocal count
        count += 1
        need(count <= 100_000 and depth <= 24, 'PUBLIC_JSON_LIMIT')
        if isinstance(item, str):
            need(len(item) <= 16_384, 'PUBLIC_JSON_LIMIT')
        elif isinstance(item, dict):
            for key, child in item.items():
                check(key, depth + 1)
                check(child, depth + 1)
        elif isinstance(item, list):
            for child in item:
                check(child, depth + 1)
    check(value)
    return value


def array(value):
    if isinstance(value, str):
        try:
            value = venue.decode_public_json(value.encode())
        except Exception:
            raise Stop('ARRAY_INVALID') from None
    need(isinstance(value, list), 'ARRAY_INVALID')
    return value


def url_ok(url):
    parts = urllib.parse.urlsplit(url)
    if url == DISCOVERY_URL:
        return True
    if parts.netloc == 'site.api.espn.com':
        return re.fullmatch(re.escape(ESPN) + r'(?:scoreboard\?dates=[0-9]{8}|summary\?event=[0-9]{1,16})', url) is not None
    try:
        venue._check_request(url, 'GET')
        return True
    except Exception:
        return False


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def bounded_body(response, deadline):
    raw = bytearray()
    sock = getattr(getattr(getattr(response, 'fp', None), 'raw', None), '_sock', None)
    need(sock is not None, 'PUBLIC_TRANSPORT_UNSUPPORTED')
    for _ in range(4096):
        remaining = deadline - time.monotonic()
        need(remaining > 0, 'NETWORK_DEADLINE')
        sock.settimeout(min(20, remaining))
        chunk = response.read1(min(65536, MAX_BYTES + 1 - len(raw)))
        if not chunk:
            return bytes(raw)
        raw.extend(chunk)
        need(len(raw) <= MAX_BYTES, 'PUBLIC_BODY_LIMIT')
    raise Stop('PUBLIC_CHUNK_LIMIT')


class Fetcher:
    def __init__(self, operation):
        self.operation = operation
        self.receipts = []
        self.started = time.monotonic()

    def get(self, url):
        need(url_ok(url) and len(self.receipts) < 32 and time.monotonic() - self.started < 100, 'NETWORK_BUDGET_OR_ENDPOINT')
        start = time.time_ns()
        receipt = {'url': url, 'started_ns': start, 'state': 'UNAVAILABLE', 'http_date': None,
                   'publication_time': None, 'sha256': None, 'raw_file': None}
        # STARTED-first operation journal already exists. Count attempts before dispatch.
        self.receipts.append(receipt)
        put(self.operation / f'request-{len(self.receipts):02d}.started.json',
            {'url': url, 'started_ns': start})
        try:
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
            request = urllib.request.Request(url, headers={'Accept': 'application/json', 'User-Agent': 'polymarket-shadow-alpha/1.0'})
            deadline = min(self.started + 120, time.monotonic() + 20)
            with opener.open(request, timeout=min(20, max(1, deadline - time.monotonic()))) as response:
                raw = bounded_body(response, deadline)
                need(response.status == 200 and len(raw) <= MAX_BYTES and not SECRET.search(raw), 'PUBLIC_BODY_INVALID')
                decode(raw)
                receipt['http_date'] = response.headers.get('Date')
                name = f'source-{len(self.receipts):02d}.json'
                with (self.operation / name).open('xb') as stream:
                    stream.write(raw)
                receipt.update(state='AVAILABLE', sha256=digest(raw), raw_file=name)
        except Exception:
            receipt['state'] = 'UNAVAILABLE'
        receipt['received_ns'] = time.time_ns()
        put(self.operation / f'receipt-{len(self.receipts):02d}.json', receipt)
        return self.data(receipt)

    def data(self, receipt):
        if receipt['state'] != 'AVAILABLE':
            return None
        return read(self.operation / receipt['raw_file'])


def source_for(receipts, url):
    matches = [r for r in receipts if r['url'] == url]
    need(len(matches) == 1, 'SOURCE_BINDING_INVALID')
    return matches[0]


def source_data(operation, receipt):
    need(receipt['state'] == 'AVAILABLE', 'SOURCE_UNAVAILABLE')
    name = receipt['raw_file']
    need(isinstance(name, str) and re.fullmatch(r'source-[0-9]{2}\.json', name), 'SOURCE_BINDING_INVALID')
    path = safe(operation / name)
    need(digest(path.read_bytes()) == receipt['sha256'], 'SOURCE_HASH_MISMATCH')
    return read(path)


def fresh_source(receipt, cutoff):
    need(receipt['started_ns'] <= receipt['received_ns'] <= cutoff, 'SOURCE_LOOKAHEAD')
    need(cutoff - receipt['received_ns'] <= 300_000_000_000, 'SOURCE_STALE')
    try:
        http_ns = ns(parsedate_to_datetime(receipt['http_date']).isoformat())
    except Exception:
        raise Stop('SOURCE_HTTP_CLOCK_UNKNOWN') from None
    need(-2_000_000_000 <= receipt['received_ns'] - http_ns <= 300_000_000_000, 'SOURCE_HTTP_STALE')


def rule(market):
    outcomes = array(market.get('outcomes'))
    tokens = array(market.get('clobTokenIds'))
    need(len(outcomes) == len(tokens) == 2 and len(set(outcomes)) == len(set(tokens)) == 2, 'BINARY_IDENTITY_INVALID')
    need(all(isinstance(x, str) and re.fullmatch(r'[A-Za-z][A-Za-z0-9 .-]{0,48}', x) for x in outcomes), 'TEAM_INVALID')
    need(all(isinstance(t, str) and re.fullmatch(r'[0-9]{1,100}', t) for t in tokens), 'TOKEN_INVALID')
    need(market.get('sportsMarketType') == 'moneyline', 'EVENT_CLASS_UNSUPPORTED')
    start = ns(market.get('gameStartTime'))
    local = datetime.fromtimestamp(start // 1_000_000_000, ZoneInfo('America/New_York'))
    month = ('January February March April May June July August September October November December').split()[local.month - 1]
    clock = f'{local.hour % 12 or 12}:{local.minute:02d}{"AM" if local.hour < 12 else "PM"}'
    expected = (f'In the upcoming NBA game, scheduled for {month} {local.day} at {clock} ET:\n'
                f'If the {outcomes[0]} win, the market will resolve to "{outcomes[0]}".\n'
                f'If the {outcomes[1]} win, the market will resolve to "{outcomes[1]}".\n'
                'If the game is postponed, this market will remain open until the game has been completed.\n'
                'If the game is canceled entirely, with no make-up game, this market will resolve 50-50.\n'
                'The result will be determined based on the final score including any overtime periods.')
    need(market.get('description') == expected and market.get('question') == f'{outcomes[0]} vs. {outcomes[1]}', 'RULE_UNSUPPORTED')
    need(market.get('resolutionSource') in ('https://www.nba.com/', 'https://www.nba.com'), 'RESOLUTION_SOURCE_INVALID')
    need(re.fullmatch(r'nba-[a-z]{2,4}-[a-z]{2,4}-' + local.strftime('%Y-%m-%d'), market.get('slug', '')) is not None, 'LEAGUE_OR_DATE_INVALID')
    return outcomes, tokens, start


def matched_event(market, events):
    outcomes, _, start = rule(market)
    found = []
    for event in events:
        competitions = event.get('competitions', [])
        if len(competitions) != 1:
            continue
        comp = competitions[0]
        names = [c.get('team', {}).get('name') for c in comp.get('competitors', [])]
        if set(names) == set(outcomes) and ns(comp['date']) == start:
            found.append(event['id'])
    need(len(found) == 1 and re.fullmatch(r'[0-9]{1,16}', found[0]), 'EVENT_NOT_UNIQUELY_MATCHED')
    return found[0]


def probability(market, summary, receipt, cutoff):
    outcomes, _, start = rule(market)
    fresh_source(receipt, cutoff)
    header = summary.get('header', {})
    need(header.get('league', {}).get('slug') == 'nba' and len(header.get('competitions', [])) == 1, 'SOURCE_EVENT_INVALID')
    competition = header['competitions'][0]
    need(ns(competition['date']) == start and cutoff < start, 'PREDICTION_NOT_PREGAME')
    need(competition.get('status', {}).get('type', {}).get('state') == 'pre', 'PREDICTION_NOT_PREGAME')
    competitors = competition.get('competitors', [])
    need(len(competitors) == 2, 'SOURCE_EVENT_INVALID')
    by_id = {c['team']['id']: c['team']['name'] for c in competitors}
    need(set(by_id.values()) == set(outcomes), 'SOURCE_TEAM_MISMATCH')
    predictor = summary.get('predictor', {})
    need(predictor.get('header') == 'Matchup Predictor', 'PROBABILITY_UNAVAILABLE')
    values = {}
    for side in ('homeTeam', 'awayTeam'):
        item = predictor.get(side, {})
        need(item.get('id') in by_id, 'SOURCE_TEAM_MISMATCH')
        values[by_id[item['id']]] = decimal(item.get('gameProjection')) / 100
    need(set(values) == set(outcomes) and sum(values.values()) == 1 and all(0 <= p <= 1 for p in values.values()), 'PROBABILITY_INVALID')
    p = values[outcomes[0]]
    return {'method': METHOD, 'event_id': header['id'], 'start_ns': start, 'p': str(p),
            'stress_lower': str(max(D(0), p - D(CONFIG['forecast_stress']))),
            'stress_upper': str(min(D(1), p + D(CONFIG['forecast_stress']))),
            'uncertainty_kind': 'UNCALIBRATED_SENSITIVITY', 'identification_bound': ['0', '1'],
            'calibration': 'UNPROVEN', 'conditional_on': 'COMPLETED_GAME',
            'publication_time': None, 'provider_model_version': 'NOT_PUBLISHED',
            'available_ns': receipt['received_ns'], 'source_sha256': receipt['sha256']}


def economics(market, book, forecast, index, receipt, cutoff, *, style='TAKER'):
    outcomes, tokens, _ = rule(market)
    fresh_source(receipt, cutoff)
    mid = market['id']
    try:
        gamma, diagnostics = venue.normalize_gamma_market(market, gamma_market_id=mid,
            condition_id=market['conditionId'], token_id=tokens[index])
        facts = venue.normalize_clob_book(book, condition_id=market['conditionId'], token_id=tokens[index])
    except Exception:
        raise Stop('VENUE_IDENTITY_OR_SHAPE_INVALID') from None
    need(not diagnostics and all(gamma[x] is True for x in ('active', 'accepting_orders', 'enable_order_book')) and gamma['closed'] is False, 'MARKET_UNAVAILABLE')
    need(gamma['gamma_neg_risk'] == facts['book_neg_risk'], 'VENUE_IDENTITY_OR_SHAPE_INVALID')
    need(0 <= cutoff - facts['book_timestamp_ns'] <= CONFIG['max_book_age_ns'], 'BOOK_STALE')
    bids, asks = facts['bids'], facts['asks']
    need(bool(bids and asks), 'BOOK_INCOMPLETE')
    bid, ask = D(bids[0][0]), D(asks[0][0])
    tick = D(facts['book_tick_size'])
    need(gamma['gamma_tick_size'] is not None and tick == D(gamma['gamma_tick_size']), 'TICK_MISMATCH')
    need(all(D(price) % tick == 0 for price, _ in (*asks, *bids)), 'PRICE_OFF_TICK')
    shares = D(CONFIG['shares'])
    p = D(forecast['p']) if index == 0 else 1 - D(forecast['p'])
    low = D(forecast['stress_lower']) if index == 0 else 1 - D(forecast['stress_upper'])
    high = D(forecast['stress_upper']) if index == 0 else 1 - D(forecast['stress_lower'])
    # Cancellation probability is unknown. Include its exact 0.5 payout in the hull.
    payout_lower, payout_upper = min(low, D('.5')), max(high, D('.5'))
    fills, _, depth = mechanics._sweep(asks, lambda price: price <= ask, shares)
    filled_capacity = sum((q for _, q in fills), D(0))
    notional = sum((price * q for price, q in fills), D(0))
    minimum = gamma['gamma_min_order_notional_usd']
    admissible = (minimum is not None and shares >= D(facts['book_min_order_size_raw'])
                  and ask * shares >= D(minimum) and filled_capacity == shares)
    need(gamma['fees_enabled'] is not None, 'FEES_UNKNOWN')
    if gamma['fees_enabled']:
        need(gamma['fee_taker_only'] is True and gamma['fee_rate'] is not None and gamma['fee_exponent'] is not None, 'FEES_UNKNOWN')
        exponent = D(gamma['fee_exponent'])
        need(exponent == exponent.to_integral_value() and 0 <= exponent <= 8, 'FEES_UNKNOWN')
        fee = mechanics._taker_fee(fills, D(gamma['fee_rate']), int(exponent)).quantize(D('.00001'), rounding=ROUND_CEILING)
    else:
        fee = D(0)
    residual = shares * D(CONFIG['residual_cost_per_share'])
    # Expected economics are scenarios, never a statement that a snapshot order filled.
    point = shares * p - notional - fee - residual if admissible else None
    lower = shares * payout_lower - notional - fee - residual if admissible else None
    upper = shares * payout_upper - notional - fee - residual if admissible else None
    action = 'RESEARCH' if lower is not None and lower > 0 else 'NO_TRADE'
    reason = 'POSITIVE_SCENARIO_FILL_MODEL_REQUIRED' if action == 'RESEARCH' else 'NONPOSITIVE_STRESS_EV' if admissible else 'MINIMUM_OR_DEPTH_UNSUPPORTED'
    if style == 'MAKER':
        action, reason = 'DEFER', 'MAKER_FILL_UNMEASURED'
    return {'market_id': mid, 'condition_id': market['conditionId'], 'token_id': tokens[index],
            'outcome_index': index, 'event_id': forecast['event_id'], 'p_estimate': str(p),
            'p_market': str((bid + ask) / 2), 'stress_payout_bound': [str(payout_lower), str(payout_upper)],
            'bid': str(bid), 'ask': str(ask), 'spread': str(ask - bid), 'shares': str(shares),
            'depth_capacity_shares': str(filled_capacity), 'fee': str(fee), 'residual_cost': str(residual),
            'gross_completion_ev': str(shares * (p - ask)),
            'completion_ev': None if point is None else str(point),
            'conservative_ev_if_filled': None if lower is None else str(lower),
            'ev_range_if_filled': None if lower is None else [str(lower), str(upper)],
            'per_intended_order_ev': 'UNKNOWN_UNMEASURED_FILL_RATE',
            'per_order_ev_identification_bound': [str(-notional - fee - residual), str(max(D(0), shares - notional))],
            'fill_outcome_independence': 'UNVERIFIED_SCENARIO_ASSUMPTION',
            'fill_probability': None, 'maker_fill_probability': None, 'admissible': admissible,
            'fill_scenarios': {'zero_fill_ev': '0', 'full_fill_stress_ev': None if lower is None else str(lower)},
            'realized_profit': None, 'restriction_observed': gamma['restricted'],
            'action': action, 'reason': reason, 'wp172_status': 'NOT_EVALUATED'}


def policy():
    value = dict(schema_version='1.0.0', policy_version=SCHEMA, eligible_market_statuses=['open'],
        metadata_freshness_seconds=300, order_book_freshness_seconds=30, resolution_rule_freshness_seconds=300,
        soft_last_trade_price_abs_delta='0.1', soft_mid_price_abs_delta='0.1', soft_spread_abs_delta='0.05',
        soft_top_depth_relative_delta='0.25', queue_capacity=20, exploration_slots=1, audit_slots=1,
        max_per_category=20, audit_seed=SCHEMA, research_archetype_taxonomy_version='alpha-archetypes/1',
        advisory_only=True, no_execution_authority=True, no_strategy_authority=True, no_qualification_authority=True)
    result = AD.build_alpha_discovery_policy(value)
    need(result.is_valid, 'NATIVE_POLICY_INVALID')
    return result.record


def native_discovery(operation, markets, observed_ns, *, create):
    path = operation / 'pit.sqlite3'
    cutoff = iso(observed_ns)
    if create:
        need(PIT.initialize_point_in_time_record_store(path).is_valid, 'NATIVE_PIT_INVALID')
        records = []
        for market in markets:
            mid = market.get('id')
            need(isinstance(mid, str) and re.fullmatch(r'[0-9]{1,32}', mid), 'MARKET_ID_INVALID')
            outcomes, tokens = array(market.get('outcomes')), array(market.get('clobTokenIds'))
            payload = {'question_text': market.get('question'), 'market_status': 'closed' if market.get('closed') else 'open',
                       'outcome_labels': outcomes, 'token_ids': ['token:polymarket:' + t for t in tokens],
                       'condition_id': market.get('conditionId'), 'category': 'NBA', 'resolution_date': market.get('endDate')}
            record = dict(schema_id='point-in-time-market-research-record', schema_version='1.0.0',
                record_family='MARKET_OBSERVATION', snapshot_id='snapshot:' + digest(canonical(market)),
                ingestion_batch_id='batch:' + digest(canonical(markets)), event_time=None, observed_time=cutoff,
                ingestion_time=cutoff, lifecycle_state='NORMALIZED_ACCEPTED', classification='PRIMARY_ASSERTION',
                lineage_parent_ids=[], supersedes_record_version_id=None, normalizer_version=SCHEMA,
                validator_version='pit-native', parameter_set_id=SCHEMA, human_review_required=False,
                canonical_payload=payload, observation_kind='MARKET_METADATA', platform_id='platform:polymarket',
                event_id='event:polymarket:' + mid, market_id='market:polymarket:' + mid, token_id=None,
                source_id='source:polymarket:gamma-markets', source_assertion_id='assertion:' + mid,
                source_snapshot_id='source:' + digest(canonical(market)))
            built = PIT.build_market_observation(record)
            need(built.is_valid, 'NATIVE_PIT_RECORD_INVALID')
            records.append(built.record)
        if records:
            need(PIT.append_point_in_time_records(path, records).is_valid, 'NATIVE_PIT_APPEND_INVALID')
    else:
        need(PIT.load_and_verify_point_in_time_record_store(path).is_valid, 'NATIVE_PIT_INVALID')
    pol = policy()
    result = AD.build_alpha_universe_snapshot(path, pol, cutoff)
    need(result.is_valid, 'NATIVE_UNIVERSE_INVALID')
    universe = result.record
    bases = AD.build_pre_allocation_triage_bases(universe, pol, analysis_temporal_mode='HISTORICAL_REPLAY',
        alpha_memory_temporal_posture='HISTORICAL_AVAILABILITY_UNPROVEN')
    need(bases.is_valid, 'NATIVE_TRIAGE_INVALID')
    final = AD.allocate_and_finalize_research_queue(universe, pol, bases.records)
    need(final.is_valid, 'NATIVE_QUEUE_INVALID')
    return {'universe': AD.alpha_discovery_record_to_mapping(universe),
            'triage': [AD.alpha_discovery_record_to_mapping(x) for x in final.records if type(x) is AD.MarketTriageDecision],
            'queue': AD.alpha_discovery_record_to_mapping(final.record)}


def analyze(operation, receipts, cutoff, *, create=False):
    discovery_receipt = source_for(receipts, DISCOVERY_URL)
    fresh_source(discovery_receipt, cutoff)
    markets = source_data(operation, discovery_receipt)
    need(isinstance(markets, list) and len(markets) <= 200, 'UNIVERSE_LIMIT')
    need(len({m['id'] for m in markets}) == len(markets), 'DUPLICATE_MARKET')
    native = native_discovery(operation, markets, discovery_receipt['received_ns'], create=create)
    rows, forecasts, scores = [], [], []
    summaries = {r['url'].split('event=')[1]: r for r in receipts if r['url'].startswith(ESPN + 'summary?')}
    events = []
    for receipt in receipts:
        if receipt['url'].startswith(ESPN + 'scoreboard?') and receipt['state'] == 'AVAILABLE':
            fresh_source(receipt, cutoff)
            events.extend(source_data(operation, receipt).get('events', []))
    # Adjacent scoreboards may overlap. Keep identical ids once; conflicting copies close matching.
    unique = {}
    for event in events:
        need(event['id'] not in unique or canonical(event) == canonical(unique[event['id']]), 'SCOREBOARD_CONFLICT')
        unique[event['id']] = event
    forecasted_events = set()
    for market in markets:
        row = {'market_id': market['id'], 'action': 'DEFER', 'reason': 'ANALYSIS_CAPACITY'}
        rows.append(row)
        try:
            eid = matched_event(market, list(unique.values()))
            need(eid not in forecasted_events and len(forecasted_events) < 8, 'DUPLICATE_OR_CAPACITY_EVENT')
            need(eid in summaries, 'PROBABILITY_UNAVAILABLE')
            receipt = summaries[eid]
            summary = source_data(operation, receipt)
            need(summary.get('header', {}).get('id') == eid, 'SOURCE_EVENT_INVALID')
            forecast = probability(market, summary, receipt, cutoff)
            forecast.update(market_id=market['id'], condition_id=market['conditionId'],
                token_ids=array(market['clobTokenIds']), outcomes=array(market['outcomes']),
                rule_sha256=digest(market['description'].encode()), cutoff_ns=cutoff,
                prediction_id=digest(canonical({'market': market['id'], 'rule': market['description'],
                    'source': forecast['source_sha256'], 'method': METHOD})))
            forecasts.append(forecast)
            forecasted_events.add(eid)
            outcomes, tokens, _ = rule(market)
            for index, token in enumerate(tokens):
                try:
                    book_receipt = source_for(receipts, venue.clob_book_url(token))
                    score = economics(market, source_data(operation, book_receipt), forecast, index, book_receipt, cutoff)
                    scores.append(score)
                except Stop as error:
                    scores.append({'market_id': market['id'], 'event_id': eid, 'outcome_index': index,
                                   'action': 'DEFER', 'reason': str(error), 'realized_profit': None})
            row.update(action='SCORED', reason='INDEPENDENT_PUBLIC_FORECAST')
        except (Stop, KeyError, TypeError, ValueError):
            row['reason'] = 'UNSUPPORTED_UNMATCHED_OR_SOURCE_UNAVAILABLE'
    scored = sum(x.get('completion_ev') is not None for x in scores)
    return {'schema': SCHEMA, 'method': METHOD, 'cutoff_ns': cutoff, 'native_discovery': native,
            'market_rows': rows, 'forecasts': forecasts, 'scores': scores,
            'denominators': {'observed': len(markets), 'screened': len(rows), 'forecasted_events': len(forecasts),
                'scored_outcomes': scored, 'actionable': sum(x['action'] == 'SHADOW_CANDIDATE' for x in scores),
                'abstained_outcomes': sum(x['action'] != 'SHADOW_CANDIDATE' for x in scores),
                'unscorable_outcomes': len(scores) - scored},
            'status': 'SHADOW_INTELLIGENCE_REAL_EVIDENCE_PASS' if forecasts and scored else 'DATA_INSUFFICIENT',
            'paper': 'NO_PAPER_SESSION', 'calibration': 'INSUFFICIENT_OUTCOMES',
            'improvement': 'IMPROVEMENT_NOT_YET_MEASURABLE', 'external_universe_completeness': 'UNPROVEN',
            'network_attempts': len(receipts), 'account_attempts': 0, 'order_attempts': 0,
            'wallet_attempts': 0, 'provider_calls': 0, 'research_credit_cost': '0',
            'source_elapsed_ns': max(r['received_ns'] for r in receipts) - min(r['started_ns'] for r in receipts),
            'realized_profit': None, 'fill_rate': None}


def root_check(root):
    root = safe(root, directory=True)
    need(root.is_dir() and read(root / 'config.json') == CONFIG, 'CONFIG_INVALID')
    return root


def paper_snapshot(path):
    # Native constructor verifies existing copied history; it never opens the original.
    from src.paper_trading.store import PaperStore
    from src.research_runtime.paper_performance_bridge import build_research_paper_performance_snapshot, snapshot_to_mapping
    store = PaperStore(path)
    try:
        snapshot = snapshot_to_mapping(build_research_paper_performance_snapshot(store))
    finally:
        store.close()
    return {'evidence_class': 'NATIVE_RESEARCH_PAPER', 'link': 'UNLINKED_NOT_CAUSAL',
            'snapshot': snapshot, 'live_profit_credit': None, 'shadow_fill_credit': None}


def link_paper(root, source):
    root = root_check(root)
    source = safe(source)
    need(source.is_file() and not source.is_relative_to(root), 'PAPER_SOURCE_INVALID')
    need(not any(Path(str(source) + suffix).exists() for suffix in ('-wal', '-shm', '-journal')), 'PAPER_SIDECAR_UNSAFE')
    need(source.stat().st_size <= 32_000_000, 'PAPER_SIZE_LIMIT')
    raw = source.read_bytes()
    with operation_lock(root):
        verify(root)
        op = begin(root, 'PAPER')
        with (op / 'paper.sqlite3').open('xb') as stream:
            stream.write(raw)
        result = paper_snapshot(op / 'paper.sqlite3')
        need(digest(source.read_bytes()) == digest(raw), 'PAPER_SOURCE_CHANGED')
        result.update(status='PAPER_LINK_RECORDED', network_attempts=0, account_attempts=0, order_attempts=0)
        return finish(op, result, [])


@contextmanager
def operation_lock(root):
    # Kernel-held lock is automatically released on process death, unlike a stale PID file.
    path = safe(root / 'operation.lock')
    with path.open('a+b') as handle:
        if os.name == 'nt':
            import msvcrt
            handle.seek(0)
            if not handle.read(1):
                handle.write(b'0')
                handle.flush()
            handle.seek(0)
            try:
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError:
                raise Stop('OPERATION_BUSY') from None
        else:
            import fcntl
            try:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError:
                raise Stop('OPERATION_BUSY') from None
        try:
            yield
        finally:
            if os.name == 'nt':
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)


def begin(root, kind):
    operations = sorted(root.glob('op-*'))
    for prior in operations:
        safe(prior, directory=True)
        need(re.fullmatch(r'op-[0-9]{6}', prior.name), 'JOURNAL_INVALID')
        if not (prior / 'terminal.json').exists():
            need((prior / 'started.json').is_file(), 'JOURNAL_INVALID')
            put(prior / 'terminal.json', {'status': 'INTERRUPTED_OR_UNKNOWN', 'started_sha256': digest((prior / 'started.json').read_bytes())})
    path = root / f'op-{len(operations) + 1:06d}'
    path.mkdir()
    put(path / 'started.json', {'schema': SCHEMA, 'kind': kind, 'started_ns': time.time_ns(),
        'ordinal': len(operations) + 1, 'config_sha256': digest((root / 'config.json').read_bytes())})
    return path


def finish(operation, result, receipts):
    inputs = {p.name: digest(p.read_bytes()) for p in sorted(operation.iterdir()) if p.is_file() and p.name != 'terminal.json'}
    put(operation / 'terminal.json', {'status': 'COMPLETED', 'result': result, 'receipts': receipts,
        'inputs_sha256': inputs})
    return result


def cycle(root, *, fetcher_type=Fetcher):
    root = root_check(root)
    with operation_lock(root):
        verify(root)
        op = begin(root, 'CYCLE')
        fetcher = fetcher_type(op)
        try:
            markets = fetcher.get(DISCOVERY_URL)
            need(isinstance(markets, list) and len(markets) <= 200, 'DISCOVERY_UNAVAILABLE')
            events = []
            date = datetime.now(timezone.utc).date()
            for day in (date, date + timedelta(days=1)):
                board = fetcher.get(ESPN + 'scoreboard?dates=' + day.strftime('%Y%m%d'))
                if board is not None:
                    events.extend(board.get('events', []))
            ids = {}
            for event in events:
                ids.setdefault(event['id'], event)
            selected = set()
            for market in markets:
                if len(selected) >= 8:
                    break
                try:
                    eid = matched_event(market, list(ids.values()))
                    need(eid not in selected, 'DUPLICATE_EVENT')
                    _, tokens, start = rule(market)
                    need(start > time.time_ns(), 'PREDICTION_NOT_PREGAME')
                except (Stop, KeyError, TypeError, ValueError):
                    continue
                selected.add(eid)
                fetcher.get(ESPN + 'summary?event=' + eid)
                for token in tokens:
                    fetcher.get(venue.clob_book_url(token))
            result = analyze(op, fetcher.receipts, time.time_ns(), create=True)
        except Exception as error:
            result = {'status': 'BLOCKED', 'reason': str(error) if isinstance(error, Stop) else 'INPUT_OR_NATIVE_INVALID',
                      'network_attempts': len(fetcher.receipts), 'account_attempts': 0, 'order_attempts': 0}
        return finish(op, result, fetcher.receipts)


def resolution(original, current, summary, receipt, cutoff):
    need(current.get('id') == original['market_id'] and current.get('conditionId') == original['condition_id'], 'OUTCOME_IDENTITY_MISMATCH')
    outcomes, tokens, _ = rule(current)
    need(tokens == original['token_ids'] and outcomes == original['outcomes'], 'OUTCOME_TOKEN_OR_ORDER_CHANGED')
    need(digest(current['description'].encode()) == original['rule_sha256'], 'OUTCOME_RULE_CHANGED')
    fresh_source(receipt, cutoff)
    need(receipt['received_ns'] > original['cutoff_ns'], 'OUTCOME_LOOKAHEAD')
    if not current.get('closed') or current.get('umaResolutionStatus') != 'resolved':
        return {'state': 'UNRESOLVED'}
    closed = ns(current.get('closedTime'))
    need(original['cutoff_ns'] < closed <= receipt['received_ns'], 'RESOLUTION_CLOCK_INVALID')
    payouts = [decimal(x) for x in array(current.get('outcomePrices'))]
    header = summary.get('header', {})
    need(header.get('id') == original['event_id'] and header.get('league', {}).get('slug') == 'nba', 'OUTCOME_EVENT_MISMATCH')
    comp = header['competitions'][0]
    need(ns(comp['date']) == original['start_ns'], 'OUTCOME_EVENT_MISMATCH')
    outcomes, _, _ = rule(current)
    competitors = comp.get('competitors', [])
    need(len(competitors) == 2 and {c['team']['name'] for c in competitors} == set(outcomes), 'OUTCOME_EVENT_MISMATCH')
    status = comp.get('status', {}).get('type', {})
    if payouts == [D('.5'), D('.5')]:
        need(status.get('name') in ('STATUS_CANCELED', 'STATUS_CANCELLED'), 'CANCELLATION_NOT_CORROBORATED')
        return {'state': 'VOID_HALF_PAY', 'payout': '0.5', 'resolved_ns': closed}
    need(sorted(payouts) == [0, 1], 'OUTCOME_PAYOUT_UNSUPPORTED')
    need(closed >= original['start_ns'], 'RESOLUTION_CLOCK_INVALID')
    if comp.get('status', {}).get('type', {}).get('completed') is not True:
        return {'state': 'INDEPENDENT_RESULT_PENDING'}
    winners = [c['team']['name'] for c in competitors if c.get('winner') is True]
    need(len(winners) == 1 and payouts[outcomes.index(winners[0])] == 1, 'OUTCOME_SOURCE_DISAGREEMENT')
    return {'state': 'COMPLETED_BINARY', 'payout': str(payouts[0]), 'event_id': original['event_id'],
            'available_ns': receipt['received_ns'], 'resolved_ns': closed, 'prediction_id': original['prediction_id']}


def loss(p, y):
    p, y = D(p), D(y)
    # Endpoint clipping applies only to log loss, never Brier or economic probability.
    clipped = min(D('.999999'), max(D('.000001'), p))
    with localcontext() as context:
        context.prec = 40
        log = -(y * clipped.ln() + (1 - y) * (1 - clipped).ln())
    return {'brier': str((p - y) ** 2), 'log_loss': str(log)}


def learning(observations):
    events = {}
    for row in observations:
        need(row['event_id'] not in events or events[row['event_id']]['y'] == row['y'], 'OUTCOME_CONFLICT')
        events.setdefault(row['event_id'], row)
    rows = list(events.values())
    metrics = [{'event_id': r['event_id'], 'forecast': loss(r['p'], r['y']),
                'market': loss(r['market_p'], r['y'])} for r in rows]
    base = {'independent_events': len(rows), 'metrics': metrics, 'realized_trade_profit': None,
            'no_trade_profit_baseline': '0', 'status': 'IMPROVEMENT_NOT_YET_MEASURABLE', 'adopted': False}
    if len(rows) < 20:
        return base
    # Append order freezes the first ten finalized events. Eligible holdout
    # forecasts must be strictly later than *all* their labels. Neither roster
    # can move when a delayed earlier event finally resolves.
    train = rows[:10]
    formed_at = max(r['outcome_available_ns'] for r in train)
    holdout = [r for r in rows[10:] if r['cutoff_ns'] > formed_at][:10]
    if len(holdout) < 10:
        return dict(base, reason='FORMATION_LABELS_NOT_AVAILABLE_BEFORE_HOLDOUT')
    def mse(group, weight):
        return sum((weight * D(r['p']) + (1 - weight) * D(r['market_p']) - D(r['y'])) ** 2 for r in group) / len(group)
    weight = min((D('.25'), D('.5'), D('.75'), D('1')), key=lambda w: (mse(train, w), -w))
    candidate, original, market = mse(holdout, weight), mse(holdout, D(1)), mse(holdout, D(0))
    proposal = {'method': METHOD, 'blend_weight': str(weight), 'formation_events': len(train),
                'holdout_events': len(holdout), 'candidate_brier': str(candidate), 'original_brier': str(original),
                'market_brier': str(market), 'automatic_adoption': False,
                'formation_event_ids': [r['event_id'] for r in train], 'formation_closed_at_ns': formed_at,
                'holdout_event_ids': [r['event_id'] for r in holdout]}
    return dict(base, status='OOS_POINT_IMPROVEMENT_OBSERVED' if candidate < min(original, market) else 'OOS_IMPROVEMENT_UNPROVEN',
                proposal_id=digest(canonical(proposal)), proposal=proposal, statistical_significance='NOT_ESTABLISHED')


def all_results(root):
    results = []
    for op in sorted(root.glob('op-*')):
        terminal = read(op / 'terminal.json') if (op / 'terminal.json').exists() else {'status': 'INTERRUPTED_OR_UNKNOWN'}
        if terminal['status'] == 'COMPLETED':
            results.append((op, terminal))
    return results


def pending_forecasts(prior):
    known, settled, observations, checked = {}, set(), [], {}
    for ordinal, (_, terminal) in enumerate(prior):
        for forecast in terminal['result'].get('forecasts', []):
            score = next((s for s in terminal['result'].get('scores', []) if s.get('market_id') == forecast['market_id'] and s.get('outcome_index') == 0 and 'p_market' in s), None)
            if score:
                known.setdefault(forecast['event_id'], (forecast, score))
        for outcome in terminal['result'].get('outcomes', []):
            checked[outcome['event_id']] = ordinal
            if outcome.get('state') in ('COMPLETED_BINARY', 'VOID_HALF_PAY'):
                settled.add(outcome['event_id'])
        observations.extend(terminal['result'].get('new_observations', []))
    pending = [(event, pair) for event, pair in known.items() if event not in settled]
    pending.sort(key=lambda item: (checked.get(item[0], -1), item[1][0]['cutoff_ns'], item[0]))
    return pending, observations


def outcome_batch(prior, operation):
    pending, _ = pending_forecasts(prior)
    started = read(operation / 'started.json')['started_ns']
    return [(event, pair) for event, pair in pending if started > pair[0]['start_ns']][:8]


def derive_outcomes(prior, operation, receipts, cutoff):
    _, observations = pending_forecasts(prior)
    outcomes, new = [], []
    for event, (forecast, score) in outcome_batch(prior, operation):
        try:
            mr = source_for(receipts, venue.gamma_market_url(forecast['market_id']))
            sr = source_for(receipts, ESPN + 'summary?event=' + event)
            fresh_source(sr, cutoff)
            outcome = resolution(forecast, source_data(operation, mr), source_data(operation, sr), mr, cutoff)
            outcome.update(event_id=event)
            if outcome['state'] == 'COMPLETED_BINARY':
                row = {'event_id': event, 'p': forecast['p'], 'market_p': score['p_market'], 'y': outcome['payout'],
                       'cutoff_ns': forecast['cutoff_ns'], 'outcome_available_ns': max(mr['received_ns'], sr['received_ns'])}
                new.append(row)
        except Exception:
            outcome = {'event_id': event, 'state': 'UNRESOLVED_OR_INVALID'}
        outcomes.append(outcome)
    return {'status': 'OUTCOMES_RECORDED', 'cutoff_ns': cutoff, 'outcomes': outcomes, 'new_observations': new,
            'learning': learning(observations + new), 'network_attempts': len(receipts),
            'account_attempts': 0, 'order_attempts': 0, 'realized_profit': None}


def update_outcomes(root, *, fetcher_type=Fetcher):
    root = root_check(root)
    # Verify immutable history before using it to bind new observations.
    with operation_lock(root):
        verify(root)
        prior = all_results(root)
        op = begin(root, 'OUTCOMES')
        fetcher = fetcher_type(op)
        try:
            for event, (forecast, _) in outcome_batch(prior, op):
                fetcher.get(venue.gamma_market_url(forecast['market_id']))
                fetcher.get(ESPN + 'summary?event=' + event)
            result = derive_outcomes(prior, op, fetcher.receipts, time.time_ns())
        except Exception:
            result = {'status': 'BLOCKED', 'reason': 'OUTCOME_INPUT_INVALID', 'network_attempts': len(fetcher.receipts)}
        return finish(op, result, fetcher.receipts)


def verify(root):
    root = root_check(root)
    completed = interrupted = attempts = unknown_attempts = 0
    prior = []
    for ordinal, op in enumerate(sorted(root.glob('op-*')), 1):
        safe(op, directory=True)
        started = read(op / 'started.json')
        need(op.name == f'op-{ordinal:06d}' and started['ordinal'] == ordinal, 'JOURNAL_INVALID')
        need(started['config_sha256'] == digest((root / 'config.json').read_bytes()), 'CONFIG_CHANGED')
        request_files = sorted(op.glob('request-*.started.json'))
        attempts += len(request_files)
        need(len(request_files) <= 32, 'JOURNAL_INVALID')
        for index, path in enumerate(request_files, 1):
            need(path.name == f'request-{index:02d}.started.json', 'JOURNAL_INVALID')
            request = read(path)
            need(url_ok(request['url']), 'SOURCE_BINDING_INVALID')
            receipt_path = op / f'receipt-{index:02d}.json'
            if not receipt_path.exists():
                unknown_attempts += 1
                continue
            receipt = read(receipt_path)
            need(receipt['url'] == request['url'] and receipt['started_ns'] == request['started_ns'], 'SOURCE_BINDING_INVALID')
            if receipt['state'] == 'AVAILABLE':
                source_data(op, receipt)
        if not (op / 'terminal.json').exists():
            interrupted += 1
            continue
        terminal = read(op / 'terminal.json')
        if terminal['status'] == 'INTERRUPTED_OR_UNKNOWN':
            need(terminal['started_sha256'] == digest((op / 'started.json').read_bytes()), 'JOURNAL_INVALID')
            interrupted += 1
            continue
        need(len(request_files) == len(terminal['receipts']), 'JOURNAL_INVALID')
        need(all(read(op / f'receipt-{i:02d}.json') == receipt for i, receipt in enumerate(terminal['receipts'], 1)), 'SOURCE_BINDING_INVALID')
        for name, sha in terminal['inputs_sha256'].items():
            need(Path(name).name == name and digest(safe(op / name).read_bytes()) == sha, 'JOURNAL_HASH_MISMATCH')
        for receipt in terminal['receipts']:
            need(url_ok(receipt['url']), 'SOURCE_BINDING_INVALID')
            if receipt['state'] == 'AVAILABLE':
                source_data(op, receipt)
        result = terminal['result']
        if started['kind'] == 'CYCLE' and result['status'] != 'BLOCKED':
            need(canonical(analyze(op, terminal['receipts'], result['cutoff_ns'])) == canonical(result), 'REPLAY_MISMATCH')
        if started['kind'] == 'OUTCOMES' and result['status'] != 'BLOCKED':
            need(canonical(derive_outcomes(prior, op, terminal['receipts'], result['cutoff_ns'])) == canonical(result), 'REPLAY_MISMATCH')
        if started['kind'] == 'PAPER':
            replay = dict(paper_snapshot(op / 'paper.sqlite3'), status='PAPER_LINK_RECORDED',
                          network_attempts=0, account_attempts=0, order_attempts=0)
            need(canonical(replay) == canonical(result), 'REPLAY_MISMATCH')
        prior.append((op, terminal))
        completed += 1
    return {'status': 'VERIFIED', 'occurrences': completed + interrupted, 'completed': completed,
            'interrupted_or_unknown': interrupted, 'recorded_network_attempts': attempts, 'fresh_attempts': 0,
            'network_attempt_outcome_unknown': unknown_attempts,
            'account_attempts': 0, 'order_attempts': 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('init', 'cycle', 'update-outcomes', 'link-paper', 'verify'))
    parser.add_argument('--scratch-dir', required=True)
    parser.add_argument('--paper-store')
    args = parser.parse_args()
    try:
        root = safe(args.scratch_dir, directory=True)
        if args.command == 'init':
            root.mkdir(parents=False, exist_ok=False)
            put(root / 'config.json', CONFIG)
            result = {'status': 'INITIALIZED', 'method': METHOD}
        elif args.command == 'link-paper':
            need(args.paper_store is not None, 'PAPER_SOURCE_REQUIRED')
            result = link_paper(root, args.paper_store)
        else:
            result = {'cycle': cycle, 'verify': verify, 'update-outcomes': update_outcomes}[args.command](root)
        # Full native records stay in the journal. The operator gets no raw metadata.
        fields = ('status', 'reason', 'method', 'denominators', 'network_attempts', 'source_elapsed_ns',
                  'account_attempts', 'wallet_attempts', 'order_attempts', 'provider_calls',
                  'research_credit_cost', 'calibration', 'improvement', 'occurrences', 'completed',
                  'interrupted_or_unknown', 'recorded_network_attempts', 'fresh_attempts',
                  'network_attempt_outcome_unknown')
        compact = {key: result[key] for key in fields if key in result}
        if 'learning' in result:
            compact['learning'] = {key: result['learning'][key] for key in ('status', 'independent_events', 'adopted')}
        print(json.dumps(compact, sort_keys=True))
        return 1 if result['status'] in ('BLOCKED', 'DATA_INSUFFICIENT') else 0
    except Exception as error:
        print(json.dumps({'status': 'BLOCKED', 'reason': str(error) if isinstance(error, Stop) else 'INPUT_OR_PATH_INVALID'}))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
