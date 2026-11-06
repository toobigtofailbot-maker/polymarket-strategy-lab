"""Rule-grounded related-market candidate discovery and formal payout proof (S10-R3-REL-01).

Pure, stdlib-only, read-only over native records. Candidates come ONLY from the native
``alpha_discovery.AlphaUniverseSnapshot`` (via the verified S10-R3-SRC-01 corpus); a caller
may bound the search and supply finite payout models for discovered candidates, never a
replacement pair list. Every result carries two independent classifications:

* ``formal``: an exhaustive bounded check of a caller-DECLARED finite payout model. Passing
  is ``FORMAL_BOUNDED_PAYOFF_PROOF`` with trust ``MODEL_CONDITIONAL_NOT_REAL_VERIFIED``.
* ``real_world``: what native evidence can say about actual settlement. Native PIT rules
  carry a rule-byte SHA-256 and source metadata but no formal resolver, so the strongest
  result here is ``INCONCLUSIVE_RULE_SEMANTICS`` (or mechanical identity / conflict).
  ``REAL_WORLD_RULE_VERIFIED`` is never emitted.

Method inspiration (ADAPT_ALGORITHM, no code copied, no dependency): Oracle3
``oracle3/arbitrage.py``@267fb7c (relation families), Oracle3 Extras
``kairos/settlement.py``@b2d807a (same/complement settlement compatibility, tie/cancel),
Chainstack ``implications.py``@1f4f366 (necessary-implication counterexample logic, an LLM
confidence is never proof), Synpath ``matcher.py``@c906cb3 (same / insufficient / not_same).
"""
from __future__ import annotations

from collections import Counter
from decimal import ROUND_HALF_EVEN, Decimal
from itertools import combinations, product
import re

from src.data_layer.analytical_research import alpha_discovery as AD
from src.data_layer.analytical_research import source_grounding as SG

RELATIONS = ("IMPLICATION", "EXCLUSIVITY", "COMPLEMENT", "SAME_EVENT", "EVENT_SUM")
GROUP_SIZE = {"IMPLICATION": (2, 2), "COMPLEMENT": (2, 2), "SAME_EVENT": (2, 2),
              "EXCLUSIVITY": (2, 4), "EVENT_SUM": (2, 4)}
SPECIAL_KINDS = ("TIE", "VOID", "CANCEL", "RESCHEDULE", "PARTIAL")
BINARY_OUTCOMES = ("No", "Yes")
GENERATORS = ("SHARED_CONDITION_ID", "SHARED_RECORDED_EVENT", "CATEGORY_QUESTION_TERMS")
BASELINE_ID = "baseline_native_relation_fields_v0"
BASELINE_MIN_SHARED_TERMS = 2
DISCOVERY_ID = "native_universe_relation_candidates_v1"
SOURCE_PINS = (
    {"capability": "R3-03", "repository": "YichengYang-Ethan/oracle3-prediction-market-agent",
     "commit": "267fb7c48dae7c4ff8922c02a3a223443e51bf0b", "path": "oracle3/arbitrage.py",
     "blob": "4805d572b55ce6547c9c46ab92a2aa4ce90de808", "adoption_mode": "ADAPT_ALGORITHM_NO_CODE_COPIED"},
    {"capability": "R3-03-FEES", "repository": "YichengYang-Ethan/oracle3-prediction-market-agent",
     "commit": "267fb7c48dae7c4ff8922c02a3a223443e51bf0b", "path": "oracle3/fees.py",
     "blob": "24624f84d40a43610302f7b8c3d17c347fa62e0c", "adoption_mode": "ADAPT_ALGORITHM_NO_CODE_COPIED"},
    {"capability": "R3-04", "repository": "YichengYang-Ethan/oracle3-extras",
     "commit": "b2d807a0513f37212623ecd3a9127af3ad506658", "path": "oracle3_extras/market/kairos/settlement.py",
     "blob": "acb2de215b43f879bddcdd7b5c163396859cf4de", "adoption_mode": "ADAPT_ALGORITHM_NO_CODE_COPIED"},
    {"capability": "R3-11", "repository": "chainstacklabs/polymarket-alpha-bot",
     "commit": "1f4f366b9c677574c8034a8720eaca917a53715b", "path": "backend/core/steps/implications.py",
     "blob": "27150d1857da9ff9ef3e2a9d738c469c591e9728", "adoption_mode": "ADAPT_ALGORITHM_NO_CODE_COPIED"},
    {"capability": "R3-19", "repository": "Synpath-ai/prediction-market-arbitrage-trading-bot",
     "commit": "c906cb36956945a291cb32a2d60a7455a0103a8f", "path": "src/matcher.py",
     "blob": "24de654e6c07c297416ea1b5e6f9de17f148432b", "adoption_mode": "ADAPT_ALGORITHM_NO_CODE_COPIED"},
)
_SHA_RE = re.compile(r"[0-9a-f]{64}")


class RelationStop(SG.GroundingStop):
    """Whole-run fail-closed stop; subclass so the legacy SRC-01 CLI handler also catches it."""


def ratio(numerator: int, denominator: int) -> dict:
    value = None if denominator == 0 else str((Decimal(numerator) / Decimal(denominator)).quantize(
        Decimal("0.000001"), rounding=ROUND_HALF_EVEN))
    return {"numerator": numerator, "denominator": denominator, "value": value}


# ------------------------------------------------------------------ native rule identity


def market_rule_status(market: AD.ObservedMarketState, bound: dict | None, pit_rule) -> dict:
    """Bind one market's rule identity to native PIT; a matching hash proves byte identity only."""
    out = {"market_id": market.market_id, "rule_content_sha256": None, "rule_record_version_id": None,
           "resolution_source_id": None, "rule_observed_time": None, "source_record_version_id": None,
           "ambiguity_labels": [], "source_hierarchy_rank": None, "human_review_state": None,
           "origin_authentication": "UNKNOWN_CALLER_LOCAL_BYTES"}
    gaps = set(market.data_gap_codes)
    if bound is None:
        out["status"] = "RULE_TEXT_UNBOUND"
        return out
    native = next(r for r in market.rules if r.rule_content_sha256 == bound["rule_content_sha256"])
    out.update(rule_content_sha256=bound["rule_content_sha256"], rule_record_version_id=native.rule_record_version_id,
               resolution_source_id=native.resolution_source_id, rule_observed_time=native.rule_observed_time,
               source_record_version_id=native.source_record_version_id)
    if pit_rule is None:
        out["status"] = "RULE_RECORD_MISSING"
        return out
    out.update(ambiguity_labels=sorted(pit_rule.ambiguity_labels), source_hierarchy_rank=pit_rule.source_hierarchy_rank,
               human_review_state=pit_rule.human_review_state)
    if (pit_rule.human_review_state == "REVIEWED_CONFLICT_UNRESOLVED" or "CONFLICTING_SOURCE_TEXT" in pit_rule.ambiguity_labels
            or gaps & {"RULE_EVIDENCE_CONFLICT", "SOURCE_EVIDENCE_CONFLICT"}):
        out["status"] = "RULE_CONFLICT"
    elif native.rule_freshness != "FRESH" or native.source_freshness != "FRESH":
        out["status"] = "RULE_STALE"
    elif (set(pit_rule.ambiguity_labels) != {"NONE_IDENTIFIED"} or pit_rule.source_hierarchy_rank != "PRIMARY_RESOLUTION_SOURCE"
          or pit_rule.human_review_state == "REVIEW_REQUIRED"):
        out["status"] = "RULE_AMBIGUOUS"
    else:
        out["status"] = "NATIVE_RULE_HASH_BOUND"
    return out


# ------------------------------------------------------------------ native candidate discovery


def _eligibility(market: AD.ObservedMarketState) -> str:
    if tuple(market.outcome_labels) != BINARY_OUTCOMES or len(market.token_ids) != 2:
        return "NONBINARY_UNSUPPORTED"
    if market.market_status != "open":
        return "STATUS_NOT_OPEN"
    if not market.question_text or "REQUIRED_METADATA_MISSING" in market.data_gap_codes:
        return "REQUIRED_METADATA_MISSING"
    if "METADATA_CONFLICT" in market.data_gap_codes or market.metadata_freshness != "FRESH":
        return "METADATA_STALE_OR_CONFLICTED"
    return "ELIGIBLE"


def candidate_key(relation: str, market_ids) -> str:
    ids = list(market_ids) if relation == "IMPLICATION" else sorted(market_ids)
    return relation + "|" + "|".join(ids)


def discover_candidates(universe: AD.AlphaUniverseSnapshot, search: dict) -> dict:
    """Propose LOW-confidence candidate groups from native fields only (never proof).

    Generators: identical native condition_id (mechanical identity), identical recorded
    (non condition-derived) event_id, and same native category with shared question terms.
    """
    families, max_size = set(search["families"]), search["max_group_size"]
    noncandidates: Counter = Counter()
    eligible = []
    for market in universe.markets:
        reason = _eligibility(market)
        if reason == "ELIGIBLE":
            eligible.append(market)
        else:
            noncandidates[reason] += 1
    found: dict[str, dict] = {}

    def propose(relation, ids, generator, overflow):
        if relation not in families:
            return
        key = candidate_key(relation, ids)
        if key in found:
            if generator not in found[key]["generators"]:
                found[key]["generators"].append(generator)
            return
        if len(found) >= search["max_candidates"]:
            overflow["CANDIDATE_CAP_EXCEEDED"] += 1
            return
        found[key] = {"candidate_key": key, "relation": relation, "market_ids": list(ids) if relation == "IMPLICATION" else sorted(ids),
                      "generators": [generator], "confidence": "LOW_CANDIDATE_ONLY_NOT_PROOF"}

    by_condition: dict[str, list] = {}
    by_event: dict[str, list] = {}
    for market in eligible:
        if market.condition_id:
            by_condition.setdefault(market.condition_id, []).append(market.market_id)
        if SG._event_identity(market) == "EVENT_ID_CONDITION_DERIVED":
            noncandidates["EVENT_ID_CONDITION_DERIVED_NOT_GROUPED"] += 1
        else:
            by_event.setdefault(market.event_id, []).append(market.market_id)
    for ids in by_condition.values():
        for pair in combinations(sorted(ids), 2):
            propose("SAME_EVENT", pair, "SHARED_CONDITION_ID", noncandidates)
    for ids in by_event.values():
        ids = sorted(ids)
        if len(ids) < 2:
            continue
        if len(ids) > max_size:
            noncandidates["EVENT_GROUP_TOO_LARGE_SPLIT_UNSUPPORTED"] += 1
            continue
        for relation in ("EXCLUSIVITY", "EVENT_SUM"):
            propose(relation, ids, "SHARED_RECORDED_EVENT", noncandidates)
        if len(ids) == 2:
            for relation in ("COMPLEMENT", "SAME_EVENT"):
                propose(relation, ids, "SHARED_RECORDED_EVENT", noncandidates)
            propose("IMPLICATION", ids, "SHARED_RECORDED_EVENT", noncandidates)
            propose("IMPLICATION", ids[::-1], "SHARED_RECORDED_EVENT", noncandidates)
    # shortcut: O(markets^2) pair scan, fine for bounded local stores; add a category index before large real stores.
    terms = {m.market_id: set(SG.tokenize(m.question_text)) for m in eligible}
    for a, b in combinations(sorted(eligible, key=lambda m: m.market_id), 2):
        if a.category and a.category == b.category and len(terms[a.market_id] & terms[b.market_id]) >= search["min_shared_terms"]:
            for relation, ids in (("SAME_EVENT", (a.market_id, b.market_id)), ("IMPLICATION", (a.market_id, b.market_id)),
                                  ("IMPLICATION", (b.market_id, a.market_id))):
                propose(relation, ids, "CATEGORY_QUESTION_TERMS", noncandidates)
    candidates = sorted(found.values(), key=lambda c: c["candidate_key"])
    return {"discovery_id": DISCOVERY_ID, "markets_total": len(universe.markets), "markets_eligible": len(eligible),
            "candidates": candidates, "generator_counts": dict(sorted(Counter(g for c in candidates for g in c["generators"]).items())),
            "noncandidate_counts": dict(sorted(noncandidates.items()))}


def baseline_native_relation_fields_v0(markets: list) -> bool:
    """New comparison baseline (not an existing verifier): 'related' iff every market shares the
    recorded event_id (condition-derived ids included, the naive weakness) or the same category
    with at least BASELINE_MIN_SHARED_TERMS shared question terms pairwise."""
    if len({m.event_id for m in markets}) == 1:
        return True
    if not markets[0].category or len({m.category for m in markets}) != 1:
        return False
    return all(len(set(SG.tokenize(a.question_text)) & set(SG.tokenize(b.question_text))) >= BASELINE_MIN_SHARED_TERMS
               for a, b in combinations(markets, 2))


# ------------------------------------------------------------------ formal payout proof


def _binary_row(row, n: int):
    """Strict 0/1 integers; anything else (0.5, "1", True) is not a supported binary payout."""
    if type(row) is not list or len(row) != n:
        return None, "MODEL_STATE_SHAPE_INVALID"
    if any(type(v) is not int or v not in (0, 1) for v in row):
        if all(type(v) in (int, float, str) and not isinstance(v, bool) for v in row):
            return None, "FRACTIONAL_OR_NONBINARY_PAYOUT_UNSUPPORTED"
        return None, "MODEL_STATE_SHAPE_INVALID"
    return tuple(row), None


def _violates(relation: str, state: tuple) -> bool:
    total = sum(state)
    if relation == "IMPLICATION":
        return state[0] == 1 and state[1] == 0
    if relation == "EXCLUSIVITY":
        return total > 1
    if relation in ("COMPLEMENT", "EVENT_SUM"):
        return total != 1
    return state[0] != state[1]  # SAME_EVENT


def formal_proof(relation: str, n: int, states, special_states) -> dict:
    """Exhaustively re-derive the relation over a declared finite YES-payout state model.

    Caller verdicts are never consulted. Unmodelled tie/void/cancel/reschedule/partial states
    keep the result inconclusive; fractional payouts are unsupported, not rounded.
    """
    low, high = GROUP_SIZE[relation]
    result = {"status": None, "trust": None, "states_admitted": [], "states_excluded": [], "counterexamples": [],
              "special_states": []}
    if not low <= n <= high:
        result["status"] = "GROUP_SIZE_UNSUPPORTED"
        return result
    if type(states) is not list or not states or len(states) > 2 ** n:
        result["status"] = "MODEL_STATE_SHAPE_INVALID"
        return result
    admitted = []
    for row in states:
        parsed, error = _binary_row(row, n)
        if error:
            result["status"] = error
            return result
        admitted.append(parsed)
    if len(set(admitted)) != len(admitted):
        result["status"] = "MODEL_DUPLICATE_STATE"
        return result
    unresolved = []
    if type(special_states) is not list or len(special_states) > len(SPECIAL_KINDS):
        result["status"] = "MODEL_STATE_SHAPE_INVALID"
        return result
    for special in special_states:
        if type(special) is not dict or set(special) != {"kind", "payout"} or special["kind"] not in SPECIAL_KINDS:
            result["status"] = "MODEL_STATE_SHAPE_INVALID"
            return result
        if special["payout"] is None:
            unresolved.append(special["kind"])
            result["special_states"].append({"kind": special["kind"], "payout": None, "status": "PAYOUT_SEMANTICS_UNKNOWN"})
            continue
        parsed, error = _binary_row(special["payout"], n)
        if error:
            result["special_states"].append({"kind": special["kind"], "payout": None, "status": error})
            unresolved.append(special["kind"])
            continue
        result["special_states"].append({"kind": special["kind"], "payout": list(parsed), "status": "MODELLED_BINARY"})
        if parsed not in admitted:
            admitted.append(parsed)
    every = list(product((0, 1), repeat=n))
    result["states_admitted"] = [list(s) for s in sorted(admitted)]
    result["states_excluded"] = [list(s) for s in every if s not in admitted]
    result["counterexamples"] = [list(s) for s in sorted(admitted) if _violates(relation, s)]
    if result["counterexamples"]:
        result["status"] = "FORMAL_COUNTEREXAMPLE"
        result["trust"] = "RELATION_FALSE_UNDER_DECLARED_MODEL"
    elif unresolved:
        result["status"] = "INCONCLUSIVE_SPECIAL_STATE_UNMODELLED"
    else:
        result["status"] = "FORMAL_BOUNDED_PAYOFF_PROOF"
        result["trust"] = "MODEL_CONDITIONAL_NOT_REAL_VERIFIED"
    return result


# ------------------------------------------------------------------ real-world classification


def real_world_classification(relation: str, markets: list, rule_rows: list, model: dict) -> dict:
    """What native evidence supports about actual settlement; never REAL_WORLD_RULE_VERIFIED."""
    reasons = []
    statuses = [r["status"] for r in rule_rows]
    claimed = model.get("claimed_rule_sha256")
    if claimed is not None:
        native = {r["rule_content_sha256"] for r in rule_rows}
        for row, digest in zip(rule_rows, claimed):
            if digest != row["rule_content_sha256"]:
                reasons.append("CROSS_MARKET_RULE_DIGEST" if digest in native else "FORGED_RULE_DIGEST")
    if model.get("cross_venue") is not None:
        status = "EXTERNAL_VENUE_UNVERIFIED"
    elif reasons or "RULE_CONFLICT" in statuses:
        status = "RULE_CONFLICT"
        if "RULE_CONFLICT" in statuses:
            reasons.append("NATIVE_RULE_CONFLICT")
    elif relation == "SAME_EVENT" and markets[0].condition_id and len({m.condition_id for m in markets}) == 1:
        status = "MECHANICAL_IDENTITY_NOT_INDEPENDENT"
    elif any(s in ("RULE_TEXT_UNBOUND", "RULE_RECORD_MISSING") for s in statuses):
        status = "INCONCLUSIVE_RULE_UNBOUND"
    elif any(s in ("RULE_AMBIGUOUS", "RULE_STALE") for s in statuses):
        status = "INCONCLUSIVE_RULE_AMBIGUOUS_OR_STALE"
    elif len(set(model["timezones"])) != 1 or (relation != "IMPLICATION" and len({m.resolution_date for m in markets}) != 1):
        status = "INCONCLUSIVE_TIME_WINDOW_MISMATCH"
    else:
        status = "INCONCLUSIVE_RULE_SEMANTICS"
        reasons.append("NATIVE_PIT_HAS_RULE_HASH_NOT_FORMAL_RESOLVER")
    return {"status": status, "reasons": sorted(set(reasons)), "real_world_rule_verified": False,
            "tradeable_equivalence_proven": False}
