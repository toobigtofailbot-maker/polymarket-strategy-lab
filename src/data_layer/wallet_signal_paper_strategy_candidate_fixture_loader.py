"""Local/offline/read-only fixture loader for wallet signal paper strategy candidate records.

Loads candidate contract record JSON fixtures from an explicit local path (single
JSON file or direct-child *.json directory) and validates each record with the
WP84 wallet signal paper strategy contract validator.

This module is advisory only.

It does not:
- create paper strategy records, paper strategy implementations, or paper strategies;
- fetch wallet data from any network or API source;
- monitor real wallets;
- copy wallets or place copy instructions;
- compute dollar PnL, expected return, or position size;
- produce buy/sell signals, live signals, or trade-ready output;
- place orders, cancel orders, size positions, or override risk;
- write files;
- access credentials or authentication clients;
- invoke an LLM, AI agent, scheduler, dashboard, or bot loop;
- run paper or live account activity;
- echo unsafe invalid input through errors, warnings, paths, metadata, or summaries.

Stdlib-only. No network access. No credentials. No file writes.

Added in WP87.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from src.data_layer.wallet_signal_paper_strategy_contract_validator import (
    ContractValidationResult,
    validate_wallet_signal_paper_strategy_contract_record,
)

# ---------------------------------------------------------------------------
# Advisory label
# ---------------------------------------------------------------------------

_ADVISORY_LABEL = (
    "ADVISORY_ONLY_WALLET_SIGNAL_PAPER_STRATEGY_CANDIDATE_FIXTURE_LOADER — "
    "This loader reads local fixture files for contract validation only. "
    "It does not create paper strategies, place orders, produce signals, "
    "monitor wallets, or perform any account activity."
)

# ---------------------------------------------------------------------------
# Load status constants
# ---------------------------------------------------------------------------

LOADED_VALID_CONTRACT_RECORD = "LOADED_VALID_CONTRACT_RECORD"
LOADED_INVALID_CONTRACT_RECORD = "LOADED_INVALID_CONTRACT_RECORD"
MALFORMED_FIXTURE_FILE = "MALFORMED_FIXTURE_FILE"
MISSING_FIXTURE_PATH = "MISSING_FIXTURE_PATH"
UNSUPPORTED_FIXTURE_PATH = "UNSUPPORTED_FIXTURE_PATH"

# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CandidateFixtureLoadItem:
    """Result of loading and validating a single candidate fixture record.

    Advisory only. Does not authorize paper strategy implementation,
    order placement, live account action, or any account activity.

    Added in WP87.
    """

    fixture_path: str
    load_status: str
    validation_status: str
    is_valid: bool
    errors: tuple[str, ...]
    warnings: tuple[str, ...]
    normalized_record: Mapping[str, object]


@dataclass(frozen=True)
class CandidateFixtureLoadResult:
    """Aggregate result of loading candidate fixture records from a local path.

    Advisory only. Does not authorize paper strategy implementation,
    order placement, live account action, or any account activity.

    Added in WP87.
    """

    root_path: str
    total_files: int
    loaded_files: int
    valid_records: int
    invalid_records: int
    malformed_files: int
    items: tuple[CandidateFixtureLoadItem, ...]
    errors: tuple[str, ...]
    warnings: tuple[str, ...]
    advisory_label: str


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_URL_PREFIXES: tuple[str, ...] = ("http://", "https://", "ftp://", "ftps://")


def _looks_like_url(path_str: str) -> bool:
    low = path_str.strip().lower()
    return any(low.startswith(p) for p in _URL_PREFIXES)


def _safe_relative_name(file_path: Path, root: Path | None) -> str:
    """Return a safe relative or basename path string for output surfaces."""
    try:
        if root is not None:
            return str(file_path.relative_to(root))
    except ValueError:
        pass
    return file_path.name


def _item_from_validation(
    safe_name: str,
    validation: ContractValidationResult,
) -> CandidateFixtureLoadItem:
    """Build a CandidateFixtureLoadItem from a completed validation result."""
    if validation.is_valid:
        load_status = LOADED_VALID_CONTRACT_RECORD
    else:
        load_status = LOADED_INVALID_CONTRACT_RECORD
    return CandidateFixtureLoadItem(
        fixture_path=safe_name,
        load_status=load_status,
        validation_status=validation.status,
        is_valid=validation.is_valid,
        errors=validation.errors,
        warnings=validation.warnings,
        normalized_record=validation.normalized_record,
    )


def _load_single_fixture_file(
    file_path: Path,
    root: Path | None,
) -> tuple[list[CandidateFixtureLoadItem], bool]:
    """Load one fixture JSON file.

    Returns (items, was_malformed). items is a list of CandidateFixtureLoadItem.
    was_malformed is True if the file could not be parsed as valid JSON containing
    a dict root. In that case, items contains exactly one MALFORMED_FIXTURE_FILE item.
    Errors in the malformed item never echo raw file content.
    """
    safe_name = _safe_relative_name(file_path, root)

    try:
        raw = file_path.read_text(encoding="utf-8")
    except OSError:
        return (
            [CandidateFixtureLoadItem(
                fixture_path=safe_name,
                load_status=MALFORMED_FIXTURE_FILE,
                validation_status="",
                is_valid=False,
                errors=("Fixture file could not be read.",),
                warnings=(),
                normalized_record={},
            )],
            True,
        )

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return (
            [CandidateFixtureLoadItem(
                fixture_path=safe_name,
                load_status=MALFORMED_FIXTURE_FILE,
                validation_status="",
                is_valid=False,
                errors=("Fixture file contains invalid JSON.",),
                warnings=(),
                normalized_record={},
            )],
            True,
        )

    if not isinstance(data, dict):
        return (
            [CandidateFixtureLoadItem(
                fixture_path=safe_name,
                load_status=MALFORMED_FIXTURE_FILE,
                validation_status="",
                is_valid=False,
                errors=("Fixture file JSON root is not a mapping object.",),
                warnings=(),
                normalized_record={},
            )],
            True,
        )

    validation = validate_wallet_signal_paper_strategy_contract_record(data)
    return ([_item_from_validation(safe_name, validation)], False)


# ---------------------------------------------------------------------------
# Public loader
# ---------------------------------------------------------------------------


def load_wallet_signal_paper_strategy_candidate_fixtures(
    path: str | Path,
) -> CandidateFixtureLoadResult:
    """Load wallet signal paper strategy candidate fixtures from an explicit local path.

    Accepts:
    - A single JSON file containing one candidate contract record object.
    - A directory: loads direct-child *.json files sorted by filename.
      Subdirectories are not descended into. Non-json files are ignored.

    Validates each record using the WP84 contract validator.
    Returns a CandidateFixtureLoadResult with per-item validation results.

    Does not raise on invalid or malformed records. Never echoes unsafe input
    through errors, warnings, statuses, or normalized_record fields.
    Stdlib-only. No network access. No credentials. No file writes.

    Added in WP87.
    """
    path_str = str(path).strip()

    if _looks_like_url(path_str):
        return CandidateFixtureLoadResult(
            root_path="",
            total_files=0,
            loaded_files=0,
            valid_records=0,
            invalid_records=0,
            malformed_files=0,
            items=(),
            errors=("URL-like path rejected. Only explicit local paths are accepted.",),
            warnings=(),
            advisory_label=_ADVISORY_LABEL,
        )

    resolved = Path(path_str)

    if not resolved.exists():
        return CandidateFixtureLoadResult(
            root_path="",
            total_files=0,
            loaded_files=0,
            valid_records=0,
            invalid_records=0,
            malformed_files=0,
            items=(),
            errors=("Fixture path does not exist.",),
            warnings=(),
            advisory_label=_ADVISORY_LABEL,
        )

    all_items: list[CandidateFixtureLoadItem] = []
    loader_errors: list[str] = []
    total_files = 0
    malformed_files_count = 0

    if resolved.is_dir():
        json_files = sorted(
            f for f in resolved.iterdir()
            if f.is_file() and f.suffix.lower() == ".json"
        )
        root_for_names: Path | None = resolved
        if not json_files:
            loader_errors.append(
                "Fixture directory contains no direct-child JSON files."
            )
        for jf in json_files:
            total_files += 1
            items, was_malformed = _load_single_fixture_file(jf, root_for_names)
            all_items.extend(items)
            if was_malformed:
                malformed_files_count += 1
    elif resolved.is_file():
        if resolved.suffix.lower() != ".json":
            return CandidateFixtureLoadResult(
                root_path="",
                total_files=0,
                loaded_files=0,
                valid_records=0,
                invalid_records=0,
                malformed_files=0,
                items=(),
                errors=("Unsupported file type. Only JSON files are accepted.",),
                warnings=(),
                advisory_label=_ADVISORY_LABEL,
            )
        total_files = 1
        root_for_names = resolved.parent
        items, was_malformed = _load_single_fixture_file(resolved, root_for_names)
        all_items.extend(items)
        if was_malformed:
            malformed_files_count += 1
    else:
        return CandidateFixtureLoadResult(
            root_path="",
            total_files=0,
            loaded_files=0,
            valid_records=0,
            invalid_records=0,
            malformed_files=0,
            items=(),
            errors=("Fixture path is neither a file nor a directory.",),
            warnings=(),
            advisory_label=_ADVISORY_LABEL,
        )

    valid_records = sum(1 for it in all_items if it.is_valid)
    invalid_records = sum(1 for it in all_items if not it.is_valid and it.load_status == LOADED_INVALID_CONTRACT_RECORD)
    loaded_files = total_files - malformed_files_count

    return CandidateFixtureLoadResult(
        root_path=resolved.name,
        total_files=total_files,
        loaded_files=loaded_files,
        valid_records=valid_records,
        invalid_records=invalid_records,
        malformed_files=malformed_files_count,
        items=tuple(all_items),
        errors=tuple(loader_errors),
        warnings=(),
        advisory_label=_ADVISORY_LABEL,
    )
