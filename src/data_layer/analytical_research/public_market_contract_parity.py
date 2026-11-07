"""Offline public market search + prediction-market identity contract parity (S10-R3-EXT-CONTRACTS-01).

Two pinned upstream contracts are mirrored as CONCEPTS only (no code copied, no SDK, no dependency):

* R3-23 Polymarket/py-sdk @aa94ec431e3d4946576fb7c0d079fe1c14fcf676 ``src/polymarket/clients/public.py``
  ``PublicClient.search`` and ``examples/search.py``: one query returns ONE mixed payload per page with
  ``events`` / ``tags`` / ``profiles``. Here only event -> market research fields are projected onto the
  native PIT universe; tags and profiles are always ``TAG_OR_PROFILE_UNSUPPORTED``.
* R3-27 ccxt/ccxt @28d9b2ca6e06173ce00f020cfd5bfac3275604d4 ``ts/src/prediction/polymarket.ts``
  ``parseEventToMarkets``: market id = conditionId, ``type: prediction``, outcome i paired with
  clobTokenIds[i], binary iff two outcomes. The sibling ``ts/src/polymarket.ts`` is Polymarket
  PERPETUAL FUTURES (``swap: true``) and is refused, never mixed in.

The corpus is only ``alpha_discovery.build_alpha_universe_snapshot`` (via ``source_grounding.load_corpus``)
over a cold-verified S10-R3-SRC-01 scratch. Native snapshots sort ``token_ids`` and ``outcome_labels``
independently, so outcome orientation is ``ORIENTATION_UNPROVEN`` and no tradable side is ever assigned.
The baseline is the merged R3-02 ``source_grounding.rank_markets`` on the identical index and cases.

Posture: research only, stdlib only, read-only, no network, no LLM, no price, order, strategy or live authority.
"""
from __future__ import annotations

from collections import Counter
import json
import math
import re

from src.data_layer.analytical_research import alpha_discovery as AD
from src.data_layer.analytical_research import source_grounding as SG
from src.data_layer.point_in_time_market_research import research_provenance as RP

WP_ID = "S10-R3-EXT-CONTRACTS-01"
CASES_SCHEMA = "s10-r3-ext-contracts01-cases-v1"
RECEIPT_SCHEMA = "s10-r3-ext-contracts01-parity-receipt-v1"
RECEIPT_PREFIX = "pmcparity:sha256:"
CALLER = ("tools/alpha/run_public_market_contract_parity.py:run -> run_source_grounding.verify -> "
          "source_grounding.load_corpus/bind_rule_texts/build_index/rank_markets -> "
          "public_market_contract_parity.field_aware_search")

# Frozen a priori, before the benchmark cases were written.
METHOD_ID = "field_aware_search_v1"
ABLATION_ID = "field_aware_text_only_v1"  # same scorer with caller filters/ids removed (attribution check)
BASELINE_ID = SG.RANKER_ID  # merged R3-02 two-stage BM25
TOP_K = SG.TOP_K
FIELD_WEIGHTS = (("question", 3), ("category", 2), ("rule", 1), ("outcomes", 1), ("date", 1))
MIN_QUERY_COVERAGE = SG.MIN_QUERY_COVERAGE
MAX_QUERY_TERMS = 16
MAX_CASES = 500
MAX_VECTORS = 200
MIN_BENCHMARK_CASES = 50

MARKET_RE = re.compile(r"market:polymarket:(0|[1-9][0-9]{0,39})")
TOKEN_RE = re.compile(r"token:polymarket:[1-9][0-9]{0,79}")
CONDITION_RE = re.compile(r"0x[0-9a-f]{64}")
_DECIMAL_RE = re.compile(r"0|[1-9][0-9]{0,79}")
_CASE_ID_RE = SG._QID_RE

REASONS = ("NOT_IN_UNIVERSE", "AMBIGUOUS", "MISSING_METADATA", "POST_CUTOFF", "NO_ADMISSIBLE_MATCH")
CORPUS_LABEL_SOURCES = {"SANITIZED_SYNTHETIC": "CALLER_SUPPLIED_SYNTHETIC", "LOCAL_REAL_PIT": "CALLER_SUPPLIED_UNVERIFIED"}
CASES_KEYS = {"schema_id", "corpus_class", "grounding_receipt_id", "as_of", "label_source", "benchmark_sha256",
              "cases", "upstream_vectors"}
CASE_KEYS = {"case_id", "decision_time", "query", "expected_market_ids"}
QUERY_KEYS = {"q", "events_status", "events_tag", "market_id", "condition_id", "event_id", "resolution_after",
              "resolution_before", "require_rule"}
VECTOR_GROUPS = {"py_sdk_search", "ccxt_prediction_markets"}
# py-sdk PublicClient.search keyword set at the pin; only the first group maps to native fields.
PY_SDK_SUPPORTED = {"q", "events_status", "events_tag", "page_size", "search_tags", "search_profiles"}
PY_SDK_UNSUPPORTED = {"ascending", "cache", "exclude_tag_ids", "keep_closed_markets", "optimized", "presets",
                      "recurrence", "sort"}
PERPS_MARKERS = ("swap", "future", "contract", "linear", "inverse", "perpetual", "perp", "funding")

SOURCE_PINS = (
    {"capability": "R3-23", "repository": "Polymarket/py-sdk", "commit": "aa94ec431e3d4946576fb7c0d079fe1c14fcf676",
     "files": {"examples/search.py": "895d728f438e42f2b795138b08b308fab568edbc",
               "src/polymarket/clients/public.py": "c0e1d178555604172474ba6031e9ce833f447821"},
     "license": "MIT", "adoption_mode": "CONTRACT_CONCEPT_ONLY_NO_CODE_COPIED"},
    {"capability": "R3-27", "repository": "ccxt/ccxt", "commit": "28d9b2ca6e06173ce00f020cfd5bfac3275604d4",
     "files": {"ts/src/prediction/polymarket.ts": "d7fb1dff7b440c86a987f0f3be948883ae1f0907"},
     "excluded_files": {"ts/src/polymarket.ts": "a428bf5ec948e154d35e9c8b1e2c155c3d6f5a53 PERPETUAL_FUTURES_NOT_PREDICTION"},
     "license": "MIT", "adoption_mode": "CONTRACT_CONCEPT_ONLY_NO_CODE_COPIED"},
)
SAFE_OUTPUT = ("OFFLINE_RESEARCH_ONLY", "PARTIAL_UPSTREAM_CONTRACT_PARITY", "LOCAL_PIT_SOURCE_ORIGIN_UNVERIFIED",
               "OWNER_ACCEPTANCE_PENDING", "NO_PROVIDER_OR_TRADING_AUTHORITY")


def _stop(code: str):
    raise SG.GroundingStop(code)


def _require(condition: bool, code: str) -> None:
    if not condition:
        _stop(code)


def _utc(value: object) -> str | None:
    if type(value) is not str:
        return None
    try:
        canonical = RP.canonicalize_utc_timestamp(value)
    except ValueError:
        return None
    return canonical if canonical == value else None


def _key(value: str):
    return RP._utc_instant_key(value)


# ------------------------------------------------------------------ native identity (R3-27 concept)


def normalize_native(universe: AD.AlphaUniverseSnapshot, rules: dict) -> dict[str, dict]:
    """One explicit identity row per native market; any defect makes the row ABSTAIN (never guessed)."""
    token_owner = Counter(t for m in universe.markets for t in set(m.token_ids))
    condition_markets: dict[str, set] = {}
    condition_events: dict[str, set] = {}
    for m in universe.markets:
        if m.condition_id:
            condition_markets.setdefault(m.condition_id, set()).add(m.market_id)
            condition_events.setdefault(m.condition_id, set()).add(m.event_id)
    rows = {}
    for m in universe.markets:
        defects = []
        if MARKET_RE.fullmatch(m.market_id) is None:
            defects.append("MARKET_ID_NONCANONICAL")
        if any(TOKEN_RE.fullmatch(t) is None for t in m.token_ids):
            defects.append("TOKEN_ID_NONCANONICAL")
        if m.condition_id is None:
            defects.append("CONDITION_ID_MISSING")
        elif CONDITION_RE.fullmatch(m.condition_id) is None:
            defects.append("CONDITION_ID_INVALID")
        elif len(condition_markets[m.condition_id]) > 1:
            defects.append("DUPLICATE_CONDITION")
        if m.condition_id and len(condition_events.get(m.condition_id, ())) > 1:
            defects.append("EVENT_RELATION_CONFLICT")
        if len(m.token_ids) < 2 or len(m.token_ids) != len(m.outcome_labels):
            defects.append("OUTCOME_TOKEN_COUNT_MISMATCH")
        if any(token_owner[t] > 1 for t in m.token_ids):
            defects.append("TOKEN_COLLISION")
        defects += [g for g in ("REQUIRED_METADATA_MISSING", "METADATA_CONFLICT") if g in m.data_gap_codes]
        if _key(m.metadata_observed_time) > _key(universe.as_of):
            defects.append("POST_CUTOFF")
        if not m.question_text:
            defects.append("QUESTION_MISSING")
        rows[m.market_id] = {
            "market_id": m.market_id, "event_id": m.event_id, "event_identity": SG._event_identity(m),
            "condition_id": m.condition_id, "category": m.category, "market_status": m.market_status,
            "resolution_date": m.resolution_date, "product": "PREDICTION_MARKET",
            "market_type": None if len(m.outcome_labels) < 2 else ("binary" if len(m.outcome_labels) == 2 else "categorical"),
            "token_ids": list(m.token_ids), "outcome_labels": list(m.outcome_labels),
            "orientation": "ORIENTATION_UNPROVEN", "orientation_basis": "NATIVE_TOKENS_AND_LABELS_SORTED_INDEPENDENTLY",
            "yes_token_id": None, "tradable_side": None,
            "metadata_record_version_id": m.metadata_record_version_id, "metadata_observed_time": m.metadata_observed_time,
            "metadata_freshness": m.metadata_freshness,
            "rules": [{"resolution_source_id": r.resolution_source_id, "rule_content_sha256": r.rule_content_sha256,
                       "rule_record_version_id": r.rule_record_version_id} for r in m.rules],
            "rule_text_bound": m.market_id in rules, "data_gap_codes": list(m.data_gap_codes),
            "identity_defects": sorted(set(defects)), "identity_status": "ABSTAIN" if defects else "VALID",
            "source_authenticity": "LOCAL_PIT_SOURCE_ORIGIN_UNVERIFIED",
        }
    return rows


def _json_list(value: object):
    """Gamma returns outcomes / clobTokenIds as JSON-encoded strings (CCXT parseJson); lists also accepted."""
    if type(value) is str:
        try:
            value = json.loads(value, parse_constant=lambda _: None)
        except (ValueError, RecursionError):
            return None
    return value if type(value) is list else None


def normalize_ccxt_prediction(vector: object, native: dict[str, dict]) -> dict:
    """Mirror ccxt prediction parseEventToMarkets identity on one offline Gamma-shaped market vector."""
    out = {"vector_id": None, "status": None, "normalized": None, "native_market_id": None, "native_cross_check": None,
           "upstream_yes_token_claim": None, "orientation": "ORIENTATION_UNPROVEN", "tradable_side": None}
    if type(vector) is not dict or set(vector) != {"vector_id", "venue_product", "market"} \
            or type(vector["vector_id"]) is not str or _CASE_ID_RE.fullmatch(vector["vector_id"]) is None \
            or type(vector["market"]) is not dict:
        out["status"] = "VECTOR_FIELDS_INVALID"
        return out
    out["vector_id"] = vector["vector_id"]
    market = vector["market"]
    product = vector["venue_product"]
    # ccxt.polymarket (ts/src/polymarket.ts) is the perpetual-futures venue; only ccxt.prediction.polymarket qualifies.
    perps = product in PERPS_MARKERS or product == "ccxt.polymarket" or any(market.get(k) is True for k in PERPS_MARKERS) \
        or str(market.get("type", "")).casefold() in PERPS_MARKERS
    if perps or product != "prediction":
        out["status"] = "PERPETUAL_PRODUCT_REJECTED" if perps else "PRODUCT_NOT_PREDICTION"
        return out
    labels, tokens = _json_list(market.get("outcomes")), _json_list(market.get("clobTokenIds"))
    condition, gamma_id = market.get("conditionId"), market.get("id")
    if type(condition) is not str or CONDITION_RE.fullmatch(condition) is None:
        out["status"] = "CONDITION_ID_INVALID"
    elif type(gamma_id) is not str or _DECIMAL_RE.fullmatch(gamma_id) is None:
        out["status"] = "MARKET_ID_NONCANONICAL"
    elif not labels or not tokens or any(type(x) is not str or not x for x in labels):
        out["status"] = "OUTCOMES_MISSING"
    elif any(type(t) is not str or _DECIMAL_RE.fullmatch(t) is None or t == "0" for t in tokens):
        out["status"] = "TOKEN_ID_NONCANONICAL"
    elif len(labels) != len(tokens):
        out["status"] = "OUTCOME_TOKEN_LENGTH_MISMATCH"  # CCXT pairs positionally and skips; strict here
    elif len(set(tokens)) != len(tokens):
        out["status"] = "TOKEN_COLLISION"
    elif len(set(labels)) != len(labels):
        out["status"] = "OUTCOME_LABEL_DUPLICATE"
    if out["status"]:
        return out
    closed = market.get("closed") is True
    out["normalized"] = {
        "id": condition, "baseId": condition, "type": "prediction", "prediction": True, "spot": False, "swap": False,
        "future": False, "contract": False, "marketType": "binary" if len(labels) == 2 else "categorical",
        "active": market.get("active") is True and not closed,
        "resolved": closed or str(market.get("umaResolutionStatus", "")).casefold() == "resolved",
        "outcomes": [{"outcomeId": "token:polymarket:" + t, "label": label, "position": i}
                     for i, (label, t) in enumerate(zip(labels, tokens))]}
    if sorted(labels) == ["No", "Yes"]:
        out["upstream_yes_token_claim"] = "token:polymarket:" + tokens[labels.index("Yes")]
    out["orientation_basis"] = "UPSTREAM_POSITIONAL_ORDER_NOT_INDEPENDENTLY_VERIFIED"
    market_id = "market:polymarket:" + gamma_id
    row = native.get(market_id)
    out["native_market_id"] = market_id
    if row is None:
        check = "NOT_IN_UNIVERSE"
    elif row["identity_status"] != "VALID":
        check = "NATIVE_IDENTITY_ABSTAINED"
    elif row["condition_id"] != condition or set(row["token_ids"]) != {o["outcomeId"] for o in out["normalized"]["outcomes"]} \
            or set(row["outcome_labels"]) != set(labels):
        check = "IDENTITY_CONFLICT"
    else:
        check = "IDENTITY_CONSISTENT"
    out.update(status="NORMALIZED", native_cross_check=check)
    return out


def evaluate_ccxt_vectors(vectors: list, native: dict[str, dict]) -> dict:
    rows = [normalize_ccxt_prediction(v, native) for v in vectors]
    claims: dict[str, set] = {}
    for r in rows:
        if r["status"] == "NORMALIZED":
            claims.setdefault(r["native_market_id"], set()).add(r["upstream_yes_token_claim"])
    for r in rows:
        if r["status"] == "NORMALIZED" and len(claims[r["native_market_id"]]) > 1:
            r["orientation_flag"] = "UPSTREAM_ORIENTATION_CLAIMS_DISAGREE"
    return {"vectors": rows, "status_counts": dict(sorted(Counter(r["status"] for r in rows).items())),
            "cross_check_counts": dict(sorted(Counter(r["native_cross_check"] for r in rows if r["native_cross_check"]).items())),
            "orientation_proven": 0, "tradable_sides_assigned": 0}


# ------------------------------------------------------------------ field-aware search


def build_field_index(universe: AD.AlphaUniverseSnapshot, rules: dict, native: dict[str, dict]) -> dict:
    docs = {}
    for m in universe.markets:
        date = []
        if m.resolution_date and len(m.resolution_date) >= 7 and m.resolution_date[5:7] in {f"{i:02d}" for i in range(1, 13)}:
            date = [m.resolution_date[:4], SG._MONTHS[int(m.resolution_date[5:7]) - 1]]
        docs[m.market_id] = {"question": set(SG.tokenize(m.question_text)), "category": set(SG.tokenize(m.category)),
                             "rule": set(SG.tokenize(rules.get(m.market_id, {}).get("text"))),
                             "outcomes": set(SG.tokenize(" ".join(m.outcome_labels))), "date": set(date)}
    admissible = [k for k, row in native.items() if row["identity_status"] == "VALID"]
    df = Counter(t for k in admissible for t in set().union(*docs[k].values()))
    n = len(admissible)
    return {"native": native, "docs": docs, "admissible": admissible, "as_of": universe.as_of,
            "idf": {t: math.log(1 + n / f) for t, f in df.items()}}


def query_terms(query: dict) -> list[str]:
    return sorted(set(SG.tokenize(query.get("q"))))[:MAX_QUERY_TERMS]


def _filter(row: dict, query: dict) -> str | None:
    """None = passes; otherwise the exclusion reason for this market."""
    for field, column in (("events_status", "market_status"), ("events_tag", "category")):
        if query.get(field) is not None:
            if row[column] is None:
                return "MISSING_METADATA"
            if row[column].casefold() != query[field].casefold():
                return "FILTERED"
    for field, later in (("resolution_after", True), ("resolution_before", False)):
        if query.get(field) is not None:
            date = _utc(row["resolution_date"])  # a non-canonical native date is missing, never a crash
            if date is None:
                return "MISSING_METADATA"
            if (_key(date) > _key(query[field])) != later or date == query[field]:
                return "FILTERED"
    if query.get("require_rule") is True and not row["rules"]:
        return "MISSING_METADATA"
    return None


def field_aware_search(index: dict, query: dict) -> dict:
    native = index["native"]
    exact = {k: query.get(k) for k in ("market_id", "condition_id", "event_id") if query.get(k) is not None}
    pool = [k for k, row in native.items() if all(row[f] == v for f, v in exact.items())]
    if exact and not pool:
        return {"ranked": [], "status": "ABSTAINED", "reason": "NOT_IN_UNIVERSE", "excluded": {}, "coverage": None}
    excluded = Counter()
    candidates = []
    for key in pool:
        row = native[key]
        if row["identity_status"] != "VALID":
            excluded["POST_CUTOFF" if "POST_CUTOFF" in row["identity_defects"] else "IDENTITY_ABSTAINED"] += 1
            continue
        reason = _filter(row, query)
        if reason:
            excluded[reason] += 1
            continue
        candidates.append(key)
    terms = query_terms(query)
    result = {"ranked": [], "status": "ABSTAINED", "reason": None, "excluded": dict(sorted(excluded.items())), "coverage": None}
    if not candidates:
        result["reason"] = next((r for r in ("POST_CUTOFF", "MISSING_METADATA") if excluded[r]), "NO_ADMISSIBLE_MATCH")
        return result
    if not terms:
        if not exact:
            result["reason"] = "NO_ADMISSIBLE_MATCH"
            return result
        return dict(result, ranked=sorted(candidates)[:TOP_K], status="RANKED", scores=["exact"] * min(len(candidates), TOP_K))
    scored = []
    for key in candidates:
        doc = index["docs"][key]
        score = sum(max((w for f, w in FIELD_WEIGHTS if t in doc[f]), default=0) * index["idf"].get(t, 0.0) for t in terms)
        hits = sum(1 for t in terms if any(t in doc[f] for f, _ in FIELD_WEIGHTS))
        if score > 0:
            scored.append((-round(score, 9), key, hits))
    scored.sort()
    if not scored:
        result["reason"] = "NO_ADMISSIBLE_MATCH"
        return result
    result["coverage"] = SG._ratio(scored[0][2], len(terms))
    if scored[0][2] / len(terms) < MIN_QUERY_COVERAGE:
        result["reason"] = "NO_ADMISSIBLE_MATCH"
        return result
    if len(scored) > 1 and scored[1][0] == scored[0][0] and native[scored[1][1]]["event_id"] != native[scored[0][1]]["event_id"]:
        result["reason"] = "AMBIGUOUS"  # exact tie across events: conservative abstention, never a coin flip
        return result
    top = scored[:TOP_K]
    return dict(result, ranked=[k for _, k, _ in top], status="RANKED", scores=[f"{-s:.6f}" for s, _, _ in top])


def native_search_page(index: dict, request: dict) -> dict:
    """py-sdk shaped single payload (events/tags/profiles) produced from the native field-aware search."""
    query = {"q": request.get("q"), "events_status": request.get("events_status"), "events_tag": request.get("events_tag")}
    found = field_aware_search(index, query)
    size = request.get("page_size", TOP_K)
    events: dict[str, list] = {}
    for key in found["ranked"][:size]:
        events.setdefault(index["native"][key]["event_id"], []).append(key)
    return {"events": [{"id": e, "market_ids": ids} for e, ids in events.items()], "tags": [], "profiles": [],
            "tags_status": "TAG_OR_PROFILE_UNSUPPORTED" if request.get("search_tags") else "NOT_REQUESTED",
            "profiles_status": "TAG_OR_PROFILE_UNSUPPORTED" if request.get("search_profiles") else "NOT_REQUESTED",
            "items_per_page": 1, "search_status": found["status"], "search_reason": found["reason"]}


def project_py_sdk_search(vector: object, index: dict) -> dict:
    """Project one offline py-sdk search vector (request + one results page) onto the native universe."""
    out = {"vector_id": None, "status": "VECTOR_FIELDS_INVALID", "parameters": {}, "events": [], "tags": [], "profiles": [],
           "native_page": None, "agreement": None}
    if type(vector) is not dict or set(vector) != {"vector_id", "request", "response_page"} \
            or type(vector["vector_id"]) is not str or _CASE_ID_RE.fullmatch(vector["vector_id"]) is None \
            or type(vector["request"]) is not dict or type(vector["response_page"]) is not dict:
        return out
    out["vector_id"] = vector["vector_id"]
    request, page = vector["request"], vector["response_page"]
    params = {k: ("SUPPORTED" if k in PY_SDK_SUPPORTED else "PARAMETER_UNSUPPORTED" if k in PY_SDK_UNSUPPORTED
                  else "PARAMETER_UNKNOWN") for k in sorted(request)}
    out["parameters"] = params
    size = request.get("page_size", TOP_K)
    if type(request.get("q")) is not str or not request["q"].strip() or type(size) is not int or not 1 <= size <= TOP_K \
            or any(request.get(k) is not None and type(request[k]) is not str for k in ("events_status", "events_tag")) \
            or any(request.get(k) is not None and type(request[k]) is not bool for k in ("search_tags", "search_profiles")) \
            or not set(page) <= {"events", "tags", "profiles"} or any(type(page.get(k, [])) is not list for k in ("events", "tags", "profiles")):
        out["status"] = "REQUEST_OR_PAGE_INVALID"
        return out
    native = index["native"]
    upstream_markets = set()
    for event in page.get("events", []):
        row = {"event_id": event.get("id") if isinstance(event, dict) else None, "status": None, "native_market_ids": [],
               "native_event_ids": []}
        markets = event.get("markets") if isinstance(event, dict) else None
        if type(markets) is not list or type(row["event_id"]) is not str or not markets:
            row["status"] = "EVENT_FIELDS_INVALID"
        else:
            for m in markets:
                gid = m.get("id") if isinstance(m, dict) else None
                key = "market:polymarket:" + gid if type(gid) is str and _DECIMAL_RE.fullmatch(gid) else None
                if key is None or key not in native:
                    row["status"] = row["status"] or "NOT_IN_UNIVERSE"
                    continue
                if native[key]["identity_status"] != "VALID" or m.get("conditionId") != native[key]["condition_id"]:
                    row["status"] = "IDENTITY_CONFLICT"
                    continue
                row["native_market_ids"].append(key)
            row["native_event_ids"] = sorted({native[k]["event_id"] for k in row["native_market_ids"]})
            if len(row["native_event_ids"]) > 1:
                row["status"] = "EVENT_RELATION_CONFLICT"
            row["status"] = row["status"] or "EVENT_PROJECTED"
            row["event_identity"] = ("EVENT_ID_MATCHES_NATIVE" if row["native_event_ids"] == ["event:polymarket:" + row["event_id"]]
                                     else "EVENT_ID_UNVERIFIED")
            if row["status"] == "EVENT_PROJECTED":
                upstream_markets.update(row["native_market_ids"])
        out["events"].append(row)
    out["tags"] = ["TAG_OR_PROFILE_UNSUPPORTED" for _ in page.get("tags", [])]
    out["profiles"] = ["TAG_OR_PROFILE_UNSUPPORTED" for _ in page.get("profiles", [])]
    out["native_page"] = native_search_page(index, request)
    mine = {k for e in out["native_page"]["events"] for k in e["market_ids"]}
    out["agreement"] = {"upstream_projected_markets": len(upstream_markets), "native_page_markets": len(mine),
                        "shared": len(upstream_markets & mine), "parity": "PARTIAL_EVENT_MARKET_ONLY"}
    out["status"] = "PROJECTED"
    return out


# ------------------------------------------------------------------ cases + benchmark


def scan_material(value: object, key: str | None = None, depth: int = 0) -> None:
    """Credential-shaped keys or values reject the file. A canonical condition id is 0x+64 hex, the same
    shape SG.SECRET_RE treats as a private key, so it is exempt only as the value of a condition-id key."""
    _require(depth <= 12, "CASES_TOO_DEEP")
    if isinstance(value, dict):
        for k, item in value.items():
            _require(not any(p in k.casefold() for p in SG.SECRET_KEY_PARTS), "FORBIDDEN_FIELD")
            scan_material(k, None, depth + 1)
            scan_material(item, k, depth + 1)
    elif isinstance(value, list):
        for item in value:
            scan_material(item, key, depth + 1)
    elif isinstance(value, str) and not (key in ("conditionId", "condition_id") and CONDITION_RE.fullmatch(value)):
        _require(SG.SECRET_RE.search(value) is None, "SECRET_MATERIAL_REJECTED")


def validate_cases(cases: object) -> None:
    """Whole-file structure only; per-case defects are counted (never silently dropped)."""
    _require(isinstance(cases, dict) and set(cases) == CASES_KEYS, "CASES_FIELDS_INVALID")
    _require(cases["schema_id"] == CASES_SCHEMA, "CASES_SCHEMA_INVALID")
    _require(cases["corpus_class"] in CORPUS_LABEL_SOURCES, "CORPUS_CLASS_INVALID")
    _require(cases["label_source"] == CORPUS_LABEL_SOURCES[cases["corpus_class"]], "LABEL_SOURCE_INVALID")
    _require(type(cases["grounding_receipt_id"]) is str
             and re.fullmatch(re.escape(SG.RECEIPT_PREFIX) + "[0-9a-f]{64}", cases["grounding_receipt_id"]) is not None,
             "GROUNDING_RECEIPT_ID_INVALID")
    _require(_utc(cases["as_of"]) is not None, "AS_OF_INVALID")
    _require(type(cases["benchmark_sha256"]) is str and SG._SHA_RE.fullmatch(cases["benchmark_sha256"]) is not None,
             "BENCHMARK_SHA_INVALID")
    _require(type(cases["cases"]) is list and 0 < len(cases["cases"]) <= MAX_CASES, "CASES_LIST_INVALID")
    vectors = cases["upstream_vectors"]
    _require(type(vectors) is dict and set(vectors) == VECTOR_GROUPS
             and all(type(v) is list and len(v) <= MAX_VECTORS for v in vectors.values()), "UPSTREAM_VECTORS_INVALID")


def benchmark_commitment(cases: dict) -> str:
    """Frozen BEFORE comparison: method settings plus every case id, query and expected label."""
    return SG.sha256_hex(SG.canonical_bytes({
        "method_id": METHOD_ID, "ablation_id": ABLATION_ID, "baseline_id": BASELINE_ID, "top_k": TOP_K,
        "field_weights": [list(w) for w in FIELD_WEIGHTS], "min_query_coverage": str(MIN_QUERY_COVERAGE),
        "cases": cases["cases"]}))


def _case_check(case: object, native: dict, seen: set, as_of: str) -> tuple[str, str | None]:
    if type(case) is not dict or set(case) != CASE_KEYS or type(case["case_id"]) is not str \
            or _CASE_ID_RE.fullmatch(case["case_id"]) is None or type(case["query"]) is not dict \
            or not set(case["query"]) <= QUERY_KEYS or type(case["expected_market_ids"]) is not list \
            or any(type(x) is not str for x in case["expected_market_ids"]):
        return "REFUSED", "CASE_FIELDS_INVALID"
    query = case["query"]
    if case["case_id"] in seen:
        return "REFUSED", "DUPLICATE_CASE_ID"
    if any(query.get(k) is not None and type(query[k]) is not str for k in QUERY_KEYS - {"require_rule"}) \
            or query.get("require_rule") not in (None, True, False) \
            or any(query.get(k) is not None and _utc(query[k]) is None for k in ("resolution_after", "resolution_before")):
        return "REFUSED", "QUERY_FIELDS_INVALID"
    if query.get("market_id") is not None and MARKET_RE.fullmatch(query["market_id"]) is None \
            or query.get("condition_id") is not None and CONDITION_RE.fullmatch(query["condition_id"]) is None:
        return "REFUSED", "EXACT_ID_NONCANONICAL"
    if not query_terms(query) and not any(query.get(k) for k in ("market_id", "condition_id", "event_id")):
        return "REFUSED", "QUERY_EMPTY"
    if len(set(case["expected_market_ids"])) != len(case["expected_market_ids"]):
        return "REFUSED", "DUPLICATE_LABEL"
    if any(x not in native for x in case["expected_market_ids"]):
        return "REFUSED", "LABEL_NOT_IN_CORPUS"
    if case["decision_time"] is not None and (_utc(case["decision_time"]) is None):
        return "REFUSED", "DECISION_TIME_INVALID"
    if case["decision_time"] is not None and _key(case["decision_time"]) < _key(as_of):
        return "ABSTAINED", "POST_CUTOFF"  # the snapshot is later than the decision: would leak future state
    return "VALID", None


def run_benchmark(cases: dict, universe: AD.AlphaUniverseSnapshot, bm25_index: dict, index: dict) -> dict:
    rows, seen = [], set()
    for case in cases["cases"]:
        status, reason = _case_check(case, index["native"], seen, universe.as_of)
        row = {"case_id": case.get("case_id") if isinstance(case, dict) and type(case.get("case_id")) is str else None,
               "status": status, "reason": reason, "relevant": [], "exact_id": False,
               METHOD_ID: [], ABLATION_ID: [], BASELINE_ID: [], "method_status": None, "method_reason": None,
               "baseline_status": None, "ablation_status": None}
        if row["case_id"]:
            seen.add(row["case_id"])
        if status == "VALID":
            query = case["query"]
            found = field_aware_search(index, query)
            ablation = field_aware_search(index, {"q": query.get("q")})
            baseline = SG.rank_markets(bm25_index, query.get("q") or "")
            row.update(relevant=sorted(case["expected_market_ids"]),
                       exact_id=any(query.get(k) for k in ("market_id", "condition_id", "event_id")),
                       method_status=found["status"], method_reason=found["reason"], method_excluded=found["excluded"],
                       ablation_status=ablation["status"], baseline_status=baseline["status"])
            row[METHOD_ID], row[ABLATION_ID], row[BASELINE_ID] = found["ranked"], ablation["ranked"], baseline["ranked"]
        rows.append(row)
    valid = [r for r in rows if r["status"] == "VALID"]
    status = "COMPLETED" if len(valid) >= MIN_BENCHMARK_CASES else "BENCHMARK_REFUSED"
    metrics = None
    if status == "COMPLETED":
        metrics = {}
        for method in (METHOD_ID, ABLATION_ID, BASELINE_ID):
            m = SG._method_metrics(rows, method)
            pos = [r for r in valid if r["relevant"]]
            m["false_top1_matches"] = SG._ratio(sum(1 for r in pos if r[method] and r[method][0] not in r["relevant"]),
                                                sum(1 for r in pos if r[method]))
            exact = [r for r in valid if r["exact_id"]]
            m["false_exact_matches"] = SG._ratio(sum(1 for r in exact if r[method] and r[method][0] not in r["relevant"]), len(exact))
            metrics[method] = m
    return {
        "status": status, "refusal_reason": None if status == "COMPLETED" else "FEWER_THAN_FIFTY_VALID_CASES",
        "denominators": {"cases_input": len(rows), "cases_valid_paired": len(valid),
                         "cases_refused": sum(1 for r in rows if r["status"] == "REFUSED"),
                         "cases_abstained_pre_scoring": sum(1 for r in rows if r["status"] == "ABSTAINED"),
                         "positive_labeled": sum(1 for r in valid if r["relevant"]),
                         "negative_no_match": sum(1 for r in valid if not r["relevant"]),
                         "exact_identifier_cases": sum(1 for r in valid if r["exact_id"]),
                         "excluded_by_reason": dict(sorted(Counter(r["reason"] for r in rows if r["reason"]).items())),
                         "snapshot_time_conflicts": sum(1 for r in rows if r["reason"] == "POST_CUTOFF")},
        "method_abstention_reasons": dict(sorted(Counter(r["method_reason"] for r in valid if r["method_reason"]).items())),
        "corpus_sha256": SG.sha256_hex(SG.canonical_bytes(cases["cases"])),
        "metrics": metrics,
        "lift_claim": None,
        "real_value": "NOT_VERIFIED",
        "cases": rows,
    }


# ------------------------------------------------------------------ receipt core


def build_parity_core(cases: dict, grounding_case: dict, grounding_inputs, read_grounding, code_identity: str,
                      grounding_verification: dict, file_hashes: dict) -> dict:
    validate_cases(cases)
    _require(benchmark_commitment(cases) == cases["benchmark_sha256"], "BENCHMARK_FREEZE_MISMATCH")
    _require(cases["grounding_receipt_id"] == grounding_verification["receipt_id"], "GROUNDING_RECEIPT_MISMATCH")
    _require(isinstance(grounding_case, dict) and grounding_case.get("corpus_class") == cases["corpus_class"],
             "CORPUS_CLASS_MISMATCH")
    as_of = RP.canonicalize_utc_timestamp(grounding_case["as_of"])
    _require(cases["as_of"] == as_of, "AS_OF_CONFLICT")
    policy, universe = SG.load_corpus(grounding_inputs / "pit.sqlite3", grounding_case["policy"], as_of)
    rules, rule_outcomes = SG.bind_rule_texts(universe, grounding_case["rule_texts"], read_grounding)
    native = normalize_native(universe, rules)
    index = build_field_index(universe, rules, native)
    bm25 = SG.build_index(universe, rules)
    bench = run_benchmark(cases, universe, bm25, index)
    vectors = cases["upstream_vectors"]
    py_sdk = [project_py_sdk_search(v, index) for v in vectors["py_sdk_search"]]
    real = cases["corpus_class"] == "LOCAL_REAL_PIT"
    core = {
        "schema_id": RECEIPT_SCHEMA, "wp_id": WP_ID, "posture": SG.RESEARCH_ONLY, "safe_output": list(SAFE_OUTPUT),
        "corpus_class": cases["corpus_class"], "label_source": cases["label_source"], "caller": CALLER,
        "code_identity": code_identity, "source_pins": [dict(p) for p in SOURCE_PINS],
        "method": {"method_id": METHOD_ID, "ablation_id": ABLATION_ID, "baseline_id": BASELINE_ID, "top_k": TOP_K,
                   "field_weights": [list(w) for w in FIELD_WEIGHTS], "min_query_coverage": str(MIN_QUERY_COVERAGE),
                   "max_query_terms": MAX_QUERY_TERMS, "reason_labels": list(REASONS)},
        "inputs": {"as_of": as_of, "file_sha256": file_hashes, "grounding_receipt_id": grounding_verification["receipt_id"],
                   "grounding_verification": grounding_verification["status"],
                   "alpha_discovery_policy_id": policy.alpha_discovery_policy_id,
                   "alpha_universe_snapshot_id": universe.alpha_universe_snapshot_id,
                   "benchmark_sha256": cases["benchmark_sha256"]},
        "corpus": {"markets_total": len(native), "identity_valid": len(index["admissible"]),
                   "identity_defect_counts": dict(sorted(Counter(d for r in native.values() for d in r["identity_defects"]).items())),
                   "rule_text_bound": len(rules), "rule_text_entries": rule_outcomes,
                   "orientation_proven": 0, "source_authenticity": "LOCAL_PIT_SOURCE_ORIGIN_UNVERIFIED",
                   "markets": [native[k] for k in sorted(native)]},
        "upstream_contracts": {
            "R3-23_py_sdk_search": {"vectors": py_sdk,
                                    "status_counts": dict(sorted(Counter(v["status"] for v in py_sdk).items())),
                                    "tags_unsupported": sum(len(v["tags"]) for v in py_sdk),
                                    "profiles_unsupported": sum(len(v["profiles"]) for v in py_sdk),
                                    "online_fetch": False},
            "R3-27_ccxt_prediction": evaluate_ccxt_vectors(vectors["ccxt_prediction_markets"], native),
        },
        "benchmark": bench,
        "real_benchmark": ("OBSERVED_CALLER_LABELS_AWAITING_INDEPENDENT_REVIEW" if real
                           else "NOT_RUN_NO_GENUINE_LOCAL_REAL_PIT_SUPPLIED"),
        "adoption": {"R3-23": "PARTIAL_OFFLINE_PARITY_OWNER_ACCEPTANCE_PENDING",
                     "R3-27": "PARTIAL_OFFLINE_PARITY_OWNER_ACCEPTANCE_PENDING",
                     "R3-24": "OPEN_SEPARATE", "other_parity_ids": "OPEN_UNCHANGED_10",
                     "provider_lanes": "SIX_SEPARATE_OWNER_GATES_UNCHANGED", "lane_b": "SEPARATE_OWNER_UNCHANGED",
                     "real_hermes_and_outcome_backlog": "OPEN_UNCHANGED", "capability_register_total": 36,
                     "new_value_acceptances": 0},
        "authority": {"research_only": True, "advisory_only": True, "human_review_required": True,
                      "alpha_promotion": False, "canonical_writes": False, "wp170_registry_writes": False,
                      "tradable_side": False, "orders": False, "strategy": False, "paper": False, "live": False,
                      "capital": False, "llm_or_hermes": False, "network_calls": 0, "provider_calls": 0,
                      "credentials": False},
    }
    return json.loads(SG.canonical_bytes(core))


def finalize(core: dict) -> dict:
    return {"core": core, "receipt_id": RECEIPT_PREFIX + SG.sha256_hex(SG.canonical_bytes({"core": core}))}
