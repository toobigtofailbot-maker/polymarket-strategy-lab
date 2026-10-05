"""Focused tests for the S10-EXEC-FEAS-01 current public execution-feasibility core.

All acquisition tests use a deterministic fake opener; no test performs real network I/O.
"""

from __future__ import annotations

from dataclasses import replace
import ast
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest

import src.execution_feasibility as EF
from src.execution_feasibility import evaluator as V
from src.execution_feasibility import models as M
from src.execution_feasibility import public_market as P
from src.execution_feasibility import (
    ExecutionFeasibilityAssessment,
    ExecutionFeasibilityError,
    ExecutionIntent,
    PublicExecutionVenueSnapshot,
    assess_execution_feasibility,
    build_execution_intent,
    fetch_public_venue_snapshot,
    record_from_mapping,
    validate_execution_feasibility_assessment,
    validate_execution_intent,
    validate_public_venue_snapshot,
)
from src.strategy_lifecycle import build_strategy_family, build_strategy_version

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "src" / "execution_feasibility"
SPEC = ROOT / "docs" / "wp_specs" / "S10-EXEC-FEAS-01" / "wp_spec.json"

GAMMA_ID = "516710"
COND = "0x" + "ab" * 32
TOKEN = "71321045679252212594626385532706912750332728571942532289631379312455583992563"
OTHER_TOKEN = "52114319501245915516055106046884209969926127482827954674443846427813813222426"
T0 = 1_800_000_000_000_000_000
BOOK_MS = T0 // 1_000_000 - 1_000
CUTOFF = T0 - 30_000_000_000
AGE = 5_000_000_000

STRATEGY_SPEC = {
    "thesis": {"claim": "fixture thesis"},
    "universe": {"category": "weather"},
    "entry_rule": {"signal": "fixture"},
    "exit_rule": {"horizon": "resolution"},
    "execution_rule": {"style": "AGGRESSIVE_TAKER", "max_slippage": "0.02"},
    "parameters": {"lookback": 5},
}


def code_of(fn, *args, **kwargs) -> str:
    with pytest.raises(ExecutionFeasibilityError) as excinfo:
        fn(*args, **kwargs)
    assert str(excinfo.value) == excinfo.value.code
    assert excinfo.value.code in M.ERROR_CODES
    return excinfo.value.code


def strategy_version(spec: dict | None = None):
    family = build_strategy_family(
        family_key="feas.family", family_label="Feasibility family", created_time_ns=1,
        creation_provenance="unit:fixture",
    )
    return build_strategy_version(
        strategy_family_id=family.strategy_family_id, parent=None, strategy_label="fixture",
        evidence_posture="REPEATABLE_STATISTICAL", strategy_code_identity="strategy_code:v1",
        strategy_spec=STRATEGY_SPEC if spec is None else spec,
        adaptive_bounds={"lookback": {"kind": "INTEGER_RANGE", "min": 0, "max": 10}},
        created_time_ns=2, creation_provenance="unit:fixture",
    )


SV = strategy_version()


def intent(**changes) -> ExecutionIntent:
    values = dict(
        strategy_version=SV, gamma_market_id=GAMMA_ID, condition_id=COND, token_id=TOKEN,
        side="BUY", execution_style="AGGRESSIVE_TAKER", order_type="FOK",
        requested_shares="25", price_limit="0.55", post_only=False,
        information_cutoff_ns=CUTOFF, max_public_data_age_ns=AGE,
    )
    values.update(changes)
    return build_execution_intent(**values)


def passive(**changes) -> ExecutionIntent:
    values = dict(execution_style="PASSIVE_MAKER", order_type="GTC", post_only=True,
                  price_limit="0.51", requested_shares="20")
    values.update(changes)
    return intent(**values)


def gamma_doc(**changes) -> dict:
    doc = {
        "id": GAMMA_ID, "conditionId": COND,
        "clobTokenIds": json.dumps([TOKEN, OTHER_TOKEN]),
        "question": "fixture?", "active": True, "closed": False, "acceptingOrders": True,
        "enableOrderBook": True, "restricted": False, "negRisk": False,
        "orderPriceMinTickSize": 0.01, "orderMinSize": 5, "feesEnabled": True,
        "feeSchedule": {"rate": 0.0333, "exponent": 1, "takerOnly": True, "rebateRate": 0.2},
        "secondsDelay": 0,
    }
    for key, value in changes.items():
        if value is _DROP:
            doc.pop(key)
        else:
            doc[key] = value
    return doc


_DROP = object()
BIDS = [("0.50", "100"), ("0.49", "200")]
ASKS = [("0.52", "10"), ("0.53", "20"), ("0.55", "30"), ("0.60", "40")]


def book_doc(bids=BIDS, asks=ASKS, **changes) -> dict:
    # Wire order per the official API presentation: bids ascending, asks descending.
    doc = {
        "market": COND, "asset_id": TOKEN, "timestamp": str(BOOK_MS), "hash": "a" * 40,
        "bids": [{"price": p, "size": s} for p, s in sorted(bids, key=lambda x: float(x[0]))],
        "asks": [{"price": p, "size": s}
                 for p, s in sorted(asks, key=lambda x: float(x[0]), reverse=True)],
        "min_order_size": "5", "tick_size": "0.01", "neg_risk": False,
        "last_trade_price": "0.51",
    }
    for key, value in changes.items():
        if value is _DROP:
            doc.pop(key)
        else:
            doc[key] = value
    return doc


def body(doc) -> P.SourceFetchResult:
    return P.SourceFetchResult("BODY", json.dumps(doc).encode("utf-8"))


UNAVAILABLE = P.SourceFetchResult("UNAVAILABLE")


def snap(gamma=None, clob=None, *, completed=T0) -> PublicExecutionVenueSnapshot:
    return P.build_public_venue_snapshot(
        gamma_market_id=GAMMA_ID, condition_id=COND, token_id=TOKEN,
        acquisition_started_ns=completed - 10_000_000, acquisition_completed_ns=completed,
        gamma=body(gamma_doc()) if gamma is None else gamma,
        clob=body(book_doc()) if clob is None else clob,
    )


def assess(i=None, s=None, at=T0):
    return assess_execution_feasibility(intent() if i is None else i,
                                        snap() if s is None else s, evaluated_at_ns=at)


class FakeResponse:
    def __init__(self, status=200, payload=b"{}", headers=None):
        self.status = status
        self.payload = payload
        self.headers = {} if headers is None else headers
        self.read_sizes: list[int] = []
        self.closed = False

    def read(self, size):
        self.read_sizes.append(size)
        return self.payload[:size]

    def close(self):
        self.closed = True


class FakeOpener:
    def __init__(self, *outcomes):
        self.outcomes = list(outcomes)
        self.requests: list = []

    def open(self, request, timeout):
        self.requests.append((request, timeout))
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome


def clock(*values):
    queue = list(values)
    return lambda: queue.pop(0)


def ok_opener():
    return FakeOpener(FakeResponse(payload=json.dumps(gamma_doc()).encode()),
                      FakeResponse(payload=json.dumps(book_doc()).encode()))


def fetch(opener):
    return fetch_public_venue_snapshot(gamma_market_id=GAMMA_ID, condition_id=COND,
                                       token_id=TOKEN, opener=opener,
                                       clock_ns=clock(T0 - 10_000_000, T0))


SOURCES = sorted(PACKAGE.glob("*.py"))


def source_text() -> str:
    return "\n".join(path.read_text(encoding="utf-8") for path in SOURCES)


# ---------------------------------------------------------------------------
# A. Import / authority posture.
# ---------------------------------------------------------------------------

_AUDIT_SCRIPT = r"""
import sys, threading
events = []
WATCH = ("socket.", "sqlite3.connect", "subprocess.", "os.system", "os.posix_spawn",
         "os.startfile", "_winapi.CreateProcess", "urllib.Request", "http.client.connect",
         "os.putenv", "os.unsetenv")
def hook(name, args):
    if name.startswith(WATCH):
        events.append(name)
    elif name == "open" and len(args) > 1 and isinstance(args[1], str) and any(c in args[1] for c in "wax+"):
        events.append("open-write")
sys.addaudithook(hook)
before = threading.active_count()
import src.execution_feasibility as pkg
assert pkg.__all__
print(repr((events, threading.active_count() - before)))
"""


def test_r001_import_has_no_side_effects() -> None:
    result = subprocess.run([sys.executable, "-B", "-c", _AUDIT_SCRIPT], cwd=ROOT,
                            capture_output=True, text=True, check=True, timeout=120)
    assert result.stdout.strip() == "([], 0)"
    # Module bodies contain only imports, constants, classes and function definitions.
    for path in SOURCES:
        module = ast.parse(path.read_text(encoding="utf-8"))
        for node in module.body:
            assert not isinstance(node, (ast.Expr, ast.For, ast.While, ast.With, ast.Try)) or (
                isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant)
            ), path.name


FORBIDDEN_SOURCE_TERMS = (
    "SecureClient", "AsyncSecureClient", "AsyncPublicClient", "PublicClient", "private key",
    "private_key", "api_key", "api key", ".env", "os.environ", "getenv", "wallet balance",
    "allowance", "place_order", "place_limit_order", "place_market_order", "cancel_order",
    "sign_order", "src.execution_gateway", "src.paper_trading", "execution_gateway",
    "paper_trading", "sqlite3", "threading", "multiprocessing", "asyncio", "while True",
    "time.sleep", "Authorization", "Cookie", "websocket", "data-api", "geoblock",
    "EXECUTABLE_EDGE_PASS", "executable_edge", "write_text", "write_bytes", "mkdir",
)


def test_r002_no_forbidden_imports_or_terms() -> None:
    text = source_text()
    lowered = text.lower()
    for term in FORBIDDEN_SOURCE_TERMS:
        assert term.lower() not in lowered, term
    imported: set[str] = set()
    for path in SOURCES:
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                imported.add(node.module)
    for path in SOURCES:
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                assert node.func.id not in {"open", "exec", "eval", "__import__"}, path.name
    assert imported <= {
        "__future__", "dataclasses", "decimal", "hashlib", "http.client", "json", "re", "time",
        "typing", "urllib.error", "urllib.parse", "urllib.request", "src.strategy_lifecycle",
    }
    # Only the explicit acquisition wrapper may read the wall clock.
    assert "time.time_ns" in (PACKAGE / "public_market.py").read_text(encoding="utf-8")
    for name in ("models.py", "evaluator.py", "__init__.py"):
        assert "import time" not in (PACKAGE / name).read_text(encoding="utf-8"), name


def test_r003_public_api_is_small_and_has_no_mutation_or_persistence() -> None:
    assert set(EF.__all__) == {
        "DIAGNOSTIC_CODES", "EXECUTION_DIMENSION_STATES", "EXECUTION_FEASIBILITY_STATUSES",
        "EXECUTION_STYLES", "FEE_EXACTNESS", "ORDER_TYPES", "RECORD_KINDS", "SIDES",
        "SOURCE_STATES", "ExecutionFeasibilityAssessment", "ExecutionFeasibilityError",
        "ExecutionIntent", "PublicExecutionVenueSnapshot", "assess_execution_feasibility",
        "build_execution_intent", "fetch_public_venue_snapshot", "record_from_mapping",
        "validate_execution_feasibility_assessment", "validate_execution_intent",
        "validate_public_venue_snapshot",
    }
    for name in (n for n in EF.__all__ if not n.isupper()):
        lowered = name.lower()
        for verb in ("order_", "submit", "sign", "cancel", "store", "persist", "write", "save",
                     "journal", "cache", "urlopen", "opener"):
            assert verb not in lowered, name
    assert sorted(path.name for path in PACKAGE.iterdir() if path.suffix == ".py") == [
        "__init__.py", "evaluator.py", "models.py", "public_market.py"]
    assert not hasattr(EF, "public_get") and not hasattr(EF, "_default_opener")


# ---------------------------------------------------------------------------
# B. StrategyVersion binding.
# ---------------------------------------------------------------------------


def test_r004_valid_strategy_version_binds() -> None:
    built = intent()
    assert built.strategy_version_id == SV.strategy_version_id
    assert validate_execution_intent(built, strategy_version=SV) is built
    assert SV == strategy_version()  # never mutated


def test_r005_tampered_strategy_version_rejects() -> None:
    tampered = strategy_version()
    object.__setattr__(tampered, "strategy_label", "tampered")
    assert code_of(intent, strategy_version=tampered) == "STRATEGY_VERSION_INVALID"
    assert code_of(intent, strategy_version=SV.to_mapping()) == "STRATEGY_VERSION_INVALID"
    assert code_of(intent, strategy_version=None) == "STRATEGY_VERSION_INVALID"


def test_r006_execution_rule_digest_derives_from_exact_canonical_spec() -> None:
    rule = STRATEGY_SPEC["execution_rule"]
    raw = json.dumps({"execution_rule": rule}, sort_keys=True, separators=(",", ":"),
                     ensure_ascii=False).encode("utf-8")
    expected = "executionrule:sha256:" + hashlib.sha256(raw).hexdigest()
    assert intent().execution_rule_sha256 == expected
    other = strategy_version({**STRATEGY_SPEC, "execution_rule": {"style": "PASSIVE_MAKER"}})
    assert intent(strategy_version=other).execution_rule_sha256 != expected
    # Only execution_rule participates: a thesis change keeps the digest.
    thesis = strategy_version({**STRATEGY_SPEC, "thesis": {"claim": "other"}})
    assert intent(strategy_version=thesis).execution_rule_sha256 == expected


def test_r007_caller_cannot_substitute_execution_rule_digest() -> None:
    with pytest.raises(TypeError):
        intent(execution_rule_sha256="executionrule:sha256:" + "0" * 64)
    forged = replace(intent(), execution_intent_id=M._PENDING_ID,
                     execution_rule_sha256="executionrule:sha256:" + "0" * 64)
    assert code_of(validate_execution_intent, forged, strategy_version=SV) == \
        "EXECUTION_RULE_BINDING_INVALID"
    other = strategy_version({**STRATEGY_SPEC, "universe": {"category": "sports"}})
    assert code_of(validate_execution_intent, intent(), strategy_version=other) == \
        "EXECUTION_RULE_BINDING_INVALID"


# ---------------------------------------------------------------------------
# C. Intent semantics.
# ---------------------------------------------------------------------------


def test_r008_valid_aggressive_intents() -> None:
    for order_type in ("FOK", "FAK"):
        for side in ("BUY", "SELL"):
            built = intent(order_type=order_type, side=side)
            assert built.post_only is False and built.gtd_expiration_unix_s is None
            assert built.advisory_only and built.no_order_authority
            assert built.no_execution_authority and built.no_live_authority


def test_r009_valid_passive_intents() -> None:
    assert passive().order_type == "GTC"
    expiration = CUTOFF // 1_000_000_000 + 180
    gtd = passive(order_type="GTD", gtd_expiration_unix_s=expiration)
    assert gtd.gtd_expiration_unix_s == expiration


def test_r010_invalid_style_order_pair_rejects() -> None:
    for style, order_type, post_only in (("AGGRESSIVE_TAKER", "GTC", False),
                                         ("AGGRESSIVE_TAKER", "GTD", False),
                                         ("PASSIVE_MAKER", "FOK", True),
                                         ("PASSIVE_MAKER", "FAK", True)):
        assert code_of(intent, execution_style=style, order_type=order_type,
                       post_only=post_only) == "FIELD_VALUE_INVALID"
    for field, value in (("side", "buy"), ("execution_style", "HYBRID"), ("order_type", "IOC")):
        assert code_of(intent, **{field: value}) == "FIELD_VALUE_INVALID"


def test_r011_post_only_mismatch_rejects() -> None:
    assert code_of(intent, post_only=True) == "FIELD_VALUE_INVALID"
    assert code_of(passive, post_only=False) == "FIELD_VALUE_INVALID"
    assert code_of(intent, post_only=1) == "FIELD_TYPE_INVALID"


def test_r012_gtc_gtd_expiration_rules() -> None:
    floor_s = CUTOFF // 1_000_000_000
    assert code_of(passive, gtd_expiration_unix_s=floor_s + 600) == "FIELD_VALUE_INVALID"
    assert code_of(passive, order_type="GTD") == "FIELD_MISSING"
    assert code_of(passive, order_type="GTD", gtd_expiration_unix_s=floor_s + 179) == \
        "FIELD_VALUE_INVALID"
    assert code_of(passive, order_type="GTD", gtd_expiration_unix_s=True) == "FIELD_TYPE_INVALID"
    assert code_of(intent, gtd_expiration_unix_s=floor_s + 600) == "FIELD_VALUE_INVALID"


def test_r013_float_nan_and_noncanonical_numbers_reject() -> None:
    for bad in (0.5, float("nan"), "0.50", "+0.5", ".5", "5e-1", "NaN", "Infinity", "-0",
                "0.1234567890123456789"):
        assert code_of(intent, price_limit=bad) in {"FIELD_TYPE_INVALID", "FIELD_VALUE_INVALID"}
    for bad in (25, 25.0, "25.0", "025", "1e3"):
        assert code_of(intent, requested_shares=bad) in {"FIELD_TYPE_INVALID",
                                                         "FIELD_VALUE_INVALID"}


def test_r014_invalid_venue_ids_reject() -> None:
    for field, bad in (("gamma_market_id", "-1"), ("gamma_market_id", " 1"),
                       ("gamma_market_id", "1" * 33), ("gamma_market_id", "abc"),
                       ("gamma_market_id", 516710), ("condition_id", COND.upper()),
                       ("condition_id", COND[:-1]), ("condition_id", "https://x/y"),
                       ("token_id", "1" * 101), ("token_id", "+1"), ("token_id", "1 2"),
                       ("token_id", "")):
        assert code_of(intent, **{field: bad}) in {"FIELD_TYPE_INVALID", "FIELD_VALUE_INVALID"}


def test_r015_intent_numeric_bounds() -> None:
    assert code_of(intent, requested_shares="0") == "FIELD_VALUE_INVALID"
    assert code_of(intent, requested_shares="-1") == "FIELD_VALUE_INVALID"
    for price in ("0", "1", "1.5"):
        assert code_of(intent, price_limit=price) == "FIELD_VALUE_INVALID"
    assert code_of(intent, max_public_data_age_ns=0) == "FIELD_VALUE_INVALID"
    assert code_of(intent, max_public_data_age_ns=60_000_000_001) == "FIELD_VALUE_INVALID"
    assert intent(max_public_data_age_ns=60_000_000_000).max_public_data_age_ns == 60_000_000_000
    assert code_of(intent, information_cutoff_ns=-1) == "FIELD_VALUE_INVALID"
    assert intent(information_cutoff_ns=0).information_cutoff_ns == 0


# ---------------------------------------------------------------------------
# D. Acquisition hardening.
# ---------------------------------------------------------------------------


def test_r016_two_fixed_host_get_requests_only() -> None:
    opener = ok_opener()
    snapshot = fetch(opener)
    assert snapshot.gamma_source_state == snapshot.clob_source_state == "AVAILABLE"
    assert len(opener.requests) == P.MAX_REQUESTS_PER_ACQUISITION == 2
    (gamma_request, gamma_timeout), (clob_request, clob_timeout) = opener.requests
    assert gamma_request.full_url == f"https://gamma-api.polymarket.com/markets/{GAMMA_ID}"
    assert clob_request.full_url == f"https://clob.polymarket.com/book?token_id={TOKEN}"
    for request, timeout in opener.requests:
        assert request.get_method() == "GET" and request.data is None
        assert timeout == 5
        headers = {k.lower() for k in (*request.headers, *request.unredirected_hdrs)}
        assert headers == {"accept"}
    assert snapshot.acquisition_started_ns == T0 - 10_000_000
    assert snapshot.acquisition_completed_ns == T0


def test_r017_forbidden_scheme_host_method_and_port_reject_before_open() -> None:
    opener = FakeOpener()
    cases = (
        ("http://clob.polymarket.com/book?token_id=1", "GET", "NETWORK_SCHEME_FORBIDDEN"),
        ("https://data-api.polymarket.com/x", "GET", "NETWORK_HOST_FORBIDDEN"),
        ("https://clob.polymarket.com:8443/book", "GET", "NETWORK_HOST_FORBIDDEN"),
        ("https://user@clob.polymarket.com/book", "GET", "NETWORK_HOST_FORBIDDEN"),
        ("https://clob.polymarket.com.evil.test/book", "GET", "NETWORK_HOST_FORBIDDEN"),
        ("https://clob.polymarket.com/order", "POST", "NETWORK_METHOD_FORBIDDEN"),
        ("https://clob.polymarket.com/order", "DELETE", "NETWORK_METHOD_FORBIDDEN"),
    )
    for url, method, expected in cases:
        assert code_of(P.public_get, url, max_bytes=10, opener=opener, method=method) == expected
    assert opener.requests == []
    assert code_of(fetch_public_venue_snapshot, gamma_market_id="1/../x", condition_id=COND,
                   token_id=TOKEN, opener=opener, clock_ns=clock()) == "FIELD_VALUE_INVALID"
    assert opener.requests == []


def test_r018_redirects_are_rejected_not_followed() -> None:
    handler = P._NoRedirectHandler()
    with pytest.raises(P._RedirectRejected):
        handler.redirect_request(None, None, 302, "Found", {}, "https://evil.test/")
    default = P._default_opener()
    assert any(isinstance(h, P._NoRedirectHandler) for h in default.handlers)
    redirect = FakeResponse(status=302, payload=b"{}", headers={"Location": "https://evil.test"})
    opener = FakeOpener(P._RedirectRejected(), redirect)
    snapshot = fetch(opener)
    assert len(opener.requests) == 2
    assert snapshot.gamma_source_state == snapshot.clob_source_state == "UNAVAILABLE"
    assert redirect.read_sizes == []


def test_r019_no_retry_or_backoff_after_failure() -> None:
    opener = FakeOpener(OSError("boom"), TimeoutError("slow"))
    snapshot = fetch(opener)
    assert len(opener.requests) == 2
    assert snapshot.diagnostic_codes == ("SOURCE_GAMMA_UNAVAILABLE", "SOURCE_CLOB_UNAVAILABLE")
    for status in (404, 429, 500, 503):
        failing = FakeOpener(FakeResponse(status=status), FakeResponse(status=status))
        assert fetch(failing).gamma_source_state == "UNAVAILABLE"
        assert len(failing.requests) == 2


def test_r020_body_caps_and_oversize_sentinel() -> None:
    declared = FakeResponse(headers={"Content-Length": str(P.GAMMA_MAX_BYTES + 1)})
    result = P.public_get(P.gamma_market_url(GAMMA_ID), max_bytes=P.GAMMA_MAX_BYTES,
                          opener=FakeOpener(declared))
    assert result.outcome == "OVERSIZE" and declared.read_sizes == [] and declared.closed
    sentinel = FakeResponse(payload=b"x" * 11)
    result = P.public_get(P.gamma_market_url(GAMMA_ID), max_bytes=10, opener=FakeOpener(sentinel))
    assert result.outcome == "OVERSIZE" and sentinel.read_sizes == [11]
    exact = FakeResponse(payload=b"x" * 10)
    result = P.public_get(P.gamma_market_url(GAMMA_ID), max_bytes=10, opener=FakeOpener(exact))
    assert result == P.SourceFetchResult("BODY", b"x" * 10)
    snapshot = snap(gamma=P.SourceFetchResult("OVERSIZE"))
    assert snapshot.gamma_source_state == "INVALID" and snapshot.gamma_payload_sha256 is None
    assert (P.GAMMA_MAX_BYTES, P.CLOB_MAX_BYTES) == (1_048_576, 4_194_304)


def test_r021_errors_are_sanitized_and_never_echo_upstream_values() -> None:
    secret = "upstream-detail-0xdeadbeef-should-not-echo"
    opener = FakeOpener(OSError(secret),
                        FakeResponse(payload=json.dumps(book_doc(market=secret)).encode()))
    snapshot = fetch(opener)
    dumped = json.dumps(snapshot.to_mapping())
    assert secret not in dumped
    assert set(snapshot.diagnostic_codes) <= set(M.DIAGNOSTIC_CODES)
    with pytest.raises(ExecutionFeasibilityError) as excinfo:
        intent(token_id=secret)
    assert secret not in str(excinfo.value) and str(excinfo.value) == "FIELD_VALUE_INVALID"
    assert str(ExecutionFeasibilityError(secret)) == "INTERNAL_VALIDATION_FAILED"


def test_r022_gamma_unavailable_preserved_as_null_facts() -> None:
    snapshot = snap(gamma=UNAVAILABLE)
    assert snapshot.gamma_source_state == "UNAVAILABLE"
    assert all(getattr(snapshot, name) is None for name in M.GAMMA_FACT_FIELDS)
    assert snapshot.clob_source_state == "AVAILABLE"
    result = assess(s=snapshot)
    assert result.status == "INCONCLUSIVE" and result.market_dimension == "UNKNOWN"
    assert "SOURCE_GAMMA_UNAVAILABLE" in result.diagnostic_codes


def test_r023_clob_unavailable_preserved_as_null_facts() -> None:
    snapshot = snap(clob=UNAVAILABLE)
    assert snapshot.bids == () and snapshot.asks == () and snapshot.book_timestamp_ns is None
    result = assess(s=snapshot)
    assert result.status == "INCONCLUSIVE"
    assert (result.book_dimension, result.fill_dimension) == ("UNKNOWN", "UNKNOWN")
    assert result.best_ask is None and result.visible_fill_shares is None


def test_r024_malformed_json_and_shapes_are_invalid_sources() -> None:
    for raw in (b"{", b"\xff\xfe", b"[]", b'{"id": NaN}', b'{"a":1,"a":2}', b'"x"'):
        snapshot = snap(gamma=P.SourceFetchResult("BODY", raw),
                        clob=P.SourceFetchResult("BODY", raw))
        assert snapshot.gamma_source_state == snapshot.clob_source_state == "INVALID"
        assert snapshot.gamma_payload_sha256 == hashlib.sha256(raw).hexdigest()
    deep = b"[" * 13 + b"]" * 13
    assert snap(gamma=P.SourceFetchResult("BODY", deep)).gamma_source_state == "INVALID"
    with pytest.raises(P._Invalid):
        P.decode_public_json(deep)
    assert P.decode_public_json(b"[" * 12 + b"]" * 12) is not None
    for doc in (gamma_doc(active="true"), gamma_doc(orderMinSize="five"),
                gamma_doc(id=_DROP), gamma_doc(clobTokenIds="not json"),
                gamma_doc(secondsDelay=1.5)):
        assert snap(gamma=body(doc)).gamma_source_state == "INVALID"
    for doc in (book_doc(hash=_DROP), book_doc(timestamp="-5"), book_doc(neg_risk="no"),
                book_doc(tick_size="1")):
        assert snap(clob=body(doc)).clob_source_state == "INVALID"


# ---------------------------------------------------------------------------
# E. Identity reconciliation.
# ---------------------------------------------------------------------------


def test_r025_gamma_identity_and_token_membership() -> None:
    assert snap().gamma_source_state == "AVAILABLE"
    as_list = snap(gamma=body(gamma_doc(clobTokenIds=[OTHER_TOKEN, TOKEN])))
    assert as_list.gamma_source_state == "AVAILABLE"
    assert as_list.identity_preimage() == {**snap().identity_preimage(),
                                           "gamma_payload_sha256": as_list.gamma_payload_sha256}


def test_r026_identity_mismatch_is_invalid_source_with_diagnostic() -> None:
    for doc in (gamma_doc(id="516711"), gamma_doc(conditionId="0x" + "cd" * 32),
                gamma_doc(clobTokenIds=json.dumps([OTHER_TOKEN]))):
        snapshot = snap(gamma=body(doc))
        assert snapshot.gamma_source_state == "INVALID"
        assert "SOURCE_IDENTITY_MISMATCH" in snapshot.diagnostic_codes
        assert assess(s=snapshot).status == "INCONCLUSIVE"
    for doc in (book_doc(market="0x" + "cd" * 32), book_doc(asset_id=OTHER_TOKEN)):
        snapshot = snap(clob=body(doc))
        assert snapshot.clob_source_state == "INVALID"
        assert snapshot.diagnostic_codes == ("SOURCE_CLOB_INVALID", "SOURCE_IDENTITY_MISMATCH")
        result = assess(s=snapshot)
        assert result.identity_dimension == "UNKNOWN" and result.status == "INCONCLUSIVE"
    other = snap()
    other_intent = intent(token_id=OTHER_TOKEN)
    assert code_of(assess_execution_feasibility, other_intent, other, evaluated_at_ns=T0) == \
        "IDENTITY_DERIVATION_MISMATCH"


def test_r027_tick_source_conflict_inconclusive() -> None:
    result = assess(s=snap(clob=body(book_doc(tick_size="0.001"))))
    assert result.tick_dimension == "UNKNOWN" and result.status == "INCONCLUSIVE"
    assert "TICK_SOURCE_CONFLICT" in result.diagnostic_codes
    missing = assess(s=snap(gamma=body(gamma_doc(orderPriceMinTickSize=_DROP))))
    assert missing.tick_dimension == "UNKNOWN" and missing.status == "INCONCLUSIVE"


def test_r028_min_order_source_conflict_inconclusive() -> None:
    # S10-LIVE-ORCH-01 repair: unequal Gamma-notional and CLOB-share minima are no longer a
    # source conflict; they are two independent dimensions that may both pass.
    result = assess(s=snap(clob=body(book_doc(min_order_size="15"))))
    assert result.minimum_order_dimension == "PASS" and result.status == "FEASIBLE"
    assert "MIN_ORDER_SOURCE_CONFLICT" not in result.diagnostic_codes
    assert result.minimum_order_notional_usd == "5"


def test_r029_neg_risk_source_conflict_inconclusive() -> None:
    result = assess(s=snap(clob=body(book_doc(neg_risk=True))))
    assert result.identity_dimension == "UNKNOWN" and result.status == "INCONCLUSIVE"
    assert "NEG_RISK_SOURCE_CONFLICT" in result.diagnostic_codes
    agreed = assess(s=snap(gamma=body(gamma_doc(negRisk=True)),
                           clob=body(book_doc(neg_risk=True))))
    assert agreed.status == "FEASIBLE"  # negRisk itself is not NOT_FEASIBLE


# ---------------------------------------------------------------------------
# F. Book normalization.
# ---------------------------------------------------------------------------


def test_r030_wire_order_normalized_bids_descending_asks_ascending() -> None:
    raw = book_doc()
    assert [level["price"] for level in raw["bids"]] == ["0.49", "0.50"]
    assert [level["price"] for level in raw["asks"]] == ["0.60", "0.55", "0.53", "0.52"]
    snapshot = snap()
    assert [p for p, _ in snapshot.bids] == ["0.5", "0.49"]
    assert [p for p, _ in snapshot.asks] == ["0.52", "0.53", "0.55", "0.6"]
    shuffled = book_doc()
    shuffled["asks"] = [shuffled["asks"][i] for i in (2, 0, 3, 1)]
    assert snap(clob=body(shuffled)).asks == snapshot.asks
    mapping = snapshot.to_mapping()
    assert mapping["bids"][0] == {"price": "0.5", "size": "100"}


def test_r031_invalid_book_levels_reject() -> None:
    cases = (
        book_doc(bids=[("0.50", "1"), ("0.5", "2")]),
        book_doc(asks=[("0", "1")]), book_doc(asks=[("1", "1")]), book_doc(asks=[("1.2", "1")]),
        book_doc(asks=[("0.6", "0")]), book_doc(asks=[("0.6", "-1")]),
        book_doc(asks=[("0.6", "abc")]),
    )
    for doc in cases:
        snapshot = snap(clob=body(doc))
        assert snapshot.clob_source_state == "INVALID"
        assert "BOOK_INVALID" in snapshot.diagnostic_codes
    extra_key = book_doc()
    extra_key["asks"][0]["owner"] = "x"
    assert snap(clob=body(extra_key)).clob_source_state == "INVALID"


def test_r032_crossed_book_invalid() -> None:
    for asks in ([("0.50", "1")], [("0.45", "1")]):
        snapshot = snap(clob=body(book_doc(asks=asks)))
        assert snapshot.clob_source_state == "INVALID"
        assert snapshot.diagnostic_codes == ("SOURCE_CLOB_INVALID", "BOOK_INVALID")
    assert code_of(replace, snap(), asks=(("0.5", "1"),)) == "FIELD_VALUE_INVALID"


def test_r033_one_sided_book_is_valid_state() -> None:
    for bids, asks in (([], ASKS), (BIDS, []), ([], [])):
        snapshot = snap(clob=body(book_doc(bids=bids, asks=asks)))
        assert snapshot.clob_source_state == "AVAILABLE"
    empty = assess(s=snap(clob=body(book_doc(bids=[], asks=[]))))
    assert empty.best_bid is None and empty.best_ask is None and empty.spread is None


def test_r034_level_cap_enforced() -> None:
    at_cap = [{"price": f"0.{i:05d}", "size": "1"} for i in range(1, M.MAX_BOOK_LEVELS + 1)]
    assert len(P._book_levels(at_cap, descending=True)) == 5_000
    with pytest.raises(P._Invalid):
        P._book_levels(at_cap + [{"price": "0.9", "size": "1"}], descending=True)
    size = "1" * 30 + "." + "1" * 18
    big = book_doc(bids=[], asks=[])
    big["bids"] = [{"price": f"0.{i:05d}", "size": size} for i in range(1, 2_501)]
    big["asks"] = [{"price": f"0.{i:05d}", "size": size} for i in range(50_000, 52_500)]
    assert len(json.dumps(big)) < P.CLOB_MAX_BYTES
    # A book that cannot fit the bounded canonical record is an invalid public source.
    snapshot = snap(clob=body(big))
    assert snapshot.clob_source_state == "INVALID" and "BOOK_INVALID" in snapshot.diagnostic_codes


def test_r035_book_timestamp_normalization_and_freshness() -> None:
    snapshot = snap()
    assert snapshot.book_timestamp_ns == BOOK_MS * 1_000_000
    assert snap(clob=body(book_doc(timestamp=BOOK_MS))).book_timestamp_ns == BOOK_MS * 1_000_000
    future = assess(s=snap(clob=body(book_doc(timestamp=str(T0 // 1_000_000 + 1)))))
    assert future.freshness_dimension == "UNKNOWN" and future.status == "INCONCLUSIVE"
    assert "BOOK_TIMESTAMP_INVALID" in future.diagnostic_codes
    edge = intent(max_public_data_age_ns=1_000_000_000)
    assert assess(i=edge).freshness_dimension == "PASS"
    stale = assess(i=intent(max_public_data_age_ns=999_999_999))
    assert stale.freshness_dimension == "UNKNOWN" and "BOOK_STALE" in stale.diagnostic_codes
    assert stale.status == "INCONCLUSIVE" and stale.fill_dimension == "UNKNOWN"


# ---------------------------------------------------------------------------
# G. Market hard facts.
# ---------------------------------------------------------------------------


def test_r036_market_hard_facts_not_feasible() -> None:
    for field, value, code in (("active", False, "MARKET_INACTIVE"),
                               ("closed", True, "MARKET_CLOSED"),
                               ("acceptingOrders", False, "MARKET_NOT_ACCEPTING_ORDERS"),
                               ("enableOrderBook", False, "ORDER_BOOK_DISABLED")):
        result = assess(s=snap(gamma=body(gamma_doc(**{field: value}))))
        assert result.market_dimension == "FAIL" and result.status == "NOT_FEASIBLE"
        assert code in result.diagnostic_codes
    restricted = assess(s=snap(gamma=body(gamma_doc(restricted=True))))
    assert restricted.status == "FEASIBLE"  # recorded, not an access authorization


def test_r037_missing_market_state_inconclusive() -> None:
    for field in ("active", "closed", "acceptingOrders", "enableOrderBook"):
        result = assess(s=snap(gamma=body(gamma_doc(**{field: _DROP}))))
        assert result.market_dimension == "UNKNOWN" and result.status == "INCONCLUSIVE"
    nulls = assess(s=snap(gamma=body(gamma_doc(active=None))))
    assert nulls.market_dimension == "UNKNOWN"


# ---------------------------------------------------------------------------
# H. Tick / I. Minimum order.
# ---------------------------------------------------------------------------


def test_r038_tick_grid_uses_exact_decimal_modulo() -> None:
    cases = (("0.01", "0.55", "PASS"), ("0.01", "0.555", "FAIL"),
             ("0.005", "0.555", "PASS"), ("0.005", "0.5525", "FAIL"),
             ("0.0025", "0.5525", "PASS"), ("0.0025", "0.553", "FAIL"),
             ("0.001", "0.553", "PASS"), ("0.001", "0.5531", "FAIL"),
             ("0.0001", "0.5531", "PASS"), ("0.0001", "0.55315", "FAIL"))
    for tick, price, expected in cases:
        s = snap(gamma=body(gamma_doc(orderPriceMinTickSize=float(tick))),
                 clob=body(book_doc(tick_size=tick)))
        result = assess(i=intent(price_limit=price, order_type="FAK"), s=s)
        assert result.tick_dimension == expected, (tick, price)
        assert ("PRICE_OFF_TICK" in result.diagnostic_codes) == (expected == "FAIL")
        if expected == "FAIL":
            assert result.status == "NOT_FEASIBLE"


def test_r039_minimum_order_notional() -> None:
    # Gamma orderMinSize is a USDC notional: 10 shares * 0.5 = 5 USDC meets 5 exactly.
    exact = assess(i=intent(requested_shares="10", price_limit="0.5", order_type="FAK"))
    assert exact.minimum_order_dimension == "PASS"
    assert exact.intent_notional_at_price_limit_usd == "5"
    assert exact.minimum_order_notional_usd == "5"
    below = assess(i=intent(requested_shares="9.98", price_limit="0.5", order_type="FAK"))
    assert below.minimum_order_dimension == "FAIL" and below.status == "NOT_FEASIBLE"
    assert "MINIMUM_ORDER_NOTIONAL_NOT_MET" in below.diagnostic_codes
    missing = assess(s=snap(gamma=body(gamma_doc(orderMinSize=_DROP))))
    assert missing.minimum_order_dimension == "UNKNOWN" and missing.status == "INCONCLUSIVE"
    assert snap(gamma=body(gamma_doc(orderMinSize=_DROP))).book_min_order_size_raw == "5"


# ---------------------------------------------------------------------------
# S10-LIVE-ORCH-01 R001/NR013: independent Gamma-notional / CLOB-share minimum dimensions.
# ---------------------------------------------------------------------------

_MIN_DIAGS = ("MINIMUM_ORDER_NOTIONAL_NOT_MET", "MINIMUM_ORDER_SHARES_NOT_MET",
              "MIN_ORDER_SOURCE_CONFLICT")


def _min_case(*, shares: str, price: str, gamma_min, book_min):
    gamma = gamma_doc(orderMinSize=gamma_min)
    book = book_doc(min_order_size=book_min)
    result = assess(i=intent(requested_shares=shares, price_limit=price, order_type="FAK"),
                    s=snap(gamma=body(gamma), clob=body(book)))
    return result, tuple(code for code in result.diagnostic_codes if code in _MIN_DIAGS)


def test_live_orch_minimum_order_dimensions_are_independent() -> None:
    """R001: Gamma minimum is USDC notional and CLOB minimum is shares, never equated."""
    assert "MINIMUM_ORDER_SHARES_NOT_MET" in M.DIAGNOSTIC_CODES
    assert M.DIAGNOSTIC_CODES.index("MINIMUM_ORDER_NOTIONAL_NOT_MET") + 1 == \
        M.DIAGNOSTIC_CODES.index("MINIMUM_ORDER_SHARES_NOT_MET")
    # Unequal values (USD 1 notional vs 5 shares) both pass: 8 shares x 0.55 = 4.4 USD.
    both, diags = _min_case(shares="8", price="0.55", gamma_min=1, book_min="5")
    assert both.minimum_order_dimension == "PASS" and diags == ()
    assert both.minimum_order_notional_usd == "1"
    # Exactly at both boundaries passes.
    edge, diags = _min_case(shares="10", price="0.5", gamma_min=5, book_min="10")
    assert edge.minimum_order_dimension == "PASS" and diags == ()


def test_live_orch_minimum_order_each_failure_is_exact() -> None:
    """Below each constraint fails with exactly the corresponding closed diagnostic."""
    notional, diags = _min_case(shares="8", price="0.55", gamma_min=5, book_min="5")
    assert notional.minimum_order_dimension == "FAIL" and notional.status == "NOT_FEASIBLE"
    assert diags == ("MINIMUM_ORDER_NOTIONAL_NOT_MET",)
    shares, diags = _min_case(shares="8", price="0.55", gamma_min=1, book_min="10")
    assert shares.minimum_order_dimension == "FAIL" and shares.status == "NOT_FEASIBLE"
    assert diags == ("MINIMUM_ORDER_SHARES_NOT_MET",)
    both, diags = _min_case(shares="4", price="0.55", gamma_min=5, book_min="5")
    assert both.minimum_order_dimension == "FAIL"
    assert diags == ("MINIMUM_ORDER_NOTIONAL_NOT_MET", "MINIMUM_ORDER_SHARES_NOT_MET")


def test_live_orch_minimum_order_missing_source_unknown() -> None:
    """A missing Gamma or CLOB minimum leaves the dimension UNKNOWN, never PASS or FAIL."""
    for gamma_min, book_min in ((_DROP, "5"), (5, _DROP)):
        result, diags = _min_case(shares="8", price="0.55", gamma_min=gamma_min, book_min=book_min)
        assert result.minimum_order_dimension == "UNKNOWN" and result.status == "INCONCLUSIVE"
        assert diags == () and result.minimum_order_notional_usd is None


def test_live_orch_frozen_base_minimum_order_defect_negative_control() -> None:
    """R009: the frozen base 3f4d9ed contained the dimension-conflating equality branch."""
    base = "3f4d9ed91c0e96b9fc19389ac59e01f079caa3fe"
    old = subprocess.run(["git", "show", f"{base}:src/execution_feasibility/evaluator.py"],
                         cwd=ROOT, capture_output=True, text=True, timeout=60)
    if old.returncode != 0:
        pytest.skip("frozen base object unavailable in this checkout")
    assert "if gamma_min != book_min:" in old.stdout
    current = (ROOT / "src" / "execution_feasibility" / "evaluator.py").read_text(encoding="utf-8")
    assert "if gamma_min != book_min:" not in current
    assert "requested_shares < book_min" in current


# ---------------------------------------------------------------------------
# J/K. Aggressive taker.
# ---------------------------------------------------------------------------


def test_r040_aggressive_buy_sweep_metrics() -> None:
    result = assess(i=intent(requested_shares="25", price_limit="0.55"))
    assert result.status == "FEASIBLE"
    assert (result.best_bid, result.best_ask, result.spread) == ("0.5", "0.52", "0.02")
    assert result.visible_fill_shares == "25" and result.fill_ratio == "1"
    assert result.weighted_execution_price == "0.526"  # (10*0.52 + 15*0.53) / 25
    assert result.slippage_per_share == "0.006" and result.slippage_cost_usd == "0.15"
    assert result.visible_depth_capacity_shares == "100"
    assert result.price_bound_capacity_shares == "60"
    assert result.passive_fill_state == "NOT_APPLICABLE"


def test_r041_aggressive_buy_fok_fak_outcomes() -> None:
    fok = assess(i=intent(requested_shares="70", price_limit="0.55"))
    assert fok.fill_dimension == "FAIL" and fok.status == "NOT_FEASIBLE"
    assert "FOK_INSUFFICIENT_VISIBLE_DEPTH" in fok.diagnostic_codes
    assert fok.visible_fill_shares == "60"
    fak = assess(i=intent(requested_shares="70", price_limit="0.55", order_type="FAK"))
    assert fak.fill_dimension == "LIMITED" and fak.status == "LIMITED"
    assert "FAK_PARTIAL_VISIBLE_FILL" in fak.diagnostic_codes
    assert fak.fill_ratio == "0.857142857142857142"  # 60/70 floored at 18 dp
    no_asks = snap(clob=body(book_doc(asks=[])))
    for order_type in ("FOK", "FAK"):
        result = assess(i=intent(order_type=order_type), s=no_asks)
        assert result.status == "NOT_FEASIBLE"
        assert "NO_VISIBLE_OPPOSING_LIQUIDITY" in result.diagnostic_codes
        assert result.weighted_execution_price is None and result.slippage_cost_usd is None
    below_limit = assess(i=intent(price_limit="0.51", order_type="FAK"))
    assert below_limit.status == "NOT_FEASIBLE" and below_limit.visible_fill_shares == "0"


def test_r042_aggressive_sell_mirrors_over_bids() -> None:
    result = assess(i=intent(side="SELL", requested_shares="150", price_limit="0.49"))
    assert result.status == "FEASIBLE" and result.visible_fill_shares == "150"
    # (100*0.50 + 50*0.49)/150 = 0.496666... floored for SELL
    assert result.weighted_execution_price == "0.496666666666666666"
    assert result.slippage_per_share == "0.003333333333333334"
    assert result.visible_depth_capacity_shares == "300"
    assert result.price_bound_capacity_shares == "300"
    partial = assess(i=intent(side="SELL", requested_shares="150", price_limit="0.5",
                              order_type="FAK"))
    assert partial.status == "LIMITED" and partial.visible_fill_shares == "100"
    fok = assess(i=intent(side="SELL", requested_shares="150", price_limit="0.5"))
    assert fok.status == "NOT_FEASIBLE"


# ---------------------------------------------------------------------------
# L. Passive maker.
# ---------------------------------------------------------------------------


def test_r043_passive_maker_rest_and_cross() -> None:
    rest = assess(i=passive(price_limit="0.51"))
    assert rest.status == "FEASIBLE" and rest.fill_dimension == "PASS"
    assert (rest.passive_fill_state, rest.passive_fill_probability) == ("UNKNOWN", None)
    assert "PASSIVE_FILL_UNKNOWN" in rest.diagnostic_codes
    assert rest.visible_fill_shares is None and rest.delay_dimension == "NOT_APPLICABLE"
    for side, price in (("BUY", "0.52"), ("BUY", "0.53"), ("SELL", "0.5"), ("SELL", "0.49")):
        crossed = assess(i=passive(side=side, price_limit=price))
        assert crossed.status == "NOT_FEASIBLE" and crossed.fill_dimension == "FAIL"
        assert "POST_ONLY_WOULD_CROSS" in crossed.diagnostic_codes
    sell = assess(i=passive(side="SELL", price_limit="0.51"))
    assert sell.status == "FEASIBLE"
    no_asks = assess(i=passive(price_limit="0.9", requested_shares="10"),
                     s=snap(clob=body(book_doc(asks=[]))))
    assert no_asks.status == "FEASIBLE"
    gtd = passive(order_type="GTD", gtd_expiration_unix_s=CUTOFF // 1_000_000_000 + 600)
    assert assess(i=gtd).status == "FEASIBLE"


# ---------------------------------------------------------------------------
# M. Fees.
# ---------------------------------------------------------------------------


def test_r044_fee_disabled_and_passive_maker_exact_zero() -> None:
    disabled = assess(s=snap(gamma=body(gamma_doc(feesEnabled=False, feeSchedule=_DROP))))
    assert disabled.fee_exactness == "EXACT_ZERO_NO_FEES"
    assert (disabled.theoretical_fee_unrounded_usd, disabled.fee_upper_bound_usd) == ("0", "0")
    maker = assess(i=passive())
    assert maker.fee_exactness == "EXACT_ZERO_MAKER" and maker.fee_upper_bound_usd == "0"
    assert maker.maker_rebate_rate == "0.2" and maker.expected_maker_rebate_usd is None


def test_r045_taker_fee_per_level_with_conservative_ceiling() -> None:
    result = assess(i=intent(requested_shares="25", price_limit="0.55"))
    # 0.0333 * (10*0.52*0.48 + 15*0.53*0.47) = 0.20754225; the VWAP-only fee would differ.
    assert result.theoretical_fee_unrounded_usd == "0.20754225"
    vwap_only = 25 * 0.0333 * 0.526 * (1 - 0.526)
    assert abs(vwap_only - 0.20754225) > 1e-6
    assert result.fee_upper_bound_usd == "0.20755"
    assert result.fee_exactness == "CONSERVATIVE_5DP_UPPER_BOUND"
    squared = snap(gamma=body(gamma_doc(feeSchedule={"rate": 0.25, "exponent": 2,
                                                     "takerOnly": True})))
    two = assess(i=intent(requested_shares="10", price_limit="0.52"), s=squared)
    assert two.theoretical_fee_unrounded_usd == "0.1557504"  # 10 * 0.25 * (0.52*0.48)^2
    assert two.fee_upper_bound_usd == "0.15576"
    zero = snap(gamma=body(gamma_doc(feeSchedule={"rate": 0.01, "exponent": 0,
                                                  "takerOnly": True})))
    assert assess(i=intent(requested_shares="10", price_limit="0.52"),
                  s=zero).theoretical_fee_unrounded_usd == "0.1"


def test_r046_unknown_fee_configuration_is_inconclusive() -> None:
    for schedule, code in (({"rate": 0.02, "exponent": 9, "takerOnly": True},
                            "FEE_EXPONENT_UNSUPPORTED"),
                           ({"rate": 0.02, "exponent": 1.5, "takerOnly": True},
                            "FEE_EXPONENT_UNSUPPORTED"),
                           ({"rate": 0.02, "exponent": 1, "takerOnly": False},
                            "FEE_CONFIG_UNKNOWN"),
                           ({"rate": "x", "exponent": 1, "takerOnly": True},
                            "FEE_CONFIG_UNKNOWN"),
                           ("bad", "FEE_CONFIG_UNKNOWN"), (_DROP, "FEE_CONFIG_UNKNOWN")):
        result = assess(s=snap(gamma=body(gamma_doc(feeSchedule=schedule))))
        assert result.fee_dimension == "UNKNOWN" and result.status == "INCONCLUSIVE"
        assert result.fee_exactness == "UNKNOWN" and code in result.diagnostic_codes
        assert result.fee_upper_bound_usd is None
    unknown_enabled = assess(s=snap(gamma=body(gamma_doc(feesEnabled=_DROP))))
    assert unknown_enabled.status == "INCONCLUSIVE"
    maker_not_taker_only = assess(i=passive(), s=snap(gamma=body(gamma_doc(
        feeSchedule={"rate": 0.02, "exponent": 1, "takerOnly": False}))))
    assert maker_not_taker_only.fee_dimension == "UNKNOWN"
    assert maker_not_taker_only.status == "INCONCLUSIVE"


def test_r047_maker_rebate_never_becomes_expected_proceeds() -> None:
    for result in (assess(), assess(i=passive())):
        assert result.expected_maker_rebate_usd is None
    tampered = assess(i=passive()).to_mapping()
    tampered["expected_maker_rebate_usd"] = "0.01"
    assert code_of(record_from_mapping, "EXECUTION_FEASIBILITY_ASSESSMENT", tampered) == \
        "FIELD_VALUE_INVALID"


# ---------------------------------------------------------------------------
# N. Delay / latency, O. adverse selection.
# ---------------------------------------------------------------------------


def test_r048_marketable_order_delay() -> None:
    assert assess().delay_dimension == "PASS"
    delayed = assess(s=snap(gamma=body(gamma_doc(secondsDelay=3))))
    assert delayed.delay_dimension == "LIMITED" and delayed.status == "LIMITED"
    assert delayed.seconds_delay == 3 and "MARKETABLE_ORDER_DELAY" in delayed.diagnostic_codes
    missing = assess(s=snap(gamma=body(gamma_doc(secondsDelay=_DROP))))
    assert missing.delay_dimension == "UNKNOWN" and missing.status == "INCONCLUSIVE"
    passive_delayed = assess(i=passive(), s=snap(gamma=body(gamma_doc(secondsDelay=3))))
    assert passive_delayed.delay_dimension == "NOT_APPLICABLE"
    assert passive_delayed.status == "FEASIBLE"


def test_r049_client_latency_unknown_and_http_duration_not_promoted() -> None:
    slow = fetch_public_venue_snapshot(gamma_market_id=GAMMA_ID, condition_id=COND,
                                       token_id=TOKEN, opener=ok_opener(),
                                       clock_ns=clock(T0 - 4_000_000_000, T0))
    for result in (assess(s=slow), assess(i=passive(), s=slow)):
        assert (result.client_latency_state, result.client_latency_ns) == ("UNKNOWN", None)
        assert "CLIENT_LATENCY_UNKNOWN" in result.diagnostic_codes
    fast = fetch(ok_opener())
    assert assess(s=fast).identity_preimage().keys() == assess(s=slow).identity_preimage().keys()
    assert assess(s=fast).client_latency_ns is None


def test_r050_adverse_selection_unknown_never_zero() -> None:
    for result in (assess(), assess(i=passive()),
                   assess(s=snap(gamma=UNAVAILABLE, clob=UNAVAILABLE))):
        assert result.adverse_selection_state == "UNKNOWN"
        assert result.adverse_selection_cost is None
        assert "ADVERSE_SELECTION_UNKNOWN" in result.diagnostic_codes
    tampered = assess().to_mapping()
    tampered["adverse_selection_cost"] = "0"
    assert code_of(record_from_mapping, "EXECUTION_FEASIBILITY_ASSESSMENT", tampered) == \
        "FIELD_VALUE_INVALID"


# ---------------------------------------------------------------------------
# P. Status precedence.
# ---------------------------------------------------------------------------


def test_r051_status_precedence() -> None:
    closed_missing_fee = assess(s=snap(gamma=body(gamma_doc(closed=True, feeSchedule=_DROP))))
    assert closed_missing_fee.status == "NOT_FEASIBLE"
    assert closed_missing_fee.fee_dimension == "UNKNOWN"
    fak = intent(requested_shares="70", order_type="FAK")
    partial_missing_fee = assess(i=fak, s=snap(gamma=body(gamma_doc(feeSchedule=_DROP))))
    assert partial_missing_fee.fill_dimension == "LIMITED"
    assert partial_missing_fee.status == "INCONCLUSIVE"
    assert assess(i=fak).status == "LIMITED"
    assert assess().status == "FEASIBLE"
    assert M.derive_status({name: "PASS" for name in M.DIMENSIONS}) == "FEASIBLE"
    assert M.derive_status({**{n: "LIMITED" for n in M.DIMENSIONS}, "fee_dimension": "UNKNOWN",
                            "tick_dimension": "FAIL"}) == "NOT_FEASIBLE"
    both = assess(s=snap(gamma=UNAVAILABLE, clob=UNAVAILABLE))
    assert both.status == "INCONCLUSIVE"
    assert all(getattr(both, name) == "UNKNOWN" for name in M.DIMENSIONS)
    order = [M.DIAGNOSTIC_CODES.index(code) for code in closed_missing_fee.diagnostic_codes]
    assert order == sorted(order)


# ---------------------------------------------------------------------------
# Q. Identity tampering, round trips and re-evaluation.
# ---------------------------------------------------------------------------


def _tamper_matrix(record, kind: str, field: str, value) -> None:
    mapping = record.to_mapping()
    assert record_from_mapping(kind, mapping) == record
    id_field = type(record).ID_FIELD
    prefix = type(record).ID_PREFIX
    forged = dict(mapping, **{id_field: prefix + "0" * 64})
    assert code_of(record_from_mapping, kind, forged) == "IDENTITY_DERIVATION_MISMATCH"
    wrong_prefix = dict(mapping, **{id_field: "other:sha256:" + mapping[id_field][-64:]})
    assert code_of(record_from_mapping, kind, wrong_prefix) == "FIELD_VALUE_INVALID"
    changed = dict(mapping, **{field: value})
    assert code_of(record_from_mapping, kind, changed) == "IDENTITY_DERIVATION_MISMATCH"
    dropped = dict(mapping)
    dropped.pop(field)
    assert code_of(record_from_mapping, kind, dropped) == "FIELD_MISSING"
    assert code_of(record_from_mapping, kind, dict(mapping, extra=1)) == "FIELD_VALUE_INVALID"
    for flag in type(record).INVARIANT_TRUE_FIELDS:
        assert code_of(record_from_mapping, kind, dict(mapping, **{flag: False})) == \
            "FIELD_VALUE_INVALID"
    raw = json.dumps(record.identity_preimage(), sort_keys=True, separators=(",", ":"),
                     ensure_ascii=False).encode("utf-8")
    assert record.record_id == prefix + hashlib.sha256(raw).hexdigest()


def test_r052_execution_intent_identity_tamper_matrix() -> None:
    _tamper_matrix(intent(), "EXECUTION_INTENT", "requested_shares", "26")
    assert intent() == intent()


def test_r053_venue_snapshot_identity_tamper_matrix() -> None:
    _tamper_matrix(snap(), "PUBLIC_EXECUTION_VENUE_SNAPSHOT", "book_hash", "b" * 40)
    assert validate_public_venue_snapshot(snap()) == snap()


def test_r054_assessment_identity_tamper_matrix() -> None:
    _tamper_matrix(assess(), "EXECUTION_FEASIBILITY_ASSESSMENT", "evaluated_at_ns", T0 + 1)
    mapping = assess().to_mapping()
    assert code_of(record_from_mapping, "EXECUTION_FEASIBILITY_ASSESSMENT",
                   dict(mapping, status="LIMITED")) == "FIELD_VALUE_INVALID"
    assert code_of(record_from_mapping, "UNKNOWN_KIND", mapping) == "SCHEMA_UNSUPPORTED"
    assert code_of(record_from_mapping, "EXECUTION_FEASIBILITY_ASSESSMENT",
                   dict(mapping, schema_version="2.0.0")) == "SCHEMA_UNSUPPORTED"


def test_r055_evaluation_time_and_type_binding() -> None:
    assert code_of(assess, at=T0 - 1) == "FIELD_VALUE_INVALID"
    assert code_of(assess, at=True) == "FIELD_TYPE_INVALID"
    assert assess(at=T0 + 5).evaluated_at_ns == T0 + 5
    assert code_of(assess_execution_feasibility, intent().to_mapping(), snap(),
                   evaluated_at_ns=T0) == "FIELD_TYPE_INVALID"
    assert code_of(assess_execution_feasibility, intent(), snap().to_mapping(),
                   evaluated_at_ns=T0) == "FIELD_TYPE_INVALID"


def test_r056_assessment_revalidates_against_exact_inputs() -> None:
    i, s = intent(), snap()
    result = assess(i, s)
    assert assess(i, s) == result  # deterministic
    assert validate_execution_feasibility_assessment(result, intent=i, venue_snapshot=s) is result
    other_snapshot = snap(gamma=body(gamma_doc(secondsDelay=2)))
    assert code_of(validate_execution_feasibility_assessment, result, intent=i,
                   venue_snapshot=other_snapshot) == "IDENTITY_DERIVATION_MISMATCH"
    assert code_of(validate_execution_feasibility_assessment, result, intent=i) == "FIELD_MISSING"
    assert result.execution_intent_id == i.execution_intent_id
    assert result.venue_snapshot_id == s.venue_snapshot_id
    assert result.strategy_version_id == SV.strategy_version_id


def test_r057_canonical_serialization_and_bounds() -> None:
    assert M.canonical_json_text({"b": 1, "a": "é"}) == '{"a":"é","b":1}'
    for bad in (1.5, float("nan"), {1: "x"}, object()):
        assert code_of(M.canonical_json_text, bad) in {"FIELD_TYPE_INVALID",
                                                       "FIELD_VALUE_INVALID"}
    nested: object = "x"
    for _ in range(13):
        nested = [nested]
    assert code_of(M.canonical_json_text, nested) == "LIMIT_EXCEEDED"
    from decimal import Decimal
    assert [M.decimal_text(Decimal(v)) for v in ("0.500", "-0", "1E+2", "1E-7", "00.10")] == \
        ["0.5", "0", "100", "0.0000001", "0.1"]
    mapping = snap().to_mapping()
    assert all(not isinstance(v, float) for v in mapping.values())
    assert len(M.canonical_json_bytes(assess().to_mapping())) < M.MAX_RECORD_BYTES
    assert M.order_diagnostics(["BOOK_STALE", "SOURCE_GAMMA_UNAVAILABLE", "BOOK_STALE"]) == \
        ("SOURCE_GAMMA_UNAVAILABLE", "BOOK_STALE")
    assert code_of(M.order_diagnostics, ["upstream text"]) == "FIELD_VALUE_INVALID"


def test_r058_spec_identity_derivation_examples_are_product_records() -> None:
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    rules = {rule["rule_id"]: rule for rule in spec["identity_derivations"]["items"]}
    assert spec["identity_derivations"]["applicable"] is True
    assert {rule["target_path"] for rule in rules.values()} == {
        "execution_intent_id", "venue_snapshot_id", "execution_feasibility_assessment_id"}
    kinds = {"polymarket-execution-intent": "EXECUTION_INTENT",
             "polymarket-public-execution-venue-snapshot": "PUBLIC_EXECUTION_VENUE_SNAPSHOT",
             "polymarket-execution-feasibility-assessment": "EXECUTION_FEASIBILITY_ASSESSMENT"}
    sys.path.insert(0, str(ROOT))
    from tools.wp import wp_spec_guard as guard  # read-only use of the unchanged guard
    seen = set()
    for example in spec["examples"]["items"]:
        record = record_from_mapping(kinds[example["input"]["schema_id"]], example["input"])
        (rule_id,) = example["derivation_rule_ids"]
        rule = rules[rule_id]
        assert sorted(rule["source_paths"]) == sorted(record.identity_preimage())
        assert rule["excluded_paths"] == []
        target = rule["target_path"]
        assert guard._canonical_derived_value(rule, example["input"]) == example["input"][target]
        modified = dict(example["input"])
        first = rule["source_paths"][0]
        modified[first] = "tampered"
        assert guard._canonical_derived_value(rule, modified) != example["input"][target]
        dropped = dict(example["input"])
        dropped.pop(first)
        with pytest.raises(KeyError):
            guard._canonical_derived_value(rule, dropped)
        seen.add(target)
    assert len(seen) == 3


def test_r059_scope_is_exact_and_excludes_forbidden_surfaces() -> None:
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    scope = spec["scope"]
    assert scope["required_changed_files"] == scope["allowed_changed_files"]
    assert len(scope["required_changed_files"]) == scope["max_changed_files"] == 17
    for path in scope["required_changed_files"]:
        for forbidden in ("src/strategy_lifecycle/", "src/execution_gateway/", "src/paper_trading/",
                          "src/research_runtime/", "src/data_layer/", "tools/", ".github/",
                          "local_data/", "pyproject.toml", "requirements"):
            assert not path.startswith(forbidden), path
        assert "data03" not in path.lower() and "data_03" not in path.lower()
    authority = spec["authority"]
    assert authority["network"] is True and authority["source_runtime"] is True
    assert authority["strategy"] is True
    for key in ("execution", "live", "credentials", "paper", "scheduler", "dependencies",
                "workflow_files", "hermes_runtime"):
        assert authority[key] is False, key


def test_r060_no_wp172_semantics_reused_or_weakened() -> None:
    text = source_text()
    assert "EXECUTABLE_EDGE_PASS" not in text and "executable_edge" not in text
    assert "queue_multiplier" not in text and "profit" not in text.lower().replace(
        "no profitability claim", "").replace("profitability", "")
    for name in ("expected_value", "net_edge", "gross_edge", "pnl", "sharpe", "roi"):
        assert name not in {f.lower() for f in ExecutionFeasibilityAssessment.__dataclass_fields__}
    assert set(M.EXECUTION_FEASIBILITY_STATUSES) == {"FEASIBLE", "LIMITED", "INCONCLUSIVE",
                                                     "NOT_FEASIBLE"}


# ---------------------------------------------------------------------------
# Final Contract Micro-Closure 01 (Side15): B1 endpoint shapes, B2 fee truthfulness.
# ---------------------------------------------------------------------------


def test_r069_only_two_exact_endpoint_shapes_pass_transport_guard() -> None:
    gamma = "https://gamma-api.polymarket.com"
    clob = "https://clob.polymarket.com"
    forbidden = (
        f"{clob}/order", f"{clob}/auth/api-key", f"{clob}/book", f"{clob}/book?",
        f"{clob}/book?token_id={TOKEN}&extra=1", f"{clob}/book?token_id={TOKEN}&token_id=1",
        f"{clob}/book?extra=1&token_id={TOKEN}", f"{clob}/book?token_id=", f"{clob}/book?token_id=+1",
        f"{clob}/book?token_id=%31", f"{clob}/book?token_id=abc", f"{clob}/book?token_id={'1' * 101}",
        f"{clob}/book/?token_id={TOKEN}", f"{clob}/book?token_id={TOKEN}#frag",
        f"{clob}/markets/{GAMMA_ID}", f"{gamma}/markets", f"{gamma}/markets/",
        f"{gamma}/markets/{GAMMA_ID}?extra=1", f"{gamma}/markets/{GAMMA_ID}?",
        f"{gamma}/markets/{GAMMA_ID}#frag", f"{gamma}/markets/{GAMMA_ID}/x", f"{gamma}/markets/abc",
        f"{gamma}/markets/-1", f"{gamma}/markets/{'1' * 33}", f"{gamma}/anything",
        f"{gamma}/book?token_id={TOKEN}", f"https://GAMMA-API.polymarket.com/markets/{GAMMA_ID}",
        f"https://gamma-api.polymarket.com:8443/markets/{GAMMA_ID}",
        f"https://u:p@clob.polymarket.com/book?token_id={TOKEN}",
    )
    opener = FakeOpener()
    for url in forbidden:
        assert code_of(P.public_get, url, max_bytes=10, opener=opener) == "NETWORK_HOST_FORBIDDEN", url
    assert opener.requests == []
    for url in (P.gamma_market_url(GAMMA_ID), P.clob_book_url(TOKEN),
                f"https://gamma-api.polymarket.com:443/markets/{GAMMA_ID}",
                f"https://clob.polymarket.com:443/book?token_id={TOKEN}"):
        ok = FakeOpener(FakeResponse(payload=b"{}"))
        assert P.public_get(url, max_bytes=10, opener=ok).outcome == "BODY", url
        assert len(ok.requests) == 1
    assert fetch(ok_opener()).clob_source_state == "AVAILABLE"


def test_r070_taker_fee_unknown_without_usable_fills() -> None:
    for snapshot in (snap(clob=UNAVAILABLE), snap(clob=body(book_doc(asks=[("0.5", "1")])))):
        result = assess(s=snapshot)
        assert (result.fee_dimension, result.fee_exactness) == ("UNKNOWN", "UNKNOWN")
        assert result.theoretical_fee_unrounded_usd is None and result.fee_upper_bound_usd is None
        assert result.status == "INCONCLUSIVE"
    stale = assess(i=intent(max_public_data_age_ns=999_999_999))
    assert stale.freshness_dimension == "UNKNOWN" and stale.fee_dimension == "UNKNOWN"
    assert stale.fee_upper_bound_usd is None
    usable = assess()
    assert usable.fee_dimension == "PASS" and usable.fee_upper_bound_usd == "0.20755"
    no_fees = assess(s=snap(gamma=body(gamma_doc(feesEnabled=False, feeSchedule=_DROP)), clob=UNAVAILABLE))
    assert (no_fees.fee_dimension, no_fees.fee_exactness, no_fees.fee_upper_bound_usd) == (
        "PASS", "EXACT_ZERO_NO_FEES", "0")
    # A known usable book with zero visible fill keeps a deterministic zero executed fee.
    zero_fill = assess(i=intent(price_limit="0.51", order_type="FAK"))
    assert zero_fill.status == "NOT_FEASIBLE" and zero_fill.fee_dimension == "PASS"
    assert zero_fill.theoretical_fee_unrounded_usd == "0" and zero_fill.fee_upper_bound_usd == "0"
