"""Finite offline source grounding + rule-aware market discovery (S10-R3-SRC-01).

  run    --case CASE.json --scratch-dir DIR   freeze the named local inputs, rank, write one receipt
  verify --scratch-dir DIR                    cold recompute from the frozen copies; fail closed

Inputs are only caller-named, already-existing local files (a native PIT record store, an
optional Alpha Factory registry, rule-text bytes and source bytes). No discovery of
environment/home paths, no download, no provider, no LLM/Hermes, no socket (a guard fails the
run if anything tries). Writes only inside the empty absolute scratch directory outside the
repository. The receipt is RESEARCH_ONLY evidence with no forecast, price, order or live authority.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import shutil
import socket
import sys
import time

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.data_layer.analytical_research import source_grounding as SG  # noqa: E402

MAX_CASE_BYTES = 1 << 20
MAX_INPUT_BYTES = 64 << 20
MAX_TEXT_INPUT_BYTES = 2 << 20


def code_identity() -> str:
    digest = hashlib.sha256()
    for path in (Path(SG.__file__), Path(__file__)):
        digest.update(path.resolve().read_bytes())
    return "code:sha256:" + digest.hexdigest()


def _inside(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


@contextmanager
def no_network():
    """Every socket entry point raises; ``attempts`` survives catch-all handlers."""
    attempts = []

    def deny(*_args, **_kwargs):
        attempts.append(1)
        raise SG.GroundingStop("NETWORK_ATTEMPT_BLOCKED")
    saved = [(owner, name, getattr(owner, name)) for owner, names in (
        (socket.socket, ("connect", "connect_ex", "sendto")),
        (socket, ("create_connection", "getaddrinfo", "gethostbyname", "gethostbyname_ex"))) for name in names]
    for owner, name, _ in saved:
        setattr(owner, name, deny)
    try:
        yield attempts
    finally:
        for owner, name, original in saved:
            setattr(owner, name, original)


def _strict_json(raw: bytes, code: str):
    def reject(_):
        raise ValueError(code)
    try:
        return json.loads(raw.decode("utf-8"), parse_constant=reject,
                          object_pairs_hook=lambda pairs: dict(pairs) if len({k for k, _ in pairs}) == len(pairs) else reject(None))
    except (UnicodeDecodeError, ValueError, RecursionError):
        raise SG.GroundingStop(code) from None


def _input_file(value: object, scratch: Path, limit: int) -> Path | None:
    """Caller path for one input; None means 'not usable' (counted per item by the core)."""
    if type(value) is not str:
        return None
    path = Path(value)
    if not path.is_absolute() or not path.is_file() or path.is_symlink():
        return None
    resolved = path.resolve()
    if _inside(resolved, REPO_ROOT) or _inside(resolved, scratch) or resolved.stat().st_size > limit:
        return None
    return resolved


def freeze(case_path: Path, scratch: Path) -> dict:
    scratch = Path(scratch)
    SG._require(scratch.is_absolute() and not _inside(scratch.resolve(), REPO_ROOT), "SCRATCH_INSIDE_REPOSITORY")
    SG._require(not scratch.is_symlink() and (not scratch.exists() or (scratch.is_dir() and not any(scratch.iterdir()))),
                "SCRATCH_NOT_EMPTY")
    scratch = scratch.resolve()
    case_path = Path(case_path)
    raw = case_path.read_bytes() if case_path.is_file() and not case_path.is_symlink() else b""
    SG._require(0 < len(raw) <= MAX_CASE_BYTES, "CASE_UNREADABLE")
    SG._require(SG.SECRET_RE.search(raw.decode("utf-8", "replace")) is None, "SECRET_MATERIAL_REJECTED")
    case = _strict_json(raw, "CASE_JSON_INVALID")
    SG.validate_case(case, frozen=False)
    stores = {}
    for role, name in (("pit_store", "pit.sqlite3"), ("alpha_registry", "alpha.sqlite3")):
        if case[role] is None:
            continue
        path = _input_file(case[role], scratch, MAX_INPUT_BYTES)
        SG._require(path is not None, f"{role.upper()}_UNUSABLE")
        SG._require(not any(Path(str(path) + s).exists() for s in ("-wal", "-shm", "-journal")), "STORE_SIDECAR_PRESENT")
        stores[name] = path
    SG._require(len(set(stores.values())) == len(stores), "STORE_PATH_DUPLICATE")
    inputs = scratch / "inputs"
    (inputs / "rules").mkdir(parents=True)
    (inputs / "sources").mkdir()
    copies = {}
    for name, path in stores.items():
        shutil.copyfile(path, inputs / name)
        copies[name] = path
    frozen = dict(case, pit_store="pit.sqlite3", alpha_registry="alpha.sqlite3" if case["alpha_registry"] else None)
    for group, folder in (("rule_texts", "rules"), ("sources", "sources")):
        items = []
        for number, item in enumerate(case[group]):
            rel = f"{folder}/{number:03d}.bin"
            path = _input_file(item.get("file") if isinstance(item, dict) else None, scratch, MAX_TEXT_INPUT_BYTES)
            # An unusable path freezes as an empty file so the core counts it per item, never silently drops it.
            (inputs / rel).write_bytes(path.read_bytes() if path else b"")
            items.append(dict(item, file=rel) if isinstance(item, dict) else {"file": rel, "invalid_entry": True})
        frozen[group] = items
    for name, path in copies.items():
        SG._require(hashlib.sha256(path.read_bytes()).digest() == hashlib.sha256((inputs / name).read_bytes()).digest(),
                    "INPUT_CHANGED_DURING_FREEZE")
    (scratch / "frozen_case.json").write_bytes(SG.canonical_bytes(frozen))
    return frozen


def run(case_path: Path, scratch_dir: Path) -> dict:
    with no_network() as attempts:
        frozen = freeze(case_path, scratch_dir)
        scratch = Path(scratch_dir).resolve()
        started = time.perf_counter_ns()
        core, elapsed = SG.build_grounding_core(frozen, scratch / "inputs", code_identity(), timer=time.perf_counter_ns)
        receipt = SG.finalize_receipt(core)
    SG._require(not attempts, "NETWORK_ATTEMPT_BLOCKED")
    receipt["non_identity"] = {"note": "timings are excluded from receipt identity",
                               "elapsed_ms": {k: round(v / 1e6, 3) for k, v in elapsed.items()},
                               "total_ms": round((time.perf_counter_ns() - started) / 1e6, 3)}
    with open(scratch / "receipt.json", "xb") as handle:
        handle.write(json.dumps(receipt, sort_keys=True, indent=1, ensure_ascii=False).encode("utf-8"))
    return {"status": "RUN_COMPLETE", "receipt_id": receipt["receipt_id"],
            "benchmark_status": core["benchmark"]["status"], "denominators": core["benchmark"]["denominators"],
            "network_attempts": 0}


def verify(scratch_dir: Path) -> dict:
    scratch = Path(scratch_dir)
    SG._require(scratch.is_absolute() and scratch.is_dir() and not _inside(scratch.resolve(), REPO_ROOT), "SCRATCH_INVALID")
    scratch = scratch.resolve()
    with no_network() as attempts:
        receipt = _strict_json((scratch / "receipt.json").read_bytes() if (scratch / "receipt.json").is_file() else b"",
                               "RECEIPT_UNREADABLE")
        frozen = _strict_json((scratch / "frozen_case.json").read_bytes() if (scratch / "frozen_case.json").is_file() else b"",
                              "FROZEN_CASE_UNREADABLE")
        core, _ = SG.build_grounding_core(frozen, scratch / "inputs", code_identity())
        failures = SG.verify_receipt(receipt, core)
    SG._require(not attempts, "NETWORK_ATTEMPT_BLOCKED")
    inputs = receipt["core"].get("inputs") if isinstance(receipt, dict) and isinstance(receipt.get("core"), dict) else None
    if not isinstance(inputs, dict) or inputs.get("file_sha256") != core["inputs"]["file_sha256"]:
        failures.insert(0, "INPUT_BYTES_TAMPERED")
    return {"status": "VERIFIED" if not failures else "TAMPER_DETECTED", "failures": failures,
            "receipt_id": receipt.get("receipt_id") if isinstance(receipt, dict) else None, "network_attempts": 0}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    first = sub.add_parser("run")
    first.add_argument("--case", required=True, type=Path)
    first.add_argument("--scratch-dir", required=True, type=Path)
    sub.add_parser("verify").add_argument("--scratch-dir", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        result = run(args.case, args.scratch_dir) if args.command == "run" else verify(args.scratch_dir)
    except SG.GroundingStop as stop:
        result = {"status": "STOPPED", "reason_code": str(stop)}
    except FileExistsError:
        result = {"status": "STOPPED", "reason_code": "WRITE_ONCE_CONFLICT"}
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] in ("RUN_COMPLETE", "VERIFIED") else 1


if __name__ == "__main__":
    raise SystemExit(main())
