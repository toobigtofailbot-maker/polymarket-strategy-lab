"""S10-CC-STREAM-01 request-scoped Control Center refresh/resync signal transport.

Transport metadata only. This module never reads a canonical store, source head, file,
environment value or network resource. It emits connection-local server-sent events that tell
the browser when to re-read the existing authoritative HTTP GET projections for its active
query family:

- ``RESYNC_REQUIRED``: first event of every connection; re-read the active family.
- ``REFRESH_DUE``: the fixed server cadence for the family elapsed; re-read the active family.
- ``HEARTBEAT``: a scheduled transport event; nothing is re-read.

A transport connection, sequence, heartbeat, signal time, refresh-due signal or transport gap
is never domain freshness, source change, market/account/host/network currentness or any
execution, live or command authority. There is no replay buffer, no persisted transport
history and no background task: the only loop is the generator below, which exists only while
its HTTP request is connected and stops on disconnect or cancellation without retrying.
"""

from __future__ import annotations

import asyncio
import json
import re
import time
from typing import Any, AsyncIterator, Awaitable, Callable
import uuid


STREAM_SCHEMA_VERSION = "1.0.0"
BASE_TICK_SECONDS = 5
STREAM_EVENT_KINDS = ("RESYNC_REQUIRED", "REFRESH_DUE", "HEARTBEAT")
# Keys are the existing frontend QueryFamily tokens ("market" is the family of the /markets
# route). Every cadence is a whole multiple of the base tick and is not caller-configurable.
STREAM_FAMILY_REFRESH_SECONDS = {
    "overview": 10,
    "market": 5,
    "experiments": 30,
    "strategies": 30,
    "hermes": 30,
    "alpha": 30,
    "ops": 5,
    "paper": 5,
    "audit": 10,
}
STREAM_FAMILIES = tuple(STREAM_FAMILY_REFRESH_SECONDS)
CONNECTION_ID_RE = re.compile(r"^ccstream:[0-9a-f]{32}$")
SSE_EVENT_NAMES = {
    "RESYNC_REQUIRED": "resync",
    "REFRESH_DUE": "refresh",
    "HEARTBEAT": "heartbeat",
}

Sleeper = Callable[[float], Awaitable[Any]]
DisconnectProbe = Callable[[], Awaitable[bool]]


def _default_connection_id() -> str:
    return "ccstream:" + uuid.uuid4().hex


# Internal deterministic test seams. Production uses the real sleeper, wall clock and UUID4.
# They are not reachable through HTTP, CLI, environment or configuration.
_sleep: Sleeper = asyncio.sleep
_clock_ns: Callable[[], int] = time.time_ns
_new_connection_id: Callable[[], str] = _default_connection_id


def stream_status(enabled: bool) -> dict[str, Any]:
    """Static transport configuration. It is never domain freshness or currentness."""
    if type(enabled) is not bool:
        raise TypeError("enabled must be bool")
    return {
        "read_only": True,
        "enabled": enabled,
        "transport": "SSE",
        "semantics": "SERVER_PACED_ACTIVE_FAMILY_REFRESH",
        "source_push": False,
        "canonical_event_stream": False,
        "domain_freshness_guarantee": False,
        "replay_available": False,
        "base_tick_seconds": BASE_TICK_SECONDS,
        "refresh_seconds_by_family": dict(STREAM_FAMILY_REFRESH_SECONDS),
    }


def event_envelope(
    connection_id: str, sequence: int, kind: str, family: str, server_time_ns: int
) -> dict[str, Any]:
    if not CONNECTION_ID_RE.fullmatch(connection_id):
        raise ValueError("invalid connection id")
    if type(sequence) is not int or sequence < 1:
        raise ValueError("invalid sequence")
    if kind not in STREAM_EVENT_KINDS:
        raise ValueError("invalid kind")
    if family not in STREAM_FAMILY_REFRESH_SECONDS:
        raise ValueError("invalid family")
    if type(server_time_ns) is not int or server_time_ns < 0:
        raise ValueError("invalid server time")
    return {
        "schema_version": STREAM_SCHEMA_VERSION,
        "connection_id": connection_id,
        "sequence": sequence,
        "kind": kind,
        "family": family,
        "server_time_ns": str(server_time_ns),
    }


def format_sse(envelope: dict[str, Any]) -> bytes:
    """Frame one envelope as an SSE event (no retry directive, no comment lines)."""
    data = json.dumps(envelope, separators=(",", ":"), ensure_ascii=True, allow_nan=False)
    return (
        f"id: {envelope['connection_id']}:{envelope['sequence']}\n"
        f"event: {SSE_EVENT_NAMES[envelope['kind']]}\n"
        f"data: {data}\n\n"
    ).encode("ascii")


async def event_stream(
    family: str,
    is_disconnected: DisconnectProbe,
    *,
    sleep: Sleeper | None = None,
    clock_ns: Callable[[], int] | None = None,
    new_connection_id: Callable[[], str] | None = None,
) -> AsyncIterator[bytes]:
    """One connection's request-scoped wait/emit loop.

    Every call is a new connection: fresh id, sequence 1 and an immediate RESYNC_REQUIRED.
    A Last-Event-ID from a previous connection is never consulted. The loop ends when the
    client disconnects or the request task is cancelled; it never retries and never outlives
    its request.
    """
    if family not in STREAM_FAMILY_REFRESH_SECONDS:
        raise ValueError("invalid family")
    sleep = sleep if sleep is not None else _sleep
    clock_ns = clock_ns if clock_ns is not None else _clock_ns
    connection_id = (new_connection_id if new_connection_id is not None else _new_connection_id)()
    refresh_ticks = STREAM_FAMILY_REFRESH_SECONDS[family] // BASE_TICK_SECONDS
    sequence = 1
    yield format_sse(event_envelope(connection_id, sequence, "RESYNC_REQUIRED", family, clock_ns()))
    tick = 0
    while True:
        await sleep(BASE_TICK_SECONDS)
        if await is_disconnected():
            return
        tick += 1
        sequence += 1
        kind = "REFRESH_DUE" if tick % refresh_ticks == 0 else "HEARTBEAT"
        yield format_sse(event_envelope(connection_id, sequence, kind, family, clock_ns()))
