"""Local/offline/read-only export layer for WP89 CandidateReviewReport objects.

Accepts a CandidateReviewReport from WP89 and writes deterministic Markdown
and/or JSON files under an operator-specified local output directory.
No network calls, no credential access, no scheduling, no account activity,
no report content modification.

Added in WP90.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from src.data_layer.wallet_signal_candidate_review_report import (
    CandidateReviewReport,
    render_wallet_signal_candidate_review_report,
)

FORMAT_MARKDOWN = "MARKDOWN"
FORMAT_JSON = "JSON"

WRITE_STATUS_WRITTEN = "WRITTEN"
WRITE_STATUS_SKIPPED_UNREQUESTED = "SKIPPED_UNREQUESTED"

EXPORT_STATUS_EXPORT_WRITTEN = "EXPORT_WRITTEN"
EXPORT_STATUS_EXPORT_PARTIAL = "EXPORT_PARTIAL"
EXPORT_STATUS_EXPORT_NOT_WRITTEN = "EXPORT_NOT_WRITTEN"

EXPORT_ADVISORY_NOTICE = "Local file export only. No account activity is authorized."

_FILENAME_MARKDOWN = "candidate_review_report.md"
_FILENAME_JSON = "candidate_review_report.json"

_ALLOWED_FORMAT_FILENAMES: dict[str, str] = {
    FORMAT_MARKDOWN: _FILENAME_MARKDOWN,
    FORMAT_JSON: _FILENAME_JSON,
}


@dataclass(frozen=True)
class CandidateReviewReportExportFile:
    format: str
    relative_path: str
    bytes_written: int
    content_sha256: str
    write_status: str


@dataclass(frozen=True)
class CandidateReviewReportExportResult:
    output_directory: str
    files: tuple[CandidateReviewReportExportFile, ...]
    export_status: str
    warnings: tuple[str, ...]
    advisory_notice: str


def render_candidate_review_report_json(report: CandidateReviewReport) -> str:
    """Serialize a CandidateReviewReport to deterministic JSON with sorted keys and trailing newline."""
    return json.dumps(asdict(report), sort_keys=True, ensure_ascii=True, indent=2) + "\n"


def candidate_review_report_export_result_to_dict(
    result: CandidateReviewReportExportResult,
) -> dict[str, Any]:
    """Return a full dataclass serialization of the export result for output-surface scanning."""
    return asdict(result)


def _sha256_hex(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def export_wallet_signal_candidate_review_report(
    report: CandidateReviewReport,
    output_dir: str | Path,
    formats: tuple[str, ...] = (FORMAT_MARKDOWN, FORMAT_JSON),
) -> CandidateReviewReportExportResult:
    """Export a WP89 candidate review report to deterministic local files.

    Writes Markdown and/or JSON under output_dir. All writes stay under output_dir.
    No network, no credentials, no account activity, no report content changes.
    """
    resolved_dir = Path(output_dir).resolve()
    resolved_dir.mkdir(parents=True, exist_ok=True)

    export_files: list[CandidateReviewReportExportFile] = []
    written_count = 0
    valid_requested = frozenset(formats) & frozenset(_ALLOWED_FORMAT_FILENAMES)

    for fmt, filename in _ALLOWED_FORMAT_FILENAMES.items():
        if fmt in valid_requested:
            if fmt == FORMAT_MARKDOWN:
                content = render_wallet_signal_candidate_review_report(report)
            else:
                content = render_candidate_review_report_json(report)
            encoded = content.encode("utf-8")
            dest = resolved_dir / filename
            dest.write_bytes(encoded)
            export_files.append(CandidateReviewReportExportFile(
                format=fmt,
                relative_path=filename,
                bytes_written=len(encoded),
                content_sha256=_sha256_hex(content),
                write_status=WRITE_STATUS_WRITTEN,
            ))
            written_count += 1
        else:
            export_files.append(CandidateReviewReportExportFile(
                format=fmt,
                relative_path=filename,
                bytes_written=0,
                content_sha256="",
                write_status=WRITE_STATUS_SKIPPED_UNREQUESTED,
            ))

    total_requested = len(valid_requested)
    if written_count == total_requested and written_count > 0:
        export_status = EXPORT_STATUS_EXPORT_WRITTEN
    elif written_count > 0:
        export_status = EXPORT_STATUS_EXPORT_PARTIAL
    else:
        export_status = EXPORT_STATUS_EXPORT_NOT_WRITTEN

    return CandidateReviewReportExportResult(
        output_directory=str(resolved_dir),
        files=tuple(export_files),
        export_status=export_status,
        warnings=(),
        advisory_notice=EXPORT_ADVISORY_NOTICE,
    )
