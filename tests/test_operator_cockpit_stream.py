"""S10-CC-STREAM-01 Control Center streaming / freshness / gap / resync transport (S01-S16).

The stream is a default-off, request-scoped SSE refresh/resync signal transport. These tests
prove the kill switch, the closed GET routes, fixed cadence, connection-local sequence,
transport-only framing, bounded disconnect/cancellation, the single centralized browser stream,
active-family-only invalidation and the transport-vs-domain semantic separation. No test opens
a socket or reaches any external or product network.
"""

from __future__ import annotations

import ast
import asyncio
import dataclasses
import inspect
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from src import operator_cockpit as cockpit
from src import operator_cockpit_stream as stream


ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "src" / "operator_cockpit_stream.py"
COCKPIT = ROOT / "src" / "operator_cockpit.py"
FRONTEND_ROOT = ROOT / "src" / "operator_cockpit_frontend"
FRONTEND = FRONTEND_ROOT / "src"
CONTRACT = ROOT / "docs" / "control_center_streaming_contract.md"

FAMILIES = ("overview", "market", "experiments", "strategies", "hermes", "alpha", "ops", "paper", "audit")
CADENCE = {
    "overview": 10, "market": 5, "experiments": 30, "strategies": 30, "hermes": 30,
    "alpha": 30, "ops": 5, "paper": 5, "audit": 10,
}
EXPECTED_STATUS_KEYS = {
    "read_only", "enabled", "transport", "semantics", "source_push", "canonical_event_stream",
    "domain_freshness_guarantee", "replay_available", "base_tick_seconds", "refresh_seconds_by_family",
}
ENVELOPE_KEYS = ["schema_version", "connection_id", "sequence", "kind", "family", "server_time_ns"]
INVALID = (400, {"error": {"code": "INVALID_INPUT"}})
DISABLED = (503, {"error": {"code": "STREAM_DISABLED"}})
FIXED_ID = "ccstream:" + "0123456789abcdef" * 2
OTHER_ID = "ccstream:" + "fedcba9876543210" * 2


def _status(enabled: bool) -> dict:
    return {
        "read_only": True,
        "enabled": enabled,
        "transport": "SSE",
        "semantics": "SERVER_PACED_ACTIVE_FAMILY_REFRESH",
        "source_push": False,
        "canonical_event_stream": False,
        "domain_freshness_guarantee": False,
        "replay_available": False,
        "base_tick_seconds": 5,
        "refresh_seconds_by_family": dict(CADENCE),
    }


def _app(enabled: bool = False):
    return cockpit.create_app(cockpit.CockpitConfig(None, None, streaming_enabled=enabled))


def _get(app, target: str) -> tuple[int, dict]:
    with TestClient(app) as client:
        response = client.get(target)
        return response.status_code, response.json()


def _method(app, target: str, method: str) -> int:
    with TestClient(app) as client:
        return client.request(method, target).status_code


def _parse_frames(raw: bytes) -> list[dict]:
    text = raw.decode("ascii")
    assert text.endswith("\n\n")
    frames = []
    for block in text[:-2].split("\n\n"):
        lines = block.split("\n")
        assert [line.split(": ", 1)[0] for line in lines] == ["id", "event", "data"], lines
        fields = dict(line.split(": ", 1) for line in lines)
        fields["envelope"] = json.loads(fields["data"])
        frames.append(fields)
    return frames


class FakeSleeper:
    """Deterministic sleeper: records each requested delay and yields once."""

    def __init__(self, block_after: int | None = None):
        self.calls: list[float] = []
        self.block_after = block_after
        self.cancelled = False

    async def __call__(self, seconds: float) -> None:
        self.calls.append(seconds)
        if self.block_after is not None and len(self.calls) > self.block_after:
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                self.cancelled = True
                raise
        await asyncio.sleep(0)


async def _never_disconnected() -> bool:
    return False


def _collect(family: str, count: int, *, ids=(FIXED_ID,), clock=None, sleeper=None) -> tuple[list[dict], FakeSleeper]:
    sleeper = sleeper or FakeSleeper()
    id_iter = iter(ids)
    times = iter(range(1_000, 10_000_000))

    async def run() -> list[bytes]:
        generator = stream.event_stream(
            family,
            _never_disconnected,
            sleep=sleeper,
            clock_ns=clock or (lambda: next(times)),
            new_connection_id=lambda: next(id_iter),
        )
        chunks = [await anext(generator) for _ in range(count)]
        await generator.aclose()
        return chunks

    chunks = asyncio.run(asyncio.wait_for(run(), 5))
    return [frame for chunk in chunks for frame in _parse_frames(chunk)], sleeper


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _module_code() -> str:
    """The stream module's executable code only: comments and every docstring removed."""
    tree = ast.parse(_source(MODULE))
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            body = node.body
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) \
                    and isinstance(body[0].value.value, str):
                node.body = body[1:] or [ast.Pass()]
    return ast.unparse(tree)


def _controller() -> str:
    app_source = _source(FRONTEND / "app.tsx")
    section = app_source[app_source.index("function StreamRefreshController("):]
    return section[: section.index("\n}\n")]


def _stream_shell_section() -> str:
    app_source = _source(FRONTEND / "app.tsx")
    start = app_source.index("// S10-CC-STREAM-01: the single centralized auto-refresh transport.")
    return app_source[start: app_source.index("export function ControlCenter()")]


def _api_stream_section() -> str:
    api_source = _source(FRONTEND / "api.ts")
    start = api_source.index("// S10-CC-STREAM-01 transport.")
    return api_source[start: api_source.index("// Cockpit reads can replay verified stores")]


def _function(source: str, name: str) -> str:
    section = source[source.index(f"function {name}("):]
    return section[: section.index("\n}\n")]


# --- Optional behavioral harness: runs the real api.ts under Node type stripping -------------

NODE_HARNESS = r"""
import { pathToFileURL } from "node:url";
const api = await import(pathToFileURL(process.argv[2]).href);
const id = (c) => "ccstream:" + c.repeat(32);
const ev = (overrides = {}) => ({
  schema_version: "1.0.0", connection_id: id("a"), sequence: 1, kind: "RESYNC_REQUIRED",
  family: "market", server_time_ns: "1791397060000985100", ...overrides,
});
const parse = (name, value, family = "market") =>
  api.parseStreamEvent(name, typeof value === "string" ? value : JSON.stringify(value), family);
const out = {};
out.valid = parse("resync", ev());
const bad = {
  wrong_family: parse("resync", ev(), "ops"),
  wrong_kind_for_name: parse("heartbeat", ev()),
  unknown_kind: parse("resync", ev({ kind: "SOURCE_CHANGED" })),
  extra_key: parse("resync", { ...ev(), market_id: "m" }),
  missing_key: parse("resync", (({ server_time_ns, ...rest }) => rest)(ev())),
  seq_zero: parse("resync", ev({ sequence: 0 })),
  seq_negative: parse("resync", ev({ sequence: -1 })),
  seq_fraction: parse("resync", ev({ sequence: 1.5 })),
  seq_string: parse("resync", ev({ sequence: "1" })),
  seq_unsafe: parse("resync", ev({ sequence: 2 ** 53 })),
  id_upper: parse("resync", ev({ connection_id: id("A") })),
  id_short: parse("resync", ev({ connection_id: "ccstream:abc" })),
  id_prefix: parse("resync", ev({ connection_id: "stream:" + "a".repeat(32) })),
  time_number: parse("resync", ev({ server_time_ns: 1 })),
  time_leading_zero: parse("resync", ev({ server_time_ns: "01" })),
  time_negative: parse("resync", ev({ server_time_ns: "-1" })),
  schema: parse("resync", ev({ schema_version: "1.0.1" })),
  not_json: parse("resync", "{not json"),
  array: parse("resync", "[1,2]"),
  oversized: parse("resync", JSON.stringify(ev()) + " ".repeat(600)),
  not_string: api.parseStreamEvent("resync", { ...ev() }, "market"),
};
out.bad = bad;
const step = (baseline, event) => api.advanceStreamBaseline(baseline, event);
const e = (sequence, kind, c = "a") => ({ ...ev({ sequence, kind, connection_id: id(c) }) });
const trace = [];
let baseline = null;
for (const event of [
  e(1, "RESYNC_REQUIRED"), e(2, "HEARTBEAT"), e(3, "REFRESH_DUE"), e(5, "HEARTBEAT"),
  e(6, "HEARTBEAT"), e(6, "HEARTBEAT"), e(4, "REFRESH_DUE"), e(5, "RESYNC_REQUIRED"),
  e(2, "HEARTBEAT", "b"), e(3, "REFRESH_DUE", "b"), e(1, "RESYNC_REQUIRED", "c"),
]) {
  const result = step(baseline, event);
  baseline = result.baseline;
  trace.push([event.sequence, event.kind, result.resync, result.invalidate, result.baseline.sequence]);
}
out.trace = trace;
out.first_heartbeat = step(null, e(7, "HEARTBEAT"));
out.url = api.streamEventUrl("market");
const status = {
  read_only: true, enabled: true, transport: "SSE", semantics: "SERVER_PACED_ACTIVE_FAMILY_REFRESH",
  source_push: false, canonical_event_stream: false, domain_freshness_guarantee: false,
  replay_available: false, base_tick_seconds: 5,
  refresh_seconds_by_family: { overview: 10, market: 5, experiments: 30, strategies: 30, hermes: 30,
    alpha: 30, ops: 5, paper: 5, audit: 10 },
};
const statusResult = (body) => { try { return api.parseStreamStatus(body).enabled; } catch (error) { return error.code; } };
out.status = {
  exact: statusResult(status),
  enabled_string: statusResult({ ...status, enabled: "true" }),
  extra_key: statusResult({ ...status, fresh: true }),
  freshness_true: statusResult({ ...status, domain_freshness_guarantee: true }),
  missing_family: statusResult({ ...status, refresh_seconds_by_family: { market: 5 } }),
  markets_token: statusResult({ ...status, refresh_seconds_by_family: { ...status.refresh_seconds_by_family, markets: 5 } }),
  zero_cadence: statusResult({ ...status, refresh_seconds_by_family: { ...status.refresh_seconds_by_family, ops: 0 } }),
};
console.log(JSON.stringify(out));
"""


@pytest.fixture(scope="module")
def node_behavior(tmp_path_factory):
    """Runs the real api.ts when Node and the locked node_modules are installed; else None."""
    node = shutil.which("node")
    if node is None or not (FRONTEND_ROOT / "node_modules" / "@tanstack" / "react-query").is_dir():
        return None
    harness = tmp_path_factory.mktemp("stream_harness") / "harness.mjs"
    harness.write_text(NODE_HARNESS, encoding="utf-8", newline="\n")
    completed = subprocess.run(
        [node, str(harness), str(FRONTEND / "api.ts")],
        capture_output=True, text=True, timeout=60, check=False,
    )
    assert completed.returncode == 0, completed.stderr[-2000:]
    return json.loads(completed.stdout.strip().splitlines()[-1])


# ---------------------------------------------------------------------------
# S01-S03 configuration, kill switch and routes
# ---------------------------------------------------------------------------


def test_s01_streaming_defaults_off_and_requires_explicit_enable(monkeypatch, tmp_path) -> None:
    names = [field.name for field in dataclasses.fields(cockpit.CockpitConfig)]
    assert names == [
        "market_truth_path", "experiment_registry_path", "paper_store_path", "gateway_store_path",
        "strategy_lifecycle_path", "hermes_strategy_manager_path", "alpha_factory_registry_path",
        "alpha_discovery_registry_path", "streaming_enabled",
    ]
    assert cockpit.CockpitConfig(None, None).streaming_enabled is False
    legacy = cockpit.CockpitConfig(None, None, None, None, None, None, None, None)
    assert legacy.streaming_enabled is False
    assert cockpit.CockpitConfig(None, None, None, None, None, None, None, None, True).streaming_enabled is True
    for wrong in (1, 0, "true", "false", None, 1.0):
        with pytest.raises(TypeError):
            cockpit.CockpitConfig(None, None, streaming_enabled=wrong)
    assert _get(_app(), "/api/stream/events?family=market") == DISABLED

    # Environment never enables streaming.
    for name in ("COCKPIT_ENABLE_STREAMING", "ENABLE_STREAMING", "STREAMING_ENABLED", "CC_STREAMING"):
        monkeypatch.setenv(name, "1")
    launched: list = []
    monkeypatch.setitem(sys.modules, "uvicorn", SimpleNamespace(run=lambda app, **kw: launched.append((app, kw))))
    base_args = ["--market-truth-store", str(tmp_path / "m.sqlite3"),
                 "--experiment-registry", str(tmp_path / "r.sqlite3")]
    assert cockpit.main(base_args) == 0
    assert cockpit.main(base_args + ["--enable-streaming"]) == 0
    assert [kw for _app_obj, kw in launched] == [{"host": "127.0.0.1", "port": 8000}] * 2
    assert _get(launched[0][0], "/api/stream/status") == (200, _status(False))
    assert _get(launched[1][0], "/api/stream/status") == (200, _status(True))
    with pytest.raises(SystemExit):
        cockpit.main(base_args + ["--enable-streaming=yes"])

    source = _source(COCKPIT)
    assert source.count('parser.add_argument("--enable-streaming", action="store_true", default=False)') == 1
    assert "streaming_enabled=args.enable_streaming" in source
    assert "streaming_enabled: bool = False" in source
    for text in (source, _module_code()):
        assert "environ" not in text and "getenv" not in text and "dotenv" not in text


def test_s02_status_contract_and_query_closure() -> None:
    for enabled in (False, True):
        app = _app(enabled)
        status, body = _get(app, "/api/stream/status")
        assert status == 200
        assert body == _status(enabled)
        assert set(body) == EXPECTED_STATUS_KEYS
        assert list(body["refresh_seconds_by_family"]) == list(FAMILIES)
        for query in ("?x", "?x=", "?x=1", "?enabled=true", "?family=market", "?a=1&a=2", "?limit=1"):
            assert _get(app, "/api/stream/status" + query) == INVALID, query
    # The status is transport configuration only: no truthy freshness/currentness/source claim.
    for claim in ("source_push", "canonical_event_stream", "domain_freshness_guarantee", "replay_available"):
        assert _status(True)[claim] is False
    serialized = json.dumps(stream.stream_status(True)).lower()
    for promoted in ("current", "fresh\": true", "healthy", "ready", "live", "account", "network"):
        assert promoted not in serialized, promoted
    assert stream.stream_status(False)["refresh_seconds_by_family"] is not stream.STREAM_FAMILY_REFRESH_SECONDS
    with pytest.raises(TypeError):
        stream.stream_status(1)


def test_s03_events_route_family_validation_disabled_and_method_closure() -> None:
    invalid_queries = (
        "", "?", "?family=", "?family=markets", "?family=MARKET", "?family=Market", "?Family=market",
        "?family=market&family=market", "?family=market&family=ops", "?family=market&x=1",
        "?x=market", "?family=overview%20", "?family=%20overview", "?family=stream", "?family=cc",
    )
    for enabled in (False, True):
        app = _app(enabled)
        for query in invalid_queries:
            # Query shape is validated before the enablement check.
            assert _get(app, "/api/stream/events" + query) == INVALID, (enabled, query)
    disabled = _app(False)
    for family in FAMILIES:
        assert _get(disabled, f"/api/stream/events?family={family}") == DISABLED, family
    assert cockpit.ERROR_STATUS["STREAM_DISABLED"] == 503
    for app in (_app(False), _app(True)):
        domain = {route.path: set(route.methods or ()) for route in app.routes if route.path.startswith("/api/")}
        assert len(domain) == 27
        assert [path for path in domain if path.startswith("/api/stream")] == ["/api/stream/status", "/api/stream/events"]
        assert domain["/api/stream/status"] == domain["/api/stream/events"] == {"GET"}
        for target in ("/api/stream/status", "/api/stream/events?family=market"):
            for method in ("POST", "PUT", "PATCH", "DELETE"):
                assert _method(app, target, method) == 405, (target, method)
    source = _source(COCKPIT)
    assert not re.search(r"@app\.(post|put|patch|delete|websocket|api_route)\(", source)
    route = source[source.index('@app.get("/api/stream/events")'):source.index("return app")]
    assert route.index("INVALID_INPUT") < route.index("STREAM_DISABLED") < route.index("StreamingResponse(")


# ---------------------------------------------------------------------------
# S04-S09 transport generator
# ---------------------------------------------------------------------------


def test_s04_first_event_is_connection_local_resync_sequence_one() -> None:
    sleeper = FakeSleeper()

    async def first() -> bytes:
        generator = stream.event_stream(
            "market", _never_disconnected, sleep=sleeper, clock_ns=lambda: 1_791_397_060_000_985_100,
            new_connection_id=lambda: FIXED_ID,
        )
        chunk = await anext(generator)
        assert sleeper.calls == []  # the first event is emitted before any wait
        await generator.aclose()
        return chunk

    chunk = asyncio.run(asyncio.wait_for(first(), 5))
    expected_data = (
        '{"schema_version":"1.0.0","connection_id":"' + FIXED_ID + '","sequence":1,'
        '"kind":"RESYNC_REQUIRED","family":"market","server_time_ns":"1791397060000985100"}'
    )
    assert chunk == f"id: {FIXED_ID}:1\nevent: resync\ndata: {expected_data}\n\n".encode("ascii")
    assert b"retry:" not in chunk and not chunk.startswith(b":")
    # Production ids are fresh UUID4-derived ccstream ids.
    ids = {stream._default_connection_id() for _ in range(50)}
    assert len(ids) == 50 and all(stream.CONNECTION_ID_RE.fullmatch(item) for item in ids)
    assert stream._new_connection_id is stream._default_connection_id
    for family in FAMILIES:
        frames, _ = _collect(family, 1)
        assert frames[0]["event"] == "resync"
        assert frames[0]["envelope"]["sequence"] == 1 and frames[0]["envelope"]["kind"] == "RESYNC_REQUIRED"


def test_s05_fixed_family_cadence_heartbeat_and_refresh_due() -> None:
    assert stream.BASE_TICK_SECONDS == 5
    assert stream.STREAM_EVENT_KINDS == ("RESYNC_REQUIRED", "REFRESH_DUE", "HEARTBEAT")
    assert stream.STREAM_FAMILY_REFRESH_SECONDS == CADENCE
    assert list(stream.STREAM_FAMILY_REFRESH_SECONDS) == list(FAMILIES) == list(stream.STREAM_FAMILIES)
    assert "markets" not in stream.STREAM_FAMILY_REFRESH_SECONDS
    assert stream.SSE_EVENT_NAMES == {"RESYNC_REQUIRED": "resync", "REFRESH_DUE": "refresh", "HEARTBEAT": "heartbeat"}
    # 60 seconds of ticks per family.
    for family, seconds in CADENCE.items():
        frames, sleeper = _collect(family, 13)
        assert sleeper.calls == [5] * 12
        kinds = [frame["envelope"]["kind"] for frame in frames]
        expected = ["RESYNC_REQUIRED"] + [
            "REFRESH_DUE" if (tick * 5) % seconds == 0 else "HEARTBEAT" for tick in range(1, 13)
        ]
        assert kinds == expected, family
        assert [frame["event"] for frame in frames] == [stream.SSE_EVENT_NAMES[kind] for kind in kinds]
        assert kinds.count("REFRESH_DUE") == 60 // seconds
    # The cadence is not caller-configurable and unknown families are refused.
    params = list(inspect.signature(stream.event_stream).parameters)
    assert params == ["family", "is_disconnected", "sleep", "clock_ns", "new_connection_id"]
    for wrong in ("markets", "MARKET", "stream", ""):
        with pytest.raises(ValueError):
            asyncio.run(anext(stream.event_stream(wrong, _never_disconnected)))
    # The frontend QueryFamily vocabulary is exactly the same nine tokens.
    api_source = _source(FRONTEND / "api.ts")
    query_family = re.search(r"export type QueryFamily = ([^;]+);", api_source).group(1)
    assert re.findall(r'"([a-z]+)"', query_family) == list(FAMILIES)
    families_const = re.search(r"export const STREAM_FAMILIES = \[(.*?)\] as const", api_source, re.S).group(1)
    assert re.findall(r'"([a-z]+)"', families_const) == list(FAMILIES)


def test_s06_sequence_is_monotonic_connection_local_and_not_persisted() -> None:
    frames, _ = _collect("overview", 20)
    assert [frame["envelope"]["sequence"] for frame in frames] == list(range(1, 21))
    assert [frame["id"] for frame in frames] == [f"{FIXED_ID}:{n}" for n in range(1, 21)]
    assert {frame["envelope"]["connection_id"] for frame in frames} == {FIXED_ID}
    # A second connection (a reconnect) gets a new id, restarts at 1 and resyncs first.
    again, _ = _collect("overview", 3, ids=(OTHER_ID,))
    assert [frame["envelope"]["sequence"] for frame in again] == [1, 2, 3]
    assert again[0]["envelope"]["kind"] == "RESYNC_REQUIRED"
    assert {frame["envelope"]["connection_id"] for frame in again} == {OTHER_ID}
    # No module-level transport state, history, buffer or replay storage.
    code = _module_code()
    assert "global " not in code and "nonlocal " not in code
    tree = ast.parse(_source(MODULE))
    module_names = {
        target.id for node in tree.body if isinstance(node, (ast.Assign, ast.AnnAssign))
        for target in (node.targets if isinstance(node, ast.Assign) else [node.target])
        if isinstance(target, ast.Name)
    }
    assert module_names == {
        "STREAM_SCHEMA_VERSION", "BASE_TICK_SECONDS", "STREAM_EVENT_KINDS", "STREAM_FAMILY_REFRESH_SECONDS",
        "STREAM_FAMILIES", "CONNECTION_ID_RE", "SSE_EVENT_NAMES", "Sleeper", "DisconnectProbe",
        "_sleep", "_clock_ns", "_new_connection_id",
    }
    for stored in ("history", "buffer", "replay_log", "deque", "last_event_id", "Last-Event-ID", "append("):
        assert stored not in code, stored


def test_s07_disconnect_and_cancellation_terminate_without_retry_or_orphan_loop() -> None:
    async def disconnect_case() -> tuple[int, list[float]]:
        probes = iter([False, False, True])
        sleeper = FakeSleeper()

        async def probe() -> bool:
            return next(probes)

        generator = stream.event_stream("ops", probe, sleep=sleeper, new_connection_id=lambda: FIXED_ID)
        emitted = [chunk async for chunk in generator]
        return len(emitted), sleeper.calls

    count, calls = asyncio.run(asyncio.wait_for(disconnect_case(), 5))
    assert count == 3  # resync + two ticks; the third tick observes the disconnect and stops
    assert calls == [5, 5, 5]

    async def cancel_case() -> tuple[bool, bool, int]:
        sleeper = FakeSleeper(block_after=1)
        generator = stream.event_stream("paper", _never_disconnected, sleep=sleeper, new_connection_id=lambda: FIXED_ID)
        received: list[bytes] = []

        async def consume() -> None:
            async for chunk in generator:
                received.append(chunk)

        task = asyncio.create_task(consume())
        while len(sleeper.calls) < 2:
            await asyncio.sleep(0)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        await generator.aclose()
        leftover = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
        with pytest.raises(StopAsyncIteration):
            await anext(generator)
        return sleeper.cancelled, not leftover, len(received)

    cancelled, no_leftover, received = asyncio.run(asyncio.wait_for(cancel_case(), 5))
    assert cancelled and no_leftover and received == 2
    assert len(FakeSleeper().calls) == 0

    # aclose() after the first event ends the loop; no retry, no background continuation.
    async def close_case() -> list[float]:
        sleeper = FakeSleeper()
        generator = stream.event_stream("audit", _never_disconnected, sleep=sleeper, new_connection_id=lambda: FIXED_ID)
        await anext(generator)
        await generator.aclose()
        with pytest.raises(StopAsyncIteration):
            await anext(generator)
        return sleeper.calls

    assert asyncio.run(asyncio.wait_for(close_case(), 5)) == []
    code = _module_code()
    for forbidden in ("create_task", "ensure_future", "run_in_executor", "get_event_loop", "call_later",
                      "threading", "Thread(", "retry", "try:", "except", "finally", "background"):
        assert forbidden not in code, forbidden
    cockpit_code = _source(COCKPIT)
    for forbidden in ("on_event", "lifespan", "add_event_handler", "BackgroundTask", "create_task",
                      "ensure_future", "threading"):
        assert forbidden not in cockpit_code, forbidden


def test_s08_stream_module_has_no_domain_store_network_filesystem_or_persistence_imports() -> None:
    tree = ast.parse(_source(MODULE))
    modules = {
        node.module if isinstance(node, ast.ImportFrom) else alias.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    assert modules == {"__future__", "asyncio", "json", "re", "time", "typing", "uuid"}
    code = _module_code()
    for forbidden in (
        "sqlite3", "open(", "pathlib", "Path(", "subprocess", "socket", "urllib", "http.client", "requests",
        "httpx", "websocket", "WebSocket", "aiohttp", "starlette", "fastapi", "Request", "src.", "paper_trading",
        "execution_gateway", "strategy_lifecycle", "research_runtime", "data_layer", "operator_cockpit_research",
        "operator_cockpit_ops", "load_", "read_text", "read_bytes", "read_gateway", "environ", "getenv",
        "write_text", "write_bytes", "pickle", "shelve", "dbm", "executemany", "poll", "head_entry",
        "market_id", "asset_id",
    ):
        assert forbidden not in code, forbidden
    assert re.findall(r"\bread_\w+", code) == ["read_only"]
    calls = {
        node.func.attr if isinstance(node.func, ast.Attribute) else getattr(node.func, "id", "")
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
    }
    assert not calls & {"open", "connect", "run", "Popen", "urlopen", "append", "initialize", "load", "read"}
    # The cockpit reaches the stream only through the module and passes only family + probe.
    cockpit_source = _source(COCKPIT)
    assert "from src import operator_cockpit_stream as stream" in cockpit_source
    assert cockpit_source.count("stream.event_stream(") == 1
    assert "stream.event_stream(pairs[0][1], request.is_disconnected)" in cockpit_source


def test_s09_sse_payload_is_transport_metadata_only_and_server_time_ns_is_string() -> None:
    huge = 2**63 + 7
    frames, _ = _collect("market", 4, clock=lambda: huge)
    for frame in frames:
        envelope = frame["envelope"]
        assert list(envelope) == ENVELOPE_KEYS
        assert envelope["schema_version"] == "1.0.0"
        assert envelope["server_time_ns"] == str(huge) and isinstance(envelope["server_time_ns"], str)
        assert type(envelope["sequence"]) is int and envelope["sequence"] >= 1
        assert envelope["kind"] in stream.STREAM_EVENT_KINDS and envelope["family"] == "market"
        assert frame["data"] == json.dumps(envelope, separators=(",", ":"))
        assert frame["id"] == f"{envelope['connection_id']}:{envelope['sequence']}"
    with pytest.raises(ValueError):
        stream.event_envelope(FIXED_ID.upper(), 1, "HEARTBEAT", "market", 1)
    for sequence in (0, -1, True, 1.0, "1"):
        with pytest.raises(ValueError):
            stream.event_envelope(FIXED_ID, sequence, "HEARTBEAT", "market", 1)
    for server_time in (-1, 1.5, "1", True):
        with pytest.raises(ValueError):
            stream.event_envelope(FIXED_ID, 1, "HEARTBEAT", "market", server_time)
    for kind in ("SOURCE_CHANGED", "MARKET_GAP", "heartbeat"):
        with pytest.raises(ValueError):
            stream.event_envelope(FIXED_ID, 1, kind, "market", 1)
    with pytest.raises(ValueError):
        stream.event_envelope(FIXED_ID, 1, "HEARTBEAT", "markets", 1)
    # No domain payload, path, error or private field can appear in the framing.
    code = _module_code()
    for domain_field in ("received_at", "observation", "experiment_id", "strategy_version", "assessment",
                         "candidate", "policy_id", "equity", "order", "fill", "gateway", "credential",
                         "Traceback", "repr(", "str(exc", "__file__"):
        assert domain_field not in code, domain_field


# ---------------------------------------------------------------------------
# S10-S15 frontend
# ---------------------------------------------------------------------------


def test_s10_frontend_has_one_central_eventsource_and_no_client_polling_or_websocket() -> None:
    sources = {path.name: _source(path) for path in sorted(FRONTEND.glob("*.ts*"))}
    assert set(sources) == {"api.ts", "app.tsx", "foundation.stories.tsx", "main.tsx"}
    combined = "".join(sources.values())
    assert combined.count("new EventSource(") == 1
    assert sources["app.tsx"].count("new EventSource(") == 1
    assert sources["app.tsx"].count("EventSource") == _controller().count("EventSource")
    assert "new EventSource(streamEventUrl(family))" in _controller()
    for name in ("api.ts", "foundation.stories.tsx", "main.tsx"):
        assert "EventSource" not in sources[name], name
    for banned in ("WebSocket", "setInterval", "refetchInterval", "setTimeout", "requestAnimationFrame",
                   "localStorage", "sessionStorage", "indexedDB", "useMutation", "sendBeacon",
                   "serviceWorker", "backoff", "Last-Event-ID", "lastEventId"):
        assert banned not in sources["api.ts"] + sources["app.tsx"], banned
    api_source = sources["api.ts"]
    assert api_source.count('method: "GET"') == 1
    assert not re.search(r"\b(POST|PUT|PATCH|DELETE)\b", api_source + sources["app.tsx"])
    for default in ("retry: false,", "refetchOnWindowFocus: false,", "refetchOnReconnect: false,", "staleTime: Infinity,"):
        assert api_source.count(default) == 1, default
    assert "streamEventUrl = (family: QueryFamily) => API_BASE + \"/stream/events?family=\" + encodeURIComponent(family)" in api_source
    assert not re.search(r"https?://", api_source + sources["app.tsx"])
    assert '["cc", "stream", "status"]' in api_source


def test_s11_frontend_resync_refresh_heartbeat_and_gap_invalidation_semantics(node_behavior) -> None:
    api_source = _source(FRONTEND / "api.ts")
    reducer = _function(api_source, "advanceStreamBaseline")
    assert "baseline.connectionId === event.connection_id && event.sequence === baseline.sequence + 1" in reducer
    assert 'if (!continuous || event.kind === "RESYNC_REQUIRED") return { baseline: next, resync: true, invalidate: true };' in reducer
    assert 'return { baseline: next, resync: false, invalidate: event.kind === "REFRESH_DUE" };' in reducer
    controller = _controller()
    assert controller.count("invalidateQueries(") == 1
    assert "queryClient.invalidateQueries({ queryKey: familyKey(family) })" in controller
    assert "if (step.invalidate) reread(step.resync);" in controller
    for forbidden in ("setQueryData", "resetQueries", "refetchQueries", "removeQueries", "invalidateQueries()",
                      '["cc"]', "queryKey: [\"cc\"", "fetchQuery", "message.data}"):
        assert forbidden not in controller, forbidden
    assert "setQueryData" not in _api_stream_section()
    if node_behavior is not None:
        # [sequence, kind, resync, invalidate, baseline sequence]
        assert node_behavior["trace"] == [
            [1, "RESYNC_REQUIRED", True, True, 1],   # first event: resync
            [2, "HEARTBEAT", False, False, 2],       # heartbeat: no invalidation
            [3, "REFRESH_DUE", False, True, 3],      # refresh due: active-family re-read
            [5, "HEARTBEAT", True, True, 5],         # skipped 4: transport gap -> resync
            [6, "HEARTBEAT", False, False, 6],
            [6, "HEARTBEAT", True, True, 6],         # duplicate sequence -> resync
            [4, "REFRESH_DUE", True, True, 4],       # backwards sequence -> resync
            [5, "RESYNC_REQUIRED", True, True, 5],   # explicit resync on the same connection
            [2, "HEARTBEAT", True, True, 2],         # new connection id -> resync
            [3, "REFRESH_DUE", False, True, 3],
            [1, "RESYNC_REQUIRED", True, True, 1],   # reconnect restarts at 1 with a new id
        ]
        assert node_behavior["first_heartbeat"] == {
            "baseline": {"connectionId": "ccstream:" + "a" * 32, "sequence": 7}, "resync": True, "invalidate": True,
        }


def test_s12_frontend_route_switch_cleanup_and_manual_refresh_preserved() -> None:
    app_source = _source(FRONTEND / "app.tsx")
    controller = _controller()
    assert "}, [enabled, family, queryClient]);" in controller
    cleanup = controller[controller.index("    return () => {"):]
    for step in ("open = false;", "source.removeEventListener(name, listener);", "source.onerror = null;", "source.close();"):
        assert step in cleanup, step
    assert "if (!enabled) return;" in controller  # disabled: no stream is constructed
    assert controller.index("if (!enabled) return;") < controller.index("new EventSource(")
    # onerror marks the transport disconnected without closing the source to retry by hand.
    onerror = controller[controller.index("source.onerror = () => {"):controller.index("return () => {")]
    assert "close()" not in onerror and "new EventSource" not in onerror and "Disconnected" in onerror
    # Manual Refresh is byte-for-byte the pre-STREAM control and is always rendered.
    assert _function(app_source, "RefreshControl") == (
        "function RefreshControl({ family }: { family: QueryFamily }) {\n"
        "  const queryClient = useQueryClient();\n"
        "  const fetching = useIsFetching({ queryKey: familyKey(family) }) > 0;\n"
        "  // Invalidate only the active route family; inactive pages keep their cached evidence.\n"
        "  const refresh = () => void queryClient.invalidateQueries({ queryKey: familyKey(family) });\n"
        "  return (\n"
        "    <Button variant=\"primary\" onClick={refresh} busy={fetching} disabled={fetching}>\n"
        "      {fetching ? \"Refreshing…\" : \"Refresh\"}\n"
        "    </Button>\n"
        "  );"
    )
    shell = _function(app_source, "ControlCenter")
    assert shell.count("<RefreshControl family={active.family} />") == 1
    assert shell.count("<StreamRefreshController family={active.family} />") == 1
    assert "enabled" not in shell
    paths = re.findall(r'\{ path: "(/[a-z]+)"', app_source)
    assert paths == ["/overview", "/markets", "/experiments", "/strategies", "/hermes", "/alpha", "/ops", "/paper", "/audit"]


def test_s13_frontend_parser_fails_closed_on_wrong_family_sequence_or_shape(node_behavior) -> None:
    api_source = _source(FRONTEND / "api.ts")
    parser = _function(api_source, "parseStreamEvent")
    for check in (
        "if (!isRecord(value) || !hasExactKeys(value, STREAM_EVENT_KEYS)) return null;",
        "if (schema_version !== STREAM_SCHEMA_VERSION) return null;",
        "!STREAM_CONNECTION_ID_RE.test(connection_id)) return null;",
        "!Number.isSafeInteger(sequence) || sequence < 1) return null;",
        "if (kind !== expectedKind) return null;",
        "if (value.family !== family) return null;",
        "!STREAM_SERVER_TIME_NS_RE.test(server_time_ns)) return null;",
    ):
        assert check in parser, check
    assert "const STREAM_CONNECTION_ID_RE = /^ccstream:[0-9a-f]{32}$/;" in api_source
    assert "const STREAM_SERVER_TIME_NS_RE = /^(0|[1-9][0-9]{0,19})$/;" in api_source
    controller = _controller()
    malformed = controller[controller.index("if (event === null) {"):controller.index("const step =")]
    assert "baseline = null;" in malformed and "return;" in malformed and "reread" not in malformed
    for leak in ("dangerouslySetInnerHTML", "{message.data}", "error.message", "String(error"):
        assert leak not in controller, leak
    status_parser = _function(api_source, "parseStreamStatus")
    assert 'throw new SafeApiError("MALFORMED_RESPONSE")' in status_parser
    assert "parseStreamStatus(await getJson<unknown>(\"/stream/status\", signal))" in api_source
    if node_behavior is not None:
        assert node_behavior["valid"] == {
            "schema_version": "1.0.0", "connection_id": "ccstream:" + "a" * 32, "sequence": 1,
            "kind": "RESYNC_REQUIRED", "family": "market", "server_time_ns": "1791397060000985100",
        }
        assert node_behavior["bad"] and all(value is None for value in node_behavior["bad"].values()), node_behavior["bad"]
        assert len(node_behavior["bad"]) == 21
        assert node_behavior["url"] == "/api/stream/events?family=market"
        assert node_behavior["status"] == {
            "exact": True, "enabled_string": "MALFORMED_RESPONSE", "extra_key": "MALFORMED_RESPONSE",
            "freshness_true": "MALFORMED_RESPONSE", "missing_family": "MALFORMED_RESPONSE",
            "markets_token": "MALFORMED_RESPONSE", "zero_cadence": "MALFORMED_RESPONSE",
        }


def test_s14_storybook_uses_shared_disabled_stream_handler_and_opens_no_real_stream() -> None:
    stories = _source(FRONTEND / "foundation.stories.tsx")
    assert "EventSource" not in stories and "/api/stream/events" not in stories
    stream_block = stories[stories.index("// S10-CC-STREAM-01:"):stories.index("export const OverviewHealthy")]
    assert not re.search(r"https?://", stream_block)
    assert 'const streamStatusDisabledHandler = http.get("/api/stream/status", () => HttpResponse.json(streamStatusDisabled));' in stories
    helper = stories[stories.index("const mock =\n"):]
    helper = helper[: helper.index("  };\n") + 4]
    assert "msw.use(streamStatusDisabledHandler, ...items.flat());" in helper
    assert stories.count("msw.use(") == 1
    assert stories.count("meta.story(") == stories.count("beforeEach: mock(") == 35
    literal = stories[stories.index("const streamStatusDisabled: StreamStatus = {") + len("const streamStatusDisabled: StreamStatus = "):]
    literal = literal[: literal.index("\n};\n") + 2]
    as_json = re.sub(r"(\w+):", r'"\1":', literal)
    as_json = re.sub(r",(\s*})", r"\1", as_json)
    assert json.loads(as_json) == stream.stream_status(False)
    preview = _source(FRONTEND_ROOT / ".storybook" / "preview.ts")
    assert 'http.all("/api/*"' in preview and "print.error()" in preview


def test_s15_transport_wording_never_promotes_freshness_currentness_or_trading_authority() -> None:
    app_source = _source(FRONTEND / "app.tsx")
    notice = (
        "Auto-refresh updates this workspace from the existing authoritative HTTP snapshots. "
        "Stream connection state is transport status, not domain freshness or trading readiness."
    )
    assert app_source.count(notice) == 1
    assert "<p className=\"stream-notice\">{STREAM_NOTICE}</p>" in app_source
    shell = _stream_shell_section()
    assert 'type TransportState = "Disabled" | "Connecting" | "Connected" | "Resyncing" | "Disconnected";' in shell
    assert "Auto-refresh: {state}" in shell and "Server refresh-signal time" in shell
    visible = shell.replace(notice, "")
    for phrase in (
        "data fresh", "is fresh", "market current", "account current", "host current", "network eligible",
        "execution ready", "live ready", "trade ready", "real-time", "realtime", "real time", "live feed",
        "source changed", "canonical event stream", "incident", "alert", "up to date", "healthy",
        "market-data gap", "market data gap", "system status", "Gate-C",
    ):
        assert phrase not in visible.lower(), phrase
    assert "Date.now" not in shell and "performance.now" not in shell
    assert "BigInt(serverTimeNs) / 1_000_000n" in shell and "Number(serverTimeNs" not in shell
    api_section = _api_stream_section().lower()
    for phrase in ("data fresh", "market current", "real-time", "source changed", "incident", "live ready"):
        assert phrase not in api_section, phrase
    contract = _source(CONTRACT)
    for separation in (
        "transport connected != domain fresh",
        "transport sequence != canonical store sequence",
        "REFRESH_DUE != source changed",
        "transport gap != market-data gap",
        "server signal time != market/account observation time",
        "recorded gateway state != current host/network/account truth",
        "SSE refresh != command/execution/live authority",
    ):
        assert separation in contract, separation
    # OPS-01 recorded gateway wording is unchanged by auto-refresh.
    assert "Recorded gateway state — not a fresh account, host or network check." in app_source


# ---------------------------------------------------------------------------
# S16 ASGI integration
# ---------------------------------------------------------------------------


def _drive(monkeypatch, *, spec_version: str, ticks: int, headers=(), block: bool = False):
    sleeper = FakeSleeper(block_after=ticks if block else None)
    ids = iter([FIXED_ID, OTHER_ID])
    monkeypatch.setattr(stream, "_sleep", sleeper)
    monkeypatch.setattr(stream, "_clock_ns", lambda: 42)
    monkeypatch.setattr(stream, "_new_connection_id", lambda: next(ids))
    app = _app(True)

    async def run() -> tuple[list[dict], list[float], bool]:
        sent: list[dict] = []
        disconnect = asyncio.Event()
        received = {"count": 0}

        async def receive() -> dict:
            received["count"] += 1
            if received["count"] == 1:
                return {"type": "http.request", "body": b"", "more_body": False}
            if disconnect.is_set():
                return {"type": "http.disconnect"}
            await disconnect.wait()
            return {"type": "http.disconnect"}

        async def send(message: dict) -> None:
            sent.append(message)
            bodies = [m for m in sent if m["type"] == "http.response.body" and m.get("body")]
            if len(bodies) >= ticks + 1:
                disconnect.set()

        scope = {
            "type": "http", "asgi": {"version": "3.0", "spec_version": spec_version}, "http_version": "1.1",
            "method": "GET", "scheme": "http", "path": "/api/stream/events", "raw_path": b"/api/stream/events",
            "query_string": b"family=market", "root_path": "",
            "headers": [(b"host", b"127.0.0.1:8000"), *headers],
            "client": ("127.0.0.1", 50000), "server": ("127.0.0.1", 8000),
        }
        await asyncio.wait_for(app(scope, receive, send), 5)
        leftover = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
        return sent, sleeper.calls, not leftover

    sent, calls, clean = asyncio.run(run())
    return sent, calls, clean, sleeper


def test_s16_asgi_streaming_response_contract_is_bounded_and_disconnect_safe(monkeypatch) -> None:
    for spec_version in ("2.4", "2.3"):
        sent, calls, clean, _ = _drive(
            monkeypatch, spec_version=spec_version, ticks=3,
            headers=[(b"last-event-id", f"{OTHER_ID}:41".encode("ascii"))],
        )
        start = sent[0]
        assert start["type"] == "http.response.start" and start["status"] == 200
        assert start["headers"] == [(b"content-type", b"text/event-stream"), (b"cache-control", b"no-cache")]
        chunks = [m["body"] for m in sent[1:] if m["type"] == "http.response.body" and m["body"]]
        frames = [frame for chunk in chunks for frame in _parse_frames(chunk)]
        assert len(frames) == 4, spec_version
        # Last-Event-ID is never used to resume: a fresh connection id, sequence 1, resync first.
        assert [f["envelope"]["sequence"] for f in frames] == [1, 2, 3, 4]
        assert {f["envelope"]["connection_id"] for f in frames} == {FIXED_ID}
        assert frames[0]["envelope"]["kind"] == "RESYNC_REQUIRED"
        assert [f["envelope"]["kind"] for f in frames[1:]] == ["REFRESH_DUE"] * 3
        assert all(f["envelope"]["server_time_ns"] == "42" for f in frames)
        assert calls == [5] * len(calls) and len(calls) <= 4  # bounded: stops at the disconnect
        assert clean, spec_version
        if spec_version == "2.4":
            assert sent[-1] == {"type": "http.response.body", "body": b"", "more_body": False}
    # Cancellation while the loop is waiting: the disconnect listener cancels the stream task.
    sent, calls, clean, sleeper = _drive(monkeypatch, spec_version="2.3", ticks=2, block=True)
    chunks = [m["body"] for m in sent if m["type"] == "http.response.body" and m.get("body")]
    assert len(chunks) == 3 and sleeper.cancelled and clean and len(calls) == 3
    # Disabled streaming never constructs a generator.
    monkeypatch.setattr(stream, "event_stream", lambda *a, **k: pytest.fail("stream constructed while disabled"))
    assert _get(_app(False), "/api/stream/events?family=market") == DISABLED
