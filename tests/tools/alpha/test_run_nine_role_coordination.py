"""S10-CAP-NINE-ROLE-COORD-01 R001/R003/R005-R010: B4 operator over real sealed native B2/B3 receipts.

The pinned parts need real B2/B3 receipts, whose B1-A spine needs the exact pinned Hermes checkout
(``POLYMARKET_HERMES_PIN_ROOT``); without it they skip with a reason (hosted CI: D001) and every unpinned guard
still runs. Unpinned journal/recovery/seal parts use layout-valid trees that the real native B2 verifier refuses:
they exercise the real native call, journal, lock, resume and seal, and never earn a role delivery.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import tempfile

import pytest

from src.data_layer.analytical_research import nine_role_coordination as NR
from src.data_layer.analytical_research import relation_wallet_spine as RW
from tests.data_layer.analytical_research import test_execution_economics_spine as X
from tests.data_layer.analytical_research import test_relation_wallet_spine as T
from tests.data_layer.analytical_research import test_source_forecast_spine as B1
from tests.tools.alpha import test_run_relation_wallet_spine as B2T
from tools.alpha import run_execution_economics_spine as B3
from tools.alpha import run_hermes_delegated_specialists as W01
from tools.alpha import run_nine_role_coordination as CLI
from tools.alpha import run_relation_wallet_spine as B2
from tools.alpha import run_source_forecast_spine as B1A

PIN = os.environ.get("POLYMARKET_HERMES_PIN_ROOT")
HISTORICAL = os.environ.get("POLYMARKET_B4_HISTORICAL_ROOT")  # optional: base-built B2/B3 trees (R008 witness)
REPO_ROOT = Path(__file__).resolve().parents[3]
# native code identities at merged base 5666a33 (this WP edits none of them)
B2_CODE_IDENTITY_AT_BASE = "code:sha256:9ccd7b6c003293fb74b3bcb4d88c90cdf3f38770e09d49cb8428630486fade0a"
B3_CODE_IDENTITY_AT_BASE = "code:sha256:5f78ea2fd2337bb178275f9d9907890da2beb960ced6f3331873f5185b7736ee"
FAKE_B2 = "b2research:sha256:" + "a" * 64
WP_PATHS = {
    "src/data_layer/analytical_research/nine_role_coordination.py", "tools/alpha/run_nine_role_coordination.py",
    "tests/data_layer/analytical_research/test_nine_role_coordination.py",
    "tests/tools/alpha/test_run_nine_role_coordination.py", "docs/nine_role_coordination_contract.md",
    "docs/deferred_items_log.md", "docs/project_status.md", "docs/repo_truth_index.md",
    "docs/status_entries/S10-CAP-NINE-ROLE-COORD-01.md", "docs/wp_specs/S10-CAP-NINE-ROLE-COORD-01/wp_prompt.txt",
    "docs/wp_specs/S10-CAP-NINE-ROLE-COORD-01/wp_spec.json"}
_PINNED: dict = {}


class _Interrupt(BaseException):
    """A clean interruption (like KeyboardInterrupt): escapes every closed handler, unwinds the writer lock."""


def _need_pin():
    if not PIN:
        pytest.skip("POLYMARKET_HERMES_PIN_ROOT not set: exact pinned Hermes checkout absent (pinned part only, D001)")


def _tree(root: Path) -> dict:
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(Path(root).rglob("*")) if p.is_file()}


def pinned_evidence() -> dict | None:
    """One real B1-A spine run through the exact pin, two real B2 runs over it (A6 admitted / A6 natively refused)
    and one real B3 run over the admitted B2: existing builders and unmodified native operators only (cached)."""
    if not PIN:
        return None
    if not _PINNED:
        base = Path(tempfile.mkdtemp(prefix="b4-pinned-")).resolve()
        world = X.build_b3_world(base / "world")
        grounding = world["world"]
        registry = (base / "registry.sqlite3").resolve()
        shutil.copyfile(grounding["registry"], registry)
        (base / "spine.json").write_text(json.dumps(B1.spine_case(grounding)), encoding="utf-8")
        (base / "fc.json").write_text(json.dumps(B1.forecast_cases(grounding)), encoding="utf-8")
        spine = (base / "spine-scratch").resolve()
        made = B1A.run((base / "spine.json").resolve(), grounding["grounding"], (base / "fc.json").resolve(), registry, spine,
                       Path(PIN))
        assert made["status"] == "RUN_COMPLETE"
        led, out = world["ledger"], {"base": base, "world": world}
        evidence = base / "inputs"
        for name, kw in (("b2-admitted", {}), ("b2-refused", {"target_wallet": T.OTHER_WALLET})):
            case = (led["base"] / ("b4-" + name + ".json")).resolve()
            case.write_text(json.dumps(T.b2_case(made["receipt_id"], world["rel"]["receipt_id"], led, **kw)), encoding="utf-8")
            got = B2.run(spine, registry, world["rel_scratch"], led["path"], case, (evidence / name).resolve())
            assert got["status"] == "RUN_COMPLETE"
            out[name] = got["receipt_id"]
        receipt = json.loads((evidence / "b2-admitted" / "receipt.json").read_bytes())
        (base / "b3case").mkdir()
        b3case = (base / "b3case" / "case.json").resolve()
        b3case.write_text(json.dumps(X.probe_case(dict(world, core=receipt["core"]), b2_receipt_id=receipt["receipt_id"])),
                          encoding="utf-8")
        got = B3.run((evidence / "b2-admitted").resolve(), b3case, None, (evidence / "b3").resolve())
        assert got["status"] == "RUN_COMPLETE" and got["a7"] == "PARTIAL"
        out["b3"] = got["receipt_id"]
        out["trees"] = {name: _tree(evidence / name) for name in ("b2-admitted", "b2-refused", "b3")}
        _PINNED.update(out)
    return _PINNED


def pinned_views() -> dict | None:
    """Real native views (unmodified top-level native verify + bounded receipt reads) over the pinned evidence."""
    ev = pinned_evidence()
    if ev is None:
        return None
    kinds = {"b2": ("b2-admitted", "B2"), "b2_refused": ("b2-refused", "B2"), "b3": ("b3", "B3")}
    return {key: CLI.native_view(ev["base"], {"slot": slot, "source_kind": kind, "receipt_id": ev[slot]})
            for key, (slot, kind) in kinds.items()}


def _fake_b2(directory: Path) -> Path:
    """A layout-valid B2-shaped tree with no B2 proof: the real native B2 verifier refuses it."""
    (directory / "inputs").mkdir(parents=True)
    (directory / "parity").mkdir()
    (directory / "receipt.json").write_bytes(b"{}")
    return directory


def _campaign(base: Path, cases: list, *, fake: bool = False) -> tuple[Path, Path, Path]:
    """evidence-root/case-NN copies + a strict manifest; cases: (source tree | None, kind, receipt id, route)."""
    root = (base / "ev").resolve()
    root.mkdir(parents=True)
    for index, (source, kind, receipt_id, route) in enumerate(cases):
        slot = root / ("case-%02d" % (index + 1))
        _fake_b2(slot) if source is None else shutil.copytree(source, slot)
    manifest = (base / "manifest.json").resolve()
    manifest.write_text(json.dumps({"schema_id": NR.MANIFEST_SCHEMA, "cases": [
        {"source_kind": k, "receipt_id": i, "route": r} for _, k, i, r in cases]}), encoding="utf-8")
    return manifest, root, (base / "scratch").resolve()


def _args(**kw):
    return type("Args", (), kw)()


def _run(manifest, root, scratch) -> dict:
    return CLI.run_safe(_args(command="run", manifest=manifest, evidence_root=root, scratch_dir=scratch))


def _resume(scratch) -> dict:
    return CLI.run_safe(_args(command="resume", scratch_dir=scratch))


def _verify(scratch) -> dict:
    return CLI.run_safe(_args(command="verify", scratch_dir=scratch))


def _events(scratch: Path) -> list:
    return [json.loads(p.read_bytes()) for p in sorted((scratch / "journal").iterdir())]


def _types(scratch: Path) -> list:
    return [(e["event"]["type"], e["event"]["payload"]["slot"], e["event"]["payload"].get("role")) for e in _events(scratch)]


def _receipt(scratch: Path) -> dict:
    return json.loads((scratch / "receipt.json").read_bytes())


def _rows(receipt: dict, index: int) -> dict:
    return {t["role"]: (t["status"], t["native_status"] if t["status"] == "COMPLETED_CONSUMED" else t["reason"])
            for t in receipt["core"]["cases"][index]["tasks"]}


def _no_dispatch(monkeypatch) -> list:
    """Any fresh W01/Hermes delegation or B1-A/B2/B3 producer run during B4 is recorded (and refused)."""
    calls = []
    for module, name in ((W01, "run"), (W01, "produce"), (B1A, "run"), (B2, "run"), (B3, "run")):
        monkeypatch.setattr(module, name, lambda *a, _n=name, **k: (calls.append(_n), (_ for _ in ()).throw(AssertionError(_n))))
    return calls


def _spy_verify(monkeypatch, check=None) -> list:
    calls = []
    for module in (B2, B3):
        real = module.verify

        def wrapped(root, _real=real, _m=module):
            calls.append((_m.__name__.rsplit(".", 1)[1], Path(root).name))
            if check:
                check(Path(root))
            return _real(root)
        monkeypatch.setattr(module, "verify", wrapped)
    return calls


# ------------------------------------------------------------------ R001


def test_b4_exact_native_case_lineage(tmp_path, monkeypatch, capsys):
    good = {"schema_id": NR.MANIFEST_SCHEMA, "cases": [{"source_kind": "B2", "receipt_id": FAKE_B2, "route": "SOURCE_REVIEW"}]}
    CLI.parse_manifest(json.dumps(good).encode())
    case = good["cases"][0]
    variants = {
        "MANIFEST_SCHEMA_UNSUPPORTED": [dict(good, schema_id="side26-nine-role-campaign-v2"), dict(good, schema_id=None)],
        "MANIFEST_UNKNOWN_FIELD": [dict(good, scratch="x"), dict(good, cases=[dict(case, path="/x")])],
        "MANIFEST_FIELD_MISSING": [{"schema_id": NR.MANIFEST_SCHEMA}, dict(good, cases=[{"source_kind": "B2", "route": "SOURCE_REVIEW"}])],
        "MANIFEST_FIELD_TYPE_INVALID": [dict(good, cases={"0": case}), dict(good, cases=[dict(case, route=True)]),
                                        dict(good, cases=[dict(case, receipt_id=1)]), dict(good, cases=["case"]), [good]],
        "MANIFEST_FIELD_VALUE_INVALID": [dict(good, cases=[]), dict(good, cases=[case, dict(case, route="FULL_SHARED_CASE"),
                                                                                  dict(case, route="WALLET_REVIEW")]),
                                         dict(good, cases=[dict(case, source_kind="b2")]),
                                         dict(good, cases=[dict(case, route="full_shared_case")]),
                                         dict(good, cases=[dict(case, source_kind="B1A")])],
        "MANIFEST_RECEIPT_ID_INVALID": [dict(good, cases=[dict(case, receipt_id=FAKE_B2.upper())]),
                                        dict(good, cases=[dict(case, receipt_id="b3research:sha256:" + "a" * 64)]),
                                        dict(good, cases=[dict(case, receipt_id=FAKE_B2 + "0")]),
                                        dict(good, cases=[dict(case, receipt_id="b2research:sha256:" + "а" * 64)]),
                                        dict(good, cases=[dict(case, receipt_id="b2research:sha256:" + "a" * 300)])],
        "MANIFEST_DUPLICATE_CASE": [dict(good, cases=[case, dict(case)])],
    }
    for code, values in variants.items():
        for value in values:
            with pytest.raises(NR.CoordinationStop) as excinfo:
                CLI.parse_manifest(json.dumps(value).encode())
            assert str(excinfo.value) == code, (code, value)
    for raw, code in ((b'{"schema_id":"a","schema_id":"b","cases":[]}', "MANIFEST_JSON_INVALID"),
                      (b'{"schema_id":NaN}', "MANIFEST_JSON_INVALID"), (b"\xff", "MANIFEST_JSON_INVALID"),
                      (b"", "MANIFEST_UNREADABLE"), (b" " * ((1 << 20) + 1), "MANIFEST_UNREADABLE")):
        with pytest.raises(CLI.STOPS) as excinfo:
            CLI.parse_manifest(raw)
        assert str(excinfo.value) == code
    two = dict(good, cases=[case, dict(case, route="FULL_SHARED_CASE")])  # same id, distinct route: two declared cases
    assert NR.slots(json.loads(json.dumps(two))) == ["case-01", "case-02"] and CLI.parse_manifest(json.dumps(two).encode())
    # malformed global layout fails before any hash or native verifier (no dispatch, no scratch)
    hashes, calls = [], _spy_verify(monkeypatch)
    real_sha = B2._sha
    monkeypatch.setattr(B2, "_sha", lambda p: (hashes.append(1), real_sha(p))[1])
    for name, mutate in (("extra", lambda root: (root / "case-02").mkdir()),
                         ("kind", lambda root: shutil.rmtree(root / "case-01" / "parity")),
                         ("member", lambda root: (root / "case-01" / "notes.txt").write_text("x"))):
        manifest, root, scratch = _campaign(tmp_path / name, [(None, "B2", FAKE_B2, "SOURCE_REVIEW")])
        mutate(root)
        assert _run(manifest, root, scratch) == {"status": "STOPPED", "reason_code": "CASE_LAYOUT_INVALID"}, name
        assert not scratch.exists()
    manifest, root, scratch = _campaign(tmp_path / "b3kind", [(None, "B3", "b3research:sha256:" + "c" * 64, "FULL_SHARED_CASE")])
    assert _run(manifest, root, scratch)["reason_code"] == "CASE_LAYOUT_INVALID"  # B2-shaped tree declared as B3
    assert hashes == [] and calls == []
    # an unverifiable source is a terminal case refusal (real native B2 verify), never a role delivery
    manifest, root, scratch = _campaign(tmp_path / "unverified", [(None, "B2", FAKE_B2, "FULL_SHARED_CASE")])
    result = _run(manifest, root, scratch)
    assert result["status"] == "RUN_COMPLETE" and calls == [("run_relation_wallet_spine", "case-01")]
    receipt = _receipt(scratch)
    assert receipt["core"]["cases"][0]["verify"] == {"status": "REFUSED", "reason": "NATIVE_VERIFY_REFUSED",
                                                     "attempt_id": receipt["core"]["cases"][0]["verify"]["attempt_id"]}
    rows = _rows(receipt, 0)
    assert all(rows[r] == ("SKIPPED", "CASE_NOT_VERIFIED") for r in NR.ROLES[:7])
    assert receipt["core"]["cases"][0]["lineage"] is None and result["totals"]["completed_consumed"] == 0
    assert str(tmp_path) not in capsys.readouterr().out
    _need_pin()
    ev, views = pinned_evidence(), pinned_views()
    manifest, root, scratch = _campaign(tmp_path / "source", [(ev["base"] / "inputs" / "b2-admitted", "B2", ev["b2-admitted"],
                                                              "SOURCE_REVIEW"),
                                                             (ev["base"] / "inputs" / "b2-admitted", "B2", ev["b2-refused"],
                                                              "SOURCE_REVIEW")])
    result = _run(manifest, root, scratch)
    assert result["status"] == "RUN_COMPLETE"
    receipt = _receipt(scratch)
    first, second = receipt["core"]["cases"]
    assert [t["status"] for t in first["tasks"][:2]] == ["COMPLETED_CONSUMED"] * 2
    assert _rows(receipt, 0)["A3"] == ("SKIPPED", "NOT_REQUESTED")
    # the declared id must equal the id the native verifier returns for that tree: a valid foreign id refuses
    assert (second["verify"]["status"], second["verify"]["reason"]) == ("REFUSED", "RECEIPT_ID_MISMATCH")
    lineage, native = first["lineage"], views["b2"]
    b2c = native["b2"]["core"]
    assert lineage["receipt_id"] == lineage["b2_receipt_id"] == ev["b2-admitted"] and lineage["b3_receipt_id"] is None
    assert lineage["spine_receipt_id"] == b2c["b1a_lineage"]["spine_receipt_id"] == native["spine"]["receipt_id"]
    assert lineage["w01_receipt_id"] == native["spine"]["core"]["w01"]["receipt_id"] == native["w01"]["receipt_id"]
    assert (lineage["grounding_receipt_id"], lineage["as_of"], lineage["alpha_universe_snapshot_id"]) == \
        tuple(b2c["shared_case"][k] for k in ("grounding_receipt_id", "as_of", "alpha_universe_snapshot_id"))
    assert lineage["decision_time"] == b2c["a5_relations"]["decision_time"] and lineage["decision_time"] >= lineage["as_of"]
    assert lineage["target_market_id"] == b2c["shared_case"]["target"]["market_id"]
    assert NR.case_lineage(views["b3"])["b2_receipt_id"] == ev["b2-admitted"]
    # mismatched nested identities refuse with closed codes (never a caller-derived role claim)
    def refused(key, mutate):
        bad = copy.deepcopy(views[key])
        mutate(bad)
        with pytest.raises(NR.CoordinationStop) as excinfo:
            NR.case_lineage(bad)
        return str(excinfo.value)
    assert refused("b2", lambda v: v.update(spine=views["b2_refused"]["spine"] | {"receipt_id": "b1spine:sha256:" + "0" * 64})) \
        == "NESTED_SPINE_MISMATCH"
    assert refused("b2", lambda v: v["w01"].update(receipt_id="hermesdelegatedreceipt:sha256:" + "0" * 64)) == "NESTED_W01_MISMATCH"
    assert refused("b2", lambda v: v["w01"]["core"].update(grounding_receipt_id="srcground:sha256:" + "0" * 64)) \
        == "NESTED_GROUNDING_MISMATCH"
    assert refused("b2", lambda v: v["b2"]["core"]["shared_case"]["target"].update(candidate_id="x")) == "NESTED_TARGET_MISMATCH"
    assert refused("b3", lambda v: v.update(b2=views["b2_refused"]["b2"])) == "NESTED_B2_MISMATCH"
    assert refused("b2", lambda v: v.update(b3=views["b3"]["b3"])) == "NESTED_B3_UNEXPECTED"
    assert refused("b2", lambda v: v.update(receipt_id=ev["b2-refused"])) == "CASE_RECEIPT_ID_MISMATCH"


# ------------------------------------------------------------------ R003


def test_b4_pinned_child_origin_pair(tmp_path, monkeypatch):
    _need_pin()
    ev, views = pinned_evidence(), pinned_views()
    dispatched = _no_dispatch(monkeypatch)
    manifest, root, scratch = _campaign(tmp_path, [(ev["base"] / "inputs" / "b2-admitted", "B2", ev["b2-admitted"],
                                                   "FORECAST_REVIEW")])
    assert _run(manifest, root, scratch)["status"] == "RUN_COMPLETE" and dispatched == []
    receipt = _receipt(scratch)
    tasks = {t["role"]: t for t in receipt["core"]["cases"][0]["tasks"]}
    w01 = views["b2"]["w01"]
    children = w01["core"]["witness_body"]["children"]
    for role, index in (("A3", 0), ("A4", 1)):
        task, child = tasks[role], children[index]
        projection = task["projection"]
        assert task["status"] == "COMPLETED_CONSUMED" and task["native_status"] == child["status"]
        for key in ("task_index", "session_id", "parent_session_id", "subagent_id", "effective_tools", "api_calls", "tokens",
                    "cost", "summary_sha256"):
            assert projection[key] == child[key], key
        assert projection["child_role"] == NR.W01_ROLES[index] == child["role"]
        assert projection["witness_id"] == w01["core"]["witness_id"] and projection["episode_id"] == w01["core"]["episode_id"]
        assert projection["w01_receipt_id"] == w01["receipt_id"] and projection["new_dispatches"] == 0
        assert projection["provider_invocations_recorded"] == "ZERO_REAL_PROVIDER_INVOCATIONS"
        assert (projection["cost"], projection["cost_status"]) == ("UNKNOWN", "UNKNOWN")  # unknown is never zero
        assert task["source"] == {"receipt_id": w01["receipt_id"], "member": "core.witness_body.children[%d]" % index}
    assert tasks["A3"]["consumer_id"] != tasks["A4"]["consumer_id"] and tasks["A3"]["source"] != tasks["A4"]["source"]
    assert tasks["A4"]["dependencies"][-1] == tasks["A3"]["consumer_id"]
    assert tasks["A3"]["projection"]["session_id"] != tasks["A4"]["projection"]["session_id"] \
        != tasks["A3"]["projection"]["parent_session_id"]
    text = json.dumps(receipt)
    assert all(c["summary"] not in text for c in children)  # raw child summaries are never echoed
    assert receipt["core"]["prior_host_witness"]["case-01"]["provider_invocations"] == "ZERO_REAL_PROVIDER_INVOCATIONS"
    # the pair is atomic: any defect refuses both halves; the B1-A summary must match the witnessed children
    def pair(mutate):
        bad = copy.deepcopy(views["b2"])
        mutate(bad)
        codes = []
        for role, deps in (("A3", {}), ("A4", {"A3": tasks["A3"]["projection"]})):
            with pytest.raises(NR.RoleRefusal) as excinfo:
                NR.consume(role, bad, deps)
            codes.append(str(excinfo.value))
        return codes
    body = lambda v: v["w01"]["core"]["witness_body"]  # noqa: E731
    assert pair(lambda v: body(v)["children"].reverse()) == ["W01_PAIR_SHAPE_INVALID"] * 2
    assert pair(lambda v: body(v)["children"].pop()) == ["W01_PAIR_SHAPE_INVALID"] * 2
    assert pair(lambda v: body(v)["children"][1].update(session_id=body(v)["children"][0]["session_id"])) \
        == ["W01_PAIR_IDENTITY_INVALID"] * 2
    assert pair(lambda v: body(v)["children"][0].update(parent_session_id="other")) == ["W01_PAIR_IDENTITY_INVALID"] * 2
    assert pair(lambda v: body(v)["children"][1].update(subagent_id=body(v)["children"][0]["subagent_id"])) \
        == ["W01_PAIR_IDENTITY_INVALID"] * 2
    assert pair(lambda v: v["spine"]["core"]["w01"]["children"][1].update(status="failed")) == ["W01_PAIR_SUMMARY_MISMATCH"] * 2
    assert pair(lambda v: v["w01"]["core"].update(witness_id="hermesdelegationwitness:sha256:" + "0" * 64)) \
        == ["W01_PAIR_WITNESS_MISMATCH"] * 2
    assert pair(lambda v: body(v)["children"][0].update(api_calls=True)) == ["W01_PAIR_USAGE_INVALID"] * 2
    with pytest.raises(NR.RoleRefusal, match="W01_PAIR_PARTNER_MISMATCH"):
        NR.consume("A4", views["b2"], {"A3": dict(tasks["A3"]["projection"], subagent_id="sa-x")})


# ------------------------------------------------------------------ R005


def test_b4_journal_intent_before_call(tmp_path, monkeypatch):
    seen = []

    def at_call(root: Path):  # what is durable on disk at the moment the native verifier is entered
        scratch = root.parents[1]
        last = _events(scratch)[-1]["event"]
        seen.append((last["type"], last["payload"]["slot"], root.name))
        seen.append(_resume(scratch)["reason_code"])  # a competing writer is refused while this one holds the lock
        seen.append(_verify(scratch)["reason_code"])
    calls = _spy_verify(monkeypatch, at_call)
    manifest, root, scratch = _campaign(tmp_path / "fake", [(None, "B2", FAKE_B2, "FULL_SHARED_CASE"),
                                                            (None, "B2", FAKE_B2[:-1] + "b", "WALLET_REVIEW")])
    caller = _tree(root)
    result = _run(manifest, root, scratch)
    assert result["status"] == "RUN_COMPLETE" and len(calls) == 2
    assert seen == [("CASE_VERIFY_STARTED", "case-01", "case-01"), "WRITER_LOCK_PRESENT", "ACTIVE_WRITER_PRESENT",
                    ("CASE_VERIFY_STARTED", "case-02", "case-02"), "WRITER_LOCK_PRESENT", "ACTIVE_WRITER_PRESENT"]
    types = _types(scratch)
    assert len(types) == 2 * (2 + 9) and [t[0] for t in types[:2]] == ["CASE_VERIFY_STARTED", "CASE_VERIFY_REFUSED"]
    assert all(t[0] == "ROLE_SKIPPED" for t in types[2:11]) and [t[2] for t in types[2:11]] == list(NR.ROLES)
    assert not (scratch / CLI.LOCK).exists() and sorted(p.name for p in scratch.iterdir()) == \
        ["inputs", "journal", "plan.json", "receipt.json"]
    assert _tree(root) == caller  # caller files never written
    # chained, exact and closed: every event links to the previous id, the first to the plan id
    events, plan = _events(scratch), json.loads((scratch / "plan.json").read_bytes())
    assert events[0]["event"]["prev"] == plan["plan_id"]
    assert all(b["event"]["prev"] == a["event_id"] for a, b in zip(events, events[1:]))
    assert all((scratch / "journal" / ("%06d.json" % (i + 1))).read_bytes() == CLI.SG.canonical_bytes(e)
               for i, e in enumerate(events))
    # write once: the run never repeats over a used scratch, an event or plan file is never replaced
    assert _run(manifest, root, scratch) == {"status": "STOPPED", "reason_code": "SCRATCH_NOT_EMPTY"}
    with pytest.raises(FileExistsError):
        CLI._write_new(scratch / "plan.json", b"{}")
    with pytest.raises(NR.CoordinationStop, match="JOURNAL_ORDER_INVALID"):  # an illegal next event is never written
        CLI._append(scratch, plan, events[:1], "ROLE_STARTED", {"slot": "case-01", "role": "A1", "task_id": "x",
                                                               "attempt_id": "y"})
    assert len(_events(scratch)) == len(events)
    _need_pin()
    monkeypatch.undo()  # the unpinned verify spy must not wrap the nested native B2 verify inside B3
    ev = pinned_evidence()
    order = []
    for role, consumer in list(NR.CONSUMERS.items()):
        def wrapped(view, deps, _role=role, _consumer=consumer):
            order.append((_role, _events(scratch2)[-1]["event"]["type"], _events(scratch2)[-1]["event"]["payload"].get("role")))
            return _consumer(view, deps)
        monkeypatch.setitem(NR.CONSUMERS, role, wrapped)
    manifest, root, scratch2 = _campaign(tmp_path / "pinned", [(ev["base"] / "inputs" / "b3", "B3", ev["b3"], "FULL_SHARED_CASE")])
    assert _run(manifest, root, scratch2)["status"] == "RUN_COMPLETE"
    first = {}
    for role, kind, announced in order:
        first.setdefault(role, (kind, announced))
    assert first == {r: ("ROLE_STARTED", r) for r in NR.ROLES[:7]}  # intent durable before every logical attempt
    starts = [t for t in _types(scratch2) if t[0] == "ROLE_STARTED"]
    assert len(starts) == len({t[2] for t in starts}) == 7  # at most one logical attempt per task


# ------------------------------------------------------------------ R006


def test_b4_resume_quarantine_and_progress(tmp_path, monkeypatch):
    real_verify = B2.verify
    calls = []

    def interrupt_first(root):
        calls.append(Path(root).name)
        if len(calls) == 1:
            raise _Interrupt()  # after CASE_VERIFY_STARTED is durable, before any terminal
        return real_verify(root)
    monkeypatch.setattr(B2, "verify", interrupt_first)
    manifest, root, scratch = _campaign(tmp_path / "case", [(None, "B2", FAKE_B2, "FULL_SHARED_CASE"),
                                                            (None, "B2", FAKE_B2[:-1] + "b", "SOURCE_REVIEW")])
    with pytest.raises(_Interrupt):
        CLI.run(manifest, root, scratch)
    assert not (scratch / CLI.LOCK).exists() and not (scratch / "receipt.json").exists()  # owner unwound cleanly
    assert _types(scratch) == [("CASE_VERIFY_STARTED", "case-01", None)]
    snapshot = (tmp_path / "interrupted").resolve()
    shutil.copytree(scratch, snapshot)
    result = _resume(scratch)
    assert result["status"] == "RESUMED_COMPLETE" and calls == ["case-01", "case-02"]  # never a second attempt
    types = _types(scratch)
    assert types[:2] == [("CASE_VERIFY_STARTED", "case-01", None), ("CASE_VERIFY_QUARANTINED", "case-01", None)]
    assert [t[0] for t in types].count("CASE_VERIFY_STARTED") == 2 and types[11:13] == [
        ("CASE_VERIFY_STARTED", "case-02", None), ("CASE_VERIFY_REFUSED", "case-02", None)]
    receipt = _receipt(scratch)
    assert receipt["core"]["cases"][0]["verify"]["status"] == "QUARANTINED"
    assert all(_rows(receipt, 0)[r] == ("SKIPPED", "CASE_NOT_VERIFIED") for r in NR.ROLES[:7])
    assert receipt["core"]["totals"]["case_verify_counts"] == {"QUARANTINED": 1, "REFUSED": 1}
    assert _verify(scratch)["status"] == "VERIFIED"
    sealed = _tree(scratch)
    assert _resume(scratch)["status"] == "SEALED_VERIFIED" and _tree(scratch) == sealed  # sealed resume is read-only
    # a stale lock (hard kill) is never stolen; a torn or gapped journal refuses; nothing is written
    for name, damage, code in (
            ("stale", lambda s: (s / CLI.LOCK).write_bytes(b"{}"), "WRITER_LOCK_PRESENT"),
            ("torn", lambda s: (s / "journal" / "000001.json").write_bytes(b'{"event_id":'), "JOURNAL_EVENT_INVALID"),
            ("empty", lambda s: (s / "journal" / "000001.json").write_bytes(b""), "JOURNAL_EVENT_INVALID"),
            ("gap", lambda s: shutil.copyfile(s / "journal" / "000001.json", s / "journal" / "000003.json"),
             "JOURNAL_SEQUENCE_INVALID"),
            ("alien", lambda s: (s / "journal" / "note.txt").write_text("x"), "SCRATCH_LAYOUT_INVALID"),
            ("plan", lambda s: (s / "plan.json").write_bytes((s / "plan.json").read_bytes() + b" "), "PLAN_MISMATCH")):
        copy_dir = (tmp_path / name).resolve()
        shutil.copytree(snapshot, copy_dir)
        damage(copy_dir)
        before = _tree(copy_dir)
        assert _resume(copy_dir) == {"status": "STOPPED", "reason_code": code}, name
        assert _tree(copy_dir) == before, name
    assert _verify(snapshot)["reason_code"] == "SCRATCH_LAYOUT_INVALID"  # unsealed: verify never seals
    shutil.copytree(snapshot, tmp_path / "locked")
    (tmp_path / "locked" / CLI.LOCK).write_bytes(b"{}")
    assert _verify((tmp_path / "locked").resolve())["reason_code"] == "ACTIVE_WRITER_PRESENT"
    # terminal state reached but the seal interrupted: resume seals only (no new event, no new attempt)
    monkeypatch.setattr(B2, "verify", real_verify)
    real_seal = CLI._seal
    monkeypatch.setattr(CLI, "_seal", lambda *a: (_ for _ in ()).throw(_Interrupt()))
    manifest, root, scratch = _campaign(tmp_path / "seal", [(None, "B2", FAKE_B2, "SOURCE_REVIEW")])
    with pytest.raises(_Interrupt):
        CLI.run(manifest, root, scratch)
    events = _events(scratch)
    monkeypatch.setattr(CLI, "_seal", real_seal)
    assert _resume(scratch)["status"] == "RESUMED_COMPLETE" and _events(scratch) == events and len(events) == 11
    _need_pin()
    ev = pinned_evidence()
    real_a3 = NR.CONSUMERS["A3"]
    a3_calls = []

    def interrupt_a3(view, deps):
        a3_calls.append(1)
        if len(a3_calls) == 1:
            raise _Interrupt()  # after ROLE_STARTED(A3) is durable
        return real_a3(view, deps)
    monkeypatch.setitem(NR.CONSUMERS, "A3", interrupt_a3)
    manifest, root, scratch = _campaign(tmp_path / "pinned", [(ev["base"] / "inputs" / "b2-refused", "B2", ev["b2-refused"],
                                                              "FULL_SHARED_CASE"),
                                                             (ev["base"] / "inputs" / "b3", "B3", ev["b3"], "FULL_SHARED_CASE")])
    with pytest.raises(_Interrupt):
        CLI.run(manifest, root, scratch)
    assert _types(scratch)[-1] == ("ROLE_STARTED", "case-01", "A3") and not (scratch / CLI.LOCK).exists()
    verifies = _spy_verify(monkeypatch)
    assert _resume(scratch)["status"] == "RESUMED_COMPLETE"
    receipt = _receipt(scratch)
    one, two = _rows(receipt, 0), _rows(receipt, 1)
    assert one["A1"][0] == one["A2"][0] == "COMPLETED_CONSUMED" and one["A3"] == ("QUARANTINED", NR.QUARANTINE_REASON)
    assert one["A4"] == one["A5"] == one["A6"] == ("SKIPPED", "PREREQUISITE_NOT_CONSUMED:A3")
    assert one["A7"] == ("SKIPPED", "B3_NOT_SUPPLIED")
    assert [two[r][0] for r in NR.ROLES[:7]] == ["COMPLETED_CONSUMED"] * 7 and two["A7"] == ("COMPLETED_CONSUMED", "PARTIAL")
    starts = [t for t in _types(scratch) if t[0] in ("ROLE_STARTED", "CASE_VERIFY_STARTED")]
    assert len(starts) == len(set(starts)) == 2 + 2 + 7 + 1  # one logical attempt per subject, A3 included
    # case-01 was cold re-read on resume only to recompute A1/A2 for the seal (validation, not a logical attempt)
    assert verifies == [("run_relation_wallet_spine", "case-01"), ("run_execution_economics_spine", "case-02"),
                        ("run_relation_wallet_spine", "b2")]  # the last is B3's own nested native B2 re-verify
    assert receipt["core"]["totals"]["quarantined"] == 1 and _verify(scratch)["status"] == "VERIFIED"
    # the seal's own native re-verify (resume after an interrupted seal) is gated too: no receipt after a socket attempt
    monkeypatch.undo()
    monkeypatch.setattr(CLI, "_seal", lambda *a: (_ for _ in ()).throw(_Interrupt()))
    manifest, root, scratch = _campaign(tmp_path / "sealnet", [(ev["base"] / "inputs" / "b2-admitted", "B2", ev["b2-admitted"],
                                                               "SOURCE_REVIEW")])
    with pytest.raises(_Interrupt):
        CLI.run(manifest, root, scratch)
    monkeypatch.undo()
    def swallowed(root):  # a native call that swallows the blocked-socket error and still verifies
        try:
            socket.create_connection(("192.0.2.1", 443))
        except Exception:  # noqa: BLE001
            pass
    _spy_verify(monkeypatch, swallowed)
    assert _resume(scratch) == {"status": "STOPPED", "reason_code": "NETWORK_ATTEMPT_BLOCKED"}
    assert not (scratch / "receipt.json").exists() and not (scratch / CLI.LOCK).exists()


# ------------------------------------------------------------------ R007


def test_b4_actual_pinned_two_case_campaign(tmp_path, monkeypatch):
    _need_pin()
    ev, views = pinned_evidence(), pinned_views()
    dispatched = _no_dispatch(monkeypatch)
    sockets = []
    monkeypatch.setattr(socket.socket, "connect", lambda s, *a, **k: sockets.append("connect"))
    monkeypatch.setattr(socket, "create_connection", lambda *a, **k: sockets.append("create_connection"))
    manifest, root, scratch = _campaign(tmp_path, [(ev["base"] / "inputs" / "b2-refused", "B2", ev["b2-refused"],
                                                   "FULL_SHARED_CASE"),
                                                  (ev["base"] / "inputs" / "b3", "B3", ev["b3"], "FULL_SHARED_CASE")])
    caller = _tree(root)
    result = _run(manifest, root, scratch)
    assert result["status"] == "RUN_COMPLETE" and result["network_attempts"] == 0 and sockets == [] and dispatched == []
    receipt = _receipt(scratch)
    assert result["receipt_id"] == receipt["receipt_id"] and _tree(root) == caller
    one, two = _rows(receipt, 0), _rows(receipt, 1)
    assert one == {"A1": ("COMPLETED_CONSUMED", "ADMITTED"), "A2": ("COMPLETED_CONSUMED", "ADMITTED"),
                   "A3": ("COMPLETED_CONSUMED", "completed"), "A4": ("COMPLETED_CONSUMED", "completed"),
                   "A5": ("COMPLETED_CONSUMED", "ADMITTED"), "A6": ("COMPLETED_CONSUMED", "REFUSED"),
                   "A7": ("SKIPPED", "B3_NOT_SUPPLIED"), "A8": ("SKIPPED", "W09_PENDING"), "A9": ("SKIPPED", "W10_PENDING")}
    assert two == dict(one, A6=("COMPLETED_CONSUMED", "ADMITTED"), A7=("COMPLETED_CONSUMED", "PARTIAL"))
    totals = receipt["core"]["totals"]
    assert (totals["planned_slots"], totals["completed_consumed"], totals["skipped"], totals["attempted"]) == (18, 13, 5, 13)
    assert totals["refused"] == totals["failed"] == totals["quarantined"] == 0 and receipt["core"]["journal"]["event_count"] == 35
    # native lineage and role digests: the same unmodified native verify + pure consumer reproduce every projection
    cases = receipt["core"]["cases"]
    assert cases[1]["lineage"]["b2_receipt_id"] == ev["b2-admitted"] and cases[1]["lineage"]["b3_receipt_id"] == ev["b3"]
    assert cases[0]["lineage"]["spine_receipt_id"] == cases[1]["lineage"]["spine_receipt_id"]  # one shared real spine
    projections = {}
    for task in cases[1]["tasks"]:
        if task["status"] == "COMPLETED_CONSUMED":
            out = NR.consume(task["role"], views["b3"], {p: projections[p] for p in NR.PREREQUISITES[task["role"]]})
            projections[task["role"]] = out["projection"]
            assert task["projection"] == out["projection"] and task["projection_sha256"] == NR.digest("projection", out["projection"])
    a7 = projections["A7"]
    assert a7["b3_receipt_id"] == ev["b3"] and a7["replay_status"] == "NOT_SUPPLIED"  # B3 R007 split: no replay claimed
    assert cases[0]["tasks"][5]["projection"]["native_reason"] == "NATIVE_REFUSED:PROFILE_REFERENCE_INVALID"
    assert receipt["core"]["new_activity"]["hermes_dispatches"] == 0 and receipt["core"]["claims"]["nine_functional_agents"] is False
    checked = _verify(scratch)
    assert checked == {"status": "VERIFIED", "failures": [], "receipt_id": receipt["receipt_id"], "network_attempts": 0}
    assert sockets == [] and dispatched == []
    # literal reading of the frozen R007: a pinned B2 source-route case and a B3 full-route case
    manifest, root, scratch = _campaign(tmp_path / "literal", [(ev["base"] / "inputs" / "b2-admitted", "B2", ev["b2-admitted"],
                                                               "SOURCE_REVIEW"),
                                                              (ev["base"] / "inputs" / "b3", "B3", ev["b3"], "FULL_SHARED_CASE")])
    assert _run(manifest, root, scratch)["status"] == "RUN_COMPLETE" and _verify(scratch)["status"] == "VERIFIED"
    receipt = _receipt(scratch)
    assert _rows(receipt, 0) == {"A1": ("COMPLETED_CONSUMED", "ADMITTED"), "A2": ("COMPLETED_CONSUMED", "ADMITTED"),
                                 **{r: ("SKIPPED", "NOT_REQUESTED") for r in ("A3", "A4", "A5", "A6", "A7")},
                                 "A8": ("SKIPPED", "W09_PENDING"), "A9": ("SKIPPED", "W10_PENDING")}
    assert _rows(receipt, 1) == two
    totals = receipt["core"]["totals"]
    assert (totals["planned_slots"], totals["completed_consumed"], totals["skipped"]) == (18, 9, 9)
    assert sockets == [] and dispatched == []


# ------------------------------------------------------------------ R008


def test_b4_native_predecessor_compatibility(tmp_path):
    for name, (module, identity) in B2T.NATIVE_IDENTITIES.items():
        assert module.code_identity() == identity, name
    assert B2.code_identity() == B2_CODE_IDENTITY_AT_BASE and B3.code_identity() == B3_CODE_IDENTITY_AT_BASE
    for rel in ("tools/alpha/run_relation_wallet_spine.py", "tools/alpha/run_execution_economics_spine.py",
                "tools/alpha/run_source_forecast_spine.py", "tools/alpha/run_hermes_delegated_specialists.py",
                "tools/alpha/run_related_market_alpha.py", "tools/alpha/run_oracle3_upstream_parity.py",
                "src/data_layer/analytical_research/relation_wallet_spine.py",
                "src/data_layer/analytical_research/execution_economics_spine.py",
                "src/data_layer/analytical_research/source_forecast_spine.py",
                "src/research_runtime/hermes_controlled_runtime/delegated_specialists.py"):
        assert "nine_role" not in (REPO_ROOT / rel).read_text(encoding="utf-8"), rel  # one-way dependency
    spec = json.loads((REPO_ROOT / "docs" / "wp_specs" / NR.WP_ID / "wp_spec.json").read_text(encoding="utf-8"))
    paths = spec["scope"]["required_changed_files"]
    assert len(paths) == 11 == len(set(paths)) and set(paths) == WP_PATHS and paths == spec["scope"]["allowed_changed_files"]
    b3_spec = json.loads((REPO_ROOT / "docs" / "wp_specs" / "S10-CAP-EXEC-ECONOMICS-01" / "wp_spec.json").read_text(encoding="utf-8"))
    assert len(b3_spec["scope"]["required_changed_files"]) == 11
    raw = X.CSV.read_bytes()
    assert X.CSV_SHA256 in (hashlib.sha256(raw).hexdigest(), hashlib.sha256(raw.replace(b"\r\n", b"\n")).hexdigest())
    for name in ("test_nine_role_coordination.py", "test_run_nine_role_coordination.py"):
        assert len(list((REPO_ROOT / "tests").rglob(name))) == 1, name
    _need_pin()
    ev = pinned_evidence()
    for name, kind in (("b2-admitted", B2), ("b2-refused", B2), ("b3", B3)):
        tree = _tree(ev["base"] / "inputs" / name)
        assert kind.verify(ev["base"] / "inputs" / name)["receipt_id"] == ev[name]
        assert tree == _tree(ev["base"] / "inputs" / name) == ev["trees"][name]  # unchanged after every B4 campaign
    if not HISTORICAL:  # explicit, never a silent pass: the base-built replay is a local exact-pin witness
        pytest.skip("POLYMARKET_B4_HISTORICAL_ROOT not set: base-built historical B2/B3 replay part only")
    # base-built (merged 5666a33) receipts replayed cold by the candidate from immutable copies
    hist = Path(HISTORICAL)
    summary = json.loads((hist / "hist_summary.json").read_bytes())
    assert summary["b2_code_identity"] == B2_CODE_IDENTITY_AT_BASE and summary["b3_code_identity"] == B3_CODE_IDENTITY_AT_BASE
    manifest, root, scratch = _campaign(tmp_path / "hist", [(hist / "b2-refused", "B2", summary["b2-refused"]["receipt_id"],
                                                             "FULL_SHARED_CASE"),
                                                            (hist / "b3", "B3", summary["b3"]["receipt_id"], "FULL_SHARED_CASE")])
    originals = {name: _tree(hist / name) for name in ("b2-refused", "b3")}
    assert _run(manifest, root, scratch)["status"] == "RUN_COMPLETE" and _verify(scratch)["status"] == "VERIFIED"
    assert _tree(scratch / "inputs" / "case-01") == originals["b2-refused"] and \
        _tree(scratch / "inputs" / "case-02") == originals["b3"]
    assert {name: _tree(hist / name) for name in originals} == originals
    assert _receipt(scratch)["core"]["totals"]["completed_consumed"] == 13


# ------------------------------------------------------------------ R009


def test_b4_scratch_bounds_authority(tmp_path, monkeypatch, capsys):
    manifest, root, scratch = _campaign(tmp_path / "base", [(None, "B2", FAKE_B2, "SOURCE_REVIEW")])
    caller = _tree(root)
    hashes, calls = [], _spy_verify(monkeypatch)
    real_sha = B2._sha
    monkeypatch.setattr(B2, "_sha", lambda p: (hashes.append(1), real_sha(p))[1])
    full = (tmp_path / "full").resolve()
    full.mkdir()
    (full / "x").write_text("x")
    bad_scratch = {"SCRATCH_INVALID": [Path("relative/scratch"), REPO_ROOT / "b4-scratch", tmp_path / "a" / ".." / "s",
                                       tmp_path / "credentials" / "s"],
                   "SCRATCH_NOT_EMPTY": [full], "INPUT_PATH_UNUSABLE": [root / "case-01" / "s", root]}
    for code, values in bad_scratch.items():
        for value in values:
            assert _run(manifest, root, value) == {"status": "STOPPED", "reason_code": code}, (code, value)
    assert _run(root / "case-01" / "receipt.json", root, scratch)["reason_code"] == "INPUT_PATHS_OVERLAP"
    assert _run(Path("manifest.json"), root, scratch)["reason_code"] == "INPUT_PATH_UNUSABLE"
    assert _run(manifest, Path("ev"), scratch)["reason_code"] == "INPUT_PATH_UNUSABLE"
    big = (tmp_path / "big.json").resolve()
    big.write_bytes(b" " * ((1 << 20) + 1))
    assert _run(big, root, scratch)["reason_code"] == "MANIFEST_UNREADABLE"
    secret = (tmp_path / "secret.json").resolve()
    secret.write_text(json.dumps({"schema_id": NR.MANIFEST_SCHEMA, "cases": [], "note": "sk-" + "a" * 24}))
    assert _run(secret, root, scratch)["reason_code"] == "SECRET_MATERIAL_REJECTED"
    # per-case (native 20000 files / 3 GiB) and aggregate (40000 / 6 GiB) caps hold by lstat, before any hash
    monkeypatch.setattr(B3, "MAX_TOTAL_FILES", 0)
    assert _run(manifest, root, scratch)["reason_code"] == "INPUT_TOO_LARGE"
    monkeypatch.undo()
    hashes, calls = [], _spy_verify(monkeypatch)
    monkeypatch.setattr(B2, "_sha", lambda p: (hashes.append(1), real_sha(p))[1])
    monkeypatch.setattr(CLI, "MAX_TOTAL_FILES", 0)
    assert _run(manifest, root, scratch)["reason_code"] == "INPUT_TOO_LARGE"
    monkeypatch.setattr(CLI, "MAX_TOTAL_FILES", 40000)
    def hardlink(r):
        (r / "case-01" / "inputs" / "a.json").write_bytes(b"{}")
        os.link(r / "case-01" / "inputs" / "a.json", r / "case-01" / "inputs" / "twin.json")
    for name, damage in (("hardlink", hardlink),
                         ("sidecar", lambda r: (r / "case-01" / "inputs" / "x.sqlite3-wal").write_bytes(b"x")),
                         ("secretdir", lambda r: (r / "case-01" / "inputs" / ".ssh").mkdir())):
        m, r, s = _campaign(tmp_path / name, [(None, "B2", FAKE_B2, "SOURCE_REVIEW")])
        damage(r)
        assert _run(m, r, s) == {"status": "STOPPED", "reason_code": "INPUT_TREE_UNSAFE"}, name
    m, r, s = _campaign(tmp_path / "link", [(None, "B2", FAKE_B2, "SOURCE_REVIEW")])
    try:
        os.symlink(r / "case-01" / "receipt.json", r / "case-01" / "inputs" / "link.json")
    except OSError:
        pass  # no symlink privilege on this host: hardlink/reparse coverage above still holds
    else:
        assert _run(m, r, s)["reason_code"] == "INPUT_TREE_UNSAFE"
    assert hashes == [] and calls == []  # every refusal above happened before any byte hash or native verifier
    # the B3 replay Parquet footer is bounded before any hash or nested verifier (native B3 preflight)
    m, r, s = _campaign(tmp_path / "parquet", [(None, "B3", "b3research:sha256:" + "c" * 64, "FULL_SHARED_CASE")])
    shutil.rmtree(r / "case-01" / "parity")
    (r / "case-01" / "inputs" / "replay.parquet").write_bytes(b"PAR1" + b"\0" * 64)
    try:
        import pyarrow.parquet  # noqa: F401
    except Exception as error:  # noqa: BLE001 - application-control hosts block the native library
        print("parquet footer part skipped:", type(error).__name__)
    else:
        assert _run(m, r, s) == {"status": "STOPPED", "reason_code": "REPLAY_FILE_UNUSABLE"} and hashes == [] and calls == []
    # an attempted socket during the native call is blocked and the whole campaign refuses (no partial seal)
    def leak(root):
        socket.create_connection(("192.0.2.1", 443))
    monkeypatch.undo()
    _spy_verify(monkeypatch, leak)
    m, r, s = _campaign(tmp_path / "net", [(None, "B2", FAKE_B2, "SOURCE_REVIEW")])
    assert _run(m, r, s) == {"status": "STOPPED", "reason_code": "NETWORK_ATTEMPT_BLOCKED"}
    assert not (s / "receipt.json").exists() and not (s / CLI.LOCK).exists()
    events = _events(s)  # durable, distinct quarantine: never an ordinary terminal or a clean-interruption record
    assert [(e["event"]["type"], e["event"]["payload"].get("reason")) for e in events] == [
        ("CASE_VERIFY_STARTED", None), ("CASE_VERIFY_QUARANTINED", "NETWORK_ATTEMPT_BLOCKED")]
    monkeypatch.undo()
    assert _resume(s)["status"] == "RESUMED_COMPLETE" and _events(s)[:2] == events  # never retried
    assert _receipt(s)["core"]["cases"][0]["verify"]["reason"] == "NETWORK_ATTEMPT_BLOCKED" and _verify(s)["status"] == "VERIFIED"
    monkeypatch.setattr(CLI, "MAX_EVENT_BYTES", 64)
    m, r, s = _campaign(tmp_path / "event", [(None, "B2", FAKE_B2, "SOURCE_REVIEW")])
    assert _run(m, r, s)["reason_code"] == "JOURNAL_EVENT_TOO_LARGE" and not list((s / "journal").iterdir())
    monkeypatch.undo()
    # usage errors and refusals never echo paths, ids or input text
    for argv in ([], ["run"], ["run", "--manifest", str(manifest)], ["verify"], ["resume", "--bogus", "x"], ["delete"]):
        with pytest.raises(SystemExit) as excinfo:
            CLI.main(argv)
        assert excinfo.value.code == 2
    assert CLI.main(["run", "--manifest", str(manifest), "--evidence-root", str(root), "--scratch-dir", str(REPO_ROOT)]) == 1
    assert CLI.main(["verify", "--scratch-dir", str(tmp_path / "missing")]) == 1
    out = capsys.readouterr().out
    assert str(tmp_path) not in out and FAKE_B2 not in out and "Traceback" not in out
    assert _tree(root) == caller and not scratch.exists()


# ------------------------------------------------------------------ R010


def test_b4_seal_exact_cold_verify(tmp_path, monkeypatch):
    manifest, root, scratch = _campaign(tmp_path / "base", [(None, "B2", FAKE_B2, "FULL_SHARED_CASE"),
                                                            (None, "B2", FAKE_B2[:-1] + "b", "RELATION_REVIEW")])
    assert _run(manifest, root, scratch)["status"] == "RUN_COMPLETE"
    receipt = _receipt(scratch)
    assert _verify(scratch)["status"] == "VERIFIED" and receipt["receipt_id"].startswith(NR.PREFIX["receipt"])
    assert receipt["receipt_id"] == NR.finalize(receipt["core"])["receipt_id"]
    sealed = _tree(scratch)

    def tampered(name, damage):
        target = (tmp_path / name).resolve()
        shutil.copytree(scratch, target)
        damage(target)
        before = _tree(target)
        out = _verify(target)
        assert _tree(target) == before, name  # verify never writes, never repairs
        return out

    def receipt_edit(edit, rehash=True):
        def damage(target):
            value = _receipt(target)
            edit(value)
            if rehash:  # a forger recomputes the id over the forged core
                value["receipt_id"] = NR.finalize(value["core"])["receipt_id"]
            (target / "receipt.json").write_bytes(json.dumps(value, sort_keys=True, indent=1).encode())
        return damage
    FORGED = ["CORE_MISMATCH", "RECEIPT_ID_MISMATCH"]  # a rehashed forged core never matches the recomputed id
    expect = {
        "bool": (receipt_edit(lambda v: v["core"]["totals"].update(failed=False)), FORGED),
        "float": (receipt_edit(lambda v: v["core"]["totals"].update(planned_slots=18.0)), FORGED),
        "reason": (receipt_edit(lambda v: v["core"]["cases"][0]["verify"].update(reason="NOT_A_REAL_REASON")), FORGED),
        "promoted": (receipt_edit(lambda v: v["core"]["cases"][0]["tasks"][0].update(status="COMPLETED_CONSUMED")),
                     FORGED),
        "claims": (receipt_edit(lambda v: v["core"]["claims"].update(nine_functional_agents=True)), FORGED),
        "extra": (receipt_edit(lambda v: v["core"].update(note="x")), FORGED),
        "missing": (receipt_edit(lambda v: v["core"].pop("capability")), FORGED),
        "id": (receipt_edit(lambda v: v.update(receipt_id=NR.PREFIX["receipt"] + "0" * 64), rehash=False), ["RECEIPT_ID_MISMATCH"]),
        "shape": (receipt_edit(lambda v: v.update(extra=1), rehash=False), ["RECEIPT_SHAPE_INVALID"]),
        "schema": (receipt_edit(lambda v: v.update(schema_id="b4-nine-role-receipt-v2"), rehash=False), ["RECEIPT_SCHEMA_INVALID"]),
    }
    for name, (damage, failures) in expect.items():
        assert tampered(name, damage) == {"status": "TAMPER_DETECTED", "failures": failures, "receipt_id": None,
                                          "network_attempts": 0}, name

    def swap(target):
        a, b = target / "journal" / "000003.json", target / "journal" / "000004.json"
        raw_a, raw_b = a.read_bytes(), b.read_bytes()
        a.write_bytes(raw_b)
        b.write_bytes(raw_a)

    def rechain_last(target):  # a false terminal: the forger rewrites the last event and recomputes its id
        path = sorted((target / "journal").iterdir())[-1]
        doc = json.loads(path.read_bytes())
        doc["event"]["payload"]["reason"] = "NOT_REQUESTED"
        path.write_bytes(CLI.SG.canonical_bytes(NR.make_event(doc["event"]["seq"], doc["event"]["prev"], doc["event"]["type"],
                                                              doc["event"]["payload"])))

    def input_byte(target):
        (target / "inputs" / "case-01" / "receipt.json").write_bytes(b"{ }")
    for name, damage, code in (("reorder", swap, "RECOMPUTE_REFUSED:JOURNAL_SEQUENCE_INVALID"),
                               ("whitespace", lambda t: (t / "journal" / "000002.json").write_bytes(
                                   (t / "journal" / "000002.json").read_bytes() + b"\n"), "RECOMPUTE_REFUSED:JOURNAL_EVENT_INVALID"),
                               ("terminal", rechain_last, "RECOMPUTE_REFUSED:JOURNAL_ORDER_INVALID"),
                               ("plan", lambda t: (t / "plan.json").write_bytes(b"{}"), "RECOMPUTE_REFUSED:PLAN_MISMATCH"),
                               ("input", input_byte, "RECOMPUTE_REFUSED:PLAN_MISMATCH"),
                               ("manifest", lambda t: (t / "inputs" / "manifest.json").write_bytes(b"{}"),
                                "RECOMPUTE_REFUSED:MANIFEST_SCHEMA_UNSUPPORTED"),
                               ("reindent", lambda t: (t / "inputs" / "manifest.json").write_bytes(
                                   json.dumps(json.loads((t / "inputs" / "manifest.json").read_bytes()), indent=4).encode()),
                                "RECOMPUTE_REFUSED:PLAN_MISMATCH"),
                               ("reformat", lambda t: (t / "receipt.json").write_bytes(
                                   json.dumps(_receipt(t), sort_keys=True).encode()), "RECEIPT_BYTES_NONCANONICAL")):
        out = tampered(name, damage)
        assert out["status"] == "TAMPER_DETECTED" and out["failures"] == [code], name
    for name, damage in (("alien", lambda t: (t / "notes.txt").write_text("x")),
                         ("noreceipt", lambda t: (t / "receipt.json").unlink())):
        assert tampered(name, damage) == {"status": "STOPPED", "reason_code": "SCRATCH_LAYOUT_INVALID"}, name
    assert _tree(scratch) == sealed and _resume(scratch)["status"] == "SEALED_VERIFIED" and _tree(scratch) == sealed
    _need_pin()
    ev = pinned_evidence()
    # a native receipt edited and rehashed by a forger: B4 never accepts it on a matching hash; the native verifier refuses
    forged = (tmp_path / "forged-tree").resolve()
    shutil.copytree(ev["base"] / "inputs" / "b2-admitted", forged)
    value = json.loads((forged / "receipt.json").read_bytes())
    value["core"]["a6_wallet"]["status"] = "INSUFFICIENT"
    value = RW.finalize(value["core"])
    (forged / "receipt.json").write_bytes(json.dumps(value, sort_keys=True, indent=1).encode())
    manifest, root, scratch2 = _campaign(tmp_path / "forged", [(forged, "B2", value["receipt_id"], "FULL_SHARED_CASE")])
    assert _run(manifest, root, scratch2)["status"] == "RUN_COMPLETE"
    case = _receipt(scratch2)["core"]["cases"][0]
    assert (case["verify"]["status"], case["verify"]["reason"]) == ("REFUSED", "NATIVE_VERIFY_REFUSED")
    assert case["counts"]["completed_consumed"] == 0
    # a delivered projection forged in the sealed receipt is caught by the native recomputation
    manifest, root, scratch3 = _campaign(tmp_path / "real", [(ev["base"] / "inputs" / "b3", "B3", ev["b3"], "FULL_SHARED_CASE")])
    assert _run(manifest, root, scratch3)["status"] == "RUN_COMPLETE"
    scratch = scratch3
    assert tampered("projection", receipt_edit(lambda v: v["core"]["cases"][0]["tasks"][6]["projection"].update(
        native_status="ADMITTED")))["failures"] == FORGED
    assert tampered("native", receipt_edit(lambda v: v["core"]["cases"][0]["tasks"][5].update(native_status="REFUSED")))[
        "failures"] == FORGED
