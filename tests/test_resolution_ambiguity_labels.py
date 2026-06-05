"""Focused tests for src/data_layer/resolution_ambiguity_labels.py.

Added in WP56. Tests cover: valid label cases, invalid label cases,
boundary tests, and optional reader tests. No network, no writes,
no parser, no scorer integration, no feature extraction.
"""

from __future__ import annotations

import importlib
import json
import pathlib
import sys
import tempfile
import types

import pytest


# ── Import guard ─────────────────────────────────────────────────────────────

def test_module_imports_without_network():
    """Module must import cleanly without network, third-party deps, or optional services."""
    import src.data_layer.resolution_ambiguity_labels as m
    assert hasattr(m, "validate_resolution_ambiguity_label")
    assert hasattr(m, "validate_resolution_ambiguity_labels")
    assert hasattr(m, "ADVISORY_LABEL")


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _valid_clear_label() -> dict:
    return {
        "schema_version": "1.0",
        "label_id": "label-20260604-001",
        "market_id": "0xabc123",
        "question_snapshot": "Will candidate X win the 2026 election?",
        "resolution_text_snapshot": "Resolves YES if AP calls the race by 2026-11-30T23:59:00Z.",
        "review_status": "REVIEWED_CLEAR",
        "ambiguity_categories": [],
        "ambiguity_severity": "NONE",
        "reviewer_confidence": "HIGH",
        "manual_review_required": False,
        "reviewed_at_utc": "2026-06-04T10:00:00Z",
        "reviewer_id_or_role": "human_analyst",
        "source_artifact_refs": ["local_data/polymarket/snapshots/manifest-20260603-001.jsonl"],
        "evidence_notes": "Resolution source, event, and cutoff are clearly stated.",
        "limitations": None,
        "advisory_label": "ADVISORY_ONLY_HUMAN_REVIEW_REQUIRED",
        "forbidden_use_notice": (
            "This label is not a trading signal, not expected return, not position sizing, "
            "not execution instruction. "
            "It is research-data-quality metadata for human research triage only."
        ),
    }


def _valid_medium_ambiguity_label() -> dict:
    return {
        "schema_version": "1.0",
        "label_id": "label-20260604-002",
        "market_id": "0xdef456",
        "question_snapshot": "Will inflation fall below 3% by end of year?",
        "resolution_text_snapshot": "Resolves YES if CPI inflation falls below 3% as reported by official statistics.",
        "review_status": "REVIEWED_MEDIUM_AMBIGUITY",
        "ambiguity_categories": ["measurement_definition_ambiguity", "unclear_source_hierarchy"],
        "ambiguity_severity": "MEDIUM",
        "reviewer_confidence": "MEDIUM",
        "manual_review_required": True,
        "reviewed_at_utc": "2026-06-04T10:05:00Z",
        "reviewer_id_or_role": "human_analyst",
        "source_artifact_refs": ["local_data/polymarket/snapshots/manifest-20260603-001.jsonl"],
        "evidence_notes": "Multiple CPI measures exist. 'Official statistics' does not name an agency.",
        "limitations": "Snapshot may not contain the full resolution source text.",
        "advisory_label": "ADVISORY_ONLY_HUMAN_REVIEW_REQUIRED",
        "forbidden_use_notice": (
            "This label is not a trading signal, not expected return, not position sizing, "
            "not execution instruction. "
            "It is research-data-quality metadata for human research triage only."
        ),
    }


def _valid_insufficient_evidence_label() -> dict:
    return {
        "schema_version": "1.0",
        "label_id": "label-20260604-003",
        "market_id": "0xghi789",
        "question_snapshot": "Will the event occur?",
        "resolution_text_snapshot": None,
        "review_status": "INSUFFICIENT_LOCAL_EVIDENCE",
        "ambiguity_categories": ["missing_resolution_source", "insufficient_local_evidence"],
        "ambiguity_severity": "UNKNOWN",
        "reviewer_confidence": "LOW",
        "manual_review_required": True,
        "reviewed_at_utc": "2026-06-04T10:10:00Z",
        "reviewer_id_or_role": "human_analyst",
        "source_artifact_refs": ["local_data/polymarket/snapshots/manifest-20260603-001.jsonl"],
        "evidence_notes": "No resolution text found in local snapshot.",
        "limitations": "Resolution text absent. Label is provisional.",
        "advisory_label": "ADVISORY_ONLY_HUMAN_REVIEW_REQUIRED",
        "forbidden_use_notice": (
            "This label is not a trading signal, not expected return, not position sizing, "
            "not execution instruction. "
            "It is research-data-quality metadata for human research triage only."
        ),
    }


def _valid_other_issue_label() -> dict:
    label = _valid_medium_ambiguity_label()
    label["label_id"] = "label-20260604-004"
    label["ambiguity_categories"] = ["other_manual_review_issue"]
    label["review_status"] = "REVIEWED_HIGH_AMBIGUITY"
    label["ambiguity_severity"] = "HIGH"
    label["evidence_notes"] = "The resolution rules reference an external document not available locally."
    return label


# ── 9.1 Valid label cases ─────────────────────────────────────────────────────

from src.data_layer.resolution_ambiguity_labels import (
    ADVISORY_LABEL,
    ALLOWED_AMBIGUITY_CATEGORIES,
    ALLOWED_CONFIDENCE_VALUES,
    ALLOWED_REVIEW_STATUSES,
    ALLOWED_SEVERITY_VALUES,
    ResolutionAmbiguityLabelValidationIssue,
    ResolutionAmbiguityLabelValidationResult,
    load_resolution_ambiguity_label_records,
    validate_resolution_ambiguity_label,
    validate_resolution_ambiguity_labels,
)


def test_valid_reviewed_clear_label():
    result = validate_resolution_ambiguity_label(_valid_clear_label())
    assert result.is_valid is True
    assert len(result.errors) == 0


def test_valid_reviewed_medium_ambiguity_label():
    result = validate_resolution_ambiguity_label(_valid_medium_ambiguity_label())
    assert result.is_valid is True
    assert len(result.errors) == 0


def test_valid_insufficient_local_evidence_label():
    result = validate_resolution_ambiguity_label(_valid_insufficient_evidence_label())
    assert result.is_valid is True
    assert len(result.errors) == 0


def test_valid_multi_category_label():
    label = _valid_medium_ambiguity_label()
    label["ambiguity_categories"] = [
        "cutoff_time_ambiguity",
        "timezone_ambiguity",
        "unclear_source_hierarchy",
        "measurement_definition_ambiguity",
    ]
    result = validate_resolution_ambiguity_label(label)
    assert result.is_valid is True


def test_valid_other_manual_review_issue_with_evidence_notes():
    result = validate_resolution_ambiguity_label(_valid_other_issue_label())
    assert result.is_valid is True, [e.message for e in result.errors]


# ── 9.2 Invalid label cases ───────────────────────────────────────────────────

def test_missing_required_field():
    label = _valid_medium_ambiguity_label()
    del label["label_id"]
    result = validate_resolution_ambiguity_label(label)
    assert result.is_valid is False
    codes = {e.code for e in result.errors}
    assert "MISSING_REQUIRED_FIELD" in codes


def test_unknown_extra_field():
    label = _valid_medium_ambiguity_label()
    label["extra_field"] = "unexpected"
    result = validate_resolution_ambiguity_label(label)
    assert result.is_valid is False
    codes = {e.code for e in result.errors}
    assert "UNKNOWN_EXTRA_FIELD" in codes


def test_invalid_review_status():
    label = _valid_medium_ambiguity_label()
    label["review_status"] = "UNTRADEABLE"
    result = validate_resolution_ambiguity_label(label)
    assert result.is_valid is False
    codes = {e.code for e in result.errors}
    assert "INVALID_REVIEW_STATUS" in codes


def test_invalid_ambiguity_category():
    label = _valid_medium_ambiguity_label()
    label["ambiguity_categories"] = ["not_a_real_category"]
    result = validate_resolution_ambiguity_label(label)
    assert result.is_valid is False
    codes = {e.code for e in result.errors}
    assert "INVALID_AMBIGUITY_CATEGORY" in codes


def test_invalid_ambiguity_severity():
    label = _valid_medium_ambiguity_label()
    label["ambiguity_severity"] = "AVOID"
    result = validate_resolution_ambiguity_label(label)
    assert result.is_valid is False
    codes = {e.code for e in result.errors}
    assert "INVALID_AMBIGUITY_SEVERITY" in codes


def test_invalid_reviewer_confidence():
    label = _valid_medium_ambiguity_label()
    label["reviewer_confidence"] = "VERY_HIGH"
    result = validate_resolution_ambiguity_label(label)
    assert result.is_valid is False
    codes = {e.code for e in result.errors}
    assert "INVALID_REVIEWER_CONFIDENCE" in codes


def test_wrong_advisory_label():
    label = _valid_medium_ambiguity_label()
    label["advisory_label"] = "MAYBE_ADVISORY"
    result = validate_resolution_ambiguity_label(label)
    assert result.is_valid is False
    codes = {e.code for e in result.errors}
    assert "WRONG_ADVISORY_LABEL" in codes


def test_missing_forbidden_use_notice():
    label = _valid_medium_ambiguity_label()
    label["forbidden_use_notice"] = ""
    result = validate_resolution_ambiguity_label(label)
    assert result.is_valid is False
    codes = {e.code for e in result.errors}
    assert "MISSING_FORBIDDEN_USE_NOTICE" in codes


def test_forbidden_use_notice_missing_not_a_trading_signal():
    label = _valid_medium_ambiguity_label()
    label["forbidden_use_notice"] = (
        "This label is not expected return, not position sizing, not execution instruction. "
        "Research data quality only."
    )
    result = validate_resolution_ambiguity_label(label)
    assert result.is_valid is False
    codes = {e.code for e in result.errors}
    assert "MISSING_REQUIRED_NON_SIGNAL_PHRASE" in codes


def test_forbidden_use_notice_missing_not_expected_return():
    label = _valid_medium_ambiguity_label()
    label["forbidden_use_notice"] = (
        "This label is not a trading signal, not position sizing, not execution instruction. "
        "Research data quality only."
    )
    result = validate_resolution_ambiguity_label(label)
    assert result.is_valid is False
    codes = {e.code for e in result.errors}
    assert "MISSING_REQUIRED_NON_SIGNAL_PHRASE" in codes


def test_forbidden_use_notice_missing_not_position_sizing():
    label = _valid_medium_ambiguity_label()
    label["forbidden_use_notice"] = (
        "This label is not a trading signal, not expected return, not execution instruction. "
        "Research data quality only."
    )
    result = validate_resolution_ambiguity_label(label)
    assert result.is_valid is False
    codes = {e.code for e in result.errors}
    assert "MISSING_REQUIRED_NON_SIGNAL_PHRASE" in codes


def test_forbidden_use_notice_missing_not_execution_instruction():
    label = _valid_medium_ambiguity_label()
    label["forbidden_use_notice"] = (
        "This label is not a trading signal, not expected return, not position sizing. "
        "Research data quality only."
    )
    result = validate_resolution_ambiguity_label(label)
    assert result.is_valid is False
    codes = {e.code for e in result.errors}
    assert "MISSING_REQUIRED_NON_SIGNAL_PHRASE" in codes


def test_manual_review_required_false_for_ambiguous_label():
    label = _valid_medium_ambiguity_label()
    label["manual_review_required"] = False
    result = validate_resolution_ambiguity_label(label)
    assert result.is_valid is False
    codes = {e.code for e in result.errors}
    assert "MANUAL_REVIEW_REQUIRED_MUST_BE_TRUE" in codes


def test_reviewed_clear_with_non_empty_ambiguity_categories():
    label = _valid_clear_label()
    label["ambiguity_categories"] = ["cutoff_time_ambiguity"]
    result = validate_resolution_ambiguity_label(label)
    assert result.is_valid is False
    codes = {e.code for e in result.errors}
    assert "REVIEWED_CLEAR_WITH_CATEGORIES" in codes


def test_insufficient_local_evidence_without_unknown_severity():
    label = _valid_insufficient_evidence_label()
    label["ambiguity_severity"] = "HIGH"
    result = validate_resolution_ambiguity_label(label)
    assert result.is_valid is False
    codes = {e.code for e in result.errors}
    assert "INSUFFICIENT_EVIDENCE_SEVERITY_MUST_BE_UNKNOWN" in codes


def test_other_manual_review_issue_without_evidence_notes():
    label = _valid_other_issue_label()
    label["evidence_notes"] = None
    result = validate_resolution_ambiguity_label(label)
    assert result.is_valid is False
    codes = {e.code for e in result.errors}
    assert "OTHER_CATEGORY_REQUIRES_EVIDENCE_NOTES" in codes


def test_source_refs_empty_list():
    label = _valid_medium_ambiguity_label()
    label["source_artifact_refs"] = []
    result = validate_resolution_ambiguity_label(label)
    assert result.is_valid is False
    codes = {e.code for e in result.errors}
    assert "EMPTY_SOURCE_ARTIFACT_REFS" in codes


def test_source_refs_contain_live_url_https():
    label = _valid_medium_ambiguity_label()
    label["source_artifact_refs"] = ["https://api.polymarket.com/markets"]
    result = validate_resolution_ambiguity_label(label)
    assert result.is_valid is False
    codes = {e.code for e in result.errors}
    assert "FORBIDDEN_SOURCE_REF" in codes


def test_source_refs_contain_live_url_http():
    label = _valid_medium_ambiguity_label()
    label["source_artifact_refs"] = ["http://example.com/data"]
    result = validate_resolution_ambiguity_label(label)
    assert result.is_valid is False
    codes = {e.code for e in result.errors}
    assert "FORBIDDEN_SOURCE_REF" in codes


def test_source_refs_contain_credential_like_string():
    label = _valid_medium_ambiguity_label()
    label["source_artifact_refs"] = ["local_data/credential_backup.json"]
    result = validate_resolution_ambiguity_label(label)
    assert result.is_valid is False
    codes = {e.code for e in result.errors}
    assert "FORBIDDEN_SOURCE_REF" in codes


def test_unparseable_reviewed_at_utc():
    label = _valid_medium_ambiguity_label()
    label["reviewed_at_utc"] = "not-a-date"
    result = validate_resolution_ambiguity_label(label)
    assert result.is_valid is False
    codes = {e.code for e in result.errors}
    assert "UNPARSEABLE_TIMESTAMP" in codes


# ── 9.3 Boundary tests ────────────────────────────────────────────────────────

def test_module_imports_without_third_party_dependencies():
    """Module must use stdlib only."""
    import src.data_layer.resolution_ambiguity_labels as m
    source = pathlib.Path(m.__file__).read_text(encoding="utf-8")
    forbidden_imports = ["requests", "httpx", "aiohttp", "numpy", "pandas", "pydantic"]
    for lib in forbidden_imports:
        assert f"import {lib}" not in source, f"Found forbidden import: {lib}"


def test_no_writes_performed(tmp_path):
    """Validate functions must not write any files."""
    before = list(tmp_path.iterdir())
    validate_resolution_ambiguity_label(_valid_medium_ambiguity_label())
    validate_resolution_ambiguity_labels([_valid_medium_ambiguity_label()])
    after = list(tmp_path.iterdir())
    assert before == after


def test_no_parser_function_exists():
    """Module must not expose a parser function."""
    import src.data_layer.resolution_ambiguity_labels as m
    for name in dir(m):
        assert "parse" not in name.lower() or name.startswith("_"), (
            f"Unexpected public parser-like function: {name}"
        )


def test_no_scorer_integration_function_exists():
    """Module must not expose scorer integration."""
    import src.data_layer.resolution_ambiguity_labels as m
    forbidden_names = {"score", "compute_score", "build_priority_output"}
    for name in dir(m):
        assert name not in forbidden_names, f"Unexpected scorer function: {name}"


def test_no_feature_extraction_integration():
    """Module must not import market_research_priority_features."""
    import src.data_layer.resolution_ambiguity_labels as m
    source = pathlib.Path(m.__file__).read_text(encoding="utf-8")
    assert "market_research_priority_features" not in source
    assert "market_research_priority_scoring" not in source


def test_no_trade_like_field_names_in_module():
    """Module must not define trade-like output field names as public constants."""
    import src.data_layer.resolution_ambiguity_labels as m
    source = pathlib.Path(m.__file__).read_text(encoding="utf-8")
    forbidden = [
        "tradability_score",
        "alpha_score",
        "edge_score",
        "opportunity_score",
        "execution_confidence",
        "expected_return",
        "fill_probability",
    ]
    for name in forbidden:
        # Only fail if it appears as an assignment/definition, not in FORBIDDEN_FIELD_NAMES list
        assert f'"{name}"' not in source or "FORBIDDEN_FIELD_NAMES" in source, (
            f"Trade-like field name '{name}' found in module source outside FORBIDDEN_FIELD_NAMES"
        )


def test_constants_advisory_label_value():
    assert ADVISORY_LABEL == "ADVISORY_ONLY_HUMAN_REVIEW_REQUIRED"


def test_constants_all_categories_present():
    expected = {
        "missing_resolution_source",
        "unclear_source_hierarchy",
        "cutoff_time_ambiguity",
        "timezone_ambiguity",
        "title_rules_mismatch",
        "entity_definition_ambiguity",
        "event_definition_ambiguity",
        "measurement_definition_ambiguity",
        "outcome_mapping_ambiguity",
        "source_conflict",
        "finality_or_revision_ambiguity",
        "duplicate_or_overlap_risk",
        "insufficient_local_evidence",
        "other_manual_review_issue",
    }
    assert expected == ALLOWED_AMBIGUITY_CATEGORIES


def test_constants_all_review_statuses_present():
    expected = {
        "NOT_REVIEWED",
        "REVIEWED_CLEAR",
        "REVIEWED_LOW_AMBIGUITY",
        "REVIEWED_MEDIUM_AMBIGUITY",
        "REVIEWED_HIGH_AMBIGUITY",
        "INSUFFICIENT_LOCAL_EVIDENCE",
    }
    assert expected == ALLOWED_REVIEW_STATUSES


def test_constants_all_severity_values_present():
    assert {"NONE", "LOW", "MEDIUM", "HIGH", "UNKNOWN"} == ALLOWED_SEVERITY_VALUES


def test_constants_all_confidence_values_present():
    assert {"LOW", "MEDIUM", "HIGH"} == ALLOWED_CONFIDENCE_VALUES


def test_batch_validate_returns_one_result_per_label():
    labels = [
        _valid_clear_label(),
        _valid_medium_ambiguity_label(),
        _valid_insufficient_evidence_label(),
    ]
    results = validate_resolution_ambiguity_labels(labels)
    assert len(results) == 3
    assert all(isinstance(r, ResolutionAmbiguityLabelValidationResult) for r in results)


def test_batch_validate_all_valid():
    labels = [_valid_clear_label(), _valid_medium_ambiguity_label()]
    results = validate_resolution_ambiguity_labels(labels)
    assert all(r.is_valid for r in results)


def test_batch_validate_with_invalid():
    bad_label = _valid_medium_ambiguity_label()
    del bad_label["label_id"]
    results = validate_resolution_ambiguity_labels([_valid_clear_label(), bad_label])
    assert results[0].is_valid is True
    assert results[1].is_valid is False


def test_result_dataclass_is_frozen():
    result = validate_resolution_ambiguity_label(_valid_clear_label())
    with pytest.raises(Exception):
        result.is_valid = False  # type: ignore[misc]


def test_issue_dataclass_is_frozen():
    issue = ResolutionAmbiguityLabelValidationIssue("field", "code", "msg")
    with pytest.raises(Exception):
        issue.field = "other"  # type: ignore[misc]


# ── 9.4 Reader tests ──────────────────────────────────────────────────────────

def test_load_json_array_from_file(tmp_path):
    data = [_valid_clear_label(), _valid_medium_ambiguity_label()]
    f = tmp_path / "labels.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    records = load_resolution_ambiguity_label_records(f)
    assert len(records) == 2
    assert records[0]["label_id"] == "label-20260604-001"


def test_load_jsonl_from_file(tmp_path):
    data = [_valid_clear_label(), _valid_medium_ambiguity_label()]
    f = tmp_path / "labels.jsonl"
    lines = "\n".join(json.dumps(r) for r in data)
    f.write_text(lines, encoding="utf-8")
    records = load_resolution_ambiguity_label_records(f)
    assert len(records) == 2


def test_load_rejects_unsupported_extension(tmp_path):
    f = tmp_path / "labels.csv"
    f.write_text("col1,col2\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Unsupported file extension"):
        load_resolution_ambiguity_label_records(f)


def test_load_rejects_invalid_json(tmp_path):
    f = tmp_path / "labels.json"
    f.write_text("{not valid json", encoding="utf-8")
    with pytest.raises((ValueError, Exception)):
        load_resolution_ambiguity_label_records(f)


def test_load_json_requires_array(tmp_path):
    f = tmp_path / "labels.json"
    f.write_text(json.dumps({"key": "value"}), encoding="utf-8")
    with pytest.raises(ValueError, match="Expected a JSON array"):
        load_resolution_ambiguity_label_records(f)


def test_load_does_not_write_output_files(tmp_path):
    data = [_valid_clear_label()]
    f = tmp_path / "labels.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    before = set(tmp_path.iterdir())
    load_resolution_ambiguity_label_records(f)
    after = set(tmp_path.iterdir())
    assert before == after


def test_load_jsonl_skips_blank_lines(tmp_path):
    data = [_valid_clear_label()]
    f = tmp_path / "labels.jsonl"
    f.write_text(json.dumps(data[0]) + "\n\n", encoding="utf-8")
    records = load_resolution_ambiguity_label_records(f)
    assert len(records) == 1


def test_load_then_validate_roundtrip(tmp_path):
    data = [_valid_clear_label(), _valid_medium_ambiguity_label()]
    f = tmp_path / "labels.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    records = load_resolution_ambiguity_label_records(f)
    results = validate_resolution_ambiguity_labels(records)
    assert all(r.is_valid for r in results)
