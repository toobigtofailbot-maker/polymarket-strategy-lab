"""Offline Metaculus source-archive quality/URL-dedup comparison over a cold-verified S10-R3-SRC-01 scratch.

  run    --src-scratch DIR --scratch-dir DIR
  verify --scratch-dir DIR

Call path (S10-R3-METACULUS-SRC-01): byte copy of the caller's SRC-01 scratch -> unchanged native
``run_source_grounding.verify`` (must be VERIFIED) -> frozen case / receipt / source bytes
(read-only) -> ``metaculus_source_archive_bridge`` -> genuine vendored Metaculus
``quality.evaluate(models.CaptureResult(...))``, ``models.url_hash`` (``canonicalize_url``) and
``models.content_hash`` -> one content-addressed RESEARCH_ONLY comparison receipt. Native source
admission stays controlling. Every socket entry point is blocked; nothing is downloaded; writes
only inside one empty absolute scratch directory outside the repository. Output never carries
source URLs, body text or local paths. No order, strategy, paper, capital or live authority.
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

from src.data_layer.analytical_research import metaculus_source_archive_bridge as MB  # noqa: E402
from src.data_layer.analytical_research import source_grounding as SG  # noqa: E402
from tools.alpha import run_related_market_alpha as REL  # noqa: E402
from tools.alpha import run_source_grounding as SGCLI  # noqa: E402

WP_ID = "S10-R3-METACULUS-SRC-01"
RECEIPT_SCHEMA = "s10-r3-metaculus-source-archive-quality-receipt-v1"
RECEIPT_PREFIX = "mcsrcqual:sha256:"
CALLER = ("tools/alpha/run_metaculus_source_archive_quality.py:run -> run_source_grounding.verify -> "
          "metaculus_source_archive_bridge.assess_sources -> quality.evaluate / models.url_hash / models.content_hash")
MAX_SRC_BYTES = 160 << 20
MAX_SRC_FILES = 2000
MAX_RUN_SECONDS = 300
CODE_FILES = (Path(MB.__file__), Path(__file__)) + tuple(MB.vendor_dir() / name for name in MB.VENDOR_PINS)


def code_identity() -> str:
    digest = hashlib.sha256()
    for path in CODE_FILES:
        digest.update(path.resolve().read_bytes())
    return "code:sha256:" + digest.hexdigest()


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise MB.MetaculusStop(code)


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _src_files(root: Path) -> list[Path]:
    files, total = [], 0
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        for name in dirnames:
            _require(not REL._unsafe_entry(Path(dirpath) / name, directory=True), "SRC_SCRATCH_UNSAFE")
        for name in filenames:
            path = Path(dirpath) / name
            _require(not REL._unsafe_entry(path, directory=False), "SRC_SCRATCH_UNSAFE")
            total += path.stat().st_size
            files.append(path)
            _require(len(files) <= MAX_SRC_FILES and total <= MAX_SRC_BYTES, "SRC_SCRATCH_TOO_LARGE")
    _require((root / "receipt.json").is_file() and (root / "frozen_case.json").is_file(), "SRC_SCRATCH_INVALID")
    return files


def _hashes(root: Path) -> dict:
    return {p.relative_to(root).as_posix(): _sha(p.read_bytes()) for p in sorted(root.rglob("*")) if p.is_file()}


def freeze(src_dir: Path, scratch: Path) -> None:
    src = REL._caller_path(str(src_dir), directory=True, scratch=scratch)
    _require(src is not None, "SRC_SCRATCH_UNUSABLE")
    for path in _src_files(src):
        target = scratch / "inputs" / "src" / path.relative_to(src)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
        _require(_sha(path.read_bytes()) == _sha(target.read_bytes()), "INPUT_CHANGED_DURING_FREEZE")


def _verify_src(scratch: Path) -> dict:
    try:
        result = SGCLI.verify(scratch / "inputs" / "src")
    except (SG.GroundingStop, OSError):
        raise MB.MetaculusStop("SRC_RECEIPT_NOT_VERIFIED") from None
    _require(result["status"] == "VERIFIED", "SRC_RECEIPT_NOT_VERIFIED")
    return {"status": result["status"], "receipt_id": result["receipt_id"]}


def build_quality_core(input_dir: Path, code_id: str, src_verification: dict) -> dict:
    src_root = Path(input_dir) / "src"
    receipt = SGCLI._strict_json((src_root / "receipt.json").read_bytes(), "SRC_RECEIPT_UNREADABLE")
    _require(receipt.get("receipt_id") == src_verification["receipt_id"], "SRC_RECEIPT_ID_MISMATCH")
    src_core = receipt["core"]
    _require(src_core.get("wp_id") == SG.WP_ID and src_core.get("schema_id") == SG.RECEIPT_SCHEMA, "SRC_RECEIPT_SCHEMA_INVALID")
    case = SGCLI._strict_json((src_root / "frozen_case.json").read_bytes(), "SRC_FROZEN_CASE_UNREADABLE")
    SG.validate_case(case, frozen=True)  # every source file is a fixed sources/NNN.bin name; no caller path is read
    declared = src_core["inputs"]["file_sha256"]

    def read(rel: str) -> bytes:
        raw = (src_root / "inputs" / rel).read_bytes() if (src_root / "inputs" / rel).is_file() else b""
        _require((_sha(raw) if raw else None) == declared.get(rel), "SRC_INPUT_HASH_MISMATCH")
        return raw
    result = MB.assess_sources(case, src_core, read)
    core = {
        "schema_id": RECEIPT_SCHEMA, "wp_id": WP_ID, "posture": SG.RESEARCH_ONLY, "caller": CALLER, "code_identity": code_id,
        "upstream": MB.upstream_identity(),
        "inputs": {"src_receipt_id": src_verification["receipt_id"], "src_verification": src_verification["status"],
                   "src_wp_id": src_core["wp_id"], "src_code_identity": src_core["code_identity"],
                   "corpus_class": src_core["corpus_class"], "origin_authentication": "CALLER_LOCAL_UNAUTHENTICATED",
                   "as_of": src_core["inputs"]["as_of"], "file_sha256": _hashes(src_root)},
        "method": {"text_view": "source_grounding._visible_text (tags stripped, whitespace collapsed) as CaptureResult.markdown",
                   "capture_fields": "url=final_url=frozen url, status_code=frozen http_status, fetched_at=ingestion_time",
                   "evaluable_native_statuses": list(MB.NATIVE_EVALUABLE),
                   "native_quality_pass_statuses": list(MB.NATIVE_QUALITY_PASS),
                   "native_status_rule": "only 2xx passes; login walls fail; temporal/URL/provenance gates precede quality",
                   "upstream_status_rule": "status_code >= 400 fails; 1xx/3xx/None are not gated by status",
                   "upstream_dedup_key": "(models.url_hash(url), CaptureResult.content_hash)",
                   "native_dedup_key": "(market_id, sha256(bytes)) after native quality pass"},
        "results": result["rows"], "counts": result["counts"], "dedup": result["dedup"],
        "invocations": result["invocations"],
        "adoption": {"R3-01": "SELECTIVE_UPSTREAM_CODE_REUSE_OFFLINE",
                     "R3-01-SOURCE_ARCHIVE": "SELECTIVE_UPSTREAM_CODE_REUSE_OFFLINE",
                     "value_status": "OPERATIONAL_USEFULNESS_NOT_VERIFIED", "owner_acceptance": "PENDING",
                     "native_source_admission": "UNCHANGED_CONTROLLING",
                     "program_capability_ids": len(MB.PROGRAM_CAPABILITY_IDS), "other_capability_ids": "UNCHANGED",
                     "r3_23_public_get_activation": "UNCONSUMED_SEPARATE_OWNER_INSTRUCTION"},
        "authority": {"research_only": True, "source_admission": False, "canonical_promotion": False,
                      "authenticated_web_evidence": False, "forecast_probability": False, "tradable": False,
                      "orders": False, "strategy": False, "paper": False, "live": False, "capital": False,
                      "store_writes": False, "network_calls": 0, "provider_calls": 0, "llm_or_hermes": False,
                      "credentials": False, "upstream_package_installed": False},
    }
    return json.loads(SG.canonical_bytes(core))


def finalize(core: dict) -> dict:
    return {"core": core, "receipt_id": RECEIPT_PREFIX + SG.sha256_hex(SG.canonical_bytes({"core": core}))}


def _summary(core: dict) -> dict:
    counts = core["counts"]
    return {key: counts[key] for key in ("sources_total", "upstream_evaluated", "abstained", "divergent_total")}


def run(src_dir: Path, scratch_dir: Path) -> dict:
    started = time.monotonic()
    scratch = REL._check_scratch(Path(scratch_dir))
    if scratch.exists() and any(scratch.iterdir()):
        return _repeat(src_dir, scratch)
    with SGCLI.no_network() as attempts:
        freeze(Path(src_dir), scratch)
        verification = _verify_src(scratch)
        core = build_quality_core(scratch / "inputs", code_identity(), verification)
    _require(not attempts, "NETWORK_ATTEMPT_BLOCKED")
    _require(time.monotonic() - started <= MAX_RUN_SECONDS, "TIME_BUDGET_EXCEEDED")
    receipt = finalize(core)
    with open(scratch / "receipt.json", "xb") as handle:
        handle.write(json.dumps(receipt, sort_keys=True, indent=1, ensure_ascii=False).encode("utf-8"))
    return {"status": "RUN_COMPLETE", "receipt_id": receipt["receipt_id"], **_summary(core),
            "quality_evaluate_invocations": core["invocations"]["quality.evaluate"], "network_attempts": 0}


def _repeat(src_dir: Path, scratch: Path) -> dict:
    """Identical SRC bytes over a verified receipt return it; anything else refuses, nothing is written."""
    _require((scratch / "receipt.json").is_file(), "SCRATCH_NOT_EMPTY")
    checked = verify(scratch)
    _require(checked["status"] == "VERIFIED", "SCRATCH_NOT_EMPTY")
    src = REL._caller_path(str(src_dir), directory=True, scratch=scratch)
    _require(src is not None, "SCRATCH_NOT_EMPTY")
    _src_files(src)
    _require(_hashes(src) == _hashes(scratch / "inputs" / "src"), "SCRATCH_NOT_EMPTY")
    return {"status": "IDEMPOTENT_VERIFIED", "receipt_id": checked["receipt_id"], "network_attempts": 0}


def verify(scratch_dir: Path) -> dict:
    scratch = Path(scratch_dir)
    _require(scratch.is_absolute() and scratch.is_dir() and not REL._inside(scratch.resolve(), REPO_ROOT), "SCRATCH_INVALID")
    scratch = scratch.resolve()
    with SGCLI.no_network() as attempts:
        path = scratch / "receipt.json"
        try:
            receipt = SGCLI._strict_json(path.read_bytes() if path.is_file() else b"", "RECEIPT_UNREADABLE")
        except SG.GroundingStop as stop:
            raise MB.MetaculusStop(str(stop)) from None
        try:
            core = build_quality_core(scratch / "inputs", code_identity(), _verify_src(scratch))
        except (MB.MetaculusStop, SG.GroundingStop, KeyError, TypeError, OSError) as stop:
            code = str(stop) if isinstance(stop, (MB.MetaculusStop, SG.GroundingStop)) else "SRC_INPUT_SHAPE_INVALID"
            return {"status": "TAMPER_DETECTED", "failures": [f"RECOMPUTE_REFUSED:{code}"],
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
    """Closed result for every outcome; refusals carry a stable code and never echo input, URLs or paths."""
    try:
        if command == "run":
            return run(args.src_scratch, args.scratch_dir)
        return verify(args.scratch_dir)
    except (MB.MetaculusStop, SG.GroundingStop) as stop:
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
    run_parser.add_argument("--src-scratch", required=True, type=Path)
    run_parser.add_argument("--scratch-dir", required=True, type=Path)
    sub.add_parser("verify").add_argument("--scratch-dir", required=True, type=Path)
    args = parser.parse_args(argv)
    result = run_safe(args.command, args)
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] in OK_STATUSES else 1


if __name__ == "__main__":
    raise SystemExit(main())
