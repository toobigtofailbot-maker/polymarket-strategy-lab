"""WP175H external-process boundary traps for the pinned v0.21.3 contract.

R002 shell metacharacters cannot become shell execution.
R003 the repository path is never supplied as the Hermes working directory.
R010 a timeout terminates the run and yields a sanitized outcome.
R016 the fake backend makes zero network/process calls.
Plus: version preflight, usage-file read-back, and the non-secret Hermes-home boundary.
"""

from __future__ import annotations

import dataclasses
import json
import os
import sys
import textwrap
from pathlib import Path

import pytest

from src.research_runtime.hermes_controlled_runtime import (
    DEFAULT_HERMES_INVOCATION_POLICY,
    ExternalHermesCliBackend,
    FakeHermesBackend,
    HermesInvocationOutcome,
    build_hermes_argv,
    build_research_run_request,
    build_version_argv,
    is_clean_research_home_control_plane,
    is_safe_research_home,
)
from src.research_runtime.hermes_controlled_runtime import runner as runner_mod
from src.research_runtime.hermes_controlled_runtime import policy as policy_mod

MANAGED_BYTES = DEFAULT_HERMES_INVOCATION_POLICY.managed_config_bytes()
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
    # WP175I P001: --safe-mode is REMOVED from the research invocation (it suppresses
    # the bundled Firecrawl backend on exact v0.21.3).
    assert "--safe-mode" not in argv  # P001
    # WP175I P002/P003: exact ignore flags retained, exactly one --toolsets web.
    assert "--ignore-user-config" in argv and "--ignore-rules" in argv  # P002
    # Supported one-shot shape (exact tagged top-level flags only). T04
    assert "-z" in argv and argv[-1] == "PROMPT"
    assert "--usage-file" in argv
    supported = {
        "hermes", "--ignore-user-config", "--ignore-rules",
        "--provider", "--model", "--toolsets", "--usage-file", "-z",
    }
    flags = {tok for tok in argv if tok.startswith("--") or tok == "-z"}
    assert flags <= supported, flags - supported
    assert argv.count("--toolsets") == 1  # P003
    assert argv[argv.index("--toolsets") + 1] == "web"
    for forbidden in ("terminal", "file", "browser", "delegation", "memory", "cron", "mcp", "safe"):
        assert forbidden not in argv


def test_p004_unsupported_flags_stay_absent_from_argv():
    """P004: --max-turns / --format / stream-json / --input-file never appear."""
    req = _request()
    argv = build_hermes_argv("hermes", req, "PROMPT")
    for forbidden in ("--max-turns", "--format", "stream-json", "--input-file", "chat", "--oneshot"):
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
    prog = "import sys; sys.stdout.write('Hermes Agent v0.21.3 (2026.9.14)')"
    probe = ExternalHermesCliBackend().probe_version(
        version_argv=[sys.executable, "-c", prog], max_output_bytes=4096, max_wall_seconds=15,
    )
    assert probe.launched is True and probe.timed_out is False
    assert probe.exit_code == 0 and probe.stdout_truncated is False
    assert probe.version_text == "Hermes Agent v0.21.3 (2026.9.14)"


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


# ---------------------------------------------------------------------------
# WP175I controlled managed scope + research-home control-plane preflight
# ---------------------------------------------------------------------------

# A fake-hermes program that reports its controlled-profile isolation: cwd, the
# backend-created HERMES_MANAGED_DIR + the managed config.yaml it can read there,
# whether control-plane env vars leaked, and a marker to look like a real run.
_MANAGED_INSPECT_PROG = textwrap.dedent(
    """
    import os, json, pathlib
    md = os.environ.get("HERMES_MANAGED_DIR")
    cfg = ""
    if md:
        try:
            cfg = pathlib.Path(md, "config.yaml").read_text(encoding="utf-8")
        except Exception:
            cfg = ""
    print(json.dumps({
        "cwd": os.getcwd(),
        "managed_dir": md,
        "managed_cfg": cfg,
        "safe_mode": os.environ.get("HERMES_SAFE_MODE"),
        "enable_project_plugins": os.environ.get("HERMES_ENABLE_PROJECT_PLUGINS"),
        "has_secret": "OPENAI_API_KEY" in os.environ,
    }))
    """
)


def _capture_mkdtemp(monkeypatch):
    """Record ephemeral dirs the backend creates, keyed by prefix."""
    created: dict[str, list[str]] = {"hermes_oneshot_": [], "hermes_managed_": []}
    real = runner_mod.tempfile.mkdtemp

    def _spy(*args, **kwargs):
        path = real(*args, **kwargs)
        prefix = kwargs.get("prefix", "")
        created.setdefault(prefix, []).append(path)
        return path

    monkeypatch.setattr(runner_mod.tempfile, "mkdtemp", _spy)
    return created


def test_p017_p018_separate_cwd_and_managed_dir_with_config(monkeypatch):
    created = _capture_mkdtemp(monkeypatch)
    outcome = ExternalHermesCliBackend().invoke(
        argv=[sys.executable, "-c", _MANAGED_INSPECT_PROG], usage_file_name="hermes_usage.json",
        max_stdout_bytes=200_000, max_stderr_bytes=65_536, max_usage_bytes=65_536,
        max_wall_seconds=30, managed_config_bytes=MANAGED_BYTES,
    )
    assert outcome.launch_failed is False and outcome.timed_out is False
    data = [json.loads(l) for l in outcome.stdout.decode().splitlines() if l.strip()][-1]
    # P017: cwd and managed dir are distinct ephemeral paths.
    cwd = Path(data["cwd"]).resolve()
    managed = Path(data["managed_dir"]).resolve()
    assert cwd != managed
    assert "hermes_oneshot_" in str(created["hermes_oneshot_"][0])
    assert "hermes_managed_" in str(managed)
    # P018: the child received the backend-created HERMES_MANAGED_DIR whose config.yaml
    # is exactly the deterministic managed bytes.
    assert data["managed_cfg"].encode("utf-8") == MANAGED_BYTES


def test_p019_ambient_managed_dir_is_never_forwarded(monkeypatch):
    monkeypatch.setenv("HERMES_MANAGED_DIR", "/attacker/controlled/scope")
    outcome = ExternalHermesCliBackend().invoke(
        argv=[sys.executable, "-c", _MANAGED_INSPECT_PROG], usage_file_name="hermes_usage.json",
        max_stdout_bytes=200_000, max_stderr_bytes=65_536, max_usage_bytes=65_536,
        max_wall_seconds=30, managed_config_bytes=MANAGED_BYTES,
    )
    data = [json.loads(l) for l in outcome.stdout.decode().splitlines() if l.strip()][-1]
    # The child sees the backend's ephemeral dir, never the ambient value.
    assert data["managed_dir"] != "/attacker/controlled/scope"
    assert "hermes_managed_" in str(data["managed_dir"])


def test_p020_ambient_safe_mode_and_project_plugins_never_forwarded(monkeypatch):
    monkeypatch.setenv("HERMES_SAFE_MODE", "1")
    monkeypatch.setenv("HERMES_ENABLE_PROJECT_PLUGINS", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-should-not-leak")
    outcome = ExternalHermesCliBackend().invoke(
        argv=[sys.executable, "-c", _MANAGED_INSPECT_PROG], usage_file_name="hermes_usage.json",
        max_stdout_bytes=200_000, max_stderr_bytes=65_536, max_usage_bytes=65_536,
        max_wall_seconds=30, managed_config_bytes=MANAGED_BYTES,
    )
    data = [json.loads(l) for l in outcome.stdout.decode().splitlines() if l.strip()][-1]
    assert data["safe_mode"] is None
    assert data["enable_project_plugins"] is None
    assert data["has_secret"] is False
    # _minimal_env also excludes them directly.
    env = runner_mod._minimal_env(None)
    for name in ("HERMES_SAFE_MODE", "HERMES_ENABLE_PROJECT_PLUGINS", "HERMES_MANAGED_DIR"):
        assert name not in env


def test_p021_managed_dir_removed_on_success(monkeypatch):
    created = _capture_mkdtemp(monkeypatch)
    ExternalHermesCliBackend().invoke(
        argv=[sys.executable, "-c", "print('hi')"], usage_file_name="hermes_usage.json",
        max_stdout_bytes=1000, max_stderr_bytes=1000, max_usage_bytes=1000, max_wall_seconds=30,
        managed_config_bytes=MANAGED_BYTES,
    )
    assert created["hermes_managed_"], "a managed dir must have been created"
    for path in created["hermes_managed_"] + created["hermes_oneshot_"]:
        assert not Path(path).exists()


def test_p022_managed_dir_removed_on_timeout(monkeypatch):
    created = _capture_mkdtemp(monkeypatch)
    outcome = ExternalHermesCliBackend().invoke(
        argv=[sys.executable, "-c", "import time; time.sleep(30)"],
        usage_file_name="hermes_usage.json", max_stdout_bytes=1000, max_stderr_bytes=1000,
        max_usage_bytes=1000, max_wall_seconds=1, managed_config_bytes=MANAGED_BYTES,
    )
    assert outcome.timed_out is True
    assert created["hermes_managed_"]
    for path in created["hermes_managed_"] + created["hermes_oneshot_"]:
        assert not Path(path).exists()


def test_p023_managed_dir_removed_on_launch_failure(monkeypatch):
    created = _capture_mkdtemp(monkeypatch)
    outcome = ExternalHermesCliBackend().invoke(
        argv=[str(REPO_ROOT / "definitely_not_an_executable_xyz")],
        usage_file_name="hermes_usage.json", max_stdout_bytes=1000, max_stderr_bytes=1000,
        max_usage_bytes=1000, max_wall_seconds=5, managed_config_bytes=MANAGED_BYTES,
    )
    assert outcome.launch_failed is True
    for path in created["hermes_managed_"] + created["hermes_oneshot_"]:
        assert not Path(path).exists()


def test_p024_research_home_in_repo_or_local_data_fails_closed(tmp_path):
    # Repo tree and local_data are rejected outright.
    assert is_clean_research_home_control_plane(str(REPO_ROOT)) is False
    assert is_clean_research_home_control_plane(
        str(Path(os.path.expanduser("~")) / "local_data" / "h")
    ) is False
    # An unsafe home passed to invoke fails closed before spawn (no HERMES_HOME set).
    outcome = ExternalHermesCliBackend().invoke(
        argv=[sys.executable, "-c", "print('x')"], usage_file_name="hermes_usage.json",
        max_stdout_bytes=1000, max_stderr_bytes=1000, max_usage_bytes=1000, max_wall_seconds=5,
        hermes_home=str(REPO_ROOT), managed_config_bytes=MANAGED_BYTES,
    )
    assert outcome.launch_failed is True


def test_p025_research_home_config_yaml_fails_closed(tmp_path):
    home = tmp_path / "research_home"
    home.mkdir()
    (home / "config.yaml").write_text("web:\n  keyless_fallback: true\n", encoding="utf-8")
    assert is_clean_research_home_control_plane(str(home)) is False
    outcome = ExternalHermesCliBackend().invoke(
        argv=[sys.executable, "-c", "print('x')"], usage_file_name="hermes_usage.json",
        max_stdout_bytes=1000, max_stderr_bytes=1000, max_usage_bytes=1000, max_wall_seconds=5,
        hermes_home=str(home), managed_config_bytes=MANAGED_BYTES,
    )
    assert outcome.launch_failed is True


def test_p026_research_home_user_plugins_fail_closed(tmp_path):
    home = tmp_path / "research_home"
    (home / "plugins" / "evil").mkdir(parents=True)
    (home / "plugins" / "evil" / "plugin.yaml").write_text("name: evil\n", encoding="utf-8")
    assert is_clean_research_home_control_plane(str(home)) is False
    outcome = ExternalHermesCliBackend().invoke(
        argv=[sys.executable, "-c", "print('x')"], usage_file_name="hermes_usage.json",
        max_stdout_bytes=1000, max_stderr_bytes=1000, max_usage_bytes=1000, max_wall_seconds=5,
        hermes_home=str(home), managed_config_bytes=MANAGED_BYTES,
    )
    assert outcome.launch_failed is True


def test_p027_research_home_auth_and_env_alone_is_permitted(tmp_path, monkeypatch):
    # A dedicated home with only a credential store (.env / auth.json) and an empty
    # plugins dir is a valid H1 profile; its secret values are never read/echoed.
    home = tmp_path / "research_home"
    home.mkdir()
    (home / ".env").write_text("FIRECRAWL_API_KEY=fc-should-not-be-read\n", encoding="utf-8")
    (home / "auth.json").write_text('{"codex": "token-should-not-be-read"}\n', encoding="utf-8")
    (home / "plugins").mkdir()  # present but empty is allowed
    assert is_clean_research_home_control_plane(str(home)) is True
    created = _capture_mkdtemp(monkeypatch)
    outcome = ExternalHermesCliBackend().invoke(
        argv=[sys.executable, "-c", _MANAGED_INSPECT_PROG], usage_file_name="hermes_usage.json",
        max_stdout_bytes=200_000, max_stderr_bytes=65_536, max_usage_bytes=65_536,
        max_wall_seconds=30, hermes_home=str(home), managed_config_bytes=MANAGED_BYTES,
    )
    assert outcome.launch_failed is False
    data = [json.loads(l) for l in outcome.stdout.decode().splitlines() if l.strip()][-1]
    # No secret value from the home is present in sanitized evidence (stdout is the
    # child's own report; the backend records no home contents).
    assert "fc-should-not-be-read" not in json.dumps(data)
    assert "token-should-not-be-read" not in json.dumps(data)
    for path in created["hermes_managed_"]:
        assert not Path(path).exists()


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


# ---------------------------------------------------------------------------
# WP175K (S10-HERMES-01C): sanitized failure-evidence capture
# ---------------------------------------------------------------------------

_sanitize = runner_mod._sanitize_stderr
_MAXEX = runner_mod.MAX_SANITIZED_STDERR_EXCERPT_BYTES

# Clearly-fake deterministic sentinels (never resemble a real credential in use).
_FAKE_SK = "sk-" + "A" * 40
_FAKE_GHP = "ghp_" + "B" * 36
_FAKE_PAT = "github_pat_" + "C" * 30
_FAKE_XOX = "xoxb-" + "1234567890-ABCDEFGHIJ"


def _enc_len(text):
    return len(text.encode("utf-8"))


def test_wp175k_a_ordinary_traceback_keeps_reason_scrubs_path():  # A
    raw = (
        'Traceback (most recent call last):\n'
        '  File "C:\\Users\\alice\\proj\\hermes_cli\\oneshot.py", line 7, in run\n'
        "    raise RuntimeError('provider init failed')\n"
        "RuntimeError: provider init failed\n"
    ).encode("utf-8")
    res = _sanitize(raw)
    assert res.status in ("AVAILABLE", "AVAILABLE_REDACTED")
    assert res.excerpt is not None
    assert "RuntimeError: provider init failed" in res.excerpt
    assert "alice" not in res.excerpt and "C:\\Users" not in res.excerpt
    assert "<PATH>" in res.excerpt
    assert _enc_len(res.excerpt) <= _MAXEX


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("API_KEY", _FAKE_SK),
        ("TOKEN", "tok_DEADBEEF_should_not_survive"),
        ("ACCESS_TOKEN", "at_DEADBEEF_should_not_survive"),
        ("REFRESH_TOKEN", "rt_DEADBEEF_should_not_survive"),
        ("PASSWORD", "hunter2_should_not_survive"),
        ("MNEMONIC", "alpha bravo charlie delta echo foxtrot"),
        ("CLOB_SECRET", "clob_DEADBEEF_should_not_survive"),
    ],
)
def test_wp175k_b_named_secret_assignments_redacted(name, value):  # B
    raw = f"boot error\n{name}={value}\nRuntimeError: denied\n".encode("utf-8")
    res = _sanitize(raw)
    assert res.status == "AVAILABLE_REDACTED"
    assert res.redaction_applied is True
    assert value not in res.excerpt
    assert "<REDACTED>" in res.excerpt
    assert "RuntimeError: denied" in res.excerpt


def test_wp175k_c_json_like_secrets_redacted():  # C
    raw = (
        '{"api_key": "' + _FAKE_SK + '", "access_token": "at_secret_value_x", '
        '"note": "startup"}\n'
    ).encode("utf-8")
    res = _sanitize(raw)
    assert res.status == "AVAILABLE_REDACTED"
    assert _FAKE_SK not in res.excerpt
    assert "at_secret_value_x" not in res.excerpt


def test_wp175k_d_bearer_basic_authorization_redacted():  # D
    raw = (
        "Authorization: Bearer abcdef0123456789ABCDEF\n"
        "used Basic YWxpY2U6c2VjcmV0cGFzcw==\n"
        "auth failed\n"
    ).encode("utf-8")
    res = _sanitize(raw)
    assert res.status == "AVAILABLE_REDACTED"
    assert "abcdef0123456789ABCDEF" not in res.excerpt
    assert "YWxpY2U6c2VjcmV0cGFzcw==" not in res.excerpt
    assert "auth failed" in res.excerpt


def test_wp175k_e_pem_private_key_block_removed():  # E
    # The PEM begin marker is split across adjacent literals so the plain marker does
    # not appear contiguously in this source file (repo secret-placeholder guard); at
    # runtime the fragments concatenate into the real marker the sanitizer must remove.
    begin_marker = "-----BEGIN PRIVATE" + " KEY-----"
    end_marker = "-----END PRIVATE" + " KEY-----"
    raw = (
        "loading key\n" + begin_marker + "\n"
        "MIIBVAIBADANBgkqhkiG9w0BExampleExampleExample\n"
        "AnotherLineOfBase64ExampleExampleExample==\n"
        + end_marker + "\nkey load failed\n"
    ).encode("utf-8")
    res = _sanitize(raw)
    assert res.status == "AVAILABLE_REDACTED"
    assert "BEGIN PRIVATE KEY" not in res.excerpt
    assert "MIIBVAIBAD" not in res.excerpt
    assert "key load failed" in res.excerpt


@pytest.mark.parametrize("token", [_FAKE_SK, _FAKE_GHP, _FAKE_PAT, _FAKE_XOX])
def test_wp175k_f_token_prefixes_redacted(token):  # F
    raw = f"startup used credential {token} then failed\n".encode("utf-8")
    res = _sanitize(raw)
    assert res.status == "AVAILABLE_REDACTED"
    assert token not in res.excerpt


def test_wp175k_f_jwt_redacted():  # F (JWT)
    jwt = "eyJhbGciOiJIUzI1Niabc.eyJzdWIiOiIxMjM0NTYabc.SflKxwRJSMeKKF2QTabc"
    raw = f"token was {jwt}\n".encode("utf-8")
    res = _sanitize(raw)
    assert res.status == "AVAILABLE_REDACTED"
    assert jwt not in res.excerpt


def test_wp175k_g_url_credentials_and_query_removed():  # G
    raw = (
        "fetch https://user:s3cretpass@example.com/path failed\n"
        "GET https://api.example.com/v1?api_key=SECRETQUERYVALUE#frag=x\n"
    ).encode("utf-8")
    res = _sanitize(raw)
    assert res.status == "AVAILABLE_REDACTED"
    assert "s3cretpass" not in res.excerpt
    assert "SECRETQUERYVALUE" not in res.excerpt


def test_wp175k_h_local_paths_scrubbed():  # H
    raw = (
        'win "C:\\Users\\bob\\repo\\src\\x.py"\n'
        "nix /home/bob/project/x.py\n"
        "mac /Users/bob/project/y.py\n"
        "tmp /tmp/hermes_oneshot_abcd/usage.json\n"
    ).encode("utf-8")
    res = _sanitize(raw)
    assert res.excerpt is not None
    for leaked in ("bob", "C:\\Users", "/home/bob", "/Users/bob", "/tmp/hermes_oneshot_abcd"):
        assert leaked not in res.excerpt
    assert "<PATH>" in res.excerpt


def test_wp175k_i_invalid_utf8_and_control_chars_never_raise():  # I
    raw = b"\xff\xfe bad bytes \x00\x07 mixed \x1b[31m RuntimeError: x\n"
    res = _sanitize(raw)
    assert res.status in ("AVAILABLE", "AVAILABLE_REDACTED", "BLOCKED_UNSAFE")
    if res.excerpt is not None:
        assert "\x00" not in res.excerpt and "\x07" not in res.excerpt
        assert _enc_len(res.excerpt) <= _MAXEX


def test_wp175k_j_long_stderr_keeps_bounded_tail():  # J
    lines = "".join(f"log line {i} ordinary text\n" for i in range(4000))
    raw = (lines + "RuntimeError: the real final reason\n").encode("utf-8")
    res = _sanitize(raw)
    assert res.status in ("AVAILABLE", "AVAILABLE_REDACTED")
    assert res.excerpt_truncated is True
    assert _enc_len(res.excerpt) <= _MAXEX
    # The tail (final fatal reason) is retained, not the head.
    assert "RuntimeError: the real final reason" in res.excerpt
    assert "log line 0 ordinary text" not in res.excerpt


def test_wp175k_k_residual_unsafe_fails_closed():  # K
    # A bare, unlabeled high-entropy blob that no named/structured rule targets: it is
    # not safely representable, so residual detection blocks the whole excerpt.
    blob = "Q7x" + "kZ9pLmN2wR4tV6yB8dF0hJ3sA5cE1gI7uO" * 3
    assert len(blob) >= 64
    raw = f"fatal: {blob}\n".encode("utf-8")
    res = _sanitize(raw)
    assert res.status == "BLOCKED_UNSAFE"
    assert res.excerpt is None


def test_wp175k_l_sanitizer_internal_error_is_fail_closed(monkeypatch):  # L
    # A deterministic fault inside the sanitizer must yield SANITIZER_ERROR with no
    # excerpt and must never propagate into the invocation path.
    def _boom(*a, **k):
        raise RuntimeError("synthetic sanitizer fault")

    monkeypatch.setattr(runner_mod, "_STDERR_CONTROL_CHARS", type("X", (), {"sub": staticmethod(_boom)}))
    res = _sanitize(b"some stderr text\nRuntimeError: x\n")
    assert res.status == "SANITIZER_ERROR"
    assert res.excerpt is None


def test_wp175k_m_outcome_has_no_raw_stderr_member():  # M
    fields = {f.name for f in dataclasses.fields(HermesInvocationOutcome)}
    assert "stderr_excerpt" in fields
    assert "raw_stderr" not in fields and "stderr" not in fields and "stderr_bytes" not in fields


def test_wp175k_empty_stderr_is_empty_status():
    assert _sanitize(b"").status == "EMPTY"
    assert _sanitize(None).status == "EMPTY"
    assert _sanitize(b"   \n\t ").status == "EMPTY"


def test_wp175k_external_backend_smoke_sanitizes_exit1_child():
    """Section 12: a harmless local subprocess (NOT Hermes -z) exits 1, prints a
    traceback with a fake secret and a fake local path to stderr, writes no usage
    file. The external backend surfaces a sanitized excerpt with neither leaked, and
    makes zero network/provider/Firecrawl calls."""
    prog = textwrap.dedent(
        r"""
        import sys
        sys.stderr.write('Traceback (most recent call last):\n')
        sys.stderr.write('  File "C:\\Users\\carol\\hermes\\run.py", line 3, in main\n')
        sys.stderr.write('API_KEY=sk-FAKE0000000000000000000000000000\n')
        sys.stderr.write('RuntimeError: synthetic provider failure\n')
        sys.exit(1)
        """
    )
    outcome = ExternalHermesCliBackend().invoke(
        argv=[sys.executable, "-c", prog], usage_file_name="hermes_usage.json",
        max_stdout_bytes=200_000, max_stderr_bytes=65_536, max_usage_bytes=65_536,
        max_wall_seconds=30,
    )
    assert outcome.exit_code == 1
    assert outcome.launch_failed is False and outcome.timed_out is False
    assert outcome.usage_file_bytes is None  # no usage file written
    assert outcome.stderr_sanitization_status in ("AVAILABLE", "AVAILABLE_REDACTED")
    excerpt = outcome.stderr_excerpt or ""
    assert "sk-FAKE0000000000000000000000000000" not in excerpt
    assert "carol" not in excerpt and "C:\\Users" not in excerpt
    assert "RuntimeError: synthetic provider failure" in excerpt


def test_wp175k_g_credential_free_url_stays_readable():
    # A plain URL with no userinfo and no query carries no credential and must remain
    # readable: the drive-letter path rule must not match the "s://" in "https://".
    raw = b"GET https://example.com/v1/models failed with 500\n"
    res = _sanitize(raw)
    assert res.status in ("AVAILABLE", "AVAILABLE_REDACTED")
    assert "https://example.com/v1/models" in res.excerpt
    assert "<PATH>" not in res.excerpt


def test_wp175k_k_medium_unlabeled_blob_also_fails_closed():
    # An unlabeled ~48-char high-entropy blob (no key name, no known prefix) that a
    # base64-encoded 32-byte key would produce must still fail closed.
    blob = "A1b2C3d4" * 6  # 48 chars, no named/prefixed structure
    assert 44 <= len(blob) < 64
    res = _sanitize(f"fatal auth: {blob}\n".encode("utf-8"))
    assert res.status == "BLOCKED_UNSAFE"
    assert res.excerpt is None


# ---------------------------------------------------------------------------
# Side11 finding A: an UNQUOTED multiword secret assignment must not leak the
# remainder tokens after the first whitespace (deterministic, fake words only).
# ---------------------------------------------------------------------------


def test_wp175k_a1_multiword_mnemonic_assignment_fully_redacted():
    # Every token of an unquoted seed phrase must be gone, not just the first word.
    raw = b"boot error\nMNEMONIC=alpha bravo charlie delta echo foxtrot\ndenied later\n"
    res = _sanitize(raw)
    assert res.status == "AVAILABLE_REDACTED"
    assert res.redaction_applied is True
    assert res.excerpt is not None
    for word in ("alpha", "bravo", "charlie", "delta", "echo", "foxtrot"):
        assert word not in res.excerpt
    assert "<REDACTED>" in res.excerpt
    # Over-redaction stops at the newline, so the next line stays readable.
    assert "denied later" in res.excerpt


def test_wp175k_a2_multiword_password_assignment_fully_redacted():
    raw = b"PASSWORD=first second third\n"
    res = _sanitize(raw)
    assert res.status == "AVAILABLE_REDACTED"
    assert res.redaction_applied is True
    assert res.excerpt is not None
    for word in ("first", "second", "third"):
        assert word not in res.excerpt
    assert "<REDACTED>" in res.excerpt


def test_wp175k_a_quoted_secret_leaves_following_pair_readable():
    # The exact-value quoted branch must still scrub only the secret, so a trailing
    # non-secret key/value on the same JSON line survives (no over-redaction).
    raw = b'{"password": "hunter2xx", "note": "startup ok"}\n'
    res = _sanitize(raw)
    assert res.status == "AVAILABLE_REDACTED"
    assert res.excerpt is not None
    assert "hunter2xx" not in res.excerpt
    assert '"note": "startup ok"' in res.excerpt


# ---------------------------------------------------------------------------
# Side11 finding B: a quoted absolute path with spaces must be fully scrubbed;
# the bare-path fallbacks alone stop at the first space and leak identity.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("label", "quoted_path", "suffix"),
    [
        ("win", '"C:\\Users\\Alice Smith\\proj\\foo.py"', "foo.py"),
        ("mac", '"/Users/Alice Smith/proj/foo.py"', "foo.py"),
        ("linux", '"/home/Alice Smith/proj/foo.py"', "foo.py"),
        ("temp", '"/tmp/Alice Smith/run/output.log"', "output.log"),
        ("unc", '"\\\\server\\share\\Alice Smith\\proj\\foo.py"', "foo.py"),
    ],
)
def test_wp175k_b_quoted_spaced_path_scrubbed(label, quoted_path, suffix):
    raw = f"File {quoted_path}, line 7, in main\nRuntimeError: boom\n".encode("utf-8")
    res = _sanitize(raw)
    assert res.status in ("AVAILABLE", "AVAILABLE_REDACTED")
    assert res.excerpt is not None
    # Synthetic username fragments and the path suffix must all be gone.
    assert "Alice" not in res.excerpt and "Smith" not in res.excerpt
    assert suffix not in res.excerpt
    assert "<PATH>" in res.excerpt
    # Surrounding traceback text around the path may remain.
    assert "RuntimeError: boom" in res.excerpt


# ---------------------------------------------------------------------------
# Side11 finding C: credential-bearing query/fragment material must be removed
# for ws/wss (and any scheme), while the credential-free base URL stays readable.
# ---------------------------------------------------------------------------


def test_wp175k_c_ws_wss_query_fragment_scheme_covered():
    raw = b"wss://example.invalid/socket?access_token=SYNTHETIC_SECRET#frag=value\n"
    res = _sanitize(raw)
    assert res.status == "AVAILABLE_REDACTED"
    assert res.excerpt is not None
    assert "SYNTHETIC_SECRET" not in res.excerpt
    assert "frag=value" not in res.excerpt
    assert "access_token=SYNTHETIC_SECRET" not in res.excerpt
    # The safe base URL may remain; no <PATH> corruption of the URL body.
    assert "wss://example.invalid/socket" in res.excerpt
    assert "<PATH>" not in res.excerpt
