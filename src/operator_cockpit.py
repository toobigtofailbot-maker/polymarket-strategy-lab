"""WP171 local, read-only operator cockpit over WP169 and WP170 evidence."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
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
        "archive_sequence", "observation_id", "occurrence_id", "raw_id",
        "source_kind", "event_kind", "event_id", "market_id", "asset_id",
        "event_time", "received_at", "canonical_payload_json",
        "canonical_payload_sha256", "status", "error_codes_json",
        "book_ready", "provenance_json",
    ),
    "gap_events": ("sequence", "asset_id", "state", "reason", "received_at"),
}

_RECENT_MARKET_SQL = """SELECT observation_id,source_kind,event_kind,event_id,
market_id,asset_id,event_time,received_at,status,error_codes_json,book_ready
FROM normalized_occurrences ORDER BY archive_sequence DESC LIMIT ?"""
_MARKET_SUMMARY_SQL = """SELECT COUNT(*),
COALESCE(SUM(CASE WHEN status='ACCEPTED' THEN 1 ELSE 0 END),0),
COALESCE(SUM(CASE WHEN status!='ACCEPTED' THEN 1 ELSE 0 END),0),
MAX(received_at) FROM normalized_occurrences"""
_GAP_COUNTS_SQL = """SELECT
COALESCE(SUM(CASE WHEN state='OPEN' THEN 1 ELSE 0 END),0),
COALESCE(SUM(CASE WHEN state='HEALED' THEN 1 ELSE 0 END),0)
FROM gap_events"""
_RECENT_GAPS_SQL = """SELECT sequence,asset_id,state,reason,received_at
FROM gap_events ORDER BY received_at DESC, sequence DESC LIMIT ?"""


@dataclass(frozen=True)
class CockpitConfig:
    market_truth_path: Path | None
    experiment_registry_path: Path | None

    def __post_init__(self) -> None:
        for value in (self.market_truth_path, self.experiment_registry_path):
            if value is not None and not isinstance(value, Path):
                raise TypeError("cockpit paths must be pathlib.Path or None")


class CockpitError(Exception):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def _error_response(code: str) -> JSONResponse:
    return JSONResponse(status_code=ERROR_STATUS[code], content={"error": {"code": code}})


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
        if connection.execute("PRAGMA application_id").fetchone()[0] != MARKET_APPLICATION_ID:
            raise CockpitError("SOURCE_UNAVAILABLE")
        if connection.execute("PRAGMA user_version").fetchone()[0] != MARKET_USER_VERSION:
            raise CockpitError("SOURCE_UNAVAILABLE")
        for table, expected in _MARKET_COLUMNS.items():
            actual = tuple(
                row[1] for row in connection.execute(f"PRAGMA table_info({table})").fetchall()
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
            items.append({
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
            })
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
        views.append({
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
                else lifecycle.terminal_result_status if lifecycle else None
            ),
            "oos_exposure_ordinal": evidence.oos_exposure_ordinal if evidence else None,
        })
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
            else latest_lifecycle.terminal_result_status if latest_lifecycle else None
        ),
        "oos_exposure_ordinal": (
            latest_evidence.oos_exposure_ordinal if latest_evidence else None
        ),
        "lifecycle_receipt_ids": [
            item.lifecycle_receipt_id for item in lifecycle
        ],
        "evidence_receipt_ids": [
            item.run_evidence_receipt_id for item in evidence
        ],
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
            items.append({
                "source": "WP170",
                "record_id": record.lifecycle_receipt_id,
                "experiment_id": record.experiment_id,
                "kind": record.action,
                "sequence": record.sequence_number,
                "status": record.to_state,
                "occurred_at": record.occurred_at,
            })
        elif isinstance(record, RunEvidenceReceipt):
            items.append({
                "source": "WP170",
                "record_id": record.run_evidence_receipt_id,
                "experiment_id": record.experiment_id,
                "kind": "RUN_EVIDENCE",
                "sequence": entry.sequence_number,
                "status": record.result_status,
                "occurred_at": record.created_at,
            })
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
    async def cockpit_error_handler(_request: Request, exc: CockpitError) -> JSONResponse:
        return _error_response(exc.code)

    @app.exception_handler(Exception)
    async def internal_error_handler(_request: Request, _exc: Exception) -> JSONResponse:
        return _error_response("INTERNAL_ERROR")

    @app.get("/api/health")
    async def health() -> dict[str, Any]:
        wp169_readable = _readable(_market_summary, config.market_truth_path)
        wp170_readable = _readable(_registry_entries, config.experiment_registry_path)
        return {
            "status": "OK" if wp169_readable and wp170_readable else "DEGRADED",
            "read_only": True,
            "wp169": {
                "configured": config.market_truth_path is not None,
                "readable": wp169_readable,
            },
            "wp170": {
                "configured": config.experiment_registry_path is not None,
                "readable": wp170_readable,
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
            "recent_activity": {
                "market_truth_count": len(_recent_market(config.market_truth_path, DEFAULT_LIMIT)),
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
        items = _experiment_views(_registry_entries(config.experiment_registry_path))[:limit]
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

    return app


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the local WP171 read-only cockpit")
    parser.add_argument("--market-truth-store", required=True, type=Path)
    parser.add_argument("--experiment-registry", required=True, type=Path)
    parser.add_argument("--port", default=8000, type=int)
    args = parser.parse_args(argv)
    if args.port < 1 or args.port > 65_535:
        parser.error("--port must be between 1 and 65535")
    import uvicorn

    uvicorn.run(
        create_app(CockpitConfig(args.market_truth_store, args.experiment_registry)),
        host="127.0.0.1",
        port=args.port,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
