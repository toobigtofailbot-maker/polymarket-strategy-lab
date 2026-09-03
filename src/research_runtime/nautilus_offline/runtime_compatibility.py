"""WP168 offline Nautilus runtime compatibility (local, offline, fail-closed).

Proves the exact ``nautilus_trader==1.231.0`` pin, the supported Python range, and the
importability of the required offline modules for the deterministic replay path, with no
network, no live/auth/Polymarket-extra/Redis requirement, and no raw exception/path echo.
"""

from __future__ import annotations

import importlib
import importlib.metadata as _metadata
import sys
from dataclasses import dataclass, field

NAUTILUS_DISTRIBUTION = "nautilus_trader"
NAUTILUS_REQUIRED_VERSION = "1.231.0"
SUPPORTED_PYTHON_MIN = (3, 12)
SUPPORTED_PYTHON_MAX_EXCLUSIVE = (3, 15)

RUNTIME_STATUS_SUPPORTED = "NAUTILUS_OFFLINE_RUNTIME_SUPPORTED"
RUNTIME_STATUS_REJECTED = "NAUTILUS_OFFLINE_RUNTIME_REJECTED"

RUNTIME_ERROR_UNSUPPORTED = "NAUTILUS_RUNTIME_UNSUPPORTED"
RUNTIME_ERROR_DEPENDENCY_VERSION_INVALID = "NAUTILUS_DEPENDENCY_VERSION_INVALID"
RUNTIME_ERROR_IMPORT_UNAVAILABLE = "NAUTILUS_IMPORT_UNAVAILABLE"

# Required offline modules; the Polymarket live adapter is intentionally absent.
REQUIRED_OFFLINE_MODULES = (
    "nautilus_trader.model.instruments",
    "nautilus_trader.model.identifiers",
    "nautilus_trader.model.objects",
    "nautilus_trader.model.data",
    "nautilus_trader.model.currencies",
    "nautilus_trader.persistence.catalog.parquet",
    "nautilus_trader.backtest.engine",
)


@dataclass(frozen=True)
class NautilusRuntimeCompatibilityResult:
    is_valid: bool
    status: str
    error_codes: tuple[str, ...]
    nautilus_version: str | None
    python_version: str
    advisory_only: bool = True
    no_execution_authority: bool = True


def _python_version_text() -> str:
    return f"{sys.version_info[0]}.{sys.version_info[1]}.{sys.version_info[2]}"


def _rejected(code: str, nautilus_version: str | None) -> NautilusRuntimeCompatibilityResult:
    return NautilusRuntimeCompatibilityResult(
        is_valid=False,
        status=RUNTIME_STATUS_REJECTED,
        error_codes=(code,),
        nautilus_version=nautilus_version,
        python_version=_python_version_text(),
        advisory_only=True,
        no_execution_authority=True,
    )


def evaluate_offline_runtime() -> NautilusRuntimeCompatibilityResult:
    """Return the closed offline-runtime compatibility result. Never raises, never echoes."""
    version_info = sys.version_info[:2]
    if not (SUPPORTED_PYTHON_MIN <= version_info < SUPPORTED_PYTHON_MAX_EXCLUSIVE):
        return _rejected(RUNTIME_ERROR_UNSUPPORTED, None)

    try:
        installed = _metadata.version(NAUTILUS_DISTRIBUTION)
    except Exception:
        return _rejected(RUNTIME_ERROR_IMPORT_UNAVAILABLE, None)
    if installed != NAUTILUS_REQUIRED_VERSION:
        return _rejected(RUNTIME_ERROR_DEPENDENCY_VERSION_INVALID, installed)

    for module_name in REQUIRED_OFFLINE_MODULES:
        try:
            importlib.import_module(module_name)
        except Exception:
            return _rejected(RUNTIME_ERROR_IMPORT_UNAVAILABLE, installed)

    return NautilusRuntimeCompatibilityResult(
        is_valid=True,
        status=RUNTIME_STATUS_SUPPORTED,
        error_codes=(),
        nautilus_version=installed,
        python_version=_python_version_text(),
        advisory_only=True,
        no_execution_authority=True,
    )
