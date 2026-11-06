"""Conditional Oracle3-style basket economics for formally proven related markets (S10-R3-REL-01).

ADAPT_ALGORITHM only (no code copied, no dependency): Oracle3 ``oracle3/arbitrage.py``@267fb7c
reference baskets and payoff lower bounds; ``oracle3/fees.py``@267fb7c "prefer per-market fee
data, never a fallback default". All venue mechanics reuse the native
``src.execution_feasibility`` offline normalization (``build_public_venue_snapshot`` on frozen
bytes) and its pure evaluator helpers (market state, tick, two-dimension minimum order,
best-first ask sweep, taker fee with conservative 5 dp ceiling). There is no second price or
fee engine.

Every positive is CONDITIONAL: on a caller-declared finite payout model, on caller-supplied
venue bytes of unauthenticated origin, and on a simultaneous multi-leg fill that no native
route can provide. Nothing here is executable-edge evidence, a guarantee, a profit claim or
an order intent; ``executable_edge`` and ``guaranteed_arbitrage`` are always False.
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import ROUND_CEILING, Decimal
from types import SimpleNamespace

from src.execution_feasibility import evaluator as EV
from src.execution_feasibility.models import decimal_text

YES, NO = "YES", "NO"
ECONOMIC_STATUSES = ("THEORETICAL_PRICE_INCONSISTENCY", "FEE_AND_DEPTH_CONDITIONAL", "MECHANICALLY_INCONCLUSIVE",
                     "NO_CONDITIONAL_EDGE", "NOT_EXECUTABLE")
FEE_POLICY_KINDS = ("GAMMA_BODY_PER_MARKET", "TEST_ONLY_HYPOTHETICAL", "NATIVE_NEAR_TERM_SCREENER", "NONE")
# Pinned from tools/alpha/run_near_term_market_screener.py (FEE_POLICY / FEE_EXPIRY); a test
# re-reads that file so drift is caught. The bound is never extended here.
NATIVE_NEAR_TERM_FEE_POLICY = "documented-fees-20261028-near-term-02"
NATIVE_NEAR_TERM_FEE_EXPIRY = "2026-11-04T00:00:00Z"
ATOMICITY = "NOT_PROVEN_NO_NATIVE_MULTI_LEG_ROUTE"
_TAKER = SimpleNamespace(execution_style="AGGRESSIVE_TAKER")  # native _fee reads only execution_style
_NOT_EXECUTABLE = frozenset({"MARKET_INACTIVE", "MARKET_CLOSED", "MARKET_NOT_ACCEPTING_ORDERS", "ORDER_BOOK_DISABLED",
                             "NEG_RISK_UNSUPPORTED", "PRICE_OFF_TICK", "MINIMUM_ORDER_NOTIONAL_NOT_MET",
                             "MINIMUM_ORDER_SHARES_NOT_MET", "COMBO_UNSUPPORTED"})
_COST_UNKNOWN = frozenset({"DEPTH_INSUFFICIENT", "FEE_CONFIG_UNKNOWN", "FEE_POLICY_EXPIRED", "FEE_POLICY_NOT_YET_VALID",
                           "FEE_POLICY_ABSENT", "FEE_POLICY_EXTENSION_REJECTED", "FEE_EXPONENT_UNSUPPORTED"})


def _xsum(values) -> Decimal:
    """Exact accumulation (native trap-on-inexact context); builtin sum would round at 28 digits."""
    total = Decimal(0)
    for value in values:
        total = EV._EXACT.add(total, value)
    return total


def utc_ns(text: str) -> int:
    moment = datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    return int(moment.timestamp()) * 1_000_000_000


def reference_baskets(relation: str, n: int) -> list[dict]:
    """Oracle3 reference baskets with the minimum payoff each must certify on a valid model."""
    table = {
        "IMPLICATION": [("NO_A_YES_B", (NO, YES), 1)],
        "EXCLUSIVITY": [("NO_ALL", (NO,) * n, n - 1)],
        "COMPLEMENT": [("YES_BOTH", (YES, YES), 1), ("NO_BOTH", (NO, NO), 1)],
        "SAME_EVENT": [("YES_A_NO_B", (YES, NO), 1), ("NO_A_YES_B", (NO, YES), 1)],
        "EVENT_SUM": [("YES_ALL", (YES,) * n, 1), ("NO_ALL", (NO,) * n, n - 1)],
    }
    return [{"basket_id": b, "sides": list(s), "required_min_payout": m} for b, s, m in table[relation]]


def certified_min_payout(states: list, sides: list) -> int:
    """Recompute min over every admitted state of the basket payout (YES pays s, NO pays 1-s)."""
    return min(sum(s if side == YES else 1 - s for s, side in zip(state, sides)) for state in states)


def evaluate_fee_policy(policy: dict, decision_ns: int) -> dict:
    """Decision-time fee provenance; unknown or expired is never treated as zero."""
    kind = policy["kind"]
    out = {"kind": kind, "policy_id": policy["policy_id"], "test_only": kind == "TEST_ONLY_HYPOTHETICAL",
           "provenance": {"GAMMA_BODY_PER_MARKET": "CALLER_SUPPLIED_GAMMA_FEE_SCHEDULE_UNAUTHENTICATED",
                          "TEST_ONLY_HYPOTHETICAL": "VERSIONED_HYPOTHETICAL_TEST_ONLY",
                          "NATIVE_NEAR_TERM_SCREENER": "NATIVE_DATED_POLICY",
                          "NONE": "ABSENT"}[kind]}
    if kind == "NONE":
        return dict(out, status="FEE_POLICY_ABSENT")
    valid_until = utc_ns(policy["valid_until"])
    if kind == "NATIVE_NEAR_TERM_SCREENER":
        if policy["policy_id"] != NATIVE_NEAR_TERM_FEE_POLICY or valid_until > utc_ns(NATIVE_NEAR_TERM_FEE_EXPIRY):
            return dict(out, status="FEE_POLICY_EXTENSION_REJECTED")
    if decision_ns < utc_ns(policy["valid_from"]):
        return dict(out, status="FEE_POLICY_NOT_YET_VALID")
    if decision_ns >= valid_until:
        return dict(out, status="FEE_POLICY_EXPIRED")
    return dict(out, status="WINDOW_VALID")


def _leg_fee(snapshot, fills, fee_policy: dict, policy: dict, reasons: set) -> tuple[str, Decimal | None, Decimal | None]:
    if fee_policy["status"] != "WINDOW_VALID":
        reasons.add(fee_policy["status"])
        return "UNKNOWN", None, None
    if fee_policy["kind"] == "TEST_ONLY_HYPOTHETICAL":
        unrounded = EV._taker_fee(fills, Decimal(policy["test_rate"]), policy["test_exponent"])
        return "TEST_ONLY_CONSERVATIVE_5DP_UPPER_BOUND", unrounded, unrounded.quantize(EV.FEE_QUANTUM, rounding=ROUND_CEILING)
    if fee_policy["kind"] == "NATIVE_NEAR_TERM_SCREENER":
        # Inside its dated window the native policy is only a documented bound, not per-market data.
        reasons.add("FEE_CONFIG_UNKNOWN")
        return "UNKNOWN", None, None
    diags: set = set()
    _dimension, exactness, unrounded, bound = EV._fee(_TAKER, snapshot, fills, diags)
    if bound is None:
        reasons.update(diags or {"FEE_CONFIG_UNKNOWN"})
        return "UNKNOWN", None, None
    return exactness, unrounded, bound


def assess_leg(snapshot, *, binding_reason: str | None, shares: Decimal, decision_ns: int, max_age_ns: int,
               fee_policy: dict, policy: dict) -> dict:
    """One taker acquisition leg against one frozen native venue snapshot (no fill guarantee)."""
    reasons: set = set()
    out = {"venue_snapshot_id": None, "token_id": None, "best_ask": None, "visible_ask_depth": None, "filled_shares": None,
           "cost_usd": None, "fee_exactness": "UNKNOWN", "fee_bound_usd": None, "fee_unrounded_usd": None,
           "all_in_usd": None, "book_age_ns": None, "execution_style_assumed": "TAKER_ASK_SWEEP",
           "maker_zero_fee_not_assumed": True}
    if snapshot is None:
        reasons.add(binding_reason or "QUOTE_MISSING")
        return dict(out, status="QUOTE_INCONCLUSIVE", reasons=sorted(reasons))
    out.update(venue_snapshot_id=snapshot.venue_snapshot_id, token_id=snapshot.token_id)
    if binding_reason:
        reasons.add(binding_reason)
    if snapshot.gamma_source_state != "AVAILABLE" or snapshot.clob_source_state != "AVAILABLE":
        reasons.add("VENUE_SOURCE_INVALID")
        return dict(out, status="QUOTE_INCONCLUSIVE", reasons=sorted(reasons))
    diags: set = set()
    market = EV._market_dimension(snapshot, diags)
    reasons.update(diags)
    if market == "UNKNOWN":
        reasons.add("MARKET_STATE_UNKNOWN")
    if EV._identity_dimension(snapshot, diags) != "PASS":
        reasons.add("NEG_RISK_SOURCE_CONFLICT")
    if snapshot.gamma_neg_risk or snapshot.book_neg_risk:
        reasons.add("NEG_RISK_UNSUPPORTED")
    book_ns, completed = snapshot.book_timestamp_ns, snapshot.acquisition_completed_ns
    if completed > decision_ns:
        reasons.add("VENUE_EVIDENCE_AFTER_DECISION")
    elif book_ns > completed:
        reasons.add("BOOK_TIMESTAMP_INVALID")
    else:
        out["book_age_ns"] = decision_ns - book_ns
        if out["book_age_ns"] > max_age_ns:
            reasons.add("BOOK_STALE")
    if not snapshot.asks:
        reasons.add("NO_ASKS")
    else:
        out["best_ask"] = snapshot.asks[0][0]
        fills, depth, _ = EV._sweep(snapshot.asks, lambda _price: True, shares)
        filled = _xsum(take for _p, take in fills)
        cost = _xsum(EV._EXACT.multiply(p, take) for p, take in fills)
        out.update(visible_ask_depth=decimal_text(depth), filled_shares=decimal_text(filled), cost_usd=decimal_text(cost))
        for price, _take in fills:
            tick = EV._tick_dimension(price, snapshot, diags)
            if tick == "UNKNOWN":
                reasons.add("TICK_UNKNOWN")
        reasons.update(diags & {"PRICE_OFF_TICK", "TICK_SOURCE_CONFLICT"})
        if filled < shares:
            reasons.add("DEPTH_INSUFFICIENT")  # full-size notional unknown: the minimum check would test a partial fill
        else:
            # Two independent native dimensions: Gamma USDC notional vs CLOB share count.
            minimum, _ = EV._minimum_order(cost, shares, snapshot, diags)
            reasons.update(diags & {"MINIMUM_ORDER_NOTIONAL_NOT_MET", "MINIMUM_ORDER_SHARES_NOT_MET"})
            if minimum == "UNKNOWN":
                reasons.add("MINIMUM_ORDER_UNKNOWN")
            exactness, unrounded, bound = _leg_fee(snapshot, fills, fee_policy, policy, reasons)
            if bound is not None:
                out.update(fee_exactness=exactness, fee_unrounded_usd=decimal_text(unrounded), fee_bound_usd=decimal_text(bound),
                           all_in_usd=decimal_text(EV._EXACT.add(cost, bound)))
    if "NEG_RISK_UNSUPPORTED" in reasons:
        reasons.discard("NEG_RISK_SOURCE_CONFLICT")
    if reasons & _NOT_EXECUTABLE:
        status = "NOT_EXECUTABLE"
    elif reasons - _COST_UNKNOWN:
        status = "QUOTE_INCONCLUSIVE"
    elif reasons:
        status = "COST_INCONCLUSIVE"
    else:
        status = "COST_KNOWN"
    return dict(out, status=status, reasons=sorted(reasons))


def assess_basket(basket: dict, states: list, legs: list[dict], shares: Decimal, *, combo: bool, fee_test_only: bool) -> dict:
    """Certified minimum payout vs worst-case acquisition; conditional, never executable."""
    certified = certified_min_payout(states, basket["sides"])
    payout = EV._EXACT.multiply(Decimal(certified), shares)
    out = {"basket_id": basket["basket_id"], "sides": basket["sides"], "required_min_payout": basket["required_min_payout"],
           "certified_min_payout": certified, "shares_per_leg": decimal_text(shares), "certified_payout_usd": decimal_text(payout),
           "top_of_book_cost_usd": None, "all_in_cost_usd": None, "conditional_margin_usd": None,
           "fee_basis": "TEST_ONLY_HYPOTHETICAL" if fee_test_only else "DECISION_TIME_SNAPSHOT",
           "legs": legs, "atomicity": ATOMICITY, "executable_edge": False, "guaranteed_arbitrage": False,
           "profit_proven": False, "conditional_on": ["DECLARED_FORMAL_MODEL", "CALLER_SUPPLIED_VENUE_BYTES_UNAUTHENTICATED",
                                                      "SIMULTANEOUS_MULTI_LEG_FILL_UNPROVEN"]}
    if certified < basket["required_min_payout"]:
        return dict(out, status="NOT_EXECUTABLE", reasons=["BASKET_ORIENTATION_INVALID"])
    statuses = {leg["status"] for leg in legs}
    reasons = sorted({r for leg in legs for r in leg["reasons"]} | ({"COMBO_UNSUPPORTED"} if combo else set()))
    if combo or "NOT_EXECUTABLE" in statuses:
        return dict(out, status="NOT_EXECUTABLE", reasons=reasons)
    if "QUOTE_INCONCLUSIVE" in statuses:
        return dict(out, status="MECHANICALLY_INCONCLUSIVE", reasons=reasons)
    top = EV._EXACT.multiply(_xsum(Decimal(leg["best_ask"]) for leg in legs), shares)
    out["top_of_book_cost_usd"] = decimal_text(top)
    if "COST_INCONCLUSIVE" in statuses:
        # Fees and depth only add cost, so a pre-fee top-of-book sum at or above payout is no edge.
        return dict(out, status="THEORETICAL_PRICE_INCONSISTENCY" if top < payout else "NO_CONDITIONAL_EDGE", reasons=reasons)
    all_in = _xsum(Decimal(leg["all_in_usd"]) for leg in legs)
    margin = EV._EXACT.subtract(payout, all_in)
    out.update(all_in_cost_usd=decimal_text(all_in), conditional_margin_usd=decimal_text(margin))
    return dict(out, status="FEE_AND_DEPTH_CONDITIONAL" if margin > 0 else "NO_CONDITIONAL_EDGE", reasons=reasons)
