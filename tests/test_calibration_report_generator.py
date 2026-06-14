"""Focused tests for the WP71 local/offline/read-only calibration report generator.

Tests cover: empty input, report type/scope, valid/invalid/stale/missing records,
all summary sections, warnings determinism, forbidden interpretation notice,
dataclass immutability, non-signal boundary, forbidden scope, and compatibility
with WP70/WP68/WP67 components.
"""

from __future__ import annotations

import dataclasses
import importlib
import inspect
import sys

import pytest

from src.data_layer.calibration_report_generator import (
    FORBIDDEN_REPORT_FIELDS,
    LocalCalibrationReport,
    build_calibration_report,
    build_calibration_report_from_load_result,
)
from src.data_layer.calibration_metric_computation import (
    compute_calibration_metrics,
)
from src.data_layer.resolved_outcome_fixture_loader import (
    LoadedCalibrationRecord,
    ResolvedOutcomeFixtureLoadResult,
)
from src.data_layer.calibration_record_validation import (
    validate_calibration_record,
)


# ---------------------------------------------------------------------------
# Shared fixture factory (mirrors test_calibration_metric_computation.py)
# ---------------------------------------------------------------------------


def _valid_record(**overrides) -> dict:
    base = {
        "_notice": "ADVISORY_ONLY",
        "_schema_version": "calibration_record_v1",
        "_status": "TEST",
        "identity": {
            "market_id": "market-abc",
            "condition_id": "cond-def",
            "question": "Will X happen?",
            "category": "Politics",
        },
        "snapshot_metadata": {
            "snapshot_time_utc": "2025-12-01T12:00:00Z",
            "local_capture_time_utc": "2025-12-01T12:05:00Z",
            "snapshot_offset_from_resolution": "T-30d",
        },
        "research_queue_state": {
            "research_queue_bucket": "REVIEW_FIRST",
            "research_review_priority": 1,
            "research_priority_score": 0.75,
            "quality_status": "ACCEPTABLE",
            "source_metadata_available": True,
            "manual_source_review_required": False,
            "resolution_ambiguity_manual_review_required": False,
            "microstructure_quality_summary": "LOCAL_DATA_AVAILABLE",
            "cross_market_candidate_count": 0,
        },
        "resolved_outcome": {
            "resolved_outcome": "YES",
            "resolution_status": "RESOLVED",
            "resolution_time_utc": "2026-01-02T00:00:00Z",
            "resolution_source_url_or_reference": "https://example.invalid/source",
            "resolution_source_type": "NEWS_ARTICLE",
            "resolution_rule_text_snapshot_available": True,
            "resolution_dispute_or_ambiguity_flag": False,
            "final_market_status": "RESOLVED",
            "outcome_token_mapping_verified": True,
        },
        "human_review": {
            "human_review_usefulness_label": "USEFUL_RESEARCH_TARGET",
        },
        "calibration_validity": {
            "record_complete": True,
            "missing_required_fields": [],
            "excluded_from_calibration": False,
            "exclusion_reason": None,
        },
    }
    base.update(overrides)
    return base


def _invalid_record() -> dict:
    return {
        "_notice": "ADVISORY_ONLY",
        "_schema_version": "calibration_record_v1",
        "_status": "TEST",
        # missing: identity, snapshot_metadata, research_queue_state,
        #          resolved_outcome, human_review, calibration_validity
    }


def _stale_record() -> dict:
    r = _valid_record()
    r["snapshot_metadata"] = {
        "snapshot_time_utc": "2025-12-01T12:00:00Z",
        "local_capture_time_utc": "2025-12-01T12:05:00Z",
        "snapshot_offset_from_resolution": "UNKNOWN_OFFSET",
    }
    return r


def _missing_resolution_source_record() -> dict:
    r = _valid_record()
    r["resolved_outcome"] = {
        "resolved_outcome": "YES",
        "resolution_status": "RESOLVED",
        "resolution_time_utc": "2026-01-02T00:00:00Z",
        "resolution_source_url_or_reference": "",  # empty — missing
        "resolution_source_type": "NEWS_ARTICLE",
        "resolution_rule_text_snapshot_available": True,
        "resolution_dispute_or_ambiguity_flag": False,
        "final_market_status": "RESOLVED",
        "outcome_token_mapping_verified": True,
    }
    return r


def _manual_review_record() -> dict:
    r = _valid_record()
    r["research_queue_state"] = dict(r["research_queue_state"])
    r["research_queue_state"]["manual_source_review_required"] = True
    return r


def _excluded_record() -> dict:
    r = _valid_record()
    r["calibration_validity"] = {
        "record_complete": False,
        "missing_required_fields": ["resolved_outcome"],
        "excluded_from_calibration": True,
        "exclusion_reason": "missing_resolved_outcome",
    }
    return r


def _post_resolution_audit_record() -> dict:
    r = _valid_record()
    r["resolved_outcome"] = dict(r["resolved_outcome"])
    r["resolved_outcome"]["resolution_dispute_or_ambiguity_flag"] = True
    return r


def _load_result_from_records(records: list[dict]) -> ResolvedOutcomeFixtureLoadResult:
    loaded = tuple(
        LoadedCalibrationRecord(
            source_path="<fixture>",
            record_index=i,
            record=r,
            validation=validate_calibration_record(r),
        )
        for i, r in enumerate(records)
    )
    valid_count = sum(1 for lr in loaded if lr.validation.is_valid)
    invalid_count = len(loaded) - valid_count
    warning_count = sum(len(lr.validation.warnings) for lr in loaded)
    return ResolvedOutcomeFixtureLoadResult(
        source_path="<fixture>",
        loaded_count=len(loaded),
        valid_count=valid_count,
        invalid_count=invalid_count,
        warning_count=warning_count,
        records=loaded,
        errors=(),
        advisory_label="ADVISORY_ONLY_RESEARCH_USEFULNESS_AUDIT",
    )


# ---------------------------------------------------------------------------
# 1. Empty input — basic report structure
# ---------------------------------------------------------------------------


class TestEmptyInput:
    def test_empty_has_correct_report_type(self):
        report = build_calibration_report([])
        assert report.report_type == "LOCAL_CALIBRATION_REPORT_V1"

    def test_empty_has_advisory_label(self):
        report = build_calibration_report([])
        assert report.advisory_label == "ADVISORY_ONLY_RESEARCH_USEFULNESS_AUDIT"

    def test_empty_has_no_records_warning(self):
        report = build_calibration_report([])
        assert "no_records" in report.warnings

    def test_empty_input_summary_zero_counts(self):
        report = build_calibration_report([])
        assert report.input_summary["record_count"] == 0
        assert report.input_summary["valid_record_count"] == 0
        assert report.input_summary["invalid_record_count"] == 0

    def test_empty_has_forbidden_interpretation_notice(self):
        report = build_calibration_report([])
        assert report.forbidden_interpretation_notice


# ---------------------------------------------------------------------------
# 2. Report scope safety booleans
# ---------------------------------------------------------------------------


class TestReportScope:
    def _scope(self) -> dict:
        return dict(build_calibration_report([]).report_scope)

    def test_scope_local_offline_read_only(self):
        assert self._scope()["local_offline_read_only"] is True

    def test_scope_no_network(self):
        assert self._scope()["no_network"] is True

    def test_scope_no_trading(self):
        assert self._scope()["no_trading"] is True

    def test_scope_no_profitability_metrics(self):
        assert self._scope()["no_profitability_metrics"] is True

    def test_scope_no_paper_trading(self):
        assert self._scope()["no_paper_trading"] is True

    def test_scope_no_live_trading(self):
        assert self._scope()["no_live_trading"] is True

    def test_scope_no_order_or_position_inputs(self):
        assert self._scope()["no_order_or_position_inputs"] is True

    def test_scope_no_file_writes(self):
        assert self._scope()["no_file_writes"] is True

    def test_scope_no_strategy_output(self):
        assert self._scope()["no_strategy_output"] is True


# ---------------------------------------------------------------------------
# 3. Valid records — input summary and coverage summary
# ---------------------------------------------------------------------------


class TestValidRecords:
    def test_valid_records_populate_input_summary(self):
        report = build_calibration_report([_valid_record(), _valid_record()])
        assert report.input_summary["record_count"] == 2
        assert report.input_summary["valid_record_count"] == 2
        assert report.input_summary["invalid_record_count"] == 0

    def test_valid_records_coverage_rate_is_one(self):
        report = build_calibration_report([_valid_record()])
        assert report.coverage_summary["coverage_rate"] == 1.0

    def test_valid_records_no_warnings(self):
        report = build_calibration_report([_valid_record()])
        assert "no_records" not in report.warnings
        assert "all_records_invalid" not in report.warnings


# ---------------------------------------------------------------------------
# 4. Invalid records — validation and missingness summaries
# ---------------------------------------------------------------------------


class TestInvalidRecords:
    def test_invalid_records_populate_validation_summary(self):
        report = build_calibration_report([_invalid_record()])
        assert report.validation_summary["warning_count"] >= 0
        assert report.input_summary["invalid_record_count"] == 1
        assert report.input_summary["valid_record_count"] == 0

    def test_invalid_records_missing_required_field_rate(self):
        report = build_calibration_report([_invalid_record()])
        assert report.missingness_summary["missing_required_field_rate"] == 1.0

    def test_all_invalid_adds_all_records_invalid_warning(self):
        report = build_calibration_report([_invalid_record()])
        assert "all_records_invalid" in report.warnings


# ---------------------------------------------------------------------------
# 5. Stale records — staleness summary
# ---------------------------------------------------------------------------


class TestStalenessRecords:
    def test_stale_record_staleness_rate_is_one(self):
        report = build_calibration_report([_stale_record()])
        assert report.staleness_summary["staleness_rate"] == 1.0

    def test_mixed_staleness_rate(self):
        report = build_calibration_report([_valid_record(), _stale_record()])
        assert report.staleness_summary["staleness_rate"] == 0.5


# ---------------------------------------------------------------------------
# 6. Missing resolution source — resolution source summary
# ---------------------------------------------------------------------------


class TestResolutionSourceSummary:
    def test_missing_resolution_source_rate(self):
        report = build_calibration_report([_missing_resolution_source_record()])
        assert report.resolution_source_summary["resolution_source_missing_rate"] == 1.0

    def test_source_metadata_available_rate_with_valid(self):
        report = build_calibration_report([_valid_record()])
        assert report.resolution_source_summary["source_metadata_available_rate"] == 1.0


# ---------------------------------------------------------------------------
# 7. Manual review flags — manual review summary
# ---------------------------------------------------------------------------


class TestManualReviewSummary:
    def test_manual_review_required_rate(self):
        report = build_calibration_report([_manual_review_record()])
        assert report.manual_review_summary["manual_review_required_rate"] == 1.0

    def test_no_manual_review_rate_with_valid(self):
        report = build_calibration_report([_valid_record()])
        assert report.manual_review_summary["manual_review_required_rate"] == 0.0

    def test_ambiguity_review_required_rate(self):
        r = _valid_record()
        r["research_queue_state"] = dict(r["research_queue_state"])
        r["research_queue_state"]["resolution_ambiguity_manual_review_required"] = True
        report = build_calibration_report([r])
        assert report.manual_review_summary["ambiguity_review_required_rate"] == 1.0


# ---------------------------------------------------------------------------
# 8. Bucket distribution passed through
# ---------------------------------------------------------------------------


class TestBucketSummary:
    def test_bucket_distribution_passed_through(self):
        r1 = _valid_record()
        r2 = _valid_record()
        r2["research_queue_state"] = dict(r2["research_queue_state"])
        r2["research_queue_state"]["research_queue_bucket"] = "REVIEW_LATER"
        report = build_calibration_report([r1, r2])
        dist = report.bucket_summary["bucket_distribution"]
        assert dist.get("REVIEW_FIRST", 0) == 1
        assert dist.get("REVIEW_LATER", 0) == 1

    def test_empty_bucket_distribution_on_empty_input(self):
        report = build_calibration_report([])
        assert report.bucket_summary["bucket_distribution"] == {}


# ---------------------------------------------------------------------------
# 9. Human review usefulness label distribution passed through
# ---------------------------------------------------------------------------


class TestHumanReviewUsefulness:
    def test_label_distribution_passed_through(self):
        report = build_calibration_report([_valid_record()])
        dist = report.human_review_usefulness_summary["human_review_usefulness_label_distribution"]
        assert dist.get("USEFUL_RESEARCH_TARGET", 0) == 1

    def test_empty_label_distribution_on_empty_input(self):
        report = build_calibration_report([])
        dist = report.human_review_usefulness_summary["human_review_usefulness_label_distribution"]
        assert dist == {}


# ---------------------------------------------------------------------------
# 10 & 11. Excluded record count and post-resolution audit warning count
# ---------------------------------------------------------------------------


class TestExcludedRecordSummary:
    def test_excluded_record_count_passed_through(self):
        report = build_calibration_report([_excluded_record()])
        assert report.excluded_record_summary["excluded_record_count"] == 1

    def test_post_resolution_audit_warning_count_passed_through(self):
        report = build_calibration_report([_post_resolution_audit_record()])
        assert report.excluded_record_summary["post_resolution_audit_warning_count"] == 1

    def test_zero_excluded_on_valid_records(self):
        report = build_calibration_report([_valid_record()])
        assert report.excluded_record_summary["excluded_record_count"] == 0
        assert report.excluded_record_summary["post_resolution_audit_warning_count"] == 0


# ---------------------------------------------------------------------------
# 12 & 13. Metric warnings included and deterministic
# ---------------------------------------------------------------------------


class TestWarnings:
    def test_metric_warnings_in_report_warnings(self):
        # Force missing_required_field_rate_high by using all invalid records (> 50%)
        records = [_invalid_record()] * 2 + [_valid_record()]
        report = build_calibration_report(records)
        assert "missing_required_field_rate_high" in report.warnings

    def test_report_warnings_are_sorted_tuple(self):
        report = build_calibration_report([_invalid_record()])
        assert isinstance(report.warnings, tuple)
        assert list(report.warnings) == sorted(report.warnings)

    def test_warnings_are_deterministic_same_input(self):
        records = [_invalid_record()]
        report1 = build_calibration_report(records)
        report2 = build_calibration_report(records)
        assert report1.warnings == report2.warnings

    def test_validation_summary_includes_warning_count(self):
        report = build_calibration_report([_invalid_record()])
        assert "warning_count" in report.validation_summary
        assert isinstance(report.validation_summary["warning_count"], int)


# ---------------------------------------------------------------------------
# 14. Forbidden interpretation notice
# ---------------------------------------------------------------------------


class TestForbiddenInterpretationNotice:
    def _notice(self) -> str:
        return build_calibration_report([]).forbidden_interpretation_notice

    def test_notice_is_non_empty_string(self):
        assert isinstance(self._notice(), str)
        assert len(self._notice()) > 0

    def test_notice_contains_advisory_only(self):
        assert "advisory-only" in self._notice().lower() or "advisory only" in self._notice().lower()

    def test_notice_contains_not_trading_language(self):
        notice_lower = self._notice().lower()
        # Notice must mention it is not a trading signal / report
        assert "not a trading signal" in notice_lower or "trading signal" in notice_lower or "not a" in notice_lower

    def test_notice_contains_not_backtest(self):
        notice_lower = self._notice().lower()
        assert "backtest" in notice_lower

    def test_notice_contains_not_profitability(self):
        notice_lower = self._notice().lower()
        assert "profitability" in notice_lower or "profit" in notice_lower


# ---------------------------------------------------------------------------
# 15. Frozen dataclass / determinism
# ---------------------------------------------------------------------------


class TestFrozenDataclass:
    def test_report_is_frozen_dataclass(self):
        report = build_calibration_report([_valid_record()])
        assert dataclasses.is_dataclass(report)
        with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
            report.report_type = "MUTATED"  # type: ignore[misc]

    def test_same_input_produces_equal_reports(self):
        records = [_valid_record()]
        r1 = build_calibration_report(records)
        r2 = build_calibration_report(records)
        assert r1 == r2

    def test_dataclass_fields_include_all_required_sections(self):
        field_names = {f.name for f in dataclasses.fields(LocalCalibrationReport)}
        required = {
            "report_type",
            "advisory_label",
            "report_scope",
            "input_summary",
            "validation_summary",
            "coverage_summary",
            "missingness_summary",
            "staleness_summary",
            "resolution_source_summary",
            "manual_review_summary",
            "bucket_summary",
            "human_review_usefulness_summary",
            "excluded_record_summary",
            "warnings",
            "forbidden_interpretation_notice",
        }
        assert required.issubset(field_names)


# ---------------------------------------------------------------------------
# 16. Generator imports no network libraries
# ---------------------------------------------------------------------------


class TestNoNetworkImports:
    def test_generator_module_imports_no_network_libraries(self):
        import src.data_layer.calibration_report_generator as mod
        source = inspect.getsource(mod)
        forbidden_network_imports = [
            "import requests",
            "import httpx",
            "import aiohttp",
            "import urllib.request",
            "from requests",
            "from httpx",
            "from aiohttp",
            "import socket",
            "import http.client",
        ]
        for forbidden in forbidden_network_imports:
            assert forbidden not in source, (
                f"Report generator must not import network library: {forbidden!r}"
            )


# ---------------------------------------------------------------------------
# 17. Generator performs no file reads/writes
# ---------------------------------------------------------------------------


class TestNoFileIO:
    def test_generator_module_has_no_file_write_patterns(self):
        import src.data_layer.calibration_report_generator as mod
        source = inspect.getsource(mod)
        forbidden_io = [
            ".write(",
            ".open(",
            "open(",
            "Path.write_",
            "write_text(",
            "write_bytes(",
        ]
        for pattern in forbidden_io:
            assert pattern not in source, (
                f"Report generator must not perform file I/O: {pattern!r}"
            )

    def test_generator_module_has_no_file_read_patterns_in_public_api(self):
        import src.data_layer.calibration_report_generator as mod
        source = inspect.getsource(mod)
        # The generator must not directly open or read files
        assert "read_text(" not in source
        assert "read_bytes(" not in source


# ---------------------------------------------------------------------------
# 18. Generator references no credentials / .env / wallet
# ---------------------------------------------------------------------------


class TestNoCredentials:
    def test_generator_module_has_no_credential_patterns(self):
        import src.data_layer.calibration_report_generator as mod
        source = inspect.getsource(mod)
        forbidden_credential_terms = [
            "PRIVATE_KEY",
            "API_KEY",
            "SECRET",
            ".env",
            "wallet",
            "seed_phrase",
            "mnemonic",
            "getenv",
            "os.environ",
            "authenticated",
        ]
        for term in forbidden_credential_terms:
            assert term not in source, (
                f"Report generator must not reference credential term: {term!r}"
            )


# ---------------------------------------------------------------------------
# 19. Generator exposes no forbidden positive trading/performance fields
# ---------------------------------------------------------------------------


class TestNoForbiddenPositiveFields:
    def test_forbidden_report_fields_constant_exists(self):
        assert isinstance(FORBIDDEN_REPORT_FIELDS, frozenset)
        assert len(FORBIDDEN_REPORT_FIELDS) > 0

    def test_dataclass_fields_not_in_forbidden_set(self):
        field_names = {f.name for f in dataclasses.fields(LocalCalibrationReport)}
        overlap = field_names & FORBIDDEN_REPORT_FIELDS
        assert overlap == set(), (
            f"LocalCalibrationReport has forbidden positive field names: {overlap}"
        )

    def test_report_type_string_not_in_forbidden_fields(self):
        report = build_calibration_report([])
        assert report.report_type not in FORBIDDEN_REPORT_FIELDS

    def test_report_summary_keys_not_in_forbidden_set(self):
        report = build_calibration_report([_valid_record()])
        summary_dicts = [
            report.input_summary,
            report.coverage_summary,
            report.missingness_summary,
            report.staleness_summary,
            report.resolution_source_summary,
            report.manual_review_summary,
            report.bucket_summary,
            report.human_review_usefulness_summary,
            report.excluded_record_summary,
        ]
        for summary in summary_dicts:
            for key in summary:
                assert key not in FORBIDDEN_REPORT_FIELDS, (
                    f"Summary key {key!r} is in FORBIDDEN_REPORT_FIELDS"
                )


# ---------------------------------------------------------------------------
# build_calibration_report_from_load_result compatibility
# ---------------------------------------------------------------------------


class TestLoadResultIntegration:
    def test_from_load_result_same_report_type(self):
        lr = _load_result_from_records([_valid_record()])
        report = build_calibration_report_from_load_result(lr)
        assert report.report_type == "LOCAL_CALIBRATION_REPORT_V1"

    def test_from_load_result_empty_records_no_records_warning(self):
        lr = _load_result_from_records([])
        report = build_calibration_report_from_load_result(lr)
        assert "no_records" in report.warnings

    def test_from_load_result_matches_direct_build_on_same_records(self):
        records = [_valid_record(), _invalid_record()]
        lr = _load_result_from_records(records)
        report_direct = build_calibration_report(records)
        report_lr = build_calibration_report_from_load_result(lr)
        # Core counts should match
        assert report_direct.input_summary["record_count"] == report_lr.input_summary["record_count"]
        assert report_direct.input_summary["valid_record_count"] == report_lr.input_summary["valid_record_count"]
        assert report_direct.coverage_summary["coverage_rate"] == report_lr.coverage_summary["coverage_rate"]


# ---------------------------------------------------------------------------
# Compatibility: WP70 metrics module importable alongside report generator
# ---------------------------------------------------------------------------


class TestCompatibility:
    def test_wp70_metrics_module_importable(self):
        mod = importlib.import_module("src.data_layer.calibration_metric_computation")
        assert hasattr(mod, "compute_calibration_metrics")
        assert hasattr(mod, "CalibrationMetricComputationResult")

    def test_wp68_loader_module_importable(self):
        mod = importlib.import_module("src.data_layer.resolved_outcome_fixture_loader")
        assert hasattr(mod, "load_resolved_outcome_fixtures")
        assert hasattr(mod, "ResolvedOutcomeFixtureLoadResult")

    def test_wp67_validator_module_importable(self):
        mod = importlib.import_module("src.data_layer.calibration_record_validation")
        assert hasattr(mod, "validate_calibration_record")

    def test_report_generator_does_not_import_metric_computation_internals(self):
        import src.data_layer.calibration_report_generator as mod
        source = inspect.getsource(mod)
        # Must use the public API; should not duplicate internal functions
        assert "_compute_from_pairs" not in source
        assert "_is_record_stale" not in source
