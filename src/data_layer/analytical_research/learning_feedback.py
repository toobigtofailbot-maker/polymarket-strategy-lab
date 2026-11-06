"""Immutable outcome -> score -> future-research learning feedback (S10-R3-LEARN-01).

Input is a cold-verified S10-R3-FORECAST-01 receipt (its frozen cases, cohort and original
p_yes values) plus a caller packet of later outcome records. Nothing is refit: each original
p_yes is scored unchanged with the native ``forecast_evaluation.score_one``. Every selected case
ends in exactly one counted state; per-record defects are counted, never dropped or repaired.

Outputs are descriptive diagnostics and an advisory, deterministic list of future research
proposals. Posture: RESEARCH_ONLY, DIAGNOSTIC_ONLY, NO_CANONICAL_WRITE. Stdlib only, no network,
no LLM/Hermes, no Alpha/PIT/WP170 write, no strategy/paper/order/live authority. A local outcome
record never authenticates settlement origin; synthetic labels never prove predictive value.
"""
from __future__ import annotations

from collections import Counter
from decimal import Decimal, localcontext
import json
import re

from src.data_layer.analytical_research import alpha_factory_registry as AFR
from src.data_layer.analytical_research import forecast_evaluation as FE
from src.data_layer.analytical_research import source_grounding as SG

WP_ID = "S10-R3-LEARN-01"
OUTCOMES_SCHEMA = "s10-r3-learn01-outcomes-v1"
RECEIPT_SCHEMA = "s10-r3-learn01-learning-receipt-v1"
RECEIPT_PREFIX = "learnfb:sha256:"
PROPOSAL_PREFIX = "learnprop:sha256:"
DIAGNOSTICS_VERSION = "learn01-diagnostics-v1"
CALLER = ("tools/alpha/run_learning_feedback.py:run -> run_forecast_evaluation.verify -> "
          "learning_feedback.build_learning_core -> forecast_evaluation.score_one")

PACKET_KEYS = {"schema_id", "packet_label", "forecast_receipt_id", "learning_cutoff", "records"}
RECORD_KEYS = {"case_id", "market_id", "event_group", "yes_label", "rule_content_sha256", "outcome_label",
               "resolved_time", "known_time", "local_first_seen_time", "source_content_sha256", "evidence_class"}
# Forecast corpus class -> the only outcome evidence class it may be joined with.
EVIDENCE_CLASS = {"SANITIZED_SYNTHETIC": "SANITIZED_SYNTHETIC", "LOCAL_REAL_PIT": "CALLER_IMPORTED_UNVERIFIED"}
OUTCOME_PROVENANCE = {"SANITIZED_SYNTHETIC": "SYNTHETIC_LABEL_NOT_SETTLEMENT",
                      "CALLER_IMPORTED_UNVERIFIED": "CALLER_IMPORTED_ORIGIN_UNAUTHENTICATED"}
MAX_RECORDS = 4000

# Per-case states; each selected case is in exactly one.
SCORABLE, MISSING, DISPUTED, LATE, EXCLUDED = "SCORABLE", "MISSING_OUTCOME", "DISPUTED", "LATE_AFTER_CUTOFF", "EXCLUDED"
CASE_STATES = (SCORABLE, MISSING, DISPUTED, LATE, EXCLUDED)
# Record refusal precedence (first failing check wins). Identity mismatches feed SOURCE_RULE_REVIEW.
IDENTITY_REASONS = ("MARKET_MISMATCH", "EVENT_GROUP_MISMATCH", "RULE_MISMATCH", "YES_LABEL_MISMATCH",
                    "OUTCOME_LABEL_UNKNOWN")

CALIBRATION_EDGES = tuple(Decimal(i) / 10 for i in range(11))  # predeclared, fixed before any outcome
MIN_BIN_N = 5
MIN_GROUP_N = 5
DRIFT_THRESHOLD = Decimal("0.15")

REASONS = ("RESOLUTION_EVIDENCE_MISSING", "SOURCE_RULE_REVIEW", "FORECAST_ABSTENTION", "INSUFFICIENT_SAMPLE",
           "CALIBRATION_DRIFT_REVIEW", "BASELINE_UNDERPERFORMING_REVIEW", "NO_PRIORITY_CHANGE")
ALPHA_LINKED, ALPHA_UNVERIFIED = "ALPHA_LINKED_READ_ONLY", "ALPHA_LINK_UNVERIFIED"

PROVIDER_LANES = ("R3-EXT-PMXT-01", "R3-EXT-SYNPATH-01", "R3-EXT-LSE-01", "R3-EXT-REACH-01", "R3-EXT-KAIROS-01",
                  "R3-EXT-BECKER-01")

_LABEL_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,95}")
_SHA_RE = re.compile(r"[0-9a-f]{64}")
_req = FE._require


def _sha(value: object) -> str:
    return SG.sha256_hex(SG.canonical_bytes(value))


# ------------------------------------------------------------------ whole-packet structure


def validate_packet(packet: object, forecast_receipt_id: str) -> None:
    """Whole-run structure stops; per-record defects are counted later by ``join_outcomes``."""
    _req(isinstance(packet, dict), "OUTCOMES_JSON_INVALID")
    FE._scan_forbidden(packet)
    _req(set(packet) == PACKET_KEYS, "OUTCOMES_FIELDS_INVALID")
    _req(packet["schema_id"] == OUTCOMES_SCHEMA, "OUTCOMES_SCHEMA_INVALID")
    _req(type(packet["packet_label"]) is str and _LABEL_RE.fullmatch(packet["packet_label"]) is not None,
         "PACKET_LABEL_INVALID")
    _req(packet["forecast_receipt_id"] == forecast_receipt_id, "FOREIGN_FORECAST_RECEIPT")
    _req(FE._utc(packet["learning_cutoff"]) is not None, "LEARNING_CUTOFF_INVALID")
    _req(type(packet["records"]) is list and 0 < len(packet["records"]) <= MAX_RECORDS, "OUTCOME_RECORDS_INVALID")


# ------------------------------------------------------------------ outcome join (forecasts never read here)


def _record_reason(rec: object, row: dict | None, evidence_class: str) -> str | None:
    """First failing check, or None. ``row`` is the frozen selected target row for rec's case."""
    clocks = {k: FE._utc(rec.get(k)) for k in ("resolved_time", "known_time")} if isinstance(rec, dict) else {}
    if not isinstance(rec, dict) or set(rec) != RECORD_KEYS or None in clocks.values() \
            or any(type(rec[k]) is not str for k in ("case_id", "market_id", "event_group", "yes_label", "outcome_label")) \
            or type(rec["rule_content_sha256"]) is not str or _SHA_RE.fullmatch(rec["rule_content_sha256"]) is None \
            or not (rec["local_first_seen_time"] is None or FE._utc(rec["local_first_seen_time"]) is not None) \
            or not (rec["source_content_sha256"] is None or (type(rec["source_content_sha256"]) is str
                                                             and _SHA_RE.fullmatch(rec["source_content_sha256"]))) \
            or rec["evidence_class"] not in OUTCOME_PROVENANCE:
        return "RECORD_FIELDS_INVALID"
    if row is None:
        return "FOREIGN_CASE"
    if rec["evidence_class"] != evidence_class:
        return "EVIDENCE_CLASS_MISMATCH"
    if rec["source_content_sha256"] is not None:
        # No source bytes are admitted by this WP, so a claimed source hash cannot be validated.
        return "SOURCE_CLAIM_UNVALIDATED"
    if rec["market_id"] != row["market_id"]:
        return "MARKET_MISMATCH"
    if rec["event_group"] != row["event_group"]:
        return "EVENT_GROUP_MISMATCH"
    if rec["rule_content_sha256"] != row["rule_content_sha256"]:
        return "RULE_MISMATCH"
    if rec["yes_label"] != row["yes_label"]:
        return "YES_LABEL_MISMATCH"
    if rec["outcome_label"] not in row["outcome_labels"]:
        return "OUTCOME_LABEL_UNKNOWN"
    resolved, known = clocks["resolved_time"], clocks["known_time"]
    first_seen = FE._utc(rec["local_first_seen_time"]) if rec["local_first_seen_time"] is not None else None
    if FE._key(known) < FE._key(resolved) or (first_seen is not None and FE._key(first_seen) < FE._key(known)):
        return "CLOCK_INCONSISTENT"
    if FE._key(resolved) <= FE._key(row["decision_time"]):
        return "RESOLVED_BEFORE_DECISION"
    return None


def _conflicts_prior(rec: dict, prior: object) -> bool:
    """A label already frozen in the forecast inputs must match exactly (label and resolution time)."""
    return isinstance(prior, dict) and type(prior.get("label")) is str and (
        prior["label"] != rec["outcome_label"] or FE._utc(prior.get("resolved_time")) != FE._utc(rec["resolved_time"]))


def join_outcomes(packet: dict, rows: dict, priors: dict, evidence_class: str) -> dict:
    """Bind each record to its frozen selected case; return one state per selected case plus the ledgers."""
    cutoff = FE._utc(packet["learning_cutoff"])
    ledger, by_case = [], {}
    for index, rec in enumerate(packet["records"]):
        case_id = rec.get("case_id") if isinstance(rec, dict) and type(rec.get("case_id")) is str else None
        row = rows.get(case_id)
        reason = _record_reason(rec, row, evidence_class)
        entry = {"index": index, "case_id": case_id if row is not None else None, "record_sha256": _sha(rec),
                 "status": "ADMITTED", "reason": reason}
        if reason is None:
            first_seen = FE._utc(rec["local_first_seen_time"]) if rec["local_first_seen_time"] is not None else None
            known = FE._utc(rec["known_time"])
            available = first_seen or known  # first_seen >= known, so it is the later availability clock
            entry.update(outcome_label=rec["outcome_label"], resolved_time=FE._utc(rec["resolved_time"]), known_time=known,
                         available_time=available,
                         clock_basis="LOCAL_FIRST_SEEN" if first_seen else "CALLER_ASSERTED_KNOWN_TIME",
                         within_cutoff=FE._key(available) <= FE._key(cutoff),
                         conflicts_prior=_conflicts_prior(rec, priors.get(case_id)))
            if entry["within_cutoff"] and entry["conflicts_prior"]:
                entry["reason"] = "PRIOR_OUTCOME_CONFLICT"  # a post-cutoff revision only feeds the correction ledger
        if entry["reason"]:
            entry = {k: entry[k] for k in ("index", "case_id", "record_sha256", "reason")} | {"status": "REFUSED"}
        ledger.append(entry)
        if row is not None:
            by_case.setdefault(case_id, []).append(entry)
    cases, corrections = {}, []
    for case_id in sorted(rows):
        entries = by_case.get(case_id, [])
        refused = sorted(e["reason"] for e in entries if e["reason"])
        admitted = [e for e in entries if e["reason"] is None]
        inside = [e for e in admitted if e["within_cutoff"]]
        state = {"case_id": case_id, "state": None, "reason": None, "y": None,
                 "record_sha256s": sorted(e["record_sha256"] for e in entries)}
        if "PRIOR_OUTCOME_CONFLICT" in refused:
            state.update(state=DISPUTED, reason="PRIOR_OUTCOME_CONFLICT")
        elif refused:
            state.update(state=EXCLUDED, reason=refused[0])
        elif not entries:
            state.update(state=MISSING, reason="NO_OUTCOME_RECORD")
        elif not inside:
            state.update(state=LATE, reason="AVAILABLE_AFTER_LEARNING_CUTOFF")
        elif len(inside) > 1:
            same = len({(e["outcome_label"], e["resolved_time"]) for e in inside}) == 1
            state.update(state=DISPUTED, reason="DUPLICATE_OUTCOME" if same else "CONFLICTING_OUTCOME")
        else:
            chosen = inside[0]
            state.update(state=SCORABLE, y=1 if chosen["outcome_label"] == rows[case_id]["yes_label"] else 0,
                         resolved_time=chosen["resolved_time"], known_time=chosen["known_time"],
                         available_time=chosen["available_time"], clock_basis=chosen["clock_basis"])
            for later in admitted:
                if not later["within_cutoff"]:  # informs a correction ledger only; history is not rewritten
                    corrections.append({"case_id": case_id, "record_sha256": later["record_sha256"],
                                        "conflicts_prior": later["conflicts_prior"],
                                        "status": "CORRECTION_AFTER_CUTOFF_SAME_LABEL"
                                        if later["outcome_label"] == chosen["outcome_label"]
                                        else "CORRECTION_AFTER_CUTOFF_LABEL_CHANGED"})
        cases[case_id] = state
    states = Counter(c["state"] for c in cases.values())
    return {
        "learning_cutoff": cutoff, "evidence_class": evidence_class, "provenance": OUTCOME_PROVENANCE[evidence_class],
        "settlement_origin_verified": False, "records": ledger, "cases": [cases[c] for c in sorted(cases)],
        "corrections": sorted(corrections, key=lambda c: (c["case_id"], c["record_sha256"])),
        "denominators": {"records_offered": len(ledger),
                         "records_admitted": sum(1 for e in ledger if e["status"] == "ADMITTED"),
                         "records_refused_by_reason": dict(sorted(Counter(e["reason"] for e in ledger if e["reason"]).items())),
                         "selected_cases": len(cases), **{s.lower(): states.get(s, 0) for s in CASE_STATES},
                         "case_reasons": dict(sorted(Counter(c["reason"] for c in cases.values() if c["reason"]).items()))},
    }


# ------------------------------------------------------------------ scoring of the original frozen probabilities


def _ids_sha(ids: list[str]) -> str:
    return _sha(sorted(ids))


def score_frozen(forecasts: dict, outcomes: dict, rows: dict) -> tuple[dict, dict]:
    """Score original p_yes unchanged; also return the paired id lists the diagnostics reuse."""
    cases = {c["case_id"]: c for c in outcomes["cases"]}
    scorable = sorted(c for c, s in cases.items() if s["state"] == SCORABLE)
    status = {m: {c: forecasts[c]["methods"][m]["status"] for c in cases} for m in FE.METHODS}
    available = {m: [c for c in scorable if status[m][c] == "FORECAST"] for m in FE.METHODS}
    paired = [c for c in scorable if all(c in available[m] for m in FE.PRIMARY_METHODS)]
    wang_paired = [c for c in paired if c in available[FE.WANG]]
    per_case = {m: {c: FE.score_one(Decimal(forecasts[c]["methods"][m]["p_yes"]), cases[c]["y"]) for c in available[m]}
                for m in FE.METHODS}
    states = Counter(s["state"] for s in cases.values())
    methods = {}
    for m in FE.METHODS:
        own = Counter(status[m][c] for c in scorable)
        methods[m] = {"lineage": FE.LINEAGE[m], "p_yes_source": "ORIGINAL_FROZEN_FORECAST_UNCHANGED",
                      "denominators": {"offered": len(cases), "eligible": len(scorable), "missing_outcome": states[MISSING],
                                       "disputed": states[DISPUTED], "late": states[LATE], "excluded": states[EXCLUDED],
                                       "abstained": own.get("ABSTAIN", 0), "unavailable": own.get("UNAVAILABLE", 0),
                                       "scored": len(available[m])},
                      "on_own_available": FE._aggregate(list(per_case[m].values())),
                      "on_paired": FE._aggregate([per_case[m][c] for c in (wang_paired if m == FE.WANG else paired)]),
                      "paired_set": "PRIMARY_AND_WANG" if m == FE.WANG else "PRIMARY",
                      "scored_case_ids_sha256": _ids_sha(available[m])}
    deltas = None
    if paired:
        ind = methods[FE.INDEPENDENT]["on_paired"]
        deltas = {f"independent_minus_{name}_{k}": FE._q(Decimal(ind[k]) - Decimal(methods[ref]["on_paired"][k]))
                  for name, ref in (("market", FE.MARKET), ("base_rate", FE.BASE_RATE)) for k in ("brier", "log_loss")}
    scored_groups = [rows[c]["event_group"] for c in scorable]
    scoring = {
        "metric_ids": ["BRIER_SCORE", "LOG_LOSS", "METACULUS_BINARY_BASELINE_SCORE"], "scorer": "forecast_evaluation.score_one",
        "log_loss_epsilon": str(FE.EPSILON), "orientation": {"BRIER_SCORE": "LOWER_IS_BETTER", "LOG_LOSS": "LOWER_IS_BETTER",
                                                             "METACULUS_BINARY_BASELINE_SCORE": "HIGHER_IS_BETTER"},
        "denominators": {"selected": len(cases), "scorable": len(scorable), "paired_intersection": len(paired),
                         "paired_with_wang": len(wang_paired), "scorable_event_groups": len(set(scored_groups)),
                         "event_groups_disjoint": len(set(scored_groups)) == len(scored_groups)},
        "paired_case_ids_sha256": _ids_sha(paired), "paired_with_wang_case_ids_sha256": _ids_sha(wang_paired),
        "methods": methods, "paired_deltas": deltas,
        "lift_status": "NO_PAIRED_CASES" if not paired else "DIAGNOSTIC_ONLY_NOT_OOS_LIFT_NOT_VALUE",
        "per_case": {c: {m: {"brier": FE._q(per_case[m][c]["brier"]), "log_loss": FE._q(per_case[m][c]["log_loss"])}
                         for m in FE.METHODS if c in per_case[m]} for c in scorable},
    }
    return scoring, {"primary": paired, "wang": wang_paired}


# ------------------------------------------------------------------ descriptive diagnostics


def _bin(p: Decimal) -> int:
    return min(int(p * 10), 9)  # edges 0.0 .. 1.0 step 0.1, last bin closed


def calibration(forecasts: dict, outcomes: dict, method: str, ids: list[str]) -> list[dict]:
    y = {c["case_id"]: c["y"] for c in outcomes["cases"]}
    bins = {i: [] for i in range(10)}
    for c in ids:
        p = Decimal(forecasts[c]["methods"][method]["p_yes"])
        bins[_bin(p)].append((p, y[c]))
    out = []
    with localcontext() as ctx:
        ctx.prec = 50
        for i in range(10):
            members = bins[i]
            n = len(members)
            out.append({"bin": f"[{CALIBRATION_EDGES[i]},{CALIBRATION_EDGES[i + 1]}{']' if i == 9 else ')'}", "n": n,
                        "mean_p_yes": FE._q(sum(p for p, _ in members) / n) if n else None,
                        "observed_yes_rate": FE._q(Decimal(sum(v for _, v in members)) / n) if n else None,
                        "status": "OK" if n >= MIN_BIN_N else "INSUFFICIENT_SAMPLE"})
    return out


def _uncertainty(diffs: list[Decimal]) -> dict:
    n = len(diffs)
    if n < 2:
        return {"n": n, "mean": None, "standard_error": None, "significance_claim": False}
    with localcontext() as ctx:
        ctx.prec = 50
        mean = sum(diffs) / n
        variance = sum((d - mean) ** 2 for d in diffs) / (n - 1)
        return {"n": n, "mean": FE._q(mean), "standard_error": FE._q((variance / n).sqrt()), "significance_claim": False}


def group_diagnostics(dimension: str, rows: dict, forecasts: dict, outcomes: dict, scoring: dict,
                      paired: list[str]) -> list[dict]:
    cases = {c["case_id"]: c for c in outcomes["cases"]}
    paired = set(paired)
    groups: dict[str, list[str]] = {}
    for c in sorted(cases):
        groups.setdefault(rows[c][dimension], []).append(c)
    out = []
    for key in sorted(groups):
        members = groups[key]
        states = Counter(cases[c]["state"] for c in members)
        scorable = [c for c in members if cases[c]["state"] == SCORABLE]
        group_paired = [c for c in scorable if c in paired]
        ind_abstain = sum(1 for c in scorable if forecasts[c]["methods"][FE.INDEPENDENT]["status"] != "FORECAST")
        sample_ok = len(group_paired) >= MIN_GROUP_N
        per = scoring["per_case"]
        diffs = [Decimal(per[c][FE.INDEPENDENT]["brier"]) - Decimal(per[c][FE.MARKET]["brier"]) for c in group_paired]
        with localcontext() as ctx:
            ctx.prec = 50
            mean_p = (sum(Decimal(forecasts[c]["methods"][FE.INDEPENDENT]["p_yes"]) for c in group_paired) / len(group_paired)
                      if group_paired else None)
            rate = Decimal(sum(cases[c]["y"] for c in group_paired)) / len(group_paired) if group_paired else None
        gap = None if mean_p is None else abs(mean_p - rate)
        out.append({
            dimension: key, "case_ids_sha256": _ids_sha(members), "selected": len(members),
            **{s.lower(): states.get(s, 0) for s in CASE_STATES},
            "independent_not_forecast": ind_abstain, "paired": len(group_paired),
            "evidence_coverage": FE._ratio(len(scorable), len(members)),
            "sample_status": "OK" if sample_ok else "INSUFFICIENT_SAMPLE", "min_group_n": MIN_GROUP_N,
            "independent_mean_p_yes": None if mean_p is None else FE._q(mean_p),
            "observed_yes_rate": None if rate is None else FE._q(rate),
            "independent_calibration_gap": None if gap is None else FE._q(gap),
            "independent_minus_market_brier": _uncertainty(diffs),
            "identity_refusals": sum(1 for c in members if cases[c]["reason"] in IDENTITY_REASONS),
        })
    return out


def diagnostics(rows: dict, forecasts: dict, outcomes: dict, scoring: dict, paired: dict) -> dict:
    calibration_ids = {m: paired["wang"] if m == FE.WANG else paired["primary"] for m in FE.METHODS}
    return {
        "version": DIAGNOSTICS_VERSION, "calibration_edges": [str(e) for e in CALIBRATION_EDGES], "min_bin_n": MIN_BIN_N,
        "min_group_n": MIN_GROUP_N, "drift_threshold": str(DRIFT_THRESHOLD), "outcome_vintage": outcomes["learning_cutoff"],
        "calibration": {m: calibration(forecasts, outcomes, m, ids) for m, ids in calibration_ids.items()},
        "by_category": group_diagnostics("category", rows, forecasts, outcomes, scoring, paired["primary"]),
        "by_horizon": group_diagnostics("horizon_band", rows, forecasts, outcomes, scoring, paired["primary"]),
        "interpretation": "DESCRIPTIVE_POSTHOC_DIAGNOSTIC_NOT_OOS_NOT_QUALIFICATION_NOT_EDGE",
    }


# ------------------------------------------------------------------ advisory future-research proposals


def proposal_reasons(group: dict) -> list[str]:
    reasons = set()
    if group["missing_outcome"] + group["late_after_cutoff"] + group["excluded"] + group["disputed"]:
        reasons.add("RESOLUTION_EVIDENCE_MISSING")
    if group["identity_refusals"] or group["disputed"]:
        reasons.add("SOURCE_RULE_REVIEW")
    if group["independent_not_forecast"]:
        reasons.add("FORECAST_ABSTENTION")
    if group["sample_status"] != "OK":
        reasons.add("INSUFFICIENT_SAMPLE")
    else:
        if Decimal(group["independent_calibration_gap"]) > DRIFT_THRESHOLD:
            reasons.add("CALIBRATION_DRIFT_REVIEW")
        if Decimal(group["independent_minus_market_brier"]["mean"]) > 0:
            reasons.add("BASELINE_UNDERPERFORMING_REVIEW")
    return [r for r in REASONS if r in reasons] or ["NO_PRIORITY_CHANGE"]


def alpha_links(registry_path, market_ids: set[str]) -> dict:
    """Read-only native registry load; returns candidate/episode ids whose subject refs hit the cohort."""
    if registry_path is None:
        return {"status": "NOT_SUPPLIED", "registry_head_entry_hash": None, "by_market": {}}
    loaded = AFR.load_and_verify_alpha_factory_registry(registry_path)
    _req(loaded.is_valid and loaded.snapshot is not None, "ALPHA_REGISTRY_INVALID")
    candidates: dict[str, list[str]] = {}
    episodes: dict[str, list[str]] = {}
    for entry in loaded.snapshot.entries:
        record = entry.record
        refs = getattr(record, "subject_refs", None)
        if refs is not None:
            candidates[record.candidate_id] = sorted(r for r in refs if r in market_ids)
        elif getattr(record, "research_episode_id", None) and getattr(record, "candidate_id", None):
            episodes.setdefault(record.candidate_id, []).append(record.research_episode_id)
    by_market: dict[str, dict] = {}
    for cid in sorted(candidates):
        for market in candidates[cid]:
            link = by_market.setdefault(market, {"candidate_ids": [], "research_episode_ids": []})
            link["candidate_ids"].append(cid)
            link["research_episode_ids"] = sorted(set(link["research_episode_ids"]) | set(episodes.get(cid, [])))
    return {"status": "VERIFIED_READ_ONLY", "registry_head_entry_hash": loaded.snapshot.head_entry_hash,
            "by_market": by_market}


def build_proposals(upstream: dict, rows: dict, outcomes: dict, diag: dict, links: dict) -> list[dict]:
    record_sha = {c["case_id"]: c["record_sha256s"] for c in outcomes["cases"]}
    proposals = []
    for group in diag["by_category"]:
        members = sorted(c for c in rows if rows[c]["category"] == group["category"])
        markets = sorted(rows[c]["market_id"] for c in members)
        cands = sorted({cid for m in markets for cid in links["by_market"].get(m, {}).get("candidate_ids", [])})
        eps = sorted({e for m in markets for e in links["by_market"].get(m, {}).get("research_episode_ids", [])})
        body = {
            "kind": "FUTURE_RESEARCH_PROPOSAL", "evidence_group": {"dimension": "category", "value": group["category"]},
            "reasons": proposal_reasons(group), "source_forecast_receipt_id": upstream["forecast_receipt_id"],
            "cohort_membership_sha256": upstream["cohort_membership_sha256"],
            "group_case_ids_sha256": group["case_ids_sha256"],
            "outcome_evidence_sha256": _sha([record_sha[c] for c in members]),
            "alpha_link": {"status": ALPHA_LINKED if cands else ALPHA_UNVERIFIED, "candidate_ids": cands,
                           "research_episode_ids": eps, "registry_head_entry_hash": links["registry_head_entry_hash"]},
            "summary": {k: group[k] for k in ("selected", "scorable", "paired", "sample_status",
                                              "independent_calibration_gap")},
            "authority": "ADVISORY_ONLY_NOT_CANONICAL_ALPHA_QUEUE_NOT_EPISODE_NOT_QUALIFICATION_NOT_SCHEDULED",
        }
        proposals.append({"proposal_id": PROPOSAL_PREFIX + _sha(body), **body})
    proposals.sort(key=lambda p: (REASONS.index(p["reasons"][0]), p["evidence_group"]["value"]))
    for rank, p in enumerate(proposals, 1):
        p["priority_rank"] = rank  # rank is derived from the ordered bodies, outside each proposal's identity
    return proposals


# ------------------------------------------------------------------ receipt core


def build_learning_core(forecast_receipt: dict, frozen_cases: dict, packet: dict, links: dict, code_identity: str,
                        input_hashes: dict) -> dict:
    core = forecast_receipt["core"]
    validate_packet(packet, forecast_receipt["receipt_id"])
    selected = core["cohort"]["selected_case_ids"]
    rows = {r["case_id"]: r for r in core["targets"] if r["status"] == "SELECTED"}
    _req(sorted(rows) == selected and sorted(core["forecasts"]) == selected, "FORECAST_COHORT_INCONSISTENT")
    priors = {t["case_id"]: t["outcome"] for t in frozen_cases["targets"]
              if isinstance(t, dict) and type(t.get("case_id")) is str and t["case_id"] in rows}
    _req(sorted(priors) == selected, "FORECAST_COHORT_INCONSISTENT")
    upstream = {"forecast_receipt_id": forecast_receipt["receipt_id"], "forecast_verify_status": "VERIFIED",
                "forecast_code_identity": core["code_identity"], "forecast_corpus_class": core["corpus_class"],
                "grounding_receipt_id": core["source_grounding"]["receipt_id"],
                "alpha_universe_snapshot_id": core["source_grounding"]["alpha_universe_snapshot_id"],
                "original_scoring_cutoff": core["inputs"]["scoring_cutoff"],
                "cohort_membership_sha256": core["cohort"]["membership_sha256"], "selected": len(selected),
                "original_scoring_snapshot_sha256": _sha(core["scoring"]),
                "original_forecasts_sha256": _sha(core["forecasts"]),
                "original_scoring_status": "UNCHANGED_HISTORICAL_SNAPSHOT"}
    outcomes = join_outcomes(packet, rows, priors, EVIDENCE_CLASS[core["corpus_class"]])
    scoring, paired = score_frozen(core["forecasts"], outcomes, rows)
    diag = diagnostics(rows, core["forecasts"], outcomes, scoring, paired)
    proposals = build_proposals(upstream, rows, outcomes, diag, links)
    learning = {
        "schema_id": RECEIPT_SCHEMA, "wp_id": WP_ID, "posture": "RESEARCH_ONLY", "score_status": "DIAGNOSTIC_ONLY",
        "write_policy": "NO_CANONICAL_WRITE", "caller": CALLER, "code_identity": code_identity, "upstream": upstream,
        "inputs": {"file_sha256": input_hashes, "packet_sha256": _sha(packet), "packet_label": packet["packet_label"]},
        "outcomes": outcomes, "scoring": scoring, "diagnostics": diag,
        "alpha": {"status": links["status"], "registry_head_entry_hash": links["registry_head_entry_hash"]},
        "proposals": proposals,
        "authority": {"research_only": True, "diagnostic_only": True, "no_canonical_write": True,
                      "alpha_registry_written": False, "research_episode_created": False, "qualification_changed": False,
                      "wp170_evidence_promoted": False, "pit_written": False, "scheduled": False, "refit": False,
                      "settlement_origin_verified": False, "oos_lift_claim": False, "real_value_verified": False,
                      "wang_is_exogenous": False, "strategy": False, "paper": False, "orders": False, "live": False,
                      "llm_or_hermes": False, "network_calls": 0, "provider_calls": 0, "credentials": False,
                      "capital_usd": "0"},
        "adoption": {"learning_loop": "FUNCTIONAL_LOOP_INTEGRATED_OFFLINE_NOT_VALUE_VERIFIED",
                     "tracked_capability_ids": 36, "capability_status_changes": 0, "provider_lanes": list(PROVIDER_LANES),
                     "provider_lane_status": "UNCHANGED_SIX_OWNER_GATED",
                     "R3-10-WANG": "MARKET_PRICE_DERIVED_NEVER_INDEPENDENT", "value_status": "NO_REAL_VALUE_VERIFIED"},
    }
    return json.loads(SG.canonical_bytes(learning))


def finalize_receipt(core: dict) -> dict:
    return {"core": core, "receipt_id": RECEIPT_PREFIX + _sha(core)}


def verify_receipt(receipt: object, recomputed_core: dict) -> list[str]:
    """Failure codes only (never input values); empty list means verified."""
    if not isinstance(receipt, dict) or set(receipt) != {"core", "receipt_id"} or not isinstance(receipt["core"], dict):
        return ["RECEIPT_SHAPE_INVALID"]
    failures = []
    if receipt["receipt_id"] != RECEIPT_PREFIX + _sha(receipt["core"]):
        failures.append("RECEIPT_ID_MISMATCH")
    if receipt["core"] != recomputed_core:
        failures.extend(f"OUTPUT_MISMATCH:{k}" for k in sorted(set(recomputed_core) | set(receipt["core"]))
                        if receipt["core"].get(k) != recomputed_core.get(k))
    return failures
