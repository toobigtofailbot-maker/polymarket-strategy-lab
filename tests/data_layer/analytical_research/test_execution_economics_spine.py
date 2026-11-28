"""S10-CAP-EXEC-ECONOMICS-01 R001-R006/R011: B3 A7 execution-economics diagnostic over the real native producers.

The same SANITIZED_SYNTHETIC B2 world (B1-A SRC-01 grounding, real REL-01, genuine vendored Oracle3 parity, real
WALLET-01 ledger) feeds the pure B3 consumers: the A5/A7 core is built by the native B2 builders, the venue snapshot
by native REL ``_venue_snapshots``, mechanics by native ``assess_execution_feasibility``. The replay rows need pyarrow
and nautilus_trader (pinned deps); hosts whose policy blocks those native libraries skip only the replay rows.
"""
from __future__ import annotations

import copy
import csv
from dataclasses import asdict
import hashlib
import io
import json
from pathlib import Path

import pytest

from src.data_layer.analytical_research import execution_economics_spine as XE
from src.data_layer.analytical_research import relation_wallet_spine as RW
from src.execution_feasibility import evaluator as EV
from src.execution_feasibility.models import build_execution_intent
from tests.data_layer.analytical_research import test_relation_wallet_spine as T
from tests.data_layer.analytical_research import test_source_forecast_spine as B1
from tests.execution_feasibility import test_execution_feasibility as EFT

REPO_ROOT = Path(__file__).resolve().parents[3]
CSV = REPO_ROOT / "docs" / "roadmaps" / "nine_agent_capability_first_20261117" / "03_FULL_36_CAPABILITY_ADOPTION_MATRIX.csv"
CSV_SHA256 = "ecea9023e74f7b97f0c6386ef00d9fc0ec57ef4919f70f3df432d2f5e529dedd"
SEVEN = {"R3-09", "R3-09-BOOK_GAPS", "R3-03-FEES", "R3-15", "R3-16", "R3-17", "R3-26"}
MODEL, BASKET = "b2-impl", "NO_A_YES_B"
DECISION_NS = 1_780_315_200_000_000_000
TARGET_MID = B1._mid(T.TARGET)


# ------------------------------------------------------------------ shared world (also used by the tools tests)


def build_b3_world(base: Path) -> dict:
    """The B2 world + a B2 core assembled by the native B2 builders (no pinned B1-A spine needed)."""
    b2 = T.build_b2_world(base / "b2")
    a5 = RW.relations(b2["binding"], b2["rel"], b2["parity"], list(T.SELECTED))
    a6 = T._a6(b2, base, "a6")
    lineage = {"spine_receipt_id": "b1spine:sha256:" + "0" * 64,
               **{k: b2["binding"][k] for k in ("grounding_receipt_id", "alpha_universe_snapshot_id", "as_of")}}
    core = RW.build_core(case_sha256="0" * 64, input_sha256={}, code_identity="code:sha256:" + "0" * 64,
                         lineage=lineage, binding=b2["binding"], a5=a5, a6=a6)
    return dict(b2, core=core)


def read_json(path: Path):
    return json.loads(Path(path).read_bytes())


def read_member(root: Path, member: str) -> bytes:
    path = Path(root) / member
    return path.read_bytes() if path.is_file() else b""


def venue_entry(rel_dir: Path, market_id: str, side: str) -> dict:
    """The frozen REL request entry REL itself bound for (market, side): never chosen by token name or order."""
    rel, request = read_json(rel_dir / "receipt.json"), read_json(rel_dir / "inputs" / "request.json")
    outcome = [o for o in rel["core"]["venue"]["entries"] if (o["market_id"], o["side"]) == (market_id, side)]
    assert len(outcome) == 1
    return request["venue"][outcome[0]["index"]]


def probe_case(world: dict, *, side: str = "YES", shares: str = "10", price: str = "0.4", order_type: str = "FOK",
               cutoff: int = DECISION_NS, strategy=None, token=None, intent_side: str = "BUY", max_age: int = 60_000_000_000, **override) -> dict:
    entry = venue_entry(world["rel_scratch"], TARGET_MID, side)
    target = world["core"]["shared_case"]["target"]
    strategy = strategy or EFT.SV
    intent = build_execution_intent(
        strategy_version=strategy, gamma_market_id=entry["gamma_market_id"], condition_id=target["condition_id"],
        token_id=token or entry["token_id"], side=intent_side, execution_style="AGGRESSIVE_TAKER", order_type=order_type,
        requested_shares=shares, price_limit=price, post_only=False, information_cutoff_ns=cutoff,
        max_public_data_age_ns=max_age)
    case = {"schema_id": XE.CASE_SCHEMA, "evidence_class": XE.EVIDENCE_CLASS,
            "b2_receipt_id": "b2research:sha256:" + "1" * 64, "model_id": MODEL, "basket_id": BASKET, "leg_side": side,
            "strategy_version": EFT.SV.to_mapping(), "probe_intent": intent.to_mapping(), "replay": None}
    case.update(override)
    return json.loads(json.dumps(case))  # exactly what a strict JSON case file carries


def bind(world: dict, case: dict, core: dict | None = None):
    core = core or world["core"]
    selected = XE.select_leg(core, case)
    return selected, XE.bind_snapshot(world["rel_scratch"], core, selected, read_json, read_member)


def stop_code(fn, *args, **kwargs) -> str:
    with pytest.raises((XE.ExecutionEconomicsStop, RW.RelationWalletStop)) as excinfo:
        fn(*args, **kwargs)
    return str(excinfo.value)


@pytest.fixture(scope="module")
def world(tmp_path_factory):
    return build_b3_world(tmp_path_factory.mktemp("b3_world"))


# ------------------------------------------------------------------ replay fixture (pyarrow + nautilus_trader)


def replay_deps():
    try:
        import pyarrow  # noqa: F401
        import pyarrow.parquet  # noqa: F401
        import src.research_runtime.nautilus_offline  # noqa: F401
    except (ImportError, OSError) as error:  # e.g. a host application-control policy blocking native DLLs
        pytest.skip(f"replay rows need pyarrow + nautilus_trader native libraries: {type(error).__name__}")


def pmxt_rows(condition: str, token: str, *, foreign_token: str | None = None) -> list:
    from tests.research_runtime.nautilus_offline import test_conversion as C
    t0 = DECISION_NS // 1_000_000 - 4_000  # ms: book, delta and trade strictly before the decision clock
    rows = [C.book(t0, t0 + 5, [["0.3900", "50.000000"]], [["0.4000", "50.000000"]]),
            C.price_change(t0 + 1000, t0 + 1006, "0.3800", "10.000000", "BUY"),
            C.trade(t0 + 2000, t0 + 2007, "0.4000", "5.000000", "BUY", "0x" + "d" * 64)]
    for r in rows:
        r["market"], r["asset_id"] = condition.encode("ascii"), token
    if foreign_token:
        rows[1]["asset_id"] = foreign_token
    return rows


def write_parquet(path: Path, rows: list) -> str:
    import pyarrow as pa
    import pyarrow.parquet as pq
    from tests.research_runtime.nautilus_offline import test_conversion as C
    pq.write_table(pa.Table.from_pylist(rows, schema=C.SCHEMA), path)
    return hashlib.sha256(path.read_bytes()).hexdigest()


def cost_model(**changes):
    from src.research_runtime.executable_edge import build_execution_cost_model
    values = dict(model_version="b3-synthetic/1", execution_mode="AGGRESSIVE_TAKER",
                  fee_schedule_reference="gamma-body-fees-20260601", fee_rate_bps=None, latency_ns=0, order_ttl_ns=None,
                  size_grid=("1", "10"), queue_ahead_multiplier="1", markout_horizon_ns=0, net_edge_threshold="0.01",
                  minimum_fill_ratio="1", minimum_capacity_quantity="1", max_data_age_ns=60_000_000_000)
    values.update(changes)
    return build_execution_cost_model(**values)


def wp170_records(reference, *, oos_ordinal=None):
    """Non-OOS WP170 fixture records through the existing native test builders (no registry, no release)."""
    from src.data_layer.analytical_research import experiment_os as EOS
    from tests.data_layer.analytical_research.test_experiment_os_lifecycle_evidence import evidence_input, lifecycle
    from tests.data_layer.analytical_research.test_experiment_os_preregistration import experiment_stack
    records = experiment_stack(cost_model_reference=reference)
    experiment = records[-1]
    role = "SELECTION" if oos_ordinal is None else "OUT_OF_SAMPLE"  # SELECTION: through START_SELECTION only
    receipts = lifecycle(experiment, 3 if oos_ordinal is None else 5)
    evidence = EOS._build_run_evidence_receipt(
        experiment, records[3], records[4], records[7], receipts, (), evidence_input(records[4], role),
        allow_oos=oos_ordinal is not None, prior_oos_release_count=(oos_ordinal or 1) - 1).record
    return experiment, evidence


def replay_case(world: dict, base: Path, *, policy: str = "KNOWN_GAPS", rows=None, model=None, records=None,
                **override) -> tuple:
    from src.data_layer.analytical_research import experiment_os as EOS
    entry = venue_entry(world["rel_scratch"], TARGET_MID, "YES")
    condition = world["core"]["shared_case"]["target"]["condition_id"]
    model = model or cost_model()
    experiment, evidence = records or wp170_records(model.cost_model_id)
    base.mkdir(parents=True, exist_ok=True)
    path = (base / "case.parquet").resolve()
    digest = write_parquet(path, rows if rows is not None else pmxt_rows(condition, entry["token_id"]))
    replay = {"parquet_sha256": digest, "known_gap_policy": policy,
              "context": {"condition_id": condition, "outcome_token_id": entry["token_id"], "outcome_label": "Yes",
                          "description": "Synthetic B3 target outcome", "activation_ns": 0,
                          "expiration_ns": 1_800_000_000_000_000_000, "price_increment": "0.01",
                          "size_increment": "0.000001", "maker_fee": None, "taker_fee": None, "ts_event_ns": 0,
                          "ts_init_ns": 0},
              "experiment": EOS.record_to_mapping(experiment), "evidence": EOS.record_to_mapping(evidence),
              "cost_model": dict(asdict(model), size_grid=list(model.size_grid)),
              "decision_event": {"market_id": TARGET_MID, "asset_id": "token:polymarket:" + entry["token_id"],
                                 "decision_time_ns": DECISION_NS, "side": "BUY", "action": "ENTER", "intended_quantity": "10",
                                 "decision_reference_price": "0.4", "estimated_value": "0.45"}}
    for key, value in override.items():
        replay[key] = value(replay) if callable(value) else value
    return json.loads(json.dumps(replay)), path


def run_replay(world: dict, replay: dict, path: Path) -> dict:
    case = probe_case(world, replay=replay)
    XE.validate_case(case)
    selected, bound = bind(world, case)
    intent, _, _ = XE.assess_point(case, bound["snapshot"], bound["decision_ns"])
    return XE.replay_diagnostic(case["replay"], path, bound, intent, selected["target"]["market_id"])


# ------------------------------------------------------------------ R001


def test_b3_exact_b2_target_and_snapshot(world):
    core, case = world["core"], probe_case(world)
    XE.validate_case(case)
    selected, bound = bind(world, case)
    target = core["shared_case"]["target"]
    assert selected["target"] == target and target["market_id"] == TARGET_MID
    assert selected["model"]["role"] == "ADMITTED" and TARGET_MID in selected["model"]["market_ids"]
    assert (selected["leg"]["market_id"], selected["leg"]["side"]) == (TARGET_MID, "YES")
    snapshot = bound["snapshot"]
    # the native REL binder rebuilt the exact snapshot B2 and the REL BOUND record carry
    assert snapshot.venue_snapshot_id == selected["leg"]["venue_snapshot_id"]
    assert snapshot.condition_id == target["condition_id"]
    assert "token:polymarket:" + snapshot.token_id in target["token_ids"]
    assert bound["decision_ns"] == DECISION_NS and snapshot.acquisition_completed_ns <= DECISION_NS
    assert bound["rel_receipt_id"] == core["a5_relations"]["rel_receipt_id"] == world["rel"]["receipt_id"]
    # the NO leg of the same target is a different native snapshot (never assumed from token order)
    _, no_bound = bind(world, probe_case(world, side="NO", basket_id="YES_A_NO_B")) if any(
        b["basket_id"] == "YES_A_NO_B" for p in core["a7_pointer"] for b in p["baskets"]) else (None, None)
    if no_bound is not None:
        assert no_bound["snapshot"].venue_snapshot_id != snapshot.venue_snapshot_id
        assert no_bound["outcome_label"] == "No"

    def tampered(mutate):
        changed = copy.deepcopy(core)
        mutate(changed)
        return changed

    refused = {m["model_id"] for m in core["a5_relations"]["selected"] if m["role"] != "ADMITTED"}
    unrelated = {r["model_id"] for r in core["a5_relations"]["rejected"]}
    rows = {
        "MODEL_NOT_SELECTED_IN_B2": (dict(case, model_id="b2-absent"), core),
        "BASKET_MISSING": (dict(case, basket_id="YES_A_YES_B"), core),
        "TARGET_LEG_MISSING": (dict(case, leg_side="NO"), core),
        "B2_EVIDENCE_CLASS_INVALID": (case, tampered(lambda c: c.update(evidence_class=XE.EVIDENCE_CLASS))),
        "MODEL_AMBIGUOUS_IN_B2": (case, tampered(lambda c: c["a5_relations"]["selected"].append(
            copy.deepcopy(next(s for s in c["a5_relations"]["selected"] if s["model_id"] == MODEL))))),
        "A7_POINTER_INVALID": (case, tampered(lambda c: next(p for p in c["a7_pointer"] if p["model_id"] == MODEL)
                                              .update(tradable=True))),
        "A7_POINTER_AMBIGUOUS": (case, tampered(lambda c: c["a7_pointer"].append(
            copy.deepcopy(next(p for p in c["a7_pointer"] if p["model_id"] == MODEL))))),
        "MODEL_NOT_TARGET_RELATED": (case, tampered(lambda c: next(s for s in c["a5_relations"]["selected"]
                                                                   if s["model_id"] == MODEL).update(market_ids=["x"]))),
    }
    if refused:
        rows["MODEL_NOT_ADMITTED"] = (dict(case, model_id=sorted(refused)[0]), core)
    if unrelated:
        rows["MODEL_NOT_SELECTED_IN_B2:rejected"] = (dict(case, model_id=sorted(unrelated)[0]), core)
    for code, (row_case, row_core) in rows.items():
        assert stop_code(XE.select_leg, row_core, row_case) == code.split(":")[0], code

    def leg(c):
        return next(g for p in c["a7_pointer"] if p["model_id"] == MODEL for b in p["baskets"] if b["basket_id"] == BASKET
                    for g in b["legs"] if g["market_id"] == TARGET_MID)
    binding_rows = {
        "SNAPSHOT_ID_MISMATCH": tampered(lambda c: leg(c).update(venue_snapshot_id="executionsnapshot:sha256:" + "0" * 64)),
        "TARGET_LEG_UNBOUND": tampered(lambda c: leg(c).update(venue_snapshot_id=None)),
        "REL_RECEIPT_MISMATCH": tampered(lambda c: [c["a5_relations"].update(rel_receipt_id="relmarket:sha256:" + "0" * 64)]
                                         + [p.update(rel_receipt_id="relmarket:sha256:" + "0" * 64) for p in c["a7_pointer"]]),
        "DECISION_CLOCK_MISMATCH": tampered(lambda c: c["a5_relations"].update(decision_time="2026-06-01T12:00:01Z")),
        "GROUNDING_MISMATCH": tampered(lambda c: c["shared_case"].update(grounding_receipt_id="srcground:sha256:" + "0" * 64)),
        "CONDITION_MISMATCH": tampered(lambda c: c["shared_case"]["target"].update(condition_id="0x" + "e" * 64)),
        "TOKEN_MISMATCH": tampered(lambda c: c["shared_case"]["target"].update(token_ids=["token:polymarket:1"])),
    }
    for code, row_core in binding_rows.items():
        with pytest.raises(XE.ExecutionEconomicsStop) as excinfo:
            selected = XE.select_leg(row_core, case)
            XE.bind_snapshot(world["rel_scratch"], row_core, selected, read_json, read_member)
        assert str(excinfo.value) == code, code
    # a member outside the frozen request is never read; a missing retained venue body refuses the binding
    assert stop_code(XE.bind_snapshot, world["rel_scratch"], core, selected, read_json, lambda root, m: b"") in (
        "SNAPSHOT_BINDING_REFUSED", "SNAPSHOT_NOT_BOUND")


# ------------------------------------------------------------------ R002


def test_b3_native_feasibility_and_fee_units(world):
    case = probe_case(world)
    _, bound = bind(world, case)
    snapshot = bound["snapshot"]
    intent, assessment, point = XE.assess_point(case, snapshot, DECISION_NS)
    # the projection is the native assessment: recomputed independently with a direct native call
    direct = EV.assess_execution_feasibility(intent, snapshot, evaluated_at_ns=DECISION_NS)
    assert direct == assessment and point["execution_feasibility_assessment_id"] == direct.execution_feasibility_assessment_id
    native = direct.to_mapping()
    assert point["status"] == native["status"] == "FEASIBLE"
    assert point["dimensions"] == {d: native[d] for d in XE.EFM.DIMENSIONS}
    assert all(point["mechanics"][k] == {"value": native[k], "unit": u} for k, u in XE.UNITS.items())
    m = point["mechanics"]
    # shares versus USDC: 10 shares x 0.40 USDC/share = 4 USDC notional; synthetic Gamma fee 0.02, exponent 1
    assert m["requested_shares"] == {"value": "10", "unit": "SHARES"} and m["visible_fill_shares"]["value"] == "10"
    assert m["best_ask"] == {"value": "0.4", "unit": "USDC_PER_SHARE"} and m["best_bid"]["value"] is None
    assert m["intent_notional_at_price_limit_usd"] == {"value": "4", "unit": "USDC"}
    assert m["theoretical_fee_unrounded_usd"] == {"value": "0.048", "unit": "USDC"}  # 10 * 0.02 * 0.4 * (1 - 0.4)
    assert m["fee_upper_bound_usd"]["unit"] == "USDC" and point["fee_exactness"] == native["fee_exactness"]
    assert point["frozen_unknowns"] == dict.fromkeys(XE.FROZEN_UNKNOWNS)
    assert point["states"]["client_latency_state"] == "UNKNOWN" and point["states"]["adverse_selection_state"] == "UNKNOWN"
    assert point["fill_claimed"] is False and point["profit_claimed"] is False and point["probe"]["fixture_assumption_only"]
    # partial visible depth: FOK above the 50-share ask refuses natively; FAK keeps the native partial-fill limitation
    for order_type, shares in (("FOK", "60"), ("FAK", "60"), ("FOK", "50")):
        c = probe_case(world, shares=shares, order_type=order_type)
        i, a, p = XE.assess_point(c, snapshot, DECISION_NS)
        assert a == EV.assess_execution_feasibility(i, snapshot, evaluated_at_ns=DECISION_NS)
        assert p["status"] == a.status and p["dimensions"]["fill_dimension"] == a.fill_dimension
    assert XE.assess_point(probe_case(world, shares="60"), snapshot, DECISION_NS)[2]["status"] == "NOT_FEASIBLE"
    assert XE.assess_point(probe_case(world, shares="50"), snapshot, DECISION_NS)[2]["status"] == "FEASIBLE"
    # a price limit below the only ask leaves zero price-bound capacity: native refusal, no invented fill
    low = XE.assess_point(probe_case(world, price="0.39"), snapshot, DECISION_NS)[2]
    assert low["status"] == "NOT_FEASIBLE" and low["mechanics"]["price_bound_capacity_shares"]["value"] in ("0", None)


# ------------------------------------------------------------------ R003


def test_b3_unknown_future_and_protocol_refusals(world):
    case = probe_case(world)
    _, bound = bind(world, case)
    snapshot = bound["snapshot"]
    other_sv = EFT.strategy_version(dict(EFT.STRATEGY_SPEC, parameters={"lookback": 6}))
    rows = {
        "PROBE_CUTOFF_NOT_DECISION_CLOCK": probe_case(world, cutoff=DECISION_NS - 1),
        "PROBE_IDENTITY_MISMATCH": probe_case(world, token=EFT.OTHER_TOKEN),
        "PROBE_SIDE_NOT_BUY": probe_case(world, intent_side="SELL"),
        "PROBE_INTENT_INVALID:EXECUTION_RULE_BINDING_INVALID": probe_case(world, strategy=other_sv),
        "STRATEGY_VERSION_INVALID": dict(case, strategy_version=dict(case["strategy_version"], strategy_label="mutated")),
        "PROBE_INTENT_INVALID": dict(case, probe_intent=dict(case["probe_intent"], requested_shares="11")),
    }
    for code, row in rows.items():
        got = stop_code(XE.assess_point, row, snapshot, DECISION_NS)
        assert got == code or (code == "PROBE_INTENT_INVALID" and got.startswith(code)), (code, got)
    # the other outcome's snapshot never substitutes for the bound leg
    no_entry = venue_entry(world["rel_scratch"], TARGET_MID, "NO")
    assert no_entry["token_id"] != snapshot.token_id
    # a clock before acquisition completed is a future-snapshot read: native refusal, never re-timed
    early = snapshot.acquisition_completed_ns - 1
    assert stop_code(XE.assess_point, probe_case(world, cutoff=early), snapshot, early).startswith("POINT_NATIVE_REFUSED:")
    # stale book (2 s old at acquisition) beyond a 1 s public-data age: native UNKNOWN freshness is kept
    stale = XE.assess_point(probe_case(world, max_age=1_000_000_000), snapshot, DECISION_NS)[2]
    assert stale["dimensions"]["freshness_dimension"] == "UNKNOWN" and "BOOK_STALE" in stale["diagnostic_codes"]
    assert stale["status"] != "FEASIBLE"
    # unknown fee (no Gamma feeSchedule) stays native UNKNOWN through the same native builder, never a default zero
    from src.execution_feasibility import public_market as PM
    entry = venue_entry(world["rel_scratch"], TARGET_MID, "YES")
    gamma = json.loads(read_member(world["rel_scratch"] / "inputs", entry["gamma_file"]))
    gamma.pop("feeSchedule")
    clob = read_member(world["rel_scratch"] / "inputs", entry["clob_file"])
    no_fee = PM.build_public_venue_snapshot(
        gamma_market_id=entry["gamma_market_id"], condition_id=snapshot.condition_id, token_id=snapshot.token_id,
        acquisition_started_ns=snapshot.acquisition_started_ns, acquisition_completed_ns=snapshot.acquisition_completed_ns,
        gamma=PM.SourceFetchResult("BODY", json.dumps(gamma).encode()), clob=PM.SourceFetchResult("BODY", clob))
    unknown = XE.assess_point(case, no_fee, DECISION_NS)[2]
    assert unknown["fee_exactness"] == "UNKNOWN" and unknown["mechanics"]["theoretical_fee_unrounded_usd"]["value"] is None
    assert unknown["dimensions"]["fee_dimension"] != "PASS" and unknown["status"] != "FEASIBLE"
    # the strict case: closed keys, closed evidence class, only AS_CAPTURED/KNOWN_GAPS replay policies, no secret keys
    good_replay = {"parquet_sha256": "0" * 64, "known_gap_policy": "KNOWN_GAPS", **{k: {} for k in (
        "context", "experiment", "evidence", "cost_model", "decision_event")}}
    XE.validate_case(dict(case, replay=good_replay))
    case_rows = {
        "CASE_FIELDS_INVALID": [dict(case, extra=1), {k: v for k, v in case.items() if k != "replay"},
                                dict(case, evidence_class="REAL_PROVIDER"), dict(case, schema_id="other"), []],
        "B2_RECEIPT_ID_INVALID": [dict(case, b2_receipt_id="b2research:sha256:XYZ")],
        "MODEL_ID_INVALID": [dict(case, model_id="bad model")],
        "BASKET_ID_INVALID": [dict(case, basket_id="no_a_yes_b")],
        "LEG_SIDE_INVALID": [dict(case, leg_side="Yes"), dict(case, leg_side=True)],
        "NATIVE_MAPPING_INVALID": [dict(case, probe_intent=[])],
        "REPLAY_FIELDS_INVALID": [dict(case, replay={}), dict(case, replay=dict(good_replay, parquet_sha256="A" * 64)),
                                  dict(case, replay=dict(good_replay, context=None))],
        "GAP_POLICY_INVALID": [dict(case, replay=dict(good_replay, known_gap_policy="NONE"))],
        "FORBIDDEN_FIELD": [dict(case, strategy_version=dict(case["strategy_version"], api_key="x"))],
    }
    for code, cases in case_rows.items():
        for row in cases:
            assert stop_code(XE.validate_case, row) == code, code


# ------------------------------------------------------------------ R004


def test_b3_native_pmxt_diagnostic_and_gap(world, tmp_path):
    replay_deps()
    results = {}
    for policy in XE.GAP_POLICIES:
        replay, path = replay_case(world, tmp_path / policy, policy=policy)
        result = run_replay(world, replay, path)
        results[policy] = result
        assert result["status"] == "DIAGNOSTIC_ONLY_NATIVE" and result["origin"] == "SYNTHETIC_PMXT_FORMAT"
        source, window = result["source"], result["window"]
        assert source["parquet_sha256"] == replay["parquet_sha256"] and source["row_count"] == 3
        assert sum(source["input_event_counts"].values()) == 3 and source["known_gap_policy"] == policy
        assert source["provider_history"] is False and source["synpath_invoked"] is False
        assert window["continuity_complete"] is False and window["known_gap_policy"] == policy
        assert window["receive_time_primary"] and window["interpolated"] is False
        assert window["first_receive_time_ns"] <= window["last_receive_time_ns"] < DECISION_NS
        assert result["assessment"]["status"] == "DIAGNOSTIC_ONLY"
        assert "MARKET_DATA_CONTINUITY_INCOMPLETE" in result["assessment"]["diagnostic_codes"]
        assert "FEE_REGIME_UNKNOWN" in result["assessment"]["diagnostic_codes"]
        assert result["assessment"]["wp173_evaluation_eligible"] is False
    assert results["AS_CAPTURED"]["window"]["lineage_id"] != results["KNOWN_GAPS"]["window"]["lineage_id"]
    condition = world["core"]["shared_case"]["target"]["condition_id"]
    token = venue_entry(world["rel_scratch"], TARGET_MID, "YES")["token_id"]
    # altered source bytes change the native lineage; a caller digest alone is never trusted
    changed_rows = pmxt_rows(condition, token)
    changed_rows[2]["size"] = changed_rows[2]["size"] * 2
    replay, path = replay_case(world, tmp_path / "changed", rows=changed_rows)
    assert run_replay(world, replay, path)["window"]["lineage_id"] != results["KNOWN_GAPS"]["window"]["lineage_id"]
    replay, path = replay_case(world, tmp_path / "digest", parquet_sha256="0" * 64)
    assert stop_code(run_replay, world, replay, path) == "REPLAY_SHA256_MISMATCH"
    # a foreign-token row refuses the whole file (no silently ignored row)
    replay, path = replay_case(world, tmp_path / "foreign", rows=pmxt_rows(condition, token, foreign_token=EFT.OTHER_TOKEN))
    assert stop_code(run_replay, world, replay, path) in ("REPLAY_ROWS_REFUSED", "REPLAY_SOURCE_REFUSED")
    # the context must carry the exact selected condition/token/Gamma orientation
    for name, mutate in (("label", lambda r: dict(r["context"], outcome_label="No")),
                         ("token", lambda r: dict(r["context"], outcome_token_id=EFT.OTHER_TOKEN)),
                         ("condition", lambda r: dict(r["context"], condition_id="0x" + "e" * 64))):
        replay, path = replay_case(world, tmp_path / name, context=mutate)
        assert stop_code(run_replay, world, replay, path) == "REPLAY_CONTEXT_IDENTITY_MISMATCH", name
    replay, path = replay_case(world, tmp_path / "ctxkeys", context=lambda r: dict(r["context"], extra=1))
    assert stop_code(run_replay, world, replay, path) == "REPLAY_CONTEXT_FIELDS_INVALID"


# ------------------------------------------------------------------ R005


def test_b3_wp172_cost_and_paper_admission_refusal(world, tmp_path, monkeypatch):
    replay_deps()
    from src.paper_trading import models as PT
    from src.data_layer.analytical_research import experiment_os as EOS
    from src.research_runtime import executable_edge as EE
    replay, path = replay_case(world, tmp_path / "ok")
    result = run_replay(world, replay, path)
    assert result["wp173"] == {"attempted": True, "refusal_code": "WP172_BINDING_INVALID", "binding_created": False}
    assert result["wp170"]["evaluated_role"] == "SELECTION" and result["wp170"]["authoritative_first_look"] is False
    assert result["wp170"]["registry_writes"] == 0 and result["assessment"]["fee_cost_known"] is False
    # direct native recomputation: same assessment id, WP173 refuses that exact diagnostic assessment
    model = cost_model()
    experiment, evidence = (EOS.record_from_mapping(EOS.PreregisteredExperiment, replay["experiment"]),
                            EOS.record_from_mapping(EOS.RunEvidenceReceipt, replay["evidence"]))
    assert result["cost_model_id"] == model.cost_model_id == experiment.cost_model_reference
    assert not EE.authoritative_first_look(experiment, evidence)
    with pytest.raises(PT.PaperTradingError, match="WP172_BINDING_INVALID"):
        PT.build_strategy_binding(EE.deserialize_assessment(EE.serialize_assessment(EE.assess_executable_edge(
            experiment, evidence, EE.build_research_decision_trace(experiment, evidence, (
                EE.ResearchDecisionEvent(**replay["decision_event"]),)), model,
            EE.build_market_truth_window(*_source_and_context(replay, path))))), model,
            strategy_label=XE.PAPER_LABEL, created_time_ns=DECISION_NS)
    bps = cost_model(fee_rate_bps="10")
    passive = cost_model(execution_mode="PASSIVE_MAKER", order_ttl_ns=1_000_000_000)
    oos = wp170_records(model.cost_model_id, oos_ordinal=1)
    rows = {
        "COST_MODEL_FEE_BPS_NOT_PERMITTED": dict(model=bps, records=wp170_records(bps.cost_model_id)),
        "COST_MODEL_MODE_MISMATCH": dict(model=passive, records=wp170_records(passive.cost_model_id)),
        "COST_MODEL_REFERENCE_MISMATCH": dict(records=wp170_records(None)),
        "WP170_OOS_REFUSED": dict(records=oos),
        "COST_MODEL_MISMATCH": dict(cost_model=lambda r: dict(r["cost_model"], cost_model_id="costmodel:sha256:" + "0" * 64)),
        "COST_MODEL_FIELDS_INVALID": dict(cost_model=lambda r: dict(r["cost_model"], extra=1)),
        "WP170_RECORD_INVALID": dict(experiment=lambda r: dict(r["experiment"], trial_number=2)),
        "DECISION_EVENT_BINDING_MISMATCH": dict(decision_event=lambda r: dict(r["decision_event"], intended_quantity="11")),
        "DECISION_EVENT_BINDING_MISMATCH:clock": dict(decision_event=lambda r: dict(r["decision_event"], decision_time_ns=DECISION_NS - 1)),
        "DECISION_EVENT_BINDING_MISMATCH:asset": dict(decision_event=lambda r: dict(r["decision_event"], asset_id="token:polymarket:1")),
        "DECISION_EVENT_FIELDS_INVALID": dict(decision_event=lambda r: dict(r["decision_event"], extra=1)),
    }
    for code, kw in rows.items():
        replay, path = replay_case(world, tmp_path / code.replace(":", "_"), **kw)
        assert stop_code(run_replay, world, replay, path) == code.split(":")[0], code
    # a WP173 that does not refuse is itself a stop: B3 never creates or records a paper binding
    replay, path = replay_case(world, tmp_path / "admit")
    monkeypatch.setattr(PT, "build_strategy_binding", lambda *a, **k: None)
    assert stop_code(run_replay, world, replay, path) == "PAPER_ADMISSION_NOT_REFUSED"


def _source_and_context(replay: dict, path: Path):
    from src.data_layer.analytical_research import pmxt_v2 as PX
    from src.research_runtime.nautilus_offline import BinaryOptionMarketContext, PmxtV2ReplaySource
    source_file = PX.PmxtV2SourceFile(path=str(path), object_name=XE.PMXT_FIXTURE["object_name"],
                                      partition_identity=XE.PMXT_FIXTURE["partition_identity"])
    described = PX.validate_and_describe_pmxt_v2_archive(
        [source_file], quality_tier=XE.PMXT_FIXTURE["quality_tier"], known_gap_policy=replay["known_gap_policy"],
        license_id=XE.PMXT_FIXTURE["license_id"], attribution=XE.PMXT_FIXTURE["attribution"])
    return (PmxtV2ReplaySource(descriptor=described.descriptor, source_files=(source_file,)),
            BinaryOptionMarketContext(**replay["context"]))


# ------------------------------------------------------------------ R006


def test_b3_capability_ledger_no_lane_b_takeover(world):
    raw = CSV.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == CSV_SHA256 or hashlib.sha256(raw.replace(b"\r\n", b"\n")).hexdigest() == CSV_SHA256
    rows = {r["capability_id"]: r for r in csv.DictReader(io.StringIO(raw.decode("utf-8")))}
    assert len(rows) == 36 and SEVEN <= set(rows) and len(set(rows) - SEVEN) == 29
    for cap, (repo, commit, _method, implementation, plan) in XE.PINS.items():
        row = rows[cap]
        assert (row["original_repo"], row["pinned_commit"]) == (repo, commit), cap
        assert (row["historical_implementation_class"], row["capability_status_at_plan"]) == (implementation, plan), cap
    assert set(XE.PINS) == SEVEN and set(XE.LANE_B) == {"R3-15", "R3-16", "R3-17", "R3-26"}
    case = probe_case(world)
    _, bound = bind(world, case)
    point = XE.assess_point(case, bound["snapshot"], DECISION_NS)[2]
    for replay in (XE.not_supplied(), dict(XE.not_supplied(), status="DIAGNOSTIC_ONLY_NATIVE")):
        ledger = XE.capability_ledger(world["core"], point, replay)
        touched = ledger["touched"]
        assert set(touched) == SEVEN and ledger["other_29_capability_ids"] == "UNCHANGED"
        assert all(r["value_verified"] is False and r["owner_disposition"] == "PENDING" for r in touched.values())
        for cap in ("R3-09", "R3-09-BOOK_GAPS"):
            assert touched[cap]["status"] == "PROVIDER_BLOCKED_OPEN" and touched[cap]["call"] == "NOT_INVOKED"
            assert "OWNER_RIGHTS_W07" in touched[cap]["blockers"] and touched[cap]["native_is_not_upstream_invocation"]
        for cap in XE.LANE_B:
            assert touched[cap]["status"] == "NO_ACCEPTED_ARTIFACT_OBSERVED" and touched[cap]["owner"] == "LANE_B_SEPARATE"
            assert touched[cap]["call"] == "NOT_INVOKED" and touched[cap]["native_consumer_evidence"] == "NONE_NO_CALIBRATION_CREDIT"
        fees = touched["R3-03-FEES"]
        # fee evidence is fixture-only and only as strong as the verified B2 row says; currentness never claimed
        assert fees["b2_status"] == world["core"]["capability"]["touched"]["R3-03-FEES"]["status"]
        assert fees["call"] == "NO_NEW_ORACLE3_INVOCATION_B2_COLD_VERIFY_ONLY"
        assert fees["blockers"] == ["CURRENT_VENUE_FEE_SCHEDULE_UNVERIFIED"]
        assert ledger["lane_b"] == "SEPARATELY_OWNED_NO_TAKEOVER" and ledger["w07_synpath_rights"] == "OPEN"
    assert XE.capability_ledger(world["core"], point, XE.not_supplied())["touched"]["R3-09"]["native_consumer_evidence"] == "NOT_EXERCISED"
    # no upstream Synpath / Lane B code is imported or named as a module by the B3 surface
    source = (REPO_ROOT / "src" / "data_layer" / "analytical_research" / "execution_economics_spine.py").read_text(encoding="utf-8")
    assert not any(f"import {m}" in source or f"from {m}" in source for m in ("synpath", "homerun", "polybot", "kalshi"))


# ------------------------------------------------------------------ R011


def test_b3_role_disposition_and_no_value_claim(world):
    case = probe_case(world)
    selected, bound = bind(world, case)
    point = XE.assess_point(case, bound["snapshot"], DECISION_NS)[2]
    role = XE.a7_role(point, XE.not_supplied(), selected)
    assert role["overall"] == "PARTIAL" and role["point_mechanics_status"] == "FEASIBLE"
    assert role["economics_supported"] is False and role["conditional_only"] is True
    assert "REPLAY_NOT_SUPPLIED" in role["reasons"] and "LANE_B_NO_ACCEPTED_ARTIFACT" in role["reasons"]
    assert "B2_ATOMICITY_" + selected["basket"]["atomicity"] in role["reasons"]
    refused_point = XE.assess_point(probe_case(world, shares="60"), bound["snapshot"], DECISION_NS)[2]
    refused = XE.a7_role(refused_point, XE.not_supplied(), selected)
    assert refused["overall"] == "REFUSED" and refused["denominators"]["point_refused"] == 1
    # the failed native dimension is retained, never dropped or re-labelled
    failed = [k for k, v in refused_point["dimensions"].items() if v not in ("PASS", "NOT_APPLICABLE")]
    assert failed and all(f"POINT_DIMENSION_{refused_point['dimensions'][k]}:{k}" in refused["reasons"] for k in failed)
    lineage = XE.b2_lineage("b2research:sha256:" + "1" * 64, world["core"], selected, bound)
    core = XE.build_core(code_identity="code:sha256:" + "0" * 64, input_sha256={}, lineage=lineage, point=point,
                         replay=XE.not_supplied(), role=role, ledger=XE.capability_ledger(world["core"], point, XE.not_supplied()))
    assert set(core) == {"schema_id", "wp_id", "evidence_class", "code_identity", "input_sha256", "b2_lineage",
                         "point_mechanics", "replay_diagnostic", "a7_role", "capability_ledger", "authority", "trace"}
    assert core["evidence_class"] == "SYNTHETIC_TEST_ONLY" and set(core["replay_diagnostic"]) == set(XE.REPLAY_FIELDS)
    assert core["b2_lineage"]["selected"]["tradable"] is False and core["b2_lineage"]["a5"]["rel_receipt_id"] == bound["rel_receipt_id"]
    authority = core["authority"]
    assert authority["human_review_required"] and authority["advisory_only"] and authority["synthetic_test_only"]
    assert not any(v for k, v in authority.items() if k not in ("human_review_required", "advisory_only", "synthetic_test_only"))
    text = json.dumps(core).lower()
    for forbidden in ('"tradable": true', '"executable_edge": true', '"value_verified": true', "economics_supported\": true",
                      "order_size", "position_size", "recommend", "net_result", "gross_research_result", "signal"):
        assert forbidden not in text, forbidden
    receipt = XE.finalize(core)
    assert receipt["receipt_id"] == XE.RECEIPT_PREFIX + hashlib.sha256(XE.SG.canonical_bytes(core)).hexdigest()
