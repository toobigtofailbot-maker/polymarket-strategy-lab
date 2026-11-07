"""Finite offline official SDK public search over frozen fixture pages (S10-R3-SDK-DIRECT-01).

  run    --grounding-scratch DIR --ext-cases CASES.json --sdk-pages PAGES.json --scratch-dir DIR
  verify --scratch-dir DIR

Call path: caller S10-R3-SRC-01 scratch -> run_source_grounding.verify (cold, before copy) -> frozen
copy -> verify again (same receipt id) -> run_public_market_contract_parity._core (merged
EXT-CONTRACTS-01 comparators on the same cases, its code identity unchanged) -> for each frozen page
one real polymarket-client 0.10.0 PublicClient.search(...).first_page() answered by
httpx.MockTransport -> typed SDK results crossed with native identities -> one content-addressed
RESEARCH_ONLY receipt. Inputs are only caller-named local files; every socket entry point is blocked
and the SDK never sees a real host. Writes only inside one empty absolute scratch directory outside
the repository; verify re-invokes the SDK on the frozen bytes and writes nothing.
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
import tracemalloc

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.data_layer.analytical_research import official_sdk_search_bridge as OSB  # noqa: E402
from src.data_layer.analytical_research import source_grounding as SG  # noqa: E402
from tools.alpha import run_public_market_contract_parity as PMCCLI  # noqa: E402
from tools.alpha import run_related_market_alpha as REL  # noqa: E402  (reused path/size/hardlink guards)
from tools.alpha import run_source_grounding as SGCLI  # noqa: E402

MAX_PAGES_BYTES = 8 << 20
MAX_RUN_SECONDS = 300
MAX_PEAK_BYTES = 512 << 20
CODE_FILES = (Path(OSB.__file__), Path(__file__))
OK_STATUSES = ("RUN_COMPLETE", "VERIFIED", "IDEMPOTENT_VERIFIED")


def code_identity() -> str:
    digest = hashlib.sha256(PMCCLI.code_identity().encode())
    for path in CODE_FILES:
        digest.update(path.resolve().read_bytes())
    return "code:sha256:" + digest.hexdigest()


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _load_pages(raw: bytes) -> dict:
    OSB._require(0 < len(raw), "PAGES_UNREADABLE")
    pages = SGCLI._strict_json(raw, "PAGES_JSON_INVALID")
    OSB.PMC.scan_material(pages)
    return pages


def _core(scratch: Path, verification: dict, timer=None) -> tuple[dict, dict]:
    inputs = scratch / "inputs"
    ext_core = PMCCLI._core(scratch, verification)  # merged EXT comparators over the same frozen cases
    cases_raw = (inputs / "cases.json").read_bytes()
    pages_raw = (inputs / "sdk_pages.json").read_bytes() if (inputs / "sdk_pages.json").is_file() else b""
    ext_cases = PMCCLI._load_cases(cases_raw)
    pages = _load_pages(pages_raw)
    hashes = dict(sorted({"cases.json": _sha(cases_raw), "sdk_pages.json": _sha(pages_raw),
                          **PMCCLI._tree_hashes(inputs / "grounding")}.items()))
    return OSB.build_sdk_core(ext_core, ext_cases, pages, SGCLI._strict_json, code_identity(), PMCCLI.code_identity(),
                              hashes, timer)


def run(grounding_dir: Path, cases_path: Path, pages_path: Path, scratch_dir: Path) -> dict:
    started = time.monotonic()
    scratch = REL._check_scratch(Path(scratch_dir))
    if scratch.exists() and any(scratch.iterdir()):
        return _repeat(grounding_dir, cases_path, pages_path, scratch)
    OSB.sdk_identity()  # wrong version, source bytes or method: stop before anything is copied
    with SGCLI.no_network() as attempts:
        grounding = REL._caller_path(str(grounding_dir), directory=True, scratch=scratch)
        OSB._require(grounding is not None, "GROUNDING_SCRATCH_UNUSABLE")
        original = PMCCLI._verify_grounding(grounding)
        cases_raw = REL._read_capped(REL._caller_path(str(cases_path), directory=False, scratch=scratch), PMCCLI.MAX_CASES_BYTES)
        PMCCLI._load_cases(cases_raw)
        pages_raw = REL._read_capped(REL._caller_path(str(pages_path), directory=False, scratch=scratch), MAX_PAGES_BYTES)
        _load_pages(pages_raw)
        files = REL._grounding_files(grounding)
        inputs = scratch / "inputs"
        inputs.mkdir(parents=True)
        for path in files:
            target = inputs / "grounding" / path.relative_to(grounding)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, target)
            OSB._require(_sha(path.read_bytes()) == _sha(target.read_bytes()), "INPUT_CHANGED_DURING_FREEZE")
        (inputs / "cases.json").write_bytes(cases_raw)
        (inputs / "sdk_pages.json").write_bytes(pages_raw)
        frozen = PMCCLI._verify_grounding(inputs / "grounding")
        OSB._require(frozen["receipt_id"] == original["receipt_id"], "INPUT_CHANGED_DURING_FREEZE")
        tracemalloc.start()
        try:
            core, measured = _core(scratch, frozen, time.perf_counter_ns)
            peak = tracemalloc.get_traced_memory()[1]
        finally:
            tracemalloc.stop()
    OSB._require(not attempts, "NETWORK_ATTEMPT_BLOCKED")
    OSB._require(time.monotonic() - started <= MAX_RUN_SECONDS, "TIME_BUDGET_EXCEEDED")
    OSB._require(peak <= MAX_PEAK_BYTES, "MEMORY_BUDGET_EXCEEDED")
    receipt = OSB.finalize(core, dict(measured, peak_traced_bytes=peak))
    with open(scratch / "receipt.json", "xb") as handle:
        handle.write(json.dumps(receipt, sort_keys=True, indent=1, ensure_ascii=False).encode("utf-8"))
    comparison = core["comparison"]
    return {"status": "RUN_COMPLETE", "receipt_id": receipt["receipt_id"], "comparison_status": comparison["status"],
            "denominators": comparison["denominators"], "real_benchmark": core["real_benchmark"], "network_attempts": 0}


def _repeat(grounding_dir: Path, cases_path: Path, pages_path: Path, scratch: Path) -> dict:
    """Identical caller bytes over a verified receipt return it; anything else refuses. Nothing is written."""
    OSB._require((scratch / "receipt.json").is_file(), "SCRATCH_NOT_EMPTY")
    checked = verify(scratch)
    OSB._require(checked["status"] == "VERIFIED", "SCRATCH_NOT_EMPTY")
    grounding = REL._caller_path(str(grounding_dir), directory=True, scratch=scratch)
    cases_raw = REL._read_capped(REL._caller_path(str(cases_path), directory=False, scratch=scratch), PMCCLI.MAX_CASES_BYTES)
    pages_raw = REL._read_capped(REL._caller_path(str(pages_path), directory=False, scratch=scratch), MAX_PAGES_BYTES)
    frozen = scratch / "inputs"
    OSB._require(grounding is not None and cases_raw == (frozen / "cases.json").read_bytes()
                 and pages_raw == (frozen / "sdk_pages.json").read_bytes()
                 and PMCCLI._tree_hashes(grounding) == PMCCLI._tree_hashes(frozen / "grounding"), "SCRATCH_NOT_EMPTY")
    return {"status": "IDEMPOTENT_VERIFIED", "receipt_id": checked["receipt_id"], "network_attempts": 0}


def _measurements_ok(value: object) -> bool:
    keys = {"sdk_invocations", "sdk_elapsed_ns_total", "sdk_elapsed_ns_max", "peak_traced_bytes", "reproducible"}
    return (isinstance(value, dict) and set(value) == keys and value["reproducible"] is False
            and all(type(value[k]) is int and value[k] >= 0 for k in keys - {"reproducible"})
            and value["peak_traced_bytes"] <= MAX_PEAK_BYTES)


def verify(scratch_dir: Path) -> dict:
    scratch = Path(scratch_dir)
    OSB._require(scratch.is_absolute() and scratch.is_dir() and not REL._inside(scratch.resolve(), REPO_ROOT), "SCRATCH_INVALID")
    scratch = scratch.resolve()
    with SGCLI.no_network() as attempts:
        path = scratch / "receipt.json"
        receipt = SGCLI._strict_json(path.read_bytes() if path.is_file() else b"", "RECEIPT_UNREADABLE")
        try:
            core, measured = _core(scratch, PMCCLI._verify_grounding(scratch / "inputs" / "grounding"))
        except SG.GroundingStop as stop:
            return {"status": "TAMPER_DETECTED", "failures": [f"RECOMPUTE_REFUSED:{stop}"],
                    "receipt_id": receipt.get("receipt_id") if isinstance(receipt, dict) else None, "network_attempts": 0}
    OSB._require(not attempts, "NETWORK_ATTEMPT_BLOCKED")
    failures = []
    if not isinstance(receipt, dict) or set(receipt) != {"core", "receipt_id", "measurements"} \
            or not isinstance(receipt["core"], dict):
        failures.append("RECEIPT_SHAPE_INVALID")
    else:
        if receipt["receipt_id"] != OSB.finalize(receipt["core"], {})["receipt_id"]:
            failures.append("RECEIPT_ID_MISMATCH")
        failures.extend(f"OUTPUT_MISMATCH:{k}" for k in sorted(set(core) | set(receipt["core"]))
                        if receipt["core"].get(k) != core.get(k))
        if not _measurements_ok(receipt["measurements"]) \
                or receipt["measurements"]["sdk_invocations"] != measured["sdk_invocations"]:
            failures.append("MEASUREMENTS_INVALID")
    return {"status": "VERIFIED" if not failures else "TAMPER_DETECTED", "failures": failures,
            "receipt_id": receipt.get("receipt_id") if isinstance(receipt, dict) else None, "network_attempts": 0}


def run_safe(command: str, args) -> dict:
    """Closed result for every outcome; refusals carry a stable code and never echo input or paths."""
    try:
        if command == "run":
            return run(args.grounding_scratch, args.ext_cases, args.sdk_pages, args.scratch_dir)
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
    for flag in ("--grounding-scratch", "--ext-cases", "--sdk-pages", "--scratch-dir"):
        first.add_argument(flag, required=True, type=Path)
    sub.add_parser("verify").add_argument("--scratch-dir", required=True, type=Path)
    args = parser.parse_args(argv)
    result = run_safe(args.command, args)
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] in OK_STATUSES else 1


if __name__ == "__main__":
    raise SystemExit(main())
