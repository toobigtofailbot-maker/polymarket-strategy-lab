"""S10-R3-LEARN-01 offline tests: verified frozen FORECAST-01 receipt -> later outcomes -> unchanged-native
scoring -> descriptive diagnostics -> advisory future-research proposals -> cold verify.

The forecast scratch is produced by the real S10-R3-FORECAST-01 fixture (SANITIZED_SYNTHETIC). Later
outcomes are synthetic too: results prove the mechanism and honest accounting, never predictive value.
The numeric oracle below is plain float math, independent of forecast_evaluation.score_one.
"""
from __future__ import annotations

import ast
import copy
from decimal import Decimal
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys

import pytest

from src.data_layer.analytical_research import forecast_evaluation as FE
from src.data_layer.analytical_research import learning_feedback as LF
from tests.data_layer.analytical_research.test_alpha_discovery import _alpha_registry
from tests.tools.alpha.test_forecast_evaluation import MARKETS, baseline, world  # noqa: F401 - module fixtures
from tools.alpha import run_forecast_evaluation as FCLI
from tools.alpha import run_learning_feedback as CLI

REPO_ROOT = Path(__file__).resolve().parents[3]
CUTOFF = "2027-06-30T00:00:00Z"
RESOLVED, KNOWN, SEEN = "2026-12-31T00:00:00Z", "2027-01-01T00:00:00Z", "2027-01-02T00:00:00Z"
LABELS = {f"t-{slug}": label for slug, _e, _c, _d, _p, label in MARKETS}
NEW_LABEL_CASE = "t-ukraine-ceasefire"  # no outcome existed at forecast time: a genuinely later observation
MISSING_CASE, LATE_CASE, CORRECTED_CASE = "t-nyc-rain", "t-grammys", "t-uk-pm"


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canon(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _forecast(scratch: Path) -> tuple[dict, dict]:
    receipt = json.loads((scratch / "receipt.json").read_text(encoding="utf-8"))
    frozen = json.loads((scratch / "frozen_cases.json").read_text(encoding="utf-8"))
    return receipt, frozen


def _selected(receipt) -> dict:
    return {r["case_id"]: r for r in receipt["core"]["targets"] if r["status"] == "SELECTED"}


def _record(row, label=None, **overrides):
    value = {"case_id": row["case_id"], "market_id": row["market_id"], "event_group": row["event_group"],
             "yes_label": row["yes_label"], "rule_content_sha256": row["rule_content_sha256"],
             "outcome_label": label or LABELS[row["case_id"]] or "No", "resolved_time": RESOLVED, "known_time": KNOWN,
             "local_first_seen_time": SEEN, "source_content_sha256": None, "evidence_class": "SANITIZED_SYNTHETIC"}
    value.update(overrides)
    return value


def _packet(receipt, records, **overrides):
    value = {"schema_id": LF.OUTCOMES_SCHEMA, "packet_label": "learn01-synthetic", "forecast_receipt_id": receipt["receipt_id"],
             "learning_cutoff": CUTOFF, "records": records}
    value.update(overrides)
    return value


def _demo_records(receipt):
    rows = _selected(receipt)
    records = [_record(r) for c, r in sorted(rows.items()) if c != MISSING_CASE]
    records = [dict(r, local_first_seen_time="2027-07-01T00:00:00Z") if r["case_id"] == LATE_CASE else r for r in records]
    flipped = "Yes" if LABELS[CORRECTED_CASE] == "No" else "No"
    records.append(_record(rows[CORRECTED_CASE], flipped, known_time="2027-08-01T00:00:00Z",
                           local_first_seen_time="2027-08-01T00:00:00Z"))  # post-cutoff revision
    return records


def _learn(tmp_path, forecast_scratch, packet, name="learn", alpha=None):
    path = tmp_path / f"{name}-outcomes.json"
    path.write_text(json.dumps(packet), encoding="utf-8")
    scratch = (tmp_path / name).resolve()
    argv = ["run", "--forecast-scratch", str(forecast_scratch), "--outcomes", str(path), "--scratch-dir", str(scratch)]
    code = CLI.main(argv + (["--alpha-registry", str(alpha)] if alpha else []))
    out = scratch / "receipt.json"
    return code, scratch, json.loads(out.read_text(encoding="utf-8")) if out.exists() else None


def _core(forecast_scratch, packet, links=None, receipt_edit=None):
    receipt, frozen = _forecast(forecast_scratch)
    if receipt_edit:
        receipt = copy.deepcopy(receipt)
        receipt_edit(receipt)
    links = links or {"status": "NOT_SUPPLIED", "registry_head_entry_hash": None, "by_market": {}}
    return LF.build_learning_core(receipt, frozen, packet, links, "code:test", {})


def _stdout(capsys):
    return json.loads(capsys.readouterr().out.strip().splitlines()[-1])


def _tree(path: Path) -> dict:
    return {p.relative_to(path).as_posix(): _sha(p.read_bytes()) for p in sorted(path.rglob("*")) if p.is_file()}


@pytest.fixture(scope="module")
def alpha(tmp_path_factory):
    base = tmp_path_factory.mktemp("learn01_alpha")
    return _alpha_registry(base, [("cpi", None), ("starship", "WATCH_FOR_CHANGE"), ("not-in-cohort", None)])


@pytest.fixture(scope="module")
def learned(baseline, alpha, tmp_path_factory):  # noqa: F811 - module fixture imported above
    forecast_scratch, receipt = baseline
    before = _sha(Path(alpha).read_bytes())
    code, scratch, out = _learn(tmp_path_factory.mktemp("learn01_run"), forecast_scratch,
                                _packet(receipt, _demo_records(receipt)), alpha=alpha)
    assert code == 0, out
    assert _sha(Path(alpha).read_bytes()) == before
    return forecast_scratch, receipt, scratch, out


# ------------------------------------------------------------------ R001


def test_learning_calls_verified_frozen_forecast_and_native_provenance(baseline, tmp_path, monkeypatch):  # noqa: F811
    forecast_scratch, receipt = baseline
    calls, real = [], FCLI.verify
    monkeypatch.setattr(FCLI, "verify", lambda d: calls.append(Path(d)) or real(d))
    code, scratch, out = _learn(tmp_path, forecast_scratch, _packet(receipt, _demo_records(receipt)))
    assert code == 0
    # the actual merged FORECAST-01 verifier ran on the caller scratch and then on the frozen copy
    assert calls[0] == forecast_scratch.resolve() and calls[1] == scratch / "inputs" / "forecast"
    assert real(scratch / "inputs" / "forecast")["status"] == "VERIFIED"
    up, core = out["core"]["upstream"], receipt["core"]
    assert up["forecast_receipt_id"] == receipt["receipt_id"] and up["forecast_verify_status"] == "VERIFIED"
    assert up["grounding_receipt_id"] == core["source_grounding"]["receipt_id"]
    assert up["alpha_universe_snapshot_id"] == core["source_grounding"]["alpha_universe_snapshot_id"]
    assert up["forecast_code_identity"] == core["code_identity"] == FCLI.code_identity()
    assert up["cohort_membership_sha256"] == core["cohort"]["membership_sha256"]
    assert up["original_forecasts_sha256"] == _sha(_canon(core["forecasts"]))
    assert up["original_scoring_snapshot_sha256"] == _sha(_canon(core["scoring"]))
    assert up["original_scoring_status"] == "UNCHANGED_HISTORICAL_SNAPSHOT"
    # one-to-one: selected ids == target rows == forecast keys == outcome case states
    rows = _selected(receipt)
    assert sorted(rows) == core["cohort"]["selected_case_ids"] == sorted(core["forecasts"])
    assert [c["case_id"] for c in out["core"]["outcomes"]["cases"]] == sorted(rows)
    for rec in _demo_records(receipt):
        if rec["case_id"] in rows:
            r = rows[rec["case_id"]]
            assert (rec["market_id"], rec["event_group"], rec["rule_content_sha256"]) == (
                r["market_id"], r["event_group"], r["rule_content_sha256"])
    # the original frozen forecast scratch is byte-identical after learning
    assert json.loads((forecast_scratch / "receipt.json").read_text(encoding="utf-8")) == receipt
    # never refits: the learning module has no path to the forecasters, and labels never move p_yes
    names = {n.attr for n in ast.walk(ast.parse(Path(LF.__file__).read_text(encoding="utf-8")))
             if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name) and n.value.id == "FE"}
    assert names.isdisjoint({"forecast_case", "beta_prior", "fit_wang", "wang_transform", "build_evaluation_core",
                             "evaluate_history", "freeze_cohort"}) and "score_one" in names
    flipped = [dict(r, outcome_label="Yes" if r["outcome_label"] == "No" else "No") for r in _demo_records(receipt)]
    other = _core(forecast_scratch, _packet(receipt, flipped))
    assert other["upstream"] == _core(forecast_scratch, _packet(receipt, _demo_records(receipt)))["upstream"]


# ------------------------------------------------------------------ R002


def test_learning_outcome_join_identity_timing_and_provenance(baseline):  # noqa: F811
    forecast_scratch, receipt = baseline
    rows = _selected(receipt)
    assert NEW_LABEL_CASE in rows
    good = {c: _record(r) for c, r in rows.items()}
    some = sorted(c for c in rows if c != NEW_LABEL_CASE and LABELS[c])[:13]

    def state_of(case, *records):
        recs = [v for c, v in good.items() if c != case] + list(records)
        core = _core(forecast_scratch, _packet(receipt, recs))
        return next(s for s in core["outcomes"]["cases"] if s["case_id"] == case), core
    r = {c: rows[c] for c in some}
    variants = [
        (some[0], _record(r[some[0]], market_id="market:polymarket:other"), "EXCLUDED", "MARKET_MISMATCH"),
        (some[1], _record(r[some[1]], event_group="event:polymarket:other"), "EXCLUDED", "EVENT_GROUP_MISMATCH"),
        (some[2], _record(r[some[2]], rule_content_sha256="0" * 64), "EXCLUDED", "RULE_MISMATCH"),
        (some[3], _record(r[some[3]], yes_label="No"), "EXCLUDED", "YES_LABEL_MISMATCH"),
        (some[4], _record(r[some[4]], outcome_label="Maybe"), "EXCLUDED", "OUTCOME_LABEL_UNKNOWN"),
        (some[5], _record(r[some[5]], known_time="2026-12-30T00:00:00Z"), "EXCLUDED", "CLOCK_INCONSISTENT"),
        (some[6], _record(r[some[6]], local_first_seen_time="2026-12-31T12:00:00Z"), "EXCLUDED", "CLOCK_INCONSISTENT"),
        (some[7], _record(r[some[7]], resolved_time="2026-06-01T00:00:00Z", known_time="2026-06-01T00:00:00Z",
                          local_first_seen_time=None), "EXCLUDED", "RESOLVED_BEFORE_DECISION"),
        (some[8], _record(r[some[8]], "Yes" if LABELS[some[8]] == "No" else "No"), "DISPUTED", "PRIOR_OUTCOME_CONFLICT"),
        (some[9], _record(r[some[9]], resolved_time="2026-12-30T00:00:00Z"), "DISPUTED", "PRIOR_OUTCOME_CONFLICT"),
        (some[10], _record(r[some[10]], evidence_class="CALLER_IMPORTED_UNVERIFIED"), "EXCLUDED", "EVIDENCE_CLASS_MISMATCH"),
        (some[11], _record(r[some[11]], source_content_sha256="a" * 64), "EXCLUDED", "SOURCE_CLAIM_UNVALIDATED"),
        (some[12], _record(r[some[12]], local_first_seen_time="2027-07-01T00:00:00Z"), "LATE_AFTER_CUTOFF",
         "AVAILABLE_AFTER_LEARNING_CUTOFF"),
    ]
    for case, record, state, reason in variants:
        got, _ = state_of(case, record)
        assert (got["state"], got["reason"], got["y"]) == (state, reason, None), (case, reason)
    got, core = state_of(some[0])  # no record at all
    assert (got["state"], got["reason"]) == ("MISSING_OUTCOME", "NO_OUTCOME_RECORD")
    rec = _record(rows[NEW_LABEL_CASE], "Yes")
    got, _ = state_of(NEW_LABEL_CASE, rec, dict(rec))
    assert (got["state"], got["reason"]) == ("DISPUTED", "DUPLICATE_OUTCOME")
    got, _ = state_of(NEW_LABEL_CASE, rec, _record(rows[NEW_LABEL_CASE], "No"))
    assert (got["state"], got["reason"]) == ("DISPUTED", "CONFLICTING_OUTCOME")
    got, core = state_of(NEW_LABEL_CASE, rec, _record(rows[NEW_LABEL_CASE], "No", known_time="2027-09-01T00:00:00Z",
                                                       local_first_seen_time=None))
    assert (got["state"], got["y"], got["clock_basis"]) == ("SCORABLE", 1, "LOCAL_FIRST_SEEN")
    assert core["outcomes"]["corrections"][0]["status"] == "CORRECTION_AFTER_CUTOFF_LABEL_CHANGED"
    got, core = state_of(NEW_LABEL_CASE, _record(rows[NEW_LABEL_CASE], "No", local_first_seen_time=None),
                         dict(good[some[0]], case_id="t-not-selected"))
    assert (got["state"], got["y"], got["clock_basis"]) == ("SCORABLE", 0, "CALLER_ASSERTED_KNOWN_TIME")
    assert core["outcomes"]["denominators"]["records_refused_by_reason"] == {"FOREIGN_CASE": 1}
    o = core["outcomes"]
    assert o["provenance"] == "SYNTHETIC_LABEL_NOT_SETTLEMENT" and o["settlement_origin_verified"] is False
    # local-real forecasts only join CALLER_IMPORTED_UNVERIFIED records, which stay unauthenticated
    real = lambda rc: rc["core"].update(corpus_class="LOCAL_REAL_PIT")  # noqa: E731
    imported = [dict(v, evidence_class="CALLER_IMPORTED_UNVERIFIED") for v in good.values()]
    core = _core(forecast_scratch, _packet(receipt, imported), receipt_edit=real)
    assert core["outcomes"]["provenance"] == "CALLER_IMPORTED_ORIGIN_UNAUTHENTICATED"
    assert core["outcomes"]["denominators"]["scorable"] == len(rows) and core["authority"]["settlement_origin_verified"] is False
    core = _core(forecast_scratch, _packet(receipt, list(good.values())), receipt_edit=real)
    assert core["outcomes"]["denominators"]["excluded"] == len(rows)


# ------------------------------------------------------------------ R003


def _oracle(p: str, y: int) -> tuple[float, float]:
    q = min(max(float(p), 1e-12), 1 - 1e-12)
    return (float(p) - y) ** 2, -math.log(q if y == 1 else 1 - q)


def test_learning_fixed_forecasts_rescored_with_matching_denominators(learned):
    _f, receipt, _s, out = learned
    core, forecasts = out["core"], receipt["core"]["forecasts"]
    states = {c["case_id"]: c for c in core["outcomes"]["cases"]}
    d = core["outcomes"]["denominators"]
    assert (d["missing_outcome"], d["late_after_cutoff"], d["disputed"], d["excluded"]) == (1, 1, 0, 0)
    assert states[MISSING_CASE]["state"] == "MISSING_OUTCOME" and states[LATE_CASE]["state"] == "LATE_AFTER_CUTOFF"
    assert states[CORRECTED_CASE]["y"] == (1 if LABELS[CORRECTED_CASE] == "Yes" else 0)  # history not rewritten
    assert core["outcomes"]["corrections"] == [{"case_id": CORRECTED_CASE, "conflicts_prior": True, "record_sha256": core[
        "outcomes"]["corrections"][0]["record_sha256"], "status": "CORRECTION_AFTER_CUTOFF_LABEL_CHANGED"}]
    scorable = sorted(c for c, s in states.items() if s["state"] == "SCORABLE")
    assert d["scorable"] == len(scorable) == d["selected_cases"] - 2
    paired = [c for c in scorable if all(forecasts[c]["methods"][m]["status"] == "FORECAST" for m in FE.PRIMARY_METHODS)]
    s = core["scoring"]
    assert s["denominators"]["paired_intersection"] == len(paired) and s["paired_case_ids_sha256"] == _sha(_canon(paired))
    assert s["denominators"]["event_groups_disjoint"] is True
    assert s["denominators"]["scorable_event_groups"] == len({_selected(receipt)[c]["event_group"] for c in scorable})
    for m in FE.METHODS:
        md = s["methods"][m]["denominators"]
        assert md["offered"] == md["eligible"] + md["missing_outcome"] + md["disputed"] + md["late"] + md["excluded"]
        assert md["eligible"] == md["scored"] + md["abstained"] + md["unavailable"]
        own = [c for c in scorable if forecasts[c]["methods"][m]["status"] == "FORECAST"]
        assert md["scored"] == len(own) and s["methods"][m]["lineage"] == FE.LINEAGE[m]
        ids = paired if m != FE.WANG else [c for c in paired if c in own]
        oracle = [_oracle(forecasts[c]["methods"][m]["p_yes"], states[c]["y"]) for c in ids]
        agg = s["methods"][m]["on_paired"]
        assert agg["n"] == len(ids)
        assert abs(float(agg["brier"]) - sum(o[0] for o in oracle) / len(ids)) < 1e-9
        assert abs(float(agg["log_loss"]) - sum(o[1] for o in oracle) / len(ids)) < 1e-9
    assert s["methods"][FE.WANG]["lineage"] == "MARKET_PRICE_DERIVED"
    ind, mkt = s["methods"][FE.INDEPENDENT]["on_paired"], s["methods"][FE.MARKET]["on_paired"]
    assert abs(float(s["paired_deltas"]["independent_minus_market_brier"]) - (float(ind["brier"]) - float(mkt["brier"]))) < 1e-11
    assert s["lift_status"] == "DIAGNOSTIC_ONLY_NOT_OOS_LIFT_NOT_VALUE"
    # the original FORECAST-01 scoring is untouched and separate
    assert core["upstream"]["original_scoring_snapshot_sha256"] == _sha(_canon(receipt["core"]["scoring"]))


# ------------------------------------------------------------------ R004


def test_learning_calibration_groups_no_value_promotion(learned):
    _f, receipt, _s, out = learned
    diag, rows = out["core"]["diagnostics"], _selected(receipt)
    assert diag["version"] == LF.DIAGNOSTICS_VERSION and diag["outcome_vintage"] == CUTOFF
    assert diag["calibration_edges"] == [str(Decimal(i) / 10) for i in range(11)]
    paired = out["core"]["scoring"]["denominators"]["paired_intersection"]
    for m in (FE.INDEPENDENT, FE.BASE_RATE, FE.MARKET):
        bins = diag["calibration"][m]
        assert len(bins) == 10 and sum(b["n"] for b in bins) == paired
        assert all(b["status"] == ("OK" if b["n"] >= LF.MIN_BIN_N else "INSUFFICIENT_SAMPLE") for b in bins)
    assert sum(b["n"] for b in diag["calibration"][FE.WANG]) == out["core"]["scoring"]["denominators"]["paired_with_wang"]
    for dim, key in (("by_category", "category"), ("by_horizon", "horizon_band")):
        groups = diag[dim]
        assert sorted(g[key] for g in groups) == sorted({r[key] for r in rows.values()})
        assert sum(g["selected"] for g in groups) == len(rows)
        for g in groups:
            assert g["selected"] == sum(g[s.lower()] for s in LF.CASE_STATES)
            assert g["sample_status"] == ("OK" if g["paired"] >= LF.MIN_GROUP_N else "INSUFFICIENT_SAMPLE")
            assert g["independent_minus_market_brier"]["significance_claim"] is False
            assert g["evidence_coverage"]["denominator"] == g["selected"]
    assert any(g["sample_status"] == "INSUFFICIENT_SAMPLE" for g in diag["by_category"])
    # an independent per-group oracle for one sufficient group
    ok = next(g for g in diag["by_category"] if g["sample_status"] == "OK")
    states = {c["case_id"]: c for c in out["core"]["outcomes"]["cases"]}
    f = receipt["core"]["forecasts"]
    ids = [c for c, r in rows.items() if r["category"] == ok["category"] and states[c]["state"] == "SCORABLE"
           and all(f[c]["methods"][m]["status"] == "FORECAST" for m in FE.PRIMARY_METHODS)]
    mean_p = sum(float(f[c]["methods"][FE.INDEPENDENT]["p_yes"]) for c in ids) / len(ids)
    rate = sum(states[c]["y"] for c in ids) / len(ids)
    assert abs(float(ok["independent_calibration_gap"]) - abs(mean_p - rate)) < 1e-9
    assert diag["interpretation"] == "DESCRIPTIVE_POSTHOC_DIAGNOSTIC_NOT_OOS_NOT_QUALIFICATION_NOT_EDGE"
    a, ad = out["core"]["authority"], out["core"]["adoption"]
    assert a["oos_lift_claim"] is a["real_value_verified"] is a["settlement_origin_verified"] is a["wang_is_exogenous"] is False
    assert a["qualification_changed"] is False and ad["value_status"] == "NO_REAL_VALUE_VERIFIED"


# ------------------------------------------------------------------ R005


def test_learning_proposes_future_alpha_research_without_registry_writes(learned, alpha, baseline, tmp_path):  # noqa: F811
    forecast_scratch, receipt, scratch, out = learned
    core, rows = out["core"], _selected(receipt)
    proposals = core["proposals"]
    categories = sorted({r["category"] for r in rows.values()})
    assert sorted(p["evidence_group"]["value"] for p in proposals) == categories
    assert [p["priority_rank"] for p in proposals] == list(range(1, len(proposals) + 1))
    assert proposals == sorted(proposals, key=lambda p: (LF.REASONS.index(p["reasons"][0]), p["evidence_group"]["value"]))
    for p in proposals:
        body = {k: v for k, v in p.items() if k not in ("proposal_id", "priority_rank")}
        assert p["proposal_id"] == LF.PROPOSAL_PREFIX + _sha(_canon(body))  # independent id oracle, no self-hash
        assert p["reasons"] and set(p["reasons"]) <= set(LF.REASONS)
        assert p["source_forecast_receipt_id"] == receipt["receipt_id"]
        assert p["cohort_membership_sha256"] == receipt["core"]["cohort"]["membership_sha256"]
        assert p["authority"].startswith("ADVISORY_ONLY_NOT_CANONICAL_ALPHA_QUEUE")
    by = {p["evidence_group"]["value"]: p for p in proposals}
    cat = {c: rows[c]["category"] for c in rows}
    assert "RESOLUTION_EVIDENCE_MISSING" in by[cat[MISSING_CASE]]["reasons"]
    assert "RESOLUTION_EVIDENCE_MISSING" in by[cat[LATE_CASE]]["reasons"]
    small = next(g for g in core["diagnostics"]["by_category"] if g["sample_status"] != "OK")
    assert "INSUFFICIENT_SAMPLE" in by[small["category"]]["reasons"]
    # read-only Alpha links: cpi (economics) and starship (science, with an episode); others unverified
    assert by["economics"]["alpha_link"]["status"] == LF.ALPHA_LINKED and by["economics"]["alpha_link"]["candidate_ids"]
    sci = by["science"]["alpha_link"]
    assert sci["status"] == LF.ALPHA_LINKED and len(sci["research_episode_ids"]) == 1
    assert all(by[c]["alpha_link"]["status"] == LF.ALPHA_UNVERIFIED for c in by if c not in ("economics", "science"))
    assert all(not by[c]["alpha_link"]["candidate_ids"] for c in by if c not in ("economics", "science"))
    # no registry supplied: every link is ALPHA_LINK_UNVERIFIED, never an invented id
    plain = _core(forecast_scratch, _packet(receipt, _demo_records(receipt)))
    assert {p["alpha_link"]["status"] for p in plain["proposals"]} == {LF.ALPHA_UNVERIFIED}
    # proposals are deterministic and the frozen registry copy equals the caller's unchanged registry
    assert (scratch / "inputs" / "alpha.sqlite3").read_bytes() == Path(alpha).read_bytes()
    a = core["authority"]
    assert a["alpha_registry_written"] is a["research_episode_created"] is a["wp170_evidence_promoted"] is False
    assert a["scheduled"] is False and a["no_canonical_write"] is True and core["write_policy"] == "NO_CANONICAL_WRITE"
    # the module never calls a canonical Alpha/WP170/PIT writer
    source = Path(LF.__file__).read_text(encoding="utf-8") + Path(CLI.__file__).read_text(encoding="utf-8")
    for writer in ("append_alpha_factory_records", "initialize_alpha_factory_registry", "append_experiment",
                   "initialize_experiment_registry", "INSERT", "UPDATE "):
        assert writer not in source


# ------------------------------------------------------------------ R006


def _tamper_copy(scratch, tmp_path, name):
    target = tmp_path / name
    shutil.copytree(scratch, target)
    return target


def test_learning_receipt_cold_verify_hash_chain_and_tamper(learned, baseline, tmp_path, capsys):  # noqa: F811
    forecast_scratch, receipt, scratch, out = learned
    before = _tree(scratch)
    assert CLI.main(["verify", "--scratch-dir", str(scratch)]) == 0
    assert _stdout(capsys) == {"status": "VERIFIED", "failures": [], "receipt_id": out["receipt_id"], "network_attempts": 0}
    assert _tree(scratch) == before  # verify never writes
    assert out["receipt_id"] == LF.RECEIPT_PREFIX + _sha(_canon(out["core"]))
    assert out["core"]["inputs"]["file_sha256"]["outcomes.json"] == _sha((scratch / "inputs" / "outcomes.json").read_bytes())
    assert out["core"]["code_identity"] == CLI.code_identity()

    def edit_receipt(name, fn, expect):
        t = _tamper_copy(scratch, tmp_path, name)
        r = json.loads((t / "receipt.json").read_text(encoding="utf-8"))
        fn(r)
        (t / "receipt.json").write_text(json.dumps(r), encoding="utf-8")
        assert CLI.main(["verify", "--scratch-dir", str(t)]) == 1
        result = _stdout(capsys)
        assert result["status"] == "TAMPER_DETECTED" and expect in result["failures"], result
    edit_receipt("score", lambda r: r["core"]["scoring"]["methods"][FE.MARKET]["on_paired"].update(brier="0.0"),
                 "OUTPUT_MISMATCH:scoring")
    edit_receipt("order", lambda r: r["core"]["proposals"].reverse(), "OUTPUT_MISMATCH:proposals")
    edit_receipt("lineage", lambda r: r["core"]["scoring"]["methods"][FE.WANG].update(lineage="EXOGENOUS"),
                 "OUTPUT_MISMATCH:scoring")
    edit_receipt("time", lambda r: r["core"]["outcomes"].update(learning_cutoff="2030-01-01T00:00:00Z"),
                 "OUTPUT_MISMATCH:outcomes")
    edit_receipt("moved", lambda r: r["core"]["outcomes"]["cases"][0].update(case_id="t-moved"), "OUTPUT_MISMATCH:outcomes")
    edit_receipt("rid", lambda r: r.update(receipt_id=LF.RECEIPT_PREFIX + "0" * 64), "RECEIPT_ID_MISMATCH")
    # changed outcome bytes inside the frozen packet
    t = _tamper_copy(scratch, tmp_path, "outcome")
    packet = json.loads((t / "inputs" / "outcomes.json").read_text(encoding="utf-8"))
    packet["records"][0]["outcome_label"] = "Yes" if packet["records"][0]["outcome_label"] == "No" else "No"
    (t / "inputs" / "outcomes.json").write_text(json.dumps(packet), encoding="utf-8")
    assert CLI.main(["verify", "--scratch-dir", str(t)]) == 1
    assert _stdout(capsys)["status"] == "TAMPER_DETECTED"
    # one byte of the frozen forecast copy (its frozen score receipt) -> upstream verify fails closed
    t = _tamper_copy(scratch, tmp_path, "upstream")
    frozen = t / "inputs" / "forecast" / "receipt.json"
    frozen.write_bytes(frozen.read_bytes().replace(b'"DIAGNOSTIC_ONLY"', b'"DIAGNOSTIC_0NLY"', 1))
    assert CLI.main(["verify", "--scratch-dir", str(t)]) == 1
    assert _stdout(capsys) == {"status": "STOPPED", "reason_code": "FORECAST_VERIFY_FAILED"}
    # foreign forecast receipt id, write-once scratch
    packet = _packet(receipt, _demo_records(receipt), forecast_receipt_id=FE.RECEIPT_PREFIX + "1" * 64)
    code, _, none = _learn(tmp_path, forecast_scratch, packet, "foreign")
    assert code == 1 and none is None and _stdout(capsys)["reason_code"] == "FOREIGN_FORECAST_RECEIPT"
    path = tmp_path / "again.json"
    path.write_text(json.dumps(_packet(receipt, _demo_records(receipt))), encoding="utf-8")
    assert CLI.main(["run", "--forecast-scratch", str(forecast_scratch), "--outcomes", str(path),
                     "--scratch-dir", str(scratch)]) == 1
    assert _stdout(capsys)["reason_code"] == "SCRATCH_NOT_EMPTY" and _tree(scratch) == before


# ------------------------------------------------------------------ R007


def test_learning_negative_matrix_and_zero_authority(baseline, tmp_path, capsys, monkeypatch):  # noqa: F811
    forecast_scratch, receipt = baseline
    rows = _selected(receipt)
    good = [_record(r) for r in rows.values()]

    def stop(packet_or_bytes, expect, name):
        path = tmp_path / f"{name}.json"
        path.write_bytes(packet_or_bytes if isinstance(packet_or_bytes, bytes) else json.dumps(packet_or_bytes).encode())
        code = CLI.main(["run", "--forecast-scratch", str(forecast_scratch), "--outcomes", str(path),
                         "--scratch-dir", str(tmp_path / f"s-{name}")])
        result = _stdout(capsys)
        assert code == 1 and result == {"status": "STOPPED", "reason_code": expect}, (name, result)
        assert not (tmp_path / f"s-{name}" / "receipt.json").exists()
    base = _packet(receipt, good)
    whole_run = [
        ("notdict", [1, 2], "OUTCOMES_JSON_INVALID"),
        ("missing", {k: v for k, v in base.items() if k != "learning_cutoff"}, "OUTCOMES_FIELDS_INVALID"),
        ("unknown", dict(base, extra=1), "OUTCOMES_FIELDS_INVALID"),
        ("schema", dict(base, schema_id="v0"), "OUTCOMES_SCHEMA_INVALID"),
        ("cutnull", dict(base, learning_cutoff=None), "LEARNING_CUTOFF_INVALID"),
        ("cutnaive", dict(base, learning_cutoff="2027-06-30T00:00:00"), "LEARNING_CUTOFF_INVALID"),
        ("label", dict(base, packet_label=""), "PACKET_LABEL_INVALID"),
        ("records-bool", dict(base, records=True), "OUTCOME_RECORDS_INVALID"),
        ("records-empty", dict(base, records=[]), "OUTCOME_RECORDS_INVALID"),
        ("forbidden", dict(base, records=[dict(good[0], order_size="1")]), "FORBIDDEN_FIELD"),
        ("credential", dict(base, api_key="x"), "FORBIDDEN_FIELD"),
        ("secret", dict(base, packet_label="sk-" + "a" * 24), "SECRET_MATERIAL_REJECTED"),
        ("nan", json.dumps(base).replace('"records"', '"nan_probe": NaN, "records"').encode(), "OUTCOMES_JSON_INVALID"),
        ("inf", json.dumps(base).replace('"records"', '"x": Infinity, "records"').encode(), "OUTCOMES_JSON_INVALID"),
        ("dupkey", json.dumps(base).replace('"records"', '"learning_cutoff": "2027-01-01T00:00:00Z", "records"').encode(),
         "OUTCOMES_JSON_INVALID"),
        ("truncated", json.dumps(base).encode()[:-7], "OUTCOMES_JSON_INVALID"),
        ("utf8", b"\xff\xfe" + json.dumps(base).encode(), "OUTCOMES_JSON_INVALID"),
        ("empty", b"", "OUTCOMES_UNREADABLE"),
        ("oversize", b" " * (CLI.MAX_OUTCOMES_BYTES + 1), "OUTCOMES_UNREADABLE"),
    ]
    for name, packet, expect in whole_run:
        stop(packet, expect, name)
    # per-record defects are counted, never a whole-run stop and never scored
    bad_types = [dict(good[0], outcome_label=True), dict(good[1], known_time=1), dict(good[2], resolved_time=None),
                 dict(good[3], local_first_seen_time=1.5), {k: v for k, v in good[4].items() if k != "event_group"},
                 dict(good[5], unknown_field=1), "row", None, dict(good[6], source_content_sha256="A" * 64),
                 dict(good[7], evidence_class="AUTHENTIC")]
    core = _core(forecast_scratch, _packet(receipt, bad_types + good[8:]))
    assert core["outcomes"]["denominators"]["records_refused_by_reason"] == {"RECORD_FIELDS_INVALID": len(bad_types)}
    d = core["outcomes"]["denominators"]
    assert (d["excluded"], d["missing_outcome"]) == (8, 0)  # attributable malformed rows exclude their case
    safe = _core(forecast_scratch, _packet(receipt, good, packet_label="research-review-calibration-outcome-source"))
    assert safe["outcomes"]["denominators"]["scorable"] == len(rows)  # safe research words are not over-blocked
    # path attacks
    good_file = tmp_path / "good.json"
    good_file.write_text(json.dumps(base), encoding="utf-8")
    empty = tmp_path / "not-a-forecast"
    empty.mkdir()
    for argv, expect in (
        (["--outcomes", "relative.json"], "OUTCOMES_UNREADABLE"),
        (["--outcomes", str(REPO_ROOT / "README.md")], "OUTCOMES_UNREADABLE"),
        (["--forecast-scratch", "relative-dir"], "FORECAST_SCRATCH_INVALID"),
        (["--scratch-dir", str(REPO_ROOT / "learn01-scratch")], "SCRATCH_INSIDE_REPOSITORY"),
        (["--scratch-dir", "relative-scratch"], "SCRATCH_INSIDE_REPOSITORY"),
        (["--alpha-registry", str(tmp_path / "absent.sqlite3")], "ALPHA_REGISTRY_UNUSABLE"),
        (["--forecast-scratch", str(tmp_path)], "FORECAST_SCRATCH_INVALID"),  # would contain the output scratch
        (["--forecast-scratch", str(empty)], "FORECAST_VERIFY_FAILED"),
    ):
        args = {"--forecast-scratch": str(forecast_scratch), "--outcomes": str(good_file),
                "--scratch-dir": str(tmp_path / f"p-{len(argv[1])}-{expect}")}
        args.update(dict(zip(argv[::2], argv[1::2])))
        assert CLI.main(["run", *[x for kv in args.items() for x in kv]]) == 1
        assert _stdout(capsys)["reason_code"] == expect, argv
    assert not (REPO_ROOT / "learn01-scratch").exists()
    hard = tmp_path / "hardlink.json"
    os.link(good_file, hard)
    assert CLI.main(["run", "--forecast-scratch", str(forecast_scratch), "--outcomes", str(hard),
                     "--scratch-dir", str(tmp_path / "s-hard")]) == 1
    assert _stdout(capsys)["reason_code"] == "OUTCOMES_UNREADABLE"
    try:
        link = tmp_path / "symlink.json"
        os.symlink(tmp_path / "plain.json", link)
        (tmp_path / "plain.json").write_text(json.dumps(base), encoding="utf-8")
    except (OSError, NotImplementedError):
        link = None  # host forbids unprivileged symlinks; the is_symlink refusal is covered by the shared check
    if link is not None:
        assert CLI.main(["run", "--forecast-scratch", str(forecast_scratch), "--outcomes", str(link),
                         "--scratch-dir", str(tmp_path / "s-sym")]) == 1
        assert _stdout(capsys)["reason_code"] == "OUTCOMES_UNREADABLE"
    # zero network enforced at the CLI boundary, not merely asserted
    real = LF.build_learning_core

    def dial(*args, **kwargs):
        socket.create_connection(("example.invalid", 443), timeout=1)
        return real(*args, **kwargs)
    monkeypatch.setattr(LF, "build_learning_core", dial)
    single = tmp_path / "single-link.json"  # good_file now has a second hard link
    single.write_text(json.dumps(base), encoding="utf-8")
    assert CLI.main(["run", "--forecast-scratch", str(forecast_scratch), "--outcomes", str(single),
                     "--scratch-dir", str(tmp_path / "s-net")]) == 1
    assert _stdout(capsys)["reason_code"] == "NETWORK_ATTEMPT_BLOCKED"
    monkeypatch.setattr(LF, "build_learning_core", real)
    # import audit: stdlib plus native research modules only
    allowed = {"__future__", "collections", "decimal", "json", "re", "argparse", "hashlib", "pathlib", "shutil", "sys",
               "src.data_layer.analytical_research", "tools.alpha"}
    for path in (Path(LF.__file__), Path(CLI.__file__)):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        mods = {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)} | {
            a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
        assert mods <= allowed, (path.name, mods - allowed)
        text = path.read_text(encoding="utf-8").lower()
        for word in ("requests", "urllib", "subprocess", "hermes_runtime", "execution_gateway", "paper_trading",
                     "live_pilot", "scheduler", "private_key"):
            assert word not in text
    a = safe["authority"]
    assert (a["network_calls"], a["provider_calls"], a["capital_usd"]) == (0, 0, "0")
    assert not any(a[k] for k in ("credentials", "strategy", "paper", "orders", "live", "llm_or_hermes", "scheduled",
                                  "pit_written", "alpha_registry_written"))


# ------------------------------------------------------------------ R008


def test_learning_end_to_end_synthetic_then_future_research_handoff(learned, alpha, tmp_path):
    forecast_scratch, receipt, scratch, out = learned
    core = out["core"]
    assert receipt["core"]["corpus_class"] == "SANITIZED_SYNTHETIC"
    assert core["upstream"]["selected"] == len(_selected(receipt)) >= 30
    d = core["outcomes"]["denominators"]
    assert d["selected_cases"] == d["scorable"] + d["missing_outcome"] + d["disputed"] + d["late_after_cutoff"] + d["excluded"]
    assert d["records_offered"] == len(_demo_records(receipt)) == d["records_admitted"]
    states = {c["case_id"]: c for c in core["outcomes"]["cases"]}
    assert states[NEW_LABEL_CASE]["state"] == "SCORABLE"  # outcome first observed after the forecast was frozen
    assert core["scoring"]["lift_status"] == "DIAGNOSTIC_ONLY_NOT_OOS_LIFT_NOT_VALUE"
    assert len(core["proposals"]) == len(core["diagnostics"]["by_category"]) >= 1
    assert core["adoption"] == {"learning_loop": "FUNCTIONAL_LOOP_INTEGRATED_OFFLINE_NOT_VALUE_VERIFIED",
                                "tracked_capability_ids": 36, "capability_status_changes": 0,
                                "provider_lanes": list(LF.PROVIDER_LANES), "provider_lane_status": "UNCHANGED_SIX_OWNER_GATED",
                                "R3-10-WANG": "MARKET_PRICE_DERIVED_NEVER_INDEPENDENT",
                                "value_status": "NO_REAL_VALUE_VERIFIED"}
    assert len(set(LF.PROVIDER_LANES)) == 6
    # the real operator as a separate process: cold verify of the run scratch, no extra files
    before = _tree(scratch)
    result = subprocess.run([sys.executable, "-B", str(REPO_ROOT / "tools" / "alpha" / "run_learning_feedback.py"),
                             "verify", "--scratch-dir", str(scratch)], capture_output=True, text=True, timeout=600,
                            cwd=str(tmp_path))
    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(result.stdout.strip().splitlines()[-1])["status"] == "VERIFIED"
    assert _tree(scratch) == before
    assert sorted(p.name for p in scratch.iterdir()) == ["inputs", "receipt.json"]
