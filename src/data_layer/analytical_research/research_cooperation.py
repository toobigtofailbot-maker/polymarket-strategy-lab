"""Offline two-role research cooperation with grounded citations (S10-R3-HERMES-COOP-01).

A FORECASTER and a FALSIFIER research submission, both supplied by the CALLER, are checked
against one cold-verified S10-R3-SRC-01 grounding snapshot:

* scope binding: both roles must carry the exact question, native market, optional native
  Alpha candidate, source cutoff, native rule hash and source allowlist of the question;
* citation ledger: only SRC-01 ACCEPTED sources get a stable integer index; each claim's
  ``source_label -> raw_evidence_reference_id -> content_sha256 -> literal excerpt`` chain must
  hold against the frozen admitted bytes and the cutoff;
* reconciliation: evidence for / against / uncertain, disagreement and abstention, with no
  vote, probability, truth value or authority.

Pinned upstream methods are ADAPTED as concepts only (no code copied, no dependency):
NousResearch/hermes-agent @345cd2b057a452236de401d3534b8502a7465e8d ``tools/delegate_tool.py``
(parent/child role-result separation; the upstream delegate really spawns child agents, this
module never does) and ``skills/research/grounded-citations/SKILL.md`` (evidence-ledger index
allocation, literal-quote verification; the upstream ledger is mutable profile state, here it
is one immutable receipt).

Role submissions are NOT evidence of real Hermes delegation or independent models/humans:
the origin is always ``CALLER_SUPPLIED_NOT_INDEPENDENTLY_VERIFIED``. A quote match proves byte
correspondence with caller-local source bytes only, never the document's public origin or
the truth of the claim. Native Hermes drafts are validated with the unchanged
``validate_research_draft``; nothing here invokes Hermes, a provider, a model or a socket.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import asdict
import json
from pathlib import Path
import re

from src.data_layer.analytical_research import source_grounding as SG
from src.data_layer.point_in_time_market_research import research_provenance as RP
from src.research_runtime.hermes_controlled_runtime import models as HM

WP_ID = "S10-R3-HERMES-COOP-01"
CASE_SCHEMA = "s10-r3-hermes-coop01-case-v1"
RECEIPT_SCHEMA = "s10-r3-hermes-coop01-receipt-v1"
RECEIPT_PREFIX = "hermescoop:sha256:"
METHOD_ID = "two_role_cooperation_v1"
BASELINE_ID = "baseline_single_role_v0"
CALLER = ("tools/alpha/run_hermes_cooperation.py:run -> run_source_grounding.verify -> source_grounding.load_corpus/"
          "bind_rule_texts/evaluate_sources/join_alpha_candidates -> research_cooperation.build_core")
ROLES = ("FORECASTER", "FALSIFIER")
STANCES = ("FOR", "AGAINST", "UNCERTAIN")
OPPOSITE_STANCE = {"FOR": "AGAINST", "AGAINST": "FOR"}  # UNCERTAIN never contradicts
SPECIALIST_ORIGIN = "CALLER_SUPPLIED_NOT_INDEPENDENTLY_VERIFIED"
SOURCE_ORIGIN = "SOURCE_ORIGIN_UNVERIFIED"
POSTURE_FLAGS = ("OFFLINE_RESEARCH_ONLY", "CITATION_INTEGRITY_NOT_FACT_TRUTH", "ROLE_ORIGIN_NOT_VERIFIED",
                 "NO_PROVIDER_OR_TRADING_AUTHORITY")

# Bounds (per case file / per question); fixed before the benchmark corpus was written.
MAX_QUESTIONS = 64
MAX_SUBMISSIONS = 4
MAX_CLAIMS_PER_QUESTION = 64
MAX_CITATIONS_PER_ROLE = 16
MAX_ALLOWLIST = 32
EXCERPT_MIN, EXCERPT_MAX = 12, 500
CLAIM_TEXT_MAX = 1000
BENCHMARK_MIN_CASES = 40

SUPPORTED = "SUPPORTED_QUOTE_PRESENT"
CONTRADICTED = "CONTRADICTED_BY_OTHER_ROLE"
UNSUPPORTED = "UNSUPPORTED_OR_UNCITED"
UNAVAILABLE = "SOURCE_UNAVAILABLE"
POST_CUTOFF = "POST_CUTOFF"
UNKNOWN = "UNKNOWN"
CLAIM_STATUSES = (SUPPORTED, CONTRADICTED, UNSUPPORTED, UNAVAILABLE, POST_CUTOFF, UNKNOWN)
DEFECTIVE = (UNSUPPORTED, UNAVAILABLE, POST_CUTOFF, UNKNOWN)
OUTCOMES = ("QUESTION_INVALID", "ABSTAINED_MISSING_ROLE", "ABSTAINED_ROLE_INVALID", "INCONCLUSIVE",
            "DISAGREEMENT_REVIEW_REQUIRED", "CITATIONS_VERIFIED_REVIEW_REQUIRED")
ABSTAINED = ("ABSTAINED_MISSING_ROLE", "ABSTAINED_ROLE_INVALID")
ROLE_EMPTY = "ROLE_EMPTY"  # a role with no claims is treated as missing, never as silent agreement

CASE_KEYS = {"schema_id", "case_label", "corpus_class", "grounding_receipt_id", "as_of", "benchmark_sha256", "questions"}
SCOPE_KEYS = ("question_id", "market_id", "candidate_id", "source_cutoff", "rule_sha256", "source_allowlist")
QUESTION_KEYS = {*SCOPE_KEYS, "labels", "submissions"}
LABEL_KEYS = {"counterevidence_in_corpus", "conflict_present"}
SUBMISSION_KEYS = {"role", "response_id", "declared_origin", "scope", "native_draft", "claims"}
CLAIM_KEYS = {"claim_id", "proposition_id", "stance", "text", "citations"}
CITATION_KEYS = {"source_label", "excerpt"}
# Prompt/tool/permission/model-control keys are never research content.
CONTROL_KEY_PARTS = ("prompt", "tool", "permission", "stderr", "command", "delegat", "toolset", "hermes_home")
_RECEIPT_ID_RE = re.compile(re.escape(SG.RECEIPT_PREFIX) + r"[0-9a-f]{64}")
_URL_OR_PATH_RE = re.compile(r"(?i)(\b[a-z][a-z0-9+.-]*://|\bwww\.|\b[a-z]:[\\/]|(^|\s)~?/[^\s/]+/|\\\\)")
_INSTRUCTION_RE = re.compile(r"(?i)(ignore (all |any )?(the )?(previous|prior|above) instructions|disregard (all |any )?"
                             r"(previous|prior|the) |you are now|system prompt|developer message|run the following|"
                             r"execute the following|call the tool|<\s*/?\s*(system|tool)\s*>)")


class CoopStop(SG.GroundingStop):
    """Whole-run fail-closed stop; subclass so SRC-01 style handlers catch it too."""


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise CoopStop(code)


def _utc(value: object) -> str | None:
    """Exact canonical UTC text, or None (a non-canonical spelling is not accepted)."""
    if type(value) is not str:
        return None
    try:
        canonical = RP.canonicalize_utc_timestamp(value)
    except ValueError:
        return None
    return canonical if canonical == value else None


def _key(ts: str):
    return RP._utc_instant_key(ts)


def _qid(value: object) -> bool:
    return type(value) is str and SG._QID_RE.fullmatch(value) is not None


def _label(value: object) -> bool:
    return type(value) is str and SG._LABEL_RE.fullmatch(value) is not None


def _sha_text(value: str) -> str:
    return SG.sha256_hex(value.encode("utf-8"))


# ------------------------------------------------------------------ whole-case validation


def _scan_keys(value: object, depth: int = 0) -> None:
    """Credential-, trade- or control-shaped keys anywhere reject the whole case.

    A native Hermes draft is skipped here: its fixed schema legitimately names authority
    flags (``no_credential_request``...) and is validated by the native validator instead.
    """
    _require(depth <= 10, "CASE_TOO_DEEP")
    if isinstance(value, dict):
        for key, item in value.items():
            _require(isinstance(key, str), "CASE_FIELDS_INVALID")
            lowered = key.casefold()
            _require(not any(p in lowered for p in SG.SECRET_KEY_PARTS + CONTROL_KEY_PARTS), "FORBIDDEN_FIELD")
            _require(not set(re.split(r"[^a-z0-9]+", lowered)) & set(SG.TRADE_KEY_WORDS), "FORBIDDEN_FIELD")
            if key != "native_draft":
                _scan_keys(item, depth + 1)
    elif isinstance(value, list):
        for item in value:
            _scan_keys(item, depth + 1)


def validate_case(case: object) -> None:
    _require(isinstance(case, dict), "CASE_JSON_INVALID")
    _scan_keys(case)
    _require(set(case) == CASE_KEYS, "CASE_FIELDS_INVALID")
    _require(case["schema_id"] == CASE_SCHEMA, "CASE_SCHEMA_INVALID")
    _require(_label(case["case_label"]), "CASE_LABEL_INVALID")
    _require(case["corpus_class"] in SG.CORPUS_CLASSES, "CORPUS_CLASS_INVALID")
    _require(type(case["grounding_receipt_id"]) is str and _RECEIPT_ID_RE.fullmatch(case["grounding_receipt_id"]) is not None,
             "GROUNDING_RECEIPT_ID_INVALID")
    _require(_utc(case["as_of"]) is not None, "AS_OF_INVALID")
    _require(type(case["benchmark_sha256"]) is str and SG._SHA_RE.fullmatch(case["benchmark_sha256"]) is not None,
             "BENCHMARK_SHA_INVALID")
    _require(type(case["questions"]) is list and 0 < len(case["questions"]) <= MAX_QUESTIONS, "QUESTIONS_INVALID")


def benchmark_commitment(case: dict) -> str:
    """Self-commitment over method ids, bounds and every complete question (labels, roles, claims, quotes).

    It binds the case file to itself; the external pre-method pin is the corpus SHA-256 in the tests.
    """
    return SG.sha256_hex(SG.canonical_bytes({"method_id": METHOD_ID, "baseline_id": BASELINE_ID,
                                             "min_cases": BENCHMARK_MIN_CASES, "questions": case["questions"]}))


# ------------------------------------------------------------------ grounding context (native SRC-01, read-only)


def cutoff_refusal(entry: dict, cutoff: str) -> str | None:
    """SRC-01's own clock and native replay-admissibility rules, re-applied at the question cutoff.

    None means admissible at ``cutoff``; ``entry`` is an SRC-01 ACCEPTED frozen source entry.
    """
    clocks = {k: SG._clock(entry[k]) for k in ("source_publish_time", "public_available_time", "local_first_seen_time",
                                               "ingestion_time", "revision_time")}
    later_import = entry["capture_mode"] == "LATER_IMPORT"
    published = [clocks[k] for k in ("source_publish_time", "public_available_time") if clocks[k]]
    if any(_key(t) > _key(cutoff) for t in published):
        return "AVAILABLE_AFTER_CUTOFF"
    if not later_import and _key(clocks["ingestion_time"]) > _key(cutoff):
        return "INGESTED_AFTER_CUTOFF"
    evidence = RP.ObservabilityEvidence(
        local_first_seen_time=None if later_import else clocks["local_first_seen_time"],
        public_available_time=clocks["public_available_time"],
        is_correction_after_cutoff=bool(clocks["revision_time"]) and _key(clocks["revision_time"]) > _key(cutoff),
        is_backfilled=later_import)
    verdict = RP.evaluate_replay_admissibility(cutoff, evidence)
    return None if verdict.status == "ADMISSIBLE" else "NOT_ADMISSIBLE_AT_CUTOFF:" + str(verdict.basis)


def grounding_context(frozen_case: dict, inputs_dir: Path) -> dict:
    """Rebuild the admitted-source ledger from a VERIFIED frozen SRC-01 scratch (inputs/ folder)."""
    SG.validate_case(frozen_case, frozen=True)
    as_of = RP.canonicalize_utc_timestamp(frozen_case["as_of"])
    inputs_dir = Path(inputs_dir)

    def read(rel: object) -> bytes:
        path = inputs_dir / rel if type(rel) is str else None
        return path.read_bytes() if path is not None and path.is_file() and not path.is_symlink() else b""
    policy, universe = SG.load_corpus(inputs_dir / "pit.sqlite3", frozen_case["policy"], as_of)
    rules, _ = SG.bind_rule_texts(universe, frozen_case["rule_texts"], read)
    outcomes, _ = SG.evaluate_sources(frozen_case["sources"], universe, as_of, read)
    registry = inputs_dir / frozen_case["alpha_registry"] if frozen_case["alpha_registry"] else None
    alpha = SG.join_alpha_candidates(registry, universe)
    ledger, unavailable, raw_by_label, url_by_label, entry_by_label = {}, {}, {}, {}, {}
    for outcome, entry in zip(outcomes, frozen_case["sources"]):
        label = outcome["source_label"]
        if label is None:
            continue
        if outcome["status"] != "ACCEPTED":
            unavailable[label] = outcome["reason"] or outcome["status"]
            continue
        raw = read(entry["file"])
        intact = bool(raw) and SG.sha256_hex(raw) == outcome["content_sha256"]
        ledger[label] = {"source_label": label, "market_id": outcome["market_id"],
                         "raw_evidence_reference_id": outcome["raw_evidence_reference_id"],
                         "content_sha256": outcome["content_sha256"], "byte_length": outcome["byte_length"],
                         "capture_mode": entry["capture_mode"],
                         "evidence_bytes": "AVAILABLE" if intact else "EVIDENCE_BYTES_UNAVAILABLE",
                         "url_sha256": _sha_text(entry["url"]), "source_origin": SOURCE_ORIGIN}
        raw_by_label[label] = raw if intact else b""
        url_by_label[label] = entry["url"]
        entry_by_label[label] = entry
    for number, label in enumerate(sorted(ledger), start=1):
        ledger[label]["citation_index"] = number
    candidates: dict[str, set] = {}
    for joined in alpha["joined"]:
        for market_id in joined["market_ids"]:
            candidates.setdefault(market_id, set()).add(joined["candidate_id"])
    return {"as_of": as_of, "corpus_class": frozen_case["corpus_class"],
            "market_ids": {m.market_id for m in universe.markets},
            "rule_sha256": {m: r["rule_content_sha256"] for m, r in rules.items()},
            "candidates": candidates, "ledger": ledger, "unavailable": unavailable,
            "raw": raw_by_label, "url": url_by_label, "entry": entry_by_label,
            "summary": {"alpha_discovery_policy_id": policy.alpha_discovery_policy_id,
                        "alpha_universe_snapshot_id": universe.alpha_universe_snapshot_id,
                        "alpha_join": alpha["status"], "rule_text_bound": len(rules),
                        "sources_unavailable": dict(sorted(unavailable.items()))}}


# ------------------------------------------------------------------ claims and citations


def _citation(cit: object, question: dict, ctx: dict) -> dict:
    row = {"citation_index": None, "source_label": None, "excerpt_sha256": None, "status": UNSUPPORTED,
           "reason": None, "quote_verified": None}
    if not isinstance(cit, dict) or set(cit) != CITATION_KEYS or not _label(cit["source_label"]) \
            or type(cit["excerpt"]) is not str or not EXCERPT_MIN <= len(cit["excerpt"]) <= EXCERPT_MAX:
        row["reason"] = "CITATION_FIELDS_INVALID"
        return row
    label, excerpt = cit["source_label"], cit["excerpt"]
    row.update(source_label=label, excerpt_sha256=_sha_text(excerpt))
    led = ctx["ledger"].get(label)
    if _URL_OR_PATH_RE.search(excerpt):
        row["reason"] = "CLAIM_CONTAINS_URL_OR_PATH"
    elif label not in question["source_allowlist"]:
        row["reason"] = "SOURCE_NOT_ALLOWLISTED"
    elif label in ctx["unavailable"]:
        row.update(status=UNAVAILABLE, reason="SRC01_" + ctx["unavailable"][label])
    elif led is None:
        row["reason"] = "UNKNOWN_SOURCE_REF"
    elif led["evidence_bytes"] != "AVAILABLE":
        row.update(citation_index=led["citation_index"], status=UNAVAILABLE, reason="EVIDENCE_BYTES_UNAVAILABLE")
    elif led["market_id"] != question["market_id"]:
        row.update(citation_index=led["citation_index"], reason="SOURCE_NOT_BOUND_TO_MARKET")
    elif (late := cutoff_refusal(ctx["entry"][label], question["source_cutoff"])) is not None:
        row.update(citation_index=led["citation_index"], status=POST_CUTOFF, reason=late)
    elif excerpt.encode("utf-8") not in ctx["raw"][label]:
        row.update(citation_index=led["citation_index"], reason="QUOTE_NOT_FOUND", quote_verified=False)
    else:
        row.update(citation_index=led["citation_index"], status=SUPPORTED, quote_verified=True)
    return row


def _claim(claim: object, question: dict, ctx: dict, seen_ids: set) -> dict:
    row = {"claim_id": None, "proposition_id": None, "stance": None, "text_sha256": None, "status": UNSUPPORTED,
           "reason": None, "citations": []}
    if not isinstance(claim, dict) or set(claim) != CLAIM_KEYS or not _qid(claim["claim_id"]) \
            or not _qid(claim["proposition_id"]) or claim["stance"] not in STANCES or type(claim["text"]) is not str \
            or not claim["text"].strip() or len(claim["text"]) > CLAIM_TEXT_MAX or type(claim["citations"]) is not list:
        row["reason"] = "CLAIM_FIELDS_INVALID"
        return row
    row.update(claim_id=claim["claim_id"], proposition_id=claim["proposition_id"], stance=claim["stance"],
               text_sha256=_sha_text(claim["text"]))
    excerpts = [c["excerpt"] for c in claim["citations"] if isinstance(c, dict) and type(c.get("excerpt")) is str]
    pairs = [SG.canonical_bytes(c) for c in claim["citations"]]  # hashable even for malformed citation values
    row["citations"] = [_citation(c, question, ctx) for c in claim["citations"]]
    if claim["claim_id"] in seen_ids:
        row["reason"] = "DUPLICATE_CLAIM_ID"
    elif _URL_OR_PATH_RE.search(claim["text"]):
        row["reason"] = "CLAIM_CONTAINS_URL_OR_PATH"
    elif any(_INSTRUCTION_RE.search(t) for t in [claim["text"], *excerpts]):
        row.update(status=UNKNOWN, reason="INSTRUCTION_SHAPED_CONTENT_NOT_EVIDENCE")
    elif not claim["citations"]:
        row["reason"] = "UNCITED"
    elif len(set(pairs)) != len(pairs):
        row["reason"] = "DUPLICATE_CITATION"
    else:
        failing = [c for c in row["citations"] if c["status"] != SUPPORTED]
        if failing:
            # Fixed precedence: unavailable source, then cutoff, then unsupported / unverified quote.
            worst = min(failing, key=lambda c: (UNAVAILABLE, POST_CUTOFF, UNSUPPORTED).index(c["status"]))
            row.update(status=worst["status"], reason=worst["reason"])
        else:
            row["status"] = SUPPORTED
    seen_ids.add(claim["claim_id"])
    return row


# ------------------------------------------------------------------ roles


def _native_draft(draft: dict, response_id: str, question: dict, ctx: dict, claims: list) -> str | None:
    """Unchanged native validator; returns a refusal reason or None. Validation never executes anything.

    The scored claims must cite only sources the validated draft itself references.
    """
    try:
        validated = HM.validate_research_draft(SG.canonical_bytes(draft), expected_request_id=response_id,
                                               max_sources=min(max(len(question["source_allowlist"]), 1),
                                                               HM.MAX_SOURCES_ABSOLUTE))
    except HM.HermesResearchError as error:
        return "NATIVE_DRAFT_REJECTED:" + error.code
    sanctioned = {ctx["url"][s] for s in question["source_allowlist"] if s in ctx["url"]}
    if any(url not in sanctioned for url in validated.source_urls):
        return "NATIVE_DRAFT_SOURCE_NOT_SANCTIONED"
    cited = {c.get("source_label") for claim in claims if isinstance(claim, dict) and type(claim.get("citations")) is list
             for c in claim["citations"] if isinstance(c, dict)}
    if any(type(s) is not str or ctx["url"].get(s) not in validated.source_urls for s in cited):
        return "NATIVE_DRAFT_CLAIM_SOURCE_UNBOUND"
    return None


def _submission(sub: object, question: dict, ctx: dict) -> dict:
    row = {"role": None, "response_id_sha256": None, "declared_origin": None, "submission_format": None,
           "status": "ROLE_INVALID", "reason": None, "specialist_origin": SPECIALIST_ORIGIN,
           "execution_provenance": "ABSENT_NO_HERMES_INVOCATION", "_claims": None, "_response_id": None}
    if not isinstance(sub, dict) or set(sub) != SUBMISSION_KEYS or sub["role"] not in ROLES or not _qid(sub["response_id"]) \
            or not (sub["declared_origin"] is None or _label(sub["declared_origin"])) \
            or not (sub["native_draft"] is None or isinstance(sub["native_draft"], dict)) or type(sub["claims"]) is not list:
        row["reason"] = "SUBMISSION_FIELDS_INVALID"
        return row
    row.update(role=sub["role"], response_id_sha256=_sha_text(sub["response_id"]), declared_origin=sub["declared_origin"],
               submission_format="NATIVE_HERMES_DRAFT_V1" if sub["native_draft"] is not None else "CALLER_ROLE_SCHEMA_V1",
               _response_id=sub["response_id"])
    if sub["scope"] != {k: question[k] for k in SCOPE_KEYS}:
        row["reason"] = "SCOPE_MISMATCH"
    elif not sub["claims"]:
        row["reason"] = ROLE_EMPTY
    elif sum(len(c["citations"]) for c in sub["claims"] if isinstance(c, dict) and type(c.get("citations")) is list) \
            > MAX_CITATIONS_PER_ROLE:
        row["reason"] = "ROLE_CITATION_LIMIT"
    elif sub["native_draft"] is not None and (reason := _native_draft(sub["native_draft"], sub["response_id"], question, ctx,
                                                                   sub["claims"])):
        row["reason"] = reason
    else:
        row.update(status="ROLE_ADMITTED", _claims=sub["claims"])
    return row


def _evaluate(roles: list[dict], question: dict, ctx: dict, rule_conflict: bool) -> dict:
    """One method over admitted role rows (1 role = baseline, 2 roles = cooperation)."""
    claims = []
    for role in roles:
        seen: set = set()
        claims.extend(dict(_claim(c, question, ctx, seen), role=role["role"]) for c in role["_claims"])
    supported = [c for c in claims if c["status"] == SUPPORTED]
    by_prop: dict[tuple, set] = {}
    for c in supported:
        by_prop.setdefault((c["proposition_id"], c["stance"]), set()).add(c["role"])
    for c in supported:
        other = OPPOSITE_STANCE.get(c["stance"])
        if other and by_prop.get((c["proposition_id"], other), set()) - {c["role"]}:
            c["status"], c["reason"] = CONTRADICTED, "OPPOSITE_STANCE_SAME_PROPOSITION_OTHER_ROLE"
    disagreement = any(c["status"] == CONTRADICTED for c in claims)
    defects = [c for c in claims if c["status"] in DEFECTIVE]
    quoted = [c for c in claims if c["status"] in (SUPPORTED, CONTRADICTED)]
    if rule_conflict:
        outcome, reason = "INCONCLUSIVE", "RULE_CONFLICT"
    elif not quoted:
        outcome, reason = "INCONCLUSIVE", "NO_VALID_CITATIONS"
    elif defects:
        outcome, reason = "INCONCLUSIVE", "CLAIM_EVIDENCE_DEFECT"
    elif disagreement:
        outcome, reason = "DISAGREEMENT_REVIEW_REQUIRED", "ROLES_CITE_OPPOSITE_STANCES"
    else:
        outcome, reason = "CITATIONS_VERIFIED_REVIEW_REQUIRED", None
    pairs = {(x["source_label"], x["excerpt_sha256"]) for c in quoted for x in c["citations"]}
    return {"outcome": outcome, "reason": reason, "disagreement_detected": disagreement,
            "claims": claims, "claim_status_counts": dict(sorted(Counter(c["status"] for c in claims).items())),
            "evidence": {s.casefold(): sum(1 for c in quoted if c["stance"] == s) for s in STANCES},
            "falsifier_against_quoted": sum(1 for c in quoted if c["role"] == "FALSIFIER" and c["stance"] == "AGAINST"),
            "distinct_quoted_sources": len({p[0] for p in pairs}), "distinct_support_pairs": len(pairs),
            "reviewer_action": "HUMAN_REVIEW_REQUIRED", "semantic_fact_verification": "NOT_AUTOMATICALLY_VERIFIED",
            "source_origin": SOURCE_ORIGIN}


def _abstain(outcome: str, reason: str) -> dict:
    return {"outcome": outcome, "reason": reason, "disagreement_detected": False, "claims": [], "claim_status_counts": {},
            "evidence": {s.casefold(): 0 for s in STANCES}, "falsifier_against_quoted": 0, "distinct_quoted_sources": 0,
            "distinct_support_pairs": 0, "reviewer_action": "HUMAN_REVIEW_REQUIRED",
            "semantic_fact_verification": "NOT_AUTOMATICALLY_VERIFIED", "source_origin": SOURCE_ORIGIN}


def _abstain_outcome(reason: str) -> str:
    return "ABSTAINED_MISSING_ROLE" if reason == ROLE_EMPTY else "ABSTAINED_ROLE_INVALID"


def _question_fields_ok(q: object, ctx: dict) -> str | None:
    if not isinstance(q, dict) or set(q) != QUESTION_KEYS or not _qid(q["question_id"]) or type(q["market_id"]) is not str \
            or not (q["candidate_id"] is None or type(q["candidate_id"]) is str) \
            or _utc(q["source_cutoff"]) is None or not (q["rule_sha256"] is None or (
                type(q["rule_sha256"]) is str and SG._SHA_RE.fullmatch(q["rule_sha256"]))) \
            or type(q["source_allowlist"]) is not list or len(q["source_allowlist"]) > MAX_ALLOWLIST \
            or not all(_label(s) for s in q["source_allowlist"]) or len(set(q["source_allowlist"])) != len(q["source_allowlist"]) \
            or not isinstance(q["labels"], dict) or set(q["labels"]) != LABEL_KEYS \
            or any(type(v) is not bool for v in q["labels"].values()) \
            or type(q["submissions"]) is not list or len(q["submissions"]) > MAX_SUBMISSIONS:
        return "QUESTION_FIELDS_INVALID"
    if _key(q["source_cutoff"]) > _key(ctx["as_of"]):
        return "SOURCE_CUTOFF_AFTER_GROUNDING_AS_OF"
    if q["market_id"] not in ctx["market_ids"]:
        return "MARKET_NOT_IN_GROUNDING_CORPUS"
    if q["candidate_id"] is not None and q["candidate_id"] not in ctx["candidates"].get(q["market_id"], set()):
        return "CANDIDATE_NOT_NATIVE_FOR_MARKET"
    if sum(len(s["claims"]) for s in q["submissions"] if isinstance(s, dict) and type(s.get("claims")) is list) \
            > MAX_CLAIMS_PER_QUESTION:
        return "QUESTION_CLAIM_LIMIT"
    return None


def assess_question(index: int, q: object, ctx: dict, seen_questions: set) -> dict:
    qid = q.get("question_id") if isinstance(q, dict) and _qid(q.get("question_id")) else None
    row = {"index": index, "question_id": qid, "market_id": None, "status": "VALID", "reason": None,
           "rule_binding": None, "source_presence": None, "labels": None, "roles": []}
    reason = _question_fields_ok(q, ctx) or ("DUPLICATE_QUESTION_ID" if qid in seen_questions else None)
    if qid:
        seen_questions.add(qid)
    if reason:
        row.update(status="QUESTION_INVALID", reason=reason)
        invalid = _abstain("QUESTION_INVALID", reason)
        return dict(row, baseline=invalid, cooperation=invalid)
    native_rule = ctx["rule_sha256"].get(q["market_id"])
    rule_conflict = q["rule_sha256"] != native_rule
    present = any(s in ctx["ledger"] and ctx["ledger"][s]["market_id"] == q["market_id"] for s in q["source_allowlist"])
    if rule_conflict:
        rule_binding = "RULE_CONFLICT"
    elif native_rule:
        rule_binding = "NATIVE_RULE_MATCH"
    else:
        rule_binding = "NO_NATIVE_RULE"
    row.update(market_id=q["market_id"], labels=dict(q["labels"]), source_presence="PRESENT" if present else "ABSENT",
               rule_binding=rule_binding)
    roles = [_submission(s, q, ctx) for s in q["submissions"]]
    row["roles"] = [{k: v for k, v in r.items() if not k.startswith("_")} for r in roles]
    forecasters = [r for r in roles if r["role"] == "FORECASTER"]
    falsifiers = [r for r in roles if r["role"] == "FALSIFIER"]
    # baseline_single_role_v0: the FORECASTER submission alone through the same citation checker.
    if not forecasters:
        baseline = _abstain("ABSTAINED_MISSING_ROLE", "FORECASTER_MISSING")
    elif len(forecasters) > 1:
        baseline = _abstain("ABSTAINED_ROLE_INVALID", "DUPLICATE_ROLE")
    elif forecasters[0]["status"] != "ROLE_ADMITTED":
        baseline = _abstain(_abstain_outcome(forecasters[0]["reason"]), forecasters[0]["reason"])
    else:
        baseline = _evaluate(forecasters, q, ctx, rule_conflict)
    invalid = [r for r in roles if r["status"] != "ROLE_ADMITTED"]
    origins = [r["declared_origin"] for r in roles if r["declared_origin"] is not None]
    if invalid:
        cooperation = _abstain(_abstain_outcome(invalid[0]["reason"]), invalid[0]["reason"])
    elif len(forecasters) > 1 or len(falsifiers) > 1:
        cooperation = _abstain("ABSTAINED_ROLE_INVALID", "DUPLICATE_ROLE")
    elif not forecasters or not falsifiers:
        cooperation = _abstain("ABSTAINED_MISSING_ROLE", "FALSIFIER_MISSING" if forecasters else "FORECASTER_MISSING")
    elif forecasters[0]["_response_id"] == falsifiers[0]["_response_id"]:
        cooperation = _abstain("ABSTAINED_ROLE_INVALID", "SAME_RESPONSE_ID_BOTH_ROLES")
    elif len(set(origins)) != len(origins):
        cooperation = _abstain("ABSTAINED_ROLE_INVALID", "SAME_DECLARED_EXECUTION_ORIGIN_BOTH_ROLES")
    else:
        cooperation = _evaluate([forecasters[0], falsifiers[0]], q, ctx, rule_conflict)
    return dict(row, baseline=baseline, cooperation=cooperation)


# ------------------------------------------------------------------ benchmark


def _method_counts(rows: list, key: str) -> dict:
    methods = [r[key] for r in rows]
    claims = [c for m in methods for c in m["claims"]]
    cites = [x for c in claims for x in c["citations"]]
    labelled = [(r["labels"], r[key]) for r in rows]
    status = Counter(c["status"] for c in claims)
    return {
        "cases": len(methods),
        "evaluated": sum(1 for m in methods if m["outcome"] not in ABSTAINED),
        "abstained": sum(1 for m in methods if m["outcome"] in ABSTAINED),
        "outcomes": dict(sorted(Counter(m["outcome"] for m in methods).items())),
        "claims_total": len(claims),
        "claims_cited": sum(1 for c in claims if c["citations"]),
        "claims_uncited": sum(1 for c in claims if not c["citations"]),
        "claims_by_status": {s: status.get(s, 0) for s in CLAIM_STATUSES},
        "citations_total": len(cites),
        "quote_verified": sum(1 for x in cites if x["quote_verified"] is True),
        "quote_false": sum(1 for x in cites if x["quote_verified"] is False),
        "citations_unsupported_source": sum(1 for x in cites if x["reason"] in (
            "UNKNOWN_SOURCE_REF", "SOURCE_NOT_ALLOWLISTED", "SOURCE_NOT_BOUND_TO_MARKET")),
        "citations_source_unavailable": sum(1 for x in cites if x["status"] == UNAVAILABLE),
        "citations_post_cutoff": sum(1 for x in cites if x["status"] == POST_CUTOFF),
        "quoted_claim_coverage": SG._ratio(status.get(SUPPORTED, 0) + status.get(CONTRADICTED, 0), len(claims)),
        "conflict_found": sum(1 for lab, m in labelled if lab["conflict_present"] and m["disagreement_detected"]),
        "conflict_missed": sum(1 for lab, m in labelled if lab["conflict_present"] and not m["disagreement_detected"]),
        "conflict_false_alarm": sum(1 for lab, m in labelled if not lab["conflict_present"] and m["disagreement_detected"]),
        "counterevidence_surfaced": sum(1 for lab, m in labelled if lab["counterevidence_in_corpus"]
                                        and m["evidence"]["against"] > 0),
        "counterevidence_missed": sum(1 for lab, m in labelled if lab["counterevidence_in_corpus"]
                                      and m["evidence"]["against"] == 0),
        "cost": {"classification": "LOCAL_CPU_ONLY", "provider_calls": 0, "network_calls": 0, "model_calls": 0,
                 "spend_usd": "0"},
    }


def run_benchmark(rows: list) -> dict:
    valid = [r for r in rows if r["status"] == "VALID"]
    both = [r for r in valid if r["baseline"]["outcome"] not in ABSTAINED and r["cooperation"]["outcome"] not in ABSTAINED]
    one = [r for r in valid if (r["baseline"]["outcome"] in ABSTAINED) != (r["cooperation"]["outcome"] in ABSTAINED)]
    status = "COMPLETED" if len(valid) >= BENCHMARK_MIN_CASES else "BENCHMARK_REFUSED"
    return {
        "status": status,
        "refusal_reason": None if status == "COMPLETED" else "FEWER_THAN_FORTY_VALID_CASES",
        "denominators": {
            "cases_total": len(rows), "cases_eligible": len(valid), "cases_invalid": len(rows) - len(valid),
            "invalid_by_reason": dict(sorted(Counter(r["reason"] for r in rows if r["status"] != "VALID").items())),
            "source_present": sum(1 for r in valid if r["source_presence"] == "PRESENT"),
            "source_absent": sum(1 for r in valid if r["source_presence"] == "ABSENT"),
            "rule_conflict": sum(1 for r in valid if r["rule_binding"] == "RULE_CONFLICT"),
            "valid_paired": len(both), "comparison_only": len(one),
            "both_abstained": len(valid) - len(both) - len(one),
            "labelled_conflict_present": sum(1 for r in valid if r["labels"]["conflict_present"]),
            "labelled_counterevidence_in_corpus": sum(1 for r in valid if r["labels"]["counterevidence_in_corpus"]),
        },
        "metrics": None if status != "COMPLETED" else {BASELINE_ID: _method_counts(valid, "baseline"),
                                                       METHOD_ID: _method_counts(valid, "cooperation")},
        "paired_metrics": None if status != "COMPLETED" else {BASELINE_ID: _method_counts(both, "baseline"),
                                                              METHOD_ID: _method_counts(both, "cooperation")},
        "interpretation": ("Labels were authored with the SANITIZED_SYNTHETIC corpus and a single role cannot "
                           "disagree with itself, so differences measure checker accounting on authored cases, "
                           "not research quality, real-world lift or real Hermes delegation."),
    }


# ------------------------------------------------------------------ receipt


def build_core(case: dict, ctx: dict, code_identity: str, file_sha256: dict, grounding_receipt_id: str,
               timer=None) -> tuple[dict, dict]:
    validate_case(case)
    _require(benchmark_commitment(case) == case["benchmark_sha256"], "BENCHMARK_FREEZE_MISMATCH")
    _require(case["grounding_receipt_id"] == grounding_receipt_id, "GROUNDING_RECEIPT_MISMATCH")
    _require(case["corpus_class"] == ctx["corpus_class"], "CORPUS_CLASS_MISMATCH")
    _require(case["as_of"] == ctx["as_of"], "AS_OF_MISMATCH")
    t0 = timer() if timer else 0
    seen: set = set()
    rows = [assess_question(i, q, ctx, seen) for i, q in enumerate(case["questions"])]
    t1 = timer() if timer else 0
    ledger = sorted(ctx["ledger"].values(), key=lambda e: e["citation_index"])
    core = {
        "schema_id": RECEIPT_SCHEMA, "wp_id": WP_ID, "posture": SG.RESEARCH_ONLY, "posture_flags": list(POSTURE_FLAGS),
        "case_label": case["case_label"], "corpus_class": case["corpus_class"], "caller": CALLER,
        "code_identity": code_identity,
        "source_pins": [
            {"capability": "R3-05", "repository": "NousResearch/hermes-agent",
             "commit": "345cd2b057a452236de401d3534b8502a7465e8d", "files": ["tools/delegate_tool.py"],
             "blob": "272ae0971881c154a624fdfe1d5e3f1269ce9b16", "license": "MIT",
             "adoption_mode": "ADAPT_CONCEPT_NO_CODE_COPIED_NEVER_INVOKED"},
            {"capability": "R3-05-CITATIONS", "repository": "NousResearch/hermes-agent",
             "commit": "345cd2b057a452236de401d3534b8502a7465e8d", "files": ["skills/research/grounded-citations/SKILL.md"],
             "blob": "97c4bce66391e88129287aa0a8f7ed75236ff513", "license": "MIT",
             "adoption_mode": "ADAPT_ALGORITHM_NO_CODE_COPIED"}],
        "method": {"method_id": METHOD_ID, "baseline_id": BASELINE_ID, "roles": list(ROLES), "stances": list(STANCES),
                   "claim_statuses": list(CLAIM_STATUSES), "outcomes": list(OUTCOMES),
                   "limits": {"questions": MAX_QUESTIONS, "submissions_per_question": MAX_SUBMISSIONS,
                              "claims_per_question": MAX_CLAIMS_PER_QUESTION, "citations_per_role": MAX_CITATIONS_PER_ROLE,
                              "allowlist": MAX_ALLOWLIST, "excerpt_chars": [EXCERPT_MIN, EXCERPT_MAX],
                              "claim_text_chars": CLAIM_TEXT_MAX, "benchmark_min_cases": BENCHMARK_MIN_CASES},
                   "quote_rule": "EXACT_UTF8_SUBSTRING_OF_FROZEN_ADMITTED_SOURCE_BYTES",
                   "native_validator": "src.research_runtime.hermes_controlled_runtime.models.validate_research_draft"},
        "inputs": {"as_of": ctx["as_of"], "grounding_receipt_id": grounding_receipt_id,
                   "grounding_verification": "VERIFIED", "benchmark_sha256": case["benchmark_sha256"],
                   "case_sha256": SG.sha256_hex(SG.canonical_bytes(case)), "file_sha256": file_sha256, **ctx["summary"]},
        "source_ledger": ledger,
        "questions": rows,
        "benchmark": run_benchmark(rows),
        "provenance": {"specialist_origin": SPECIALIST_ORIGIN, "source_origin": SOURCE_ORIGIN,
                       "semantic_fact_verification": "NOT_AUTOMATICALLY_VERIFIED",
                       "real_hermes_delegation": "NOT_INVOKED", "independent_model_execution": "NOT_PROVEN"},
        "adoption": {
            "R3-05": "OFFLINE_RESEARCH_COOP_FUNCTIONAL_NOT_REAL_HERMES_DELEGATION_INTEGRATED",
            "R3-05-CITATIONS": "OFFLINE_CITATION_LEDGER_FUNCTIONAL_NOT_VALUE_VERIFIED",
            "R3-29": "PARITY_OPEN_NOT_SELF_CLOSED",
            "reason": ("SANITIZED_SYNTHETIC corpus proves callable behaviour only, never research quality or real delegation"
                       if case["corpus_class"] == "SANITIZED_SYNTHETIC" else
                       "LOCAL_REAL_PIT observation awaits independent review; never self-declared VALUE_VERIFIED"),
            "other_capability_ids": "UNCHANGED_34_OF_36", "parity_candidates_12": "OPEN",
            "provider_lanes": "SIX_SEPARATE_OWNER_GATES_UNCHANGED", "lane_b": "SEPARATE_OWNER_UNCHANGED",
        },
        "authority": {"research_only": True, "forecast_probability": False, "truth_verdict": False, "consensus_vote": False,
                      "strategy": False, "paper": False, "orders": False, "live": False, "capital": False,
                      "store_writes": False, "wp170_registry_writes": False, "hermes_invocation": False,
                      "delegate_task": False, "provider_calls": 0, "model_calls": 0, "network_calls": 0,
                      "credentials": False, "promotion": False},
    }
    return json.loads(SG.canonical_bytes(core)), {METHOD_ID: t1 - t0}


def finalize(core: dict) -> dict:
    core_hash = SG.sha256_hex(SG.canonical_bytes(core))
    ledger = core["source_ledger"]
    manifest = RP.build_research_provenance_manifest(
        repo_code_identity=core["code_identity"], information_cutoff=core["inputs"]["as_of"],
        output_identity="hermescoopcore:sha256:" + core_hash, output_hash=core_hash,
        input_evidence_reference_ids=[e["raw_evidence_reference_id"] for e in ledger],
        input_content_hashes=[e["content_sha256"] for e in ledger],
        dataset_refs=[core["inputs"]["grounding_receipt_id"], core["inputs"]["alpha_universe_snapshot_id"]],
        request_source_version_refs=sorted({f"{p['repository']}@{p['commit']}" for p in core["source_pins"]}),
        dq_flags=["OK"], replay_fidelity="FAITHFUL",
        gap_summary=json.dumps(core["benchmark"]["denominators"], sort_keys=True))
    body = json.loads(SG.canonical_bytes({"core": core, "provenance_manifest": asdict(manifest)}))
    return {**body, "receipt_id": RECEIPT_PREFIX + SG.sha256_hex(SG.canonical_bytes(body))}


NON_IDENTITY_NOTE = "timings are excluded from receipt identity"


def verify_receipt(receipt: object, recomputed_core: dict) -> list[str]:
    """Failure codes (empty = verified); fails closed on any mismatch."""
    if not isinstance(receipt, dict) or set(receipt) - {"non_identity"} != {"core", "provenance_manifest", "receipt_id"} \
            or not isinstance(receipt["core"], dict) or not isinstance(receipt["provenance_manifest"], dict):
        return ["RECEIPT_SHAPE_INVALID"]
    extra = receipt.get("non_identity", {})
    elapsed = extra.get("elapsed_ms", {}) if isinstance(extra, dict) else None
    if not isinstance(extra, dict) or set(extra) - {"note", "elapsed_ms", "total_ms"} or not isinstance(elapsed, dict) \
            or set(elapsed) - {METHOD_ID} or any(type(v) not in (int, float) for v in [*elapsed.values(), extra.get("total_ms", 0)]) \
            or extra.get("note", NON_IDENTITY_NOTE) != NON_IDENTITY_NOTE:
        return ["NON_IDENTITY_INVALID"]
    failures = []
    body = {"core": receipt["core"], "provenance_manifest": receipt["provenance_manifest"]}
    if receipt["receipt_id"] != RECEIPT_PREFIX + SG.sha256_hex(SG.canonical_bytes(body)):
        failures.append("RECEIPT_ID_MISMATCH")
    try:
        manifest = RP.ResearchProvenanceManifest(**{k: tuple(v) if isinstance(v, list) else v
                                                   for k, v in receipt["provenance_manifest"].items()})
        if not RP.verify_research_provenance_manifest_identity(manifest):
            failures.append("MANIFEST_ID_MISMATCH")
        if manifest.output_hash != SG.sha256_hex(SG.canonical_bytes(receipt["core"])):
            failures.append("MANIFEST_OUTPUT_BINDING_MISMATCH")
    except (TypeError, KeyError, ValueError, AttributeError):
        failures.append("MANIFEST_SHAPE_INVALID")
    if receipt["core"] != recomputed_core:
        failures.extend(f"OUTPUT_MISMATCH:{k}" for k in sorted(set(recomputed_core) | set(receipt["core"]))
                        if receipt["core"].get(k) != recomputed_core.get(k))
    elif receipt["provenance_manifest"] != finalize(recomputed_core)["provenance_manifest"]:
        failures.append("MANIFEST_RECOMPUTE_MISMATCH")
    return failures
