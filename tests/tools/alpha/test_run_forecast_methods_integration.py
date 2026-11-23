"""S10-CAP-B1-METHODS-01 operator tests: the real CLI, version-aware legacy compatibility, write-once replay, register.

Same frozen SANITIZED_SYNTHETIC world as the forecast evaluation tests. No network, provider or canonical write.
"""
# ruff: noqa: F811 - pytest fixtures imported from the forecast evaluation tests are re-used as parameters
from __future__ import annotations

import ast
import csv
from decimal import Decimal
import json
from pathlib import Path
import shutil
import socket
import subprocess
import sys

import pytest

from src.data_layer.analytical_research import forecast_evaluation as FE
from src.data_layer.analytical_research import forecast_methods_integration as FMI
from src.data_layer.analytical_research import source_forecast_spine as SP
from tests.data_layer.analytical_research.test_forecast_methods_integration import (  # noqa: F401 - module fixtures
    bound_forecast, methods_doc,
)
from tests.tools.alpha.test_forecast_evaluation import baseline, world  # noqa: F401 - module fixtures
from tests.tools.alpha.test_forecast_wp170_binding import (  # noqa: F401 - module fixtures
    LEGACY_V2_COMMIT, full_registry, grounding, legacy, legacy_v2, nm,
)
from tools.alpha import run_forecast_evaluation as FCLI
from tools.alpha import run_forecast_methods_integration as CLI

REPO_ROOT = Path(__file__).resolve().parents[3]
ENTRY = str(REPO_ROOT / "tools" / "alpha" / "run_forecast_methods_integration.py")
ROADMAP = REPO_ROOT / "docs" / "roadmaps" / "nine_agent_capability_first_20261117"
SPEC = REPO_ROOT / "docs" / "wp_specs" / "S10-CAP-B1-METHODS-01" / "wp_spec.json"


def _stdout(capsys):
    return json.loads(capsys.readouterr().out.strip().splitlines()[-1])


def _run(tmp_path, forecast_scratch, methods, name="m"):
    path = tmp_path / f"{name}-methods.json"
    path.write_text(json.dumps(methods), encoding="utf-8")
    scratch = (tmp_path / name).resolve()
    code = CLI.main(["run", "--forecast-scratch", str(forecast_scratch), "--methods", str(path), "--scratch-dir", str(scratch)])
    receipt_path = scratch / "receipt.json"
    return code, scratch, json.loads(receipt_path.read_text(encoding="utf-8")) if receipt_path.exists() else None


@pytest.fixture(scope="module")
def methods_run(bound_forecast, tmp_path_factory):
    scratch, receipt = bound_forecast
    code, mscratch, mreceipt = _run(tmp_path_factory.mktemp("b1b_methods"), scratch, methods_doc(receipt["receipt_id"]))
    assert code == 0, mreceipt
    return mscratch, mreceipt


# ------------------------------------------------------------------ R006


def test_native_evaluator_consumes_method_probability_opt_in(bound_forecast, methods_run, tmp_path, monkeypatch):
    fscratch, freceipt = bound_forecast
    calls = []
    real = FCLI.verify
    monkeypatch.setattr(FCLI, "verify", lambda d: calls.append(Path(d)) or real(d))
    code, scratch, receipt = _run(tmp_path, fscratch, methods_doc(freceipt["receipt_id"]))
    assert code == 0
    # the caller's forecast scratch and then the frozen copy are both actually cold-verified
    assert calls[0] == fscratch and calls[1] == scratch / "inputs" / "forecast"
    core = receipt["core"]
    assert receipt["receipt_id"].startswith(FMI.RECEIPT_PREFIX) and core["schema_id"] == FMI.RECEIPT_SCHEMA
    assert core["code_identity"] == CLI.code_identity() and core["caller"] == FMI.CALLER
    assert receipt == methods_run[1] or receipt["receipt_id"] == methods_run[1]["receipt_id"]
    # the candidate is scored by the native score_one on the predeclared native cohort (recomputed here)
    frozen = json.loads((fscratch / "frozen_cases.json").read_text(encoding="utf-8"))
    labels = {t["case_id"]: (1 if t["outcome"]["label"] == "Yes" else 0) for t in frozen["targets"] if t["outcome"]}
    per_case = core["scoring"]["per_case"]
    assert per_case
    for c, scores in per_case.items():
        mine = FE.score_one(Decimal(core["candidate_p_yes"][c]), labels[c])
        assert scores[FMI.CANDIDATE_ID]["brier"] == FE._q(mine["brier"])
        native = FE.score_one(Decimal(freceipt["core"]["forecasts"][c]["methods"][FE.WANG]["p_yes"]), labels[c])
        assert scores[FE.WANG]["log_loss"] == FE._q(native["log_loss"])
    assert core["scoring"]["denominators"]["selected"] == freceipt["core"]["cohort"]["denominators"]["selected"]
    # separate versioned receipt; the forecast receipt itself is untouched and still verifies
    assert FCLI.verify(fscratch)["status"] == "VERIFIED"
    assert json.loads((fscratch / "receipt.json").read_text(encoding="utf-8")) == freceipt
    # never an A3 child probability, qualified strategy, confirmed edge or OOS release
    a = core["authority"]
    assert a["candidate_is_a3_child_probability"] is False and a["qualification_claim"] is False
    assert a["oos_release"] is False and a["wp170_run_evidence_receipt"] is False and a["real_value_verified"] is False
    text = json.dumps(receipt)
    for word in ("CONFIRMED_EDGE", "QUALIFIED_STRATEGY", "VALUE_VERIFIED\"", "OOS_RELEASED"):
        assert word not in text
    assert core["sampler"]["wp170"]["oos_release"] == "NOT_RELEASED"


# ------------------------------------------------------------------ R008


def test_legacy_v1_v2_receipts_and_b1a_compatibility(baseline, legacy, legacy_v2, bound_forecast, tmp_path, capsys):
    # historical v1 (c249409) and v2 (0d5ddfa) receipts cold-verify unchanged with their pinned identities
    for name in ("unbound", "bound"):
        for runs, identity, schema in ((legacy, FE.LEGACY_V1_CODE_IDENTITY, FE.LEGACY_RECEIPT_SCHEMA),
                                       (legacy_v2, FE.LEGACY_V2_CODE_IDENTITY, FE.RECEIPT_SCHEMA)):
            lscratch, lreceipt, _ = runs[name]
            assert (lreceipt["core"]["schema_id"], lreceipt["core"]["code_identity"]) == (schema, identity)
            proc = subprocess.run([sys.executable, "-B", str(REPO_ROOT / "tools" / "alpha" / "run_forecast_evaluation.py"),
                                   "verify", "--scratch-dir", str(lscratch)], capture_output=True, text=True, timeout=600)
            assert proc.returncode == 0 and json.loads(proc.stdout) == {
                "status": "VERIFIED", "failures": [], "receipt_id": lreceipt["receipt_id"], "network_attempts": 0}
    # the default run is unchanged apart from the code identity it honestly stamps
    current, old = baseline[1]["core"], legacy_v2["unbound"][1]["core"]
    assert current["code_identity"] == FCLI.code_identity() != old["code_identity"]
    assert {k: v for k, v in current.items() if k != "code_identity"} == {k: v for k, v in old.items() if k != "code_identity"}
    # WP170 split membership of the sealed legacy v2 bound receipt equals the current one
    assert legacy_v2["bound"][1]["core"]["wp170"] == bound_forecast[1]["core"]["wp170"]
    # B1-A spine forecast binding consumes the legacy and the current v2 receipt identically
    receipts = {"legacy": legacy_v2["bound"][1], "current": bound_forecast[1]}
    row = next(r for r in receipts["current"]["core"]["targets"] if r["status"] == "SELECTED")
    scouted = {"grounding_receipt_id": receipts["current"]["core"]["source_grounding"]["receipt_id"],
               "target": {"market_id": row["market_id"], "rule_sha256": row["rule_content_sha256"],
                          "question_sha256": row["question_sha256"], "event_id": row["event_group"]}}
    researched = {"raw_evidence_reference_ids": list(row["grounded_source_reference_ids"])}
    bound = {k: SP.bind_forecast(v, scouted, researched) for k, v in receipts.items()}
    assert dict(bound["legacy"], receipt_id=None) == dict(bound["current"], receipt_id=None)
    assert bound["current"]["is_a3_child_forecast"] is False
    # the methods vertical consumes a sealed legacy v2 forecast scratch, and refuses a v1 one
    lscratch, lreceipt, _ = legacy_v2["bound"]
    code, _s, mreceipt = _run(tmp_path, lscratch, methods_doc(lreceipt["receipt_id"]), "legacy")
    assert code == 0 and mreceipt["core"]["forecast_receipt"]["code_identity"] == FE.LEGACY_V2_CODE_IDENTITY
    v1scratch, v1receipt, _ = legacy["bound"]
    assert _run(tmp_path, v1scratch, methods_doc(v1receipt["receipt_id"]), "v1")[0] == 1
    assert _stdout(capsys)["reason_code"] == "FORECAST_RECEIPT_SCHEMA_UNSUPPORTED"
    # B1-A / W01 / roadmap source bytes are unchanged against the pinned pre-WP main
    for path in ("src/data_layer/analytical_research/source_forecast_spine.py", "tools/alpha/run_source_forecast_spine.py",
                 "src/data_layer/analytical_research/learning_feedback.py", "src/data_layer/analytical_research/experiment_os.py"):
        pinned = subprocess.run(["git", "-C", str(REPO_ROOT), "show", f"{LEGACY_V2_COMMIT}:{path}"], capture_output=True,
                                check=True).stdout
        assert pinned.replace(b"\r\n", b"\n") == (REPO_ROOT / path).read_bytes().replace(b"\r\n", b"\n"), path


# ------------------------------------------------------------------ R010


def test_method_parity_cold_verify_idempotence_network_deny(bound_forecast, methods_run, tmp_path, monkeypatch, capsys):
    fscratch, freceipt = bound_forecast
    scratch, receipt = methods_run
    assert CLI.verify(scratch) == {"status": "VERIFIED", "failures": [], "receipt_id": receipt["receipt_id"],
                                   "network_attempts": 0}
    # repeated same input is idempotent (identical id); a used scratch is write-once
    code, _, again = _run(tmp_path, fscratch, methods_doc(freceipt["receipt_id"]), "again")
    assert code == 0 and again["receipt_id"] == receipt["receipt_id"]
    methods_path = tmp_path / "again-methods.json"
    assert CLI.main(["run", "--forecast-scratch", str(fscratch), "--methods", str(methods_path), "--scratch-dir",
                     str(tmp_path / "again")]) == 1 and _stdout(capsys)["reason_code"] == "SCRATCH_NOT_EMPTY"
    # tamper: receipt field, frozen methods, frozen forecast copy
    work = tmp_path / "work"
    shutil.copytree(scratch, work)
    bad = json.loads(json.dumps(receipt))
    bad["core"]["sampler"]["denominators"]["selected"] += 1
    (work / "receipt.json").write_text(json.dumps(bad), encoding="utf-8")
    out = CLI.verify(work)
    assert out["status"] == "TAMPER_DETECTED" and "RECEIPT_ID_MISMATCH" in out["failures"]
    (work / "receipt.json").write_text(json.dumps(receipt), encoding="utf-8")
    altered = methods_doc(freceipt["receipt_id"])
    altered["sampler"]["seed"] += 1
    (work / "inputs" / "methods.json").write_text(json.dumps(altered), encoding="utf-8")
    out = CLI.verify(work)
    assert out["status"] == "TAMPER_DETECTED" and "OUTPUT_MISMATCH:sampler" in out["failures"]
    shutil.copyfile(scratch / "inputs" / "methods.json", work / "inputs" / "methods.json")
    assert CLI.verify(work)["status"] == "VERIFIED"
    rule = next((work / "inputs" / "forecast" / "inputs" / "grounding" / "inputs" / "rules").iterdir())
    rule.write_bytes(rule.read_bytes() + b" tampered")
    assert CLI.main(["verify", "--scratch-dir", str(work)]) == 1
    assert _stdout(capsys)["reason_code"] == "GROUNDING_VERIFY_FAILED"  # the inner SRC-01 cold verify refuses first
    # partial scratch refuses rather than replays
    partial = tmp_path / "partial"
    shutil.copytree(scratch, partial)
    (partial / "receipt.json").unlink()
    assert CLI.main(["verify", "--scratch-dir", str(partial)]) == 1 and _stdout(capsys)["reason_code"] == "RECEIPT_UNREADABLE"
    shutil.copyfile(scratch / "receipt.json", partial / "receipt.json")
    (partial / "inputs" / "methods.json").unlink()
    assert CLI.main(["verify", "--scratch-dir", str(partial)]) == 1 and _stdout(capsys)["reason_code"] == "METHODS_UNREADABLE"
    # altered code identity is a mismatch, never replayed
    monkeypatch.setattr(CLI, "code_identity", lambda: "code:sha256:" + "1" * 64)
    out = CLI.verify(scratch)
    assert out["status"] == "TAMPER_DETECTED" and "OUTPUT_MISMATCH:code_identity" in out["failures"]
    monkeypatch.undo()
    # no socket in the method run, CLI or fake provider boundary: any attempt fails the run closed
    real = FMI.build_methods_core

    def phoning(*a, **k):
        try:
            socket.create_connection(("192.0.2.1", 9))
        except Exception:  # noqa: BLE001 - the guard must still see the attempt
            pass
        return real(*a, **k)
    monkeypatch.setattr(FMI, "build_methods_core", phoning)
    code, _, none = _run(tmp_path, fscratch, methods_doc(freceipt["receipt_id"]), "net")
    assert code == 1 and none is None and _stdout(capsys)["reason_code"] == "NETWORK_ATTEMPT_BLOCKED"
    monkeypatch.undo()
    # secret material and scratch inside the repository are refused; output never echoes input
    secret = tmp_path / "secret.json"
    secret.write_text(json.dumps(methods_doc(freceipt["receipt_id"], case_label="x")).replace(
        '"x"', '"sk-' + "A" * 40 + '"'), encoding="utf-8")
    assert CLI.main(["run", "--forecast-scratch", str(fscratch), "--methods", str(secret), "--scratch-dir",
                     str(tmp_path / "sec")]) == 1
    printed = capsys.readouterr().out
    assert "STOPPED" in printed and "sk-" not in printed and "Traceback" not in printed
    assert CLI.main(["run", "--forecast-scratch", str(fscratch), "--methods", str(secret), "--scratch-dir",
                     str(REPO_ROOT / "tmp-b1b")]) == 1 and _stdout(capsys)["reason_code"] == "SCRATCH_INSIDE_REPOSITORY"
    # the real entry point as its own process: run + verify, zero network, no spend
    path = tmp_path / "proc-methods.json"
    path.write_text(json.dumps(methods_doc(freceipt["receipt_id"])), encoding="utf-8")
    pscratch = (tmp_path / "proc").resolve()
    proc = subprocess.run([sys.executable, "-B", ENTRY, "run", "--forecast-scratch", str(fscratch), "--methods", str(path),
                           "--scratch-dir", str(pscratch)], capture_output=True, text=True, timeout=600)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    out = json.loads(proc.stdout)
    assert out["status"] == "RUN_COMPLETE" and out["network_attempts"] == 0 and out["receipt_id"] == receipt["receipt_id"]
    proc = subprocess.run([sys.executable, "-B", ENTRY, "verify", "--scratch-dir", str(pscratch)], capture_output=True,
                          text=True, timeout=600)
    assert proc.returncode == 0 and json.loads(proc.stdout)["status"] == "VERIFIED"
    assert receipt["core"]["authority"]["network_calls"] == 0 and receipt["core"]["provider_methods"]["spend_usd"] == "0"


# ------------------------------------------------------------------ R012


def test_capability_register_and_unchanged_source_boundaries(methods_run):
    with (ROADMAP / "03_FULL_36_CAPABILITY_ADOPTION_MATRIX.csv").open(encoding="utf-8", newline="") as handle:
        rows = {r["capability_id"]: r for r in csv.DictReader(handle)}
    assert len(rows) == 36
    for e in FMI.REGISTER:  # the nine touched ids keep their original repo and pin
        assert rows[e["capability"]]["original_repo"] == e["repository"]
        assert rows[e["capability"]]["pinned_commit"] == e["commit"]
    # the immutable roadmap archive is byte-unchanged against the pinned pre-WP main
    diff = subprocess.run(["git", "-C", str(REPO_ROOT), "diff", "--quiet", LEGACY_V2_COMMIT, "--", str(ROADMAP)],
                          capture_output=True)
    assert diff.returncode == 0
    core = methods_run[1]["core"]
    register = {e["capability"]: e for e in core["capability_register"]}
    assert list(register) == list(FMI.TOUCHED_IDS) and len(register) == 9
    assert set(rows) - set(register) and len(set(rows) - set(register)) == 27
    assert core["program"]["other_program_ids"] == "UNCHANGED_27_OF_36"
    assert core["program"]["a3_real_model_claim"] is False and core["program"]["a4_genuine_claim"] is False
    assert core["program"]["a8"] == "DIAGNOSTICS_ONLY"
    assert core["learning_feedback_read_only"]["routing"] == "NOT_PERFORMED_A8_FEEDBACK_ROUTING_IS_B5"
    # no ID is accepted without executed upstream evidence; blocked IDs carry a cause and zero fake forecasts
    assert {c for c, e in register.items() if e["disposition"] == "ENG_OFFLINE"} == {"R3-12", "R3-12-SAMPLER", "R3-20", "R3-22"}
    for c in ("R3-01", "R3-10", "R3-18"):
        assert register[c]["forecasts_contributed"] == 0 and register[c]["cause"]
    assert register["R3-10-WANG"]["disposition"] == "BLOCKED" and register["R3-10-WANG"]["forecasts_contributed"] > 0
    assert register["R3-12-SAMPLER"]["membership_sha256"] == core["sampler"]["membership_sha256"]
    text = json.dumps(core)
    assert "VALUE_VERIFIED\"" not in text and core["authority"]["real_value_verified"] is False
    # declared scope: exactly 16 paths, no workflow/dependency/credential/Hermes/execution surface
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    allowed = spec["scope"]["allowed_changed_files"]
    assert len(allowed) == 16 == spec["scope"]["max_changed_files"] and spec["scope"]["exact_scope_required"] is True
    assert not [p for p in allowed if p.startswith((".github/", "config/", "tools/hermes/", "src/execution_gateway/"))
                or p.endswith(("requirements.txt", "pyproject.toml", ".lock"))]
    assert spec["authority"]["network"] is False and spec["authority"]["credentials"] is False
    assert spec["authority"]["dependencies"] is False and spec["authority"]["live"] is False
    for p in (Path(FMI.__file__), Path(CLI.__file__)):  # no network, subprocess or provider client imported
        tree = ast.parse(p.read_text(encoding="utf-8"))
        names = {a.name.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names} |                 {n.module.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module}
        assert not names & {"urllib", "requests", "http", "subprocess", "socket", "openai", "litellm", "httpx",
                            "aiohttp", "forecasting_tools", "numpy", "pandas", "scipy"}, p.name
