"""S10-R3-SDK-DIRECT-01 offline tests: verified SRC-01 scratch -> merged EXT comparators -> the REAL
installed polymarket-client 0.10.0 PublicClient.search(...).first_page() over httpx.MockTransport ->
typed SDK results crossed with native identities -> receipt -> cold verify.

The labelled cases are exactly the frozen S10-R3-EXT-CONTRACTS-01 cases (imported, not copied). The
SDK pages are SANITIZED_SYNTHETIC Gamma-shaped fixtures written by a label-blind generator: every
corpus market whose question shares at least one query term, in corpus order, capped at the page
size. They stand in for a server response so the real SDK has bytes to parse; they are not a ranker
under test and say nothing about real Gamma search quality.
"""
from __future__ import annotations

import ast
import base64
import dataclasses
import hashlib
import json
import os
from pathlib import Path
import socket
import sys

import pytest

from polymarket._internal import dispatch as sdk_dispatch
from polymarket.clients.public import PublicClient
from polymarket.models.gamma.search import SearchResults
from polymarket.pagination import Page

from src.data_layer.analytical_research import official_sdk_search_bridge as OSB
from src.data_layer.analytical_research import public_market_contract_parity as PMC
from src.data_layer.analytical_research import source_grounding as SG
from tests.tools.alpha.test_public_market_contract_parity import (
    ALL, AS_OF, CASES, EXPECTED_METRICS, OBSERVED, SLUGS, build_cases, cond, dec, last, make_world, mid, tokens, tree)
from tools.alpha import run_official_sdk_search as CLI
from tools.alpha import run_public_market_contract_parity as PMCCLI
from tools.alpha import run_source_grounding as SGCLI

REPO_ROOT = Path(__file__).resolve().parents[3]
QUESTIONS = {m[0]: m[3] for m in ALL}
EVENTS = {m[0]: m[1] for m in ALL}
EVENT_ORDER = list(dict.fromkeys(m[1] for m in ALL))


def gamma_market(slug, labels=None, toks=None, **extra):
    no, yes = tokens(slug)
    labels = labels or (["A", "B", "C"] if slug == "tri" else ["Yes", "No"])
    toks = toks or ([yes, no, str(int(yes) + 9 * 10**19)] if slug == "tri" else [yes, no])
    return {"id": dec(slug), "conditionId": cond(slug), "question": QUESTIONS[slug], "outcomes": json.dumps(labels),
            "clobTokenIds": json.dumps(toks), "active": True, "closed": False, **extra}


def gamma_body(slugs, foreign=False, tags=False, pagination=None):
    events = {}
    for slug in slugs:
        events.setdefault(EVENTS[slug], []).append(gamma_market(slug))
    body = {"events": [{"id": str(800000 + EVENT_ORDER.index(e)), "title": e, "markets": ms} for e, ms in events.items()]}
    if foreign:
        body["events"].append({"id": "899999", "markets": [{"id": "990001", "conditionId": "0x" + "e" * 64,
                                                             "outcomes": '["Yes","No"]', "clobTokenIds": '["11","12"]'}]})
    if tags:
        body["tags"] = [{"id": "1", "label": "synthetic", "slug": "synthetic"}]
    if pagination is not None:
        body["pagination"] = pagination
    return json.dumps(body).encode()


def label_blind_hits(q, size=10):
    terms = set(SG.tokenize(q))
    return [s for s in SLUGS if terms & set(SG.tokenize(QUESTIONS[s]))][:size]


def entry(case_id, query, body, status=200, ct="application/json", captured=OBSERVED, **request):
    req = {"q": query.get("q"), "page_size": 10, **{k: query[k] for k in ("events_status", "events_tag") if query.get(k)}}
    req.update(request)
    return {"case_id": case_id, "captured_at": captured, "request": req,
            "response": {"status": status, "content_type": ct, "body_b64": base64.b64encode(body).decode()}}


def benchmark_pages():
    out = []
    for i, case in enumerate(CASES):
        q = case["query"].get("q")
        if q:
            out.append(entry(case["case_id"], case["query"], gamma_body(label_blind_hits(q), foreign=i % 7 == 3,
                                                                        tags=i % 5 == 1)))
    return out


def build_pages(ext_cases, pages=None, **overrides):
    value = {"schema_id": OSB.PAGES_SCHEMA, "corpus_class": ext_cases["corpus_class"],
             "ext_benchmark_sha256": ext_cases["benchmark_sha256"], "source_label": OSB.SOURCE_LABEL,
             "sdk": {"distribution": "polymarket-client", "version": "0.10.0"},
             "pages": benchmark_pages() if pages is None else pages}
    value.update(overrides)
    return value


def run_cli(tmp_path, world, ext_cases, pages, name="sdk", grounding=None):
    cases_path, pages_path = tmp_path / f"{name}-cases.json", tmp_path / f"{name}-pages.json"
    cases_path.write_text(json.dumps(ext_cases), encoding="utf-8")
    pages_path.write_text(json.dumps(pages), encoding="utf-8")
    scratch = (tmp_path / name).resolve()
    code = CLI.main(["run", "--grounding-scratch", str(grounding or world["grounding"]), "--ext-cases", str(cases_path),
                     "--sdk-pages", str(pages_path), "--scratch-dir", str(scratch)])
    receipt = scratch / "receipt.json"
    return code, scratch, json.loads(receipt.read_text(encoding="utf-8")) if receipt.exists() else None


SDK = None  # one real SDK client shared by the direct calls (its constructor builds five TLS httpx clients)


@pytest.fixture(scope="module", autouse=True)
def sdk_client():
    global SDK
    with PublicClient() as SDK:
        yield SDK


@pytest.fixture(scope="module")
def world(tmp_path_factory):
    return make_world(tmp_path_factory.mktemp("sdk01_inputs"))


@pytest.fixture(scope="module")
def baseline(world, tmp_path_factory):
    ext_cases = build_cases(world["receipt_id"])
    code, scratch, receipt = run_cli(tmp_path_factory.mktemp("sdk01_run"), world, ext_cases, build_pages(ext_cases))
    assert code == 0, receipt
    return scratch, receipt


def native_rows(scratch, world):
    core = PMCCLI._core(scratch, {"status": "VERIFIED", "receipt_id": world["receipt_id"]})
    return {m["market_id"]: m for m in core["corpus"]["markets"]}


def pages_by_case(receipt):
    return {p["case_id"]: p for p in receipt["core"]["pages"] if p["status"] != "DUPLICATE_PAGE"}


def typed(body, **request):
    return OSB.invoke_search({"q": "nba finals", "page_size": 10, **request}, body, 200, "application/json", SDK)


# ------------------------------------------------------------------ R001


def test_sdk_sdk_real_import_and_search(baseline, world, tmp_path, monkeypatch, capsys):
    _, receipt = baseline
    sdk = receipt["core"]["sdk"]
    assert sdk["distribution"] == "polymarket-client" and sdk["version"] == "0.10.0"
    assert sdk["commit"] == "579bb2e56be9cc5d152546985870ee6ad795ec52" and sdk["tag"] == "polymarket-client-v0.10.0"
    assert sdk["files"]["clients/public.py"] == "abe091d10ba65132e0674605c6a48023b0317bff"
    assert sdk["files"]["clients/_transport.py"] == "4c049727d7f2f3c7ab656872c4a54863ac240d4c"
    assert sdk["upstream_seam_test"] == {"tests/unit/test_paginate_transport.py": "f2a608f025c2eb74c4d1d49365541c86ab188d81"}
    assert sdk["installed_blobs_match_tag"] is True and sdk["method"] == "polymarket.clients.public.PublicClient.search"
    # the real SDK code objects run: search -> page-based paginator -> SDK-owned SearchResults parser
    entered = set()
    targets = {PublicClient.search.__code__, sdk_dispatch.sync_paginate_page_based.__code__,
               SearchResults.parse_page_response.__func__.__code__}

    def profile(frame, event, _arg):
        if event == "call" and frame.f_code in targets:
            entered.add(frame.f_code)
    sys.setprofile(profile)
    try:
        call = typed(gamma_body(["nba-celtics", "nba-thunder"]))
    finally:
        sys.setprofile(None)
    assert entered == targets
    assert call["status"] == "SDK_TYPED_PAGE" and type(call["page"]) is Page
    assert len(call["page"].items) == 1 and type(call["page"].items[0]) is SearchResults
    assert [m.id for m in call["page"].items[0].events[0].markets] == [dec("nba-celtics"), dec("nba-thunder")]
    assert call["requests"] == [{"method": "GET", "scheme": "https", "host": "fixture.invalid", "path": "/public-search",
                                 "params": [["limit_per_type", "10"], ["page", "1"], ["q", "nba finals"]]}]
    # every invoked page in the receipt went through exactly one SDK request to the fixture host
    invoked = [p for p in receipt["core"]["pages"] if p["sdk_invoked"]]
    assert invoked and all(len(p["requests"]) == 1 and p["requests"][0]["host"] == "fixture.invalid" for p in invoked)
    # a fake replacing the SDK method is refused before anything runs; a hand-made page never reaches the transport
    ext_cases = build_cases(world["receipt_id"])

    def fake_search(self, **kwargs):
        return type("P", (), {"first_page": lambda _s: Page(items=(SearchResults(),), has_more=False)})()
    monkeypatch.setattr(PublicClient, "search", fake_search)
    with pytest.raises(SG.GroundingStop, match="SDK_METHOD_NOT_UPSTREAM"):
        OSB.sdk_identity()
    assert typed(gamma_body(["cpi"]))["status"] == "MOCK_TRANSPORT_NOT_REACHED"
    code, _, r = run_cli(tmp_path, world, ext_cases, build_pages(ext_cases), name="fake")
    assert code == 1 and r is None and last(capsys) == {"status": "STOPPED", "reason_code": "SDK_METHOD_NOT_UPSTREAM"}
    monkeypatch.undo()
    # wrong installed version or source bytes stop before any input is read
    monkeypatch.setattr(OSB, "metadata", type("M", (), {"version": staticmethod(lambda _d: "0.9.0"),
                                                       "PackageNotFoundError": LookupError}))
    code, _, r = run_cli(tmp_path, world, ext_cases, build_pages(ext_cases), name="ver")
    assert code == 1 and r is None and last(capsys)["reason_code"] == "SDK_VERSION_MISMATCH"
    monkeypatch.undo()
    monkeypatch.setitem(OSB.SDK_FILES, "clients/public.py", "0" * 40)
    with pytest.raises(SG.GroundingStop, match="SDK_SOURCE_MISMATCH"):
        OSB.sdk_identity()
    # a typed-looking object that is not the SDK's own type is refused
    fake_page = Page(items=({"events": []},), has_more=False)
    assert OSB.project_typed_page(fake_page, {}, {})["status"] == "SDK_TYPED_RESULT_INVALID"
    assert OSB.project_typed_page(object(), {}, {})["status"] == "SDK_TYPED_RESULT_INVALID"


# ------------------------------------------------------------------ R002


def test_sdk_sdk_offline_transport_and_page_contract(baseline, monkeypatch):
    _, receipt = baseline
    # SDK-supported filters are passed through and appear in the single request it builds
    call = typed(gamma_body(["cpi"], tags=True), events_tag="economics", search_tags=True)
    assert call["status"] == "SDK_TYPED_PAGE"
    assert call["requests"][0]["params"] == [["events_tag", "economics"], ["limit_per_type", "10"], ["page", "1"],
                                             ["q", "nba finals"], ["search_tags", "true"]]
    projected = OSB.project_typed_page(call["page"], None, {})
    assert projected["tags_unsupported"] == 1 and projected["market_status_counts"] == {"NOT_IN_UNIVERSE": 1}
    # continuation: the SDK yields a cursor, the bridge refuses it and no second request is ever made
    more = typed(gamma_body(["cpi"], pagination={"hasMore": True, "totalResults": 40}))
    assert more["status"] == "SDK_TYPED_PAGE" and len(more["requests"]) == 1 and more["page"].next_cursor is not None
    assert OSB.project_typed_page(more["page"], None, {})["status"] == "PAGE_CONTINUATION_REFUSED"
    # redirect and server errors are SDK-rejected after one request; nothing is followed
    for status, code in ((302, "SDK_REDIRECT_REFUSED"), (307, "SDK_REDIRECT_REFUSED"), (500, "SDK_REQUEST_REJECTED"),
                         (429, "SDK_RATE_LIMITED")):
        result = OSB.invoke_search({"q": "x"}, b"{}", status, "application/json", SDK)
        assert result["status"] == code and len(result["requests"]) == 1 and result["page"] is None
    # a second request (implicit paging or retry) is never answered with data
    def double(self):
        self._fetch(None)
        return self._fetch(None)
    monkeypatch.setattr("polymarket.pagination.Paginator.first_page", double)
    assert OSB.invoke_search({"q": "x"}, gamma_body(["cpi"]), 200, "application/json", SDK)["status"] == "SECOND_REQUEST_REFUSED"
    monkeypatch.undo()
    # without a caller client the bridge builds and closes its own; the shared client's default gamma is restored
    assert OSB.invoke_search({"q": "x"}, gamma_body(["cpi"]), 200, "application/json")["status"] == "SDK_TYPED_PAGE"
    assert SDK._ctx.gamma._base_url != OSB.FIXTURE_BASE
    # bytes, request parameters and status are hash-bound per page; unsupported SDK keywords are refused
    pages = pages_by_case(receipt)
    p = pages["r02"]
    body = base64.b64decode(benchmark_pages()[1]["response"]["body_b64"])
    assert p["body_sha256"] == hashlib.sha256(body).hexdigest() and p["response_status"] == 200
    assert p["requests"][0]["params"] == [["limit_per_type", "10"], ["page", "1"], ["q", "LaGuardia Airport station temperature reading"]]
    assert set(receipt["core"]["inputs"]["file_sha256"]) >= {"cases.json", "sdk_pages.json", "grounding/receipt.json"}
    sorted_req = OSB._page_precheck(entry("r02", {"q": "x"}, b"{}", sort="volume"), {"r02": {"q": "x"}}, set(), AS_OF)
    assert sorted_req == ("REQUEST_PARAMETER_UNSUPPORTED", None)
    tags = receipt["core"]["comparison"]["source_coverage"]
    assert tags["tags_unsupported"] > 0 and tags["profiles_unsupported"] == 0
    assert "TAGS_AND_PROFILES_NOT_PROJECTED" in receipt["core"]["upstream_gaps"]


# ------------------------------------------------------------------ R003


def test_sdk_sdk_native_pit_verified_crossing(baseline, world, tmp_path, monkeypatch):
    verified = []
    real_verify = SGCLI.verify
    monkeypatch.setattr(SGCLI, "verify", lambda p: verified.append(Path(p)) or real_verify(p))
    ext_cases = build_cases(world["receipt_id"])
    code, scratch, receipt = run_cli(tmp_path, world, ext_cases, build_pages(ext_cases))
    assert code == 0
    monkeypatch.undo()
    core = receipt["core"]
    # caller SRC-01 bytes verified first, then the frozen copy, by the unchanged native verifier
    assert verified[0] == world["grounding"] and set(verified[1:]) == {scratch / "inputs" / "grounding"}
    from src.data_layer.analytical_research import alpha_discovery as AD
    from tests.tools.alpha.test_source_grounding import _policy_mapping
    native = AD.build_alpha_universe_snapshot(world["pit"], AD.build_alpha_discovery_policy(_policy_mapping()).record, AS_OF).record
    assert core["inputs"]["alpha_universe_snapshot_id"] == native.alpha_universe_snapshot_id
    assert core["inputs"]["grounding_receipt_id"] == world["receipt_id"] and core["inputs"]["as_of"] == AS_OF
    assert core["native_corpus"]["markets_total"] == len(native.markets) == len(ALL)
    rows = native_rows(scratch, world)
    no, yes = tokens("cpi")

    def cross(body):
        call = typed(body)
        return OSB.project_typed_page(call["page"], json.loads(body), rows)

    ok = cross(gamma_body(["cpi"]))
    m = ok["events"][0]["markets"][0]
    assert m["status"] == "IDENTITY_CONSISTENT" and m["native_market_id"] == mid("cpi") and ok["ranked"] == [mid("cpi")]
    assert m["event_identity"] == "EVENT_ID_UNVERIFIED"  # a Gamma event id never silently equals a native event
    assert m["orientation"] == "ORIENTATION_UNPROVEN" and m["tradable_side"] is None and m["sdk_yes_slot_label"] == "Yes"
    # SDK v0.10.0 names outcomes[0] ".yes" positionally: a No-first market lands "No" in the yes slot
    flipped = cross(json.dumps({"events": [{"id": "1", "markets": [gamma_market("cpi", labels=["No", "Yes"], toks=[no, yes])]}]}).encode())
    assert flipped["events"][0]["markets"][0]["sdk_yes_slot_label"] == "No"
    assert flipped["events"][0]["markets"][0]["status"] == "IDENTITY_CONSISTENT"  # identity holds, orientation stays unproven
    statuses = {
        "CONDITION_ID_CONFLICT": gamma_market("cpi", conditionId=cond("gdp")),
        "NOT_IN_UNIVERSE": gamma_market("cpi", id="999999999"),
        "NATIVE_IDENTITY_ABSTAINED": gamma_market("collide-a"),
        "OUTCOME_TOKEN_CONFLICT": gamma_market("cpi", toks=[yes, "123"]),
        "MARKET_ID_NONCANONICAL": gamma_market("cpi", id="legacy-slug"),
    }
    for expected, market in statuses.items():
        got = cross(json.dumps({"events": [{"id": "1", "markets": [market]}]}).encode())
        assert got["events"][0]["markets"][0]["status"] == expected and got["ranked"] == [], expected
    # one SDK event spanning two native events, and one market under two SDK events, are both conflicts
    ambiguous = cross(json.dumps({"events": [{"id": "1", "markets": [gamma_market("cpi"), gamma_market("gdp")]}]}).encode())
    assert ambiguous["market_status_counts"] == {"EVENT_RELATION_CONFLICT": 2} and ambiguous["ranked"] == []
    twice = cross(json.dumps({"events": [{"id": "1", "markets": [gamma_market("cpi")]},
                                         {"id": "2", "markets": [gamma_market("cpi")]}]}).encode())
    assert twice["market_status_counts"] == {"EVENT_RELATION_CONFLICT": 1, "IDENTITY_CONSISTENT": 1}
    dup = cross(json.dumps({"events": [{"id": "1", "markets": [gamma_market("cpi"), gamma_market("cpi")]}]}).encode())
    assert dup["market_status_counts"] == {"DUPLICATE_MARKET": 1, "IDENTITY_CONSISTENT": 1} and dup["ranked"] == [mid("cpi")]
    # noncanonical: research staging only, nothing written back, caller scratch still verifies
    assert core["authority"]["canonical_writes"] is False and core["authority"]["alpha_promotion"] is False
    assert core["native_corpus"]["orientation_proven"] == 0 and core["source_authenticity"] == "SOURCE_ORIGIN_UNVERIFIED"
    assert all(m["orientation"] == "ORIENTATION_UNPROVEN" for p in core["pages"] if p["projection"]
               for e in p["projection"]["events"] for m in e["markets"])
    assert SGCLI.verify(world["grounding"])["status"] == "VERIFIED"


# ------------------------------------------------------------------ R004


def test_sdk_sdk_vs_existing_native_methods(baseline, world, tmp_path):
    _, receipt = baseline
    comparison = receipt["core"]["comparison"]
    assert comparison["status"] == "COMPLETED" and comparison["lift_claim"] is None
    assert comparison["metric_semantics"].startswith("SDK_ROWS_ARE_CALLER_SUPPLIED_FIXTURE_PAGES")
    methods = {OSB.METHOD_ID, PMC.METHOD_ID, PMC.BASELINE_ID}
    assert set(comparison["metrics_all_ext_valid_cases"]) == set(comparison["metrics_sdk_paired_cases"]) == methods
    d = comparison["denominators"]
    for m in methods:  # identical cases for every method in each scope
        assert comparison["metrics_all_ext_valid_cases"][m]["abstained"]["denominator"] == d["ext_cases_valid"]
        assert comparison["metrics_sdk_paired_cases"][m]["abstained"]["denominator"] == d["cases_paired"]
    # the EXT comparators are the merged ones, unchanged: same rankings and the same pinned EXT metrics
    for m in (PMC.METHOD_ID, PMC.BASELINE_ID):
        observed = {k: v["value"] for k, v in comparison["metrics_all_ext_valid_cases"][m].items() if k != "cost"}
        assert observed == {k: v for k, v in EXPECTED_METRICS[m].items() if k in observed}
    code, _, ext = run_ext_cli(tmp_path, world)
    assert code == 0
    assert receipt["core"]["ext_benchmark_reference"]["metrics"] == ext["core"]["benchmark"]["metrics"]
    assert receipt["core"]["inputs"]["ext_core_receipt_id"] == ext["receipt_id"]
    ext_rows = {r["case_id"]: r for r in ext["core"]["benchmark"]["cases"] if r["status"] == "VALID"}
    for row in comparison["cases"]:
        assert row[PMC.METHOD_ID] == ext_rows[row["case_id"]][PMC.METHOD_ID]
        assert row[PMC.BASELINE_ID] == ext_rows[row["case_id"]][PMC.BASELINE_ID]
    # coverage of the supplied pages is reported apart from ranking quality
    cov = comparison["source_coverage"]
    assert set(cov) >= {"sdk_market_rows", "identity_consistent_rate", "labels_present_in_page", "sdk_dropped_markets"}
    assert cov["sdk_market_status_counts"]["NOT_IN_UNIVERSE"] > 0 and cov["sdk_dropped_markets"] > 0


def run_ext_cli(tmp_path, world):
    path = tmp_path / "ext-cases.json"
    path.write_text(json.dumps(build_cases(world["receipt_id"])), encoding="utf-8")
    scratch = (tmp_path / "ext").resolve()
    code = PMCCLI.main(["run", "--grounding-scratch", str(world["grounding"]), "--cases", str(path), "--scratch-dir", str(scratch)])
    return code, scratch, json.loads((scratch / "receipt.json").read_text(encoding="utf-8"))


# ------------------------------------------------------------------ R005


def test_sdk_sdk_fail_closed_adversarial(world, tmp_path, capsys):
    ext_cases = build_cases(world["receipt_id"])
    q = {c["case_id"]: c["query"] for c in reversed(CASES)}
    good = gamma_body(["cpi"])
    late = "2026-06-02T00:00:00Z"
    bad = [
        entry("r03", q["r03"], b"<html>not json"),
        entry("r04", q["r04"], b'{"events": [], "t": "\xff"}'),
        entry("r05", q["r05"], b'{"events": [], "x": NaN}'),
        entry("r06", q["r06"], b'{"events": [], "events": []}'),
        entry("r07", q["r07"], b'{"events": {}}'),
        entry("r08", q["r08"], b'{"events": [], "pagination": {"hasMore": "yes"}}'),
        entry("p01", q["p01"], gamma_body(["cpi"], pagination={"hasMore": True})),
        entry("p02", q["p02"], b" " * (OSB.MAX_PAGE_BYTES + 1)),
        entry("p03", q["p03"], good, captured=late),
        entry("p04", q["p04"], good, captured="2026-06-01 00:00"),
        dict(entry("p05", q["p05"], good), response={"status": 200, "content_type": "application/json", "body_b64": "%%%"}),
        dict(entry("p06", q["p06"], good), extra=1),
        entry("p07", q["p07"], good, sort="volume"),
        entry("p08", q["p08"], good, q="something else"),
        entry("p09", q["p09"], good), entry("p09", q["p09"], good),
        entry("zz9", {"q": "unknown"}, good),
        entry("t01", q["t01"], good),  # EXT abstained the case (post-cutoff): never paired
        entry("p10", q["p10"], json.dumps({"events": [{"id": "1", "markets": [gamma_market("tri"), {"id": "5"}]}]}).encode()),
        entry("p11", q["p11"], b'[]'),
        entry("p12", q["p12"], b"{}", status=302),
        entry("p13", q["p13"], json.dumps({"events": [{"title": "no id"}]}).encode()),
    ]
    code, _, receipt = run_cli(tmp_path, world, ext_cases, build_pages(ext_cases, pages=bad), name="adv")
    assert code == 0
    got = [p["status"] for p in receipt["core"]["pages"]]
    assert got == ["SDK_PARSE_REJECTED", "SDK_PARSE_REJECTED", "STRICT_JSON_REJECTED", "STRICT_JSON_REJECTED",
                   "SDK_PARSE_REJECTED", "SDK_PARSE_REJECTED", "PAGE_CONTINUATION_REFUSED", "PAGE_OVERSIZE",
                   "SOURCE_POST_CUTOFF", "PAGE_FIELDS_INVALID", "PAGE_FIELDS_INVALID", "PAGE_FIELDS_INVALID",
                   "REQUEST_PARAMETER_UNSUPPORTED", "REQUEST_CASE_MISMATCH", "SDK_TYPED_PAGE_PROJECTED", "DUPLICATE_PAGE",
                   "PAGE_CASE_NOT_PAIRED", "PAGE_CASE_NOT_PAIRED", "SDK_TYPED_PAGE_PROJECTED", "SDK_PARSE_REJECTED",
                   "SDK_REDIRECT_REFUSED", "SDK_PARSE_REJECTED"]
    pages = receipt["core"]["pages"]
    # the SDK accepted NaN / duplicate keys; the native strict check refuses them after the real call
    assert pages[2]["sdk_invoked"] and pages[2]["sdk_error"] is None and pages[3]["sdk_invoked"]
    assert pages[0]["sdk_error"] == "UnexpectedResponseError" and pages[20]["sdk_error"] == "RequestRejectedError"
    assert not any(pages[i]["sdk_invoked"] for i in (7, 8, 9, 10, 11, 12, 13, 15, 16, 17))
    # the SDK silently drops the categorical and the malformed market; the drop is counted, never hidden
    assert pages[18]["projection"]["sdk_dropped_markets"] == 2 and pages[18]["projection"]["ranked"] == []
    comparison = receipt["core"]["comparison"]
    assert comparison["status"] == "PAIRED_BENCHMARK_REFUSED" and comparison["metrics_sdk_paired_cases"] is None
    assert comparison["metrics_all_ext_valid_cases"] is None and comparison["lift_claim"] is None
    assert receipt["core"]["source_authenticity"] == "SOURCE_ORIGIN_UNVERIFIED"
    # whole-file defects stop with stable codes and no receipt
    for name, pages_doc, code_ in (
            ("schema", build_pages(ext_cases, schema_id="other"), "PAGES_SCHEMA_INVALID"),
            ("label", build_pages(ext_cases, source_label="GAMMA_LIVE"), "SOURCE_LABEL_INVALID"),
            ("sdkreq", build_pages(ext_cases, sdk={"distribution": "polymarket-client", "version": "0.11.0"}), "SDK_REQUIREMENT_MISMATCH"),
            ("bind", build_pages(ext_cases, ext_benchmark_sha256="0" * 64), "BENCHMARK_BINDING_MISMATCH"),
            ("corpus", build_pages(ext_cases, corpus_class="LOCAL_REAL_PIT"), "CORPUS_CLASS_MISMATCH"),
            ("empty", build_pages(ext_cases, pages=[]), "PAGES_LIST_INVALID"),
            ("unknown", dict(build_pages(ext_cases), extra=True), "PAGES_FIELDS_INVALID")):
        code, _, r = run_cli(tmp_path, world, ext_cases, pages_doc, name=f"neg-{name}")
        assert code == 1 and r is None and last(capsys)["reason_code"] == code_, name


# ------------------------------------------------------------------ R006


def test_sdk_sdk_benchmark_fixed_denominators(baseline, world, tmp_path):
    _, receipt = baseline
    core = receipt["core"]
    comparison = core["comparison"]
    assert len(CASES) == 60 and core["ext_benchmark_reference"]["denominators"]["cases_valid_paired"] == 57
    assert comparison["denominators"] == EXPECTED_DENOMINATORS
    rows = comparison["cases"]
    paired = [r for r in rows if r["paired"]]
    assert len(paired) >= 50 and core["real_benchmark"] == "NOT_RUN_REAL_DATA" and comparison["real_value"] == "NOT_VERIFIED"
    for scope, subset in (("metrics_all_ext_valid_cases", rows), ("metrics_sdk_paired_cases", paired)):
        pos = [r for r in subset if r["relevant"]]
        for m, metrics in comparison[scope].items():
            assert metrics["recall_at_10"]["numerator"] == sum(len(set(r[m]) & set(r["relevant"])) for r in pos)
            assert metrics["recall_at_10"]["denominator"] == sum(len(r["relevant"]) for r in pos)
            assert metrics["precision_at_10"]["denominator"] == sum(len(r[m]) for r in pos)
            assert metrics["cost"] == {"classification": "LOCAL_CPU_ONLY", "provider_calls": 0, "network_calls": 0,
                                       "spend_usd": "0"}
    observed = {s: {m: {k: v["value"] for k, v in vals.items() if k != "cost"} for m, vals in comparison[s].items()}
                for s in ("metrics_all_ext_valid_cases", "metrics_sdk_paired_cases")}
    assert observed == EXPECTED_SDK_METRICS
    # measured overhead is reported beside the content-addressed core, never inside it
    measured = receipt["measurements"]
    assert measured["reproducible"] is False and measured["sdk_invocations"] == comparison["denominators"]["sdk_invocations"]
    assert measured["sdk_elapsed_ns_total"] > 0 and 0 < measured["peak_traced_bytes"] <= CLI.MAX_PEAK_BYTES
    # too few pages pair: no metrics at all
    ext_cases = build_cases(world["receipt_id"])
    code, _, small = run_cli(tmp_path, world, ext_cases, build_pages(ext_cases, pages=benchmark_pages()[:20]), name="small")
    assert code == 0 and small["core"]["comparison"]["status"] == "PAIRED_BENCHMARK_REFUSED"
    assert small["core"]["comparison"]["metrics_sdk_paired_cases"] is None


# Observed once on the frozen cases and label-blind fixture pages; pinned so drift is visible. The SDK
# rows only re-express what the fixture pages contain: not retrieval quality, not a lift.
EXPECTED_DENOMINATORS = {'cases_not_sdk_searchable': 4,
 'cases_paired': 53,
 'cases_without_usable_page': 4,
 'ext_cases_valid': 57,
 'page_status_counts': {'DUPLICATE_PAGE': 1, 'PAGE_CASE_NOT_PAIRED': 2, 'SDK_TYPED_PAGE_PROJECTED': 53},
 'pages_refused_before_sdk': 3,
 'pages_submitted': 56,
 'paired_negative_no_match': 6,
 'paired_positive_labeled': 47,
 'sdk_invocations': 53,
 'sdk_typed_pages_usable': 53}
EXPECTED_SDK_METRICS = {'metrics_all_ext_valid_cases': {'field_aware_search_v1': {'abstained': '0.245614',
                                                           'false_relatedness_items': '0.697531',
                                                           'negative_queries_with_results': '0.142857',
                                                           'positive_queries_with_zero_hits': '0.160000',
                                                           'precision_at_10': '0.322368',
                                                           'recall_at_10': '0.844828'},
                                 'official_sdk_public_search_fixture_page_v0_10_0': {'abstained': '0.122807',
                                                                                     'false_relatedness_items': '0.738372',
                                                                                     'negative_queries_with_results': '0.428571',
                                                                                     'positive_queries_with_zero_hits': '0.180000',
                                                                                     'precision_at_10': '0.283019',
                                                                                     'recall_at_10': '0.775862'},
                                 'pa_event_market_bm25_v1': {'abstained': '0.210526',
                                                             'false_relatedness_items': '0.747573',
                                                             'negative_queries_with_results': '0.142857',
                                                             'positive_queries_with_zero_hits': '0.120000',
                                                             'precision_at_10': '0.265306',
                                                             'recall_at_10': '0.896552'}},
 'metrics_sdk_paired_cases': {'field_aware_search_v1': {'abstained': '0.207547',
                                                        'false_relatedness_items': '0.701863',
                                                        'negative_queries_with_results': '0.166667',
                                                        'positive_queries_with_zero_hits': '0.127660',
                                                        'precision_at_10': '0.317881',
                                                        'recall_at_10': '0.872727'},
                              'official_sdk_public_search_fixture_page_v0_10_0': {'abstained': '0.056604',
                                                                                  'false_relatedness_items': '0.738372',
                                                                                  'negative_queries_with_results': '0.500000',
                                                                                  'positive_queries_with_zero_hits': '0.127660',
                                                                                  'precision_at_10': '0.283019',
                                                                                  'recall_at_10': '0.818182'},
                              'pa_event_market_bm25_v1': {'abstained': '0.150943',
                                                          'false_relatedness_items': '0.747573',
                                                          'negative_queries_with_results': '0.166667',
                                                          'positive_queries_with_zero_hits': '0.063830',
                                                          'precision_at_10': '0.265306',
                                                          'recall_at_10': '0.945455'}}}


# ------------------------------------------------------------------ R007


def _edit_receipt(scratch, change, measurements=None):
    path = scratch / "receipt.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    change(data["core"])
    data["receipt_id"] = OSB.finalize(data["core"], {})["receipt_id"]
    if measurements:
        data["measurements"].update(measurements)
    path.write_text(json.dumps(data), encoding="utf-8")


def test_sdk_sdk_cold_receipt_security(baseline, world, tmp_path, capsys, monkeypatch):
    scratch, receipt = baseline
    before = tree(scratch)
    calls = []
    real_invoke = OSB.invoke_search
    monkeypatch.setattr(OSB, "invoke_search", lambda *a: calls.append(1) or real_invoke(*a))
    assert CLI.main(["verify", "--scratch-dir", str(scratch)]) == 0
    monkeypatch.undo()
    out = capsys.readouterr().out
    assert json.loads(out)["status"] == "VERIFIED" and str(tmp_path) not in out and "\\" not in out
    assert len(calls) == receipt["measurements"]["sdk_invocations"] > 0  # cold verify re-runs the real SDK on frozen bytes
    assert tree(scratch) == before  # verify writes nothing
    ext_cases = build_cases(world["receipt_id"])
    code, other, again = run_cli(tmp_path, world, ext_cases, build_pages(ext_cases), name="second")
    assert code == 0 and again["receipt_id"] == receipt["receipt_id"] and again["core"] == receipt["core"]
    assert receipt["core"]["code_identity"] == CLI.code_identity()
    assert receipt["core"]["inputs"]["ext_code_identity"] == PMCCLI.code_identity()
    # idempotent repeat; different bytes refuse; nothing overwritten
    capsys.readouterr()
    argv = ["run", "--grounding-scratch", str(world["grounding"]), "--ext-cases", str(tmp_path / "second-cases.json"),
            "--sdk-pages", str(tmp_path / "second-pages.json"), "--scratch-dir", str(other)]
    assert CLI.main(argv) == 0 and last(capsys)["status"] == "IDEMPOTENT_VERIFIED"
    (tmp_path / "second-pages.json").write_text(json.dumps(build_pages(ext_cases, pages=benchmark_pages()[:51])), encoding="utf-8")
    snap = tree(other)
    assert CLI.main(argv) == 1 and last(capsys)["reason_code"] == "SCRATCH_NOT_EMPTY" and tree(other) == snap
    # output, measurement and frozen-input tamper are all detected
    _edit_receipt(other, lambda core: core["comparison"].update(lift_claim="LIFT"))
    assert CLI.main(["verify", "--scratch-dir", str(other)]) == 1 and last(capsys)["failures"] == ["OUTPUT_MISMATCH:comparison"]
    _edit_receipt(other, lambda core: core["comparison"].update(lift_claim=None), {"reproducible": True})
    assert CLI.main(["verify", "--scratch-dir", str(other)]) == 1 and last(capsys)["failures"] == ["MEASUREMENTS_INVALID"]
    frozen = other / "inputs" / "sdk_pages.json"
    doc = json.loads(frozen.read_text(encoding="utf-8"))
    doc["pages"][0]["response"]["body_b64"] = base64.b64encode(gamma_body(["gdp"])).decode()
    frozen.write_text(json.dumps(doc), encoding="utf-8")
    assert CLI.main(["verify", "--scratch-dir", str(other)]) == 1
    assert "OUTPUT_MISMATCH:pages" in last(capsys)["failures"]
    # path, size and content guards (stable codes, no echo)
    good_cases = tmp_path / "good-cases.json"
    good_cases.write_text(json.dumps(ext_cases), encoding="utf-8")
    good_pages = tmp_path / "good-pages.json"
    good_pages.write_text(json.dumps(build_pages(ext_cases)), encoding="utf-8")

    def stopped(pages_path, scratch_dir):
        assert CLI.main(["run", "--grounding-scratch", str(world["grounding"]), "--ext-cases", str(good_cases),
                         "--sdk-pages", str(pages_path), "--scratch-dir", str(scratch_dir)]) == 1
        return last(capsys)["reason_code"]
    assert stopped(good_pages, REPO_ROOT / "sdk01-forbidden") == "SCRATCH_INSIDE_REPOSITORY"
    assert not (REPO_ROOT / "sdk01-forbidden").exists()
    assert stopped("good-pages.json", tmp_path / "rel") == "PAGES_UNREADABLE"
    assert stopped(tmp_path / "x" / ".." / "good-pages.json", tmp_path / "dots") == "PAGES_UNREADABLE"
    os.link(good_pages, tmp_path / "hard.json")
    assert stopped(tmp_path / "hard.json", tmp_path / "hl") == "PAGES_UNREADABLE"
    try:
        os.symlink(good_pages, tmp_path / "sym.json")
    except OSError:
        pass  # symlink privilege missing on this host (Windows WinError 1314); hosted Linux exercises it
    else:
        assert stopped(tmp_path / "sym.json", tmp_path / "sl") == "PAGES_UNREADABLE"
    big = tmp_path / "big.json"
    big.write_bytes(b" " * (CLI.MAX_PAGES_BYTES + 1))
    assert stopped(big, tmp_path / "big") == "PAGES_UNREADABLE"
    secret_page = entry("r02", CASES[1]["query"], json.dumps({"events": [], "note": "sk-" + "a" * 24}).encode())
    wallet_page = entry("r02", CASES[1]["query"], json.dumps({"events": [], "profiles": [{"id": "p", "wallet": "0x1"}]}).encode())
    for name, raw, code_ in (
            ("secret", json.dumps(build_pages(ext_cases, pages=[secret_page])), "SECRET_MATERIAL_REJECTED"),
            ("wallet", json.dumps(build_pages(ext_cases, pages=[wallet_page])), "FORBIDDEN_FIELD"),
            ("auth", json.dumps(dict(build_pages(ext_cases), Authorization="x")), "FORBIDDEN_FIELD"),
            ("dupkey", '{"a": 1, "a": 2}', "PAGES_JSON_INVALID"),
            ("nan", '{"a": NaN}', "PAGES_JSON_INVALID")):
        path = tmp_path / f"{name}.json"
        path.write_text(raw, encoding="utf-8")
        assert stopped(path, tmp_path / name) == code_, name
    # a socket attempt anywhere in the run fails closed and writes no receipt
    monkeypatch.setattr(OSB, "invoke_search", lambda *a: socket.create_connection(("192.0.2.1", 80)) or real_invoke(*a))
    net_pages = tmp_path / "net-pages.json"  # good_pages now has a second hard link and is refused by design
    net_pages.write_text(json.dumps(build_pages(ext_cases)), encoding="utf-8")
    assert stopped(net_pages, tmp_path / "net") == "NETWORK_ATTEMPT_BLOCKED"
    assert not (tmp_path / "net" / "receipt.json").exists()
    monkeypatch.undo()
    # legacy identities preserved: SRC-01 receipt still verifies under its own code identity
    grounding = json.loads((world["grounding"] / "receipt.json").read_text(encoding="utf-8"))
    assert grounding["core"]["code_identity"] == SGCLI.code_identity()
    assert SGCLI.verify(world["grounding"])["status"] == "VERIFIED"


# ------------------------------------------------------------------ R008


def test_sdk_sdk_upstream_adoption_and_authority(baseline):
    _, receipt = baseline
    core = receipt["core"]
    adoption = core["adoption"]
    assert adoption["capability_register_total"] == 36 == len(adoption["capabilities"])
    assert adoption["capabilities"]["R3-23"] == "DIRECT_UPSTREAM_INTEGRATION_OFFLINE_PENDING_OWNER_VALUE"
    assert adoption["capabilities"]["R3-27"] == "CUSTOM_ADAPTED_IMPLEMENTATION_OWNER_ACCEPTANCE_PENDING"
    assert {v for k, v in adoption["capabilities"].items() if k not in ("R3-23", "R3-27")} == {"UNCHANGED_TRACKED"}
    assert adoption["owner_value_acceptances"] == 0 and adoption["parity_auto_acceptance"] is False
    assert adoption["ccxt_direct_reuse"] == "NOT_ADOPTED_SEPARATE_DECISION" and adoption["pr268"] == "SEPARATE_UNCONSUMED"
    assert core["safe_output"] == ["OFFLINE_RESEARCH_ONLY", "DIRECT_UPSTREAM_SDK_METHOD_INVOKED_ON_FIXTURE",
                                   "SOURCE_ORIGIN_UNVERIFIED", "REAL_VALUE_NOT_VERIFIED", "NO_PROVIDER_OR_TRADING_AUTHORITY"]
    assert core["sdk"]["adoption_mode"] == "DIRECT_IMPORT_AND_INVOCATION_NO_CODE_COPIED"
    assert core["sdk"]["commit"] != "aa94ec431e3d4946576fb7c0d079fe1c14fcf676"
    auth = core["authority"]
    assert {k for k, v in auth.items() if v not in (False, 0)} == {"research_only", "advisory_only", "human_review_required",
                                                                    "sdk_methods_invoked"}
    assert auth["sdk_methods_invoked"] == ["PublicClient.search"] and auth["real_gamma_requests"] == 0
    # imports: stdlib, httpx, the public SDK search surface and native research modules only
    sdk_allowed = {"polymarket.clients._transport", "polymarket.clients.public", "polymarket.errors",
                   "polymarket.models.gamma.event", "polymarket.models.gamma.market", "polymarket.models.gamma.search",
                   "polymarket.pagination"}
    allowed = sdk_allowed | {"__future__", "base64", "binascii", "collections", "dataclasses", "hashlib", "importlib",
                             "inspect", "json", "pathlib", "re", "httpx", "argparse", "shutil", "sys", "time", "tracemalloc",
                             "src.data_layer.analytical_research", "src.data_layer.point_in_time_market_research", "tools.alpha"}
    for path in (Path(OSB.__file__), Path(CLI.__file__)):
        source = path.read_text(encoding="utf-8")
        tree_ = ast.parse(source)
        for node in ast.walk(tree_):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                names = [node.module] if isinstance(node, ast.ImportFrom) else [a.name for a in node.names]
                assert all(n in allowed for n in names), (path.name, names)
                if isinstance(node, ast.ImportFrom) and node.module.startswith("polymarket"):
                    assert not any("Secure" in a.name or "auth" in a.name.lower() for a in node.names)
        called = {n.func.attr for n in ast.walk(tree_) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                  and isinstance(n.func.value, ast.Name) and n.func.value.id == "client"}
        assert called <= {"search"}, called
        lowered = source.casefold()
        for forbidden in ("subprocess", "urllib", "import requests", "environ", "getenv", "gamma-api.polymarket.com",
                          "secureclient", "py_clob_client"):
            assert forbidden not in lowered, (path.name, forbidden)
    # docs: contract, deferred log and status keep every gate open
    doc = (REPO_ROOT / "docs" / "official_sdk_search_bridge_contract.md").read_text(encoding="utf-8")
    for phrase in ("579bb2e56be9cc5d152546985870ee6ad795ec52", "MockTransport", "LOCAL_FIXTURE_UNAUTHENTICATED",
                   "DIRECT_UPSTREAM_INTEGRATION_OFFLINE_PENDING_OWNER_VALUE", "CUSTOM_ADAPTED_IMPLEMENTATION", "NOT_RUN_REAL_DATA",
                   "ORIENTATION_UNPROVEN", "36", "S10-R3-REAL-PUBLIC-GET-01"):
        assert phrase in doc, phrase
    log = (REPO_ROOT / "docs" / "deferred_items_log.md").read_text(encoding="utf-8")
    section = log.split("S10-R3-SDK-DIRECT-01 deferred items")[-1]
    assert "S10-R3-SDK-DIRECT-01-D001" in section and "R3-27" in section and "PR #268" in section
    assert (REPO_ROOT / "docs" / "status_entries" / "S10-R3-SDK-DIRECT-01.md").is_file()
    with PublicClient() as client:  # the upstream-tested seam the bridge relies on still exists
        assert dataclasses.is_dataclass(client._ctx) and hasattr(client._ctx, "gamma")
