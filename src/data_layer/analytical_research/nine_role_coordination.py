"""B4 finite conditional nine-role native receipt coordinator: pure core (S10-CAP-NINE-ROLE-COORD-01).

Pure, deterministic functions only (no I/O): the strict campaign manifest, the write-once plan and its identities,
the fixed nine-slot routing table, the seven read-side role consumers (A1-A7) over already cold-verified native
B1-A / W01 / B2 / B3 receipts, the hash-chained journal state machine and the sealed receipt core. A8/A9 are
explicit dependency skips (W09/W10). Every consumer reads native fields by their exact keys; a consumer delivery
(COMPLETED_CONSUMED) is kept separate from the native disposition it carries (ADMITTED / REFUSED / INSUFFICIENT /
PARTIAL ...), which is never promoted. Nothing here dispatches a model, provider, Hermes child or network call.
"""
from __future__ import annotations

from collections import Counter
import hashlib
import json
import re

from src.data_layer.analytical_research import source_grounding as SG

WP_ID = "S10-CAP-NINE-ROLE-COORD-01"
VERSION = "b4-nine-role-coordination-v1"
MANIFEST_SCHEMA = "side26-nine-role-campaign-v1"
PLAN_SCHEMA = "b4-nine-role-plan-v1"
EVENT_SCHEMA = "b4-nine-role-event-v1"
RECEIPT_SCHEMA = "b4-nine-role-receipt-v1"
EVIDENCE_CLASS = "OFFLINE_ENGINEERING_COORDINATION_DIAGNOSTIC"
KINDS = ("campaign", "case", "task", "attempt", "consumer", "event", "plan", "receipt")
PREFIX = {k: "b4" + k + ":sha256:" for k in KINDS}

ROLES = ("A1", "A2", "A3", "A4", "A5", "A6", "A7", "A8", "A9")
ROLE_NAMES = {"A1": "A1_SCOUT", "A2": "A2_RESEARCH", "A3": "A3_FORECASTER", "A4": "A4_FALSIFIER", "A5": "A5_RELATIONS",
              "A6": "A6_WALLET", "A7": "A7_EXECUTION_ECONOMICS", "A8": "A8_LEARNING", "A9": "A9_IMPROVEMENT"}
ROUTES = {"SOURCE_REVIEW": ("A1", "A2"),
          "FORECAST_REVIEW": ("A1", "A2", "A3", "A4"),
          "RELATION_REVIEW": ("A1", "A2", "A3", "A4", "A5", "A7"),
          "WALLET_REVIEW": ("A1", "A2", "A3", "A4", "A6"),
          "FULL_SHARED_CASE": ("A1", "A2", "A3", "A4", "A5", "A6", "A7")}
# A4 needs its A3 pair partner delivered (atomic W01 pair); A5/A6 need both, independently of each other.
PREREQUISITES = {"A1": (), "A2": ("A1",), "A3": ("A1", "A2"), "A4": ("A1", "A2", "A3"),
                 "A5": ("A1", "A2", "A3", "A4"), "A6": ("A1", "A2", "A3", "A4"), "A7": ("A1", "A2", "A3", "A4", "A5"),
                 "A8": (), "A9": ()}
FUTURE = {"A8": "W09_PENDING", "A9": "W10_PENDING"}
SOURCE_KINDS = ("B2", "B3")
RECEIPT_RE = {"B2": re.compile(r"b2research:sha256:[0-9a-f]{64}"), "B3": re.compile(r"b3research:sha256:[0-9a-f]{64}")}
W01_ROLES = ("FORECASTER", "FALSIFIER")
MAX_CASES = 2
MAX_RECEIPT_ID_CHARS = 256
MAX_EVENTS = 100
CODE_RE = re.compile(r"[A-Z][A-Z0-9_]{0,63}(:[A-Z0-9_]{1,63})?")
HEX_RE = re.compile(r"[0-9a-f]{64}")

DELIVERY = ("COMPLETED_CONSUMED", "SKIPPED", "REFUSED", "FAILED", "QUARANTINED")
CASE_TERMINAL = {"CASE_VERIFIED": "VERIFIED", "CASE_VERIFY_REFUSED": "REFUSED", "CASE_VERIFY_FAILED": "FAILED",
                 "CASE_VERIFY_QUARANTINED": "QUARANTINED"}
ROLE_TERMINAL = {"ROLE_COMPLETED_CONSUMED": "COMPLETED_CONSUMED", "ROLE_REFUSED": "REFUSED", "ROLE_FAILED": "FAILED",
                 "ROLE_QUARANTINED": "QUARANTINED"}
SKIP_REASONS = frozenset({"NOT_REQUESTED", "W09_PENDING", "W10_PENDING", "CASE_NOT_VERIFIED", "B3_NOT_SUPPLIED",
                          "A5_NATIVE_NOT_ADMITTED"} | {"PREREQUISITE_NOT_CONSUMED:" + r for r in ROLES[:5]})
QUARANTINE_REASON = "INTERRUPTED_IN_FLIGHT"
NETWORK_QUARANTINE_REASON = "NETWORK_ATTEMPT_BLOCKED"  # a case verify that tried a socket: kept distinct
_CASE_KEYS = {"slot", "case_id", "attempt_id"}
_ROLE_KEYS = {"slot", "role", "task_id", "attempt_id"}
PAYLOAD_KEYS = {
    "CASE_VERIFY_STARTED": _CASE_KEYS, "CASE_VERIFIED": _CASE_KEYS | {"lineage_sha256"},
    "CASE_VERIFY_REFUSED": _CASE_KEYS | {"reason"}, "CASE_VERIFY_FAILED": _CASE_KEYS | {"reason"},
    "CASE_VERIFY_QUARANTINED": _CASE_KEYS | {"reason"},
    "ROLE_STARTED": _ROLE_KEYS, "ROLE_SKIPPED": {"slot", "role", "task_id", "reason"},
    "ROLE_COMPLETED_CONSUMED": _ROLE_KEYS | {"consumer_id", "source", "projection_sha256", "native_status", "dependencies"},
    "ROLE_REFUSED": _ROLE_KEYS | {"reason"}, "ROLE_FAILED": _ROLE_KEYS | {"reason"},
    "ROLE_QUARANTINED": _ROLE_KEYS | {"reason"}}

CAPABILITY = {
    "R3-21": {"repository": "pmxt-dev/pmxt-mcp", "commit": "b47230894e7d0b2a97fc571ce6fea32cf566a9a8",
              "method": "createServer; generated tools catalog incl write routes",
              "native_concept": "CLOSED_ROUTE_TABLE_AND_DENIED_MUTATION_NO_TOOL_CATALOG"},
    "R3-29": {"repository": "valory-xyz/trader", "commit": "b5b0281adecfeca56e0fb5bb7aec7c35c96d24b6",
              "method": "RequestType enum from polymarket_client/request_types.py",
              "native_concept": "CLOSED_TASK_TERMINAL_STATES_FAIL_ABORT_QUARANTINE"}}
AUTHORITY = {"advisory_only": True, "offline_only": True, "provider_calls": 0, "network_calls": 0,
             "hermes_dispatches": 0, "model_calls": 0, "orders": 0, "capital_usd": 0, "paper": False,
             "execution": False, "live": False, "strategy_mutation": False, "scheduler": False,
             "canonical_store_writes": 0, "human_review_required": True}
CLAIMS = {"nine_functional_agents": False, "integration_complete": False, "autonomous_recovery": False,
          "external_attestation": False, "economics_supported": False}
DEFERRALS = ("NO_NEW_DISPATCH_PRIOR_W01_WITNESS_ONLY", "A8_W09_PENDING", "A9_W10_PENDING",
             "HARD_KILL_STALE_LOCK_TORN_JOURNAL_RECOVERY_W11_W12", "B3_R007_SPLIT_AND_D001_D008_CARRIED")


class CoordinationStop(Exception):
    """Whole-operation fail-closed stop with a stable closed code (never echoes input)."""


class RoleRefusal(Exception):
    """A role consumer cannot deliver from the verified native evidence (closed code)."""


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise CoordinationStop(code)


def _deliver(condition: bool, code: str) -> None:
    if not condition:
        raise RoleRefusal(code)


def digest(kind: str, value: object) -> str:
    """Domain-separated SHA-256 over native canonical bytes; no timestamps or randomness."""
    return hashlib.sha256(("b4:" + kind + "\n").encode("ascii") + SG.canonical_bytes(value)).hexdigest()


def ident(kind: str, value: object) -> str:
    return PREFIX[kind] + digest(kind, value)


def sha_json(value: object) -> str:
    return hashlib.sha256(SG.canonical_bytes(value)).hexdigest()


# ------------------------------------------------------------------ R001 manifest + R002 plan / routing


def validate_manifest(manifest: object) -> None:
    """Closed manifest v1; failure precedence: schema -> unknown -> missing -> type -> value."""
    _require(type(manifest) is dict, "MANIFEST_FIELD_TYPE_INVALID")
    _require(manifest.get("schema_id") == MANIFEST_SCHEMA and type(manifest.get("schema_id")) is str,
             "MANIFEST_SCHEMA_UNSUPPORTED")
    _require(set(manifest) <= {"schema_id", "cases"}, "MANIFEST_UNKNOWN_FIELD")
    _require("cases" in manifest, "MANIFEST_FIELD_MISSING")
    cases = manifest["cases"]
    _require(type(cases) is list, "MANIFEST_FIELD_TYPE_INVALID")
    _require(1 <= len(cases) <= MAX_CASES, "MANIFEST_FIELD_VALUE_INVALID")
    for case in cases:
        _require(type(case) is dict, "MANIFEST_FIELD_TYPE_INVALID")
        _require(set(case) <= {"source_kind", "receipt_id", "route"}, "MANIFEST_UNKNOWN_FIELD")
        _require(set(case) == {"source_kind", "receipt_id", "route"}, "MANIFEST_FIELD_MISSING")
        _require(all(type(v) is str for v in case.values()), "MANIFEST_FIELD_TYPE_INVALID")
        _require(case["source_kind"] in SOURCE_KINDS and case["route"] in ROUTES, "MANIFEST_FIELD_VALUE_INVALID")
        rid = case["receipt_id"]
        _require(rid.isascii() and len(rid) <= MAX_RECEIPT_ID_CHARS and RECEIPT_RE[case["source_kind"]].fullmatch(rid)
                 is not None, "MANIFEST_RECEIPT_ID_INVALID")
    pairs = [(c["receipt_id"], c["route"]) for c in cases]
    _require(len(set(pairs)) == len(pairs), "MANIFEST_DUPLICATE_CASE")


def slots(manifest: dict) -> list[str]:
    return ["case-%02d" % (i + 1) for i in range(len(manifest["cases"]))]


def policy() -> dict:
    return {"version": VERSION, "roles": list(ROLES), "routes": {k: list(v) for k, v in ROUTES.items()},
            "prerequisites": {k: list(v) for k, v in PREREQUISITES.items()}, "future": dict(FUTURE),
            "max_attempts_per_subject": 1, "automatic_retry": False}


def build_plan(manifest: dict, inventory: dict) -> dict:
    """Write-once plan: every case always gets nine fixed slots with exact ids and prerequisites."""
    validate_manifest(manifest)
    campaign_id = ident("campaign", {"version": VERSION, "manifest": manifest, "inventory": inventory, "policy": policy()})
    cases = []
    for slot, case in zip(slots(manifest), manifest["cases"]):
        case_id = ident("case", {"campaign_id": campaign_id, "slot": slot, "receipt_id": case["receipt_id"],
                                 "route": case["route"]})
        tasks = []
        for role in ROLES:
            task_id = ident("task", {"case_id": case_id, "role": role})
            tasks.append({"role": role, "task_id": task_id, "attempt_id": ident("attempt", {"subject": task_id, "ordinal": 1}),
                          "requested": role in ROUTES[case["route"]], "prerequisites": list(PREREQUISITES[role])})
        cases.append({"slot": slot, "case_id": case_id, "source_kind": case["source_kind"],
                      "receipt_id": case["receipt_id"], "route": case["route"],
                      "verify_attempt_id": ident("attempt", {"subject": case_id, "ordinal": 1}), "tasks": tasks})
    plan = {"schema_id": PLAN_SCHEMA, "wp_id": WP_ID, "version": VERSION, "campaign_id": campaign_id,
            "inventory": inventory, "policy": policy(), "cases": cases}
    plan = json.loads(SG.canonical_bytes(plan))
    return {"plan_id": ident("plan", plan), "plan": plan}


def decide(case: dict, role: str, verify_status: str | None, results: dict) -> tuple[str, str | None]:
    """('SKIP', reason) or ('ATTEMPT', None) from the route, the case verification and same-case results only."""
    if role in FUTURE:
        return "SKIP", FUTURE[role]
    if role not in ROUTES[case["route"]]:
        return "SKIP", "NOT_REQUESTED"
    if verify_status != "VERIFIED":
        return "SKIP", "CASE_NOT_VERIFIED"
    if role == "A7" and case["source_kind"] != "B3":
        return "SKIP", "B3_NOT_SUPPLIED"
    for prerequisite in PREREQUISITES[role]:
        if (results.get(prerequisite) or {}).get("status") != "COMPLETED_CONSUMED":
            return "SKIP", "PREREQUISITE_NOT_CONSUMED:" + prerequisite
    if role == "A7" and results["A5"]["native_status"] != "ADMITTED":
        return "SKIP", "A5_NATIVE_NOT_ADMITTED"
    return "ATTEMPT", None


# ------------------------------------------------------------------ R001/R003 native lineage over verified receipts


def case_lineage(view: dict) -> dict:
    """Same-case identity across the verified nested receipts (B3 ->) B2 -> B1-A -> W01, by native ids only."""
    b2, spine, w01, b3 = view["b2"], view["spine"], view["w01"], view["b3"]
    b2c, sc, wc = b2["core"], spine["core"], w01["core"]
    lin, shared = b2c["b1a_lineage"], b2c["shared_case"]
    _require(lin["spine_receipt_id"] == spine["receipt_id"], "NESTED_SPINE_MISMATCH")
    _require(sc["w01"]["receipt_id"] == w01["receipt_id"] == lin["a3_a4"]["w01_receipt_id"], "NESTED_W01_MISMATCH")
    grounding = shared["grounding_receipt_id"]
    _require(grounding == lin["grounding_receipt_id"] == sc["a1_scout"]["grounding_receipt_id"]
             == wc["grounding_receipt_id"] == sc["w01"]["grounding_receipt_id"], "NESTED_GROUNDING_MISMATCH")
    _require(shared["alpha_universe_snapshot_id"] == lin["alpha_universe_snapshot_id"]
             == sc["a1_scout"]["alpha_universe_snapshot_id"] and shared["as_of"] == lin["as_of"] == sc["a1_scout"]["as_of"],
             "NESTED_UNIVERSE_MISMATCH")
    _require(shared["target"] == lin["a1_target"] == sc["a1_scout"]["target"], "NESTED_TARGET_MISMATCH")
    decision_time = b2c["a5_relations"]["decision_time"]
    _require(type(decision_time) is str and decision_time >= shared["as_of"], "NESTED_DECISION_TIME_INVALID")
    b3_id = None
    if view["source_kind"] == "B3":
        bl = b3["core"]["b2_lineage"]
        _require(bl["b2_receipt_id"] == b2["receipt_id"] and bl["b2_code_identity"] == b2c["code_identity"],
                 "NESTED_B2_MISMATCH")
        _require(bl["b1a"] == {"spine_receipt_id": spine["receipt_id"], "grounding_receipt_id": grounding,
                               "alpha_universe_snapshot_id": shared["alpha_universe_snapshot_id"], "as_of": shared["as_of"]}
                 and bl["target"] == shared["target"] and bl["decision_time"] == decision_time, "NESTED_B3_LINEAGE_MISMATCH")
        b3_id = b3["receipt_id"]
    else:
        _require(b3 is None, "NESTED_B3_UNEXPECTED")
    _require(view["receipt_id"] == (b3_id if b3_id else b2["receipt_id"]), "CASE_RECEIPT_ID_MISMATCH")
    return {"source_kind": view["source_kind"], "receipt_id": view["receipt_id"], "b3_receipt_id": b3_id,
            "b2_receipt_id": b2["receipt_id"], "b2_code_identity": b2c["code_identity"],
            "spine_receipt_id": spine["receipt_id"], "spine_code_identity": sc["code_identity"],
            "w01_receipt_id": w01["receipt_id"], "witness_id": wc["witness_id"], "episode_id": wc["episode_id"],
            "forecast_receipt_id": sc["forecast_diagnostic"]["receipt_id"], "grounding_receipt_id": grounding,
            "alpha_universe_snapshot_id": shared["alpha_universe_snapshot_id"], "as_of": shared["as_of"],
            "decision_time": decision_time, "target_market_id": shared["target"]["market_id"],
            "candidate_id": shared["target"]["candidate_id"], "target_sha256": sha_json(shared["target"]),
            "native_evidence_class": {"b2": b2c["evidence_class"], "w01": wc["evidence_class"],
                                      "b3": b3["core"]["evidence_class"] if b3_id else None},
            "prior_host_witness": {"provider_invocations": wc["provider_invocations"],
                                   "acceptance_status": wc["acceptance_status"]}}


# ------------------------------------------------------------------ R004 seven typed role consumers


def _a1(view: dict, deps: dict) -> dict:
    sc, lin = view["spine"]["core"], view["b2"]["core"]["b1a_lineage"]
    a1 = sc["a1_scout"]
    _deliver(a1["target"] == lin["a1_target"] and a1["grounding_receipt_id"] == lin["grounding_receipt_id"],
             "A1_LINEAGE_MISMATCH")
    target = a1["target"]
    return {"source": {"receipt_id": view["spine"]["receipt_id"], "member": "core.a1_scout"},
            "native_status": a1["status"],
            "projection": {"role": ROLE_NAMES["A1"], "native_status": a1["status"], "native_reason": a1["reason"],
                           "target_market_id": target["market_id"], "event_id": target["event_id"],
                           "candidate_id": target["candidate_id"], "catalog": target["catalog"],
                           "target_sha256": sha_json(target), "grounding_receipt_id": a1["grounding_receipt_id"],
                           "alpha_universe_snapshot_id": a1["alpha_universe_snapshot_id"], "as_of": a1["as_of"],
                           "denominators": a1["denominators"]}}


def _a2(view: dict, deps: dict) -> dict:
    sc, lin = view["spine"]["core"], view["b2"]["core"]["b1a_lineage"]
    a2 = sc["a2_research"]
    _deliver(a2["source_allowlist"] == lin["a2_source_allowlist"]
             and a2["raw_evidence_reference_ids"] == lin["a2_raw_evidence_reference_ids"], "A2_LINEAGE_MISMATCH")
    _deliver(a2["sdk"]["real_network_requests"] == 0 and type(a2["sdk"]["real_network_requests"]) is int,
             "A2_NETWORK_EVIDENCE_INVALID")
    _deliver(deps["A1"]["grounding_receipt_id"] == lin["grounding_receipt_id"], "A2_GROUNDING_MISMATCH")
    return {"source": {"receipt_id": view["spine"]["receipt_id"], "member": "core.a2_research"},
            "native_status": a2["status"],
            "projection": {"role": ROLE_NAMES["A2"], "native_status": a2["status"], "native_reason": a2["reason"],
                           "source_allowlist": a2["source_allowlist"], "upstream_excluded": a2["upstream_excluded"],
                           "raw_evidence_reference_ids": a2["raw_evidence_reference_ids"],
                           "admitted_label_reference_ids": a2["admitted_label_reference_ids"],
                           "denominators": a2["denominators"], "native_vs_upstream": a2["native_vs_upstream"],
                           "metaculus_counts": a2["metaculus"]["counts"],
                           "sdk_mock_transport_requests": a2["sdk"]["mock_transport_requests"],
                           "sdk_real_network_requests": a2["sdk"]["real_network_requests"],
                           "grounding_receipt_id": deps["A1"]["grounding_receipt_id"]}}


def w01_pair(view: dict) -> list:
    """The atomic W01 FORECASTER/FALSIFIER pair; any defect refuses both, never one half."""
    w01, sc, lin = view["w01"], view["spine"]["core"], view["b2"]["core"]["b1a_lineage"]
    core = w01["core"]
    body = core["witness_body"]
    children = body["children"]
    _deliver(type(children) is list and len(children) == 2 and [c["task_index"] for c in children] == [0, 1]
             and [c["role"] for c in children] == list(W01_ROLES), "W01_PAIR_SHAPE_INVALID")
    parent = body["parent_session_id"]
    sessions = [c["session_id"] for c in children]
    _deliver(all(type(s) is str and s for s in sessions + [parent]) and len(set(sessions)) == 2 and parent not in sessions
             and all(c["parent_session_id"] == parent for c in children)
             and len({c["subagent_id"] for c in children}) == 2, "W01_PAIR_IDENTITY_INVALID")
    summary = [{"task_index": c["task_index"], "role": c["role"], "status": c["status"]} for c in children]
    _deliver(summary == sc["w01"]["children"] == lin["a3_a4"]["children"], "W01_PAIR_SUMMARY_MISMATCH")
    _deliver(core["witness_id"] == sc["w01"]["witness_id"] == lin["a3_a4"]["witness_id"]
             and core["episode_id"] == sc["w01"]["episode_id"] == lin["a3_a4"]["episode_id"], "W01_PAIR_WITNESS_MISMATCH")
    _deliver(all(type(c["api_calls"]) is int and type(c["tokens"]) is dict and HEX_RE.fullmatch(c["summary_sha256"])
                 for c in children), "W01_PAIR_USAGE_INVALID")
    return children


def _child(view: dict, index: int, role: str) -> dict:
    children = w01_pair(view)
    child, core = children[index], view["w01"]["core"]
    cost = child["cost"]
    return {"source": {"receipt_id": view["w01"]["receipt_id"], "member": "core.witness_body.children[%d]" % index},
            "native_status": child["status"],
            "projection": {"role": ROLE_NAMES[role], "native_status": child["status"], "task_index": child["task_index"],
                           "child_role": child["role"], "session_id": child["session_id"],
                           "parent_session_id": child["parent_session_id"], "subagent_id": child["subagent_id"],
                           "partner_subagent_id": children[1 - index]["subagent_id"],
                           "effective_tools": child["effective_tools"], "api_calls": child["api_calls"],
                           "tokens": child["tokens"], "cost": cost,
                           "cost_status": "UNKNOWN" if cost == "UNKNOWN" else "RECORDED_BY_PRIOR_W01",
                           "summary_sha256": child["summary_sha256"], "witness_id": core["witness_id"],
                           "episode_id": core["episode_id"], "w01_receipt_id": view["w01"]["receipt_id"],
                           "provider_invocations_recorded": core["provider_invocations"], "new_dispatches": 0}}


def _a3(view: dict, deps: dict) -> dict:
    out = _child(view, 0, "A3")
    forecast = view["spine"]["core"]["forecast_diagnostic"]
    out["projection"]["forecast"] = {k: forecast[k] for k in ("receipt_id", "score_status", "case_id", "decision_time",
                                                              "method_parity", "is_a3_child_forecast")}
    return out


def _a4(view: dict, deps: dict) -> dict:
    out = _child(view, 1, "A4")
    _deliver(deps["A3"]["subagent_id"] == out["projection"]["partner_subagent_id"]
             and deps["A3"]["session_id"] != out["projection"]["session_id"], "W01_PAIR_PARTNER_MISMATCH")
    return out


def _a5(view: dict, deps: dict) -> dict:
    b2c = view["b2"]["core"]
    a5 = b2c["a5_relations"]
    _deliver(b2c["shared_case"]["grounding_receipt_id"] == deps["A1"]["grounding_receipt_id"]
             and sha_json(b2c["shared_case"]["target"]) == deps["A1"]["target_sha256"], "A5_SHARED_CASE_MISMATCH")
    _deliver(all(p["tradable"] is False and p["executable_edge"] is False and p["conditional_only"] is True
                 for p in a5["a7_pointer"]), "A5_POINTER_AUTHORITY_INVALID")
    return {"source": {"receipt_id": view["b2"]["receipt_id"], "member": "core.a5_relations"},
            "native_status": a5["status"],
            "projection": {"role": ROLE_NAMES["A5"], "native_status": a5["status"], "native_reason": a5["reason"],
                           "b2_receipt_id": view["b2"]["receipt_id"], "rel_receipt_id": a5["rel_receipt_id"],
                           "rel_code_identity": a5["rel_code_identity"], "parity_receipt_id": a5["parity_receipt_id"],
                           "parity_code_identity": a5["parity_code_identity"], "decision_time": a5["decision_time"],
                           "fee_policy_id": a5["fee_policy_id"], "upstream": a5["upstream"],
                           "denominators": a5["denominators"],
                           "selected": [{"model_id": s["model_id"], "relation": s["relation"], "role": s["role"],
                                         "reason": s["reason"], "disposition": s["disposition"],
                                         "oracle3_verdict": s["oracle3"]["verdict"]} for s in a5["selected"]],
                           "rejected": a5["rejected"],
                           "a7_pointer": [{"model_id": p["model_id"], "native_economic_status": p["native_economic_status"],
                                           "conditional_only": True, "tradable": False, "executable_edge": False}
                                          for p in a5["a7_pointer"]]}}


def _a6(view: dict, deps: dict) -> dict:
    b2c = view["b2"]["core"]
    a6 = b2c["a6_wallet"]
    _deliver(b2c["shared_case"]["grounding_receipt_id"] == deps["A1"]["grounding_receipt_id"], "A6_SHARED_CASE_MISMATCH")
    assessment = a6["assessment"] or {}
    return {"source": {"receipt_id": view["b2"]["receipt_id"], "member": "core.a6_wallet"},
            "native_status": a6["status"],
            "projection": {"role": ROLE_NAMES["A6"], "native_status": a6["status"], "native_reason": a6["reason"],
                           "b2_receipt_id": view["b2"]["receipt_id"], "cohort_snapshot_id": a6["cohort_snapshot_id"],
                           "wallet_as_of": a6["wallet_as_of"], "ledger_entries": a6["ledger_entries"],
                           "context_counts": a6["context_counts"],
                           "profile_id": (a6["profile"] or {}).get("wallet_profile_snapshot_id"),
                           "sample_strength": (a6["profile"] or {}).get("sample_strength"),
                           "assessment_id": assessment.get("wallet_copyability_research_assessment_id"),
                           "event_reason_counts": assessment.get("event_reason_counts"),
                           "delay_statuses": [[d["delay_seconds"], d["status"]] for d in assessment.get("delay_results", [])],
                           "native_authority": assessment.get("authority"), "economics_claimed": False}}


def _a7(view: dict, deps: dict) -> dict:
    b3c = view["b3"]["core"]
    role, lineage, point, replay = b3c["a7_role"], b3c["b2_lineage"], b3c["point_mechanics"], b3c["replay_diagnostic"]
    selected = lineage["selected"]
    _deliver(lineage["b2_receipt_id"] == deps["A5"]["b2_receipt_id"] == view["b2"]["receipt_id"], "A7_B2_LINEAGE_MISMATCH")
    _deliver(sha_json(lineage["target"]) == deps["A1"]["target_sha256"], "A7_TARGET_MISMATCH")
    _deliver(selected["model_id"] in [s["model_id"] for s in deps["A5"]["selected"] if s["role"] == "ADMITTED"],
             "A7_MODEL_NOT_A5_ADMITTED")
    _deliver(role["economics_supported"] is False and role["conditional_only"] is True and selected["tradable"] is False
             and selected["executable_edge"] is False and point["fill_claimed"] is False and point["profit_claimed"] is False,
             "A7_AUTHORITY_INVALID")
    _deliver(lineage["venue_snapshot_id"] == point["venue_snapshot_id"], "A7_SNAPSHOT_MISMATCH")
    return {"source": {"receipt_id": view["b3"]["receipt_id"], "member": "core.a7_role"},
            "native_status": role["overall"],
            "projection": {"role": ROLE_NAMES["A7"], "native_status": role["overall"],
                           "b3_receipt_id": view["b3"]["receipt_id"], "b2_receipt_id": lineage["b2_receipt_id"],
                           "model_id": selected["model_id"], "basket_id": selected["basket_id"],
                           "atomicity": selected["atomicity"], "venue_snapshot_id": lineage["venue_snapshot_id"],
                           "execution_feasibility_assessment_id": point["execution_feasibility_assessment_id"],
                           "point_mechanics_status": point["status"], "fee_exactness": point["fee_exactness"],
                           "replay_status": replay["status"], "reasons": role["reasons"],
                           "denominators": role["denominators"], "economics_supported": False,
                           "wallet_economics": "NOT_CLAIMED", "conditional_only": True}}


CONSUMERS = {"A1": _a1, "A2": _a2, "A3": _a3, "A4": _a4, "A5": _a5, "A6": _a6, "A7": _a7}


def consume(role: str, view: dict, deps: dict) -> dict:
    """One typed consumer per eligible role; malformed native shapes refuse (closed), they never deliver."""
    _require(role in CONSUMERS, "ROLE_HAS_NO_CONSUMER")
    try:
        out = CONSUMERS[role](view, deps)
    except (KeyError, TypeError, AttributeError, IndexError):
        raise RoleRefusal("NATIVE_FIELD_SHAPE_INVALID") from None
    _deliver(type(out["native_status"]) is str and CODE_RE.fullmatch(out["native_status"].upper()) is not None,
             "NATIVE_STATUS_INVALID")
    return json.loads(SG.canonical_bytes(out))


def consumer_record(task: dict, out: dict, dependency_ids: list) -> dict:
    projection_sha256 = digest("projection", out["projection"])
    return {"consumer_id": ident("consumer", {"task_id": task["task_id"], "source": out["source"],
                                              "projection_sha256": projection_sha256, "dependencies": dependency_ids}),
            "source": out["source"], "projection_sha256": projection_sha256, "native_status": out["native_status"],
            "dependencies": list(dependency_ids)}


# ------------------------------------------------------------------ R005/R006 journal state machine


def make_event(seq: int, prev: str, kind: str, payload: dict) -> dict:
    envelope = {"schema_id": EVENT_SCHEMA, "seq": seq, "prev": prev, "type": kind, "payload": payload}
    return {"event_id": ident("event", envelope), "event": envelope}


def _fresh_state(plan: dict) -> dict:
    return {"cases": [{"verify": None, "verify_reason": None, "lineage_sha256": None,
                       "tasks": {r: None for r in ROLES}} for _ in plan["cases"]],
            "in_flight": None, "head": None, "count": 0}


def next_step(plan: dict, state: dict):
    """The single next legal subject: ('CASE', i) or ('ROLE', i, role); None when every slot is terminal."""
    for index, case_state in enumerate(state["cases"]):
        if case_state["verify"] is None:
            return ("CASE", index)
        for role in ROLES:
            if case_state["tasks"][role] is None:
                return ("ROLE", index, role)
    return None


def _results(case_state: dict) -> dict:
    return {r: v for r, v in case_state["tasks"].items() if v is not None}


def _check_terminal(kind: str, payload: dict, task_or_case: dict, results: dict) -> None:
    if kind == "CASE_VERIFY_QUARANTINED":
        _require(payload["reason"] in (QUARANTINE_REASON, NETWORK_QUARANTINE_REASON), "JOURNAL_PAYLOAD_INVALID")
    elif kind == "ROLE_QUARANTINED":
        _require(payload["reason"] == QUARANTINE_REASON, "JOURNAL_PAYLOAD_INVALID")
    elif kind == "CASE_VERIFIED":
        _require(type(payload["lineage_sha256"]) is str and HEX_RE.fullmatch(payload["lineage_sha256"]) is not None,
                 "JOURNAL_PAYLOAD_INVALID")
    elif kind == "ROLE_COMPLETED_CONSUMED":
        deps = [results[p]["consumer_id"] for p in task_or_case["prerequisites"]]
        _require(payload["dependencies"] == deps and type(payload["consumer_id"]) is str
                 and payload["consumer_id"].startswith(PREFIX["consumer"])
                 and HEX_RE.fullmatch(payload["consumer_id"][len(PREFIX["consumer"]):]) is not None
                 and type(payload["projection_sha256"]) is str and HEX_RE.fullmatch(payload["projection_sha256"]) is not None
                 and type(payload["native_status"]) is str and type(payload["source"]) is dict
                 and set(payload["source"]) == {"receipt_id", "member"}
                 and all(type(v) is str for v in payload["source"].values()), "JOURNAL_PAYLOAD_INVALID")
        _require(payload["consumer_id"] == ident("consumer", {"task_id": task_or_case["task_id"],
                                                               "source": payload["source"],
                                                               "projection_sha256": payload["projection_sha256"],
                                                               "dependencies": deps}), "JOURNAL_CONSUMER_ID_INVALID")
    else:
        _require(type(payload["reason"]) is str and CODE_RE.fullmatch(payload["reason"]) is not None,
                 "JOURNAL_PAYLOAD_INVALID")


def _apply(plan: dict, state: dict, doc: object) -> None:
    _require(type(doc) is dict and set(doc) == {"event_id", "event"} and type(doc["event"]) is dict, "JOURNAL_EVENT_INVALID")
    envelope = doc["event"]
    _require(set(envelope) == {"schema_id", "seq", "prev", "type", "payload"} and envelope["schema_id"] == EVENT_SCHEMA,
             "JOURNAL_EVENT_INVALID")
    _require(type(envelope["seq"]) is int and envelope["seq"] == state["count"] + 1, "JOURNAL_SEQUENCE_INVALID")
    _require(envelope["prev"] == (state["head"] or state["plan_id"]), "JOURNAL_CHAIN_BROKEN")
    _require(doc["event_id"] == ident("event", envelope), "JOURNAL_EVENT_ID_INVALID")
    kind, payload = envelope["type"], envelope["payload"]
    _require(kind in PAYLOAD_KEYS and type(payload) is dict and set(payload) == PAYLOAD_KEYS[kind], "JOURNAL_PAYLOAD_INVALID")
    step = next_step(plan, state)
    _require(step is not None, "JOURNAL_OVERRUN")
    case = plan["cases"][step[1]]
    case_state = state["cases"][step[1]]
    # the event family must fit the next step before any family-specific key is read
    _require(payload["slot"] == case["slot"] and kind.startswith(step[0] + "_"), "JOURNAL_ORDER_INVALID")
    if step[0] == "CASE":
        _require(payload["case_id"] == case["case_id"] and payload["attempt_id"] == case["verify_attempt_id"],
                 "JOURNAL_IDENTITY_INVALID")
        if state["in_flight"] is None:
            _require(kind == "CASE_VERIFY_STARTED", "JOURNAL_ORDER_INVALID")
            state["in_flight"] = ("CASE", step[1])
        else:
            _require(kind in CASE_TERMINAL, "JOURNAL_ORDER_INVALID")
            _check_terminal(kind, payload, case, {})
            case_state["verify"] = CASE_TERMINAL[kind]
            case_state["verify_reason"] = payload.get("reason")
            case_state["lineage_sha256"] = payload.get("lineage_sha256")
            state["in_flight"] = None
    else:
        role = step[2]
        task = case["tasks"][ROLES.index(role)]
        _require(payload["role"] == role and payload["task_id"] == task["task_id"], "JOURNAL_IDENTITY_INVALID")
        results = _results(case_state)
        if state["in_flight"] is None:
            decision, reason = decide(case, role, case_state["verify"], results)
            if decision == "SKIP":
                _require(kind == "ROLE_SKIPPED" and payload["reason"] == reason, "JOURNAL_ORDER_INVALID")
                case_state["tasks"][role] = {"status": "SKIPPED", "reason": reason, "attempt_id": None,
                                             "native_status": None, "record": None}
            else:
                _require(kind == "ROLE_STARTED" and payload["attempt_id"] == task["attempt_id"], "JOURNAL_ORDER_INVALID")
                state["in_flight"] = ("ROLE", step[1], role)
        else:
            _require(kind in ROLE_TERMINAL and payload["attempt_id"] == task["attempt_id"], "JOURNAL_ORDER_INVALID")
            _check_terminal(kind, payload, task, {p: results[p]["record"] for p in task["prerequisites"]
                                                  if kind == "ROLE_COMPLETED_CONSUMED"})
            record = {k: payload[k] for k in ("consumer_id", "source", "projection_sha256", "native_status",
                                              "dependencies")} if kind == "ROLE_COMPLETED_CONSUMED" else None
            case_state["tasks"][role] = {"status": ROLE_TERMINAL[kind], "reason": payload.get("reason"),
                                         "attempt_id": task["attempt_id"],
                                         "native_status": payload.get("native_status"), "record": record}
            state["in_flight"] = None
    state["head"], state["count"] = doc["event_id"], state["count"] + 1


def replay(plan_doc: dict, events: list) -> dict:
    """Strict replay of a (possibly incomplete) journal against the plan; any illegal event refuses."""
    _require(type(events) is list and len(events) <= MAX_EVENTS, "JOURNAL_TOO_LONG")
    plan = plan_doc["plan"]
    state = _fresh_state(plan)
    state["plan_id"] = plan_doc["plan_id"]
    for doc in events:
        _apply(plan, state, doc)
    state["complete"] = state["in_flight"] is None and next_step(plan, state) is None
    return state


def quarantine_event(plan_doc: dict, state: dict) -> tuple[str, dict]:
    """The single terminal for an in-flight subject found on resume: never a second logical attempt."""
    plan = plan_doc["plan"]
    flight = state["in_flight"]
    _require(flight is not None, "NOTHING_IN_FLIGHT")
    case = plan["cases"][flight[1]]
    if flight[0] == "CASE":
        return "CASE_VERIFY_QUARANTINED", {"slot": case["slot"], "case_id": case["case_id"],
                                           "attempt_id": case["verify_attempt_id"], "reason": QUARANTINE_REASON}
    task = case["tasks"][ROLES.index(flight[2])]
    return "ROLE_QUARANTINED", {"slot": case["slot"], "role": flight[2], "task_id": task["task_id"],
                                "attempt_id": task["attempt_id"], "reason": QUARANTINE_REASON}


# ------------------------------------------------------------------ R010-R012 receipt core


def counts(rows: list) -> dict:
    statuses = Counter(r["status"] for r in rows)
    return {"planned_slots": len(rows), **{s.lower(): statuses.get(s, 0) for s in DELIVERY},
            "attempted": sum(1 for r in rows if r["attempt_id"] is not None),
            "native_status_counts": dict(sorted(Counter(r["native_status"] for r in rows
                                                        if r["status"] == "COMPLETED_CONSUMED").items())),
            "skip_reason_counts": dict(sorted(Counter(r["reason"] for r in rows if r["status"] == "SKIPPED").items()))}


def capability() -> dict:
    rows = {key: dict(row, original_status="CONCEPT_ONLY", disposition="PARTIAL_CONCEPT_UNACCEPTED", invoked=False,
                      installed=False, value_verified=False, owner_disposition="PENDING", upstream_adoption=False)
            for key, row in CAPABILITY.items()}
    return {"touched": rows, "other_34_capability_ids": "UNCHANGED", "w07_source_rights": "OPEN",
            "lane_b": "R3-15/R3-16/R3-17/R3-26_SEPARATELY_OWNED_UNTOUCHED", "pr_268": "SEPARATE_UNTOUCHED"}


def handoffs(plan: dict, case: dict, rows: list) -> dict:
    """Frozen non-authorizing W09/W10 handoff metadata only; nothing is learned, routed or optimised here."""
    evidence = [r["consumer_id"] for r in rows if r["consumer_id"] is not None]
    return {role: {"campaign_id": plan["campaign_id"], "case_id": case["case_id"],
                   "task_id": case["tasks"][ROLES.index(role)]["task_id"], "version": VERSION,
                   "evidence_consumer_ids": evidence, "dependency": FUTURE[role], "authorizes": "NOTHING"}
            for role in ("A8", "A9")}


def build_core(*, code_identity: str, plan_doc: dict, state: dict, lineages: dict, projections: dict) -> dict:
    """Closed receipt core from the replayed plan + journal; lineages/projections only from native recomputation."""
    _require(state["complete"], "CAMPAIGN_INCOMPLETE")
    plan = plan_doc["plan"]
    cases, all_rows = [], []
    for case, case_state in zip(plan["cases"], state["cases"]):
        rows = []
        for task in case["tasks"]:
            result = case_state["tasks"][task["role"]]
            record = result["record"] or {}
            _require(result["status"] in DELIVERY, "SLOT_NOT_TERMINAL")
            rows.append({"role": task["role"], "task_id": task["task_id"], "requested": task["requested"],
                         "status": result["status"], "reason": result["reason"], "attempt_id": result["attempt_id"],
                         "native_status": result["native_status"], "consumer_id": record.get("consumer_id"),
                         "source": record.get("source"), "projection_sha256": record.get("projection_sha256"),
                         "dependencies": record.get("dependencies", []),
                         "projection": projections.get((case["slot"], task["role"]))})
        _require(len(rows) == len(ROLES), "DENOMINATOR_LOST")
        _require(all((r["status"] == "COMPLETED_CONSUMED") == (r["projection"] is not None) for r in rows),
                 "UNCONSUMED_COMPLETION")
        all_rows += rows
        cases.append({"slot": case["slot"], "case_id": case["case_id"], "source_kind": case["source_kind"],
                      "receipt_id": case["receipt_id"], "route": case["route"],
                      "verify": {"status": case_state["verify"], "reason": case_state["verify_reason"],
                                 "attempt_id": case["verify_attempt_id"]},
                      "lineage": lineages.get(case["slot"]), "tasks": rows, "counts": counts(rows),
                      "handoffs": handoffs(plan, case, rows)})
    verified = [c for c in cases if c["verify"]["status"] == "VERIFIED"]
    _require(all(c["lineage"] is not None for c in verified) and len(lineages) == len(verified), "LINEAGE_LOST")
    core = {"schema_id": RECEIPT_SCHEMA, "wp_id": WP_ID, "version": VERSION, "evidence_class": EVIDENCE_CLASS,
            "code_identity": code_identity, "plan_id": plan_doc["plan_id"], "campaign_id": plan["campaign_id"],
            "inventory": plan["inventory"], "journal": {"head_event_id": state["head"], "event_count": state["count"]},
            "cases": cases,
            "totals": dict(counts(all_rows), cases=len(cases),
                           case_verify_counts=dict(sorted(Counter(c["verify"]["status"] for c in cases).items()))),
            "prior_host_witness": {c["slot"]: {k: c["lineage"][k] for k in ("w01_receipt_id", "witness_id", "episode_id")}
                                   | c["lineage"]["prior_host_witness"] for c in verified},
            "new_activity": {"provider_calls": 0, "hermes_dispatches": 0, "model_calls": 0, "network_calls": 0,
                             "orders": 0, "capital_usd": 0},
            "usage": {"elapsed": "UNKNOWN_NOT_OBSERVED", "new_model_cost": "NONE_INCURRED",
                      "prior_child_cost": "AS_RECORDED_BY_W01_UNKNOWN_STAYS_UNKNOWN"},
            "journal_evidence": "LOCAL_HASH_CHAIN_STRUCTURAL_ONLY_NOT_EXTERNAL_ATTESTATION",
            "capability": capability(), "authority": AUTHORITY, "claims": CLAIMS, "deferrals": list(DEFERRALS)}
    return json.loads(SG.canonical_bytes(core))


def finalize(core: dict) -> dict:
    return {"schema_id": RECEIPT_SCHEMA, "receipt_id": ident("receipt", core), "core": core}
