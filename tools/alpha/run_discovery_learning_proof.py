"""Finite foreground discovery -> offline decision -> research-paper evidence proof (S10-ALPHA-03A).

One operator, three explicit phases, no defaults:

  prepare --case CASE.json --scratch-dir DIR   freeze byte copies of the named local stores
  run     --scratch-dir DIR                    compose native APIs once; write one manifest
  verify  --scratch-dir DIR                    cold replay from the frozen copies; zero dispatch

It composes only merged native components: ALPHA-02 universe/triage/queue, the Alpha
registry, the strategy lifecycle and Hermes manager stores, AUTO-02 ``run_one_cycle`` over
the offline injected Stage B backend, and the WP173 research-paper snapshot feeding a
FakeHermesBackend ``PERFORMANCE_UPDATE``. What it adds is the missing cross-system record:
the queue -> menu derivation (with RESEARCH_NEEDED and overflow kept), a STARTED-first
occurrence ledger with exactly one terminal per occurrence, and one sanitized,
content-addressed manifest that ``verify`` re-derives.

It never calls a provider, OAuth, market or account endpoint, opens no socket (a guard
fails the run if anything tries), places no paper or live order and writes nothing outside
the scratch directory. Every result is research evidence with no execution authority;
``DECISION_LINKED`` is an identity relation, never a causal claim.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import shutil
import socket
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.data_layer.analytical_research import alpha_discovery as AD  # noqa: E402
from src.data_layer.analytical_research.alpha_factory import OpportunityCandidate  # noqa: E402
from src.data_layer.analytical_research import alpha_factory_registry as AFR  # noqa: E402
from src.execution_feasibility import public_market as venue  # noqa: E402
from src.paper_trading.models import build_research_strategy_binding  # noqa: E402
from src.research_runtime import autonomous_opportunity_cycle as cycle  # noqa: E402
from src.research_runtime import paper_performance_bridge as bridge  # noqa: E402
from src.research_runtime.hermes_controlled_runtime import autonomous_feedback as fb  # noqa: E402
from src.research_runtime.hermes_controlled_runtime import strategy_manager as sm  # noqa: E402
from src.research_runtime.hermes_controlled_runtime import tool_free_stage_b as stage_b  # noqa: E402
from src.research_runtime.hermes_controlled_runtime.runner import FakeHermesBackend, HermesInvocationOutcome  # noqa: E402
from src.strategy_lifecycle import load_strategy_lifecycle_store  # noqa: E402

CASE_SCHEMA = "s10-alpha03a-proof-case-v1"
PREPARED_SCHEMA = "s10-alpha03a-prepared-v1"
MANIFEST_SCHEMA = "s10-alpha03a-proof-manifest-v1"
MANIFEST_PREFIX = "alpha03aproof:sha256:"
OCCURRENCE_PREFIX = "alpha03aocc:sha256:"
MENU_LIMIT = 8  # AUTO-01's own bound
MAX_OCCURRENCES = 3
MAX_CASE_BYTES = 1 << 20
MAX_MANIFEST_BYTES = 256 << 10
PROOF_LEVELS = ("SYNTHETIC_ONLY", "LOCAL_RESEARCH_COPY")
SOURCE_ROLES = ("pit_store", "alpha_registry", "lifecycle_store", "hermes_manager_store", "paper_store")
CONCLUSIONS = ("PLUMBING_ONLY", "VERIFIED_OUTCOME_FEEDBACK_OBSERVED", "BLOCKED")
_LABEL = re.compile(r"[a-z0-9][a-z0-9_-]{0,47}")
_GAMMA_MARKET = re.compile(r"market:polymarket:([0-9]{1,32})")
_TOKEN = re.compile(r"token:polymarket:([0-9]{1,96})")
_SECRET = re.compile(
    r"(?i)(sk-[a-z0-9_-]{16,}|bearer\s+[a-z0-9._-]{8,}|-----begin [a-z ]*private key|"
    r"\"(api_key|access_token|refresh_token|id_token|password|passphrase|mnemonic|seed_phrase|"
    r"private_key|client_secret|authorization|cookie)\")")
_DANGER_PARTS = {".ssh", ".aws", ".gnupg", ".codex", ".hermes", "credentials", "secrets", "agent_memory"}
_ABSOLUTE = re.compile(r"([A-Za-z]:[\\/]|\\\\|/(Users|home|tmp|var|private|mnt)/)")
_CASE_KEYS = {"schema_id", "case_label", "proof_level", "sources", "discovery", "decision", "paper"}
_DISCOVERY_KEYS = {"policy", "as_of", "prior_as_of", "analysis_temporal_mode", "alpha_memory_temporal_posture"}
_DECISION_KEYS = {"surface_report", "model_label", "information_cutoff_ns", "evaluated_at_ns", "deadline_ns",
                  "venue_snapshots", "occurrences"}
_OCCURRENCE_KEYS = {"label", "issued_at_ns", "completed_at_ns", "choice"}
_VENUE_KEYS = {"gamma_market_id", "condition_id", "token_id", "acquisition_started_ns", "acquisition_completed_ns",
               "gamma_document", "clob_document"}
_PAPER_KEYS = {"binding", "strategy_version_id", "information_cutoff", "decision_time_ns", "provider_label",
               "model_label", "manager_clock_utc", "manager_draft", "manager_usage"}
_LANES = ("core_triage_ids", "exploration_triage_ids", "audit_triage_ids", "deferred_triage_ids",
          "skipped_ineligible_triage_ids", "skipped_capacity_triage_ids")


class ProofStop(Exception):
    """Typed, sanitized fail-closed terminal; the code is the whole message."""


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise ProofStop(code)


def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode()


def _sha(value: object) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def _file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _strict_load(raw: bytes, code: str) -> object:
    def pairs(items):
        keys = [k for k, _ in items]
        _require(len(keys) == len(set(keys)), code)
        return dict(items)

    def constant(_):
        raise ProofStop(code)
    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=pairs, parse_constant=constant)
    except ProofStop:
        raise
    except Exception:
        raise ProofStop(code) from None


def _read_json(path: Path, code: str, limit: int = MAX_CASE_BYTES) -> dict:
    _require(path.is_file() and not path.is_symlink() and path.stat().st_size <= limit, code)
    value = _strict_load(path.read_bytes(), code)
    _require(type(value) is dict, code)
    return value


def _write_once(path: Path, value: object) -> None:
    with path.open("xb") as stream:
        stream.write(canonical(value))


def _int_ns(value: object) -> bool:
    return type(value) is int and 0 < value < 1 << 63


def _iso_ns(text: str) -> int:
    moment = datetime.fromisoformat(text.replace("Z", "+00:00"))
    _require(moment.tzinfo is not None, "CASE_CLOCK_INVALID")
    return int(moment.timestamp()) * 1_000_000_000


def _inside(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


@contextmanager
def no_network():
    """Every socket entry point raises; ``attempts`` survives native catch-all handlers."""
    attempts = []

    def deny(*_args, **_kwargs):
        attempts.append(1)
        raise ProofStop("NETWORK_ATTEMPT_BLOCKED")
    saved = (socket.socket.connect, socket.socket.connect_ex, socket.create_connection, socket.getaddrinfo)
    socket.socket.connect = socket.socket.connect_ex = deny
    socket.create_connection = socket.getaddrinfo = deny
    try:
        yield attempts
    finally:
        socket.socket.connect, socket.socket.connect_ex, socket.create_connection, socket.getaddrinfo = saved


# ------------------------------------------------------------------ case validation


def validate_case(case: dict) -> None:
    _require(set(case) == _CASE_KEYS and case["schema_id"] == CASE_SCHEMA, "CASE_FIELDS_INVALID")
    _require(type(case["case_label"]) is str and _LABEL.fullmatch(case["case_label"]) is not None, "CASE_FIELDS_INVALID")
    _require(case["proof_level"] in PROOF_LEVELS, "CASE_PROOF_LEVEL_INVALID")
    sources, paper = case["sources"], case["paper"]
    _require(type(sources) is dict and set(sources) == set(SOURCE_ROLES), "CASE_SOURCES_INVALID")
    _require(all(type(sources[r]) is str for r in SOURCE_ROLES[:4]), "CASE_SOURCES_INVALID")
    _require((paper is None) == (sources["paper_store"] is None), "CASE_PAPER_INVALID")
    discovery = case["discovery"]
    _require(type(discovery) is dict and set(discovery) == _DISCOVERY_KEYS and type(discovery["policy"]) is dict and
             type(discovery["as_of"]) is str and (discovery["prior_as_of"] is None or type(discovery["prior_as_of"]) is str),
             "CASE_DISCOVERY_INVALID")
    decision = case["decision"]
    _require(type(decision) is dict and set(decision) == _DECISION_KEYS and type(decision["surface_report"]) is dict and
             type(decision["model_label"]) is str and
             all(_int_ns(decision[k]) for k in ("information_cutoff_ns", "evaluated_at_ns", "deadline_ns")),
             "CASE_DECISION_INVALID")
    venues = decision["venue_snapshots"]
    _require(type(venues) is list and len(venues) <= MENU_LIMIT and
             all(type(v) is dict and set(v) == _VENUE_KEYS for v in venues), "CASE_VENUE_INVALID")
    occurrences = decision["occurrences"]
    _require(type(occurrences) is list and 1 <= len(occurrences) <= MAX_OCCURRENCES, "CASE_OCCURRENCES_INVALID")
    _require(all(type(o) is dict and set(o) == _OCCURRENCE_KEYS and type(o["label"]) is str and
                 _LABEL.fullmatch(o["label"]) is not None and _int_ns(o["issued_at_ns"]) and
                 _int_ns(o["completed_at_ns"]) and type(o["choice"]) is dict for o in occurrences),
             "CASE_OCCURRENCES_INVALID")
    _require(len({o["label"] for o in occurrences}) == len(occurrences), "CASE_OCCURRENCE_LABEL_DUPLICATE")
    if paper is not None:
        _require(type(paper) is dict and set(paper) == _PAPER_KEYS and type(paper["binding"]) is dict and
                 type(paper["manager_draft"]) is dict and type(paper["manager_usage"]) is dict and
                 "request_id" not in paper["manager_draft"] and _int_ns(paper["decision_time_ns"]),
                 "CASE_PAPER_INVALID")


# ------------------------------------------------------------------ prepare


def prepare(case_path: Path, scratch_dir: Path) -> dict:
    scratch = Path(scratch_dir)
    _require(scratch.is_absolute() and not _inside(scratch.resolve(), REPO_ROOT), "SCRATCH_INSIDE_REPOSITORY")
    _require(not scratch.is_symlink() and (not scratch.exists() or (scratch.is_dir() and not any(scratch.iterdir()))),
             "SCRATCH_NOT_EMPTY")
    case_path = Path(case_path)
    raw = case_path.read_bytes() if case_path.is_file() and not case_path.is_symlink() else b""
    _require(0 < len(raw) <= MAX_CASE_BYTES, "CASE_UNREADABLE")
    _require(_SECRET.search(raw.decode("utf-8", "replace")) is None, "SECRET_MATERIAL_REJECTED")
    case = _strict_load(raw, "CASE_JSON_INVALID")
    _require(type(case) is dict, "CASE_JSON_INVALID")
    validate_case(case)
    paths = {}
    for role in SOURCE_ROLES:
        if case["sources"][role] is None:
            continue
        path = Path(case["sources"][role])
        _require(path.is_absolute() and path.is_file() and not path.is_symlink(), "SOURCE_MISSING")
        resolved = path.resolve()
        _require(not _inside(resolved, REPO_ROOT), "SOURCE_INSIDE_REPOSITORY")
        _require(not _inside(resolved, scratch.resolve()), "SOURCE_INSIDE_SCRATCH")
        _require(not ({p.lower() for p in resolved.parts} & _DANGER_PARTS) and
                 not re.search(r"(?i)(oauth|credential|secret|wallet)", resolved.name), "SOURCE_DANGER_PATH")
        _require(not any(Path(str(resolved) + s).exists() for s in ("-wal", "-shm", "-journal")),
                 "SOURCE_SIDECAR_PRESENT")
        paths[role] = resolved
    _require(len(set(paths.values())) == len(paths), "SOURCE_PATH_DUPLICATE")
    (scratch / "inputs").mkdir(parents=True)
    (scratch / "private").mkdir()
    refs = {}
    for role, path in paths.items():
        target = scratch / "inputs" / f"{role}.sqlite3"
        shutil.copyfile(path, target)
        digest = _file_sha(path)
        _require(_file_sha(target) == digest, "SOURCE_COPY_MISMATCH")
        refs[role] = dict(sha256=digest, bytes=target.stat().st_size)
    (scratch / "private" / "case.json").write_bytes(raw)
    _write_once(scratch / "private" / "operator_paths.json", {r: str(p) for r, p in paths.items()})
    prepared = dict(schema_id=PREPARED_SCHEMA, case_label=case["case_label"], proof_level=case["proof_level"],
                    case_sha256=hashlib.sha256(raw).hexdigest(), source_refs=refs)
    _write_once(scratch / "prepared.json", prepared)
    return dict(status="PREPARED", **prepared)


def _load_prepared(scratch: Path) -> tuple[dict, dict]:
    prepared = _read_json(scratch / "prepared.json", "PREPARED_MISSING")
    raw = (scratch / "private" / "case.json").read_bytes() if (scratch / "private" / "case.json").is_file() else b""
    _require(hashlib.sha256(raw).hexdigest() == prepared.get("case_sha256"), "CASE_COPY_TAMPERED")
    case = _strict_load(raw, "CASE_JSON_INVALID")
    validate_case(case)
    for role, ref in prepared["source_refs"].items():
        copy = scratch / "inputs" / f"{role}.sqlite3"
        _require(copy.is_file() and _file_sha(copy) == ref["sha256"], "INPUT_COPY_TAMPERED")
    return prepared, case


def _originals_unchanged(scratch: Path, prepared: dict) -> bool:
    paths = _read_json(scratch / "private" / "operator_paths.json", "PREPARED_MISSING")
    return all(Path(paths[r]).is_file() and _file_sha(Path(paths[r])) == ref["sha256"]
               for r, ref in prepared["source_refs"].items())


# ------------------------------------------------------------------ native composition


def derive_discovery(inputs: Path, discovery: dict, cutoff_ns: int) -> dict:
    """Native ALPHA-02 universe -> triage -> queue, with the exact observed partition."""
    policy_result = AD.build_alpha_discovery_policy(discovery["policy"])
    _require(policy_result.is_valid, "DISCOVERY_POLICY_INVALID")
    policy = policy_result.record
    _require(_iso_ns(discovery["as_of"]) <= cutoff_ns, "DISCOVERY_AFTER_DECISION_CUTOFF")
    pit = inputs / "pit_store.sqlite3"
    current = AD.build_alpha_universe_snapshot(pit, policy, discovery["as_of"])
    _require(current.is_valid, "DISCOVERY_UNIVERSE_INVALID")
    universe = current.record
    _require(len(universe.markets) > 0, "ZERO_OBSERVATIONS")
    prior, changes = None, ()
    if discovery["prior_as_of"] is not None:
        _require(_iso_ns(discovery["prior_as_of"]) < _iso_ns(discovery["as_of"]), "PRIOR_NOT_BEFORE_CURRENT")
        prior_result = AD.build_alpha_universe_snapshot(pit, policy, discovery["prior_as_of"])
        _require(prior_result.is_valid, "DISCOVERY_UNIVERSE_INVALID")
        prior = prior_result.record
        compared = AD.compare_alpha_universes(prior, universe, policy)
        _require(compared.is_valid, "DISCOVERY_COMPARISON_INVALID")
        changes = tuple(compared.records)
    registry_path = None
    if discovery["alpha_memory_temporal_posture"] != "HISTORICAL_AVAILABILITY_UNPROVEN":
        registry_path = (inputs / "alpha_registry.sqlite3").resolve()
    bases = AD.build_pre_allocation_triage_bases(
        universe, policy, analysis_temporal_mode=discovery["analysis_temporal_mode"],
        alpha_memory_temporal_posture=discovery["alpha_memory_temporal_posture"],
        alpha_registry_path=registry_path, prior=prior, material_changes=changes)
    _require(bases.is_valid, (bases.error_codes or ("DISCOVERY_TRIAGE_INVALID",))[0])
    queue_result = AD.allocate_and_finalize_research_queue(universe, policy, bases.records, prior=prior)
    _require(queue_result.is_valid, "DISCOVERY_QUEUE_INVALID")
    queue, decisions = queue_result.record, tuple(queue_result.records[:-1])
    by_triage = {d.market_triage_decision_id: d for d in decisions}
    placed = [t for lane in _LANES for t in getattr(queue, lane)]
    markets = sorted(m.market_id for m in universe.markets)
    _require(sorted(placed) == sorted(queue.all_triage_ids) == sorted(by_triage) and
             sorted(by_triage[t].market_id for t in placed) == markets, "QUEUE_PARTITION_INVALID")
    return dict(universe=universe, queue=queue, decisions=decisions, by_triage=by_triage, summary=dict(
        policy_id=policy.alpha_discovery_policy_id, universe_id=universe.alpha_universe_snapshot_id,
        prior_universe_id=prior.alpha_universe_snapshot_id if prior else None,
        material_change_count=len(changes), as_of=universe.as_of, cutoff_mode=universe.cutoff_mode,
        coverage_scope=universe.coverage_scope, external_universe_completeness=universe.external_universe_completeness,
        analysis_temporal_mode=queue.analysis_temporal_mode, alpha_memory_temporal_posture=queue.alpha_memory_temporal_posture,
        alpha_registry_head=queue.alpha_registry_head_entry_hash, queue_id=queue.alpha_research_queue_snapshot_id,
        observed_market_count=len(markets),
        partition={lane.replace("_triage_ids", ""): len(getattr(queue, lane)) for lane in _LANES},
        prior_only_market_count=len(queue.prior_only_market_ids)))


def derive_menu(inputs: Path, discovery: dict) -> dict:
    """Selected queue rows -> exact canonical memberships; nothing guessed, nothing dropped."""
    life = load_strategy_lifecycle_store(inputs / "lifecycle_store.sqlite3")
    _require(life.snapshot is not None, "LIFECYCLE_STORE_INVALID")
    lifecycle = life.snapshot
    hermes = sm.load_hermes_strategy_manager_store(inputs / "hermes_manager_store.sqlite3")
    registry = AFR.load_and_verify_alpha_factory_registry(inputs / "alpha_registry.sqlite3")
    _require(registry.is_valid, "ALPHA_REGISTRY_INVALID")
    candidates = {e.record.candidate_id: e.record for e in registry.snapshot.entries
                  if type(e.record) is OpportunityCandidate}
    markets = {m.market_id: m for m in discovery["universe"].markets}
    queue, by_triage = discovery["queue"], discovery["by_triage"]
    selected = [t for lane in _LANES[:3] for t in getattr(queue, lane)]
    rows, members, exclusions, seen, seen_versions = [], [], [], set(), set()
    for triage_id in sorted(by_triage, key=lambda t: by_triage[t].market_id):
        d = by_triage[triage_id]
        rows.append(dict(market_id=d.market_id, final_disposition=d.final_disposition, selected_lane=d.selected_lane,
                         priority_class=d.priority_class, matched_candidate_count=len(d.matched_candidate_ids),
                         menu_status="NOT_SELECTED" if d.selected_lane is None else (
                             "RESEARCH_NEEDED" if not d.matched_candidate_ids else "CANDIDATES_EVALUATED")))
    for triage_id in selected:  # native lane order (core, exploration, audit), then exact ids
        d = by_triage[triage_id]
        market = markets[d.market_id]
        for candidate_id in sorted(d.matched_candidate_ids):
            def exclude(code, version_id=None, market_id=d.market_id, candidate_id=candidate_id):
                exclusions.append(dict(market_id=market_id, candidate_id=candidate_id,
                                       strategy_version_id=version_id, status=code))
            if candidate_id in seen:
                exclude("DUPLICATE_CANDIDATE"); continue
            seen.add(candidate_id)
            candidate = candidates.get(candidate_id)
            gamma = _GAMMA_MARKET.fullmatch(d.market_id)
            tokens = sorted(set(getattr(candidate, "subject_refs", ())) & set(market.token_ids))
            versions = sorted((v for v in lifecycle.strategy_versions if candidate_id in v.evidence_refs),
                              key=lambda v: v.strategy_version_id)
            if candidate is None:
                exclude("CANDIDATE_NOT_IN_REGISTRY"); continue
            if gamma is None or not market.condition_id:
                exclude("MARKET_IDENTITY_UNVERIFIED"); continue
            if len(tokens) != 1 or _TOKEN.fullmatch(tokens[0]) is None:
                exclude("TOKEN_LINK_UNVERIFIED"); continue
            if not versions:
                exclude("NO_ELIGIBLE_STRATEGY"); continue
            for version in versions:
                if version.strategy_version_id in seen_versions:
                    exclude("DUPLICATE_STRATEGY_VERSION", version.strategy_version_id); continue
                seen_versions.add(version.strategy_version_id)
                if hermes.latest_assessment_id(version.strategy_version_id) is None:
                    exclude("NO_HERMES_ASSESSMENT", version.strategy_version_id); continue
                if len(members) >= MENU_LIMIT:
                    exclude("MENU_CAPACITY_OVERFLOW", version.strategy_version_id); continue
                members.append(dict(candidate_id=candidate_id, strategy_version_id=version.strategy_version_id,
                                    gamma_market_id=gamma.group(1), condition_id=market.condition_id,
                                    token_id=_TOKEN.fullmatch(tokens[0]).group(1)))
    return dict(members=members, summary=dict(
        lifecycle_head=lifecycle.store_head_entry_hash, hermes_head=hermes.store_head_entry_hash,
        alpha_registry_head=registry.snapshot.head_entry_hash, menu_size=len(members),
        menu_sha256=cycle._digest(list(members)) if members else None,
        status="VERIFIED_MENU" if members else "NO_ELIGIBLE_STRATEGY",
        market_rows=rows, exclusions=exclusions,
        research_needed_count=sum(r["menu_status"] == "RESEARCH_NEEDED" for r in rows),
        overflow_count=sum(e["status"] == "MENU_CAPACITY_OVERFLOW" for e in exclusions)))


class _EchoDraftBackend(FakeHermesBackend):
    """FakeHermesBackend answering every manager request with the case's fixed draft."""

    def __init__(self, draft: dict, usage: dict):
        self._draft, self._usage = draft, canonical(usage)
        super().__init__([self._outcome(b"{}")])

    def _outcome(self, stdout: bytes) -> HermesInvocationOutcome:
        return HermesInvocationOutcome(stdout=stdout, stdout_truncated=False, stderr_byte_len=0,
                                       stderr_truncated=False, usage_file_bytes=self._usage,
                                       usage_file_truncated=False, exit_code=0, timed_out=False,
                                       launch_failed=False, duration_ms=1)

    def invoke(self, **kwargs):
        self.call_count += 1
        argv = kwargs["argv"]
        envelope = json.loads(argv[argv.index("-z") + 1])
        return self._outcome(json.dumps(dict(self._draft, request_id=envelope["request_id"])).encode())


class _NoDispatchBackend:
    """Verify-time Stage B backend: any dispatch is a fresh attempt and fails verification."""

    def _dispatch(self, *_args, **_kwargs):
        raise ProofStop("VERIFY_FRESH_DISPATCH_ATTEMPTED")


def _venue_snapshots(decision: dict) -> tuple:
    out = []
    for v in decision["venue_snapshots"]:
        out.append(venue.build_public_venue_snapshot(
            gamma_market_id=v["gamma_market_id"], condition_id=v["condition_id"], token_id=v["token_id"],
            acquisition_started_ns=v["acquisition_started_ns"], acquisition_completed_ns=v["acquisition_completed_ns"],
            gamma=venue.SourceFetchResult("BODY", canonical(v["gamma_document"])),
            clob=venue.SourceFetchResult("BODY", canonical(v["clob_document"]))))
    return tuple(out)


def _cycle_args(scratch: Path, case: dict, menu: list, ordinal: int, occurrence: dict, backend, paper_feedback):
    decision, inputs = case["decision"], scratch / "inputs"
    return dict(journal_dir=scratch / "journal" / f"occ-{ordinal}", surface_report=decision["surface_report"],
                backend=backend, model_label=decision["model_label"], candidate_menu=menu,
                lifecycle_store_path=inputs / "lifecycle_store.sqlite3",
                hermes_manager_store_path=scratch / "work" / "hermes_manager_store.sqlite3",
                alpha_registry_path=inputs / "alpha_registry.sqlite3", venue_snapshots=_venue_snapshots(decision),
                information_cutoff_ns=decision["information_cutoff_ns"], issued_at_ns=occurrence["issued_at_ns"],
                evaluated_at_ns=decision["evaluated_at_ns"], deadline_ns=decision["deadline_ns"],
                paper_feedback=paper_feedback)


def _paper_feedback(scratch: Path, case: dict) -> dict | None:
    paper = case["paper"]
    if paper is None:
        return None
    binding = build_research_strategy_binding(**{k: tuple(v) if type(v) is list else v
                                                 for k, v in paper["binding"].items()})
    clock_at = datetime.fromisoformat(paper["manager_clock_utc"].replace("Z", "+00:00"))
    return dict(paper_store_path=scratch / "inputs" / "paper_store.sqlite3", expected_binding=binding,
                lifecycle_snapshot=load_strategy_lifecycle_store(scratch / "inputs" / "lifecycle_store.sqlite3").snapshot,
                strategy_version_id=paper["strategy_version_id"], information_cutoff=paper["information_cutoff"],
                decision_time_ns=paper["decision_time_ns"], backend=_EchoDraftBackend(paper["manager_draft"], paper["manager_usage"]),
                hermes_manager_store_path=scratch / "work" / "hermes_manager_store.sqlite3",
                provider_label=paper["provider_label"], model_label=paper["model_label"], clock=lambda: clock_at)


def terminal_class(bundle: dict) -> str:
    """Closed mapping of one native cycle bundle; anything unrecognised is a rejection."""
    outcome, status = bundle.get("outcome"), bundle.get("auto01_status")
    if outcome == "ELIGIBLE_PREVIEW":
        return "COMPLETED_PREVIEW"
    if status == "NO_TRADE" and outcome in ("NO_TRADE", "PAUSE", "REASSESS"):
        return "ABSTAINED_" + outcome
    if outcome == "INTERRUPTED_BLOCKED":
        return "INTERRUPTED_OR_UNKNOWN"
    if status == "INCONCLUSIVE" or (status is None and outcome == bundle.get("stage_b_status") and
                                    outcome not in (None, stage_b.VALID_OUTPUT)):
        return "INCONCLUSIVE"  # no admissible decision came back (provider/schema/tool failure)
    return "REJECTED"


def feedback_class(bundle: dict, klass: str) -> str:
    if klass == "INTERRUPTED_OR_UNKNOWN":
        return "NO_TERMINAL_DECISION"
    feedback = bundle.get("paper_feedback")
    if feedback is None:
        return "NO_PAPER_SESSION"
    if feedback.get("decision_linkage") == "DECISION_LINKED" and feedback.get("status") == "ASSESSED":
        return "DECISION_LINKED_NONCAUSAL"
    if feedback.get("status") == "DEFERRED_NOT_DECISION_LINKED":
        return "NOT_APPLICABLE_FEEDBACK" if klass.startswith("ABSTAINED_") else "DEFERRED"
    return "REJECTED_" + str(feedback.get("reason_code") or feedback.get("status"))


def _occurrence_row(ordinal: int, occurrence_id: str, label: str, bundle: dict | None) -> dict:
    if bundle is None:  # STARTED with no terminal: crashed before the native cycle returned
        return dict(ordinal=ordinal, occurrence_id=occurrence_id, label=label, terminal_class="INTERRUPTED_OR_UNKNOWN",
                    feedback_class="NO_TERMINAL_DECISION", bundle_id=None, request_id=None, stage_b_status=None,
                    auto01_receipt_id=None, outcome=None, linked_candidate_id=None, linked_strategy_version_id=None,
                    paper_snapshot_id=None, assessment_id=None, run_record_id=None)
    klass = terminal_class(bundle)
    feedback = bundle.get("paper_feedback") or {}
    return dict(ordinal=ordinal, occurrence_id=occurrence_id, label=label, terminal_class=klass,
                feedback_class=feedback_class(bundle, klass), bundle_id=bundle.get("bundle_id"),
                request_id=bundle.get("request_id"), stage_b_status=bundle.get("stage_b_status"),
                auto01_receipt_id=bundle.get("auto01_receipt_id"), outcome=bundle.get("outcome"),
                linked_candidate_id=feedback.get("linked_candidate_id"),
                linked_strategy_version_id=feedback.get("linked_strategy_version_id"),
                paper_snapshot_id=feedback.get("paper_snapshot_id"), assessment_id=feedback.get("assessment_id"),
                run_record_id=feedback.get("run_record_id"))


def denominators(rows: list, not_attempted: int) -> dict:
    classes = sorted({r["terminal_class"] for r in rows})
    interrupted = sum(r["terminal_class"] == "INTERRUPTED_OR_UNKNOWN" for r in rows)
    return dict(attempted=len(rows), completed=len(rows) - interrupted, interrupted_or_unknown=interrupted,
                not_attempted=not_attempted, by_terminal_class={c: sum(r["terminal_class"] == c for r in rows) for c in classes},
                feedback_linked=sum(r["feedback_class"] == "DECISION_LINKED_NONCAUSAL" for r in rows),
                feedback_not_applicable=sum(r["feedback_class"] == "NOT_APPLICABLE_FEEDBACK" for r in rows))


def _paper_summary(scratch: Path, case: dict) -> dict:
    if case["paper"] is None:
        return dict(status="UNAVAILABLE", reason="NO_RESEARCH_PAPER_SESSION")
    try:
        with bridge.PaperStore(scratch / "inputs" / "paper_store.sqlite3") as store:
            snap = bridge.build_research_paper_performance_snapshot(store)
    except Exception:
        return dict(status="UNAVAILABLE", reason="PAPER_STORE_INVALID")
    return dict(status="RESEARCH_PAPER_OBSERVED", evidence_class="RESEARCH_PAPER_SIMULATED", snapshot_id=snap.snapshot_id,
                binding_id=snap.binding_id, candidate_id=snap.candidate_id, event_sequence=snap.paper_store_event_sequence,
                event_head=snap.paper_store_event_head, state_hash=snap.paper_store_state_hash,
                observation_start_ns=snap.observation_start_ns, observation_end_ns=snap.observation_end_ns,
                intent_count=snap.intent_count, order_count=snap.order_count, fill_count=snap.fill_count,
                zero_fill=snap.fill_count == 0, risk_deny_count=snap.risk_deny_count, fee_total=snap.fee_total,
                spread_cost_total=snap.spread_cost_total, slippage_total=snap.depth_slippage_cost_total,
                pending_markout_count=snap.pending_markout_count, realized_paper_pnl=snap.realized_paper_pnl,
                unrealized_paper_pnl=snap.unrealized_paper_pnl if snap.unrealized_paper_pnl is not None else "UNKNOWN_MISSING_MARKS",
                gapped_asset_count=snap.gapped_asset_count, pnl_basis="CUMULATIVE_SESSION",
                window_delta="NOT_COMPUTED_SINGLE_SNAPSHOT", real_venue=False, qualification_claim=False)


def manager_updates(scratch: Path) -> int | None:
    """PERFORMANCE_UPDATE runs this proof added to the scratch manager store (orphans included)."""
    work = scratch / "work" / "hermes_manager_store.sqlite3"
    if not work.is_file():
        return None
    count = lambda path: sum(r.trigger == "PERFORMANCE_UPDATE"  # noqa: E731
                             for r in sm.load_hermes_strategy_manager_store(path).run_records)
    return count(work) - count(scratch / "inputs" / "hermes_manager_store.sqlite3")


def _assemble(prepared: dict, case: dict, *, discovery=None, menu=None, rows=(), not_attempted=0, paper=None,
              blocked_code=None, network_attempts=0, manager_update_count=None) -> dict:
    rows = list(rows)
    linked = any(r["feedback_class"] == "DECISION_LINKED_NONCAUSAL" for r in rows)
    conclusion = "BLOCKED" if blocked_code else ("VERIFIED_OUTCOME_FEEDBACK_OBSERVED" if linked else "PLUMBING_ONLY")
    body = dict(
        schema_id=MANIFEST_SCHEMA, case_label=prepared["case_label"], case_sha256=prepared["case_sha256"],
        proof_level=prepared["proof_level"], source_refs=prepared["source_refs"],
        discovery=discovery, menu=menu, occurrences=rows, denominators=denominators(rows, not_attempted),
        paper=paper, manager_performance_updates=manager_update_count, conclusion=conclusion, blocked_code=blocked_code,
        clocks=dict(decision_clock_class="CALLER_SUPPLIED", current_venue_freshness_claimed=False,
                    information_cutoff_ns=case["decision"]["information_cutoff_ns"]),
        authority=dict(real_provider=stage_b.REAL_PROVIDER_NOT_INVOKED, model_origin_proof=fb.MODEL_ORIGIN,
                       network_attempts=network_attempts, no_order=True, no_live=True, no_policy_mutation=True,
                       causal_claim=False, alpha_claim=False, external_universe_completeness_claimed=False),
        limitations=["observed universe only; external Polymarket completeness unproven",
                     "offline injected Stage B; model origin unverified",
                     "FakeHermesBackend manager feedback; simulated research paper, not a venue",
                     "DECISION_LINKED is an identity relation, not causation"])
    manifest = dict(body, manifest_id=MANIFEST_PREFIX + _sha(body))
    text = canonical(manifest).decode()
    _require(len(text) <= MAX_MANIFEST_BYTES, "MANIFEST_TOO_LARGE")
    _require(_ABSOLUTE.search(text) is None and _SECRET.search(text) is None, "MANIFEST_NOT_SANITIZED")
    return manifest


# ------------------------------------------------------------------ run


def run(scratch_dir: Path) -> dict:
    scratch = Path(scratch_dir)
    prepared, case = _load_prepared(scratch)
    manifest_path = scratch / "manifest.json"
    if manifest_path.exists():  # finite: a second run is a replay of the stored result
        return dict(verify(scratch), replay=True)
    _require(_originals_unchanged(scratch, prepared), "SOURCE_CHANGED_SINCE_PREPARE")
    for name in ("work", "ledger", "journal"):
        (scratch / name).mkdir(exist_ok=True)
    work_manager = scratch / "work" / "hermes_manager_store.sqlite3"
    if not work_manager.exists():
        shutil.copyfile(scratch / "inputs" / "hermes_manager_store.sqlite3", work_manager)
    decision = case["decision"]
    with no_network() as attempts:
        try:
            discovery = _checked(derive_discovery, scratch / "inputs", case["discovery"],
                                 decision["information_cutoff_ns"], code="DISCOVERY_INPUT_INVALID")
            menu = _checked(derive_menu, scratch / "inputs", discovery, code="MENU_STORE_INVALID")
            _checked(_venue_snapshots, decision, code="VENUE_SNAPSHOT_INVALID")
            _checked(_paper_feedback, scratch, case, code="PAPER_BINDING_INVALID")
        except ProofStop as stop:
            manifest = _assemble(prepared, case, blocked_code=str(stop), network_attempts=len(attempts))
            _write_once(manifest_path, manifest)
            return manifest
        rows, not_attempted, members = [], 0, menu["members"]
        for ordinal, occurrence in enumerate(decision["occurrences"], 1):
            occurrence_id = OCCURRENCE_PREFIX + _sha([prepared["case_sha256"], ordinal, occurrence["label"]])
            started, terminal = (scratch / "ledger" / f"occ-{ordinal}.{kind}.json" for kind in ("started", "terminal"))
            if not members:
                not_attempted += 1
                continue
            if terminal.exists():
                rows.append(_read_json(terminal, "LEDGER_TAMPERED")["row"]); continue
            if started.exists():  # crashed after STARTED: classify once, never redispatch
                row = _occurrence_row(ordinal, occurrence_id, occurrence["label"], None)
                _write_once(terminal, dict(row=row, bundle=None)); rows.append(row); continue
            _write_once(started, dict(occurrence_id=occurrence_id, ordinal=ordinal, label=occurrence["label"],
                                      issued_at_ns=occurrence["issued_at_ns"], state="STARTED"))
            try:
                request_id = fb.cycle_request(
                    surface_report=decision["surface_report"], candidate_menu=members,
                    information_cutoff_ns=decision["information_cutoff_ns"], issued_at_ns=occurrence["issued_at_ns"],
                    deadline_ns=decision["deadline_ns"], model_label=decision["model_label"]).request_id
            except ValueError:
                request_id = None  # run_one_cycle records the typed request rejection itself
            canned = {} if request_id is None else {request_id: dict(
                model=decision["model_label"], content=json.dumps(occurrence["choice"]),
                completed_at_ns=occurrence["completed_at_ns"])}
            try:
                bundle = fb.run_one_cycle(**_cycle_args(scratch, case, members, ordinal, occurrence,
                                                        stage_b.OfflineStageBBackend(canned), _paper_feedback(scratch, case)))
            except Exception:
                if not attempts:
                    raise  # an unexplained native failure is a crash: rerun classifies it once
                bundle = None  # network guard tripped mid-occurrence: terminal, then stop
            row = _occurrence_row(ordinal, occurrence_id, occurrence["label"], bundle)
            _write_once(terminal, dict(row=row, bundle=bundle))
            rows.append(row)
            if attempts:
                break
        paper = _paper_summary(scratch, case)
    blocked = None
    if attempts:
        blocked = "NETWORK_ATTEMPT_BLOCKED"
    elif not _originals_unchanged(scratch, prepared):
        blocked = "SOURCE_MUTATED"
    elif any(_file_sha(scratch / "inputs" / f"{r}.sqlite3") != ref["sha256"] for r, ref in prepared["source_refs"].items()):
        blocked = "INPUT_COPY_MUTATED"
    manifest = _assemble(prepared, case, discovery=discovery["summary"], menu=dict(menu["summary"], members=members),
                         rows=rows, not_attempted=not_attempted, paper=paper, blocked_code=blocked,
                         network_attempts=len(attempts), manager_update_count=manager_updates(scratch))
    _write_once(manifest_path, manifest)
    return manifest


def _checked(function, *args, code: str):
    try:
        return function(*args)
    except ProofStop:
        raise
    except Exception:
        raise ProofStop(code) from None


# ------------------------------------------------------------------ verify


def verify(scratch_dir: Path) -> dict:
    """Cold re-derivation from the frozen copies; never a second decision or manager call."""
    scratch = Path(scratch_dir)
    try:
        prepared, case = _load_prepared(scratch)
        manifest = _read_json(scratch / "manifest.json", "MANIFEST_MISSING", MAX_MANIFEST_BYTES)
        body = {k: v for k, v in manifest.items() if k != "manifest_id"}
        _require(manifest.get("manifest_id") == MANIFEST_PREFIX + _sha(body), "MANIFEST_TAMPERED")
        _require(manifest["schema_id"] == MANIFEST_SCHEMA and manifest["conclusion"] in CONCLUSIONS, "MANIFEST_TAMPERED")
        _require((manifest["case_sha256"], manifest["source_refs"]) == (prepared["case_sha256"], prepared["source_refs"]),
                 "MANIFEST_SOURCE_MISMATCH")
        decision = case["decision"]
        with no_network() as attempts:
            if manifest["blocked_code"] is None:
                discovery = derive_discovery(scratch / "inputs", case["discovery"], decision["information_cutoff_ns"])
                menu = derive_menu(scratch / "inputs", discovery)
                _require(discovery["summary"] == manifest["discovery"], "DISCOVERY_REPLAY_MISMATCH")
                _require(dict(menu["summary"], members=menu["members"]) == manifest["menu"], "MENU_REPLAY_MISMATCH")
                rows = _verify_occurrences(scratch, case, prepared, menu["members"], manifest)
                _require(_paper_summary(scratch, case) == manifest["paper"], "PAPER_REPLAY_MISMATCH")
                not_attempted = len(decision["occurrences"]) if not menu["members"] else 0
                _require(denominators(rows, not_attempted) == manifest["denominators"], "DENOMINATOR_MISMATCH")
                _require(manager_updates(scratch) == manifest["manager_performance_updates"], "MANAGER_UPDATE_MISMATCH")
            else:  # a blocked proof is verified as a record only; nothing is re-derived from it
                _require(manifest["conclusion"] == "BLOCKED", "CONCLUSION_MISMATCH")
        _require(not attempts, "NETWORK_ATTEMPT_BLOCKED")
        linked = any(r["feedback_class"] == "DECISION_LINKED_NONCAUSAL" for r in manifest["occurrences"])
        expected = "BLOCKED" if manifest["blocked_code"] else (
            "VERIFIED_OUTCOME_FEEDBACK_OBSERVED" if linked else "PLUMBING_ONLY")
        _require(manifest["conclusion"] == expected, "CONCLUSION_MISMATCH")
        return dict(status="VERIFIED", manifest_id=manifest["manifest_id"], conclusion=manifest["conclusion"],
                    denominators=manifest["denominators"], fresh_attempts=0,
                    originals_unchanged=_originals_unchanged(scratch, prepared))
    except ProofStop as stop:
        return dict(status="VERIFY_FAILED", reason_code=str(stop), fresh_attempts=0)
    except Exception:
        return dict(status="VERIFY_FAILED", reason_code="VERIFY_INPUT_INVALID", fresh_attempts=0)


def _verify_occurrences(scratch: Path, case: dict, prepared: dict, members: list, manifest: dict) -> list:
    rows, decision = [], case["decision"]
    for ordinal, occurrence in enumerate(decision["occurrences"], 1):
        started, terminal = (scratch / "ledger" / f"occ-{ordinal}.{kind}.json" for kind in ("started", "terminal"))
        if not members:
            _require(not started.exists() and not terminal.exists(), "LEDGER_UNEXPECTED_OCCURRENCE")
            continue
        _require(started.is_file() and terminal.is_file(), "LEDGER_INCOMPLETE")
        record = _read_json(terminal, "LEDGER_TAMPERED")
        occurrence_id = OCCURRENCE_PREFIX + _sha([prepared["case_sha256"], ordinal, occurrence["label"]])
        _require(_read_json(started, "LEDGER_TAMPERED").get("occurrence_id") == occurrence_id, "LEDGER_TAMPERED")
        bundle = record.get("bundle")
        if bundle is not None:
            digest = fb.CYCLE_PREFIX + fb._digest({k: v for k, v in bundle.items() if k != "bundle_id"})
            _require(bundle.get("bundle_id") == digest, "BUNDLE_TAMPERED")
            if any((scratch / "journal" / f"occ-{ordinal}").glob("cycle-*.json")):
                replay = fb.run_one_cycle(**_cycle_args(scratch, case, members, ordinal, occurrence,
                                                        _NoDispatchBackend(), None))
                _require(replay == bundle, "JOURNAL_REPLAY_MISMATCH")
            _verify_feedback(scratch, case, bundle)
        row = _occurrence_row(ordinal, occurrence_id, occurrence["label"], bundle)
        _require(row == record.get("row"), "LEDGER_TAMPERED")
        rows.append(row)
    _require(rows == manifest["occurrences"], "OCCURRENCE_MISMATCH")
    return rows


def _verify_feedback(scratch: Path, case: dict, bundle: dict) -> None:
    feedback = bundle.get("paper_feedback") or {}
    if feedback.get("decision_linkage") != "DECISION_LINKED" or feedback.get("status") != "ASSESSED":
        return
    store = sm.load_hermes_strategy_manager_store(scratch / "work" / "hermes_manager_store.sqlite3")
    run_record = next((r for r in store.run_records if r.run_record_id == feedback["run_record_id"]), None)
    assessment = next((a for a in store.assessments if a.assessment_id == feedback["assessment_id"]), None)
    _require(run_record is not None and assessment is not None and run_record.trigger == "PERFORMANCE_UPDATE" and
             run_record.trigger_ref == feedback["paper_snapshot_id"] and feedback["evidence_id"] in assessment.input_evidence_refs,
             "FEEDBACK_REPLAY_MISMATCH")
    _require(feedback["linked_candidate_id"] == case["paper"]["binding"]["candidate_id"], "FEEDBACK_REPLAY_MISMATCH")
    with bridge.PaperStore(scratch / "inputs" / "paper_store.sqlite3") as paper:
        _require(bridge.build_research_paper_performance_snapshot(paper).snapshot_id == feedback["paper_snapshot_id"],
                 "FEEDBACK_REPLAY_MISMATCH")


# ------------------------------------------------------------------ CLI


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    first = sub.add_parser("prepare")
    first.add_argument("--case", required=True, type=Path)
    first.add_argument("--scratch-dir", required=True, type=Path)
    for name in ("run", "verify"):
        sub.add_parser(name).add_argument("--scratch-dir", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "prepare":
            result = prepare(args.case, args.scratch_dir)
        elif args.command == "run":
            result = run(args.scratch_dir)
        else:
            result = verify(args.scratch_dir)
    except ProofStop as stop:
        result = dict(status="STOPPED", reason_code=str(stop))
    except FileExistsError:
        result = dict(status="STOPPED", reason_code="WRITE_ONCE_CONFLICT")
    summary = {k: result.get(k) for k in ("status", "reason_code", "manifest_id", "conclusion", "blocked_code",
                                          "denominators", "fresh_attempts", "replay") if k in result}
    print(json.dumps(summary, sort_keys=True))
    ok = result.get("status") in ("PREPARED", "VERIFIED") or (
        args.command == "run" and result.get("conclusion") in CONCLUSIONS[:2])
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
