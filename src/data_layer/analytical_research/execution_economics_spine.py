"""B3 shared-PIT A7 execution-economics diagnostic over native producers (S10-CAP-EXEC-ECONOMICS-01).

A thin, deterministic, offline consumer. It mints no market, fee, fill, queue, risk or strategy model:

* ``select_leg``: the cold-verified B2 core -> one A5 ``ADMITTED`` model containing the shared-case target ->
  one A7-pointer basket -> exactly one target leg (market id + YES/NO side, never by token name or order).
* ``bind_snapshot``: the frozen REL-01 request + cold-verified SRC-01 grounding markets -> native
  ``run_related_market_alpha._venue_snapshots`` over the retained Gamma/CLOB bytes; the snapshot id must equal the
  B2 leg and the single REL ``BOUND`` record, and acquisition must complete by the frozen REL decision clock.
* ``assess_point``: caller-frozen native ``StrategyVersion`` + ``ExecutionIntent`` -> native
  ``assess_execution_feasibility`` at that clock + full recomputation (shares vs USDC units and unknowns kept).
* ``replay_diagnostic`` (optional): native WP167 describe -> WP168 conversion via WP172 market truth ->
  ``assess_executable_edge`` on non-OOS WP170 fixture records -> WP173 ``build_strategy_binding`` refusal.

Evidence class SYNTHETIC_TEST_ONLY: a delayed public quote is not a fill, a non-OOS diagnostic is not a first look,
and nothing here is a signal, size, recommendation, order, paper binding or value claim.
"""
from __future__ import annotations

from dataclasses import asdict, fields
from decimal import Decimal, InvalidOperation
from collections import Counter
import json
import re

from src.data_layer.analytical_research import related_market_economics as RE
from src.data_layer.analytical_research import relation_wallet_spine as RW
from src.data_layer.analytical_research import source_forecast_spine as SP
from src.data_layer.analytical_research import source_grounding as SG
from src.execution_feasibility import evaluator as EV
from src.execution_feasibility import models as EFM
from src import strategy_lifecycle as SL

WP_ID = "S10-CAP-EXEC-ECONOMICS-01"
CASE_SCHEMA = "s10-cap-b3-execution-economics-case-v1"
RECEIPT_SCHEMA = "s10-cap-b3-execution-economics-receipt-v1"
RECEIPT_PREFIX = "b3research:sha256:"
EVIDENCE_CLASS = "SYNTHETIC_TEST_ONLY"
CASE_KEYS = {"schema_id", "evidence_class", "b2_receipt_id", "model_id", "basket_id", "leg_side", "strategy_version",
             "probe_intent", "replay"}
REPLAY_KEYS = {"parquet_sha256", "known_gap_policy", "context", "experiment", "evidence", "cost_model", "decision_event"}
GAP_POLICIES = ("AS_CAPTURED", "KNOWN_GAPS")  # never NONE: a synthetic fixture cannot attest continuity
B2_ID_RE = re.compile(r"b2research:sha256:[0-9a-f]{64}")
BASKET_RE = re.compile(r"[A-Z][A-Z_]{0,31}")
HEX64_RE = re.compile(r"[0-9a-f]{64}")
TOKEN_PREFIX = "token:polymarket:"
MAX_REPLAY_ROWS = 4096
PAPER_LABEL = "B3_SYNTHETIC_DIAGNOSTIC"
# PMXT descriptor labels for a local synthetic fixture: the third-party format label is not provider history.
PMXT_FIXTURE = {"object_name": "case.parquet", "partition_identity": "synthetic_case", "quality_tier": "synthetic_fixture",
                "license_id": "SYNTHETIC_TEST_ONLY", "attribution": "local synthetic fixture"}
WP170_LINEAGE = ("experiment_family_id", "trial_number", "dataset_binding_id", "research_dataset_manifest_id",
                 "split_assignment_id", "feature_set_id", "label_definition_id", "code_version", "parameters_json",
                 "random_seeds", "baseline_id")
UNITS = {"best_bid": "USDC_PER_SHARE", "best_ask": "USDC_PER_SHARE", "spread": "USDC_PER_SHARE",
         "requested_shares": "SHARES", "visible_fill_shares": "SHARES", "fill_ratio": "RATIO",
         "weighted_execution_price": "USDC_PER_SHARE", "slippage_per_share": "USDC_PER_SHARE",
         "slippage_cost_usd": "USDC", "visible_depth_capacity_shares": "SHARES", "price_bound_capacity_shares": "SHARES",
         "minimum_order_notional_usd": "USDC", "intent_notional_at_price_limit_usd": "USDC",
         "theoretical_fee_unrounded_usd": "USDC", "fee_upper_bound_usd": "USDC", "maker_rebate_rate": "RATE",
         "seconds_delay": "SECONDS"}
FROZEN_UNKNOWNS = ("expected_maker_rebate_usd", "client_latency_ns", "passive_fill_probability", "adverse_selection_cost")
REPLAY_FIELDS = ("status", "origin", "source", "window", "wp170", "cost_model_id", "trace_id", "assessment", "wp173")

# Seven W06 IDs at their frozen 36-row CSV pins (sha256 ecea9023...); the CSV is never edited.
PINS = {
    "R3-09": ("Synpath-ai/synpath", "ab7c64b273cb2cc33300a56873b2e4a0f3fe2e2d", "history.fetch_order_book_range",
              "NOT_IMPLEMENTED", "NOT_STARTED_OR_PROVIDER_BLOCKED"),
    "R3-09-BOOK_GAPS": ("Synpath-ai/synpath", "ab7c64b273cb2cc33300a56873b2e4a0f3fe2e2d", "iter_book_timeline; BookGap",
                        "NOT_IMPLEMENTED", "NOT_STARTED_OR_PROVIDER_BLOCKED"),
    "R3-03-FEES": ("YichengYang-Ethan/oracle3-prediction-market-agent", "267fb7c48dae7c4ff8922c02a3a223443e51bf0b",
                   "PolymarketSchedule.fee", "SELECTIVE_UPSTREAM_CODE_REUSE", "ENGINEERED_OFFLINE_NOT_OPERATIONALLY_ACCEPTED"),
    "R3-15": ("braedonsaunders/homerun", "6cb8ea5614e7a1b6f4c692a5b17436e888904092", "fill_calibration",
              "CONCEPT_ONLY", "PARTIAL_CONCEPT_UNACCEPTED"),
    "R3-16": ("ent0n29/polybot", "51e5362f026adf54162fc1256f453241d93680e6", "calibrate_maker_fill_model",
              "NOT_IMPLEMENTED", "NOT_STARTED_OR_PROVIDER_BLOCKED"),
    "R3-17": ("zachdaube/kalshi-market-maker", "212c957c2b63a1a775949f9e7562911fdc033f28", "quotes",
              "NOT_IMPLEMENTED", "NOT_STARTED_OR_PROVIDER_BLOCKED"),
    "R3-26": ("evan-kolberg/prediction-market-backtesting", "c76e77af00ef53472a9da8f66dae7fdd2d3e5928",
              "polymarket_pmxt_book_100_replay_runner", "CONCEPT_ONLY", "PARTIAL_CONCEPT_UNACCEPTED"),
}
LANE_B = ("R3-15", "R3-16", "R3-17", "R3-26")
AUTHORITY = {"advisory_only": True, "synthetic_test_only": True, "provider_calls": 0, "network_calls": 0,
             "llm_or_hermes_calls": 0, "orders": False, "paper": False, "paper_binding_created": False, "live": False,
             "strategy": False, "qualification": False, "oos_release": False, "credentials": False, "capital": False,
             "tradable": False, "executable_edge": False, "economics_supported": False, "fills_claimed": False,
             "profit_or_size_claim": False, "store_writes": False, "human_review_required": True}


class ExecutionEconomicsStop(Exception):
    """Closed refusal: the message is a stable code, never caller text."""


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise ExecutionEconomicsStop(code)


def _unique(items: list, missing: str, ambiguous: str):
    _require(bool(items), missing)
    _require(len(items) == 1, ambiguous)
    return items[0]


def validate_case(case: object) -> None:
    """Closed whole-case structure; native loaders validate every nested native mapping later."""
    _require(isinstance(case, dict) and set(case) == CASE_KEYS and case["schema_id"] == CASE_SCHEMA
             and case["evidence_class"] == EVIDENCE_CLASS, "CASE_FIELDS_INVALID")
    _require(type(case["b2_receipt_id"]) is str and B2_ID_RE.fullmatch(case["b2_receipt_id"]) is not None, "B2_RECEIPT_ID_INVALID")
    _require(type(case["model_id"]) is str and SG._QID_RE.fullmatch(case["model_id"]) is not None, "MODEL_ID_INVALID")
    _require(type(case["basket_id"]) is str and BASKET_RE.fullmatch(case["basket_id"]) is not None, "BASKET_ID_INVALID")
    _require(case["leg_side"] in (RE.YES, RE.NO) and type(case["leg_side"]) is str, "LEG_SIDE_INVALID")
    _require(type(case["strategy_version"]) is dict and type(case["probe_intent"]) is dict, "NATIVE_MAPPING_INVALID")
    replay = case["replay"]
    if replay is not None:
        _require(type(replay) is dict and set(replay) == REPLAY_KEYS and type(replay["parquet_sha256"]) is str
                 and HEX64_RE.fullmatch(replay["parquet_sha256"]) is not None
                 and all(type(replay[k]) is dict for k in REPLAY_KEYS - {"parquet_sha256", "known_gap_policy"}),
                 "REPLAY_FIELDS_INVALID")
        _require(type(replay["known_gap_policy"]) is str and replay["known_gap_policy"] in GAP_POLICIES, "GAP_POLICY_INVALID")
    RW._scan_secret_keys(case)


# ------------------------------------------------------------------ R001 exact B2 leg + native snapshot


def select_leg(b2_core: dict, case: dict) -> dict:
    """The exact admitted model/basket/target leg of the verified B2 core; never a substitute leg."""
    _require(b2_core.get("wp_id") == RW.WP_ID and b2_core.get("evidence_class") == RW.EVIDENCE_CLASS, "B2_EVIDENCE_CLASS_INVALID")
    target = b2_core["shared_case"]["target"]
    a5 = b2_core["a5_relations"]
    model = _unique([s for s in a5["selected"] if s["model_id"] == case["model_id"]], "MODEL_NOT_SELECTED_IN_B2",
                    "MODEL_AMBIGUOUS_IN_B2")
    _require(model["role"] == "ADMITTED", "MODEL_NOT_ADMITTED")
    _require(target["market_id"] in model["market_ids"], "MODEL_NOT_TARGET_RELATED")
    pointer = _unique([p for p in b2_core["a7_pointer"] if p["model_id"] == case["model_id"]], "A7_POINTER_MISSING",
                      "A7_POINTER_AMBIGUOUS")
    _require(pointer["conditional_only"] is True and pointer["tradable"] is False and pointer["executable_edge"] is False
             and pointer["rel_receipt_id"] == a5["rel_receipt_id"], "A7_POINTER_INVALID")
    basket = _unique([b for b in pointer["baskets"] if b["basket_id"] == case["basket_id"]], "BASKET_MISSING", "BASKET_AMBIGUOUS")
    leg = _unique([g for g in basket["legs"] if g["market_id"] == target["market_id"] and g["side"] == case["leg_side"]],
                  "TARGET_LEG_MISSING", "TARGET_LEG_AMBIGUOUS")
    _require(type(leg["venue_snapshot_id"]) is str, "TARGET_LEG_UNBOUND")
    return {"target": target, "model": model, "pointer": pointer, "basket": basket, "leg": leg}


def bind_snapshot(rel_dir, b2_core: dict, selected: dict, read_json, read_member) -> dict:
    """Rebuild the exact frozen REL snapshot with the native binder; identity, provenance and clock bound."""
    from tools.alpha import run_related_market_alpha as REL  # the native binder itself, not a re-implementation
    a5, target, leg = b2_core["a5_relations"], selected["target"], selected["leg"]
    rel = read_json(rel_dir / "receipt.json")
    request = read_json(rel_dir / "inputs" / "request.json")
    try:
        REL.validate_request(request, frozen=True)
    except Exception:  # noqa: BLE001 - native closed refusal, never echoed
        raise ExecutionEconomicsStop("REL_REQUEST_INVALID") from None
    _require(rel["receipt_id"] == a5["rel_receipt_id"], "REL_RECEIPT_MISMATCH")
    _require(rel["core"]["corpus_class"] == request["corpus_class"] == "SANITIZED_SYNTHETIC", "B2_NOT_SANITIZED_SYNTHETIC")
    _require(request["decision_time"] == rel["core"]["inputs"]["decision_time"] == a5["decision_time"], "DECISION_CLOCK_MISMATCH")
    grounding = SP.load_grounding(rel_dir / "inputs" / "grounding")
    shared = b2_core["shared_case"]
    _require(grounding["receipt_id"] == shared["grounding_receipt_id"]
             and grounding["universe"].alpha_universe_snapshot_id == shared["alpha_universe_snapshot_id"], "GROUNDING_MISMATCH")
    markets = {m.market_id: m for m in grounding["universe"].markets}
    allowed = {e[k] for e in request["venue"] for k in ("gamma_file", "clob_file")}
    found, failures, _ = REL._venue_snapshots(request["venue"], markets,
                                              lambda m: read_member(rel_dir / "inputs", m) if m in allowed else b"")
    key = (target["market_id"], leg["side"])
    _require(key not in failures, "SNAPSHOT_BINDING_REFUSED")
    snapshot = found.get(key)
    _require(snapshot is not None, "SNAPSHOT_NOT_BOUND")
    _require(snapshot.venue_snapshot_id == leg["venue_snapshot_id"], "SNAPSHOT_ID_MISMATCH")
    recorded = [o for o in rel["core"]["venue"]["entries"] if (o["market_id"], o["side"]) == key and o["status"] == "BOUND"]
    _require(len(recorded) == 1 and recorded[0]["venue_snapshot_id"] == snapshot.venue_snapshot_id, "REL_RECORD_MISMATCH")
    _require(snapshot.condition_id == markets[key[0]].condition_id == target["condition_id"], "CONDITION_MISMATCH")
    _require(TOKEN_PREFIX + snapshot.token_id in target["token_ids"], "TOKEN_MISMATCH")
    decision_ns = RE.utc_ns(request["decision_time"])
    _require(snapshot.acquisition_completed_ns <= decision_ns, "SNAPSHOT_ACQUIRED_AFTER_DECISION")
    # REL derives the side from the frozen Gamma outcome order; the PMXT context label must match it.
    return {"snapshot": snapshot, "decision_ns": decision_ns, "decision_time": request["decision_time"],
            "outcome_label": {RE.YES: "Yes", RE.NO: "No"}[leg["side"]], "rel_receipt_id": rel["receipt_id"]}


# ------------------------------------------------------------------ R002/R003 native point mechanics


def assess_point(case: dict, snapshot, decision_ns: int) -> tuple:
    """Native intent + snapshot -> native assessment at the REL clock; returns (intent, assessment, projection)."""
    try:
        version = SL.record_from_mapping("STRATEGY_VERSION", case["strategy_version"])
    except Exception:  # noqa: BLE001 - native closed refusal
        raise ExecutionEconomicsStop("STRATEGY_VERSION_INVALID") from None
    try:
        intent = EFM.validate_execution_intent(EFM.ExecutionIntent.from_mapping(case["probe_intent"]), strategy_version=version)
    except EFM.ExecutionFeasibilityError as error:
        raise ExecutionEconomicsStop("PROBE_INTENT_INVALID:" + error.code) from None
    except Exception:  # noqa: BLE001
        raise ExecutionEconomicsStop("PROBE_INTENT_INVALID") from None
    _require(intent.information_cutoff_ns == decision_ns, "PROBE_CUTOFF_NOT_DECISION_CLOCK")
    _require((intent.gamma_market_id, intent.condition_id, intent.token_id)
             == (snapshot.gamma_market_id, snapshot.condition_id, snapshot.token_id), "PROBE_IDENTITY_MISMATCH")
    _require(intent.side == "BUY", "PROBE_SIDE_NOT_BUY")  # buying the selected outcome leg; not an order
    try:
        assessment = EV.assess_execution_feasibility(intent, snapshot, evaluated_at_ns=decision_ns)
        EV.validate_execution_feasibility_assessment(assessment, intent=intent, venue_snapshot=snapshot)
        _require(EFM.record_from_mapping(assessment.RECORD_KIND, assessment.to_mapping()) == assessment, "POINT_ROUNDTRIP_FAILED")
    except EFM.ExecutionFeasibilityError as error:
        raise ExecutionEconomicsStop("POINT_NATIVE_REFUSED:" + error.code) from None
    m = assessment.to_mapping()
    projection = {
        "execution_feasibility_assessment_id": assessment.execution_feasibility_assessment_id,
        "execution_intent_id": intent.execution_intent_id, "venue_snapshot_id": snapshot.venue_snapshot_id,
        "strategy_version_id": intent.strategy_version_id, "execution_rule_sha256": intent.execution_rule_sha256,
        "evaluated_at_ns": assessment.evaluated_at_ns, "information_cutoff_ns": assessment.information_cutoff_ns,
        "status": assessment.status, "dimensions": {d: m[d] for d in EFM.DIMENSIONS},
        "probe": {"side": intent.side, "execution_style": intent.execution_style, "order_type": intent.order_type,
                  "post_only": intent.post_only, "fixture_assumption_only": True},
        "mechanics": {k: {"value": m[k], "unit": u} for k, u in UNITS.items()},
        "fee_exactness": m["fee_exactness"],
        "states": {k: m[k] for k in ("client_latency_state", "passive_fill_state", "adverse_selection_state")},
        "frozen_unknowns": {k: m[k] for k in FROZEN_UNKNOWNS},
        "diagnostic_codes": list(m["diagnostic_codes"]),
        "public_mechanics_only": True, "fill_claimed": False, "profit_claimed": False}
    return intent, assessment, projection


# ------------------------------------------------------------------ R004/R005 optional native replay + WP173 refusal


def _utc_ns(text: object) -> int:
    try:
        return RE.utc_ns(text)
    except (TypeError, ValueError):
        raise ExecutionEconomicsStop("WP170_CLOCK_INVALID") from None


def not_supplied() -> dict:
    return dict({k: None for k in REPLAY_FIELDS}, status="NOT_SUPPLIED")


def replay_diagnostic(replay: dict, parquet_path, bound: dict, intent, target_market_id: str) -> dict:
    """One explicit synthetic PMXT-format file -> native WP167/168/172 diagnostic -> native WP173 refusal."""
    from src.data_layer.analytical_research import experiment_os as EOS
    from src.data_layer.analytical_research import pmxt_v2 as PX
    from src.paper_trading.models import PaperTradingError, build_strategy_binding
    from src.research_runtime import executable_edge as EE
    from src.research_runtime.nautilus_offline import BinaryOptionMarketContext, PmxtV2ReplaySource, convert_pmxt_v2_events
    snapshot, decision_ns = bound["snapshot"], bound["decision_ns"]
    # cost model: exact native schema, rebuilt by the native builder and compared canonically (id and flags included)
    given = replay["cost_model"]
    _require(set(given) == {f.name for f in fields(EE.ExecutionCostModel)} and type(given["size_grid"]) is list, "COST_MODEL_FIELDS_INVALID")
    _require(given["fee_rate_bps"] is None, "COST_MODEL_FEE_BPS_NOT_PERMITTED")  # never a converted per-level native fee
    try:
        model = EE.build_execution_cost_model(**{k: given[k] for k in given if k not in (
            "schema_id", "schema_version", "cost_model_id", "advisory_only", "no_execution_authority")})
        EE.validate_execution_cost_model(model)
    except (EE.ExecutableEdgeError, TypeError):
        raise ExecutionEconomicsStop("COST_MODEL_INVALID") from None
    _require(SG.canonical_bytes(dict(asdict(model), size_grid=list(model.size_grid))) == SG.canonical_bytes(given), "COST_MODEL_MISMATCH")
    _require(model.execution_mode == intent.execution_style, "COST_MODEL_MODE_MISMATCH")
    # WP170 fixture records: native loaders; non-OOS, no first look, every duplicated lineage field equal
    try:
        experiment = EOS.record_from_mapping(EOS.PreregisteredExperiment, replay["experiment"])
        evidence = EOS.record_from_mapping(EOS.RunEvidenceReceipt, replay["evidence"])
    except Exception:  # noqa: BLE001 - native closed refusal
        raise ExecutionEconomicsStop("WP170_RECORD_INVALID") from None
    _require(evidence.evaluated_role in EOS.RESEARCH_ROLES and evidence.evaluated_role != "OUT_OF_SAMPLE"
             and evidence.oos_exposure_ordinal == 0 and not EE.authoritative_first_look(experiment, evidence), "WP170_OOS_REFUSED")
    _require(evidence.experiment_id == experiment.experiment_id
             and all(getattr(evidence, k) == getattr(experiment, k) for k in WP170_LINEAGE), "WP170_LINEAGE_MISMATCH")
    _require(experiment.cost_model_reference == model.cost_model_id, "COST_MODEL_REFERENCE_MISMATCH")
    _require(_utc_ns(experiment.preregistered_at) <= decision_ns and _utc_ns(evidence.created_at) <= decision_ns,
             "WP170_RECORD_AFTER_DECISION")
    # decision event: explicit B3 binding to the exact snapshot leg and clock (no native alias)
    given = replay["decision_event"]
    _require(set(given) == {f.name for f in fields(EE.ResearchDecisionEvent)}, "DECISION_EVENT_FIELDS_INVALID")
    event = EE.ResearchDecisionEvent(**given)
    try:
        same_shares = Decimal(event.intended_quantity) == Decimal(intent.requested_shares)
    except (InvalidOperation, TypeError):
        same_shares = False
    _require(event.market_id == target_market_id and event.asset_id == TOKEN_PREFIX + snapshot.token_id
             and (event.side, event.action) == ("BUY", "ENTER") and type(event.decision_time_ns) is int
             and event.decision_time_ns == decision_ns and same_shares, "DECISION_EVENT_BINDING_MISMATCH")
    # context: exact selected condition/token/Gamma orientation; native mapping validates the rest
    given = replay["context"]
    _require(set(given) == {f.name for f in fields(BinaryOptionMarketContext)}, "REPLAY_CONTEXT_FIELDS_INVALID")
    context = BinaryOptionMarketContext(**given)
    _require((context.condition_id, context.outcome_token_id, context.outcome_label)
             == (snapshot.condition_id, snapshot.token_id, bound["outcome_label"]), "REPLAY_CONTEXT_IDENTITY_MISMATCH")
    # WP167 describe with fixed synthetic labels and the caller's gap policy; caller digest alone is never trusted
    source_file = PX.PmxtV2SourceFile(path=str(parquet_path), object_name=PMXT_FIXTURE["object_name"],
                                      partition_identity=PMXT_FIXTURE["partition_identity"])
    described = PX.validate_and_describe_pmxt_v2_archive(
        [source_file], quality_tier=PMXT_FIXTURE["quality_tier"], known_gap_policy=replay["known_gap_policy"],
        license_id=PMXT_FIXTURE["license_id"], attribution=PMXT_FIXTURE["attribution"])
    _require(described.is_valid, "REPLAY_SOURCE_REFUSED")
    descriptor = described.descriptor
    _require(len(descriptor.source_objects) == 1 and descriptor.source_objects[0].source_sha256 == replay["parquet_sha256"],
             "REPLAY_SHA256_MISMATCH")
    _require(0 < described.total_row_count <= MAX_REPLAY_ROWS, "REPLAY_ROWS_OUT_OF_BOUNDS")
    source = PmxtV2ReplaySource(descriptor=descriptor, source_files=(source_file,))
    stream = convert_pmxt_v2_events(source, context)
    _require(stream.is_valid, "REPLAY_ROWS_REFUSED")  # a foreign condition/token row refuses the whole file
    _require(sum(n for _, n in stream.input_event_counts_by_type) == described.total_row_count, "REPLAY_ROW_DENOMINATOR_MISMATCH")
    try:
        window = EE.build_market_truth_window(source, context)
        EE.validate_any_market_truth_window(window)
        trace = EE.build_research_decision_trace(experiment, evidence, (event,))
        assessed = EE.assess_executable_edge(experiment, evidence, trace, model, window)
        restored = EE.deserialize_assessment(EE.serialize_assessment(assessed))  # in memory only
    except EE.ExecutableEdgeError as error:
        raise ExecutionEconomicsStop("REPLAY_NATIVE_REFUSED:" + str(error).split(":")[0]) from None
    _require(restored == assessed, "REPLAY_SERIALIZATION_MISMATCH")
    _require(window.continuity_complete is False and window.known_gap_policy == replay["known_gap_policy"], "REPLAY_CONTINUITY_CLAIMED")
    _require(restored.status == "DIAGNOSTIC_ONLY" and not restored.wp173_evaluation_eligible
             and "MARKET_DATA_CONTINUITY_INCOMPLETE" in restored.diagnostic_codes, "REPLAY_UNEXPECTED_ELIGIBILITY")
    try:
        build_strategy_binding(restored, model, strategy_label=PAPER_LABEL, created_time_ns=decision_ns)
    except PaperTradingError as error:
        _require(str(error) == "WP172_BINDING_INVALID", "PAPER_REFUSAL_UNEXPECTED")
    else:
        raise ExecutionEconomicsStop("PAPER_ADMISSION_NOT_REFUSED")
    return {
        "status": "DIAGNOSTIC_ONLY_NATIVE", "origin": "SYNTHETIC_PMXT_FORMAT",
        "source": {"parquet_sha256": descriptor.source_objects[0].source_sha256, "external_dataset_id": descriptor.external_dataset_id,
                   "quality_tier": descriptor.quality_tier, "license_id": descriptor.license_id,
                   "known_gap_policy": descriptor.known_gap_policy, "row_count": described.total_row_count,
                   "input_event_counts": dict(stream.input_event_counts_by_type), "coverage_start": described.coverage_start,
                   "coverage_end": described.coverage_end, "provider_history": False, "synpath_invoked": False},
        "window": {"lineage_id": window.lineage_id, "instrument_id": window.instrument_id,
                   "conversion_policy_version": window.conversion_policy_version, "known_gap_policy": window.known_gap_policy,
                   "continuity_complete": window.continuity_complete, "event_count": len(window.events),
                   "event_kind_counts": dict(sorted(Counter(e.kind for e in window.events).items())),
                   "first_receive_time_ns": window.first_receive_time_ns, "last_receive_time_ns": window.last_receive_time_ns,
                   "receive_time_primary": True, "interpolated": False},
        "wp170": {"experiment_id": experiment.experiment_id, "run_evidence_receipt_id": evidence.run_evidence_receipt_id,
                  "evaluated_role": evidence.evaluated_role, "oos_exposure_ordinal": evidence.oos_exposure_ordinal,
                  "authoritative_first_look": False, "fixture_assumption_only": True, "registry_writes": 0},
        "cost_model_id": model.cost_model_id, "trace_id": trace.trace_id,
        "assessment": {"assessment_id": restored.assessment_id, "status": restored.status,
                       "wp173_evaluation_eligible": restored.wp173_evaluation_eligible,
                       "diagnostic_codes": list(restored.diagnostic_codes), "assumptions": list(restored.assumptions),
                       "fee_cost_known": restored.fee_cost is not None, "intended_quantity": restored.intended_quantity,
                       "fill_ratio": restored.fill_ratio, "markout_retrospective_fixture_only": True,
                       "serialization_round_trip": True},
        "wp173": {"attempted": True, "refusal_code": "WP172_BINDING_INVALID", "binding_created": False}}


# ------------------------------------------------------------------ R006/R011/R012 role, ledger, receipt


def a7_role(point: dict, replay: dict, selected: dict) -> dict:
    supplied = replay["status"] != "NOT_SUPPLIED"
    reasons = ["POINT_MECHANICS_" + point["status"], "REPLAY_" + ("DIAGNOSTIC_ONLY_CONTINUITY_INCOMPLETE" if supplied else "NOT_SUPPLIED"),
               "WP173_ADMISSION_REFUSED" if supplied else "WP173_NOT_ATTEMPTED_NO_REPLAY", "LANE_B_NO_ACCEPTED_ARTIFACT",
               "SYNPATH_PROVIDER_BLOCKED", "FEE_CURRENTNESS_UNVERIFIED", "B2_ATOMICITY_" + selected["basket"]["atomicity"]]
    reasons += ["POINT_DIMENSION_" + v + ":" + k for k, v in sorted(point["dimensions"].items()) if v not in ("PASS", "NOT_APPLICABLE")]
    return {"role": "A7_EXECUTION_ECONOMICS", "overall": "REFUSED" if point["status"] == "NOT_FEASIBLE" else "PARTIAL",
            "point_mechanics_status": point["status"], "replay_status": replay["status"], "reasons": reasons,
            "economics_supported": False, "conditional_only": True, "b4_handoff": "READ_ONLY_TYPED_RECEIPT",
            "denominators": {"requested_cases": 1, "selected_legs": 1, "point_evaluated": 1,
                             "point_refused": int(point["status"] == "NOT_FEASIBLE"), "replay_attempted": int(supplied),
                             "replay_evaluated": int(supplied), "paper_admission_refused": int(supplied),
                             "terminal_dispositions": 1}}


def capability_ledger(b2_core: dict, point: dict, replay: dict) -> dict:
    supplied = replay["status"] != "NOT_SUPPLIED"
    b2_fee = b2_core["capability"]["touched"]["R3-03-FEES"]["status"]
    synpath = {"status": "PROVIDER_BLOCKED_OPEN", "call": "NOT_INVOKED",
               "blockers": ["OWNER_RIGHTS_W07", "ACTUAL_PROVIDER_COVERAGE_WITNESS_ABSENT"],
               "native_consumer_evidence": "WP167_168_172_SYNTHETIC_KNOWN_GAP_DIAGNOSTIC" if supplied else "NOT_EXERCISED",
               "native_is_not_upstream_invocation": True}
    rows = {"R3-09": dict(synpath), "R3-09-BOOK_GAPS": dict(synpath),
            "R3-03-FEES": {"status": "B2_FIXTURE_FEE_CONSUMED_NATIVE_POINT_FEE_CURRENTNESS_UNVERIFIED"
                           if b2_fee == "FIXTURE_FEE_SCHEDULE_INVOKED_CURRENTNESS_UNVERIFIED" else "NOT_EXERCISED_ON_SHARED_CASE",
                           "call": "NO_NEW_ORACLE3_INVOCATION_B2_COLD_VERIFY_ONLY", "b2_status": b2_fee,
                           "native_consumer_evidence": "EXECUTION_FEASIBILITY_FEE_" + point["fee_exactness"],
                           "blockers": ["CURRENT_VENUE_FEE_SCHEDULE_UNVERIFIED"]}}
    for key in LANE_B:
        rows[key] = {"status": "NO_ACCEPTED_ARTIFACT_OBSERVED", "call": "NOT_INVOKED", "owner": "LANE_B_SEPARATE",
                     "native_consumer_evidence": "NONE_NO_CALIBRATION_CREDIT",
                     "blockers": ["SEPARATELY_REVIEWED_EXACT_LANE_B_ARTIFACT_ABSENT", "OWNER_PERMISSION_REQUIRED"]}
    for key, row in rows.items():
        repo, commit, method, implementation, plan = PINS[key]
        row.update(repository=repo, commit=commit, method=method, original_implementation_class=implementation,
                   original_status_at_plan=plan, value_verified=False, owner_disposition="PENDING")
    return {"touched": rows, "other_29_capability_ids": "UNCHANGED", "w06": "PARTIAL_NATIVE_ENGINEERING_ONLY",
            "w07_synpath_rights": "OPEN", "lane_b": "SEPARATELY_OWNED_NO_TAKEOVER"}


def b2_lineage(b2_receipt_id: str, b2_core: dict, selected: dict, bound: dict) -> dict:
    lineage, a5, a6 = b2_core["b1a_lineage"], b2_core["a5_relations"], b2_core["a6_wallet"]
    return {"b2_receipt_id": b2_receipt_id, "b2_code_identity": b2_core["code_identity"],
            "b1a": {k: lineage[k] for k in ("spine_receipt_id", "grounding_receipt_id", "alpha_universe_snapshot_id", "as_of")},
            "target": selected["target"], "decision_time": bound["decision_time"],
            "a5": {k: a5[k] for k in ("status", "rel_receipt_id", "parity_receipt_id", "rel_code_identity", "denominators")},
            "a6": {"status": a6["status"], "cohort_snapshot_id": a6["cohort_snapshot_id"],
                   "profile_id": (a6.get("profile") or {}).get("wallet_profile_snapshot_id"),
                   "assessment_id": (a6.get("assessment") or {}).get("wallet_copyability_research_assessment_id")},
            "selected": {"model_id": selected["model"]["model_id"], "basket_id": selected["basket"]["basket_id"],
                         "basket_status": selected["basket"]["status"], "atomicity": selected["basket"]["atomicity"],
                         "leg": selected["leg"], "native_economic_status": selected["pointer"]["native_economic_status"],
                         "conditional_only": True, "tradable": False, "executable_edge": False},
            "venue_snapshot_id": bound["snapshot"].venue_snapshot_id, "rel_receipt_id": bound["rel_receipt_id"]}


def build_core(*, code_identity: str, input_sha256: dict, lineage: dict, point: dict, replay: dict, role: dict,
               ledger: dict) -> dict:
    trace = ["B2 cold verify", "A5 admitted model + A7 pointer leg", "REL native _venue_snapshots", "execution_feasibility assess"]
    if replay["status"] != "NOT_SUPPLIED":
        trace += ["WP167 describe", "WP168/172 market truth", "WP172 assess_executable_edge", "WP173 binding refusal"]
    return json.loads(SG.canonical_bytes({
        "schema_id": RECEIPT_SCHEMA, "wp_id": WP_ID, "evidence_class": EVIDENCE_CLASS, "code_identity": code_identity,
        "input_sha256": input_sha256, "b2_lineage": lineage, "point_mechanics": point, "replay_diagnostic": replay,
        "a7_role": role, "capability_ledger": ledger, "authority": AUTHORITY, "trace": trace}))


def finalize(core: dict) -> dict:
    return {"schema_id": RECEIPT_SCHEMA, "receipt_id": RECEIPT_PREFIX + RW.sha_json(core), "core": core}
