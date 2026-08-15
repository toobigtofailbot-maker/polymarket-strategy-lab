"""Focused tests for the WP164 bounded real/public Polymarket population.

These tests never touch the network. Every network-capable path is exercised with
an injected fake GET-only client, an injected guard, and a fixed clock.
"""

from __future__ import annotations

import datetime
import json
import os
import tempfile

import pytest

import src.data_layer.point_in_time_market_research as pit
from src.data_layer.polymarket.models import AdapterResult, ReadOnlyRequestInfo
from src.data_layer.point_in_time_market_research import (
    polymarket_public_population as pop,
)
from src.data_layer.point_in_time_market_research import (
    PolymarketPublicPopulationConfig as Cfg,
    initialize_manifest_store,
    initialize_point_in_time_record_store,
    load_and_verify_manifest_store,
    load_and_verify_point_in_time_record_store,
    populate_initial_polymarket_public_data,
    recover_initial_polymarket_public_registration,
)


FIXED_CLOCK = datetime.datetime(2026, 8, 14, 12, 0, 0, tzinfo=datetime.UTC)


def _clock():
    return FIXED_CLOCK


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
        allowed = endpoint_key != self._deny
        return _Decision(allowed)


class _Decision:
    def __init__(self, allowed):
        self.allowed = allowed


def _stores():
    directory = tempfile.mkdtemp()
    record_path = os.path.join(directory, "records.sqlite3")
    manifest_path = os.path.join(directory, "manifest.sqlite3")
    initialize_point_in_time_record_store(record_path)
    initialize_manifest_store(manifest_path)
    return record_path, manifest_path


# ── Public surface ────────────────────────────────────────────────────────────


def test_locked_labels_and_vocabularies_are_exact():
    assert (
        pop.POLYMARKET_PUBLIC_POPULATION_LABEL
        == "POLYMARKET_REAL_PUBLIC_INITIAL_POINT_IN_TIME_POPULATION"
    )
    assert (
        pop.POLYMARKET_PUBLIC_POPULATION_POSTURE
        == "EXPLICIT_NETWORK_GET_ONLY_BOUNDED_INITIAL_SEED_NO_TRADING_AUTHORITY"
    )
    assert pop.POLYMARKET_PUBLIC_POPULATION_STATUSES == (
        "POPULATION_DRY_RUN",
        "POPULATION_PERSISTED_AND_REGISTERED",
        "POPULATION_ALREADY_REGISTERED",
        "POPULATION_RECORDS_PERSISTED_REGISTRATION_FAILED",
        "POPULATION_RECOVERED_REGISTRATION",
        "POPULATION_REJECTED",
    )
    assert pop.POLYMARKET_PUBLIC_POPULATION_ERROR_CODES == (
        "POPULATION_INPUT_INVALID",
        "POPULATION_RECORD_STORE_INVALID",
        "POPULATION_MANIFEST_STORE_INVALID",
        "POPULATION_RECORD_STORE_NOT_EMPTY",
        "POPULATION_POLICY_INVALID",
        "POPULATION_GUARD_DENIED",
        "POPULATION_FETCH_FAILED",
        "POPULATION_RESPONSE_INVALID",
        "POPULATION_BUILD_FAILED",
        "POPULATION_BATCH_INVALID",
        "POPULATION_RECORD_APPEND_FAILED",
        "POPULATION_REGISTRATION_FAILED",
        "POPULATION_RECOVERY_INVALID",
        "POPULATION_UNEXPECTED_ERROR",
    )


def test_config_and_result_are_frozen():
    cfg = _config()
    with pytest.raises(Exception):
        cfg.markets_limit = 9  # type: ignore[misc]
    record_path, manifest_path = _stores()
    result = populate_initial_polymarket_public_data(record_path, manifest_path, cfg)
    with pytest.raises(Exception):
        result.status = "x"  # type: ignore[misc]


def test_package_exports_end_with_the_eight_wp164_symbols():
    assert pit.__all__[-8:] == (
        "POLYMARKET_PUBLIC_POPULATION_LABEL",
        "POLYMARKET_PUBLIC_POPULATION_POSTURE",
        "POLYMARKET_PUBLIC_POPULATION_STATUSES",
        "POLYMARKET_PUBLIC_POPULATION_ERROR_CODES",
        "PolymarketPublicPopulationConfig",
        "PolymarketPublicPopulationResult",
        "populate_initial_polymarket_public_data",
        "recover_initial_polymarket_public_registration",
    )
    assert all(
        getattr(pit, name) is getattr(pop, name) for name in pit.__all__[-8:]
    )


# ── Dry run ───────────────────────────────────────────────────────────────────


def test_default_dry_run_makes_no_network_call():
    record_path, manifest_path = _stores()
    client = FakeClient([_market("100", ["tok1"])])
    result = populate_initial_polymarket_public_data(
        record_path, manifest_path, _config(markets_limit=3), client=client
    )
    assert result.is_valid is True
    assert result.status == "POPULATION_DRY_RUN"
    assert result.network_used is False
    assert result.recovery_required is False
    assert result.warning_codes == ()
    assert result.advisory_only is True
    assert result.no_execution_authority is True
    assert result.requested_markets_limit == 3
    assert result.bounded_markets_limit == 3
    assert (result.fetched_market_count, result.built_record_count, result.inserted_record_count) == (0, 0, 0)
    assert client.markets_calls == 0
    assert load_and_verify_point_in_time_record_store(record_path).snapshot.records == ()
    assert load_and_verify_manifest_store(manifest_path).snapshot.manifest_entries == ()


def test_dry_run_bounds_limits_through_policy():
    record_path, manifest_path = _stores()
    result = populate_initial_polymarket_public_data(
        record_path, manifest_path, _config(markets_limit=25, order_books_limit=20)
    )
    assert result.bounded_markets_limit == 25
    assert result.bounded_order_books_limit == 20


# ── Config boundary ───────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "overrides",
    [
        {"markets_limit": 26},
        {"markets_limit": -1},
        {"order_books_limit": 21},
        {"order_books_limit": -1},
        {"manifest_id": ""},
        {"manifest_id": " leading"},
        {"parameter_set_id": "x" * 257},
    ],
)
def test_invalid_config_rejected_without_network(overrides):
    record_path, manifest_path = _stores()
    client = FakeClient([_market("100", ["tok1"])])
    # bool markets_limit must also be rejected; build the config directly.
    cfg = _config(allow_network=True, **overrides)
    result = populate_initial_polymarket_public_data(
        record_path, manifest_path, cfg, client=client
    )
    assert result.is_valid is False
    assert result.error_codes == ("POPULATION_INPUT_INVALID",)
    assert client.markets_calls == 0


def test_non_config_object_rejected():
    record_path, manifest_path = _stores()
    result = populate_initial_polymarket_public_data(
        record_path, manifest_path, {"markets_limit": 1}
    )
    assert result.error_codes == ("POPULATION_INPUT_INVALID",)


def test_bool_markets_limit_rejected():
    record_path, manifest_path = _stores()
    cfg = Cfg(
        manifest_id="manifest:polymarket:test",
        parameter_set_id="params:v1",
        normalizer_version="norm:v1",
        validator_version="val:v1",
        markets_limit=True,  # bool is not an accepted int
        allow_network=True,
    )
    client = FakeClient([_market("100", ["tok1"])])
    result = populate_initial_polymarket_public_data(
        record_path, manifest_path, cfg, client=client
    )
    assert result.error_codes == ("POPULATION_INPUT_INVALID",)
    assert client.markets_calls == 0


# ── Store preconditions ───────────────────────────────────────────────────────


def test_invalid_record_store_makes_no_network_call():
    directory = tempfile.mkdtemp()
    record_path = os.path.join(directory, "missing.sqlite3")
    manifest_path = os.path.join(directory, "manifest.sqlite3")
    initialize_manifest_store(manifest_path)
    client = FakeClient([_market("100", ["tok1"])])
    result = populate_initial_polymarket_public_data(
        record_path, manifest_path, _config(allow_network=True), client=client
    )
    assert result.error_codes == ("POPULATION_RECORD_STORE_INVALID",)
    assert client.markets_calls == 0


def test_invalid_manifest_store_makes_no_network_call():
    directory = tempfile.mkdtemp()
    record_path = os.path.join(directory, "records.sqlite3")
    manifest_path = os.path.join(directory, "missing.sqlite3")
    initialize_point_in_time_record_store(record_path)
    client = FakeClient([_market("100", ["tok1"])])
    result = populate_initial_polymarket_public_data(
        record_path, manifest_path, _config(allow_network=True), client=client
    )
    assert result.error_codes == ("POPULATION_MANIFEST_STORE_INVALID",)
    assert client.markets_calls == 0


def test_non_empty_record_store_rejected_without_network():
    record_path, manifest_path = _stores()
    client = FakeClient([_market("100", ["tok1"])])
    first = populate_initial_polymarket_public_data(
        record_path, manifest_path, _config(allow_network=True, markets_limit=1),
        client=client, utcnow_provider=_clock,
    )
    assert first.status == "POPULATION_PERSISTED_AND_REGISTERED"
    second_client = FakeClient([_market("100", ["tok1"])])
    second = populate_initial_polymarket_public_data(
        record_path, manifest_path, _config(allow_network=True, markets_limit=1),
        client=second_client, utcnow_provider=_clock,
    )
    assert second.error_codes == ("POPULATION_RECORD_STORE_NOT_EMPTY",)
    assert second.network_used is False
    assert second_client.markets_calls == 0


# ── Gamma success ─────────────────────────────────────────────────────────────


def test_single_market_population_persists_and_registers():
    record_path, manifest_path = _stores()
    client = FakeClient([_market("100", ["tok1"])])
    result = populate_initial_polymarket_public_data(
        record_path, manifest_path, _config(allow_network=True, markets_limit=1),
        client=client, utcnow_provider=_clock,
    )
    assert result.is_valid is True
    assert result.status == "POPULATION_PERSISTED_AND_REGISTERED"
    assert result.network_used is True
    assert result.fetched_market_count == 1
    assert result.built_record_count == 1
    assert result.inserted_record_count == 1
    assert result.record_store_status == "RECORD_STORE_APPEND_COMMITTED"
    assert result.registration_status == "ADAPTER_PERSISTED"
    assert result.captured_at_utc == "2026-08-14T12:00:00Z"
    assert result.snapshot_id.startswith("snapshot:sha256:")
    assert result.dataset_snapshot_reference_id is not None
    assert result.manifest_entry_id is not None
    snapshot = load_and_verify_point_in_time_record_store(record_path).snapshot
    assert len(snapshot.records) == 1
    record = snapshot.records[0]
    assert record.observation_kind == "MARKET_METADATA"
    assert record.envelope.classification == "PRIMARY_ASSERTION"
    assert record.envelope.lifecycle_state == "NORMALIZED_ACCEPTED"
    assert record.envelope.lineage_parent_ids == ()
    assert record.token_id is None


def test_multiple_markets_are_deterministically_sorted():
    record_path, manifest_path = _stores()
    markets = [_market("300", ["t3"]), _market("100", ["t1"]), _market("200", ["t2"])]
    client = FakeClient(markets)
    result = populate_initial_polymarket_public_data(
        record_path, manifest_path, _config(allow_network=True, markets_limit=3),
        client=client, utcnow_provider=_clock,
    )
    assert result.status == "POPULATION_PERSISTED_AND_REGISTERED"
    assert result.built_record_count == 3
    records = load_and_verify_point_in_time_record_store(record_path).snapshot.records
    market_ids = {r.market_id for r in records}
    assert market_ids == {
        "market:polymarket:100",
        "market:polymarket:200",
        "market:polymarket:300",
    }


def test_response_order_does_not_change_identity():
    def run(order):
        record_path, manifest_path = _stores()
        markets = [_market(mid, [f"tok{mid}a", f"tok{mid}b"]) for mid in order]
        client = FakeClient(
            markets,
            books={f"tok{mid}a": _book(f"tok{mid}a") for mid in order}
            | {f"tok{mid}b": _book(f"tok{mid}b") for mid in order},
        )
        return populate_initial_polymarket_public_data(
            record_path, manifest_path,
            _config(allow_network=True, markets_limit=2, order_books_limit=4),
            client=client, utcnow_provider=_clock,
        )

    forward = run(["100", "200"])
    reverse = run(["200", "100"])
    assert forward.snapshot_id == reverse.snapshot_id
    assert forward.dataset_snapshot_reference_id == reverse.dataset_snapshot_reference_id
    assert forward.manifest_entry_id == reverse.manifest_entry_id


def test_duplicate_market_ids_rejected():
    record_path, manifest_path = _stores()
    client = FakeClient([_market("100", ["a"]), _market("100", ["b"])])
    result = populate_initial_polymarket_public_data(
        record_path, manifest_path, _config(allow_network=True, markets_limit=2),
        client=client, utcnow_provider=_clock,
    )
    assert result.error_codes == ("POPULATION_RESPONSE_INVALID",)
    assert load_and_verify_point_in_time_record_store(record_path).snapshot.records == ()


def test_zero_markets_limit_rejected_in_network_mode():
    record_path, manifest_path = _stores()
    client = FakeClient([_market("100", ["a"])])
    result = populate_initial_polymarket_public_data(
        record_path, manifest_path, _config(allow_network=True, markets_limit=0),
        client=client, utcnow_provider=_clock,
    )
    assert result.error_codes == ("POPULATION_INPUT_INVALID",)
    assert client.markets_calls == 0


# ── Order book success ────────────────────────────────────────────────────────


def test_order_book_population_guards_and_normalizes():
    record_path, manifest_path = _stores()
    client = FakeClient(
        [_market("100", ["tokA", "tokB"])],
        books={"tokA": _book("tokA"), "tokB": _book("tokB")},
    )
    guard = DenyGuard(deny_key=None)  # allow everything, record ordering
    result = populate_initial_polymarket_public_data(
        record_path, manifest_path,
        _config(allow_network=True, markets_limit=1, order_books_limit=1),
        client=client, guard=guard, utcnow_provider=_clock,
    )
    assert result.status == "POPULATION_PERSISTED_AND_REGISTERED"
    assert result.fetched_order_book_count == 1
    assert client.book_calls == ["tokA"]
    # Guard consulted for gamma before clob.
    assert guard.calls == ["gamma_markets", "clob_book"]
    records = load_and_verify_point_in_time_record_store(record_path).snapshot.records
    kinds = sorted(r.observation_kind for r in records)
    assert kinds == ["MARKET_METADATA", "ORDER_BOOK"]
    book = next(r for r in records if r.observation_kind == "ORDER_BOOK")
    assert book.token_id == "token:polymarket:tokA"
    payload = json.loads(book.canonical_payload_json)
    assert payload["tick_size"] == "0.01"
    assert payload["minimum_order_size"] == "1"
    assert payload["bids"] == [{"price": "0.40", "size": "10"}]


def test_ambiguous_token_to_market_mapping_rejected():
    record_path, manifest_path = _stores()
    # Same token appears in two different markets.
    client = FakeClient(
        [_market("100", ["shared"]), _market("200", ["shared"])],
        books={"shared": _book("shared")},
    )
    result = populate_initial_polymarket_public_data(
        record_path, manifest_path,
        _config(allow_network=True, markets_limit=2, order_books_limit=1),
        client=client, utcnow_provider=_clock,
    )
    assert result.error_codes == ("POPULATION_RESPONSE_INVALID",)
    assert load_and_verify_point_in_time_record_store(record_path).snapshot.records == ()


def test_order_book_asset_id_mismatch_rejected():
    record_path, manifest_path = _stores()
    client = FakeClient(
        [_market("100", ["tokA"])],
        books={"tokA": _book("tokA", asset_id="WRONG")},
    )
    result = populate_initial_polymarket_public_data(
        record_path, manifest_path,
        _config(allow_network=True, markets_limit=1, order_books_limit=1),
        client=client, utcnow_provider=_clock,
    )
    assert result.error_codes == ("POPULATION_RESPONSE_INVALID",)
    assert load_and_verify_manifest_store(manifest_path).snapshot.manifest_entries == ()


# ── Network failure ───────────────────────────────────────────────────────────


def test_guard_denied_before_gamma_makes_no_call():
    record_path, manifest_path = _stores()
    client = FakeClient([_market("100", ["a"])])
    guard = DenyGuard(deny_key="gamma_markets")
    result = populate_initial_polymarket_public_data(
        record_path, manifest_path, _config(allow_network=True, markets_limit=1),
        client=client, guard=guard, utcnow_provider=_clock,
    )
    assert result.error_codes == ("POPULATION_GUARD_DENIED",)
    assert client.markets_calls == 0


def test_guard_denied_before_book_persists_nothing():
    record_path, manifest_path = _stores()
    client = FakeClient(
        [_market("100", ["tokA"])], books={"tokA": _book("tokA")}
    )
    guard = DenyGuard(deny_key="clob_book")
    result = populate_initial_polymarket_public_data(
        record_path, manifest_path,
        _config(allow_network=True, markets_limit=1, order_books_limit=1),
        client=client, guard=guard, utcnow_provider=_clock,
    )
    assert result.error_codes == ("POPULATION_GUARD_DENIED",)
    assert load_and_verify_point_in_time_record_store(record_path).snapshot.records == ()
    assert load_and_verify_manifest_store(manifest_path).snapshot.manifest_entries == ()


@pytest.mark.parametrize("status", [429, 500, 503])
def test_gamma_non_2xx_rejected(status):
    record_path, manifest_path = _stores()
    client = FakeClient([_market("100", ["a"])], markets_status=status)
    result = populate_initial_polymarket_public_data(
        record_path, manifest_path, _config(allow_network=True, markets_limit=1),
        client=client, utcnow_provider=_clock,
    )
    assert result.error_codes == ("POPULATION_RESPONSE_INVALID",)


def test_gamma_network_exception_is_fetch_failed():
    record_path, manifest_path = _stores()
    client = RaisingClient(RuntimeError("boom https://secret.invalid/path"))
    result = populate_initial_polymarket_public_data(
        record_path, manifest_path, _config(allow_network=True, markets_limit=1),
        client=client, utcnow_provider=_clock,
    )
    assert result.error_codes == ("POPULATION_FETCH_FAILED",)


def test_malformed_gamma_item_rejected():
    record_path, manifest_path = _stores()
    client = FakeClient([_market("100", ["a"]), "not-a-dict"])
    result = populate_initial_polymarket_public_data(
        record_path, manifest_path, _config(allow_network=True, markets_limit=2),
        client=client, utcnow_provider=_clock,
    )
    assert result.error_codes == ("POPULATION_RESPONSE_INVALID",)


def test_malformed_clob_response_rejected_and_no_write():
    record_path, manifest_path = _stores()
    bad_book = {"asset_id": "tokA", "bids": "notalist", "asks": [], "tick_size": "0.01", "min_order_size": "1"}
    client = FakeClient([_market("100", ["tokA"])], books={"tokA": bad_book})
    result = populate_initial_polymarket_public_data(
        record_path, manifest_path,
        _config(allow_network=True, markets_limit=1, order_books_limit=1),
        client=client, utcnow_provider=_clock,
    )
    assert result.error_codes == ("POPULATION_RESPONSE_INVALID",)
    assert load_and_verify_point_in_time_record_store(record_path).snapshot.records == ()


# ── Build / payload ───────────────────────────────────────────────────────────


def test_empty_outcomes_rejected_by_builder():
    record_path, manifest_path = _stores()
    client = FakeClient([_market("100", ["a"], outcomes=[])])
    result = populate_initial_polymarket_public_data(
        record_path, manifest_path, _config(allow_network=True, markets_limit=1),
        client=client, utcnow_provider=_clock,
    )
    assert result.error_codes == ("POPULATION_BUILD_FAILED",)
    assert load_and_verify_point_in_time_record_store(record_path).snapshot.records == ()


def test_normalized_payload_excludes_float_fields():
    record_path, manifest_path = _stores()
    market = _market("100", ["a"])
    market["liquidity"] = 12.5  # a float API field that must never enter the payload
    client = FakeClient([market])
    result = populate_initial_polymarket_public_data(
        record_path, manifest_path, _config(allow_network=True, markets_limit=1),
        client=client, utcnow_provider=_clock,
    )
    assert result.status == "POPULATION_PERSISTED_AND_REGISTERED"
    record = load_and_verify_point_in_time_record_store(record_path).snapshot.records[0]
    payload = json.loads(record.canonical_payload_json)
    assert "liquidity" not in payload
    assert set(payload) == {
        "question_text",
        "market_status",
        "outcome_labels",
        "condition_id",
        "token_ids",
        "resolution_date",
        "category",
        "raw_field_names",
    }
    assert "liquidity" in payload["raw_field_names"]


# ── Persistence order ─────────────────────────────────────────────────────────


def test_record_append_failure_creates_no_manifest_reference(monkeypatch):
    record_path, manifest_path = _stores()

    class _Fail:
        is_valid = False
        status = "RECORD_STORE_REJECTED"
        error_codes = ("RECORD_STORE_WRITE_FAILED",)
        snapshot = None
        inserted_record_version_ids = ()

    monkeypatch.setattr(pop, "append_point_in_time_records", lambda *a, **k: _Fail())
    register_calls = []
    real_register = pop.persist_validated_record_batch_snapshot
    monkeypatch.setattr(
        pop,
        "persist_validated_record_batch_snapshot",
        lambda *a, **k: register_calls.append(1) or real_register(*a, **k),
    )
    client = FakeClient([_market("100", ["a"])])
    result = populate_initial_polymarket_public_data(
        record_path, manifest_path, _config(allow_network=True, markets_limit=1),
        client=client, utcnow_provider=_clock,
    )
    assert result.error_codes == ("POPULATION_RECORD_APPEND_FAILED",)
    assert result.record_store_error_codes == ("RECORD_STORE_WRITE_FAILED",)
    assert register_calls == []
    assert load_and_verify_manifest_store(manifest_path).snapshot.manifest_entries == ()


def test_registration_failure_keeps_records_and_requires_recovery(monkeypatch):
    record_path, manifest_path = _stores()

    class _Rejected:
        is_valid = False
        status = "ADAPTER_REJECTED"
        error_codes = ("ADAPTER_STORE_APPEND_FAILED",)
        dataset_reference = None
        manifest_entry = None

    monkeypatch.setattr(
        pop, "persist_validated_record_batch_snapshot", lambda *a, **k: _Rejected()
    )
    client = FakeClient([_market("100", ["a"])])
    result = populate_initial_polymarket_public_data(
        record_path, manifest_path, _config(allow_network=True, markets_limit=1),
        client=client, utcnow_provider=_clock,
    )
    assert result.status == "POPULATION_RECORDS_PERSISTED_REGISTRATION_FAILED"
    assert result.is_valid is False
    assert result.recovery_required is True
    assert result.network_used is True
    assert result.record_store_status == "RECORD_STORE_APPEND_COMMITTED"
    assert result.registration_error_codes == ("ADAPTER_STORE_APPEND_FAILED",)
    assert result.dataset_snapshot_reference_id is None
    assert result.manifest_entry_id is None
    # Records remain committed.
    assert len(load_and_verify_point_in_time_record_store(record_path).snapshot.records) == 1


# ── Recovery ──────────────────────────────────────────────────────────────────


def _seed_unregistered(monkeypatch_ctx, record_path, manifest_path, cfg):
    """Populate records but force registration to fail, leaving an unregistered seed."""

    class _Rejected:
        is_valid = False
        status = "ADAPTER_REJECTED"
        error_codes = ("ADAPTER_STORE_APPEND_FAILED",)
        dataset_reference = None
        manifest_entry = None

    original = pop.persist_validated_record_batch_snapshot
    pop.persist_validated_record_batch_snapshot = lambda *a, **k: _Rejected()
    try:
        client = FakeClient(
            [_market("100", ["tokA"])], books={"tokA": _book("tokA")}
        )
        result = populate_initial_polymarket_public_data(
            record_path, manifest_path, cfg, client=client, utcnow_provider=_clock
        )
    finally:
        pop.persist_validated_record_batch_snapshot = original
    assert result.status == "POPULATION_RECORDS_PERSISTED_REGISTRATION_FAILED"


def test_offline_recovery_after_registration_failure():
    record_path, manifest_path = _stores()
    cfg = _config(allow_network=True, markets_limit=1, order_books_limit=1)
    _seed_unregistered(None, record_path, manifest_path, cfg)
    recovered = recover_initial_polymarket_public_registration(
        record_path, manifest_path, cfg
    )
    assert recovered.status == "POPULATION_RECOVERED_REGISTRATION"
    assert recovered.is_valid is True
    assert recovered.network_used is False
    assert recovered.recovery_required is False
    assert recovered.dataset_snapshot_reference_id is not None
    assert recovered.manifest_entry_id is not None
    assert len(load_and_verify_manifest_store(manifest_path).snapshot.manifest_entries) == 1


def test_recovery_is_idempotent_when_already_registered():
    record_path, manifest_path = _stores()
    cfg = _config(allow_network=True, markets_limit=1)
    client = FakeClient([_market("100", ["a"])])
    populate_initial_polymarket_public_data(
        record_path, manifest_path, cfg, client=client, utcnow_provider=_clock
    )
    recovered = recover_initial_polymarket_public_registration(
        record_path, manifest_path, cfg
    )
    assert recovered.status == "POPULATION_ALREADY_REGISTERED"
    assert recovered.is_valid is True
    assert recovered.network_used is False


def test_recovery_rejects_empty_store():
    record_path, manifest_path = _stores()
    recovered = recover_initial_polymarket_public_registration(
        record_path, manifest_path, _config()
    )
    assert recovered.error_codes == ("POPULATION_RECOVERY_INVALID",)


def test_recovery_rejects_mismatched_provenance():
    record_path, manifest_path = _stores()
    cfg = _config(allow_network=True, markets_limit=1)
    client = FakeClient([_market("100", ["a"])])
    populate_initial_polymarket_public_data(
        record_path, manifest_path, cfg, client=client, utcnow_provider=_clock
    )
    other = _config(parameter_set_id="params:OTHER")
    recovered = recover_initial_polymarket_public_registration(
        record_path, manifest_path, other
    )
    assert recovered.error_codes == ("POPULATION_RECOVERY_INVALID",)


# ── No echo ───────────────────────────────────────────────────────────────────


def test_failure_result_never_echoes_secret_url_or_question():
    record_path, manifest_path = _stores()
    marker = "SECRET_MARKER_c0ffee"
    url = "https://secret.invalid/leak?token=abc"
    client = RaisingClient(RuntimeError(f"{marker} {url}"))
    result = populate_initial_polymarket_public_data(
        record_path, manifest_path, _config(allow_network=True, markets_limit=1),
        client=client, utcnow_provider=_clock,
    )
    text = repr(result)
    assert marker not in text
    assert url not in text
    assert "secret.invalid" not in text


def test_build_failure_does_not_expose_question_text():
    record_path, manifest_path = _stores()
    client = FakeClient(
        [_market("100", ["a"], question="SUPERSECRETQUESTION", outcomes=[])]
    )
    result = populate_initial_polymarket_public_data(
        record_path, manifest_path, _config(allow_network=True, markets_limit=1),
        client=client, utcnow_provider=_clock,
    )
    assert result.error_codes == ("POPULATION_BUILD_FAILED",)
    assert "SUPERSECRETQUESTION" not in repr(result)


# ── Security source scan ──────────────────────────────────────────────────────


def _module_source() -> str:
    import importlib.util

    spec = importlib.util.find_spec(
        "src.data_layer.point_in_time_market_research.polymarket_public_population"
    )
    assert spec is not None and spec.origin is not None
    with open(spec.origin, "r", encoding="utf-8") as handle:
        return handle.read()


def _imported_top_level_modules() -> set[str]:
    import ast

    tree = ast.parse(_module_source())
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                modules.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0 and node.module:
                modules.add(node.module.split(".")[0])
    return modules


def _identifier_tokens() -> set[str]:
    """Return NAME tokens only, excluding all string and comment tokens.

    This is token-aware, so descriptive text inside docstrings/comments (which
    legitimately names forbidden concepts) never produces a false positive.
    """

    import io
    import tokenize

    identifiers: set[str] = set()
    reader = io.StringIO(_module_source()).readline
    for tok in tokenize.generate_tokens(reader):
        if tok.type == tokenize.NAME:
            identifiers.add(tok.string)
    return identifiers


def _attribute_names() -> set[str]:
    import ast

    tree = ast.parse(_module_source())
    return {
        node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)
    }


def test_module_has_no_direct_network_or_forbidden_imports():
    modules = _imported_top_level_modules()
    for forbidden in (
        "urllib",
        "requests",
        "httpx",
        "aiohttp",
        "websockets",
        "socket",
        "subprocess",
        "os",
    ):
        assert forbidden not in modules, forbidden


def test_module_has_no_forbidden_identifiers_in_code():
    identifiers = _identifier_tokens()
    for forbidden in (
        "environ",
        "getenv",
        "snapshot_writer",
        "write_snapshots",
        "capture_market_snapshots",
        "local_data",
        "get_health",
        "get_market",
        "place_order",
        "cancel_order",
        "sleep",
    ):
        assert forbidden not in identifiers, forbidden
    # ``get_markets`` (plural) is allowed and distinct from ``get_market``.
    assert "get_markets" in identifiers


def test_module_has_no_scheduler_loop_or_retry_constructs():
    import ast

    tree = ast.parse(_module_source())
    for node in ast.walk(tree):
        assert not isinstance(node, (ast.While, ast.AsyncFor, ast.AsyncFunctionDef))


def test_module_only_uses_get_only_client_methods():
    attributes = _attribute_names()
    assert "get_markets" in attributes
    assert "get_order_book_snapshot" in attributes
    for forbidden in ("get_health", "get_market", "get_books", "post"):
        assert forbidden not in attributes, forbidden
