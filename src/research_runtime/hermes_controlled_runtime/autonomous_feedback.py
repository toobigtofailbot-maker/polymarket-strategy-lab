"""Producer-bound choice provenance and verified paper feedback (S10-HERMES-AUTO-02).

Three finite offline helpers composing EXISTING native components only:

* :func:`build_choice_provenance` / :func:`verify_choice_provenance` -- one canonical,
  content-addressed record binding a producer-owned Stage B output digest (never the raw
  text) to its request, menu, schema, clocks, verified store heads and tool surface. An
  offline injected backend is ALWAYS ``OFFLINE_INJECTED`` / ``MODEL_ORIGIN_UNVERIFIED``.
* :func:`run_paper_performance_update` -- verified WP173 research-paper snapshot ->
  native ContextEvidenceItem -> native ``run_hermes_strategy_assessment`` with
  ``trigger="PERFORMANCE_UPDATE"`` and an injected FakeHermesBackend. Read-only on the
  paper store; no paper order, policy or lifecycle mutation.
* :func:`run_one_cycle` -- one journaled cycle: Stage B -> provenance -> AUTO-01
  ``evaluate_once`` -> optional paper feedback. Replays return the stored bundle and
  never redispatch. No scheduler, retry, live permit or order.

S10-HERMES-AUTO-02-REAL-01 adds :func:`verify_real_origin_evidence` /
:func:`admit_real01_choice`: a real-origin seam that fails closed with
``REAL_ORIGIN_UNVERIFIED``. S10-HERMES-AUTO-02-REAL-01-ACTIVATION admits exactly one source
class through it, a witnessed official ChatGPT-plan OAuth result (:func:`admit_oauth_choice`).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re

from src.research_runtime.hermes_controlled_runtime import tool_free_stage_b as stage_b

PROVENANCE_PREFIX = "choiceprovenance:sha256:"
CYCLE_PREFIX = "auto02cycle:sha256:"
TRANSPORT_MODE = stage_b.TRANSPORT_OFFLINE_INJECTED
WITNESS_CLASS = "LOCAL_OFFLINE_PRODUCER"
MODEL_ORIGIN = "MODEL_ORIGIN_UNVERIFIED"
PROMOTION_GATE = "REAL_PROVIDER_PROMOTION_REQUIRES_SEPARATE_EMPIRICAL_AUTHORITY"
_RECORD_KEYS = {
    "schema_id", "provenance_id", "request_id", "raw_output_sha256", "candidate_menu_sha256",
    "output_schema_sha256", "model_input_sha256", "information_cutoff_ns", "issued_at_ns",
    "response_completed_ns", "deadline_ns", "model_label", "strategy_version_id", "hermes_assessment_id",
    "lifecycle_head", "hermes_head", "paper_snapshot_id", "hermes_commit", "tool_surface_fingerprint", "runtime_profile_sha256",
    "transport_mode", "producer_witness_class", "model_origin_proof", "real_provider", "promotion_gate",
}
_OPAQUE = re.compile(r"[a-z][a-z0-9_]*:sha256:[0-9a-f]{64}")
_UNIX_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)


class FeedbackRejected(ValueError):
    pass


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise FeedbackRejected(code)


def _digest(value: object) -> str:
    return hashlib.sha256(stage_b._canonical(value)).hexdigest()


def _optional_id(value: object) -> bool:
    return value is None or (type(value) is str and _OPAQUE.fullmatch(value) is not None)


def choice_output_schema_sha256() -> str:
    """Digest of the exact AUTO-01 strict choice contract the Stage B model must emit."""
    from src.research_runtime import autonomous_opportunity_cycle as cycle
    return _digest(dict(actions=["NO_TRADE", "PAUSE", "REASSESS", "TRADE"], clock_keys=sorted(cycle._CLOCK_KEYS),
                        trade_keys=sorted(cycle._TRADE_KEYS), max_bytes=stage_b.MAX_OUTPUT_BYTES,
                        proof_level="SYNTHETIC_ONLY"))


def build_choice_provenance(result: object, *, request: object, strategy_version_id: object,
                            hermes_assessment_id: object, lifecycle_head: object, hermes_head: object,
                            paper_snapshot_id: object = None) -> dict:
    """Producer-side record. Heads/ids are caller-verified store values, never model text."""
    _require(stage_b.is_producer_result(result) and stage_b.request_is_bound(request) and
             result.request_id == request.request_id and result.runtime_profile_sha256 == request.runtime_profile_sha256, "PRODUCER_RESULT_INVALID")
    # No cold-verified prior-paper input exists yet: any non-None reference is unverified.
    _require(paper_snapshot_id is None, "PRIOR_PAPER_SNAPSHOT_UNVERIFIED")
    _require(all(_optional_id(v) for v in (strategy_version_id, hermes_assessment_id)) and
             all(type(h) is str and stage_b._HEX64.fullmatch(h) for h in (lifecycle_head, hermes_head)),
             "PROVENANCE_BINDING_INVALID")
    record = dict(
        schema_id="hermes-auto02-choice-provenance", request_id=request.request_id,
        raw_output_sha256=result.raw_output_sha256, candidate_menu_sha256=request.candidate_menu_sha256,
        output_schema_sha256=request.output_schema_sha256, model_input_sha256=request.model_input_sha256,
        information_cutoff_ns=request.information_cutoff_ns, issued_at_ns=request.issued_at_ns,
        response_completed_ns=result.response_completed_ns, deadline_ns=request.deadline_ns,
        model_label=request.model_label, strategy_version_id=strategy_version_id,
        hermes_assessment_id=hermes_assessment_id, lifecycle_head=lifecycle_head, hermes_head=hermes_head,
        paper_snapshot_id=paper_snapshot_id, hermes_commit=request.hermes_commit,
        tool_surface_fingerprint=request.tool_surface_fingerprint, runtime_profile_sha256=request.runtime_profile_sha256, transport_mode=TRANSPORT_MODE,
        producer_witness_class=WITNESS_CLASS, model_origin_proof=MODEL_ORIGIN,
        real_provider=stage_b.REAL_PROVIDER_NOT_INVOKED, promotion_gate=PROMOTION_GATE,
    )
    record["provenance_id"] = PROVENANCE_PREFIX + _digest(record)
    return record


def verify_choice_provenance(record: object, *, raw_choice: bytes, candidate_menu_sha256: str,
                             information_cutoff_ns: int, evaluated_at_ns: int) -> dict:
    """Trusted verifier used by AUTO-01. Fixed offline labels; any edit changes the id."""
    _require(type(record) is dict and set(record) == _RECORD_KEYS, "PROVENANCE_FIELDS_INVALID")
    body = {k: v for k, v in record.items() if k != "provenance_id"}
    _require(record["provenance_id"] == PROVENANCE_PREFIX + _digest(body), "PROVENANCE_TAMPERED")
    _require(record["schema_id"] == "hermes-auto02-choice-provenance" and record["transport_mode"] == TRANSPORT_MODE
             and record["producer_witness_class"] == WITNESS_CLASS and record["model_origin_proof"] == MODEL_ORIGIN
             and record["real_provider"] == stage_b.REAL_PROVIDER_NOT_INVOKED
             and record["promotion_gate"] == PROMOTION_GATE
             and record["hermes_commit"] == stage_b.PINNED_HERMES_COMMIT
             and stage_b.profile_digest_is_approved(record["runtime_profile_sha256"]), "PROVENANCE_ORIGIN_FORGED")
    _require(record["paper_snapshot_id"] is None, "PRIOR_PAPER_SNAPSHOT_UNVERIFIED")
    _require(record["output_schema_sha256"] == choice_output_schema_sha256(), "PROVENANCE_SCHEMA_MISMATCH")
    _require(type(raw_choice) is bytes and hashlib.sha256(raw_choice).hexdigest() == record["raw_output_sha256"],
             "PROVENANCE_OUTPUT_MISMATCH")
    _require(record["candidate_menu_sha256"] == candidate_menu_sha256, "PROVENANCE_MENU_MISMATCH")
    times = [record[k] for k in ("information_cutoff_ns", "issued_at_ns", "response_completed_ns", "deadline_ns")]
    _require(all(stage_b._time(t) for t in times) and record["information_cutoff_ns"] == information_cutoff_ns and
             times[0] <= times[1] <= times[2] <= evaluated_at_ns < times[3], "PROVENANCE_CLOCK_INVALID")
    bound_request = stage_b.StageBRequest(**{k: record[k] for k in (
        "request_id", "candidate_menu_sha256", "output_schema_sha256", "model_input_sha256",
        "information_cutoff_ns", "issued_at_ns", "deadline_ns", "model_label", "hermes_commit",
        "tool_surface_fingerprint", "runtime_profile_sha256")})
    _require(stage_b.request_is_bound(bound_request), "PROVENANCE_ORIGIN_FORGED")
    return dict(record)


# --------------------------------------------------------------------- REAL-01 seam


REAL_ORIGIN_UNVERIFIED = "REAL_ORIGIN_UNVERIFIED"


def verify_real_origin_evidence(evidence: object) -> dict:
    """Fail-closed real-origin admission seam (S10-HERMES-AUTO-02-REAL-01 / -ACTIVATION).

    Only first-party evidence observed on a genuinely invoked provider transport may pass:
    the live, non-replayed ``oauth_plan_stage_b.OAuthPlanResult`` witnessed by that module
    (real mode, plan eligibility established, provider-reported response id, exact model and
    usage). Its verified origin record is returned. Every other input -- REAL-01 offline
    records, mock-transport or replayed results, relabelled strings, recomputed digests or
    forged dicts -- is rejected with ``REAL_ORIGIN_UNVERIFIED``.
    """
    from src.research_runtime.hermes_controlled_runtime import oauth_plan_stage_b as oauth
    if not oauth.is_witnessed_result(evidence):
        raise FeedbackRejected(REAL_ORIGIN_UNVERIFIED)
    return dict(evidence.origin)


def admit_real01_choice(result: object, **evaluate_once_kwargs) -> dict:
    """Route one REAL-01 Stage B result through AUTO-01; always a non-executable rejection today."""
    from src.research_runtime import autonomous_opportunity_cycle as cycle
    from src.research_runtime.hermes_controlled_runtime import real_provider_stage_b as real
    _require(type(result) is real.Real01Result and result.status == real.VALID_OUTPUT and
             type(result.output_bytes) is bytes, "REAL01_RESULT_INVALID")
    return cycle.evaluate_once(choice=result.output_bytes, real_origin_evidence=result.origin, **evaluate_once_kwargs)


def admit_oauth_choice(result: object, **evaluate_once_kwargs) -> dict:
    """Route one ACTIVATION OAuth result through AUTO-01; at best a non-executable preview."""
    from src.research_runtime import autonomous_opportunity_cycle as cycle
    from src.research_runtime.hermes_controlled_runtime import oauth_plan_stage_b as oauth
    _require(type(result) is oauth.OAuthPlanResult and result.status == oauth.VALID_OUTPUT and
             type(result.output_bytes) is bytes, "OAUTH_RESULT_INVALID")
    return cycle.evaluate_once(choice=result.output_bytes, real_origin_evidence=result, **evaluate_once_kwargs)


# --------------------------------------------------------------------- paper feedback


def _cutoff_text(ns: int) -> str:
    seconds, rest = divmod(ns, 1_000_000_000)
    return (_UNIX_EPOCH + timedelta(seconds=seconds + (1 if rest else 0))).strftime("%Y-%m-%dT%H:%M:%SZ")


def _facts(snapshot) -> dict:
    counts = dict(snapshot.closed_order_state_counts)
    return dict(intent_count=snapshot.intent_count, order_count=snapshot.order_count, fill_count=snapshot.fill_count,
                rejected_order_count=counts.get("REJECTED", 0), risk_deny_count=snapshot.risk_deny_count,
                fill_ratio=snapshot.fill_ratio, fee_total=snapshot.fee_total,
                slippage_total=snapshot.depth_slippage_cost_total, spread_cost_total=snapshot.spread_cost_total,
                adverse_selection_cost_total=snapshot.adverse_selection_cost_total,
                pending_markout_count=snapshot.pending_markout_count,
                realized_paper_pnl=snapshot.realized_paper_pnl,
                unrealized_paper_pnl=snapshot.unrealized_paper_pnl)  # None stays UNKNOWN, never zero


def run_paper_performance_update(*, paper_store_path, expected_binding, lifecycle_snapshot, strategy_version_id,
                                 information_cutoff, decision_time_ns, backend, hermes_manager_store_path,
                                 provider_label, model_label, clock=None) -> dict:
    """Verified research-paper outcome -> next native PERFORMANCE_UPDATE assessment."""
    from decimal import Decimal
    from src.research_runtime.hermes_controlled_runtime import strategy_manager as sm
    from src.research_runtime.hermes_controlled_runtime.runner import FakeHermesBackend
    # Paper access only through the existing read-only WP173 adapter (P036: this package
    # imports no paper/execution surface directly).
    from src.research_runtime import paper_performance_bridge as bridge
    PaperStore, ResearchPaperStrategyBinding = bridge.PaperStore, bridge.ResearchPaperStrategyBinding
    build_research_paper_performance_snapshot = bridge.build_research_paper_performance_snapshot
    build_snapshot_context_evidence = bridge.build_snapshot_context_evidence
    receipt = dict(schema_id="hermes-auto02-paper-feedback", status="REJECTED", reason_code=None,
                   paper_snapshot_id=None, evidence_id=None, direction=None, facts=None,
                   manager_status=None, manager_error=None, run_record_id=None, assessment_id=None,
                   trigger="PERFORMANCE_UPDATE", paper_evidence_class="RESEARCH_PAPER_SIMULATED",
                   live_pnl_claim=False, no_order=True, no_policy_mutation=True)
    try:
        _require(isinstance(backend, FakeHermesBackend), "BACKEND_NOT_OFFLINE")
        binding = expected_binding
        _require(type(binding) is ResearchPaperStrategyBinding and binding.research_paper_only and
                 not binding.live_promotion_eligible and not binding.gate_c_eligible and
                 Decimal(binding.real_capital_usd) == 0, "BINDING_NOT_RESEARCH_ONLY")
        version = lifecycle_snapshot.version_by_id(strategy_version_id)
        _require(version is not None and binding.candidate_id in version.evidence_refs, "BINDING_STRATEGY_MISMATCH")
        path = Path(paper_store_path)
        # PaperStore creates missing files; a missing outcome must fail before opening.
        _require(path.is_file() and not path.is_symlink(), "PAPER_OUTCOME_MISSING")
        try:
            with PaperStore(path) as store:
                snapshot = build_research_paper_performance_snapshot(store)
        except Exception:
            raise FeedbackRejected("PAPER_STORE_INVALID") from None
        receipt["paper_snapshot_id"] = snapshot.snapshot_id
        _require(snapshot.binding_kind == "RESEARCH_PAPER" and (
            snapshot.binding_id, snapshot.candidate_id, snapshot.strategy_spec_id, snapshot.strategy_version,
            snapshot.strategy_code_identity, snapshot.subject_refs, snapshot.scope_id) == (
            binding.binding_id, binding.candidate_id, binding.strategy_spec_id, binding.strategy_version,
            binding.strategy_code_identity, binding.subject_refs, binding.scope_id),
            "PAPER_SCOPE_MISMATCH")
        cutoff = sm.validate_information_cutoff(information_cutoff)
        evidence_cutoff = _cutoff_text(snapshot.information_cutoff_ns)
        _require(evidence_cutoff <= cutoff, "PAPER_EVIDENCE_AFTER_CUTOFF")
        history = sm.load_hermes_strategy_manager_store(hermes_manager_store_path)
        previous = next((a for a in history.assessments
                         if a.assessment_id == history.latest_assessment_id(strategy_version_id)), None)
        _require(previous is None or previous.information_cutoff < cutoff, "CUTOFF_NOT_ADVANCED")
        facts = _facts(snapshot)
        total = Decimal(snapshot.realized_paper_pnl) + Decimal(snapshot.unrealized_paper_pnl or "0")
        # Missing marks or non-positive paper results are contradicting, never assumed flat.
        direction = "SUPPORTING" if snapshot.unrealized_paper_pnl is not None and total > 0 else "CONTRADICTING"
        item = build_snapshot_context_evidence(
            snapshot, subject_refs=snapshot.subject_refs, scope_sha256=snapshot.scope_id.rsplit(":", 1)[1],
            information_cutoff=evidence_cutoff, admissibility_status="ADMISSIBLE", direction=direction)
        summary = (f"simulated research paper: orders {facts['order_count']} fills {facts['fill_count']} "
                   f"rejected {facts['rejected_order_count']} fill ratio {facts['fill_ratio']} "
                   f"realized {facts['realized_paper_pnl']} unrealized {facts['unrealized_paper_pnl'] or 'UNKNOWN'}")
        evidence = sm.build_strategy_assessment_evidence(item, summary[:160])
        receipt.update(evidence_id=item.evidence_id, direction=direction, facts=facts)
        result = sm.run_hermes_strategy_assessment(
            lifecycle_snapshot=lifecycle_snapshot, strategy_version_id=strategy_version_id,
            trigger="PERFORMANCE_UPDATE", trigger_ref=snapshot.snapshot_id,
            subject_refs=(version.strategy_version_id, version.strategy_family_id, *snapshot.subject_refs),
            evidence=(evidence,), information_cutoff=cutoff, decision_time_ns=decision_time_ns,
            provider_label=provider_label, model_label=model_label, backend=backend,
            store_path=hermes_manager_store_path, clock=clock)
        receipt.update(manager_status=result.status, manager_error=result.error_code,
                       run_record_id=result.run_record.run_record_id if result.run_record else None,
                       assessment_id=result.assessment.assessment_id if result.assessment else None,
                       status="ASSESSED" if result.status == sm.STATUS_ASSESSMENT_RECORDED else "MANAGER_NOT_ASSESSED")
    except FeedbackRejected as error:
        receipt.update(reason_code=str(error))
    except Exception:
        receipt.update(reason_code="FEEDBACK_INPUT_INVALID")
    return receipt


# --------------------------------------------------------------------- one cycle


def _write_once(path: Path, body: dict) -> None:
    with path.open("xb") as stream:
        stream.write(stage_b._canonical(body))


def _read_bundle(path: Path) -> dict:
    bundle = json.loads(path.read_bytes())
    body = {k: v for k, v in bundle.items() if k != "bundle_id"}
    _require(bundle.get("bundle_id") == CYCLE_PREFIX + _digest(body), "JOURNAL_TAMPERED")
    return bundle


def cycle_request(*, surface_report, candidate_menu, information_cutoff_ns, issued_at_ns, deadline_ns,
                  model_label) -> stage_b.StageBRequest:
    """The Stage B request a cycle dispatches; the menu digest is AUTO-01's own."""
    from src.research_runtime import autonomous_opportunity_cycle as cycle
    menu = [dict(item) for item in candidate_menu]
    return stage_b.build_stage_b_request(
        surface_report=surface_report, candidate_menu_sha256=cycle._digest(menu),
        output_schema_sha256=choice_output_schema_sha256(),
        model_input_sha256=_digest(dict(menu=menu, information_cutoff_ns=information_cutoff_ns)),
        information_cutoff_ns=information_cutoff_ns, issued_at_ns=issued_at_ns, deadline_ns=deadline_ns,
        model_label=model_label)


def run_one_cycle(*, journal_dir, surface_report, backend, model_label, candidate_menu, lifecycle_store_path,
                  hermes_manager_store_path, alpha_registry_path, venue_snapshots, information_cutoff_ns,
                  issued_at_ns, evaluated_at_ns, deadline_ns, prior_paper_snapshot_id=None,
                  paper_feedback=None) -> dict:
    """One finite cycle; every terminal (including denials) is a bound denominator outcome."""
    from src.research_runtime import autonomous_opportunity_cycle as cycle
    bundle = dict(schema_id="hermes-auto02-cycle", cycle_id=None, request_id=None, outcome=None,
                  tool_surface_fingerprint=None, hermes_commit=None, stage_b_status=None,
                  choice_provenance_id=None, auto01_receipt_id=None, auto01_status=None, auto01_reason_codes=[],
                  auto01_native_reasons={}, paper_feedback=None, real_provider=stage_b.REAL_PROVIDER_NOT_INVOKED,
                  model_origin_proof=MODEL_ORIGIN, preview_authority="NON_EXECUTABLE_WITHOUT_SEPARATE_LIVE_AUTHORITY",
                  no_live=True, no_order=True)
    try:
        menu = [dict(item) for item in candidate_menu]
        request = cycle_request(surface_report=surface_report, candidate_menu=menu,
                                information_cutoff_ns=information_cutoff_ns, issued_at_ns=issued_at_ns,
                                deadline_ns=deadline_ns, model_label=model_label)
    except Exception as error:
        bundle.update(outcome="TOOL_SURFACE_OR_REQUEST_REJECTED",
                      stage_b_status=str(error) if isinstance(error, ValueError) else "REQUEST_INVALID")
        bundle["bundle_id"] = CYCLE_PREFIX + _digest(bundle)
        return bundle
    if prior_paper_snapshot_id is not None:
        bundle.update(outcome="PRIOR_PAPER_SNAPSHOT_UNVERIFIED", request_id=request.request_id)
        bundle["bundle_id"] = CYCLE_PREFIX + _digest(bundle)
        return bundle
    root = Path(journal_dir).absolute()
    terminal = root / ("cycle-" + request.request_id.rsplit(":", 1)[1] + ".json")
    if terminal.exists():
        try:
            return _read_bundle(terminal)  # replay: stored evidence only, zero redispatch
        except Exception:
            bundle.update(outcome="JOURNAL_INVALID", request_id=request.request_id)
            bundle["bundle_id"] = CYCLE_PREFIX + _digest(bundle)
            return bundle
    bundle.update(cycle_id=CYCLE_PREFIX + request.request_id.rsplit(":", 1)[1], request_id=request.request_id,
                  tool_surface_fingerprint=request.tool_surface_fingerprint, runtime_profile_sha256=request.runtime_profile_sha256, hermes_commit=request.hermes_commit)
    result = stage_b.run_tool_free_stage_b(request, backend=backend, reservation_dir=root)
    bundle["stage_b_status"] = result.status
    if result.status == "DISPATCH_ALREADY_RESERVED":
        # Interrupted (or concurrently running) earlier dispatch: block, never journal over it.
        bundle["outcome"] = "INTERRUPTED_BLOCKED"
        bundle["bundle_id"] = CYCLE_PREFIX + _digest(bundle)
        return bundle
    receipt = None
    if result.status != stage_b.VALID_OUTPUT:
        bundle["outcome"] = result.status
    else:
        try:
            receipt = _admit(cycle, request, result, menu, lifecycle_store_path, hermes_manager_store_path,
                             alpha_registry_path, venue_snapshots, information_cutoff_ns, evaluated_at_ns, deadline_ns)
            bundle.update(choice_provenance_id=receipt["choice_provenance_id"], auto01_receipt_id=receipt["receipt_id"],
                          auto01_status=receipt["status"], auto01_reason_codes=list(receipt["reason_codes"]),
                          auto01_native_reasons=receipt["native_reasons"],
                          outcome=receipt["reason_codes"][0] if receipt["status"] == "NO_TRADE" else receipt["status"])
        except Exception:
            bundle["outcome"] = "PROVENANCE_OR_STORE_INVALID"
    if paper_feedback is not None:
        bundle["paper_feedback"] = _linked_feedback(paper_feedback, receipt, hermes_manager_store_path)
    bundle["bundle_id"] = CYCLE_PREFIX + _digest(bundle)
    _write_once(terminal, bundle)
    return bundle


def _linked_feedback(paper_feedback: dict, receipt: dict | None, hermes_manager_store_path) -> dict:
    """PERFORMANCE_UPDATE only for the native selection this cycle actually previewed.

    Non-trade, rejected, inconclusive or invalid decisions defer feedback (the standalone
    helper stays available); a mismatched strategy/candidate/store never reaches the manager.
    """
    linkage = dict(decision_linkage=None, linked_auto01_receipt_id=None, linked_candidate_id=None,
                   linked_strategy_version_id=None)
    if receipt is None or receipt["status"] != "ELIGIBLE_PREVIEW":
        return dict(schema_id="hermes-auto02-paper-feedback", status="DEFERRED_NOT_DECISION_LINKED",
                    reason_code="NO_PREVIEWED_SELECTION", **dict(linkage, decision_linkage="DEFERRED"))
    try:
        binding, lifecycle = paper_feedback["expected_binding"], paper_feedback["lifecycle_snapshot"]
        linked = (paper_feedback["strategy_version_id"] == receipt["strategy_version_id"] and
                  getattr(binding, "candidate_id", None) == receipt["candidate_id"] and
                  getattr(lifecycle, "store_head_entry_hash", None) == receipt["lifecycle_head"] and
                  Path(paper_feedback["hermes_manager_store_path"]).resolve() == Path(hermes_manager_store_path).resolve())
    except Exception:
        linked = False
    if not linked:
        return dict(schema_id="hermes-auto02-paper-feedback", status="REJECTED", reason_code="FEEDBACK_LINEAGE_MISMATCH",
                    **dict(linkage, decision_linkage="MISMATCH"))
    try:
        feedback = run_paper_performance_update(**paper_feedback)
    except TypeError:  # malformed caller arguments must not lose an already-dispatched cycle
        return dict(schema_id="hermes-auto02-paper-feedback", status="REJECTED", reason_code="FEEDBACK_INPUT_INVALID",
                    **dict(linkage, decision_linkage="MISMATCH"))
    feedback.update(decision_linkage="DECISION_LINKED", linked_auto01_receipt_id=receipt["receipt_id"],
                    linked_candidate_id=receipt["candidate_id"], linked_strategy_version_id=receipt["strategy_version_id"])
    return feedback


def _admit(cycle, request, result, menu, lifecycle_store_path, hermes_manager_store_path, alpha_registry_path,
           venue_snapshots, information_cutoff_ns, evaluated_at_ns, deadline_ns) -> dict:
    from src.strategy_lifecycle import load_strategy_lifecycle_store
    from src.research_runtime.hermes_controlled_runtime.strategy_manager import load_hermes_strategy_manager_store
    from src.strategy_lifecycle.models import strict_json_loads
    proposal = strict_json_loads(result.output_bytes.decode("utf-8"))
    lifecycle = load_strategy_lifecycle_store(lifecycle_store_path).snapshot
    hermes = load_hermes_strategy_manager_store(hermes_manager_store_path)
    claimed = proposal.get("action") == "TRADE"
    record = build_choice_provenance(
        result, request=request,
        strategy_version_id=proposal.get("strategy_version_id") if claimed and _optional_id(proposal.get("strategy_version_id")) else None,
        hermes_assessment_id=proposal.get("hermes_assessment_id") if claimed and _optional_id(proposal.get("hermes_assessment_id")) else None,
        lifecycle_head=lifecycle.store_head_entry_hash if lifecycle else None,
        hermes_head=hermes.store_head_entry_hash)
    receipt = cycle.evaluate_once(
        lifecycle_store_path=lifecycle_store_path, hermes_manager_store_path=hermes_manager_store_path,
        alpha_registry_path=alpha_registry_path, candidate_menu=menu, choice=result.output_bytes,
        venue_snapshots=venue_snapshots, evaluated_at_ns=evaluated_at_ns,
        information_cutoff_ns=information_cutoff_ns, deadline_ns=deadline_ns, producer_evidence=record)
    return dict(receipt, choice_provenance_id=record["provenance_id"])
