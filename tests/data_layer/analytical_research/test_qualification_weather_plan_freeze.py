"""S10-QUAL-PLAN-01 weather qualification prospective plan freeze: focused oracles.

The committed plan is a content-addressed analytic commitment only. These tests read two
committed docs files; they access no DATA-02/DATA-03 row and no network, and they never build a
real QualificationCandidate, PreregisteredExperiment, lifecycle record or gate receipt. The
compatibility test resolves the plan with SYNTHETIC mechanical values against the synthetic
S10-QUAL-01 Alpha fixture only.
"""

from __future__ import annotations

import ast
import copy
import hashlib
import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import NormalDist

import pytest

from src.data_layer.analytical_research import experiment_os as eo
from src.data_layer.analytical_research import qualification as q
from tests.data_layer.analytical_research.test_qualification import (
    CANONICAL_BINARY_CANDIDATE_ID,
    af1_pass,
    binary_input,
    build,
    lineage,  # noqa: F401  (pytest fixture)
    manifest,
    ok,
    rejected,
)

ROOT = Path(__file__).resolve().parents[3]
PLAN_DIR = ROOT / "docs" / "qualification_plans" / "S10-QUAL-PLAN-01"
PLAN_PATH = PLAN_DIR / "weather_plan_v1.json"
POWER_PATH = PLAN_DIR / "power_analysis_v1.md"
SPEC_PATH = ROOT / "docs" / "wp_specs" / "S10-QUAL-PLAN-01" / "wp_spec.json"

PLAN_SHA256 = "d24cdc8ac75068b3bf7dc62c4fcf585d7cd381dd9203fac889f028620c4e69da"
OOS_START = "2026-10-15T00:00:00Z"
CAP = "2027-02-12T00:00:00Z"
FREEZE_DEADLINE = "2026-10-14T00:00:00Z"
WX = "wx.ndfd_pop12_max_climate_day_v1"
LEAD = "time.ndfd_lead_hours_v1"
MKT = "mkt.ext_b0_probability_v1"
LABEL = "label.polymarket_nws_cli_rain_yes_v1"

SECTIONS = (
    "lineage", "hypothesis_plan", "feature_plan", "label_plan", "dataset_split_plan",
    "sample_power_plan", "test_family_plan", "forecast_evaluation_plan",
    "execution_feasibility_plan", "forecast_model_spec", "prospective_data_seal",
    "wp170_handoff", "mechanical_resolution_rules",
)
CANDIDATE_SECTIONS = (
    "hypothesis_plan", "feature_plan", "label_plan", "dataset_split_plan", "sample_power_plan",
    "test_family_plan", "forecast_evaluation_plan", "execution_feasibility_plan",
)
# The existing builder's closed keyset for every candidate plan body (qualification.py).
BUILDER_KEYS = {
    "hypothesis_plan": q._HYPOTHESIS_KEYS,
    "feature_plan": q._FEATURE_KEYS,
    "label_plan": q._LABEL_KEYS,
    "dataset_split_plan": q._SPLIT_KEYS,
    "sample_power_plan": q._POWER_KEYS,
    "test_family_plan": q._TEST_FAMILY_KEYS,
    "forecast_evaluation_plan": q._FORECAST_KEYS,
    "execution_feasibility_plan": frozenset(q.EXECUTION_FEASIBILITY_CLASSES),
}
EXPECTED_SECTION_KEYS = {
    "authority": {
        "analytic_commitment_only", "preregistration_authority", "oos_release_authority",
        "creates_preregistered_experiment", "creates_lifecycle_or_oos_release_record",
        "creates_qualification_candidate", "runs_qualification_gate", "creates_data03_data",
        "fits_model", "computes_score", "network", "freeze_time_authority",
        "committer_or_author_timestamp_authority", "freeze_deadline", "freeze_deadline_rule",
        "freeze_window_missed_terminal", "oos_start_movable_after_exposure", "plan_hash_rule",
        "live", "gate_c", "capital_at_risk_usd", "orders",
    },
    "lineage": {
        "alpha_candidate_id", "hypothesis_family_id", "governing_research_episode_id",
        "alpha_registry_head_entry_hash", "af1_gate_receipt_id", "alpha_result_state",
        "alpha_registry_mutated", "provenance_context", "historical_corpus", "controlling_contracts",
    },
    "hypothesis_plan": {"candidate_plan", "mechanical_fields"},
    "feature_plan": {
        "candidate_plan", "mechanical_fields", "feature_definitions", "b2_is_exact_b1_union_added",
        "imputation", "label_value_enters_features",
    },
    "label_plan": {
        "candidate_plan", "mechanical_fields", "yes_threshold_inches", "trace_counts_as_yes",
        "climate_day_rule", "finality_policies", "sources_must_agree",
        "label_finality_deadline_seconds", "label_finality_deadline_exclusion_reason",
        "source_read_exclusions_remain_exclusions", "label_value_enters_b0_or_features",
    },
    "dataset_split_plan": {
        "candidate_plan", "mechanical_fields", "row_definition", "statistical_unit",
        "leakage_group_id_rule", "related_group_id_rule", "market_id_rule",
        "all_rows_of_a_target_date_share_one_role", "historical_allocation",
    },
    "sample_power_plan": {
        "candidate_plan", "mechanical_fields", "power_analysis_doc_path",
        "power_analysis_doc_sha256_lf", "prospective_statistical_unit", "per_date_loss",
        "one_sided_alpha", "target_power", "planning_mde_dz", "planning_rho1", "vif_rule", "vif",
        "oos_target_effective_dates", "development_sample", "corpus_scores_or_effects_used",
    },
    "test_family_plan": {
        "candidate_plan", "mechanical_fields", "comparison_sequence", "sequence_rule", "fwer",
        "per_comparison_one_sided_alpha", "per_date_differential", "null_hypothesis",
        "alternative_hypothesis", "statistic", "statistic_rule", "rejection_rule",
        "zero_variance_rule", "absolute_criterion", "support_rule", "score_computed_in_plan_01",
    },
    "forecast_evaluation_plan": {
        "candidate_plan", "mechanical_fields", "b0_mechanics", "same_row_set_for_b0_b1_b2",
        "secondary_diagnostic", "log_loss_probability_clip_lower",
        "log_loss_probability_clip_upper", "log_loss_diagnostic_only", "reliability_bins",
        "reliability_bin_rule", "murphy_decomposition", "calibration_diagnostic_only",
    },
    "execution_feasibility_plan": {
        "candidate_plan", "mechanical_fields", "class_meanings", "required_captures",
        "supplementary_captures", "expected_states", "available_criteria",
        "data02_current_only_facts_remain_current_only", "backdating_current_evidence",
        "not_applicable_state_used",
    },
    "forecast_model_spec": {
        "model_family", "definitions", "b0", "b1", "b2", "intercept", "interactions",
        "feature_dropping", "alternate_models", "estimation", "objective",
        "penalty_strength_tunable", "fit_rows", "fit_weights", "solver", "fit_failed_consequence",
        "implementation_parity_rule", "selection_role", "selection_diagnostics",
        "selection_causes_refit", "selection_causes_recalibration",
        "selection_causes_feature_or_model_choice", "selection_causes_threshold_change",
        "analytic_change_after_selection", "post_hoc_calibration", "hyperparameter_search",
        "search_space", "randomness", "oos_forecast_rule",
    },
    "prospective_data_seal": {
        "oos_start", "cap", "cap_days_after_oos_start", "freeze_deadline", "data02_dates_status",
        "data03_permitted_actions", "forbidden_exposures_before_wp170_oos_release",
        "permitted_visible_summaries", "eligibility", "exclusion_reason_codes", "membership_seal",
        "terminals",
    },
    "wp170_handoff": {
        "sole_preregistration_and_oos_authority", "plan_01_role", "wp170_changed_by_plan_01",
        "preregistered_at_rule", "preregistered_at_may_equal_plan_freeze_time",
        "creation_provenance_must_bind", "trial_number", "search_space", "parameters_rule",
        "parameters", "random_seeds", "split", "known_later_dependency",
    },
    "mechanical_resolution_rules": {
        "discretion_permitted", "operator_override_permitted", "unresolvable_terminal",
        "candidate_static_fields", "candidate_lineage_fields", "candidate_mechanical_fields",
        "builder_inputs", "rules",
    },
}
SOLVER_KEYS = {
    "method", "modified_score", "hat_diagonal", "step", "initialization", "convergence_tolerance",
    "convergence_rule", "max_iterations", "step_halving", "line_search", "step_cap",
    "fit_failed_rule", "fit_failed_terminal", "fallback", "restart", "model_substitution",
    "alternate_feature_set",
}
MEMBERSHIP_PREIMAGE_KEYS = [
    "cap", "data03_bundle_id", "end_time", "oos_exclusions", "oos_row_ids", "oos_start",
    "oos_target_dates", "plan_01_plan_sha256",
]
FORBIDDEN_EXPOSURES = [
    "LABEL_VALUES", "PREVALENCE", "PER_MARKET_OUTCOMES", "FEATURE_DISTRIBUTIONS",
    "B1_B2_FORECASTS", "BRIER_OR_LOG_LOSS", "MODEL_COEFFICIENTS", "COMPARISON_STATISTICS",
    "ANY_RESULT_DEPENDENT_SUMMARY",
]
PERMITTED_SUMMARIES = [
    "DISCOVERED_INCLUDED_EXCLUDED_COUNTS_BY_CLOSED_REASON",
    "ELIGIBLE_ROW_AND_DATE_COUNTS_PER_CHECKPOINT",
    "B0_AVAILABILITY_COUNTS_AND_MIDPOINT_VS_TRADE_BASIS_COUNTS",
    "COVERAGE_CLASSES",
    "NETWORK_AND_SEED_ACCOUNTING",
    "IDS_AND_HASHES",
    "EXECUTION_TERMS_EVIDENCE_STATES",
]


# ── helpers ──────────────────────────────────────────────────────────────────
def _reject_float(_token):
    raise ValueError("binary float")


def _reject_constant(_token):
    raise ValueError("non-finite constant")


def _strict_pairs(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise ValueError("duplicate key")
        out[key] = value
    return out


def raw_plan() -> bytes:
    return PLAN_PATH.read_bytes()


def load_plan() -> dict:
    return json.loads(
        raw_plan().decode("utf-8"), object_pairs_hook=_strict_pairs,
        parse_float=_reject_float, parse_constant=_reject_constant,
    )


def canonical(value) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False,
    ).encode("utf-8")


def walk(value, path=()):
    yield path, value
    if isinstance(value, dict):
        for key, item in value.items():
            yield from walk(item, path + (key,))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from walk(item, path + (index,))


def utc(text: str) -> datetime:
    return datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


# Synthetic mechanical values, one per closed value type. Never real DATA-02/DATA-03 ids.
SYN_BUNDLE = "data03bundle:sha256:" + "1" * 64
SYN_DATASET_REF = "externaldataset:synthetic-plan01-fixture"
SYN_CUTOFF = "2026-12-20T00:00:00Z"


def synthetic_value(rule_id: str, rule: dict, field: str):
    kind = rule["value_type"]
    if rule_id == "MR04_FEATURE_EVIDENCE_REFS_V1":
        assert kind == "EVIDENCE_ID_LIST_PER_FEATURE_REF"
        return {ref: sorted([SYN_BUNDLE, f"data03featurecol:{ref}"]) for ref in (WX, LEAD, MKT)}
    if rule_id == "MR05_LABEL_EVIDENCE_REFS_V1":
        assert kind == "EVIDENCE_ID_LIST"
        return sorted([SYN_BUNDLE, "data03labelstore:synthetic"])
    if rule_id == "MR06_DATASET_REFS_V1":
        assert kind == "EVIDENCE_ID_LIST"
        return [SYN_DATASET_REF]
    if rule_id == "MR07_FORMATION_START_V1":
        assert kind == "UTC_SECOND"
        return "2026-08-17T12:09:00Z"
    if rule_id == "MR08_SELECTION_START_V1":
        assert kind == "UTC_SECOND"
        return "2026-09-19T12:09:00Z"
    if rule_id == "MR09_END_TIME_V1":
        assert kind == "UTC_SECOND"
        return "2026-12-08T12:09:01Z"
    if rule_id == "MR10_OOS_ROW_COUNT_V1":
        assert kind == "COUNT"
        return 1000
    if rule_id == "MR11_OOS_DATE_COUNT_V1":
        assert kind == "COUNT"
        return 50
    if rule_id == "MR12_EXECUTION_EVIDENCE_STATE_V1":
        assert kind == "EXECUTION_ENTRY"
        states = {"SPREAD_DEPTH": "PARTIAL", "LATENCY": "MISSING", "PARTIAL_FILL": "MISSING"}
        state = states.get(field, "AVAILABLE")
        refs = [] if state == "MISSING" else [f"data03capture:{field.lower()}"]
        return {"state": state, "evidence_reference_ids": refs}
    if rule_id == "MR01_INFORMATION_CUTOFF_V1":
        assert kind == "UTC_SECOND"
        return SYN_CUTOFF
    if rule_id == "MR03_CREATION_PROVENANCE_V1":
        assert kind == "TEXT"
        return ("synthetic S10-QUAL-PLAN-01 compatibility fixture; plan sha256 " + PLAN_SHA256
                + "; oosmembership:sha256:" + "2" * 64)
    raise AssertionError(rule_id)


def resolve(plan: dict, lin) -> dict:
    """Mechanically resolve the frozen plan into a builder input mapping (synthetic values)."""
    rules = plan["mechanical_resolution_rules"]
    value: dict = {}
    for name in CANDIDATE_SECTIONS:
        body = copy.deepcopy(plan[name]["candidate_plan"])
        for field, rule_id in plan[name]["mechanical_fields"].items():
            body[field] = synthetic_value(rule_id, rules["rules"][rule_id], field)
        value[name] = body
    value.update(copy.deepcopy(rules["candidate_static_fields"]))
    for field, rule_id in rules["candidate_mechanical_fields"].items():
        value[field] = synthetic_value(rule_id, rules["rules"][rule_id], field)
    # Synthetic lineage stands in for lineage.* (the real registry is never read here).
    value["alpha_candidate_id"] = lin.candidate.candidate_id
    value["hypothesis_family_id"] = lin.family.hypothesis_family_id
    value["governing_research_episode_id"] = lin.episode.research_episode_id
    return value


def synthetic_manifests():
    return [manifest(cutoff="2026-12-19T00:00:00Z", dataset_refs=(SYN_DATASET_REF,))]


# ── 1-3: closed keysets, canonical bytes, hash stability, no floats ─────────
def test_p01_plan_keysets_are_closed():
    plan = load_plan()
    assert set(plan) == {"schema_id", "schema_version", "wp_id", "plan_version", "authority", *SECTIONS}
    assert plan["schema_id"] == "polymarket-qualification-analytic-plan-freeze"
    assert plan["schema_version"] == "1.0.0"
    assert plan["wp_id"] == "S10-QUAL-PLAN-01"
    assert plan["plan_version"] == "weather_plan_v1"
    for name, keys in EXPECTED_SECTION_KEYS.items():
        assert set(plan[name]) == keys, name
    for name in CANDIDATE_SECTIONS:
        static = set(plan[name]["candidate_plan"])
        mechanical = set(plan[name]["mechanical_fields"])
        assert not static & mechanical, name
        assert static | mechanical == set(BUILDER_KEYS[name]), name
    assert set(plan["forecast_model_spec"]["solver"]) == SOLVER_KEYS
    assert set(plan["feature_plan"]["feature_definitions"]) == {WX, LEAD, MKT}
    assert set(plan["lineage"]["provenance_context"]) == {
        "source_wp", "research_question", "alpha_family_falsifiable_theme",
    }


def test_p02_plan_bytes_are_canonical_and_hash_stable():
    raw = raw_plan()
    plan = load_plan()
    assert raw == canonical(plan)
    assert canonical(json.loads(canonical(plan))) == raw
    assert not raw.endswith(b"\n") and not raw.endswith(b"\r")
    assert raw.isascii()
    raw.decode("utf-8")
    assert hashlib.sha256(raw).hexdigest() == PLAN_SHA256
    # The hash is never inside its own preimage.
    assert PLAN_SHA256.encode() not in raw
    assert plan["authority"]["plan_hash_rule"] == "SHA256_OF_EXACT_FILE_BYTES_HASH_NOT_IN_PREIMAGE"
    # A one-byte semantic change changes the identity.
    mutated = copy.deepcopy(plan)
    mutated["prospective_data_seal"]["oos_start"] = "2026-10-16T00:00:00Z"
    assert hashlib.sha256(canonical(mutated)).hexdigest() != PLAN_SHA256


def test_p02_noncanonical_encodings_are_distinguishable():
    plan = load_plan()
    raw = raw_plan()
    for variant in (
        json.dumps(plan, sort_keys=True).encode(),
        json.dumps(dict(reversed(list(plan.items()))), sort_keys=False, separators=(",", ":")).encode(),
        raw + b"\n",
        json.dumps(plan, sort_keys=True, separators=(",", ":"), indent=1).encode(),
    ):
        assert variant != raw


def test_p03_no_binary_floats_nan_or_infinity():
    text = raw_plan().decode("utf-8")
    for token in ("NaN", "Infinity"):
        assert token not in text
    for path, value in walk(load_plan()):
        assert not isinstance(value, float), path
    with pytest.raises(ValueError):
        json.loads('{"x":0.5}', parse_float=_reject_float)
    with pytest.raises(ValueError):
        json.loads('{"x":NaN}', parse_constant=_reject_constant)


def test_p03_strict_loader_rejects_duplicate_keys():
    with pytest.raises(ValueError):
        json.loads('{"a":1,"a":2}', object_pairs_hook=_strict_pairs)


# ── 4-5: prospective boundary ────────────────────────────────────────────────
def test_p04_oos_start_deadline_and_cap_literals():
    plan = load_plan()
    seal = plan["prospective_data_seal"]
    assert plan["dataset_split_plan"]["candidate_plan"]["oos_start"] == OOS_START
    assert seal["oos_start"] == OOS_START
    assert plan["wp170_handoff"]["split"]["oos_start"] == OOS_START
    assert seal["cap"] == CAP
    assert seal["eligibility"]["row_decision_time_lower_bound"] == OOS_START
    assert seal["eligibility"]["row_decision_time_upper_bound_exclusive"] == CAP
    assert seal["cap_days_after_oos_start"] == 120
    assert utc(CAP) - utc(OOS_START) == timedelta(days=120)
    assert seal["freeze_deadline"] == plan["authority"]["freeze_deadline"] == FREEZE_DEADLINE
    assert utc(OOS_START) - utc(FREEZE_DEADLINE) == timedelta(days=1)
    embargo = plan["dataset_split_plan"]["candidate_plan"]["embargo_seconds"]
    assert embargo == 172800
    assert utc(seal["eligibility"]["wp170_embargo_lower_bound"]) == utc(OOS_START) + timedelta(seconds=embargo)
    authority = plan["authority"]
    assert authority["freeze_time_authority"] == "GITHUB_SERVER_PR_MERGE_TIMESTAMP_ON_MAIN_PLUS_MERGE_COMMIT_SHA"
    assert authority["committer_or_author_timestamp_authority"] is False
    assert authority["freeze_window_missed_terminal"] == "OOS_START_FREEZE_WINDOW_MISSED"
    assert authority["oos_start_movable_after_exposure"] is False


def test_p05_data02_is_permanently_historical_non_oos():
    plan = load_plan()
    corpus = plan["lineage"]["historical_corpus"]
    assert corpus["source_wp"] == "S10-QUAL-DATA-02"
    assert corpus["oos_status"] == "HISTORICAL_NON_OOS"
    assert corpus["oos_status_permanent"] is True
    assert corpus["canonical_pit"] is False
    assert utc(corpus["last_target_date"] + "T00:00:00Z") < utc(OOS_START)
    allocation = plan["dataset_split_plan"]["historical_allocation"]
    assert allocation["historical_status"] == "HISTORICAL_NON_OOS"
    assert allocation["permitted_roles"] == ["FORMATION", "SELECTION"]
    assert plan["prospective_data_seal"]["data02_dates_status"] == "HISTORICAL_NON_OOS_PERMANENT"


# ── 6-8: B0 / features / label ───────────────────────────────────────────────
def test_p06_b0_rule_is_exact():
    plan = load_plan()
    forecast = plan["forecast_evaluation_plan"]
    body = forecast["candidate_plan"]
    assert body["b0_rule"] == q.B0_RULE_EXTERNAL_PIT_MARKET_PROBABILITY_V1
    assert body["b0_parameters"] == {"max_midpoint_spread": "0.1", "max_last_trade_age_seconds": 86400}
    mech = forecast["b0_mechanics"]
    assert "ask - bid, recomputed" in mech["spread_rule"]
    assert "0 <= bid <= ask <= 1" in mech["midpoint_rule"]
    assert "spread <= max_midpoint_spread" in mech["midpoint_rule"]
    assert "max_last_trade_age_seconds" in mech["last_trade_rule"]
    assert mech["unavailable_rule"] == "otherwise B0_UNAVAILABLE"
    assert mech["observability_clock"] == "CAPTURE_TIMESTAMP_RECEIVED"
    assert mech["b0_missing_excludes_row_from"] == ["B0", "B1", "B2"]
    assert mech["b0_missing_exclusion_before_label_access"] is True
    for key in ("imputation", "canonical_pit_relabeling", "backdating_by_last_modified_or_public_available_time"):
        assert mech[key] is False, key
    assert mech["b0_scored_unclipped"] is True
    assert forecast["same_row_set_for_b0_b1_b2"] is True


def test_p07_features_are_exact():
    plan = load_plan()
    body = plan["feature_plan"]["candidate_plan"]
    assert body["feature_refs"] == sorted([WX, LEAD, MKT])
    assert body["feature_source_classes"] == {
        WX: "PUBLIC_NON_MARKET", LEAD: "TIME_ONLY", MKT: "MARKET_EXTERNAL_RECONSTRUCTION",
    }
    forecast = plan["forecast_evaluation_plan"]["candidate_plan"]
    assert forecast["b1_feature_refs"] == sorted([WX, LEAD])
    assert forecast["b2_market_added_feature_refs"] == [MKT]
    assert forecast["b2_feature_refs"] == sorted(set(forecast["b1_feature_refs"]) | {MKT})
    assert plan["feature_plan"]["b2_is_exact_b1_union_added"] is True
    definitions = plan["feature_plan"]["feature_definitions"]
    wx = definitions[WX]
    assert wx["value_rule"].startswith("q = clip(max PoP12_percent / 100")
    assert (wx["clip_lower"], wx["clip_upper"], wx["model_transform"]) == ("0.01", "0.99", "logit(q)")
    lead = definitions[LEAD]
    assert lead["value_rule"].startswith("L = (climate_day_start - vintage_public_available_time) / 24h")
    assert (lead["unit"], lead["model_transform"]) == ("DAYS_OF_24_HOURS", "identity")
    mkt = definitions[MKT]
    assert mkt["model_input_rule"] == "m = clip(B0, 0.001, 0.999)"
    assert (mkt["clip_lower"], mkt["clip_upper"], mkt["model_transform"]) == ("0.001", "0.999", "logit(m)")
    assert [definitions[r]["model_role"] for r in (WX, LEAD, MKT)] == ["B1_AND_B2", "B1_AND_B2", "B2_ADDED"]
    assert plan["feature_plan"]["imputation"] is False
    assert plan["feature_plan"]["label_value_enters_features"] is False
    assert "no imputation" in body["missing_data_policy"]


def test_p08_label_rule_is_exact():
    plan = load_plan()
    label = plan["label_plan"]
    body = label["candidate_plan"]
    assert body["label_ref"] == LABEL
    assert LABEL not in plan["feature_plan"]["candidate_plan"]["feature_refs"]
    assert ">= 0.01 inch" in body["prediction_target"] and "trace does not count" in body["prediction_target"]
    assert label["yes_threshold_inches"] == "0.01"
    assert label["trace_counts_as_yes"] is False
    assert label["climate_day_rule"] == "DATA02_RULE_BOUND_LOCAL_STANDARD_TIME_DAY"
    assert label["sources_must_agree"] == ["GAMMA_FINAL_OUTCOME", "PENDULUMFLOW_V3_MARKET_RESOLVED"]
    assert label["finality_policies"] == sorted(["FIRST_PUBLISHED_FINAL", "LATEST_BEFORE_2359_ET", "LAST_BEFORE_1400_ET"])
    assert label["source_read_exclusions_remain_exclusions"] is True
    assert label["label_value_enters_b0_or_features"] is False
    assert label["label_finality_deadline_seconds"] == 604800
    assert label["label_finality_deadline_exclusion_reason"] in (
        plan["prospective_data_seal"]["exclusion_reason_codes"]["market"]
    )


# ── 9-10: model, solver, no search ───────────────────────────────────────────
def test_p09_forecast_model_and_solver_are_frozen():
    spec = load_plan()["forecast_model_spec"]
    assert spec["model_family"] == "BINARY_LOGISTIC_REGRESSION"
    assert spec["b1"]["formula"] == "p1 = sigmoid(beta0 + beta1*logit(q) + beta2*L)"
    assert spec["b2"]["formula"] == "p2 = sigmoid(gamma0 + gamma1*logit(q) + gamma2*L + gamma3*logit(m))"
    assert spec["b1"]["design_columns"] == ["1", "logit(q)", "L"]
    assert spec["b2"]["design_columns"] == ["1", "logit(q)", "L", "logit(m)"]
    assert spec["b0"] == {"forecast": "B0 value itself, unclipped", "fitted": False}
    assert spec["intercept"] is True
    for key in ("interactions", "feature_dropping", "alternate_models", "penalty_strength_tunable"):
        assert spec[key] is False, key
    assert spec["estimation"] == "FIRTH_JEFFREYS_PRIOR_BIAS_REDUCTION"
    assert "0.5*ln(det(I(beta)))" in spec["objective"]
    assert (spec["fit_rows"], spec["fit_weights"]) == ("FORMATION_EFFECTIVE_ROWS_ONLY", "NONE")
    solver = spec["solver"]
    assert solver["initialization"] == "ALL_ZERO_COEFFICIENTS"
    assert solver["convergence_tolerance"] == "0.0000000001"
    assert float(solver["convergence_tolerance"]) == 1e-10
    assert "max(abs(delta_coefficient)) < convergence_tolerance" in solver["convergence_rule"]
    assert solver["max_iterations"] == 100
    assert solver["fit_failed_terminal"] == "FIT_FAILED"
    for key in ("step_halving", "line_search", "step_cap", "fallback", "restart", "model_substitution",
                "alternate_feature_set"):
        assert solver[key] is False, key
    assert spec["selection_role"] == "DIAGNOSTICS_ONLY"
    for key in ("selection_causes_refit", "selection_causes_recalibration",
                "selection_causes_feature_or_model_choice", "selection_causes_threshold_change"):
        assert spec[key] is False, key
    assert spec["analytic_change_after_selection"] == "INVALIDATES_PLAN_REQUIRES_NEW_FAMILY_TRIAL_AND_FREEZE"


def test_p10_no_open_hyperparameter_or_search_field():
    plan = load_plan()
    spec = plan["forecast_model_spec"]
    assert spec["post_hoc_calibration"] == "NONE"
    assert spec["hyperparameter_search"] == "NONE"
    assert spec["randomness"] == "NONE"
    assert spec["search_space"] == {} and plan["wp170_handoff"]["search_space"] == {}
    search_keys = sorted(
        str(path[-1]) for path, _ in walk(plan)
        if path and isinstance(path[-1], str)
        and {"search", "hyperparameter", "grid", "tuning", "seed", "seeds"} & set(path[-1].split("_"))
    )
    # grid_rule is the NDFD station grid-point binding; line_search is a frozen False solver flag.
    assert search_keys == [
        "grid_rule", "hyperparameter_search", "line_search", "random_seeds", "search_space", "search_space",
    ]
    for path, value in walk(plan):
        if isinstance(value, str):
            assert value not in {"TBD", "TODO", "PLACEHOLDER", "OPERATOR_CHOICE", "TO_BE_DECIDED"}, path


def test_p10_no_placeholder_in_candidate_plans():
    plan = load_plan()
    for name in CANDIDATE_SECTIONS:
        for path, value in walk(plan[name]["candidate_plan"]):
            if isinstance(value, str):
                assert "<" not in value and ">" not in value.replace(">=", "").replace("->", ""), (name, path)


def test_p11_wp170_random_seeds_empty_and_admissible():
    handoff = load_plan()["wp170_handoff"]
    assert handoff["random_seeds"] == []
    assert eo._tuple_int(handoff["random_seeds"]) == ()
    assert eo._canonical_mapping_json(handoff["search_space"]) == "{}"
    parameters = handoff["parameters"]
    assert eo._canonical_mapping_json(parameters) == canonical(parameters).decode("utf-8")
    assert not {k for k in parameters if k.startswith(("beta", "gamma", "coef"))}
    assert handoff["parameters_rule"] == "FROZEN_MODEL_CONSTANTS_ONLY_NEVER_FITTED_COEFFICIENTS"
    assert parameters["max_midpoint_spread"] == "0.1"
    assert parameters["max_last_trade_age_seconds"] == 86400
    assert parameters["convergence_tolerance"] == "0.0000000001"
    assert parameters["max_iterations"] == 100


# ── 11-16: floors, power, test family ────────────────────────────────────────
def test_p12_formation_and_selection_floors():
    allocation = load_plan()["dataset_split_plan"]["historical_allocation"]
    assert allocation["min_structurally_eligible_formation_rows"] == 385
    assert allocation["min_effective_formation_target_dates"] == 20
    assert allocation["selection_rule"] == "LAST_7_ELIGIBLE_HISTORICAL_TARGET_DATES"
    assert allocation["selection_date_count"] == 7
    assert allocation["min_effective_selection_target_dates"] == 5
    assert allocation["formation_precedes_selection"] is True
    assert allocation["epv10_used"] is False
    assert allocation["outcome_or_performance_dependent"] is False
    assert allocation["formation_shortfall_terminal"] == "QUAL_FORMATION_INSUFFICIENT"
    assert allocation["selection_shortfall_terminal"] == "QUAL_SELECTION_INSUFFICIENT"


def test_p13_min_rows_per_role_and_grouping():
    plan = load_plan()
    split = plan["dataset_split_plan"]
    assert split["candidate_plan"]["min_samples_per_role"] == 100
    assert split["historical_allocation"]["min_rows_per_role"] == 100
    assert plan["wp170_handoff"]["split"]["min_samples_per_role"] == 100
    assert split["candidate_plan"]["group_policy"] == "EXCLUSIVE"
    assert split["candidate_plan"]["event_grouping_rule"] == "LEAKAGE_MARKET_RELATED_EXCLUSIVE"
    assert split["candidate_plan"]["purge_rule"] == "PURGE_LABEL_AVAILABILITY_AT_OR_AFTER_NEXT_BOUNDARY"
    assert split["candidate_plan"]["inclusion_policy"] == "DECISION_TIME_HALF_OPEN"
    assert split["leakage_group_id_rule"] == split["related_group_id_rule"] == "target_date"
    assert split["all_rows_of_a_target_date_share_one_role"] is True


def test_p14_oos_target_and_power_plan_recompute():
    plan = load_plan()
    power = plan["sample_power_plan"]
    body = power["candidate_plan"]
    assert body["analysis_unit"] == "target_date"
    assert body["required_independent_group_count"] == 50 == power["oos_target_effective_dates"]
    assert plan["prospective_data_seal"]["eligibility"]["target_effective_dates"] == 50
    assert (body["target_power"], body["significance_level"], body["minimum_detectable_effect"]) == ("0.8", "0.025", "0.5")
    assert (power["planning_rho1"], power["vif_rule"], power["vif"]) == ("0.25", "1 + 2*rho1", "1.5")
    assert power["corpus_scores_or_effects_used"] is False
    normal = NormalDist()
    z_alpha, z_power = normal.inv_cdf(1 - 0.025), normal.inv_cdf(0.8)
    required = (1 + 2 * 0.25) * (((z_alpha + z_power) / 0.5) ** 2 + z_alpha ** 2 / 2)
    assert math.ceil(required) == 50
    development = power["development_sample"]
    assert development["method"] == "RILEY_2020_CRITERION_III_OVERALL_RISK_PRECISION"
    assert math.ceil((1.96 / 0.05) ** 2 * 0.5 * 0.5) == development["required_formation_rows"] == 385
    assert development["epv10_used"] is False
    lf = POWER_PATH.read_bytes().replace(b"\r\n", b"\n")
    assert hashlib.sha256(lf).hexdigest() == power["power_analysis_doc_sha256_lf"]
    assert power["power_analysis_doc_path"] == "docs/qualification_plans/S10-QUAL-PLAN-01/power_analysis_v1.md"
    doc = " ".join(POWER_PATH.read_text(encoding="utf-8").split())
    for text in ("n = ceil(49.9744) = 50", "ceil(384.16) = 385", "EPV10 (events per variable) is **not** used",
                 "Development sufficiency", "OOS comparison power"):
        assert text in doc, text


def test_p15_fixed_sequence_comparison_order():
    family = load_plan()["test_family_plan"]
    assert [(c["order"], c["candidate"], c["comparator"]) for c in family["comparison_sequence"]] == [
        (1, "B2", "B0"), (2, "B2", "B1"), (3, "B1", "B0"),
    ]
    assert family["sequence_rule"] == "FIXED_SEQUENCE_LATER_CONFIRMATORY_ONLY_IF_ALL_PRECEDING_REJECT"
    body = family["candidate_plan"]
    assert (body["correction_policy"], body["family_size"]) == ("FAMILY_TRIAL_COUNT", 3)
    assert "Fixed-sequence one-sided" in body["multiplicity_method"] and "FWER at 0.025" in body["multiplicity_method"]
    assert family["fwer"] == family["per_comparison_one_sided_alpha"] == "0.025"
    assert family["statistic"] == "DIEBOLD_MARIANO_NEWEY_WEST_BARTLETT_LAG1"
    assert "V = gamma_0 + gamma_1" in family["statistic_rule"]
    assert "t_{0.975, n-1}" in family["rejection_rule"]
    assert family["zero_variance_rule"] == "V = 0 does not reject"
    assert family["score_computed_in_plan_01"] is False


def test_p16_brier_primary_logloss_diagnostic_threshold():
    plan = load_plan()
    body = plan["test_family_plan"]["candidate_plan"]
    assert body["primary_metric_name"] == "BRIER_SCORE" == plan["forecast_evaluation_plan"]["candidate_plan"]["primary_proper_score"]
    assert body["primary_metric_direction"] == "LOWER_IS_BETTER"
    assert body["secondary_metric_names"] == ["LOG_LOSS"]
    assert body["acceptance_thresholds"] == {"primary_metric_operator": "LTE", "primary_metric_threshold": "0.25"}
    assert body["baseline_acceptance_rule"] == "CANDIDATE_LTE_BASELINE"
    absolute = plan["test_family_plan"]["absolute_criterion"]
    assert (absolute["forecast"], absolute["operator"], absolute["threshold"]) == ("B2", "LTE", "0.25")
    forecast = plan["forecast_evaluation_plan"]
    assert forecast["secondary_diagnostic"] == "LOG_LOSS" and forecast["log_loss_diagnostic_only"] is True
    assert forecast["reliability_bins"] == 10 and forecast["murphy_decomposition"] is True
    assert forecast["calibration_diagnostic_only"] is True


# ── 17-21: DATA-03 seal, cap, execution evidence, WP170 authority ───────────
def test_p17_data03_forbidden_exposures_exact():
    seal = load_plan()["prospective_data_seal"]
    assert seal["forbidden_exposures_before_wp170_oos_release"] == FORBIDDEN_EXPOSURES
    assert seal["permitted_visible_summaries"] == PERMITTED_SUMMARIES
    assert not set(FORBIDDEN_EXPOSURES) & set(PERMITTED_SUMMARIES)
    eligibility = seal["eligibility"]
    assert eligibility["never_depends_on"] == ["FORECAST", "OUTCOME_VALUE", "PERFORMANCE", "SCORE"]
    assert "OUTCOME_VALUE" not in eligibility["depends_only_on"]
    assert eligibility["membership"] == "CHRONOLOGICALLY_FIRST_50_ELIGIBLE_TARGET_DATES"
    assert eligibility["replacement_after_entry"] is False
    assert "never skipped" in eligibility["pending_date_rule"]


def test_p18_membership_seal_preimage_exact():
    seal = load_plan()["prospective_data_seal"]["membership_seal"]
    assert seal["id_prefix"] == "oosmembership:sha256:"
    assert seal["preimage_keys"] == MEMBERSHIP_PREIMAGE_KEYS
    assert seal["oos_exclusion_item_keys"] == ["reason_code", "subject_id", "subject_kind", "target_date"]
    assert seal["must_be_reproduced_by"] == ["S10-QUAL-REAL-01", "WP170_SPLIT_ASSIGNMENT"]
    # Synthetic preimage: deterministic id, sensitive to every member.
    preimage = {
        "cap": CAP, "data03_bundle_id": SYN_BUNDLE, "end_time": "2026-12-08T12:09:01Z",
        "oos_exclusions": [{"reason_code": "B0_UNAVAILABLE", "subject_id": "row-x", "subject_kind": "ROW",
                            "target_date": "2026-10-20"}],
        "oos_row_ids": ["row-a", "row-b"], "oos_start": OOS_START,
        "oos_target_dates": [f"2026-10-{d}" for d in range(17, 31)], "plan_01_plan_sha256": PLAN_SHA256,
    }
    assert sorted(preimage) == MEMBERSHIP_PREIMAGE_KEYS
    ident = seal["id_prefix"] + hashlib.sha256(canonical(preimage)).hexdigest()
    assert ident == seal["id_prefix"] + hashlib.sha256(canonical(copy.deepcopy(preimage))).hexdigest()
    for key in MEMBERSHIP_PREIMAGE_KEYS:
        changed = copy.deepcopy(preimage)
        changed[key] = "changed"
        assert seal["id_prefix"] + hashlib.sha256(canonical(changed)).hexdigest() != ident, key


def test_p19_cap_terminal_exact():
    seal = load_plan()["prospective_data_seal"]
    terminals = seal["terminals"]
    assert terminals["insufficient_at_cap"] == "QUAL_OOS_INSUFFICIENT_AT_CAP"
    assert terminals["accrual_incomplete"] == "ACCRUAL_INCOMPLETE"
    assert terminals["extension_permitted"] is False
    assert "no extension" in terminals["insufficient_at_cap_rule"]
    assert "no S10-QUAL-REAL-01" in terminals["insufficient_at_cap_rule"]
    assert "structural counts only" in terminals["accrual_incomplete_rule"]


def test_p20_execution_evidence_is_never_backdated():
    execution = load_plan()["execution_feasibility_plan"]
    assert execution["candidate_plan"] == {}
    assert execution["mechanical_fields"] == {c: "MR12_EXECUTION_EVIDENCE_STATE_V1" for c in q.EXECUTION_FEASIBILITY_CLASSES}
    assert execution["backdating_current_evidence"] is False
    assert execution["data02_current_only_facts_remain_current_only"] is True
    assert execution["not_applicable_state_used"] is False
    assert "NOT_REPRESENTED_AS_HISTORICAL" in execution["available_criteria"]
    assert "CAPTURED_WITH_HONEST_AVAILABILITY_OR_CAPTURE_TIMESTAMP_AT_OR_BEFORE_CANDIDATE_CUTOFF" in execution["available_criteria"]
    assert execution["expected_states"]["SPREAD_DEPTH"] == "MAY_REMAIN_PARTIAL"
    assert execution["expected_states"]["LATENCY"] == execution["expected_states"]["PARTIAL_FILL"] == "MAY_REMAIN_MISSING"
    assert set(execution["required_captures"]) == set(q.EXECUTION_FEASIBILITY_CLASSES)
    for needed in ("CURRENT_ORDER_PRICE_MIN_TICK_SIZE", "CURRENT_ORDER_MIN_SIZE"):
        assert needed in execution["required_captures"]["TICK_SIZE_MIN_ORDER"]
    assert "OFFICIAL_FEE_DOCUMENTATION" in execution["required_captures"]["FEES"]


def test_p21_wp170_remains_sole_preregistration_authority():
    plan = load_plan()
    handoff = plan["wp170_handoff"]
    assert handoff["sole_preregistration_and_oos_authority"] == "WP170"
    assert plan["authority"]["preregistration_authority"] == plan["authority"]["oos_release_authority"] == "WP170_ONLY"
    assert handoff["plan_01_role"] == "ANALYTIC_COMMITMENT_ONLY"
    assert handoff["wp170_changed_by_plan_01"] is False
    assert handoff["preregistered_at_rule"] == "ACTUAL_BUILD_TIME_OF_THE_PREREGISTERED_EXPERIMENT"
    assert handoff["preregistered_at_may_equal_plan_freeze_time"] is False
    assert handoff["creation_provenance_must_bind"] == [
        "PLAN_01_MERGE_COMMIT_SHA", "PLAN_01_PLAN_SHA256", "DATA03_OOSMEMBERSHIP_ID",
        "REAL01_QUAL_PASS_RECEIPT_ID", "STATEMENT_EXPERIMENT_INPUTS_EQUAL_FROZEN_PLAN",
    ]
    later = handoff["known_later_dependency"]
    assert later["blocks_plan_01"] is False and later["blocks_prospective_accrual"] is False
    assert later["eligible_only_after"] == "REAL_QUAL_PASS"


def test_p22_no_experiment_lifecycle_candidate_or_gate_object_is_created():
    authority = load_plan()["authority"]
    for key in ("creates_preregistered_experiment", "creates_lifecycle_or_oos_release_record",
                "creates_qualification_candidate", "runs_qualification_gate", "creates_data03_data",
                "fits_model", "computes_score", "network", "live"):
        assert authority[key] is False, key
    assert authority["gate_c"] == "NOT_AUTHORIZED"
    assert authority["capital_at_risk_usd"] == 0 and authority["orders"] == 0
    for path in PLAN_DIR.iterdir():
        text = path.read_text(encoding="utf-8")
        for prefix in ("experiment:sha256:", "qualificationcandidate:sha256:", "qualificationgate:sha256:",
                       "oosmembership:sha256:0", "split:sha256:", "lifecycle:sha256:"):
            assert prefix not in text, (path.name, prefix)


def test_p23_no_source_network_or_data_access():
    tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported |= {alias.name.split(".")[0] for alias in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    for banned in ("socket", "urllib", "http", "requests", "httpx", "subprocess", "sqlite3"):
        assert banned not in imported, banned
    assert not any(name.startswith(("tools.", "src.data_layer.polymarket")) for name in imported)
    spec = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    required = spec["scope"]["required_changed_files"]
    assert len(required) == len(set(required)) == spec["scope"]["max_changed_files"] == 13
    assert required == spec["scope"]["allowed_changed_files"]
    assert not [p for p in required if p.startswith(("src/", "tools/", ".github/"))]
    assert "pyproject.toml" not in required
    for key in ("source_runtime", "network", "dependencies", "workflow_files", "credentials", "scheduler",
                "hermes_runtime", "strategy", "paper", "execution", "live"):
        assert spec["authority"][key] is False, key
    for path in required:
        assert (ROOT / path).is_file(), path


# ── 24-25: synthetic mechanical compatibility, unchanged behavior ───────────
def test_p24_every_mechanical_rule_is_closed_and_used():
    plan = load_plan()
    rules = plan["mechanical_resolution_rules"]
    assert rules["discretion_permitted"] is False and rules["operator_override_permitted"] is False
    used = set(rules["candidate_mechanical_fields"].values())
    for name in CANDIDATE_SECTIONS:
        used |= set(plan[name]["mechanical_fields"].values())
    used |= {rules["builder_inputs"]["provenance_manifests"],
             plan["prospective_data_seal"]["eligibility"]["rule"],
             plan["dataset_split_plan"]["historical_allocation"]["eligible_historical_date_rule"]}
    assert used == set(rules["rules"])
    for rule_id, rule in rules["rules"].items():
        assert set(rule) == {"target", "value_type", "rule"}, rule_id
        assert rule["value_type"] in {
            "UTC_SECOND", "MANIFEST_SEQUENCE", "TEXT", "EVIDENCE_ID_LIST_PER_FEATURE_REF", "EVIDENCE_ID_LIST",
            "COUNT", "EXECUTION_ENTRY", "OOS_MEMBERSHIP", "DATE_ROLE_ALLOCATION",
        }, rule_id
    static = rules["candidate_static_fields"]
    lineage_fields = rules["candidate_lineage_fields"]
    mechanical = rules["candidate_mechanical_fields"]
    assert set(static) | set(lineage_fields) | set(mechanical) | set(CANDIDATE_SECTIONS) == q._INPUT_KEYS
    assert static == {"candidate_version": "s10-qual-real-01-weather-v1",
                      "qualification_mode": "BINARY_PROBABILITY", "wallet_dependency": "NON_WALLET"}
    for field, pointer in lineage_fields.items():
        assert pointer == f"lineage.{field}"
        assert plan["lineage"][field].startswith(("alphacandidate:sha256:", "alphafamily:sha256:", "alphaepisode:sha256:"))


def test_p24_synthetic_resolution_builds_a_valid_candidate(lineage):
    plan = load_plan()
    value = resolve(plan, lineage)
    record = ok(q.build_qualification_candidate(lineage.snapshot, af1_pass(), synthetic_manifests(), value))
    # Static decisions survive the builder byte-for-byte (the builder only canonicalizes).
    for name in CANDIDATE_SECTIONS:
        normalized = json.loads(getattr(record, f"{name}_json"))
        assert normalized == json.loads(canonical(value[name])), name
        for field, expected in plan[name]["candidate_plan"].items():
            assert normalized[field] == expected, (name, field)
    assert json.loads(record.dataset_split_plan_json)["oos_start"] == OOS_START
    assert json.loads(record.forecast_evaluation_plan_json)["b0_rule"] == "EXTERNAL_PIT_MARKET_PROBABILITY_V1"
    assert record.qualification_mode == "BINARY_PROBABILITY"
    # The synthetic candidate never carries the real Alpha lineage.
    assert record.alpha_candidate_id != plan["lineage"]["alpha_candidate_id"]
    assert ok(q.validate_qualification_candidate(record)) is record
    # Deterministic: same synthetic resolution, same identity.
    again = ok(q.build_qualification_candidate(lineage.snapshot, af1_pass(), synthetic_manifests(), resolve(plan, lineage)))
    assert again.qualification_candidate_id == record.qualification_candidate_id


@pytest.mark.parametrize(
    ("section", "field", "bad", "code"),
    [
        ("dataset_split_plan", "selection_start", "2026-10-15T00:00:00Z", "DATASET_SPLIT_PLAN_INVALID"),
        ("dataset_split_plan", "end_time", "2026-10-14T00:00:00Z", "DATASET_SPLIT_PLAN_INVALID"),
        ("dataset_split_plan", "dataset_snapshot_reference_ids", ["externaldataset:not-covered"], "PROVENANCE_INVALID"),
        ("execution_feasibility_plan", "FEES", {"state": "AVAILABLE", "evidence_reference_ids": []}, "EXECUTION_FEASIBILITY_INVALID"),
        ("execution_feasibility_plan", "LATENCY", {"state": "MISSING", "evidence_reference_ids": ["x"]}, "EXECUTION_FEASIBILITY_INVALID"),
        ("feature_plan", "feature_evidence_refs", {WX: [SYN_BUNDLE]}, "FEATURE_PLAN_INVALID"),
        ("label_plan", "evidence_reference_ids", [], "LABEL_PLAN_INVALID"),
        ("sample_power_plan", "available_sample_count", -1, "POWER_PLAN_INVALID"),
    ],
)
def test_p24_mechanical_values_outside_the_rule_reject(lineage, section, field, bad, code):
    value = resolve(load_plan(), lineage)
    value[section][field] = bad
    rejected(q.build_qualification_candidate(lineage.snapshot, af1_pass(), synthetic_manifests(), value), code)


@pytest.mark.parametrize(
    ("section", "field", "bad", "code"),
    [
        ("forecast_evaluation_plan", "b0_rule", "PIT_MARKET_PROBABILITY_V1", "FORECAST_PLAN_INVALID"),
        ("forecast_evaluation_plan", "b1_feature_refs", sorted([WX, LEAD, MKT]), "FORECAST_PLAN_INVALID"),
        ("forecast_evaluation_plan", "b2_feature_refs", sorted([WX, MKT]), "FORECAST_PLAN_INVALID"),
        ("test_family_plan", "primary_metric_name", "LOG_LOSS", "TEST_FAMILY_PLAN_INVALID"),
        ("hypothesis_plan", "human_review_state", "PENDING", "HYPOTHESIS_PLAN_INVALID"),
        ("dataset_split_plan", "embargo_seconds", -1, "DATASET_SPLIT_PLAN_INVALID"),
        ("feature_plan", "feature_source_classes", {WX: "PUBLIC_NON_MARKET", LEAD: "TIME_ONLY", MKT: "MARKET_PIT"}, "FORECAST_PLAN_INVALID"),
    ],
)
def test_p24_semantic_edits_of_static_decisions_reject(lineage, section, field, bad, code):
    value = resolve(load_plan(), lineage)
    value[section][field] = bad
    rejected(q.build_qualification_candidate(lineage.snapshot, af1_pass(), synthetic_manifests(), value), code)


def test_p24_float_in_resolved_plan_rejects(lineage):
    value = resolve(load_plan(), lineage)
    value["forecast_evaluation_plan"]["b0_parameters"]["max_midpoint_spread"] = 0.1
    rejected(q.build_qualification_candidate(lineage.snapshot, af1_pass(), synthetic_manifests(), value),
             "FIELD_TYPE_INVALID")


def test_p25_existing_qualification_behavior_unchanged(lineage):
    record = ok(build(lineage))
    assert record.qualification_candidate_id == CANONICAL_BINARY_CANDIDATE_ID
    assert q.QUALIFICATION_SCHEMA_VERSION == "1.0.0"
    assert q.B0_RULE_EXTERNAL_PIT_MARKET_PROBABILITY_V1 == "EXTERNAL_PIT_MARKET_PROBABILITY_V1"
    assert q._B0_RULE_MARKET_ADDED_SOURCE_CLASS == {
        "PIT_MARKET_PROBABILITY_V1": "MARKET_PIT",
        "EXTERNAL_PIT_MARKET_PROBABILITY_V1": "MARKET_EXTERNAL_RECONSTRUCTION",
    }
    assert eo.CORRECTION_POLICIES == ("SINGLETON", "FAMILY_TRIAL_COUNT")
    assert eo.GROUP_POLICIES == ("EXCLUSIVE", "DECLARED_NO_ISOLATION")
    rejected(build(lineage, binary_input(lineage, qualification_mode="PLAN_01")), "FIELD_VALUE_INVALID")
