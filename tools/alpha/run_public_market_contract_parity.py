"""Finite offline public market search + prediction-market contract parity (S10-R3-EXT-CONTRACTS-01).

  run    --grounding-scratch DIR --cases CASES.json --scratch-dir DIR
  verify --scratch-dir DIR

Call path: caller S10-R3-SRC-01 scratch -> run_source_grounding.verify (cold, before copy) -> frozen
copy -> run_source_grounding.verify again (same receipt id) -> source_grounding.load_corpus /
bind_rule_texts -> field-aware search vs merged rank_markets on the same cases -> one
content-addressed RESEARCH_ONLY receipt. Inputs are only caller-named existing local files; nothing
is downloaded, no provider/SDK/LLM/Hermes is called and every socket entry point is blocked. Writes
only inside one empty absolute scratch directory outside the repository; verify writes nothing.
No tradable side, order, strategy, paper, capital or live authority.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
import time

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.data_layer.analytical_research import alpha_discovery as AD  # noqa: E402
from src.data_layer.analytical_research import public_market_contract_parity as PMC  # noqa: E402
from src.data_layer.analytical_research import source_grounding as SG  # noqa: E402
from tools.alpha import run_related_market_alpha as REL  # noqa: E402  (reused path/size/hardlink guards)
from tools.alpha import run_source_grounding as SGCLI  # noqa: E402

MAX_CASES_BYTES = 1 << 20
MAX_RUN_SECONDS = 300
CODE_FILES = (Path(PMC.__file__), Path(__file__), Path(SG.__file__), Path(SGCLI.__file__), Path(AD.__file__),
              Path(REL.__file__))
OK_STATUSES = ("RUN_COMPLETE", "VERIFIED", "IDEMPOTENT_VERIFIED")


def code_identity() -> str:
    digest = hashlib.sha256()
    for path in CODE_FILES:
        digest.update(path.resolve().read_bytes())
    return "code:sha256:" + digest.hexdigest()


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _verify_grounding(path: Path) -> dict:
    try:
        result = SGCLI.verify(path)
    except (SG.GroundingStop, OSError):
        PMC._stop("GROUNDING_RECEIPT_NOT_VERIFIED")
    PMC._require(result["status"] == "VERIFIED", "GROUNDING_RECEIPT_NOT_VERIFIED")
    return {"status": result["status"], "receipt_id": result["receipt_id"]}


def _load_cases(raw: bytes) -> dict:
    PMC._require(0 < len(raw), "CASES_UNREADABLE")
    cases = SGCLI._strict_json(raw, "CASES_JSON_INVALID")
    PMC.scan_material(cases)
    PMC.validate_cases(cases)
    return cases


def _tree_hashes(root: Path) -> dict:
    return {"grounding/" + p.relative_to(root).as_posix(): _sha(p.read_bytes()) for p in REL._grounding_files(root)}


def _core(scratch: Path, verification: dict) -> dict:
    inputs = scratch / "inputs"
    grounding = inputs / "grounding"

    def read(rel) -> bytes:
        path = grounding / "inputs" / rel if type(rel) is str else None
        return path.read_bytes() if path is not None and path.is_file() and not path.is_symlink() else b""
    raw = (inputs / "cases.json").read_bytes() if (inputs / "cases.json").is_file() else b""
    cases = _load_cases(raw)
    grounding_case = SGCLI._strict_json((grounding / "frozen_case.json").read_bytes(), "GROUNDING_SCRATCH_INVALID")
    hashes = dict(sorted({"cases.json": _sha(raw), **_tree_hashes(grounding)}.items()))
    return PMC.build_parity_core(cases, grounding_case, grounding / "inputs", read, code_identity(), verification, hashes)


def run(grounding_dir: Path, cases_path: Path, scratch_dir: Path) -> dict:
    started = time.monotonic()
    scratch = REL._check_scratch(Path(scratch_dir))
    if scratch.exists() and any(scratch.iterdir()):
        return _repeat(grounding_dir, cases_path, scratch)
    with SGCLI.no_network() as attempts:
        grounding = REL._caller_path(str(grounding_dir), directory=True, scratch=scratch)
        PMC._require(grounding is not None, "GROUNDING_SCRATCH_UNUSABLE")
        original = _verify_grounding(grounding)  # cold-verify the caller's bytes before anything is copied
        raw = REL._read_capped(REL._caller_path(str(cases_path), directory=False, scratch=scratch), MAX_CASES_BYTES)
        _load_cases(raw)
        files = REL._grounding_files(grounding)
        inputs = scratch / "inputs"
        inputs.mkdir(parents=True)
        for path in files:
            target = inputs / "grounding" / path.relative_to(grounding)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, target)
            PMC._require(_sha(path.read_bytes()) == _sha(target.read_bytes()), "INPUT_CHANGED_DURING_FREEZE")
        (inputs / "cases.json").write_bytes(raw)
        frozen = _verify_grounding(inputs / "grounding")
        PMC._require(frozen["receipt_id"] == original["receipt_id"], "INPUT_CHANGED_DURING_FREEZE")
        core = _core(scratch, frozen)
    PMC._require(not attempts, "NETWORK_ATTEMPT_BLOCKED")
    PMC._require(time.monotonic() - started <= MAX_RUN_SECONDS, "TIME_BUDGET_EXCEEDED")
    receipt = PMC.finalize(core)
    with open(scratch / "receipt.json", "xb") as handle:
        handle.write(json.dumps(receipt, sort_keys=True, indent=1, ensure_ascii=False).encode("utf-8"))
    bench = core["benchmark"]
    return {"status": "RUN_COMPLETE", "receipt_id": receipt["receipt_id"], "benchmark_status": bench["status"],
            "denominators": bench["denominators"], "real_benchmark": core["real_benchmark"], "network_attempts": 0}


def _repeat(grounding_dir: Path, cases_path: Path, scratch: Path) -> dict:
    """Identical caller bytes over a verified receipt return it; anything else refuses. Nothing is written."""
    PMC._require((scratch / "receipt.json").is_file(), "SCRATCH_NOT_EMPTY")
    checked = verify(scratch)
    PMC._require(checked["status"] == "VERIFIED", "SCRATCH_NOT_EMPTY")
    grounding = REL._caller_path(str(grounding_dir), directory=True, scratch=scratch)
    raw = REL._read_capped(REL._caller_path(str(cases_path), directory=False, scratch=scratch), MAX_CASES_BYTES)
    frozen = scratch / "inputs"
    PMC._require(grounding is not None and raw == (frozen / "cases.json").read_bytes()
                 and _tree_hashes(grounding) == _tree_hashes(frozen / "grounding"), "SCRATCH_NOT_EMPTY")
    return {"status": "IDEMPOTENT_VERIFIED", "receipt_id": checked["receipt_id"], "network_attempts": 0}


def verify(scratch_dir: Path) -> dict:
    scratch = Path(scratch_dir)
    PMC._require(scratch.is_absolute() and scratch.is_dir() and not REL._inside(scratch.resolve(), REPO_ROOT), "SCRATCH_INVALID")
    scratch = scratch.resolve()
    with SGCLI.no_network() as attempts:
        path = scratch / "receipt.json"
        receipt = SGCLI._strict_json(path.read_bytes() if path.is_file() else b"", "RECEIPT_UNREADABLE")
        try:
            core = _core(scratch, _verify_grounding(scratch / "inputs" / "grounding"))
        except SG.GroundingStop as stop:
            return {"status": "TAMPER_DETECTED", "failures": [f"RECOMPUTE_REFUSED:{stop}"],
                    "receipt_id": receipt.get("receipt_id") if isinstance(receipt, dict) else None, "network_attempts": 0}
    PMC._require(not attempts, "NETWORK_ATTEMPT_BLOCKED")
    failures = []
    if not isinstance(receipt, dict) or set(receipt) != {"core", "receipt_id"} or not isinstance(receipt["core"], dict):
        failures.append("RECEIPT_SHAPE_INVALID")
    else:
        if receipt["receipt_id"] != PMC.finalize(receipt["core"])["receipt_id"]:
            failures.append("RECEIPT_ID_MISMATCH")
        failures.extend(f"OUTPUT_MISMATCH:{k}" for k in sorted(set(core) | set(receipt["core"]))
                        if receipt["core"].get(k) != core.get(k))
    return {"status": "VERIFIED" if not failures else "TAMPER_DETECTED", "failures": failures,
            "receipt_id": receipt.get("receipt_id") if isinstance(receipt, dict) else None, "network_attempts": 0}


def run_safe(command: str, args) -> dict:
    """Closed result for every outcome; refusals carry a stable code and never echo input or paths."""
    try:
        if command == "run":
            return run(args.grounding_scratch, args.cases, args.scratch_dir)
        return verify(args.scratch_dir)
    except SG.GroundingStop as stop:
        return {"status": "STOPPED", "reason_code": str(stop)}
    except FileExistsError:
        return {"status": "STOPPED", "reason_code": "WRITE_ONCE_CONFLICT"}
    except Exception:  # noqa: BLE001 - sanitized: no exception text or path is echoed
        return {"status": "STOPPED", "reason_code": "INTERNAL_REFUSAL"}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    first = sub.add_parser("run")
    for flag in ("--grounding-scratch", "--cases", "--scratch-dir"):
        first.add_argument(flag, required=True, type=Path)
    sub.add_parser("verify").add_argument("--scratch-dir", required=True, type=Path)
    args = parser.parse_args(argv)
    result = run_safe(args.command, args)
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] in OK_STATUSES else 1


if __name__ == "__main__":
    raise SystemExit(main())
