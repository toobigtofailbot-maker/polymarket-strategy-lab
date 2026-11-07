"""Dormant one-request official SDK public search probe (S10-R3-REAL-PUBLIC-GET-01, Phase A).

The installed upstream ``polymarket-client==0.10.0`` builds and parses the request:
``PublicClient.search(q="bitcoin", page_size=2).first_page()`` -> ``GET /public-search`` with
``q=bitcoin&page=1&limit_per_type=2``. This module only supplies the transport underneath, through the
same ``SyncTransport(client=httpx.Client(...))`` seam S10-R3-SDK-DIRECT-01 uses, and a guard that
enforces the exact envelope at transport level: one attempt, exact HTTPS host/port/path/query/method,
no redirect, retry, proxy, environment, cookie or auth header, identity encoding, <= 1 MiB read before
the SDK parses, bounded timeouts and a 15 s wall budget. Nothing from the SDK is copied.

Activation is sealed. ``OWNER_ACTIVATION_SHA256`` is ``None`` in Phase A, so ``live`` refuses before any
transport exists. Only a reviewed change merged by the owner may pin the SHA-256 of one exact owner
activation record; a caller-created file, flag or fixture can never satisfy the pin. The pin is a
repository review control, not a cryptographic signature.

Posture: research only, no credentials, no order, strategy, paper, capital or live-trading authority.
"""
from __future__ import annotations

import dataclasses
import json
import threading
import time

import httpx
from polymarket.clients._transport import SyncTransport
from polymarket.clients.public import PublicClient
from polymarket.errors import PolymarketError

from src.data_layer.analytical_research import official_sdk_search_bridge as OSB
from src.data_layer.analytical_research import public_market_contract_parity as PMC
from src.data_layer.analytical_research import source_grounding as SG

WP_ID = "S10-R3-REAL-PUBLIC-GET-01"
RECEIPT_SCHEMA = "s10-r3-real-public-get01-receipt-v1"
RECEIPT_PREFIX = "sdkpublicget:sha256:"
ACTIVATION_SCHEMA = "s10-r3-real-public-get01-owner-activation-v1"

# Phase B (S10-R3-REAL-PUBLIC-GET-01B): SHA-256 of Karl's exact approved record; usable only once owner-merged.
OWNER_ACTIVATION_SHA256: str | None = "a642058790796d4ec4de25c6b03003d0b0c0242c942a9b5c58843ddc4520634a"

GAMMA_BASE = "https://gamma-api.polymarket.com"
HOST = "gamma-api.polymarket.com"
PATH = OSB.SEARCH_PATH
SDK_CALL = {"q": "bitcoin", "page_size": 2}
QUERY = (("limit_per_type", "2"), ("page", "1"), ("q", "bitcoin"))
REQUEST_URL = GAMMA_BASE + PATH + "?q=bitcoin&page=1&limit_per_type=2"
MAX_ATTEMPTS = 1
MAX_BODY_BYTES = 1 << 20
WALL_SECONDS = 15.0
TIMEOUT = httpx.Timeout(connect=4.0, read=4.0, write=4.0, pool=1.0)
ALLOWED_HEADERS = frozenset({"host", "accept", "accept-encoding", "connection", "user-agent"})

TRANSPORT_PUBLIC = "PUBLIC_TLS_TRANSPORT_OBSERVED"
TRANSPORT_INJECTED = "TEST_INJECTED_TRANSPORT_NOT_PUBLIC"
SOURCE_AUTHENTICITY = "REMOTE_CONTENT_NOT_INDEPENDENTLY_ATTESTED"
SAFE_OUTPUT = ("RESEARCH_ONLY", "DIRECT_UPSTREAM_SDK", "ONE_ATTEMPT_MAXIMUM", "TLS_GET_IS_NOT_SETTLEMENT_OR_PIT_EVIDENCE",
               "SINGLE_PAGE_NOT_A_BENCHMARK", "NO_CREDENTIALS", "NO_TRADING")
ACTIVATION_KEYS = {"schema_id", "wp_id", "approved_by", "attempt_id", "request_url", "max_attempts", "scratch_dir",
                   "not_before_utc", "not_after_utc", "envelope_sha256"}
ATTEMPT_KEYS = {"outcome", "network_dials", "http_status", "content_type", "byte_count", "body_sha256",
                "acquired_start_utc", "acquired_end_utc", "duration_ns"}


class ProbeRefusal(Exception):
    """Closed refusal raised inside the transport; deliberately not an httpx error so the SDK never wraps it."""


def envelope() -> dict:
    return {"method": "GET", "url": REQUEST_URL, "scheme": "https", "host": HOST, "port": 443, "path": PATH,
            "query": [list(p) for p in QUERY], "sdk_call": "PublicClient.search(q='bitcoin', page_size=2).first_page()",
            "max_attempts": MAX_ATTEMPTS, "max_body_bytes": MAX_BODY_BYTES, "wall_seconds": str(WALL_SECONDS),
            "timeout": {"connect": "4.0", "read": "4.0", "write": "4.0", "pool": "1.0"}, "retries": 0,
            "follow_redirects": False, "trust_env": False, "proxy": None, "tls_verify": True, "http2": False,
            "accept_encoding": "identity", "cookies": False, "auth_headers": False, "pagination_followed": False,
            "sdk": {"distribution": OSB.SDK_DISTRIBUTION, "version": OSB.SDK_VERSION, "commit": OSB.SDK_COMMIT}}


def envelope_sha256() -> str:
    return SG.sha256_hex(SG.canonical_bytes(envelope()))


# ------------------------------------------------------------------ guarded transport


def request_defect(request: httpx.Request) -> str | None:
    url = request.url
    if request.method != "GET":
        return "METHOD_REFUSED"
    if url.scheme != "https" or url.host != HOST or url.port not in (None, 443) or url.userinfo:
        return "HOST_REFUSED"
    if url.path != PATH or url.fragment:
        return "PATH_REFUSED"
    if tuple(sorted(url.params.multi_items())) != QUERY:
        return "QUERY_REFUSED"
    names = {k.decode("latin-1").lower() for k, _ in request.headers.raw}
    if not names <= ALLOWED_HEADERS or request.headers.get("accept-encoding") != "identity":
        return "HEADER_REFUSED"
    try:
        has_body = bool(request.content)
    except httpx.RequestNotRead:
        has_body = True
    if has_body:
        return "BODY_REFUSED"
    return None


class OneShotTransport(httpx.BaseTransport):
    """Lets at most one request through to ``inner`` and reads at most MAX_BODY_BYTES within the wall budget."""

    def __init__(self, inner: httpx.BaseTransport, started: float, clock=time.monotonic):
        self.inner, self.started, self.clock = inner, started, clock
        self.calls, self.dials, self.facts = 0, 0, {}

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        self.calls += 1
        if self.calls > MAX_ATTEMPTS:
            raise ProbeRefusal("SECOND_REQUEST_REFUSED")
        defect = request_defect(request)
        if defect:
            raise ProbeRefusal(defect)
        self.dials += 1  # counted before dialing: a failed attempt is still the one attempt
        response = self.inner.handle_request(request)
        try:
            status = response.status_code
            content_type = response.headers.get("content-type", "")
            self.facts.update(http_status=status, content_type=content_type[:128])
            if 300 <= status < 400:
                raise ProbeRefusal("REDIRECT_REFUSED")
            if response.headers.get("content-encoding", "identity").lower() != "identity":
                raise ProbeRefusal("CONTENT_ENCODING_REFUSED")
            declared = response.headers.get("content-length")
            if declared is not None and (not declared.isdigit() or int(declared) > MAX_BODY_BYTES):
                raise ProbeRefusal("RESPONSE_OVERSIZE")
            body, chunks = bytearray(), iter(response.stream)
            while True:
                # the next read may block for one read timeout: stop before it could cross the wall
                if self.clock() - self.started + TIMEOUT.read > WALL_SECONDS:
                    raise ProbeRefusal("TIME_BUDGET_EXCEEDED")
                chunk = next(chunks, None)
                if chunk is None:
                    break
                body += chunk
                if len(body) > MAX_BODY_BYTES:
                    raise ProbeRefusal("RESPONSE_OVERSIZE")
            self.facts["body"] = bytes(body)
        finally:
            response.close()
        return httpx.Response(status, headers={"content-type": content_type}, content=bytes(body), request=request)


def public_inner_transport() -> httpx.HTTPTransport:
    """The only real egress: TLS verified, HTTP/1.1, no retries, no proxy, no environment."""
    return httpx.HTTPTransport(verify=True, trust_env=False, http1=True, http2=False, retries=0, proxy=None,
                               limits=httpx.Limits(max_connections=1, max_keepalive_connections=0))


def _utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _one_attempt(inner: httpx.BaseTransport, client: PublicClient, clock) -> dict:
    started = clock()
    guard = OneShotTransport(inner, started, clock)
    result = {"outcome": None, "start_utc": _utc_now(), "guard": guard}
    original = client._ctx
    with httpx.Client(base_url=GAMMA_BASE, transport=guard, trust_env=False, follow_redirects=False, timeout=TIMEOUT,
                      headers={"accept-encoding": "identity"}) as http:
        client._ctx = dataclasses.replace(original, gamma=SyncTransport(base_url=GAMMA_BASE, client=http))
        try:
            client.search(**SDK_CALL).first_page()
            result["outcome"] = "SDK_TYPED_PAGE"
        except ProbeRefusal as refusal:
            result["outcome"] = str(refusal)
        except PolymarketError as error:  # 429/5xx/non-JSON: a counted failed attempt, never retried
            result["outcome"] = OSB._sdk_error_code(error, guard.facts.get("http_status", 0))
        except Exception:  # noqa: BLE001 - sanitized, no exception text kept
            result["outcome"] = "TRANSPORT_FAILED"
        finally:
            client._ctx = original
    result.update(end_utc=_utc_now(), duration_ns=int((clock() - started) * 1e9))
    return result


def acquire(inner: httpx.BaseTransport | None = None, clock=time.monotonic, client: PublicClient | None = None) -> dict:
    """Exactly one SDK attempt, run in a worker so the caller regains control within the wall budget.

    ``inner=None`` is the real public egress and is reachable only after ``authorize_live``. ``client``
    lets tests share one SDK client (its constructor builds five TLS-configured httpx clients)."""
    if client is None:
        with PublicClient() as own:
            return acquire(inner, clock, own)
    transport_origin = TRANSPORT_PUBLIC if inner is None else TRANSPORT_INJECTED
    box: dict = {}
    inner = inner or public_inner_transport()
    worker = threading.Thread(target=lambda: box.update(_one_attempt(inner, client, clock)), daemon=True)
    worker.start()
    worker.join(WALL_SECONDS + 1.0)
    if worker.is_alive():  # DNS or a stalled peer: the attempt is spent and abandoned, never repeated
        return {"outcome": "TIME_BUDGET_EXCEEDED", "network_dials": 1, "http_status": None, "content_type": None,
                "body": None, "acquired_start_utc": None, "acquired_end_utc": _utc_now(), "duration_ns": None,
                "transport_origin": transport_origin}
    guard = box["guard"]
    return {"outcome": box["outcome"], "network_dials": guard.dials, "http_status": guard.facts.get("http_status"),
            "content_type": guard.facts.get("content_type"), "body": guard.facts.get("body"),
            "acquired_start_utc": box["start_utc"], "acquired_end_utc": box["end_utc"],
            "duration_ns": box["duration_ns"], "transport_origin": transport_origin}


# ------------------------------------------------------------------ owner activation (sealed in Phase A)


def authorize_live(record_raw: bytes, scratch_dir: str, now_utc: str, strict_json) -> dict:
    """Refuses unless the record is byte-identical to the merged owner pin and still binds this exact attempt."""
    _require = OSB._require
    _require(OWNER_ACTIVATION_SHA256 is not None, "LIVE_ACTIVATION_SEALED")
    _require(SG.sha256_hex(record_raw) == OWNER_ACTIVATION_SHA256, "ACTIVATION_FINGERPRINT_MISMATCH")
    record = strict_json(record_raw, "ACTIVATION_RECORD_INVALID")
    _require(isinstance(record, dict) and set(record) == ACTIVATION_KEYS, "ACTIVATION_RECORD_INVALID")
    _require(record["schema_id"] == ACTIVATION_SCHEMA and record["wp_id"] == WP_ID
             and record["request_url"] == REQUEST_URL and record["max_attempts"] == MAX_ATTEMPTS
             and record["envelope_sha256"] == envelope_sha256(), "ACTIVATION_SCOPE_MISMATCH")
    _require(record["scratch_dir"] == scratch_dir, "ACTIVATION_SCRATCH_MISMATCH")
    start, end = PMC._utc(record["not_before_utc"]), PMC._utc(record["not_after_utc"])
    _require(start is not None and end is not None
             and PMC._key(start) <= PMC._key(now_utc) <= PMC._key(end), "ACTIVATION_WINDOW_INVALID")
    return record


# ------------------------------------------------------------------ offline replay, receipt


def first_page_view(page):
    """The single first page with its continuation stripped: the cursor is recorded, never followed."""
    return dataclasses.replace(page, has_more=False, next_cursor=None)


def replay(body: bytes | None, status: int | None, content_type: str | None, strict_json, native: dict | None = None,
           client: PublicClient | None = None) -> dict:
    """Re-run the real SDK on the frozen bytes through OSB's MockTransport seam; deterministic and offline."""
    if body is None or type(status) is not int:
        return {"sdk_status": "NO_RESPONSE_CAPTURED", "strict_json": "NOT_CHECKED", "summary": None, "projection": None}
    call = OSB.invoke_search(dict(SDK_CALL), body, status, content_type or "", client)
    try:
        parsed, strict = strict_json(body, "STRICT_JSON_REJECTED"), "STRICT_JSON_OK"
    except SG.GroundingStop:
        parsed, strict = None, "STRICT_JSON_REJECTED"  # the SDK may accept NaN or duplicate keys; native strict JSON never does
    out = {"sdk_status": call["status"], "strict_json": strict, "summary": None, "projection": None}
    if call["status"] != "SDK_TYPED_PAGE":
        return out
    page = call["page"]
    results = page.items[0]
    ids = [m.id for e in results.events for m in (e.markets or ())]
    out["summary"] = {"events": len(results.events), "typed_markets": len(ids),
                      "decimal_market_ids": sorted({i for i in ids if type(i) is str and OSB._DECIMAL_RE.fullmatch(i)}),
                      "noncanonical_market_ids": sum(1 for i in ids if not (type(i) is str and OSB._DECIMAL_RE.fullmatch(i))),
                      "tags_unsupported": len(results.tags), "profiles_unsupported": len(results.profiles),
                      "continuation_present": bool(page.has_more), "continuation_followed": False}
    if native is not None and parsed is not None:
        out["projection"] = OSB.project_typed_page(first_page_view(page), parsed, native)
    return out


def build_core(attempt: dict, activation_sha256: str | None, code_identity: str, strict_json,
               client: PublicClient | None = None) -> dict:
    facts = {k: attempt[k] for k in ATTEMPT_KEYS - {"body_sha256", "byte_count"}}
    body = attempt["body"]
    facts.update(byte_count=len(body) if body is not None else None,
                 body_sha256=SG.sha256_hex(body) if body is not None else None)
    parsed = replay(body, attempt["http_status"], attempt["content_type"], strict_json, client=client)
    core = {
        "schema_id": RECEIPT_SCHEMA, "wp_id": WP_ID, "posture": SG.RESEARCH_ONLY, "safe_output": list(SAFE_OUTPUT),
        "code_identity": code_identity, "sdk": OSB.sdk_identity(), "envelope": envelope(),
        "envelope_sha256": envelope_sha256(), "activation_record_sha256": activation_sha256,
        "transport_origin": attempt["transport_origin"], "source_authenticity": SOURCE_AUTHENTICITY,
        "attempt": facts, "sdk_replay": {k: parsed[k] for k in ("sdk_status", "strict_json", "summary")},
        "native_pit_crosscheck": "NOT_IN_RECEIPT_RUN_BY_VERIFY",
        "adoption": {"R3-23": "DIRECT_UPSTREAM_INTEGRATED_OPERATIONAL_VALUE_PENDING_OWNER",
                     "capability_register_total": len(OSB.CAPABILITY_IDS), "owner_value_acceptances": 0,
                     "benchmark": "NOT_RUN_SINGLE_PAGE", "lift_claim": None, "pr268": "SEPARATE_UNCONSUMED"},
        "authority": {"research_only": True, "canonical_writes": False, "orders": False, "strategy": False,
                      "paper": False, "live_trading": False, "capital": False, "credentials": False,
                      "hermes": False, "provider_calls": 0, "scheduler": False, "max_network_dials": MAX_ATTEMPTS},
    }
    canonical = SG.canonical_bytes(core)
    OSB._require(SG.SECRET_RE.search(canonical.decode("utf-8")) is None, "RECEIPT_SECRET_SHAPED")  # never echoes content
    return json.loads(canonical)


def finalize(core: dict) -> dict:
    return {"core": core, "receipt_id": RECEIPT_PREFIX + SG.sha256_hex(SG.canonical_bytes({"core": core}))}


def receipt_bytes(receipt: dict) -> bytes:
    return json.dumps(receipt, sort_keys=True, indent=1, ensure_ascii=True).encode("ascii")
