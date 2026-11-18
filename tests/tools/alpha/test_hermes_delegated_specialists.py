"""S10-HERMES-DELEGATED-SPECIALISTS-01 R007-R012: witnessed pinned children -> grounded cooperation -> Alpha episode.

Chain under test (all native, offline): real SRC-01 scratch from the unmodified SRC-01 CLI -> operator
``run`` -> real pinned upstream ``delegate_task`` (two witnessed leaf children, scripted provider
boundary only) -> ``research_cooperation.assess_question`` -> ``build_research_episode`` ->
``append_alpha_factory_records`` -> cold ``load_and_verify_alpha_factory_registry``. The registry is an
isolated copy seeded by the native test helper (one source, one candidate, one family); nothing here
creates a candidate or family. Evidence class OFFLINE_NATIVE_DELEGATION_TEST_ONLY; no research quality,
real provider or Alpha claim is made. The pin comes from ``POLYMARKET_HERMES_PIN_ROOT``; without it the
pinned tests skip.
"""
from __future__ import annotations

import ast
import copy
import json
import os
from pathlib import Path
import shutil
import socket

import pytest

from src.data_layer.analytical_research import alpha_factory as AF
from src.data_layer.analytical_research import alpha_factory_registry as AFR
from src.data_layer.analytical_research import research_cooperation as HC
from src.data_layer.analytical_research import source_grounding as SG
from src.research_runtime.hermes_controlled_runtime import delegated_specialists as DS
from src.research_runtime.hermes_controlled_runtime import runner as RUNNER
from src.research_runtime.hermes_controlled_runtime.policy import DelegatedSpecialistsPolicy
from tests.data_layer.analytical_research.test_alpha_discovery import _alpha_registry, _pit_store
from tests.tools.alpha.test_source_grounding import AS_OF, QUERIES, RULES, _mid, _pit_records, _policy_mapping, _sha, _source
from tools.alpha import run_hermes_delegated_specialists as OP
from tools.alpha import run_source_grounding as SGCLI

PIN = os.environ.get("POLYMARKET_HERMES_PIN_ROOT")
pinned = pytest.mark.skipif(not PIN, reason="POLYMARKET_HERMES_PIN_ROOT not set: exact pinned Hermes checkout absent")
REPO_ROOT = Path(__file__).resolve().parents[3]
CUTOFF = "2026-06-01T00:00:00Z"
PRO = "the leading indicator moved toward the YES outcome"
CON = "the indicator stalled and points toward NO"
FAKE = "the indicator tripled overnight and settled the question"


def _brief(line):
    filler = "This synthetic briefing paragraph exists only so the archived page passes the length gate. " * 3
    return f"<html><body><h1>Synthetic briefing for cpi</h1><p>Observers say {line}.</p><p>{filler}</p></body></html>".encode()


def _claims(cid, prop, stance, label, excerpt):
    return json.dumps({"claims": [{"claim_id": cid, "proposition_id": prop, "stance": stance,
                                   "text": "Synthetic research claim.",
                                   "citations": [{"source_label": label, "excerpt": excerpt}]}]})


@pytest.fixture(scope="module")
def seeded(tmp_path_factory):
    """Real SRC-01 scratch plus the seeded native Alpha registry it froze (source + candidate + family)."""
    base = tmp_path_factory.mktemp("w01_inputs")
    pit = _pit_store(base, _pit_records())
    alpha = _alpha_registry(base, [("cpi", None)])

    def put(name, data):
        path = (base / name).resolve()
        path.write_bytes(data)
        return path
    rules = [{"market_id": _mid(s), "file": str(put(f"rule-{s}.txt", t.encode()))} for s, t in RULES.items()]
    sources = [_source(f"cpi-{kind}", "cpi", put(f"cpi-{kind}.html", _brief(line)), _brief(line))
               for kind, line in (("pro", PRO), ("con", CON))]
    late = _brief("a late revision arrived after the morning cutoff")
    sources.append(_source("cpi-late", "cpi", put("cpi-late.html", late), late, source_publish_time="2026-05-31T12:00:00Z",
                           public_available_time="2026-05-31T12:00:00Z", local_first_seen_time="2026-05-31T13:00:00Z",
                           ingestion_time="2026-05-31T13:00:01Z"))
    queries = [{"query_id": q, "text": t, "category_hint": c, "relevant_market_ids": [_mid(s) for s in rel]}
               for q, t, c, rel in QUERIES]
    src_case = {"schema_id": SG.CASE_SCHEMA, "case_label": "w01-grounding", "corpus_class": "SANITIZED_SYNTHETIC",
                "pit_store": str(pit), "alpha_registry": str(alpha), "policy": _policy_mapping(), "as_of": AS_OF,
                "rule_texts": rules, "sources": sources, "queries": queries}
    case_path = base / "src-case.json"
    case_path.write_text(json.dumps(src_case), encoding="utf-8")
    scratch = (tmp_path_factory.mktemp("w01_src") / "grounding").resolve()
    assert SGCLI.main(["run", "--case", str(case_path), "--scratch-dir", str(scratch)]) == 0
    records = {type(e.record).__name__: e.record_id for e in AFR.load_and_verify_alpha_factory_registry(alpha).snapshot.entries}
    receipt = json.loads((scratch / "receipt.json").read_text(encoding="utf-8"))
    return {"scratch": scratch, "registry": alpha, "base": base, "receipt": receipt,
            "candidate": receipt["core"]["alpha_join"]["joined"][0]["candidate_id"],
            "family": records["HypothesisFamily"], "source": records["ResearchSourceReference"]}


def _case(seeded, *, forecaster=None, falsifier=None, allowlist=("cpi-pro", "cpi-con"), cutoff=CUTOFF):
    def script(content):
        return {"mode": "reply", "content": content, "prompt_tokens": 64, "completion_tokens": 64, "seconds": 0}
    return {"schema_id": OP.CASE_SCHEMA,
            "question": {"question_id": "q-w01-cpi", "market_id": _mid("cpi"), "candidate_id": seeded["candidate"],
                         "source_cutoff": cutoff, "rule_sha256": _sha(RULES["cpi"].encode()),
                         "source_allowlist": list(allowlist)},
            "research_question": "Does the admitted public briefing support the cpi market outcome?",
            "hypothesis_family_id": seeded["family"], "source_reference_ids": [seeded["source"]],
            "evidence_lanes": ["FUNDAMENTAL"],
            "scripted_children": {"FORECASTER": script(forecaster or _claims("f1", "p1", "FOR", "cpi-pro", PRO)),
                                  "FALSIFIER": script(falsifier or _claims("x1", "p2", "AGAINST", "cpi-con", CON))}}


def _write_case(tmp_path, case, name="case.json"):
    path = (tmp_path / name).resolve()
    path.write_text(json.dumps(case), encoding="utf-8")
    return path


def _registry_copy(seeded, tmp_path, name="target.sqlite3"):
    target = (tmp_path / name).resolve()
    shutil.copyfile(seeded["registry"], target)
    return target


def _rows(path):
    return AFR.load_and_verify_alpha_factory_registry(path).snapshot.total_rows


def _cli(*argv):
    return OP.main([str(a) for a in argv])


@pytest.fixture(scope="module")
def delivered(seeded, tmp_path_factory):
    """One real operator run: pinned delegation -> grounding -> Alpha append, then stdout result."""
    work = tmp_path_factory.mktemp("w01_run")
    registry = _registry_copy(seeded, work)
    case_path = _write_case(work, _case(seeded))
    scratch = (work / "scratch").resolve()
    rows_before = _rows(registry)
    result = OP.run(case_path, seeded["scratch"], registry, scratch, Path(PIN))
    return {"result": result, "registry": registry, "case": case_path, "scratch": scratch, "rows_before": rows_before,
            "receipt": json.loads((scratch / "receipt.json").read_text(encoding="utf-8")), "work": work}


def _ground_ctx(seeded, tmp_path):
    scratch = (tmp_path / "frozen").resolve()
    OP.freeze(seeded["scratch"], _write_case(tmp_path, _case(seeded), "frozen-case.json"), scratch)
    return OP.ground(scratch)


def _rebody(body, index, summary):
    """A self-consistent witness body whose child ``index`` returned ``summary`` (as a real child could)."""
    body = copy.deepcopy(body)
    child = body["children"][index]
    child["summary"], child["summary_sha256"] = summary, SG.sha256_hex(summary.encode("utf-8"))
    body["stable_binding"] = DS._stable_binding(DelegatedSpecialistsPolicy(), body, body["children"])
    return body


@pinned
def test_existing_grounded_cooperation_citations_are_reused(delivered, seeded, tmp_path):
    result, receipt = delivered["result"], delivered["receipt"]
    assert result["status"] == "RUN_COMPLETE" and result["cooperation_outcome"] == "CITATIONS_VERIFIED_REVIEW_REQUIRED"
    assert SGCLI.verify(seeded["scratch"])["status"] == "VERIFIED"
    assert receipt["core"]["grounding_receipt_id"] == seeded["receipt"]["receipt_id"]
    coop = receipt["core"]["cooperation"]["cooperation"]
    assert {c["status"] for c in coop["claims"]} == {HC.SUPPORTED}
    assert all(x["quote_verified"] is True for c in coop["claims"] for x in c["citations"])
    roles = receipt["core"]["cooperation"]["roles"]
    assert [r["role"] for r in roles] == ["FORECASTER", "FALSIFIER"] and {r["status"] for r in roles} == {"ROLE_ADMITTED"}
    # The historical 40-case synthetic operator is untouched and not reused as research quality.
    assert HC.BENCHMARK_MIN_CASES == 40 and HC.SPECIALIST_ORIGIN == "CALLER_SUPPLIED_NOT_INDEPENDENTLY_VERIFIED"
    assert "benchmark" not in receipt["core"]
    # Native checker rejects a fabricated quote, a non-allowlisted source and a post-cutoff source.
    case, ctx, grounding_id, _ = _ground_ctx(seeded, tmp_path)
    body = receipt["core"]["witness_body"]
    for index, summary, reason in (
            (0, _claims("f1", "p1", "FOR", "cpi-pro", FAKE), "COOPERATION_NOT_GROUNDED:INCONCLUSIVE"),
            (1, _claims("x1", "p2", "AGAINST", "cpi-late", "a late revision arrived"), "COOPERATION_NOT_GROUNDED:INCONCLUSIVE"),
            (0, '{"claims": [], "role": "FALSIFIER"}', "CHILD_OUTPUT_SCHEMA_INVALID"),
            (1, "not json at all", "CHILD_OUTPUT_NOT_JSON")):
        with pytest.raises(SG.GroundingStop, match=reason):
            OP.derive(_rebody(body, index, summary), case, ctx, grounding_id)
    late_case = dict(case, question=dict(case["question"], source_allowlist=["cpi-pro", "cpi-con", "cpi-late"],
                                         source_cutoff="2026-05-31T06:00:00Z"))
    late_body = _rebody(dict(body, source_binding_sha256=OP.source_binding(late_case, grounding_id)), 1,
                        _claims("x1", "p2", "AGAINST", "cpi-late", "a late revision arrived"))
    with pytest.raises(HC.CoopStop, match="COOPERATION_NOT_GROUNDED:INCONCLUSIVE"):
        OP.derive(late_body, late_case, ctx, grounding_id)


@pinned
def test_actual_alpha_registry_consumer_append_and_cold_replay(delivered, seeded, tmp_path):
    result, registry = delivered["result"], delivered["registry"]
    assert result["append_status"] == "REGISTRY_APPEND_COMMITTED"
    cold = AFR.load_and_verify_alpha_factory_registry(registry)
    assert cold.is_valid and cold.snapshot.total_rows == delivered["rows_before"] + 1
    head = cold.snapshot.entries[-1]
    assert head.record_id == result["episode_id"] and head.record_kind == "RESEARCH_EPISODE"
    assert cold.snapshot.head_entry_hash == delivered["receipt"]["core"]["registry_head_after"]
    episode = head.record
    assert episode.candidate_id == seeded["candidate"] and episode.hypothesis_family_id == seeded["family"]
    assert episode.source_reference_ids == (seeded["source"],)
    assert seeded["receipt"]["receipt_id"] in episode.deterministic_evidence_refs
    assert episode.producer_receipt_ref == delivered["receipt"]["core"]["witness_body"]["stable_binding"]
    # Second full run (new scratch, new native child sessions) yields the same episode: idempotent append.
    again = OP.run(delivered["case"], seeded["scratch"], registry, (tmp_path / "scratch2").resolve(), Path(PIN))
    assert again["status"] == "RUN_COMPLETE" and again["append_status"] == "REGISTRY_APPEND_IDEMPOTENT"
    assert again["episode_id"] == result["episode_id"] and again["witness_id"] != result["witness_id"]
    assert _rows(registry) == delivered["rows_before"] + 1
    # Repeat over the same scratch: cold-verified, nothing re-run or re-written.
    repeat = OP.run(delivered["case"], seeded["scratch"], registry, delivered["scratch"], Path(PIN))
    assert repeat["status"] == "IDEMPOTENT_VERIFIED" and _rows(registry) == delivered["rows_before"] + 1
    assert OP.verify(delivered["scratch"], registry)["status"] == "VERIFIED"


@pinned
def test_alpha_rejects_forged_witness_or_broken_lineage(delivered, seeded, tmp_path):
    case, ctx, grounding_id, frozen_registry = _ground_ctx(seeded, tmp_path)
    registry = _registry_copy(seeded, tmp_path)
    rows = _rows(registry)
    body = delivered["receipt"]["core"]["witness_body"]
    forged = DS.DelegationWitness(delivered["receipt"]["core"]["witness_id"], json.dumps(body, sort_keys=True))
    with pytest.raises(HC.CoopStop, match="WITNESS_NOT_HOST_ISSUED|WITNESS_TAMPERED|WITNESS_ALREADY_CONSUMED"):
        OP.consume_witness(forged, case, ctx, grounding_id, registry, frozen_registry)
    with pytest.raises(HC.CoopStop, match="WITNESS_NOT_HOST_ISSUED"):
        OP.consume_witness(body, case, ctx, grounding_id, registry, frozen_registry)  # self-assigned receipt
    digest_changed = copy.deepcopy(body)
    digest_changed["children"][1]["summary_sha256"] = "0" * 64  # event/output digest tamper
    tampered = (
        ("WITNESS_SOURCE_BINDING_MISMATCH", dict(body, source_binding_sha256="0" * 64)),
        ("WITNESS_ROLE_LINEAGE_INVALID", dict(body, children=[dict(body["children"][0], role="FALSIFIER"),
                                                              body["children"][1]])),
        ("WITNESS_ROLE_LINEAGE_INVALID", digest_changed),
        ("WITNESS_STABLE_BINDING_MISMATCH", dict(body, stable_binding=DS.BINDING_PREFIX + "0" * 64)),
        ("WITNESS_BODY_INVALID", dict(body, policy_id="hermesdelegatedpolicy:sha256:" + "0" * 64)),
    )
    for code, bad in tampered:
        with pytest.raises(HC.CoopStop, match=code):
            OP.derive(bad, case, ctx, grounding_id)
    bad_case = {"CANDIDATE_NOT_IN_LINEAGE": dict(case, question=dict(case["question"], candidate_id="alphacandidate:sha256:" + "0" * 64)),
                "FAMILY_NOT_IN_LINEAGE": dict(case, hypothesis_family_id="alphafamily:sha256:" + "0" * 64),
                "SOURCE_REFERENCE_NOT_IN_LINEAGE": dict(case, source_reference_ids=["alphasource:sha256:" + "0" * 64])}
    for code, changed in bad_case.items():
        with pytest.raises(HC.CoopStop, match=code):
            OP._registry_lineage(registry, frozen_registry, changed, ctx)
    outsider = (tmp_path / "outsider.sqlite3").resolve()
    assert AFR.initialize_alpha_factory_registry(outsider).is_valid
    with pytest.raises(HC.CoopStop, match="REGISTRY_LINEAGE_MISMATCH"):
        OP._registry_lineage(outsider, frozen_registry, case, ctx)
    with pytest.raises(HC.CoopStop, match="REGISTRY_LINEAGE_MISMATCH"):
        OP._registry_lineage(registry, None, case, ctx)  # missing predecessor registry
    # Through the public run path: an outsider registry is refused after a genuine witnessed run, with no write.
    outsider_rows = _rows(outsider)
    refused = OP.run_safe(type("A", (), {"command": "run", "case": delivered["case"], "grounding_scratch": seeded["scratch"],
                                          "registry": outsider, "scratch_dir": (tmp_path / "s-out").resolve(),
                                          "pin_root": Path(PIN)})())
    assert refused == {"status": "STOPPED", "reason_code": "REGISTRY_LINEAGE_MISMATCH"}
    assert _rows(outsider) == outsider_rows and _rows(registry) == rows


@pinned
def test_engineering_only_no_product_network_or_credentials(delivered, monkeypatch, tmp_path):
    core = delivered["receipt"]["core"]
    assert core["provider_invocations"] == "ZERO_REAL_PROVIDER_INVOCATIONS"
    assert core["delegation_receipt"]["network_attempts_denied"] >= 1 and core["witness_body"]["transport"] == \
        "OFFLINE_SCRIPTED_PROVIDER_BOUNDARY"
    assert delivered["result"]["network_attempts"] == 0
    # The worker env is a closed allowlist; nothing (credentials included) is inherited from the host.
    captured = {}

    def capture(python, script, args, *, env, cwd, timeout_seconds, max_output_bytes=1 << 20):
        captured.update(env=dict(env), args=list(args))
        return RUNNER.PinnedWorkerOutcome(None, True, False, "0" * 64, "0" * 64, 0, 0)
    monkeypatch.setattr(RUNNER, "run_pinned_python_worker", capture)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-not-forwarded-0000000000")
    monkeypatch.setenv("POLYMARKET_PRIVATE_KEY", "not-forwarded")
    result = DS.run_delegated_specialists(DelegatedSpecialistsPolicy(), PIN, request_id="w01-env",
                                          source_binding_sha256="d" * 64, goals=("a", "b"), contexts=("c", "c"),
                                          scripted={0: DS.scripted_reply("{}"), 1: DS.scripted_reply("{}")})
    assert result.refusal_codes == ("WORKER_TIMEOUT",) and result.witness is None
    allowed = {"HERMES_HOME", "HOME", "USERPROFILE", "APPDATA", "LOCALAPPDATA", "TEMP", "TMP", "HERMES_MANAGED_DIR",
               "PATH", "PYTHONDONTWRITEBYTECODE", "PYTHONNOUSERSITE", "PYTHONIOENCODING", "NO_COLOR",
               "HERMES_DISABLE_LAZY_INSTALLS", "SYSTEMROOT"}
    assert set(captured["env"]) <= allowed and "not-forwarded" not in json.dumps(captured)
    home_keys = ("HERMES_HOME", "HOME", "USERPROFILE", "APPDATA", "LOCALAPPDATA", "TEMP", "TMP", "HERMES_MANAGED_DIR")
    assert all("w01-delegation-" in captured["env"][k] for k in home_keys)  # ephemeral, never the user profile
    assert captured["env"]["PATH"] == str(DS.pin_python(Path(PIN)).parent)
    # Host-side operator code path imports no network, account, order or execution module.
    for path in (Path(OP.__file__), Path(DS.__file__)):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        names = {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names} | \
                {n.module or "" for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}
        assert not {m for m in names if m.split(".")[0] in {"requests", "httpx", "urllib3", "aiohttp", "websockets"}}
        assert not any(x in m for m in names for x in ("execution", "order", "wallet", "signer", "paper", "live_trading"))
    # Global sockets are disallowed during the host-side consumer path too.
    monkeypatch.setattr(socket.socket, "connect", lambda *a, **k: (_ for _ in ()).throw(OSError("denied")))
    assert OP.verify(delivered["scratch"], delivered["registry"])["status"] == "VERIFIED"


@pinned
def test_resume_replay_failure_and_sanitized_identity(delivered, seeded, monkeypatch, tmp_path):
    registry = delivered["registry"]
    rows = _rows(registry)
    # Crash before the receipt: a half-written scratch is never resumed or re-run.
    crashed = (tmp_path / "crashed").resolve()
    OP.freeze(seeded["scratch"], delivered["case"], crashed)
    stopped = OP.run_safe(type("A", (), {"command": "run", "case": delivered["case"], "grounding_scratch": seeded["scratch"],
                                          "registry": registry, "scratch_dir": crashed, "pin_root": Path(PIN)})())
    assert stopped == {"status": "STOPPED", "reason_code": "SCRATCH_NOT_EMPTY"} and _rows(registry) == rows
    # Restart: a recorded witness reloaded from disk can never be claimed again.
    core = delivered["receipt"]["core"]
    reloaded = DS.DelegationWitness(core["witness_id"], DS._canonical(core["witness_body"]).decode("utf-8"))
    with pytest.raises(DS.DelegationRefusal, match="WITNESS_ALREADY_CONSUMED"):
        DS.claim_witness(reloaded)
    monkeypatch.setattr(DS, "_ISSUED", {})
    monkeypatch.setattr(DS, "_CONSUMED", set())
    with pytest.raises(DS.DelegationRefusal, match="WITNESS_NOT_HOST_ISSUED"):
        DS.claim_witness(reloaded)
    # Cold re-derivation from durable frozen inputs; any stale or edited receipt is detected.
    checked = OP.verify(delivered["scratch"], registry)
    assert checked["status"] == "VERIFIED" and checked["witness_origin"] == "RECORDED_COLD_REDERIVED_NOT_REISSUABLE"
    stale = (tmp_path / "stale").resolve()
    shutil.copytree(delivered["scratch"], stale)
    edited = json.loads((stale / "receipt.json").read_text(encoding="utf-8"))
    edited["core"]["witness_body"]["children"][0]["summary"] = _claims("f1", "p1", "FOR", "cpi-pro", FAKE)
    (stale / "receipt.json").write_text(json.dumps(edited), encoding="utf-8")
    assert OP.verify(stale, registry)["status"] == "TAMPER_DETECTED"
    (stale / "inputs" / "case.json").write_bytes(b"{}")
    assert OP.verify(stale, registry)["status"] == "TAMPER_DETECTED"
    # Sanitized identity: no local paths, raw stderr or exception text in results or the receipt.
    text = json.dumps([delivered["result"], delivered["receipt"], checked, stopped])
    for needle in (str(Path.home()), str(delivered["work"]), str(seeded["base"]), "Traceback", "\\\\Users", "/home/"):
        assert needle not in text
    assert "stderr" not in json.dumps(delivered["result"])


@pinned
def test_no_alpha_qualification_paper_or_strategy_promotion(delivered, seeded):
    entries = AFR.load_and_verify_alpha_factory_registry(delivered["registry"]).snapshot.entries
    added = entries[delivered["rows_before"]:]
    assert [e.record_kind for e in added] == ["RESEARCH_EPISODE"]  # no new candidate, family or source
    episode = added[0].record
    assert episode.advisory_only and episode.no_execution_authority and episode.no_strategy_authority \
        and episode.no_qualification_authority
    assert episode.result_state == "DATA_INSUFFICIENT" and episode.producer_type == "OTHER_VALIDATED_ADVISORY"
    assert episode.producer_type != "HERMES_CONTROLLED_RESEARCH" and episode.human_review_required is True
    assert episode.confidence_label == "very_low" and episode.known_missing_data
    assert json.loads(episode.evidence_regime_json)["evidence_class"] == "OFFLINE_NATIVE_DELEGATION_TEST_ONLY"
    authority = delivered["receipt"]["core"]["authority"]
    assert all(authority.values())
    for path in (Path(OP.__file__), Path(DS.__file__)):
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        modules = {n.module or "" for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)} | \
                  {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
        for forbidden in ("qualification", "strategy_manager", "wp170", "wp172", "wp173", "gate_c", "paper",
                          "learning", "alpha_discovery"):
            assert not any(forbidden in m for m in modules)
