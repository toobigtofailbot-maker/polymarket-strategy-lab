"""Causal historical diagnostics. Statistics alone never authenticate a corpus."""
from decimal import Decimal, localcontext, ROUND_FLOOR
import re

from src.execution_gateway.gateway import GatewayError, _canonical_decimal
from src.live_pilot import pilot as native

Z = Decimal('1.6448536269514722')
ROW_KEYS = frozenset(('event_group source_cutoff_ns resolved_ns method_id method_sha256 '
    'rule_sha256 horizon_s p_point payout raw_sha256').split())
METHODS = frozenset(('NBA_ESPN_V1', 'RAIN_NWS_V1'))
# No original pre-event corpus with independently verified settlement has been accepted.
PRODUCTION_CORPORA = frozenset()


def require(ok, code='CALIBRATION_INVALID'):
    if not ok:
        raise GatewayError(code)


def number(value):
    require(type(value) is str and len(value) <= 64)
    try:
        d = Decimal(value)
        require(d.is_finite() and 0 <= d <= 1 and _canonical_decimal(d) == value)
        return d
    except Exception:
        raise GatewayError('CALIBRATION_INVALID') from None


def integer(value, low=0):
    require(type(value) is int and low <= value <= 2**63-1)
    return value


def sha(value):
    require(type(value) is str and re.fullmatch('[0-9a-f]{64}', value))
    return value


def bucket(value):
    with localcontext() as ctx:
        ctx.prec = 80
        return min(int(number(value) * 10), 9)


def wilson_lower(k, n):
    integer(n, 1)
    integer(k)
    require(k <= n)
    with localcontext() as ctx:
        ctx.prec = 80
        p = Decimal(k) / n
        z2 = Z * Z
        lower = (p + z2/(2*n) - Z*(p*(1-p)/n + z2/(4*n*n)).sqrt())/(1+z2/n)
        return max(Decimal(0), min(Decimal(1), lower)).quantize(Decimal('0.000001'), rounding=ROUND_FLOOR)


def historical_bound(records, *, p_point, method_id, method_sha256, rule_sha256,
                     horizon_s, decision_ns, method_frozen_ns):
    """Validate every row before selecting a bucket; returns TEST_ONLY diagnostics.

    Original receipt authentication and independent settlement are separate trust
    requirements. Self-hashed rows cannot promote this result into production.
    """
    result = dict(status='NO_TRADE', reason='CALIBRATION_INSUFFICIENT', evidence_class='TEST_ONLY',
        production_eligible=False, method_id=method_id if type(method_id) is str and method_id in METHODS else None,
        method_sha256=None, rule_sha256=None, horizon_s=None, bucket=None, n_train=0,
        n_holdout=0, n_bucket=0, k=0, lower=None, model_brier=None, baseline_brier=None,
        training_prevalence=None, training_end_ns=None, holdout_start_ns=None, holdout_end_ns=None,
        dataset_sha256=None, raw_sha256=[], record_sha256=None)
    try:
        require(type(records) is list and len(records) <= 100_000)
        if not records:
            return _seal(result)
        require(method_id in METHODS)
        sha(method_sha256); sha(rule_sha256)
        integer(horizon_s, 1); integer(decision_ns, 1); integer(method_frozen_ns, 1)
        selected_bucket = bucket(p_point)
        result.update(method_sha256=method_sha256, rule_sha256=rule_sha256,
                      horizon_s=horizon_s, bucket=selected_bucket)
        seen = set()
        for r in records:
            require(type(r) is dict and set(r) == ROW_KEYS)
            group = r['event_group']
            require(type(group) is str and re.fullmatch('[A-Za-z0-9_.:-]{1,160}', group) and group not in seen)
            seen.add(group)
            integer(r['horizon_s'], 1)
            require((r['method_id'], r['method_sha256'], r['rule_sha256'], r['horizon_s']) ==
                    (method_id, method_sha256, rule_sha256, horizon_s))
            integer(r['source_cutoff_ns'], 1); integer(r['resolved_ns'], 1)
            require(r['source_cutoff_ns'] < r['resolved_ns'] < decision_ns)
            integer(r['payout']); require(r['payout'] in (0, 1))
            number(r['p_point']); sha(r['raw_sha256'])
        ordered = sorted(records, key=lambda r: (r['resolved_ns'], r['event_group']))
        result['dataset_sha256'] = native._digest(native._canonical(ordered))
        result['raw_sha256'] = sorted({r['raw_sha256'] for r in ordered})
        train_n = 7*len(ordered)//10
        train, hold = ordered[:train_n], ordered[train_n:]
        result.update(n_train=len(train), n_holdout=len(hold))
        if not train or not hold:
            return _seal(result)
        require(train[-1]['resolved_ns'] < hold[0]['resolved_ns'])
        require(method_frozen_ns < min(r['source_cutoff_ns'] for r in hold))
        with localcontext() as ctx:
            ctx.prec = 80
            prevalence = Decimal(sum(r['payout'] for r in train))/len(train)
            model = sum(((number(r['p_point'])-r['payout'])**2 for r in hold), Decimal(0))/len(hold)
            baseline = sum(((prevalence-r['payout'])**2 for r in hold), Decimal(0))/len(hold)
            rows = [r for r in hold if bucket(r['p_point']) == selected_bucket]
            k = sum(r['payout'] for r in rows)
            result.update(n_bucket=len(rows), k=k, training_prevalence=_canonical_decimal(prevalence),
                model_brier=_canonical_decimal(model), baseline_brier=_canonical_decimal(baseline),
                training_end_ns=train[-1]['resolved_ns'], holdout_start_ns=hold[0]['resolved_ns'],
                holdout_end_ns=hold[-1]['resolved_ns'])
            if len(rows) < 50:
                return _seal(result)
            result['lower'] = _canonical_decimal(wilson_lower(k, len(rows)))
            result['reason'] = 'CALIBRATION_NOT_VERIFIED' if model <= baseline else 'CALIBRATION_BASELINE_FAILED'
            result['status'] = 'DIAGNOSTIC_READY' if model <= baseline else 'NO_TRADE'
    except Exception:
        # Invalid inputs never leak record values or partial numeric admission fields.
        result = dict.fromkeys(result)
        result.update(status='NO_TRADE', reason='CALIBRATION_INVALID', evidence_class='TEST_ONLY',
                      production_eligible=False, raw_sha256=[])
    return _seal(result)


def _seal(result):
    result['record_sha256'] = native._digest(native._canonical({k:v for k,v in result.items() if k != 'record_sha256'}))
    return result
