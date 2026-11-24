"""S10-CAP-B2-RELATIONS-WALLET-01 R003/R005/R007/R008/R010/R012: B2 operator over the real native producers.

Same SANITIZED_SYNTHETIC frozen world as the data-layer B2 tests: B1-A SRC-01 grounding (+ one same-event
market) -> real REL-01 run -> genuine vendored Oracle3 parity -> real WALLET-01 ledger -> native WALLET-02/03.
The full B1-A spine receipt needs the exact pinned Hermes checkout (``POLYMARKET_HERMES_PIN_ROOT``); without it
the pinned parts skip with a reason and every unpinned consumer/refusal part still runs.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import socket

import pytest

from src.data_layer.analytical_research import relation_wallet_spine as RW
from src.data_layer.wallet_intelligence import copyability as WC
from src.data_layer.wallet_intelligence import ledger as WL
from src.data_layer.wallet_intelligence import profile as WP
from tests.data_layer.analytical_research import test_relation_wallet_spine as T
from tests.data_layer.analytical_research import test_source_forecast_spine as B1
from tools.alpha import run_oracle3_upstream_parity as PAR
from tools.alpha import run_related_market_alpha as REL
from tools.alpha import run_relation_wallet_spine as CLI
from tools.alpha import run_source_forecast_spine as B1A

PIN = os.environ.get("POLYMARKET_HERMES_PIN_ROOT")
REPO_ROOT = Path(__file__).resolve().parents[3]
CSV = REPO_ROOT / "docs" / "roadmaps" / "nine_agent_capability_first_20261117" / "03_FULL_36_CAPABILITY_ADOPTION_MATRIX.csv"
CSV_SHA256 = "ecea9023e74f7b97f0c6386ef00d9fc0ec57ef4919f70f3df432d2f5e529dedd"
SIX = {"R3-03", "R3-03-FEES", "R3-04", "R3-11", "R3-19", "R3-14"}
# native producer identities at merged base 573ac90 (this WP edits none of them)
NATIVE_IDENTITIES = {
    "REL": (REL, "code:sha256:c33424a1ebcfc62188e190978386be1f657d80cfc85c49dd773dea5d79d7c316"),
    "PAR": (PAR, "code:sha256:679c35543ca72d03e7e404b839aa19e08402e73dd5b768ed665a086ba4403ebd"),
    "B1A": (B1A, "code:sha256:5d6a525f7e1741f00e458552551ff10dc618c6227aa9572a3e0af074b6d2e1d6"),
}


def _need_pin():
    if not PIN:
        pytest.skip("POLYMARKET_HERMES_PIN_ROOT not set: exact pinned Hermes checkout absent (pinned part only)")


def _tree(root: Path) -> dict:
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(Path(root).rglob("*")) if p.is_file()}


def _args(**kw):
    return type("Args", (), dict(command="run", **kw))()


def _write_case(directory: Path, case: dict) -> Path:
    path = (directory / "b2-case.json").resolve()
    path.write_text(json.dumps(case), encoding="utf-8")
    return path


def _argv(spine, registry, rel, ledger, case, scratch):
    return ["run", "--spine-scratch", str(spine), "--alpha-registry", str(registry), "--rel-scratch", str(rel),
            "--wallet-ledger", str(ledger), "--case", str(case), "--scratch-dir", str(scratch)]


@pytest.fixture(scope="module")
def b2(tmp_path_factory):
    return T.build_b2_world(tmp_path_factory.mktemp("b2_tools_world"))


@pytest.fixture(scope="module")
def pinned(b2, tmp_path_factory):
    """One real B1-A spine run (W01 children through the exact pin) and one complete B2 run over it."""
    if not PIN:
        return None
    base = tmp_path_factory.mktemp("b2_pinned")
    world = b2["world"]
    registry = (base / "registry.sqlite3").resolve()
    shutil.copyfile(world["registry"], registry)
    case = (base / "spine.json").resolve()
    case.write_text(json.dumps(B1.spine_case(world)), encoding="utf-8")
    fc = (base / "fc.json").resolve()
    fc.write_text(json.dumps(B1.forecast_cases(world)), encoding="utf-8")
    spine = (base / "spine-scratch").resolve()
    spine_result = B1A.run(case, world["grounding"], fc, registry, spine, Path(PIN))
    assert spine_result["status"] == "RUN_COMPLETE"
    b2_case = _write_case(b2["ledger"]["base"], T.b2_case(spine_result["receipt_id"], b2["rel"]["receipt_id"], b2["ledger"]))
    caller = {"spine": _tree(spine), "registry": hashlib.sha256(registry.read_bytes()).hexdigest(), "rel": _tree(b2["rel_scratch"]),
              "ledger": _tree(b2["ledger"]["base"])}
    scratch = (base / "b2-scratch").resolve()
    calls = []
    real_connect, real_create = socket.socket.connect, socket.create_connection
    socket.socket.connect = lambda self, *a, **k: calls.append("connect")  # spy beneath the operator's own block
    socket.create_connection = lambda *a, **k: calls.append("create_connection")
    try:
        result = CLI.run_safe(_args(spine_scratch=spine, alpha_registry=registry, rel_scratch=b2["rel_scratch"],
                                    wallet_ledger=b2["ledger"]["path"], case=b2_case, scratch_dir=scratch))
    finally:
        socket.socket.connect, socket.create_connection = real_connect, real_create
    return {"spine": spine, "spine_receipt": json.loads((spine / "receipt.json").read_text(encoding="utf-8")),
            "registry": registry, "case": b2_case, "scratch": scratch, "result": result, "calls": calls,
            "caller_before": caller, "receipt": json.loads((scratch / "receipt.json").read_text(encoding="utf-8"))
            if (scratch / "receipt.json").is_file() else None, "base": base}


# ------------------------------------------------------------------ R003


def test_b2_real_rel_oracle_native_consumption(b2, tmp_path):
    before = _tree(b2["rel_scratch"])
    assert REL.verify(b2["rel_scratch"])["status"] == "VERIFIED"
    assert PAR.verify(b2["parity_scratch"])["status"] == "VERIFIED"
    a5 = RW.relations(b2["binding"], b2["rel"], b2["parity"], list(T.SELECTED))
    rel_rows = {r["model_id"]: r for r in b2["rel"]["core"]["results"]}
    par_rows = {c["model_id"]: c for c in b2["parity"]["core"]["results"]}
    # copied, never re-derived: every selected field equals the native REL row / genuine parity case
    for s in a5["selected"]:
        row, case = rel_rows[s["model_id"]], par_rows[s["model_id"]]
        assert s["formal"] == {k: row["formal"][k] for k in ("status", "trust", "counterexamples", "special_states")}
        assert (s["disposition"], s["relation"], s["market_ids"]) == (row["disposition"], row["relation"], row["market_ids"])
        assert (s["oracle3"]["verdict"], s["oracle3"]["reason"]) == (case["verdict"], case["reason"])
        assert s["oracle3"]["parity"] == [p["parity"] for p in case["parity"]]
    for p in a5["a7_pointer"]:
        assert p["native_economic_status"] == rel_rows[p["model_id"]]["economics"]["status"]
        assert len(p["baskets"]) == len(rel_rows[p["model_id"]]["economics"]["baskets"])
    assert a5["rel_code_identity"] == b2["rel"]["core"]["code_identity"] == NATIVE_IDENTITIES["REL"][1]
    assert a5["parity_code_identity"] == b2["parity"]["core"]["code_identity"]
    assert a5["upstream"]["invoked"] and a5["status"] == "ADMITTED"
    # a model id absent from REL, and parity from a different REL run, both refuse
    with pytest.raises(RW.RelationWalletStop, match="MODEL_ID_NOT_UNIQUE_IN_REL"):
        RW.relations(b2["binding"], b2["rel"], b2["parity"], ["b2-impl", "b2-unknown"])
    other = T.run_rel_and_parity(b2["world"], tmp_path / "other", models=T.MODELS[:2], name="other")
    assert other["rel"]["receipt_id"] != b2["rel"]["receipt_id"]
    with pytest.raises(RW.RelationWalletStop, match="PARITY_REL_MISMATCH"):
        RW.relations(b2["binding"], b2["rel"], other["parity"], ["b2-impl"])
    assert RW.relations(b2["binding"], other["rel"], other["parity"], ["b2-impl"])["status"] == "ADMITTED"
    # consumption never writes the native REL scratch
    assert _tree(b2["rel_scratch"]) == before


# ------------------------------------------------------------------ R005


def test_b2_native_wallet_profile_and_copyability(b2):
    led = b2["ledger"]
    before = led["path"].read_bytes()
    case = T.b2_case("b1spine:sha256:" + "0" * 64, b2["rel"]["receipt_id"], led)
    first = RW.wallet(b2["binding"], led["path"], case, T.reader(led["base"]), T.DECISION)
    assert first == RW.wallet(b2["binding"], led["path"], case, T.reader(led["base"]), T.DECISION)  # deterministic
    assert led["path"].read_bytes() == before and WL.load_and_verify_wallet_evidence_ledger(led["path"]).is_valid
    assert first["status"] == "ADMITTED" and first["ledger_head"] == led["head"]
    # the B2 ids are exactly the native WALLET-02/03 builders' ids on the same inputs
    manifests = (led["manifest"], led["book_manifest"])
    cohort = WP.wallet_discovery_cohort_from_mapping(case["cohort"], provenance_manifests=manifests)
    contexts = tuple(WP.wallet_profile_market_context_from_mapping(m) for m in case["market_contexts"])
    profile = WP.build_wallet_profile_snapshot(wallet_ledger_path=led["path"], cohort_snapshot=cohort, target_wallet=T.WALLET,
                                               as_of=T.WALLET_AS_OF, market_contexts=contexts, identity_observability={})
    assert first["profile"]["wallet_profile_snapshot_id"] == profile.wallet_profile_snapshot_id
    assert first["cohort_snapshot_id"] == cohort.wallet_discovery_cohort_snapshot_id
    grouped = {}
    for entry in WL.load_and_verify_wallet_evidence_ledger(led["path"]).snapshot.entries:
        grouped.setdefault(entry.record_kind, {})[entry.record_id] = entry.payload
    witness = RW._witness(case["quote_witnesses"][0], grouped, T.reader(led["base"]))
    assessment = WC.build_wallet_copyability_research_assessment(
        profile=profile, wallet_ledger_path=led["path"], expected_ledger_head=led["head"], cohort_snapshot=cohort,
        target_wallet=T.WALLET, as_of=T.WALLET_AS_OF, market_contexts=contexts, quote_witnesses=(witness,),
        delay_seconds=("1", "5"), cost_scenarios=(WC.WalletCopyabilityCostScenario(**T.COST),), identity_observability=None)
    assert first["assessment"]["wallet_copyability_research_assessment_id"] == assessment.wallet_copyability_research_assessment_id
    mapping = WC.wallet_copyability_research_assessment_to_mapping(assessment)
    assert WC.wallet_copyability_research_assessment_from_mapping(mapping) == assessment
    one = first["assessment"]["delay_results"][0]
    assert (one["delay_seconds"], one["status"], one["eligible_event_count"]) == ("1", "OBSERVABLE_CONDITIONAL", 1)
    assert first["assessment"]["target_eligible_events"] == 1 and first["target_context_id"] == contexts[0].wallet_profile_market_context_id
    assert first["assessment"]["quote_source_status_counts"] == {"OBSERVED": 1}
    assert T.WALLET.lower() not in json.dumps(first).lower()  # ids and counts only, never the address


# ------------------------------------------------------------------ R007


def test_b2_b1a_to_joint_role_receipt(b2, pinned, capsys):
    _need_pin()
    assert pinned["result"] == {"status": "RUN_COMPLETE", "receipt_id": pinned["receipt"]["receipt_id"], "a5": "ADMITTED",
                                "a6": "ADMITTED", "network_attempts": 0}
    core, spine = pinned["receipt"]["core"], pinned["spine_receipt"]
    assert pinned["receipt"]["receipt_id"].startswith(RW.RECEIPT_PREFIX) and core["schema_id"] == RW.RECEIPT_SCHEMA
    # A1-A4 read-only lineage: the exact B1-A receipt ids, never re-run or re-minted
    lineage = core["b1a_lineage"]
    assert lineage == RW.b1a_lineage(spine) and lineage["spine_receipt_id"] == spine["receipt_id"]
    assert lineage["a3_a4"]["provider_invocations"] == RW.b1a_lineage(spine)["a3_a4"]["provider_invocations"]
    assert core["shared_case"]["target"] == lineage["a1_target"]
    assert core["shared_case"]["grounding_receipt_id"] == lineage["grounding_receipt_id"] == b2["binding"]["grounding_receipt_id"]
    assert core["a5_relations"]["rel_receipt_id"] == b2["rel"]["receipt_id"] and core["a6_wallet"]["ledger_head"] == b2["ledger"]["head"]
    assert core["roles"] == {"A1_A4": "READ_ONLY_B1A_LINEAGE", "A5_relations": "ADMITTED", "A6_wallet": "ADMITTED",
                             "A7_execution_economics": "CONDITIONAL_READ_SIDE_POINTER_ONLY_NO_NEW_MODEL",
                             "A8_A9": "NOT_ATTEMPTED_LATER_OWNERS", "coordinator": "FUTURE_W08_CONSUMES_THIS_INTERFACE",
                             "llm_child_invocations": 0}
    assert core["authority"] == RW.AUTHORITY and core["evidence_class"] == "OFFLINE_ENGINEERING_DEMONSTRATION"
    assert set(core["input_sha256"]) == {"spine", "registry", "rel", "ledger", "case", "bundle"}
    assert CLI.main(["verify", "--scratch-dir", str(pinned["scratch"])]) == 0
    out = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert out == {"status": "VERIFIED", "failures": [], "receipt_id": pinned["receipt"]["receipt_id"], "network_attempts": 0}
    text = json.dumps(pinned["receipt"]).lower()
    assert T.WALLET.lower() not in text and "0x" + "1" * 40 not in text


# ------------------------------------------------------------------ R008


def test_b2_historical_native_receipts_unchanged(b2, pinned):
    for name, (module, identity) in NATIVE_IDENTITIES.items():
        assert module.code_identity() == identity, name
    assert b2["rel"]["core"]["code_identity"] == NATIVE_IDENTITIES["REL"][1]
    assert b2["parity"]["core"]["code_identity"] == NATIVE_IDENTITIES["PAR"][1]
    # one-way dependency: no native producer imports the B2 consumer
    for rel in ("tools/alpha/run_related_market_alpha.py", "tools/alpha/run_oracle3_upstream_parity.py",
                "tools/alpha/run_source_forecast_spine.py", "tools/alpha/run_hermes_delegated_specialists.py",
                "src/data_layer/analytical_research/source_forecast_spine.py",
                "src/data_layer/analytical_research/oracle3_upstream_bridge.py",
                "src/data_layer/wallet_intelligence/ledger.py", "src/data_layer/wallet_intelligence/profile.py",
                "src/data_layer/wallet_intelligence/copyability.py"):
        assert "relation_wallet_spine" not in (REPO_ROOT / rel).read_text(encoding="utf-8"), rel
    # native receipts still cold-verify unchanged after B2 consumption
    before = {k: _tree(b2[k]) for k in ("rel_scratch", "parity_scratch")}
    assert REL.verify(b2["rel_scratch"])["receipt_id"] == b2["rel"]["receipt_id"]
    assert PAR.verify(b2["parity_scratch"])["receipt_id"] == b2["parity"]["receipt_id"]
    assert {k: _tree(b2[k]) for k in before} == before
    if pinned is None:
        pytest.skip("pinned part: B1-A spine receipt cold replay requires POLYMARKET_HERMES_PIN_ROOT")
    spine_before = _tree(pinned["spine"])
    checked = B1A.verify(pinned["spine"], pinned["registry"])
    assert checked["status"] == "VERIFIED" and checked["receipt_id"] == pinned["spine_receipt"]["receipt_id"]
    assert _tree(pinned["spine"]) == spine_before
    assert pinned["receipt"]["core"]["a5_relations"]["parity_code_identity"] == NATIVE_IDENTITIES["PAR"][1]


# ------------------------------------------------------------------ R010


def test_b2_write_once_cold_verify_and_tamper(b2, pinned, tmp_path, capsys):
    world, led = b2["world"], b2["ledger"]
    case_dir = (tmp_path / "case").resolve()
    case_dir.mkdir()
    shutil.copyfile(led["base"] / "book-1.json", case_dir / "book-1.json")
    case = _write_case(case_dir, T.b2_case("b1spine:sha256:" + "0" * 64, b2["rel"]["receipt_id"], led))
    base = dict(spine_scratch=world["grounding"], alpha_registry=world["registry"], rel_scratch=b2["rel_scratch"],
                wallet_ledger=led["path"], case=case)
    busy = (tmp_path / "busy").resolve()
    busy.mkdir()
    (busy / "x").write_bytes(b"1")
    assert CLI.run_safe(_args(**base, scratch_dir=busy)) == {"status": "STOPPED", "reason_code": "SCRATCH_NOT_EMPTY"}
    assert CLI.run_safe(_args(**base, scratch_dir=REPO_ROOT / "b2-scratch"))["reason_code"] == "SCRATCH_INVALID"
    assert CLI.run_safe(_args(**base, scratch_dir=Path("relative")))["reason_code"] == "SCRATCH_INVALID"
    overlap = dict(base, case=(b2["rel_scratch"] / "receipt.json").resolve())
    assert CLI.run_safe(_args(**overlap, scratch_dir=(tmp_path / "o").resolve()))["reason_code"] == "INPUT_PATHS_OVERLAP"
    side = Path(str(led["path"]) + "-wal")
    side.write_bytes(b"")
    try:
        assert CLI.run_safe(_args(**base, scratch_dir=(tmp_path / "s").resolve()))["reason_code"] == "SQLITE_SIDECAR_PRESENT"
    finally:
        side.unlink()
    # a stop after freezing leaves a partial scratch that is never reused nor verified
    partial = (tmp_path / "partial").resolve()
    stopped = CLI.run_safe(_args(**base, scratch_dir=partial))
    assert stopped == {"status": "STOPPED", "reason_code": "SPINE_NOT_VERIFIED"}  # a grounding is not a spine
    assert (partial / "inputs").is_dir() and not (partial / "receipt.json").exists()
    assert CLI.run_safe(_args(**base, scratch_dir=partial))["reason_code"] == "SCRATCH_NOT_EMPTY"
    assert CLI.run_safe(type("V", (), dict(command="verify", scratch_dir=partial))())["status"] != "VERIFIED"
    assert CLI.main(["verify", "--scratch-dir", str((tmp_path / "missing").resolve())]) == 1
    capsys.readouterr()
    _need_pin()
    assert pinned["result"]["status"] == "RUN_COMPLETE" and pinned["calls"] == []
    caller_after = {"spine": _tree(pinned["spine"]), "registry": hashlib.sha256(pinned["registry"].read_bytes()).hexdigest(),
                    "rel": _tree(b2["rel_scratch"]), "ledger": _tree(led["base"])}
    assert caller_after == pinned["caller_before"]  # caller stores, case and retained bytes untouched
    # write once: a second run into the completed scratch refuses, verify is read-only
    scratch = pinned["scratch"]
    again = CLI.run_safe(_args(spine_scratch=pinned["spine"], alpha_registry=pinned["registry"], rel_scratch=b2["rel_scratch"],
                               wallet_ledger=led["path"], case=pinned["case"], scratch_dir=scratch))
    assert again == {"status": "STOPPED", "reason_code": "SCRATCH_NOT_EMPTY"}
    before = _tree(scratch)
    assert CLI.verify(scratch)["status"] == "VERIFIED" and _tree(scratch) == before
    # relocated copy still verifies; every tamper in a copy is detected
    moved = (tmp_path / "moved").resolve()
    shutil.copytree(scratch, moved)
    assert CLI.verify(moved)["receipt_id"] == pinned["receipt"]["receipt_id"]

    def flip(path: Path):
        data = bytearray(path.read_bytes())
        data[len(data) // 2] ^= 0x01
        path.write_bytes(bytes(data))

    def edit_receipt(path: Path):
        receipt = json.loads(path.read_text(encoding="utf-8"))
        receipt["core"]["a6_wallet"]["status"] = "INSUFFICIENT"
        path.write_text(json.dumps(receipt), encoding="utf-8")

    tampers = {"receipt": ("receipt.json", edit_receipt), "case": ("inputs/case.json", lambda p: p.write_bytes(p.read_bytes() + b" ")),
               "registry": ("inputs/alpha_registry.sqlite3", flip), "ledger": ("inputs/wallet_ledger.sqlite3", flip),
               "rel": ("inputs/rel/receipt.json", flip), "parity": ("parity/receipt.json", flip),
               "bundle": ("inputs/bundle/book-1.json", flip), "spine": ("inputs/spine/receipt.json", flip)}
    for name, (member, mutate) in tampers.items():
        copy_dir = (tmp_path / ("t-" + name)).resolve()
        shutil.copytree(scratch, copy_dir)
        mutate(copy_dir / member)
        result = CLI.run_safe(type("V", (), dict(command="verify", scratch_dir=copy_dir))())
        assert result["status"] in ("TAMPER_DETECTED", "STOPPED") and result["status"] != "VERIFIED", name
        assert "Traceback" not in json.dumps(result) and str(copy_dir) not in json.dumps(result), name


# ------------------------------------------------------------------ R012


def test_b2_six_id_ledger_and_scope(b2):
    raw = CSV.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == CSV_SHA256 or hashlib.sha256(raw.replace(b"\r\n", b"\n")).hexdigest() == CSV_SHA256
    rows = [line for line in raw.decode("utf-8").splitlines()[1:] if line]
    ids = [line.split(",", 1)[0] for line in rows]
    assert len(ids) == 36 == len(set(ids)) and SIX <= set(ids)
    # every pinned repo/commit matches the frozen CSV row for that id
    by_id = {line.split(",", 1)[0]: line for line in rows}
    for cap, (repo, commit, _member, _licence) in RW.PINS.items():
        assert by_id[cap].split(",")[1:3] == [repo, commit], cap
    assert set(RW.PINS) == SIX and set(RW.OPEN_CAUSES) == SIX - {"R3-03", "R3-03-FEES"}
    a5 = RW.relations(b2["binding"], b2["rel"], b2["parity"], list(T.SELECTED))
    ledger = RW.capability_ledger(a5, {"ledger_head": b2["ledger"]["head"]})
    assert set(ledger["touched"]) == SIX and len(set(ids) - SIX) == 30
    assert ledger["other_30_capability_ids"] == "UNCHANGED" and ledger["w06_book_gap_fill_model"] == "NOT_ATTEMPTED"
    assert ledger["lane_b"] == "R3-15/R3-16/R3-17/R3-26_SEPARATELY_OWNED_UNTOUCHED"
    assert not any(w in json.dumps(ledger) for w in ("OPERATIONAL", "ADOPTED", "PROFIT", "LIVE_READY", '"value_verified": true'))
    # exact 11-path scope; new test basenames do not collide with any other test module
    spec = json.loads((REPO_ROOT / "docs" / "wp_specs" / RW.WP_ID / "wp_spec.json").read_text(encoding="utf-8"))
    paths = spec["scope"]["required_changed_files"]
    assert len(paths) == 11 == len(set(paths)) and paths == spec["scope"]["allowed_changed_files"]
    assert {"src/data_layer/analytical_research/relation_wallet_spine.py", "tools/alpha/run_relation_wallet_spine.py"} <= set(paths)
    for name in ("test_relation_wallet_spine.py", "test_run_relation_wallet_spine.py"):
        assert len(list((REPO_ROOT / "tests").rglob(name))) == 1, name
