"""Direct official Polymarket SDK public search on an offline injected transport (S10-R3-SDK-DIRECT-01).

This module imports the installed upstream ``polymarket-client==0.10.0`` (Polymarket/py-sdk tag
``polymarket-client-v0.10.0``, commit 579bb2e56be9cc5d152546985870ee6ad795ec52) and calls its real
``PublicClient.search(q=..., page_size=...).first_page()``. The only seam is the one the upstream
test ``tests/unit/test_paginate_transport.py`` uses: a ``SyncTransport`` over
``httpx.Client(transport=httpx.MockTransport(handler))`` placed into ``client._ctx.gamma`` with
``dataclasses.replace``. The handler answers exactly one GET with one caller-supplied frozen page;
the SDK owns request building, JSON decoding, status handling, pagination and typed parsing. No SDK
code is copied and no search algorithm is reimplemented here.

Typed SDK results are crossed with the native identity rows that
``public_market_contract_parity.normalize_native`` builds from a cold-verified S10-R3-SRC-01 scratch.
Pages are ``LOCAL_FIXTURE_UNAUTHENTICATED``: SDK parsing never authenticates their origin, and the
SDK's positional ``outcomes.yes`` slot is never treated as a proven outcome orientation.

Posture: research only, offline, no credentials, no authenticated client, no order, strategy,
paper, capital or live authority. Only ``PublicClient.search`` is invoked.
"""
from __future__ import annotations

import base64
import binascii
from collections import Counter
import dataclasses
import hashlib
from importlib import metadata
import inspect
import json
from pathlib import Path
import re

import httpx
from polymarket.clients._transport import SyncTransport
from polymarket.clients.public import PublicClient
from polymarket.errors import (PolymarketError, RateLimitError, RequestRejectedError, TransportError,
                               UnexpectedResponseError, UserInputError)
from polymarket.models.gamma.event import Event
from polymarket.models.gamma.market import Market
from polymarket.models.gamma.search import SearchResults
from polymarket.pagination import Page

from src.data_layer.analytical_research import public_market_contract_parity as PMC
from src.data_layer.analytical_research import source_grounding as SG
from src.data_layer.point_in_time_market_research import research_provenance as RP

WP_ID = "S10-R3-SDK-DIRECT-01"
PAGES_SCHEMA = "s10-r3-sdk-direct01-pages-v1"
RECEIPT_SCHEMA = "s10-r3-sdk-direct01-receipt-v1"
RECEIPT_PREFIX = "sdksearch:sha256:"
SOURCE_LABEL = "LOCAL_FIXTURE_UNAUTHENTICATED"
METHOD_ID = "official_sdk_public_search_fixture_page_v0_10_0"
CALLER = ("tools/alpha/run_official_sdk_search.py:run -> run_source_grounding.verify -> "
          "run_public_market_contract_parity._core -> official_sdk_search_bridge.invoke_search -> "
          "polymarket.clients.public.PublicClient.search(...).first_page() -> httpx.MockTransport")

SDK_DISTRIBUTION = "polymarket-client"
SDK_VERSION = "0.10.0"
SDK_REPOSITORY = "Polymarket/py-sdk"
SDK_TAG = "polymarket-client-v0.10.0"
SDK_COMMIT = "579bb2e56be9cc5d152546985870ee6ad795ec52"
# Git blob ids at SDK_COMMIT (src/polymarket/<path>); the installed bytes must be identical.
SDK_FILES = {
    "clients/public.py": "abe091d10ba65132e0674605c6a48023b0317bff",
    "clients/_transport.py": "4c049727d7f2f3c7ab656872c4a54863ac240d4c",
    "_internal/dispatch.py": "a28467b4c786fc17f9973e026293972f6905e632",
    "_internal/pagination.py": "b568b36e757ce945ff70b80e054ac23c7338e393",
    "_internal/actions/gamma.py": "53bf8972a0bbfc712ebb5f4e83e92aab141fbfbd",
    "models/gamma/search.py": "1952797ecfa1695bfbf3fb97ba070540affbf15f",
    "models/gamma/event.py": "ae791c3c8d8b0a0a5ab163442ee589accc9246e1",
    "models/gamma/market.py": "83ce8cabd44087e099bda4db06b36b534a591060",
    "pagination.py": "fdb5c49e6037674f18b14e127cc1d0081ec916db",
    "errors.py": "262978d58a59693efae708e8f3cdcfc12e00fed9",
    "version.py": "4c1b50b4491fe60b51469be3a888c89a0d651380",
}
UPSTREAM_SEAM_TEST = {"tests/unit/test_paginate_transport.py": "f2a608f025c2eb74c4d1d49365541c86ab188d81"}
FIXTURE_BASE = "https://fixture.invalid"  # RFC 2606 reserved: never resolvable, answered only by MockTransport
SEARCH_PATH = "/public-search"

SDK_KWARGS = ("q", "page_size", "events_status", "events_tag", "search_tags", "search_profiles")
MAX_PAGES = 500
MAX_PAGE_BYTES = 256 * 1024
TOP_K = SG.TOP_K
PAGES_KEYS = {"schema_id", "corpus_class", "ext_benchmark_sha256", "source_label", "sdk", "pages"}
PAGE_KEYS = {"case_id", "captured_at", "request", "response"}
RESPONSE_KEYS = {"status", "content_type", "body_b64"}
_DECIMAL_RE = re.compile(r"0|[1-9][0-9]{0,39}")

SAFE_OUTPUT = ("OFFLINE_RESEARCH_ONLY", "DIRECT_UPSTREAM_SDK_METHOD_INVOKED_ON_FIXTURE", "SOURCE_ORIGIN_UNVERIFIED",
               "REAL_VALUE_NOT_VERIFIED", "NO_PROVIDER_OR_TRADING_AUTHORITY")
CAPABILITY_IDS = tuple([f"R3-{i:02d}" for i in range(1, 30)] + [
    "R3-01-SOURCE_ARCHIVE", "R3-03-FEES", "R3-05-CITATIONS", "R3-07-ROUTER", "R3-09-BOOK_GAPS", "R3-10-WANG",
    "R3-12-SAMPLER"])
ADOPTION_CHANGES = {"R3-23": "DIRECT_UPSTREAM_INTEGRATION_OFFLINE_PENDING_OWNER_VALUE",
                    "R3-27": "CUSTOM_ADAPTED_IMPLEMENTATION_OWNER_ACCEPTANCE_PENDING"}


def _stop(code: str):
    raise SG.GroundingStop(code)


def _require(condition: bool, code: str) -> None:
    if not condition:
        _stop(code)


def _git_blob(raw: bytes) -> str:
    return hashlib.sha1(b"blob %d\0" % len(raw) + raw, usedforsecurity=False).hexdigest()


# ------------------------------------------------------------------ SDK identity


def sdk_identity() -> dict:
    """Installed distribution, source bytes and the search method must be the pinned upstream ones."""
    try:
        version = metadata.version(SDK_DISTRIBUTION)
    except metadata.PackageNotFoundError:
        _stop("SDK_NOT_INSTALLED")
    _require(version == SDK_VERSION, "SDK_VERSION_MISMATCH")
    root = Path(inspect.getsourcefile(PublicClient)).resolve().parents[1]
    installed = {rel: _git_blob((root / rel).read_bytes()) if (root / rel).is_file() else None for rel in SDK_FILES}
    _require(installed == SDK_FILES, "SDK_SOURCE_MISMATCH")
    method = PublicClient.__dict__.get("search")
    _require(inspect.isfunction(method) and method.__qualname__ == "PublicClient.search"
             and Path(inspect.getsourcefile(method)).resolve() == root / "clients" / "public.py", "SDK_METHOD_NOT_UPSTREAM")
    return {"distribution": SDK_DISTRIBUTION, "version": version, "repository": SDK_REPOSITORY, "tag": SDK_TAG,
            "commit": SDK_COMMIT, "license": "MIT", "installed_blobs_match_tag": True, "files": dict(SDK_FILES),
            "upstream_seam_test": dict(UPSTREAM_SEAM_TEST), "method": "polymarket.clients.public.PublicClient.search",
            "call": "search(q=..., page_size=...).first_page()",
            "seam": "SyncTransport(client=httpx.Client(transport=httpx.MockTransport)) via dataclasses.replace(_ctx, gamma=...)",
            "adoption_mode": "DIRECT_IMPORT_AND_INVOCATION_NO_CODE_COPIED",
            "not_conflated_with": "aa94ec431e3d4946576fb7c0d079fe1c14fcf676 (R3 concept pin, a different revision)"}


# ------------------------------------------------------------------ real SDK invocation


def _sdk_error_code(error: PolymarketError, status: int) -> str:
    if isinstance(error, RateLimitError):
        return "SDK_RATE_LIMITED"
    if isinstance(error, RequestRejectedError):
        return "SDK_REDIRECT_REFUSED" if 300 <= status < 400 else "SDK_REQUEST_REJECTED"
    if isinstance(error, UnexpectedResponseError):
        return "SDK_PARSE_REJECTED"
    if isinstance(error, UserInputError):
        return "SDK_INPUT_REJECTED"
    if isinstance(error, TransportError):
        return "SDK_TRANSPORT_ERROR"
    return "SDK_ERROR"


def invoke_search(request: dict, body: bytes, status: int, content_type: str, client: PublicClient | None = None) -> dict:
    """One real ``PublicClient.search(...).first_page()`` answered by one frozen page; never a second request.

    ``client`` lets one run reuse a single SDK client (its constructor builds five TLS-configured
    httpx clients); only its gamma transport is swapped per page, exactly as the upstream test does."""
    if client is None:
        with PublicClient() as own:
            return invoke_search(request, body, status, content_type, own)
    calls = []

    def handler(req: httpx.Request) -> httpx.Response:
        calls.append({"method": req.method, "scheme": req.url.scheme, "host": req.url.host, "path": req.url.path,
                      "params": sorted([k, v] for k, v in req.url.params.multi_items())})
        if len(calls) > 1:
            return httpx.Response(599)  # no paging, retry or follow-up is ever answered
        return httpx.Response(status, content=body, headers={"content-type": content_type})

    kwargs = {k: request[k] for k in SDK_KWARGS if request.get(k) is not None}
    original = client._ctx
    with httpx.Client(base_url=FIXTURE_BASE, transport=httpx.MockTransport(handler), follow_redirects=False) as http:
        client._ctx = dataclasses.replace(original, gamma=SyncTransport(base_url=FIXTURE_BASE, client=http))
        try:
            page = client.search(**kwargs).first_page()
            outcome = {"status": "SDK_TYPED_PAGE", "sdk_error": None}
        except PolymarketError as error:
            page, outcome = None, {"status": _sdk_error_code(error, status), "sdk_error": type(error).__name__}
        finally:
            client._ctx = original  # the unused default gamma transport is restored so close() releases it
    expected = sorted([k, str(v).lower() if type(v) is bool else str(v)] for k, v in
                      {**{k: v for k, v in kwargs.items() if k != "page_size"}, "page": 1,
                       "limit_per_type": kwargs.get("page_size", 10)}.items())
    if not calls:
        outcome = {"status": "MOCK_TRANSPORT_NOT_REACHED", "sdk_error": None}
    elif len(calls) > 1:
        outcome = {"status": "SECOND_REQUEST_REFUSED", "sdk_error": None}
    elif calls[0] != {"method": "GET", "scheme": "https", "host": "fixture.invalid", "path": SEARCH_PATH, "params": expected}:
        outcome = {"status": "SDK_REQUEST_SHAPE_UNEXPECTED", "sdk_error": None}
    return {**outcome, "requests": calls, "page": page if outcome["status"] == "SDK_TYPED_PAGE" else None}


# ------------------------------------------------------------------ typed projection onto native identities


def _raw_market_counts(raw: object) -> list[int] | None:
    events = raw.get("events") if isinstance(raw, dict) else None
    if not isinstance(events, list):
        return None
    return [len(e["markets"]) if isinstance(e, dict) and isinstance(e.get("markets"), list) else 0 for e in events]


def project_typed_page(page: object, raw: object, native: dict[str, dict]) -> dict:
    """Read only SDK-typed objects; the raw page is used solely to count markets the SDK dropped."""
    out = {"status": None, "events": [], "ranked": [], "tags_unsupported": 0, "profiles_unsupported": 0,
           "sdk_dropped_markets": 0, "market_status_counts": {}}
    items = page.items if type(page) is Page else None
    if not items or len(items) != 1 or type(items[0]) is not SearchResults \
            or any(type(e) is not Event for e in items[0].events) \
            or any(type(m) is not Market for e in items[0].events for m in (e.markets or ())):
        out["status"] = "SDK_TYPED_RESULT_INVALID"
        return out
    if page.has_more or page.next_cursor is not None:
        out["status"] = "PAGE_CONTINUATION_REFUSED"  # one bounded page per case; the cursor is never followed
        return out
    results = items[0]
    out["tags_unsupported"], out["profiles_unsupported"] = len(results.tags), len(results.profiles)
    raw_counts = _raw_market_counts(raw)
    seen: dict[str, str] = {}
    statuses = Counter()
    for position, event in enumerate(results.events):
        typed = tuple(event.markets or ())
        dropped = raw_counts[position] - len(typed) if raw_counts and position < len(raw_counts) else 0
        out["sdk_dropped_markets"] += max(dropped, 0)
        row = {"sdk_event_id": event.id, "markets": [], "sdk_dropped_markets": max(dropped, 0)}
        for market in typed:
            key = "market:polymarket:" + market.id if type(market.id) is str and _DECIMAL_RE.fullmatch(market.id) else None
            native_row = native.get(key) if key else None
            labels = [market.outcomes.yes.label, market.outcomes.no.label]
            sdk_tokens = [t for t in (market.outcomes.yes.token_id, market.outcomes.no.token_id) if t is not None]
            if key is None:
                status = "MARKET_ID_NONCANONICAL"
            elif native_row is None:
                status = "NOT_IN_UNIVERSE"
            elif native_row["identity_status"] != "VALID":
                status = "NATIVE_IDENTITY_ABSTAINED"
            elif market.condition_id != native_row["condition_id"]:
                status = "CONDITION_ID_CONFLICT"
            elif set(labels) != set(native_row["outcome_labels"]) or (
                    sdk_tokens and {"token:polymarket:" + t for t in sdk_tokens} != set(native_row["token_ids"])):
                status = "OUTCOME_TOKEN_CONFLICT"
            elif key in seen:
                status = "DUPLICATE_MARKET" if seen[key] == event.id else "EVENT_RELATION_CONFLICT"
            else:
                status = "IDENTITY_CONSISTENT"
            if key:
                seen.setdefault(key, event.id)
            statuses[status] += 1
            row["markets"].append({
                "sdk_market_id": market.id, "native_market_id": key if native_row else None, "status": status,
                "native_event_id": native_row["event_id"] if native_row else None,
                "event_identity": ("EVENT_ID_MATCHES_NATIVE" if native_row and native_row["event_id"] == "event:polymarket:" + event.id
                                   else "EVENT_ID_UNVERIFIED"),
                # SDK v0.10.0 maps outcomes[0] -> .yes positionally, whatever its label says
                "sdk_yes_slot_label": labels[0], "sdk_yes_slot_positional": True,
                "orientation": "ORIENTATION_UNPROVEN", "tradable_side": None})
        native_events = {m["native_event_id"] for m in row["markets"] if m["status"] == "IDENTITY_CONSISTENT"}
        if len(native_events) > 1:
            for m in row["markets"]:
                if m["status"] == "IDENTITY_CONSISTENT":
                    m["status"] = "EVENT_RELATION_CONFLICT"
                    statuses["IDENTITY_CONSISTENT"] -= 1
                    statuses["EVENT_RELATION_CONFLICT"] += 1
        out["events"].append(row)
    for event_row in out["events"]:
        for m in event_row["markets"]:
            if m["status"] == "IDENTITY_CONSISTENT" and m["native_market_id"] not in out["ranked"]:
                out["ranked"].append(m["native_market_id"])
    out["ranked"] = out["ranked"][:TOP_K]
    out["market_status_counts"] = dict(sorted((k, v) for k, v in statuses.items() if v))
    out["status"] = "SDK_TYPED_PAGE_PROJECTED"
    return out


# ------------------------------------------------------------------ caller pages


def validate_pages(pages: object, ext_cases: dict) -> None:
    """Whole-file structure only; per-page defects become counted page statuses."""
    _require(isinstance(pages, dict) and set(pages) == PAGES_KEYS, "PAGES_FIELDS_INVALID")
    _require(pages["schema_id"] == PAGES_SCHEMA, "PAGES_SCHEMA_INVALID")
    _require(pages["source_label"] == SOURCE_LABEL, "SOURCE_LABEL_INVALID")
    _require(pages["corpus_class"] == ext_cases["corpus_class"], "CORPUS_CLASS_MISMATCH")
    _require(pages["ext_benchmark_sha256"] == ext_cases["benchmark_sha256"], "BENCHMARK_BINDING_MISMATCH")
    _require(pages["sdk"] == {"distribution": SDK_DISTRIBUTION, "version": SDK_VERSION}, "SDK_REQUIREMENT_MISMATCH")
    _require(type(pages["pages"]) is list and 0 < len(pages["pages"]) <= MAX_PAGES, "PAGES_LIST_INVALID")


def _page_precheck(entry: object, queries: dict, seen: set, as_of: str) -> tuple[str | None, bytes | None]:
    if type(entry) is not dict or set(entry) != PAGE_KEYS or type(entry["case_id"]) is not str \
            or type(entry["request"]) is not dict or type(entry["response"]) is not dict \
            or set(entry["response"]) != RESPONSE_KEYS or type(entry["response"]["status"]) is not int \
            or type(entry["response"]["content_type"]) is not str or type(entry["response"]["body_b64"]) is not str:
        return "PAGE_FIELDS_INVALID", None
    if entry["case_id"] in seen:
        return "DUPLICATE_PAGE", None
    seen.add(entry["case_id"])
    query = queries.get(entry["case_id"])
    if query is None:
        return "PAGE_CASE_NOT_PAIRED", None
    request = entry["request"]
    if not set(request) <= set(SDK_KWARGS):
        return "REQUEST_PARAMETER_UNSUPPORTED", None
    if type(request.get("q")) is not str or not request["q"].strip() \
            or type(request.get("page_size", TOP_K)) is not int or not 1 <= request.get("page_size", TOP_K) <= TOP_K \
            or any(type(request.get(k, False)) is not bool for k in ("search_tags", "search_profiles")) \
            or any(request.get(k) is not None and type(request[k]) is not str for k in ("events_status", "events_tag")):
        return "REQUEST_INVALID", None
    if any(request.get(k) != query.get(k) for k in ("q", "events_status", "events_tag")):
        return "REQUEST_CASE_MISMATCH", None
    captured = PMC._utc(entry["captured_at"])
    if captured is None:
        return "PAGE_FIELDS_INVALID", None
    if RP._utc_instant_key(captured) > RP._utc_instant_key(as_of):
        return "SOURCE_POST_CUTOFF", None  # a page observed after the snapshot would leak later state
    try:
        body = base64.b64decode(entry["response"]["body_b64"], validate=True)
    except (binascii.Error, ValueError):
        return "PAGE_FIELDS_INVALID", None
    if len(body) > MAX_PAGE_BYTES:
        return "PAGE_OVERSIZE", None
    return None, body


def _scan_page(body: bytes, strict_json) -> tuple[object, bool]:
    """Secret-shaped content anywhere stops the whole run; returns (strict object or None, strict_ok)."""
    try:
        parsed = strict_json(body, "PAGE_STRICT_JSON_INVALID")
    except SG.GroundingStop:
        _require(SG.SECRET_RE.search(body.decode("utf-8", "replace")) is None, "SECRET_MATERIAL_REJECTED")
        return None, False
    PMC.scan_material(parsed)
    return parsed, True


def valid_case_queries(ext_cases: dict, ext_core: dict) -> dict[str, dict]:
    """Queries of the EXT cases its own benchmark judged VALID (refused duplicates never pair)."""
    return {row["case_id"]: case["query"] for case, row in zip(ext_cases["cases"], ext_core["benchmark"]["cases"])
            if row["status"] == "VALID"}


def evaluate_pages(pages: dict, queries: dict, native: dict[str, dict], as_of: str, strict_json, timer=None) -> tuple[list, dict]:
    rows, seen, elapsed = [], set(), []
    with PublicClient() as client:
        for entry in pages["pages"]:
            rows.append(_evaluate_page(entry, queries, seen, native, as_of, strict_json, timer, elapsed, client))
    measured = {"sdk_invocations": len(elapsed), "sdk_elapsed_ns_total": int(sum(elapsed)),
                "sdk_elapsed_ns_max": int(max(elapsed, default=0))}
    return rows, measured


def _evaluate_page(entry, queries, seen, native, as_of, strict_json, timer, elapsed, client) -> dict:
    reason, body = _page_precheck(entry, queries, seen, as_of)
    row = {"case_id": entry.get("case_id") if isinstance(entry, dict) and type(entry.get("case_id")) is str else None,
           "status": reason, "sdk_invoked": False, "sdk_error": None, "requests": [], "body_sha256": None,
           "projection": None}
    if reason is None:
        parsed, strict_ok = _scan_page(body, strict_json)
        t0 = timer() if timer else 0
        call = invoke_search(entry["request"], body, entry["response"]["status"], entry["response"]["content_type"], client)
        elapsed.append((timer() - t0) if timer else 0)
        row.update(sdk_invoked=True, sdk_error=call["sdk_error"], requests=call["requests"],
                   body_sha256=SG.sha256_hex(body), captured_at=entry["captured_at"],
                   response_status=entry["response"]["status"], content_type=entry["response"]["content_type"])
        if call["status"] != "SDK_TYPED_PAGE":
            row["status"] = call["status"]
        elif not strict_ok:
            row["status"] = "STRICT_JSON_REJECTED"  # the SDK accepted NaN or duplicate keys; native strict JSON does not
        else:
            row["projection"] = project_typed_page(call["page"], parsed, native)
            row["status"] = row["projection"]["status"]
    return row


# ------------------------------------------------------------------ same-case comparison


def run_comparison(ext_core: dict, queries: dict, page_rows: list) -> dict:
    by_case = {r["case_id"]: r for r in page_rows if r["case_id"] and r["status"] != "DUPLICATE_PAGE"}
    rows = []
    for case in ext_core["benchmark"]["cases"]:
        if case["status"] != "VALID":
            continue
        page = by_case.get(case["case_id"])
        q = queries[case["case_id"]].get("q")
        searchable = type(q) is str and bool(q.strip())
        status = (page["status"] if page else "NO_PAGE_SUPPLIED") if searchable else "CASE_NOT_SDK_SEARCHABLE"
        ranked = page["projection"]["ranked"] if page and page["projection"] and status == "SDK_TYPED_PAGE_PROJECTED" else []
        rows.append({"case_id": case["case_id"], "status": "VALID", "relevant": case["relevant"], "sdk_page_status": status,
                     "paired": status == "SDK_TYPED_PAGE_PROJECTED", METHOD_ID: ranked,
                     PMC.METHOD_ID: case[PMC.METHOD_ID], PMC.BASELINE_ID: case[PMC.BASELINE_ID]})
    paired = [r for r in rows if r["paired"]]
    methods = (METHOD_ID, PMC.METHOD_ID, PMC.BASELINE_ID)
    projected = [p for p in page_rows if p["status"] == "SDK_TYPED_PAGE_PROJECTED"]
    market_counts = Counter()
    for p in projected:
        market_counts.update(p["projection"]["market_status_counts"])
    returned = sum(market_counts.values())
    labelled = [r for r in paired if r["relevant"]]
    completed = len(paired) >= PMC.MIN_BENCHMARK_CASES
    return {
        "status": "COMPLETED" if completed else "PAIRED_BENCHMARK_REFUSED",
        "metric_semantics": "SDK_ROWS_ARE_CALLER_SUPPLIED_FIXTURE_PAGES_PARSED_BY_THE_REAL_SDK_NOT_SDK_RETRIEVAL_QUALITY",
        "denominators": {
            "pages_submitted": len(page_rows),
            "pages_refused_before_sdk": sum(1 for p in page_rows if not p["sdk_invoked"]),
            "sdk_invocations": sum(1 for p in page_rows if p["sdk_invoked"]),
            "sdk_typed_pages_usable": len(projected),
            "page_status_counts": dict(sorted(Counter(p["status"] for p in page_rows).items())),
            "ext_cases_valid": len(rows), "cases_paired": len(paired),
            "cases_not_sdk_searchable": sum(1 for r in rows if r["sdk_page_status"] == "CASE_NOT_SDK_SEARCHABLE"),
            "cases_without_usable_page": sum(1 for r in rows if not r["paired"]),
            "paired_positive_labeled": len(labelled), "paired_negative_no_match": len(paired) - len(labelled)},
        "source_coverage": {
            "sdk_market_rows": returned, "sdk_market_status_counts": dict(sorted(market_counts.items())),
            "identity_consistent_rate": SG._ratio(market_counts["IDENTITY_CONSISTENT"], returned),
            "sdk_dropped_markets": sum(p["projection"]["sdk_dropped_markets"] for p in projected),
            "labels_present_in_page": SG._ratio(sum(len(set(r[METHOD_ID]) & set(r["relevant"])) for r in labelled),
                                                sum(len(r["relevant"]) for r in labelled)),
            "tags_unsupported": sum(p["projection"]["tags_unsupported"] for p in projected),
            "profiles_unsupported": sum(p["projection"]["profiles_unsupported"] for p in projected)},
        # fewer than fifty paired cases: no metrics at all, never a partial score
        "metrics_all_ext_valid_cases": {m: SG._method_metrics(rows, m) for m in methods} if completed else None,
        "metrics_sdk_paired_cases": {m: SG._method_metrics(paired, m) for m in methods} if completed else None,
        "lift_claim": None, "real_value": "NOT_VERIFIED",
        "cases": rows,
    }


# ------------------------------------------------------------------ receipt core


def build_sdk_core(ext_core: dict, ext_cases: dict, pages: dict, strict_json, code_identity: str, ext_code_identity: str,
                   file_hashes: dict, timer=None) -> tuple[dict, dict]:
    identity = sdk_identity()
    validate_pages(pages, ext_cases)
    native = {m["market_id"]: m for m in ext_core["corpus"]["markets"]}
    as_of = ext_core["inputs"]["as_of"]
    queries = valid_case_queries(ext_cases, ext_core)
    page_rows, measured = evaluate_pages(pages, queries, native, as_of, strict_json, timer)
    comparison = run_comparison(ext_core, queries, page_rows)
    real = ext_cases["corpus_class"] == "LOCAL_REAL_PIT"
    core = {
        "schema_id": RECEIPT_SCHEMA, "wp_id": WP_ID, "posture": SG.RESEARCH_ONLY, "safe_output": list(SAFE_OUTPUT),
        "caller": CALLER, "code_identity": code_identity, "sdk": identity, "source_label": SOURCE_LABEL,
        "source_authenticity": "SOURCE_ORIGIN_UNVERIFIED", "corpus_class": ext_cases["corpus_class"],
        "inputs": {"as_of": as_of, "file_sha256": file_hashes, "grounding_receipt_id": ext_core["inputs"]["grounding_receipt_id"],
                   "alpha_universe_snapshot_id": ext_core["inputs"]["alpha_universe_snapshot_id"],
                   "ext_benchmark_sha256": ext_cases["benchmark_sha256"], "ext_code_identity": ext_code_identity,
                   "ext_core_receipt_id": PMC.finalize(ext_core)["receipt_id"]},
        "native_corpus": {"markets_total": ext_core["corpus"]["markets_total"],
                          "identity_valid": ext_core["corpus"]["identity_valid"], "orientation_proven": 0},
        "pages": page_rows,
        "comparison": comparison,
        "ext_benchmark_reference": {"denominators": ext_core["benchmark"]["denominators"],
                                    "metrics": ext_core["benchmark"]["metrics"]},
        "real_benchmark": "OBSERVED_CALLER_FIXTURES_AWAITING_INDEPENDENT_REVIEW" if real else "NOT_RUN_REAL_DATA",
        "upstream_gaps": ["SDK_YES_SLOT_IS_POSITIONAL_NOT_SEMANTIC", "SDK_DROPS_NON_BINARY_OR_INVALID_MARKETS_SILENTLY",
                          "SDK_ACCEPTS_NAN_AND_DUPLICATE_KEYS", "SDK_SEARCH_HAS_NO_EXACT_ID_OR_RULE_FILTERS",
                          "TAGS_AND_PROFILES_NOT_PROJECTED", "REAL_GAMMA_GET_NOT_AUTHORIZED"],
        "adoption": {"capabilities": {cid: ADOPTION_CHANGES.get(cid, "UNCHANGED_TRACKED") for cid in CAPABILITY_IDS},
                     "capability_register_total": len(CAPABILITY_IDS), "ccxt_direct_reuse": "NOT_ADOPTED_SEPARATE_DECISION",
                     "owner_value_acceptances": 0, "parity_auto_acceptance": False, "pr268": "SEPARATE_UNCONSUMED"},
        "authority": {"research_only": True, "advisory_only": True, "human_review_required": True,
                      "alpha_promotion": False, "canonical_writes": False, "wp170_registry_writes": False,
                      "tradable_side": False, "orders": False, "strategy": False, "paper": False, "live": False,
                      "capital": False, "llm_or_hermes": False, "credentials": False, "authenticated_methods": False,
                      "network_calls": 0, "provider_calls": 0, "real_gamma_requests": 0,
                      "sdk_methods_invoked": ["PublicClient.search"]},
    }
    return json.loads(SG.canonical_bytes(core)), measured


def finalize(core: dict, measurements: dict) -> dict:
    """The id binds the deterministic core only; wall-clock measurements are reported beside it."""
    return {"core": core, "receipt_id": RECEIPT_PREFIX + SG.sha256_hex(SG.canonical_bytes({"core": core})),
            "measurements": dict(measurements, reproducible=False)}
