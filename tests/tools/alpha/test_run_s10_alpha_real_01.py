"""S10-ALPHA-REAL-01 operator tests (Phase A).

Zero network, zero real Hermes: every research child is the merged FakeHermesBackend behind
the operator's capture backend, and every Alpha registry lives in a pytest temp directory.
Named nodes map to the frozen evidence plan R001-R014.
"""

from __future__ import annotations

import ast
import dataclasses
import json
from pathlib import Path

import pytest

import tools.alpha.run_s10_alpha_real_01 as operator
from src.data_layer.analytical_research.alpha_factory import build_research_source_reference
from src.data_layer.analytical_research.alpha_factory_registry import (
    append_alpha_factory_records,
    initialize_alpha_factory_registry,
    load_and_verify_alpha_factory_registry,
)
from src.research_runtime.hermes_controlled_runtime import (
    FakeHermesBackend,
    run_controlled_hermes_research,
)
from src.research_runtime.hermes_controlled_runtime.models import (
    DRAFT_AUTHORITY_FLAGS,
    DRAFT_LIST_FIELDS,
    DRAFT_SCHEMA_VERSION,
    canonical_json_bytes,
)
from src.research_runtime.hermes_controlled_runtime.runner import HermesInvocationOutcome

ROOT = Path(__file__).resolve().parents[3]
OPERATOR_SOURCE = ROOT / "tools" / "alpha" / "run_s10_alpha_real_01.py"
PROMPT = ROOT / "docs" / "wp_specs" / "S10-ALPHA-REAL-01" / "wp_prompt.txt"
GIT_OK = operator.GitState(head="a" * 40, branch=operator.PINNED_BRANCH, clean=True, base_is_ancestor=True)
RAW_MARKER = "RAW-STDOUT-ONLY-MARKER-7f3c"
SOURCES = [
    {"title": "NWS Climate Report", "url": "https://forecast.weather.gov/product.php?site=OKX&product=CLI", "source_class": "official"},
    {"title": "NWS Climate Report", "url": "https://forecast.weather.gov/product.php?site=OKX&product=CLI", "source_class": "official"},
    {"title": "Polymarket rain market rules", "url": "https://polymarket.com/event/example-rain", "source_class": "public_market_data"},
    {"title": "Past weather help", "url": "https://www.weather.gov/help-past-weather", "source_class": "reference"},
]


# ── fixtures / helpers ───────────────────────────────────────────────────────


def _draft(request_id: str, **overrides: object) -> dict[str, object]:
    document: dict[str, object] = {
        "schema_version": DRAFT_SCHEMA_VERSION, "request_id": request_id,
        "research_summary": "Synthetic research summary.", "confidence_label": "low",
        "evidence_for": ["for-1"], "evidence_against": ["against-1"], "uncertainties": ["u-1"],
        "known_missing_data": ["m-1"], "falsification_checks_performed": ["f-1"],
        "limitations": ["l-1"], "what_would_change_the_conclusion": ["w-1"],
        "suggested_next_research_steps": ["n-1"], "source_references": list(SOURCES),
        "raw_only_field": RAW_MARKER,
    }
    for flag in DRAFT_AUTHORITY_FLAGS:
        document[flag] = True
    document.update(overrides)
    return document


def _usage(**overrides: object) -> bytes:
    document = {
        "input_tokens": 50, "output_tokens": 80, "total_tokens": 130, "api_calls": 7,
        "estimated_cost_usd": 0.0, "cost_status": "estimated", "cost_source": "official_docs_snapshot",
        "model": "gpt-5.6-sol", "provider": "openai-codex", "session_id": "s1",
        "completed": True, "failed": False,
    }
    document.update(overrides)
    return json.dumps(document).encode("utf-8")


def _backend(draft: dict[str, object] | None = None, usage: bytes | None = None, **kwargs: object) -> FakeHermesBackend:
    document = draft if draft is not None else _draft(operator.EXPECTED_REQUEST_ID)
    outcome = HermesInvocationOutcome(
        stdout=json.dumps(document).encode("utf-8"), stdout_truncated=False, stderr_byte_len=0,
        stderr_truncated=False, usage_file_bytes=usage if usage is not None else _usage(),
        usage_file_truncated=False, exit_code=0, timed_out=False, launch_failed=False, duration_ms=5,
    )
    return FakeHermesBackend([outcome], **kwargs)


@pytest.fixture()
def env(tmp_path: Path):
    repo = tmp_path / "repo"
    (repo / "local_data").mkdir(parents=True)
    home = tmp_path / "research-home"
    home.mkdir()
    exe = tmp_path / "bin" / "hermes.exe"
    exe.parent.mkdir()
    exe.write_bytes(b"")
    return repo, operator.RuntimePaths(executable=str(exe), home=str(home))


def _prepare(repo: Path, paths: operator.RuntimePaths, git: operator.GitState = GIT_OK) -> str:
    return operator.prepare(repo, git_state=git, paths=paths)


def _run(repo: Path, paths: operator.RuntimePaths, backend: object, digest: str | None = None, **kwargs: object) -> dict:
    envelope = digest if digest is not None else _prepare(repo, paths)
    options = {
        "envelope_sha256": envelope, "acknowledgement": operator.RUNTIME_ACKNOWLEDGEMENT,
        "credential_confirmation": operator.CREDENTIAL_SETUP_CONFIRMATION,
        "git_state": GIT_OK, "backend": backend, "paths": paths,
    }
    options.update(kwargs)
    return operator.run_real(repo, **options)


def _workspace(repo: Path) -> Path:
    return operator.workspace_path(repo)


def _write_decision(repo: Path, state: str, **overrides: object) -> dict:
    workspace = _workspace(repo)
    result = json.loads((workspace / operator.RUNTIME_RESULT_FILENAME).read_bytes())
    decision = {
        "schema_id": operator.DECISION_SCHEMA_ID, "schema_version": "1.0.0", "wp_id": operator.WP_ID,
        "reviewer": "Side13", "request_id": operator.EXPECTED_REQUEST_ID,
        "hermes_receipt_id": result["receipt_id"],
        "full_draft_projection_sha256": result["full_draft_projection_sha256"],
        "review_bundle_sha256": operator._file_sha256(workspace / operator.BUNDLE_FILENAME),
        "result_state": state,
    }
    decision.update(overrides)
    (workspace / operator.DECISION_FILENAME).write_bytes(json.dumps(decision).encode("utf-8"))
    return decision


def _validated_run(repo: Path, paths: operator.RuntimePaths, draft: dict[str, object] | None = None) -> dict:
    result = _run(repo, paths, _backend(draft))
    assert result["runtime_state"] == "RUN_VALIDATED", result["reason_code"]
    operator.build_review_bundle(repo)
    return result


def _stop(call, *args, **kwargs) -> operator.AlphaRealOperatorError:
    with pytest.raises(operator.AlphaRealOperatorError) as info:
        call(*args, **kwargs)
    return info.value


# ── R001 ─────────────────────────────────────────────────────────────────────


PREPARE_CASES = {
    "dirty": (dataclasses.replace(GIT_OK, clean=False), "WORKTREE_DIRTY"),
    "wrong_branch": (dataclasses.replace(GIT_OK, branch="main"), "STATE_DRIFT"),
    "base_not_ancestor": (dataclasses.replace(GIT_OK, base_is_ancestor=False), "STATE_DRIFT"),
    "bad_head": (dataclasses.replace(GIT_OK, head="HEAD"), "STATE_DRIFT"),
}


@pytest.mark.parametrize("case", [
    *PREPARE_CASES, "missing_home", "unsafe_home", "unclean_home", "missing_executable",
    "version_mismatch", "startup_failure", "wrong_acknowledgement", "wrong_confirmation",
    "wrong_envelope_digest", "head_moved", "policy_mismatch", "model_changed", "workspace_conflict",
])
def test_preflight_failures_make_zero_launches_and_do_not_consume(env, monkeypatch, case) -> None:
    repo, paths = env
    backend = _backend()
    if case in PREPARE_CASES:
        git, code = PREPARE_CASES[case]
        assert _stop(_prepare, repo, paths, git).code == code
    elif case == "missing_home":
        Path(paths.home).rmdir()
        error = _stop(_prepare, repo, paths)
        assert (error.code, error.terminal) == ("HUMAN_CREDENTIAL_SETUP_REQUIRED", "PRE_RUNTIME_STOP")
        assert not _workspace(repo).exists()
    elif case == "unsafe_home":
        unsafe = repo / "local_data" / "home"
        unsafe.mkdir()
        assert _stop(_prepare, repo, dataclasses.replace(paths, home=str(unsafe))).code == "HERMES_HOME_UNSAFE"
        assert _stop(_prepare, repo, dataclasses.replace(paths, home="relative-home")).code == "HERMES_HOME_UNSAFE"
    elif case == "unclean_home":
        (Path(paths.home) / "config.yaml").write_text("x", encoding="utf-8")
        assert _stop(_prepare, repo, paths).code == "HERMES_HOME_CONTROL_PLANE_INVALID"
    elif case == "missing_executable":
        digest = _prepare(repo, dataclasses.replace(paths, executable=paths.executable + ".missing"))
        error = _stop(_run, repo, dataclasses.replace(paths, executable=paths.executable + ".missing"), backend, digest)
        assert error.code == "HERMES_EXECUTABLE_INVALID"
    elif case == "version_mismatch":
        backend = _backend(version_text="hermes-agent 0.21.2")
        assert _stop(_run, repo, paths, backend).code == "HERMES_VERSION_PREFLIGHT_FAILED"
    elif case == "startup_failure":
        backend = _backend(startup_exit_code=1)
        assert _stop(_run, repo, paths, backend).code == "HERMES_STARTUP_PREFLIGHT_FAILED"
    elif case == "wrong_acknowledgement":
        assert _stop(_run, repo, paths, backend, acknowledgement="YES").code == "ACKNOWLEDGEMENT_INVALID"
    elif case == "wrong_confirmation":
        assert _stop(_run, repo, paths, backend, credential_confirmation="done").code == "CREDENTIAL_SETUP_CONFIRMATION_INVALID"
    elif case == "wrong_envelope_digest":
        _prepare(repo, paths)
        assert _stop(_run, repo, paths, backend, "0" * 64).code == "ENVELOPE_DIGEST_MISMATCH"
    elif case == "head_moved":
        digest = _prepare(repo, paths)
        moved = dataclasses.replace(GIT_OK, head="b" * 40)
        assert _stop(_run, repo, paths, backend, digest, git_state=moved).code == "ENVELOPE_MISMATCH"
    elif case == "policy_mismatch":
        monkeypatch.setattr(operator, "EXPECTED_POLICY_ID", "hermesinvocationpolicy:sha256:" + "0" * 64)
        assert _stop(_prepare, repo, paths).code == "POLICY_MISMATCH"
    elif case == "model_changed":
        original = operator.request_literals
        monkeypatch.setattr(operator, "request_literals", lambda: {**original(), "model_label": "other-model"})
        assert _stop(_prepare, repo, paths).code == "REQUEST_IDENTITY_MISMATCH"
    elif case == "workspace_conflict":
        digest = _prepare(repo, paths)
        (_workspace(repo) / "stray.json").write_text("{}", encoding="utf-8")
        assert _stop(_run, repo, paths, backend, digest).code == "WORKSPACE_CONFLICT"
        assert _stop(_prepare, repo, paths).code == "WORKSPACE_CONFLICT"
    assert backend.call_count == 0
    assert not (_workspace(repo) / operator.SENTINEL_FILENAME).exists()


# ── R002 ─────────────────────────────────────────────────────────────────────


class _FlakyProbeBackend:
    """Probes pass for the operator preflight, then fail inside the controller."""

    def __init__(self, inner: FakeHermesBackend) -> None:
        self.inner = inner
        self.version_calls = 0

    def probe_version(self, **kwargs):
        self.version_calls += 1
        probe = self.inner.probe_version(**kwargs)
        return probe if self.version_calls == 1 else dataclasses.replace(probe, version_text="hermes-agent 9.9.9")

    def probe_startup(self, **kwargs):
        return self.inner.probe_startup(**kwargs)

    def invoke(self, **kwargs):
        return self.inner.invoke(**kwargs)


def test_single_research_child_launch_and_no_rerun(env, tmp_path) -> None:
    repo, paths = env
    backend = _backend()
    result = _run(repo, paths, backend)
    assert result["runtime_state"] == "RUN_VALIDATED"
    assert result["research_child_launch_count"] == 1 and backend.call_count == 1
    assert result["receipt"]["transport_attempt_count"] == 1
    sentinel = json.loads((_workspace(repo) / operator.SENTINEL_FILENAME).read_bytes())
    assert sentinel["request_id"] == operator.EXPECTED_REQUEST_ID
    second = _stop(_run, repo, paths, _backend(), "0" * 64)
    assert second.code == "ATTEMPT_ALREADY_CONSUMED" and backend.call_count == 1
    # The capture backend refuses a second delegation outright.
    capture = operator.CaptureBackend(_backend(), tmp_path / "s.json", {"k": "v"})
    capture.invoke(argv=["x"], usage_file_name="u.json", max_stdout_bytes=10_000, max_stderr_bytes=10,
                   max_usage_bytes=10_000, max_wall_seconds=1)
    assert _stop(capture.invoke, argv=["x"]).code == "SECOND_RESEARCH_CHILD_LAUNCH_REFUSED"
    # A controller-internal preflight failure launches nothing and consumes nothing.
    other = tmp_path / "other"
    (other / "local_data").mkdir(parents=True)
    flaky = _FlakyProbeBackend(_backend())
    assert _stop(_run, other, paths, flaky).code == "CONTROLLER_PREFLIGHT_FAILED"
    assert flaky.inner.call_count == 0 and not (_workspace(other) / operator.SENTINEL_FILENAME).exists()
    # Structural: exactly one controller call site and no rerun/fallback vocabulary.
    source = OPERATOR_SOURCE.read_text(encoding="utf-8")
    assert source.count("run = controller(") == 1
    run_real_node = next(n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef) and n.name == "run_real")
    assert not any(isinstance(n, (ast.For, ast.While, ast.AsyncFor)) for n in ast.walk(run_real_node))
    run_real_body = ast.get_source_segment(source, run_real_node)
    for forbidden in ("retry(", "fallback_backend", "run_blind_phase(", "context_mode=True"):
        assert forbidden not in run_real_body, forbidden


def test_sentinel_write_failure_is_non_consuming(env, monkeypatch) -> None:
    repo, paths = env
    backend = _backend()
    digest = _prepare(repo, paths)

    def refuse(path, value):
        raise OSError("disk")

    monkeypatch.setattr(operator, "_write_exclusive_canonical", refuse)
    error = _stop(_run, repo, paths, backend, digest)
    assert (error.code, error.terminal) == ("SENTINEL_WRITE_FAILED", "PRE_RUNTIME_STOP")
    assert backend.call_count == 0


# ── R003 ─────────────────────────────────────────────────────────────────────


def test_capture_backend_returns_delegated_outcome_unchanged(tmp_path) -> None:
    inner = _backend()
    capture = operator.CaptureBackend(inner, tmp_path / "sentinel.json", {"k": "v"})
    assert capture.probe_version(version_argv=["x"], max_output_bytes=1, max_wall_seconds=1) is inner._version
    assert capture.probe_startup(startup_argv=["x"], max_output_bytes=1, max_wall_seconds=1) is inner._startup
    assert inner.version_probe_count == 1 and inner.startup_probe_count == 1
    outcome = capture.invoke(argv=["x"], usage_file_name="u.json", max_stdout_bytes=10_000_000,
                             max_stderr_bytes=10, max_usage_bytes=10_000, max_wall_seconds=1)
    assert outcome is capture.captured_outcome
    assert capture.captured_stdout is outcome.stdout
    assert json.loads((tmp_path / "sentinel.json").read_bytes()) == {"k": "v"}
    # The retained stdout is exactly what the merged backend bounded.
    bounded = operator.CaptureBackend(_backend(), tmp_path / "s2.json", {})
    small = bounded.invoke(argv=["x"], usage_file_name="u.json", max_stdout_bytes=64,
                           max_stderr_bytes=10, max_usage_bytes=10_000, max_wall_seconds=1)
    assert len(bounded.captured_stdout) == 64 and small.stdout_truncated is True


# ── R004 ─────────────────────────────────────────────────────────────────────


def _tampering_controller(**changes):
    def controller(request, backend, **kwargs):
        run = run_controlled_hermes_research(request, backend, **kwargs)
        return dataclasses.replace(run, validated_draft=dataclasses.replace(run.validated_draft, **changes))
    return controller


@pytest.mark.parametrize("changes", [
    {"research_summary": "different"}, {"confidence_label": "high"}, {"source_urls": ()},
    {"falsification_checks_performed": ("other",)}, {"request_id": "x"}, {"source_references": ()},
])
def test_full_draft_revalidation_mismatch_blocks_append(env, changes) -> None:
    repo, paths = env
    result = _run(repo, paths, _backend(), controller=_tampering_controller(**changes))
    assert (result["runtime_state"], result["reason_code"]) == ("RUNTIME_FAILURE", "DRAFT_REVALIDATION_MISMATCH")
    workspace = _workspace(repo)
    assert not (workspace / operator.PROJECTION_FILENAME).exists()
    assert operator.verify_run(repo) == "RUNTIME_FAILURE DRAFT_REVALIDATION_MISMATCH"
    assert _stop(operator.build_review_bundle, repo).code == "RUN_NOT_VALIDATED"
    assert _stop(operator.finalize_alpha, repo).code == "RUN_NOT_VALIDATED"
    assert not (workspace / operator.REGISTRY_FILENAME).exists()
    # Unit level: non-bytes capture and matching capture.
    assert _stop(operator.revalidate_full_draft, None, None, None).code == "DRAFT_REVALIDATION_MISMATCH"


def test_matching_revalidation_builds_exact_projection(env) -> None:
    repo, paths = env
    result = _run(repo, paths, _backend())
    projection = json.loads((_workspace(repo) / operator.PROJECTION_FILENAME).read_bytes())
    assert set(projection) == operator.PROJECTION_KEYS
    assert projection["source_references"] == SOURCES
    for field in DRAFT_LIST_FIELDS:
        assert projection[field] == _draft("x")[field]
    assert result["full_draft_projection_sha256"] == operator.canonical_sha256(projection)


# ── R005 ─────────────────────────────────────────────────────────────────────


def test_only_validated_projection_persisted(env, monkeypatch, capsys) -> None:
    repo, paths = env
    secret_value = "sk-test-" + "Q" * 24
    monkeypatch.setenv("OPENAI_API_KEY", secret_value)
    _validated_run(repo, paths)
    _write_decision(repo, "DATA_INSUFFICIENT")
    operator.finalize_alpha(repo)
    workspace = _workspace(repo)
    names = {p.name for p in workspace.iterdir()}
    assert names <= operator.WORKSPACE_FILENAMES
    for path in workspace.iterdir():
        data = path.read_bytes()
        assert RAW_MARKER.encode() not in data, path.name
        assert secret_value.encode() not in data, path.name
    result = json.loads((workspace / operator.RUNTIME_RESULT_FILENAME).read_bytes())
    assert "stderr_excerpt" not in result["receipt"] and "stderr_excerpt_present" in result["receipt"]
    printed = capsys.readouterr()
    assert RAW_MARKER not in printed.out + printed.err and secret_value not in printed.out + printed.err


def test_cli_prepare_prints_closed_code_only(monkeypatch, tmp_path, capsys) -> None:
    # Hermetic: the missing-home checkpoint is injected through the check_home seam, so the
    # result never depends on whether the real pinned research home exists on this machine.
    repo = tmp_path / "repo"
    (repo / "local_data").mkdir(parents=True)
    monkeypatch.setattr(operator, "REPO_ROOT", repo)
    monkeypatch.setattr(operator, "read_git_state", lambda root: GIT_OK)
    seen: list[operator.RuntimePaths] = []

    def missing_home(paths: operator.RuntimePaths) -> None:
        seen.append(paths)
        raise operator.AlphaRealOperatorError("HUMAN_CREDENTIAL_SETUP_REQUIRED", "PRE_RUNTIME_STOP")

    monkeypatch.setattr(operator, "check_home", missing_home)
    assert operator.main(["prepare"]) == 2
    printed = capsys.readouterr()
    assert printed.out == ""
    assert printed.err.strip() == "PRE_RUNTIME_STOP HUMAN_CREDENTIAL_SETUP_REQUIRED"
    assert seen == [operator.PINNED_RUNTIME_PATHS]
    assert not operator.workspace_path(repo).exists()


# ── R006 ─────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("mutation", [
    "missing", "extra_key", "projection_digest", "bundle_digest", "receipt_id", "request_id",
    "unsupported_state", "lowercase_state", "reviewer", "schema", "bundle_changed", "not_object",
])
def test_review_decision_binding_rejections(env, mutation) -> None:
    repo, paths = env
    _validated_run(repo, paths)
    workspace = _workspace(repo)
    decision_path = workspace / operator.DECISION_FILENAME
    if mutation == "missing":
        pass
    elif mutation == "extra_key":
        _write_decision(repo, "DATA_INSUFFICIENT", evidence_for=["edited"])
    elif mutation == "projection_digest":
        _write_decision(repo, "DATA_INSUFFICIENT", full_draft_projection_sha256="0" * 64)
    elif mutation == "bundle_digest":
        _write_decision(repo, "DATA_INSUFFICIENT", review_bundle_sha256="0" * 64)
    elif mutation == "receipt_id":
        _write_decision(repo, "DATA_INSUFFICIENT", hermes_receipt_id="hermesresearchreceipt:sha256:" + "0" * 64)
    elif mutation == "request_id":
        _write_decision(repo, "DATA_INSUFFICIENT", request_id="hermesresearchrequest:sha256:" + "0" * 64)
    elif mutation == "unsupported_state":
        _write_decision(repo, "EXECUTION_UNECONOMIC")
    elif mutation == "lowercase_state":
        _write_decision(repo, "research_supportive")
    elif mutation == "reviewer":
        _write_decision(repo, "DATA_INSUFFICIENT", reviewer="operator")
    elif mutation == "schema":
        _write_decision(repo, "DATA_INSUFFICIENT", schema_version="1.0.1")
    elif mutation == "bundle_changed":
        _write_decision(repo, "DATA_INSUFFICIENT")
        bundle = workspace / operator.BUNDLE_FILENAME
        bundle.write_bytes(bundle.read_bytes() + b" ")
    elif mutation == "not_object":
        decision_path.write_bytes(b"[]")
    for call in (operator.verify_review, operator.finalize_alpha):
        error = _stop(call, repo)
        assert (error.code, error.terminal) == ("REVIEW_DECISION_INVALID", "STOP_AWAITING_SIDE13")
    assert not (workspace / operator.REGISTRY_FILENAME).exists()


def test_operator_has_no_default_result_state() -> None:
    source = OPERATOR_SOURCE.read_text(encoding="utf-8")
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            for default in [*node.args.defaults, *node.args.kw_defaults]:
                if isinstance(default, ast.Constant):
                    assert default.value not in operator.REVIEW_STATES, node.name
    assert "decision[\"result_state\"]" in source and "DECISION_FILENAME" in source


# ── R007 ─────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("state", operator.REVIEW_STATES)
def test_review_state_evidence_mismatch_rejects(env, state) -> None:
    repo, paths = env
    field = operator.STATE_REQUIRED_FIELD[state]
    _validated_run(repo, paths, _draft(operator.EXPECTED_REQUEST_ID, **{field: []}))
    bundle = json.loads((_workspace(repo) / operator.BUNDLE_FILENAME).read_bytes())
    admissible = {item["result_state"]: item["admissible"] for item in bundle["allowed_result_states"]}
    assert admissible[state] is False
    _write_decision(repo, state)
    for call in (operator.verify_review, operator.finalize_alpha):
        assert _stop(call, repo).code == "REVIEW_STATE_EVIDENCE_MISMATCH"
    assert not (_workspace(repo) / operator.REGISTRY_FILENAME).exists()


# ── R008 ─────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("state", operator.REVIEW_STATES)
def test_five_review_states_map_to_episode(env, state) -> None:
    repo, paths = env
    result = _validated_run(repo, paths)
    _write_decision(repo, state)
    assert operator.verify_review(repo) == state
    evidence = operator.finalize_alpha(repo)
    assert evidence["terminal"] == operator.STATE_TERMINAL[state]
    assert evidence["s10_qual_real_01_draft_eligible"] is (state == "RESEARCH_SUPPORTIVE")
    loaded = load_and_verify_alpha_factory_registry(str(_workspace(repo) / operator.REGISTRY_FILENAME))
    episode = next(e.record for e in loaded.snapshot.entries if e.record_kind == "research_episode"
                   or type(e.record).__name__ == "ResearchEpisode")
    projection = json.loads((_workspace(repo) / operator.PROJECTION_FILENAME).read_bytes())
    assert episode.result_state == state
    assert episode.confidence_label == projection["confidence_label"]
    for field in DRAFT_LIST_FIELDS:
        assert list(getattr(episode, field)) == projection[field]
    assert episode.producer_type == "HERMES_CONTROLLED_RESEARCH"
    assert episode.producer_receipt_ref == result["receipt_id"]
    assert episode.deterministic_evidence_refs == (result["receipt_id"],)
    assert episode.research_as_of == result["receipt"]["end_utc"]
    assert episode.tested_assumptions == operator.TESTED_ASSUMPTIONS
    assert episode.material_change_basis == ()
    assert episode.predecessor_episode_id is None and episode.reopened_episode_id is None
    assert operator.verify_final(repo)["terminal"] == operator.STATE_TERMINAL[state]


# ── R009 ─────────────────────────────────────────────────────────────────────


def test_source_mapping_dedup_and_null_content_hash(env) -> None:
    assert operator.SOURCE_CLASS_MAP == {
        "official": "OFFICIAL", "news": "NEWS", "reference": "REFERENCE",
        "public_market_data": "PUBLIC_MARKET_DATA", "academic": "OTHER_PUBLIC", "other_public": "OTHER_PUBLIC",
    }
    receipt_id = "hermesresearchreceipt:sha256:" + "1" * 64
    end_utc = "2026-10-01T00:00:00Z"
    projection = {"source_references": [
        {"title": "A", "url": "https://www.weather.gov/a", "source_class": "official"},
        {"title": "A", "url": "https://www.weather.gov/a", "source_class": "official"},
        {"title": "A2", "url": "https://www.weather.gov/a", "source_class": "official"},
        {"title": "N", "url": "https://news.example.com/n", "source_class": "news"},
        {"title": "R", "url": "https://www.weather.gov/r", "source_class": "reference"},
        {"title": "P", "url": "https://polymarket.com/event/rain", "source_class": "public_market_data"},
        {"title": "Paper", "url": "https://journals.example.org/p", "source_class": "academic"},
        {"title": "O", "url": "https://example.org/o", "source_class": "other_public"},
        {"title": "Private", "url": "https://10.0.0.1/x", "source_class": "official"},
    ]}
    usable, excluded = operator.map_sources(projection, receipt_id, end_utc)
    assert [s.source_class for s in usable] == [
        "OFFICIAL", "OFFICIAL", "NEWS", "REFERENCE", "PUBLIC_MARKET_DATA", "OTHER_PUBLIC", "OTHER_PUBLIC"]
    assert excluded[0] == {"index": 1, "codes": ["EXACT_DUPLICATE_SOURCE"]}
    assert excluded[1]["index"] == 8 and excluded[1]["codes"]
    for source in usable:
        assert source.content_sha256 is None
        assert source.observed_at == end_utc and source.source_kind == "PUBLIC_HTTPS"
        assert source.provenance == operator.SOURCE_PROVENANCE_PREFIX + receipt_id
    assert [s.source_locator for s in usable][4] == "https://polymarket.com/event/rain"
    # End to end: zero usable sources -> RUNTIME_FAILURE, no append.
    repo, paths = env
    private = [{"title": "X", "url": "https://10.0.0.1/x", "source_class": "official"}]
    _validated_run(repo, paths, _draft(operator.EXPECTED_REQUEST_ID, source_references=private))
    _write_decision(repo, "DATA_INSUFFICIENT")
    error = _stop(operator.finalize_alpha, repo)
    assert (error.code, error.terminal) == ("FINALIZE_NO_USABLE_SOURCE", "RUNTIME_FAILURE")
    assert not (_workspace(repo) / operator.REGISTRY_FILENAME).exists()


# ── R010 ─────────────────────────────────────────────────────────────────────


def test_frozen_alpha_constants_and_expected_ids() -> None:
    assert operator.build_frozen_request().request_id == operator.EXPECTED_REQUEST_ID
    candidate, family = operator.build_expected_candidate_family()
    assert candidate.candidate_id == operator.EXPECTED_CANDIDATE_ID
    assert family.hypothesis_family_id == operator.EXPECTED_FAMILY_ID
    prompt = PROMPT.read_text(encoding="utf-8")
    for literal in (operator.RESEARCH_QUESTION, operator.RESEARCH_OBJECTIVE, operator.PUBLIC_MARKET_CONTEXT,
                    operator.CANDIDATE_THESIS, operator.PINNED_HERMES_EXECUTABLE, operator.PINNED_HERMES_HOME,
                    operator.EXPECTED_REQUEST_ID, operator.EXPECTED_CANDIDATE_ID, operator.EXPECTED_FAMILY_ID,
                    operator.EXPECTED_POLICY_ID, operator.RUNTIME_ACKNOWLEDGEMENT,
                    operator.CREDENTIAL_SETUP_CONFIRMATION, operator.PINNED_BRANCH, operator.PRODUCER_VERSION,
                    *operator.TESTED_ASSUMPTIONS):
        assert literal in prompt, literal[:40]
    for mapping in (operator.EXACT_SCOPE, operator.EVIDENCE_REGIME, family_dims := operator.family_input()["mechanism_dimensions"]):
        assert json.dumps(mapping, separators=(", ", ": "), ensure_ascii=False) in prompt, mapping
    assert family_dims["wallet_dependency"] == "NON_WALLET"
    envelope = operator.build_envelope("c" * 40)
    assert envelope["max_research_child_launches"] == 1 and envelope["context_mode"] is False
    assert envelope["hermes_executable"] == operator.PINNED_HERMES_EXECUTABLE
    assert envelope["hermes_home"] == operator.PINNED_HERMES_HOME
    assert envelope["accepted_reported_cost_ceiling_usd"] == "5"
    assert operator.PINNED_RUNTIME_PATHS == operator.RuntimePaths(
        operator.PINNED_HERMES_EXECUTABLE, operator.PINNED_HERMES_HOME)
    # CLI exposes no executable/home override.
    source = OPERATOR_SOURCE.read_text(encoding="utf-8")
    assert "--hermes-home" not in source.split("def build_parser", 1)[1]
    assert "--hermes-executable" not in source.split("def build_parser", 1)[1]


# ── R011 ─────────────────────────────────────────────────────────────────────


def test_finalize_idempotent_and_divergent_registry_rejects(env, tmp_path) -> None:
    repo, paths = env
    result = _validated_run(repo, paths)
    _write_decision(repo, "WATCH_FOR_CHANGE")
    first = operator.finalize_alpha(repo)
    assert first["finalize_outcome"] == "APPEND_COMMITTED"
    second = operator.finalize_alpha(repo)
    assert second["finalize_outcome"] == "IDEMPOTENT_FINALIZED_SUCCESS"
    assert second["registry_head_entry_hash"] == first["registry_head_entry_hash"]
    assert operator.verify_final(repo)["registry_head_entry_hash"] == first["registry_head_entry_hash"]
    registry = _workspace(repo) / operator.REGISTRY_FILENAME
    # A divergent sibling episode appended outside the operator: finalize and verify-final stop.
    projection = json.loads((_workspace(repo) / operator.PROJECTION_FILENAME).read_bytes())
    candidate, family = operator.build_expected_candidate_family()
    sources, _ = operator.map_sources(projection, result["receipt_id"], result["receipt"]["end_utc"])
    divergent = operator.build_episode("DATA_INSUFFICIENT", projection, candidate, family, sources,
                                       result["receipt_id"], result["receipt"]["end_utc"])
    assert append_alpha_factory_records(str(registry), [divergent]).is_valid
    assert _stop(operator.finalize_alpha, repo).code == "ALPHA_FINALIZATION_CONFLICT"
    assert _stop(operator.verify_final, repo).code == "FINAL_EVIDENCE_INVALID"
    # A partial registry (candidate only) also stops before any append.
    other = tmp_path / "other"
    (other / "local_data").mkdir(parents=True)
    _validated_run(other, paths)
    _write_decision(other, "WATCH_FOR_CHANGE")
    partial = _workspace(other) / operator.REGISTRY_FILENAME
    assert initialize_alpha_factory_registry(str(partial)).is_valid
    assert append_alpha_factory_records(str(partial), [candidate]).is_valid
    assert _stop(operator.finalize_alpha, other).code == "ALPHA_FINALIZATION_CONFLICT"
    assert load_and_verify_alpha_factory_registry(str(partial)).snapshot.total_rows == 1


# ── R012 ─────────────────────────────────────────────────────────────────────


def _seed_registry(path: Path, state: str) -> None:
    candidate, family = operator.build_expected_candidate_family()
    receipt_id = "hermesresearchreceipt:sha256:" + "2" * 64
    source = build_research_source_reference({
        "source_kind": "PUBLIC_HTTPS", "source_class": "OFFICIAL", "source_locator": "https://www.weather.gov/x",
        "title": "X", "observed_at": "2026-10-01T00:00:00Z", "content_sha256": None, "provenance": "seed",
    }).record
    projection = {field: ["item"] for field in DRAFT_LIST_FIELDS}
    projection["confidence_label"] = "low"
    episode = operator.build_episode(state, projection, candidate, family, [source], receipt_id, "2026-10-01T00:00:00Z")
    path.parent.mkdir(parents=True, exist_ok=True)
    assert initialize_alpha_factory_registry(str(path)).is_valid
    assert append_alpha_factory_records(str(path), [source, candidate, family, episode]).is_valid


@pytest.mark.parametrize("case", ["supportive", "non_supportive", "corrupt", "unrelated"])
def test_prepare_inventory_existing_alpha_outcomes(env, case) -> None:
    repo, paths = env
    target = repo / "local_data" / "elsewhere" / "alpha.sqlite3"
    if case == "supportive":
        _seed_registry(target, "RESEARCH_SUPPORTIVE")
        error = _stop(_prepare, repo, paths)
        assert (error.code, error.terminal) == ("ALREADY_SATISFIED_EXISTING_ALPHA", "ALREADY_SATISFIED_EXISTING_ALPHA")
        assert error.existing["candidate_id"] == operator.EXPECTED_CANDIDATE_ID
        assert error.existing["head_entry_hash"]
    elif case == "non_supportive":
        _seed_registry(target, "DATA_INSUFFICIENT")
        assert _stop(_prepare, repo, paths).code == "EXISTING_ALPHA_CONFLICT"
    elif case == "corrupt":
        target.parent.mkdir(parents=True)
        header = bytearray(operator.SQLITE_HEADER + bytes(84))
        header[68:72] = operator.ALPHA_REGISTRY_APPLICATION_ID.to_bytes(4, "big")
        target.write_bytes(bytes(header))
        assert _stop(_prepare, repo, paths).code == "EXISTING_ALPHA_CONFLICT"
    else:
        target.parent.mkdir(parents=True)
        assert initialize_alpha_factory_registry(str(target)).is_valid
        _prepare(repo, paths)
        inventory = json.loads((_workspace(repo) / operator.INVENTORY_FILENAME).read_bytes())
        assert inventory["existing_alpha_registries"][0]["classification"] == "UNRELATED"
        return
    assert not _workspace(repo).exists()


def test_protected_prior_evidence_must_remain_unchanged(env) -> None:
    repo, paths = env
    protected = repo / "local_data" / "s10_gate_af1" / "attempt-04" / "AF1_FINAL_GATE_EVIDENCE.json"
    protected.parent.mkdir(parents=True)
    protected.write_bytes(b"{}")
    _validated_run(repo, paths)
    inventory = json.loads((_workspace(repo) / operator.INVENTORY_FILENAME).read_bytes())
    assert inventory["protected_evidence_files"][0]["path"].endswith("AF1_FINAL_GATE_EVIDENCE.json")
    _write_decision(repo, "DATA_INSUFFICIENT")
    protected.write_bytes(b"{\"changed\":true}")
    assert _stop(operator.finalize_alpha, repo).code == "PROTECTED_EVIDENCE_CHANGED"


# ── R013 ─────────────────────────────────────────────────────────────────────


ALLOWED_IMPORTS = {
    "__future__", "argparse", "dataclasses", "datetime", "hashlib", "json", "os", "pathlib",
    "subprocess", "sys", "typing",
    "src.data_layer.analytical_research.alpha_factory",
    "src.data_layer.analytical_research.alpha_factory_registry",
    "src.research_runtime.hermes_controlled_runtime",
    "src.research_runtime.hermes_controlled_runtime.controller",
    "src.research_runtime.hermes_controlled_runtime.models",
    "src.research_runtime.hermes_controlled_runtime.policy",
}


def test_no_forbidden_import_or_call_paths() -> None:
    source = OPERATOR_SOURCE.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.add(node.module or "")
    assert imported == ALLOWED_IMPORTS
    docstring = ast.get_docstring(tree, clean=False) or ""
    lowered = source.replace(docstring, "", 1).lower()
    for forbidden in (
        "qualification_gate", "import qualification", "qualificationcandidate", "experiment_os",
        "experiment_registry", "paper_trading", "execution_gateway", "src.oms", "src.risk",
        "data_layer.polymarket", "gamma", "clob", "websocket", "requests", "httpx", "urllib",
        "socket", "keyring", "prefect", "apscheduler", "crontab", "private_key", "run_blind_phase(",
    ):
        assert forbidden not in lowered, forbidden
    # The only subprocess use is fixed local git argv.
    calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and getattr(n.func, "attr", "") == "run"
             and getattr(getattr(n.func, "value", None), "id", "") == "subprocess"]
    assert len(calls) == 1
    assert '["git", *args]' in source


# ── R014 ─────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("usage,expected", [
    ({"api_calls": 9}, ("RUN_VALIDATED", None)),
    ({"estimated_cost_usd": 5.01}, ("RUNTIME_FAILURE", "RECEIPT_")),
    ({"cost_status": "unknown"}, ("RUNTIME_FAILURE", "RECEIPT_")),
    ({"model": "other-model"}, ("RUNTIME_FAILURE", "RECEIPT_")),
])
def test_api_call_count_reported_not_violation(env, usage, expected) -> None:
    repo, paths = env
    backend = _backend(usage=_usage(**usage))
    result = _run(repo, paths, backend)
    assert result["runtime_state"] == expected[0]
    assert backend.call_count == 1 and (_workspace(repo) / operator.SENTINEL_FILENAME).exists()
    if expected[1] is None:
        assert result["receipt"]["api_call_count"] == 9
        operator.build_review_bundle(repo)
        bundle = json.loads((_workspace(repo) / operator.BUNDLE_FILENAME).read_bytes())
        assert bundle["receipt_summary"]["api_call_count"] == 9
    else:
        assert result["reason_code"].startswith(expected[1])
        assert not (_workspace(repo) / operator.PROJECTION_FILENAME).exists()
        assert _stop(_run, repo, paths, _backend(), "0" * 64).code == "ATTEMPT_ALREADY_CONSUMED"


def test_workspace_json_is_canonical(env) -> None:
    repo, paths = env
    _validated_run(repo, paths)
    for path in _workspace(repo).iterdir():
        if path.suffix == ".json" and path.name != operator.DECISION_FILENAME:
            assert canonical_json_bytes(json.loads(path.read_bytes())) == path.read_bytes(), path.name
