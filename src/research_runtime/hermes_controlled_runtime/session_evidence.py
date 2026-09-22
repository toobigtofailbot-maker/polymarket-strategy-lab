"""Read-only sanitized projection of one exact pinned Hermes session."""

from __future__ import annotations

import dataclasses
import json
import re
import sqlite3
from pathlib import Path
from urllib.parse import quote

from .models import canonical_json_bytes, content_address, sha256_hex

ALLOWED_OBSERVED_TOOLS = frozenset({"web_search", "web_extract"})
_HTTPS = re.compile(r"https://[^\s\"'<>]+", re.IGNORECASE)


@dataclasses.dataclass(frozen=True)
class HermesToolCallEvidence:
    ordinal: int
    tool_name: str
    argument_sha256: str
    result_sha256: str | None
    observed_url_digests: tuple[str, ...]
    content_hashes: tuple[str, ...]


@dataclasses.dataclass(frozen=True)
class HermesSessionEvidence:
    session_evidence_id: str
    schema_version: str
    session_id_digest: str
    transcript_evidence_status: str
    observed_tool_calls: tuple[HermesToolCallEvidence, ...]
    observed_tool_names: tuple[str, ...]
    unexpected_tool_names: tuple[str, ...]
    auxiliary_task_names: tuple[str, ...]
    configured_backend: str
    actual_backend_attestation_status: str
    local_pre_dispatch_url_safety: str
    post_result_final_url_safety: str
    remote_firecrawl_http_redirect_telemetry: str
    remote_firecrawl_private_target_proof: str
    same_provider_recovery: str
    exact_provider_attempt_count: str

    @property
    def observed_url_digests(self) -> tuple[str, ...]:
        return tuple(sorted({digest for call in self.observed_tool_calls for digest in call.observed_url_digests}))

    def identity_fields(self) -> dict[str, object]:
        return {
            field.name: _value(getattr(self, field.name))
            for field in dataclasses.fields(self)
            if field.name != "session_evidence_id"
        }


def _value(value: object) -> object:
    if dataclasses.is_dataclass(value):
        return {field.name: _value(getattr(value, field.name)) for field in dataclasses.fields(value)}
    if isinstance(value, tuple):
        return [_value(item) for item in value]
    return value


def _urls(value: object) -> tuple[str, ...]:
    found: set[str] = set()
    def visit(item: object) -> None:
        if isinstance(item, str):
            for url in _HTTPS.findall(item[:262_144]):
                if len(url) <= 2048:
                    found.add(sha256_hex(url.encode("utf-8")))
        elif isinstance(item, list):
            for child in item[:256]:
                visit(child)
        elif isinstance(item, dict):
            for child in list(item.values())[:256]:
                visit(child)
    visit(value)
    return tuple(sorted(found))


def _projection(session_id: str, *, status: str, calls: tuple[HermesToolCallEvidence, ...] = (),
                auxiliary: tuple[str, ...] = (), configured_backend: str = "firecrawl") -> HermesSessionEvidence:
    names = tuple(call.tool_name for call in calls)
    unexpected = tuple(sorted(set(names) - ALLOWED_OBSERVED_TOOLS))
    partial = HermesSessionEvidence(
        "", "hermes-session-evidence/1.0.0", sha256_hex(session_id.encode("utf-8")),
        status, calls, names, unexpected, tuple(sorted(auxiliary)), configured_backend,
        "NOT_DIRECTLY_ATTESTED", "ENFORCED_PINNED_V0_21_3",
        "ENFORCED_PINNED_V0_21_3", "UNAVAILABLE", "UNKNOWN",
        "UNKNOWN_POSSIBLE", "UNKNOWN",
    )
    return dataclasses.replace(
        partial,
        session_evidence_id=content_address("hermessessionevidence:sha256:", partial.identity_fields()),
    )


def unavailable_session_evidence(session_id: str, *, configured_backend: str = "firecrawl") -> HermesSessionEvidence:
    return _projection(session_id, status="UNAVAILABLE", configured_backend=configured_backend)


def _columns(connection: sqlite3.Connection, table: str) -> tuple[str, ...]:
    return tuple(row[1] for row in connection.execute(f'PRAGMA table_info("{table}")'))


def collect_hermes_session_evidence(
    research_home: object, *, session_id: str, configured_backend: str = "firecrawl"
) -> HermesSessionEvidence:
    """Select exactly ``session_id`` from ``state.db`` without writes or migration."""
    if not isinstance(session_id, str) or not session_id:
        return unavailable_session_evidence("INVALID", configured_backend=configured_backend)
    try:
        db = Path(research_home) / "state.db"
        if not db.is_file() or db.is_symlink():
            return unavailable_session_evidence(session_id, configured_backend=configured_backend)
        posix_db = str(db.resolve()).replace(chr(92), "/")
        uri = f"file:{quote(posix_db, safe='/:')}?mode=ro&immutable=1"
        connection = sqlite3.connect(uri, uri=True)
        try:
            tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if "messages" not in tables:
                return unavailable_session_evidence(session_id, configured_backend=configured_backend)
            columns = _columns(connection, "messages")
            if "session_id" not in columns:
                return unavailable_session_evidence(session_id, configured_backend=configured_backend)
            order = "id" if "id" in columns else "rowid"
            wanted = [name for name in ("role", "content", "tool_calls", "tool_name") if name in columns]
            if not {"role", "content"}.issubset(wanted):
                return unavailable_session_evidence(session_id, configured_backend=configured_backend)
            sql = f'SELECT {",".join(wanted)} FROM messages WHERE session_id=? ORDER BY {order}'
            rows = connection.execute(sql, (session_id,)).fetchall()
            if not rows:
                return unavailable_session_evidence(session_id, configured_backend=configured_backend)
            calls: list[dict[str, object]] = []
            for row in rows:
                item = dict(zip(wanted, row))
                raw_calls = item.get("tool_calls")
                if raw_calls:
                    try:
                        decoded = json.loads(raw_calls) if isinstance(raw_calls, str) else raw_calls
                    except (ValueError, TypeError):
                        return _projection(session_id, status="INVALID", configured_backend=configured_backend)
                    if not isinstance(decoded, list):
                        return _projection(session_id, status="INVALID", configured_backend=configured_backend)
                    for call in decoded:
                        if not isinstance(call, dict):
                            return _projection(session_id, status="INVALID", configured_backend=configured_backend)
                        function = call.get("function", call)
                        if not isinstance(function, dict) or not isinstance(function.get("name"), str):
                            return _projection(session_id, status="INVALID", configured_backend=configured_backend)
                        arguments = function.get("arguments", "")
                        arg_raw = arguments if isinstance(arguments, str) else canonical_json_bytes(arguments).decode("utf-8")
                        calls.append({"name": function["name"], "arguments": arg_raw, "result": None})
                tool_name = item.get("tool_name")
                if item.get("role") == "tool" or tool_name:
                    if calls and calls[-1]["result"] is None:
                        calls[-1]["result"] = item.get("content") or ""
            evidence: list[HermesToolCallEvidence] = []
            for ordinal, call in enumerate(calls):
                arguments = str(call["arguments"])
                result = call["result"]
                combined: list[object] = [arguments]
                if result is not None:
                    combined.append(str(result))
                url_digests = tuple(sorted({digest for value in combined for digest in _urls(value)}))
                content_hashes = () if result is None else (sha256_hex(str(result).encode("utf-8")),)
                evidence.append(HermesToolCallEvidence(
                    ordinal, str(call["name"]), sha256_hex(arguments.encode("utf-8")),
                    None if result is None else sha256_hex(str(result).encode("utf-8")),
                    url_digests, content_hashes,
                ))
            auxiliary: tuple[str, ...] = ()
            if "session_model_usage" in tables:
                usage_columns = _columns(connection, "session_model_usage")
                task_col = next((name for name in ("task_name", "task_type", "task") if name in usage_columns), None)
                if "session_id" in usage_columns and task_col:
                    auxiliary = tuple(str(row[0]) for row in connection.execute(
                        f'SELECT "{task_col}" FROM session_model_usage WHERE session_id=? ORDER BY rowid', (session_id,)
                    ).fetchall() if row[0] is not None)
            return _projection(session_id, status="AVAILABLE", calls=tuple(evidence), auxiliary=auxiliary, configured_backend=configured_backend)
        finally:
            connection.close()
    except (OSError, sqlite3.Error, ValueError, TypeError):
        return unavailable_session_evidence(session_id, configured_backend=configured_backend)
