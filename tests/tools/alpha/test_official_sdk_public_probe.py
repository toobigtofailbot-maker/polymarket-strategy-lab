"""S10-R3-REAL-PUBLIC-GET-01 offline tests (Phase A): the REAL installed polymarket-client 0.10.0
PublicClient.search(q="bitcoin", page_size=2).first_page() over the one-shot guarded transport.

Every response comes from ``httpx.MockTransport`` standing in for the inner socket transport; every
socket entry point is blocked for every test. Owner activation is sealed in the repository; tests
that exercise the dormant acquisition path pin a test record with ``monkeypatch`` only, and every
such receipt is labelled TEST_INJECTED_TRANSPORT_NOT_PUBLIC. No test dials a real host.
"""
from __future__ import annotations

import ast
import json
import os
from pathlib import Path
import shutil
import ssl
import threading
import time

import httpx
import pytest

from polymarket.clients.public import PublicClient
from polymarket.models.gamma.search import SearchResults

from src.data_layer.analytical_research import official_sdk_public_probe as PROBE
from src.data_layer.analytical_research import official_sdk_search_bridge as OSB
from src.data_layer.analytical_research import public_market_contract_parity as PMC
from src.data_layer.analytical_research import source_grounding as SG
from tests.tools.alpha.test_official_sdk_search import gamma_body
from tests.tools.alpha.test_public_market_contract_parity import cond, dec, make_world, mid, tree
from tools.alpha import run_official_sdk_public_probe as CLI
from tools.alpha import run_source_grounding as SGCLI

REPO_ROOT = Path(__file__).resolve().parents[3]
PROBE_SRC = Path(PROBE.__file__).read_text(encoding="utf-8")
CLI_SRC = Path(CLI.__file__).read_text(encoding="utf-8")
NOW = "2026-11-07T12:00:00Z"
HITS = ["oh-sen-dem", "oh-sen-rep"]
BODY = gamma_body(HITS, pagination={"hasMore": True, "totalResults": 9})
SDK = None


@pytest.fixture(scope="module", autouse=True)
def sdk_client():
    global SDK
    with PublicClient() as SDK:
        yield SDK


@pytest.fixture(autouse=True)
def offline():
    with SGCLI.no_network() as attempts:
        yield
    assert not attempts, "a socket entry point was reached"


@pytest.fixture(scope="module")
def world(tmp_path_factory):
    with SGCLI.no_network():
        return make_world(tmp_path_factory.mktemp("pubget_inputs"))


class RawChunks(httpx.SyncByteStream):
    """Undecoded chunks, as the real socket transport returns them (no eager read or decode)."""

    def __init__(self, *chunks):
        self.chunks = chunks

    def __iter__(self):
        yield from self.chunks


def mock(status=200, body=BODY, headers=None, log=None, raise_error=None, stream=None):
    log = [] if log is None else log

    def handler(request):
        log.append(request)
        if raise_error is not None:
            raise raise_error
        if stream is not None:
            return httpx.Response(status, headers={"content-type": "application/json", **(headers or {})}, stream=stream)
        return httpx.Response(status, content=body, headers={"content-type": "application/json", **(headers or {})})
    return httpx.MockTransport(handler), log


def record(scratch, **over):
    value = {"schema_id": PROBE.ACTIVATION_SCHEMA, "wp_id": PROBE.WP_ID, "approved_by": "test-fixture-not-owner",
             "attempt_id": "t-0001", "request_url": PROBE.REQUEST_URL, "max_attempts": 1, "scratch_dir": str(scratch),
             "not_before_utc": "2026-11-01T00:00:00Z", "not_after_utc": "2026-11-30T00:00:00Z",
             "envelope_sha256": PROBE.envelope_sha256()}
    value.update(over)
    return SG.canonical_bytes(value)


def write_record(tmp_path, scratch, name="record.json", **over):
    path = (tmp_path / name).resolve()
    path.write_bytes(record(scratch, **over))
    return path


def pinned_live(monkeypatch, tmp_path, inner, name="acq", **over):
    scratch = (tmp_path / name).resolve()
    path = write_record(tmp_path, scratch, f"{name}-record.json", **over)
    monkeypatch.setattr(PROBE, "OWNER_ACTIVATION_SHA256", SG.sha256_hex(path.read_bytes()))
    return scratch, path, CLI.live(scratch, path, inner=inner, now_utc=NOW)


def one(inner, clock=None):
    return PROBE.acquire(inner, clock or time.monotonic, client=SDK)


def guard_request(**over):
    params = over.pop("params", {"q": "bitcoin", "page": "1", "limit_per_type": "2"})
    url = over.pop("url", PROBE.GAMMA_BASE + PROBE.PATH)
    headers = {"accept-encoding": "identity", **over.pop("headers", {})}
    return httpx.Request(over.pop("method", "GET"), url, params=params, headers=headers, **over)


@pytest.fixture(scope="module")
def acquired(tmp_path_factory):
    """One dormant-path acquisition with a monkeypatched test pin and an injected inner transport."""
    base = tmp_path_factory.mktemp("pubget_acq")
    inner, log = mock(headers={"set-cookie": "sess=DO-NOT-ECHO", "x-request-id": "DO-NOT-ECHO"})
    with SGCLI.no_network() as attempts, pytest.MonkeyPatch.context() as mp:
        scratch, path, result = pinned_live(mp, base, inner)
        pin = PROBE.OWNER_ACTIVATION_SHA256
    assert not attempts
    return {"scratch": scratch, "record": path, "result": result, "log": log, "pin": pin, "base": base}


# ------------------------------------------------------------------ R001


def test_probe_real_pinned_sdk_method(monkeypatch):
    identity = OSB.sdk_identity()
    assert identity["version"] == "0.10.0" and identity["commit"] == "579bb2e56be9cc5d152546985870ee6ad795ec52"
    assert identity["installed_blobs_match_tag"] is True and identity["files"] == OSB.SDK_FILES
    calls = []
    real = PublicClient.search

    def spy(self, **kwargs):
        calls.append(kwargs)
        return real(self, **kwargs)
    monkeypatch.setattr(PublicClient, "search", spy)
    inner, log = mock()
    attempt = one(inner)
    assert attempt["outcome"] == "SDK_TYPED_PAGE" and calls == [{"q": "bitcoin", "page_size": 2}] and len(log) == 1
    monkeypatch.setattr(PublicClient, "search", real)
    # the frozen bytes re-parse through the SDK's own typed models via the SDK-DIRECT-01 MockTransport seam
    call = OSB.invoke_search(dict(PROBE.SDK_CALL), attempt["body"], 200, "application/json", SDK)
    assert call["status"] == "SDK_TYPED_PAGE" and type(call["page"].items[0]) is SearchResults
    replayed = PROBE.replay(attempt["body"], 200, "application/json", SGCLI._strict_json, client=SDK)
    assert replayed["summary"]["typed_markets"] == 2 and replayed["summary"]["decimal_market_ids"] == sorted(dec(s) for s in HITS)
    # no copied SDK logic or search algorithm: no parser/paginator/model code, SDK reached only by import
    tree_ = ast.parse(PROBE_SRC)
    assert {n.name for n in ast.walk(tree_) if isinstance(n, ast.ClassDef)} == {"ProbeRefusal", "OneShotTransport"}
    funcs = {n.name for n in ast.walk(tree_) if isinstance(n, ast.FunctionDef)}
    assert not funcs & {"search", "search_spec", "parse_page", "sync_paginate_page_based", "rank", "score"}
    imports = {n.module for n in ast.walk(tree_) if isinstance(n, ast.ImportFrom)}
    assert {"polymarket.clients.public", "polymarket.clients._transport"} <= imports
    assert OSB.SDK_VERSION == "0.10.0" and PROBE.SDK_CALL == {"q": "bitcoin", "page_size": 2}


# ------------------------------------------------------------------ R002


def test_probe_exact_one_request_transport(monkeypatch):
    inner, log = mock()
    attempt = one(inner)
    assert attempt["outcome"] == "SDK_TYPED_PAGE" and attempt["network_dials"] == 1 and len(log) == 1
    sent = log[0]
    assert sent.method == "GET" and str(sent.url) == PROBE.REQUEST_URL
    assert sorted(sent.url.params.multi_items()) == [("limit_per_type", "2"), ("page", "1"), ("q", "bitcoin")]
    names = {k.lower() for k in sent.headers}
    assert names <= PROBE.ALLOWED_HEADERS and sent.headers["accept-encoding"] == "identity"
    assert not names & {"cookie", "authorization", "proxy-authorization"} and sent.content == b""
    assert sent.extensions["timeout"] == {"connect": 4.0, "read": 4.0, "write": 4.0, "pool": 1.0}
    # the continuation exists but is never followed: still exactly one request
    replayed = PROBE.replay(attempt["body"], 200, "application/json", SGCLI._strict_json, client=SDK)
    assert replayed["summary"]["continuation_present"] is True and replayed["summary"]["continuation_followed"] is False
    # the real egress: TLS verified with hostname check, HTTP/1.1 only, zero retries, one connection, no proxy
    for key, value in {"HTTPS_PROXY": "http://127.0.0.1:9", "ALL_PROXY": "http://127.0.0.1:9", "SSL_CERT_FILE": "missing"}.items():
        monkeypatch.setenv(key, value)
    real = PROBE.public_inner_transport()
    pool = real._pool
    assert type(pool).__name__ == "ConnectionPool" and pool._retries == 0 and pool._http2 is False
    assert pool._ssl_context.verify_mode == ssl.CERT_REQUIRED and pool._ssl_context.check_hostname is True
    assert pool._max_connections == 1 and pool._max_keepalive_connections == 0
    real.close()
    env = PROBE.envelope()
    assert env["url"] == "https://gamma-api.polymarket.com/public-search?q=bitcoin&page=1&limit_per_type=2"
    assert (env["max_attempts"], env["max_body_bytes"], env["wall_seconds"], env["retries"]) == (1, 1 << 20, "15.0", 0)
    assert env["follow_redirects"] is False and env["trust_env"] is False and env["proxy"] is None and env["tls_verify"]
    assert "trust_env=False, follow_redirects=False" in PROBE_SRC
    # the read cap applies to bytes before the SDK parses: exactly 1 MiB is read, one more byte is refused
    exact = b'{"events":[]}' + b" " * (PROBE.MAX_BODY_BYTES - 13)
    assert one(mock(body=exact)[0])["outcome"] == "SDK_TYPED_PAGE"
    over = one(mock(body=exact + b" ")[0])
    assert over["outcome"] == "RESPONSE_OVERSIZE" and over["network_dials"] == 1 and over["body"] is None
    # wall budget: a read that could cross 15 s is not started
    ticks = iter([0.0, 0.0, 12.0, 12.0, 12.0, 12.0])
    slow = one(mock()[0], clock=lambda: next(ticks, 12.0))
    assert slow["outcome"] == "TIME_BUDGET_EXCEEDED" and slow["network_dials"] == 1


# ------------------------------------------------------------------ R003


def test_probe_activation_requires_independent_owner_gate(tmp_path, monkeypatch, capsys):
    assert PROBE.OWNER_ACTIVATION_SHA256 is None  # Phase A: sealed in the committed source
    pin = [n for n in ast.walk(ast.parse(PROBE_SRC)) if isinstance(n, ast.AnnAssign)
           and getattr(n.target, "id", None) == "OWNER_ACTIVATION_SHA256"]
    assert len(pin) == 1 and isinstance(pin[0].value, ast.Constant) and pin[0].value.value is None
    built = []
    monkeypatch.setattr(PROBE, "public_inner_transport", lambda: built.append(1))
    monkeypatch.setattr(PROBE, "acquire", lambda *a, **k: built.append(2))
    scratch = (tmp_path / "s").resolve()
    good = write_record(tmp_path, scratch)  # a perfectly shaped, self-authored record is still not owner approval
    for argv in (["live", "--scratch-dir", str(scratch), "--activation-record", str(good)],
                 ["live", "--scratch-dir", str(scratch), "--activation-record", str(tmp_path / "absent.json")],
                 ["live", "--scratch-dir", "relative", "--activation-record", "x"]):
        assert CLI.main(argv) == 1
        out = json.loads(capsys.readouterr().out)
        assert out["status"] == "STOPPED" and out["reason_code"] == "LIVE_ACTIVATION_SEALED"
    assert built == [] and not scratch.exists()
    assert "live(args.scratch_dir, args.activation_record)" in CLI_SRC  # argparse never injects a transport
    checked = CLI.check()
    assert checked["live_activation"] == "SEALED" and checked["actual_live_get_executed"] is False
    # even with a pin, only the byte-identical pinned record passes; a caller cannot self-approve
    monkeypatch.setattr(PROBE, "OWNER_ACTIVATION_SHA256", SG.sha256_hex(record(scratch, attempt_id="owner-1")))
    for raw in (good.read_bytes(), record(scratch, attempt_id="owner-1") + b" ", b""):
        with pytest.raises(SG.GroundingStop, match="ACTIVATION_FINGERPRINT_MISMATCH"):
            PROBE.authorize_live(raw, str(scratch), NOW, SGCLI._strict_json)
    assert PROBE.authorize_live(record(scratch, attempt_id="owner-1"), str(scratch), NOW, SGCLI._strict_json)
    for over, code in (({"request_url": PROBE.REQUEST_URL + "&x=1"}, "ACTIVATION_SCOPE_MISMATCH"),
                       ({"max_attempts": 2}, "ACTIVATION_SCOPE_MISMATCH"),
                       ({"envelope_sha256": "0" * 64}, "ACTIVATION_SCOPE_MISMATCH"),
                       ({"wp_id": "S10-R3-SDK-DIRECT-01"}, "ACTIVATION_SCOPE_MISMATCH"),
                       ({"scratch_dir": str(tmp_path / "other")}, "ACTIVATION_SCRATCH_MISMATCH"),
                       ({"not_after_utc": "2026-11-07T11:59:59Z"}, "ACTIVATION_WINDOW_INVALID"),
                       ({"not_before_utc": "2026-11-07T12:00:01Z"}, "ACTIVATION_WINDOW_INVALID"),
                       ({"not_before_utc": "yesterday"}, "ACTIVATION_WINDOW_INVALID")):
        raw = record(scratch, **over)
        monkeypatch.setattr(PROBE, "OWNER_ACTIVATION_SHA256", SG.sha256_hex(raw))
        with pytest.raises(SG.GroundingStop, match=code):
            PROBE.authorize_live(raw, str(scratch), NOW, SGCLI._strict_json)
    extra = json.loads(record(scratch)) | {"note": 1}
    raw = SG.canonical_bytes(extra)
    monkeypatch.setattr(PROBE, "OWNER_ACTIVATION_SHA256", SG.sha256_hex(raw))
    with pytest.raises(SG.GroundingStop, match="ACTIVATION_RECORD_INVALID"):
        PROBE.authorize_live(raw, str(scratch), NOW, SGCLI._strict_json)
    assert built == []


# ------------------------------------------------------------------ R004


def test_probe_raw_source_freeze_and_receipt(acquired, tmp_path, monkeypatch):
    scratch, result = acquired["scratch"], acquired["result"]
    assert result["status"] == "ACQUIRED" and result["outcome"] == "SDK_TYPED_PAGE" and result["network_attempts"] == 1
    assert len(acquired["log"]) == 1 and result["transport_origin"] == PROBE.TRANSPORT_INJECTED
    assert sorted(p.name for p in scratch.iterdir()) == ["attempt_claimed.json", "raw_response.bin", "receipt.json"]
    assert (scratch / "raw_response.bin").read_bytes() == BODY
    receipt = json.loads((scratch / "receipt.json").read_text(encoding="ascii"))
    core, facts = receipt["core"], receipt["core"]["attempt"]
    assert receipt["receipt_id"] == PROBE.finalize(core)["receipt_id"] == result["receipt_id"]
    assert set(facts) == PROBE.ATTEMPT_KEYS and facts["http_status"] == 200 and facts["content_type"] == "application/json"
    assert facts["byte_count"] == len(BODY) and facts["body_sha256"] == SG.sha256_hex(BODY) and facts["network_dials"] == 1
    assert PMC._utc(facts["acquired_start_utc"]) == facts["acquired_start_utc"]
    assert facts["acquired_start_utc"] <= facts["acquired_end_utc"] and type(facts["duration_ns"]) is int
    assert core["envelope"] == PROBE.envelope() and core["sdk"] == OSB.sdk_identity()
    assert core["code_identity"] == CLI.code_identity() and core["activation_record_sha256"] == acquired["pin"]
    assert core["source_authenticity"] == "REMOTE_CONTENT_NOT_INDEPENDENTLY_ATTESTED"
    assert PROBE.TRANSPORT_PUBLIC == "PUBLIC_TLS_TRANSPORT_OBSERVED" != core["transport_origin"]
    assert core["sdk_replay"]["sdk_status"] == "SDK_TYPED_PAGE" and core["sdk_replay"]["strict_json"] == "STRICT_JSON_OK"
    text = (scratch / "receipt.json").read_text(encoding="ascii")
    assert "DO-NOT-ECHO" not in text and "set-cookie" not in text and SG.SECRET_RE.search(text) is None
    assert cond(HITS[0]) not in text  # a condition id is never copied into the receipt
    # a failed attempt is still the one attempt: counted, frozen, never retried
    inner, log = mock(status=503, body=b'{"error":"busy"}')
    scratch2, _, failed = pinned_live(monkeypatch, tmp_path, inner, name="fail503")
    assert failed["status"] == "ACQUIRED" and failed["outcome"] == "SDK_REQUEST_REJECTED" and len(log) == 1
    facts2 = json.loads((scratch2 / "receipt.json").read_text(encoding="ascii"))["core"]["attempt"]
    assert facts2["http_status"] == 503 and facts2["network_dials"] == 1 and facts2["byte_count"] == 16
    assert CLI.verify(scratch2)["status"] == "VERIFIED"


# ------------------------------------------------------------------ R005


def test_probe_native_pit_research_crosscheck(acquired, world, tmp_path, monkeypatch):
    scratch = acquired["scratch"]
    before = tree(world["base"])
    crossed = CLI.verify(scratch, world["grounding"])
    assert crossed["status"] == "VERIFIED"
    check = crossed["native_pit_crosscheck"]
    assert check["status"] == "CROSSED" and check["grounding_receipt_id"] == world["receipt_id"]
    assert check["market_status_counts"] == {"IDENTITY_CONSISTENT": 2} and check["ranked_native_ids"] == [mid(s) for s in HITS]
    assert check["orientation"] == "ORIENTATION_UNPROVEN" and check["tradable_side"] is None
    assert check["settlement_equivalence"] == "NOT_CLAIMED" and check["real_value"] == "NOT_VERIFIED"
    assert tree(world["base"]) == before  # read-only: no canonical or PIT write
    assert CLI.verify(scratch)["native_pit_crosscheck"] == {"status": "NATIVE_PIT_CROSSCHECK_NOT_RUN"}
    assert CLI.verify(scratch, Path("relative"))["native_pit_crosscheck"]["reason"] == "GROUNDING_SCRATCH_UNUSABLE"
    bad = tmp_path / "bad_grounding"
    shutil.copytree(world["grounding"], bad)
    (bad / "receipt.json").write_bytes((bad / "receipt.json").read_bytes().replace(b'"', b"'", 1))
    assert CLI.verify(scratch, bad.resolve())["native_pit_crosscheck"] == {"status": "NOT_CROSSED",
                                                                           "reason": "GROUNDING_NOT_VERIFIED"}
    # unknown markets and conflicting identities abstain; nothing is guessed
    body = json.loads(BODY)
    body["events"][0]["markets"][0]["conditionId"] = "0x" + "d" * 64
    body["events"].append({"id": "899999", "markets": [{"id": "990001", "conditionId": "0x" + "e" * 64,
                                                         "outcomes": '["Yes","No"]', "clobTokenIds": '["11","12"]'}]})
    scratch2, _, out = pinned_live(monkeypatch, tmp_path, mock(body=json.dumps(body).encode())[0], name="conflict")
    counts = CLI.verify(scratch2, world["grounding"])["native_pit_crosscheck"]["market_status_counts"]
    assert counts == {"CONDITION_ID_CONFLICT": 1, "IDENTITY_CONSISTENT": 1, "NOT_IN_UNIVERSE": 1}
    # a PIT snapshot later than the acquisition is a source/time conflict, never crossed
    monkeypatch.setattr(PROBE, "_utc_now", lambda: "2026-01-01T00:00:00Z")
    scratch3, _, _ = pinned_live(monkeypatch, tmp_path, mock()[0], name="early", not_before_utc="2025-12-01T00:00:00Z")
    assert CLI.verify(scratch3, world["grounding"])["native_pit_crosscheck"] == {"status": "NOT_CROSSED",
                                                                                 "reason": "SOURCE_TIME_CONFLICT"}


# ------------------------------------------------------------------ R006


def test_probe_cold_replay_idempotence_and_no_repeat_network(acquired, tmp_path, monkeypatch):
    scratch, log = acquired["scratch"], acquired["log"]
    before = tree(scratch)
    first, second = CLI.verify(scratch), CLI.verify(scratch)
    assert first == second and first["status"] == "VERIFIED" and first["failures"] == [] and first["network_attempts"] == 0
    assert tree(scratch) == before and len(log) == 1  # replay is offline, writes nothing, dials nothing
    monkeypatch.setattr(PROBE, "OWNER_ACTIVATION_SHA256", acquired["pin"])
    calls = []
    monkeypatch.setattr(PROBE, "acquire", lambda *a, **k: calls.append(1))
    again = CLI.live(scratch, acquired["record"], inner=mock()[0], now_utc=NOW)
    assert again == {"status": "IDEMPOTENT_VERIFIED", "receipt_id": first["receipt_id"], "network_attempts": 0}
    other = write_record(tmp_path, scratch, "other.json", attempt_id="t-0002")
    monkeypatch.setattr(PROBE, "OWNER_ACTIVATION_SHA256", SG.sha256_hex(other.read_bytes()))
    with pytest.raises(SG.GroundingStop, match="ATTEMPT_ALREADY_CONSUMED"):
        CLI.live(scratch, other, inner=mock()[0], now_utc=NOW)
    # a claimed attempt without a receipt (crash after claim) is spent, never retried
    crashed = (tmp_path / "crashed").resolve()
    crashed.mkdir()
    (crashed / CLI.ATTEMPT_MARKER).write_bytes(b"{}")
    path = write_record(tmp_path, crashed, "crashed.json")
    monkeypatch.setattr(PROBE, "OWNER_ACTIVATION_SHA256", SG.sha256_hex(path.read_bytes()))
    with pytest.raises(SG.GroundingStop, match="ATTEMPT_ALREADY_CONSUMED"):
        CLI.live(crashed, path, inner=mock()[0], now_utc=NOW)
    assert calls == [] and tree(scratch) == before
    # only absolute scratch outside the repository; no symlink, hardlink or in-scratch record
    with pytest.raises(SG.GroundingStop, match="SCRATCH_INSIDE_REPOSITORY"):
        CLI.live(REPO_ROOT / "scratch_here", path, inner=mock()[0], now_utc=NOW)
    fresh = (tmp_path / "fresh").resolve()
    link = tmp_path / "hard.json"
    real_record = write_record(tmp_path, fresh, "fresh.json")
    os.link(real_record, link)
    monkeypatch.setattr(PROBE, "OWNER_ACTIVATION_SHA256", SG.sha256_hex(real_record.read_bytes()))
    with pytest.raises(SG.GroundingStop, match="ACTIVATION_FINGERPRINT_MISMATCH"):
        CLI.live(fresh, link.resolve(), inner=mock()[0], now_utc=NOW)  # hardlinked record reads as unusable
    assert not fresh.exists()
    try:
        alias = tmp_path / "alias"
        alias.symlink_to(tmp_path / "target_dir", target_is_directory=True)
    except OSError:
        alias = None
    if alias is not None:
        with pytest.raises(SG.GroundingStop, match="SCRATCH_(INVALID|INSIDE_REPOSITORY)"):
            CLI.live(alias, real_record, inner=mock()[0], now_utc=NOW)
    # tamper stops: raw bytes, receipt field, receipt id
    copy = tmp_path / "tamper"
    shutil.copytree(scratch, copy)
    (copy / "raw_response.bin").write_bytes(BODY.replace(b"Ohio", b"Iowa", 1))
    assert CLI.verify(copy.resolve())["failures"] == ["OUTPUT_MISMATCH:attempt"]
    shutil.copyfile(scratch / "raw_response.bin", copy / "raw_response.bin")
    receipt = json.loads((copy / "receipt.json").read_text(encoding="ascii"))
    receipt["core"]["transport_origin"] = PROBE.TRANSPORT_PUBLIC
    (copy / "receipt.json").write_bytes(PROBE.receipt_bytes(receipt))
    assert CLI.verify(copy.resolve())["failures"] == ["RECEIPT_ID_MISMATCH"]
    # an exhaustive no-polling posture: the CLI has no loop, sleep or scheduler
    nodes = list(ast.walk(ast.parse(CLI_SRC)))
    names = {getattr(n.func, "attr", getattr(n.func, "id", None)) for n in nodes if isinstance(n, ast.Call)}
    assert not names & {"sleep", "schedule", "Timer"} and not any(isinstance(n, ast.While) for n in nodes)


# ------------------------------------------------------------------ R007


def test_probe_negative_security_and_adversarial_matrix(tmp_path, monkeypatch, capsys):
    # request envelope: refused before the inner transport is ever reached
    for over, code in (
            ({"url": "http://gamma-api.polymarket.com/public-search"}, "HOST_REFUSED"),
            ({"url": "https://clob.polymarket.com/public-search"}, "HOST_REFUSED"),
            ({"url": "https://gamma-api.polymarket.com:8443/public-search"}, "HOST_REFUSED"),
            ({"url": "https://user:pw@gamma-api.polymarket.com/public-search"}, "HOST_REFUSED"),
            ({"url": "https://gamma-api.polymarket.com/markets"}, "PATH_REFUSED"),
            ({"url": "https://gamma-api.polymarket.com/public-search#x"}, "PATH_REFUSED"),
            ({"params": {"q": "ethereum", "page": "1", "limit_per_type": "2"}}, "QUERY_REFUSED"),
            ({"params": {"q": "bitcoin", "page": "2", "limit_per_type": "2"}}, "QUERY_REFUSED"),
            ({"params": {"q": "bitcoin", "page": "1", "limit_per_type": "2", "events_tag": "x"}}, "QUERY_REFUSED"),
            ({"params": [("q", "bitcoin"), ("q", "bitcoin"), ("page", "1"), ("limit_per_type", "2")]}, "QUERY_REFUSED"),
            ({"method": "POST"}, "METHOD_REFUSED"),
            ({"method": "HEAD"}, "METHOD_REFUSED"),
            ({"headers": {"cookie": "a=b"}}, "HEADER_REFUSED"),
            ({"headers": {"authorization": "Basic eDp5"}}, "HEADER_REFUSED"),
            ({"headers": {"proxy-authorization": "Basic eDp5"}}, "HEADER_REFUSED"),
            ({"headers": {"accept-encoding": "gzip"}}, "HEADER_REFUSED"),
            ({"content": b"x"}, "HEADER_REFUSED")):
        inner, log = mock()
        guard = PROBE.OneShotTransport(inner, time.monotonic())
        with pytest.raises(PROBE.ProbeRefusal, match=code):
            guard.handle_request(guard_request(**over))
        assert log == [] and guard.dials == 0
    assert PROBE.request_defect(httpx.Request("GET", PROBE.REQUEST_URL, content=b"x",
                                              headers={"accept-encoding": "identity", "content-length": "1"})) \
        in ("HEADER_REFUSED", "BODY_REFUSED")
    # an unexpected second request through the same guard never reaches the inner transport
    inner, log = mock()
    guard = PROBE.OneShotTransport(inner, time.monotonic())
    guard.handle_request(guard_request()).close()
    with pytest.raises(PROBE.ProbeRefusal, match="SECOND_REQUEST_REFUSED"):
        guard.handle_request(guard_request())
    assert len(log) == 1 and guard.dials == 1
    # responses: each is one counted attempt, never followed, retried or parsed past the guard
    big = b'{"events":[' + b" " * PROBE.MAX_BODY_BYTES + b"]}"
    for kwargs, outcome in (
            ({"status": 301, "headers": {"location": "https://evil.invalid/"}}, "REDIRECT_REFUSED"),
            ({"status": 307, "headers": {"location": PROBE.REQUEST_URL}}, "REDIRECT_REFUSED"),
            ({"status": 429, "headers": {"retry-after": "0"}}, "SDK_RATE_LIMITED"),
            ({"status": 500}, "SDK_REQUEST_REJECTED"),
            ({"status": 502}, "SDK_REQUEST_REJECTED"),
            ({"status": 503}, "SDK_REQUEST_REJECTED"),
            ({"body": b"{not json"}, "SDK_PARSE_REJECTED"),
            ({"body": b"<html>blocked</html>", "headers": {"content-type": "text/html"}}, "SDK_PARSE_REJECTED"),
            ({"body": b'{"events":"not-a-list"}'}, "SDK_PARSE_REJECTED"),
            ({"body": big}, "RESPONSE_OVERSIZE"),
            ({"stream": httpx.ByteStream(big)}, "RESPONSE_OVERSIZE"),
            ({"headers": {"content-length": "99999999"}}, "RESPONSE_OVERSIZE"),
            ({"headers": {"content-encoding": "gzip"}, "stream": RawChunks(b"gzip-bytes")}, "CONTENT_ENCODING_REFUSED"),
            ({"stream": RawChunks(*[b" " * 65536] * 17)}, "RESPONSE_OVERSIZE"),
            ({"raise_error": httpx.ConnectError("refused")}, "SDK_TRANSPORT_ERROR"),
            ({"raise_error": httpx.ReadTimeout("slow")}, "SDK_TRANSPORT_ERROR")):
        inner, log = mock(**kwargs)
        attempt = one(inner)
        assert attempt["outcome"] == outcome, kwargs
        assert attempt["network_dials"] == 1 and len(log) == 1, kwargs
    # NaN / duplicate keys: the SDK accepts them, native strict JSON flags the frozen bytes
    for raw in (b'{"events":[],"x":NaN}', b'{"events":[],"events":[]}'):
        attempt = one(mock(body=raw)[0])
        core = PROBE.build_core(attempt, None, "code:sha256:" + "0" * 64, SGCLI._strict_json, client=SDK)
        assert attempt["outcome"] == "SDK_TYPED_PAGE" and core["sdk_replay"]["strict_json"] == "STRICT_JSON_REJECTED"
    # a stalled peer (or DNS) cannot hold the caller past the wall budget; the attempt is spent
    monkeypatch.setattr(PROBE, "WALL_SECONDS", 0.2)
    release = threading.Event()
    hung = httpx.MockTransport(lambda request: (release.wait(10), httpx.Response(200, content=BODY))[1])
    with PublicClient() as own:
        stalled = PROBE.acquire(hung, client=own)
        release.set()
    assert stalled["outcome"] == "TIME_BUDGET_EXCEEDED" and stalled["network_dials"] == 1 and stalled["body"] is None
    monkeypatch.undo()
    # proxy / credential environment cannot leak into the request
    netrc = tmp_path / "netrc"
    netrc.write_text("machine gamma-api.polymarket.com login u password p\n", encoding="utf-8")
    for key, value in {"NETRC": str(netrc), "HTTPS_PROXY": "http://127.0.0.1:9", "HTTP_PROXY": "http://127.0.0.1:9",
                       "ALL_PROXY": "socks5://127.0.0.1:9", "SSL_CERT_FILE": str(netrc)}.items():
        monkeypatch.setenv(key, value)
    inner, log = mock()
    assert one(inner)["outcome"] == "SDK_TYPED_PAGE" and "authorization" not in log[0].headers
    monkeypatch.undo()
    # SDK drift stops before the attempt is claimed
    inner, log = mock()
    scratch = (tmp_path / "drift").resolve()
    path = write_record(tmp_path, scratch, "drift.json")
    monkeypatch.setattr(PROBE, "OWNER_ACTIVATION_SHA256", SG.sha256_hex(path.read_bytes()))
    monkeypatch.setattr(OSB.metadata, "version", lambda name: "0.10.1")
    with pytest.raises(SG.GroundingStop, match="SDK_VERSION_MISMATCH"):
        CLI.live(scratch, path, inner=inner, now_utc=NOW)
    monkeypatch.setattr(OSB.metadata, "version", lambda name: "0.10.0")
    monkeypatch.setitem(OSB.SDK_FILES, "clients/public.py", "0" * 40)
    with pytest.raises(SG.GroundingStop, match="SDK_SOURCE_MISMATCH"):
        CLI.live(scratch, path, inner=inner, now_utc=NOW)
    assert log == [] and not (scratch / CLI.ATTEMPT_MARKER).exists()
    monkeypatch.undo()
    # missing approval / changed fingerprint / invalid paths: closed, sanitized refusals
    monkeypatch.setattr(PROBE, "OWNER_ACTIVATION_SHA256", SG.sha256_hex(path.read_bytes()))
    path.write_bytes(record(scratch, attempt_id="edited"))
    for argv, code in ((["live", "--scratch-dir", str(scratch), "--activation-record", str(path)], "ACTIVATION_FINGERPRINT_MISMATCH"),
                       (["live", "--scratch-dir", str(scratch), "--activation-record", str(tmp_path / "missing")], "ACTIVATION_FINGERPRINT_MISMATCH"),
                       (["live", "--scratch-dir", "rel/dir", "--activation-record", str(path)], "SCRATCH_INSIDE_REPOSITORY"),
                       (["verify", "--scratch-dir", "rel/dir"], "SCRATCH_INVALID"),
                       (["verify", "--scratch-dir", str(tmp_path.resolve())], "RECEIPT_UNREADABLE")):
        assert CLI.main(argv) == 1
        out = capsys.readouterr().out
        assert json.loads(out)["reason_code"] == code and str(tmp_path) not in out and "edited" not in out
    # receipt time conflict and raw tampering are detected on cold replay
    inner, _ = mock()
    scratch2, _, _ = pinned_live(monkeypatch, tmp_path, inner, name="times")
    receipt = json.loads((scratch2 / "receipt.json").read_text(encoding="ascii"))
    receipt["core"]["attempt"]["acquired_start_utc"] = "2026-11-08T00:00:00Z"
    receipt = PROBE.finalize(receipt["core"])
    (scratch2 / "receipt.json").write_bytes(PROBE.receipt_bytes(receipt))
    assert CLI.verify(scratch2)["failures"] == ["ACQUISITION_TIME_CONFLICT"]
    (scratch2 / "raw_response.bin").write_bytes(b'{"events":[]}')
    assert "OUTPUT_MISMATCH:attempt" in CLI.verify(scratch2)["failures"]


# ------------------------------------------------------------------ R008


def test_probe_owner_scope_and_36_adoption_boundary(acquired):
    assert len(OSB.CAPABILITY_IDS) == len(set(OSB.CAPABILITY_IDS)) == 36
    core = json.loads((acquired["scratch"] / "receipt.json").read_text(encoding="ascii"))["core"]
    adoption = core["adoption"]
    assert adoption["capability_register_total"] == 36 and adoption["owner_value_acceptances"] == 0
    assert adoption["R3-23"] == "DIRECT_UPSTREAM_INTEGRATED_OPERATIONAL_VALUE_PENDING_OWNER"
    assert adoption["benchmark"] == "NOT_RUN_SINGLE_PAGE" and adoption["lift_claim"] is None
    assert adoption["pr268"] == "SEPARATE_UNCONSUMED"
    authority = core["authority"]
    assert authority["max_network_dials"] == 1 and authority["provider_calls"] == 0 and authority["research_only"] is True
    assert not any(authority[k] for k in ("canonical_writes", "orders", "strategy", "paper", "live_trading", "capital",
                                          "credentials", "hermes", "scheduler"))
    assert {"SINGLE_PAGE_NOT_A_BENCHMARK", "NO_TRADING", "NO_CREDENTIALS"} <= set(core["safe_output"])
    # imports stay inside research, SDK public client and httpx; no protected runtime, Hermes or order path
    allowed = {"__future__", "dataclasses", "json", "threading", "time", "httpx", "argparse", "hashlib", "pathlib", "sys",
               "polymarket.clients._transport", "polymarket.clients.public", "polymarket.errors",
               "src.data_layer.analytical_research", "tools.alpha"}
    for source in (PROBE_SRC, CLI_SRC):
        mods = set()
        for n in ast.walk(ast.parse(source)):
            if isinstance(n, ast.ImportFrom):
                mods.add(n.module)
            elif isinstance(n, ast.Import):
                mods.update(a.name for a in n.names)
        assert mods <= allowed, mods - allowed
        lowered = source.lower()
        for word in ("mnemonic", "private_key", "clob.polymarket", "data-api", "execution_gateway", "paper_trading",
                     "live_pilot", "hermes_", "openai", "anthropic", "subprocess", "apscheduler", "crontab"):
            assert word not in lowered, word
    assert PROBE.OWNER_ACTIVATION_SHA256 is None and CLI.check()["actual_live_get_executed"] is False
    status = (REPO_ROOT / "docs/status_entries/S10-R3-REAL-PUBLIC-GET-01.md").read_text(encoding="utf-8")
    assert "ACTUAL_LIVE_GET_EXECUTED=NO" in status and "Merge NOT authorized" in status
    deferred = (REPO_ROOT / "docs/deferred_items_log.md").read_text(encoding="utf-8")
    assert "S10-R3-REAL-PUBLIC-GET-01-D001" in deferred
    contract = (REPO_ROOT / "docs/official_sdk_public_probe_contract.md").read_text(encoding="utf-8")
    assert "LIVE_ACTIVATION_SEALED" in contract and "REMOTE_CONTENT_NOT_INDEPENDENTLY_ATTESTED" in contract
