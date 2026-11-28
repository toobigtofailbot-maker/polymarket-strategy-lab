"""S10-CAP-NINE-ROLE-COORD-01 R002/R004/R011/R012: pure B4 routing, role consumers, capability rows and denominators.

Routing, journal and denominator mechanics run on synthetic consumer records (``simulate``): they prove the closed
state machine and the counts only, never an integration or role credit. A5/A6/A7 consumers run on real native B2/B3
cores built by the existing native builders (no pin needed); A1-A4 run on the real pinned B1-A/W01 receipts and skip
with a reason when the exact pinned Hermes checkout is absent (D001).
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import re

import pytest

from src.data_layer.analytical_research import execution_economics_spine as XE
from src.data_layer.analytical_research import nine_role_coordination as NR
from src.data_layer.analytical_research import relation_wallet_spine as RW
from tests.data_layer.analytical_research import test_execution_economics_spine as X
from tests.data_layer.analytical_research import test_relation_wallet_spine as T

REPO_ROOT = Path(__file__).resolve().parents[3]
B2_ID = "b2research:sha256:" + "a" * 64
B3_ID = "b3research:sha256:" + "b" * 64
INVENTORY = {"case-01": {"files": 1, "bytes": 1, "sha256": "0" * 64}, "case-02": {"files": 1, "bytes": 1, "sha256": "1" * 64}}


def manifest(*cases) -> dict:
    return {"schema_id": NR.MANIFEST_SCHEMA, "cases": [dict(source_kind=k, receipt_id=i, route=r) for k, i, r in cases]}


def plan_for(*cases) -> dict:
    m = manifest(*cases)
    return NR.build_plan(m, {s: INVENTORY[s] for s in NR.slots(m)})


def fake_lineage(slot: str) -> dict:
    return {"w01_receipt_id": "hermesdelegatedreceipt:sha256:" + "c" * 64, "witness_id": "w:" + slot, "episode_id": "e:" + slot,
            "prior_host_witness": {"provider_invocations": "ZERO_REAL_PROVIDER_INVOCATIONS", "acceptance_status": "X"}}


def simulate(plan_doc: dict, outcomes: dict, *, stop_at: int | None = None) -> tuple[list, dict]:
    """The CLI's own decide/append order with synthetic outcomes (mechanics only, never role credit).

    outcomes: slot -> {"verify": CASE_* terminal event type, role: ("COMPLETED_CONSUMED", native) | (STATUS, code)}."""
    events, projections = [], {}

    def add(kind, payload):
        prev = events[-1]["event_id"] if events else plan_doc["plan_id"]
        events.append(NR.make_event(len(events) + 1, prev, kind, payload))
        state = NR.replay(plan_doc, events)
        if stop_at is not None and len(events) >= stop_at:
            raise StopIteration
        return state

    state = NR.replay(plan_doc, [])
    try:
        for index, case in enumerate(plan_doc["plan"]["cases"]):
            spec = outcomes.get(case["slot"], {})
            ids = {"slot": case["slot"], "case_id": case["case_id"], "attempt_id": case["verify_attempt_id"]}
            state = add("CASE_VERIFY_STARTED", ids)
            kind = spec.get("verify", "CASE_VERIFIED")
            extra = {"lineage_sha256": "d" * 64} if kind == "CASE_VERIFIED" else {"reason": spec.get("verify_reason", "NATIVE_VERIFY_REFUSED")}
            state = add(kind, dict(ids, **extra))
            for task in case["tasks"]:
                role, cs = task["role"], state["cases"][index]
                decision, reason = NR.decide(case, role, cs["verify"], {r: v for r, v in cs["tasks"].items() if v})
                rid = {"slot": case["slot"], "role": role, "task_id": task["task_id"]}
                if decision == "SKIP":
                    state = add("ROLE_SKIPPED", dict(rid, reason=reason))
                    continue
                rid["attempt_id"] = task["attempt_id"]
                state = add("ROLE_STARTED", rid)
                status, value = spec.get(role, ("COMPLETED_CONSUMED", "ADMITTED"))
                if status == "COMPLETED_CONSUMED":
                    out = {"source": {"receipt_id": case["receipt_id"], "member": role}, "native_status": value,
                           "projection": {"synthetic_mechanics_only": role, "native_status": value}}
                    record = NR.consumer_record(task, out, [cs["tasks"][p]["record"]["consumer_id"] for p in task["prerequisites"]])
                    state = add("ROLE_COMPLETED_CONSUMED", dict(rid, **record))
                    projections[(case["slot"], role)] = out["projection"]
                else:
                    state = add("ROLE_" + status, dict(rid, reason=value))
    except StopIteration:
        pass
    return events, projections


def statuses(state: dict, index: int) -> dict:
    return {r: (v["status"], v["reason"] if v["status"] != "COMPLETED_CONSUMED" else v["native_status"])
            for r, v in state["cases"][index]["tasks"].items()}


def stop(fn, *args, **kwargs) -> str:
    with pytest.raises(NR.CoordinationStop) as excinfo:
        fn(*args, **kwargs)
    return str(excinfo.value)


# ------------------------------------------------------------------ R002


def test_b4_route_matrix_and_denominator():
    seen = set()
    for route, requested in NR.ROUTES.items():
        for kind, rid in (("B2", B2_ID), ("B3", B3_ID)):
            plan_doc = plan_for((kind, rid, route), ("B2", B2_ID[:-1] + "f", "SOURCE_REVIEW"))
            cases = plan_doc["plan"]["cases"]
            assert [len(c["tasks"]) for c in cases] == [9, 9] and [t["role"] for t in cases[0]["tasks"]] == list(NR.ROLES)
            ids = [c["case_id"] for c in cases] + [t[k] for c in cases for t in c["tasks"] for k in ("task_id", "attempt_id")] \
                + [c["verify_attempt_id"] for c in cases]
            assert len(ids) == len(set(ids)) == 2 + 36 + 2 and all(re.fullmatch(r"b4[a-z]+:sha256:[0-9a-f]{64}", i) for i in ids)
            seen.add(plan_doc["plan_id"])
            assert [t["requested"] for t in cases[0]["tasks"]] == [r in requested for r in NR.ROLES]
            assert plan_for((kind, rid, route), ("B2", B2_ID[:-1] + "f", "SOURCE_REVIEW")) == plan_doc  # deterministic
            events, _ = simulate(plan_doc, {})
            state = NR.replay(plan_doc, events)
            got = statuses(state, 0)
            assert state["complete"] and len(got) == 9
            for role in NR.ROLES:
                status, value = got[role]
                if role in ("A8", "A9"):
                    assert (status, value) == ("SKIPPED", NR.FUTURE[role])
                elif role not in requested:
                    assert (status, value) == ("SKIPPED", "NOT_REQUESTED")
                elif role == "A7" and kind == "B2":
                    assert (status, value) == ("SKIPPED", "B3_NOT_SUPPLIED")
                else:
                    assert status == "COMPLETED_CONSUMED", (route, kind, role)
            # count conservation: exactly nine terminal slots per case, mutually exclusive
            assert sum(Counter_of(state, 0).values()) == 9
    assert len(seen) == 10  # a distinct plan per (route, kind)
    full = plan_for(("B3", B3_ID, "FULL_SHARED_CASE"))
    # native A5 refusal/insufficiency is consumed (delivery) yet blocks only A7; A6 refusal blocks nothing
    for native in ("REFUSED", "INSUFFICIENT"):
        got = statuses(NR.replay(full, simulate(full, {"case-01": {"A5": ("COMPLETED_CONSUMED", native)}})[0]), 0)
        assert got["A5"] == ("COMPLETED_CONSUMED", native) and got["A6"][0] == "COMPLETED_CONSUMED"
        assert got["A7"] == ("SKIPPED", "A5_NATIVE_NOT_ADMITTED")
    got = statuses(NR.replay(full, simulate(full, {"case-01": {"A6": ("COMPLETED_CONSUMED", "REFUSED")}})[0]), 0)
    assert got["A6"] == ("COMPLETED_CONSUMED", "REFUSED") and got["A7"] == ("COMPLETED_CONSUMED", "ADMITTED")
    # the W01 pair is atomic: a refused/failed/quarantined A3 never lets A4 or the downstream roles run
    for status in ("REFUSED", "FAILED"):
        got = statuses(NR.replay(full, simulate(full, {"case-01": {"A3": (status, "W01_PAIR_SHAPE_INVALID")}})[0]), 0)
        assert got["A3"] == (status, "W01_PAIR_SHAPE_INVALID") and got["A4"] == ("SKIPPED", "PREREQUISITE_NOT_CONSUMED:A3")
        assert got["A5"] == got["A6"] == ("SKIPPED", "PREREQUISITE_NOT_CONSUMED:A3") and got["A7"][0] == "SKIPPED"
    got = statuses(NR.replay(full, simulate(full, {"case-01": {"A4": ("REFUSED", "W01_PAIR_PARTNER_MISMATCH")}})[0]), 0)
    assert got["A3"][0] == "COMPLETED_CONSUMED" and got["A5"] == got["A6"] == ("SKIPPED", "PREREQUISITE_NOT_CONSUMED:A4")
    got = statuses(NR.replay(full, simulate(full, {"case-01": {"A1": ("REFUSED", "A1_LINEAGE_MISMATCH")}})[0]), 0)
    assert got["A2"] == ("SKIPPED", "PREREQUISITE_NOT_CONSUMED:A1") and got["A7"] == ("SKIPPED", "PREREQUISITE_NOT_CONSUMED:A1")
    # an unverified case skips every requested role, while non-requested and future reasons are preserved
    wallet = plan_for(("B2", B2_ID, "WALLET_REVIEW"))
    for kind in ("CASE_VERIFY_REFUSED", "CASE_VERIFY_FAILED", "CASE_VERIFY_QUARANTINED"):
        reason = NR.QUARANTINE_REASON if kind == "CASE_VERIFY_QUARANTINED" else "NATIVE_VERIFY_REFUSED"
        got = statuses(NR.replay(wallet, simulate(wallet, {"case-01": {"verify": kind, "verify_reason": reason}})[0]), 0)
        assert [got[r] for r in ("A1", "A6")] == [("SKIPPED", "CASE_NOT_VERIFIED")] * 2
        assert got["A5"] == got["A7"] == ("SKIPPED", "NOT_REQUESTED")
        assert (got["A8"], got["A9"]) == (("SKIPPED", "W09_PENDING"), ("SKIPPED", "W10_PENDING"))
    # no truthy coercion: only the exact closed strings count
    case = full["plan"]["cases"][0]
    good = {r: {"status": "COMPLETED_CONSUMED", "native_status": "ADMITTED"} for r in NR.ROLES[:6]}
    assert NR.decide(case, "A7", "VERIFIED", good) == ("ATTEMPT", None)
    for bad in ({"status": "completed_consumed"}, {"status": True}, {"status": 1}, {"status": "COMPLETED_CONSUMED "}):
        assert NR.decide(case, "A7", "VERIFIED", dict(good, A3=dict(good["A3"], **bad)))[0] == "SKIP"
    for native in ("admitted", True, 1, None):
        assert NR.decide(case, "A7", "VERIFIED", dict(good, A5=dict(good["A5"], native_status=native))) \
            == ("SKIP", "A5_NATIVE_NOT_ADMITTED")
    for verify in ("verified", True, None, "REFUSED"):
        assert NR.decide(case, "A1", verify, {}) == ("SKIP", "CASE_NOT_VERIFIED")
    assert NR.decide(case, "A8", "VERIFIED", good) == ("SKIP", "W09_PENDING")


def Counter_of(state: dict, index: int) -> dict:
    out: dict = {}
    for value in state["cases"][index]["tasks"].values():
        out[value["status"]] = out.get(value["status"], 0) + 1
    assert set(out) <= set(NR.DELIVERY)
    return out


# ------------------------------------------------------------------ R004


@pytest.fixture(scope="module")
def world(tmp_path_factory):
    """Real native B2 core (native REL/Oracle3/WALLET builders) and a real native B3 core over it (no pin needed)."""
    world = X.build_b3_world(tmp_path_factory.mktemp("b4_world"))
    b2 = RW.finalize(world["core"])
    case = X.probe_case(world, b2_receipt_id=b2["receipt_id"])
    selected, bound = X.bind(world, case)
    _, _, point = XE.assess_point(case, bound["snapshot"], X.DECISION_NS)
    replay = XE.not_supplied()
    core = XE.build_core(code_identity="code:sha256:" + "0" * 64, input_sha256={},
                         lineage=XE.b2_lineage(b2["receipt_id"], world["core"], selected, bound), point=point,
                         replay=replay, role=XE.a7_role(point, replay, selected),
                         ledger=XE.capability_ledger(world["core"], point, replay))
    return dict(world, b2=b2, b3=XE.finalize(core), refused_a6=T._a6(world, tmp_path_factory.mktemp("b4_a6"), "notcohort",
                                                                       target_wallet=T.OTHER_WALLET))


def _a1_dep(core: dict) -> dict:
    return {"grounding_receipt_id": core["shared_case"]["grounding_receipt_id"],
            "target_sha256": NR.sha_json(core["shared_case"]["target"])}


def test_b4_role_consumers_native_states(world):
    view = {"source_kind": "B3", "receipt_id": world["b3"]["receipt_id"], "b2": world["b2"], "b3": world["b3"],
            "spine": None, "w01": None}
    a1 = _a1_dep(world["core"])
    a5 = NR.consume("A5", view, {"A1": a1})
    native = world["core"]["a5_relations"]
    assert a5["native_status"] == native["status"] == "ADMITTED" and a5["source"] == {"receipt_id": world["b2"]["receipt_id"],
                                                                                    "member": "core.a5_relations"}
    p5 = a5["projection"]
    assert p5["rel_receipt_id"] == native["rel_receipt_id"] and p5["denominators"] == native["denominators"]
    assert [s["model_id"] for s in p5["selected"]] == [s["model_id"] for s in native["selected"]]
    assert all(p["tradable"] is False and p["executable_edge"] is False for p in p5["a7_pointer"])
    a6 = NR.consume("A6", view, {"A1": a1})
    assert a6["native_status"] == world["core"]["a6_wallet"]["status"] == "ADMITTED"
    assert a6["projection"]["assessment_id"] == world["core"]["a6_wallet"]["assessment"]["wallet_copyability_research_assessment_id"]
    a7 = NR.consume("A7", view, {"A1": a1, "A5": p5})
    role = world["b3"]["core"]["a7_role"]
    assert a7["native_status"] == role["overall"] == "PARTIAL" and a7["projection"]["reasons"] == role["reasons"]
    assert a7["projection"]["economics_supported"] is False and a7["projection"]["wallet_economics"] == "NOT_CLAIMED"
    assert a7["projection"]["point_mechanics_status"] == world["b3"]["core"]["point_mechanics"]["status"]
    # delivery is not the native disposition: a natively refused A6 is a consumed delivery carrying REFUSED
    refused = copy.deepcopy(view)
    refused["b2"]["core"]["a6_wallet"] = world["refused_a6"]
    out = NR.consume("A6", refused, {"A1": a1})
    assert out["native_status"] == "REFUSED" and out["projection"]["native_reason"] == "NATIVE_REFUSED:PROFILE_REFERENCE_INVALID"
    assert out["projection"]["assessment_id"] is None and out["projection"]["economics_claimed"] is False
    for status in ("REFUSED", "INSUFFICIENT"):
        bad = copy.deepcopy(view)
        bad["b2"]["core"]["a5_relations"]["status"] = status
        assert NR.consume("A5", bad, {"A1": a1})["native_status"] == status  # never promoted to ADMITTED
    # wallet-shaped, condition-shaped and raw summary material never reaches a projection
    text = json.dumps([a5, a6, a7, out]).lower()
    assert T.WALLET.lower() not in text and T.OTHER_WALLET.lower() not in text
    assert world["core"]["shared_case"]["target"]["condition_id"].lower() not in text
    # closed refusals: each defect refuses that role (never a partial delivery)
    def refuse(role, mutate, deps):
        bad = copy.deepcopy(view)
        mutate(bad)
        with pytest.raises(NR.RoleRefusal) as excinfo:
            NR.consume(role, bad, deps)
        return str(excinfo.value)
    assert refuse("A5", lambda v: v["b2"]["core"]["shared_case"].update(grounding_receipt_id="srcground:sha256:" + "9" * 64),
                  {"A1": a1}) == "A5_SHARED_CASE_MISMATCH"
    assert refuse("A5", lambda v: v["b2"]["core"]["a5_relations"]["a7_pointer"][0].update(tradable=True), {"A1": a1}) \
        == "A5_POINTER_AUTHORITY_INVALID"
    assert refuse("A6", lambda v: v["b2"]["core"]["shared_case"].update(grounding_receipt_id="x"), {"A1": a1}) \
        == "A6_SHARED_CASE_MISMATCH"
    assert refuse("A7", lambda v: v["b3"]["core"]["a7_role"].update(economics_supported=True), {"A1": a1, "A5": p5}) \
        == "A7_AUTHORITY_INVALID"
    assert refuse("A7", lambda v: v["b3"]["core"]["b2_lineage"].update(b2_receipt_id=B2_ID), {"A1": a1, "A5": p5}) \
        == "A7_B2_LINEAGE_MISMATCH"
    assert refuse("A7", lambda v: v["b3"]["core"]["b2_lineage"]["selected"].update(model_id="other-model"),
                  {"A1": a1, "A5": p5}) == "A7_MODEL_NOT_A5_ADMITTED"
    assert refuse("A7", lambda v: v["b3"]["core"]["b2_lineage"].update(venue_snapshot_id="venue:x"), {"A1": a1, "A5": p5}) \
        == "A7_SNAPSHOT_MISMATCH"
    assert refuse("A7", lambda v: None, {"A1": dict(a1, target_sha256="0" * 64), "A5": p5}) == "A7_TARGET_MISMATCH"
    assert refuse("A5", lambda v: v["b2"]["core"].pop("a5_relations"), {"A1": a1}) == "NATIVE_FIELD_SHAPE_INVALID"
    assert refuse("A7", lambda v: v.update(b3=None), {"A1": a1, "A5": p5}) == "NATIVE_FIELD_SHAPE_INVALID"
    assert refuse("A6", lambda v: v["b2"]["core"]["a6_wallet"].update(status=True), {"A1": a1}) == "NATIVE_STATUS_INVALID"
    # A8/A9 have no consumer at all: they are dependency skips, never a stub delivery
    for role in ("A8", "A9", "A0"):
        assert stop(NR.consume, role, view, {}) == "ROLE_HAS_NO_CONSUMER"
    assert set(NR.CONSUMERS) == set(NR.ROLES[:7]) and len({id(f) for f in NR.CONSUMERS.values()}) == 7
    # A1-A4 run on the real pinned B1-A / W01 receipts (same builders the tools tests use)
    from tests.tools.alpha import test_run_nine_role_coordination as TT
    views = TT.pinned_views()
    if views is None:
        pytest.skip("pinned part: real B1-A/W01 receipts need POLYMARKET_HERMES_PIN_ROOT (D001)")
    real = views["b3"]
    p1 = NR.consume("A1", real, {})
    spine = real["spine"]["core"]
    assert p1["native_status"] == spine["a1_scout"]["status"] == "ADMITTED"
    assert p1["projection"]["target_market_id"] == spine["a1_scout"]["target"]["market_id"]
    p2 = NR.consume("A2", real, {"A1": p1["projection"]})
    assert p2["projection"]["source_allowlist"] == spine["a2_research"]["source_allowlist"]
    assert p2["projection"]["sdk_real_network_requests"] == 0 and p1["source"]["receipt_id"] == p2["source"]["receipt_id"]
    assert p1["projection"] != p2["projection"] and p1["source"]["member"] != p2["source"]["member"]  # distinct projections
    bad = copy.deepcopy(real)
    bad["spine"]["core"]["a2_research"]["source_allowlist"] = []
    with pytest.raises(NR.RoleRefusal, match="A2_LINEAGE_MISMATCH"):
        NR.consume("A2", bad, {"A1": p1["projection"]})
    bad = copy.deepcopy(real)
    bad["spine"]["core"]["a1_scout"]["target"]["candidate_id"] = "other"
    with pytest.raises(NR.RoleRefusal, match="A1_LINEAGE_MISMATCH"):
        NR.consume("A1", bad, {})


# ------------------------------------------------------------------ R011


def test_b4_capability_and_successor_boundaries():
    rows = NR.capability()
    assert set(rows["touched"]) == {"R3-21", "R3-29"} and rows["other_34_capability_ids"] == "UNCHANGED"
    assert rows["pr_268"] == "SEPARATE_UNTOUCHED" and rows["w07_source_rights"] == "OPEN"
    assert rows["lane_b"] == "R3-15/R3-16/R3-17/R3-26_SEPARATELY_OWNED_UNTOUCHED"
    for row in rows["touched"].values():
        assert (row["original_status"], row["disposition"], row["owner_disposition"]) == \
            ("CONCEPT_ONLY", "PARTIAL_CONCEPT_UNACCEPTED", "PENDING")
        assert row["invoked"] is False and row["installed"] is False and row["value_verified"] is False
        assert row["upstream_adoption"] is False
    # the frozen 36-row roadmap matrix is the source for both pins and is byte-unchanged
    raw = X.CSV.read_bytes()
    assert X.CSV_SHA256 in (hashlib.sha256(raw).hexdigest(), hashlib.sha256(raw.replace(b"\r\n", b"\n")).hexdigest())
    lines = raw.decode("utf-8").splitlines()
    ids = [line.split(",", 1)[0] for line in lines[1:] if line.strip()]
    assert len(ids) == 36 == len(set(ids))
    for key, row in NR.CAPABILITY.items():
        found = [line for line in lines if line.startswith(key + ",")]
        assert len(found) == 1 and row["repository"] + "," + row["commit"] in found[0] and ",CONCEPT_ONLY," in found[0]
    # successor boundary: A8/A9 are dependency skips with frozen non-authorizing handoffs only
    plan_doc = plan_for(("B3", B3_ID, "FULL_SHARED_CASE"))
    events, projections = simulate(plan_doc, {})
    state = NR.replay(plan_doc, events)
    core = NR.build_core(code_identity="code:sha256:" + "0" * 64, plan_doc=plan_doc, state=state,
                         lineages={"case-01": fake_lineage("case-01")}, projections=projections)
    hand = core["cases"][0]["handoffs"]
    assert set(hand) == {"A8", "A9"} and [hand[r]["dependency"] for r in ("A8", "A9")] == ["W09_PENDING", "W10_PENDING"]
    assert all(h["authorizes"] == "NOTHING" and set(h) == {"campaign_id", "case_id", "task_id", "version",
                                                            "evidence_consumer_ids", "dependency", "authorizes"}
               for h in hand.values())
    assert hand["A8"]["evidence_consumer_ids"] == [t["consumer_id"] for t in core["cases"][0]["tasks"] if t["consumer_id"]]
    assert "A8" not in NR.CONSUMERS and "A9" not in NR.CONSUMERS
    spec = json.loads((REPO_ROOT / "docs" / "wp_specs" / NR.WP_ID / "wp_spec.json").read_text(encoding="utf-8"))
    assert spec["successor_boundary"]["next_wp"] == "S10-CAP-LEARNING-ROUTING-01" and spec["successor_boundary"]["separately_gated"]
    # no learning, routing mutation, prompt optimisation, provider, network or protected import in the new surfaces
    forbidden = re.compile(r"^\s*(from|import)\s+(src\.(research_runtime|execution_gateway|paper_trading|risk_engine|live_pilot|"
                           r"strategy_lifecycle|exploratory_gate_c|data_layer\.polymarket)|tools\.(hermes|polymarket|execution|"
                           r"deployment)|requests|httpx|urllib|socket|subprocess|openai|anthropic)", re.M)
    for rel in ("src/data_layer/analytical_research/nine_role_coordination.py", "tools/alpha/run_nine_role_coordination.py"):
        text = (REPO_ROOT / rel).read_text(encoding="utf-8")
        assert forbidden.search(text) is None, rel
        assert "learning_feedback" not in text and "experiment_registry" not in text, rel


# ------------------------------------------------------------------ R012


def test_b4_terminal_denominators_and_failures():
    plan_doc = plan_for(("B3", B3_ID, "FULL_SHARED_CASE"), ("B2", B2_ID, "RELATION_REVIEW"))
    outcomes = {"case-01": {"A2": ("COMPLETED_CONSUMED", "REFUSED"), "A6": ("FAILED", "CONSUMER_EXCEPTION"),
                            "A7": ("REFUSED", "A7_AUTHORITY_INVALID")},
                "case-02": {"A4": ("QUARANTINED", NR.QUARANTINE_REASON)}}
    events, projections = simulate(plan_doc, outcomes)
    state = NR.replay(plan_doc, events)
    core = NR.build_core(code_identity="code:sha256:" + "0" * 64, plan_doc=plan_doc, state=state,
                         lineages={s: fake_lineage(s) for s in ("case-01", "case-02")}, projections=projections)
    one, two = core["cases"][0]["counts"], core["cases"][1]["counts"]
    assert one["planned_slots"] == two["planned_slots"] == 9 and core["totals"]["planned_slots"] == 18
    for c in (one, two, core["totals"]):
        assert sum(c[s.lower()] for s in NR.DELIVERY) == c["planned_slots"]  # mutually exclusive, nothing unfinished
    assert (one["completed_consumed"], one["failed"], one["refused"], one["skipped"]) == (5, 1, 1, 2)
    assert one["native_status_counts"] == {"ADMITTED": 4, "REFUSED": 1}  # consumed native refusal stays REFUSED
    assert (two["completed_consumed"], two["quarantined"], two["skipped"]) == (3, 1, 5)
    assert two["skip_reason_counts"] == {"NOT_REQUESTED": 1, "PREREQUISITE_NOT_CONSUMED:A4": 1, "B3_NOT_SUPPLIED": 1,
                                         "W09_PENDING": 1, "W10_PENDING": 1}
    assert one["attempted"] == 7 and two["attempted"] == 4  # attempts are derived from the journal, never asserted
    rows = core["cases"][0]["tasks"]
    assert all((r["attempt_id"] is None) == (r["status"] == "SKIPPED") for r in rows)
    assert all((r["projection"] is None) == (r["status"] != "COMPLETED_CONSUMED") for r in rows)
    assert core["claims"] == NR.CLAIMS and not any(core["claims"].values())
    assert core["new_activity"] == {"provider_calls": 0, "hermes_dispatches": 0, "model_calls": 0, "network_calls": 0,
                                    "orders": 0, "capital_usd": 0}
    assert core["usage"]["elapsed"] == "UNKNOWN_NOT_OBSERVED" and core["journal"]["event_count"] == len(events)
    assert "nine functional agents" not in json.dumps(core).lower() and core["journal_evidence"].endswith("NOT_EXTERNAL_ATTESTATION")
    # an incomplete campaign or a lost projection/lineage never seals
    partial = NR.replay(plan_doc, events[:-1])
    assert not partial["complete"]
    assert stop(NR.build_core, code_identity="c", plan_doc=plan_doc, state=partial, lineages={}, projections={}) \
        == "CAMPAIGN_INCOMPLETE"
    lost = dict(projections)
    lost.pop(("case-01", "A1"))
    assert stop(NR.build_core, code_identity="c", plan_doc=plan_doc, state=state,
                lineages={s: fake_lineage(s) for s in ("case-01", "case-02")}, projections=lost) == "UNCONSUMED_COMPLETION"
    assert stop(NR.build_core, code_identity="c", plan_doc=plan_doc, state=state, lineages={"case-01": fake_lineage("case-01")},
                projections=projections) == "LINEAGE_LOST"
    # invalid transitions and out-of-order events refuse with closed codes (failure precedence: shape -> order)
    def forged(index: int, **changes) -> list:
        bad = copy.deepcopy(events[:index])
        envelope = copy.deepcopy(events[index]["event"])
        for key, value in changes.items():
            if key == "payload":
                envelope["payload"].update(value)
            else:
                envelope[key] = value
        return bad + [{"event_id": NR.ident("event", envelope), "event": envelope}]
    started = next(i for i, e in enumerate(events) if e["event"]["type"] == "ROLE_STARTED")
    skipped = next(i for i, e in enumerate(events) if e["event"]["type"] == "ROLE_SKIPPED")
    cases = {
        "JOURNAL_SEQUENCE_INVALID": forged(3, seq=9), "JOURNAL_CHAIN_BROKEN": forged(3, prev=events[1]["event_id"]),
        "JOURNAL_ORDER_INVALID": forged(0, type="CASE_VERIFIED", payload={"lineage_sha256": "d" * 64}),
        "JOURNAL_PAYLOAD_INVALID": forged(1, payload={"lineage_sha256": "D" * 64}),
        "JOURNAL_IDENTITY_INVALID": forged(0, payload={"case_id": plan_doc["plan"]["cases"][1]["case_id"]}),
        "JOURNAL_EVENT_INVALID": forged(0, schema_id="other"),
    }
    for code, bad in cases.items():
        assert stop(NR.replay, plan_doc, bad) == code, code
    assert stop(NR.replay, plan_doc, events[:3] + [dict(events[3], event_id=NR.PREFIX["event"] + "0" * 64)]) \
        == "JOURNAL_EVENT_ID_INVALID"
    assert stop(NR.replay, plan_doc, events + [events[-1]]) in ("JOURNAL_SEQUENCE_INVALID", "JOURNAL_OVERRUN")
    assert stop(NR.replay, plan_doc, events[:started] + events[started + 1:]) in ("JOURNAL_SEQUENCE_INVALID",
                                                                                  "JOURNAL_CHAIN_BROKEN")
    assert stop(NR.replay, plan_doc, [events[1]]) == "JOURNAL_SEQUENCE_INVALID"
    # a skip whose closed reason differs from the deterministic decision, or a start where routing says skip
    skip_env = events[skipped]["event"]
    wrong = copy.deepcopy(skip_env)
    wrong["payload"]["reason"] = "NOT_REQUESTED" if skip_env["payload"]["reason"] != "NOT_REQUESTED" else "W09_PENDING"
    assert stop(NR.replay, plan_doc, events[:skipped] + [{"event_id": NR.ident("event", wrong), "event": wrong}]) \
        == "JOURNAL_ORDER_INVALID"
    task = next(t for t in plan_doc["plan"]["cases"][0]["tasks"] if t["role"] == skip_env["payload"]["role"])
    start = dict(skip_env, type="ROLE_STARTED", payload={k: v for k, v in skip_env["payload"].items() if k != "reason"}
                 | {"attempt_id": task["attempt_id"]})
    assert stop(NR.replay, plan_doc, events[:skipped] + [{"event_id": NR.ident("event", start), "event": start}]) \
        == "JOURNAL_ORDER_INVALID"
    # a completed delivery that misstates its dependencies or consumer id; a quarantine with a free-form reason
    done = next(i for i, e in enumerate(events) if e["event"]["type"] == "ROLE_COMPLETED_CONSUMED"
                and e["event"]["payload"]["role"] == "A2")
    assert stop(NR.replay, plan_doc, forged(done, payload={"dependencies": []})) == "JOURNAL_PAYLOAD_INVALID"
    assert stop(NR.replay, plan_doc, forged(done, payload={"projection_sha256": "e" * 64})) == "JOURNAL_CONSUMER_ID_INVALID"
    assert stop(NR.replay, plan_doc, forged(done, payload={"native_status": 1})) == "JOURNAL_PAYLOAD_INVALID"
    quarantined = next(i for i, e in enumerate(events) if e["event"]["type"] == "ROLE_QUARANTINED")
    assert stop(NR.replay, plan_doc, forged(quarantined, payload={"reason": "RETRY_LATER"})) == "JOURNAL_PAYLOAD_INVALID"
    assert stop(NR.replay, plan_doc, events + [events[0]] * (NR.MAX_EVENTS + 1 - len(events))) == "JOURNAL_TOO_LONG"
    # an interrupted prefix replays to exactly one in-flight subject, whose only terminal is QUARANTINED
    prefix, _ = simulate(plan_doc, outcomes, stop_at=started + 1)
    flight = NR.replay(plan_doc, prefix)
    assert flight["in_flight"] == ("ROLE", 0, "A1") and not flight["complete"]
    kind, payload = NR.quarantine_event(plan_doc, flight)
    assert kind == "ROLE_QUARANTINED" and payload["reason"] == NR.QUARANTINE_REASON
    assert stop(NR.quarantine_event, plan_doc, state) == "NOTHING_IN_FLIGHT"
