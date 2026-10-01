"""S10-QUAL-DATA-03 pure accrual module tests and negative-test matrix (offline, deterministic).

Covers the exact PLAN-01 binding, the frozen census, label-free row identity, B0 / q / L
materialization, the stable chronological prefix and seal decisions, the OOS-membership preimage
(positive and negative), MR15, the provenance ceiling, MR12 execution evidence, the hash-chained
ledger and the closed visible-report firewall.
"""

from __future__ import annotations

import ast
import hashlib
import json
from datetime import date, datetime, timedelta
from pathlib import Path

import pytest

from src.data_layer.analytical_research import pendulumflow_v3 as v3
from src.data_layer.analytical_research import qualification as qualification_module
from src.data_layer.analytical_research import qualification_data_readiness as qd
from src.data_layer.analytical_research import qualification_oos_accrual as oa

ROOT = Path(__file__).resolve().parents[3]
PLAN_BYTES = (ROOT / oa.PLAN_PATH).read_bytes()
POWER_BYTES = (ROOT / oa.POWER_DOC_PATH).read_bytes()
A, B = qd.CHECKPOINT_A, qd.CHECKPOINT_B
BUNDLE = oa.BUNDLE_ID_PREFIX + "ab" * 32


def utc(text: str) -> datetime:
    return datetime.fromisoformat(text.replace("Z", "+00:00"))


# ── PLAN-01 binding ───────────────────────────────────────────────────────────


def test_exact_plan_binding_and_freeze_event() -> None:
    assert hashlib.sha256(PLAN_BYTES).hexdigest() == oa.PLAN_SHA256
    binding = oa.verify_plan_binding(PLAN_BYTES, POWER_BYTES)
    assert binding["oos_start"] == "2026-10-15T00:00:00Z" and binding["cap"] == "2027-02-12T00:00:00Z"
    assert binding["embargo_lower_bound"] == "2026-10-17T00:00:00Z"
    assert oa.verify_plan_binding(PLAN_BYTES, POWER_BYTES.replace(b"\n", b"\r\n"))["plan_sha256"] == oa.PLAN_SHA256
    event = oa.verify_freeze_event(oa.PLAN_MERGE_SHA, oa.PLAN_MERGE_PARENTS, "GitHub", "2026-09-30T20:39:26-06:00")
    assert event == {"plan_merge_sha": oa.PLAN_MERGE_SHA, "plan_merge_time": "2026-10-01T02:39:26Z",
                     "freeze_deadline": "2026-10-14T00:00:00Z"}
    plan = json.loads(PLAN_BYTES)
    assert plan["lineage"]["historical_corpus"]["bundle_id"] == oa.DATA02_BUNDLE_ID
    assert plan["lineage"]["historical_corpus"]["logical_dataset_id"] == oa.DATA02_DATASET_ID


@pytest.mark.parametrize("mutation", [
    lambda p, w: (p + b" ", w),
    lambda p, w: (p.replace(b"2026-10-15T00:00:00Z", b"2026-10-16T00:00:00Z", 1), w),
    lambda p, w: (p, w + b"x"),
    lambda p, w: (b"", w),
])
def test_tampered_plan_or_power_doc_is_plan_freeze_invalid(mutation) -> None:
    plan, power = mutation(PLAN_BYTES, POWER_BYTES)
    with pytest.raises(oa.AccrualError, match="PLAN_FREEZE_INVALID"):
        oa.verify_plan_binding(plan, power)


@pytest.mark.parametrize("sha,parents,committer,moment", [
    (oa.PLAN_MERGE_SHA, oa.PLAN_MERGE_PARENTS, "GitHub", "2026-10-14T00:00:01Z"),  # late
    (oa.PLAN_MERGE_SHA, oa.PLAN_MERGE_PARENTS, "GitHub", "2026-10-01T02:39:27Z"),  # not the merge instant
    (oa.PLAN_MERGE_SHA, oa.PLAN_MERGE_PARENTS, "karl", "2026-10-01T02:39:26Z"),  # not a server merge
    ("0" * 40, oa.PLAN_MERGE_PARENTS, "GitHub", "2026-10-01T02:39:26Z"),
    (oa.PLAN_MERGE_SHA, oa.PLAN_MERGE_PARENTS[::-1], "GitHub", "2026-10-01T02:39:26Z"),
    (oa.PLAN_MERGE_SHA, oa.PLAN_MERGE_PARENTS, "GitHub", "2026-10-01T02:39:26"),  # naive
    (oa.PLAN_MERGE_SHA, oa.PLAN_MERGE_PARENTS, "GitHub", "garbage"),
])
def test_invalid_or_late_freeze_event_rejects(sha, parents, committer, moment) -> None:
    with pytest.raises(oa.AccrualError, match="PLAN_FREEZE_INVALID"):
        oa.verify_freeze_event(sha, parents, committer, moment)


def test_plan_exclusion_vocabulary_is_exact_and_never_minted_codes_rejected() -> None:
    codes = json.loads(PLAN_BYTES)["prospective_data_seal"]["exclusion_reason_codes"]
    assert tuple(codes["market"]) == oa.MARKET_EXCLUSION_REASONS and tuple(codes["row"]) == oa.ROW_EXCLUSION_REASONS
    assert tuple(codes["date"]) == oa.DATE_EXCLUSION_REASONS
    assert "LABEL_GAMMA_NOT_FINAL" not in oa.MARKET_EXCLUSION_REASONS
    for kind, code in (("MARKET", "LABEL_GAMMA_NOT_FINAL"), ("MARKET", "BUDGET_EXHAUSTED_BEFORE_EVALUATION"),
                       ("ROW", "BUDGET_EXHAUSTED_BEFORE_EVALUATION"), ("ROW", "OOS_DATE_NO_ELIGIBLE_ROW"), ("SAMPLE", "B0_UNAVAILABLE")):
        with pytest.raises(oa.AccrualError):
            oa.oos_exclusion("2026-10-18", kind, "x", code)
    with pytest.raises(oa.AccrualError):
        oa.oos_exclusion("2026-10-18", "DATE", "2026-10-19", "OOS_DATE_NO_ELIGIBLE_ROW")


def test_local_provenance_ceiling_equals_qualification_constant() -> None:
    assert oa.MAX_QUALIFICATION_PROVENANCE_MANIFESTS == qualification_module.MAX_QUALIFICATION_PROVENANCE_MANIFESTS == 256
    assert oa.PROSPECTIVE_MANIFEST_RESERVE == 150


# ── census ────────────────────────────────────────────────────────────────────


def test_frozen_census_hours_and_window() -> None:
    assert oa.window_dates()[0] == "2026-10-15" and oa.window_dates()[-1] == "2027-02-11" and len(oa.window_dates()) == 120
    assert oa.required_discovery_hours(date(2026, 10, 16)) == ("2026-10-15/11", "2026-10-15/12", "2026-10-16/11", "2026-10-16/12")
    assert len(oa.required_discovery_hours(date(2027, 3, 1))) == 240
    with pytest.raises(oa.AccrualError):
        oa.discovery_hour(date(2026, 10, 15), 13)


def test_failed_discovery_hour_never_closes_the_census_until_read() -> None:
    day = date(2026, 10, 17)
    hours = set(oa.required_discovery_hours(day))
    assert oa.census_closed(day, frozenset(hours))
    missing = hours - {"2026-10-16/12"}
    assert not oa.census_closed(day, frozenset(missing))
    assert oa.census_closed(date(2026, 10, 15), frozenset(missing))  # earlier dates do not need the later hour
    assert not oa.census_closed(date(2026, 10, 14), frozenset(hours))  # outside the plan window
    assert not oa.census_closed(date(2027, 2, 12), frozenset(oa.required_discovery_hours(date(2027, 2, 12))))


def _event(market_id: str, slug: str, received: str, hour: str, condition: str = "0x" + "11" * 32) -> v3.V3Event:
    return v3.V3Event("new_market", hour, 0, condition, None, market_id, received, received[:23] + "Z",
                      tuple(sorted((("assets_ids", "1,2"), ("outcomes", "Yes\u001fNo"), ("question", "Will it rain?"), ("slug", slug)))))


def test_census_collapses_witness_copies_deterministically_and_assigns_by_slug_date() -> None:
    slug = "where-will-it-rain-on-october-17-2026-new-york-ny"
    early = _event("10", slug, "2026-10-16T11:09:14.000001Z", "2026-10-16/11")
    late = _event("10", slug, "2026-10-16T11:09:16.000000Z", "2026-10-16/11")
    other = _event("11", "where-will-it-rain-on-october-18-2026-new-york-ny", "2026-10-16T12:00:00.000000Z", "2026-10-16/12")
    beyond = _event("10", slug, "2026-10-16T10:00:00.000000Z", "2026-10-18/11")  # later census hour: ignored for 10-17
    for events in ({"2026-10-16/11": [early, late], "2026-10-16/12": [other], "2026-10-18/11": [beyond]},
                   {"2026-10-18/11": [beyond], "2026-10-16/12": [other], "2026-10-16/11": [late, early]}):
        census = oa.assign_census(events, date(2026, 10, 17))
        assert [c.market_id for c in census.candidates] == ["10"]
        assert census.candidates[0].first_received == "2026-10-16T11:09:14.000001Z"
    bad = _event("10", slug, "2026-10-16T11:09:17.000000Z", "2026-10-16/11", condition="0x" + "22" * 32)
    census = oa.assign_census({"2026-10-16/11": [early, bad]}, date(2026, 10, 17))
    assert census.candidates == () and census.inconsistent_market_ids == ("10",)
    noise = _event("12", "will-btc-go-up", "2026-10-16T11:00:00.000000Z", "2026-10-16/11")
    assert not oa.is_rain_family_event(noise)


# ── row identity ──────────────────────────────────────────────────────────────


def test_row_id_is_exactly_the_six_label_free_fields() -> None:
    fields = dict(target_date="2026-10-18", market_id="4100180", condition_id="0x" + "18" * 32, checkpoint_id=A,
                  decision_time="2026-10-17T12:09:14.805697Z", yes_token_id="41001801")
    row = oa.prospective_row_id(**fields)
    body = {k: fields[k] for k in ("target_date", "market_id", "condition_id", "checkpoint_id", "decision_time", "yes_token_id")}
    assert row == oa.ROW_ID_PREFIX + hashlib.sha256(qd.canonical_json_bytes(body)).hexdigest()
    for key in fields:
        changed = dict(fields)
        changed[key] = {"checkpoint_id": B, "decision_time": "2026-10-18T05:00:00Z", "target_date": "2026-10-19"}.get(key, "9")
        assert oa.prospective_row_id(**changed) != row
    import inspect
    assert list(inspect.signature(oa.prospective_row_id).parameters) == list(body)
    with pytest.raises(oa.AccrualError):
        oa.prospective_row_id(**{**fields, "checkpoint_id": "LABEL"})


# ── B0 / q / L ────────────────────────────────────────────────────────────────


def _history(bid: str | None = "0.40", ask: str | None = "0.46", trade: dict | None = None, state: str = "OBSERVED") -> dict:
    return {"best_bid_ask": {"best_bid": bid, "best_ask": ask, "spread": "0.99", "timestamp_received": "2026-10-17T11:00:00.000000Z"},
            "last_trade_price": trade, "last_trade_price_state": state}


CP = utc("2026-10-17T12:00:00Z")


def test_b0_midpoint_trade_unavailable_and_source_invalid_distinctions() -> None:
    assert oa.materialize_b0(_history(), CP) == oa.B0Result(True, "MIDPOINT", "0.43")
    assert oa.materialize_b0(_history("0.40", "0.50"), CP) == oa.B0Result(True, "MIDPOINT", "0.45")  # spread == 0.1
    trade = {"price": "0.52", "timestamp_received": "2026-10-16T12:00:00.000000Z"}  # exactly 86400 s
    assert oa.materialize_b0(_history("0.30", "0.41", trade), CP) == oa.B0Result(True, "LAST_TRADE", "0.52")
    stale = {"price": "0.52", "timestamp_received": "2026-10-16T11:59:59.999999Z"}
    assert oa.materialize_b0(_history("0.30", "0.41", stale), CP) == oa.B0Result(False, None, None)
    assert oa.materialize_b0(_history(None, "0.41", None, "NOT_OBSERVED_IN_SEARCHED_HOURS"), CP).available is False
    assert oa.materialize_b0(_history("0", "0.05"), CP).available is False  # one-sided book is not a valid book
    with pytest.raises(qd.RuleExclusion, match="MARKET_HISTORY_SOURCE_INVALID"):
        oa.materialize_b0(_history("0.30", "0.41", None, oa.LTP_STATE_SEARCH_INCOMPLETE), CP)
    with pytest.raises(oa.AccrualError):  # look-ahead
        oa.materialize_b0(_history(trade={"price": "0.5", "timestamp_received": "2026-10-17T12:00:01Z"}), CP)


def test_q_and_l_are_canonical_decimal_strings() -> None:
    weather = {"periods": [{"pop12_percent": 40}, {"pop12_percent": 10}], "climate_day_start": "2026-10-18T05:00:00Z",
               "public_available_time": "2026-10-17T10:51:56Z"}
    assert oa.materialize_q(weather) == "0.4"
    assert oa.materialize_q({**weather, "periods": [{"pop12_percent": 100}]}) == "0.99"
    assert oa.materialize_q({**weather, "periods": [{"pop12_percent": 0}]}) == "0.01"
    assert oa.materialize_q({**weather, "periods": [{"pop12_percent": 5}]}) == "0.05"
    assert oa.materialize_l(weather) == ("65284", "0.755601851852")
    assert oa.materialize_l({**weather, "public_available_time": "2026-10-18T06:00:00.5Z"}) == ("-3600.5", "-0.041672453704")
    for bad in ({**weather, "periods": []}, {**weather, "periods": [{"pop12_percent": 101}]}, {**weather, "periods": [{"pop12_percent": 4.0}]}):
        with pytest.raises(oa.AccrualError):
            oa.materialize_q(bad)
    assert oa.canonical_decimal(oa.Decimal("1E+1")) == "10" and oa.canonical_decimal(oa.Decimal("-0.00")) == "0"


# ── stable prefix / seal decision ─────────────────────────────────────────────


def _window(n: int) -> list[str]:
    return [(date(2026, 10, 15) + timedelta(days=i)).isoformat() for i in range(n)]


def test_pending_earlier_date_blocks_and_never_leapfrogged() -> None:
    window = _window(60)
    states = {d: oa.DATE_ELIGIBLE for d in window}
    states[window[3]] = oa.DATE_PENDING
    prefix = oa.stable_prefix(states, window)
    assert prefix.eligible_dates == tuple(window[:3]) and prefix.earliest_pending_date == window[3] and not prefix.complete
    assert oa.seal_decision(prefix, {}) == oa.SEAL_NOT_READY


def test_pending_after_d50_does_not_block_the_stable_prefix() -> None:
    window = _window(60)
    states = {d: oa.DATE_ELIGIBLE for d in window}
    states[window[55]] = oa.DATE_PENDING
    prefix = oa.stable_prefix(states, window)
    assert prefix.complete and prefix.eligible_dates == tuple(window[:50])
    rows = {d: ["r1", "r2"] for d in window}
    assert oa.seal_decision(prefix, rows) == oa.STATE_SEALED


def test_excluded_former_pending_date_shifts_prefix_before_seal() -> None:
    window = _window(60)
    states = {d: oa.DATE_ELIGIBLE for d in window}
    states[window[3]] = oa.DATE_PENDING
    assert oa.stable_prefix(states, window).eligible_dates == tuple(window[:3])
    states[window[3]] = oa.DATE_EXCLUDED  # the formerly pending date became excluded before the seal
    shifted = oa.stable_prefix(states, window)
    assert shifted.complete and shifted.eligible_dates == tuple(window[:3] + window[4:51])


def test_rows_insufficient_and_cap_insufficiency_waits_for_pending() -> None:
    window = _window(60)
    states = {d: oa.DATE_ELIGIBLE for d in window[:50]} | {d: oa.DATE_EXCLUDED for d in window[50:]}
    prefix = oa.stable_prefix(states, window)
    assert oa.seal_decision(prefix, {d: ["r"] for d in window}) == oa.STATE_ROWS_INSUFFICIENT  # 50 rows < 100
    few = {d: oa.DATE_EXCLUDED for d in window} | {window[0]: oa.DATE_ELIGIBLE}
    few[window[40]] = oa.DATE_PENDING
    assert oa.seal_decision(oa.stable_prefix(few, window), {}) == oa.SEAL_NOT_READY
    few[window[40]] = oa.DATE_EXCLUDED
    terminal = oa.stable_prefix(few, window)
    assert terminal.window_terminal and oa.seal_decision(terminal, {}) == oa.STATE_INSUFFICIENT_AT_CAP


def test_date_classification_precedence() -> None:
    assert oa.classify_date("2026-10-18", {}) == (oa.DATE_EXCLUDED, "OOS_DATE_NO_ELIGIBLE_ROW")
    assert oa.classify_date("2026-10-15", {"r": "2026-10-14T23:59:59Z"}) == (oa.DATE_EXCLUDED, "OOS_DATE_DECISION_BEFORE_START")
    assert oa.classify_date("2026-10-17", {"r": "2026-10-16T23:59:59Z", "s": "2026-10-17T05:00:00Z"}) == \
        (oa.DATE_EXCLUDED, "OOS_DATE_DECISION_IN_WP170_EMBARGO")
    assert oa.classify_date("2027-02-11", {"r": "2027-02-12T00:00:00Z"}) == (oa.DATE_EXCLUDED, "OOS_DATE_DECISION_AT_OR_AFTER_CAP")
    assert oa.classify_date("2026-10-18", {"r": "2026-10-17T00:00:00Z"}) == (oa.DATE_ELIGIBLE, None)
    assert oa.mr09_end_time(["2026-10-18T05:00:00.999Z", "2026-10-17T12:09:14Z"]) == "2026-10-18T05:00:01Z"


# ── membership seal (positive + negative matrix) ──────────────────────────────


def _row(i: int) -> str:
    return oa.ROW_ID_PREFIX + hashlib.sha256(str(i).encode()).hexdigest()


def _entries(window: list[str], rows_per_date: int = 2) -> list[dict[str, object]]:
    entries = []
    counter = 0
    for day in window:
        times = {}
        for k in range(rows_per_date):
            counter += 1
            times[_row(counter)] = f"{day}T0{5 + k}:00:00Z"
        entries.append({"entry_kind": "DATE", "target_date": day, "classification": oa.DATE_ELIGIBLE, "reason": None,
                        "row_decision_times": dict(sorted(times.items())),
                        "exclusions": [oa.oos_exclusion(day, "ROW", f"9{counter}:{B}", "B0_UNAVAILABLE")]})
    return entries


def _membership(entries, window):
    prefix = oa.stable_prefix({e["target_date"]: e["classification"] for e in entries}, window)
    preimage = oa.expected_membership(entries, prefix, BUNDLE)
    return prefix, preimage, {"preimage": preimage, "oos_membership_id": oa.membership_id(preimage)}


def test_membership_preimage_keys_order_and_id_exact() -> None:
    window = _window(52)
    entries = _entries(window[2:])
    entries = [{"entry_kind": "DATE", "target_date": d, "classification": oa.DATE_EXCLUDED, "reason": "OOS_DATE_NO_ELIGIBLE_ROW",
                "row_decision_times": {}, "exclusions": [oa.oos_exclusion(d, "DATE", d, "OOS_DATE_NO_ELIGIBLE_ROW")]}
               for d in window[:2]] + entries
    prefix, preimage, stored = _membership(entries, window)
    assert tuple(sorted(preimage)) == oa.MEMBERSHIP_PREIMAGE_KEYS
    assert json.loads(PLAN_BYTES)["prospective_data_seal"]["membership_seal"]["preimage_keys"] == list(oa.MEMBERSHIP_PREIMAGE_KEYS)
    assert preimage["oos_target_dates"] == window[2:52] and preimage["oos_row_ids"] == sorted(preimage["oos_row_ids"])
    keys = [(e["target_date"], e["subject_kind"], e["subject_id"]) for e in preimage["oos_exclusions"]]
    assert keys == sorted(keys) and len(preimage["oos_exclusions"]) == 52
    canonical = json.dumps(preimage, sort_keys=True, separators=(",", ":")).encode()
    assert stored["oos_membership_id"] == oa.MEMBERSHIP_ID_PREFIX + hashlib.sha256(canonical).hexdigest()
    assert oa.verify_membership(stored, entries, prefix, BUNDLE) == stored["oos_membership_id"]


def test_mr15_prospective_sample_universe_exact() -> None:
    window = _window(56)
    entries = _entries(window[1:52])
    entries.insert(0, {"entry_kind": "DATE", "target_date": window[0], "classification": oa.DATE_EXCLUDED,
                       "reason": "OOS_DATE_DECISION_IN_WP170_EMBARGO", "row_decision_times": {},
                       "exclusions": [oa.oos_exclusion(window[0], "DATE", window[0], "OOS_DATE_DECISION_IN_WP170_EMBARGO")]})
    _prefix, preimage, _stored = _membership(entries, window)
    samples = oa.mr15_prospective_sample_ids(preimage)
    in_prefix = {r for e in entries if e["target_date"] in preimage["oos_target_dates"] for r in e["row_decision_times"]}
    after_d50 = {r for e in entries if e["target_date"] > preimage["oos_target_dates"][-1] for r in e["row_decision_times"]}
    assert set(samples) == in_prefix and len(samples) == 100 and not (set(samples) & after_d50) and after_d50
    assert all(e["target_date"] != window[0] for e in entries if set(e["row_decision_times"]) & set(samples))


def _mutations():
    def reorder(p):
        p["oos_target_dates"] = [p["oos_target_dates"][1], p["oos_target_dates"][0], *p["oos_target_dates"][2:]]

    def extra(p):
        p["oos_row_ids"] = sorted(p["oos_row_ids"] + [_row(99999)])

    def missing(p):
        p["oos_row_ids"] = p["oos_row_ids"][1:]

    def duplicate(p):
        p["oos_row_ids"] = sorted(p["oos_row_ids"] + p["oos_row_ids"][:1])

    def reason(p):
        p["oos_exclusions"][0]["reason_code"] = "GRID_BINDING_INVALID"

    def plan(p):
        p["plan_01_plan_sha256"] = "0" * 64

    def bundle(p):
        p["data03_bundle_id"] = oa.BUNDLE_ID_PREFIX + "cd" * 32

    def substitute(p):
        p["oos_target_dates"] = p["oos_target_dates"][:-1] + ["2026-12-30"]

    def skipped(p):
        p["oos_target_dates"] = p["oos_target_dates"][1:] + ["2026-12-31"]

    def cap(p):
        p["cap"] = "2027-03-01T00:00:00Z"

    def end(p):
        p["end_time"] = "2027-01-01T00:00:00Z"

    def extra_key(p):
        p["labels"] = []

    return [reorder, extra, missing, duplicate, reason, plan, bundle, substitute, skipped, cap, end, extra_key]


@pytest.mark.parametrize("mutate", _mutations())
def test_membership_negative_matrix_rejects(mutate) -> None:
    window = _window(55)
    entries = _entries(window[:52])
    prefix, preimage, stored = _membership(entries, window)
    tampered = json.loads(json.dumps(preimage))
    mutate(tampered)
    with pytest.raises(oa.AccrualError, match="MEMBERSHIP_REPRODUCTION_FAILED"):
        oa.verify_membership({"preimage": tampered, "oos_membership_id": stored["oos_membership_id"]}, entries, prefix, BUNDLE)
    with pytest.raises(oa.AccrualError, match="MEMBERSHIP_REPRODUCTION_FAILED"):
        oa.verify_membership({"preimage": preimage, "oos_membership_id": stored["oos_membership_id"]}, entries, prefix,
                             oa.BUNDLE_ID_PREFIX + "ef" * 32)


def test_post_seal_mutation_and_skipped_pending_date_reject() -> None:
    window = _window(55)
    entries = _entries(window[:52])
    prefix, preimage, stored = _membership(entries, window)
    with pytest.raises(oa.AccrualError, match="MEMBERSHIP_REPRODUCTION_FAILED"):
        oa.verify_membership({**stored, "oos_membership_id": oa.MEMBERSHIP_ID_PREFIX + "00" * 32}, entries, prefix, BUNDLE)
    pending = [dict(e) for e in entries]
    pending[4] = {**pending[4], "classification": oa.DATE_PENDING}
    later = oa.stable_prefix({e["target_date"]: e["classification"] for e in pending}, window)
    assert not later.complete
    with pytest.raises(oa.AccrualError, match="MEMBERSHIP_REPRODUCTION_FAILED"):
        oa.expected_membership(pending, later, BUNDLE)
    moved = [dict(e) for e in entries]
    moved[7]["row_decision_times"] = {**moved[7]["row_decision_times"], _row(424242): moved[7]["target_date"] + "T09:00:00Z"}
    with pytest.raises(oa.AccrualError, match="MEMBERSHIP_REPRODUCTION_FAILED"):
        oa.verify_membership(stored, moved, prefix, BUNDLE)


def test_label_or_value_mutation_never_changes_row_ids() -> None:
    base = dict(target_date="2026-10-18", market_id="1", condition_id="0x" + "01" * 32, checkpoint_id=A,
                decision_time="2026-10-17T12:00:00Z", yes_token_id="11")
    labels_yes = {oa.prospective_row_id(**base): {"label_yes": True}}
    labels_no = {oa.prospective_row_id(**base): {"label_yes": False}}
    assert set(labels_yes) == set(labels_no)
    assert oa.label_store_id(labels_yes) != oa.label_store_id(labels_no)
    assert oa.feature_column_id("wx.ndfd_pop12_max_climate_day_v1", {next(iter(labels_yes)): "0.4"}) != \
        oa.feature_column_id("wx.ndfd_pop12_max_climate_day_v1", {next(iter(labels_yes)): "0.41"})
    with pytest.raises(oa.AccrualError):
        oa.feature_column_id("b1.forecast", {"r": "0.5"})


# ── provenance ceiling ────────────────────────────────────────────────────────


def test_provenance_pre_gate_and_unavoidable_projection() -> None:
    assert oa.provenance_pre_gate(106) and not oa.provenance_pre_gate(107)
    assert oa.projected_manifest_count(100, []) == 250
    assert oa.projected_manifest_count(100, [4] * 10) == 100 + 40 + 120
    assert oa.projected_manifest_count(100, [4] * 60) == 100 + 200
    assert oa.projected_manifest_count(106, [3] * 50) == 256


# ── execution evidence (MR12) ─────────────────────────────────────────────────


CUTOFF = utc("2026-12-31T00:00:00Z")


def _gamma_capture(n: int, *, pre_close: bool = True, cohort: str | None = "cohort-a", at: str = "2026-10-20T00:00:00Z") -> dict:
    return {"capture_id": f"{oa.CAPTURE_ID_PREFIX}{n:064x}", "captured_at": at, "pre_close": pre_close, "fees_enabled_known": True,
            "tick_known": True, "min_size_known": True, "parsed_rule_cohort_id": cohort}


def _market(n: int, *, cohort: str = "cohort-a", captures=None, tick_complete: bool = True) -> dict:
    return {"market_id": str(n), "rule_cohort_id": cohort, "gamma_captures": captures if captures is not None else [_gamma_capture(n)],
            "tick_history_complete": tick_complete, "tick_history_capture_ids": [f"{oa.CAPTURE_ID_PREFIX}{n + 1000:064x}"]}


FEE = {"capture_id": oa.CAPTURE_ID_PREFIX + "f" * 64, "captured_at": "2026-10-20T00:00:00Z", "url": oa.FEE_DOC_URL, "contract_valid": True}


def test_execution_terms_family_cohort_sufficiency_and_expected_states() -> None:
    markets = [_market(1), _market(2, captures=[_gamma_capture(2, pre_close=False)])]  # cohort covered by market 1's open capture
    result = oa.classify_execution_evidence(markets, [FEE], CUTOFF, 4, 4)
    assert {k: v["state"] for k, v in result.items()} == {"FEES": "AVAILABLE", "LATENCY": "MISSING", "PARTIAL_FILL": "MISSING",
                                                          "RESOLUTION_RULES": "AVAILABLE", "SPREAD_DEPTH": "PARTIAL",
                                                          "TICK_SIZE_MIN_ORDER": "AVAILABLE"}
    assert result["FEES"]["evidence_reference_ids"] == sorted(result["FEES"]["evidence_reference_ids"])
    assert result["LATENCY"]["evidence_reference_ids"] == []
    uncovered = [_market(1), _market(3, cohort="cohort-b", captures=[_gamma_capture(3, pre_close=False, cohort="cohort-b")])]
    partial = oa.classify_execution_evidence(uncovered, [FEE], CUTOFF, 4, 4)
    assert partial["RESOLUTION_RULES"]["state"] == "MISSING" and partial["FEES"]["state"] == "PARTIAL"
    incomplete = oa.classify_execution_evidence([_market(1, tick_complete=False)], [FEE], CUTOFF, 2, 2)
    assert incomplete["TICK_SIZE_MIN_ORDER"]["state"] == "PARTIAL"


def test_execution_evidence_never_backdated_and_fee_url_exact() -> None:
    markets = [_market(1, captures=[_gamma_capture(1, at="2027-01-05T00:00:00Z")])]
    late = oa.classify_execution_evidence(markets, [{**FEE, "captured_at": "2027-01-05T00:00:00Z"}], CUTOFF, 2, 2)
    assert late["FEES"]["state"] == "MISSING" and late["RESOLUTION_RULES"]["state"] == "MISSING"
    wrong = oa.classify_execution_evidence([_market(1)], [{**FEE, "url": "https://docs.polymarket.com/trading/fees"}], CUTOFF, 2, 2)
    assert wrong["FEES"]["required_captures"]["OFFICIAL_FEE_DOCUMENTATION"] is False
    invalid = oa.classify_execution_evidence([_market(1)], [{**FEE, "contract_valid": False}], CUTOFF, 2, 2)
    assert invalid["FEES"]["state"] == "PARTIAL"
    assert oa.fee_document_valid(oa.FEE_DOC_URL, 200, b"<html>Trading fees ... Weather markets</html>")
    assert not oa.fee_document_valid(oa.FEE_DOC_URL, 200, b"<html>Trading fees only</html>")
    assert not oa.fee_document_valid(oa.FEE_DOC_URL, 301, b"<html>fee weather</html>")
    assert not oa.fee_document_valid(oa.FEE_DOC_URL.replace("13364478", "1"), 200, b"<html>fee weather</html>")


# ── ledger chain ──────────────────────────────────────────────────────────────


def test_terminal_ledger_entries_are_hash_chained_and_immutable() -> None:
    entries = oa.chain_append([], [{"entry_kind": "DATE", "run": 1, "target_date": "2026-10-16"}])
    entries = oa.chain_append(entries, [{"entry_kind": "DATE", "run": 2, "target_date": "2026-10-17"}])
    head = oa.verify_chain(entries)
    assert head == entries[-1]["entry_hash"] and entries[0]["prev"] == oa.LEDGER_GENESIS
    extended = oa.chain_append(entries, [{"entry_kind": "DATE", "run": 3, "target_date": "2026-10-18"}])
    oa.assert_terminal_entries_unchanged(entries, extended)
    mutated = [dict(e) for e in extended]
    mutated[0]["target_date"] = "2026-10-20"
    for bad in (mutated, extended[1:], [extended[1], extended[0], extended[2]]):
        with pytest.raises(oa.AccrualError, match="LEDGER_CHAIN_INVALID"):
            oa.verify_chain(bad)
    with pytest.raises(oa.AccrualError, match="LEDGER_CHAIN_INVALID"):
        oa.assert_terminal_entries_unchanged(entries, oa.chain_append([], [{"entry_kind": "DATE", "run": 1, "target_date": "x"}]))


# ── visible-report firewall ───────────────────────────────────────────────────


def _seal_report(**overrides) -> dict:
    report = {"kind": "SEAL", "wp_id": oa.WP_ID, "status": "SEALED", "state": oa.STATE_SEALED, "plan_sha256": oa.PLAN_SHA256,
              "ledger_head": oa.LEDGER_ENTRY_PREFIX + "a" * 64, "oos_membership_id": oa.MEMBERSHIP_ID_PREFIX + "b" * 64,
              "data03_bundle_id": BUNDLE, "oos_target_dates": 50, "oos_rows": 120, "oos_exclusions": 3,
              "end_time": "2026-12-20T05:00:01Z", "provenance": {"n2": 90, "prospective": 150, "total": 240, "ceiling": 256},
              "execution_evidence_states": {c: "MISSING" for c in oa.EXECUTION_CLASSES}}
    report.update(overrides)
    return report


@pytest.mark.parametrize("override", [
    {"labels": [1]},  # extra key
    {"oos_rows": -1},
    {"oos_rows": "120"},
    {"state": "QUAL_PASS"},
    {"end_time": "winning_outcome=Yes"},
    {"oos_membership_id": "CANARY Yes 0.43"},
    {"provenance": {"n2": 90, "prospective": 150, "total": 240, "ceiling": 256, "prevalence": 1}},
    {"execution_evidence_states": {"FEES": "AVAILABLE_YES"}},
    {"execution_evidence_states": {"BRIER": "MISSING"}},
])
def test_visible_schema_rejects_extra_keys_and_open_text(override) -> None:
    with pytest.raises(oa.AccrualError, match="VISIBLE_SCHEMA_VIOLATION"):
        oa.validate_visible_report(_seal_report(**override))
    assert oa.validate_visible_report(_seal_report())["kind"] == "SEAL"
    with pytest.raises(oa.AccrualError, match="VISIBLE_SCHEMA_VIOLATION"):
        oa.validate_visible_report({k: v for k, v in _seal_report().items() if k != "oos_rows"})


def _market_entry(market_id: str, basis: str, reason: str | None) -> dict:
    return {"entry_kind": "MARKET", "subject_id": market_id, "market_exclusion": None,
            "rows": [{"checkpoint_id": A, "state": "ELIGIBLE", "b0_basis": basis, "reason": None},
                     {"checkpoint_id": B, "state": "EXCLUDED", "b0_basis": None, "reason": reason}]}


def test_structural_counts_invariant_under_sealed_value_and_label_permutation() -> None:
    markets = [_market_entry("1", "MIDPOINT", "B0_UNAVAILABLE"), _market_entry("2", "LAST_TRADE", "CHECKPOINT_B_MARKET_NOT_OPEN_60M")]
    dates = [{"entry_kind": "DATE", "target_date": "2026-10-18", "classification": oa.DATE_ELIGIBLE, "reason": None,
              "eligible_rows_by_checkpoint": {A: 2, B: 0},
              "exclusions": [oa.oos_exclusion("2026-10-18", "ROW", f"1:{B}", "B0_UNAVAILABLE")]}]
    sealed_a = [{"row_id": "r1", "label": {"label_yes": True}, "features": {"q": "0.4"}}]
    sealed_b = [{"row_id": "r1", "label": {"label_yes": False}, "features": {"q": "0.9"}}]
    kwargs = dict(discovered_markets=2, outside_window_markets=0, discovery_hours_read=4, discovery_hours_pending=0,
                  coverage_classes={"FULL": 3})
    first = oa.structural_counts(markets, dates, **kwargs)
    assert first == oa.structural_counts(markets, dates, **kwargs) and sealed_a != sealed_b
    assert first["b0_basis"] == {"LAST_TRADE": 1, "MIDPOINT": 1} and first["b0_unavailable"] == 1
    assert first["row_exclusions_by_reason"][B] == {"B0_UNAVAILABLE": 1}
    assert "label" not in json.dumps(first) and "0.4" not in json.dumps(first)


def test_pure_module_has_no_forecast_fit_score_candidate_or_network_surface() -> None:
    path = ROOT / "src" / "data_layer" / "analytical_research" / "qualification_oos_accrual.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported = {(node.module or "") for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
    imported |= {alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names}
    assert imported <= {"__future__", "hashlib", "json", "re", "dataclasses", "datetime", "decimal", "typing", ""}
    names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)} | \
        {node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)}
    for banned in ("urlopen", "socket", "requests", "build_qualification_candidate", "evaluate_qualification", "sigmoid",
                   "brier", "logit", "open"):
        assert banned not in names, banned


def test_historical_n2_fails_closed_on_unreadable_rows() -> None:
    bad = {"best_bid_ask": {"best_bid": "0.4", "best_ask": "x", "timestamp_received": "2026-10-17T11:00:00Z"}}
    with pytest.raises(oa.AccrualError):
        oa.materialize_b0(bad, CP)
    with pytest.raises(oa.AccrualError, match="PLAN_FREEZE_INVALID"):
        oa.historical_n2({"bundle_id": "x"})
