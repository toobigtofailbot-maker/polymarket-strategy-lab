"""S10-ALPHA-03A finite discovery -> offline decision -> research-paper proof (R001-R007).

SYNTHETIC_ONLY: every store is a native store built from merged native fixtures in pytest
scratch; Stage B is the offline injected backend over the recorded tool surface, and the
strategy manager is a FakeHermesBackend. No provider, OAuth, market or account access.
"""
import ast
import hashlib
import inspect
import json
from pathlib import Path
import socket

import pytest

import tools.alpha.run_discovery_learning_proof as proof
from src.paper_trading.models import build_research_strategy_binding
from src.research_runtime import autonomous_opportunity_cycle as cycle
from src.research_runtime.hermes_controlled_runtime import autonomous_feedback as fb
from src.research_runtime.hermes_controlled_runtime import strategy_manager as sm
from src.research_runtime.hermes_controlled_runtime import tool_free_stage_b as tf
from tests.data_layer.analytical_research import test_alpha_discovery as discovery_fixtures
from tests.exploratory_gate_c import test_exploratory_gate_c as native
from tests.research_runtime.hermes_controlled_runtime.test_autonomous_feedback import (
    CUTOFF, candidate_of, paper_store,
)
from tests.research_runtime.hermes_controlled_runtime.test_tool_free_stage_b import RECORDED_REPORT
from tests.research_runtime.test_autonomous_opportunity_cycle import MODEL, world

ROOT = Path(__file__).resolve().parents[3]
TOOL = ROOT / "tools" / "alpha" / "run_discovery_learning_proof.py"
TRADED, UNMATCHED, CROWDED = native.GAMMA_ID, "900001", "900002"


def _pit_records(gamma, condition, tokens):
    meta = {"market_status": "open", "outcome_labels": ["No", "Yes"], "question_text": f"Question {gamma}",
            "token_ids": list(tokens), "condition_id": condition, "category": "test",
            "resolution_date": "2026-12-01T00:00:00Z"}
    built, _ = discovery_fixtures._pit_built(
        "PIT-C01-VALID-MARKET-METADATA", platform_id="platform:polymarket", event_id=f"event:polymarket:{gamma}",
        market_id=f"market:polymarket:{gamma}", source_id="source:polymarket:gamma-markets",
        source_assertion_id=f"assertion:alpha03a:meta:{gamma}", canonical_payload=meta)
    records = [built]
    for index, token in enumerate(tokens):
        book, _ = discovery_fixtures._pit_built(
            "PIT-C02-VALID-ORDER-BOOK-MISSING-EVENT-TIME", platform_id="platform:polymarket",
            event_id=f"event:polymarket:{gamma}", market_id=f"market:polymarket:{gamma}", token_id=token,
            source_id="source:polymarket:clob-book", source_assertion_id=f"assertion:alpha03a:book:{gamma}:{index}",
            canonical_payload={"bids": [{"price": "0.45", "size": "10"}], "asks": [{"price": "0.55", "size": "12"}],
                               "tick_size": "0.01", "minimum_order_size": "1", "last_trade_price": "0.5"})
        records.append(book)
    return records


def _binding_inputs(binding):
    names = inspect.signature(build_research_strategy_binding).parameters
    return {name: list(v) if type(v := getattr(binding, name)) is tuple else v for name in names}


def build_case(root, *, traded_tokens=None, paper="own", hermes=True, occurrences=None, discovery=None,
               markets=True, **paper_changes):
    """Native world + PIT store + optional research-paper session -> (case path, world, args, proposal)."""
    root.mkdir(parents=True)
    w, args, proposal, _ = world(root / "world", hermes=hermes)
    tokens = traded_tokens or [f"token:polymarket:{native.TOKEN}", f"token:polymarket:{native.OTHER_TOKEN}"]
    records = []
    if markets:
        records = (_pit_records(TRADED, native.COND, tokens)
                   + _pit_records(UNMATCHED, "0x" + "cd" * 32, ["token:polymarket:111", "token:polymarket:222"])
                   + _pit_records(CROWDED, "0x" + "ef" * 32, ["token:polymarket:333", "token:polymarket:444"]))
    pit = discovery_fixtures._pit_store(root, records)
    abstain = {key: proposal[key] for key in cycle._CLOCK_KEYS}
    if occurrences is None:
        occurrences = [dict(label="trade", issued_at_ns=native.T0, completed_at_ns=native.T0 + 1000, choice=proposal),
                       dict(label="no-trade", issued_at_ns=native.T0 + 10, completed_at_ns=native.T0 + 1000,
                            choice=dict(abstain, action="NO_TRADE", produced_at_ns=native.T0 + 10))]
    else:
        occurrences = occurrences(proposal, abstain)
    paper_section, paper_path = None, None
    if paper is not None:
        version = w.version if paper == "own" else w.other_version
        paper_path = root / "paper.sqlite3"
        binding = paper_store(paper_path, candidate_of(version), **({"orders": False} if paper == "empty" else {}))
        draft = native._draft("placeholder", native.judgment())
        draft.pop("request_id")
        paper_section = dict(binding=_binding_inputs(binding), strategy_version_id=version.strategy_version_id,
                             information_cutoff=CUTOFF, decision_time_ns=native.T0, provider_label="example-provider",
                             model_label="example-model", manager_clock_utc="2026-10-01T12:00:00Z",
                             manager_draft=draft, manager_usage=json.loads(native._usage()))
        paper_section.update(paper_changes)
    policy = discovery_fixtures._policy(metadata_freshness_seconds=120, order_book_freshness_seconds=120,
                                        resolution_rule_freshness_seconds=120, queue_capacity=2)
    case = dict(
        schema_id=proof.CASE_SCHEMA, case_label="alpha03a-fixture", proof_level="SYNTHETIC_ONLY",
        sources=dict(pit_store=str(pit), alpha_registry=str(args["alpha_registry_path"]),
                     lifecycle_store=str(args["lifecycle_store_path"]),
                     hermes_manager_store=str(args["hermes_manager_store_path"]),
                     paper_store=str(paper_path) if paper_path else None),
        discovery=dict(policy={k: v for k, v in discovery_fixtures.AD.alpha_discovery_record_to_mapping(policy).items()
                               if k != "alpha_discovery_policy_id"},
                       as_of="2026-01-01T00:00:30Z", prior_as_of=None, analysis_temporal_mode="CURRENT_BUILD_ANALYSIS",
                       alpha_memory_temporal_posture="CURRENT_REGISTRY_BUILD_TIME_ONLY"),
        decision=dict(surface_report=RECORDED_REPORT, model_label=MODEL, information_cutoff_ns=native.T0,
                      evaluated_at_ns=native.AT, deadline_ns=args["deadline_ns"],
                      venue_snapshots=[dict(gamma_market_id=native.GAMMA_ID, condition_id=native.COND,
                                            token_id=native.TOKEN, acquisition_started_ns=native.T0 - 10_000_000,
                                            acquisition_completed_ns=native.T0, gamma_document=native.gamma_doc(),
                                            clob_document=native.book_doc())],
                      occurrences=occurrences),
        paper=paper_section)
    case["discovery"].update(discovery or {})
    path = root / "case.json"
    path.write_text(json.dumps(case), encoding="utf-8")
    return path, w, args, proposal


def prepared_run(tmp_path, name="case", **kwargs):
    case, w, args, proposal = build_case(tmp_path / name, **kwargs)
    scratch = tmp_path / f"{name}-scratch"
    assert proof.prepare(case, scratch)["status"] == "PREPARED"
    return proof.run(scratch), scratch, w, args, proposal


def source_digests(case_path):
    sources = json.loads(Path(case_path).read_text(encoding="utf-8"))["sources"]
    return {role: hashlib.sha256(Path(p).read_bytes()).hexdigest() for role, p in sources.items() if p}


def test_observed_universe_scope_and_complete_queue(tmp_path):
    manifest, scratch, _, _, _ = prepared_run(tmp_path)
    found = manifest["discovery"]
    assert (found["coverage_scope"], found["external_universe_completeness"]) == ("BOUNDED_OBSERVED_UNIVERSE", "UNPROVEN")
    assert found["observed_market_count"] == 3 and sum(found["partition"].values()) == 3
    assert found["partition"]["skipped_capacity"] == 1  # capacity skips stay counted, never dropped
    rows = {row["market_id"]: row for row in manifest["menu"]["market_rows"]}
    assert sorted(rows) == sorted(f"market:polymarket:{g}" for g in (TRADED, UNMATCHED, CROWDED))
    assert rows.pop(f"market:polymarket:{TRADED}")["menu_status"] == "CANDIDATES_EVALUATED"
    # Of the two unmatched markets the native seeded audit lane takes one; the other is a
    # counted capacity skip. Neither is guessed into a strategy.
    assert sorted((r["menu_status"], r["final_disposition"]) for r in rows.values()) == [
        ("NOT_SELECTED", "SKIPPED_CAPACITY"), ("RESEARCH_NEEDED", "AUDIT")]
    assert manifest["authority"]["external_universe_completeness_claimed"] is False
    # Historical replay with unproven Alpha memory: native UNKNOWN memory, so no candidate is
    # matched, every selected row needs research and no decision is attempted.
    historical, _, _, _, _ = prepared_run(tmp_path, "historical", discovery=dict(
        analysis_temporal_mode="HISTORICAL_REPLAY", alpha_memory_temporal_posture="HISTORICAL_AVAILABILITY_UNPROVEN"))
    assert historical["discovery"]["alpha_registry_head"] is None
    assert historical["menu"]["status"] == "NO_ELIGIBLE_STRATEGY" and historical["menu"]["members"] == []
    assert {r["menu_status"] for r in historical["menu"]["market_rows"]} == {"RESEARCH_NEEDED", "NOT_SELECTED"}
    assert historical["denominators"]["attempted"] == 0 and historical["denominators"]["not_attempted"] == 2
    assert historical["conclusion"] == "PLUMBING_ONLY"
    assert proof.verify(scratch)["status"] == "VERIFIED"


def test_canonical_menu_requires_exact_verified_lineage(tmp_path, monkeypatch):
    manifest, _, w, args, _ = prepared_run(tmp_path)
    # Derived only from native records: exactly AUTO-01's own validated fixture menu.
    assert manifest["menu"]["members"] == args["candidate_menu"]
    assert manifest["menu"]["menu_sha256"] == cycle._digest(args["candidate_menu"])
    assert manifest["menu"]["research_needed_count"] == 1 and manifest["menu"]["exclusions"] == []
    # A market whose observed tokens the candidate does not name is never guessed into the menu.
    unlinked, _, _, _, _ = prepared_run(tmp_path, "unlinked", traded_tokens=["token:polymarket:7", "token:polymarket:8"])
    assert unlinked["menu"]["status"] == "NO_ELIGIBLE_STRATEGY"
    assert {e["status"] for e in unlinked["menu"]["exclusions"]} == {"TOKEN_LINK_UNVERIFIED"}
    assert unlinked["denominators"]["attempted"] == 0
    # No Hermes assessment: excluded with a typed reason, not offered.
    unassessed, _, _, _, _ = prepared_run(tmp_path, "unassessed", hermes=False)
    assert {e["status"] for e in unassessed["menu"]["exclusions"]} == {"NO_HERMES_ASSESSMENT"}
    # Over capacity: the overflow member stays counted, never silently truncated.
    monkeypatch.setattr(proof, "MENU_LIMIT", 1)
    overflow, _, _, _, _ = prepared_run(tmp_path, "overflow")
    assert len(overflow["menu"]["members"]) == 1 and overflow["menu"]["overflow_count"] == 1
    assert overflow["menu"]["members"][0] in args["candidate_menu"]


def test_decision_attempt_denominators_crash_replay_and_no_trade(tmp_path, monkeypatch):
    def three(proposal, abstain):
        return [dict(label="pause", issued_at_ns=native.T0, completed_at_ns=native.T0 + 1000,
                     choice=dict(abstain, action="PAUSE")),
                dict(label="crash", issued_at_ns=native.T0 + 10, completed_at_ns=native.T0 + 1000,
                     choice=dict(abstain, action="NO_TRADE", produced_at_ns=native.T0 + 10)),
                dict(label="reassess", issued_at_ns=native.T0 + 20, completed_at_ns=native.T0 + 1000,
                     choice=dict(abstain, action="REASSESS", produced_at_ns=native.T0 + 20))]
    case, _, _, _ = build_case(tmp_path / "crash", occurrences=three, paper=None)
    scratch = tmp_path / "crash-scratch"
    proof.prepare(case, scratch)
    dispatched = []
    original_dispatch = tf.OfflineStageBBackend._dispatch

    def counted(self, *a, **k):
        dispatched.append(1)
        return original_dispatch(self, *a, **k)
    monkeypatch.setattr(tf.OfflineStageBBackend, "_dispatch", counted)
    real_cycle, calls = fb.run_one_cycle, []

    def crash_second(**kwargs):
        calls.append(1)
        if len(calls) == 2:
            assert (scratch / "ledger" / "occ-2.started.json").is_file()  # STARTED persisted before work
            raise KeyboardInterrupt
        return real_cycle(**kwargs)
    monkeypatch.setattr(fb, "run_one_cycle", crash_second)
    with pytest.raises(KeyboardInterrupt):
        proof.run(scratch)
    assert not (scratch / "manifest.json").exists() and not (scratch / "ledger" / "occ-2.terminal.json").exists()
    monkeypatch.setattr(fb, "run_one_cycle", real_cycle)
    manifest = proof.run(scratch)
    rows = manifest["occurrences"]
    assert [r["terminal_class"] for r in rows] == ["ABSTAINED_PAUSE", "INTERRUPTED_OR_UNKNOWN", "ABSTAINED_REASSESS"]
    assert manifest["denominators"] == dict(
        attempted=3, completed=2, interrupted_or_unknown=1, not_attempted=0,
        by_terminal_class={"ABSTAINED_PAUSE": 1, "ABSTAINED_REASSESS": 1, "INTERRUPTED_OR_UNKNOWN": 1},
        feedback_linked=0, feedback_not_applicable=0)
    assert len(dispatched) == 2  # the interrupted occurrence is never redispatched
    assert {r["feedback_class"] for r in rows} == {"NO_PAPER_SESSION", "NO_TERMINAL_DECISION"}
    # Replay of a finished proof and cold verification: zero fresh attempts.
    replay = proof.run(scratch)
    assert replay["replay"] is True and replay["status"] == "VERIFIED" and replay["fresh_attempts"] == 0
    assert len(dispatched) == 2
    # The same immutable choice on two explicit occurrences is two attempts, not one.
    def twice(proposal, abstain):
        choice = dict(abstain, action="NO_TRADE")
        return [dict(label=label, issued_at_ns=native.T0, completed_at_ns=native.T0 + 1000, choice=choice)
                for label in ("first", "second")]
    same, _, _, _, _ = prepared_run(tmp_path, "same", occurrences=twice, paper=None)
    assert same["denominators"]["attempted"] == 2 == same["denominators"]["by_terminal_class"]["ABSTAINED_NO_TRADE"]
    assert len({r["occurrence_id"] for r in same["occurrences"]}) == 2 and len(dispatched) == 4


def test_paper_snapshot_exact_binding_and_missingness(tmp_path):
    manifest, scratch, w, _, _ = prepared_run(tmp_path)
    paper = manifest["paper"]
    case = json.loads((tmp_path / "case" / "case.json").read_text(encoding="utf-8"))
    assert paper["status"] == "RESEARCH_PAPER_OBSERVED" and paper["evidence_class"] == "RESEARCH_PAPER_SIMULATED"
    assert paper["binding_id"] == build_research_strategy_binding(**{
        k: tuple(v) if type(v) is list else v for k, v in case["paper"]["binding"].items()}).binding_id
    assert paper["candidate_id"] == candidate_of(w.version)
    assert (paper["order_count"], paper["fill_count"], paper["zero_fill"]) == (1, 1, False) and paper["fee_total"] != "0"
    assert paper["event_head"] and paper["state_hash"] and paper["event_sequence"] >= 1
    assert (paper["pnl_basis"], paper["window_delta"]) == ("CUMULATIVE_SESSION", "NOT_COMPUTED_SINGLE_SNAPSHOT")
    assert paper["real_venue"] is False and paper["qualification_claim"] is False
    assert paper["unrealized_paper_pnl"] is not None  # missing marks would be UNKNOWN_MISSING_MARKS, never zero
    # A zero-fill session is reported as zero fills, not as a missing session.
    empty, _, _, _, _ = prepared_run(tmp_path, "empty", paper="empty")
    assert empty["paper"]["zero_fill"] is True and empty["paper"]["order_count"] == 0
    # No research-paper session: unavailable, never a fabricated outcome.
    absent, _, _, _, _ = prepared_run(tmp_path, "absent", paper=None)
    assert absent["paper"] == dict(status="UNAVAILABLE", reason="NO_RESEARCH_PAPER_SESSION")
    assert {r["feedback_class"] for r in absent["occurrences"]} == {"NO_PAPER_SESSION"}
    assert absent["conclusion"] == "PLUMBING_ONLY"
    assert hashlib.sha256((scratch / "inputs" / "paper_store.sqlite3").read_bytes()).hexdigest() == \
        manifest["source_refs"]["paper_store"]["sha256"]


def test_feedback_identity_and_time_no_causality(tmp_path):
    manifest, scratch, w, args, _ = prepared_run(tmp_path)
    trade, no_trade = manifest["occurrences"]
    assert trade["terminal_class"] == "COMPLETED_PREVIEW" and trade["feedback_class"] == "DECISION_LINKED_NONCAUSAL"
    assert (trade["linked_candidate_id"], trade["linked_strategy_version_id"]) == (
        args["candidate_menu"][0]["candidate_id"], w.version.strategy_version_id)
    assert no_trade["terminal_class"] == "ABSTAINED_NO_TRADE" and no_trade["feedback_class"] == "NOT_APPLICABLE_FEEDBACK"
    assert no_trade["assessment_id"] is None and no_trade["paper_snapshot_id"] is None
    assert manifest["conclusion"] == "VERIFIED_OUTCOME_FEEDBACK_OBSERVED"
    assert manifest["authority"]["causal_claim"] is False and manifest["authority"]["alpha_claim"] is False
    store = sm.load_hermes_strategy_manager_store(scratch / "work" / "hermes_manager_store.sqlite3")
    updates = [r for r in store.run_records if r.trigger == "PERFORMANCE_UPDATE"]
    assert [r.trigger_ref for r in updates] == [trade["paper_snapshot_id"]]
    assert manifest["manager_performance_updates"] == 1  # every manager write is visible in the record
    # The source manager store is untouched: feedback lands only in the scratch work copy.
    original = sm.load_hermes_strategy_manager_store(args["hermes_manager_store_path"])
    assert not [r for r in original.run_records if r.trigger == "PERFORMANCE_UPDATE"]
    # A disjoint paper session (other candidate/strategy) never earns decision credit.
    other, _, _, _, _ = prepared_run(tmp_path, "other", paper="other")
    assert other["occurrences"][0]["feedback_class"] == "REJECTED_FEEDBACK_LINEAGE_MISMATCH"
    assert other["conclusion"] == "PLUMBING_ONLY"
    # Time: a cutoff that does not advance past the prior assessment, or that precedes the
    # paper evidence, is refused natively before the manager is called.
    for name, cutoff, code in (("stale", native.HERMES_CUTOFF, "CUTOFF_NOT_ADVANCED"),
                               ("lookahead", "1970-01-01T00:00:00Z", "PAPER_EVIDENCE_AFTER_CUTOFF")):
        late, _, _, _, _ = prepared_run(tmp_path, name, information_cutoff=cutoff)
        assert late["occurrences"][0]["feedback_class"] == "REJECTED_" + code, name
        assert late["conclusion"] == "PLUMBING_ONLY"
    # Discovery observed after the decision cutoff would be lookahead: blocked.
    future, _, _, _, _ = prepared_run(tmp_path, "future", discovery=dict(as_of="2027-12-31T00:00:00Z"))
    assert (future["conclusion"], future["blocked_code"]) == ("BLOCKED", "DISCOVERY_AFTER_DECISION_CUTOFF")


def test_failclosed_input_scope_and_no_external_side_effects(tmp_path, monkeypatch):
    case, w, args, _ = build_case(tmp_path / "base")
    before = source_digests(case)
    body = json.loads(case.read_text(encoding="utf-8"))

    def prepare_variant(name, mutate, scratch=None):
        variant = json.loads(json.dumps(body))
        mutate(variant)
        path = tmp_path / f"{name}.json"
        path.write_text(json.dumps(variant), encoding="utf-8")
        with pytest.raises(proof.ProofStop) as stopped:
            proof.prepare(path, scratch or tmp_path / f"{name}-scratch")
        return str(stopped.value)
    danger = tmp_path / ".ssh"
    danger.mkdir()
    (danger / "pit.sqlite3").write_bytes(Path(body["sources"]["pit_store"]).read_bytes())
    for name, mutate, code in (
        ("missing", lambda c: c["sources"].update(pit_store=str(tmp_path / "absent.sqlite3")), "SOURCE_MISSING"),
        ("in-repo", lambda c: c["sources"].update(pit_store=str(TOOL)), "SOURCE_INSIDE_REPOSITORY"),
        ("danger", lambda c: c["sources"].update(pit_store=str(danger / "pit.sqlite3")), "SOURCE_DANGER_PATH"),
        ("duplicate", lambda c: c["sources"].update(alpha_registry=c["sources"]["pit_store"]), "SOURCE_PATH_DUPLICATE"),
        ("secret", lambda c: c["decision"]["occurrences"][0]["choice"].update(api_key="x"), "SECRET_MATERIAL_REJECTED"),
        ("level", lambda c: c.update(proof_level="CURRENT_LIVE"), "CASE_PROOF_LEVEL_INVALID"),
        ("too-many", lambda c: c["decision"]["occurrences"].extend([c["decision"]["occurrences"][0]] * 3),
         "CASE_OCCURRENCES_INVALID"),
        ("unknown-field", lambda c: c.update(execute=True), "CASE_FIELDS_INVALID"),
    ):
        assert prepare_variant(name, mutate) == code, name
    assert prepare_variant("scratch", lambda c: None, scratch=ROOT / "local_data" / "alpha03a") == "SCRATCH_INSIDE_REPOSITORY"
    assert not (ROOT / "local_data" / "alpha03a").exists()

    def blocked(name, **kwargs):
        manifest, scratch, _, _, _ = prepared_run(tmp_path, name, **kwargs)
        assert manifest["conclusion"] == "BLOCKED" and manifest["denominators"]["attempted"] == 0, (name, manifest)
        return manifest["blocked_code"]
    assert blocked("empty", markets=False) == "ZERO_OBSERVATIONS"
    assert blocked("mixed-clock", discovery=dict(analysis_temporal_mode="HISTORICAL_REPLAY")) == "TEMPORAL_POSTURE_INVALID"
    # Stale head: the named source changed after prepare.
    scratch = tmp_path / "stale-scratch"
    proof.prepare(case, scratch)
    w.assess(t=native.T0 - 400_000)
    with pytest.raises(proof.ProofStop, match="SOURCE_CHANGED_SINCE_PREPARE"):
        proof.run(scratch)
    # Corrupt frozen input copy.
    corrupt_case, _, _, _ = build_case(tmp_path / "corrupt")
    corrupt = tmp_path / "corrupt-scratch"
    proof.prepare(corrupt_case, corrupt)
    (corrupt / "inputs" / "pit_store.sqlite3").write_bytes(b"not a database")
    with pytest.raises(proof.ProofStop, match="INPUT_COPY_TAMPERED"):
        proof.run(corrupt)
    # Any network attempt from inside the native chain fails the whole run.
    net_case, _, _, _ = build_case(tmp_path / "net")
    net_before = source_digests(net_case)
    monkeypatch.setattr(tf.OfflineStageBBackend, "_dispatch",
                        lambda self, *a, **k: socket.create_connection(("provider.invalid", 443)))
    net = tmp_path / "net-scratch"
    proof.prepare(net_case, net)
    manifest = proof.run(net)
    assert (manifest["conclusion"], manifest["blocked_code"]) == ("BLOCKED", "NETWORK_ATTEMPT_BLOCKED")
    assert manifest["authority"]["network_attempts"] >= 1 and source_digests(net_case) == net_before
    monkeypatch.undo()
    # An unexpected write to a named source during the run is detected.
    mut_case, _, _, _ = build_case(tmp_path / "mutate")
    pit_original = Path(json.loads(mut_case.read_text(encoding="utf-8"))["sources"]["pit_store"])
    mutated = tmp_path / "mutate-scratch"
    proof.prepare(mut_case, mutated)
    real_summary = proof._paper_summary
    monkeypatch.setattr(proof, "_paper_summary", lambda *a: (pit_original.write_bytes(pit_original.read_bytes() + b"x"),
                                                            real_summary(*a))[1])
    assert proof.run(mutated)["blocked_code"] == "SOURCE_MUTATED"
    # The operator has no provider, OAuth, socket, subprocess or order surface at all.
    tree = ast.parse(TOOL.read_text(encoding="utf-8"))
    imported = {alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names}
    imported |= {node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module}
    forbidden = ("urllib", "http", "requests", "httpx", "subprocess", "oauth_plan_stage_b", "real_provider_stage_b",
                 "paper_trading.engine", "execution", "live")
    assert not [m for m in imported if any(part in m.split(".") or m.endswith(part) for part in forbidden)
                and m != "src.execution_feasibility"], imported
    assert source_digests(case) != before  # only the deliberate stale-head append changed a source
    assert {k: v for k, v in source_digests(case).items() if k != "hermes_manager_store"} == \
        {k: v for k, v in before.items() if k != "hermes_manager_store"}


def test_cold_reverify_denominators_and_sanitized_manifest(tmp_path, capsys):
    case, _, _, proposal = build_case(tmp_path / "cold")
    scratch = tmp_path / "cold-scratch"
    assert proof.main(["prepare", "--case", str(case), "--scratch-dir", str(scratch)]) == 0
    assert proof.main(["run", "--scratch-dir", str(scratch)]) == 0
    assert proof.main(["verify", "--scratch-dir", str(scratch)]) == 0
    printed = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    assert [p["status"] for p in printed[::2]] == ["PREPARED", "VERIFIED"]
    manifest = json.loads((scratch / "manifest.json").read_text(encoding="utf-8"))
    body = {k: v for k, v in manifest.items() if k != "manifest_id"}
    assert manifest["manifest_id"] == proof.MANIFEST_PREFIX + hashlib.sha256(proof.canonical(body)).hexdigest()
    assert manifest["conclusion"] in proof.CONCLUSIONS and printed[1]["conclusion"] == manifest["conclusion"]
    result = proof.verify(scratch)
    assert result["status"] == "VERIFIED" and result["fresh_attempts"] == 0 and result["originals_unchanged"]
    # Sanitized: no local paths, raw model output or order detail; ids and digests only.
    text = (scratch / "manifest.json").read_text(encoding="utf-8")
    for leaked in (str(tmp_path), str(tmp_path).replace("\\", "/"), json.dumps(proposal), "PASSIVE_MAKER", "api_key"):
        assert leaked not in text
    # Deterministic: an independent scratch over the same case yields the identical manifest.
    again = tmp_path / "again-scratch"
    proof.prepare(case, again)
    assert proof.run(again)["manifest_id"] == manifest["manifest_id"]
    # Tampering anywhere in the evidence chain is detected without any fresh dispatch.
    def tampered(name, damage):
        target = tmp_path / f"{name}-scratch"
        proof.prepare(case, target)
        proof.run(target)
        damage(target)
        verdict = proof.verify(target)
        assert verdict["status"] == "VERIFY_FAILED" and verdict["fresh_attempts"] == 0, (name, verdict)
        return verdict["reason_code"]

    def edit(path, old, new):
        path.write_bytes(path.read_bytes().replace(old, new))
    assert tampered("manifest", lambda t: edit(t / "manifest.json", b'"attempted":2', b'"attempted":1')) == "MANIFEST_TAMPERED"
    assert tampered("ledger", lambda t: edit(t / "ledger" / "occ-2.terminal.json", b"NOT_APPLICABLE_FEEDBACK",
                                             b"DECISION_LINKED_NONCAUSAL")) in ("LEDGER_TAMPERED", "BUNDLE_TAMPERED")
    assert tampered("missing", lambda t: (t / "ledger" / "occ-1.terminal.json").unlink()) == "LEDGER_INCOMPLETE"
    assert tampered("input", lambda t: edit(t / "inputs" / "alpha_registry.sqlite3", b"SQLite", b"SQLitf")) == "INPUT_COPY_TAMPERED"
    journal = lambda t: next((t / "journal" / "occ-1").glob("cycle-*.json"))  # noqa: E731
    assert tampered("journal", lambda t: edit(journal(t), b"ELIGIBLE_PREVIEW", b"NO_TRADE")) == "JOURNAL_REPLAY_MISMATCH"
    assert tampered("manager", lambda t: (t / "work" / "hermes_manager_store.sqlite3").write_bytes(b"")) in (
        "FEEDBACK_REPLAY_MISMATCH", "VERIFY_INPUT_INVALID")
