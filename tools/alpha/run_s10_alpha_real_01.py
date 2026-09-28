"""Manual foreground operator for S10-ALPHA-REAL-01 (first real non-wallet Alpha seed).

Frozen package: ``docs/wp_specs/S10-ALPHA-REAL-01/`` and
``docs/alpha_real_non_wallet_seed_contract.md``.

Every command is zero-network except ``run-real``, which performs at most ONE controlled
Hermes v0.21.3 public-web research-child launch through the merged
``run_controlled_hermes_research`` (context mode off) and only after the separate runtime
activation. The operator writes only beneath ``local_data/s10_alpha_real_01/attempt-01/``.

Exact command grammar (always run from the repository root):

  prepare
  verify-local
  run-real            --envelope-sha256 HEX64
                      --acknowledgement I_AUTHORIZE_EXACT_S10_ALPHA_REAL_01_RUNTIME_ENVELOPE
                      --credential-setup-confirmation
                          I_CONFIRM_S10_ALPHA_REAL_01_HERMES_HOME_CREDENTIAL_SETUP_COMPLETE
  verify-run
  build-review-bundle
  verify-review
  finalize-alpha
  verify-final

The Hermes executable and research home are pinned constants; there is no command-line
override. The operator never reads, creates, edits or echoes credential content, never
creates the research home, has no scheduler, no automatic retry and no second attempt.
Console output is closed codes, ids and digests only.
"""

from __future__ import annotations

import argparse
import dataclasses
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Callable, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.data_layer.analytical_research.alpha_factory import (  # noqa: E402
    HypothesisFamily,
    OpportunityCandidate,
    ResearchEpisode,
    ResearchSourceReference,
    build_hypothesis_family,
    build_opportunity_candidate,
    build_research_episode,
    build_research_source_reference,
)
from src.data_layer.analytical_research.alpha_factory_registry import (  # noqa: E402
    append_alpha_factory_records,
    initialize_alpha_factory_registry,
    load_and_verify_alpha_factory_registry,
)
from src.research_runtime.hermes_controlled_runtime import (  # noqa: E402
    DEFAULT_HERMES_INVOCATION_POLICY,
    NON_AUTHORITY_NOTICE,
    ExternalHermesCliBackend,
    build_research_run_request,
    build_version_argv,
    capture_final_response,
    is_clean_research_home_control_plane,
    is_safe_research_home,
    is_supported_hermes_version,
    run_controlled_hermes_research,
    validate_research_draft,
)
from src.research_runtime.hermes_controlled_runtime.controller import (  # noqa: E402
    _STARTUP_PROBE_MAX_BYTES,
    _STARTUP_PROBE_MAX_SECONDS,
    _VERSION_PROBE_MAX_BYTES,
    _VERSION_PROBE_MAX_SECONDS,
    build_startup_argv,
)
from src.research_runtime.hermes_controlled_runtime.models import (  # noqa: E402
    DRAFT_LIST_FIELDS,
    REQUEST_SCHEMA_VERSION,
    canonical_json_bytes,
)
from src.research_runtime.hermes_controlled_runtime.policy import (  # noqa: E402
    PolicyBroadeningError,
    validate_executable_path,
)


# ── Frozen package identity ───────────────────────────────────────────────────

WP_ID = "S10-ALPHA-REAL-01"
BASE_SHA = "f74e183a514d21a28013bf433c79126a68c72389"
PINNED_BRANCH = "claude/s10-alpha-real-01-seed-746777"
PINNED_HERMES_EXECUTABLE = r"C:\Users\dersu\polymarket-h1-runtime\hermes-agent-v0.21.3\.venv\Scripts\hermes.exe"
PINNED_HERMES_HOME = r"C:\Users\dersu\polymarket-alpha-real-01\hermes-home"
HERMES_VERSION = "0.21.3"
EXPECTED_POLICY_ID = (
    "hermesinvocationpolicy:sha256:18b8f788fa436712b377c81b10bdbd594cdb7afb3844fcc8559fde3b28c25e81"
)
EXPECTED_REQUEST_ID = (
    "hermesresearchrequest:sha256:efca8c27a92b32282cac6bee0a7a6d2455da590bdc54f6b883bfc16308bfdf2d"
)
EXPECTED_CANDIDATE_ID = "alphacandidate:sha256:2d1523c8086acf536ad07512e1eaffed9cb9405b65e83c87b89b40ba77ee3add"
EXPECTED_FAMILY_ID = "alphafamily:sha256:136000bd56f2fc27cf490cf675ddf2715b0acfc1ee934aa5cdf2579925c208d8"
RUNTIME_ACKNOWLEDGEMENT = "I_AUTHORIZE_EXACT_S10_ALPHA_REAL_01_RUNTIME_ENVELOPE"
CREDENTIAL_SETUP_CONFIRMATION = "I_CONFIRM_S10_ALPHA_REAL_01_HERMES_HOME_CREDENTIAL_SETUP_COMPLETE"
SUCCESS_TERMINAL_STATUS = "RESEARCH_DRAFT_VALIDATED"

WORKSPACE_PARTS = ("local_data", "s10_alpha_real_01", "attempt-01")
WORKSPACE_TEXT = "local_data/s10_alpha_real_01/attempt-01"
REGISTRY_FILENAME = "alpha_registry.sqlite3"
REGISTRY_TEXT = WORKSPACE_TEXT + "/" + REGISTRY_FILENAME
INVENTORY_FILENAME = "ALPHA_REAL_01_PREPARE_INVENTORY.json"
ENVELOPE_FILENAME = "ALPHA_REAL_01_RUNTIME_ACTIVATION_ENVELOPE.json"
SENTINEL_FILENAME = "ALPHA_REAL_01_ATTEMPT_SENTINEL.json"
RUNTIME_RESULT_FILENAME = "ALPHA_REAL_01_RUNTIME_RESULT.json"
PROJECTION_FILENAME = "ALPHA_REAL_01_FULL_DRAFT_PROJECTION.json"
BUNDLE_FILENAME = "ALPHA_REAL_01_REVIEW_BUNDLE.json"
DECISION_FILENAME = "ALPHA_REAL_01_SIDE13_REVIEW_DECISION.json"
FINAL_EVIDENCE_FILENAME = "ALPHA_REAL_01_FINAL_EVIDENCE.json"
WORKSPACE_FILENAMES = frozenset({
    INVENTORY_FILENAME, ENVELOPE_FILENAME, SENTINEL_FILENAME, RUNTIME_RESULT_FILENAME,
    PROJECTION_FILENAME, BUNDLE_FILENAME, DECISION_FILENAME, REGISTRY_FILENAME,
    FINAL_EVIDENCE_FILENAME,
})
PROTECTED_EVIDENCE_DIRS = ("s10_gate_af1", "s10_gate_h1")
MAX_INVENTORY_FILES = 50_000
ALPHA_REGISTRY_APPLICATION_ID = 1464877425
SQLITE_HEADER = b"SQLite format 3\x00"

# ── Frozen research request (Section 4) ───────────────────────────────────────

RESEARCH_QUESTION = "Are contract-specific official NWS precipitation forecasts and observations for Polymarket daily-rain markets sufficiently repeatable, point-in-time observable and falsifiable to justify later deterministic testing of whether public non-market weather information adds predictive information beyond contemporaneous Polymarket market probability?"
RESEARCH_OBJECTIVE = "Using only public web sources, assess the research question across: repeatability of market and rule structure; designated station, report and source semantics; source publication and public-availability timing; historical data availability; a falsifiable mechanism for public-weather information versus market probability; leakage and point-in-time threats; contradictory evidence and reasons the mechanism may fail; sample and data limitations; and exact evidence still needed before any out-of-sample study. Report evidence for and against, uncertainties, known missing data, falsification checks performed, limitations, what would change the conclusion and suggested next research steps. Do not estimate any current market probability, do not recommend any side, entry, exit or size, do not estimate returns and do not claim profitability."
PUBLIC_MARKET_CONTEXT = "Research program scope: Polymarket daily-rain and precipitation markets that resolve on official US National Weather Service (NWS) reports, studied as a market family. No specific live market, event, token or wallet identifier is in scope. Contract rules may name a designated weather station, an official NWS or NOAA climate report as the resolution source, and a local-day measurement window. Public Polymarket rule and market web pages may be read only as untrusted public evidence."
MAX_SOURCES = 12
MAX_OUTPUT_BYTES = 1_000_000


def request_literals() -> dict[str, object]:
    """The exact Section 4 request mapping (notice resolved to the merged constant)."""
    return {
        "schema_version": REQUEST_SCHEMA_VERSION,
        "research_question": RESEARCH_QUESTION,
        "research_objective": RESEARCH_OBJECTIVE,
        "research_category": "fundamental",
        "public_market_context": PUBLIC_MARKET_CONTEXT,
        "allowed_research_scope": ["public_web", "public_reference", "public_market_data"],
        "required_source_types": ["official", "reference", "public_market_data"],
        "max_sources": MAX_SOURCES,
        "max_wall_seconds": 300,
        "max_output_bytes": MAX_OUTPUT_BYTES,
        "max_accepted_estimated_cost_usd": "5",
        "provider_label": "openai-codex",
        "model_label": "gpt-5.6-sol",
        "human_review_required": True,
        "non_authority_notice": NON_AUTHORITY_NOTICE,
    }


# ── Frozen Alpha constants (Section 12) ───────────────────────────────────────

CANDIDATE_THESIS = "Contract-specific official NWS forecasts and observations may contain independently observable public information whose incremental predictive value beyond contemporaneous Polymarket market probability can later be tested without wallet evidence."
EVIDENCE_LANES = ("HISTORICAL_REPEATABILITY", "RESOLUTION_RULES", "WEATHER")
CREATION_PROVENANCE = "S10-ALPHA-REAL-01 controlled public-web research"
PRODUCER_VERSION = "s10-alpha-real-01-operator-1.0.0+hermes-0.21.3"
SOURCE_PROVENANCE_PREFIX = "S10-ALPHA-REAL-01 controlled public-web research; hermes receipt "
MECHANISM_KEY = "nws-public-weather-vs-market-probability"
TESTED_ASSUMPTIONS = (
    "Official NWS information used by a future feature is publicly available before contract resolution at the time it is used.",
    "NWS publication and observation timing can later be reconstructed point-in-time.",
    "Sufficiently comparable NWS-resolved daily-rain contracts and history may exist for later deterministic testing.",
    "The future B1 feature set is constructible without wallet evidence and without contemporaneous or future market information except where later B0/B2 definitions explicitly permit MARKET_PIT.",
)
EXACT_SCOPE = {
    "program_key": "polymarket-nws-daily-rain-v1",
    "venue": "POLYMARKET",
    "market_family": "NWS_RESOLVED_DAILY_RAIN_PRECIPITATION",
    "resolution_source_family": "OFFICIAL_NWS_NOAA_REPORTS",
    "specific_market_ids_in_scope": False,
    "wallet_dependency": "NON_WALLET",
}
EVIDENCE_REGIME = {
    "producer": "HERMES_CONTROLLED_RESEARCH",
    "research_mode": "SINGLE_CONTROLLED_PUBLIC_WEB_RUN",
    "hermes_version": "0.21.3",
    "exposed_toolset": "WEB_ONLY",
    "context_mode": False,
    "wallet_evidence_used": False,
    "repo_polymarket_product_api_used": False,
    "source_content_bytes_bound": False,
}
SOURCE_CLASS_MAP = {
    "official": "OFFICIAL",
    "news": "NEWS",
    "reference": "REFERENCE",
    "public_market_data": "PUBLIC_MARKET_DATA",
    "academic": "OTHER_PUBLIC",
    "other_public": "OTHER_PUBLIC",
}
REVIEW_STATES = (
    "RESEARCH_SUPPORTIVE", "NO_EDGE_CURRENTLY", "HYPOTHESIS_FALSIFIED",
    "DATA_INSUFFICIENT", "WATCH_FOR_CHANGE",
)
STATE_REQUIRED_FIELD = {
    "RESEARCH_SUPPORTIVE": "evidence_for",
    "NO_EDGE_CURRENTLY": "evidence_against",
    "HYPOTHESIS_FALSIFIED": "evidence_against",
    "DATA_INSUFFICIENT": "known_missing_data",
    "WATCH_FOR_CHANGE": "what_would_change_the_conclusion",
}
STATE_TERMINAL = {
    "RESEARCH_SUPPORTIVE": "ALPHA_REAL_01_SUPPORTIVE",
    "NO_EDGE_CURRENTLY": "ALPHA_REAL_01_NON_SUPPORTIVE",
    "HYPOTHESIS_FALSIFIED": "ALPHA_REAL_01_NON_SUPPORTIVE",
    "DATA_INSUFFICIENT": "ALPHA_REAL_01_INSUFFICIENT",
    "WATCH_FOR_CHANGE": "ALPHA_REAL_01_INSUFFICIENT",
}
PROJECTION_SCHEMA_ID = "s10-alpha-real-01-full-draft-projection"
DECISION_SCHEMA_ID = "s10-alpha-real-01-review-decision"
DECISION_KEYS = frozenset({
    "schema_id", "schema_version", "wp_id", "reviewer", "request_id", "hermes_receipt_id",
    "full_draft_projection_sha256", "review_bundle_sha256", "result_state",
})
PROJECTION_KEYS = frozenset({
    "schema_id", "schema_version", "request_id", "research_summary", "confidence_label",
    *DRAFT_LIST_FIELDS, "source_references",
})
# The six ValidatedResearchDraft fields the controller retains (Section 10 step D).
RETAINED_DRAFT_FIELDS = (
    "request_id", "research_summary", "confidence_label", "source_references",
    "source_urls", "falsification_checks_performed",
)


def candidate_input() -> dict[str, object]:
    return {
        "candidate_version": "1.0.0",
        "title": "Official-weather information incrementality for NWS-resolved Polymarket rain markets",
        "research_question": RESEARCH_QUESTION,
        "thesis": CANDIDATE_THESIS,
        "subject_refs": ["research-program:polymarket:nws-daily-rain-v1"],
        "evidence_lanes": list(EVIDENCE_LANES),
        "scope_key": "polymarket-nws-daily-rain-v1",
        "mechanism_hint": "official-weather-information-incrementality",
        "novelty_dimensions": {
            "subject_keys": ["polymarket-nws-daily-rain"],
            "scope_key": "polymarket-nws-daily-rain-v1",
            "mechanism_key": MECHANISM_KEY,
        },
        "discovery_provenance": CREATION_PROVENANCE,
        "human_review_required": True,
    }


def family_input() -> dict[str, object]:
    return {
        "family_version": "1.0.0",
        "family_name": "NWS public-weather incrementality versus market probability",
        "mechanism_key": MECHANISM_KEY,
        "mechanism_dimensions": {
            "domain": "WEATHER_DAILY_PRECIPITATION",
            "information_source": "OFFICIAL_NWS_PUBLIC_NON_MARKET",
            "future_baseline_concept": "CONTEMPORANEOUS_POLYMARKET_PROBABILITY",
            "wallet_dependency": "NON_WALLET",
        },
        "falsifiable_theme": "Under point-in-time-safe testing, official NWS public weather information fails to add reproducible out-of-sample predictive information beyond contemporaneous Polymarket probability.",
        "predecessor_family_id": None,
        "creation_provenance": CREATION_PROVENANCE,
        "human_review_required": True,
    }


# ── Closed operator stops ─────────────────────────────────────────────────────


class AlphaRealOperatorError(RuntimeError):
    """Closed sanitized stop: ``str(error)`` is the closed code; ``terminal`` its class."""

    def __init__(self, code: str, terminal: str = "PRE_RUNTIME_STOP") -> None:
        super().__init__(code)
        self.code = code
        self.terminal = terminal


def _pre(code: str) -> AlphaRealOperatorError:
    return AlphaRealOperatorError(code, "PRE_RUNTIME_STOP")


def _runtime_failure(code: str) -> AlphaRealOperatorError:
    return AlphaRealOperatorError(code, "RUNTIME_FAILURE")


def _review_stop(code: str) -> AlphaRealOperatorError:
    return AlphaRealOperatorError(code, "STOP_AWAITING_SIDE13")


# ── Canonical local I/O ───────────────────────────────────────────────────────


def canonical_sha256(value: object) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()  # type: ignore[arg-type]


def _reject_constant(value: str) -> object:
    raise ValueError("JSON_CONSTANT_FORBIDDEN")


def _reject_float(value: str) -> object:
    raise ValueError("JSON_FLOAT_FORBIDDEN")


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("JSON_DUPLICATE_KEY")
        result[key] = value
    return result


def _read_json(path: Path, code: str) -> dict[str, object]:
    try:
        value = json.loads(
            path.read_bytes().decode("utf-8"), object_pairs_hook=_unique_object,
            parse_constant=_reject_constant, parse_float=_reject_float,
        )
    except (OSError, UnicodeError, ValueError, RecursionError):
        raise AlphaRealOperatorError(code, "STOP_AWAITING_SIDE13") from None
    if not isinstance(value, dict):
        raise AlphaRealOperatorError(code, "STOP_AWAITING_SIDE13")
    return value


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_canonical(path: Path, value: object) -> str:
    """Write canonical JSON bytes (no trailing newline); file SHA-256 == canonical SHA-256."""
    payload = canonical_json_bytes(value)  # type: ignore[arg-type]
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_bytes(payload)
    os.replace(temporary, path)
    return hashlib.sha256(payload).hexdigest()


def _write_exclusive_canonical(path: Path, value: object) -> None:
    payload = canonical_json_bytes(value)  # type: ignore[arg-type]
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0)
    descriptor = os.open(path, flags, 0o600)
    try:
        view = memoryview(payload)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                raise OSError("exclusive write failed")
            view = view[written:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def workspace_path(repo_root: Path) -> Path:
    return Path(repo_root).resolve().joinpath(*WORKSPACE_PARTS)


# ── Local git state (read-only, zero-network) ─────────────────────────────────


@dataclasses.dataclass(frozen=True)
class GitState:
    head: str
    branch: str
    clean: bool
    base_is_ancestor: bool


def read_git_state(repo_root: Path) -> GitState:
    def run(*args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(  # noqa: S603 - fixed local git argv, no shell, no network
            ["git", *args], cwd=str(repo_root), capture_output=True, text=True, check=False,
        )

    head = run("rev-parse", "HEAD").stdout.strip()
    branch = run("branch", "--show-current").stdout.strip()
    status = run("status", "--porcelain")
    ancestor = run("merge-base", "--is-ancestor", BASE_SHA, "HEAD")
    return GitState(
        head=head, branch=branch,
        clean=status.returncode == 0 and status.stdout.strip() == "",
        base_is_ancestor=ancestor.returncode == 0,
    )


def check_git_state(state: GitState) -> None:
    if len(state.head) != 40 or any(ch not in "0123456789abcdef" for ch in state.head):
        raise _pre("STATE_DRIFT")
    if state.branch != PINNED_BRANCH or not state.base_is_ancestor:
        raise _pre("STATE_DRIFT")
    if not state.clean:
        raise _pre("WORKTREE_DIRTY")


# ── Request / identity reproduction ───────────────────────────────────────────


def build_frozen_request():
    request = build_research_run_request(request_literals())
    if request.request_id != EXPECTED_REQUEST_ID:
        raise _pre("REQUEST_IDENTITY_MISMATCH")
    return request


def build_expected_candidate_family() -> tuple[OpportunityCandidate, HypothesisFamily]:
    candidate = build_opportunity_candidate(candidate_input())
    family = build_hypothesis_family(family_input())
    if not candidate.is_valid or not family.is_valid:
        raise _runtime_failure("ALPHA_BUILD_REJECTED")
    if (candidate.record.candidate_id != EXPECTED_CANDIDATE_ID
            or family.record.hypothesis_family_id != EXPECTED_FAMILY_ID):
        raise _runtime_failure("ALPHA_BUILD_REJECTED")
    return candidate.record, family.record


def check_policy() -> None:
    policy = DEFAULT_HERMES_INVOCATION_POLICY
    if policy.policy_id != EXPECTED_POLICY_ID or policy.max_transport_retries != 0:
        raise _pre("POLICY_MISMATCH")


# ── Hermes executable / home (names only; never credential content) ───────────


@dataclasses.dataclass(frozen=True)
class RuntimePaths:
    executable: str = PINNED_HERMES_EXECUTABLE
    home: str = PINNED_HERMES_HOME


PINNED_RUNTIME_PATHS = RuntimePaths()


def check_home(paths: RuntimePaths) -> None:
    """Existence and merged safe/clean predicates only. Missing home is a human checkpoint."""
    if not is_safe_research_home(paths.home):
        raise _pre("HERMES_HOME_UNSAFE")
    if not os.path.isdir(paths.home):
        raise _pre("HUMAN_CREDENTIAL_SETUP_REQUIRED")
    if not is_clean_research_home_control_plane(paths.home):
        raise _pre("HERMES_HOME_CONTROL_PLANE_INVALID")


def check_executable(paths: RuntimePaths) -> tuple[tuple[str, ...], tuple[str, ...]]:
    exe = paths.executable
    if not isinstance(exe, str) or not os.path.isabs(exe) or not os.path.isfile(exe):
        raise _pre("HERMES_EXECUTABLE_INVALID")
    try:
        validate_executable_path(exe)
        return build_version_argv(exe), build_startup_argv(exe)
    except PolicyBroadeningError:
        raise _pre("HERMES_EXECUTABLE_INVALID") from None


def run_offline_probes(paths: RuntimePaths, backend: object) -> None:
    """Merged offline --version and --help probes (throwaway home; no provider call)."""
    version_argv, startup_argv = check_executable(paths)
    version = backend.probe_version(  # type: ignore[attr-defined]
        version_argv=version_argv, max_output_bytes=_VERSION_PROBE_MAX_BYTES,
        max_wall_seconds=_VERSION_PROBE_MAX_SECONDS,
    )
    if (not version.launched or version.timed_out or version.exit_code != 0
            or version.stdout_truncated or not is_supported_hermes_version(version.version_text)):
        raise _pre("HERMES_VERSION_PREFLIGHT_FAILED")
    startup = backend.probe_startup(  # type: ignore[attr-defined]
        startup_argv=startup_argv, max_output_bytes=_STARTUP_PROBE_MAX_BYTES,
        max_wall_seconds=_STARTUP_PROBE_MAX_SECONDS,
    )
    if not startup.launched or startup.timed_out or startup.exit_code != 0:
        raise _pre("HERMES_STARTUP_PREFLIGHT_FAILED")


# ── Pre-runtime inventory (Section 15) ────────────────────────────────────────


def _alpha_application_id(path: Path) -> int | None:
    try:
        with path.open("rb") as handle:
            header = handle.read(100)
    except OSError:
        return None
    if len(header) < 72 or not header.startswith(SQLITE_HEADER):
        return None
    return int.from_bytes(header[68:72], "big")


def _current_leaves(records: Sequence[object], candidate_id: str, family_id: str) -> list[ResearchEpisode]:
    episodes = [r for r in records if isinstance(r, ResearchEpisode)]
    lineage = [e for e in episodes if e.candidate_id == candidate_id and e.hypothesis_family_id == family_id]
    parents = {ref for e in episodes for ref in (e.predecessor_episode_id, e.reopened_episode_id) if ref}
    return [e for e in lineage if e.research_episode_id not in parents]


def classify_existing_registry(path: Path, expected_candidate: OpportunityCandidate) -> dict[str, object]:
    result = load_and_verify_alpha_factory_registry(str(path))
    if not result.is_valid or result.snapshot is None:
        raise _pre("EXISTING_ALPHA_CONFLICT")
    records = [entry.record for entry in result.snapshot.entries]
    candidates = [r for r in records if isinstance(r, OpportunityCandidate)]
    families = [r for r in records if isinstance(r, HypothesisFamily)]
    has_candidate = any(c.candidate_id == EXPECTED_CANDIDATE_ID for c in candidates)
    has_family = any(f.hypothesis_family_id == EXPECTED_FAMILY_ID for f in families)
    foreign_candidate = any(
        c.candidate_id != EXPECTED_CANDIDATE_ID
        and c.novelty_fingerprint == expected_candidate.novelty_fingerprint for c in candidates
    )
    foreign_family = any(
        f.hypothesis_family_id != EXPECTED_FAMILY_ID and f.mechanism_key == MECHANISM_KEY for f in families
    )
    if foreign_candidate or foreign_family:
        raise _pre("EXISTING_ALPHA_CONFLICT")
    if not (has_candidate or has_family):
        return {"classification": "UNRELATED", "head_entry_hash": result.snapshot.head_entry_hash}
    leaves = _current_leaves(records, EXPECTED_CANDIDATE_ID, EXPECTED_FAMILY_ID)
    if has_candidate and has_family and len(leaves) == 1 and leaves[0].result_state == "RESEARCH_SUPPORTIVE":
        error = AlphaRealOperatorError("ALREADY_SATISFIED_EXISTING_ALPHA", "ALREADY_SATISFIED_EXISTING_ALPHA")
        error.existing = {  # type: ignore[attr-defined]
            "candidate_id": EXPECTED_CANDIDATE_ID, "hypothesis_family_id": EXPECTED_FAMILY_ID,
            "research_episode_id": leaves[0].research_episode_id,
            "head_entry_hash": result.snapshot.head_entry_hash,
        }
        raise error
    raise _pre("EXISTING_ALPHA_CONFLICT")


def build_inventory(repo_root: Path, expected_candidate: OpportunityCandidate) -> dict[str, object]:
    root = Path(repo_root).resolve()
    local_data = root / "local_data"
    dedicated = workspace_path(root) / REGISTRY_FILENAME
    alpha_registries: list[dict[str, object]] = []
    protected: list[dict[str, object]] = []
    seen = 0
    if local_data.is_dir():
        for directory, dirnames, filenames in os.walk(local_data, followlinks=False):
            dirnames.sort()
            for name in sorted(filenames):
                seen += 1
                if seen > MAX_INVENTORY_FILES:
                    raise _pre("INVENTORY_LIMIT_EXCEEDED")
                path = Path(directory) / name
                if path.is_symlink() or not path.is_file():
                    continue
                relative = path.relative_to(root).as_posix()
                parts = path.relative_to(local_data).parts
                if parts and parts[0] in PROTECTED_EVIDENCE_DIRS:
                    protected.append({"path": relative, "size": path.stat().st_size, "sha256": _file_sha256(path)})
                if path == dedicated:
                    continue
                if _alpha_application_id(path) == ALPHA_REGISTRY_APPLICATION_ID:
                    classified = classify_existing_registry(path, expected_candidate)
                    alpha_registries.append({"path": relative, **classified})
    return {
        "schema_id": "s10-alpha-real-01-prepare-inventory",
        "schema_version": "1.0.0",
        "wp_id": WP_ID,
        "existing_alpha_registries": alpha_registries,
        "protected_evidence_files": protected,
        "protected_evidence_sha256": canonical_sha256({"files": protected}),
    }


def check_protected_unchanged(repo_root: Path, inventory: Mapping[str, object]) -> None:
    root = Path(repo_root).resolve()
    recorded = inventory.get("protected_evidence_files")
    if not isinstance(recorded, list):
        raise _review_stop("PROTECTED_EVIDENCE_CHANGED")
    current: list[dict[str, object]] = []
    for directory in PROTECTED_EVIDENCE_DIRS:
        base = root / "local_data" / directory
        if not base.is_dir():
            continue
        for parent, dirnames, filenames in os.walk(base, followlinks=False):
            dirnames.sort()
            for name in sorted(filenames):
                path = Path(parent) / name
                if path.is_symlink() or not path.is_file():
                    continue
                current.append({"path": path.relative_to(root).as_posix(), "size": path.stat().st_size,
                                "sha256": _file_sha256(path)})
    key = lambda item: str(item["path"])  # noqa: E731
    if sorted(current, key=key) != sorted(recorded, key=key):
        raise _review_stop("PROTECTED_EVIDENCE_CHANGED")


# ── Activation envelope (Section 9) ───────────────────────────────────────────


def build_envelope(head: str, paths: RuntimePaths = PINNED_RUNTIME_PATHS) -> dict[str, object]:
    return {
        "schema_id": "s10-alpha-real-01-runtime-activation-envelope",
        "schema_version": "1.0.0",
        "wp_id": WP_ID,
        "phase_a_head": head,
        "base_main": BASE_SHA,
        "hermes_executable": paths.executable,
        "hermes_home": paths.home,
        "hermes_version": HERMES_VERSION,
        "policy_id": EXPECTED_POLICY_ID,
        "request_id": EXPECTED_REQUEST_ID,
        "request_literals_sha256": canonical_sha256(request_literals()),
        "context_mode": False,
        "max_controller_executions": 1,
        "max_research_child_launches": 1,
        "automatic_controller_rerun": 0,
        "replacement_research_run": 0,
        "content_schema_rerun": 0,
        "provider_model_fallback": 0,
        "backend_fallback_rescue": 0,
        "accepted_reported_cost_ceiling_usd": "5",
        "capital_usd": 0,
        "operator_polymarket_product_api_calls": 0,
        "h1_5": 0,
        "workspace": WORKSPACE_TEXT,
        "registry_path": REGISTRY_TEXT,
        "required_acknowledgement": RUNTIME_ACKNOWLEDGEMENT,
        "required_credential_confirmation": CREDENTIAL_SETUP_CONFIRMATION,
    }


def _local_checks(repo_root: Path, git_state: GitState, paths: RuntimePaths) -> tuple[OpportunityCandidate, dict[str, object]]:
    check_git_state(git_state)
    check_policy()
    build_frozen_request()
    candidate, _family = build_expected_candidate_family()
    inventory = build_inventory(repo_root, candidate)
    check_home(paths)
    return candidate, inventory


def prepare(repo_root: Path, *, git_state: GitState | None = None,
            paths: RuntimePaths = PINNED_RUNTIME_PATHS) -> str:
    """Zero-network state/inventory/home checks; writes inventory + envelope only on success."""
    root = Path(repo_root).resolve()
    state = git_state if git_state is not None else read_git_state(root)
    _candidate, inventory = _local_checks(root, state, paths)
    envelope = build_envelope(state.head, paths)
    workspace = workspace_path(root)
    if workspace.exists():
        present = {p.name for p in workspace.iterdir()}
        if not present <= {INVENTORY_FILENAME, ENVELOPE_FILENAME}:
            raise _pre("WORKSPACE_CONFLICT")
        for name, value in ((INVENTORY_FILENAME, inventory), (ENVELOPE_FILENAME, envelope)):
            target = workspace / name
            if target.exists() and target.read_bytes() != canonical_json_bytes(value):
                raise _pre("WORKSPACE_CONFLICT")
    workspace.mkdir(parents=True, exist_ok=True)
    _write_canonical(workspace / INVENTORY_FILENAME, inventory)
    return _write_canonical(workspace / ENVELOPE_FILENAME, envelope)


def verify_local(repo_root: Path, *, git_state: GitState | None = None, backend: object | None = None,
                 paths: RuntimePaths = PINNED_RUNTIME_PATHS) -> str:
    """Re-verify prepare outputs against current state, then run the offline probes."""
    root = Path(repo_root).resolve()
    state = git_state if git_state is not None else read_git_state(root)
    _candidate, inventory = _local_checks(root, state, paths)
    workspace = workspace_path(root)
    envelope_path = workspace / ENVELOPE_FILENAME
    inventory_path = workspace / INVENTORY_FILENAME
    if not envelope_path.is_file() or not inventory_path.is_file():
        raise _pre("PREPARE_REQUIRED")
    if envelope_path.read_bytes() != canonical_json_bytes(build_envelope(state.head, paths)):
        raise _pre("ENVELOPE_MISMATCH")
    if inventory_path.read_bytes() != canonical_json_bytes(inventory):
        raise _pre("WORKSPACE_CONFLICT")
    run_offline_probes(paths, backend if backend is not None else ExternalHermesCliBackend())
    return _file_sha256(envelope_path)


# ── Capture / delegation backend (Section 10) ─────────────────────────────────


class CaptureBackend:
    """Thin wrapper around the merged backend: one delegated invoke, stdout kept in memory.

    The attempt sentinel is created exclusively IMMEDIATELY before the one delegation, so
    attempt consumption coincides with the research-child launch. A second invoke is refused.
    """

    def __init__(self, inner: object, sentinel_path: Path, sentinel_value: Mapping[str, object]) -> None:
        self._inner = inner
        self._sentinel_path = sentinel_path
        self._sentinel_value = dict(sentinel_value)
        self.invoke_count = 0
        self.captured_stdout: bytes | None = None
        self.captured_outcome: object | None = None

    def probe_version(self, **kwargs: object) -> object:
        return self._inner.probe_version(**kwargs)  # type: ignore[attr-defined]

    def probe_startup(self, **kwargs: object) -> object:
        return self._inner.probe_startup(**kwargs)  # type: ignore[attr-defined]

    def invoke(self, **kwargs: object) -> object:
        if self.invoke_count:
            raise AlphaRealOperatorError("SECOND_RESEARCH_CHILD_LAUNCH_REFUSED", "RUNTIME_FAILURE")
        try:
            _write_exclusive_canonical(self._sentinel_path, self._sentinel_value)
        except OSError:
            raise _pre("SENTINEL_WRITE_FAILED") from None
        self.invoke_count = 1
        outcome = self._inner.invoke(**kwargs)  # type: ignore[attr-defined]
        self.captured_outcome = outcome
        self.captured_stdout = outcome.stdout  # type: ignore[attr-defined]
        return outcome


def sanitized_receipt(receipt: object) -> dict[str, object]:
    mapping = dataclasses.asdict(receipt)  # type: ignore[arg-type]
    excerpt = mapping.pop("stderr_excerpt", None)
    mapping["stderr_excerpt_present"] = excerpt is not None
    return mapping


def revalidate_full_draft(captured_stdout: object, receipt: object, validated_draft: object) -> dict[str, object]:
    """Steps A-F: recapture, revalidate, compare the six retained fields, build projection."""
    if not isinstance(captured_stdout, bytes) or validated_draft is None:
        raise _runtime_failure("DRAFT_REVALIDATION_MISMATCH")
    response = capture_final_response(captured_stdout, max_bytes=MAX_OUTPUT_BYTES)
    if not response.ok or response.final_text is None:
        raise _runtime_failure("DRAFT_REVALIDATION_MISMATCH")
    try:
        redraft = validate_research_draft(
            response.final_text, expected_request_id=receipt.request_id,  # type: ignore[attr-defined]
            max_sources=MAX_SOURCES, context_mode=False,
        )
    except Exception:
        raise _runtime_failure("DRAFT_REVALIDATION_MISMATCH") from None
    for field in RETAINED_DRAFT_FIELDS:
        if getattr(redraft, field) != getattr(validated_draft, field):
            raise _runtime_failure("DRAFT_REVALIDATION_MISMATCH")
    document = json.loads(response.final_text)
    projection: dict[str, object] = {
        "schema_id": PROJECTION_SCHEMA_ID,
        "schema_version": "1.0.0",
        "request_id": redraft.request_id,
        "research_summary": document["research_summary"],
        "confidence_label": document["confidence_label"],
        "source_references": [
            {"title": item["title"], "url": item["url"], "source_class": item["source_class"]}
            for item in document["source_references"]
        ],
    }
    for field in DRAFT_LIST_FIELDS:
        projection[field] = list(document[field])
    if (projection["research_summary"] != redraft.research_summary
            or [s["url"] for s in projection["source_references"]] != list(redraft.source_urls)  # type: ignore[index, union-attr]
            or tuple(projection["falsification_checks_performed"]) != redraft.falsification_checks_performed):  # type: ignore[arg-type]
        raise _runtime_failure("DRAFT_REVALIDATION_MISMATCH")
    return projection


# ── run-real (the only network command) ───────────────────────────────────────


def run_real(
    repo_root: Path, *, envelope_sha256: str, acknowledgement: str, credential_confirmation: str,
    git_state: GitState | None = None, backend: object | None = None,
    paths: RuntimePaths = PINNED_RUNTIME_PATHS,
    controller: Callable[..., object] = run_controlled_hermes_research,
) -> dict[str, object]:
    root = Path(repo_root).resolve()
    workspace = workspace_path(root)
    sentinel = workspace / SENTINEL_FILENAME
    if sentinel.exists():
        raise AlphaRealOperatorError("ATTEMPT_ALREADY_CONSUMED", "ATTEMPT_ALREADY_CONSUMED")
    if acknowledgement != RUNTIME_ACKNOWLEDGEMENT:
        raise _pre("ACKNOWLEDGEMENT_INVALID")
    if credential_confirmation != CREDENTIAL_SETUP_CONFIRMATION:
        raise _pre("CREDENTIAL_SETUP_CONFIRMATION_INVALID")
    state = git_state if git_state is not None else read_git_state(root)
    inner = backend if backend is not None else ExternalHermesCliBackend()
    envelope_digest = verify_local(root, git_state=state, backend=inner, paths=paths)
    if envelope_sha256 != envelope_digest:
        raise _pre("ENVELOPE_DIGEST_MISMATCH")
    present = {p.name for p in workspace.iterdir()}
    if present != {INVENTORY_FILENAME, ENVELOPE_FILENAME}:
        raise _pre("WORKSPACE_CONFLICT")
    request = build_frozen_request()
    capture = CaptureBackend(inner, sentinel, {
        "schema_id": "s10-alpha-real-01-attempt-sentinel", "schema_version": "1.0.0",
        "wp_id": WP_ID, "envelope_sha256": envelope_digest, "request_id": request.request_id,
        "consumed_at_utc": _utc_now(),
    })
    try:
        run = controller(
            request, capture, executable_path=paths.executable,
            policy=DEFAULT_HERMES_INVOCATION_POLICY, hermes_home=paths.home, context_mode=False,
        )
    except AlphaRealOperatorError as exc:
        if capture.invoke_count == 0:
            raise
        return _persist_runtime_failure(workspace, envelope_digest, None, exc.code)
    except Exception:
        if capture.invoke_count == 0:
            raise _pre("CONTROLLER_EXCEPTION_BEFORE_LAUNCH") from None
        return _persist_runtime_failure(workspace, envelope_digest, None, "CONTROLLER_EXCEPTION_AFTER_LAUNCH")
    receipt = run.receipt  # type: ignore[attr-defined]
    if capture.invoke_count == 0:
        # Controller-internal version/startup preflight failed: no child, no sentinel.
        raise _pre("CONTROLLER_PREFLIGHT_FAILED")
    if receipt.terminal_status != SUCCESS_TERMINAL_STATUS:
        return _persist_runtime_failure(workspace, envelope_digest, receipt, "RECEIPT_" + str(receipt.terminal_status))
    if (receipt.transport_attempt_count != 1 or receipt.policy_id != EXPECTED_POLICY_ID
            or receipt.request_id != EXPECTED_REQUEST_ID
            or receipt.verified_provider != "openai-codex" or receipt.verified_model != "gpt-5.6-sol"):
        return _persist_runtime_failure(workspace, envelope_digest, receipt, "RUNTIME_BINDING_MISMATCH")
    try:
        projection = revalidate_full_draft(capture.captured_stdout, receipt, run.validated_draft)  # type: ignore[attr-defined]
    except AlphaRealOperatorError as exc:
        return _persist_runtime_failure(workspace, envelope_digest, receipt, exc.code)
    projection_sha = _write_canonical(workspace / PROJECTION_FILENAME, projection)
    session = getattr(run, "session_evidence", None)
    result = {
        "schema_id": "s10-alpha-real-01-runtime-result", "schema_version": "1.0.0", "wp_id": WP_ID,
        "runtime_state": "RUN_VALIDATED", "terminal": None, "reason_code": None,
        "research_child_launch_count": capture.invoke_count,
        "envelope_sha256": envelope_digest, "receipt_id": receipt.receipt_id,
        "receipt": sanitized_receipt(receipt),
        "session_evidence_id": getattr(session, "session_evidence_id", None),
        "full_draft_projection_sha256": projection_sha,
    }
    _write_canonical(workspace / RUNTIME_RESULT_FILENAME, result)
    return result


def _persist_runtime_failure(workspace: Path, envelope_digest: str, receipt: object | None, code: str) -> dict[str, object]:
    result = {
        "schema_id": "s10-alpha-real-01-runtime-result", "schema_version": "1.0.0", "wp_id": WP_ID,
        "runtime_state": "RUNTIME_FAILURE", "terminal": "RUNTIME_FAILURE", "reason_code": code,
        "research_child_launch_count": 1, "envelope_sha256": envelope_digest,
        "receipt_id": getattr(receipt, "receipt_id", None),
        "receipt": sanitized_receipt(receipt) if receipt is not None else None,
        "session_evidence_id": None, "full_draft_projection_sha256": None,
    }
    _write_canonical(workspace / RUNTIME_RESULT_FILENAME, result)
    return result


# ── Post-run verification / review ────────────────────────────────────────────


def _load_validated_run(workspace: Path) -> tuple[dict[str, object], dict[str, object]]:
    if not (workspace / SENTINEL_FILENAME).is_file():
        raise _review_stop("RUN_EVIDENCE_INVALID")
    result = _read_json(workspace / RUNTIME_RESULT_FILENAME, "RUN_EVIDENCE_INVALID")
    if result.get("runtime_state") != "RUN_VALIDATED" or result.get("wp_id") != WP_ID:
        raise _review_stop("RUN_NOT_VALIDATED")
    projection_path = workspace / PROJECTION_FILENAME
    if not projection_path.is_file() or _file_sha256(projection_path) != result.get("full_draft_projection_sha256"):
        raise _review_stop("RUN_EVIDENCE_INVALID")
    projection = _read_json(projection_path, "RUN_EVIDENCE_INVALID")
    receipt = result.get("receipt")
    if (set(projection) != PROJECTION_KEYS or projection.get("schema_id") != PROJECTION_SCHEMA_ID
            or projection.get("request_id") != EXPECTED_REQUEST_ID or not isinstance(receipt, dict)
            or receipt.get("receipt_id") != result.get("receipt_id")
            or receipt.get("terminal_status") != SUCCESS_TERMINAL_STATUS):
        raise _review_stop("RUN_EVIDENCE_INVALID")
    envelope_path = workspace / ENVELOPE_FILENAME
    if not envelope_path.is_file() or _file_sha256(envelope_path) != result.get("envelope_sha256"):
        raise _review_stop("RUN_EVIDENCE_INVALID")
    return result, projection


def verify_run(repo_root: Path) -> str:
    workspace = workspace_path(repo_root)
    if not (workspace / SENTINEL_FILENAME).is_file():
        raise _review_stop("RUN_EVIDENCE_INVALID")
    result = _read_json(workspace / RUNTIME_RESULT_FILENAME, "RUN_EVIDENCE_INVALID")
    if result.get("runtime_state") == "RUNTIME_FAILURE":
        return "RUNTIME_FAILURE " + str(result.get("reason_code"))
    _load_validated_run(workspace)
    return "RUN_EVIDENCE_VALID"


def map_sources(projection: Mapping[str, object], receipt_id: str, end_utc: str) -> tuple[list[ResearchSourceReference], list[dict[str, object]]]:
    usable: list[ResearchSourceReference] = []
    excluded: list[dict[str, object]] = []
    seen: set[tuple[str, str, str]] = set()
    for index, item in enumerate(projection["source_references"]):  # type: ignore[union-attr]
        key = (item["url"], item["title"], item["source_class"])
        if key in seen:
            excluded.append({"index": index, "codes": ["EXACT_DUPLICATE_SOURCE"]})
            continue
        seen.add(key)
        alpha_class = SOURCE_CLASS_MAP.get(item["source_class"])
        if alpha_class is None:
            excluded.append({"index": index, "codes": ["SOURCE_CLASS_UNMAPPED"]})
            continue
        built = build_research_source_reference({
            "source_kind": "PUBLIC_HTTPS", "source_class": alpha_class,
            "source_locator": item["url"], "title": item["title"], "observed_at": end_utc,
            "content_sha256": None, "provenance": SOURCE_PROVENANCE_PREFIX + receipt_id,
        })
        if built.is_valid:
            usable.append(built.record)
        else:
            excluded.append({"index": index, "codes": list(built.error_codes)})
    return usable, excluded


def build_review_bundle(repo_root: Path) -> str:
    workspace = workspace_path(repo_root)
    result, projection = _load_validated_run(workspace)
    receipt = result["receipt"]
    candidate, family = build_expected_candidate_family()
    usable, excluded = map_sources(projection, str(result["receipt_id"]), str(receipt["end_utc"]))  # type: ignore[index]
    summary_keys = (
        "receipt_id", "request_id", "policy_id", "hermes_version", "provider_label", "model_label",
        "verified_provider", "verified_model", "terminal_status", "transport_attempt_count",
        "api_call_count", "token_input_count", "token_output_count", "total_token_count",
        "estimated_cost_usd", "cost_status", "cost_source", "start_utc", "end_utc", "source_url_count",
    )
    bundle = {
        "schema_id": "s10-alpha-real-01-review-bundle", "schema_version": "1.0.0", "wp_id": WP_ID,
        "research_question": RESEARCH_QUESTION,
        "full_draft_projection": projection,
        "full_draft_projection_sha256": result["full_draft_projection_sha256"],
        "receipt_summary": {key: receipt[key] for key in summary_keys},  # type: ignore[index]
        "envelope_sha256": result["envelope_sha256"],
        "expected_candidate_id": candidate.candidate_id,
        "expected_hypothesis_family_id": family.hypothesis_family_id,
        "usable_source_count": len(usable),
        "excluded_sources": excluded,
        "allowed_result_states": [
            {"result_state": state, "required_list": STATE_REQUIRED_FIELD[state],
             "admissible": bool(projection[STATE_REQUIRED_FIELD[state]])}
            for state in REVIEW_STATES
        ],
        "non_authority_notice": NON_AUTHORITY_NOTICE,
    }
    return _write_canonical(workspace / BUNDLE_FILENAME, bundle)


def load_decision(workspace: Path, result: Mapping[str, object], projection: Mapping[str, object]) -> str:
    bundle_path = workspace / BUNDLE_FILENAME
    if not bundle_path.is_file():
        raise _review_stop("REVIEW_BUNDLE_REQUIRED")
    decision = _read_json(workspace / DECISION_FILENAME, "REVIEW_DECISION_INVALID")
    expected = {
        "schema_id": DECISION_SCHEMA_ID, "schema_version": "1.0.0", "wp_id": WP_ID,
        "reviewer": "Side13", "request_id": EXPECTED_REQUEST_ID,
        "hermes_receipt_id": result["receipt_id"],
        "full_draft_projection_sha256": result["full_draft_projection_sha256"],
        "review_bundle_sha256": _file_sha256(bundle_path),
    }
    if set(decision) != DECISION_KEYS:
        raise _review_stop("REVIEW_DECISION_INVALID")
    for key, value in expected.items():
        if type(decision[key]) is not type(value) or decision[key] != value:
            raise _review_stop("REVIEW_DECISION_INVALID")
    state = decision["result_state"]
    if not isinstance(state, str) or state not in REVIEW_STATES:
        raise _review_stop("REVIEW_DECISION_INVALID")
    if not projection[STATE_REQUIRED_FIELD[state]]:
        raise _review_stop("REVIEW_STATE_EVIDENCE_MISMATCH")
    return state


def verify_review(repo_root: Path) -> str:
    workspace = workspace_path(repo_root)
    result, projection = _load_validated_run(workspace)
    return load_decision(workspace, result, projection)


# ── finalize-alpha / verify-final (Sections 12-14) ────────────────────────────


def build_episode(state: str, projection: Mapping[str, object], candidate: OpportunityCandidate,
                  family: HypothesisFamily, sources: Sequence[ResearchSourceReference],
                  receipt_id: str, end_utc: str) -> ResearchEpisode:
    mapping: dict[str, object] = {
        "episode_version": "1.0.0",
        "candidate_id": candidate.candidate_id,
        "hypothesis_family_id": family.hypothesis_family_id,
        "predecessor_episode_id": None,
        "reopened_episode_id": None,
        "result_state": state,
        "confidence_label": projection["confidence_label"],
        "evidence_lanes": list(EVIDENCE_LANES),
        "exact_scope": dict(EXACT_SCOPE),
        "evidence_regime": dict(EVIDENCE_REGIME),
        "research_question": RESEARCH_QUESTION,
        "thesis": CANDIDATE_THESIS,
        "tested_assumptions": list(TESTED_ASSUMPTIONS),
        "source_reference_ids": [s.source_reference_id for s in sources],
        "deterministic_evidence_refs": [receipt_id],
        "material_change_basis": [],
        "producer_type": "HERMES_CONTROLLED_RESEARCH",
        "producer_version": PRODUCER_VERSION,
        "producer_receipt_ref": receipt_id,
        "research_as_of": end_utc,
        "creation_provenance": CREATION_PROVENANCE,
        "human_review_required": True,
    }
    for field in DRAFT_LIST_FIELDS:
        mapping[field] = list(projection[field])  # type: ignore[call-overload]
    built = build_research_episode(mapping)
    if not built.is_valid:
        raise _runtime_failure("ALPHA_BUILD_REJECTED")
    return built.record


def _batch(repo_root: Path) -> tuple[str, list[object], ResearchEpisode, dict[str, object], dict[str, object], list[dict[str, object]]]:
    workspace = workspace_path(repo_root)
    result, projection = _load_validated_run(workspace)
    state = load_decision(workspace, result, projection)
    receipt_id = str(result["receipt_id"])
    end_utc = str(result["receipt"]["end_utc"])  # type: ignore[index]
    candidate, family = build_expected_candidate_family()
    sources, excluded = map_sources(projection, receipt_id, end_utc)
    if not sources:
        raise _runtime_failure("FINALIZE_NO_USABLE_SOURCE")
    episode = build_episode(state, projection, candidate, family, sources, receipt_id, end_utc)
    return state, [*sources, candidate, family, episode], episode, result, projection, excluded


def finalize_alpha(repo_root: Path) -> dict[str, object]:
    root = Path(repo_root).resolve()
    workspace = workspace_path(root)
    inventory = _read_json(workspace / INVENTORY_FILENAME, "RUN_EVIDENCE_INVALID")
    check_protected_unchanged(root, inventory)
    state, batch, episode, result, _projection, excluded = _batch(root)
    registry = workspace / REGISTRY_FILENAME
    if not registry.exists():
        init = initialize_alpha_factory_registry(str(registry))
        if not init.is_valid:
            raise _review_stop("ALPHA_FINALIZATION_CONFLICT")
    loaded = load_and_verify_alpha_factory_registry(str(registry))
    if not loaded.is_valid or loaded.snapshot is None:
        raise _review_stop("ALPHA_FINALIZATION_CONFLICT")
    existing = {entry.record_id: entry.record for entry in loaded.snapshot.entries}
    expected = {_record_id(record): record for record in batch}
    if not existing:
        appended = append_alpha_factory_records(str(registry), batch)
        if not appended.is_valid or set(appended.inserted_record_ids) != set(expected):
            raise _review_stop("ALPHA_FINALIZATION_CONFLICT")
        outcome = "APPEND_COMMITTED"
    elif existing == expected:
        outcome = "IDEMPOTENT_FINALIZED_SUCCESS"
    else:
        raise _review_stop("ALPHA_FINALIZATION_CONFLICT")
    reloaded = load_and_verify_alpha_factory_registry(str(registry))
    if (not reloaded.is_valid or reloaded.snapshot is None
            or {e.record_id: e.record for e in reloaded.snapshot.entries} != expected):
        raise _review_stop("ALPHA_FINALIZATION_CONFLICT")
    evidence = _final_evidence(state, batch, episode, result, excluded, reloaded.snapshot)
    target = workspace / FINAL_EVIDENCE_FILENAME
    if target.exists() and target.read_bytes() != canonical_json_bytes(evidence):
        raise _review_stop("ALPHA_FINALIZATION_CONFLICT")
    _write_canonical(target, evidence)
    return {**evidence, "finalize_outcome": outcome}


_RECORD_ID_FIELD = {
    ResearchSourceReference: "source_reference_id",
    OpportunityCandidate: "candidate_id",
    HypothesisFamily: "hypothesis_family_id",
    ResearchEpisode: "research_episode_id",
}


def _record_id(record: object) -> str:
    field = _RECORD_ID_FIELD.get(type(record))
    if field is None:
        raise _review_stop("ALPHA_FINALIZATION_CONFLICT")
    return getattr(record, field)


def _final_evidence(state: str, batch: Sequence[object], episode: ResearchEpisode, result: Mapping[str, object],
                    excluded: Sequence[Mapping[str, object]], snapshot: object) -> dict[str, object]:
    sources = [r for r in batch if isinstance(r, ResearchSourceReference)]
    terminal = STATE_TERMINAL[state]
    return {
        "schema_id": "s10-alpha-real-01-final-evidence", "schema_version": "1.0.0", "wp_id": WP_ID,
        "terminal": terminal,
        "result_state": state,
        "s10_qual_real_01_draft_eligible": terminal == "ALPHA_REAL_01_SUPPORTIVE",
        "receipt_id": result["receipt_id"],
        "envelope_sha256": result["envelope_sha256"],
        "full_draft_projection_sha256": result["full_draft_projection_sha256"],
        "source_reference_ids": sorted(s.source_reference_id for s in sources),
        "excluded_sources": list(excluded),
        "candidate_id": EXPECTED_CANDIDATE_ID,
        "hypothesis_family_id": EXPECTED_FAMILY_ID,
        "research_episode_id": episode.research_episode_id,
        "registry_path": REGISTRY_TEXT,
        "registry_total_rows": snapshot.total_rows,  # type: ignore[attr-defined]
        "registry_head_entry_hash": snapshot.head_entry_hash,  # type: ignore[attr-defined]
        "qualification_authority": False,
        "execution_authority": False,
    }


def verify_final(repo_root: Path) -> dict[str, object]:
    root = Path(repo_root).resolve()
    workspace = workspace_path(root)
    evidence = _read_json(workspace / FINAL_EVIDENCE_FILENAME, "FINAL_EVIDENCE_INVALID")
    inventory = _read_json(workspace / INVENTORY_FILENAME, "FINAL_EVIDENCE_INVALID")
    check_protected_unchanged(root, inventory)
    state, batch, episode, result, _projection, excluded = _batch(root)
    loaded = load_and_verify_alpha_factory_registry(str(workspace / REGISTRY_FILENAME))
    if not loaded.is_valid or loaded.snapshot is None:
        raise _review_stop("FINAL_EVIDENCE_INVALID")
    records = [entry.record for entry in loaded.snapshot.entries]
    if {e.record_id: e.record for e in loaded.snapshot.entries} != {_record_id(r): r for r in batch}:
        raise _review_stop("FINAL_EVIDENCE_INVALID")
    leaves = _current_leaves(records, EXPECTED_CANDIDATE_ID, EXPECTED_FAMILY_ID)
    if len(leaves) != 1 or leaves[0] != episode or leaves[0].result_state != state:
        raise _review_stop("FINAL_EVIDENCE_INVALID")
    recomputed = _final_evidence(state, batch, episode, result, excluded, loaded.snapshot)
    if canonical_json_bytes(recomputed) != canonical_json_bytes(evidence):
        raise _review_stop("FINAL_EVIDENCE_INVALID")
    return evidence


# ── CLI ───────────────────────────────────────────────────────────────────────


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("prepare", "verify-local", "verify-run", "build-review-bundle", "verify-review",
                 "finalize-alpha", "verify-final"):
        sub.add_parser(name)
    real = sub.add_parser("run-real")
    real.add_argument("--envelope-sha256", required=True)
    real.add_argument("--acknowledgement", required=True)
    real.add_argument("--credential-setup-confirmation", required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "prepare":
            print("PREPARED_ZERO_NETWORK envelope_sha256=" + prepare(REPO_ROOT))
        elif args.command == "verify-local":
            print("LOCAL_PREFLIGHT_VALID envelope_sha256=" + verify_local(REPO_ROOT))
        elif args.command == "run-real":
            result = run_real(
                REPO_ROOT, envelope_sha256=args.envelope_sha256, acknowledgement=args.acknowledgement,
                credential_confirmation=args.credential_setup_confirmation,
            )
            print(" ".join(str(part) for part in (
                result["runtime_state"], result["reason_code"] or "",
                "launches=" + str(result["research_child_launch_count"]),
                "receipt_id=" + str(result["receipt_id"]),
                "projection_sha256=" + str(result["full_draft_projection_sha256"]),
            ) if part != ""))
        elif args.command == "verify-run":
            print(verify_run(REPO_ROOT))
        elif args.command == "build-review-bundle":
            print("SIDE13_REVIEW_REQUIRED review_bundle_sha256=" + build_review_bundle(REPO_ROOT))
        elif args.command == "verify-review":
            print("REVIEW_DECISION_VALID result_state=" + verify_review(REPO_ROOT))
        elif args.command == "finalize-alpha":
            evidence = finalize_alpha(REPO_ROOT)
            print(f"{evidence['terminal']} {evidence['finalize_outcome']} "
                  f"episode={evidence['research_episode_id']} head={evidence['registry_head_entry_hash']}")
        else:
            evidence = verify_final(REPO_ROOT)
            print(f"FINAL_EVIDENCE_VALID {evidence['terminal']} "
                  f"s10_qual_real_01_draft_eligible={evidence['s10_qual_real_01_draft_eligible']}")
        return 0
    except AlphaRealOperatorError as exc:
        existing = getattr(exc, "existing", None)
        suffix = "".join(f" {key}={existing[key]}" for key in sorted(existing)) if existing else ""
        print(f"{exc.terminal} {exc.code}{suffix}", file=sys.stderr)
        return 2
    except (OSError, ValueError):
        print("PRE_RUNTIME_STOP LOCAL_IO_OR_VALUE_ERROR", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
