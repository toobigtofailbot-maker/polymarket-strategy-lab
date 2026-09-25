"""Focused tests for the WP164 bounded real/public Polymarket population.

These tests never touch the network. Every network-capable path is exercised with
an injected fake GET-only client, an injected guard, and a fixed clock.
"""

from __future__ import annotations

import datetime
import json
import os
import tempfile
from pathlib import Path
from types import SimpleNamespace

import pytest
from tools.polymarket import run_wp164a_public_smoke as smoke

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


def _market(
    gamma_id: str,
    tokens,
    *,
    condition=None,
    question=None,
    outcomes=None,
    active=True,
    closed=False,
):
    return {
        "id": gamma_id,
        "conditionId": condition if condition is not None else f"0xcond{gamma_id}",
        "question": question if question is not None else f"Question {gamma_id}",
        "active": active,
        "closed": closed,
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


def _advancing_now():
    """An injected monotonic surrogate that satisfies every conservative interval.

    This lives only in tests; production never fabricates elapsed guard time.
    """

    state = {"t": 0.0}

    def _next() -> float:
        state["t"] += 3600.0
        return state["t"]

    return _next


def _raise(exc):
    def _boom(*args, **kwargs):
        raise exc

    return _boom


def _smoke_envelope(root: Path, phase_sha: str) -> tuple[dict, str, str]:
    tracked = {
        smoke.PROMPT_PATH: b"prompt",
        smoke.SPEC_PATH: b"spec",
        smoke.CONTRACT_PATH: b"contract",
        smoke.OPERATOR_PATH: Path(smoke.__file__).read_bytes(),
    }
    for relative, payload in tracked.items():
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
    workspace = f"local_data/wp164a_public_smoke/{phase_sha}/attempt-03"
    envelope_path = workspace + ".authorization.json"
    mapping = {
        "schema_id": smoke.ENVELOPE_SCHEMA_ID,
        "schema_version": smoke.ENVELOPE_SCHEMA_VERSION,
        "wp_id": smoke.WP_ID,
        "base_sha": smoke.BASE_SHA,
        "phase_a_commit_sha": phase_sha,
        "wp_prompt_sha256": smoke._sha256_bytes(tracked[smoke.PROMPT_PATH]),
        "wp_spec_sha256": smoke._sha256_bytes(tracked[smoke.SPEC_PATH]),
        "contract_sha256": smoke._sha256_bytes(tracked[smoke.CONTRACT_PATH]),
        "operator_path": smoke.OPERATOR_PATH,
        "operator_sha256": smoke._sha256_bytes(tracked[smoke.OPERATOR_PATH]),
        "workspace_attempt_id": smoke.WORKSPACE_ATTEMPT_ID,
        "workspace_relpath": workspace,
        "manifest_id": smoke.MANIFEST_ID,
        "parameter_set_id": smoke.PARAMETER_SET_ID,
        "normalizer_version": smoke.NORMALIZER_VERSION,
        "validator_version": smoke.VALIDATOR_VERSION,
        "markets_limit": smoke.MARKETS_LIMIT,
        "order_books_limit": smoke.ORDER_BOOKS_LIMIT,
        "max_coordinator_invocations": smoke.MAX_COORDINATOR_INVOCATIONS,
        "retry_limit": smoke.RETRY_LIMIT,
        "replacement_invocation_authorized": False,
        "public_network_authorized": True,
        "hermes_provider_authorized": False,
        "h1_fifth_invocation_authorized": False,
        "af1_attempt_03_authorized": False,
        "merge_authorized": False,
        "credentials_authorized": False,
        "scheduler_authorized": False,
    }
    target = root / envelope_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(smoke._canonical_json_bytes(mapping))
    return mapping, workspace, envelope_path


def _prepare_smoke_repo(monkeypatch, tmp_path: Path):
    phase_sha = "5" * 40
    (tmp_path / ".git").mkdir()
    envelope, workspace, envelope_path = _smoke_envelope(tmp_path, phase_sha)
    monkeypatch.setattr(smoke, "REPO_ROOT", tmp_path)
    monkeypatch.chdir(tmp_path)

    def _fake_git(*args):
        if args == ("rev-parse", "HEAD"):
            return phase_sha
        if args == ("branch", "--show-current"):
            return smoke.BRANCH
        if args == ("rev-parse", "origin/main"):
            return smoke.BASE_SHA
        if args == ("merge-base", "--is-ancestor", smoke.BASE_SHA, phase_sha):
            return ""
        if args == ("status", "--porcelain"):
            return ""
        raise AssertionError(args)

    monkeypatch.setattr(smoke, "_git", _fake_git)
    argv = [
        "--workspace",
        workspace,
        "--authorization-envelope",
        envelope_path,
        "--allow-public-network",
        "--acknowledgement",
        smoke.ACKNOWLEDGEMENT,
    ]
    return envelope, workspace, envelope_path, argv


# ── Forgery builders for recovery re-proof tests ──────────────────────────────

from src.data_layer.point_in_time_market_research.records import (  # noqa: E402
    PointInTimeBatchValidationResult,
    SUPPORTED_SCHEMA_ID,
    SUPPORTED_SCHEMA_VERSION,
    build_market_observation,
    validate_record_batch,
)


def _gamma_payload(condition="0xcond100", tokens=("tokA",)):
    return {
        "question_text": "Q",
        "market_status": "open",
        "outcome_labels": ["Yes", "No"],
        "condition_id": condition,
        "token_ids": list(tokens),
        "resolution_date": None,
        "category": None,
        "raw_field_names": ["id"],
    }


def _clob_payload():
    return {
        "bids": [{"price": "0.4", "size": "1"}],
        "asks": [{"price": "0.6", "size": "1"}],
        "tick_size": "0.01",
        "minimum_order_size": "1",
        "clob_timestamp": None,
        "book_hash": None,
        "last_trade_price": None,
        "raw_field_names": ["asks", "bids"],
    }


def _make_gamma_record(
    cfg,
    *,
    snapshot_id,
    ingestion_batch_id,
    captured,
    market_id="market:polymarket:100",
    event_id="event:polymarket:0xcond100",
    payload=None,
    source_snapshot_id=None,
    source_assertion_id=None,
):
    payload = payload if payload is not None else _gamma_payload()
    if source_snapshot_id is None:
        source_snapshot_id = pop._content_id(
            "srcsnap:sha256:",
            {
                "source_id": pop._GAMMA_SOURCE_ID,
                "market_id": market_id,
                "snapshot_id": snapshot_id,
                "canonical_payload": payload,
            },
        )
    if source_assertion_id is None:
        source_assertion_id = pop._content_id(
            "assertion:sha256:",
            {
                "source_snapshot_id": source_snapshot_id,
                "observation_kind": "MARKET_METADATA",
                "market_id": market_id,
                "event_id": event_id,
                "token_id": None,
            },
        )
    inp = {
        "schema_id": SUPPORTED_SCHEMA_ID,
        "schema_version": SUPPORTED_SCHEMA_VERSION,
        "record_family": "MARKET_OBSERVATION",
        "observation_kind": "MARKET_METADATA",
        "platform_id": pop._PLATFORM_ID,
        "event_id": event_id,
        "market_id": market_id,
        "token_id": None,
        "source_id": pop._GAMMA_SOURCE_ID,
        "source_assertion_id": source_assertion_id,
        "source_snapshot_id": source_snapshot_id,
        "snapshot_id": snapshot_id,
        "ingestion_batch_id": ingestion_batch_id,
        "event_time": None,
        "observed_time": captured,
        "ingestion_time": captured,
        "lifecycle_state": "NORMALIZED_ACCEPTED",
        "classification": "PRIMARY_ASSERTION",
        "lineage_parent_ids": [],
        "supersedes_record_version_id": None,
        "normalizer_version": cfg.normalizer_version,
        "validator_version": cfg.validator_version,
        "parameter_set_id": cfg.parameter_set_id,
        "human_review_required": False,
        "canonical_payload": payload,
    }
    result = build_market_observation(inp)
    assert result.is_valid, result.error_codes
    return result.record


def _make_book_record(
    cfg,
    *,
    snapshot_id,
    ingestion_batch_id,
    captured,
    raw_token,
    market_id="market:polymarket:100",
    event_id="event:polymarket:0xcond100",
    payload=None,
):
    payload = payload if payload is not None else _clob_payload()
    parent = {"market_id": market_id, "event_id": event_id}
    return pop._build_order_book_record(
        parent,
        raw_token,
        payload,
        snapshot_id=snapshot_id,
        ingestion_batch_id=ingestion_batch_id,
        captured_at_utc=captured,
        config=cfg,
    )


_ARB_SNAPSHOT = "snapshot:sha256:" + "a" * 64
_ARB_INGEST = "ingest:sha256:" + "b" * 64
_ARB_TIME = "2026-08-14T12:00:00Z"


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
    """A genuine-typed success result with caller-supplied nested objects."""

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


def _genuine_reference_and_entry():
    record_path, manifest_path = _stores()
    client = FakeClient([_market("999", ["ztok"])])
    populate_initial_polymarket_public_data(
        record_path,
        manifest_path,
        _config(allow_network=True, markets_limit=1),
        client=client,
        utcnow_provider=_clock,
    )
    snapshot = load_and_verify_manifest_store(manifest_path).snapshot
    return snapshot.dataset_references[0], snapshot.manifest_entries[0]


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


def test_package_exports_contain_the_exact_contiguous_wp164_block():
    # Future-safe: the eight WP164 symbols must appear as one contiguous block
    # starting at POLYMARKET_PUBLIC_POPULATION_LABEL, wherever successor WPs append
    # their own exports afterward.
    expected = (
        "POLYMARKET_PUBLIC_POPULATION_LABEL",
        "POLYMARKET_PUBLIC_POPULATION_POSTURE",
        "POLYMARKET_PUBLIC_POPULATION_STATUSES",
        "POLYMARKET_PUBLIC_POPULATION_ERROR_CODES",
        "PolymarketPublicPopulationConfig",
        "PolymarketPublicPopulationResult",
        "populate_initial_polymarket_public_data",
        "recover_initial_polymarket_public_registration",
    )
    start = pit.__all__.index("POLYMARKET_PUBLIC_POPULATION_LABEL")
    assert pit.__all__[start : start + 8] == expected
    assert all(getattr(pit, name) is getattr(pop, name) for name in expected)


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
    assert (
        result.fetched_market_count,
        result.built_record_count,
        result.inserted_record_count,
    ) == (0, 0, 0)
    assert client.markets_calls == 0
    assert (
        load_and_verify_point_in_time_record_store(record_path).snapshot.records == ()
    )
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
        record_path,
        manifest_path,
        _config(allow_network=True, markets_limit=1),
        client=client,
        utcnow_provider=_clock,
    )
    assert first.status == "POPULATION_PERSISTED_AND_REGISTERED"
    second_client = FakeClient([_market("100", ["tok1"])])
    second = populate_initial_polymarket_public_data(
        record_path,
        manifest_path,
        _config(allow_network=True, markets_limit=1),
        client=second_client,
        utcnow_provider=_clock,
    )
    assert second.error_codes == ("POPULATION_RECORD_STORE_NOT_EMPTY",)
    assert second.network_used is False
    assert second_client.markets_calls == 0


# ── Gamma success ─────────────────────────────────────────────────────────────


def test_single_market_population_persists_and_registers():
    record_path, manifest_path = _stores()
    client = FakeClient([_market("100", ["tok1"])])
    result = populate_initial_polymarket_public_data(
        record_path,
        manifest_path,
        _config(allow_network=True, markets_limit=1),
        client=client,
        utcnow_provider=_clock,
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
        record_path,
        manifest_path,
        _config(allow_network=True, markets_limit=3),
        client=client,
        utcnow_provider=_clock,
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
        # An injected time sequence satisfying the guard intervals lets the
        # multi-book run complete so identity determinism is actually proven.
        return populate_initial_polymarket_public_data(
            record_path,
            manifest_path,
            _config(allow_network=True, markets_limit=2, order_books_limit=4),
            client=client,
            now_provider=_advancing_now(),
            utcnow_provider=_clock,
        )

    forward = run(["100", "200"])
    reverse = run(["200", "100"])
    assert forward.status == "POPULATION_PERSISTED_AND_REGISTERED"
    assert reverse.status == "POPULATION_PERSISTED_AND_REGISTERED"
    assert forward.snapshot_id is not None
    assert forward.snapshot_id == reverse.snapshot_id
    assert (
        forward.dataset_snapshot_reference_id == reverse.dataset_snapshot_reference_id
    )
    assert forward.manifest_entry_id == reverse.manifest_entry_id


def test_duplicate_market_ids_rejected():
    record_path, manifest_path = _stores()
    client = FakeClient([_market("100", ["a"]), _market("100", ["b"])])
    result = populate_initial_polymarket_public_data(
        record_path,
        manifest_path,
        _config(allow_network=True, markets_limit=2),
        client=client,
        utcnow_provider=_clock,
    )
    assert result.error_codes == ("POPULATION_RESPONSE_INVALID",)
    assert (
        load_and_verify_point_in_time_record_store(record_path).snapshot.records == ()
    )


def test_zero_markets_limit_rejected_in_network_mode():
    record_path, manifest_path = _stores()
    client = FakeClient([_market("100", ["a"])])
    result = populate_initial_polymarket_public_data(
        record_path,
        manifest_path,
        _config(allow_network=True, markets_limit=0),
        client=client,
        utcnow_provider=_clock,
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
        record_path,
        manifest_path,
        _config(allow_network=True, markets_limit=1, order_books_limit=1),
        client=client,
        guard=guard,
        utcnow_provider=_clock,
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


def test_large_valid_order_book_population_persists_and_registers():
    record_path, manifest_path = _stores()
    bids = tuple((f"0.{index:03d}", str(index)) for index in range(1, 129))
    asks = tuple(
        (f"0.{index + 200:03d}", str(index)) for index in range(1, 129)
    )
    client = FakeClient(
        [_market("100", ["tokA"])],
        books={"tokA": _book("tokA", bids=bids, asks=asks)},
    )

    result = populate_initial_polymarket_public_data(
        record_path,
        manifest_path,
        _config(allow_network=True, markets_limit=1, order_books_limit=1),
        client=client,
        guard=DenyGuard(deny_key=None),
        utcnow_provider=_clock,
    )

    assert result.is_valid is True
    assert result.status == "POPULATION_PERSISTED_AND_REGISTERED"
    assert result.error_codes == ()
    assert result.fetched_market_count == 1
    assert result.fetched_order_book_count == 1
    assert result.built_record_count == 2
    assert result.inserted_record_count == 2
    assert result.registration_status == "ADAPTER_PERSISTED"
    assert result.dataset_snapshot_reference_id is not None
    assert result.manifest_entry_id is not None
    assert client.markets_calls == 1
    assert client.book_calls == ["tokA"]

    records = load_and_verify_point_in_time_record_store(record_path).snapshot.records
    book = next(record for record in records if record.observation_kind == "ORDER_BOOK")
    assert len(book.canonical_payload_json) > 4096
    assert (
        "RECORD_VERSION_HASH_COLLISION_OR_MISMATCH" not in result.error_codes
    )
    manifest = load_and_verify_manifest_store(manifest_path).snapshot
    assert len(manifest.dataset_references) == 1
    assert len(manifest.manifest_entries) == 1


def test_ambiguous_token_to_market_mapping_rejected():
    record_path, manifest_path = _stores()
    # Same token appears in two different markets.
    client = FakeClient(
        [_market("100", ["shared"]), _market("200", ["shared"])],
        books={"shared": _book("shared")},
    )
    result = populate_initial_polymarket_public_data(
        record_path,
        manifest_path,
        _config(allow_network=True, markets_limit=2, order_books_limit=1),
        client=client,
        utcnow_provider=_clock,
    )
    assert result.error_codes == ("POPULATION_RESPONSE_INVALID",)
    assert (
        load_and_verify_point_in_time_record_store(record_path).snapshot.records == ()
    )


def test_order_book_asset_id_mismatch_rejected():
    record_path, manifest_path = _stores()
    client = FakeClient(
        [_market("100", ["tokA"])],
        books={"tokA": _book("tokA", asset_id="WRONG")},
    )
    result = populate_initial_polymarket_public_data(
        record_path,
        manifest_path,
        _config(allow_network=True, markets_limit=1, order_books_limit=1),
        client=client,
        utcnow_provider=_clock,
    )
    assert result.error_codes == ("POPULATION_RESPONSE_INVALID",)
    assert load_and_verify_manifest_store(manifest_path).snapshot.manifest_entries == ()


# ── Network failure ───────────────────────────────────────────────────────────


def test_guard_denied_before_gamma_makes_no_call():
    record_path, manifest_path = _stores()
    client = FakeClient([_market("100", ["a"])])
    guard = DenyGuard(deny_key="gamma_markets")
    result = populate_initial_polymarket_public_data(
        record_path,
        manifest_path,
        _config(allow_network=True, markets_limit=1),
        client=client,
        guard=guard,
        utcnow_provider=_clock,
    )
    assert result.error_codes == ("POPULATION_GUARD_DENIED",)
    assert client.markets_calls == 0


def test_guard_denied_before_book_persists_nothing():
    record_path, manifest_path = _stores()
    client = FakeClient([_market("100", ["tokA"])], books={"tokA": _book("tokA")})
    guard = DenyGuard(deny_key="clob_book")
    result = populate_initial_polymarket_public_data(
        record_path,
        manifest_path,
        _config(allow_network=True, markets_limit=1, order_books_limit=1),
        client=client,
        guard=guard,
        utcnow_provider=_clock,
    )
    assert result.error_codes == ("POPULATION_GUARD_DENIED",)
    assert (
        load_and_verify_point_in_time_record_store(record_path).snapshot.records == ()
    )
    assert load_and_verify_manifest_store(manifest_path).snapshot.manifest_entries == ()


@pytest.mark.parametrize("status", [429, 500, 503])
def test_gamma_non_2xx_rejected(status):
    record_path, manifest_path = _stores()
    client = FakeClient([_market("100", ["a"])], markets_status=status)
    result = populate_initial_polymarket_public_data(
        record_path,
        manifest_path,
        _config(allow_network=True, markets_limit=1),
        client=client,
        utcnow_provider=_clock,
    )
    assert result.error_codes == ("POPULATION_RESPONSE_INVALID",)


def test_gamma_network_exception_is_fetch_failed():
    record_path, manifest_path = _stores()
    client = RaisingClient(RuntimeError("boom https://secret.invalid/path"))
    result = populate_initial_polymarket_public_data(
        record_path,
        manifest_path,
        _config(allow_network=True, markets_limit=1),
        client=client,
        utcnow_provider=_clock,
    )
    assert result.error_codes == ("POPULATION_FETCH_FAILED",)


def test_malformed_gamma_item_rejected():
    record_path, manifest_path = _stores()
    client = FakeClient([_market("100", ["a"]), "not-a-dict"])
    result = populate_initial_polymarket_public_data(
        record_path,
        manifest_path,
        _config(allow_network=True, markets_limit=2),
        client=client,
        utcnow_provider=_clock,
    )
    assert result.error_codes == ("POPULATION_RESPONSE_INVALID",)


def test_malformed_clob_response_rejected_and_no_write():
    record_path, manifest_path = _stores()
    bad_book = {
        "asset_id": "tokA",
        "bids": "notalist",
        "asks": [],
        "tick_size": "0.01",
        "min_order_size": "1",
    }
    client = FakeClient([_market("100", ["tokA"])], books={"tokA": bad_book})
    result = populate_initial_polymarket_public_data(
        record_path,
        manifest_path,
        _config(allow_network=True, markets_limit=1, order_books_limit=1),
        client=client,
        utcnow_provider=_clock,
    )
    assert result.error_codes == ("POPULATION_RESPONSE_INVALID",)
    assert (
        load_and_verify_point_in_time_record_store(record_path).snapshot.records == ()
    )


# ── Build / payload ───────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("tokens", "outcomes", "expected_build_errors"),
    [
        (("a",), [], ("FIELD_TYPE_INVALID",)),
        (
            tuple(f"token-{index}" for index in range(257)),
            None,
            ("PAYLOAD_SEQUENCE_LIMIT_EXCEEDED",),
        ),
    ],
)
def test_metadata_build_failure_retains_closed_wp156_diagnostics(
    tokens, outcomes, expected_build_errors
):
    record_path, manifest_path = _stores()
    client = FakeClient([_market("100", tokens, outcomes=outcomes)])
    result = populate_initial_polymarket_public_data(
        record_path,
        manifest_path,
        _config(allow_network=True, markets_limit=1),
        client=client,
        utcnow_provider=_clock,
    )
    assert result.error_codes == ("POPULATION_BUILD_FAILED",)
    assert result.build_failure_observation_kind == "MARKET_METADATA"
    assert result.build_status == "REJECTED_CONTRACT"
    assert result.build_error_codes == expected_build_errors
    assert result.build_warning_codes == ("EVENT_TIME_MISSING_ALLOWED",)
    assert result.build_quarantine_id is not None
    assert result.build_input_fingerprint_sha256 is not None
    assert result.snapshot_id is not None
    assert result.captured_at_utc == "2026-08-14T12:00:00Z"
    assert (result.fetched_market_count, result.built_record_count) == (1, 0)
    assert result.batch_is_valid is None
    assert result.batch_status is None
    assert result.batch_error_codes == ()
    assert (
        load_and_verify_point_in_time_record_store(record_path).snapshot.records == ()
    )
    assert load_and_verify_manifest_store(manifest_path).snapshot.manifest_entries == ()


def test_normalized_payload_excludes_float_fields():
    record_path, manifest_path = _stores()
    market = _market("100", ["a"])
    market["liquidity"] = 12.5  # a float API field that must never enter the payload
    client = FakeClient([market])
    result = populate_initial_polymarket_public_data(
        record_path,
        manifest_path,
        _config(allow_network=True, markets_limit=1),
        client=client,
        utcnow_provider=_clock,
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


# ── WP164A compatibility repair matrix ──────────────────────────────────────


def test_wp164a_complete_batch_diagnostics_are_retained(monkeypatch):
    accepted_id = "a" * 64
    duplicate_id = "b" * 64
    quarantined_id = "c" * 64
    typed_batch = PointInTimeBatchValidationResult(
        is_valid=False,
        status="REJECTED_CONTRACT",
        error_codes=("FIELD_TYPE_INVALID",),
        warning_codes=("EVENT_TIME_MISSING_ALLOWED",),
        accepted_record_version_ids=(accepted_id,),
        exact_duplicate_record_version_ids=(duplicate_id,),
        quarantined_record_version_ids=(quarantined_id,),
        canonical_batch_sha256="d" * 64,
    )
    monkeypatch.setattr(pop, "validate_record_batch", lambda records: typed_batch)
    record_path, manifest_path = _stores()
    result = populate_initial_polymarket_public_data(
        record_path,
        manifest_path,
        _config(allow_network=True, markets_limit=1),
        client=FakeClient([_market("100", ["tok1"])]),
        utcnow_provider=_clock,
    )

    assert result.error_codes == ("POPULATION_BATCH_INVALID",)
    assert result.batch_is_valid is typed_batch.is_valid
    assert result.batch_status == typed_batch.status
    assert result.batch_error_codes == typed_batch.error_codes
    assert result.batch_warning_codes == typed_batch.warning_codes
    assert (
        result.batch_accepted_record_version_ids
        == typed_batch.accepted_record_version_ids
    )
    assert (
        result.batch_exact_duplicate_record_version_ids
        == typed_batch.exact_duplicate_record_version_ids
    )
    assert (
        result.batch_quarantined_record_version_ids
        == typed_batch.quarantined_record_version_ids
    )
    assert result.canonical_batch_sha256 == typed_batch.canonical_batch_sha256
    assert (result.fetched_market_count, result.built_record_count) == (1, 1)
    rendered = repr(result)
    assert "Question 100" not in rendered
    assert "example.invalid" not in rendered
    assert record_path not in rendered and manifest_path not in rendered


def test_wp164a_stronger_batch_rejection_retains_valid_typed_result(monkeypatch):
    captured = {}

    def _valid_but_incomplete(records):
        captured["batch"] = PointInTimeBatchValidationResult(
            is_valid=True,
            status="VALID",
            error_codes=(),
            warning_codes=(),
            accepted_record_version_ids=(records[0].envelope.record_version_id,),
            exact_duplicate_record_version_ids=(),
            quarantined_record_version_ids=(),
            canonical_batch_sha256="e" * 64,
        )
        return captured["batch"]

    monkeypatch.setattr(pop, "validate_record_batch", _valid_but_incomplete)
    record_path, manifest_path = _stores()
    result = populate_initial_polymarket_public_data(
        record_path,
        manifest_path,
        _config(allow_network=True, markets_limit=2),
        client=FakeClient([_market("100", ["a"]), _market("200", ["b"])]),
        utcnow_provider=_clock,
    )

    batch = captured["batch"]
    assert result.error_codes == ("POPULATION_BATCH_INVALID",)
    assert result.batch_is_valid is True
    assert result.batch_status == "VALID"
    assert result.batch_accepted_record_version_ids == batch.accepted_record_version_ids
    assert result.canonical_batch_sha256 == batch.canonical_batch_sha256
    assert result.inserted_record_count == 0


@pytest.mark.parametrize(
    ("markets", "books", "book_limit", "expected"),
    [
        ([_market("100", ["a"], active=False, closed=False)], {}, 0, (1, 0, 0)),
        (
            [_market("100", ["a"])],
            {
                "a": {
                    "asset_id": "a",
                    "bids": "invalid",
                    "asks": [],
                    "tick_size": "0.01",
                    "min_order_size": "1",
                }
            },
            1,
            (1, 1, 0),
        ),
        (
            [_market("100", ["a"]), _market("200", ["b"], outcomes=[])],
            {},
            0,
            (2, 0, 1),
        ),
    ],
)
def test_wp164a_rejection_preserves_completed_stage_counts(
    markets, books, book_limit, expected
):
    record_path, manifest_path = _stores()
    result = populate_initial_polymarket_public_data(
        record_path,
        manifest_path,
        _config(
            allow_network=True,
            markets_limit=len(markets),
            order_books_limit=book_limit,
        ),
        client=FakeClient(markets, books=books),
        guard=DenyGuard(deny_key=None),
        utcnow_provider=_clock,
    )
    assert result.is_valid is False
    assert (
        result.fetched_market_count,
        result.fetched_order_book_count,
        result.built_record_count,
    ) == expected
    assert result.inserted_record_count == 0


@pytest.mark.parametrize(
    ("active", "closed", "expected_status"),
    [
        (True, False, "open"),
        (False, True, "closed"),
        (True, True, "closed"),
        (False, False, None),
        ("true", False, None),
        (True, "false", None),
        (None, None, None),
    ],
)
def test_wp164a_market_status_normalization_is_closed(active, closed, expected_status):
    record_path, manifest_path = _stores()
    result = populate_initial_polymarket_public_data(
        record_path,
        manifest_path,
        _config(allow_network=True, markets_limit=1),
        client=FakeClient([_market("100", ["a"], active=active, closed=closed)]),
        utcnow_provider=_clock,
    )
    if expected_status is None:
        assert result.error_codes == ("POPULATION_RESPONSE_INVALID",)
        assert result.built_record_count == 0
    else:
        assert result.is_valid is True
        records = load_and_verify_point_in_time_record_store(
            record_path
        ).snapshot.records
        payload = json.loads(records[0].canonical_payload_json)
        assert payload["market_status"] == expected_status


def test_wp164a_twenty_five_market_one_book_offline_pipeline():
    markets = [
        _market(
            str(index),
            [f"token-{index}-yes", f"token-{index}-no"],
            condition=f"0xcondition{index:02d}",
        )
        for index in range(25)
    ]
    selected_token = "token-0-yes"
    record_path, manifest_path = _stores()
    result = populate_initial_polymarket_public_data(
        record_path,
        manifest_path,
        _config(allow_network=True, markets_limit=25, order_books_limit=1),
        client=FakeClient(markets, books={selected_token: _book(selected_token)}),
        now_provider=_advancing_now(),
        utcnow_provider=_clock,
    )

    assert (result.requested_markets_limit, result.bounded_markets_limit) == (25, 25)
    assert (result.requested_order_books_limit, result.bounded_order_books_limit) == (
        1,
        1,
    )
    assert (
        result.fetched_market_count,
        result.fetched_order_book_count,
        result.built_record_count,
        result.inserted_record_count,
    ) == (25, 1, 26, 26)
    assert result.status == "POPULATION_PERSISTED_AND_REGISTERED"
    assert result.batch_is_valid is True
    assert result.batch_status == "VALID_WITH_WARNINGS"
    assert result.batch_error_codes == ()
    assert result.batch_exact_duplicate_record_version_ids == ()
    assert result.batch_quarantined_record_version_ids == ()
    assert len(result.batch_accepted_record_version_ids) == 26
    assert len(set(result.batch_accepted_record_version_ids)) == 26
    assert result.dataset_snapshot_reference_id is not None
    assert result.manifest_entry_id is not None

    records = load_and_verify_point_in_time_record_store(record_path).snapshot.records
    metadata = [
        record for record in records if record.observation_kind == "MARKET_METADATA"
    ]
    assert len(metadata) == 25
    assert all(
        json.loads(record.canonical_payload_json)["market_status"] == "open"
        for record in metadata
    )
    typed_batch = validate_record_batch(records)
    assert result.batch_is_valid == typed_batch.is_valid
    assert result.batch_status == typed_batch.status
    assert result.batch_error_codes == typed_batch.error_codes
    assert result.batch_warning_codes == typed_batch.warning_codes
    assert (
        result.batch_accepted_record_version_ids
        == typed_batch.accepted_record_version_ids
    )
    assert (
        result.batch_exact_duplicate_record_version_ids
        == typed_batch.exact_duplicate_record_version_ids
    )
    assert (
        result.batch_quarantined_record_version_ids
        == typed_batch.quarantined_record_version_ids
    )
    assert result.canonical_batch_sha256 == typed_batch.canonical_batch_sha256
    assert result.build_failure_observation_kind is None
    assert result.build_status is None
    assert result.build_error_codes == ()
    assert result.build_warning_codes == ()
    assert result.build_quarantine_id is None
    assert result.build_input_fingerprint_sha256 is None


def test_wp164a_deep_book_retains_exact_order_book_build_diagnostics():
    markets = [
        _market(
            str(index),
            [f"token-{index}-yes", f"token-{index}-no"],
            condition=f"0xcondition{index:02d}",
        )
        for index in range(25)
    ]
    selected_token = "token-0-yes"
    deep_bids = tuple(("0.40", str(index + 1)) for index in range(257))
    record_path, manifest_path = _stores()
    result = populate_initial_polymarket_public_data(
        record_path,
        manifest_path,
        _config(allow_network=True, markets_limit=25, order_books_limit=1),
        client=FakeClient(
            markets,
            books={selected_token: _book(selected_token, bids=deep_bids)},
        ),
        now_provider=_advancing_now(),
        utcnow_provider=_clock,
    )

    assert result.error_codes == ("POPULATION_BUILD_FAILED",)
    assert (result.fetched_market_count, result.fetched_order_book_count) == (25, 1)
    assert (result.built_record_count, result.inserted_record_count) == (25, 0)
    assert result.build_failure_observation_kind == "ORDER_BOOK"
    assert result.build_status == "REJECTED_CONTRACT"
    assert result.build_error_codes == ("PAYLOAD_SEQUENCE_LIMIT_EXCEEDED",)
    assert result.build_warning_codes == ("EVENT_TIME_MISSING_ALLOWED",)
    assert result.build_quarantine_id is not None
    assert result.build_input_fingerprint_sha256 is not None
    assert result.snapshot_id is not None
    assert result.captured_at_utc == "2026-08-14T12:00:00Z"
    assert result.batch_is_valid is None
    assert result.batch_status is None
    assert result.batch_error_codes == ()
    assert result.batch_warning_codes == ()
    assert result.batch_accepted_record_version_ids == ()
    assert result.batch_exact_duplicate_record_version_ids == ()
    assert result.batch_quarantined_record_version_ids == ()
    assert result.canonical_batch_sha256 is None
    assert (
        load_and_verify_point_in_time_record_store(record_path).snapshot.records == ()
    )
    assert load_and_verify_manifest_store(manifest_path).snapshot.manifest_entries == ()


# ── WP164A frozen public-smoke operator (offline only) ──────────────────────


def test_wp164a_smoke_operator_cli_denies_without_exact_opt_in():
    calls = []
    missing_opt_in = [
        "--workspace",
        "local_data/wp164a_public_smoke/" + "5" * 40 + "/attempt-03",
        "--authorization-envelope",
        "local_data/wp164a_public_smoke/" + "5" * 40 + "/attempt-03.authorization.json",
        "--acknowledgement",
        smoke.ACKNOWLEDGEMENT,
    ]
    code, summary = smoke.run(
        missing_opt_in, coordinator=lambda *args: calls.append(args)
    )
    assert code == 2 and summary["terminal"] == smoke.STATE_DRIFT
    wrong_ack = missing_opt_in[:4] + [
        "--allow-public-network",
        "--acknowledgement",
        "WRONG",
    ]
    code, summary = smoke.run(wrong_ack, coordinator=lambda *args: calls.append(args))
    assert code == 2 and summary["terminal"] == smoke.STATE_DRIFT
    assert calls == []


def test_wp164a_smoke_operator_freezes_exact_cli_surface():
    parser = smoke._build_parser()
    assert {
        action.dest for action in parser._actions if action.dest != "help"
    } == {
        "workspace",
        "authorization_envelope",
        "allow_public_network",
        "acknowledgement",
    }


def test_wp164a_smoke_operator_accepts_exact_envelope_and_sibling_paths(
    monkeypatch, tmp_path
):
    envelope, workspace, envelope_path, _argv = _prepare_smoke_repo(
        monkeypatch, tmp_path
    )
    phase_sha, resolved_workspace, resolved_envelope = smoke._validate_envelope(
        envelope,
        workspace_arg=workspace,
        envelope_arg=envelope_path,
    )
    assert phase_sha == "5" * 40
    assert resolved_workspace == (tmp_path / workspace).resolve()
    assert resolved_envelope == (tmp_path / envelope_path).resolve()
    assert set(envelope) == smoke.ENVELOPE_KEYS
    assert len(envelope) == 28


@pytest.mark.parametrize(
    ("mutation", "value"),
    [
        ("missing", None),
        ("extra", None),
        ("markets_limit", True),
        ("retry_limit", False),
        ("operator_path", "tools/polymarket/alias.py"),
        ("manifest_id", "manifest:wrong"),
        ("public_network_authorized", False),
    ],
)
def test_wp164a_smoke_operator_rejects_envelope_drift(
    monkeypatch, tmp_path, mutation, value
):
    envelope, workspace, envelope_path, _argv = _prepare_smoke_repo(
        monkeypatch, tmp_path
    )
    if mutation == "missing":
        envelope.pop("wp_id")
    elif mutation == "extra":
        envelope["wp"] = "WP164A"
    else:
        envelope[mutation] = value
    with pytest.raises(smoke._StateDrift):
        smoke._validate_envelope(
            envelope,
            workspace_arg=workspace,
            envelope_arg=envelope_path,
        )


@pytest.mark.parametrize(
    ("workspace_change", "envelope_change"),
    [
        ("../escape", None),
        (None, "../authorization.json"),
        ("local_data/wp164a_public_smoke/wrong/attempt-03", None),
        (None, "local_data/wp164a_public_smoke/wrong.authorization.json"),
    ],
)
def test_wp164a_smoke_operator_rejects_path_drift(
    monkeypatch, tmp_path, workspace_change, envelope_change
):
    envelope, workspace, envelope_path, _argv = _prepare_smoke_repo(
        monkeypatch, tmp_path
    )
    with pytest.raises(smoke._StateDrift):
        smoke._validate_envelope(
            envelope,
            workspace_arg=workspace_change or workspace,
            envelope_arg=envelope_change or envelope_path,
        )


def test_wp164a_smoke_operator_wrong_frozen_digest_makes_zero_calls(
    monkeypatch, tmp_path
):
    envelope, _workspace, envelope_path, argv = _prepare_smoke_repo(
        monkeypatch, tmp_path
    )
    envelope["wp_prompt_sha256"] = "0" * 64
    (tmp_path / envelope_path).write_bytes(smoke._canonical_json_bytes(envelope))
    calls = []
    code, summary = smoke.run(argv, coordinator=lambda *args: calls.append(args))
    assert code == 2 and summary["terminal"] == smoke.STATE_DRIFT
    assert calls == []


def test_wp164a_smoke_operator_rejects_duplicate_envelope_key(tmp_path):
    path = tmp_path / "duplicate.json"
    path.write_text('{"schema_id":"a","schema_id":"b"}', encoding="utf-8")
    with pytest.raises(smoke._StateDrift):
        smoke._bounded_json_object(path)


def test_wp164a_smoke_operator_preexisting_workspace_makes_zero_calls(
    monkeypatch, tmp_path
):
    _envelope, workspace, _envelope_path, argv = _prepare_smoke_repo(
        monkeypatch, tmp_path
    )
    (tmp_path / workspace).mkdir()
    (tmp_path / workspace / smoke.SENTINEL_NAME).write_text(
        "already consumed", encoding="utf-8"
    )
    calls = []
    code, summary = smoke.run(argv, coordinator=lambda *args: calls.append(args))
    assert code == 2 and summary["terminal"] == smoke.STATE_DRIFT
    assert calls == []
    assert (tmp_path / workspace / smoke.SENTINEL_NAME).read_text(
        encoding="utf-8"
    ) == "already consumed"


def test_wp164a_smoke_operator_store_initialization_failure_makes_zero_calls(
    monkeypatch, tmp_path
):
    _envelope, workspace, _envelope_path, argv = _prepare_smoke_repo(
        monkeypatch, tmp_path
    )
    monkeypatch.setattr(
        smoke,
        "initialize_point_in_time_record_store",
        lambda path: SimpleNamespace(is_valid=False, snapshot=None),
    )
    calls = []
    code, summary = smoke.run(argv, coordinator=lambda *args: calls.append(args))
    assert code == 2 and summary["terminal"] == smoke.STATE_DRIFT
    assert calls == []
    assert not (tmp_path / workspace / smoke.SENTINEL_NAME).exists()


def test_wp164a_smoke_operator_one_call_exact_config_and_canonical_result(
    monkeypatch, tmp_path
):
    envelope, workspace, _envelope_path, argv = _prepare_smoke_repo(
        monkeypatch, tmp_path
    )
    captured = []
    writes = []
    real_write = smoke._exclusive_json_write

    def _count_write(path, mapping):
        writes.append(path.name)
        return real_write(path, mapping)

    monkeypatch.setattr(smoke, "_exclusive_json_write", _count_write)

    def _coordinator(record_path, manifest_path, config):
        captured.append((record_path, manifest_path, config))
        assert (record_path.parent / smoke.SENTINEL_NAME).is_file()
        assert load_and_verify_point_in_time_record_store(
            record_path
        ).snapshot.records == ()
        manifest = load_and_verify_manifest_store(manifest_path).snapshot
        assert manifest.dataset_references == () and manifest.manifest_entries == ()
        return pop._result(
            is_valid=False,
            status="POPULATION_REJECTED",
            error_codes=("POPULATION_BUILD_FAILED",),
            snapshot_id="snapshot:sha256:" + "a" * 64,
            captured_at_utc="2026-09-24T12:00:00Z",
            requested_markets_limit=25,
            bounded_markets_limit=25,
            requested_order_books_limit=1,
            bounded_order_books_limit=1,
            fetched_market_count=25,
            fetched_order_book_count=1,
            built_record_count=25,
            network_used=True,
            build_failure_observation_kind="ORDER_BOOK",
            build_status="REJECTED_CONTRACT",
            build_error_codes=("PAYLOAD_SEQUENCE_LIMIT_EXCEEDED",),
            build_warning_codes=("EVENT_TIME_MISSING_ALLOWED",),
            build_quarantine_id="quarantine:sha256:" + "b" * 64,
            build_input_fingerprint_sha256="c" * 64,
        )

    code, summary = smoke.run(argv, coordinator=_coordinator)
    assert code == 2 and summary["terminal"] == smoke.BUILD_FAILED
    assert len(captured) == 1
    record_path, manifest_path, config = captured[0]
    assert record_path.name == smoke.RECORD_STORE_NAME
    assert manifest_path.name == smoke.MANIFEST_STORE_NAME
    assert config == Cfg(
        manifest_id=smoke.MANIFEST_ID,
        parameter_set_id=smoke.PARAMETER_SET_ID,
        normalizer_version=smoke.NORMALIZER_VERSION,
        validator_version=smoke.VALIDATOR_VERSION,
        markets_limit=25,
        order_books_limit=1,
        allow_network=True,
    )
    sentinel_path = tmp_path / workspace / smoke.SENTINEL_NAME
    result_path = tmp_path / workspace / smoke.RESULT_NAME
    assert sentinel_path.is_file() and result_path.is_file()
    sentinel = json.loads(sentinel_path.read_text(encoding="utf-8"))
    artifact = json.loads(result_path.read_text(encoding="utf-8"))
    assert sentinel["invocation_state"] == "STARTED"
    assert sentinel["authorization_envelope_sha256"] == smoke._sha256_bytes(
        smoke._canonical_json_bytes(envelope)
    )
    assert artifact["error_codes"] == ["POPULATION_BUILD_FAILED"]
    assert artifact["build_error_codes"] == ["PAYLOAD_SEQUENCE_LIMIT_EXCEEDED"]
    assert summary["result_sha256"] == smoke._file_sha256(result_path)
    assert summary["coordinator_invocations"] == 1
    assert writes == [smoke.SENTINEL_NAME, smoke.RESULT_NAME]


def _real_smoke_coordinator(client):
    def _coordinator(record_path, manifest_path, config):
        return populate_initial_polymarket_public_data(
            record_path,
            manifest_path,
            config,
            client=client,
            now_provider=_advancing_now(),
            utcnow_provider=_clock,
        )

    return _coordinator


@pytest.mark.parametrize(
    ("markets", "books", "expected_counts"),
    [
        (
            [
                _market(
                    str(index),
                    [f"token-{index}-yes", f"token-{index}-no"],
                    condition=f"0xcondition{index:02d}",
                )
                for index in range(25)
            ],
            {"token-0-yes": _book("token-0-yes")},
            (25, 1, 26, 26),
        ),
        (
            [_market("100", ["tokA"])],
            {
                "tokA": _book(
                    "tokA",
                    bids=tuple(
                        (f"0.{index:03d}", str(index)) for index in range(1, 129)
                    ),
                    asks=tuple(
                        (f"0.{index + 200:03d}", str(index))
                        for index in range(1, 129)
                    ),
                )
            },
            (1, 1, 2, 2),
        ),
        (
            [_market("100", ["tokA"]), _market("200", ["tokB"])],
            {"tokA": _book("tokA")},
            (2, 1, 3, 3),
        ),
        (
            [_market("100", [])],
            {},
            (1, 0, 1, 1),
        ),
    ],
    ids=("exact-25-1", "large-book", "fewer-with-book", "zero-book"),
)
def test_wp164a_smoke_operator_real_chain_success_variants(
    monkeypatch, tmp_path, markets, books, expected_counts
):
    _envelope, workspace, _envelope_path, argv = _prepare_smoke_repo(
        monkeypatch, tmp_path
    )
    client = FakeClient(markets, books=books)

    code, summary = smoke.run(argv, coordinator=_real_smoke_coordinator(client))

    assert code == 0
    assert summary["terminal"] == smoke.COMPLETE_SUCCESS
    assert summary["coordinator_invocations"] == 1
    assert summary["retry_count"] == 0
    actual_counts = (
        summary["fetched_market_count"],
        summary["fetched_order_book_count"],
        summary["built_record_count"],
        summary["inserted_record_count"],
    )
    assert actual_counts == expected_counts
    assert client.markets_calls == 1
    assert len(client.book_calls) == expected_counts[1]
    artifact = json.loads(
        (tmp_path / workspace / smoke.RESULT_NAME).read_text(encoding="utf-8")
    )
    assert artifact["batch_is_valid"] is True
    assert len(artifact["batch_accepted_record_version_ids"]) == expected_counts[2]
    assert artifact["batch_exact_duplicate_record_version_ids"] == []
    assert artifact["batch_quarantined_record_version_ids"] == []
    records = load_and_verify_point_in_time_record_store(
        tmp_path / workspace / smoke.RECORD_STORE_NAME
    ).snapshot.records
    if expected_counts == (1, 1, 2, 2):
        book = next(
            record for record in records if record.observation_kind == "ORDER_BOOK"
        )
        assert len(book.canonical_payload_json) > 4096


@pytest.mark.parametrize(
    ("client", "expected_terminal", "expected_counts"),
    [
        (
            FakeClient(
                [
                    _market(
                        str(index),
                        [f"token-{index}-yes", f"token-{index}-no"],
                        condition=f"0xcondition{index:02d}",
                    )
                    for index in range(25)
                ],
                books={
                    "token-0-yes": _book(
                        "token-0-yes",
                        bids=tuple(("0.40", str(index + 1)) for index in range(257)),
                    )
                },
            ),
            smoke.BUILD_FAILED,
            (25, 1, 25, 0),
        ),
        (FakeClient([], markets_status=503), smoke.EXTERNAL_INVALID, (0, 0, 0, 0)),
    ],
    ids=("typed-build-failure", "external-response-failure"),
)
def test_wp164a_smoke_operator_real_chain_closed_failures(
    monkeypatch, tmp_path, client, expected_terminal, expected_counts
):
    _envelope, workspace, _envelope_path, argv = _prepare_smoke_repo(
        monkeypatch, tmp_path
    )

    code, summary = smoke.run(argv, coordinator=_real_smoke_coordinator(client))

    assert code == 2
    assert summary["terminal"] == expected_terminal
    assert summary["coordinator_invocations"] == 1
    assert summary["retry_count"] == 0
    assert (
        summary["fetched_market_count"],
        summary["fetched_order_book_count"],
        summary["built_record_count"],
        summary["inserted_record_count"],
    ) == expected_counts
    assert (tmp_path / workspace / smoke.SENTINEL_NAME).is_file()
    assert (tmp_path / workspace / smoke.RESULT_NAME).is_file()


def test_wp164a_smoke_operator_post_sentinel_exception_is_nonretryable(
    monkeypatch, tmp_path
):
    _envelope, workspace, _envelope_path, argv = _prepare_smoke_repo(
        monkeypatch, tmp_path
    )
    calls = []

    def _raise_after_sentinel(*args):
        calls.append(args)
        raise RuntimeError("must not escape or retry")

    code, summary = smoke.run(argv, coordinator=_raise_after_sentinel)
    assert code == 2 and summary["terminal"] == smoke.LOCAL_EVIDENCE_DEFECT
    assert len(calls) == 1
    assert (tmp_path / workspace / smoke.SENTINEL_NAME).is_file()
    assert not (tmp_path / workspace / smoke.RESULT_NAME).exists()
    code, summary = smoke.run(argv, coordinator=_raise_after_sentinel)
    assert code == 2 and summary["terminal"] == smoke.STATE_DRIFT
    assert len(calls) == 1


def _empty_verified_stores():
    return (
        SimpleNamespace(is_valid=True, snapshot=SimpleNamespace(records=())),
        SimpleNamespace(
            is_valid=True,
            snapshot=SimpleNamespace(dataset_references=(), manifest_entries=()),
        ),
    )


@pytest.mark.parametrize(
    ("errors", "network_used", "expected"),
    [
        (("POPULATION_BUILD_FAILED",), True, smoke.BUILD_FAILED),
        (("POPULATION_BATCH_INVALID",), True, smoke.BATCH_INVALID),
        (("POPULATION_FETCH_FAILED",), True, smoke.EXTERNAL_INVALID),
        (("POPULATION_RESPONSE_INVALID",), True, smoke.EXTERNAL_INVALID),
        (("POPULATION_FETCH_FAILED",), False, smoke.LOCAL_EVIDENCE_DEFECT),
        (
            ("POPULATION_BUILD_FAILED", "POPULATION_BATCH_INVALID"),
            True,
            smoke.LOCAL_EVIDENCE_DEFECT,
        ),
        (("POPULATION_UNEXPECTED_ERROR",), True, smoke.LOCAL_EVIDENCE_DEFECT),
    ],
)
def test_wp164a_smoke_operator_closed_failure_terminal_mapping(
    errors, network_used, expected
):
    record_store, manifest_store = _empty_verified_stores()
    result = pop._result(
        is_valid=False,
        status="POPULATION_REJECTED",
        error_codes=errors,
        network_used=network_used,
    )
    assert smoke._classify(result, record_store, manifest_store) == expected


def test_wp164a_smoke_operator_success_allows_actual_counts_below_limits():
    accepted_id = "a" * 64
    batch = PointInTimeBatchValidationResult(
        is_valid=True,
        status="VALID_WITH_WARNINGS",
        error_codes=(),
        warning_codes=("EVENT_TIME_MISSING_ALLOWED",),
        accepted_record_version_ids=(accepted_id,),
        exact_duplicate_record_version_ids=(),
        quarantined_record_version_ids=(),
        canonical_batch_sha256="b" * 64,
    )
    result = pop._result(
        is_valid=True,
        status="POPULATION_PERSISTED_AND_REGISTERED",
        requested_markets_limit=25,
        bounded_markets_limit=25,
        requested_order_books_limit=1,
        bounded_order_books_limit=1,
        fetched_market_count=1,
        fetched_order_book_count=0,
        built_record_count=1,
        inserted_record_count=1,
        dataset_snapshot_reference_id="reference:1",
        manifest_entry_id="entry:1",
        record_store_status="RECORD_STORE_APPEND_COMMITTED",
        registration_status="ADAPTER_PERSISTED",
        network_used=True,
        batch=batch,
    )
    record_store = SimpleNamespace(
        is_valid=True,
        snapshot=SimpleNamespace(
            records=(
                SimpleNamespace(
                    envelope=SimpleNamespace(record_version_id=accepted_id)
                ),
            )
        ),
    )
    manifest_store = SimpleNamespace(
        is_valid=True,
        snapshot=SimpleNamespace(
            dataset_references=(
                SimpleNamespace(dataset_snapshot_reference_id="reference:1"),
            ),
            manifest_entries=(SimpleNamespace(manifest_entry_id="entry:1"),),
        ),
    )
    assert smoke._classify(result, record_store, manifest_store) == smoke.COMPLETE_SUCCESS


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
        record_path,
        manifest_path,
        _config(allow_network=True, markets_limit=1),
        client=client,
        utcnow_provider=_clock,
    )
    assert result.error_codes == ("POPULATION_RECORD_APPEND_FAILED",)
    assert result.record_store_error_codes == ("RECORD_STORE_WRITE_FAILED",)
    assert register_calls == []
    assert load_and_verify_manifest_store(manifest_path).snapshot.manifest_entries == ()


def test_registration_failure_keeps_records_and_requires_recovery(monkeypatch):
    record_path, manifest_path = _stores()

    # A genuine invalid adapter result carrying a known closed WP162 code.
    monkeypatch.setattr(
        pop,
        "persist_validated_record_batch_snapshot",
        lambda *a, **k: _adapter_rejected(("ADAPTER_STORE_APPEND_FAILED",)),
    )
    client = FakeClient([_market("100", ["a"])])
    result = populate_initial_polymarket_public_data(
        record_path,
        manifest_path,
        _config(allow_network=True, markets_limit=1),
        client=client,
        utcnow_provider=_clock,
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
    assert (
        len(load_and_verify_point_in_time_record_store(record_path).snapshot.records)
        == 1
    )


# ── Recovery ──────────────────────────────────────────────────────────────────


def _seed_unregistered(monkeypatch_ctx, record_path, manifest_path, cfg):
    """Populate records but force registration to fail, leaving an unregistered seed."""

    original = pop.persist_validated_record_batch_snapshot
    pop.persist_validated_record_batch_snapshot = lambda *a, **k: _adapter_rejected(
        ("ADAPTER_STORE_APPEND_FAILED",)
    )
    try:
        client = FakeClient([_market("100", ["tokA"])], books={"tokA": _book("tokA")})
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
    assert (
        len(load_and_verify_manifest_store(manifest_path).snapshot.manifest_entries)
        == 1
    )


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
        record_path,
        manifest_path,
        _config(allow_network=True, markets_limit=1),
        client=client,
        utcnow_provider=_clock,
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
        record_path,
        manifest_path,
        _config(allow_network=True, markets_limit=1),
        client=client,
        utcnow_provider=_clock,
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
    return {node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)}


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


# ── Blocker A: the local guard is the runtime authority ───────────────────────


def test_production_default_has_no_fabricated_guard_clock():
    source = _module_source()
    assert "_default_now_provider" not in source
    assert "3600" not in source


def test_real_guard_constant_time_denies_second_book():
    # Real RateLimitGuard (default) + a constant injected time: the conservative
    # minimum interval must deny the second back-to-back CLOB book.
    record_path, manifest_path = _stores()
    client = FakeClient(
        [_market("100", ["tokA", "tokB"])],
        books={"tokA": _book("tokA"), "tokB": _book("tokB")},
    )
    result = populate_initial_polymarket_public_data(
        record_path,
        manifest_path,
        _config(allow_network=True, markets_limit=1, order_books_limit=2),
        client=client,
        now_provider=lambda: 1000.0,
        utcnow_provider=_clock,
    )
    assert result.error_codes == ("POPULATION_GUARD_DENIED",)
    assert result.network_used is True
    # First book fetched; second denied before its client call; nothing persisted.
    assert client.book_calls == ["tokA"]
    assert (
        load_and_verify_point_in_time_record_store(record_path).snapshot.records == ()
    )
    assert load_and_verify_manifest_store(manifest_path).snapshot.manifest_entries == ()


def test_injected_advancing_time_allows_multiple_books():
    record_path, manifest_path = _stores()
    client = FakeClient(
        [_market("100", ["tokA", "tokB"])],
        books={"tokA": _book("tokA"), "tokB": _book("tokB")},
    )
    result = populate_initial_polymarket_public_data(
        record_path,
        manifest_path,
        _config(allow_network=True, markets_limit=1, order_books_limit=2),
        client=client,
        now_provider=_advancing_now(),
        utcnow_provider=_clock,
    )
    assert result.status == "POPULATION_PERSISTED_AND_REGISTERED"
    assert result.fetched_order_book_count == 2
    assert client.book_calls == ["tokA", "tokB"]


# ── Observability: network_used is truthful ───────────────────────────────────


def test_gamma_guard_denial_reports_network_used_false():
    record_path, manifest_path = _stores()
    client = FakeClient([_market("100", ["a"])])
    guard = DenyGuard(deny_key="gamma_markets")
    result = populate_initial_polymarket_public_data(
        record_path,
        manifest_path,
        _config(allow_network=True, markets_limit=1),
        client=client,
        guard=guard,
        utcnow_provider=_clock,
    )
    assert result.error_codes == ("POPULATION_GUARD_DENIED",)
    assert result.network_used is False
    assert client.markets_calls == 0


def test_book_guard_denial_after_gamma_reports_network_used_true():
    record_path, manifest_path = _stores()
    client = FakeClient([_market("100", ["tokA"])], books={"tokA": _book("tokA")})
    guard = DenyGuard(deny_key="clob_book")
    result = populate_initial_polymarket_public_data(
        record_path,
        manifest_path,
        _config(allow_network=True, markets_limit=1, order_books_limit=1),
        client=client,
        guard=guard,
        utcnow_provider=_clock,
    )
    assert result.error_codes == ("POPULATION_GUARD_DENIED",)
    assert result.network_used is True
    assert client.markets_calls == 1


# ── Blocker B: registration exception after committed append is recoverable ───


def test_registration_exception_after_commit_preserves_recovery(monkeypatch):
    record_path, manifest_path = _stores()
    marker = "SECRET_REG_MARKER_beef"
    url = "https://reg.invalid/leak?token=xyz"
    monkeypatch.setattr(
        pop,
        "persist_validated_record_batch_snapshot",
        _raise(RuntimeError(f"{marker} {url}")),
    )
    client = FakeClient([_market("100", ["a"])])
    result = populate_initial_polymarket_public_data(
        record_path,
        manifest_path,
        _config(allow_network=True, markets_limit=1),
        client=client,
        utcnow_provider=_clock,
    )
    assert result.status == "POPULATION_RECORDS_PERSISTED_REGISTRATION_FAILED"
    assert result.is_valid is False
    assert result.recovery_required is True
    assert result.network_used is True
    assert result.record_store_status == "RECORD_STORE_APPEND_COMMITTED"
    assert result.registration_error_codes == ()  # a raised exception echoes nothing
    assert result.dataset_snapshot_reference_id is None
    assert result.manifest_entry_id is None
    text = repr(result)
    assert marker not in text and url not in text
    # Records remain committed; manifest untouched.
    assert (
        len(load_and_verify_point_in_time_record_store(record_path).snapshot.records)
        == 1
    )
    assert load_and_verify_manifest_store(manifest_path).snapshot.manifest_entries == ()


def test_offline_recovery_after_raised_registration_exception(monkeypatch):
    record_path, manifest_path = _stores()
    cfg = _config(allow_network=True, markets_limit=1, order_books_limit=1)
    monkeypatch.setattr(
        pop,
        "persist_validated_record_batch_snapshot",
        _raise(RuntimeError("boom during population registration")),
    )
    client = FakeClient([_market("100", ["tokA"])], books={"tokA": _book("tokA")})
    first = populate_initial_polymarket_public_data(
        record_path, manifest_path, cfg, client=client, utcnow_provider=_clock
    )
    assert first.status == "POPULATION_RECORDS_PERSISTED_REGISTRATION_FAILED"
    monkeypatch.undo()
    recovered = recover_initial_polymarket_public_registration(
        record_path, manifest_path, cfg
    )
    assert recovered.status == "POPULATION_RECOVERED_REGISTRATION"
    assert recovered.network_used is False
    assert (
        len(load_and_verify_manifest_store(manifest_path).snapshot.manifest_entries)
        == 1
    )


def test_recovery_side_registration_exception_fails_closed(monkeypatch):
    record_path, manifest_path = _stores()
    cfg = _config(allow_network=True, markets_limit=1, order_books_limit=1)
    _seed_unregistered(None, record_path, manifest_path, cfg)
    before = len(
        load_and_verify_point_in_time_record_store(record_path).snapshot.records
    )
    marker = "SECRET_RECOVER_MARKER_cafe"
    url = "https://recover.invalid/leak"
    monkeypatch.setattr(
        pop,
        "persist_validated_record_batch_snapshot",
        _raise(RuntimeError(f"{marker} {url}")),
    )
    result = recover_initial_polymarket_public_registration(
        record_path, manifest_path, cfg
    )
    assert result.is_valid is False
    assert result.error_codes == ("POPULATION_REGISTRATION_FAILED",)
    text = repr(result)
    assert marker not in text and url not in text
    # Recovery never mutates records.
    assert (
        len(load_and_verify_point_in_time_record_store(record_path).snapshot.records)
        == before
    )


# ── Blocker C: recovery re-proves genuine WP164 construction ──────────────────


def test_recovery_rejects_forged_seed_with_arbitrary_identity_ids():
    record_path, manifest_path = _stores()
    cfg = _config()
    # A WP156-valid record reusing WP164 source IDs but with arbitrary, self-
    # consistent snapshot/batch IDs (source ids derived from the arbitrary snapshot).
    forged = _make_gamma_record(
        cfg,
        snapshot_id=_ARB_SNAPSHOT,
        ingestion_batch_id=_ARB_INGEST,
        captured=_ARB_TIME,
    )
    from src.data_layer.point_in_time_market_research import (
        append_point_in_time_records,
    )

    append_point_in_time_records(record_path, (forged,))
    result = recover_initial_polymarket_public_registration(
        record_path, manifest_path, cfg
    )
    assert result.error_codes == ("POPULATION_RECOVERY_INVALID",)
    assert load_and_verify_manifest_store(manifest_path).snapshot.manifest_entries == ()


def test_recovery_rejects_book_only_store():
    record_path, manifest_path = _stores()
    cfg = _config()
    book = _make_book_record(
        cfg,
        snapshot_id=_ARB_SNAPSHOT,
        ingestion_batch_id=_ARB_INGEST,
        captured=_ARB_TIME,
        raw_token="tokA",
    )
    from src.data_layer.point_in_time_market_research import (
        append_point_in_time_records,
    )

    append_point_in_time_records(record_path, (book,))
    result = recover_initial_polymarket_public_registration(
        record_path, manifest_path, cfg
    )
    assert result.error_codes == ("POPULATION_RECOVERY_INVALID",)


def test_recovery_rejects_orphan_clob_token():
    record_path, manifest_path = _stores()
    cfg = _config()
    gamma = _make_gamma_record(
        cfg,
        snapshot_id=_ARB_SNAPSHOT,
        ingestion_batch_id=_ARB_INGEST,
        captured=_ARB_TIME,
        payload=_gamma_payload(tokens=("tokA",)),
    )
    orphan = _make_book_record(
        cfg,
        snapshot_id=_ARB_SNAPSHOT,
        ingestion_batch_id=_ARB_INGEST,
        captured=_ARB_TIME,
        raw_token="tokORPHAN",
    )
    from src.data_layer.point_in_time_market_research import (
        append_point_in_time_records,
    )

    append_point_in_time_records(record_path, (gamma, orphan))
    result = recover_initial_polymarket_public_registration(
        record_path, manifest_path, cfg
    )
    assert result.error_codes == ("POPULATION_RECOVERY_INVALID",)


def test_recovery_rejects_misparented_clob():
    record_path, manifest_path = _stores()
    cfg = _config()
    g1 = _make_gamma_record(
        cfg,
        snapshot_id=_ARB_SNAPSHOT,
        ingestion_batch_id=_ARB_INGEST,
        captured=_ARB_TIME,
        market_id="market:polymarket:100",
        event_id="event:polymarket:0xcond100",
        payload=_gamma_payload(condition="0xcond100", tokens=("tokA",)),
    )
    g2 = _make_gamma_record(
        cfg,
        snapshot_id=_ARB_SNAPSHOT,
        ingestion_batch_id=_ARB_INGEST,
        captured=_ARB_TIME,
        market_id="market:polymarket:200",
        event_id="event:polymarket:0xcond200",
        payload=_gamma_payload(condition="0xcond200", tokens=("tokC",)),
    )
    # A book for tokA (owned by market 100) parented to market 200.
    misparented = _make_book_record(
        cfg,
        snapshot_id=_ARB_SNAPSHOT,
        ingestion_batch_id=_ARB_INGEST,
        captured=_ARB_TIME,
        raw_token="tokA",
        market_id="market:polymarket:200",
        event_id="event:polymarket:0xcond200",
    )
    from src.data_layer.point_in_time_market_research import (
        append_point_in_time_records,
    )

    append_point_in_time_records(record_path, (g1, g2, misparented))
    result = recover_initial_polymarket_public_registration(
        record_path, manifest_path, cfg
    )
    assert result.error_codes == ("POPULATION_RECOVERY_INVALID",)


def test_recovery_rejects_wrong_source_snapshot_id():
    record_path, manifest_path = _stores()
    cfg = _config()
    forged = _make_gamma_record(
        cfg,
        snapshot_id=_ARB_SNAPSHOT,
        ingestion_batch_id=_ARB_INGEST,
        captured=_ARB_TIME,
        source_snapshot_id="srcsnap:sha256:" + "c" * 64,  # not the WP164 derivation
    )
    from src.data_layer.point_in_time_market_research import (
        append_point_in_time_records,
    )

    append_point_in_time_records(record_path, (forged,))
    result = recover_initial_polymarket_public_registration(
        record_path, manifest_path, cfg
    )
    assert result.error_codes == ("POPULATION_RECOVERY_INVALID",)


# ── Malformed / hostile adapter registration results are contained ────────────


def test_registration_none_result_after_commit_is_recoverable(monkeypatch):
    record_path, manifest_path = _stores()
    monkeypatch.setattr(
        pop, "persist_validated_record_batch_snapshot", lambda *a, **k: None
    )
    client = FakeClient([_market("100", ["a"])])
    result = populate_initial_polymarket_public_data(
        record_path,
        manifest_path,
        _config(allow_network=True, markets_limit=1),
        client=client,
        utcnow_provider=_clock,
    )
    assert result.status == "POPULATION_RECORDS_PERSISTED_REGISTRATION_FAILED"
    assert result.recovery_required is True
    assert result.record_store_status == "RECORD_STORE_APPEND_COMMITTED"
    assert result.dataset_snapshot_reference_id is None
    assert result.manifest_entry_id is None
    assert "POPULATION_UNEXPECTED_ERROR" not in result.error_codes
    assert (
        len(load_and_verify_point_in_time_record_store(record_path).snapshot.records)
        == 1
    )
    assert load_and_verify_manifest_store(manifest_path).snapshot.manifest_entries == ()


def test_registration_result_with_raising_property_is_recoverable(monkeypatch):
    record_path, manifest_path = _stores()
    marker = "SECRET_RAISE_MARKER_1a2b"
    url = "https://raise.invalid/leak"

    class _Raising:
        @property
        def is_valid(self):
            raise RuntimeError(f"{marker} {url}")

    monkeypatch.setattr(
        pop, "persist_validated_record_batch_snapshot", lambda *a, **k: _Raising()
    )
    client = FakeClient([_market("100", ["a"])])
    result = populate_initial_polymarket_public_data(
        record_path,
        manifest_path,
        _config(allow_network=True, markets_limit=1),
        client=client,
        utcnow_provider=_clock,
    )
    assert result.status == "POPULATION_RECORDS_PERSISTED_REGISTRATION_FAILED"
    assert result.recovery_required is True
    assert "POPULATION_UNEXPECTED_ERROR" not in result.error_codes
    text = repr(result)
    assert marker not in text and url not in text
    assert (
        len(load_and_verify_point_in_time_record_store(record_path).snapshot.records)
        == 1
    )


def test_registration_fake_success_missing_fields_is_registration_failure(monkeypatch):
    record_path, manifest_path = _stores()

    class _FakeSuccess:
        is_valid = True
        status = "ADAPTER_PERSISTED"
        dataset_reference = None
        manifest_entry = None
        error_codes = ()

    monkeypatch.setattr(
        pop, "persist_validated_record_batch_snapshot", lambda *a, **k: _FakeSuccess()
    )
    client = FakeClient([_market("100", ["a"])])
    result = populate_initial_polymarket_public_data(
        record_path,
        manifest_path,
        _config(allow_network=True, markets_limit=1),
        client=client,
        utcnow_provider=_clock,
    )
    # Not a success and not a generic exception.
    assert result.is_valid is False
    assert result.status == "POPULATION_RECORDS_PERSISTED_REGISTRATION_FAILED"
    assert result.recovery_required is True
    assert result.dataset_snapshot_reference_id is None
    assert result.manifest_entry_id is None
    assert "POPULATION_UNEXPECTED_ERROR" not in result.error_codes
    assert (
        len(load_and_verify_point_in_time_record_store(record_path).snapshot.records)
        == 1
    )


def test_recovery_side_malformed_registration_result_fails_closed(monkeypatch):
    record_path, manifest_path = _stores()
    cfg = _config(allow_network=True, markets_limit=1, order_books_limit=1)
    _seed_unregistered(None, record_path, manifest_path, cfg)
    before = len(
        load_and_verify_point_in_time_record_store(record_path).snapshot.records
    )
    monkeypatch.setattr(
        pop, "persist_validated_record_batch_snapshot", lambda *a, **k: None
    )
    result = recover_initial_polymarket_public_registration(
        record_path, manifest_path, cfg
    )
    assert result.is_valid is False
    assert result.error_codes == ("POPULATION_REGISTRATION_FAILED",)
    assert result.network_used is False
    assert (
        len(load_and_verify_point_in_time_record_store(record_path).snapshot.records)
        == before
    )


# ── Same-market duplicate token IDs vs cross-market ambiguity ─────────────────


def test_recovery_accepts_same_market_duplicate_token_ids(monkeypatch):
    record_path, manifest_path = _stores()
    cfg = _config(allow_network=True, markets_limit=1, order_books_limit=1)
    # One market whose token list repeats the same raw token; WP164 dedupes it to
    # a single book, so this is a genuine seed the network path can create.
    client = FakeClient(
        [_market("100", ["tokA", "tokA"])], books={"tokA": _book("tokA")}
    )

    monkeypatch.setattr(
        pop,
        "persist_validated_record_batch_snapshot",
        lambda *a, **k: _adapter_rejected(("ADAPTER_STORE_APPEND_FAILED",)),
    )
    seed = populate_initial_polymarket_public_data(
        record_path, manifest_path, cfg, client=client, utcnow_provider=_clock
    )
    assert seed.status == "POPULATION_RECORDS_PERSISTED_REGISTRATION_FAILED"
    monkeypatch.undo()
    recovered = recover_initial_polymarket_public_registration(
        record_path, manifest_path, cfg
    )
    assert recovered.status == "POPULATION_RECOVERED_REGISTRATION"
    assert recovered.network_used is False


def test_recovery_rejects_cross_market_ambiguous_token():
    record_path, manifest_path = _stores()
    cfg = _config()
    g1 = _make_gamma_record(
        cfg,
        snapshot_id=_ARB_SNAPSHOT,
        ingestion_batch_id=_ARB_INGEST,
        captured=_ARB_TIME,
        market_id="market:polymarket:100",
        event_id="event:polymarket:0xcond100",
        payload=_gamma_payload(condition="0xcond100", tokens=("tokA",)),
    )
    g2 = _make_gamma_record(
        cfg,
        snapshot_id=_ARB_SNAPSHOT,
        ingestion_batch_id=_ARB_INGEST,
        captured=_ARB_TIME,
        market_id="market:polymarket:200",
        event_id="event:polymarket:0xcond200",
        payload=_gamma_payload(condition="0xcond200", tokens=("tokA",)),
    )
    book = _make_book_record(
        cfg,
        snapshot_id=_ARB_SNAPSHOT,
        ingestion_batch_id=_ARB_INGEST,
        captured=_ARB_TIME,
        raw_token="tokA",
        market_id="market:polymarket:100",
        event_id="event:polymarket:0xcond100",
    )
    from src.data_layer.point_in_time_market_research import (
        append_point_in_time_records,
    )

    append_point_in_time_records(record_path, (g1, g2, book))
    result = recover_initial_polymarket_public_registration(
        record_path, manifest_path, cfg
    )
    assert result.error_codes == ("POPULATION_RECOVERY_INVALID",)


# ── registration_error_codes is closed and no-echo safe ───────────────────────


def test_registration_arbitrary_error_code_string_is_not_echoed(monkeypatch):
    record_path, manifest_path = _stores()
    marker = "SECRET_MARKER_face https://secret.invalid/leak"
    monkeypatch.setattr(
        pop,
        "persist_validated_record_batch_snapshot",
        lambda *a, **k: _adapter_rejected((marker,)),
    )
    client = FakeClient([_market("100", ["a"])])
    result = populate_initial_polymarket_public_data(
        record_path,
        manifest_path,
        _config(allow_network=True, markets_limit=1),
        client=client,
        utcnow_provider=_clock,
    )
    assert result.status == "POPULATION_RECORDS_PERSISTED_REGISTRATION_FAILED"
    assert result.recovery_required is True
    # Arbitrary (non-closed) codes are dropped; nothing echoed.
    assert result.registration_error_codes == ()
    text = repr(result)
    assert "SECRET_MARKER_face" not in text and "secret.invalid" not in text
    assert (
        len(load_and_verify_point_in_time_record_store(record_path).snapshot.records)
        == 1
    )
    assert load_and_verify_manifest_store(manifest_path).snapshot.manifest_entries == ()


def test_registration_known_closed_code_is_preserved(monkeypatch):
    record_path, manifest_path = _stores()
    # A mix of a known closed code and an arbitrary string: keep only the closed one.
    monkeypatch.setattr(
        pop,
        "persist_validated_record_batch_snapshot",
        lambda *a, **k: _adapter_rejected(
            ("ADAPTER_STORE_APPEND_FAILED", "SECRET leak")
        ),
    )
    client = FakeClient([_market("100", ["a"])])
    result = populate_initial_polymarket_public_data(
        record_path,
        manifest_path,
        _config(allow_network=True, markets_limit=1),
        client=client,
        utcnow_provider=_clock,
    )
    assert result.status == "POPULATION_RECORDS_PERSISTED_REGISTRATION_FAILED"
    assert result.registration_error_codes == ("ADAPTER_STORE_APPEND_FAILED",)
    assert "SECRET" not in repr(result)


def test_registration_error_codes_raising_iterable_fails_closed(monkeypatch):
    record_path, manifest_path = _stores()

    class _RaisingIterable:
        def __iter__(self):
            raise RuntimeError("SECRET_ITER https://iter.invalid")

    monkeypatch.setattr(
        pop,
        "persist_validated_record_batch_snapshot",
        lambda *a, **k: _adapter_rejected(_RaisingIterable()),
    )
    client = FakeClient([_market("100", ["a"])])
    result = populate_initial_polymarket_public_data(
        record_path,
        manifest_path,
        _config(allow_network=True, markets_limit=1),
        client=client,
        utcnow_provider=_clock,
    )
    assert result.status == "POPULATION_RECORDS_PERSISTED_REGISTRATION_FAILED"
    assert result.recovery_required is True
    assert result.registration_error_codes == ()
    assert "SECRET_ITER" not in repr(result)
    assert (
        len(load_and_verify_point_in_time_record_store(record_path).snapshot.records)
        == 1
    )


# ── Nested success-object fields are validated, never blindly dereferenced ─────


def test_success_result_with_fake_dataset_reference_fails_closed(monkeypatch):
    record_path, manifest_path = _stores()
    _reference, entry = _genuine_reference_and_entry()
    monkeypatch.setattr(
        pop,
        "persist_validated_record_batch_snapshot",
        lambda *a, **k: _adapter_success(object(), entry),
    )
    client = FakeClient([_market("100", ["a"])])
    result = populate_initial_polymarket_public_data(
        record_path,
        manifest_path,
        _config(allow_network=True, markets_limit=1),
        client=client,
        utcnow_provider=_clock,
    )
    assert result.is_valid is False
    assert result.status == "POPULATION_RECORDS_PERSISTED_REGISTRATION_FAILED"
    assert result.recovery_required is True
    assert result.dataset_snapshot_reference_id is None
    assert result.manifest_entry_id is None
    assert "POPULATION_UNEXPECTED_ERROR" not in result.error_codes
    assert (
        len(load_and_verify_point_in_time_record_store(record_path).snapshot.records)
        == 1
    )


def test_success_result_with_fake_manifest_entry_fails_closed(monkeypatch):
    record_path, manifest_path = _stores()
    reference, _entry = _genuine_reference_and_entry()
    monkeypatch.setattr(
        pop,
        "persist_validated_record_batch_snapshot",
        lambda *a, **k: _adapter_success(reference, object()),
    )
    client = FakeClient([_market("100", ["a"])])
    result = populate_initial_polymarket_public_data(
        record_path,
        manifest_path,
        _config(allow_network=True, markets_limit=1),
        client=client,
        utcnow_provider=_clock,
    )
    assert result.is_valid is False
    assert result.status == "POPULATION_RECORDS_PERSISTED_REGISTRATION_FAILED"
    assert result.recovery_required is True
    assert result.dataset_snapshot_reference_id is None
    assert result.manifest_entry_id is None
    assert "POPULATION_UNEXPECTED_ERROR" not in result.error_codes


def test_success_result_with_raising_nested_id_property_fails_closed(monkeypatch):
    record_path, manifest_path = _stores()
    _reference, entry = _genuine_reference_and_entry()
    marker = "SECRET_NESTED_ID https://nested.invalid"

    class _RaisingReference:
        @property
        def dataset_snapshot_reference_id(self):
            raise RuntimeError(marker)

    monkeypatch.setattr(
        pop,
        "persist_validated_record_batch_snapshot",
        lambda *a, **k: _adapter_success(_RaisingReference(), entry),
    )
    client = FakeClient([_market("100", ["a"])])
    result = populate_initial_polymarket_public_data(
        record_path,
        manifest_path,
        _config(allow_network=True, markets_limit=1),
        client=client,
        utcnow_provider=_clock,
    )
    # The exact-type gate rejects the fake reference before its id is ever read.
    assert result.is_valid is False
    assert result.status == "POPULATION_RECORDS_PERSISTED_REGISTRATION_FAILED"
    assert result.recovery_required is True
    assert "POPULATION_UNEXPECTED_ERROR" not in result.error_codes
    assert "SECRET_NESTED_ID" not in repr(result)


def test_genuine_already_persisted_recovery_uses_extracted_values(monkeypatch):
    # A genuine ADAPTER_ALREADY_PERSISTED path (idempotent recovery) still yields
    # a valid result built from extracted trusted scalars.
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
    assert type(recovered.dataset_snapshot_reference_id) is str
    assert type(recovered.manifest_entry_id) is str
