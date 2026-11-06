"""Finite offline two-role research cooperation with grounded citations (S10-R3-HERMES-COOP-01).

  run    --grounding-scratch DIR --case CASE.json --scratch-dir DIR
  verify --scratch-dir DIR

Call path: copy of an existing S10-R3-SRC-01 scratch -> native ``run_source_grounding.verify``
(cold recompute, must be VERIFIED) -> native ``load_corpus``/``bind_rule_texts``/
``evaluate_sources``/``join_alpha_candidates`` -> ``hermes_cooperation.build_core`` -> one
content-addressed RESEARCH_ONLY receipt. The FORECASTER/FALSIFIER submissions in the case file
are caller-supplied; this tool never runs Hermes, ``delegate_task``, a provider, a model or a
socket (every socket entry point is blocked). Writes only inside one empty absolute scratch
directory outside the repository. The SRC-01 CLI is called, never modified, so historical
SRC-01 receipts keep their code identity.

Exit codes: 0 RUN_COMPLETE / VERIFIED / IDEMPOTENT_VERIFIED, 1 refusal or tamper, 2 usage error.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import sys
import time

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.data_layer.analytical_research import hermes_cooperation as HC  # noqa: E402
from src.data_layer.analytical_research import source_grounding as SG  # noqa: E402
from src.research_runtime.hermes_controlled_runtime import models as HM  # noqa: E402
from tools.alpha import run_source_grounding as SGCLI  # noqa: E402

MAX_CASE_BYTES = 256 << 10
MAX_GROUNDING_BYTES = 64 << 20
MAX_GROUNDING_FILES = 2000
MAX_RUN_SECONDS = 300
SECRET_DIR_PARTS = {".ssh", ".aws", ".gnupg", ".azure", ".kube", ".docker", "credentials", "secrets", ".password-store"}
FILE_ATTRIBUTE_REPARSE_POINT = 0x400
CODE_FILES = (Path(HC.__file__), Path(__file__), Path(SG.__file__), Path(SGCLI.__file__), Path(HM.__file__))
OK_STATUSES = ("RUN_COMPLETE", "VERIFIED", "IDEMPOTENT_VERIFIED")


def code_identity() -> str:
    digest = hashlib.sha256()
    for path in CODE_FILES:
        digest.update(path.resolve().read_bytes())
    return "code:sha256:" + digest.hexdigest()


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise HC.CoopStop(code)


def _inside(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _unsafe_entry(path: Path, *, directory: bool) -> bool:
    """Symlink, reparse point, hardlink, non-regular entry."""
    try:
        info = os.lstat(path)
    except OSError:
        return True
    if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & FILE_ATTRIBUTE_REPARSE_POINT:
        return True
    if directory:
        return not stat.S_ISDIR(info.st_mode)
    return not stat.S_ISREG(info.st_mode) or info.st_nlink != 1


def _caller_path(value: Path, *, directory: bool, scratch: Path) -> Path | None:
    """One caller-named absolute path, or None when unusable (never echoed)."""
    text = str(value)
    path = Path(text)
    if not text or "\x00" in text or not path.is_absolute() or ".." in path.parts or _unsafe_entry(path, directory=directory):
        return None
    if any(_unsafe_entry(parent, directory=True) for parent in list(path.parents)[:-1] if parent.exists()):
        return None
    resolved = path.resolve()
    if os.path.normcase(str(resolved)) != os.path.normcase(os.path.abspath(text)):
        return None  # alias (8.3 name, junction or mount) rejected
    if {p.casefold() for p in resolved.parts} & SECRET_DIR_PARTS or _inside(resolved, REPO_ROOT):
        return None
    if _inside(resolved, scratch) or _inside(scratch, resolved):
        return None
    return resolved


def _grounding_files(root: Path) -> list[Path]:
    files, total = [], 0
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        for name in dirnames:
            _require(not _unsafe_entry(Path(dirpath) / name, directory=True), "GROUNDING_SCRATCH_UNSAFE")
        for name in filenames:
            path = Path(dirpath) / name
            _require(not _unsafe_entry(path, directory=False), "GROUNDING_SCRATCH_UNSAFE")
            total += path.stat().st_size
            files.append(path)
    _require(len(files) <= MAX_GROUNDING_FILES and total <= MAX_GROUNDING_BYTES, "GROUNDING_SCRATCH_TOO_LARGE")
    _require((root / "receipt.json").is_file() and (root / "frozen_case.json").is_file(), "GROUNDING_SCRATCH_INVALID")
    return files


def _read_case(path: Path | None) -> bytes:
    if path is None:
        return b""
    with open(path, "rb") as handle:
        data = handle.read(MAX_CASE_BYTES + 1)
    return data if len(data) <= MAX_CASE_BYTES else b""


def _check_scratch(scratch: Path) -> Path:
    _require(scratch.is_absolute() and not _inside(scratch.resolve(), REPO_ROOT), "SCRATCH_INSIDE_REPOSITORY")
    _require(not scratch.is_symlink() and not (scratch.exists() and _unsafe_entry(scratch, directory=True)), "SCRATCH_INVALID")
    return scratch.resolve()


def _parse_case(raw: bytes) -> dict:
    _require(0 < len(raw), "CASE_UNREADABLE")
    _require(SG.SECRET_RE.search(raw.decode("utf-8", "replace")) is None, "SECRET_MATERIAL_REJECTED")
    case = SGCLI._strict_json(raw, "CASE_JSON_INVALID")
    HC.validate_case(case)
    _require(HC.benchmark_commitment(case) == case["benchmark_sha256"], "BENCHMARK_FREEZE_MISMATCH")
    return case


def freeze(grounding_dir: Path, case_path: Path, scratch: Path) -> None:
    grounding = _caller_path(grounding_dir, directory=True, scratch=scratch)
    _require(grounding is not None, "GROUNDING_SCRATCH_UNUSABLE")
    raw = _read_case(_caller_path(case_path, directory=False, scratch=scratch))
    _parse_case(raw)
    files = _grounding_files(grounding)
    inputs = scratch / "inputs"
    inputs.mkdir(parents=True)
    for path in files:
        target = inputs / "grounding" / path.relative_to(grounding)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
        _require(path.read_bytes() == target.read_bytes(), "INPUT_CHANGED_DURING_FREEZE")
    (inputs / "case.json").write_bytes(raw)  # byte-preserved caller case


def _verify_grounding(scratch: Path) -> str:
    """Native SRC-01 cold verification of the frozen grounding copy (real call, no re-implementation)."""
    try:
        result = SGCLI.verify(scratch / "inputs" / "grounding")
    except SG.GroundingStop:
        raise HC.CoopStop("GROUNDING_RECEIPT_NOT_VERIFIED") from None
    _require(result["status"] == "VERIFIED", "GROUNDING_RECEIPT_NOT_VERIFIED")
    return result["receipt_id"]


def build(scratch: Path, timer=None) -> tuple[dict, dict]:
    inputs = scratch / "inputs"
    grounding_receipt_id = _verify_grounding(scratch)
    case = _parse_case((inputs / "case.json").read_bytes() if (inputs / "case.json").is_file() else b"")
    frozen = SGCLI._strict_json((inputs / "grounding" / "frozen_case.json").read_bytes(), "GROUNDING_SCRATCH_INVALID")
    ctx = HC.grounding_context(frozen, inputs / "grounding" / "inputs")
    file_sha256 = {p.relative_to(inputs).as_posix(): SG.sha256_hex(p.read_bytes())
                   for p in sorted(inputs.rglob("*")) if p.is_file()}
    return HC.build_core(case, ctx, code_identity(), file_sha256, grounding_receipt_id, timer=timer)


def run(grounding_dir: Path, case_path: Path, scratch_dir: Path) -> dict:
    started = time.monotonic()
    scratch = _check_scratch(Path(scratch_dir))
    if scratch.exists() and any(scratch.iterdir()):
        return _repeat(Path(grounding_dir), Path(case_path), scratch)
    with SGCLI.no_network() as attempts:
        freeze(Path(grounding_dir), Path(case_path), scratch)
        core, elapsed = build(scratch, timer=time.perf_counter_ns)
        receipt = HC.finalize(core)
    _require(not attempts, "NETWORK_ATTEMPT_BLOCKED")
    _require(time.monotonic() - started <= MAX_RUN_SECONDS, "TIME_BUDGET_EXCEEDED")
    receipt["non_identity"] = {"note": HC.NON_IDENTITY_NOTE,
                               "elapsed_ms": {k: round(v / 1e6, 3) for k, v in elapsed.items()},
                               "total_ms": round((time.monotonic() - started) * 1e3, 3)}
    with open(scratch / "receipt.json", "xb") as handle:
        handle.write(json.dumps(receipt, sort_keys=True, indent=1, ensure_ascii=False).encode("utf-8"))
    bench = core["benchmark"]
    return {"status": "RUN_COMPLETE", "receipt_id": receipt["receipt_id"], "grounding_receipt_id": core["inputs"]["grounding_receipt_id"],
            "benchmark_status": bench["status"], "denominators": bench["denominators"],
            "specialist_origin": HC.SPECIALIST_ORIGIN, "network_attempts": 0}


def _repeat(grounding_dir: Path, case_path: Path, scratch: Path) -> dict:
    """Safe repeat: identical inputs over a verified receipt return it; nothing is written."""
    _require((scratch / "receipt.json").is_file(), "SCRATCH_NOT_EMPTY")
    checked = verify(scratch)
    _require(checked["status"] == "VERIFIED", "SCRATCH_NOT_EMPTY")
    grounding = _caller_path(grounding_dir, directory=True, scratch=scratch)
    raw = _read_case(_caller_path(case_path, directory=False, scratch=scratch))
    frozen = scratch / "inputs"
    _require(grounding is not None and raw == (frozen / "case.json").read_bytes(), "SCRATCH_NOT_EMPTY")
    current = {p.relative_to(grounding).as_posix(): SG.sha256_hex(p.read_bytes()) for p in _grounding_files(grounding)}
    stored = {p.relative_to(frozen / "grounding").as_posix(): SG.sha256_hex(p.read_bytes())
              for p in (frozen / "grounding").rglob("*") if p.is_file()}
    _require(stored == current, "SCRATCH_NOT_EMPTY")
    return {"status": "IDEMPOTENT_VERIFIED", "receipt_id": checked["receipt_id"], "network_attempts": 0}


def verify(scratch_dir: Path) -> dict:
    scratch = Path(scratch_dir)
    _require(scratch.is_absolute() and scratch.is_dir() and not _inside(scratch.resolve(), REPO_ROOT), "SCRATCH_INVALID")
    scratch = scratch.resolve()
    with SGCLI.no_network() as attempts:
        receipt = SGCLI._strict_json((scratch / "receipt.json").read_bytes() if (scratch / "receipt.json").is_file() else b"",
                                     "RECEIPT_UNREADABLE")
        receipt_id = receipt.get("receipt_id") if isinstance(receipt, dict) else None
        try:
            core, _ = build(scratch)
        except SG.GroundingStop as stop:
            return {"status": "TAMPER_DETECTED", "failures": [f"RECOMPUTE_REFUSED:{stop}"], "receipt_id": receipt_id,
                    "network_attempts": 0}
        failures = HC.verify_receipt(receipt, core)
    _require(not attempts, "NETWORK_ATTEMPT_BLOCKED")
    return {"status": "VERIFIED" if not failures else "TAMPER_DETECTED", "failures": failures, "receipt_id": receipt_id,
            "network_attempts": 0}


def run_safe(args) -> dict:
    """Closed result for every outcome; refusals carry a stable code and never echo input or paths."""
    try:
        if args.command == "run":
            return run(args.grounding_scratch, args.case, args.scratch_dir)
        return verify(args.scratch_dir)
    except SG.GroundingStop as stop:
        return {"status": "STOPPED", "reason_code": str(stop)}
    except FileExistsError:
        return {"status": "STOPPED", "reason_code": "WRITE_ONCE_CONFLICT"}
    except Exception:  # noqa: BLE001 - sanitized: no exception text or path is echoed
        return {"status": "STOPPED", "reason_code": "INTERNAL_REFUSAL"}


class _Parser(argparse.ArgumentParser):
    def error(self, message):  # sanitized usage error: never echo caller arguments
        print(json.dumps({"status": "USAGE_ERROR", "reason_code": "USAGE_INVALID"}, sort_keys=True))
        raise SystemExit(2)


def main(argv: list[str] | None = None) -> int:
    parser = _Parser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True, parser_class=_Parser)
    first = sub.add_parser("run")
    for flag in ("--grounding-scratch", "--case", "--scratch-dir"):
        first.add_argument(flag, required=True, type=Path)
    sub.add_parser("verify").add_argument("--scratch-dir", required=True, type=Path)
    result = run_safe(parser.parse_args(argv))
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] in OK_STATUSES else 1


if __name__ == "__main__":
    raise SystemExit(main())
