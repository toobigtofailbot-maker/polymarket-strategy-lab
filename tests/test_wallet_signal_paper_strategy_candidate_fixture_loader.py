"""Focused tests for WP87 wallet signal paper strategy candidate fixture loader.

Tests cover:
- valid fixture loads and produces one valid item (WP87 §11)
- directory with mixed valid/invalid/malformed fixtures loads deterministically (WP87 §11)
- missing path returns safe result (WP87 §11)
- malformed JSON returns safe result without raw JSON echo (WP87 §11)
- forbidden status fixture is invalid and errors do not echo forbidden status (WP87 §11/13)
- forbidden metadata fixture is invalid and output does not echo unsafe content (WP87 §14)
- invalid fixture normalized_record is empty (WP87 §10/11)
- full loader result recursively contains no forbidden terms (WP87 §12/13)
- loader does not import forbidden modules (WP87 §9/11)
- loader does not write files (WP87 §9/11)
- fixture order is deterministic (WP87 §11)
- status fragment exists and references WP87 (WP87 §18)

Added in WP87.
"""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path

import pytest

from src.data_layer.wallet_signal_paper_strategy_candidate_fixture_loader import (
    LOADED_INVALID_CONTRACT_RECORD,
    LOADED_VALID_CONTRACT_RECORD,
    MALFORMED_FIXTURE_FILE,
    MISSING_FIXTURE_PATH,
    UNSUPPORTED_FIXTURE_PATH,
    CandidateFixtureLoadItem,
    CandidateFixtureLoadResult,
    load_wallet_signal_paper_strategy_candidate_fixtures,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = ROOT / "tests" / "fixtures" / "wallet_signal_paper_strategy_candidates"
VALID_FIXTURE = FIXTURE_DIR / "valid_candidate.json"
INVALID_STATUS_FIXTURE = FIXTURE_DIR / "invalid_forbidden_status.json"
INVALID_METADATA_FIXTURE = FIXTURE_DIR / "invalid_forbidden_metadata.json"
MALFORMED_FIXTURE = FIXTURE_DIR / "malformed_json.json"

# ---------------------------------------------------------------------------
# Forbidden terms for output safety scanning
# ---------------------------------------------------------------------------

_FORBIDDEN_OUTPUT_TERMS: tuple[str, ...] = (
    "buy",
    "sell",
    "trade",
    "trading",
    "execute",
    "execution",
    "order_ready",
    "execution_ready",
    "entry",
    "exit",
    "position_size",
    "position sizing",
    "position-size",
    "expected_return",
    "expected return",
    "expected-return",
    "profit_target",
    "profit target",
    "stop_loss",
    "stop loss",
    "take_profit",
    "take profit",
    "live_signal",
    "live signal",
    "auto_copy",
    "auto copy",
    "copy signal",
    "wallet copy instruction",
    "pnl_target",
    "pnl target",
    "paper_trading_candidate",
    "paper trading candidate",
    "strategy_signal",
    "strategy signal",
    "TRADE_READY",
    "COPY_READY",
    "LIVE_READY",
    "ORDER_READY",
    "EXECUTION_READY",
    "BUY_SIGNAL",
    "SELL_SIGNAL",
    "AUTO_APPROVED",
)

_SAFETY_FLAG_EXCEPTION_KEYS: frozenset[str] = frozenset({
    "not_automated_copy_trading",
    "no_live_execution",
    "no_order_placement",
    "no_position_sizing",
})

_ALLOWED_LOAD_STATUSES: frozenset[str] = frozenset({
    LOADED_VALID_CONTRACT_RECORD,
    LOADED_INVALID_CONTRACT_RECORD,
    MALFORMED_FIXTURE_FILE,
    MISSING_FIXTURE_PATH,
    UNSUPPORTED_FIXTURE_PATH,
    "",
})


def _scan_for_forbidden_terms(obj: object, path: str = "") -> list[str]:
    """Recursively scan a loader result object for forbidden output terms.

    Returns a list of violation descriptions. Safety flag exception keys are exempt.
    """
    violations: list[str] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            current = f"{path}.{k}" if path else k
            if k not in _SAFETY_FLAG_EXCEPTION_KEYS:
                norm_k = k.lower().replace("_", " ").replace("-", " ")
                for term in _FORBIDDEN_OUTPUT_TERMS:
                    if term.lower() in norm_k:
                        violations.append(
                            f"Forbidden term '{term}' found in key at path '{current}'"
                        )
                        break
            violations.extend(_scan_for_forbidden_terms(v, current))
    elif isinstance(obj, (list, tuple)):
        for i, item in enumerate(obj):
            violations.extend(_scan_for_forbidden_terms(item, f"{path}[{i}]"))
    elif isinstance(obj, str):
        norm_v = obj.lower().replace("_", " ").replace("-", " ")
        for term in _FORBIDDEN_OUTPUT_TERMS:
            if term.lower() in norm_v:
                violations.append(
                    f"Forbidden term '{term}' found in string value at '{path}': {repr(obj[:60])}"
                )
                break
    return violations


def _result_to_dict(result: CandidateFixtureLoadResult) -> dict:
    """Convert a loader result to a plain dict for recursive scanning."""
    return {
        "root_path": result.root_path,
        "total_files": result.total_files,
        "loaded_files": result.loaded_files,
        "valid_records": result.valid_records,
        "invalid_records": result.invalid_records,
        "malformed_files": result.malformed_files,
        "items": [_item_to_dict(it) for it in result.items],
        "errors": list(result.errors),
        "warnings": list(result.warnings),
    }


def _item_to_dict(item: CandidateFixtureLoadItem) -> dict:
    return {
        "fixture_path": item.fixture_path,
        "load_status": item.load_status,
        "validation_status": item.validation_status,
        "is_valid": item.is_valid,
        "errors": list(item.errors),
        "warnings": list(item.warnings),
        "normalized_record": dict(item.normalized_record),
    }


# ---------------------------------------------------------------------------
# Basic fixture file checks
# ---------------------------------------------------------------------------


def test_fixture_files_exist() -> None:
    """All four WP87 fixture files must exist."""
    for fpath in (VALID_FIXTURE, INVALID_STATUS_FIXTURE, INVALID_METADATA_FIXTURE, MALFORMED_FIXTURE):
        assert fpath.is_file(), f"Required fixture file missing: {fpath}"


def test_fixture_directory_exists() -> None:
    assert FIXTURE_DIR.is_dir(), f"Fixture directory missing: {FIXTURE_DIR}"


# ---------------------------------------------------------------------------
# Valid fixture test
# ---------------------------------------------------------------------------


def test_valid_fixture_loads() -> None:
    """Valid fixture must load as one valid item."""
    result = load_wallet_signal_paper_strategy_candidate_fixtures(VALID_FIXTURE)
    assert result.valid_records == 1
    assert result.invalid_records == 0
    assert result.malformed_files == 0
    assert result.total_files == 1
    assert len(result.items) == 1
    item = result.items[0]
    assert item.is_valid is True
    assert item.load_status == LOADED_VALID_CONTRACT_RECORD
    assert item.validation_status == "VALID_CONTRACT_RECORD"
    assert item.errors == ()
    assert item.normalized_record != {}


def test_valid_fixture_item_has_safe_fixture_path() -> None:
    """Fixture path in result must not be an absolute machine path."""
    result = load_wallet_signal_paper_strategy_candidate_fixtures(VALID_FIXTURE)
    item = result.items[0]
    path_str = item.fixture_path
    assert path_str, "fixture_path must not be empty"
    assert "\\" not in path_str or not Path(path_str).is_absolute(), (
        f"fixture_path should be a safe relative name, got: {path_str!r}"
    )
    assert "/home/" not in path_str
    assert "C:\\" not in path_str and "C:/" not in path_str or not Path(path_str).is_absolute()


# ---------------------------------------------------------------------------
# Missing path test
# ---------------------------------------------------------------------------


def test_missing_path_returns_safe_result() -> None:
    """A missing path must return a MISSING_FIXTURE_PATH-like result without raising."""
    result = load_wallet_signal_paper_strategy_candidate_fixtures(
        "/nonexistent/path/that/does/not/exist/wp87_test.json"
    )
    assert result.valid_records == 0
    assert result.total_files == 0
    assert len(result.errors) >= 1
    assert result.items == ()


def test_missing_path_result_has_no_forbidden_terms() -> None:
    result = load_wallet_signal_paper_strategy_candidate_fixtures(
        "/nonexistent/wp87_missing_test.json"
    )
    violations = _scan_for_forbidden_terms(_result_to_dict(result))
    assert violations == [], f"Forbidden terms in missing-path result: {violations}"


# ---------------------------------------------------------------------------
# Malformed JSON test
# ---------------------------------------------------------------------------


def test_malformed_json_safe_error() -> None:
    """Malformed JSON fixture must produce a safe MALFORMED_FIXTURE_FILE item."""
    result = load_wallet_signal_paper_strategy_candidate_fixtures(MALFORMED_FIXTURE)
    assert result.total_files == 1
    assert result.malformed_files == 1
    assert result.valid_records == 0
    assert len(result.items) == 1
    item = result.items[0]
    assert item.load_status == MALFORMED_FIXTURE_FILE
    assert item.is_valid is False
    assert item.normalized_record == {}


def test_malformed_json_error_does_not_echo_raw_json() -> None:
    """Error messages for malformed JSON must not include raw JSON content."""
    result = load_wallet_signal_paper_strategy_candidate_fixtures(MALFORMED_FIXTURE)
    item = result.items[0]
    full_error_text = " ".join(item.errors)
    forbidden_json_snippets = [
        "unclosed_object",
        "intentionally_malformed",
        "WP87 reviewer",
    ]
    for snippet in forbidden_json_snippets:
        assert snippet not in full_error_text, (
            f"Error message echoes raw JSON content '{snippet}': {full_error_text!r}"
        )


def test_malformed_json_result_has_no_forbidden_terms() -> None:
    result = load_wallet_signal_paper_strategy_candidate_fixtures(MALFORMED_FIXTURE)
    violations = _scan_for_forbidden_terms(_result_to_dict(result))
    assert violations == [], f"Forbidden terms in malformed result: {violations}"


# ---------------------------------------------------------------------------
# Forbidden status fixture test
# ---------------------------------------------------------------------------


def test_forbidden_status_fixture_is_invalid() -> None:
    """Fixture with TRADE_READY eligibility_status must fail validation."""
    result = load_wallet_signal_paper_strategy_candidate_fixtures(INVALID_STATUS_FIXTURE)
    assert result.valid_records == 0
    assert result.invalid_records == 1
    assert len(result.items) == 1
    item = result.items[0]
    assert item.is_valid is False
    assert item.load_status == LOADED_INVALID_CONTRACT_RECORD


def test_forbidden_status_fixture_no_echo() -> None:
    """Loader result must not echo 'TRADE_READY' or other forbidden status strings."""
    result = load_wallet_signal_paper_strategy_candidate_fixtures(INVALID_STATUS_FIXTURE)
    item = result.items[0]
    forbidden_echo = ["TRADE_READY", "COPY_READY", "BUY_SIGNAL", "SELL_SIGNAL"]
    all_text = " ".join(item.errors) + " ".join(item.warnings)
    for term in forbidden_echo:
        assert term not in all_text, (
            f"Forbidden status term '{term}' echoed in item output: {all_text!r}"
        )


def test_forbidden_status_normalized_record_is_empty() -> None:
    """Invalid item's normalized_record must be empty."""
    result = load_wallet_signal_paper_strategy_candidate_fixtures(INVALID_STATUS_FIXTURE)
    item = result.items[0]
    assert item.normalized_record == {}


def test_forbidden_status_result_has_no_forbidden_terms() -> None:
    """Full result for forbidden-status fixture must not contain forbidden terms."""
    result = load_wallet_signal_paper_strategy_candidate_fixtures(INVALID_STATUS_FIXTURE)
    violations = _scan_for_forbidden_terms(_result_to_dict(result))
    assert violations == [], f"Forbidden terms in forbidden-status result: {violations}"


# ---------------------------------------------------------------------------
# Forbidden metadata fixture test
# ---------------------------------------------------------------------------


def test_metadata_fixture_is_invalid() -> None:
    """Fixture with forbidden raw metadata key must fail validation."""
    result = load_wallet_signal_paper_strategy_candidate_fixtures(INVALID_METADATA_FIXTURE)
    assert result.valid_records == 0
    assert result.invalid_records == 1
    item = result.items[0]
    assert item.is_valid is False
    assert item.load_status == LOADED_INVALID_CONTRACT_RECORD


def test_metadata_fixture_no_echo() -> None:
    """Loader result must not echo unsafe metadata key names or values."""
    result = load_wallet_signal_paper_strategy_candidate_fixtures(INVALID_METADATA_FIXTURE)
    item = result.items[0]
    unsafe_values = ["position_size", "25", "expected_return", "research advisory label only"]
    all_text = " ".join(item.errors) + " ".join(item.warnings)
    for val in unsafe_values:
        assert val not in all_text, (
            f"Unsafe value '{val}' echoed in item output: {all_text!r}"
        )


def test_metadata_fixture_normalized_record_is_empty() -> None:
    """Invalid metadata fixture normalized_record must be empty."""
    result = load_wallet_signal_paper_strategy_candidate_fixtures(INVALID_METADATA_FIXTURE)
    item = result.items[0]
    assert item.normalized_record == {}


def test_metadata_fixture_result_has_no_forbidden_terms() -> None:
    """Full result for forbidden-metadata fixture must not contain forbidden terms."""
    result = load_wallet_signal_paper_strategy_candidate_fixtures(INVALID_METADATA_FIXTURE)
    violations = _scan_for_forbidden_terms(_result_to_dict(result))
    assert violations == [], f"Forbidden terms in metadata result: {violations}"


# ---------------------------------------------------------------------------
# Invalid normalized_record generic test
# ---------------------------------------------------------------------------


def test_invalid_item_normalized_record_empty() -> None:
    """For any invalid fixture, normalized_record must be empty."""
    for fixture in (INVALID_STATUS_FIXTURE, INVALID_METADATA_FIXTURE):
        result = load_wallet_signal_paper_strategy_candidate_fixtures(fixture)
        for item in result.items:
            if not item.is_valid:
                assert item.normalized_record == {}, (
                    f"Invalid item at {item.fixture_path} has non-empty normalized_record"
                )


# ---------------------------------------------------------------------------
# Mixed directory test
# ---------------------------------------------------------------------------


def test_mixed_directory_loads_deterministically() -> None:
    """Directory with mixed fixtures must load all files deterministically."""
    result = load_wallet_signal_paper_strategy_candidate_fixtures(FIXTURE_DIR)
    assert result.total_files == 4
    assert result.valid_records == 1
    # invalid + malformed >= 3
    assert result.invalid_records + result.malformed_files >= 3
    assert len(result.items) >= 1


def test_mixed_directory_item_order_is_sorted() -> None:
    """Items from a directory load must appear in sorted filename order."""
    result = load_wallet_signal_paper_strategy_candidate_fixtures(FIXTURE_DIR)
    names = [it.fixture_path for it in result.items]
    assert names == sorted(names), f"Items not in sorted order: {names}"


def test_mixed_directory_result_has_no_forbidden_terms() -> None:
    """Full directory load result must not contain forbidden terms."""
    result = load_wallet_signal_paper_strategy_candidate_fixtures(FIXTURE_DIR)
    violations = _scan_for_forbidden_terms(_result_to_dict(result))
    assert violations == [], f"Forbidden terms in directory result: {violations}"


def test_mixed_directory_valid_item_has_valid_status() -> None:
    result = load_wallet_signal_paper_strategy_candidate_fixtures(FIXTURE_DIR)
    valid_items = [it for it in result.items if it.is_valid]
    assert len(valid_items) == 1
    assert valid_items[0].load_status == LOADED_VALID_CONTRACT_RECORD
    assert valid_items[0].normalized_record != {}


def test_mixed_directory_invalid_items_have_empty_normalized_records() -> None:
    result = load_wallet_signal_paper_strategy_candidate_fixtures(FIXTURE_DIR)
    for item in result.items:
        if not item.is_valid:
            assert item.normalized_record == {}, (
                f"Invalid item {item.fixture_path} has non-empty normalized_record"
            )


# ---------------------------------------------------------------------------
# Load status allowlist test
# ---------------------------------------------------------------------------


def test_load_status_values_are_from_allowlist() -> None:
    """All item load_status values must be from the allowed set."""
    result = load_wallet_signal_paper_strategy_candidate_fixtures(FIXTURE_DIR)
    for item in result.items:
        assert item.load_status in _ALLOWED_LOAD_STATUSES, (
            f"Unexpected load_status: {item.load_status!r}"
        )


def test_allowed_statuses_do_not_contain_forbidden_terms() -> None:
    """The allowed status constants must not contain forbidden trading terms."""
    all_statuses = [
        LOADED_VALID_CONTRACT_RECORD,
        LOADED_INVALID_CONTRACT_RECORD,
        MALFORMED_FIXTURE_FILE,
        MISSING_FIXTURE_PATH,
        UNSUPPORTED_FIXTURE_PATH,
    ]
    for status in all_statuses:
        norm = status.lower().replace("_", " ").replace("-", " ")
        for term in _FORBIDDEN_OUTPUT_TERMS:
            assert term.lower() not in norm, (
                f"Forbidden term '{term}' found in status constant '{status}'"
            )


# ---------------------------------------------------------------------------
# Unsupported file type test
# ---------------------------------------------------------------------------


def test_unsupported_file_type_safe_result(tmp_path: Path) -> None:
    """Non-json file must produce a safe result without raising."""
    txt_file = tmp_path / "candidate.txt"
    txt_file.write_text("not json", encoding="utf-8")
    result = load_wallet_signal_paper_strategy_candidate_fixtures(txt_file)
    assert result.valid_records == 0
    assert result.total_files == 0
    assert len(result.errors) >= 1


def test_url_like_path_rejected() -> None:
    """URL-like paths must be rejected without raising."""
    result = load_wallet_signal_paper_strategy_candidate_fixtures("https://example.com/fixture.json")
    assert result.valid_records == 0
    assert len(result.errors) >= 1


# ---------------------------------------------------------------------------
# Forbidden imports test
# ---------------------------------------------------------------------------


def test_loader_has_no_forbidden_imports() -> None:
    """Loader module must not import network, client, order, or scheduler modules."""
    loader_path = (
        ROOT / "src" / "data_layer"
        / "wallet_signal_paper_strategy_candidate_fixture_loader.py"
    )
    source = loader_path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imported.append(node.module)
    forbidden_import_patterns = [
        "requests",
        "urllib.request",
        "http.client",
        "socket",
        "asyncio",
        "aiohttp",
        "boto",
        "polymarket",
        "order",
        "scheduler",
        "dashboard",
        "paper_trading",
        "paper_order",
        "paper_portfolio",
        "live",
        "credential",
        "auth",
        "execution_gateway",
        "strategy_modules",
        "monitoring",
        "hermes",
    ]
    violations = []
    for imp in imported:
        for pattern in forbidden_import_patterns:
            if pattern in imp.lower():
                violations.append(f"Forbidden import: {imp!r} (matched pattern {pattern!r})")
    assert violations == [], f"Loader has forbidden imports: {violations}"


# ---------------------------------------------------------------------------
# Loader does not write files test
# ---------------------------------------------------------------------------


def test_loader_does_not_write_files() -> None:
    """Loader module source must not contain file-write operations."""
    loader_path = (
        ROOT / "src" / "data_layer"
        / "wallet_signal_paper_strategy_candidate_fixture_loader.py"
    )
    source = loader_path.read_text(encoding="utf-8")
    write_patterns = [
        r"\.write\(",
        r"\.write_text\(",
        r"\.write_bytes\(",
        r"open\([^)]*['\"][wa]['\"]",
        r"json\.dump\(",
    ]
    for pattern in write_patterns:
        match = re.search(pattern, source)
        assert match is None, (
            f"Loader source contains potential file-write operation matching {pattern!r}"
        )


# ---------------------------------------------------------------------------
# Full result output safety scan (reviewer trap)
# ---------------------------------------------------------------------------


def test_load_result_has_no_forbidden_terms_valid() -> None:
    """Full result for valid fixture must not contain forbidden terms in output surfaces."""
    result = load_wallet_signal_paper_strategy_candidate_fixtures(VALID_FIXTURE)
    violations = _scan_for_forbidden_terms(_result_to_dict(result))
    assert violations == [], f"Forbidden terms in valid fixture result: {violations}"


def test_load_result_advisory_label_has_no_forbidden_terms() -> None:
    """Advisory label must not contain forbidden terms."""
    result = load_wallet_signal_paper_strategy_candidate_fixtures(VALID_FIXTURE)
    norm = result.advisory_label.lower().replace("_", " ").replace("-", " ")
    for term in _FORBIDDEN_OUTPUT_TERMS:
        assert term.lower() not in norm, (
            f"Forbidden term '{term}' found in advisory_label: {result.advisory_label!r}"
        )


# ---------------------------------------------------------------------------
# Reviewer trap: specific forbidden input values must not appear in output
# ---------------------------------------------------------------------------


def test_trade_ready_not_in_any_result_surface() -> None:
    """'TRADE_READY' must not appear in any loader output surface for any fixture."""
    for fixture in (VALID_FIXTURE, INVALID_STATUS_FIXTURE, INVALID_METADATA_FIXTURE, MALFORMED_FIXTURE):
        result = load_wallet_signal_paper_strategy_candidate_fixtures(fixture)
        result_text = json.dumps(_result_to_dict(result))
        assert "TRADE_READY" not in result_text, (
            f"'TRADE_READY' found in loader output for {fixture.name}: {result_text[:200]!r}"
        )


def test_position_size_not_in_any_result_surface() -> None:
    """'position_size' must not appear in any loader output for any fixture."""
    for fixture in (VALID_FIXTURE, INVALID_STATUS_FIXTURE, INVALID_METADATA_FIXTURE, MALFORMED_FIXTURE):
        result = load_wallet_signal_paper_strategy_candidate_fixtures(fixture)
        result_text = json.dumps(_result_to_dict(result))
        assert "position_size" not in result_text.lower(), (
            f"'position_size' found in loader output for {fixture.name}: {result_text[:200]!r}"
        )


def test_expected_return_not_in_any_result_surface() -> None:
    """'expected_return' must not appear in any loader output for any fixture."""
    for fixture in (VALID_FIXTURE, INVALID_STATUS_FIXTURE, INVALID_METADATA_FIXTURE, MALFORMED_FIXTURE):
        result = load_wallet_signal_paper_strategy_candidate_fixtures(fixture)
        result_text = json.dumps(_result_to_dict(result))
        assert "expected_return" not in result_text.lower(), (
            f"'expected_return' found in loader output for {fixture.name}: {result_text[:200]!r}"
        )


# ---------------------------------------------------------------------------
# Status fragment test
# ---------------------------------------------------------------------------


def test_status_fragment_wp87_exists() -> None:
    """docs/status_entries/WP87.md must exist and reference WP87."""
    fragment = ROOT / "docs" / "status_entries" / "WP87.md"
    assert fragment.is_file(), f"WP87 status fragment not found: {fragment}"
    text = fragment.read_text(encoding="utf-8")
    assert "WP87" in text, "WP87 status fragment must reference WP87"
    assert "wallet_signal_paper_strategy_candidate_fixture_loader" in text, (
        "WP87 status fragment must reference the loader module"
    )


# ---------------------------------------------------------------------------
# Result dataclass structure tests
# ---------------------------------------------------------------------------


def test_result_is_frozen_dataclass() -> None:
    """CandidateFixtureLoadResult must be a frozen dataclass."""
    result = load_wallet_signal_paper_strategy_candidate_fixtures(VALID_FIXTURE)
    with pytest.raises((AttributeError, TypeError)):
        result.valid_records = 999  # type: ignore[misc]


def test_item_is_frozen_dataclass() -> None:
    """CandidateFixtureLoadItem must be a frozen dataclass."""
    result = load_wallet_signal_paper_strategy_candidate_fixtures(VALID_FIXTURE)
    item = result.items[0]
    with pytest.raises((AttributeError, TypeError)):
        item.is_valid = False  # type: ignore[misc]


def test_result_has_advisory_label() -> None:
    """All results must include a non-empty advisory_label."""
    for fixture in (VALID_FIXTURE, INVALID_STATUS_FIXTURE, MALFORMED_FIXTURE):
        result = load_wallet_signal_paper_strategy_candidate_fixtures(fixture)
        assert result.advisory_label
        assert "ADVISORY" in result.advisory_label


def test_missing_path_result_also_has_advisory_label() -> None:
    result = load_wallet_signal_paper_strategy_candidate_fixtures(
        "/nonexistent/wp87_label_test.json"
    )
    assert result.advisory_label
    assert "ADVISORY" in result.advisory_label


# ---------------------------------------------------------------------------
# Empty directory test
# ---------------------------------------------------------------------------


def test_empty_directory_safe_result(tmp_path: Path) -> None:
    """An empty directory must return a safe result with an error, not raise."""
    result = load_wallet_signal_paper_strategy_candidate_fixtures(tmp_path)
    assert result.valid_records == 0
    assert result.total_files == 0
    assert len(result.errors) >= 1
    assert result.items == ()
