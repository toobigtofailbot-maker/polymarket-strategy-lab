"""Focused tests for the WP165 bounded incremental cumulative-lineage capture.

These tests never touch the network. Every network-capable path is exercised with
an injected fake GET-only client, an injected guard, and a fixed clock. The prior
registered baseline is always produced by the merged WP164 seed coordinator so the
cross-run lineage is proven against a genuine committed dataset.
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
    polymarket_incremental_population as inc,
)
from src.data_layer.point_in_time_market_research import (
    polymarket_public_population as pop,
)
from src.data_layer.point_in_time_market_research import (
    PolymarketPublicPopulationConfig as Cfg,
    append_manifest_store_batch,
    append_point_in_time_records,
    initialize_manifest_store,
    initialize_point_in_time_record_store,
    load_and_verify_manifest_store,
    load_and_verify_point_in_time_record_store,
    populate_initial_polymarket_public_data,
    capture_incremental_polymarket_public_data,
    recover_incremental_polymarket_public_registration,
    validate_record_batch,
)
from src.data_layer.point_in_time_market_research import (
    dataset_persistence_adapter as _dpa,
)


# ── Fixtures / injection seams (never touch the network) ──────────────────────


def _config(**overrides) -> Cfg:
    base = dict(
        manifest_id="manifest:polymarket:test",
        parameter_set_id="params:v1",
        normalizer_version="norm:v1",
        validator_version="val:v1",
        markets_limit=2,
        order_books_limit=0,
        allow_network=False,
    )
    base.update(overrides)
    return Cfg(**base)


def _request_info(status: int = 200) -> ReadOnlyRequestInfo:
    return ReadOnlyRequestInfo(
        method="GET", url="https://example.invalid", status_code=status, latency_ms=1.0
    )


def _market(gamma_id: str, tokens, *, condition=None, question=None, outcomes=None):
    return {
        "id": gamma_id,
        "conditionId": condition if condition is not None else f"0xcond{gamma_id}",
        "question": question if question is not None else f"Question {gamma_id}",
        "active": "open",
        "outcomes": json.dumps(outcomes if outcomes is not None else ["Yes", "No"]),
        "clobTokenIds": json.dumps(list(tokens)),
        "endDate": "2026-12-31",
        "category": "Sports",
    }


def _book(token_id, *, bids=(("0.40", "10"),), asks=(("0.60", "5"),), asset_id=...):
    data = {
        "asset_id": token_id if asset_id is ... else asset_id,
        "bids": [{"price": p, "size": s} for p, s in bids],
        "asks": [{"price": p, "size": s} for p, s in asks],
        "tick_size": "0.01",
        "min_order_size": "1",
        "timestamp": "1700000000",
        "hash": "bookhash",
        "last_trade_price": "0.5",
    }
    if asset_id is None:
        data.pop("asset_id")
    return data


class FakeClient:
    def __init__(self, markets, books=None, *, markets_status=200):
        self._markets = markets
        self._books = books or {}
        self._markets_status = markets_status
        self.markets_calls = 0
        self.book_calls: list[str] = []

    def get_markets(self, limit=None):
        self.markets_calls += 1
        return AdapterResult(
            data=self._markets, request_info=_request_info(self._markets_status)
        )

    def get_order_book_snapshot(self, token_id):
        self.book_calls.append(token_id)
        entry = self._books[token_id]
        if isinstance(entry, Exception):
            raise entry
        data, status = entry if isinstance(entry, tuple) else (entry, 200)
        return AdapterResult(data=data, request_info=_request_info(status))


class RaisingClient:
    def __init__(self, exc):
        self._exc = exc
        self.markets_calls = 0

    def get_markets(self, limit=None):
        self.markets_calls += 1
        raise self._exc

    def get_order_book_snapshot(self, token_id):  # pragma: no cover - never reached
        raise AssertionError("order book must not be fetched")


class DenyGuard:
    """Deny a specific endpoint; allow all others."""

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


def _stores():
    directory = tempfile.mkdtemp()
    record_path = os.path.join(directory, "records.sqlite3")
    manifest_path = os.path.join(directory, "manifest.sqlite3")
    initialize_point_in_time_record_store(record_path)
    initialize_manifest_store(manifest_path)
    return record_path, manifest_path


def _clock(day=14):
    return lambda: datetime.datetime(2026, 8, day, 12, 0, 0, tzinfo=datetime.UTC)


def _seed(record_path, manifest_path, markets=None, books=None, *, markets_limit=1,
          order_books_limit=0, day=14):
    """Populate a genuine registered WP164 baseline via the merged seed coordinator."""

    client = FakeClient(
        markets if markets is not None else [_market("100", ["tok1"])], books
    )
    result = populate_initial_polymarket_public_data(
        record_path,
        manifest_path,
        _config(
            allow_network=True,
            markets_limit=markets_limit,
            order_books_limit=order_books_limit,
        ),
        client=client,
        now_provider=_advancing_now(),
        utcnow_provider=_clock(day),
    )
    assert result.is_valid, result.error_codes
    return result


def _seeded(markets=None, books=None, **kw):
    record_path, manifest_path = _stores()
    _seed(record_path, manifest_path, markets, books, **kw)
    return record_path, manifest_path


def _capture(record_path, manifest_path, markets, books=None, *, markets_limit=1,
             order_books_limit=0, day=15, client=None, guard=None):
    if client is None:
        client = FakeClient(markets, books)
    return capture_incremental_polymarket_public_data(
        record_path,
        manifest_path,
        _config(
            allow_network=True,
            markets_limit=markets_limit,
            order_books_limit=order_books_limit,
        ),
        client=client,
        guard=guard,
        now_provider=_advancing_now(),
        utcnow_provider=_clock(day),
    )


def _store_records(record_path):
    return load_and_verify_point_in_time_record_store(record_path).snapshot.records


def _manifest_snapshot(manifest_path):
    return load_and_verify_manifest_store(manifest_path).snapshot


# ── Public surface ────────────────────────────────────────────────────────────


def test_locked_labels_and_vocabularies_are_exact():
    assert (
        inc.POLYMARKET_INCREMENTAL_POPULATION_LABEL
        == "POLYMARKET_BOUNDED_CUMULATIVE_INCREMENTAL_POINT_IN_TIME_POPULATION"
    )
    assert (
        inc.POLYMARKET_INCREMENTAL_POPULATION_POSTURE
        == "MANUAL_GET_ONLY_CUMULATIVE_256_RECORD_CROSS_RUN_LINEAGE_NO_TRADING_AUTHORITY"
    )
    assert inc.POLYMARKET_INCREMENTAL_POPULATION_STATUSES == (
        "INCREMENTAL_DRY_RUN",
        "INCREMENTAL_PERSISTED_AND_REGISTERED",
        "INCREMENTAL_RECORDS_PERSISTED_REGISTRATION_FAILED",
        "INCREMENTAL_RECOVERED_REGISTRATION",
        "INCREMENTAL_ALREADY_REGISTERED",
        "INCREMENTAL_REJECTED",
    )
    assert inc.POLYMARKET_INCREMENTAL_POPULATION_ERROR_CODES == (
        "INCREMENTAL_INPUT_INVALID",
        "INCREMENTAL_RECORD_STORE_INVALID",
        "INCREMENTAL_MANIFEST_STORE_INVALID",
        "INCREMENTAL_BASELINE_UNREGISTERED",
        "INCREMENTAL_BASELINE_REFERENCE_INVALID",
        "INCREMENTAL_PROVENANCE_MISMATCH",
        "INCREMENTAL_CAPACITY_EXCEEDED",
        "INCREMENTAL_POLICY_INVALID",
        "INCREMENTAL_GUARD_DENIED",
        "INCREMENTAL_FETCH_FAILED",
        "INCREMENTAL_RESPONSE_INVALID",
        "INCREMENTAL_IDENTITY_DRIFT",
        "INCREMENTAL_BUILD_FAILED",
        "INCREMENTAL_BATCH_INVALID",
        "INCREMENTAL_RECORD_APPEND_FAILED",
        "INCREMENTAL_REGISTRATION_FAILED",
        "INCREMENTAL_RECOVERY_INVALID",
        "INCREMENTAL_UNEXPECTED_ERROR",
    )


def test_result_is_frozen():
    record_path, manifest_path = _seeded()
    result = capture_incremental_polymarket_public_data(
        record_path, manifest_path, _config()
    )
    with pytest.raises(Exception):
        result.status = "x"  # type: ignore[misc]
    assert result.advisory_only is True
    assert result.no_execution_authority is True


def test_package_exports_contain_the_seven_wp165_symbols_as_a_block():
    # WP166 appended its own exports after WP165, so the WP165 block is no longer
    # the package tail; it remains a future-safe contiguous seven-symbol block.
    start = pit.__all__.index("POLYMARKET_INCREMENTAL_POPULATION_LABEL")
    block = pit.__all__[start : start + 7]
    assert block == (
        "POLYMARKET_INCREMENTAL_POPULATION_LABEL",
        "POLYMARKET_INCREMENTAL_POPULATION_POSTURE",
        "POLYMARKET_INCREMENTAL_POPULATION_STATUSES",
        "POLYMARKET_INCREMENTAL_POPULATION_ERROR_CODES",
        "PolymarketIncrementalPopulationResult",
        "capture_incremental_polymarket_public_data",
        "recover_incremental_polymarket_public_registration",
    )
    assert all(getattr(pit, name) is getattr(inc, name) for name in block)


def test_incremental_reuses_the_exact_wp164_config():
    assert inc.PolymarketPublicPopulationConfig is pop.PolymarketPublicPopulationConfig


# ── Dry run ───────────────────────────────────────────────────────────────────


def test_default_dry_run_makes_no_network_call_and_no_write():
    record_path, manifest_path = _seeded()
    before_records = _store_records(record_path)
    before_entries = _manifest_snapshot(manifest_path).manifest_entries
    client = FakeClient([_market("200", ["tok9"])])
    result = capture_incremental_polymarket_public_data(
        record_path, manifest_path, _config(markets_limit=2), client=client
    )
    assert result.is_valid
    assert result.status == "INCREMENTAL_DRY_RUN"
    assert result.network_used is False
    assert result.recovery_required is False
    assert result.prior_registered_record_count == 1
    assert result.cumulative_record_count == 1
    assert result.new_record_count == 0
    assert client.markets_calls == 0
    assert _store_records(record_path) == before_records
    assert _manifest_snapshot(manifest_path).manifest_entries == before_entries


# ── Baseline preconditions before any network ────────────────────────────────


def test_empty_record_store_rejected_without_network():
    record_path, manifest_path = _stores()
    client = FakeClient([_market("100", ["tok1"])])
    result = _capture(record_path, manifest_path, [_market("100", ["tok1"])], client=client)
    assert not result.is_valid
    assert result.error_codes == ("INCREMENTAL_RECORD_STORE_INVALID",)
    assert client.markets_calls == 0
    assert result.network_used is False


def test_missing_record_store_rejected_without_network():
    directory = tempfile.mkdtemp()
    record_path = os.path.join(directory, "missing.sqlite3")
    manifest_path = os.path.join(directory, "manifest.sqlite3")
    initialize_manifest_store(manifest_path)
    client = FakeClient([_market("100", ["tok1"])])
    result = _capture(record_path, manifest_path, [_market("100", ["tok1"])], client=client)
    assert result.error_codes == ("INCREMENTAL_RECORD_STORE_INVALID",)
    assert client.markets_calls == 0


def test_missing_manifest_store_rejected_without_network():
    record_path, manifest_path = _seeded()
    other = os.path.join(tempfile.mkdtemp(), "absent.sqlite3")
    client = FakeClient([_market("100", ["tok1"])])
    result = _capture(record_path, other, [_market("100", ["tok1"])], client=client)
    assert result.error_codes == ("INCREMENTAL_MANIFEST_STORE_INVALID",)
    assert client.markets_calls == 0


def test_unregistered_manifest_rejected_without_network():
    # A record store populated but with a fresh empty manifest: no registered
    # baseline reference exists at all.
    record_path, manifest_path = _stores()
    _seed(record_path, manifest_path)
    fresh_manifest = os.path.join(tempfile.mkdtemp(), "empty.sqlite3")
    initialize_manifest_store(fresh_manifest)
    client = FakeClient([_market("100", ["tok1"])])
    result = _capture(record_path, fresh_manifest, [_market("100", ["tok1"])], client=client)
    assert result.error_codes == ("INCREMENTAL_MANIFEST_STORE_INVALID",)
    assert client.markets_calls == 0


def test_store_manifest_divergence_rejected_without_network():
    # Two independent seeds produce two stores/manifests. Pairing store A with
    # manifest B is a store/reference divergence and must never fetch.
    record_a, manifest_a = _seeded([_market("100", ["a"])])
    record_b, manifest_b = _seeded([_market("777", ["z"])])
    client = FakeClient([_market("100", ["a"])])
    result = _capture(record_a, manifest_b, [_market("100", ["a"])], client=client)
    assert not result.is_valid
    assert result.error_codes == ("INCREMENTAL_BASELINE_REFERENCE_INVALID",)
    assert client.markets_calls == 0


def test_forged_strict_superset_blocks_network_and_is_not_recoverable():
    # An arbitrary WP156-looking record that is not a genuine failed WP165 run is
    # still blocked before any network, but recovery_required is False because the
    # difference could never be one genuine incremental run.
    record_path, manifest_path = _seeded()
    extra = _seed_extra_record(record_path)
    append_point_in_time_records(record_path, (extra,))
    client = FakeClient([_market("100", ["tok1"])])
    result = _capture(record_path, manifest_path, [_market("100", ["tok1"])], client=client)
    assert not result.is_valid
    assert result.error_codes == ("INCREMENTAL_BASELINE_UNREGISTERED",)
    assert result.recovery_required is False
    assert client.markets_calls == 0
    assert result.network_used is False


def test_genuine_failed_run_strict_superset_is_recoverable():
    record_path, manifest_path = _seeded()
    # A genuine failed-registration run leaves a recoverable orphan suffix.
    real = inc.persist_validated_record_batch_snapshot
    inc.persist_validated_record_batch_snapshot = lambda *a, **k: _adapter_rejected(())
    try:
        _capture(record_path, manifest_path, [_market("200", ["tok2"])])
    finally:
        inc.persist_validated_record_batch_snapshot = real
    client = FakeClient([_market("300", ["tok3"])])
    result = _capture(record_path, manifest_path, [_market("300", ["tok3"])], client=client, day=17)
    assert result.error_codes == ("INCREMENTAL_BASELINE_UNREGISTERED",)
    assert result.recovery_required is True
    assert client.markets_calls == 0
    assert result.network_used is False


def test_two_orphan_batches_strict_superset_is_not_recoverable():
    record_path, manifest_path = _seeded()
    orphan_a = _forge_gamma("501", ["t501"], snap="a" * 64, batch="a" * 64,
                            captured="2026-08-21T00:00:00Z")
    orphan_b = _forge_gamma("502", ["t502"], snap="b" * 64, batch="b" * 64,
                            captured="2026-08-22T00:00:00Z")
    append_point_in_time_records(record_path, (orphan_a, orphan_b))
    client = FakeClient([_market("100", ["tok1"])])
    result = _capture(record_path, manifest_path, [_market("100", ["tok1"])], client=client)
    assert result.error_codes == ("INCREMENTAL_BASELINE_UNREGISTERED",)
    assert result.recovery_required is False
    assert client.markets_calls == 0


def test_mixed_provenance_store_rejected_without_network():
    record_path, manifest_path = _seeded()
    client = FakeClient([_market("100", ["tok1"])])
    # A config whose parameter set differs from the committed dataset provenance.
    result = capture_incremental_polymarket_public_data(
        record_path,
        manifest_path,
        _config(allow_network=True, parameter_set_id="params:OTHER"),
        client=client,
        utcnow_provider=_clock(15),
    )
    assert result.error_codes == ("INCREMENTAL_PROVENANCE_MISMATCH",)
    assert client.markets_calls == 0


def _seed_extra_record(record_path):
    """A second genuine WP164-shaped PRIMARY_ASSERTION record for orphan tests."""

    payload = {
        "question_text": "Q",
        "market_status": "open",
        "outcome_labels": ["Yes", "No"],
        "condition_id": "0xcond200",
        "token_ids": ["tok2"],
        "resolution_date": None,
        "category": None,
        "raw_field_names": ["id"],
    }
    snap = "snapshot:sha256:" + "a" * 64
    batch = "ingest:sha256:" + "b" * 64
    return pop._build_gamma_record(
        {
            "market_id": "market:polymarket:200",
            "event_id": "event:polymarket:0xcond200",
            "payload": payload,
        },
        snapshot_id=snap,
        ingestion_batch_id=batch,
        captured_at_utc="2026-08-20T00:00:00Z",
        config=_config(),
    )


_ORPHAN_SNAP = "snapshot:sha256:" + "c" * 64
_ORPHAN_BATCH = "ingest:sha256:" + "c" * 64
_ORPHAN_TIME = "2026-08-20T00:00:00Z"


def _clob_payload_dict():
    return {
        "bids": [{"price": "0.40", "size": "10"}],
        "asks": [{"price": "0.60", "size": "5"}],
        "tick_size": "0.01",
        "minimum_order_size": "1",
        "clob_timestamp": None,
        "book_hash": None,
        "last_trade_price": None,
        "raw_field_names": ["asks", "bids"],
    }


def _forge_gamma(gid, tokens, *, snap=None, batch=None, captured=_ORPHAN_TIME):
    """A structurally genuine WP164-shaped Gamma record with caller-chosen ids."""

    snapshot_id = ("snapshot:sha256:" + snap) if snap else _ORPHAN_SNAP
    batch_id = ("ingest:sha256:" + batch) if batch else _ORPHAN_BATCH
    payload = {
        "question_text": "Q",
        "market_status": "open",
        "outcome_labels": ["Yes", "No"],
        "condition_id": "0xc" + gid,
        "token_ids": list(tokens),
        "resolution_date": None,
        "category": None,
        "raw_field_names": ["id"],
    }
    return pop._build_gamma_record(
        {
            "market_id": "market:polymarket:" + gid,
            "event_id": "event:polymarket:0xc" + gid,
            "payload": payload,
        },
        snapshot_id=snapshot_id,
        ingestion_batch_id=batch_id,
        captured_at_utc=captured,
        config=_config(),
    )


def _forge_book(market_gid, raw_token, *, snap=None, batch=None, captured=_ORPHAN_TIME):
    """A structurally genuine WP164-shaped order-book record parented to ``market_gid``."""

    snapshot_id = ("snapshot:sha256:" + snap) if snap else _ORPHAN_SNAP
    batch_id = ("ingest:sha256:" + batch) if batch else _ORPHAN_BATCH
    parent = {
        "market_id": "market:polymarket:" + market_gid,
        "event_id": "event:polymarket:0xc" + market_gid,
    }
    return pop._build_order_book_record(
        parent,
        raw_token,
        _clob_payload_dict(),
        snapshot_id=snapshot_id,
        ingestion_batch_id=batch_id,
        captured_at_utc=captured,
        config=_config(),
    )


# ── Capacity before network ──────────────────────────────────────────────────


def test_capacity_guard_helper_rejects_over_256():
    with pytest.raises(inc._IncrementalReject) as excinfo:
        inc._require_capacity(240, 25, 20)
    assert excinfo.value.code == "INCREMENTAL_CAPACITY_EXCEEDED"


def test_worst_case_capacity_exceeded_before_any_client_call():
    record_path, manifest_path = _seeded()
    # Fill the store to a point where existing + bounded markets/books > 256.
    filler = _bulk_records(record_path, manifest_path, target=250)
    client = FakeClient([_market("100", ["tok1"])])
    result = capture_incremental_polymarket_public_data(
        record_path,
        manifest_path,
        _config(allow_network=True, markets_limit=25, order_books_limit=20),
        client=client,
        utcnow_provider=_clock(20),
    )
    assert result.error_codes == ("INCREMENTAL_CAPACITY_EXCEEDED",)
    assert client.markets_calls == 0
    assert filler >= 250


def _bulk_records(record_path, manifest_path, *, target):
    """Grow a registered baseline to ``target`` records via repeated captures.

    Each run stays within the 256 cumulative cap by only requesting as many new
    markets as remain to reach ``target``.
    """

    day = 15
    made = len(_store_records(record_path))
    market_id = 1000
    while made < target:
        count = min(24, target - made)
        markets = [
            _market(str(market_id + i), [f"tk{market_id + i}"]) for i in range(count)
        ]
        result = _capture(
            record_path, manifest_path, markets, markets_limit=count, day=day
        )
        assert result.is_valid, result.error_codes
        made = result.cumulative_record_count
        market_id += count
        day += 1
    return made


# ── Classification: Gamma ────────────────────────────────────────────────────


def test_new_gamma_market_is_primary_assertion():
    record_path, manifest_path = _seeded()
    result = _capture(record_path, manifest_path, [_market("200", ["tok2"])])
    assert result.is_valid
    assert result.status == "INCREMENTAL_PERSISTED_AND_REGISTERED"
    assert (result.primary_assertion_count, result.exact_duplicate_count,
            result.source_revision_count) == (1, 0, 0)
    assert result.new_record_count == 1
    assert result.cumulative_record_count == 2


def test_unchanged_gamma_is_exact_duplicate_with_exact_parent():
    record_path, manifest_path = _seeded()
    prior = _store_records(record_path)[0]
    result = _capture(record_path, manifest_path, [_market("100", ["tok1"])])
    assert result.is_valid
    assert (result.primary_assertion_count, result.exact_duplicate_count,
            result.source_revision_count) == (0, 1, 0)
    new = [
        r for r in _store_records(record_path)
        if r.envelope.record_version_id != prior.envelope.record_version_id
    ]
    assert len(new) == 1
    dup = new[0]
    assert dup.envelope.classification == "EXACT_DUPLICATE"
    assert dup.envelope.lineage_parent_ids == (prior.envelope.record_version_id,)
    assert dup.envelope.supersedes_record_version_id is None
    assert dup.envelope.canonical_payload_sha256 == prior.envelope.canonical_payload_sha256


def test_changed_gamma_is_source_revision_with_exact_parent_and_supersedes():
    record_path, manifest_path = _seeded()
    prior = _store_records(record_path)[0]
    result = _capture(
        record_path, manifest_path, [_market("100", ["tok1"], question="CHANGED")]
    )
    assert result.is_valid
    assert (result.primary_assertion_count, result.exact_duplicate_count,
            result.source_revision_count) == (0, 0, 1)
    new = [
        r for r in _store_records(record_path)
        if r.envelope.record_version_id != prior.envelope.record_version_id
    ]
    assert len(new) == 1
    rev = new[0]
    assert rev.envelope.classification == "SOURCE_REVISION"
    assert rev.envelope.lineage_parent_ids == (prior.envelope.record_version_id,)
    assert rev.envelope.supersedes_record_version_id == prior.envelope.record_version_id
    assert rev.envelope.canonical_payload_sha256 != prior.envelope.canonical_payload_sha256


def test_classification_counts_sum_to_new_record_count():
    record_path, manifest_path = _seeded(
        [_market("100", ["tok1"]), _market("101", ["tok2"])], markets_limit=2
    )
    # Unchanged 100, changed 101, brand-new 102.
    result = _capture(
        record_path,
        manifest_path,
        [
            _market("100", ["tok1"]),
            _market("101", ["tok2"], question="CHANGED"),
            _market("102", ["tok3"]),
        ],
        markets_limit=3,
    )
    assert result.is_valid
    assert result.primary_assertion_count == 1
    assert result.exact_duplicate_count == 1
    assert result.source_revision_count == 1
    total = (result.primary_assertion_count + result.exact_duplicate_count
             + result.source_revision_count)
    assert total == result.new_record_count == 3


# ── Classification: order books ──────────────────────────────────────────────


def test_new_unchanged_and_changed_order_book_lineage():
    record_path, manifest_path = _seeded(
        [_market("100", ["tok1"])], {"tok1": _book("tok1")},
        markets_limit=1, order_books_limit=1,
    )
    priors = {r.token_id: r for r in _store_records(record_path) if r.token_id}
    prior_book = priors["token:polymarket:tok1"]
    # Unchanged book -> EXACT_DUPLICATE; the gamma parent is also unchanged.
    result = _capture(
        record_path, manifest_path, [_market("100", ["tok1"])], {"tok1": _book("tok1")},
        markets_limit=1, order_books_limit=1,
    )
    assert result.is_valid
    assert result.exact_duplicate_count == 2
    # Changed book -> SOURCE_REVISION on the book.
    result2 = _capture(
        record_path, manifest_path, [_market("100", ["tok1"])],
        {"tok1": _book("tok1", bids=(("0.55", "3"),))},
        markets_limit=1, order_books_limit=1, day=16,
    )
    assert result2.is_valid
    assert result2.source_revision_count == 1
    revised = [
        r for r in _store_records(record_path)
        if r.token_id == "token:polymarket:tok1"
        and r.envelope.classification == "SOURCE_REVISION"
    ]
    assert len(revised) == 1
    # The revision supersedes the LATEST prior book (the unchanged EXACT_DUPLICATE
    # captured in the middle), never the original seed record.
    book_history = [
        r for r in _store_records(record_path)
        if r.token_id == "token:polymarket:tok1"
        and r.envelope.classification != "SOURCE_REVISION"
    ]
    latest_prior = max(
        book_history,
        key=lambda r: (r.envelope.ingestion_time, r.envelope.observed_time,
                       r.envelope.record_version_id),
    )
    assert revised[0].envelope.supersedes_record_version_id == (
        latest_prior.envelope.record_version_id
    )
    assert prior_book.envelope.record_version_id != latest_prior.envelope.record_version_id


# ── Identity drift ───────────────────────────────────────────────────────────


def test_changed_event_identity_rejected():
    record_path, manifest_path = _seeded([_market("100", ["tok1"])])
    drifted = _market("100", ["tok1"], condition="0xTOTALLYDIFFERENT")
    client = FakeClient([drifted])
    result = _capture(record_path, manifest_path, [drifted], client=client)
    assert not result.is_valid
    assert result.error_codes == ("INCREMENTAL_IDENTITY_DRIFT",)
    # Nothing persisted.
    assert len(_store_records(record_path)) == 1


def test_token_moved_market_rejected():
    record_path, manifest_path = _seeded(
        [_market("100", ["tok1"])], {"tok1": _book("tok1")},
        markets_limit=1, order_books_limit=1,
    )
    # Same raw token under a different market id.
    result = _capture(
        record_path, manifest_path, [_market("999", ["tok1"])], {"tok1": _book("tok1")},
        markets_limit=1, order_books_limit=1,
    )
    assert not result.is_valid
    assert result.error_codes == ("INCREMENTAL_IDENTITY_DRIFT",)


def test_latest_parent_chosen_across_multiple_history_versions():
    record_path, manifest_path = _seeded([_market("100", ["tok1"])])
    v1 = _store_records(record_path)[0]
    # First revision (v2 supersedes v1).
    r2 = _capture(record_path, manifest_path, [_market("100", ["tok1"], question="v2")], day=15)
    assert r2.source_revision_count == 1
    v2 = next(
        r for r in _store_records(record_path)
        if r.envelope.classification == "SOURCE_REVISION"
    )
    # Second revision must parent/supersede the LATEST prior (v2), never v1.
    r3 = _capture(record_path, manifest_path, [_market("100", ["tok1"], question="v3")], day=16)
    assert r3.source_revision_count == 1
    v3 = next(
        r for r in _store_records(record_path)
        if r.envelope.classification == "SOURCE_REVISION"
        and r.envelope.record_version_id not in {v2.envelope.record_version_id}
    )
    assert v3.envelope.supersedes_record_version_id == v2.envelope.record_version_id
    assert v3.envelope.lineage_parent_ids == (v2.envelope.record_version_id,)
    assert v1.envelope.record_version_id != v2.envelope.record_version_id


# ── Cumulative registration semantics ────────────────────────────────────────


def test_cumulative_reference_contains_prior_and_new_ids_and_old_reference_immutable():
    record_path, manifest_path = _seeded()
    before = _manifest_snapshot(manifest_path)
    original_reference = before.dataset_references[0]
    prior_ids = set(original_reference.ordinary_record_version_ids)

    result = _capture(record_path, manifest_path, [_market("200", ["tok2"])])
    assert result.is_valid

    after = _manifest_snapshot(manifest_path)
    # The original reference object is preserved unchanged (append-only).
    assert original_reference in after.dataset_references
    new_reference = next(
        r for r in after.dataset_references
        if r.dataset_snapshot_reference_id == result.dataset_snapshot_reference_id
    )
    cumulative_ids = set(new_reference.ordinary_record_version_ids)
    store_ids = {r.envelope.record_version_id for r in _store_records(record_path)}
    assert cumulative_ids == store_ids
    assert prior_ids < cumulative_ids
    assert len(cumulative_ids) == 2


def test_only_new_records_appended():
    record_path, manifest_path = _seeded()
    calls: list[tuple] = []
    real_append = inc.append_point_in_time_records

    def spy(path, records):
        calls.append(tuple(records))
        return real_append(path, records)

    inc.append_point_in_time_records = spy
    try:
        result = _capture(record_path, manifest_path, [_market("200", ["tok2"])])
    finally:
        inc.append_point_in_time_records = real_append
    assert result.is_valid
    assert len(calls) == 1
    appended = calls[0]
    assert len(appended) == 1  # only the one new record, not the prior
    assert appended[0].market_id == "market:polymarket:200"


def test_no_external_known_parent_ids_passed_through_wp162():
    record_path, manifest_path = _seeded()
    seen: list[dict] = []
    real = inc.persist_validated_record_batch_snapshot

    def spy(path, records, **kwargs):
        seen.append(kwargs)
        return real(path, records, **kwargs)

    inc.persist_validated_record_batch_snapshot = spy
    try:
        result = _capture(record_path, manifest_path, [_market("200", ["tok2"])])
    finally:
        inc.persist_validated_record_batch_snapshot = real
    assert result.is_valid
    assert seen and all("known_parent_record_ids" not in kw for kw in seen)
    # The registered reference recomputes as a self-contained validated batch.
    reference = next(
        r for r in _manifest_snapshot(manifest_path).dataset_references
        if r.dataset_snapshot_reference_id == result.dataset_snapshot_reference_id
    )
    from src.data_layer.point_in_time_market_research import validate_record_batch
    batch = validate_record_batch(_store_records(record_path))
    assert batch.is_valid
    assert batch.accepted_record_version_ids == reference.ordinary_record_version_ids


# ── Network failure paths write nothing ──────────────────────────────────────


def test_gamma_guard_denial_reports_no_network_and_no_write():
    record_path, manifest_path = _seeded()
    before = _store_records(record_path)
    client = FakeClient([_market("200", ["tok2"])])
    result = capture_incremental_polymarket_public_data(
        record_path, manifest_path, _config(allow_network=True, markets_limit=1),
        client=client, guard=DenyGuard(pop._GAMMA_ENDPOINT_KEY),
        utcnow_provider=_clock(15),
    )
    assert result.error_codes == ("INCREMENTAL_GUARD_DENIED",)
    assert result.network_used is False
    assert client.markets_calls == 0
    assert _store_records(record_path) == before


def test_book_guard_denial_rejects_whole_run_after_gamma():
    record_path, manifest_path = _seeded(
        [_market("100", ["tok1"])], {"tok1": _book("tok1")},
        markets_limit=1, order_books_limit=1,
    )
    before = _store_records(record_path)
    client = FakeClient([_market("100", ["tok1"])], {"tok1": _book("tok1")})
    result = capture_incremental_polymarket_public_data(
        record_path, manifest_path,
        _config(allow_network=True, markets_limit=1, order_books_limit=1),
        client=client, guard=DenyGuard(pop._CLOB_ENDPOINT_KEY),
        utcnow_provider=_clock(16),
    )
    assert result.error_codes == ("INCREMENTAL_GUARD_DENIED",)
    assert result.network_used is True
    assert _store_records(record_path) == before


def test_fetch_failure_writes_nothing():
    record_path, manifest_path = _seeded()
    before = _store_records(record_path)
    client = RaisingClient(RuntimeError("boom"))
    result = capture_incremental_polymarket_public_data(
        record_path, manifest_path, _config(allow_network=True, markets_limit=1),
        client=client, now_provider=_advancing_now(), utcnow_provider=_clock(15),
    )
    assert result.error_codes == ("INCREMENTAL_FETCH_FAILED",)
    assert _store_records(record_path) == before


def test_malformed_response_writes_nothing():
    record_path, manifest_path = _seeded()
    before = _store_records(record_path)
    client = FakeClient([{"garbage": True}])
    result = capture_incremental_polymarket_public_data(
        record_path, manifest_path, _config(allow_network=True, markets_limit=1),
        client=client, now_provider=_advancing_now(), utcnow_provider=_clock(15),
    )
    assert result.error_codes == ("INCREMENTAL_RESPONSE_INVALID",)
    assert _store_records(record_path) == before


# ── Deterministic response order ─────────────────────────────────────────────


def test_response_order_does_not_change_identities():
    def run(order):
        record_path, manifest_path = _seeded(
            [_market("100", ["a"]), _market("101", ["b"])], markets_limit=2
        )
        result = _capture(
            record_path, manifest_path,
            [_market(mid, [tok]) for mid, tok in order],
            markets_limit=2,
        )
        assert result.is_valid, result.error_codes
        return result.snapshot_id

    assert run([("300", "x"), ("301", "y")]) == run([("301", "y"), ("300", "x")])


# ── Post-append registration failure and offline recovery ────────────────────


def test_append_failure_never_registers():
    record_path, manifest_path = _seeded()
    entries_before = _manifest_snapshot(manifest_path).manifest_entries

    def boom(path, records):
        raise RuntimeError("append exploded")

    real = inc.append_point_in_time_records
    inc.append_point_in_time_records = boom
    try:
        result = _capture(record_path, manifest_path, [_market("200", ["tok2"])])
    finally:
        inc.append_point_in_time_records = real
    assert result.error_codes == ("INCREMENTAL_RECORD_APPEND_FAILED",)
    assert _manifest_snapshot(manifest_path).manifest_entries == entries_before


from src.data_layer.point_in_time_market_research.dataset_persistence_adapter import (  # noqa: E402
    DatasetPersistenceAdapterResult as _AdapterResult,
)


def _adapter_rejected(error_codes):
    """A genuine invalid DatasetPersistenceAdapterResult carrying arbitrary codes."""

    return _AdapterResult(
        is_valid=False,
        status="ADAPTER_REJECTED",
        error_codes=error_codes,
        upstream_error_codes=(),
        store_error_codes=(),
        warning_codes=(),
        dataset_reference=None,
        manifest_entry=None,
        store_status=None,
        human_review_required=False,
        advisory_only=True,
        no_execution_authority=True,
    )


def _adapter_success(reference, entry):
    """A genuine-typed ADAPTER_PERSISTED result with caller-supplied nested objects."""

    return _AdapterResult(
        is_valid=True,
        status="ADAPTER_PERSISTED",
        error_codes=(),
        upstream_error_codes=(),
        store_error_codes=(),
        warning_codes=(),
        dataset_reference=reference,
        manifest_entry=entry,
        store_status="STORE_APPEND_COMMITTED",
        human_review_required=False,
        advisory_only=True,
        no_execution_authority=True,
    )


@pytest.mark.parametrize(
    "adapter",
    [
        lambda *a, **k: _adapter_rejected(("ADAPTER_STORE_APPEND_FAILED",)),
        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("adapter exploded")),
        lambda *a, **k: object(),  # malformed (wrong type)
    ],
)
def test_registration_failure_leaves_records_and_requires_recovery(adapter):
    record_path, manifest_path = _seeded()
    real = inc.persist_validated_record_batch_snapshot
    inc.persist_validated_record_batch_snapshot = adapter
    try:
        result = _capture(record_path, manifest_path, [_market("200", ["tok2"])])
    finally:
        inc.persist_validated_record_batch_snapshot = real
    assert result.status == "INCREMENTAL_RECORDS_PERSISTED_REGISTRATION_FAILED"
    assert result.error_codes == ("INCREMENTAL_REGISTRATION_FAILED",)
    assert result.recovery_required is True
    assert result.record_store_status == "RECORD_STORE_APPEND_COMMITTED"
    assert result.dataset_snapshot_reference_id is None
    # The new record is committed and never deleted.
    assert len(_store_records(record_path)) == 2


def test_registration_diagnostics_are_closed_vocabulary_only():
    record_path, manifest_path = _seeded()
    # A genuine invalid adapter result whose error_codes carry hostile extras.
    leaky = _adapter_rejected(("ADAPTER_BATCH_INVALID", "sneaky/path", 42))
    real = inc.persist_validated_record_batch_snapshot
    inc.persist_validated_record_batch_snapshot = lambda *a, **k: leaky
    try:
        result = _capture(record_path, manifest_path, [_market("200", ["tok2"])])
    finally:
        inc.persist_validated_record_batch_snapshot = real
    assert result.status == "INCREMENTAL_RECORDS_PERSISTED_REGISTRATION_FAILED"
    assert result.registration_error_codes == ("ADAPTER_BATCH_INVALID",)
    assert "sneaky/path" not in result.registration_error_codes


def test_genuine_one_run_offline_recovery():
    record_path, manifest_path = _seeded()
    real = inc.persist_validated_record_batch_snapshot
    inc.persist_validated_record_batch_snapshot = lambda *a, **k: _adapter_rejected(())
    try:
        _capture(record_path, manifest_path, [_market("200", ["tok2"])])
    finally:
        inc.persist_validated_record_batch_snapshot = real
    recovered = recover_incremental_polymarket_public_registration(
        record_path, manifest_path, _config()
    )
    assert recovered.is_valid
    assert recovered.status == "INCREMENTAL_RECOVERED_REGISTRATION"
    assert recovered.new_record_count == 1
    assert recovered.cumulative_record_count == 2
    assert recovered.prior_registered_record_count == 1
    assert recovered.network_used is False
    reference = next(
        r for r in _manifest_snapshot(manifest_path).dataset_references
        if r.dataset_snapshot_reference_id == recovered.dataset_snapshot_reference_id
    )
    assert set(reference.ordinary_record_version_ids) == {
        r.envelope.record_version_id for r in _store_records(record_path)
    }


def test_already_converged_recovery_is_noop():
    record_path, manifest_path = _seeded()
    result = recover_incremental_polymarket_public_registration(
        record_path, manifest_path, _config()
    )
    assert result.is_valid
    assert result.status == "INCREMENTAL_ALREADY_REGISTERED"
    assert result.new_record_count == 0


def test_recovery_rejects_forged_orphan_with_wrong_run_identity():
    record_path, manifest_path = _seeded()
    append_point_in_time_records(record_path, (_seed_extra_record(record_path),))
    result = recover_incremental_polymarket_public_registration(
        record_path, manifest_path, _config()
    )
    assert not result.is_valid
    assert result.error_codes == ("INCREMENTAL_RECOVERY_INVALID",)


def test_recovery_rejects_two_distinct_orphan_batches():
    record_path, manifest_path = _seeded()
    # Two orphans with different snapshot/batch identities cannot be one run.
    payload = {
        "question_text": "Q", "market_status": "open", "outcome_labels": ["Yes", "No"],
        "condition_id": "0xc", "token_ids": ["t"], "resolution_date": None,
        "category": None, "raw_field_names": ["id"],
    }
    orphan_a = pop._build_gamma_record(
        {"market_id": "market:polymarket:501", "event_id": "event:polymarket:0xc501",
         "payload": dict(payload, condition_id="0xc501", token_ids=["t501"])},
        snapshot_id="snapshot:sha256:" + "a" * 64,
        ingestion_batch_id="ingest:sha256:" + "a" * 64,
        captured_at_utc="2026-08-21T00:00:00Z", config=_config(),
    )
    orphan_b = pop._build_gamma_record(
        {"market_id": "market:polymarket:502", "event_id": "event:polymarket:0xc502",
         "payload": dict(payload, condition_id="0xc502", token_ids=["t502"])},
        snapshot_id="snapshot:sha256:" + "b" * 64,
        ingestion_batch_id="ingest:sha256:" + "b" * 64,
        captured_at_utc="2026-08-22T00:00:00Z", config=_config(),
    )
    append_point_in_time_records(record_path, (orphan_a, orphan_b))
    result = recover_incremental_polymarket_public_registration(
        record_path, manifest_path, _config()
    )
    assert result.error_codes == ("INCREMENTAL_RECOVERY_INVALID",)


def test_recovery_rejects_non_config_object():
    record_path, manifest_path = _seeded()
    result = recover_incremental_polymarket_public_registration(
        record_path, manifest_path, object()
    )
    assert result.error_codes == ("INCREMENTAL_INPUT_INVALID",)


# ── Blocker A: latest prior uses timestamp chronology, not string order ───────


def test_latest_prior_uses_timestamp_chronology_not_string_order():
    record_path, manifest_path = _stores()
    # Seed v1 at a whole-second time on the SAME second as the fractional v2.
    _seed(record_path, manifest_path, [_market("100", ["tok1"])], day=15)
    v1 = _store_records(record_path)[0]
    assert v1.envelope.ingestion_time == "2026-08-15T12:00:00Z"

    # v2 at a FRACTIONAL time that is chronologically LATER than v1 but sorts
    # BEFORE it lexically ("...:00.500000Z" < "...:00Z" because '.' < 'Z').
    r2 = capture_incremental_polymarket_public_data(
        record_path, manifest_path,
        _config(allow_network=True, markets_limit=1),
        client=FakeClient([_market("100", ["tok1"], question="v2")]),
        now_provider=_advancing_now(),
        utcnow_provider=lambda: datetime.datetime(
            2026, 8, 15, 12, 0, 0, 500000, tzinfo=datetime.UTC
        ),
    )
    assert r2.is_valid and r2.source_revision_count == 1
    v2 = next(
        r for r in _store_records(record_path)
        if r.envelope.classification == "SOURCE_REVISION"
    )
    # Confirm the trap: lexically v2 sorts BEFORE v1, so string ordering would
    # wrongly keep v1 as the latest prior.
    assert v2.envelope.ingestion_time < v1.envelope.ingestion_time

    # v3 is chronologically after both; it must parent/supersede v2 (the true
    # latest), never v1.
    r3 = capture_incremental_polymarket_public_data(
        record_path, manifest_path,
        _config(allow_network=True, markets_limit=1),
        client=FakeClient([_market("100", ["tok1"], question="v3")]),
        now_provider=_advancing_now(),
        utcnow_provider=lambda: datetime.datetime(
            2026, 8, 15, 12, 0, 1, tzinfo=datetime.UTC
        ),
    )
    assert r3.is_valid and r3.source_revision_count == 1
    v3 = next(
        r for r in _store_records(record_path)
        if r.envelope.classification == "SOURCE_REVISION"
        and r.envelope.record_version_id != v2.envelope.record_version_id
    )
    assert v3.envelope.supersedes_record_version_id == v2.envelope.record_version_id
    assert v3.envelope.lineage_parent_ids == (v2.envelope.record_version_id,)


def test_malformed_prior_timestamp_helper_fails_closed():
    with pytest.raises(inc._IncrementalReject) as excinfo:
        inc._parse_utc("not-a-timestamp")
    assert excinfo.value.code == "INCREMENTAL_RECORD_STORE_INVALID"
    with pytest.raises(inc._IncrementalReject):
        inc._parse_utc("2026-08-15T12:00:00")  # naive, no zone


# ── Blocker B: config manifest_id bound before network ───────────────────────


def test_manifest_id_mismatch_rejected_before_network():
    record_path, manifest_path = _seeded()
    before_records = _store_records(record_path)
    before_entries = _manifest_snapshot(manifest_path).manifest_entries
    client = FakeClient([_market("200", ["tok2"])])
    result = capture_incremental_polymarket_public_data(
        record_path, manifest_path,
        _config(allow_network=True, markets_limit=1, manifest_id="manifest:polymarket:OTHER"),
        client=client, utcnow_provider=_clock(15),
    )
    assert result.error_codes == ("INCREMENTAL_PROVENANCE_MISMATCH",)
    assert result.network_used is False
    assert result.recovery_required is False
    assert client.markets_calls == 0
    assert _store_records(record_path) == before_records
    assert _manifest_snapshot(manifest_path).manifest_entries == before_entries


# ── Blocker C: recovery proves the config-bounded capture shape ──────────────


def test_recovery_rejects_book_only_orphan_run():
    record_path, manifest_path = _seeded()
    append_point_in_time_records(record_path, (_forge_book("300", "tokX"),))
    result = recover_incremental_polymarket_public_registration(
        record_path, manifest_path, _config(order_books_limit=1)
    )
    assert result.error_codes == ("INCREMENTAL_RECOVERY_INVALID",)


def test_recovery_rejects_clob_orphan_when_books_disabled():
    record_path, manifest_path = _seeded()
    append_point_in_time_records(
        record_path,
        (_forge_gamma("300", ["tokX"]), _forge_book("300", "tokX")),
    )
    # order_books_limit == 0 -> bounded_books == 0 -> a CLOB orphan is impossible.
    result = recover_incremental_polymarket_public_registration(
        record_path, manifest_path, _config(order_books_limit=0)
    )
    assert result.error_codes == ("INCREMENTAL_RECOVERY_INVALID",)


def test_recovery_rejects_more_gamma_than_markets_limit():
    record_path, manifest_path = _seeded()
    append_point_in_time_records(
        record_path,
        (_forge_gamma("301", ["t301"]), _forge_gamma("302", ["t302"])),
    )
    result = recover_incremental_polymarket_public_registration(
        record_path, manifest_path, _config(markets_limit=1)
    )
    assert result.error_codes == ("INCREMENTAL_RECOVERY_INVALID",)


def test_recovery_rejects_clob_token_absent_from_same_run_gamma():
    record_path, manifest_path = _seeded()
    # Gamma 300 owns only tokA; a book for an unrelated token cannot belong.
    append_point_in_time_records(
        record_path,
        (_forge_gamma("300", ["tokA"]), _forge_book("300", "tokZZZ")),
    )
    result = recover_incremental_polymarket_public_registration(
        record_path, manifest_path, _config(order_books_limit=1)
    )
    assert result.error_codes == ("INCREMENTAL_RECOVERY_INVALID",)


def test_recovery_rejects_misparented_same_run_clob():
    record_path, manifest_path = _seeded()
    # tokA is owned by Gamma 300, but the book claims market/event 400.
    append_point_in_time_records(
        record_path,
        (_forge_gamma("300", ["tokA"]), _forge_book("400", "tokA")),
    )
    result = recover_incremental_polymarket_public_registration(
        record_path, manifest_path, _config(order_books_limit=1)
    )
    assert result.error_codes == ("INCREMENTAL_RECOVERY_INVALID",)


def test_recovery_rejects_book_not_matching_deterministic_selection():
    record_path, manifest_path = _seeded()
    # Gamma 300 offers tokA,tokB; bounded_books=1 selects tokA, but the orphan
    # carries tokB instead of the deterministically selected tokA.
    append_point_in_time_records(
        record_path,
        (_forge_gamma("300", ["tokA", "tokB"]), _forge_book("300", "tokB")),
    )
    result = recover_incremental_polymarket_public_registration(
        record_path, manifest_path, _config(order_books_limit=1)
    )
    assert result.error_codes == ("INCREMENTAL_RECOVERY_INVALID",)


def test_recovery_accepts_genuine_run_with_book():
    record_path, manifest_path = _seeded(
        [_market("100", ["tok1"])], {"tok1": _book("tok1")},
        markets_limit=1, order_books_limit=1,
    )
    real = inc.persist_validated_record_batch_snapshot
    inc.persist_validated_record_batch_snapshot = lambda *a, **k: _adapter_rejected(())
    try:
        _capture(
            record_path, manifest_path, [_market("100", ["tok1"], question="v2")],
            {"tok1": _book("tok1", bids=(("0.55", "3"),))},
            markets_limit=1, order_books_limit=1,
        )
    finally:
        inc.persist_validated_record_batch_snapshot = real
    result = recover_incremental_polymarket_public_registration(
        record_path, manifest_path, _config(markets_limit=1, order_books_limit=1)
    )
    assert result.is_valid
    assert result.status == "INCREMENTAL_RECOVERED_REGISTRATION"
    assert result.new_record_count == 2


def test_recovery_accepts_same_market_duplicate_token_once():
    record_path, manifest_path = _seeded(
        [_market("100", ["dup", "dup"])], {"dup": _book("dup")},
        markets_limit=1, order_books_limit=2,
    )
    # The seed already de-duplicated the repeated token into a single book.
    real = inc.persist_validated_record_batch_snapshot
    inc.persist_validated_record_batch_snapshot = lambda *a, **k: _adapter_rejected(())
    try:
        _capture(
            record_path, manifest_path, [_market("100", ["dup", "dup"], question="v2")],
            {"dup": _book("dup", bids=(("0.55", "3"),))},
            markets_limit=1, order_books_limit=2,
        )
    finally:
        inc.persist_validated_record_batch_snapshot = real
    result = recover_incremental_polymarket_public_registration(
        record_path, manifest_path, _config(markets_limit=1, order_books_limit=2)
    )
    assert result.is_valid
    assert result.status == "INCREMENTAL_RECOVERED_REGISTRATION"


# ── Blocker D: typed-but-false WP162 success is proven, not trusted ──────────


def _unrelated_reference_and_entry():
    """A genuine registered reference/entry from an INDEPENDENT dataset/manifest."""
    record_path, manifest_path = _seeded([_market("888", ["zzz"])])
    _capture(record_path, manifest_path, [_market("889", ["yyy"])])
    snapshot = _manifest_snapshot(manifest_path)
    reference = max(
        snapshot.dataset_references, key=lambda r: len(r.ordinary_record_version_ids)
    )
    entry = next(
        e for e in snapshot.manifest_entries
        if e.dataset_snapshot_reference_id == reference.dataset_snapshot_reference_id
    )
    return reference, entry


def test_typed_success_with_unrelated_reference_entry_rejected():
    record_path, manifest_path = _seeded()
    unrelated_ref, unrelated_entry = _unrelated_reference_and_entry()
    real = inc.persist_validated_record_batch_snapshot
    inc.persist_validated_record_batch_snapshot = lambda *a, **k: _adapter_success(
        unrelated_ref, unrelated_entry
    )
    try:
        result = _capture(record_path, manifest_path, [_market("200", ["tok2"])])
    finally:
        inc.persist_validated_record_batch_snapshot = real
    assert result.status == "INCREMENTAL_RECORDS_PERSISTED_REGISTRATION_FAILED"
    assert result.error_codes == ("INCREMENTAL_REGISTRATION_FAILED",)
    assert result.recovery_required is True
    assert result.dataset_snapshot_reference_id is None
    # The real manifest was never actually written by the fake adapter.
    assert len(_manifest_snapshot(manifest_path).manifest_entries) == 1


def test_typed_success_without_manifest_write_rejected():
    record_path, manifest_path = _seeded()
    other_manifest = os.path.join(tempfile.mkdtemp(), "other.sqlite3")
    initialize_manifest_store(other_manifest)
    real = inc.persist_validated_record_batch_snapshot

    def redirect(path, records, **kwargs):
        # Genuine typed success whose reference/entry match THIS batch, but the
        # write lands in an unrelated manifest — the real manifest stays empty.
        return real(other_manifest, records, **kwargs)

    inc.persist_validated_record_batch_snapshot = redirect
    try:
        result = _capture(record_path, manifest_path, [_market("200", ["tok2"])])
    finally:
        inc.persist_validated_record_batch_snapshot = real
    assert result.status == "INCREMENTAL_RECORDS_PERSISTED_REGISTRATION_FAILED"
    assert result.error_codes == ("INCREMENTAL_REGISTRATION_FAILED",)
    assert result.recovery_required is True
    # The reference is genuinely absent from the real manifest.
    assert len(_manifest_snapshot(manifest_path).manifest_entries) == 1
    # And offline recovery can still complete the registration for real.
    recovered = recover_incremental_polymarket_public_registration(
        record_path, manifest_path, _config()
    )
    assert recovered.is_valid
    assert recovered.status == "INCREMENTAL_RECOVERED_REGISTRATION"


def test_genuine_registration_persists_and_reverifies():
    record_path, manifest_path = _seeded()
    result = _capture(record_path, manifest_path, [_market("200", ["tok2"])])
    assert result.is_valid
    assert result.status == "INCREMENTAL_PERSISTED_AND_REGISTERED"
    snapshot = _manifest_snapshot(manifest_path)
    reference = next(
        r for r in snapshot.dataset_references
        if r.dataset_snapshot_reference_id == result.dataset_snapshot_reference_id
    )
    # The registered cumulative reference recomputes to the full store batch.
    batch = validate_record_batch(_store_records(record_path))
    assert reference.ordinary_record_version_ids == batch.accepted_record_version_ids
    assert reference.validated_batch_sha256 == batch.canonical_batch_sha256


# ── Registered-baseline reference proof against the record store ─────────────


def _make_genuine_orphan(record_path, manifest_path, markets):
    """Leave exactly one genuine failed-registration WP165 orphan run in the store."""

    real = inc.persist_validated_record_batch_snapshot
    inc.persist_validated_record_batch_snapshot = lambda *a, **k: _adapter_rejected(())
    try:
        result = _capture(record_path, manifest_path, markets)
    finally:
        inc.persist_validated_record_batch_snapshot = real
    assert result.status == "INCREMENTAL_RECORDS_PERSISTED_REGISTRATION_FAILED"


def _register_forged_reference(
    manifest_path, config, *, ordinary_ids, batch_sha,
    effective_time="2026-08-25T00:00:00Z",
):
    """Register an internally self-consistent VALIDATED_RECORD_BATCH reference whose
    ordinary ids/hash are caller-chosen, at the append-chain head, via the public
    WP160 builders and WP161 store append."""

    reference = _dpa._build_reference(
        derivation_mode="VALIDATED_RECORD_BATCH",
        validated_batch_sha256=batch_sha,
        ordinary_ids=tuple(ordinary_ids),
        review_ids=(),
        query_spec_sha256=None,
        query_result_sha256=None,
        cutoff_mode=None,
        cutoff_time=None,
        result_view=None,
        query_engine_version=None,
        validator_version=config.validator_version,
        parameter_set_id=config.parameter_set_id,
    )
    assert reference is not None
    entries = _manifest_snapshot(manifest_path).manifest_entries
    head = max(entries, key=lambda e: e.sequence_number)
    entry = _dpa._build_register_entry(
        manifest_id=config.manifest_id,
        sequence_number=len(entries),
        previous_manifest_entry_id=head.manifest_entry_id,
        dataset_snapshot_reference_id=reference.dataset_snapshot_reference_id,
        effective_time=effective_time,
        parameter_set_id=config.parameter_set_id,
        human_review_required=False,
    )
    assert entry is not None
    appended = append_manifest_store_batch(
        manifest_path, dataset_references=(reference,), manifest_entries=(entry,)
    )
    assert appended.is_valid, appended.error_codes
    return reference


def test_strict_superset_materialization_failure_blocks_capture(monkeypatch):
    record_path, manifest_path = _seeded()
    _make_genuine_orphan(record_path, manifest_path, [_market("200", ["tok2"])])
    before_records = _store_records(record_path)
    before_entries = _manifest_snapshot(manifest_path).manifest_entries

    def boom(*a, **k):
        raise RuntimeError("materialization exploded")

    monkeypatch.setattr(inc, "materialize_dataset_snapshot_reference", boom)
    client = FakeClient([_market("300", ["tok3"])])
    result = capture_incremental_polymarket_public_data(
        record_path, manifest_path, _config(allow_network=True, markets_limit=1),
        client=client, utcnow_provider=_clock(18),
    )
    assert result.error_codes == ("INCREMENTAL_BASELINE_REFERENCE_INVALID",)
    assert result.recovery_required is False
    assert result.network_used is False
    assert client.markets_calls == 0
    assert _store_records(record_path) == before_records
    assert _manifest_snapshot(manifest_path).manifest_entries == before_entries


def test_strict_superset_materialization_failure_blocks_recovery(monkeypatch):
    record_path, manifest_path = _seeded()
    _make_genuine_orphan(record_path, manifest_path, [_market("200", ["tok2"])])
    before_records = _store_records(record_path)
    before_entries = _manifest_snapshot(manifest_path).manifest_entries

    seen = []
    real_persist = inc.persist_validated_record_batch_snapshot

    def spy_persist(*a, **k):
        seen.append(True)
        return real_persist(*a, **k)

    monkeypatch.setattr(inc, "persist_validated_record_batch_snapshot", spy_persist)

    def boom(*a, **k):
        raise RuntimeError("materialization exploded")

    monkeypatch.setattr(inc, "materialize_dataset_snapshot_reference", boom)
    result = recover_incremental_polymarket_public_registration(
        record_path, manifest_path, _config()
    )
    assert result.error_codes == ("INCREMENTAL_BASELINE_REFERENCE_INVALID",)
    assert result.recovery_required is False
    assert result.network_used is False
    assert seen == []  # WP162 registration never reached
    assert _store_records(record_path) == before_records
    assert _manifest_snapshot(manifest_path).manifest_entries == before_entries


def test_wrong_registered_batch_hash_rejected_before_network_and_registration():
    record_path, manifest_path = _seeded()
    registered = _store_records(record_path)
    ordinary = validate_record_batch(registered).accepted_record_version_ids
    # Leave a genuine orphan suffix, THEN make the latest reference name the genuine
    # baseline records with a different valid SHA-256 value.
    _make_genuine_orphan(record_path, manifest_path, [_market("200", ["tok2"])])
    _register_forged_reference(
        manifest_path, _config(), ordinary_ids=ordinary, batch_sha="f" * 64
    )
    before_entries = _manifest_snapshot(manifest_path).manifest_entries

    # Capture must not heal the reference.
    client = FakeClient([_market("300", ["tok3"])])
    cap = capture_incremental_polymarket_public_data(
        record_path, manifest_path, _config(allow_network=True, markets_limit=1),
        client=client, utcnow_provider=_clock(18),
    )
    assert cap.error_codes == ("INCREMENTAL_BASELINE_REFERENCE_INVALID",)
    assert client.markets_calls == 0
    # Recovery must not heal the reference.
    rec = recover_incremental_polymarket_public_registration(
        record_path, manifest_path, _config()
    )
    assert rec.error_codes == ("INCREMENTAL_BASELINE_REFERENCE_INVALID",)
    assert _manifest_snapshot(manifest_path).manifest_entries == before_entries


def test_wrong_registered_ordinary_id_order_rejected():
    record_path, manifest_path = _seeded(
        [_market("100", ["a"]), _market("101", ["b"])], markets_limit=2
    )
    registered = _store_records(record_path)
    batch = validate_record_batch(registered)
    assert len(batch.accepted_record_version_ids) >= 2
    reversed_ids = tuple(reversed(batch.accepted_record_version_ids))
    _make_genuine_orphan(record_path, manifest_path, [_market("200", ["tok2"])])
    # Same records, same (correct) hash, but a noncanonical ordinary-id order.
    _register_forged_reference(
        manifest_path, _config(),
        ordinary_ids=reversed_ids, batch_sha=batch.canonical_batch_sha256,
    )
    before_entries = _manifest_snapshot(manifest_path).manifest_entries

    client = FakeClient([_market("300", ["tok3"])])
    cap = capture_incremental_polymarket_public_data(
        record_path, manifest_path, _config(allow_network=True, markets_limit=1),
        client=client, utcnow_provider=_clock(18),
    )
    assert cap.error_codes == ("INCREMENTAL_BASELINE_REFERENCE_INVALID",)
    assert client.markets_calls == 0
    rec = recover_incremental_polymarket_public_registration(
        record_path, manifest_path, _config()
    )
    assert rec.error_codes == ("INCREMENTAL_BASELINE_REFERENCE_INVALID",)
    assert _manifest_snapshot(manifest_path).manifest_entries == before_entries


def test_genuine_strict_superset_recovers_through_shared_reference_proof():
    record_path, manifest_path = _seeded()
    _make_genuine_orphan(record_path, manifest_path, [_market("200", ["tok2"])])
    # A subsequent capture attempt recognizes the recoverable orphan.
    client = FakeClient([_market("300", ["tok3"])])
    blocked = capture_incremental_polymarket_public_data(
        record_path, manifest_path, _config(allow_network=True, markets_limit=1),
        client=client, utcnow_provider=_clock(18),
    )
    assert blocked.error_codes == ("INCREMENTAL_BASELINE_UNREGISTERED",)
    assert blocked.recovery_required is True
    assert client.markets_calls == 0
    # Offline recovery completes with zero network.
    recovered = recover_incremental_polymarket_public_registration(
        record_path, manifest_path, _config()
    )
    assert recovered.is_valid
    assert recovered.status == "INCREMENTAL_RECOVERED_REGISTRATION"
    assert recovered.network_used is False


def test_equal_baseline_dry_run_uses_shared_reference_proof():
    record_path, manifest_path = _seeded()
    result = capture_incremental_polymarket_public_data(
        record_path, manifest_path, _config(markets_limit=1)
    )
    assert result.is_valid
    assert result.status == "INCREMENTAL_DRY_RUN"
    assert result.network_used is False
    # The converged reference still materializes through the shared proof.
    recovered = recover_incremental_polymarket_public_registration(
        record_path, manifest_path, _config()
    )
    assert recovered.status == "INCREMENTAL_ALREADY_REGISTERED"


# ── Config boundary ──────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "overrides",
    [
        {"markets_limit": 26},
        {"markets_limit": -1},
        {"order_books_limit": 21},
        {"manifest_id": ""},
        {"parameter_set_id": " padded "},
    ],
)
def test_invalid_config_rejected_without_network(overrides):
    record_path, manifest_path = _seeded()
    client = FakeClient([_market("100", ["tok1"])])
    result = capture_incremental_polymarket_public_data(
        record_path, manifest_path, _config(allow_network=True, **overrides),
        client=client,
    )
    assert result.error_codes == ("INCREMENTAL_INPUT_INVALID",)
    assert client.markets_calls == 0


def test_non_config_object_rejected():
    record_path, manifest_path = _seeded()
    result = capture_incremental_polymarket_public_data(
        record_path, manifest_path, object()
    )
    assert result.error_codes == ("INCREMENTAL_INPUT_INVALID",)


def test_bool_markets_limit_rejected():
    record_path, manifest_path = _seeded()
    result = capture_incremental_polymarket_public_data(
        record_path, manifest_path, _config(markets_limit=True)
    )
    assert result.error_codes == ("INCREMENTAL_INPUT_INVALID",)


# ── Source-boundary and import allowlist locks ───────────────────────────────


def _module_source() -> str:
    import importlib.util

    spec = importlib.util.find_spec(
        "src.data_layer.point_in_time_market_research.polymarket_incremental_population"
    )
    assert spec is not None and spec.origin is not None
    with open(spec.origin, "r", encoding="utf-8") as handle:
        return handle.read()


_WP164_IMPORT_ALLOWLIST = frozenset(
    {
        "PolymarketPublicPopulationConfig",
        "_PLATFORM_ID",
        "_GAMMA_SOURCE_ID",
        "_CLOB_SOURCE_ID",
        "_GAMMA_ENDPOINT_KEY",
        "_CLOB_ENDPOINT_KEY",
        "_bounded_limits",
        "_build_guard",
        "_consult_guard",
        "_get_markets",
        "_parse_markets",
        "_select_tokens",
        "_get_order_book",
        "_normalize_order_book",
        "_capture_time",
        "_build_gamma_record",
        "_build_order_book_record",
    }
)


def test_wp164_import_allowlist_is_enforced():
    tree = ast.parse(_module_source())
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "polymarket_public_population":
            assert node.level == 1
            for alias in node.names:
                imported.add(alias.name)
    assert imported, "expected a sibling import from polymarket_public_population"
    assert imported <= _WP164_IMPORT_ALLOWLIST, imported - _WP164_IMPORT_ALLOWLIST
    forbidden = {
        "_run_network_population",
        "_run_identities",
        "_safe_register",
        "_validate_config",
        "_verify_manifest_store",
        "_verify_empty_record_store",
        "_load_recovery_records",
        "_prove_wp164_construction",
        "_PopulationReject",
        "populate_initial_polymarket_public_data",
        "recover_initial_polymarket_public_registration",
    }
    assert not (imported & forbidden)


def test_module_has_no_direct_network_or_forbidden_imports():
    tree = ast.parse(_module_source())
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                modules.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            modules.add(node.module.split(".")[0])
    for forbidden in (
        "urllib", "requests", "httpx", "aiohttp", "websockets", "socket",
        "subprocess", "os",
    ):
        assert forbidden not in modules, forbidden


def test_module_has_no_forbidden_identifiers():
    identifiers: set[str] = set()
    reader = io.StringIO(_module_source()).readline
    for tok in tokenize.generate_tokens(reader):
        if tok.type == tokenize.NAME:
            identifiers.add(tok.string)
    for forbidden in (
        "environ", "getenv", "snapshot_writer", "write_snapshots",
        "capture_market_snapshots", "local_data", "get_health", "get_market",
        "place_order", "cancel_order", "sleep", "keyset", "cursor",
        "known_parent_record_ids",
    ):
        assert forbidden not in identifiers, forbidden


def test_module_has_no_scheduler_loop_or_retry_constructs():
    tree = ast.parse(_module_source())
    for node in ast.walk(tree):
        assert not isinstance(node, (ast.While, ast.AsyncFor, ast.AsyncFunctionDef))


def test_invalid_results_never_echo_untrusted_text():
    """Every reachable rejection carries only closed-vocabulary codes and no echo."""

    record_path, manifest_path = _seeded()
    results = [
        capture_incremental_polymarket_public_data(record_path, manifest_path, object()),
        capture_incremental_polymarket_public_data("/no/such/path", manifest_path, _config()),
        recover_incremental_polymarket_public_registration(record_path, "/no/such", _config()),
    ]
    allowed = set(inc.POLYMARKET_INCREMENTAL_POPULATION_ERROR_CODES)
    for result in results:
        for code in result.error_codes:
            assert code in allowed
        for code in result.registration_error_codes:
            assert code in inc._ADAPTER_ERROR_CODES
        for code in result.record_store_error_codes:
            assert code in inc._STORE_ERROR_CODES
        assert result.warning_codes == ()
