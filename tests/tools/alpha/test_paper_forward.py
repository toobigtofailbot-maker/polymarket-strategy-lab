"""S10-PAPER-FORWARD-01 R001-R010: finite offline research-paper forward loop over native WP173.

Every market, price, resolution, candidate and lifecycle record here is invented
(SYNTHETIC_TEST_ONLY); nothing touches a network, provider, account or live path.
"""
from __future__ import annotations

import ast
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import socket
import subprocess
import sys

import pytest

import tools.alpha.run_paper_forward as forward
from src.data_layer.polymarket import market_truth as mt
from src.data_layer.polymarket.market_truth_store import MarketTruthStore
from src.paper_trading import PaperEngine, PaperMarketEvent, PaperStore
from src.strategy_lifecycle import (
    append_strategy_lifecycle_record, build_strategy_family, build_strategy_version,
    initialize_strategy_lifecycle_store,
)
from tests.data_layer.polymarket.test_market_truth_models_store import CONDITION, _book_raw
from tests.exploratory_gate_c import test_exploratory_gate_c as gate_c

ROOT = Path(__file__).resolve().parents[3]
TOOL = ROOT / "tools" / "alpha" / "run_paper_forward.py"
S = 1_000_000_000
T0 = 1_788_220_800 * S  # 2026-09-01T00:00:00Z synthetic origin
MAX_AGE = 3 * S
A, B, C, D, E = (f"market:fwd-{x}" for x in "abcde")
FORBIDDEN_TERMS = ("buy/sell recommendation", "trade-ready", "execution-ready", "position sizing",
                   "expected return", "profit target", "stop loss", "take profit", "copy signal",
                   "strategy signal", "paper trading candidate")


def yes(market: str) -> str:
    return market.replace("market:", "asset:") + "-yes"


def h(tag: str) -> str:
    return hashlib.sha256(f"SYNTHETIC_TEST_ONLY:{tag}".encode()).hexdigest()


def at(seconds) -> int:
    return T0 + int(Decimal(str(seconds)) * S)


def binding_args(**changes) -> dict:
    args = dict(
        candidate_id="alphacandidate:sha256:" + h("candidate"), hypothesis_family_id="family:sha256:" + h("family"),
        research_episode_id="episode:sha256:" + h("episode"), strategy_spec_id="strategyspec:sha256:" + h("spec"),
        strategy_version="paper-forward-test-v1", strategy_code_identity="code:sha256:" + h("code"),
        subject_refs=[A, B, C, D], scope_id="scope:sha256:" + h("scope"), allowed_market_ids=[A, B, C, D],
        market_data_lineage_id="lineage:sha256:" + h("lineage"), decision_time_start_ns=T0,
        decision_time_end_ns=T0 + 3600 * S, execution_mode="AGGRESSIVE_TAKER", fee_rate_bps="200",
        maker_rebate_bps="0", latency_ns=50_000_000, order_ttl_ns=None, queue_ahead_multiplier="1",
        markout_horizon_ns=0, max_data_age_ns=MAX_AGE, reserved_evidence_policy="NON_CONFIRMATORY_RESEARCH_PAPER",
        reserved_evidence_refs=[], admitted_scope_refs=[], created_time_ns=T0 - S)
    args.update(changes)
    return args


def plan(binding=None, **changes) -> dict:
    value = dict(
        schema=forward.PLAN_SCHEMA, frozen_at_ns=T0 - S, session_label="paper-forward-test",
        binding=binding or binding_args(),
        risk_limits=dict(initial_cash="100", max_single_order_notional="50", max_per_market_gross_exposure="60",
                         max_total_gross_exposure="90", max_open_orders=10, max_session_drawdown="50",
                         max_utc_day_loss="50", minimum_free_cash_reserve="0", max_market_data_age_ns=MAX_AGE,
                         max_position_quantity="100"),
        rule=dict(name=forward.RULE, min_edge="0.02", max_quantity="10"),
        fee=dict(basis="CONSERVATIVE_UPPER_BOUND_ESTIMATE", fee_rate="0.02", fee_exponent=1, maker_rebate_bps="0"),
        outcome_handling="NATIVE_SETTLEMENT_ONLY", strategy_version_id=None)
    value.update(changes)
    return value


def book(market, seconds, bid, ask, size="50", bid_size=None, asset=None) -> dict:
    receive = at(seconds)
    return dict(kind="BOOK", market_id=market, asset_id=asset or yes(market), event_time_ns=receive - 1_000_000,
                receive_time_ns=receive, lineage=f"synthetic:book:{market}:{receive}",
                bids=[[bid, bid_size or size]], asks=[[ask, size]])


def trade(market, seconds, side, price, size) -> dict:
    receive = at(seconds)
    return dict(kind="TRADE", market_id=market, asset_id=yes(market), event_time_ns=receive - 1_000_000,
                receive_time_ns=receive, lineage=f"synthetic:trade:{market}:{receive}", side=side, price=price,
                size=size)


def gap(market, seconds) -> dict:
    receive = at(seconds)
    return dict(kind="GAP_OPEN", market_id=market, asset_id=yes(market), event_time_ns=receive - 1_000_000,
                receive_time_ns=receive, lineage=f"synthetic:gap:{market}:{receive}")


def resolution(market, seconds, winner) -> dict:
    receive = at(seconds)
    return dict(kind="RESOLUTION", market_id=market, asset_id=None, event_time_ns=receive - 1_000_000,
                receive_time_ns=receive, lineage=f"synthetic:resolution:{market}:{receive}", winner_asset_id=winner)


def cand(oid, market, seconds, fair, *, lag="0.5", asset=None) -> dict:
    return dict(occurrence_id=f"occurrence:{oid}", market_id=market, asset_id=asset or yes(market),
                fair_value=fair, source_time_ns=at(seconds) - int(Decimal(lag) * S), decision_time_ns=at(seconds))


class Case:
    """One operator run directory with its explicit input files (all outside the repository)."""

    def __init__(self, tmp_path: Path, name: str, plan_value: dict):
        self.root = tmp_path / name
        self.root.mkdir()
        self.run_dir = self.root / "run"
        self.plan = self._write("plan.json", plan_value)
        self.counter = 0

    def _write(self, name: str, value: dict) -> Path:
        path = self.root / name
        path.write_bytes(json.dumps(value, indent=1).encode())
        return path

    def files(self, candidates: list, events: list, label="SYNTHETIC_TEST_ONLY") -> tuple[Path, Path]:
        self.counter += 1
        return (self._write(f"candidates-{self.counter}.json", dict(schema=forward.CANDIDATES_SCHEMA,
                                                                    candidates=candidates)),
                self._write(f"replay-{self.counter}.json", dict(schema=forward.REPLAY_SCHEMA, label=label,
                                                                events=events)))

    def argv(self, candidates, events, *extra, label="SYNTHETIC_TEST_ONLY", max_decisions="50") -> list[str]:
        cpath, rpath = self.files(candidates, events, label)
        return ["run", "--plan", str(self.plan), "--candidates", str(cpath), "--run-dir", str(self.run_dir),
                "--max-decisions", max_decisions, "--replay-events", str(rpath), *extra]

    def run(self, capsys, candidates, events, *extra, **kwargs) -> tuple[int, dict]:
        return cli(capsys, *self.argv(candidates, events, *extra, **kwargs))

    def ledger(self) -> list[dict]:
        return forward.read_ledger(self.run_dir / forward.LEDGER)

    def verify(self, capsys) -> tuple[int, dict]:
        return cli(capsys, "verify", "--plan", str(self.plan), "--run-dir", str(self.run_dir))


def cli(capsys, *argv) -> tuple[int, dict]:
    code = forward.main(list(argv))
    return code, json.loads(capsys.readouterr().out)


def terminals(ledger: list[dict]) -> dict:
    return {e["body"]["occurrence_id"]: e["body"] for e in ledger if e["kind"] == "TERMINAL"}


def kinds(ledger: list[dict]) -> list[str]:
    return [e["kind"] for e in ledger]


def assert_reconciled(report: dict) -> None:
    funnel, orders = report["funnel"], report["orders_as_of"]
    assert funnel["raw_candidate_rows"] == funnel["unique_occurrences"] + funnel["suppressed_duplicate_rows"]
    assert funnel["unique_occurrences"] == funnel["terminals"] == sum(funnel["by_class"].values())
    assert funnel["by_class"]["ATTEMPTED_INTENT"] + funnel["by_class"]["RECOVERED"] == funnel["native_intent_count"]
    assert sum(orders["by_status"].values()) == funnel["native_intent_count"]


def sha_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


# ---------------------------------------------------------------- R001

def test_frozen_plan_precedes_decisions_and_stays_research_only(tmp_path, capsys) -> None:
    case = Case(tmp_path, "r001", plan())
    events = [book(A, 9, "0.40", "0.42"), book(A, 10.1, "0.40", "0.42")]
    code, out = case.run(capsys, [cand("a1", A, 10, "0.60")], events)
    assert code == 0 and out["status"] == "COMPLETED"
    ledger = case.ledger()
    assert kinds(ledger)[:3] == ["PLAN_FROZEN", "RUN_INVOKED", "STARTED"]
    frozen = ledger[0]["body"]
    assert frozen["plan_sha256"] == sha_file(case.plan)
    assert frozen["plan_evidence_class"] == "LOCAL_RUN_ORDER"
    assert out["report"]["labels"]["plan_evidence_class"] == "LOCAL_RUN_ORDER"
    with PaperStore(case.run_dir / forward.PAPER) as store:
        binding = PaperEngine.open(store).state.binding
    assert binding.research_paper_only and not binding.live_promotion_eligible and not binding.gate_c_eligible
    assert Decimal(binding.real_capital_usd) == 0
    assert binding.reserved_evidence_policy == "NON_CONFIRMATORY_RESEARCH_PAPER"

    # A changed plan on rerun fails closed without touching the ledger.
    before = sha_file(case.run_dir / forward.LEDGER)
    case.plan.write_bytes(json.dumps(plan(session_label="other")).encode())
    code, out = case.run(capsys, [cand("a1", A, 10, "0.60")], events)
    assert (code, out["reason_code"]) == (1, "PLAN_CHANGED")
    assert sha_file(case.run_dir / forward.LEDGER) == before

    # A plan frozen at/after a candidate time, or with reserved/OOS refs, never starts a run.
    for name, value, reason in (
            ("late", plan(frozen_at_ns=at(10)), "PLAN_NOT_FROZEN_BEFORE_CANDIDATES"),
            ("reserved", plan(binding_args(reserved_evidence_refs=["oos:sha256:" + h("oos")])),
             "PLAN_NOT_RESEARCH_ONLY"),
            ("policy", plan(binding_args(reserved_evidence_policy="CONFIRMATORY")), "PLAN_NOT_RESEARCH_ONLY")):
        other = Case(tmp_path, f"r001-{name}", value)
        code, out = other.run(capsys, [cand("a1", A, 10, "0.60")], events)
        assert (code, out["reason_code"]) == (1, reason)
        assert not other.run_dir.exists()


# ---------------------------------------------------------------- R002

def test_decision_uses_only_prior_fresh_book_for_exact_asset(tmp_path, capsys) -> None:
    case = Case(tmp_path, "r002", plan())
    events = [book(B, 1, "0.40", "0.42"), book(C, 11, "0.40", "0.42"), gap(C, 12),
              book(A, 18, "0.40", "0.60"), book(A, 20, "0.40", "0.42"),  # second A book is equal-time
              book(A, 24, "0.40", "0.42"), book(A, 26, "0.40", "0.42"), book(B, 59, "0.40", "0.42")]
    rows = [cand("future", A, 15, "0.90", lag="0"),
            cand("equal-time", A, 20, "0.55"),
            cand("stale", B, 20.5, "0.90"),
            cand("gapped", C, 21, "0.90"),
            cand("no-book", D, 21, "0.90"),
            cand("wrong-token", A, 22, "0.90", asset=yes(B)),
            cand("wrong-cohort", E, 22, "0.90"),
            cand("buy", A, 25, "0.60"),
            cand("stale-held", A, 60, "0.10")]
    code, out = case.run(capsys, rows, events)
    assert code == 0
    got = terminals(case.ledger())
    classes = {k.split(":")[1]: v["terminal_class"] for k, v in got.items()}
    assert classes == {"future": "SOURCE_FUTURE", "equal-time": "ABSTAINED_NO_TRADE", "stale": "SOURCE_STALE",
                       "gapped": "SOURCE_GAP", "no-book": "SOURCE_GAP", "wrong-token": "WRONG_SCOPE",
                       "wrong-cohort": "WRONG_SCOPE", "buy": "ATTEMPTED_INTENT", "stale-held": "SOURCE_STALE"}
    # The equal-time book (receive == decision) is processed only after the decision.
    assert got["occurrence:equal-time"]["book_lineage"] == f"synthetic:book:{A}:{at(18)}"
    assert got["occurrence:gapped"]["reason"] == "GAPPED_BOOK"
    assert got["occurrence:no-book"]["reason"] == "NO_BOOK"
    assert got["occurrence:wrong-token"]["reason"] == "ASSET_NOT_IN_MARKET"
    # Held asset A is stale (34 s) although the feed is fresh (B at 59 s): no SELL is attempted.
    assert got["occurrence:stale-held"]["book_age_ns"] == at(60) - at(26)
    report = out["report"]
    assert report["funnel"]["native_intent_count"] == 1
    assert report["orders_as_of"]["by_status"]["FILLED"] == 1
    assert_reconciled(report)


# ---------------------------------------------------------------- R003

def test_fee_bound_and_unknown_cost(tmp_path, capsys) -> None:
    _plan, _sha, binding, _limits = forward.load_plan(Case(tmp_path, "r003-load", plan()).plan)
    good = dict(basis="CONSERVATIVE_UPPER_BOUND_ESTIMATE", fee_rate="0.02", fee_exponent=1, maker_rebate_bps="0")
    assert forward.fee_scenario(dict(fee=good), binding) == "ESTIMATE"
    assert forward.fee_scenario(dict(fee=dict(basis="SYNTHETIC_TEST_ONLY")), binding) == "SYNTHETIC_TEST_ONLY"
    for bad in (dict(good, fee_exponent=0), dict(good, fee_exponent="1"), dict(good, fee_exponent=True),
                dict(good, fee_rate="0.021"), dict(good, maker_rebate_bps="1"), dict(good, basis="EXACT_VENUE"),
                {k: v for k, v in good.items() if k != "fee_rate"}, dict(good, fee_rate="NaN"), {}):
        assert forward.fee_scenario(dict(fee=bad), binding) == "COST_UNKNOWN", bad
    # The bound: rate*(p(1-p))^e <= p*rate for integer e >= 1 on the whole price grid; e = 0 breaks it.
    rate = Decimal("0.02")
    grid = [Decimal(i) / 100 for i in range(101)]
    assert all(rate * (p * (1 - p)) ** e <= p * rate for p in grid for e in (1, 2, 3))
    assert rate * (Decimal("0.01") * Decimal("0.99")) ** 0 > Decimal("0.01") * rate

    events = [book(A, 9, "0.40", "0.50"), book(B, 9, "0.40", "0.50"),
              book(A, 10.1, "0.40", "0.50"), book(B, 10.1, "0.40", "0.50")]
    rows = [cand("edge-at-min", A, 10, "0.53"), cand("edge-below-min", B, 10, "0.5299")]
    case = Case(tmp_path, "r003", plan())
    code, out = case.run(capsys, rows, events)
    got = terminals(case.ledger())
    # 0.53 - 0.50 - 0.50*200/1e4 = 0.02 == min_edge; one ten-thousandth less abstains.
    assert got["occurrence:edge-at-min"]["terminal_class"] == "ATTEMPTED_INTENT"
    assert got["occurrence:edge-below-min"]["reason"] == "EDGE_BELOW_MIN"
    assert out["report"]["labels"]["fee"] == "ESTIMATE"

    unknown = Case(tmp_path, "r003-unknown", plan(fee=dict(good, fee_exponent=0)))
    code, out = unknown.run(capsys, rows, events)
    assert code == 0
    assert {t["terminal_class"] for t in terminals(unknown.ledger()).values()} == {"COST_UNKNOWN"}
    assert out["report"]["funnel"]["native_intent_count"] == 0
    assert out["report"]["labels"]["fee"] == "COST_UNKNOWN"


# ---------------------------------------------------------------- R004

def test_full_funnel_counts_reconcile_with_native_snapshot(tmp_path, capsys) -> None:
    case = Case(tmp_path, "r004", plan())
    events = [book(A, 9, "0.40", "0.42"), book(B, 9, "0.40", "0.42"), resolution(C, 9.5, None),
              book(C, 9.6, "0.40", "0.42"), book(A, 10.1, "0.40", "0.42")]
    rows = [cand("a1", A, 10, "0.60"), cand("b1", B, 10, "0.60"), cand("c1", C, 10, "0.60"),
            cand("a1", A, 10, "0.60"), dict(cand("b1", B, 10, "0.60"), fair_value="0.70"),
            cand("n1", A, 10.5, "0.45")]
    code, out = case.run(capsys, rows, events)
    assert code == 0
    report = out["report"]
    assert report["funnel"] == dict(raw_candidate_rows=6, unique_occurrences=4, suppressed_duplicate_rows=2,
                                    terminals=4, native_intent_count=3, risk_denied=1,
                                    by_class=dict({k: 0 for k in forward.TERMINAL_CLASSES},
                                                  ATTEMPTED_INTENT=3, ABSTAINED_NO_TRADE=1))
    suppressed = [e["body"] for e in case.ledger() if e["kind"] == "DUPLICATE_SUPPRESSED"]
    assert [s["content_matches"] for s in suppressed] == [True, False]
    got = terminals(case.ledger())
    assert {k: (v["initial_status"], v["risk_permitted"]) for k, v in got.items() if "intent_id" in v} == {
        "occurrence:a1": ("OPEN", True), "occurrence:b1": ("OPEN", True), "occurrence:c1": ("REJECTED", False)}
    # Accepted B order is still OPEN as of the cutoff: a nonterminal observation, never NOT_FILLED terminal.
    orders = report["orders_as_of"]
    assert {k: v for k, v in orders["by_status"].items() if v} == {"FILLED": 1, "OPEN": 1, "REJECTED": 1}
    assert orders["not_filled_count"] == 1 and "NOT_FILLED" not in json.dumps(case.ledger())
    assert_reconciled(report)

    # Same file again: no new STARTED or suppression; a later B book fills B without rewriting terminals.
    lines = (case.run_dir / forward.LEDGER).read_bytes().splitlines()
    code, out = case.run(capsys, rows, events + [book(B, 12, "0.40", "0.42")])
    assert code == 0
    after = case.ledger()
    assert (case.run_dir / forward.LEDGER).read_bytes().splitlines()[:len(lines)] == lines
    assert kinds(after).count("STARTED") == 4 and kinds(after).count("DUPLICATE_SUPPRESSED") == 2
    assert {k: v for k, v in out["report"]["orders_as_of"]["by_status"].items() if v} == {"FILLED": 2, "REJECTED": 1}
    assert_reconciled(out["report"])

    # PASSIVE_MAKER: PARTIALLY_FILLED as of the cutoff, later FILLED (one run) or EXPIRED (another).
    passive = plan(binding_args(execution_mode="PASSIVE_MAKER", order_ttl_ns=10 * S, fee_rate_bps="0"),
                   fee=dict(basis="SYNTHETIC_TEST_ONLY"))
    # Native maker fills use the last book at/before arrival, so no book is posted after arrival here.
    base = [book(A, 9, "0.49", "0.51", bid_size="2"), trade(A, 10.2, "SELL", "0.49", "5")]
    for name, tail, extra, final in (("fill", [trade(A, 11, "SELL", "0.49", "7")], (), "FILLED"),
                                     ("expire", [], ("--finish-time-ns", str(at(30))), "EXPIRED")):
        pcase = Case(tmp_path, f"r004-{name}", passive)
        code, out = pcase.run(capsys, [cand("p1", A, 10, "0.60")], base)
        assert code == 0
        first = pcase.ledger()
        assert out["report"]["orders_as_of"]["by_status"]["PARTIALLY_FILLED"] == 1
        assert out["report"]["orders_as_of"]["not_filled_quantity"] == "7"
        assert terminals(first)["occurrence:p1"]["initial_status"] == "OPEN"
        code, out = pcase.run(capsys, [cand("p1", A, 10, "0.60")], base + tail, *extra)
        assert code == 0
        assert out["report"]["orders_as_of"]["by_status"][final] == 1
        assert [e for e in pcase.ledger() if e["kind"] == "TERMINAL"] == [e for e in first if e["kind"] == "TERMINAL"]
        assert_reconciled(out["report"])


# ---------------------------------------------------------------- R005

def _three(case):
    events = [book(m, 9, "0.40", "0.42") for m in (A, B, C)] + [book(m, 10.1, "0.40", "0.42") for m in (A, B, C)]
    return [cand("a1", A, 10, "0.60"), cand("b1", B, 10, "0.60"), cand("c1", C, 10, "0.60")], events


def test_started_first_restart_duplicate_and_interrupted(tmp_path, capsys, monkeypatch) -> None:
    case = Case(tmp_path, "r005", plan())
    rows, events = _three(case)
    original_submit, original_decide = PaperEngine.submit, forward.decide
    seen = []

    def checked_submit(self, intent):  # STARTED for this exact occurrence is durable before any submit
        last = forward.read_ledger(case.run_dir / forward.LEDGER)[-1]
        assert last["kind"] == "STARTED" and last["body"]["candidate"]["asset_id"] == intent.asset_id
        seen.append(intent.asset_id)
        return original_submit(self, intent)

    def crash_before_b(engine, plan_value, fee_label, row):
        if row["occurrence_id"] == "occurrence:b1":
            raise RuntimeError("SIMULATED_CRASH_BEFORE_SUBMIT")
        return original_decide(engine, plan_value, fee_label, row)

    monkeypatch.setattr(PaperEngine, "submit", checked_submit)
    monkeypatch.setattr(forward, "decide", crash_before_b)
    with pytest.raises(RuntimeError):
        forward.run(forward._parser().parse_args(case.argv(rows, events)))
    assert seen == [yes(A)] and kinds(case.ledger())[-1] == "STARTED"

    def crash_after_c(self, intent):
        order = original_submit(self, intent)
        if intent.asset_id == yes(C):
            raise RuntimeError("SIMULATED_CRASH_AFTER_SUBMIT")
        return order

    monkeypatch.setattr(forward, "decide", original_decide)
    monkeypatch.setattr(PaperEngine, "submit", crash_after_c)
    with pytest.raises(RuntimeError):
        forward.run(forward._parser().parse_args(case.argv(rows, events)))
    monkeypatch.setattr(PaperEngine, "submit", original_submit)

    code, out = case.run(capsys, rows, events)
    assert code == 0
    got = terminals(case.ledger())
    assert got["occurrence:b1"]["terminal_class"] == "INTERRUPTED_OR_UNKNOWN"
    assert got["occurrence:c1"]["terminal_class"] == "RECOVERED"
    with PaperStore(case.run_dir / forward.PAPER) as store:
        orders = PaperEngine.open(store).state.orders
    assert got["occurrence:c1"]["intent_id"] == next(o.intent_id for o in orders if o.asset_id == yes(C))
    assert {o.asset_id for o in orders} == {yes(A), yes(C)}  # b1 never retried, c1 never resubmitted
    assert kinds(case.ledger()).count("STARTED") == 3
    assert out["report"]["funnel"]["native_intent_count"] == 2
    assert_reconciled(out["report"])

    # Duplicate rows after restart (a new file repeating old rows) are suppressed, never rebooked.
    code, out = case.run(capsys, rows + [cand("a1", A, 10, "0.60"), cand("d1", D, 13, "0.60")],
                         events + [book(D, 12, "0.40", "0.42"), book(D, 13.1, "0.40", "0.42")])
    assert code == 0
    funnel = out["report"]["funnel"]
    assert (funnel["raw_candidate_rows"], funnel["unique_occurrences"], funnel["suppressed_duplicate_rows"]) == (8, 4, 4)
    assert_reconciled(out["report"])

    # A new occurrence reusing a claimed (asset, decision time) fails closed before any ledger write.
    before = sha_file(case.run_dir / forward.LEDGER)
    code, out = case.run(capsys, [cand("other", A, 10, "0.60")], events)
    assert (code, out["reason_code"]) == (1, "CANDIDATES_OCCURRENCE_COLLISION")
    assert sha_file(case.run_dir / forward.LEDGER) == before

    # A foreign writer between runs fails the resume closed.
    with PaperStore(case.run_dir / forward.PAPER) as store:
        PaperEngine.open(store).process_market_event(PaperMarketEvent(
            "BOOK", D, yes(D), at(20), at(20), "foreign:book", (("0.40", "1"),), (("0.42", "1"),)))
    code, out = case.run(capsys, rows, events)
    assert (code, out["reason_code"]) == (1, "PAPER_STORE_FOREIGN")

    # A foreign market event written after a crash, before resume, fails the resume closed.
    crashed = Case(tmp_path, "r005-crash-foreign", plan())
    monkeypatch.setattr(forward, "decide", crash_before_b)
    with pytest.raises(RuntimeError):
        forward.run(forward._parser().parse_args(crashed.argv(rows, events)))
    monkeypatch.setattr(forward, "decide", original_decide)
    with PaperStore(crashed.run_dir / forward.PAPER) as store:
        PaperEngine.open(store).process_market_event(PaperMarketEvent(
            "BOOK", B, yes(B), at(9.5), at(9.5), "foreign:after-crash", (("0.40", "1"),), (("0.42", "1"),)))
    code, out = crashed.run(capsys, rows, events)
    assert (code, out["reason_code"]) == (1, "PAPER_STORE_FOREIGN")

    # A foreign writer during a run trips the native stale-writer guard.
    stale = Case(tmp_path, "r005-stale", plan())

    def foreign_write(engine, plan_value, fee_label, row):
        with PaperStore(stale.run_dir / forward.PAPER) as store:
            PaperEngine.open(store).process_market_event(PaperMarketEvent(
                "BOOK", A, yes(A), at(9.5), at(9.5), "foreign:during", (("0.40", "1"),), (("0.42", "1"),)))
        return original_decide(engine, plan_value, fee_label, row)

    monkeypatch.setattr(forward, "decide", foreign_write)
    code, out = stale.run(capsys, rows[:1], events)
    assert (code, out["reason_code"]) == (1, "STALE_PAPER_STATE")


# ---------------------------------------------------------------- R006

def test_sell_settlement_and_unknown_outcome_truth(tmp_path, capsys) -> None:
    case = Case(tmp_path, "r006", plan())
    prices = {A: ("0.40", "0.42"), C: ("0.43", "0.45"), D: ("0.50", "0.52")}
    up = dict(prices, **{A: ("0.50", "0.52")})
    events = ([book(m, 9, *p) for m, p in prices.items()] + [book(m, 10.1, *p) for m, p in prices.items()]
              + [book(m, 29, *p) for m, p in up.items()] + [book(m, 30.1, *p) for m, p in up.items()]
              + [resolution(C, 40, yes(C)), resolution(D, 41, None), book(A, 100, "0.50", "0.52")])
    rows = [cand("a-buy", A, 10, "0.60"), cand("c-buy", C, 10, "0.60"), cand("d-buy", D, 10, "0.60"),
            cand("a-sell", A, 30, "0.40")]
    code, out = case.run(capsys, rows, events)
    assert code == 0
    got = terminals(case.ledger())
    assert got["occurrence:a-sell"]["side"] == "SELL" and got["occurrence:a-sell"]["quantity"] == "10"
    report, outcomes = out["report"], out["report"]["outcomes"]
    fee = lambda q, p: Decimal(q) * Decimal(p) * Decimal("200") / 10_000  # noqa: E731
    a_round_trip = 10 * (Decimal("0.50") - Decimal("0.42")) - fee(10, "0.42") - fee(10, "0.50")
    c_settlement = 10 * (1 - Decimal("0.45")) - fee(10, "0.45")
    assert Decimal(outcomes["realized"]) == a_round_trip + c_settlement == Decimal("6.026")
    # D's null winner stays pending and unsettled; its mark is stale, so unrealized is UNKNOWN, never 0.
    assert outcomes["unrealized"] == "UNKNOWN"
    assert outcomes["resolution_pending_count"] == 1
    assert outcomes["unsettled_positions"] == [dict(market_id=D, asset_id=yes(D), quantity="10",
                                                    status="UNSETTLED_RESOLUTION_PENDING")]
    assert outcomes["all_positions_closed"] is False
    assert (outcomes["resolutions_with_winner"], outcomes["resolutions_without_winner"]) == (1, 1)
    assert report["labels"]["resolution"] == "IMPORTED_UNVERIFIED_RESOLUTION"
    assert_reconciled(report)


# ---------------------------------------------------------------- R007

def _lifecycle(path: Path, candidate_id: str):
    assert initialize_strategy_lifecycle_store(path).is_valid
    family = build_strategy_family(family_key="synthetic.forward", family_label="SYNTHETIC forward",
                                   created_time_ns=1, creation_provenance="synthetic:fixture")
    versions = [build_strategy_version(
        strategy_family_id=family.strategy_family_id, parent=None, strategy_label=label,
        evidence_posture="NOVEL_EXPLORATORY", strategy_code_identity=f"synthetic:{label}",
        strategy_spec=gate_c.STRATEGY_SPEC, adaptive_bounds=gate_c.BOUNDS, evidence_refs=refs,
        created_time_ns=2, creation_provenance="synthetic:fixture")
        for label, refs in (("matching", (candidate_id,)), ("unmatched", ()))]
    for record in (family, *versions):
        assert append_strategy_lifecycle_record(path, record).is_valid
    return versions


def test_feedback_requires_matching_lifecycle_and_fake_backend(tmp_path, capsys) -> None:
    life = tmp_path / "lifecycle.sqlite3"
    matching, unmatched = _lifecycle(life, binding_args()["candidate_id"])
    draft = gate_c._draft("placeholder", gate_c.judgment())
    draft.pop("request_id")
    inputs = tmp_path / "feedback.json"
    inputs.write_bytes(json.dumps(dict(
        schema=forward.FEEDBACK_SCHEMA, information_cutoff="2026-09-01T01:00:00Z", decision_time_ns=at(600),
        provider_label="example-provider", model_label="example-model", manager_clock_utc="2026-10-01T12:00:00Z",
        manager_draft=draft, manager_usage=json.loads(gate_c._usage()))).encode())
    events = [book(A, 9, "0.40", "0.42"), book(A, 10.1, "0.40", "0.42")]

    def feedback(case, *extra):
        return cli(capsys, "feedback", "--plan", str(case.plan), "--run-dir", str(case.run_dir),
                   "--feedback-input", str(inputs), "--manager-store", str(case.root / "manager.sqlite3"), *extra)

    results = {}
    for name, version_id in (("none", None), ("unmatched", unmatched.strategy_version_id),
                             ("matching", matching.strategy_version_id)):
        case = Case(tmp_path, f"r007-{name}", plan(strategy_version_id=version_id))
        assert case.run(capsys, [cand("a1", A, 10, "0.60")], events)[0] == 0
        results[name] = case
    for name in ("none", "unmatched"):
        code, out = feedback(results[name], "--lifecycle-store", str(life))
        assert (code, out["status"], out["backend_calls"]) == (0, "FEEDBACK_PENDING_NO_MATCHING_LIFECYCLE", 0)
    case = results["matching"]
    code, out = feedback(case)  # absent lifecycle store
    assert (out["status"], out["backend_calls"]) == ("FEEDBACK_PENDING_NO_MATCHING_LIFECYCLE", 0)

    paper_before, life_before = sha_file(case.run_dir / forward.PAPER), sha_file(life)
    args = forward._parser().parse_args(["feedback", "--plan", str(case.plan), "--run-dir", str(case.run_dir),
                                         "--feedback-input", str(inputs), "--manager-store",
                                         str(case.root / "manager.sqlite3"), "--lifecycle-store", str(life)])
    bad_clock = tmp_path / "feedback-bad-clock.json"
    bad_clock.write_bytes(json.dumps(dict(json.loads(inputs.read_bytes()), manager_clock_utc="not-a-time")).encode())
    code, out = cli(capsys, "feedback", "--plan", str(case.plan), "--run-dir", str(case.run_dir), "--feedback-input",
                    str(bad_clock), "--manager-store", str(case.root / "manager.sqlite3"), "--lifecycle-store", str(life))
    assert (code, out["reason_code"]) == (1, "FEEDBACK_INPUT_INVALID")
    rejected = forward.feedback(args, backend=object())
    assert (rejected["status"], rejected["reason_code"], rejected["backend_calls"]) == (
        "REJECTED", "BACKEND_NOT_OFFLINE", 0)
    code, out = feedback(case, "--lifecycle-store", str(life))
    assert (code, out["status"], out["backend_calls"]) == (0, "ASSESSED", 1)
    assert out["receipt"]["live_pnl_claim"] is False and out["receipt"]["no_order"] is True
    assert (case.root / "manager.sqlite3").is_file()
    code, out = feedback(case, "--lifecycle-store", str(life))
    assert (out["status"], out["reason_code"], out["backend_calls"]) == ("REJECTED", "CUTOFF_NOT_ADVANCED", 0)
    assert sha_file(case.run_dir / forward.PAPER) == paper_before and sha_file(life) == life_before


# ---------------------------------------------------------------- R008

def test_cold_verify_hash_chain_and_tamper(tmp_path, capsys) -> None:
    case = Case(tmp_path, "r008", plan())
    rows, events = _three(case)
    code, run_out = case.run(capsys, rows, events)
    assert code == 0
    names = (forward.LEDGER, forward.PAPER, forward.REPORT)
    before = {n: sha_file(case.run_dir / n) for n in names}
    code, out = case.verify(capsys)
    assert (code, out["status"]) == (0, "VERIFIED") and out["report"] == run_out["report"]
    cold = subprocess.run([sys.executable, "-B", str(TOOL), "verify", "--plan", str(case.plan), "--run-dir",
                           str(case.run_dir)], cwd=ROOT, capture_output=True, check=False)
    assert cold.returncode == 0 and json.loads(cold.stdout)["report"] == run_out["report"]
    assert {n: sha_file(case.run_dir / n) for n in names} == before

    ledger_path = case.run_dir / forward.LEDGER
    good = ledger_path.read_bytes()
    lines = good.splitlines(keepends=True)
    index = next(i for i, line in enumerate(lines) if b'"TERMINAL"' in line)
    for name, data, reason in (
            ("edited", b"".join(lines[:index] + [lines[index].replace(b"ATTEMPTED_INTENT", b"ABSTAINED_NO_TRADE")]
                                + lines[index + 1:]), "LEDGER_TAMPERED"),
            ("truncated", good[:-5], "LEDGER_TAMPERED"),
            ("unfinished", b"".join(lines[:-1]), "RUN_INCOMPLETE_RESUME_REQUIRED")):
        ledger_path.write_bytes(data)
        assert case.verify(capsys)[1]["reason_code"] == reason, name
    ledger_path.write_bytes(good)

    original_plan = case.plan.read_bytes()
    case.plan.write_bytes(original_plan + b" ")
    assert case.verify(capsys)[1]["reason_code"] == "PLAN_CHANGED"
    case.plan.write_bytes(original_plan)

    paper = case.run_dir / forward.PAPER
    original_paper = paper.read_bytes()
    foreign = Case(tmp_path, "r008-foreign", plan(session_label="foreign"))
    assert foreign.run(capsys, rows, events)[0] == 0
    paper.write_bytes((foreign.run_dir / forward.PAPER).read_bytes())
    assert case.verify(capsys)[1]["reason_code"] == "PAPER_STORE_FOREIGN"
    paper.write_bytes(original_paper)
    with PaperStore(paper) as store:
        PaperEngine.open(store).process_market_event(PaperMarketEvent(
            "BOOK", A, yes(A), at(50), at(50), "foreign:after", (("0.40", "1"),), (("0.42", "1"),)))
    assert case.verify(capsys)[1]["reason_code"] == "PAPER_STORE_ALTERED_AFTER_RUN"


# ---------------------------------------------------------------- R009

def test_finite_offline_cli_no_network_no_daemon(tmp_path, capsys, monkeypatch) -> None:
    tree = ast.parse(TOOL.read_text(encoding="utf-8"))
    imported = {alias.name.split(".")[0] for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom))
                for alias in node.names} | {node.module.split(".")[0] for node in ast.walk(tree)
                                            if isinstance(node, ast.ImportFrom) and node.module}
    assert not imported & {"socket", "subprocess", "threading", "multiprocessing", "asyncio", "sched", "time",
                           "urllib", "http", "requests", "signal"}
    assert not [n for n in ast.walk(tree) if isinstance(n, ast.While) and isinstance(n.test, ast.Constant)]
    assert "sleep" not in TOOL.read_text(encoding="utf-8")

    case = Case(tmp_path, "r009", plan())
    rows, events = _three(case)
    original = forward.decide

    def socket_attempt(*args):
        try:
            socket.create_connection(("example.invalid", 443))
        except Exception:  # noqa: BLE001 - the guard must still count a swallowed attempt
            pass
        return original(*args)

    monkeypatch.setattr(forward, "decide", socket_attempt)
    code, out = case.run(capsys, rows, events)
    assert (code, out["reason_code"]) == (1, "NETWORK_ATTEMPTED")
    monkeypatch.setattr(forward, "decide", original)

    bounded = Case(tmp_path, "r009-bound", plan())
    code, out = bounded.run(capsys, rows, events, max_decisions="1")
    assert code == 0 and kinds(bounded.ledger()).count("STARTED") == 1
    assert bounded.ledger()[-1]["body"]["bound_reached"] is True
    assert bounded.ledger()[-1]["body"]["input_rows_not_reached"] == 2
    code, out = bounded.run(capsys, rows, events, max_decisions="5")
    assert code == 0 and kinds(bounded.ledger()).count("STARTED") == 3
    assert out["report"]["funnel"]["native_intent_count"] == 3
    with pytest.raises(SystemExit):
        forward._parser().parse_args(["run", "--plan", "p", "--candidates", "c", "--run-dir", "r",
                                      "--replay-events", "e"])
    inside = forward._parser().parse_args(case.argv(rows, events)[:6] + [str(ROOT / "local_data" / "x"),
                                                                         "--max-decisions", "1",
                                                                         "--replay-events", "e"])
    with pytest.raises(forward.ForwardStop, match="PATH_INSIDE_REPOSITORY"):
        forward.run(inside)

    # WP169 accepted observation through native Wp169ReadOnlyTail, in a separate finite interpreter.
    market = tmp_path / "market_truth.sqlite3"
    with MarketTruthStore(market) as source:
        raw = _book_raw()
        source.append(raw, mt.normalize_websocket_message(raw, book_readiness={}))
    received = int(datetime(2024, 7, 3, 9, 46, 40, tzinfo=timezone.utc).timestamp()) * S
    start = received - 60 * S
    wp169 = Case(tmp_path, "r009-wp169", plan(
        binding_args(subject_refs=[CONDITION], allowed_market_ids=[CONDITION], decision_time_start_ns=start,
                     decision_time_end_ns=start + 3600 * S, created_time_ns=start - S),
        frozen_at_ns=start - S))
    candidates, _replay = wp169.files([dict(occurrence_id="occurrence:wp169", market_id=CONDITION, asset_id="7",
                                            fair_value="0.90", source_time_ns=received + S // 2,
                                            decision_time_ns=received + S)], [])
    market_before = sha_file(market)
    # A WP169 read truncated by --max-market-events fails closed before any decision or STARTED.
    many = tmp_path / "market_truth_many.sqlite3"
    with MarketTruthStore(many) as source:
        for seq in (0, 1):
            raw = _book_raw(seq)
            source.append(raw, mt.normalize_websocket_message(raw, book_readiness={}))
    truncated = Case(tmp_path, "r009-truncated", json.loads(wp169.plan.read_bytes()))
    code, out = cli(capsys, "run", "--plan", str(truncated.plan), "--candidates", str(candidates), "--run-dir",
                    str(truncated.run_dir), "--max-decisions", "5", "--market-truth-store", str(many),
                    "--max-market-events", "1")
    assert (code, out["reason_code"]) == (1, "WP169_READ_INCOMPLETE")
    assert kinds(truncated.ledger()) == ["PLAN_FROZEN"]
    argv = [sys.executable, "-B", str(TOOL), "run", "--plan", str(wp169.plan), "--candidates", str(candidates),
            "--run-dir", str(wp169.run_dir), "--max-decisions", "5", "--market-truth-store", str(market)]
    for _attempt in range(2):
        done = subprocess.run(argv, cwd=ROOT, capture_output=True, check=False, timeout=120)
        assert done.returncode == 0, done.stdout + done.stderr
    report = json.loads(done.stdout)["report"]
    assert report["labels"]["market_source"] == "WP169_ACCEPTED_OBSERVATION"
    assert report["funnel"]["unique_occurrences"] == 1 and report["funnel"]["native_intent_count"] == 1
    assert report["orders_as_of"]["by_status"]["OPEN"] == 1
    assert kinds(wp169.ledger()).count("STARTED") == 1
    assert sha_file(market) == market_before


# ---------------------------------------------------------------- R010

def test_report_labels_and_no_overclaim(tmp_path, capsys) -> None:
    reports = {}
    for label in ("SYNTHETIC_TEST_ONLY", "IMPORTED_UNVERIFIED"):
        case = Case(tmp_path, f"r010-{label}", plan())
        rows, events = _three(case)
        code, out = case.run(capsys, rows, events, label=label)
        assert code == 0
        reports[label] = out["report"]
        for blob in ((case.run_dir / forward.REPORT).read_bytes(), (case.run_dir / forward.LEDGER).read_bytes()):
            assert not [t for t in FORBIDDEN_TERMS if t in blob.decode().lower()]
    synthetic, imported = reports["SYNTHETIC_TEST_ONLY"], reports["IMPORTED_UNVERIFIED"]
    assert synthetic["labels"]["market_source"] == "SYNTHETIC_TEST_ONLY"
    assert imported["labels"]["market_source"] == "IMPORTED_UNVERIFIED_MARKET_EVENTS"
    for report in reports.values():
        assert report["labels"]["signal"] == "IMPORTED_UNVERIFIED_SIGNAL"
        assert report["labels"]["fills"] == "SIMULATED_PAPER_FILL"
        assert report["labels"]["resolution"] == "IMPORTED_UNVERIFIED_RESOLUTION"
        assert report["labels"]["plan_evidence_class"] == "LOCAL_RUN_ORDER"
        assert report["labels"]["fee"] == "ESTIMATE"
        assert set(report["outcomes"]) >= {"realized", "unrealized", "resolution_pending_count"}
        assert report["claims"] == dict(venue_return=False, edge=False, qualification=False, oos=False,
                                        exact_venue_fee=False)
        assert report["authority"] == dict(research_paper_only=True, real_capital_usd="0", simulated_paper_only=True,
                                           live=False, execution_authority=False, hermes_authority=False)
