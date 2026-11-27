"""B3 shared-PIT A7 execution-economics diagnostic operator (S10-CAP-EXEC-ECONOMICS-01).

  run    --b2-scratch DIR --case FILE [--replay-file FILE] --scratch-dir DIR
  verify --scratch-dir DIR

One finite, manual, offline pass over caller-named local copies only. Every entry (run and verify) first checks the
closed scratch layout (inputs/{b2/,case.json[,replay.parquet]} [+ receipt.json once sealed]; anything else refuses),
then lstat caps and the replay Parquet footer bounds, and only then hashes a byte; the same layout and digests are
re-checked after the native calls. Call path: freeze (bounds, hash, copy, re-hash) -> unmodified ``run_relation_wallet_spine.verify`` on the frozen B2 copy -> exact admitted target leg ->
native REL ``_venue_snapshots`` over the frozen REL bytes -> native ``assess_execution_feasibility`` -> optional native
WP167/168/172 replay diagnostic + WP173 refusal -> one write-once ``b3research:sha256:`` receipt. ``verify`` only
reads: it cold-verifies B2 again and recomputes the whole core from the frozen copies. Every socket entry point is
blocked; caller files are never written.

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

from src.data_layer.analytical_research import execution_economics_spine as XE  # noqa: E402
from src.data_layer.analytical_research import relation_wallet_spine as RW  # noqa: E402
from src.data_layer.analytical_research import source_grounding as SG  # noqa: E402
from tools.alpha import run_related_market_alpha as REL  # noqa: E402
from tools.alpha import run_relation_wallet_spine as B2  # noqa: E402
from tools.alpha import run_source_grounding as SGCLI  # noqa: E402

MAX_CASE_BYTES = 1 << 20
MAX_TOTAL_BYTES = 3 << 30
MAX_TOTAL_FILES = 20000
MAX_RECEIPT_BYTES = 16 << 20
MAX_PARQUET_BYTES = 16 << 20
MAX_PARQUET_UNCOMPRESSED = 64 << 20
OK_STATUSES = ("RUN_COMPLETE", "VERIFIED")
STOPS = (XE.ExecutionEconomicsStop,) + B2.STOPS
LAYOUT = {"b2": "b2", "case": "case.json", "replay": "replay.parquet"}


def code_identity() -> str:
    digest = hashlib.sha256()
    for path in (Path(__file__), Path(XE.__file__)):
        digest.update(path.resolve().read_bytes())
    return "code:sha256:" + digest.hexdigest()


def _walk(root: Path) -> dict:
    """B2's lstat-only walk (links, reparse points, hardlinks, sidecars, secret dirs refused) under B3 caps."""
    XE._require(not REL._unsafe_entry(root, directory=True), "INPUT_TREE_UNSAFE")
    out, total = {}, 0
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        for name in dirnames:
            XE._require(not REL._unsafe_entry(Path(dirpath) / name, directory=True)
                        and name.casefold() not in REL.SECRET_DIR_PARTS, "INPUT_TREE_UNSAFE")
        for name in filenames:
            path = Path(dirpath) / name
            XE._require(not REL._unsafe_entry(path, directory=False) and not name.endswith(B2.SIDECARS), "INPUT_TREE_UNSAFE")
            total += os.lstat(path).st_size
            XE._require(len(out) < MAX_TOTAL_FILES and total <= MAX_TOTAL_BYTES, "INPUT_TOO_LARGE")
            out[path.relative_to(root).as_posix()] = path
    return out


def _file(path: Path, limit: int, code: str) -> dict:
    XE._require(not REL._unsafe_entry(path, directory=False) and 0 < os.lstat(path).st_size <= limit, code)
    return {"": path}


def _inventory(paths: dict) -> dict:
    """Path safety and every cap by lstat before any byte is hashed."""
    found = {"b2": _walk(paths["b2"]), "case": _file(paths["case"], MAX_CASE_BYTES, "CASE_UNREADABLE")}
    if "replay" in paths:
        found["replay"] = _file(paths["replay"], MAX_PARQUET_BYTES, "REPLAY_FILE_UNUSABLE")
    entries = [p for files in found.values() for p in files.values()]
    XE._require(len(entries) <= MAX_TOTAL_FILES and sum(os.lstat(p).st_size for p in entries) <= MAX_TOTAL_BYTES,
                "INPUT_TOO_LARGE")
    return found


def _hashes(paths: dict) -> dict:
    """lstat inventory, then the replay footer bounds, and only then any byte hash."""
    found = _inventory(paths)
    if "replay" in found:
        _parquet_bounds(paths["replay"])
    return {key: {rel: B2._sha(path) for rel, path in files.items()} for key, files in found.items()}


def _scratch(path) -> Path:
    """B2's scratch guard plus REL's caller-path principles: no secret-named part, no unsafe existing parent."""
    scratch = B2._scratch(path)
    XE._require(not {p.casefold() for p in scratch.parts} & REL.SECRET_DIR_PARTS
                and not any(REL._unsafe_entry(p, directory=True) for p in list(scratch.parents)[:-1] if p.exists()),
                "SCRATCH_INVALID")
    return scratch


def _entries(directory: Path, required: dict, optional: dict) -> None:
    """Exactly the named members (name -> is_dir), each a safe regular file or directory by lstat; nothing else."""
    XE._require(not REL._unsafe_entry(directory, directory=True), "SCRATCH_LAYOUT_INVALID")
    names = {entry.name for entry in os.scandir(directory)}
    allowed = {**required, **optional}
    XE._require(set(required) <= names <= set(allowed), "SCRATCH_LAYOUT_INVALID")
    XE._require(not any(REL._unsafe_entry(directory / name, directory=allowed[name]) for name in names),
                "SCRATCH_LAYOUT_INVALID")


def _layout(scratch: Path, sealed: bool) -> Path:
    """Closed scratch layout: inputs/ (+ receipt.json once sealed); inputs/ = b2/, case.json, optional replay.parquet."""
    _entries(scratch, {"inputs": True, **({"receipt.json": False} if sealed else {})}, {})
    inputs = scratch / "inputs"
    _entries(inputs, {LAYOUT["b2"]: True, LAYOUT["case"]: False}, {LAYOUT["replay"]: False})
    return inputs


def _sources(b2_scratch, case_path, replay_file, scratch: Path) -> dict:
    """Caller paths -> resolved safe absolute paths (never echoed); disjoint from each other and the scratch."""
    resolved = {}
    for key, value, directory in (("b2", b2_scratch, True), ("case", case_path, False), ("replay", replay_file, False)):
        if key == "replay" and value is None:
            continue
        path = REL._caller_path(str(value), directory=directory, scratch=scratch)
        XE._require(path is not None, "INPUT_PATH_UNUSABLE:" + key)
        resolved[key] = path
    pairs = list(resolved.items())
    XE._require(all(ka == kb or not (REL._inside(a, b) or REL._inside(b, a)) for ka, a in pairs for kb, b in pairs),
                "INPUT_PATHS_OVERLAP")
    return resolved


def _masked(value: object) -> object:
    """Native condition ids are 0x+64 hex (key-shaped for SECRET_RE); only those closed fields are masked, and each
    must later equal the condition of the exact B2/REL snapshot."""
    if isinstance(value, dict):
        return {k: "CONDITION" if k == "condition_id" else _masked(v) for k, v in value.items()}
    return [_masked(v) for v in value] if isinstance(value, list) else value


def parse_case(raw: bytes) -> dict:
    XE._require(0 < len(raw) <= MAX_CASE_BYTES, "CASE_UNREADABLE")
    case = SGCLI._strict_json(raw, "CASE_JSON_INVALID")
    XE._require(SG.SECRET_RE.search(json.dumps(_masked(case), ensure_ascii=False)) is None, "SECRET_MATERIAL_REJECTED")
    XE.validate_case(case)
    return case


def _parquet_bounds(path: Path) -> None:
    """Footer-declared rows and uncompressed bytes, before any input hash, nested verifier or native WP167 parse."""
    import pyarrow.parquet as pq  # lazy: only a supplied replay needs it
    try:
        meta = pq.ParquetFile(path).metadata
        rows = meta.num_rows
        declared = sum(meta.row_group(i).total_byte_size for i in range(meta.num_row_groups))
    except Exception:  # noqa: BLE001 - unreadable footer is a closed refusal
        raise XE.ExecutionEconomicsStop("REPLAY_FILE_UNUSABLE") from None
    XE._require(0 < rows <= XE.MAX_REPLAY_ROWS, "REPLAY_ROWS_OUT_OF_BOUNDS")
    XE._require(declared <= MAX_PARQUET_UNCOMPRESSED, "REPLAY_UNCOMPRESSED_TOO_LARGE")


def _freeze(sources: dict, inputs: Path) -> None:
    inputs.mkdir(parents=True)
    for rel in _walk(sources["b2"]):
        target = inputs / LAYOUT["b2"] / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(sources["b2"] / rel, target)
    for key in ("case", "replay"):
        if key in sources:
            shutil.copyfile(sources[key], inputs / LAYOUT[key])


def _frozen(inputs: Path, case: dict) -> dict:
    paths = {key: inputs / LAYOUT[key] for key in ("b2", "case")}
    replay = inputs / LAYOUT["replay"]
    XE._require((case["replay"] is None) != (replay.exists() or replay.is_symlink()), "REPLAY_FILE_CASE_MISMATCH")
    if case["replay"] is not None:
        paths["replay"] = replay
    return paths


def _read_member(root: Path, member: str) -> bytes:
    path = root / member
    return REL._read_capped(path, REL.MAX_VENUE_BYTES) if not REL._unsafe_entry(path, directory=False) else b""


def _case(path: Path) -> tuple:
    """Bounded strict case read; the parsed bytes are returned so they can be bound to the input digest."""
    _file(path, MAX_CASE_BYTES, "CASE_UNREADABLE")
    raw = REL._read_capped(path, MAX_CASE_BYTES)
    return parse_case(raw), hashlib.sha256(raw).hexdigest()


def compute(scratch: Path, sealed: bool = False) -> dict:
    """Everything from the frozen copies: exact layout, every bound, then hashes, B2 cold verify, the pure B3
    consumers, and the same layout + digests again after every native call."""
    inputs = _layout(scratch, sealed)
    case, case_digest = _case(inputs / LAYOUT["case"])
    paths = _frozen(inputs, case)
    hashes = _hashes(paths)
    XE._require(hashes["case"][""] == case_digest, "FROZEN_INPUT_CHANGED")  # the parsed bytes are the sealed bytes
    b2_dir = paths["b2"]
    checked = B2.verify(b2_dir)
    XE._require(checked["status"] == "VERIFIED" and checked["receipt_id"] == case["b2_receipt_id"], "B2_NOT_VERIFIED")
    b2_core = B2._read_json(b2_dir / "receipt.json", "B2_NOT_VERIFIED")["core"]
    selected = XE.select_leg(b2_core, case)
    bound = XE.bind_snapshot(b2_dir / "inputs" / B2.LAYOUT["rel"], b2_core, selected,
                             lambda p: B2._read_json(p, "REL_RECEIPT_UNREADABLE"), _read_member)
    intent, _, point = XE.assess_point(case, bound["snapshot"], bound["decision_ns"])
    if case["replay"] is None:
        replay = XE.not_supplied()
    else:
        replay = XE.replay_diagnostic(case["replay"], paths["replay"], bound, intent, selected["target"]["market_id"])
    _layout(scratch, sealed)  # before/after frozen witness: no native call added, removed or changed a member
    XE._require(_hashes(_frozen(inputs, case)) == hashes, "FROZEN_INPUT_CHANGED")
    core = XE.build_core(code_identity=code_identity(),
                         input_sha256={k: RW.sha_json(v) for k, v in sorted(hashes.items())},
                         lineage=XE.b2_lineage(case["b2_receipt_id"], b2_core, selected, bound), point=point,
                         replay=replay, role=XE.a7_role(point, replay, selected),
                         ledger=XE.capability_ledger(b2_core, point, replay))
    return {"core": core, "a7": core["a7_role"]["overall"], "point": point["status"], "replay": replay["status"]}


def run(b2_scratch, case_path, replay_file, scratch_dir) -> dict:
    scratch = _scratch(scratch_dir)
    XE._require(not (scratch.exists() and any(scratch.iterdir())), "SCRATCH_NOT_EMPTY")  # write once, no hidden rerun
    with SGCLI.no_network() as attempts:
        sources = _sources(b2_scratch, case_path, replay_file, scratch)
        case, case_digest = _case(sources["case"])
        XE._require((case["replay"] is None) == ("replay" not in sources), "REPLAY_FILE_CASE_MISMATCH")
        before = _hashes(sources)
        XE._require(before["case"][""] == case_digest, "INPUT_CHANGED_DURING_RUN")
        _freeze(sources, scratch / "inputs")
        _layout(scratch, sealed=False)
        XE._require(_hashes(_frozen(scratch / "inputs", case)) == before, "INPUT_CHANGED_DURING_FREEZE")
        result = compute(scratch)
        XE._require(_hashes(sources) == before, "INPUT_CHANGED_DURING_RUN")  # caller files untouched
    XE._require(not attempts, "NETWORK_ATTEMPT_BLOCKED")
    receipt = XE.finalize(result["core"])
    data = json.dumps(receipt, sort_keys=True, indent=1, ensure_ascii=False).encode("utf-8")
    XE._require(len(data) <= MAX_RECEIPT_BYTES, "RECEIPT_TOO_LARGE")  # stop before writing, never a truncated seal
    with open(scratch / "receipt.json", "xb") as handle:
        handle.write(data)
    return {"status": "RUN_COMPLETE", "receipt_id": receipt["receipt_id"], "a7": result["a7"], "point": result["point"],
            "replay": result["replay"], "network_attempts": 0}


def verify(scratch_dir) -> dict:
    """Cold and read-only: B2 re-verified, whole core recomputed and compared byte for byte."""
    scratch = _scratch(scratch_dir)
    XE._require(scratch.is_dir(), "SCRATCH_INVALID")
    failures = []
    with SGCLI.no_network() as attempts:
        _layout(scratch, sealed=True)  # exact sealed layout before any read, hash or native verifier
        raw = REL._read_capped(scratch / "receipt.json", MAX_RECEIPT_BYTES)
        receipt = SGCLI._strict_json(raw, "RECEIPT_UNREADABLE")
        try:
            core = compute(scratch, sealed=True)["core"]
            XE._require(REL._read_capped(scratch / "receipt.json", MAX_RECEIPT_BYTES) == raw, "RECEIPT_CHANGED")
            if not isinstance(receipt, dict) or set(receipt) != {"schema_id", "receipt_id", "core"}:
                failures.append("RECEIPT_SHAPE_INVALID")
            elif receipt["schema_id"] != XE.RECEIPT_SCHEMA:
                failures.append("RECEIPT_SCHEMA_INVALID")
            elif type(receipt["core"]) is not dict:
                failures.append("RECEIPT_FIELDS_INVALID")
            else:  # exact canonical bytes; the id is recomputed from the recomputed core
                if SG.canonical_bytes(receipt["core"]) != SG.canonical_bytes(core):
                    failures.append("CORE_MISMATCH")
                if receipt["receipt_id"] != XE.finalize(core)["receipt_id"]:
                    failures.append("RECEIPT_ID_MISMATCH")
        except STOPS as stop:
            failures.append("RECOMPUTE_REFUSED:" + str(stop).split(":")[0])
        except (KeyError, TypeError, AttributeError, OSError, ValueError):
            failures.append("RECEIPT_FIELDS_INVALID")
    XE._require(not attempts, "NETWORK_ATTEMPT_BLOCKED")
    return {"status": "VERIFIED" if not failures else "TAMPER_DETECTED", "failures": failures,
            "receipt_id": receipt.get("receipt_id") if isinstance(receipt, dict) and not failures else None,
            "network_attempts": 0}


def run_safe(args) -> dict:
    """Closed result for every outcome; never echoes input text, paths, ids or tracebacks."""
    try:
        if args.command == "run":
            return run(args.b2_scratch, args.case, args.replay_file, args.scratch_dir)
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
    for flag in ("--b2-scratch", "--case", "--scratch-dir"):
        first.add_argument(flag, required=True, type=Path)
    first.add_argument("--replay-file", type=Path, default=None)
    sub.add_parser("verify").add_argument("--scratch-dir", required=True, type=Path)
    result = run_safe(parser.parse_args(argv))
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] in OK_STATUSES else 1


if __name__ == "__main__":
    raise SystemExit(main())
