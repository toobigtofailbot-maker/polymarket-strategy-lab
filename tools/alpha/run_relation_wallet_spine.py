"""B2 shared-PIT relation + public-wallet advisory handoff operator (S10-CAP-B2-RELATIONS-WALLET-01).

  run    --spine-scratch DIR --alpha-registry FILE --rel-scratch DIR --wallet-ledger FILE --case FILE --scratch-dir DIR
  verify --scratch-dir DIR

One finite, manual, offline pass over caller-named local copies only. Call path: freeze (hash, copy, re-hash) ->
unmodified ``run_source_forecast_spine.verify`` on the frozen B1-A scratch + registry copy -> native scout ->
unmodified ``run_related_market_alpha.verify`` -> unmodified ``run_oracle3_upstream_parity.run`` + ``.verify`` on
the frozen REL copy -> native WALLET-01/02/03 on the frozen ledger copy -> one write-once receipt. ``verify``
only reads: it cold-verifies every nested producer again and recomputes the whole core from the frozen copies.
Every socket entry point is blocked; caller stores are never written.

Exit codes: 0 RUN_COMPLETE / VERIFIED, 1 refusal or tamper, 2 usage error.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.data_layer.analytical_research import oracle3_upstream_bridge as OB  # noqa: E402
from src.data_layer.analytical_research import relation_wallet_spine as RW  # noqa: E402
from src.data_layer.analytical_research import source_grounding as SG  # noqa: E402
from tools.alpha import run_oracle3_upstream_parity as PAR  # noqa: E402
from tools.alpha import run_related_market_alpha as REL  # noqa: E402
from tools.alpha import run_source_forecast_spine as B1A  # noqa: E402
from tools.alpha import run_source_grounding as SGCLI  # noqa: E402

MAX_CASE_BYTES = 1 << 20
MAX_TOTAL_BYTES = 1 << 30
MAX_TOTAL_FILES = 8000
MAX_RECEIPT_BYTES = 16 << 20  # ids, counts and <= 200 model rows (~34 KiB observed); bounded read before parsing
SIDECARS = ("-wal", "-shm", "-journal")
OK_STATUSES = ("RUN_COMPLETE", "VERIFIED")
STOPS = (RW.RelationWalletStop, SG.GroundingStop, OB.Oracle3Stop) + B1A.STOPS
LAYOUT = {"spine": "spine", "registry": "alpha_registry.sqlite3", "rel": "rel", "ledger": "wallet_ledger.sqlite3",
          "case": "case.json", "bundle": "bundle"}


def code_identity() -> str:
    digest = hashlib.sha256()
    for path in (Path(__file__), Path(RW.__file__)):
        digest.update(path.resolve().read_bytes())
    return "code:sha256:" + digest.hexdigest()


def _sha(path: Path) -> str:
    with open(path, "rb") as handle:  # streamed, never a whole-file read
        return hashlib.file_digest(handle, "sha256").hexdigest()


def _size(path: Path, limit: int, code: str) -> int:
    """lstat only: a regular single-link file (no link, reparse point or hardlink) of at most ``limit`` bytes."""
    RW._require(not REL._unsafe_entry(path, directory=False) and os.lstat(path).st_size <= limit, code)
    return os.lstat(path).st_size


def _walk(root: Path) -> dict:
    """The root and every child by lstat: regular single-link files only; no links, reparse points, SQLite
    sidecars or secret-shaped dirs. Returns {relative path: path}; nothing is read."""
    RW._require(not REL._unsafe_entry(root, directory=True), "INPUT_TREE_UNSAFE")
    out, total = {}, 0
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        for name in dirnames:
            RW._require(not REL._unsafe_entry(Path(dirpath) / name, directory=True)
                        and name.casefold() not in REL.SECRET_DIR_PARTS, "INPUT_TREE_UNSAFE")
        for name in filenames:
            path = Path(dirpath) / name
            RW._require(not REL._unsafe_entry(path, directory=False) and not name.endswith(SIDECARS), "INPUT_TREE_UNSAFE")
            total += os.lstat(path).st_size
            RW._require(len(out) < MAX_TOTAL_FILES and total <= MAX_TOTAL_BYTES, "INPUT_TOO_LARGE")
            out[path.relative_to(root).as_posix()] = path
    return out


def _tree(root: Path) -> dict:
    return {rel: _sha(path) for rel, path in _walk(root).items()}


def _file(path: Path) -> dict:
    RW._require(not any(Path(str(path) + s).exists() for s in SIDECARS), "SQLITE_SIDECAR_PRESENT")
    RW._require(not REL._unsafe_entry(path, directory=False), "INPUT_TREE_UNSAFE")
    return {"": path}


def _sources(args: dict, scratch: Path) -> dict:
    """Caller paths -> resolved safe absolute paths (never echoed); disjoint from each other and the scratch."""
    resolved = {}
    for key, directory in (("spine", True), ("registry", False), ("rel", True), ("ledger", False), ("case", False)):
        path = REL._caller_path(str(args[key]), directory=directory, scratch=scratch)
        RW._require(path is not None, "INPUT_PATH_UNUSABLE:" + key)
        resolved[key] = path
    pairs = list(resolved.items())
    RW._require(all(ka == kb or not (REL._inside(a, b) or REL._inside(b, a)) for ka, a in pairs for kb, b in pairs),
                "INPUT_PATHS_OVERLAP")  # distinct roles are disjoint, equal paths included
    return resolved


def _member(root: Path, member: str) -> Path:
    """One retained quote member: root-relative regular single-link file (no link/junction/alias/escape), by lstat."""
    path = root / member
    chain = [root, path.parent] + [p for p in path.parent.parents if REL._inside(p, root) and p != root]
    RW._require(not any(REL._unsafe_entry(p, directory=True) for p in chain)
                and not REL._unsafe_entry(path, directory=False)
                and os.path.normcase(str(path.resolve())) == os.path.normcase(str(path))
                and 0 < os.lstat(path).st_size <= RW.MAX_MEMBER_BYTES, "QUOTE_MEMBER_UNSAFE")
    return path


def _inventory(paths: dict, member_root: Path, case: dict) -> dict:
    """Every byte the receipt depends on (trees, files, case, retained members), checked by lstat only.
    Path safety and the aggregate file/byte caps hold before any byte is hashed."""
    found = {key: _walk(paths[key]) for key in ("spine", "rel")}
    found.update({key: _file(paths[key]) for key in ("registry", "ledger")})
    _size(paths["case"], MAX_CASE_BYTES, "CASE_UNREADABLE")
    found["case"] = {"": paths["case"]}
    found["bundle"] = {m: _member(member_root, m) for m in RW.members(case)}
    entries = [path for files in found.values() for path in files.values()]
    RW._require(len(entries) <= MAX_TOTAL_FILES and sum(os.lstat(p).st_size for p in entries) <= MAX_TOTAL_BYTES,
                "INPUT_TOO_LARGE")
    return found


def _hashes(paths: dict, member_root: Path, case: dict) -> dict:
    return {key: {rel: _sha(path) for rel, path in files.items()} for key, files in _inventory(paths, member_root, case).items()}


def _snapshot(sources: dict, case: dict) -> dict:
    """Hash every caller byte the receipt depends on, after the inventory checks."""
    return _hashes(sources, sources["case"].parent, case)


def _masked(value: object) -> object:
    """Native condition ids are 0x+64 hex (key-shaped for SECRET_RE); only that closed field is masked, and
    RW.wallet later requires every such value to equal a condition of the shared PIT universe."""
    if isinstance(value, dict):
        return {k: "CONDITION" if k == "condition_value" else _masked(v) for k, v in value.items()}
    return [_masked(v) for v in value] if isinstance(value, list) else value


def parse_case(raw: bytes) -> dict:
    RW._require(0 < len(raw) <= MAX_CASE_BYTES, "CASE_UNREADABLE")
    case = SGCLI._strict_json(raw, "CASE_JSON_INVALID")
    RW._require(SG.SECRET_RE.search(json.dumps(_masked(case), ensure_ascii=False)) is None, "SECRET_MATERIAL_REJECTED")
    RW.validate_case(case)
    return case


def _freeze(sources: dict, case: dict, inputs: Path) -> None:
    inputs.mkdir(parents=True)
    for key in ("spine", "rel"):
        for rel in _tree(sources[key]):
            target = inputs / LAYOUT[key] / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(sources[key] / rel, target)
    for key in ("registry", "ledger", "case"):
        shutil.copyfile(sources[key], inputs / LAYOUT[key])
    for member in RW.members(case):
        target = inputs / LAYOUT["bundle"] / member
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(sources["case"].parent / member, target)


def _frozen_hashes(inputs: Path, case: dict) -> dict:
    """The frozen copies under the same inventory checks and caps as the caller inputs (cold verify included)."""
    RW._require(not REL._unsafe_entry(inputs, directory=True), "INPUT_TREE_UNSAFE")
    return _hashes({key: inputs / LAYOUT[key] for key in ("spine", "registry", "rel", "ledger", "case")},
                   inputs / LAYOUT["bundle"], case)


def _read_member(inputs: Path, allowed: list):
    def read(member: str) -> bytes:
        return REL._read_capped(_member(inputs / LAYOUT["bundle"], member), RW.MAX_MEMBER_BYTES) if member in allowed else b""
    return read


def _read_json(path: Path, code: str):
    """A bounded regular single-link JSON file (the derived parity receipt and the B2 receipt)."""
    raw = REL._read_capped(path, MAX_RECEIPT_BYTES) if not REL._unsafe_entry(path, directory=False) else b""
    return SGCLI._strict_json(raw, code)


def compute(scratch: Path) -> dict:
    """Everything from the frozen copies: nested native verifiers first, then the pure B2 consumers."""
    inputs = scratch / "inputs"
    RW._require(not REL._unsafe_entry(inputs, directory=True), "INPUT_TREE_UNSAFE")
    case_path = inputs / LAYOUT["case"]
    _size(case_path, MAX_CASE_BYTES, "CASE_UNREADABLE")
    raw = REL._read_capped(case_path, MAX_CASE_BYTES)
    case = parse_case(raw)
    hashes = _frozen_hashes(inputs, case)
    spine_dir, registry = inputs / LAYOUT["spine"], inputs / LAYOUT["registry"]
    checked = B1A.verify(spine_dir, registry)
    RW._require(checked["status"] == "VERIFIED" and checked["receipt_id"] == case["spine_receipt_id"], "SPINE_NOT_VERIFIED")
    spine = json.loads((spine_dir / "receipt.json").read_bytes())
    lineage = RW.b1a_lineage(spine)
    binding = RW.bind_target(spine_dir / "forecast" / "inputs" / "grounding", case["target_market_id"], lineage)
    rel_checked = REL.verify(inputs / LAYOUT["rel"])
    RW._require(rel_checked["status"] == "VERIFIED" and rel_checked["receipt_id"] == case["rel_receipt_id"], "REL_NOT_VERIFIED")
    RW._require(not REL._unsafe_entry(scratch / "parity", directory=True), "PARITY_NOT_VERIFIED")
    par_checked = PAR.verify(scratch / "parity")
    RW._require(par_checked["status"] == "VERIFIED", "PARITY_NOT_VERIFIED")
    rel = json.loads((inputs / LAYOUT["rel"] / "receipt.json").read_bytes())
    parity = _read_json(scratch / "parity" / "receipt.json", "PARITY_NOT_VERIFIED")
    RW._require(parity["receipt_id"] == par_checked["receipt_id"]
                and _tree(scratch / "parity" / "inputs" / "rel") == hashes["rel"], "PARITY_INPUT_MISMATCH")
    a5 = RW.relations(binding, rel, parity, case["model_ids"])
    a6 = RW.wallet(binding, inputs / LAYOUT["ledger"], case, _read_member(inputs, RW.members(case)), rel["core"]["inputs"]["decision_time"])
    core = RW.build_core(case_sha256=hashlib.sha256(raw).hexdigest(),
                         input_sha256={k: RW.sha_json(v) for k, v in sorted(hashes.items())},
                         code_identity=code_identity(), lineage=lineage, binding=binding, a5=a5, a6=a6)
    return {"core": core, "a5": a5["status"], "a6": a6["status"]}


def _scratch(path: Path) -> Path:
    scratch = Path(path)
    RW._require(scratch.is_absolute() and ".." not in scratch.parts and not REL._inside(scratch.resolve(), REPO_ROOT)
                and os.path.normcase(str(scratch.resolve())) == os.path.normcase(os.path.abspath(scratch))  # no alias
                and not (scratch.exists() and REL._unsafe_entry(scratch, directory=True)), "SCRATCH_INVALID")
    return scratch.resolve()


def run(spine_scratch, alpha_registry, rel_scratch, wallet_ledger, case_path, scratch_dir) -> dict:
    scratch = _scratch(scratch_dir)
    RW._require(not (scratch.exists() and any(scratch.iterdir())), "SCRATCH_NOT_EMPTY")  # write once, no hidden rerun
    with SGCLI.no_network() as attempts:
        sources = _sources({"spine": spine_scratch, "registry": alpha_registry, "rel": rel_scratch,
                            "ledger": wallet_ledger, "case": case_path}, scratch)
        case = parse_case(REL._read_capped(sources["case"], MAX_CASE_BYTES))
        before = _snapshot(sources, case)
        _freeze(sources, case, scratch / "inputs")
        RW._require(_frozen_hashes(scratch / "inputs", case) == before, "INPUT_CHANGED_DURING_FREEZE")
        produced = PAR.run(scratch / "inputs" / LAYOUT["rel"], scratch / "parity")
        RW._require(produced["status"] == "RUN_COMPLETE", "PARITY_NOT_COMPLETE")
        result = compute(scratch)
        RW._require(_snapshot(sources, case) == before, "INPUT_CHANGED_DURING_RUN")  # caller stores untouched
    RW._require(not attempts, "NETWORK_ATTEMPT_BLOCKED")
    receipt = RW.finalize(result["core"])
    with open(scratch / "receipt.json", "xb") as handle:
        handle.write(json.dumps(receipt, sort_keys=True, indent=1, ensure_ascii=False).encode("utf-8"))
    return {"status": "RUN_COMPLETE", "receipt_id": receipt["receipt_id"], "a5": result["a5"], "a6": result["a6"],
            "network_attempts": 0}


def verify(scratch_dir) -> dict:
    """Cold and read-only: nested producers re-verified, whole core recomputed and compared."""
    scratch = _scratch(scratch_dir)
    RW._require(scratch.is_dir(), "SCRATCH_INVALID")
    failures = []
    with SGCLI.no_network() as attempts:
        receipt = _read_json(scratch / "receipt.json", "RECEIPT_UNREADABLE")
        try:
            core = compute(scratch)["core"]
            if not isinstance(receipt, dict) or set(receipt) != {"schema_id", "receipt_id", "core"}:
                failures.append("RECEIPT_SHAPE_INVALID")
            elif receipt["schema_id"] != RW.RECEIPT_SCHEMA:  # outside the hashed core: checked exactly
                failures.append("RECEIPT_SCHEMA_INVALID")
            elif type(receipt["core"]) is not dict:
                failures.append("RECEIPT_FIELDS_INVALID")
            else:  # exact canonical bytes (no null/absent or bool/int/float conflation); closed codes, no caller keys
                if SG.canonical_bytes(receipt["core"]) != SG.canonical_bytes(core):
                    failures.append("CORE_MISMATCH")
                if receipt["receipt_id"] != RW.finalize(core)["receipt_id"]:
                    failures.append("RECEIPT_ID_MISMATCH")
        except STOPS as stop:
            failures.append("RECOMPUTE_REFUSED:" + str(stop).split(":")[0])
        except (KeyError, TypeError, AttributeError, OSError, ValueError):
            failures.append("RECEIPT_FIELDS_INVALID")
    RW._require(not attempts, "NETWORK_ATTEMPT_BLOCKED")
    return {"status": "VERIFIED" if not failures else "TAMPER_DETECTED", "failures": failures,
            "receipt_id": receipt.get("receipt_id") if isinstance(receipt, dict) and not failures else None,
            "network_attempts": 0}


def run_safe(args) -> dict:
    """Closed result for every outcome; never echoes input text, paths, addresses or tracebacks."""
    try:
        if args.command == "run":
            return run(args.spine_scratch, args.alpha_registry, args.rel_scratch, args.wallet_ledger, args.case, args.scratch_dir)
        return verify(args.scratch_dir)
    except STOPS as stop:
        return {"status": "STOPPED", "reason_code": str(stop)}
    except FileExistsError:
        return {"status": "STOPPED", "reason_code": "WRITE_ONCE_CONFLICT"}
    except Exception:  # noqa: BLE001 - sanitized
        return {"status": "STOPPED", "reason_code": "INTERNAL_REFUSAL"}


class _Parser(argparse.ArgumentParser):
    def error(self, message):  # never echo caller arguments
        print(json.dumps({"status": "USAGE_ERROR", "reason_code": "USAGE_INVALID"}, sort_keys=True))
        raise SystemExit(2)


def main(argv: list[str] | None = None) -> int:
    parser = _Parser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True, parser_class=_Parser)
    first = sub.add_parser("run")
    for flag in ("--spine-scratch", "--alpha-registry", "--rel-scratch", "--wallet-ledger", "--case", "--scratch-dir"):
        first.add_argument(flag, required=True, type=Path)
    sub.add_parser("verify").add_argument("--scratch-dir", required=True, type=Path)
    result = run_safe(parser.parse_args(argv))
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] in OK_STATUSES else 1


if __name__ == "__main__":
    raise SystemExit(main())
