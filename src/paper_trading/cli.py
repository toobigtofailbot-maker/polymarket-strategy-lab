"""Thin explicit-path manual CLI for the WP173 foreground paper runtime."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys

from src.research_runtime.executable_edge import (
    ExecutionCostModel,
    deserialize_assessment,
    validate_execution_cost_model,
)

from .engine import PaperEngine
from .models import (
    PaperMarketEvent,
    PaperRiskLimits,
    PaperTradingError,
    build_paper_intent,
    build_strategy_binding,
    canonical_json_bytes,
    dataclass_from_mapping,
    validate_market_event,
)
from .runtime import LiveStoreRuntime, Wp169ReadOnlyTail, run_replay
from .store import PaperStore


def _local_bytes(path: Path, *, suffix: str) -> bytes:
    try:
        absolute = path.absolute()
        if (
            path.suffix != suffix
            or path.is_symlink()
            or not path.is_file()
            or path.stat().st_nlink != 1
            or any(parent.is_symlink() for parent in absolute.parents)
            or path.stat().st_size > 1_048_576
        ):
            raise PaperTradingError("INPUT_INVALID")
        return path.read_bytes()
    except PaperTradingError:
        raise
    except (OSError, UnicodeError, ValueError):
        raise PaperTradingError("INPUT_INVALID") from None


def _json_file(path: Path) -> object:
    try:
        value = json.loads(_local_bytes(path, suffix=".json").decode("utf-8"))
    except PaperTradingError:
        raise
    except (UnicodeError, ValueError):
        raise PaperTradingError("INPUT_INVALID") from None
    if not isinstance(value, (dict, list)):
        raise PaperTradingError("INPUT_INVALID")
    return value


def _cost_model(path: Path) -> ExecutionCostModel:
    value = _json_file(path)
    if not isinstance(value, dict):
        raise PaperTradingError("INPUT_INVALID")
    try:
        value["size_grid"] = tuple(value["size_grid"])
        model = ExecutionCostModel(**value)
        validate_execution_cost_model(model)
        return model
    except Exception:
        raise PaperTradingError("INPUT_INVALID") from None


def _limits(path: Path) -> PaperRiskLimits:
    value = _json_file(path)
    if not isinstance(value, dict):
        raise PaperTradingError("INPUT_INVALID")
    return dataclass_from_mapping(PaperRiskLimits, value)


def _open_engine(path: Path) -> tuple[PaperStore, PaperEngine]:
    store = PaperStore(path)
    return store, PaperEngine.open(store)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="WP173 simulated-paper runtime")
    sub = parser.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init")
    init.add_argument("--paper-store", required=True, type=Path)
    init.add_argument("--assessment", required=True, type=Path)
    init.add_argument("--cost-model", required=True, type=Path)
    init.add_argument("--limits", required=True, type=Path)
    init.add_argument("--strategy-label", required=True)
    init.add_argument("--event-time-ns", required=True, type=int)
    for name in ("status", "pause", "resume", "kill"):
        command = sub.add_parser(name)
        command.add_argument("--paper-store", required=True, type=Path)
        if name != "status":
            command.add_argument("--event-time-ns", required=True, type=int)
    submit = sub.add_parser("submit-intent")
    submit.add_argument("--paper-store", required=True, type=Path)
    submit.add_argument("--intent", required=True, type=Path)
    cancel = sub.add_parser("cancel")
    cancel.add_argument("--paper-store", required=True, type=Path)
    cancel.add_argument("--order-id", required=True)
    cancel.add_argument("--event-time-ns", required=True, type=int)
    run = sub.add_parser("run")
    run.add_argument("--paper-store", required=True, type=Path)
    run.add_argument("--mode", required=True, choices=("REPLAY", "LIVE_STORE"))
    run.add_argument("--input", type=Path)
    run.add_argument("--market-truth-store", type=Path)
    run.add_argument("--max-polls", type=int)
    run.add_argument("--poll-interval", type=float, default=0.25)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "init":
            assessment = deserialize_assessment(
                _local_bytes(args.assessment, suffix=".json")
            )
            cost_model = _cost_model(args.cost_model)
            binding = build_strategy_binding(
                assessment,
                cost_model,
                strategy_label=args.strategy_label,
                created_time_ns=args.event_time_ns,
            )
            with PaperStore(args.paper_store, create=True) as store:
                engine = PaperEngine.create(
                    store,
                    binding,
                    _limits(args.limits),
                    assessment=assessment,
                    cost_model=cost_model,
                    session_label=args.strategy_label,
                    created_time_ns=args.event_time_ns,
                )
                output = engine.summary()
        else:
            store, engine = _open_engine(args.paper_store)
            try:
                if args.command == "status":
                    output = engine.summary()
                elif args.command in {"pause", "resume", "kill"}:
                    getattr(engine, args.command)(args.event_time_ns)
                    output = engine.summary()
                elif args.command == "cancel":
                    output = asdict(engine.cancel(args.order_id, args.event_time_ns))
                elif args.command == "submit-intent":
                    value = _json_file(args.intent)
                    if not isinstance(value, dict):
                        raise PaperTradingError("INPUT_INVALID")
                    intent = build_paper_intent(engine.state.binding, **value)
                    output = asdict(engine.submit(intent))
                elif args.mode == "REPLAY":
                    if args.input is None or args.market_truth_store is not None:
                        raise PaperTradingError("INPUT_INVALID")
                    value = _json_file(args.input)
                    if not isinstance(value, dict) or set(value) - {
                        "events",
                        "intents",
                        "finish_time_ns",
                    }:
                        raise PaperTradingError("INPUT_INVALID")
                    events = tuple(
                        dataclass_from_mapping(PaperMarketEvent, item)
                        for item in value.get("events", [])
                    )
                    for event in events:
                        validate_market_event(event)
                    intents = tuple(
                        build_paper_intent(engine.state.binding, **item)
                        for item in value.get("intents", [])
                    )
                    run_replay(
                        engine,
                        market_events=events,
                        intents=intents,
                        finish_time_ns=value.get("finish_time_ns"),
                    )
                    output = engine.summary()
                else:
                    if args.market_truth_store is None or args.input is not None:
                        raise PaperTradingError("INPUT_INVALID")
                    LiveStoreRuntime(
                        engine,
                        Wp169ReadOnlyTail(
                            args.market_truth_store,
                            processed_lineages=tuple(
                                event.data["lineage"]
                                for event in store.events()
                                if event.event_type == "MARKET_EVENT"
                                and isinstance(event.data.get("lineage"), str)
                            ),
                        ),
                        args.poll_interval,
                    ).run_foreground(max_polls=args.max_polls)
                    output = engine.summary()
            finally:
                store.close()
        sys.stdout.buffer.write(canonical_json_bytes(output) + b"\n")
        return 0
    except PaperTradingError as exc:
        sys.stdout.buffer.write(
            canonical_json_bytes({"error": {"code": str(exc)}}) + b"\n"
        )
        return 2
    except (OSError, ValueError, TypeError):
        sys.stdout.buffer.write(
            canonical_json_bytes({"error": {"code": "INPUT_INVALID"}}) + b"\n"
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
