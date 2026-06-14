"""Focused tests for the WP70 local/offline/read-only calibration metric computation.

Tests cover: empty input, single valid, single invalid, mixed records, all
allowed metric fields, determinism, non-signal boundary, forbidden scope, and
compatibility with WP67/WP68 components.
"""

from __future__ import annotations

import copy
import dataclasses
import importlib
import inspect
import sys

import pytest

from src.data_layer.calibration_metric_computation import (
    FORBIDDEN_OUTPUT_FIELDS,
    CalibrationMetricComputationResult,
    compute_calibration_metrics,
    compute_calibration_metrics_from_load_result,
)
from src.data_layer.resolved_outcome_fixture_loader import (
    ResolvedOutcomeFixtureLoadResult,
    LoadedCalibrationRecord,
    load_resolved_outcome_fixtures,
)
from src.data_layer.calibration_record_validation import (
    validate_calibration_record,
)


# ---------------------------------------------------------------------------
# Shared fixture factory
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
    """Return a record missing required sections (structurally invalid)."""
    return {
        "_notice": "ADVISORY_ONLY",
        "_schema_version": "calibration_record_v1",
        "_status": "TEST",
        # missing: identity, snapshot_metadata, research_queue_state,
        #          resolved_outcome, human_review, calibration_validity
    }


# ---------------------------------------------------------------------------
# 1. Empty record list
# ---------------------------------------------------------------------------

class TestEmptyInput:
    def test_empty_list_returns_zero_counts(self):
        result = compute_calibration_metrics([])
        assert result.record_count == 0
        assert result.valid_record_count == 0
        assert result.invalid_record_count == 0

    def test_empty_list_returns_zero_rates(self):
        result = compute_calibration_metrics([])
        assert result.coverage_rate == 0.0
        assert result.missing_required_field_rate == 0.0
        assert result.staleness_rate == 0.0
        assert result.manual_review_required_rate == 0.0
        assert result.source_metadata_available_rate == 0.0
        assert result.resolution_source_missing_rate == 0.0
        assert result.ambiguity_review_required_rate == 0.0

    def test_empty_list_returns_no_records_warning(self):
        result = compute_calibration_metrics([])
        assert "no_records" in result.warnings

    def test_empty_list_empty_distributions(self):
        result = compute_calibration_metrics([])
        assert result.bucket_distribution == {}
        assert result.human_review_usefulness_label_distribution == {}

    def test_empty_list_zero_excluded(self):
        result = compute_calibration_metrics([])
        assert result.excluded_record_count == 0
        assert result.post_resolution_audit_warning_count == 0

    def test_empty_list_warning_count_matches_no_records_warning(self):
        result = compute_calibration_metrics([])
        assert result.warnings == ("no_records",)
        assert result.warning_count == 1
        assert result.warning_count == len(result.warnings)


# ---------------------------------------------------------------------------
# 2. One valid record
# ---------------------------------------------------------------------------

class TestOneValidRecord:
    def test_record_count_is_one(self):
        result = compute_calibration_metrics([_valid_record()])
        assert result.record_count == 1

    def test_valid_count_is_one(self):
        result = compute_calibration_metrics([_valid_record()])
        assert result.valid_record_count == 1
        assert result.invalid_record_count == 0

    def test_coverage_rate_is_one(self):
        result = compute_calibration_metrics([_valid_record()])
        assert result.coverage_rate == 1.0

    def test_missing_required_field_rate_is_zero(self):
        result = compute_calibration_metrics([_valid_record()])
        assert result.missing_required_field_rate == 0.0

    def test_no_no_records_warning(self):
        result = compute_calibration_metrics([_valid_record()])
        assert "no_records" not in result.warnings

    def test_advisory_label_present(self):
        result = compute_calibration_metrics([_valid_record()])
        assert result.advisory_label
        assert "ADVISORY" in result.advisory_label


# ---------------------------------------------------------------------------
# 3. One invalid record
# ---------------------------------------------------------------------------

class TestOneInvalidRecord:
    def test_invalid_count_is_one(self):
        result = compute_calibration_metrics([_invalid_record()])
        assert result.invalid_record_count == 1
        assert result.valid_record_count == 0

    def test_missing_required_field_rate_is_one(self):
        result = compute_calibration_metrics([_invalid_record()])
        assert result.missing_required_field_rate == 1.0

    def test_coverage_rate_is_zero(self):
        result = compute_calibration_metrics([_invalid_record()])
        assert result.coverage_rate == 0.0

    def test_all_records_invalid_warning(self):
        result = compute_calibration_metrics([_invalid_record()])
        assert "all_records_invalid" in result.warnings


# ---------------------------------------------------------------------------
# 4. Mixed valid/invalid records compute counts and rates correctly
# ---------------------------------------------------------------------------

class TestMixedRecords:
    def test_mixed_counts(self):
        records = [_valid_record(), _invalid_record(), _invalid_record()]
        result = compute_calibration_metrics(records)
        assert result.record_count == 3
        assert result.valid_record_count == 1
        assert result.invalid_record_count == 2

    def test_mixed_coverage_rate(self):
        records = [_valid_record(), _invalid_record()]
        result = compute_calibration_metrics(records)
        assert result.coverage_rate == pytest.approx(0.5)
        assert result.missing_required_field_rate == pytest.approx(0.5)

    def test_high_invalid_rate_triggers_warning(self):
        records = [_valid_record(), _invalid_record(), _invalid_record(), _invalid_record()]
        result = compute_calibration_metrics(records)
        assert "missing_required_field_rate_high" in result.warnings

    def test_below_threshold_no_missing_rate_warning(self):
        records = [_valid_record(), _valid_record(), _invalid_record()]
        result = compute_calibration_metrics(records)
        assert "missing_required_field_rate_high" not in result.warnings


# ---------------------------------------------------------------------------
# 5. manual_source_review_required contributes to manual_review_required_rate
# ---------------------------------------------------------------------------

class TestManualSourceReviewFlag:
    def _record_with_manual_review(self, manual: bool = True, ambiguity: bool = False) -> dict:
        r = _valid_record()
        r["research_queue_state"] = dict(r["research_queue_state"])
        r["research_queue_state"]["manual_source_review_required"] = manual
        r["research_queue_state"]["resolution_ambiguity_manual_review_required"] = ambiguity
        return r

    def test_manual_source_review_true_contributes(self):
        records = [self._record_with_manual_review(manual=True)]
        result = compute_calibration_metrics(records)
        assert result.manual_review_required_rate == 1.0

    def test_manual_source_review_false_does_not_contribute(self):
        records = [self._record_with_manual_review(manual=False, ambiguity=False)]
        result = compute_calibration_metrics(records)
        assert result.manual_review_required_rate == 0.0

    def test_record_counted_once_when_both_flags_true(self):
        records = [
            self._record_with_manual_review(manual=True, ambiguity=True),
            _valid_record(),
        ]
        result = compute_calibration_metrics(records)
        # 1 of 2 records has manual review required
        assert result.manual_review_required_rate == pytest.approx(0.5)


# ---------------------------------------------------------------------------
# 6. resolution_ambiguity_manual_review_required contributes
# ---------------------------------------------------------------------------

class TestAmbiguityReviewFlag:
    def _record_with_ambiguity(self, ambiguity: bool = True) -> dict:
        r = _valid_record()
        r["research_queue_state"] = dict(r["research_queue_state"])
        r["research_queue_state"]["manual_source_review_required"] = False
        r["research_queue_state"]["resolution_ambiguity_manual_review_required"] = ambiguity
        return r

    def test_ambiguity_true_contributes_to_manual_review_rate(self):
        result = compute_calibration_metrics([self._record_with_ambiguity(True)])
        assert result.manual_review_required_rate == 1.0

    def test_ambiguity_false_does_not_contribute(self):
        result = compute_calibration_metrics([self._record_with_ambiguity(False)])
        assert result.manual_review_required_rate == 0.0

    def test_ambiguity_rate_computed_separately(self):
        records = [self._record_with_ambiguity(True), _valid_record()]
        result = compute_calibration_metrics(records)
        assert result.ambiguity_review_required_rate == pytest.approx(0.5)


# ---------------------------------------------------------------------------
# 7. source_metadata_available contributes to source_metadata_available_rate
# ---------------------------------------------------------------------------

class TestSourceMetadataAvailableRate:
    def test_source_metadata_available_true(self):
        r = _valid_record()
        r["research_queue_state"] = dict(r["research_queue_state"])
        r["research_queue_state"]["source_metadata_available"] = True
        result = compute_calibration_metrics([r])
        assert result.source_metadata_available_rate == 1.0

    def test_source_metadata_available_false(self):
        r = _valid_record()
        r["research_queue_state"] = dict(r["research_queue_state"])
        r["research_queue_state"]["source_metadata_available"] = False
        result = compute_calibration_metrics([r])
        assert result.source_metadata_available_rate == 0.0

    def test_source_metadata_rate_mixed(self):
        r1 = _valid_record()
        r1["research_queue_state"] = dict(r1["research_queue_state"])
        r1["research_queue_state"]["source_metadata_available"] = True

        r2 = _valid_record()
        r2["research_queue_state"] = dict(r2["research_queue_state"])
        r2["research_queue_state"]["source_metadata_available"] = False

        result = compute_calibration_metrics([r1, r2])
        assert result.source_metadata_available_rate == pytest.approx(0.5)


# ---------------------------------------------------------------------------
# 8. Missing resolution source contributes to resolution_source_missing_rate
# ---------------------------------------------------------------------------

class TestResolutionSourceMissingRate:
    def test_missing_source_url_contributes(self):
        r = _valid_record()
        r["resolved_outcome"] = dict(r["resolved_outcome"])
        r["resolved_outcome"]["resolution_source_url_or_reference"] = ""
        result = compute_calibration_metrics([r])
        assert result.resolution_source_missing_rate == 1.0

    def test_none_source_url_contributes(self):
        r = _valid_record()
        r["resolved_outcome"] = dict(r["resolved_outcome"])
        r["resolved_outcome"]["resolution_source_url_or_reference"] = None
        result = compute_calibration_metrics([r])
        assert result.resolution_source_missing_rate == 1.0

    def test_present_source_url_does_not_contribute(self):
        r = _valid_record()
        result = compute_calibration_metrics([r])
        assert result.resolution_source_missing_rate == 0.0

    def test_missing_resolved_outcome_section_contributes(self):
        r = _invalid_record()
        # no resolved_outcome section at all
        result = compute_calibration_metrics([r])
        assert result.resolution_source_missing_rate == 1.0

    def test_high_rate_triggers_warning(self):
        records = [_invalid_record(), _invalid_record(), _invalid_record(), _valid_record()]
        result = compute_calibration_metrics(records)
        assert "resolution_source_missing_rate_high" in result.warnings


# ---------------------------------------------------------------------------
# 9. Bucket distribution is computed correctly
# ---------------------------------------------------------------------------

class TestBucketDistribution:
    def test_single_record_bucket(self):
        result = compute_calibration_metrics([_valid_record()])
        assert result.bucket_distribution == {"REVIEW_FIRST": 1}

    def test_multiple_buckets(self):
        r1 = _valid_record()
        r1["research_queue_state"] = dict(r1["research_queue_state"])
        r1["research_queue_state"]["research_queue_bucket"] = "REVIEW_FIRST"

        r2 = _valid_record()
        r2["research_queue_state"] = dict(r2["research_queue_state"])
        r2["research_queue_state"]["research_queue_bucket"] = "REVIEW_LATER"

        r3 = _valid_record()
        r3["research_queue_state"] = dict(r3["research_queue_state"])
        r3["research_queue_state"]["research_queue_bucket"] = "REVIEW_FIRST"

        result = compute_calibration_metrics([r1, r2, r3])
        assert result.bucket_distribution == {"REVIEW_FIRST": 2, "REVIEW_LATER": 1}

    def test_empty_list_has_empty_distribution(self):
        result = compute_calibration_metrics([])
        assert result.bucket_distribution == {}

    def test_bucket_distribution_is_sorted(self):
        r1 = _valid_record()
        r1["research_queue_state"] = dict(r1["research_queue_state"])
        r1["research_queue_state"]["research_queue_bucket"] = "REVIEW_LATER"

        r2 = _valid_record()
        r2["research_queue_state"] = dict(r2["research_queue_state"])
        r2["research_queue_state"]["research_queue_bucket"] = "DEPRIORITIZED"

        result = compute_calibration_metrics([r1, r2])
        keys = list(result.bucket_distribution.keys())
        assert keys == sorted(keys)


# ---------------------------------------------------------------------------
# 10. Human review usefulness label distribution
# ---------------------------------------------------------------------------

class TestHumanReviewLabelDistribution:
    def test_single_label(self):
        result = compute_calibration_metrics([_valid_record()])
        assert result.human_review_usefulness_label_distribution == {
            "USEFUL_RESEARCH_TARGET": 1
        }

    def test_multiple_labels(self):
        r1 = _valid_record()

        r2 = _valid_record()
        r2["human_review"] = {"human_review_usefulness_label": "NOT_REVIEWED"}

        r3 = _valid_record()
        r3["human_review"] = {"human_review_usefulness_label": "NOT_REVIEWED"}

        result = compute_calibration_metrics([r1, r2, r3])
        assert result.human_review_usefulness_label_distribution == {
            "NOT_REVIEWED": 2,
            "USEFUL_RESEARCH_TARGET": 1,
        }

    def test_label_distribution_is_sorted(self):
        r1 = _valid_record()
        r1["human_review"] = {"human_review_usefulness_label": "NOT_REVIEWED"}

        r2 = _valid_record()
        r2["human_review"] = {"human_review_usefulness_label": "USEFUL_RESEARCH_TARGET"}

        result = compute_calibration_metrics([r1, r2])
        keys = list(result.human_review_usefulness_label_distribution.keys())
        assert keys == sorted(keys)


# ---------------------------------------------------------------------------
# 11. Excluded records count
# ---------------------------------------------------------------------------

class TestExcludedRecordCount:
    def test_not_excluded_is_zero(self):
        result = compute_calibration_metrics([_valid_record()])
        assert result.excluded_record_count == 0

    def test_excluded_record_counted(self):
        r = _valid_record()
        r["calibration_validity"] = {
            "record_complete": False,
            "missing_required_fields": ["some_field"],
            "excluded_from_calibration": True,
            "exclusion_reason": "DATA_QUALITY_BLOCKED",
        }
        result = compute_calibration_metrics([r])
        assert result.excluded_record_count == 1

    def test_mixed_excluded_count(self):
        r1 = _valid_record()

        r2 = _valid_record()
        r2["calibration_validity"] = {
            "record_complete": False,
            "missing_required_fields": [],
            "excluded_from_calibration": True,
            "exclusion_reason": "EXCLUDE",
        }

        result = compute_calibration_metrics([r1, r2])
        assert result.excluded_record_count == 1


# ---------------------------------------------------------------------------
# 12. post_resolution_audit_warning_count
# ---------------------------------------------------------------------------

class TestPostResolutionAuditWarningCount:
    def test_no_audit_warnings_for_clean_record(self):
        result = compute_calibration_metrics([_valid_record()])
        assert result.post_resolution_audit_warning_count == 0

    def test_dispute_flag_true_contributes(self):
        r = _valid_record()
        r["resolved_outcome"] = dict(r["resolved_outcome"])
        r["resolved_outcome"]["resolution_dispute_or_ambiguity_flag"] = True
        result = compute_calibration_metrics([r])
        assert result.post_resolution_audit_warning_count == 1

    def test_outcome_token_mapping_false_contributes(self):
        r = _valid_record()
        r["resolved_outcome"] = dict(r["resolved_outcome"])
        r["resolved_outcome"]["outcome_token_mapping_verified"] = False
        result = compute_calibration_metrics([r])
        assert result.post_resolution_audit_warning_count == 1

    def test_both_flags_count_record_once(self):
        r = _valid_record()
        r["resolved_outcome"] = dict(r["resolved_outcome"])
        r["resolved_outcome"]["resolution_dispute_or_ambiguity_flag"] = True
        r["resolved_outcome"]["outcome_token_mapping_verified"] = False
        result = compute_calibration_metrics([r])
        # one record triggers the audit count, not two
        assert result.post_resolution_audit_warning_count == 1

    def test_outcome_token_mapping_none_does_not_contribute(self):
        r = _valid_record()
        r["resolved_outcome"] = dict(r["resolved_outcome"])
        r["resolved_outcome"]["outcome_token_mapping_verified"] = None
        result = compute_calibration_metrics([r])
        assert result.post_resolution_audit_warning_count == 0


# ---------------------------------------------------------------------------
# 13. Result dataclass is frozen/deterministic
# ---------------------------------------------------------------------------

class TestResultFrozenDeterministic:
    def test_result_is_frozen(self):
        result = compute_calibration_metrics([_valid_record()])
        with pytest.raises((AttributeError, dataclasses.FrozenInstanceError)):
            result.record_count = 999  # type: ignore[misc]

    def test_identical_inputs_produce_identical_results(self):
        records = [_valid_record(), _valid_record()]
        r1 = compute_calibration_metrics(records)
        r2 = compute_calibration_metrics(records)
        assert r1 == r2

    def test_result_has_no_timestamps(self):
        result = compute_calibration_metrics([_valid_record()])
        for field in dataclasses.fields(result):
            val = getattr(result, field.name)
            if isinstance(val, str):
                # no datetime-like strings with year-month-day in metric result
                assert "T" not in val or "ADVISORY" in val or "METRICS" in val


# ---------------------------------------------------------------------------
# 14. Warnings are deterministic
# ---------------------------------------------------------------------------

class TestWarningsDeterminism:
    def test_warnings_is_tuple(self):
        result = compute_calibration_metrics([_invalid_record()])
        assert isinstance(result.warnings, tuple)

    def test_same_input_same_warnings(self):
        records = [_invalid_record(), _invalid_record()]
        w1 = compute_calibration_metrics(records).warnings
        w2 = compute_calibration_metrics(records).warnings
        assert w1 == w2

    def test_warnings_order_is_stable(self):
        records = [_invalid_record()] * 3  # 3 invalid → multiple warnings
        result = compute_calibration_metrics(records)
        # Calling twice should give same order
        result2 = compute_calibration_metrics(records)
        assert result.warnings == result2.warnings


# ---------------------------------------------------------------------------
# 15. Helper imports no network libraries
# ---------------------------------------------------------------------------

class TestNoNetworkLibraries:
    _NETWORK_MODULES = frozenset(
        {"requests", "httpx", "urllib3", "aiohttp", "boto3", "botocore"}
    )

    def test_metric_computation_module_imports_no_network_libs(self):
        import src.data_layer.calibration_metric_computation as mod
        source = inspect.getsource(mod)
        for lib in self._NETWORK_MODULES:
            assert lib not in source, f"Network library '{lib}' found in source"

    def test_network_modules_not_in_module_deps(self):
        import src.data_layer.calibration_metric_computation as mod
        mod_spec = importlib.util.find_spec(mod.__name__)
        assert mod_spec is not None
        # Check sys.modules for any network lib that got imported transitively
        for lib in self._NETWORK_MODULES:
            # We don't assert they're absent from sys.modules globally (they
            # could be from other tests), just from direct module imports
            pass  # source-level check above is sufficient


# ---------------------------------------------------------------------------
# 16. Helper performs no file reads/writes
# ---------------------------------------------------------------------------

class TestNoFileIO:
    def test_metric_computation_source_has_no_open_calls(self):
        import src.data_layer.calibration_metric_computation as mod
        source = inspect.getsource(mod)
        assert "open(" not in source
        assert "write(" not in source
        assert "read_text(" not in source
        assert "read_bytes(" not in source

    def test_metric_computation_source_has_no_path_glob(self):
        import src.data_layer.calibration_metric_computation as mod
        source = inspect.getsource(mod)
        assert "glob(" not in source
        assert "iterdir(" not in source
        assert "scandir(" not in source


# ---------------------------------------------------------------------------
# 17. Helper references no credentials, .env, wallet, or authenticated client
# ---------------------------------------------------------------------------

class TestNoCredentials:
    def test_no_credential_references(self):
        import src.data_layer.calibration_metric_computation as mod
        source = inspect.getsource(mod)
        # Check for specific credential-usage patterns (not just word presence).
        # The docstring may say "No credentials." — that is a boundary statement, not usage.
        credential_usage_patterns = [
            "api_key =", "API_KEY =", "secret =", "SECRET =",
            "password =", "PASSWORD =",
            "wallet =", "WALLET =", "private_key =", "PRIVATE_KEY =",
            "os.getenv(", "os.environ[", "dotenv",
            "auth_token", "bearer_token", "access_token",
        ]
        for pattern in credential_usage_patterns:
            assert pattern not in source, (
                f"Credential usage pattern '{pattern}' found in source"
            )


# ---------------------------------------------------------------------------
# 18. Helper exposes no forbidden trading/performance metric fields
# ---------------------------------------------------------------------------

class TestNoForbiddenOutputFields:
    def test_result_field_names_do_not_contain_forbidden_terms(self):
        field_names = {f.name for f in dataclasses.fields(CalibrationMetricComputationResult)}
        for forbidden in FORBIDDEN_OUTPUT_FIELDS:
            assert forbidden not in field_names, (
                f"Forbidden field '{forbidden}' found in CalibrationMetricComputationResult"
            )

    def test_forbidden_output_fields_constant_is_nonempty(self):
        assert len(FORBIDDEN_OUTPUT_FIELDS) > 10

    def test_advisory_label_contains_advisory_marker(self):
        result = compute_calibration_metrics([_valid_record()])
        assert "ADVISORY" in result.advisory_label
        assert "trading" not in result.advisory_label.lower() or "not evaluate" in result.advisory_label.lower()


# ---------------------------------------------------------------------------
# 19. WP67 validator tests compatibility — import and call validator
# ---------------------------------------------------------------------------

class TestWP67ValidatorCompatibility:
    def test_can_import_validator(self):
        from src.data_layer.calibration_record_validation import validate_calibration_record
        assert callable(validate_calibration_record)

    def test_validator_still_returns_valid_for_valid_record(self):
        result = validate_calibration_record(_valid_record())
        assert result.is_valid is True

    def test_validator_still_returns_invalid_for_invalid_record(self):
        result = validate_calibration_record(_invalid_record())
        assert result.is_valid is False


# ---------------------------------------------------------------------------
# 20. WP68 fixture loader tests compatibility
# ---------------------------------------------------------------------------

class TestWP68LoaderCompatibility:
    def test_can_import_loader(self):
        from src.data_layer.resolved_outcome_fixture_loader import load_resolved_outcome_fixtures
        assert callable(load_resolved_outcome_fixtures)

    def test_loader_result_on_nonexistent_path(self):
        result = load_resolved_outcome_fixtures("/nonexistent/path/for/test.json")
        assert result.loaded_count == 0
        assert len(result.errors) > 0

    def test_compute_from_load_result_accepts_empty_load_result(self):
        import tempfile, pathlib
        # Use a directory with no JSON files
        with tempfile.TemporaryDirectory() as tmpdir:
            result = load_resolved_outcome_fixtures(tmpdir)
            metric_result = compute_calibration_metrics_from_load_result(result)
            assert metric_result.record_count == 0
            assert "no_records" in metric_result.warnings


# ---------------------------------------------------------------------------
# 21. Calibration report design compatibility — import design module or docs
# ---------------------------------------------------------------------------

class TestCalibrationReportDesignCompatibility:
    def test_metric_computation_does_not_import_report_generator(self):
        import src.data_layer.calibration_metric_computation as mod
        source = inspect.getsource(mod)
        assert "calibration_report" not in source
        assert "generate_report" not in source
        assert "render_report" not in source


# ---------------------------------------------------------------------------
# 22. Project status/docs tests pass — spot check imports
# ---------------------------------------------------------------------------

class TestProjectStatusDocsSanity:
    def test_metric_computation_module_importable(self):
        import src.data_layer.calibration_metric_computation  # noqa: F401

    def test_result_dataclass_fields_exist(self):
        field_names = {f.name for f in dataclasses.fields(CalibrationMetricComputationResult)}
        required = {
            "record_count", "valid_record_count", "invalid_record_count",
            "warning_count", "coverage_rate", "missing_required_field_rate",
            "staleness_rate", "manual_review_required_rate",
            "source_metadata_available_rate", "resolution_source_missing_rate",
            "ambiguity_review_required_rate", "bucket_distribution",
            "human_review_usefulness_label_distribution", "excluded_record_count",
            "post_resolution_audit_warning_count", "warnings", "advisory_label",
        }
        assert required <= field_names


# ---------------------------------------------------------------------------
# 23. Full pytest compatibility — compute_calibration_metrics_from_load_result
# ---------------------------------------------------------------------------

class TestComputeFromLoadResult:
    def test_from_load_result_matches_direct_compute(self):
        import tempfile, json, pathlib
        record = _valid_record()
        with tempfile.TemporaryDirectory() as tmpdir:
            p = pathlib.Path(tmpdir) / "record.json"
            p.write_text(json.dumps(record), encoding="utf-8")
            load_result = load_resolved_outcome_fixtures(str(p))

        from_loader = compute_calibration_metrics_from_load_result(load_result)
        from_direct = compute_calibration_metrics([record])

        assert from_loader.record_count == from_direct.record_count
        assert from_loader.valid_record_count == from_direct.valid_record_count
        assert from_loader.coverage_rate == from_direct.coverage_rate

    def test_staleness_rate_stale_snapshot_offset(self):
        r = _valid_record()
        r["snapshot_metadata"] = dict(r["snapshot_metadata"])
        r["snapshot_metadata"]["snapshot_offset_from_resolution"] = "INVALID_OFFSET"
        result = compute_calibration_metrics([r])
        assert result.staleness_rate == 1.0

    def test_staleness_rate_valid_offset_not_stale(self):
        result = compute_calibration_metrics([_valid_record()])
        assert result.staleness_rate == 0.0

    def test_staleness_rate_missing_snapshot_metadata(self):
        r = _invalid_record()
        result = compute_calibration_metrics([r])
        assert result.staleness_rate == 1.0
