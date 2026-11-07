"""S10-R3-EXT-CONTRACTS-01 offline tests: verified SRC-01 scratch -> real CLI -> field-aware search,
py-sdk search projection and CCXT prediction identity -> receipt -> cold verify.

The corpus is SANITIZED_SYNTHETIC: the frozen S10-R3-SRC-01 markets/queries re-keyed to canonical
decimal ids plus adversarial identity markets. Method parameters in public_market_contract_parity.py
were fixed before these cases were written and were not tuned on them. Results prove callable
behaviour and honest accounting only, never real-world search value.
"""
from __future__ import annotations

import ast
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket

import pytest

from src.data_layer.analytical_research import alpha_discovery as AD
from src.data_layer.analytical_research import public_market_contract_parity as PMC
from src.data_layer.analytical_research import source_grounding as SG
from tests.data_layer.analytical_research.test_alpha_discovery import _pit_built, _pit_store
from tests.tools.alpha.test_source_grounding import MARKETS as SRC_MARKETS, QUERIES as SRC_QUERIES, RULES, _policy_mapping
from tools.alpha import run_public_market_contract_parity as CLI
from tools.alpha import run_source_grounding as SGCLI

REPO_ROOT = Path(__file__).resolve().parents[3]
AS_OF = "2026-06-01T12:00:00Z"
OBSERVED, INGESTED = "2026-06-01T00:00:01Z", "2026-06-01T00:00:02Z"

# (slug, event, category, question, date, status, labels, override)
EXTRA = (
    ("closed-mkt", "nba-finals-2025", "sports", "Will the Denver Nuggets win the 2025 NBA Finals?", "2025-06-30", "closed", None, None),
    ("nocat", "lisbon-heat-2026", None, "Will Lisbon record a heatwave in August 2026?", "2026-09-01", "open", None, None),
    ("tri", "lisbon-mayor-2026", "politics", "Which party wins the 2026 Lisbon mayoral race?", "2026-10-01", "open", ["A", "B", "C"], None),
    ("collide-a", "berlin-chess-2026", "misc", "Will Berlin host the 2026 chess olympiad?", "2026-12-31", "open", None, "COLLIDE"),
    ("collide-b", "berlin-rowing-2026", "misc", "Will Berlin host the 2026 rowing world championships?", "2026-12-31", "open", None, "COLLIDE"),
    ("dupcond-a", "oslo-event-a", "misc", "Will Oslo open the new opera wing in 2026?", "2026-12-31", "open", None, "DUPCOND"),
    ("dupcond-b", "oslo-event-b", "misc", "Will Oslo open the new metro line in 2026?", "2026-12-31", "open", None, "DUPCOND"),
    ("legacy", "legacy-event", "misc", "Will the legacy slug market keep its old identifier?", "2026-12-31", "open", None, "LEGACY"),
)
ALL = [(s, e, c, q, d, "open", None, None) for s, e, c, q, d in SRC_MARKETS] + list(EXTRA)
SLUGS = [m[0] for m in ALL]


def dec(slug):
    return str(700000 + SLUGS.index(slug))


def mid(slug):
    return "market:polymarket:legacy-slug" if slug == "legacy" else f"market:polymarket:{dec(slug)}"


def cond(slug):
    return "0x" + hashlib.sha256(("dupcond" if slug.startswith("dupcond") else slug).encode()).hexdigest()


def tokens(slug):
    i = SLUGS.index(slug)
    no, yes = str(10**20 + 2 * i), str(10**20 + 2 * i + 1)
    if slug == "collide-b":
        no = tokens("collide-a")[0]
    return no, yes


def event_id(slug):
    return "event:polymarket:synthetic-" + next(m[1] for m in ALL if m[0] == slug)


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _pit_records():
    records = []
    times = dict(observed_time=OBSERVED, ingestion_time=INGESTED)
    for slug, event, category, question, date, status, labels, _ in ALL:
        no, yes = tokens(slug)
        token_list = [f"token:polymarket:{no}", f"token:polymarket:{yes}"] + ([f"token:polymarket:{int(yes) + 9 * 10**19}"] if labels else [])
        payload = {"market_status": status, "outcome_labels": labels or ["No", "Yes"], "question_text": question,
                   "token_ids": token_list, "condition_id": cond(slug), "category": category,
                   "resolution_date": date + "T00:00:00Z"}
        meta, _ = _pit_built("PIT-C01-VALID-MARKET-METADATA", platform_id="platform:polymarket", event_id=event_id(slug),
                             market_id=mid(slug), source_id="source:polymarket:gamma-markets",
                             source_assertion_id=f"assertion:ext01:meta:{slug}", snapshot_id=f"snapshot:ext01:meta:{slug}",
                             source_snapshot_id=f"source-snapshot:ext01:meta:{slug}", event_time="2026-06-01T00:00:00Z",
                             canonical_payload=payload, **times)
        records.append(meta)
        if slug in RULES:
            source, _ = _pit_built("PIT-C04-VALID-SOURCE-SNAPSHOT", source_id=f"source:ext01:rules:{slug}",
                                   snapshot_id=f"snapshot:ext01:rulesrc:{slug}", **times)
            rule, _ = _pit_built("PIT-C05-VALID-RESOLUTION-RULE-SNAPSHOT", platform_id="platform:polymarket",
                                 event_id=event_id(slug), market_id=mid(slug),
                                 resolution_source_id="resolution-source:polymarket:primary",
                                 source_snapshot_id=source.envelope.source_snapshot_id,
                                 rule_content_sha256=_sha(RULES[slug].encode()), snapshot_id=f"snapshot:ext01:rule:{slug}",
                                 observed_time="2026-06-01T00:00:03Z", ingestion_time="2026-06-01T00:00:04Z")
            records.extend((source, rule))
    return records


def _q(q=None, **filters):
    return {"q": q, **filters}


def _case(case_id, query, labels, decision_time=None):
    return {"case_id": case_id, "decision_time": decision_time, "query": query, "expected_market_ids": [mid(s) for s in labels]}


CASES = [_case(q, _q(t, events_tag=None), rel) for q, t, _hint, rel in SRC_QUERIES] + [
    _case("x01", _q(market_id=mid("nyc-temp")), ["nyc-temp"]),
    _case("x02", _q("CPI inflation", condition_id=cond("cpi")), ["cpi"]),
    _case("x03", _q("Finals", event_id=event_id("nba-celtics")), ["nba-celtics", "nba-thunder"]),
    _case("x04", _q(market_id="market:polymarket:999999999"), []),
    _case("x05", _q(market_id=mid("collide-a")), ["collide-a"]),
    _case("f01", _q("NBA Finals", events_status="closed"), ["closed-mkt"]),
    _case("f02", _q("hurricane 2026", events_tag="weather", resolution_before="2026-12-01T00:00:00Z"),
          ["hurricane-cat5", "hurricane-landfall"]),
    _case("f03", _q("Federal Reserve September", require_rule=True), ["fed-cut-sep"]),
    _case("f04", _q("Lisbon heatwave August", events_tag="weather"), ["nocat"]),
    _case("f05", _q(market_id=mid("nocat"), events_tag="weather"), ["nocat"]),
    _case("a01", _q("Central Park high above 95F July 4"), ["nyc-temp", "nyc-temp-lga"]),
    _case("t01", _q("Ohio Senate"), ["oh-sen-dem", "oh-sen-rep"], decision_time="2026-05-01T00:00:00Z"),
    _case("tri01", _q("Lisbon mayoral race party"), ["tri"]),
    {"case_id": "bad01", "decision_time": None, "query": _q("fake label"), "expected_market_ids": ["market:polymarket:424242"]},
    _case("r01", _q("duplicate id"), ["cpi"]),
]


def gamma_market(slug, labels=("No", "Yes"), toks=None, **extra):
    no, yes = tokens(slug)
    toks = list(toks) if toks is not None else ([no, yes] if list(labels) == ["No", "Yes"] else [yes, no])
    return {"id": dec(slug), "conditionId": cond(slug), "outcomes": json.dumps(list(labels)), "clobTokenIds": json.dumps(toks),
            "active": True, "closed": False, **extra}


def ccxt_vectors():
    no, yes = tokens("cpi")
    return [
        {"vector_id": "c01", "venue_product": "prediction", "market": gamma_market("cpi")},
        {"vector_id": "c02", "venue_product": "prediction", "market": gamma_market("cpi", labels=("Yes", "No"), toks=[no, yes])},
        {"vector_id": "c03", "venue_product": "ccxt.polymarket", "market": dict(gamma_market("gdp"), swap=True, type="swap")},
        {"vector_id": "c04", "venue_product": "spot", "market": gamma_market("gdp")},
        {"vector_id": "c05", "venue_product": "prediction", "market": gamma_market("gdp", toks=[tokens("gdp")[0]])},
        {"vector_id": "c06", "venue_product": "prediction", "market": gamma_market("gdp", toks=[tokens("gdp")[0]] * 2)},
        {"vector_id": "c07", "venue_product": "prediction", "market": dict(gamma_market("gdp"), conditionId="0xABC")},
        {"vector_id": "c08", "venue_product": "prediction", "market": gamma_market("gdp", toks=["0x1f", tokens("gdp")[1]])},
        {"vector_id": "c09", "venue_product": "prediction", "market": gamma_market("gdp", toks=[tokens("gdp")[0], "123"])},
        {"vector_id": "c10", "venue_product": "prediction",
         "market": gamma_market("tri", labels=("A", "B", "C"), toks=[*tokens("tri"), str(int(tokens("tri")[1]) + 9 * 10**19)])},
        {"vector_id": "c11", "venue_product": "prediction", "market": dict(gamma_market("gdp"), id="999999999")},
        {"vector_id": "c12", "venue_product": "prediction", "market": gamma_market("collide-a")},
        {"vector_id": "c13", "venue_product": "prediction", "market": dict(gamma_market("ecb"), closed=True, umaResolutionStatus="resolved")},
    ]


def py_sdk_vectors():
    page_markets = [{"id": dec(s), "conditionId": cond(s)} for s in ("nba-celtics", "nba-thunder")]
    return [
        {"vector_id": "s01", "request": {"q": "2026 NBA Finals", "search_tags": True, "search_profiles": True, "page_size": 3},
         "response_page": {"events": [{"id": "9001", "title": "NBA Finals 2026", "markets": page_markets}],
                           "tags": [{"id": "1", "label": "NBA"}], "profiles": [{"id": "p1", "name": "fan"}]}},
        {"vector_id": "s02", "request": {"q": "FIFA World Cup", "sort": "volume", "recurrence": "daily", "brand_new": 1},
         "response_page": {"events": [{"id": "9002", "markets": [{"id": dec("wc-brazil"), "conditionId": cond("wc-brazil")}]}]}},
        {"vector_id": "s03", "request": {"q": "unknown"},
         "response_page": {"events": [{"id": "9003", "markets": [{"id": "999999999", "conditionId": cond("cpi")}]}]}},
        {"vector_id": "s04", "request": {"q": "CPI"},
         "response_page": {"events": [{"id": "9004", "markets": [{"id": dec("cpi"), "conditionId": cond("gdp")}]}]}},
        {"vector_id": "s05", "request": {"q": "mixed"},
         "response_page": {"events": [{"id": "9005", "markets": [{"id": dec(s), "conditionId": cond(s)} for s in ("cpi", "gdp")]}]}},
        {"vector_id": "s06", "request": {"q": "bad page", "page_size": 0}, "response_page": {"events": []}},
    ]


def build_cases(receipt_id, corpus_class="SANITIZED_SYNTHETIC", cases=None, **overrides):
    value = {"schema_id": PMC.CASES_SCHEMA, "corpus_class": corpus_class, "grounding_receipt_id": receipt_id, "as_of": AS_OF,
             "label_source": PMC.CORPUS_LABEL_SOURCES[corpus_class], "benchmark_sha256": "0" * 64,
             "cases": json.loads(json.dumps(CASES if cases is None else cases)),  # never alias the frozen module list
             "upstream_vectors": {"py_sdk_search": py_sdk_vectors(), "ccxt_prediction_markets": ccxt_vectors()}}
    value["benchmark_sha256"] = PMC.benchmark_commitment(value)
    value.update(overrides)
    return value


def make_world(base, corpus_class="SANITIZED_SYNTHETIC"):
    base.mkdir(parents=True, exist_ok=True)
    pit = _pit_store(base, _pit_records())

    def put(name, data):
        path = (base / name).resolve()
        path.write_bytes(data)
        return path
    rules = [{"market_id": mid(s), "file": str(put(f"rule-{s}.txt", t.encode()))} for s, t in RULES.items()]
    case = {"schema_id": SG.CASE_SCHEMA, "case_label": "ext01-grounding", "corpus_class": corpus_class, "pit_store": str(pit),
            "alpha_registry": None, "policy": _policy_mapping(), "as_of": AS_OF, "rule_texts": rules, "sources": [],
            "queries": [{"query_id": "g01", "text": "Ohio Senate", "category_hint": None,
                         "relevant_market_ids": [mid("oh-sen-dem")]}]}
    grounding = (base / "grounding").resolve()
    assert SGCLI.main(["run", "--case", str(put("grounding-case.json", json.dumps(case).encode())),
                       "--scratch-dir", str(grounding)]) == 0
    receipt_id = json.loads((grounding / "receipt.json").read_text(encoding="utf-8"))["receipt_id"]
    return {"base": base, "pit": pit, "grounding": grounding, "receipt_id": receipt_id, "put": put}


def run_cli(tmp_path, world, cases, name="ext", grounding=None):
    path = tmp_path / f"{name}-cases.json"
    path.write_text(json.dumps(cases), encoding="utf-8")
    scratch = (tmp_path / name).resolve()
    code = CLI.main(["run", "--grounding-scratch", str(grounding or world["grounding"]), "--cases", str(path),
                     "--scratch-dir", str(scratch)])
    receipt = scratch / "receipt.json"
    return code, scratch, json.loads(receipt.read_text(encoding="utf-8")) if receipt.exists() else None


def last(capsys):
    return json.loads(capsys.readouterr().out.strip().splitlines()[-1])


def tree(root):
    return {p.relative_to(root).as_posix(): (_sha(p.read_bytes()), p.stat().st_mtime_ns) for p in Path(root).rglob("*") if p.is_file()}


@pytest.fixture(scope="module")
def world(tmp_path_factory):
    return make_world(tmp_path_factory.mktemp("ext01_inputs"))


@pytest.fixture(scope="module")
def baseline(world, tmp_path_factory):
    code, scratch, receipt = run_cli(tmp_path_factory.mktemp("ext01_run"), world, build_cases(world["receipt_id"]))
    assert code == 0, receipt
    return scratch, receipt


def rows(receipt):
    return {r["case_id"]: r for r in receipt["core"]["benchmark"]["cases"] if r["case_id"] and r["status"] != "REFUSED"}


def markets(receipt):
    return {m["market_id"]: m for m in receipt["core"]["corpus"]["markets"]}


# ------------------------------------------------------------------ R001


def test_ext_native_src_cold_verify_and_actual_pit_consumer(world, tmp_path, monkeypatch, capsys):
    verified, loaded, ranked = [], [], []
    real_verify, real_load, real_rank = SGCLI.verify, SG.load_corpus, SG.rank_markets
    monkeypatch.setattr(SGCLI, "verify", lambda p: verified.append(Path(p)) or real_verify(p))
    monkeypatch.setattr(SG, "load_corpus", lambda *a: loaded.append(Path(a[0])) or real_load(*a))
    monkeypatch.setattr(SG, "rank_markets", lambda i, q: ranked.append(q) or real_rank(i, q))
    code, scratch, receipt = run_cli(tmp_path, world, build_cases(world["receipt_id"]))
    assert code == 0 and receipt
    core = receipt["core"]
    # caller bytes verified first, then the frozen copy; every corpus load reads only the frozen copy
    assert verified[0] == world["grounding"] and verified[1] == scratch / "inputs" / "grounding"
    frozen_pit = scratch / "inputs" / "grounding" / "inputs" / "pit.sqlite3"
    # one read-only load inside the native verifier of the caller bytes; everything after reads the frozen copy
    assert loaded[0] == world["grounding"] / "inputs" / "pit.sqlite3" and loaded[1:] and set(loaded[1:]) == {frozen_pit}
    # two calls come from the native verifier recomputing the grounding receipt's own query (caller + frozen copy)
    assert len(ranked) == 2 + core["benchmark"]["denominators"]["cases_valid_paired"]
    native = AD.build_alpha_universe_snapshot(world["pit"], AD.build_alpha_discovery_policy(_policy_mapping()).record, AS_OF).record
    assert core["inputs"]["alpha_universe_snapshot_id"] == native.alpha_universe_snapshot_id
    assert core["inputs"]["grounding_receipt_id"] == world["receipt_id"] and core["inputs"]["grounding_verification"] == "VERIFIED"
    assert sorted(markets(receipt)) == sorted(m.market_id for m in native.markets) and len(native.markets) == len(ALL)
    assert core["caller"] == PMC.CALLER

    # tampered SRC-01 bytes: no success receipt
    bad = (tmp_path / "tampered").resolve()
    shutil.copytree(world["grounding"], bad)
    pit = bad / "inputs" / "pit.sqlite3"
    pit.write_bytes(pit.read_bytes()[:-1] + b"\x00")
    code, scratch2, receipt2 = run_cli(tmp_path, world, build_cases(world["receipt_id"]), name="t1", grounding=bad)
    assert code == 1 and receipt2 is None and last(capsys) == {"status": "STOPPED", "reason_code": "GROUNDING_RECEIPT_NOT_VERIFIED"}
    assert not scratch2.exists() or not any(scratch2.iterdir())
    # foreign receipt id
    code, _, receipt3 = run_cli(tmp_path, world, build_cases(SG.RECEIPT_PREFIX + "a" * 64), name="t2")
    assert code == 1 and receipt3 is None and last(capsys)["reason_code"] == "GROUNDING_RECEIPT_MISMATCH"
    # non-verified source: receipt removed
    unverified = (tmp_path / "unverified").resolve()
    shutil.copytree(world["grounding"], unverified)
    (unverified / "receipt.json").unlink()
    code, _, receipt4 = run_cli(tmp_path, world, build_cases(world["receipt_id"]), name="t3", grounding=unverified)
    assert code == 1 and receipt4 is None and last(capsys)["reason_code"] == "GROUNDING_RECEIPT_NOT_VERIFIED"


# ------------------------------------------------------------------ R002


def test_ext_py_sdk_search_event_tag_profile_contract(baseline, world, tmp_path, capsys):
    _, receipt = baseline
    pins = {p["capability"]: p for p in receipt["core"]["source_pins"]}
    assert pins["R3-23"]["commit"] == "aa94ec431e3d4946576fb7c0d079fe1c14fcf676"
    assert pins["R3-23"]["files"] == {"examples/search.py": "895d728f438e42f2b795138b08b308fab568edbc",
                                      "src/polymarket/clients/public.py": "c0e1d178555604172474ba6031e9ce833f447821"}
    contract = receipt["core"]["upstream_contracts"]["R3-23_py_sdk_search"]
    assert contract["online_fetch"] is False and contract["tags_unsupported"] == 1 and contract["profiles_unsupported"] == 1
    v = {x["vector_id"]: x for x in contract["vectors"]}
    s01 = v["s01"]
    assert s01["status"] == "PROJECTED" and s01["tags"] == s01["profiles"] == ["TAG_OR_PROFILE_UNSUPPORTED"]
    assert s01["events"][0]["status"] == "EVENT_PROJECTED" and s01["events"][0]["event_identity"] == "EVENT_ID_UNVERIFIED"
    assert s01["events"][0]["native_market_ids"] == [mid("nba-celtics"), mid("nba-thunder")]
    page = s01["native_page"]
    assert set(page) >= {"events", "tags", "profiles"} and page["items_per_page"] == 1 and page["tags"] == page["profiles"] == []
    assert page["tags_status"] == page["profiles_status"] == "TAG_OR_PROFILE_UNSUPPORTED"
    assert sum(len(e["market_ids"]) for e in page["events"]) <= 3
    assert s01["agreement"] == {"upstream_projected_markets": 2, "native_page_markets": 3, "shared": 2,
                                "parity": "PARTIAL_EVENT_MARKET_ONLY"}
    assert v["s02"]["parameters"] == {"brand_new": "PARAMETER_UNKNOWN", "q": "SUPPORTED", "recurrence": "PARAMETER_UNSUPPORTED",
                                      "sort": "PARAMETER_UNSUPPORTED"}
    assert v["s02"]["native_page"]["tags_status"] == "NOT_REQUESTED"
    assert v["s03"]["events"][0]["status"] == "NOT_IN_UNIVERSE"
    assert v["s04"]["events"][0]["status"] == "IDENTITY_CONFLICT"
    assert v["s05"]["events"][0]["status"] == "EVENT_RELATION_CONFLICT"
    assert v["s06"]["status"] == "REQUEST_OR_PAGE_INVALID"
    assert contract["status_counts"] == {"PROJECTED": 5, "REQUEST_OR_PAGE_INVALID": 1}
    # an untrusted profile carrying a wallet field is refused outright, never parsed
    cases = build_cases(world["receipt_id"])
    cases["upstream_vectors"]["py_sdk_search"][0]["response_page"]["profiles"][0]["wallet"] = "0x" + "1" * 40
    code, _, r = run_cli(tmp_path, world, cases, name="wallet")
    assert code == 1 and r is None and last(capsys)["reason_code"] == "FORBIDDEN_FIELD"


# ------------------------------------------------------------------ R003


def test_ext_ccxt_prediction_market_identity_outcome_orientation(baseline):
    _, receipt = baseline
    pin = next(p for p in receipt["core"]["source_pins"] if p["capability"] == "R3-27")
    assert pin["files"] == {"ts/src/prediction/polymarket.ts": "d7fb1dff7b440c86a987f0f3be948883ae1f0907"}
    assert "PERPETUAL_FUTURES_NOT_PREDICTION" in pin["excluded_files"]["ts/src/polymarket.ts"]
    ccxt = receipt["core"]["upstream_contracts"]["R3-27_ccxt_prediction"]
    v = {x["vector_id"]: x for x in ccxt["vectors"]}
    c01 = v["c01"]
    assert c01["status"] == "NORMALIZED" and c01["native_cross_check"] == "IDENTITY_CONSISTENT"
    n = c01["normalized"]
    assert n["id"] == cond("cpi") and n["type"] == "prediction" and n["prediction"] is True and n["swap"] is False
    assert n["marketType"] == "binary" and n["active"] is True and n["resolved"] is False
    assert [o["outcomeId"] for o in n["outcomes"]] == [f"token:polymarket:{t}" for t in tokens("cpi")]
    # a positional upstream claim is recorded, never promoted to proven orientation or a side
    assert c01["upstream_yes_token_claim"] == f"token:polymarket:{tokens('cpi')[1]}"
    assert v["c02"]["upstream_yes_token_claim"] == f"token:polymarket:{tokens('cpi')[0]}"
    assert v["c01"]["orientation_flag"] == v["c02"]["orientation_flag"] == "UPSTREAM_ORIENTATION_CLAIMS_DISAGREE"
    assert all(x["orientation"] == "ORIENTATION_UNPROVEN" and x["tradable_side"] is None for x in ccxt["vectors"])
    assert ccxt["orientation_proven"] == ccxt["tradable_sides_assigned"] == 0
    assert v["c03"]["status"] == "PERPETUAL_PRODUCT_REJECTED" and v["c04"]["status"] == "PRODUCT_NOT_PREDICTION"
    assert v["c05"]["status"] == "OUTCOME_TOKEN_LENGTH_MISMATCH" and v["c06"]["status"] == "TOKEN_COLLISION"
    assert v["c07"]["status"] == "CONDITION_ID_INVALID" and v["c08"]["status"] == "TOKEN_ID_NONCANONICAL"
    assert v["c09"]["native_cross_check"] == "IDENTITY_CONFLICT"
    assert v["c10"]["normalized"]["marketType"] == "categorical" and v["c10"]["upstream_yes_token_claim"] is None
    assert v["c11"]["native_cross_check"] == "NOT_IN_UNIVERSE" and v["c12"]["native_cross_check"] == "NATIVE_IDENTITY_ABSTAINED"
    assert v["c13"]["normalized"]["resolved"] is True and v["c13"]["normalized"]["active"] is False
    # native identity: every row unoriented; adversarial rows abstain with explicit defects
    rows_ = markets(receipt)
    assert all(r["orientation"] == "ORIENTATION_UNPROVEN" and r["yes_token_id"] is None and r["tradable_side"] is None
               for r in rows_.values())
    assert rows_[mid("cpi")]["identity_status"] == "VALID" and rows_[mid("cpi")]["outcome_labels"] == ["No", "Yes"]
    assert "TOKEN_COLLISION" in rows_[mid("collide-a")]["identity_defects"] == rows_[mid("collide-b")]["identity_defects"]
    assert {"DUPLICATE_CONDITION", "EVENT_RELATION_CONFLICT"} <= set(rows_[mid("dupcond-a")]["identity_defects"])
    assert rows_["market:polymarket:legacy-slug"]["identity_defects"] == ["MARKET_ID_NONCANONICAL"]
    assert rows_[mid("tri")]["market_type"] == "categorical" and rows_[mid("tri")]["identity_status"] == "VALID"
    assert receipt["core"]["corpus"]["orientation_proven"] == 0
    # direct adversarial unit vectors
    assert PMC.normalize_ccxt_prediction({"vector_id": "u1", "venue_product": "perpetual", "market": {}}, {})["status"] \
        == "PERPETUAL_PRODUCT_REJECTED"
    assert PMC.normalize_ccxt_prediction({"vector_id": "u2", "venue_product": "prediction",
                                          "market": dict(gamma_market("cpi"), outcomes="not json")}, {})["status"] == "OUTCOMES_MISSING"
    assert PMC.normalize_ccxt_prediction(["not", "a", "dict"], {})["status"] == "VECTOR_FIELDS_INVALID"


# ------------------------------------------------------------------ R004


def test_ext_field_aware_search_market_filter_and_native_candidate_receipt(baseline, world):
    scratch, receipt = baseline
    r = rows(receipt)
    method = PMC.METHOD_ID
    assert r["x01"][method] == [mid("nyc-temp")] and r["x02"][method] == [mid("cpi")]
    assert set(r["x03"][method]) == {mid("nba-celtics"), mid("nba-thunder")}
    assert r["x04"]["method_reason"] == "NOT_IN_UNIVERSE" and r["x04"][method] == []
    assert r["x05"]["method_reason"] == "NO_ADMISSIBLE_MATCH" and r["x05"]["method_excluded"] == {"IDENTITY_ABSTAINED": 1}
    assert r["f01"][method] == [mid("closed-mkt")]
    assert set(r["f02"][method][:2]) == {mid("hurricane-cat5"), mid("hurricane-landfall")}  # "2026" also matches others
    assert all(markets(receipt)[m]["category"] == "weather" for m in r["f02"][method])
    # rule-presence filter: the unruled sibling is excluded, the text-only ablation still returns it
    assert r["f03"][method][0] == mid("fed-cut-sep") and mid("fed-hold-sep") not in r["f03"][method]
    assert mid("fed-hold-sep") in r["f03"][PMC.ABLATION_ID]
    assert r["f05"]["method_reason"] == "MISSING_METADATA" and r["f05"]["method_excluded"] == {"MISSING_METADATA": 1}
    assert r["a01"]["method_reason"] == "AMBIGUOUS" and r["a01"][method] == []
    assert r["t01"]["status"] == "ABSTAINED" and r["t01"]["reason"] == "POST_CUTOFF"
    assert r["tri01"][method][0] == mid("tri")
    native_ids = set(markets(receipt))
    assert all(set(x[method]) <= native_ids for x in r.values())
    assert set(receipt["core"]["benchmark"]["method_abstention_reasons"]) <= set(PMC.REASONS)
    # deterministic: same index and query give the same ordering
    case = json.loads((scratch / "inputs" / "cases.json").read_text(encoding="utf-8"))
    core = CLI._core(scratch, {"status": "VERIFIED", "receipt_id": world["receipt_id"]})
    assert core == receipt["core"] and case["cases"][0]["case_id"] == "r01"
    # candidates are research-only, human-reviewed, and nothing is promoted or written back
    auth = receipt["core"]["authority"]
    assert auth["advisory_only"] and auth["human_review_required"] and not auth["alpha_promotion"]
    assert not auth["canonical_writes"] and not auth["wp170_registry_writes"] and not auth["tradable_side"]
    assert all(m["rules"] is not None and m["metadata_record_version_id"] for m in receipt["core"]["corpus"]["markets"])
    assert SGCLI.verify(world["grounding"])["status"] == "VERIFIED"  # caller scratch untouched


# ------------------------------------------------------------------ R005


def test_ext_real_local_pit_admissibility_and_temporal_abstention(baseline, tmp_path, capsys):
    _, synthetic = baseline
    assert synthetic["core"]["real_benchmark"] == "NOT_RUN_NO_GENUINE_LOCAL_REAL_PIT_SUPPLIED"
    real = make_world(tmp_path / "real", corpus_class="LOCAL_REAL_PIT")
    code, _, receipt = run_cli(tmp_path, real, build_cases(real["receipt_id"], corpus_class="LOCAL_REAL_PIT"))
    assert code == 0 and receipt
    core = receipt["core"]
    native = AD.build_alpha_universe_snapshot(real["pit"], AD.build_alpha_discovery_policy(_policy_mapping()).record, AS_OF).record
    # the caller's own PIT is consumed as-is: no fixture substitution, no synthetic fallback
    assert core["inputs"]["alpha_universe_snapshot_id"] == native.alpha_universe_snapshot_id
    assert core["corpus_class"] == "LOCAL_REAL_PIT" and core["label_source"] == "CALLER_SUPPLIED_UNVERIFIED"
    assert core["real_benchmark"] == "OBSERVED_CALLER_LABELS_AWAITING_INDEPENDENT_REVIEW"
    assert core["corpus"]["source_authenticity"] == "LOCAL_PIT_SOURCE_ORIGIN_UNVERIFIED"
    assert all(m["metadata_observed_time"] == OBSERVED for m in core["corpus"]["markets"])
    # valid partial coverage survives: abstaining identities do not stop the run
    assert 0 < core["corpus"]["identity_valid"] < core["corpus"]["markets_total"]
    assert core["corpus"]["identity_defect_counts"]["TOKEN_COLLISION"] == 2
    for cases, code_ in (
            (build_cases(real["receipt_id"], corpus_class="SANITIZED_SYNTHETIC"), "CORPUS_CLASS_MISMATCH"),
            (build_cases(real["receipt_id"], corpus_class="LOCAL_REAL_PIT", label_source="CALLER_SUPPLIED_SYNTHETIC"), "LABEL_SOURCE_INVALID"),
            (build_cases(real["receipt_id"], corpus_class="LOCAL_REAL_PIT", as_of="2026-06-02T12:00:00Z"), "AS_OF_CONFLICT"),
            (build_cases(real["receipt_id"], corpus_class="LOCAL_REAL_PIT", as_of="2026-06-01 12:00"), "AS_OF_INVALID")):
        code, _, r = run_cli(tmp_path, real, cases, name=f"neg-{code_}")
        assert code == 1 and r is None and last(capsys)["reason_code"] == code_
    # direct temporal and metadata abstentions on the native identity table
    universe = AD.build_alpha_universe_snapshot(real["pit"], AD.build_alpha_discovery_policy(_policy_mapping()).record,
                                                "2026-06-01T00:00:03Z").record
    rows_ = PMC.normalize_native(universe, {})
    late = universe.markets[0].__class__(**{**universe.markets[0].__dict__, "metadata_observed_time": "2026-06-02T00:00:00Z"})
    assert "POST_CUTOFF" in PMC.normalize_native(universe.__class__(**{**universe.__dict__, "markets": (late,)}), {})[late.market_id]["identity_defects"]
    index = PMC.build_field_index(universe, {}, rows_)
    assert PMC.field_aware_search(index, {"q": "Lisbon heatwave", "events_tag": "weather"})["excluded"]["MISSING_METADATA"] == 1
    assert PMC.field_aware_search(index, {"q": "Ohio Senate", "require_rule": True})["reason"] == "MISSING_METADATA"
    # a non-canonical native resolution date abstains per market instead of aborting the run
    odd = universe.markets[0].__class__(**{**universe.markets[0].__dict__, "resolution_date": "2026-13"})
    odd_universe = universe.__class__(**{**universe.__dict__, "markets": (odd,)})
    odd_index = PMC.build_field_index(odd_universe, {}, PMC.normalize_native(odd_universe, {}))
    assert PMC.field_aware_search(odd_index, {"market_id": odd.market_id, "resolution_after": "2026-01-01T00:00:00Z"})["reason"] \
        == "MISSING_METADATA"


# ------------------------------------------------------------------ R006


def test_ext_same_corpus_baseline_comparison_50_cases_and_exact_denominators(baseline, world, tmp_path, capsys):
    _, receipt = baseline
    bench = receipt["core"]["benchmark"]
    assert bench["status"] == "COMPLETED" and bench["lift_claim"] is None and bench["real_value"] == "NOT_VERIFIED"
    assert bench["denominators"] == {"cases_input": 60, "cases_valid_paired": 57, "cases_refused": 2,
                                     "cases_abstained_pre_scoring": 1, "positive_labeled": 50, "negative_no_match": 7,
                                     "exact_identifier_cases": 6,
                                     "excluded_by_reason": {"DUPLICATE_CASE_ID": 1, "LABEL_NOT_IN_CORPUS": 1, "POST_CUTOFF": 1},
                                     "snapshot_time_conflicts": 1}
    valid = [c for c in bench["cases"] if c["status"] == "VALID"]
    pos = [c for c in valid if c["relevant"]]
    for method in (PMC.METHOD_ID, PMC.ABLATION_ID, PMC.BASELINE_ID):
        m = bench["metrics"][method]
        assert m["recall_at_10"]["numerator"] == sum(len(set(c[method]) & set(c["relevant"])) for c in pos)
        assert m["recall_at_10"]["denominator"] == sum(len(c["relevant"]) for c in pos)
        assert m["precision_at_10"]["denominator"] == sum(len(c[method]) for c in pos)
        assert m["abstained"]["denominator"] == len(valid) == 57
        assert m["false_exact_matches"]["denominator"] == 6
        assert m["cost"] == {"classification": "LOCAL_CPU_ONLY", "provider_calls": 0, "network_calls": 0, "spend_usd": "0"}
    # observed once with the a-priori parameters; pinned so drift is visible, never tuned to improve
    observed = {k: {n: v["value"] for n, v in bench["metrics"][k].items() if n != "cost"} for k in bench["metrics"]}
    assert observed == EXPECTED_METRICS
    # labels changed after the freeze are refused outright
    cases = build_cases(world["receipt_id"])
    cases["cases"][0]["expected_market_ids"] = [mid("gdp")]
    code, _, r = run_cli(tmp_path, world, cases, name="refreeze")
    assert code == 1 and r is None and last(capsys)["reason_code"] == "BENCHMARK_FREEZE_MISMATCH"
    # fewer than fifty valid cases: no metrics, never a partial score
    code, _, r = run_cli(tmp_path, world, build_cases(world["receipt_id"], cases=CASES[:20]), name="small")
    assert code == 0 and r["core"]["benchmark"]["status"] == "BENCHMARK_REFUSED" and r["core"]["benchmark"]["metrics"] is None


# Observed on the frozen synthetic cases with the a-priori parameters (no tuning). Not a lift claim:
# field-aware search is more precise here but recalls fewer labelled markets than the merged baseline.
EXPECTED_METRICS = {
    "field_aware_search_v1": {"abstained": "0.245614", "false_exact_matches": "0.000000", "false_relatedness_items": "0.697531",
                              "false_top1_matches": "0.000000", "negative_queries_with_results": "0.142857",
                              "positive_queries_with_zero_hits": "0.160000", "precision_at_10": "0.322368",
                              "recall_at_10": "0.844828"},
    "field_aware_text_only_v1": {"abstained": "0.245614", "false_exact_matches": "0.000000",
                                 "false_relatedness_items": "0.721591", "false_top1_matches": "0.023810",
                                 "negative_queries_with_results": "0.142857", "positive_queries_with_zero_hits": "0.160000",
                                 "precision_at_10": "0.295181", "recall_at_10": "0.844828"},
    "pa_event_market_bm25_v1": {"abstained": "0.210526", "false_exact_matches": "0.000000", "false_relatedness_items": "0.747573",
                                "false_top1_matches": "0.045455", "negative_queries_with_results": "0.142857",
                                "positive_queries_with_zero_hits": "0.120000", "precision_at_10": "0.265306",
                                "recall_at_10": "0.896552"},
}


# ------------------------------------------------------------------ R007


def _edit_receipt(scratch, change):
    path = scratch / "receipt.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    change(data["core"])
    data["receipt_id"] = PMC.finalize(data["core"])["receipt_id"]
    path.write_text(json.dumps(data), encoding="utf-8")


def test_ext_cli_cold_replay_write_once_tamper_security_and_no_network(baseline, world, tmp_path, capsys, monkeypatch):
    scratch, receipt = baseline
    before = tree(scratch)
    assert CLI.main(["verify", "--scratch-dir", str(scratch)]) == 0
    out = capsys.readouterr().out
    assert json.loads(out)["status"] == "VERIFIED" and str(tmp_path) not in out and "\\" not in out
    assert tree(scratch) == before  # verify writes nothing
    # content-addressed and deterministic across scratch directories
    code, other, again = run_cli(tmp_path, world, build_cases(world["receipt_id"]), name="second")
    assert code == 0 and again["receipt_id"] == receipt["receipt_id"]
    assert set(receipt["core"]["inputs"]["file_sha256"]) >= {"cases.json", "grounding/receipt.json", "grounding/inputs/pit.sqlite3"}
    assert receipt["core"]["code_identity"] == CLI.code_identity()
    # idempotent repeat on identical bytes; different bytes refuse; nothing is overwritten
    cases_path = tmp_path / "second-cases.json"
    capsys.readouterr()
    assert CLI.main(["run", "--grounding-scratch", str(world["grounding"]), "--cases", str(cases_path),
                     "--scratch-dir", str(other)]) == 0 and last(capsys)["status"] == "IDEMPOTENT_VERIFIED"
    cases_path.write_text(json.dumps(build_cases(world["receipt_id"], cases=CASES[:55])), encoding="utf-8")
    snap = tree(other)
    assert CLI.main(["run", "--grounding-scratch", str(world["grounding"]), "--cases", str(cases_path),
                     "--scratch-dir", str(other)]) == 1 and last(capsys)["reason_code"] == "SCRATCH_NOT_EMPTY"
    assert tree(other) == snap
    # output tamper (even with a recomputed id) and frozen-input tamper are detected
    _edit_receipt(other, lambda core: core["benchmark"].update(lift_claim="LIFT"))
    assert CLI.main(["verify", "--scratch-dir", str(other)]) == 1
    assert last(capsys)["failures"] == ["OUTPUT_MISMATCH:benchmark"]
    frozen = other / "inputs" / "cases.json"
    frozen.write_bytes(frozen.read_bytes().replace(b'"r01"', b'"r99"', 1))
    assert CLI.main(["verify", "--scratch-dir", str(other)]) == 1
    assert last(capsys)["failures"] == ["RECOMPUTE_REFUSED:BENCHMARK_FREEZE_MISMATCH"]
    # path, size and content guards (stable codes, no echo)
    good = build_cases(world["receipt_id"])
    good_path = tmp_path / "good.json"
    good_path.write_text(json.dumps(good), encoding="utf-8")

    def stopped(argv):
        assert CLI.main(argv) == 1
        return last(capsys)["reason_code"]
    run = ["run", "--grounding-scratch", str(world["grounding"]), "--cases"]
    assert stopped(run + [str(good_path), "--scratch-dir", str(REPO_ROOT / "ext01-forbidden")]) == "SCRATCH_INSIDE_REPOSITORY"
    assert not (REPO_ROOT / "ext01-forbidden").exists()
    assert stopped(run + ["good.json", "--scratch-dir", str(tmp_path / "rel")]) == "CASES_UNREADABLE"
    assert stopped(run + [str(tmp_path / "x" / ".." / "good.json"), "--scratch-dir", str(tmp_path / "dots")]) == "CASES_UNREADABLE"
    os.link(good_path, tmp_path / "hard.json")
    assert stopped(run + [str(tmp_path / "hard.json"), "--scratch-dir", str(tmp_path / "hl")]) == "CASES_UNREADABLE"
    try:
        os.symlink(tmp_path / "second-cases.json", tmp_path / "sym.json")
    except OSError:
        pass  # symlink privilege missing on this host (Windows WinError 1314); hosted Linux exercises it
    else:
        assert stopped(run + [str(tmp_path / "sym.json"), "--scratch-dir", str(tmp_path / "sl")]) == "CASES_UNREADABLE"
    big = tmp_path / "big.json"
    big.write_bytes(b" " * (CLI.MAX_CASES_BYTES + 1))
    assert stopped(run + [str(big), "--scratch-dir", str(tmp_path / "big")]) == "CASES_UNREADABLE"
    for name, raw, code_ in (
            ("secret", json.dumps(dict(good, schema_id="sk-" + "a" * 24)), "SECRET_MATERIAL_REJECTED"),
            ("auth", json.dumps(dict(good, Authorization="x")), "FORBIDDEN_FIELD"),
            ("dupkey", '{"a": 1, "a": 2}', "CASES_JSON_INVALID"),
            ("nan", '{"a": NaN}', "CASES_JSON_INVALID"),
            ("utf", b"\xff\xfe".decode("latin-1"), "CASES_JSON_INVALID")):
        path = tmp_path / f"{name}.json"
        path.write_text(raw, encoding="utf-8")
        assert stopped(run + [str(path), "--scratch-dir", str(tmp_path / name)]) == code_
    # a socket attempt anywhere in the run fails closed and writes no receipt
    real = PMC.field_aware_search
    monkeypatch.setattr(PMC, "field_aware_search", lambda *a: socket.create_connection(("192.0.2.1", 80)) or real(*a))
    net_cases = tmp_path / "net.json"
    net_cases.write_text(json.dumps(good), encoding="utf-8")
    assert stopped(run + [str(net_cases), "--scratch-dir", str(tmp_path / "net")]) == "NETWORK_ATTEMPT_BLOCKED"
    assert not (tmp_path / "net" / "receipt.json").exists()


# ------------------------------------------------------------------ R008


def test_ext_no_unapproved_authority_or_parity_owner_auto_acceptance(baseline, world):
    _, receipt = baseline
    core = receipt["core"]
    assert core["adoption"] == {"R3-23": "PARTIAL_OFFLINE_PARITY_OWNER_ACCEPTANCE_PENDING",
                                "R3-27": "PARTIAL_OFFLINE_PARITY_OWNER_ACCEPTANCE_PENDING",
                                "R3-24": "OPEN_SEPARATE", "other_parity_ids": "OPEN_UNCHANGED_10",
                                "provider_lanes": "SIX_SEPARATE_OWNER_GATES_UNCHANGED", "lane_b": "SEPARATE_OWNER_UNCHANGED",
                                "real_hermes_and_outcome_backlog": "OPEN_UNCHANGED", "capability_register_total": 36,
                                "new_value_acceptances": 0}
    assert core["safe_output"] == list(PMC.SAFE_OUTPUT) and "OWNER_ACCEPTANCE_PENDING" in core["safe_output"]
    assert {k for k, v in core["authority"].items() if v not in (False, 0)} == {"research_only", "advisory_only",
                                                                                 "human_review_required"}
    # legacy SRC-01 identity untouched: its receipt still verifies under the merged verifier's own code identity
    grounding = json.loads((world["grounding"] / "receipt.json").read_text(encoding="utf-8"))
    assert grounding["core"]["code_identity"] == SGCLI.code_identity()
    # imports: stdlib + native research modules only; no socket/http/SDK/ccxt/Hermes/execution
    allowed = {"__future__", "collections", "json", "math", "re", "argparse", "hashlib", "pathlib", "shutil", "sys", "time",
               "src.data_layer.analytical_research", "src.data_layer.point_in_time_market_research", "tools.alpha"}
    for path in (Path(PMC.__file__), Path(CLI.__file__)):
        source = path.read_text(encoding="utf-8")
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                names = [node.module] if isinstance(node, ast.ImportFrom) else [a.name for a in node.names]
                assert all(n in allowed for n in names), (path.name, names)
        lowered = source.casefold()
        assert "subprocess" not in lowered and "urllib" not in lowered and "requests" not in lowered
        assert "hermes" not in path.name and "mnemonic" not in lowered
    doc = (REPO_ROOT / "docs" / "public_market_contract_parity.md").read_text(encoding="utf-8")
    for phrase in ("OWNER_ACCEPTANCE_PENDING", "R3-24", "ts/src/prediction/polymarket.ts", "ORIENTATION_UNPROVEN",
                   "TAG_OR_PROFILE_UNSUPPORTED", "NOT_RUN", "36"):
        assert phrase in doc
    log = (REPO_ROOT / "docs" / "deferred_items_log.md").read_text(encoding="utf-8")
    assert "S10-R3-EXT-CONTRACTS-01-D001" in log and "R3-24" in log.split("S10-R3-EXT-CONTRACTS-01 deferred items")[-1]
