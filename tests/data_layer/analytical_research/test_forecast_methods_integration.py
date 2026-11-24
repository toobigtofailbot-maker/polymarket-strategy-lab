"""S10-CAP-B1-METHODS-01: pinned upstream sampler / Wang / metric parity consumed by the native forecast scorers.

The corpus is the frozen SANITIZED_SYNTHETIC S10-R3-FORECAST-01 world (real SRC-01 grounding, real native WP170
registry). Golden values below were produced by executing the pinned upstream callables locally (see
docs/forecast_methods_integration_contract.md); CI never fetches or imports upstream code. Setting
POLYMARKET_UPSTREAM_ROOT to a directory holding the pinned checkouts re-runs the live comparisons.
Nothing here is real-world evidence: no value, lift, OOS release or qualification claim.
"""
# ruff: noqa: F811 - pytest fixtures imported from the forecast evaluation tests are re-used as parameters
from __future__ import annotations

import ast
import copy
from decimal import Decimal
import json
import os
from pathlib import Path
import sys

import pytest

from src.data_layer.analytical_research import experiment_os as EOS
from src.data_layer.analytical_research import forecast_evaluation as FE
from src.data_layer.analytical_research import forecast_methods_integration as FMI
from src.data_layer.analytical_research import learning_feedback as LF
from tests.tools.alpha.test_forecast_evaluation import (  # noqa: F401 - module fixtures
    DECISION, _cases, baseline, world,
)
from tests.tools.alpha.test_forecast_wp170_binding import (  # noqa: F401 - module fixtures
    _bound_cases, _run, full_registry, grounding, nm,
)
from tools.alpha import run_forecast_evaluation as FCLI

REPO_ROOT = Path(__file__).resolve().parents[3]
ROADMAP = REPO_ROOT / "docs" / "roadmaps" / "nine_agent_capability_first_20261117"
CATEGORY_MAP = {"politics": "Politics & Governance", "sports": "Sports", "weather": "Environment & Energy",
                "economics": "Economics & Business", "entertainment": "Arts & Recreation", "science": "Science & Tech"}
SEED = 20261123

# numpy.random.RandomState: seed 42 random_sample(3), then permutation(10); seed 2**32-1 choice(25, 7, replace=False)
NUMPY_GOLDEN = {"rs42_random": [0.3745401188473625, 0.9507143064099162, 0.7319939418114051],
                "rs42_perm10": [9, 7, 0, 3, 5, 8, 2, 1, 6, 4], "rsmax_choice": [23, 8, 24, 18, 4, 9, 15]}
# Metaculus/metaculus@bfae5fe evaluate_forecasts_baseline_spot_forecast(binary) and forecastbench-sim@27776fc
# CachedForecast(excess_brier).score(), executed on the pinned files: key "p|y".
METACULUS_GOLDEN = {"0.001|0": 99.85565831303313, "0.001|1": -896.5784284662087, "0.05|1": -332.1928094887362,
                    "0.2|0": 67.80719051126378, "0.37|0": 33.34237337251918, "0.37|1": -43.440282414577496,
                    "0.5|1": 0.0, "0.62|0": -39.592867633113926, "0.62|1": 31.034012061215048,
                    "0.8|1": 67.80719051126378, "0.95|1": 92.5999418556223, "0.999|1": 99.85565831303313}
FBSIM_GOLDEN = {"0.001|0": 1e-06, "0.05|0": 0.0025000000000000005, "0.2|1": 0.6400000000000001, "0.37|0": 0.1369,
                "0.37|1": 0.39690000000000003, "0.5|1": 0.25, "0.62|1": 0.1444, "0.8|1": 0.03999999999999998,
                "0.95|1": 0.0025000000000000044, "0.999|1": 1.0000000000000019e-06}
FBSIM_REJECTED = [("forecast", float("nan")), ("truth", 1.1), ("forecast", True), ("forecast", -0.01)]


def methods_doc(receipt_id: str, **over) -> dict:
    value = {"schema_id": FMI.METHODS_SCHEMA, "case_label": "b1b-synthetic", "forecast_receipt_id": receipt_id,
             "sampler": {"seed": SEED, "n_target": 12, "forecast_datetime": DECISION, "category_map": dict(CATEGORY_MAP)},
             "wang": {"lambda_tolerance": "0.000001"}, "provider_methods": []}
    value.update(over)
    return value


@pytest.fixture(scope="module")
def bound_forecast(world, full_registry, tmp_path_factory):
    """A real v2 forecast receipt bound to the real native WP170 registry (the B1-A/SRC-01 cohort shape)."""
    code, scratch, receipt = _run(tmp_path_factory.mktemp("b1b_forecast"), world, _bound_cases(world, full_registry), "fc")
    assert code == 0 and FCLI.verify(scratch)["status"] == "VERIFIED"
    return scratch, receipt


def _inputs(bound_forecast):
    scratch, receipt = bound_forecast
    frozen = json.loads((scratch / "frozen_cases.json").read_text(encoding="utf-8"))
    _, native = FE.load_wp170(scratch / "inputs" / "wp170.sqlite3", frozen["wp170"]["experiment_id"])
    return receipt, frozen, native


def _core(bound_forecast, methods=None, register=FMI.REGISTER, frozen=None):
    receipt, frozen0, native = _inputs(bound_forecast)
    return FMI.build_methods_core(receipt, frozen or frozen0, methods_doc(receipt["receipt_id"]) if methods is None else methods,
                                  native,
                                  "code:test", {}, register)


def _frame(receipt):
    return [r for r in receipt["core"]["targets"] if "stratum" in r]


def _upstream_root() -> Path | None:
    value = os.environ.get("POLYMARKET_UPSTREAM_ROOT")
    return Path(value) if value else None


# ------------------------------------------------------------------ R001


def test_upstream_pin_api_license_and_call_trace(bound_forecast, monkeypatch):
    FMI.check_register(FMI.REGISTER)
    by_id = {e["capability"]: e for e in FMI.REGISTER}
    assert tuple(by_id) == FMI.TOUCHED_IDS == ("R3-01", "R3-06", "R3-10", "R3-10-WANG", "R3-12", "R3-12-SAMPLER",
                                               "R3-18", "R3-20", "R3-22")
    # pins come from the unchanged native register and match the immutable roadmap source register
    with (ROADMAP / "09_SOURCE_TO_CLAIM_REGISTER.csv").open(encoding="utf-8") as handle:
        register_text = handle.read()
    for e in FMI.REGISTER:
        pin = next(p for p in FE.SOURCE_PINS if p["capability"] == e["capability"])
        assert (e["repository"], e["commit"], e["file"], e["license"]) == (pin["repository"], pin["commit"], pin["file"],
                                                                           pin["license"])
        assert e["commit"] in register_text and len(e["commit"]) == 40
    # truthful method classes: only executed, licensed callables with a native consumer are ENG_OFFLINE
    assert {c for c, e in by_id.items() if e["disposition"] == "ENG_OFFLINE"} == {"R3-12", "R3-12-SAMPLER", "R3-20", "R3-22"}
    assert by_id["R3-20"]["method_class"] == FMI.EXECUTED_STUBS and by_id["R3-12"]["method_class"] == FMI.EXECUTED
    assert {c for c, e in by_id.items() if e["method_class"] == FMI.PORT_ONLY} == {"R3-06", "R3-10-WANG"}
    assert {c for c, e in by_id.items() if e["method_class"] == FMI.NOT_IMPLEMENTED} == {"R3-01", "R3-10", "R3-18"}
    assert by_id["R3-18"]["license"] == "NONE_DECLARED" and by_id["R3-18"]["disposition"] == "OPEN_OWNER_RIGHTS"
    assert all(e["cause"] for e in FMI.REGISTER if e["disposition"] != "ENG_OFFLINE")
    # the numpy legacy RandomState stream is reproduced exactly (values from numpy itself)
    rs = FMI.LegacyMT(42)
    assert rs.random_sample(3) == NUMPY_GOLDEN["rs42_random"] and rs.permutation(10) == NUMPY_GOLDEN["rs42_perm10"]
    assert FMI.LegacyMT(2 ** 32 - 1).permutation(25)[:7] == NUMPY_GOLDEN["rsmax_choice"]
    # executed upstream scorer goldens == independent formulas == native score_one
    for key, value in METACULUS_GOLDEN.items():
        p, y = Decimal(key.split("|")[0]), int(key.split("|")[1])
        assert FMI.metaculus_binary_baseline(p, y) == pytest.approx(value, abs=1e-9)
        assert float(FE.score_one(p, y)["baseline_score"]) == pytest.approx(value, abs=1e-9)
    for key, value in FBSIM_GOLDEN.items():
        p, y = key.split("|")
        assert FMI.fbsim_excess_brier(float(p), float(y)) == value
        assert float(FE.score_one(Decimal(p), int(y))["brier"]) == pytest.approx(value, abs=1e-15)
    # no upstream code imported or copied: the module imports only stdlib and native repo modules
    tree = ast.parse(Path(FMI.__file__).read_text(encoding="utf-8"))
    imported = {a.name.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names} | \
               {n.module.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module}
    assert imported <= {"__future__", "collections", "datetime", "decimal", "json", "math", "random", "re", "statistics",
                        "src"}
    # call trace: every native consumer is genuinely invoked
    calls = []
    for owner, name in ((FE, "score_diagnostic_candidate"), (FE, "score_one"), (FE, "evaluate_history"),
                        (FE, "resolve_outcome"), (LF, "score_frozen"), (LF, "calibration"), (LF, "_uncertainty"),
                        (EOS, "membership_hash")):
        real = getattr(owner, name)
        monkeypatch.setattr(owner, name, lambda *a, _r=real, _n=name, **k: calls.append(_n) or _r(*a, **k))
    core = _core(bound_forecast)
    assert set(calls) >= {"score_diagnostic_candidate", "score_one", "evaluate_history", "resolve_outcome", "score_frozen",
                          "calibration", "_uncertainty", "membership_hash"}
    assert [e["capability"] for e in core["capability_register"]] == list(FMI.TOUCHED_IDS)
    root = _upstream_root()
    if root is not None:  # live: re-run the pinned upstream scorers (needs numpy; never in CI)
        sys.path.insert(0, str(root / "forecastbench-sim" / "packages" / "fbsim-benchmark" / "src"))
        from fbsim_benchmark.adapters import CachedForecast
        for key, value in FBSIM_GOLDEN.items():
            p, y = key.split("|")
            record = dict(schema_version="1", world="starsim", metric="excess_brier", forecast=float(p), truth=float(y))
            assert CachedForecast.parse(record).score() == value


# ------------------------------------------------------------------ R002


def test_native_cohort_and_wp170_identity_bound_before_methods(bound_forecast, capsys):
    receipt, frozen, _native = _inputs(bound_forecast)
    core = _core(bound_forecast)
    fc = receipt["core"]
    assert core["forecast_receipt"] == {"receipt_id": receipt["receipt_id"], "verify_status": "VERIFIED",
                                        "code_identity": fc["code_identity"], "corpus_class": "SANITIZED_SYNTHETIC",
                                        "grounding_receipt_id": fc["source_grounding"]["receipt_id"],
                                        "grounding_as_of": fc["source_grounding"]["as_of"],
                                        "wp170_status": "WP170_REFERENCES_VERIFIED_READ_ONLY_MEMBERSHIP_MAPPED"}
    # the frame is exactly the native event-deduplicated sampling frame, with native market/rule/event identities
    frame = _frame(receipt)
    assert len(frame) == fc["cohort"]["denominators"]["sampling_frame"]
    assert core["inputs"]["frame_case_ids_sha256"] == FE.SG.sha256_hex(FE.SG.canonical_bytes([r["case_id"] for r in frame]))
    assert all(r["rule_content_sha256"] and r["event_group"] and r["question_sha256"] for r in frame)
    w = core["sampler"]["wp170"]
    assert w["status"] == "WP170_MEMBERSHIP_READ_ONLY" and w["receipt_membership_hashes_match"] is True
    assert w["native_membership_hashes"] == fc["wp170"]["membership"]["membership_hashes"]
    assert w["oos_release"] == "NOT_RELEASED" and w["run_evidence_receipt"] is None
    assert core["inputs"]["outcomes_read_in_method_phase"] is False
    # outcomes never reach the method phase: flipping every target outcome changes only scores
    flipped = copy.deepcopy(frozen)
    for t in flipped["targets"]:
        if t["outcome"] is not None:
            t["outcome"]["label"] = "No" if t["outcome"]["label"] == "Yes" else "Yes"
    other = _core(bound_forecast, frozen=flipped)
    assert other["sampler"] == core["sampler"] and other["wang"] == core["wang"]
    assert other["candidate_p_yes"] == core["candidate_p_yes"] and other["scoring"] != core["scoring"]
    # clock refusals: a sampler clock after any decision or before the grounding cutoff stops the run
    for when, code in (("2026-06-02T00:00:01Z", "SAMPLER_CLOCK_AFTER_DECISION"),
                       ("2026-05-01T00:00:00Z", "SAMPLER_CLOCK_BEFORE_GROUNDING")):
        bad = methods_doc(receipt["receipt_id"])
        bad["sampler"]["forecast_datetime"] = when
        with pytest.raises(FE.EvaluationStop, match=code):
            _core(bound_forecast, bad)
    # a different forecast receipt than the verified one is a source mismatch
    with pytest.raises(FE.EvaluationStop, match="SOURCE_RECEIPT_MISMATCH"):
        _core(bound_forecast, methods_doc(FE.RECEIPT_PREFIX + "0" * 64))


# ------------------------------------------------------------------ R003


def test_forecastbench_stratified_sampler_same_seed_native_membership(bound_forecast):
    receipt, _frozen, native = _inputs(bound_forecast)
    core = _core(bound_forecast)
    s = core["sampler"]
    frame = _frame(receipt)
    d = s["denominators"]
    assert d["frame"] == len(frame) and d["requested"] == 12
    thinned = sum(d["thinning_dropped_by_reason"].values())
    assert d["pool_after_thinning"] + thinned == d["frame"]
    assert d["weighted"] + d["zero_weight_or_unknown_bin"] == d["pool_after_thinning"]
    assert d["selected"] == len(s["selected_case_ids_in_upstream_order"]) == min(12, d["weighted"])
    assert d["thinning_dropped_by_reason"]["CATEGORY_NOT_IN_UPSTREAM_TAXONOMY"] == sum(
        1 for r in frame if r["category"] not in CATEGORY_MAP)
    assert sum(b["selected"] for b in s["bins"].values()) == d["selected"]
    assert all(b["selected"] <= b["available"] for b in s["bins"].values())
    # same seed, same input -> same membership; another seed is a different, still exact draw
    assert _core(bound_forecast)["sampler"] == s
    other = methods_doc(receipt["receipt_id"])
    other["sampler"]["seed"] = SEED + 1
    assert _core(bound_forecast, other)["sampler"]["membership_sha256"] != s["membership_sha256"]
    # the native sampler is not silently equated with the upstream one
    cmp_ = s["native_sampler_comparison"]
    assert cmp_["status"] == "NATIVE_SHA256_DRAW_AND_STRATA_DIFFER_FROM_UPSTREAM_NOT_EQUATED"
    assert cmp_["overlap"] + cmp_["upstream_only"] == d["selected"]
    assert cmp_["native_membership_sha256"] == receipt["core"]["cohort"]["membership_sha256"]
    # the selected ids are read against the native TemporalSplitManifest (all fixtures are OUT_OF_SAMPLE)
    w = s["wp170"]
    assert sum(w["selected_by_binding_status"].values()) == d["selected"]
    assert w["selected_mapped_by_role"]["OUT_OF_SAMPLE"] == w["selected_by_binding_status"].get("MAPPED", 0) > 0
    assert w["native_membership_hashes"]["OUT_OF_SAMPLE"] == EOS.membership_hash(native["split"], "OUT_OF_SAMPLE")
    root = _upstream_root()
    if root is not None:  # live: the real pinned forecastbench functions on the same rows and seed
        sys.path.insert(0, str(root / "forecastbench" / "src"))
        import pandas as pd
        from datetime import datetime
        from question_sampling import _binning as B
        from question_sampling import _sampling as S
        df = pd.DataFrame([{"case_id": r["case_id"], "category": CATEGORY_MAP.get(r["category"]),
                            "freeze_datetime_value": r["market_price"] if r["market_price"] is not None else "N/A",
                            "market_info_close_datetime": r["resolution_date"] or "N/A"} for r in frame])
        rs = S._as_random_state(SEED)
        df = S.thin_pool_by_category(df, random_state=rs)
        df = B.calculate_bin_weights(B.create_composite_bins(B.add_bin_columns(
            df, datetime.fromisoformat(DECISION.replace("Z", "+00:00")))))
        live = list(S.stratified_sample_questions(df, 12, random_state=rs)["case_id"])
        assert live == s["selected_case_ids_in_upstream_order"] == GOLDEN_FB_SELECTION
    assert s["selected_case_ids_in_upstream_order"] == GOLDEN_FB_SELECTION


# Real forecastbench@e8d3c94 thin_pool_by_category + stratified_sample_questions on this frame, seed 20261123, n=12.
GOLDEN_FB_SELECTION = ["t-ga-gov", "t-nyc-temp", "t-uk-pm", "t-fr-assembly", "t-shutdown", "t-oh-sen-dem", "t-nyc-rain",
                       "t-fed-cut-sep", "t-cpi", "t-unemployment", "t-gdp", "t-box-office"]


# ------------------------------------------------------------------ R004


def test_upstream_wang_mle_train_only_parity_or_refusal(bound_forecast):
    receipt, frozen, _native = _inputs(bound_forecast)
    core = _core(bound_forecast)
    w = core["wang"]
    forecasts = receipt["core"]["forecasts"]
    assert w["method_id"] == FMI.CANDIDATE_ID and w["lineage"] == "MARKET_PRICE_DERIVED"
    assert w["objective"]["lambda_bounds"] == ["-2.0", "2.0"] and w["native_parameterization"]["lambda_bounds"] == ["-1.0", "1.0"]
    fitted = [c for c, e in w["cases"].items() if "port_lambda" in e]
    assert fitted and w["parity_counts"].get("MATCH", 0) == len(fitted)  # history prices 0.2..0.8: same training set
    for c in fitted:
        e = w["cases"][c]
        assert abs(Decimal(e["port_lambda"]) - Decimal(forecasts[c]["methods"][FE.WANG]["lambda"])) <= Decimal("1e-6")
        assert e["training_ids_sha256"] == forecasts[c]["methods"][FE.WANG]["training"]["training_ids_sha256"]
        assert abs(float(e["gradient_per_obs"])) <= 1e-5  # upstream analytic gradient ~ 0 at the optimum
    # candidate p equals the native Wang transform to within the lambda tolerance effect
    for c in fitted:
        if core["candidate_p_yes"][c] is not None:
            assert abs(Decimal(core["candidate_p_yes"][c]) - Decimal(forecasts[c]["methods"][FE.WANG]["p_yes"])) < Decimal("1e-5")
    # independent check of the port optimum on the pinned objective
    prices = [Decimal(p) for p in ("0.2", "0.35", "0.5", "0.65", "0.8")] * 8
    outcomes = [1 if i % 5 < 2 else 0 for i in range(40)]
    fit = FMI.fit_upstream_wang(prices, outcomes)
    grid = min((FMI.upstream_nll(x / 1000, [FMI._z(p) for p in prices], outcomes), x / 1000) for x in range(-2000, 2001))
    assert fit["converged"] and abs(fit["lambda"] - grid[1]) <= 1e-3
    # a boundary-price training row (exactly 0.05) differs between the native closed and the upstream open range
    edge = copy.deepcopy(frozen)
    for h in edge["history"][:30]:
        h["market_price"] = "0.05"
    edge_core = _core(bound_forecast, frozen=edge)
    reasons = {r for e in edge_core["wang"]["cases"].values() for r in e.get("parity_reasons", [])}
    assert "TRAINING_SET_DIFFERS_OPEN_VS_CLOSED_PRICE_RANGE" in reasons
    assert edge_core["wang"]["parity_counts"].get("PARITY_FAILED", 0) > 0  # mismatch reported, never PASS
    # held-out exclusion: no training row may share an event with an evaluated target
    rows = receipt["core"]["targets"]
    leak = [{"history_id": "x", "event_group": next(r["event_group"] for r in rows if "event_group" in r)}]
    with pytest.raises(FE.EvaluationStop, match="TRAIN_TEST_OVERLAP"):
        FMI.wang_candidates(rows, leak, frozen["method"], forecasts, Decimal("0.000001"))


# ------------------------------------------------------------------ R005


def test_forecastbot_and_metac_template_fake_provider_or_explicit_open(bound_forecast):
    core = _core(bound_forecast)
    reg = {e["capability"]: e for e in core["capability_register"]}
    for cid in ("R3-01", "R3-18"):
        assert reg[cid]["method_class"] == FMI.NOT_IMPLEMENTED and reg[cid]["forecasts_contributed"] == 0
        assert core["provider_methods"][cid] == "EXPLICIT_OPEN_ZERO_FORECASTS"
    assert reg["R3-01"]["disposition"] == "BLOCKED" and "COST_UNKNOWN" in reg["R3-01"]["cause"]
    assert reg["R3-18"]["disposition"] == "OPEN_OWNER_RIGHTS" and "NO_LICENSE" in reg["R3-18"]["cause"]
    assert core["provider_methods"]["provider_calls"] == 0 and core["authority"]["provider_calls"] == 0
    # the only candidate is the market-derived Wang port; no provider-shaped method id reaches the scorer
    assert set(core["scoring"]["methods"]) == set(FE.METHODS) | {FMI.CANDIDATE_ID}
    assert core["authority"]["candidate_is_a3_child_probability"] is False
    # asking for provider execution (unknown model cost, no spend authority) refuses before any method runs
    receipt, *_ = _inputs(bound_forecast)
    with pytest.raises(FE.EvaluationStop, match="PROVIDER_EXECUTION_NOT_AUTHORIZED_COST_UNKNOWN"):
        _core(bound_forecast, methods_doc(receipt["receipt_id"], provider_methods=[{"capability": "R3-01"}]))


# ------------------------------------------------------------------ R007


def test_three_benchmark_scoring_sources_same_cohort_parity(bound_forecast):
    core = _core(bound_forecast)
    scoring, parity = core["scoring"], core["metric_parity"]
    n = scoring["denominators"]["paired_with_all_native"]
    assert n > 0
    for cid in ("R3-20", "R3-22", "R3-06"):
        assert parity[cid]["n"] == n and parity[cid]["counts"].get("MISMATCH", 0) == 0
    assert parity["R3-22"]["counts"]["MATCH"] == parity["R3-06"]["counts"]["MATCH"] == n
    assert "SUM, not a mean" in parity["R3-06"]["note"]
    # the native consumers are the real ones: same cohort as score_cohort and learning_feedback.score_frozen
    receipt, *_ = _inputs(bound_forecast)
    native = receipt["core"]["scoring"]
    assert core["learning_feedback_read_only"]["paired_intersection"] == native["denominators"]["paired_intersection"]
    for m in FE.METHODS:  # candidate-paired native aggregates are recomputable from per-case native scores
        assert scoring["methods"][m]["on_paired"]["n"] == n
    assert len(core["learning_feedback_read_only"]["candidate_calibration"]) == 10
    # forecastbench-sim reject contract and the Metaculus unclipped boundary are explicit
    for field, value in FBSIM_REJECTED:
        args = {"forecast": 0.4, "truth": 0.6, field: value}
        with pytest.raises(FE.EvaluationStop, match="FBSIM_RECORD_REJECTED"):
            FMI.fbsim_excess_brier(args["forecast"], args["truth"])
    assert FMI.metaculus_binary_baseline(Decimal("1"), 0) == float("-inf")
    assert FE.score_one(Decimal("1"), 0)["clipped"] is True
    assert FMI.gnosis_binary_squared_errors(Decimal("0.3"), 1) == 2 * FE.score_one(Decimal("0.3"), 1)["brier"]


# ------------------------------------------------------------------ R009


def test_method_parity_negative_matrix_and_denominators(bound_forecast, monkeypatch):
    receipt, frozen, _native = _inputs(bound_forecast)
    rid = receipt["receipt_id"]

    def refuses(code, methods=None, register=FMI.REGISTER, frozen_=None):
        with pytest.raises(FE.EvaluationStop) as caught:
            _core(bound_forecast, methods, register, frozen_)
        assert str(caught.value) == code
        assert rid not in str(caught.value) and "politics" not in str(caught.value)  # no input echo

    def reg(cid, **over):
        return tuple(dict(e, **over) if e["capability"] == cid else e for e in FMI.REGISTER)
    # unsupported / wrong pin, missing license, false acceptance, changed callable class
    refuses("REGISTER_PIN_MISMATCH", register=reg("R3-12", commit="0" * 40))
    refuses("REGISTER_PIN_MISMATCH", register=reg("R3-20", file="scoring/other.py"))
    refuses("REGISTER_LICENSE_MISMATCH", register=reg("R3-22", license=None))
    refuses("REGISTER_FALSE_ACCEPTANCE", register=reg("R3-18", disposition="ENG_OFFLINE"))
    refuses("REGISTER_FALSE_ACCEPTANCE", register=reg("R3-10-WANG", disposition="ENG_OFFLINE"))
    refuses("REGISTER_DISPOSITION_INVALID", register=reg("R3-01", disposition="VALUE_VERIFIED"))
    refuses("REGISTER_CAUSE_MISSING", register=reg("R3-06", cause=""))
    refuses("REGISTER_IDS_INVALID", register=FMI.REGISTER[:-1])
    # malformed / type / null / empty methods files
    for bad, code in ((methods_doc(rid, extra=1), "METHODS_FIELDS_INVALID"),
                      (dict(methods_doc(rid), schema_id="v9"), "METHODS_SCHEMA_INVALID"),
                      (methods_doc(rid, case_label=None), "METHODS_FIELDS_INVALID"),
                      (methods_doc(rid, forecast_receipt_id="x"), "FORECAST_RECEIPT_ID_INVALID"),
                      (methods_doc(rid, wang={"lambda_tolerance": "NaN"}), "WANG_INVALID"),
                      (methods_doc(rid, wang={}), "WANG_INVALID"),
                      (methods_doc(rid, order_size=1), "FORBIDDEN_FIELD"),
                      (methods_doc(rid, access_token="x"), "FORBIDDEN_FIELD")):
        refuses(code, bad)
    for field, value in (("seed", -1), ("seed", True), ("seed", 2 ** 32), ("n_target", None), ("forecast_datetime", "now"),
                         ("category_map", {"politics": "Not A Category"}), ("category_map", [])):
        bad = methods_doc(rid)
        bad["sampler"][field] = value
        refuses("SAMPLER_INVALID", bad)
    refuses("METHODS_JSON_INVALID", [])
    # duplicate sample, absent / NaN / boundary candidate probability, scorer direction mismatch
    frame = _frame(receipt)
    with pytest.raises(FE.EvaluationStop, match="DUPLICATE_SAMPLE"):
        FMI.sample_forecastbench(frame + frame[:1], methods_doc(rid)["sampler"])
    sel = [r for r in receipt["core"]["targets"] if r["status"] == "SELECTED"]
    cases_by_id = {t["case_id"]: t for t in frozen["targets"]}
    for bad_p in ("nan", "1.5", "-0", "0.1234567890123"):
        cand = {"method_id": "x", "lineage": "L", "p_yes": {c: bad_p for c in receipt["core"]["forecasts"]}}
        with pytest.raises(FE.EvaluationStop, match="CANDIDATE_PROBABILITY_INVALID"):
            FE.score_diagnostic_candidate(cases_by_id, receipt["core"]["targets"], receipt["core"]["forecasts"], cand,
                                          "SANITIZED_SYNTHETIC", FE._utc(frozen["scoring_cutoff"]))
    absent = {"method_id": "x", "lineage": "L", "p_yes": {c: None for c in receipt["core"]["forecasts"]}}
    out = FE.score_diagnostic_candidate(cases_by_id, receipt["core"]["targets"], receipt["core"]["forecasts"], absent,
                                        "SANITIZED_SYNTHETIC", FE._utc(frozen["scoring_cutoff"]))
    assert out["denominators"]["candidate_available"] == 0 == out["denominators"]["paired_with_all_native"]
    assert out["denominators"]["candidate_missing"] == out["denominators"]["scorable"] <= len(sel)
    with pytest.raises(FE.EvaluationStop, match="CANDIDATE_SHAPE_INVALID"):
        FE.score_diagnostic_candidate(cases_by_id, receipt["core"]["targets"], receipt["core"]["forecasts"],
                                      dict(absent, method_id=FE.MARKET), "SANITIZED_SYNTHETIC", FE._utc(frozen["scoring_cutoff"]))
    real = FE.score_diagnostic_candidate
    monkeypatch.setattr(FE, "score_diagnostic_candidate", lambda *a, **k: dict(
        real(*a, **k), orientation={"BRIER_SCORE": "HIGHER_IS_BETTER", "LOG_LOSS": "LOWER_IS_BETTER",
                                    "METACULUS_BINARY_BASELINE_SCORE": "HIGHER_IS_BETTER"}))
    refuses("SCORER_DIRECTION_MISMATCH")
    monkeypatch.setattr(FE, "score_diagnostic_candidate", real)
    # stale / future source: v1 (pre-membership) forecast receipts are not a supported source
    stale = copy.deepcopy(receipt)
    stale["core"]["schema_id"] = FE.LEGACY_RECEIPT_SCHEMA
    with pytest.raises(FE.EvaluationStop, match="FORECAST_RECEIPT_SCHEMA_UNSUPPORTED"):
        FMI.build_methods_core(stale, frozen, methods_doc(rid), None, "code:test", {})
    # accurate offered / admitted / scored / abstained / excluded / paired denominators
    core = _core(bound_forecast)
    sd, cd = core["scoring"]["denominators"], receipt["core"]["cohort"]["denominators"]
    assert sd["selected"] == cd["selected"] and sd["scorable"] + receipt["core"]["scoring"]["denominators"]["not_scorable"] == sd["selected"]
    assert sd["candidate_available"] + sd["candidate_missing"] == sd["scorable"]
    assert sd["paired_with_all_native"] <= sd["candidate_available"]
    abstained = sum(1 for e in core["wang"]["cases"].values() if e["status"] != "FORECAST")
    assert abstained + sum(1 for v in core["candidate_p_yes"].values() if v is not None) == sd["selected"]
    # inapplicable categories, recorded: no trade fee/order/live surface exists in this offline diagnostic
    assert all(core["authority"][k] is False for k in ("orders", "live", "paper", "strategy", "credentials"))


# ------------------------------------------------------------------ R011


def test_paired_native_vs_upstream_no_false_lift(bound_forecast):
    core = _core(bound_forecast)
    pc = core["paired_comparison"]
    assert pc["orientation"] == FMI.ORIENTATION and pc["value_claim"] is False
    assert pc["n_paired"] == core["scoring"]["denominators"]["paired_with_all_native"] > 0
    assert pc["paired_case_ids_sha256"] == core["scoring"]["paired_case_ids_sha256"]
    for key in ("candidate_minus_wang_probit_distortion_v1_brier", "candidate_minus_market_reference_price_v1_log_loss"):
        assert pc[key]["n"] == pc["n_paired"] and pc[key]["significance_claim"] is False
        assert pc[key]["standard_error"] is not None
    # synthetic labels are never lift, even if a score is lower
    assert pc["lift_status"] == "INCONCLUSIVE_SYNTHETIC_LABELS_NOT_VALUE"
    assert core["scoring"]["lift_status"] == "DIAGNOSTIC_CANDIDATE_NOT_VALUE"
    # log loss is the native clipped value
    assert core["scoring"]["log_loss_epsilon"] == str(FE.EPSILON)
    # the same rules on a LOCAL_REAL_PIT-labelled cohort: small n is INCONCLUSIVE, never lift
    scoring = dict(core["scoring"])
    assert FMI.paired_comparison(scoring, "LOCAL_REAL_PIT")["lift_status"] == "INCONCLUSIVE_INSUFFICIENT_PAIRED"
    assert FMI.paired_comparison(dict(scoring, per_case={}, paired_case_ids_sha256="x"),
                                 "LOCAL_REAL_PIT")["lift_status"] == "NO_PAIRED_CASES"
    big = {f"c{i}": {FMI.CANDIDATE_ID: {"brier": "0.2", "log_loss": "0.6"}, FE.WANG: {"brier": "0.2", "log_loss": "0.6"},
                     FE.MARKET: {"brier": "0.2", "log_loss": "0.6"}} for i in range(40)}
    flat = FMI.paired_comparison(dict(scoring, per_case=big), "LOCAL_REAL_PIT")
    assert flat["lift_status"] == "NO_LIFT"  # identical scores are no lift
    noisy = {c: {m: {"brier": str(Decimal("0.2") + (Decimal(i % 2) / 100 if m == FMI.CANDIDATE_ID else 0)),
                     "log_loss": "0.6"} for m in v} for i, (c, v) in enumerate(big.items())}
    assert FMI.paired_comparison(dict(scoring, per_case=noisy), "LOCAL_REAL_PIT")["lift_status"] == "NO_LIFT"  # worse
    better = {c: {m: {"brier": str(Decimal("0.2") - (Decimal(1 + i % 2) / 100 if m == FMI.CANDIDATE_ID else 0)),
                      "log_loss": "0.6"} for m in v} for i, (c, v) in enumerate(big.items())}
    # even a consistently lower real-cohort Brier is only an unreviewed local observation, never value
    assert FMI.paired_comparison(dict(scoring, per_case=better), "LOCAL_REAL_PIT")["lift_status"] ==         "LOCAL_OBSERVATION_UNREVIEWED_NOT_VALUE"
