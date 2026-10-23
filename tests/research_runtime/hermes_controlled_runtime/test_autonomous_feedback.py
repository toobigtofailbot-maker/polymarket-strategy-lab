"""S10-HERMES-AUTO-02 provenance, verified paper feedback and one-cycle evidence.

All outcomes are SYNTHETIC fixtures over real native stores: offline injected Stage B,
FakeHermesBackend strategy manager and a simulated WP173 research-paper session.
"""
import hashlib
import json
from pathlib import Path
import runpy
import subprocess
from unittest.mock import patch

import pytest

from src.paper_trading import PaperEngine, PaperStore
from src.research_runtime import autonomous_opportunity_cycle as cycle
from src.research_runtime.hermes_controlled_runtime import autonomous_feedback as fb
from src.research_runtime.hermes_controlled_runtime import strategy_manager as sm
from src.research_runtime.hermes_controlled_runtime import tool_free_stage_b as tf
from tests.exploratory_gate_c import test_exploratory_gate_c as native
from tests.paper_trading.conftest import generous_limits, paper_book
from tests.paper_trading.test_models import _research_binding, _research_intent
from tests.research_runtime.hermes_controlled_runtime.test_tool_free_stage_b import RECORDED_REPORT, mutated
from tests.research_runtime.test_autonomous_opportunity_cycle import BASE_SHA, MODEL, closed, produce, world

ROOT = Path(__file__).resolve().parents[3]
CUTOFF = "2026-10-01T06:00:00Z"  # strictly after the fixture's INITIAL_ASSESSMENT cutoff


def reid(record, **changes):
    value = dict(record, **changes)
    value.pop("provenance_id")
    value["provenance_id"] = fb.PROVENANCE_PREFIX + fb._digest(value)
    return value


def test_provenance_rejects_model_self_attestation_and_tampering(tmp_path):
    w, args, proposal, _ = world(tmp_path / "w")
    request, result, record, content = produce(tmp_path, args, proposal)
    # Offline injection is always labelled offline/unverified, however valid the JSON.
    assert (record["transport_mode"], record["producer_witness_class"], record["model_origin_proof"],
            record["real_provider"]) == ("OFFLINE_INJECTED", "LOCAL_OFFLINE_PRODUCER", "MODEL_ORIGIN_UNVERIFIED",
                                         "REAL_PROVIDER_NOT_INVOKED")
    assert content not in json.dumps(record)

    def bound(rec, choice=content):
        return cycle.evaluate_once(**dict(args, choice=choice, producer_evidence=rec))
    assert bound(record)["status"] == "ELIGIBLE_PREVIEW"
    other = w.other_version.strategy_version_id
    for rec, code in (
        (reid(record, transport_mode="REAL_PROVIDER"), "PROVENANCE_ORIGIN_FORGED"),
        (reid(record, model_origin_proof="MODEL_ORIGIN_VERIFIED"), "PROVENANCE_ORIGIN_FORGED"),
        (reid(record, producer_witness_class="PROVIDER_ATTESTED"), "PROVENANCE_ORIGIN_FORGED"),
        (reid(record, real_provider="REAL_PROVIDER_INVOKED"), "PROVENANCE_ORIGIN_FORGED"),
        (reid(record, promotion_gate="PROMOTED"), "PROVENANCE_ORIGIN_FORGED"),
        (reid(record, hermes_commit="0" * 40), "PROVENANCE_ORIGIN_FORGED"),
        (dict(record, model_label="other-model"), "PROVENANCE_TAMPERED"),
        (dict(record, raw_output_sha256="0" * 64), "PROVENANCE_TAMPERED"),
        (dict(record, usage={"cost_usd": "0.01"}), "PROVENANCE_FIELDS_INVALID"),
        ({k: v for k, v in record.items() if k != "tool_surface_fingerprint"}, "PROVENANCE_FIELDS_INVALID"),
        ("forged", "PROVENANCE_FIELDS_INVALID"),
        (reid(record, output_schema_sha256="0" * 64), "PROVENANCE_SCHEMA_MISMATCH"),
        (reid(record, raw_output_sha256="0" * 64), "PROVENANCE_OUTPUT_MISMATCH"),
        (reid(record, candidate_menu_sha256="0" * 64), "PROVENANCE_MENU_MISMATCH"),
        (reid(record, information_cutoff_ns=native.T0 - 1), "PROVENANCE_CLOCK_INVALID"),
        (reid(record, response_completed_ns=native.AT + 1), "PROVENANCE_CLOCK_INVALID"),
        (reid(record, deadline_ns=native.AT), "PROVENANCE_CLOCK_INVALID"),
        (reid(record, issued_at_ns=native.T0 + 1), "PROVENANCE_ORIGIN_FORGED"),
        (reid(record, lifecycle_head="0" * 64), "PRODUCER_STATE_CHANGED"),
        (reid(record, strategy_version_id=other), "PRODUCER_CLAIM_MISMATCH"),
        (reid(record, hermes_assessment_id=None), "PRODUCER_CLAIM_MISMATCH"),
    ):
        receipt = bound(rec)
        closed(receipt)
        assert receipt["reason_codes"] == [code], (code, receipt["reason_codes"])
    # A record never transfers to a changed model output or reordered menu.
    for choice in (json.dumps(dict(proposal, requested_shares="11")), content + " "):
        assert bound(record, choice)["reason_codes"] == ["PROVENANCE_OUTPUT_MISMATCH"]
    reordered = cycle.evaluate_once(**dict(args, candidate_menu=args["candidate_menu"][::-1], choice=content,
                                           producer_evidence=record))
    assert reordered["reason_codes"] == ["PROVENANCE_MENU_MISMATCH"]
    # Model self-attestation inside the choice text is rejected by the strict native schema.
    for index, claim in enumerate((dict(proposal, producer_receipt="REAL_PROVIDER"),
                                   dict(proposal, model_origin_proof="VERIFIED", estimated_cost_usd="0"),
                                   dict(proposal, proof_level="REAL_PROVIDER"))):
        _, _, claimed, text = produce(tmp_path, args, claim, journal=f"claim{index}")
        receipt = bound(claimed, text)
        closed(receipt)
        assert receipt["reason_codes"] in (["CHOICE_FIELDS_INVALID"], ["PRODUCER_UNVERIFIED"])
    # Only a producer-owned, non-replayed result can become a record.
    forged = tf.StageBResult(request.request_id, tf.VALID_OUTPUT, result.raw_output_sha256,
                             result.response_completed_ns, content.encode())
    replay = tf.run_tool_free_stage_b(request, backend=tf.OfflineStageBBackend({}), reservation_dir=tmp_path / "stageb")
    assert replay.status == "DISPATCH_ALREADY_RESERVED"
    for candidate in (forged, replay):
        with pytest.raises(fb.FeedbackRejected, match="PRODUCER_RESULT_INVALID"):
            fb.build_choice_provenance(candidate, request=request, strategy_version_id=None,
                                       hermes_assessment_id=None, lifecycle_head="0" * 64, hermes_head="0" * 64)
    # Store change between producer verification and Gate C fails closed.
    w.assess(t=native.T0 - 500_000)
    assert bound(record)["reason_codes"] == ["PRODUCER_STATE_CHANGED"]


def candidate_of(version):
    return next(ref for ref in version.evidence_refs if ref.startswith("alphacandidate:sha256:"))


def paper_store(path, candidate_id, *, quantity="4", orders=True):
    store = PaperStore(path, create=True)
    binding = _research_binding(candidate_id=candidate_id)
    engine = PaperEngine.create_research(store, binding, generous_limits(), session_label="research",
                                         created_time_ns=100)
    engine.process_market_event(paper_book(100))
    if orders:
        engine.submit(_research_intent(binding, decision_time_ns=101, quantity=quantity))
        engine.process_market_event(paper_book(111))
    store.close()
    return binding


def feedback(w, path, binding, manager, **changes):
    values = dict(paper_store_path=path, expected_binding=binding, lifecycle_snapshot=w.snapshot(),
                  strategy_version_id=w.version.strategy_version_id, information_cutoff=CUTOFF,
                  decision_time_ns=native.T0, backend=manager, hermes_manager_store_path=w.hermes,
                  provider_label="example-provider", model_label="example-model", clock=lambda: native.FIXED_CLOCK)
    values.update(changes)
    return fb.run_paper_performance_update(**values)


def test_verified_wp173_paper_snapshot_drives_native_performance_update(tmp_path):
    w, _, _, _ = world(tmp_path / "w")
    path = tmp_path / "paper.sqlite3"
    binding = paper_store(path, candidate_of(w.version))
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    backend = native.StrategyBackend(native.judgment())
    receipt = feedback(w, path, binding, backend)
    assert receipt["status"] == "ASSESSED" and backend.call_count == 1, receipt
    assert hashlib.sha256(path.read_bytes()).hexdigest() == before  # read-only paper store
    store = sm.load_hermes_strategy_manager_store(w.hermes)
    run = next(r for r in store.run_records if r.run_record_id == receipt["run_record_id"])
    assessment = next(a for a in store.assessments if a.assessment_id == receipt["assessment_id"])
    assert run.trigger == "PERFORMANCE_UPDATE" and run.trigger_ref == receipt["paper_snapshot_id"]
    assert receipt["evidence_id"] in assessment.input_evidence_refs
    assert store.latest_assessment_id(w.version.strategy_version_id) == assessment.assessment_id
    facts = receipt["facts"]
    assert facts["fill_count"] == 1 and facts["order_count"] == 1 and facts["fee_total"] != "0"
    assert receipt["paper_evidence_class"] == "RESEARCH_PAPER_SIMULATED" and receipt["live_pnl_claim"] is False
    # Zero-result and risk-denied sessions are assessed as visible contradicting evidence.
    for name, kwargs in (("empty", dict(orders=False)), ("denied", dict(quantity="100000"))):
        w2, _, _, _ = world(tmp_path / name)
        other_path = tmp_path / f"{name}.sqlite3"
        other = paper_store(other_path, candidate_of(w2.version), **kwargs)
        result = feedback(w2, other_path, other, native.StrategyBackend(native.judgment()))
        assert result["status"] == "ASSESSED" and result["direction"] == "CONTRADICTING", result
        assert result["facts"]["fill_count"] == 0
    assert result["facts"]["risk_deny_count"] + result["facts"]["rejected_order_count"] >= 1
    # Fail closed before any manager dispatch.
    corrupt = tmp_path / "corrupt.sqlite3"
    paper_store(corrupt, candidate_of(w.version))
    import sqlite3
    with sqlite3.connect(corrupt) as connection:
        connection.execute("UPDATE paper_checkpoint SET state_hash=?", ("0" * 64,))
    wrong = _research_binding(candidate_id=candidate_of(w.version), scope_id="scope:sha256:" + "9" * 64)
    unrelated = _research_binding(candidate_id="alphacandidate:sha256:" + "8" * 64)
    missing = tmp_path / "missing.sqlite3"
    for changes, code in (
        (dict(information_cutoff=native.HERMES_CUTOFF), "CUTOFF_NOT_ADVANCED"),
        (dict(information_cutoff="1970-01-01T00:00:00Z"), "PAPER_EVIDENCE_AFTER_CUTOFF"),
        (dict(expected_binding=wrong), "PAPER_SCOPE_MISMATCH"),
        (dict(expected_binding=unrelated), "BINDING_STRATEGY_MISMATCH"),
        (dict(expected_binding=object()), "BINDING_NOT_RESEARCH_ONLY"),
        (dict(strategy_version_id=w.other_version.strategy_version_id), "BINDING_STRATEGY_MISMATCH"),
        (dict(paper_store_path=missing), "PAPER_OUTCOME_MISSING"),
        (dict(paper_store_path=corrupt), "PAPER_STORE_INVALID"),
        (dict(backend=object()), "BACKEND_NOT_OFFLINE"),
        (dict(information_cutoff="not-a-cutoff"), "FEEDBACK_INPUT_INVALID"),
    ):
        probe = native.StrategyBackend(native.judgment())
        rejected = feedback(w, path, binding, probe, **changes)
        assert rejected["status"] == "REJECTED" and rejected["reason_code"] == code, (code, rejected)
        assert probe.call_count == 0 and rejected["assessment_id"] is None
    assert not missing.exists()


def cycle_run(tmp_path, args, choice, *, journal="journal", report=RECORDED_REPORT, response=None, **extra):
    canned = dict(model=MODEL, content=json.dumps(choice), completed_at_ns=native.T0 + 1000)
    canned.update(response or {})
    try:
        request = fb.cycle_request(surface_report=report, candidate_menu=args["candidate_menu"],
            information_cutoff_ns=native.T0, issued_at_ns=native.T0, deadline_ns=args["deadline_ns"], model_label=MODEL)
        backend = tf.OfflineStageBBackend({request.request_id: canned})
    except ValueError:
        backend = tf.OfflineStageBBackend({})  # an unverified surface never yields a request
    values = dict(journal_dir=tmp_path / journal, surface_report=report, backend=backend, model_label=MODEL,
                  candidate_menu=args["candidate_menu"], lifecycle_store_path=args["lifecycle_store_path"],
                  hermes_manager_store_path=args["hermes_manager_store_path"],
                  alpha_registry_path=args["alpha_registry_path"], venue_snapshots=args["venue_snapshots"],
                  information_cutoff_ns=native.T0, issued_at_ns=native.T0, evaluated_at_ns=native.AT,
                  deadline_ns=args["deadline_ns"])
    values.update(extra)
    return fb.run_one_cycle(**values), backend, values


def test_one_cycle_evidence_denominator_and_replay(tmp_path):
    w, args, proposal, _ = world(tmp_path / "w")
    path = tmp_path / "paper.sqlite3"
    binding = paper_store(path, candidate_of(w.version))
    manager = native.StrategyBackend(native.judgment())
    first, backend, values = cycle_run(tmp_path, args, proposal, paper_feedback=dict(
        paper_store_path=path, expected_binding=binding, lifecycle_snapshot=w.snapshot(),
        strategy_version_id=w.version.strategy_version_id, information_cutoff=CUTOFF, decision_time_ns=native.T0,
        backend=manager, hermes_manager_store_path=w.hermes, provider_label="example-provider",
        model_label="example-model", clock=lambda: native.FIXED_CLOCK))
    assert first["outcome"] == "ELIGIBLE_PREVIEW" and first["stage_b_status"] == "VALID_OUTPUT", first
    assert first["paper_feedback"]["status"] == "ASSESSED" and first["choice_provenance_id"].startswith(fb.PROVENANCE_PREFIX)
    # (b) Matching native selection: feedback is decision-linked to this exact receipt.
    assert first["paper_feedback"]["decision_linkage"] == "DECISION_LINKED"
    assert first["paper_feedback"]["linked_auto01_receipt_id"] == first["auto01_receipt_id"]
    assert (first["paper_feedback"]["linked_candidate_id"], first["paper_feedback"]["linked_strategy_version_id"]) == (
        binding.candidate_id, w.version.strategy_version_id)
    assert first["auto01_receipt_id"].startswith("decisioncycle:sha256:") and first["no_order"] and first["no_live"]
    assert first["real_provider"] == "REAL_PROVIDER_NOT_INVOKED" and first["model_origin_proof"] == "MODEL_ORIGIN_UNVERIFIED"
    body = {k: v for k, v in first.items() if k != "bundle_id"}
    assert first["bundle_id"] == fb.CYCLE_PREFIX + fb._digest(body)
    # Exact replay: stored bundle, zero Stage B redispatch, zero manager redispatch.
    assert fb.run_one_cycle(**values) == first and backend.dispatch_count == 1 and manager.call_count == 1
    dumped = json.dumps(first)
    assert str(tmp_path) not in dumped and json.dumps(proposal) not in dumped and "PASSIVE_MAKER" not in dumped
    abstain = {key: proposal[key] for key in cycle._CLOCK_KEYS}
    denominators = []
    for name, choice, response, outcome in (
        ("no-trade", dict(abstain, action="NO_TRADE"), None, "NO_TRADE"),
        ("pause", dict(abstain, action="PAUSE"), None, "PAUSE"),
        ("reassess", dict(abstain, action="REASSESS"), None, "REASSESS"),
        ("rejected", dict(proposal, requested_shares="1"), None, "REJECTED"),
        ("outside-menu", dict(proposal, candidate_id="alphacandidate:sha256:" + "f" * 64), None, "REJECTED"),
        ("tool-call", proposal, dict(tool_calls=[{"name": "terminal"}]), "TOOL_CALL_ATTEMPT_INVALID"),
        ("provider-error", proposal, dict(error="HTTP 400"), "PROVIDER_ERROR"),
        ("bad-json", proposal, dict(content='{"action":'), "OUTPUT_JSON_INVALID"),
        ("forged-usage", proposal, dict(usage={"estimated_cost_usd": 0}), "RESPONSE_INVALID"),
    ):
        bundle, other, again = cycle_run(tmp_path, args, choice, journal=name, response=response)
        assert bundle["outcome"] == outcome, (name, bundle)
        assert fb.run_one_cycle(**again) == bundle and other.dispatch_count == 1
        denominators.append(bundle["bundle_id"])
    assert len(set(denominators)) == len(denominators)
    # An interrupted earlier reservation blocks permanently without redispatch.
    request = fb.cycle_request(surface_report=RECORDED_REPORT, candidate_menu=args["candidate_menu"],
        information_cutoff_ns=native.T0, issued_at_ns=native.T0, deadline_ns=args["deadline_ns"], model_label=MODEL)
    (tmp_path / "interrupted").mkdir()
    (tmp_path / "interrupted" / ("stageb-" + request.request_id.rsplit(":", 1)[1] + ".reserved")).write_bytes(b"x")
    blocked, idle, again = cycle_run(tmp_path, args, proposal, journal="interrupted")
    assert blocked["outcome"] == "INTERRUPTED_BLOCKED" and idle.dispatch_count == 0
    assert fb.run_one_cycle(**again) == blocked
    # Tampered journal and unverified tool surface fail closed without dispatch or journal writes.
    terminal = next((tmp_path / "journal").glob("cycle-*.json"))
    terminal.write_bytes(terminal.read_bytes().replace(b"ELIGIBLE_PREVIEW", b"NO_TRADE"))
    tampered, _, _ = cycle_run(tmp_path, args, proposal)
    assert tampered["outcome"] == "JOURNAL_INVALID"
    surface, idle, _ = cycle_run(tmp_path, args, proposal, journal="surface",
                                 report=mutated(("explicit_empty", "request_tools"), ["memory"]))
    assert surface["outcome"] == "TOOL_SURFACE_OR_REQUEST_REJECTED" and surface["stage_b_status"] == "EFFECTIVE_TOOLS_PRESENT"
    assert idle.dispatch_count == 0 and not (tmp_path / "surface").exists()


def paper_args(w, path, binding, manager, version):
    return dict(paper_store_path=path, expected_binding=binding, lifecycle_snapshot=w.snapshot(),
                strategy_version_id=version.strategy_version_id, information_cutoff=CUTOFF,
                decision_time_ns=native.T0, backend=manager, hermes_manager_store_path=w.hermes,
                provider_label="example-provider", model_label="example-model", clock=lambda: native.FIXED_CLOCK)


def test_cycle_paper_feedback_bound_to_native_selection(tmp_path):
    """SIDE20 correction: decision -> PERFORMANCE_UPDATE linkage uses native verified identities."""
    w, args, proposal, _ = world(tmp_path / "w")
    # (a) A real, correctly formed research-paper session for the OTHER strategy/candidate.
    unrelated_path = tmp_path / "unrelated.sqlite3"
    unrelated = paper_store(unrelated_path, candidate_of(w.other_version))
    manager = native.StrategyBackend(native.judgment())
    head = sm.load_hermes_strategy_manager_store(w.hermes).store_head_entry_hash
    mismatch, backend, values = cycle_run(tmp_path, args, proposal, journal="mismatch",
                                          paper_feedback=paper_args(w, unrelated_path, unrelated, manager, w.other_version))
    assert mismatch["outcome"] == "ELIGIBLE_PREVIEW" and backend.dispatch_count == 1
    assert mismatch["paper_feedback"]["reason_code"] == "FEEDBACK_LINEAGE_MISMATCH"
    assert mismatch["paper_feedback"]["decision_linkage"] == "MISMATCH" and manager.call_count == 0
    assert sm.load_hermes_strategy_manager_store(w.hermes).store_head_entry_hash == head  # no assessment write
    assert fb.run_one_cycle(**values) == mismatch and backend.dispatch_count == 1 and manager.call_count == 0
    # Each identity leg alone breaks linkage: candidate, strategy, lifecycle head, manager store.
    own_path = tmp_path / "own.sqlite3"
    own = paper_store(own_path, candidate_of(w.version))
    foreign, _, _, _ = world(tmp_path / "foreign", policy=native._policy(label="Foreign envelope"))
    assert foreign.snapshot().store_head_entry_hash != w.snapshot().store_head_entry_hash
    for name, changes in (("candidate", dict(expected_binding=unrelated)),
                          ("strategy", dict(strategy_version_id=w.other_version.strategy_version_id)),
                          ("lifecycle", dict(lifecycle_snapshot=foreign.snapshot())),
                          ("store", dict(hermes_manager_store_path=foreign.hermes)),
                          ("malformed", dict(expected_binding=None))):
        feedback_args = dict(paper_args(w, own_path, own, manager, w.version), **changes)
        bundle, _, _ = cycle_run(tmp_path, args, proposal, journal=f"leg-{name}", paper_feedback=feedback_args)
        assert bundle["outcome"] == "ELIGIBLE_PREVIEW", name
        assert bundle["paper_feedback"]["reason_code"] == "FEEDBACK_LINEAGE_MISMATCH", name
    typo = dict(paper_args(w, own_path, own, manager, w.version), informaton_cutoff=CUTOFF)
    bundle, _, again = cycle_run(tmp_path, args, proposal, journal="typo", paper_feedback=typo)
    assert bundle["paper_feedback"]["reason_code"] == "FEEDBACK_INPUT_INVALID" and fb.run_one_cycle(**again) == bundle
    assert manager.call_count == 0
    assert sm.load_hermes_strategy_manager_store(w.hermes).store_head_entry_hash == head
    # The unrelated session is itself valid: the standalone helper assesses it for its own strategy.
    standalone = fb.run_paper_performance_update(**paper_args(w, unrelated_path, unrelated, manager, w.other_version))
    assert standalone["status"] == "ASSESSED" and manager.call_count == 1
    # (c) An unverified prior paper snapshot reference is refused before dispatch or journaling.
    forged_prior = "researchpapersnapshot:sha256:" + "1" * 64
    refused, idle, _ = cycle_run(tmp_path, args, proposal, journal="prior", prior_paper_snapshot_id=forged_prior)
    assert refused["outcome"] == "PRIOR_PAPER_SNAPSHOT_UNVERIFIED" and idle.dispatch_count == 0
    assert not (tmp_path / "prior").exists()
    request, result, record, content = produce(tmp_path, args, proposal, journal="prior-record")
    with pytest.raises(fb.FeedbackRejected, match="PRIOR_PAPER_SNAPSHOT_UNVERIFIED"):
        fb.build_choice_provenance(result, request=request, strategy_version_id=None, hermes_assessment_id=None,
                                   lifecycle_head="0" * 64, hermes_head="0" * 64, paper_snapshot_id=forged_prior)
    forged = cycle.evaluate_once(**dict(args, choice=content, producer_evidence=reid(record, paper_snapshot_id=forged_prior)))
    assert forged["reason_codes"] == ["PRIOR_PAPER_SNAPSHOT_UNVERIFIED"] and forged["preview_permit"] is None
    # (d) Non-trade / rejected denominators are recorded, never credited with feedback, and replay.
    abstain = {key: proposal[key] for key in cycle._CLOCK_KEYS}
    for name, choice, outcome in (("no-trade", dict(abstain, action="NO_TRADE"), "NO_TRADE"),
                                  ("rejected", dict(proposal, requested_shares="1"), "REJECTED")):
        quiet = native.StrategyBackend(native.judgment())
        bundle, other, again = cycle_run(tmp_path, args, choice, journal=f"deferred-{name}",
                                         paper_feedback=paper_args(w, own_path, own, quiet, w.version))
        assert bundle["outcome"] == outcome and bundle["paper_feedback"]["status"] == "DEFERRED_NOT_DECISION_LINKED"
        assert fb.run_one_cycle(**again) == bundle and other.dispatch_count == 1 and quiet.call_count == 0


REAL01_GUARD_ADDITIONS = {
    "tests/test_hermes_advisory_foundation_architecture_docs.py": (
        "                # S10-HERMES-AUTO-02-REAL-01: exact dormant offline-wire source only.\n"
        '                "src/research_runtime/hermes_controlled_runtime/real_provider_stage_b.py",\n',
        "    # S10-HERMES-AUTO-02-REAL-01: an unregistered sibling of the new module stays rejected.\n"
        '    hostile = "src/research_runtime/hermes_controlled_runtime/real_provider_stage_b_shadow.py"\n'
        "    assert hostile not in allowed and any(pattern.search(hostile) for pattern in forbidden_patterns)\n"),
    "tests/test_hermes_input_output_contracts_and_validator_requirements_docs.py": (
        "                # S10-HERMES-AUTO-02-REAL-01: exact dormant offline-wire source/test only.\n"
        '                "src/research_runtime/hermes_controlled_runtime/real_provider_stage_b.py",\n'
        '                "tests/research_runtime/hermes_controlled_runtime/test_real_provider_stage_b.py",\n',
        "    # S10-HERMES-AUTO-02-REAL-01: unregistered siblings of the new module/test stay rejected.\n"
        '    for hostile in ("src/research_runtime/hermes_controlled_runtime/real_provider_stage_b_shadow.py",\n'
        '                    "tests/research_runtime/hermes_controlled_runtime/test_real_provider_stage_b_shadow.py"):\n'
        "        assert hostile not in allowed and any(pattern.search(hostile) for pattern in forbidden_patterns)\n"),
}


ACTIVATION_GUARD_ADDITIONS = {
    "tests/test_hermes_advisory_foundation_architecture_docs.py": (
        "                # S10-HERMES-AUTO-02-REAL-01-ACTIVATION: exact official OAuth plan-usage source only.\n"
        '                "src/research_runtime/hermes_controlled_runtime/oauth_plan_stage_b.py",\n',
        "    # S10-HERMES-AUTO-02-REAL-01-ACTIVATION: an unregistered sibling of the OAuth module stays rejected.\n"
        '    hostile = "src/research_runtime/hermes_controlled_runtime/oauth_plan_stage_b_shadow.py"\n'
        "    assert hostile not in allowed and any(pattern.search(hostile) for pattern in forbidden_patterns)\n"),
    "tests/test_hermes_input_output_contracts_and_validator_requirements_docs.py": (
        "                # S10-HERMES-AUTO-02-REAL-01-ACTIVATION: exact official OAuth plan-usage source/test only.\n"
        '                "src/research_runtime/hermes_controlled_runtime/oauth_plan_stage_b.py",\n'
        '                "tests/research_runtime/hermes_controlled_runtime/test_oauth_plan_stage_b.py",\n',
        "    # S10-HERMES-AUTO-02-REAL-01-ACTIVATION: unregistered siblings of the OAuth module/test stay rejected.\n"
        '    for hostile in ("src/research_runtime/hermes_controlled_runtime/oauth_plan_stage_b_shadow.py",\n'
        '                    "tests/research_runtime/hermes_controlled_runtime/test_oauth_plan_stage_b_shadow.py"):\n'
        "        assert hostile not in allowed and any(pattern.search(hostile) for pattern in forbidden_patterns)\n"),
}


def test_auto02_historical_hermes_guards_exact_allowlist_and_sibling_negative():
    scope = json.loads((ROOT / "docs/wp_specs/S10-HERMES-AUTO-02/wp_spec.json").read_text(encoding="utf-8"))
    paths = scope["scope"]["required_changed_files"]
    sibling = "src/research_runtime/hermes_controlled_runtime/unknown_auto02_module.py"
    test_sibling = "tests/research_runtime/hermes_controlled_runtime/test_unknown_auto02.py"
    additions = {
        "tests/test_hermes_advisory_foundation_architecture_docs.py": (
            "                # S10-HERMES-AUTO-02: exact offline tool-free Stage B and feedback sources only.\n"
            '                "src/research_runtime/hermes_controlled_runtime/tool_free_stage_b.py",\n'
            '                "src/research_runtime/hermes_controlled_runtime/autonomous_feedback.py",\n'),
        "tests/test_hermes_input_output_contracts_and_validator_requirements_docs.py": (
            "                # S10-HERMES-AUTO-02: exact offline tool-free Stage B and feedback sources/tests only.\n"
            '                "src/research_runtime/hermes_controlled_runtime/tool_free_stage_b.py",\n'
            '                "src/research_runtime/hermes_controlled_runtime/autonomous_feedback.py",\n'
            '                "tests/research_runtime/hermes_controlled_runtime/test_tool_free_stage_b.py",\n'
            '                "tests/research_runtime/hermes_controlled_runtime/test_autonomous_feedback.py",\n'),
    }
    for guard_path, addition in additions.items():
        base = subprocess.run(["git", "show", f"{BASE_SHA}:{guard_path}"], cwd=ROOT, capture_output=True,
                              text=True, check=True).stdout
        current = (ROOT / guard_path).read_text(encoding="utf-8")
        # S10-HERMES-AUTO-02-REAL-01 and -ACTIVATION exact additions
        for real01 in ACTIVATION_GUARD_ADDITIONS[guard_path] + REAL01_GUARD_ADDITIONS[guard_path]:
            assert current.count(real01) == 1
            current = current.replace(real01, "", 1)
        assert current.count(addition) == 1 and current.replace(addition, "", 1) == base
        guard = runpy.run_path(str(ROOT / guard_path))["test_no_actual_hermes_implementation_artifacts_added"]
        guard()  # real tracked tree
        listing = "\n".join(paths) + "\n"
        with patch.object(subprocess, "run", return_value=subprocess.CompletedProcess([], 0, listing, "")):
            guard()
        rejected = [sibling] + ([test_sibling] if "input_output" in guard_path else [])
        for extra in rejected:
            with patch.object(subprocess, "run",
                              return_value=subprocess.CompletedProcess([], 0, listing + extra + "\n", "")):
                with pytest.raises(AssertionError):
                    guard()
    # Architecture guard is unmodified: the Hermes child directory approval already covers both modules.
    # S10-HERMES-LIVE-BRIDGE-01 (R4): the only difference is its one exact-file entry outside the Hermes package.
    base = subprocess.run(["git", "show", BASE_SHA + ":tests/test_architecture_boundaries.py"], cwd=ROOT,
                          capture_output=True, text=True, check=True).stdout
    current = (ROOT / "tests/test_architecture_boundaries.py").read_text()
    bridge = ('    # S10-HERMES-LIVE-BRIDGE-01: exact foreground read-only live-preflight composer only.\n'
              '    "src/research_runtime/live_preflight_bridge.py",\n')
    assert current.count(bridge) == 1 and current.replace(bridge, "", 1) == base
    scopes = runpy.run_path(str(ROOT / "tests/test_architecture_boundaries.py"))["APPROVED_SRC_SCOPES"]
    assert "src/research_runtime/hermes_controlled_runtime" in scopes


def test_activation_real_origin_source_class_spoof_replay_and_guards(tmp_path, monkeypatch):
    """S10-HERMES-AUTO-02-REAL-01-ACTIVATION: one admitted source class; offline/spoofed/replayed never."""
    import dataclasses
    from src.research_runtime.hermes_controlled_runtime import oauth_plan_stage_b as op
    from src.research_runtime.hermes_controlled_runtime import real_provider_stage_b as rp
    from tests.research_runtime.hermes_controlled_runtime import test_oauth_plan_stage_b as fx
    fx.Spy(monkeypatch, fx.dispatch())
    eligibility = op.evaluate_preflight(fx.preflight(), attestation=dict(fx.ATTEST), checked_at_ns=fx.T0)
    wire = op.OAuthPlanTransport(fx.PIN_ROOT, tmp_path / "creds")
    result = op.run_oauth_attempt(fx.REQUEST, eligibility=eligibility, transport=wire, journal_dir=tmp_path / "j",
                                  clock_ns=fx.clock())
    record = fb.verify_real_origin_evidence(result)
    assert record == result.origin and record["real_origin"] == op.REAL_ORIGIN_VERIFIED
    replay = op.run_oauth_attempt(fx.REQUEST, eligibility=eligibility, transport=wire, journal_dir=tmp_path / "j",
                                  clock_ns=fx.clock())
    assert replay.replayed and wire.dispatch_count == 1
    relabelled = dict(record, transport_mode=op.TRANSPORT_MOCK)
    relabelled["record_id"] = op.RECORD_ID_PREFIX + tf._digest({k: v for k, v in relabelled.items() if k != "record_id"})
    real01 = rp.Real01Result("real01:sha256:" + "0" * 64, rp.VALID_OUTPUT, dict(record), result.output_bytes)
    spoofs = (replay, dataclasses.replace(result, _witness=None), dataclasses.replace(result, origin=relabelled),
              op.OAuthPlanResult(result.request_id, result.status, dict(record), result.output_bytes),
              dataclasses.replace(result, output_bytes=b'{"action":"PAUSE"}'), real01, record, json.dumps(record),
              "REAL_ORIGIN_VERIFIED", None, {})
    for evidence in spoofs:
        with pytest.raises(fb.FeedbackRejected, match="REAL_ORIGIN_UNVERIFIED"):
            fb.verify_real_origin_evidence(evidence)
    # The REAL-01 offline route still never admits, and its seam keeps rejecting.
    with pytest.raises(fb.FeedbackRejected, match="REAL01_RESULT_INVALID"):
        fb.admit_real01_choice(result)
    with pytest.raises(fb.FeedbackRejected, match="OAUTH_RESULT_INVALID"):
        fb.admit_oauth_choice(real01)
    # Historical guards: the exact 13-path ACTIVATION scope passes; unknown siblings stay rejected.
    scope = json.loads((ROOT / "docs/wp_specs/S10-HERMES-AUTO-02-REAL-01-ACTIVATION/wp_spec.json").read_text(encoding="utf-8"))
    listing = "\n".join(scope["scope"]["required_changed_files"]) + "\n"
    assert len(scope["scope"]["required_changed_files"]) == 13
    for guard_path in ACTIVATION_GUARD_ADDITIONS:
        guard = runpy.run_path(str(ROOT / guard_path))["test_no_actual_hermes_implementation_artifacts_added"]
        with patch.object(subprocess, "run", return_value=subprocess.CompletedProcess([], 0, listing, "")):
            guard()
        siblings = ["src/research_runtime/hermes_controlled_runtime/oauth_plan_stage_b_v2.py"]
        if "input_output" in guard_path:
            siblings.append("tests/research_runtime/hermes_controlled_runtime/test_oauth_plan_stage_b_extra.py")
        for extra in siblings:
            with patch.object(subprocess, "run", return_value=subprocess.CompletedProcess([], 0, listing + extra + "\n", "")):
                with pytest.raises(AssertionError):
                    guard()


def test_security_profile_provenance_rejects_old_or_forged_identity(tmp_path):
    w, args, proposal, _ = world(tmp_path / "world")
    request, result, record, content = produce(tmp_path, args, proposal)
    assert record["runtime_profile_sha256"] == request.runtime_profile_sha256 == result.runtime_profile_sha256
    checked = cycle.evaluate_once(**dict(args, choice=content, producer_evidence=record))
    assert checked["status"] == "ELIGIBLE_PREVIEW"
    for digest in (None, "0" * 64, tf._profile_entries()[1]["profile_id"].rsplit(":", 1)[1]):
        forged = reid(record, runtime_profile_sha256=digest)
        verdict = cycle.evaluate_once(**dict(args, choice=content, producer_evidence=forged))
        assert verdict["status"] != "ELIGIBLE_PREVIEW"
    old = dict(record); old.pop("runtime_profile_sha256")
    old["provenance_id"] = fb.PROVENANCE_PREFIX + fb._digest({k:v for k,v in old.items() if k != "provenance_id"})
    assert cycle.evaluate_once(**dict(args, choice=content, producer_evidence=old))["status"] != "ELIGIBLE_PREVIEW"
    assert "runtime_profile_sha256" in result.to_public()
