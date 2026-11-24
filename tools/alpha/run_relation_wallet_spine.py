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
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _tree(root: Path) -> dict:
    """Regular single-link files only; no links, reparse points, SQLite sidecars or secret-shaped dirs."""
    out, total = {}, 0
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        for name in dirnames:
            RW._require(not REL._unsafe_entry(Path(dirpath) / name, directory=True)
                        and name.casefold() not in REL.SECRET_DIR_PARTS, "INPUT_TREE_UNSAFE")
        for name in filenames:
            path = Path(dirpath) / name
            RW._require(not REL._unsafe_entry(path, directory=False) and not name.endswith(SIDECARS), "INPUT_TREE_UNSAFE")
            total += path.stat().st_size
            RW._require(len(out) < MAX_TOTAL_FILES and total <= MAX_TOTAL_BYTES, "INPUT_TOO_LARGE")  # cap before hashing
            out[path.relative_to(root).as_posix()] = _sha(path)
    return out


def _file(path: Path) -> dict:
    RW._require(not any(Path(str(path) + s).exists() for s in SIDECARS), "SQLITE_SIDECAR_PRESENT")
    return {"": _sha(path)}


def _sources(args: dict, scratch: Path) -> dict:
    """Caller paths -> resolved safe absolute paths (never echoed); disjoint from each other and the scratch."""
    resolved = {}
    for key, directory in (("spine", True), ("registry", False), ("rel", True), ("ledger", False), ("case", False)):
        path = REL._caller_path(str(args[key]), directory=directory, scratch=scratch)
        RW._require(path is not None, "INPUT_PATH_UNUSABLE:" + key)
        resolved[key] = path
    paths = list(resolved.values())
    RW._require(all(a == b or not (REL._inside(a, b) or REL._inside(b, a)) for a in paths for b in paths), "INPUT_PATHS_OVERLAP")
    return resolved


def member_hashes(case_path: Path, case: dict) -> dict:
    """Retained quote bytes: case-parent relative regular single-link files only (no link/junction/alias/escape)."""
    parent, out = case_path.parent, {}
    for member in RW.members(case):
        path = parent / member
        chain = [path.parent] + [p for p in path.parent.parents if REL._inside(p, parent) and p != parent]
        RW._require(path.is_file() and not REL._unsafe_entry(path, directory=False)
                    and not any(REL._unsafe_entry(p, directory=True) for p in chain)
                    and os.path.normcase(str(path.resolve())) == os.path.normcase(str(path))
                    and 0 < path.stat().st_size <= RW.MAX_MEMBER_BYTES, "QUOTE_MEMBER_UNSAFE")
        out[member] = _sha(path)
    return out


def _snapshot(sources: dict, case: dict) -> dict:
    """Hash every caller byte the receipt depends on (trees, files, retained quote members)."""
    hashes = {key: (_tree(path) if key in ("spine", "rel") else _file(path)) for key, path in sources.items() if key != "case"}
    hashes["case"] = {"": _sha(sources["case"])}
    parent = sources["case"].parent
    bundle = hashes["bundle"] = member_hashes(sources["case"], case)
    files = sum(len(v) for v in hashes.values())
    total = sum((sources[k] / rel if rel else sources[k]).stat().st_size for k in ("spine", "rel", "registry", "ledger")
                for rel in hashes[k]) + sum((parent / m).stat().st_size for m in bundle)
    RW._require(files <= MAX_TOTAL_FILES and total <= MAX_TOTAL_BYTES, "INPUT_TOO_LARGE")
    return hashes


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
    hashes = {key: (_tree(inputs / LAYOUT[key]) if key in ("spine", "rel") else _file(inputs / LAYOUT[key]))
              for key in ("spine", "registry", "rel", "ledger", "case")}
    hashes["bundle"] = {m: _sha(inputs / LAYOUT["bundle"] / m) for m in RW.members(case)}
    return hashes


def _read_member(inputs: Path, allowed: list):
    def read(member: str) -> bytes:
        path = inputs / LAYOUT["bundle"] / member
        return path.read_bytes() if member in allowed and path.is_file() and not path.is_symlink() else b""
    return read


def compute(scratch: Path) -> dict:
    """Everything from the frozen copies: nested native verifiers first, then the pure B2 consumers."""
    inputs = scratch / "inputs"
    raw = (inputs / LAYOUT["case"]).read_bytes()
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
    par_checked = PAR.verify(scratch / "parity")
    RW._require(par_checked["status"] == "VERIFIED", "PARITY_NOT_VERIFIED")
    rel = json.loads((inputs / LAYOUT["rel"] / "receipt.json").read_bytes())
    parity = json.loads((scratch / "parity" / "receipt.json").read_bytes())
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
    RW._require(scratch.is_absolute() and not REL._inside(scratch.resolve(), REPO_ROOT) and not scratch.is_symlink()
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
        path = scratch / "receipt.json"
        receipt = SGCLI._strict_json(path.read_bytes() if path.is_file() else b"", "RECEIPT_UNREADABLE")
        try:
            core = compute(scratch)["core"]
            if not isinstance(receipt, dict) or set(receipt) != {"schema_id", "receipt_id", "core"}:
                failures.append("RECEIPT_SHAPE_INVALID")
            else:
                if receipt["receipt_id"] != RW.finalize(receipt["core"])["receipt_id"]:
                    failures.append("RECEIPT_ID_MISMATCH")
                failures.extend(f"CORE_MISMATCH:{k}" for k in sorted(set(core) | set(receipt["core"]))
                                if receipt["core"].get(k) != core.get(k))
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
