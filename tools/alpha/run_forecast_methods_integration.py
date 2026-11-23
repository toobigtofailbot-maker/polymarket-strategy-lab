"""Finite offline pinned-method parity over one verified forecast cohort (S10-CAP-B1-METHODS-01).

  run    --forecast-scratch DIR --methods METHODS.json --scratch-dir DIR
         cold-verify the forecast_evaluation scratch (and through it SRC-01 and WP170), freeze it with the methods
         file, run the ForecastBench sampler port, the Wang upstream-objective port and the metric parity probes,
         score through the native scorers, write one write-once receipt
  verify --scratch-dir DIR
         cold-verify the frozen forecast copy and recompute everything from frozen copies; never writes.

Inputs are only caller-named local files. No network (a guard fails the run on any socket use), no provider, LLM or
Hermes, no canonical store write. Output goes only into an empty absolute scratch directory outside the repository.
RESEARCH_ONLY / DIAGNOSTIC_ONLY evidence.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import time

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.data_layer.analytical_research import forecast_evaluation as FE  # noqa: E402
from src.data_layer.analytical_research import forecast_methods_integration as FMI  # noqa: E402
from src.data_layer.analytical_research import source_grounding as SG  # noqa: E402
from tools.alpha import run_forecast_evaluation as FCLI  # noqa: E402
from tools.alpha import run_source_grounding as SRC  # noqa: E402

MAX_METHODS_BYTES = 1 << 20


def code_identity() -> str:
    digest = hashlib.sha256()
    for path in (Path(FMI.__file__), Path(__file__)):
        digest.update(path.resolve().read_bytes())
    digest.update(FCLI.code_identity().encode("ascii"))  # forecast/grounding code is bound transitively
    return "code:sha256:" + digest.hexdigest()


def _safe_id(receipt: object) -> str | None:
    value = receipt.get("receipt_id") if isinstance(receipt, dict) else None
    return value if type(value) is str and FE.re.fullmatch(FE.re.escape(FMI.RECEIPT_PREFIX) + "[0-9a-f]{64}", value) else None


def _evaluate(scratch: Path) -> dict:
    """Shared by run and verify: cold-verify the frozen forecast copy, then recompute the methods core."""
    inputs = scratch / "inputs"
    forecast = inputs / "forecast"
    FE._require(FCLI.verify(forecast)["status"] == "VERIFIED", "FORECAST_VERIFY_FAILED")
    receipt = SRC._strict_json((forecast / "receipt.json").read_bytes(), "FORECAST_RECEIPT_UNREADABLE")
    frozen = SRC._strict_json((forecast / "frozen_cases.json").read_bytes(), "FORECAST_RECEIPT_UNREADABLE")
    methods = SRC._strict_json((inputs / "methods.json").read_bytes() if (inputs / "methods.json").is_file() else b"",
                               "METHODS_UNREADABLE")
    _, native = FE.load_wp170(forecast / "inputs" / "wp170.sqlite3" if frozen["wp170"] else None,
                              frozen["wp170"]["experiment_id"] if frozen["wp170"] else None)
    hashes = {p.relative_to(inputs).as_posix(): SG.sha256_hex(p.read_bytes())
              for p in sorted(inputs.rglob("*")) if p.is_file()}
    return FMI.build_methods_core(receipt, frozen, methods, native, code_identity(), hashes)


def run(forecast_scratch: Path, methods_path: Path, scratch_dir: Path) -> dict:
    started = time.perf_counter_ns()
    with SRC.no_network() as attempts:
        scratch = Path(scratch_dir)
        FE._require(scratch.is_absolute() and not SRC._inside(scratch.resolve(), REPO_ROOT), "SCRATCH_INSIDE_REPOSITORY")
        FE._require(not scratch.is_symlink() and (not scratch.exists() or (scratch.is_dir() and not any(scratch.iterdir()))),
                    "SCRATCH_NOT_EMPTY")
        scratch = scratch.resolve()
        source = Path(forecast_scratch)
        FE._require(source.is_absolute() and source.is_dir() and not source.is_symlink()
                    and not SRC._inside(source.resolve(), REPO_ROOT) and not SRC._inside(scratch, source.resolve()),
                    "FORECAST_SCRATCH_INVALID")
        FE._require(FCLI.verify(source.resolve())["status"] == "VERIFIED", "FORECAST_VERIFY_FAILED")
        methods_file = FCLI._regular_outside(str(methods_path), scratch, MAX_METHODS_BYTES, "METHODS_UNREADABLE")
        raw = methods_file.read_bytes()
        FE._require(SG.SECRET_RE.search(raw.decode("utf-8", "replace")) is None, "SECRET_MATERIAL_REJECTED")
        FMI.validate_methods(SRC._strict_json(raw, "METHODS_JSON_INVALID"))
        inputs = scratch / "inputs"
        inputs.mkdir(parents=True)
        FCLI._copy_grounding(source.resolve(), inputs / "forecast")
        (inputs / "methods.json").write_bytes(raw)
        FE._require(hashlib.sha256(methods_file.read_bytes()).digest() == hashlib.sha256(raw).digest(),
                    "INPUT_CHANGED_DURING_FREEZE")
        core = _evaluate(scratch)
        receipt = FMI.finalize_receipt(core)
    FE._require(not attempts, "NETWORK_ATTEMPT_BLOCKED")
    receipt["non_identity"] = {"note": FE.NON_IDENTITY_NOTE, "total_ms": round((time.perf_counter_ns() - started) / 1e6, 3)}
    with open(scratch / "receipt.json", "xb") as handle:
        handle.write(json.dumps(receipt, sort_keys=True, indent=1, ensure_ascii=False).encode("utf-8"))
    return {"status": "RUN_COMPLETE", "receipt_id": receipt["receipt_id"], "score_status": core["score_status"],
            "sampler": core["sampler"]["denominators"], "scoring": core["scoring"]["denominators"],
            "lift_status": core["paired_comparison"]["lift_status"], "network_attempts": 0}


def verify(scratch_dir: Path) -> dict:
    scratch = Path(scratch_dir)
    FE._require(scratch.is_absolute() and scratch.is_dir() and not SRC._inside(scratch.resolve(), REPO_ROOT), "SCRATCH_INVALID")
    scratch = scratch.resolve()
    with SRC.no_network() as attempts:
        receipt = SRC._strict_json((scratch / "receipt.json").read_bytes() if (scratch / "receipt.json").is_file() else b"",
                                   "RECEIPT_UNREADABLE")
        failures = FMI.verify_receipt(receipt, _evaluate(scratch))
    FE._require(not attempts, "NETWORK_ATTEMPT_BLOCKED")
    return {"status": "VERIFIED" if not failures else "TAMPER_DETECTED", "failures": failures,
            "receipt_id": _safe_id(receipt), "network_attempts": 0}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    first = sub.add_parser("run")
    first.add_argument("--forecast-scratch", required=True, type=Path)
    first.add_argument("--methods", required=True, type=Path)
    first.add_argument("--scratch-dir", required=True, type=Path)
    sub.add_parser("verify").add_argument("--scratch-dir", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        result = (run(args.forecast_scratch, args.methods, args.scratch_dir) if args.command == "run"
                  else verify(args.scratch_dir))
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
