"""WP169 focused tests: runtime orchestration, import safety, and authority scan."""

from __future__ import annotations

import ast
import asyncio
import json
import pathlib
import threading

import pytest

from src.data_layer.polymarket import market_truth as mt
from src.data_layer.polymarket.market_truth_runtime import (
    _run_market_truth_runtime,
    _run_recurring,
    _validate_config,
    run_market_truth_runtime,
)

CONDITION = "0x" + "a" * 64
WALLET = "0x" + "b" * 40
_PKG = pathlib.Path(__file__).resolve().parents[3] / "src" / "data_layer" / "polymarket"
_MODULES = (
    "market_truth.py", "market_truth_store.py", "market_truth_websocket.py",
    "market_truth_data_api.py", "market_truth_onchain.py", "market_truth_runtime.py",
)


def test_import_has_no_network_or_runtime_side_effect() -> None:
    before = threading.active_count()
    import importlib

    for name in ("market_truth", "market_truth_store", "market_truth_websocket",
                 "market_truth_data_api", "market_truth_onchain", "market_truth_runtime"):
        importlib.import_module(f"src.data_layer.polymarket.{name}")
    assert threading.active_count() == before
    # No module-level (import-time) network / thread / process / scheduler call.
    forbidden_calls = {
        "urlopen", "socket", "connect", "run", "Thread", "Popen", "system",
        "create_task", "ensure_future", "start",
    }
    for module in _MODULES:
        tree = ast.parse((_PKG / module).read_text(encoding="utf-8"))
        for node in tree.body:
            for descendant in ast.walk(node):
                if isinstance(descendant, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    break
            if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
                name = _call_name(node.value.func)
                assert name not in forbidden_calls, (module, name)


def _call_name(func: ast.AST) -> str | None:
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def test_source_has_no_forbidden_authority_imports_or_calls() -> None:
    import io
    import tokenize

    # Identifiers (NAME tokens) that must never appear in real code paths. Docstrings
    # and comments (which legitimately describe the prohibitions) are excluded.
    forbidden_identifiers = {
        "place_order", "cancel_order", "sign_order", "submit_order",
        "py_clob_client", "eth_account", "PolymarketAuthedClient",
    }
    # Auth-style header/string literals that must never be emitted.
    forbidden_string_substrings = ("authorization", "x-api-key", "cookie", "bearer ")

    paths = [_PKG / module for module in _MODULES]
    paths.append((_PKG.parents[2] / "tools" / "polymarket" / "run_public_market_truth.py"))
    for path in paths:
        text = path.read_text(encoding="utf-8")
        names: set[str] = set()
        strings: list[str] = []
        for token in tokenize.generate_tokens(io.StringIO(text).readline):
            if token.type == tokenize.NAME:
                names.add(token.string)
            elif token.type == tokenize.STRING:
                strings.append(token.string.lower())
        assert not (names & forbidden_identifiers), (path.name, names & forbidden_identifiers)
        # market_truth.py holds the defensive no-echo scanner whose regex intentionally
        # names auth-style tokens to detect leaks; the transport modules must not.
        if path.name != "market_truth.py":
            joined = "\n".join(strings)
            for needle in forbidden_string_substrings:
                assert needle not in joined, (path.name, needle)
        # POST framing is allowed ONLY for the Polygon read-only JSON-RPC transport.
        if 'method="POST"' in text or "method='POST'" in text:
            assert "onchain" in path.name, (path.name, "unexpected POST")


def test_runtime_config_validation_and_precedence() -> None:
    limits = mt.AcquisitionLimits()
    db = pathlib.Path("x.sqlite3")
    # XOR: both assets and discover_active is invalid; neither is invalid.
    assert _validate_config(mt.MarketTruthRuntimeConfig(output_db=db, asset_ids=("7",), discover_active=True), limits) == "INPUT_INVALID"
    assert _validate_config(mt.MarketTruthRuntimeConfig(output_db=db), limits) == "INPUT_INVALID"
    # Valid explicit-assets config.
    assert _validate_config(mt.MarketTruthRuntimeConfig(output_db=db, asset_ids=("7",), duration_seconds=1), limits) is None
    # Exactly one block bound is invalid.
    assert _validate_config(mt.MarketTruthRuntimeConfig(output_db=db, asset_ids=("7",), from_block=5), limits) == "INPUT_INVALID"
    # Both block bounds override lookback and must be ordered within span.
    assert _validate_config(mt.MarketTruthRuntimeConfig(output_db=db, asset_ids=("7",), from_block=10, to_block=5), limits) == "INPUT_INVALID"
    assert _validate_config(mt.MarketTruthRuntimeConfig(output_db=db, asset_ids=("7",), from_block=5, to_block=10), limits) is None
    # Wallet / condition format bounds.
    assert _validate_config(mt.MarketTruthRuntimeConfig(output_db=db, asset_ids=("7",), wallet="0xbad"), limits) == "INPUT_INVALID"
    assert _validate_config(mt.MarketTruthRuntimeConfig(output_db=db, asset_ids=("7",), condition_id="0xbad"), limits) == "INPUT_INVALID"


async def _fake_ws(asset_ids, store, stop, *, limits=None, **kw):
    # A realistic WS streams until the shared stop is signalled (by a sibling terminal, the
    # duration watchdog, or caller stop), rather than terminating first and short-circuiting
    # sibling cadence passes.
    await stop.wait()
    return store.receipt("STOPPED", (), "CALLER_STOP")


async def _terminal_ws(asset_ids, store, stop, *, limits=None, **kw):
    """A WS that returns a terminal receipt immediately (for item-10 sibling-stop tests)."""
    return store.receipt("STOPPED", (), "CALLER_STOP")


def _fake_rpc(url, body, timeout):
    """Deterministic offline Polygon RPC transport for runtime orchestration tests."""
    method = json.loads(body)["method"]
    if method == "eth_chainId":
        return (200, {}, json.dumps({"result": "0x89"}).encode())
    if method == "eth_blockNumber":
        return (200, {}, json.dumps({"result": hex(1000)}).encode())
    if method == "eth_getLogs":
        return (200, {}, json.dumps({"result": []}).encode())
    if method == "eth_getBlockByNumber":
        bn = int(json.loads(body)["params"][0], 16)
        return (200, {}, json.dumps({"result": {"number": hex(bn), "hash": "0x" + "a" * 64, "timestamp": hex(1720000000)}}).encode())
    raise AssertionError(method)


def test_runtime_is_manual_bounded_and_gracefully_stoppable(tmp_path) -> None:
    async def scenario() -> mt.AcquisitionReceipt:
        stop = asyncio.Event()

        def data_transport(url, headers, timeout):
            return (200, {}, json.dumps({}).encode())

        cfg = mt.MarketTruthRuntimeConfig(
            output_db=tmp_path / "wp169_rt.sqlite3", asset_ids=("7",), duration_seconds=2
        )
        return await _run_market_truth_runtime(
            cfg, stop, websocket_runner=_fake_ws, rpc_transport=_fake_rpc, data_transport=data_transport
        )

    receipt = asyncio.run(scenario())
    assert receipt.status == "STOPPED"
    # Invalid config returns a closed FAILED receipt without opening a store.
    async def invalid() -> mt.AcquisitionReceipt:
        return await _run_market_truth_runtime(
            mt.MarketTruthRuntimeConfig(output_db=tmp_path / "y.sqlite3"), asyncio.Event(),
            websocket_runner=_fake_ws, rpc_transport=_fake_rpc,
        )

    bad = asyncio.run(invalid())
    assert bad.status == "FAILED" and bad.error_codes == ("INPUT_INVALID",)


def test_runtime_input_precedence_discovery_and_surface_selection(tmp_path) -> None:
    market_record = {
        "conditionId": CONDITION,
        "active": True,
        "closed": False,
        "acceptingOrders": True,
        "clobTokenIds": json.dumps(["7", "11"]),
        "question": "Will X happen?",
        "outcomes": ["Yes", "No"],
    }

    async def scenario() -> mt.AcquisitionReceipt:
        stop = asyncio.Event()
        calls = {"markets": 0, "other": 0}

        def data_transport(url, headers, timeout):
            if "/markets" in url:
                calls["markets"] += 1
                return (200, {}, json.dumps([market_record]).encode())
            calls["other"] += 1
            return (200, {}, json.dumps({}).encode())

        cfg = mt.MarketTruthRuntimeConfig(
            output_db=tmp_path / "wp169_disc.sqlite3", discover_active=True,
            duration_seconds=2, max_pages=1,
        )
        receipt = await _run_market_truth_runtime(
            cfg, stop, websocket_runner=_fake_ws, rpc_transport=_fake_rpc, data_transport=data_transport
        )
        assert calls["markets"] >= 1  # discovery queried Gamma /markets
        return receipt

    receipt = asyncio.run(scenario())
    assert receipt.status in ("STOPPED", "OK")
    # Discovery exhaustion (no eligible market) fails closed with RESPONSE_INVALID.
    async def empty() -> mt.AcquisitionReceipt:
        def data_transport(url, headers, timeout):
            return (200, {}, json.dumps([]).encode())

        cfg = mt.MarketTruthRuntimeConfig(
            output_db=tmp_path / "wp169_empty.sqlite3", discover_active=True, duration_seconds=1,
        )
        return await _run_market_truth_runtime(
            cfg, asyncio.Event(), websocket_runner=_fake_ws, rpc_transport=_fake_rpc, data_transport=data_transport
        )

    exhausted = asyncio.run(empty())
    assert exhausted.status == "FAILED" and exhausted.error_codes == ("RESPONSE_INVALID",)


def test_cadence_recurs_and_stop_interrupts_next_wait() -> None:
    """C: acquisition recurs (immediate + at least one more pass) and the stop event
    interrupts the next inter-pass wait; a terminal pass error propagates and stops."""
    async def scenario():
        stop = asyncio.Event()
        passes = {"n": 0}

        def pass_fn():
            passes["n"] += 1
            return mt.AcquisitionReceipt("OK", (), 0, 0, 0, 0, 0, 0, "NONE")

        waits = {"n": 0}

        async def wait(poll_seconds, stop_event):
            waits["n"] += 1
            if waits["n"] == 1:
                return False  # proceed to a second cadence pass
            stop_event.set()
            return True  # stop interrupts the next wait

        receipts = await _run_recurring(pass_fn, 10, stop, wait)
        return passes["n"], waits["n"], receipts

    pass_count, wait_count, receipts = asyncio.run(scenario())
    assert pass_count == 2  # immediate + one recurrence
    assert wait_count == 2 and all(r.status == "OK" for r in receipts)

    async def terminal():
        stop = asyncio.Event()
        calls = {"n": 0}

        def pass_fn():
            calls["n"] += 1
            return mt.AcquisitionReceipt("FAILED", ("RESPONSE_INVALID",), 0, 0, 0, 0, 0, 0, "NONE")

        async def wait(poll_seconds, stop_event):
            return False

        receipts = await _run_recurring(pass_fn, 10, stop, wait)
        return calls["n"], stop.is_set(), receipts

    calls, stopped, receipts = asyncio.run(terminal())
    # First terminal error propagates and signals siblings to stop; no second pass.
    assert calls == 1 and stopped is True
    assert receipts[-1].status == "FAILED"


async def _one_pass_wait(poll_seconds, stop_event):
    # After the immediate pass, signal the shared stop so a blocking WS returns promptly and
    # no surface runs a second cadence pass.
    stop_event.set()
    return True


def test_data_or_config_failure_propagates_as_failed(tmp_path) -> None:
    """#1: a Data/CLOB surface failure is not masked as OK; the runtime returns FAILED."""
    async def scenario() -> mt.AcquisitionReceipt:
        def data_transport(url, headers, timeout):
            return (404, {}, b"{}")  # non-retryable 4xx -> RESPONSE_INVALID

        cfg = mt.MarketTruthRuntimeConfig(
            output_db=tmp_path / "wp169_fail.sqlite3", asset_ids=("7",),
            condition_id=CONDITION, duration_seconds=2,
        )
        return await _run_market_truth_runtime(
            cfg, asyncio.Event(), websocket_runner=_fake_ws, rpc_transport=_fake_rpc,
            data_transport=data_transport, wait_fn=_one_pass_wait,
        )

    receipt = asyncio.run(scenario())
    assert receipt.status == "FAILED", receipt
    assert "RESPONSE_INVALID" in receipt.error_codes


def test_unexpected_task_exception_is_sanitized_failed(tmp_path) -> None:
    """#2: an unexpected task exception surfaces as sanitized FAILED INTERNAL_CLOSED_FAILURE."""
    async def raising_ws(*args, **kwargs):
        raise RuntimeError("boom with a /secret/path and Traceback text")

    async def scenario() -> mt.AcquisitionReceipt:
        def data_transport(url, headers, timeout):
            return (200, {}, b"{}")

        cfg = mt.MarketTruthRuntimeConfig(
            output_db=tmp_path / "wp169_exc.sqlite3", asset_ids=("7",), duration_seconds=2,
        )
        return await _run_market_truth_runtime(
            cfg, asyncio.Event(), websocket_runner=raising_ws, rpc_transport=_fake_rpc,
            data_transport=data_transport, wait_fn=_one_pass_wait,
        )

    receipt = asyncio.run(scenario())
    assert receipt.status == "FAILED"
    assert receipt.error_codes == ("INTERNAL_CLOSED_FAILURE",)
    assert mt.scan_no_echo({"error_codes": list(receipt.error_codes)})


def test_wallet_and_condition_filter_matrix(tmp_path) -> None:
    """#7: with condition + wallet, all three wallet surfaces carry the market filter and
    the single /trades request is shared (not duplicated)."""
    calls: list[str] = []

    async def scenario() -> None:
        def data_transport(url, headers, timeout):
            calls.append(url)
            return (200, {}, b"[]")  # empty page: OK with zero records

        cfg = mt.MarketTruthRuntimeConfig(
            output_db=tmp_path / "wp169_matrix.sqlite3", asset_ids=("7",),
            condition_id=CONDITION, wallet=WALLET, duration_seconds=2,
        )
        await _run_market_truth_runtime(
            cfg, asyncio.Event(), websocket_runner=_fake_ws, rpc_transport=_fake_rpc,
            data_transport=data_transport, wait_fn=_one_pass_wait,
        )

    asyncio.run(scenario())
    trades = [u for u in calls if "/trades" in u]
    activity = [u for u in calls if "/activity" in u]
    positions = [u for u in calls if "/positions" in u]
    assert trades and all("market=" in u and "user=" in u for u in trades)
    assert len(set(trades)) == 1  # single shared /trades, not duplicated
    assert activity and all("market=" in u and "user=" in u for u in activity)
    assert positions and all("market=" in u and "user=" in u for u in positions)


def test_discovery_normalizes_selected_market(tmp_path) -> None:
    """#8: active-market discovery stores a normalized Gamma dynamic_config observation
    for the selected market, not raw-only evidence."""
    from src.data_layer.polymarket.market_truth_store import MarketTruthStore

    market = {
        "conditionId": CONDITION, "active": True, "closed": False,
        "acceptingOrders": True, "clobTokenIds": json.dumps(["7", "11"]),
        "question": "Will X happen?", "outcomes": ["Yes", "No"],
        "events": [{"id": "55"}],
    }
    db = tmp_path / "wp169_disc_norm.sqlite3"

    async def scenario() -> None:
        def data_transport(url, headers, timeout):
            if "/markets" in url:
                return (200, {}, json.dumps([market]).encode())
            return (200, {}, b"{}")

        cfg = mt.MarketTruthRuntimeConfig(
            output_db=db, discover_active=True, duration_seconds=2, max_pages=1,
        )
        await _run_market_truth_runtime(
            cfg, asyncio.Event(), websocket_runner=_fake_ws, rpc_transport=_fake_rpc,
            data_transport=data_transport, wait_fn=_one_pass_wait,
        )

    asyncio.run(scenario())
    with MarketTruthStore(db) as store:
        configs = [
            o for o in store.iter_normalized(limit=1000)
            if o.event_kind == "dynamic_config" and o.market_id == CONDITION
        ]
        assert configs, "selected Gamma market must be stored as a normalized dynamic_config"


def test_network_call_limit_preserved_by_runtime_aggregation(tmp_path) -> None:
    """SEED01: a surface reaching the shared network-call budget surfaces as the runtime
    terminal STOPPED / NETWORK_CALL_LIMIT -- never mislabelled DURATION_EXPIRED."""
    async def scenario() -> mt.AcquisitionReceipt:
        def data_transport(url, headers, timeout):
            return (200, {}, b"[]")

        cfg = mt.MarketTruthRuntimeConfig(
            output_db=tmp_path / "wp169_ncl.sqlite3", asset_ids=("7",),
            condition_id=CONDITION, duration_seconds=5,
        )
        return await _run_market_truth_runtime(
            cfg, asyncio.Event(), websocket_runner=_fake_ws,
            data_transport=data_transport, rpc_transport=_fake_rpc, wait_fn=_one_pass_wait,
            limits=mt.AcquisitionLimits(max_network_calls=1),
        )

    receipt = asyncio.run(scenario())
    assert receipt.status == "STOPPED" and receipt.stop_reason == "NETWORK_CALL_LIMIT", receipt


def test_default_runtime_path_performs_rpc(tmp_path, monkeypatch) -> None:
    """SEED20: the DEFAULT runtime path (no injected rpc_transport) performs the certified
    Polygon RPC acquisition via the real default transport -- it is never silently skipped."""
    import src.data_layer.polymarket.market_truth_onchain as oc

    calls: list[str] = []

    def fake_default(url, body, timeout):
        method = json.loads(body)["method"]
        calls.append(method)
        return _fake_rpc(url, body, timeout)

    monkeypatch.setattr(oc, "_default_rpc_transport", fake_default)

    async def scenario() -> mt.AcquisitionReceipt:
        def data_transport(url, headers, timeout):
            return (200, {}, b"[]")

        cfg = mt.MarketTruthRuntimeConfig(
            output_db=tmp_path / "wp169_defrpc.sqlite3", asset_ids=("7",), duration_seconds=5,
        )
        # rpc_transport is intentionally NOT injected -> exercises the default path.
        return await _run_market_truth_runtime(
            cfg, asyncio.Event(), websocket_runner=_fake_ws,
            data_transport=data_transport, wait_fn=_one_pass_wait,
        )

    asyncio.run(scenario())
    assert "eth_chainId" in calls and "eth_blockNumber" in calls, calls


def test_public_api_signatures_match_frozen_contract() -> None:
    """SEED07: every frozen public function/method/class has EXACTLY its certified
    parameter list -- no extra keyword seams leak into the public API (seams are private)."""
    import inspect

    from src.data_layer.polymarket import market_truth as _mt
    from src.data_layer.polymarket.market_truth_store import MarketTruthStore
    from src.data_layer.polymarket.market_truth_websocket import (
        MarketBookState, SubscriptionController, run_market_websocket,
    )
    from src.data_layer.polymarket.market_truth_data_api import (
        PublicMarketDataClient, collect_public_page,
    )
    from src.data_layer.polymarket.market_truth_onchain import (
        collect_order_filled_logs, decode_order_filled_v2, validate_public_rpc_url,
    )
    from src.data_layer.polymarket.market_truth_runtime import run_market_truth_runtime as rmtr

    expected = {
        rmtr: ["config", "stop_event", "limits", "websocket_runner"],
        run_market_websocket: ["asset_ids", "store", "stop_event", "limits",
                               "websocket_url", "connection_factory", "subscription_controller"],
        collect_public_page: ["client", "store", "endpoint", "params", "max_pages", "stop_event"],
        collect_order_filled_logs: ["provider", "store", "from_block", "to_block",
                                    "latest_block", "limits", "transport"],
        decode_order_filled_v2: ["raw", "log", "latest_block", "block_timestamp", "confirmation_depth"],
        validate_public_rpc_url: ["provider"],
        _mt.make_raw_envelope: ["source_kind", "source_id", "source_cursor", "received_at",
                                "raw_bytes", "occurrence_sequence", "limits"],
        _mt.normalize_websocket_message: ["raw", "book_readiness"],
        _mt.normalize_public_record: ["raw", "endpoint", "record_index"],
        _mt.build_point_in_time_observation: ["raw", "observation", "ingestion_batch_id",
                                              "snapshot_id", "configuration", "market_context"],
        _mt.canonical_json_bytes: ["value", "max_bytes"],
        PublicMarketDataClient.__init__: ["self", "limits", "transport", "clock"],
        PublicMarketDataClient.get_page: ["self", "endpoint", "params"],
        MarketBookState.__init__: ["self", "asset_ids"],
        MarketBookState.plan: ["self", "observations"],
        MarketBookState.commit: ["self", "plan"],
        MarketBookState.discard: ["self", "plan", "reason"],
        MarketBookState.from_checkpoint: ["checkpoint"],
        SubscriptionController.__init__: ["self", "limits"],
        SubscriptionController.submit: ["self", "update"],
        MarketTruthStore.__init__: ["self", "path", "limits"],
        MarketTruthStore.append: ["self", "raw", "observations"],
        MarketTruthStore.write_checkpoint: ["self", "checkpoint_key", "value", "state"],
        MarketTruthStore.load_checkpoint: ["self", "checkpoint_key"],
        MarketTruthStore.iter_normalized: ["self", "after_sequence", "limit"],
        MarketTruthStore.mark_session: ["self", "session_id", "state", "received_at"],
        MarketTruthStore.mark_gap: ["self", "asset_id", "state", "reason", "received_at"],
    }
    for func, params in expected.items():
        actual = list(inspect.signature(func).parameters)
        assert actual == params, (getattr(func, "__qualname__", func), actual, params)


async def _stopped_ws(asset_ids, store, stop, *, limits=None, **kw):
    return store.receipt("STOPPED", (), "CALLER_STOP")


async def _failed_ws(asset_ids, store, stop, *, limits=None, **kw):
    return store.receipt("FAILED", ("RETRY_EXHAUSTED",), "RECONNECT_LIMIT")


def test_ws_terminal_stops_siblings_no_second_pass(tmp_path) -> None:
    """Item 10: any terminal WS receipt (STOPPED or FAILED) immediately signals sibling stop
    so a data cadence performs at most its one immediate pass -- never a second pass -- even
    when the inter-pass wait would otherwise continue."""
    async def _never_wait(poll_seconds, stop_event):
        return False  # would allow endless recurrence if the shared stop were not set

    async def run_with(ws, name) -> int:
        passes = {"trades": 0}

        def data_transport(url, headers, timeout):
            if "/trades" in url:
                passes["trades"] += 1
            return (200, {}, b"[]")

        cfg = mt.MarketTruthRuntimeConfig(
            output_db=tmp_path / f"item10_{name}.sqlite3", asset_ids=("7",),
            condition_id=CONDITION, duration_seconds=30,
        )
        await asyncio.wait_for(
            _run_market_truth_runtime(
                cfg, asyncio.Event(), websocket_runner=ws, data_transport=data_transport,
                rpc_transport=_fake_rpc, wait_fn=_never_wait,
            ),
            timeout=10,
        )
        return passes["trades"]

    assert asyncio.run(run_with(_stopped_ws, "stopped")) == 1
    assert asyncio.run(run_with(_failed_ws, "failed")) == 1


def test_no_unexpected_public_methods() -> None:
    """Item 8: MarketBookState and MarketTruthState expose ONLY the exact frozen public
    methods; implementation-only helpers are private (underscore-prefixed)."""
    from src.data_layer.polymarket.market_truth_websocket import MarketBookState
    from src.data_layer.polymarket.market_truth_store import MarketTruthStore

    frozen_book = {
        "subscribe", "unsubscribe", "mark_disconnect", "plan", "commit", "discard",
        "is_ready", "snapshot_json", "from_checkpoint",
    }
    public_book = {name for name in dir(MarketBookState) if not name.startswith("_")}
    assert public_book == frozen_book, public_book

    frozen_store = {
        "initialize", "append", "mark_session", "mark_gap", "write_checkpoint",
        "load_checkpoint", "iter_normalized", "receipt", "close",
    }
    public_store = {name for name in dir(MarketTruthStore) if not name.startswith("_")}
    assert public_store == frozen_store, public_store


def test_http_retry_exhaustion_stop_reason_is_none_not_reconnect_limit(tmp_path) -> None:
    """Reviewer B #1: an HTTP-surface RETRY_EXHAUSTED aggregates to FAILED with stop_reason
    NONE (never RECONNECT_LIMIT, which is reserved for WS reconnect exhaustion)."""
    async def scenario() -> mt.AcquisitionReceipt:
        def data_transport(url, headers, timeout):
            return (503, {"Retry-After": "0"}, b"{}")  # always retryable -> RETRY_EXHAUSTED

        cfg = mt.MarketTruthRuntimeConfig(
            output_db=tmp_path / "wp169_httpretry.sqlite3", asset_ids=("7",),
            condition_id=CONDITION, duration_seconds=30,
        )
        return await _run_market_truth_runtime(
            cfg, asyncio.Event(), websocket_runner=_fake_ws, data_transport=data_transport,
            rpc_transport=_fake_rpc, wait_fn=_one_pass_wait,
        )

    receipt = asyncio.run(scenario())
    assert receipt.status == "FAILED" and "RETRY_EXHAUSTED" in receipt.error_codes
    assert receipt.stop_reason == "NONE", receipt


def test_ws_reconnect_limit_stop_reason_preserved(tmp_path) -> None:
    """Reviewer B #1: a WS reconnect-exhaustion FAILED/RETRY_EXHAUSTED keeps its RECONNECT_LIMIT
    stop_reason through aggregation."""
    async def scenario() -> mt.AcquisitionReceipt:
        def data_transport(url, headers, timeout):
            return (200, {}, b"[]")

        cfg = mt.MarketTruthRuntimeConfig(
            output_db=tmp_path / "wp169_wsrecon.sqlite3", asset_ids=("7",),
            condition_id=CONDITION, duration_seconds=30,
        )
        return await _run_market_truth_runtime(
            cfg, asyncio.Event(), websocket_runner=_failed_ws, data_transport=data_transport,
            rpc_transport=_fake_rpc, wait_fn=_one_pass_wait,
        )

    receipt = asyncio.run(scenario())
    assert receipt.status == "FAILED" and receipt.error_codes == ("RETRY_EXHAUSTED",)
    assert receipt.stop_reason == "RECONNECT_LIMIT", receipt


def test_store_limit_aggregates_with_store_limit_stop_reason(tmp_path) -> None:
    """Reviewer round-2 #1: a STORE_LIMIT_EXCEEDED originating from a non-WS (HTTP) surface
    aggregates to the runtime terminal FAILED/STORE_LIMIT_EXCEEDED/STORE_LIMIT."""
    async def scenario() -> mt.AcquisitionReceipt:
        def data_transport(url, headers, timeout):
            return (200, {}, json.dumps([
                {"conditionId": CONDITION, "price": "0.5", "size": "1", "side": "BUY",
                 "transactionHash": "0x" + "c" * 64, "timestamp": 1720000000}
            ]).encode())

        cfg = mt.MarketTruthRuntimeConfig(
            output_db=tmp_path / "wp169_rtstore.sqlite3", asset_ids=("7",),
            condition_id=CONDITION, duration_seconds=30,
        )
        return await _run_market_truth_runtime(
            cfg, asyncio.Event(), websocket_runner=_fake_ws, data_transport=data_transport,
            rpc_transport=_fake_rpc, wait_fn=_one_pass_wait,
            limits=mt.AcquisitionLimits(max_store_rows=1),
        )

    receipt = asyncio.run(scenario())
    assert receipt.status == "FAILED" and "STORE_LIMIT_EXCEEDED" in receipt.error_codes
    assert receipt.stop_reason == "STORE_LIMIT", receipt
