"""Focused tests for the WP166 bounded scalable one-page keyset lineage-delta
public Polymarket capture coordinator and offline registration recovery.

These tests never touch the network. Every network-capable path is exercised with
an injected fake GET-only keyset client, an injected guard, and a fixed clock. The
prior registered baseline is always produced by the merged WP164 seed coordinator
so the cross-run lineage is proven against a genuine committed dataset.
"""

from __future__ import annotations

import ast
import datetime
import io
import json
import os
import tempfile
import tokenize

import pytest

import src.data_layer.point_in_time_market_research as pit
from src.data_layer.polymarket.models import AdapterResult, ReadOnlyRequestInfo
from src.data_layer.point_in_time_market_research import (
    polymarket_scaled_population as scaled,
)
from src.data_layer.point_in_time_market_research import (
    PolymarketPublicPopulationConfig as WP164Cfg,
    PolymarketScaledPopulationConfig as Cfg,
    append_point_in_time_records,
    initialize_manifest_store,
    initialize_point_in_time_record_store,
    load_and_verify_manifest_store,
    load_and_verify_point_in_time_record_store,
    materialize_dataset_snapshot_reference,
    populate_initial_polymarket_public_data,
    capture_scaled_polymarket_public_page,
    recover_scaled_polymarket_public_registration,
)


PROV = dict(
    parameter_set_id="params:v1", normalizer_version="norm:v1", validator_version="val:v1"
)
MANIFEST_ID = "manifest:polymarket:test"

SCALED_SRC = (
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    + "/src/data_layer/point_in_time_market_research/polymarket_scaled_population.py"
)


# ── Fixtures / injection seams (never touch the network) ──────────────────────


def _request_info(status: int = 200) -> ReadOnlyRequestInfo:
    return ReadOnlyRequestInfo(
        method="GET", url="https://example.invalid", status_code=status, latency_ms=1.0
    )


def _market(gid, tokens=(), *, question=None, condition=None):
    return {
        "id": gid,
        "conditionId": condition if condition is not None else f"0xc{gid}",
        "question": question if question is not None else f"Q{gid}",
        "active": "open",
        "outcomes": json.dumps(["Yes", "No"]),
        "clobTokenIds": json.dumps(list(tokens)),
        "endDate": "2026-12-31",
        "category": "Sports",
    }


def _book(token_id, *, bids=(("0.40", "10"),), asks=(("0.60", "5"),)):
    return {
        "asset_id": token_id,
        "bids": [{"price": p, "size": s} for p, s in bids],
        "asks": [{"price": p, "size": s} for p, s in asks],
        "tick_size": "0.01",
        "min_order_size": "1",
        "timestamp": "1700000000",
        "hash": "bookhash",
        "last_trade_price": "0.5",
    }


class WP164Client:
    def __init__(self, markets, books=None):
        self._m = markets
        self._books = books or {}

    def get_markets(self, limit=None):
        return AdapterResult(data=self._m, request_info=_request_info())

    def get_order_book_snapshot(self, token_id):
        return AdapterResult(data=self._books[token_id], request_info=_request_info())


class KeysetClient:
    """A fake GET-only keyset client. Records every call for loop/offset checks."""

    def __init__(self, markets, *, next_cursor=None, books=None, status=200,
                 markets_key="markets"):
        self._m = markets
        self._nc = next_cursor
        self._books = books or {}
        self._status = status
        self._markets_key = markets_key
        self.keyset_calls: list[tuple] = []
        self.book_calls: list[str] = []

    def get_markets_keyset(self, *, limit=100, after_cursor=None):
        self.keyset_calls.append((limit, after_cursor))
        data = {self._markets_key: self._m}
        if self._nc is not None:
            data["next_cursor"] = self._nc
        return AdapterResult(data=data, request_info=_request_info(self._status))

    def get_order_book_snapshot(self, token_id):
        self.book_calls.append(token_id)
        entry = self._books[token_id]
        if isinstance(entry, Exception):
            raise entry
        return AdapterResult(data=entry, request_info=_request_info())


class AllowGuard:
    def __init__(self):
        self.calls: list[str] = []

    def record_allowed(self, endpoint_key, *, now=None):
        self.calls.append(endpoint_key)
        return _Decision(True)


class DenyGuard:
    def __init__(self, deny_key):
        self._deny = deny_key
        self.calls: list[str] = []

    def record_allowed(self, endpoint_key, *, now=None):
        self.calls.append(endpoint_key)
        return _Decision(endpoint_key != self._deny)


class _Decision:
    def __init__(self, allowed):
        self.allowed = allowed


def _advancing_now():
    state = {"t": 0.0}

    def _next() -> float:
        state["t"] += 3600.0
        return state["t"]

    return _next


def _clock(day=15):
    return lambda: datetime.datetime(2026, 8, day, 12, 0, 0, tzinfo=datetime.UTC)


def _stores():
    directory = tempfile.mkdtemp()
    record_path = os.path.join(directory, "records.sqlite3")
    manifest_path = os.path.join(directory, "manifest.sqlite3")
    initialize_point_in_time_record_store(record_path)
    initialize_manifest_store(manifest_path)
    return record_path, manifest_path


def _scfg(**overrides) -> Cfg:
    base = dict(
        manifest_id=MANIFEST_ID,
        page_limit=5,
        after_cursor=None,
        order_books_limit=0,
        allow_network=False,
        allow_documented_unverified_keyset=False,
        **PROV,
    )
    base.update(overrides)
    return Cfg(**base)


def _seed(record_path, manifest_path, markets=None, books=None, *,
          markets_limit=2, order_books_limit=0, day=14):
    markets = markets if markets is not None else [_market("100", ["t1"]), _market("101", ["t2"])]
    result = populate_initial_polymarket_public_data(
        record_path,
        manifest_path,
        WP164Cfg(
            manifest_id=MANIFEST_ID,
            markets_limit=markets_limit,
            order_books_limit=order_books_limit,
            allow_network=True,
            **PROV,
        ),
        client=WP164Client(markets, books),
        guard=AllowGuard(),
        now_provider=_advancing_now(),
        utcnow_provider=_clock(day),
    )
    assert result.is_valid, result.error_codes
    return result


def _seeded(markets=None, books=None, **kw):
    record_path, manifest_path = _stores()
    _seed(record_path, manifest_path, markets, books, **kw)
    return record_path, manifest_path


def _capture(record_path, manifest_path, page, *, cfg=None, client=None,
             next_cursor=None, books=None, guard=None, day=15, **cfg_overrides):
    cfg = cfg or _scfg(
        allow_network=True, allow_documented_unverified_keyset=True, **cfg_overrides
    )
    if client is None:
        client = KeysetClient(page, next_cursor=next_cursor, books=books)
    return capture_scaled_polymarket_public_page(
        record_path,
        manifest_path,
        cfg,
        client=client,
        guard=guard or AllowGuard(),
        now_provider=_advancing_now(),
        utcnow_provider=_clock(day),
    ), client


def _record_ids(record_path):
    loaded = load_and_verify_point_in_time_record_store(record_path)
    assert loaded.is_valid
    return {r.envelope.record_version_id for r in loaded.snapshot.records}


def _adapter_rejected(codes):
    from src.data_layer.point_in_time_market_research.dataset_persistence_adapter import (
        DatasetPersistenceAdapterResult,
    )

    return DatasetPersistenceAdapterResult(
        is_valid=False, status="ADAPTER_REJECTED", error_codes=tuple(codes),
        upstream_error_codes=(), store_error_codes=(), warning_codes=(),
        dataset_reference=None, manifest_entry=None, store_status=None,
        human_review_required=False, advisory_only=True, no_execution_authority=True,
    )


# ── Public surface / posture ──────────────────────────────────────────────────


def test_public_constants_and_posture_are_exact() -> None:
    assert (
        scaled.POLYMARKET_SCALED_POPULATION_LABEL
        == "POLYMARKET_SCALABLE_KEYSET_LINEAGE_DELTA_POPULATION"
    )
    assert scaled.POLYMARKET_SCALED_POPULATION_POSTURE == (
        "MANUAL_ONE_PAGE_KEYSET_GET_ONLY_EXTERNAL_PARENT_COMMITTED_NO_TRADING_AUTHORITY"
    )
    assert scaled.POLYMARKET_SCALED_POPULATION_STATUSES == (
        "SCALED_DRY_RUN",
        "SCALED_PERSISTED_AND_REGISTERED",
        "SCALED_RECORDS_PERSISTED_REGISTRATION_FAILED",
        "SCALED_RECOVERED_REGISTRATION",
        "SCALED_ALREADY_REGISTERED",
        "SCALED_REJECTED",
    )


def test_package_exports_end_with_the_eight_wp166_symbols() -> None:
    assert pit.__all__[-8:] == (
        "POLYMARKET_SCALED_POPULATION_LABEL",
        "POLYMARKET_SCALED_POPULATION_POSTURE",
        "POLYMARKET_SCALED_POPULATION_STATUSES",
        "POLYMARKET_SCALED_POPULATION_ERROR_CODES",
        "PolymarketScaledPopulationConfig",
        "PolymarketScaledPopulationResult",
        "capture_scaled_polymarket_public_page",
        "recover_scaled_polymarket_public_registration",
    )
    assert all(getattr(pit, name) is getattr(scaled, name) for name in pit.__all__[-8:])


def test_result_and_config_are_frozen() -> None:
    import dataclasses

    result = scaled.capture_scaled_polymarket_public_page("x", "y", _scfg())
    assert result.advisory_only is True and result.no_execution_authority is True
    with pytest.raises(dataclasses.FrozenInstanceError):
        result.is_valid = True  # type: ignore[misc]


# ── Config boundary ───────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "override",
    [
        dict(page_limit=0),
        dict(page_limit=101),
        dict(page_limit=True),
        dict(order_books_limit=-1),
        dict(order_books_limit=21),
        dict(after_cursor=""),
        dict(after_cursor="  spaced  "),
        dict(after_cursor="line\nbreak"),
        dict(after_cursor="x" * 2049),
        dict(after_cursor=123),
        dict(allow_network="yes"),
        dict(manifest_id=""),
    ],
)
def test_config_boundary_rejects_invalid(override) -> None:
    result = capture_scaled_polymarket_public_page("x", "y", _scfg(**override))
    assert not result.is_valid
    assert result.error_codes == ("SCALED_INPUT_INVALID",)


def test_config_wrong_type_rejected() -> None:
    result = capture_scaled_polymarket_public_page("x", "y", object())
    assert result.error_codes == ("SCALED_INPUT_INVALID",)


# ── Dry run / double opt-in ───────────────────────────────────────────────────


def test_dry_run_makes_zero_network_calls() -> None:
    record_path, manifest_path = _seeded()
    guard = AllowGuard()
    result = capture_scaled_polymarket_public_page(
        record_path, manifest_path, _scfg(), guard=guard
    )
    assert result.is_valid and result.status == "SCALED_DRY_RUN"
    assert result.network_used is False
    assert result.prior_registered_unique_record_count == 2
    assert guard.calls == []


def test_double_opt_in_required_lone_allow_network_rejected() -> None:
    record_path, manifest_path = _seeded()
    client = KeysetClient([_market("102", ["t3"])])
    result = capture_scaled_polymarket_public_page(
        record_path, manifest_path, _scfg(allow_network=True), client=client
    )
    assert not result.is_valid
    assert result.error_codes == ("SCALED_KEYSET_OPT_IN_REQUIRED",)
    assert result.network_used is False
    assert client.keyset_calls == []


# ── One page, no loop, response boundary ──────────────────────────────────────


def test_single_keyset_page_no_cursor_loop() -> None:
    record_path, manifest_path = _seeded()
    result, client = _capture(
        record_path, manifest_path, [_market("102", ["t3"])], next_cursor="NEXT_PAGE"
    )
    assert result.is_valid and result.status == "SCALED_PERSISTED_AND_REGISTERED"
    # Exactly ONE keyset request; the request limit reflects page_limit, no cursor.
    assert client.keyset_calls == [(5, None)]
    assert result.next_cursor == "NEXT_PAGE"


def test_after_cursor_forwarded_next_cursor_returned() -> None:
    record_path, manifest_path = _seeded()
    result, client = _capture(
        record_path, manifest_path, [_market("102", ["t3"])],
        next_cursor="C2", after_cursor="C1",
    )
    assert result.is_valid
    assert client.keyset_calls == [(5, "C1")]
    assert result.after_cursor == "C1"
    assert result.next_cursor == "C2"


def test_missing_next_cursor_returns_none() -> None:
    record_path, manifest_path = _seeded()
    result, _ = _capture(record_path, manifest_path, [_market("102", ["t3"])])
    assert result.is_valid and result.next_cursor is None


@pytest.mark.parametrize(
    "client_kw",
    [
        dict(markets_key="items"),  # missing 'markets' key
        dict(next_cursor="bad\ncursor"),  # invalid cursor grammar
        dict(next_cursor="x" * 2049),  # cursor too long
    ],
)
def test_response_boundary_rejects_bad_wrapper(client_kw) -> None:
    record_path, manifest_path = _seeded()
    client = KeysetClient([_market("102", ["t3"])], **client_kw)
    result = capture_scaled_polymarket_public_page(
        record_path, manifest_path,
        _scfg(allow_network=True, allow_documented_unverified_keyset=True),
        client=client, guard=AllowGuard(), utcnow_provider=_clock(15),
    )
    assert not result.is_valid
    assert result.error_codes == ("SCALED_RESPONSE_INVALID",)
    assert result.network_used is True


def test_page_exceeding_page_limit_rejected() -> None:
    record_path, manifest_path = _seeded()
    # page_limit=2 but the response returns 3 markets.
    client = KeysetClient([_market("a", ["ta"]), _market("b", ["tb"]), _market("c", ["tc"])])
    result = capture_scaled_polymarket_public_page(
        record_path, manifest_path,
        _scfg(page_limit=2, allow_network=True, allow_documented_unverified_keyset=True),
        client=client, guard=AllowGuard(), utcnow_provider=_clock(15),
    )
    assert not result.is_valid and result.error_codes == ("SCALED_RESPONSE_INVALID",)


# ── Classification against the whole registered history ───────────────────────


def test_primary_duplicate_and_revision_classification() -> None:
    record_path, manifest_path = _seeded()  # seed markets 100, 101
    page = [
        _market("100", ["t1"]),  # unchanged -> EXACT_DUPLICATE
        _market("101", ["t2"], question="Q101 CHANGED"),  # -> SOURCE_REVISION
        _market("102", ["t3"]),  # new -> PRIMARY_ASSERTION
    ]
    result, _ = _capture(record_path, manifest_path, page)
    assert result.is_valid
    assert result.primary_assertion_count == 1
    assert result.exact_duplicate_count == 1
    assert result.source_revision_count == 1
    assert result.new_record_count == 3
    assert result.page_market_count == 3 and result.page_book_count == 0


def test_v2_reference_contains_only_current_records_with_external_parents() -> None:
    record_path, manifest_path = _seeded()
    page = [_market("100", ["t1"]), _market("102", ["t3"])]  # dup + new
    result, _ = _capture(record_path, manifest_path, page)
    assert result.is_valid
    snapshot = load_and_verify_manifest_store(manifest_path).snapshot
    ref = next(
        r for r in snapshot.dataset_references
        if r.dataset_snapshot_reference_id == result.dataset_snapshot_reference_id
    )
    assert ref.derivation_mode == "LINEAGE_DELTA_RECORD_BATCH"
    # Only the 2 current records are ordinary; the 1 prior parent is external.
    assert len(ref.ordinary_record_version_ids) == 2
    assert len(ref.external_parent_record_version_ids) == 1
    assert ref.created_from_manifest_entry_id is not None
    mat = materialize_dataset_snapshot_reference(record_path, ref)
    assert mat.is_valid
    assert mat.verification_mode == "LINEAGE_DELTA_PARENT_CONTEXT_RECOMPUTED"
    assert len(mat.ordinary_records) == 2 and len(mat.external_parent_records) == 1


def test_optional_books_captured_and_ordering_deterministic() -> None:
    record_path, manifest_path = _seeded(
        markets=[_market("100", ["t1"])], markets_limit=1
    )
    page = [_market("200", ["tokA", "tokB"])]
    books = {"tokA": _book("tokA"), "tokB": _book("tokB")}
    result, client = _capture(
        record_path, manifest_path, page, books=books, order_books_limit=5
    )
    assert result.is_valid, (result.error_codes, result.registration_error_codes)
    assert result.page_market_count == 1 and result.page_book_count == 2
    assert result.new_record_count == 3
    # Exactly one keyset page (limit reflects page_limit) then two book reads.
    assert client.keyset_calls == [(5, None)]
    assert sorted(client.book_calls) == ["tokA", "tokB"]


def test_book_failure_aborts_whole_page_without_persistence() -> None:
    record_path, manifest_path = _seeded(markets=[_market("100", ["t1"])], markets_limit=1)
    before = _record_ids(record_path)
    page = [_market("200", ["tokA"])]
    books = {"tokA": RuntimeError("boom")}
    client = KeysetClient(page, books=books)
    result = capture_scaled_polymarket_public_page(
        record_path, manifest_path,
        _scfg(order_books_limit=5, allow_network=True, allow_documented_unverified_keyset=True),
        client=client, guard=AllowGuard(), utcnow_provider=_clock(15),
    )
    assert not result.is_valid
    assert _record_ids(record_path) == before  # nothing persisted


# ── Identity drift ────────────────────────────────────────────────────────────


def test_identity_drift_rejected() -> None:
    record_path, manifest_path = _seeded(markets=[_market("100", ["t1"], condition="0xAAA")], markets_limit=1)
    # Same market id 100 but a different condition => different event id.
    page = [_market("100", ["t1"], condition="0xBBB")]
    result, _ = _capture(record_path, manifest_path, page)
    assert not result.is_valid and result.error_codes == ("SCALED_IDENTITY_DRIFT",)


# ── Physical history beyond 256 ───────────────────────────────────────────────


def test_physical_history_beyond_256_records() -> None:
    record_path, manifest_path = _seeded(markets=[_market("seed", ["ts"])], markets_limit=1)
    total = 1
    for page_index in range(3):
        page = [
            _market(f"p{page_index}_{i}", [f"tok{page_index}_{i}"]) for i in range(100)
        ]
        result, _ = _capture(
            record_path, manifest_path, page, page_limit=100, day=15 + page_index
        )
        assert result.is_valid, (result.status, result.error_codes)
        total += 100
    assert total == 301
    assert len(_record_ids(record_path)) == 301
    # The manifest holds only the seed + three delta registrations (well under 256).
    snapshot = load_and_verify_manifest_store(manifest_path).snapshot
    assert len(snapshot.manifest_entries) == 4
    assert len(snapshot.dataset_references) == 4
    # A converged dry-run confirms baseline equality at 301 registered records.
    dry = capture_scaled_polymarket_public_page(record_path, manifest_path, _scfg())
    assert dry.is_valid and dry.prior_registered_unique_record_count == 301


# ── Capacity gates (pre-network) ──────────────────────────────────────────────


def test_capacity_gate_blocks_before_network() -> None:
    record_path, manifest_path = _seeded()
    # A store near the WP163 horizon: force existing + page over 4096 by claiming a
    # huge page_limit is impossible (capped at 100), so instead assert the gate is
    # consulted by using a config whose page+existing cannot exceed 4096 here; the
    # dedicated gate test uses the manifest-entry ceiling via monkeypatching.
    guard = AllowGuard()
    # Monkeypatch the store horizon down to force the capacity rejection.
    original = scaled._MAX_STORE_RECORDS
    scaled._MAX_STORE_RECORDS = 2  # existing is already 2
    try:
        result = capture_scaled_polymarket_public_page(
            record_path, manifest_path,
            _scfg(allow_network=True, allow_documented_unverified_keyset=True),
            client=KeysetClient([_market("102", ["t3"])]), guard=guard,
            utcnow_provider=_clock(15),
        )
    finally:
        scaled._MAX_STORE_RECORDS = original
    assert not result.is_valid
    assert result.error_codes == ("SCALED_CAPACITY_EXCEEDED",)
    assert guard.calls == []  # no network consulted


# ── Append / registration ordering and recovery ───────────────────────────────


def _failing_capture(record_path, manifest_path, page, *, cursor=None, day=15):
    real = scaled.persist_lineage_delta_record_batch_snapshot
    scaled.persist_lineage_delta_record_batch_snapshot = lambda *a, **k: _adapter_rejected(())
    try:
        return capture_scaled_polymarket_public_page(
            record_path, manifest_path,
            _scfg(after_cursor=cursor, allow_network=True, allow_documented_unverified_keyset=True),
            client=KeysetClient(page), guard=AllowGuard(), utcnow_provider=_clock(day),
        )
    finally:
        scaled.persist_lineage_delta_record_batch_snapshot = real


@pytest.mark.parametrize(
    "adapter",
    [
        lambda *a, **k: _adapter_rejected(("ADAPTER_STORE_APPEND_FAILED",)),
        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("adapter exploded")),
        lambda *a, **k: object(),
    ],
)
def test_registration_failure_leaves_records_and_requires_recovery(adapter) -> None:
    record_path, manifest_path = _seeded()
    before = _record_ids(record_path)
    real = scaled.persist_lineage_delta_record_batch_snapshot
    scaled.persist_lineage_delta_record_batch_snapshot = adapter
    try:
        result = capture_scaled_polymarket_public_page(
            record_path, manifest_path,
            _scfg(allow_network=True, allow_documented_unverified_keyset=True),
            client=KeysetClient([_market("102", ["t3"])], next_cursor="KEEP"),
            guard=AllowGuard(), utcnow_provider=_clock(15),
        )
    finally:
        scaled.persist_lineage_delta_record_batch_snapshot = real
    assert result.status == "SCALED_RECORDS_PERSISTED_REGISTRATION_FAILED"
    assert result.error_codes == ("SCALED_REGISTRATION_FAILED",)
    assert result.recovery_required is True
    assert result.network_used is True
    assert result.next_cursor == "KEEP"  # validated cursor preserved
    assert result.dataset_snapshot_reference_id is None
    # The new records are committed and never deleted.
    assert len(_record_ids(record_path)) == len(before) + 1


def test_registration_diagnostics_are_closed_vocabulary_only() -> None:
    record_path, manifest_path = _seeded()
    leaky = _adapter_rejected(("ADAPTER_BATCH_INVALID", "sneaky/path", 42))
    real = scaled.persist_lineage_delta_record_batch_snapshot
    scaled.persist_lineage_delta_record_batch_snapshot = lambda *a, **k: leaky
    try:
        result = capture_scaled_polymarket_public_page(
            record_path, manifest_path,
            _scfg(allow_network=True, allow_documented_unverified_keyset=True),
            client=KeysetClient([_market("102", ["t3"])]), guard=AllowGuard(),
            utcnow_provider=_clock(15),
        )
    finally:
        scaled.persist_lineage_delta_record_batch_snapshot = real
    assert result.registration_error_codes == ("ADAPTER_BATCH_INVALID",)
    assert "sneaky/path" not in result.registration_error_codes


def test_offline_recovery_reregisters_one_committed_page() -> None:
    record_path, manifest_path = _seeded()
    fail = _failing_capture(record_path, manifest_path, [_market("102", ["t3"])], cursor="CX")
    assert fail.status == "SCALED_RECORDS_PERSISTED_REGISTRATION_FAILED"
    recovered = recover_scaled_polymarket_public_registration(
        record_path, manifest_path, _scfg(after_cursor="CX")
    )
    assert recovered.is_valid
    assert recovered.status == "SCALED_RECOVERED_REGISTRATION"
    assert recovered.new_record_count == 1
    assert recovered.network_used is False
    # Now converged.
    again = recover_scaled_polymarket_public_registration(
        record_path, manifest_path, _scfg(after_cursor="CX")
    )
    assert again.status == "SCALED_ALREADY_REGISTERED"


def test_recovery_no_op_when_already_converged() -> None:
    record_path, manifest_path = _seeded()
    result = recover_scaled_polymarket_public_registration(
        record_path, manifest_path, _scfg()
    )
    assert result.is_valid and result.status == "SCALED_ALREADY_REGISTERED"
    assert result.network_used is False


def test_recovery_wrong_after_cursor_rejected() -> None:
    record_path, manifest_path = _seeded()
    _failing_capture(record_path, manifest_path, [_market("102", ["t3"])], cursor="RIGHT")
    wrong = recover_scaled_polymarket_public_registration(
        record_path, manifest_path, _scfg(after_cursor="WRONG")
    )
    assert not wrong.is_valid and wrong.error_codes == ("SCALED_RECOVERY_INVALID",)
    right = recover_scaled_polymarket_public_registration(
        record_path, manifest_path, _scfg(after_cursor="RIGHT")
    )
    assert right.status == "SCALED_RECOVERED_REGISTRATION"


def test_recovery_multiple_orphan_pages_rejected() -> None:
    record_path, manifest_path = _seeded()
    # First orphan page via a failing capture (market 102).
    _failing_capture(record_path, manifest_path, [_market("102", ["t3"])], cursor="C1", day=15)
    # Build a SECOND, distinct genuine orphan page in an independent seeded store
    # (a new capture on this store would be blocked at baseline), then inject its
    # new primary record into the real store so the suffix spans two page identities.
    extra = _orphan_records_for([_market("103", ["t4"])], cursor="C2", day=16)
    assert extra
    appended = append_point_in_time_records(record_path, extra)
    assert appended.is_valid, appended.error_codes
    multi = recover_scaled_polymarket_public_registration(
        record_path, manifest_path, _scfg(after_cursor="C1")
    )
    assert not multi.is_valid and multi.error_codes == ("SCALED_RECOVERY_INVALID",)


def _orphan_records_for(page, *, cursor, day):
    """Return the NEW primary records a scaled page would produce, from a fresh store."""

    fresh_record, fresh_manifest = _seeded()
    base = _record_ids(fresh_record)
    _failing_capture(fresh_record, fresh_manifest, page, cursor=cursor, day=day)
    loaded = load_and_verify_point_in_time_record_store(fresh_record)
    return [
        rec
        for rec in loaded.snapshot.records
        if rec.envelope.record_version_id not in base
    ]


# ── Baseline convergence ──────────────────────────────────────────────────────


def test_strict_superset_blocks_new_capture_and_advises_recovery() -> None:
    record_path, manifest_path = _seeded()
    _failing_capture(record_path, manifest_path, [_market("102", ["t3"])], cursor="CX")
    result, _ = _capture(record_path, manifest_path, [_market("999", ["t9"])])
    assert not result.is_valid
    assert result.error_codes == ("SCALED_BASELINE_UNREGISTERED",)
    assert result.recovery_required is True
    assert result.network_used is False


# ── Security / no-echo / no-scheduler ─────────────────────────────────────────


def test_source_has_no_scheduler_retry_sleep_auth_or_trading_terms() -> None:
    with open(SCALED_SRC, "r", encoding="utf-8") as handle:
        source = handle.read()
    # Precise code-level tokens that would signal scheduling, retry loops, sleeps,
    # authenticated network, or trading (prose like "no scheduler" is unaffected).
    for banned in (
        "time.sleep",
        "asyncio",
        "threading.",
        "subprocess",
        "requests.",
        "place_order",
        "private_key",
        "api_key",
        "\ndef get_markets(",  # only the keyset call is used
    ):
        assert banned not in source, banned
    # No automatic cursor loop: get_markets_keyset is called exactly once in source.
    assert source.count("get_markets_keyset(") == 1


def test_no_url_path_or_cursor_echo_on_rejection() -> None:
    record_path, manifest_path = _seeded()
    client = KeysetClient([_market("102", ["t3"])], next_cursor="SECRET_CURSOR", markets_key="items")
    result = capture_scaled_polymarket_public_page(
        record_path, manifest_path,
        _scfg(allow_network=True, allow_documented_unverified_keyset=True),
        client=client, guard=AllowGuard(), utcnow_provider=_clock(15),
    )
    assert not result.is_valid
    rendered = repr(result)
    assert "SECRET_CURSOR" not in rendered
    assert "/markets/keyset" not in rendered
    assert result.next_cursor is None


def test_module_imports_no_network_or_execution_dependency() -> None:
    with open(SCALED_SRC, "r", encoding="utf-8") as handle:
        tree = ast.parse(handle.read())
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)
    for banned in ("urllib", "socket", "http", "requests", "subprocess", "os.environ"):
        assert not any(name.startswith(banned) for name in imported), banned
