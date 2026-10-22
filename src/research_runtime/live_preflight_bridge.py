"""One witnessed OAuth choice + canonical strategy assessment -> read-only LIVE-ORCH preflight.

S10-HERMES-LIVE-BRIDGE-01. A foreground composer of unchanged native interfaces only:

    witnessed OAuthPlanResult -> AUTO-01 admission (choice, menu, clocks, lineage)
    -> latest canonical HermesStrategyAssessment + its run record (verified store)
    -> fresh public venue -> native ExecutionIntent / feasibility / Gate C permit
    -> LiveOrchestrator.preflight(permit, intent)

It never invokes a provider, reads a credential, opens an account session, signs or
transmits anything. NO_TRADE / PAUSE / REASSESS abstain before any venue read or permit.
The frozen Stage B ``SYNTHETIC_ONLY`` label is kept as a label: the OAuth witness proves
only that the choice bytes came from a real call, never live venue or market truth. A
valid assessment's provider/model labels are not proof of authenticated inference. Any
injected seam marks the receipt OFFLINE_TEST_ONLY (protocol proof, never a real PASS).
Lives outside hermes_controlled_runtime because P036 bans execution_gateway imports there.
"""
import hashlib
import json

_MAX_TIME = 2**63 - 1
_ABSTAIN = ("NO_TRADE", "PAUSE", "REASSESS")
_STRATEGY_CODES = {"HERMES_ASSESSMENT_REQUIRED", "HERMES_ASSESSMENT_STALE", "HERMES_LINEAGE_STALE_OR_FORGED"}
_SEAMS = ("clock_ns", "host_currentness", "geoblock", "venue_fetcher")


class _Blocked(Exception):
    def __init__(self, code: str, *more: str):
        super().__init__(code)
        self.codes = [code, *more]


def _require(condition: bool, code: str, *more: str) -> None:
    if not condition:
        raise _Blocked(code, *more)


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def run_live_preflight_bridge(
    oauth_result, *, live_config, alpha_registry_path, candidate_menu, menu_venue_snapshots,
    evaluated_at_ns, information_cutoff_ns, deadline_ns, max_public_data_age_ns=5_000_000_000,
    max_hermes_age_ns=300_000_000_000, clock_ns=None, host_currentness=None, geoblock=None,
    venue_fetcher=None,
) -> dict:
    """Return one sanitized PASS / BLOCKED / ABSTAIN receipt; never raises, never trades.

    ``oauth_result`` is an already produced, in-memory OAuthPlanResult; the caller owns its
    separately authorized production. ``menu_venue_snapshots`` are the pre-choice public
    snapshots the menu was derived from (AUTO-01 requires them at or before the cutoff).
    The four seams default to the native LIVE-ORCH read-only functions; supplying any of
    them classifies the run as OFFLINE_TEST_ONLY.
    """
    seams = dict(clock_ns=clock_ns, host_currentness=host_currentness, geoblock=geoblock,
                 venue_fetcher=venue_fetcher)
    offline = any(seams[name] is not None for name in _SEAMS)
    calls = dict(provider=0, oauth_dispatch=0, venue_fetch=0, permit_built=0, preflight=0, canary=0, reconcile=0,
                 private_session=0, order=0)
    receipt = dict(
        schema_id="hermes-live-preflight-bridge", schema_version="1.0.0",
        status="BLOCKED", stage="WITNESS", reason_codes=[], native_reasons={},
        evidence_class="OFFLINE_TEST_ONLY" if offline else "NATIVE_READ_ONLY_SEAMS",
        claim="PROTOCOL_ONLY" if offline else "READ_ONLY_PREFLIGHT_ONLY_NOT_ACCOUNT_READINESS",
        choice_proof_level="SYNTHETIC_ONLY", choice_proof_level_meaning="FROZEN_STAGE_B_LABEL_NOT_LIVE_VENUE_EVIDENCE",
        choice_origin="UNVERIFIED", choice_origin_limit="PROVIDER_REPORTED_NOT_CRYPTOGRAPHIC",
        real_origin_record_id=None, requested_choice_sha256=None, candidate_menu_sha256=None, action=None,
        auto01_receipt_id=None, auto01_status=None, auto01_preview="NEVER_PROMOTED",
        strategy_assessment=None, strategy_origin_proof="LABELS_ONLY_NOT_PROOF_OF_AUTHENTICATED_INFERENCE",
        hermes_assessment_id=None, hermes_run_record_id=None, hermes_run_terminal_status=None,
        hermes_run_provider_label=None, hermes_run_model_label=None,
        candidate_id=None, strategy_version_id=None, gamma_market_id=None, condition_id=None, token_id=None,
        lifecycle_head=None, hermes_head=None, active_policy_id=None,
        fresh_venue_snapshot_id=None, execution_intent_id=None, feasibility_assessment_id=None,
        feasibility_status=None, gate_c_decision_id=None, permit_id=None, permit_valid_until_ns=None,
        preflight_status=None, preflight_code=None, preflight_details={},
        calls=calls, exposure_posture="NO_NEW_EXPOSURE", account_readiness="NOT_EVALUATED",
        no_order=True, no_live_authority=True,
    )
    try:
        from src.research_runtime.hermes_controlled_runtime import oauth_plan_stage_b as oauth
        # A replayed, mock, forged or unwitnessed result stops before any store read.
        _require(oauth.is_witnessed_result(oauth_result), "REAL_ORIGIN_UNVERIFIED")
        receipt.update(stage="CHOICE_AND_STRATEGY", real_origin_record_id=oauth_result.origin["record_id"],
                       choice_origin="OFFLINE_TEST_ONLY" if offline else "REAL_OAUTH_ORIGIN_BOUND")
        from src.research_runtime.hermes_controlled_runtime.autonomous_feedback import admit_oauth_choice
        admitted = admit_oauth_choice(
            oauth_result, lifecycle_store_path=live_config.lifecycle_store_path,
            hermes_manager_store_path=live_config.hermes_store_path, alpha_registry_path=alpha_registry_path,
            candidate_menu=candidate_menu, venue_snapshots=menu_venue_snapshots, evaluated_at_ns=evaluated_at_ns,
            information_cutoff_ns=information_cutoff_ns, deadline_ns=deadline_ns,
            max_public_data_age_ns=max_public_data_age_ns, max_hermes_age_ns=max_hermes_age_ns)
        receipt.update({k: admitted[k] for k in (
            "requested_choice_sha256", "candidate_menu_sha256", "candidate_id", "strategy_version_id",
            "gamma_market_id", "condition_id", "token_id", "lifecycle_head", "hermes_head", "active_policy_id",
            "hermes_assessment_id")}, auto01_receipt_id=admitted["receipt_id"], auto01_status=admitted["status"])
        codes = list(admitted["reason_codes"])
        if admitted["status"] == "NO_TRADE":
            _require(admitted["proof_level"] == "REAL_OAUTH_ORIGIN_BOUND" and len(codes) == 1 and
                     codes[0] in _ABSTAIN, "CHOICE_INVALID")
            receipt.update(status="ABSTAIN", stage="COMPLETE", action=codes[0], reason_codes=codes)
            return _finish(receipt)
        # The native gate verdict is recomputed below on a fresh venue; every earlier
        # AUTO-01 check (witness, menu, clocks, lineage, latest assessment) must have passed.
        reached_gate = admitted["status"] == "ELIGIBLE_PREVIEW" or codes == ["NATIVE_GATE_REJECTED"]
        if not reached_gate:
            extra = ["STRATEGY_ASSESSMENT_UNAVAILABLE"] if set(codes) & _STRATEGY_CODES else []
            receipt.update(native_reasons=dict(auto01=codes, **admitted["native_reasons"]))
            raise _Blocked(*(extra + codes or ["CHOICE_REJECTED"]))
        _require(admitted["proof_level"] == "REAL_OAUTH_ORIGIN_BOUND" and admitted["execution_intent"] is not None,
                 "CHOICE_INVALID")
        receipt["action"] = "TRADE"
        shape = admitted["execution_intent"]
        _require(shape["side"] == "BUY", "SIDE_UNSUPPORTED_FIRST_CANARY")
        choice = json.loads(oauth_result.output_bytes)
        _require(choice.get("proof_level") == "SYNTHETIC_ONLY", "CHOICE_INVALID")

        receipt["stage"] = "NATIVE_STRATEGY"
        from src.research_runtime.hermes_controlled_runtime.strategy_manager import load_hermes_strategy_manager_store
        from src.strategy_lifecycle import load_strategy_lifecycle_store
        hermes = load_hermes_strategy_manager_store(live_config.hermes_store_path)
        latest_id = hermes.latest_assessment_id(admitted["strategy_version_id"])
        latest = [a for a in hermes.assessments if a.assessment_id == latest_id]
        _require(hermes.store_head_entry_hash == admitted["hermes_head"] and len(latest) == 1 and
                 latest_id == admitted["hermes_assessment_id"], "STRATEGY_ASSESSMENT_UNAVAILABLE", "STORE_CHANGED")
        latest = latest[0]
        runs = [r for r in hermes.run_records if r.run_record_id == latest.run_record_id]
        _require(len(runs) == 1 and (runs[0].strategy_version_id, runs[0].runtime_request_id,
                 runs[0].runtime_receipt_id) == (latest.strategy_version_id, latest.runtime_request_id,
                 latest.runtime_receipt_id), "STRATEGY_ASSESSMENT_UNAVAILABLE", "STRATEGY_RUN_RECORD_MISMATCH")
        receipt.update(strategy_assessment="VALIDATED_CANONICAL_ONLY", hermes_run_record_id=runs[0].run_record_id,
                       hermes_run_terminal_status=runs[0].terminal_status,
                       hermes_run_provider_label=runs[0].provider_label, hermes_run_model_label=runs[0].model_label)
        lifecycle = load_strategy_lifecycle_store(live_config.lifecycle_store_path)
        _require(lifecycle.is_valid is True and lifecycle.snapshot is not None and
                 lifecycle.snapshot.store_head_entry_hash == admitted["lifecycle_head"], "STORE_CHANGED")
        version = lifecycle.snapshot.version_by_id(admitted["strategy_version_id"])
        window_end = min(admitted["choice_expires_at_ns"], deadline_ns, latest.decision_time_ns + max_hermes_age_ns)

        receipt["stage"] = "FRESH_NATIVE_PERMIT"
        from src.execution_gateway import live_orch
        from src.execution_feasibility import (
            ExecutionFeasibilityError, PublicExecutionVenueSnapshot, assess_execution_feasibility,
            build_execution_intent,
        )
        from src.exploratory_gate_c import build_exploratory_gate_c_permit, evaluate_exploratory_gate_c
        native = live_orch.LiveOrchDependencies()
        clock = seams["clock_ns"] or native.clock_ns
        fetch = seams["venue_fetcher"] or native.venue_fetcher

        def counted_fetch(**kwargs):
            calls["venue_fetch"] += 1
            return fetch(**kwargs)

        def refused(*_args, **_kwargs):  # preflight never needs a secret, client or pause
            calls["private_session"] += 1
            raise live_orch.GatewayError("BRIDGE_PRIVATE_ACCESS_REFUSED")

        now = clock()
        _require(type(now) is int and evaluated_at_ns <= now < window_end <= _MAX_TIME, "CHOICE_WINDOW_EXPIRED")
        try:
            snapshot = counted_fetch(gamma_market_id=shape["gamma_market_id"], condition_id=shape["condition_id"],
                                     token_id=shape["token_id"])
        except ExecutionFeasibilityError:
            raise _Blocked("VENUE_SNAPSHOT_UNAVAILABLE") from None
        _require(type(snapshot) is PublicExecutionVenueSnapshot and
                 (snapshot.gamma_market_id, snapshot.condition_id, snapshot.token_id) ==
                 (shape["gamma_market_id"], shape["condition_id"], shape["token_id"]) and
                 snapshot.acquisition_completed_ns > information_cutoff_ns, "VENUE_SNAPSHOT_INVALID")
        receipt["fresh_venue_snapshot_id"] = snapshot.venue_snapshot_id
        intent = build_execution_intent(
            strategy_version=version, **{k: shape[k] for k in (
                "gamma_market_id", "condition_id", "token_id", "side", "execution_style", "order_type",
                "requested_shares", "price_limit", "post_only", "gtd_expiration_unix_s")},
            information_cutoff_ns=snapshot.acquisition_completed_ns, max_public_data_age_ns=max_public_data_age_ns)
        at = max(clock(), snapshot.acquisition_completed_ns)
        feasibility = assess_execution_feasibility(intent, snapshot, evaluated_at_ns=at)
        decision = evaluate_exploratory_gate_c(
            lifecycle_store_path=live_config.lifecycle_store_path,
            hermes_manager_store_path=live_config.hermes_store_path, strategy_version_id=version.strategy_version_id,
            execution_intent=intent, venue_snapshot=snapshot, execution_feasibility_assessment=feasibility,
            evaluated_at_ns=at)
        receipt.update(execution_intent_id=intent.execution_intent_id,
                       feasibility_assessment_id=feasibility.execution_feasibility_assessment_id,
                       feasibility_status=feasibility.status, gate_c_decision_id=decision.decision_id,
                       native_reasons=dict(execution=list(feasibility.diagnostic_codes),
                                           gate_c=list(decision.reason_codes)))
        _require(decision.lifecycle_store_head_entry_hash == admitted["lifecycle_head"] and
                 decision.hermes_manager_store_head_entry_hash == admitted["hermes_head"] and
                 decision.hermes_assessment_id == latest.assessment_id, "STORE_CHANGED")
        _require(decision.status == "PERMIT_ELIGIBLE", "GATE_C_REJECTED")
        permit = build_exploratory_gate_c_permit(decision, execution_intent=intent)
        calls["permit_built"] += 1
        receipt.update(permit_id=permit.permit_id, permit_valid_until_ns=permit.valid_until_ns)

        receipt["stage"] = "PREFLIGHT"
        _require(clock() < window_end, "CHOICE_WINDOW_EXPIRED")
        dependencies = live_orch.LiveOrchDependencies(
            clock_ns=clock, host_currentness=seams["host_currentness"] or native.host_currentness,
            geoblock=seams["geoblock"] or native.geoblock, venue_fetcher=counted_fetch,
            secret_provider_factory=refused, client_factory=refused, pause=refused)
        orchestrator = live_orch.LiveOrchestrator(live_config, dependencies=dependencies)
        calls["preflight"] += 1
        result = orchestrator.preflight(permit, intent)
        details = {k: result.details[k] for k in ("venue_snapshot_id", "execution_feasibility_assessment_id",
                   "principal_notional_usd", "worst_case_fee_reserve_usd", "ledger_episodes") if k in result.details}
        receipt.update(preflight_status=result.status, preflight_code=result.code, preflight_details=details)
        _require(result.status == "PREFLIGHT_PASS" and result.create_transmits == 0, "PREFLIGHT_BLOCKED", result.code)
        receipt.update(status="PASS", stage="COMPLETE", reason_codes=["PREFLIGHT_PASS"])
    except _Blocked as error:
        receipt.update(status="BLOCKED", reason_codes=error.codes)
    except Exception as error:  # native validation code only; never the message or input
        code = getattr(error, "code", None)
        receipt.update(status="BLOCKED", reason_codes=["NATIVE_INPUT_REJECTED" if isinstance(code, str)
                                                       else "INPUT_OR_STORE_INVALID"])
        if isinstance(code, str) and code.isupper() and len(code) <= 64:
            receipt["native_reasons"] = dict(receipt["native_reasons"], validation=[code])
    if receipt["status"] != "PASS":
        receipt.update(permit_id=None, permit_valid_until_ns=None)
    return _finish(receipt)


def _finish(receipt: dict) -> dict:
    receipt["receipt_id"] = "livepreflightbridge:sha256:" + _digest(receipt)
    return receipt
