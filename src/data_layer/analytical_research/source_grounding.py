"""Offline source grounding and rule-aware market discovery (S10-R3-SRC-01).

Two pinned external method families are ADAPTED (algorithm only, no code copied, no
dependency):

* Polymarket/agents @081f2b5594c37edeb9d3780a778c084d5b6f2743
  ``agents/connectors/chroma.py`` ``PolymarketRAG.events`` / ``.markets``: index event
  descriptions with their market linkage and market descriptions with question/outcome
  metadata, then return scored matches. Here: a two-stage lexical BM25 event -> market
  ranker over the native observed universe (no Gamma client, Chroma or OpenAI
  embeddings). ``agents/application/prompts.py`` ``superforecaster`` step 1-2 (break the
  question down, gather information): here deterministic rule-grounded subquestions with
  claim-source links and NO probability.
* Metaculus/forecasting-tools @a54dd6443d19745b267e99a3b0b7627e74b9a57a
  ``source_archive/quality.py`` (HTTP status, minimum text length 200, block-page
  signatures) and ``pipeline.py`` (stored / deduped / quality_failed accounting by content
  hash). Here: applied to caller-supplied already-local bytes and bound to the native
  ``RawEvidenceReference`` / ``ResearchProvenanceManifest`` identities.

The corpus is only ``alpha_discovery.build_alpha_universe_snapshot``. Rule wording only
enters from caller bytes whose SHA-256 equals a native ``rule_content_sha256``.

Posture: research only, stdlib only, read-only over native stores, no network, no LLM,
no forecast probability, price, edge, strategy, paper, order or live authority.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import asdict
from decimal import ROUND_HALF_EVEN, Decimal
import hashlib
import json
import math
from pathlib import Path
import re

from src.data_layer.analytical_research import alpha_discovery as AD
from src.data_layer.analytical_research import alpha_factory_registry as AFR
from src.data_layer.point_in_time_market_research import research_provenance as RP

WP_ID = "S10-R3-SRC-01"
CASE_SCHEMA = "s10-r3-src01-case-v1"
RECEIPT_SCHEMA = "s10-r3-src01-grounding-receipt-v1"
RECEIPT_PREFIX = "srcground:sha256:"
RESEARCH_ONLY = "RESEARCH_ONLY"
CALLER = "tools/alpha/run_source_grounding.py:run -> source_grounding.build_grounding_core -> source_grounding.rank_markets"

# Ranking parameters frozen a priori (textbook BM25 defaults) before the benchmark corpus.
RANKER_ID = "pa_event_market_bm25_v1"
BASELINE_ID = "baseline_plain_v0"
TOP_K = 10
BM25_K1 = 1.2
BM25_B = 0.75
EVENT_WEIGHT = 0.5
MIN_QUERY_COVERAGE = 0.5  # ranker abstains unless >= half of distinct query terms are matched
AMBIGUITY_RATIO = 0.95
BENCHMARK_MIN_LABELED = 30
MIN_TEXT_LEN = 200  # Metaculus quality.MIN_TEXT_LEN
MAX_ITEMS = 500

SOURCE_PINS = (
    {"capability": "R3-02", "repository": "Polymarket/agents", "commit": "081f2b5594c37edeb9d3780a778c084d5b6f2743",
     "files": ["agents/connectors/chroma.py", "agents/application/prompts.py"], "license": "MIT",
     "adoption_mode": "ADAPT_ALGORITHM_NO_CODE_COPIED"},
    {"capability": "R3-01-SOURCE_ARCHIVE", "repository": "Metaculus/forecasting-tools",
     "commit": "a54dd6443d19745b267e99a3b0b7627e74b9a57a",
     "files": ["forecasting_tools/agents_and_tools/source_archive/pipeline.py",
               "forecasting_tools/agents_and_tools/source_archive/quality.py"], "license": "MIT",
     "adoption_mode": "ADAPT_ALGORITHM_NO_CODE_COPIED"},
)

# Metaculus quality.BLOCK_SIGNATURES (matched case-insensitively against extracted text).
BLOCK_SIGNATURES = (
    "verify you are a human", "are you a human", "checking your browser before",
    "enable javascript and cookies to continue", "please enable javascript",
    "access to this page has been denied", "access denied", "request unsuccessful. incapsula",
    "attention required! | cloudflare", "ddos protection by cloudflare", "ray id:", "captcha",
    "unusual traffic from your computer",
)
# Local extension (not upstream): login / paywall interstitials.
LOGIN_SIGNATURES = ("sign in to continue", "log in to continue", "please log in", "subscribe to continue reading")

STOPWORDS = frozenset(
    "a an and are as at be before by do does for from has have in is it of on or the to was were will with "
    "who what when which than this that any be".split())

CASE_KEYS = {"schema_id", "case_label", "corpus_class", "pit_store", "alpha_registry", "policy", "as_of",
             "rule_texts", "sources", "queries"}
CORPUS_CLASSES = ("SANITIZED_SYNTHETIC", "LOCAL_REAL_PIT")
RULE_KEYS = {"market_id", "file"}
SOURCE_KEYS = {"source_label", "market_id", "file", "url", "http_status", "media_type", "capture_mode",
               "declared_sha256", "source_publish_time", "public_available_time", "local_first_seen_time",
               "ingestion_time", "revision_time"}
CAPTURE_MODES = ("PROSPECTIVE_LOCAL_CAPTURE", "LATER_IMPORT")
QUERY_KEYS = {"query_id", "text", "category_hint", "relevant_market_ids"}
SECRET_KEY_PARTS = ("api_key", "apikey", "secret", "password", "passphrase", "private_key", "mnemo", "seed_phrase",
                    "access_token", "refresh_token", "authorization", "cookie", "credential", "wallet")
TRADE_KEY_WORDS = ("order", "side", "size", "price", "amount", "signature", "stake", "bet")
SECRET_RE = re.compile(r"(?i)(sk-[a-z0-9_-]{16,}|bearer\s+[a-z0-9._-]{8,}|-----begin [a-z ]*private key|"
                       r"\b0x[0-9a-f]{64}\b|gh[pousr]_[a-z0-9]{20,})")
_LABEL_RE = re.compile(r"[a-z0-9][a-z0-9_-]{0,47}")
_QID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,63}")
_SHA_RE = re.compile(r"[0-9a-f]{64}")
_REL_RE = re.compile(r"(rules|sources)/[0-9]{3}\.bin")
_TOKEN_RE = re.compile(r"[a-z0-9]+")
_TAG_RE = re.compile(r"<[^>]*>")
_MONTHS = ("january february march april may june july august september october november december").split()


class GroundingStop(Exception):
    """Whole-run fail-closed stop with a stable code (never echoes input)."""


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise GroundingStop(code)


def canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _ratio(numerator: int, denominator: int) -> dict:
    value = None if denominator == 0 else str((Decimal(numerator) / Decimal(denominator)).quantize(
        Decimal("0.000001"), rounding=ROUND_HALF_EVEN))
    return {"numerator": numerator, "denominator": denominator, "value": value}


def tokenize(text: str | None) -> list[str]:
    if not text:
        return []
    return [t for t in _TOKEN_RE.findall(text.casefold()) if t not in STOPWORDS]


# ------------------------------------------------------------------ case validation


def _scan_forbidden(value: object, depth: int = 0, *, trade_words: bool = True) -> None:
    """Credential- or trade-shaped keys anywhere reject the case (keys only; safe wording in values is allowed)."""
    _require(depth <= 8, "CASE_TOO_DEEP")
    if isinstance(value, dict):
        for key, item in value.items():
            _require(isinstance(key, str), "CASE_FIELDS_INVALID")
            lowered = key.casefold()
            _require(not any(p in lowered for p in SECRET_KEY_PARTS), "FORBIDDEN_FIELD")
            _require(not trade_words or not set(re.split(r"[^a-z0-9]+", lowered)) & set(TRADE_KEY_WORDS),
                     "FORBIDDEN_FIELD")
            # The native policy has its own strict FORBIDDEN_FIELD check and legitimately names price deltas.
            _scan_forbidden(item, depth + 1, trade_words=trade_words and not (depth == 0 and key == "policy"))
    elif isinstance(value, list):
        for item in value:
            _scan_forbidden(item, depth + 1, trade_words=trade_words)


def validate_case(case: object, *, frozen: bool) -> None:
    """Whole-case structure. Per-item defects of rules/sources/queries are counted later."""
    _require(isinstance(case, dict), "CASE_JSON_INVALID")
    _scan_forbidden(case)
    _require(set(case) == CASE_KEYS, "CASE_FIELDS_INVALID")
    _require(case["schema_id"] == CASE_SCHEMA, "CASE_SCHEMA_INVALID")
    _require(type(case["case_label"]) is str and _LABEL_RE.fullmatch(case["case_label"]) is not None, "CASE_LABEL_INVALID")
    _require(case["corpus_class"] in CORPUS_CLASSES, "CORPUS_CLASS_INVALID")
    _require(type(case["as_of"]) is str, "AS_OF_INVALID")
    try:
        RP.canonicalize_utc_timestamp(case["as_of"])
    except ValueError:
        raise GroundingStop("AS_OF_INVALID") from None
    _require(type(case["policy"]) is dict, "POLICY_INVALID")
    _require(type(case["pit_store"]) is str and case["pit_store"], "PIT_STORE_INVALID")
    _require(case["alpha_registry"] is None or (type(case["alpha_registry"]) is str and case["alpha_registry"]),
             "ALPHA_REGISTRY_INVALID")
    for name in ("rule_texts", "sources", "queries"):
        _require(type(case[name]) is list and len(case[name]) <= MAX_ITEMS, "CASE_LIST_INVALID")
    _require(len(case["queries"]) > 0, "QUERIES_EMPTY")
    if frozen:
        _require(case["pit_store"] == "pit.sqlite3", "FROZEN_CASE_INVALID")
        _require(case["alpha_registry"] in (None, "alpha.sqlite3"), "FROZEN_CASE_INVALID")
        for item in case["rule_texts"] + case["sources"]:
            _require(type(item) is dict and type(item.get("file")) is str and _REL_RE.fullmatch(item["file"]) is not None,
                     "FROZEN_CASE_INVALID")


# ------------------------------------------------------------------ corpus


def load_corpus(store_path: Path, policy_mapping: dict, as_of: str):
    policy = AD.build_alpha_discovery_policy(policy_mapping)
    _require(policy.is_valid, "POLICY_INVALID")
    built = AD.build_alpha_universe_snapshot(store_path, policy.record, as_of)
    _require(built.is_valid and isinstance(built.record, AD.AlphaUniverseSnapshot), "UNIVERSE_INVALID")
    return policy.record, built.record


def _event_identity(market: AD.ObservedMarketState) -> str:
    if market.condition_id and market.event_id == "event:polymarket:" + market.condition_id:
        return "EVENT_ID_CONDITION_DERIVED"
    return "EVENT_ID_AS_RECORDED"


def bind_rule_texts(universe: AD.AlphaUniverseSnapshot, entries: list, read) -> tuple[dict, list]:
    """Admit rule wording only when its bytes hash to the market's native rule_content_sha256."""
    markets = {m.market_id: m for m in universe.markets}
    bound: dict[str, dict] = {}
    outcomes = []
    for index, entry in enumerate(entries):
        status = "BOUND"
        market_id = entry.get("market_id") if isinstance(entry, dict) else None
        rule = None
        if not isinstance(entry, dict) or set(entry) != RULE_KEYS or type(market_id) is not str:
            status = "RULE_FIELDS_INVALID"
        elif market_id not in markets:
            status = "RULE_MARKET_NOT_IN_CORPUS"
        elif market_id in bound:
            status = "RULE_DUPLICATE"
        else:
            raw = read(entry["file"])
            digest = sha256_hex(raw) if raw else None
            rule = next((r for r in markets[market_id].rules if r.rule_content_sha256 == digest), None)
            if not raw:
                status = "RULE_BYTES_MISSING"
            elif rule is None:
                status = "RULE_HASH_MISMATCH"
            else:
                try:
                    text = raw.decode("utf-8")
                except UnicodeDecodeError:
                    status = "RULE_BYTES_INVALID"
                else:
                    bound[market_id] = {"text": text, "rule_content_sha256": digest,
                                        "rule_record_version_id": rule.rule_record_version_id,
                                        "resolution_source_id": rule.resolution_source_id}
        outcomes.append({"index": index, "market_id": market_id if type(market_id) is str and market_id in markets else None,
                         "status": status})
    return bound, outcomes


def market_document(market: AD.ObservedMarketState, rule_text: str | None) -> list[str]:
    tokens = tokenize(market.question_text) * 2  # question is the primary field (BM25F-lite weight 2)
    tokens += tokenize(market.category) + tokenize(" ".join(market.outcome_labels))
    if market.resolution_date and len(market.resolution_date) >= 7:
        tokens += [market.resolution_date[:4], _MONTHS[int(market.resolution_date[5:7]) - 1]]
    return tokens + tokenize(rule_text)


class _BM25:
    def __init__(self, docs: dict[str, list[str]]):
        self.docs = {k: Counter(v) for k, v in docs.items()}
        self.lengths = {k: len(v) for k, v in docs.items()}
        self.avg = (sum(self.lengths.values()) / len(docs)) if docs else 0.0
        df = Counter(t for counts in self.docs.values() for t in counts)
        n = len(docs)
        self.idf = {t: math.log(1 + (n - f + 0.5) / (f + 0.5)) for t, f in df.items()}

    def score(self, key: str, terms: list[str]) -> float:
        counts, length, total = self.docs[key], self.lengths[key], 0.0
        for term in terms:
            tf = counts.get(term, 0)
            if tf:
                total += self.idf[term] * tf * (BM25_K1 + 1) / (tf + BM25_K1 * (1 - BM25_B + BM25_B * length / (self.avg or 1)))
        return round(total, 9)  # rounded so ordering is stable across libm builds


def build_index(universe: AD.AlphaUniverseSnapshot, rules: dict) -> dict:
    rankable = [m for m in universe.markets if m.question_text]
    docs = {m.market_id: market_document(m, rules.get(m.market_id, {}).get("text")) for m in rankable}
    events: dict[str, list[str]] = {}
    for m in rankable:
        events.setdefault(m.event_id, []).extend(docs[m.market_id])
    return {"markets": {m.market_id: m for m in rankable}, "docs": docs, "market_bm25": _BM25(docs),
            "event_docs": events, "event_bm25": _BM25(events)}


def rank_markets(index: dict, query: str) -> dict:
    """Two-stage event -> market lexical retrieval (Polymarket Agents events/markets, adapted)."""
    terms = sorted(set(tokenize(query)))
    if not terms:
        return {"ranked": [], "status": "ABSTAINED", "reason": "QUERY_HAS_NO_TERMS", "flags": [], "coverage": None}
    event_scores = {e: index["event_bm25"].score(e, terms) for e in index["event_docs"]}
    scored = []
    for market_id, market in index["markets"].items():
        final = round(index["market_bm25"].score(market_id, terms) + EVENT_WEIGHT * event_scores[market.event_id], 9)
        if final > 0:
            scored.append((-final, market_id))
    scored.sort()
    if not scored:
        return {"ranked": [], "status": "ABSTAINED", "reason": "NO_MATCH", "flags": [], "coverage": _ratio(0, len(terms))}
    best = index["markets"][scored[0][1]]
    matched = set(index["docs"][best.market_id]) | set(index["event_docs"][best.event_id])
    coverage = sum(1 for t in terms if t in matched)
    if coverage / len(terms) < MIN_QUERY_COVERAGE:
        return {"ranked": [], "status": "ABSTAINED", "reason": "LOW_QUERY_COVERAGE", "flags": [],
                "coverage": _ratio(coverage, len(terms))}
    top = scored[:TOP_K]
    flags = []
    if len(top) > 1 and -top[1][0] >= AMBIGUITY_RATIO * -top[0][0] and \
            index["markets"][top[1][1]].event_id != best.event_id:
        flags.append("AMBIGUOUS_TOP_RANK")
    titles: dict[str, set] = {}
    for _, market_id in top:
        m = index["markets"][market_id]
        titles.setdefault(m.question_text.casefold(), set()).add(tuple(sorted(r.rule_content_sha256 for r in m.rules)))
    if any(len(v) > 1 for v in titles.values()):
        flags.append("SAME_TITLE_DIFFERENT_RULES")
    return {"ranked": [m for _, m in top], "scores": [f"{-s:.6f}" for s, _ in top], "status": "RANKED",
            "reason": None, "flags": flags, "coverage": _ratio(coverage, len(terms))}


def rank_baseline_plain_v0(universe: AD.AlphaUniverseSnapshot, query: str, category_hint: str | None) -> list[str]:
    """Constructed native-field baseline: distinct case-folded token overlap with question_text,
    exact native category equal to the query hint as tie-break, then market_id. Not a pre-existing tool."""
    terms = set(tokenize(query))
    scored = []
    for m in universe.markets:
        overlap = len(terms & set(tokenize(m.question_text)))
        if overlap:
            scored.append((-overlap, 0 if category_hint is not None and m.category == category_hint else 1, m.market_id))
    return [m for *_, m in sorted(scored)[:TOP_K]]


def subquestions(market: AD.ObservedMarketState, rule: dict | None, source_refs: list[str]) -> list[dict]:
    """Deterministic decomposition (superforecaster steps 1-2) with claim-source links; never a probability."""
    q = market.question_text
    items = [{"text": f"Which outcome of {list(market.outcome_labels)} does '{q}' resolve to by {market.resolution_date or 'an unrecorded date'}?",
              "claim_sources": [market.metadata_record_version_id]}]
    if rule:
        first = re.split(r"(?<=[.!?])\s", rule["text"].strip(), maxsplit=1)[0][:300]
        items.append({"text": f"Under the hash-verified rule ({rule['resolution_source_id']}): '{first}' - what pre-cutoff evidence satisfies it?",
                      "claim_sources": [rule["rule_record_version_id"], "rule:sha256:" + rule["rule_content_sha256"]]})
    else:
        items.append({"text": "RULE_TEXT_UNAVAILABLE: resolution wording is not verified; reason only from question, category, outcomes and date.",
                      "claim_sources": [r.rule_record_version_id for r in market.rules]})
    items.append({"text": "Which admitted pre-cutoff sources bear on this market?" if source_refs
                  else "No admitted pre-cutoff source is bound to this market.", "claim_sources": list(source_refs)})
    return items


# ------------------------------------------------------------------ sources (Metaculus quality, adapted)


def _visible_text(raw: bytes) -> str | None:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return None
    if "\x00" in text:
        return None
    return re.sub(r"\s+", " ", _TAG_RE.sub(" ", text)).strip()


def quality_verdict(http_status: int, raw: bytes) -> tuple[str, str | None]:
    # Upstream gates >= 400; a 1xx/3xx capture is not a body either, so only 2xx can pass.
    if not 200 <= http_status <= 299:
        return "QUALITY_FAILED", f"HTTP_STATUS_{http_status}"
    text = _visible_text(raw)
    if text is None:
        return "QUALITY_FAILED", "INVALID_BYTES"
    lowered = text.casefold()
    if any(sig in lowered for sig in BLOCK_SIGNATURES):
        return "QUALITY_FAILED", "BLOCK_SIGNATURE"
    if any(sig in lowered for sig in LOGIN_SIGNATURES):
        return "QUALITY_FAILED", "LOGIN_WALL"
    if len(text) < MIN_TEXT_LEN:
        return "QUALITY_FAILED", "THIN_CONTENT"
    return "PASSED", None


def _safe_url(url: object) -> bool:
    return (type(url) is str and len(url) <= 512 and re.fullmatch(r"https?://[^\s@/?#]+(/[^\s?#]*)?(\?[^\s#]*)?", url) is not None
            and SECRET_RE.search(url) is None and not re.search(r"(?i)[?&](token|key|sig|auth|session)[a-z_]*=", url))


def _clock(value: object) -> str | None:
    return None if value is None else RP.canonicalize_utc_timestamp(value)


def evaluate_sources(entries: list, universe: AD.AlphaUniverseSnapshot, as_of: str, read) -> tuple[list, list]:
    markets = {m.market_id for m in universe.markets}
    labels: set[str] = set()
    seen_content: set[tuple[str, str]] = set()
    outcomes, accepted = [], []
    for index, entry in enumerate(entries):
        out = {"index": index, "source_label": None, "market_id": None, "status": "REJECTED", "reason": None,
               "content_sha256": None, "byte_length": None, "admissibility": None, "raw_evidence_reference_id": None}
        outcomes.append(out)
        if not isinstance(entry, dict) or set(entry) != SOURCE_KEYS or type(entry["source_label"]) is not str \
                or _LABEL_RE.fullmatch(entry["source_label"]) is None or type(entry["market_id"]) is not str \
                or type(entry["http_status"]) is not int or not 100 <= entry["http_status"] <= 599 \
                or type(entry["media_type"]) is not str or not entry["media_type"] \
                or entry["capture_mode"] not in CAPTURE_MODES or type(entry["declared_sha256"]) is not str \
                or _SHA_RE.fullmatch(entry["declared_sha256"]) is None:
            out["reason"] = "SOURCE_FIELDS_INVALID"
            continue
        out["source_label"] = entry["source_label"]
        if entry["source_label"] in labels:
            out["reason"] = "CONFLICTING_SOURCE_IDENTITY"
            continue
        labels.add(entry["source_label"])
        if entry["market_id"] not in markets:
            out["reason"] = "SOURCE_MARKET_NOT_IN_CORPUS"
            continue
        out["market_id"] = entry["market_id"]
        if not _safe_url(entry["url"]):
            out["reason"] = "SOURCE_URL_UNSAFE"
            continue
        raw = read(entry["file"])
        if not raw:
            out["reason"] = "SOURCE_MISSING_OR_EMPTY"
            continue
        digest = sha256_hex(raw)
        out["content_sha256"], out["byte_length"] = digest, len(raw)
        if digest != entry["declared_sha256"]:
            out["reason"] = "SOURCE_BYTES_CHANGED"
            continue
        try:
            clocks = {k: _clock(entry[k]) for k in ("source_publish_time", "public_available_time",
                                                    "local_first_seen_time", "ingestion_time", "revision_time")}
        except ValueError:
            out["reason"] = "SOURCE_CLOCK_INVALID"
            continue
        later_import = entry["capture_mode"] == "LATER_IMPORT"
        key = RP._utc_instant_key
        published = [clocks[k] for k in ("source_publish_time", "public_available_time") if clocks[k]]
        if any(key(t) > key(as_of) for t in published):
            out["reason"] = "FUTURE_CONTENT"
            continue
        if clocks["local_first_seen_time"] and any(key(t) > key(clocks["local_first_seen_time"]) for t in published):
            out["reason"] = "SOURCE_CLOCK_INCONSISTENT"  # seen locally before it was published/available
            continue
        if clocks["ingestion_time"] is None:
            out["reason"] = "SOURCE_INGESTION_CLOCK_MISSING"
            continue
        if clocks["local_first_seen_time"] and key(clocks["ingestion_time"]) < key(clocks["local_first_seen_time"]):
            out["reason"] = "SOURCE_CLOCK_INCONSISTENT"
            continue
        if not later_import and key(clocks["ingestion_time"]) > key(as_of):
            out["reason"] = "SOURCE_INGESTED_AFTER_CUTOFF"
            continue
        if later_import:
            clocks["local_first_seen_time"] = None  # a later import never carries a prospective first-seen
        evidence = RP.ObservabilityEvidence(
            local_first_seen_time=clocks["local_first_seen_time"],
            public_available_time=clocks["public_available_time"],
            is_correction_after_cutoff=bool(clocks["revision_time"]) and key(clocks["revision_time"]) > key(as_of),
            is_backfilled=later_import)
        admissibility = RP.evaluate_replay_admissibility(as_of, evidence)
        out["admissibility"] = admissibility.to_dict()
        if admissibility.status != "ADMISSIBLE":
            out["reason"] = {"CORRECTION_AFTER_CUTOFF": "LATE_REVISION", "NOT_YET_SEEN": "FUTURE_CONTENT"}.get(
                admissibility.basis, "NO_OBSERVABILITY_EVIDENCE")
            continue
        verdict, reason = quality_verdict(entry["http_status"], raw)
        if verdict != "PASSED":
            out["status"], out["reason"] = "QUALITY_FAILED", reason
            continue
        if (entry["market_id"], digest) in seen_content:
            out["status"], out["reason"] = "DEDUPED", "DUPLICATE_CONTENT"
            continue
        seen_content.add((entry["market_id"], digest))
        reference = RP.build_raw_evidence_reference(
            source_system="caller-local-bytes", endpoint=entry["url"], retrieval_method=entry["capture_mode"],
            content_sha256=digest, byte_length=len(raw), media_type=entry["media_type"],
            pit=RP.build_pit_timestamps(**{k: v for k, v in clocks.items() if k != "revision_time"},
                                        correction_or_revision_time=clocks["revision_time"]),
            dq_flags=["BACKFILLED"] if later_import else ["OK"], replay_fidelity="FAITHFUL")
        out["status"], out["raw_evidence_reference_id"] = "ACCEPTED", reference.raw_evidence_reference_id
        accepted.append({"market_id": entry["market_id"], "reference": _reference_mapping(reference)})
    return outcomes, accepted


def _reference_mapping(reference: RP.RawEvidenceReference) -> dict:
    return {"raw_evidence_reference_id": reference.raw_evidence_reference_id, **reference.logical_preimage()}


def rebuild_reference(mapping: dict) -> RP.RawEvidenceReference:
    pairs = [tuple(p) for p in mapping["request_parameters"]]
    return RP.RawEvidenceReference(
        raw_evidence_reference_id=mapping["raw_evidence_reference_id"], schema_id=mapping["schema_id"],
        schema_version=mapping["schema_version"], source_system=mapping["source_system"], endpoint=mapping["endpoint"],
        retrieval_method=mapping["retrieval_method"], request_parameters=tuple(pairs), cursor_anchor=mapping["cursor_anchor"],
        pit=RP.PitTimestamps(**mapping["pit"]), content_sha256=mapping["content_sha256"], byte_length=mapping["byte_length"],
        media_type=mapping["media_type"], api_version=mapping["api_version"], raw_snapshot_ref=mapping["raw_snapshot_ref"],
        dq_flags=tuple(mapping["dq_flags"]), replay_fidelity=mapping["replay_fidelity"])


# ------------------------------------------------------------------ optional Alpha join


def join_alpha_candidates(registry_path: Path | None, universe: AD.AlphaUniverseSnapshot) -> dict:
    if registry_path is None:
        return {"status": "NOT_SUPPLIED", "candidates": 0, "joined": [], "unresolved_refs": 0}
    loaded = AFR.load_and_verify_alpha_factory_registry(registry_path)
    _require(loaded.is_valid and loaded.snapshot is not None, "ALPHA_REGISTRY_INVALID")
    markets = {m.market_id for m in universe.markets}
    joined, unresolved, candidates = [], 0, 0
    for entry in loaded.snapshot.entries:
        refs = getattr(entry.record, "subject_refs", None)
        if refs is None:
            continue
        candidates += 1
        market_refs = [r for r in refs or () if r.startswith("market:")]
        hit = sorted(r for r in market_refs if r in markets)
        unresolved += len(market_refs) - len(hit)
        if hit:
            joined.append({"candidate_id": entry.record.candidate_id, "market_ids": hit})
    return {"status": "JOINED_READ_ONLY", "candidates": candidates, "joined": joined, "unresolved_refs": unresolved}


# ------------------------------------------------------------------ benchmark


def _validate_queries(queries: list, markets: set) -> list[dict]:
    seen: set[str] = set()
    out = []
    for index, q in enumerate(queries):
        row = {"index": index, "query_id": None, "status": "VALID", "reason": None}
        if not isinstance(q, dict) or set(q) != QUERY_KEYS or type(q["query_id"]) is not str \
                or _QID_RE.fullmatch(q["query_id"]) is None or type(q["text"]) is not str \
                or not (q["category_hint"] is None or type(q["category_hint"]) is str) \
                or type(q["relevant_market_ids"]) is not list or any(type(x) is not str for x in q["relevant_market_ids"]):
            row.update(status="REFUSED", reason="QUERY_FIELDS_INVALID")
        elif q["query_id"] in seen:
            row.update(query_id=q["query_id"], status="REFUSED", reason="DUPLICATE_QUERY_ID")
        elif not tokenize(q["text"]):
            row.update(query_id=q["query_id"], status="REFUSED", reason="QUERY_EMPTY")
        elif len(set(q["relevant_market_ids"])) != len(q["relevant_market_ids"]):
            row.update(query_id=q["query_id"], status="REFUSED", reason="DUPLICATE_LABEL")
        elif any(x not in markets for x in q["relevant_market_ids"]):
            row.update(query_id=q["query_id"], status="REFUSED", reason="LABEL_NOT_IN_CORPUS")
        else:
            row["query_id"] = q["query_id"]
        if row["query_id"]:
            seen.add(row["query_id"])
        out.append(row)
    return out


def _method_metrics(rows: list[dict], key: str) -> dict:
    valid = [r for r in rows if r["status"] == "VALID"]
    pos = [r for r in valid if r["relevant"]]
    neg = [r for r in valid if not r["relevant"]]
    hits = sum(len(set(r[key]) & set(r["relevant"])) for r in pos)
    relevant = sum(len(r["relevant"]) for r in pos)
    retrieved_pos = sum(len(r[key]) for r in pos)
    retrieved_all = sum(len(r[key]) for r in valid)
    nonrelevant_all = sum(len(set(r[key]) - set(r["relevant"])) for r in valid)
    return {
        "recall_at_10": _ratio(hits, relevant),
        "precision_at_10": _ratio(hits, retrieved_pos),
        "false_relatedness_items": _ratio(nonrelevant_all, retrieved_all),
        "negative_queries_with_results": _ratio(sum(1 for r in neg if r[key]), len(neg)),
        "positive_queries_with_zero_hits": _ratio(sum(1 for r in pos if not set(r[key]) & set(r["relevant"])), len(pos)),
        "abstained": _ratio(sum(1 for r in valid if not r[key]), len(valid)),
        "cost": {"classification": "LOCAL_CPU_ONLY", "provider_calls": 0, "network_calls": 0, "spend_usd": "0"},
    }


def run_benchmark(case: dict, universe: AD.AlphaUniverseSnapshot, index: dict, rules: dict, refs_by_market: dict,
                  timer=None) -> dict:
    markets = {m.market_id for m in universe.markets}
    checks = _validate_queries(case["queries"], markets)
    rows = []
    elapsed = {RANKER_ID: 0, BASELINE_ID: 0}
    for check, q in zip(checks, case["queries"]):
        row = dict(check)
        row.update(relevant=sorted(q["relevant_market_ids"]) if check["status"] == "VALID" else [],
                   ranker=[], baseline=[], ranker_status=None, ranker_reason=None, flags=[], coverage=None,
                   scores=[], subquestions=[])
        if check["status"] == "VALID":
            t0 = timer() if timer else 0
            ranked = rank_markets(index, q["text"])
            t1 = timer() if timer else 0
            row["baseline"] = rank_baseline_plain_v0(universe, q["text"], q["category_hint"])
            t2 = timer() if timer else 0
            elapsed[RANKER_ID] += t1 - t0
            elapsed[BASELINE_ID] += t2 - t1
            row.update(ranker=ranked["ranked"], ranker_status=ranked["status"], ranker_reason=ranked["reason"],
                       flags=ranked["flags"], coverage=ranked["coverage"], scores=ranked.get("scores", []))
            for market_id in ranked["ranked"][:3]:
                row["subquestions"].append({"market_id": market_id, "event_identity": _event_identity(index["markets"][market_id]),
                                            "items": subquestions(index["markets"][market_id], rules.get(market_id),
                                                                  refs_by_market.get(market_id, []))})
        rows.append(row)
    valid = [r for r in rows if r["status"] == "VALID"]
    labeled = sum(1 for r in valid if r["relevant"])
    refused = Counter(r["reason"] for r in rows if r["status"] == "REFUSED")
    status = "COMPLETED" if labeled >= BENCHMARK_MIN_LABELED else "BENCHMARK_REFUSED"
    metrics = None if status != "COMPLETED" else {RANKER_ID: _method_metrics(rows, "ranker"),
                                                  BASELINE_ID: _method_metrics(rows, "baseline")}
    return {
        "status": status,
        "refusal_reason": None if status == "COMPLETED" else "FEWER_THAN_THIRTY_VALID_LABELED_CASES",
        "denominators": {"cases_total": len(rows), "cases_valid": len(valid), "cases_refused": len(rows) - len(valid),
                         "positive_labeled": labeled, "negative_no_match": len(valid) - labeled,
                         "refused_by_reason": dict(sorted(refused.items()))},
        "corpus_sha256": sha256_hex(canonical_bytes(case["queries"])),
        "metrics": metrics,
        "cases": rows,
        "_elapsed": elapsed,
    }


# ------------------------------------------------------------------ receipt


def build_grounding_core(case: dict, input_dir: Path, code_identity: str, timer=None) -> tuple[dict, dict]:
    """Compute the receipt core from a FROZEN case and its frozen input directory (read-only)."""
    validate_case(case, frozen=True)
    as_of = RP.canonicalize_utc_timestamp(case["as_of"])
    input_dir = Path(input_dir)

    def read(rel: str) -> bytes:
        path = input_dir / rel
        return path.read_bytes() if path.is_file() and not path.is_symlink() else b""

    input_hashes = {}
    for rel in sorted({"pit.sqlite3", *([case["alpha_registry"]] if case["alpha_registry"] else []),
                       *(e["file"] for e in case["rule_texts"] + case["sources"])}):
        raw = read(rel)
        input_hashes[rel] = sha256_hex(raw) if raw else None
    policy, universe = load_corpus(input_dir / "pit.sqlite3", case["policy"], as_of)
    rules, rule_outcomes = bind_rule_texts(universe, case["rule_texts"], read)
    source_outcomes, accepted = evaluate_sources(case["sources"], universe, as_of, read)
    refs_by_market: dict[str, list[str]] = {}
    for item in accepted:
        refs_by_market.setdefault(item["market_id"], []).append(item["reference"]["raw_evidence_reference_id"])
    index = build_index(universe, rules)
    alpha = join_alpha_candidates(input_dir / case["alpha_registry"] if case["alpha_registry"] else None, universe)
    bench = run_benchmark(case, universe, index, rules, refs_by_market, timer)
    elapsed = bench.pop("_elapsed")
    gaps = Counter(g for m in universe.markets for g in m.data_gap_codes)
    core = {
        "schema_id": RECEIPT_SCHEMA, "wp_id": WP_ID, "posture": RESEARCH_ONLY, "case_label": case["case_label"],
        "corpus_class": case["corpus_class"], "caller": CALLER, "code_identity": code_identity,
        "source_pins": [dict(p) for p in SOURCE_PINS],
        "method": {"ranker_id": RANKER_ID, "baseline_id": BASELINE_ID, "top_k": TOP_K, "bm25_k1": str(BM25_K1),
                   "bm25_b": str(BM25_B), "event_weight": str(EVENT_WEIGHT), "min_query_coverage": str(MIN_QUERY_COVERAGE),
                   "ambiguity_ratio": str(AMBIGUITY_RATIO), "min_text_len": MIN_TEXT_LEN, "stopwords": sorted(STOPWORDS)},
        "inputs": {"as_of": as_of, "case_sha256": sha256_hex(canonical_bytes(case)), "file_sha256": input_hashes,
                   "alpha_discovery_policy_id": policy.alpha_discovery_policy_id,
                   "alpha_universe_snapshot_id": universe.alpha_universe_snapshot_id},
        "corpus": {"markets_total": len(universe.markets), "markets_rankable": len(index["markets"]),
                   "markets_unrankable_no_question": len(universe.markets) - len(index["markets"]),
                   "market_ids": [m.market_id for m in universe.markets],
                   "events_total": len(index["event_docs"]),
                   "event_id_condition_derived": sum(1 for m in universe.markets if _event_identity(m) == "EVENT_ID_CONDITION_DERIVED"),
                   "data_gap_counts": dict(sorted(gaps.items())),
                   "rule_text_bound": len(rules), "rule_text_unavailable": len(index["markets"]) - sum(1 for m in rules if m in index["markets"]),
                   "rule_text_entries": rule_outcomes},
        "sources": {"entries": source_outcomes, "accepted_references": [a["reference"] for a in accepted],
                    "counts": dict(sorted(Counter(o["reason"] or o["status"] for o in source_outcomes).items()))},
        "alpha_join": alpha,
        "benchmark": bench,
        "adoption": {
            "R3-02": "NOT_VALUE_VERIFIED",
            "R3-02_reason": ("SANITIZED_SYNTHETIC corpus proves callable behaviour only, never real-world lift"
                             if case["corpus_class"] == "SANITIZED_SYNTHETIC" else
                             "LOCAL_REAL_PIT observation awaits independent review; never self-declared VALUE_VERIFIED"),
            "R3-01-SOURCE_ARCHIVE": "INTEGRATED_OFFLINE_NOT_VALUE_VERIFIED",
            "provider_lanes": "UNCHANGED_OWNER_GATED",
        },
        "authority": {"research_only": True, "forecast_probability": False, "price_or_edge": False, "strategy": False,
                      "paper": False, "orders": False, "live": False, "store_writes": False, "llm_or_hermes": False,
                      "network_calls": 0, "provider_calls": 0, "credentials": False},
    }
    return json.loads(canonical_bytes(core)), elapsed


def finalize_receipt(core: dict) -> dict:
    core_hash = sha256_hex(canonical_bytes(core))
    refs = core["sources"]["accepted_references"]
    manifest = RP.build_research_provenance_manifest(
        repo_code_identity=core["code_identity"], information_cutoff=core["inputs"]["as_of"],
        output_identity="srcgroundcore:sha256:" + core_hash, output_hash=core_hash,
        input_evidence_reference_ids=[r["raw_evidence_reference_id"] for r in refs],
        input_content_hashes=[r["content_sha256"] for r in refs],
        dataset_refs=[core["inputs"]["alpha_universe_snapshot_id"], "pit:sha256:" + core["inputs"]["file_sha256"]["pit.sqlite3"]],
        request_source_version_refs=[f"{p['repository']}@{p['commit']}" for p in core["source_pins"]],
        dq_flags=["BACKFILLED"] if any("BACKFILLED" in r["dq_flags"] for r in refs) else ["OK"],
        replay_fidelity="FAITHFUL", gap_summary=json.dumps(core["sources"]["counts"], sort_keys=True))
    body = json.loads(canonical_bytes({"core": core, "provenance_manifest": asdict(manifest)}))
    return {**body, "receipt_id": RECEIPT_PREFIX + sha256_hex(canonical_bytes(body))}


def verify_receipt(receipt: object, recomputed_core: dict) -> list[str]:
    """Return failure codes (empty list = verified). Fails closed on any mismatch."""
    if not isinstance(receipt, dict) or set(receipt) - {"non_identity"} != {"core", "provenance_manifest", "receipt_id"} \
            or not isinstance(receipt["core"], dict) or not isinstance(receipt["provenance_manifest"], dict):
        return ["RECEIPT_SHAPE_INVALID"]
    # Timings are outside identity, so the block may hold timings only (no smuggled status claims).
    extra = receipt.get("non_identity", {})
    elapsed = extra.get("elapsed_ms", {}) if isinstance(extra, dict) else None
    if not isinstance(extra, dict) or set(extra) - {"note", "elapsed_ms", "total_ms"} or not isinstance(elapsed, dict) \
            or set(elapsed) - {RANKER_ID, BASELINE_ID} \
            or any(type(v) not in (int, float) for v in [*elapsed.values(), extra.get("total_ms", 0)]) \
            or extra.get("note", "timings are excluded from receipt identity") != "timings are excluded from receipt identity":
        return ["NON_IDENTITY_INVALID"]
    failures = []
    body = {"core": receipt["core"], "provenance_manifest": receipt["provenance_manifest"]}
    if receipt["receipt_id"] != RECEIPT_PREFIX + sha256_hex(canonical_bytes(body)):
        failures.append("RECEIPT_ID_MISMATCH")
    try:
        manifest = RP.ResearchProvenanceManifest(**{k: tuple(v) if isinstance(v, list) else v
                                                   for k, v in receipt["provenance_manifest"].items()})
        if not RP.verify_research_provenance_manifest_identity(manifest):
            failures.append("MANIFEST_ID_MISMATCH")
        if manifest.output_hash != sha256_hex(canonical_bytes(receipt["core"])):
            failures.append("MANIFEST_OUTPUT_BINDING_MISMATCH")
        for ref in receipt["core"]["sources"]["accepted_references"]:
            if not RP.verify_raw_evidence_reference_identity(rebuild_reference(ref)):
                failures.append("RAW_EVIDENCE_ID_MISMATCH")
                break
    except (TypeError, KeyError, ValueError, AttributeError):
        failures.append("MANIFEST_SHAPE_INVALID")
    expected = finalize_receipt(recomputed_core)
    if receipt["core"] != recomputed_core:
        diff = sorted(k for k in set(recomputed_core) | set(receipt["core"]) if receipt["core"].get(k) != recomputed_core.get(k))
        failures.extend(f"OUTPUT_MISMATCH:{k}" for k in diff)
    elif receipt["provenance_manifest"] != expected["provenance_manifest"]:
        failures.append("MANIFEST_RECOMPUTE_MISMATCH")
    return failures
