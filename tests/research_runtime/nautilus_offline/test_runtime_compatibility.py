"""WP168 offline runtime compatibility tests (R002-R006, R029 supporting)."""

from __future__ import annotations

import dataclasses
import importlib.metadata
import pathlib
import sys
import tomllib

import pytest

import src.research_runtime.nautilus_offline as offline
from src.research_runtime.nautilus_offline import (
    NAUTILUS_REQUIRED_VERSION,
    RUNTIME_STATUS_SUPPORTED,
    evaluate_offline_runtime,
)

ROOT = pathlib.Path(__file__).resolve().parents[3]

EXPECTED_DIRECT_DEPENDENCIES = {
    "pyarrow": "25.0.1",
    "duckdb": "1.5.5",
    "polars": "1.44.1",
    "nautilus_trader": "1.231.0",
}


def test_supported_python_range() -> None:
    assert (3, 12) <= sys.version_info[:2] < (3, 15)


def test_pyproject_declares_nautilus_and_wp167_pins_and_range() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    assert project["requires-python"] == ">=3.12,<3.15"
    declared = sorted(project["dependencies"])
    assert declared == sorted(
        f"{name}=={version}" for name, version in EXPECTED_DIRECT_DEPENDENCIES.items()
    )


def test_installed_metadata_matches_nautilus_pin() -> None:
    assert importlib.metadata.version("nautilus_trader") == NAUTILUS_REQUIRED_VERSION
    assert NAUTILUS_REQUIRED_VERSION == "1.231.0"


def test_compatibility_result_supported_and_no_echo() -> None:
    result = evaluate_offline_runtime()
    assert result.is_valid is True
    assert result.status == RUNTIME_STATUS_SUPPORTED
    assert result.error_codes == ()
    assert result.nautilus_version == "1.231.0"
    assert result.advisory_only is True
    assert result.no_execution_authority is True
    # No caller path / raw exception content in the closed public result.
    hits = offline.scan_public_result_for_echo(result, ("Traceback", "\\", "site-packages"))
    assert hits == ()


def test_required_offline_modules_import_and_no_polymarket_extra_or_redis() -> None:
    from src.research_runtime.nautilus_offline.runtime_compatibility import REQUIRED_OFFLINE_MODULES

    import importlib

    for module_name in REQUIRED_OFFLINE_MODULES:
        importlib.import_module(module_name)
    # The Polymarket live adapter (extra) and redis must NOT be required/installed.
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("py_clob_client_v2")
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("redis")


def test_compatibility_result_is_frozen_dataclass() -> None:
    assert dataclasses.is_dataclass(offline.NautilusRuntimeCompatibilityResult)
    result = evaluate_offline_runtime()
    with pytest.raises(dataclasses.FrozenInstanceError):
        result.is_valid = False  # type: ignore[misc]
