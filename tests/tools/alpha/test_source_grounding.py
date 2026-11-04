"""S10-R3-SRC-01 offline tests: native PIT/Alpha corpus -> real CLI -> ranker -> receipt -> cold verify.

The benchmark corpus below is SANITIZED_SYNTHETIC and frozen inline. Ranking parameters in
source_grounding.py are textbook BM25 defaults fixed before this corpus was written. Results
prove callable behaviour and honest accounting only, never real-world retrieval lift.
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
from src.data_layer.analytical_research import source_grounding as SG
from src.data_layer.point_in_time_market_research import research_provenance as RP
from tests.data_layer.analytical_research.test_alpha_discovery import _alpha_registry, _pit_built, _pit_store
from tools.alpha import run_source_grounding as CLI

REPO_ROOT = Path(__file__).resolve().parents[3]
AS_OF = "2026-06-01T12:00:00Z"
OBSERVED, INGESTED = "2026-06-01T00:00:01Z", "2026-06-01T00:00:02Z"

# ------------------------------------------------------------------ frozen SANITIZED_SYNTHETIC corpus
# (slug, event, category, question, resolution_date); native PIT metadata requires question_text.
MARKETS = (
    ("oh-sen-dem", "oh-senate-2026", "politics", "Will the Democratic candidate win the 2026 Ohio Senate election?", "2026-11-03"),
    ("oh-sen-rep", "oh-senate-2026", "politics", "Will the Republican candidate win the 2026 Ohio Senate election?", "2026-11-03"),
    ("ga-gov", "ga-gov-2026", "politics", "Will the incumbent party hold the Georgia governorship in 2026?", "2026-11-03"),
    ("uk-pm", "uk-pm-2026", "politics", "Will the UK Prime Minister leave office before July 2026?", "2026-07-01"),
    ("fr-assembly", "fr-dissolve-2026", "politics", "Will France dissolve the National Assembly in 2026?", "2026-12-31"),
    ("house-control", "us-house-2026", "politics", "Will Democrats control the US House after the 2026 midterms?", "2026-11-30"),
    ("shutdown", "us-shutdown-2026", "politics", "Will the US federal government shut down before October 1, 2026?", "2026-10-01"),
    ("nba-celtics", "nba-finals-2026", "sports", "Will the Boston Celtics win the 2026 NBA Finals?", "2026-06-30"),
    ("nba-thunder", "nba-finals-2026", "sports", "Will the Oklahoma City Thunder win the 2026 NBA Finals?", "2026-06-30"),
    ("wc-brazil", "world-cup-2026", "sports", "Will Brazil win the 2026 FIFA World Cup?", "2026-07-19"),
    ("wc-france", "world-cup-2026", "sports", "Will France win the 2026 FIFA World Cup?", "2026-07-19"),
    ("wimbledon", "wimbledon-2026", "sports", "Will the top seed win the 2026 Wimbledon men's singles title?", "2026-07-12"),
    ("superbowl", "super-bowl-lxi", "sports", "Will the Kansas City Chiefs win Super Bowl LXI?", "2027-02-14"),
    ("tdf", "tour-de-france-2026", "sports", "Will a Slovenian rider win the 2026 Tour de France?", "2026-07-26"),
    ("nyc-temp", "nyc-high-temp-jul", "weather", "Will Central Park record a high above 95F on July 4, 2026?", "2026-07-05"),
    ("nyc-temp-lga", "nyc-high-temp-jul-alt", "weather", "Will Central Park record a high above 95F on July 4, 2026?", "2026-07-05"),
    ("nyc-rain", "nyc-rain-jul", "weather", "Will New York City record more than 4 inches of rain in July 2026?", "2026-08-01"),
    ("hurricane-cat5", "atlantic-hurricanes-2026", "weather", "Will a Category 5 hurricane form in the Atlantic in 2026?", "2026-11-30"),
    ("hurricane-landfall", "atlantic-hurricanes-2026", "weather", "Will a major hurricane make landfall in Florida in 2026?", "2026-11-30"),
    ("london-snow", "london-snow-xmas", "weather", "Will London see measurable snowfall on Christmas Day 2026?", "2026-12-26"),
    ("chicago-temp", "chicago-temp-jan", "weather", "Will Chicago's lowest January 2026 temperature fall below -10F?", "2026-02-01"),
    ("fed-cut-sep", "fed-sep-2026", "economics", "Will the Federal Reserve cut interest rates at the September 2026 FOMC meeting?", "2026-09-17"),
    ("fed-hold-sep", "fed-sep-2026", "economics", "Will the Federal Reserve hold interest rates at the September 2026 FOMC meeting?", "2026-09-17"),
    ("cpi", "us-cpi-aug-2026", "economics", "Will US CPI inflation exceed 3% year over year in August 2026?", "2026-09-15"),
    ("unemployment", "us-jobs-oct-2026", "economics", "Will the US unemployment rate be 4.5% or higher in October 2026?", "2026-11-06"),
    ("recession", "us-recession-2026", "economics", "Will the NBER declare a US recession starting in 2026?", "2027-06-30"),
    ("ecb", "ecb-oct-2026", "economics", "Will the European Central Bank raise rates in October 2026?", "2026-10-30"),
    ("gdp", "us-gdp-q3-2026", "economics", "Will US real GDP growth for Q3 2026 be negative?", "2026-10-29"),
    ("oscars-bp", "oscars-2027", "entertainment", "Will a streaming film win Best Picture at the 2027 Academy Awards?", "2027-03-15"),
    ("taylor-album", "taylor-album-2026", "entertainment", "Will Taylor Swift release a new studio album in 2026?", "2026-12-31"),
    ("box-office", "summer-box-office-2026", "entertainment", "Will any film gross over $1 billion worldwide in summer 2026?", "2026-09-30"),
    ("grammys", "grammys-2027", "entertainment", "Will a debut artist win Album of the Year at the 2027 Grammys?", "2027-02-10"),
    ("starship", "starship-orbit-2026", "science", "Will SpaceX Starship complete a full orbital flight in 2026?", "2026-12-31"),
    ("artemis", "artemis-ii", "science", "Will NASA launch the Artemis II crewed mission before December 2026?", "2026-12-01"),
    ("ai-model", "ai-release-2026", "technology", "Will OpenAI release GPT-6 before the end of 2026?", "2026-12-31"),
    ("apple-glasses", "apple-glasses-2026", "technology", "Will Apple announce smart glasses at WWDC 2026?", "2026-06-12"),
    ("fusion", "fusion-record-2026", "science", "Will a fusion experiment report net energy gain again in 2026?", "2026-12-31"),
    ("ukraine-ceasefire", "ukraine-ceasefire-2026", "world", "Will Russia and Ukraine agree to a ceasefire in 2026?", "2026-12-31"),
    ("olympics-host", "olympics-2036", "sports", "Will India be named host of the 2036 Summer Olympics in 2026?", "2026-12-31"),
)
RULES = {
    "nyc-temp": "This market resolves YES if the NOAA NWS daily climate report for the Central Park station records a maximum temperature above 95 degrees Fahrenheit on July 4 2026. Otherwise NO.",
    "nyc-temp-lga": "This market resolves YES if the NOAA NWS daily climate report for the LaGuardia Airport station records a maximum temperature above 95 degrees Fahrenheit on July 4 2026. Otherwise NO.",
    "fed-cut-sep": "Resolves YES if the FOMC statement published by the Federal Reserve Board after the September 2026 meeting lowers the target range for the federal funds rate. Otherwise NO.",
    "cpi": "Resolves per the Bureau of Labor Statistics CPI-U all items index, twelve month percent change, not seasonally adjusted, for August 2026, as first published.",
    "hurricane-cat5": "Resolves YES if the National Hurricane Center reports any Atlantic basin tropical cyclone reaching Category 5 intensity on the Saffir-Simpson scale during 2026.",
    "house-control": "Resolves YES if the Democratic Party wins at least 218 seats in the US House of Representatives as called by the Associated Press for the November 2026 elections.",
    "starship": "Resolves YES if SpaceX Starship reaches orbital velocity and completes at least one full orbit, as confirmed by SpaceX or the FAA, during 2026.",
    "unemployment": "Resolves using the Bureau of Labor Statistics Employment Situation report headline U-3 unemployment rate for October 2026.",
}
# (query_id, text, category_hint, relevant slugs); empty list = expected no match.
QUERIES = (
    ("r01", "NOAA Central Park station maximum temperature July 4", "weather", ["nyc-temp"]),
    ("r02", "LaGuardia Airport station temperature reading", "weather", ["nyc-temp-lga"]),
    ("r03", "Bureau of Labor Statistics consumer price index August", "economics", ["cpi"]),
    ("r04", "federal funds rate target range lowered", "economics", ["fed-cut-sep"]),
    ("r05", "National Hurricane Center Saffir-Simpson category five", "weather", ["hurricane-cat5"]),
    ("r06", "Associated Press 218 seats House", "politics", ["house-control"]),
    ("r07", "Starship orbital velocity FAA confirmation", "science", ["starship"]),
    ("r08", "U-3 headline unemployment rate October", "economics", ["unemployment"]),
    ("e01", "2026 Ohio Senate election", "politics", ["oh-sen-dem", "oh-sen-rep"]),
    ("e02", "who wins the 2026 NBA Finals", "sports", ["nba-celtics", "nba-thunder"]),
    ("e03", "2026 FIFA World Cup winner", "sports", ["wc-brazil", "wc-france"]),
    ("e04", "September 2026 FOMC interest rate decision", "economics", ["fed-cut-sep", "fed-hold-sep"]),
    ("e05", "Atlantic hurricane season 2026", "weather", ["hurricane-cat5", "hurricane-landfall"]),
    ("p01", "Georgia governor race incumbent party", "politics", ["ga-gov"]),
    ("p02", "UK Prime Minister resign", "politics", ["uk-pm"]),
    ("p03", "France dissolve National Assembly", "politics", ["fr-assembly"]),
    ("p04", "government shutdown October", "politics", ["shutdown"]),
    ("p05", "Kansas City Chiefs Super Bowl", "sports", ["superbowl"]),
    ("p06", "Wimbledon men's singles top seed", "sports", ["wimbledon"]),
    ("p07", "Slovenian rider Tour de France", "sports", ["tdf"]),
    ("p08", "New York City July rainfall inches", "weather", ["nyc-rain"]),
    ("p09", "Florida major hurricane landfall", "weather", ["hurricane-landfall"]),
    ("p10", "London snow Christmas", "weather", ["london-snow"]),
    ("p11", "Chicago January cold temperature", "weather", ["chicago-temp"]),
    ("p12", "NBER recession declaration", "economics", ["recession"]),
    ("p13", "European Central Bank rate hike October", "economics", ["ecb"]),
    ("p14", "negative GDP growth third quarter", "economics", ["gdp"]),
    ("p15", "streaming film Best Picture Oscars", "entertainment", ["oscars-bp"]),
    ("p16", "Taylor Swift new album", "entertainment", ["taylor-album"]),
    ("p17", "billion dollar box office summer", "entertainment", ["box-office"]),
    ("p18", "Album of the Year debut artist Grammys", "entertainment", ["grammys"]),
    ("p19", "Artemis II crewed launch NASA", "science", ["artemis"]),
    ("p20", "GPT-6 release OpenAI", "technology", ["ai-model"]),
    ("p21", "Apple smart glasses WWDC", "technology", ["apple-glasses"]),
    ("p22", "fusion net energy gain", "science", ["fusion"]),
    ("p23", "Russia Ukraine ceasefire agreement", "world", ["ukraine-ceasefire"]),
    ("p24", "2036 Olympics host India", "sports", ["olympics-host"]),
    ("h01", "Will the central bank lower borrowing costs this autumn", "economics", ["fed-cut-sep"]),
    ("h02", "Will the Chiefs repeat as NFL champions", "sports", ["superbowl"]),
    ("n01", "Will the price of eggs double in Tokyo supermarkets", None, []),
    ("n02", "Mars rover discovers fossil evidence", None, []),
    ("n03", "Will the Eiffel Tower close for renovation", None, []),
    ("n04", "Cricket test series Australia India", None, []),
    ("n05", "Will Lake Tahoe freeze over", None, []),
    ("n06", "Will 2026 be a year", None, []),
)
CORPUS = {"class": "SANITIZED_SYNTHETIC", "markets": [list(m) for m in MARKETS], "rules": RULES,
          "queries": [list(q) for q in QUERIES]}
CORPUS_SHA256 = "4a3639c3b66a9b55b06d2bdd5f9504ef18222dffe284b13292f0fa3ad7c2d030"

GOOD_HTML = ("<html><body><h1>August CPI release</h1><p>" + "The consumer price index report for the period "
             "was published on schedule with the usual tables and methodology notes. " * 5 + "</p></body></html>").encode()
FED_TEXT = ("Federal Reserve press release. The Committee decided to maintain the target range. " * 4).encode()


def _mid(slug):
    return f"market:polymarket:{slug}"


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _policy_mapping():
    return {"schema_version": "1.0.0", "policy_version": "src01-fixture/1", "eligible_market_statuses": ["open"],
            "metadata_freshness_seconds": 86400, "order_book_freshness_seconds": 30,
            "resolution_rule_freshness_seconds": 86400, "soft_last_trade_price_abs_delta": "0.1",
            "soft_mid_price_abs_delta": "0.1", "soft_spread_abs_delta": "0.05", "soft_top_depth_relative_delta": "0.25",
            "queue_capacity": 4, "exploration_slots": 1, "audit_slots": 1, "max_per_category": 2,
            "audit_seed": "src01-seed", "research_archetype_taxonomy_version": "alpha-archetypes/1",
            "advisory_only": True, "no_execution_authority": True, "no_strategy_authority": True,
            "no_qualification_authority": True}


def _pit_records():
    records = []
    times = dict(observed_time=OBSERVED, ingestion_time=INGESTED)
    for slug, event, category, question, date in MARKETS:
        payload = {"market_status": "open", "outcome_labels": ["No", "Yes"], "question_text": question,
                   "token_ids": [f"token:polymarket:{slug}-no", f"token:polymarket:{slug}-yes"],
                   "condition_id": f"condition:{slug}", "category": category, "resolution_date": date + "T00:00:00Z"}
        meta, _ = _pit_built("PIT-C01-VALID-MARKET-METADATA", platform_id="platform:polymarket",
                             event_id=f"event:polymarket:synthetic-{event}", market_id=_mid(slug),
                             source_id="source:polymarket:gamma-markets", source_assertion_id=f"assertion:src01:meta:{slug}",
                             snapshot_id=f"snapshot:src01:meta:{slug}", source_snapshot_id=f"source-snapshot:src01:meta:{slug}",
                             event_time="2026-06-01T00:00:00Z", canonical_payload=payload, **times)
        records.append(meta)
        if slug in RULES:
            source, _ = _pit_built("PIT-C04-VALID-SOURCE-SNAPSHOT", source_id=f"source:src01:rules:{slug}",
                                   snapshot_id=f"snapshot:src01:rulesrc:{slug}", **times)
            rule, _ = _pit_built("PIT-C05-VALID-RESOLUTION-RULE-SNAPSHOT", platform_id="platform:polymarket",
                                 event_id=f"event:polymarket:synthetic-{event}", market_id=_mid(slug),
                                 resolution_source_id="resolution-source:polymarket:primary",
                                 source_snapshot_id=source.envelope.source_snapshot_id,
                                 rule_content_sha256=_sha(RULES[slug].encode()), snapshot_id=f"snapshot:src01:rule:{slug}",
                                 observed_time="2026-06-01T00:00:03Z", ingestion_time="2026-06-01T00:00:04Z")
            records.extend((source, rule))
    return records


def _source(label, slug, file, data, **overrides):
    value = {"source_label": label, "market_id": _mid(slug), "file": str(file), "url": f"https://example.invalid/{label}",
             "http_status": 200, "media_type": "text/html", "capture_mode": "PROSPECTIVE_LOCAL_CAPTURE",
             "declared_sha256": _sha(data), "source_publish_time": "2026-05-30T00:00:00Z",
             "public_available_time": "2026-05-30T00:00:00Z", "local_first_seen_time": "2026-05-31T00:00:00Z",
             "ingestion_time": "2026-05-31T00:00:01Z", "revision_time": None}
    value.update(overrides)
    return value


@pytest.fixture(scope="module")
def world(tmp_path_factory):
    base = tmp_path_factory.mktemp("src01_inputs")
    pit = _pit_store(base, _pit_records())
    alpha = _alpha_registry(base, [("cpi", None), ("not-in-corpus", None)])
    files = {}

    def put(name, data):
        path = (base / name).resolve()
        path.write_bytes(data)
        files[name] = path
        return path
    rule_entries = [{"market_id": _mid(s), "file": str(put(f"rule-{s}.txt", t.encode()))} for s, t in RULES.items()]
    rule_entries.append({"market_id": _mid("gdp"), "file": str(put("rule-gdp-forged.txt", b"Forged rule wording."))})
    rule_entries.append({"market_id": _mid("ghost"), "file": str(put("rule-ghost.txt", b"No such market."))})
    sources = [
        _source("cpi-release", "cpi", put("cpi.html", GOOD_HTML), GOOD_HTML),
        _source("cpi-mirror", "cpi", files["cpi.html"], GOOD_HTML),  # same bytes -> DEDUPED
        _source("fed-import", "fed-hold-sep", put("fed.txt", FED_TEXT), FED_TEXT, capture_mode="LATER_IMPORT",
                media_type="text/plain", local_first_seen_time="2026-07-01T00:00:00Z",
                ingestion_time="2026-07-01T00:00:01Z"),
    ]
    queries = [{"query_id": q, "text": t, "category_hint": c, "relevant_market_ids": [_mid(s) for s in rel]}
               for q, t, c, rel in QUERIES]
    case = {"schema_id": SG.CASE_SCHEMA, "case_label": "src01-synthetic", "corpus_class": "SANITIZED_SYNTHETIC",
            "pit_store": str(pit), "alpha_registry": str(alpha), "policy": _policy_mapping(), "as_of": AS_OF,
            "rule_texts": rule_entries, "sources": sources, "queries": queries}
    return {"base": base, "pit": pit, "alpha": alpha, "case": case, "put": put}


def _run(tmp_path, case, name="scratch"):
    case_path = tmp_path / f"{name}-case.json"
    case_path.write_text(json.dumps(case), encoding="utf-8")
    scratch = (tmp_path / name).resolve()
    code = CLI.main(["run", "--case", str(case_path), "--scratch-dir", str(scratch)])
    receipt = json.loads((scratch / "receipt.json").read_text(encoding="utf-8")) if (scratch / "receipt.json").exists() else None
    return code, scratch, receipt


def _verify(scratch, capsys=None):
    code = CLI.main(["verify", "--scratch-dir", str(scratch)])
    return code


@pytest.fixture(scope="module")
def baseline_run(world, tmp_path_factory):
    tmp = tmp_path_factory.mktemp("src01_run")
    code, scratch, receipt = _run(tmp, world["case"])
    assert code == 0, receipt
    return scratch, receipt


def _cases(receipt):
    return {c["query_id"]: c for c in receipt["core"]["benchmark"]["cases"] if c["query_id"]}


# ------------------------------------------------------------------ R001


def test_source_grounding_native_reader_and_real_discovery_caller(world, tmp_path, monkeypatch):
    calls = []
    real = SG.rank_markets
    monkeypatch.setattr(SG, "rank_markets", lambda index, query: calls.append(query) or real(index, query))
    code, scratch, receipt = _run(tmp_path, world["case"])
    assert code == 0 and receipt is not None
    core = receipt["core"]
    assert len(calls) == core["benchmark"]["denominators"]["cases_valid"] == len(QUERIES)
    policy = AD.build_alpha_discovery_policy(_policy_mapping()).record
    native = AD.build_alpha_universe_snapshot(world["pit"], policy, AS_OF).record
    assert core["inputs"]["alpha_universe_snapshot_id"] == native.alpha_universe_snapshot_id
    native_ids = {m.market_id for m in native.markets}
    assert core["corpus"]["market_ids"] == sorted(native_ids) and len(native_ids) == len(MARKETS)
    assert core["corpus"]["markets_unrankable_no_question"] == 0
    ranked = [m for c in core["benchmark"]["cases"] for m in c["ranker"]]
    assert ranked and set(ranked) <= native_ids
    r01 = _cases(receipt)["r01"]
    assert r01["ranker"][0] == _mid("nyc-temp") and "SAME_TITLE_DIFFERENT_RULES" in r01["flags"]
    grounded = r01["subquestions"][0]["items"][1]
    assert "hash-verified rule" in grounded["text"] and f"rule:sha256:{_sha(RULES['nyc-temp'].encode())}" in grounded["claim_sources"]
    assert r01["subquestions"][0]["event_identity"] == "EVENT_ID_AS_RECORDED"
    e01 = _cases(receipt)["e01"]
    assert set(e01["ranker"][:2]) == {_mid("oh-sen-dem"), _mid("oh-sen-rep")}
    assert core["caller"] == SG.CALLER and core["alpha_join"]["joined"][0]["market_ids"] == [_mid("cpi")]
    assert core["alpha_join"]["unresolved_refs"] == 1


def test_condition_derived_event_identity_is_labelled():
    market = AD.ObservedMarketState("market:polymarket:1", "event:polymarket:0xabc", "open", "0xabc", (), (), None,
                                    None, "q", "record:sha256:" + "a" * 64, OBSERVED, "FRESH", "a" * 64, "b" * 64,
                                    "c" * 64, (), (), ())
    assert SG._event_identity(market) == "EVENT_ID_CONDITION_DERIVED"


# ------------------------------------------------------------------ R002

# Observed on the frozen corpus with a-priori parameters (no tuning). Not a lift claim: the ranker
# trails the baseline on recall/precision here and only abstains better on no-match queries.
EXPECTED_METRICS = {
    "baseline_plain_v0": {"abstained": "0.066667", "false_relatedness_items": "0.702128",
                          "negative_queries_with_results": "0.500000", "positive_queries_with_zero_hits": "0.051282",
                          "precision_at_10": "0.328125", "recall_at_10": "0.954545"},
    "pa_event_market_bm25_v1": {"abstained": "0.177778", "false_relatedness_items": "0.737179",
                                "negative_queries_with_results": "0.166667", "positive_queries_with_zero_hits": "0.076923",
                                "precision_at_10": "0.280822", "recall_at_10": "0.931818"},
}


def test_source_grounding_polymarket_agents_30_case_recall_and_precision(baseline_run, world, tmp_path):
    assert len(QUERIES) >= 30 and SG.BENCHMARK_MIN_LABELED == 30
    assert _sha(SG.canonical_bytes(CORPUS)) == CORPUS_SHA256
    _, receipt = baseline_run
    bench = receipt["core"]["benchmark"]
    assert bench["status"] == "COMPLETED"
    assert bench["denominators"] == {"cases_total": 45, "cases_valid": 45, "cases_refused": 0, "positive_labeled": 39,
                                     "negative_no_match": 6, "refused_by_reason": {}}
    for method, key in ((SG.RANKER_ID, "ranker"), (SG.BASELINE_ID, "baseline")):
        m = bench["metrics"][method]
        pos = [c for c in bench["cases"] if c["relevant"]]
        assert m["recall_at_10"]["numerator"] == sum(len(set(c[key]) & set(c["relevant"])) for c in pos)
        assert m["recall_at_10"]["denominator"] == sum(len(c["relevant"]) for c in pos) == 44
        assert m["precision_at_10"]["denominator"] == sum(len(c[key]) for c in pos)
        assert m["cost"] == {"classification": "LOCAL_CPU_ONLY", "provider_calls": 0, "network_calls": 0, "spend_usd": "0"}
    assert {k: {n: bench["metrics"][k][n]["value"] for n in bench["metrics"][k] if n != "cost"} for k in bench["metrics"]} == EXPECTED_METRICS
    # honest failures stay in the denominator
    cases = _cases(receipt)
    assert _mid("fed-cut-sep") not in cases["h01"]["ranker"] and cases["n06"]["ranker"]
    # baseline is the constructed question-text overlap with category tie-break
    assert _mid("nyc-temp-lga") not in cases["r02"]["baseline"] and cases["r02"]["ranker"][0] == _mid("nyc-temp-lga")
    assert cases["p17"]["ranker_reason"] == "LOW_QUERY_COVERAGE" and _mid("box-office") in cases["p17"]["baseline"]
    # fewer than thirty labeled cases -> refused, denominator preserved
    short = dict(world["case"], queries=world["case"]["queries"][:29])
    code, _, small = _run(tmp_path, short, "short")
    assert code == 0 and small["core"]["benchmark"]["status"] == "BENCHMARK_REFUSED"
    assert small["core"]["benchmark"]["metrics"] is None and small["core"]["benchmark"]["denominators"]["cases_total"] == 29


def test_baseline_plain_v0_definition():
    m = lambda slug, cat, q: AD.ObservedMarketState(_mid(slug), "event:x", "open", None, (), (), None, cat, q,
                                                    "record:sha256:" + "a" * 64, OBSERVED, "FRESH", "a" * 64, "b" * 64,
                                                    "c" * 64, (), (), ())
    universe = type("U", (), {"markets": (m("b", "x", "Rain in Paris"), m("a", "y", "Rain in Paris"), m("c", "y", "Snow"))})
    assert SG.rank_baseline_plain_v0(universe, "RAIN paris", "x") == [_mid("b"), _mid("a")]
    assert SG.rank_baseline_plain_v0(universe, "rain paris", "y") == [_mid("a"), _mid("b")]
    assert SG.rank_baseline_plain_v0(universe, "hail", None) == []


# ------------------------------------------------------------------ R003


def test_source_grounding_source_archive_quality_and_native_receipt(baseline_run):
    _, receipt = baseline_run
    sources = receipt["core"]["sources"]
    by_label = {e["source_label"]: e for e in sources["entries"]}
    assert by_label["cpi-release"]["status"] == "ACCEPTED"
    assert by_label["cpi-release"]["content_sha256"] == _sha(GOOD_HTML)
    assert by_label["cpi-release"]["admissibility"]["basis"] == "LOCAL_FIRST_SEEN"
    assert by_label["cpi-mirror"]["status"] == "DEDUPED"
    fed = by_label["fed-import"]
    assert fed["status"] == "ACCEPTED" and fed["admissibility"] == {"status": "ADMISSIBLE", "basis": "PUBLIC_AVAILABLE",
                                                                   "retained_dq_flags": ["BACKFILLED"]}
    refs = sources["accepted_references"]
    assert len(refs) == 2
    for ref in refs:
        assert RP.verify_raw_evidence_reference_identity(SG.rebuild_reference(ref))
    assert {r["retrieval_method"]: r["dq_flags"] for r in refs} == {"PROSPECTIVE_LOCAL_CAPTURE": ["OK"], "LATER_IMPORT": ["BACKFILLED"]}
    # a later import never carries a first-seen clock, so no downstream consumer can re-admit it as prospective
    imported = next(r for r in refs if r["retrieval_method"] == "LATER_IMPORT")
    assert imported["pit"]["local_first_seen_time"] is None and imported["pit"]["public_available_time"] == "2026-05-30T00:00:00Z"
    later = RP.evaluate_replay_admissibility(AS_OF, RP.ObservabilityEvidence(
        local_first_seen_time=imported["pit"]["local_first_seen_time"], public_available_time=imported["pit"]["public_available_time"]))
    assert later.basis == "PUBLIC_AVAILABLE"
    manifest = receipt["provenance_manifest"]
    assert manifest["input_evidence_reference_ids"] == [r["raw_evidence_reference_id"] for r in refs]
    assert manifest["output_hash"] == _sha(SG.canonical_bytes(receipt["core"]))
    assert manifest["information_cutoff"] == AS_OF and manifest["dq_flags"] == ["BACKFILLED"]
    rebuilt = RP.ResearchProvenanceManifest(**{k: tuple(v) if isinstance(v, list) else v for k, v in manifest.items()})
    assert RP.verify_research_provenance_manifest_identity(rebuilt)
    grounded = [c for c in receipt["core"]["benchmark"]["cases"] for s in c["subquestions"]
                if s["market_id"] == _mid("cpi") for i in s["items"] if by_label["cpi-release"]["raw_evidence_reference_id"] in i["claim_sources"]]
    assert grounded


# ------------------------------------------------------------------ R004

BLOCK_PAGE = b"<html>Attention Required! | Cloudflare " + b"x" * 300 + b"</html>"
LOGIN_PAGE = b"<html>Please log in to read this article " + b"y" * 300 + b"</html>"
INTERSTITIAL = b"<html>Checking your browser before accessing the site " + b"z" * 300 + b"</html>"


def test_source_grounding_404_block_thin_late_and_rule_mismatch_refusal(world, tmp_path):
    put = world["put"]
    long_ok = GOOD_HTML
    bad = [
        ("http-404", put("404.html", long_ok), long_ok, {"http_status": 404}, "HTTP_STATUS_404"),
        ("blocked", put("block.html", BLOCK_PAGE), BLOCK_PAGE, {}, "BLOCK_SIGNATURE"),
        ("interstitial", put("inter.html", INTERSTITIAL), INTERSTITIAL, {}, "BLOCK_SIGNATURE"),
        ("login", put("login.html", LOGIN_PAGE), LOGIN_PAGE, {}, "LOGIN_WALL"),
        ("thin", put("thin.html", b"<p>short</p>"), b"<p>short</p>", {}, "THIN_CONTENT"),
        ("binary", put("bin.html", b"\xff\xfe\x00" * 100), b"\xff\xfe\x00" * 100, {}, "INVALID_BYTES"),
        ("empty", put("empty.html", b""), b"", {}, "SOURCE_MISSING_OR_EMPTY"),
        ("changed-body", put("changed.html", long_ok + b" "), long_ok, {}, "SOURCE_BYTES_CHANGED"),
        ("future", put("future.html", long_ok), long_ok, {"local_first_seen_time": "2026-06-02T00:00:00Z",
                                                           "ingestion_time": "2026-06-01T11:00:00Z"}, "SOURCE_CLOCK_INCONSISTENT"),
        ("future-public", put("fp.html", long_ok), long_ok, {"local_first_seen_time": None,
                                                              "public_available_time": "2026-06-02T00:00:00Z"}, "FUTURE_CONTENT"),
        ("future-published", put("fpub.html", long_ok), long_ok, {"source_publish_time": "2026-09-01T00:00:00Z",
                                                                   "public_available_time": "2026-09-01T00:00:00Z"}, "FUTURE_CONTENT"),
        ("seen-before-published", put("sbp.html", long_ok), long_ok, {"source_publish_time": "2026-05-31T12:00:00Z",
                                                                       "public_available_time": "2026-05-31T12:00:00Z"},
         "SOURCE_CLOCK_INCONSISTENT"),
        ("redirect", put("302.html", long_ok), long_ok, {"http_status": 302}, "HTTP_STATUS_302"),
        ("status-zero", put("s0.html", long_ok), long_ok, {"http_status": 0}, "SOURCE_FIELDS_INVALID"),
        ("status-bool", put("sb.html", long_ok), long_ok, {"http_status": True}, "SOURCE_FIELDS_INVALID"),
        ("late-revision", put("late.html", long_ok), long_ok, {"revision_time": "2026-06-05T00:00:00Z"}, "LATE_REVISION"),
        ("no-clock", put("noclock.html", long_ok), long_ok, {"local_first_seen_time": None, "public_available_time": None},
         "NO_OBSERVABILITY_EVIDENCE"),
        ("bad-clock", put("badclock.html", long_ok), long_ok, {"public_available_time": "2026-05-30 00:00"}, "SOURCE_CLOCK_INVALID"),
        ("not-utc", put("notutc.html", long_ok), long_ok, {"public_available_time": "2026-05-30T00:00:00"}, "SOURCE_CLOCK_INVALID"),
        ("ingested-late", put("il.html", long_ok), long_ok, {"ingestion_time": "2026-06-03T00:00:00Z"}, "SOURCE_INGESTED_AFTER_CUTOFF"),
        ("ghost-market", put("ghost.html", long_ok), long_ok, {"market_id": "market:polymarket:ghost"}, "SOURCE_MARKET_NOT_IN_CORPUS"),
        ("cred-url", put("cred.html", long_ok), long_ok, {"url": "https://user:pw@example.invalid/x"}, "SOURCE_URL_UNSAFE"),
        ("token-url", put("tok.html", long_ok), long_ok, {"url": "https://example.invalid/x?token=abc"}, "SOURCE_URL_UNSAFE"),
        ("wrong-type", put("wt.html", long_ok), long_ok, {"http_status": "200"}, "SOURCE_FIELDS_INVALID"),
        ("null-mode", put("nm.html", long_ok), long_ok, {"capture_mode": None}, "SOURCE_FIELDS_INVALID"),
        ("cpi-release", put("dup.html", long_ok), long_ok, {}, "CONFLICTING_SOURCE_IDENTITY"),
    ]
    sources = [_source("cpi-release", "cpi", put("first.html", long_ok), long_ok)]
    for label, path, declared, overrides, _ in bad:
        sources.append(_source(label, "cpi", path, declared, **overrides))
    sources.append({"source_label": "missing-keys", "market_id": _mid("cpi")})
    sources.append("not-a-mapping")
    code, scratch, receipt = _run(tmp_path, dict(world["case"], sources=sources))
    assert code == 0
    entries = receipt["core"]["sources"]["entries"]
    assert len(entries) == len(sources)
    assert entries[0]["status"] == "ACCEPTED"
    for entry, (label, _, _, _, reason) in zip(entries[1:], bad):
        assert entry["status"] != "ACCEPTED" and entry["reason"] == reason, (label, entry)
        assert entry["raw_evidence_reference_id"] is None
    assert [e["reason"] for e in entries[-2:]] == ["SOURCE_FIELDS_INVALID", "SOURCE_FIELDS_INVALID"]
    assert len(receipt["core"]["sources"]["accepted_references"]) == 1
    rules = {e["index"]: e for e in receipt["core"]["corpus"]["rule_text_entries"]}
    assert rules[len(RULES)]["status"] == "RULE_HASH_MISMATCH"
    assert rules[len(RULES) + 1]["status"] == "RULE_MARKET_NOT_IN_CORPUS"
    gdp = [c for c in receipt["core"]["benchmark"]["cases"] for s in c["subquestions"] if s["market_id"] == _mid("gdp")]
    assert gdp and all("RULE_TEXT_UNAVAILABLE" in s["items"][1]["text"]
                       for c in gdp for s in c["subquestions"] if s["market_id"] == _mid("gdp"))
    assert receipt["core"]["corpus"]["rule_text_bound"] == len(RULES)
    assert _verify(scratch) == 0


# ------------------------------------------------------------------ R005


def test_source_grounding_dedup_missing_abstention_and_conflict_accounting(world, tmp_path):
    queries = list(world["case"]["queries"])
    queries += [dict(queries[0]),  # duplicate id
                {"query_id": "x-empty", "text": "the of and", "category_hint": None, "relevant_market_ids": []},
                {"query_id": "x-ghost", "text": "ghost market", "category_hint": None, "relevant_market_ids": ["market:polymarket:ghost"]},
                {"query_id": "x-duplab", "text": "Ohio Senate", "category_hint": None,
                 "relevant_market_ids": [_mid("oh-sen-dem"), _mid("oh-sen-dem")]},
                {"query_id": "x-missing", "text": "no labels key"},
                {"query_id": None, "text": "null id", "category_hint": None, "relevant_market_ids": []},
                {"query_id": "x-type", "text": 7, "category_hint": None, "relevant_market_ids": []}]
    code, scratch, receipt = _run(tmp_path, dict(world["case"], queries=queries))
    assert code == 0
    d = receipt["core"]["benchmark"]["denominators"]
    assert d["cases_total"] == len(queries) == d["cases_valid"] + d["cases_refused"]
    assert d["refused_by_reason"] == {"DUPLICATE_LABEL": 1, "DUPLICATE_QUERY_ID": 1, "LABEL_NOT_IN_CORPUS": 1,
                                      "QUERY_EMPTY": 1, "QUERY_FIELDS_INVALID": 3}
    assert receipt["core"]["benchmark"]["status"] == "COMPLETED" and d["positive_labeled"] == 39
    negatives = [c for c in receipt["core"]["benchmark"]["cases"] if c["status"] == "VALID" and not c["relevant"]]
    assert len(negatives) == 6 and sum(1 for c in negatives if c["ranker_status"] == "ABSTAINED") >= 1
    abstained = receipt["core"]["benchmark"]["metrics"][SG.RANKER_ID]["abstained"]
    assert abstained["denominator"] == d["cases_valid"]
    assert receipt["core"]["sources"]["counts"]["DUPLICATE_CONTENT"] == 1
    # case-level missing input stops the whole run (no silent partial corpus)
    broken = dict(world["case"])
    broken.pop("queries")
    assert _run(tmp_path, broken, "broken")[0] == 1


# ------------------------------------------------------------------ R006


def _copy(scratch, tmp_path, name):
    dst = tmp_path / name
    shutil.copytree(scratch, dst)
    return dst


def _rewrite(path, mutate, *, reid=False):
    receipt = json.loads(path.read_text(encoding="utf-8"))
    mutate(receipt)
    if reid:
        body = {"core": receipt["core"], "provenance_manifest": receipt["provenance_manifest"]}
        receipt["receipt_id"] = SG.RECEIPT_PREFIX + _sha(SG.canonical_bytes(body))
    path.write_text(json.dumps(receipt), encoding="utf-8")


def test_source_grounding_cold_verify_tamper_and_no_network(baseline_run, tmp_path, world, monkeypatch, capsys):
    scratch, receipt = baseline_run
    assert _verify(scratch) == 0
    assert json.loads(capsys.readouterr().out.strip().splitlines()[-1])["status"] == "VERIFIED"
    mutations = {
        "ranked": (lambda r: r["core"]["benchmark"]["cases"][0]["ranker"].reverse(), True),
        "ranked-noreid": (lambda r: r["core"]["benchmark"]["cases"][0]["ranker"].reverse(), False),
        "metric": (lambda r: r["core"]["benchmark"]["metrics"][SG.RANKER_ID]["recall_at_10"].update(numerator=44), True),
        "population": (lambda r: r["core"]["benchmark"]["denominators"].update(cases_total=30), True),
        "question-binding": (lambda r: r["core"]["benchmark"]["cases"][0].update(relevant=[_mid("gdp")]), True),
        "rule-binding": (lambda r: r["core"]["corpus"].update(rule_text_bound=0), True),
        "hash": (lambda r: r["core"]["sources"]["accepted_references"][0].update(content_sha256="0" * 64), True),
        "adoption": (lambda r: r["core"]["adoption"].update({"R3-02": "VALUE_VERIFIED"}), True),
        "manifest": (lambda r: r["provenance_manifest"].update(gap_summary="{}"), True),
        "core-not-mapping": (lambda r: r.update(core=["x"]), False),
        "non-identity-smuggle": (lambda r: r["non_identity"].update({"R3-02": "VALUE_VERIFIED"}), False),
        "non-identity-timing-type": (lambda r: r["non_identity"]["elapsed_ms"].update({SG.RANKER_ID: "fast"}), False),
    }
    for name, (mutate, reid) in mutations.items():
        dst = _copy(scratch, tmp_path, name)
        _rewrite(dst / "receipt.json", mutate, reid=reid)
        assert _verify(dst) == 1, name
    capsys.readouterr()
    altered = _copy(scratch, tmp_path, "bytes")
    (altered / "inputs" / "sources" / "000.bin").write_bytes(GOOD_HTML + b"tamper")
    assert _verify(altered) == 1
    assert "INPUT_BYTES_TAMPERED" in json.loads(capsys.readouterr().out.strip().splitlines()[-1])["failures"]
    store = _copy(scratch, tmp_path, "store")
    (store / "inputs" / "pit.sqlite3").write_bytes(b"not a store")
    assert _verify(store) == 1
    rule = _copy(scratch, tmp_path, "rule")
    (rule / "inputs" / "rules" / "000.bin").write_bytes(b"swapped rule")
    assert _verify(rule) == 1
    # a foreign receipt from a different (valid) run does not verify here
    other_case = dict(world["case"], case_label="src01-other")
    _, other, _ = _run(tmp_path, other_case, "other")
    foreign = _copy(scratch, tmp_path, "foreign")
    shutil.copyfile(other / "receipt.json", foreign / "receipt.json")
    assert _verify(foreign) == 1
    # every patched socket entry point is denied inside the guard and restored after it
    with CLI.no_network() as attempts:
        for call in (lambda: socket.gethostbyname("example.invalid"), lambda: socket.getaddrinfo("example.invalid", 80),
                     lambda: socket.socket().sendto(b"x", ("127.0.0.1", 9))):
            with pytest.raises(SG.GroundingStop):
                call()
    assert len(attempts) == 3 and socket.gethostbyname is not None and "deny" not in socket.getaddrinfo.__name__
    # any socket attempt inside the run is blocked and fails the run closed
    real = SG.rank_markets

    def leaky(index, query):
        try:
            socket.create_connection(("example.invalid", 80), timeout=0.01)
        except Exception:
            pass
        return real(index, query)
    monkeypatch.setattr(SG, "rank_markets", leaky)
    capsys.readouterr()
    code, _, leaked = _run(tmp_path, world["case"], "leak")
    assert code == 1 and leaked is None
    assert json.loads(capsys.readouterr().out.strip())["reason_code"] == "NETWORK_ATTEMPT_BLOCKED"
    assert receipt["core"]["authority"]["network_calls"] == 0 and receipt["core"]["authority"]["provider_calls"] == 0


# ------------------------------------------------------------------ R007


def test_source_grounding_legacy_baseline_unchanged_and_no_authority(world, baseline_run, tmp_path):
    before = {p: _sha(p.read_bytes()) for p in (world["pit"], world["alpha"])}
    policy = AD.build_alpha_discovery_policy(_policy_mapping()).record
    universe_before = AD.build_alpha_universe_snapshot(world["pit"], policy, AS_OF).record.alpha_universe_snapshot_id
    code, _, receipt = _run(tmp_path, world["case"])
    assert code == 0
    assert {p: _sha(p.read_bytes()) for p in before} == before
    assert AD.build_alpha_universe_snapshot(world["pit"], policy, AS_OF).record.alpha_universe_snapshot_id == universe_before
    authority = receipt["core"]["authority"]
    assert authority.pop("research_only") is True and not any(authority.values())
    forbidden = {"probability", "p_fair", "fair_value", "edge", "price", "order", "size", "side", "stake"}

    def keys(value, path=()):
        if isinstance(value, dict):
            for k, v in value.items():
                yield path + (k,)
                yield from keys(v, path + (k,))
        elif isinstance(value, list):
            for v in value:
                yield from keys(v, path)
    leaked = [p for p in keys(receipt["core"]) if p[0] != "authority" and set(p[-1].split("_")) & forbidden]
    assert leaked == []
    allowed = {"__future__", "collections", "dataclasses", "decimal", "hashlib", "json", "math", "pathlib", "re",
               "src.data_layer.analytical_research", "src.data_layer.point_in_time_market_research"}
    for path in (Path(SG.__file__), Path(CLI.__file__)):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        names = {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)} | \
                {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
        assert names <= allowed | {"argparse", "contextlib", "shutil", "socket", "sys", "time"}, names
    assert receipt["core"]["inputs"]["file_sha256"]["pit.sqlite3"] == before[world["pit"]]


@pytest.mark.parametrize("mutate, code", [
    (lambda c: c.pop("as_of"), "CASE_FIELDS_INVALID"),
    (lambda c: c.update(as_of=None), "AS_OF_INVALID"),
    (lambda c: c.update(as_of="2026-06-01 12:00"), "AS_OF_INVALID"),
    (lambda c: c.update(queries="all"), "CASE_LIST_INVALID"),
    (lambda c: c.update(queries=[]), "QUERIES_EMPTY"),
    (lambda c: c.update(api_key="x"), "FORBIDDEN_FIELD"),
    (lambda c: c.update(API_KEY="x"), "FORBIDDEN_FIELD"),
    (lambda c: c["queries"][0].update(order_side="BUY"), "FORBIDDEN_FIELD"),
    (lambda c: c["queries"][0].update(Wallet="w"), "FORBIDDEN_FIELD"),
    (lambda c: c["queries"][0].update(text="sk-" + "a" * 24), "SECRET_MATERIAL_REJECTED"),
    (lambda c: c.update(corpus_class="REAL_WORLD_LIFT"), "CORPUS_CLASS_INVALID"),
    (lambda c: c.update(schema_id="other"), "CASE_SCHEMA_INVALID"),
    (lambda c: c.update(pit_store="relative/pit.sqlite3"), "PIT_STORE_UNUSABLE"),
    (lambda c: c["policy"].update(queue_capacity="4"), "POLICY_INVALID"),
    (lambda c: c["policy"].update(client_secret="x"), "FORBIDDEN_FIELD"),
])
def test_case_negative_matrix(world, tmp_path, capsys, mutate, code):
    case = json.loads(json.dumps(world["case"]))
    mutate(case)
    capsys.readouterr()
    assert _run(tmp_path, case)[0] == 1
    assert json.loads(capsys.readouterr().out.strip())["reason_code"] == code


def test_scratch_and_input_boundaries(world, tmp_path, capsys):
    case_path = tmp_path / "case.json"
    case_path.write_text(json.dumps(world["case"]), encoding="utf-8")
    assert CLI.main(["run", "--case", str(case_path), "--scratch-dir", str(REPO_ROOT / "local_data" / "src01")]) == 1
    assert json.loads(capsys.readouterr().out.strip())["reason_code"] == "SCRATCH_INSIDE_REPOSITORY"
    busy = tmp_path / "busy"
    busy.mkdir()
    (busy / "x").write_text("x")
    assert CLI.main(["run", "--case", str(case_path), "--scratch-dir", str(busy)]) == 1
    assert json.loads(capsys.readouterr().out.strip())["reason_code"] == "SCRATCH_NOT_EMPTY"
    assert CLI.main(["run", "--case", str(tmp_path / "absent.json"), "--scratch-dir", str(tmp_path / "s2")]) == 1
    assert json.loads(capsys.readouterr().out.strip())["reason_code"] == "CASE_UNREADABLE"
    (tmp_path / "bad.json").write_text('{"a": NaN}', encoding="utf-8")
    assert CLI.main(["run", "--case", str(tmp_path / "bad.json"), "--scratch-dir", str(tmp_path / "s3")]) == 1
    assert json.loads(capsys.readouterr().out.strip())["reason_code"] == "CASE_JSON_INVALID"
    (tmp_path / "deep.json").write_text("[" * 200000 + "]" * 200000, encoding="utf-8")
    assert CLI.main(["run", "--case", str(tmp_path / "deep.json"), "--scratch-dir", str(tmp_path / "s5")]) == 1
    assert json.loads(capsys.readouterr().out.strip())["reason_code"] == "CASE_JSON_INVALID"
    assert CLI.main(["verify", "--scratch-dir", str(tmp_path / "s4-missing")]) == 1


def test_safe_wording_in_values_is_not_over_blocked(world, tmp_path):
    case = json.loads(json.dumps(world["case"]))
    case["queries"][0]["text"] = "Will the price of eggs and order of finish change? NOAA Central Park temperature"
    code, _, receipt = _run(tmp_path, case)
    assert code == 0 and receipt["core"]["benchmark"]["cases"][0]["status"] == "VALID"


# ------------------------------------------------------------------ R008


def test_source_grounding_report_truthful_adoption_receipt(baseline_run):
    _, receipt = baseline_run
    core = receipt["core"]
    assert core["posture"] == "RESEARCH_ONLY" and core["wp_id"] == "S10-R3-SRC-01"
    assert core["adoption"]["R3-02"] == "NOT_VALUE_VERIFIED" and "never real-world lift" in core["adoption"]["R3-02_reason"]
    assert core["adoption"]["R3-01-SOURCE_ARCHIVE"] == "INTEGRATED_OFFLINE_NOT_VALUE_VERIFIED"
    pins = {p["repository"]: p for p in core["source_pins"]}
    assert pins["Polymarket/agents"]["commit"] == "081f2b5594c37edeb9d3780a778c084d5b6f2743"
    assert pins["Metaculus/forecasting-tools"]["commit"] == "a54dd6443d19745b267e99a3b0b7627e74b9a57a"
    assert all(p["adoption_mode"] == "ADAPT_ALGORITHM_NO_CODE_COPIED" for p in pins.values())
    assert core["code_identity"] == CLI.code_identity() and receipt["receipt_id"].startswith(SG.RECEIPT_PREFIX)
    assert [c["query_id"] for c in core["benchmark"]["cases"]] == [q[0] for q in QUERIES]
    assert core["sources"]["counts"] == {"ACCEPTED": 2, "DUPLICATE_CONTENT": 1}
    assert "elapsed_ms" in receipt["non_identity"] and "non_identity" not in core
    contract = (REPO_ROOT / "docs" / "source_grounding_contract.md").read_text(encoding="utf-8")
    assert CORPUS_SHA256 in contract and SG.RANKER_ID in contract and SG.BASELINE_ID in contract
