"""WP168 offline runtime compatibility tests (R002-R006, R029 supporting)."""

from __future__ import annotations

import dataclasses
import importlib.metadata
import pathlib
import sys
import tomllib

import pytest

import src.research_runtime.nautilus_offline as offline
from src.research_runtime.nautilus_offline.conversion import _scan_public_result_for_echo
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
    hits = _scan_public_result_for_echo(result, ("Traceback", "\\", "site-packages"))
    assert hits == ()


def test_required_offline_modules_import_and_no_polymarket_extra() -> None:
    from src.research_runtime.nautilus_offline.runtime_compatibility import REQUIRED_OFFLINE_MODULES

    import importlib

    for module_name in REQUIRED_OFFLINE_MODULES:
        importlib.import_module(module_name)
    # The Polymarket live adapter (extra) and redis must NOT be required/installed.
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("py_clob_client_v2")
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("redis")


def test_package_imports_no_forbidden_runtime_and_no_network(tmp_path, monkeypatch) -> None:
    # R029: the package imports no live/auth/execution/scheduler runtime and opens no network.
    import socket
    import sys

    from test_conversion import valid_stream

    import ast

    package_dir = pathlib.Path(offline.__file__).resolve().parent
    forbidden_roots = (
        "nautilus_trader.live",
        "nautilus_trader.adapters.polymarket",
        "py_clob_client",
        "py_clob_client_v2",
        "redis",
        "websocket",
        "websockets",
        "aiohttp",
        "src.execution_gateway",
        "src.risk_engine",
        "src.strategy_modules",
        "src.paper_trading",
        "sched",
        "apscheduler",
    )

    def _is_forbidden(module_name: str) -> bool:
        return any(module_name == root or module_name.startswith(root + ".") for root in forbidden_roots)

    for source_file in package_dir.glob("*.py"):
        tree = ast.parse(source_file.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert not _is_forbidden(alias.name), f"{source_file.name} imports {alias.name}"
            elif isinstance(node, ast.ImportFrom) and node.module:
                assert not _is_forbidden(node.module), f"{source_file.name} imports from {node.module}"

    # No forbidden module is pulled into sys.modules by importing the package.
    for module_name in ("py_clob_client_v2", "redis"):
        assert module_name not in sys.modules

    # No network: forbid all socket connections, then run the full public pipeline offline.
    def _no_network(*args, **kwargs):
        raise AssertionError("network access is forbidden in the offline replay path")

    monkeypatch.setattr(socket.socket, "connect", _no_network, raising=False)
    monkeypatch.setattr(socket, "create_connection", _no_network, raising=False)

    stream = valid_stream(tmp_path / "src")
    assert stream.is_valid
    build_result = offline.build_catalog(stream, tmp_path / "catalog")
    assert build_result.is_valid
    assert offline.query_catalog(build_result).is_valid
    assert offline.run_offline_replay(stream, tmp_path / "replay").is_valid


def test_compatibility_result_is_frozen_dataclass() -> None:
    assert dataclasses.is_dataclass(offline.NautilusRuntimeCompatibilityResult)
    result = evaluate_offline_runtime()
    with pytest.raises(dataclasses.FrozenInstanceError):
        result.is_valid = False  # type: ignore[misc]
