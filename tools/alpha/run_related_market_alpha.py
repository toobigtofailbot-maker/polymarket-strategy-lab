"""Finite offline related-market discovery + conditional basket economics (S10-R3-REL-01).

  run    --grounding-scratch DIR --request-file REQ.json --scratch-dir DIR
  verify --scratch-dir DIR

Call path: verified S10-R3-SRC-01 scratch (cold-verified copy) -> native Alpha universe and
hash-bound PIT rules -> native candidate discovery -> formal payout proof / counterexamples
-> conditional Oracle3 baskets over native offline venue snapshots, fees and depth ->
one content-addressed RESEARCH_ONLY receipt. Inputs are only caller-named existing local
files; nothing is downloaded, no provider/LLM/Hermes is called and every socket entry point
is blocked. Writes only inside one empty absolute scratch directory outside the repository.
No order, strategy, paper, capital, executable-edge or live authority.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import os
import re
from pathlib import Path
import shutil
import stat
import sys
import time

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from decimal import Decimal, InvalidOperation  # noqa: E402

from src.data_layer.analytical_research import alpha_discovery as AD  # noqa: E402
from src.data_layer.analytical_research import related_market as RM  # noqa: E402
from src.data_layer.analytical_research import related_market_economics as RE  # noqa: E402
from src.data_layer.analytical_research import source_grounding as SG  # noqa: E402
from src.data_layer.point_in_time_market_research import record_store as PRS  # noqa: E402
from src.data_layer.point_in_time_market_research import records as PR  # noqa: E402
from src.data_layer.point_in_time_market_research import research_provenance as RP  # noqa: E402
from src.execution_feasibility import evaluator as EV  # noqa: E402
from src.execution_feasibility import public_market as PM  # noqa: E402
from src.execution_feasibility.models import ExecutionFeasibilityError  # noqa: E402
from tools.alpha import run_source_grounding as SGCLI  # noqa: E402

WP_ID = "S10-R3-REL-01"
REQUEST_SCHEMA = "s10-r3-rel01-request-v1"
RECEIPT_SCHEMA = "s10-r3-rel01-related-market-research-receipt-v1"
RECEIPT_PREFIX = "relmarket:sha256:"
CALLER = ("tools/alpha/run_related_market_alpha.py:run -> run_source_grounding.verify -> source_grounding.load_corpus/"
          "bind_rule_texts -> related_market.discover_candidates/formal_proof -> related_market_economics.assess_basket")
MAX_REQUEST_BYTES = 1 << 20
MAX_VENUE_BYTES = 4 << 20
MAX_GROUNDING_BYTES = 160 << 20
MAX_GROUNDING_FILES = 2000
MAX_MODELS = 200
MAX_VENUE = 400
MAX_RUN_SECONDS = 300
MAX_SHARES = Decimal("1000000")
_SHARES_RE = re.compile(r"(0|[1-9][0-9]{0,6})(\.[0-9]{1,6})?")
REQUEST_KEYS = {"schema_id", "request_label", "corpus_class", "decision_time", "max_book_age_seconds", "basket_shares",
                "search", "fee_policy", "models", "venue", "benchmark_sha256"}
SEARCH_KEYS = {"families", "max_group_size", "min_shared_terms", "max_candidates"}
FEE_KEYS = {"policy_id", "kind", "valid_from", "valid_until", "test_rate", "test_exponent"}
MODEL_KEYS = {"model_id", "relation", "market_ids", "states", "special_states", "timezones", "yes_token_ids",
              "claimed_rule_sha256", "claimed_verdict", "cross_venue", "combo", "expected"}
VENUE_KEYS = {"market_id", "gamma_market_id", "token_id", "gamma_file", "clob_file", "acquisition_started",
              "acquisition_completed"}
EXPECTED_LABELS = ("FORMAL_VALID", "COUNTEREXAMPLE", "RULE_CONFLICT", "INCONCLUSIVE", "NOT_NATIVE_CANDIDATE", "MODEL_INVALID")
SECRET_DIR_PARTS = {".ssh", ".aws", ".gnupg", ".azure", ".kube", ".docker", "credentials", "secrets", ".password-store"}
FILE_ATTRIBUTE_REPARSE_POINT = 0x400
CODE_FILES = (Path(RM.__file__), Path(RE.__file__), Path(__file__), Path(SG.__file__), Path(SGCLI.__file__),
              Path(AD.__file__), Path(EV.__file__), Path(PM.__file__))


def code_identity() -> str:
    digest = hashlib.sha256()
    for path in CODE_FILES:
        digest.update(path.resolve().read_bytes())
    return "code:sha256:" + digest.hexdigest()


def _stop(code: str):
    raise RM.RelationStop(code)


def _require(condition: bool, code: str) -> None:
    if not condition:
        _stop(code)


def _inside(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _unsafe_entry(path: Path, *, directory: bool) -> bool:
    """Symlink, reparse point, hardlink, non-regular entry or secret-shaped directory."""
    try:
        info = os.lstat(path)
    except OSError:
        return True
    if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & FILE_ATTRIBUTE_REPARSE_POINT:
        return True
    if directory:
        return not stat.S_ISDIR(info.st_mode)
    return not stat.S_ISREG(info.st_mode) or info.st_nlink != 1


def _caller_path(value: object, *, directory: bool, scratch: Path | None) -> Path | None:
    """One caller-named path, or None when unusable (never echoed)."""
    if type(value) is not str or not value or "\x00" in value:
        return None
    path = Path(value)
    if not path.is_absolute() or ".." in path.parts or _unsafe_entry(path, directory=directory):
        return None
    if any(_unsafe_entry(parent, directory=True) for parent in list(path.parents)[:-1] if parent.exists()):
        return None
    resolved = path.resolve()
    if os.path.normcase(str(resolved)) != os.path.normcase(os.path.abspath(value)):
        return None  # alias (8.3 name, junction or mount) rejected
    if {p.casefold() for p in resolved.parts} & SECRET_DIR_PARTS or _inside(resolved, REPO_ROOT):
        return None
    if scratch is not None and (_inside(resolved, scratch) or _inside(scratch, resolved)):
        return None
    return resolved


def _read_capped(path: Path | None, limit: int) -> bytes:
    """Bounded read (no stat-then-read race); oversize reads as unusable."""
    if path is None:
        return b""
    with open(path, "rb") as handle:
        data = handle.read(limit + 1)
    return data if len(data) <= limit else b""


def _strict_json(raw: bytes, code: str):
    return SGCLI._strict_json(raw, code)


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _utc(value: object) -> str | None:
    if type(value) is not str:
        return None
    try:
        canonical = RP.canonicalize_utc_timestamp(value)
    except ValueError:
        return None
    return canonical if canonical == value else None


def _label(value: object) -> bool:
    return type(value) is str and SG._LABEL_RE.fullmatch(value) is not None


def _scan_secrets(value: object, depth: int = 0) -> None:
    _require(depth <= 8, "REQUEST_TOO_DEEP")
    if isinstance(value, dict):
        for key, item in value.items():
            _require(not any(p in key.casefold() for p in SG.SECRET_KEY_PARTS), "FORBIDDEN_FIELD")
            _scan_secrets(item, depth + 1)
    elif isinstance(value, list):
        for item in value:
            _scan_secrets(item, depth + 1)


def validate_request(request: object, *, frozen: bool) -> None:
    """Whole-request structure; per-model and per-venue defects are counted per item later."""
    _require(isinstance(request, dict), "REQUEST_JSON_INVALID")
    _scan_secrets(request)
    _require(set(request) == REQUEST_KEYS, "REQUEST_FIELDS_INVALID")
    _require(request["schema_id"] == REQUEST_SCHEMA, "REQUEST_SCHEMA_INVALID")
    _require(_label(request["request_label"]), "REQUEST_LABEL_INVALID")
    _require(request["corpus_class"] in SG.CORPUS_CLASSES, "CORPUS_CLASS_INVALID")
    _require(_utc(request["decision_time"]) is not None and request["decision_time"].endswith("Z")
             and len(request["decision_time"]) == 20, "DECISION_TIME_INVALID")
    _require(type(request["max_book_age_seconds"]) is int and 1 <= request["max_book_age_seconds"] <= 3600, "BOOK_AGE_INVALID")
    shares_text = request["basket_shares"]
    _require(type(shares_text) is str and _SHARES_RE.fullmatch(shares_text) is not None
             and 0 < Decimal(shares_text) <= MAX_SHARES, "BASKET_SHARES_INVALID")
    search = request["search"]
    _require(type(search) is dict and set(search) == SEARCH_KEYS and type(search["families"]) is list and search["families"]
             and len(set(search["families"])) == len(search["families"]) and set(search["families"]) <= set(RM.RELATIONS)
             and type(search["max_group_size"]) is int and 2 <= search["max_group_size"] <= 4
             and type(search["min_shared_terms"]) is int and 1 <= search["min_shared_terms"] <= 10
             and type(search["max_candidates"]) is int and 1 <= search["max_candidates"] <= 500, "SEARCH_INVALID")
    fee = request["fee_policy"]
    _require(type(fee) is dict and set(fee) == FEE_KEYS and fee["kind"] in RE.FEE_POLICY_KINDS and _label(fee["policy_id"]),
             "FEE_POLICY_INVALID")
    if fee["kind"] == "NONE":
        _require(fee["valid_from"] is None and fee["valid_until"] is None, "FEE_POLICY_INVALID")
    else:
        _require(all(type(fee[k]) is str and _utc(fee[k]) == fee[k] and len(fee[k]) == 20 for k in ("valid_from", "valid_until"))
                 and fee["valid_from"] < fee["valid_until"], "FEE_POLICY_INVALID")
    if fee["kind"] == "TEST_ONLY_HYPOTHETICAL":
        _require(fee["policy_id"].startswith("test-only-") and type(fee["test_rate"]) is str
                 and type(fee["test_exponent"]) is int and 0 <= fee["test_exponent"] <= EV.MAX_SUPPORTED_FEE_EXPONENT,
                 "FEE_POLICY_INVALID")
        try:
            rate = Decimal(fee["test_rate"])
        except InvalidOperation:
            _stop("FEE_POLICY_INVALID")
        _require(rate.is_finite() and 0 <= rate <= 1, "FEE_POLICY_INVALID")
    else:
        _require(fee["test_rate"] is None and fee["test_exponent"] is None, "FEE_POLICY_INVALID")
    _require(type(request["models"]) is list and 0 < len(request["models"]) <= MAX_MODELS, "MODELS_INVALID")
    _require(type(request["venue"]) is list and len(request["venue"]) <= MAX_VENUE, "VENUE_LIST_INVALID")
    _require(type(request["benchmark_sha256"]) is str and SG._SHA_RE.fullmatch(request["benchmark_sha256"]) is not None,
             "BENCHMARK_SHA_INVALID")
    if frozen:
        for number, entry in enumerate(request["venue"]):
            _require(type(entry) is dict and entry.get("gamma_file") == f"venue/{number:03d}-gamma.bin"
                     and entry.get("clob_file") == f"venue/{number:03d}-clob.bin", "FROZEN_REQUEST_INVALID")


def benchmark_commitment(request: dict) -> str:
    """Frozen BEFORE comparison: method settings, every case id/relation/markets and expected label."""
    cases = [[m.get("model_id"), m.get("relation"), m.get("market_ids"), m.get("expected")] if isinstance(m, dict) else None
             for m in request["models"]]
    return SG.sha256_hex(SG.canonical_bytes({"discovery_id": RM.DISCOVERY_ID, "baseline_id": RM.BASELINE_ID,
                                             "baseline_min_shared_terms": RM.BASELINE_MIN_SHARED_TERMS,
                                             "search": request["search"], "cases": cases}))


# ------------------------------------------------------------------ freeze


def _check_scratch(scratch: Path) -> Path:
    _require(scratch.is_absolute() and not _inside(scratch.resolve(), REPO_ROOT), "SCRATCH_INSIDE_REPOSITORY")
    _require(not scratch.is_symlink() and not (scratch.exists() and _unsafe_entry(scratch, directory=True)), "SCRATCH_INVALID")
    return scratch.resolve()


def _grounding_files(root: Path) -> list[Path]:
    files, total = [], 0
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        for name in dirnames:
            _require(not _unsafe_entry(Path(dirpath) / name, directory=True), "GROUNDING_SCRATCH_UNSAFE")
        for name in filenames:
            path = Path(dirpath) / name
            _require(not _unsafe_entry(path, directory=False), "GROUNDING_SCRATCH_UNSAFE")
            total += path.stat().st_size
            files.append(path)
    _require(len(files) <= MAX_GROUNDING_FILES and total <= MAX_GROUNDING_BYTES, "GROUNDING_SCRATCH_TOO_LARGE")
    _require((root / "receipt.json").is_file() and (root / "frozen_case.json").is_file(), "GROUNDING_SCRATCH_INVALID")
    return files


def freeze(grounding_dir: Path, request_path: Path, scratch: Path) -> None:
    grounding = _caller_path(str(grounding_dir), directory=True, scratch=scratch)
    _require(grounding is not None, "GROUNDING_SCRATCH_UNUSABLE")
    source = _caller_path(str(request_path), directory=False, scratch=scratch)
    raw = _read_capped(source, MAX_REQUEST_BYTES)
    _require(0 < len(raw), "REQUEST_UNREADABLE")
    _require(SG.SECRET_RE.search(raw.decode("utf-8", "replace")) is None, "SECRET_MATERIAL_REJECTED")
    request = _strict_json(raw, "REQUEST_JSON_INVALID")
    validate_request(request, frozen=False)
    _require(benchmark_commitment(request) == request["benchmark_sha256"], "BENCHMARK_FREEZE_MISMATCH")
    files = _grounding_files(grounding)
    inputs = scratch / "inputs"
    (inputs / "venue").mkdir(parents=True)
    for path in files:
        target = inputs / "grounding" / path.relative_to(grounding)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
        _require(_sha(path.read_bytes()) == _sha(target.read_bytes()), "INPUT_CHANGED_DURING_FREEZE")
    venue = []
    for number, entry in enumerate(request["venue"]):
        frozen_entry = dict(entry) if isinstance(entry, dict) else {"invalid_entry": True}
        for role in ("gamma", "clob"):
            rel = f"venue/{number:03d}-{role}.bin"
            path = _caller_path(entry.get(f"{role}_file") if isinstance(entry, dict) else None, directory=False, scratch=scratch)
            data = _read_capped(path, MAX_VENUE_BYTES)
            # An unusable path freezes as an empty file so the core counts it per leg, never silently drops it.
            (inputs / rel).write_bytes(data)
            frozen_entry[f"{role}_file"] = rel
        venue.append(frozen_entry)
    (inputs / "request.source.json").write_bytes(raw)
    (inputs / "request.json").write_bytes(SG.canonical_bytes(dict(request, venue=venue)))


# ------------------------------------------------------------------ core


def _venue_snapshots(entries: list, markets: dict, read) -> tuple[dict, dict, list]:
    """(market_id, side) -> native snapshot; per-entry outcomes; binding failures by key."""
    found: dict = {}
    failures: dict = {}
    outcomes = []
    for number, entry in enumerate(entries):
        status, side, snapshot_id = "BOUND", None, None
        market = markets.get(entry.get("market_id")) if isinstance(entry, dict) and type(entry.get("market_id")) is str else None
        gamma, clob = read(entry["gamma_file"]) if isinstance(entry, dict) else b"", read(entry["clob_file"]) if isinstance(entry, dict) else b""
        if not isinstance(entry, dict) or set(entry) != VENUE_KEYS or not all(type(entry[k]) is str for k in VENUE_KEYS):
            status = "VENUE_FIELDS_INVALID"
        elif market is None:
            status = "VENUE_MARKET_NOT_IN_CORPUS"
        elif "token:polymarket:" + entry["token_id"] not in market.token_ids or not market.condition_id:
            status = "VENUE_IDENTITY_MISMATCH"
        elif not gamma or not clob:
            status = "VENUE_FILE_UNUSABLE"
        elif _utc(entry["acquisition_started"]) != entry["acquisition_started"] or \
                _utc(entry["acquisition_completed"]) != entry["acquisition_completed"] or \
                len(entry["acquisition_completed"]) != 20 or entry["acquisition_started"] > entry["acquisition_completed"]:
            status = "VENUE_CLOCK_INVALID"
        else:
            try:
                document = PM.decode_public_json(gamma)
                tokens = PM._token_ids(document.get("clobTokenIds")) if isinstance(document, dict) else []
                labels = document.get("outcomes") if isinstance(document, dict) else None
                labels = json.loads(labels) if type(labels) is str else labels
                label = labels[tokens.index(entry["token_id"])] if type(labels) is list and len(labels) == len(tokens) == 2 \
                    and entry["token_id"] in tokens else None
                side = {"Yes": RE.YES, "No": RE.NO}.get(label)
                snapshot = PM.build_public_venue_snapshot(
                    gamma_market_id=entry["gamma_market_id"], condition_id=market.condition_id, token_id=entry["token_id"],
                    acquisition_started_ns=RE.utc_ns(entry["acquisition_started"]),
                    acquisition_completed_ns=RE.utc_ns(entry["acquisition_completed"]),
                    gamma=PM.SourceFetchResult("BODY", gamma), clob=PM.SourceFetchResult("BODY", clob))
            except (ExecutionFeasibilityError, ValueError, TypeError, IndexError, AttributeError, PM._Invalid, RecursionError):
                status = "VENUE_SOURCE_INVALID"
            else:
                snapshot_id = snapshot.venue_snapshot_id
                if side is None:
                    status = "ORIENTATION_UNKNOWN"
                elif (market.market_id, side) in found or (market.market_id, side) in failures:
                    found.pop((market.market_id, side), None)
                    failures[(market.market_id, side)] = "VENUE_DUPLICATE"
                    status = "VENUE_DUPLICATE"
                else:
                    found[(market.market_id, side)] = snapshot
        if status != "BOUND" and market is not None and side is not None and (market.market_id, side) not in failures:
            failures[(market.market_id, side)] = status
        outcomes.append({"index": number, "market_id": market.market_id if market else None, "side": side,
                         "status": status, "venue_snapshot_id": snapshot_id})
    return found, failures, outcomes


def _model_fields_ok(model: object) -> bool:
    if type(model) is not dict or set(model) != MODEL_KEYS:
        return False
    n = len(model["market_ids"]) if type(model["market_ids"]) is list else 0
    return (SG._QID_RE.fullmatch(model["model_id"] if type(model["model_id"]) is str else "") is not None
            and model["relation"] in RM.RELATIONS and 2 <= n <= 4 and all(type(m) is str for m in model["market_ids"])
            and type(model["timezones"]) is list and len(model["timezones"]) == n and all(type(t) is str for t in model["timezones"])
            and (model["yes_token_ids"] is None or (type(model["yes_token_ids"]) is list and len(model["yes_token_ids"]) == n))
            and (model["claimed_rule_sha256"] is None or (type(model["claimed_rule_sha256"]) is list
                                                         and len(model["claimed_rule_sha256"]) == n
                                                         and all(type(d) is str for d in model["claimed_rule_sha256"])))
            and (model["cross_venue"] is None or _label(model["cross_venue"])) and type(model["combo"]) is bool
            and model["expected"] in EXPECTED_LABELS and type(model["claimed_verdict"]) in (type(None), bool, str))


def _disposition(formal: str | None, real: str | None, matched: bool, fields_ok: bool) -> str:
    if not fields_ok or formal in ("MODEL_STATE_SHAPE_INVALID", "MODEL_DUPLICATE_STATE", "GROUP_SIZE_UNSUPPORTED"):
        return "MODEL_INVALID"
    if not matched:
        return "NOT_NATIVE_CANDIDATE"
    if formal == "FORMAL_COUNTEREXAMPLE":
        return "COUNTEREXAMPLE"
    if formal != "FORMAL_BOUNDED_PAYOFF_PROOF":
        return "INCONCLUSIVE"
    if real == "RULE_CONFLICT":
        return "RULE_CONFLICT"
    return "INCONCLUSIVE" if real == "EXTERNAL_VENUE_UNVERIFIED" else "FORMAL_VALID"


def assess_model(model: object, markets: dict, rule_rows: dict, candidates: dict, venue: tuple, request: dict,
                 fee_policy: dict, decision_ns: int) -> dict:
    fields_ok = _model_fields_ok(model)
    row = {"model_id": model.get("model_id") if isinstance(model, dict) and type(model.get("model_id")) is str else None,
           "relation": None, "market_ids": [], "expected": model.get("expected") if isinstance(model, dict) else None,
           "native_candidate_key": None, "native_generators": [], "rules": [], "formal": None, "real_world": None,
           "economics": {"status": "NOT_EVALUATED", "reason": None, "baskets": []}, "baseline_related": False,
           "claimed_verdict_ignored": True}
    if not fields_ok:
        row.update(status="MODEL_FIELDS_INVALID", disposition="MODEL_INVALID")
        return row
    relation, ids, n = model["relation"], model["market_ids"], len(model["market_ids"])
    row.update(relation=relation, market_ids=list(ids))
    present = [markets.get(m) for m in ids]
    if len(set(ids)) != n or None in present:
        row.update(status="MARKET_DUPLICATE_OR_NOT_IN_CORPUS", disposition="NOT_NATIVE_CANDIDATE")
        return row
    row["baseline_related"] = RM.baseline_native_relation_fields_v0(present)
    candidate = candidates.get(RM.candidate_key(relation, ids))
    rules = [rule_rows[m] for m in ids]
    row["rules"] = [{"market_id": r["market_id"], "status": r["status"], "rule_content_sha256": r["rule_content_sha256"]} for r in rules]
    formal = RM.formal_proof(relation, n, model["states"], model["special_states"])
    real = RM.real_world_classification(relation, present, rules, model)
    if model["yes_token_ids"] is not None:
        # The caller's YES-token belief must agree with the Gamma outcome order of the frozen venue bytes.
        venue_yes = {m: "token:polymarket:" + snap.token_id for (m, s), snap in venue[0].items() if s == RE.YES}
        if any(type(t) is not str or t not in markets[m].token_ids or (m in venue_yes and venue_yes[m] != t)
               for m, t in zip(ids, model["yes_token_ids"])):
            kept = set(real["reasons"]) - {"NATIVE_PIT_HAS_RULE_HASH_NOT_FORMAL_RESOLVER"}
            real = dict(real, status="RULE_CONFLICT", reasons=sorted(kept | {"ORIENTATION_CONTRADICTED"}))
    row.update(formal=formal, real_world=real,
               disposition=_disposition(formal["status"], real["status"], candidate is not None, True))
    if candidate is None:
        # Caller models only qualify candidates the native discovery proposed; never a manual pair list.
        row["status"] = "NOT_NATIVE_CANDIDATE"
        return row
    row.update(native_candidate_key=candidate["candidate_key"], native_generators=candidate["generators"], status="EVALUATED")
    if formal["status"] != "FORMAL_BOUNDED_PAYOFF_PROOF":
        row["economics"]["reason"] = "NO_FORMAL_PROOF"
        return row
    if real["status"] in ("RULE_CONFLICT", "EXTERNAL_VENUE_UNVERIFIED"):
        row["economics"]["reason"] = real["status"]
        return row
    shares = Decimal(request["basket_shares"])
    baskets = []
    for basket in RE.reference_baskets(relation, n):
        legs = []
        for market_id, side in zip(ids, basket["sides"]):
            leg = RE.assess_leg(venue[0].get((market_id, side)), binding_reason=venue[1].get((market_id, side)), shares=shares,
                                decision_ns=decision_ns, max_age_ns=request["max_book_age_seconds"] * 1_000_000_000,
                                fee_policy=fee_policy, policy=request["fee_policy"])
            legs.append(dict(leg, market_id=market_id, side=side))
        baskets.append(RE.assess_basket(basket, formal["states_admitted"], legs, shares, combo=model["combo"],
                                        fee_test_only=fee_policy["test_only"]))
    order = {s: i for i, s in enumerate(("FEE_AND_DEPTH_CONDITIONAL", "THEORETICAL_PRICE_INCONSISTENCY", "NO_CONDITIONAL_EDGE",
                                         "MECHANICALLY_INCONCLUSIVE", "NOT_EXECUTABLE"))}
    row["economics"] = {"status": min((b["status"] for b in baskets), key=order.get), "reason": None, "baskets": baskets}
    return row


def _benchmark(rows: list) -> dict:
    total = len(rows)
    truth = [r["expected"] == "FORMAL_VALID" for r in rows]
    verifier = [r["disposition"] == "FORMAL_VALID" for r in rows]
    baseline = [r["baseline_related"] for r in rows]
    abstain = ("INCONCLUSIVE", "NOT_NATIVE_CANDIDATE", "MODEL_INVALID")
    evaluated = [r for r in rows if r["status"] == "EVALUATED"]

    def method(proposed):
        tp = sum(1 for p, t in zip(proposed, truth) if p and t)
        fp = sum(1 for p, t in zip(proposed, truth) if p and not t)
        return {"proposed": sum(proposed), "true_matches": tp, "false_relationship_matches": fp,
                "precision": RM.ratio(tp, sum(proposed)), "recall": RM.ratio(tp, sum(truth)),
                "false_positive_rate": RM.ratio(fp, total - sum(truth))}
    baskets = [b for r in rows for b in r["economics"]["baskets"]]
    legs = [leg for b in baskets for leg in b["legs"]]
    disposition_counts = dict(sorted(Counter(r["disposition"] for r in rows).items()))
    return {
        "cases_total": total, "expected_label_counts": dict(sorted(Counter(r["expected"] for r in rows).items())),
        "disposition_counts": disposition_counts,
        "disposition_agreement": RM.ratio(sum(1 for r in rows if r["disposition"] == r["expected"]), total),
        RM.BASELINE_ID: method(baseline), "related_market_verifier_v1": method(verifier),
        "eligible_inspected": sum(1 for r in rows if r["status"] == "EVALUATED"),
        "native_candidates_matched": sum(1 for r in rows if r["native_candidate_key"]),
        "formal_conditional_proofs": sum(1 for r in rows if r["formal"] and r["formal"]["status"] == "FORMAL_BOUNDED_PAYOFF_PROOF"),
        "native_identity_only": sum(1 for r in evaluated if r["real_world"]["status"] == "MECHANICAL_IDENTITY_NOT_INDEPENDENT"),
        "semantic_unknown": sum(1 for r in evaluated if r["real_world"]["status"].startswith("INCONCLUSIVE")),
        "abstained_or_ambiguous": sum(1 for r in rows if r["disposition"] in abstain),
        "real_world_verified": 0, "real_world_evaluable": 0,
        "economic_status_counts": dict(sorted(Counter(r["economics"]["status"] for r in rows).items())),
        "price_inconsistencies": sum(1 for b in baskets if b["status"] == "THEORETICAL_PRICE_INCONSISTENCY"),
        "after_cost_test_evaluable": sum(1 for b in baskets if b["all_in_cost_usd"] is not None),
        "fee_known_legs": sum(1 for leg in legs if leg["fee_bound_usd"] is not None),
        "fee_unknown_legs": sum(1 for leg in legs if leg["fee_bound_usd"] is None),
        "zero_improvement_permitted": True,
    }


def build_related_core(input_dir: Path, code_id: str, grounding_verification: dict) -> dict:
    input_dir = Path(input_dir)

    def read(rel: str) -> bytes:
        path = input_dir / rel
        return path.read_bytes() if type(rel) is str and path.is_file() and not path.is_symlink() else b""
    request = _strict_json(read("request.json"), "FROZEN_REQUEST_UNREADABLE")
    validate_request(request, frozen=True)
    _require(benchmark_commitment(request) == request["benchmark_sha256"], "BENCHMARK_FREEZE_MISMATCH")
    grounding = input_dir / "grounding"
    case = _strict_json(read("grounding/frozen_case.json"), "GROUNDING_SCRATCH_INVALID")
    _require(isinstance(case, dict) and case.get("corpus_class") == request["corpus_class"], "CORPUS_CLASS_MISMATCH")
    as_of = RP.canonicalize_utc_timestamp(case["as_of"])
    policy, universe = SG.load_corpus(grounding / "inputs" / "pit.sqlite3", case["policy"], as_of)
    bound, rule_outcomes = SG.bind_rule_texts(universe, case["rule_texts"],
                                             lambda rel: read("grounding/inputs/" + rel) if type(rel) is str else b"")
    store = PRS.load_and_verify_point_in_time_record_store(grounding / "inputs" / "pit.sqlite3")
    _require(store.is_valid and store.snapshot is not None, "PIT_STORE_INVALID")
    pit_rules = {r.envelope.record_version_id: r for r in store.snapshot.records if isinstance(r, PR.ResolutionRuleSnapshotRecord)}
    markets = {m.market_id: m for m in universe.markets}
    rule_rows = {}
    for market in universe.markets:
        native = bound.get(market.market_id)
        version = next((r.rule_record_version_id for r in market.rules if native and r.rule_content_sha256 == native["rule_content_sha256"]), None)
        rule_rows[market.market_id] = RM.market_rule_status(market, native, pit_rules.get(version))
    discovery = RM.discover_candidates(universe, request["search"])
    candidates = {c["candidate_key"]: c for c in discovery["candidates"]}
    decision_ns = RE.utc_ns(request["decision_time"])
    fee_policy = RE.evaluate_fee_policy(request["fee_policy"], decision_ns)
    venue = _venue_snapshots(request["venue"], markets, read)
    seen, rows = set(), []
    for model in request["models"]:
        row = assess_model(model, markets, rule_rows, candidates, venue, request, fee_policy, decision_ns)
        if row["model_id"] in seen:
            row.update(status="MODEL_ID_DUPLICATE", disposition="MODEL_INVALID", formal=None, real_world=None,
                       economics={"status": "NOT_EVALUATED", "reason": "MODEL_ID_DUPLICATE", "baskets": []})
        seen.add(row["model_id"])
        rows.append(row)
    file_hashes = {rel: (SG.sha256_hex(read(rel)) if read(rel) else None) for rel in sorted(
        ["request.json", "request.source.json"] + [e[k] for e in request["venue"] for k in ("gamma_file", "clob_file")]
        + ["grounding/" + p.relative_to(grounding).as_posix() for p in sorted(grounding.rglob("*")) if p.is_file()])}
    core = {
        "schema_id": RECEIPT_SCHEMA, "wp_id": WP_ID, "posture": SG.RESEARCH_ONLY, "request_label": request["request_label"],
        "corpus_class": request["corpus_class"], "caller": CALLER, "code_identity": code_id,
        "source_pins": [dict(p) for p in RM.SOURCE_PINS],
        "method": {"discovery_id": RM.DISCOVERY_ID, "generators": list(RM.GENERATORS), "baseline_id": RM.BASELINE_ID,
                   "baseline_min_shared_terms": RM.BASELINE_MIN_SHARED_TERMS, "search": request["search"],
                   "relations": list(RM.RELATIONS), "fee_quantum": str(EV.FEE_QUANTUM), "fee_rounding": "ROUND_CEILING_PER_LEG",
                   "native_mechanics": "src.execution_feasibility build_public_venue_snapshot + evaluator helpers"},
        "inputs": {"as_of": as_of, "decision_time": request["decision_time"], "file_sha256": file_hashes,
                   "grounding_receipt_id": grounding_verification["receipt_id"],
                   "grounding_verification": grounding_verification["status"],
                   "alpha_discovery_policy_id": policy.alpha_discovery_policy_id,
                   "alpha_universe_snapshot_id": universe.alpha_universe_snapshot_id,
                   "benchmark_sha256": request["benchmark_sha256"]},
        "corpus": {"markets_total": len(universe.markets), "market_ids": sorted(markets),
                   "rule_status_counts": dict(sorted(Counter(r["status"] for r in rule_rows.values()).items())),
                   "rule_text_entries": rule_outcomes, "rules": [rule_rows[m] for m in sorted(rule_rows)],
                   "event_id_condition_derived": sum(1 for m in universe.markets if SG._event_identity(m) == "EVENT_ID_CONDITION_DERIVED")},
        "discovery": discovery,
        "venue": {"entries": venue[2], "counts": dict(sorted(Counter(o["status"] for o in venue[2]).items()))},
        "fee_policy": fee_policy,
        "results": rows,
        "benchmark": _benchmark(rows),
        "adoption": {
            "R3-03": "INTEGRATED_OFFLINE_CONDITIONAL_NOT_VALUE_VERIFIED",
            "R3-03-FEES": "NATIVE_FEE_PATH_CONDITIONAL_EXPIRED_POLICY_REFUSED",
            "R3-04": "SETTLEMENT_COMPATIBILITY_INCONCLUSIVE_WITHOUT_FORMAL_RESOLVER",
            "R3-11": "COUNTEREXAMPLE_CHECK_INTEGRATED_NO_LLM_PROOF",
            "R3-19": "SAME_INSUFFICIENT_NOT_SAME_DISPOSITION_INTEGRATED",
            "reason": ("SANITIZED_SYNTHETIC corpus proves callable behaviour only, never real Alpha or arbitrage"
                       if request["corpus_class"] == "SANITIZED_SYNTHETIC" else
                       "LOCAL_REAL_PIT observation awaits independent review; never self-declared VALUE_VERIFIED"),
            "other_31_capability_ids": "UNCHANGED", "provider_lanes": "SIX_SEPARATE_OWNER_GATES_UNCHANGED",
        },
        "authority": {"research_only": True, "executable_edge": False, "guaranteed_arbitrage": False, "profit_claim": False,
                      "orders": False, "strategy": False, "paper": False, "live": False, "capital": False,
                      "store_writes": False, "wp170_registry_writes": False, "llm_or_hermes": False,
                      "network_calls": 0, "provider_calls": 0, "credentials": False},
    }
    return json.loads(SG.canonical_bytes(core))


def finalize(core: dict) -> dict:
    return {"core": core, "receipt_id": RECEIPT_PREFIX + SG.sha256_hex(SG.canonical_bytes({"core": core}))}


# ------------------------------------------------------------------ commands


def _verify_grounding(scratch: Path) -> dict:
    try:
        result = SGCLI.verify(scratch / "inputs" / "grounding")
    except SG.GroundingStop:
        _stop("GROUNDING_RECEIPT_NOT_VERIFIED")
    _require(result["status"] == "VERIFIED", "GROUNDING_RECEIPT_NOT_VERIFIED")
    return {"status": result["status"], "receipt_id": result["receipt_id"]}


def run(grounding_dir: Path, request_path: Path, scratch_dir: Path) -> dict:
    started = time.monotonic()
    scratch = _check_scratch(Path(scratch_dir))
    if scratch.exists() and any(scratch.iterdir()):
        return _repeat(grounding_dir, request_path, scratch)
    with SGCLI.no_network() as attempts:
        freeze(Path(grounding_dir), Path(request_path), scratch)
        verification = _verify_grounding(scratch)
        core = build_related_core(scratch / "inputs", code_identity(), verification)
    _require(not attempts, "NETWORK_ATTEMPT_BLOCKED")
    _require(time.monotonic() - started <= MAX_RUN_SECONDS, "TIME_BUDGET_EXCEEDED")
    receipt = finalize(core)
    with open(scratch / "receipt.json", "xb") as handle:
        handle.write(json.dumps(receipt, sort_keys=True, indent=1, ensure_ascii=False).encode("utf-8"))
    return {"status": "RUN_COMPLETE", "receipt_id": receipt["receipt_id"], "results": len(core["results"]),
            "candidates": len(core["discovery"]["candidates"]), "network_attempts": 0}


def _repeat(grounding_dir: Path, request_path: Path, scratch: Path) -> dict:
    """Safe repeat: identical inputs over a verified receipt return it; nothing is written."""
    _require((scratch / "receipt.json").is_file(), "SCRATCH_NOT_EMPTY")
    checked = verify(scratch)
    _require(checked["status"] == "VERIFIED", "SCRATCH_NOT_EMPTY")
    source = _caller_path(str(request_path), directory=False, scratch=scratch)
    grounding = _caller_path(str(grounding_dir), directory=True, scratch=scratch)
    raw = _read_capped(source, MAX_REQUEST_BYTES)
    frozen = scratch / "inputs"
    _require(grounding is not None and raw == (frozen / "request.source.json").read_bytes(), "SCRATCH_NOT_EMPTY")
    # Every caller byte the receipt depends on must be identical: the grounding tree and each venue body.
    current = {"grounding/" + p.relative_to(grounding).as_posix(): _sha(p.read_bytes()) for p in _grounding_files(grounding)}
    for number, entry in enumerate(_strict_json(raw, "SCRATCH_NOT_EMPTY")["venue"]):
        for role in ("gamma", "clob"):
            path = _caller_path(entry.get(f"{role}_file") if isinstance(entry, dict) else None, directory=False, scratch=scratch)
            current[f"venue/{number:03d}-{role}.bin"] = _sha(_read_capped(path, MAX_VENUE_BYTES))
    stored = {"grounding/" + p.relative_to(frozen / "grounding").as_posix(): _sha(p.read_bytes())
              for p in (frozen / "grounding").rglob("*") if p.is_file()}
    stored.update({rel: _sha((frozen / rel).read_bytes()) for rel in current if rel.startswith("venue/") and (frozen / rel).is_file()})
    _require(stored == current, "SCRATCH_NOT_EMPTY")
    return {"status": "IDEMPOTENT_VERIFIED", "receipt_id": checked["receipt_id"], "network_attempts": 0}


def verify(scratch_dir: Path) -> dict:
    scratch = Path(scratch_dir)
    _require(scratch.is_absolute() and scratch.is_dir() and not _inside(scratch.resolve(), REPO_ROOT), "SCRATCH_INVALID")
    scratch = scratch.resolve()
    with SGCLI.no_network() as attempts:
        receipt = _strict_json((scratch / "receipt.json").read_bytes() if (scratch / "receipt.json").is_file() else b"",
                               "RECEIPT_UNREADABLE")
        try:
            verification = _verify_grounding(scratch)
            core = build_related_core(scratch / "inputs", code_identity(), verification)
        except SG.GroundingStop as stop:
            return {"status": "TAMPER_DETECTED", "failures": [f"RECOMPUTE_REFUSED:{stop}"],
                    "receipt_id": receipt.get("receipt_id") if isinstance(receipt, dict) else None, "network_attempts": 0}
    _require(not attempts, "NETWORK_ATTEMPT_BLOCKED")
    failures = []
    if not isinstance(receipt, dict) or set(receipt) != {"core", "receipt_id"} or not isinstance(receipt["core"], dict):
        failures.append("RECEIPT_SHAPE_INVALID")
    else:
        if receipt["receipt_id"] != finalize(receipt["core"])["receipt_id"]:
            failures.append("RECEIPT_ID_MISMATCH")
        failures.extend(f"OUTPUT_MISMATCH:{k}" for k in sorted(set(core) | set(receipt["core"]))
                        if receipt["core"].get(k) != core.get(k))
    return {"status": "VERIFIED" if not failures else "TAMPER_DETECTED", "failures": failures,
            "receipt_id": receipt.get("receipt_id") if isinstance(receipt, dict) else None, "network_attempts": 0}


def run_safe(command: str, args) -> dict:
    """Closed result for every outcome; refusals carry a stable code and never echo input or paths."""
    try:
        if command == "run":
            return run(args.grounding_scratch, args.request_file, args.scratch_dir)
        return verify(args.scratch_dir)
    except SG.GroundingStop as stop:
        return {"status": "STOPPED", "reason_code": str(stop)}
    except FileExistsError:
        return {"status": "STOPPED", "reason_code": "WRITE_ONCE_CONFLICT"}
    except Exception:  # noqa: BLE001 - sanitized: no exception text or path is echoed
        return {"status": "STOPPED", "reason_code": "INTERNAL_REFUSAL"}


OK_STATUSES = ("RUN_COMPLETE", "VERIFIED", "IDEMPOTENT_VERIFIED")


def add_run_arguments(parser) -> None:
    parser.add_argument("--grounding-scratch", required=True, type=Path)
    parser.add_argument("--request-file", required=True, type=Path)
    parser.add_argument("--scratch-dir", required=True, type=Path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    add_run_arguments(sub.add_parser("run"))
    sub.add_parser("verify").add_argument("--scratch-dir", required=True, type=Path)
    args = parser.parse_args(argv)
    result = run_safe(args.command, args)
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] in OK_STATUSES else 1


if __name__ == "__main__":
    raise SystemExit(main())
