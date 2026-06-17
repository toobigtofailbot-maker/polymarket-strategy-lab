"""Focused tests for WP78 wallet trade event fixture validation and loading."""

from __future__ import annotations

import ast
import importlib
import inspect
import json
import sys
import tempfile
from pathlib import Path
from typing import Any

import pytest

from src.data_layer.wallet_trade_event_fixtures import (
    EXPECTED_NOTICE,
    EXPECTED_SCHEMA_VERSION,
    LoadedWalletTradeEventRecord,
    WalletTradeEventFixtureLoadResult,
    WalletTradeEventValidationResult,
    load_wallet_trade_event_fixtures,
    validate_wallet_trade_event_snapshot,
)


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_EXAMPLE = ROOT / "docs" / "schemas" / "wallet_trade_event_snapshot_v1.example.json"

SAFETY_FLAGS = (
    "manual_research_only",
    "not_automated_copy_trading",
    "no_live_execution",
    "no_order_placement",
    "no_position_sizing",
    "no_risk_override",
    "no_parameter_auto_change",
)

FORBIDDEN_EXACT_KEYS = {
    "buy",
    "sell",
    "entry",
    "exit",
    "position_size",
    "expected_return",
    "profit_target",
    "stop_loss",
    "take_profit",
    "live_signal",
    "execute",
    "auto_copy",
}


def _read_example() -> dict[str, Any]:
    return json.loads(SCHEMA_EXAMPLE.read_text(encoding="utf-8"))


def _walk_keys(value: Any) -> list[str]:
    keys: list[str] = []
    if isinstance(value, dict):
        for key, nested in value.items():
            keys.append(str(key).lower())
            keys.extend(_walk_keys(nested))
    elif isinstance(value, list):
        for item in value:
            keys.extend(_walk_keys(item))
    return keys


def _valid_record(**overrides: Any) -> dict[str, Any]:
    record = {
        "_notice": EXPECTED_NOTICE,
        "_schema_version": EXPECTED_SCHEMA_VERSION,
        "_status": "TEST_FIXTURE",
        "event": {
            "schema_version": EXPECTED_SCHEMA_VERSION,
            "event_id": "evt-001",
            "source_type": "LOCAL_FIXTURE",
            "source_id": "unit-test",
            "observed_at_utc": "2026-01-01T00:00:00Z",
        },
        "wallet_reference": {
            "wallet_id_or_address": "0x0000000000000000000000000000000000000000",
        },
        "market_reference": {
            "market_id": "market-001",
            "condition_id": "condition-001",
            "market_category": "Politics",
            "asset_id": "asset-001",
            "outcome_label": "Yes",
        },
        "observation": {
            "direction_observed": "YES_OBSERVED",
            "price_observed": 0.42,
            "size_observed": 100.0,
        },
        "context": {
            "liquidity_context_available": False,
            "orderbook_context_available": False,
            "copyability_context_available": False,
        },
        "review": {
            "suspicious_flow_flag": False,
            "human_review_required": True,
            "advisory_only_notice": "Historical local fixture observation only.",
        },
        "safety": {flag: True for flag in SAFETY_FLAGS},
    }
    for key, value in overrides.items():
        record[key] = value
    return record


def _write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data), encoding="utf-8")


def _source() -> str:
    module = importlib.import_module("src.data_layer.wallet_trade_event_fixtures")
    return inspect.getsource(module)


def test_static_schema_example_exists_and_parses_as_json() -> None:
    data = _read_example()
    assert data["_notice"] == EXPECTED_NOTICE
    assert data["_schema_version"] == EXPECTED_SCHEMA_VERSION


def test_static_schema_example_uses_placeholder_wallet_identity_only() -> None:
    data = _read_example()
    assert data["wallet_reference"]["wallet_id_or_address"] == (
        "0x0000000000000000000000000000000000000000"
    )
    serialized = json.dumps(data)
    assert "0x0000000000000000000000000000000000000000" in serialized


def test_static_schema_example_includes_required_top_level_sections() -> None:
    data = _read_example()
    for section in (
        "_notice",
        "_schema_version",
        "_status",
        "event",
        "wallet_reference",
        "market_reference",
        "observation",
        "context",
        "review",
        "safety",
    ):
        assert section in data


def test_static_schema_example_includes_all_safety_flags_true() -> None:
    safety = _read_example()["safety"]
    for flag in SAFETY_FLAGS:
        assert safety.get(flag) is True


def test_static_schema_example_has_no_forbidden_trade_like_keys() -> None:
    keys = set(_walk_keys(_read_example()))
    assert keys.isdisjoint(FORBIDDEN_EXACT_KEYS)


def test_validator_accepts_valid_event_record() -> None:
    result = validate_wallet_trade_event_snapshot(_valid_record())
    assert result.is_valid
    assert result.invalid_fields == ()
    assert result.advisory_label == "WALLET_TRADE_EVENT_FIXTURE_VALID"


def test_validator_rejects_missing_required_sections() -> None:
    record = _valid_record()
    del record["market_reference"]
    result = validate_wallet_trade_event_snapshot(record)
    assert not result.is_valid
    assert "market_reference" in result.invalid_fields


def test_validator_rejects_null_required_field() -> None:
    record = _valid_record()
    record["event"]["event_id"] = None
    result = validate_wallet_trade_event_snapshot(record)
    assert not result.is_valid
    assert "event.event_id" in result.invalid_fields


def test_validator_rejects_empty_required_section() -> None:
    record = _valid_record()
    record["wallet_reference"] = {}
    result = validate_wallet_trade_event_snapshot(record)
    assert not result.is_valid
    assert "wallet_reference" in result.invalid_fields
    assert "wallet_reference.wallet_id_or_address" in result.invalid_fields


def test_validator_rejects_unsupported_schema_version() -> None:
    record = _valid_record()
    record["_schema_version"] = "WALLET_TRADE_EVENT_SNAPSHOT_V2"
    record["event"]["schema_version"] = "WALLET_TRADE_EVENT_SNAPSHOT_V2"
    result = validate_wallet_trade_event_snapshot(record)
    assert not result.is_valid
    assert "_schema_version" in result.invalid_fields
    assert "event.schema_version" in result.invalid_fields


def test_validator_rejects_live_api_source_type() -> None:
    record = _valid_record()
    record["event"]["source_type"] = "LIVE_API"
    result = validate_wallet_trade_event_snapshot(record)
    assert not result.is_valid
    assert "event.source_type" in result.invalid_fields
    assert any("LIVE_API" in warning for warning in result.warnings)


@pytest.mark.parametrize("direction", ["BUY", "SELL", "LONG", "SHORT", "ENTER", "EXIT", "TRADE"])
def test_validator_rejects_unsupported_direction_values(direction: str) -> None:
    record = _valid_record()
    record["observation"]["direction_observed"] = direction
    result = validate_wallet_trade_event_snapshot(record)
    assert not result.is_valid
    assert "observation.direction_observed" in result.invalid_fields


def test_validator_accepts_safe_allowed_direction_wording() -> None:
    record = _valid_record()
    record["observation"]["direction_observed"] = "HISTORICAL_OBSERVATION_ONLY"
    result = validate_wallet_trade_event_snapshot(record)
    assert result.is_valid


def test_validator_rejects_safety_flags_missing_or_false() -> None:
    record = _valid_record()
    del record["safety"]["no_live_execution"]
    record["safety"]["no_order_placement"] = False
    result = validate_wallet_trade_event_snapshot(record)
    assert not result.is_valid
    assert "safety.no_live_execution" in result.invalid_fields
    assert "safety.no_order_placement" in result.invalid_fields


@pytest.mark.parametrize("field", ["price_observed", "size_observed"])
def test_validator_rejects_wrong_numeric_field_type(field: str) -> None:
    record = _valid_record()
    record["observation"][field] = "1.0"
    result = validate_wallet_trade_event_snapshot(record)
    assert not result.is_valid
    assert f"observation.{field}" in result.invalid_fields


def test_validator_rejects_non_boolean_context_flag() -> None:
    record = _valid_record()
    record["context"]["liquidity_context_available"] = "false"
    result = validate_wallet_trade_event_snapshot(record)
    assert not result.is_valid
    assert "context.liquidity_context_available" in result.invalid_fields


def test_validator_rejects_real_looking_secret_or_wallet_key_fields() -> None:
    record = _valid_record()
    record["wallet_private_key"] = "not-a-real-key"
    record["api_key"] = "not-a-real-api-key"
    result = validate_wallet_trade_event_snapshot(record)
    assert not result.is_valid
    assert "wallet_private_key" in result.invalid_fields
    assert "api_key" in result.invalid_fields


@pytest.mark.parametrize("key", ["position_size", "expected_return", "execute", "auto_copy"])
def test_validator_rejects_forbidden_exact_keys(key: str) -> None:
    record = _valid_record()
    record[key] = "forbidden"
    result = validate_wallet_trade_event_snapshot(record)
    assert not result.is_valid
    assert key in result.invalid_fields


def test_validator_rejects_malformed_timestamp() -> None:
    record = _valid_record()
    record["event"]["observed_at_utc"] = "2026-01-01"
    result = validate_wallet_trade_event_snapshot(record)
    assert not result.is_valid
    assert "event.observed_at_utc" in result.invalid_fields


def test_validator_result_is_frozen() -> None:
    result = validate_wallet_trade_event_snapshot(_valid_record())
    with pytest.raises((AttributeError, TypeError)):
        result.is_valid = False  # type: ignore[misc]


def test_loader_accepts_single_valid_json_object() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "record.json"
        _write_json(path, _valid_record())
        result = load_wallet_trade_event_fixtures(path)
    assert result.loaded_count == 1
    assert result.valid_count == 1
    assert result.invalid_count == 0
    assert result.errors == ()
    assert result.records[0].record_index is None


def test_loader_accepts_json_list_and_preserves_order() -> None:
    rec1 = _valid_record()
    rec1["event"]["event_id"] = "evt-001"
    rec2 = _valid_record()
    rec2["event"]["event_id"] = "evt-002"
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "records.json"
        _write_json(path, [rec1, rec2])
        result = load_wallet_trade_event_fixtures(path)
    assert result.loaded_count == 2
    assert [r.record["event"]["event_id"] for r in result.records] == ["evt-001", "evt-002"]
    assert [r.record_index for r in result.records] == [0, 1]


def test_loader_accepts_directory_json_files_sorted_by_filename() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        for name in ("z.json", "a.json", "m.json"):
            record = _valid_record()
            record["event"]["event_id"] = name
            _write_json(tmp / name, record)
        result = load_wallet_trade_event_fixtures(tmp)
    assert [r.record["event"]["event_id"] for r in result.records] == ["a.json", "m.json", "z.json"]


def test_loader_does_not_recursively_load_nested_json_files() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        _write_json(tmp / "top.json", _valid_record())
        nested = tmp / "nested"
        nested.mkdir()
        _write_json(nested / "nested.json", _valid_record())
        result = load_wallet_trade_event_fixtures(tmp)
    assert result.loaded_count == 1
    assert result.records[0].source_path.endswith("top.json")


def test_loader_ignores_non_json_files_in_directories() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        _write_json(tmp / "record.json", _valid_record())
        (tmp / "notes.txt").write_text("ignored", encoding="utf-8")
        result = load_wallet_trade_event_fixtures(tmp)
    assert result.loaded_count == 1
    assert result.valid_count == 1


def test_loader_rejects_missing_path() -> None:
    result = load_wallet_trade_event_fixtures("/missing/wallet/events.json")
    assert result.loaded_count == 0
    assert any("does not exist" in error for error in result.errors)


def test_loader_rejects_invalid_json() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "bad.json"
        path.write_text("{ invalid json", encoding="utf-8")
        result = load_wallet_trade_event_fixtures(path)
    assert result.loaded_count == 0
    assert any("Invalid JSON" in error for error in result.errors)


def test_loader_rejects_unsupported_extensions() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "record.jsonl"
        path.write_text("{}", encoding="utf-8")
        result = load_wallet_trade_event_fixtures(path)
    assert result.loaded_count == 0
    assert any("Unsupported file extension" in error for error in result.errors)


@pytest.mark.parametrize("url", [
    "http://example.com/events.json",
    "https://example.com/events.json",
    "ws://example.com/events.json",
    "wss://example.com/events.json",
    "ftp://example.com/events.json",
])
def test_loader_rejects_url_like_paths(url: str) -> None:
    result = load_wallet_trade_event_fixtures(url)
    assert result.loaded_count == 0
    assert any("URL-like path rejected" in error for error in result.errors)


def test_loader_records_invalid_event_without_raising() -> None:
    bad_record = _valid_record()
    bad_record["event"]["source_type"] = "LIVE_API"
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "invalid.json"
        _write_json(path, bad_record)
        result = load_wallet_trade_event_fixtures(path)
    assert result.loaded_count == 1
    assert result.valid_count == 0
    assert result.invalid_count == 1
    assert not result.records[0].validation.is_valid


def test_loader_returns_deterministic_count_fields() -> None:
    good = _valid_record()
    bad = _valid_record()
    bad["safety"]["no_live_execution"] = False
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "records.json"
        _write_json(path, [good, bad])
        first = load_wallet_trade_event_fixtures(path)
        second = load_wallet_trade_event_fixtures(path)
    assert first.loaded_count == second.loaded_count == 2
    assert first.valid_count == second.valid_count == 1
    assert first.invalid_count == second.invalid_count == 1
    assert first.warning_count == second.warning_count


def test_loader_reports_non_object_list_entry_error() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "mixed.json"
        _write_json(path, [_valid_record(), "bad-entry"])
        result = load_wallet_trade_event_fixtures(path)
    assert result.loaded_count == 1
    assert any("index 1" in error and "not an object" in error for error in result.errors)


def test_loader_result_dataclasses_are_frozen() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "record.json"
        _write_json(path, _valid_record())
        result = load_wallet_trade_event_fixtures(path)
    with pytest.raises((AttributeError, TypeError)):
        result.loaded_count = 99  # type: ignore[misc]
    with pytest.raises((AttributeError, TypeError)):
        result.records[0].source_path = "changed"  # type: ignore[misc]
    with pytest.raises((AttributeError, TypeError)):
        result.records[0].validation.is_valid = False  # type: ignore[misc]


def test_dataclass_types_are_frozen() -> None:
    assert WalletTradeEventValidationResult.__dataclass_params__.frozen is True
    assert LoadedWalletTradeEventRecord.__dataclass_params__.frozen is True
    assert WalletTradeEventFixtureLoadResult.__dataclass_params__.frozen is True


def test_module_imports_no_network_libraries() -> None:
    tree = ast.parse(_source())
    forbidden = {"urllib", "requests", "httpx", "aiohttp", "socket", "http.client", "websocket"}
    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
    assert imports.isdisjoint(forbidden)


def test_module_performs_no_file_writes() -> None:
    source = _source()
    for pattern in (".write(", ".write_text(", ".write_bytes(", "open("):
        assert pattern not in source


def test_module_references_no_credentials_or_auth_clients() -> None:
    source = _source()
    forbidden_patterns = (
        "import dotenv",
        "from dotenv",
        "import keyring",
        "import cryptography",
        "import py_clob_client",
        "from py_clob_client",
        "os.getenv",
        "os.environ",
        ".env",
        "auth_client",
        "authenticated_client",
    )
    for pattern in forbidden_patterns:
        assert pattern not in source


def test_module_imports_no_llm_or_agent_libraries() -> None:
    source = _source()
    for pattern in (
        "import anthropic",
        "import openai",
        "import langchain",
        "import llama",
        "import hermes",
        "import transformers",
    ):
        assert pattern not in source


def test_module_does_not_compute_forbidden_wallet_or_trading_metrics() -> None:
    source = _source()
    forbidden_function_patterns = (
        "def compute_wallet_skill",
        "def compute_wallet_rank",
        "def compute_copyability",
        "def compute_research_priority",
        "def compute_strategy",
        "def compute_paper_pnl",
        "def compute_live_pnl",
        "def calculate_copyability",
        "def calculate_expected_return",
        "def rank_wallet",
    )
    for pattern in forbidden_function_patterns:
        assert pattern not in source


def test_loader_source_does_not_use_recursive_directory_scan() -> None:
    source = _source()
    for pattern in ("rglob", "os.walk", "glob.glob"):
        assert pattern not in source


def test_module_not_loaded_from_network_or_llm_libraries() -> None:
    mod_name = "src.data_layer.wallet_trade_event_fixtures"
    mod = sys.modules.get(mod_name) or importlib.import_module(mod_name)
    assert "site-packages" not in str(Path(mod.__file__))


def test_negative_matrix_duplicate_conflicting_input_stays_record_level() -> None:
    first = _valid_record()
    second = _valid_record()
    first["event"]["event_id"] = "duplicate-event-id"
    second["event"]["event_id"] = "duplicate-event-id"
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "records.json"
        _write_json(path, [first, second])
        result = load_wallet_trade_event_fixtures(path)
    assert result.loaded_count == 2
    assert result.valid_count == 2
    assert result.errors == ()


def test_negative_matrix_case_insensitive_forbidden_key_variant() -> None:
    record = _valid_record()
    record["Expected_Return"] = "forbidden"
    result = validate_wallet_trade_event_snapshot(record)
    assert not result.is_valid
    assert "Expected_Return" in result.invalid_fields
