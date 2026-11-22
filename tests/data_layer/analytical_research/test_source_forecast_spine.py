"""S10-CAP-B1-SOURCE-FORECAST-01 R001/R002/R004/R005/R008: native source/PIT -> A1 -> A2 -> forecast binding.

One SANITIZED_SYNTHETIC frozen world built only with the existing native test helpers: a real PIT store,
a seeded native Alpha registry (one source, one candidate, one family), the real SRC-01 CLI scratch, real
pinned Metaculus leaves, the real pinned official SDK on MockTransport and the real forecast_evaluation
CLI. Nothing here proves forecast skill, real retrieval lift or semantic truth.
"""
from __future__ import annotations

import base64
import copy
import json
from pathlib import Path
import shutil

import pytest

from src.data_layer.analytical_research import alpha_factory_registry as AFR
from src.data_layer.analytical_research import forecast_evaluation as FE
from src.data_layer.analytical_research import metaculus_source_archive_bridge as MSA
from src.data_layer.analytical_research import official_sdk_search_bridge as OSB
from src.data_layer.analytical_research import public_market_contract_parity as PMC
from src.data_layer.analytical_research import source_forecast_spine as SP
from src.data_layer.analytical_research import source_grounding as SG
from tests.data_layer.analytical_research.test_alpha_discovery import _alpha_registry, _pit_built, _pit_store
from tests.tools.alpha.test_forecast_evaluation import HISTORY_SPECS, _history
from tests.tools.alpha.test_source_grounding import _policy_mapping, _sha, _source
from tools.alpha import run_forecast_evaluation as FCLI
from tools.alpha import run_source_grounding as SGCLI

AS_OF = "2026-06-01T12:00:00Z"
OBSERVED, INGESTED = "2026-06-01T00:00:01Z", "2026-06-01T00:00:02Z"
DECISION = "2026-06-02T00:00:00Z"
TARGET = "560001"
# (decimal id, event slug, category, question, resolution date, rule text or None, condition override)
MARKETS = (
    ("560001", "us-cpi-aug-2026", "economics", "Will US CPI inflation exceed 3% year over year in August 2026?", "2026-09-15",
     "Resolves per the Bureau of Labor Statistics CPI-U all items index, twelve month percent change, not seasonally "
     "adjusted, for August 2026, as first published.", None),
    ("560002", "fed-sep-2026", "economics", "Will the Federal Reserve cut interest rates at the September 2026 FOMC meeting?",
     "2026-09-17", "Resolves YES if the FOMC statement lowers the target range for the federal funds rate. Otherwise NO.", None),
    ("560003", "starship-orbit-2026", "science", "Will SpaceX Starship complete a full orbital flight in 2026?", "2026-12-31",
     "Resolves YES if SpaceX Starship completes at least one full orbit during 2026.", None),
    ("560004", "us-gdp-q3-2026", "economics", "Will US real GDP growth for Q3 2026 be negative?", "2026-10-29", None, None),
    ("560005", "legacy-noncanonical", "economics", "Will the legacy record keep a noncanonical condition id?", "2026-12-31",
     "Resolves YES on the stated legacy rule.", "condition:legacy"),
)
PRO = "the consumer price index moved toward the YES outcome"
CON = "the consumer price index stalled and points toward NO"
FAKE = "the index tripled overnight and settled the question"


def _mid(dec):
    return f"market:polymarket:{dec}"


def _cond(dec):
    return "0x" + _sha(("b1a-" + dec).encode())


def _tokens(dec):
    base = 10 ** 20 + 2 * int(dec)
    return f"token:polymarket:{base}", f"token:polymarket:{base + 1}"


def _brief(line):
    filler = "This synthetic briefing paragraph exists only so the archived page passes the length gate. " * 3
    return f"<html><body><h1>Synthetic briefing for cpi</h1><p>Observers say {line}.</p><p>{filler}</p></body></html>".encode()


def _pit_records(markets=MARKETS):
    records = []
    times = dict(observed_time=OBSERVED, ingestion_time=INGESTED)
    for dec, event, category, question, date, rule, cond in markets:
        payload = {"market_status": "open", "outcome_labels": ["No", "Yes"], "question_text": question,
                   "token_ids": list(_tokens(dec)), "condition_id": cond or _cond(dec), "category": category,
                   "resolution_date": date + "T00:00:00Z"}
        meta, _ = _pit_built("PIT-C01-VALID-MARKET-METADATA", platform_id="platform:polymarket",
                             event_id=f"event:polymarket:synthetic-{event}", market_id=_mid(dec),
                             source_id="source:polymarket:gamma-markets", source_assertion_id=f"assertion:b1a:meta:{dec}",
                             snapshot_id=f"snapshot:b1a:meta:{dec}", source_snapshot_id=f"source-snapshot:b1a:meta:{dec}",
                             event_time="2026-06-01T00:00:00Z", canonical_payload=payload, **times)
        records.append(meta)
        if rule:
            source, _ = _pit_built("PIT-C04-VALID-SOURCE-SNAPSHOT", source_id=f"source:b1a:rules:{dec}",
                                   snapshot_id=f"snapshot:b1a:rulesrc:{dec}", **times)
            built, _ = _pit_built("PIT-C05-VALID-RESOLUTION-RULE-SNAPSHOT", platform_id="platform:polymarket",
                                  event_id=f"event:polymarket:synthetic-{event}", market_id=_mid(dec),
                                  resolution_source_id="resolution-source:polymarket:primary",
                                  source_snapshot_id=source.envelope.source_snapshot_id,
                                  rule_content_sha256=_sha(rule.encode()), snapshot_id=f"snapshot:b1a:rule:{dec}",
                                  observed_time="2026-06-01T00:00:03Z", ingestion_time="2026-06-01T00:00:04Z")
            records.extend((source, built))
    return records


def gamma_body(decs, **override):
    markets = []
    for dec in decs:
        no, yes = (t.rsplit(":", 1)[1] for t in _tokens(dec))
        row = {"id": dec, "conditionId": _cond(dec), "question": next(m[3] for m in MARKETS if m[0] == dec),
               "outcomes": json.dumps(["Yes", "No"]), "clobTokenIds": json.dumps([yes, no]), "active": True, "closed": False}
        row.update(override)
        markets.append(row)
    # one SDK event per native event (several native events in one SDK event is an EVENT_RELATION_CONFLICT)
    return json.dumps({"events": [{"id": str(870001 + i), "title": "synthetic", "markets": [m]}
                                  for i, m in enumerate(markets)]}).encode()


def sdk_page(query_id="sdk-cpi", q="consumer price index August", body=None, status=200):
    return {"query_id": query_id, "request": {"q": q, "page_size": 10},
            "response": {"status": status, "content_type": "application/json",
                         "body_b64": base64.b64encode(gamma_body([TARGET, "560002"]) if body is None else body).decode()}}


def build_world(base: Path, *, markets=MARKETS, sources=None, registry_markets=(TARGET,), label="b1a-grounding"):
    """Real SRC-01 scratch over a native PIT store + seeded native Alpha registry; returns ids for the spine case."""
    base.mkdir(parents=True, exist_ok=True)
    pit = _pit_store(base, _pit_records(markets))
    alpha = _alpha_registry(base, [(m, None) for m in registry_markets])

    def put(name, data):
        path = (base / name).resolve()
        path.write_bytes(data)
        return path
    rules = [{"market_id": _mid(m[0]), "file": str(put(f"rule-{m[0]}.txt", m[5].encode()))} for m in markets if m[5]]
    if sources is None:
        sources = [_source(f"cpi-{kind}", TARGET, put(f"cpi-{kind}.html", _brief(line)), _brief(line))
                   for kind, line in (("pro", PRO), ("con", CON))]
        late = _brief("a late revision arrived after the cutoff")
        sources.append(_source("cpi-late", TARGET, put("cpi-late.html", late), late,
                               local_first_seen_time="2026-06-01T13:00:00Z", ingestion_time="2026-06-01T13:00:01Z"))
    src_case = {"schema_id": SG.CASE_SCHEMA, "case_label": label, "corpus_class": "SANITIZED_SYNTHETIC",
                "pit_store": str(pit), "alpha_registry": str(alpha), "policy": _policy_mapping(), "as_of": AS_OF,
                "rule_texts": rules, "sources": sources,
                "queries": [{"query_id": "q-cpi", "text": "Bureau of Labor Statistics consumer price index August",
                             "category_hint": "economics", "relevant_market_ids": [_mid(TARGET)]}]}
    case_path = base / "src-case.json"
    case_path.write_text(json.dumps(src_case), encoding="utf-8")
    scratch = (base / "grounding").resolve()
    assert SGCLI.main(["run", "--case", str(case_path), "--scratch-dir", str(scratch)]) == 0
    records = {type(e.record).__name__: e.record_id for e in AFR.load_and_verify_alpha_factory_registry(alpha).snapshot.entries}
    receipt = json.loads((scratch / "receipt.json").read_text(encoding="utf-8"))
    return {"base": base, "grounding": scratch, "registry": alpha, "receipt": receipt, "pit": pit,
            "family": records.get("HypothesisFamily"), "source": records.get("ResearchSourceReference")}


def claims(cid, prop, stance, label, excerpt):
    return json.dumps({"claims": [{"claim_id": cid, "proposition_id": prop, "stance": stance, "text": "Synthetic research claim.",
                                   "citations": [{"source_label": label, "excerpt": excerpt}]}]})


def spine_case(world, *, forecaster=None, falsifier=None, pages=None, **override):
    def script(content):
        return {"mode": "reply", "content": content, "prompt_tokens": 64, "completion_tokens": 64, "seconds": 0}
    value = {"schema_id": SP.CASE_SCHEMA, "target_market_id": _mid(TARGET),
             "research_question": "Does the admitted public briefing support the CPI market outcome?",
             "hypothesis_family_id": world["family"], "source_reference_ids": [world["source"]],
             "evidence_lanes": ["FUNDAMENTAL"],
             "scripted_children": {"FORECASTER": script(forecaster or claims("f1", "p1", "FOR", "cpi-pro", PRO)),
                                   "FALSIFIER": script(falsifier or claims("x1", "p2", "AGAINST", "cpi-con", CON))},
             "sdk_pages": [sdk_page()] if pages is None else pages}
    value.update(override)
    return value


def forecast_cases(world, **target_override):
    question = next(m[3] for m in MARKETS if m[0] == TARGET)
    rule = next(m[5] for m in MARKETS if m[0] == TARGET)
    target = {"case_id": "t-cpi", "market_id": _mid(TARGET), "question_sha256": _sha(question.encode()),
              "rule_content_sha256": _sha(rule.encode()), "yes_label": "Yes", "decision_time": DECISION,
              "market_price": "0.33", "price_observed_time": "2026-06-01T23:59:00Z",
              "outcome": {"label": "No", "resolved_time": "2026-09-16T00:00:00Z", "known_time": "2026-09-17T00:00:00Z",
                          "provenance": "SANITIZED_SYNTHETIC_LABEL"}}
    target.update(target_override)
    return {"schema_id": FE.CASES_SCHEMA, "case_label": "b1a-forecast", "corpus_class": "SANITIZED_SYNTHETIC",
            "grounding_receipt_id": world["receipt"]["receipt_id"], "wp170": None,
            "method": {"prior_alpha": "1", "prior_beta": "1", "min_training_n": 3, "wang_min_training_n": 20,
                       "horizon_edges_days": [30, 90, 365], "price_edges": ["0.2", "0.4", "0.6", "0.8"],
                       "max_price_age_seconds": 3600},
            "sampler": {"seed": "b1a-seed", "sample_n": 1}, "scoring_cutoff": "2027-12-31T00:00:00Z",
            "history": [_history(s) for s in HISTORY_SPECS[:60]], "targets": [target]}


@pytest.fixture(scope="module")
def world(tmp_path_factory):
    return build_world(tmp_path_factory.mktemp("b1a_world"))


@pytest.fixture(scope="module")
def grounding(world):
    return SP.load_grounding(world["grounding"])


# ------------------------------------------------------------------ R001


def test_a1_native_pit_scout_keeps_exact_market_identity(world, grounding, monkeypatch, tmp_path):
    calls = []
    real_verify, real_corpus, real_native = SGCLI.verify, SG.load_corpus, PMC.normalize_native
    monkeypatch.setattr(SGCLI, "verify", lambda d: calls.append("SRC01.verify") or real_verify(d))
    monkeypatch.setattr(SG, "load_corpus", lambda *a: calls.append("load_corpus") or real_corpus(*a))
    monkeypatch.setattr(PMC, "normalize_native", lambda *a: calls.append("normalize_native") or real_native(*a))
    g = SP.load_grounding(world["grounding"])
    result = SP.scout(g, _mid(TARGET))
    assert calls == ["SRC01.verify", "load_corpus", "load_corpus", "normalize_native"]  # verify recomputes natively, then A1
    assert result["status"] == "ADMITTED" and result["reason"] is None
    t = result["target"]
    native = {m.market_id: m for m in g["universe"].markets}[_mid(TARGET)]
    # exact native identities preserved, never minted
    assert t["market_id"] == native.market_id and t["event_id"] == native.event_id == "event:polymarket:synthetic-us-cpi-aug-2026"
    assert t["condition_id"] == native.condition_id == _cond(TARGET)
    assert t["token_ids"] == list(native.token_ids) and set(t["token_ids"]) == set(_tokens(TARGET))
    assert t["rule_sha256"] == native.rules[0].rule_content_sha256 == _sha(MARKETS[0][5].encode())
    assert t["question_sha256"] == _sha(MARKETS[0][3].encode()) and t["catalog"] == "CATALOG_ROUNDTRIP_OK"
    joined = world["receipt"]["core"]["alpha_join"]["joined"]
    assert t["candidate_id"] == joined[0]["candidate_id"] and joined[0]["market_ids"] == [_mid(TARGET)]
    assert result["alpha_universe_snapshot_id"] == world["receipt"]["core"]["inputs"]["alpha_universe_snapshot_id"]
    d = result["denominators"]
    assert d["examined"] == 5 and d["identity_valid"] == 4 and d["identity_abstained"] == 1
    assert d["identity_defects"] == {"CONDITION_ID_INVALID": 1} and d["rule_text_bound"] == 4
    assert d["catalog"] == {"records": 5, "unique_markets": 5, "duplicate_market_records": 0, "roundtrip_conflicts": 0}
    assert (d["admitted"], d["refused"], d["ambiguous"], d["discovered_new_markets"]) == (1, 0, 0, 0)
    # each non-target refuses with its own closed reason; denominators unchanged
    for market_id, reason in ((_mid("560004"), "TARGET_RULE_NOT_BOUND"), (_mid("560005"), "TARGET_IDENTITY_ABSTAINED"),
                              (_mid("560002"), "TARGET_CANDIDATE_MISSING"), (_mid("999999"), "TARGET_NOT_IN_UNIVERSE")):
        refused = SP.scout(g, market_id)
        assert (refused["status"], refused["reason"], refused["target"]) == ("REFUSED", reason, None)
        assert refused["denominators"]["examined"] == 5 and refused["denominators"]["refused"] == 1
    # empty universe: honest zero denominators, refusal, nothing invented
    empty = build_world(tmp_path / "empty", markets=(), sources=[], registry_markets=())
    blank = SP.scout(SP.load_grounding(empty["grounding"]), _mid(TARGET))
    assert blank["reason"] == "TARGET_NOT_IN_UNIVERSE" and blank["denominators"]["examined"] == 0


# ------------------------------------------------------------------ R002


def test_a2_cold_source_grounding_and_upstream_leaves_consumed(world, grounding, monkeypatch):
    scouted = SP.scout(grounding, _mid(TARGET))
    calls = {"assess_sources": 0, "invoke_search": 0, "sdk_identity": 0}
    real_assess, real_invoke, real_identity = MSA.assess_sources, OSB.invoke_search, OSB.sdk_identity

    def assess(*a):
        calls["assess_sources"] += 1
        return real_assess(*a)

    def invoke(*a):
        calls["invoke_search"] += 1
        return real_invoke(*a)
    monkeypatch.setattr(MSA, "assess_sources", assess)
    monkeypatch.setattr(OSB, "invoke_search", invoke)
    monkeypatch.setattr(OSB, "sdk_identity", lambda: calls.__setitem__("sdk_identity", 1) or real_identity())
    with SGCLI.no_network() as attempts:
        result = SP.research(grounding, scouted, [sdk_page()])
    assert attempts == [] and calls == {"assess_sources": 1, "invoke_search": 1, "sdk_identity": 1}
    assert result["status"] == "ADMITTED" and result["source_allowlist"] == ["cpi-pro", "cpi-con"]
    entries = world["receipt"]["core"]["sources"]["entries"]
    accepted = [e["raw_evidence_reference_id"] for e in entries if e["status"] == "ACCEPTED"]
    assert result["raw_evidence_reference_ids"] == accepted and len(accepted) == 2
    late = next(e for e in entries if e["source_label"] == "cpi-late")
    assert late["status"] != "ACCEPTED" and result["denominators"]["target_sources_refused"] == {late["reason"]: 1}
    assert result["denominators"]["target_sources_total"] == 3 and result["denominators"]["allowlisted"] == 2
    # seen / known / ingestion clocks preserved from the native raw evidence references
    for ref in accepted:
        pit = result["reference_clocks"][ref]
        assert pit["ingestion_time"] == "2026-05-31T00:00:01Z" and pit["local_first_seen_time"] == "2026-05-31T00:00:00Z"
    # upstream Metaculus leaves actually evaluated each admitted target source
    rows = {r["source_label"]: r for r in result["metaculus"]["target_rows"]}
    assert rows["cpi-pro"]["verdict"] == rows["cpi-con"]["verdict"] == "UPSTREAM_EVALUATED"
    assert rows["cpi-late"]["verdict"] == "ABSTAINED" and result["metaculus"]["invocations"]["quality.evaluate"] == 2
    # SDK on MockTransport: one request to fixture.invalid only, target identity consistent with native
    sdk = result["sdk"]
    assert sdk["mock_transport_requests"] == 1 and sdk["real_network_requests"] == 0
    assert sdk["rows"][0]["status"] == "SDK_TYPED_PAGE" and sdk["rows"][0]["target_sdk_status"] == ["IDENTITY_CONSISTENT"]
    # the upstream result is consumed downstream: an upstream quality failure removes a label from the allowlist
    real_rows = real_assess(grounding["frozen"], grounding["core"], grounding["read"])

    def failing(*a):
        out = copy.deepcopy(real_rows)
        for row in out["rows"]:
            if row["source_label"] == "cpi-con":
                row["upstream_passed"] = False
        return out
    monkeypatch.setattr(MSA, "assess_sources", failing)
    narrowed = SP.research(grounding, scouted, [sdk_page()])
    assert narrowed["source_allowlist"] == ["cpi-pro"] and narrowed["upstream_excluded"] == {"cpi-con": "UPSTREAM_QUALITY_NOT_PASSED"}
    # SDK identity conflict on the target refuses A2
    monkeypatch.setattr(MSA, "assess_sources", real_assess)
    conflict = SP.research(grounding, scouted, [sdk_page(body=gamma_body([TARGET], conditionId="0x" + "f" * 64))])
    assert (conflict["status"], conflict["reason"]) == ("REFUSED", "SDK_TARGET_IDENTITY_CONFLICT")


# ------------------------------------------------------------------ R004


def test_forecast_diagnostic_consumer_bound_to_frozen_scope(world, grounding, tmp_path, monkeypatch):
    scouted = SP.scout(grounding, _mid(TARGET))
    researched = SP.research(grounding, scouted, [sdk_page()])
    cases_path = tmp_path / "fc.json"
    cases_path.write_text(json.dumps(forecast_cases(world)), encoding="utf-8")
    scratch = (tmp_path / "fc").resolve()
    calls = []
    real_run, real_verify = FCLI.run, FCLI.verify
    monkeypatch.setattr(FCLI, "run", lambda *a: calls.append("run") or real_run(*a))
    monkeypatch.setattr(FCLI, "verify", lambda *a: calls.append("verify") or real_verify(*a))
    assert FCLI.run(world["grounding"], cases_path, scratch)["status"] == "RUN_COMPLETE"
    assert FCLI.verify(scratch)["status"] == "VERIFIED" and calls == ["run", "verify"]
    receipt = json.loads((scratch / "receipt.json").read_text(encoding="utf-8"))
    bound = SP.bind_forecast(receipt, scouted, researched)
    assert bound["receipt_id"] == receipt["receipt_id"] and bound["receipt_id"].startswith(FE.RECEIPT_PREFIX)
    assert bound["score_status"] == receipt["core"]["score_status"] == "DIAGNOSTIC_ONLY"
    assert bound["decision_time"] == DECISION and bound["is_a3_child_forecast"] is False and bound["method_parity"] == "B1_B_PENDING"
    assert receipt["core"]["history"]["provenance"] == "CALLER_ASSERTED_CLOCKS_NOT_SRC01_GROUNDED"
    # never recomputes or fabricates a score: the bound fields are exactly the receipt's
    row = next(r for r in receipt["core"]["targets"] if r["case_id"] == "t-cpi")
    assert row["grounded_source_reference_ids"] == sorted(researched["raw_evidence_reference_ids"])
    # wrong rule, wrong question, wrong grounding refuse binding
    for override, code in (({"rule_content_sha256": "0" * 64}, "FORECAST_TARGET_NOT_SELECTED"),
                           ({"question_sha256": "1" * 64}, "FORECAST_TARGET_NOT_SELECTED")):
        p = tmp_path / f"fc-{code}-{len(override)}-{list(override)[0]}.json"
        p.write_text(json.dumps(forecast_cases(world, **override)), encoding="utf-8")
        s = (tmp_path / ("fc-" + list(override)[0])).resolve()
        assert real_run(world["grounding"], p, s)["status"] == "RUN_COMPLETE"
        with pytest.raises(SP.SpineStop, match=code):
            SP.bind_forecast(json.loads((s / "receipt.json").read_text(encoding="utf-8")), scouted, researched)
    foreign = copy.deepcopy(receipt)
    foreign["core"]["source_grounding"]["receipt_id"] = SG.RECEIPT_PREFIX + "0" * 64
    with pytest.raises(SP.SpineStop, match="FORECAST_GROUNDING_MISMATCH"):
        SP.bind_forecast(foreign, scouted, researched)


# ------------------------------------------------------------------ R005


def test_b1_negative_identity_time_and_source_matrix(world, grounding, tmp_path):
    scouted = SP.scout(grounding, _mid(TARGET))
    # unknown / cross-venue / noncanonical market id: closed refusal before any lookup
    for bad in ("market:kalshi:560001", "market:polymarket:cpi", 560001):
        with pytest.raises(SP.SpineStop, match="TARGET_MARKET_ID_NONCANONICAL|SPINE_CASE_FIELDS_INVALID"):
            SP.validate_case(spine_case(world, target_market_id=bad))
    assert SP.scout(grounding, _mid("870001"))["reason"] == "TARGET_NOT_IN_UNIVERSE"
    # mismatched rule hash -> rule not bound -> refused
    frozen = json.loads((world["grounding"] / "frozen_case.json").read_text(encoding="utf-8"))
    rule_rel = next(e["file"] for e in frozen["rule_texts"] if e["market_id"] == _mid(TARGET))
    bad = SP.load_grounding(world["grounding"])
    real_read = bad["read"]
    bad["rules"] = SG.bind_rule_texts(bad["universe"], frozen["rule_texts"],
                                      lambda rel: real_read(rel) + b" altered" if rel == rule_rel else real_read(rel))[0]
    assert SP.scout(bad, _mid(TARGET))["reason"] == "TARGET_RULE_NOT_BOUND"
    # duplicate / ambiguous canonical identity: two candidates for the target, and a duplicate condition id
    amb = build_world(tmp_path / "amb", registry_markets=(TARGET,))
    reg = SP.load_grounding(amb["grounding"])
    reg["core"] = copy.deepcopy(reg["core"])
    reg["core"]["alpha_join"]["joined"].append({"candidate_id": "candidate:sha256:" + "a" * 64, "market_ids": [_mid(TARGET)]})
    ambiguous = SP.scout(reg, _mid(TARGET))
    assert ambiguous["reason"] == "TARGET_CANDIDATE_AMBIGUOUS" and ambiguous["denominators"]["ambiguous"] == 1
    dup = tuple(m if m[0] != "560002" else (*m[:6], _cond(TARGET)) for m in MARKETS)
    d = build_world(tmp_path / "dup", markets=dup)
    dup_scout = SP.scout(SP.load_grounding(d["grounding"]), _mid(TARGET))
    assert dup_scout["reason"] == "TARGET_IDENTITY_ABSTAINED"
    assert dup_scout["denominators"]["identity_defects"]["DUPLICATE_CONDITION"] == 2
    # absent source bytes / late capture / unsupported duplicate label: no admitted pre-cutoff source -> A2 refuses
    def put(base, name, data):
        path = (base / name).resolve()
        path.write_bytes(data)
        return path
    nb = tmp_path / "nosrc"
    nb.mkdir()
    srcs = [_source("cpi-missing", TARGET, nb / "absent.html", b"x"),
            _source("cpi-late", TARGET, put(nb, "late.html", _brief(PRO)), _brief(PRO),
                    local_first_seen_time="2026-06-01T13:00:00Z", ingestion_time="2026-06-01T13:00:01Z"),
            _source("cpi-rev", TARGET, put(nb, "rev.html", _brief(CON)), _brief(CON), revision_time="2026-06-02T00:00:00Z"),
            _source("cpi-unauth", TARGET, put(nb, "unauth.html", _brief(PRO)), _brief(PRO), http_status=401)]
    nw = build_world(tmp_path / "nosrcw", sources=srcs)
    ng = SP.load_grounding(nw["grounding"])
    refused = SP.research(ng, SP.scout(ng, _mid(TARGET)), [sdk_page()])
    assert (refused["status"], refused["reason"]) == ("REFUSED", "NO_ADMITTED_PRE_CUTOFF_SOURCE")
    assert refused["denominators"]["target_sources_total"] == 4 and refused["denominators"]["target_sources_accepted"] == 0
    assert sum(refused["denominators"]["target_sources_refused"].values()) == 4
    # missing / conflicting candidate or family lineage refuses before any dispatch
    case = spine_case(world)
    SP.check_lineage(world["registry"], case, scouted["target"]["candidate_id"])
    for broken, code in ((dict(case, hypothesis_family_id=world["source"]), "FAMILY_NOT_IN_LINEAGE"),
                         (dict(case, source_reference_ids=[world["family"]]), "SOURCE_REFERENCE_NOT_IN_LINEAGE")):
        with pytest.raises(SP.SpineStop, match=code):
            SP.check_lineage(world["registry"], broken, scouted["target"]["candidate_id"])
    with pytest.raises(SP.SpineStop, match="CANDIDATE_NOT_IN_LINEAGE"):
        SP.check_lineage(world["registry"], case, "candidate:sha256:" + "b" * 64)
    # an A1 or A2 refusal never yields a W01 handoff
    with pytest.raises(SP.SpineStop, match="A1_A2_NOT_ADMITTED"):
        SP.w01_case(case, scouted, refused)


# ------------------------------------------------------------------ R008


def test_b1_upstream_vs_native_measurement_no_false_lift(world, grounding):
    scouted = SP.scout(grounding, _mid(TARGET))
    # same held fixture, same query: SDK page lists the target second, native ranker ranks it first -> NO_LIFT
    pages = [sdk_page("sdk-cpi", body=gamma_body(["560002", TARGET])), sdk_page("sdk-empty", body=gamma_body([]))]
    result = SP.research(grounding, scouted, pages)
    rows = {r["query_id"]: r for r in result["sdk"]["rows"]}
    assert rows["sdk-cpi"]["target_rank"] == {"native": 1, "sdk": 2} and rows["sdk-cpi"]["lift"] == "NO_LIFT"
    assert rows["sdk-empty"]["target_rank"]["sdk"] is None and rows["sdk-empty"]["lift"] == "NO_LIFT"
    assert result["native_vs_upstream"] == "NO_LIFT"
    # imported upstream calls have an actual downstream read: Metaculus verdicts shape the W01 allowlist
    handoff = SP.w01_case(spine_case(world), scouted, result)
    assert handoff["question"]["source_allowlist"] == result["source_allowlist"]
    assert result["metaculus"]["counts"]["promoted_by_upstream"] == 0
    # citations/coverage counted, model usage UNKNOWN, never invented costs or economic edge
    assert result["denominators"]["allowlisted"] == 2 and result["denominators"]["target_sources_total"] == 3
    assert SP.AUTHORITY["model_spend"].startswith("UNKNOWN") and SP.AUTHORITY["provider_calls"] == 0
    assert all("edge" not in k and "pnl" not in k for k in json.dumps(result).lower().split('"'))
    # a malformed SDK page is a counted per-page status, not a dropped row
    broken = SP.research(grounding, scouted, [dict(sdk_page(), response=dict(sdk_page()["response"], body_b64="%%%"))])
    assert broken["sdk"]["rows"][0]["status"] == "PAGE_BODY_INVALID"
