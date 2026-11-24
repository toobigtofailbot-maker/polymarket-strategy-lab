"""B2 shared-PIT relation (A5) + public-wallet (A6) advisory handoff (S10-CAP-B2-RELATIONS-WALLET-01).

A thin, deterministic, offline consumer over EXISTING verified native producers. It mints no market, rule,
relation, wallet, profile, fee or Alpha identity and is not a canonical store:

* ``bind_target``: the cold-verified B1-A spine's frozen SRC-01 grounding -> native ``source_forecast_spine``
  ``load_grounding`` + ``scout`` -> the exact target (market/event/condition/tokens/question/rule/candidate),
  universe and ``as_of``, cross-checked against the B1-A receipt's own A1 target by native ID only.
* ``relations``: a cold-verified REL-01 receipt and the Oracle3 parity receipt generated from it -> only the
  caller's predeclared model IDs; each must be unique in REL, must contain the target and must carry the exact
  grounding-bound rule SHA for every member market. Native formal / real-world / economics outcomes and the
  genuine ``check_constraint`` parity are copied, never re-derived; the A7 pointer is read-side only.
* ``wallet``: native WALLET-01 ``load_and_verify_wallet_evidence_ledger`` at the exact expected head ->
  native WALLET-02 mapping loaders + ``build_wallet_profile_snapshot`` -> native WALLET-03
  ``build_wallet_copyability_research_assessment`` and its mapping round trip. Every market context must
  resolve by exact condition and token to the same PIT universe with the exact PIT metadata clock.

Evidence class OFFLINE_ENGINEERING_DEMONSTRATION: conditional relation economics are not executable, a
delayed public quote is not a fill, a public address is not a person, and nothing here is a signal, rank,
recommendation, order, size or value claim.
"""
from __future__ import annotations

from collections import Counter
import json
import re

from src.data_layer.analytical_research import public_market_contract_parity as PMC
from src.data_layer.analytical_research import source_forecast_spine as SP
from src.data_layer.analytical_research import source_grounding as SG
from src.data_layer.point_in_time_market_research.research_provenance import (
    RawEvidenceReference, build_pit_timestamps, build_raw_evidence_reference)
from src.data_layer.wallet_intelligence import copyability as WC
from src.data_layer.wallet_intelligence import ledger as WL
from src.data_layer.wallet_intelligence import profile as WP

WP_ID = "S10-CAP-B2-RELATIONS-WALLET-01"
CASE_SCHEMA = "s10-cap-b2-relation-wallet-case-v1"
RECEIPT_SCHEMA = "s10-cap-b2-relation-wallet-receipt-v1"
RECEIPT_PREFIX = "b2research:sha256:"
EVIDENCE_CLASS = "OFFLINE_ENGINEERING_DEMONSTRATION"
CASE_KEYS = {"schema_id", "spine_receipt_id", "rel_receipt_id", "target_market_id", "model_ids",
             "expected_wallet_ledger_head", "target_wallet", "wallet_as_of", "cohort", "market_contexts",
             "identity_observability", "quote_witnesses", "delay_seconds", "cost_scenarios"}
QUOTE_KEYS = {"condition_context", "condition_value", "token_context", "token_value", "price_direction_sign", "price",
              "top_level_depth_shares", "observability", "dq_flags", "replay_fidelity", "raw_evidence_reference_id",
              "research_provenance_manifest_id", "raw_content_member"}
COST_KEYS = {"taker_fee_per_share", "slippage_per_share", "transaction_cost_per_share", "required_depth_shares"}
REGISTERED_KEYS = ("raw_evidence_reference_id", "research_provenance_manifest_id", "raw_content_member")
MAX_MODELS = 200
MAX_CONTEXTS = 64
MAX_QUOTES = 64
MAX_MEMBER_BYTES = 65536
MEMBER_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}(/[A-Za-z0-9][A-Za-z0-9._-]{0,63}){0,3}")
SPINE_ID_RE = re.compile(r"b1spine:sha256:[0-9a-f]{64}")
REL_ID_RE = re.compile(r"relmarket:sha256:[0-9a-f]{64}")
HEX64_RE = re.compile(r"[0-9a-f]{64}")
WALLET_RE = re.compile(r"0x[0-9a-fA-F]{40}")
TOKEN_PREFIX = "token:polymarket:"

# Six W04/W05 IDs; the frozen 36-row CSV is never edited. Status is computed from the actual receipt below.
PINS = {
    "R3-03": ("YichengYang-Ethan/oracle3-prediction-market-agent", "267fb7c48dae7c4ff8922c02a3a223443e51bf0b",
              "oracle3/arbitrage.py check_constraint (vendored blob 4805d57)", "Apache-2.0"),
    "R3-03-FEES": ("YichengYang-Ethan/oracle3-prediction-market-agent", "267fb7c48dae7c4ff8922c02a3a223443e51bf0b",
                   "oracle3/fees.py PolymarketSchedule (vendored blob 24624f8)", "Apache-2.0"),
    "R3-04": ("YichengYang-Ethan/oracle3-extras", "b2d807a0513f37212623ecd3a9127af3ad506658",
              "oracle3_extras/market/kairos/settlement.py (blob acb2de2)", "Apache-2.0"),
    "R3-11": ("chainstacklabs/polymarket-alpha-bot", "1f4f366b9c677574c8034a8720eaca917a53715b",
              "backend/core/steps/implications.py (blob 27150d1)", "Apache-2.0"),
    "R3-19": ("Synpath-ai/prediction-market-arbitrage-trading-bot", "c906cb36956945a291cb32a2d60a7455a0103a8f",
              "src/matcher.py (blob 24de654)", "MIT"),
    "R3-14": ("Jon-Becker/prediction-market-analysis", "2d69f7330fdee142d2cf75d901841f9174fdbbd2",
              "docs/SCHEMAS.md (blob ba241fe) + indexers", "MIT code; dataset rights unstated"),
}
OPEN_CAUSES = {
    "R3-04": "IMPORT_CLOSURE_NEEDS_UNVENDORED_ORACLE3_MARKET_RELATIONS_AND_KAIROS_PROVIDER_CLIENT",
    "R3-11": "IMPORT_CLOSURE_NEEDS_LLM_CLIENT_AND_LOGURU_NO_COPY_AUTHORITY_DERIVE_COVERS_CONSUMES_LLM_OUTPUT",
    "R3-19": "RESOLVE_NEEDS_SYNPATH_SDK_AND_NETWORK_CATALOG_PROVIDER_RIGHTS_SEPARATE",
    "R3-14": "OPEN_OWNER_RIGHTS_36GIB_EXTERNAL_DATASET_NO_DATA_LICENSE_CONTAINS_PUBLIC_ADDRESSES_NOT_DOWNLOADED",
}
AUTHORITY = {"advisory_only": True, "provider_calls": 0, "network_calls": 0, "llm_or_hermes_calls": 0, "orders": False,
             "paper": False, "live": False, "strategy": False, "qualification": False, "credentials": False,
             "capital": False, "tradable": False, "executable_edge": False, "copy_recommendation": False,
             "person_inference": False, "store_writes": False, "human_review_required": True}


class RelationWalletStop(Exception):
    """Closed refusal: the message is a stable code, never caller text."""


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise RelationWalletStop(code)


def sha_json(value: object) -> str:
    return SG.sha256_hex(SG.canonical_bytes(value))


def _utc(value: object) -> bool:
    return type(value) is str and len(value) == 20 and value.endswith("Z") and SG.RP.canonicalize_utc_timestamp(value) == value


def validate_case(case: object) -> None:
    """Closed whole-case structure; native loaders validate the nested native mappings later."""
    _require(isinstance(case, dict) and set(case) == CASE_KEYS and case["schema_id"] == CASE_SCHEMA, "CASE_FIELDS_INVALID")
    _require(type(case["spine_receipt_id"]) is str and SPINE_ID_RE.fullmatch(case["spine_receipt_id"]) is not None
             and type(case["rel_receipt_id"]) is str and REL_ID_RE.fullmatch(case["rel_receipt_id"]) is not None,
             "UPSTREAM_RECEIPT_ID_INVALID")
    _require(type(case["target_market_id"]) is str and PMC.MARKET_RE.fullmatch(case["target_market_id"]) is not None,
             "TARGET_MARKET_ID_NONCANONICAL")
    ids = case["model_ids"]
    _require(type(ids) is list and 0 < len(ids) <= MAX_MODELS and all(type(m) is str and SG._QID_RE.fullmatch(m) for m in ids),
             "MODEL_IDS_INVALID")
    _require(len(set(ids)) == len(ids), "MODEL_IDS_DUPLICATE")
    _require(type(case["expected_wallet_ledger_head"]) is str and HEX64_RE.fullmatch(case["expected_wallet_ledger_head"]),
             "WALLET_HEAD_INVALID")
    _require(type(case["target_wallet"]) is str and WALLET_RE.fullmatch(case["target_wallet"]) is not None, "TARGET_WALLET_INVALID")
    try:
        _require(_utc(case["wallet_as_of"]), "WALLET_AS_OF_INVALID")
    except ValueError:
        raise RelationWalletStop("WALLET_AS_OF_INVALID") from None
    _require(isinstance(case["cohort"], dict), "COHORT_INVALID")
    contexts = case["market_contexts"]
    _require(type(contexts) is list and 0 < len(contexts) <= MAX_CONTEXTS and all(isinstance(c, dict) for c in contexts),
             "MARKET_CONTEXTS_INVALID")
    _require(case["identity_observability"] is None or (isinstance(case["identity_observability"], dict)
                                                        and all(isinstance(v, dict) for v in case["identity_observability"].values())),
             "IDENTITY_OBSERVABILITY_INVALID")
    quotes = case["quote_witnesses"]
    _require(type(quotes) is list and len(quotes) <= MAX_QUOTES and all(isinstance(q, dict) and set(q) == QUOTE_KEYS for q in quotes),
             "QUOTE_WITNESSES_INVALID")
    for q in quotes:
        registered = [q[k] is not None for k in REGISTERED_KEYS]
        _require(all(registered) or not any(registered), "QUOTE_REGISTRATION_PARTIAL")  # retained bytes all-or-nothing
        _require(q["raw_content_member"] is None or (type(q["raw_content_member"]) is str
                                                     and MEMBER_RE.fullmatch(q["raw_content_member"]) is not None
                                                     and ".." not in q["raw_content_member"].split("/")), "QUOTE_MEMBER_INVALID")
        _require(type(q["price_direction_sign"]) is int and type(q["price"]) is str, "QUOTE_WITNESSES_INVALID")
    _require(type(case["delay_seconds"]) is list and all(type(d) is str for d in case["delay_seconds"]), "DELAY_SECONDS_INVALID")
    costs = case["cost_scenarios"]
    _require(type(costs) is list and 0 < len(costs) <= 16 and all(
        isinstance(c, dict) and set(c) == COST_KEYS and all(v is None or type(v) is str for v in c.values()) for c in costs),
        "COST_SCENARIOS_INVALID")
    _scan_secret_keys(case)


# Native WALLET-02/03 closed field names legitimately contain "wallet"/"price"/"side"; every nested mapping is
# closed-key strict in its native loader, so this is defense in depth against credential-shaped keys only.
_SECRET_PARTS = tuple(p for p in SG.SECRET_KEY_PARTS if p != "wallet")


def _scan_secret_keys(value: object, depth: int = 0) -> None:
    _require(depth <= 8, "CASE_TOO_DEEP")
    if isinstance(value, dict):
        for key, item in value.items():
            _require(type(key) is str and not any(p in key.casefold() for p in _SECRET_PARTS), "FORBIDDEN_FIELD")
            _scan_secret_keys(item, depth + 1)
    elif isinstance(value, list):
        for item in value:
            _scan_secret_keys(item, depth + 1)


def members(case: dict) -> list[str]:
    return sorted({q["raw_content_member"] for q in case["quote_witnesses"] if q["raw_content_member"] is not None})


# ------------------------------------------------------------------ B1-A target binding (A1-A4 lineage, read-only)


def b1a_lineage(spine_receipt: dict) -> dict:
    core = spine_receipt["core"]
    w01, forecast = core["w01"], core["forecast_diagnostic"]
    return {"spine_receipt_id": spine_receipt["receipt_id"], "spine_code_identity": core["code_identity"],
            "a1_target": core["a1_scout"]["target"], "grounding_receipt_id": core["a1_scout"]["grounding_receipt_id"],
            "alpha_universe_snapshot_id": core["a1_scout"]["alpha_universe_snapshot_id"], "as_of": core["a1_scout"]["as_of"],
            "a2_source_allowlist": core["a2_research"]["source_allowlist"],
            "a2_raw_evidence_reference_ids": core["a2_research"]["raw_evidence_reference_ids"],
            "forecast_receipt_id": forecast["receipt_id"], "forecast_case_id": forecast["case_id"],
            "a3_a4": {"w01_receipt_id": w01["receipt_id"], "witness_id": w01["witness_id"], "episode_id": w01["episode_id"],
                      "append_status": w01["append_status"], "cooperation_outcome": w01["cooperation_outcome"],
                      "children": w01["children"], "provider_invocations": w01["provider_invocations"]}}


def bind_target(grounding_dir, target_market_id: str, lineage: dict | None) -> dict:
    """Native scout over the frozen SRC-01 grounding; compared to the B1-A receipt by native IDs only."""
    grounding = SP.load_grounding(grounding_dir)
    scouted = SP.scout(grounding, target_market_id)
    _require(scouted["status"] == "ADMITTED", "TARGET_NOT_ADMITTED:" + str(scouted["reason"]))
    if lineage is not None:
        _require(scouted["grounding_receipt_id"] == lineage["grounding_receipt_id"]
                 and scouted["alpha_universe_snapshot_id"] == lineage["alpha_universe_snapshot_id"]
                 and scouted["as_of"] == lineage["as_of"], "SPINE_GROUNDING_MISMATCH")
        _require(scouted["target"] == lineage["a1_target"], "SPINE_TARGET_MISMATCH")
    markets = {m.market_id: m for m in grounding["universe"].markets}
    by_condition = Counter(m.condition_id for m in markets.values() if m.condition_id)
    return {"grounding_receipt_id": scouted["grounding_receipt_id"],
            "alpha_universe_snapshot_id": scouted["alpha_universe_snapshot_id"], "as_of": scouted["as_of"],
            "target": scouted["target"], "scout_denominators": scouted["denominators"],
            "rules": {k: v["rule_content_sha256"] for k, v in grounding["rules"].items()},
            "markets": {k: {"condition_id": m.condition_id, "token_ids": list(m.token_ids),
                            "metadata_observed_time": m.metadata_observed_time,
                            "condition_unique": by_condition.get(m.condition_id, 0) == 1} for k, m in markets.items()}}


# ------------------------------------------------------------------ A5 relations + Oracle3 + A7 pointer


def _leg(leg: dict) -> dict:
    return {"market_id": leg["market_id"], "side": leg["side"], "status": leg["status"], "reasons": leg.get("reasons", []),
            "fee_exactness": leg["fee_exactness"], "fee_known": leg["fee_bound_usd"] is not None,
            "depth_known": leg["visible_ask_depth"] is not None, "venue_snapshot_id": leg["venue_snapshot_id"]}


def relations(binding: dict, rel: dict, parity: dict, model_ids: list) -> dict:
    """Selected native REL-01 rows + their genuine Oracle3 parity cases; full native denominators retained."""
    rel_core, par_core = rel["core"], parity["core"]
    _require(rel_core["inputs"]["grounding_receipt_id"] == binding["grounding_receipt_id"], "REL_GROUNDING_MISMATCH")
    _require(rel_core["inputs"]["alpha_universe_snapshot_id"] == binding["alpha_universe_snapshot_id"]
             and rel_core["inputs"]["as_of"] == binding["as_of"], "REL_UNIVERSE_MISMATCH")
    _require(rel_core["inputs"]["decision_time"] >= binding["as_of"], "REL_DECISION_BEFORE_AS_OF")
    _require(par_core["inputs"]["rel_receipt_id"] == rel["receipt_id"], "PARITY_REL_MISMATCH")
    counts = Counter(r["model_id"] for r in rel_core["results"])
    parity_counts = Counter(c["model_id"] for c in par_core["results"])
    target = binding["target"]["market_id"]
    selected, rejected, pointer = [], [], []
    for model_id in model_ids:
        _require(counts[model_id] == 1 and parity_counts[model_id] == 1, "MODEL_ID_NOT_UNIQUE_IN_REL")
        row = next(r for r in rel_core["results"] if r["model_id"] == model_id)
        case = next(c for c in par_core["results"] if c["model_id"] == model_id)
        if target not in row["market_ids"]:
            rejected.append({"model_id": model_id, "reason": "MODEL_NOT_TARGET_RELATED"})
            continue
        if row["status"] != "EVALUATED":
            rejected.append({"model_id": model_id, "reason": "NATIVE_NOT_EVALUATED:" + row["status"],
                             "native_disposition": row["disposition"]})
            continue
        # every member market must carry the exact rule version the shared grounding bound (no foreign corpus)
        _require([r["market_id"] for r in row["rules"]] == row["market_ids"]
                 and all(binding["rules"].get(r["market_id"]) == r["rule_content_sha256"] for r in row["rules"]),
                 "RULE_IDENTITY_MISMATCH")
        admitted = row["disposition"] == "FORMAL_VALID" and case["verdict"] == "UPSTREAM_CONDITIONAL_EVALUATED"
        if admitted:
            reason = None
        elif row["disposition"] != "FORMAL_VALID":
            reason = row["disposition"]
        else:
            reason = "ORACLE3_" + case["verdict"] + ":" + str(case["reason"])
        selected.append({
            "model_id": model_id, "relation": row["relation"], "market_ids": list(row["market_ids"]),
            "target_position": row["market_ids"].index(target), "native_candidate_key": row["native_candidate_key"],
            "native_generators": row["native_generators"],
            "formal": {k: row["formal"][k] for k in ("status", "trust", "counterexamples", "special_states")},
            "real_world": {"status": row["real_world"]["status"], "reasons": row["real_world"]["reasons"]},
            "disposition": row["disposition"], "expected": row["expected"],
            "oracle3": {"verdict": case["verdict"], "reason": case["reason"],
                        "parity": [p["parity"] for p in case["parity"]],
                        "schedules": None if case["upstream"] is None else case["upstream"]["schedules"],
                        "violated": None if case["upstream"] is None else case["upstream"]["violated"],
                        "assessment": None if case["upstream"] is None else case["upstream"]["assessment"]},
            "role": "ADMITTED" if admitted else "REFUSED", "reason": reason})
        pointer.append({"rel_receipt_id": rel["receipt_id"], "model_id": model_id,
                        "native_economic_status": row["economics"]["status"], "native_economic_reason": row["economics"]["reason"],
                        "baskets": [{"basket_id": b["basket_id"], "sides": b["sides"], "status": b["status"],
                                     "reasons": b.get("reasons", []), "atomicity": b["atomicity"],
                                     "legs": [_leg(leg) for leg in b["legs"]]} for b in row["economics"]["baskets"]],
                        "tradable": False, "executable_edge": False, "conditional_only": True})
    admitted = [s for s in selected if s["role"] == "ADMITTED"]
    if admitted:
        status, reason = "ADMITTED", None
    elif selected:
        status, reason = "REFUSED", "NO_SELECTED_MODEL_ADMITTED"
    else:
        status, reason = "INSUFFICIENT", "NO_TARGET_MODEL_SELECTED"
    return {"status": status, "reason": reason,
            "rel_receipt_id": rel["receipt_id"], "rel_code_identity": rel_core["code_identity"],
            "parity_receipt_id": parity["receipt_id"], "parity_code_identity": par_core["code_identity"],
            "decision_time": rel_core["inputs"]["decision_time"], "fee_policy_id": rel_core["fee_policy"].get("policy_id"),
            "upstream": {"repository": par_core["upstream"]["repository"], "commit": par_core["upstream"]["commit"],
                         "invoked": par_core["upstream"]["invoked"]},
            "denominators": {"rel_results_total": len(rel_core["results"]), "rel_disposition_counts": rel_core["benchmark"]["disposition_counts"],
                             "parity_counts": par_core["counts"], "check_constraint_invocations": par_core["check_constraint_invocations"],
                             "requested": len(model_ids), "selected": len(selected), "rejected": len(rejected),
                             "admitted": len(admitted), "refused": len(selected) - len(admitted)},
            "selected": selected, "rejected": rejected, "a7_pointer": pointer}


# ------------------------------------------------------------------ A6 wallet profile + copyability


def _raw_reference(payload: dict) -> RawEvidenceReference:
    preimage = {k: v for k, v in payload.items() if k not in ("record_kind", "schema_id", "schema_version", "raw_evidence_reference_id")}
    preimage["pit"] = build_pit_timestamps(**preimage["pit"])
    built = build_raw_evidence_reference(**preimage)
    _require(built.raw_evidence_reference_id == payload["raw_evidence_reference_id"], "QUOTE_REFERENCE_IDENTITY_MISMATCH")
    return built


def _witness(q: dict, grouped: dict, read_member) -> WC.WalletCopyabilityQuoteWitness:
    raw = manifest = content = None
    if q["raw_evidence_reference_id"] is not None:
        raw_payload = grouped.get("RAW_EVIDENCE_REFERENCE", {}).get(q["raw_evidence_reference_id"])
        manifest_payload = grouped.get("RESEARCH_PROVENANCE_MANIFEST", {}).get(q["research_provenance_manifest_id"])
        _require(raw_payload is not None and manifest_payload is not None, "QUOTE_REFERENCE_NOT_IN_LEDGER")
        raw, manifest = _raw_reference(raw_payload), WC._manifest(manifest_payload)
        content = read_member(q["raw_content_member"])
        _require(0 < len(content) <= MAX_MEMBER_BYTES, "QUOTE_MEMBER_UNREADABLE")
    return WC.WalletCopyabilityQuoteWitness(
        q["condition_context"], q["condition_value"], q["token_context"], q["token_value"], q["price_direction_sign"],
        q["price"], q["top_level_depth_shares"], WP._observability_from_mapping(q["observability"]), tuple(q["dq_flags"]),
        q["replay_fidelity"], raw, manifest, content)


def _context_status(context, binding: dict, as_of: str) -> str:
    if (context.condition_context, context.token_context, context.instrument_class) != (
            "DATA_API_RESPONSE_CONDITION_ID", "CLOB_TOKEN_ID", "STANDARD_BINARY_OUTCOME"):
        return "CONTEXT_NOT_STANDARD_BINARY_NATIVE_IDS"
    found = [(k, m) for k, m in binding["markets"].items() if m["condition_id"] == context.condition_value]
    if not found:
        return "CONTEXT_FOREIGN_TO_PIT_UNIVERSE"
    if len(found) > 1 or not found[0][1]["condition_unique"]:
        return "CONTEXT_CONDITION_AMBIGUOUS"
    market = found[0][1]
    if TOKEN_PREFIX + context.token_value not in market["token_ids"]:
        return "CONTEXT_TOKEN_NOT_IN_MARKET"
    if context.metadata_observability.local_first_seen_time != market["metadata_observed_time"]:
        return "CONTEXT_METADATA_CLOCK_MISMATCH"
    if market["metadata_observed_time"] > as_of:
        return "CONTEXT_OBSERVED_AFTER_WALLET_AS_OF"
    return "BOUND:" + found[0][0]


def wallet(binding: dict, ledger_path, case: dict, read_member, decision_time: str) -> dict:
    """Native WALLET-01 -> WALLET-02 -> WALLET-03 on the same verified head, cohort, contexts and cutoff."""
    as_of = case["wallet_as_of"]
    _require(binding["as_of"] <= decision_time and as_of <= decision_time, "WALLET_AS_OF_AFTER_DECISION")
    loaded = WL.load_and_verify_wallet_evidence_ledger(ledger_path)
    _require(loaded.is_valid and loaded.snapshot is not None, "WALLET_LEDGER_NOT_VERIFIED")
    _require(loaded.snapshot.head_hash == case["expected_wallet_ledger_head"], "WALLET_LEDGER_HEAD_MISMATCH")
    grouped: dict = {}
    for entry in loaded.snapshot.entries:
        grouped.setdefault(entry.record_kind, {})[entry.record_id] = entry.payload
    try:
        manifests = tuple(WC._manifest(p) for p in grouped.get("RESEARCH_PROVENANCE_MANIFEST", {}).values())
        cohort = WP.wallet_discovery_cohort_from_mapping(case["cohort"], provenance_manifests=manifests)
        contexts = tuple(WP.wallet_profile_market_context_from_mapping(m) for m in case["market_contexts"])
        identities = None if case["identity_observability"] is None else {
            k: WP._observability_from_mapping(v) for k, v in case["identity_observability"].items()}
        witnesses = tuple(_witness(q, grouped, read_member) for q in case["quote_witnesses"])
        costs = tuple(WC.WalletCopyabilityCostScenario(**c) for c in case["cost_scenarios"])
    except (WP.WalletProfileError, WC.WalletCopyabilityError) as error:
        raise RelationWalletStop("WALLET_INPUT_REFUSED:" + str(error).split(":")[0]) from None
    except (ValueError, TypeError, KeyError, AttributeError):
        raise RelationWalletStop("WALLET_INPUT_INVALID") from None
    statuses = {c.wallet_profile_market_context_id: _context_status(c, binding, as_of) for c in contexts}
    if all(s.startswith("BOUND:") for s in statuses.values()):  # unbound contexts refuse A6 below anyway
        _require(all(w.condition_value in {c.condition_value for c in contexts} for w in witnesses), "QUOTE_CONDITION_NOT_BOUND")
    target = binding["target"]
    target_ids = [cid for cid, s in statuses.items() if s == "BOUND:" + target["market_id"]
                  and next(c for c in contexts if c.wallet_profile_market_context_id == cid).token_value
                  in [t[len(TOKEN_PREFIX):] for t in target["token_ids"]]]
    context_counts = {"considered": len(contexts), "bound": sum(1 for s in statuses.values() if s.startswith("BOUND:")),
                      "refused": dict(sorted(Counter(s for s in statuses.values() if not s.startswith("BOUND:")).items())),
                      "target_contexts": len(target_ids)}
    base = {"ledger_head": loaded.snapshot.head_hash, "ledger_entries": len(loaded.snapshot.entries),
            "cohort_snapshot_id": cohort.wallet_discovery_cohort_snapshot_id, "wallet_as_of": as_of,
            "context_counts": context_counts, "profile": None, "assessment": None}
    reason = None
    if context_counts["bound"] != len(contexts):
        reason = "CONTEXT_NOT_BOUND_TO_SHARED_PIT_UNIVERSE"
    elif len(target_ids) != 1:
        reason = "TARGET_CONTEXT_MISSING" if not target_ids else "TARGET_CONTEXT_AMBIGUOUS"
    if reason:
        return dict(base, status="REFUSED", reason=reason)
    try:
        profile = WP.build_wallet_profile_snapshot(
            wallet_ledger_path=ledger_path, cohort_snapshot=cohort, target_wallet=case["target_wallet"], as_of=as_of,
            market_contexts=contexts, identity_observability=identities or {})
        assessment = WC.build_wallet_copyability_research_assessment(
            profile=profile, wallet_ledger_path=ledger_path, expected_ledger_head=case["expected_wallet_ledger_head"],
            cohort_snapshot=cohort, target_wallet=case["target_wallet"], as_of=as_of, market_contexts=contexts,
            quote_witnesses=witnesses, delay_seconds=tuple(case["delay_seconds"]), cost_scenarios=costs,
            identity_observability=identities)
        mapping = WC.wallet_copyability_research_assessment_to_mapping(assessment)
        _require(WC.wallet_copyability_research_assessment_from_mapping(mapping) == assessment, "WALLET03_MAPPING_ROUNDTRIP_FAILED")
    except (WP.WalletProfileError, WC.WalletCopyabilityError) as error:
        return dict(base, status="REFUSED", reason="NATIVE_REFUSED:" + str(error).split(":")[0])
    target_id = target_ids[0]
    delays = []
    for result in mapping["delay_results"]:
        excluded = sum(n for _, n in result["excluded_reason_counts"])
        _require(result["considered_event_count"] == result["eligible_event_count"] + excluded, "WALLET_DENOMINATOR_INVALID")
        delays.append({k: result[k] for k in ("delay_seconds", "considered_event_count", "eligible_event_count",
                                              "excluded_reason_counts", "independently_observable_quote_count",
                                              "context_coverage_count", "outcome_reason_counts", "status",
                                              "best_scenario_price_difference_after_costs",
                                              "worst_scenario_price_difference_after_costs")})
    events = mapping["event_evidence"]
    target_eligible = sum(1 for e in events if e["market_context_id"] == target_id and e["reason"] == "ELIGIBLE")
    observed = any(d["status"] == "OBSERVABLE_CONDITIONAL" for d in delays)
    if not target_eligible:
        status, reason = "INSUFFICIENT", "NO_TARGET_ELIGIBLE_EVENT"
    elif not observed:
        status, reason = "INSUFFICIENT", "NO_OBSERVED_CONDITIONAL_DELAY_RESULT"
    else:
        status, reason = "ADMITTED", None
    sample = WP.wallet_profile_snapshot_to_mapping(profile)["sample_strength"]
    return dict(base, status=status, reason=reason,
                target_context_id=target_id,
                profile={"wallet_profile_snapshot_id": profile.wallet_profile_snapshot_id,
                         "subject_cluster_id": profile.subject_cluster_id, "sample_strength": sample},
                assessment={"wallet_copyability_research_assessment_id": assessment.wallet_copyability_research_assessment_id,
                            "market_context_ids": mapping["market_context_ids"], "delay_seconds": mapping["delay_seconds"],
                            "event_reason_counts": dict(sorted(Counter(e["reason"] for e in events).items())),
                            "target_eligible_events": target_eligible,
                            "quote_source_status_counts": dict(sorted(Counter(q["source_status"] for q in mapping["quote_evidence"]).items())),
                            "delay_results": delays,
                            "authority": {k: mapping[k] for k in ("advisory_only", "no_execution_authority",
                                                                  "no_strategy_authority", "no_qualification_authority")}})


# ------------------------------------------------------------------ receipt


def capability_ledger(a5: dict, a6: dict) -> dict:
    evaluated = [s for s in a5["selected"] if s["oracle3"]["verdict"] == "UPSTREAM_CONDITIONAL_EVALUATED"]
    fee_schedules = sorted({f'{v["venue"]}:{v["source"]}:taker_rate={v["taker_rate"]}'
                            for s in evaluated for v in (s["oracle3"]["schedules"] or {}).values()})
    every = a5["selected"] + a5["rejected"]
    rows = {
        "R3-03": {"status": "ENG_OFFLINE_SHARED_CASE_CONSUMED_BY_A5_NOT_VALUE_VERIFIED" if evaluated else "NOT_EXERCISED_ON_SHARED_CASE",
                  "call": "TRUE_VENDORED_UPSTREAM_CALL", "evaluated_selected_models": len(evaluated)},
        "R3-03-FEES": {"status": "FIXTURE_FEE_SCHEDULE_INVOKED_CURRENTNESS_UNVERIFIED" if evaluated else "NOT_EXERCISED_ON_SHARED_CASE",
                       "call": "TRUE_VENDORED_UPSTREAM_CALL", "schedules": fee_schedules},
        "R3-04": {"status": "OPEN", "call": "NATIVE_ONLY", "cause": OPEN_CAUSES["R3-04"],
                  "native_real_world_counts": dict(sorted(Counter(s["real_world"]["status"] for s in a5["selected"]).items()))},
        "R3-11": {"status": "OPEN", "call": "NATIVE_ONLY", "cause": OPEN_CAUSES["R3-11"],
                  "native_counterexamples": sum(1 for s in a5["selected"] if s["disposition"] == "COUNTEREXAMPLE")},
        "R3-19": {"status": "OPEN", "call": "NATIVE_ONLY", "cause": OPEN_CAUSES["R3-19"],
                  "native_disposition_counts": dict(sorted(Counter(s.get("disposition", "REJECTED") for s in every).items()))},
        "R3-14": {"status": "OPEN_OWNER_RIGHTS", "call": "BLOCKED_SCHEMA_INSPECTED_ONLY", "cause": OPEN_CAUSES["R3-14"],
                  "native_wallet01_consumed": a6["ledger_head"] is not None},
    }
    for key, row in rows.items():
        repo, commit, member, licence = PINS[key]
        row.update(repository=repo, commit=commit, member=member, license=licence, value_verified=False,
                   owner_disposition="PENDING")
    return {"touched": rows, "other_30_capability_ids": "UNCHANGED", "b1b_open_rows_retained": 5,
            "lane_b": "R3-15/R3-16/R3-17/R3-26_SEPARATELY_OWNED_UNTOUCHED", "w06_book_gap_fill_model": "NOT_ATTEMPTED"}


def roles(a5: dict, a6: dict) -> dict:
    return {"A1_A4": "READ_ONLY_B1A_LINEAGE", "A5_relations": a5["status"], "A6_wallet": a6["status"],
            "A7_execution_economics": "CONDITIONAL_READ_SIDE_POINTER_ONLY_NO_NEW_MODEL",
            "A8_A9": "NOT_ATTEMPTED_LATER_OWNERS", "coordinator": "FUTURE_W08_CONSUMES_THIS_INTERFACE",
            "llm_child_invocations": 0}


def build_core(*, case_sha256: str, input_sha256: dict, code_identity: str, lineage: dict, binding: dict, a5: dict,
               a6: dict) -> dict:
    return json.loads(SG.canonical_bytes({
        "schema_id": RECEIPT_SCHEMA, "wp_id": WP_ID, "evidence_class": EVIDENCE_CLASS, "code_identity": code_identity,
        "case_sha256": case_sha256, "input_sha256": input_sha256, "b1a_lineage": lineage,
        "shared_case": {k: binding[k] for k in ("grounding_receipt_id", "alpha_universe_snapshot_id", "as_of", "target",
                                                "scout_denominators")},
        "a5_relations": a5, "a6_wallet": a6, "a7_pointer": a5["a7_pointer"], "roles": roles(a5, a6),
        "capability": capability_ledger(a5, a6),
        "trace": ["B1-A verify", "native scout", "REL-01 verify", "Oracle3 parity run/verify", "WALLET-01 verify",
                  "WALLET-02 profile", "WALLET-03 copyability + mapping round trip"],
        "authority": AUTHORITY}))


def finalize(core: dict) -> dict:
    return {"schema_id": RECEIPT_SCHEMA, "receipt_id": RECEIPT_PREFIX + sha_json(core), "core": core}
