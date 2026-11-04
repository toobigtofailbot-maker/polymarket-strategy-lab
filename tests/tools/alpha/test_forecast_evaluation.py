"""S10-R3-FORECAST-01 offline tests: real SRC-01 grounding -> verify -> forecast/abstain -> cohort -> score -> cold verify.

The corpus below is SANITIZED_SYNTHETIC and frozen inline (hash recorded in
docs/forecast_evaluation_contract.md). Method parameters were fixed before the corpus was written.
Results prove callable behaviour and honest accounting only, never real-world predictive value.
"""
from __future__ import annotations

import ast
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import hashlib
import json
import math
from pathlib import Path
import shutil
import socket
import subprocess
import sys

import pytest

import src.data_layer.analytical_research as ar
from src.data_layer.analytical_research import alpha_discovery as AD
from src.data_layer.analytical_research import forecast_evaluation as FE
from tests.data_layer.analytical_research.test_alpha_discovery import _pit_built, _pit_store
from tests.data_layer.analytical_research.test_experiment_os_preregistration import experiment_stack
from types import SimpleNamespace

from tests.tools.alpha.test_source_grounding import GOOD_HTML, _policy_mapping, _source
from tools.alpha import run_forecast_evaluation as CLI
from tools.alpha import run_source_grounding as SRC

REPO_ROOT = Path(__file__).resolve().parents[3]
AS_OF = "2026-06-01T12:00:00Z"
DECISION = "2026-06-02T00:00:00Z"
CUTOFF = "2027-12-31T00:00:00Z"
OBSERVED, INGESTED = "2026-06-01T00:00:01Z", "2026-06-01T00:00:02Z"

# ------------------------------------------------------------------ frozen SANITIZED_SYNTHETIC corpus
# (slug, event, category, resolution_date, target market_price or None, outcome label or None)
MARKETS = (
    ("ga-gov", "ga-gov-2026", "politics", "2026-11-03", "0.55", "Yes"),
    ("uk-pm", "uk-pm-2026", "politics", "2026-07-01", "0.2", "No"),
    ("fr-assembly", "fr-dissolve-2026", "politics", "2026-12-31", "0.31", "No"),
    ("house-control", "us-house-2026", "politics", "2026-11-30", "0.48", "Yes"),
    ("shutdown", "us-shutdown-2026", "politics", "2026-10-01", "0.62", "Yes"),
    ("oh-sen-dem", "oh-senate-2026", "politics", "2026-11-03", "0.41", "No"),
    ("oh-sen-rep", "oh-senate-2026", "politics", "2026-11-03", "0.59", "Yes"),
    ("nba-celtics", "nba-finals-2026", "sports", "2026-06-30", "0.37", "No"),
    ("wc-brazil", "world-cup-2026", "sports", "2026-07-19", "0.14", "No"),
    ("wimbledon", "wimbledon-2026", "sports", "2026-07-12", "0.45", "Yes"),
    ("superbowl", "super-bowl-lxi", "sports", "2027-02-14", "0.17", "No"),
    ("tdf", "tour-de-france-2026", "sports", "2026-07-26", "0.66", "Yes"),
    ("olympics-host", "olympics-2036", "sports", "2026-12-31", "0.28", "No"),
    ("nyc-temp", "nyc-high-temp-jul", "weather", "2026-07-05", "0.22", "No"),
    ("nyc-rain", "nyc-rain-jul", "weather", "2026-08-01", "0.35", "Yes"),
    ("hurricane-cat5", "atlantic-hurricanes-2026", "weather", "2026-11-30", "0.4", "No"),
    ("london-snow", "london-snow-xmas", "weather", "2026-12-26", "0.08", "No"),
    ("chicago-temp", "chicago-temp-jan", "weather", "2027-02-01", None, "Yes"),
    ("fed-cut-sep", "fed-sep-2026", "economics", "2026-09-17", "0.57", "Yes"),
    ("cpi", "us-cpi-aug-2026", "economics", "2026-09-15", "0.33", "No"),
    ("unemployment", "us-jobs-oct-2026", "economics", "2026-11-06", "0.25", "No"),
    ("recession", "us-recession-2026", "economics", "2027-06-30", "0.19", "No"),
    ("ecb", "ecb-oct-2026", "economics", "2026-10-30", "0", "No"),
    ("gdp", "us-gdp-q3-2026", "economics", "2026-10-29", "0.12", "No"),
    ("oscars-bp", "oscars-2027", "entertainment", "2027-03-15", "0.44", "Yes"),
    ("taylor-album", "taylor-album-2026", "entertainment", "2026-12-31", "0.52", "Yes"),
    ("box-office", "summer-box-office-2026", "entertainment", "2026-09-30", "0.61", "Yes"),
    ("grammys", "grammys-2027", "entertainment", "2027-02-10", "0.27", "No"),
    ("starship", "starship-orbit-2026", "science", "2026-12-31", "0.7", "Yes"),
    ("artemis", "artemis-ii", "science", "2026-12-01", "0.46", "No"),
    ("fusion", "fusion-record-2026", "science", "2026-12-31", "0.36", "No"),
    ("ai-model", "ai-release-2026", "technology", "2026-12-31", "0.3", "No"),
    ("apple-glasses", "apple-glasses-2026", "technology", "2026-06-12", "1", "Yes"),
    ("ukraine-ceasefire", "ukraine-ceasefire-2026", "world", "2026-12-31", "0.21", None),
    ("mars-sample", "mars-sample-2026", "science", "2026-12-31", "0.11", "No"),
    ("eu-election", "eu-vote-2026", "politics", "2026-09-30", "0.5", "Yes"),
    ("btc-100k", "btc-100k-2026", "crypto", "2026-12-31", "0.4", "Yes"),
)
CATEGORIES = ("politics", "sports", "weather", "economics", "entertainment", "science")
HORIZON_DAYS = (10, 60, 200, 400)
HISTORY_PRICES = ("0.2", "0.35", "0.5", "0.65", "0.8")


def _history_specs():
    """120 resolved prior events; outcome pattern fixed a priori (40% YES), prices weakly informative."""
    specs = []
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    for i in range(120):
        days = HORIZON_DAYS[(i // 6) % 4]
        decision = start + timedelta(days=i)
        price = HISTORY_PRICES[(i * 3) % 5]
        outcome = 1 if (i * 7) % 10 < 4 else 0
        specs.append((f"h{i:03d}", f"hist-event-{i:03d}", CATEGORIES[i % 6], decision, days, outcome, price))
    return specs


HISTORY_SPECS = _history_specs()
CORPUS = {"class": "SANITIZED_SYNTHETIC", "markets": [list(m) for m in MARKETS],
          "history": [[s[0], s[1], s[2], s[3].strftime("%Y-%m-%d"), s[4], s[5], s[6]] for s in HISTORY_SPECS]}
CORPUS_SHA256 = "2b8be21612572111e5458a30923fe9a35133d44746a1e9b00e3d8ff8ec161238"


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _mid(slug):
    return f"market:polymarket:{slug}"


def _question(slug):
    return f"Synthetic question for {slug.replace('-', ' ')} resolving YES on its stated rule?"


def _rule(slug):
    return f"This SANITIZED_SYNTHETIC market {slug} resolves YES only if its named official source confirms the event. Otherwise NO."


def _pit_records():
    records = []
    times = dict(observed_time=OBSERVED, ingestion_time=INGESTED)
    for slug, event, category, date, _price, _label in MARKETS:
        payload = {"market_status": "open", "outcome_labels": ["No", "Yes"], "question_text": _question(slug),
                   "token_ids": [f"token:polymarket:{slug}-no", f"token:polymarket:{slug}-yes"],
                   "condition_id": f"condition:{slug}", "category": category, "resolution_date": date + "T00:00:00Z"}
        meta, _ = _pit_built("PIT-C01-VALID-MARKET-METADATA", platform_id="platform:polymarket",
                             event_id=f"event:polymarket:synthetic-{event}", market_id=_mid(slug),
                             source_id="source:polymarket:gamma-markets", source_assertion_id=f"assertion:fc01:meta:{slug}",
                             snapshot_id=f"snapshot:fc01:meta:{slug}", source_snapshot_id=f"source-snapshot:fc01:meta:{slug}",
                             event_time="2026-06-01T00:00:00Z", canonical_payload=payload, **times)
        source, _ = _pit_built("PIT-C04-VALID-SOURCE-SNAPSHOT", source_id=f"source:fc01:rules:{slug}",
                               snapshot_id=f"snapshot:fc01:rulesrc:{slug}", **times)
        rule, _ = _pit_built("PIT-C05-VALID-RESOLUTION-RULE-SNAPSHOT", platform_id="platform:polymarket",
                             event_id=f"event:polymarket:synthetic-{event}", market_id=_mid(slug),
                             resolution_source_id="resolution-source:polymarket:primary",
                             source_snapshot_id=source.envelope.source_snapshot_id,
                             rule_content_sha256=_sha(_rule(slug).encode()), snapshot_id=f"snapshot:fc01:rule:{slug}",
                             observed_time="2026-06-01T00:00:03Z", ingestion_time="2026-06-01T00:00:04Z")
        records.extend((meta, source, rule))
    return records


def _target(slug, price, label, **overrides):
    value = {"case_id": f"t-{slug}", "market_id": _mid(slug), "question_sha256": _sha(_question(slug).encode()),
             "rule_content_sha256": _sha(_rule(slug).encode()), "yes_label": "Yes", "decision_time": DECISION,
             "market_price": price, "price_observed_time": None if price is None else "2026-06-01T23:59:00Z",
             "outcome": None if label is None else {"label": label, "resolved_time": "2026-12-31T00:00:00Z",
                                                    "known_time": "2027-01-01T00:00:00Z",
                                                    "provenance": "SANITIZED_SYNTHETIC_LABEL"}}
    value.update(overrides)
    return value


def _history(spec, **overrides):
    hid, group, category, decision, days, outcome, price = spec
    resolution = decision + timedelta(days=days)
    value = {"history_id": hid, "event_group": group, "category": category, "decision_time": _iso(decision),
             "resolution_time": _iso(resolution), "resolution_known_time": _iso(resolution + timedelta(days=1)),
             "source_observed_time": _iso(decision), "evidence_capture": "PROSPECTIVE", "outcome": outcome,
             "market_price": price, "price_observed_time": _iso(decision - timedelta(seconds=60))}
    value.update(overrides)
    return value


def _cases(receipt_id, **overrides):
    targets = [_target(slug, price, label) for slug, _e, _c, _d, price, label in MARKETS]
    history = [_history(s) for s in HISTORY_SPECS]
    history += [  # explicit refusal rows kept in every denominator
        _history(("hx-backfilled", "hx-1", "politics", datetime(2024, 3, 1, tzinfo=timezone.utc), 60, 1, "0.5"),
                 evidence_capture="BACKFILLED"),
        _history(("hx-overlap", "event:polymarket:synthetic-us-cpi-aug-2026", "economics",
                  datetime(2024, 3, 1, tzinfo=timezone.utc), 60, 1, "0.5")),
        _history(("hx-late", "hx-3", "sports", datetime(2026, 5, 1, tzinfo=timezone.utc), 60, 1, "0.5")),
        _history(("hx-bool", "hx-4", "sports", datetime(2024, 3, 1, tzinfo=timezone.utc), 60, 1, "0.5"), outcome=True),
    ]
    value = {"schema_id": FE.CASES_SCHEMA, "case_label": "fc01-synthetic", "corpus_class": "SANITIZED_SYNTHETIC",
             "grounding_receipt_id": receipt_id, "wp170": None,
             "method": {"prior_alpha": "1", "prior_beta": "1", "min_training_n": 3, "wang_min_training_n": 20,
                        "horizon_edges_days": [30, 90, 365], "price_edges": ["0.2", "0.4", "0.6", "0.8"],
                        "max_price_age_seconds": 3600},
             "sampler": {"seed": "fc01-seed", "sample_n": 33}, "scoring_cutoff": CUTOFF,
             "history": history, "targets": targets}
    value.update(overrides)
    return value


@pytest.fixture(scope="module")
def world(tmp_path_factory):
    base = tmp_path_factory.mktemp("fc01_inputs")
    pit = _pit_store(base, _pit_records())
    rules = []
    for slug, *_ in MARKETS:
        path = (base / f"rule-{slug}.txt").resolve()
        path.write_bytes(_rule(slug).encode())
        rules.append({"market_id": _mid(slug), "file": str(path)})
    html = (base / "cpi.html").resolve()
    html.write_bytes(GOOD_HTML)
    sources = [_source("cpi-release", "cpi", html, GOOD_HTML),
               _source("starship-note", "starship", html, GOOD_HTML)]  # admitted by native SRC-01 quality/PIT rules
    src_case = {"schema_id": "s10-r3-src01-case-v1", "case_label": "fc01-grounding", "corpus_class": "SANITIZED_SYNTHETIC",
                "pit_store": str(pit), "alpha_registry": None, "policy": _policy_mapping(), "as_of": AS_OF,
                "rule_texts": rules, "sources": sources,
                "queries": [{"query_id": "q1", "text": "Starship orbit", "category_hint": "science",
                             "relevant_market_ids": [_mid("starship")]}]}
    case_path = base / "src-case.json"
    case_path.write_text(json.dumps(src_case), encoding="utf-8")
    grounding = (tmp_path_factory.mktemp("fc01_grounding") / "g").resolve()
    assert SRC.main(["run", "--case", str(case_path), "--scratch-dir", str(grounding)]) == 0
    receipt = json.loads((grounding / "receipt.json").read_text(encoding="utf-8"))
    return {"base": base, "pit": pit, "grounding": grounding, "src_receipt": receipt}


def _run(tmp_path, world, cases, name="fc"):
    cases_path = tmp_path / f"{name}-cases.json"
    cases_path.write_text(json.dumps(cases), encoding="utf-8")
    scratch = (tmp_path / name).resolve()
    code = CLI.main(["run", "--grounding-scratch", str(world["grounding"]), "--cases", str(cases_path),
                     "--scratch-dir", str(scratch)])
    receipt_path = scratch / "receipt.json"
    return code, scratch, json.loads(receipt_path.read_text(encoding="utf-8")) if receipt_path.exists() else None


@pytest.fixture(scope="module")
def baseline(world, tmp_path_factory):
    code, scratch, receipt = _run(tmp_path_factory.mktemp("fc01_run"), world, _cases(world["src_receipt"]["receipt_id"]))
    assert code == 0, receipt
    return scratch, receipt


def _bound(world, cases):
    """Native in-process binding for variant cores (same functions the CLI calls)."""
    g = world["grounding"]
    receipt = json.loads((g / "receipt.json").read_text(encoding="utf-8"))
    frozen = json.loads((g / "frozen_case.json").read_text(encoding="utf-8"))
    return FE.bind_grounding(receipt, frozen, g / "inputs", cases)


def _core(world, cases):
    return FE.build_evaluation_core(cases, _bound(world, cases), FE.bind_wp170(None, None), "code:test", {})


def _stdout(capsys):
    return json.loads(capsys.readouterr().out.strip().splitlines()[-1])


# ------------------------------------------------------------------ R001


def test_forecast_native_grounding_and_wp170_binding(world, tmp_path, monkeypatch, capsys):
    calls = []
    real = SRC.verify
    monkeypatch.setattr(SRC, "verify", lambda d: calls.append(Path(d)) or real(d))
    rid = world["src_receipt"]["receipt_id"]
    code, scratch, receipt = _run(tmp_path, world, _cases(rid))
    assert code == 0
    # actually cold-verified: the caller's SRC-01 scratch and then the frozen copy
    assert calls[0] == world["grounding"] and calls[1] == scratch / "inputs" / "grounding"
    core = receipt["core"]
    assert core["source_grounding"] == {"receipt_id": rid, "verify_status": "VERIFIED", "as_of": AS_OF,
                                        "alpha_universe_snapshot_id": world["src_receipt"]["core"]["inputs"]["alpha_universe_snapshot_id"],
                                        "bound_rule_markets": len(MARKETS), "markets_with_admitted_sources": 2}
    native = AD.build_alpha_universe_snapshot(world["pit"], AD.build_alpha_discovery_policy(_policy_mapping()).record, AS_OF).record
    by_id = {m.market_id: m for m in native.markets}
    starship = next(r for r in core["targets"] if r["case_id"] == "t-starship")
    assert starship["event_group"] == by_id[_mid("starship")].event_id
    assert starship["rule_content_sha256"] == by_id[_mid("starship")].rules[0].rule_content_sha256
    assert starship["outcome_labels"] == ["No", "Yes"] and starship["category"] == "science"
    accepted = {e["market_id"]: e["raw_evidence_reference_id"] for e in world["src_receipt"]["core"]["sources"]["entries"]
                if e["status"] == "ACCEPTED"}
    assert starship["source_status"] == "SRC01_ADMITTED_SOURCES"
    assert starship["grounded_source_reference_ids"] == [accepted[_mid("starship")]]
    plain = next(r for r in core["targets"] if r["case_id"] == "t-artemis")
    assert plain["source_status"] == "NO_ADMITTED_SOURCE" and plain["grounded_source_reference_ids"] == []
    assert core["history"]["provenance"] == "CALLER_ASSERTED_CLOCKS_NOT_SRC01_GROUNDED"
    assert core["wp170"]["status"] == "DIAGNOSTIC_ONLY_EXPERIMENT_UNBOUND" and core["score_status"] == "DIAGNOSTIC_ONLY"
    assert core["authority"]["wp170_run_evidence_receipt"] is False and core["authority"]["qualification_claim"] is False

    # foreign/wrong grounding receipt id and a tampered SRC-01 scratch both stop
    assert _run(tmp_path, world, _cases(FE.SG.RECEIPT_PREFIX + "0" * 64), "wrong")[0] == 1
    assert _stdout(capsys)["reason_code"] == "GROUNDING_RECEIPT_MISMATCH"
    bad = tmp_path / "bad-grounding"
    shutil.copytree(world["grounding"], bad)
    rule = next((bad / "inputs" / "rules").iterdir())
    rule.write_bytes(rule.read_bytes() + b" tampered")
    world_bad = dict(world, grounding=bad.resolve())
    assert _run(tmp_path, world_bad, _cases(rid), "tampered")[0] == 1
    assert _stdout(capsys)["reason_code"] == "GROUNDING_VERIFY_FAILED"

    # a real native WP170 registry is verified read-only; no preregistration is created
    registry = (tmp_path / "wp170" / "registry.sqlite3")
    registry.parent.mkdir()
    assert ar.initialize_experiment_registry(registry).is_valid
    records = experiment_stack()
    assert ar.append_experiment_records(registry, records).is_valid
    before = _sha(registry.read_bytes())
    experiment = records[-1]
    bound = _cases(rid, wp170={"registry_file": str(registry.resolve()), "experiment_id": experiment.experiment_id})
    code, scratch_b, receipt_b = _run(tmp_path, world, bound, "bound")
    assert code == 0
    w = receipt_b["core"]["wp170"]
    assert w["status"] == "WP170_REFERENCES_VERIFIED_READ_ONLY_MEMBERSHIP_NOT_MAPPED"
    assert w["experiment_id"] == experiment.experiment_id and w["split_assignment_id"] == experiment.split_assignment_id
    assert receipt_b["core"]["score_status"] == "DIAGNOSTIC_ONLY" and _sha(registry.read_bytes()) == before
    assert CLI.main(["verify", "--scratch-dir", str(scratch_b)]) == 0
    capsys.readouterr()
    missing = _cases(rid, wp170={"registry_file": str(registry.resolve()), "experiment_id": "experiment:sha256:" + "0" * 64})
    assert _run(tmp_path, world, missing, "missing-exp")[0] == 1
    assert _stdout(capsys)["reason_code"] == "WP170_EXPERIMENT_NOT_FOUND"
    junk = tmp_path / "junk.sqlite3"
    junk.write_bytes(b"not a registry")
    assert _run(tmp_path, world, _cases(rid, wp170={"registry_file": str(junk.resolve()), "experiment_id": "x"}), "junk")[0] == 1
    assert _stdout(capsys)["reason_code"] == "WP170_REGISTRY_INVALID"


# ------------------------------------------------------------------ R002


def _oracle_prior(category, horizon_days_band, decision="2026-06-02"):
    """Independent manual oracle: (k + 1) / (n + 2) over admitted same-stratum history."""
    lo, hi = horizon_days_band
    rows = [s for s in HISTORY_SPECS if s[2] == category and lo <= s[4] < hi]
    return Decimal(sum(s[5] for s in rows) + 1) / Decimal(len(rows) + 2), len(rows)


def test_forecast_training_only_independent_probability_or_abstain(world, baseline):
    _, receipt = baseline
    f = receipt["core"]["forecasts"]
    # starship: science, 2026-06-02 -> 2026-12-31 = 212 days -> H[90,365)d
    expected, n = _oracle_prior("science", (90, 365))
    ind = f["t-starship"]["methods"][FE.INDEPENDENT]
    assert ind["status"] == "FORECAST" and ind["lineage"] == "EXOGENOUS"
    assert Decimal(ind["p_yes"]) == expected.quantize(FE.Q12) and ind["training"]["n"] == n
    # the late sports history row (known after decision) is excluded from training for every target
    assert all(v["training_excluded_not_known_before_decision"] == 1 for v in f.values())
    # world/technology categories have no history: explicit ABSTAIN with numerator/denominator, no 0.5 or price
    tech = f["t-ai-model"]["methods"][FE.INDEPENDENT]
    assert tech == {"status": "ABSTAIN", "reason": "ABSTAIN_NO_TRAINING", "p_yes": None, "lineage": "EXOGENOUS",
                    "training": {"successes": 0, "n": 0, "required_n": 3}, "stratum": "technology|H[90,365)d"}
    base = f["t-ai-model"]["methods"][FE.BASE_RATE]
    assert base["status"] == "FORECAST" and base["training"]["n"] == 120  # admitted history known before decision
    # prices and target outcomes never move the independent forecast
    rid = world["src_receipt"]["receipt_id"]
    cases = _cases(rid)
    for t in cases["targets"]:
        t["market_price"] = "0.99" if t["market_price"] is not None else None
        if t["outcome"]:
            t["outcome"]["label"] = "No" if t["outcome"]["label"] == "Yes" else "Yes"
    changed = _core(world, cases)["forecasts"]
    common = set(f) & set(changed)  # new prices move price bands, so compare the shared selected cases
    assert len(common) >= 25
    for cid in common:
        assert changed[cid]["methods"][FE.INDEPENDENT] == f[cid]["methods"][FE.INDEPENDENT]
        assert changed[cid]["methods"][FE.BASE_RATE] == f[cid]["methods"][FE.BASE_RATE]
    # history known only after the decision cannot train: moving the decision earlier shrinks training
    early = _cases(rid)
    for t in early["targets"]:
        t["decision_time"] = AS_OF
        t["price_observed_time"] = None if t["market_price"] is None else "2026-06-01T11:59:00Z"
    early["history"].append(_history(("hx-after", "hx-9", "science", datetime(2025, 1, 1, tzinfo=timezone.utc), 200, 1, "0.5"),
                                     resolution_known_time="2026-06-01T18:00:00Z"))
    e = _core(world, early)["forecasts"]["t-starship"]
    assert e["training_excluded_not_known_before_decision"] == 2


# ------------------------------------------------------------------ R003


def _oracle_lambda(prices, outcomes):
    """Independent grid oracle for the intercept probit distortion (step 1e-4)."""
    from statistics import NormalDist
    nd = NormalDist()
    z = [nd.inv_cdf(min(max(p, 1e-6), 1 - 1e-6)) for p in prices]

    def nll(lam):
        return -sum(math.log(min(max(nd.cdf(zi - lam), 1e-12), 1 - 1e-12)) if y else
                    math.log(1 - min(max(nd.cdf(zi - lam), 1e-12), 1 - 1e-12)) for zi, y in zip(z, outcomes))
    return min((nll(k / 10000), k / 10000) for k in range(-10000, 10001))[1]


def test_forecast_price_wang_is_nonindependent_training_only(world, baseline):
    _, receipt = baseline
    f = receipt["core"]["forecasts"]
    w = f["t-starship"]["methods"][FE.WANG]
    assert w["lineage"] == "MARKET_PRICE_DERIVED" and w["status"] == "FORECAST"
    prices = [float(s[6]) for s in HISTORY_SPECS]
    outcomes = [s[5] for s in HISTORY_SPECS]
    assert abs(float(w["lambda"]) - _oracle_lambda(prices, outcomes)) <= 2e-4 and w["training"]["n"] == 120
    expected = FE.wang_transform(Decimal("0.7"), float(w["lambda"]))
    assert Decimal(w["p_yes"]) == expected and Decimal(w["p_yes"]) != Decimal("0.7")
    # never substituted for, or labelled as, the independent forecast
    assert w["p_yes"] != f["t-starship"]["methods"][FE.INDEPENDENT]["p_yes"]
    assert all(v["methods"][FE.WANG]["lineage"] != "EXOGENOUS" for v in f.values())
    assert receipt["core"]["authority"]["wang_is_exogenous"] is False
    # no target price -> unavailable; finite at 0/1 prices; outcomes of targets never refit lambda
    assert f["t-chicago-temp"]["methods"][FE.WANG]["status"] == "UNAVAILABLE"
    for p in (f["t-ecb"]["methods"][FE.WANG]["p_yes"], f["t-apple-glasses"]["methods"][FE.WANG]["p_yes"]):
        assert 0 < Decimal(p) < 1
    flipped = _cases(world["src_receipt"]["receipt_id"])
    for t in flipped["targets"]:
        if t["outcome"]:
            t["outcome"]["label"] = "No"
    assert _core(world, flipped)["forecasts"]["t-starship"]["methods"][FE.WANG]["lambda"] == w["lambda"]
    # too little priced training -> ABSTAIN, not a guess
    thin = _cases(world["src_receipt"]["receipt_id"])
    thin["method"]["wang_min_training_n"] = 500
    a = _core(world, thin)["forecasts"]["t-starship"]["methods"][FE.WANG]
    assert a["status"] == "ABSTAIN" and a["p_yes"] is None and a["training"] == {"n": 120, "required_n": 500}


# ------------------------------------------------------------------ R004


def test_forecast_frozen_stratification_and_exact_denominators(world, baseline):
    _, receipt = baseline
    cohort = receipt["core"]["cohort"]
    d = cohort["denominators"]
    assert d == {"offered": 37, "eligible": 36, "event_groups": 35, "event_group_duplicates": 1, "sampling_frame": 35,
                 "requested": 33, "selected": 33, "not_sampled": 2, "ineligible_by_reason": {"CRYPTO_EXCLUDED": 1}}
    assert sum(s["available"] for s in cohort["strata"]) == 35 and sum(s["selected"] for s in cohort["strata"]) == 33
    assert sorted(c for s in cohort["strata"] for c in s["selected_case_ids"]) == cohort["selected_case_ids"]
    for s in cohort["strata"]:
        p = s["inclusion_probability_within_stratum"]
        assert p["numerator"] == s["selected"] and p["denominator"] == s["available"]
    oh = [r for r in receipt["core"]["targets"] if r["case_id"] in ("t-oh-sen-dem", "t-oh-sen-rep")]
    assert sorted(r["status"] for r in oh) in (["EXCLUDED", "SELECTED"], ["EXCLUDED", "EXCLUDED"])
    assert any(r["reason"] == "EVENT_GROUP_DUPLICATE" for r in oh)
    assert all(r["event_group_selection"] == {"numerator": 1, "denominator": 2, "value": "0.500000000000"} for r in oh)
    # same-case membership: every method is forecast for exactly the selected set
    assert sorted(receipt["core"]["forecasts"]) == cohort["selected_case_ids"]
    # labels cannot affect sampling; the seed does
    rid = world["src_receipt"]["receipt_id"]
    relabeled = _cases(rid)
    for t in relabeled["targets"]:
        t["outcome"] = None
    assert _core(world, relabeled)["cohort"]["membership_sha256"] == cohort["membership_sha256"]
    # independent oracle for largest-remainder apportionment on a hand-built frame
    def frame():
        return [{"status": "ELIGIBLE", "case_id": f"c{i}", "event_group": f"g{i}", "category": cat, "horizon_band": "H",
                 "price_band": "P"} for i, cat in enumerate(["a"] * 5 + ["b"] * 3 + ["c"] * 2)]
    out = FE.freeze_cohort(frame(), {"seed": "s", "sample_n": 5})
    # shares 2.5 / 1.5 / 1.0 -> floors 2/1/1, the one leftover slot goes to the largest remainder tie broken by size (a)
    assert {s["stratum"]: s["selected"] for s in out["strata"]} == {"a|H|P": 3, "b|H|P": 1, "c|H|P": 1}
    picked_a = sorted((hashlib.sha256(f"s|c{i}".encode()).hexdigest(), f"c{i}") for i in range(5))[:3]
    assert sorted(c for _, c in picked_a) == next(s for s in out["strata"] if s["stratum"] == "a|H|P")["selected_case_ids"]
    again = FE.freeze_cohort(frame(), {"seed": "s", "sample_n": 5})
    assert again["membership_sha256"] == out["membership_sha256"]
    draws = set()
    for seed in ("s", "s2", "s3", "s4", "s5"):  # the seed, not the labels, decides the draw (hash oracle per seed)
        got = FE.freeze_cohort(frame(), {"seed": seed, "sample_n": 5})
        a_ids = next(x for x in got["strata"] if x["stratum"] == "a|H|P")["selected_case_ids"]
        assert a_ids == sorted(c for _, c in sorted((hashlib.sha256(f"{seed}|c{i}".encode()).hexdigest(), f"c{i}")
                                                    for i in range(5))[:3])
        draws.add(tuple(a_ids))
    assert len(draws) > 1


# ------------------------------------------------------------------ R005


def _manual_scores(p: Decimal, y: int):
    eps = Decimal("1e-12")
    q = min(max(p, eps), 1 - eps)
    q = q if y else 1 - q
    return (p - y) ** 2, -math.log(float(q)), 100 * math.log2(2 * float(q))


def test_forecast_brier_logloss_paired_baseline_and_abstention(baseline):
    _, receipt = baseline
    sc = receipt["core"]["scoring"]
    f = receipt["core"]["forecasts"]
    labels = {c["case_id"]: c["y"] for c in sc["cases"] if c["scorable"]}
    paired = [c for c in labels if all(f[c]["methods"][m]["status"] == "FORECAST" for m in FE.PRIMARY_METHODS)]
    wang_paired = [c for c in paired if f[c]["methods"][FE.WANG]["status"] == "FORECAST"]
    assert sc["denominators"]["paired_intersection"] == len(paired) > 0
    assert sc["denominators"]["paired_with_wang"] == len(wang_paired) > 0
    for m in FE.METHODS:
        got = sc["methods"][m]["on_paired"]
        ids = wang_paired if m == FE.WANG else paired
        b = [_manual_scores(Decimal(f[c]["methods"][m]["p_yes"]), labels[c]) for c in ids]
        assert got["n"] == len(ids)
        assert abs(Decimal(got["brier"]) - sum(x[0] for x in b) / len(b)) <= Decimal("1e-12")
        assert abs(float(got["log_loss"]) - sum(x[1] for x in b) / len(b)) <= 1e-9
        assert abs(float(got["baseline_score"]) - sum(x[2] for x in b) / len(b)) <= 1e-7
        assert sc["methods"][m]["cost"] == FE.COST and sc["methods"][m]["errors"] == 0
    # visible, not fabricated: unresolved, unavailable baseline, abstention, boundary 0/1, clipping
    assert sc["denominators"]["not_scorable_by_reason"].get("UNRESOLVED", 0) == (1 if "t-ukraine-ceasefire" in f else 0)
    assert sc["methods"][FE.MARKET]["unavailable"] >= (1 if "t-chicago-temp" in labels else 0)
    assert sc["methods"][FE.INDEPENDENT]["abstained"] >= 1
    mkt = sc["methods"][FE.MARKET]
    assert mkt["boundary_probability_0_or_1"] == sum(1 for c in labels if f[c]["methods"][FE.MARKET]["p_yes"] in ("0", "1"))
    assert mkt["on_own_available"]["clipped"] == mkt["boundary_probability_0_or_1"]
    assert sc["log_loss_epsilon"] == "1E-12" and sc["orientation"]["BRIER_SCORE"] == "LOWER_IS_BETTER"
    assert sc["lift_status"] == "SYNTHETIC_CONTRACT_EVIDENCE_NOT_VALUE"
    assert Decimal(sc["paired_deltas"]["independent_minus_market_brier"]) == \
        Decimal(sc["methods"][FE.INDEPENDENT]["on_paired"]["brier"]) - Decimal(sc["methods"][FE.MARKET]["on_paired"]["brier"])
    assert "total_ms" in receipt["non_identity"]
    # exact oracle points: Brier(0.7, YES) = 0.09; log loss at p = 0 for YES is clipped to -ln(1e-12), never infinite
    one = FE.score_one(Decimal("0.7"), 1)
    assert one["brier"] == Decimal("0.09") and abs(float(one["log_loss"]) + math.log(0.7)) < 1e-15
    edge = FE.score_one(Decimal("0"), 1)
    assert edge["clipped"] and abs(float(edge["log_loss"]) - 12 * math.log(10)) < 1e-9 and edge["brier"] == 1
    assert FE.score_one(Decimal("0.5"), 0)["baseline_score"] == 0
    assert FE._aggregate([]) == {"n": 0, "brier": None, "log_loss": None, "baseline_score": None, "clipped": 0}


# ------------------------------------------------------------------ R006


def _tampered_copy(scratch, tmp_path, name):
    target = tmp_path / name
    shutil.copytree(scratch, target)
    return target.resolve()


def test_forecast_cold_verify_tamper_and_temporal_conflicts(world, baseline, tmp_path, capsys):
    scratch, receipt = baseline
    listing = sorted((p.relative_to(scratch).as_posix(), _sha(p.read_bytes())) for p in scratch.rglob("*") if p.is_file())
    assert CLI.main(["verify", "--scratch-dir", str(scratch)]) == 0
    assert _stdout(capsys)["status"] == "VERIFIED"
    assert sorted((p.relative_to(scratch).as_posix(), _sha(p.read_bytes())) for p in scratch.rglob("*") if p.is_file()) == listing

    def edit_receipt(fn):
        def apply(d):
            r = json.loads((d / "receipt.json").read_text(encoding="utf-8"))
            fn(r)
            (d / "receipt.json").write_text(json.dumps(r), encoding="utf-8")
        return apply

    def edit_cases(fn, both=True):
        def apply(d):
            for name in (("inputs/cases.json", "frozen_cases.json") if both else ("inputs/cases.json",)):
                c = json.loads((d / name).read_text(encoding="utf-8"))
                fn(c)
                (d / name).write_text(json.dumps(c), encoding="utf-8")
        return apply

    def set_label(c):
        next(t for t in c["targets"] if t["case_id"] == "t-starship")["outcome"]["label"] = "No"

    def set_cutoff(c):
        c["scoring_cutoff"] = "2026-12-31T00:00:00Z"

    def set_decision(c):
        next(t for t in c["targets"] if t["case_id"] == "t-starship")["decision_time"] = "2026-06-03T00:00:00Z"

    def set_alpha(c):
        c["method"]["prior_alpha"] = "2"

    def set_seed(c):
        c["sampler"]["seed"] = "forged"

    def set_cost(r):
        r["core"]["scoring"]["methods"][FE.MARKET]["cost"]["spend_usd"] = "5"

    def rehash(r):
        r["core"]["forecasts"]["t-starship"]["methods"][FE.INDEPENDENT]["p_yes"] = "0.9"
        r["receipt_id"] = FE.RECEIPT_PREFIX + _sha(FE.SG.canonical_bytes(r["core"]))

    def provenance(r):
        r["core"]["method"]["producers"][FE.WANG]["lineage"] = "EXOGENOUS"

    def corrupt_grounding(d):
        rule = sorted((d / "inputs" / "grounding" / "inputs" / "rules").iterdir())[0]
        rule.write_bytes(b"changed rule")

    expectations = {
        "label": (edit_cases(set_label), "OUTPUT_MISMATCH:"),
        "cutoff": (edit_cases(set_cutoff), "OUTPUT_MISMATCH:"),
        "decision": (edit_cases(set_decision), "OUTPUT_MISMATCH:"),
        "model_param": (edit_cases(set_alpha), "OUTPUT_MISMATCH:"),
        "split_seed": (edit_cases(set_seed), "OUTPUT_MISMATCH:"),
        "frozen_only": (edit_cases(set_label, both=False), "FROZEN_CASES_MISMATCH"),
        "costs": (edit_receipt(set_cost), "RECEIPT_ID_MISMATCH"),
        "output_rehashed": (edit_receipt(rehash), "OUTPUT_MISMATCH:forecasts"),
        "model_provenance": (edit_receipt(provenance), "RECEIPT_ID_MISMATCH"),
        "foreign_id_text": (edit_receipt(lambda r: r.update(receipt_id="Synthetic question injected")), "RECEIPT_ID_MISMATCH"),
    }
    for name, (mutate, code) in expectations.items():
        copy_dir = _tampered_copy(scratch, tmp_path, name)
        mutate(copy_dir)
        assert CLI.main(["verify", "--scratch-dir", str(copy_dir)]) == 1, name
        out = capsys.readouterr().out
        result = json.loads(out)
        assert result["status"] == "TAMPER_DETECTED" and any(f.startswith(code) for f in result["failures"]), (name, result)
        assert "Synthetic question" not in out and "fc01-seed" not in out  # codes only, no raw input echo
    g = _tampered_copy(scratch, tmp_path, "grounding")
    corrupt_grounding(g)
    assert CLI.main(["verify", "--scratch-dir", str(g)]) == 1
    assert _stdout(capsys)["reason_code"] == "GROUNDING_VERIFY_FAILED"
    # temporal conflicts are per-case refusals, never silent scores
    rid = world["src_receipt"]["receipt_id"]
    cases = _cases(rid, sampler={"seed": "fc01-seed", "sample_n": 200})
    t = {x["case_id"]: x for x in cases["targets"]}
    t["t-starship"]["outcome"].update(resolved_time="2026-06-01T00:00:00Z", known_time="2026-06-01T00:00:00Z")  # pre-decision
    t["t-house-control"]["outcome"].update(resolved_time="2026-06-01T00:00:00Z", known_time="2026-07-01T00:00:00Z")
    t["t-artemis"]["outcome"]["known_time"] = "2028-01-01T00:00:00Z"  # after scoring cutoff
    t["t-fusion"]["outcome"]["resolved_time"] = "2027-02-01T00:00:00Z"  # resolved after known
    t["t-gdp"]["decision_time"] = "2026-05-01T00:00:00Z"  # before grounding cutoff
    t["t-uk-pm"]["decision_time"] = "2026-07-02T00:00:00Z"  # after resolution date
    t["t-cpi"]["price_observed_time"] = "2026-06-02T00:00:01Z"  # post-decision price
    t["t-tdf"]["price_observed_time"] = "2026-05-01T00:00:00Z"  # stale price
    core = _core(world, cases)
    reasons = core["scoring"]["denominators"]["not_scorable_by_reason"]
    assert reasons["OUTCOME_RESOLVED_BEFORE_DECISION"] == 2 and reasons["OUTCOME_AFTER_SCORING_CUTOFF"] == 1
    assert reasons["OUTCOME_CLOCK_INCONSISTENT"] == 1
    rows = {r["case_id"]: r for r in core["targets"]}
    assert rows["t-gdp"]["reason"] == "DECISION_BEFORE_GROUNDING_CUTOFF"
    assert rows["t-uk-pm"]["reason"] == "DECISION_AFTER_RESOLUTION_DATE"
    assert rows["t-cpi"]["price_reason"] == "PRICE_AFTER_DECISION" and rows["t-cpi"]["price_band"] == "MISSING"
    assert rows["t-tdf"]["price_reason"] == "PRICE_STALE"
    assert core["forecasts"]["t-cpi"]["methods"][FE.MARKET]["reason"] == "BASELINE_UNAVAILABLE:PRICE_AFTER_DECISION"


# ------------------------------------------------------------------ R007


def test_forecast_negative_matrix_and_authority_nonexpansion(world, tmp_path, capsys, monkeypatch):
    rid = world["src_receipt"]["receipt_id"]

    def stop(cases=None, raw=None, name="neg"):
        path = tmp_path / f"{name}.json"
        path.write_bytes(raw if raw is not None else json.dumps(cases).encode())
        scratch = (tmp_path / f"{name}-out").resolve()
        code = CLI.main(["run", "--grounding-scratch", str(world["grounding"]), "--cases", str(path), "--scratch-dir", str(scratch)])
        out = capsys.readouterr().out
        assert code == 1 and not (scratch / "receipt.json").exists()
        return json.loads(out)["reason_code"], out

    def mutate(fn):
        c = _cases(rid)
        fn(c)
        return c
    whole = {
        "missing_field": (mutate(lambda c: c.pop("sampler")), "CASES_FIELDS_INVALID"),
        "bool_as_number": (mutate(lambda c: c["method"].update(min_training_n=True)), "METHOD_INVALID"),
        "float_prior": (mutate(lambda c: c["method"].update(prior_alpha=1.0)), "METHOD_INVALID"),
        "noncanonical_edge": (mutate(lambda c: c["method"].update(price_edges=["0.20", "0.4"])), "METHOD_INVALID"),
        "unsorted_edges": (mutate(lambda c: c["method"].update(horizon_edges_days=[90, 30])), "METHOD_INVALID"),
        "noncanonical_prior": (mutate(lambda c: c["method"].update(prior_alpha="0001.5")), "METHOD_INVALID"),
        "duplicate_case_id": (mutate(lambda c: c["targets"].append(dict(c["targets"][0]))), "DUPLICATE_CASE_ID"),
        "duplicate_history_id": (mutate(lambda c: c["history"].append(dict(c["history"][0]))), "DUPLICATE_HISTORY_ID"),
        "empty_targets": (mutate(lambda c: c.update(targets=[])), "TARGETS_EMPTY"),
        "schema": (mutate(lambda c: c.update(schema_id="other")), "CASES_SCHEMA_INVALID"),
        "corpus_mismatch": (mutate(lambda c: c.update(corpus_class="LOCAL_REAL_PIT")), "CORPUS_CLASS_MISMATCH"),
        "secret_key": (mutate(lambda c: c["method"].update(api_key="x")), "FORBIDDEN_FIELD"),
        "trade_key": (mutate(lambda c: c["targets"][0].update(order_size="1")), "FORBIDDEN_FIELD"),
        "bad_cutoff": (mutate(lambda c: c.update(scoring_cutoff="2027-01-01T00:00:00+05:00")), "SCORING_CUTOFF_INVALID"),
    }
    for name, (cases, code) in whole.items():
        assert stop(cases, name=name)[0] == code, name
    secret = "sk-" + "a1b2c3d4" * 3
    code, out = stop(_cases(rid, case_label=secret), name="secret_value")
    assert code == "SECRET_MATERIAL_REJECTED" and secret not in out
    base_raw = json.dumps(_cases(rid))
    assert stop(raw=base_raw.replace('"min_training_n": 3', '"min_training_n": NaN').encode(), name="nan")[0] == "CASES_JSON_INVALID"
    assert stop(raw=base_raw.replace('"min_training_n": 3', '"min_training_n": Infinity').encode(), name="inf")[0] == "CASES_JSON_INVALID"
    assert stop(raw=base_raw.replace('"wp170": null', '"wp170": null, "wp170": null').encode(), name="dupkey")[0] == "CASES_JSON_INVALID"
    assert stop(raw=b"{not json", name="malformed")[0] == "CASES_JSON_INVALID"
    assert stop(raw=b" " * (CLI.MAX_CASES_BYTES + 1), name="oversized")[0] == "CASES_UNREADABLE"
    assert stop(raw=b"", name="empty")[0] == "CASES_UNREADABLE"
    # scratch inside the repository and a non-empty scratch are refused
    good = tmp_path / "good.json"
    good.write_text(base_raw, encoding="utf-8")
    assert CLI.main(["run", "--grounding-scratch", str(world["grounding"]), "--cases", str(good),
                     "--scratch-dir", str(REPO_ROOT / "fc01-scratch")]) == 1
    assert _stdout(capsys)["reason_code"] == "SCRATCH_INSIDE_REPOSITORY" and not (REPO_ROOT / "fc01-scratch").exists()

    # per-item rejections are counted, never silently dropped or scored
    def per_target(fn):
        c = _cases(rid, sampler={"seed": "fc01-seed", "sample_n": 200})
        fn({t["case_id"]: t for t in c["targets"]})
        return {r["case_id"] or f"#{r['index']}": r for r in _core(world, c)["targets"]}
    checks = (  # (row to inspect, mutation, expected reason); invalid rows carry no case_id, only an index
        ("#0", lambda t: t["t-ga-gov"].update(market_price=0.7), "TARGET_FIELDS_INVALID"),
        ("#0", lambda t: t["t-ga-gov"].update(market_price="1.5"), "TARGET_FIELDS_INVALID"),
        ("#0", lambda t: t["t-ga-gov"].update(market_price="-0.1"), "TARGET_FIELDS_INVALID"),
        ("#0", lambda t: t["t-ga-gov"].update(market_price="0.50"), "TARGET_FIELDS_INVALID"),
        ("#0", lambda t: t["t-ga-gov"].update(market_price=True), "TARGET_FIELDS_INVALID"),
        ("#0", lambda t: t["t-ga-gov"].update(decision_time="2026-06-02"), "TARGET_FIELDS_INVALID"),
        ("#0", lambda t: t["t-ga-gov"].pop("yes_label"), "TARGET_FIELDS_INVALID"),
        ("t-ecb", lambda t: t["t-ecb"].update(rule_content_sha256="0" * 64), "RULE_MISMATCH"),
        ("t-tdf", lambda t: t["t-tdf"].update(question_sha256="0" * 64), "QUESTION_MISMATCH"),
        ("t-nyc-rain", lambda t: t["t-nyc-rain"].update(yes_label="Maybe"), "OUTCOME_ORIENTATION_MISMATCH"),
        ("t-grammys", lambda t: t["t-grammys"].update(market_id=_mid("ghost")), "MARKET_NOT_IN_GROUNDING"),
        ("t-gdp", lambda t: t["t-recession"].update(market_id=_mid("gdp")), "DUPLICATE_MARKET"),
        ("t-recession", lambda t: t["t-recession"].update(market_id=_mid("gdp")), "QUESTION_MISMATCH"),
    )
    for key, fn, reason in checks:
        row = per_target(fn)[key]
        assert row["reason"] == reason and row["status"] == "INELIGIBLE", (key, row)
    native_gap = SimpleNamespace(market_id=_mid("nocat"), event_id="event:x", question_text="q", outcome_labels=("No", "Yes"),
                                 category=None, resolution_date=None)
    gap_rows = FE.evaluate_targets(
        {"method": _cases(rid)["method"], "targets": [_target("nocat", "0.5", "Yes", question_sha256=_sha(b"q"))]},
        {"universe": SimpleNamespace(markets=[native_gap]), "bound_rules": {}, "source_refs": {}, "as_of": AS_OF})
    assert gap_rows[0]["reason"] == "CATEGORY_MISSING"  # no "MISSING" sentinel stratum can collide with history
    hist = _core(world, _cases(rid))["history"]
    assert hist["excluded_by_reason"] == {"HISTORY_BACKFILLED": 1, "HISTORY_EVENT_GROUP_OVERLAPS_TARGET": 1,
                                          "HISTORY_FIELDS_INVALID": 1}
    assert hist["offered"] == 124 and hist["admitted"] == 121  # hx-late is admitted, then excluded per target by time
    # unverified / unresolved truth and wrong provenance are not scored
    c = _cases(rid, sampler={"seed": "fc01-seed", "sample_n": 200})
    tt = {t["case_id"]: t for t in c["targets"]}
    tt["t-starship"]["outcome"]["provenance"] = "LOCAL_RESOLUTION_RECORD"
    tt["t-artemis"]["outcome"]["label"] = "Maybe"
    tt["t-fusion"]["outcome"] = {"label": "Yes"}
    reasons = _core(world, c)["scoring"]["denominators"]["not_scorable_by_reason"]
    assert reasons["OUTCOME_PROVENANCE_INVALID"] == 1 and reasons["OUTCOME_LABEL_UNKNOWN"] == 1
    assert reasons["OUTCOME_INVALID"] == 1 and reasons["UNRESOLVED"] == 1
    # safe research wording is not overblocked: price/market words in keys and values are allowed
    ok = _cases(rid)
    ok["history"][0]["category"] = "price of eggs"
    FE.validate_cases(ok, frozen=False)
    # network attempts fail the run; no socket even when a caller tries
    monkeypatch.setattr(FE, "freeze_cohort", lambda *a, **k: socket.create_connection(("example.invalid", 80)))
    assert stop(_cases(rid), name="net")[0] == "NETWORK_ATTEMPT_BLOCKED"
    # authority non-expansion: no network/provider/Hermes/order/paper/live imports or writes in either module
    for path in (Path(FE.__file__), Path(CLI.__file__)):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        names = {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names} | \
                {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module}
        assert not names & {"socket", "urllib", "urllib.request", "http.client", "requests", "subprocess", "httpx", "ssl"}
        assert not any(x and any(p in x for p in ("execution", "paper_trading", "live_pilot", "hermes", "research_runtime",
                                                    "polymarket_client", "strategy")) for x in names)
        source = path.read_text(encoding="utf-8")
        assert "append_experiment_records" not in source and "initialize_" not in source and "while True" not in source


# ------------------------------------------------------------------ R008


def test_forecast_real_cli_offline_suite_and_adoption_truth(world, baseline, tmp_path):
    assert _sha(FE.SG.canonical_bytes(CORPUS)) == CORPUS_SHA256
    assert sum(1 for m in MARKETS if m[2] != "crypto") >= 30
    scratch, receipt = baseline
    core = receipt["core"]
    assert core["corpus_class"] == "SANITIZED_SYNTHETIC" and core["cohort"]["denominators"]["selected"] >= 30
    assert core["caller"] == FE.CALLER and receipt["receipt_id"].startswith(FE.RECEIPT_PREFIX)
    # the actual entry point, as a separate process, cold-verifies with zero network
    proc = subprocess.run([sys.executable, "-B", str(REPO_ROOT / "tools" / "alpha" / "run_forecast_evaluation.py"),
                           "verify", "--scratch-dir", str(scratch)], capture_output=True, text=True, timeout=300)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert json.loads(proc.stdout) == {"status": "VERIFIED", "failures": [], "receipt_id": receipt["receipt_id"],
                                       "network_attempts": 0}
    # deterministic rerun -> identical receipt id; write-once scratch
    code, _, again = _run(tmp_path, world, _cases(world["src_receipt"]["receipt_id"]), "again")
    assert code == 0 and again["receipt_id"] == receipt["receipt_id"]
    # adoption truth: no value, qualification or full parity closure from synthetic or tests-only evidence
    a = core["adoption"]
    assert a["value_status"] == "NO_REAL_VALUE_VERIFIED"
    assert {a[k] for k in ("R3-18", "R3-20", "R3-22")} == {"PARITY_OPEN_PENDING_KARL_ACCEPTANCE"}
    assert a["R3-10-WANG"].startswith("MARKET_PRICE_DERIVED") and a["provider_lanes"] == "UNCHANGED_SIX_OWNER_GATED"
    assert {p["capability"] for p in core["source_pins"]} == {"R3-01", "R3-06", "R3-10", "R3-10-WANG", "R3-12",
                                                               "R3-12-SAMPLER", "R3-18", "R3-20", "R3-22"}
    text = json.dumps(receipt)
    assert "REAL_VALUE_VERIFIED" not in text.replace("NO_REAL_VALUE_VERIFIED", "")
    assert all("NOT_VALUE_VERIFIED" in v or v.startswith("NO_REAL") for v in a.values() if v.endswith("VALUE_VERIFIED"))
    assert core["successor"]["wp_id"] == "S10-R3-LEARN-01" and core["successor"]["status"] == "MANDATORY_PENDING"
    assert core["authority"]["real_value_verified"] is False and core["authority"]["orders"] is False
    assert core["scoring"]["lift_status"] == "SYNTHETIC_CONTRACT_EVIDENCE_NOT_VALUE"
    # identical cohorts: every method is scored on the same paired set
    d = core["scoring"]["denominators"]
    assert {core["scoring"]["methods"][m]["on_paired"]["n"] for m in FE.PRIMARY_METHODS} == {d["paired_intersection"]}
    assert core["scoring"]["methods"][FE.WANG]["on_paired"]["n"] == d["paired_with_wang"] <= d["paired_intersection"]
