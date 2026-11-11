"""Offline independent forecasting, stratified cohort and same-case scoring (S10-R3-FORECAST-01).

Input is a cold-verified S10-R3-SRC-01 grounding scratch (its frozen native PIT universe and
hash-bound rule bytes) plus a caller case file of targets and resolved history. Pinned external
method families are ADAPTED (algorithm/concept only, no code copied, no dependency):

* R3-01 Metaculus/forecasting-tools@a54dd64 ``forecast_bots/forecast_bot.py``: forecast-or-refuse
  protocol with producer lineage; here one deterministic producer, repetitions never independent.
* R3-06 gnosis/prediction-market-agent-tooling@817117d ``benchmark/benchmark.py``: same-case
  outcomes with abstention, error and cost accounting per method.
* R3-10 YichengYang-Ethan/prediction-market-pricing@04b916c ``identification/external_benchmark.py``:
  exogenous prior kept separate from market-derived inputs (only the separation; no benchmark data).
* R3-10-WANG same pin ``models/hierarchical_wang_mle.py``: intercept-only probit distortion
  Pr(y=1) = Phi(Phi^-1(p) - lambda), bounded scalar MLE on lambda in [-1, 1], p clipped 1e-6,
  Phi clipped 1e-12, training prices in [0.05, 0.95]. Always MARKET_PRICE_DERIVED.
* R3-12 / R3-12-SAMPLER forecastingresearch/forecastbench@e8d3c94 ``question_sampling/_sampling.py``:
  composite-bin stratification with largest-remainder quota apportionment and a seeded draw;
  here the draw is SHA-256 ordering so it is platform independent.
* R3-20 Metaculus/metaculus@bfae5fe ``scoring/score_math.py``: binary baseline score
  100 * ln(2q) / ln(2) as a parity reference next to Brier and log loss.
* R3-18 metac-bot-template@bcbd016 and R3-22 forecastbench-sim@27776fc: protocol / adversarial
  contract tests only (the tests are independently authored; no GPL or unlicensed code copied).

S10-R3-FORECAST-WP170-BIND-01 binds each eligible target to at most one native WP170 ``ResearchSample``
(embedded in the verified ``ResearchDatasetManifest``) and its ``TemporalSplitManifest`` role, with native
``experiment_os.membership_hash`` values, in v2 receipts. Unbound cases are counted per reason. v1 receipts
still replay in their original shape.

Posture: research only, stdlib only, read-only over native stores, no network, no LLM/Hermes,
no price/edge/strategy/paper/order/live authority. Scores are DIAGNOSTIC_ONLY research evidence.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime
from decimal import ROUND_HALF_EVEN, Decimal, localcontext
import hashlib
import json
import math
from pathlib import Path
import re
from statistics import NormalDist

from src.data_layer.analytical_research import experiment_os as EOS
from src.data_layer.analytical_research import experiment_registry as ER
from src.data_layer.analytical_research import source_grounding as SG
from src.data_layer.point_in_time_market_research import research_provenance as RP

WP_ID = "S10-R3-FORECAST-01"
CASES_SCHEMA = "s10-r3-forecast01-cases-v1"
# v1 receipts (S10-R3-FORECAST-01) replay unchanged; v2 adds the WP170 per-case membership block.
LEGACY_RECEIPT_SCHEMA = "s10-r3-forecast01-score-receipt-v1"
RECEIPT_SCHEMA = "s10-r3-forecast01-score-receipt-v2"
RECEIPT_SCHEMAS = (LEGACY_RECEIPT_SCHEMA, RECEIPT_SCHEMA)
# code_identity() of the four identity files at merged main c249409 (the last v1-producing code), LF bytes.
LEGACY_V1_CODE_IDENTITY = "code:sha256:1309f030573183d99c6b9ee5a7b281bcf07fcbf19667946b09eb53568ea419ed"
BINDING_WP_ID = "S10-R3-FORECAST-WP170-BIND-01"
RECEIPT_PREFIX = "fcsteval:sha256:"
CALLER = ("tools/alpha/run_forecast_evaluation.py:run -> run_source_grounding.verify -> "
          "forecast_evaluation.build_evaluation_core")

EPSILON = Decimal("1e-12")  # declared log-loss clip; every clipped forecast is counted
Q12 = Decimal("0.000000000001")
WANG_P_CLIP = 1e-6
WANG_PHI_CLIP = 1e-12
WANG_LAMBDA_BOUNDS = (-1.0, 1.0)
WANG_PRICE_RANGE = (Decimal("0.05"), Decimal("0.95"))
WANG_ITERATIONS = 120
MAX_ITEMS = 2000

INDEPENDENT = "independent_stratum_prior_v1"
BASE_RATE = "train_base_rate_global_v1"
MARKET = "market_reference_price_v1"
WANG = "wang_probit_distortion_v1"
METHODS = (INDEPENDENT, BASE_RATE, MARKET, WANG)
PRIMARY_METHODS = (INDEPENDENT, BASE_RATE, MARKET)
LINEAGE = {INDEPENDENT: "EXOGENOUS", BASE_RATE: "EXOGENOUS", MARKET: "MARKET_PRICE", WANG: "MARKET_PRICE_DERIVED"}
COST = {"classification": "LOCAL_CPU_ONLY", "provider_calls": 0, "network_calls": 0, "spend_usd": "0"}

CORPUS_CLASSES = ("SANITIZED_SYNTHETIC", "LOCAL_REAL_PIT")
OUTCOME_PROVENANCE = {"SANITIZED_SYNTHETIC": "SANITIZED_SYNTHETIC_LABEL", "LOCAL_REAL_PIT": "LOCAL_RESOLUTION_RECORD"}
CASES_KEYS = {"schema_id", "case_label", "corpus_class", "grounding_receipt_id", "wp170", "method", "sampler",
              "scoring_cutoff", "history", "targets"}
METHOD_KEYS = {"prior_alpha", "prior_beta", "min_training_n", "wang_min_training_n", "horizon_edges_days",
               "price_edges", "max_price_age_seconds"}
SAMPLER_KEYS = {"seed", "sample_n"}
WP170_KEYS = {"registry_file", "experiment_id"}
TARGET_KEYS = {"case_id", "market_id", "question_sha256", "rule_content_sha256", "yes_label", "decision_time",
               "market_price", "price_observed_time", "outcome"}
OUTCOME_KEYS = {"label", "resolved_time", "known_time", "provenance"}
HISTORY_KEYS = {"history_id", "event_group", "category", "decision_time", "resolution_time", "resolution_known_time",
                "source_observed_time", "evidence_capture", "outcome", "market_price", "price_observed_time"}
CRYPTO_CATEGORIES = ("crypto", "cryptocurrency", "bitcoin", "ethereum")
# Price is a legitimate research field here, so unlike SRC-01 it is not a forbidden key word.
TRADE_KEY_WORDS = ("order", "orders", "side", "size", "amount", "signature", "stake", "bet", "fill", "position")

_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,95}")
_SHA_RE = re.compile(r"[0-9a-f]{64}")
_PROB_RE = re.compile(r"0|1|0\.[0-9]{0,11}[1-9]")  # canonical: no sign, exponent, trailing zero or > 12 dp
_POS_DEC_RE = re.compile(r"[1-9][0-9]{0,3}|(0|[1-9][0-9]{0,3})\.[0-9]{0,5}[1-9]")


class EvaluationStop(Exception):
    """Whole-run fail-closed stop with a stable code; never carries input values."""


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise EvaluationStop(code)


def _int(value: object, low: int, high: int) -> bool:
    return type(value) is int and low <= value <= high  # bool is rejected by the exact type check


def _utc(value: object) -> str | None:
    """Canonical UTC string or None when invalid (non-string, naive, offset, malformed)."""
    try:
        return RP.canonicalize_utc_timestamp(value)
    except ValueError:
        return None


def _key(ts: str):
    return RP._utc_instant_key(ts)


def _seconds(start: str, end: str) -> int:
    parse = lambda s: datetime.fromisoformat(s.replace("Z", "+00:00"))  # noqa: E731
    return math.floor((parse(end) - parse(start)).total_seconds())


def _q(value: Decimal) -> str:
    return str(value.quantize(Q12, rounding=ROUND_HALF_EVEN))


def _ratio(numerator: int, denominator: int) -> dict:
    value = None if denominator == 0 else _q(Decimal(numerator) / Decimal(denominator))
    return {"numerator": numerator, "denominator": denominator, "value": value}


def _prob(value: object) -> Decimal | None:
    return Decimal(value) if type(value) is str and _PROB_RE.fullmatch(value) else None


def _scan_forbidden(value: object, depth: int = 0) -> None:
    _require(depth <= 8, "CASES_TOO_DEEP")
    if isinstance(value, dict):
        for key, item in value.items():
            lowered = key.casefold()
            _require(not any(p in lowered for p in SG.SECRET_KEY_PARTS), "FORBIDDEN_FIELD")
            _require(not set(re.split(r"[^a-z0-9]+", lowered)) & set(TRADE_KEY_WORDS), "FORBIDDEN_FIELD")
            _scan_forbidden(item, depth + 1)
    elif isinstance(value, list):
        for item in value:
            _scan_forbidden(item, depth + 1)


# ------------------------------------------------------------------ whole-case structure


def validate_cases(cases: object, *, frozen: bool) -> None:
    """Whole-run structure; per-target and per-history defects are counted later, never dropped."""
    _require(isinstance(cases, dict), "CASES_JSON_INVALID")
    _scan_forbidden(cases)
    _require(set(cases) == CASES_KEYS, "CASES_FIELDS_INVALID")
    _require(cases["schema_id"] == CASES_SCHEMA, "CASES_SCHEMA_INVALID")
    _require(type(cases["case_label"]) is str and _ID_RE.fullmatch(cases["case_label"]) is not None, "CASE_LABEL_INVALID")
    _require(cases["corpus_class"] in CORPUS_CLASSES, "CORPUS_CLASS_INVALID")
    _require(type(cases["grounding_receipt_id"]) is str and re.fullmatch(re.escape(SG.RECEIPT_PREFIX) + "[0-9a-f]{64}",
             cases["grounding_receipt_id"]) is not None, "GROUNDING_RECEIPT_ID_INVALID")
    _require(_utc(cases["scoring_cutoff"]) is not None, "SCORING_CUTOFF_INVALID")
    m = cases["method"]
    _require(type(m) is dict and set(m) == METHOD_KEYS, "METHOD_INVALID")
    _require(all(type(m[k]) is str and _POS_DEC_RE.fullmatch(m[k]) and Decimal(m[k]) > 0 for k in ("prior_alpha", "prior_beta")),
             "METHOD_INVALID")
    _require(_int(m["min_training_n"], 1, 100000) and _int(m["wang_min_training_n"], 2, 100000)
             and _int(m["max_price_age_seconds"], 1, 10 ** 8), "METHOD_INVALID")
    edges = m["horizon_edges_days"]
    _require(type(edges) is list and 0 < len(edges) <= 12 and all(_int(e, 1, 36500) for e in edges)
             and edges == sorted(set(edges)), "METHOD_INVALID")
    prices = m["price_edges"]
    _require(type(prices) is list and 0 < len(prices) <= 19 and all(_prob(p) is not None and 0 < _prob(p) < 1 for p in prices)
             and [_prob(p) for p in prices] == sorted({_prob(p) for p in prices}), "METHOD_INVALID")
    s = cases["sampler"]
    _require(type(s) is dict and set(s) == SAMPLER_KEYS and type(s["seed"]) is str and _ID_RE.fullmatch(s["seed"]) is not None
             and _int(s["sample_n"], 1, MAX_ITEMS), "SAMPLER_INVALID")
    w = cases["wp170"]
    _require(w is None or (type(w) is dict and set(w) == WP170_KEYS and type(w["registry_file"]) is str
                           and type(w["experiment_id"]) is str and _ID_RE.fullmatch(w["experiment_id"]) is not None),
             "WP170_BINDING_INVALID")
    if frozen:
        _require(w is None or w["registry_file"] == "wp170.sqlite3", "FROZEN_CASES_INVALID")
    for name in ("history", "targets"):
        _require(type(cases[name]) is list and len(cases[name]) <= MAX_ITEMS, "CASES_LIST_INVALID")
    _require(len(cases["targets"]) > 0, "TARGETS_EMPTY")
    for name, id_key in (("targets", "case_id"), ("history", "history_id")):
        ids = [i[id_key] for i in cases[name] if isinstance(i, dict) and type(i.get(id_key)) is str]
        _require(len(ids) == len(set(ids)), "DUPLICATE_CASE_ID" if name == "targets" else "DUPLICATE_HISTORY_ID")


# ------------------------------------------------------------------ native grounding + WP170 binding


def bind_grounding(receipt: dict, frozen_case: dict, grounding_inputs: Path, cases: dict) -> dict:
    """Bind the cold-verified SRC-01 receipt to its frozen native universe and hash-bound rule bytes."""
    core = receipt["core"]
    _require(receipt["receipt_id"] == cases["grounding_receipt_id"], "GROUNDING_RECEIPT_MISMATCH")
    _require(core["wp_id"] == SG.WP_ID and core["schema_id"] == SG.RECEIPT_SCHEMA, "GROUNDING_RECEIPT_FOREIGN")
    _require(core["corpus_class"] == cases["corpus_class"], "CORPUS_CLASS_MISMATCH")
    as_of = core["inputs"]["as_of"]
    _, universe = SG.load_corpus(Path(grounding_inputs) / "pit.sqlite3", frozen_case["policy"], as_of)
    _require(universe.alpha_universe_snapshot_id == core["inputs"]["alpha_universe_snapshot_id"], "GROUNDING_UNIVERSE_MISMATCH")
    bound = {}
    for entry in core["corpus"]["rule_text_entries"]:
        if entry["status"] == "BOUND":
            rel = frozen_case["rule_texts"][entry["index"]]["file"]
            bound[entry["market_id"]] = SG.sha256_hex((Path(grounding_inputs) / rel).read_bytes())
    sources: dict[str, list[str]] = {}  # admitted, as-of-cutoff source references per market (SRC-01 verified)
    for entry in core["sources"]["entries"]:
        if entry["status"] == "ACCEPTED":
            sources.setdefault(entry["market_id"], []).append(entry["raw_evidence_reference_id"])
    return {"receipt_id": receipt["receipt_id"], "as_of": as_of, "universe": universe, "bound_rules": bound,
            "source_refs": {k: sorted(v) for k, v in sources.items()},
            "alpha_universe_snapshot_id": universe.alpha_universe_snapshot_id}


def load_wp170(registry_path: Path | None, experiment_id: str | None) -> tuple[dict, dict | None]:
    """Read-only native WP170 load: (public reference block, native experiment/split/manifest or None).

    Never a preregistration, registry write or RunEvidenceReceipt."""
    if registry_path is None:
        return {"status": "DIAGNOSTIC_ONLY_EXPERIMENT_UNBOUND", "experiment_id": None, "split_assignment_id": None,
                "oos_membership_hash": None, "registry_head_entry_hash": None}, None
    loaded = ER.load_and_verify_experiment_registry(registry_path)
    _require(loaded.is_valid and loaded.snapshot is not None, "WP170_REGISTRY_INVALID")
    records = [e.record for e in loaded.snapshot.entries]
    experiment = next((r for r in records if isinstance(r, EOS.PreregisteredExperiment) and r.experiment_id == experiment_id), None)
    _require(experiment is not None, "WP170_EXPERIMENT_NOT_FOUND")
    split = next((r for r in records if isinstance(r, EOS.TemporalSplitManifest)
                  and r.split_assignment_id == experiment.split_assignment_id), None)
    _require(split is not None, "WP170_SPLIT_NOT_FOUND")
    manifest = next((r for r in records if isinstance(r, EOS.ResearchDatasetManifest)
                     and r.research_dataset_manifest_id == experiment.research_dataset_manifest_id), None)
    _require(manifest is not None, "WP170_MANIFEST_NOT_FOUND")
    check_wp170_identities(experiment, split, manifest)
    public = {"status": "WP170_REFERENCES_VERIFIED_READ_ONLY_MEMBERSHIP_NOT_MAPPED", "experiment_id": experiment.experiment_id,
              "split_assignment_id": split.split_assignment_id, "oos_membership_hash": EOS.membership_hash(split, "OUT_OF_SAMPLE"),
              "registry_head_entry_hash": loaded.snapshot.head_entry_hash}
    return public, {"experiment": experiment, "split": split, "manifest": manifest}


def bind_wp170(registry_path: Path | None, experiment_id: str | None) -> dict:
    """Public WP170 reference block only (the v1 receipt shape)."""
    return load_wp170(registry_path, experiment_id)[0]


def check_wp170_identities(experiment, split, manifest) -> None:
    """Dataset, feature, label, manifest and split identities must agree; any disagreement stops the run."""
    sample_ids = [s.sample_id for s in manifest.samples]
    _require(split.dataset_manifest_id == manifest.research_dataset_manifest_id == experiment.research_dataset_manifest_id
             and manifest.dataset_binding_id == split.dataset_binding_id == experiment.dataset_binding_id
             and manifest.feature_definition_ids == split.feature_definition_ids == experiment.feature_definition_ids
             and manifest.feature_set_id == split.feature_set_id == experiment.feature_set_id
             and manifest.label_definition_id == split.label_definition_id == experiment.label_definition_id
             and len(sample_ids) == len(set(sample_ids)) == manifest.total_sample_count
             and all(s.dataset_binding_id == manifest.dataset_binding_id and s.feature_set_id == manifest.feature_set_id
                     and s.label_definition_id == manifest.label_definition_id for s in manifest.samples),
             "WP170_IDENTITY_MISMATCH")
    split_ids = [i for _, f in SPLIT_SETS for i in getattr(split, f)]
    # every split sample is a manifest sample in exactly one role/purge/embargo set
    _require(set(split_ids) <= set(sample_ids) and len(split_ids) == len(set(split_ids)), "WP170_SPLIT_INVALID")


SPLIT_SETS = (("FORMATION", "formation_sample_ids"), ("SELECTION", "selection_sample_ids"),
              ("OUT_OF_SAMPLE", "oos_sample_ids"), ("PURGED", "purged_sample_ids"), ("EMBARGOED", "embargoed_sample_ids"))


def _refusal_reason(r: dict, s, native_market, role: str | None, cross_market: bool, rule_conflict: bool,
                    scoring_cutoff: str) -> str | None:
    """First provenance, clock or split-role violation of a proven sample match, in fixed precedence; else None."""
    if cross_market:
        return "CROSS_MARKET_SOURCE"
    if rule_conflict:
        return "RULE_VERSION_CONFLICT"
    if _key(s.feature_availability_time) > _key(r["decision_time"]):
        return "FEATURE_AFTER_DECISION"
    if _key(s.feature_availability_time) < _key(native_market.metadata_observed_time):
        return "FEATURE_BEFORE_SOURCE_OBSERVED"
    if r["resolution_date"] is not None and _key(s.target_time) < _key(r["resolution_date"]):
        return "TARGET_BEFORE_NATIVE_RESOLUTION"
    if _key(s.label_availability_time) > _key(scoring_cutoff):
        return "LABEL_AVAILABLE_AFTER_SCORING_CUTOFF"
    if role is None:
        return "SAMPLE_OUTSIDE_SPLIT_WINDOW"
    if role in ("PURGED", "EMBARGOED"):
        return "SAMPLE_" + role
    return None


def map_wp170_membership(rows: list[dict], native: dict, grounding: dict, scoring_cutoff: str) -> dict:
    """Bind each eligible target to at most one native ResearchSample and its split role (diagnostic only).

    Uses only label-free target rows, native PIT market records and the verified WP170 manifest/split; outcomes
    are never read. A case that does not bind is counted with a reason; it never stops the run or the cohort."""
    split, manifest = native["split"], native["manifest"]
    roles = {sample_id: role for role, name in SPLIT_SETS for sample_id in getattr(split, name)}  # disjoint (checked)
    markets = {m.market_id: m for m in grounding["universe"].markets}
    metadata_owner = {m.metadata_record_version_id: m.market_id for m in markets.values()}
    rule_owner = {r.rule_record_version_id: (m.market_id, r.rule_content_sha256) for m in markets.values() for r in m.rules}
    by_market: dict[str, list] = {}
    for s in manifest.samples:
        by_market.setdefault(s.market_id, []).append(s)
    entries, groups = [], {}
    for r in rows:
        if "event_group" not in r:  # never eligible, so there is no grounded target to bind
            continue
        e = {"case_id": r["case_id"], "market_id": r["market_id"], "status": "UNMAPPED", "reason": None,
             "sample_id": None, "role": None}
        entries.append(e)
        candidates = by_market.get(r["market_id"], [])
        matches = [s for s in candidates if _key(s.decision_time) == _key(r["decision_time"])]
        if not candidates or not matches:
            e["reason"] = "SAMPLE_NOT_FOUND" if not candidates else "DECISION_TIME_MISMATCH"
            continue
        if len(matches) > 1:
            e.update(status="AMBIGUOUS", reason="MULTIPLE_SAMPLES_MATCH")
            continue
        s, native_market = matches[0], markets[r["market_id"]]
        cited = set(s.source_record_version_ids)
        cited_markets = {metadata_owner[c] for c in cited if c in metadata_owner} | {rule_owner[c][0] for c in cited if c in rule_owner}
        role = roles.get(s.sample_id)
        if native_market.metadata_record_version_id not in cited:
            e["reason"] = "SOURCE_PROVENANCE_UNPROVEN"  # no transitive proof that the sample is this PIT market
            continue
        e["sample_id"] = s.sample_id
        rule_conflict = any(rule_owner[c][1] != r["rule_content_sha256"] for c in cited if c in rule_owner)
        reason = _refusal_reason(r, s, native_market, role, bool(cited_markets - {r["market_id"]}), rule_conflict,
                                 scoring_cutoff)
        if reason:
            e.update(status="REFUSED", reason=reason)
            continue
        e.update(status="MAPPED", role=role)
        if s.leakage_group_id is not None:
            groups[r["case_id"]] = (r["event_group"], s.leakage_group_id)
    # One native event must map to one leakage group and back; otherwise grouping is not provably consistent.
    event_groups: dict[str, set] = {}
    leak_events: dict[str, set] = {}
    for event, leak in groups.values():
        event_groups.setdefault(event, set()).add(leak)
        leak_events.setdefault(leak, set()).add(event)
    for e in entries:
        pair = groups.get(e["case_id"])
        if pair and (len(event_groups[pair[0]]) > 1 or len(leak_events[pair[1]]) > 1):
            e.update(status="REFUSED", reason="EVENT_LEAKAGE_GROUP_CONFLICT", role=None)
    selected = {r["case_id"] for r in rows if r["status"] == "SELECTED"}
    mapped = [e for e in entries if e["status"] == "MAPPED"]
    count = Counter(e["status"] for e in entries)
    return {
        "binding_wp_id": BINDING_WP_ID,
        "method": "EXACT_MARKET_ID_AND_DECISION_TIME_PLUS_CITED_NATIVE_PIT_METADATA_RECORD",
        "rule_binding": "RULE_HASH_NOT_IN_RESEARCH_SAMPLE_CHECKED_ONLY_VIA_CITED_RULE_RECORD_VERSIONS",
        "labels_read_for_mapping": False, "cohort_selection_changed": False,
        "oos_release": "NOT_RELEASED", "run_evidence_receipt": None, "qualification_claim": False,
        "research_dataset_manifest_id": manifest.research_dataset_manifest_id,
        "dataset_binding_id": manifest.dataset_binding_id, "feature_set_id": manifest.feature_set_id,
        "label_definition_id": manifest.label_definition_id, "split_assignment_hash": split.assignment_hash,
        "membership_hashes": {role: EOS.membership_hash(split, role) for role in EOS.RESEARCH_ROLES},
        "mapped_sample_ids_sha256": SG.sha256_hex(SG.canonical_bytes(sorted(e["sample_id"] for e in mapped))),
        "denominators": {
            "targets_offered": len(rows), "not_eligible_not_bound": len(rows) - len(entries), "binding_frame": len(entries),
            **{k.lower(): count.get(k, 0) for k in ("MAPPED", "UNMAPPED", "AMBIGUOUS", "REFUSED")},
            "by_reason": dict(sorted(Counter(e["reason"] for e in entries if e["reason"]).items())),
            "mapped_by_role": {role: sum(1 for e in mapped if e["role"] == role) for role in EOS.RESEARCH_ROLES},
            "selected_mapped_by_role": {role: sum(1 for e in mapped if e["role"] == role and e["case_id"] in selected)
                                        for role in EOS.RESEARCH_ROLES},
        },
        "entries": entries,
    }


# ------------------------------------------------------------------ bands


def horizon_band(decision: str, resolution: str | None, edges: list[int]) -> str:
    if resolution is None:
        return "MISSING"
    days = _seconds(decision, resolution) // 86400
    lower = 0
    for edge in edges:
        if days < edge:
            return f"H[{lower},{edge})d"
        lower = edge
    return f"H[{lower},inf)d"


def price_band(price: Decimal | None, edges: list[str]) -> str:
    if price is None:
        return "MISSING"
    lower = "0"
    for edge in edges:
        if price < Decimal(edge):
            return f"P[{lower},{edge})"
        lower = edge
    return f"P[{lower},1]"


def _contemporaneous_price(item: dict, decision: str, max_age: int) -> tuple[Decimal | None, str | None]:
    """Only a price recorded at or before the decision and not stale counts; never a later revision."""
    if item["market_price"] is None:
        return None, "PRICE_MISSING"
    observed = _utc(item["price_observed_time"])
    if observed is None:
        return None, "PRICE_CLOCK_MISSING"
    if _key(observed) > _key(decision):
        return None, "PRICE_AFTER_DECISION"
    if _seconds(observed, decision) > max_age:
        return None, "PRICE_STALE"
    return _prob(item["market_price"]), None


# ------------------------------------------------------------------ targets + frozen cohort (outcomes never read)


def evaluate_targets(cases: dict, grounding: dict) -> list[dict]:
    m = cases["method"]
    markets = {x.market_id: x for x in grounding["universe"].markets}
    seen_markets: set[str] = set()
    rows = []
    for index, t in enumerate(cases["targets"]):
        row = {"index": index, "case_id": None, "market_id": None, "status": "INELIGIBLE", "reason": None}
        rows.append(row)
        if not isinstance(t, dict) or set(t) != TARGET_KEYS or type(t["case_id"]) is not str \
                or _ID_RE.fullmatch(t["case_id"]) is None or type(t["market_id"]) is not str \
                or type(t["question_sha256"]) is not str or _SHA_RE.fullmatch(t["question_sha256"]) is None \
                or type(t["rule_content_sha256"]) is not str or _SHA_RE.fullmatch(t["rule_content_sha256"]) is None \
                or type(t["yes_label"]) is not str or _utc(t["decision_time"]) is None \
                or not (t["market_price"] is None or _prob(t["market_price"]) is not None) \
                or not (t["price_observed_time"] is None or _utc(t["price_observed_time"]) is not None):
            row["reason"] = "TARGET_FIELDS_INVALID"
            continue
        row["case_id"] = t["case_id"]
        native = markets.get(t["market_id"])
        if native is None:
            row["reason"] = "MARKET_NOT_IN_GROUNDING"
            continue
        row["market_id"] = t["market_id"]
        if t["market_id"] in seen_markets:
            row["reason"] = "DUPLICATE_MARKET"
            continue
        seen_markets.add(t["market_id"])
        decision = _utc(t["decision_time"])
        resolution = _utc(native.resolution_date) if native.resolution_date else None
        if native.question_text is None or SG.sha256_hex(native.question_text.encode("utf-8")) != t["question_sha256"]:
            row["reason"] = "QUESTION_MISMATCH"
        elif len(native.outcome_labels) != 2 or len(set(native.outcome_labels)) != 2:
            row["reason"] = "NOT_BINARY"
        elif t["yes_label"] not in native.outcome_labels:
            row["reason"] = "OUTCOME_ORIENTATION_MISMATCH"
        elif not native.category:
            row["reason"] = "CATEGORY_MISSING"
        elif native.category.casefold() in CRYPTO_CATEGORIES:
            row["reason"] = "CRYPTO_EXCLUDED"
        elif t["market_id"] not in grounding["bound_rules"]:
            row["reason"] = "RULE_TEXT_NOT_BOUND"
        elif grounding["bound_rules"][t["market_id"]] != t["rule_content_sha256"]:
            row["reason"] = "RULE_MISMATCH"
        elif _key(decision) < _key(grounding["as_of"]):
            row["reason"] = "DECISION_BEFORE_GROUNDING_CUTOFF"
        elif resolution is not None and _key(resolution) <= _key(decision):
            row["reason"] = "DECISION_AFTER_RESOLUTION_DATE"
        else:
            price, price_reason = _contemporaneous_price(t, decision, m["max_price_age_seconds"])
            refs = grounding["source_refs"].get(t["market_id"], [])
            row.update(status="ELIGIBLE", event_group=native.event_id, category=native.category,
                       grounded_source_reference_ids=refs,
                       source_status="SRC01_ADMITTED_SOURCES" if refs else "NO_ADMITTED_SOURCE",
                       question_sha256=t["question_sha256"], rule_content_sha256=t["rule_content_sha256"],
                       yes_label=t["yes_label"], outcome_labels=list(native.outcome_labels), decision_time=decision,
                       resolution_date=resolution, horizon_band=horizon_band(decision, resolution, m["horizon_edges_days"]),
                       market_price=None if price is None else str(price), price_reason=price_reason,
                       price_band=price_band(price, m["price_edges"]))
    return rows


def _draw_key(seed: str, case_id: str) -> str:
    return hashlib.sha256(f"{seed}|{case_id}".encode("utf-8")).hexdigest()


def freeze_cohort(rows: list[dict], sampler: dict) -> dict:
    """ForecastBench-style composite-bin largest-remainder apportionment with a SHA-256 seeded draw.

    Takes only label-free target rows: outcomes are not an input, so they cannot affect selection."""
    seed = sampler["seed"]
    eligible = [r for r in rows if r["status"] == "ELIGIBLE"]
    groups: dict[str, list[dict]] = {}
    for r in eligible:
        groups.setdefault(r["event_group"], []).append(r)
    kept = []
    for members in groups.values():  # one market per event: no mixed results across a shared event
        members.sort(key=lambda r: _draw_key(seed, r["case_id"]))
        for r in members:
            r["event_group_selection"] = _ratio(1, len(members))
        kept.append(members[0])
        for r in members[1:]:
            r.update(status="EXCLUDED", reason="EVENT_GROUP_DUPLICATE")
    strata: dict[str, list[dict]] = {}
    for r in kept:
        r["stratum"] = f"{r['category']}|{r['horizon_band']}|{r['price_band']}"
        strata.setdefault(r["stratum"], []).append(r)
    total, target = len(kept), min(sampler["sample_n"], len(kept))
    quota = {}
    if total:
        share = {s: Decimal(target) * len(v) / Decimal(total) for s, v in strata.items()}
        quota = {s: min(int(share[s]), len(strata[s])) for s in strata}
        for s in sorted(strata, key=lambda s: (-(share[s] % 1), -len(strata[s]), s)):
            if sum(quota.values()) >= target:
                break
            if quota[s] < len(strata[s]):
                quota[s] += 1
        for s in sorted(strata, key=lambda s: (-len(strata[s]), s)):  # fill any shortage from largest strata
            while sum(quota.values()) < target and quota[s] < len(strata[s]):
                quota[s] += 1
    summary = []
    for s in sorted(strata):
        members = sorted(strata[s], key=lambda r: _draw_key(seed, r["case_id"]))
        for rank, r in enumerate(members):
            r["status"], r["reason"] = ("SELECTED", None) if rank < quota[s] else ("EXCLUDED", "NOT_SAMPLED")
        summary.append({"stratum": s, "available": len(members), "selected": quota[s],
                        "inclusion_probability_within_stratum": _ratio(quota[s], len(members)),
                        "selected_case_ids": sorted(r["case_id"] for r in members[:quota[s]])})
    reasons = Counter(r["reason"] for r in rows if r["status"] != "SELECTED")
    selected = sorted(r["case_id"] for r in rows if r["status"] == "SELECTED")
    return {
        "seed": seed, "draw": "sha256(seed|case_id) ascending within stratum", "strata": summary,
        "inclusion_note": "overall inclusion = event_group_selection (per target row) x inclusion_probability_within_stratum",
        "selected_case_ids": selected,
        "membership_sha256": SG.sha256_hex(SG.canonical_bytes(selected)),
        "denominators": {"offered": len(rows), "eligible": len(eligible), "event_groups": len(groups),
                         "event_group_duplicates": reasons.get("EVENT_GROUP_DUPLICATE", 0),
                         "sampling_frame": total, "requested": sampler["sample_n"], "selected": len(selected),
                         "not_sampled": reasons.get("NOT_SAMPLED", 0),
                         "ineligible_by_reason": dict(sorted((k, v) for k, v in reasons.items()
                                                             if k not in ("EVENT_GROUP_DUPLICATE", "NOT_SAMPLED")))},
    }


# ------------------------------------------------------------------ training history


def evaluate_history(cases: dict, target_groups: set[str]) -> tuple[list[dict], list[dict]]:
    m = cases["method"]
    rows, valid = [], []
    for index, h in enumerate(cases["history"]):
        row = {"index": index, "history_id": None, "status": "EXCLUDED", "reason": None}
        rows.append(row)
        clocks = {k: _utc(h.get(k)) for k in ("decision_time", "resolution_time", "resolution_known_time",
                                              "source_observed_time")} if isinstance(h, dict) else {}
        if not isinstance(h, dict) or set(h) != HISTORY_KEYS or type(h["history_id"]) is not str \
                or _ID_RE.fullmatch(h["history_id"]) is None or type(h["event_group"]) is not str or not h["event_group"] \
                or type(h["category"]) is not str or not h["category"] or None in clocks.values() \
                or h["evidence_capture"] not in ("PROSPECTIVE", "BACKFILLED") or h["outcome"] not in (0, 1) \
                or type(h["outcome"]) is not int \
                or not (h["market_price"] is None or _prob(h["market_price"]) is not None) \
                or not (h["price_observed_time"] is None or _utc(h["price_observed_time"]) is not None):
            row["reason"] = "HISTORY_FIELDS_INVALID"
            continue
        row["history_id"] = h["history_id"]
        if h["evidence_capture"] == "BACKFILLED":
            row["reason"] = "HISTORY_BACKFILLED"
        elif not _key(clocks["decision_time"]) < _key(clocks["resolution_time"]) <= _key(clocks["resolution_known_time"]):
            row["reason"] = "HISTORY_CLOCK_INCONSISTENT"
        elif h["event_group"] in target_groups:
            row["reason"] = "HISTORY_EVENT_GROUP_OVERLAPS_TARGET"  # same event in train and evaluation = leakage
        elif h["category"].casefold() in CRYPTO_CATEGORIES:
            row["reason"] = "CRYPTO_EXCLUDED"
        else:
            price, price_reason = _contemporaneous_price(h, clocks["decision_time"], m["max_price_age_seconds"])
            row.update(status="ADMITTED", reason=None)
            valid.append({**clocks, "history_id": h["history_id"], "event_group": h["event_group"],
                          "category": h["category"], "outcome": h["outcome"], "price": price, "price_reason": price_reason,
                          "horizon_band": horizon_band(clocks["decision_time"], clocks["resolution_time"],
                                                       m["horizon_edges_days"])})
    return rows, valid


def _training(valid: list[dict], decision: str) -> tuple[list[dict], int]:
    """Only history resolved, known and source-observed strictly before the target decision."""
    usable = [h for h in valid if _key(h["resolution_known_time"]) < _key(decision)
              and _key(h["source_observed_time"]) < _key(decision)]
    return usable, len(valid) - len(usable)


# ------------------------------------------------------------------ forecasters


def beta_prior(outcomes: list[int], alpha: Decimal, beta: Decimal, min_n: int) -> dict:
    """Beta-smoothed binomial base rate (k + a) / (n + a + b); ABSTAIN below min_n, never 0.5 or price."""
    n, k = len(outcomes), sum(outcomes)
    if n < min_n:
        return {"status": "ABSTAIN", "reason": "ABSTAIN_NO_TRAINING", "p_yes": None,
                "training": {"successes": k, "n": n, "required_n": min_n}}
    with localcontext() as ctx:
        ctx.prec = 50
        p = (Decimal(k) + alpha) / (Decimal(n) + alpha + beta)
    return {"status": "FORECAST", "reason": None, "p_yes": _q(p), "training": {"successes": k, "n": n, "required_n": min_n}}


_N = NormalDist()


def _wang_nll(lam: float, z: list[float], y: list[int]) -> float:
    total = 0.0
    for zi, yi in zip(z, y):
        phi = min(max(_N.cdf(zi - lam), WANG_PHI_CLIP), 1 - WANG_PHI_CLIP)
        total -= math.log(phi) if yi else math.log(1 - phi)
    return round(total, 9)  # rounded so the bracket search is stable across libm builds


def fit_wang(prices: list[Decimal], outcomes: list[int]) -> float:
    """Train-only intercept MLE of lambda (golden-section on the convex probit NLL, fixed iterations)."""
    z = [_N.inv_cdf(min(max(float(p), WANG_P_CLIP), 1 - WANG_P_CLIP)) for p in prices]
    lo, hi = WANG_LAMBDA_BOUNDS
    ratio = (math.sqrt(5) - 1) / 2
    for _ in range(WANG_ITERATIONS):
        a, b = hi - ratio * (hi - lo), lo + ratio * (hi - lo)
        if _wang_nll(a, z, outcomes) <= _wang_nll(b, z, outcomes):
            hi = b
        else:
            lo = a
    return round((lo + hi) / 2, 9)


def wang_transform(price: Decimal, lam: float) -> Decimal:
    z = _N.inv_cdf(min(max(float(price), WANG_P_CLIP), 1 - WANG_P_CLIP))
    return Decimal(repr(_N.cdf(z - lam))).quantize(Q12, rounding=ROUND_HALF_EVEN)


def forecast_case(row: dict, valid_history: list[dict], method: dict) -> dict:
    training, excluded_late = _training(valid_history, row["decision_time"])
    alpha, beta = Decimal(method["prior_alpha"]), Decimal(method["prior_beta"])
    stratum = [h["outcome"] for h in training if h["category"] == row["category"] and h["horizon_band"] == row["horizon_band"]]
    out = {
        INDEPENDENT: {**beta_prior(stratum, alpha, beta, method["min_training_n"]),
                      "stratum": f"{row['category']}|{row['horizon_band']}"},
        BASE_RATE: beta_prior([h["outcome"] for h in training], alpha, beta, method["min_training_n"]),
        MARKET: ({"status": "FORECAST", "reason": None, "p_yes": row["market_price"]} if row["market_price"] is not None
                 else {"status": "UNAVAILABLE", "reason": "BASELINE_UNAVAILABLE:" + row["price_reason"], "p_yes": None}),
    }
    priced = [h for h in training if h["price"] is not None and WANG_PRICE_RANGE[0] <= h["price"] <= WANG_PRICE_RANGE[1]]
    if len(priced) < method["wang_min_training_n"]:
        out[WANG] = {"status": "ABSTAIN", "reason": "ABSTAIN_NO_TRAINING", "p_yes": None, "lambda": None,
                     "training": {"n": len(priced), "required_n": method["wang_min_training_n"]}}
    else:
        lam = fit_wang([h["price"] for h in priced], [h["outcome"] for h in priced])
        out[WANG] = {"status": "FORECAST" if row["market_price"] is not None else "UNAVAILABLE",
                     "reason": None if row["market_price"] is not None else "BASELINE_UNAVAILABLE:" + row["price_reason"],
                     "p_yes": None if row["market_price"] is None else _q(wang_transform(Decimal(row["market_price"]), lam)),
                     "lambda": f"{lam:.9f}", "lambda_at_bound": abs(abs(lam) - WANG_LAMBDA_BOUNDS[1]) < 1e-6, "training": {"n": len(priced), "required_n": method["wang_min_training_n"],
                                                          "training_ids_sha256": SG.sha256_hex(SG.canonical_bytes(
                                                              sorted(h["history_id"] for h in priced)))}}
    for name in METHODS:
        out[name]["lineage"] = LINEAGE[name]
    return {"training_n": len(training), "training_excluded_not_known_before_decision": excluded_late,
            "training_ids_sha256": SG.sha256_hex(SG.canonical_bytes(sorted(h["history_id"] for h in training))),
            "methods": out}


# ------------------------------------------------------------------ outcomes + scoring


def resolve_outcome(row: dict, outcome: object, corpus_class: str, scoring_cutoff: str) -> tuple[int | None, str | None]:
    """Score only an outcome resolved and known after the decision and by the scoring cutoff."""
    if outcome is None:
        return None, "UNRESOLVED"
    if not isinstance(outcome, dict) or set(outcome) != OUTCOME_KEYS or type(outcome["label"]) is not str \
            or _utc(outcome["resolved_time"]) is None or _utc(outcome["known_time"]) is None:
        return None, "OUTCOME_INVALID"
    if outcome["label"] not in row["outcome_labels"]:
        return None, "OUTCOME_LABEL_UNKNOWN"
    if outcome["provenance"] != OUTCOME_PROVENANCE[corpus_class]:
        return None, "OUTCOME_PROVENANCE_INVALID"
    resolved, known = _utc(outcome["resolved_time"]), _utc(outcome["known_time"])
    if _key(resolved) > _key(known):
        return None, "OUTCOME_CLOCK_INCONSISTENT"
    if _key(resolved) <= _key(row["decision_time"]):  # with resolved <= known this also covers known-before
        return None, "OUTCOME_RESOLVED_BEFORE_DECISION"
    if _key(known) > _key(scoring_cutoff):
        return None, "OUTCOME_AFTER_SCORING_CUTOFF"
    return (1 if outcome["label"] == row["yes_label"] else 0), None


def score_one(p: Decimal, y: int) -> dict:
    """Brier, epsilon-clipped log loss and Metaculus binary baseline score; clipping is reported."""
    with localcontext() as ctx:
        ctx.prec = 50
        clipped = min(max(p, EPSILON), 1 - EPSILON)
        q = clipped if y == 1 else 1 - clipped
        return {"brier": (p - y) ** 2, "log_loss": -q.ln(), "baseline_score": 100 * (2 * q).ln() / Decimal(2).ln(),
                "clipped": clipped != p}


def _aggregate(scores: list[dict]) -> dict:
    n = len(scores)
    if n == 0:
        return {"n": 0, "brier": None, "log_loss": None, "baseline_score": None, "clipped": 0}
    with localcontext() as ctx:
        ctx.prec = 50
        return {"n": n, **{k: _q(sum(s[k] for s in scores) / n) for k in ("brier", "log_loss", "baseline_score")},
                "clipped": sum(1 for s in scores if s["clipped"])}


def score_cohort(cases_by_id: dict, rows: list[dict], forecasts: dict, corpus_class: str, cutoff: str) -> dict:
    selected = [r for r in rows if r["status"] == "SELECTED"]
    per_case, labels = [], {}
    for r in selected:
        y, reason = resolve_outcome(r, cases_by_id[r["case_id"]]["outcome"], corpus_class, cutoff)
        labels[r["case_id"]] = y
        per_case.append({"case_id": r["case_id"], "scorable": y is not None, "not_scorable_reason": reason, "y": y})
    scorable = [r["case_id"] for r in selected if labels[r["case_id"]] is not None]
    available = {m: [c for c in scorable if forecasts[c]["methods"][m]["status"] == "FORECAST"] for m in METHODS}
    # Primary comparison is independent vs market vs train base rate; Wang is a separate comparator.
    paired = [c for c in scorable if all(c in available[m] for m in PRIMARY_METHODS)]
    wang_paired = [c for c in paired if c in available[WANG]]

    def scores(method, ids):
        return [score_one(Decimal(forecasts[c]["methods"][method]["p_yes"]), labels[c]) for c in ids]
    methods = {}
    for m in METHODS:
        statuses = Counter(forecasts[c]["methods"][m]["status"] for c in scorable)
        boundary = sum(1 for c in available[m] if Decimal(forecasts[c]["methods"][m]["p_yes"]) in (0, 1))
        methods[m] = {"lineage": LINEAGE[m], "on_own_available": _aggregate(scores(m, available[m])),
                      "on_paired": _aggregate(scores(m, paired if m != WANG else wang_paired)),
                      "paired_set": "PRIMARY" if m != WANG else "PRIMARY_AND_WANG", "abstained": statuses.get("ABSTAIN", 0),
                      "unavailable": statuses.get("UNAVAILABLE", 0), "boundary_probability_0_or_1": boundary,
                      "errors": 0, "cost": dict(COST)}  # any error is a whole-run INTERNAL_VALIDATION_FAILED stop
    deltas = None
    if paired:
        ind, mkt = methods[INDEPENDENT]["on_paired"], methods[MARKET]["on_paired"]
        deltas = {"independent_minus_market_brier": _q(Decimal(ind["brier"]) - Decimal(mkt["brier"])),
                  "independent_minus_market_log_loss": _q(Decimal(ind["log_loss"]) - Decimal(mkt["log_loss"]))}
    reasons = Counter(c["not_scorable_reason"] for c in per_case if not c["scorable"])
    return {
        "metric_ids": ["BRIER_SCORE", "LOG_LOSS", "METACULUS_BINARY_BASELINE_SCORE"], "log_loss_epsilon": str(EPSILON),
        "orientation": {"BRIER_SCORE": "LOWER_IS_BETTER", "LOG_LOSS": "LOWER_IS_BETTER",
                        "METACULUS_BINARY_BASELINE_SCORE": "HIGHER_IS_BETTER"},
        "denominators": {"selected": len(selected), "scorable": len(scorable), "not_scorable": len(selected) - len(scorable),
                         "not_scorable_by_reason": dict(sorted(reasons.items())),
                         "available_by_method": {m: len(available[m]) for m in METHODS}, "paired_intersection": len(paired),
                         "paired_with_wang": len(wang_paired)},
        "paired_case_ids_sha256": SG.sha256_hex(SG.canonical_bytes(paired)),
        "paired_with_wang_case_ids_sha256": SG.sha256_hex(SG.canonical_bytes(wang_paired)),
        "methods": methods, "paired_deltas": deltas,
        "lift_status": ("NO_PAIRED_CASES" if not paired else "SYNTHETIC_CONTRACT_EVIDENCE_NOT_VALUE"
                        if corpus_class == "SANITIZED_SYNTHETIC" else "LOCAL_OBSERVATION_UNREVIEWED_NOT_VALUE"),
        "cases": per_case,
    }


# ------------------------------------------------------------------ receipt core


def build_evaluation_core(cases: dict, grounding: dict, wp170: dict, code_identity: str, input_hashes: dict,
                          wp170_native: dict | None = None, schema: str = RECEIPT_SCHEMA) -> dict:
    """v1 rebuilds the historical receipt byte for byte; v2 adds the per-case WP170 membership block."""
    _require(schema in RECEIPT_SCHEMAS, "RECEIPT_SCHEMA_UNSUPPORTED")
    validate_cases(cases, frozen=True)
    rows = evaluate_targets(cases, grounding)
    cohort = freeze_cohort(rows, cases["sampler"])  # before any outcome is read
    if schema == RECEIPT_SCHEMA:
        _require((wp170_native is None) == (wp170["experiment_id"] is None), "WP170_NATIVE_CONTEXT_MISSING")
        membership = (None if wp170_native is None
                      else map_wp170_membership(rows, wp170_native, grounding, _utc(cases["scoring_cutoff"])))
        wp170 = dict(wp170, membership=membership)
        if membership is not None and membership["denominators"]["mapped"]:
            wp170["status"] = "WP170_REFERENCES_VERIFIED_READ_ONLY_MEMBERSHIP_MAPPED"
    target_groups = {r["event_group"] for r in rows if "event_group" in r}
    history_rows, valid_history = evaluate_history(cases, target_groups)
    forecasts = {r["case_id"]: forecast_case(r, valid_history, cases["method"]) for r in rows if r["status"] == "SELECTED"}
    cases_by_id = {t["case_id"]: t for t in cases["targets"] if isinstance(t, dict) and type(t.get("case_id")) is str}
    scoring = score_cohort(cases_by_id, rows, forecasts, cases["corpus_class"], _utc(cases["scoring_cutoff"]))
    core = {
        "schema_id": schema, "wp_id": WP_ID, "posture": "RESEARCH_ONLY", "score_status": "DIAGNOSTIC_ONLY",
        "case_label": cases["case_label"], "corpus_class": cases["corpus_class"], "caller": CALLER,
        "code_identity": code_identity,
        "source_grounding": {"receipt_id": grounding["receipt_id"], "verify_status": "VERIFIED", "as_of": grounding["as_of"],
                             "alpha_universe_snapshot_id": grounding["alpha_universe_snapshot_id"],
                             "bound_rule_markets": len(grounding["bound_rules"]),
                             "markets_with_admitted_sources": len(grounding["source_refs"])},
        "wp170": wp170,
        "inputs": {"file_sha256": input_hashes, "cases_sha256": SG.sha256_hex(SG.canonical_bytes(cases)),
                   "scoring_cutoff": _utc(cases["scoring_cutoff"])},
        "method": {**cases["method"], "log_loss_epsilon": str(EPSILON), "wang": {
            "lambda_bounds": [str(b) for b in WANG_LAMBDA_BOUNDS], "p_clip": str(WANG_P_CLIP), "phi_clip": str(WANG_PHI_CLIP),
            "training_price_range": [str(b) for b in WANG_PRICE_RANGE], "iterations": WANG_ITERATIONS},
            "producers": {m: {"lineage": LINEAGE[m], "producer_id": m} for m in METHODS},
            "independent_exogenous_lineages": 1, "aggregation": "NONE_SINGLE_PRODUCER_PER_LINEAGE"},
        "targets": rows,
        "cohort": cohort,
        "history": {"offered": len(history_rows), "admitted": len(valid_history),
                    "provenance": "CALLER_ASSERTED_CLOCKS_NOT_SRC01_GROUNDED",
                    "excluded_by_reason": dict(sorted(Counter(r["reason"] for r in history_rows if r["reason"]).items())),
                    "entries": history_rows},
        "forecasts": forecasts,
        "scoring": scoring,
        "source_pins": [dict(p) for p in SOURCE_PINS],
        "adoption": dict(ADOPTION),
        "authority": {"research_only": True, "independent_probability_is_market_derived": False,
                      "wang_is_exogenous": False, "qualification_claim": False, "real_value_verified": False,
                      "wp170_run_evidence_receipt": False, "canonical_store_writes": False, "strategy": False,
                      "paper": False, "orders": False, "live": False, "llm_or_hermes": False, "network_calls": 0,
                      "provider_calls": 0, "credentials": False, "capital_usd": "0"},
        "successor": {"wp_id": "S10-R3-LEARN-01", "status": "MANDATORY_PENDING",
                      "rule": "consume immutable score receipts after resolution; propose future research priority only"},
    }
    return json.loads(SG.canonical_bytes(core))


def finalize_receipt(core: dict) -> dict:
    return {"core": core, "receipt_id": RECEIPT_PREFIX + SG.sha256_hex(SG.canonical_bytes(core))}


def verify_receipt(receipt: object, recomputed_core: dict) -> list[str]:
    """Failure codes only (never input values); empty list means verified."""
    if not isinstance(receipt, dict) or set(receipt) - {"non_identity"} != {"core", "receipt_id"} \
            or not isinstance(receipt["core"], dict):
        return ["RECEIPT_SHAPE_INVALID"]
    extra = receipt.get("non_identity", {})
    if not isinstance(extra, dict) or set(extra) - {"note", "total_ms"} \
            or type(extra.get("total_ms", 0)) not in (int, float) \
            or extra.get("note", NON_IDENTITY_NOTE) != NON_IDENTITY_NOTE:
        return ["NON_IDENTITY_INVALID"]
    failures = []
    if receipt["receipt_id"] != RECEIPT_PREFIX + SG.sha256_hex(SG.canonical_bytes(receipt["core"])):
        failures.append("RECEIPT_ID_MISMATCH")
    if receipt["core"] != recomputed_core:
        failures.extend(f"OUTPUT_MISMATCH:{k}" for k in sorted(set(recomputed_core) | set(receipt["core"]))
                        if receipt["core"].get(k) != recomputed_core.get(k))
    return failures


NON_IDENTITY_NOTE = "timings are excluded from receipt identity"

SOURCE_PINS = (
    {"capability": "R3-01", "repository": "Metaculus/forecasting-tools", "commit": "a54dd6443d19745b267e99a3b0b7627e74b9a57a",
     "file": "forecasting_tools/forecast_bots/forecast_bot.py", "license": "MIT", "adoption_mode": "ADAPT_CONCEPT_NO_CODE_COPIED"},
    {"capability": "R3-06", "repository": "gnosis/prediction-market-agent-tooling",
     "commit": "817117d9e5b9ebe62ed1bf5ed090c67e49dab77f", "file": "prediction_market_agent_tooling/benchmark/benchmark.py",
     "license": "LGPL-3.0", "adoption_mode": "ADAPT_CONCEPT_NO_CODE_COPIED"},
    {"capability": "R3-10", "repository": "YichengYang-Ethan/prediction-market-pricing",
     "commit": "04b916c34d29c4d586ffd16b0b2036aadcca2308", "file": "src/identification/external_benchmark.py",
     "license": "MIT", "adoption_mode": "ADAPT_CONCEPT_NO_CODE_COPIED"},
    {"capability": "R3-10-WANG", "repository": "YichengYang-Ethan/prediction-market-pricing",
     "commit": "04b916c34d29c4d586ffd16b0b2036aadcca2308", "file": "src/models/hierarchical_wang_mle.py",
     "license": "MIT", "adoption_mode": "ADAPT_ALGORITHM_NO_CODE_COPIED"},
    {"capability": "R3-12", "repository": "forecastingresearch/forecastbench", "commit": "e8d3c94f9b7f424bbd1205007db08cf2950a45a3",
     "file": "src/question_sampling/_sampling.py", "license": "MIT", "adoption_mode": "ADAPT_ALGORITHM_NO_CODE_COPIED"},
    {"capability": "R3-12-SAMPLER", "repository": "forecastingresearch/forecastbench",
     "commit": "e8d3c94f9b7f424bbd1205007db08cf2950a45a3", "file": "src/question_sampling/_sampling.py", "license": "MIT",
     "adoption_mode": "ADAPT_ALGORITHM_NO_CODE_COPIED"},
    {"capability": "R3-18", "repository": "Metaculus/metac-bot-template", "commit": "bcbd016b9c6aee4f62ceeb7f8556b4d96d97b1cc",
     "file": "integrations/main_lightningrod_eval.py", "license": "NONE_DECLARED", "adoption_mode": "READ_ONLY_CONCEPT_TESTS_ONLY"},
    {"capability": "R3-20", "repository": "Metaculus/metaculus", "commit": "bfae5fe87e049404cd1ff094150dee10360aec59",
     "file": "scoring/score_math.py", "license": "BSD-2-Clause", "adoption_mode": "ADAPT_FORMULA_NO_CODE_COPIED"},
    {"capability": "R3-22", "repository": "forecastingresearch/forecastbench-sim",
     "commit": "27776fc49bcf3753302045c762830088040c5629", "file": "packages/fbsim-benchmark/tests/test_contract.py",
     "license": "GPL-3.0", "adoption_mode": "READ_ONLY_CONCEPT_TESTS_ONLY"},
)

ADOPTION = {
    "R3-01": "PROTOCOL_ADAPTED_SINGLE_PRODUCER_NOT_VALUE_VERIFIED",
    "R3-06": "SAME_CASE_ACCOUNTING_INTEGRATED_OFFLINE_NOT_VALUE_VERIFIED",
    "R3-10": "EXOGENOUS_SEPARATION_INTEGRATED_OFFLINE_NO_EXTERNAL_BENCHMARK_DATA",
    "R3-10-WANG": "MARKET_PRICE_DERIVED_COMPARATOR_INTEGRATED_OFFLINE_NEVER_INDEPENDENT",
    "R3-12": "INTEGRATED_OFFLINE_NOT_VALUE_VERIFIED",
    "R3-12-SAMPLER": "INTEGRATED_OFFLINE_NOT_VALUE_VERIFIED",
    "R3-18": "PARITY_OPEN_PENDING_KARL_ACCEPTANCE",
    "R3-20": "PARITY_OPEN_PENDING_KARL_ACCEPTANCE",
    "R3-22": "PARITY_OPEN_PENDING_KARL_ACCEPTANCE",
    "value_status": "NO_REAL_VALUE_VERIFIED",
    "other_program_ids": "UNCHANGED_27_OF_36",
    "provider_lanes": "UNCHANGED_SIX_OWNER_GATED",
}
