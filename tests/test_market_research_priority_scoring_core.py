"""Focused tests for WP49 Market Research Priority Scoring core scorer.

Tests the src/data_layer/market_research_priority_scoring.py module.
All tests are local/offline/in-memory. No network. No file I/O.
"""

from __future__ import annotations

import importlib
import pathlib
import sys

import pytest

import src.data_layer.market_research_priority_scoring as scorer
from src.data_layer.market_research_priority_scoring import (
    ADVISORY_LABEL,
    FORBIDDEN_OUTPUT_FIELDS,
    FORBIDDEN_USE_NOTICE,
    PENALTY_COMPONENTS,
    POSITIVE_COMPONENTS,
    REQUIRED_MARKET_FIELDS,
    REQUIRED_TOP_LEVEL_FIELDS,
    RESEARCH_PRIORITY_COMPONENTS,
    SCHEMA_VERSION,
    MarketResearchPriorityOutputError,
    assert_market_research_priority_output,
    build_market_research_priority_output,
    compute_research_priority_score,
    contains_forbidden_output_fields,
    validate_market_research_priority_output,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _valid_score_components() -> dict:
    return {
        "data_completeness": 0.9,
        "snapshot_freshness": 0.8,
        "quality_gate_status": 1.0,
        "market_activity_metadata": 1.0,
        "category_coverage": 1.0,
        "token_outcome_completeness": 0.75,
        "order_book_availability": 1.0,
        "spread_structure_observed": 0.5,
        "visible_local_liquidity_proxy": 0.4,
        "guard_provenance_quality": 1.0,
        "duplicate_conflict_penalty": 0.0,
        "missing_data_penalty": 0.0,
        "deferred_item_caveat_penalty": 0.0,
    }


def _valid_staleness() -> dict:
    return {
        "staleness_flag": False,
        "snapshot_age_seconds": 3600,
        "freshness_threshold_seconds": 86400,
        "stale_inputs": [],
        "staleness_warning": None,
        "requires_recapture_before_use": False,
    }


def _valid_provenance() -> dict:
    return {
        "snapshot_manifest_ids": ["manifest-test-001"],
        "source_export_paths": ["local_data/polymarket/snapshots/test.jsonl"],
        "capture_session_ids": ["session-test-001"],
        "guard_policy_version": "wp18-guard-v1",
        "quality_report_ids": ["quality-test-001"],
        "input_artifact_types": ["market_metadata_snapshot"],
    }


def _valid_missing_data() -> dict:
    return {
        "missing_data_warning": False,
        "missing_metadata_fields": [],
        "missing_order_book": False,
        "missing_outcome_tokens": False,
        "missing_category": False,
        "missing_resolution_source": False,
        "insufficient_coverage_reason": None,
    }


def _valid_quality_gates() -> dict:
    return {
        "quality_status": "ACCEPTABLE",
        "quality_warnings": [],
        "dedupe_conflict_flag": False,
        "guard_enforced_capture": True,
        "deferred_item_caveats": ["WP8-D002", "WP16-D002"],
    }


def _valid_run_context() -> dict:
    return {
        "generated_at_utc": "2026-06-03T12:00:00Z",
        "run_id": "run-test-001",
        "source_artifacts": {
            "snapshot_manifest_ids": ["manifest-test-001"],
            "capture_session_ids": ["session-test-001"],
        },
        "scope": {
            "candidate_market_count": 1,
            "scoring_run_type": "local_offline_research_triage",
        },
    }


def _valid_market_context() -> dict:
    return {
        "market_id": "0xtest123",
        "question": "Will event X occur before date Y?",
        "category": "politics",
        "active_status": True,
        "score_components": _valid_score_components(),
        "staleness": _valid_staleness(),
        "provenance": _valid_provenance(),
        "missing_data": _valid_missing_data(),
        "quality_gates": _valid_quality_gates(),
        "component_explanation": "Test market with complete, fresh, quality data.",
    }


# ── Boundary: no forbidden imports ───────────────────────────────────────────

def test_scorer_module_no_requests_import():
    mod = importlib.import_module("src.data_layer.market_research_priority_scoring")
    src_file = pathlib.Path(mod.__file__)
    text = src_file.read_text(encoding="utf-8")
    assert "import requests" not in text
    assert "import httpx" not in text
    assert "import aiohttp" not in text
    assert "import websocket" not in text
    assert "import polymarket" not in text
    assert "import subprocess" not in text


def test_scorer_module_no_open_call():
    mod = importlib.import_module("src.data_layer.market_research_priority_scoring")
    src_file = pathlib.Path(mod.__file__)
    text = src_file.read_text(encoding="utf-8")
    assert "open(" not in text


def test_scorer_module_no_cli_argparse():
    mod = importlib.import_module("src.data_layer.market_research_priority_scoring")
    src_file = pathlib.Path(mod.__file__)
    text = src_file.read_text(encoding="utf-8")
    assert "argparse" not in text
    assert "__main__" not in text


def test_scorer_module_stdlib_only():
    mod = importlib.import_module("src.data_layer.market_research_priority_scoring")
    src_file = pathlib.Path(mod.__file__)
    text = src_file.read_text(encoding="utf-8")
    for forbidden in ("requests", "httpx", "aiohttp", "sqlalchemy", "redis",
                      "celery", "flask", "fastapi", "django", "anthropic",
                      "openai", "hermes"):
        assert forbidden not in text, f"Forbidden dependency '{forbidden}' found in scorer"


# ── Constants ─────────────────────────────────────────────────────────────────

def test_advisory_label_value():
    assert ADVISORY_LABEL == "ADVISORY_ONLY_HUMAN_REVIEW_REQUIRED"


def test_schema_version_present():
    assert SCHEMA_VERSION


def test_forbidden_output_fields_includes_trade_signal():
    assert "trade_signal" in FORBIDDEN_OUTPUT_FIELDS


def test_forbidden_output_fields_includes_alpha_score():
    assert "alpha_score" in FORBIDDEN_OUTPUT_FIELDS


def test_forbidden_output_fields_includes_opportunity_score():
    assert "opportunity_score" in FORBIDDEN_OUTPUT_FIELDS


def test_forbidden_output_fields_includes_expected_return():
    assert "expected_return" in FORBIDDEN_OUTPUT_FIELDS


def test_forbidden_output_fields_includes_position_size():
    assert "position_size" in FORBIDDEN_OUTPUT_FIELDS


def test_forbidden_output_fields_includes_order_params():
    assert "order_params" in FORBIDDEN_OUTPUT_FIELDS


def test_forbidden_output_fields_includes_live_trade_authorization():
    assert "live_trade_authorization" in FORBIDDEN_OUTPUT_FIELDS


def test_forbidden_output_fields_includes_paper_trade_authorization():
    assert "paper_trade_authorization" in FORBIDDEN_OUTPUT_FIELDS


def test_positive_components_count():
    assert len(POSITIVE_COMPONENTS) == 10


def test_penalty_components_count():
    assert len(PENALTY_COMPONENTS) == 3


def test_research_priority_components_combines_both():
    assert set(POSITIVE_COMPONENTS).issubset(set(RESEARCH_PRIORITY_COMPONENTS))
    assert set(PENALTY_COMPONENTS).issubset(set(RESEARCH_PRIORITY_COMPONENTS))


def test_required_top_level_fields_includes_advisory_label():
    assert "advisory_label" in REQUIRED_TOP_LEVEL_FIELDS


def test_required_top_level_fields_includes_human_review_required():
    assert "human_review_required" in REQUIRED_TOP_LEVEL_FIELDS


def test_required_market_fields_includes_research_priority_score():
    assert "research_priority_score" in REQUIRED_MARKET_FIELDS


def test_required_market_fields_includes_advisory_label():
    assert "advisory_label" in REQUIRED_MARKET_FIELDS


def test_forbidden_use_notice_contains_not_trading_signal():
    assert "not a trading signal" in FORBIDDEN_USE_NOTICE


def test_forbidden_use_notice_contains_not_expected_return():
    assert "not expected return" in FORBIDDEN_USE_NOTICE


def test_forbidden_use_notice_contains_not_position_sizing():
    assert "not position sizing" in FORBIDDEN_USE_NOTICE


def test_forbidden_use_notice_contains_not_execution_instruction():
    assert "not an execution instruction" in FORBIDDEN_USE_NOTICE


# ── Core output: valid inputs ─────────────────────────────────────────────────

def test_build_output_returns_dict():
    out = build_market_research_priority_output(
        _valid_run_context(), _valid_market_context()
    )
    assert isinstance(out, dict)


def test_build_output_advisory_label():
    out = build_market_research_priority_output(
        _valid_run_context(), _valid_market_context()
    )
    assert out["advisory_label"] == ADVISORY_LABEL


def test_build_output_human_review_required_true():
    out = build_market_research_priority_output(
        _valid_run_context(), _valid_market_context()
    )
    assert out["human_review_required"] is True


def test_build_output_contains_forbidden_use_notice():
    out = build_market_research_priority_output(
        _valid_run_context(), _valid_market_context()
    )
    assert "forbidden_use_notice" in out
    assert out["forbidden_use_notice"]


def test_build_output_markets_is_list():
    out = build_market_research_priority_output(
        _valid_run_context(), _valid_market_context()
    )
    assert isinstance(out["markets"], list)
    assert len(out["markets"]) == 1


def test_build_output_all_required_top_level_fields():
    out = build_market_research_priority_output(
        _valid_run_context(), _valid_market_context()
    )
    for field in REQUIRED_TOP_LEVEL_FIELDS:
        assert field in out, f"Missing top-level field: {field}"


def test_build_output_all_required_market_fields():
    out = build_market_research_priority_output(
        _valid_run_context(), _valid_market_context()
    )
    market = out["markets"][0]
    for field in REQUIRED_MARKET_FIELDS:
        assert field in market, f"Missing market field: {field}"


def test_build_output_market_advisory_label():
    out = build_market_research_priority_output(
        _valid_run_context(), _valid_market_context()
    )
    market = out["markets"][0]
    assert market["advisory_label"] == ADVISORY_LABEL


def test_build_output_market_human_review_required_true():
    out = build_market_research_priority_output(
        _valid_run_context(), _valid_market_context()
    )
    market = out["markets"][0]
    assert market["human_review_required"] is True


def test_build_output_market_forbidden_use_notice_present():
    out = build_market_research_priority_output(
        _valid_run_context(), _valid_market_context()
    )
    market = out["markets"][0]
    assert market["forbidden_use_notice"]


def test_build_output_score_is_float():
    out = build_market_research_priority_output(
        _valid_run_context(), _valid_market_context()
    )
    score = out["markets"][0]["research_priority_score"]
    assert isinstance(score, float)


def test_build_output_score_bounded_low():
    out = build_market_research_priority_output(
        _valid_run_context(), _valid_market_context()
    )
    score = out["markets"][0]["research_priority_score"]
    assert score >= 0.0


def test_build_output_score_bounded_high():
    out = build_market_research_priority_output(
        _valid_run_context(), _valid_market_context()
    )
    score = out["markets"][0]["research_priority_score"]
    assert score <= 1.0


def test_build_output_score_rank_is_none():
    out = build_market_research_priority_output(
        _valid_run_context(), _valid_market_context()
    )
    assert out["markets"][0]["score_rank"] is None


def test_build_output_schema_version():
    out = build_market_research_priority_output(
        _valid_run_context(), _valid_market_context()
    )
    assert out["schema_version"] == SCHEMA_VERSION


def test_build_output_does_not_contain_research_priority_score_at_top_level():
    out = build_market_research_priority_output(
        _valid_run_context(), _valid_market_context()
    )
    assert "research_priority_score" not in out


def test_build_output_research_priority_score_only_in_market_object():
    out = build_market_research_priority_output(
        _valid_run_context(), _valid_market_context()
    )
    assert "research_priority_score" in out["markets"][0]


def test_build_output_passes_validation():
    out = build_market_research_priority_output(
        _valid_run_context(), _valid_market_context()
    )
    errors = validate_market_research_priority_output(out)
    assert errors == [], f"Validation errors: {errors}"


# ── Score determinism ─────────────────────────────────────────────────────────

def test_compute_score_deterministic():
    sc = _valid_score_components()
    st = _valid_staleness()
    pr = _valid_provenance()
    md = _valid_missing_data()
    qg = _valid_quality_gates()
    score1 = compute_research_priority_score(sc, st, pr, md, qg)
    score2 = compute_research_priority_score(sc, st, pr, md, qg)
    assert score1 == score2


def test_build_output_score_deterministic():
    out1 = build_market_research_priority_output(
        _valid_run_context(), _valid_market_context()
    )
    out2 = build_market_research_priority_output(
        _valid_run_context(), _valid_market_context()
    )
    assert out1["markets"][0]["research_priority_score"] == \
           out2["markets"][0]["research_priority_score"]


# ── Degradation: staleness ────────────────────────────────────────────────────

def test_stale_input_caps_score():
    sc = _valid_score_components()
    st = dict(_valid_staleness())
    st["staleness_flag"] = True
    st["staleness_warning"] = "Snapshot is stale."
    st["requires_recapture_before_use"] = True
    pr = _valid_provenance()
    md = _valid_missing_data()
    qg = _valid_quality_gates()

    fresh_score = compute_research_priority_score(sc, _valid_staleness(), pr, md, qg)
    stale_score = compute_research_priority_score(sc, st, pr, md, qg)
    assert stale_score <= fresh_score
    assert stale_score <= 0.3


def test_stale_input_adds_warning():
    mc = dict(_valid_market_context())
    st = dict(_valid_staleness())
    st["staleness_flag"] = True
    st["staleness_warning"] = "Data is stale."
    mc["staleness"] = st
    out = build_market_research_priority_output(_valid_run_context(), mc)
    assert any("staleness" in w.lower() or "stale" in w.lower()
               for w in out["contract_warnings"])


# ── Degradation: missing provenance ──────────────────────────────────────────

def test_missing_provenance_caps_score():
    sc = _valid_score_components()
    st = _valid_staleness()
    pr_missing = {
        "snapshot_manifest_ids": [],
        "source_export_paths": [],
        "capture_session_ids": [],
        "guard_policy_version": None,
        "quality_report_ids": [],
        "input_artifact_types": [],
    }
    md = _valid_missing_data()
    qg = _valid_quality_gates()

    full_score = compute_research_priority_score(sc, st, _valid_provenance(), md, qg)
    no_prov_score = compute_research_priority_score(sc, st, pr_missing, md, qg)
    assert no_prov_score <= full_score
    assert no_prov_score <= 0.2


def test_missing_provenance_adds_warning():
    mc = dict(_valid_market_context())
    mc["provenance"] = {
        "snapshot_manifest_ids": [],
        "source_export_paths": [],
        "capture_session_ids": [],
        "guard_policy_version": None,
        "quality_report_ids": [],
        "input_artifact_types": [],
    }
    out = build_market_research_priority_output(_valid_run_context(), mc)
    assert any("provenance" in w.lower() for w in out["contract_warnings"])


# ── Degradation: missing data warning ─────────────────────────────────────────

def test_missing_data_warning_caps_score():
    sc = _valid_score_components()
    st = _valid_staleness()
    pr = _valid_provenance()
    md_warn = dict(_valid_missing_data())
    md_warn["missing_data_warning"] = True
    md_warn["insufficient_coverage_reason"] = "No order-book snapshot."
    qg = _valid_quality_gates()

    clean_score = compute_research_priority_score(sc, st, pr, _valid_missing_data(), qg)
    warn_score = compute_research_priority_score(sc, st, pr, md_warn, qg)
    assert warn_score <= clean_score
    assert warn_score <= 0.5


def test_missing_data_adds_warning():
    mc = dict(_valid_market_context())
    md = dict(_valid_missing_data())
    md["missing_data_warning"] = True
    mc["missing_data"] = md
    out = build_market_research_priority_output(_valid_run_context(), mc)
    assert any("missing data" in w.lower() for w in out["contract_warnings"])


# ── Degradation: quality gate failure ────────────────────────────────────────

def test_quality_gate_failing_caps_score():
    sc = _valid_score_components()
    st = _valid_staleness()
    pr = _valid_provenance()
    md = _valid_missing_data()
    qg_fail = dict(_valid_quality_gates())
    qg_fail["quality_status"] = "FAILING"

    ok_score = compute_research_priority_score(sc, st, pr, md, _valid_quality_gates())
    fail_score = compute_research_priority_score(sc, st, pr, md, qg_fail)
    assert fail_score <= ok_score
    assert fail_score <= 0.2


def test_quality_gate_degraded_caps_score():
    sc = _valid_score_components()
    st = _valid_staleness()
    pr = _valid_provenance()
    md = _valid_missing_data()
    qg_deg = dict(_valid_quality_gates())
    qg_deg["quality_status"] = "DEGRADED"

    ok_score = compute_research_priority_score(sc, st, pr, md, _valid_quality_gates())
    deg_score = compute_research_priority_score(sc, st, pr, md, qg_deg)
    assert deg_score <= ok_score
    assert deg_score <= 0.5


def test_quality_gate_unknown_caps_score():
    sc = _valid_score_components()
    st = _valid_staleness()
    pr = _valid_provenance()
    md = _valid_missing_data()
    qg_unk = dict(_valid_quality_gates())
    qg_unk["quality_status"] = "UNKNOWN"

    unk_score = compute_research_priority_score(sc, st, pr, md, qg_unk)
    assert unk_score <= 0.5


# ── Degradation: missing component values ────────────────────────────────────

def test_missing_positive_component_lowers_score():
    sc_full = _valid_score_components()
    sc_missing = dict(sc_full)
    del sc_missing["data_completeness"]
    st = _valid_staleness()
    pr = _valid_provenance()
    md = _valid_missing_data()
    qg = _valid_quality_gates()

    full_score = compute_research_priority_score(sc_full, st, pr, md, qg)
    missing_score = compute_research_priority_score(sc_missing, st, pr, md, qg)
    assert missing_score < full_score


def test_all_missing_positive_components_gives_zero():
    sc_empty: dict = {}
    st = _valid_staleness()
    pr = _valid_provenance()
    md = _valid_missing_data()
    qg = _valid_quality_gates()
    score = compute_research_priority_score(sc_empty, st, pr, md, qg)
    assert score == 0.0


def test_missing_component_value_does_not_default_high():
    sc_missing = {k: None for k in POSITIVE_COMPONENTS}
    sc_missing.update({k: 0.0 for k in PENALTY_COMPONENTS})
    st = _valid_staleness()
    pr = _valid_provenance()
    md = _valid_missing_data()
    qg = _valid_quality_gates()
    score = compute_research_priority_score(sc_missing, st, pr, md, qg)
    assert score == 0.0


# ── Validation: missing required top-level field ──────────────────────────────

def test_validation_fails_missing_advisory_label():
    out = build_market_research_priority_output(
        _valid_run_context(), _valid_market_context()
    )
    del out["advisory_label"]
    errors = validate_market_research_priority_output(out)
    assert any("advisory_label" in e for e in errors)


def test_validation_fails_missing_human_review_required():
    out = build_market_research_priority_output(
        _valid_run_context(), _valid_market_context()
    )
    del out["human_review_required"]
    errors = validate_market_research_priority_output(out)
    assert any("human_review_required" in e for e in errors)


def test_validation_fails_missing_markets():
    out = build_market_research_priority_output(
        _valid_run_context(), _valid_market_context()
    )
    del out["markets"]
    errors = validate_market_research_priority_output(out)
    assert any("markets" in e for e in errors)


def test_validation_fails_missing_schema_version():
    out = build_market_research_priority_output(
        _valid_run_context(), _valid_market_context()
    )
    del out["schema_version"]
    errors = validate_market_research_priority_output(out)
    assert any("schema_version" in e for e in errors)


# ── Validation: wrong advisory label ─────────────────────────────────────────

def test_validation_fails_wrong_advisory_label():
    out = build_market_research_priority_output(
        _valid_run_context(), _valid_market_context()
    )
    out["advisory_label"] = "WRONG_LABEL"
    errors = validate_market_research_priority_output(out)
    assert any("advisory_label" in e for e in errors)


def test_validation_fails_human_review_required_false():
    out = build_market_research_priority_output(
        _valid_run_context(), _valid_market_context()
    )
    out["human_review_required"] = False
    errors = validate_market_research_priority_output(out)
    assert any("human_review_required" in e for e in errors)


# ── Validation: missing required market field ─────────────────────────────────

def test_validation_fails_missing_market_research_priority_score():
    out = build_market_research_priority_output(
        _valid_run_context(), _valid_market_context()
    )
    del out["markets"][0]["research_priority_score"]
    errors = validate_market_research_priority_output(out)
    assert any("research_priority_score" in e for e in errors)


def test_validation_fails_missing_market_advisory_label():
    out = build_market_research_priority_output(
        _valid_run_context(), _valid_market_context()
    )
    del out["markets"][0]["advisory_label"]
    errors = validate_market_research_priority_output(out)
    assert any("advisory_label" in e for e in errors)


# ── Validation: score bounds ──────────────────────────────────────────────────

def test_validation_fails_score_none():
    out = build_market_research_priority_output(
        _valid_run_context(), _valid_market_context()
    )
    out["markets"][0]["research_priority_score"] = None
    errors = validate_market_research_priority_output(out)
    assert errors, "Expected validation errors when research_priority_score is None"
    assert any(
        "research_priority_score" in e and ("None" in e or "not a number" in e or "invalid" in e)
        for e in errors
    ), f"Expected error mentioning score is None or invalid; got: {errors}"


def test_validation_fails_score_below_zero():
    out = build_market_research_priority_output(
        _valid_run_context(), _valid_market_context()
    )
    out["markets"][0]["research_priority_score"] = -0.1
    errors = validate_market_research_priority_output(out)
    assert any("< 0.0" in e for e in errors)


def test_validation_fails_score_above_one():
    out = build_market_research_priority_output(
        _valid_run_context(), _valid_market_context()
    )
    out["markets"][0]["research_priority_score"] = 1.1
    errors = validate_market_research_priority_output(out)
    assert any("> 1.0" in e for e in errors)


def test_score_exactly_zero_is_valid():
    out = build_market_research_priority_output(
        _valid_run_context(), _valid_market_context()
    )
    out["markets"][0]["research_priority_score"] = 0.0
    errors = validate_market_research_priority_output(out)
    score_errors = [e for e in errors if "research_priority_score" in e and
                    ("< 0.0" in e or "> 1.0" in e)]
    assert score_errors == []


def test_score_exactly_one_is_valid():
    out = build_market_research_priority_output(
        _valid_run_context(), _valid_market_context()
    )
    out["markets"][0]["research_priority_score"] = 1.0
    errors = validate_market_research_priority_output(out)
    score_errors = [e for e in errors if "research_priority_score" in e and
                    ("< 0.0" in e or "> 1.0" in e)]
    assert score_errors == []


# ── Validation: forbidden fields ─────────────────────────────────────────────

def test_validation_fails_forbidden_trade_signal():
    out = build_market_research_priority_output(
        _valid_run_context(), _valid_market_context()
    )
    out["trade_signal"] = "buy"
    errors = validate_market_research_priority_output(out)
    assert any("trade_signal" in e for e in errors)


def test_validation_fails_forbidden_alpha_score():
    out = build_market_research_priority_output(
        _valid_run_context(), _valid_market_context()
    )
    out["alpha_score"] = 0.9
    errors = validate_market_research_priority_output(out)
    assert any("alpha_score" in e for e in errors)


def test_validation_fails_forbidden_expected_return():
    out = build_market_research_priority_output(
        _valid_run_context(), _valid_market_context()
    )
    out["expected_return"] = 0.15
    errors = validate_market_research_priority_output(out)
    assert any("expected_return" in e for e in errors)


def test_validation_fails_forbidden_opportunity_score():
    out = build_market_research_priority_output(
        _valid_run_context(), _valid_market_context()
    )
    out["opportunity_score"] = 0.8
    errors = validate_market_research_priority_output(out)
    assert any("opportunity_score" in e for e in errors)


def test_validation_fails_forbidden_position_size():
    out = build_market_research_priority_output(
        _valid_run_context(), _valid_market_context()
    )
    out["position_size"] = 100
    errors = validate_market_research_priority_output(out)
    assert any("position_size" in e for e in errors)


def test_validation_fails_forbidden_order_params():
    out = build_market_research_priority_output(
        _valid_run_context(), _valid_market_context()
    )
    out["order_params"] = {"side": "buy"}
    errors = validate_market_research_priority_output(out)
    assert any("order_params" in e for e in errors)


def test_validation_fails_forbidden_nested_in_market():
    out = build_market_research_priority_output(
        _valid_run_context(), _valid_market_context()
    )
    out["markets"][0]["trade_signal"] = "buy"
    errors = validate_market_research_priority_output(out)
    assert any("trade_signal" in e for e in errors)


def test_validation_fails_forbidden_deeply_nested():
    out = build_market_research_priority_output(
        _valid_run_context(), _valid_market_context()
    )
    out["markets"][0]["score_components"]["alpha_score"] = 0.9
    errors = validate_market_research_priority_output(out)
    assert any("alpha_score" in e for e in errors)


# ── contains_forbidden_output_fields ─────────────────────────────────────────

def test_contains_forbidden_empty_dict():
    assert contains_forbidden_output_fields({}) == []


def test_contains_forbidden_clean_output():
    out = build_market_research_priority_output(
        _valid_run_context(), _valid_market_context()
    )
    assert contains_forbidden_output_fields(out) == []


def test_contains_forbidden_finds_top_level():
    assert "trade_signal" in contains_forbidden_output_fields({"trade_signal": "x"})


def test_contains_forbidden_finds_nested():
    obj = {"a": {"alpha_score": 0.5}}
    assert "alpha_score" in contains_forbidden_output_fields(obj)


def test_contains_forbidden_finds_in_list():
    obj = {"markets": [{"opportunity_score": 0.7}]}
    assert "opportunity_score" in contains_forbidden_output_fields(obj)


def test_contains_forbidden_no_duplicates():
    obj = {"trade_signal": 1, "nested": {"trade_signal": 2}}
    found = contains_forbidden_output_fields(obj)
    assert found.count("trade_signal") == 1


# ── assert_market_research_priority_output ────────────────────────────────────

def test_assert_passes_on_valid_output():
    out = build_market_research_priority_output(
        _valid_run_context(), _valid_market_context()
    )
    assert_market_research_priority_output(out)


def test_assert_raises_on_invalid_output():
    out = build_market_research_priority_output(
        _valid_run_context(), _valid_market_context()
    )
    del out["advisory_label"]
    with pytest.raises(MarketResearchPriorityOutputError):
        assert_market_research_priority_output(out)


def test_assert_raises_on_forbidden_field():
    out = build_market_research_priority_output(
        _valid_run_context(), _valid_market_context()
    )
    out["trade_signal"] = "buy"
    with pytest.raises(MarketResearchPriorityOutputError):
        assert_market_research_priority_output(out)


def test_assert_error_message_contains_field_name():
    out = build_market_research_priority_output(
        _valid_run_context(), _valid_market_context()
    )
    del out["advisory_label"]
    with pytest.raises(MarketResearchPriorityOutputError) as exc_info:
        assert_market_research_priority_output(out)
    assert "advisory_label" in str(exc_info.value)


# ── Score computation edge cases ──────────────────────────────────────────────

def test_compute_score_all_max_positive_no_penalty():
    sc = {k: 1.0 for k in POSITIVE_COMPONENTS}
    sc.update({k: 0.0 for k in PENALTY_COMPONENTS})
    score = compute_research_priority_score(
        sc, _valid_staleness(), _valid_provenance(),
        _valid_missing_data(), _valid_quality_gates()
    )
    assert score == 1.0


def test_compute_score_all_zero_positive():
    sc = {k: 0.0 for k in POSITIVE_COMPONENTS}
    sc.update({k: 0.0 for k in PENALTY_COMPONENTS})
    score = compute_research_priority_score(
        sc, _valid_staleness(), _valid_provenance(),
        _valid_missing_data(), _valid_quality_gates()
    )
    assert score == 0.0


def test_compute_score_max_penalty():
    sc = {k: 1.0 for k in POSITIVE_COMPONENTS}
    sc.update({k: -1.0 for k in PENALTY_COMPONENTS})
    score = compute_research_priority_score(
        sc, _valid_staleness(), _valid_provenance(),
        _valid_missing_data(), _valid_quality_gates()
    )
    assert score >= 0.0
    assert score <= 1.0
    assert score < 1.0


def test_compute_score_clamps_to_zero_not_negative():
    sc = {k: 0.0 for k in POSITIVE_COMPONENTS}
    sc.update({k: -1.0 for k in PENALTY_COMPONENTS})
    score = compute_research_priority_score(
        sc, _valid_staleness(), _valid_provenance(),
        _valid_missing_data(), _valid_quality_gates()
    )
    assert score == 0.0


def test_compute_score_multiple_caps_uses_lowest():
    sc = {k: 1.0 for k in POSITIVE_COMPONENTS}
    sc.update({k: 0.0 for k in PENALTY_COMPONENTS})
    st = dict(_valid_staleness())
    st["staleness_flag"] = True
    md = dict(_valid_missing_data())
    md["missing_data_warning"] = True
    qg = dict(_valid_quality_gates())
    qg["quality_status"] = "FAILING"
    score = compute_research_priority_score(
        sc, st, _valid_provenance(), md, qg
    )
    assert score <= min(0.3, 0.5, 0.2)


# ── Docs contract alignment ───────────────────────────────────────────────────

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
CONTRACT_DOC = REPO_ROOT / "docs" / "market_research_priority_scoring_output_contract.md"
PROJECT_STATUS = REPO_ROOT / "docs" / "project_status.md"
DEFERRED_LOG = REPO_ROOT / "docs" / "deferred_items_log.md"


def test_output_contract_doc_exists():
    assert CONTRACT_DOC.is_file()


def test_output_contract_advisory_label_unchanged():
    text = CONTRACT_DOC.read_text(encoding="utf-8")
    assert "ADVISORY_ONLY_HUMAN_REVIEW_REQUIRED" in text


def test_output_contract_forbids_expected_return():
    text = CONTRACT_DOC.read_text(encoding="utf-8")
    assert "expected_return" in text
    assert "forbidden" in text.lower() or "Forbidden" in text


def test_output_contract_forbids_execution_fields():
    text = CONTRACT_DOC.read_text(encoding="utf-8")
    assert "execution_confidence" in text
    assert "order_params" in text


def test_project_status_wp49_active():
    text = PROJECT_STATUS.read_text(encoding="utf-8")
    assert "WP49" in text


def test_project_status_wp48_in_merged_wps():
    text = PROJECT_STATUS.read_text(encoding="utf-8")
    merged_line = next(
        line for line in text.splitlines() if line.startswith("- Merged WPs:")
    )
    assert "WP48" in merged_line


def test_project_status_core_scorer_merged():
    # WP49 is merged; project_status.md must reflect CORE_SCORER_MERGED (not ON_BRANCH)
    text = PROJECT_STATUS.read_text(encoding="utf-8")
    assert "CORE_SCORER_MERGED" in text
    assert "CORE_SCORER_ON_BRANCH" not in text


def test_project_status_live_trading_disabled():
    assert "Live trading status: DISABLED" in PROJECT_STATUS.read_text(encoding="utf-8")


def test_project_status_hermes_not_installed():
    assert "NOT_INSTALLED_NOT_RUNTIME_DEPENDENCY" in PROJECT_STATUS.read_text(encoding="utf-8")


def test_deferred_log_wp49_d001_present():
    text = DEFERRED_LOG.read_text(encoding="utf-8")
    assert "WP49-D001" in text


def test_deferred_log_wp49_d002_present():
    text = DEFERRED_LOG.read_text(encoding="utf-8")
    assert "WP49-D002" in text


def test_deferred_log_wp49_d003_present():
    text = DEFERRED_LOG.read_text(encoding="utf-8")
    assert "WP49-D003" in text
