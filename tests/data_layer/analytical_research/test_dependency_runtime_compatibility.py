"""WP167 dependency-pin and runtime-compatibility evidence.

PyArrow and Polars are validated everywhere. DuckDB's exact-version import/execute
proof runs under strict hosted CI (``WP167_STRICT_DUCKDB=1``); locally it is skipped
with an explicit reason because the DuckDB native extension is blocked by Windows
Smart App Control. The pin/floor metadata checks (which never import the DuckDB
native module) run everywhere so the exact three direct dependencies and the
supported Python floor are always proven.
"""

from __future__ import annotations

import importlib.metadata
import os
import pathlib
import sys
import tomllib

import pytest

import src.data_layer.analytical_research as ar


ROOT = pathlib.Path(__file__).resolve().parents[3]

EXPECTED_DIRECT_DEPENDENCIES = {
    "pyarrow": "25.0.1",
    "duckdb": "1.5.5",
    "polars": "1.44.1",
    # WP168 adds the offline NautilusTrader kernel dependency (base install only).
    "nautilus_trader": "1.231.0",
    # WP169 adds the exact websockets pin for the public Market WebSocket data plane.
    "websockets": "17.1",
}


def test_supported_python_floor():
    assert (3, 12) <= sys.version_info[:2] < (3, 15)


def test_pyproject_declares_exact_supported_pins_and_range():
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    project = data["project"]
    assert project["requires-python"] == ">=3.12,<3.15"
    declared = sorted(project["dependencies"])
    assert declared == sorted(
        f"{name}=={version}" for name, version in EXPECTED_DIRECT_DEPENDENCIES.items()
    )


def test_installed_metadata_matches_pins():
    for name, version in EXPECTED_DIRECT_DEPENDENCIES.items():
        assert importlib.metadata.version(name) == version


def test_check_analytical_runtime_passes():
    result = ar.check_analytical_runtime()
    assert result.is_valid and result.status == "ANALYTICAL_RUNTIME_SUPPORTED"
    assert result.error_codes == ()
    assert result.pyarrow_version == "25.0.1"
    assert result.duckdb_version == "1.5.5"
    assert result.polars_version == "1.44.1"
    assert result.advisory_only is True and result.no_execution_authority is True


def test_pyarrow_imports_and_version():
    import pyarrow

    assert pyarrow.__version__ == "25.0.1"


def test_polars_imports_and_version():
    import polars

    assert polars.__version__ == "1.44.1"


def test_check_analytical_runtime_detects_dependency_mismatch(monkeypatch):
    def fake_version(distribution):
        if distribution == "pyarrow":
            return "0.0.0"
        return importlib.metadata.version(distribution)

    monkeypatch.setattr(
        "src.data_layer.analytical_research.research_dataset._installed_version",
        lambda dist: "0.0.0" if dist == "pyarrow" else importlib.metadata.version(dist),
    )
    result = ar.check_analytical_runtime()
    assert not result.is_valid
    assert "ANALYTICS_DEPENDENCY_VERSION_INVALID" in result.error_codes


def test_duckdb_native_module_executes_under_strict_ci():
    strict = os.environ.get("WP167_STRICT_DUCKDB") == "1"
    if not strict:
        pytest.skip(
            "DuckDB native execution proof is asserted only under strict hosted CI "
            "(WP167_STRICT_DUCKDB=1); it is gated off in the local/non-strict "
            "environment regardless of local native-module availability (which is "
            "observational and can change as Windows Smart App Control reputation "
            "evolves)"
        )
    import duckdb

    assert duckdb.__version__ == "1.5.5"
    connection = duckdb.connect()
    try:
        assert connection.execute("SELECT 42").fetchone()[0] == 42
    finally:
        connection.close()
