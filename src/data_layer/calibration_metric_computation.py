"""Local/offline/read-only calibration metric computation.

Computes research-quality and data-completeness metrics from loaded and
validated calibration records.

Does not read or write files.
Does not compute trading performance, profitability, or signal quality metrics.
Does not fetch resolved outcomes from any network source.
Stdlib-only. No network access. No credentials.

Added in WP70.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence

from src.data_layer.calibration_record_validation import (
    ALLOWED_SNAPSHOT_OFFSETS,
    CalibrationRecordValidationResult,
    validate_calibration_record,
)
from src.data_layer.resolved_outcome_fixture_loader import (
    ResolvedOutcomeFixtureLoadResult,
)


_ADVISORY_LABEL = (
    "ADVISORY_ONLY_RESEARCH_USEFULNESS_METRICS — These metrics describe calibration "
    "record coverage, missingness, staleness, and review burden. They do not evaluate "
    "trading performance, profitability, signal quality, or strategy metrics."
)

# Conservative thresholds for research-quality alerting only.
# Not used for scoring or trading decisions.
_HIGH_RATE_THRESHOLD = 0.5

# Forbidden output field names — metric computation must never expose these.
# Stored here for use in boundary tests.
FORBIDDEN_OUTPUT_FIELDS: frozenset[str] = frozenset(
    {
        "profit",
        "pnl",
        "roi",
        "expected_return",
        "win_rate",
        "hit_rate",
        "sharpe",
        "strategy_return",
        "portfolio_return",
        "trade_result",
        "position_size",
        "execution_quality",
        "fill_quality",
        "fill_probability",
        "slippage",
        "edge",
        "alpha",
        "opportunity",
        "arbitrage",
        "mispricing",
        "tradability",
        "buy",
        "sell",
        "entry",
        "exit",
    }
)


@dataclass(frozen=True)
class CalibrationMetricComputationResult:
    record_count: int
    valid_record_count: int
    invalid_record_count: int
    warning_count: int
    coverage_rate: float
    missing_required_field_rate: float
    staleness_rate: float
    manual_review_required_rate: float
    source_metadata_available_rate: float
    resolution_source_missing_rate: float
    ambiguity_review_required_rate: float
    bucket_distribution: Mapping[str, int]
    human_review_usefulness_label_distribution: Mapping[str, int]
    excluded_record_count: int
    post_resolution_audit_warning_count: int
    warnings: tuple[str, ...]
    advisory_label: str


def _safe_rate(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 0.0
    return numerator / denominator


def _is_record_stale(record: Mapping[str, object]) -> bool:
    """Return True if the snapshot offset is missing or not an allowed value."""
    snapshot = record.get("snapshot_metadata")
    if not isinstance(snapshot, dict):
        return True
    offset = snapshot.get("snapshot_offset_from_resolution")
    return offset is None or offset not in ALLOWED_SNAPSHOT_OFFSETS


def _compute_from_pairs(
    pairs: Sequence[tuple[Mapping[str, object], CalibrationRecordValidationResult]],
) -> CalibrationMetricComputationResult:
    record_count = len(pairs)

    if record_count == 0:
        return CalibrationMetricComputationResult(
            record_count=0,
            valid_record_count=0,
            invalid_record_count=0,
            warning_count=0,
            coverage_rate=0.0,
            missing_required_field_rate=0.0,
            staleness_rate=0.0,
            manual_review_required_rate=0.0,
            source_metadata_available_rate=0.0,
            resolution_source_missing_rate=0.0,
            ambiguity_review_required_rate=0.0,
            bucket_distribution={},
            human_review_usefulness_label_distribution={},
            excluded_record_count=0,
            post_resolution_audit_warning_count=0,
            warnings=("no_records",),
            advisory_label=_ADVISORY_LABEL,
        )

    valid_count = sum(1 for _, v in pairs if v.is_valid)
    invalid_count = record_count - valid_count
    validation_warning_count = sum(len(v.warnings) for _, v in pairs)

    stale_count = 0
    manual_review_count = 0
    source_metadata_count = 0
    resolution_source_missing_count = 0
    ambiguity_review_count = 0
    excluded_count = 0
    post_resolution_audit_count = 0
    bucket_dist: dict[str, int] = defaultdict(int)
    label_dist: dict[str, int] = defaultdict(int)

    for record, _validation in pairs:
        if _is_record_stale(record):
            stale_count += 1

        rqs = record.get("research_queue_state")
        if isinstance(rqs, dict):
            if (
                rqs.get("manual_source_review_required") is True
                or rqs.get("resolution_ambiguity_manual_review_required") is True
            ):
                manual_review_count += 1

            if rqs.get("source_metadata_available") is True:
                source_metadata_count += 1

            if rqs.get("resolution_ambiguity_manual_review_required") is True:
                ambiguity_review_count += 1

            bucket = rqs.get("research_queue_bucket")
            if isinstance(bucket, str) and bucket:
                bucket_dist[bucket] += 1

        ro = record.get("resolved_outcome")
        if isinstance(ro, dict):
            ref = ro.get("resolution_source_url_or_reference")
            if not isinstance(ref, str) or not ref.strip():
                resolution_source_missing_count += 1

            if (
                ro.get("resolution_dispute_or_ambiguity_flag") is True
                or ro.get("outcome_token_mapping_verified") is False
            ):
                post_resolution_audit_count += 1
        else:
            resolution_source_missing_count += 1

        hr = record.get("human_review")
        if isinstance(hr, dict):
            label = hr.get("human_review_usefulness_label")
            if isinstance(label, str) and label:
                label_dist[label] += 1

        cal_val = record.get("calibration_validity")
        if isinstance(cal_val, dict) and cal_val.get("excluded_from_calibration") is True:
            excluded_count += 1

    metric_warnings: list[str] = []
    if valid_count == 0:
        metric_warnings.append("all_records_invalid")
    if _safe_rate(invalid_count, record_count) > _HIGH_RATE_THRESHOLD:
        metric_warnings.append("missing_required_field_rate_high")
    if _safe_rate(resolution_source_missing_count, record_count) > _HIGH_RATE_THRESHOLD:
        metric_warnings.append("resolution_source_missing_rate_high")
    if _safe_rate(manual_review_count, record_count) > _HIGH_RATE_THRESHOLD:
        metric_warnings.append("manual_review_required_rate_high")

    total_warning_count = validation_warning_count + len(metric_warnings)

    return CalibrationMetricComputationResult(
        record_count=record_count,
        valid_record_count=valid_count,
        invalid_record_count=invalid_count,
        warning_count=total_warning_count,
        coverage_rate=_safe_rate(valid_count, record_count),
        missing_required_field_rate=_safe_rate(invalid_count, record_count),
        staleness_rate=_safe_rate(stale_count, record_count),
        manual_review_required_rate=_safe_rate(manual_review_count, record_count),
        source_metadata_available_rate=_safe_rate(source_metadata_count, record_count),
        resolution_source_missing_rate=_safe_rate(resolution_source_missing_count, record_count),
        ambiguity_review_required_rate=_safe_rate(ambiguity_review_count, record_count),
        bucket_distribution=dict(sorted(bucket_dist.items())),
        human_review_usefulness_label_distribution=dict(sorted(label_dist.items())),
        excluded_record_count=excluded_count,
        post_resolution_audit_warning_count=post_resolution_audit_count,
        warnings=tuple(metric_warnings),
        advisory_label=_ADVISORY_LABEL,
    )


def compute_calibration_metrics(
    records: Iterable[Mapping[str, object]],
) -> CalibrationMetricComputationResult:
    """Compute research-quality metrics from an iterable of calibration record mappings.

    Validates each record using the WP67 schema validator to determine valid/invalid
    counts. Does not read files, write files, or access the network.
    """
    pairs = [
        (record, validate_calibration_record(record))
        for record in records
    ]
    return _compute_from_pairs(pairs)


def compute_calibration_metrics_from_load_result(
    load_result: ResolvedOutcomeFixtureLoadResult,
) -> CalibrationMetricComputationResult:
    """Compute research-quality metrics from a WP68 ResolvedOutcomeFixtureLoadResult.

    Uses existing per-record validation results. Does not re-validate records,
    does not read files, write files, or access the network.
    """
    pairs = [
        (loaded.record, loaded.validation)
        for loaded in load_result.records
    ]
    return _compute_from_pairs(pairs)
