"""Offline interface inspection for the sandbox-installed official client."""

from __future__ import annotations

import importlib
import inspect
import sys
from importlib import metadata
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from sandbox_policy import (  # noqa: E402
    CANDIDATE_DISTRIBUTION,
    CANDIDATE_IMPORTS,
    EXCLUDED_METHOD_KEYWORDS,
    PUBLIC_METHOD_CANDIDATES,
    VENV_DIR,
    is_running_inside_sandbox,
)


def load_candidate_module():
    errors: list[str] = []
    for name in CANDIDATE_IMPORTS:
        try:
            return name, importlib.import_module(name)
        except Exception as exc:  # pragma: no cover - depends on optional package
            errors.append(f"{name}: {exc.__class__.__name__}: {exc}")
    raise RuntimeError("; ".join(errors))


def collect_names(module: object) -> set[str]:
    names = {name for name in dir(module) if not name.startswith("_")}
    for submodule_name in ("client", "clob_client"):
        try:
            submodule = importlib.import_module(f"{module.__name__}.{submodule_name}")  # type: ignore[attr-defined]
        except Exception:
            continue
        names.update(name for name in dir(submodule) if not name.startswith("_"))
        client_cls = getattr(submodule, "ClobClient", None)
        if client_cls is not None:
            names.update(name for name, _ in inspect.getmembers(client_cls) if not name.startswith("_"))
    return names


def main() -> int:
    if not is_running_inside_sandbox():
        print("Refusing package inspection outside .venv-official-client/.")
        print(f"Run with: {VENV_DIR / 'Scripts' / 'python.exe'} tools/polymarket/official_client_sandbox/inspect_package.py")
        return 0

    try:
        version = metadata.version(CANDIDATE_DISTRIBUTION)
    except metadata.PackageNotFoundError:
        print(f"{CANDIDATE_DISTRIBUTION} is not installed in the sandbox.")
        return 0

    try:
        module_name, module = load_candidate_module()
    except RuntimeError as exc:
        print(f"Package metadata exists, but import failed: {exc}")
        return 0

    names = collect_names(module)
    public_hits = sorted(name for name in names if name in PUBLIC_METHOD_CANDIDATES)
    excluded_hits = sorted(
        name
        for name in names
        if any(keyword in name.lower() for keyword in EXCLUDED_METHOD_KEYWORDS)
    )

    print("Official client sandbox package inspection")
    print(f"  distribution: {CANDIDATE_DISTRIBUTION}")
    print(f"  version: {version}")
    print(f"  import module: {module_name}")
    print(f"  import path: {getattr(module, '__file__', '(unknown)')}")
    print(f"  public read-only candidate methods located: {public_hits or 'none'}")
    print(f"  excluded live/auth/account method names present: {excluded_hits[:40] or 'none'}")
    print("  inspection only: no client constructed, no network call made")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
