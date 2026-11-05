"""Finite offline outcome -> score -> future-research learning operator (S10-R3-LEARN-01).

  run    --forecast-scratch DIR --outcomes OUTCOMES.json --scratch-dir DIR [--alpha-registry FILE]
         cold-verify the S10-R3-FORECAST-01 scratch, freeze it with the outcome packet (and an optional
         Alpha registry, read-only), verify the frozen copy again, join, score, diagnose, propose, write once
  verify --scratch-dir DIR
         re-verify the frozen forecast copy and recompute everything from frozen copies; never writes

Inputs are only caller-named local files. No network (a guard fails the run on any socket use),
no provider, LLM or Hermes, no canonical Alpha/PIT/WP170 write. Output goes only into an empty
absolute scratch directory outside the repository. RESEARCH_ONLY / DIAGNOSTIC_ONLY / NO_CANONICAL_WRITE.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.data_layer.analytical_research import forecast_evaluation as FE  # noqa: E402
from src.data_layer.analytical_research import learning_feedback as LF  # noqa: E402
from src.data_layer.analytical_research import source_grounding as SG  # noqa: E402
from tools.alpha import run_forecast_evaluation as FCLI  # noqa: E402
from tools.alpha import run_source_grounding as SRC  # noqa: E402

MAX_OUTCOMES_BYTES = FCLI.MAX_CASES_BYTES
MAX_REGISTRY_BYTES = FCLI.MAX_REGISTRY_BYTES
MAX_FORECAST_BYTES = FCLI.MAX_GROUNDING_BYTES + FCLI.MAX_CASES_BYTES + FCLI.MAX_REGISTRY_BYTES


def code_identity() -> str:
    digest = hashlib.sha256()
    for path in (Path(LF.__file__), Path(__file__)):
        digest.update(path.resolve().read_bytes())
    digest.update(FCLI.code_identity().encode("ascii"))  # forecast/grounding code is bound transitively
    return "code:sha256:" + digest.hexdigest()


def _regular_outside(value: Path, scratch: Path, limit: int, code: str) -> Path:
    path = Path(value)
    FE._require(path.is_absolute() and path.is_file() and not path.is_symlink(), code)
    resolved = path.resolve()
    stat = resolved.stat()
    FE._require(not SRC._inside(resolved, REPO_ROOT) and not SRC._inside(resolved, scratch)
                and stat.st_nlink == 1 and 0 < stat.st_size <= limit, code)
    return resolved


def _copy_forecast(source: Path, target: Path) -> None:
    """Copy the FORECAST-01 scratch tree; symlinks, hardlinks or oversized trees refuse."""
    total = 0
    for item in source.rglob("*"):
        FE._require(not item.is_symlink() and (not item.is_file() or item.stat().st_nlink == 1), "FORECAST_SCRATCH_INVALID")
        total += item.stat().st_size if item.is_file() else 0
    FE._require(total <= MAX_FORECAST_BYTES, "FORECAST_SCRATCH_INVALID")
    shutil.copytree(source, target)


def _input_hashes(inputs: Path) -> dict:
    return {p.relative_to(inputs).as_posix(): SG.sha256_hex(p.read_bytes())
            for p in sorted(inputs.rglob("*")) if p.is_file()}


def _safe_id(receipt: object) -> str | None:
    value = receipt.get("receipt_id") if isinstance(receipt, dict) else None
    return value if type(value) is str and FE.re.fullmatch(FE.re.escape(LF.RECEIPT_PREFIX) + "[0-9a-f]{64}", value) else None


def _forecast_verified(path: Path) -> bool:
    """The merged FORECAST-01 verifier; any of its own stops is one closed upstream failure here."""
    try:
        return FCLI.verify(path)["status"] == "VERIFIED"
    except (FE.EvaluationStop, SG.GroundingStop):
        return False


def _read(path: Path, code: str):
    return SRC._strict_json(path.read_bytes() if path.is_file() else b"", code)


def _evaluate(scratch: Path) -> dict:
    """Shared by run and verify: cold-verify the frozen forecast copy, then compute the learning core."""
    inputs = scratch / "inputs"
    forecast_dir = inputs / "forecast"
    FE._require(_forecast_verified(forecast_dir), "FORECAST_VERIFY_FAILED")
    forecast = _read(forecast_dir / "receipt.json", "FORECAST_RECEIPT_UNREADABLE")
    frozen_cases = _read(forecast_dir / "frozen_cases.json", "FORECAST_RECEIPT_UNREADABLE")
    FE._require(forecast["core"]["code_identity"] == FCLI.code_identity(), "FORECAST_CODE_IDENTITY_MISMATCH")
    packet = _read(inputs / "outcomes.json", "OUTCOMES_JSON_INVALID")
    registry = inputs / "alpha.sqlite3"
    selected = {r["market_id"] for r in forecast["core"]["targets"] if r["status"] == "SELECTED"}
    links = LF.alpha_links(registry if registry.is_file() else None, selected)
    return LF.build_learning_core(forecast, frozen_cases, packet, links, code_identity(), _input_hashes(inputs))


def run(forecast_scratch: Path, outcomes_path: Path, scratch_dir: Path, alpha_registry: Path | None = None) -> dict:
    with SRC.no_network() as attempts:
        scratch = Path(scratch_dir)
        FE._require(scratch.is_absolute() and not SRC._inside(scratch.resolve(), REPO_ROOT), "SCRATCH_INSIDE_REPOSITORY")
        FE._require(not scratch.is_symlink() and (not scratch.exists() or (scratch.is_dir() and not any(scratch.iterdir()))),
                    "SCRATCH_NOT_EMPTY")
        scratch = scratch.resolve()
        forecast = Path(forecast_scratch)
        FE._require(forecast.is_absolute() and forecast.is_dir() and not forecast.is_symlink()
                    and not SRC._inside(forecast.resolve(), REPO_ROOT) and not SRC._inside(scratch, forecast.resolve())
                    and not SRC._inside(forecast.resolve(), scratch), "FORECAST_SCRATCH_INVALID")
        FE._require(_forecast_verified(forecast.resolve()), "FORECAST_VERIFY_FAILED")
        outcomes_file = _regular_outside(outcomes_path, scratch, MAX_OUTCOMES_BYTES, "OUTCOMES_UNREADABLE")
        raw = outcomes_file.read_bytes()
        FE._require(SG.SECRET_RE.search(raw.decode("utf-8", "replace")) is None, "SECRET_MATERIAL_REJECTED")
        packet = SRC._strict_json(raw, "OUTCOMES_JSON_INVALID")
        receipt = _read(forecast.resolve() / "receipt.json", "FORECAST_RECEIPT_UNREADABLE")
        LF.validate_packet(packet, receipt["receipt_id"])
        registry = None
        if alpha_registry is not None:
            registry = _regular_outside(alpha_registry, scratch, MAX_REGISTRY_BYTES, "ALPHA_REGISTRY_UNUSABLE")
            FE._require(not any(Path(str(registry) + s).exists() for s in ("-wal", "-shm", "-journal")), "STORE_SIDECAR_PRESENT")
        inputs = scratch / "inputs"
        inputs.mkdir(parents=True)
        _copy_forecast(forecast.resolve(), inputs / "forecast")
        (inputs / "outcomes.json").write_bytes(raw)
        if registry is not None:
            shutil.copyfile(registry, inputs / "alpha.sqlite3")
        FE._require(outcomes_file.read_bytes() == raw, "INPUT_CHANGED_DURING_FREEZE")
        core = _evaluate(scratch)
        receipt = LF.finalize_receipt(core)
    FE._require(not attempts, "NETWORK_ATTEMPT_BLOCKED")
    with open(scratch / "receipt.json", "xb") as handle:
        handle.write(json.dumps(receipt, sort_keys=True, indent=1, ensure_ascii=False).encode("utf-8"))
    return {"status": "RUN_COMPLETE", "receipt_id": receipt["receipt_id"], "posture": core["posture"],
            "write_policy": core["write_policy"], "outcomes": core["outcomes"]["denominators"],
            "scoring": core["scoring"]["denominators"], "proposals": len(core["proposals"]), "network_attempts": 0}


def verify(scratch_dir: Path) -> dict:
    scratch = Path(scratch_dir)
    FE._require(scratch.is_absolute() and scratch.is_dir() and not SRC._inside(scratch.resolve(), REPO_ROOT), "SCRATCH_INVALID")
    scratch = scratch.resolve()
    with SRC.no_network() as attempts:
        receipt = _read(scratch / "receipt.json", "RECEIPT_UNREADABLE")
        core = _evaluate(scratch)
        failures = LF.verify_receipt(receipt, core)
    FE._require(not attempts, "NETWORK_ATTEMPT_BLOCKED")
    return {"status": "VERIFIED" if not failures else "TAMPER_DETECTED", "failures": failures,
            "receipt_id": _safe_id(receipt), "network_attempts": 0}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    first = sub.add_parser("run")
    first.add_argument("--forecast-scratch", required=True, type=Path)
    first.add_argument("--outcomes", required=True, type=Path)
    first.add_argument("--scratch-dir", required=True, type=Path)
    first.add_argument("--alpha-registry", type=Path)
    sub.add_parser("verify").add_argument("--scratch-dir", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        result = (run(args.forecast_scratch, args.outcomes, args.scratch_dir, args.alpha_registry)
                  if args.command == "run" else verify(args.scratch_dir))
    except (FE.EvaluationStop, SG.GroundingStop) as stop:
        result = {"status": "STOPPED", "reason_code": str(stop)}
    except FileExistsError:
        result = {"status": "STOPPED", "reason_code": "WRITE_ONCE_CONFLICT"}
    except Exception:  # noqa: BLE001 - any other failure is closed and never echoes input or a traceback
        result = {"status": "STOPPED", "reason_code": "INTERNAL_VALIDATION_FAILED"}
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] in ("RUN_COMPLETE", "VERIFIED") else 1


if __name__ == "__main__":
    raise SystemExit(main())
