"""S10-R3-ORACLE-UPSTREAM-01: genuine vendored Oracle3 code over cold-verified native REL-01 evidence.

Native REL-01 fixtures (SANITIZED_SYNTHETIC) are reused from test_related_market_alpha. The direct
vectors below are re-derived against the pinned upstream tests/test_arbitrage.py (blob 09a8022)
and tests/test_fees.py (blob ca8b710); those files are references only and are not vendored.
Nothing here proves real settlement, fees, executable edge or Alpha.
"""
from __future__ import annotations

import ast
import copy
from decimal import Decimal
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tomllib
import types

import pytest

from src.data_layer.analytical_research import oracle3_upstream_bridge as OB
from tests.tools.alpha import test_related_market_alpha as RT
from tools.alpha import run_oracle3_upstream_parity as PAR
from tools.alpha import run_related_market_alpha as REL

REPO_ROOT = Path(__file__).resolve().parents[3]
VENDOR = REPO_ROOT / "src" / "data_layer" / "analytical_research" / "oracle3"
# Native REL-01 code identity on main e9099c4: the historical modules must stay byte-identical.
REL_CODE_IDENTITY = "code:sha256:c33424a1ebcfc62188e190978386be1f657d80cfc85c49dd773dea5d79d7c316"
TEST_FEES = {"policy_id": "test-only-oracle3-parity", "kind": "TEST_ONLY_HYPOTHETICAL", "valid_from": "2026-06-01T00:00:00Z",
             "valid_until": "2026-06-02T00:00:00Z", "test_rate": "0.03", "test_exponent": 1}
BASELINE_ABSTENTIONS = {
    "NATIVE_NOT_EVALUATED:MARKET_DUPLICATE_OR_NOT_IN_CORPUS": 2, "NATIVE_NOT_EVALUATED:MODEL_FIELDS_INVALID": 1,
    "NATIVE_NOT_EVALUATED:NOT_NATIVE_CANDIDATE": 6, "NO_FORMAL_PROOF": 20, "NO_USABLE_QUOTE_OR_DEPTH": 10,
    "RELATION_NOT_ADMISSIBLE:EXTERNAL_VENUE_UNVERIFIED": 1, "RELATION_NOT_ADMISSIBLE:MECHANICAL_IDENTITY_NOT_INDEPENDENT": 2,
    "RELATION_NOT_ADMISSIBLE:RULE_CONFLICT": 4}


def run_parity(rel_scratch, scratch, capsys=None):
    code = PAR.main(["run", "--rel-scratch", str(rel_scratch), "--scratch-dir", str(scratch)])
    output = json.loads(capsys.readouterr().out.strip().splitlines()[-1]) if capsys else None
    path = Path(scratch) / "receipt.json"
    return code, output, json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def cases(receipt):
    return {c["model_id"]: c for c in receipt["core"]["results"]}


def tree_hashes(root):
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(root.rglob("*")) if p.is_file()}


def vendor_copy(tmp_path, mutate=None):
    target = tmp_path / "vendor" / "oracle3"
    target.mkdir(parents=True)
    for name in OB.VENDOR_PINS:
        shutil.copyfile(VENDOR / name, target / name)
    if mutate:
        mutate(target)
    return target


@pytest.fixture(scope="module")
def world(tmp_path_factory):
    return RT.make_world(tmp_path_factory.mktemp("o3_inputs"))


@pytest.fixture(scope="module")
def rel(world, tmp_path_factory):
    code, scratch, receipt = RT.run_rel(tmp_path_factory.mktemp("o3_rel"), world, RT.build_request(world))
    assert code == 0
    return scratch, receipt


@pytest.fixture(scope="module")
def parity(rel, tmp_path_factory):
    scratch = (tmp_path_factory.mktemp("o3_par") / "parity").resolve()
    code, _, receipt = run_parity(rel[0], scratch)
    assert code == 0, receipt
    return scratch, receipt


def _variant_rel(world, tmp_path, name, replace, fee_policy=None):
    """A genuine REL-01 run whose venue list swaps listed entries for new frozen bodies."""
    venue = list(world["venue"])
    for index, (slug, side, asks) in replace.items():
        venue[index] = RT._venue_entry(world["put"], 300 + index + 10 * len(name), slug, side, asks, {}, {})
    code, scratch, receipt = RT.run_rel(tmp_path, world, RT.build_request(world, venue=venue, fee_policy=fee_policy), name=name)
    assert code == 0
    return scratch, receipt


# ------------------------------------------------------------------ R001


def _imports(source: bytes) -> set:
    found = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            found.add(node.module)
    return found


def test_oracle3_exact_upstream_source_and_licenses(tmp_path, monkeypatch):
    # Exactly the five pinned upstream files, byte-identical by Git blob, and nothing else vendored.
    assert sorted(p.name for p in VENDOR.iterdir()) == sorted(OB.VENDOR_PINS)
    for name, pin in OB.VENDOR_PINS.items():
        assert OB.git_blob_sha1((VENDOR / name).read_bytes()) == pin
    assert OB.UPSTREAM_COMMIT == "267fb7c48dae7c4ff8922c02a3a223443e51bf0b"
    assert OB.read_verified_vendor().keys() == OB.VENDOR_PINS.keys()
    license_text = (VENDOR / "LICENSE").read_text(encoding="utf-8")
    notice = (VENDOR / "NOTICE").read_text(encoding="utf-8")
    assert "Apache License" in license_text and "Version 2.0, January 2004" in license_text
    for needle in ("Oracle3", "Copyright 2026 Yicheng Yang", "ulab-uiuc/oracle3", "coinjure", "MIT License",
                   "Copyright (c) 2024 Haofei Yu", "Apache License, Version 2.0"):
        assert needle in notice
    # Import closure: stdlib only, plus the one absolute intra-package import the alias resolves.
    stdlib = set(sys.stdlib_module_names) | {"__future__"}
    closure = {"__init__.py": set(), "fees.py": {"__future__", "collections.abc", "dataclasses", "decimal", "typing"},
               "arbitrage.py": {"__future__", "math", "dataclasses", "decimal", "typing", "oracle3.fees"}}
    for name, expected in closure.items():
        source = (VENDOR / name).read_bytes()
        assert _imports(source) == expected
        assert {m.split(".")[0] for m in expected if m != "oracle3.fees"} <= stdlib
        names = {n.id for n in ast.walk(ast.parse(source)) if isinstance(n, ast.Name)}
        assert not names & {"open", "eval", "exec", "__import__", "compile", "socket", "subprocess", "os"}
    fees, _ = OB.load_upstream()
    assert sys.modules["oracle3"].__version__ == OB.UPSTREAM_VERSION == "1.2.2"
    # No package install or dependency: the full upstream project is never referenced.
    project = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")).get("project", {})
    declared = json.dumps([project.get("dependencies", []), project.get("optional-dependencies", {})]).casefold()
    assert not any(dep in declared for dep in ("oracle3", "py-clob-client", "kalshi", "openai-agents", "mcp"))
    # Refusals: missing LICENSE, mutated blob, an added upstream import.
    for mutate, code in ((lambda d: (d / "LICENSE").unlink(), "UPSTREAM_FILE_MISSING"),
                         (lambda d: (d / "NOTICE").write_bytes(b"x" + (VENDOR / "NOTICE").read_bytes()), "UPSTREAM_BLOB_MISMATCH"),
                         (lambda d: (d / "fees.py").write_bytes(b"import socket\n" + (VENDOR / "fees.py").read_bytes()),
                          "UPSTREAM_BLOB_MISMATCH")):
        copy_dir = vendor_copy(tmp_path / code / str(len(list(tmp_path.iterdir()))), mutate)
        monkeypatch.setattr(OB, "vendor_dir", lambda d=copy_dir: d)
        with pytest.raises(OB.Oracle3Stop, match=code):
            OB.load_upstream()
        monkeypatch.undo()


# ------------------------------------------------------------------ R002


def test_oracle3_real_check_constraint_invoked(rel, tmp_path, monkeypatch):
    fees, arbitrage = OB.load_upstream()
    # The genuine upstream functions, compiled from the vendored file under their original module names.
    assert arbitrage.check_constraint.__code__.co_filename == str(VENDOR / "arbitrage.py")
    assert fees.PolymarketSchedule.fee.__code__.co_filename == str(VENDOR / "fees.py")
    assert sys.modules["oracle3.arbitrage"] is arbitrage and sys.modules["oracle3.fees"] is fees
    assert arbitrage.FeeSchedule is fees.FeeSchedule and arbitrage.Quote.__module__ == "oracle3.arbitrage"
    original, calls = arbitrage.check_constraint, []

    def spy(relation, quotes, **kwargs):
        result = original(relation, quotes, **kwargs)
        calls.append((relation, quotes, kwargs, result))
        return result

    def never(*_args):
        raise AssertionError("default fee schedule reached")
    monkeypatch.setattr(arbitrage, "check_constraint", spy)
    monkeypatch.setattr(arbitrage, "default_schedule", never)
    code, _, receipt = run_parity(rel[0], tmp_path / "spy")
    assert code == 0
    core = receipt["core"]
    assert len(calls) == core["check_constraint_invocations"] == core["counts"]["upstream_evaluated"] == 3
    evaluated = {c["model_id"]: c for c in core["results"] if c["verdict"] == "UPSTREAM_CONDITIONAL_EVALUATED"}
    assert sorted(evaluated) == ["v01", "v07", "v08"]
    for (relation, quotes, kwargs, result), model_id in zip(calls, sorted(evaluated)):
        case = evaluated[model_id]
        assert relation == OB.RELATIONS[case["relation"]] and kwargs == {"contracts": 10.0, "maker": False}
        assert [q.market_id for q in quotes] == case["market_ids"]
        assert all(type(q.schedule) is fees.PolymarketSchedule and q.schedule.source.startswith("feeSchedule") for q in quotes)
        assert all(q.schedule.rate == Decimal("0.02") and q.venue == "polymarket" for q in quotes)
        assert [repr(b.net_edge) for b in result.baskets] == [p["upstream"]["net_edge"] for p in case["parity"]]
        assert case["upstream"]["assessment"] == {"relation_verified": False, "execution_verified": False,
                                                  "conditional_on_relation": True}
    # Removing the genuine call removes the evidence: the receipt is not produced by a rewrite.
    monkeypatch.setattr(arbitrage, "check_constraint", original)
    assert core["upstream"]["invoked"][1] == "oracle3.arbitrage.check_constraint"


# ------------------------------------------------------------------ R003


def test_oracle3_verified_native_rel_cold_consumer(rel, parity, world, tmp_path, capsys):
    rel_scratch, rel_receipt = rel
    scratch, receipt = parity
    core = receipt["core"]
    before = tree_hashes(rel_scratch)
    assert REL.code_identity() == REL_CODE_IDENTITY == rel_receipt["core"]["code_identity"] == core["inputs"]["rel_code_identity"]
    assert core["inputs"]["rel_receipt_id"] == rel_receipt["receipt_id"] and core["inputs"]["rel_verification"] == "VERIFIED"
    assert core["inputs"]["file_sha256"] == tree_hashes(rel_scratch)  # every frozen REL byte is bound
    assert tree_hashes(scratch / "inputs" / "rel") == before
    assert REL.verify(scratch / "inputs" / "rel")["status"] == "VERIFIED"  # the frozen copy cold-verifies natively
    assert core["counts"]["cases_total"] == len(rel_receipt["core"]["results"]) == 49
    for case, row in zip(core["results"], rel_receipt["core"]["results"]):
        assert (case["model_id"], case["native_disposition"], case["native_economic_status"]) == (
            row["model_id"], row["disposition"], row["economics"]["status"])
    assert tree_hashes(rel_scratch) == before  # read-only consumer
    # A forged REL receipt, a forged frozen request and a missing receipt all refuse.
    for name, edit, code in (
            ("forged_receipt", lambda d: _rewrite(d / "receipt.json", lambda r: r["core"]["benchmark"].update(cases_total=0)),
             "REL_RECEIPT_NOT_VERIFIED"),
            ("forged_request", lambda d: (d / "inputs" / "request.json").write_bytes(b" " + (d / "inputs" / "request.json").read_bytes()),
             "REL_RECEIPT_NOT_VERIFIED"),
            ("forged_fee", lambda d: _rewrite(d / "receipt.json", lambda r: r["core"]["fee_policy"].update(status="WINDOW_VALID", kind="TEST_ONLY_HYPOTHETICAL")),
             "REL_RECEIPT_NOT_VERIFIED"),
            ("no_receipt", lambda d: (d / "receipt.json").unlink(), "REL_SCRATCH_INVALID")):
        forged = tmp_path / name
        shutil.copytree(rel_scratch, forged)
        edit(forged)
        code_out, output, written = run_parity(forged, tmp_path / f"{name}-out", capsys)
        assert (code_out, output["status"], output["reason_code"], written) == (1, "STOPPED", code, None)


def _rewrite(path, change):
    receipt = json.loads(path.read_text(encoding="utf-8"))
    change(receipt)
    path.write_text(json.dumps(receipt), encoding="utf-8")


# ------------------------------------------------------------------ R004


def test_oracle3_known_fee_conditional_abstentions(world, rel, parity, tmp_path):
    core = parity[1]["core"]
    assert core["counts"]["abstention_reasons"] == BASELINE_ABSTENTIONS
    by_id = cases(parity[1])
    assert by_id["i06"]["reason"] == "RELATION_NOT_ADMISSIBLE:EXTERNAL_VENUE_UNVERIFIED"  # cross-venue claim
    assert by_id["r04"]["reason"] == "RELATION_NOT_ADMISSIBLE:RULE_CONFLICT"  # caller YES-token orientation contradicted
    assert by_id["v06"]["reason"] == "RELATION_NOT_ADMISSIBLE:MECHANICAL_IDENTITY_NOT_INDEPENDENT"
    assert by_id["v12"]["reason"] == "RELATION_NOT_ADMISSIBLE:MECHANICAL_IDENTITY_NOT_INDEPENDENT"
    assert by_id["v05"]["reason"] == "NO_USABLE_QUOTE_OR_DEPTH"  # depth below basket size
    assert by_id["v04"]["reason"] == "NO_USABLE_QUOTE_OR_DEPTH"  # stale book
    assert by_id["v11"]["reason"] == "NO_USABLE_QUOTE_OR_DEPTH"  # neg-risk leg is not executable natively
    for case in core["results"]:
        assert case["tradable"] is False and case["executable_edge"] is False and case["profit_claim"] is False
        assert "CALLER_DECLARED_FORMAL_RELATION" in case["conditional_on"]
    # Fee provenance at decision time: absent, expired, dated-native-bound and unsupported exponent all abstain.
    policies = {
        "none": ({"policy_id": "no-fees", "kind": "NONE", "valid_from": None, "valid_until": None, "test_rate": None,
                  "test_exponent": None}, "FEE_POLICY_ABSENT"),
        "expired": (dict(RT.GAMMA_FEES, valid_from="2026-05-01T00:00:00Z", valid_until="2026-06-01T00:00:00Z"), "FEE_POLICY_EXPIRED"),
        "native": ({"policy_id": "documented-fees-20261028-near-term-02", "kind": "NATIVE_NEAR_TERM_SCREENER",
                    "valid_from": "2026-05-01T00:00:00Z", "valid_until": "2026-11-04T00:00:00Z", "test_rate": None,
                    "test_exponent": None}, "FEE_CONFIG_UNKNOWN"),
        "exponent": (dict(TEST_FEES, test_exponent=2), "FEE_EXPONENT_UNSUPPORTED_BY_UPSTREAM"),
    }
    for name, (policy, reason) in policies.items():
        code, scratch, receipt = RT.run_rel(tmp_path, world, RT.build_request(world, fee_policy=policy), name=name)
        assert code == 0
        cores = run_parity(scratch, tmp_path / f"{name}-out")[2]["core"]
        assert cores["check_constraint_invocations"] == 0 and cores["counts"]["upstream_evaluated"] == 0
        if name == "exponent":
            # Native prices exponent 2 itself; upstream documents exponent 1 only, so the comparison abstains.
            assert cores["counts"]["abstention_reasons"].get(reason) == 3
        else:
            # Native legs are already cost-unknown, so the native quote gate abstains first.
            assert cores["counts"]["abstention_reasons"].get("NO_USABLE_QUOTE_OR_DEPTH", 0) >= 13
    # Explicit-only Gamma fee terms through the genuine upstream parser; never the default or a category rate.
    fees, _ = OB.load_upstream()
    body = json.loads(RT.gamma_body("oh-dem"))
    assert OB._gamma_schedule(fees, json.dumps(body).encode())[0].rate == Decimal("0.02")
    assert OB._gamma_schedule(fees, json.dumps({k: v for k, v in body.items() if k != "feeSchedule"}).encode()) == (
        None, "FEE_SCHEDULE_NOT_EXPLICIT_NO_DEFAULT")
    assert OB._gamma_schedule(fees, json.dumps(dict(body, feeSchedule={"rate": "0.02", "exponent": 2})).encode()) == (
        None, "FEE_SCHEDULE_UNSUPPORTED_BY_UPSTREAM")
    assert OB._gamma_schedule(fees, json.dumps(dict(body, feeSchedule={"rate": None})).encode())[1] == "FEE_SCHEDULE_UNSUPPORTED_BY_UPSTREAM"
    assert OB._gamma_schedule(fees, b"not json")[1] == "FEE_SOURCE_UNREADABLE"
    disabled = OB._gamma_schedule(fees, json.dumps(dict(body, feesEnabled=False)).encode())[0]
    assert disabled.rate == 0 and disabled.source == "feesEnabled=false"
    sources = {"a": json.dumps(body).encode(), "b": json.dumps(dict(body, feeSchedule={"rate": "0.05"})).encode()}
    assert OB._schedules(fees, {"status": "WINDOW_VALID", "kind": "GAMMA_BODY_PER_MARKET"}, {}, {"m": ["a", "b"]},
                         sources.__getitem__) == (None, "FEE_SCHEDULE_CONFLICT")
    # LOCAL_REAL_PIT: no decision-time confirmed rule exists natively, so every case abstains.
    real = RT.make_world((tmp_path / "real").resolve(), corpus_class="LOCAL_REAL_PIT")
    code, scratch, _ = RT.run_rel(tmp_path, real, RT.build_request(real, corpus_class="LOCAL_REAL_PIT"), name="real-rel")
    assert code == 0
    real_core = run_parity(scratch, tmp_path / "real-out")[2]["core"]
    assert real_core["check_constraint_invocations"] == 0
    # 49 cases - 9 not natively evaluated - 20 without a formal proof = 20 that reach the real-rule gate.
    assert real_core["counts"]["abstention_reasons"]["REAL_RULE_CONFIRMATION_ABSENT"] == 20


# ------------------------------------------------------------------ R005


def test_oracle3_upstream_aligned_relation_and_fee_vectors(world, parity, tmp_path):
    fees, arbitrage = OB.load_upstream()
    free = fees.KalshiSchedule(multiplier=Decimal("0"))
    kalshi = fees.KalshiSchedule()

    def q(market_id, venue="kalshi", schedule=free, **prices):
        return arbitrage.Quote(market_id, venue, schedule=schedule, **prices)
    check = arbitrage.check_constraint
    # All five relations, re-derived numbers.
    best = check("implication", [q("A", yes_bid=0.62), q("B", yes_ask=0.58)]).best
    assert best.description == "NO on A + YES on B" and best.cost == pytest.approx(0.96) and best.net_edge == pytest.approx(0.04)
    best = check("exclusivity", [q("A", yes_bid=0.3), q("B", yes_bid=0.3), q("C", yes_bid=0.3), q("D", yes_bid=0.15)]).best
    assert best.payoff_per_contract == 3 and best.gross_edge == pytest.approx(0.05)
    result = check("complement", [q("A", yes_ask=0.4), q("B", yes_ask=0.55, no_ask=0.47)])
    assert [b.description for b in result.baskets] == ["YES on A + YES on B"] and result.missing_quotes == ["A:no_ask"]
    best = check("event_sum", [q("A", yes_ask=0.3), q("B", yes_ask=0.32), q("C", yes_ask=0.33)]).best
    assert best.description == "YES on every outcome" and best.gross_edge == pytest.approx(0.05)
    poly = fees.PolymarketSchedule(rate=Decimal("0.04"))
    best = check("same_event", [q("K", yes_ask=0.60, schedule=kalshi), q("P", venue="polymarket", yes_bid=0.64, schedule=poly)]).best
    assert best.fees == pytest.approx(0.0168 + 0.00922)  # Kalshi 0.07*.6*.4 -> 0.0168; Polymarket .04*.36*.64 -> 0.00922
    # Explicit Kalshi and Polymarket schedules, fee-erases-edge and size scaling.
    taxed = check("implication", [q("A", yes_bid=0.6, schedule=kalshi), q("B", yes_ask=0.55, schedule=kalshi)])
    assert taxed.best.fees == pytest.approx(0.0342) and taxed.best.net_edge == pytest.approx(0.0158)
    erased = check("implication", [q("A", yes_bid=0.51, schedule=kalshi), q("B", yes_ask=0.50, schedule=kalshi)])
    assert erased.violated and not erased.profitable_after_fees
    hundred = check("implication", [q("A", yes_bid=0.6, schedule=kalshi), q("B", yes_ask=0.55, schedule=kalshi)], contracts=100)
    assert hundred.best.gross_edge == pytest.approx(100 * taxed.best.gross_edge)
    assert fees.PolymarketSchedule(rate=Decimal("0.07")).fee(0.30, 100) == Decimal("1.47000")
    assert fees.PolymarketSchedule(rate=Decimal("0.04")).fee(0.001, 0.01) == Decimal("0.00001")  # 5 dp minimum
    assert fees.KalshiSchedule(increment=fees.CENT).fee(0.5, 100) == Decimal("1.75")
    # Duplicate contracts, missing quotes, invalid and non-finite inputs are refused by the upstream code itself.
    with pytest.raises(ValueError, match="duplicate contract"):
        check("complement", [q("A", yes_ask=0.3), q(" A ", venue=" Kalshi ", yes_ask=0.3)])
    for bad in (math.nan, math.inf, -0.01, 1.01):
        with pytest.raises(ValueError):
            check("implication", [q("A"), q("B", yes_ask=bad)])
    with pytest.raises(ValueError):
        check("implication", [q("A"), q("B")], contracts=math.nan)
    with pytest.raises(ValueError):
        fees.PolymarketSchedule(rate=Decimal("0.04")).fee(1.0, 1)
    # Native REL denominators: the synthetic corpus is single-level and rate-aligned, so parity is exact.
    counts = parity[1]["core"]["counts"]
    assert (counts["cases_total"], counts["upstream_evaluated"], counts["abstained"], counts["baskets_compared"]) == (49, 3, 46, 5)
    assert (counts["parity_exact"], counts["parity_sign_agrees_value_delta"], counts["parity_sign_mismatch"]) == (5, 0, 0)
    # Depth: upstream assumes a full fill at the top price; the native sweep is the authority and differences surface.
    deep, _ = _variant_rel(world, tmp_path, "deep", {0: ("oh-dem", "YES", [("0.45", "1"), ("0.6", "50")])})
    deep_core = run_parity(deep, tmp_path / "deep-out")[2]["core"]
    v01 = {p["basket_id"]: p for p in cases({"core": deep_core})["v01"]["parity"]}
    assert v01["YES_BOTH"]["parity"] == "SIGN_MISMATCH" and v01["NO_BOTH"]["parity"] == "EXACT"
    assert Decimal(v01["YES_BOTH"]["delta"]["cost_usd"]) == 0  # same top-of-book quote ...
    assert Decimal(v01["YES_BOTH"]["native"]["conditional_margin_usd"]) < 0 < Decimal(v01["YES_BOTH"]["upstream"]["net_edge"])
    assert cases({"core": deep_core})["v01"]["reason"] == "SIGN_MISMATCH"
    shallow, _ = _variant_rel(world, tmp_path, "shallow", {1: ("oh-rep", "YES", [("0.5", "5"), ("0.51", "50")])}, TEST_FEES)
    shallow_core = run_parity(shallow, tmp_path / "shallow-out")[2]["core"]
    v01 = {p["basket_id"]: p for p in cases({"core": shallow_core})["v01"]["parity"]}
    assert v01["YES_BOTH"]["parity"] == "SIGN_AGREES_VALUE_DELTA" and Decimal(v01["YES_BOTH"]["delta"]["net_edge_usd"]) > 0
    schedule = cases({"core": shallow_core})["v01"]["upstream"]["schedules"]
    assert {s["source"] for s in schedule.values()} == {"TEST_ONLY_HYPOTHETICAL:test-only-oracle3-parity"}
    assert shallow_core["counts"]["parity_sign_agrees_value_delta"] >= 1 and shallow_core["counts"]["real_world_verified"] == 0


# ------------------------------------------------------------------ R006


def test_oracle3_receipt_cold_verify_and_tamper(rel, parity, tmp_path, capsys):
    rel_scratch, _ = rel
    scratch, receipt = parity
    assert PAR.verify(scratch) == {"status": "VERIFIED", "failures": [], "receipt_id": receipt["receipt_id"], "network_attempts": 0}
    assert receipt["receipt_id"] == PAR.finalize(receipt["core"])["receipt_id"]
    assert receipt["receipt_id"].startswith(PAR.RECEIPT_PREFIX)
    upstream = receipt["core"]["upstream"]
    assert upstream["commit"] == OB.UPSTREAM_COMMIT and upstream["git_blob_sha1"] == OB.VENDOR_PINS
    assert receipt["core"]["code_identity"] == PAR.code_identity()
    # Idempotent repeat writes nothing.
    snapshot = tree_hashes(scratch)
    code, output, _ = run_parity(rel_scratch, scratch, capsys)
    assert (code, output["status"], output["receipt_id"]) == (0, "IDEMPOTENT_VERIFIED", receipt["receipt_id"])
    assert tree_hashes(scratch) == snapshot
    # Tampering: core content, receipt id, frozen REL input.
    for name, edit, failure in (
            ("counts", lambda d: _rewrite(d / "receipt.json", lambda r: r["core"]["counts"].update(upstream_evaluated=99)),
             "OUTPUT_MISMATCH:counts"),
            ("id", lambda d: _rewrite(d / "receipt.json", lambda r: r.update(receipt_id=PAR.RECEIPT_PREFIX + "0" * 64)),
             "RECEIPT_ID_MISMATCH"),
            ("calls", lambda d: _rewrite(d / "receipt.json", lambda r: r["core"].update(check_constraint_invocations=0)),
             "OUTPUT_MISMATCH:check_constraint_invocations"),
            ("rel", lambda d: _rewrite(d / "inputs" / "rel" / "receipt.json", lambda r: r["core"].update(request_label="forged")),
             "RECOMPUTE_REFUSED:REL_RECEIPT_NOT_VERIFIED")):
        copy_dir = tmp_path / f"tamper-{name}"
        shutil.copytree(scratch, copy_dir)
        edit(copy_dir)
        result = PAR.verify(copy_dir)
        assert result["status"] == "TAMPER_DETECTED" and failure in result["failures"]
    # Changed REL bytes over an existing scratch refuse without overwrite; a partial scratch refuses.
    changed = tmp_path / "changed-rel"
    shutil.copytree(rel_scratch, changed)
    first = tmp_path / "changed-out"
    assert run_parity(changed, first)[0] == 0
    (changed / "inputs" / "request.source.json").write_bytes(b" " + (changed / "inputs" / "request.source.json").read_bytes())
    before = tree_hashes(first)
    code, output, _ = run_parity(changed, first, capsys)
    assert (code, output["reason_code"]) == (1, "SCRATCH_NOT_EMPTY") and tree_hashes(first) == before
    partial = tmp_path / "partial"
    (partial / "inputs").mkdir(parents=True)
    code, output, _ = run_parity(rel_scratch, partial, capsys)
    assert (code, output["reason_code"]) == (1, "SCRATCH_NOT_EMPTY") and not (partial / "receipt.json").exists()


# ------------------------------------------------------------------ R007


def test_oracle3_security_and_negative_matrix(rel, parity, tmp_path, capsys, monkeypatch):
    rel_scratch, rel_receipt = rel
    # Socket attempts are blocked and refuse the run even when the attempt is swallowed.
    real_assess = OB.assess_rel_core

    def leaky(*args):
        try:
            socket.create_connection(("192.0.2.1", 443), timeout=0.01)
        except Exception:  # noqa: BLE001
            pass
        return real_assess(*args)
    monkeypatch.setattr(OB, "assess_rel_core", leaky)
    code, output, written = run_parity(rel_scratch, tmp_path / "net", capsys)
    assert (code, output["reason_code"], written) == (1, "NETWORK_ATTEMPT_BLOCKED", None)
    monkeypatch.undo()
    # Foreign preloaded modules are never overwritten.
    OB.load_upstream()
    for name in ("oracle3", "oracle3.fees", "oracle3.arbitrage"):
        foreign = types.ModuleType(name)
        monkeypatch.setitem(sys.modules, name, foreign)
        with pytest.raises(OB.Oracle3Stop, match="UPSTREAM_ALIAS_COLLISION"):
            OB.load_upstream()
        assert sys.modules[name] is foreign
        code, output, _ = run_parity(rel_scratch, tmp_path / f"alias-{name}", capsys)
        assert (code, output["reason_code"]) == (1, "UPSTREAM_ALIAS_COLLISION")
        monkeypatch.undo()
    # Import-resolution failure cleans up: arbitrage first cannot find oracle3.fees (no search path).
    monkeypatch.setattr(OB, "MODULE_FILES", (("oracle3", "__init__.py"), ("oracle3.arbitrage", "arbitrage.py"), ("oracle3.fees", "fees.py")))
    for name in ("oracle3", "oracle3.fees", "oracle3.arbitrage"):
        sys.modules.pop(name, None)
    with pytest.raises(OB.Oracle3Stop, match="UPSTREAM_IMPORT_FAILED"):
        OB.load_upstream()
    assert not {"oracle3", "oracle3.fees", "oracle3.arbitrage"} & set(sys.modules)
    monkeypatch.undo()
    OB.load_upstream()
    # Loader path swap: hard-linked or symlinked vendored files are refused even with identical bytes.
    # Link a temporary copy, never the repository file (a link would raise its st_nlink too).
    linked = vendor_copy(tmp_path / "hard", lambda d: os.link(d / "fees.py", tmp_path / "fees-alias.py"))
    monkeypatch.setattr(OB, "vendor_dir", lambda: linked)
    with pytest.raises(OB.Oracle3Stop, match="UPSTREAM_FILE_UNSAFE"):
        OB.load_upstream()
    monkeypatch.undo()
    try:
        sym = vendor_copy(tmp_path / "sym", lambda d: (d / "NOTICE").unlink() or (d / "NOTICE").symlink_to(VENDOR / "NOTICE"))
    except OSError:
        sym = None  # Windows without symlink privilege: the lstat guard is still exercised by the hard link above
    if sym is not None:
        monkeypatch.setattr(OB, "vendor_dir", lambda: sym)
        with pytest.raises(OB.Oracle3Stop, match="UPSTREAM_FILE_UNSAFE"):
            OB.load_upstream()
        monkeypatch.undo()
    # Verified import side effects in a fresh interpreter: three module names, no sys.path/env change, no bytecode.
    probe = (
        "import json, os, sys\n"
        "from src.data_layer.analytical_research import oracle3_upstream_bridge as OB\n"
        "mods, path, env = set(sys.modules), list(sys.path), dict(os.environ)\n"
        "OB.load_upstream()\n"
        "new = sorted(set(sys.modules) - mods)\n"
        "import importlib\n"
        "try:\n    importlib.import_module('oracle3.other'); extra = True\nexcept ImportError:\n    extra = False\n"
        "print(json.dumps({'new': new, 'path': sys.path == path, 'env': dict(os.environ) == env, 'extra': extra}))\n")
    result = subprocess.run([sys.executable, "-B", "-c", probe], cwd=REPO_ROOT, capture_output=True, text=True, timeout=120, check=True)
    facts = json.loads(result.stdout.strip().splitlines()[-1])
    assert {"oracle3", "oracle3.fees", "oracle3.arbitrage"} <= set(facts["new"])
    assert set(facts["new"]) - {"oracle3", "oracle3.fees", "oracle3.arbitrage"} <= set(sys.stdlib_module_names)
    assert facts["path"] and facts["env"] and not facts["extra"]
    assert not (VENDOR / "__pycache__").exists()
    # Without the alias the upstream absolute import cannot resolve (no sys.path shortcut exists).
    plain = subprocess.run([sys.executable, "-B", "-c", "import src.data_layer.analytical_research.oracle3.arbitrage"],
                           cwd=REPO_ROOT, capture_output=True, text=True, timeout=120)
    assert plain.returncode != 0 and "No module named 'oracle3'" in plain.stderr
    # Caller paths: relative, traversal, inside the repository, missing, oversize; scratch inside the repository.
    for value, code in (("relative/rel", "REL_SCRATCH_UNUSABLE"), (str(tmp_path / "x" / ".." / "rel"), "REL_SCRATCH_UNUSABLE"),
                        (str(REPO_ROOT / "docs"), "REL_SCRATCH_UNUSABLE"), (str(tmp_path / "missing"), "REL_SCRATCH_UNUSABLE")):
        assert run_parity(value, tmp_path / f"p-{len(code)}-{abs(hash(value))}", capsys)[1]["reason_code"] == code
    assert run_parity(rel_scratch, REPO_ROOT / "local_data" / "o3", capsys)[1]["reason_code"] == "SCRATCH_INSIDE_REPOSITORY"
    monkeypatch.setattr(PAR, "MAX_REL_FILES", 1)
    assert run_parity(rel_scratch, tmp_path / "big", capsys)[1]["reason_code"] == "REL_SCRATCH_TOO_LARGE"
    monkeypatch.undo()
    # Malformed native evidence reaching the bridge directly: NaN/Inf/garbage price, missing price, duplicate id.
    row = next(r for r in rel_receipt["core"]["results"] if r["model_id"] == "v08")
    request = json.loads((rel_scratch / "inputs" / "request.json").read_bytes())
    sources = {}
    for outcome in rel_receipt["core"]["venue"]["entries"]:
        if outcome["status"] == "BOUND":
            sources.setdefault(outcome["venue_snapshot_id"], set()).add(request["venue"][outcome["index"]]["gamma_file"])

    def assess(mutated):
        return OB.assess_case(mutated, corpus_class="SANITIZED_SYNTHETIC", fee_policy=rel_receipt["core"]["fee_policy"],
                              policy=request["fee_policy"], shares="10", venue_sources=sources,
                              read=lambda rel_path: (rel_scratch / "inputs" / rel_path).read_bytes(), counter=[])

    def with_ask(value):
        mutated = copy.deepcopy(row)
        for leg in mutated["economics"]["baskets"][0]["legs"]:
            leg["best_ask"] = value
        return mutated
    assert assess(copy.deepcopy(row))["verdict"] == "UPSTREAM_CONDITIONAL_EVALUATED"
    for value in ("NaN", "Infinity", "-0.01", "1.5", "0", "garbage"):
        assert assess(with_ask(value))["verdict"] == "UPSTREAM_REFUSED"
    assert assess(with_ask(None))["reason"] == "NO_USABLE_QUOTE_OR_DEPTH"
    duplicate = copy.deepcopy(row)
    duplicate["market_ids"] = [row["market_ids"][0]] * 2
    for leg in duplicate["economics"]["baskets"][0]["legs"]:
        leg["market_id"] = row["market_ids"][0]
    assert assess(duplicate)["verdict"] in ("UPSTREAM_REFUSED", "ABSTAINED")
    unbound = copy.deepcopy(row)
    for leg in unbound["economics"]["baskets"][0]["legs"]:
        leg["venue_snapshot_id"] = "unknown-snapshot"
    assert assess(unbound)["reason"] == "FEE_SOURCE_UNBOUND"
    # Outputs never echo caller paths, headers or secret-shaped text.
    text = json.dumps(parity[1])
    assert str(tmp_path) not in text and str(rel_scratch) not in text and str(REPO_ROOT) not in text
    assert REL.SG.SECRET_RE.search(text) is None


# ------------------------------------------------------------------ R008


def test_oracle3_governance_no_authority_and_36_ids(parity):
    core = parity[1]["core"]
    ids = OB.PROGRAM_CAPABILITY_IDS
    assert len(ids) == len(set(ids)) == 36 and {"R3-03", "R3-03-FEES", "R3-23", "R3-29", "R3-12-SAMPLER"} <= set(ids)
    contract = (REPO_ROOT / "docs" / "oracle3_upstream_reuse_contract.md").read_text(encoding="utf-8")
    assert all(f"`{cid}`" in contract for cid in ids)
    assert core["adoption"]["R3-03"] == core["adoption"]["R3-03-FEES"] == "SELECTIVE_UPSTREAM_CODE_REUSE"
    assert core["adoption"]["value_status"] == "CONDITIONAL_NOT_VALUE_VERIFIED" and core["adoption"]["owner_acceptance"] == "PENDING"
    assert core["adoption"]["program_capability_ids"] == 36 and core["adoption"]["other_capability_ids"] == "UNCHANGED"
    assert core["adoption"]["r3_23_public_get_activation"] == "UNCONSUMED_SEPARATE_OWNER_INSTRUCTION"
    authority = core["authority"]
    assert authority.pop("research_only") is True and authority.pop("network_calls") == 0 and authority.pop("provider_calls") == 0
    assert set(authority.values()) == {False}
    assert core["counts"]["real_world_verified"] == 0 and core["counts"]["tradable"] == 0
    # Bridge + CLI import closure: no execution, paper, live, credential, provider or network surface.
    forbidden = ("src.execution_gateway", "src.paper_trading", "src.live_pilot", "src.research_runtime", "tools.polymarket",
                 "tools.hermes", "requests", "urllib", "http", "socket", "py_clob_client", "official_sdk")
    for path in (Path(OB.__file__), Path(PAR.__file__)):
        source = path.read_bytes()
        assert not any(m.startswith(forbidden) for m in _imports(source))
        attributes = {n.attr for n in ast.walk(ast.parse(source)) if isinstance(n, ast.Attribute)}
        assert not attributes & {"default_schedule", "for_category"}  # the bridge never asks for a fallback fee
    # Historical native identities are unchanged.
    assert REL.code_identity() == REL_CODE_IDENTITY
    status = (REPO_ROOT / "docs" / "status_entries" / "S10-R3-ORACLE-UPSTREAM-01.md").read_text(encoding="utf-8")
    assert "S10-R3-ORACLE-UPSTREAM-01" in status and "Merge: NO" in status
