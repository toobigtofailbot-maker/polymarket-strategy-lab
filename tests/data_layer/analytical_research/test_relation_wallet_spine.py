"""S10-CAP-B2-RELATIONS-WALLET-01 R001/R002/R004/R006/R009/R011: shared-PIT A5 relation + A6 wallet consumers.

One SANITIZED_SYNTHETIC frozen world built only with existing native producers and unchanged test helpers:
the B1-A SRC-01 grounding (plus one same-event CPI market), a real REL-01 run over that SAME grounding, the
genuine vendored Oracle3 parity operator over that REL scratch, and a real WALLET-01 ledger appended through
the native API whose condition/token are the PIT target's. Nothing here proves real relations, settlement,
fees, copyable or predictive wallets, executable edge or value; public addresses are synthetic.
"""
from __future__ import annotations

import copy
import json
from hashlib import sha256
from pathlib import Path

import pytest

from src.data_layer.analytical_research import relation_wallet_spine as RW
from src.data_layer.analytical_research import source_grounding as SG
from src.data_layer.point_in_time_market_research.research_provenance import (
    ObservabilityEvidence, build_pit_timestamps, build_raw_evidence_reference, build_research_provenance_manifest)
from src.data_layer.wallet_intelligence import contracts as WCON
from src.data_layer.wallet_intelligence import ledger as WL
from src.data_layer.wallet_intelligence import profile as WP
from tests.data_layer.analytical_research import test_source_forecast_spine as B1
from tools.alpha import run_oracle3_upstream_parity as PAR
from tools.alpha import run_related_market_alpha as REL

TARGET = B1.TARGET
RELATED = "560006"  # same recorded event: >4% implies >3%
RELATED_ROW = (RELATED, "us-cpi-aug-2026", "economics", "Will US CPI inflation exceed 4% year over year in August 2026?",
               "2026-09-15", "Resolves YES if the BLS CPI-U twelve month change for August 2026 exceeds 4 percent.", None)
MARKETS = B1.MARKETS + (RELATED_ROW,)
DECISION = "2026-06-01T12:00:00Z"
WALLET = "0x" + "1" * 40
OTHER_WALLET = "0x" + "2" * 40
WALLET_AS_OF = "2026-06-01T03:00:00Z"
EVENT_AT, SEEN_AT, QUOTE_AT = "2026-06-01T02:00:00Z", "2026-06-01T02:00:05Z", "2026-06-01T02:00:06Z"
IMPL = [[0, 0], [0, 1], [1, 1]]
GAMMA_FEES = {"policy_id": "gamma-body-fees-20260601", "kind": "GAMMA_BODY_PER_MARKET", "valid_from": "2026-06-01T00:00:00Z",
              "valid_until": "2026-06-02T00:00:00Z", "test_rate": None, "test_exponent": None}
COST = {"taker_fee_per_share": "0.01", "slippage_per_share": "0.02", "transaction_cost_per_share": "0.005",
        "required_depth_shares": "1"}


def _tok(dec, side):
    no, yes = (t.rsplit(":", 1)[1] for t in B1._tokens(dec))
    return yes if side == "YES" else no


def _model(model_id, relation, decs, states, expected, special=(), **extra):
    model = {"model_id": model_id, "relation": relation, "market_ids": [B1._mid(d) for d in decs], "states": states,
             "special_states": [{"kind": k, "payout": p} for k, p in special], "timezones": ["UTC"] * len(decs),
             "yes_token_ids": None, "claimed_rule_sha256": None, "claimed_verdict": None, "cross_venue": None, "combo": False,
             "expected": expected}
    model.update(extra)
    return model


MODELS = [
    _model("b2-impl", "IMPLICATION", [RELATED, TARGET], IMPL, "FORMAL_VALID"),
    _model("b2-reverse", "IMPLICATION", [TARGET, RELATED], [[0, 0], [1, 0], [1, 1]], "COUNTEREXAMPLE"),
    _model("b2-tie", "COMPLEMENT", [TARGET, RELATED], [[1, 0], [0, 1]], "INCONCLUSIVE", special=[("TIE", None)]),
    _model("b2-void", "EXCLUSIVITY", [TARGET, RELATED], [[0, 0], [1, 0], [0, 1]], "FORMAL_VALID", special=[("VOID", [0, 0])]),
    _model("b2-cancel", "IMPLICATION", [RELATED, TARGET], IMPL, "INCONCLUSIVE", special=[("CANCEL", None)]),
    _model("b2-resched", "IMPLICATION", [RELATED, TARGET], IMPL, "INCONCLUSIVE", special=[("RESCHEDULE", None)]),
    _model("b2-partial", "EXCLUSIVITY", [TARGET, RELATED], [[0, 0], [1, 0], [0, 1]], "INCONCLUSIVE",
           special=[("PARTIAL", ["0.5", "0.5"])]),
    _model("b2-rule", "COMPLEMENT", [TARGET, RELATED], [[1, 0], [0, 1]], "RULE_CONFLICT", claimed_rule_sha256=["f" * 64, "f" * 64]),
    _model("b2-foreign", "IMPLICATION", ["560002", "560003"], IMPL, "NOT_NATIVE_CANDIDATE"),
]
SELECTED = [m["model_id"] for m in MODELS]
VENUE = ((RELATED, "NO", "0.55"), (TARGET, "YES", "0.40"), (TARGET, "NO", "0.62"), (RELATED, "YES", "0.47"))


def gamma(dec, rate="0.02"):
    return json.dumps({"id": str(700000 + int(dec)), "conditionId": B1._cond(dec),
                       "clobTokenIds": json.dumps([_tok(dec, "YES"), _tok(dec, "NO")]), "outcomes": json.dumps(["Yes", "No"]),
                       "active": True, "closed": False, "acceptingOrders": True, "enableOrderBook": True, "restricted": False,
                       "negRisk": False, "orderPriceMinTickSize": "0.01", "orderMinSize": "1", "feesEnabled": True,
                       "feeSchedule": {"rate": rate, "exponent": 1, "takerOnly": True}, "secondsDelay": 0}).encode()


def clob(dec, side, ask):
    return json.dumps({"market": B1._cond(dec), "asset_id": _tok(dec, side), "timestamp": "1780315195000", "hash": "b2",
                       "bids": [], "asks": [{"price": ask, "size": "50"}], "min_order_size": "1", "tick_size": "0.01",
                       "neg_risk": False, "last_trade_price": "0.5"}).encode()


def venue_entries(base: Path, venue=VENUE):
    entries = []
    for number, (dec, side, ask) in enumerate(venue):
        g, c = (base / f"gamma-{number:03d}.json").resolve(), (base / f"clob-{number:03d}.json").resolve()
        g.write_bytes(gamma(dec))
        c.write_bytes(clob(dec, side, ask))
        entries.append({"market_id": B1._mid(dec), "gamma_market_id": str(700000 + int(dec)), "token_id": _tok(dec, side),
                        "gamma_file": str(g), "clob_file": str(c), "acquisition_started": "2026-06-01T11:59:56Z",
                        "acquisition_completed": "2026-06-01T11:59:57Z"})
    return entries


def rel_request(entries, models=None):
    request = {"schema_id": REL.REQUEST_SCHEMA, "request_label": "b2-shared-case", "corpus_class": "SANITIZED_SYNTHETIC",
               "decision_time": DECISION, "max_book_age_seconds": 60, "basket_shares": "10",
               "search": {"families": ["IMPLICATION", "EXCLUSIVITY", "COMPLEMENT", "SAME_EVENT", "EVENT_SUM"],
                          "max_group_size": 4, "min_shared_terms": 4, "max_candidates": 200},
               "fee_policy": dict(GAMMA_FEES), "models": copy.deepcopy(models or MODELS), "venue": entries,
               "benchmark_sha256": "0" * 64}
    request["benchmark_sha256"] = REL.benchmark_commitment(request)
    return request


def run_rel_and_parity(world: dict, base: Path, models=None, name="rel"):
    base.mkdir(parents=True, exist_ok=True)
    request = (base / f"{name}-request.json").resolve()
    request.write_text(json.dumps(rel_request(venue_entries(base), models)), encoding="utf-8")
    rel_scratch, par_scratch = (base / f"{name}-scratch").resolve(), (base / f"{name}-parity").resolve()
    assert REL.run(world["grounding"], request, rel_scratch)["status"] == "RUN_COMPLETE"
    assert PAR.run(rel_scratch, par_scratch)["status"] == "RUN_COMPLETE"
    load = lambda p: json.loads((p / "receipt.json").read_text(encoding="utf-8"))  # noqa: E731
    return {"rel_scratch": rel_scratch, "parity_scratch": par_scratch, "rel": load(rel_scratch), "parity": load(par_scratch)}


# ------------------------------------------------------------------ native WALLET-01 ledger on the PIT target


def _obs(at, **extra):
    return ObservabilityEvidence(local_first_seen_time=at, **extra)


def _obs_map(at, **extra):
    return WP._observability_to_mapping(_obs(at, **extra))


def book_bytes(condition, token, price="0.42", depth="10"):
    return WCON.wallet_canonical_json_bytes({"market": condition, "asset_id": token, "asks": [{"price": price, "size": depth}],
                                             "bids": [{"price": price, "size": depth}]})


def _book_records(condition, token, content, at=QUOTE_AT):
    raw = build_raw_evidence_reference(
        source_system="POLYMARKET_CLOB", endpoint="/book", retrieval_method="GET", request_parameters={"token_id": token},
        pit=build_pit_timestamps(local_first_seen_time=at, ingestion_time=at), content_sha256=sha256(content).hexdigest(),
        byte_length=len(content), media_type="application/json", dq_flags=("OK",), replay_fidelity="EXACT",
        raw_snapshot_ref="synthetic:b2-retained-book")
    manifest = build_research_provenance_manifest(
        repo_code_identity="synthetic-b2", information_cutoff=at, input_evidence_reference_ids=(raw.raw_evidence_reference_id,),
        input_content_hashes=(raw.content_sha256,), output_identity="synthetic-b2-book", output_hash=raw.content_sha256)
    return raw, manifest


def build_ledger(base: Path, *, condition=None, token=None, events=None, observation_seen=SEEN_AT, book=None):
    """Native append API only; returns ids the case needs (no second wallet event format)."""
    condition = condition or B1._cond(TARGET)
    token = token or _tok(TARGET, "YES")
    base.mkdir(parents=True, exist_ok=True)
    path = (base / "wallet.sqlite").resolve()
    assert WL.initialize_wallet_evidence_ledger(str(path)).is_valid
    manifest = build_research_provenance_manifest(repo_code_identity="synthetic-b2", information_cutoff="2026-05-30T00:00:00Z",
                                                  output_identity="b2-wallet", output_hash="9" * 64)
    run_key = WCON.derive_ingest_run_key({"wallet": WALLET, "case": "b2"})
    trades = build_raw_evidence_reference(
        source_system="POLYMARKET_DATA_API_V2", endpoint="/v2/trades", retrieval_method="GET/fixture", content_sha256="a" * 64,
        byte_length=10, media_type="application/json", pit=build_pit_timestamps(local_first_seen_time=observation_seen,
                                                                                ingestion_time=observation_seen),
        dq_flags=("OK",), replay_fidelity="FAITHFUL", request_parameters={"user": WALLET, "run": run_key[-8:]})
    page = WCON.build_wallet_feed_page_evidence(
        raw_evidence_reference_id=trades.raw_evidence_reference_id, ingest_run_key=run_key, feed_key="TRADES",
        canonical_request_identity={"user": WALLET}, requested_page_size=100, has_more=False,
        local_first_seen_time=observation_seen, ingestion_time=observation_seen, api_source_parser_version="b2/1",
        dq_flags=("OK",), replay_fidelity="FAITHFUL", source_row_count=10, normalized_event_count=10, observation_count=10)
    events = events or [dict()]
    built = []
    for number, spec in enumerate(events):
        kwargs = dict(identity_strength="API_NATIVE_STRONG", canonical_event_type="TRADE_FILL", canonical_wallet=WALLET,
                      source_system_family="POLYMARKET_DATA_API_V2", side="BUY", price="0.25", notional="10",
                      event_time=EVENT_AT, condition_context="DATA_API_RESPONSE_CONDITION_ID", condition_value=condition,
                      token_context="CLOB_TOKEN_ID", token_value=token, combo_state="FALSE", native_event_id=f"b2-event-{number}")
        kwargs.update(spec)
        built.append(WCON.build_wallet_evidence_event(**kwargs))
    observations = [WCON.build_wallet_event_observation(
        wallet_event_id=e.wallet_event_id, wallet_feed_page_evidence_id=page.wallet_feed_page_evidence_id, ingest_run_key=run_key,
        source_system="POLYMARKET_DATA_API_V2", endpoint="/v2/trades", source_activity_type="TRADE",
        pit=build_pit_timestamps(event_time=e.event_time, local_first_seen_time=observation_seen, ingestion_time=observation_seen),
        dq_flags=("OK",), replay_fidelity="FAITHFUL", raw_evidence_reference_id=trades.raw_evidence_reference_id) for e in built]
    content = book if book is not None else book_bytes(condition, token)
    raw, book_manifest = _book_records(condition, token, content)
    result = WL.append_wallet_evidence_records(str(path), [manifest, trades, page, *built, *observations, raw, book_manifest])
    assert result.is_valid, result.error_codes
    (base / "book-1.json").write_bytes(content)
    return {"path": path, "head": result.snapshot.head_hash, "manifest": manifest, "raw": raw, "book_manifest": book_manifest,
            "condition": condition, "token": token, "base": base}


def cohort_mapping(manifest, *, wallets=(WALLET,)):
    members = tuple(WP.WalletDiscoveryCohortMember(
        canonical_wallet=w, cohort_role="CANDIDATE", discovery_reason="verified-public-cohort",
        discovery_evidence_reference_ids=("evidence:b2-cohort",),
        discovery_provenance_manifest_ids=(manifest.research_provenance_manifest_id,),
        discovery_observability=_obs("2026-05-30T00:00:00Z")) for w in wallets)
    cohort = WP.build_wallet_discovery_cohort_snapshot(
        discovery_cutoff="2026-05-31T00:00:00Z", evaluation_start="2026-05-31T00:00:00Z", evaluation_end="2026-06-30T00:00:00Z",
        discovery_method="CALLER_SUPPLIED_PIT_SET", selection_policy_id="b2-selection", selection_policy_version="1",
        members=members, provenance_manifests=(manifest,))
    return WP.wallet_discovery_cohort_to_mapping(cohort)


def context_mapping(manifest, *, condition=None, token=None, metadata_at=B1.OBSERVED, instrument="STANDARD_BINARY_OUTCOME"):
    context = WP.build_wallet_profile_market_context(
        condition_context="DATA_API_RESPONSE_CONDITION_ID", condition_value=condition or B1._cond(TARGET),
        token_context="CLOB_TOKEN_ID", token_value=token or _tok(TARGET, "YES"), instrument_class=instrument,
        category_label="economics", mechanism_label="binary", horizon_label="quarterly", independence_group_id="b2-cpi",
        metadata_observability=_obs(metadata_at), metadata_dq_flags=("OK",), metadata_replay_fidelity="FAITHFUL",
        research_provenance_manifest_ids=(manifest.research_provenance_manifest_id,))
    return WP.wallet_profile_market_context_to_mapping(context)


def quote_map(ledger, *, registered=True, sign=1, price="0.42", depth="10", token=None, at=QUOTE_AT):
    return {"condition_context": "DATA_API_RESPONSE_CONDITION_ID", "condition_value": ledger["condition"],
            "token_context": "CLOB_TOKEN_ID", "token_value": token or ledger["token"], "price_direction_sign": sign,
            "price": price, "top_level_depth_shares": depth, "observability": _obs_map(at), "dq_flags": ["OK"],
            "replay_fidelity": "EXACT",
            "raw_evidence_reference_id": ledger["raw"].raw_evidence_reference_id if registered else None,
            "research_provenance_manifest_id": ledger["book_manifest"].research_provenance_manifest_id if registered else None,
            "raw_content_member": "book-1.json" if registered else None}


def b2_case(spine_receipt_id, rel_receipt_id, ledger, **override):
    value = {"schema_id": RW.CASE_SCHEMA, "spine_receipt_id": spine_receipt_id, "rel_receipt_id": rel_receipt_id,
             "target_market_id": B1._mid(TARGET), "model_ids": list(SELECTED), "expected_wallet_ledger_head": ledger["head"],
             "target_wallet": WALLET, "wallet_as_of": WALLET_AS_OF, "cohort": cohort_mapping(ledger["manifest"]),
             "market_contexts": [context_mapping(ledger["manifest"])], "identity_observability": None,
             "quote_witnesses": [quote_map(ledger)], "delay_seconds": ["1", "5"], "cost_scenarios": [dict(COST)]}
    value.update(override)
    return value


def build_b2_world(base: Path) -> dict:
    world = B1.build_world(base / "grounding-world", markets=MARKETS)
    rel = run_rel_and_parity(world, base / "rel")
    ledger = build_ledger(base / "wallet")
    return {"world": world, **rel, "ledger": ledger, "binding": RW.bind_target(world["grounding"], B1._mid(TARGET), None)}


def reader(base: Path):
    return lambda member: (base / member).read_bytes() if (base / member).is_file() else b""


@pytest.fixture(scope="module")
def b2(tmp_path_factory):
    return build_b2_world(tmp_path_factory.mktemp("b2_world"))


def _a6(b2, base: Path, name: str, ledger_kw=None, **case_kw):
    led = build_ledger(base / name, **(ledger_kw or {}))
    case = b2_case("b1spine:sha256:" + "0" * 64, b2["rel"]["receipt_id"], led)
    for key, value in case_kw.items():
        case[key] = value(led) if callable(value) else value
    RW.validate_case(case)
    return RW.wallet(b2["binding"], led["path"], case, reader(led["base"]), DECISION)


def _a5(b2, binding=None, rel=None, parity=None, model_ids=SELECTED):
    return RW.relations(binding or b2["binding"], rel or b2["rel"], parity or b2["parity"], list(model_ids))


def _selected(a5):
    return {s["model_id"]: s for s in a5["selected"]}


# ------------------------------------------------------------------ R001


def test_b2_pinned_oracle_and_other_source_dispositions(b2, tmp_path, monkeypatch):
    from src.data_layer.analytical_research import oracle3_upstream_bridge as OB
    vendor = OB.vendor_dir()
    # exact vendored pin, byte-identical blobs; nothing from R3-04/11/19/14 was vendored or copied
    assert OB.UPSTREAM_COMMIT == RW.PINS["R3-03"][1] == RW.PINS["R3-03-FEES"][1]
    assert sorted(p.name for p in vendor.iterdir()) == sorted(OB.VENDOR_PINS)
    assert all(OB.git_blob_sha1((vendor / n).read_bytes()) == pin for n, pin in OB.VENDOR_PINS.items())
    repo = Path(__file__).resolve().parents[3]
    copied = [p for p in (repo / "src").rglob("*.py")
              if p.name in ("settlement.py", "implications.py", "matcher.py") or {"kairos", "synpath"} & set(p.parts)]
    assert copied == []
    # genuine upstream check_constraint + PolymarketSchedule.fee invocations on the shared fixture (spied, not mocked)
    fees, arbitrage = OB.load_upstream()
    calls, fee_calls = [], []
    real_check, real_fee = arbitrage.check_constraint, fees.PolymarketSchedule.fee

    def spy_check(*args, **kwargs):
        calls.append(args[0])
        return real_check(*args, **kwargs)

    def spy_fee(self, *args, **kwargs):
        fee_calls.append(type(self).__name__)
        return real_fee(self, *args, **kwargs)

    def never(*_args):
        raise AssertionError("default fee schedule reached")
    monkeypatch.setattr(arbitrage, "check_constraint", spy_check)
    monkeypatch.setattr(fees.PolymarketSchedule, "fee", spy_fee)
    monkeypatch.setattr(arbitrage, "default_schedule", never)
    assert PAR.run(b2["rel_scratch"], (tmp_path / "spy-parity").resolve())["status"] == "RUN_COMPLETE"
    monkeypatch.undo()
    spied = json.loads((tmp_path / "spy-parity" / "receipt.json").read_text(encoding="utf-8"))
    assert spied["core"]["results"] == b2["parity"]["core"]["results"]  # what the consumer reads is what the calls produced
    assert len(calls) == spied["core"]["check_constraint_invocations"] == 2
    assert fee_calls and set(fee_calls) == {"PolymarketSchedule"}
    a5 = _a5(b2)
    evaluated = sorted(s["model_id"] for s in a5["selected"] if s["oracle3"]["verdict"] == "UPSTREAM_CONDITIONAL_EVALUATED")
    assert evaluated == ["b2-impl", "b2-void"] and a5["denominators"]["check_constraint_invocations"] == 2
    assert a5["upstream"]["commit"] == RW.PINS["R3-03"][1]
    touched = RW.capability_ledger(a5, {"ledger_head": "h"})["touched"]
    assert set(touched) == {"R3-03", "R3-03-FEES", "R3-04", "R3-11", "R3-19", "R3-14"}
    assert touched["R3-03"]["status"] == "ENG_OFFLINE_SHARED_CASE_CONSUMED_BY_A5_NOT_VALUE_VERIFIED"
    assert touched["R3-03-FEES"]["schedules"] == ["polymarket:feeSchedule (unnamed):taker_rate=0.02"]
    for key in ("R3-04", "R3-11", "R3-19"):
        assert touched[key]["status"] == "OPEN" and touched[key]["call"] == "NATIVE_ONLY" and touched[key]["cause"]
    assert touched["R3-14"]["status"] == "OPEN_OWNER_RIGHTS" and touched["R3-14"]["call"] == "BLOCKED_SCHEMA_INSPECTED_ONLY"
    assert all(r["value_verified"] is False and r["owner_disposition"] == "PENDING" for r in touched.values())
    # selected models that never reach the upstream call earn no R3-03 evidence
    abstained = RW.capability_ledger(_a5(b2, model_ids=["b2-reverse", "b2-tie"]), {"ledger_head": "h"})["touched"]
    assert abstained["R3-03"]["status"] == abstained["R3-03-FEES"]["status"] == "NOT_EXERCISED_ON_SHARED_CASE"


# ------------------------------------------------------------------ R002


def test_b2_exact_shared_pit_case_binding(b2, tmp_path):
    from src.data_layer.analytical_research import source_forecast_spine as SP
    binding, target = b2["binding"], b2["binding"]["target"]
    scouted = SP.scout(SP.load_grounding(b2["world"]["grounding"]), B1._mid(TARGET))
    assert target == scouted["target"] and binding["grounding_receipt_id"] == b2["world"]["receipt"]["receipt_id"]
    assert target["condition_id"] == B1._cond(TARGET) and target["token_ids"] == list(B1._tokens(TARGET))
    assert target["rule_sha256"] == binding["rules"][B1._mid(TARGET)] and target["candidate_id"].startswith("alphacandidate:")
    # B1-A lineage is compared by native IDs only
    lineage = {"grounding_receipt_id": binding["grounding_receipt_id"], "as_of": binding["as_of"],
               "alpha_universe_snapshot_id": binding["alpha_universe_snapshot_id"], "a1_target": dict(target)}
    assert RW.bind_target(b2["world"]["grounding"], B1._mid(TARGET), lineage)["target"] == target
    for field in ("candidate_id", "question_sha256", "condition_id"):
        with pytest.raises(RW.RelationWalletStop, match="SPINE_TARGET_MISMATCH"):
            RW.bind_target(b2["world"]["grounding"], B1._mid(TARGET), dict(lineage, a1_target=dict(target, **{field: "x"})))
    with pytest.raises(RW.RelationWalletStop, match="SPINE_GROUNDING_MISMATCH"):
        RW.bind_target(b2["world"]["grounding"], B1._mid(TARGET),
                       dict(lineage, grounding_receipt_id="srcground:sha256:" + "0" * 64))
    # no new candidate creation: a market without a preexisting Alpha candidate, an unknown and a noncanonical one
    for market, code in ((RELATED, "TARGET_CANDIDATE_MISSING"), ("999999", "TARGET_NOT_IN_UNIVERSE"),
                         ("560005", "TARGET_IDENTITY_ABSTAINED")):
        with pytest.raises(RW.RelationWalletStop, match="TARGET_NOT_ADMITTED:" + code):
            RW.bind_target(b2["world"]["grounding"], B1._mid(market), None)
    # REL must point to the SAME grounding receipt and universe, decided at/after as_of
    rel = b2["rel"]
    for key, value, code in (("grounding_receipt_id", "srcground:sha256:" + "1" * 64, "REL_GROUNDING_MISMATCH"),
                             ("alpha_universe_snapshot_id", "alphauniverse:sha256:" + "1" * 64, "REL_UNIVERSE_MISMATCH"),
                             ("decision_time", "2026-06-01T11:00:00Z", "REL_DECISION_BEFORE_AS_OF")):
        forged = copy.deepcopy(rel)
        forged["core"]["inputs"][key] = value
        with pytest.raises(RW.RelationWalletStop, match=code):
            _a5(b2, rel=forged)
    with pytest.raises(RW.RelationWalletStop, match="PARITY_REL_MISMATCH"):
        _a5(b2, rel=dict(rel, receipt_id="relmarket:sha256:" + "2" * 64))
    # wallet contexts bind by exact condition/token to the same PIT universe and the exact PIT metadata clock
    assert _a6(b2, tmp_path, "ok")["context_counts"] == {"considered": 1, "bound": 1, "refused": {}, "target_contexts": 1}
    refusals = {
        "CONTEXT_FOREIGN_TO_PIT_UNIVERSE": dict(market_contexts=lambda lg: [context_mapping(lg["manifest"], condition="0x" + "e" * 64)]),
        "CONTEXT_TOKEN_NOT_IN_MARKET": dict(market_contexts=lambda lg: [context_mapping(lg["manifest"], token=_tok("560002", "YES"))]),
        "CONTEXT_METADATA_CLOCK_MISMATCH": dict(
            market_contexts=lambda lg: [context_mapping(lg["manifest"], metadata_at="2026-06-01T00:00:00Z")]),
        "CONTEXT_OBSERVED_AFTER_WALLET_AS_OF": dict(wallet_as_of="2026-06-01T00:00:00Z"),
        "CONTEXT_NOT_STANDARD_BINARY_NATIVE_IDS": dict(market_contexts=lambda lg: [context_mapping(lg["manifest"], instrument="OTHER")]),
    }
    for code, change in refusals.items():
        result = _a6(b2, tmp_path, code, **change)
        assert result["status"] == "REFUSED" and result["reason"] == "CONTEXT_NOT_BOUND_TO_SHARED_PIT_UNIVERSE", code
        assert result["context_counts"]["refused"] == {code: 1} and result["context_counts"]["considered"] == 1
        assert result["profile"] is None and result["assessment"] is None  # no native builder ran on a foreign case
    # a bound non-target context never stands in for the target
    other = _a6(b2, tmp_path, "other", quote_witnesses=[], market_contexts=lambda lg: [
        context_mapping(lg["manifest"], condition=B1._cond(RELATED), token=_tok(RELATED, "YES"))])
    assert other["status"] == "REFUSED" and other["reason"] == "TARGET_CONTEXT_MISSING"


# ------------------------------------------------------------------ R004


def test_b2_rule_direction_and_settlement_refusals(b2):
    a5 = _a5(b2)
    rows = _selected(a5)
    impl, reverse = rows["b2-impl"], rows["b2-reverse"]
    # direction is preserved: RELATED (>4%) -> TARGET (>3%) proves under the model; the reverse is a counterexample
    assert impl["market_ids"] == [B1._mid(RELATED), B1._mid(TARGET)] and impl["target_position"] == 1
    assert impl["formal"]["status"] == "FORMAL_BOUNDED_PAYOFF_PROOF" and impl["role"] == "ADMITTED"
    assert impl["native_candidate_key"] and "SHARED_RECORDED_EVENT" in impl["native_generators"]
    assert reverse["disposition"] == "COUNTEREXAMPLE" and reverse["formal"]["counterexamples"] and reverse["role"] == "REFUSED"
    assert reverse["oracle3"] == dict(reverse["oracle3"], verdict="ABSTAINED", reason="NO_FORMAL_PROOF")
    # tie / cancel / reschedule / partial without declared payout semantics stay inconclusive, never proven
    for model_id in ("b2-tie", "b2-cancel", "b2-resched", "b2-partial"):
        assert rows[model_id]["disposition"] == "INCONCLUSIVE" and rows[model_id]["role"] == "REFUSED", model_id
        assert rows[model_id]["oracle3"]["verdict"] == "ABSTAINED", model_id
    # a declared VOID payout is modelled explicitly; still only conditional, never real settlement truth
    assert rows["b2-void"]["formal"]["special_states"] and rows["b2-void"]["real_world"]["status"] == "INCONCLUSIVE_RULE_SEMANTICS"
    # a caller rule claim contradicting the hash-bound PIT rule is a native RULE_CONFLICT
    assert rows["b2-rule"]["disposition"] == "RULE_CONFLICT" and rows["b2-rule"]["role"] == "REFUSED"
    assert {r["real_world"]["status"] for r in rows.values()} <= {"INCONCLUSIVE_RULE_SEMANTICS", "RULE_CONFLICT"}
    # a member rule hash that is not the shared grounding's refuses the whole envelope
    forged = copy.deepcopy(b2["binding"])
    forged["rules"][B1._mid(RELATED)] = "0" * 64
    with pytest.raises(RW.RelationWalletStop, match="RULE_IDENTITY_MISMATCH"):
        _a5(b2, binding=forged)
    # R3-04/11/19 stay native-only: a missing upstream source/provider never becomes relation proof
    touched = RW.capability_ledger(a5, {"ledger_head": "h"})["touched"]
    assert touched["R3-11"]["native_counterexamples"] == 1
    assert touched["R3-04"]["status"] == touched["R3-11"]["status"] == touched["R3-19"]["status"] == "OPEN"


# ------------------------------------------------------------------ R006


def _denominators_hold(result):
    for d in result["assessment"]["delay_results"]:
        assert d["considered_event_count"] == d["eligible_event_count"] + sum(n for _, n in d["excluded_reason_counts"])
    return result


def test_b2_wallet_observability_and_gap_refusals(b2, tmp_path):
    base = _denominators_hold(_a6(b2, tmp_path, "base"))
    assert base["status"] == "ADMITTED"
    assert [d["status"] for d in base["assessment"]["delay_results"]] == ["OBSERVABLE_CONDITIONAL", "UNOBSERVABLE"]
    assert base["assessment"]["quote_source_status_counts"] == {"OBSERVED": 1}
    # event time is never availability: an observation first seen after the cutoff is not admissible
    late = _denominators_hold(_a6(b2, tmp_path, "late", ledger_kw={"observation_seen": "2026-06-01T04:00:00Z"}))
    assert late["status"] == "INSUFFICIENT" and late["assessment"]["event_reason_counts"] == {"PIT_NOT_ADMISSIBLE": 1}
    weak = _denominators_hold(_a6(b2, tmp_path, "weak", ledger_kw={
        "events": [dict(identity_strength="WEAK_PARTIAL", native_event_id=None)]}))
    assert weak["status"] == "INSUFFICIENT" and weak["assessment"]["event_reason_counts"] == {"AMBIGUOUS_IDENTITY": 1}
    two = _denominators_hold(_a6(b2, tmp_path, "two", ledger_kw={
        "events": [dict(), dict(native_event_id="b2-event-x", event_time="2026-06-01T02:00:01Z")]}))
    assert two["assessment"]["delay_results"][0]["considered_event_count"] == 2
    outcomes = {
        "noquote": (dict(quote_witnesses=[]), {}, "UNOBSERVABLE"),
        "scenario": (dict(quote_witnesses=lambda lg: [quote_map(lg, registered=False)]), {"SCENARIO_ONLY": 1}, "SCENARIO_ONLY"),
        "wrongtoken": (dict(quote_witnesses=lambda lg: [quote_map(lg, registered=False, token=_tok(TARGET, "NO"))]),
                       {"SCENARIO_ONLY": 1}, "UNOBSERVABLE"),
        "orientation": (dict(quote_witnesses=lambda lg: [quote_map(lg, sign=-1)]), {"OBSERVED": 1}, "UNOBSERVABLE"),
        "nocost": (dict(cost_scenarios=[{k: None for k in COST}]), {"OBSERVED": 1}, "INSUFFICIENT_CONTEXT"),
        "nodepth": (dict(quote_witnesses=lambda lg: [quote_map(lg, depth=None)]), {"OBSERVED": 1}, "INSUFFICIENT_CONTEXT"),
        "latequote": (dict(quote_witnesses=lambda lg: [quote_map(lg, registered=False, at="2026-06-01T05:00:00Z")]),
                      {"PIT_NOT_ADMISSIBLE": 1}, "UNOBSERVABLE"),
    }
    for name, (change, quote_counts, first_status) in outcomes.items():
        result = _denominators_hold(_a6(b2, tmp_path, name, **change))
        assert result["status"] == "INSUFFICIENT", name
        assert result["assessment"]["quote_source_status_counts"] == quote_counts, name
        assert result["assessment"]["delay_results"][0]["status"] == first_status, name
    nocost = _a6(b2, tmp_path, "nocost-reasons", cost_scenarios=[{k: None for k in COST}])
    assert nocost["assessment"]["delay_results"][0]["outcome_reason_counts"] == [["MISSING_COST_ASSUMPTION", 1]]
    # an account outside the frozen cohort is a native refusal, never a silent re-cohort
    assert _a6(b2, tmp_path, "notcohort", target_wallet=OTHER_WALLET)["reason"] == "NATIVE_REFUSED:PROFILE_REFERENCE_INVALID"
    # registered quotes must resolve to ledger records and matching retained bytes
    with pytest.raises(RW.RelationWalletStop, match="QUOTE_REFERENCE_NOT_IN_LEDGER"):
        _a6(b2, tmp_path, "unregistered", quote_witnesses=lambda lg: [dict(quote_map(lg), raw_evidence_reference_id="rawevidence:x")])

    def tampered_bytes(led):
        (led["base"] / "book-1.json").write_bytes(book_bytes(led["condition"], led["token"], price="0.43"))
        return [quote_map(led)]
    tampered = _a6(b2, tmp_path, "bytes", quote_witnesses=tampered_bytes)
    assert (tampered["status"], tampered["reason"]) == ("REFUSED", "NATIVE_REFUSED:COPYABILITY_BINDING_INVALID")
    with pytest.raises(RW.RelationWalletStop, match="QUOTE_CONDITION_NOT_BOUND"):
        _a6(b2, tmp_path, "qcond", quote_witnesses=lambda lg: [dict(quote_map(lg, registered=False), condition_value="0x" + "e" * 64)])
    # drift, corruption and cutoffs after the REL decision stop the whole envelope
    with pytest.raises(RW.RelationWalletStop, match="WALLET_LEDGER_HEAD_MISMATCH"):
        _a6(b2, tmp_path, "head", expected_wallet_ledger_head="0" * 64)
    with pytest.raises(RW.RelationWalletStop, match="WALLET_AS_OF_AFTER_DECISION"):
        _a6(b2, tmp_path, "after", wallet_as_of="2026-06-01T13:00:00Z")
    led = build_ledger(tmp_path / "corrupt")
    data = bytearray(led["path"].read_bytes())
    data[-64:] = b"\x00" * 64
    led["path"].write_bytes(bytes(data))
    with pytest.raises(RW.RelationWalletStop, match="WALLET_LEDGER_NOT_VERIFIED|WALLET_LEDGER_HEAD_MISMATCH"):
        RW.wallet(b2["binding"], led["path"], b2_case("b1spine:sha256:" + "0" * 64, b2["rel"]["receipt_id"], led),
                  reader(led["base"]), DECISION)
    # neither the public address nor a synthetic estimate becomes a person, score, rank or recommendation
    text = json.dumps(base).lower()
    assert WALLET.lower() not in text and not any(w in text for w in ("score", "rank", "recommend", "signal"))


# ------------------------------------------------------------------ R009


def test_b2_strict_inputs_and_authority_denial(b2, tmp_path):
    from tools.alpha import run_relation_wallet_spine as CLI
    led = build_ledger(tmp_path / "strict")
    good = b2_case("b1spine:sha256:" + "0" * 64, b2["rel"]["receipt_id"], led)
    raw = json.dumps(good).encode()
    assert CLI.parse_case(raw) == good  # native 0x+64 condition ids are masked only at their closed field
    q = good["quote_witnesses"][0]
    matrix = [
        ({k: v for k, v in good.items() if k != "model_ids"}, "CASE_FIELDS_INVALID"),                     # missing field
        (dict(good, extra=1), "CASE_FIELDS_INVALID"),                                                       # unknown field
        (dict(good, schema_id="s10-cap-b2-relation-wallet-case-v0"), "CASE_FIELDS_INVALID"),              # wrong schema
        (dict(good, model_ids=None), "MODEL_IDS_INVALID"),                                                  # null
        (dict(good, model_ids=[]), "MODEL_IDS_INVALID"),                                                    # empty
        (dict(good, model_ids=[1]), "MODEL_IDS_INVALID"),                                                   # wrong type
        (dict(good, model_ids=["b2-impl", "b2-impl"]), "MODEL_IDS_DUPLICATE"),                              # duplicate
        (dict(good, model_ids=[f"m{i}" for i in range(201)]), "MODEL_IDS_INVALID"),                         # bound
        (dict(good, spine_receipt_id="b1spine:sha256:XYZ"), "UPSTREAM_RECEIPT_ID_INVALID"),                # invalid id
        (dict(good, rel_receipt_id="oracle3parity:sha256:" + "0" * 64), "UPSTREAM_RECEIPT_ID_INVALID"),    # foreign id
        (dict(good, target_market_id="Market:Polymarket:560001"), "TARGET_MARKET_ID_NONCANONICAL"),        # case variant
        (dict(good, wallet_as_of="2026-06-01T03:00:00+00:00"), "WALLET_AS_OF_INVALID"),                    # clock form
        (dict(good, wallet_as_of="not-a-time"), "WALLET_AS_OF_INVALID"),                                   # malformed clock
        (dict(good, expected_wallet_ledger_head=True), "WALLET_HEAD_INVALID"),                             # bool
        (dict(good, target_wallet="alice"), "TARGET_WALLET_INVALID"),
        (dict(good, market_contexts=[]), "MARKET_CONTEXTS_INVALID"),
        (dict(good, quote_witnesses=[dict(q, raw_content_member=None)]), "QUOTE_REGISTRATION_PARTIAL"),
        (dict(good, quote_witnesses=[dict(q, raw_content_member="../book-1.json")]), "QUOTE_MEMBER_INVALID"),  # traversal
        (dict(good, quote_witnesses=[dict(q, raw_content_member="C:/x/book.json")]), "QUOTE_MEMBER_INVALID"),  # absolute
        (dict(good, quote_witnesses=[dict(q, price_direction_sign=True)]), "QUOTE_WITNESSES_INVALID"),        # bool-as-int
        (dict(good, cost_scenarios=[dict(COST, taker_fee_per_share=0.01)]), "COST_SCENARIOS_INVALID"),        # float
        (dict(good, cohort=dict(good["cohort"], api_key="x")), "FORBIDDEN_FIELD"),                           # secret key
        (dict(good, cohort=dict(good["cohort"], Private_Key="x")), "FORBIDDEN_FIELD"),                       # case variant
        (dict(good, identity_observability={"x": {"pass_phrase": "y", "passphrase": "y"}}), "FORBIDDEN_FIELD"),
        (dict(good, target_wallet="0x" + "a" * 64), "SECRET_MATERIAL_REJECTED"),                            # key-shaped
        (dict(good, model_ids=["sk-" + "a" * 20]), "SECRET_MATERIAL_REJECTED"),                             # token shape
        (dict(good, quote_witnesses=[dict(q, token_value="ghp_" + "a" * 24)]), "SECRET_MATERIAL_REJECTED"),
        (b'{"schema_id": 1, "schema_id": 2}', "CASE_JSON_INVALID"),                                         # duplicate key
        (b'{"x": NaN}', "CASE_JSON_INVALID"),                                                                # nonfinite
        (b"\xff\xfe\x00", "CASE_JSON_INVALID"),                                                              # encoding
        (raw[:-5], "CASE_JSON_INVALID"),                                                                     # truncated
        (b"", "CASE_UNREADABLE"),
        (b" " * (CLI.MAX_CASE_BYTES + 1), "CASE_UNREADABLE"),
    ]
    for case, code in matrix:
        payload = case if isinstance(case, bytes) else json.dumps(case).encode()
        with pytest.raises((RW.RelationWalletStop, SG.GroundingStop), match=code):
            CLI.parse_case(payload)
    # allowed advisory wording is not over-blocked: native price/depth/fee field names and safe values pass
    ok = dict(good, delay_seconds=["1"], quote_witnesses=[dict(q, dq_flags=["OK"])])
    assert CLI.parse_case(json.dumps(ok).encode())["delay_seconds"] == ["1"]
    # closed authority; usage errors never echo arguments; refusals never echo paths or addresses
    assert all(v in (False, 0) for k, v in RW.AUTHORITY.items() if k not in ("advisory_only", "human_review_required"))
    for argv in (["run"], ["verify"], ["frobnicate"], ["run", "--order", "1"], ["verify", "--scratch-dir"]):
        with pytest.raises(SystemExit) as exit_info:
            CLI.main(argv)
        assert exit_info.value.code == 2
    named = tmp_path / ("0x" + "1" * 40)
    out = CLI.run_safe(type("A", (), dict(command="run", spine_scratch=named, alpha_registry=named, rel_scratch=named,
                                          wallet_ledger=named, case=named, scratch_dir=(tmp_path / "s").resolve()))())
    assert out == {"status": "STOPPED", "reason_code": "INPUT_PATH_UNUSABLE:spine"}
    # retained members: regular single-link files under the case parent only
    bundle = (tmp_path / "bundle").resolve()
    bundle.mkdir()
    (bundle / "case.json").write_bytes(raw)
    (bundle / "book-1.json").write_bytes((led["base"] / "book-1.json").read_bytes())
    assert set(CLI.member_hashes(bundle / "case.json", good)) == {"book-1.json"}
    outside = (tmp_path / "outside.json").resolve()
    outside.write_bytes(b"{}")
    import os
    makers = {"big.json": lambda p: p.write_bytes(b"x" * (RW.MAX_MEMBER_BYTES + 1)), "absent.json": lambda p: None,
              "hard.json": lambda p: os.link(outside, p), "link.json": lambda p: p.symlink_to(outside)}
    for name, make in makers.items():
        try:
            make(bundle / name)
        except (OSError, NotImplementedError):
            continue  # no link privilege on this host: the remaining rows still exercise the guard
        with pytest.raises(RW.RelationWalletStop, match="QUOTE_MEMBER_UNSAFE"):
            CLI.member_hashes(bundle / "case.json", dict(good, quote_witnesses=[dict(q, raw_content_member=name)]))
    # SQLite sidecars next to a caller store refuse (no half-committed journal is ever frozen)
    for suffix in CLI.SIDECARS:
        side = Path(str(led["path"]) + suffix)
        side.write_bytes(b"")
        with pytest.raises(RW.RelationWalletStop, match="SQLITE_SIDECAR_PRESENT"):
            CLI._file(led["path"])
        side.unlink()


# ------------------------------------------------------------------ R011


def test_b2_same_case_comparison_and_no_value_claim(b2, tmp_path):
    a5 = _a5(b2)
    par = b2["parity"]["core"]
    # full native denominators retained; the selected/rejected split is explicit and adds up
    d = a5["denominators"]
    assert d["requested"] == len(SELECTED) == d["selected"] + d["rejected"] and d["admitted"] + d["refused"] == d["selected"]
    assert d["parity_counts"] == par["counts"] and d["rel_results_total"] == len(b2["rel"]["core"]["results"])
    assert d["admitted"] == 2 and a5["rejected"] == [{"model_id": "b2-foreign", "reason": "MODEL_NOT_TARGET_RELATED"}]
    # native vs Oracle3 on the same model: genuine parity labels and explicit abstentions retained
    rows = _selected(a5)
    for model_id in ("b2-impl", "b2-void"):
        assert rows[model_id]["oracle3"]["parity"] and set(rows[model_id]["oracle3"]["parity"]) <= {
            "EXACT", "SIGN_AGREES_VALUE_DELTA", "SIGN_MISMATCH", "NATIVE_COST_UNKNOWN"}
        assert rows[model_id]["oracle3"]["assessment"] == {"relation_verified": False, "execution_verified": False,
                                                          "conditional_on_relation": True}
    assert sum(1 for r in rows.values() if r["oracle3"]["verdict"] == "ABSTAINED") == par["counts"]["abstained"] - 1
    # A7 receives the native conditional economics pointer only: never tradable, no fill/size/signal model
    pointer = {p["model_id"]: p for p in a5["a7_pointer"]}
    assert set(pointer) == set(rows)
    impl = pointer["b2-impl"]
    assert impl["native_economic_status"] == "FEE_AND_DEPTH_CONDITIONAL" and impl["tradable"] is False
    assert impl["conditional_only"] is True and impl["executable_edge"] is False
    legs = [leg for b in impl["baskets"] for leg in b["legs"]]
    assert legs and all(set(leg) == {"market_id", "side", "status", "reasons", "fee_exactness", "fee_known", "depth_known",
                                     "venue_snapshot_id"} for leg in legs)
    assert all(b["atomicity"] for b in impl["baskets"])
    assert pointer["b2-reverse"]["native_economic_status"] == "NOT_EVALUATED" and pointer["b2-reverse"]["baskets"] == []
    # a missing venue leg stays unknown on the pointer and the upstream call abstains (no inference)
    sparse = run_rel_and_parity(b2["world"], tmp_path / "sparse", name="sparse")
    assert sparse["parity"]["core"]["counts"] == par["counts"]
    a6 = _a6(b2, tmp_path, "value")
    assert a6["assessment"]["authority"] == {"advisory_only": True, "no_execution_authority": True,
                                             "no_strategy_authority": True, "no_qualification_authority": True}
    core = RW.build_core(case_sha256="0" * 64, input_sha256={}, code_identity="code:sha256:x", lineage={},
                         binding=b2["binding"], a5=a5, a6=a6)
    text = json.dumps(core).lower()
    for forbidden in ('"value_verified": true', '"tradable": true', "order_size", "position_size", "lift", "slippage_model"):
        assert forbidden not in text
    assert core["roles"]["A7_execution_economics"] == "CONDITIONAL_READ_SIDE_POINTER_ONLY_NO_NEW_MODEL"
    assert core["authority"]["tradable"] is False and core["authority"]["copy_recommendation"] is False
