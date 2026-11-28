"""B4 finite conditional nine-role native receipt coordinator operator (S10-CAP-NINE-ROLE-COORD-01).

  run    --manifest FILE --evidence-root DIR --scratch-dir DIR
  resume --scratch-dir DIR
  verify --scratch-dir DIR

One finite, manual, offline campaign over one or two caller-named sealed native trees (evidence-root/case-01
[/case-02], each an exact B2 or B3 scratch). Every entry first checks the closed layouts and lstat caps (and a B3
replay Parquet footer) before hashing a byte. ``run`` freezes inputs/manifest.json + inputs/case-NN, writes a
write-once plan.json, then per case: durable CASE_VERIFY_STARTED -> one unmodified ``run_relation_wallet_spine
.verify`` or ``run_execution_economics_spine.verify`` -> terminal; per role A1..A9: SKIPPED, or durable ROLE_STARTED
-> one typed read-side consumer -> terminal. Each event is an exclusive, fsynced, hash-chained journal file written
BEFORE the call it announces. ``resume`` never repeats an uncertain attempt: an in-flight subject is QUARANTINED and
the campaign continues; a sealed scratch is only verified. ``verify`` is read-only and recomputes everything.
A single-writer ``active.lock`` is never stolen. Every socket entry point is blocked; caller files are never written.

Exit codes: 0 RUN_COMPLETE / RESUMED_COMPLETE / SEALED_VERIFIED / VERIFIED, 1 refusal or tamper, 2 usage error.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.data_layer.analytical_research import nine_role_coordination as NR  # noqa: E402
from src.data_layer.analytical_research import relation_wallet_spine as RW  # noqa: E402
from src.data_layer.analytical_research import source_grounding as SG  # noqa: E402
from tools.alpha import run_execution_economics_spine as B3  # noqa: E402
from tools.alpha import run_related_market_alpha as REL  # noqa: E402
from tools.alpha import run_relation_wallet_spine as B2  # noqa: E402
from tools.alpha import run_source_grounding as SGCLI  # noqa: E402

MAX_MANIFEST_BYTES = 1 << 20
MAX_PLAN_BYTES = 1 << 20
MAX_EVENT_BYTES = 64 << 10
MAX_RECEIPT_BYTES = 16 << 20
MAX_NATIVE_RECEIPT_BYTES = 16 << 20
MAX_TOTAL_BYTES = 6 << 30  # per case: B3's 3 GiB / 20000 files (its own _walk)
MAX_TOTAL_FILES = 40000
OK_STATUSES = ("RUN_COMPLETE", "RESUMED_COMPLETE", "SEALED_VERIFIED", "VERIFIED")
STOPS = (NR.CoordinationStop,) + B3.STOPS
LOCK = "active.lock"
EVENT_RE = re.compile(r"[0-9]{6}\.json")
CASE_TOP = {"B2": {"inputs": True, "parity": True, "receipt.json": False}, "B3": {"inputs": True, "receipt.json": False}}


def code_identity() -> str:
    digest = hashlib.sha256()
    for path in (Path(__file__), Path(NR.__file__)):
        digest.update(path.resolve().read_bytes())
    return "code:sha256:" + digest.hexdigest()


# ------------------------------------------------------------------ R009 layouts, caps, inventory (before any hash)


def _entries(directory: Path, required: dict, optional: dict, code: str) -> set:
    """Exactly the named members (name -> is_dir), each a safe regular file or directory by lstat; nothing else."""
    NR._require(not REL._unsafe_entry(directory, directory=True), code)
    names = {entry.name for entry in os.scandir(directory)}
    allowed = {**required, **optional}
    NR._require(set(required) <= names <= set(allowed), code)
    NR._require(not any(REL._unsafe_entry(directory / n, directory=allowed[n]) for n in names), code)
    return names


def _cases_layout(root: Path, manifest: dict, extra: dict | None = None) -> None:
    """root holds exactly case-01[/case-02] (+ ``extra``); each case has the exact top level of its native kind."""
    _entries(root, {**{slot: True for slot in NR.slots(manifest)}, **(extra or {})}, {}, "CASE_LAYOUT_INVALID")
    for slot, case in zip(NR.slots(manifest), manifest["cases"]):
        _entries(root / slot, CASE_TOP[case["source_kind"]], {}, "CASE_LAYOUT_INVALID")


def _inventory(root: Path, manifest: dict) -> tuple[dict, dict]:
    """lstat walk + caps for every case, then the B3 replay footer bounds, and only then the byte hashes."""
    walks = {slot: B3._walk(root / slot) for slot in NR.slots(manifest)}
    entries = [p for files in walks.values() for p in files.values()]
    NR._require(len(entries) <= MAX_TOTAL_FILES and sum(os.lstat(p).st_size for p in entries) <= MAX_TOTAL_BYTES,
                "INPUT_TOO_LARGE")
    for slot, case in zip(NR.slots(manifest), manifest["cases"]):
        if case["source_kind"] == "B3" and "inputs/replay.parquet" in walks[slot]:
            B3._parquet_bounds(walks[slot]["inputs/replay.parquet"])
    hashes = {slot: {rel: B2._sha(path) for rel, path in sorted(files.items())} for slot, files in walks.items()}
    summary = {slot: {"files": len(walks[slot]), "bytes": sum(os.lstat(p).st_size for p in walks[slot].values()),
                      "sha256": RW.sha_json(hashes[slot])} for slot in walks}
    return summary, hashes


def _bound(summary: dict, raw: bytes) -> dict:
    """The plan binds the exact frozen manifest bytes, not only their parse."""
    return dict(summary, **{"manifest.json": {"sha256": hashlib.sha256(raw).hexdigest()}})


def parse_manifest(raw: bytes) -> dict:
    NR._require(0 < len(raw) <= MAX_MANIFEST_BYTES, "MANIFEST_UNREADABLE")
    manifest = SGCLI._strict_json(raw, "MANIFEST_JSON_INVALID")
    NR._require(SG.SECRET_RE.search(raw.decode("utf-8", "replace")) is None, "SECRET_MATERIAL_REJECTED")
    NR.validate_manifest(manifest)
    return manifest


def _read(path: Path, limit: int, code: str) -> bytes:
    NR._require(not REL._unsafe_entry(path, directory=False) and 0 < os.lstat(path).st_size <= limit, code)
    raw = REL._read_capped(path, limit)
    NR._require(bool(raw), code)
    return raw


def _layout(scratch: Path, *, sealed: bool, lock: bool) -> set:
    required = {"inputs": True, "plan.json": False, "journal": True, **({"receipt.json": False} if sealed else {})}
    names = _entries(scratch, required, {LOCK: False} if lock else {}, "SCRATCH_LAYOUT_INVALID")
    journal = scratch / "journal"
    for entry in os.scandir(journal):
        NR._require(EVENT_RE.fullmatch(entry.name) is not None
                    and not REL._unsafe_entry(journal / entry.name, directory=False), "SCRATCH_LAYOUT_INVALID")
    return names


def _load(scratch: Path) -> tuple[dict, list, dict]:
    """Frozen manifest + inventory -> recomputed plan (byte-exact), then the strict journal; nothing is written."""
    inputs = scratch / "inputs"
    raw = _read(inputs / "manifest.json", MAX_MANIFEST_BYTES, "MANIFEST_UNREADABLE")
    manifest = parse_manifest(raw)
    _cases_layout(inputs, manifest, {"manifest.json": False})
    summary, hashes = _inventory(inputs, manifest)
    plan_doc = NR.build_plan(manifest, _bound(summary, raw))
    NR._require(_read(scratch / "plan.json", MAX_PLAN_BYTES, "PLAN_UNREADABLE") == SG.canonical_bytes(plan_doc),
                "PLAN_MISMATCH")
    names = sorted(e.name for e in os.scandir(scratch / "journal"))
    NR._require(len(names) <= NR.MAX_EVENTS and names == ["%06d.json" % (i + 1) for i in range(len(names))],
                "JOURNAL_SEQUENCE_INVALID")
    events = []
    for name in names:
        raw = _read(scratch / "journal" / name, MAX_EVENT_BYTES, "JOURNAL_EVENT_INVALID")
        doc = SGCLI._strict_json(raw, "JOURNAL_EVENT_INVALID") if raw else None
        NR._require(SG.canonical_bytes(doc) == raw, "JOURNAL_EVENT_INVALID")  # exact canonical bytes, nothing torn
        events.append(doc)
    NR.replay(plan_doc, events)
    return plan_doc, events, hashes


# ------------------------------------------------------------------ R005 durable single writer + journal


def _fsync_dir(path: Path) -> None:
    if os.name != "nt":  # Windows cannot open a directory handle for fsync
        fd = os.open(path, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)


def _write_new(path: Path, data: bytes) -> None:
    """Exclusive create, write, flush and fsync before returning: the record is durable before the next call."""
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0), 0o600)
    try:
        view = memoryview(data)
        while view:  # os.write may write fewer bytes than asked
            view = view[os.write(fd, view):]
        os.fsync(fd)
    finally:
        os.close(fd)
    _fsync_dir(path.parent)


@contextmanager
def _writer(scratch: Path):
    """The one writer: O_EXCL lock; released only by its owner on clean unwinding. Never stolen or aged out."""
    path = scratch / LOCK
    try:
        _write_new(path, SG.canonical_bytes({"schema_id": "b4-nine-role-lock-v1", "wp_id": NR.WP_ID}))
    except FileExistsError:
        raise NR.CoordinationStop("WRITER_LOCK_PRESENT") from None
    try:
        yield
    finally:
        os.unlink(path)


def _append(scratch: Path, plan_doc: dict, events: list, kind: str, payload: dict) -> dict:
    prev = events[-1]["event_id"] if events else plan_doc["plan_id"]
    doc = NR.make_event(len(events) + 1, prev, kind, payload)
    state = NR.replay(plan_doc, events + [doc])  # only a legal next event is ever written
    data = SG.canonical_bytes(doc)
    NR._require(len(data) <= MAX_EVENT_BYTES, "JOURNAL_EVENT_TOO_LARGE")
    _write_new(scratch / "journal" / ("%06d.json" % doc["event"]["seq"]), data)
    events.append(doc)
    return state


# ------------------------------------------------------------------ R001/R003 one native verify per case attempt


def _receipt(path: Path) -> dict:
    return SGCLI._strict_json(_read(path, MAX_NATIVE_RECEIPT_BYTES, "NATIVE_RECEIPT_UNREADABLE"), "NATIVE_RECEIPT_UNREADABLE")


def native_view(scratch: Path, case: dict) -> dict:
    """The unmodified top-level native verifier on the frozen copy (it re-verifies its own nested producers), then
    bounded reads of the receipts it just verified. Nothing is accepted on a matching hash alone."""
    root = scratch / "inputs" / case["slot"]
    checked = B2.verify(root) if case["source_kind"] == "B2" else B3.verify(root)
    NR._require(checked["status"] == "VERIFIED", "NATIVE_VERIFY_REFUSED")
    NR._require(checked["receipt_id"] == case["receipt_id"], "RECEIPT_ID_MISMATCH")
    b2_dir = root if case["source_kind"] == "B2" else root / "inputs" / B3.LAYOUT["b2"]
    top = _receipt(root / "receipt.json")
    NR._require(top.get("receipt_id") == case["receipt_id"], "RECEIPT_ID_MISMATCH")
    spine_dir = b2_dir / "inputs" / B2.LAYOUT["spine"]
    return {"source_kind": case["source_kind"], "receipt_id": case["receipt_id"],
            "b2": top if case["source_kind"] == "B2" else _receipt(b2_dir / "receipt.json"),
            "spine": _receipt(spine_dir / "receipt.json"), "w01": _receipt(spine_dir / "w01" / "receipt.json"),
            "b3": top if case["source_kind"] == "B3" else None}


def _lineage(view: dict) -> dict:
    try:
        return NR.case_lineage(view)
    except (KeyError, TypeError, AttributeError, IndexError):
        raise NR.CoordinationStop("NESTED_FIELD_SHAPE_INVALID") from None


def _deps(plan_case: dict, role: str, projections: dict) -> dict:
    return {p: projections[(plan_case["slot"], p)] for p in NR.PREREQUISITES[role]}


def _drive(scratch: Path, plan_doc: dict, events: list, attempts: list) -> dict:
    """Fixed bounded loop to the end of the plan; at most one logical attempt per case verify and per role."""
    state = NR.replay(plan_doc, events)
    if state["in_flight"] is not None:
        state = _append(scratch, plan_doc, events, *NR.quarantine_event(plan_doc, state))
    views, projections = {}, {}

    def view_for(case: dict) -> dict:  # validation-only cold re-read on resume; never a logical attempt
        if case["slot"] not in views:
            view = native_view(scratch, case)
            NR._require(NR.sha_json(_lineage(view)) == state["cases"][plan_case_index[case["slot"]]]["lineage_sha256"],
                        "CASE_REVERIFY_MISMATCH")
            views[case["slot"]] = view
        return views[case["slot"]]

    plan_case_index = {c["slot"]: i for i, c in enumerate(plan_doc["plan"]["cases"])}
    for index, case in enumerate(plan_doc["plan"]["cases"]):
        if state["cases"][index]["verify"] is None:
            ids = {"slot": case["slot"], "case_id": case["case_id"], "attempt_id": case["verify_attempt_id"]}
            state = _append(scratch, plan_doc, events, "CASE_VERIFY_STARTED", ids)
            outcome = None
            try:
                view = native_view(scratch, case)
                lineage = _lineage(view)
            except STOPS as stop:
                outcome = ("CASE_VERIFY_REFUSED", dict(ids, reason=_code(stop)))
            except Exception:  # noqa: BLE001 - closed failure, never retried
                outcome = ("CASE_VERIFY_FAILED", dict(ids, reason="NATIVE_VERIFY_EXCEPTION"))
            if attempts:  # durable and distinct, never an ordinary terminal or a clean-interruption quarantine
                _append(scratch, plan_doc, events, "CASE_VERIFY_QUARANTINED", dict(ids, reason=NR.NETWORK_QUARANTINE_REASON))
                raise NR.CoordinationStop("NETWORK_ATTEMPT_BLOCKED")  # stops unsealed; never retried
            if outcome:
                state = _append(scratch, plan_doc, events, *outcome)
            else:
                views[case["slot"]] = view
                state = _append(scratch, plan_doc, events, "CASE_VERIFIED", dict(ids, lineage_sha256=NR.sha_json(lineage)))
        for task in case["tasks"]:
            role, case_state = task["role"], state["cases"][index]
            done = case_state["tasks"][role]
            if done is not None:
                if done["status"] == "COMPLETED_CONSUMED":  # recomputed for dependants, never re-attempted
                    try:
                        out = NR.consume(role, view_for(case), _deps(case, role, projections))
                    except NR.RoleRefusal:
                        raise NR.CoordinationStop("CONSUMER_RECOMPUTE_REFUSED") from None
                    NR._require(NR.consumer_record(task, out, done["record"]["dependencies"]) == done["record"],
                                "CONSUMER_RECOMPUTE_MISMATCH")
                    projections[(case["slot"], role)] = out["projection"]
                continue
            decision, reason = NR.decide(case, role, case_state["verify"], {r: v for r, v in case_state["tasks"].items() if v})
            ids = {"slot": case["slot"], "role": role, "task_id": task["task_id"]}
            if decision == "SKIP":
                state = _append(scratch, plan_doc, events, "ROLE_SKIPPED", dict(ids, reason=reason))
                continue
            view = view_for(case)  # a re-read failure stops the campaign; it is never recorded as a role outcome
            ids["attempt_id"] = task["attempt_id"]
            state = _append(scratch, plan_doc, events, "ROLE_STARTED", ids)
            try:
                out = NR.consume(role, view, _deps(case, role, projections))
            except NR.RoleRefusal as refusal:
                state = _append(scratch, plan_doc, events, "ROLE_REFUSED", dict(ids, reason=_code(refusal)))
            except Exception:  # noqa: BLE001 - closed failure, never retried
                state = _append(scratch, plan_doc, events, "ROLE_FAILED", dict(ids, reason="CONSUMER_EXCEPTION"))
            else:
                deps_ids = [case_state["tasks"][p]["record"]["consumer_id"] for p in task["prerequisites"]]
                record = NR.consumer_record(task, out, deps_ids)
                state = _append(scratch, plan_doc, events, "ROLE_COMPLETED_CONSUMED", dict(ids, **record))
                projections[(case["slot"], role)] = out["projection"]
    return _seal(scratch, plan_doc, events, views, attempts)


def _code(error: Exception) -> str:
    code = str(error).split(":")[0] if not isinstance(error, (NR.CoordinationStop, NR.RoleRefusal)) else str(error)
    return code if NR.CODE_RE.fullmatch(code) else "NATIVE_REFUSAL"


# ------------------------------------------------------------------ R010 seal + cold verify


def recompute(scratch: Path, plan_doc: dict, events: list, views: dict) -> dict:
    """Receipt core from the replayed journal; every verified case and every delivered role is recomputed from
    the frozen native bytes (native verify again, then the same pure consumer), never trusted from the journal."""
    state = NR.replay(plan_doc, events)
    NR._require(state["complete"], "CAMPAIGN_INCOMPLETE")
    lineages, projections = {}, {}
    for index, case in enumerate(plan_doc["plan"]["cases"]):
        case_state = state["cases"][index]
        if case_state["verify"] != "VERIFIED":
            continue  # structural only: refused/failed/quarantined history is local evidence, not attestation
        view = views.get(case["slot"]) or native_view(scratch, case)
        lineage = _lineage(view)
        NR._require(NR.sha_json(lineage) == case_state["lineage_sha256"], "LINEAGE_RECOMPUTE_MISMATCH")
        lineages[case["slot"]] = lineage
        for task in case["tasks"]:
            done = case_state["tasks"][task["role"]]
            if done["status"] != "COMPLETED_CONSUMED":
                continue
            try:
                out = NR.consume(task["role"], view, _deps(case, task["role"], projections))
            except NR.RoleRefusal:
                raise NR.CoordinationStop("CONSUMER_RECOMPUTE_REFUSED") from None
            NR._require(NR.consumer_record(task, out, done["record"]["dependencies"]) == done["record"],
                        "CONSUMER_RECOMPUTE_MISMATCH")
            projections[(case["slot"], task["role"])] = out["projection"]
    return NR.build_core(code_identity=code_identity(), plan_doc=plan_doc, state=state, lineages=lineages,
                         projections=projections)


def _receipt_bytes(receipt: dict) -> bytes:
    return json.dumps(receipt, sort_keys=True, indent=1, ensure_ascii=False).encode("utf-8")


def _seal(scratch: Path, plan_doc: dict, events: list, views: dict, attempts: list) -> dict:
    core = recompute(scratch, plan_doc, events, views)  # may re-enter native verifiers (resume)
    NR._require(not attempts, "NETWORK_ATTEMPT_BLOCKED")  # a blocked socket attempt never reaches a seal
    receipt = NR.finalize(core)
    data = _receipt_bytes(receipt)
    NR._require(len(data) <= MAX_RECEIPT_BYTES, "RECEIPT_TOO_LARGE")
    _write_new(scratch / "receipt.json", data)
    return {"receipt_id": receipt["receipt_id"], "totals": core["totals"], "network_attempts": 0}


def run(manifest_path, evidence_root, scratch_dir) -> dict:
    scratch = B3._scratch(scratch_dir)
    with SGCLI.no_network() as attempts:
        manifest_file = REL._caller_path(str(manifest_path), directory=False, scratch=scratch)
        root = REL._caller_path(str(evidence_root), directory=True, scratch=scratch)
        NR._require(manifest_file is not None and root is not None, "INPUT_PATH_UNUSABLE")
        NR._require(not (scratch.exists() and any(scratch.iterdir())), "SCRATCH_NOT_EMPTY")  # write once, no hidden rerun
        NR._require(not REL._inside(manifest_file, root), "INPUT_PATHS_OVERLAP")
        raw = _read(manifest_file, MAX_MANIFEST_BYTES, "MANIFEST_UNREADABLE")
        manifest = parse_manifest(raw)
        _cases_layout(root, manifest)
        before, hashes = _inventory(root, manifest)
        scratch.mkdir(parents=True, exist_ok=True)
        with _writer(scratch):
            inputs = scratch / "inputs"
            inputs.mkdir()
            for slot, files in hashes.items():
                for name, is_dir in CASE_TOP[manifest["cases"][NR.slots(manifest).index(slot)]["source_kind"]].items():
                    if is_dir:  # the file copy below would drop an empty native top-level directory
                        (inputs / slot / name).mkdir(parents=True)
                for rel in files:
                    target = inputs / slot / rel
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(root / slot / rel, target)
            _write_new(inputs / "manifest.json", raw)
            NR._require(_inventory(inputs, manifest) == (before, hashes), "INPUT_CHANGED_DURING_FREEZE")
            plan_doc = NR.build_plan(manifest, _bound(before, raw))
            _write_new(scratch / "plan.json", SG.canonical_bytes(plan_doc))
            (scratch / "journal").mkdir()
            result = _drive(scratch, plan_doc, [], attempts)
        NR._require(_inventory(root, manifest) == (before, hashes), "INPUT_CHANGED_DURING_RUN")  # caller files untouched
    NR._require(not attempts, "NETWORK_ATTEMPT_BLOCKED")
    return dict(result, status="RUN_COMPLETE")


def resume(scratch_dir) -> dict:
    scratch = B3._scratch(scratch_dir)
    NR._require(scratch.is_dir(), "SCRATCH_INVALID")
    if (scratch / "receipt.json").exists() or (scratch / "receipt.json").is_symlink():
        checked = verify(scratch)  # sealed: read-only, never overwritten or re-run
        return dict(checked, status="SEALED_VERIFIED") if checked["status"] == "VERIFIED" else checked
    NR._require(not (scratch / LOCK).exists() and not (scratch / LOCK).is_symlink(), "WRITER_LOCK_PRESENT")
    _layout(scratch, sealed=False, lock=False)
    with SGCLI.no_network() as attempts:
        with _writer(scratch):
            plan_doc, events, _ = _load(scratch)
            result = _drive(scratch, plan_doc, events, attempts)
    NR._require(not attempts, "NETWORK_ATTEMPT_BLOCKED")
    return dict(result, status="RESUMED_COMPLETE")


def _digest_tree(scratch: Path) -> dict:
    return {p.relative_to(scratch).as_posix(): B2._sha(p) for p in sorted(scratch.rglob("*")) if p.is_file()}


def verify(scratch_dir) -> dict:
    """Cold and read-only: no writer present; layout, plan, journal, native verify and every delivered projection
    recomputed; the whole core compared as exact canonical bytes and the id recomputed."""
    scratch = B3._scratch(scratch_dir)
    NR._require(scratch.is_dir(), "SCRATCH_INVALID")
    NR._require(not (scratch / LOCK).exists() and not (scratch / LOCK).is_symlink(), "ACTIVE_WRITER_PRESENT")
    failures = []
    with SGCLI.no_network() as attempts:
        _layout(scratch, sealed=True, lock=False)  # exact sealed layout before any read, hash or native verifier
        raw = _read(scratch / "receipt.json", MAX_RECEIPT_BYTES, "RECEIPT_UNREADABLE")
        receipt = SGCLI._strict_json(raw, "RECEIPT_UNREADABLE")
        before = None
        try:
            plan_doc, events, _ = _load(scratch)  # bounds and the exact plan/journal before the whole-tree witness
            before = _digest_tree(scratch)
            core = recompute(scratch, plan_doc, events, {})
            if not isinstance(receipt, dict) or set(receipt) != {"schema_id", "receipt_id", "core"}:
                failures.append("RECEIPT_SHAPE_INVALID")
            elif receipt["schema_id"] != NR.RECEIPT_SCHEMA:
                failures.append("RECEIPT_SCHEMA_INVALID")
            elif type(receipt["core"]) is not dict:
                failures.append("RECEIPT_FIELDS_INVALID")
            else:  # exact canonical bytes (no bool/int/float or null/absent conflation); id from the recomputed core
                if SG.canonical_bytes(receipt["core"]) != SG.canonical_bytes(core):
                    failures.append("CORE_MISMATCH")
                if receipt["receipt_id"] != NR.finalize(core)["receipt_id"]:
                    failures.append("RECEIPT_ID_MISMATCH")
                if raw != _receipt_bytes(receipt):
                    failures.append("RECEIPT_BYTES_NONCANONICAL")
        except STOPS as stop:
            failures.append("RECOMPUTE_REFUSED:" + _code(stop))
        except (KeyError, TypeError, AttributeError, OSError, ValueError):
            failures.append("RECEIPT_FIELDS_INVALID")
        if before is not None and _digest_tree(scratch) != before:
            failures.append("SCRATCH_CHANGED_DURING_VERIFY")
    NR._require(not attempts, "NETWORK_ATTEMPT_BLOCKED")
    return {"status": "VERIFIED" if not failures else "TAMPER_DETECTED", "failures": failures,
            "receipt_id": receipt.get("receipt_id") if isinstance(receipt, dict) and not failures else None,
            "network_attempts": 0}


def run_safe(args) -> dict:
    """Closed result for every outcome; never echoes input text, paths, ids or tracebacks."""
    try:
        if args.command == "run":
            return run(args.manifest, args.evidence_root, args.scratch_dir)
        if args.command == "resume":
            return resume(args.scratch_dir)
        return verify(args.scratch_dir)
    except STOPS as stop:
        return {"status": "STOPPED", "reason_code": _code(stop)}
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
    for flag in ("--manifest", "--evidence-root", "--scratch-dir"):
        first.add_argument(flag, required=True, type=Path)
    for name in ("resume", "verify"):
        sub.add_parser(name).add_argument("--scratch-dir", required=True, type=Path)
    result = run_safe(parser.parse_args(argv))
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] in OK_STATUSES else 1


if __name__ == "__main__":
    raise SystemExit(main())
