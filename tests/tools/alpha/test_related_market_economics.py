"""S10-R3-REL-01 conditional Oracle3 basket economics over native offline venue mechanics.

All venue bodies are SANITIZED_SYNTHETIC. A positive here is conditional on a declared formal
model, unauthenticated caller bytes and an unproven simultaneous fill: never executable edge,
guaranteed arbitrage or profit.
"""
from __future__ import annotations

from decimal import ROUND_CEILING, ROUND_HALF_EVEN, Decimal
from itertools import product
from pathlib import Path
import re

import pytest

from src.data_layer.analytical_research import related_market as RM
from src.data_layer.analytical_research import related_market_economics as RE
from src.execution_feasibility import evaluator as EV
from src.execution_feasibility import public_market as PM
from tests.tools.alpha.test_related_market_alpha import (MARKETS, _condition, _tokens, build_request, clob_body, gamma_body,
                                                         make_world, rows, run_rel)

REPO_ROOT = Path(__file__).resolve().parents[3]
DECISION_NS = RE.utc_ns("2026-06-01T12:00:00Z")
MAX_AGE_NS = 60 * 10 ** 9
GAMMA = {"policy_id": "gamma-body", "kind": "GAMMA_BODY_PER_MARKET", "valid_from": "2026-06-01T00:00:00Z",
         "valid_until": "2026-06-02T00:00:00Z", "test_rate": None, "test_exponent": None}


def snap(slug="oh-dem", side="YES", asks=(("0.45", "50"),), *, gamma=None, clob=None, completed="2026-06-01T11:59:57Z"):
    no, yes = _tokens(slug)
    row = next(m for m in MARKETS if m[0] == slug)
    return PM.build_public_venue_snapshot(
        gamma_market_id=str(500 + [m[0] for m in MARKETS].index(slug)), condition_id=_condition(row),
        token_id=yes if side == "YES" else no, acquisition_started_ns=RE.utc_ns("2026-06-01T11:59:56Z"),
        acquisition_completed_ns=RE.utc_ns(completed),
        gamma=PM.SourceFetchResult("BODY", gamma_body(slug, **(gamma or {}))),
        clob=PM.SourceFetchResult("BODY", clob_body(slug, side, list(asks), **(clob or {}))))


def leg(snapshot, *, shares="10", policy=GAMMA, decision_ns=DECISION_NS, binding=None):
    fee = RE.evaluate_fee_policy(policy, decision_ns)
    return RE.assess_leg(snapshot, binding_reason=binding, shares=Decimal(shares), decision_ns=decision_ns,
                         max_age_ns=MAX_AGE_NS, fee_policy=fee, policy=policy)


@pytest.fixture(scope="module")
def world(tmp_path_factory):
    return make_world(tmp_path_factory.mktemp("rel01_econ"))


# ------------------------------------------------------------------ R004


def test_rel_conditional_oracle3_baskets_and_native_costs(world, tmp_path, monkeypatch):
    # Reference baskets certify their Oracle3 minimum on every valid model of every supported n.
    for relation in RM.RELATIONS:
        low, high = RM.GROUP_SIZE[relation]
        for n in range(low, high + 1):
            valid = [list(s) for s in product((0, 1), repeat=n)
                     if RM.formal_proof(relation, n, [list(s)], [])["status"] == "FORMAL_BOUNDED_PAYOFF_PROOF"]
            for basket in RE.reference_baskets(relation, n):
                assert RE.certified_min_payout(valid, basket["sides"]) >= basket["required_min_payout"]
                assert basket["required_min_payout"] in (1, n - 1)
    # Wrong implication direction: NO(B)+YES(A) on an A->B model certifies 0 and is refused.
    wrong = {"basket_id": "NO_B_YES_A", "sides": ["YES", "NO"], "required_min_payout": 1}
    states = [[0, 0], [0, 1], [1, 1]]
    assert RE.certified_min_payout(states, wrong["sides"]) == 0
    out = RE.assess_basket(wrong, states, [], Decimal("10"), combo=False, fee_test_only=False)
    assert out["status"] == "NOT_EXECUTABLE" and out["reasons"] == ["BASKET_ORIENTATION_INVALID"]
    # Integrated: native snapshot + native sweep and taker-fee helpers are the only cost engine.
    calls = {"_sweep": 0, "_taker_fee": 0, "_minimum_order": 0, "_tick_dimension": 0, "build_public_venue_snapshot": 0}
    for name in calls:
        owner = PM if name == "build_public_venue_snapshot" else EV
        real = getattr(owner, name)
        monkeypatch.setattr(owner, name, lambda *a, _r=real, _n=name, **k: calls.__setitem__(_n, calls[_n] + 1) or _r(*a, **k))
    code, _, receipt = run_rel(tmp_path, world, build_request(world))
    assert code == 0 and all(calls.values()), calls
    v01 = {b["basket_id"]: b for b in rows(receipt)["v01"]["economics"]["baskets"]}
    yes = v01["YES_BOTH"]
    # Independent recomputation: shares * rate * p * (1 - p), ceiling at 5 dp per leg.
    fee = lambda p: (Decimal("10") * Decimal("0.02") * p * (1 - p)).quantize(Decimal("0.00001"), rounding=ROUND_CEILING)
    expected_all_in = Decimal("4.5") + fee(Decimal("0.45")) + Decimal("5") + fee(Decimal("0.5"))
    assert Decimal(yes["all_in_cost_usd"]) == expected_all_in == Decimal("9.5995")
    assert yes["certified_payout_usd"] == "10" and Decimal(yes["conditional_margin_usd"]) == Decimal("10") - expected_all_in
    assert yes["status"] == "FEE_AND_DEPTH_CONDITIONAL" and yes["atomicity"] == RE.ATOMICITY
    assert yes["executable_edge"] is False and yes["guaranteed_arbitrage"] is False and yes["profit_proven"] is False
    assert "SIMULTANEOUS_MULTI_LEG_FILL_UNPROVEN" in yes["conditional_on"]
    assert all(leg["fee_exactness"] == "CONSERVATIVE_5DP_UPPER_BOUND" and leg["venue_snapshot_id"] for leg in yes["legs"])
    assert v01["NO_BOTH"]["status"] == "NO_CONDITIONAL_EDGE"
    v05 = rows(receipt)["v05"]["economics"]["baskets"][0]
    assert v05["status"] == "THEORETICAL_PRICE_INCONSISTENCY" and "DEPTH_INSUFFICIENT" in v05["reasons"]
    assert v05["top_of_book_cost_usd"] == "9" and v05["all_in_cost_usd"] is None  # raw quote sum is never a fill proof
    # The protected WP172 executable-edge assessor is never referenced.
    for path in (Path(RE.__file__), Path(RM.__file__), REPO_ROOT / "tools" / "alpha" / "run_related_market_alpha.py"):
        text = path.read_text(encoding="utf-8")
        assert "assess_executable_edge" not in text and "research_runtime" not in text


# ------------------------------------------------------------------ R005


def test_rel_economic_unknown_fee_depth_clock_and_atomicity(world, tmp_path):
    screener = (REPO_ROOT / "tools" / "alpha" / "run_near_term_market_screener.py").read_text(encoding="utf-8")
    assert f"FEE_POLICY = '{RE.NATIVE_NEAR_TERM_FEE_POLICY}'" in screener
    assert re.search(r"FEE_EXPIRY = 1793750400 \* NS", screener) and RE.utc_ns(RE.NATIVE_NEAR_TERM_FEE_EXPIRY) == 1793750400 * 10 ** 9
    native = {"policy_id": RE.NATIVE_NEAR_TERM_FEE_POLICY, "kind": "NATIVE_NEAR_TERM_SCREENER",
              "valid_from": "2026-10-28T00:00:00Z", "valid_until": RE.NATIVE_NEAR_TERM_FEE_EXPIRY, "test_rate": None, "test_exponent": None}
    nov6 = RE.utc_ns("2026-11-06T00:00:00Z")
    assert RE.evaluate_fee_policy(native, nov6)["status"] == "FEE_POLICY_EXPIRED"
    assert RE.evaluate_fee_policy(dict(native, valid_until="2026-12-01T00:00:00Z"), nov6)["status"] == "FEE_POLICY_EXTENSION_REJECTED"
    assert RE.evaluate_fee_policy(dict(GAMMA, valid_from="2026-06-01T12:00:01Z"), DECISION_NS)["status"] == "FEE_POLICY_NOT_YET_VALID"
    # Expired / absent / dated-bound / missing per-market fees are unknown, never zero.
    s = snap()
    for policy in (dict(native, valid_from="2026-05-01T00:00:00Z", valid_until="2026-06-01T00:00:00Z"),
                   {"policy_id": "none", "kind": "NONE", "valid_from": None, "valid_until": None, "test_rate": None, "test_exponent": None},
                   dict(native, valid_from="2026-05-01T00:00:00Z", valid_until=RE.NATIVE_NEAR_TERM_FEE_EXPIRY)):
        out = leg(s, policy=policy)
        assert out["status"] == "COST_INCONCLUSIVE" and out["fee_bound_usd"] is None and out["all_in_usd"] is None
    assert "FEE_CONFIG_UNKNOWN" in leg(snap(gamma={"feeSchedule": None}))["reasons"]
    assert leg(snap(gamma={"feesEnabled": None}))["reasons"] == ["FEE_CONFIG_UNKNOWN"]
    # 5 dp fee rounding is a ceiling, so the bound never underestimates the unrounded fee.
    out = leg(snap(asks=(("0.37", "50"),)), shares="7")
    unrounded = Decimal("7") * Decimal("0.02") * Decimal("0.37") * Decimal("0.63")
    assert Decimal(out["fee_unrounded_usd"]) == unrounded == Decimal("0.032634")
    assert out["fee_bound_usd"] == "0.03264" and unrounded.quantize(Decimal("0.00001"), rounding=ROUND_HALF_EVEN) < unrounded
    test_only = {"policy_id": "test-only-flat-2pct", "kind": "TEST_ONLY_HYPOTHETICAL", "valid_from": "2026-06-01T00:00:00Z",
                 "valid_until": "2026-06-02T00:00:00Z", "test_rate": "0.02", "test_exponent": 1}
    assert leg(snap(asks=(("0.37", "50"),)), shares="7", policy=test_only)["fee_exactness"] == "TEST_ONLY_CONSERVATIVE_5DP_UPPER_BOUND"
    # Quote, depth, clock, minimum, tick and structure dimensions.
    assert leg(snap(asks=()))["reasons"] == ["NO_ASKS"] and leg(None)["reasons"] == ["QUOTE_MISSING"]
    assert leg(snap(asks=(("0.45", "4"),)))["reasons"] == ["DEPTH_INSUFFICIENT"]
    assert "BOOK_STALE" in leg(snap(clob={"ts_ms": 1780315000000}))["reasons"]
    assert "BOOK_TIMESTAMP_INVALID" in leg(snap(clob={"ts_ms": 1780315199000}))["reasons"]
    assert "VENUE_EVIDENCE_AFTER_DECISION" in leg(snap(completed="2026-06-01T12:00:05Z"))["reasons"]
    assert leg(snap(asks=(("0.4", "50"),), gamma={"min_notional": "5"}))["reasons"] == ["MINIMUM_ORDER_NOTIONAL_NOT_MET"]
    assert leg(snap(asks=(("0.4", "50"),), clob={"min_shares": "15"}))["reasons"] == ["MINIMUM_ORDER_SHARES_NOT_MET"]
    assert leg(snap(asks=(("0.4", "50"),), gamma={"min_notional": "3"}, clob={"min_shares": "10"}))["status"] == "COST_KNOWN"
    off = leg(snap(asks=(("0.455", "50"),)))
    assert off["status"] == "NOT_EXECUTABLE" and "PRICE_OFF_TICK" in off["reasons"]
    neg = leg(snap(gamma={"neg_risk": True}, clob={"neg_risk": True}))
    assert neg["status"] == "NOT_EXECUTABLE" and neg["reasons"] == ["NEG_RISK_UNSUPPORTED"]
    assert leg(snap(gamma={"acceptingOrders": False}))["status"] == "NOT_EXECUTABLE"
    assert leg(s, binding="ORIENTATION_UNKNOWN")["status"] == "QUOTE_INCONCLUSIVE"
    # Basket-level: combos are unsupported; quote gaps are mechanically inconclusive; known costs stay conditional.
    good = [dict(leg(snap("oh-dem")), market_id="a", side="YES"), dict(leg(snap("oh-rep", asks=(("0.5", "50"),))), market_id="b", side="YES")]
    basket = RE.reference_baskets("COMPLEMENT", 2)[0]
    assert RE.assess_basket(basket, [[1, 0], [0, 1]], good, Decimal("10"), combo=True, fee_test_only=False)["status"] == "NOT_EXECUTABLE"
    missing = [good[0], dict(leg(None), market_id="b", side="YES")]
    assert RE.assess_basket(basket, [[1, 0], [0, 1]], missing, Decimal("10"), combo=False, fee_test_only=False)["status"] \
        == "MECHANICALLY_INCONCLUSIVE"
    tested = RE.assess_basket(basket, [[1, 0], [0, 1]], good, Decimal("10"), combo=False, fee_test_only=True)
    assert tested["status"] == "FEE_AND_DEPTH_CONDITIONAL" and tested["fee_basis"] == "TEST_ONLY_HYPOTHETICAL"
    assert tested["atomicity"] == "NOT_PROVEN_NO_NATIVE_MULTI_LEG_ROUTE" and tested["executable_edge"] is False
    # Integrated: with no fee source the same corpus never reaches an after-cost status.
    none = {"policy_id": "none", "kind": "NONE", "valid_from": None, "valid_until": None, "test_rate": None, "test_exponent": None}
    code, _, receipt = run_rel(tmp_path, world, build_request(world, fee_policy=none), name="nofee")
    assert code == 0
    statuses = [b["status"] for r in receipt["core"]["results"] for b in r["economics"]["baskets"]]
    assert "FEE_AND_DEPTH_CONDITIONAL" not in statuses and receipt["core"]["benchmark"]["fee_known_legs"] == 0
    v01 = {b["basket_id"]: b for b in rows(receipt)["v01"]["economics"]["baskets"]}
    assert v01["YES_BOTH"]["status"] == "THEORETICAL_PRICE_INCONSISTENCY" and "FEE_POLICY_ABSENT" in v01["YES_BOTH"]["reasons"]
    # Venue binding negatives are counted per entry, never silently dropped.
    venue = [dict(world["venue"][0]), dict(world["venue"][0], token_id="999999"), dict(world["venue"][1], market_id="market:polymarket:ghost"),
             dict(world["venue"][2], gamma_file=str(tmp_path / "absent.json"))]
    code, _, receipt = run_rel(tmp_path, world, build_request(world, venue=venue), name="venue-neg")
    assert code == 0
    counts = receipt["core"]["venue"]["counts"]
    assert counts == {"BOUND": 1, "VENUE_FILE_UNUSABLE": 1, "VENUE_IDENTITY_MISMATCH": 1, "VENUE_MARKET_NOT_IN_CORPUS": 1}
    duplicate = [world["venue"][0], world["venue"][0]]
    code, _, receipt = run_rel(tmp_path, world, build_request(world, venue=duplicate), name="venue-dup")
    assert receipt["core"]["venue"]["counts"] == {"BOUND": 1, "VENUE_DUPLICATE": 1}
    yes = {b["basket_id"]: b for b in rows(receipt)["v01"]["economics"]["baskets"]}["YES_BOTH"]
    assert "VENUE_DUPLICATE" in yes["legs"][0]["reasons"] and yes["status"] == "MECHANICALLY_INCONCLUSIVE"
