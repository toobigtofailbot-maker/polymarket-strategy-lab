"""WP169 focused tests: public GET client allowlists, retry, bounds, and query domains."""

from __future__ import annotations

import json

import pytest


from src.data_layer.polymarket import market_truth as mt
from src.data_layer.polymarket.market_truth_data_api import (
    NetworkBudgetExhausted,
    PublicMarketDataClient,
    RateLimiter,
    _http_checkpoint_key,
    _normalize_params,
    collect_public_page,
)
from src.data_layer.polymarket.market_truth_store import MarketTruthStore

CONDITION = "0x" + "a" * 64
WALLET = "0x" + "b" * 40


def _clock():
    state = {"i": 0}

    def tick():
        state["i"] += 1
        return f"2024-07-03T10:00:{state['i'] % 60:02d}.000000Z"

    return tick


def _trade_body():
    return json.dumps([
        {"conditionId": CONDITION, "price": "0.5", "size": "2", "side": "BUY",
         "transactionHash": "0x" + "c" * 64, "timestamp": 1720000000}
    ]).encode()


def test_public_client_enforces_allowlist_pagination_retry_and_bounds() -> None:
    clock = _clock()

    class Transport:
        def __init__(self):
            self.calls = 0

        def __call__(self, url, headers, timeout):
            self.calls += 1
            # No credential/auth header is ever supplied by the client.
            assert "Authorization" not in headers
            if self.calls == 1:
                return (429, {"Retry-After": "0"}, b"{}")
            return (200, {}, _trade_body())

    client = PublicMarketDataClient(transport=Transport(), clock=clock)
    result = client.get_page("trades", {"limit": 100, "market": CONDITION})
    assert result.status == "OK"
    # Every attempt (including the retryable error body) is retained as raw evidence.
    assert len(result.attempts) == 2 and result.successful_attempt_index == 1

    # Invalid Retry-After fails closed with RETRY_AFTER_INVALID.
    class BadRetry:
        def __call__(self, url, headers, timeout):
            return (503, {"Retry-After": "abc"}, b"{}")

    bad = PublicMarketDataClient(transport=BadRetry(), clock=clock).get_page("trades", {"limit": 5})
    assert bad.status == "FAILED" and bad.error_codes == ("RETRY_AFTER_INVALID",)

    # Oversize response fails closed with RESPONSE_TOO_LARGE.
    class Huge:
        def __call__(self, url, headers, timeout):
            return (200, {}, b"x" * (5 * 1024 * 1024))

    huge = PublicMarketDataClient(
        mt.AcquisitionLimits(max_response_bytes=1024), transport=Huge(), clock=clock
    ).get_page("trades", {"limit": 5})
    assert huge.status == "FAILED" and huge.error_codes == ("RESPONSE_TOO_LARGE",)

    # A non-retryable 4xx does not retry.
    class Forbidden:
        def __init__(self):
            self.calls = 0

        def __call__(self, url, headers, timeout):
            self.calls += 1
            return (404, {}, b"{}")

    forbidden = Forbidden()
    resp = PublicMarketDataClient(transport=forbidden, clock=clock).get_page("trades", {"limit": 5})
    assert resp.status == "FAILED" and forbidden.calls == 1

    # No-echo: failed results carry no URL/host/body.
    assert mt.scan_no_echo({"status": bad.status, "error_codes": list(bad.error_codes)})


def test_asset_and_endpoint_query_domains_are_bounded() -> None:
    # Unknown / inapplicable keys fail closed with ENDPOINT_FORBIDDEN.
    with pytest.raises(mt.MarketTruthError) as excinfo:
        _normalize_params("trades", {"bogus": "1"})
    assert excinfo.value.code == "ENDPOINT_FORBIDDEN"
    with pytest.raises(mt.MarketTruthError):
        _normalize_params("book", {"token_id": "7", "offset": 0})

    # Client policy is stricter than provider: limit >= 1.
    with pytest.raises(mt.MarketTruthError) as excinfo:
        _normalize_params("trades", {"limit": 0})
    assert excinfo.value.code == "INPUT_INVALID"

    # market and eventId are mutually exclusive.
    with pytest.raises(mt.MarketTruthError):
        _normalize_params("trades", {"market": CONDITION, "eventId": "5"})

    # Required keys: activity/positions need user; holders needs market.
    with pytest.raises(mt.MarketTruthError):
        _normalize_params("activity", {"limit": 10})
    with pytest.raises(mt.MarketTruthError):
        _normalize_params("holders", {"limit": 5})

    # DEPOSIT/WITHDRAWAL activity type requires excludeDepositsWithdrawals=false.
    with pytest.raises(mt.MarketTruthError):
        _normalize_params("activity", {"limit": 10, "user": WALLET, "type": "DEPOSIT"})
    ok = _normalize_params(
        "activity", {"limit": 10, "user": WALLET, "type": "DEPOSIT", "excludeDepositsWithdrawals": False}
    )
    assert ok["excludeDepositsWithdrawals"] == "false"

    # Endpoint-specific value domains: holders limit 1..20.
    with pytest.raises(mt.MarketTruthError):
        _normalize_params("holders", {"limit": 21, "market": CONDITION})
    valid = _normalize_params("holders", {"limit": 20, "market": CONDITION})
    assert valid["limit"] == "20"

    # Offset bounds per endpoint (activity offset max 5000).
    with pytest.raises(mt.MarketTruthError):
        _normalize_params("activity", {"limit": 10, "user": WALLET, "offset": 5001})

    # Asset-id domain is validated for the reusable book/WS API.
    with pytest.raises(mt.MarketTruthError):
        mt.validate_asset_ids(["07"])  # leading zero
    assert mt.validate_asset_ids(["0", "7", "123"]) == ("0", "7", "123")


def test_collect_public_page_archives_before_normalizing(tmp_path) -> None:
    clock = _clock()

    class Transport:
        def __init__(self):
            self.calls = 0

        def __call__(self, url, headers, timeout):
            self.calls += 1
            if self.calls == 1:
                return (429, {"Retry-After": "0"}, b"{}")
            return (200, {}, _trade_body())

    with MarketTruthStore(tmp_path / "wp169_data.sqlite3") as store:
        receipt = collect_public_page(
            PublicMarketDataClient(transport=Transport(), clock=clock),
            store, "trades", {"limit": 100, "market": CONDITION}, max_pages=1,
        )
        assert receipt.status == "OK"
        # Both the retryable error body and the success body are archived; one record normalizes.
        assert receipt.raw_count >= 2 and receipt.normalized_count == 1


def test_retry_after_and_backoff_delays_are_applied_exactly() -> None:
    """D: get_page actually waits the certified Retry-After / exponential backoff."""
    clock = _clock()

    class RetryAfter:
        def __init__(self):
            self.n = 0

        def __call__(self, url, headers, timeout):
            self.n += 1
            if self.n <= 2:
                return (503, {"Retry-After": "7"}, b"{}")
            return (200, {}, _trade_body())

    slept: list[float] = []
    client = PublicMarketDataClient(transport=RetryAfter(), clock=clock)
    client._sleeper = lambda d: slept.append(d)  # private test seam
    result = client.get_page("trades", {"limit": 100, "market": CONDITION})
    assert result.status == "OK"
    assert client.retry_delays == [7.0, 7.0] and slept == [7.0, 7.0]

    # Without Retry-After: deterministic exponential backoff 1,2,4.
    class Retryable:
        def __call__(self, url, headers, timeout):
            return (502, {}, b"{}")

    slept2: list[float] = []
    retry_client = PublicMarketDataClient(transport=Retryable(), clock=clock)
    retry_client._sleeper = lambda d: slept2.append(d)  # private test seam
    exhausted = retry_client.get_page("trades", {"limit": 5})
    assert exhausted.status == "FAILED" and exhausted.error_codes == ("RETRY_EXHAUSTED",)
    assert slept2 == [1.0, 2.0, 4.0]


def test_rate_limiter_enforces_caps_and_shared_budget() -> None:
    """D: the monotonic token bucket delays when a per-source cap is hit and refuses
    once the shared network budget is exhausted."""
    rl_slept: list[float] = []
    now = {"t": 0.0}
    limiter = RateLimiter(
        mt.AcquisitionLimits(data_calls_per_10_seconds=2),
        monotonic=lambda: now["t"],
        sleeper=lambda d: (rl_slept.append(d), now.__setitem__("t", now["t"] + d)),
    )
    limiter.acquire("DATA")
    limiter.acquire("DATA")
    delay = limiter.acquire("DATA")  # third within the 10s window -> delay 10s then grant
    assert delay == 10.0 and rl_slept == [10.0]

    budget = RateLimiter(
        mt.AcquisitionLimits(max_network_calls=1), monotonic=lambda: 0.0, sleeper=lambda d: None
    )
    budget.acquire("DATA")
    # Budget exhaustion is a graceful terminal signal (NetworkBudgetExhausted), which the
    # runtime maps to STOPPED / NETWORK_CALL_LIMIT -- never a NETWORK_TIMEOUT failure.
    with pytest.raises(NetworkBudgetExhausted):
        budget.acquire("DATA")


def test_rate_limiter_rechecks_cap_after_partial_sleep() -> None:
    """SEED02: the per-source cap is re-checked under the lock after EVERY sleep. A sleeper
    that advances the clock by less than the requested delay must cause another wait rather
    than an over-cap grant (the old code granted after exactly one sleep)."""
    slept: list[float] = []
    now = {"t": 0.0}

    def sleeper(d: float) -> None:
        slept.append(d)
        now["t"] += 3.0  # partial advance: less than the requested delay

    limiter = RateLimiter(
        mt.AcquisitionLimits(data_calls_per_10_seconds=1),
        monotonic=lambda: now["t"], sleeper=sleeper,
    )
    limiter.acquire("DATA")  # t=0 grant; window holds one stamp until t>=10
    now["t"] = 1.0
    limiter.acquire("DATA")  # must not grant until the 10s window genuinely clears
    assert now["t"] >= 10.0  # granted only after the window cleared
    assert len(slept) >= 2  # re-checked and waited again (old code slept exactly once)


def test_shared_budget_spans_source_kinds() -> None:
    """F6: the single foreground network-call budget is shared across ALL source kinds,
    not per-source; two different-source acquires exhaust a budget of two."""
    limiter = RateLimiter(mt.AcquisitionLimits(max_network_calls=2))
    limiter.acquire("DATA")
    limiter.acquire("POLYGON")
    with pytest.raises(NetworkBudgetExhausted):
        limiter.acquire("GAMMA")
    assert limiter.network_calls == 2


def test_activity_side_validated_and_preserved() -> None:
    """SEED18: /activity accepts side=BUY/SELL; it is preserved in the canonical query and
    an invalid side fails closed (never silently dropped)."""
    ok = _normalize_params("activity", {"limit": 10, "user": WALLET, "side": "SELL"})
    assert ok["side"] == "SELL"
    with pytest.raises(mt.MarketTruthError):
        _normalize_params("activity", {"limit": 10, "user": WALLET, "side": "MAYBE"})


def test_collect_public_page_rejects_nonzero_caller_offset(tmp_path) -> None:
    """SEED19: collect_public_page manages paged offsets via checkpoints; a nonzero caller
    offset must fail closed rather than be silently ignored. offset=0 or omitted is OK."""
    class Transport:
        def __call__(self, url, headers, timeout):
            return (200, {}, _trade_body())

    with MarketTruthStore(tmp_path / "wp169_offset.sqlite3") as store:
        client = PublicMarketDataClient(transport=Transport(), clock=_clock())
        bad = collect_public_page(
            client, store, "trades", {"limit": 10, "market": CONDITION, "offset": 50}
        )
        assert bad.status == "FAILED" and bad.error_codes == ("INPUT_INVALID",)
        ok = collect_public_page(
            client, store, "trades", {"limit": 10, "market": CONDITION, "offset": 0}
        )
        assert ok.status == "OK"


def test_raw_archive_store_failure_is_terminal(tmp_path) -> None:
    """SEED14 / Reviewer C F3: an intermediate retry-attempt raw whose archival fails
    (store byte exhaustion) is terminal and visible -- the page does not silently continue
    and return OK with the retry-body evidence dropped."""
    class Transport:
        def __init__(self):
            self.n = 0

        def __call__(self, url, headers, timeout):
            self.n += 1
            if self.n == 1:
                return (503, {"Retry-After": "0"}, b'{"blob":"' + b"x" * 4000 + b'"}')
            return (200, {}, _trade_body())

    limits = mt.AcquisitionLimits(max_store_bytes=1000)
    with MarketTruthStore(tmp_path / "wp169_rawfail.sqlite3", limits) as store:
        client = PublicMarketDataClient(limits, transport=Transport(), clock=_clock())
        receipt = collect_public_page(
            client, store, "trades", {"limit": 100, "market": CONDITION}, max_pages=1
        )
    assert receipt.status == "FAILED" and receipt.error_codes == ("STORE_LIMIT_EXCEEDED",)


def test_shared_budget_is_thread_safe_and_terminates_stopped(tmp_path) -> None:
    """#3: the shared budget is concurrency-safe (never over-grants) and its exhaustion
    surfaces through collect_public_page as STOPPED / NETWORK_CALL_LIMIT, not FAILED."""
    import threading

    limiter = RateLimiter(mt.AcquisitionLimits(max_network_calls=50))
    granted = {"n": 0}
    granted_lock = threading.Lock()

    def worker():
        for _ in range(40):
            try:
                limiter.acquire("DATA")
                with granted_lock:
                    granted["n"] += 1
            except NetworkBudgetExhausted:
                return

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    # Exactly the budget is granted across all threads -- never more (no over-grant).
    assert granted["n"] == 50 and limiter.network_calls == 50

    # collect_public_page maps budget exhaustion to a graceful STOPPED terminal.
    exhausted = RateLimiter(mt.AcquisitionLimits(max_network_calls=1))
    exhausted.acquire("DATA")  # spend the budget

    class Transport:
        def __call__(self, url, headers, timeout):
            return (200, {}, _trade_body())

    client = PublicMarketDataClient(transport=Transport(), clock=_clock())
    client._rate_limiter = exhausted  # private shared-budget test seam
    with MarketTruthStore(tmp_path / "wp169_budget.sqlite3") as store:
        receipt = collect_public_page(client, store, "trades", {"limit": 100, "market": CONDITION}, max_pages=1)
    assert receipt.status == "STOPPED" and receipt.stop_reason == "NETWORK_CALL_LIMIT"


def test_page_and_record_bounds_fail_closed_before_normalization(tmp_path) -> None:
    """H: over-limit record counts and oversize records fail the page closed with only
    the raw envelope plus one quarantined observation (no partial children)."""
    clock = _clock()

    class OverCount:
        def __call__(self, url, headers, timeout):
            records = [
                {"conditionId": CONDITION, "price": "0.5", "size": "1", "side": "BUY",
                 "transactionHash": "0x" + "c" * 64, "timestamp": 1720000000}
                for _ in range(3)
            ]
            return (200, {}, json.dumps(records).encode())

    with MarketTruthStore(tmp_path / "wp169_over_count.sqlite3") as store:
        receipt = collect_public_page(
            PublicMarketDataClient(transport=OverCount(), clock=clock),
            store, "trades", {"limit": 2, "market": CONDITION}, max_pages=1,
        )
        assert receipt.status == "FAILED" and receipt.error_codes == ("RESPONSE_INVALID",)
        assert receipt.raw_count == 1 and receipt.normalized_count == 0 and receipt.quarantined_count == 1

    class OverBytes:
        def __call__(self, url, headers, timeout):
            return (200, {}, json.dumps([{"conditionId": CONDITION, "blob": "x" * 300000, "timestamp": 1720000000}]).encode())

    with MarketTruthStore(tmp_path / "wp169_over_bytes.sqlite3") as store:
        receipt = collect_public_page(
            PublicMarketDataClient(transport=OverBytes(), clock=clock),
            store, "trades", {"limit": 100, "market": CONDITION}, max_pages=1,
        )
        assert receipt.status == "FAILED" and receipt.error_codes == ("RESPONSE_TOO_LARGE",)
        assert receipt.raw_count == 1 and receipt.quarantined_count == 1


def test_get_page_never_emits_network_call_limit_error_code() -> None:
    """Item 15: NETWORK_CALL_LIMIT is a stop reason, not a closed error code; get_page
    raises the private NetworkBudgetExhausted instead of emitting it, and every emitted
    PublicPageResult error code belongs to the frozen error vocabulary."""
    assert "NETWORK_CALL_LIMIT" not in mt.ERROR_PRECEDENCE

    class Ok:
        def __call__(self, url, headers, timeout):
            return (200, {}, _trade_body())

    exhausted = RateLimiter(mt.AcquisitionLimits(max_network_calls=1))
    exhausted.acquire("DATA")  # spend the budget
    client = PublicMarketDataClient(transport=Ok(), clock=_clock())
    client._rate_limiter = exhausted
    with pytest.raises(NetworkBudgetExhausted):
        client.get_page("trades", {"limit": 10, "market": CONDITION})

    # Error-producing results only ever carry frozen error codes.
    for status in (404, 503):
        class T:
            def __init__(self, s):
                self.s = s

            def __call__(self, url, headers, timeout):
                return (self.s, {"Retry-After": "abc"} if self.s == 503 else {}, b"{}")

        r = PublicMarketDataClient(transport=T(status), clock=_clock()).get_page("trades", {"limit": 5})
        assert r.status == "FAILED"
        assert all(code in mt.ERROR_PRECEDENCE for code in r.error_codes), r.error_codes


def test_canonical_decimal_query_identity() -> None:
    """Item 16: filterAmount/sizeThreshold are canonicalized so equivalent spellings share
    one query/checkpoint identity; exponent/negative/negative-zero fail closed."""
    variants = [
        _normalize_params("trades", {"limit": 10, "filterType": "CASH", "filterAmount": spelling})["filterAmount"]
        for spelling in ("1", "01", "1.0", "1.00")
    ]
    assert variants == ["1", "1", "1", "1"], variants
    for bad in ("-1", "1e5", "-0", "1.", "abc", "0x1"):
        with pytest.raises(mt.MarketTruthError):
            _normalize_params("trades", {"limit": 10, "filterType": "CASH", "filterAmount": bad})
    p = _normalize_params("positions", {"limit": 10, "user": WALLET, "sizeThreshold": "2.50"})
    assert p["sizeThreshold"] == "2.5"


def test_shared_stop_halts_multipage_http(tmp_path) -> None:
    """Item 11: an in-flight bounded request (page 1) finishes, but page 2 must not begin once
    the shared stop is set. collect_public_page threads the shared stop to every page."""
    import asyncio

    stop = asyncio.Event()
    calls = {"n": 0}

    class Transport:
        def __call__(self, url, headers, timeout):
            calls["n"] += 1
            stop.set()  # after the page-1 request, the shared stop fires
            records = [
                {"conditionId": CONDITION, "price": "0.5", "size": "1", "side": "BUY",
                 "transactionHash": "0x" + "c" * 64, "timestamp": 1720000000}
                for _ in range(2)
            ]
            return (200, {}, json.dumps(records).encode())

    with MarketTruthStore(tmp_path / "wp169_multipage.sqlite3") as store:
        client = PublicMarketDataClient(transport=Transport(), clock=_clock())
        receipt = collect_public_page(
            client, store, "trades", {"limit": 2, "market": CONDITION}, max_pages=2, stop_event=stop
        )
    # Page 1 ran (in-flight finished); page 2 did not begin once the stop was set.
    assert calls["n"] == 1, calls
    assert receipt.status == "STOPPED" and receipt.stop_reason == "CALLER_STOP"


def test_collect_public_page_store_limit_stop_reason(tmp_path) -> None:
    """Reviewer round-2 #1: collect_public_page propagates STORE_LIMIT_EXCEEDED with the
    frozen stop_reason STORE_LIMIT."""
    class Transport:
        def __call__(self, url, headers, timeout):
            return (200, {}, _trade_body())

    with MarketTruthStore(tmp_path / "wp169_cppstore.sqlite3", mt.AcquisitionLimits(max_store_rows=1)) as store:
        client = PublicMarketDataClient(transport=Transport(), clock=_clock())
        receipt = collect_public_page(client, store, "trades", {"limit": 100, "market": CONDITION}, max_pages=1)
    assert receipt.status == "FAILED" and receipt.error_codes == ("STORE_LIMIT_EXCEEDED",)
    assert receipt.stop_reason == "STORE_LIMIT", receipt


def _http_ck_key(endpoint, params):
    norm = _normalize_params(endpoint, params)
    norm.pop("offset", None)
    return _http_checkpoint_key(endpoint, norm)


class _OffsetTransport:
    """Records the offset each request carried and returns `count` distinct trade records."""

    def __init__(self, count):
        self.count = count
        self.offsets = []
        self.seq = 0

    def __call__(self, url, headers, timeout):
        import urllib.parse as _up
        q = _up.parse_qs(_up.urlparse(url).query)
        self.offsets.append(q.get("offset", ["0"])[0])
        recs = []
        for _ in range(self.count):
            self.seq += 1
            recs.append({
                "conditionId": CONDITION, "price": "0.5", "size": "2", "side": "BUY",
                "transactionHash": "0x" + f"{self.seq:064x}", "timestamp": 1720000000 + self.seq,
            })
        return (200, {}, json.dumps(recs).encode())


def test_collect_public_page_resume_checkpoint_lifecycle(tmp_path) -> None:
    """Literal frozen HTTP resume semantics (wp_prompt.txt 384-393): a durably committed FULL
    page writes ACTIVE next_offset=offset+limit; the NEXT invocation resumes exactly there,
    not zero; a short/empty page writes SUPERSEDED next_offset=0 so the following crawl begins
    a new head crawl at zero; a FAILED page does not advance or reset the prior checkpoint.
    Red-sensitive to each sub-behavior (start-at-zero regression, ACTIVE<->SUPERSEDED flip,
    failed-page advance)."""
    query = {"limit": 2, "market": CONDITION}
    key = _http_ck_key("trades", query)
    with MarketTruthStore(tmp_path / "wp169_resume.sqlite3") as store:
        # (a) A full page writes ACTIVE next_offset == limit; first request starts at zero.
        t1 = _OffsetTransport(count=2)
        r1 = collect_public_page(PublicMarketDataClient(transport=t1, clock=_clock()),
                                 store, "trades", dict(query), max_pages=1)
        assert r1.status == "OK"
        ck = store.load_checkpoint(key)
        assert ck is not None and ck.state == "ACTIVE"
        assert json.loads(ck.value_json)["next_offset"] == 2
        assert t1.offsets == ["0"], t1.offsets

        # (b) The next invocation resumes EXACTLY at the checkpointed offset, not zero.
        t2 = _OffsetTransport(count=2)
        r2 = collect_public_page(PublicMarketDataClient(transport=t2, clock=_clock()),
                                 store, "trades", dict(query), max_pages=1)
        assert r2.status == "OK"
        assert t2.offsets == ["2"], t2.offsets
        assert json.loads(store.load_checkpoint(key).value_json)["next_offset"] == 4

        # (c) A short page (record_count < limit) writes SUPERSEDED next_offset=0; the FOLLOWING
        # crawl then restarts a new head crawl at zero.
        t3 = _OffsetTransport(count=1)
        r3 = collect_public_page(PublicMarketDataClient(transport=t3, clock=_clock()),
                                 store, "trades", dict(query), max_pages=1)
        assert r3.status == "OK"
        ck3 = store.load_checkpoint(key)
        assert ck3.state == "SUPERSEDED" and json.loads(ck3.value_json)["next_offset"] == 0
        assert t3.offsets == ["4"], t3.offsets
        t4 = _OffsetTransport(count=1)
        collect_public_page(PublicMarketDataClient(transport=t4, clock=_clock()),
                            store, "trades", dict(query), max_pages=1)
        assert t4.offsets == ["0"], t4.offsets  # SUPERSEDED is not ACTIVE -> head zero

        # (d) A FAILED page leaves the prior ACTIVE checkpoint byte-for-byte unchanged.
        t5 = _OffsetTransport(count=2)
        collect_public_page(PublicMarketDataClient(transport=t5, clock=_clock()),
                            store, "trades", dict(query), max_pages=1)
        before = store.load_checkpoint(key)
        assert before.state == "ACTIVE"

        class _BadTransport:
            def __call__(self, url, headers, timeout):
                recs = [{"conditionId": CONDITION, "price": "0.5", "size": "2", "side": "BUY",
                         "transactionHash": "0x" + f"{i:064x}", "timestamp": 1720000000 + i}
                        for i in range(3)]  # 3 > limit 2 -> RESPONSE_INVALID terminal
                return (200, {}, json.dumps(recs).encode())

        rbad = collect_public_page(PublicMarketDataClient(transport=_BadTransport(), clock=_clock()),
                                   store, "trades", dict(query), max_pages=1)
        assert rbad.status == "FAILED"
        after = store.load_checkpoint(key)
        assert after.state == before.state and after.value_json == before.value_json


def _ts01_bodies():
    return (
        json.dumps({"id": "42", "conditionId": CONDITION, "clobTokenIds": '["7","8"]'}).encode(),
        json.dumps({"asset_id": "7", "market": CONDITION,
                    "bids": [{"price": "0.4", "size": "2"}], "asks": []}).encode(),
    )


def test_ts01_producer_witness_binds_attempts_and_clocks(tmp_path):
    from src.data_layer.polymarket import market_truth_data_api as api

    calls = []
    gamma, book = _ts01_bodies()

    def transport(url, headers, timeout):
        calls.append((url, dict(headers), timeout))
        if len(calls) == 1:
            return 429, {"Retry-After": "0"}, b'{"retry":true}'
        return 200, {}, gamma if "/markets/" in url else book

    path = tmp_path / "pair.sqlite3"
    result = api.collect_trusted_research_pair(path, "42", transport=transport, clock=_clock())
    assert result["status"] == "ADMITTED"
    assert result["proof_level"] == "LOCAL_PRODUCER_WITNESS"
    assert result["transport_mode"] == "INJECTED"
    assert result["token_id"] == "7"
    assert [call[0] for call in calls] == [
        api.GAMMA_BASE + "/markets/42", api.GAMMA_BASE + "/markets/42",
        api.CLOB_BASE + "/book?token_id=7",
    ]
    assert all(set(headers) == {"Accept", "User-Agent"} for _, headers, _ in calls)
    assert [attempt["http_status"] for attempt in result["attempts"]] == [429, 200, 200]
    for item in result["attempts"]:
        assert item["request_started_at"] < item["response_completed_at"] < item["received_at"]
        assert item["duration_ns"] >= 0
        assert item["byte_length"] == len(item["raw_bytes"])
        assert item["raw_sha256"] == mt.sha256_hex(item["raw_bytes"])
        assert item["occurrence_id"] and item["raw_id"]
    assert result["attempts"][0]["source_cursor"] == "http:market-by-id:offset:0:attempt:0"
    assert result["attempts"][1]["source_cursor"] == "http:market-by-id:offset:0:attempt:1"
    assert result == api.export_trusted_research_pair(path)

    # Capture is opt-in; normal callers still sample only the original receive clock.
    ticks = []
    client = api.PublicMarketDataClient(transport=lambda *a: (200, {}, gamma),
                                       clock=lambda: ticks.append(1) or "2024-07-03T10:00:01.000000Z")
    assert client.get_page("market-by-id", {"id": 42}).status == "OK"
    assert ticks == [1] and client._ts01_attempts is None


def test_ts01_gamma_clob_link_and_negative_transport(tmp_path, monkeypatch):
    import io
    import urllib.error
    import urllib.request
    from src.data_layer.polymarket import market_truth_data_api as api

    gamma, book = _ts01_bodies()
    # A negative from each actual trust boundary, without expanding the test framework.
    invalid_markets = [b'null', b'[]', b'{}', b'{', b'\xff',
            b'{"id":"42","id":"43"}',
            json.dumps({"id": "43", "clobTokenIds": ["7"]}).encode()]
    invalid_markets += [json.dumps({"id": "42", "conditionId": CONDITION,
                                    "clobTokenIds": tokens}).encode()
                        for tokens in (None, [], ["7", "7"], [7], ["07"], "not-json")]
    for index, body in enumerate(invalid_markets):
        result = api.collect_trusted_research_pair(tmp_path / f"gamma{index}.sqlite3", "42",
            transport=lambda *args, body=body: (200, {}, body), clock=_clock())
        assert result == {"status": "NOT_ADMITTED", "error_code": "RESPONSE_INVALID"}
    for index, invalid_book in enumerate((b'{}', b'[]',
            json.dumps({"asset_id": "8", "market": CONDITION, "bids": [], "asks": []}).encode(),
            json.dumps({"asset_id": "7", "market": CONDITION, "bids": [None], "asks": []}).encode())):
        result = api.collect_trusted_research_pair(tmp_path / f"book{index}.sqlite3", "42",
            transport=lambda url, *a, body=invalid_book: (200, {}, gamma if "/markets/" in url else body),
            clock=_clock())
        assert result["status"] == "NOT_ADMITTED"
    for market_id in (None, "", "0", "01", "0x123", True, "42?x=1"):
        def forbidden(*args):
            pytest.fail("invalid market must never acquire")
        assert api.collect_trusted_research_pair(tmp_path / "invalid.sqlite3", market_id,
            transport=forbidden)["status"] == "NOT_ADMITTED"

    # No sleeping: 429 exhaustion retains all bounded attempts and writes no receipt.
    calls = []
    limited = tmp_path / "retry.sqlite3"
    assert api.collect_trusted_research_pair(limited, "42", clock=_clock(),
        transport=lambda *a: (calls.append(1) or 429, {"Retry-After": "0"}, b'{}'))["status"] == "NOT_ADMITTED"
    assert len(calls) == mt.AcquisitionLimits().max_retries + 1
    with MarketTruthStore(limited) as store:
        assert store.receipt().raw_count == len(calls)
    assert not limited.with_suffix(".ts01.json").exists()
    for name, transport in (
        ("redirect", lambda *a: (302, {"Location": "https://example.invalid"}, b'{}')),
        ("oversize", lambda *a: (200, {}, b'x' * 1025)),
        ("badstatus", lambda *a: (True, {}, gamma)),
        ("timeout", lambda *a: (_ for _ in ()).throw(TimeoutError("do not echo"))),
    ):
        assert api.collect_trusted_research_pair(tmp_path / f"{name}.sqlite3", "42",
            transport=transport, clock=_clock(), limits=mt.AcquisitionLimits(max_response_bytes=1024))["status"] == "NOT_ADMITTED"

    class Response(io.BytesIO):
        code = 200
        headers = {}
        def read(self, size=-1):
            assert size == 1025  # hard cap at the read, never an unbounded read()
            return super().read(size)

    with pytest.raises(mt.MarketTruthError):
        api._ts01_bounded_body(Response(b'x' * 2048), 1024)
    for declared in ("2048", "x", "1", "-1"):
        response = Response(b'{}'); response.headers = {"Content-Length": declared}
        with pytest.raises(mt.MarketTruthError):
            api._ts01_bounded_body(response, 1024)

    # Exercise the actual no-redirect opener policy, with no sockets or external calls.
    seen = []
    def fake_opener(proxy, handler):
        assert isinstance(proxy, urllib.request.ProxyHandler) and proxy.proxies == {}
        assert isinstance(handler, urllib.request.HTTPRedirectHandler)
        assert handler.redirect_request(None, None, 302, "", {}, "https://example.invalid") is None
        class Opener:
            def open(self, request, timeout):
                seen.append((request.full_url, request.get_method()))
                raise urllib.error.HTTPError(request.full_url, 302, "", {}, Response(b'{}'))
        return Opener()
    monkeypatch.setattr(urllib.request, "build_opener", fake_opener)
    assert api.collect_trusted_research_pair(tmp_path / "default.sqlite3", "42")["status"] == "NOT_ADMITTED"
    assert seen == [(api.GAMMA_BASE + "/markets/42", "GET")]

    # Locally sampled backwards/invalid clocks must never promote a pair receipt.
    for index, bad_clock in enumerate((
        lambda: "invalid", iter(["2024-07-03T10:00:02.000000Z",
                                 "2024-07-03T10:00:01.000000Z"] * 3).__next__,
    )):
        assert api.collect_trusted_research_pair(tmp_path / f"clock{index}.sqlite3", "42",
            transport=lambda url, *a: (200, {}, gamma if "/markets/" in url else book),
            clock=bad_clock)["status"] == "NOT_ADMITTED"
    assert api.collect_trusted_research_pair(tmp_path / "rowbound.sqlite3", "42",
        transport=lambda url, *a: (200, {}, gamma if "/markets/" in url else book),
        clock=_clock(), limits=mt.AcquisitionLimits(max_store_rows=1))["status"] == "NOT_ADMITTED"
