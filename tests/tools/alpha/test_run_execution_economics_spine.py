"""S10-CAP-EXEC-ECONOMICS-01 R007-R010/R012: B3 operator over a real pinned B2 receipt and the native producers.

The pinned parts need a complete B2 run, whose B1-A spine needs the exact pinned Hermes checkout
(``POLYMARKET_HERMES_PIN_ROOT``); without it they skip with a reason (hosted CI: D001) and every unpinned guard
still runs. The replay parts need pyarrow + nautilus_trader native libraries; a host whose application-control
policy blocks them skips only those parts (the Linux container and hosted CI run them).
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import socket

import pytest

from src.data_layer.analytical_research import execution_economics_spine as XE
from tests.data_layer.analytical_research import test_execution_economics_spine as X
from tests.data_layer.analytical_research import test_relation_wallet_spine as T
from tests.data_layer.analytical_research import test_source_forecast_spine as B1
from tests.tools.alpha import test_run_relation_wallet_spine as B2T
from tools.alpha import run_execution_economics_spine as CLI
from tools.alpha import run_oracle3_upstream_parity as PAR
from tools.alpha import run_related_market_alpha as REL
from tools.alpha import run_relation_wallet_spine as B2
from tools.alpha import run_source_forecast_spine as B1A

PIN = os.environ.get("POLYMARKET_HERMES_PIN_ROOT")
REPO_ROOT = Path(__file__).resolve().parents[3]
B2_CODE_IDENTITY_AT_BASE = "code:sha256:9ccd7b6c003293fb74b3bcb4d88c90cdf3f38770e09d49cb8428630486fade0a"  # merged 55fee02
WP_PATHS = {
    "src/data_layer/analytical_research/execution_economics_spine.py", "tools/alpha/run_execution_economics_spine.py",
    "tests/data_layer/analytical_research/test_execution_economics_spine.py",
    "tests/tools/alpha/test_run_execution_economics_spine.py", "docs/execution_economics_spine_contract.md",
    "docs/deferred_items_log.md", "docs/project_status.md", "docs/repo_truth_index.md",
    "docs/status_entries/S10-CAP-EXEC-ECONOMICS-01.md", "docs/wp_specs/S10-CAP-EXEC-ECONOMICS-01/wp_prompt.txt",
    "docs/wp_specs/S10-CAP-EXEC-ECONOMICS-01/wp_spec.json"}


def _need_pin():
    if not PIN:
        pytest.skip("POLYMARKET_HERMES_PIN_ROOT not set: exact pinned Hermes checkout absent (pinned part only, D001)")


def _tree(root: Path) -> dict:
    return B2T._tree(root)


def _run(**kw) -> dict:
    return CLI.run_safe(type("Args", (), dict(command="run", replay_file=None, **kw))())


def _verify(scratch: Path) -> dict:
    return CLI.run_safe(type("V", (), dict(command="verify", scratch_dir=scratch))())


def _write(directory: Path, name: str, value) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = (directory / name).resolve()
    path.write_bytes(value if isinstance(value, bytes) else json.dumps(value).encode("utf-8"))
    return path


class _Sockets:
    """A spy beneath the operator's own socket block: any attempt is recorded."""

    def __init__(self, monkeypatch):
        self.calls = []
        monkeypatch.setattr(socket.socket, "connect", lambda s, *a, **k: self.calls.append("connect"))
        monkeypatch.setattr(socket, "create_connection", lambda *a, **k: self.calls.append("create_connection"))


@pytest.fixture(scope="module")
def world(tmp_path_factory):
    return X.build_b3_world(tmp_path_factory.mktemp("b3_tools_world"))


@pytest.fixture(scope="module")
def pinned(world, tmp_path_factory):
    """One real B1-A spine run through the exact pin and one complete B2 run over it (existing builders only)."""
    if not PIN:
        return None
    base = tmp_path_factory.mktemp("b3_pinned")
    grounding_world = world["world"]
    registry = (base / "registry.sqlite3").resolve()
    shutil.copyfile(grounding_world["registry"], registry)
    spine_case = _write(base, "spine.json", B1.spine_case(grounding_world))
    fc = _write(base, "fc.json", B1.forecast_cases(grounding_world))
    spine = (base / "spine-scratch").resolve()
    spine_result = B1A.run(spine_case, grounding_world["grounding"], fc, registry, spine, Path(PIN))
    assert spine_result["status"] == "RUN_COMPLETE"
    b2_case = _write(world["ledger"]["base"], "b3-b2-case.json",
                     T.b2_case(spine_result["receipt_id"], world["rel"]["receipt_id"], world["ledger"]))
    scratch = (base / "b2-scratch").resolve()
    result = B2.run(spine, registry, world["rel_scratch"], world["ledger"]["path"], b2_case, scratch)
    assert result["status"] == "RUN_COMPLETE"
    receipt = json.loads((scratch / "receipt.json").read_bytes())
    case = X.probe_case(dict(world, core=receipt["core"]), b2_receipt_id=receipt["receipt_id"])
    return {"base": base, "scratch": scratch, "receipt": receipt, "case": case, "spine_receipt_id": spine_result["receipt_id"]}


@pytest.fixture(scope="module")
def sealed(pinned, tmp_path_factory):
    """One write-once B3 run over the pinned B2 scratch (replay null) and its caller-input hashes."""
    if pinned is None:
        return None
    base = tmp_path_factory.mktemp("b3_sealed")
    case = _write(base / "case", "b3-case.json", pinned["case"])
    before = {"b2": _tree(pinned["scratch"]), "case": hashlib.sha256(case.read_bytes()).hexdigest()}
    calls = []
    real_connect, real_create = socket.socket.connect, socket.create_connection
    socket.socket.connect = lambda self, *a, **k: calls.append("connect")
    socket.create_connection = lambda *a, **k: calls.append("create_connection")
    try:
        result = _run(b2_scratch=pinned["scratch"], case=case, scratch_dir=(base / "b3").resolve())
    finally:
        socket.socket.connect, socket.create_connection = real_connect, real_create
    return {"base": base, "case": case, "scratch": (base / "b3").resolve(), "result": result, "calls": calls,
            "before": before, "receipt": json.loads(((base / "b3") / "receipt.json").read_bytes())
            if ((base / "b3") / "receipt.json").is_file() else None}


def _fake_b2(base: Path) -> Path:
    """A plain caller directory standing in for a B2 scratch: path/schema guards stop before any B2 verify."""
    root = (base / "fake-b2").resolve()
    root.mkdir(parents=True, exist_ok=True)
    (root / "receipt.json").write_bytes(b"{}")
    return root


# ------------------------------------------------------------------ R007


def test_b3_pinned_b2_to_a7_handoff(world, pinned, sealed):
    _need_pin()
    result, receipt = sealed["result"], sealed["receipt"]
    assert result["status"] == "RUN_COMPLETE" and result["network_attempts"] == 0 and sealed["calls"] == []
    assert result["receipt_id"] == receipt["receipt_id"] and result["a7"] == "PARTIAL" and result["point"] == "FEASIBLE"
    assert result["replay"] == "NOT_SUPPLIED"
    checked = _verify(sealed["scratch"])
    assert checked == {"status": "VERIFIED", "failures": [], "receipt_id": receipt["receipt_id"], "network_attempts": 0}
    core, b2_core = receipt["core"], pinned["receipt"]["core"]
    lineage = core["b2_lineage"]
    # the real pinned B2 / B1-A / A5 / A6 identities flow through unchanged; no new candidate or provider
    assert lineage["b2_receipt_id"] == pinned["receipt"]["receipt_id"] and lineage["b2_code_identity"] == b2_core["code_identity"]
    assert lineage["b1a"]["spine_receipt_id"] == pinned["spine_receipt_id"] == b2_core["b1a_lineage"]["spine_receipt_id"]
    assert lineage["target"] == b2_core["shared_case"]["target"]
    assert lineage["a5"]["rel_receipt_id"] == b2_core["a5_relations"]["rel_receipt_id"] == world["rel"]["receipt_id"]
    assert lineage["a5"]["denominators"] == b2_core["a5_relations"]["denominators"]
    assert lineage["a6"]["status"] == b2_core["a6_wallet"]["status"]
    # B2 leg -> native REL snapshot -> native EF assessment, recomputed here with direct native calls
    selected, bound = X.bind(dict(world, core=b2_core), pinned["case"])
    intent, assessment, point = XE.assess_point(pinned["case"], bound["snapshot"], X.DECISION_NS)
    assert core["point_mechanics"] == json.loads(json.dumps(point))
    assert lineage["venue_snapshot_id"] == selected["leg"]["venue_snapshot_id"] == point["venue_snapshot_id"]
    assert core["point_mechanics"]["status"] in ("FEASIBLE", "LIMITED")
    # native outputs drive the A7 reasons; replay absent is explicit, never scanned for or defaulted
    assert "POINT_MECHANICS_" + point["status"] in core["a7_role"]["reasons"]
    assert core["replay_diagnostic"] == XE.not_supplied() and core["trace"][-1] == "execution_feasibility assess"
    assert _tree(pinned["scratch"]) == sealed["before"]["b2"]
    assert hashlib.sha256(sealed["case"].read_bytes()).hexdigest() == sealed["before"]["case"]


# ------------------------------------------------------------------ R008


def test_b3_historical_receipts_and_scope(world, pinned, sealed):
    # native producer code identities are the merged-base values (this WP edits none of them)
    for name, (module, identity) in B2T.NATIVE_IDENTITIES.items():
        assert module.code_identity() == identity, name
    assert B2.code_identity() == B2_CODE_IDENTITY_AT_BASE
    for rel in ("tools/alpha/run_relation_wallet_spine.py", "tools/alpha/run_related_market_alpha.py",
                "tools/alpha/run_oracle3_upstream_parity.py", "tools/alpha/run_source_forecast_spine.py",
                "src/data_layer/analytical_research/relation_wallet_spine.py",
                "src/data_layer/analytical_research/source_forecast_spine.py",
                "src/execution_feasibility/evaluator.py", "src/execution_feasibility/models.py",
                "src/research_runtime/executable_edge/evaluator.py", "src/research_runtime/executable_edge/models.py",
                "src/research_runtime/executable_edge/market_truth.py", "src/research_runtime/executable_edge/persistence.py",
                "src/paper_trading/models.py", "src/data_layer/analytical_research/pmxt_v2.py",
                "src/data_layer/analytical_research/experiment_os.py"):
        assert "execution_economics_spine" not in (REPO_ROOT / rel).read_text(encoding="utf-8"), rel
    # the native REL and Oracle3 receipts still cold-verify with identical ids and bytes after B3 consumption
    before = {k: _tree(world[k]) for k in ("rel_scratch", "parity_scratch")}
    assert REL.verify(world["rel_scratch"])["receipt_id"] == world["rel"]["receipt_id"]
    assert PAR.verify(world["parity_scratch"])["receipt_id"] == world["parity"]["receipt_id"]
    assert {k: _tree(world[k]) for k in before} == before
    # exact 11-path frozen scope; the B2 spec and the roadmap CSV are untouched
    spec = json.loads((REPO_ROOT / "docs" / "wp_specs" / XE.WP_ID / "wp_spec.json").read_text(encoding="utf-8"))
    paths = spec["scope"]["required_changed_files"]
    assert len(paths) == 11 == len(set(paths)) and set(paths) == WP_PATHS and paths == spec["scope"]["allowed_changed_files"]
    b2_spec = json.loads((REPO_ROOT / "docs" / "wp_specs" / "S10-CAP-B2-RELATIONS-WALLET-01" / "wp_spec.json").read_text(encoding="utf-8"))
    assert len(b2_spec["scope"]["required_changed_files"]) == 11
    raw = X.CSV.read_bytes()
    assert X.CSV_SHA256 in (hashlib.sha256(raw).hexdigest(), hashlib.sha256(raw.replace(b"\r\n", b"\n")).hexdigest())
    for name in ("test_execution_economics_spine.py", "test_run_execution_economics_spine.py"):
        assert len(list((REPO_ROOT / "tests").rglob(name))) == 1, name
    _need_pin()
    # the real pinned B2 receipt cold-verifies again with the identical id and bytes after the B3 run
    tree = _tree(pinned["scratch"])
    checked = B2.verify(pinned["scratch"])
    assert checked["status"] == "VERIFIED" and checked["receipt_id"] == pinned["receipt"]["receipt_id"]
    assert _tree(pinned["scratch"]) == tree == sealed["before"]["b2"]
    frozen = sealed["scratch"] / "inputs" / "b2"
    assert _tree(frozen) == tree  # sealed copy is byte-identical, no migrated receipt or identity alias
    assert pinned["receipt"]["core"]["a5_relations"]["parity_code_identity"] == B2T.NATIVE_IDENTITIES["PAR"][1]


# ------------------------------------------------------------------ R009


def test_b3_paths_schema_bounds_and_no_echo(world, tmp_path, monkeypatch, capsys):
    fake = _fake_b2(tmp_path)
    case_value = X.probe_case(world)
    CLI.parse_case(json.dumps(case_value).encode())  # positive: native fee/leg/intent/condition words are allowed
    case = _write(tmp_path / "case", "case.json", case_value)
    out = lambda name: (tmp_path / name).resolve()  # noqa: E731
    secret_dir = tmp_path / ".ssh"
    secret_dir.mkdir()
    secret_case = _write(secret_dir, "case.json", case_value)
    twin = tmp_path / "twin.json"
    shutil.copyfile(case, twin)
    linked = tmp_path / "hard.json"
    os.link(twin, linked)
    path_rows = {
        "INPUT_PATH_UNUSABLE:b2": [dict(b2_scratch=Path("relative"), case=case), dict(b2_scratch=REPO_ROOT / "docs", case=case),
                                   dict(b2_scratch=fake / ".." / "fake-b2", case=case)],
        "INPUT_PATH_UNUSABLE:case": [dict(b2_scratch=fake, case=secret_case), dict(b2_scratch=fake, case=linked.resolve()),
                                     dict(b2_scratch=fake, case=REPO_ROOT / "docs" / "wp_specs" / XE.WP_ID / "wp_spec.json"),
                                     dict(b2_scratch=fake, case=tmp_path / "missing.json")],
        "INPUT_PATHS_OVERLAP": [dict(b2_scratch=fake, case=fake / "receipt.json")],
    }
    for code, rows in path_rows.items():
        for number, kw in enumerate(rows):
            assert _run(**kw, scratch_dir=out(f"p-{code[:5]}-{number}")) == {"status": "STOPPED", "reason_code": code}, (code, number)
    if hasattr(os, "symlink"):
        try:
            (tmp_path / "sym.json").symlink_to(case)
        except OSError:
            pass
        else:
            assert _run(b2_scratch=fake, case=tmp_path / "sym.json", scratch_dir=out("sym"))["reason_code"] == "INPUT_PATH_UNUSABLE:case"
    # strict JSON and closed schema, refused before any byte is hashed
    hashed = []
    real_sha = B2._sha
    monkeypatch.setattr(B2, "_sha", lambda p: (hashed.append(1), real_sha(p))[1])
    raw_rows = {
        "CASE_JSON_INVALID": [b'{"a": 1, "a": 2}', b'{"x": NaN}', b"\xff", b"[1"],
        "CASE_UNREADABLE": [b""],
        "SECRET_MATERIAL_REJECTED": [json.dumps(dict(case_value, model_id="sk-" + "a" * 20)).encode()],
        "CASE_FIELDS_INVALID": [json.dumps(dict(case_value, extra=None)).encode(), b"{}"],
        "FORBIDDEN_FIELD": [json.dumps(dict(case_value, probe_intent=dict(case_value["probe_intent"], passphrase="x"))).encode()],
        "REPLAY_FIELDS_INVALID": [json.dumps(dict(case_value, replay=0)).encode(), json.dumps(dict(case_value, replay=[])).encode()],
        "LEG_SIDE_INVALID": [json.dumps(dict(case_value, leg_side=1)).encode()],
    }
    for code, raws in raw_rows.items():
        for number, raw in enumerate(raws):
            row_case = _write(tmp_path / f"c-{code}-{number}", "case.json", raw)
            assert _run(b2_scratch=fake, case=row_case, scratch_dir=out(f"r-{code}-{number}")) == {
                "status": "STOPPED", "reason_code": code}, (code, number)
    big = _write(tmp_path / "big", "case.json", b" " * (CLI.MAX_CASE_BYTES + 1))
    assert _run(b2_scratch=fake, case=big, scratch_dir=out("bigrun"))["reason_code"] == "CASE_UNREADABLE"
    # replay is an explicit null with no path; an unexpected or missing replay path refuses
    replay_value = {"parquet_sha256": "0" * 64, "known_gap_policy": "AS_CAPTURED", **{k: {} for k in (
        "context", "experiment", "evidence", "cost_model", "decision_event")}}
    with_replay = _write(tmp_path / "wr", "case.json", dict(case_value, replay=replay_value))
    parquet = _write(tmp_path / "pq", "x.parquet", b"PAR1")
    assert _run(b2_scratch=fake, case=with_replay, scratch_dir=out("m1"))["reason_code"] == "REPLAY_FILE_CASE_MISMATCH"
    assert CLI.run_safe(type("A", (), dict(command="run", b2_scratch=fake, case=case, replay_file=parquet,
                                           scratch_dir=out("m2")))())["reason_code"] == "REPLAY_FILE_CASE_MISMATCH"
    big_pq = _write(tmp_path / "bigpq", "x.parquet", b"0" * (CLI.MAX_PARQUET_BYTES + 1))
    assert CLI.run_safe(type("A", (), dict(command="run", b2_scratch=fake, case=with_replay, replay_file=big_pq,
                                           scratch_dir=out("m3")))())["reason_code"] == "REPLAY_FILE_UNUSABLE"
    # aggregate tree caps and SQLite sidecars by lstat before hashing
    (fake / "ledger.sqlite3-wal").write_bytes(b"")
    assert _run(b2_scratch=fake, case=case, scratch_dir=out("side"))["reason_code"] == "INPUT_TREE_UNSAFE"
    (fake / "ledger.sqlite3-wal").unlink()
    monkeypatch.setattr(CLI, "MAX_TOTAL_FILES", 1)
    (fake / "second.bin").write_bytes(b"1")
    assert _run(b2_scratch=fake, case=case, scratch_dir=out("cap"))["reason_code"] == "INPUT_TOO_LARGE"
    (fake / "second.bin").unlink()
    assert hashed == []
    monkeypatch.undo()
    # a real run over a non-B2 tree stops at the nested B2 verifier; zero sockets, no echo of any caller value
    spy = _Sockets(monkeypatch)
    stopped = _run(b2_scratch=fake, case=case, scratch_dir=out("nob2"))
    assert stopped["status"] == "STOPPED" and spy.calls == []
    capsys.readouterr()
    for argv in (["run", "--case", "sk-" + "b" * 24], ["nope"], [], ["verify"]):
        with pytest.raises(SystemExit) as excinfo:
            CLI.main(argv)
        assert excinfo.value.code == 2
        printed = capsys.readouterr().out
        assert json.loads(printed) == {"status": "USAGE_ERROR", "reason_code": "USAGE_INVALID"} and "sk-" not in printed
    assert CLI.main(["run", "--b2-scratch", str(fake), "--case", str(case), "--scratch-dir", str(out("echo"))]) == 1
    printed = capsys.readouterr().out
    assert str(tmp_path) not in printed and "Traceback" not in printed and set(json.loads(printed)) == {"status", "reason_code"}


# ------------------------------------------------------------------ R010


def test_b3_write_once_exact_cold_verify(world, pinned, sealed, tmp_path):
    fake, case = _fake_b2(tmp_path), _write(tmp_path / "case", "case.json", X.probe_case(world))
    busy = (tmp_path / "busy").resolve()
    busy.mkdir()
    (busy / "x").write_bytes(b"1")
    assert _run(b2_scratch=fake, case=case, scratch_dir=busy) == {"status": "STOPPED", "reason_code": "SCRATCH_NOT_EMPTY"}
    for bad in (REPO_ROOT / "b3-scratch", Path("relative")):
        assert _run(b2_scratch=fake, case=case, scratch_dir=bad)["reason_code"] == "SCRATCH_INVALID"
    # a stop after freezing leaves a partial scratch that is never reused nor verified
    partial = (tmp_path / "partial").resolve()
    assert _run(b2_scratch=fake, case=case, scratch_dir=partial)["status"] == "STOPPED"
    assert _run(b2_scratch=fake, case=case, scratch_dir=partial)["reason_code"] == "SCRATCH_NOT_EMPTY"
    assert _verify(partial)["status"] in ("STOPPED", "TAMPER_DETECTED") and _verify(partial).get("receipt_id") is None
    assert _verify((tmp_path / "missing").resolve())["status"] == "STOPPED"
    _need_pin()
    scratch, receipt = sealed["scratch"], sealed["receipt"]
    assert _run(b2_scratch=pinned["scratch"], case=sealed["case"], scratch_dir=scratch)["reason_code"] == "SCRATCH_NOT_EMPTY"
    # relocation keeps the same id and bytes; verify writes nothing
    moved = (tmp_path / "relocated").resolve()
    shutil.copytree(scratch, moved)
    tree = _tree(moved)
    assert _verify(moved)["receipt_id"] == receipt["receipt_id"] and _tree(moved) == tree

    def tampered(name: str, mutate) -> dict:
        copy_dir = (tmp_path / name).resolve()
        shutil.copytree(scratch, copy_dir)
        mutate(copy_dir)
        result = _verify(copy_dir)
        assert result["receipt_id"] is None and result["status"] in ("TAMPER_DETECTED", "STOPPED"), name
        return result

    def receipt_edit(fn):
        def mutate(d):
            value = json.loads((d / "receipt.json").read_bytes())
            fn(value)
            (d / "receipt.json").write_text(json.dumps(value), encoding="utf-8")
        return mutate

    def rehashed(fn):
        def edit(value):
            fn(value["core"])
            value["receipt_id"] = XE.finalize(value["core"])["receipt_id"]
        return receipt_edit(edit)

    assert tampered("t-core", rehashed(lambda c: c["a7_role"].update(overall="ECONOMICS_SUPPORTED")))["failures"] == [
        "CORE_MISMATCH", "RECEIPT_ID_MISMATCH"]
    assert tampered("t-null", rehashed(lambda c: c.update(caller_note=None)))["failures"] == ["CORE_MISMATCH", "RECEIPT_ID_MISMATCH"]
    assert tampered("t-bool", rehashed(lambda c: c["authority"].update(advisory_only=1)))["failures"] == [
        "CORE_MISMATCH", "RECEIPT_ID_MISMATCH"]
    assert tampered("t-id", receipt_edit(lambda v: v.update(receipt_id=XE.RECEIPT_PREFIX + "0" * 64)))["failures"] == [
        "RECEIPT_ID_MISMATCH"]
    assert tampered("t-schema", receipt_edit(lambda v: v.update(schema_id="other")))["failures"] == ["RECEIPT_SCHEMA_INVALID"]
    assert tampered("t-shape", receipt_edit(lambda v: v.update(extra=1)))["failures"] == ["RECEIPT_SHAPE_INVALID"]
    assert tampered("t-list", receipt_edit(lambda v: v.update(core=[])))["failures"] == ["RECEIPT_FIELDS_INVALID"]
    assert tampered("t-case", lambda d: (d / "inputs" / "case.json").write_text(
        json.dumps(dict(pinned["case"], model_id="b2-absent")), encoding="utf-8"))["failures"] == [
        "RECOMPUTE_REFUSED:MODEL_NOT_SELECTED_IN_B2"]
    assert tampered("t-b2", lambda d: (d / "inputs" / "b2" / "receipt.json").write_bytes(b"{}"))["failures"][0].startswith(
        "RECOMPUTE_REFUSED:")
    assert tampered("t-replay", lambda d: (d / "inputs" / "replay.parquet").write_bytes(b"PAR1"))["failures"] == [
        "RECOMPUTE_REFUSED:REPLAY_FILE_CASE_MISMATCH"]

    def hardlink(d):
        member = d / "inputs" / "case.json"
        B2T._hardlink_twin(member, d / "twin.json")
    assert tampered("t-hard", hardlink)["failures"] == ["RECOMPUTE_REFUSED:CASE_UNREADABLE"]


# ------------------------------------------------------------------ R012


def test_b3_optional_replay_disposition_and_denominator(world, tmp_path, monkeypatch):
    case = X.probe_case(world)
    selected, bound = X.bind(world, case)
    point = XE.assess_point(case, bound["snapshot"], X.DECISION_NS)[2]
    absent = XE.not_supplied()
    assert absent == dict.fromkeys(XE.REPLAY_FIELDS, None) | {"status": "NOT_SUPPLIED"}
    role = XE.a7_role(point, absent, selected)
    assert role["denominators"] == {"requested_cases": 1, "selected_legs": 1, "point_evaluated": 1, "point_refused": 0,
                                    "replay_attempted": 0, "replay_evaluated": 0, "paper_admission_refused": 0,
                                    "terminal_dispositions": 1}
    assert role["b4_handoff"] == "READ_ONLY_TYPED_RECEIPT" and "WP173_NOT_ATTEMPTED_NO_REPLAY" in role["reasons"]
    X.replay_deps()
    replay, path = X.replay_case(world, tmp_path / "rp")
    diagnostic = X.run_replay(world, replay, path)
    supplied = XE.a7_role(point, diagnostic, selected)
    assert supplied["overall"] == "PARTIAL" and supplied["replay_status"] == "DIAGNOSTIC_ONLY_NATIVE"
    assert {k: supplied["denominators"][k] for k in ("replay_attempted", "replay_evaluated", "paper_admission_refused",
                                                       "terminal_dispositions")} == dict.fromkeys(
        ("replay_attempted", "replay_evaluated", "paper_admission_refused", "terminal_dispositions"), 1)
    assert "REPLAY_DIAGNOSTIC_ONLY_CONTINUITY_INCOMPLETE" in supplied["reasons"] and "WP173_ADMISSION_REFUSED" in supplied["reasons"]
    assert diagnostic["source"]["row_count"] == 3 and diagnostic["window"]["continuity_complete"] is False
    ledger = XE.capability_ledger(world["core"], point, diagnostic)
    assert ledger["touched"]["R3-09-BOOK_GAPS"]["native_consumer_evidence"] == "WP167_168_172_SYNTHETIC_KNOWN_GAP_DIAGNOSTIC"
    # footer-declared bounds refuse before any native WP167 parse
    assert CLI._parquet_bounds(path) is None
    (tmp_path / "bad.parquet").write_bytes(b"PAR1 not a parquet footer PAR1")
    with pytest.raises(XE.ExecutionEconomicsStop, match="REPLAY_FILE_UNUSABLE"):
        CLI._parquet_bounds(tmp_path / "bad.parquet")
    monkeypatch.setattr(XE, "MAX_REPLAY_ROWS", 2)
    with pytest.raises(XE.ExecutionEconomicsStop, match="REPLAY_ROWS_OUT_OF_BOUNDS"):
        CLI._parquet_bounds(path)
    monkeypatch.undo()
    monkeypatch.setattr(CLI, "MAX_PARQUET_UNCOMPRESSED", 1)
    with pytest.raises(XE.ExecutionEconomicsStop, match="REPLAY_UNCOMPRESSED_TOO_LARGE"):
        CLI._parquet_bounds(path)
    monkeypatch.undo()
    # the operator's replay branch end to end over a sealed scratch. B2 cold verify itself needs the pin (R007/R010),
    # so here ONLY the nested B2 verifier is replaced by a recorder; every B3 step after it is the real code.
    scratch = (tmp_path / "b3").resolve()
    b2_dir = scratch / "inputs" / "b2"
    shutil.copytree(world["rel_scratch"], b2_dir / "inputs" / "rel")
    receipt = XE.json.loads(XE.SG.canonical_bytes({"schema_id": "s10-cap-b2", "receipt_id": "b2research:sha256:" + "1" * 64,
                                                   "core": world["core"]}))
    (b2_dir / "receipt.json").write_text(json.dumps(receipt), encoding="utf-8")
    (scratch / "inputs" / "case.json").write_text(json.dumps(dict(case, replay=replay)), encoding="utf-8")
    shutil.copyfile(path, scratch / "inputs" / "replay.parquet")
    seen = []
    monkeypatch.setattr(B2, "verify", lambda d: (seen.append(Path(d)), {"status": "VERIFIED", "receipt_id": receipt["receipt_id"]})[1])
    result = CLI.compute(scratch)
    assert seen == [b2_dir] and result["replay"] == "DIAGNOSTIC_ONLY_NATIVE" and result["a7"] == "PARTIAL"
    core = result["core"]
    assert core["replay_diagnostic"] == json.loads(json.dumps(diagnostic)) and core["trace"][-1] == "WP173 binding refusal"
    assert set(core["input_sha256"]) == {"b2", "case", "replay"}
    (scratch / "inputs" / "replay.parquet").write_bytes(path.read_bytes()[:-8] + b"\0" * 8)
    with pytest.raises(XE.ExecutionEconomicsStop):  # tampered sealed replay bytes refuse (footer or digest), never ignored
        CLI.compute(scratch)
