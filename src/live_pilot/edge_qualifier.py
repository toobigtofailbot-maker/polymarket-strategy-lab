"""Independent edge boundary. No production corpus/method is approved on this base."""
from decimal import Decimal, localcontext
import json

from src.execution_gateway.gateway import GatewayError
from src.live_pilot import calibration, pilot as native

PRODUCTION_METHODS = frozenset()
MARKER = 'autonomous_edge'


def evidence_diagnosis(scratch):
    """Replay information is separate from financial admission, even when valid."""
    from src.live_pilot.provenance import verify_capture
    evidence = verify_capture(scratch)
    return dict(status='NO_TRADE', reason='CALIBRATION_NOT_VERIFIED', p_lower=None,
                production_eligible=False, evidence=evidence)


def qualify_candidate(forecast, calibration_result=None):
    """Shaped forecasts and numerical diagnostics confer no production authority."""
    from src.live_pilot.autonomous_cycle import validate_forecast
    result = dict(status='NO_TRADE', reason='CALIBRATION_NOT_VERIFIED', p_lower=None,
                  production_eligible=False, source_method=None)
    try:
        validate_forecast(forecast)
        result['source_method'] = forecast['native_method_id']
        if calibration_result is None:
            calibration_result = calibration.historical_bound([], p_point=forecast['p_point'],
                method_id=forecast['native_method_id'], method_sha256=forecast['native_method_sha256'],
                rule_sha256=forecast['resolution_rule_sha256'], horizon_s=None,
                decision_ns=forecast['evaluated_ns'], method_frozen_ns=None)
            result['reason'] = calibration_result['reason']
        # Do not trust diagnostic flags, caller hashes, model confidence, or an injected allowlist.
        if forecast['native_method_id'] not in PRODUCTION_METHODS:
            return result
        raise GatewayError('CALIBRATION_NOT_VERIFIED')
    except Exception:
        result.update(reason='CALIBRATION_NOT_VERIFIED', p_lower=None)
    return result


def require_native_edge(version, intent, *, required=False):
    """Called by LIVE-ORCH in its wallet lock, never a model-supplied callback.

    Proof is acyclic: method/corpus -> strategy -> current intent. Until original
    provenance is accepted, every opt-in marker refuses, including a rehashed file.
    """
    try:
        rule = json.loads(version.strategy_spec_json)['execution_rule']
        if MARKER not in rule:
            if required:
                raise GatewayError('EDGE_PROOF_REQUIRED')
            return
        marker = rule[MARKER]
        if type(marker) is not dict or set(marker) != {'method_id', 'method_sha256', 'corpus_proof_sha256'}:
            raise GatewayError('EDGE_PROOF_INVALID')
        calibration.sha(marker['method_sha256']); calibration.sha(marker['corpus_proof_sha256'])
        if marker['method_id'] not in PRODUCTION_METHODS:
            raise GatewayError('CALIBRATION_NOT_VERIFIED')
        raise GatewayError('CALIBRATION_NOT_VERIFIED')
    except GatewayError:
        raise
    except Exception:
        raise GatewayError('EDGE_PROOF_INVALID') from None


def combined_loss(checkpoint, evaluation, proposed, *, activation_ledger_head):
    """Conservative lifetime loss; profits in other lifecycles cannot replenish it."""
    calibration.sha(activation_ledger_head)
    if any(type(v) is not Decimal or not v.is_finite() or v < 0
           for v in (proposed, evaluation.total_commitment)):
        raise GatewayError('EDGE_ACCOUNT_UNVERIFIED')
    if evaluation.blocking_codes:
        raise GatewayError('EDGE_ACCOUNT_UNVERIFIED')
    with localcontext() as ctx:
        ctx.prec = 80
        episodes = checkpoint['episodes']
        ids = [e['episode_id'] for e in episodes]
        if len(ids) != len(set(ids)):
            raise GatewayError('EDGE_ACCOUNT_UNVERIFIED')
        loss = Decimal(0)
        for buy in episodes:
            if buy['binding']['side'] != 'BUY' or buy['state'] not in ('CLOSED_RECONCILED', 'TERMINAL_NO_POSITION', 'CREATE_REJECTED'):
                continue
            trades = buy['reconciliation']['trades']
            cost = sum((native._decimal(t['principal_usd']) for t in trades if t['status'] == 'CONFIRMED'), Decimal(0))
            cost += _fee(buy)
            exits = [e for e in episodes if e['binding'].get('closes_episode_id') == buy['episode_id']]
            proceeds = Decimal(0)
            for sell in exits:
                if sell['binding']['side'] != 'SELL' or sell['state'] not in ('CLOSED_RECONCILED', 'TERMINAL_NO_POSITION'):
                    raise GatewayError('EDGE_ACCOUNT_UNVERIFIED')
                proceeds += sum((native._decimal(t['principal_usd']) for t in sell['reconciliation']['trades']
                                 if t['status'] == 'CONFIRMED'), Decimal(0)) - _fee(sell)
            # No verified redemption receipt exists on this base: held-to-resolution
            # proceeds remain zero, a conservative loss rather than invented profit.
            loss += max(cost-proceeds, Decimal(0))
        total = loss + evaluation.total_commitment + proposed
        if total > Decimal(10):
            raise GatewayError('EDGE_COMBINED_LOSS_LIMIT')
        return total


def _fee(episode):
    r = episode['reconciliation']
    if r['fee_state'] == 'NOT_REQUIRED':
        return Decimal(0)
    if r['fee_state'] != 'RECONCILED' or r['actual_fee_usd'] is None:
        raise GatewayError('EDGE_ACCOUNT_UNVERIFIED')
    return native._decimal(r['actual_fee_usd'])
