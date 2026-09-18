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
            "max_wall_seconds": 60,
            "max_output_bytes": 200_000,
            "max_accepted_estimated_cost_usd": "1",
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
    assert "--input-file" not in argv  # T01
    assert "--format" not in argv  # T02
    assert "stream-json" not in argv  # T02
    # --max-turns is chat-subparser only in v0.21.3; never on the top-level -z path.
    assert "--max-turns" not in argv  # T03
    # Supported one-shot shape (exact tagged top-level flags only). T04
    assert "-z" in argv and argv[-1] == "PROMPT"
    assert "--usage-file" in argv
    assert "--safe-mode" in argv
    assert "--ignore-user-config" in argv and "--ignore-rules" in argv
    supported = {
        "hermes", "--safe-mode", "--ignore-user-config", "--ignore-rules",
        "--provider", "--model", "--toolsets", "--usage-file", "-z",
    }
    flags = {tok for tok in argv if tok.startswith("--") or tok == "-z"}
    assert flags <= supported, flags - supported
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
    assert probe.exit_code == 0 and probe.stdout_truncated is False
    assert "0.21.3" in (probe.version_text or "")


# A version-probe stand-in that reports its isolation: HERMES_HOME, that home's
# config.yaml, the presence of a provider-secret env var, and its cwd.
_PROBE_INSPECT_PROG = textwrap.dedent(
    """
    import os, json, pathlib
    home = os.environ.get("HERMES_HOME")
    cfg = ""
    try:
        cfg = pathlib.Path(home, "config.yaml").read_text(encoding="utf-8")
    except Exception:
        cfg = ""
    print(json.dumps({
        "home": home,
        "cfg": cfg,
        "has_secret": "OPENAI_API_KEY" in os.environ,
        "cwd": os.getcwd(),
        "marker": "hermes-agent 0.21.3",
    }))
    """
)


def test_version_probe_isolated_update_disabled_home_and_clean(monkeypatch):  # C14-C17
    # A provider secret in the parent env must not reach the probe child.
    monkeypatch.setenv("OPENAI_API_KEY", "sk-should-not-leak")
    probe = ExternalHermesCliBackend().probe_version(
        version_argv=[sys.executable, "-c", _PROBE_INSPECT_PROG],
        max_output_bytes=4096, max_wall_seconds=30,
    )
    assert probe.launched is True and probe.exit_code == 0
    data = json.loads(probe.version_text)
    home = data["home"]
    # C14: a dedicated throwaway HERMES_HOME (never the real research home).
    assert home and "hermes_verprobe_" in home
    # C16: its config disables the passive update check.
    assert "updates" in data["cfg"] and "check: false" in data["cfg"]
    # C17: no provider secret was forwarded into the probe environment.
    assert data["has_secret"] is False
    # cwd is the probe home, never the repository root.
    assert Path(data["cwd"]).resolve() != REPO_ROOT
    # C15: the probe home is removed on teardown.
    assert not Path(home).exists()


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


def test_c18_repo_home_rejected_regardless_of_cwd(monkeypatch, tmp_path):  # C18
    # The repository boundary is derived from the module location, not os.getcwd():
    # chdir OUTSIDE the repo and a HERMES_HOME inside the repo is still rejected.
    monkeypatch.chdir(tmp_path)
    assert is_safe_research_home(str(REPO_ROOT)) is False
    assert is_safe_research_home(str(REPO_ROOT / "sub" / "hermes_home")) is False


def test_c19_external_dedicated_home_accepted(tmp_path):  # C19
    external = tmp_path / "dedicated_research_home"
    external.mkdir()
    assert is_safe_research_home(str(external)) is True


def test_c20_windows_argv_bound_with_quote_heavy_content():  # C20
    req = _request()
    # Quote-heavy content stays under the raw prompt byte bound but expands past the
    # assembled Windows command-line ceiling after argv quoting (each " -> \").
    quote_heavy = '"' * 16000
    assert len(quote_heavy.encode("utf-8")) <= policy_mod.MAX_PROMPT_BYTES
    import subprocess as _sp
    # Sanity: the assembled command line really does exceed the ceiling.
    assembled = _sp.list2cmdline(build_version_argv("hermes")[:1] + (quote_heavy,))
    assert len(assembled) > policy_mod.MAX_COMMAND_LINE_CHARS
    with pytest.raises(policy_mod.PolicyBroadeningError):
        build_hermes_argv("hermes", req, quote_heavy)
