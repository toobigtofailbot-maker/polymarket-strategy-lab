"""WP175H external-process boundary traps.

R002 shell metacharacters cannot become shell execution.
R003 the repository path is never supplied as the Hermes working directory.
R010 a timeout terminates the run and yields a sanitized outcome.
R016 the fake backend makes zero network/process calls.
"""

from __future__ import annotations

import json
import os
import subprocess
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


# --- R002: argv only, no shell string ---------------------------------------


def test_r002_shell_metacharacter_executable_rejected():
    req = _request()
    with pytest.raises(policy_mod.PolicyBroadeningError):
        build_hermes_argv("hermes; rm -rf /", req, "research_query.json")


def test_argv_is_a_list_with_exactly_one_web_toolset():
    req = _request()
    argv = build_hermes_argv("hermes", req, "research_query.json")
    assert isinstance(argv, tuple)
    assert argv.count("--toolsets") == 1
    toolset_value = argv[argv.index("--toolsets") + 1]
    assert toolset_value == "web"
    for forbidden in ("terminal", "file", "browser", "delegation", "memory", "cron", "mcp", "safe"):
        assert forbidden not in argv


def test_r002_metacharacter_argument_is_not_shell_interpreted(tmp_path):
    """A metacharacter passed as an ARGUMENT reaches the child literally."""
    marker = tmp_path / "pwned"
    prog = textwrap.dedent(
        """
        import sys, json
        print(json.dumps({"type": "session", "version": "hermes-agent 0.21.3"}))
        print(json.dumps({"type": "result", "subtype": "success",
                          "result": "{}", "argv": sys.argv[1:]}))
        """
    )
    argv = [sys.executable, "-c", prog, f"; touch {marker}", "&& echo hi"]
    backend = ExternalHermesCliBackend()
    outcome = backend.invoke(
        argv=argv,
        query_bytes=b"{}",
        query_file_name="research_query.json",
        max_stdout_bytes=200_000,
        max_stderr_bytes=65_536,
        max_wall_seconds=30,
    )
    assert outcome.launch_failed is False
    assert outcome.timed_out is False
    # No shell side effect happened.
    assert not marker.exists()
    payload = [json.loads(line) for line in outcome.stdout.decode().splitlines() if line.strip()]
    literal_args = payload[-1]["argv"]
    assert f"; touch {marker}" in literal_args


# --- R003: ephemeral empty cwd, never repo/home -----------------------------


def test_r003_working_directory_is_ephemeral_never_repo_or_home():
    prog = textwrap.dedent(
        """
        import os, json
        print(json.dumps({"type": "session", "version": "hermes-agent 0.21.3"}))
        print(json.dumps({"type": "result", "subtype": "success",
                          "result": "{}", "cwd": os.getcwd()}))
        """
    )
    argv = [sys.executable, "-c", prog]
    backend = ExternalHermesCliBackend()
    outcome = backend.invoke(
        argv=argv,
        query_bytes=b"{}",
        query_file_name="research_query.json",
        max_stdout_bytes=200_000,
        max_stderr_bytes=65_536,
        max_wall_seconds=30,
    )
    payload = [json.loads(line) for line in outcome.stdout.decode().splitlines() if line.strip()]
    child_cwd = Path(payload[-1]["cwd"]).resolve()
    assert child_cwd != REPO_ROOT
    assert child_cwd != Path(os.path.expanduser("~")).resolve()
    assert "local_data" not in str(child_cwd)
    # Teardown removed the ephemeral directory.
    assert not child_cwd.exists()


def test_query_file_with_separator_is_rejected():
    backend = ExternalHermesCliBackend()
    outcome = backend.invoke(
        argv=[sys.executable, "-c", "pass"],
        query_bytes=b"{}",
        query_file_name="../escape.json",
        max_stdout_bytes=1000,
        max_stderr_bytes=1000,
        max_wall_seconds=5,
    )
    assert outcome.launch_failed is True


# --- R010: timeout ----------------------------------------------------------


def test_r010_timeout_terminates_and_is_sanitized():
    prog = "import time\ntime.sleep(30)\n"
    argv = [sys.executable, "-c", prog]
    backend = ExternalHermesCliBackend()
    outcome = backend.invoke(
        argv=argv,
        query_bytes=b"{}",
        query_file_name="research_query.json",
        max_stdout_bytes=1000,
        max_stderr_bytes=1000,
        max_wall_seconds=1,
    )
    assert outcome.timed_out is True
    assert outcome.exit_code is None
    assert outcome.transport_retry_eligible is True


def test_launch_failure_for_missing_executable():
    backend = ExternalHermesCliBackend()
    outcome = backend.invoke(
        argv=[str(REPO_ROOT / "definitely_not_an_executable_xyz")],
        query_bytes=b"{}",
        query_file_name="research_query.json",
        max_stdout_bytes=1000,
        max_stderr_bytes=1000,
        max_wall_seconds=5,
    )
    assert outcome.launch_failed is True
    assert outcome.transport_retry_eligible is True


# --- R016: fake backend makes zero process/network calls --------------------


def test_r016_fake_backend_makes_no_process_call(monkeypatch):
    def _boom(*args, **kwargs):  # pragma: no cover - must never be called
        raise AssertionError("fake backend must not spawn a process")

    monkeypatch.setattr(runner_mod.subprocess, "Popen", _boom)
    backend = FakeHermesBackend.from_transcript(b'{"type":"result","subtype":"success","result":"{}"}')
    outcome = backend.invoke(
        argv=("hermes", "chat"),
        query_bytes=b"{}",
        query_file_name="research_query.json",
        max_stdout_bytes=1000,
        max_stderr_bytes=1000,
        max_wall_seconds=5,
    )
    assert isinstance(outcome, HermesInvocationOutcome)
    assert backend.call_count == 1
    assert backend.recorded_query_file_names == ["research_query.json"]


def test_fake_backend_enforces_stdout_cap():
    backend = FakeHermesBackend.from_transcript(b"x" * 100)
    outcome = backend.invoke(
        argv=("hermes",),
        query_bytes=b"{}",
        query_file_name="research_query.json",
        max_stdout_bytes=10,
        max_stderr_bytes=10,
        max_wall_seconds=5,
    )
    assert outcome.stdout_truncated is True
    assert len(outcome.stdout) == 10


def test_r009_external_backend_truncates_oversized_stdout():
    prog = textwrap.dedent(
        """
        import sys
        sys.stdout.write("z" * 5000)
        """
    )
    backend = ExternalHermesCliBackend()
    outcome = backend.invoke(
        argv=[sys.executable, "-c", prog],
        query_bytes=b"{}",
        query_file_name="research_query.json",
        max_stdout_bytes=100,
        max_stderr_bytes=100,
        max_wall_seconds=30,
    )
    assert outcome.stdout_truncated is True
    assert len(outcome.stdout) == 100
