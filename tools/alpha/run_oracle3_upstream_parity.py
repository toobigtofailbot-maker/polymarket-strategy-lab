"""Offline Oracle3 upstream parity over a cold-verified S10-R3-REL-01 receipt (S10-R3-ORACLE-UPSTREAM-01).

  run    --rel-scratch DIR --scratch-dir DIR
  verify --scratch-dir DIR

Call path: byte copy of the caller's REL-01 scratch -> unchanged native
``run_related_market_alpha.verify`` (must be VERIFIED) -> frozen receipt / request / Gamma bytes
(read-only) -> ``oracle3_upstream_bridge`` -> genuine vendored ``oracle3.arbitrage.check_constraint``
with explicit ``oracle3.fees`` schedules -> one content-addressed RESEARCH_ONLY parity receipt.
Every socket entry point is blocked; nothing is downloaded; writes only inside one empty absolute
scratch directory outside the repository. No order, strategy, paper, capital or live authority.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import time

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.data_layer.analytical_research import oracle3_upstream_bridge as OB  # noqa: E402
from src.data_layer.analytical_research import source_grounding as SG  # noqa: E402
from tools.alpha import run_related_market_alpha as REL  # noqa: E402
from tools.alpha import run_source_grounding as SGCLI  # noqa: E402

WP_ID = "S10-R3-ORACLE-UPSTREAM-01"
RECEIPT_SCHEMA = "s10-r3-oracle3-upstream-parity-receipt-v1"
RECEIPT_PREFIX = "oracle3parity:sha256:"
CALLER = ("tools/alpha/run_oracle3_upstream_parity.py:run -> run_related_market_alpha.verify -> "
          "oracle3_upstream_bridge.assess_rel_core -> oracle3.arbitrage.check_constraint")
MAX_REL_BYTES = 200 << 20
MAX_REL_FILES = 3000
CODE_FILES = (Path(OB.__file__), Path(__file__)) + tuple(OB.vendor_dir() / name for name in OB.VENDOR_PINS)


def code_identity() -> str:
    digest = hashlib.sha256()
    for path in CODE_FILES:
        digest.update(path.resolve().read_bytes())
    return "code:sha256:" + digest.hexdigest()


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise OB.Oracle3Stop(code)


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _rel_files(root: Path) -> list[Path]:
    files, total = [], 0
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        for name in dirnames:
            _require(not REL._unsafe_entry(Path(dirpath) / name, directory=True), "REL_SCRATCH_UNSAFE")
        for name in filenames:
            path = Path(dirpath) / name
            _require(not REL._unsafe_entry(path, directory=False), "REL_SCRATCH_UNSAFE")
            total += path.stat().st_size
            files.append(path)
    _require(len(files) <= MAX_REL_FILES and total <= MAX_REL_BYTES, "REL_SCRATCH_TOO_LARGE")
    _require((root / "receipt.json").is_file() and (root / "inputs" / "request.json").is_file(), "REL_SCRATCH_INVALID")
    return files


def _hashes(root: Path) -> dict:
    return {p.relative_to(root).as_posix(): _sha(p.read_bytes()) for p in sorted(root.rglob("*")) if p.is_file()}


def freeze(rel_dir: Path, scratch: Path) -> None:
    rel = REL._caller_path(str(rel_dir), directory=True, scratch=scratch)
    _require(rel is not None, "REL_SCRATCH_UNUSABLE")
    for path in _rel_files(rel):
        target = scratch / "inputs" / "rel" / path.relative_to(rel)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
        _require(_sha(path.read_bytes()) == _sha(target.read_bytes()), "INPUT_CHANGED_DURING_FREEZE")


def _verify_rel(scratch: Path) -> dict:
    try:
        result = REL.verify(scratch / "inputs" / "rel")
    except SG.GroundingStop:
        raise OB.Oracle3Stop("REL_RECEIPT_NOT_VERIFIED") from None
    _require(result["status"] == "VERIFIED", "REL_RECEIPT_NOT_VERIFIED")
    return {"status": result["status"], "receipt_id": result["receipt_id"]}


def build_parity_core(input_dir: Path, code_id: str, rel_verification: dict) -> dict:
    rel_root = Path(input_dir) / "rel"

    def read(rel: str) -> bytes:
        path = rel_root / "inputs" / rel
        return path.read_bytes() if type(rel) is str and ".." not in Path(rel).parts and path.is_file() else b""
    receipt = REL._strict_json((rel_root / "receipt.json").read_bytes(), "REL_RECEIPT_UNREADABLE")
    _require(receipt.get("receipt_id") == rel_verification["receipt_id"], "REL_RECEIPT_ID_MISMATCH")
    rel_core = receipt["core"]
    request_raw = read("request.json")
    _require(_sha(request_raw) == rel_core["inputs"]["file_sha256"].get("request.json"), "REL_INPUT_HASH_MISMATCH")
    request = REL._strict_json(request_raw, "REL_REQUEST_UNREADABLE")
    result = OB.assess_rel_core(rel_core, request, read)
    core = {
        "schema_id": RECEIPT_SCHEMA, "wp_id": WP_ID, "posture": SG.RESEARCH_ONLY, "caller": CALLER, "code_identity": code_id,
        "upstream": OB.upstream_identity(),
        "inputs": {"rel_receipt_id": rel_verification["receipt_id"], "rel_verification": rel_verification["status"],
                   "rel_wp_id": rel_core["wp_id"], "rel_code_identity": rel_core["code_identity"],
                   "corpus_class": rel_core["corpus_class"], "decision_time": rel_core["inputs"]["decision_time"],
                   "basket_shares": request["basket_shares"], "fee_policy": rel_core["fee_policy"],
                   "file_sha256": _hashes(rel_root)},
        "method": {"relations": OB.RELATIONS, "admitted_real_world": list(OB.ADMITTED_REAL_WORLD), "venue": OB.VENUE,
                   "quote_source": "native best_ask of COST_KNOWN legs in non-NOT_EXECUTABLE native baskets",
                   "fee_source": "explicit TEST_ONLY rate or per-market frozen Gamma feeSchedule; never default/category",
                   "order_type": "taker", "comparison": "upstream float top-of-book vs native exact Decimal depth sweep"},
        "results": result["cases"], "counts": result["counts"],
        "check_constraint_invocations": result["check_constraint_invocations"],
        "adoption": {"R3-03": "SELECTIVE_UPSTREAM_CODE_REUSE", "R3-03-FEES": "SELECTIVE_UPSTREAM_CODE_REUSE",
                     "value_status": "CONDITIONAL_NOT_VALUE_VERIFIED", "owner_acceptance": "PENDING",
                     "R3-04": "REFERENCE_ONLY_UNCHANGED", "R3-11": "REFERENCE_ONLY_UNCHANGED", "R3-19": "REFERENCE_ONLY_UNCHANGED",
                     "program_capability_ids": len(OB.PROGRAM_CAPABILITY_IDS), "other_capability_ids": "UNCHANGED",
                     "r3_23_public_get_activation": "UNCONSUMED_SEPARATE_OWNER_INSTRUCTION"},
        "authority": {"research_only": True, "tradable": False, "executable_edge": False, "guaranteed_arbitrage": False,
                      "profit_claim": False, "orders": False, "strategy": False, "paper": False, "live": False,
                      "capital": False, "store_writes": False, "network_calls": 0, "provider_calls": 0,
                      "credentials": False, "upstream_package_installed": False},
    }
    return json.loads(SG.canonical_bytes(core))


def finalize(core: dict) -> dict:
    return {"core": core, "receipt_id": RECEIPT_PREFIX + SG.sha256_hex(SG.canonical_bytes({"core": core}))}


def run(rel_dir: Path, scratch_dir: Path) -> dict:
    started = time.monotonic()
    scratch = REL._check_scratch(Path(scratch_dir))
    if scratch.exists() and any(scratch.iterdir()):
        return _repeat(rel_dir, scratch)
    with SGCLI.no_network() as attempts:
        freeze(Path(rel_dir), scratch)
        verification = _verify_rel(scratch)
        core = build_parity_core(scratch / "inputs", code_identity(), verification)
    _require(not attempts, "NETWORK_ATTEMPT_BLOCKED")
    _require(time.monotonic() - started <= REL.MAX_RUN_SECONDS, "TIME_BUDGET_EXCEEDED")
    receipt = finalize(core)
    with open(scratch / "receipt.json", "xb") as handle:
        handle.write(json.dumps(receipt, sort_keys=True, indent=1, ensure_ascii=False).encode("utf-8"))
    return {"status": "RUN_COMPLETE", "receipt_id": receipt["receipt_id"], "cases": core["counts"]["cases_total"],
            "check_constraint_invocations": core["check_constraint_invocations"], "network_attempts": 0}


def _repeat(rel_dir: Path, scratch: Path) -> dict:
    """Identical REL bytes over a verified receipt return it; anything else refuses, nothing is written."""
    _require((scratch / "receipt.json").is_file(), "SCRATCH_NOT_EMPTY")
    checked = verify(scratch)
    _require(checked["status"] == "VERIFIED", "SCRATCH_NOT_EMPTY")
    rel = REL._caller_path(str(rel_dir), directory=True, scratch=scratch)
    _require(rel is not None, "SCRATCH_NOT_EMPTY")
    _rel_files(rel)
    _require(_hashes(rel) == _hashes(scratch / "inputs" / "rel"), "SCRATCH_NOT_EMPTY")
    return {"status": "IDEMPOTENT_VERIFIED", "receipt_id": checked["receipt_id"], "network_attempts": 0}


def verify(scratch_dir: Path) -> dict:
    scratch = Path(scratch_dir)
    _require(scratch.is_absolute() and scratch.is_dir() and not REL._inside(scratch.resolve(), REPO_ROOT), "SCRATCH_INVALID")
    scratch = scratch.resolve()
    with SGCLI.no_network() as attempts:
        path = scratch / "receipt.json"
        receipt = REL._strict_json(path.read_bytes() if path.is_file() else b"", "RECEIPT_UNREADABLE")
        try:
            core = build_parity_core(scratch / "inputs", code_identity(), _verify_rel(scratch))
        except (OB.Oracle3Stop, SG.GroundingStop) as stop:
            return {"status": "TAMPER_DETECTED", "failures": [f"RECOMPUTE_REFUSED:{stop}"],
                    "receipt_id": receipt.get("receipt_id") if isinstance(receipt, dict) else None, "network_attempts": 0}
    _require(not attempts, "NETWORK_ATTEMPT_BLOCKED")
    failures = []
    if not isinstance(receipt, dict) or set(receipt) != {"core", "receipt_id"} or not isinstance(receipt["core"], dict):
        failures.append("RECEIPT_SHAPE_INVALID")
    else:
        if receipt["receipt_id"] != finalize(receipt["core"])["receipt_id"]:
            failures.append("RECEIPT_ID_MISMATCH")
        failures.extend(f"OUTPUT_MISMATCH:{k}" for k in sorted(set(core) | set(receipt["core"]))
                        if receipt["core"].get(k) != core.get(k))
    return {"status": "VERIFIED" if not failures else "TAMPER_DETECTED", "failures": failures,
            "receipt_id": receipt.get("receipt_id") if isinstance(receipt, dict) else None, "network_attempts": 0}


def run_safe(command: str, args) -> dict:
    """Closed result for every outcome; refusals carry a stable code and never echo input or paths."""
    try:
        if command == "run":
            return run(args.rel_scratch, args.scratch_dir)
        return verify(args.scratch_dir)
    except (OB.Oracle3Stop, SG.GroundingStop) as stop:
        return {"status": "STOPPED", "reason_code": str(stop)}
    except FileExistsError:
        return {"status": "STOPPED", "reason_code": "WRITE_ONCE_CONFLICT"}
    except Exception:  # noqa: BLE001 - sanitized: no exception text or path is echoed
        return {"status": "STOPPED", "reason_code": "INTERNAL_REFUSAL"}


OK_STATUSES = ("RUN_COMPLETE", "VERIFIED", "IDEMPOTENT_VERIFIED")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    run_parser = sub.add_parser("run")
    run_parser.add_argument("--rel-scratch", required=True, type=Path)
    run_parser.add_argument("--scratch-dir", required=True, type=Path)
    sub.add_parser("verify").add_argument("--scratch-dir", required=True, type=Path)
    args = parser.parse_args(argv)
    result = run_safe(args.command, args)
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] in OK_STATUSES else 1


if __name__ == "__main__":
    raise SystemExit(main())
