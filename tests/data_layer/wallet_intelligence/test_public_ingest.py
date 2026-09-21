"""Public ingest lifecycle tests (S10-WALLET-01, Section 15)."""

from __future__ import annotations

import json
from types import SimpleNamespace
import urllib.error

import pytest

from src.data_layer.point_in_time_market_research.research_provenance import (
    build_pit_timestamps,
    build_raw_evidence_reference,
)
from src.data_layer.polymarket.public_client import PolymarketPublicClient
from src.data_layer.wallet_intelligence import contracts as c
from src.data_layer.wallet_intelligence import ledger as L
from src.data_layer.wallet_intelligence import public_ingest as pi


WALLET = "0x" + "1" * 40


def _request(**overrides):
    params = dict(
        canonical_wallet=WALLET,
        trades_start="2026-01-01T00:00:00Z",
        trades_end="2026-01-02T00:00:00Z",
        activity_start="2026-01-01T00:00:00Z",
        activity_end="2026-01-02T00:00:00Z",
        run_started_at="2026-01-03T00:00:00Z",
    )
    params.update(overrides)
    return pi.WalletIngestRequest(**params)


def _page(rows, *, next_cursor=None, has_more=False, sha="a" * 64, blen=100, params=(("user", WALLET),)):
    return {
        "rows": rows,
        "next_cursor": next_cursor,
        "has_more": has_more,
        "content_sha256": sha,
        "body_byte_length": blen,
        "request_parameters": list(params),
    }


def _trade_row(cond, tx):
    return {
        "condition_id": cond,
        "token_id": "111",
        "side": "BUY",
        "price": "0.5",
        "size": "10",
        "timestamp": "2026-01-01T12:00:00Z",
        "transaction_hash": tx,
        "proxy_wallet": WALLET,
    }


def _new_ledger(tmp_path, name="w.sqlite"):
    path = str(tmp_path / name)
    L.initialize_wallet_evidence_ledger(path)
    return path


def _clock(n=40):
    return [f"2026-01-03T00:{i // 60:02d}:{i % 60:02d}Z" for i in range(1, n + 1)]


def _record_count(path, *kinds):
    snapshot = L.load_and_verify_wallet_evidence_ledger(path).snapshot
    return sum(entry.record_kind in kinds for entry in snapshot.entries)


class _Guard:
    def __init__(self, allowed, log=None):
        self.allowed = allowed
        self.calls = 0
        self.log = log

    def record_allowed(self, endpoint_key):
        self.calls += 1
        if self.log is not None:
            self.log.append(("guard", endpoint_key))
        return SimpleNamespace(allowed=self.allowed)


class _SequenceGuard:
    def __init__(self, decisions):
        self.decisions = list(decisions)
        self.calls = 0

    def record_allowed(self, endpoint_key):
        decision = self.decisions[min(self.calls, len(self.decisions) - 1)]
        self.calls += 1
        return SimpleNamespace(allowed=decision)


class _RawResponse:
    def __init__(self, body, status=200):
        self.body = body
        self.status = status
        self.headers = {}
        self.position = 0

    def read(self, size=-1):
        if size is None or size < 0:
            size = len(self.body) - self.position
        chunk = self.body[self.position:self.position + size]
        self.position += len(chunk)
        return chunk

    def getcode(self):
        return self.status

    def close(self):
        pass


class _RawOpener:
    def __init__(self, outcomes=(), attempt_state=None):
        self.outcomes = list(outcomes)
        self.attempt_state = attempt_state
        self.calls = 0
        self.observed_attempt_counts = []

    def open(self, request, timeout=None):
        self.calls += 1
        if self.attempt_state is not None:
            self.observed_attempt_counts.append(
                self.attempt_state.transport_attempt_count
            )
        if not self.outcomes:
            raise AssertionError("unexpected raw opener call")
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome


def _valid_response(rows=()):
    body = json.dumps(
        {"data": list(rows), "pagination": {"has_more": False, "next_cursor": None}}
    ).encode("utf-8")
    return _RawResponse(body)


class _WalletClient:
    def __init__(self, log=None):
        self.calls = 0
        self.log = log

    def _page(self, feed):
        self.calls += 1
        if self.log is not None:
            self.log.append(("client", feed))
        return SimpleNamespace(
            rows=(), next_cursor=None, has_more=False,
            content_sha256="a" * 64, body_byte_length=2,
            request_parameters=(("user", WALLET),),
        )

    def get_wallet_trades_page(self, **kwargs):
        return self._page("TRADES")

    def get_wallet_activity_page(self, **kwargs):
        return self._page("STANDARD_ACTIVITY")

    def get_wallet_activity_combos_page(self, **kwargs):
        return self._page("COMBO_ACTIVITY")


# ---------------------------------------------------------------------------
# Dry run + network default OFF (R-W20).
# ---------------------------------------------------------------------------
def test_dry_run_zero_network_zero_writes(tmp_path):
    path = _new_ledger(tmp_path)
    res = pi.ingest_wallet_evidence(_request(), ledger_path=path, mode="DRY_RUN")
    assert res.collection_completion_state == "DRY_RUN"
    assert res.transport_call_count == 0
    assert res.appended_record_count == 0
    snapshot = L.load_and_verify_wallet_evidence_ledger(path).snapshot
    assert len(snapshot.entries) == 0


@pytest.mark.parametrize("guard", [None, object()])
def test_network_missing_or_invalid_guard_rejected_before_acquisition(tmp_path, guard):
    path = _new_ledger(tmp_path)
    opener = _RawOpener()
    result = pi.ingest_wallet_evidence(
        _request(), ledger_path=path, mode="NETWORK",
        client=PolymarketPublicClient(), opener=opener, guard=guard,
    )
    assert result.collection_completion_state == "REJECTED_BEFORE_ACQUISITION"
    assert result.error_codes == ("RATE_LIMIT_GUARD_DENIED",)
    assert result.transport_call_count == result.appended_record_count == 0
    assert opener.calls == 0
    assert _record_count(
        path, "RAW_EVIDENCE_REFERENCE", "WALLET_FEED_PAGE_EVIDENCE",
        "WALLET_EVENT_OBSERVATION", "WALLET_EVIDENCE_EVENT",
        "WALLET_INGEST_RUN_RECEIPT",
    ) == 0


def test_network_denied_guard_zero_transport_and_records(tmp_path):
    path = _new_ledger(tmp_path)
    guard = _Guard(False)
    opener = _RawOpener()
    result = pi.ingest_wallet_evidence(
        _request(), ledger_path=path, mode="NETWORK",
        client=PolymarketPublicClient(), opener=opener,
        guard=guard, clock_times=_clock(),
    )
    assert guard.calls == 1
    assert opener.calls == 0
    assert result.collection_completion_state == "REJECTED_BEFORE_ACQUISITION"
    assert result.error_codes == ("RATE_LIMIT_GUARD_DENIED",)
    assert result.transport_call_count == result.appended_record_count == 0
    assert _record_count(
        path, "RAW_EVIDENCE_REFERENCE", "WALLET_FEED_PAGE_EVIDENCE",
        "WALLET_EVENT_OBSERVATION", "WALLET_EVIDENCE_EVENT",
        "WALLET_INGEST_RUN_RECEIPT",
    ) == 0


def test_make_network_fetcher_rejects_missing_guard():
    with pytest.raises(c.WalletContractError) as exc:
        pi.make_network_fetcher(
            PolymarketPublicClient(), request=_request(), opener=_RawOpener(),
            guard=None, attempt_state=pi._NetworkAttemptState(),
        )
    assert str(exc.value) == "RATE_LIMIT_GUARD_DENIED"


@pytest.mark.parametrize(
    "case",
    ["duck", "subclass", "public_shadow", "internal_shadow", "class_replaced"],
)
def test_network_rejects_every_altered_client_path(tmp_path, monkeypatch, case):
    custom_calls = {"n": 0}

    def custom(*args, **kwargs):
        custom_calls["n"] += 1
        raise AssertionError("custom client path used")

    if case == "duck":
        client = _WalletClient()
    elif case == "subclass":
        class AlteredClient(PolymarketPublicClient):
            def get_wallet_trades_page(self, **kwargs):
                return custom(**kwargs)

        client = AlteredClient()
    else:
        client = PolymarketPublicClient()
        if case == "public_shadow":
            client.get_wallet_trades_page = custom
        elif case == "internal_shadow":
            client._wallet_data_api_get_page = custom
        else:
            monkeypatch.setattr(
                PolymarketPublicClient, "_wallet_data_api_get_page", custom
            )

    path = _new_ledger(tmp_path, f"{case}.sqlite")
    guard = _Guard(True)
    opener = _RawOpener()
    result = pi.ingest_wallet_evidence(
        _request(), ledger_path=path, mode="NETWORK", client=client,
        opener=opener, guard=guard,
    )
    assert result.collection_completion_state == "REJECTED_BEFORE_ACQUISITION"
    assert result.error_codes == ("FIELD_VALUE_INVALID",)
    assert result.transport_call_count == result.appended_record_count == 0
    assert guard.calls == opener.calls == custom_calls["n"] == 0
    assert _record_count(
        path, "RAW_EVIDENCE_REFERENCE", "WALLET_FEED_PAGE_EVIDENCE",
        "WALLET_EVENT_OBSERVATION", "WALLET_EVIDENCE_EVENT",
        "WALLET_INGEST_RUN_RECEIPT",
    ) == 0

    attempt_state = pi._NetworkAttemptState()
    direct_guard = _Guard(True)
    direct_opener = _RawOpener()
    with pytest.raises(c.WalletContractError) as exc:
        pi.make_network_fetcher(
            client, request=_request(), opener=direct_opener,
            guard=direct_guard, attempt_state=attempt_state,
        )
    assert str(exc.value) == "FIELD_VALUE_INVALID"
    assert attempt_state.transport_attempt_count == 0
    assert direct_guard.calls == direct_opener.calls == custom_calls["n"] == 0


@pytest.mark.parametrize(
    ("failure", "expected_code"),
    [
        ("source_unavailable", "SOURCE_UNAVAILABLE"),
        ("invalid_envelope", "SOURCE_RESPONSE_INVALID"),
        ("runtime", "INTERNAL_VALIDATION_FAILED"),
    ],
)
def test_network_post_dispatch_failures_preserve_attempt_and_receipt(
    tmp_path, failure, expected_code
):
    if failure == "source_unavailable":
        outcome = urllib.error.URLError("offline")
    elif failure == "invalid_envelope":
        outcome = _RawResponse(b'{"data":[]}')
    else:
        outcome = RuntimeError("bounded failure")
    path = _new_ledger(tmp_path, f"{failure}.sqlite")
    opener = _RawOpener([outcome])
    result = pi.ingest_wallet_evidence(
        _request(), ledger_path=path, mode="NETWORK",
        client=PolymarketPublicClient(), opener=opener,
        guard=_SequenceGuard([True, False, False]), clock_times=_clock(),
    )
    assert opener.calls == result.transport_call_count == 1
    assert result.collection_completion_state != "REJECTED_BEFORE_ACQUISITION"
    assert result.feed_outcomes[0].failure_codes == (expected_code,)
    assert result.wallet_ingest_run_receipt_id is not None
    assert _record_count(
        path, "RAW_EVIDENCE_REFERENCE", "WALLET_FEED_PAGE_EVIDENCE",
        "WALLET_EVENT_OBSERVATION", "WALLET_EVIDENCE_EVENT",
    ) == 0
    assert _record_count(path, "WALLET_INGEST_RUN_RECEIPT") == 1


def test_network_zero_dispatch_client_validation_failure_is_terminal(tmp_path):
    path = _new_ledger(tmp_path)
    opener = _RawOpener()
    guard = _Guard(True)
    result = pi.ingest_wallet_evidence(
        _request(page_size=101), ledger_path=path, mode="NETWORK",
        client=PolymarketPublicClient(), opener=opener,
        guard=guard, clock_times=_clock(),
    )
    assert result.collection_completion_state == "REJECTED_BEFORE_ACQUISITION"
    assert result.error_codes == ("FIELD_VALUE_INVALID",)
    assert result.transport_call_count == result.appended_record_count == 0
    assert guard.calls == 1
    assert opener.calls == 0
    assert _record_count(
        path, "RAW_EVIDENCE_REFERENCE", "WALLET_FEED_PAGE_EVIDENCE",
        "WALLET_EVENT_OBSERVATION", "WALLET_EVIDENCE_EVENT",
        "WALLET_INGEST_RUN_RECEIPT",
    ) == 0


def test_network_failed_request_then_guard_denial_preserves_both_failures(tmp_path):
    path = _new_ledger(tmp_path)
    opener = _RawOpener([urllib.error.URLError("offline")])
    guard = _SequenceGuard([True, False, False])
    result = pi.ingest_wallet_evidence(
        _request(), ledger_path=path, mode="NETWORK",
        client=PolymarketPublicClient(), opener=opener,
        guard=guard, clock_times=_clock(),
    )
    assert opener.calls == result.transport_call_count == 1
    assert result.collection_completion_state != "REJECTED_BEFORE_ACQUISITION"
    assert result.feed_outcomes[0].failure_codes == ("SOURCE_UNAVAILABLE",)
    assert result.feed_outcomes[1].failure_codes == ("RATE_LIMIT_GUARD_DENIED",)
    assert result.wallet_ingest_run_receipt_id is not None


def test_network_success_then_guard_denial_preserves_page_evidence(tmp_path):
    path = _new_ledger(tmp_path)
    opener = _RawOpener([_valid_response()])
    guard = _SequenceGuard([True, False, False])
    result = pi.ingest_wallet_evidence(
        _request(), ledger_path=path, mode="NETWORK",
        client=PolymarketPublicClient(), opener=opener,
        guard=guard, clock_times=_clock(),
    )
    assert opener.calls == result.transport_call_count == 1
    assert result.collection_completion_state != "REJECTED_BEFORE_ACQUISITION"
    assert result.feed_outcomes[0].page_count == 1
    assert result.feed_outcomes[1].failure_codes == ("RATE_LIMIT_GUARD_DENIED",)
    assert result.wallet_ingest_run_receipt_id is not None
    assert _record_count(path, "RAW_EVIDENCE_REFERENCE") == 1
    assert _record_count(path, "WALLET_FEED_PAGE_EVIDENCE") == 1


def test_network_direct_fetcher_counts_only_raw_opener_dispatch():
    attempt_state = pi._NetworkAttemptState()
    opener = _RawOpener([_valid_response()], attempt_state=attempt_state)
    guard = _Guard(True)
    fetch = pi.make_network_fetcher(
        PolymarketPublicClient(), request=_request(), opener=opener,
        guard=guard, attempt_state=attempt_state,
    )
    page = fetch("TRADES", None)
    assert guard.calls == opener.calls == 1
    assert opener.observed_attempt_counts == [1]
    assert attempt_state.transport_attempt_count == 1
    assert "_transport" not in page

    with pytest.raises(c.WalletContractError) as exc:
        pi.make_network_fetcher(
            PolymarketPublicClient(), request=_request(),
            opener=pi._CountingOpener(_RawOpener(), pi._NetworkAttemptState()),
            guard=_Guard(True), attempt_state=pi._NetworkAttemptState(),
        )
    assert str(exc.value) == "FIELD_VALUE_INVALID"


def test_network_rejects_arbitrary_page_fetcher_without_invocation(tmp_path):
    path = _new_ledger(tmp_path)
    calls = {"n": 0}

    def bypass(feed, cursor):
        calls["n"] += 1
        return _page([])

    result = pi.ingest_wallet_evidence(
        _request(), ledger_path=path, mode="NETWORK", page_fetcher=bypass,
        client=_WalletClient(), opener=object(), guard=_Guard(True),
    )
    assert result.collection_completion_state == "REJECTED_BEFORE_ACQUISITION"
    assert result.error_codes == ("FIELD_VALUE_INVALID",)
    assert calls["n"] == 0
    assert result.transport_call_count == result.appended_record_count == 0
    assert _record_count(
        path, "RAW_EVIDENCE_REFERENCE", "WALLET_FEED_PAGE_EVIDENCE",
        "WALLET_EVENT_OBSERVATION", "WALLET_EVIDENCE_EVENT",
        "WALLET_INGEST_RUN_RECEIPT",
    ) == 0


# ---------------------------------------------------------------------------
# Complete run + per-feed completeness (R-F03 / R-V2-06 positive).
# ---------------------------------------------------------------------------
def test_complete_run_all_three_feeds(tmp_path):
    path = _new_ledger(tmp_path)
    pages = {
        "TRADES": [_page([_trade_row("0xabc", "0x" + "a" * 64)])],
        "STANDARD_ACTIVITY": [
            _page([{"type": "TRADE", "is_combo": False, "condition_id": "0xabc",
                    "price": "0.5", "size": "10", "side": "BUY",
                    "timestamp": "2026-01-01T12:00:00Z", "transaction_hash": "0x" + "d" * 64}])
        ],
        "COMBO_ACTIVITY": [_page([])],
    }
    res = pi.ingest_wallet_evidence(
        _request(), ledger_path=path, mode="LOCAL_RESPONSE_FIXTURE",
        page_fetcher=pi.make_local_fixture_fetcher(pages), clock_times=_clock(),
    )
    assert res.collection_completion_state == "COMPLETE"
    assert res.wallet_ingest_run_receipt_id is not None
    states = {o.feed_key: o.completion_state for o in res.feed_outcomes}
    assert states == {"TRADES": "COMPLETE", "STANDARD_ACTIVITY": "COMPLETE", "COMBO_ACTIVITY": "COMPLETE"}
    # combo feed reports NOT_SUPPORTED time filtering.
    combo_receipt = next(o.receipt for o in res.feed_outcomes if o.feed_key == "COMBO_ACTIVITY")
    assert combo_receipt.time_filter_capability == "NOT_SUPPORTED"
    assert combo_receipt.requested_start is None and combo_receipt.requested_end is None


# ---------------------------------------------------------------------------
# Zero-event page is first-class evidence (R-D01).
# ---------------------------------------------------------------------------
def test_zero_event_page_persists_raw_and_page(tmp_path):
    path = _new_ledger(tmp_path)
    pages = {
        "TRADES": [_page([])],
        "STANDARD_ACTIVITY": [_page([])],
        "COMBO_ACTIVITY": [_page([])],
    }
    res = pi.ingest_wallet_evidence(
        _request(), ledger_path=path, mode="LOCAL_RESPONSE_FIXTURE",
        page_fetcher=pi.make_local_fixture_fetcher(pages), clock_times=_clock(),
    )
    snapshot = L.load_and_verify_wallet_evidence_ledger(path).snapshot
    tagged = L.query_records_by_ingest_run_key(snapshot, res.ingest_run_key)
    pages_found = [t for t in tagged if t.record_kind == "WALLET_FEED_PAGE_EVIDENCE"]
    raws = [e for e in snapshot.entries if e.record_kind == "RAW_EVIDENCE_REFERENCE"]
    assert len(pages_found) == 3  # one zero-event page per feed
    assert len(raws) == 3
    for page in pages_found:
        assert page.payload["normalized_event_count"] == 0
        assert page.payload["observation_count"] == 0


# ---------------------------------------------------------------------------
# Pagination: no duplicate, no omission (R-W06 / R-V2-02).
# ---------------------------------------------------------------------------
def test_pagination_dedupes_overlapping_event(tmp_path):
    path = _new_ledger(tmp_path)
    rowA = _trade_row("0xaaa", "0x" + "a" * 64)
    rowB = _trade_row("0xbbb", "0x" + "b" * 64)
    rowC = _trade_row("0xccc", "0x" + "c" * 64)
    pages = {
        "TRADES": [
            _page([rowA, rowB], next_cursor="C2", has_more=True, sha="1" * 64),
            _page([rowB, rowC], next_cursor=None, has_more=False, sha="2" * 64),
        ],
        "STANDARD_ACTIVITY": [_page([])],
        "COMBO_ACTIVITY": [_page([])],
    }
    res = pi.ingest_wallet_evidence(
        _request(), ledger_path=path, mode="LOCAL_RESPONSE_FIXTURE",
        page_fetcher=pi.make_local_fixture_fetcher(pages), clock_times=_clock(),
    )
    assert res.collection_completion_state == "COMPLETE"
    snapshot = L.load_and_verify_wallet_evidence_ledger(path).snapshot
    events = [e for e in snapshot.entries if e.record_kind == "WALLET_EVIDENCE_EVENT"]
    observations = [e for e in snapshot.entries if e.record_kind == "WALLET_EVENT_OBSERVATION"]
    # A,B,C distinct events (B not double-counted); 4 observations (A,B / B,C).
    assert len(events) == 3
    assert len(observations) == 4
    trades = next(o for o in res.feed_outcomes if o.feed_key == "TRADES")
    assert trades.page_count == 2
    assert trades.cursor_chain == ((None, "C2"), ("C2", None))


# ---------------------------------------------------------------------------
# Max-page truncation -> PARTIAL_LIMIT (R-V2-06 / cursor).
# ---------------------------------------------------------------------------
def test_max_page_truncation_is_partial_limit(tmp_path):
    path = _new_ledger(tmp_path)
    # Every trades page reports has_more with a fresh cursor -> never terminates
    # until the hard page bound stops it.
    trades_pages = [
        _page([_trade_row(f"0x{i:03x}", "0x" + f"{i:064x}")], next_cursor=f"C{i}", has_more=True, sha=f"{i:064x}")
        for i in range(pi.WALLET_MAX_PAGES_PER_FEED + 3)
    ]
    pages = {"TRADES": trades_pages, "STANDARD_ACTIVITY": [_page([])], "COMBO_ACTIVITY": [_page([])]}
    res = pi.ingest_wallet_evidence(
        _request(), ledger_path=path, mode="LOCAL_RESPONSE_FIXTURE",
        page_fetcher=pi.make_local_fixture_fetcher(pages), clock_times=_clock(60),
    )
    trades = next(o for o in res.feed_outcomes if o.feed_key == "TRADES")
    assert trades.completion_state == "PARTIAL_LIMIT"
    assert trades.page_count == pi.WALLET_MAX_PAGES_PER_FEED
    assert "PARTIALLY_OBSERVED" in trades.dq_flags and "SEQUENCE_GAP" in trades.dq_flags
    assert res.collection_completion_state == "PARTIAL_LIMIT"


@pytest.mark.parametrize(
    ("row_count", "page_size", "feed_rows", "run_rows", "passes"),
    [
        (100, 100, 900, 2900, True),
        (101, 100, 0, 0, False),
        (1, 100, 1000, 0, False),
        (1, 100, 0, 3000, False),
    ],
)
def test_projected_row_limit_exact_boundaries(row_count, page_size, feed_rows, run_rows, passes):
    if passes:
        assert pi._validate_projected_row_limits(
            row_count=row_count, requested_page_size=page_size,
            committed_feed_rows=feed_rows, committed_run_rows=run_rows,
        ) == (1000, 3000)
    else:
        with pytest.raises(pi._StopFeed) as exc:
            pi._validate_projected_row_limits(
                row_count=row_count, requested_page_size=page_size,
                committed_feed_rows=feed_rows, committed_run_rows=run_rows,
            )
        assert exc.value.code == "LIMIT_EXCEEDED"


def test_oversized_page_is_not_persisted(tmp_path):
    path = _new_ledger(tmp_path)
    pages = {
        "TRADES": [_page([{}] * 101)],
        "STANDARD_ACTIVITY": [_page([])],
        "COMBO_ACTIVITY": [_page([])],
    }
    result = pi.ingest_wallet_evidence(
        _request(), ledger_path=path, mode="LOCAL_RESPONSE_FIXTURE",
        page_fetcher=pi.make_local_fixture_fetcher(pages), clock_times=_clock(),
    )
    trades = result.feed_outcomes[0]
    assert trades.completion_state == "PARTIAL_LIMIT"
    assert trades.failure_codes == ("LIMIT_EXCEEDED",)
    assert trades.page_count == trades.source_row_count == 0
    snapshot = L.load_and_verify_wallet_evidence_ledger(path).snapshot
    assert not any(
        entry.payload.get("feed_key") == "TRADES"
        for entry in snapshot.entries
        if entry.record_kind == "WALLET_FEED_PAGE_EVIDENCE"
    )


def test_projected_feed_overflow_does_not_persist_offending_page(tmp_path, monkeypatch):
    path = _new_ledger(tmp_path)
    monkeypatch.setattr(pi, "WALLET_MAX_SOURCE_ROWS_PER_FEED_RUN", 1)
    pages = {
        "TRADES": [
            _page([_trade_row("0xaaa", "0x" + "a" * 64)], next_cursor="C2", has_more=True),
            _page([_trade_row("0xbbb", "0x" + "b" * 64)], sha="b" * 64),
        ],
        "STANDARD_ACTIVITY": [_page([])], "COMBO_ACTIVITY": [_page([])],
    }
    result = pi.ingest_wallet_evidence(
        _request(), ledger_path=path, mode="LOCAL_RESPONSE_FIXTURE",
        page_fetcher=pi.make_local_fixture_fetcher(pages), clock_times=_clock(),
    )
    trades = result.feed_outcomes[0]
    assert trades.completion_state == "PARTIAL_LIMIT"
    assert trades.page_count == trades.source_row_count == 1
    assert len(trades.raw_evidence_ids) == len(trades.event_ids) == 1


def test_projected_run_overflow_does_not_persist_offending_page(tmp_path, monkeypatch):
    path = _new_ledger(tmp_path)
    monkeypatch.setattr(pi, "WALLET_MAX_SOURCE_ROWS_TOTAL_RUN", 1)
    pages = {
        "TRADES": [_page([_trade_row("0xaaa", "0x" + "a" * 64)])],
        "STANDARD_ACTIVITY": [_page([{"type": "REWARD", "usdc_size": "1"}])],
        "COMBO_ACTIVITY": [_page([])],
    }
    result = pi.ingest_wallet_evidence(
        _request(), ledger_path=path, mode="LOCAL_RESPONSE_FIXTURE",
        page_fetcher=pi.make_local_fixture_fetcher(pages), clock_times=_clock(),
    )
    standard = result.feed_outcomes[1]
    assert standard.completion_state == "PARTIAL_LIMIT"
    assert standard.page_count == standard.source_row_count == 0
    assert result.feed_outcomes[0].page_count == result.feed_outcomes[0].source_row_count == 1


def test_duplicate_cursor_is_partial_cursor_gap(tmp_path):
    path = _new_ledger(tmp_path)
    pages = {
        "TRADES": [
            _page([_trade_row("0xaaa", "0x" + "a" * 64)], next_cursor="LOOP", has_more=True, sha="1" * 64),
            _page([_trade_row("0xbbb", "0x" + "b" * 64)], next_cursor="LOOP", has_more=True, sha="2" * 64),
        ],
        "STANDARD_ACTIVITY": [_page([])],
        "COMBO_ACTIVITY": [_page([])],
    }
    res = pi.ingest_wallet_evidence(
        _request(), ledger_path=path, mode="LOCAL_RESPONSE_FIXTURE",
        page_fetcher=pi.make_local_fixture_fetcher(pages), clock_times=_clock(),
    )
    trades = next(o for o in res.feed_outcomes if o.feed_key == "TRADES")
    assert trades.completion_state == "PARTIAL_CURSOR_GAP"


# ---------------------------------------------------------------------------
# Partial run durability (R-V2-06): page1 survives page2 failure.
# ---------------------------------------------------------------------------
def test_partial_run_page1_durable_after_page2_failure(tmp_path):
    path = _new_ledger(tmp_path)
    # TRADES has only one fixture page but claims has_more -> next fetch raises
    # StopFeed (fixture exhausted) after page1 is already committed.
    pages = {
        "TRADES": [_page([_trade_row("0xaaa", "0x" + "a" * 64)], next_cursor="C2", has_more=True)],
        "STANDARD_ACTIVITY": [_page([])],
        "COMBO_ACTIVITY": [_page([])],
    }
    res = pi.ingest_wallet_evidence(
        _request(), ledger_path=path, mode="LOCAL_RESPONSE_FIXTURE",
        page_fetcher=pi.make_local_fixture_fetcher(pages), clock_times=_clock(),
    )
    trades = next(o for o in res.feed_outcomes if o.feed_key == "TRADES")
    assert trades.completion_state == "PARTIAL_SOURCE_FAILURE"
    assert trades.page_count == 1  # page 1 committed and durable
    assert res.collection_completion_state != "COMPLETE"
    snapshot = L.load_and_verify_wallet_evidence_ledger(path).snapshot
    page1 = [e for e in snapshot.entries if e.record_kind == "WALLET_FEED_PAGE_EVIDENCE" and e.payload["feed_key"] == "TRADES"]
    assert len(page1) == 1
    assert page1[0].payload["local_first_seen_time"]  # first-seen preserved


# ---------------------------------------------------------------------------
# Run-key collision / reuse guard (R-D03).
# ---------------------------------------------------------------------------
def test_run_key_collision_rejected_before_acquisition(tmp_path):
    path = _new_ledger(tmp_path)
    pages = {"TRADES": [_page([])], "STANDARD_ACTIVITY": [_page([])], "COMBO_ACTIVITY": [_page([])]}
    first = pi.ingest_wallet_evidence(
        _request(), ledger_path=path, mode="LOCAL_RESPONSE_FIXTURE",
        page_fetcher=pi.make_local_fixture_fetcher(pages), clock_times=_clock(),
    )
    assert first.collection_completion_state == "COMPLETE"

    calls = {"n": 0}

    def counting_fetch(feed, cursor):
        calls["n"] += 1
        return _page([])

    second = pi.ingest_wallet_evidence(
        _request(), ledger_path=path, mode="LOCAL_RESPONSE_FIXTURE",
        page_fetcher=counting_fetch, clock_times=_clock(),
    )
    assert second.collection_completion_state == "REJECTED_BEFORE_ACQUISITION"
    assert second.error_codes == ("LEDGER_IDENTITY_CONFLICT",)
    assert calls["n"] == 0  # zero transport / zero fetch


def test_same_inputs_same_run_key():
    a = pi.derive_run_key(_request())
    b = pi.derive_run_key(_request())
    assert a == b and a.startswith("walletingestrun:sha256:")


# ---------------------------------------------------------------------------
# Interrupted-run offline recovery (R-D02 / R-F01).
# ---------------------------------------------------------------------------
def test_offline_recovery_appends_partial_interrupted(tmp_path):
    path = _new_ledger(tmp_path)
    request = _request()
    run_key = pi.derive_run_key(request)
    # Simulate an interrupted run: commit one page (raw + page) under the run key,
    # but NO terminal receipt.
    raw = build_raw_evidence_reference(
        source_system="POLYMARKET_DATA_API_V2",
        endpoint="/v2/trades",
        retrieval_method="GET/urllib",
        content_sha256="a" * 64,
        byte_length=10,
        media_type="application/json",
        pit=build_pit_timestamps(local_first_seen_time="2026-01-03T00:00:01Z", ingestion_time="2026-01-03T00:00:02Z"),
        dq_flags=["OK"],
        replay_fidelity="FAITHFUL",
    )
    page = c.build_wallet_feed_page_evidence(
        raw_evidence_reference_id=raw.raw_evidence_reference_id,
        ingest_run_key=run_key,
        feed_key="TRADES",
        canonical_request_identity={"user": WALLET},
        requested_page_size=100,
        has_more=True,
        local_first_seen_time="2026-01-03T00:00:01Z",
        ingestion_time="2026-01-03T00:00:02Z",
        api_source_parser_version="v/1",
        dq_flags=["OK"],
        replay_fidelity="FAITHFUL",
        source_row_count=0,
        normalized_event_count=0,
        observation_count=0,
    )
    L.append_wallet_evidence_records(path, [raw, page])

    rec = pi.recover_interrupted_wallet_ingest(request, ledger_path=path, run_ended_at="2026-01-03T01:00:00Z")
    assert rec.collection_completion_state == "PARTIAL_INTERRUPTED"
    assert rec.transport_call_count == 0
    assert rec.wallet_ingest_run_receipt_id is not None

    # A second recovery after the terminal receipt exists must reject.
    rec2 = pi.recover_interrupted_wallet_ingest(request, ledger_path=path, run_ended_at="2026-01-03T02:00:00Z")
    assert rec2.collection_completion_state == "REJECTED_BEFORE_ACQUISITION"
    assert rec2.error_codes == ("LEDGER_IDENTITY_CONFLICT",)


def test_offline_recovery_rejects_when_no_page_evidence(tmp_path):
    path = _new_ledger(tmp_path)
    rec = pi.recover_interrupted_wallet_ingest(_request(), ledger_path=path, run_ended_at="2026-01-03T01:00:00Z")
    assert rec.collection_completion_state == "REJECTED_BEFORE_ACQUISITION"


# ---------------------------------------------------------------------------
# Activity combo discriminator handling.
# ---------------------------------------------------------------------------
def test_activity_trade_is_combo_true_false(tmp_path):
    path = _new_ledger(tmp_path)
    combo_condition = "0x03" + "a" * 60
    pages = {
        "TRADES": [_page([])],
        "STANDARD_ACTIVITY": [
            _page([
                {"type": "TRADE", "is_combo": True, "condition_id": combo_condition,
                 "token_id": "combo-position", "price": "0.5",
                 "size": "10", "side": "BUY", "timestamp": "2026-01-01T12:00:00Z",
                 "transaction_hash": "0x" + "a" * 64},
                {"type": "TRADE", "is_combo": False, "condition_id": "0xdef", "price": "0.6",
                 "size": "5", "side": "SELL", "timestamp": "2026-01-01T12:00:01Z",
                 "transaction_hash": "0x" + "b" * 64},
            ])
        ],
        "COMBO_ACTIVITY": [_page([])],
    }
    res = pi.ingest_wallet_evidence(
        _request(), ledger_path=path, mode="LOCAL_RESPONSE_FIXTURE",
        page_fetcher=pi.make_local_fixture_fetcher(pages), clock_times=_clock(),
    )
    snapshot = L.load_and_verify_wallet_evidence_ledger(path).snapshot
    events = [e for e in snapshot.entries if e.record_kind == "WALLET_EVIDENCE_EVENT"]
    combo_states = sorted(e.payload["combo_state"] for e in events)
    assert combo_states == ["FALSE", "TRUE"]
    by_state = {e.payload["combo_state"]: e.payload for e in events}
    assert by_state["TRUE"]["condition_context"] == "COMBO_CONDITION_ID"
    assert by_state["TRUE"]["token_context"] == "COMBO_POSITION_ID"
    assert by_state["FALSE"]["condition_context"] == "DATA_API_RESPONSE_CONDITION_ID"


def test_activity_economic_fields_and_combo_payout_survive_verified_load(tmp_path):
    path = _new_ledger(tmp_path)
    combo_condition = "0x03" + "b" * 60
    pages = {
        "TRADES": [_page([])],
        "STANDARD_ACTIVITY": [_page([
            {"type": "REWARD", "usdc_size": "12.50", "timestamp": "2026-01-01T12:00:00Z"},
            {"type": "TIP", "side": "IN", "usdc_size": "2.00", "timestamp": "2026-01-01T12:00:01Z"},
            {"type": "TIP", "side": "OUT", "timestamp": "2026-01-01T12:00:02Z"},
        ])],
        "COMBO_ACTIVITY": [_page([{
            "id": "combo-redeem-1", "type": "REDEEM",
            "combo_condition_id": combo_condition,
            "combo_position_id": "combo-position-1",
            "amount_usdc": "10.00", "payout_usdc": "7.50",
            "timestamp": "2026-01-01T12:00:03Z",
        }])],
    }
    result = pi.ingest_wallet_evidence(
        _request(), ledger_path=path, mode="LOCAL_RESPONSE_FIXTURE",
        page_fetcher=pi.make_local_fixture_fetcher(pages), clock_times=_clock(),
    )
    assert result.collection_completion_state == "COMPLETE"
    loaded = L.load_and_verify_wallet_evidence_ledger(path)
    assert loaded.is_valid
    events = [
        entry.payload for entry in loaded.snapshot.entries
        if entry.record_kind == "WALLET_EVIDENCE_EVENT"
    ]
    reward = next(event for event in events if event["canonical_event_type"] == "REWARD")
    tips = sorted(
        (event for event in events if event["canonical_event_type"] == "TIP"),
        key=lambda event: event["side"],
    )
    redeem = next(
        event for event in events if event["canonical_event_type"] == "REDEEM_SETTLEMENT"
    )
    assert reward["notional"] == "12.5"
    assert [(tip["side"], tip["notional"]) for tip in tips] == [("IN", "2"), ("OUT", None)]
    assert redeem["notional"] == "10"
    assert redeem["payout"] == "7.5"
    assert redeem["token_context"] == "COMBO_POSITION_ID"


def test_wallet_package_has_no_forbidden_network_imports():
    import src.data_layer.wallet_intelligence.public_ingest as module
    import inspect

    for mod in (module,):
        source = inspect.getsource(mod)
        for forbidden in ("import requests", "import httpx", "import aiohttp", "import websockets", "import socket", "py_clob_client"):
            assert forbidden not in source
