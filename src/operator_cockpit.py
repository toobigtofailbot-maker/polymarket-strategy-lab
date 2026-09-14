"""WP171/WP173 local read-only cockpit over market, research, and paper evidence."""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re
import sqlite3
from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.data_layer.analytical_research import (
    LifecycleReceipt,
    PreregisteredExperiment,
    RunEvidenceReceipt,
    load_and_verify_experiment_registry,
)
from src.paper_trading.accounting import mark_account
from src.paper_trading.engine import (
    _replay_journal,
    state_from_mapping,
    state_to_mapping,
    valid_marks,
)
from src.paper_trading.models import (
    PAPER_APPLICATION_ID,
    PAPER_USER_VERSION,
    PaperTradingError,
    content_id,
)
from src.paper_trading.store import JournalEvent, PaperStore


MARKET_APPLICATION_ID = 1_347_242_297
MARKET_USER_VERSION = 1
DEFAULT_LIMIT = 50
MAX_LIMIT = 100
ERROR_STATUS = {
    "INVALID_INPUT": 400,
    "NOT_FOUND": 404,
    "SOURCE_UNAVAILABLE": 503,
    "INTERNAL_ERROR": 500,
}
EXPERIMENT_ID_RE = re.compile(r"^experiment:sha256:[0-9a-f]{64}$")
_ASCII_INTEGER_RE = re.compile(r"^[0-9]+$")

_MARKET_COLUMNS = {
    "normalized_occurrences": (
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
    ),
    "gap_events": ("sequence", "asset_id", "state", "reason", "received_at"),
}

_RECENT_MARKET_SQL = """SELECT observation_id,source_kind,event_kind,event_id,
market_id,asset_id,event_time,received_at,status,error_codes_json,book_ready
FROM normalized_occurrences ORDER BY archive_sequence DESC LIMIT ?"""
_MARKET_SUMMARY_SQL = """SELECT COUNT(*),
COALESCE(SUM(CASE WHEN status='ACCEPTED' THEN 1 ELSE 0 END),0),
COALESCE(SUM(CASE WHEN status='QUARANTINED' THEN 1 ELSE 0 END),0),
MAX(received_at) FROM normalized_occurrences"""
_GAP_COUNTS_SQL = """SELECT
COALESCE(SUM(CASE WHEN state='OPEN' THEN 1 ELSE 0 END),0),
COALESCE(SUM(CASE WHEN state='HEALED' THEN 1 ELSE 0 END),0)
FROM gap_events"""
_RECENT_GAPS_SQL = """SELECT sequence,asset_id,state,reason,received_at
FROM gap_events ORDER BY received_at DESC, sequence DESC LIMIT ?"""

_PAPER_COLUMNS = {
    "paper_journal": (
        "sequence",
        "event_id",
        "event_type",
        "event_time_ns",
        "payload_json",
        "previous_event_hash",
        "event_hash",
    ),
    "paper_checkpoint": (
        "singleton",
        "last_sequence",
        "last_event_hash",
        "state_json",
        "state_hash",
    ),
}


@dataclass(frozen=True)
class CockpitConfig:
    market_truth_path: Path | None
    experiment_registry_path: Path | None
    paper_store_path: Path | None = None

    def __post_init__(self) -> None:
        for value in (
            self.market_truth_path,
            self.experiment_registry_path,
            self.paper_store_path,
        ):
            if value is not None and not isinstance(value, Path):
                raise TypeError("cockpit paths must be pathlib.Path or None")


class CockpitError(Exception):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def _error_response(code: str) -> JSONResponse:
    return JSONResponse(
        status_code=ERROR_STATUS[code], content={"error": {"code": code}}
    )


def _parse_limit(value: str | None) -> int:
    if value is None:
        return DEFAULT_LIMIT
    if len(value) > 3 or not _ASCII_INTEGER_RE.fullmatch(value):
        raise CockpitError("INVALID_INPUT")
    parsed = int(value)
    if parsed < 1 or parsed > MAX_LIMIT:
        raise CockpitError("INVALID_INPUT")
    return parsed


def _request_limit(request: Request) -> int:
    pairs = list(request.query_params.multi_items())
    if any(key != "limit" for key, _value in pairs):
        raise CockpitError("INVALID_INPUT")
    values = request.query_params.getlist("limit")
    if len(values) > 1:
        raise CockpitError("INVALID_INPUT")
    return _parse_limit(values[0] if values else None)


def _validated_path(value: Path | None) -> Path:
    if value is None:
        raise CockpitError("SOURCE_UNAVAILABLE")
    try:
        absolute = value.absolute()
        if (
            value.suffix != ".sqlite3"
            or value.is_symlink()
            or not value.is_file()
            or value.stat().st_nlink != 1
            or any(parent.is_symlink() for parent in absolute.parents)
        ):
            raise CockpitError("SOURCE_UNAVAILABLE")
        return value.resolve(strict=True)
    except CockpitError:
        raise
    except (OSError, RuntimeError, ValueError):
        raise CockpitError("SOURCE_UNAVAILABLE") from None


def _open_market(path: Path | None) -> sqlite3.Connection:
    validated = _validated_path(path)
    connection: sqlite3.Connection | None = None
    try:
        connection = sqlite3.connect(validated.as_uri() + "?mode=ro", uri=True)
        connection.row_factory = sqlite3.Row
        if (
            connection.execute("PRAGMA application_id").fetchone()[0]
            != MARKET_APPLICATION_ID
        ):
            raise CockpitError("SOURCE_UNAVAILABLE")
        if (
            connection.execute("PRAGMA user_version").fetchone()[0]
            != MARKET_USER_VERSION
        ):
            raise CockpitError("SOURCE_UNAVAILABLE")
        for table, expected in _MARKET_COLUMNS.items():
            actual = tuple(
                row[1]
                for row in connection.execute(f"PRAGMA table_info({table})").fetchall()
            )
            if actual != expected:
                raise CockpitError("SOURCE_UNAVAILABLE")
        return connection
    except CockpitError:
        if connection is not None:
            connection.close()
        raise
    except (OSError, sqlite3.Error, ValueError):
        if connection is not None:
            connection.close()
        raise CockpitError("SOURCE_UNAVAILABLE") from None


def _open_paper(path: Path | None) -> sqlite3.Connection:
    validated = _validated_path(path)
    connection: sqlite3.Connection | None = None
    try:
        connection = sqlite3.connect(validated.as_uri() + "?mode=ro", uri=True)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA query_only=ON")
        if (
            connection.execute("PRAGMA application_id").fetchone()[0]
            != PAPER_APPLICATION_ID
        ):
            raise CockpitError("SOURCE_UNAVAILABLE")
        if (
            connection.execute("PRAGMA user_version").fetchone()[0]
            != PAPER_USER_VERSION
        ):
            raise CockpitError("SOURCE_UNAVAILABLE")
        if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise CockpitError("SOURCE_UNAVAILABLE")
        for table, expected in _PAPER_COLUMNS.items():
            actual = tuple(
                row[1] for row in connection.execute(f"PRAGMA table_info({table})")
            )
            if actual != expected:
                raise CockpitError("SOURCE_UNAVAILABLE")
        rows = connection.execute(
            "SELECT sequence,event_id,event_type,event_time_ns,payload_json,"
            "previous_event_hash,event_hash FROM paper_journal ORDER BY sequence"
        ).fetchall()
        previous = None
        last_state = None
        journal_events = []
        for expected_sequence, row in enumerate(rows, 1):
            if (
                row["sequence"] != expected_sequence
                or row["previous_event_hash"] != previous
            ):
                raise CockpitError("SOURCE_UNAVAILABLE")
            expected_hash = PaperStore._event_hash(
                row["sequence"],
                row["event_id"],
                row["event_type"],
                row["event_time_ns"],
                row["payload_json"],
                row["previous_event_hash"],
            )
            if expected_hash != row["event_hash"]:
                raise CockpitError("SOURCE_UNAVAILABLE")
            payload = json.loads(row["payload_json"])
            if row["event_id"] != content_id(
                "paperevent:sha256:",
                {
                    "event_type": row["event_type"],
                    "event_time_ns": row["event_time_ns"],
                    "data": payload["data"],
                },
            ):
                raise CockpitError("SOURCE_UNAVAILABLE")
            journal_events.append(
                JournalEvent(
                    row["sequence"], row["event_id"], row["event_type"],
                    row["event_time_ns"], payload["data"], payload["state_after"],
                    row["previous_event_hash"], row["event_hash"],
                )
            )
            last_state = json.dumps(
                payload["state_after"],
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
                allow_nan=False,
            )
            previous = row["event_hash"]
        checkpoint = connection.execute(
            "SELECT last_sequence,last_event_hash,state_json,state_hash "
            "FROM paper_checkpoint WHERE singleton=1"
        ).fetchone()
        if not rows or checkpoint is None:
            raise CockpitError("SOURCE_UNAVAILABLE")
        if (
            checkpoint["last_sequence"] != len(rows)
            or checkpoint["last_event_hash"] != previous
            or checkpoint["state_json"] != last_state
            or hashlib.sha256(checkpoint["state_json"].encode("utf-8")).hexdigest()
            != checkpoint["state_hash"]
        ):
            raise CockpitError("SOURCE_UNAVAILABLE")
        replayed = _replay_journal(tuple(journal_events))
        if state_to_mapping(replayed) != json.loads(checkpoint["state_json"]):
            raise CockpitError("SOURCE_UNAVAILABLE")
        return connection
    except CockpitError:
        if connection is not None:
            connection.close()
        raise
    except (OSError, sqlite3.Error, ValueError, KeyError, TypeError, PaperTradingError):
        if connection is not None:
            connection.close()
        raise CockpitError("SOURCE_UNAVAILABLE") from None


def _paper_state(path: Path | None):
    connection = _open_paper(path)
    try:
        row = connection.execute(
            "SELECT state_json FROM paper_checkpoint WHERE singleton=1"
        ).fetchone()
        return state_from_mapping(json.loads(row[0]))
    except Exception:
        raise CockpitError("SOURCE_UNAVAILABLE") from None
    finally:
        connection.close()


def _paper_summary(path: Path | None) -> dict[str, Any]:
    state = _paper_state(path)
    marked = mark_account(state.account, valid_marks(state))
    return {
        "session_id": state.session_id,
        "control_state": state.control_state,
        "reconciliation_state": "OK",
        "cash": state.account.cash,
        "free_cash": str(
            Decimal(state.account.cash) - Decimal(state.account.reserved_cash)
        ),
        "reserved_cash": state.account.reserved_cash,
        "equity": marked["equity"],
        "realized_pnl": state.account.realized_pnl,
        "unrealized_pnl": marked["unrealized_pnl"],
        "open_order_count": sum(
            order.status in {"OPEN", "PARTIALLY_FILLED"} for order in state.orders
        ),
        "fill_count": len(state.fills),
        "markout_count": len(state.markouts),
        "last_market_receive_ns": state.last_market_receive_ns,
        "simulated_paper_only": True,
    }


def _paper_orders(path: Path | None, limit: int) -> list[dict[str, Any]]:
    state = _paper_state(path)
    orders = sorted(
        state.orders,
        key=lambda item: (item.created_time_ns, item.order_id),
        reverse=True,
    )[:limit]
    return [
        {
            "order_id": item.order_id,
            "intent_id": item.intent_id,
            "market_id": item.market_id,
            "asset_id": item.asset_id,
            "side": item.side,
            "order_style": item.order_style,
            "quantity": item.quantity,
            "filled_quantity": item.filled_quantity,
            "average_fill_price": (
                str(Decimal(item.fill_notional) / Decimal(item.filled_quantity))
                if Decimal(item.filled_quantity)
                else None
            ),
            "fee_paid": item.fee_paid,
            "status": item.status,
            "created_time_ns": item.created_time_ns,
        }
        for item in orders
    ]


def _paper_fills(path: Path | None, limit: int) -> list[dict[str, Any]]:
    state = _paper_state(path)
    markouts = {item.fill_id: item for item in state.markouts}
    fills = sorted(
        state.fills, key=lambda item: (item.receive_time_ns, item.fill_id), reverse=True
    )[:limit]
    return [
        {
            "fill_id": item.fill_id,
            "order_id": item.order_id,
            "market_id": item.market_id,
            "asset_id": item.asset_id,
            "side": item.side,
            "quantity": item.quantity,
            "price": item.price,
            "fee": item.fee,
            "spread_cost": item.spread_cost,
            "depth_slippage_cost": item.depth_slippage_cost,
            "latency_cost": item.latency_cost,
            "adverse_selection_cost": (
                markouts[item.fill_id].adverse_selection_cost
                if item.fill_id in markouts
                else None
            ),
            "markout_status": (
                markouts[item.fill_id].status if item.fill_id in markouts else "PENDING"
            ),
            "receive_time_ns": item.receive_time_ns,
            "fill_kind": item.fill_kind,
        }
        for item in fills
    ]


def _paper_positions(path: Path | None, limit: int) -> list[dict[str, Any]]:
    state = _paper_state(path)
    marks = valid_marks(state)
    return [
        {
            "market_id": item.market_id,
            "asset_id": item.asset_id,
            "quantity": item.quantity,
            "cost_basis": item.cost_basis,
            "realized_pnl": item.realized_pnl,
            "mark": marks.get(item.asset_id),
            "marked_value": (
                str(Decimal(item.quantity) * Decimal(marks[item.asset_id]))
                if item.asset_id in marks
                else None
            ),
        }
        for item in state.account.positions[:limit]
    ]


def _paper_risk(path: Path | None) -> dict[str, Any]:
    state = _paper_state(path)
    active = [
        item for item in state.orders if item.status in {"OPEN", "PARTIALLY_FILLED"}
    ]
    denied = [item for item in state.risk_decisions if item.result == "DENY"]
    return {
        "limits": asdict(state.limits),
        "utilization": {
            "open_orders": len(active),
            "max_open_orders": state.limits.max_open_orders,
            "reserved_cash": state.account.reserved_cash,
            "reserved_positions": [
                list(item) for item in state.account.reserved_positions
            ],
            "daily_realized_pnl": [
                list(item) for item in state.account.daily_realized_pnl
            ],
        },
        "latest_decision": asdict(state.risk_decisions[-1])
        if state.risk_decisions
        else None,
        "deny_count": len(denied),
        "resolution_pending": list(state.resolution_pending),
    }


def _paper_audit(path: Path | None, limit: int) -> list[dict[str, Any]]:
    connection = _open_paper(path)
    try:
        rows = connection.execute(
            "SELECT sequence,event_id,event_type,event_time_ns FROM paper_journal "
            "ORDER BY sequence DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [
            {
                "source": "WP173",
                "record_id": row["event_id"],
                "kind": row["event_type"],
                "sequence": row["sequence"],
                "status": "RECORDED",
                "occurred_time_ns": row["event_time_ns"],
            }
            for row in rows
        ]
    except sqlite3.Error:
        raise CockpitError("SOURCE_UNAVAILABLE") from None
    finally:
        connection.close()


def _market_summary(path: Path | None) -> dict[str, Any]:
    connection = _open_market(path)
    try:
        total, accepted, quarantined, latest = connection.execute(
            _MARKET_SUMMARY_SQL
        ).fetchone()
        opened, healed = connection.execute(_GAP_COUNTS_SQL).fetchone()
        open_gaps = max(0, opened - healed)
        return {
            "normalized_count": total,
            "accepted_count": accepted,
            "quarantined_count": quarantined,
            "open_gap_count": open_gaps,
            "latest_received_at": latest,
        }
    except sqlite3.Error:
        raise CockpitError("SOURCE_UNAVAILABLE") from None
    finally:
        connection.close()


def _recent_market(path: Path | None, limit: int) -> list[dict[str, Any]]:
    connection = _open_market(path)
    try:
        rows = connection.execute(_RECENT_MARKET_SQL, (limit,)).fetchall()
        items = []
        for row in rows:
            try:
                error_codes = json.loads(row["error_codes_json"])
            except (json.JSONDecodeError, TypeError):
                raise CockpitError("SOURCE_UNAVAILABLE") from None
            if not isinstance(error_codes, list) or not all(
                isinstance(code, str) for code in error_codes
            ):
                raise CockpitError("SOURCE_UNAVAILABLE")
            items.append(
                {
                    "observation_id": row["observation_id"],
                    "source_kind": row["source_kind"],
                    "event_kind": row["event_kind"],
                    "event_id": row["event_id"],
                    "market_id": row["market_id"],
                    "asset_id": row["asset_id"],
                    "event_time": row["event_time"],
                    "received_at": row["received_at"],
                    "status": row["status"],
                    "error_codes": error_codes,
                    "book_ready": bool(row["book_ready"]),
                }
            )
        return items
    except CockpitError:
        raise
    except sqlite3.Error:
        raise CockpitError("SOURCE_UNAVAILABLE") from None
    finally:
        connection.close()


def _recent_gaps(path: Path | None, limit: int) -> list[dict[str, Any]]:
    connection = _open_market(path)
    try:
        return [
            {
                "source": "WP169",
                "record_id": None,
                "experiment_id": None,
                "kind": "GAP",
                "sequence": row["sequence"],
                "status": row["state"],
                "occurred_at": row["received_at"],
            }
            for row in connection.execute(_RECENT_GAPS_SQL, (limit,)).fetchall()
        ]
    except sqlite3.Error:
        raise CockpitError("SOURCE_UNAVAILABLE") from None
    finally:
        connection.close()


def _registry_entries(path: Path | None) -> tuple[Any, ...]:
    validated = _validated_path(path)
    try:
        result = load_and_verify_experiment_registry(validated)
    except Exception:
        raise CockpitError("SOURCE_UNAVAILABLE") from None
    if not result.is_valid or result.snapshot is None:
        raise CockpitError("SOURCE_UNAVAILABLE")
    return result.snapshot.entries


def _experiment_views(entries: tuple[Any, ...]) -> list[dict[str, Any]]:
    latest_lifecycle: dict[str, LifecycleReceipt] = {}
    latest_evidence: dict[str, RunEvidenceReceipt] = {}
    experiments: list[tuple[int, PreregisteredExperiment]] = []
    for entry in entries:
        record = entry.record
        if isinstance(record, PreregisteredExperiment):
            experiments.append((entry.sequence_number, record))
        elif isinstance(record, LifecycleReceipt):
            latest_lifecycle[record.experiment_id] = record
        elif isinstance(record, RunEvidenceReceipt):
            latest_evidence[record.experiment_id] = record

    views = []
    for sequence, record in sorted(experiments, key=lambda item: item[0], reverse=True):
        lifecycle = latest_lifecycle.get(record.experiment_id)
        evidence = latest_evidence.get(record.experiment_id)
        views.append(
            {
                "experiment_id": record.experiment_id,
                "experiment_family_id": record.experiment_family_id,
                "trial_number": record.trial_number,
                "hypothesis_id": record.hypothesis_id,
                "dataset_binding_id": record.dataset_binding_id,
                "split_assignment_id": record.split_assignment_id,
                "baseline_id": record.baseline_id,
                "preregistered_at": record.preregistered_at,
                "lifecycle_state": lifecycle.to_state if lifecycle else None,
                "result_status": (
                    evidence.result_status
                    if evidence
                    else lifecycle.terminal_result_status
                    if lifecycle
                    else None
                ),
                "oos_exposure_ordinal": evidence.oos_exposure_ordinal
                if evidence
                else None,
            }
        )
    return views


def _experiment_detail(entries: tuple[Any, ...], experiment_id: str) -> dict[str, Any]:
    experiment = next(
        (
            entry.record
            for entry in entries
            if isinstance(entry.record, PreregisteredExperiment)
            and entry.record.experiment_id == experiment_id
        ),
        None,
    )
    if experiment is None:
        raise CockpitError("NOT_FOUND")
    lifecycle = [
        entry.record
        for entry in entries
        if isinstance(entry.record, LifecycleReceipt)
        and entry.record.experiment_id == experiment_id
    ]
    evidence = [
        entry.record
        for entry in entries
        if isinstance(entry.record, RunEvidenceReceipt)
        and entry.record.experiment_id == experiment_id
    ]
    latest_lifecycle = lifecycle[-1] if lifecycle else None
    latest_evidence = evidence[-1] if evidence else None
    return {
        "experiment_id": experiment.experiment_id,
        "experiment_family_id": experiment.experiment_family_id,
        "trial_number": experiment.trial_number,
        "hypothesis_id": experiment.hypothesis_id,
        "dataset_binding_id": experiment.dataset_binding_id,
        "research_dataset_manifest_id": experiment.research_dataset_manifest_id,
        "feature_definition_ids": list(experiment.feature_definition_ids),
        "feature_set_id": experiment.feature_set_id,
        "label_definition_id": experiment.label_definition_id,
        "split_assignment_id": experiment.split_assignment_id,
        "primary_metric_id": experiment.primary_metric_id,
        "secondary_metric_ids": list(experiment.secondary_metric_ids),
        "baseline_id": experiment.baseline_id,
        "cost_model_reference": experiment.cost_model_reference,
        "preregistered_at": experiment.preregistered_at,
        "lifecycle_state": latest_lifecycle.to_state if latest_lifecycle else None,
        "result_status": (
            latest_evidence.result_status
            if latest_evidence
            else latest_lifecycle.terminal_result_status
            if latest_lifecycle
            else None
        ),
        "oos_exposure_ordinal": (
            latest_evidence.oos_exposure_ordinal if latest_evidence else None
        ),
        "lifecycle_receipt_ids": [item.lifecycle_receipt_id for item in lifecycle],
        "evidence_receipt_ids": [item.run_evidence_receipt_id for item in evidence],
    }


def _registry_summary(entries: tuple[Any, ...]) -> dict[str, int]:
    return {
        "experiment_count": sum(
            isinstance(entry.record, PreregisteredExperiment) for entry in entries
        ),
        "lifecycle_count": sum(
            isinstance(entry.record, LifecycleReceipt) for entry in entries
        ),
        "evidence_count": sum(
            isinstance(entry.record, RunEvidenceReceipt) for entry in entries
        ),
    }


def _registry_audit(entries: tuple[Any, ...]) -> list[dict[str, Any]]:
    items = []
    for entry in entries:
        record = entry.record
        if isinstance(record, LifecycleReceipt):
            items.append(
                {
                    "source": "WP170",
                    "record_id": record.lifecycle_receipt_id,
                    "experiment_id": record.experiment_id,
                    "kind": record.action,
                    "sequence": record.sequence_number,
                    "status": record.to_state,
                    "occurred_at": record.occurred_at,
                }
            )
        elif isinstance(record, RunEvidenceReceipt):
            items.append(
                {
                    "source": "WP170",
                    "record_id": record.run_evidence_receipt_id,
                    "experiment_id": record.experiment_id,
                    "kind": "RUN_EVIDENCE",
                    "sequence": entry.sequence_number,
                    "status": record.result_status,
                    "occurred_at": record.created_at,
                }
            )
    return items


def _audit(config: CockpitConfig, limit: int) -> list[dict[str, Any]]:
    entries = _registry_entries(config.experiment_registry_path)
    combined = _registry_audit(entries) + _recent_gaps(config.market_truth_path, limit)
    combined.sort(
        key=lambda item: (
            item["occurred_at"],
            item["source"],
            item["record_id"] or "",
            item["sequence"],
        ),
        reverse=True,
    )
    return combined[:limit]


def _readable(reader: Any, path: Path | None) -> bool:
    if path is None:
        return False
    try:
        reader(path)
        return True
    except Exception:
        return False


def create_app(config: CockpitConfig) -> FastAPI:
    """Create the import-safe, manually launched read-only cockpit application."""
    app = FastAPI(title="WP171 Operator Cockpit", version="1.0.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
        allow_methods=["GET"],
        allow_headers=["Content-Type"],
    )

    @app.exception_handler(CockpitError)
    async def cockpit_error_handler(
        _request: Request, exc: CockpitError
    ) -> JSONResponse:
        return _error_response(exc.code)

    @app.exception_handler(Exception)
    async def internal_error_handler(
        _request: Request, _exc: Exception
    ) -> JSONResponse:
        return _error_response("INTERNAL_ERROR")

    @app.get("/api/health")
    async def health() -> dict[str, Any]:
        wp169_readable = _readable(_market_summary, config.market_truth_path)
        wp170_readable = _readable(_registry_entries, config.experiment_registry_path)
        paper_readable = _readable(_paper_summary, config.paper_store_path)
        paper_ok = config.paper_store_path is None or paper_readable
        return {
            "status": "OK"
            if wp169_readable and wp170_readable and paper_ok
            else "DEGRADED",
            "read_only": True,
            "wp169": {
                "configured": config.market_truth_path is not None,
                "readable": wp169_readable,
            },
            "wp170": {
                "configured": config.experiment_registry_path is not None,
                "readable": wp170_readable,
            },
            "paper": {
                "configured": config.paper_store_path is not None,
                "readable": paper_readable,
            },
        }

    @app.get("/api/overview")
    async def overview() -> dict[str, Any]:
        market = _market_summary(config.market_truth_path)
        entries = _registry_entries(config.experiment_registry_path)
        experiments = _registry_summary(entries)
        return {
            "read_only": True,
            "market_truth": market,
            "experiments": experiments,
            "paper": (
                _paper_summary(config.paper_store_path)
                if config.paper_store_path is not None
                else None
            ),
            "recent_activity": {
                "market_truth_count": len(
                    _recent_market(config.market_truth_path, DEFAULT_LIMIT)
                ),
                "audit_count": len(_audit(config, DEFAULT_LIMIT)),
            },
        }

    @app.get("/api/market-truth/recent")
    async def market_truth_recent(request: Request) -> dict[str, Any]:
        limit = _request_limit(request)
        items = _recent_market(config.market_truth_path, limit)
        return {"items": items, "count": len(items), "limit": limit}

    @app.get("/api/experiments")
    async def experiments(request: Request) -> dict[str, Any]:
        limit = _request_limit(request)
        items = _experiment_views(_registry_entries(config.experiment_registry_path))[
            :limit
        ]
        return {"items": items, "count": len(items), "limit": limit}

    @app.get("/api/experiments/{experiment_id}")
    async def experiment_detail(experiment_id: str) -> dict[str, Any]:
        if not EXPERIMENT_ID_RE.fullmatch(experiment_id):
            raise CockpitError("INVALID_INPUT")
        item = _experiment_detail(
            _registry_entries(config.experiment_registry_path), experiment_id
        )
        return {"item": item}

    @app.get("/api/audit/recent")
    async def audit_recent(request: Request) -> dict[str, Any]:
        limit = _request_limit(request)
        items = _audit(config, limit)
        return {"items": items, "count": len(items), "limit": limit}

    @app.get("/api/paper/summary")
    async def paper_summary() -> dict[str, Any]:
        return _paper_summary(config.paper_store_path)

    @app.get("/api/paper/orders")
    async def paper_orders(request: Request) -> dict[str, Any]:
        limit = _request_limit(request)
        items = _paper_orders(config.paper_store_path, limit)
        return {"items": items, "count": len(items), "limit": limit}

    @app.get("/api/paper/fills")
    async def paper_fills(request: Request) -> dict[str, Any]:
        limit = _request_limit(request)
        items = _paper_fills(config.paper_store_path, limit)
        return {"items": items, "count": len(items), "limit": limit}

    @app.get("/api/paper/positions")
    async def paper_positions(request: Request) -> dict[str, Any]:
        limit = _request_limit(request)
        items = _paper_positions(config.paper_store_path, limit)
        return {"items": items, "count": len(items), "limit": limit}

    @app.get("/api/paper/risk")
    async def paper_risk() -> dict[str, Any]:
        return _paper_risk(config.paper_store_path)

    @app.get("/api/paper/audit")
    async def paper_audit(request: Request) -> dict[str, Any]:
        limit = _request_limit(request)
        items = _paper_audit(config.paper_store_path, limit)
        return {"items": items, "count": len(items), "limit": limit}

    return app


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the local WP171 read-only cockpit"
    )
    parser.add_argument("--market-truth-store", required=True, type=Path)
    parser.add_argument("--experiment-registry", required=True, type=Path)
    parser.add_argument("--paper-store", type=Path)
    parser.add_argument("--port", default=8000, type=int)
    args = parser.parse_args(argv)
    if args.port < 1 or args.port > 65_535:
        parser.error("--port must be between 1 and 65535")
    import uvicorn

    uvicorn.run(
        create_app(
            CockpitConfig(
                args.market_truth_store,
                args.experiment_registry,
                args.paper_store,
            )
        ),
        host="127.0.0.1",
        port=args.port,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
