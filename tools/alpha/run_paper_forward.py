"""S10-PAPER-FORWARD-01: finite offline research-paper forward decision and evidence loop.

Turns a pre-frozen research-only plan plus a time-ordered imported candidate file into native
WP173 research-paper intents, records every candidate occurrence in an append-only hash-chained
ledger, reconciles that full funnel with the unchanged native snapshot and, only for a matching
StrategyVersion, feeds the snapshot to the native PERFORMANCE_UPDATE through an offline
FakeHermesBackend.

Subcommands: ``run`` (finite run-once; rerun on the same run directory resumes), ``verify``
(cold, read-only) and ``feedback`` (optional, offline). Explicit paths only. No product,
provider or account network (a guard fails the run on any socket use), no scheduler, no
credentials, no order or live path. Every result is simulated research paper evidence with no
execution authority; nothing here is a venue return, edge, qualification or OOS claim.
"""
from __future__ import annotations

import argparse
from datetime import datetime
from decimal import Decimal, InvalidOperation
import hashlib
import json
import os
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.paper_trading import PaperEngine, PaperMarketEvent, PaperRiskLimits, PaperStore  # noqa: E402
from src.paper_trading.models import (  # noqa: E402
    PaperTradingError, build_paper_intent, build_research_strategy_binding,
)
from src.paper_trading.runtime import Wp169ReadOnlyTail  # noqa: E402
from src.research_runtime.paper_performance_bridge import (  # noqa: E402
    build_research_paper_performance_snapshot, snapshot_to_mapping,
)
from src.research_runtime.hermes_controlled_runtime import autonomous_feedback as fb  # noqa: E402
from src.research_runtime.hermes_controlled_runtime import strategy_manager as sm  # noqa: E402
from src.strategy_lifecycle import load_strategy_lifecycle_store  # noqa: E402
from tools.alpha.run_discovery_learning_proof import (  # noqa: E402
    ProofStop, _EchoDraftBackend, canonical, no_network,
)

PLAN_SCHEMA = "s10-paper-forward-plan-v1"
CANDIDATES_SCHEMA = "s10-paper-forward-candidates-v1"
REPLAY_SCHEMA = "s10-paper-forward-replay-v1"
FEEDBACK_SCHEMA = "s10-paper-forward-feedback-input-v1"
REPORT_SCHEMA = "s10-paper-forward-report-v1"
RULE = "FAIR_VALUE_EDGE_V1"
RESEARCH_POLICY = "NON_CONFIRMATORY_RESEARCH_PAPER"
LEDGER, PAPER, REPORT = "ledger.jsonl", "paper_store.sqlite3", "report.json"
NO_TRADE_CLASSES = ("ABSTAINED_NO_TRADE", "SOURCE_FUTURE", "SOURCE_STALE", "SOURCE_GAP",
                    "WRONG_SCOPE", "COST_UNKNOWN")
INTENT_CLASSES = ("ATTEMPTED_INTENT", "RECOVERED")
TERMINAL_CLASSES = NO_TRADE_CLASSES + INTENT_CLASSES + ("INTERRUPTED_OR_UNKNOWN",)
ORDER_STATUSES = ("PENDING_RISK", "OPEN", "PARTIALLY_FILLED", "REJECTED", "FILLED", "CANCELLED", "EXPIRED")
CLOSED_STATUSES = ("REJECTED", "FILLED", "CANCELLED", "EXPIRED")
SOURCE_LABELS = {"WP169": "WP169_ACCEPTED_OBSERVATION", "SYNTHETIC_TEST_ONLY": "SYNTHETIC_TEST_ONLY",
                 "IMPORTED_UNVERIFIED": "IMPORTED_UNVERIFIED_MARKET_EVENTS"}
_PLAN_KEYS = {"schema", "frozen_at_ns", "session_label", "binding", "risk_limits", "rule", "fee",
              "outcome_handling", "strategy_version_id"}
_CANDIDATE_KEYS = {"occurrence_id", "market_id", "asset_id", "fair_value", "source_time_ns", "decision_time_ns"}
_EVENT_KEYS = {"kind", "market_id", "asset_id", "event_time_ns", "receive_time_ns", "lineage", "bids", "asks",
               "side", "price", "size", "winner_asset_id"}


class ForwardStop(Exception):
    """Fail-closed stop with a stable reason code."""


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise ForwardStop(code)


def _sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _int_ns(value: object) -> bool:
    return type(value) is int and value >= 0


def _dec(value: object, code: str) -> Decimal:
    _require(type(value) is str, code)
    try:
        number = Decimal(value)
    except InvalidOperation:
        raise ForwardStop(code) from None
    _require(number.is_finite(), code)
    return number


def _reject_float(_text: str) -> None:
    raise ValueError("float")


def _load_json(path: Path, code: str, *, floats: bool = False) -> tuple[dict, bytes]:
    """Prices, sizes and money stay decimal strings; only the native usage record may carry floats."""
    try:
        raw = Path(path).read_bytes()
        value = json.loads(raw, parse_float=None if floats else _reject_float)
    except (OSError, ValueError):
        raise ForwardStop(code) from None
    _require(type(value) is dict, code)
    return value, raw


def _outside_repo(path: Path) -> Path:
    resolved = Path(path).resolve()
    _require(resolved != REPO_ROOT and REPO_ROOT not in resolved.parents, "PATH_INSIDE_REPOSITORY")
    return resolved


# ---------------------------------------------------------------- plan, candidates, market source

def load_plan(path: Path) -> tuple[dict, str, object, PaperRiskLimits]:
    plan, raw = _load_json(path, "PLAN_INVALID")
    _require(set(plan) == _PLAN_KEYS and plan["schema"] == PLAN_SCHEMA and _int_ns(plan["frozen_at_ns"])
             and type(plan["session_label"]) is str and plan["session_label"]
             and plan["outcome_handling"] == "NATIVE_SETTLEMENT_ONLY"
             and (plan["strategy_version_id"] is None or type(plan["strategy_version_id"]) is str),
             "PLAN_INVALID")
    args = plan["binding"]
    _require(type(args) is dict and args.get("reserved_evidence_policy") == RESEARCH_POLICY
             and args.get("reserved_evidence_refs") == [], "PLAN_NOT_RESEARCH_ONLY")
    rule = plan["rule"]
    _require(type(rule) is dict and set(rule) == {"name", "min_edge", "max_quantity"} and rule["name"] == RULE,
             "PLAN_INVALID")
    _require(_dec(rule["max_quantity"], "PLAN_INVALID") > 0 and _dec(rule["min_edge"], "PLAN_INVALID") >= 0,
             "PLAN_INVALID")
    _require(type(plan["fee"]) is dict and type(plan["risk_limits"]) is dict, "PLAN_INVALID")
    try:
        binding = build_research_strategy_binding(**{k: tuple(v) if type(v) is list else v for k, v in args.items()})
        limits = PaperRiskLimits(**plan["risk_limits"])
    except (TypeError, PaperTradingError):
        raise ForwardStop("PLAN_INVALID") from None
    _require(binding.research_paper_only and not binding.live_promotion_eligible and not binding.gate_c_eligible
             and Decimal(binding.real_capital_usd) == 0, "PLAN_NOT_RESEARCH_ONLY")
    return plan, _sha_bytes(raw), binding, limits


def fee_scenario(plan: dict, binding) -> str:
    """Return the fee label, or COST_UNKNOWN when the plan fee is not a proven upper bound."""
    fee = plan["fee"]
    if fee.get("basis") == "SYNTHETIC_TEST_ONLY" and set(fee) == {"basis"}:
        return "SYNTHETIC_TEST_ONLY"
    if set(fee) != {"basis", "fee_rate", "fee_exponent", "maker_rebate_bps"} \
            or fee["basis"] != "CONSERVATIVE_UPPER_BOUND_ESTIMATE":
        return "COST_UNKNOWN"
    try:
        rate, rebate = _dec(fee["fee_rate"], "X"), _dec(fee["maker_rebate_bps"], "X")
    except ForwardStop:
        return "COST_UNKNOWN"
    # rate*(p(1-p))^e <= rate*p <= p*bps/1e4 for every p in [0,1] only when e >= 1 (integer).
    if (type(fee["fee_exponent"]) is not int or fee["fee_exponent"] < 1 or rate < 0 or rebate != 0
            or Decimal(binding.maker_rebate_bps) != 0 or Decimal(binding.fee_rate_bps) < rate * 10_000):
        return "COST_UNKNOWN"
    return "ESTIMATE"


def load_candidates(path: Path, frozen_at_ns: int) -> tuple[list[dict], str]:
    value, raw = _load_json(path, "CANDIDATES_INVALID")
    rows = value.get("candidates")
    _require(set(value) == {"schema", "candidates"} and value["schema"] == CANDIDATES_SCHEMA
             and type(rows) is list, "CANDIDATES_INVALID")
    previous, first = None, {}
    for row in rows:
        _require(type(row) is dict and set(row) == _CANDIDATE_KEYS
                 and all(type(row[k]) is str and row[k] for k in ("occurrence_id", "market_id", "asset_id"))
                 and _int_ns(row["source_time_ns"]) and _int_ns(row["decision_time_ns"]), "CANDIDATES_INVALID")
        fair = _dec(row["fair_value"], "CANDIDATES_INVALID")
        _require(0 <= fair <= 1, "CANDIDATES_INVALID")
        _require(frozen_at_ns < row["source_time_ns"] and frozen_at_ns < row["decision_time_ns"],
                 "PLAN_NOT_FROZEN_BEFORE_CANDIDATES")
        _require(previous is None or row["decision_time_ns"] >= previous, "CANDIDATES_NOT_TIME_ORDERED")
        previous = row["decision_time_ns"]
        first.setdefault(row["occurrence_id"], row)
    # Native intent ids are content-derived; two occurrences on one asset at one decision time collide.
    keys = [(r["asset_id"], r["decision_time_ns"]) for r in first.values()]
    _require(len(keys) == len(set(keys)), "CANDIDATES_OCCURRENCE_COLLISION")
    return rows, _sha_bytes(raw)


def _levels(value: object) -> tuple[tuple[str, str], ...]:
    _require(type(value) is list and all(type(item) is list and len(item) == 2
                                         and all(type(x) is str for x in item) for item in value),
             "REPLAY_INVALID")
    return tuple((price, size) for price, size in value)


def load_replay(path: Path) -> tuple[list[PaperMarketEvent], str, str]:
    value, raw = _load_json(path, "REPLAY_INVALID")
    _require(set(value) == {"schema", "label", "events"} and value["schema"] == REPLAY_SCHEMA
             and value["label"] in ("SYNTHETIC_TEST_ONLY", "IMPORTED_UNVERIFIED")
             and type(value["events"]) is list, "REPLAY_INVALID")
    events, lineages, last = [], set(), None
    for item in value["events"]:
        _require(type(item) is dict and set(item) <= _EVENT_KEYS and _int_ns(item.get("receive_time_ns"))
                 and _int_ns(item.get("event_time_ns")) and item.get("lineage") not in lineages, "REPLAY_INVALID")
        _require(last is None or item["receive_time_ns"] >= last, "REPLAY_NOT_TIME_ORDERED")
        last = item["receive_time_ns"]
        lineages.add(item["lineage"])
        try:
            events.append(PaperMarketEvent(
                item.get("kind"), item.get("market_id"), item.get("asset_id"), item["event_time_ns"],
                item["receive_time_ns"], item["lineage"], _levels(item.get("bids", [])),
                _levels(item.get("asks", [])), item.get("side"), item.get("price"), item.get("size"),
                item.get("winner_asset_id")))
        except TypeError:
            raise ForwardStop("REPLAY_INVALID") from None
    return events, _sha_bytes(raw), value["label"]


def _processed_lineages(store: PaperStore) -> list[str]:
    return [event.data["lineage"] for event in store.events() if event.event_type == "MARKET_EVENT"]


def market_events(args, store: PaperStore) -> tuple[list[PaperMarketEvent], dict, set]:
    """Return unapplied source events, the source identity and every lineage the source holds."""
    done = set(_processed_lineages(store))
    if args.replay_events is not None:
        events, digest, label = load_replay(args.replay_events)
        source = dict(kind=label, sha256=digest)
    else:
        try:
            tail = Wp169ReadOnlyTail(args.market_truth_store)
            events = list(tail.read_new(limit=args.max_market_events))
        except PaperTradingError as exc:
            raise ForwardStop(f"WP169_{exc}") from None
        # A truncated read would let later decisions use a book that unread earlier events replaced.
        _require(tail.bootstrap_complete, "WP169_READ_INCOMPLETE")
        source = dict(kind="WP169", sha256=None)
    return [e for e in events if e.lineage not in done], source, {e.lineage for e in events}


_FOREIGN_TYPES = {"SESSION_INITIALIZED", "CONTROL_CHANGED"}


def _require_own_writes(entries: list[dict], store: PaperStore, lineages: set, open_rows: list[dict]) -> None:
    """After a crash, every journal event past the last recorded head must come from this run's inputs."""
    last = max(e["body"]["paper_head"]["sequence"] for e in entries if "paper_head" in e["body"])
    keys = {(r["market_id"], r["asset_id"], r["decision_time_ns"]) for r in open_rows}
    for event in store.events():
        if event.sequence <= last:
            continue
        data = event.data
        _require(event.event_type not in _FOREIGN_TYPES
                 and (event.event_type != "MARKET_EVENT" or data["lineage"] in lineages)
                 and (event.event_type != "ORDER_PENDING_RISK"
                      or (data["order"]["market_id"], data["order"]["asset_id"],
                          data["order"]["created_time_ns"]) in keys)
                 and data.get("reason") not in ("MANUAL_PAPER_CANCEL", "SESSION_KILLED"), "PAPER_STORE_FOREIGN")


# ---------------------------------------------------------------- ledger

def _entry_hash(seq: int, prev: str | None, kind: str, body: dict) -> str:
    return _sha_bytes(canonical(dict(seq=seq, prev=prev, kind=kind, body=body)))


def read_ledger(path: Path) -> list[dict]:
    try:
        lines = Path(path).read_bytes().split(b"\n")
    except OSError:
        raise ForwardStop("LEDGER_UNAVAILABLE") from None
    _require(lines[-1] == b"", "LEDGER_TAMPERED")
    entries, prev = [], None
    for seq, line in enumerate(lines[:-1]):
        try:
            entry = json.loads(line)
        except ValueError:
            raise ForwardStop("LEDGER_TAMPERED") from None
        _require(type(entry) is dict and set(entry) == {"seq", "prev", "kind", "body", "hash"}
                 and entry["seq"] == seq and entry["prev"] == prev and canonical(entry) == line
                 and entry["hash"] == _entry_hash(seq, prev, entry["kind"], entry["body"]), "LEDGER_TAMPERED")
        entries.append(entry)
        prev = entry["hash"]
    _require(bool(entries) and entries[0]["kind"] == "PLAN_FROZEN", "LEDGER_TAMPERED")
    return entries


class Ledger:
    def __init__(self, path: Path, entries: list[dict]):
        self.path, self.entries = path, entries

    def append(self, kind: str, body: dict) -> dict:
        seq = len(self.entries)
        prev = self.entries[-1]["hash"] if self.entries else None
        entry = dict(seq=seq, prev=prev, kind=kind, body=body, hash=_entry_hash(seq, prev, kind, body))
        with open(self.path, "ab") as handle:
            handle.write(canonical(entry) + b"\n")
            handle.flush()
            os.fsync(handle.fileno())
        self.entries.append(entry)
        return entry


def _head(store: PaperStore) -> dict:
    head = store.current_head()
    return dict(sequence=head.last_sequence, event_hash=head.last_event_hash)


# ---------------------------------------------------------------- decision

def _initial_status(engine: PaperEngine, order) -> str:
    decision = next(d for d in engine.state.risk_decisions if d.decision_id == order.risk_decision_id)
    return "REJECTED" if decision.result == "DENY" else "OPEN"


def _intent_body(engine: PaperEngine, order) -> dict:
    status = _initial_status(engine, order)
    return dict(intent_id=order.intent_id, order_id=order.order_id, side=order.side, quantity=order.quantity,
                reference_price=order.reference_price, risk_permitted=status != "REJECTED",
                initial_status=status, paper_head=_head(engine.store))


def _committed_order(engine: PaperEngine, row: dict):
    return next((o for o in engine.state.orders if o.asset_id == row["asset_id"]
                 and o.market_id == row["market_id"] and o.created_time_ns == row["decision_time_ns"]), None)


def decide(engine: PaperEngine, plan: dict, fee_label: str, row: dict) -> tuple[str, dict]:
    """Closed FAIR_VALUE_EDGE_V1 decision on the native book strictly before decision time."""
    state, binding = engine.state, engine.state.binding
    decision = row["decision_time_ns"]
    if fee_label == "COST_UNKNOWN":
        return "COST_UNKNOWN", dict(reason="FEE_NOT_PROVEN_UPPER_BOUND")
    if row["market_id"] not in binding.allowed_market_ids or not (
            binding.decision_time_start_ns <= decision < binding.decision_time_end_ns):
        return "WRONG_SCOPE", dict(reason="OUTSIDE_FROZEN_COHORT_OR_WINDOW")
    if row["source_time_ns"] >= decision:
        return "SOURCE_FUTURE", dict(reason="SOURCE_NOT_BEFORE_DECISION")
    if state.last_market_receive_ns is not None and state.last_market_receive_ns >= decision:
        return "SOURCE_FUTURE", dict(reason="MARKET_STATE_AFTER_DECISION")
    book = next((b for b in state.books if b.asset_id == row["asset_id"]), None)
    if book is None or row["asset_id"] in state.gapped_assets:
        return "SOURCE_GAP", dict(reason="NO_BOOK" if book is None else "GAPPED_BOOK")
    if book.market_id != row["market_id"]:
        return "WRONG_SCOPE", dict(reason="ASSET_NOT_IN_MARKET")
    age = decision - book.receive_time_ns
    if age > binding.max_data_age_ns:
        return "SOURCE_STALE", dict(reason="BOOK_OLDER_THAN_MAX_DATA_AGE", book_age_ns=age)
    fair, min_edge = Decimal(row["fair_value"]), Decimal(plan["rule"]["min_edge"])
    bps = Decimal(binding.fee_rate_bps) / 10_000
    held = next((Decimal(p.quantity) for p in state.account.positions if p.asset_id == row["asset_id"]), Decimal(0))
    free = held - Decimal(dict(state.account.reserved_positions).get(row["asset_id"], "0"))
    detail = dict(book_lineage=book.lineage, book_age_ns=age)
    taker = binding.execution_mode == "AGGRESSIVE_TAKER"
    if held <= 0:
        if not book.asks:
            return "ABSTAINED_NO_TRADE", dict(detail, reason="NO_ASK")
        ask = Decimal(book.asks[0][0])
        if fair - ask - ask * bps < min_edge:
            return "ABSTAINED_NO_TRADE", dict(detail, reason="EDGE_BELOW_MIN")
        side, quantity, price = "BUY", plan["rule"]["max_quantity"], book.asks[0][0] if taker else book.bids[0][0]
    else:
        if not book.bids or free <= 0:
            return "ABSTAINED_NO_TRADE", dict(detail, reason="NO_BID" if free > 0 else "NO_FREE_POSITION")
        bid = Decimal(book.bids[0][0])
        if bid - bid * bps - fair < min_edge:
            return "ABSTAINED_NO_TRADE", dict(detail, reason="EDGE_BELOW_MIN")
        side, quantity, price = "SELL", format(free, "f"), book.bids[0][0] if taker else book.asks[0][0]
    intent = build_paper_intent(binding, market_id=row["market_id"], asset_id=row["asset_id"], side=side,
                                quantity=quantity, order_style=binding.execution_mode, reference_price=price,
                                decision_time_ns=decision)
    order = engine.submit(intent)
    return "ATTEMPTED_INTENT", dict(detail, **_intent_body(engine, order))


# ---------------------------------------------------------------- run

def _claimed(entries: list[dict]) -> tuple[dict, set, dict]:
    started, rows, terminal = {}, set(), {}
    for entry in entries:
        body = entry["body"]
        if entry["kind"] in ("STARTED", "DUPLICATE_SUPPRESSED"):
            rows.add((body["candidates_sha256"], body["row_index"]))
        if entry["kind"] == "STARTED":
            started[body["occurrence_id"]] = body
        elif entry["kind"] == "TERMINAL":
            terminal[body["occurrence_id"]] = body
    return started, rows, terminal


def run(args) -> dict:
    run_dir = _outside_repo(args.run_dir)
    plan, plan_sha, binding, limits = load_plan(args.plan)
    rows, cand_sha = load_candidates(args.candidates, plan["frozen_at_ns"])
    fee_label = fee_scenario(plan, binding)
    ledger_path, paper_path = run_dir / LEDGER, run_dir / PAPER
    if ledger_path.exists():
        ledger = Ledger(ledger_path, read_ledger(ledger_path))
        frozen = ledger.entries[0]["body"]
        _require(frozen["plan_sha256"] == plan_sha, "PLAN_CHANGED")
        store = PaperStore(paper_path)
        engine = PaperEngine.open(store)
        _require(engine.state.control_state != "RECONCILIATION_BLOCKED"
                 and engine.state.session_id == frozen["session_id"], "PAPER_STORE_FOREIGN")
        last = ledger.entries[-1]
        # After a clean finish nobody else may have written; after a crash only our own submit may have.
        _require(last["kind"] != "RUN_FINISHED" or last["body"]["paper_head"] == _head(store), "PAPER_STORE_FOREIGN")
    else:
        _require(not paper_path.exists(), "PAPER_STORE_FOREIGN")
        run_dir.mkdir(parents=True, exist_ok=True)
        ledger = Ledger(ledger_path, [])
        store = PaperStore(paper_path, create=True)
        engine = PaperEngine.create_research(store, binding, limits, session_label=plan["session_label"],
                                             created_time_ns=plan["frozen_at_ns"])
        ledger.append("PLAN_FROZEN", dict(
            plan_sha256=plan_sha, plan=plan, binding_id=binding.binding_id, session_id=engine.state.session_id,
            plan_evidence_class="LOCAL_RUN_ORDER", fee_label=fee_label, paper_head=_head(store)))
    try:
        return _resume_and_run(args, plan, fee_label, rows, cand_sha, ledger, store, engine)
    finally:
        store.close()


def _resume_and_run(args, plan, fee_label, rows, cand_sha, ledger, store, engine) -> dict:
    events, source, lineages = market_events(args, store)
    first_source = next((e["body"]["market_source"]["kind"] for e in ledger.entries if e["kind"] == "RUN_INVOKED"),
                        source["kind"])
    _require(first_source == source["kind"], "MARKET_SOURCE_CHANGED")
    claimed = {(b["candidate"]["asset_id"], b["candidate"]["decision_time_ns"]): oid
               for oid, b in _claimed(ledger.entries)[0].items()}
    _require(all(claimed.get((r["asset_id"], r["decision_time_ns"]), r["occurrence_id"]) == r["occurrence_id"]
                 for r in rows), "CANDIDATES_OCCURRENCE_COLLISION")
    started, _rows, terminal = _claimed(ledger.entries)
    if ledger.entries[-1]["kind"] != "RUN_FINISHED":
        _require_own_writes(ledger.entries, store, lineages,
                            [b["candidate"] for oid, b in started.items() if oid not in terminal])
    ledger.append("RUN_INVOKED", dict(candidates_sha256=cand_sha, signal_label="IMPORTED_UNVERIFIED_SIGNAL",
                                      market_source=source, max_decisions=args.max_decisions))
    started, seen_rows, terminal = _claimed(ledger.entries)
    for occurrence_id, body in started.items():  # reconcile STARTED without terminal exactly once
        if occurrence_id in terminal:
            continue
        order = _committed_order(engine, body["candidate"])
        if order is None:
            ledger.append("TERMINAL", dict(occurrence_id=occurrence_id, terminal_class="INTERRUPTED_OR_UNKNOWN",
                                           reason="NO_COMMITTED_NATIVE_INTENT"))
        else:
            ledger.append("TERMINAL", dict(occurrence_id=occurrence_id, terminal_class="RECOVERED",
                                           **_intent_body(engine, order)))
    started, seen_rows, terminal = _claimed(ledger.entries)
    position, decisions = 0, 0

    def feed(before_ns: int | None) -> None:
        nonlocal position
        while position < len(events) and (before_ns is None or events[position].receive_time_ns < before_ns):
            engine.process_market_event(events[position])
            position += 1

    stopped_at = None
    for index, row in enumerate(rows):
        if (cand_sha, index) in seen_rows:
            continue
        if row["occurrence_id"] in started:
            claimed = started[row["occurrence_id"]]["candidate"]
            ledger.append("DUPLICATE_SUPPRESSED", dict(occurrence_id=row["occurrence_id"], candidates_sha256=cand_sha,
                                                       row_index=index, content_matches=claimed == row))
            continue
        if decisions >= args.max_decisions:
            stopped_at = row["decision_time_ns"]
            break
        ledger.append("STARTED", dict(occurrence_id=row["occurrence_id"], candidates_sha256=cand_sha,
                                      row_index=index, candidate=row, paper_head=_head(store)))
        started[row["occurrence_id"]] = dict(candidate=row)
        engine.check_store_head()
        feed(row["decision_time_ns"])
        klass, detail = decide(engine, plan, fee_label, row)
        ledger.append("TERMINAL", dict(occurrence_id=row["occurrence_id"], terminal_class=klass, **detail))
        decisions += 1
    feed(stopped_at)
    if args.finish_time_ns is not None:
        engine.advance_time(args.finish_time_ns)
    report = build_report(ledger.entries, store, engine)
    recorded = _claimed(ledger.entries)[1]
    ledger.append("RUN_FINISHED", dict(snapshot_id=report["snapshot_id"], paper_head=_head(store),
                                       decisions_this_run=decisions, bound_reached=stopped_at is not None,
                                       input_file_rows=len(rows),
                                       input_rows_not_reached=sum((cand_sha, i) not in recorded
                                                                  for i in range(len(rows)))))
    report["ledger_head"] = ledger.entries[-1]["hash"]
    Path(ledger.path.parent / REPORT).write_bytes(canonical(report) + b"\n")
    return report


# ---------------------------------------------------------------- report and reconciliation

def build_report(entries: list[dict], store: PaperStore, engine: PaperEngine) -> dict:
    snapshot = build_research_paper_performance_snapshot(store)
    snap = snapshot_to_mapping(snapshot)
    started, rows, terminal = _claimed(entries)
    suppressed = sum(e["kind"] == "DUPLICATE_SUPPRESSED" for e in entries)
    by_class = {k: sum(t["terminal_class"] == k for t in terminal.values()) for k in TERMINAL_CLASSES}
    intents = [t for t in terminal.values() if t["terminal_class"] in INTENT_CLASSES]
    orders = engine.state.orders
    by_status = {s: sum(o.status == s for o in orders) for s in ORDER_STATUSES}
    unfilled = [o for o in orders if o.status != "REJECTED" and Decimal(o.filled_quantity) < Decimal(o.quantity)]
    native_closed = dict(snapshot.closed_order_state_counts)
    _require(len(rows) == len(started) + suppressed
             and len(started) == len(terminal) and set(started) == set(terminal)
             and len(intents) == snapshot.intent_count == len({t["intent_id"] for t in intents})
             and {t["intent_id"] for t in intents} == {o.intent_id for o in orders}
             and sum(not t["risk_permitted"] for t in intents) == snapshot.risk_deny_count
             and sum(by_status.values()) == snapshot.order_count
             and all(by_status[s] == native_closed[s] for s in CLOSED_STATUSES), "FUNNEL_RECONCILIATION_BLOCKED")
    frozen = entries[0]["body"]
    source = next((e["body"]["market_source"]["kind"] for e in entries if e["kind"] == "RUN_INVOKED"), None)
    resolutions = [e.data for e in store.events()
                   if e.event_type == "MARKET_EVENT" and e.data["kind"] == "RESOLUTION"]
    pending = set(engine.state.resolution_pending)
    positions = [dict(market_id=p.market_id, asset_id=p.asset_id, quantity=p.quantity,
                      status="UNSETTLED_RESOLUTION_PENDING" if p.market_id in pending else "UNSETTLED_OPEN")
                 for p in engine.state.account.positions if Decimal(p.quantity) != 0]
    return dict(
        schema=REPORT_SCHEMA, snapshot_id=snapshot.snapshot_id, paper_head=_head(store),
        plan_sha256=frozen["plan_sha256"],
        labels=dict(signal="IMPORTED_UNVERIFIED_SIGNAL", market_source=SOURCE_LABELS.get(source),
                    fills="SIMULATED_PAPER_FILL", fee=frozen["fee_label"],
                    plan_evidence_class=frozen["plan_evidence_class"],
                    resolution="WP169_ACCEPTED_OBSERVATION" if source == "WP169" else "IMPORTED_UNVERIFIED_RESOLUTION"),
        funnel=dict(raw_candidate_rows=len(rows), unique_occurrences=len(started),
                    suppressed_duplicate_rows=suppressed, terminals=len(terminal), by_class=by_class,
                    native_intent_count=snapshot.intent_count, risk_denied=snapshot.risk_deny_count),
        orders_as_of=dict(cutoff_ns=snapshot.information_cutoff_ns, by_status=by_status,
                          nonterminal=["OPEN", "PARTIALLY_FILLED"], not_filled_count=len(unfilled),
                          not_filled_quantity=format(sum((Decimal(o.quantity) - Decimal(o.filled_quantity)
                                                          for o in unfilled), Decimal(0)), "f")),
        outcomes=dict(realized=snap["realized_paper_pnl"],
                      unrealized=snap["unrealized_paper_pnl"] if snap["unrealized_paper_pnl"] is not None
                      else "UNKNOWN",
                      fee_total=snap["fee_total"], resolution_pending_count=snapshot.resolution_pending_count,
                      resolutions_with_winner=sum(r["winner_asset_id"] is not None for r in resolutions),
                      resolutions_without_winner=sum(r["winner_asset_id"] is None for r in resolutions),
                      unsettled_positions=positions, all_positions_closed=not positions),
        authority=dict(research_paper_only=True, real_capital_usd="0", simulated_paper_only=True,
                       live=False, execution_authority=False, hermes_authority=False),
        claims=dict(venue_return=False, edge=False, qualification=False, oos=False, exact_venue_fee=False),
    )


def verify(args) -> dict:
    """Cold, read-only: recompute chain, plan hash, native snapshot and funnel; write nothing."""
    run_dir = Path(args.run_dir)
    plan_raw = Path(args.plan).read_bytes()
    entries = read_ledger(run_dir / LEDGER)
    frozen = entries[0]["body"]
    _require(frozen["plan_sha256"] == _sha_bytes(plan_raw), "PLAN_CHANGED")
    _require(entries[-1]["kind"] == "RUN_FINISHED", "RUN_INCOMPLETE_RESUME_REQUIRED")
    paper_path = run_dir / PAPER
    _require(paper_path.is_file(), "PAPER_STORE_FOREIGN")
    try:
        with PaperStore(paper_path) as store:
            engine = PaperEngine.open(store)
            _require(engine.state.session_id == frozen["session_id"]
                     and engine.state.control_state != "RECONCILIATION_BLOCKED", "PAPER_STORE_FOREIGN")
            journal = {e.sequence: e.event_hash for e in store.events()}
            for entry in entries:
                head = entry["body"].get("paper_head")
                _require(head is None or journal.get(head["sequence"]) == head["event_hash"], "PAPER_STORE_FOREIGN")
            report = build_report(entries, store, engine)
    except PaperTradingError as exc:
        raise ForwardStop("PAPER_STORE_FOREIGN" if "RECONCILIATION" in str(exc) else f"PAPER_{exc}") from None
    _require(report["snapshot_id"] == entries[-1]["body"]["snapshot_id"], "PAPER_STORE_ALTERED_AFTER_RUN")
    report["ledger_head"] = entries[-1]["hash"]
    return dict(status="VERIFIED", report=report)


# ---------------------------------------------------------------- feedback

def feedback(args, *, backend=None) -> dict:
    """Offline PERFORMANCE_UPDATE only for a matching lifecycle version; never changes the plan."""
    verified = verify(args)
    entries = read_ledger(Path(args.run_dir) / LEDGER)
    plan = entries[0]["body"]["plan"]
    pending = dict(status="FEEDBACK_PENDING_NO_MATCHING_LIFECYCLE", backend_calls=0,
                   snapshot_id=verified["report"]["snapshot_id"])
    if plan["strategy_version_id"] is None or args.lifecycle_store is None:
        return pending
    inputs, _raw = _load_json(args.feedback_input, "FEEDBACK_INPUT_INVALID", floats=True)
    _require(set(inputs) == {"schema", "information_cutoff", "decision_time_ns", "provider_label", "model_label",
                             "manager_clock_utc", "manager_draft", "manager_usage"}
             and inputs["schema"] == FEEDBACK_SCHEMA and type(inputs["manager_draft"]) is dict
             and "request_id" not in inputs["manager_draft"] and type(inputs["manager_usage"]) is dict
             and _int_ns(inputs["decision_time_ns"]) and type(inputs["manager_clock_utc"]) is str,
             "FEEDBACK_INPUT_INVALID")
    try:
        clock_at = datetime.fromisoformat(inputs["manager_clock_utc"].replace("Z", "+00:00"))
    except ValueError:
        raise ForwardStop("FEEDBACK_INPUT_INVALID") from None
    lifecycle = load_strategy_lifecycle_store(args.lifecycle_store)
    _require(lifecycle.is_valid, "LIFECYCLE_STORE_INVALID")
    _plan, _sha, binding, _limits = load_plan(args.plan)
    version = lifecycle.snapshot.version_by_id(plan["strategy_version_id"])
    if version is None or binding.candidate_id not in version.evidence_refs:
        return pending
    if backend is None:
        backend = _EchoDraftBackend(inputs["manager_draft"], inputs["manager_usage"])
    manager = _outside_repo(args.manager_store)
    if not manager.exists():
        sm.initialize_hermes_strategy_manager_store(manager)
    receipt = fb.run_paper_performance_update(
        paper_store_path=Path(args.run_dir) / PAPER, expected_binding=binding, lifecycle_snapshot=lifecycle.snapshot,
        strategy_version_id=plan["strategy_version_id"], information_cutoff=inputs["information_cutoff"],
        decision_time_ns=inputs["decision_time_ns"], backend=backend,
        hermes_manager_store_path=manager, provider_label=inputs["provider_label"],
        model_label=inputs["model_label"], clock=lambda: clock_at)
    return dict(status=receipt["status"], reason_code=receipt["reason_code"],
                backend_calls=getattr(backend, "call_count", 0), snapshot_id=verified["report"]["snapshot_id"],
                receipt=receipt)


# ---------------------------------------------------------------- CLI

def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    run_p = sub.add_parser("run")
    run_p.add_argument("--plan", type=Path, required=True)
    run_p.add_argument("--candidates", type=Path, required=True)
    run_p.add_argument("--run-dir", type=Path, required=True)
    run_p.add_argument("--max-decisions", type=int, required=True)
    run_p.add_argument("--max-market-events", type=int, default=1000)
    run_p.add_argument("--finish-time-ns", type=int, default=None)
    source = run_p.add_mutually_exclusive_group(required=True)
    source.add_argument("--replay-events", type=Path)
    source.add_argument("--market-truth-store", type=Path)
    for name in ("verify", "feedback"):
        p = sub.add_parser(name)
        p.add_argument("--plan", type=Path, required=True)
        p.add_argument("--run-dir", type=Path, required=True)
    fb_p = sub.choices["feedback"]
    fb_p.add_argument("--lifecycle-store", type=Path, default=None)
    fb_p.add_argument("--feedback-input", type=Path, required=True)
    fb_p.add_argument("--manager-store", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "run" and not (1 <= args.max_decisions <= 100_000):
        print(json.dumps(dict(status="REJECTED", reason_code="MAX_DECISIONS_INVALID")))
        return 2
    with no_network() as attempts:
        try:
            result = dict(run=lambda: dict(status="COMPLETED", report=run(args)), verify=lambda: verify(args),
                          feedback=lambda: feedback(args))[args.command]()
            code = 0
        except (ForwardStop, PaperTradingError, ProofStop, OSError) as exc:
            result, code = dict(status="REJECTED", reason_code=str(exc)), 1
    if attempts:
        result, code = dict(status="REJECTED", reason_code="NETWORK_ATTEMPTED"), 1
    print(json.dumps(result, sort_keys=True, default=str))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
