"""Witnessed pinned-Hermes specialists -> grounded cooperation -> advisory Alpha episode (S10-HERMES-DELEGATED-SPECIALISTS-01).

  run    --case CASE.json --grounding-scratch DIR --registry ALPHA.sqlite3 --scratch-dir DIR --pin-root DIR
  verify --scratch-dir DIR --registry ALPHA.sqlite3

Call path: copy of an existing S10-R3-SRC-01 scratch -> native ``run_source_grounding.verify`` (cold,
must be VERIFIED) -> ``research_cooperation.grounding_context`` -> ``delegated_specialists
.run_delegated_specialists`` (real pinned upstream ``delegate_task``, two witnessed leaf children,
offline scripted provider boundary only) -> one-shot ``claim_witness`` -> per-question native
``research_cooperation.assess_question`` -> ``alpha_factory.build_research_episode`` ->
``alpha_factory_registry.append_alpha_factory_records`` -> cold ``load_and_verify_alpha_factory_registry``.

The child summaries are untrusted content: role comes from the host task index, response and origin
ids from the witnessed native child identity, never from model text. The episode is advisory
(``DATA_INSUFFICIENT``, ``OTHER_VALIDATED_ADVISORY``, human review required) and appends to an
already-seeded candidate/family/source lineage only. Evidence class OFFLINE_NATIVE_DELEGATION_TEST_ONLY:
no real provider, market GET, credential, qualification, paper or order path exists here. The
historical 40-case ``run_hermes_cooperation`` operator is untouched.

Exit codes: 0 RUN_COMPLETE / VERIFIED / IDEMPOTENT_VERIFIED, 1 refusal or tamper, 2 usage error.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.data_layer.analytical_research import alpha_factory as AF  # noqa: E402
from src.data_layer.analytical_research import alpha_factory_registry as AFR  # noqa: E402
from src.data_layer.analytical_research import research_cooperation as HC  # noqa: E402
from src.data_layer.analytical_research import source_grounding as SG  # noqa: E402
from src.research_runtime.hermes_controlled_runtime import delegated_specialists as DS  # noqa: E402
from src.research_runtime.hermes_controlled_runtime.policy import DelegatedSpecialistsPolicy  # noqa: E402
from tools.alpha import run_hermes_cooperation as COOP  # noqa: E402
from tools.alpha import run_source_grounding as SGCLI  # noqa: E402

CASE_SCHEMA = "s10-hermes-delegated-case-v1"
RECEIPT_SCHEMA = "s10-hermes-delegated-receipt-v1"
RECEIPT_PREFIX = "hermesdelegatedreceipt:sha256:"
COOP_PREFIX = "hermesdelegatedcoop:sha256:"
CASE_KEYS = {"schema_id", "question", "research_question", "hypothesis_family_id", "source_reference_ids",
             "evidence_lanes", "scripted_children"}
SCRIPT_KEYS = {"mode", "content", "prompt_tokens", "completion_tokens", "seconds"}
GROUNDED_OUTCOMES = ("CITATIONS_VERIFIED_REVIEW_REQUIRED", "DISAGREEMENT_REVIEW_REQUIRED")
PRODUCER_VERSION = "s10-hermes-delegated-specialists-01"
WITNESS_ORIGIN_COLD = "RECORDED_COLD_REDERIVED_NOT_REISSUABLE"
OK_STATUSES = ("RUN_COMPLETE", "VERIFIED", "IDEMPOTENT_VERIFIED")
CODE_FILES = (Path(__file__), Path(DS.__file__), Path(HC.__file__), Path(SG.__file__), Path(AF.__file__), Path(AFR.__file__))


def code_identity() -> str:
    digest = hashlib.sha256()
    for path in CODE_FILES:
        digest.update(path.resolve().read_bytes())
    return "code:sha256:" + digest.hexdigest()


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise HC.CoopStop(code)


def _sha_json(value: object) -> str:
    return SG.sha256_hex(SG.canonical_bytes(value))


# ------------------------------------------------------------------ case and grounding


def parse_case(raw: bytes) -> dict:
    _require(0 < len(raw) <= COOP.MAX_CASE_BYTES, "CASE_UNREADABLE")
    _require(SG.SECRET_RE.search(raw.decode("utf-8", "replace")) is None, "SECRET_MATERIAL_REJECTED")
    case = SGCLI._strict_json(raw, "CASE_JSON_INVALID")
    _require(isinstance(case, dict) and set(case) == CASE_KEYS and case["schema_id"] == CASE_SCHEMA, "CASE_FIELDS_INVALID")
    question = case["question"]
    _require(isinstance(question, dict) and set(question) == set(HC.SCOPE_KEYS) and type(question["candidate_id"]) is str,
             "CASE_QUESTION_INVALID")
    _require(type(case["research_question"]) is str and case["research_question"].strip()
             and type(case["hypothesis_family_id"]) is str and isinstance(case["source_reference_ids"], list)
             and case["source_reference_ids"] and isinstance(case["evidence_lanes"], list), "CASE_FIELDS_INVALID")
    scripted = case["scripted_children"]
    _require(isinstance(scripted, dict) and set(scripted) == set(DS.ROLE_BY_INDEX)
             and all(isinstance(s, dict) and set(s) == SCRIPT_KEYS and s["mode"] in DS.SCRIPTED_MODES
                     and type(s["content"]) is str and type(s["prompt_tokens"]) is int
                     and type(s["completion_tokens"]) is int and type(s["seconds"]) in (int, float)
                     for s in scripted.values()), "CASE_SCRIPTED_CHILDREN_INVALID")
    return case


def freeze(grounding_dir: Path, case_path: Path, scratch: Path) -> None:
    grounding = COOP._caller_path(grounding_dir, directory=True, scratch=scratch)
    _require(grounding is not None, "GROUNDING_SCRATCH_UNUSABLE")
    raw = COOP._read_case(COOP._caller_path(case_path, directory=False, scratch=scratch))
    parse_case(raw)
    inputs = scratch / "inputs"
    inputs.mkdir(parents=True)
    for path in COOP._grounding_files(grounding):
        target = inputs / "grounding" / path.relative_to(grounding)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
        _require(path.read_bytes() == target.read_bytes(), "INPUT_CHANGED_DURING_FREEZE")
    (inputs / "case.json").write_bytes(raw)


def ground(scratch: Path) -> tuple[dict, dict, str, Path | None]:
    """(case, ctx, grounding receipt id, frozen registry path) from the frozen scratch, cold-verified natively."""
    inputs = scratch / "inputs"
    grounding_receipt_id = COOP._verify_grounding(scratch)
    case = parse_case((inputs / "case.json").read_bytes() if (inputs / "case.json").is_file() else b"")
    frozen = SGCLI._strict_json((inputs / "grounding" / "frozen_case.json").read_bytes(), "GROUNDING_SCRATCH_INVALID")
    ctx = HC.grounding_context(frozen, inputs / "grounding" / "inputs")
    registry = inputs / "grounding" / "inputs" / frozen["alpha_registry"] if frozen["alpha_registry"] else None
    return case, ctx, grounding_receipt_id, registry


def source_binding(case: dict, grounding_receipt_id: str) -> str:
    return _sha_json({"grounding_receipt_id": grounding_receipt_id, "question": case["question"],
                      "research_question": case["research_question"]})


def produce(policy, pin_root: object, case: dict, binding: str) -> DS.DelegationResult:
    scope = json.dumps(case["question"], sort_keys=True)
    contract = ('Return ONLY a JSON object {"claims": [...]}; each claim has claim_id, proposition_id, stance '
                '(FOR/AGAINST/UNCERTAIN), text and citations [{source_label, excerpt}] quoting admitted sources.')
    goals = (f"Forecast: {case['research_question']}", f"Falsify the forecast for: {case['research_question']}")
    scripted = {i: dict(case["scripted_children"][role]) for i, role in enumerate(DS.ROLE_BY_INDEX)}
    return DS.run_delegated_specialists(policy, pin_root, request_id="w01-" + binding[:32], source_binding_sha256=binding,
                                        goals=goals, contexts=(f"{scope}\n{contract}",) * 2, scripted=scripted)


# ------------------------------------------------------------------ witness -> cooperation -> episode


def _check_body(body: dict, binding: str) -> None:
    policy = DelegatedSpecialistsPolicy()
    _require(body.get("schema_id") == DS.SEALED_SCHEMA and body.get("policy_id") == policy.policy_id
             and body.get("pin_commit") == DS.PIN_COMMIT and body.get("evidence_class") == DS.EVIDENCE_CLASS,
             "WITNESS_BODY_INVALID")
    _require(body.get("source_binding_sha256") == binding, "WITNESS_SOURCE_BINDING_MISMATCH")
    children = body.get("children")
    _require(isinstance(children, list) and [c.get("task_index") for c in children] == [0, 1], "WITNESS_ROLE_LINEAGE_INVALID")
    for child in children:
        _require(child.get("role") == DS.ROLE_BY_INDEX[child["task_index"]] and child.get("status") == "completed"
                 and child.get("effective_tools") == list(policy.child_tools) and child.get("depth") == 1
                 and child.get("delegate_role") == "leaf" and child.get("parent_session_id") == body.get("parent_session_id")
                 and type(child.get("summary")) is str
                 and SG.sha256_hex(child["summary"].encode("utf-8")) == child.get("summary_sha256"),
                 "WITNESS_ROLE_LINEAGE_INVALID")
    _require(body.get("stable_binding") == DS._stable_binding(policy, {"source_binding_sha256": binding}, children),
             "WITNESS_STABLE_BINDING_MISMATCH")


def _submission(child: dict, case: dict) -> dict:
    output = SGCLI._strict_json(child["summary"].encode("utf-8"), "CHILD_OUTPUT_NOT_JSON")
    _require(isinstance(output, dict) and set(output) == {"claims"} and type(output["claims"]) is list,
             "CHILD_OUTPUT_SCHEMA_INVALID")  # role / origin / scope self-claims in model text are rejected
    _require(SG._QID_RE.fullmatch(child["subagent_id"]) is not None and SG._LABEL_RE.fullmatch(child["subagent_id"]),
             "CHILD_IDENTITY_INVALID")
    return {"role": DS.ROLE_BY_INDEX[child["task_index"]], "response_id": child["subagent_id"],
            "declared_origin": child["subagent_id"], "scope": dict(case["question"]), "native_draft": None,
            "claims": output["claims"]}


def derive(body: dict, case: dict, ctx: dict, grounding_receipt_id: str) -> tuple[dict, object]:
    """Native per-question cooperation over the witnessed children, then the native advisory episode record."""
    binding = source_binding(case, grounding_receipt_id)
    _check_body(body, binding)
    question = dict(case["question"], labels={"counterevidence_in_corpus": False, "conflict_present": False},
                    submissions=[_submission(c, case) for c in body["children"]])
    row = HC.assess_question(0, question, ctx, set())
    _require(row["status"] == "VALID", "QUESTION_INVALID:" + str(row["reason"]))
    cooperation = row["cooperation"]
    _require(cooperation["outcome"] in GROUNDED_OUTCOMES, "COOPERATION_NOT_GROUNDED:" + cooperation["outcome"])
    claims = cooperation["claims"]
    evidence_for = [f"{c['role']} claim {c['claim_id']} cites a verified admitted quote" for c in claims
                    if c["status"] == HC.SUPPORTED and c["stance"] == "FOR"]
    evidence_against = [f"{c['role']} claim {c['claim_id']} cites a verified admitted quote against the thesis" for c in claims
                        if c["status"] in (HC.SUPPORTED, HC.CONTRADICTED) and c["stance"] == "AGAINST"]
    scope = case["question"]
    mapping = {
        "episode_version": "v1", "candidate_id": scope["candidate_id"],
        "hypothesis_family_id": case["hypothesis_family_id"], "predecessor_episode_id": None,
        "reopened_episode_id": None, "result_state": "DATA_INSUFFICIENT", "confidence_label": "very_low",
        "evidence_lanes": list(case["evidence_lanes"]),
        "exact_scope": {"question_id": scope["question_id"], "market_id": scope["market_id"],
                        "source_cutoff": scope["source_cutoff"]},
        "evidence_regime": {"evidence_class": DS.EVIDENCE_CLASS, "acceptance_status": DS.ACCEPTANCE_STATUS,
                            "provider_invocations": DS.PROVIDER_INVOCATIONS},
        "research_question": case["research_question"].strip(),
        "thesis": "Two witnessed specialist children produced grounded citations; the evidence remains insufficient.",
        "tested_assumptions": ["Both specialists were witnessed native upstream leaf children bound by task index."],
        "evidence_for": evidence_for, "evidence_against": evidence_against,
        "uncertainties": ["Citation integrity does not verify semantic truth of the cited sources."],
        "known_missing_data": ["Real provider-backed specialist acceptance is pending.",
                               "No independent semantic fact verification was performed."],
        "falsification_checks_performed": [
            f"FALSIFIER child citations checked by native research_cooperation: {cooperation['outcome']}."],
        "limitations": [f"Evidence class {DS.EVIDENCE_CLASS}: offline scripted provider boundary only."],
        "what_would_change_the_conclusion": ["A separately authorized real provider-backed specialist acceptance."],
        "suggested_next_research_steps": ["Human review of the cited excerpts."],
        "source_reference_ids": list(case["source_reference_ids"]),
        "deterministic_evidence_refs": [grounding_receipt_id, COOP_PREFIX + _sha_json(cooperation), body["stable_binding"]],
        "material_change_basis": [], "producer_type": "OTHER_VALIDATED_ADVISORY", "producer_version": PRODUCER_VERSION,
        "producer_receipt_ref": body["stable_binding"], "research_as_of": scope["source_cutoff"],
        "creation_provenance": "offline_native_delegation_test_only", "human_review_required": True,
    }
    built = AF.build_research_episode(mapping)
    _require(built.is_valid, "EPISODE_INVALID:" + ",".join(built.error_codes))
    return row, built.record


def _registry_lineage(registry: Path, frozen_registry: Path | None, case: dict, ctx: dict) -> AFR.AlphaFactoryRegistrySnapshot:
    """The target registry must extend the grounding's frozen registry and hold every referenced record."""
    _require(frozen_registry is not None, "REGISTRY_LINEAGE_MISMATCH")
    target, frozen = (AFR.load_and_verify_alpha_factory_registry(p) for p in (registry, frozen_registry))
    _require(target.is_valid and frozen.is_valid, "REGISTRY_NOT_VERIFIED")
    prefix = [e.entry_hash for e in frozen.snapshot.entries]
    _require(prefix and [e.entry_hash for e in target.snapshot.entries][:len(prefix)] == prefix, "REGISTRY_LINEAGE_MISMATCH")
    records = {e.record_id: e.record for e in target.snapshot.entries}
    scope = case["question"]
    _require(scope["candidate_id"] in ctx["candidates"].get(scope["market_id"], set())
             and isinstance(records.get(scope["candidate_id"]), AF.OpportunityCandidate), "CANDIDATE_NOT_IN_LINEAGE")
    _require(isinstance(records.get(case["hypothesis_family_id"]), AF.HypothesisFamily), "FAMILY_NOT_IN_LINEAGE")
    _require(all(isinstance(records.get(s), AF.ResearchSourceReference) for s in case["source_reference_ids"]),
             "SOURCE_REFERENCE_NOT_IN_LINEAGE")
    return target.snapshot


def consume_witness(witness: object, case: dict, ctx: dict, grounding_receipt_id: str, registry: Path,
                    frozen_registry: Path | None) -> dict:
    """Claim (one-shot), ground, check lineage, append one advisory episode and cold-reload. No append on any refusal."""
    try:
        body = DS.claim_witness(witness)
    except DS.DelegationRefusal as refusal:
        raise HC.CoopStop(refusal.code) from None
    row, episode = derive(body, case, ctx, grounding_receipt_id)
    before = _registry_lineage(registry, frozen_registry, case, ctx)
    appended = AFR.append_alpha_factory_records(registry, [episode])
    _require(appended.is_valid, "REGISTRY_APPEND_REJECTED:" + ",".join(appended.error_codes))
    cold = AFR.load_and_verify_alpha_factory_registry(registry)
    _require(cold.is_valid and episode.research_episode_id in {e.record_id for e in cold.snapshot.entries}, "REGISTRY_COLD_READ_FAILED")
    return {"body": body, "row": row, "episode_id": episode.research_episode_id, "append_status": appended.status,
            "registry_head_before": before.head_entry_hash, "registry_head_after": cold.snapshot.head_entry_hash,
            "registry_rows_after": cold.snapshot.total_rows}


# ------------------------------------------------------------------ operator


def _finalize(core: dict) -> dict:
    return {"schema_id": RECEIPT_SCHEMA, "receipt_id": RECEIPT_PREFIX + _sha_json(core), "core": core}


def run(case_path: Path, grounding_dir: Path, registry_path: Path, scratch_dir: Path, pin_root: Path) -> dict:
    scratch = COOP._check_scratch(Path(scratch_dir))
    if scratch.exists() and any(scratch.iterdir()):
        return _repeat(Path(case_path), scratch, Path(registry_path))
    registry = COOP._caller_path(Path(registry_path), directory=False, scratch=scratch)
    _require(registry is not None, "REGISTRY_PATH_UNUSABLE")
    with SGCLI.no_network() as attempts:
        freeze(Path(grounding_dir), Path(case_path), scratch)
        case, ctx, grounding_receipt_id, frozen_registry = ground(scratch)
        produced = produce(DelegatedSpecialistsPolicy(), pin_root, case, source_binding(case, grounding_receipt_id))
        _require(produced.status == "WITNESSED", "DELEGATION_REFUSED:" + ",".join(produced.refusal_codes))
        consumed = consume_witness(produced.witness, case, ctx, grounding_receipt_id, registry, frozen_registry)
    _require(not attempts, "NETWORK_ATTEMPT_BLOCKED")
    inputs = scratch / "inputs"
    core = {"wp_id": DS.WP_ID, "code_identity": code_identity(), "grounding_receipt_id": grounding_receipt_id,
            "input_sha256": {p.relative_to(inputs).as_posix(): SG.sha256_hex(p.read_bytes())
                             for p in sorted(inputs.rglob("*")) if p.is_file()},
            "witness_id": produced.witness.witness_id, "witness_body": consumed["body"],
            "delegation_receipt": produced.receipt, "cooperation": consumed["row"], "episode_id": consumed["episode_id"],
            "append_status": consumed["append_status"], "registry_head_before": consumed["registry_head_before"],
            "registry_head_after": consumed["registry_head_after"], "evidence_class": DS.EVIDENCE_CLASS,
            "acceptance_status": DS.ACCEPTANCE_STATUS, "provider_invocations": DS.PROVIDER_INVOCATIONS,
            "authority": {"advisory_only": True, "no_execution_authority": True, "no_strategy_authority": True,
                          "no_qualification_authority": True, "human_review_required": True}}
    receipt = _finalize(core)
    with open(scratch / "receipt.json", "xb") as handle:
        handle.write(json.dumps(receipt, sort_keys=True, indent=1, ensure_ascii=False).encode("utf-8"))
    return {"status": "RUN_COMPLETE", "receipt_id": receipt["receipt_id"], "episode_id": consumed["episode_id"],
            "append_status": consumed["append_status"], "cooperation_outcome": consumed["row"]["cooperation"]["outcome"],
            "witness_id": produced.witness.witness_id, "evidence_class": DS.EVIDENCE_CLASS,
            "acceptance_status": DS.ACCEPTANCE_STATUS, "network_attempts": 0}


def _repeat(case_path: Path, scratch: Path, registry_path: Path) -> dict:
    """A non-empty scratch is never re-run: it must cold-verify and match the caller's case bytes, else refuse."""
    _require((scratch / "receipt.json").is_file(), "SCRATCH_NOT_EMPTY")
    checked = verify(scratch, registry_path)
    raw = COOP._read_case(COOP._caller_path(case_path, directory=False, scratch=scratch))
    _require(checked["status"] == "VERIFIED" and raw == (scratch / "inputs" / "case.json").read_bytes(), "SCRATCH_NOT_EMPTY")
    return {"status": "IDEMPOTENT_VERIFIED", "receipt_id": checked["receipt_id"], "network_attempts": 0}


def verify(scratch_dir: Path, registry_path: Path) -> dict:
    """Cold re-derivation from frozen inputs and the recorded witness body; never re-issues or re-appends."""
    scratch = Path(scratch_dir)
    _require(scratch.is_absolute() and scratch.is_dir() and not COOP._inside(scratch.resolve(), REPO_ROOT), "SCRATCH_INVALID")
    scratch = scratch.resolve()
    with SGCLI.no_network() as attempts:
        receipt = SGCLI._strict_json((scratch / "receipt.json").read_bytes() if (scratch / "receipt.json").is_file() else b"",
                                     "RECEIPT_UNREADABLE")
        failures = []
        try:
            core = receipt["core"]
            case, ctx, grounding_receipt_id, _ = ground(scratch)
            body = core["witness_body"]
            body_json = DS._canonical(body).decode("utf-8")
            if core["witness_id"] != DS.WITNESS_PREFIX + SG.sha256_hex(body_json.encode("utf-8")):
                failures.append("WITNESS_ID_MISMATCH")
            row, episode = derive(body, case, ctx, grounding_receipt_id)
            if row != core["cooperation"]:
                failures.append("COOPERATION_MISMATCH")
            if episode.research_episode_id != core["episode_id"] or grounding_receipt_id != core["grounding_receipt_id"]:
                failures.append("EPISODE_MISMATCH")
            loaded = AFR.load_and_verify_alpha_factory_registry(Path(registry_path))
            if not loaded.is_valid or episode.research_episode_id not in {e.record_id for e in loaded.snapshot.entries}:
                failures.append("EPISODE_NOT_IN_REGISTRY")
            if receipt.get("receipt_id") != _finalize(core)["receipt_id"]:
                failures.append("RECEIPT_ID_MISMATCH")
        except SG.GroundingStop as stop:
            failures.append(f"RECOMPUTE_REFUSED:{stop}")
        except (KeyError, TypeError, AttributeError):
            failures.append("RECEIPT_FIELDS_INVALID")
    _require(not attempts, "NETWORK_ATTEMPT_BLOCKED")
    return {"status": "VERIFIED" if not failures else "TAMPER_DETECTED", "failures": failures,
            "receipt_id": receipt.get("receipt_id") if isinstance(receipt, dict) else None,
            "witness_origin": WITNESS_ORIGIN_COLD, "network_attempts": 0}


def run_safe(args) -> dict:
    """Closed result for every outcome; refusals carry a stable code and never echo input, paths or stderr."""
    try:
        if args.command == "run":
            return run(args.case, args.grounding_scratch, args.registry, args.scratch_dir, args.pin_root)
        return verify(args.scratch_dir, args.registry)
    except SG.GroundingStop as stop:
        return {"status": "STOPPED", "reason_code": str(stop)}
    except FileExistsError:
        return {"status": "STOPPED", "reason_code": "WRITE_ONCE_CONFLICT"}
    except Exception:  # noqa: BLE001 - sanitized: no exception text or path is echoed
        return {"status": "STOPPED", "reason_code": "INTERNAL_REFUSAL"}


class _Parser(argparse.ArgumentParser):
    def error(self, message):  # sanitized usage error: never echo caller arguments
        print(json.dumps({"status": "USAGE_ERROR", "reason_code": "USAGE_INVALID"}, sort_keys=True))
        raise SystemExit(2)


def main(argv: list[str] | None = None) -> int:
    parser = _Parser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True, parser_class=_Parser)
    first = sub.add_parser("run")
    for flag in ("--case", "--grounding-scratch", "--registry", "--scratch-dir", "--pin-root"):
        first.add_argument(flag, required=True, type=Path)
    second = sub.add_parser("verify")
    for flag in ("--scratch-dir", "--registry"):
        second.add_argument(flag, required=True, type=Path)
    result = run_safe(parser.parse_args(argv))
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] in OK_STATUSES else 1


if __name__ == "__main__":
    raise SystemExit(main())
