"""Dedicated append-only SQLite journal and fail-closed recovery for WP173."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import sqlite3
from collections.abc import Mapping, Sequence

from .models import (
    PAPER_APPLICATION_ID,
    PAPER_USER_VERSION,
    PaperTradingError,
    canonical_json_bytes,
    content_id,
)


_TABLES = {
    "paper_journal": (
        "CREATE TABLE paper_journal ("
        "sequence INTEGER PRIMARY KEY AUTOINCREMENT,"
        "event_id TEXT NOT NULL UNIQUE,"
        "event_type TEXT NOT NULL,"
        "event_time_ns INTEGER NOT NULL,"
        "payload_json TEXT NOT NULL,"
        "previous_event_hash TEXT,"
        "event_hash TEXT NOT NULL UNIQUE)"
    ),
    "paper_checkpoint": (
        "CREATE TABLE paper_checkpoint ("
        "singleton INTEGER PRIMARY KEY CHECK(singleton=1),"
        "last_sequence INTEGER NOT NULL,"
        "last_event_hash TEXT NOT NULL,"
        "state_json TEXT NOT NULL,"
        "state_hash TEXT NOT NULL)"
    ),
}


@dataclass(frozen=True)
class JournalMutation:
    event_id: str
    event_type: str
    event_time_ns: int
    data: Mapping[str, object]
    state_after: Mapping[str, object]


@dataclass(frozen=True)
class JournalEvent:
    sequence: int
    event_id: str
    event_type: str
    event_time_ns: int
    data: dict[str, object]
    state_after: dict[str, object]
    previous_event_hash: str | None
    event_hash: str


def _normalize_ddl(value: object) -> str | None:
    return " ".join(value.split()) if isinstance(value, str) else None


def _validated_path(path: str | Path, *, may_create: bool) -> Path:
    if not isinstance(path, (str, Path)):
        raise PaperTradingError("SOURCE_UNAVAILABLE")
    target = Path(path)
    if (
        target.suffix != ".sqlite3"
        or not target.parent.exists()
        or not target.parent.is_dir()
    ):
        raise PaperTradingError("SOURCE_UNAVAILABLE")
    absolute = target.absolute()
    try:
        if target.is_symlink() or any(
            parent.is_symlink() for parent in absolute.parents
        ):
            raise PaperTradingError("SOURCE_UNAVAILABLE")
        if target.exists():
            if not target.is_file() or target.stat().st_nlink != 1:
                raise PaperTradingError("SOURCE_UNAVAILABLE")
        elif not may_create:
            raise PaperTradingError("SOURCE_UNAVAILABLE")
    except OSError:
        raise PaperTradingError("SOURCE_UNAVAILABLE") from None
    return target


class PaperStore:
    """One caller-selected paper database; never opens or mutates predecessor stores."""

    def __init__(self, path: str | Path, *, create: bool = False) -> None:
        self.path = _validated_path(path, may_create=create)
        self.reconciliation_blocked = False
        existed = self.path.exists()
        if not existed:
            try:
                fd = os.open(str(self.path), os.O_CREAT | os.O_EXCL | os.O_RDWR, 0o600)
                os.close(fd)
            except OSError:
                raise PaperTradingError("SOURCE_UNAVAILABLE") from None
        try:
            self.connection = sqlite3.connect(str(self.path), isolation_level=None)
            self.connection.execute("PRAGMA foreign_keys=ON")
            if existed:
                self._verify_schema()
            else:
                self._create_schema()
            self.reconciliation_blocked = not self._verify_journal_and_checkpoint()
        except PaperTradingError:
            if hasattr(self, "connection"):
                self.connection.close()
            raise
        except sqlite3.Error:
            if hasattr(self, "connection"):
                self.connection.close()
            raise PaperTradingError("SOURCE_UNAVAILABLE") from None

    def _create_schema(self) -> None:
        self.connection.execute("BEGIN")
        try:
            self.connection.execute(f"PRAGMA application_id={PAPER_APPLICATION_ID}")
            self.connection.execute(f"PRAGMA user_version={PAPER_USER_VERSION}")
            for ddl in _TABLES.values():
                self.connection.execute(ddl)
            self.connection.execute("COMMIT")
        except sqlite3.Error:
            self.connection.execute("ROLLBACK")
            raise PaperTradingError("SOURCE_UNAVAILABLE") from None

    def _verify_schema(self) -> None:
        try:
            app_id = self.connection.execute("PRAGMA application_id").fetchone()[0]
            version = self.connection.execute("PRAGMA user_version").fetchone()[0]
            integrity = self.connection.execute("PRAGMA integrity_check").fetchone()[0]
            sql = {
                row[0]: row[1]
                for row in self.connection.execute(
                    "SELECT name,sql FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
        except sqlite3.Error:
            raise PaperTradingError("SOURCE_UNAVAILABLE") from None
        if (
            app_id != PAPER_APPLICATION_ID
            or version != PAPER_USER_VERSION
            or integrity != "ok"
        ):
            raise PaperTradingError("SOURCE_UNAVAILABLE")
        if any(
            _normalize_ddl(sql.get(name)) != _normalize_ddl(ddl)
            for name, ddl in _TABLES.items()
        ):
            raise PaperTradingError("SOURCE_UNAVAILABLE")

    @staticmethod
    def _event_hash(
        sequence: int,
        event_id: str,
        event_type: str,
        event_time_ns: int,
        payload_json: str,
        previous_hash: str | None,
    ) -> str:
        return hashlib.sha256(
            canonical_json_bytes(
                {
                    "sequence": sequence,
                    "event_id": event_id,
                    "event_type": event_type,
                    "event_time_ns": event_time_ns,
                    "payload_json": payload_json,
                    "previous_event_hash": previous_hash,
                }
            )
        ).hexdigest()

    def _verify_journal_and_checkpoint(self) -> bool:
        try:
            rows = self.connection.execute(
                "SELECT sequence,event_id,event_type,event_time_ns,payload_json,"
                "previous_event_hash,event_hash FROM paper_journal ORDER BY sequence"
            ).fetchall()
            previous = None
            last_state_json = None
            for expected_sequence, row in enumerate(rows, 1):
                (
                    sequence,
                    event_id,
                    event_type,
                    event_time_ns,
                    payload_json,
                    prior,
                    digest,
                ) = row
                if sequence != expected_sequence or prior != previous:
                    return False
                if digest != self._event_hash(
                    sequence, event_id, event_type, event_time_ns, payload_json, prior
                ):
                    return False
                payload = json.loads(payload_json)
                if canonical_json_bytes(payload).decode("utf-8") != payload_json:
                    return False
                if not isinstance(payload, dict) or set(payload) != {
                    "data",
                    "state_after",
                }:
                    return False
                if event_id != content_id(
                    "paperevent:sha256:",
                    {
                        "event_type": event_type,
                        "event_time_ns": event_time_ns,
                        "data": payload["data"],
                    },
                ):
                    return False
                last_state_json = canonical_json_bytes(payload["state_after"]).decode(
                    "utf-8"
                )
                previous = digest
            checkpoint = self.connection.execute(
                "SELECT last_sequence,last_event_hash,state_json,state_hash FROM paper_checkpoint WHERE singleton=1"
            ).fetchone()
            if not rows:
                return checkpoint is None
            if checkpoint is None:
                return False
            sequence, digest, state_json, state_hash = checkpoint
            return bool(
                sequence == len(rows)
                and digest == previous
                and state_json == last_state_json
                and hashlib.sha256(state_json.encode("utf-8")).hexdigest() == state_hash
                and canonical_json_bytes(json.loads(state_json)).decode("utf-8")
                == state_json
            )
        except (sqlite3.Error, ValueError, TypeError):
            return False

    def close(self) -> None:
        self.connection.close()

    def __enter__(self) -> "PaperStore":
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        self.close()

    def events(self) -> tuple[JournalEvent, ...]:
        result = []
        try:
            rows = self.connection.execute(
                "SELECT sequence,event_id,event_type,event_time_ns,payload_json,"
                "previous_event_hash,event_hash FROM paper_journal ORDER BY sequence"
            ).fetchall()
            for row in rows:
                payload = json.loads(row[4])
                result.append(
                    JournalEvent(
                        row[0],
                        row[1],
                        row[2],
                        row[3],
                        payload["data"],
                        payload["state_after"],
                        row[5],
                        row[6],
                    )
                )
        except (sqlite3.Error, ValueError, KeyError, TypeError):
            raise PaperTradingError("RECONCILIATION_BLOCKED") from None
        return tuple(result)

    def load_state(self) -> dict[str, object] | None:
        if self.reconciliation_blocked:
            raise PaperTradingError("RECONCILIATION_BLOCKED")
        return self.load_state_allow_blocked()

    def load_state_allow_blocked(self) -> dict[str, object] | None:
        row = self.connection.execute(
            "SELECT state_json FROM paper_checkpoint WHERE singleton=1"
        ).fetchone()
        try:
            value = None if row is None else json.loads(row[0])
        except (TypeError, ValueError):
            raise PaperTradingError("RECONCILIATION_BLOCKED") from None
        return value

    def _write_checkpoint(self, sequence: int, digest: str, state_json: str) -> None:
        state_hash = hashlib.sha256(state_json.encode("utf-8")).hexdigest()
        self.connection.execute(
            "INSERT INTO paper_checkpoint(singleton,last_sequence,last_event_hash,state_json,state_hash) "
            "VALUES(1,?,?,?,?) ON CONFLICT(singleton) DO UPDATE SET "
            "last_sequence=excluded.last_sequence,last_event_hash=excluded.last_event_hash,"
            "state_json=excluded.state_json,state_hash=excluded.state_hash",
            (sequence, digest, state_json, state_hash),
        )

    def commit(
        self, mutations: Sequence[JournalMutation], final_state: Mapping[str, object]
    ) -> str:
        if self.reconciliation_blocked:
            raise PaperTradingError("RECONCILIATION_BLOCKED")
        if not mutations:
            raise PaperTradingError("MUTATION_INVALID")
        canonical_final = canonical_json_bytes(final_state).decode("utf-8")
        self.connection.execute("BEGIN IMMEDIATE")
        try:
            existing = []
            for mutation in mutations:
                row = self.connection.execute(
                    "SELECT event_type,event_time_ns,payload_json FROM paper_journal WHERE event_id=?",
                    (mutation.event_id,),
                ).fetchone()
                payload_json = canonical_json_bytes(
                    {
                        "data": dict(mutation.data),
                        "state_after": dict(mutation.state_after),
                    }
                ).decode("utf-8")
                if row is not None:
                    if row != (
                        mutation.event_type,
                        mutation.event_time_ns,
                        payload_json,
                    ):
                        raise PaperTradingError("IDENTITY_CONFLICT")
                    existing.append(True)
                else:
                    existing.append(False)
            if any(existing):
                if not all(existing):
                    raise PaperTradingError("IDENTITY_CONFLICT")
                checkpoint = self.connection.execute(
                    "SELECT state_json FROM paper_checkpoint WHERE singleton=1"
                ).fetchone()
                if checkpoint is None or checkpoint[0] != canonical_final:
                    raise PaperTradingError("IDENTITY_CONFLICT")
                self.connection.execute("COMMIT")
                return "IDEMPOTENT"
            row = self.connection.execute(
                "SELECT sequence,event_hash FROM paper_journal ORDER BY sequence DESC LIMIT 1"
            ).fetchone()
            sequence = row[0] if row else 0
            previous = row[1] if row else None
            for mutation in mutations:
                sequence += 1
                payload_json = canonical_json_bytes(
                    {
                        "data": dict(mutation.data),
                        "state_after": dict(mutation.state_after),
                    }
                ).decode("utf-8")
                digest = self._event_hash(
                    sequence,
                    mutation.event_id,
                    mutation.event_type,
                    mutation.event_time_ns,
                    payload_json,
                    previous,
                )
                self.connection.execute(
                    "INSERT INTO paper_journal(event_id,event_type,event_time_ns,payload_json,previous_event_hash,event_hash) "
                    "VALUES(?,?,?,?,?,?)",
                    (
                        mutation.event_id,
                        mutation.event_type,
                        mutation.event_time_ns,
                        payload_json,
                        previous,
                        digest,
                    ),
                )
                previous = digest
            self._write_checkpoint(sequence, previous, canonical_final)
            self.connection.execute("COMMIT")
            return "COMMITTED"
        except PaperTradingError:
            self.connection.execute("ROLLBACK")
            raise
        except Exception:
            self.connection.execute("ROLLBACK")
            raise PaperTradingError("TRANSACTION_FAILED") from None


def mutation(
    event_type: str,
    event_time_ns: int,
    data: Mapping[str, object],
    state_after: Mapping[str, object],
) -> JournalMutation:
    preimage = {
        "event_type": event_type,
        "event_time_ns": event_time_ns,
        "data": dict(data),
    }
    return JournalMutation(
        content_id("paperevent:sha256:", preimage),
        event_type,
        event_time_ns,
        dict(data),
        dict(state_after),
    )
