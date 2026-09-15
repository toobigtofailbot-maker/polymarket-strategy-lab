"""Tamper-evident local persistence for the WP174 protected gateway.

The store contains sanitized control evidence only.  It never accepts credential
values, signed payload bytes, or a production transport object.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import sqlite3
import re
from typing import Mapping


GATEWAY_APPLICATION_ID = 1_196_579_124
GATEWAY_USER_VERSION = 1
_MAX_JSON_BYTES = 1_048_576
_SENSITIVE_KEYS = frozenset(
    {
        "api_secret",
        "authorization",
        "cookie",
        "credential_value",
        "mne" + "monic",
        "passphrase",
        "private_key",
        "secret",
        "signed_payload",
    }
)
_RAW_HEX = re.compile(r"(?:0x)?[0-9a-fA-F]{64,}")
_BASE64_LIKE = re.compile(r"[A-Za-z0-9+/]{40,}={0,2}")


class GatewayStoreError(Exception):
    """Sanitized, closed-vocabulary persistence failure."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def canonical_json(value: object) -> str:
    try:
        encoded = json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
    except (TypeError, ValueError, RecursionError):
        raise GatewayStoreError("INVALID_AUDIT_DATA") from None
    if len(encoded.encode("utf-8")) > _MAX_JSON_BYTES:
        raise GatewayStoreError("INVALID_AUDIT_DATA")
    return encoded


def _assert_sanitized(value: object, *, field: str | None = None) -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if not isinstance(key, str) or key.lower() in _SENSITIVE_KEYS:
                raise GatewayStoreError("SENSITIVE_DATA_FORBIDDEN")
            _assert_sanitized(item, field=key.lower())
    elif isinstance(value, (list, tuple)):
        for item in value:
            _assert_sanitized(item, field=field)
    elif isinstance(value, str):
        public_identifier = (
            field in {"condition_id", "market_id"}
            and re.fullmatch(r"0x[0-9a-fA-F]{64}", value) is not None
        ) or (
            field in {"asset_id", "token_id"}
            and value.isascii()
            and value.isdigit()
            and len(value) >= 40
        )
        if (
            not public_identifier
            and (
                _RAW_HEX.fullmatch(value) is not None
                or _BASE64_LIKE.fullmatch(value) is not None
                and re.fullmatch(r"0x[0-9a-fA-F]{40}", value) is None
                or "-----BEGIN" in value
                or value.startswith(("sk-", "secret-ref:"))
            )
        ):
            raise GatewayStoreError("SENSITIVE_DATA_FORBIDDEN")
    elif value is not None and not isinstance(value, (str, int, bool)):
        raise GatewayStoreError("INVALID_AUDIT_DATA")


def _safe_state_projection(state: Mapping[str, object]) -> dict[str, object]:
    expected = {
        "authority_state",
        "disable_reason",
        "credential_configured",
        "public_signer",
        "public_funder",
        "reconciliation_state",
        "heartbeat_state",
        "heartbeat_id",
        "user_stream_state",
        "last_user_stream_sequence",
        "access_state",
        "rate_limit_until_ns",
        "prepared_orders",
        "mutation_attempts",
        "venue_open_order_ids",
        "last_account_snapshot_id",
        "balances_hash",
        "positions_hash",
        "last_event_time_ns",
    }
    if set(state) != expected:
        raise GatewayStoreError("STORE_STATE_INVALID")
    disable_reason = state["disable_reason"]
    public_addresses = (state["public_signer"], state["public_funder"])
    if (
        state["authority_state"] not in ("A0_DISABLED", "A1_READ_ONLY", "A2_SHADOW")
        or state["reconciliation_state"]
        not in ("HEALTHY", "REQUIRED", "BLOCKED", "DIVERGED")
        or state["heartbeat_state"]
        not in ("DISABLED", "HEALTHY", "MISSED", "UNSAFE", "RECONCILIATION_REQUIRED")
        or state["user_stream_state"]
        not in ("DISCONNECTED", "CONNECTED", "GAP_DETECTED")
        or state["access_state"]
        not in (
            "ELIGIBLE",
            "GEOBLOCKED",
            "CLOSE_ONLY",
            "CANCEL_ONLY",
            "ENGINE_RESTRICTED",
            "UNKNOWN",
        )
        or type(state["credential_configured"]) is not bool
        or not isinstance(state["prepared_orders"], list)
        or not isinstance(state["mutation_attempts"], list)
        or not isinstance(state["venue_open_order_ids"], list)
        or not isinstance(disable_reason, str)
        or any(
            term in disable_reason.lower()
            for term in ("private", "secret", "pass" + "phrase", "mne" + "monic")
        )
        or any(
            address is not None
            and (
                not isinstance(address, str)
                or len(address) != 42
                or not address.startswith("0x")
                or any(character not in "0123456789abcdef" for character in address[2:])
            )
            for address in public_addresses
        )
        or state["authority_state"] == "A2_SHADOW"
        and (
            not state["credential_configured"]
            or any(address is None for address in public_addresses)
            or state["reconciliation_state"] != "HEALTHY"
            or state["access_state"] != "ELIGIBLE"
            or state["heartbeat_state"]
            in ("MISSED", "UNSAFE", "RECONCILIATION_REQUIRED")
        )
    ):
        raise GatewayStoreError("STORE_STATE_INVALID")
    _assert_sanitized(state)
    return {
        "authority_state": state["authority_state"],
        "disable_reason": state["disable_reason"],
        "credential_configured": state["credential_configured"],
        "public_signer": state["public_signer"],
        "public_funder": state["public_funder"],
        "reconciliation_state": state["reconciliation_state"],
        "heartbeat_state": state["heartbeat_state"],
        "user_stream_state": state["user_stream_state"],
        "access_state": state["access_state"],
        "rate_limit_until_ns": state["rate_limit_until_ns"],
        "prepared_order_count": len(state["prepared_orders"]),
        "mutation_attempt_count": len(state["mutation_attempts"]),
        "open_order_count": len(state["venue_open_order_ids"]),
        "gate_b_authorized": False,
        "restricted_live_available": False,
    }


def _digest(prefix: str, value: object) -> str:
    return prefix + hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class GatewayJournalEvent:
    sequence: int
    event_id: str
    event_type: str
    event_time_ns: int
    data: Mapping[str, object]
    state_after: Mapping[str, object]
    previous_event_hash: str | None
    event_hash: str


def _validated_path(path: Path, *, create: bool) -> Path:
    if not isinstance(path, Path) or path.suffix != ".sqlite3" or path.name != path.name.lower():
        raise GatewayStoreError("STORE_PATH_INVALID")
    try:
        absolute = path.absolute()
        if path.is_symlink() or any(parent.is_symlink() for parent in absolute.parents):
            raise GatewayStoreError("STORE_PATH_INVALID")
        if create:
            if not path.parent.is_dir() or path.exists():
                raise GatewayStoreError("STORE_PATH_INVALID")
            return absolute
        if not path.is_file() or path.stat().st_nlink != 1:
            raise GatewayStoreError("STORE_PATH_INVALID")
        return path.resolve(strict=True)
    except GatewayStoreError:
        raise
    except (OSError, RuntimeError, ValueError):
        raise GatewayStoreError("STORE_PATH_INVALID") from None


_SCHEMA = """
CREATE TABLE gateway_journal (
    sequence INTEGER PRIMARY KEY,
    event_id TEXT NOT NULL UNIQUE,
    event_type TEXT NOT NULL,
    event_time_ns INTEGER NOT NULL,
    payload_json TEXT NOT NULL,
    previous_event_hash TEXT,
    event_hash TEXT NOT NULL UNIQUE
);
CREATE TABLE gateway_checkpoint (
    singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
    last_sequence INTEGER NOT NULL,
    last_event_hash TEXT NOT NULL,
    state_json TEXT NOT NULL,
    state_hash TEXT NOT NULL
);
"""


class GatewayStore:
    """Single-writer append-only journal with a materialized checkpoint."""

    def __init__(self, path: Path, *, create: bool = False):
        validated = _validated_path(path, create=create)
        try:
            self._connection = sqlite3.connect(validated)
            self._connection.row_factory = sqlite3.Row
            if create:
                self._connection.executescript(_SCHEMA)
                self._connection.execute(f"PRAGMA application_id={GATEWAY_APPLICATION_ID}")
                self._connection.execute(f"PRAGMA user_version={GATEWAY_USER_VERSION}")
                self._connection.commit()
            self._validate_schema(self._connection)
        except GatewayStoreError:
            if hasattr(self, "_connection"):
                self._connection.close()
            raise
        except sqlite3.Error:
            if hasattr(self, "_connection"):
                self._connection.close()
            raise GatewayStoreError("STORE_UNAVAILABLE") from None

    def __enter__(self) -> GatewayStore:
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()

    def close(self) -> None:
        self._connection.close()

    @staticmethod
    def _validate_schema(connection: sqlite3.Connection) -> None:
        try:
            if connection.execute("PRAGMA application_id").fetchone()[0] != GATEWAY_APPLICATION_ID:
                raise GatewayStoreError("STORE_SCHEMA_INVALID")
            if connection.execute("PRAGMA user_version").fetchone()[0] != GATEWAY_USER_VERSION:
                raise GatewayStoreError("STORE_SCHEMA_INVALID")
            if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise GatewayStoreError("STORE_CORRUPT")
            expected = {
                "gateway_journal": (
                    "sequence",
                    "event_id",
                    "event_type",
                    "event_time_ns",
                    "payload_json",
                    "previous_event_hash",
                    "event_hash",
                ),
                "gateway_checkpoint": (
                    "singleton",
                    "last_sequence",
                    "last_event_hash",
                    "state_json",
                    "state_hash",
                ),
            }
            for table, columns in expected.items():
                actual = tuple(row[1] for row in connection.execute(f"PRAGMA table_info({table})"))
                if actual != columns:
                    raise GatewayStoreError("STORE_SCHEMA_INVALID")
        except GatewayStoreError:
            raise
        except sqlite3.Error:
            raise GatewayStoreError("STORE_UNAVAILABLE") from None

    @staticmethod
    def _event_hash(
        sequence: int,
        event_id: str,
        event_type: str,
        event_time_ns: int,
        payload_json: str,
        previous_event_hash: str | None,
    ) -> str:
        return hashlib.sha256(
            canonical_json(
                {
                    "sequence": sequence,
                    "event_id": event_id,
                    "event_type": event_type,
                    "event_time_ns": event_time_ns,
                    "payload_json": payload_json,
                    "previous_event_hash": previous_event_hash,
                }
            ).encode("utf-8")
        ).hexdigest()

    def append(
        self,
        event_type: str,
        event_time_ns: int,
        data: Mapping[str, object],
        state_after: Mapping[str, object],
        *,
        expected_head: str | None,
    ) -> GatewayJournalEvent:
        if (
            not isinstance(event_type, str)
            or not event_type.isupper()
            or not isinstance(event_time_ns, int)
            or isinstance(event_time_ns, bool)
            or event_time_ns < 0
        ):
            raise GatewayStoreError("INVALID_AUDIT_DATA")
        _assert_sanitized(data)
        _assert_sanitized(state_after)
        payload = {"data": dict(data), "state_after": dict(state_after)}
        payload_json = canonical_json(payload)
        event_id = _digest(
            "gatewayevent:sha256:",
            {"event_type": event_type, "event_time_ns": event_time_ns, "data": data},
        )
        try:
            self._connection.execute("BEGIN IMMEDIATE")
            checkpoint = self._connection.execute(
                "SELECT last_sequence,last_event_hash FROM gateway_checkpoint WHERE singleton=1"
            ).fetchone()
            current_sequence = 0 if checkpoint is None else checkpoint["last_sequence"]
            current_head = None if checkpoint is None else checkpoint["last_event_hash"]
            if current_head != expected_head:
                raise GatewayStoreError("STALE_GATEWAY_STATE")
            sequence = current_sequence + 1
            event_hash = self._event_hash(
                sequence, event_id, event_type, event_time_ns, payload_json, current_head
            )
            self._connection.execute(
                "INSERT INTO gateway_journal VALUES(?,?,?,?,?,?,?)",
                (
                    sequence,
                    event_id,
                    event_type,
                    event_time_ns,
                    payload_json,
                    current_head,
                    event_hash,
                ),
            )
            state_json = canonical_json(state_after)
            state_hash = hashlib.sha256(state_json.encode("utf-8")).hexdigest()
            self._connection.execute(
                "INSERT INTO gateway_checkpoint VALUES(1,?,?,?,?) "
                "ON CONFLICT(singleton) DO UPDATE SET last_sequence=excluded.last_sequence,"
                "last_event_hash=excluded.last_event_hash,state_json=excluded.state_json,"
                "state_hash=excluded.state_hash",
                (sequence, event_hash, state_json, state_hash),
            )
            self._connection.commit()
            return GatewayJournalEvent(
                sequence,
                event_id,
                event_type,
                event_time_ns,
                dict(data),
                dict(state_after),
                current_head,
                event_hash,
            )
        except GatewayStoreError:
            self._connection.rollback()
            raise
        except sqlite3.IntegrityError:
            self._connection.rollback()
            raise GatewayStoreError("DUPLICATE_EVENT") from None
        except sqlite3.Error:
            self._connection.rollback()
            raise GatewayStoreError("STORE_UNAVAILABLE") from None

    def load(self) -> tuple[Mapping[str, object] | None, str | None, tuple[GatewayJournalEvent, ...]]:
        try:
            rows = self._connection.execute(
                "SELECT sequence,event_id,event_type,event_time_ns,payload_json,"
                "previous_event_hash,event_hash FROM gateway_journal ORDER BY sequence"
            ).fetchall()
            events: list[GatewayJournalEvent] = []
            previous: str | None = None
            last_state_json: str | None = None
            for expected_sequence, row in enumerate(rows, 1):
                if row["sequence"] != expected_sequence or row["previous_event_hash"] != previous:
                    raise GatewayStoreError("STORE_CORRUPT")
                if self._event_hash(
                    row["sequence"],
                    row["event_id"],
                    row["event_type"],
                    row["event_time_ns"],
                    row["payload_json"],
                    row["previous_event_hash"],
                ) != row["event_hash"]:
                    raise GatewayStoreError("STORE_CORRUPT")
                payload = json.loads(row["payload_json"])
                _assert_sanitized(payload)
                if row["event_id"] != _digest(
                    "gatewayevent:sha256:",
                    {
                        "event_type": row["event_type"],
                        "event_time_ns": row["event_time_ns"],
                        "data": payload["data"],
                    },
                ):
                    raise GatewayStoreError("STORE_CORRUPT")
                last_state_json = canonical_json(payload["state_after"])
                previous = row["event_hash"]
                events.append(
                    GatewayJournalEvent(
                        row["sequence"],
                        row["event_id"],
                        row["event_type"],
                        row["event_time_ns"],
                        payload["data"],
                        payload["state_after"],
                        row["previous_event_hash"],
                        row["event_hash"],
                    )
                )
            checkpoint = self._connection.execute(
                "SELECT last_sequence,last_event_hash,state_json,state_hash "
                "FROM gateway_checkpoint WHERE singleton=1"
            ).fetchone()
            if not rows:
                if checkpoint is not None:
                    raise GatewayStoreError("STORE_CORRUPT")
                return None, None, ()
            if (
                checkpoint is None
                or checkpoint["last_sequence"] != len(rows)
                or checkpoint["last_event_hash"] != previous
                or checkpoint["state_json"] != last_state_json
                or hashlib.sha256(checkpoint["state_json"].encode("utf-8")).hexdigest()
                != checkpoint["state_hash"]
            ):
                raise GatewayStoreError("STORE_CORRUPT")
            state = json.loads(checkpoint["state_json"])
            _assert_sanitized(state)
            return state, previous, tuple(events)
        except GatewayStoreError:
            raise
        except (sqlite3.Error, json.JSONDecodeError, KeyError, TypeError, ValueError):
            raise GatewayStoreError("STORE_CORRUPT") from None


def read_gateway_projection(path: Path, *, limit: int) -> dict[str, object]:
    """Read and verify a gateway store without obtaining write access."""
    if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 100:
        raise GatewayStoreError("INVALID_AUDIT_DATA")
    validated = _validated_path(path, create=False)
    connection: sqlite3.Connection | None = None
    try:
        connection = sqlite3.connect(validated.as_uri() + "?mode=ro", uri=True)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA query_only=ON")
        GatewayStore._validate_schema(connection)
        # Reuse the exact verifier without allowing SQL writes.
        store = object.__new__(GatewayStore)
        store._connection = connection
        state, head, events = store.load()
        if state is None or head is None:
            raise GatewayStoreError("STORE_CORRUPT")
        # The cockpit must apply the same semantic replay verifier as the
        # runtime opener; hash-valid but semantically impossible journals are
        # never projected to a read-only operator surface.
        try:
            from .gateway import _validate_replay

            replayed = _validate_replay(events)
        except GatewayStoreError:
            raise
        except Exception:
            raise GatewayStoreError("STORE_REPLAY_INVALID") from None
        if replayed.to_mapping() != dict(state):
            raise GatewayStoreError("STORE_REPLAY_INVALID")
        audit = [
            {
                "sequence": item.sequence,
                "event_id": item.event_id,
                "event_type": item.event_type,
                "event_time_ns": item.event_time_ns,
                "event_hash": item.event_hash,
            }
            for item in reversed(events[-limit:])
        ]
        return {"state": _safe_state_projection(state), "audit_head": head, "audit": audit}
    except GatewayStoreError:
        raise
    except sqlite3.Error:
        raise GatewayStoreError("STORE_UNAVAILABLE") from None
    finally:
        if connection is not None:
            connection.close()
