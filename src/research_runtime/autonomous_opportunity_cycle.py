"""One offline opportunity choice -> native mechanics -> non-executable preview.

No producer is invoked here. Synthetic input proves mechanics only; model origin
stays UNVERIFIED. Store paths and untrusted prose never enter the receipt.
"""
from datetime import datetime, timezone
import hashlib

from src.execution_feasibility import (
    ExecutionFeasibilityError, assess_execution_feasibility, build_execution_intent,
    validate_public_venue_snapshot,
)
from src.execution_feasibility.models import canonical_json_bytes, parse_decimal
from src.exploratory_gate_c import ExploratoryGateCError
from src.strategy_lifecycle import load_strategy_lifecycle_store
from src.strategy_lifecycle.models import strict_json_loads

_MAX_TIME = 2**63 - 1
_MENU_KEYS = {"candidate_id", "strategy_version_id", "gamma_market_id", "condition_id", "token_id"}
_CLOCK_KEYS = {"action", "proof_level", "information_cutoff_ns", "produced_at_ns", "expires_at_ns"}
_TRADE_KEYS = {
    "candidate_id", "strategy_version_id", "hermes_assessment_id", "context_sha256", "active_policy_id",
    "side", "execution_style", "order_type", "requested_shares", "price_limit", "post_only",
    "gtd_expiration_unix_s",
}


class _Rejected(ValueError):
    pass


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise _Rejected(code)


def _time(value: object) -> bool:
    return type(value) is int and 0 <= value <= _MAX_TIME


def _digest(value: object) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _utc_ns(value: str) -> int:
    moment = datetime.fromisoformat(value.replace("Z", "+00:00"))
    delta = moment - datetime(1970, 1, 1, tzinfo=timezone.utc)
    return (delta.days * 86400 + delta.seconds) * 1_000_000_000 + delta.microseconds * 1000


def evaluate_once(
    *, lifecycle_store_path, hermes_manager_store_path, alpha_registry_path,
    candidate_menu, choice, venue_snapshots, evaluated_at_ns, information_cutoff_ns,
    deadline_ns, max_public_data_age_ns=5_000_000_000, max_hermes_age_ns=300_000_000_000,
    venue_proof_level="SYNTHETIC_ONLY", producer_evidence=None, real_origin_evidence=None,
) -> dict:
    """Read verified stores, validate untrusted JSON bytes/text and return one receipt.

    Times are caller-supplied Unix nanoseconds, never sampled from the host clock.
    The bounded deadline is an evidence-time admission bound, not a background timer.
    Only explicitly synthetic injection is admitted until a real producer is authorized.
    ``producer_evidence`` (S10-HERMES-AUTO-02, optional) is a record from the trusted
    autonomous_feedback verifier binding this exact choice to an OFFLINE producer; it
    relabels proof_level only and never grants live, permit or model-origin authority.
    ``real_origin_evidence`` (S10-HERMES-AUTO-02-REAL-01, optional) is the dormant
    real-producer seam: it always rejects with ``REAL_ORIGIN_UNVERIFIED`` before any
    store is read, until a separately PROTECTED activation observes a real provider call.
    """
    receipt = dict(
        schema_id="hermes-autonomous-opportunity-cycle", schema_version="1.0.0",
        status="REJECTED", reason_codes=[], native_reasons={},
        candidate_menu_sha256=None, requested_choice_sha256=None, venue_snapshot_ids=[],
        evaluated_at_ns=evaluated_at_ns if _time(evaluated_at_ns) else None,
        information_cutoff_ns=information_cutoff_ns if _time(information_cutoff_ns) else None,
        deadline_ns=deadline_ns if _time(deadline_ns) else None,
        max_public_data_age_ns=max_public_data_age_ns if _time(max_public_data_age_ns) else None,
        max_hermes_age_ns=max_hermes_age_ns if _time(max_hermes_age_ns) else None,
        candidate_id=None, strategy_version_id=None, gamma_market_id=None, condition_id=None, token_id=None,
        lifecycle_head=None, hermes_head=None, alpha_head=None, active_policy_id=None,
        hermes_assessment_id=None, context_sha256=None, execution_intent=None,
        feasibility_assessment_id=None, feasibility_status=None, gate_c_decision_id=None,
        preview_permit=None, preview_valid_until_ns=None,
        choice_produced_at_ns=None, choice_expires_at_ns=None, hermes_decision_time_ns=None,
        proof_level="SYNTHETIC_ONLY", model_origin_proof="UNVERIFIED", exposure_posture="NO_NEW_EXPOSURE",
        preview_authority="NON_EXECUTABLE_WITHOUT_SEPARATE_LIVE_AUTHORITY",
        no_live=True, no_order=True,
    )
    if producer_evidence is not None:
        receipt.update(proof_level="OFFLINE_PRODUCER_BOUND", choice_provenance_id=None, choice_transport_mode=None,
                       producer_witness_class=None, real_provider="REAL_PROVIDER_NOT_INVOKED")
    if real_origin_evidence is not None:
        receipt.update(proof_level="REAL_ORIGIN_UNVERIFIED", real_origin_status="REAL_ORIGIN_UNVERIFIED",
                       real_provider="REAL_PROVIDER_NOT_INVOKED")
    record = None
    try:
        _require(all(_time(t) for t in (evaluated_at_ns, information_cutoff_ns, deadline_ns,
                                       max_public_data_age_ns, max_hermes_age_ns)), "TIME_INVALID")
        _require(0 < max_public_data_age_ns <= 300_000_000_000 and
                 0 < max_hermes_age_ns <= 86_400_000_000_000 and
                 information_cutoff_ns <= evaluated_at_ns < deadline_ns <=
                 evaluated_at_ns + 300_000_000_000, "DEADLINE_INVALID")
        _require(type(choice) in (str, bytes), "CHOICE_INVALID")
        raw = choice.encode("utf-8") if isinstance(choice, str) else choice
        _require(0 < len(raw) <= 16_384, "CHOICE_SIZE_INVALID")
        receipt["requested_choice_sha256"] = hashlib.sha256(raw).hexdigest()
        _require(type(candidate_menu) in (tuple, list) and len(candidate_menu) <= 8, "MENU_INVALID")
        _require(all(type(item) is dict and set(item) == _MENU_KEYS and
                     all(type(v) is str and 0 < len(v) <= 256 for v in item.values())
                     for item in candidate_menu), "MENU_INVALID")
        candidate_menu = [dict(item) for item in candidate_menu]
        # Hash the caller's ordered menu; never rank or replace its selected member.
        receipt["candidate_menu_sha256"] = _digest(list(candidate_menu))
        _require(len({m["candidate_id"] for m in candidate_menu}) == len(candidate_menu) and
                 len({m["strategy_version_id"] for m in candidate_menu}) == len(candidate_menu), "MENU_AMBIGUOUS")
        _require(type(venue_snapshots) in (tuple, list) and len(venue_snapshots) <= 8, "VENUE_MENU_INVALID")
        snapshots = []
        for snapshot in venue_snapshots:
            validate_public_venue_snapshot(snapshot)
            _require(snapshot.acquisition_completed_ns <= information_cutoff_ns, "VENUE_AFTER_CUTOFF")
            snapshots.append(snapshot)
        receipt["venue_snapshot_ids"] = [s.venue_snapshot_id for s in snapshots]
        _require(len(set(receipt["venue_snapshot_ids"])) == len(snapshots), "VENUE_AMBIGUOUS")
        proposal = strict_json_loads(raw.decode("utf-8"))
        _require(type(proposal) is dict, "CHOICE_INVALID")
        action = proposal.get("action")
        _require(action in ("TRADE", "NO_TRADE", "PAUSE", "REASSESS"), "CHOICE_INVALID")
        keys = _CLOCK_KEYS | _TRADE_KEYS if action == "TRADE" else _CLOCK_KEYS
        _require(set(proposal) == keys, "CHOICE_FIELDS_INVALID")
        _require(proposal["proof_level"] == venue_proof_level == "SYNTHETIC_ONLY", "PRODUCER_UNVERIFIED")
        _require(all(_time(proposal[k]) for k in ("information_cutoff_ns", "produced_at_ns", "expires_at_ns")),
                 "CHOICE_TIME_INVALID")
        _require(proposal["information_cutoff_ns"] == information_cutoff_ns and
                 information_cutoff_ns <= proposal["produced_at_ns"] <= evaluated_at_ns <
                 proposal["expires_at_ns"] <= deadline_ns, "CHOICE_STALE_OR_CUTOFF_CONFLICT")
        receipt.update(choice_produced_at_ns=proposal["produced_at_ns"], choice_expires_at_ns=proposal["expires_at_ns"])
        if real_origin_evidence is not None:
            from src.research_runtime.hermes_controlled_runtime.autonomous_feedback import verify_real_origin_evidence
            _require(producer_evidence is None, "PRODUCER_EVIDENCE_CONFLICT")
            try:
                verify_real_origin_evidence(real_origin_evidence)
            except ValueError as error:
                raise _Rejected(str(error)) from None
        if producer_evidence is not None:
            from src.research_runtime.hermes_controlled_runtime.autonomous_feedback import verify_choice_provenance
            try:
                record = verify_choice_provenance(producer_evidence, raw_choice=raw,
                    candidate_menu_sha256=receipt["candidate_menu_sha256"],
                    information_cutoff_ns=information_cutoff_ns, evaluated_at_ns=evaluated_at_ns)
            except ValueError as error:
                raise _Rejected(str(error)) from None
            # The model's own clock claim must fall inside the producer-observed dispatch window.
            _require(record["issued_at_ns"] <= proposal["produced_at_ns"] <= record["response_completed_ns"] and
                     record["deadline_ns"] == deadline_ns, "PRODUCER_CLOCK_CONFLICT")

        # Native Hermes/Gate-C imports transitively initialize analytical libraries.
        # Keep that work behind an explicit valid cycle, never module import.
        from src.exploratory_gate_c import build_exploratory_gate_c_permit, evaluate_exploratory_gate_c
        from src.research_runtime.hermes_controlled_runtime.strategy_manager import (
            load_hermes_strategy_manager_store, strategy_lifecycle_context_fingerprint,
        )
        lifecycle_result = load_strategy_lifecycle_store(lifecycle_store_path)
        _require(lifecycle_result.is_valid is True and lifecycle_result.snapshot is not None, "LIFECYCLE_STORE_INVALID")
        lifecycle = lifecycle_result.snapshot
        hermes = load_hermes_strategy_manager_store(hermes_manager_store_path)
        # Alpha's package initializes analytical libraries; defer that until an explicit cycle.
        from src.data_layer.analytical_research.alpha_factory import OpportunityCandidate
        from src.data_layer.analytical_research.alpha_factory_registry import load_and_verify_alpha_factory_registry
        alpha_result = load_and_verify_alpha_factory_registry(alpha_registry_path)
        _require(alpha_result.is_valid is True and alpha_result.snapshot is not None, "ALPHA_STORE_INVALID")
        alpha = alpha_result.snapshot
        candidates = {e.record.candidate_id: e.record for e in alpha.entries if type(e.record) is OpportunityCandidate}
        for item in candidate_menu:
            candidate = candidates.get(item["candidate_id"])
            version = lifecycle.version_by_id(item["strategy_version_id"])
            _require(candidate is not None and version is not None and
                     {ref for ref in version.evidence_refs if ref.startswith("alphacandidate:sha256:")} == {candidate.candidate_id} and
                     f'market:polymarket:{item["gamma_market_id"]}' in candidate.subject_refs and
                     f'token:polymarket:{item["token_id"]}' in candidate.subject_refs, "ALPHA_STRATEGY_LINEAGE_INVALID")
        receipt.update(lifecycle_head=lifecycle.store_head_entry_hash, hermes_head=hermes.store_head_entry_hash,
                       alpha_head=alpha.head_entry_hash, active_policy_id=lifecycle.active_policy_id)
        if record is not None:
            _require(record["lifecycle_head"] == lifecycle.store_head_entry_hash and
                     record["hermes_head"] == hermes.store_head_entry_hash, "PRODUCER_STATE_CHANGED")
            _require(action == "TRADE" or record["strategy_version_id"] is record["hermes_assessment_id"] is None,
                     "PRODUCER_CLAIM_MISMATCH")
            receipt.update(choice_provenance_id=record["provenance_id"], choice_transport_mode=record["transport_mode"],
                           producer_witness_class=record["producer_witness_class"])
        if action != "TRADE":
            receipt.update(status="NO_TRADE", reason_codes=[action], exposure_posture="NO_NEW_EXPOSURE")
        else:
            selected = [m for m in candidate_menu if m["candidate_id"] == proposal["candidate_id"] and
                        m["strategy_version_id"] == proposal["strategy_version_id"]]
            _require(len(selected) == 1, "CHOICE_OUTSIDE_MENU")
            item = selected[0]
            version = lifecycle.version_by_id(item["strategy_version_id"])
            matches = [s for s in snapshots if (s.gamma_market_id, s.condition_id, s.token_id) ==
                       (item["gamma_market_id"], item["condition_id"], item["token_id"])]
            _require(len(matches) == 1, "VENUE_MISSING_OR_AMBIGUOUS")
            snapshot = matches[0]
            latest_id = hermes.latest_assessment_id(version.strategy_version_id)
            latest = next((a for a in hermes.assessments if a.assessment_id == latest_id), None)
            _require(latest is not None, "HERMES_ASSESSMENT_REQUIRED")
            context = strategy_lifecycle_context_fingerprint(lifecycle, version.strategy_version_id)
            _require(proposal["hermes_assessment_id"] == latest.assessment_id and
                     proposal["context_sha256"] == latest.strategy_lifecycle_context_sha256 == context and
                     proposal["active_policy_id"] == latest.active_policy_id == lifecycle.active_policy_id,
                     "HERMES_LINEAGE_STALE_OR_FORGED")
            _require(record is None or (record["strategy_version_id"], record["hermes_assessment_id"]) ==
                     (version.strategy_version_id, latest.assessment_id), "PRODUCER_CLAIM_MISMATCH")
            _require(evaluated_at_ns - max_hermes_age_ns < latest.decision_time_ns <= information_cutoff_ns and
                     _utc_ns(latest.information_cutoff) <= information_cutoff_ns, "HERMES_ASSESSMENT_STALE")
            receipt.update(**item, hermes_assessment_id=latest.assessment_id, context_sha256=context,
                           hermes_decision_time_ns=latest.decision_time_ns)
            shape = {k: proposal[k] for k in ("side", "execution_style", "order_type", "requested_shares",
                     "price_limit", "post_only", "gtd_expiration_unix_s")}
            _require(shape["order_type"] in ("GTC", "GTD"), "ORDER_TYPE_UNSUPPORTED")
            # Native parsing rejects floats, noncanonical syntax, infinity and excess precision.
            parse_decimal(shape["requested_shares"])
            parse_decimal(shape["price_limit"])
            intent = build_execution_intent(strategy_version=version,
                **{k: item[k] for k in ("gamma_market_id", "condition_id", "token_id")}, **shape,
                information_cutoff_ns=information_cutoff_ns, max_public_data_age_ns=max_public_data_age_ns)
            feasibility = assess_execution_feasibility(intent, snapshot, evaluated_at_ns=evaluated_at_ns)
            decision = evaluate_exploratory_gate_c(
                lifecycle_store_path=lifecycle_store_path, hermes_manager_store_path=hermes_manager_store_path,
                strategy_version_id=version.strategy_version_id, execution_intent=intent, venue_snapshot=snapshot,
                execution_feasibility_assessment=feasibility, evaluated_at_ns=evaluated_at_ns)
            # Gate C reopens both stores: reject concurrent changes rather than bind mixed evidence.
            _require(decision.lifecycle_store_head_entry_hash == lifecycle.store_head_entry_hash and
                     decision.hermes_manager_store_head_entry_hash == hermes.store_head_entry_hash and
                     decision.hermes_assessment_id == latest.assessment_id, "STORE_CHANGED_DURING_CYCLE")
            receipt.update(execution_intent=intent.to_mapping(),
                feasibility_assessment_id=feasibility.execution_feasibility_assessment_id,
                feasibility_status=feasibility.status, gate_c_decision_id=decision.decision_id,
                native_reasons=dict(execution=list(feasibility.diagnostic_codes), gate_c=list(decision.reason_codes),
                    capacity=list(decision.portfolio_capacity_reason_codes),
                    strategy_capacity=list(decision.target_strategy_capacity_reason_codes)))
            if decision.status == "PERMIT_ELIGIBLE":
                permit = build_exploratory_gate_c_permit(decision, execution_intent=intent)
                receipt.update(status="ELIGIBLE_PREVIEW", preview_permit=permit.to_mapping(),
                    preview_valid_until_ns=min(permit.valid_until_ns, proposal["expires_at_ns"],
                                              latest.decision_time_ns + max_hermes_age_ns))
            else:
                receipt.update(status="INCONCLUSIVE" if feasibility.status == "INCONCLUSIVE" else "REJECTED",
                               reason_codes=["NATIVE_GATE_REJECTED"])
    except _Rejected as error:
        receipt.update(status="REJECTED", reason_codes=[str(error)], preview_permit=None)
    except (ExecutionFeasibilityError, ExploratoryGateCError) as error:
        receipt.update(status="REJECTED", reason_codes=["NATIVE_INPUT_REJECTED"],
                       native_reasons={"validation": [error.code]}, preview_permit=None)
    except Exception:
        receipt.update(status="REJECTED", reason_codes=["INPUT_OR_STORE_INVALID"], preview_permit=None)
    receipt["receipt_id"] = "decisioncycle:sha256:" + _digest(receipt)
    return receipt
