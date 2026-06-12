"""Local/offline/read-only resolved outcome fixture loader.

Loads calibration record JSON fixtures from an explicit local path (single JSON
file, JSON list file, or direct-child *.json directory) and validates each record
with the WP67 calibration record schema validator.

Does not fetch resolved outcomes from any network source.
Does not compute calibration metrics, trading performance, or signal quality.
Does not write files.
Does not scan directories recursively.
Stdlib-only. No network access. No credentials.

Added in WP68.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


from src.data_layer.calibration_record_validation import (
    CalibrationRecordValidationResult,
    validate_calibration_record,
)


_ADVISORY_LABEL = (
    "ADVISORY_ONLY_RESEARCH_USEFULNESS_AUDIT — This loader reads local calibration "
    "record fixtures for structural validation only. It does not evaluate trading "
    "performance, profitability, signal quality, or resolved outcome ingestion."
)

_URL_PREFIXES: tuple[str, ...] = ("http://", "https://", "ftp://", "ftps://")


@dataclass(frozen=True)
class LoadedCalibrationRecord:
    source_path: str
    record_index: int | None
    record: Mapping[str, object]
    validation: CalibrationRecordValidationResult


@dataclass(frozen=True)
class ResolvedOutcomeFixtureLoadResult:
    source_path: str
    loaded_count: int
    valid_count: int
    invalid_count: int
    warning_count: int
    records: tuple[LoadedCalibrationRecord, ...]
    errors: tuple[str, ...]
    advisory_label: str


def _looks_like_url(path_str: str) -> bool:
    low = path_str.strip().lower()
    return any(low.startswith(prefix) for prefix in _URL_PREFIXES)


def _load_single_file(
    file_path: Path,
) -> tuple[list[LoadedCalibrationRecord], list[str]]:
    """Load records from a single JSON file. Returns (records, errors)."""
    records: list[LoadedCalibrationRecord] = []
    errors: list[str] = []

    try:
        raw = file_path.read_text(encoding="utf-8")
    except OSError as exc:
        errors.append(f"Cannot read file '{file_path}': {exc}")
        return records, errors

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        errors.append(f"Invalid JSON in '{file_path}': {exc}")
        return records, errors

    if isinstance(data, dict):
        validation = validate_calibration_record(data)
        records.append(
            LoadedCalibrationRecord(
                source_path=str(file_path),
                record_index=None,
                record=data,
                validation=validation,
            )
        )
    elif isinstance(data, list):
        for i, item in enumerate(data):
            if not isinstance(item, dict):
                errors.append(
                    f"JSON list entry at index {i} in '{file_path}' is not an object "
                    f"(got {type(item).__name__}); skipping."
                )
                continue
            validation = validate_calibration_record(item)
            records.append(
                LoadedCalibrationRecord(
                    source_path=str(file_path),
                    record_index=i,
                    record=item,
                    validation=validation,
                )
            )
    else:
        errors.append(
            f"JSON root in '{file_path}' is neither an object nor a list "
            f"(got {type(data).__name__})."
        )

    return records, errors


def load_resolved_outcome_fixtures(
    path: str | Path,
) -> ResolvedOutcomeFixtureLoadResult:
    """Load calibration record fixtures from an explicit local path.

    Accepts:
    - A single JSON file containing one calibration record object.
    - A single JSON file containing a JSON list of calibration record objects.
    - A directory: loads direct-child *.json files sorted by filename.
      Non-json files in the directory are ignored (not loaded, not read).
      Subdirectories are not descended into.

    Returns a ResolvedOutcomeFixtureLoadResult with per-record validation results.
    Does not raise on invalid records. May return loader-level errors for
    missing paths, unsupported extensions, invalid JSON, or URL-like inputs.
    """
    path_str = str(path).strip()

    if _looks_like_url(path_str):
        return ResolvedOutcomeFixtureLoadResult(
            source_path=path_str,
            loaded_count=0,
            valid_count=0,
            invalid_count=0,
            warning_count=0,
            records=(),
            errors=(f"URL-like path rejected: '{path_str}'. Only explicit local paths are accepted.",),
            advisory_label=_ADVISORY_LABEL,
        )

    resolved = Path(path_str)

    if not resolved.exists():
        return ResolvedOutcomeFixtureLoadResult(
            source_path=path_str,
            loaded_count=0,
            valid_count=0,
            invalid_count=0,
            warning_count=0,
            records=(),
            errors=(f"Path does not exist: '{path_str}'.",),
            advisory_label=_ADVISORY_LABEL,
        )

    all_records: list[LoadedCalibrationRecord] = []
    all_errors: list[str] = []

    if resolved.is_dir():
        json_files = sorted(
            f for f in resolved.iterdir() if f.is_file() and f.suffix.lower() == ".json"
        )
        if not json_files:
            all_errors.append(
                f"Directory '{path_str}' contains no direct-child *.json files."
            )
        for json_file in json_files:
            recs, errs = _load_single_file(json_file)
            all_records.extend(recs)
            all_errors.extend(errs)
    elif resolved.is_file():
        if resolved.suffix.lower() != ".json":
            return ResolvedOutcomeFixtureLoadResult(
                source_path=path_str,
                loaded_count=0,
                valid_count=0,
                invalid_count=0,
                warning_count=0,
                records=(),
                errors=(
                    f"Unsupported file extension '{resolved.suffix}' for '{path_str}'. "
                    "Only .json files are accepted.",
                ),
                advisory_label=_ADVISORY_LABEL,
            )
        recs, errs = _load_single_file(resolved)
        all_records.extend(recs)
        all_errors.extend(errs)
    else:
        return ResolvedOutcomeFixtureLoadResult(
            source_path=path_str,
            loaded_count=0,
            valid_count=0,
            invalid_count=0,
            warning_count=0,
            records=(),
            errors=(f"Path is neither a file nor a directory: '{path_str}'.",),
            advisory_label=_ADVISORY_LABEL,
        )

    valid_count = sum(1 for r in all_records if r.validation.is_valid)
    invalid_count = sum(1 for r in all_records if not r.validation.is_valid)
    warning_count = sum(len(r.validation.warnings) for r in all_records)

    return ResolvedOutcomeFixtureLoadResult(
        source_path=path_str,
        loaded_count=len(all_records),
        valid_count=valid_count,
        invalid_count=invalid_count,
        warning_count=warning_count,
        records=tuple(all_records),
        errors=tuple(all_errors),
        advisory_label=_ADVISORY_LABEL,
    )
