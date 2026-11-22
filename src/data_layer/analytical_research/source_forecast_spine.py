"""B1-A source/PIT -> A1 scout -> A2 research -> W01 A3/A4 + forecast diagnostic consumer spine (S10-CAP-B1-SOURCE-FORECAST-01).

A thin, deterministic, offline projection over EXISTING native producers; it mints no market, source,
candidate, family, forecast or witness identity and is not a canonical store:

* A1 ``scout``: a cold-verified S10-R3-SRC-01 grounding scratch -> ``source_grounding.load_corpus``
  (``alpha_discovery.build_alpha_universe_snapshot``) -> ``bind_rule_texts`` ->
  ``public_market_contract_parity.normalize_native`` -> ``MarketCatalog.from_market_records`` round-trip
  cross-check -> receipt ``alpha_join``. One caller-named target market is admitted or refused with the full
  examined/valid/abstained/duplicate/ambiguous denominator.
* A2 ``research``: the SRC-01 receipt's accepted pre-cutoff sources for the target, consumed together with
  the real pinned ``metaculus_source_archive_bridge.assess_sources`` (an upstream quality failure removes a
  label from the W01 allowlist, never adds one) and real ``official_sdk_search_bridge.invoke_search`` calls on
  frozen pages (MockTransport, fixture.invalid) projected onto the native identities; a target identity
  conflict refuses. Native ranking vs SDK ranking is measured on the same query; no lift is inferred unless
  the SDK ranks the target strictly better.
* ``w01_case``: the existing W01 case shape built only from those verified identities plus the caller's
  scripted provider boundary; ``bind_forecast``: the existing forecast_evaluation receipt bound by identity.

Evidence class OFFLINE_ENGINEERING_DEMONSTRATION: no provider, model, network, credential, order, paper,
qualification or strategy authority. Citation integrity is not semantic truth.
"""
from __future__ import annotations

import base64
from collections import Counter
import json
from pathlib import Path

from src.data_layer.analytical_research import alpha_factory as AF
from src.data_layer.analytical_research import alpha_factory_registry as AFR
from src.data_layer.analytical_research import metaculus_source_archive_bridge as MSA
from src.data_layer.analytical_research import official_sdk_search_bridge as OSB
from src.data_layer.analytical_research import public_market_contract_parity as PMC
from src.data_layer.analytical_research import source_grounding as SG
from src.data_layer.polymarket.market_catalog import MarketCatalog
from src.data_layer.polymarket.snapshot_models import MarketMetadataSnapshotRecord

WP_ID = "S10-CAP-B1-SOURCE-FORECAST-01"
CASE_SCHEMA = "s10-cap-b1-spine-case-v1"
RECEIPT_SCHEMA = "s10-cap-b1-spine-receipt-v1"
RECEIPT_PREFIX = "b1spine:sha256:"
W01_CASE_SCHEMA = "s10-hermes-delegated-case-v1"
EVIDENCE_CLASS = "OFFLINE_ENGINEERING_DEMONSTRATION"
CASE_KEYS = {"schema_id", "target_market_id", "research_question", "hypothesis_family_id", "source_reference_ids",
             "evidence_lanes", "scripted_children", "sdk_pages"}
PAGE_KEYS = {"query_id", "request", "response"}
MAX_PAGES = 8
CATALOG_SOURCE = "native_pit_projection_cross_check"

# 36-row capability ledger delta (the frozen CSV is never edited). Only actual receipt + downstream read is credited.
CAPABILITY_TOUCHED = {
    "R3-02": "NATIVE_SOURCE_RETRIEVAL_CONSUMED_BY_W01_AND_FORECAST_OFFLINE_NOT_VALUE_VERIFIED",
    "R3-01-SOURCE_ARCHIVE": "PINNED_QUALITY_RESULT_CONSUMED_INTO_W01_ALLOWLIST_OFFLINE_NOT_VALUE_VERIFIED",
    "R3-23": "OFFICIAL_SDK_SEARCH_INVOKED_ON_FIXTURE_IDENTITY_CROSS_CHECK_CONSUMED_NOT_VALUE_VERIFIED",
    "R3-05": "W01_OFFLINE_WITNESSED_CHILDREN_CONSUMED_SPINE_PACKET_PROVIDER_ACCEPTANCE_PENDING",
    "R3-05-CITATIONS": "W01_NATIVE_CITATION_CHECK_ON_SPINE_ALLOWLIST_SEMANTIC_TRUTH_UNVERIFIED",
}
CAPABILITY_OPEN = {
    "B1_B_METHOD_PARITY_PENDING": ["R3-01", "R3-10", "R3-10-WANG", "R3-12", "R3-12-SAMPLER", "R3-18"],
    "LATER_LEARNING_OWNERS": ["R3-06", "R3-20", "R3-22"],
    "PROVIDER_OR_SOURCE_RIGHTS_BLOCKED": ["R3-07", "R3-07-ROUTER", "R3-08", "R3-13", "R3-21", "R3-28"],
    "DEFERRED_SAME_CASE_PARITY_REQUIRED": ["R3-24", "R3-25", "R3-27"],
    "LANE_B_SEPARATELY_OWNED": ["R3-15", "R3-16", "R3-17", "R3-26"],
}
AUTHORITY = {"advisory_only": True, "provider_calls": 0, "model_spend": "UNKNOWN_NOT_INCURRED_SCRIPTED_BOUNDARY",
             "network_calls": 0, "orders": False, "paper": False, "live": False, "strategy": False,
             "qualification": False, "credentials": False, "human_review_required": True}


class SpineStop(Exception):
    """Closed refusal: the message is a stable code, never caller text."""


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise SpineStop(code)


def sha_json(value: object) -> str:
    return SG.sha256_hex(SG.canonical_bytes(value))


def validate_case(case: object) -> None:
    _require(isinstance(case, dict) and set(case) == CASE_KEYS and case["schema_id"] == CASE_SCHEMA, "SPINE_CASE_FIELDS_INVALID")
    _require(type(case["target_market_id"]) is str and PMC.MARKET_RE.fullmatch(case["target_market_id"]) is not None,
             "TARGET_MARKET_ID_NONCANONICAL")
    _require(type(case["research_question"]) is str and case["research_question"].strip()
             and type(case["hypothesis_family_id"]) is str and isinstance(case["source_reference_ids"], list)
             and case["source_reference_ids"] and all(type(s) is str for s in case["source_reference_ids"])
             and len(set(case["source_reference_ids"])) == len(case["source_reference_ids"])
             and isinstance(case["evidence_lanes"], list) and isinstance(case["scripted_children"], dict),
             "SPINE_CASE_FIELDS_INVALID")
    pages = case["sdk_pages"]
    _require(isinstance(pages, list) and len(pages) <= MAX_PAGES
             and all(isinstance(p, dict) and set(p) == PAGE_KEYS and type(p["query_id"]) is str
                     and isinstance(p["request"], dict) and type(p["request"].get("q")) is str
                     and isinstance(p["response"], dict) and set(p["response"]) == OSB.RESPONSE_KEYS for p in pages)
             and len({p["query_id"] for p in pages}) == len(pages), "SDK_PAGES_INVALID")
    # credential- or trade-shaped keys refuse; SDK requests legitimately carry ``page_size`` (secrets still refused)
    SG._scan_forbidden({k: v for k, v in case.items() if k not in ("scripted_children", "sdk_pages")})
    SG._scan_forbidden(pages, trade_words=False)


# ------------------------------------------------------------------ frozen grounding


def load_grounding(grounding_dir: Path) -> dict:
    """Cold-verified SRC-01 receipt + frozen case + native universe and rule binding (read-only)."""
    from tools.alpha import run_source_grounding as SGCLI  # the native verifier itself, not a re-implementation
    grounding_dir = Path(grounding_dir)
    checked = SGCLI.verify(grounding_dir)
    _require(checked["status"] == "VERIFIED", "GROUNDING_NOT_VERIFIED")
    receipt = SGCLI._strict_json((grounding_dir / "receipt.json").read_bytes(), "GROUNDING_RECEIPT_UNREADABLE")
    frozen = SGCLI._strict_json((grounding_dir / "frozen_case.json").read_bytes(), "GROUNDING_RECEIPT_UNREADABLE")
    inputs = grounding_dir / "inputs"

    def read(rel: str) -> bytes:
        path = inputs / rel
        return path.read_bytes() if path.is_file() and not path.is_symlink() else b""
    core = receipt["core"]
    _, universe = SG.load_corpus(inputs / "pit.sqlite3", frozen["policy"], core["inputs"]["as_of"])
    _require(universe.alpha_universe_snapshot_id == core["inputs"]["alpha_universe_snapshot_id"], "GROUNDING_UNIVERSE_MISMATCH")
    rules, _ = SG.bind_rule_texts(universe, frozen["rule_texts"], read)
    return {"receipt_id": receipt["receipt_id"], "core": core, "frozen": frozen, "read": read, "inputs": inputs,
            "universe": universe, "rules": rules, "as_of": core["inputs"]["as_of"]}


# ------------------------------------------------------------------ A1 market scout


def _catalog_cross_check(universe, native: dict) -> tuple[dict, dict]:
    """Project PIT markets into WP10 snapshot records only to use the native catalog's lookups as a round trip."""
    records = [MarketMetadataSnapshotRecord(
        snapshot_id=m.metadata_record_version_id or "", captured_at_utc=m.metadata_observed_time or "",
        source=CATALOG_SOURCE, adapter_version=WP_ID, market_id=m.market_id, condition_id=m.condition_id or "",
        question=m.question_text or "", market_status=m.market_status or "", outcome_labels=list(m.outcome_labels),
        token_ids=list(m.token_ids), resolution_date=m.resolution_date, category=m.category, raw_field_names=[])
        for m in universe.markets]
    built = MarketCatalog.from_market_records(records)
    catalog = built.catalog
    status = {}
    for market_id, row in native.items():
        ok = (catalog.get_market(market_id) is not None
              and catalog.find_by_condition_id(row["condition_id"] or "") == market_id
              and all(catalog.find_by_token_id(t) == market_id for t in row["token_ids"]))
        status[market_id] = "CATALOG_ROUNDTRIP_OK" if ok else "CATALOG_ROUNDTRIP_CONFLICT"
    counts = {"records": built.total_records_processed, "unique_markets": built.unique_market_count,
              "duplicate_market_records": built.duplicate_market_count,
              "roundtrip_conflicts": sum(1 for s in status.values() if s != "CATALOG_ROUNDTRIP_OK")}
    return status, counts


def scout(grounding: dict, target_market_id: str) -> dict:
    universe = grounding["universe"]
    native = PMC.normalize_native(universe, grounding["rules"])
    catalog_status, catalog_counts = _catalog_cross_check(universe, native)
    joined = grounding["core"]["alpha_join"]["joined"]
    candidates = sorted({j["candidate_id"] for j in joined if target_market_id in j["market_ids"]})
    defects = Counter(d for row in native.values() for d in row["identity_defects"])
    denominators = {
        "examined": len(universe.markets), "identity_valid": sum(1 for r in native.values() if r["identity_status"] == "VALID"),
        "identity_abstained": sum(1 for r in native.values() if r["identity_status"] != "VALID"),
        "identity_defects": dict(sorted(defects.items())), "rule_text_bound": len(grounding["rules"]),
        "catalog": catalog_counts, "alpha_candidates_joined": len(joined),
        "admitted": 0, "refused": 0, "ambiguous": 0, "discovered_new_markets": 0}
    row = native.get(target_market_id)
    reason = None
    if row is None:
        reason = "TARGET_NOT_IN_UNIVERSE"
    elif row["identity_status"] != "VALID":
        reason = "TARGET_IDENTITY_ABSTAINED"
    elif catalog_status[target_market_id] != "CATALOG_ROUNDTRIP_OK" or catalog_counts["duplicate_market_records"]:
        reason = "TARGET_CATALOG_CONFLICT"
    elif target_market_id not in grounding["rules"]:
        reason = "TARGET_RULE_NOT_BOUND"
    elif not candidates:
        reason = "TARGET_CANDIDATE_MISSING"
    elif len(candidates) > 1:
        reason = "TARGET_CANDIDATE_AMBIGUOUS"
    key = "admitted" if reason is None else ("ambiguous" if reason == "TARGET_CANDIDATE_AMBIGUOUS" else "refused")
    denominators[key] = 1
    market = next((m for m in universe.markets if m.market_id == target_market_id), None)
    target = None if reason else {
        "market_id": target_market_id, "event_id": row["event_id"], "condition_id": row["condition_id"],
        "token_ids": list(row["token_ids"]), "outcome_labels": list(row["outcome_labels"]),
        "question_sha256": SG.sha256_hex(market.question_text.encode("utf-8")),
        "rule_sha256": grounding["rules"][target_market_id]["rule_content_sha256"],
        "rule_record_version_id": grounding["rules"][target_market_id]["rule_record_version_id"],
        "candidate_id": candidates[0], "catalog": catalog_status[target_market_id]}
    return {"status": "ADMITTED" if reason is None else "REFUSED", "reason": reason, "target": target,
            "grounding_receipt_id": grounding["receipt_id"],
            "alpha_universe_snapshot_id": universe.alpha_universe_snapshot_id, "as_of": grounding["as_of"],
            "denominators": denominators, "native": native}


# ------------------------------------------------------------------ A2 research specialist


def _sdk_measurement(grounding: dict, native: dict, pages: list, target_id: str) -> dict:
    index = SG.build_index(grounding["universe"], grounding["rules"])
    rows, calls = [], 0
    from polymarket.clients.public import PublicClient  # pinned SDK; identity checked by sdk_identity() first
    with PublicClient() as client:
        for page in pages:
            response = page["response"]
            try:
                body = base64.b64decode(response["body_b64"], validate=True)
            except (ValueError, TypeError):
                rows.append({"query_id": page["query_id"], "status": "PAGE_BODY_INVALID"})
                continue
            invoked = OSB.invoke_search(page["request"], body, response["status"], response["content_type"], client)
            calls += len(invoked["requests"])
            projected = None
            if invoked["status"] == "SDK_TYPED_PAGE":
                try:
                    raw = json.loads(body.decode("utf-8"))
                except (UnicodeDecodeError, ValueError):
                    raw = None
                projected = OSB.project_typed_page(invoked["page"], raw, native)
            native_rank = SG.rank_markets(index, page["request"]["q"])
            sdk_ranked = projected["ranked"] if projected and projected["status"] == "SDK_TYPED_PAGE_PROJECTED" else []
            target_rows = [m for e in (projected or {}).get("events", []) for m in e["markets"] if m["native_market_id"] == target_id]
            pos = {"native": native_rank["ranked"].index(target_id) + 1 if target_id in native_rank["ranked"] else None,
                   "sdk": sdk_ranked.index(target_id) + 1 if target_id in sdk_ranked else None}
            lift = "SDK_RANKS_TARGET_STRICTLY_BETTER" if pos["sdk"] and (pos["native"] is None or pos["sdk"] < pos["native"]) \
                else "NO_LIFT"
            rows.append({"query_id": page["query_id"], "status": invoked["status"],
                         "projection_status": projected["status"] if projected else None,
                         "market_status_counts": projected["market_status_counts"] if projected else {},
                         "sdk_dropped_markets": projected["sdk_dropped_markets"] if projected else 0,
                         "target_sdk_status": [m["status"] for m in target_rows], "native_status": native_rank["status"],
                         "target_rank": pos, "lift": lift, "orientation": "ORIENTATION_UNPROVEN"})
    return {"rows": rows, "mock_transport_requests": calls, "real_network_requests": 0}


def research(grounding: dict, scouted: dict, pages: list) -> dict:
    _require(scouted["status"] == "ADMITTED", "A1_NOT_ADMITTED")
    target_id = scouted["target"]["market_id"]
    core = grounding["core"]
    entries = core["sources"]["entries"]
    mine = [e for e in entries if e["market_id"] == target_id]
    refs = {r["raw_evidence_reference_id"]: r for r in core["sources"]["accepted_references"]}
    accepted = [e for e in mine if e["status"] == "ACCEPTED"]
    upstream = MSA.assess_sources(grounding["frozen"], core, grounding["read"])
    by_index = {r["index"]: r for r in upstream["rows"]}
    allow, excluded = [], {}
    for entry in accepted:
        row = by_index[entry["index"]]
        if row["verdict"] == "UPSTREAM_EVALUATED" and row["upstream_passed"]:
            allow.append(entry["source_label"])
        else:
            excluded[entry["source_label"]] = "UPSTREAM_QUALITY_NOT_PASSED" if row["verdict"] == "UPSTREAM_EVALUATED" \
                else "UPSTREAM_ABSTAINED:" + str(row["reason"]).split(":")[0]
    OSB.sdk_identity()
    sdk = _sdk_measurement(grounding, scouted["native"], pages, target_id)
    conflicts = [s for r in sdk["rows"] for s in r.get("target_sdk_status", []) if s != "IDENTITY_CONSISTENT"]
    reason = None
    if conflicts:
        reason = "SDK_TARGET_IDENTITY_CONFLICT"
    elif not allow:
        reason = "NO_ADMITTED_PRE_CUTOFF_SOURCE"
    clocks = {e["raw_evidence_reference_id"]: refs[e["raw_evidence_reference_id"]].get("pit") for e in accepted}
    return {"status": "ADMITTED" if reason is None else "REFUSED", "reason": reason, "source_allowlist": allow,
            "upstream_excluded": excluded,
            "raw_evidence_reference_ids": [e["raw_evidence_reference_id"] for e in accepted],
            "admitted_label_reference_ids": [e["raw_evidence_reference_id"] for e in accepted if e["source_label"] in allow],
            "reference_clocks": clocks,
            "denominators": {"target_sources_total": len(mine), "target_sources_accepted": len(accepted),
                             "target_sources_refused": dict(sorted(Counter(e["reason"] or e["status"] for e in mine
                                                                          if e["status"] != "ACCEPTED").items())),
                             "allowlisted": len(allow), "upstream_excluded": len(excluded),
                             "corpus_sources_total": len(entries)},
            "metaculus": {"invocations": upstream["invocations"], "counts": upstream["counts"],
                          "target_rows": [{k: by_index[e["index"]][k] for k in ("source_label", "verdict", "reason",
                                                                                "upstream_passed", "agreement")}
                                          for e in mine]},
            "sdk": sdk,
            "native_vs_upstream": "NO_LIFT" if all(r.get("lift") == "NO_LIFT" for r in sdk["rows"]) else
                                  "SDK_BETTER_ON_SOME_QUERY_FIXTURE_ONLY_NOT_VALUE_VERIFIED"}


# ------------------------------------------------------------------ W01 handoff and forecast binding


def check_lineage(registry: Path, case: dict, candidate_id: str) -> None:
    loaded = AFR.load_and_verify_alpha_factory_registry(Path(registry))
    _require(loaded.is_valid and loaded.snapshot is not None, "REGISTRY_NOT_VERIFIED")
    records = {e.record_id: e.record for e in loaded.snapshot.entries}
    _require(isinstance(records.get(candidate_id), AF.OpportunityCandidate), "CANDIDATE_NOT_IN_LINEAGE")
    _require(isinstance(records.get(case["hypothesis_family_id"]), AF.HypothesisFamily), "FAMILY_NOT_IN_LINEAGE")
    _require(all(isinstance(records.get(s), AF.ResearchSourceReference) for s in case["source_reference_ids"]),
             "SOURCE_REFERENCE_NOT_IN_LINEAGE")


def w01_case(case: dict, scouted: dict, researched: dict) -> dict:
    """The existing W01 case shape, every identity copied from verified A1/A2 output (never from the model)."""
    _require(scouted["status"] == "ADMITTED" and researched["status"] == "ADMITTED", "A1_A2_NOT_ADMITTED")
    target = scouted["target"]
    return {"schema_id": W01_CASE_SCHEMA,
            "question": {"question_id": "b1a-" + target["market_id"].rsplit(":", 1)[1], "market_id": target["market_id"],
                         "candidate_id": target["candidate_id"], "source_cutoff": scouted["as_of"],
                         "rule_sha256": target["rule_sha256"], "source_allowlist": list(researched["source_allowlist"])},
            "research_question": case["research_question"], "hypothesis_family_id": case["hypothesis_family_id"],
            "source_reference_ids": list(case["source_reference_ids"]), "evidence_lanes": list(case["evidence_lanes"]),
            "scripted_children": case["scripted_children"]}


def bind_forecast(receipt: dict, scouted: dict, researched: dict) -> dict:
    """Bind the cold-verified forecast_evaluation receipt to the same market, rule, question and grounding."""
    core = receipt["core"]
    target = scouted["target"]
    _require(core["source_grounding"]["receipt_id"] == scouted["grounding_receipt_id"], "FORECAST_GROUNDING_MISMATCH")
    rows = [r for r in core["targets"] if r["market_id"] == target["market_id"]]
    _require(len(rows) == 1 and rows[0]["status"] == "SELECTED", "FORECAST_TARGET_NOT_SELECTED")  # eligible and in cohort
    row = rows[0]
    _require(row["rule_content_sha256"] == target["rule_sha256"] and row["question_sha256"] == target["question_sha256"]
             and row["event_group"] == target["event_id"], "FORECAST_TARGET_SCOPE_MISMATCH")
    _require(row["grounded_source_reference_ids"] == sorted(researched["raw_evidence_reference_ids"]),
             "FORECAST_SOURCE_REFERENCE_MISMATCH")
    return {"receipt_id": receipt["receipt_id"], "score_status": core["score_status"], "case_id": row["case_id"],
            "decision_time": row["decision_time"], "target_status": row["status"],
            "target_status_counts": dict(sorted(Counter(r["status"] for r in core["targets"]).items())),
            "is_a3_child_forecast": False, "method_parity": "B1_B_PENDING"}


def build_core(case: dict, scouted: dict, researched: dict, forecast: dict, w01: dict, code_identity: str) -> dict:
    a1 = {k: v for k, v in scouted.items() if k != "native"}
    return json.loads(SG.canonical_bytes({
        "schema_id": RECEIPT_SCHEMA, "wp_id": WP_ID, "evidence_class": EVIDENCE_CLASS, "code_identity": code_identity,
        "case_sha256": sha_json(case), "a1_scout": a1, "a2_research": researched, "forecast_diagnostic": forecast,
        "w01": w01, "trace": ["SRC-01 verify", "A1 scout", "A2 research (Metaculus leaves + SDK MockTransport)",
                              "forecast_evaluation run+verify", "W01 run+verify (pinned Hermes, scripted boundary)",
                              "Alpha cold read"],
        "capability_touched": CAPABILITY_TOUCHED, "capability_open": CAPABILITY_OPEN, "authority": AUTHORITY}))


def finalize(core: dict) -> dict:
    return {"schema_id": RECEIPT_SCHEMA, "receipt_id": RECEIPT_PREFIX + sha_json(core), "core": core}
