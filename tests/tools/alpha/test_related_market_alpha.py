"""S10-R3-REL-01: native SRC-01/Alpha/PIT -> related candidates -> formal proof -> receipt -> cold verify.

The corpus, venue bodies and 49 benchmark models below are SANITIZED_SYNTHETIC and frozen inline.
They prove callable behaviour and honest accounting only: never real Alpha, real settlement
equivalence, executable arbitrage or profit.
"""
from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
import shutil
import socket

import pytest

from src.data_layer.analytical_research import alpha_discovery as AD
from src.data_layer.analytical_research import related_market as RM
from src.data_layer.analytical_research import source_grounding as SG
from tests.data_layer.analytical_research.test_alpha_discovery import _pit_built, _pit_store
from tools.alpha import run_related_market_alpha as REL
from tools.alpha import run_source_grounding as SGCLI

REPO_ROOT = Path(__file__).resolve().parents[3]
AS_OF = "2026-06-01T12:00:00Z"
DECISION = "2026-06-01T12:00:00Z"
OBSERVED, INGESTED = "2026-06-01T00:00:01Z", "2026-06-01T00:00:02Z"

# (slug, recorded event, category, question, resolution date, condition key, outcomes, status, rule review/ambiguity)
MARKETS = (
    ("oh-dem", "oh-senate", "politics", "Will the Democratic candidate win the 2026 Ohio Senate race?", "2026-11-03", None, None, "open", None),
    ("oh-rep", "oh-senate", "politics", "Will the Republican candidate win the 2026 Ohio Senate race?", "2026-11-03", None, None, "open", None),
    ("fed-cut", "fed-sep", "economics", "Will the Fed cut rates at the September 2026 meeting?", "2026-09-17", None, None, "open", None),
    ("fed-hold", "fed-sep", "economics", "Will the Fed hold rates at the September 2026 meeting?", "2026-09-17", None, None, "open", None),
    ("nba-cel", "nba-finals", "sports", "Will the Celtics win the 2026 NBA Finals?", "2026-06-30", None, None, "open", None),
    ("nba-okc", "nba-finals", "sports", "Will the Thunder win the 2026 NBA Finals?", "2026-06-30", None, None, "open", None),
    ("nba-nyk", "nba-finals", "sports", "Will the Knicks win the 2026 NBA Finals?", "2026-06-30", None, None, "open", None),
    ("wc-bra", "world-cup", "soccer", "Will Brazil win the 2026 World Cup?", "2026-07-19", None, None, "open", None),
    ("wc-fra", "world-cup", "soccer", "Will France win the 2026 World Cup?", "2026-07-19", None, None, "open", None),
    ("wc-esp", "world-cup", "soccer", "Will Spain win the 2026 World Cup?", "2026-07-19", None, None, "open", None),
    ("wc-arg", "world-cup", "soccer", "Will Argentina win the 2026 World Cup?", "2026-07-19", None, None, "open", None),
    ("osc-a", "oscars", "film", "Will film A win Best Picture?", "2027-03-15", None, None, "open", None),
    ("osc-b", "oscars", "film", "Will film B win Best Picture?", "2027-03-15", None, None, "open", None),
    ("osc-c", "oscars", "film", "Will film C win Best Picture?", "2027-03-15", None, None, "open", None),
    ("osc-d", "oscars", "film", "Will film D win Best Picture?", "2027-03-15", None, None, "open", None),
    ("osc-e", "oscars", "film", "Will film E win Best Picture?", "2027-03-15", None, None, "open", None),
    ("btc-100k", "btc-100k", "crypto", "Will Bitcoin trade above 100k by December 2026?", "2026-12-31", None, None, "open", None),
    ("btc-80k", "btc-80k", "crypto", "Will Bitcoin trade above 80k by December 2026?", "2026-12-31", None, None, "open", None),
    ("eth-5k", "eth-5k", "ether", "Will Ether close above 5k in December 2026?", "2026-12-31", None, None, "open", None),
    ("eth-3k", "eth-3k", "ether", "Will Ether close above 3k in December 2026?", "2026-12-31", None, None, "open", None),
    ("temp-a", "temp-a", "weather", "Central Park July 4 high above 95F (listing A)", "2026-07-05", "temp-shared", None, "open", None),
    ("temp-b", "temp-b", "weather", "Duplicate listing B for the July 4 Central Park heat market", "2026-07-05", "temp-shared", None, "open", None),
    ("nyc-cp", "nyc-cp", "climate", "Will Central Park record a high above 95F on July 4 2026?", "2026-07-05", None, None, "open", None),
    ("nyc-lga", "nyc-lga", "climate", "Will LaGuardia record a high above 95F on July 4 2026?", "2026-07-05", None, None, "open", None),
    ("conf-a", "conf-event", "law", "Will the court rule for the plaintiff?", "2026-10-01", None, None, "open", "CONFLICT"),
    ("conf-b", "conf-event", "law", "Will the court rule for the defendant?", "2026-10-01", None, None, "open", None),
    ("amb-a", "amb-event", "space", "Will the launch happen in Q3?", "2026-09-30", None, None, "open", "AMBIGUOUS"),
    ("amb-b", "amb-event", "space", "Will the launch slip past Q3?", "2026-09-30", None, None, "open", None),
    ("tri", "tri-event", "misc", "Which of three outcomes happens?", "2026-12-31", None, ["A", "B", "C"], "open", None),
    ("closed-x", "closed-event", "misc", "Already closed market X", "2026-01-01", None, None, "closed", None),
    ("closed-y", "closed-event", "misc", "Already closed market Y", "2026-01-01", None, None, "closed", None),
    ("cond-derived", None, "misc", "Market with a condition-derived event id", "2026-12-31", None, None, "open", None),
)
NO_RULE = {"amb-b"}


def _mid(slug):
    return f"market:polymarket:{slug}"


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _condition(row):
    return "0x" + _sha((row[5] or row[0]).encode())


def _tokens(slug):
    index = [m[0] for m in MARKETS].index(slug)
    return str(10_000 + 2 * index), str(10_001 + 2 * index)  # (no, yes)


def _rule_text(slug):
    return f"Synthetic rule for {slug}: resolves YES only per the named primary source; otherwise NO.".encode()


def _policy_mapping():
    return {"schema_version": "1.0.0", "policy_version": "rel01-fixture/1", "eligible_market_statuses": ["open"],
            "metadata_freshness_seconds": 86400, "order_book_freshness_seconds": 30,
            "resolution_rule_freshness_seconds": 86400, "soft_last_trade_price_abs_delta": "0.1",
            "soft_mid_price_abs_delta": "0.1", "soft_spread_abs_delta": "0.05", "soft_top_depth_relative_delta": "0.25",
            "queue_capacity": 4, "exploration_slots": 1, "audit_slots": 1, "max_per_category": 2,
            "audit_seed": "rel01-seed", "research_archetype_taxonomy_version": "alpha-archetypes/1",
            "advisory_only": True, "no_execution_authority": True, "no_strategy_authority": True,
            "no_qualification_authority": True}


def _pit_records():
    records = []
    times = dict(observed_time=OBSERVED, ingestion_time=INGESTED)
    for row in MARKETS:
        slug, event, category, question, date, _cond, outcomes, status, review = row
        no, yes = _tokens(slug)
        labels = outcomes or ["No", "Yes"]
        tokens = [f"token:polymarket:{no}", f"token:polymarket:{yes}"] + ([f"token:polymarket:{int(yes) + 90000}"] if outcomes else [])
        event_id = f"event:polymarket:{_condition(row)}" if event is None else f"event:polymarket:synthetic-{event}"
        payload = {"market_status": status, "outcome_labels": labels, "question_text": question, "token_ids": tokens,
                   "condition_id": _condition(row), "category": category, "resolution_date": date + "T00:00:00Z"}
        meta, _ = _pit_built("PIT-C01-VALID-MARKET-METADATA", platform_id="platform:polymarket", event_id=event_id,
                             market_id=_mid(slug), source_id="source:polymarket:gamma-markets",
                             source_assertion_id=f"assertion:rel01:meta:{slug}", snapshot_id=f"snapshot:rel01:meta:{slug}",
                             source_snapshot_id=f"source-snapshot:rel01:meta:{slug}", event_time="2026-06-01T00:00:00Z",
                             canonical_payload=payload, **times)
        records.append(meta)
        if slug in NO_RULE:
            continue
        source, _ = _pit_built("PIT-C04-VALID-SOURCE-SNAPSHOT", source_id=f"source:rel01:rules:{slug}",
                               snapshot_id=f"snapshot:rel01:rulesrc:{slug}", **times)
        extra = {"CONFLICT": dict(human_review_state="REVIEWED_CONFLICT_UNRESOLVED"),
                 # Native standard builders refuse ambiguity labels, so a non-primary source rank is the native ambiguity.
                 "AMBIGUOUS": dict(source_hierarchy_rank="SECONDARY_OFFICIAL_SOURCE")}.get(review, {})
        rule, _ = _pit_built("PIT-C05-VALID-RESOLUTION-RULE-SNAPSHOT", platform_id="platform:polymarket", event_id=event_id,
                             market_id=_mid(slug), resolution_source_id="resolution-source:polymarket:primary",
                             source_snapshot_id=source.envelope.source_snapshot_id, rule_content_sha256=_sha(_rule_text(slug)),
                             snapshot_id=f"snapshot:rel01:rule:{slug}", observed_time="2026-06-01T00:00:03Z",
                             ingestion_time="2026-06-01T00:00:04Z", **extra)
        records.extend((source, rule))
    return records


def gamma_body(slug, *, fees=True, rate="0.02", neg_risk=False, tick="0.01", min_notional="1", **overrides):
    no, yes = _tokens(slug)
    row = next(m for m in MARKETS if m[0] == slug)
    body = {"id": str(500 + [m[0] for m in MARKETS].index(slug)), "conditionId": _condition(row),
            "clobTokenIds": json.dumps([yes, no]), "outcomes": json.dumps(["Yes", "No"]), "active": True, "closed": False,
            "acceptingOrders": True, "enableOrderBook": True, "restricted": False, "negRisk": neg_risk,
            "orderPriceMinTickSize": tick, "orderMinSize": min_notional, "feesEnabled": fees,
            "feeSchedule": {"rate": rate, "exponent": 1, "takerOnly": True}, "secondsDelay": 0}
    body.update(overrides)
    return json.dumps(body).encode()


def clob_body(slug, side, asks, *, ts_ms=None, neg_risk=False, tick="0.01", min_shares="1", bids=()):
    no, yes = _tokens(slug)
    row = next(m for m in MARKETS if m[0] == slug)
    ts = ts_ms if ts_ms is not None else 1780315195000  # 2026-06-01T11:59:55Z
    return json.dumps({"market": _condition(row), "asset_id": yes if side == "YES" else no, "timestamp": str(ts), "hash": "abc123",
                       "bids": [{"price": p, "size": s} for p, s in bids], "asks": [{"price": p, "size": s} for p, s in asks],
                       "min_order_size": min_shares, "tick_size": tick, "neg_risk": neg_risk, "last_trade_price": "0.5"}).encode()


# Integrated venue evidence: (slug, side, asks, clob overrides, gamma overrides)
VENUE = (
    ("oh-dem", "YES", [("0.45", "50")], {}, {}), ("oh-rep", "YES", [("0.5", "50")], {}, {}),
    ("oh-dem", "NO", [("0.56", "50")], {}, {}), ("oh-rep", "NO", [("0.52", "50")], {}, {}),
    ("btc-100k", "NO", [("0.3", "2")], {}, {}), ("btc-80k", "YES", [("0.6", "50")], {}, {}),
    ("btc-100k", "YES", [("0.7", "50")], {}, {}),
    ("wc-bra", "YES", [("0.2", "50")], {}, {}), ("wc-fra", "YES", [("0.25", "50")], {}, {}),
    ("wc-esp", "YES", [("0.3", "50")], {"ts_ms": 1780310000000}, {}), ("wc-arg", "YES", [("0.2", "50")], {}, {}),
    ("fed-cut", "NO", [("0.4", "50")], {"neg_risk": True}, {"neg_risk": True}), ("fed-hold", "NO", [("0.4", "50")], {}, {}),
)

S = [[1, 0], [0, 1]]
ONE_HOT3, ONE_HOT4 = [[1, 0, 0], [0, 1, 0], [0, 0, 1]], [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]]
IMPL = [[0, 0], [0, 1], [1, 1]]


def _m(mid, relation, slugs, states, expected, special=(), tz=None, **extra):
    model = {"model_id": mid, "relation": relation, "market_ids": [_mid(s) for s in slugs], "states": states,
             "special_states": [{"kind": k, "payout": p} for k, p in special], "timezones": tz or ["UTC"] * len(slugs),
             "yes_token_ids": None, "claimed_rule_sha256": None, "claimed_verdict": None, "cross_venue": None, "combo": False,
             "expected": expected}
    model.update(extra)
    return model


OH, FED, NBA, WC = ["oh-dem", "oh-rep"], ["fed-cut", "fed-hold"], ["nba-cel", "nba-okc", "nba-nyk"], ["wc-bra", "wc-fra", "wc-esp", "wc-arg"]
MODELS = [
    _m("v01", "COMPLEMENT", OH, S, "FORMAL_VALID"),
    _m("v02", "EXCLUSIVITY", FED, [[0, 0], [1, 0], [0, 1]], "FORMAL_VALID"),
    _m("v03", "EXCLUSIVITY", NBA, ONE_HOT3 + [[0, 0, 0]], "FORMAL_VALID"),
    _m("v04", "EVENT_SUM", WC, ONE_HOT4, "FORMAL_VALID"),
    _m("v05", "IMPLICATION", ["btc-100k", "btc-80k"], IMPL, "FORMAL_VALID"),
    _m("v06", "SAME_EVENT", ["temp-a", "temp-b"], [[0, 0], [1, 1]], "FORMAL_VALID"),
    _m("v07", "EVENT_SUM", OH, S, "FORMAL_VALID"),
    _m("v08", "EXCLUSIVITY", OH, S, "FORMAL_VALID"),
    _m("v09", "EXCLUSIVITY", WC, ONE_HOT4, "FORMAL_VALID"),
    _m("v10", "IMPLICATION", ["eth-5k", "eth-3k"], IMPL, "FORMAL_VALID"),
    # Formally valid ONLY under the caller's incomplete declared model (a hike is omitted): conditional, not real.
    _m("v11", "COMPLEMENT", FED, S, "FORMAL_VALID"),
    _m("v12", "SAME_EVENT", ["temp-a", "temp-b"], [[0, 0], [1, 1]], "FORMAL_VALID", tz=["UTC", "America/New_York"]),
    _m("v13", "IMPLICATION", ["btc-100k", "btc-80k"], IMPL, "FORMAL_VALID", special=[("TIE", [0, 0])]),
    _m("v14", "EXCLUSIVITY", NBA, ONE_HOT3, "FORMAL_VALID", special=[("VOID", [0, 0, 0])]),
    _m("v15", "EVENT_SUM", NBA, ONE_HOT3, "FORMAL_VALID"),
    _m("c01", "IMPLICATION", ["btc-80k", "btc-100k"], [[0, 0], [1, 0], [1, 1]], "COUNTEREXAMPLE"),
    _m("c02", "COMPLEMENT", FED, [[0, 0], [1, 0], [0, 1]], "COUNTEREXAMPLE"),
    _m("c03", "EVENT_SUM", NBA, ONE_HOT3 + [[0, 0, 0]], "COUNTEREXAMPLE"),
    _m("c04", "EXCLUSIVITY", OH, S + [[1, 1]], "COUNTEREXAMPLE"),
    _m("c05", "SAME_EVENT", ["nyc-cp", "nyc-lga"], [[0, 0], [1, 1], [1, 0]], "COUNTEREXAMPLE"),
    _m("c06", "IMPLICATION", ["eth-3k", "eth-5k"], [[0, 0], [1, 0], [1, 1]], "COUNTEREXAMPLE"),
    _m("c07", "EVENT_SUM", WC, ONE_HOT4 + [[0, 0, 0, 0]], "COUNTEREXAMPLE"),
    _m("c08", "COMPLEMENT", OH, S, "COUNTEREXAMPLE", special=[("TIE", [0, 0])]),
    _m("c09", "SAME_EVENT", ["btc-100k", "btc-80k"], IMPL, "COUNTEREXAMPLE"),
    _m("c10", "IMPLICATION", ["eth-3k", "eth-5k"], [[1, 0]], "COUNTEREXAMPLE", claimed_verdict=True),
    _m("c11", "EVENT_SUM", WC, ONE_HOT4, "COUNTEREXAMPLE", special=[("CANCEL", [0, 0, 0, 0])]),
    _m("i01", "COMPLEMENT", OH, S, "INCONCLUSIVE", special=[("TIE", None)]),
    _m("i02", "EXCLUSIVITY", NBA, ONE_HOT3, "INCONCLUSIVE", special=[("VOID", None)]),
    _m("i03", "IMPLICATION", ["btc-100k", "btc-80k"], IMPL, "INCONCLUSIVE", special=[("CANCEL", None)]),
    _m("i04", "SAME_EVENT", ["temp-a", "temp-b"], [[0.5, 0.5]], "INCONCLUSIVE"),
    _m("i05", "EVENT_SUM", WC, ONE_HOT4, "INCONCLUSIVE", special=[("PARTIAL", ["0.5", "0.5", 0, 0])]),
    _m("i06", "EXCLUSIVITY", FED, [[0, 0], [1, 0], [0, 1]], "INCONCLUSIVE", cross_venue="kalshi-claimed"),
    _m("i07", "IMPLICATION", ["eth-5k", "eth-3k"], IMPL, "INCONCLUSIVE", special=[("RESCHEDULE", None)]),
    _m("r01", "COMPLEMENT", ["conf-a", "conf-b"], S, "RULE_CONFLICT"),
    _m("r02", "COMPLEMENT", OH, S, "RULE_CONFLICT", claimed_rule_sha256=["f" * 64, _sha(_rule_text("oh-rep"))]),
    _m("r03", "COMPLEMENT", OH, S, "RULE_CONFLICT", claimed_rule_sha256=[_sha(_rule_text("oh-rep")), _sha(_rule_text("oh-rep"))]),
    _m("r04", "IMPLICATION", ["btc-100k", "btc-80k"], IMPL, "RULE_CONFLICT",
       yes_token_ids=[f"token:polymarket:{_tokens('btc-100k')[0]}", f"token:polymarket:{_tokens('btc-80k')[1]}"]),
    _m("n01", "IMPLICATION", ["fed-cut", "wc-bra"], IMPL, "NOT_NATIVE_CANDIDATE"),
    _m("n02", "COMPLEMENT", ["oh-dem", "ghost"], S, "NOT_NATIVE_CANDIDATE"),
    _m("n03", "EXCLUSIVITY", ["oh-dem", "oh-dem"], S, "NOT_NATIVE_CANDIDATE"),
    _m("n04", "EVENT_SUM", ["osc-a", "osc-b", "osc-c", "osc-d"], ONE_HOT4, "NOT_NATIVE_CANDIDATE"),
    _m("n05", "COMPLEMENT", ["tri", "oh-dem"], S, "NOT_NATIVE_CANDIDATE"),
    _m("n06", "SAME_EVENT", ["closed-x", "closed-y"], [[0, 0], [1, 1]], "NOT_NATIVE_CANDIDATE"),
    _m("n07", "EXCLUSIVITY", ["nyc-cp", "nyc-lga"], [[0, 0], [1, 0], [0, 1]], "NOT_NATIVE_CANDIDATE"),
    _m("x01", "IMPLICATION", NBA, ONE_HOT3, "MODEL_INVALID"),
    _m("x02", "COMPLEMENT", OH, S + [[1, 0]], "MODEL_INVALID"),
    _m("x03", "COMPLEMENT", OH, [[1, 0, 0]], "MODEL_INVALID"),
    _m("x04", "CORRELATION", OH, S, "MODEL_INVALID"),
    _m("x05", "COMPLEMENT", OH, [[True, False]], "MODEL_INVALID"),
]
SEARCH = {"families": list(RM.RELATIONS), "max_group_size": 4, "min_shared_terms": 4, "max_candidates": 200}
GAMMA_FEES = {"policy_id": "gamma-body-fees-20260601", "kind": "GAMMA_BODY_PER_MARKET",
              "valid_from": "2026-06-01T00:00:00Z", "valid_until": "2026-06-02T00:00:00Z", "test_rate": None, "test_exponent": None}
CORPUS_SHA256 = "244756ff9f45cb16c10d0b96cb342df8a9f2590f0d4a2301663733bc6507f312"


def corpus_sha256():
    frozen = {"markets": [list(m) for m in MARKETS], "venue": [list(v[:3]) + [v[3], v[4]] for v in VENUE], "models": MODELS}
    return _sha(SG.canonical_bytes(frozen))


def build_request(world, *, models=None, fee_policy=None, venue=None, corpus_class="SANITIZED_SYNTHETIC", **overrides):
    request = {"schema_id": REL.REQUEST_SCHEMA, "request_label": "rel01-synthetic", "corpus_class": corpus_class,
               "decision_time": DECISION, "max_book_age_seconds": 60, "basket_shares": "10", "search": dict(SEARCH),
               "fee_policy": dict(fee_policy or GAMMA_FEES), "models": json.loads(json.dumps(models or MODELS)),
               "venue": world["venue"] if venue is None else venue, "benchmark_sha256": "0" * 64}
    request.update(overrides)
    request["benchmark_sha256"] = REL.benchmark_commitment(request)
    return request


def _venue_entry(put, number, slug, side, asks, clob_extra, gamma_extra):
    no, yes = _tokens(slug)
    gamma = put(f"gamma-{number:03d}.json", gamma_body(slug, **gamma_extra))
    clob = put(f"clob-{number:03d}.json", clob_body(slug, side, asks, **clob_extra))
    return {"market_id": _mid(slug), "gamma_market_id": str(500 + [m[0] for m in MARKETS].index(slug)),
            "token_id": yes if side == "YES" else no, "gamma_file": str(gamma), "clob_file": str(clob),
            "acquisition_started": "2026-06-01T11:59:56Z", "acquisition_completed": "2026-06-01T11:59:57Z"}


def make_world(base, corpus_class="SANITIZED_SYNTHETIC"):
    base.mkdir(parents=True, exist_ok=True)
    pit = _pit_store(base, _pit_records())

    def put(name, data):
        path = (base / name).resolve()
        path.write_bytes(data)
        return path
    rule_entries = [{"market_id": _mid(m[0]), "file": str(put(f"rule-{m[0]}.txt", _rule_text(m[0])))}
                    for m in MARKETS if m[0] not in NO_RULE]
    case = {"schema_id": SG.CASE_SCHEMA, "case_label": "rel01-grounding", "corpus_class": corpus_class, "pit_store": str(pit),
            "alpha_registry": None, "policy": _policy_mapping(), "as_of": AS_OF, "rule_texts": rule_entries, "sources": [],
            "queries": [{"query_id": "q01", "text": "Ohio Senate race", "category_hint": "politics",
                         "relevant_market_ids": [_mid("oh-dem"), _mid("oh-rep")]}]}
    case_path = put("grounding-case.json", json.dumps(case).encode())
    grounding = (base / "grounding").resolve()
    assert SGCLI.main(["run", "--case", str(case_path), "--scratch-dir", str(grounding)]) == 0
    venue = [_venue_entry(put, i, *v) for i, v in enumerate(VENUE)]
    return {"base": base, "pit": pit, "grounding": grounding, "venue": venue, "put": put}


def run_rel(tmp_path, world, request, name="rel"):
    req = tmp_path / f"{name}-request.json"
    req.write_text(json.dumps(request), encoding="utf-8")
    scratch = (tmp_path / name).resolve()
    code = REL.main(["run", "--grounding-scratch", str(world["grounding"]), "--request-file", str(req),
                     "--scratch-dir", str(scratch)])
    path = scratch / "receipt.json"
    return code, scratch, json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def last_output(capsys):
    return json.loads(capsys.readouterr().out.strip().splitlines()[-1])


@pytest.fixture(scope="module")
def world(tmp_path_factory):
    return make_world(tmp_path_factory.mktemp("rel01_inputs"))


@pytest.fixture(scope="module")
def baseline(world, tmp_path_factory):
    tmp = tmp_path_factory.mktemp("rel01_run")
    code, scratch, receipt = run_rel(tmp, world, build_request(world))
    assert code == 0, receipt
    return scratch, receipt


def rows(receipt):
    return {r["model_id"]: r for r in receipt["core"]["results"]}


# ------------------------------------------------------------------ R001


def test_rel_native_src01_call_path_and_candidate_generation(world, baseline, tmp_path, monkeypatch):
    calls = {"discover": 0, "verify": 0}
    real_discover, real_verify = RM.discover_candidates, SGCLI.verify
    monkeypatch.setattr(RM, "discover_candidates", lambda *a: calls.__setitem__("discover", calls["discover"] + 1) or real_discover(*a))
    monkeypatch.setattr(SGCLI, "verify", lambda s: calls.__setitem__("verify", calls["verify"] + 1) or real_verify(s))
    code, _, receipt = run_rel(tmp_path, world, build_request(world))
    assert code == 0 and calls == {"discover": 1, "verify": 1}
    core = receipt["core"]
    policy = AD.build_alpha_discovery_policy(_policy_mapping()).record
    native = AD.build_alpha_universe_snapshot(world["pit"], policy, AS_OF).record
    assert core["inputs"]["alpha_universe_snapshot_id"] == native.alpha_universe_snapshot_id
    assert core["inputs"]["grounding_verification"] == "VERIFIED"
    assert core["inputs"]["grounding_receipt_id"] == json.loads((world["grounding"] / "receipt.json").read_text())["receipt_id"]
    assert core["corpus"]["market_ids"] == sorted(m.market_id for m in native.markets)
    discovery = core["discovery"]
    keys = {c["candidate_key"]: c for c in discovery["candidates"]}
    # Native discovery proposes candidates from all three generators; the caller supplied none of them.
    assert set(discovery["generator_counts"]) == set(RM.GENERATORS)
    assert keys[RM.candidate_key("SAME_EVENT", [_mid("temp-a"), _mid("temp-b")])]["generators"][0] == "SHARED_CONDITION_ID"
    assert "SHARED_RECORDED_EVENT" in keys[RM.candidate_key("EVENT_SUM", [_mid(s) for s in WC])]["generators"]
    assert keys[RM.candidate_key("IMPLICATION", [_mid("btc-100k"), _mid("btc-80k")])]["generators"] == ["CATEGORY_QUESTION_TERMS"]
    assert all(c["confidence"] == "LOW_CANDIDATE_ONLY_NOT_PROOF" for c in discovery["candidates"])
    assert set(m for c in discovery["candidates"] for m in c["market_ids"]) <= set(core["corpus"]["market_ids"])
    counts = discovery["noncandidate_counts"]
    assert counts["NONBINARY_UNSUPPORTED"] == 1 and counts["STATUS_NOT_OPEN"] == 2
    assert counts["EVENT_GROUP_TOO_LARGE_SPLIT_UNSUPPORTED"] == 1  # 5-market oscars event is not silently split
    assert counts["EVENT_ID_CONDITION_DERIVED_NOT_GROUPED"] == 1 and core["corpus"]["event_id_condition_derived"] == 1
    v05 = rows(receipt)["v05"]
    assert v05["native_candidate_key"] and v05["native_generators"] == ["CATEGORY_QUESTION_TERMS"]
    assert [r["market_id"] for r in v05["rules"]] == [_mid("btc-100k"), _mid("btc-80k")]
    assert rows(receipt)["n01"]["status"] == "NOT_NATIVE_CANDIDATE"  # a caller pair alone never becomes a candidate
    # Bounded caller search parameters only narrow the native generator.
    narrow = build_request(world, search=dict(SEARCH, families=["EVENT_SUM"]))
    code, _, other = run_rel(tmp_path, world, narrow, name="narrow")
    assert code == 0 and {c["relation"] for c in other["core"]["discovery"]["candidates"]} == {"EVENT_SUM"}


# ------------------------------------------------------------------ R002


def test_rel_hash_bound_rule_semantics_and_orientation(baseline):
    _, receipt = baseline
    core, by = receipt["core"], rows(receipt)
    rules = {r["market_id"]: r for r in core["corpus"]["rules"]}
    oh = rules[_mid("oh-dem")]
    assert oh["status"] == "NATIVE_RULE_HASH_BOUND" and oh["rule_content_sha256"] == _sha(_rule_text("oh-dem"))
    assert oh["rule_record_version_id"].startswith("record:sha256:") and oh["resolution_source_id"].endswith(":primary")
    assert oh["source_hierarchy_rank"] == "PRIMARY_RESOLUTION_SOURCE" and oh["ambiguity_labels"] == ["NONE_IDENTIFIED"]
    assert oh["origin_authentication"] == "UNKNOWN_CALLER_LOCAL_BYTES"  # a hash proves byte identity only
    assert rules[_mid("conf-a")]["status"] == "RULE_CONFLICT" and rules[_mid("amb-a")]["status"] == "RULE_AMBIGUOUS"
    assert rules[_mid("amb-b")]["status"] == "RULE_TEXT_UNBOUND"
    # Every evaluated candidate keeps BOTH the formal result and a non-verified real-world class.
    for row in by.values():
        if row["real_world"]:
            assert row["real_world"]["real_world_rule_verified"] is False
            assert row["real_world"]["tradeable_equivalence_proven"] is False
    assert by["v01"]["real_world"]["status"] == "INCONCLUSIVE_RULE_SEMANTICS"
    assert by["v01"]["real_world"]["reasons"] == ["NATIVE_PIT_HAS_RULE_HASH_NOT_FORMAL_RESOLVER"]
    assert by["v06"]["real_world"]["status"] == "MECHANICAL_IDENTITY_NOT_INDEPENDENT"
    assert by["r01"]["real_world"]["status"] == "RULE_CONFLICT" and by["r01"]["disposition"] == "RULE_CONFLICT"
    assert by["r02"]["real_world"]["reasons"] == ["FORGED_RULE_DIGEST"]
    assert by["r03"]["real_world"]["reasons"] == ["CROSS_MARKET_RULE_DIGEST"]
    assert by["r04"]["real_world"]["reasons"] == ["ORIENTATION_CONTRADICTED"]  # Gamma outcome order disagrees
    assert by["i06"]["real_world"]["status"] == "EXTERNAL_VENUE_UNVERIFIED" and by["i06"]["disposition"] == "INCONCLUSIVE"
    assert by["v12"]["real_world"]["status"] == "MECHANICAL_IDENTITY_NOT_INDEPENDENT"
    # Time-window mismatch: same pair with different deadlines stays inconclusive in the unit classifier.
    a, b = (AD.ObservedMarketState(_mid(x), f"event:polymarket:e{x}", "open", None, (), ("No", "Yes"), d, "c", "q",
                                   "record:sha256:" + "a" * 64, OBSERVED, "FRESH", "a" * 64, "b" * 64, "c" * 64, (), (), ())
            for x, d in (("p", "2026-01-01T00:00:00Z"), ("q", "2026-02-01T00:00:00Z")))
    good = {"status": "NATIVE_RULE_HASH_BOUND", "rule_content_sha256": "1" * 64}
    model = {"timezones": ["UTC", "UTC"], "claimed_rule_sha256": None, "cross_venue": None}
    assert RM.real_world_classification("COMPLEMENT", [a, b], [good, dict(good, rule_content_sha256="2" * 64)], model)["status"] \
        == "INCONCLUSIVE_TIME_WINDOW_MISMATCH"
    assert RM.real_world_classification("IMPLICATION", [a, b], [good, good], dict(model, timezones=["UTC", "Europe/London"]))["status"] \
        == "INCONCLUSIVE_TIME_WINDOW_MISMATCH"
    vocab = {r["real_world"]["status"] for r in by.values() if r["real_world"]}
    assert "REAL_WORLD_RULE_VERIFIED" not in vocab and core["benchmark"]["real_world_verified"] == 0


# ------------------------------------------------------------------ R003


def test_rel_exhaustive_truth_tables_and_counterexamples(baseline):
    by = rows(baseline[1])
    assert by["c01"]["formal"]["counterexamples"] == [[1, 0]]  # wrong implication direction
    assert by["c02"]["formal"]["counterexamples"] == [[0, 0]]
    assert by["c03"]["formal"]["counterexamples"] == [[0, 0, 0]]
    assert by["c04"]["formal"]["counterexamples"] == [[1, 1]]
    assert by["c05"]["formal"]["counterexamples"] == [[1, 0]]
    assert by["c08"]["formal"]["counterexamples"] == [[0, 0]]  # a modelled tie breaks the complement
    assert by["c10"]["formal"]["status"] == "FORMAL_COUNTEREXAMPLE" and by["c10"]["claimed_verdict_ignored"] is True
    assert by["c11"]["formal"]["special_states"] == [{"kind": "CANCEL", "payout": [0, 0, 0, 0], "status": "MODELLED_BINARY"}]
    v05 = by["v05"]["formal"]
    assert v05["status"] == "FORMAL_BOUNDED_PAYOFF_PROOF" and v05["trust"] == "MODEL_CONDITIONAL_NOT_REAL_VERIFIED"
    assert v05["states_admitted"] == [[0, 0], [0, 1], [1, 1]] and v05["states_excluded"] == [[1, 0]]
    for mid in ("i01", "i02", "i03", "i07"):
        assert by[mid]["formal"]["status"] == "INCONCLUSIVE_SPECIAL_STATE_UNMODELLED"
    assert by["i04"]["formal"]["status"] == "FRACTIONAL_OR_NONBINARY_PAYOUT_UNSUPPORTED"
    assert by["i05"]["formal"]["special_states"][0]["status"] == "FRACTIONAL_OR_NONBINARY_PAYOUT_UNSUPPORTED"
    assert by["x01"]["formal"]["status"] == "GROUP_SIZE_UNSUPPORTED" and by["x02"]["formal"]["status"] == "MODEL_DUPLICATE_STATE"
    assert by["x05"]["formal"]["status"] == "MODEL_STATE_SHAPE_INVALID" and by["x04"]["status"] == "MODEL_FIELDS_INVALID"
    # Exhaustive truth tables for every family and n, independent of any caller verdict.
    for relation in RM.RELATIONS:
        low, high = RM.GROUP_SIZE[relation]
        for n in range(low, high + 1):
            for state in __import__("itertools").product((0, 1), repeat=n):
                result = RM.formal_proof(relation, n, [list(state)], [])
                total = sum(state)
                holds = {"IMPLICATION": not (state[0] == 1 and state[1] == 0), "EXCLUSIVITY": total <= 1,
                         "COMPLEMENT": total == 1, "EVENT_SUM": total == 1, "SAME_EVENT": state[0] == state[1]}[relation]
                assert result["status"] == ("FORMAL_BOUNDED_PAYOFF_PROOF" if holds else "FORMAL_COUNTEREXAMPLE")


# ------------------------------------------------------------------ R006


def test_rel_source_grounding_related_subcommand_and_cold_verify(world, baseline, tmp_path, capsys, monkeypatch):
    request = build_request(world)
    req = tmp_path / "req.json"
    req.write_text(json.dumps(request), encoding="utf-8")
    scratch = (tmp_path / "via-src01").resolve()
    capsys.readouterr()
    assert SGCLI.main(["related", "--grounding-scratch", str(world["grounding"]), "--request-file", str(req),
                       "--scratch-dir", str(scratch)]) == 0
    out = last_output(capsys)
    receipt = json.loads((scratch / "receipt.json").read_text(encoding="utf-8"))
    assert out["status"] == "RUN_COMPLETE" and out["receipt_id"] == receipt["receipt_id"] == baseline[1]["receipt_id"]
    assert receipt["receipt_id"] == REL.RECEIPT_PREFIX + SG.sha256_hex(SG.canonical_bytes({"core": receipt["core"]}))
    # Legacy SRC-01 verify is unchanged and still verifies its own scratch.
    assert SGCLI.main(["verify", "--scratch-dir", str(world["grounding"])]) == 0
    assert last_output(capsys)["status"] == "VERIFIED"
    # Cold verify with sockets blocked and no writes.
    before = {p: p.read_bytes() for p in scratch.rglob("*") if p.is_file()}
    attempts = []
    monkeypatch.setattr(socket, "create_connection", lambda *a, **k: attempts.append(1))
    assert REL.main(["verify", "--scratch-dir", str(scratch)]) == 0 and last_output(capsys)["status"] == "VERIFIED"
    assert {p: p.read_bytes() for p in scratch.rglob("*") if p.is_file()} == before and attempts == []
    # Safe repeat over identical inputs is idempotent and writes nothing.
    assert SGCLI.main(["related", "--grounding-scratch", str(world["grounding"]), "--request-file", str(req),
                       "--scratch-dir", str(scratch)]) == 0
    assert last_output(capsys)["status"] == "IDEMPOTENT_VERIFIED"
    assert {p: p.read_bytes() for p in scratch.rglob("*") if p.is_file()} == before
    # A changed venue body behind an identical request is NOT an idempotent repeat.
    clob = Path(request["venue"][0]["clob_file"])
    original = clob.read_bytes()
    clob.write_bytes(clob_body("oh-dem", "YES", [("0.44", "50")]))
    try:
        assert SGCLI.main(["related", "--grounding-scratch", str(world["grounding"]), "--request-file", str(req),
                           "--scratch-dir", str(scratch)]) == 1
        assert last_output(capsys)["reason_code"] == "SCRATCH_NOT_EMPTY"
    finally:
        clob.write_bytes(original)
    # Tamper matrix: each frozen artifact, generated result or identity change is detected.
    tampers = {
        "venue quote": lambda s: (s / "inputs" / "venue" / "000-clob.bin").write_bytes(clob_body("oh-dem", "YES", [("0.01", "50")])),
        "frozen rule": lambda s: next((s / "inputs" / "grounding" / "inputs" / "rules").iterdir()).write_bytes(b"edited rule"),
        "pit snapshot": lambda s: (s / "inputs" / "grounding" / "inputs" / "pit.sqlite3").write_bytes(b"x"),
        "request case": lambda s: (s / "inputs" / "request.source.json").write_bytes(b"{}"),
        "result": lambda s: _edit_receipt(s, lambda r: r["core"]["results"][0].update(disposition="FORMAL_VALID", expected="X")),
        "input hash": lambda s: _edit_receipt(s, lambda r: r["core"]["inputs"].update(benchmark_sha256="1" * 64)),
        "code identity": lambda s: _edit_receipt(s, lambda r: r["core"].update(code_identity="code:sha256:" + "0" * 64)),
        "receipt id": lambda s: _edit_receipt(s, lambda r: r.update(receipt_id=REL.RECEIPT_PREFIX + "0" * 64)),
    }
    for name, tamper in tampers.items():
        copy = (tmp_path / f"tamper-{name.replace(' ', '-')}").resolve()
        shutil.copytree(scratch, copy)
        tamper(copy)
        assert REL.main(["verify", "--scratch-dir", str(copy)]) == 1, name
        assert last_output(capsys)["status"] == "TAMPER_DETECTED", name
    # Replay-code identity drift is detected without editing the receipt.
    monkeypatch.setattr(REL, "code_identity", lambda: "code:sha256:" + "9" * 64)
    assert REL.main(["verify", "--scratch-dir", str(scratch)]) == 1
    assert "OUTPUT_MISMATCH:code_identity" in last_output(capsys)["failures"]


def _edit_receipt(scratch, change):
    path = scratch / "receipt.json"
    receipt = json.loads(path.read_text(encoding="utf-8"))
    change(receipt)
    path.write_text(json.dumps(receipt), encoding="utf-8")


# ------------------------------------------------------------------ R007

# Observed on the frozen corpus (no tuning). Labels are the expected FORMAL disposition, authored with the
# corpus, so verifier agreement 49/49 measures closed-rule consistency, not real-world lift. The baseline's
# 29 false relationship matches come from native event/category/title grouping alone.
EXPECTED_BENCHMARK = {
    "abstained_or_ambiguous": 19, "after_cost_test_evaluable": 5, "eligible_inspected": 40, "fee_known_legs": 20,
    "fee_unknown_legs": 34, "formal_conditional_proofs": 25, "native_candidates_matched": 40, "native_identity_only": 3,
    "price_inconsistencies": 2, "semantic_unknown": 32,
    "economic_status_counts": {"FEE_AND_DEPTH_CONDITIONAL": 2, "MECHANICALLY_INCONCLUSIVE": 9, "NOT_EVALUATED": 34,
                               "NOT_EXECUTABLE": 1, "NO_CONDITIONAL_EDGE": 1, "THEORETICAL_PRICE_INCONSISTENCY": 2},
}


def test_rel_frozen_40_cases_baseline_denominators(baseline):
    assert corpus_sha256() == CORPUS_SHA256
    bench = baseline[1]["core"]["benchmark"]
    assert bench["cases_total"] == len(MODELS) >= 40
    invalid = sum(1 for m in MODELS if m["expected"] != "FORMAL_VALID")
    assert invalid >= 10 and len({m["relation"] for m in MODELS if m["expected"] == "FORMAL_VALID"}) == 5
    assert bench["expected_label_counts"] == {"COUNTEREXAMPLE": 11, "FORMAL_VALID": 15, "INCONCLUSIVE": 7,
                                              "MODEL_INVALID": 5, "NOT_NATIVE_CANDIDATE": 7, "RULE_CONFLICT": 4}
    # Recomputed independently from the per-case rows, never trusted from the summary.
    by = rows(baseline[1])
    truth = {k for k, r in by.items() if r["expected"] == "FORMAL_VALID"}
    base_prop = {k for k, r in by.items() if r["baseline_related"]}
    ver_prop = {k for k, r in by.items() if r["disposition"] == "FORMAL_VALID"}
    for key, prop in ((RM.BASELINE_ID, base_prop), ("related_market_verifier_v1", ver_prop)):
        assert bench[key]["proposed"] == len(prop) and bench[key]["true_matches"] == len(prop & truth)
        assert bench[key]["false_relationship_matches"] == len(prop - truth)
        assert bench[key]["false_positive_rate"]["denominator"] == len(MODELS) - len(truth)
    assert bench["disposition_agreement"]["numerator"] == sum(1 for r in by.values() if r["disposition"] == r["expected"])
    assert {k: bench[k] for k in EXPECTED_BENCHMARK} == EXPECTED_BENCHMARK
    assert bench["real_world_verified"] == 0 and bench["real_world_evaluable"] == 0
    assert bench["zero_improvement_permitted"] is True


# ------------------------------------------------------------------ R008


@pytest.mark.parametrize("mutate, code", [
    (lambda r: r.pop("search"), "REQUEST_FIELDS_INVALID"),
    (lambda r: r.update(schema_id="other"), "REQUEST_SCHEMA_INVALID"),
    (lambda r: r.update(corpus_class="REAL_ALPHA"), "CORPUS_CLASS_INVALID"),
    (lambda r: r.update(decision_time="2026-06-01 12:00"), "DECISION_TIME_INVALID"),
    (lambda r: r.update(basket_shares="1e3"), "BASKET_SHARES_INVALID"),
    (lambda r: r.update(basket_shares="-1"), "BASKET_SHARES_INVALID"),
    (lambda r: r["search"].update(max_group_size=5), "SEARCH_INVALID"),
    (lambda r: r["search"].update(families=["CORRELATION"]), "SEARCH_INVALID"),
    (lambda r: r["fee_policy"].update(kind="ZERO_FEES"), "FEE_POLICY_INVALID"),
    (lambda r: r["fee_policy"].update(test_rate="0.02"), "FEE_POLICY_INVALID"),
    (lambda r: r.update(api_key="x"), "FORBIDDEN_FIELD"),
    (lambda r: r["models"][0].update(Private_Key="x"), "FORBIDDEN_FIELD"),
    (lambda r: r.update(request_label="sk-" + "a" * 30), "SECRET_MATERIAL_REJECTED"),
    (lambda r: r.update(models=[]), "MODELS_INVALID"),
    (lambda r: r.update(benchmark_sha256="a" * 64), "BENCHMARK_FREEZE_MISMATCH"),
    (lambda r: r.update(corpus_class="LOCAL_REAL_PIT"), "CORPUS_CLASS_MISMATCH"),
])
def test_rel_request_negative_matrix(world, tmp_path, capsys, mutate, code):
    request = build_request(world)
    mutate(request)
    if code not in ("BENCHMARK_FREEZE_MISMATCH", "REQUEST_FIELDS_INVALID") and "search" in request:
        request["benchmark_sha256"] = REL.benchmark_commitment(request) if isinstance(request.get("models"), list) else "0" * 64
    capsys.readouterr()
    assert run_rel(tmp_path, world, request)[0] == 1
    out = last_output(capsys)
    assert out == {"status": "STOPPED", "reason_code": code}  # sanitized: no input, path or exception text


def test_rel_negative_matrix_authority_and_adoption_truth(world, baseline, tmp_path, capsys, monkeypatch):
    request = build_request(world)
    req = tmp_path / "req.json"
    req.write_text(json.dumps(request), encoding="utf-8")
    capsys.readouterr()
    # Scratch, symlink, traversal and overlap boundaries.
    for scratch, code in ((REPO_ROOT / "local_data" / "rel01", "SCRATCH_INSIDE_REPOSITORY"),
                          (world["grounding"] / "nested", "GROUNDING_SCRATCH_UNUSABLE")):
        assert REL.main(["run", "--grounding-scratch", str(world["grounding"]), "--request-file", str(req),
                         "--scratch-dir", str(scratch)]) == 1
        assert last_output(capsys)["reason_code"] == code
    busy = tmp_path / "busy"
    busy.mkdir()
    (busy / "x").write_text("x")
    assert REL.main(["run", "--grounding-scratch", str(world["grounding"]), "--request-file", str(req), "--scratch-dir", str(busy)]) == 1
    assert last_output(capsys)["reason_code"] == "SCRATCH_NOT_EMPTY"
    traversal = str(tmp_path / "x" / ".." / "req.json")
    assert REL.main(["run", "--grounding-scratch", str(world["grounding"]), "--request-file", traversal,
                     "--scratch-dir", str(tmp_path / "t1")]) == 1
    assert last_output(capsys)["reason_code"] == "REQUEST_UNREADABLE"
    try:
        (tmp_path / "link.json").symlink_to(req)
        symlink_ok = True
    except OSError:
        symlink_ok = False  # Windows without symlink privilege: covered by the lstat guard unit check below
    if symlink_ok:
        assert REL.main(["run", "--grounding-scratch", str(world["grounding"]), "--request-file", str(tmp_path / "link.json"),
                         "--scratch-dir", str(tmp_path / "t2")]) == 1
        assert last_output(capsys)["reason_code"] == "REQUEST_UNREADABLE"
    hard = tmp_path / "hard.json"
    try:
        import os
        os.link(req, hard)
        assert REL._caller_path(str(hard), directory=False, scratch=None) is None  # hardlinked input rejected
        hard.unlink()
    except OSError:
        pass
    secret_dir = tmp_path / "secrets"
    secret_dir.mkdir()
    shutil.copyfile(req, secret_dir / "req.json")
    assert REL._caller_path(str(secret_dir / "req.json"), directory=False, scratch=None) is None
    (tmp_path / "big.json").write_bytes(b" " * (REL.MAX_REQUEST_BYTES + 1))
    assert REL.main(["run", "--grounding-scratch", str(world["grounding"]), "--request-file", str(tmp_path / "big.json"),
                     "--scratch-dir", str(tmp_path / "t3")]) == 1
    assert last_output(capsys)["reason_code"] == "REQUEST_UNREADABLE"
    # A tampered grounding scratch is refused before any relation work.
    bad = (tmp_path / "bad-grounding").resolve()
    shutil.copytree(world["grounding"], bad)
    (bad / "inputs" / "pit.sqlite3").write_bytes(b"edited")
    assert REL.main(["run", "--grounding-scratch", str(bad), "--request-file", str(req), "--scratch-dir", str(tmp_path / "t4")]) == 1
    assert last_output(capsys)["reason_code"] == "GROUNDING_RECEIPT_NOT_VERIFIED"
    # Network socket attempt during the run fails closed even if caught inside.
    real = RM.discover_candidates

    def sneaky(*args):
        try:
            socket.create_connection(("example.invalid", 443))
        except Exception:
            pass
        return real(*args)
    monkeypatch.setattr(RM, "discover_candidates", sneaky)
    assert REL.main(["run", "--grounding-scratch", str(world["grounding"]), "--request-file", str(req),
                     "--scratch-dir", str(tmp_path / "t5")]) == 1
    assert last_output(capsys)["reason_code"] == "NETWORK_ATTEMPT_BLOCKED"
    monkeypatch.setattr(RM, "discover_candidates", real)
    # Abort mid-run leaves a partial scratch that is never a receipt and refuses reuse; resume needs a new scratch.
    monkeypatch.setattr(REL, "build_related_core", _raise_budget)
    partial = (tmp_path / "partial").resolve()
    assert REL.main(["run", "--grounding-scratch", str(world["grounding"]), "--request-file", str(req), "--scratch-dir", str(partial)]) == 1
    assert last_output(capsys)["reason_code"] == "TIME_BUDGET_EXCEEDED" and not (partial / "receipt.json").exists()
    monkeypatch.undo()
    assert REL.main(["run", "--grounding-scratch", str(world["grounding"]), "--request-file", str(req), "--scratch-dir", str(partial)]) == 1
    assert last_output(capsys)["reason_code"] == "SCRATCH_NOT_EMPTY"
    assert REL.main(["verify", "--scratch-dir", str(partial)]) == 1
    # No mutation of PIT / Alpha / grounding inputs, and closed authority.
    before = {p: _sha(p.read_bytes()) for p in [world["pit"], *world["grounding"].rglob("*")] if p.is_file()}
    code, _, receipt = run_rel(tmp_path, world, request, name="authority")
    assert code == 0 and {p: _sha(p.read_bytes()) for p in before} == before
    authority = dict(receipt["core"]["authority"])
    assert authority.pop("research_only") is True and not any(authority.values())
    for row in receipt["core"]["results"]:
        for basket in row["economics"]["baskets"]:
            assert basket["executable_edge"] is False and basket["guaranteed_arbitrage"] is False and basket["profit_proven"] is False
    statuses = {b["status"] for r in receipt["core"]["results"] for b in r["economics"]["baskets"]}
    assert not statuses & {"EXECUTABLE_EDGE_PASS", "GUARANTEED_ARBITRAGE"}
    # Malformed per-model / per-venue fields are counted per item, never a whole-run crash.
    assert not REL._model_fields_ok(dict(MODELS[0], claimed_rule_sha256=[[1], [2]]))
    odd = build_request(world, venue=[dict(world["venue"][0], market_id=["x"])])
    code, _, odd_receipt = run_rel(tmp_path, world, odd, name="odd-venue")
    assert code == 0 and odd_receipt["core"]["venue"]["counts"] == {"VENUE_FIELDS_INVALID": 1}
    # Imports stay inside the native research/feasibility boundary (no WP170/WP172, live, paper, gateway, Hermes).
    allowed = {"__future__", "argparse", "collections", "datetime", "decimal", "hashlib", "itertools", "json", "os", "pathlib",
               "re", "shutil", "stat", "sys", "time", "types", "src.data_layer.analytical_research",
               "src.data_layer.point_in_time_market_research", "src.execution_feasibility", "src.execution_feasibility.models",
               "tools.alpha"}
    for path in (Path(RM.__file__), Path(REL.RE.__file__), Path(REL.__file__)):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        names = {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)} | \
                {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
        assert names <= allowed, (path.name, names - allowed)
    # Adoption truth: five targeted IDs, never value-verified; the other 31 and six provider lanes unchanged.
    adoption = receipt["core"]["adoption"]
    assert {k for k in adoption if k.startswith("R3-")} == {"R3-03", "R3-03-FEES", "R3-04", "R3-11", "R3-19"}
    assert not any("VALUE_VERIFIED" in v and "NOT_VALUE_VERIFIED" not in v for v in adoption.values())
    assert adoption["other_31_capability_ids"] == "UNCHANGED" and adoption["provider_lanes"] == "SIX_SEPARATE_OWNER_GATES_UNCHANGED"
    pins = {p["capability"]: p for p in receipt["core"]["source_pins"]}
    assert set(pins) == {"R3-03", "R3-03-FEES", "R3-04", "R3-11", "R3-19"}
    assert all(p["adoption_mode"] == "ADAPT_ALGORITHM_NO_CODE_COPIED" for p in pins.values())
    # Exact contract binding.
    contract = (REPO_ROOT / "docs" / "related_market_alpha_contract.md").read_text(encoding="utf-8")
    assert CORPUS_SHA256 in contract and RM.BASELINE_ID in contract and REL.RECEIPT_SCHEMA in contract


def _raise_budget(*_args):
    raise REL.RM.RelationStop("TIME_BUDGET_EXCEEDED")


def test_rel_local_real_pit_path_is_not_promoted(tmp_path):
    """LOCAL_REAL_PIT class is accepted as a label only; nothing is promoted to real verification."""
    world = make_world((tmp_path / "real").resolve(), corpus_class="LOCAL_REAL_PIT")
    code, _, receipt = run_rel(tmp_path, world, build_request(world, corpus_class="LOCAL_REAL_PIT", models=MODELS[:6]))
    assert code == 0
    core = receipt["core"]
    assert core["corpus_class"] == "LOCAL_REAL_PIT" and "awaits independent review" in core["adoption"]["reason"]
    assert core["benchmark"]["real_world_verified"] == 0
    assert all(r["real_world"]["real_world_rule_verified"] is False for r in core["results"])
