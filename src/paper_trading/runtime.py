"""Finite replay and read-only WP169 live-store adapters for WP173."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
import time
from collections.abc import Sequence
from decimal import Decimal

from src.data_layer.polymarket.market_truth import (
    canonical_json_bytes as wp169_canonical_bytes,
    compute_observation_id,
)
from src.data_layer.polymarket.market_truth_store import (
    APPLICATION_ID as MARKET_APPLICATION_ID,
    USER_VERSION as MARKET_USER_VERSION,
)
from src.research_runtime.executable_edge import (
    MarketTruthWindow,
    ResearchDecisionTrace,
    validate_market_truth_window,
    validate_research_decision_trace,
)

from .engine import PaperEngine
from .models import (
    PaperIntent,
    PaperMarketEvent,
    PaperTradingError,
    build_paper_intent,
    decimal_text,
)


_NORMALIZED_COLUMNS = (
    "archive_sequence",
    "observation_id",
    "occurrence_id",
    "raw_id",
    "source_kind",
    "event_kind",
    "event_id",
    "market_id",
    "asset_id",
    "event_time",
    "received_at",
    "canonical_payload_json",
    "canonical_payload_sha256",
    "status",
    "error_codes_json",
    "book_ready",
    "provenance_json",
)
_GAP_COLUMNS = ("sequence", "asset_id", "state", "reason", "received_at")


def _time_ns(value: str) -> int:
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%fZ").replace(
            tzinfo=timezone.utc
        )
    except (TypeError, ValueError):
        raise PaperTradingError("MARKET_TRUTH_INVALID") from None
    return int(parsed.timestamp() * 1_000_000_000)


def _levels(value: object, *, reverse: bool) -> tuple[tuple[str, str], ...]:
    if not isinstance(value, list):
        raise PaperTradingError("MARKET_TRUTH_INVALID")
    result = []
    for item in value:
        if not isinstance(item, dict) or set(item) != {"price", "size"}:
            raise PaperTradingError("MARKET_TRUTH_INVALID")
        result.append(
            (
                decimal_text(Decimal(item["price"])),
                decimal_text(Decimal(item["size"])),
            )
        )
    return tuple(
        sorted(
            result,
            key=lambda level: Decimal(level[0]),
            reverse=reverse,
        )
    )


def run_replay(
    engine: PaperEngine,
    *,
    market_events: Sequence[PaperMarketEvent],
    intents: Sequence[PaperIntent],
    finish_time_ns: int | None = None,
) -> None:
    """Run deterministic receive-time replay; market truth wins equal-time ties."""
    actions = [
        (event.receive_time_ns, 0, index, event)
        for index, event in enumerate(market_events)
    ] + [
        (intent.decision_time_ns, 1, index, intent)
        for index, intent in enumerate(intents)
    ]
    if actions != sorted(actions, key=lambda item: item[:3]):
        actions.sort(key=lambda item: item[:3])
    for _time_value, kind, _index, value in actions:
        if kind == 0:
            engine.process_market_event(value)
        else:
            engine.submit(value)
    if finish_time_ns is not None:
        engine.advance_time(finish_time_ns)


def run_wp172_replay(
    engine: PaperEngine,
    *,
    market_truth: MarketTruthWindow,
    decision_trace: ResearchDecisionTrace,
) -> None:
    """Validate and replay the exact WP172 window/decision trace bound to the session."""
    try:
        validate_market_truth_window(market_truth)
        validate_research_decision_trace(decision_trace)
    except Exception:
        raise PaperTradingError("WP172_REPLAY_INVALID") from None
    binding = engine.state.binding
    assets = {event.asset_id for event in decision_trace.events}
    markets = {event.market_id for event in decision_trace.events}
    instrument_asset = market_truth.instrument_id.removesuffix(".POLYMARKET")
    if (
        decision_trace.trace_id != binding.decision_trace_id
        or market_truth.lineage_id != binding.market_data_lineage_id
        or decision_trace.experiment_id != binding.experiment_id
        or decision_trace.first_look_evidence_id != binding.first_look_evidence_id
        or assets != {instrument_asset}
        or len(markets) != 1
    ):
        raise PaperTradingError("WP172_REPLAY_INVALID")
    market_id = next(iter(markets))
    paper_events = tuple(
        PaperMarketEvent(
            event.kind,
            market_id,
            instrument_asset,
            event.event_time_ns,
            event.receive_time_ns,
            f"{market_truth.lineage_id}:{index}",
            event.bids,
            event.asks,
            event.side,
            event.price,
            event.size,
        )
        for index, event in enumerate(market_truth.events)
    )
    intents = tuple(
        build_paper_intent(
            binding,
            market_id=event.market_id,
            asset_id=event.asset_id,
            side=event.side,
            quantity=event.intended_quantity,
            order_style=binding.execution_mode,
            reference_price=event.decision_reference_price,
            decision_time_ns=event.decision_time_ns,
        )
        for event in decision_trace.events
    )
    run_replay(
        engine,
        market_events=paper_events,
        intents=intents,
        finish_time_ns=market_truth.last_receive_time_ns,
    )


class Wp169ReadOnlyTail:
    """Bounded `mode=ro` reader for accepted canonical local WP169 observations."""

    def __init__(
        self, path: str | Path, *, processed_lineages: Sequence[str] = ()
    ) -> None:
        if not isinstance(path, (str, Path)):
            raise PaperTradingError("SOURCE_UNAVAILABLE")
        candidate = Path(path)
        try:
            absolute = candidate.absolute()
            if (
                candidate.suffix != ".sqlite3"
                or candidate.is_symlink()
                or not candidate.is_file()
                or candidate.stat().st_nlink != 1
                or any(parent.is_symlink() for parent in absolute.parents)
            ):
                raise PaperTradingError("SOURCE_UNAVAILABLE")
            self.path = candidate.resolve(strict=True)
        except (OSError, RuntimeError, ValueError):
            raise PaperTradingError("SOURCE_UNAVAILABLE") from None
        self._books: dict[str, tuple[dict[str, str], dict[str, str]]] = {}
        self._markets: dict[str, str] = {}
        self._observation_sequence = 0
        self._gap_sequence = 0
        if any(not isinstance(item, str) or not item for item in processed_lineages):
            raise PaperTradingError("INPUT_INVALID")
        self._processed_lineages = frozenset(processed_lineages)
        self.bootstrap_complete = False
        self._verify()

    def _connect(self) -> sqlite3.Connection:
        try:
            connection = sqlite3.connect(self.path.as_uri() + "?mode=ro", uri=True)
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA query_only=ON")
            return connection
        except sqlite3.Error:
            raise PaperTradingError("SOURCE_UNAVAILABLE") from None

    def _verify(self) -> None:
        connection = self._connect()
        try:
            if (
                connection.execute("PRAGMA application_id").fetchone()[0]
                != MARKET_APPLICATION_ID
            ):
                raise PaperTradingError("SOURCE_UNAVAILABLE")
            if (
                connection.execute("PRAGMA user_version").fetchone()[0]
                != MARKET_USER_VERSION
            ):
                raise PaperTradingError("SOURCE_UNAVAILABLE")
            for table, expected in {
                "normalized_occurrences": _NORMALIZED_COLUMNS,
                "gap_events": _GAP_COLUMNS,
            }.items():
                actual = tuple(
                    row[1] for row in connection.execute(f"PRAGMA table_info({table})")
                )
                if actual != expected:
                    raise PaperTradingError("SOURCE_UNAVAILABLE")
        except sqlite3.Error:
            raise PaperTradingError("SOURCE_UNAVAILABLE") from None
        finally:
            connection.close()

    @staticmethod
    def _validated_payload(row: sqlite3.Row) -> dict[str, object]:
        try:
            payload = json.loads(row["canonical_payload_json"])
            errors = json.loads(row["error_codes_json"])
            provenance = json.loads(row["provenance_json"])
        except (TypeError, ValueError):
            raise PaperTradingError("MARKET_TRUTH_INVALID") from None
        payload_json = wp169_canonical_bytes(payload).decode("utf-8")
        provenance_json = wp169_canonical_bytes(provenance).decode("utf-8")
        digest = hashlib.sha256(payload_json.encode("utf-8")).hexdigest()
        source_content_id = row["raw_id"]
        if row["source_kind"] == "POLYGON":
            source_content_id = payload.get("source_log_id", source_content_id)
        expected_id = compute_observation_id(
            source_content_id=source_content_id,
            source_kind=row["source_kind"],
            event_kind=row["event_kind"],
            event_id=row["event_id"],
            market_id=row["market_id"],
            asset_id=row["asset_id"],
            event_time=row["event_time"],
            canonical_payload_sha256=row["canonical_payload_sha256"],
            status=row["status"],
            error_codes=tuple(errors),
            book_ready=bool(row["book_ready"]),
            provenance_json=row["provenance_json"],
        )
        if (
            row["status"] != "ACCEPTED"
            or errors != []
            or payload_json != row["canonical_payload_json"]
            or provenance_json != row["provenance_json"]
            or digest != row["canonical_payload_sha256"]
            or expected_id != row["observation_id"]
        ):
            raise PaperTradingError("MARKET_TRUTH_INVALID")
        return payload

    def _convert(self, row: sqlite3.Row) -> PaperMarketEvent | None:
        payload = self._validated_payload(row)
        market_id = row["market_id"]
        asset_id = row["asset_id"]
        if not isinstance(market_id, str):
            return None
        receive_ns = _time_ns(row["received_at"])
        event_ns = _time_ns(row["event_time"] or row["received_at"])
        lineage = row["observation_id"]
        if isinstance(asset_id, str):
            self._markets[asset_id] = market_id
        if (
            row["event_kind"] == "book"
            and isinstance(asset_id, str)
            and row["book_ready"]
        ):
            bids = _levels(payload.get("bids"), reverse=True)
            asks = _levels(payload.get("asks"), reverse=False)
            self._books[asset_id] = (dict(bids), dict(asks))
            return PaperMarketEvent(
                "BOOK", market_id, asset_id, event_ns, receive_ns, lineage, bids, asks
            )
        if (
            row["event_kind"] == "price_change"
            and isinstance(asset_id, str)
            and row["book_ready"]
        ):
            if asset_id not in self._books:
                raise PaperTradingError("MARKET_TRUTH_GAP")
            bids, asks = self._books[asset_id]
            side = payload.get("side")
            levels = bids if side == "BUY" else asks if side == "SELL" else None
            if levels is None:
                raise PaperTradingError("MARKET_TRUTH_INVALID")
            price = payload.get("price")
            size = payload.get("size")
            if not isinstance(price, str) or not isinstance(size, str):
                raise PaperTradingError("MARKET_TRUTH_INVALID")
            if Decimal(size) == 0:
                levels.pop(price, None)
            else:
                levels[price] = size
            ordered_bids = tuple(
                sorted(
                    bids.items(),
                    key=lambda item: Decimal(item[0]),
                    reverse=True,
                )
            )
            ordered_asks = tuple(
                sorted(
                    asks.items(),
                    key=lambda item: Decimal(item[0]),
                )
            )
            return PaperMarketEvent(
                "BOOK",
                market_id,
                asset_id,
                event_ns,
                receive_ns,
                lineage,
                ordered_bids,
                ordered_asks,
            )
        if row["event_kind"] in {
            "last_trade_price",
            "trade",
            "activity",
        } and isinstance(asset_id, str):
            side, price, size = (
                payload.get("side"),
                payload.get("price"),
                payload.get("size"),
            )
            if (
                side in {"BUY", "SELL"}
                and isinstance(price, str)
                and isinstance(size, str)
            ):
                return PaperMarketEvent(
                    "TRADE",
                    market_id,
                    asset_id,
                    event_ns,
                    receive_ns,
                    lineage,
                    side=side,
                    price=price,
                    size=size,
                )
        if row["event_kind"] == "market_resolved":
            winner = payload.get("winner")
            winner_asset = (
                winner if isinstance(winner, str) and winner == asset_id else None
            )
            return PaperMarketEvent(
                "RESOLUTION",
                market_id,
                asset_id,
                event_ns,
                receive_ns,
                lineage,
                winner_asset_id=winner_asset,
            )
        return None

    def read_new(self, *, limit: int = 1000) -> tuple[PaperMarketEvent, ...]:
        if (
            not isinstance(limit, int)
            or isinstance(limit, bool)
            or limit < 1
            or limit > 10_000
        ):
            raise PaperTradingError("INPUT_INVALID")
        self._verify()
        connection = self._connect()
        try:
            observations = connection.execute(
                "SELECT * FROM normalized_occurrences WHERE archive_sequence>? AND status='ACCEPTED' "
                "ORDER BY archive_sequence ASC LIMIT ?",
                (self._observation_sequence, limit + 1),
            ).fetchall()
            gaps = connection.execute(
                "SELECT sequence,asset_id,state,reason,received_at FROM gap_events "
                "WHERE sequence>? ORDER BY sequence ASC LIMIT ?",
                (self._gap_sequence, limit + 1),
            ).fetchall()
        except sqlite3.Error:
            raise PaperTradingError("SOURCE_UNAVAILABLE") from None
        finally:
            connection.close()
        combined = [
            (_time_ns(row["received_at"]), 0, row["archive_sequence"], row)
            for row in observations
        ] + [
            (_time_ns(row["received_at"]), 1, row["sequence"], row)
            for row in gaps
        ]
        combined.sort(key=lambda item: item[:3])
        events: list[PaperMarketEvent] = []
        for at, kind, sequence, row in combined[:limit]:
            if kind == 0:
                converted = self._convert(row)
                self._observation_sequence = sequence
            else:
                lineage = f"wp169-gap:{sequence}"
                converted = PaperMarketEvent(
                    "GAP_OPEN" if row["state"] == "OPEN" else "GAP_HEALED",
                    self._markets.get(row["asset_id"], "market:unknown"),
                    row["asset_id"], at, at, lineage,
                )
                self._gap_sequence = sequence
            if converted is not None and converted.lineage not in self._processed_lineages:
                events.append(converted)
        connection = self._connect()
        try:
            remaining_observations = connection.execute(
                "SELECT 1 FROM normalized_occurrences WHERE archive_sequence>? "
                "AND status='ACCEPTED' LIMIT 1", (self._observation_sequence,)
            ).fetchone()
            remaining_gaps = connection.execute(
                "SELECT 1 FROM gap_events WHERE sequence>? LIMIT 1", (self._gap_sequence,)
            ).fetchone()
        except sqlite3.Error:
            raise PaperTradingError("SOURCE_UNAVAILABLE") from None
        finally:
            connection.close()
        self.bootstrap_complete = remaining_observations is None and remaining_gaps is None
        return tuple(events)


@dataclass(frozen=True)
class LiveStoreRuntime:
    engine: PaperEngine
    tail: Wp169ReadOnlyTail
    poll_interval_seconds: float = 0.25

    def __post_init__(self) -> None:
        if (
            not isinstance(self.poll_interval_seconds, (int, float))
            or not 0.01 <= self.poll_interval_seconds <= 60
        ):
            raise PaperTradingError("INPUT_INVALID")

    def poll_once(self, *, limit: int = 1000) -> int:
        events = self.tail.read_new(limit=limit)
        for event in events:
            self.engine.process_market_event(event)
        if self.tail.bootstrap_complete:
            self.engine.advance_time(time.time_ns())
        return len(events)

    def run_foreground(self, *, max_polls: int | None = None) -> None:
        if max_polls is not None and (not isinstance(max_polls, int) or max_polls < 1):
            raise PaperTradingError("INPUT_INVALID")
        polls = 0
        while self.engine.state.control_state not in {
            "KILLED",
            "RECONCILIATION_BLOCKED",
        }:
            self.poll_once()
            polls += 1
            if max_polls is not None and polls >= max_polls:
                return
            time.sleep(self.poll_interval_seconds)
