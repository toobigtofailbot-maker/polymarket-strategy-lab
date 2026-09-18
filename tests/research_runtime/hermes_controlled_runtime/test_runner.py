"""WP175H external-process boundary traps for the pinned v0.21.3 contract.

R002 shell metacharacters cannot become shell execution.
R003 the repository path is never supplied as the Hermes working directory.
R010 a timeout terminates the run and yields a sanitized outcome.
R016 the fake backend makes zero network/process calls.
Plus: version preflight, usage-file read-back, and the non-secret Hermes-home boundary.
"""

from __future__ import annotations

import json
import os
import sys
import textwrap
from pathlib import Path

import pytest

from src.research_runtime.hermes_controlled_runtime import (
    ExternalHermesCliBackend,
    FakeHermesBackend,
    HermesInvocationOutcome,
    build_hermes_argv,
    build_research_run_request,
    build_version_argv,
    is_safe_research_home,
)
from src.research_runtime.hermes_controlled_runtime import runner as runner_mod
from src.research_runtime.hermes_controlled_runtime import policy as policy_mod
from src.research_runtime.hermes_controlled_runtime.models import (
    NON_AUTHORITY_NOTICE,
    REQUEST_SCHEMA_VERSION,
)

REPO_ROOT = Path(__file__).resolve().parents[3]


def _request():
    return build_research_run_request(
        {
            "schema_version": REQUEST_SCHEMA_VERSION,
            "research_question": "Will the public event resolve YES?",
            "research_objective": "Assess public evidence.",
            "research_category": "event_outcome",
            "public_market_context": "A Polymarket public market.",
            "allowed_research_scope": ["public_web"],
            "required_source_types": ["news"],
            "max_sources": 5,
            "provider_label": "example-provider",
            "model_label": "example-model",
            "max_turns": 10,
            "max_wall_seconds": 60,
            "max_output_bytes": 200_000,
            "max_estimated_cost_usd": "1",
            "human_review_required": True,
            "non_authority_notice": NON_AUTHORITY_NOTICE,
        }
    )


def _outcome(stdout=b"{}"):
    return HermesInvocationOutcome(
        stdout=stdout, stdout_truncated=False, stderr_byte_len=0, stderr_truncated=False,
        usage_file_bytes=None, usage_file_truncated=False, exit_code=0, timed_out=False,
        launch_failed=False, duration_ms=0,
    )


# --- argv shape: R002 + no unsupported flags ---------------------------------


def test_r002_shell_metacharacter_executable_rejected():
    req = _request()
    with pytest.raises(policy_mod.PolicyBroadeningError):
        build_hermes_argv("hermes; rm -rf /", req, "PROMPT")


def test_argv_uses_pinned_v0213_shape_without_unsupported_flags():
    req = _request()
    argv = build_hermes_argv("hermes", req, "PROMPT")
    assert isinstance(argv, tuple)
    # Corrected external contract: no unsupported v0.21.3 flags.
    assert "--input-file" not in argv
    assert "--format" not in argv
    assert "stream-json" not in argv
    # Supported one-shot shape.
    assert "-z" in argv and argv[-1] == "PROMPT"
    assert "--usage-file" in argv
    assert argv.count("--toolsets") == 1
    assert argv[argv.index("--toolsets") + 1] == "web"
    for forbidden in ("terminal", "file", "browser", "delegation", "memory", "cron", "mcp", "safe"):
        assert forbidden not in argv


def test_over_bound_prompt_fails_before_spawn():
    req = _request()
    huge = "x" * (policy_mod.MAX_PROMPT_BYTES + 1)
    with pytest.raises(policy_mod.PolicyBroadeningError):
        build_hermes_argv("hermes", req, huge)


def test_r002_metacharacter_argument_is_not_shell_interpreted(tmp_path):
    marker = tmp_path / "pwned"
    prog = textwrap.dedent(
        """
        import sys, json
        print(json.dumps({"argv": sys.argv[1:]}))
        """
    )
    argv = [sys.executable, "-c", prog, f"; touch {marker}", "&& echo hi"]
    outcome = ExternalHermesCliBackend().invoke(
        argv=argv, usage_file_name="hermes_usage.json", max_stdout_bytes=200_000,
        max_stderr_bytes=65_536, max_usage_bytes=65_536, max_wall_seconds=30,
    )
    assert outcome.launch_failed is False and outcome.timed_out is False
    assert not marker.exists()
    payload = [json.loads(l) for l in outcome.stdout.decode().splitlines() if l.strip()]
    assert f"; touch {marker}" in payload[-1]["argv"]


# --- R003: ephemeral cwd never repo/home; usage read-back --------------------


def test_r003_working_directory_is_ephemeral_and_usage_file_read_back():
    prog = textwrap.dedent(
        """
        import os, json
        # Emulate Hermes writing a usage file into its cwd.
        with open("hermes_usage.json", "w") as fh:
            json.dump({"input_tokens": 3, "output_tokens": 4}, fh)
        print(json.dumps({"cwd": os.getcwd()}))
        """
    )
    outcome = ExternalHermesCliBackend().invoke(
        argv=[sys.executable, "-c", prog], usage_file_name="hermes_usage.json",
        max_stdout_bytes=200_000, max_stderr_bytes=65_536, max_usage_bytes=65_536,
        max_wall_seconds=30,
    )
    payload = [json.loads(l) for l in outcome.stdout.decode().splitlines() if l.strip()]
    child_cwd = Path(payload[-1]["cwd"]).resolve()
    assert child_cwd != REPO_ROOT
    assert child_cwd != Path(os.path.expanduser("~")).resolve()
    assert "local_data" not in str(child_cwd)
    assert not child_cwd.exists()  # teardown removed it
    assert outcome.usage_file_bytes is not None
    assert json.loads(outcome.usage_file_bytes.decode())["input_tokens"] == 3


def test_usage_file_with_separator_is_rejected():
    outcome = ExternalHermesCliBackend().invoke(
        argv=[sys.executable, "-c", "pass"], usage_file_name="../escape.json",
        max_stdout_bytes=1000, max_stderr_bytes=1000, max_usage_bytes=1000, max_wall_seconds=5,
    )
    assert outcome.launch_failed is True


# --- R010: timeout ----------------------------------------------------------


def test_r010_timeout_terminates_and_is_sanitized():
    outcome = ExternalHermesCliBackend().invoke(
        argv=[sys.executable, "-c", "import time; time.sleep(30)"],
        usage_file_name="hermes_usage.json", max_stdout_bytes=1000, max_stderr_bytes=1000,
        max_usage_bytes=1000, max_wall_seconds=1,
    )
    assert outcome.timed_out is True
    assert outcome.exit_code is None
    assert outcome.transport_retry_eligible is True


def test_launch_failure_for_missing_executable():
    outcome = ExternalHermesCliBackend().invoke(
        argv=[str(REPO_ROOT / "definitely_not_an_executable_xyz")],
        usage_file_name="hermes_usage.json", max_stdout_bytes=1000, max_stderr_bytes=1000,
        max_usage_bytes=1000, max_wall_seconds=5,
    )
    assert outcome.launch_failed is True and outcome.transport_retry_eligible is True


def test_r009_external_backend_truncates_oversized_stdout():
    outcome = ExternalHermesCliBackend().invoke(
        argv=[sys.executable, "-c", "import sys; sys.stdout.write('z'*5000)"],
        usage_file_name="hermes_usage.json", max_stdout_bytes=100, max_stderr_bytes=100,
        max_usage_bytes=100, max_wall_seconds=30,
    )
    assert outcome.stdout_truncated is True and len(outcome.stdout) == 100


# --- version preflight ------------------------------------------------------


def test_external_version_probe_reads_version_no_research_call():
    prog = "import sys; sys.stdout.write('hermes-agent 0.21.3')"
    probe = ExternalHermesCliBackend().probe_version(
        version_argv=[sys.executable, "-c", prog], max_output_bytes=4096, max_wall_seconds=15,
    )
    assert probe.launched is True and probe.timed_out is False
    assert "0.21.3" in (probe.version_text or "")


def test_build_version_argv_is_argv_only():
    assert build_version_argv("hermes") == ("hermes", "--version")


# --- R016: fake backend makes zero process/network calls --------------------


def test_r016_fake_backend_makes_no_process_call(monkeypatch):
    def _boom(*args, **kwargs):  # pragma: no cover - must never be called
        raise AssertionError("fake backend must not spawn a process")

    monkeypatch.setattr(runner_mod.subprocess, "Popen", _boom)
    monkeypatch.setattr(runner_mod.subprocess, "run", _boom)
    backend = FakeHermesBackend.from_transcript(b'{"ok": true}')
    probe = backend.probe_version(version_argv=("hermes", "--version"), max_output_bytes=10, max_wall_seconds=5)
    assert "0.21.3" in (probe.version_text or "")
    outcome = backend.invoke(
        argv=("hermes", "-z", "p"), usage_file_name="hermes_usage.json",
        max_stdout_bytes=1000, max_stderr_bytes=1000, max_usage_bytes=1000, max_wall_seconds=5,
    )
    assert isinstance(outcome, HermesInvocationOutcome)
    assert backend.call_count == 1 and backend.version_probe_count == 1


def test_fake_backend_enforces_stdout_cap():
    backend = FakeHermesBackend.from_transcript(b"x" * 100)
    outcome = backend.invoke(
        argv=("hermes",), usage_file_name="hermes_usage.json", max_stdout_bytes=10,
        max_stderr_bytes=10, max_usage_bytes=10, max_wall_seconds=5,
    )
    assert outcome.stdout_truncated is True and len(outcome.stdout) == 10


# --- credential / Hermes-home boundary --------------------------------------


def test_no_provider_secret_env_forwarded(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-should-not-be-forwarded")
    monkeypatch.setenv("HERMES_PROVIDER_SECRET", "nope")
    monkeypatch.setenv("SOME_AUTH_TOKEN", "nope")
    env = runner_mod._minimal_env(None)
    for key in env:
        assert not runner_mod._looks_secret(key)
    assert "OPENAI_API_KEY" not in env
    assert "HERMES_PROVIDER_SECRET" not in env
    assert "SOME_AUTH_TOKEN" not in env


def test_only_safe_non_secret_hermes_home_is_forwarded(tmp_path):
    safe_home = tmp_path / "research_home"
    safe_home.mkdir()
    assert is_safe_research_home(str(safe_home)) is True
    env = runner_mod._minimal_env(str(safe_home))
    assert env.get("HERMES_HOME") == str(safe_home)


def test_unsafe_hermes_home_is_rejected():
    # Inside the repository worktree.
    assert is_safe_research_home(str(REPO_ROOT)) is False
    # Relative path.
    assert is_safe_research_home("relative/home") is False
    # local_data tree.
    assert is_safe_research_home(str(Path(os.path.expanduser("~")) / "local_data" / "h")) is False
    # Traversal marker.
    assert is_safe_research_home("/opt/../etc/home") is False
