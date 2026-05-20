"""Offline quality checks for local Polymarket snapshot records.

This module reads only objects already loaded from local snapshot files.
It has no network, credential, scheduler, database, strategy, or execution
authority.
"""

from __future__ import annotations

import dataclasses
from collections import Counter, defaultdict
from datetime import UTC, datetime
from typing import Dict, Iterable, List, Optional

from .market_catalog import MarketCatalog
from .snapshot_reader import SnapshotFileSummary, SnapshotLoadResult, SnapshotReadError


INFO = "INFO"
WARNING = "WARNING"
ERROR = "ERROR"
SEVERITIES = (INFO, WARNING, ERROR)
PUBLIC_GET_PROVENANCE_FRAGMENT = "public-get-only"
GUARD_ENFORCED_FRAGMENT = "guard enforced: yes"
LOCAL_WP16_POLICY_FRAGMENT = "local wp16 policy"
WP8_D002_OPEN_FRAGMENT = "wp8-d002 remains open"
UNCONFIRMED_LIMITS_FRAGMENT = "not confirmed venue limits"


@dataclasses.dataclass
class QualityIssue:
    """One quality issue found in local snapshot data."""

    severity: str
    code: str
    message: str
    record_type: str
    snapshot_id: Optional[str] = None
    market_id: Optional[str] = None
    field: Optional[str] = None
    count: int = 1
    remediation_hint: Optional[str] = None

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)


@dataclasses.dataclass
class QualityGateResult:
    """Structured result for the offline quality gate."""

    passed: bool
    fail_on_warning: bool
    error_count: int
    warning_count: int
    info_count: int
    status: str

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)


@dataclasses.dataclass
class SnapshotQualitySummary:
    """Counts and file metadata for loaded local snapshot files."""

    input_dir: str
    markets_file_present: bool
    order_books_file_present: bool
    manifest_count: int
    market_record_count: int
    order_book_record_count: int
    manifest_record_count: int
    market_lines_read: int
    order_book_lines_read: int
    manifest_files_read: int
    malformed_market_lines: int
    malformed_order_book_lines: int
    malformed_manifest_files: int
    manifest_network_used_true_count: int
    manifest_network_used_false_count: int
    manifest_output_files_empty_count: int
    guard_enforced_manifest_count: int
    unguarded_network_manifest_count: int
    guard_provenance_unknown_manifest_count: int
    local_budget_policy_manifest_count: int

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)


@dataclasses.dataclass
class CatalogQualitySummary:
    """Quality metrics for the in-memory local catalog."""

    unique_market_count: int
    total_record_count: int
    duplicate_market_count: int
    token_count: int
    category_distribution: Dict[str, int]
    status_distribution: Dict[str, int]
    snapshot_id_count: int
    snapshot_ids: List[str]
    latest_snapshot_timestamp: Optional[str]
    missing_category_count: int
    missing_resolution_date_count: int
    order_book_token_count: int
    order_book_tokens_matching_catalog_count: int
    order_book_tokens_without_market_count: int

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)


@dataclasses.dataclass
class SnapshotQualityReport:
    """Complete local quality report for snapshot files and catalog metrics."""

    generated_at_utc: str
    input_dir: str
    snapshot_summary: SnapshotQualitySummary
    catalog_summary: CatalogQualitySummary
    gate_result: QualityGateResult
    issues: List[QualityIssue]

    def issue_counts_by_severity(self) -> Dict[str, int]:
        counts = {severity: 0 for severity in SEVERITIES}
        for issue in self.issues:
            counts[issue.severity] = counts.get(issue.severity, 0) + 1
        return counts

    def to_dict(self, max_issues: Optional[int] = None) -> dict:
        issues = self.issues if max_issues is None else self.issues[:max_issues]
        return {
            "generated_at_utc": self.generated_at_utc,
            "input_dir": self.input_dir,
            "snapshot_summary": self.snapshot_summary.to_dict(),
            "catalog_summary": self.catalog_summary.to_dict(),
            "gate_result": self.gate_result.to_dict(),
            "issue_counts_by_severity": self.issue_counts_by_severity(),
            "issues": [issue.to_dict() for issue in issues],
        }


def build_snapshot_quality_report(
    *,
    file_summary: SnapshotFileSummary,
    market_result: SnapshotLoadResult,
    order_book_result: SnapshotLoadResult,
    manifest_result: SnapshotLoadResult,
    fail_on_warning: bool = False,
    generated_at_utc: Optional[str] = None,
) -> SnapshotQualityReport:
    """Build a structured quality report from already-loaded local snapshots."""

    generated_at_utc = generated_at_utc or _utc_now_iso()
    issues: List[QualityIssue] = []

    issues.extend(_read_errors_to_issues("market", market_result.errors))
    issues.extend(_read_errors_to_issues("order_book", order_book_result.errors))
    issues.extend(_read_errors_to_issues("manifest", manifest_result.errors))

    market_records = list(market_result.records)
    order_book_records = list(order_book_result.records)
    manifests = list(manifest_result.records)

    issues.extend(_validate_market_records(market_records))
    issues.extend(_validate_order_book_records(order_book_records))
    issues.extend(_validate_manifests(manifests))
    issues.extend(_validate_cross_record_quality(market_records, order_book_records))

    catalog_build = MarketCatalog.from_market_records(market_records)
    catalog_summary = _build_catalog_summary(
        catalog=catalog_build.catalog,
        total_record_count=catalog_build.total_records_processed,
        duplicate_market_count=catalog_build.duplicate_market_count,
        order_book_records=order_book_records,
    )
    snapshot_summary = _build_snapshot_summary(
        file_summary=file_summary,
        market_result=market_result,
        order_book_result=order_book_result,
        manifest_result=manifest_result,
    )
    gate = evaluate_quality_gate(issues, fail_on_warning=fail_on_warning)

    return SnapshotQualityReport(
        generated_at_utc=generated_at_utc,
        input_dir=file_summary.input_dir,
        snapshot_summary=snapshot_summary,
        catalog_summary=catalog_summary,
        gate_result=gate,
        issues=sorted(issues, key=_issue_sort_key),
    )


def evaluate_quality_gate(
    issues: Iterable[QualityIssue],
    *,
    fail_on_warning: bool = False,
) -> QualityGateResult:
    """Evaluate quality issues without exiting the process."""

    counts = Counter(issue.severity for issue in issues)
    error_count = counts.get(ERROR, 0)
    warning_count = counts.get(WARNING, 0)
    info_count = counts.get(INFO, 0)
    passed = error_count == 0 and (not fail_on_warning or warning_count == 0)
    return QualityGateResult(
        passed=passed,
        fail_on_warning=fail_on_warning,
        error_count=error_count,
        warning_count=warning_count,
        info_count=info_count,
        status="PASS" if passed else "FAIL",
    )


def _build_snapshot_summary(
    *,
    file_summary: SnapshotFileSummary,
    market_result: SnapshotLoadResult,
    order_book_result: SnapshotLoadResult,
    manifest_result: SnapshotLoadResult,
) -> SnapshotQualitySummary:
    manifests = list(manifest_result.records)
    guard_enforced_count = sum(1 for m in manifests if _manifest_is_guard_enforced(m))
    unguarded_network_count = sum(
        1
        for m in manifests
        if getattr(m, "network_used", None) is True and not _manifest_is_guard_enforced(m)
    )
    guard_unknown_count = sum(1 for m in manifests if not _manifest_is_guard_enforced(m))
    local_budget_count = sum(1 for m in manifests if _manifest_has_local_budget_policy(m))
    return SnapshotQualitySummary(
        input_dir=file_summary.input_dir,
        markets_file_present=file_summary.markets_file_present,
        order_books_file_present=file_summary.order_books_file_present,
        manifest_count=file_summary.manifest_count,
        market_record_count=len(market_result.records),
        order_book_record_count=len(order_book_result.records),
        manifest_record_count=len(manifests),
        market_lines_read=market_result.lines_read,
        order_book_lines_read=order_book_result.lines_read,
        manifest_files_read=manifest_result.lines_read,
        malformed_market_lines=len(market_result.errors),
        malformed_order_book_lines=len(order_book_result.errors),
        malformed_manifest_files=len(manifest_result.errors),
        manifest_network_used_true_count=sum(1 for m in manifests if m.network_used is True),
        manifest_network_used_false_count=sum(1 for m in manifests if m.network_used is False),
        manifest_output_files_empty_count=sum(1 for m in manifests if not m.output_files),
        guard_enforced_manifest_count=guard_enforced_count,
        unguarded_network_manifest_count=unguarded_network_count,
        guard_provenance_unknown_manifest_count=guard_unknown_count,
        local_budget_policy_manifest_count=local_budget_count,
    )


def _build_catalog_summary(
    *,
    catalog: MarketCatalog,
    total_record_count: int,
    duplicate_market_count: int,
    order_book_records: list,
) -> CatalogQualitySummary:
    summary = catalog.summary()
    latest_markets = catalog.get_latest_markets()
    latest_timestamps = [
        market.captured_at_utc for market in latest_markets.values() if market.captured_at_utc
    ]
    order_book_tokens = {record.token_id for record in order_book_records if record.token_id}
    matching_tokens = {
        token_id for token_id in order_book_tokens if catalog.find_by_token_id(token_id)
    }
    return CatalogQualitySummary(
        unique_market_count=summary["unique_market_count"],
        total_record_count=total_record_count,
        duplicate_market_count=duplicate_market_count,
        token_count=summary["total_token_count"],
        category_distribution=summary["category_distribution"],
        status_distribution=summary["status_distribution"],
        snapshot_id_count=summary["snapshot_id_count"],
        snapshot_ids=summary["snapshot_ids"],
        latest_snapshot_timestamp=max(latest_timestamps) if latest_timestamps else None,
        missing_category_count=sum(1 for m in latest_markets.values() if not m.category),
        missing_resolution_date_count=sum(
            1 for m in latest_markets.values() if not m.resolution_date
        ),
        order_book_token_count=len(order_book_tokens),
        order_book_tokens_matching_catalog_count=len(matching_tokens),
        order_book_tokens_without_market_count=len(order_book_tokens - matching_tokens),
    )


def _read_errors_to_issues(record_type: str, errors: list) -> List[QualityIssue]:
    issues = []
    for error in errors:
        if not isinstance(error, SnapshotReadError):
            continue
        location = error.file_path
        if error.line_number is not None:
            location = f"{location}:{error.line_number}"
        issues.append(
            QualityIssue(
                severity=ERROR,
                code="MALFORMED_LOCAL_RECORD",
                message=f"Malformed {record_type} snapshot data at {location}.",
                record_type=record_type,
                remediation_hint="Inspect or recapture the affected local snapshot file.",
            )
        )
    return issues


def _validate_market_records(records: list) -> List[QualityIssue]:
    issues: List[QualityIssue] = []
    for record in records:
        context = {
            "record_type": "market",
            "snapshot_id": getattr(record, "snapshot_id", None),
            "market_id": getattr(record, "market_id", None),
        }
        issues.extend(_require_non_empty(record, "snapshot_id", **context))
        issues.extend(_require_iso_like(record, "captured_at_utc", **context))
        issues.extend(_require_non_empty(record, "market_id", **context))
        issues.extend(_require_non_empty(record, "condition_id", **context))
        issues.extend(_require_non_empty(record, "question", **context))
        issues.extend(_require_list(record, "token_ids", **context))
        issues.extend(_require_list(record, "outcome_labels", **context))
        issues.extend(_require_list(record, "raw_field_names", **context))
        issues.extend(_require_public_get_provenance(record, **context))

        token_ids = getattr(record, "token_ids", None)
        outcome_labels = getattr(record, "outcome_labels", None)
        if isinstance(token_ids, list) and not token_ids:
            issues.append(
                QualityIssue(
                    severity=ERROR,
                    code="EMPTY_TOKEN_IDS",
                    message="Market record has no token_ids.",
                    field="token_ids",
                    remediation_hint="Inspect the source snapshot record.",
                    **context,
                )
            )
        if isinstance(token_ids, list) and isinstance(outcome_labels, list):
            if len(token_ids) != len(outcome_labels):
                issues.append(
                    QualityIssue(
                        severity=WARNING,
                        code="TOKEN_OUTCOME_LENGTH_MISMATCH",
                        message="Market token_ids and outcome_labels lengths differ.",
                        field="token_ids",
                        count=abs(len(token_ids) - len(outcome_labels)),
                        remediation_hint="Verify whether the source market payload changed shape.",
                        **context,
                    )
                )
    return issues


def _validate_order_book_records(records: list) -> List[QualityIssue]:
    issues: List[QualityIssue] = []
    for record in records:
        context = {
            "record_type": "order_book",
            "snapshot_id": getattr(record, "snapshot_id", None),
            "market_id": None,
        }
        issues.extend(_require_non_empty(record, "snapshot_id", **context))
        issues.extend(_require_iso_like(record, "captured_at_utc", **context))
        issues.extend(_require_non_empty(record, "token_id", **context))
        issues.extend(_require_list(record, "raw_field_names", **context))
        issues.extend(_require_public_get_provenance(record, **context))
        issues.extend(_require_list(record, "bids", **context))
        issues.extend(_require_list(record, "asks", **context))
    return issues


def _validate_manifests(manifests: list) -> List[QualityIssue]:
    issues: List[QualityIssue] = []
    for manifest in manifests:
        context = {
            "record_type": "manifest",
            "snapshot_id": getattr(manifest, "snapshot_id", None),
            "market_id": None,
        }
        issues.extend(_require_non_empty(manifest, "snapshot_id", **context))
        issues.extend(_require_iso_like(manifest, "created_at_utc", **context))
        output_files = getattr(manifest, "output_files", None)
        if not isinstance(output_files, list) or not output_files:
            issues.append(
                QualityIssue(
                    severity=ERROR,
                    code="MANIFEST_OUTPUT_FILES_EMPTY",
                    message="Snapshot manifest output_files is missing or empty.",
                    field="output_files",
                    remediation_hint="Use the WP10 follow-up writer behavior for future captures.",
                    **context,
                )
            )
        if getattr(manifest, "network_used", None) is True and not _manifest_is_guard_enforced(manifest):
            issues.append(
                QualityIssue(
                    severity=WARNING,
                    code="NETWORK_USED_WITHOUT_GUARD_PROVENANCE",
                    message=(
                        "Network-used manifest does not show guard enforcement provenance; "
                        "this may be an older pre-WP18 snapshot or an unguarded capture and "
                        "should not be used for guard-dependent research without review."
                    ),
                    field="notes",
                    remediation_hint=(
                        "Review the local manifest provenance before using it for "
                        "guard-dependent research."
                    ),
                    **context,
                )
            )
        if _manifest_is_guard_enforced(manifest) and not _manifest_has_local_budget_policy(manifest):
            issues.append(
                QualityIssue(
                    severity=WARNING,
                    code="GUARD_PROVENANCE_INCOMPLETE",
                    message=(
                        "Guard provenance is incomplete; local-budget and rate-limit "
                        "uncertainty should remain explicit."
                    ),
                    field="notes",
                    remediation_hint=(
                        "Prefer WP18-style notes that mention local WP16 policy, "
                        "WP8-D002, or unconfirmed venue limits."
                    ),
                    **context,
                )
            )
    return issues


def _validate_cross_record_quality(
    market_records: list,
    order_book_records: list,
) -> List[QualityIssue]:
    issues: List[QualityIssue] = []
    by_snapshot_market: Dict[tuple, int] = defaultdict(int)
    token_to_markets: Dict[str, set] = defaultdict(set)
    catalog_tokens = set()

    for record in market_records:
        snapshot_id = getattr(record, "snapshot_id", "")
        market_id = getattr(record, "market_id", "")
        if snapshot_id and market_id:
            by_snapshot_market[(snapshot_id, market_id)] += 1
        token_ids = getattr(record, "token_ids", [])
        if isinstance(token_ids, list):
            for token_id in token_ids:
                if token_id:
                    token_to_markets[token_id].add(market_id)
                    catalog_tokens.add(token_id)

    for (snapshot_id, market_id), count in sorted(by_snapshot_market.items()):
        if count > 1:
            issues.append(
                QualityIssue(
                    severity=ERROR,
                    code="DUPLICATE_MARKET_ID_IN_SNAPSHOT",
                    message="Multiple market records share the same market_id in one snapshot.",
                    record_type="market",
                    snapshot_id=snapshot_id,
                    market_id=market_id,
                    field="market_id",
                    count=count,
                    remediation_hint="Deduplicate local records before using this snapshot for research.",
                )
            )

    for token_id, market_ids in sorted(token_to_markets.items()):
        clean_market_ids = {mid for mid in market_ids if mid}
        if len(clean_market_ids) > 1:
            issues.append(
                QualityIssue(
                    severity=ERROR,
                    code="TOKEN_ID_MULTIPLE_MARKETS",
                    message="One token_id maps to multiple market_ids.",
                    record_type="market",
                    field="token_ids",
                    count=len(clean_market_ids),
                    remediation_hint="Inspect local snapshots for stale or conflicting market records.",
                )
            )

    order_book_tokens = {
        getattr(record, "token_id", "") for record in order_book_records if getattr(record, "token_id", "")
    }
    for token_id in sorted(order_book_tokens - catalog_tokens):
        issues.append(
            QualityIssue(
                severity=WARNING,
                code="ORDER_BOOK_TOKEN_WITHOUT_MARKET",
                message="Order-book token_id has no matching market token in the loaded catalog.",
                record_type="order_book",
                field="token_id",
                remediation_hint="Load the matching market snapshot or ignore this order-book record.",
            )
        )

    return issues


def _require_non_empty(obj: object, field: str, **context: object) -> List[QualityIssue]:
    value = getattr(obj, field, None)
    if isinstance(value, str):
        ok = bool(value.strip())
    else:
        ok = value is not None
    if ok:
        return []
    return [
        QualityIssue(
            severity=ERROR,
            code="REQUIRED_FIELD_EMPTY",
            message=f"Required field {field} is missing or empty.",
            field=field,
            remediation_hint="Inspect the local snapshot record schema.",
            **context,
        )
    ]


def _require_list(obj: object, field: str, **context: object) -> List[QualityIssue]:
    value = getattr(obj, field, None)
    if isinstance(value, list):
        return []
    return [
        QualityIssue(
            severity=ERROR,
            code="REQUIRED_FIELD_NOT_LIST",
            message=f"Required field {field} is not a list.",
            field=field,
            remediation_hint="Inspect the local snapshot record schema.",
            **context,
        )
    ]


def _require_iso_like(obj: object, field: str, **context: object) -> List[QualityIssue]:
    value = getattr(obj, field, None)
    if isinstance(value, str) and _is_iso_like(value):
        return []
    return [
        QualityIssue(
            severity=ERROR,
            code="TIMESTAMP_NOT_ISO_LIKE",
            message=f"Timestamp field {field} is missing or not ISO-like.",
            field=field,
            remediation_hint="Use UTC ISO-format timestamps for snapshot records.",
            **context,
        )
    ]


def _require_public_get_provenance(obj: object, **context: object) -> List[QualityIssue]:
    provenance = getattr(obj, "read_only_provenance", "")
    if isinstance(provenance, str) and PUBLIC_GET_PROVENANCE_FRAGMENT in provenance:
        return []
    return [
        QualityIssue(
            severity=ERROR,
            code="READ_ONLY_PROVENANCE_MISSING",
            message="read_only_provenance is missing or lacks public-get-only.",
            field="read_only_provenance",
            remediation_hint="Use WP10 snapshot records with read-only provenance.",
            **context,
        )
    ]


def _manifest_is_guard_enforced(manifest: object) -> bool:
    notes = _manifest_notes(manifest)
    return any(
        fragment in notes
        for fragment in (
            GUARD_ENFORCED_FRAGMENT,
            LOCAL_WP16_POLICY_FRAGMENT,
            WP8_D002_OPEN_FRAGMENT,
            UNCONFIRMED_LIMITS_FRAGMENT,
        )
    )


def _manifest_has_local_budget_policy(manifest: object) -> bool:
    notes = _manifest_notes(manifest)
    return any(
        fragment in notes
        for fragment in (
            LOCAL_WP16_POLICY_FRAGMENT,
            WP8_D002_OPEN_FRAGMENT,
            UNCONFIRMED_LIMITS_FRAGMENT,
        )
    )


def _manifest_notes(manifest: object) -> str:
    notes = getattr(manifest, "notes", "")
    return notes.casefold() if isinstance(notes, str) else ""


def _is_iso_like(value: str) -> bool:
    if "T" not in value:
        return False
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return True


def _utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _issue_sort_key(issue: QualityIssue) -> tuple:
    severity_rank = {ERROR: 0, WARNING: 1, INFO: 2}
    return (
        severity_rank.get(issue.severity, 9),
        issue.code,
        issue.snapshot_id or "",
        issue.market_id or "",
        issue.field or "",
    )
