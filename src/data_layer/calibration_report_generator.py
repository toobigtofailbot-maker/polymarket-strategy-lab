"""Local/offline/read-only calibration report generator.

Builds an in-memory LocalCalibrationReport from already-loaded calibration
records or a WP68 ResolvedOutcomeFixtureLoadResult.

Does not read or write files.
Does not compute trading performance, profitability, or signal quality metrics.
Does not fetch resolved outcomes from any network source.
Stdlib-only. No network access. No credentials.

Added in WP71.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping

from src.data_layer.calibration_metric_computation import (
    FORBIDDEN_OUTPUT_FIELDS,
    CalibrationMetricComputationResult,
    compute_calibration_metrics,
    compute_calibration_metrics_from_load_result,
)
from src.data_layer.resolved_outcome_fixture_loader import (
    ResolvedOutcomeFixtureLoadResult,
)


_REPORT_TYPE = "LOCAL_CALIBRATION_REPORT_V1"
_ADVISORY_LABEL = "ADVISORY_ONLY_RESEARCH_USEFULNESS_AUDIT"

_REPORT_SCOPE: dict[str, object] = {
    "local_offline_read_only": True,
    "no_network": True,
    "no_trading": True,
    "no_profitability_metrics": True,
    "no_strategy_output": True,
    "no_paper_trading": True,
    "no_live_trading": True,
    "no_order_or_position_inputs": True,
    "no_file_writes": True,
}

_FORBIDDEN_INTERPRETATION_NOTICE = (
    "This local calibration report is an advisory-only research-usefulness audit. "
    "It is not a trading signal, profitability report, strategy backtest, "
    "expected-return model, position-sizing input, execution-quality report, "
    "paper-trading report, or live-trading report."
)

# Exposed for use in boundary tests — mirrors WP70 FORBIDDEN_OUTPUT_FIELDS.
FORBIDDEN_REPORT_FIELDS: frozenset[str] = FORBIDDEN_OUTPUT_FIELDS


@dataclass(frozen=True)
class LocalCalibrationReport:
    report_type: str
    advisory_label: str
    report_scope: Mapping[str, object]
    input_summary: Mapping[str, object]
    validation_summary: Mapping[str, object]
    coverage_summary: Mapping[str, object]
    missingness_summary: Mapping[str, object]
    staleness_summary: Mapping[str, object]
    resolution_source_summary: Mapping[str, object]
    manual_review_summary: Mapping[str, object]
    bucket_summary: Mapping[str, object]
    human_review_usefulness_summary: Mapping[str, object]
    excluded_record_summary: Mapping[str, object]
    warnings: tuple[str, ...]
    forbidden_interpretation_notice: str


def _build_report_from_metrics(
    metrics: CalibrationMetricComputationResult,
) -> LocalCalibrationReport:
    report_warnings: list[str] = list(metrics.warnings)
    if metrics.record_count == 0 and "no_records" not in report_warnings:
        report_warnings.append("no_records")
    if (
        metrics.valid_record_count == 0
        and metrics.record_count > 0
        and "all_records_invalid" not in report_warnings
    ):
        report_warnings.append("all_records_invalid")
    report_warnings_tuple = tuple(sorted(set(report_warnings)))

    return LocalCalibrationReport(
        report_type=_REPORT_TYPE,
        advisory_label=_ADVISORY_LABEL,
        report_scope=dict(_REPORT_SCOPE),
        input_summary={
            "record_count": metrics.record_count,
            "valid_record_count": metrics.valid_record_count,
            "invalid_record_count": metrics.invalid_record_count,
        },
        validation_summary={
            "warning_count": metrics.warning_count,
            "warnings": metrics.warnings,
        },
        coverage_summary={
            "coverage_rate": metrics.coverage_rate,
        },
        missingness_summary={
            "missing_required_field_rate": metrics.missing_required_field_rate,
        },
        staleness_summary={
            "staleness_rate": metrics.staleness_rate,
        },
        resolution_source_summary={
            "source_metadata_available_rate": metrics.source_metadata_available_rate,
            "resolution_source_missing_rate": metrics.resolution_source_missing_rate,
        },
        manual_review_summary={
            "manual_review_required_rate": metrics.manual_review_required_rate,
            "ambiguity_review_required_rate": metrics.ambiguity_review_required_rate,
        },
        bucket_summary={
            "bucket_distribution": metrics.bucket_distribution,
        },
        human_review_usefulness_summary={
            "human_review_usefulness_label_distribution": metrics.human_review_usefulness_label_distribution,
        },
        excluded_record_summary={
            "excluded_record_count": metrics.excluded_record_count,
            "post_resolution_audit_warning_count": metrics.post_resolution_audit_warning_count,
        },
        warnings=report_warnings_tuple,
        forbidden_interpretation_notice=_FORBIDDEN_INTERPRETATION_NOTICE,
    )


def build_calibration_report(
    records: Iterable[Mapping[str, object]],
) -> LocalCalibrationReport:
    """Build an in-memory LocalCalibrationReport from an iterable of calibration records.

    Uses WP70 metric computation. Does not read files, write files, or access the network.
    """
    metrics = compute_calibration_metrics(records)
    return _build_report_from_metrics(metrics)


def build_calibration_report_from_load_result(
    load_result: ResolvedOutcomeFixtureLoadResult,
) -> LocalCalibrationReport:
    """Build an in-memory LocalCalibrationReport from a WP68 ResolvedOutcomeFixtureLoadResult.

    Uses WP70 metric computation. Does not read files, write files, or access the network.
    """
    metrics = compute_calibration_metrics_from_load_result(load_result)
    return _build_report_from_metrics(metrics)
