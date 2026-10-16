"""SYNTHETIC_ONLY fixtures; real native verified stores, no provider or account."""
import ast
import copy
import hashlib
import json
from pathlib import Path
import runpy
import socket
import subprocess
import sys
from unittest.mock import patch

import pytest

from src.research_runtime import autonomous_opportunity_cycle as cycle
from src.data_layer.analytical_research import alpha_factory as af
from src.data_layer.analytical_research import alpha_factory_registry as registry
from src.strategy_lifecycle import (
    build_strategy_family, build_strategy_version, initialize_strategy_lifecycle_store,
)
from src.execution_feasibility import build_execution_intent
import src.exploratory_gate_c as gate
from tests.data_layer.analytical_research.test_alpha_factory_records import candidate_input
from tests.exploratory_gate_c import test_exploratory_gate_c as native

ROOT = Path(__file__).resolve().parents[2]


def world(tmp_path, *, allocation=True, hermes=True, policy=None):
    tmp_path.mkdir(parents=True, exist_ok=True)
    lifecycle, manager, alpha = (tmp_path / name for name in ("life.sqlite3", "hermes.sqlite3", "alpha.sqlite3"))
    assert initialize_strategy_lifecycle_store(lifecycle).is_valid
    native.sm.initialize_hermes_strategy_manager_store(manager)
    assert registry.initialize_alpha_factory_registry(alpha).is_valid
    candidates, versions, families = [], [], []
    for name in ("first", "second"):
        scope = f"auto01-{name}"
        candidate = af.build_opportunity_candidate(candidate_input(
            subject_refs=[f"market:polymarket:{native.GAMMA_ID}", f"token:polymarket:{native.TOKEN}"],
            scope_key=scope, novelty_dimensions={"subject_keys": [name], "scope_key": scope,
                                                "mechanism_key": "fixture-mechanism"})).record
        assert candidate is not None
        candidates.append(candidate)
        family = build_strategy_family(family_key=scope, family_label=name, created_time_ns=1,
                                       creation_provenance="synthetic:fixture")
        families.append(family)
        versions.append(build_strategy_version(strategy_family_id=family.strategy_family_id,
            parent=None, strategy_label=name, evidence_posture="NOVEL_EXPLORATORY",
            strategy_code_identity=f"synthetic:{name}", strategy_spec=native.STRATEGY_SPEC,
            adaptive_bounds=native.BOUNDS, evidence_refs=(candidate.candidate_id,), created_time_ns=2,
            creation_provenance="synthetic:fixture"))
    assert registry.append_alpha_factory_records(alpha, tuple(candidates)).is_valid
    policy = policy or native._policy()
    w = native.World(lifecycle, manager, families[0], versions[0], families[1], versions[1], policy, None)
    for record in (*families, *versions, policy, native._activate(policy)):
        w.append(record)
    if allocation:
        for version in versions:
            w.append(native._allocation(version, policy, valid_until=policy.expires_at_ns))
    assessments = [w.assess(version=v, t=native.T0 - 1_000_000) for v in versions] if hermes else []
    menu = [dict(candidate_id=c.candidate_id, strategy_version_id=v.strategy_version_id,
                 gamma_market_id=native.GAMMA_ID, condition_id=native.COND, token_id=native.TOKEN)
            for c, v in zip(candidates, versions)]
    clocks = dict(proof_level="SYNTHETIC_ONLY", information_cutoff_ns=native.T0,
                  produced_at_ns=native.T0, expires_at_ns=native.AT + 1_000_000_000)
    proposal = dict(action="TRADE", **clocks, candidate_id=candidates[0].candidate_id,
        strategy_version_id=versions[0].strategy_version_id, hermes_assessment_id=None,
        context_sha256=None, active_policy_id=policy.policy_id, side="BUY", execution_style="PASSIVE_MAKER",
        order_type="GTC", requested_shares="10", price_limit="0.51", post_only=True,
        gtd_expiration_unix_s=None)
    if assessments:
        proposal.update(hermes_assessment_id=assessments[0].assessment_id,
                        context_sha256=assessments[0].strategy_lifecycle_context_sha256)
    args = dict(lifecycle_store_path=lifecycle, hermes_manager_store_path=manager, alpha_registry_path=alpha,
        candidate_menu=menu, choice=json.dumps(proposal), venue_snapshots=(native.snap(),),
        evaluated_at_ns=native.AT, information_cutoff_ns=native.T0, deadline_ns=native.AT + 2_000_000_000)
    return w, args, proposal, assessments


def run(args, proposal=None, **changes):
    return cycle.evaluate_once(**dict(args, **({"choice": json.dumps(proposal)} if proposal is not None else {}), **changes))


def closed(receipt):
    assert receipt["status"] in {"REJECTED", "INCONCLUSIVE", "NO_TRADE"}
    assert receipt["preview_permit"] is None and receipt["no_order"] and receipt["no_live"]
    assert receipt["receipt_id"].startswith("decisioncycle:sha256:")


def test_hermes_choice_controls_candidate_and_exact_intent(tmp_path):
    w, args, proposal, assessments = world(tmp_path)
    first = run(args)
    assert first["status"] == "ELIGIBLE_PREVIEW", first
    proposal.update(args["candidate_menu"][1])
    # Market identities live only in the offered menu, not untrusted choice fields.
    for key in ("gamma_market_id", "condition_id", "token_id"):
        proposal.pop(key)
    proposal.update(hermes_assessment_id=assessments[1].assessment_id,
        context_sha256=assessments[1].strategy_lifecycle_context_sha256,
        side="SELL", requested_shares="11", price_limit="0.55")
    second = run(args, proposal)
    assert second["status"] == "ELIGIBLE_PREVIEW", second
    assert second["candidate_id"] == args["candidate_menu"][1]["candidate_id"] != first["candidate_id"]
    exact = build_execution_intent(strategy_version=w.other_version,
        gamma_market_id=native.GAMMA_ID, condition_id=native.COND, token_id=native.TOKEN,
        side="SELL", execution_style="PASSIVE_MAKER", order_type="GTC", requested_shares="11",
        price_limit="0.55", post_only=True, information_cutoff_ns=native.T0, max_public_data_age_ns=native.AGE)
    assert second["execution_intent"] == exact.to_mapping()
    for action in ("NO_TRADE", "PAUSE", "REASSESS"):
        abstain = {key: proposal[key] for key in cycle._CLOCK_KEYS}
        abstain["action"] = action
        receipt = run(args, abstain)
        closed(receipt)
        assert receipt["status"] == "NO_TRADE" and receipt["reason_codes"] == [action]
        assert receipt["requested_choice_sha256"] is not None


def test_native_exec_feas_and_gate_c_only_preview(tmp_path, monkeypatch):
    _, args, proposal, _ = world(tmp_path)
    calls = []
    for name in ("build_execution_intent", "assess_execution_feasibility", "evaluate_exploratory_gate_c",
                 "build_exploratory_gate_c_permit"):
        owner = gate if name in ("evaluate_exploratory_gate_c", "build_exploratory_gate_c_permit") else cycle
        original = getattr(owner, name)
        def observed(*a, _fn=original, _name=name, **kw):
            calls.append(_name)
            return _fn(*a, **kw)
        monkeypatch.setattr(owner, name, observed)
    receipt = run(args)
    assert calls == ["build_execution_intent", "assess_execution_feasibility", "evaluate_exploratory_gate_c",
                     "build_exploratory_gate_c_permit"]
    permit = receipt["preview_permit"]
    assert permit["execution_intent_id"] == receipt["execution_intent"]["execution_intent_id"]
    assert permit["hermes_assessment_id"] == receipt["hermes_assessment_id"]
    assert permit["valid_until_ns"] <= native.PUBLIC_DEADLINE
    assert receipt["preview_authority"] == "NON_EXECUTABLE_WITHOUT_SEPARATE_LIVE_AUTHORITY"
    assert receipt["model_origin_proof"] == "UNVERIFIED" and receipt["proof_level"] == "SYNTHETIC_ONLY"
    calls.clear()
    bad = run(args, dict(proposal, requested_shares="1"))
    closed(bad)
    assert "build_exploratory_gate_c_permit" not in calls and bad["native_reasons"]["execution"]
    proposal.update(order_type="GTD", gtd_expiration_unix_s=native.T0 // 1_000_000_000 + 180)
    assert run(args, proposal)["status"] == "ELIGIBLE_PREVIEW"


def test_missing_or_stale_policy_hermes_venue_rejects(tmp_path):
    w, args, proposal, _ = world(tmp_path / "main")
    for changes in (
        {"venue_snapshots": ()},
        {"venue_snapshots": (native.snap(gamma=native.gamma_doc(feeSchedule={"rate": 0.1, "exponent": 99})),)},
        {"venue_snapshots": (native.snap(clob=native.book_doc(timestamp=str(native.BOOK_MS - 60000))),)},
        {"venue_snapshots": (native.snap(clob=native.book_doc(min_order_size="50")),)},
    ):
        closed(run(args, **changes))
    for changes in (dict(price_limit="0.511"), dict(requested_shares="100")):
        closed(run(args, dict(proposal, **changes)))
    assert "ORDER_NOTIONAL_EXCEEDS_POLICY_ORDER_MAX" in run(
        args, dict(proposal, requested_shares="100"))["native_reasons"]["gate_c"]
    closed(run(args, max_hermes_age_ns=1))
    old = copy.deepcopy(proposal)
    w.assess(t=native.T0 - 500000)
    closed(run(args, old))  # latest required even though context is unchanged
    w.append(native._pause(w.version))
    closed(run(args, proposal))
    for name, kw in (("allocation", {"allocation": False}), ("hermes", {"hermes": False}),
                     ("expired", {"policy": native._policy(expires=native.T0 - 1)})):
        _, other, _, _ = world(tmp_path / name, **kw)
        closed(run(other))
    w2, other, choice2, _ = world(tmp_path / "pause")
    w2.append(native._pause(w2.version))
    assessment = w2.assess(t=native.T0 - 500000)
    choice2.update(hermes_assessment_id=assessment.assessment_id, context_sha256=assessment.strategy_lifecycle_context_sha256)
    rejected = run(other, choice2)
    closed(rejected)
    assert rejected["native_reasons"]["strategy_capacity"]
    w2.append(native._health(w2.version, "NEW", "QUARANTINED", t=200))
    assessment = w2.assess(t=native.T0 - 200000)
    choice2.update(hermes_assessment_id=assessment.assessment_id, context_sha256=assessment.strategy_lifecycle_context_sha256)
    closed(run(other, choice2))
    w3, other, choice3, _ = world(tmp_path / "no-policy")
    w3.append(native.build_portfolio_policy_receipt(action="REVOKE", policy_id=w3.policy.policy_id,
        previous_active_policy_id=w3.policy.policy_id, human_authorization_ref="synthetic:revoke", created_time_ns=2000))
    closed(run(other, choice3))
    w4, other, choice4, _ = world(tmp_path / "soft-pause")
    assessment = w4.assess(native.judgment(lifecycle_action="REDUCE", risk_direction="DECREASE"),
                           t=native.T0 - 500000)
    choice4.update(hermes_assessment_id=assessment.assessment_id, context_sha256=assessment.strategy_lifecycle_context_sha256)
    rejected = run(other, choice4)
    closed(rejected)
    assert rejected["exposure_posture"] == "NO_NEW_EXPOSURE"


def test_untrusted_choice_and_forged_lineage_fail_closed(tmp_path, monkeypatch):
    w, args, proposal, _ = world(tmp_path)
    raw = json.dumps(proposal)
    for bad in ("", "[]", '{"action":"NO_TRADE","action":"TRADE"}', raw[:-1] + ',"price_limit":NaN}',
                raw[:-1] + ',"secret":"/private/wallet"}', json.dumps(dict(proposal, requested_shares=10)),
                json.dumps(dict(proposal, price_limit="NaN")), json.dumps(dict(proposal, price_limit="1e-2")),
                json.dumps(dict(proposal, price_limit="1.1")), json.dumps(dict(proposal, requested_shares="-1")),
                json.dumps(dict(proposal, order_type="MARKET")), json.dumps(dict(proposal, action="")),
                json.dumps(dict(proposal, proof_level="REAL_PROVIDER")),
                json.dumps(dict(proposal, expires_at_ns=native.T0)),
                json.dumps(dict(proposal, information_cutoff_ns=native.T0-1)),
                json.dumps(dict(proposal, candidate_id="forged")),
                json.dumps(dict(proposal, hermes_assessment_id="hermes:forged")),
                json.dumps(dict(proposal, context_sha256="f"*64)),
                json.dumps(dict(proposal, strategy_version_id=w.other_version.strategy_version_id))):
        receipt = run(args, choice=bad)
        closed(receipt)
        assert "/private/wallet" not in json.dumps(receipt)
    for changes in ({"candidate_menu": args["candidate_menu"] * 5},
                    {"candidate_menu": args["candidate_menu"] * 2},
                    {"deadline_ns": native.T0}, {"evaluated_at_ns": True},
                    {"venue_proof_level": "SOURCE_VERIFIED"}):
        closed(run(args, **changes))
    forged = copy.copy(args["venue_snapshots"][0])
    object.__setattr__(forged, "venue_snapshot_id", "forged")
    closed(run(args, venue_snapshots=(forged,)))
    closed(run(args, hermes_manager_store_path=tmp_path / "missing-private-store.sqlite3"))
    assert not (tmp_path / "missing-private-store.sqlite3").exists()
    menu = copy.deepcopy(args["candidate_menu"])
    menu[0]["condition_id"] = "0x" + "cd"*32
    closed(run(args, candidate_menu=menu))
    menu = copy.deepcopy(args["candidate_menu"])
    menu[0]["candidate_id"] = "alphacandidate:sha256:" + "f"*64
    closed(run(args, candidate_menu=menu))
    original = gate.evaluate_exploratory_gate_c
    def concurrent(**kw):
        w.assess(t=native.T0-500000)
        return original(**kw)
    monkeypatch.setattr(gate, "evaluate_exploratory_gate_c", concurrent)
    assert run(args)["reason_codes"] == ["STORE_CHANGED_DURING_CYCLE"]


def test_content_address_replay_no_side_effects(tmp_path, monkeypatch):
    _, args, proposal, _ = world(tmp_path)
    def digests():
        return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in tmp_path.rglob("*") if p.is_file()}
    before = digests()
    def forbidden(*a, **kw):
        raise AssertionError("forbidden side effect")
    with monkeypatch.context() as m:
        m.setattr(socket, "socket", forbidden)
        m.setattr(subprocess, "Popen", forbidden)
        first = run(args)
        second = run(args)
    assert first["status"] == "ELIGIBLE_PREVIEW" and first == second
    assert cycle.canonical_json_bytes(first) == cycle.canonical_json_bytes(second)
    preimage = dict(first); preimage.pop("receipt_id")
    assert first["receipt_id"] == "decisioncycle:sha256:" + hashlib.sha256(cycle.canonical_json_bytes(preimage)).hexdigest()
    for other in (run(args, dict(proposal, requested_shares="11")),
                  run(args, information_cutoff_ns=native.T0+1,
                      choice=json.dumps(dict(proposal, information_cutoff_ns=native.T0+1, produced_at_ns=native.T0+1))),
                  run(args, venue_snapshots=(native.snap(clob=native.book_doc(last_trade_price="0.50")),))):
        assert other["receipt_id"] != first["receipt_id"]
    assert before == digests()
    assert str(tmp_path) not in json.dumps(first)
    imports = {n.module for n in ast.walk(ast.parse(Path(cycle.__file__).read_text())) if isinstance(n, ast.ImportFrom)}
    assert not any(n and ("execution_gateway" in n or "paper_trading" in n) for n in imports)
    script = '''import sys
def guard(name,args):
 if name.startswith(("socket.","subprocess.","sqlite3.connect","os.system","os.putenv")): raise RuntimeError(name)
sys.addaudithook(guard)
import src.research_runtime.autonomous_opportunity_cycle
print("IMPORT_NO_IO_PASS")
'''
    result = subprocess.run([sys.executable, "-B", "-c", script], cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0 and "IMPORT_NO_IO_PASS" in result.stdout, result.stderr


def test_architecture_exact_approval_preserves_all_original_guards(tmp_path):
    guard = runpy.run_path(str(ROOT / "tests/test_architecture_boundaries.py"))
    scopes = guard["APPROVED_SRC_SCOPES"]
    target = "src/research_runtime/autonomous_opportunity_cycle.py"
    sibling = "src/research_runtime/autonomous_opportunity_cycle_unapproved.py"
    assert scopes.count(target) == 1
    assert scopes[-3:] == ("src/strategy_lifecycle", "src/execution_feasibility", "src/exploratory_gate_c")
    names = [f"test_wp{wp}_does_not_add_new_src_files" for wp in (88,91,92,93,94,115)]
    for path, rejected in ((target, False), (sibling, True)):
        with patch.object(subprocess, "run", return_value=subprocess.CompletedProcess([], 0, path+"\n", "")):
            for name in names:
                if rejected:
                    with pytest.raises(AssertionError): guard[name]()
                else:
                    guard[name]()
    guard["test_no_executable_files_exist_under_src_except_approved_scope"]()
    guard["test_strategy_lifecycle_is_only_new_approved_source_family"]()
    # Original filesystem assertion must reject the sibling in an isolated synthetic root.
    fake = tmp_path / sibling
    fake.parent.mkdir(parents=True); fake.write_text("# synthetic unapproved sibling\n")
    fs = guard["test_no_executable_files_exist_under_src_except_approved_scope"]
    with patch.dict(fs.__globals__, ROOT=tmp_path):
        with pytest.raises(AssertionError): fs()
    source = subprocess.run(["git", "show", "7d1e817793612ffc607ff4278abc4a6c71eb9acd:tests/test_architecture_boundaries.py"],
                            cwd=ROOT, capture_output=True, text=True, check=True).stdout
    modified = (ROOT / "tests/test_architecture_boundaries.py").read_text()
    addition = '    # S10-HERMES-AUTO-01: exact offline opportunity connector only.\n    "'+target+'",\n'
    assert modified.replace(addition, "", 1) == source
