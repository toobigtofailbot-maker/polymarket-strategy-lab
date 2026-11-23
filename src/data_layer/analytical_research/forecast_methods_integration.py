"""Pinned upstream forecast, sampling and benchmark-metric parity over one native forecast cohort (S10-CAP-B1-METHODS-01).

Input is a cold-verified v2 ``forecast_evaluation`` receipt (itself over a cold-verified SRC-01 grounding and, when bound,
a native WP170 registry) plus a caller methods file. Every method below is classified truthfully:

* R3-12 / R3-12-SAMPLER forecastingresearch/forecastbench@e8d3c94 ``question_sampling/_sampling.py``
  (``thin_pool_by_category``, ``stratified_sample_questions``) and ``_binning.py``: stdlib port, including the numpy
  legacy ``RandomState`` MT19937 stream, ``choice(replace=False)`` and pandas ``DataFrame.sample`` order. Exact parity
  with the real pinned callables was demonstrated by executing them locally (MIT); no code is copied.
* R3-10-WANG YichengYang-Ethan/prediction-market-pricing@04b916c ``hierarchical_wang_mle.estimate_mle`` intercept-only:
  the pinned objective (open (0.05, 0.95) price filter, p clip 1e-6, Phi clip 1e-12, lambda bounds (-2, 2)) with a
  deterministic 1-D search in place of scipy L-BFGS-B and the upstream analytic gradient as the convergence check.
  The real callable needs scipy (not installed, install not authorized): BLOCKED, port parity is run evidence only.
* R3-20 Metaculus/metaculus@bfae5fe ``evaluate_forecasts_baseline_spot_forecast`` (binary) and R3-22
  forecastingresearch/forecastbench-sim@27776fc ``CachedForecast`` excess_brier contract: pinned callables executed
  locally to fixed golden values; here independent one-line formulas are compared with native ``score_one``.
* R3-06 gnosis/prediction-market-agent-tooling@817117d ``Benchmarker.calculate_squared_errors``: formula only, the real
  callable needs sklearn/tqdm/web3 market models: BLOCKED. R3-10 external benchmark needs an Odds API key and network,
  R3-01 ForecastBot needs litellm/openai providers, R3-18 metac-bot-template declares no license: all OPEN with zero
  forecasts.

Native consumers actually called: ``forecast_evaluation.score_diagnostic_candidate`` / ``score_one`` / ``resolve_outcome``
/ ``evaluate_history`` / ``load_wp170``, ``experiment_os.membership_hash`` and ``learning_feedback.score_frozen`` /
``_uncertainty`` / ``calibration`` (read-only). Outcomes are read only in the scoring phase.

Posture: research only, stdlib only, read-only, no network, no provider/LLM, no strategy/paper/order/live authority.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime
from decimal import ROUND_HALF_EVEN, Decimal
import json
import math
import random
import re
from statistics import NormalDist

from src.data_layer.analytical_research import experiment_os as EOS
from src.data_layer.analytical_research import forecast_evaluation as FE
from src.data_layer.analytical_research import learning_feedback as LF
from src.data_layer.analytical_research import source_grounding as SG

WP_ID = "S10-CAP-B1-METHODS-01"
METHODS_SCHEMA = "s10-cap-b1-methods01-methods-v1"
RECEIPT_SCHEMA = "s10-cap-b1-methods01-receipt-v1"
RECEIPT_PREFIX = "fcstmeth:sha256:"
CANDIDATE_ID = "wang_upstream_objective_port_v1"
CALLER = ("tools/alpha/run_forecast_methods_integration.py:run -> run_forecast_evaluation.verify -> "
          "forecast_methods_integration.build_methods_core -> forecast_evaluation.score_diagnostic_candidate")
MIN_PAIRED_FOR_OBSERVATION = 30

METHODS_KEYS = {"schema_id", "case_label", "forecast_receipt_id", "sampler", "wang", "provider_methods"}
SAMPLER_KEYS = {"seed", "n_target", "forecast_datetime", "category_map"}
WANG_KEYS = {"lambda_tolerance"}
_TOL_RE = re.compile(r"0\.0*[1-9][0-9]{0,3}")
_ID_RE = FE._ID_RE

ORIENTATION = {"BRIER_SCORE": "LOWER_IS_BETTER", "LOG_LOSS": "LOWER_IS_BETTER",
               "METACULUS_BINARY_BASELINE_SCORE": "HIGHER_IS_BETTER"}
DISPOSITIONS = ("ENG_OFFLINE", "PARITY_FAILED", "OPEN_OWNER_RIGHTS", "BLOCKED")
EXECUTED = "UPSTREAM_CALLABLE_EXECUTED_LOCALLY_GOLDEN_PINNED"
EXECUTED_STUBS = "UPSTREAM_CALLABLE_EXECUTED_LOCALLY_UNUSED_IMPORTS_STUBBED_GOLDEN_PINNED"
PORT_ONLY = "SOURCE_PORT_UPSTREAM_NOT_EXECUTED"
NOT_IMPLEMENTED = "NOT_IMPLEMENTED_ZERO_FORECASTS"


def _pin(capability: str) -> dict:
    return next(p for p in FE.SOURCE_PINS if p["capability"] == capability)


def _entry(capability, callable_, method_class, disposition, cause, native_consumer):
    pin = _pin(capability)
    return {"capability": capability, "repository": pin["repository"], "commit": pin["commit"], "file": pin["file"],
            "license": pin["license"], "callable": callable_, "method_class": method_class, "disposition": disposition,
            "cause": cause, "native_consumer": native_consumer}


# The nine touched IDs. Repository/commit/file/license are read from the unchanged native FE.SOURCE_PINS register.
REGISTER = (
    _entry("R3-01", "ForecastBot._run_individual_question/_aggregate_predictions", NOT_IMPLEMENTED, "BLOCKED",
           "DEPENDENCY_CLOSURE_NOT_INSTALLED_LITELLM_OPENAI_ASKNEWS_REAL_PROVIDER_COST_UNKNOWN", None),
    _entry("R3-06", "Benchmarker.calculate_squared_errors", PORT_ONLY, "BLOCKED",
           "UPSTREAM_IMPORT_NEEDS_SKLEARN_TQDM_WEB3_MARKET_MODELS_RUN_AGENTS_NEEDS_NETWORK",
           "forecast_evaluation.score_one"),
    _entry("R3-10", "external_benchmark.run_analysis", NOT_IMPLEMENTED, "BLOCKED",
           "REQUIRES_ODDS_API_KEY_CREDENTIAL_NETWORK_AND_NBA_DATA", None),
    _entry("R3-10-WANG", "hierarchical_wang_mle.estimate_mle(intercept-only)", PORT_ONLY, "BLOCKED",
           "UPSTREAM_CALLABLE_NEEDS_SCIPY_NOT_INSTALLED_PORT_PARITY_IS_RUN_EVIDENCE_ONLY",
           "forecast_evaluation.score_diagnostic_candidate"),
    _entry("R3-12", "thin_pool_by_category", EXECUTED, "ENG_OFFLINE", None,
           "experiment_os.TemporalSplitManifest membership read"),
    _entry("R3-12-SAMPLER", "stratified_sample_questions", EXECUTED, "ENG_OFFLINE", None,
           "experiment_os.TemporalSplitManifest membership read"),
    _entry("R3-18", "integrations/main_lightningrod_eval", NOT_IMPLEMENTED, "OPEN_OWNER_RIGHTS",
           "NO_LICENSE_DECLARED_AND_DEPENDS_ON_FORECASTING_TOOLS_LIGHTNINGROD_PROVIDERS", None),
    _entry("R3-20", "evaluate_forecasts_baseline_spot_forecast(binary)", EXECUTED_STUBS, "ENG_OFFLINE", None,
           "forecast_evaluation.score_one"),
    _entry("R3-22", "fbsim_benchmark.adapters.CachedForecast(excess_brier)", EXECUTED, "ENG_OFFLINE", None,
           "forecast_evaluation.score_one"),
)
TOUCHED_IDS = tuple(e["capability"] for e in REGISTER)


def check_register(register: tuple) -> None:
    """The register must match the native pins exactly and never mark an unexecuted or unlicensed method complete."""
    FE._require(tuple(e.get("capability") for e in register) == TOUCHED_IDS, "REGISTER_IDS_INVALID")
    for e in register:
        pin = _pin(e["capability"])
        FE._require(all(e.get(k) == pin[k] for k in ("repository", "commit", "file")), "REGISTER_PIN_MISMATCH")
        FE._require(type(e.get("license")) is str and e["license"] == pin["license"], "REGISTER_LICENSE_MISMATCH")
        FE._require(e.get("disposition") in DISPOSITIONS, "REGISTER_DISPOSITION_INVALID")
        if e["disposition"] == "ENG_OFFLINE":
            FE._require(e.get("method_class") in (EXECUTED, EXECUTED_STUBS) and e["license"] != "NONE_DECLARED"
                        and e.get("native_consumer"), "REGISTER_FALSE_ACCEPTANCE")
        else:
            FE._require(type(e.get("cause")) is str and e["cause"], "REGISTER_CAUSE_MISSING")


# ------------------------------------------------------------------ numpy legacy RandomState(int) on stdlib MT19937


class LegacyMT:
    """``numpy.random.RandomState(seed)`` draws: the same MT19937 generator and ``init_genrand`` seeding, via stdlib."""

    def __init__(self, seed: int):
        FE._require(type(seed) is int and 0 <= seed <= 0xFFFFFFFF, "SAMPLER_SEED_INVALID")
        key, s = [], seed
        for pos in range(624):
            key.append(s)
            s = (1812433253 * (s ^ (s >> 30)) + pos + 1) & 0xFFFFFFFF
        self._r = random.Random()
        self._r.setstate((3, tuple(key) + (624,), None))

    def random_sample(self, n: int) -> list[float]:
        return [self._r.random() for _ in range(n)]  # genrand_res53 == numpy legacy next_double

    def _interval(self, mx: int) -> int:
        mask = mx
        for shift in (1, 2, 4, 8, 16):
            mask |= mask >> shift
        while True:  # masked rejection sampling, as numpy random_interval for max <= 2**32 - 1
            value = self._r.getrandbits(32) & mask
            if value <= mx:
                return value

    def permutation(self, n: int) -> list[int]:
        arr = list(range(n))
        for i in range(n - 1, 0, -1):
            j = self._interval(i)
            arr[i], arr[j] = arr[j], arr[i]
        return arr


# ------------------------------------------------------------------ forecastbench@e8d3c94 sampler port

FB_MARKET_VALUE = ((0.00, 0.01, 0, False), (0.01, 0.10, 0, False), (0.10, 0.20, 0.125, False), (0.20, 0.30, 0.125, False),
                   (0.30, 0.40, 0.125, False), (0.40, 0.50, 0.125, False), (0.50, 0.60, 0.125, False),
                   (0.60, 0.70, 0.125, False), (0.70, 0.80, 0.125, False), (0.80, 0.90, 0.125, True),
                   (0.90, 0.99, 0, False), (0.99, 1.00, 0, False))
FB_TIME_HORIZON = ((0, 7, 0), (8, 25, 0.20), (26, 50, 0.35), (51, 70, 0.20), (71, 90, 0.1), (91, 120, 0.08),
                   (121, 180, 0.05), (181, 365, 0.02), (366, float("inf"), 0))
FB_CATEGORY_WEIGHTS = {"Science & Tech": 1.0, "Healthcare & Biology": 1.0, "Economics & Business": 1.0,
                       "Environment & Energy": 1.0, "Politics & Governance": 1.0, "Arts & Recreation": 1.0,
                       "Security & Defense": 1.0, "Sports": 0.03, "Other": 1.0}


def fb_market_value_bin(value: str | None) -> str:
    if value is None:
        return "unknown"
    val = float(value)
    for lo, hi, _w, inclusive in FB_MARKET_VALUE:
        if (lo <= val <= hi) if inclusive else (lo <= val < hi):
            return f"{lo}-{hi}%"
    return "unknown"


def fb_time_horizon_bin(close: str | None, forecast_dt: datetime) -> str:
    if close is None:
        return "unknown"
    days = (datetime.fromisoformat(close) - forecast_dt).days
    for lo, hi, _w in FB_TIME_HORIZON:
        if lo <= days <= hi:
            return f"{lo}-{hi}d"
    return "unknown"


def fb_bin_weights(pool: list[dict]) -> dict:
    """calculate_bin_weights: product of the two configured weights, normalised in first-appearance order."""
    mv = {f"{lo}-{hi}%": w for lo, hi, w, _ in FB_MARKET_VALUE}
    th = {f"{lo}-{hi}d": w for lo, hi, w in FB_TIME_HORIZON}
    weights: dict[str, float] = {}
    for r in pool:
        if r["composite_bin"] not in weights:
            weights[r["composite_bin"]] = mv.get(r["market_value_bin"], 0) * th.get(r["time_horizon_bin"], 0)
    total = sum(weights.values())
    return {k: v / total for k, v in weights.items()} if total > 0 else weights


def fb_stratified(pool: list[dict], weights: dict, n_target: int, rng: LegacyMT) -> tuple[list[dict], dict]:
    """stratified_sample_questions: largest-remainder quota, shortage fill, per-bin DataFrame.sample order."""
    if not pool or n_target == 0:
        return [], {}
    weighted = [r for r in pool if weights[r["composite_bin"]] > 0]
    FE._require(bool(weighted), "SAMPLER_NO_WEIGHTED_ROWS")
    available: dict[str, int] = {}
    for r in weighted:
        available[r["composite_bin"]] = available.get(r["composite_bin"], 0) + 1
    frac = {b: n_target * weights[b] for b in available}
    quota = {b: min(int(frac[b]), available[b]) for b in available}
    for b in sorted(quota, key=lambda b: (frac[b] % 1, weights[b]), reverse=True):
        if sum(quota.values()) == n_target:
            break
        if quota[b] < available[b]:
            quota[b] += 1
    shortage = n_target - sum(quota.values())
    if shortage > 0:
        for b in sorted(quota, key=lambda b: weights[b], reverse=True):
            add = min(shortage, available[b] - quota[b])
            quota[b] += add
            shortage -= add
            if shortage == 0:
                break
    out = []
    for b, n in quota.items():
        if n > 0:
            members = [r for r in weighted if r["composite_bin"] == b]
            out.extend(members[i] for i in rng.permutation(len(members))[:n])  # legacy choice(replace=False)
    FE._require(bool(out), "SAMPLER_NO_RESULT")
    return out, {b: {"available": available[b], "selected": quota[b], "weight": repr(weights[b])} for b in available}


def sample_forecastbench(frame: list[dict], sampler: dict) -> dict:
    """thin_pool_by_category -> add_bin_columns -> composite bins -> weights -> stratified sample (fixed seed).

    ``frame`` is label-free native rows; a native category outside the predeclared map is NaN upstream and so dropped."""
    ids = [r["case_id"] for r in frame]
    FE._require(len(ids) == len(set(ids)), "DUPLICATE_SAMPLE")
    forecast_dt = datetime.fromisoformat(FE._utc(sampler["forecast_datetime"]).replace("Z", "+00:00"))
    rng = LegacyMT(sampler["seed"])
    draws = rng.random_sample(len(frame))
    pool, dropped = [], Counter()
    for r, draw in zip(frame, draws):
        category = sampler["category_map"].get(r["category"])
        if category not in FB_CATEGORY_WEIGHTS:
            dropped["CATEGORY_NOT_IN_UPSTREAM_TAXONOMY"] += 1
        elif not draw < FB_CATEGORY_WEIGHTS[category]:
            dropped["CATEGORY_THINNED"] += 1
        else:
            mv = fb_market_value_bin(r["market_price"])
            th = fb_time_horizon_bin(r["resolution_date"], forecast_dt)
            pool.append({"case_id": r["case_id"], "market_value_bin": mv, "time_horizon_bin": th,
                         "composite_bin": f"{mv}_{th}"})
    weights = fb_bin_weights(pool)
    selected, bins = fb_stratified(pool, weights, sampler["n_target"], rng)
    selected_ids = [r["case_id"] for r in selected]
    FE._require(len(selected_ids) == len(set(selected_ids)), "DUPLICATE_SAMPLE")
    zero = sum(1 for r in pool if weights[r["composite_bin"]] == 0)
    return {
        "capabilities": ["R3-12", "R3-12-SAMPLER"], "input_order": "native frozen target order",
        "selected_case_ids_in_upstream_order": selected_ids,
        "membership_sha256": SG.sha256_hex(SG.canonical_bytes(sorted(selected_ids))),
        "bins": dict(sorted(bins.items())),
        "denominators": {"frame": len(frame), "thinning_dropped_by_reason": dict(sorted(dropped.items())),
                         "pool_after_thinning": len(pool), "zero_weight_or_unknown_bin": zero,
                         "weighted": len(pool) - zero, "requested": sampler["n_target"], "selected": len(selected_ids)},
    }


def wp170_membership_read(selected_ids: list[str], forecast_core: dict, native: dict | None) -> dict:
    """Read the sampled ids' native ResearchSample binding and TemporalSplitManifest role (never a release or write)."""
    membership = forecast_core["wp170"].get("membership")
    if native is None or membership is None:
        return {"status": "WP170_UNBOUND_NO_MEMBERSHIP_READ", "selected": len(selected_ids)}
    split = native["split"]
    roles = {sid: role for role, field in FE.SPLIT_SETS for sid in getattr(split, field)}
    entries = {e["case_id"]: e for e in membership["entries"]}
    by_status, by_role, sample_ids = Counter(), Counter(), []
    for case_id in selected_ids:
        e = entries.get(case_id)
        status = "NOT_IN_BINDING_FRAME" if e is None else e["status"]
        by_status[status] += 1
        if status == "MAPPED":
            FE._require(roles.get(e["sample_id"]) == e["role"], "WP170_ROLE_MISMATCH")  # receipt vs native split
            by_role[e["role"]] += 1
            sample_ids.append(e["sample_id"])
    return {"status": "WP170_MEMBERSHIP_READ_ONLY", "split_assignment_id": split.split_assignment_id,
            "native_membership_hashes": {role: EOS.membership_hash(split, role) for role in EOS.RESEARCH_ROLES},
            "receipt_membership_hashes_match": membership["membership_hashes"] == {
                role: EOS.membership_hash(split, role) for role in EOS.RESEARCH_ROLES},
            "selected_by_binding_status": dict(sorted(by_status.items())),
            "selected_mapped_by_role": {role: by_role.get(role, 0) for role in EOS.RESEARCH_ROLES},
            "selected_sample_ids_sha256": SG.sha256_hex(SG.canonical_bytes(sorted(sample_ids))),
            "oos_release": "NOT_RELEASED", "run_evidence_receipt": None}


# ------------------------------------------------------------------ pricing@04b916c intercept-only Wang MLE port

UP_PRICE_OPEN = (Decimal("0.05"), Decimal("0.95"))
UP_P_CLIP, UP_PHI_CLIP, UP_BOUNDS, UP_START = 1e-6, 1e-12, (-2.0, 2.0), 0.176
UP_ITERATIONS = 200
_N = NormalDist()


def _z(p: Decimal) -> float:
    return _N.inv_cdf(min(max(float(p), UP_P_CLIP), 1 - UP_P_CLIP))


def upstream_nll(lam: float, z: list[float], y: list[int]) -> float:
    total = 0.0
    for zi, yi in zip(z, y):
        phi = min(max(_N.cdf(zi - lam), UP_PHI_CLIP), 1 - UP_PHI_CLIP)
        total -= math.log(phi) if yi else math.log(1 - phi)
    return round(total, 9)  # stable comparisons across libm builds


def upstream_gradient(lam: float, z: list[float], y: list[int]) -> float:
    """d NLL / d lambda from the upstream analytic score (offset model eta = z - lambda)."""
    total = 0.0
    for zi, yi in zip(z, y):
        eta = zi - lam
        phi, big = _N.pdf(eta), min(max(_N.cdf(eta), UP_PHI_CLIP), 1 - UP_PHI_CLIP)
        total += yi * phi / big - (1 - yi) * phi / (1 - big)
    return total


def fit_upstream_wang(prices: list[Decimal], outcomes: list[int]) -> dict:
    z = [_z(p) for p in prices]
    lo, hi = UP_BOUNDS
    ratio = (math.sqrt(5) - 1) / 2
    for _ in range(UP_ITERATIONS):
        a, b = hi - ratio * (hi - lo), lo + ratio * (hi - lo)
        if upstream_nll(a, z, outcomes) <= upstream_nll(b, z, outcomes):
            hi = b
        else:
            lo = a
    lam = round((lo + hi) / 2, 9)
    grad = upstream_gradient(lam, z, outcomes)
    at_bound = min(abs(lam - UP_BOUNDS[0]), abs(lam - UP_BOUNDS[1])) < 1e-6
    return {"lambda": lam, "gradient_per_obs": grad / len(z), "at_bound": at_bound,
            "converged": at_bound or abs(grad / len(z)) <= 1e-5}


def wang_candidates(rows: list[dict], valid_history: list[dict], method: dict, native_forecasts: dict,
                    tolerance: Decimal) -> dict:
    """Per selected case: upstream-objective lambda on train-only history vs the native fit_wang lambda.

    Uses label-free target rows and pre-decision training history only; target outcomes are never an input."""
    groups = {r["event_group"] for r in rows if "event_group" in r}
    FE._require(not {h["event_group"] for h in valid_history} & groups, "TRAIN_TEST_OVERLAP")
    p_yes, cases, parity = {}, {}, Counter()
    for r in (r for r in rows if r["status"] == "SELECTED"):
        c = r["case_id"]
        training, _ = FE._training(valid_history, r["decision_time"])
        priced = [h for h in training if h["price"] is not None and UP_PRICE_OPEN[0] < h["price"] < UP_PRICE_OPEN[1]]
        native = native_forecasts[c]["methods"][FE.WANG]
        entry = {"training_n": len(priced), "training_ids_sha256": SG.sha256_hex(SG.canonical_bytes(
            sorted(h["history_id"] for h in priced))), "native_lambda": native["lambda"]}
        cases[c] = entry
        if len(priced) < method["wang_min_training_n"]:
            p_yes[c] = None
            entry.update(status="ABSTAIN", reason="ABSTAIN_NO_TRAINING", parity="NOT_COMPARABLE_NATIVE_OR_PORT_UNFIT")
            parity[entry["parity"]] += 1
            continue
        fit = fit_upstream_wang([h["price"] for h in priced], [h["outcome"] for h in priced])
        FE._require(fit["converged"], "WANG_PORT_NOT_CONVERGED")
        entry.update(port_lambda=f"{fit['lambda']:.9f}", port_at_bound=fit["at_bound"],
                     gradient_per_obs=f"{fit['gradient_per_obs']:.3e}")
        if native["lambda"] is None:
            entry["parity"] = "NOT_COMPARABLE_NATIVE_OR_PORT_UNFIT"
        else:
            reasons = []
            if entry["training_ids_sha256"] != native["training"]["training_ids_sha256"]:
                reasons.append("TRAINING_SET_DIFFERS_OPEN_VS_CLOSED_PRICE_RANGE")
            if native["lambda_at_bound"]:
                reasons.append("NATIVE_LAMBDA_AT_NARROWER_BOUND")
            if abs(Decimal(entry["port_lambda"]) - Decimal(native["lambda"])) > tolerance:
                reasons.append("LAMBDA_OUTSIDE_TOLERANCE")
            entry["parity"] = "PARITY_FAILED" if reasons else "MATCH"
            entry["parity_reasons"] = reasons
        parity[entry["parity"]] += 1
        if r["market_price"] is None:
            p_yes[c] = None
            entry.update(status="UNAVAILABLE", reason="BASELINE_UNAVAILABLE:" + r["price_reason"])
            continue
        value = _N.cdf(_z(Decimal(r["market_price"])) - fit["lambda"])
        FE._require(math.isfinite(value) and 0 <= value <= 1, "CANDIDATE_PROBABILITY_INVALID")
        p_yes[c] = format(Decimal(repr(value)).quantize(FE.Q12, rounding=ROUND_HALF_EVEN), "f")  # fixed point, 12 dp
        entry.update(status="FORECAST", reason=None)
    return {"capability": "R3-10-WANG", "method_id": CANDIDATE_ID, "lineage": "MARKET_PRICE_DERIVED",
            "lambda_tolerance": str(tolerance), "parity_counts": dict(sorted(parity.items())),
            "objective": {"price_open_interval": [str(b) for b in UP_PRICE_OPEN], "p_clip": str(UP_P_CLIP),
                          "phi_clip": str(UP_PHI_CLIP), "lambda_bounds": [str(b) for b in UP_BOUNDS],
                          "upstream_optimizer": "scipy L-BFGS-B from 0.176 (not executed)",
                          "port_optimizer": f"golden-section {UP_ITERATIONS} iterations + upstream gradient check"},
            "native_parameterization": {"price_closed_interval": [str(b) for b in FE.WANG_PRICE_RANGE],
                                        "lambda_bounds": [str(b) for b in FE.WANG_LAMBDA_BOUNDS]},
            "cases": cases, "p_yes": p_yes}


# ------------------------------------------------------------------ three binary metric sources (formulas only)


def metaculus_binary_baseline(p: Decimal, y: int) -> float:
    """score_math binary spot baseline: 100 * ln(pmf[y] * 2) / ln 2 (no clip; -inf at a wrong certainty)."""
    q = float(p) if y == 1 else 1 - float(p)
    return -math.inf if q == 0 else 100 * math.log(q * 2) / math.log(2)


def fbsim_excess_brier(forecast: object, truth: object) -> float:
    """CachedForecast excess_brier contract: finite non-bool numbers in [0, 1], else rejected."""
    ok = all(isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x) and 0 <= x <= 1
             for x in (forecast, truth))
    FE._require(ok, "FBSIM_RECORD_REJECTED")
    return (forecast - truth) ** 2


def gnosis_binary_squared_errors(p: Decimal, y: int) -> Decimal:
    """calculate_squared_errors over both binary outcomes against a resolved 0/1 market: 2 * (p - y)^2."""
    return (p - y) ** 2 + ((1 - p) - (1 - y)) ** 2


def metric_parity(scoring: dict, p_yes: dict) -> dict:
    """Each source metric on the candidate-paired cases vs native score_one, with explicit divergence counts."""
    out = {"R3-20": Counter(), "R3-22": Counter(), "R3-06": Counter()}
    for c, per in scoring["per_case"].items():
        y = scoring["labels"][c]
        p = Decimal(p_yes[c])
        native = per[CANDIDATE_ID]
        mc = metaculus_binary_baseline(p, y)
        if math.isinf(mc):
            out["R3-20"]["BOUNDARY_DIVERGENCE_NATIVE_CLIPPED"] += 1
        else:
            out["R3-20"]["MATCH" if abs(Decimal(repr(mc)) - Decimal(native["baseline_score"])) <= Decimal("1e-6")
                         else "MISMATCH"] += 1
        brier = Decimal(native["brier"])
        out["R3-22"]["MATCH" if abs(Decimal(repr(fbsim_excess_brier(float(p), float(y)))) - brier) <= Decimal("1e-9")
                     else "MISMATCH"] += 1
        out["R3-06"]["MATCH" if abs(gnosis_binary_squared_errors(p, y) - 2 * brier) <= Decimal("1e-9")
                     else "MISMATCH"] += 1
    notes = {"R3-20": "native score_one clips at 1e-12; upstream is unclipped",
             "R3-22": "excess_brier against a 0/1 truth equals native Brier",
             "R3-06": "upstream sums both outcomes (2 x Brier) and _compute_mse returns a SUM, not a mean"}
    return {k: {"n": sum(v.values()), "counts": dict(sorted(v.items())), "note": notes[k]} for k, v in out.items()}


# ------------------------------------------------------------------ paired comparison (no false lift)


def paired_comparison(scoring: dict, corpus_class: str) -> dict:
    paired = sorted(scoring["per_case"])
    out = {"orientation": dict(ORIENTATION), "paired_case_ids_sha256": scoring["paired_case_ids_sha256"],
           "n_paired": len(paired), "abstained_or_missing": scoring["denominators"]["candidate_missing"]}
    for ref in (FE.WANG, FE.MARKET):
        for metric in ("brier", "log_loss"):
            diffs = [Decimal(scoring["per_case"][c][CANDIDATE_ID][metric]) - Decimal(scoring["per_case"][c][ref][metric])
                     for c in paired]
            out[f"candidate_minus_{ref}_{metric}"] = LF._uncertainty(diffs)
    d = out[f"candidate_minus_{FE.WANG}_brier"]
    if not paired:
        status = "NO_PAIRED_CASES"
    elif corpus_class == "SANITIZED_SYNTHETIC":
        status = "INCONCLUSIVE_SYNTHETIC_LABELS_NOT_VALUE"
    elif len(paired) < MIN_PAIRED_FOR_OBSERVATION or d["standard_error"] is None:
        status = "INCONCLUSIVE_INSUFFICIENT_PAIRED"
    elif Decimal(d["mean"]) + 2 * Decimal(d["standard_error"]) < 0:
        status = "LOCAL_OBSERVATION_UNREVIEWED_NOT_VALUE"
    else:
        status = "NO_LIFT"
    out["lift_status"] = status
    out["value_claim"] = False
    return out


# ------------------------------------------------------------------ methods file + receipt core


def validate_methods(methods: object) -> None:
    FE._require(isinstance(methods, dict), "METHODS_JSON_INVALID")
    FE._scan_forbidden(methods)
    FE._require(set(methods) == METHODS_KEYS, "METHODS_FIELDS_INVALID")
    FE._require(methods["schema_id"] == METHODS_SCHEMA, "METHODS_SCHEMA_INVALID")
    FE._require(type(methods["case_label"]) is str and _ID_RE.fullmatch(methods["case_label"]) is not None,
                "METHODS_FIELDS_INVALID")
    FE._require(type(methods["forecast_receipt_id"]) is str and re.fullmatch(re.escape(FE.RECEIPT_PREFIX) + "[0-9a-f]{64}",
                methods["forecast_receipt_id"]) is not None, "FORECAST_RECEIPT_ID_INVALID")
    # Provider-backed methods (ForecastBot, LightningRod) have no spend authority and an unknown model cost.
    FE._require(methods["provider_methods"] == [], "PROVIDER_EXECUTION_NOT_AUTHORIZED_COST_UNKNOWN")
    s = methods["sampler"]
    FE._require(type(s) is dict and set(s) == SAMPLER_KEYS and type(s["seed"]) is int and 0 <= s["seed"] <= 0xFFFFFFFF
                and FE._int(s["n_target"], 0, FE.MAX_ITEMS) and FE._utc(s["forecast_datetime"]) is not None
                and type(s["category_map"]) is dict and len(s["category_map"]) <= 64
                and all(type(k) is str and v in FB_CATEGORY_WEIGHTS for k, v in s["category_map"].items()),
                "SAMPLER_INVALID")
    w = methods["wang"]
    FE._require(type(w) is dict and set(w) == WANG_KEYS and type(w["lambda_tolerance"]) is str
                and _TOL_RE.fullmatch(w["lambda_tolerance"]) is not None, "WANG_INVALID")


def build_methods_core(forecast_receipt: dict, frozen_cases: dict, methods: dict, wp170_native: dict | None,
                       code_identity: str, input_hashes: dict, register: tuple = REGISTER) -> dict:
    """forecast receipt (cold-verified by the caller) -> sampler / Wang / metric parity -> native scorers -> core."""
    validate_methods(methods)
    check_register(register)
    core = forecast_receipt["core"]
    FE._require(core["schema_id"] == FE.RECEIPT_SCHEMA, "FORECAST_RECEIPT_SCHEMA_UNSUPPORTED")
    FE._require(forecast_receipt["receipt_id"] == methods["forecast_receipt_id"], "SOURCE_RECEIPT_MISMATCH")
    rows = core["targets"]
    frame = [r for r in rows if "stratum" in r]  # native event-group-deduplicated sampling frame, label-free
    fdt = FE._utc(methods["sampler"]["forecast_datetime"])
    FE._require(FE._key(fdt) >= FE._key(core["source_grounding"]["as_of"]), "SAMPLER_CLOCK_BEFORE_GROUNDING")
    FE._require(all(FE._key(fdt) <= FE._key(r["decision_time"]) for r in frame), "SAMPLER_CLOCK_AFTER_DECISION")
    # ---- method phase: label-free target rows + pre-decision training history only
    sampled = sample_forecastbench(frame, methods["sampler"])
    native_selected = core["cohort"]["selected_case_ids"]
    fb_ids = set(sampled["selected_case_ids_in_upstream_order"])
    sampled["native_sampler_comparison"] = {
        "status": "NATIVE_SHA256_DRAW_AND_STRATA_DIFFER_FROM_UPSTREAM_NOT_EQUATED", "native_selected": len(native_selected),
        "overlap": len(fb_ids & set(native_selected)), "upstream_only": len(fb_ids - set(native_selected)),
        "native_only": len(set(native_selected) - fb_ids), "native_membership_sha256": core["cohort"]["membership_sha256"]}
    sampled["wp170"] = wp170_membership_read(sampled["selected_case_ids_in_upstream_order"], core, wp170_native)
    _, valid_history = FE.evaluate_history(frozen_cases, {r["event_group"] for r in rows if "event_group" in r})
    wang = wang_candidates(rows, valid_history, frozen_cases["method"], core["forecasts"],
                           Decimal(methods["wang"]["lambda_tolerance"]))
    # ---- scoring phase: native outcome gate and scorers
    cases_by_id = {t["case_id"]: t for t in frozen_cases["targets"] if isinstance(t, dict) and type(t.get("case_id")) is str}
    cutoff = FE._utc(frozen_cases["scoring_cutoff"])
    scoring = FE.score_diagnostic_candidate(cases_by_id, rows, core["forecasts"],
                                            {"method_id": CANDIDATE_ID, "lineage": wang["lineage"], "p_yes": wang["p_yes"]},
                                            core["corpus_class"], cutoff)
    FE._require(scoring["orientation"] == ORIENTATION and scoring["scorer"] == "forecast_evaluation.score_one",
                "SCORER_DIRECTION_MISMATCH")
    selected = [r for r in rows if r["status"] == "SELECTED"]
    outcomes = {"cases": []}
    for r in selected:
        y, _reason = FE.resolve_outcome(r, cases_by_id[r["case_id"]]["outcome"], core["corpus_class"], cutoff)
        outcomes["cases"].append({"case_id": r["case_id"], "state": LF.SCORABLE if y is not None else LF.MISSING, "y": y})
    lf_scoring, lf_paired = LF.score_frozen(core["forecasts"], outcomes, {r["case_id"]: r for r in selected})
    FE._require(lf_scoring["denominators"]["paired_intersection"] == core["scoring"]["denominators"]["paired_intersection"],
                "NATIVE_CONSUMER_DISAGREEMENT")
    augmented = {c: {"methods": {CANDIDATE_ID: {"p_yes": wang["p_yes"][c]}}} for c in scoring["per_case"]}
    register_out = []
    for e in register:
        item = dict(e, forecasts_contributed=0)
        if e["capability"] == "R3-10-WANG":
            item.update(forecasts_contributed=scoring["denominators"]["candidate_available"],
                        run_parity_counts=wang["parity_counts"])
        if e["capability"] in ("R3-12", "R3-12-SAMPLER"):
            item.update(frozen_input_n=len(frame), selected_n=len(fb_ids), membership_sha256=sampled["membership_sha256"])
        register_out.append(item)
    out = {
        "schema_id": RECEIPT_SCHEMA, "wp_id": WP_ID, "posture": "RESEARCH_ONLY", "score_status": "DIAGNOSTIC_ONLY",
        "case_label": methods["case_label"], "caller": CALLER, "code_identity": code_identity,
        "forecast_receipt": {"receipt_id": forecast_receipt["receipt_id"], "verify_status": "VERIFIED",
                             "code_identity": core["code_identity"], "corpus_class": core["corpus_class"],
                             "grounding_receipt_id": core["source_grounding"]["receipt_id"],
                             "grounding_as_of": core["source_grounding"]["as_of"],
                             "wp170_status": core["wp170"]["status"]},
        "inputs": {"file_sha256": input_hashes, "methods_sha256": SG.sha256_hex(SG.canonical_bytes(methods)),
                   "frame_case_ids_sha256": SG.sha256_hex(SG.canonical_bytes([r["case_id"] for r in frame])),
                   "outcomes_read_in_method_phase": False},
        "sampler": sampled,
        "wang": {k: v for k, v in wang.items() if k != "p_yes"},
        "candidate_p_yes": wang["p_yes"],
        "scoring": {k: v for k, v in scoring.items() if k != "labels"},
        "metric_parity": metric_parity(scoring, wang["p_yes"]),
        "paired_comparison": paired_comparison(scoring, core["corpus_class"]),
        "learning_feedback_read_only": {
            "scorer": lf_scoring["scorer"], "paired_intersection": lf_scoring["denominators"]["paired_intersection"],
            "paired_case_ids_sha256": lf_scoring["paired_case_ids_sha256"], "lift_status": lf_scoring["lift_status"],
            "candidate_calibration": LF.calibration(augmented, outcomes, CANDIDATE_ID, sorted(scoring["per_case"])),
            "routing": "NOT_PERFORMED_A8_FEEDBACK_ROUTING_IS_B5"},
        "capability_register": register_out,
        "provider_methods": {"R3-01": "EXPLICIT_OPEN_ZERO_FORECASTS", "R3-18": "EXPLICIT_OPEN_ZERO_FORECASTS",
                             "provider_calls": 0, "spend_usd": "0"},
        "program": {"touched_ids": list(TOUCHED_IDS), "other_program_ids": "UNCHANGED_27_OF_36",
                    "a3_real_model_claim": False, "a4_genuine_claim": False, "a8": "DIAGNOSTICS_ONLY"},
        "authority": {"research_only": True, "candidate_is_a3_child_probability": False, "qualification_claim": False,
                      "real_value_verified": False, "wp170_run_evidence_receipt": False, "oos_release": False,
                      "canonical_store_writes": False, "strategy": False, "paper": False, "orders": False,
                      "live": False, "llm_or_hermes": False, "network_calls": 0, "provider_calls": 0,
                      "credentials": False, "capital_usd": "0"},
    }
    return json.loads(SG.canonical_bytes(out))


def finalize_receipt(core: dict) -> dict:
    return {"core": core, "receipt_id": RECEIPT_PREFIX + SG.sha256_hex(SG.canonical_bytes(core))}


def verify_receipt(receipt: object, recomputed_core: dict) -> list[str]:
    """Failure codes only (never input values); empty means verified."""
    if not isinstance(receipt, dict) or set(receipt) - {"non_identity"} != {"core", "receipt_id"} \
            or not isinstance(receipt["core"], dict):
        return ["RECEIPT_SHAPE_INVALID"]
    extra = receipt.get("non_identity", {})
    if not isinstance(extra, dict) or set(extra) - {"note", "total_ms"} or type(extra.get("total_ms", 0)) not in (int, float) \
            or extra.get("note", FE.NON_IDENTITY_NOTE) != FE.NON_IDENTITY_NOTE:
        return ["NON_IDENTITY_INVALID"]
    failures = []
    if receipt["receipt_id"] != RECEIPT_PREFIX + SG.sha256_hex(SG.canonical_bytes(receipt["core"])):
        failures.append("RECEIPT_ID_MISMATCH")
    if receipt["core"] != recomputed_core:
        failures.extend(f"OUTPUT_MISMATCH:{k}" for k in sorted(set(recomputed_core) | set(receipt["core"]))
                        if receipt["core"].get(k) != recomputed_core.get(k))
    return failures
