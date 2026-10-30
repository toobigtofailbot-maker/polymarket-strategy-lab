"""Complement payoff diagnostics; the native gateway has no atomic two-leg route."""
from decimal import Decimal, localcontext
import re

from src.live_pilot.calibration import require, number, integer, sha
from src.live_pilot import pilot as native

KEYS = frozenset(('condition_id rule_sha256 token_ids outcome_indices payouts asks shares '
    'fees_usd reserve_usd margin_usd source_ns evaluated_ns settlement_kind neg_risk combo raw_sha256').split())


def money(value):
    require(type(value) is str and len(value) <= 64)
    d = native._decimal(value)
    require(d >= 0 and d <= Decimal('1000000'))
    return d


def verify_complement(record, *, now_ns):
    result = dict(status='NO_TRADE', reason='STRUCTURAL_INVALID', theoretical_margin_usd=None,
        execution_eligible=False, evidence_class='RESEARCH_ONLY', record_sha256=None)
    try:
        require(type(record) is dict and set(record) == KEYS)
        require(type(record['condition_id']) is str and re.fullmatch('0x[0-9a-f]{64}', record['condition_id']))
        sha(record['rule_sha256']); sha(record['raw_sha256'])
        tokens = record['token_ids']
        require(type(tokens) is list and len(tokens) == 2 and tokens[0] != tokens[1]
                and all(type(t) is str and re.fullmatch('[0-9]{1,80}', t) for t in tokens))
        require(record['outcome_indices'] == [0, 1] and all(type(x) is int for x in record['outcome_indices']))
        require(record['payouts'] == ['1', '1'] and record['settlement_kind'] == 'BINARY_CTF_EXACTLY_ONE_WINNER'
                and record['neg_risk'] is False and record['combo'] is False)
        integer(now_ns, 1); integer(record['source_ns'], 1); integer(record['evaluated_ns'], 1)
        require(record['source_ns'] <= record['evaluated_ns'] <= now_ns < record['source_ns']+30*10**9)
        require(type(record['asks']) is list and len(record['asks']) == 2
                and type(record['fees_usd']) is list and len(record['fees_usd']) == 2)
        with localcontext() as ctx:
            ctx.prec = 80
            asks = [number(v) for v in record['asks']]
            require(all(0 < p < 1 for p in asks))
            q = money(record['shares']); require(q > 0)
            fees = sum((money(v) for v in record['fees_usd']), Decimal(0))
            bound = q - q*sum(asks) - fees - money(record['reserve_usd'])
            result.update(status='STRUCTURAL_CANDIDATE' if bound > money(record['margin_usd']) else 'NO_TRADE',
                reason='MULTI_LEG_EXECUTION_UNPROVEN', theoretical_margin_usd=format(bound, 'f'))
    except Exception:
        pass
    result['record_sha256'] = native._digest(native._canonical({k:v for k,v in result.items() if k != 'record_sha256'}))
    return result


def assess_capture(scratch):
    """Cold-replay native public capture without inventing settlement semantics.

    Gamma binary labels and complementary token ids alone do not prove absence
    of void/cancel ambiguity. This source supplies no certified rule theorem.
    """
    from tools.alpha import run_near_term_market_screener as scanner
    try:
        verified = scanner.verify(scratch)
        if verified['status'] != 'VERIFIED':
            raise ValueError()
        return dict(status='NO_TRADE', reason='SETTLEMENT_UNVERIFIED', execution_eligible=False,
                    source_manifest_sha256=verified['manifest_sha256'])
    except Exception:
        return dict(status='NO_TRADE', reason='STRUCTURAL_SOURCE_UNVERIFIED', execution_eligible=False,
                    source_manifest_sha256=None)
