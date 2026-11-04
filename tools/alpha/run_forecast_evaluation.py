"""Finite offline forecast evaluation over a verified S10-R3-SRC-01 grounding (S10-R3-FORECAST-01).

  run    --grounding-scratch DIR --cases CASES.json --scratch-dir DIR
         cold-verify the SRC-01 scratch, freeze it with the cases (and an optional WP170 registry),
         forecast or abstain, freeze the cohort, score, write one receipt
  verify --scratch-dir DIR
         re-verify the frozen SRC-01 copy and recompute everything from frozen copies; never writes

Inputs are only caller-named local files. No network (a guard fails the run on any socket use),
no provider, LLM or Hermes, no canonical store write. Output goes only into an empty absolute
scratch directory outside the repository. RESEARCH_ONLY / DIAGNOSTIC_ONLY evidence.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import sys
import time

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.data_layer.analytical_research import forecast_evaluation as FE  # noqa: E402
from src.data_layer.analytical_research import source_grounding as SG  # noqa: E402
from tools.alpha import run_source_grounding as SRC  # noqa: E402

MAX_CASES_BYTES = 4 << 20
MAX_GROUNDING_BYTES = 256 << 20
MAX_REGISTRY_BYTES = 64 << 20


def code_identity() -> str:
    digest = FE.hashlib.sha256()
    for path in (Path(FE.__file__), Path(__file__), Path(SG.__file__), Path(SRC.__file__)):
        digest.update(path.resolve().read_bytes())
    return "code:sha256:" + digest.hexdigest()


def _regular_outside(value: object, scratch: Path, limit: int, code: str) -> Path:
    FE._require(type(value) is str, code)
    path = Path(value)
    FE._require(path.is_absolute() and path.is_file() and not path.is_symlink(), code)
    resolved = path.resolve()
    FE._require(not SRC._inside(resolved, REPO_ROOT) and not SRC._inside(resolved, scratch)
                and 0 < resolved.stat().st_size <= limit, code)
    return resolved


def _copy_grounding(source: Path, target: Path) -> None:
    """Copy the SRC-01 scratch tree; symlinks or oversized trees refuse."""
    total = 0
    for item in source.rglob("*"):
        FE._require(not item.is_symlink(), "GROUNDING_SCRATCH_INVALID")
        total += item.stat().st_size if item.is_file() else 0
    FE._require(total <= MAX_GROUNDING_BYTES, "GROUNDING_SCRATCH_INVALID")
    shutil.copytree(source, target)


def _input_hashes(inputs: Path) -> dict:
    return {p.relative_to(inputs).as_posix(): SG.sha256_hex(p.read_bytes())
            for p in sorted(inputs.rglob("*")) if p.is_file()}


def _safe_id(receipt: object) -> str | None:
    """Echo a receipt id only in its own shape, never arbitrary text from an untrusted receipt."""
    value = receipt.get("receipt_id") if isinstance(receipt, dict) else None
    return value if type(value) is str and FE.re.fullmatch(FE.re.escape(FE.RECEIPT_PREFIX) + "[0-9a-f]{64}", value) else None


def _evaluate(scratch: Path, frozen: dict) -> dict:
    """Shared by run and verify: cold-verify the frozen SRC-01 copy, bind it, compute the core."""
    inputs = scratch / "inputs"
    grounding_dir = inputs / "grounding"
    checked = SRC.verify(grounding_dir)
    FE._require(checked["status"] == "VERIFIED", "GROUNDING_VERIFY_FAILED")
    receipt = SRC._strict_json((grounding_dir / "receipt.json").read_bytes(), "GROUNDING_RECEIPT_UNREADABLE")
    frozen_case = SRC._strict_json((grounding_dir / "frozen_case.json").read_bytes(), "GROUNDING_RECEIPT_UNREADABLE")
    FE.validate_cases(frozen, frozen=True)
    grounding = FE.bind_grounding(receipt, frozen_case, grounding_dir / "inputs", frozen)
    wp170 = FE.bind_wp170(inputs / "wp170.sqlite3" if frozen["wp170"] else None,
                          frozen["wp170"]["experiment_id"] if frozen["wp170"] else None)
    return FE.build_evaluation_core(frozen, grounding, wp170, code_identity(), _input_hashes(inputs))


def run(grounding_scratch: Path, cases_path: Path, scratch_dir: Path) -> dict:
    started = time.perf_counter_ns()
    with SRC.no_network() as attempts:
        scratch = Path(scratch_dir)
        FE._require(scratch.is_absolute() and not SRC._inside(scratch.resolve(), REPO_ROOT), "SCRATCH_INSIDE_REPOSITORY")
        FE._require(not scratch.is_symlink() and (not scratch.exists() or (scratch.is_dir() and not any(scratch.iterdir()))),
                    "SCRATCH_NOT_EMPTY")
        scratch = scratch.resolve()
        grounding = Path(grounding_scratch)
        FE._require(grounding.is_absolute() and grounding.is_dir() and not grounding.is_symlink()
                    and not SRC._inside(grounding.resolve(), REPO_ROOT) and not SRC._inside(scratch, grounding.resolve()),
                    "GROUNDING_SCRATCH_INVALID")
        FE._require(SRC.verify(grounding.resolve())["status"] == "VERIFIED", "GROUNDING_VERIFY_FAILED")
        cases_file = _regular_outside(str(cases_path), scratch, MAX_CASES_BYTES, "CASES_UNREADABLE")
        raw = cases_file.read_bytes()
        FE._require(SG.SECRET_RE.search(raw.decode("utf-8", "replace")) is None, "SECRET_MATERIAL_REJECTED")
        cases = SRC._strict_json(raw, "CASES_JSON_INVALID")
        FE.validate_cases(cases, frozen=False)
        registry = None
        if cases["wp170"] is not None:
            registry = _regular_outside(cases["wp170"]["registry_file"], scratch, MAX_REGISTRY_BYTES, "WP170_REGISTRY_UNUSABLE")
            FE._require(not any(Path(str(registry) + s).exists() for s in ("-wal", "-shm", "-journal")), "STORE_SIDECAR_PRESENT")
        inputs = scratch / "inputs"
        inputs.mkdir(parents=True)
        _copy_grounding(grounding.resolve(), inputs / "grounding")
        frozen = dict(cases)
        if registry is not None:
            shutil.copyfile(registry, inputs / "wp170.sqlite3")
            frozen["wp170"] = dict(cases["wp170"], registry_file="wp170.sqlite3")
        (inputs / "cases.json").write_bytes(raw)
        FE._require(FE.hashlib.sha256(cases_file.read_bytes()).digest() == FE.hashlib.sha256(raw).digest(),
                    "INPUT_CHANGED_DURING_FREEZE")
        (scratch / "frozen_cases.json").write_bytes(SG.canonical_bytes(frozen))
        core = _evaluate(scratch, frozen)
        receipt = FE.finalize_receipt(core)
    FE._require(not attempts, "NETWORK_ATTEMPT_BLOCKED")
    receipt["non_identity"] = {"note": FE.NON_IDENTITY_NOTE, "total_ms": round((time.perf_counter_ns() - started) / 1e6, 3)}
    with open(scratch / "receipt.json", "xb") as handle:
        handle.write(json.dumps(receipt, sort_keys=True, indent=1, ensure_ascii=False).encode("utf-8"))
    return {"status": "RUN_COMPLETE", "receipt_id": receipt["receipt_id"], "score_status": core["score_status"],
            "wp170_status": core["wp170"]["status"], "cohort": core["cohort"]["denominators"],
            "scoring": core["scoring"]["denominators"], "network_attempts": 0}


def verify(scratch_dir: Path) -> dict:
    scratch = Path(scratch_dir)
    FE._require(scratch.is_absolute() and scratch.is_dir() and not SRC._inside(scratch.resolve(), REPO_ROOT), "SCRATCH_INVALID")
    scratch = scratch.resolve()
    with SRC.no_network() as attempts:
        receipt = SRC._strict_json((scratch / "receipt.json").read_bytes() if (scratch / "receipt.json").is_file() else b"",
                                   "RECEIPT_UNREADABLE")
        frozen = SRC._strict_json((scratch / "frozen_cases.json").read_bytes()
                                  if (scratch / "frozen_cases.json").is_file() else b"", "FROZEN_CASES_UNREADABLE")
        raw = (scratch / "inputs" / "cases.json").read_bytes() if (scratch / "inputs" / "cases.json").is_file() else b""
        original = SRC._strict_json(raw, "FROZEN_CASES_UNREADABLE")
        expected = dict(original, wp170=None if original.get("wp170") is None else
                        dict(original["wp170"], registry_file="wp170.sqlite3")) if isinstance(original, dict) else None
        if expected != frozen:
            return {"status": "TAMPER_DETECTED", "failures": ["FROZEN_CASES_MISMATCH"], "network_attempts": 0,
                    "receipt_id": _safe_id(receipt)}
        core = _evaluate(scratch, frozen)
        failures = FE.verify_receipt(receipt, core)
    FE._require(not attempts, "NETWORK_ATTEMPT_BLOCKED")
    return {"status": "VERIFIED" if not failures else "TAMPER_DETECTED", "failures": failures,
            "receipt_id": _safe_id(receipt), "network_attempts": 0}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    first = sub.add_parser("run")
    first.add_argument("--grounding-scratch", required=True, type=Path)
    first.add_argument("--cases", required=True, type=Path)
    first.add_argument("--scratch-dir", required=True, type=Path)
    sub.add_parser("verify").add_argument("--scratch-dir", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        result = (run(args.grounding_scratch, args.cases, args.scratch_dir) if args.command == "run"
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
